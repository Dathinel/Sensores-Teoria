#!/usr/bin/env python3
"""
Lanzador de las apps de las prácticas del repo Sensores-Teoria (vive en <raíz>/_lanzador/).

Para quien no conoce el repo: doble clic en el ABRIR.bat de la carpeta de una práctica (en
Linux/Mac, `sh abrir.sh`). Ese .bat corre `python _lanzador/lanzador.py --practica <carpeta>`
y se abre la app de esa práctica en una ventana tipo programa. Ver _lanzador/LEEME.md.

Cómo funciona por dentro (solo biblioteca estándar, Python >= 3.9, para que no haya que
instalar nada antes de poder abrir el lanzador):

  1. Cada práctica declara cómo se prueba en `<carpeta>/probar.json` (ver CONTRATO abajo).
  2. Este script levanta un servidor HTTP en 127.0.0.1 (solo esta máquina; nunca en la red)
     y sirve la app de la práctica (`/app/<carpeta>/`), que lee su manifiesto por una API JSON.
  3. Al pulsar un botón, la app le pide al servidor "lanza la acción X de la práctica Y".
     El servidor SOLO ejecuta acciones declaradas en un probar.json: nunca un comando que
     venga escrito desde la página. Además exige un token secreto (que solo conoce la página
     que sirvió) para que otra web abierta en el navegador no pueda dispararlas.
  4. Las acciones `python` corren con el entorno virtual de la práctica (`<carpeta>/entorno/`),
     creado e instalado solo la primera vez, mostrando el progreso; su salida va a la app
     (o a una consola nueva si la acción dice "modo": "consola").

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

CAMPOS AÑADIDOS para las apps por práctica (ver _lanzador/LEEME.md):
  nivel superior  "app": ruta del index.html de la app (por defecto "app/index.html").
  cada acción     "entrada": true (lee del teclado: la app muestra una caja de texto),
                  "ventana": true (abre su propia ventana), "modo": "app" | "consola".
  Desde una app (`/app/<carpeta>/`), las acciones python corren SIN consola: su salida va a
  un buffer que la página lee por partes (/api/salida?tid=N&desde=M) y, si "entrada", su
  stdin queda abierto (/api/entrada). "modo": "consola" conserva la consola de siempre.
  "duracion": "~4-5 min" o "duracion_s": 270 -> barra estimada y reloj "lleva 1:23 de ~4:30".
  "duracion_es": "arranque" -> esa duración es solo el arranque (el programa sigue hasta que se
                  detiene): pasado ese tiempo la app dice "en marcha", no "tardando más".
  "progreso_regex": "it (\\d+)/(\\d+)" -> barra real con lo que imprime el programa (sintaxis
                  de JavaScript: la aplica la página; un grupo = porcentaje, dos = hecho/total).

Opciones de línea de comandos (sobre todo para desarrollar/probar el lanzador):
  --practica DIR    abre la app de esa práctica;
                    si ya hay un lanzador abierto con la misma raíz, lo reutiliza
  --puerto N        puerto preferido (8099 por defecto; si está ocupado busca otro libre)
  --raiz DIR        carpeta donde buscar */probar.json (por defecto la del repo)
  --entornos DIR    crear/usar los entornos en DIR/<carpeta>/entorno en vez de en cada práctica
  --no-navegador    no abrir el navegador al arrancar
  --comprobar       solo revisar los probar.json e imprimir los errores (no levanta servidor)
"""

import argparse
import codecs
import itertools
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

if sys.version_info < (3, 9):  # pragma: no cover - se comprueba también en cada ABRIR.bat
    sys.exit("El lanzador necesita Python 3.9 o más nuevo.")

ES_WINDOWS = os.name == "nt"
ES_MAC = sys.platform == "darwin"
ESTE_ARCHIVO = Path(__file__).resolve()
TIPOS = ("python", "html", "archivo", "docker", "url", "info")
GITHUB = "https://github.com/Dathinel/Sensores-Teoria/blob/main/"
FIRMA = "lanzador-sensores-teoria"  # para reconocer un lanzador ya abierto en el puerto

# En Windows, los procesos auxiliares (pip, docker info, chequeos) no deben abrir una
# ventana negra que parpadea; las acciones del usuario sí abren su propia consola.
SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0) if ES_WINDOWS else 0
CONSOLA_NUEVA = getattr(subprocess, "CREATE_NEW_CONSOLE", 0) if ES_WINDOWS else 0


class Config:
    raiz = ESTE_ARCHIVO.parent.parent   # la raíz del repo (este archivo vive en <raíz>/_lanzador/)
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
    con la lista de errores, para que un manifiesto mal escrito no tumbe el lanzador."""
    archivo = carpeta / "probar.json"
    p = {
        "carpeta": carpeta.name, "id": carpeta.name, "titulo": carpeta.name, "resumen": "",
        "pide": [], "notas": [], "python": None, "acciones": [], "errores": [],
        "readme": (carpeta / "README.md").is_file(),
        "github": GITHUB + urllib.parse.quote(carpeta.name) + "/README.md",
        "app": None,
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
    # App de la práctica (apps-comun/LEEME.md): "app" o, por defecto, app/index.html.
    rel_app = str(datos.get("app") or "app/index.html").replace("\\", "/")
    f_app = ruta_dentro(carpeta, rel_app)
    p["app_declarada"] = rel_app
    if f_app is not None and f_app.is_file() and f_app.suffix.lower() in (".html", ".htm"):
        p["app"] = "/app/" + urllib.parse.quote(carpeta.name) + "/" + (urllib.parse.quote(f_app.name) if f_app.name.lower() != "index.html" else "")
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
        # Añadidos para las apps: lee del teclado, abre su propia ventana, dónde se ve la salida.
        "entrada": bool(a.get("entrada")),
        "ventana": bool(a.get("ventana")),
        "modo": str(a.get("modo") or "app"),
        # Texto propio para el recuadro de error de la app (qué hacer si falla ESTA acción).
        "si_falla": str(a.get("si_falla") or ""),
        # Acción interna de una app (no sale en la lista de pruebas) y si se para sola al cerrar la app.
        "oculta": bool(a.get("oculta") or a.get("solo_app")),
        "vida": "app" if str(a.get("vida") or "") == "app" else "",
        # Cuánto suele tardar (barra estimada + reloj "lleva 1:23 de ~4:30" en la app) y qué
        # línea de la salida indica el avance real (barra real). Ver _lanzador/LEEME.md.
        "duracion": str(a.get("duracion") or ""),
        "duracion_s": None,
        "progreso_regex": str(a.get("progreso_regex") or ""),
        # "arranque": la duración es solo lo que tarda en arrancar un programa que sigue en marcha
        # hasta que se detiene (YOLO con la cámara); pasado ese tiempo la app dice "en marcha".
        "duracion_es": str(a.get("duracion_es") or ""),
    }
    errores = []
    if acc["duracion_es"] not in ("", "total", "arranque"):
        errores.append(f"\"duracion_es\" \"{acc['duracion_es']}\" desconocido (válidos: total, arranque)")
    if a.get("duracion_s") is not None:
        try:
            acc["duracion_s"] = max(1, int(float(a["duracion_s"])))
        except (TypeError, ValueError):
            errores.append("\"duracion_s\" debe ser un número de segundos")
    elif acc["duracion"]:
        acc["duracion_s"] = segundos_de(acc["duracion"])
        if acc["duracion_s"] is None:
            errores.append(f"no entiendo la \"duracion\" \"{acc['duracion']}\" (ejemplos: \"~4-5 min\", \"30 s\", \"1 min 30 s\")")
    if acc["duracion_s"] and not acc["duracion"]:
        acc["duracion"] = "~" + reloj(acc["duracion_s"])
    if acc["progreso_regex"]:
        # La usa la página (JavaScript): se revisa aquí que compile y que no use sintaxis
        # solo de Python, para que el error salga en --comprobar y no en silencio en la app.
        try:
            r = re.compile(acc["progreso_regex"])
            if "(?P" in acc["progreso_regex"]:
                errores.append("\"progreso_regex\": usa grupos normales ( ), no (?P<nombre>...) (lo lee JavaScript)")
            elif r.groups < 1:
                errores.append("\"progreso_regex\" necesita un grupo (porcentaje) o dos (hecho, total)")
        except re.error as e:
            errores.append(f"\"progreso_regex\" no es una expresión regular válida: {e}")
    if acc["modo"] not in ("app", "consola"):
        errores.append(f"modo \"{acc['modo']}\" desconocido (válidos: app, consola)")
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


UNIDADES = {"h": 3600, "hora": 3600, "horas": 3600, "min": 60, "m": 60, "mins": 60, "minuto": 60, "minutos": 60,
            "s": 1, "seg": 1, "segs": 1, "segundo": 1, "segundos": 1}


def segundos_de(texto):
    """"~4-5 min" -> 270 (el punto medio de un rango), "30 s" -> 30, "1 min 30 s" -> 90.
    Solo cuenta la PRIMERA duración del texto (y las unidades menores pegadas a ella, como el
    "30 s" de "1 min 30 s"): en "~30 s si ya están las imágenes; la primera vez 10-20 min"
    es 30 s (lo habitual; el resto es una aclaración para leer). None si no hay ninguna."""
    total, ultimo, fin = 0.0, None, None
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)(?:\s*(?:-|–|a)\s*(\d+(?:[.,]\d+)?))?\s*([a-záéíóú]+)", texto.lower()):
        u = UNIDADES.get(m.group(3))
        if not u:
            continue
        if ultimo is not None and (u >= ultimo or texto[fin:m.start()].strip(" ,y")):
            break
        a = float(m.group(1).replace(",", "."))
        b = float(m.group(2).replace(",", ".")) if m.group(2) else a
        total += (a + b) / 2 * u
        ultimo, fin = u, m.end()
    return max(1, round(total)) if ultimo is not None else None


def reloj(seg):
    seg = int(round(seg))
    return f"{seg // 60}:{seg % 60:02d}"


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

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")   # colores/cursor de docker y otros: fuera del log
CONTADOR_TID = itertools.count(1)


class Trabajo:
    """Un botón pulsado: estado + salida numerada (la página la pide por partes con desde=N).

    Cada línea lleva un tipo: "sis" (mensajes del lanzador), "pip" (lo que imprime pip o
    venv mientras se prepara el entorno), "prog" (lo que imprime el programa) e "in" (lo
    que el usuario le escribió desde la app)."""

    def __init__(self, carpeta, accion, nombre, modo="consola", entrada=False):
        self.tid = next(CONTADOR_TID)
        self.carpeta, self.accion, self.nombre = carpeta, accion, nombre
        self.estado = "preparando"     # preparando | instalando | lanzada | terminada | error | detenida
        self.fase = ""                 # revisando | creando | instalando | compilando | docker | corriendo
        self.mensaje = ""
        self.pid = None
        self.codigo = None
        self.inicio = time.time()
        self.lanzado = None            # cuándo arrancó el programa (tras preparar el entorno)
        self.fin = None
        self.lineas = deque(maxlen=5000)   # (n, tipo, texto): pip puede escupir miles
        self.total = 0
        self.parcial = ""              # texto sin salto de línea todavía (p. ej. la pregunta de un input())
        self.proceso = None
        self.stdin = None
        self.modo = modo               # "app" (salida en la página) o "consola" (ventana aparte)
        self.entrada = entrada
        self.abrir = ""                # docker en modo app: dirección a abrir al terminar
        self.cancelado = False
        self.fallo_en = None           # "preparar" | "programa"
        self.vida_app = False          # "vida": "app": se detiene si la app se cierra
        self.seguimiento = True        # False si no podemos saber cuándo termina (Terminal de macOS)
        self.cerrojo = threading.Lock()

    def escribir(self, linea, tipo="sis"):
        with self.cerrojo:
            self._agregar(tipo, linea.rstrip("\r\n"))

    def _agregar(self, tipo, texto):
        self.total += 1
        self.lineas.append((self.total, tipo, ANSI.sub("", texto)[:2000]))

    def alimentar(self, texto, tipo="prog"):
        """Trozos crudos de la salida de un programa (pueden cortar una línea por la mitad)."""
        with self.cerrojo:
            s = (self.parcial + ANSI.sub("", texto)).replace("\r\n", "\n")
            *completas, resto = s.split("\n")
            for l in completas:
                # \r sin \n = barra de progreso que se reescribe: queda lo último.
                partes = [x for x in l.split("\r") if x.strip()]
                self._agregar(tipo, partes[-1] if partes else "")
            if len(resto) > 4000:
                self._agregar(tipo, resto)
                resto = ""
            self.parcial = resto

    def cerrar_parcial(self, tipo="prog"):
        with self.cerrojo:
            if self.parcial.strip():
                partes = [x for x in self.parcial.split("\r") if x.strip()]
                self._agregar(tipo, partes[-1])
            self.parcial = ""

    def poner(self, estado, mensaje=None, fase=None):
        if self.cancelado and estado != "detenida":
            return   # tras Detener, lo que siga haciendo el hilo de la acción ya no cambia el estado
        self.estado = estado
        if mensaje is not None:
            self.mensaje = mensaje
        if fase is not None:
            self.fase = fase
        if estado in ("terminada", "error", "detenida"):
            self.fin = time.time()

    @property
    def activo(self):
        return self.estado in ("preparando", "instalando", "lanzada")

    def resumen(self):
        return {"tid": self.tid, "carpeta": self.carpeta, "accion": self.accion, "nombre": self.nombre,
                "estado": self.estado, "fase": self.fase, "mensaje": self.mensaje, "pid": self.pid,
                "codigo": self.codigo, "inicio": self.inicio, "lanzado": self.lanzado, "fin": self.fin,
                "modo": self.modo, "entrada": self.entrada and self.stdin is not None and self.estado == "lanzada",
                "abrir": self.abrir, "fallo_en": self.fallo_en, "parcial": self.parcial.split("\r")[-1][-500:]}

    def a_dict(self):
        """Para /api/trabajos: el resumen + las últimas 400 líneas como texto."""
        with self.cerrojo:
            log = [x for (_, _, x) in list(self.lineas)[-400:]]
        d = self.resumen()
        d["log"] = log
        return d

    def salida(self, desde):
        """Las líneas con número > desde (y "siguiente" para la próxima petición)."""
        with self.cerrojo:
            lineas = [{"n": n, "t": t, "x": x} for (n, t, x) in self.lineas if n > desde]
            total = self.total
        d = self.resumen()
        d.update(lineas=lineas, siguiente=total)
        return d


TRABAJOS = {}                 # (carpeta, accion) -> último Trabajo
POR_TID = {}                  # tid -> Trabajo (los últimos 300)
TRABAJOS_LOCK = threading.Lock()
ENTORNO_LOCKS = {}            # un cerrojo por carpeta: dos botones no crean el mismo entorno a la vez
ESTADO_ENTORNOS = {}          # carpeta -> {"estado": ..., "detalle": ...} para el aviso de la tarjeta


def registrar(t):
    with TRABAJOS_LOCK:
        TRABAJOS[(t.carpeta, t.accion)] = t
        POR_TID[t.tid] = t
        while len(POR_TID) > 300:
            POR_TID.pop(min(POR_TID))


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


def correr_con_log(trabajo, cmd, cwd=None, tipo="pip", env_extra=None):
    """Corre un comando sin ventana y va pasando su salida, línea a línea, al log del trabajo."""
    if trabajo.cancelado:
        raise ErrorClaro("Detenido.")   # pulsaron Detener mientras se preparaba: no seguir
    trabajo.escribir("$ " + " ".join(str(c) for c in cmd), tipo)
    env = entorno_hijo()
    env.update(env_extra or {})
    env.setdefault("COMPOSE_ANSI", "never")       # docker compose sin colores ni cursores
    env.setdefault("BUILDKIT_PROGRESS", "plain")
    p = subprocess.Popen([str(c) for c in cmd], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                         creationflags=SIN_VENTANA, env=env)
    trabajo.proceso = p
    for linea in p.stdout:
        if linea.strip():
            trabajo.escribir(linea, tipo)
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
    """Para mostrar en la app qué Pythons hay (ayuda a entender los avisos)."""
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
        trabajo.poner("instalando", f"Instalando {len(paquetes)} librería(s) de Python (puede tardar unos minutos la primera vez)…",
                      fase="instalando")
        codigo = correr_con_log(trabajo, comando)
    else:
        # Se comprueba ANTES de llamar a pip: sin compilador, pip fallaría tras varios minutos
        # con un error poco claro ("Unable to find a compatible Visual Studio installation").
        vcvars = buscar_build_tools()
        if not vcvars:
            raise ErrorClaro(MENSAJE_BUILD_TOOLS)
        trabajo.poner("instalando", "Instalando paquetes y COMPILANDO PyBullet: la primera vez tarda unos 10-15 minutos "
                                    "(las siguientes es inmediato, pip guarda lo compilado en su caché)…", fase="compilando")
        # pip tiene que correr DENTRO del entorno del compilador (vcvars64.bat): solo poner el
        # compilador en el PATH no basta. DISTUTILS_USE_SDK=1 le dice a setuptools que use ese
        # entorno ya preparado en vez de buscar Visual Studio por su cuenta (lo que fallaba).
        # Se escribe un .bat junto al entorno porque las rutas con espacios dentro de `cmd /c "..."`
        # se rompen con facilidad. Las rutas NO van escritas dentro del .bat sino en variables de
        # entorno (LANZ_*): cmd.exe lee los .bat con la página de códigos de la consola, así que
        # una ruta con tildes o ñ (C:\Users\José\...) escrita en el archivo llegaría deformada;
        # en una variable de entorno llega en Unicode tal cual.
        bat = Path(python).resolve().parent.parent / "instalar_con_msvc.bat"
        linea = subprocess.list2cmdline(comando[1:])   # "-m pip install ..." (solo ASCII)
        bat.write_text("@echo off\r\n"
                       "set \"PATH=%LANZ_VS_INSTALADOR%;%PATH%\"\r\n"
                       "call \"%LANZ_VCVARS%\" >nul || exit /b 1\r\n"
                       "set DISTUTILS_USE_SDK=1\r\n"
                       f"\"%LANZ_PYTHON%\" {linea}\r\n", encoding="ascii", errors="replace")
        trabajo.escribir(f"Compilador: {vcvars}")
        codigo = correr_con_log(trabajo, ["cmd", "/c", str(bat)], env_extra={
            "LANZ_VS_INSTALADOR": str(carpeta_instalador_vs()), "LANZ_VCVARS": str(vcvars),
            "LANZ_PYTHON": str(python)})
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

        trabajo.poner("instalando", f"Creando el entorno de Python {version} de esta práctica (solo la primera vez)…", fase="creando")
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


def revisar_entorno_de(d):
    """Mira el entorno de UNA práctica y deja en ESTADO_ENTORNOS si está "listo", si "se creará
    la primera vez", etc. (para el aviso de la tarjeta y del panel de la app)."""
    try:
        p = leer_manifiesto(d)
        conf = p.get("python")
        if not conf or not conf["paquetes"]:
            return
        env = ruta_entorno(p["carpeta"])
        py = python_del_entorno(env)
        subs = [Path(a["cwd"]) / "entorno" for a in p["acciones"]
                if a["tipo"] == "python" and a.get("cwd") and Path(a["cwd"]).resolve() != d.resolve()]
        if not env.exists() and not Config.entornos and any(python_del_entorno(x).exists() for x in subs):
            ESTADO_ENTORNOS[p["carpeta"]] = {"estado": "subcarpetas", "detalle": ""}
            return
        if not env.exists():
            v = next((v for v in conf["versiones"] if buscar_python(v)), None)
            ESTADO_ENTORNOS[p["carpeta"]] = (
                {"estado": "nuevo", "detalle": f"Python {v}"} if v or not conf["versiones"]
                else {"estado": "sin-python", "detalle": ", ".join(conf["versiones"])})
            return
        est = revisar_entorno(py, conf["paquetes"]) if py.exists() else None
        if est is None:
            ESTADO_ENTORNOS[p["carpeta"]] = {"estado": "roto", "detalle": str(env)}
        elif est["faltan"]:
            ESTADO_ENTORNOS[p["carpeta"]] = {"estado": "faltan", "detalle": ", ".join(est["faltan"])}
        else:
            ESTADO_ENTORNOS[p["carpeta"]] = {"estado": "listo", "detalle": f"Python {est['version']}"}
    except Exception as e:  # un fallo aquí solo deja la tarjeta sin aviso
        ESTADO_ENTORNOS[d.name] = {"estado": "desconocido", "detalle": str(e)}


def revisar_entornos_en_segundo_plano(primero=None):
    """Al arrancar, mira cada entorno. En un hilo aparte: con 12 prácticas tarda unos segundos
    y la página no debe esperar. `primero`: la práctica que se abre con --practica va antes."""
    carpetas = carpetas_con_manifiesto()
    carpetas.sort(key=lambda d: d.name != primero)
    for d in carpetas:
        if d.name not in ESTADO_ENTORNOS:
            revisar_entorno_de(d)


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


def vigilar(trabajo, p, al_terminar=None, lector=None):
    """Hilo que espera a que el programa (o su consola) termine y deja el trabajo terminado."""
    codigo = p.wait()
    if lector:
        lector.join(timeout=5)     # que llegue a la página lo último que imprimió
        trabajo.cerrar_parcial()
    trabajo.codigo = codigo
    if trabajo.stdin:
        try:
            trabajo.stdin.close()
        except OSError:
            pass
        trabajo.stdin = None
    if trabajo.estado == "detenida" or trabajo.cancelado:
        return
    if codigo == 0:
        trabajo.poner("terminada", "Terminó bien.")
        if al_terminar:
            al_terminar()
    else:
        trabajo.fallo_en = "programa"
        if trabajo.modo == "app":
            trabajo.poner("error", f"El programa terminó con error (código {codigo}).")
        else:
            trabajo.poner("error", f"Terminó con error (código {codigo}). La ventana muestra el detalle.")


# --------------------------------------------------------------------------------------
# Modo app: sin consola, la salida va al buffer del trabajo y la página la lee por partes
# --------------------------------------------------------------------------------------

def lanzar_en_app(trabajo, cmd, cwd, entrada=False, env_extra=None):
    """Corre `cmd` SIN ventana de consola (las ventanas propias del programa, PyBullet u
    OpenCV, se abren igual). stdout y stderr van juntos, en el orden en que salen, al buffer
    del trabajo; stdin queda abierto si la acción declara "entrada"."""
    env = entorno_hijo()
    env.update(env_extra or {})
    opciones = {}
    if ES_WINDOWS:
        opciones["creationflags"] = SIN_VENTANA
    else:
        opciones["start_new_session"] = True   # grupo propio: Detener mata también a los hijos
    p = subprocess.Popen([str(c) for c in cmd], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.PIPE if entrada else subprocess.DEVNULL, env=env, **opciones)
    trabajo.proceso = p
    trabajo.pid = p.pid
    trabajo.stdin = p.stdin if entrada else None
    trabajo.lanzado = time.time()
    if trabajo.cancelado:          # Detener llegó mientras arrancaba
        matar_arbol(p.pid)

    def leer():
        # Se lee por trozos (read1), no por líneas: así una pregunta sin salto de línea, como
        # la de input("Escribe: "), aparece en la página enseguida.
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        while True:
            try:
                datos = p.stdout.read1(65536)
            except (OSError, ValueError):
                break
            if not datos:
                break
            trabajo.alimentar(dec.decode(datos))
        trabajo.alimentar(dec.decode(b"", final=True))

    lector = threading.Thread(target=leer, daemon=True)
    lector.start()
    trabajo.poner("lanzada", "En marcha.", fase="corriendo")
    return p, lector


def escribir_entrada(carpeta, accion_id, texto):
    """Lo que el usuario escribe en la caja de la app va al stdin del programa (+ Enter)."""
    with TRABAJOS_LOCK:
        t = TRABAJOS.get((carpeta, accion_id))
    if not t or t.estado != "lanzada" or t.modo != "app":
        raise ErrorClaro("El programa no está en marcha: pulsa Iniciar primero.")
    if not t.stdin:
        raise ErrorClaro("Este programa no lee del teclado (su acción no tiene \"entrada\": true).")
    texto = str(texto).replace("\r", "").replace("\n", " ")[:4000]
    try:
        t.stdin.write((texto + "\n").encode("utf-8"))
        t.stdin.flush()
    except (OSError, ValueError):
        raise ErrorClaro("El programa ya no acepta texto (¿terminó?).")
    # La pregunta que estaba a medias (input("Escribe: ")) queda como línea propia y debajo lo
    # que contestó el usuario, como se vería en una consola.
    with t.cerrojo:
        pregunta, t.parcial = t.parcial.split("\r")[-1], ""
        if pregunta.strip():
            t._agregar("pregunta", pregunta)   # la página la pinta en la misma línea que la respuesta
        t._agregar("in", texto)
    return t


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

def iniciar_accion(carpeta, accion_id, detener=False, desde_app=False):
    """desde_app: la pide una app (/app/...). Entonces las acciones python y docker corren
    sin consola con la salida en la página, salvo que la acción diga "modo": "consola"."""
    practica = buscar_practica(carpeta)
    accion = buscar_accion(practica, accion_id)
    clave = (carpeta, accion_id)
    en_app = desde_app and accion.get("modo", "app") != "consola" and accion["tipo"] in ("python", "docker")
    with TRABAJOS_LOCK:
        previo = TRABAJOS.get(clave)
        if not detener and previo and previo.activo and previo.seguimiento:
            raise ErrorClaro(f"\"{accion['nombre']}\" ya está en marcha. Ciérrala (o pulsa Detener) antes de lanzarla otra vez.")
        if detener and previo and previo.activo:
            # Detener lo que está corriendo: el programa con todos sus hijos, o el pip/venv que
            # está preparando el entorno. Se marca cancelado ANTES: si el programa todavía no
            # arrancó (revisando el entorno), ya no se lanza, y si arranca justo ahora,
            # lanzar_en_app lo mata en cuanto existe (un solo clic en Detener basta).
            previo.cancelado = True
            if previo.pid or previo.proceso:
                matar_arbol(previo.pid or previo.proceso.pid)
            previo.poner("detenida", "Detenido." if previo.modo == "app" else "Detenida desde el lanzador.")
            if accion["tipo"] != "docker":
                return previo
        elif detener and accion["tipo"] != "docker":
            # Solo docker tiene un "detener" propio (docker compose stop) aunque no haya nada en
            # marcha; en los demás tipos, seguir adelante LANZARÍA la acción (abriría el archivo).
            raise ErrorClaro("No hay nada en marcha que detener.")
        nombre = accion["nombre"] + (" (detener)" if detener else "")
        t = Trabajo(carpeta, accion_id + (":detener" if detener else ""), nombre,
                    modo="app" if en_app else "consola", entrada=bool(accion.get("entrada")) and en_app)
        t.vida_app = en_app and accion.get("vida") == "app"
    registrar(t)
    threading.Thread(target=ejecutar, args=(t, practica, accion, detener), daemon=True).start()
    return t


def ejecutar(t, practica, accion, detener):
    try:
        tipo = accion["tipo"]
        titulo = f"{practica['id']} · {accion['nombre']}"
        if tipo == "python":
            t.poner("preparando", "Revisando el entorno de Python…", fase="revisando")
            python = preparar_entorno(t, practica, accion)
            if t.cancelado:
                return
            if accion.get("modulo"):
                cmd = [python, "-m", accion["modulo"], *accion["args"]]
            else:
                cmd = [python, accion["script"], *accion["args"]]
            t.escribir("Lanzo: " + accion.get("muestra", ""))
            if t.modo == "app":
                p, lector = lanzar_en_app(t, cmd, accion["cwd"], entrada=t.entrada)
                vigilar(t, p, lector=lector)
                return
            # La ventana queda abierta al terminar ("Pulsa Enter"): varios scripts solo imprimen
            # un resultado y terminan (el gemelo del tema 10), y si se cerrara sola no se vería.
            p = lanzar_en_consola(t, cmd, accion["cwd"], titulo, pausa="siempre")
            if p and t.cancelado:
                matar_arbol(p.pid)
            if p:
                vigilar(t, p)
        elif tipo == "archivo":
            abrir_con_sistema(accion["ruta"])
            t.poner("terminada", "Abierto con el programa del sistema.")
        elif tipo == "docker":
            t.poner("preparando", "Comprobando que Docker Desktop esté abierto (puede tardar unos segundos)…", fase="docker")
            ok, msg = comprobar_docker()
            t.escribir(msg)
            if not ok:
                raise ErrorClaro(msg)
            carpeta = str(Config.raiz / practica["carpeta"])
            tipo_log = "prog" if t.modo == "app" else "pip"
            if detener:
                t.poner("lanzada", "Deteniendo los contenedores…", fase="corriendo")
                codigo = correr_con_log(t, ["docker", "compose", "-f", accion["compose"], *accion["detener"]],
                                        cwd=carpeta, tipo=tipo_log)
                t.codigo = codigo
                if codigo != 0:
                    raise ErrorClaro("docker compose no pudo detener el laboratorio (mira el registro).")
                t.poner("terminada", "Contenedores detenidos.")
                return
            cmd = ["docker", "compose", "-f", accion["compose"], *accion["args"]]
            t.escribir("Lanzo: " + " ".join(cmd))
            abrir = accion.get("abrir")
            if t.modo == "app":
                # Sin consola: lo que imprime compose (construir la imagen, la simulación) se ve
                # en la página. Al terminar bien, la página muestra el botón para abrir "abrir".
                p, lector = lanzar_en_app(t, cmd, carpeta,
                                          env_extra={"COMPOSE_ANSI": "never", "BUILDKIT_PROGRESS": "plain"})
                t.poner("lanzada", "Trabajando con Docker…")

                def al_terminar_app():
                    if abrir:
                        t.abrir = abrir
                        t.poner("terminada", "Laboratorio levantado.")
                vigilar(t, p, al_terminar_app, lector=lector)
                return
            # Con `up -d` compose vuelve enseguida y la consola puede cerrarse sola (luego se abre
            # "abrir"); sin -d (p. ej. `run --rm simulacion`) lo que importa es lo que imprime,
            # así que la ventana queda abierta al terminar para poder leerlo.
            separado = any(x in ("-d", "--detach") for x in accion["args"])
            p = lanzar_en_consola(t, cmd, carpeta, titulo, pausa="error" if separado else "siempre")

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
        if t.cancelado:
            return
        t.escribir(str(e))
        t.fallo_en = "preparar" if not t.lanzado else "programa"
        t.poner("error", str(e))
    except Exception as e:  # cualquier otra cosa: mensaje corto, no una traza
        if t.cancelado:
            return
        t.escribir(f"{type(e).__name__}: {e}")
        t.fallo_en = "preparar" if not t.lanzado else "programa"
        t.poner("error", f"Algo falló al lanzar la acción: {e}")


def detener_trabajos_de_app(motivo="Detenido: se cerró el lanzador."):
    """Al cerrarse el lanzador (su ventana, Ctrl+C, el cierre solo por inactividad o "Salir"),
    los programas que corren SIN consola (modo app) se detienen con sus hijos. Si no, quedarían
    huérfanos e invisibles: nadie lee ya su salida, y en cuanto llenan el tubo de stdout se
    quedan colgados (una ventana de PyBullet congelada que no se puede cerrar desde la app).
    Los de "modo": "consola" tienen su propia ventana y siguen: se cierran desde ella."""
    with TRABAJOS_LOCK:
        activos = [t for t in TRABAJOS.values() if t.activo and t.modo == "app" and (t.pid or t.proceso)]
    for t in activos:
        t.cancelado = True
        try:
            matar_arbol(t.pid or t.proceso.pid)
        except Exception:
            pass
        t.poner("detenida", motivo)
    return len(activos)


_MANEJADOR_CONSOLA = []   # referencia viva al callback de ctypes (si se libera, Windows llamaría a basura)


def al_cerrar_la_consola():
    """Windows: cerrar la ventana negra del ABRIR.bat (o cerrar sesión / apagar) mata el
    proceso de golpe, sin pasar por los `finally`. Con SetConsoleCtrlHandler se alcanza a
    detener los programas en modo app (Windows da ~5 s) antes de que eso pase."""
    if not ES_WINDOWS:
        return
    try:
        import ctypes
        from ctypes import wintypes
        tipo = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

        def manejador(evento):
            if evento in (2, 5, 6):   # CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT
                detener_trabajos_de_app()
            return False              # que siga el manejo normal (Ctrl+C -> KeyboardInterrupt)
        _MANEJADOR_CONSOLA.append(tipo(manejador))
        ctypes.windll.kernel32.SetConsoleCtrlHandler(_MANEJADOR_CONSOLA[-1], True)
    except Exception:
        pass


def matar_arbol(pid):
    """Cierra el programa (o su consola) y todo lo que corre dentro (sus procesos hijos)."""
    if ES_WINDOWS:
        correr_corto(["taskkill", "/PID", str(pid), "/T", "/F"], timeout=15)
    else:
        try:
            os.killpg(os.getpgid(pid), 15)   # modo app: el programa tiene su propio grupo
        except (OSError, AttributeError):
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
    print("Lanzado desde la app de la práctica (Sensores-Teoria).")
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
    entornos, git, las bases de datos locales y los PDF/Word privados que el .gitignore ya
    excluye del repo. Vale para /repo/ y para /app/."""
    rel = str(rel).replace("\\", "/")
    # Windows: "x.db::$DATA" (flujo de datos alternativo) abre el mismo archivo "x.db", y los
    # puntos/espacios del final se ignoran ("x.db." es "x.db"): sin esto, se saltarían los
    # filtros de abajo. Ningún archivo legítimo del repo lleva ":" en la ruta.
    if ":" in rel:
        return True
    partes = [x.lower().rstrip(". ") for x in rel.split("/") if x]
    if any(x in ("entorno", ".git", "respaldos", "__pycache__", ".claude") for x in partes):
        return True
    nombre = partes[-1] if partes else ""
    return (nombre.startswith(".env") or re.search(r"\.(db|sqlite3?)(-wal|-shm|-journal)?$", nombre) is not None
            or "umng.pdf" in nombre or nombre.startswith("enlace readme"))


ESTADO_VIDA = {"ultimo": time.time()}   # última petición recibida (para el cierre solo en modo --practica)
LATIDOS = {}   # carpeta -> última vez que una página de su app dio señales de vida
SIN_LATIDO_S = 90   # holgado: Chrome frena los temporizadores de una pestaña oculta (hasta 1 por minuto)


def vigilar_latidos():
    """Acciones con "vida": "app" lanzadas desde una app: si la app se cierra (sin latido en
    SIN_LATIDO_S segundos, o 10 s tras el aviso de cierre de la página), se detienen solas."""
    while True:
        time.sleep(5)
        ahora = time.time()
        with TRABAJOS_LOCK:
            candidatos = [t for t in TRABAJOS.values() if getattr(t, "vida_app", False) and t.activo]
        for t in candidatos:
            if ahora - LATIDOS.get(t.carpeta, t.inicio) > SIN_LATIDO_S and ahora - t.inicio > 15:
                t.cancelado = True
                if t.pid or t.proceso:
                    matar_arbol(t.pid or t.proceso.pid)
                t.poner("detenida", "Detenido: se cerró la app.")
APPS_COMUN = ESTE_ARCHIVO.parent / "apps-comun"   # _lanzador/apps-comun, servida en /comun/


def carpeta_de_app(practica):
    """Carpeta servida en /app/<carpeta>/: la del index.html de la app (campo "app")."""
    if not practica.get("app"):
        return None
    f = ruta_dentro(Config.raiz / practica["carpeta"], practica["app_declarada"])
    return f.parent if f is not None else None


def inyectar_meta(html, carpeta, carga=None):
    """A cada página de una app se le agregan el token y la carpeta: así /comun/app.js puede
    lanzar acciones sin que la app sepa nada del token.

    carga: en la página principal de la app, {"num", "titulo"} para la pantalla de carga
    "Abriendo la práctica…" (va en el HTML mismo, así se ve desde el primer instante, antes
    de que carguen el CSS, las fuentes y app.js; app.js la va avanzando y la quita)."""
    # El valor va escapado como HTML (no como JSON: "á" llegaría tal cual a app.js y una
    # carpeta con tildes no se encontraría).
    meta = (f'<meta name="probar-token" content="{Config.token}">'
            f'<meta name="probar-carpeta" content="{escapar_html(carpeta)}">')
    if carga:
        meta += CARGA_HEAD
    m = re.search(r"<head[^>]*>", html, re.I)
    html = html[:m.end()] + meta + html[m.end():] if m else meta + html
    if carga:
        div = (CARGA_DIV.replace("__NUM__", escapar_html(carga.get("num", "")))
               .replace("__TITULO__", escapar_html(carga.get("titulo", ""))))
        m = re.search(r"<body[^>]*>", html, re.I)
        html = html[:m.end()] + div + html[m.end():] if m else div + html
    return html


def escapar_html(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


# Pantalla de carga (estilo propio en línea: no depende de app.css). app.js la controla con
# App.carga(paso, fraccion) y App.cargaLista(); si app.js no llega a cargar, el script en
# línea la quita al terminar de cargar la página, y la animación CSS la quita a los 25 s
# pase lo que pase (nunca deja la app tapada).
CARGA_HEAD = """<style id="app-carga-estilo">
#app-carga{position:fixed;inset:0;z-index:5000;background:#0d1013;color:#e7e9ec;display:flex;align-items:center;justify-content:center;
font-family:"Space Grotesk",system-ui,"Segoe UI",sans-serif;transition:opacity .35s;animation:app-carga-fuera .4s 25s forwards}
#app-carga.fuera{opacity:0;pointer-events:none}
#app-carga .c{width:min(460px,calc(100vw - 32px));text-align:center}
#app-carga .n{display:inline-block;font:600 .85rem "IBM Plex Mono",Consolas,monospace;background:#4f8fce;color:#0d1013;border-radius:5px;padding:.15rem .55rem;margin-bottom:.9rem}
#app-carga h1{font-size:1.25rem;font-weight:600;margin:0 0 .3rem}
#app-carga .t{color:#8b929b;margin:0 0 1.2rem;font-size:.95rem;line-height:1.4}
#app-carga .b{height:8px;border-radius:999px;background:#0a0d10;border:1px solid #262b31;overflow:hidden}
#app-carga .b>div{height:100%;width:8%;background:#4f8fce;border-radius:999px;transition:width .4s}
#app-carga .p{font:.78rem "IBM Plex Mono",Consolas,monospace;color:#8b929b;margin:.6rem 0 0;min-height:1.2em}
@keyframes app-carga-fuera{to{opacity:0;visibility:hidden}}
</style><script>
addEventListener("load",function(){setTimeout(function(){if(!window.App){var c=document.getElementById("app-carga");if(c)c.remove();}},400);});
</script>"""
CARGA_DIV = ('<div id="app-carga" role="status" aria-live="polite"><div class="c"><div class="n">__NUM__</div>'
             '<h1>Abriendo la práctica…</h1><p class="t">__TITULO__</p><div class="b"><div id="app-carga-barra"></div></div>'
             '<p class="p" id="app-carga-paso">Cargando la página…</p></div></div>')


class Manejador(BaseHTTPRequestHandler):
    server_version = "LanzadorSensores/2.0"

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

    def redirigir(self, destino):
        self.send_response(302)
        self.send_header("Location", destino)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def host_valido(self):
        # Defensa contra "DNS rebinding": una web externa no puede hablarle a este servidor
        # aunque consiga que su dominio apunte a 127.0.0.1, porque el Host no coincidiría.
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        return host in ("127.0.0.1", "localhost")

    def origen_valido(self):
        # Además del token: si el navegador manda Origin (siempre en un POST con fetch), tiene
        # que ser este mismo servidor. Otra web abierta no puede disparar acciones.
        origen = self.headers.get("Origin")
        if not origen:
            return True
        return origen in (f"http://127.0.0.1:{Config.puerto}", f"http://localhost:{Config.puerto}")

    # Un fallo dentro de una petición nunca debe tumbar el lanzador: se responde 500 y sigue.
    def do_GET(self):
        self._sin_caerse(self._get)

    def do_POST(self):
        self._sin_caerse(self._post)

    def _sin_caerse(self, f):
        try:
            f()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            try:
                self.responder(500, {"error": f"Error inesperado del lanzador: {type(e).__name__}: {e}"})
            except Exception:
                pass

    # --- GET --------------------------------------------------------------------------
    def _get(self):
        if not self.host_valido():
            return self.responder(403, {"error": "Host no permitido"})
        ESTADO_VIDA["ultimo"] = time.time()
        ruta = urllib.parse.urlparse(self.path)
        camino = urllib.parse.unquote(ruta.path)
        q = urllib.parse.parse_qs(ruta.query)
        if camino in ("/", "/index.html"):
            return self.responder(200, INICIO_HTML, "text/html; charset=utf-8")
        if camino == "/api/ping":
            if q.get("app"):
                LATIDOS[q["app"][0]] = time.time()
            return self.responder(200, {"firma": FIRMA, "api": API_VERSION, "raiz": str(Config.raiz)})
        if camino == "/api/practicas":
            return self.responder(200, {
                "practicas": cargar_practicas(), "entornos": ESTADO_ENTORNOS,
                "python": "%d.%d.%d" % sys.version_info[:3], "pythons": PYTHONS_VISTOS,
                "build_tools": ESTADO_SISTEMA.get("build_tools"),
                "raiz": str(Config.raiz), "sistema": "windows" if ES_WINDOWS else ("mac" if ES_MAC else "linux"),
            })
        if camino.startswith("/api/practica/"):
            try:
                p = buscar_practica(camino[len("/api/practica/"):].strip("/"))
            except ErrorClaro as e:
                return self.responder(404, {"error": str(e)})
            LATIDOS[p["carpeta"]] = time.time()
            if p["carpeta"] not in ESTADO_ENTORNOS:
                revisar_entorno_de(Config.raiz / p["carpeta"])
            with TRABAJOS_LOCK:
                trabajos = [t.resumen() for t in TRABAJOS.values() if t.carpeta == p["carpeta"]]
            return self.responder(200, {
                "practica": p, "entorno": ESTADO_ENTORNOS.get(p["carpeta"]), "trabajos": trabajos,
                "python": "%d.%d.%d" % sys.version_info[:3], "pythons": PYTHONS_VISTOS,
                "build_tools": ESTADO_SISTEMA.get("build_tools"),
                "sistema": "windows" if ES_WINDOWS else ("mac" if ES_MAC else "linux"),
            })
        if camino == "/api/trabajos":
            with TRABAJOS_LOCK:
                lista = [t.a_dict() for t in TRABAJOS.values()]
            return self.responder(200, lista)
        if camino == "/api/salida":
            try:
                tid, desde = int(q.get("tid", ["0"])[0]), int(q.get("desde", ["0"])[0])
            except ValueError:
                return self.responder(400, {"error": "tid y desde deben ser números"})
            t = POR_TID.get(tid)
            if t:
                LATIDOS[t.carpeta] = time.time()
            if not t:
                return self.responder(404, {"error": "Ese trabajo ya no existe (¿se reinició el lanzador?)."})
            return self.responder(200, t.salida(desde))
        if camino.startswith("/readme/"):
            carpeta = camino[len("/readme/"):].strip("/")
            d = ruta_dentro(Config.raiz, carpeta)
            if d is None or not (d / "README.md").is_file():
                return self.responder(404, "No hay README en esa carpeta.", "text/plain; charset=utf-8")
            # json.dumps dentro de <script>: "<" escapado para que un "</script>" no cierre el bloque.
            pagina = (README_HTML.replace("__CARPETA__", json.dumps(carpeta).replace("<", "\\u003c"))
                      .replace("__CARPETA_URL__", urllib.parse.quote(carpeta))
                      .replace("__BASE__", "/repo/" + urllib.parse.quote(carpeta) + "/")
                      .replace("__GITHUB__", GITHUB + urllib.parse.quote(carpeta) + "/README.md"))
            return self.responder(200, pagina, "text/html; charset=utf-8")
        if camino.startswith("/repo/"):
            return self.servir_archivo(camino[len("/repo/"):])
        if camino.startswith("/comun/"):
            return self.servir_archivo(camino[len("/comun/"):], base=APPS_COMUN)
        if camino.startswith("/app/"):
            return self.servir_app(camino[len("/app/"):])
        return self.responder(404, {"error": "No existe"})

    def servir_app(self, resto):
        carpeta, _, rel = resto.partition("/")
        try:
            p = buscar_practica(carpeta)
        except ErrorClaro as e:
            return self.responder(404, str(e), "text/plain; charset=utf-8")
        base = carpeta_de_app(p)
        if base is None:
            # Todavía no tiene app: la página de inicio la señala (no un error).
            return self.redirigir("/?practica=" + urllib.parse.quote(carpeta) + "#p-" + urllib.parse.quote(carpeta))
        if "/" not in resto:
            # Sin la barra final, las rutas relativas de la app (./estilo.css) se romperían.
            return self.redirigir("/app/" + urllib.parse.quote(carpeta) + "/")
        if not rel:
            rel = Path(p["app_declarada"]).name
        principal = rel == Path(p["app_declarada"]).name
        carga = {"num": p["id"] if re.match(r"\d", p["carpeta"]) else "★", "titulo": p["titulo"]} if principal else None
        return self.servir_archivo(rel, base=base, carpeta_app=carpeta, carga=carga)

    def servir_archivo(self, rel, base=None, carpeta_app=None, carga=None):
        """Sirve los archivos del repo (previews HTML, imágenes, README) para que se abran por
        http://127.0.0.1 en vez de file://: Web Serial, la cámara y fetch() lo necesitan."""
        base = base or Config.raiz
        if archivo_prohibido(rel):
            return self.responder(403, "Ese archivo no se sirve (privado o del entorno).", "text/plain; charset=utf-8")
        f = ruta_dentro(base, rel)
        if f is not None and f.is_dir():
            f = f / "index.html"
        if f is None or not f.is_file():
            return self.responder(404, "No existe.", "text/plain; charset=utf-8")
        try:
            if archivo_prohibido(str(f.relative_to(Config.raiz.resolve()))):
                return self.responder(403, "Ese archivo no se sirve (privado o del entorno).", "text/plain; charset=utf-8")
        except ValueError:
            pass   # apps-comun con --raiz en otra carpeta
        tipo = MIME.get(f.suffix.lower()) or mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        if carpeta_app and f.suffix.lower() in (".html", ".htm"):
            try:
                datos = f.read_bytes()
            except OSError:
                return self.responder(500, "No se pudo leer.", "text/plain; charset=utf-8")
            datos = inyectar_meta(datos.decode("utf-8", "replace"), carpeta_app, carga).encode("utf-8")
            return self.responder(200, datos, tipo)
        self.enviar_por_partes(f, tipo)

    def enviar_por_partes(self, f, tipo):
        """Archivo en bloques y con soporte de Range (206): Chrome lo necesita para reproducir
        y adelantar un <video> mp4; así tampoco se carga un video entero en memoria."""
        try:
            tam = f.stat().st_size
            inicio, fin, codigo = 0, tam - 1, 200
            rango = (self.headers.get("Range") or "").strip()
            m = re.match(r"^bytes=(\d*)-(\d*)$", rango)
            if m and (m.group(1) or m.group(2)):
                if m.group(1):
                    inicio = int(m.group(1))
                    fin = min(int(m.group(2)), tam - 1) if m.group(2) else tam - 1
                else:   # "bytes=-500": los últimos 500
                    inicio = max(0, tam - int(m.group(2)))
                if inicio >= tam or inicio > fin:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{tam}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                codigo = 206
            largo = max(0, fin - inicio + 1)
            with open(f, "rb") as arch:
                self.send_response(codigo)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(largo))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "no-store")
                if codigo == 206:
                    self.send_header("Content-Range", f"bytes {inicio}-{fin}/{tam}")
                self.end_headers()
                arch.seek(inicio)
                falta = largo
                while falta > 0:
                    trozo = arch.read(min(262144, falta))
                    if not trozo:
                        break
                    self.wfile.write(trozo)
                    falta -= len(trozo)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass   # el navegador cortó (normal al adelantar un video)
        except OSError:
            self.responder(500, "No se pudo leer.", "text/plain; charset=utf-8")

    # --- POST -------------------------------------------------------------------------
    def _post(self):
        if not self.host_valido() or not self.origen_valido():
            return self.responder(403, {"error": "Host u origen no permitido"})
        try:
            largo = int(self.headers.get("Content-Length") or 0)
            datos = json.loads(self.rfile.read(min(largo, 65536)) or b"{}")
            if not isinstance(datos, dict):
                raise ValueError
        except (ValueError, OSError):
            return self.responder(400, {"error": "Petición mal formada."})
        camino = urllib.parse.urlparse(self.path).path
        # El token solo lo conoce la página servida por este proceso: sin él, nada se ejecuta.
        # (/api/adios llega por navigator.sendBeacon, que no puede poner cabeceras: va en el cuerpo.)
        token = str(datos.get("token", "")) if camino == "/api/adios" else self.headers.get("X-Token", "")
        if not secrets.compare_digest(token, Config.token):
            return self.responder(403, {"error": "Token inválido: recarga la página (el lanzador se reinició)."})
        ESTADO_VIDA["ultimo"] = time.time()
        try:
            if camino in ("/api/accion", "/api/detener"):
                t = iniciar_accion(str(datos.get("carpeta", "")), str(datos.get("accion", "")),
                                   detener=camino == "/api/detener", desde_app=datos.get("modo") == "app")
                return self.responder(200, t.a_dict())
            if camino == "/api/adios":
                # La página de una app se está cerrando (o recargando): si en 10 s no vuelve a
                # dar señales, sus acciones "vida": "app" se detienen.
                c = str(datos.get("carpeta", ""))
                LATIDOS[c] = time.time() - SIN_LATIDO_S + 10
                return self.responder(200, {"ok": True})
            if camino == "/api/entrada":
                t = escribir_entrada(str(datos.get("carpeta", "")), str(datos.get("accion", "")), datos.get("texto", ""))
                return self.responder(200, {"ok": True, "tid": t.tid})
            if camino == "/api/docker":
                ok, msg = comprobar_docker()
                return self.responder(200, {"ok": ok, "mensaje": msg})
            if camino == "/api/carpeta":
                practica = buscar_practica(str(datos.get("carpeta", "")))
                abrir_con_sistema(Config.raiz / practica["carpeta"])
                return self.responder(200, {"ok": True})
            if camino == "/api/ventana":
                # Abrir una app: en una ventana tipo programa si hay Edge/Chrome.
                practica = buscar_practica(str(datos.get("carpeta", "")))
                if not practica.get("app"):
                    raise ErrorClaro("Esta práctica todavía no tiene app.")
                ok = abrir_ventana(f"http://127.0.0.1:{Config.puerto}{practica['app']}", como_app=True, solo_app=True)
                return self.responder(200, {"ok": ok, "url": practica["app"]})
            if camino == "/api/salir":
                # Puede haber varias apps (o la página de inicio) usando este mismo lanzador: si algo está en
                # marcha, no se cierra sin confirmarlo.
                with TRABAJOS_LOCK:
                    activos = [t.nombre for t in TRABAJOS.values() if t.activo]
                if activos and not datos.get("forzar"):
                    return self.responder(409, {"error": "Hay acciones en marcha: " + ", ".join(activos), "activos": activos})
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
API_VERSION = 3      # 2 = con apps por práctica (/app/, /comun/, /api/salida, /api/entrada);
                     # 3 = en _lanzador/, pantalla de carga, duracion/progreso_regex, sin hub


def ping(puerto):
    """El /api/ping de un lanzador en ese puerto, o None si ahí no hay uno."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/ping", timeout=1.0) as r:
            d = json.loads(r.read().decode("utf-8"))
            return d if d.get("firma") == FIRMA else None
    except Exception:
        return None


def buscar_lanzador_abierto(preferido):
    """Un lanzador ya abierto (doble clic dos veces, o el ABRIR.bat de otra práctica) con la
    MISMA raíz y que ya sepa servir apps: se reutiliza en vez de levantar otro."""
    for puerto in range(preferido, preferido + 10):
        d = ping(puerto)
        if d and d.get("api", 1) >= API_VERSION and Path(d.get("raiz", "")).resolve() == Config.raiz.resolve():
            return puerto
    return None


class Servidor(ThreadingHTTPServer):
    # En Windows SO_REUSEADDR deja abrir un puerto que YA usa otro programa (y entonces las
    # peticiones van a parar a cualquiera de los dos): sin él, el puerto ocupado da error y se
    # prueba el siguiente.
    allow_reuse_address = not ES_WINDOWS
    daemon_threads = True


def crear_servidor(preferido):
    for puerto in [preferido, *range(preferido + 1, preferido + 30), 0]:
        try:
            return Servidor(("127.0.0.1", puerto), Manejador)
        except OSError:
            continue
    raise SystemExit("No encontré ningún puerto libre para el lanzador.")


def buscar_navegador_app():
    """Edge o Chrome, para abrir la app en una ventana propia (--app=URL), sin pestañas ni
    barra de direcciones: se ve como un programa. None si no hay (u otro sistema)."""
    if not ES_WINDOWS:
        return None
    pf = [os.environ.get(k) for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    candidatos = []
    for base in filter(None, pf):
        candidatos += [Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                       Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"]
    for c in candidatos:
        if c.is_file():
            return c
    return None


def abrir_ventana(url, como_app=True, solo_app=False):
    """Abre la URL como programa (Edge/Chrome --app) o, si no hay, en el navegador por defecto.
    solo_app: si no hay Edge/Chrome no abre nada y devuelve False (la página abre una pestaña)."""
    exe = buscar_navegador_app() if como_app else None
    if exe:
        try:
            # Ventana tipo programa, maximizada, y siempre una ventana nueva (no una pestaña en
            # una ventana ya abierta del navegador). El botón "Pantalla completa" de la app
            # (o F11) la pasa a pantalla completa.
            subprocess.Popen([str(exe), f"--app={url}", "--start-maximized", "--new-window"], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=SIN_VENTANA)
            return True
        except OSError:
            pass
    if solo_app:
        return False
    webbrowser.open(url)
    return True


def minimizar_consola():
    """En modo --practica la consola solo mantiene vivo el servidor: se minimiza para que se
    vea la app y no una ventana negra (sigue en la barra de tareas; cerrarla apaga la app)."""
    if not ES_WINDOWS:
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 6)   # SW_MINIMIZE
    except Exception:
        pass


def cerrar_si_nadie_usa(servidor, minutos):
    """Modo --practica: si en `minutos` ninguna página le habla al lanzador (las apps mandan
    un latido cada 20 s) y no hay nada en marcha, se apaga solo (no queda colgado)."""
    while True:
        time.sleep(15)
        with TRABAJOS_LOCK:
            hay_activos = any(t.activo for t in TRABAJOS.values())
        if not hay_activos and time.time() - ESTADO_VIDA["ultimo"] > minutos * 60:
            print(f"Nadie usa la app desde hace {minutos} minutos: cierro el lanzador.")
            servidor.shutdown()
            return


def destino_practica(carpeta):
    """Ruta a abrir para --practica: la app si existe; si no, la página de inicio que la señala."""
    p = buscar_practica(carpeta)
    return p["app"] or ("/?practica=" + urllib.parse.quote(p["carpeta"]) + "#p-" + urllib.parse.quote(p["carpeta"])), bool(p["app"])


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
        app = "con app" if p["app"] else "sin app todavía"
        print(f"[{marca}] {p['carpeta']}: {p['titulo']} ({len(p['acciones'])} acciones, {app})")
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
    ap.add_argument("--practica", help="abre la app de esa práctica (nombre de su carpeta)")
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

    destino, es_app = "/", False
    if args.practica:
        nombre = args.practica.strip().strip("\\/").replace("\\", "/").split("/")[-1]
        try:
            destino, es_app = destino_practica(nombre)
        except ErrorClaro:
            print(f"No hay ninguna práctica \"{nombre}\" con probar.json en {Config.raiz}.")
            print("Prácticas disponibles: " + ", ".join(d.name for d in carpetas_con_manifiesto()))
            sys.exit(1)

    abierto = buscar_lanzador_abierto(args.puerto)
    if abierto:
        url = f"http://127.0.0.1:{abierto}{destino}"
        print(f"El lanzador ya estaba abierto: abro {url}")
        if not args.no_navegador:
            abrir_ventana(url, como_app=es_app)
        return

    servidor = crear_servidor(args.puerto)
    Config.puerto = servidor.server_address[1]
    url = f"http://127.0.0.1:{Config.puerto}{destino}"
    al_cerrar_la_consola()
    threading.Thread(target=revisar_entornos_en_segundo_plano, args=(nombre if args.practica else None,),
                     daemon=True).start()
    threading.Thread(target=vigilar_latidos, daemon=True).start()
    threading.Thread(target=lambda: PYTHONS_VISTOS.extend(versiones_instaladas()), daemon=True).start()
    if ES_WINDOWS:
        threading.Thread(target=lambda: ESTADO_SISTEMA.update(build_tools=buscar_build_tools() is not None),
                         daemon=True).start()
    if args.practica:
        print("Sensores-Teoria · " + (f"app de la práctica {args.practica}" if es_app
                                      else f"práctica {args.practica} (todavía sin app propia)"))
        print(f"  Página: {url}")
        print("  Esta ventana mantiene la app funcionando: déjala abierta (minimizada) mientras la usas.")
        print("  Para cerrar: cierra esta ventana. Si nadie usa la app en 10 minutos, se cierra sola.")
        if not args.no_navegador:   # con --no-navegador (pruebas) no se cierra solo
            threading.Thread(target=cerrar_si_nadie_usa, args=(servidor, 10), daemon=True).start()
    else:
        print("Lanzador de Sensores-Teoria (sin --practica)")
        print("  Cada práctica se abre con doble clic en el ABRIR.bat de su carpeta.")
        print(f"  Página con los enlaces a las {len(carpetas_con_manifiesto())} apps: {url}")
        print("  Ciérrala con Ctrl+C o cerrando esta ventana.")
    if not args.no_navegador:
        abrir_ventana(url, como_app=es_app)
        if args.practica:
            minimizar_consola()
    try:
        servidor.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        n = detener_trabajos_de_app()
        servidor.server_close()
        print("Lanzador cerrado." + (f" Detuve {n} programa(s) que seguían en marcha." if n else ""))


# --------------------------------------------------------------------------------------
# Página de inicio mínima (sin --practica): ya no hay "hub"; cada práctica se abre desde su
# ABRIR.bat. Esta página solo enlaza las apps (útil para saltar de una a otra).
# --------------------------------------------------------------------------------------

INICIO_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prácticas de Sensores-Teoria</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root { --bg: #0d1013; --panel: #15191d; --borde: #262b31; --texto: #e7e9ec; --tenue: #8b929b; --acento: #4f8fce; --amarillo: #e8b930; }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: var(--bg); color: var(--texto); font-family: "Space Grotesk", system-ui, "Segoe UI", sans-serif; }
  main { max-width: 860px; margin: 0 auto; padding: 2rem 16px 3rem; }
  h1 { font-size: 1.35rem; margin: 0 0 0.4rem; }
  p.sub { color: var(--tenue); margin: 0 0 1.4rem; line-height: 1.55; }
  p.sub b { color: var(--texto); font-weight: 500; }
  ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }
  li { display: flex; align-items: center; gap: 0.8rem; background: var(--panel); border: 1px solid var(--borde); border-radius: 8px; padding: 0.65rem 0.8rem; flex-wrap: wrap; }
  li.resaltada { border-color: var(--acento); }
  .num { font-family: "IBM Plex Mono", monospace; font-size: 0.75rem; font-weight: 600; background: var(--acento); color: var(--bg); border-radius: 4px; padding: 0.1rem 0.45rem; min-width: 1.8rem; text-align: center; }
  .final .num { background: var(--amarillo); }
  .tit { flex: 1 1 280px; min-width: 0; }
  .tit small { display: block; font-family: "IBM Plex Mono", monospace; font-size: 0.68rem; color: var(--tenue); }
  a.btn { font-family: "IBM Plex Mono", monospace; font-size: 0.75rem; color: var(--acento); text-decoration: none; border: 1px solid var(--borde); border-radius: 6px; padding: 0.35rem 0.7rem; white-space: nowrap; }
  a.btn:hover { border-color: var(--acento); }
  .nota { margin-top: 1.4rem; font-size: 0.82rem; color: var(--tenue); }
</style>
</head>
<body>
<main>
  <h1>Prácticas de Sensores-Teoria</h1>
  <p class="sub">Cada práctica se abre con <b>doble clic en el <code>ABRIR.bat</code> de su carpeta</b> (en Linux/Mac,
    <code>sh abrir.sh</code>): se abre su app, con lo que pide la actividad, cómo funciona y un botón por cada prueba.
    Esta página solo enlaza las apps de este lanzador, por si se quiere saltar de una a otra.</p>
  <ul id="lista"><li>Cargando…</li></ul>
  <p class="nota" id="nota"></p>
</main>
<script>
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pedida = new URLSearchParams(location.search).get("practica");
fetch("/api/practicas").then((r) => r.json()).then((d) => {
  document.getElementById("lista").innerHTML = d.practicas.map((p) => {
    const final = !/^\d/.test(p.carpeta);
    return `<li class="${final ? "final" : ""} ${p.carpeta === pedida ? "resaltada" : ""}"><span class="num">${esc(final ? "★" : p.id)}</span>
      <span class="tit">${esc(p.titulo)}<small>${esc(p.carpeta)}/ABRIR.bat</small></span>
      ${p.app ? `<a class="btn" href="${esc(p.app)}">Abrir la app</a>` : `<span class="tit"><small>todavía sin app</small></span>`}
      ${p.readme ? `<a class="btn" href="/readme/${encodeURIComponent(p.carpeta)}">README</a>` : ""}</li>`;
  }).join("");
  if (pedida) document.getElementById("nota").textContent = `La práctica "${pedida}" todavía no tiene app propia: su README explica cómo probarla.`;
}).catch(() => { document.getElementById("lista").innerHTML = "<li>El lanzador no responde: vuelve a abrir la práctica con su ABRIR.bat.</li>"; });
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
<div class="barra"><a href="/app/__CARPETA_URL__/">← volver a la app</a><a href="__GITHUB__" target="_blank" rel="noopener">ver en GitHub</a></div>
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
  // Anclas como en GitHub (marked ya no pone id a los títulos): minúsculas, sin puntuación
  // (las tildes se quedan), espacios -> "-", y -1, -2... si se repite. Ver _lanzador/revisar_enlaces.py.
  const vistos = {};
  for (const h of main.querySelectorAll("h1,h2,h3,h4,h5,h6")) {
    const base = h.textContent.trim().toLowerCase().replace(/[^\p{L}\p{M}\p{N}\p{Pc} -]/gu, "").replace(/ /g, "-");
    h.id = vistos[base] ? `${base}-${vistos[base]}` : base; vistos[base] = (vistos[base] || 0) + 1;
  }
  // Con <base href> un enlace "#ancla" iría a /repo/<carpeta>/#ancla (otra página): se resuelve aquí.
  main.addEventListener("click", (ev) => {
    const a = ev.target.closest && ev.target.closest("a[href^='#']");
    if (!a) return;
    ev.preventDefault();
    const id = decodeURIComponent(a.getAttribute("href").slice(1));
    const destino = document.getElementById(id);
    if (destino) { destino.scrollIntoView({ behavior: "smooth" }); history.replaceState(null, "", "#" + encodeURIComponent(id)); }
  });
  if (window.mermaid) { mermaid.initialize({ startOnLoad: false, theme: "default" }); try { await mermaid.run(); } catch (e) {} }
  if (location.hash) { const d = document.getElementById(decodeURIComponent(location.hash.slice(1))); if (d) d.scrollIntoView(); }
}).catch(() => { document.getElementById("md").textContent = "No se pudo leer el README."; });
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
