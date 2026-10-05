#!/usr/bin/env python3
"""
Lanzador de las prácticas del repo Sensores-Teoria.

Para quien no conoce el repo: doble clic en PROBAR.bat (Windows) o `python probar.py`.
Se abre una página en el navegador (el "hub") con una tarjeta por práctica: qué pide el
enunciado, qué se puede probar sin hardware y un botón por cada cosa que se puede lanzar.

Cómo funciona por dentro (solo biblioteca estándar, Python >= 3.9, para que no haya que
instalar nada antes de poder abrir el lanzador):

  1. Cada práctica declara cómo se prueba en `<carpeta>/probar.json` (ver CONTRATO abajo).
  2. Este script levanta un servidor HTTP en 127.0.0.1 (solo esta máquina; nunca en la red)
     y sirve la página del hub, que lee esos manifiestos por una API JSON.
  3. Al pulsar un botón, el hub le pide al servidor "lanza la acción X de la práctica Y".
     El servidor SOLO ejecuta acciones declaradas en un probar.json: nunca un comando que
     venga escrito desde la página. Además exige un token secreto (que solo conoce la página
     que sirvió) para que otra web abierta en el navegador no pueda dispararlas.
  4. Las acciones `python` corren en una CONSOLA NUEVA con el entorno virtual de la práctica
     (`<carpeta>/entorno/`), creado e instalado solo la primera vez, mostrando el progreso.

CONTRATO de probar.json (el del plan, con las precisiones de este lanzador):

{
  "id": "7",                                   # texto corto; se muestra como número de la tarjeta
  "titulo": "...", "resumen": "1-3 frases",
  "pide": ["cada punto del enunciado", ...],   # lista de textos (un texto suelto también vale)
  "notas": "requisitos especiales",            # texto o lista de textos (opcional)
  "python": {"versiones": ["3.13", "3.12"],    # orden de preferencia para CREAR el entorno
             "paquetes": ["pybullet==3.2.7"]}, # lo que se instala con pip (opcional si no hay python)
  "acciones": [ {
      "id": "sim", "nombre": "...", "tipo": "python|html|archivo|docker|url|info",
      "descripcion": "qué se ve y cómo se usa", "cubre": ["punto del enunciado", ...],
      # "cwd" (cualquier tipo): subcarpeta de la práctica, por defecto ".". "script" y
      #          "archivo" son relativos a "cwd" (si ahí no están, se prueba en la carpeta).
      # python : "script", o en su lugar "modulo" (corre `python -m modulo`, AÑADIDO por este
      #          lanzador, retrocompatible), "args": [...]. Opcional (AÑADIDO): "paquetes" de
      #          la acción, si necesita menos que los de toda la práctica. El entorno es
      #          <carpeta>/entorno; si no existe y <cwd>/entorno sí y encuentra todo lo que el
      #          script importa, se usa ese (el tema 8 tiene uno por punto). En Windows, si los
      #          paquetes incluyen pybullet (no hay ruedas: se compila), pip corre dentro de
      #          vcvars64.bat de las Visual Studio Build Tools, o se avisa cómo instalarlas.
      #          La consola queda abierta al terminar ("Pulsa Enter") para leer el resultado.
      # html   : "archivo" -> se abre en el navegador servido por este mismo servidor
      #          (http://127.0.0.1:puerto/repo/...), así funcionan Web Serial, la cámara y los
      #          fetch relativos, que desde file:// a veces no.
      # archivo: "archivo" -> se abre con el programa del sistema (imagen, video, pdf, .bat).
      # docker : "compose", "args" (por defecto ["up", "-d"]), "abrir" (url a abrir cuando
      #          termina bien), "detener" (args para parar; por defecto ["stop"]).
      # url    : "url" (o "abrir") -> se abre en el navegador.
      # info   : solo texto; si trae "archivo" se puede ver en el navegador.
  } ]
}

Opciones de línea de comandos (sobre todo para desarrollar/probar el lanzador):
  --puerto N        puerto preferido (8099 por defecto; si está ocupado busca otro libre)
  --raiz DIR        carpeta donde buscar */probar.json (por defecto la del repo)
  --entornos DIR    crear/usar los entornos en DIR/<carpeta>/entorno en vez de en cada práctica
  --no-navegador    no abrir el navegador al arrancar
  --comprobar       solo revisar los probar.json e imprimir los errores (no levanta servidor)
"""

import argparse
import json
import mimetypes
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if sys.version_info < (3, 9):  # pragma: no cover - se comprueba también en PROBAR.bat
    sys.exit("El lanzador necesita Python 3.9 o más nuevo.")

ES_WINDOWS = os.name == "nt"
ES_MAC = sys.platform == "darwin"
ESTE_ARCHIVO = Path(__file__).resolve()
TIPOS = ("python", "html", "archivo", "docker", "url", "info")
GITHUB = "https://github.com/Dathinel/Sensores-Teoria/blob/main/"
FIRMA = "lanzador-sensores-teoria"  # para reconocer un hub ya abierto en el puerto

# En Windows, los procesos auxiliares (pip, docker info, chequeos) no deben abrir una
# ventana negra que parpadea; las acciones del usuario sí abren su propia consola.
SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0) if ES_WINDOWS else 0
CONSOLA_NUEVA = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if ES_WINDOWS else 0


class Config:
    raiz = ESTE_ARCHIVO.parent      # dónde están las carpetas con probar.json
    entornos = None                 # None = <carpeta>/entorno ; si no, <entornos>/<carpeta>/entorno
    token = secrets.token_urlsafe(24)
    puerto = 8099


class ErrorClaro(Exception):
    """Error con un mensaje en español pensado para mostrarse tal cual en la página."""


# --------------------------------------------------------------------------------------
# Lectura y validación de los probar.json
# --------------------------------------------------------------------------------------

def clave_orden(nombre):
    """Ordena 1, 2, ..., 10, 11 por número (no alfabético: '10' < '2') y lo demás al final."""
    m = re.match(r"(\d+)", nombre)
    return (0, int(m.group(1)), nombre) if m else (1, 0, nombre)


def como_lista(valor):
    """Los manifiestos los escriben personas: aceptar un texto suelto donde se espera lista."""
    if valor is None:
        return []
    if isinstance(valor, (list, tuple)):
        return [v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) for v in valor]
    return [str(valor)]


def ruta_dentro(base, relativa):
    """Resuelve `relativa` dentro de `base` y se niega a salir de ella (p. ej. '../../')."""
    p = (base / relativa).resolve()
    try:
        p.relative_to(base.resolve())
    except ValueError:
        return None
    return p


def leer_manifiesto(carpeta):
    """Devuelve la práctica normalizada. NUNCA lanza: un probar.json roto produce una tarjeta
    con la lista de errores, para que un manifiesto mal escrito no tumbe todo el hub."""
    archivo = carpeta / "probar.json"
    p = {
        "carpeta": carpeta.name, "id": carpeta.name, "titulo": carpeta.name, "resumen": "",
        "pide": [], "notas": [], "python": None, "acciones": [], "errores": [],
        "readme": (carpeta / "README.md").is_file(),
        "github": GITHUB + urllib.parse.quote(carpeta.name) + "/README.md",
    }
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        p["errores"].append(f"probar.json no es JSON válido (línea {e.lineno}, columna {e.colno}): {e.msg}")
        return p
    except (OSError, UnicodeDecodeError) as e:
        p["errores"].append(f"No se pudo leer probar.json: {e}")
        return p
    if not isinstance(datos, dict):
        p["errores"].append("probar.json debe ser un objeto { ... }")
        return p

    p["id"] = str(datos.get("id", carpeta.name))
    p["titulo"] = str(datos.get("titulo") or carpeta.name)
    p["resumen"] = str(datos.get("resumen") or "")
    p["pide"] = como_lista(datos.get("pide"))
    p["notas"] = como_lista(datos.get("notas"))
    if not datos.get("titulo"):
        p["errores"].append("Falta \"titulo\".")

    py = datos.get("python")
    if py is not None:
        if not isinstance(py, dict):
            p["errores"].append("\"python\" debe ser un objeto {\"versiones\": [...], \"paquetes\": [...]}")
        else:
            p["python"] = {"versiones": como_lista(py.get("versiones")), "paquetes": como_lista(py.get("paquetes"))}
            # Para avisar en la tarjeta ANTES de instalar: PyBullet se compila en Windows.
            p["compila"] = necesita_compilar(p["python"]["paquetes"])

    acciones = datos.get("acciones")
    if not isinstance(acciones, list):
        p["errores"].append("Falta la lista \"acciones\".")
        acciones = []
    vistos = set()
    for i, a in enumerate(acciones, 1):
        p["acciones"].append(validar_accion(carpeta, a, i, vistos))
    return p


def validar_accion(carpeta, a, i, vistos):
    """Normaliza una acción y anota en "error" lo que impide lanzarla (el botón sale apagado)."""
    if not isinstance(a, dict):
        return {"id": f"accion-{i}", "nombre": f"Acción {i}", "tipo": "info", "descripcion": "",
                "cubre": [], "error": "La acción no es un objeto { ... }"}
    acc = {
        "id": str(a.get("id") or f"accion-{i}"),
        "nombre": str(a.get("nombre") or a.get("id") or f"Acción {i}"),
        "tipo": str(a.get("tipo") or ""),
        "descripcion": str(a.get("descripcion") or ""),
        "cubre": como_lista(a.get("cubre")),
        "error": None,
    }
    errores = []
    if acc["id"] in vistos:
        errores.append(f"id repetido \"{acc['id']}\"")
        acc["id"] = f"{acc['id']}-{i}"
    vistos.add(acc["id"])
    tipo = acc["tipo"]
    if tipo not in TIPOS:
        errores.append(f"tipo \"{tipo}\" desconocido (válidos: {', '.join(TIPOS)})")

    if tipo == "python":
        cwd = ruta_dentro(carpeta, str(a.get("cwd") or "."))
        if cwd is None or not cwd.is_dir():
            errores.append(f"la carpeta cwd \"{a.get('cwd')}\" no existe")
            cwd = carpeta
        acc["cwd"] = str(cwd)
        acc["args"] = [str(x) for x in (a.get("args") or [])] if isinstance(a.get("args") or [], list) else []
        if a.get("paquetes"):
            acc["paquetes"] = como_lista(a.get("paquetes"))  # opcional: lo mínimo para ESTA acción
        if a.get("modulo"):
            acc["modulo"] = str(a["modulo"])
            acc["muestra"] = "python -m " + acc["modulo"]
        elif a.get("script"):
            # Contrato: "script" es relativo a "cwd" (y "cwd" a la carpeta de la práctica). Por
            # tolerancia, si ahí no está, se prueba relativo a la carpeta de la práctica.
            s = ruta_dentro(carpeta, str(Path(cwd).relative_to(carpeta.resolve()) / str(a["script"])))
            if s is None or not s.is_file():
                s = ruta_dentro(carpeta, str(a["script"]))
            if s is None or not s.is_file():
                errores.append(f"no existe el script \"{a['script']}\"")
            else:
                acc["script"] = str(s)
            acc["muestra"] = "python " + str(a["script"])
        else:
            errores.append("falta \"script\" (o \"modulo\")")
        if acc["args"]:
            acc["muestra"] = acc.get("muestra", "") + " " + " ".join(acc["args"])

    elif tipo in ("html", "archivo") or (tipo == "info" and a.get("archivo")):
        rel = str(a.get("archivo") or "")
        f = None
        if rel and a.get("cwd"):
            # Contrato: "archivo" es relativo a "cwd" si la acción lo trae (p. ej. cwd "punto-1",
            # archivo "preview.html"); si ahí no está, se prueba relativo a la carpeta.
            base = ruta_dentro(carpeta, str(a["cwd"]))
            g = ruta_dentro(carpeta, str(Path(base).relative_to(carpeta.resolve()) / rel)) if base else None
            if g is not None and g.exists():
                f = g
                rel = g.relative_to(carpeta.resolve()).as_posix()
        if rel and f is None:
            f = ruta_dentro(carpeta, rel)
        if f is None or not f.exists():
            if tipo != "info":
                errores.append(f"no existe el archivo \"{rel}\"")
        else:
            acc["archivo"] = rel.replace("\\", "/")
            acc["ruta"] = str(f)
            # html e info se abren servidos por este servidor (ver /repo/ más abajo)
            acc["enlace"] = "/repo/" + urllib.parse.quote(f"{carpeta.name}/{acc['archivo']}")

    elif tipo == "docker":
        rel = str(a.get("compose") or "docker-compose.yml")
        f = ruta_dentro(carpeta, rel)
        if f is None or not f.is_file():
            errores.append(f"no existe el compose \"{rel}\"")
        else:
            acc["compose"] = str(f)
        args = a.get("args") or ["up", "-d"]
        det = a.get("detener") or ["stop"]
        acc["args"] = [str(x) for x in args] if isinstance(args, list) else ["up", "-d"]
        acc["detener"] = [str(x) for x in det] if isinstance(det, list) else ["stop"]
        acc["abrir"] = str(a.get("abrir") or "")
        acc["muestra"] = f"docker compose -f {rel} " + " ".join(acc["args"])

    elif tipo == "url":
        u = str(a.get("url") or a.get("abrir") or "")
        if not re.match(r"^https?://", u):
            errores.append("falta \"url\" (http:// o https://)")
        acc["url"] = u

    if errores:
        acc["error"] = "; ".join(errores)
    return acc


def carpetas_con_manifiesto():
    raiz = Config.raiz
    try:
        hijos = [d for d in raiz.iterdir() if d.is_dir() and (d / "probar.json").is_file()]
    except OSError:
        return []
    return sorted(hijos, key=lambda d: clave_orden(d.name))


def cargar_practicas():
    # Se relee en cada petición (es barato): así un probar.json recién escrito aparece al
    # recargar la página, y una acción se lanza siempre con la versión actual del manifiesto.
    return [leer_manifiesto(d) for d in carpetas_con_manifiesto()]


def buscar_practica(carpeta):
    d = ruta_dentro(Config.raiz, carpeta)
    if d is None or d.parent != Config.raiz.resolve() or not (d / "probar.json").is_file():
        raise ErrorClaro(f"No hay ninguna práctica \"{carpeta}\" con probar.json.")
    return leer_manifiesto(d)


def buscar_accion(practica, accion_id):
    for a in practica["acciones"]:
        if a["id"] == accion_id:
            if a["error"]:
                raise ErrorClaro(f"La acción \"{a['nombre']}\" tiene un error en probar.json: {a['error']}")
            return a
    raise ErrorClaro(f"La práctica {practica['carpeta']} no declara la acción \"{accion_id}\".")


# --------------------------------------------------------------------------------------
# Trabajos: cada botón pulsado es un "trabajo" con estado y log, que la página consulta
# --------------------------------------------------------------------------------------

class Trabajo:
    def __init__(self, carpeta, accion, nombre):
        self.carpeta, self.accion, self.nombre = carpeta, accion, nombre
        self.estado = "preparando"     # preparando | instalando | lanzada | terminada | error | detenida
        self.mensaje = ""
        self.pid = None
        self.codigo = None
        self.inicio = time.time()
        self.fin = None
        self.log = deque(maxlen=400)   # solo las últimas líneas: pip puede escupir miles
        self.proceso = None
        self.seguimiento = True        # False si no podemos saber cuándo termina (Terminal de macOS)
        self.cerrojo = threading.Lock()

    def escribir(self, linea):
        with self.cerrojo:
            self.log.append(linea.rstrip("\r\n")[:500])

    def poner(self, estado, mensaje=None):
        self.estado = estado
        if mensaje is not None:
            self.mensaje = mensaje
        if estado in ("terminada", "error", "detenida"):
            self.fin = time.time()

    @property
    def activo(self):
        return self.estado in ("preparando", "instalando", "lanzada")

    def a_dict(self):
        with self.cerrojo:
            log = list(self.log)
        return {"carpeta": self.carpeta, "accion": self.accion, "nombre": self.nombre,
                "estado": self.estado, "mensaje": self.mensaje, "pid": self.pid,
                "codigo": self.codigo, "inicio": self.inicio, "fin": self.fin, "log": log}


TRABAJOS = {}                 # (carpeta, accion) -> último Trabajo
TRABAJOS_LOCK = threading.Lock()
ENTORNO_LOCKS = {}            # un cerrojo por carpeta: dos botones no crean el mismo entorno a la vez
ESTADO_ENTORNOS = {}          # carpeta -> {"estado": ..., "detalle": ...} para el aviso de la tarjeta


def cerrojo_entorno(carpeta):
    with TRABAJOS_LOCK:
        return ENTORNO_LOCKS.setdefault(carpeta, threading.Lock())


def entorno_hijo():
    # UTF-8 y sin buffer: las líneas de pip y de los scripts llegan al log enseguida y con tildes.
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env.pop("PYTHONHOME", None)
    return env


def correr_con_log(trabajo, cmd, cwd=None):
    """Corre un comando sin ventana y va pasando su salida, línea a línea, al log del trabajo."""
    trabajo.escribir("$ " + " ".join(str(c) for c in cmd))
    p = subprocess.Popen([str(c) for c in cmd], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                         creationflags=SIN_VENTANA, env=entorno_hijo())
    trabajo.proceso = p
    for linea in p.stdout:
        if linea.strip():
            trabajo.escribir(linea)
    return p.wait()


def correr_corto(cmd, timeout=30, cwd=None):
    """Para chequeos rápidos (versión de Python, docker info). Devuelve (código, salida)."""
    try:
        r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, creationflags=SIN_VENTANA,
                           stdin=subprocess.DEVNULL, env=entorno_hijo(), cwd=cwd)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


# --------------------------------------------------------------------------------------
# Entornos virtuales
# --------------------------------------------------------------------------------------

def ruta_entorno(carpeta):
    if Config.entornos:
        return Config.entornos / carpeta / "entorno"
    return Config.raiz / carpeta / "entorno"


def python_del_entorno(env):
    return env / ("Scripts/python.exe" if ES_WINDOWS else "bin/python")


def nombre_distribucion(requisito):
    """'pybullet==3.2.7' -> 'pybullet'; 'paho-mqtt>=2' -> 'paho-mqtt'; 'x[extra]' -> 'x'."""
    return re.split(r"[<>=!~;\[\s@]", requisito.strip(), maxsplit=1)[0]


# Se ejecuta DENTRO del python del entorno. Se comprueba la DISTRIBUCIÓN instalada (lo que
# pip instala, p. ej. "opencv-python") con importlib.metadata, en vez de importar el módulo
# ("cv2"): así no hace falta una tabla de nombres pip -> módulo y es mucho más rápido que
# importar TensorFlow o PyBullet solo para ver si están.
CHEQUEO = (
    "import sys, json\n"
    "from importlib import metadata\n"
    "faltan = []\n"
    "for n in json.loads(sys.argv[1]):\n"
    "    try:\n"
    "        metadata.distribution(n)\n"
    "    except Exception:\n"
    "        faltan.append(n)\n"
    "print(json.dumps({'version': '%d.%d' % sys.version_info[:2], 'faltan': faltan}))\n"
)


def revisar_entorno(python, paquetes):
    """None si ese python no arranca; si arranca, {'version': 'X.Y', 'faltan': [...]}."""
    nombres = [nombre_distribucion(p) for p in paquetes]
    codigo, salida = correr_corto([python, "-c", CHEQUEO, json.dumps(nombres)], timeout=60)
    if codigo != 0:
        return None
    try:
        return json.loads(salida.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def buscar_python(version):
    """Ruta a un Python X.Y instalado, o None. En Windows con el lanzador `py -X.Y` (lo instala
    el instalador oficial de python.org); en Linux/Mac, `pythonX.Y` del PATH."""
    if "%d.%d" % sys.version_info[:2] == version:
        return sys.executable
    if ES_WINDOWS and shutil.which("py"):
        codigo, salida = correr_corto(["py", f"-{version}", "-c", "import sys; print(sys.executable)"], 20)
        if codigo == 0 and salida.strip():
            return salida.strip().splitlines()[-1]
    w = shutil.which(f"python{version}")
    return w


def versiones_instaladas():
    """Para mostrar en la cabecera del hub qué Pythons hay (ayuda a entender los avisos)."""
    vistas = []
    for v in ("3.9", "3.10", "3.11", "3.12", "3.13", "3.14"):
        if buscar_python(v):
            vistas.append(v)
    return vistas


def mensaje_instalar_python(versiones):
    v = versiones[0] if versiones else "3.12"
    if ES_WINDOWS:
        return (f"No encontré ninguna de estas versiones de Python: {', '.join(versiones)}. "
                f"Instala Python {v} desde https://www.python.org/downloads/ (busca la última \"Python {v}.x\", "
                "\"Windows installer (64-bit)\"; deja marcada la opción del \"py launcher\") y vuelve a pulsar el botón.")
    return (f"No encontré ninguna de estas versiones de Python: {', '.join(versiones)}. "
            f"Instala Python {v} (python.org, o el gestor de paquetes de tu sistema: "
            f"apt install python{v} python{v}-venv / brew install python@{v}) y vuelve a pulsar el botón.")


def carpeta_instalador_vs():
    # Donde vive vswhere.exe. Hay que ponerla en el PATH antes de vcvars64.bat: si no, vcvars
    # escribe "vswhere.exe no se reconoce" y deja el entorno del compilador a medias.
    return Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft Visual Studio" / "Installer"


def buscar_build_tools():
    """Ruta de vcvars64.bat de unas Visual Studio Build Tools con el compilador de C++, o None.
    PyBullet no publica ruedas (paquetes ya compilados) para Windows en ninguna versión: pip
    siempre lo compila desde el código fuente, y para eso hace falta MSVC."""
    if not ES_WINDOWS:
        return None
    vswhere = carpeta_instalador_vs() / "vswhere.exe"
    if not vswhere.is_file():
        return None
    codigo, salida = correr_corto([vswhere, "-products", "*", "-latest", "-requires",
                                   "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                                   "-property", "installationPath"], timeout=30)
    ruta = salida.strip().splitlines()[-1].strip() if codigo == 0 and salida.strip() else ""
    vcvars = Path(ruta) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat" if ruta else None
    return vcvars if vcvars and vcvars.is_file() else None


MENSAJE_BUILD_TOOLS = (
    "PyBullet se compila en Windows (no hay versión ya compilada) y para eso faltan las "
    "\"Visual Studio Build Tools\" con \"Desarrollo para el escritorio con C++\". Instálalas con este comando "
    "en una consola (unos 2-3 GB, una sola vez): "
    "winget install Microsoft.VisualStudio.2022.BuildTools --override \"--quiet --wait --add "
    "Microsoft.VisualStudio.Workload.VCTools --includeRecommended\" "
    "(o desde https://visualstudio.microsoft.com/es/visual-cpp-build-tools/ ) y vuelve a pulsar el botón. "
    "Mientras tanto, lo que no necesita instalación (previews, videos, Docker) funciona igual."
)


def necesita_compilar(paquetes):
    return ES_WINDOWS and any(nombre_distribucion(p).lower() == "pybullet" for p in paquetes)


def instalar_paquetes(trabajo, python, paquetes):
    comando = [str(python), "-m", "pip", "install", "--disable-pip-version-check",
               # --progress-bar off: la barra de pip usa \r y en el log saldría como basura.
               "--progress-bar", "off", *paquetes]
    if not necesita_compilar(paquetes):
        trabajo.poner("instalando", f"Instalando {len(paquetes)} paquete(s) con pip (puede tardar unos minutos la primera vez)…")
        codigo = correr_con_log(trabajo, comando)
    else:
        # Se comprueba ANTES de llamar a pip: sin compilador, pip fallaría tras varios minutos
        # con un error poco claro ("Unable to find a compatible Visual Studio installation").
        vcvars = buscar_build_tools()
        if not vcvars:
            raise ErrorClaro(MENSAJE_BUILD_TOOLS)
        trabajo.poner("instalando", "Instalando paquetes y COMPILANDO PyBullet: la primera vez tarda unos 10-15 minutos "
                                    "(las siguientes es inmediato, pip guarda lo compilado en su caché)…")
        # pip tiene que correr DENTRO del entorno del compilador (vcvars64.bat): solo poner el
        # compilador en el PATH no basta. DISTUTILS_USE_SDK=1 le dice a setuptools que use ese
        # entorno ya preparado en vez de buscar Visual Studio por su cuenta (lo que fallaba).
        # Se escribe un .bat junto al entorno porque las rutas con espacios dentro de `cmd /c "..."`
        # se rompen con facilidad.
        bat = Path(python).resolve().parent.parent / "instalar_con_msvc.bat"
        linea = subprocess.list2cmdline(comando)
        bat.write_text("@echo off\r\n"
                       f"set \"PATH={carpeta_instalador_vs()};%PATH%\"\r\n"
                       f"call \"{vcvars}\" >nul || exit /b 1\r\n"
                       "set DISTUTILS_USE_SDK=1\r\n"
                       f"{linea}\r\n", encoding="utf-8")
        trabajo.escribir(f"Compilador: {vcvars}")
        codigo = correr_con_log(trabajo, ["cmd", "/c", str(bat)])
    if codigo != 0:
        raise ErrorClaro("pip no pudo instalar los paquetes (mira las últimas líneas del registro). "
                         "Suele ser falta de internet o que no hay versión del paquete para ese Python.")


def entorno_de_subcarpeta(trabajo, practica, accion, necesarios):
    """Algunas prácticas con varios puntos (el tema 8) tienen un entorno por punto, en la
    carpeta de trabajo de la acción (`<carpeta>/<cwd>/entorno`). Si ese entorno ya existe y
    trae lo que la acción necesita, se usa tal cual: así no se crea otro entorno de cientos
    de MB solo porque los paquetes estén repartidos. Si no sirve, devuelve None."""
    if Config.entornos or not accion:
        return None  # con --entornos todo va a la carpeta indicada
    cwd = Path(accion.get("cwd") or "")
    if not cwd.is_dir() or cwd.resolve() == (Config.raiz / practica["carpeta"]).resolve():
        return None
    env = cwd / "entorno"
    py = python_del_entorno(env)
    if not py.exists():
        return None
    if accion.get("paquetes") or not accion.get("script"):
        est = revisar_entorno(py, necesarios)
        if est is None or est["faltan"]:
            return None
    else:
        # Sin "paquetes" propios de la acción: en vez de exigir TODOS los de la práctica (el
        # entorno del punto 1 no tiene TensorFlow y no lo necesita), se comprueba que ese
        # entorno encuentre cada módulo que el script importa arriba del todo.
        modulos = importaciones_del_script(accion["script"])
        if modulos is None:
            return None
        codigo, salida = correr_corto([py, "-c", CHEQUEO_MODULOS, json.dumps(modulos)], timeout=60, cwd=str(cwd))
        if codigo != 0 or salida.strip().splitlines()[-1:] != ["[]"]:
            return None
    trabajo.escribir(f"Uso el entorno de la subcarpeta: {env}")
    return str(py)


# find_spec localiza un módulo sin importarlo (rápido incluso para TensorFlow). Corre con el
# cwd de la acción, así también encuentra los módulos propios que están junto al script.
CHEQUEO_MODULOS = (
    "import sys, json, importlib.util\n"
    "faltan = []\n"
    "for m in json.loads(sys.argv[1]):\n"
    "    try:\n"
    "        if importlib.util.find_spec(m) is None: faltan.append(m)\n"
    "    except Exception:\n"
    "        faltan.append(m)\n"
    "print(json.dumps(faltan))\n"
)


def importaciones_del_script(script):
    """Módulos que el script importa en el nivel superior (no los de dentro de un try: esos
    suelen ser opcionales, como `serial` en el patrón "sin ESP32"). None si no se puede leer."""
    import ast
    try:
        arbol = ast.parse(Path(script).read_text(encoding="utf-8-sig"))
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
        return None
    mods = set()
    for nodo in arbol.body:
        if isinstance(nodo, ast.Import):
            mods.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            mods.add(nodo.module.split(".")[0])
    return sorted(mods)


def preparar_entorno(trabajo, practica, accion=None):
    """Devuelve el python con el que correr la acción, creando o completando el entorno de la
    práctica si hace falta. Lanza ErrorClaro con instrucciones si no se puede.

    Paquetes que se exigen: los de la acción si declara "paquetes" (añadido de este lanzador,
    opcional), si no, todos los de "python.paquetes" de la práctica."""
    conf = practica.get("python")
    if not conf or (not conf["paquetes"] and not conf["versiones"]):
        trabajo.escribir("La práctica no pide paquetes: uso el mismo Python del lanzador.")
        return sys.executable
    paquetes, versiones = conf["paquetes"], conf["versiones"]
    necesarios = (accion or {}).get("paquetes") or paquetes
    carpeta = practica["carpeta"]
    env = ruta_entorno(carpeta)
    py = python_del_entorno(env)

    with cerrojo_entorno(carpeta):
        sub = entorno_de_subcarpeta(trabajo, practica, accion, necesarios)
        if sub:
            return sub
        if env.exists():
            if not py.exists():
                raise ErrorClaro(f"La carpeta {env} existe pero no es un entorno de Python válido. "
                                 "Bórrala y vuelve a pulsar el botón: se crea sola.")
            trabajo.escribir(f"Reviso el entorno existente: {env}")
            est = revisar_entorno(py, necesarios)
            if est is None:
                raise ErrorClaro(f"El entorno {env} no arranca (quizá se desinstaló el Python con que se creó). "
                                 "Bórralo y vuelve a pulsar el botón: se crea solo.")
            # Si es de otra versión que la pedida pero tiene todo, se usa igual: ya funciona.
            if est["faltan"]:
                trabajo.escribir(f"Al entorno (Python {est['version']}) le faltan: {', '.join(est['faltan'])}")
                faltan = {n.lower() for n in est["faltan"]}
                instalar_paquetes(trabajo, py, [p for p in necesarios if nombre_distribucion(p).lower() in faltan])
            ESTADO_ENTORNOS[carpeta] = {"estado": "listo", "detalle": f"Python {est['version']}"}
            trabajo.escribir(f"Entorno listo (Python {est['version']}).")
            return str(py)

        base, version = None, None
        for v in versiones or ["%d.%d" % sys.version_info[:2]]:
            base = buscar_python(v)
            if base:
                version = v
                break
        if not base:
            ESTADO_ENTORNOS[carpeta] = {"estado": "sin-python", "detalle": ", ".join(versiones)}
            raise ErrorClaro(mensaje_instalar_python(versiones))

        trabajo.poner("instalando", f"Creando el entorno con Python {version} (solo la primera vez)…")
        env.parent.mkdir(parents=True, exist_ok=True)
        if correr_con_log(trabajo, [base, "-m", "venv", str(env)]) != 0 or not py.exists():
            raise ErrorClaro(f"No se pudo crear el entorno en {env} con Python {version}. "
                             "En Linux puede faltar el paquete python3-venv.")
        # Convención del repo: el entorno se excluye solo de git con un .gitignore que dice "*".
        gi = env / ".gitignore"
        if not gi.exists():
            gi.write_text("*\n", encoding="utf-8")
        if paquetes:
            instalar_paquetes(trabajo, py, paquetes)
        est = revisar_entorno(py, paquetes)
        if est is None or est["faltan"]:
            raise ErrorClaro("El entorno se creó pero siguen faltando paquetes: "
                             + ", ".join((est or {}).get("faltan", paquetes)))
        ESTADO_ENTORNOS[carpeta] = {"estado": "listo", "detalle": f"Python {est['version']}"}
        trabajo.escribir(f"Entorno creado y listo (Python {est['version']}).")
        return str(py)


def revisar_entornos_en_segundo_plano():
    """Al arrancar, mira cada entorno para que la tarjeta diga "listo" o "se creará la primera
    vez". En un hilo aparte: con 12 prácticas tarda unos segundos y la página no debe esperar."""
    for d in carpetas_con_manifiesto():
        try:
            p = leer_manifiesto(d)
            conf = p.get("python")
            if not conf or not conf["paquetes"]:
                continue
            env = ruta_entorno(p["carpeta"])
            py = python_del_entorno(env)
            subs = [Path(a["cwd"]) / "entorno" for a in p["acciones"]
                    if a["tipo"] == "python" and a.get("cwd") and Path(a["cwd"]).resolve() != d.resolve()]
            if not env.exists() and not Config.entornos and any(python_del_entorno(x).exists() for x in subs):
                ESTADO_ENTORNOS[p["carpeta"]] = {"estado": "subcarpetas", "detalle": ""}
                continue
            if not env.exists():
                v = next((v for v in conf["versiones"] if buscar_python(v)), None)
                ESTADO_ENTORNOS[p["carpeta"]] = (
                    {"estado": "nuevo", "detalle": f"Python {v}"} if v or not conf["versiones"]
                    else {"estado": "sin-python", "detalle": ", ".join(conf["versiones"])})
                continue
            est = revisar_entorno(py, conf["paquetes"]) if py.exists() else None
            if est is None:
                ESTADO_ENTORNOS[p["carpeta"]] = {"estado": "roto", "detalle": str(env)}
            elif est["faltan"]:
                ESTADO_ENTORNOS[p["carpeta"]] = {"estado": "faltan", "detalle": ", ".join(est["faltan"])}
            else:
                ESTADO_ENTORNOS[p["carpeta"]] = {"estado": "listo", "detalle": f"Python {est['version']}"}
        except Exception as e:  # un fallo aquí solo deja la tarjeta sin aviso
            ESTADO_ENTORNOS[d.name] = {"estado": "desconocido", "detalle": str(e)}


# --------------------------------------------------------------------------------------
# Lanzar en una consola nueva
# --------------------------------------------------------------------------------------

def lanzar_en_consola(trabajo, cmd, cwd, titulo, pausa="error"):
    """Abre una consola nueva que corre `cmd` a través de este mismo archivo en modo --hijo:
    el modo hijo pone el título, explica cómo cerrar y, si el programa falla, deja la ventana
    abierta para leer el error (si no, la consola se cerraría sola y el error se perdería)."""
    envoltura = [sys.executable, str(ESTE_ARCHIVO), "--hijo", "--titulo", titulo, "--pausa", pausa, "--", *cmd]
    if ES_WINDOWS:
        p = subprocess.Popen(envoltura, cwd=cwd, creationflags=CONSOLA_NUEVA, env=entorno_hijo())
    elif ES_MAC:
        # Terminal.app no devuelve el PID del programa: se lanza y no se le puede seguir.
        import shlex
        linea = f"cd {shlex.quote(str(cwd))} && " + " ".join(shlex.quote(str(c)) for c in envoltura)
        script = f'tell application "Terminal" to do script "{linea.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
        subprocess.Popen(["osascript", "-e", script])
        trabajo.seguimiento = False
        trabajo.poner("lanzada", "Abierta en una ventana de Terminal.")
        return None
    else:
        terminal = None
        for t in ("x-terminal-emulator", "konsole", "xfce4-terminal", "xterm", "gnome-terminal"):
            if shutil.which(t):
                terminal = t
                break
        if terminal == "gnome-terminal":
            # gnome-terminal delega en un servidor y vuelve enseguida: no hay PID que seguir.
            subprocess.Popen([terminal, "--", *envoltura], cwd=cwd)
            trabajo.seguimiento = False
            trabajo.poner("lanzada", "Abierta en una ventana de terminal.")
            return None
        if terminal:
            p = subprocess.Popen([terminal, "-e", *envoltura], cwd=cwd, env=entorno_hijo())
        else:
            # Sin emulador de terminal (p. ej. un servidor): la salida va al registro de la página.
            trabajo.escribir("No encontré una terminal gráfica: la salida se muestra aquí.")
            p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                 encoding="utf-8", errors="replace", env=entorno_hijo())
            threading.Thread(target=lambda: [trabajo.escribir(l) for l in p.stdout], daemon=True).start()
    trabajo.proceso = p
    trabajo.pid = p.pid
    trabajo.poner("lanzada", f"En marcha en su propia ventana (PID {p.pid}); al cerrarla queda como terminada.")
    return p


def vigilar(trabajo, p, al_terminar=None):
    """Hilo que espera a que la consola se cierre y deja el trabajo como terminado."""
    codigo = p.wait()
    trabajo.codigo = codigo
    if trabajo.estado == "detenida":
        return
    if codigo == 0:
        trabajo.poner("terminada", "Terminó bien.")
        if al_terminar:
            al_terminar()
    else:
        trabajo.poner("error", f"Terminó con error (código {codigo}). La ventana muestra el detalle.")


def abrir_con_sistema(ruta):
    if ES_WINDOWS:
        os.startfile(str(ruta))  # el programa asociado: visor de fotos, reproductor, lector de PDF
    elif ES_MAC:
        subprocess.Popen(["open", str(ruta)])
    else:
        subprocess.Popen(["xdg-open", str(ruta)])


# --------------------------------------------------------------------------------------
# Docker
# --------------------------------------------------------------------------------------

def comprobar_docker():
    """(ok, mensaje). `docker info` falla si Docker Desktop no está abierto aunque esté instalado."""
    if not shutil.which("docker"):
        return False, ("Docker no está instalado. Instala Docker Desktop desde "
                       "https://www.docker.com/products/docker-desktop/ , ábrelo y vuelve a intentar.")
    codigo, salida = correr_corto(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=30)
    if codigo != 0 or not salida.strip() or "error" in salida.lower():
        return False, ("Docker está instalado pero no responde: abre Docker Desktop, espera a que diga "
                       "\"Engine running\" y vuelve a pulsar el botón.")
    return True, f"Docker responde (motor {salida.strip().splitlines()[-1]})."


# --------------------------------------------------------------------------------------
# Ejecutar una acción (en un hilo: la petición HTTP vuelve enseguida y la página sondea)
# --------------------------------------------------------------------------------------

def iniciar_accion(carpeta, accion_id, detener=False):
    practica = buscar_practica(carpeta)
    accion = buscar_accion(practica, accion_id)
    clave = (carpeta, accion_id)
    with TRABAJOS_LOCK:
        previo = TRABAJOS.get(clave)
        if not detener and previo and previo.activo and previo.seguimiento:
            raise ErrorClaro(f"\"{accion['nombre']}\" ya está en marcha. Ciérrala (o pulsa Detener) antes de lanzarla otra vez.")
        if detener and accion["tipo"] == "python":
            if not previo or not previo.activo or not previo.pid:
                raise ErrorClaro("No hay nada en marcha que detener.")
            matar_arbol(previo.pid)
            previo.poner("detenida", "Detenida desde el lanzador.")
            return previo
        nombre = accion["nombre"] + (" (detener)" if detener else "")
        t = Trabajo(carpeta, accion_id + (":detener" if detener else ""), nombre)
        TRABAJOS[(carpeta, t.accion)] = t
    threading.Thread(target=ejecutar, args=(t, practica, accion, detener), daemon=True).start()
    return t


def ejecutar(t, practica, accion, detener):
    try:
        tipo = accion["tipo"]
        titulo = f"{practica['id']} · {accion['nombre']}"
        if tipo == "python":
            python = preparar_entorno(t, practica, accion)
            if accion.get("modulo"):
                cmd = [python, "-m", accion["modulo"], *accion["args"]]
            else:
                cmd = [python, accion["script"], *accion["args"]]
            t.escribir("Lanzo: " + accion.get("muestra", ""))
            # La ventana queda abierta al terminar ("Pulsa Enter"): varios scripts solo imprimen
            # un resultado y terminan (el gemelo del tema 10), y si se cerrara sola no se vería.
            p = lanzar_en_consola(t, cmd, accion["cwd"], titulo, pausa="siempre")
            if p:
                vigilar(t, p)
        elif tipo == "archivo":
            abrir_con_sistema(accion["ruta"])
            t.poner("terminada", "Abierto con el programa del sistema.")
        elif tipo == "docker":
            ok, msg = comprobar_docker()
            t.escribir(msg)
            if not ok:
                raise ErrorClaro(msg)
            carpeta = str(Config.raiz / practica["carpeta"])
            if detener:
                t.poner("lanzada", "Deteniendo los contenedores…")
                codigo = correr_con_log(t, ["docker", "compose", "-f", accion["compose"], *accion["detener"]], cwd=carpeta)
                t.codigo = codigo
                if codigo != 0:
                    raise ErrorClaro("docker compose no pudo detener el laboratorio (mira el registro).")
                t.poner("terminada", "Contenedores detenidos.")
                return
            cmd = ["docker", "compose", "-f", accion["compose"], *accion["args"]]
            t.escribir("Lanzo: " + " ".join(cmd))
            # Con `up -d` compose vuelve enseguida y la consola puede cerrarse sola (luego se abre
            # "abrir"); sin -d (p. ej. `run --rm simulacion`) lo que importa es lo que imprime,
            # así que la ventana queda abierta al terminar para poder leerlo.
            separado = any(x in ("-d", "--detach") for x in accion["args"])
            p = lanzar_en_consola(t, cmd, carpeta, titulo, pausa="error" if separado else "siempre")
            abrir = accion.get("abrir")

            def al_terminar():
                if abrir:
                    webbrowser.open(abrir)
                    t.poner("terminada", f"Laboratorio levantado; abrí {abrir}")
            if p:
                vigilar(t, p, al_terminar)
        else:
            # html, url e info los abre la propia página (window.open); aquí no hay nada que hacer.
            t.poner("terminada", "Abierto en el navegador.")
    except ErrorClaro as e:
        t.escribir(str(e))
        t.poner("error", str(e))
    except Exception as e:  # cualquier otra cosa: mensaje corto, no una traza
        t.escribir(f"{type(e).__name__}: {e}")
        t.poner("error", f"Algo falló al lanzar la acción: {e}")


def matar_arbol(pid):
    """Cierra la consola y todo lo que corre dentro (el script y sus hijos)."""
    if ES_WINDOWS:
        correr_corto(["taskkill", "/PID", str(pid), "/T", "/F"], timeout=15)
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass


# --------------------------------------------------------------------------------------
# Modo hijo: lo que corre dentro de la consola nueva
# --------------------------------------------------------------------------------------

def modo_hijo(titulo, pausa, cmd):
    if ES_WINDOWS:
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(titulo)
        except Exception:
            pass
    linea = "=" * min(78, max(30, len(titulo) + 4))
    print(linea)
    print(f"  {titulo}")
    print(linea)
    print("Lanzado desde el lanzador de Sensores-Teoria (PROBAR.bat).")
    print("Para cerrar: Ctrl+C aquí, o cierra la ventana del programa.\n")
    try:
        p = subprocess.Popen(cmd)
    except OSError as e:
        print(f"No se pudo ejecutar: {e}")
        esperar_enter()
        return 1
    interrumpido = False
    while True:
        try:
            codigo = p.wait()
            break
        except KeyboardInterrupt:
            # El Ctrl+C también le llega al programa; se le da un momento para cerrar limpio.
            interrumpido = True
            try:
                codigo = p.wait(timeout=5)
                break
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                p.kill()
    print(f"\n--- El programa terminó (código {codigo}{', 0 = sin errores' if codigo == 0 else ''}) ---")
    if (pausa == "siempre" and not interrumpido) or (pausa == "error" and codigo != 0 and not interrumpido):
        if codigo != 0:
            print("Algo salió mal: lee el mensaje de arriba. Esta ventana queda abierta para eso.")
        esperar_enter()
    return codigo


def esperar_enter():
    try:
        input("Pulsa Enter para cerrar esta ventana…")
    except (EOFError, KeyboardInterrupt):
        pass


# --------------------------------------------------------------------------------------
# Servidor HTTP
# --------------------------------------------------------------------------------------

# Tipos MIME fijos: en Windows mimetypes lee el registro y a veces da .js como text/plain,
# y entonces el navegador se niega a ejecutar los módulos de un preview.html.
MIME = {".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8", ".js": "text/javascript",
        ".mjs": "text/javascript", ".css": "text/css", ".json": "application/json", ".md": "text/plain; charset=utf-8",
        ".txt": "text/plain; charset=utf-8", ".py": "text/plain; charset=utf-8", ".png": "image/png",
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".svg": "image/svg+xml",
        ".webp": "image/webp", ".mp4": "video/mp4", ".webm": "video/webm", ".pdf": "application/pdf",
        ".wasm": "application/wasm", ".glb": "model/gltf-binary", ".urdf": "text/plain; charset=utf-8",
        ".yml": "text/plain; charset=utf-8", ".yaml": "text/plain; charset=utf-8", ".ino": "text/plain; charset=utf-8",
        ".cpp": "text/plain; charset=utf-8", ".h": "text/plain; charset=utf-8"}


def archivo_prohibido(rel):
    """Lo que el servidor de archivos nunca entrega aunque se lo pidan: secretos (.env), los
    entornos, git, y los PDF/Word privados que el .gitignore ya excluye del repo."""
    partes = [x.lower() for x in Path(rel).parts]
    if any(x in ("entorno", ".git", "respaldos", "__pycache__", ".claude") for x in partes):
        return True
    nombre = partes[-1] if partes else ""
    return (nombre.startswith(".env") or nombre.endswith(".db") or "umng.pdf" in nombre
            or nombre.startswith("enlace readme"))


class Manejador(BaseHTTPRequestHandler):
    server_version = "LanzadorSensores/1.0"

    def log_message(self, formato, *args):
        pass  # sin una línea por petición en la consola del lanzador

    # --- utilidades -------------------------------------------------------------------
    def responder(self, codigo, cuerpo, tipo="application/json; charset=utf-8", extra=None):
        if isinstance(cuerpo, (dict, list)):
            cuerpo = json.dumps(cuerpo, ensure_ascii=False)
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(cuerpo)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def host_valido(self):
        # Defensa contra "DNS rebinding": una web externa no puede hablarle a este servidor
        # aunque consiga que su dominio apunte a 127.0.0.1, porque el Host no coincidiría.
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        return host in ("127.0.0.1", "localhost")

    # --- GET --------------------------------------------------------------------------
    def do_GET(self):
        if not self.host_valido():
            return self.responder(403, {"error": "Host no permitido"})
        ruta = urllib.parse.urlparse(self.path)
        camino = urllib.parse.unquote(ruta.path)
        if camino in ("/", "/index.html"):
            return self.responder(200, HUB_HTML.replace("__TOKEN__", Config.token), "text/html; charset=utf-8")
        if camino == "/api/ping":
            return self.responder(200, {"firma": FIRMA})
        if camino == "/api/practicas":
            return self.responder(200, {
                "practicas": cargar_practicas(), "entornos": ESTADO_ENTORNOS,
                "python": "%d.%d.%d" % sys.version_info[:3], "pythons": PYTHONS_VISTOS,
                "build_tools": ESTADO_SISTEMA.get("build_tools"),
                "raiz": str(Config.raiz), "sistema": "windows" if ES_WINDOWS else ("mac" if ES_MAC else "linux"),
            })
        if camino == "/api/trabajos":
            with TRABAJOS_LOCK:
                lista = [t.a_dict() for t in TRABAJOS.values()]
            return self.responder(200, lista)
        if camino.startswith("/readme/"):
            carpeta = camino[len("/readme/"):].strip("/")
            d = ruta_dentro(Config.raiz, carpeta)
            if d is None or not (d / "README.md").is_file():
                return self.responder(404, "No hay README en esa carpeta.", "text/plain; charset=utf-8")
            pagina = (README_HTML.replace("__CARPETA__", json.dumps(carpeta))
                      .replace("__BASE__", "/repo/" + urllib.parse.quote(carpeta) + "/")
                      .replace("__GITHUB__", GITHUB + urllib.parse.quote(carpeta) + "/README.md"))
            return self.responder(200, pagina, "text/html; charset=utf-8")
        if camino.startswith("/repo/"):
            return self.servir_archivo(camino[len("/repo/"):])
        return self.responder(404, {"error": "No existe"})

    def servir_archivo(self, rel):
        """Sirve los archivos del repo (previews HTML, imágenes, README) para que se abran por
        http://127.0.0.1 en vez de file://: Web Serial, la cámara y fetch() lo necesitan."""
        if archivo_prohibido(rel):
            return self.responder(403, "Ese archivo no se sirve (privado o del entorno).", "text/plain; charset=utf-8")
        f = ruta_dentro(Config.raiz, rel)
        if f is not None and f.is_dir():
            f = f / "index.html"
        if f is None or not f.is_file():
            return self.responder(404, "No existe.", "text/plain; charset=utf-8")
        tipo = MIME.get(f.suffix.lower()) or mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        try:
            datos = f.read_bytes()
        except OSError:
            return self.responder(500, "No se pudo leer.", "text/plain; charset=utf-8")
        self.responder(200, datos, tipo)

    # --- POST -------------------------------------------------------------------------
    def do_POST(self):
        if not self.host_valido():
            return self.responder(403, {"error": "Host no permitido"})
        # El token solo lo conoce la página servida por este proceso: sin él, nada se ejecuta.
        if not secrets.compare_digest(self.headers.get("X-Token", ""), Config.token):
            return self.responder(403, {"error": "Token inválido: recarga la página del lanzador."})
        try:
            largo = int(self.headers.get("Content-Length") or 0)
            datos = json.loads(self.rfile.read(min(largo, 65536)) or b"{}")
        except (ValueError, OSError):
            return self.responder(400, {"error": "Petición mal formada."})
        camino = urllib.parse.urlparse(self.path).path
        try:
            if camino in ("/api/accion", "/api/detener"):
                t = iniciar_accion(str(datos.get("carpeta", "")), str(datos.get("accion", "")),
                                   detener=camino == "/api/detener")
                return self.responder(200, t.a_dict())
            if camino == "/api/docker":
                ok, msg = comprobar_docker()
                return self.responder(200, {"ok": ok, "mensaje": msg})
            if camino == "/api/carpeta":
                practica = buscar_practica(str(datos.get("carpeta", "")))
                abrir_con_sistema(Config.raiz / practica["carpeta"])
                return self.responder(200, {"ok": True})
            if camino == "/api/salir":
                self.responder(200, {"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return None
        except ErrorClaro as e:
            return self.responder(400, {"error": str(e)})
        except Exception as e:
            return self.responder(500, {"error": f"Error inesperado: {e}"})
        return self.responder(404, {"error": "No existe"})


PYTHONS_VISTOS = []
ESTADO_SISTEMA = {}  # build_tools: True/False en Windows (None mientras se busca o fuera de Windows)


def hub_ya_abierto(puerto):
    """Si ya hay un lanzador en ese puerto (doble clic dos veces), se reutiliza."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/ping", timeout=1.5) as r:
            return json.loads(r.read().decode("utf-8")).get("firma") == FIRMA
    except Exception:
        return False


def crear_servidor(preferido):
    for puerto in [preferido, *range(preferido + 1, preferido + 30), 0]:
        try:
            return ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
        except OSError:
            continue
    raise SystemExit("No encontré ningún puerto libre para el lanzador.")


def comprobar_manifiestos():
    """--comprobar: lista cada probar.json y sus errores, sin levantar nada."""
    practicas = cargar_practicas()
    if not practicas:
        print(f"No hay ningún */probar.json en {Config.raiz}")
        return 1
    malos = 0
    for p in practicas:
        errores = list(p["errores"]) + [f"acción {a['id']}: {a['error']}" for a in p["acciones"] if a["error"]]
        marca = "OK " if not errores else "MAL"
        print(f"[{marca}] {p['carpeta']}: {p['titulo']} ({len(p['acciones'])} acciones)")
        for e in errores:
            print(f"       - {e}")
        malos += bool(errores)
    sin = [d.name for d in sorted(Config.raiz.iterdir(), key=lambda d: clave_orden(d.name))
           if d.is_dir() and not d.name.startswith(".") and (re.match(r"\d+-", d.name) or d.name == "proyecto-final")
           and not (d / "probar.json").is_file()]
    if sin:
        print("Sin probar.json: " + ", ".join(sin))
    return 1 if malos else 0


def main():
    ap = argparse.ArgumentParser(description="Lanzador de las prácticas de Sensores-Teoria.")
    ap.add_argument("--puerto", type=int, default=8099)
    ap.add_argument("--raiz")
    ap.add_argument("--entornos")
    ap.add_argument("--no-navegador", action="store_true")
    ap.add_argument("--comprobar", action="store_true")
    ap.add_argument("--hijo", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--titulo", default="", help=argparse.SUPPRESS)
    ap.add_argument("--pausa", default="error", help=argparse.SUPPRESS)
    ap.add_argument("resto", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    args = ap.parse_args()

    # Salida redirigida (a un archivo o a otra terminal): UTF-8 para que no salgan '?' en las
    # tildes. En una consola real Python ya escribe bien con la API de Windows.
    for flujo in (sys.stdout, sys.stderr):
        if flujo and not flujo.isatty() and hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    if args.hijo:
        cmd = args.resto[1:] if args.resto[:1] == ["--"] else args.resto
        sys.exit(modo_hijo(args.titulo, args.pausa, cmd))

    if args.raiz:
        Config.raiz = Path(args.raiz).resolve()
    if args.entornos:
        Config.entornos = Path(args.entornos).resolve()
    if args.comprobar:
        sys.exit(comprobar_manifiestos())

    if hub_ya_abierto(args.puerto):
        url = f"http://127.0.0.1:{args.puerto}/"
        print(f"El lanzador ya estaba abierto en {url} (lo abro en el navegador).")
        if not args.no_navegador:
            webbrowser.open(url)
        return

    servidor = crear_servidor(args.puerto)
    Config.puerto = servidor.server_address[1]
    url = f"http://127.0.0.1:{Config.puerto}/"
    threading.Thread(target=revisar_entornos_en_segundo_plano, daemon=True).start()
    threading.Thread(target=lambda: PYTHONS_VISTOS.extend(versiones_instaladas()), daemon=True).start()
    if ES_WINDOWS:
        threading.Thread(target=lambda: ESTADO_SISTEMA.update(build_tools=buscar_build_tools() is not None),
                         daemon=True).start()
    print("Lanzador de Sensores-Teoria")
    print(f"  Página: {url}")
    print(f"  Prácticas con probar.json: {len(carpetas_con_manifiesto())} (en {Config.raiz})")
    print("  Deja esta ventana abierta mientras pruebas; ciérrala (o Ctrl+C) para apagar el lanzador.")
    print("  Lo que ya se lanzó en otras ventanas sigue abierto aunque cierres esta.")
    if not args.no_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        print("Lanzador cerrado.")


# --------------------------------------------------------------------------------------
# Página del hub (HTML + CSS + JS embebidos: así el lanzador es un solo archivo)
# --------------------------------------------------------------------------------------

HUB_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Probar las prácticas</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0d1013; --panel: #15191d; --panel-border: #262b31; --hondo: #0a0d10;
    --text: #e7e9ec; --text-muted: #8b929b; --accent: #4f8fce; --verde-ok: #4caf7d;
    --rojo: #d9534f; --amarillo: #e8b930; --modo: #9b7fd1;
    --mono: "IBM Plex Mono", ui-monospace, Consolas, monospace;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: var(--bg); color: var(--text); font-family: "Space Grotesk", system-ui, "Segoe UI", sans-serif; }
  body { padding: 1.2rem 1.4rem 3rem; min-height: 100vh; }
  @media (max-width: 720px) { body { padding: 0.9rem 16px 2rem; } }
  a { color: var(--accent); }
  .cabecera { max-width: 1400px; margin: 0 auto 1rem; }
  .fila { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; flex-wrap: wrap; }
  h1 { font-size: 1.35rem; font-weight: 600; margin: 0 0 0.3rem; }
  .sub { color: var(--text-muted); font-size: 0.86rem; margin: 0; max-width: 900px; line-height: 1.5; }
  .sub b { color: var(--text); font-weight: 500; }
  .chips-sis { font-family: var(--mono); font-size: 0.68rem; color: var(--text-muted); display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.6rem; }
  .chip { border: 1px solid var(--panel-border); border-radius: 999px; padding: 0.15rem 0.55rem; white-space: nowrap; }
  .chip.ok { border-color: #2c5a43; color: var(--verde-ok); }
  .chip.mal { border-color: #5a2a29; color: #e58a87; }
  .herramientas { max-width: 1400px; margin: 0 auto 1rem; display: flex; gap: 0.6rem; flex-wrap: wrap; align-items: center; }
  input[type=search] { flex: 1 1 260px; min-width: 0; background: var(--panel); color: var(--text); border: 1px solid var(--panel-border);
    border-radius: 6px; padding: 0.55rem 0.75rem; font-family: var(--mono); font-size: 0.8rem; }
  input[type=search]:focus { outline: none; border-color: var(--accent); }
  .filtros { display: flex; gap: 0.35rem; flex-wrap: wrap; }
  button { font-family: var(--mono); }
  .filtro { background: transparent; color: var(--text-muted); border: 1px solid var(--panel-border); padding: 0.42rem 0.7rem; border-radius: 6px; font-size: 0.7rem; cursor: pointer; }
  .filtro.activo { border-color: var(--accent); color: var(--accent); }
  .rejilla { max-width: 1400px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 620px), 1fr)); gap: 1rem; align-items: start; }
  .tarjeta { background: var(--panel); border: 1px solid var(--panel-border); border-radius: 8px; padding: 1rem; min-width: 0; }
  .tarjeta.rota { border-color: #5a2a29; }
  .tarjeta.final { border-top: 3px solid var(--amarillo); }
  .tit { display: flex; gap: 0.7rem; align-items: baseline; }
  .num { font-family: var(--mono); font-size: 0.75rem; color: var(--bg); background: var(--accent); border-radius: 4px; padding: 0.1rem 0.45rem; font-weight: 600; flex: none; }
  .final .num { background: var(--amarillo); }
  .tarjeta h2 { font-size: 1.02rem; font-weight: 600; margin: 0; line-height: 1.3; }
  .carpeta { font-family: var(--mono); font-size: 0.66rem; color: var(--text-muted); margin: 0.25rem 0 0.6rem; word-break: break-all; }
  .resumen { font-size: 0.86rem; line-height: 1.5; margin: 0 0 0.7rem; color: #cfd3d8; }
  .seccion { font-family: var(--mono); font-size: 0.64rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted); margin: 0.8rem 0 0.4rem; }
  ul.pide { margin: 0; padding-left: 1.1rem; font-size: 0.8rem; line-height: 1.5; color: #cfd3d8; }
  .notas { background: var(--hondo); border: 1px solid var(--panel-border); border-left: 3px solid var(--amarillo); border-radius: 6px; padding: 0.5rem 0.7rem; font-size: 0.78rem; line-height: 1.5; color: #cfd3d8; margin-top: 0.7rem; }
  .notas p { margin: 0.15rem 0; }
  .errores { background: #1d1314; border: 1px solid #5a2a29; border-radius: 6px; padding: 0.5rem 0.7rem; font-family: var(--mono); font-size: 0.72rem; color: #e58a87; margin: 0.5rem 0; }
  .entorno { font-family: var(--mono); font-size: 0.68rem; color: var(--text-muted); margin-top: 0.4rem; }
  .entorno.ok { color: var(--verde-ok); } .entorno.mal { color: #e58a87; }
  .accion { border: 1px solid var(--panel-border); border-radius: 6px; padding: 0.6rem 0.7rem; margin-bottom: 0.5rem; background: #12161a; }
  .accion-cab { display: flex; justify-content: space-between; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
  .accion-nombre { font-weight: 600; font-size: 0.88rem; }
  .tipo { font-family: var(--mono); font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.06em; border: 1px solid var(--panel-border); border-radius: 4px; padding: 0.05rem 0.35rem; color: var(--text-muted); margin-left: 0.4rem; vertical-align: middle; }
  .t-python { color: var(--verde-ok); border-color: #2c5a43; } .t-html { color: var(--accent); border-color: #2a4766; }
  .t-libre { color: #7fd1a8; border-color: #23412f; text-transform: none; letter-spacing: 0; }
  .t-docker { color: var(--modo); border-color: #4a3d66; } .t-archivo, .t-url { color: var(--amarillo); border-color: #5e4c18; }
  .botones { display: flex; gap: 0.35rem; }
  .btn { background: #1c2126; color: var(--text); border: 1px solid var(--panel-border); padding: 0.4rem 0.75rem; border-radius: 6px; font-size: 0.72rem; cursor: pointer; white-space: nowrap; }
  .btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
  .btn:disabled, .btn.primario:disabled, .btn.rojo:disabled { color: #4a5058; border-color: var(--panel-border); cursor: default; }
  .btn.primario { border-color: #2a4766; color: #9cc2ea; }
  .btn.rojo { border-color: #5a2a29; color: #e58a87; }
  .desc { font-size: 0.78rem; line-height: 1.5; color: #b9bec4; margin: 0.35rem 0 0; }
  .muestra { font-family: var(--mono); font-size: 0.66rem; color: var(--text-muted); margin-top: 0.3rem; word-break: break-all; }
  .cubre { font-family: var(--mono); font-size: 0.64rem; line-height: 1.5; color: #9cc2ea; margin-top: 0.4rem; }
  .cubre b { color: var(--text-muted); font-weight: 500; }
  .indice { max-width: 1400px; margin: -0.4rem auto 1rem; display: flex; gap: 0.3rem; flex-wrap: wrap; }
  .indice a { font-family: var(--mono); font-size: 0.68rem; color: var(--text-muted); text-decoration: none; border: 1px solid var(--panel-border); border-radius: 4px; padding: 0.15rem 0.45rem; }
  .indice a:hover { color: var(--accent); border-color: var(--accent); }
  .indice a.oculto { opacity: 0.3; }
  .estado { font-family: var(--mono); font-size: 0.7rem; margin-top: 0.4rem; display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
  .punto { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); flex: none; }
  .e-preparando .punto, .e-instalando .punto { background: var(--amarillo); animation: lat 1s infinite; }
  .e-lanzada .punto { background: var(--verde-ok); animation: lat 1.6s infinite; }
  .e-terminada .punto { background: var(--accent); } .e-error .punto { background: var(--rojo); } .e-detenida .punto { background: var(--text-muted); }
  .e-error { color: #e58a87; }
  @keyframes lat { 50% { opacity: 0.3; } }
  details.log summary { font-family: var(--mono); font-size: 0.66rem; color: var(--text-muted); cursor: pointer; margin-top: 0.3rem; }
  pre.log { background: var(--hondo); border: 1px solid var(--panel-border); border-radius: 6px; padding: 0.5rem; font-size: 0.66rem; max-height: 220px; overflow: auto; white-space: pre-wrap; word-break: break-all; margin: 0.3rem 0 0; color: #b9bec4; }
  .pie { display: flex; gap: 0.8rem; flex-wrap: wrap; margin-top: 0.8rem; font-family: var(--mono); font-size: 0.7rem; }
  .pie a, .pie button.enlace { color: var(--accent); background: none; border: none; padding: 0; cursor: pointer; font-size: 0.7rem; text-decoration: underline; }
  .vacio { max-width: 1400px; margin: 2rem auto; color: var(--text-muted); font-family: var(--mono); font-size: 0.8rem; text-align: center; }
  .aviso-global { max-width: 1400px; margin: 0 auto 1rem; padding: 0.6rem 0.8rem; border-radius: 6px; font-family: var(--mono); font-size: 0.74rem; display: none; }
  .aviso-global.mal { display: block; background: #1d1314; border: 1px solid #5a2a29; color: #e58a87; }
  .aviso-global.ok { display: block; background: #112019; border: 1px solid #2c5a43; color: var(--verde-ok); }
</style>
</head>
<body>
<header class="cabecera">
  <div class="fila">
    <div>
      <h1>Probar las prácticas · Sensores Teoría 2026-2</h1>
      <p class="sub">Una tarjeta por práctica: <b>qué pide la actividad</b> y <b>botones para probarla sin hardware</b>
        (sin ESP32 ni sensores). Los programas en Python se abren en <b>su propia ventana</b>; la primera vez el lanzador
        prepara solo su entorno e instala lo que necesitan (tarda unos minutos, se ve el progreso aquí). Deja abierta la
        consola del lanzador mientras pruebas.</p>
      <div class="chips-sis" id="sistema"></div>
    </div>
    <div class="botones"><button class="btn" id="btnDocker">Comprobar Docker</button><button class="btn rojo" id="btnSalir">Cerrar lanzador</button></div>
  </div>
</header>
<div class="aviso-global" id="aviso"></div>
<div class="herramientas">
  <input type="search" id="buscar" placeholder="Buscar: brazo, YOLO, voz, docker, webcam…" autocomplete="off">
  <div class="filtros" id="filtros">
    <button class="filtro activo" data-f="todas">Todas</button>
    <button class="filtro" data-f="navegador">Solo navegador</button>
    <button class="filtro" data-f="python">Python</button>
    <button class="filtro" data-f="docker">Docker</button>
  </div>
</div>
<nav class="indice" id="indice"></nav>
<main class="rejilla" id="rejilla"></main>
<div class="vacio" id="vacio" hidden></div>
<script>
const TOKEN = "__TOKEN__";
const WINGET = 'winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"';
const TIPO_TXT = { python: "python", html: "navegador", archivo: "archivo", docker: "docker", url: "web", info: "info" };
const ESTADO_TXT = { preparando: "preparando", instalando: "instalando", lanzada: "en marcha", terminada: "terminada", error: "error", detenida: "detenida" };
let DATOS = { practicas: [], entornos: {} };
let TRABAJOS = {};
let filtro = "todas";

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(ruta, cuerpo) {
  const r = await fetch(ruta, cuerpo === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json", "X-Token": TOKEN }, body: JSON.stringify(cuerpo) });
  let d = null;
  try { d = await r.json(); } catch (e) { /* respuesta no JSON */ }
  if (!r.ok) throw new Error((d && d.error) || `Error ${r.status}`);
  return d;
}

function aviso(texto, ok) {
  const el = document.getElementById("aviso");
  el.textContent = texto; el.className = "aviso-global " + (ok ? "ok" : "mal");
  clearTimeout(aviso.t); aviso.t = setTimeout(() => { el.className = "aviso-global"; }, ok ? 6000 : 15000);
}

function textoEntorno(p) {
  const base = textoEntornoBase(p);
  if (!base || !p.compila || (DATOS.entornos[p.carpeta] || {}).estado === "listo"
      || (DATOS.entornos[p.carpeta] || {}).estado === "subcarpetas") return base;
  // PyBullet en Windows se compila: se avisa ANTES de pulsar, con el remedio si falta el compilador.
  if (DATOS.build_tools === false)
    return { cls: "mal", txt: base.txt + ". OJO: PyBullet se compila en Windows y faltan las Visual Studio Build Tools (C++). "
      + "Instálalas una vez con: " + WINGET + " — mientras tanto funciona todo lo marcado \"sin instalar nada\"." };
  return { cls: base.cls, txt: base.txt + ". La primera vez COMPILA PyBullet (10-15 min, con las Visual Studio Build Tools ya instaladas)." };
}

function textoEntornoBase(p) {
  if (!p.python || !(p.python.paquetes || []).length) return null;
  const e = DATOS.entornos[p.carpeta];
  const n = p.python.paquetes.length;
  if (!e) return { cls: "", txt: `Entorno de Python: revisando… (${n} paquete${n > 1 ? "s" : ""})` };
  if (e.estado === "listo") return { cls: "ok", txt: `Entorno de Python listo (${e.detalle})` };
  if (e.estado === "nuevo") return { cls: "", txt: `La primera vez se crea su entorno con ${e.detalle} e instala ${n} paquete${n > 1 ? "s" : ""}: ${p.python.paquetes.join(", ")}` };
  if (e.estado === "faltan") return { cls: "", txt: `Al entorno le faltan paquetes (${e.detalle}); se instalan al pulsar un botón de Python` };
  if (e.estado === "sin-python") return { cls: "mal", txt: `Necesita Python ${e.detalle} y no está instalado: instálalo desde python.org (el botón explica cuál)` };
  if (e.estado === "subcarpetas") return { cls: "ok", txt: "Usa el entorno de cada subcarpeta (si a alguno le falta algo, se prepara al pulsar)" };
  if (e.estado === "roto") return { cls: "mal", txt: `El entorno ${e.detalle} no arranca: bórralo y se crea solo` };
  return { cls: "", txt: "Entorno: " + (e.detalle || e.estado) };
}

// Qué se puede probar YA, sin instalar nada en el PC (útil mientras se instala o compila lo demás).
function sinInstalar(p, a) {
  // Una url a localhost (dashboard del laboratorio) necesita algo levantado antes: sin marca.
  if (a.tipo === "url" && /^https?:\/\/(localhost|127\.0\.0\.1)/.test(a.url || "")) return "";
  if (["html", "archivo", "url", "info"].includes(a.tipo) || (a.tipo === "python" && !(p.python && p.python.paquetes.length)))
    return '<span class="tipo t-libre">sin instalar nada</span>';
  if (a.tipo === "docker") return '<span class="tipo t-libre">sin compilar: Docker</span>';
  return "";
}

function htmlAccion(p, a) {
  const deshab = a.error ? "disabled" : "";
  let botones = "";
  if (a.tipo === "info") {
    botones = a.enlace ? `<button class="btn" data-ver="${esc(a.enlace)}">Ver archivo</button>` : "";
  } else {
    const etiqueta = { python: "Lanzar", html: "Abrir", archivo: "Abrir", docker: "Levantar", url: "Abrir" }[a.tipo] || "Abrir";
    botones = `<button class="btn primario" data-lanzar="${esc(a.id)}" ${deshab}>${etiqueta}</button>`;
    if (a.tipo === "python" || a.tipo === "docker")
      // En python, Detener sale solo mientras corre; en docker siempre (el laboratorio puede
      // seguir levantado de otra vez que se abrió el lanzador).
      botones += `<button class="btn rojo" data-detener="${esc(a.id)}" ${deshab} ${a.tipo === "python" ? "hidden" : ""}>Detener</button>`;
  }
  return `<div class="accion" data-accion="${esc(a.id)}">
    <div class="accion-cab"><div><span class="accion-nombre">${esc(a.nombre)}</span><span class="tipo t-${esc(a.tipo)}">${esc(TIPO_TXT[a.tipo] || a.tipo)}</span>${sinInstalar(p, a)}</div>
      <div class="botones">${botones}</div></div>
    ${a.descripcion ? `<p class="desc">${esc(a.descripcion)}</p>` : ""}
    ${a.muestra ? `<div class="muestra">${esc(a.muestra)}</div>` : ""}
    ${a.tipo === "docker" && a.abrir ? `<div class="muestra">luego abre ${esc(a.abrir)}</div>` : ""}
    ${a.cubre.length ? `<div class="cubre"><b>Cubre del enunciado:</b> ${a.cubre.map(esc).join(" · ")}</div>` : ""}
    ${a.error ? `<div class="errores">No se puede lanzar: ${esc(a.error)}</div>` : ""}
    <div class="estado" hidden></div>
    <details class="log" hidden><summary>registro</summary><pre class="log"></pre></details>
  </div>`;
}

function htmlTarjeta(p) {
  const final = !/^\d/.test(p.carpeta);
  const ent = textoEntorno(p);
  return `<article id="p-${esc(p.carpeta)}" class="tarjeta ${p.errores.length ? "rota" : ""} ${final ? "final" : ""}" data-carpeta="${esc(p.carpeta)}">
    <div class="tit"><span class="num">${esc(final ? "★" : p.id)}</span><h2>${esc(p.titulo)}</h2></div>
    <div class="carpeta">${esc(p.carpeta)}/</div>
    ${p.resumen ? `<p class="resumen">${esc(p.resumen)}</p>` : ""}
    ${p.errores.length ? `<div class="errores">probar.json con errores:<br>${p.errores.map(esc).join("<br>")}</div>` : ""}
    ${p.pide.length ? `<div class="seccion">Qué pide la actividad</div><ul class="pide">${p.pide.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
    ${p.acciones.length ? `<div class="seccion">Probar</div>${p.acciones.map((a) => htmlAccion(p, a)).join("")}` : ""}
    ${ent ? `<div class="entorno ${ent.cls}" data-entorno>${esc(ent.txt)}</div>` : ""}
    ${p.notas.length ? `<div class="notas">${p.notas.map((n) => `<p>${esc(n)}</p>`).join("")}</div>` : ""}
    <div class="pie">
      ${p.readme ? `<a href="/readme/${encodeURIComponent(p.carpeta)}" target="_blank" rel="noopener">README (aquí)</a>` : ""}
      <a href="${esc(p.github)}" target="_blank" rel="noopener">README en GitHub</a>
      <button class="enlace" data-carpeta-abrir>Abrir la carpeta</button>
    </div>
  </article>`;
}

function textoBusqueda(p) {
  return [p.carpeta, p.id, p.titulo, p.resumen, ...p.pide, ...p.notas,
    ...p.acciones.flatMap((a) => [a.nombre, a.descripcion, a.tipo, TIPO_TXT[a.tipo], ...a.cubre])].join(" ").toLowerCase()
    .normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function pasaFiltro(p) {
  const tipos = new Set(p.acciones.map((a) => a.tipo));
  if (filtro === "python") return tipos.has("python");
  if (filtro === "docker") return tipos.has("docker");
  if (filtro === "navegador") return tipos.has("html") || tipos.has("url");
  return true;
}

function aplicarFiltros() {
  const q = document.getElementById("buscar").value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
  let visibles = 0;
  for (const el of document.querySelectorAll(".tarjeta")) {
    const p = DATOS.practicas.find((x) => x.carpeta === el.dataset.carpeta);
    const ok = p && pasaFiltro(p) && (!q || q.split(/\s+/).every((t) => textoBusqueda(p).includes(t)));
    el.hidden = !ok; visibles += ok;
    const enl = document.querySelector(`.indice a[data-c="${CSS.escape(el.dataset.carpeta)}"]`);
    if (enl) enl.classList.toggle("oculto", !ok);
  }
  const v = document.getElementById("vacio");
  v.hidden = visibles > 0;
  v.textContent = DATOS.practicas.length ? "Ninguna práctica coincide con la búsqueda." :
    "Todavía no hay ninguna práctica con probar.json en " + (DATOS.raiz || "la carpeta del repo") + ".";
}

function pintarSistema() {
  const s = document.getElementById("sistema");
  const py = DATOS.pythons && DATOS.pythons.length ? DATOS.pythons.join(" · ") : "buscando…";
  s.innerHTML = `<span class="chip">lanzador: Python ${esc(DATOS.python)}</span><span class="chip">Pythons instalados: ${esc(py)}</span>`
    + `<span class="chip">${DATOS.practicas.length} prácticas</span>`;
}

async function cargar() {
  try { DATOS = await api("/api/practicas"); }
  catch (e) { aviso("No pude leer las prácticas: " + e.message); return; }
  document.getElementById("rejilla").innerHTML = DATOS.practicas.map(htmlTarjeta).join("");
  // Índice de saltos rápidos: con 12 tarjetas largas, ir directo a la que interesa.
  document.getElementById("indice").innerHTML = DATOS.practicas.map((p) =>
    `<a href="#p-${esc(p.carpeta)}" data-c="${esc(p.carpeta)}" title="${esc(p.titulo)}">${esc(/^\d/.test(p.carpeta) ? p.id : "★ final")}</a>`).join("");
  pintarSistema(); aplicarFiltros(); pintarTrabajos();
}

// Los avisos de entorno y la lista de Pythons se calculan en segundo plano al arrancar:
// se refrescan unas cuantas veces sin repintar las tarjetas (no se pierde lo que se ve).
async function refrescarEntornos() {
  try {
    const d = await api("/api/practicas");
    DATOS.entornos = d.entornos; DATOS.pythons = d.pythons; DATOS.build_tools = d.build_tools;
    for (const el of document.querySelectorAll(".tarjeta")) {
      const p = DATOS.practicas.find((x) => x.carpeta === el.dataset.carpeta);
      const div = el.querySelector("[data-entorno]"); const ent = p && textoEntorno(p);
      if (div && ent) { div.textContent = ent.txt; div.className = "entorno " + ent.cls; }
    }
    pintarSistema();
  } catch (e) { /* el lanzador se cerró: lo avisa el sondeo de trabajos */ }
}

function pintarTrabajos() {
  for (const t of Object.values(TRABAJOS)) {
    const [accionId, sufijo] = t.accion.split(":");
    const el = document.querySelector(`.tarjeta[data-carpeta="${CSS.escape(t.carpeta)}"] .accion[data-accion="${CSS.escape(accionId)}"]`);
    if (!el) continue;
    // El trabajo "detener" y el de lanzar comparten la misma fila: se muestra el más reciente.
    const otro = TRABAJOS[t.carpeta + "|" + (sufijo ? accionId : accionId + ":detener")];
    if (otro && otro.inicio > t.inicio) continue;
    const est = el.querySelector(".estado");
    est.hidden = false;
    est.className = "estado e-" + t.estado;
    const dur = Math.round(((t.fin || Date.now() / 1000) - t.inicio));
    est.innerHTML = `<span class="punto"></span><b>${esc(t.nombre)}</b> · ${esc(ESTADO_TXT[t.estado] || t.estado)}`
      + (t.pid ? ` · PID ${t.pid}` : "") + (t.codigo !== null && t.codigo !== undefined ? ` · código ${t.codigo}` : "") + ` · ${dur}s` + (t.mensaje ? `<span>— ${esc(t.mensaje)}</span>` : "");
    const det = el.querySelector("details.log");
    if (t.log.length) {
      det.hidden = false;
      const pre = det.querySelector("pre");
      const abajo = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 8;
      pre.textContent = t.log.join("\n");
      if (abajo) pre.scrollTop = pre.scrollHeight;
      if ((t.estado === "instalando" || t.estado === "error") && !det.dataset.tocado) det.open = true;
    }
    const bDet = el.querySelector("[data-detener]");
    if (bDet && el.querySelector(".t-python") && !sufijo) bDet.hidden = t.estado !== "lanzada";
    const bLan = el.querySelector("[data-lanzar]");
    if (bLan && !bLan.dataset.err) bLan.disabled = !sufijo && ["preparando", "instalando", "lanzada"].includes(t.estado);
  }
}

let fallosSondeo = 0;
async function sondear() {
  try {
    const lista = await api("/api/trabajos");
    TRABAJOS = {};
    for (const t of lista) TRABAJOS[t.carpeta + "|" + t.accion] = t;
    pintarTrabajos(); fallosSondeo = 0;
  } catch (e) {
    if (++fallosSondeo === 3) aviso("El lanzador no responde: ¿se cerró su consola? Vuelve a abrir PROBAR.bat.");
  }
  setTimeout(sondear, 1200);
}

document.getElementById("rejilla").addEventListener("click", async (ev) => {
  const b = ev.target.closest("button"); if (!b) return;
  const tarjeta = b.closest(".tarjeta"); const carpeta = tarjeta.dataset.carpeta;
  const p = DATOS.practicas.find((x) => x.carpeta === carpeta);
  if (b.dataset.ver) { window.open(b.dataset.ver, "_blank", "noopener"); return; }
  if (b.hasAttribute("data-carpeta-abrir")) {
    try { await api("/api/carpeta", { carpeta }); } catch (e) { aviso(e.message); } return;
  }
  const id = b.dataset.lanzar || b.dataset.detener;
  if (!id) return;
  const a = p.acciones.find((x) => x.id === id);
  // html y url se abren desde aquí mismo (dentro del clic, para que el navegador no lo bloquee).
  if (b.dataset.lanzar && (a.tipo === "html" || a.tipo === "url")) {
    window.open(a.tipo === "html" ? a.enlace : a.url, "_blank", "noopener"); return;
  }
  b.disabled = true;
  try {
    const t = await api(b.dataset.lanzar ? "/api/accion" : "/api/detener", { carpeta, accion: id });
    TRABAJOS[t.carpeta + "|" + t.accion] = t; pintarTrabajos();
  } catch (e) { aviso(e.message); }
  finally { setTimeout(() => { b.disabled = false; pintarTrabajos(); }, 800); }
});
document.getElementById("rejilla").addEventListener("toggle", (ev) => { if (ev.target.matches("details.log")) ev.target.dataset.tocado = "1"; }, true);

document.getElementById("buscar").addEventListener("input", aplicarFiltros);
document.getElementById("filtros").addEventListener("click", (ev) => {
  const b = ev.target.closest(".filtro"); if (!b) return;
  filtro = b.dataset.f;
  for (const x of document.querySelectorAll(".filtro")) x.classList.toggle("activo", x === b);
  aplicarFiltros();
});
document.getElementById("btnDocker").addEventListener("click", async (ev) => {
  ev.target.disabled = true;
  try { const r = await api("/api/docker", {}); aviso(r.mensaje, r.ok); } catch (e) { aviso(e.message); }
  ev.target.disabled = false;
});
document.getElementById("btnSalir").addEventListener("click", async () => {
  if (!confirm("¿Cerrar el lanzador? Lo que ya abriste en otras ventanas sigue abierto.")) return;
  try { await api("/api/salir", {}); } catch (e) { /* ya se cerró */ }
  document.body.innerHTML = '<p class="vacio">Lanzador cerrado. Para volver a abrirlo: doble clic en PROBAR.bat.</p>';
});

cargar().then(() => { sondear(); [2000, 5000, 10000, 20000, 40000].forEach((ms) => setTimeout(refrescarEntornos, ms)); });
</script>
</body>
</html>
"""


# Vista simple de un README: el .md se baja del propio servidor y se convierte con marked
# (y los diagramas mermaid con mermaid). Sin internet, se muestra el texto tal cual.
README_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<base href="__BASE__">
<title>README</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root { --bg: #0d1013; --panel: #15191d; --panel-border: #262b31; --text: #e7e9ec; --text-muted: #8b929b; --accent: #4f8fce; }
  html, body { margin: 0; background: var(--bg); color: var(--text); font-family: "Space Grotesk", system-ui, "Segoe UI", sans-serif; }
  body { padding: 1.2rem 16px 3rem; }
  main { max-width: 920px; margin: 0 auto; line-height: 1.6; font-size: 0.95rem; }
  a { color: var(--accent); }
  .barra { max-width: 920px; margin: 0 auto 1rem; font-family: "IBM Plex Mono", monospace; font-size: 0.72rem; color: var(--text-muted); display: flex; gap: 1rem; flex-wrap: wrap; }
  img { max-width: 100%; height: auto; border-radius: 6px; }
  pre, code { font-family: "IBM Plex Mono", ui-monospace, Consolas, monospace; font-size: 0.82em; }
  pre { background: var(--panel); border: 1px solid var(--panel-border); border-radius: 6px; padding: 0.7rem; overflow-x: auto; }
  :not(pre) > code { background: var(--panel); padding: 0.05rem 0.3rem; border-radius: 4px; }
  table { border-collapse: collapse; display: block; overflow-x: auto; }
  th, td { border: 1px solid var(--panel-border); padding: 0.3rem 0.55rem; }
  h1, h2, h3 { line-height: 1.3; } h2 { border-bottom: 1px solid var(--panel-border); padding-bottom: 0.2rem; }
  blockquote { border-left: 3px solid var(--panel-border); margin: 0; padding-left: 0.9rem; color: var(--text-muted); }
  .mermaid { background: #f4f5f7; border-radius: 6px; padding: 0.6rem; overflow-x: auto; }
</style>
</head>
<body>
<div class="barra"><a href="/">← volver al lanzador</a><a href="__GITHUB__" target="_blank" rel="noopener">ver en GitHub</a></div>
<main id="md">Cargando…</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
const carpeta = __CARPETA__;
document.title = "README · " + carpeta;
fetch("README.md").then((r) => r.text()).then(async (texto) => {
  const main = document.getElementById("md");
  if (!window.marked) { main.innerHTML = ""; const pre = document.createElement("pre"); pre.textContent = texto; main.appendChild(pre); return; }
  main.innerHTML = marked.parse(texto);
  // Los bloques ```mermaid salen como <code class="language-mermaid">: se convierten en diagramas.
  for (const c of main.querySelectorAll("code.language-mermaid")) {
    const div = document.createElement("div"); div.className = "mermaid"; div.textContent = c.textContent;
    c.parentElement.replaceWith(div);
  }
  if (window.mermaid) { mermaid.initialize({ startOnLoad: false, theme: "default" }); try { await mermaid.run(); } catch (e) {} }
}).catch(() => { document.getElementById("md").textContent = "No se pudo leer el README."; });
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
