"""Asistente del proyecto (fase 7, CLAUDE.md seccion 14).

Misma idea que el tema 4 del repositorio (4-chatbot-asistente-voz/comando_voz.py):
una frase en palabras normales (escrita o dicha) va a la API de DeepSeek, que
responde SOLO con un objeto JSON; el programa valida ese JSON y recien ahi
actua. Aca el JSON trae dos cosas:

    {"respuesta": "texto para la persona",
     "acciones": [{"cmd": "carro", "accion": "avanzar", "distancia_m": 0.3}, ...]}

- `respuesta`: contesta con los datos del proyecto. Para eso, en cada pregunta
  se le manda (1) el estado EN VIVO de la corrida sacado de SQLite (totales,
  monedas por denominacion, rechazos por causa, vasos, carro, alarmas, lo que
  acaba de pasar) y (2) la documentacion del proyecto que tiene que ver con la
  pregunta. "Lee todo el proyecto" por busqueda: todos los documentos (README,
  CLAUDE.md, docs/*.md, la configuracion) se parten en secciones y se mandan las
  que mas palabras comparten con la pregunta. Mandar los ~300 kB completos en
  cada pregunta seria lento y caro, y no mejora la respuesta.
- `acciones`: ordenes para la linea o el carro, las MISMAS que dejan los botones
  del dashboard en la tabla `ordenes` (el supervisor las valida otra vez; el
  carro, una tercera vez). El modelo nunca mueve nada directamente: si propone
  algo que no esta en la lista blanca de abajo, se descarta.

Sin clave de DeepSeek o sin internet (el dia de la sustentacion la red del
salon puede fallar), un interprete LOCAL entiende las ordenes y las preguntas
basicas con expresiones regulares, y para lo demas muestra la parte de la
documentacion que mas se parece a la pregunta. Asi el asistente nunca queda
mudo.

Regla de la seccion 14: nunca inventa cifras. Las cifras salen del estado
inyectado; si una no esta, dice que no tiene ese dato.

Este modulo no importa Streamlit: lo usa el dashboard y se puede probar solo.
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
URL_DEEPSEEK = "https://api.deepseek.com"
MODELO = os.environ.get("DEEPSEEK_MODELO", "deepseek-chat")

# Documentos que el asistente puede consultar (todo lo escrito del proyecto).
DOCUMENTOS = ["README.md", "CLAUDE.md", "docs/paso-a-paso.md", "docs/sensores.md", "docs/componentes.md",
              "docs/conexiones.md", "docs/replicacion.md", "docs/revision-final.md", "docs/costos.md",
              "docs/bitacora.md",
              "config/parametros.yaml", "config/monedas.yaml"]
MAX_CARACTERES_DOCS = 24000      # ~7000 tokens de documentacion por pregunta
# Proveedor LOCAL (usuario, 2026-09-27): Ollama con un modelo chico en el mismo portatil, para
# probar el asistente sin internet ni clave. El modelo vive en la carpeta del usuario (.ollama),
# FUERA del proyecto: no pesa en GitHub. Ollama habla el mismo formato de OpenAI, asi que se usa
# el mismo cliente, el mismo prompt, el mismo JSON y la misma lista blanca que con DeepSeek.
URL_LOCAL = os.environ.get("ASISTENTE_URL_LOCAL", "http://localhost:11434")
# `qwen2.5-proyecto` = qwen2.5:3b con 8192 tokens de contexto (Ollama trae ~4000 por defecto),
# creado con `python -m app.asistente --preparar-local`. Si no existe, se usa el de base.
MODELO_LOCAL = os.environ.get("ASISTENTE_MODELO_LOCAL", "qwen2.5-proyecto")
MODELO_LOCAL_BASE = "qwen2.5:3b"
# Ollama usa por defecto un contexto de ~4000 tokens: si el prompt lo pasa, se corta POR EL
# PRINCIPIO y el modelo pierde las instrucciones (se vio: respondia sin la clave "respuesta").
# Por eso al modelo local va menos: sin el README y con ~3000 caracteres de documentacion.
MAX_CARACTERES_DOCS_LOCAL = 9000   # con 8192 tokens de contexto (medido: 3,5 de 4 GB en la RTX 3050)
MAX_CARACTERES_DOCS_LOCAL_BASE = 3000
MAX_SECCION = 3500
TURNOS_DE_MEMORIA = 6            # preguntas y respuestas anteriores que se le recuerdan

DENOMINACIONES = (50, 100, 200, 500, 1000)


# ---------------------------------------------------------------------
# ordenes permitidas (lista blanca)
# ---------------------------------------------------------------------

ACCIONES_CARRO = {
    "detener": {},
    "avanzar": {"distancia_m": (0.01, 1.5)},
    "retroceder": {"distancia_m": (0.01, 0.30)},
    "girar": {"grados": (-180.0, 180.0)},
    "ir_a": {"x": (-1.0, 4.0), "y": (-3.0, 2.0)},
    "ir_meta": {},
    "volver_muelle": {},
    "seguir_linea": {},
}
ORDENES_LINEA = {
    "iniciar": {},
    "pausar": {},
    "reanudar": {},
    "paro": {},
    "embalar_parciales": {},
    "lote": {"valor": (1, 25)},
    "velocidad": {"valor": (0.25, 8.0)},
}


def validar_accion(a: dict) -> tuple[dict | None, str]:
    """Devuelve (orden lista para la tabla `ordenes`, "") o (None, motivo).
    Todo numero fuera de rango o accion desconocida se descarta."""
    if not isinstance(a, dict):
        return None, "no es un objeto"
    cmd = a.get("cmd")
    if cmd == "carro":
        accion = a.get("accion")
        if accion not in ACCIONES_CARRO:
            return None, f"acción del carro desconocida: {accion}"
        limpia = {"cmd": "carro", "accion": accion}
        campos = ACCIONES_CARRO[accion]
    elif cmd in ORDENES_LINEA:
        limpia = {"cmd": cmd}
        campos = ORDENES_LINEA[cmd]
    else:
        return None, f"orden desconocida: {cmd}"
    for nombre, (minimo, maximo) in campos.items():
        try:
            valor = float(a[nombre])
        except (KeyError, TypeError, ValueError):
            return None, f"a '{cmd} {a.get('accion', '')}' le falta '{nombre}'"
        if not math.isfinite(valor) or not minimo <= valor <= maximo:
            return None, f"'{nombre}' = {valor:g} está fuera de {minimo:g}…{maximo:g}"
        limpia[nombre] = int(valor) if cmd == "lote" else round(valor, 3)
    if cmd == "carro" and accion == "girar" and limpia["grados"] == 0:
        return None, "un giro de 0 grados no hace nada"
    if cmd == "iniciar":
        limpia["escenario"] = "prueba_completa"
    limpia["origen"] = "asistente"
    return limpia, ""


# ---------------------------------------------------------------------
# conocimiento: los documentos del proyecto, partidos en secciones
# ---------------------------------------------------------------------

_PALABRAS_VACIAS = set("""
el la los las un una unos unas de del al a en y o u que por para con sin se su sus es son lo le les como
mas pero muy ya hay este esta estos estas ese esa eso cual cuales cuanto cuanta cuantos cuantas donde cuando
porque sobre entre tiene tienen fue ser hace hacer puede pueden cada todo toda todos todas otro otra me mi
yo tu usted nos qué cómo dónde cuándo cuál
""".split())


def normalizar(texto: str) -> str:
    """minusculas y sin tildes (la busqueda no depende de como se escriba)."""
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _palabras(texto: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9_]+", normalizar(texto)) if len(w) >= 3 and w not in _PALABRAS_VACIAS]


@dataclass
class Seccion:
    archivo: str
    titulo: str
    texto: str
    palabras: set[str] = field(default_factory=set)


def _partir(archivo: str, texto: str) -> list[Seccion]:
    """Markdown: por titulos (#, ##, ###). YAML: por claves de primer nivel o
    por puntos del paso a paso. Las secciones largas se cortan."""
    if archivo.endswith(".md"):
        patron = re.compile(r"^#{1,3} .*$", re.M)
    else:
        patron = re.compile(r"^(?:[a-z_]+:|  - numero:).*$", re.M)
    cortes = [m.start() for m in patron.finditer(texto)] or [0]
    if cortes[0] != 0:
        cortes.insert(0, 0)
    secciones = []
    for i, ini in enumerate(cortes):
        trozo = texto[ini:cortes[i + 1] if i + 1 < len(cortes) else len(texto)].strip()
        if not trozo:
            continue
        titulo = trozo.splitlines()[0].lstrip("# ").strip()[:90]
        for k in range(0, len(trozo), MAX_SECCION):
            parte = trozo[k:k + MAX_SECCION]
            secciones.append(Seccion(archivo, titulo if k == 0 else f"{titulo} (sigue)", parte))
    return secciones


_CORPUS: list[Seccion] | None = None
_IDF: dict[str, float] = {}


def corpus(recargar: bool = False) -> list[Seccion]:
    """Todas las secciones de todos los documentos (se lee una vez)."""
    global _CORPUS, _IDF
    if _CORPUS is None or recargar:
        secciones = []
        for rel in DOCUMENTOS:
            ruta = RAIZ / rel
            if ruta.exists():
                secciones += _partir(rel, ruta.read_text(encoding="utf-8"))
        for s in secciones:
            s.palabras = set(_palabras(s.titulo + " " + s.texto))
        n = len(secciones) or 1
        df: dict[str, int] = {}
        for s in secciones:
            for w in s.palabras:
                df[w] = df.get(w, 0) + 1
        _IDF = {w: math.log(n / c) for w, c in df.items()}
        _CORPUS = secciones
    return _CORPUS


def buscar(pregunta: str, limite_caracteres: int = MAX_CARACTERES_DOCS) -> list[Seccion]:
    """Las secciones que mas palabras (poco comunes) comparten con la pregunta."""
    secciones = corpus()
    q = set(_palabras(pregunta))
    if not q:
        return []
    puntaje = []
    for s in secciones:
        comunes = q & s.palabras
        if comunes:
            p = sum(_IDF.get(w, 0) for w in comunes)
            # El titulo pesa el doble: una seccion que SE LLAMA como la pregunta.
            p += sum(_IDF.get(w, 0) for w in comunes & set(_palabras(s.titulo)))
            puntaje.append((p, s))
    puntaje.sort(key=lambda x: -x[0])
    elegidas, total = [], 0
    for _, s in puntaje:
        if total + len(s.texto) > limite_caracteres:
            continue
        elegidas.append(s)
        total += len(s.texto)
    return elegidas


# ---------------------------------------------------------------------
# estado en vivo (de SQLite)
# ---------------------------------------------------------------------


def estado_en_vivo(conexion: sqlite3.Connection) -> dict:
    """Lo que el asistente sabe de la corrida en curso. Solo cifras que
    estan en la base: si algo no esta, no aparece (y el asistente dice que
    no tiene ese dato)."""
    fila = conexion.execute("SELECT ts, payload FROM eventos WHERE tipo = 'tel' ORDER BY id DESC LIMIT 1").fetchone()
    tel = json.loads(fila["payload"]) if fila else {}
    acept = conexion.execute(
        "SELECT denominacion, COUNT(*) AS n, COALESCE(SUM(valor),0) AS v, COALESCE(SUM(masa_estimada_g),0) AS g "
        "FROM elementos WHERE veredicto = 'aceptada' GROUP BY denominacion").fetchall()
    rech = conexion.execute(
        "SELECT causa, COUNT(*) AS n FROM elementos WHERE veredicto = 'rechazada' GROUP BY causa").fetchall()
    vasos = conexion.execute("SELECT estado, COUNT(*) AS n, COALESCE(SUM(valor_total),0) AS v FROM vasos "
                             "GROUP BY estado").fetchall()
    entregados = conexion.execute(
        "SELECT COUNT(*) FROM eventos WHERE origen = 'carro' AND tipo = 'entregado'").fetchone()[0]
    evasiones = conexion.execute("SELECT COUNT(*) FROM ruta WHERE evento_obstaculo = 'evasion'").fetchone()[0]
    puntos = conexion.execute("SELECT posicion_x, posicion_y FROM ruta WHERE evento_obstaculo IS NULL "
                              "ORDER BY id").fetchall()
    distancia = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(puntos, puntos[1:]))
    recientes = conexion.execute(
        "SELECT ts, origen, tipo, payload FROM eventos WHERE tipo NOT IN ('tel', 'paso', 'orden', 'espera') "
        "ORDER BY id DESC LIMIT 25").fetchall()

    por_denominacion = {str(f["denominacion"]): {"monedas": f["n"], "valor_pesos": f["v"],
                                                 "peso_estimado_g": round(f["g"], 1)} for f in acept}
    carro = tel.get("carro")
    if carro:
        carro = {k: carro.get(k) for k in ("estado", "fase", "x", "y", "rumbo", "odometria", "vaso_id",
                                           "inclinacion_vaso_grados", "ultima_orden", "radio")}
    return {
        "hay_datos": bool(fila),
        "hora_ultimo_dato": fila["ts"] if fila else None,
        "estado_linea": tel.get("linea"),
        "ciclo": tel.get("tick"),
        "velocidad_simulacion": tel.get("velocidad"),
        "monedas_por_vaso": tel.get("monedas_por_vaso"),
        "piezas_por_cargar": tel.get("pendientes"),
        "totales": {
            "monedas_aceptadas": sum(f["n"] for f in acept),
            "valor_aceptado_pesos": sum(f["v"] for f in acept),
            "peso_estimado_g": round(sum(f["g"] for f in acept), 1),
            "nota_peso": "estimado por conteo (masa nominal de cada moneda reconocida); no hay balanza",
            "piezas_rechazadas": sum(f["n"] for f in rech),
            "vasos_entregados_en_meta": entregados,
        },
        "aceptadas_por_denominacion": por_denominacion,
        "rechazos_por_causa": {f["causa"]: f["n"] for f in rech},
        "vasos_por_estado": {f["estado"]: {"vasos": f["n"], "valor_pesos": f["v"]} for f in vasos},
        "almacen_tubos": tel.get("almacen"),
        "almacen_valor_pesos": tel.get("almacen_valor"),
        "canaleta_vasos_esperando": len(tel.get("canaleta") or []),
        "tapas_restantes": tel.get("tapas_restantes"),
        "cortina_activa": tel.get("cortina_activa"),
        "alarmas": tel.get("alarmas"),
        "errores_del_filtro": tel.get("errores_filtrado"),
        "carro": carro,
        "ruta": {"distancia_recorrida_m": round(distancia, 2), "evasiones": evasiones},
        "ultima_orden": tel.get("ultima_orden"),
        "ultimos_eventos": [f"{r['ts'][11:19]} {r['origen']}.{r['tipo']} {r['payload'][:160]}" for r in recientes],
    }


# ---------------------------------------------------------------------
# la conversacion (tabla `asistente`: la ven el dashboard y el visor 3D)
# ---------------------------------------------------------------------


def guardar_mensaje(conexion: sqlite3.Connection, rol: str, texto: str, *, modo: str = "",
                    acciones: list | None = None) -> None:
    from app import db

    conexion.execute("INSERT INTO asistente (ts, rol, texto, modo, acciones) VALUES (?, ?, ?, ?, ?)",
                     (db.ahora(), rol, texto, modo, json.dumps(acciones or [], ensure_ascii=False)))
    conexion.commit()


def marcar_pensando(conexion: sqlite3.Connection, proveedor: str | None, pregunta: str = "") -> None:
    """Deja escrito quien esta pensando (el visor lo anima); None = nadie."""
    from app import db

    conexion.execute("INSERT OR REPLACE INTO asistente_pensando (id, proveedor, pregunta, desde) VALUES (1, ?, ?, ?)",
                     (proveedor, pregunta[:200], db.ahora()))
    conexion.commit()


def pensando(conexion: sqlite3.Connection) -> dict | None:
    f = conexion.execute("SELECT proveedor, pregunta, desde FROM asistente_pensando WHERE id = 1").fetchone()
    return dict(f) if f and f["proveedor"] else None


def conversacion(conexion: sqlite3.Connection, limite: int = 40) -> list[dict]:
    filas = conexion.execute("SELECT ts, rol, texto, modo, acciones FROM asistente ORDER BY id DESC LIMIT ?",
                             (limite,)).fetchall()
    return [dict(f, acciones=json.loads(f["acciones"] or "[]")) for f in reversed(filas)]


def borrar_conversacion(conexion: sqlite3.Connection) -> None:
    conexion.execute("DELETE FROM asistente")
    conexion.commit()


# ---------------------------------------------------------------------
# DeepSeek
# ---------------------------------------------------------------------

PROMPT_SISTEMA = """
Eres el asistente del "Sistema de Logística de Monedas Inteligentes" (proyecto del segundo corte de
Micros y Laboratorio, Ingeniería Mecatrónica, UMNG; grupo con el elemento 7: detector de elementos de
monedas y vasos). Hablas español de Colombia, claro y breve, para alguien que puede no conocer el sistema.

Recibes: (1) ESTADO_EN_VIVO, un JSON con las cifras reales de la corrida actual; (2) DOCUMENTACION, las
secciones del proyecto relacionadas con la pregunta; (3) la frase de la persona.

Responde ÚNICAMENTE con un objeto JSON, sin texto antes ni después:
{"respuesta": "<texto para la persona>", "acciones": [ ...órdenes... ]}

Reglas:
- Nunca inventes cifras. Toda cifra de la corrida sale de ESTADO_EN_VIVO; si no está, di que no tienes ese
  dato. Lo técnico (sensores, pines, medidas, decisiones) sale de DOCUMENTACION; si no está, dilo.
- "acciones" va vacío si la persona solo pregunta. Solo agrega órdenes si la persona pide hacer algo.
  Órdenes posibles (exactamente estas):
  {"cmd":"carro","accion":"detener"}
  {"cmd":"carro","accion":"avanzar","distancia_m":0.3}      (0.01 a 1.5 m, hacia adelante, despacio)
  {"cmd":"carro","accion":"retroceder","distancia_m":0.1}   (0.01 a 0.3 m: atrás no tiene sensor)
  {"cmd":"carro","accion":"girar","grados":90}              (-180 a 180; positivo = izquierda)
  {"cmd":"carro","accion":"ir_a","x":1.2,"y":-0.5}           (metros, coordenadas de la pista)
  {"cmd":"carro","accion":"ir_meta"}      {"cmd":"carro","accion":"volver_muelle"}
  {"cmd":"carro","accion":"seguir_linea"} (retomar el recorrido automático)
  {"cmd":"pausar"} {"cmd":"reanudar"} {"cmd":"paro"} {"cmd":"iniciar"} {"cmd":"embalar_parciales"}
  {"cmd":"lote","valor":10} (monedas por vaso)   {"cmd":"velocidad","valor":2} (0.25 a 8)
- Varias órdenes seguidas se ejecutan en orden, pero una orden nueva al carro reemplaza la anterior: para
  una secuencia de movimientos del carro, manda solo la primera y explica que la siguiente se pide después.
- Si preguntan por una medida que ningún sensor del proyecto mide EN VIVO (temperatura, voltaje o
  corriente de algo, humedad...), di claramente que no hay un sensor que la mida y que no tienes ese
  dato; puedes dar el valor NOMINAL de la documentación, aclarando que no es una medición.
- Una pregunta (¿...?) nunca da órdenes: "acciones" va vacío.
- El carro no choca: antes de moverse mira el camino, y si ve algo adelante se detiene; si la persona pide
  algo que lo haría chocar o salir de la pista, explícalo. Las cm se pasan a metros.
- En "respuesta": si es una orden, una o dos frases diciendo qué vas a hacer. Si es una pregunta,
  de 2 a 6 frases completas: la respuesta directa primero, con las cifras exactas de ESTADO_EN_VIVO
  (con sus unidades) o los datos de DOCUMENTACION, y después el porqué o el detalle útil. Nunca
  contestes una pregunta con una sola frase: agrega qué significa la cifra, de dónde sale (qué
  sensor, estación o archivo) y un dato relacionado del estado o de la documentación. No nombres
  campos internos (ESTADO_EN_VIVO, claves del JSON como valor_aceptado_pesos): habla como persona.
"""


def cliente_deepseek():
    """Cliente de la API (formato de OpenAI) o None si no hay clave. La clave
    va en la variable de entorno DEEPSEEK_API_KEY o en un archivo .env en la
    raiz del proyecto (ignorado por git), como en el tema 4."""
    try:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
    except ImportError:
        pass
    clave = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not clave:
        return None
    from openai import OpenAI

    return OpenAI(api_key=clave, base_url=URL_DEEPSEEK, timeout=40, max_retries=1)


def cliente_local():
    """Cliente de Ollama (si esta corriendo y tiene el modelo), o None."""
    import urllib.request

    try:
        with urllib.request.urlopen(URL_LOCAL + "/api/tags", timeout=0.8) as r:
            modelos = [m["name"] for m in json.loads(r.read()).get("models", [])]
    except (OSError, ValueError):
        return None
    global MODELO_LOCAL
    nombres = {m.split(":")[0] if m.endswith(":latest") else m for m in modelos}
    if MODELO_LOCAL not in nombres:
        if MODELO_LOCAL_BASE not in nombres:
            return None
        MODELO_LOCAL = MODELO_LOCAL_BASE           # sin el de contexto largo: el de base
    from openai import OpenAI

    return OpenAI(api_key="ollama", base_url=URL_LOCAL + "/v1", timeout=90, max_retries=0)


def preguntar_deepseek(cliente, pregunta: str, estado: dict, historial: list[dict]) -> dict:
    """Una pregunta a DeepSeek. Devuelve {"respuesta", "acciones", "documentos"}."""
    return preguntar_llm(cliente, MODELO, pregunta, estado, historial)


def preguntar_llm(cliente, modelo: str, pregunta: str, estado: dict, historial: list[dict],
                  limite_docs: int = MAX_CARACTERES_DOCS, con_readme: bool = True, dato_verificado: str = "") -> dict:
    """Una pregunta a un modelo con API de OpenAI (DeepSeek u Ollama). `dato_verificado`: la
    respuesta exacta que ya calcularon las reglas (el modelo la amplia, no la recalcula)."""
    docs = buscar(pregunta, limite_docs)
    readme = ((RAIZ / "README.md").read_text(encoding="utf-8")
              if con_readme and (RAIZ / "README.md").exists() else "")
    documentacion = readme + "\n\n" + "\n\n".join(f"[{s.archivo} · {s.titulo}]\n{s.texto}" for s in docs
                                                  if s.archivo != "README.md")
    mensajes = [{"role": "system", "content": PROMPT_SISTEMA}]
    for m in historial[-2 * TURNOS_DE_MEMORIA:]:
        mensajes.append({"role": "user" if m["rol"] == "usuario" else "assistant", "content": m["texto"]})
    # Documentacion primero y el estado en vivo pegado a la pregunta: un modelo chico se
    # "pierde" si las cifras quedan al principio de un texto largo (se vio en las pruebas).
    mensajes.append({"role": "user", "content": (
        "DOCUMENTACION:\n" + documentacion
        + "\n\nESTADO_EN_VIVO (cifras reales de la corrida):\n" + json.dumps(estado, ensure_ascii=False)
        + ("\n\nDATO VERIFICADO (cifras exactas, úsalas tal cual y amplía la explicación):\n" + dato_verificado
           if dato_verificado else "")
        + "\n\nFRASE DE LA PERSONA:\n" + pregunta)})
    r = cliente.chat.completions.create(model=modelo, messages=mensajes, response_format={"type": "json_object"},
                                        temperature=0.2, max_tokens=900)
    datos = json.loads(r.choices[0].message.content or "{}")
    if not isinstance(datos, dict):
        datos = {}
    texto = datos.get("respuesta")
    if not isinstance(texto, str) or not texto.strip():
        # Un modelo chico a veces cambia el nombre de la clave: el primer texto que traiga.
        texto = next((v for v in datos.values() if isinstance(v, str) and v.strip()), "")
    return {"respuesta": texto.strip() or "(sin respuesta)",
            "acciones": datos.get("acciones") or [], "documentos": [f"{s.archivo} · {s.titulo}" for s in docs[:6]]}


# ---------------------------------------------------------------------
# interprete local (sin internet)
# ---------------------------------------------------------------------

_NUM = r"(-?\d+(?:[.,]\d+)?)"


def _num(t: str) -> float:
    return float(t.replace(",", "."))


def _distancia_m(texto: str) -> float | None:
    m = re.search(_NUM + r"\s*(cm|centimetros?|m|metros?|mm|milimetros?)?\b", texto)
    if not m:
        return None
    v, u = _num(m.group(1)), (m.group(2) or "cm")
    return v / 100 if u.startswith("c") else v / 1000 if u.startswith("mm") or u.startswith("mili") else v


def es_pregunta(frase: str) -> bool:
    t = normalizar(frase).strip()
    return "?" in t or "¿" in frase or bool(re.match(r"(cuant|que |como |donde |cual|por ?que|quien|cuando |how |what |where )", t))


# Pide un movimiento del carro (si no, una orden al carro de un modelo chico se descarta).
PIDE_MOVIMIENTO = re.compile(r"\b(muev|avanz|abanz|avans|retroce|reversa|gir|volte|rota|media vuelta|ve |ir |vaya|anda|"
                             r"lleva|vuelv|regres|deten|det[eé]n|frena|para el|pare|quieto|sigue|retoma|meta|muelle|punto)")


# Medidas que ningun sensor del proyecto toma en vivo.
SIN_SENSOR = re.compile(r"\b(temperatura|voltaje|tension|corriente|humedad)\b")


def interpretar_orden_local(frase: str) -> list[dict]:
    """Ordenes con expresiones regulares (sin DeepSeek). Devuelve la lista de
    ordenes crudas (despues se validan igual que las de DeepSeek)."""
    t = normalizar(frase).strip()
    # Una pregunta nunca mueve nada ("¿cuantos vasos llegaron a la meta?").
    if es_pregunta(frase):
        return []
    carro = re.search(r"\b(carro|vehiculo|carrito|robot)\b", t)
    if re.search(r"\bparo( de emergencia)?\b|\bemergencia\b", t):
        return [{"cmd": "paro"}]
    if re.search(r"\b(deten|detente|detener|frena|frenar|quieto|para el|pare el|stop)\b", t):
        return [{"cmd": "carro", "accion": "detener"}] if carro or "linea" not in t else [{"cmd": "pausar"}]
    if re.search(r"\b(meta)\b", t) and re.search(r"\b(ve|ir|vaya|lleva|llevar|anda|hasta|a la)\b", t):
        return [{"cmd": "carro", "accion": "ir_meta"}]
    if re.search(r"\b(muelle|base|casa|inicio)\b", t) and re.search(r"\b(vuelve|volver|regresa|regresar|ve|ir|vaya)\b", t):
        return [{"cmd": "carro", "accion": "volver_muelle"}]
    if re.search(r"\b(sigue|seguir|retoma|retomar)\b.*\b(linea|ruta|recorrido|cinta)\b", t):
        return [{"cmd": "carro", "accion": "seguir_linea"}]
    m = re.search(r"\bx\s*=?\s*" + _NUM + r".*?\by\s*=?\s*" + _NUM, t) or \
        re.search(r"\(\s*" + _NUM + r"\s*[,;]\s*" + _NUM + r"\s*\)", t)
    if m and re.search(r"\b(ve|ir|vaya|anda|lleva|posicion|punto|a)\b", t):
        return [{"cmd": "carro", "accion": "ir_a", "x": _num(m.group(1)), "y": _num(m.group(2))}]
    if re.search(r"\b(gira|girar|voltea|voltear|rota|rotar|da la vuelta|media vuelta)\b", t):
        if "media vuelta" in t or "da la vuelta" in t:
            return [{"cmd": "carro", "accion": "girar", "grados": 180}]
        g = re.search(_NUM + r"\s*(?:grados?|°)?", t)
        grados = _num(g.group(1)) if g else 90.0
        if "derech" in t:
            grados = -abs(grados)
        return [{"cmd": "carro", "accion": "girar", "grados": grados}]
    if re.search(r"\b(avanza|avanzar|abanza|abanzar|avansa|avansar|adelante|muevete|mueve|camina)\b", t):
        return [{"cmd": "carro", "accion": "avanzar", "distancia_m": _distancia_m(t) or 0.2}]
    if re.search(r"\b(retrocede|retroceder|atras|reversa)\b", t):
        return [{"cmd": "carro", "accion": "retroceder", "distancia_m": _distancia_m(t) or 0.1}]
    if re.search(r"\b(pausa|pausar|pausala)\b", t):
        return [{"cmd": "pausar"}]
    if re.search(r"\b(reanuda|reanudar|continua|continuar|sigue la linea de produccion)\b", t):
        return [{"cmd": "reanudar"}]
    if re.search(r"\b(inicia|iniciar|empieza|empezar|arranca|arrancar)\b.*\b(corrida|prueba|linea)\b", t):
        return [{"cmd": "iniciar"}]
    if re.search(r"\b(empaca|empacar|embala|embalar)\b", t):
        return [{"cmd": "embalar_parciales"}]
    m = re.search(r"\blote\b.*?" + _NUM, t) or re.search(_NUM + r"\s*monedas por vaso", t)
    if m:
        return [{"cmd": "lote", "valor": _num(m.group(1))}]
    m = re.search(r"\bvelocidad\b.*?" + _NUM, t)
    if m:
        return [{"cmd": "velocidad", "valor": _num(m.group(1))}]
    return []


def _pesos(v) -> str:
    return f"${int(v or 0):,}".replace(",", ".")


NOMBRE_CAUSA = {"no_metalico": "no metálico", "fuera_de_rango": "fuera de rango", "no_circular": "no circular",
                "perforado": "perforado", "no_reconocida": "no reconocida", "incoherente": "incoherente"}
ESTADO_CARRO = {"siguiendo": "siguiendo la línea", "maniobra": "maniobrando", "en_meta": "en la meta",
                "esperando_carga": "en el muelle", "detenido": "detenido", "manual": "cumpliendo una orden",
                "esperando_orden": "quieto, esperando otra orden"}


def responder_local(frase: str, estado: dict) -> str:
    """Preguntas basicas con las cifras del estado (sin DeepSeek)."""
    t = normalizar(frase)
    if re.search(r"\b(costo|costos|cuesta|cuestan|precio|precios|presupuesto|barato|abaratar|ahorrar|ahorro)", t):
        from app import costos

        subs = sorted(costos.por_subsistema().items(), key=lambda x: -x[1])
        mejores = costos.ahorros()[:3]
        return (f"El proyecto cuesta {costos.pesos(costos.total())} en Colombia (precios del "
                f"{costos.cargar()['consultado']}, sin el portátil). Lo más caro: "
                + ", ".join(f"{n} {costos.pesos(v)}" for n, v in subs[:3]) + ". Dónde ahorrar: "
                + "; ".join(f"{a['titulo']} ({costos.pesos(a['ahorro'])}, riesgo {a['riesgo']})" for a in mejores)
                + ". Detalle en docs/costos.md.")
    if not estado.get("hay_datos"):
        return "Todavía no hay datos de ninguna corrida: empiece una desde la barra de la izquierda."
    tot = estado["totales"]
    partes = []
    if re.search(r"\b(dinero|plata|valor|pesos|cuanto se ha|money)\b", t):
        partes.append(f"Valor aceptado: {_pesos(tot['valor_aceptado_pesos'])} en {tot['monedas_aceptadas']} monedas; "
                      f"en el almacén hay {_pesos(estado.get('almacen_valor_pesos'))} guardados.")
    if re.search(r"\b(moneda|monedas|denominacion|denominaciones|coins)\b", t) and re.search(r"\b(cuant|total|how many)", t):
        por = estado["aceptadas_por_denominacion"]
        detalle = ", ".join(f"{d['monedas']} de {_pesos(int(k))}" for k, d in sorted(por.items(), key=lambda x: int(x[0])))
        partes.append(f"Monedas aceptadas: {tot['monedas_aceptadas']}" + (f" ({detalle})." if detalle else "."))
    if re.search(r"\b(peso|pesa|pesan|gramos|masa)\b", t):
        partes.append(f"Peso estimado: {tot['peso_estimado_g']} g ({tot['nota_peso']}).")
    if re.search(r"\b(rechaz|rechazo|rechazos|rechazadas|causa|causas|filtro|filtros)", t):
        causas = estado["rechazos_por_causa"]
        detalle = ", ".join(f"{NOMBRE_CAUSA.get(c, c)}: {n}" for c, n in causas.items())
        partes.append(f"Piezas rechazadas: {tot['piezas_rechazadas']}" + (f" ({detalle})." if detalle else "."))
    if re.search(r"\b(vaso|vasos)\b", t):
        partes.append(f"Vasos entregados en la meta: {tot['vasos_entregados_en_meta']}; "
                      f"esperando en la canaleta: {estado['canaleta_vasos_esperando']}.")
    if re.search(r"\b(confianza|umbral)\b", t):
        from app import configuracion

        c = configuracion.cargar_parametros()["filtrado"]["confianza_minima"]
        partes.append(f"La cámara acepta una moneda solo si la reconoce con confianza de al menos {c:.2f} "
                      f"({c * 100:.0f} %); por debajo se rechaza como «no reconocida».")
    if SIN_SENSOR.search(t):
        partes.append("No hay un sensor que mida eso en vivo, así que no tengo ese dato (solo los valores "
                      "nominales de la documentación).")
    if re.search(r"\b(carro|vehiculo|donde esta|ruta|obstaculo|obstaculos)\b", t) and \
            re.search(r"\b(donde|estado|posicion|ubicacion|cuant|recorr)", t):
        c = estado.get("carro")
        if c:
            partes.append(f"El carro está {ESTADO_CARRO.get(c['estado'], c['estado'])} en ({c['x']:.2f}, {c['y']:.2f}) m"
                          + (f", con el vaso {c['vaso_id']}" if c.get("vaso_id") else "")
                          + f"; lleva {estado['ruta']['distancia_recorrida_m']} m y {estado['ruta']['evasiones']} evasiones.")
        else:
            partes.append("En esta corrida no hay carro con física.")
    if re.search(r"\b(alarma|alarmas|problema|falla)\b", t):
        al = estado.get("alarmas") or []
        partes.append("Alarmas: " + (", ".join(a.replace("_", " ") for a in al) if al else "ninguna") + ".")
    if re.search(r"\b(estado|como va|linea)\b", t) and not partes:
        partes.append(f"La línea está {estado.get('estado_linea')}, ciclo {estado.get('ciclo')}; "
                      f"faltan {estado.get('piezas_por_cargar')} piezas por cargar.")
    if partes:
        return " ".join(partes)
    docs = buscar(frase, 4000)
    if docs:
        s = docs[0]
        extracto = re.sub(r"\s+", " ", s.texto)[:700]
        return (f"Sin DeepSeek solo entiendo órdenes y preguntas básicas de la corrida. Lo más relacionado "
                f"que encontré en la documentación ({s.archivo}, «{s.titulo}»): {extracto}…")
    return "No tengo ese dato. Sin DeepSeek entiendo órdenes (p. ej. «avanza 30 cm») y preguntas básicas."


# ---------------------------------------------------------------------
# punto de entrada
# ---------------------------------------------------------------------


@dataclass
class Respuesta:
    texto: str
    modo: str                                  # "deepseek", "ollama" o "local" (reglas)
    ordenes: list[dict] = field(default_factory=list)   # validas: van a la tabla `ordenes`
    descartadas: list[str] = field(default_factory=list)
    documentos: list[str] = field(default_factory=list)
    aviso: str = ""


def atender(frase: str, conexion: sqlite3.Connection, *, usar: str = "auto", usar_deepseek: bool = True,
            cliente=None, cliente_ia_local=None) -> Respuesta:
    """Atiende una frase y guarda la conversacion. Proveedores, en orden:
    DeepSeek (si hay clave y responde) -> modelo LOCAL de Ollama (si esta
    corriendo) -> interprete de reglas (siempre). `usar`: "auto", "deepseek",
    "ollama" o "reglas" (para probar uno solo). NO deja las ordenes en la
    tabla: eso lo hace quien llama (el dashboard), para que la persona vea
    que se va a hacer."""
    if not usar_deepseek:
        usar = "reglas"
    estado = estado_en_vivo(conexion)
    historial = conversacion(conexion, 2 * TURNOS_DE_MEMORIA)
    avisos = []
    crudo = None
    if usar in ("auto", "deepseek"):
        if cliente is None and usar == "auto" and cliente_deepseek() is not None and not hay_internet():
            avisos.append("Sin internet: no se consulta DeepSeek.")
            cliente = False
        cliente = cliente if cliente is not None else cliente_deepseek()
        if cliente is False:
            pass
        elif cliente is None:
            avisos.append("Sin clave de DeepSeek (DEEPSEEK_API_KEY).")
        else:
            try:
                marcar_pensando(conexion, "deepseek", frase)
                crudo = preguntar_deepseek(cliente, frase, estado, historial)
                modo = "deepseek"
            except Exception as error:  # red caida, clave rechazada, JSON roto...
                avisos.append(f"DeepSeek no respondió ({type(error).__name__}: {str(error)[:90]}).")
    if crudo is None and usar in ("auto", "ollama") and SIN_SENSOR.search(normalizar(frase)):
        # Medidas que ningun sensor toma: las reglas lo dicen sin inventar (el modelo local
        # contestaba "7,4 V en este momento", que es el valor nominal, no una medicion).
        crudo = {"respuesta": responder_local(frase, estado), "acciones": [], "documentos": []}
        modo = "local"
    if crudo is None and usar in ("auto", "ollama") and interpretar_orden_local(frase):
        # Una orden clara la decide el interprete de reglas (siempre igual), no el modelo
        # chico: en las pruebas, "gira 45 grados a la derecha" le hizo inventar 4 ordenes
        # seguidas. El modelo local se usa para lo que hace bien: responder preguntas.
        ordenes = interpretar_orden_local(frase)
        crudo = {"respuesta": describir_ordenes(ordenes), "acciones": ordenes, "documentos": []}
        modo = "local"
    if crudo is None and usar in ("auto", "ollama"):
        local = cliente_ia_local or cliente_local()
        if local is None:
            avisos.append(f"El modelo local ({MODELO_LOCAL}) no está corriendo (Ollama).")
        else:
            try:
                marcar_pensando(conexion, "ollama", frase)
                # Menos contexto: pocos eventos, menos historial y menos documentacion.
                compacto = {k: v for k, v in estado.items() if k not in ("ultimos_eventos", "errores_del_filtro")}
                limite = MAX_CARACTERES_DOCS_LOCAL if MODELO_LOCAL != MODELO_LOCAL_BASE else MAX_CARACTERES_DOCS_LOCAL_BASE
                # Si las reglas ya tienen la cifra exacta, va como dato verificado: el modelo chico
                # confundia "cuanto pesan" (gramos) con pesos colombianos.
                regla = responder_local(frase, estado) if estado.get("hay_datos") else ""
                verificado = "" if regla.startswith(("Sin DeepSeek", "No tengo")) else regla
                crudo = preguntar_llm(local, MODELO_LOCAL, frase, compacto, historial[-2:], limite, con_readme=False,
                                      dato_verificado=verificado)
                modo = "ollama"
            except Exception as error:
                avisos.append(f"El modelo local no respondió ({type(error).__name__}: {str(error)[:90]}).")
    marcar_pensando(conexion, None)
    aviso = " ".join(avisos + (["Respondo con el intérprete de reglas."] if crudo is None and avisos else []))
    if crudo is None:
        ordenes = interpretar_orden_local(frase)
        texto = (describir_ordenes(ordenes) if ordenes else responder_local(frase, estado))
        crudo = {"respuesta": texto, "acciones": ordenes, "documentos": []}
        modo = "local"
    validas, descartadas = [], []
    carro_ya = False
    if es_pregunta(frase) and crudo["acciones"]:
        # Una pregunta nunca mueve nada (en las pruebas, "¿cuántos vasos llegaron a la meta?" hizo
        # que el modelo local mandara el carro a un punto).
        descartadas.append("una pregunta no da órdenes")
        crudo["acciones"] = []
    if modo == "ollama" and not PIDE_MOVIMIENTO.search(normalizar(frase)):
        quitadas = [a for a in crudo["acciones"] if isinstance(a, dict) and a.get("cmd") == "carro"]
        if quitadas:
            descartadas.append("el modelo local propuso mover el carro sin que se lo pidieran")
            crudo["acciones"] = [a for a in crudo["acciones"] if a not in quitadas]
    for a in corregir_giros(frase, crudo["acciones"] if isinstance(crudo["acciones"], list) else []):
        orden, motivo = validar_accion(a)
        if orden and orden["cmd"] == "carro" and carro_ya:
            # Una orden nueva al carro reemplaza a la anterior: mandar varias en el mismo
            # mensaje solo dejaria la ultima. Se cumple la primera; las demas se piden despues.
            descartadas.append(f"{orden['accion']}: una sola orden al carro por mensaje")
            continue
        if orden:
            carro_ya = carro_ya or orden["cmd"] == "carro"
            validas.append(orden)
        else:
            descartadas.append(motivo)
    guardar_mensaje(conexion, "usuario", frase)
    guardar_mensaje(conexion, "asistente", crudo["respuesta"], modo=modo, acciones=validas)
    return Respuesta(crudo["respuesta"], modo, validas, descartadas, crudo.get("documentos", []), aviso)


# ---------------------------------------------------------------------
# internet y voz (usuario, 2026-09-28: la voz tiene que funcionar SIN internet)
# ---------------------------------------------------------------------
#
# Con internet se usa lo del tema 4: reconocimiento de Google en es-CO y respuesta con gTTS.
# Sin internet (o si Google falla), todo en el mismo portatil:
# - Oir: Whisper (faster-whisper, modelo "small", ~480 MB). Se descarga UNA vez en la carpeta del
#   usuario (~/.cache/huggingface), fuera del proyecto, con `python -m app.asistente --preparar-voz`.
#   Probado con frases del proyecto: "base" oia "abanza" y "muye"; "small" las escribe bien, con
#   tildes, y tarda ~0,1 s por frase ya cargado (la primera vez, ~10 s en cargarse).
# - Hablar: las voces de Windows (SAPI, p. ej. "Microsoft Helena", es-ES) con pyttsx3. Corre en un
#   proceso aparte: pyttsx3 se cuelga si se llama dos veces en el mismo proceso, y Streamlit atiende
#   cada interaccion en otro hilo (la voz de Windows es COM y quiere su propio hilo inicializado).

MODELO_VOZ = os.environ.get("ASISTENTE_MODELO_VOZ", "small")
_internet = {"t": 0.0, "hay": False}
_whisper = {}


def hay_internet(cada_s: float = 15.0) -> bool:
    """True si se alcanza internet (se revisa como mucho cada `cada_s` segundos).
    Abre una conexion TCP (sin mandar nada) a DeepSeek o, si no, a Google: sin red
    falla en milisegundos (no hay DNS) y con una red sin salida, al 1,5 s."""
    import socket
    import time

    ahora = time.monotonic()
    if _internet["t"] and ahora - _internet["t"] < cada_s:
        return _internet["hay"]
    hay = False
    for host in ("api.deepseek.com", "www.google.com"):
        try:
            socket.create_connection((host, 443), timeout=1.5).close()
            hay = True
            break
        except OSError:
            continue
    _internet.update(t=ahora, hay=hay)
    return hay


def _whisper_modelo():
    if "modelo" not in _whisper:
        from faster_whisper import WhisperModel

        # CPU e int8: no compite con el modelo de lenguaje por los 4 GB de la GPU.
        _whisper["modelo"] = WhisperModel(MODELO_VOZ, device="cpu", compute_type="int8")
    return _whisper["modelo"]


def transcribir_local(audio_wav: bytes) -> str:
    """Audio -> texto con Whisper en el portatil (sin internet)."""
    import io

    segmentos, _ = _whisper_modelo().transcribe(
        io.BytesIO(audio_wav), language="es", beam_size=1, vad_filter=True,
        # Palabras del proyecto que una frase suelta no le deja adivinar.
        initial_prompt="Carro, muelle, meta, línea, monedas, vasos, canaleta, centímetros, grados.")
    return " ".join(s.text.strip() for s in segmentos).strip()


def transcribir(audio_wav: bytes) -> tuple[str | None, str]:
    """Audio del microfono (WAV, lo que da st.audio_input) -> texto.
    Devuelve (texto, quien lo reconocio) o (None, motivo si fallo).
    Con internet, Google (como el tema 4); sin internet o si falla, Whisper local."""
    import io

    motivos = []
    if hay_internet():
        try:
            import speech_recognition as sr

            reconocedor = sr.Recognizer()
            reconocedor.operation_timeout = 8
            with sr.AudioFile(io.BytesIO(audio_wav)) as fuente:
                audio = reconocedor.record(fuente)
            return reconocedor.recognize_google(audio, language="es-CO"), "Google"
        except ImportError:
            motivos.append("falta SpeechRecognition")
        except Exception as error:  # sin respuesta de Google, audio que no entendio...
            motivos.append(f"Google: {type(error).__name__}")
    try:
        texto = transcribir_local(audio_wav)
    except ImportError:
        return None, "Sin internet y sin el reconocimiento local (pip install faster-whisper)."
    except Exception as error:
        return None, f"No se pudo transcribir ({'; '.join(motivos + [str(error)[:80]])})."
    if not texto:
        return None, "No se entendió el audio."
    return texto, "Whisper local (sin internet)"


def _limpiar_para_voz(texto: str) -> str:
    return re.sub(r"<[^>]+>|[*_`#]", "", texto)[:600]


def voz_local(texto: str) -> bytes | None:
    """Texto -> WAV con una voz de Windows en espanol, en un proceso aparte."""
    import subprocess
    import sys
    import tempfile

    ruta = Path(tempfile.gettempdir()) / f"asistente_voz_{os.getpid()}.wav"
    try:
        ruta.unlink(missing_ok=True)
        subprocess.run([sys.executable, "-m", "app.asistente", "--decir", str(ruta)], cwd=RAIZ,
                       input=_limpiar_para_voz(texto), text=True, encoding="utf-8", timeout=60,
                       capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return ruta.read_bytes() if ruta.exists() and ruta.stat().st_size > 1000 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _decir_a_archivo(ruta: str, texto: str) -> None:
    """Lo que corre el proceso aparte de voz_local."""
    import pyttsx3

    motor = pyttsx3.init()
    voces = motor.getProperty("voices")
    espanol = [v for v in voces if "spanish" in v.name.lower() or "es-" in v.id.lower() or "es_" in v.id.lower()
               or any(n in v.name.lower() for n in ("helena", "sabina", "laura", "pablo", "raul"))]
    if espanol:
        motor.setProperty("voice", espanol[0].id)
    motor.setProperty("rate", 175)
    motor.save_to_file(texto, ruta)
    motor.runAndWait()


def voz(texto: str) -> tuple[bytes, str] | None:
    """Texto -> (audio, formato "mp3"|"wav"). Con internet gTTS (acento colombiano);
    sin internet, la voz de Windows. None si no se pudo."""
    import io

    if hay_internet():
        try:
            from gtts import gTTS

            buf = io.BytesIO()
            gTTS(_limpiar_para_voz(texto), lang="es", tld="com.co", timeout=8).write_to_fp(buf)
            return buf.getvalue(), "mp3"
        except Exception:  # Google no respondio: se sigue con la voz local
            pass
    wav = voz_local(texto)
    return (wav, "wav") if wav else None


def preparar_voz() -> str:
    """Descarga el modelo de Whisper (una vez, necesita internet) y prueba la voz de Windows."""
    _whisper_modelo()
    wav = voz_local("Listo. El asistente ya puede oír y hablar sin internet.")
    return (f"Whisper '{MODELO_VOZ}' listo. Voz de Windows: "
            + ("lista." if wav else "no se pudo generar (¿pyttsx3 instalado?)."))


def corregir_giros(frase: str, acciones: list) -> list:
    """Un modelo chico a veces se equivoca con el signo del giro (se vio: "a la
    derecha" -> +45). Si la frase dice el lado, manda la frase: derecha =
    negativo, izquierda = positivo (misma convencion que el carro)."""
    t = normalizar(frase)
    lado = -1 if "derech" in t else 1 if "izquierd" in t else 0
    out = []
    for a in acciones:
        if lado and isinstance(a, dict) and a.get("accion") == "girar":
            try:
                a = dict(a, grados=lado * abs(float(a.get("grados", 0))))
            except (TypeError, ValueError):
                pass
        out.append(a)
    return out


def precargar_local() -> None:
    """Carga el modelo local en la GPU en segundo plano (la primera respuesta
    tarda ~1 min si el modelo no esta cargado). No hace nada si Ollama no esta."""
    import threading
    import urllib.request

    def _cargar():
        try:
            datos = json.dumps({"model": MODELO_LOCAL, "prompt": "", "keep_alive": "30m"}).encode()
            urllib.request.urlopen(urllib.request.Request(URL_LOCAL + "/api/generate", data=datos), timeout=120).read()
        except OSError:
            pass

    threading.Thread(target=_cargar, daemon=True).start()


def describir_ordenes(ordenes: list[dict]) -> str:
    textos = []
    for o in ordenes:
        if o["cmd"] == "carro":
            a = o["accion"]
            textos.append({
                "detener": "Detengo el carro.",
                "avanzar": f"El carro avanza {float(o.get('distancia_m', 0)) * 100:.0f} cm (mira el camino antes).",
                "retroceder": f"El carro retrocede {float(o.get('distancia_m', 0)) * 100:.0f} cm.",
                "girar": f"El carro gira {abs(float(o.get('grados', 0))):.0f}° a la "
                         f"{'izquierda' if float(o.get('grados', 0)) > 0 else 'derecha'}.",
                "ir_a": f"El carro va al punto ({o.get('x')}, {o.get('y')}) m.",
                "ir_meta": "El carro va a la meta siguiendo la línea.",
                "volver_muelle": "El carro vuelve al muelle.",
                "seguir_linea": "El carro retoma la línea.",
            }.get(a, a))
        else:
            textos.append({"pausar": "Pauso la línea.", "reanudar": "La línea sigue.", "paro": "PARO de emergencia.",
                           "iniciar": "Empiezo una corrida nueva.", "embalar_parciales": "Empaco lo guardado.",
                           "lote": f"Lote de {o.get('valor')} monedas por vaso.",
                           "velocidad": f"Velocidad ×{o.get('valor')}."}.get(o["cmd"], o["cmd"]))
    return " ".join(textos)


def preparar_local() -> str:
    """Crea en Ollama `qwen2.5-proyecto` (qwen2.5:3b con 8192 tokens de contexto). Una vez."""
    import subprocess
    import tempfile

    ollama = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe") if os.name == "nt" else "ollama"
    with tempfile.NamedTemporaryFile("w", suffix=".Modelfile", delete=False, encoding="utf-8") as f:
        f.write(f"FROM {MODELO_LOCAL_BASE}\nPARAMETER num_ctx 8192\nPARAMETER temperature 0.2\n")
    r = subprocess.run([ollama, "create", "qwen2.5-proyecto", "-f", f.name], capture_output=True, text=True)
    return r.stdout + r.stderr


if __name__ == "__main__":
    import sys

    if "--preparar-local" in sys.argv:
        print(preparar_local())
    if "--preparar-voz" in sys.argv:
        print(preparar_voz())
    if "--decir" in sys.argv:
        _decir_a_archivo(sys.argv[sys.argv.index("--decir") + 1], sys.stdin.read())
