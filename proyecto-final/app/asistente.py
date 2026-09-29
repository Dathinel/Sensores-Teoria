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

Foco (usuario, 2026-09-28): la especialidad del asistente es el filtrado de monedas (elemento 7) y
el movimiento del carro; lo demas tambien lo responde. Eso se nota en el prompt de sistema, en el
peso de la busqueda (factor_foco), en el orden del estado en vivo (monedas, carro, lo demas) y en las
reglas (rechazos con su causa, denominaciones, almacen, ultima inspeccion, donde esta el carro).
Como funciona el modelo local por dentro y por que se eligio: docs/modelo-local.md.

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
              # Documentos del 2026-09-28 (si todavia no existen, se saltan).
              "docs/logica-interna.md", "docs/electrica.md", "docs/peso.md", "docs/modelo-local.md",
              "docs/fisica-vs-3d.md",
              "config/parametros.yaml", "config/monedas.yaml"]
MAX_CARACTERES_DOCS = 24000      # ~7000 tokens de documentacion por pregunta
# Proveedor LOCAL (usuario, 2026-09-27): Ollama con un modelo chico en el mismo portatil, para
# probar el asistente sin internet ni clave. El modelo (~1,9 GB, Q4_K_M) vive FUERA del proyecto,
# en la carpeta que diga OLLAMA_MODELS (en este portatil, D:\cosas uni\Micros\instalados): no pesa
# en GitHub. Explicacion completa del modelo y de como se usa: docs/modelo-local.md. Ollama habla el mismo formato de OpenAI, asi que se usa
# el mismo cliente, el mismo prompt, el mismo JSON y la misma lista blanca que con DeepSeek.
URL_LOCAL = os.environ.get("ASISTENTE_URL_LOCAL", "http://localhost:11434")
# `qwen2.5-proyecto` = qwen2.5:3b con 8192 tokens de contexto (Ollama trae ~4000 por defecto),
# creado con `python -m app.asistente --preparar-local`. Si no existe, se usa el de base.
MODELO_LOCAL = os.environ.get("ASISTENTE_MODELO_LOCAL", "qwen2.5-proyecto")
MODELO_LOCAL_BASE = "qwen2.5:3b"
# Ollama usa por defecto un contexto de ~4000 tokens: si el prompt lo pasa, se corta POR EL
# PRINCIPIO y el modelo pierde las instrucciones (se vio: respondia sin la clave "respuesta").
# Por eso al modelo local va menos: sin el README; con el contexto subido a 8192 tokens
# (qwen2.5-proyecto) caben ~9000 caracteres de documentacion (3000 con el modelo base).
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
def _capacidad_tubo() -> int:
    """El lote no puede pasar de lo que cabe en un tubo (config: planta.capacidad_tubo). Antes el
    tope era un 25 escrito a mano: si el tubo del CAD cambia, el asistente seguia aceptando lotes
    que nunca se completan (un lote de 40 en un tubo de 25 = `tubo_lleno` para siempre)."""
    try:
        from app.configuracion import cargar_parametros

        return int(cargar_parametros()["planta"]["capacidad_tubo"])
    except Exception:   # sin config legible, el valor documentado (CLAUDE.md, seccion 5)
        return 25


ORDENES_LINEA = {
    "iniciar": {},
    "pausar": {},
    "reanudar": {},
    "paro": {},
    "embalar_parciales": {},
    "lote": {"valor": (1, _capacidad_tubo())},
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
        if cmd == "lote" and valor != int(valor):
            # "10.5 monedas por vaso" no existe: se rechaza en vez de truncar en silencio.
            return None, f"el lote tiene que ser un número entero de monedas (llegó {valor:g})"
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
    foco: float = 1.0          # peso extra por tratar de monedas o del carro (factor_foco)


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
                # Los cuadritos de color de las tablas de cables (<span style=...>■</span>) no le
                # dicen nada al modelo y gastan contexto: se quitan.
                texto = re.sub(r"<span[^>]*>■</span>", "", ruta.read_text(encoding="utf-8"))
                secciones += _partir(rel, texto)
        for s in secciones:
            s.palabras = set(_palabras(s.titulo + " " + s.texto))
            s.foco = factor_foco(s)
        n = len(secciones) or 1
        df: dict[str, int] = {}
        for s in secciones:
            for w in s.palabras:
                df[w] = df.get(w, 0) + 1
        _IDF = {w: math.log(n / c) for w, c in df.items()}
        _CORPUS = secciones
    return _CORPUS


# Foco del grupo (usuario, 2026-09-28: "LLM enfocado a la parte de monedas y movimiento del carro
# pero sin dejar de lado lo demas"). El elemento 7 es el filtrado de monedas, y el carro es lo que
# mas se le pide al asistente. Las secciones que TRATAN de eso (su titulo lo dice) pesan un poco
# mas en la busqueda; las demas no se excluyen: una pregunta de costos sigue trayendo costos,
# porque el peso extra solo multiplica un puntaje que ya existe (sin palabras en comun, 0 x 1,3 = 0).
FOCO_MONEDAS = re.compile(r"moneda|filtr|rechaz|capacitiv|inductiv|vision|camara|diametro|circular|perfora|"
                          r"confianza|coheren|denominaci|familia|almacen|revolver|lote|clasific")
FOCO_CARRO = re.compile(r"carro|vehiculo|ruta|odometr|evasi|obstacul|muelle|\bmeta\b|encoder|ultrason|acople")
PESO_FOCO = 1.3               # la seccion SE LLAMA como un tema del foco


def factor_foco(s: Seccion) -> float:
    """Cuanto se multiplica el puntaje de una seccion por tratar del foco del grupo. Solo cuenta el
    TITULO (de que trata la seccion); la bitacora no, porque sus titulos resumen una sesion entera
    ("carro mas rapido y proyecto reorganizado") y le ganaban a secciones de verdad (se vio: costos)."""
    if s.archivo == "docs/bitacora.md":
        return 1.0
    titulo = normalizar(s.titulo)
    return PESO_FOCO if FOCO_MONEDAS.search(titulo) or FOCO_CARRO.search(titulo) else 1.0


def buscar(pregunta: str, limite_caracteres: int = MAX_CARACTERES_DOCS) -> list[Seccion]:
    """Las secciones que mas palabras (poco comunes) comparten con la pregunta, con un peso
    extra para las de monedas/filtros/rechazos y carro/ruta (`factor_foco`)."""
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
            puntaje.append((p * s.foco, s))
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


def viajes_del_carro(conexion: sqlite3.Connection) -> dict:
    """Cuanto se demora el carro: la MISMA cuenta que la pestana Carro del dashboard
    (app/dashboard/datos.py, viajes_del_carro), sin pandas. Un viaje empieza con `carga` (sale del
    muelle con el vaso), la ida termina en `meta` y el viaje completo en el `en_muelle` siguiente.
    Antes el asistente no tenia este dato y contestaba "¿qué tanto se demora el carro?" con
    vaguedades aunque el dashboard mostraba ~154 s por viaje."""
    from datetime import datetime

    viajes, actual = [], None
    for f in conexion.execute("SELECT ts, tipo FROM eventos WHERE origen = 'carro' AND tipo IN "
                              "('carga', 'meta', 'en_muelle') ORDER BY id").fetchall():
        t = datetime.fromisoformat(f["ts"])
        if f["tipo"] == "carga":
            actual = {"sale": t, "meta": None, "vuelve": None}
            viajes.append(actual)
        elif actual is not None:
            if f["tipo"] == "meta" and actual["meta"] is None:
                actual["meta"] = t
            elif f["tipo"] == "en_muelle" and actual["meta"] is not None and actual["vuelve"] is None:
                actual["vuelve"] = t
    idas = [(v["meta"] - v["sale"]).total_seconds() for v in viajes if v["meta"]]
    completos = [(v["vuelve"] - v["sale"]).total_seconds() for v in viajes if v["vuelve"]]
    return {
        "viajes_empezados": len(viajes),
        "viajes_completos": len(completos),
        "ultimo_viaje_completo_s": round(completos[-1]) if completos else None,
        "promedio_viaje_completo_s": round(sum(completos) / len(completos)) if completos else None,
        "ultima_ida_a_la_meta_s": round(idas[-1]) if idas else None,
        "promedio_ida_a_la_meta_s": round(sum(idas) / len(idas)) if idas else None,
    }


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

    # Lo ultimo que vio la camara (E3) y los ultimos rechazos: con esto el asistente puede
    # contestar "que fue lo ultimo que reviso la camara" o "por que rechazo la ultima pieza".
    vision = conexion.execute("SELECT ts, payload FROM eventos WHERE origen = 'e3' AND tipo = 'vision' "
                              "ORDER BY id DESC LIMIT 1").fetchone()
    ultima_vision = None
    if vision:
        v = json.loads(vision["payload"])
        ultima_vision = {k: v.get(k) for k in ("casilla", "diametro_mm", "circularidad", "contornos_internos",
                                               "clase", "confianza", "combinacion", "veredicto", "causa")}
        ultima_vision["hora"] = vision["ts"][11:19]
    ultimos_rechazos = [{"casilla": f["casilla"], "causa": f["causa"], "hora": (f["ts"] or "")[11:19]}
                        for f in conexion.execute("SELECT casilla, causa, ts FROM elementos WHERE veredicto = "
                                                  "'rechazada' ORDER BY id DESC LIMIT 5").fetchall()]
    eventos_carro = [f"{r['ts'][11:19]} {r['tipo']}" for r in conexion.execute(
        "SELECT ts, tipo FROM eventos WHERE origen = 'carro' AND tipo NOT IN ('estado', 'tel') "
        "ORDER BY id DESC LIMIT 6").fetchall()]

    por_denominacion = {str(f["denominacion"]): {"monedas": f["n"], "valor_pesos": f["v"],
                                                 "peso_estimado_g": round(f["g"], 1)} for f in acept}
    carro = tel.get("carro")
    if carro:
        carro = {k: carro.get(k) for k in ("estado", "fase", "x", "y", "rumbo", "odometria", "vaso_id",
                                           "inclinacion_vaso_grados", "ultima_orden", "radio")}
        carro["que_hace"] = ESTADO_CARRO.get(carro["estado"], carro["estado"])
        carro["ultimos_eventos"] = eventos_carro
    # ORDEN de las claves = orden en que el modelo las lee (el JSON va tal cual): primero lo de
    # las monedas (elemento 7, la especialidad del grupo), despues el carro y al final lo demas.
    return {
        "hay_datos": bool(fila),
        "hora_ultimo_dato": fila["ts"] if fila else None,
        # --- monedas: filtrado, rechazos y almacen
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
        "ultimos_rechazos": ultimos_rechazos,
        "ultima_inspeccion_camara": ultima_vision,
        "confianza_minima": tel.get("confianza_minima"),
        "errores_del_filtro": tel.get("errores_filtrado"),
        "almacen_tubos": tel.get("almacen"),
        "almacen_valor_pesos": tel.get("almacen_valor"),
        "monedas_por_vaso": tel.get("monedas_por_vaso"),
        # --- carro y ruta
        "carro": carro,
        "ruta": {"distancia_recorrida_m": round(distancia, 2), "evasiones": evasiones,
                 "tiempos_de_viaje": viajes_del_carro(conexion)},
        # --- lo demas: linea, vasos, seguridad
        "estado_linea": tel.get("linea"),
        "ciclo": tel.get("tick"),
        "velocidad_simulacion": tel.get("velocidad"),
        "piezas_por_cargar": tel.get("pendientes"),
        "vasos_por_estado": {f["estado"]: {"vasos": f["n"], "valor_pesos": f["v"]} for f in vasos},
        # Los vacios desechados quedan "rechazada" en la tabla vasos: aqui se cuentan aparte.
        "vasos_vacios_desechados": conexion.execute(
            "SELECT COUNT(*) FROM eventos WHERE tipo = 'descarga' "
            "AND json_extract(payload, '$.destino') = 'vacio'").fetchone()[0],
        "canaleta_vasos_esperando": len(tel.get("canaleta") or []),
        "tapas_restantes": tel.get("tapas_restantes"),
        "cortina_activa": tel.get("cortina_activa"),
        "alarmas": tel.get("alarmas"),
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

_PLANTILLA_PROMPT = """
Eres el asistente del "Sistema de Logística de Monedas Inteligentes" (proyecto del segundo corte de
Micros y Laboratorio, Ingeniería Mecatrónica, UMNG; grupo con el elemento 7: detector de elementos de
monedas y vasos). Hablas español de Colombia, claro y breve, para alguien que puede no conocer el sistema.

TU ESPECIALIDAD (responde esto con más detalle que lo demás):
1. El FILTRADO DE MONEDAS, que es la parte del grupo (elemento 7). La cinta de monedas tiene 4 estaciones:
   E1 presencia (infrarrojo: ¿hay algo en la casilla?); E2 material (capacitivo + inductivo debajo de la
   cinta: capacitivo solo = no metálico, rechazo "no_metalico"); E3 visión (cámara cenital, dos fotos:
   diámetro en mm fuera de {dmin}-{dmax} = "fuera_de_rango", circularidad < {circ} = "no_circular", agujeros o
   contornos internos = "perforado", clase "otro" o confianza < {conf} = "no_reconocida", diámetro que
   no coincide con la denominación reconocida (> {coh} mm) = "incoherente"); E4 descarga (una compuerta
   manda lo aceptado al tubo de su denominación en el almacén revólver y TODO rechazo a una sola bandeja).
   Denominaciones 50, 100, 200, 500 y 1000 de la familia nueva y la antigua; cada vaso lleva UNA sola
   denominación, en lotes (monedas por vaso); lo que no completa lote queda guardado en su tubo. El peso
   es ESTIMADO por conteo (no hay balanza ni celda de carga). Al hablar de rechazos, di la causa en
   palabras y qué estación la detecta.
2. El MOVIMIENTO DEL CARRO: sus órdenes (abajo), la odometría con encoders (se pone en cero en el muelle),
   la evasión de los 3 obstáculos con el ultrasónico, la meta y la vuelta al muelle de reversa. Para
   "dónde está / qué hace el carro" usa lo que dice el carro en ESTADO_EN_VIVO (que_hace, x, y,
   ultimos_eventos, ruta).
Lo demás (vasos, tapa y prensa, cortina, canaleta, costos, parte eléctrica, pines, simulación) también
lo respondes, con los datos de DOCUMENTACION; no lo desvíes hacia las monedas si no lo preguntan.

Recibes: (1) ESTADO_EN_VIVO, un JSON con las cifras reales de la corrida actual; (2) DOCUMENTACION, las
secciones del proyecto relacionadas con la pregunta; (3) la frase de la persona.

Responde ÚNICAMENTE con un objeto JSON, sin texto antes ni después:
{{"respuesta": "<texto para la persona>", "acciones": [ ...órdenes... ]}}

Reglas:
- Nunca inventes cifras. Toda cifra de la corrida sale de ESTADO_EN_VIVO; si no está, di que no tienes ese
  dato. Lo técnico (sensores, pines, medidas, decisiones) sale de DOCUMENTACION; si no está, dilo.
- "acciones" va vacío si la persona solo pregunta. Solo agrega órdenes si la persona pide hacer algo.
  Órdenes posibles (exactamente estas):
  {{"cmd":"carro","accion":"detener"}}
  {{"cmd":"carro","accion":"avanzar","distancia_m":0.3}}      (0.01 a 1.5 m, hacia adelante, despacio)
  {{"cmd":"carro","accion":"retroceder","distancia_m":0.1}}   (0.01 a 0.3 m: atrás no tiene sensor)
  {{"cmd":"carro","accion":"girar","grados":90}}              (-180 a 180; positivo = izquierda)
  {{"cmd":"carro","accion":"ir_a","x":1.2,"y":-0.5}}           (metros, coordenadas de la pista)
  {{"cmd":"carro","accion":"ir_meta"}}      {{"cmd":"carro","accion":"volver_muelle"}}
  {{"cmd":"carro","accion":"seguir_linea"}} (retomar el recorrido automático)
  {{"cmd":"pausar"}} {{"cmd":"reanudar"}} {{"cmd":"paro"}} {{"cmd":"iniciar"}} {{"cmd":"embalar_parciales"}}
  {{"cmd":"lote","valor":10}} (monedas por vaso)   {{"cmd":"velocidad","valor":2}} (0.25 a 8)
- Varias órdenes seguidas se ejecutan en orden, pero una orden nueva al carro reemplaza la anterior: para
  una secuencia de movimientos del carro, manda solo la primera y explica que la siguiente se pide después.
- Si preguntan por una medida que ningún sensor del proyecto mide EN VIVO (temperatura, voltaje o
  corriente de algo, humedad...), di claramente que no hay un sensor que la mida y que no tienes ese
  dato; puedes dar el valor NOMINAL de la documentación, aclarando que no es una medición.
- Una pregunta (¿...?) nunca da órdenes: "acciones" va vacío. Tampoco un pedido de información
  ("dime", "explícame", "cuéntame", "muéstrame").
- Nunca digas que el carro "se moverá", "irá" o "volverá" si "acciones" no lleva esa orden: sin orden,
  el carro NO se mueve. Escribe texto plano, sin markdown (sin `comillas invertidas` ni **negritas**).
- En las tablas de conexiones, "G25.S" es el GPIO 25 del ESP32 (fila S = señal de la placa GVS) y
  "M.STEP" es la entrada STEP del driver; el pin del ESP32 es el número que va después de la G.
- El carro no choca: antes de moverse mira el camino, y si ve algo adelante se detiene; si la persona pide
  algo que lo haría chocar o salir de la pista, explícalo. Las cm se pasan a metros. El carro anda SOLO
  por el piso: nunca puede atravesar ni entrar a la planta (cintas, filtro, almacén, canaleta) ni al
  muelle por un costado; no prometas eso ni mandes ir_a a un punto de la planta.
- En "respuesta": si es una orden, una o dos frases diciendo qué vas a hacer. Si es una pregunta,
  de 2 a 6 frases completas: la respuesta directa primero, con las cifras exactas de ESTADO_EN_VIVO
  (con sus unidades) o los datos de DOCUMENTACION, y después el porqué o el detalle útil. Nunca
  contestes una pregunta con una sola frase: agrega qué significa la cifra, de dónde sale (qué
  sensor, estación o archivo) y un dato relacionado del estado o de la documentación. No nombres
  campos internos (ESTADO_EN_VIVO, claves del JSON como valor_aceptado_pesos): habla como persona.
"""


def _umbrales_filtrado() -> dict:
    """Los umbrales del filtrado para el prompt, leidos de config/parametros.yaml (fuente unica;
    ningun numero magico en el codigo). Si la configuracion no se puede leer, los de CLAUDE.md sec. 7."""
    try:
        from app.configuracion import cargar_parametros

        f = cargar_parametros()["filtrado"]
        valores = (f["diametro_min_mm"], f["diametro_max_mm"], f["circularidad_minima"], f["confianza_minima"],
                   f["tolerancia_coherencia_mm"])
    except Exception:  # sin configuracion: los valores de la seccion 7
        valores = (16.5, 27.5, 0.90, 0.85, 1.2)
    return {k: f"{v:g}".replace(".", ",") for k, v in zip(("dmin", "dmax", "circ", "conf", "coh"), valores)}


PROMPT_SISTEMA = _PLANTILLA_PROMPT.format(**_umbrales_filtrado())


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


# "que + subjuntivo" es un PEDIDO, no una pregunta (revision logica 2026-09-29): el usuario habla
# asi ("que vaya a donde esta el filtro", "que avance el carro 30 cm", "que vuelva al muelle") y
# `es_pregunta` tomaba el "que " inicial como el "que" interrogativo, asi que esas ordenes no daban
# nada. El interrogativo lleva tilde ("¿qué hay?") o va seguido de es/hay/tan/cuanto/hace...: ninguna
# de esas es un subjuntivo de esta lista, asi que siguen siendo preguntas (y una pregunta nunca
# mueve nada). Si la frase trae "qué" CON tilde, gana la pregunta.
_QUE_PEDIDO = re.compile(
    r"que\s+(el carro|el carrito|el vehiculo|el robot|la linea( de produccion)?|la planta|la produccion|"
    r"la cinta|se|lo|le)?\s*"
    r"(avance|avancen|abance|retroceda|retrocedan|gire|giren|voltee|rote|vaya|vayan|vuelva|vuelvan|regrese|"
    r"regresen|siga|sigan|retome|mueva|muevan|detenga|detengan|pare|paren|frene|frenen|ande|camine|lleve|"
    r"pause|reanude|continue|arranque|inicie|empiece|empaque|embale|haga|quede|de (la|media) vuelta)\b")


def es_pedido_con_que(frase: str) -> bool:
    """"que vaya a la meta" (pedido) y no "qué hay en la meta" (pregunta)."""
    t = normalizar(frase).strip().lstrip("¡ ")
    return (not frase.strip().lstrip("¡ ").lower().startswith("qué") and "?" not in frase and "¿" not in frase
            and bool(_QUE_PEDIDO.match(t)))


def es_pregunta(frase: str) -> bool:
    t = normalizar(frase).strip()
    if es_pedido_con_que(frase):
        return False
    return "?" in t or "¿" in frase or bool(re.match(r"(cuant|que |como |donde |cual|por ?que|quien|cuando |how |what |where )", t))


# Pide un movimiento del carro. Si la frase no lo pide, ninguna orden al carro pasa, venga de
# donde venga (reglas, modelo local o DeepSeek; antes el candado era solo para el modelo local).
# Incluye lo que el interprete de reglas entiende como orden (adelante, atras, camina, stop,
# "da la vuelta") para que el candado no le quite una orden legitima.
# Con las formas de "que + subjuntivo" (avance, siga, frene, lleve, camine: 2026-09-29; "avance" se
# escribe con c y el candado le quitaba la orden a "que avance el carro 30 cm").
PIDE_MOVIMIENTO = re.compile(r"\b(muev|avanz|avanc|abanz|abanc|avans|adelante|camin|retroce|reversa|atras|gir|volte|"
                             r"rota|rote|media vuelta|da la vuelta|de la vuelta|ve |ir |vaya|anda|ande|llev|vuelv|"
                             r"regres|deten|det[eé]n|fren|para el|pare|quieto|stop|sigue|siga|retom|continu|meta|"
                             r"muelle|punto)")

# ---- A quien le habla la frase: al carro, a la linea o a nadie (revision logica 2026-09-29) ----
# `PIDE_MOVIMIENTO` solo mira si aparece un verbo de movimiento, sin importar de QUIEN se habla:
# "la moneda avanza por la cinta" mandaba el carro 0,2 m adelante y "sigue la linea de produccion"
# lo ponia a seguir su linea negra (la regla de reanudar nunca se alcanzaba). Ahora una orden al
# carro exige que la frase nombre al carro o que EMPIECE con el verbo (imperativo: "avanza 30 cm",
# "que vuelva al muelle"), y nunca sale si una moneda/pieza/cinta/la planta es el sujeto o lo que
# se mueve.

# Palabras de relleno al inicio de un pedido. "que" es el del pedido ("que vuelva al muelle"): las
# preguntas ya se descartaron antes con `es_consulta`.
_RELLENO = re.compile(r"^\s*((por favor|porfa|oye|ey|bueno|ok|okay|listo|entonces|ahora|y|ya|puedes|podrias|"
                      r"haz que|haga que|hazme el favor de|haz el favor de|necesito que|quiero que|que)\s+)+")
CARRO = re.compile(r"\b(carro|carrito|vehiculo|robot)\b")
# Lo que NO es el carro: si es el sujeto de la frase, el movimiento es de eso (la moneda avanza por la
# cinta, la pieza retrocede, la cinta gira) y el carro no se toca. "linea" sola es la linea negra del
# carro; "linea de produccion", "produccion" y "planta" son la linea de la planta.
AJENO_AL_CARRO = (r"(monedas?|piezas?|cintas?|bandas?|vasos?|elementos?|botones|boton|tapas?|carrusel|tubos?|"
                  r"prensa|empujador|compuerta|linea de produccion|produccion|planta)")
_AJENO = re.compile(r"\b" + AJENO_AL_CARRO + r"\b")
# Verbos (y adverbios) con los que se le da una orden al carro. Si la frase no nombra al carro, tiene
# que EMPEZAR con uno de estos (despues del relleno).
_VERBO_CARRO = (r"(avanz\w*|avance\w*|abanz\w*|abance\w*|avans\w*|adelante|atras|reversa|retroce\w*|muev\w*|"
                r"camin\w*|gir[ae]\w*|volte\w*|rot[ae]\w*|da|de|media vuelta|ve|ir|vaya\w*|vete|anda\w*|"
                r"ande|llev[ae]\w*|vuelv\w*|volver|regres\w*|devuelve\w*|sigue|seguir|siga\w*|retom\w*|"
                r"deten\w*|detien\w*|para|pare\w*|frena\w*|frene\w*|quieto|stop|continu\w*)")
# Verbo que MUEVE a su complemento: "avanza la cinta", "gira el carrusel", "sigue la linea de
# produccion", "deten la planta" hablan de mover eso, no el carro.
_VERBO_CON_OBJETO_AJENO = re.compile(
    r"\b(avanz\w*|avance\w*|retroce\w*|gir[ae]\w*|volte\w*|rot[ae]\w*|muev\w*|deten\w*|detenga\w*|para|pare\w*|"
    r"frena\w*|frene\w*|sigue|seguir|siga\w*|retom\w*|continu\w*)\s+((el|la|los|las|un|una|esa|esta|esas|estas)\s+)?"
    + AJENO_AL_CARRO + r"\b")


def _sin_relleno(t: str) -> str:
    """Frase normalizada, sin signos y sin el relleno del principio."""
    return _RELLENO.sub("", re.sub(r"[¡!¿?.,;:]", " ", t)).strip()


def pide_mover_carro(frase: str) -> bool:
    """La frase le da una orden AL CARRO (no a una moneda, a la cinta ni a la planta)."""
    t = _sin_relleno(normalizar(frase))
    carro, ajeno = CARRO.search(t), _AJENO.search(t)
    verbo = re.search(r"\b" + _VERBO_CARRO + r"\b", t)
    if ajeno and (not carro or ajeno.start() < carro.start()) and (not verbo or ajeno.start() < verbo.start()):
        return False     # "la moneda avanza por la cinta": el sujeto es la moneda
    objeto = _VERBO_CON_OBJETO_AJENO.search(t)
    if objeto and (not carro or objeto.start() < carro.start()):
        return False     # "avanza la cinta", "sigue la linea de produccion"
    if carro:
        return True      # "que el carro vaya a la meta", "gira el carro 90 grados"
    return bool(re.match(_VERBO_CARRO + r"\b", t))   # imperativo al inicio: "avanza 30 cm", "stop"


# Pausar / reanudar LA LINEA (regla acordada con el usuario, 2026-09-29): "deten/para la linea",
# "deten todo", "para la planta", "deten la produccion" = PAUSA (se sale con "reanudar"). El PARO
# queda para "paro", "paro de emergencia" o la urgencia explicita ("para todo ya", `pide_paro`).
# Antes "deten todo/la planta/la produccion" daban `carro detener` (la linea seguia) y "para todo"
# o "para la linea" no daban nada.
_OBJETO_LINEA = r"(todo|toda la planta|la planta|la linea( de produccion)?|la produccion|la maquina|las cintas)"
_PAUSA_DETEN = re.compile(r"\b(deten|detenga|detengan|detener|frena|frene|frenen|frenar|pausa|pausar|pause|"
                          r"paraliza|paralizar)\s+" + _OBJETO_LINEA + r"\b")
# "para" tambien es preposicion ("sirve para todo", "gira el carro para la derecha"): solo cuenta
# como verbo al inicio de la frase o justo antes de todo/la linea/la planta/la produccion, y no
# despues de palabras que la vuelven preposicion.
_PAUSA_PARA = re.compile(r"(?:^|\b(\w+)\s+)(para|pare|paren|parar)\s+" + _OBJETO_LINEA + r"\b")
_ANTES_DE_PREPOSICION = {"sirve", "sirven", "usa", "usan", "util", "listo", "lista", "listos", "hecho", "hecha",
                         "bueno", "buena", "necesario", "necesaria", "importante", "suficiente", "tiempo", "espacio"}


def pide_pausa_linea(frase: str) -> bool:
    t = _sin_relleno(normalizar(frase))
    if _PAUSA_DETEN.search(t):
        return True
    for m in _PAUSA_PARA.finditer(t):
        if m.group(1) not in _ANTES_DE_PREPOSICION:
            return True
    return False


# Reanudar la LINEA: "sigue/continua/retoma la linea de produccion / la produccion / la planta".
_REANUDA_LINEA = re.compile(r"\b(reanuda\w*|reanude\w*|continua\w*|continue\w*|sigue|seguir|siga\w*|retoma\w*|"
                            r"retome\w*|arranca de nuevo)\b.*\b(linea de produccion|produccion|planta)\b")

# Pedir INFORMACION no es dar una orden (revision 2026-09-28): "Dime cuantos vasos llegaron a la
# meta" mandaba el carro a la meta, "Explicame el paro de emergencia" paraba la linea y "Cuentame
# como hace la media vuelta el carro" lo giraba 180 grados. `es_pregunta` solo mira el "?" o la
# primera palabra, y el reconocimiento de voz (Whisper, Google) NO pone signos de pregunta. Con
# estos verbos de explicar/informar la frase nunca da ordenes, con ningun proveedor.
PIDE_INFORMACION = re.compile(
    r"\b(explica\w*|expliq\w*|cuentame|cuentanos|contame|dime|dinos|digame|hablame|hablanos|habla de|"
    r"resume\w*|resumen|muestrame|muestranos|describe\w*|detalla\w*|informame|ensename|"
    r"que es|que son|como funciona\w*|como se hace|como hace|quiero saber|me gustaria saber|necesito saber|"
    r"recuerdame)\b")


def pide_informacion(frase: str) -> bool:
    """La frase pide que se EXPLIQUE o INFORME algo (sin signo de pregunta)."""
    return bool(PIDE_INFORMACION.search(normalizar(frase)))


def es_consulta(frase: str) -> bool:
    """Pregunta o pedido de informacion: ninguna de las dos mueve nada."""
    return es_pregunta(frase) or pide_informacion(frase)


# Paro de emergencia: SOLO con un imperativo explicito. Antes bastaba con que la frase nombrara
# "paro" o "emergencia" ("explicame el paro de emergencia" paraba la linea). Vale: la frase entera
# es el grito ("paro!", "paro de emergencia", "emergencia ya") o un verbo que lo manda ("haz
# paro", "activa el paro", "paro ya") o la urgencia explicita ("para todo ya", "deten la linea ahora
# mismo"). "para todo" o "deten la linea" a secas son PAUSA (`pide_pausa_linea`).
PARO_SOLO = re.compile(r"\s*(paro|emergencia|paro de emergencia)(\s+(ya|ahora|ahora mismo|inmediato|por favor))?\s*$")
PARO_IMPERATIVO = re.compile(
    r"\b(haz|haga|hace|activa|active|activar|pulsa|pulse|presiona|presione|aprieta|oprime|dale|da|dele|"
    r"ejecuta|ejecute|manda|mande)\s+(un |el |al )?(boton de(l)? )?paro\b"
    r"|\bparo( de emergencia)? (ya|ahora|inmediato)\b"
    r"|\b(para|pare|paren|deten|detenga|detengan|frena|frene)\s+(todo|toda la planta|la planta|la linea|"
    r"la maquina|la produccion)\s+(ya|ahora|ahora mismo|inmediatamente|de inmediato)\b")
# "detén la línea" / "para todo" a secas NO son paro: dan PAUSA (se sigue con "reanudar"). Del PARO
# solo se sale con Iniciar, que empieza una corrida nueva: se reserva para "paro" o para la urgencia
# explícita ("para todo ya", "detén la línea ahora mismo").


def pide_paro(frase: str) -> bool:
    t = re.sub(r"[¡!.,;]", " ", normalizar(frase)).strip()
    return bool(PARO_SOLO.match(t) or PARO_IMPERATIVO.search(t))


# Medidas que ningun sensor del proyecto toma en vivo.
SIN_SENSOR = re.compile(r"\b(temperatura|voltaje|tension|corriente|humedad)\b")

# Pedir que el carro ATRAVIESE la planta (usuario, 2026-09-27: "que vaya a donde esta el filtro de
# monedas, lo atraviese y que el propio sistema lo pase por el lado con sus sensores"). El modelo
# local contesto "cruzara por el" y lo mando a (-0,5; 0), dentro de la planta: el carro se trabo
# contra el muelle. El carro anda por el PISO; la planta, la canaleta y el muelle estan prohibidos
# en su mapa. Se contesta con reglas, con cualquier proveedor, y no sale ninguna orden.
ATRAVESAR = re.compile(r"\b(atravies|atraves|cruce|cruza|cruzar|traspas|pase por (encima|dentro|debajo|medio)|"
                       r"por (encima|dentro|debajo|en medio) de)")
ESTRUCTURA = re.compile(r"\b(planta|filtro|cinta|banda|almacen|revolver|canaleta|mesa|estacion|maquina|prensa|"
                        r"camara|sensores|embalaje)")


_zonas = {}


def destino_imposible(x: float, y: float) -> str:
    """"" si el carro puede ir a (x, y); si no, el motivo. Mismo mapa y misma holgura que usa el
    carro (control/vehiculo.py: motivo_destino), armado de la geometria (sim/geometria.py)."""
    from app.configuracion import cargar_parametros
    from control.vehiculo import holguras_carro, motivo_destino
    from sim.geometria import zonas_carro

    if "z" not in _zonas:
        p = cargar_parametros()
        _zonas["z"] = zonas_carro(p)
        _zonas["holgura"] = holguras_carro(p["vehiculo"])[1]
    return motivo_destino(_zonas["z"], float(x), float(y), _zonas["holgura"])


def pide_atravesar(frase: str) -> bool:
    """Una ORDEN (no una pregunta) de que el carro atraviese la planta. Tiene que hablar del
    carro, mandarlo a algun lado o empezar con el verbo: "la moneda pasa por encima de la cinta"
    o "cruce la camara con la mano" no son pedidos al carro."""
    t = normalizar(frase)
    if es_pregunta(frase) or not (ATRAVESAR.search(t) and ESTRUCTURA.search(t)):
        return False
    return bool(re.search(r"\b(carro|vehiculo|vaya|ve a|ir a|lleve|llevalo|haga que|hazlo|muev)", t)
                # Con la frase original (con tildes): "crucé ..." es pasado, no una orden.
                or re.match(r"\s*(atraviesa|atraviese|cruza|cruce|pasa por|pase por)\b", frase.lower()))


RESPUESTA_ATRAVESAR = (
    "Eso no se puede: el carro anda por el piso de la pista y no puede atravesar la planta (las cintas, el "
    "filtro de monedas, el almacén, la canaleta), ni subirse a ella. Además, en su mapa esas zonas están "
    "prohibidas, así que rechaza cualquier destino dentro de ellas. Por los sensores del filtro pasan las "
    "monedas sobre la cinta, no el carro. Lo que sí puede: ir a la meta, volver al muelle, avanzar, girar "
    "o ir a un punto del piso libre alrededor de la pista.")


# Frases que PROMETEN mover el carro (revision visual 2026-09-28: el modelo local decia "se moverá a
# tres posiciones aleatorias" o "se moverá al muelle" sin mandar ninguna orden). Si al final no sale
# ninguna orden al carro, esas oraciones se quitan de la respuesta y se dice que no se movio.
#
# Dos clases (revision logica 2026-09-29): la PRIMERA PERSONA ("lo muevo", "voy a mover", "avanzaré")
# siempre es una promesa de hacerlo ahora por una orden; la IMPERSONAL ("se moverá", "va a moverse")
# a veces describe el FUNCIONAMIENTO AUTOMATICO ("se moverá solo a la meta cuando lo carguen", "cada
# vez que entra al muelle...") y eso es informacion correcta: antes se borraba y se le pegaba "no se
# mueve", que confundia. Solo se quita la impersonal si no trae una marca de automatico/condicion.
# "(?<!no )": "No lo muevo: ese punto está dentro de la planta" es justo lo contrario de una promesa.
PROMESA_PRIMERA_PERSONA = re.compile(
    r"(?<!no )\b(lo movere|movere|voy a mover|lo muevo|muevo el carro|lo llevo|lo llevare|llevare el carro|"
    r"lo mando|lo mandare|enviare el carro|mandare el carro|avanzare|retrocedere|girare|ire a)\b")
PROMESA_IMPERSONAL = re.compile(
    r"(?<!no )\b(se movera|va a moverse|se desplazara|comenzara a moverse|empezara a moverse)\b")
FUNCIONAMIENTO_AUTOMATICO = re.compile(
    r"\b(solo|sola|por si solo|por si mismo|automatic\w*|por su cuenta|cuando|cada vez|siempre|en cuanto|"
    r"apenas|una vez que|despues de|al (terminar|llegar|cargar\w*|recibir|entrar))\b")
# Compatibilidad (evaluador y pruebas viejas): cualquiera de las dos formas.
PROMESA_MOVIMIENTO = re.compile(PROMESA_PRIMERA_PERSONA.pattern + "|" + PROMESA_IMPERSONAL.pattern)


def promete_movimiento(oracion: str) -> str:
    """El trozo de la oracion que promete mover el carro AHORA, o "" (una descripcion del recorrido
    automatico no cuenta)."""
    t = normalizar(oracion)
    m = PROMESA_PRIMERA_PERSONA.search(t)
    if m:
        return m.group(0)
    m = PROMESA_IMPERSONAL.search(t)
    if m and not FUNCIONAMIENTO_AUTOMATICO.search(t):
        return m.group(0)
    return ""


def quitar_promesas(texto: str) -> tuple[str, bool]:
    """Quita las oraciones que prometen un movimiento del carro. Devuelve (texto, quito_algo)."""
    oraciones = re.split(r"(?<=[.!?])\s+", texto.strip())
    quedan = [o for o in oraciones if not promete_movimiento(o)]
    return " ".join(quedan).strip(), len(quedan) != len(oraciones)


def limpiar_markdown(texto: str) -> str:
    """La respuesta se muestra como texto plano (visor 3D, voz): sin `codigo`, **negritas** ni
    titulos "#". El modelo local a veces escribe `qwen2.5-proyecto` y en el visor quedaban las
    comillas invertidas sueltas."""
    t = texto.replace("```", "").replace("`", "")
    t = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), t)
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", t)
    return t.strip()


def _orden_al_carro(t: str) -> dict | None:
    """La orden al carro de una frase ya normalizada que SI le habla al carro, o None."""
    tl = _sin_relleno(t)
    # "para" como verbo solo al inicio o en "para el carro": "gira el carro para el lado derecho"
    # antes lo detenia (la regla buscaba "para el" en cualquier parte).
    if re.search(r"\b(deten|detente|detener|detenga|detengase|frena|frenar|frene|quieto|stop)\b", tl) \
            or re.match(r"(para|pare|parate|parese)\b", tl) or re.search(r"\b(para|pare) (el|al) (carro|carrito|vehiculo|robot)\b", tl):
        return {"cmd": "carro", "accion": "detener"}
    if re.search(r"\b(meta)\b", t) and re.search(r"\b(ve|ir|vaya|vayan|lleva|llevar|lleve|anda|hasta|a la)\b", t):
        return {"cmd": "carro", "accion": "ir_meta"}
    if re.search(r"\b(muelle|base|casa|inicio)\b", t) and re.search(
            r"\b(vuelve|volver|vuelva|regresa|regresar|regrese|ve|ir|vaya|lleva|llevar|lleve|llevalo|manda|mandar|"
            r"mande|devuelve|devuelva)\b", t):
        return {"cmd": "carro", "accion": "volver_muelle"}
    if re.search(r"\b(sigue|seguir|siga|retoma|retomar|retome)\b.*\b(linea|ruta|recorrido)\b", t):
        return {"cmd": "carro", "accion": "seguir_linea"}
    m = re.search(r"\bx\s*=?\s*" + _NUM + r".*?\by\s*=?\s*" + _NUM, t) or \
        re.search(r"\(\s*" + _NUM + r"\s*[,;]\s*" + _NUM + r"\s*\)", t)
    if m and re.search(r"\b(ve|ir|vaya|anda|lleva|lleve|posicion|punto|a)\b", t):
        return {"cmd": "carro", "accion": "ir_a", "x": _num(m.group(1)), "y": _num(m.group(2))}
    if re.search(r"\b(gira|girar|gire|giren|voltea|voltear|voltee|rota|rotar|rote|da la vuelta|de la vuelta|"
                 r"media vuelta)\b", t):
        if "media vuelta" in t or re.search(r"\b(da|de) la vuelta\b", t):
            return {"cmd": "carro", "accion": "girar", "grados": 180}
        g = re.search(_NUM + r"\s*(?:grados?|°)?", t)
        grados = _num(g.group(1)) if g else 90.0
        if "derech" in t:
            grados = -abs(grados)
        return {"cmd": "carro", "accion": "girar", "grados": grados}
    if re.search(r"\b(avanza|avanzar|avance|avancen|avanzando|abanza|abanzar|abance|avansa|avansar|adelante|"
                 r"muevete|mueve|muevelo|mueva|muevase|camina|camine)\b", t):
        return {"cmd": "carro", "accion": "avanzar", "distancia_m": _distancia_m(t) or 0.2}
    if re.search(r"\b(retrocede|retroceder|retroceda|atras|reversa)\b", t):
        return {"cmd": "carro", "accion": "retroceder", "distancia_m": _distancia_m(t) or 0.1}
    return None


def interpretar_orden_local(frase: str) -> list[dict]:
    """Ordenes con expresiones regulares (sin DeepSeek). Devuelve la lista de
    ordenes crudas (despues se validan igual que las de DeepSeek)."""
    t = normalizar(frase).strip()
    # Una pregunta nunca mueve nada ("¿cuantos vasos llegaron a la meta?"), y un pedido de
    # informacion tampoco ("dime cuantos vasos llegaron a la meta", sin signos: asi lo escribe
    # el reconocimiento de voz).
    if es_consulta(frase):
        return []
    if pide_paro(frase):
        return [{"cmd": "paro"}]
    # La LINEA antes que el carro: "deten todo", "para la planta" (pausa) y "sigue la linea de
    # produccion" (reanudar) no son ordenes al carro.
    if pide_pausa_linea(frase):
        return [{"cmd": "pausar"}]
    if _REANUDA_LINEA.search(t):
        return [{"cmd": "reanudar"}]
    # Ordenes al carro: solo si la frase le habla al carro (ver `pide_mover_carro`). Se incluyen las
    # formas de "que + subjuntivo" (avance, vuelva, gire...), que es como pide las cosas el usuario.
    if pide_mover_carro(frase):
        orden = _orden_al_carro(t)
        if orden:
            return [orden]
    if re.search(r"\b(pausa|pausar|pausala|pause)\b", t):
        return [{"cmd": "pausar"}]
    if re.search(r"\b(reanuda|reanudar|reanude|continua|continuar|continue)\b", t):
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
# Qué estación detecta cada causa de rechazo y con qué regla (CLAUDE.md sec. 7). Los umbrales
# se rellenan con los de config/parametros.yaml (_umbrales_filtrado).
EXPLICA_CAUSA = {
    "no_metalico": "E2 (material): el capacitivo la ve y el inductivo no, así que no es metal",
    "fuera_de_rango": "E3 (cámara): su diámetro está fuera de {dmin}-{dmax} mm",
    "no_circular": "E3 (cámara): circularidad menor a {circ} (bloques, fichas irregulares)",
    "perforado": "E3 (cámara): tiene agujeros o contornos internos (botones, arandelas)",
    "no_reconocida": "E3 (cámara): no reconoce la cara con confianza de al menos {conf} "
                     "(monedas extranjeras o muy antiguas)",
    "incoherente": "E3 (cámara): el diámetro medido difiere más de {coh} mm del de la denominación reconocida",
}


# Preguntas técnicas del FILTRADO que se repiten (foco del grupo). Sin modelo, las reglas las
# contestan con esto en vez de un pedazo de documentación; con el modelo local, van como DATO
# VERIFICADO (en la batería, "cómo sabe si es de metal" hizo que el modelo chico dijera que no
# había sensor de metal, porque la búsqueda no le trajo la sección del inductivo).
SABER_FILTRADO = [
    (re.compile(r"\b(metal|metalic\w*|capacitiv\w*|inductiv\w*)\b"),
     "El material lo decide la estación 2 con dos sensores DEBAJO de la cinta, mirando a través de la banda: "
     "un capacitivo (ve cualquier objeto) y un inductivo M18 (solo ve metal). Si el capacitivo ve la pieza y "
     "el inductivo no, no es metal y se rechaza como «no metálico», sin gastar la cámara; si los dos la ven, "
     "es metálica y sigue a la cámara."),
    (re.compile(r"(huec|ueco|agujer|perfor|ojal|arandela)"),
     "Los botones y arandelas con agujeros los saca la cámara (estación 3): busca contornos internos cerrados "
     "dentro de la pieza y, si encuentra alguno, la rechaza como «perforado»."),
    (re.compile(r"\b(euro|euros|extranjer\w*|otro pais|otros paises|dolar\w*|centimo\w*)\b"),
     "Una moneda extranjera no se rechaza por tamaño (un euro mide 23,25 mm, casi como una de $500), sino por "
     "la CARA: la cámara la clasifica y, si no la reconoce como moneda colombiana con confianza de al menos "
     "{conf}, la rechaza como «no reconocida»; y si la confunde con una colombiana, la regla de coherencia "
     "compara su diámetro con el de esa denominación (tolerancia {coh} mm) y la rechaza como «incoherente»."),
    (re.compile(r"\b(celdas? de carga|balanza|bascula|hx711)\b"),
     "El proyecto no usa celdas de carga: el grupo las prohibió (difíciles de acondicionar y dan problemas). "
     "El peso que se muestra es ESTIMADO por conteo: la suma de la masa nominal de cada moneda reconocida."),
]


MONTAJE = re.compile(r"\b(montaje|estructura|maquina|planta|sistema|proyecto|todo|completo|equipo|carro)\b")
CONSUMO = re.compile(r"\b(consum\w*|potencia|vatios|watts?|energia|autonomia|dura la bateria|cuanto dura)\b")


def _kg(gramos: float) -> str:
    return f"{gramos / 1000:.2f}".replace(".", ",") + " kg"


def peso_montaje() -> str:
    """Peso de TODO el montaje (config/masas.yaml, app/masas.py), no el de las monedas. "" si falla."""
    try:
        from app import masas

        zonas = sorted(masas.por_zona().items(), key=lambda x: -x[1])
        return (f"El montaje completo pesa unos {_kg(masas.total())} sin el portátil (suma de masas de "
                f"hoja de datos y estimadas, en docs/peso.md; no se pesa en la línea). Lo más pesado: "
                + ", ".join(f"{z} {_kg(g)}" for z, g in zonas[:3]) + ".")
    except Exception:  # config a medio editar: se sigue sin esta frase
        return ""


def consumo_electrico() -> str:
    """Consumo CALCULADO (sim/electrica.py -> docs/electrica.md), no medido. "" si no está el documento."""
    ruta = RAIZ / "docs" / "electrica.md"
    if not ruta.exists():
        return ""
    texto = ruta.read_text(encoding="utf-8")
    partes = []
    m = re.search(r"\*\*Consumo desde la red\*\*:\s*([^\n]+?)\s*\(", texto)
    if m:
        partes.append(f"La planta consume, según la simulación eléctrica, {m.group(1).strip()} desde la red")
    m = re.search(r"\*\*Autonom[ií]a\*\*[^:]*:\s*\*\*([^*]+)\*\*", texto)
    if m:
        partes.append(f"el carro, con su batería 2S, tiene unas {m.group(1).strip()}")
    if not partes:
        return ""
    return ("; ".join(partes) + ". Son valores CALCULADOS con corrientes de hoja de datos (docs/electrica.md), "
            "no medidos: ningún sensor mide el consumo en vivo.")


def _denominacion_nombrada(t: str) -> int | None:
    """La denominación que nombra una frase ya normalizada ("de 500", "de mil", "1.000"), o None."""
    m = re.search(r"\b(1[.,]?000|mil|500|200|100|50|quinientos|doscientos|cien)\b", t)
    if not m:
        return None
    palabra = m.group(1).replace(".", "").replace(",", "")
    return {"mil": 1000, "quinientos": 500, "doscientos": 200, "cien": 100}.get(palabra) or int(palabra)


ESTADO_CARRO = {"siguiendo":"siguiendo la línea", "maniobra": "maniobrando", "en_meta": "en la meta",
                "esperando_carga": "en el muelle", "detenido": "detenido", "manual": "cumpliendo una orden",
                "esperando_orden": "quieto, esperando otra orden"}


def responder_local(frase: str, estado: dict) -> str:
    """Preguntas basicas con las cifras del estado (sin DeepSeek)."""
    t = normalizar(frase)
    if re.search(r"\b(costo|costos|cuesta|cuestan|precio|precios|presupuesto|barato|abaratar|ahorrar|ahorro)", t):
        try:
            from app import costos

            subs = sorted(costos.por_subsistema().items(), key=lambda x: -x[1])
            mejores = costos.ahorros()[:3]
            return (f"El proyecto cuesta {costos.pesos(costos.total())} en Colombia (precios del "
                    f"{costos.cargar()['consultado']}, sin el portátil). Lo más caro: "
                    + ", ".join(f"{n} {costos.pesos(v)}" for n, v in subs[:3]) + ". Dónde ahorrar: "
                    + "; ".join(f"{a['titulo']} ({costos.pesos(a['ahorro'])}, riesgo {a['riesgo']})"
                                for a in mejores)
                    + ". Detalle en docs/costos.md.")
        except Exception:  # precios.yaml a medio editar o con otro formato: sigue con lo demás
            pass           # (el asistente nunca se cae por una tabla; se busca en docs/costos.md)
    # Lo técnico del filtrado no depende de la corrida: se contesta aunque no haya datos.
    saber = [texto.format(**_umbrales_filtrado()) for patron, texto in SABER_FILTRADO if patron.search(t)]
    # Peso de TODO el montaje (no el de las monedas) y consumo eléctrico: salen de los documentos
    # calculados (docs/peso.md, docs/electrica.md), no de la corrida.
    pide_peso = re.search(r"\b(peso|pesa|pesan|kilos?|kg|masa)\b", t)
    peso_de_montaje = bool(pide_peso and MONTAJE.search(t) and not re.search(r"\bmonedas?\b", t))
    if peso_de_montaje:
        saber.append(peso_montaje())
    if SIN_SENSOR.search(t):
        saber.append("No hay un sensor que mida eso en vivo, así que no tengo ese dato; lo que sí hay son "
                     "valores nominales o calculados de la documentación.")
    if CONSUMO.search(t) or re.search(r"\b(voltaje|tension|corriente)\b", t):
        saber.append(consumo_electrico())
    saber = [x for x in saber if x]
    if not estado.get("hay_datos"):
        return " ".join(saber) or "Todavía no hay datos de ninguna corrida: empiece una desde la barra de la izquierda."
    tot = estado["totales"]
    partes = list(saber)
    if re.search(r"\b(dinero|plata|valor|pesos|cuanto se ha|money)\b", t):
        partes.append(f"Valor aceptado: {_pesos(tot['valor_aceptado_pesos'])} en {tot['monedas_aceptadas']} monedas; "
                      f"en el almacén hay {_pesos(estado.get('almacen_valor_pesos'))} guardados.")
    tubos = estado.get("almacen_tubos") or {}
    denominacion = _denominacion_nombrada(t)
    if denominacion and re.search(r"\b(cuant|hay|tiene|llevan?|van|guardad|aceptad)", t) and \
            re.search(r"\b(monedas?|pesos|almac|almasen|tubo|hay de)", t):
        # "cuánto hay de 500", "cuántas monedas de mil hay en el almacén": la de esa denominación.
        d = estado["aceptadas_por_denominacion"].get(str(denominacion), {"monedas": 0, "valor_pesos": 0,
                                                                         "peso_estimado_g": 0})
        texto = (f"De {_pesos(denominacion)}: {d['monedas']} monedas aceptadas en esta corrida "
                 f"({_pesos(d['valor_pesos'])}, {d['peso_estimado_g']} g estimados)")
        if str(denominacion) in tubos:
            if re.search(r"\b(almac|almasen|tubo)", t):
                # Preguntan por el ALMACEN: esa cifra va primero. El modelo local chico repite la
                # primera cifra del dato verificado y contestaba las aceptadas (3) en vez de las
                # que quedan en el tubo (0 tras soltar un lote).
                n = tubos[str(denominacion)]
                texto = ((f"El tubo de {_pesos(denominacion)} del almacén está VACÍO ahora: 0 monedas guardadas "
                          f"(el último lote ya cayó a un vaso). ") if not n else
                         f"En el tubo de {_pesos(denominacion)} del almacén hay {n} monedas guardadas ahora. ") +                     "Aparte, " + texto[0].lower() + texto[1:]
            else:
                texto += f"; en su tubo del almacén hay {tubos[str(denominacion)]} guardadas"
        partes.append(texto + ".")
    elif re.search(r"\b(moneda|monedas|denominacion|denominaciones|coins)\b", t) and \
            re.search(r"\b(cuant|total|how many)", t) and not re.search(r"rechaz", t):
        por = estado["aceptadas_por_denominacion"]
        detalle = ", ".join(f"{d['monedas']} de {_pesos(int(k))}" for k, d in sorted(por.items(), key=lambda x: int(x[0])))
        partes.append(f"Monedas aceptadas: {tot['monedas_aceptadas']}" + (f" ({detalle})." if detalle else "."))
    if re.search(r"\b(almacen|almasen|almazen|revolver|tubos?)\b", t) and not denominacion and tubos:
        detalle = ", ".join(f"{n} de {_pesos(int(k)) if k.isdigit() else k}" for k, n in tubos.items() if n)
        partes.append(f"En el almacén revólver hay {_pesos(estado.get('almacen_valor_pesos'))} guardados"
                      + (f" ({detalle})" if detalle else " (todos los tubos vacíos)")
                      + f"; un vaso se llena cuando un tubo junta {estado.get('monedas_por_vaso')} monedas "
                        f"de la misma denominación.")
    if re.search(r"\b(peso|pesa|pesan|gramos|masa)\b", t) and not peso_de_montaje:
        partes.append(f"Peso estimado de las monedas aceptadas: {tot['peso_estimado_g']} g ({tot['nota_peso']}).")
    # "filtro" solo pide cifras de rechazos si no es una pregunta técnica ya contestada arriba: en la
    # batería, "qué filtro saca los botones con huecos" recibió también "el último rechazo fue en la
    # casilla 52 (no reconocida)" y el modelo local los mezcló ("el último perforado fue la 52").
    if re.search(r"\b(rechaz|rechazo|rechazos|rechazadas|causa|causas)", t) or \
            (re.search(r"\bfiltros?\b", t) and not saber):
        causas = estado["rechazos_por_causa"]
        detalle = ", ".join(f"{NOMBRE_CAUSA.get(c, c)}: {n}" for c, n in causas.items())
        partes.append(f"Piezas rechazadas: {tot['piezas_rechazadas']}" + (f" ({detalle})." if detalle else "."))
        if causas and re.search(r"\b(por ?que|causa|causas|motivo|explica|razon)", t):
            # "cuántas rechazó y POR QUÉ": qué estación detecta cada causa y con qué umbral.
            u = _umbrales_filtrado()
            partes.append("Por qué: " + "; ".join(f"{NOMBRE_CAUSA.get(c, c)} = {EXPLICA_CAUSA[c].format(**u)}"
                                                  for c in causas if c in EXPLICA_CAUSA) + ".")
        ultimos = estado.get("ultimos_rechazos") or []
        if ultimos:
            partes.append(f"El último rechazo fue en la casilla {ultimos[0]['casilla']} "
                          f"({NOMBRE_CAUSA.get(ultimos[0]['causa'], ultimos[0]['causa'])}).")
    v = estado.get("ultima_inspeccion_camara")
    if v and (re.search(r"\bultim", t) and re.search(r"\b(moneda|pieza|camara|vision|revis|inspecc|vio)", t)
              or re.search(r"\b(camara|vision)\b", t) and re.search(r"\b(vio|reviso|midio|detecto)\b", t)):
        agujeros = v.get("contornos_internos")
        partes.append(
            f"La última pieza que revisó la cámara (casilla {v['casilla']}, {v.get('hora', '')}) midió "
            f"{v['diametro_mm']} mm de diámetro y circularidad {v['circularidad']}, "
            + ("sin agujeros" if not agujeros else f"con {agujeros} agujeros")
            # "otro" no es una denominación: dicho así, el modelo local ya no la llama "una de 500".
            + (f"; NO la reconoció como ninguna moneda colombiana (clase «otro», confianza {v['confianza']})"
               if v.get("clase") in (None, "otro") else
               f"; la reconoció como «{v['clase']}» con confianza {v['confianza']}")
            + " → " + (v["veredicto"] or "")
            + (f" ({NOMBRE_CAUSA.get(v['causa'], v['causa'])})" if v.get("causa") else "") + ".")
    if re.search(r"\b(vaso|vasos)\b", t):
        partes.append(f"Vasos entregados en la meta: {tot['vasos_entregados_en_meta']}; "
                      f"esperando en la canaleta: {estado['canaleta_vasos_esperando']}.")
    if re.search(r"\b(confianza|umbral)\b", t):
        from app import configuracion

        c = configuracion.cargar_parametros()["filtrado"]["confianza_minima"]
        partes.append(f"La cámara acepta una moneda solo si la reconoce con confianza de al menos {c:.2f} "
                      f"({c * 100:.0f} %); por debajo se rechaza como «no reconocida».")
    if re.search(r"\b(carro|vehiculo|carrito|donde esta|ruta|obstaculo|obstaculos|evasion|evasiones)\b", t) and \
            re.search(r"\b(donde|estado|posicion|ubicacion|cuant|recorr|hac|asiendo|haciendo|que esta|como va|"
                      r"evasion|metros)", t):
        c = estado.get("carro")
        if c:
            radio = c.get("radio") or {}
            ultimos = c.get("ultimos_eventos") or []
            partes.append(
                f"El carro está {ESTADO_CARRO.get(c['estado'], c['estado'])} en ({c['x']:.2f}, {c['y']:.2f}) m"
                + (f" (tramo: {c['fase']})" if c.get("fase") else "")
                + (f", con el vaso {c['vaso_id']}" if c.get("vaso_id") else ", sin vaso")
                + f"; lleva {estado['ruta']['distancia_recorrida_m']} m recorridos y {estado['ruta']['evasiones']} "
                  f"evasiones de obstáculos."
                + (" La radio (ESP-NOW) está " + ("conectada." if radio.get("enlace") else "SIN enlace.")
                   if radio else "")
                + (f" Lo último que hizo: {', '.join(e.split(' ', 1)[1].replace('_', ' ') for e in ultimos[:3])}."
                   if ultimos else ""))
        else:
            partes.append("En esta corrida no hay carro con física.")
    if re.search(r"\b(carro|vehiculo|carrito|viaje|viajes)\b", t) and \
            re.search(r"\b(demora\w*|tarda\w*|dura|duracion|cuanto tiempo|que tan rapido|segundos|minutos)\b", t):
        v = estado.get("ruta", {}).get("tiempos_de_viaje") or {}
        if v.get("viajes_completos"):
            partes.append(
                f"El carro se demora en promedio {v['promedio_viaje_completo_s']} s por viaje completo (sale del "
                f"muelle con el vaso, llega a la meta y vuelve); el último tardó {v['ultimo_viaje_completo_s']} s. "
                f"Solo la ida a la meta: {v['promedio_ida_a_la_meta_s']} s en promedio. "
                f"Lleva {v['viajes_completos']} viajes completos (del registro de eventos del carro).")
        elif v.get("ultima_ida_a_la_meta_s") is not None:
            partes.append(f"El carro tardó {v['ultima_ida_a_la_meta_s']} s en llegar a la meta; todavía no "
                          "completó un viaje de vuelta al muelle.")
        else:
            partes.append("Todavía no hay un viaje del carro registrado en esta corrida: no tengo ese dato.")
    if re.search(r"\b(alarma|alarmas|problema|falla)\b", t):
        al = estado.get("alarmas") or []
        partes.append("Alarmas: " + (", ".join(a.replace("_", " ") for a in al) if al else "ninguna") + ".")
    if re.search(r"\b(estado|como va|linea)\b", t) and not partes:
        partes.append(f"La línea está {estado.get('estado_linea')}, ciclo {estado.get('ciclo')}; "
                      f"faltan {estado.get('piezas_por_cargar')} piezas por cargar.")
    if partes:
        return " ".join(partes)
    # La seccion que resume la bateria de pruebas (docs/modelo-local.md) CITA las preguntas de la
    # bateria palabra por palabra, asi que siempre gana la busqueda para esas preguntas, pero no
    # trae la respuesta (se vio con "¿qué pin manda los pasos (STEP)?": salia ella en vez de la
    # tabla de conexiones). Como extracto de respuesta se prefiere otra seccion.
    docs = [d for d in buscar(frase, 4000 + MAX_SECCION) if not d.titulo.startswith("Resultados de la batería")]
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
    if pide_atravesar(frase):
        crudo = {"respuesta": RESPUESTA_ATRAVESAR, "acciones": [], "documentos": []}
        modo = "local"
    if crudo is None and usar in ("auto", "deepseek"):
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
    if crudo is None and usar in ("auto", "ollama") and estado.get("hay_datos") \
            and _denominacion_nombrada(normalizar(frase)) and re.search(r"\b(almac|almasen|tubo)", normalizar(frase)):
        # "cuántas monedas de mil hay en el almacén" es una LECTURA de un número, que las reglas
        # tienen exacto. El modelo local chico, aun con el número como dato verificado, repetía las
        # monedas aceptadas (3) en vez de las del tubo (0, recién soltado un lote): 3 de 4 veces mal.
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
    if not isinstance(crudo.get("acciones"), list):
        crudo["acciones"] = []
    if es_consulta(frase) and crudo["acciones"]:
        # Una pregunta (o un "explícame", "dime", "cuéntame"...) nunca mueve nada, con ningún
        # proveedor (en las pruebas, "¿cuántos vasos llegaron a la meta?" hizo que el modelo local
        # mandara el carro a un punto).
        descartadas.append("una pregunta o un pedido de información no da órdenes")
        crudo["acciones"] = []
    if not PIDE_MOVIMIENTO.search(normalizar(frase)) or not pide_mover_carro(frase):
        # Candado para TODOS los proveedores (antes solo el modelo local): sin un verbo de
        # movimiento en la frase, ninguna orden al carro; y tampoco si el verbo es de otra cosa
        # ("la moneda avanza por la cinta", "sigue la línea de producción": 2026-09-29).
        quitadas = [a for a in crudo["acciones"] if isinstance(a, dict) and a.get("cmd") == "carro"]
        if quitadas:
            descartadas.append("se propuso mover el carro sin que la frase lo pidiera")
            crudo["acciones"] = [a for a in crudo["acciones"] if a not in quitadas]
    if not pide_paro(frase):
        # El paro detiene TODO y solo sale con una corrida nueva: solo con un imperativo explícito.
        quitadas = [a for a in crudo["acciones"] if isinstance(a, dict) and a.get("cmd") == "paro"]
        if quitadas:
            descartadas.append('paro: solo con una orden explícita ("haz paro", "paro de emergencia", "para todo ya")')
            crudo["acciones"] = [a for a in crudo["acciones"] if a not in quitadas]
    for a in corregir_giros(frase, crudo["acciones"]):
        orden, motivo = validar_accion(a)
        if orden and orden["cmd"] == "carro" and orden["accion"] == "ir_a":
            # Un destino dentro de la planta, la canaleta o el muelle, o fuera del piso: ni se
            # manda (el carro tambien lo rechazaria), y la respuesta dice por que en vez de
            # prometer el movimiento.
            imposible = destino_imposible(orden["x"], orden["y"])
            if imposible:
                descartadas.append(imposible)
                crudo["respuesta"] = f"No lo muevo: {imposible}."
                continue
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
    crudo["respuesta"] = limpiar_markdown(str(crudo.get("respuesta") or ""))
    if not any(o["cmd"] == "carro" for o in validas):
        # No se promete lo que no se mandó: sin orden al carro, fuera las oraciones "se moverá...".
        texto, quito = quitar_promesas(crudo["respuesta"])
        if quito:
            crudo["respuesta"] = (texto + " " if texto else "") + "No mandé ninguna orden al carro: no se mueve."
    guardar_mensaje(conexion, "usuario", frase)
    guardar_mensaje(conexion, "asistente", crudo["respuesta"], modo=modo, acciones=validas)
    return Respuesta(crudo["respuesta"], modo, validas, descartadas, crudo.get("documentos", []), aviso)


# ---------------------------------------------------------------------
# internet y voz (usuario, 2026-09-27: la voz tiene que funcionar SIN internet)
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

    import shutil

    # Ollama se instalo en D: (el disco del sistema no se llena; usuario, 2026-09-28); antes vivia
    # en la carpeta del usuario. Se prueba el PATH, D: y la ruta de instalacion por defecto.
    candidatos = [shutil.which("ollama") or "", r"D:\Program Files\Ollama\ollama.exe",
                  os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")]
    ollama = next((c for c in candidatos if c and Path(c).exists()), "ollama")
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
