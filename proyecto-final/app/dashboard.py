"""Dashboard de Streamlit (CLAUDE.md, seccion 13).

Este proceso SOLO LEE de SQLite y escribe ordenes en la tabla `ordenes`
(seccion 8). No importa PyBullet ni abre la simulacion: la linea la corre
`app/supervisor.py` en otro proceso. Por eso se puede refrescar, recargar o
abrir en varias pestanas del navegador sin que la linea se entere.

Refresco en vivo con `st.fragment(run_every=...)`: solo se reejecuta el
bloque de cada pestana cada `dashboard.refresco_s` segundos, no la pagina
entera, y no hay ningun bucle infinito dentro del script.

Uso, desde la raiz del repo (con el supervisor corriendo en otra terminal):
    streamlit run app/dashboard.py
o todo junto con:
    python -m app.lanzar
"""

from __future__ import annotations

import html
import json
import math
import sys
from datetime import datetime
from pathlib import Path

# Streamlit agrega al path la carpeta del script (app/), no la raiz del
# repo; sin esto no se encuentran los paquetes `app` y `control`.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402


from app import configuracion, db  # noqa: E402
from control import monedas as tabla_monedas  # noqa: E402
from control import reglas  # noqa: E402
from control.tiempos import presupuesto, tiempo_real_estimado_s  # noqa: E402

PARAMETROS = configuracion.cargar_parametros()
REFRESCO_S = PARAMETROS["dashboard"]["refresco_s"]
URL_VISOR = f"http://localhost:{PARAMETROS['supervisor']['puerto_http']}"

ESTACIONES_MONEDAS = ("Presencia", "Material", "Visión", "Descarga")
ESTACIONES_VASOS = ("Verificación", "Llenado", "Tapa", "Prensa", "Descarga")
DENOMINACIONES = (50, 100, 200, 500, 1000)

# Que etapa detecta cada causa (todas salen por la misma bandeja: filtro total).
ETAPA_DE_CAUSA = {c: ("material" if c == reglas.CAUSA_NO_METALICO else "vision") for c in reglas.CAUSAS_VALIDAS}
NOMBRE_CAUSA = {
    "no_metalico": "No metálico",
    "fuera_de_rango": "Fuera de rango",
    "no_circular": "No circular",
    "perforado": "Perforado",
    "no_reconocida": "No reconocida",
    "incoherente": "Incoherente",
}
QUE_FILTRA = {
    "no_metalico": "botones de plástico, bloques",
    "fuera_de_rango": "piezas muy chicas o muy grandes",
    "no_circular": "bloques y fichas irregulares",
    "perforado": "arandelas, botones con ojales",
    "no_reconocida": "monedas extranjeras, confianza baja",
    "incoherente": "clase y diámetro que no cuadran",
}

AMBAR = "#f2b134"
VERDE = "#3fb68b"
ROJO = "#e5534b"
AZUL = "#539bf5"
MORADO = "#b083f0"
GRIS = "#8b949e"

st.set_page_config(page_title="Monedas inteligentes", page_icon="🪙", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;600&display=swap');
:root { --fondo:#0e1116; --panel:#161b22; --borde:#2a313c; --texto:#e6e8eb; --tenue:#8b949e;
        --ambar:#f2b134; --verde:#3fb68b; --rojo:#e5534b; --azul:#539bf5; --morado:#b083f0; }
html, body, [class*="css"], .stMarkdown, .stMetric, button, input { font-family:'Space Grotesk', sans-serif; }
code, .mono { font-family:'IBM Plex Mono', monospace; }
.block-container { padding-top:1.4rem; }
[data-testid="stMetricValue"] { font-family:'IBM Plex Mono', monospace; font-weight:600; }
.cabecera { display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom:4px; }
.cabecera h1 { font-size:1.55rem; margin:0; font-weight:700; letter-spacing:-0.01em; }
.chip { display:inline-block; padding:2px 10px; border-radius:999px; font-family:'IBM Plex Mono', monospace;
        font-size:0.78rem; border:1px solid var(--borde); color:var(--tenue); }
.chip.corriendo { color:#0e1116; background:var(--verde); border-color:var(--verde); }
.chip.pausada { color:#0e1116; background:var(--ambar); border-color:var(--ambar); }
.chip.paro { color:#fff; background:var(--rojo); border-color:var(--rojo); }
.chip.terminada { color:#0e1116; background:var(--azul); border-color:var(--azul); }
.aviso { border-radius:8px; padding:10px 14px; margin:8px 0; font-size:0.92rem; }
.aviso.rojo { background:rgba(229,83,75,.14); border:1px solid var(--rojo); }
.aviso.ambar { background:rgba(242,177,52,.12); border:1px solid var(--ambar); }
/* Avisos GRANDES (usuario, 2026-09-27): que se note de lejos si no es en vivo o no hay internet. */
.aviso-grande { border-radius:10px; padding:12px 18px; margin:10px 0 6px; font-size:0.95rem; line-height:1.4; }
.aviso-grande b.titulo { display:block; font-size:1.15rem; letter-spacing:.04em; margin-bottom:2px; }
.aviso-grande.demo { background:var(--ambar); color:#1b1300; }
.aviso-grande.offline { background:rgba(229,83,75,.16); border:2px solid var(--rojo); }
.aviso-grande.offline b.titulo { color:#ff8a80; }
.chip.origen { color:var(--texto); border-color:var(--azul); }
.chip.real { color:#0e1116; background:var(--morado); border-color:var(--morado); }
.chip.sinred { color:#fff; background:var(--rojo); border-color:var(--rojo); }
.cinta { display:grid; gap:6px; margin:6px 0 2px; }
.cinta.m { grid-template-columns:repeat(7, minmax(0,1fr)); }
.cinta.v { grid-template-columns:repeat(5, minmax(0,1fr)); }
.casilla { background:#07090c; border:1px solid var(--borde); border-radius:8px; padding:8px 6px 10px;
           min-height:150px; display:flex; flex-direction:column; align-items:center; gap:6px; }
.casilla .est { font-size:0.72rem; color:var(--tenue); text-transform:uppercase; letter-spacing:.05em; text-align:center; }
.casilla .num { font-family:'IBM Plex Mono', monospace; font-size:0.7rem; color:#586069; }
.ficha { display:flex; align-items:center; justify-content:center; font-family:'IBM Plex Mono', monospace;
         font-weight:600; font-size:0.78rem; color:#1b1300; margin-top:6px; }
.ficha.moneda { border-radius:50%; background:radial-gradient(circle at 35% 30%, #ffe08a, #c9982e 70%); }
.ficha.boton_plastico { border-radius:50%; background:#d9259f; color:#fff; }
.ficha.boton_metalico { border-radius:50%; background:radial-gradient(circle at 35% 30%, #d0d4da, #7d828a 70%); }
.ficha.bloque { border-radius:3px; background:#3372c4; color:#fff; }
.ficha .ojal { width:5px; height:5px; background:#07090c; border-radius:50%; margin:0 2px; }
.veredicto { font-size:0.72rem; text-align:center; line-height:1.2; }
.veredicto.ok { color:var(--verde); } .veredicto.no { color:var(--rojo); } .veredicto.pend { color:var(--tenue); }
.vacia { color:#30363d; font-size:0.75rem; margin-top:30px; }
.vaso { width:54px; height:70px; border:2px solid #9aa4b1; border-top:none; border-radius:0 0 10px 10px;
        position:relative; overflow:hidden; margin-top:10px; background:rgba(154,164,177,.06); }
.vaso .nivel { position:absolute; bottom:0; left:0; right:0; background:linear-gradient(#ffd66b,#c9982e); }
.vaso.tapado::before { content:''; position:absolute; top:0; left:-2px; right:-2px; height:6px; background:#f28c28; z-index:2; }
.vaso.ausente { border-style:dashed; border-color:var(--rojo); background:none; }
.vaso.figura { width:44px; height:28px; margin-top:52px; border:none; border-radius:4px; background:#8a4fcf; }
.estado-vaso { font-family:'IBM Plex Mono', monospace; font-size:0.72rem; padding:1px 8px; border-radius:999px; border:1px solid var(--borde); }
.leds { display:flex; flex-wrap:wrap; gap:8px 16px; margin:8px 0 4px; }
.led { display:flex; align-items:center; gap:6px; font-size:0.82rem; color:var(--tenue); }
.led i { width:10px; height:10px; border-radius:50%; background:#30363d; display:inline-block; }
.led.on i { background:var(--verde); box-shadow:0 0 8px var(--verde); }
.led.on.alarma i { background:var(--rojo); box-shadow:0 0 8px var(--rojo); }
.led.on { color:var(--texto); }
.bitacora { font-family:'IBM Plex Mono', monospace; font-size:0.76rem; color:var(--tenue); line-height:1.55; }
.bitacora b { color:var(--texto); font-weight:600; }
.nota { color:var(--tenue); font-size:0.8rem; }
.tarjetas { display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:10px; margin:10px 0 14px; }
.tarjeta { background:var(--panel); border:1px solid var(--borde); border-left:4px solid var(--tenue); border-radius:10px; padding:10px 14px; }
.t-titulo { font-size:0.74rem; color:var(--tenue); text-transform:uppercase; letter-spacing:.05em; }
.t-estado { font-size:1.15rem; font-weight:700; margin:2px 0; }
.t-detalle { font-size:0.82rem; color:var(--tenue); }
.frases { display:flex; flex-direction:column; gap:6px; }
.frase { display:flex; gap:8px; align-items:flex-start; font-size:0.9rem; line-height:1.35; padding:6px 8px;
         border-radius:8px; background:rgba(22,27,34,.7); border:1px solid var(--borde); }
.frase .hora { font-family:'IBM Plex Mono', monospace; font-size:0.72rem; color:#586069; min-width:58px; padding-top:2px; }
.frase .ico { min-width:20px; }
.respuesta { border-radius:8px; padding:7px 10px; margin:6px 0; font-size:0.85rem; }
.respuesta.ok { background:rgba(63,182,139,.15); border:1px solid var(--verde); }
.respuesta.no { background:rgba(242,177,52,.13); border:1px solid var(--ambar); }
[data-testid="stMetricValue"] { font-size:1.9rem; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# datos
# ---------------------------------------------------------------------


@st.cache_resource
def _conexion(ruta: str):
    return db.conectar_lectura(ruta)


def conexion():
    # Una conexion por base (si cambia la ruta, no se reusa la anterior).
    return _conexion(str(configuracion.ruta_bd(PARAMETROS)))


def consulta(sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, conexion(), params=params)


def telemetria() -> dict | None:
    return db.ultima_telemetria(conexion())


def eventos_recientes(limite: int = 14) -> list[dict]:
    filas = conexion().execute(
        "SELECT ts, origen, tipo, payload FROM eventos WHERE tipo NOT IN ('tel', 'paso') "
        "ORDER BY id DESC LIMIT ?",
        (limite,),
    ).fetchall()
    return [dict(f) for f in filas]


def enviar(comando: dict, aviso: str) -> None:
    db.insertar_orden(conexion(), comando)
    st.toast(aviso)


def pesos(valor) -> str:
    return f"${int(valor or 0):,}".replace(",", ".")


def nombre_denominacion(d) -> str:
    """'$500', o 'otras denominaciones' para el vaso de las que ya no circulan."""
    return "otras denominaciones" if d == "otras" else pesos(d)


def figura_base(alto: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=alto,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Space Grotesk, sans-serif", color="#c9d1d9", size=13),
        xaxis=dict(gridcolor="#21262d", zeroline=False),
        yaxis=dict(gridcolor="#21262d", zeroline=False),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------
# piezas de HTML de la linea en vivo
# ---------------------------------------------------------------------


def html_ficha(c: dict) -> str:
    tipo = c["tipo"]
    if tipo == "moneda":
        denominacion = (c.get("clase_real") or "?").split("_")[0]
        return f'<div class="ficha moneda" style="width:46px;height:46px">{denominacion}</div>'
    if tipo == "vacia_registrada":
        # Casilla que el infrarrojo vio ocupada (una mano) pero viaja vacia.
        return '<div class="ficha" style="width:40px;height:40px;border:2px dashed #e5534b;border-radius:50%;color:#e5534b">✋</div>'
    if tipo in ("boton_plastico", "boton_metalico"):
        return f'<div class="ficha {tipo}" style="width:40px;height:40px"><span class="ojal"></span><span class="ojal"></span></div>'
    return '<div class="ficha bloque" style="width:36px;height:36px"></div>'


def html_veredicto(c: dict) -> str:
    if c.get("causa"):
        return f'<div class="veredicto no">✕ {NOMBRE_CAUSA.get(c["causa"], c["causa"])}</div>'
    if c.get("aceptada"):
        conf = f' · {c["confianza"]:.2f}' if c.get("confianza") is not None else ""
        return f'<div class="veredicto ok">✓ {html.escape(str(c.get("clase")))}{conf}</div>'
    if c.get("metal") is True:
        return '<div class="veredicto pend">metal · a visión</div>'
    return '<div class="veredicto pend">en camino</div>'


def html_cinta_monedas(tel: dict) -> str:
    partes = ['<div class="cinta m">']
    for i, nombre in enumerate(ESTACIONES_MONEDAS):
        c = tel["casillas_monedas"][i]
        cuerpo = '<div class="vacia">—</div>' if c is None else html_ficha(c) + html_veredicto(c)
        num = f'#{c["id"]}' if c else "&nbsp;"
        partes.append(
            f'<div class="casilla"><div class="est">E{i + 1} · {nombre}</div>{cuerpo}<div class="num">{num}</div></div>'
        )
    partes.append("</div>")
    return "".join(partes)


COLOR_ESTADO_VASO = {
    "valida": GRIS, "llenando": AMBAR, "llena": AMBAR, "tapada": VERDE,
    "invalida": ROJO, "rechazada": ROJO, "entregada": AZUL, "vacia": "#30363d",
}


def html_cinta_vasos(tel: dict) -> str:
    por_vaso = max(1, tel.get("monedas_por_vaso") or 5)
    partes = ['<div class="cinta v">']
    for i, nombre in enumerate(ESTACIONES_VASOS):
        v = tel["casillas_vasos"][i]
        if v is None:
            cuerpo = '<div class="vacia">sin vaso</div>'
            num = "&nbsp;"
        else:
            nivel = min(1.0, v["cantidad"] / por_vaso) * 100
            clases = "vaso"
            if v["fisico"] == "ausente":
                clases += " ausente"
            elif v["fisico"] == "figura":
                clases += " figura"
            if v["estado"] in ("tapada", "entregada"):
                clases += " tapado"
            relleno = f'<div class="nivel" style="height:{nivel:.0f}%"></div>' if v["fisico"] == "vaso" else ""
            color = COLOR_ESTADO_VASO.get(v["estado"], GRIS)
            # Un vaso recien puesto en la entrada todavia no paso la
            # verificacion: su registro dice "vacia" solo porque es el estado
            # inicial, no porque la camara lo haya visto vacio.
            estado_txt = "por verificar" if (v["estado"] == "vacia" and i == 0) else v["estado"]
            etiqueta = {"ausente": "retirado", "figura": "figura extraña"}.get(v["fisico"], "")
            etiqueta = f'<div class="veredicto no">{etiqueta}</div>' if etiqueta else ""
            cuerpo = (
                f'<div class="{clases}">{relleno}</div>'
                f'<span class="estado-vaso" style="color:{color};border-color:{color}">{estado_txt}</span>'
                f'<div class="veredicto pend">{v["cantidad"]} mon · {pesos(v["valor"])}</div>{etiqueta}'
                + (f'<div class="veredicto ok">vaso de {nombre_denominacion(v["denominacion"])}</div>'
                   if v.get("denominacion") else "")
            )
            num = f'vaso {v["id"]}'
        partes.append(
            f'<div class="casilla"><div class="est">{nombre}</div>{cuerpo}<div class="num">{num}</div></div>'
        )
    partes.append("</div>")
    return "".join(partes)


def html_almacen(tel: dict) -> str:
    """Los 5 tubos del almacen, con cuantas monedas tiene cada uno y cuanto
    falta para el lote."""
    almacen = tel.get("almacen") or {}
    lote = max(1, tel.get("monedas_por_vaso") or 5)
    capacidad = max(lote, tel.get("capacidad_tubo") or 25)
    partes = ['<div class="cinta" style="grid-template-columns:repeat(6, minmax(0,1fr))">']
    for d in ("50", "100", "200", "500", "1000", "otras"):
        n = int(almacen.get(d, 0))
        if d == "otras":
            # Denominaciones sin tubo ($1, $2, $5, $10, $20 de series viejas) y lo que no se
            # alcanzo a registrar: se guarda, no forma lotes.
            partes.append(
                f'<div class="casilla" style="min-height:120px"><div class="est">otras</div>'
                f'<div style="width:40px;height:40px;border:2px dashed #8b949e;border-radius:6px;margin-top:20px;'
                f'display:flex;align-items:center;justify-content:center;font-family:IBM Plex Mono,monospace">{n}</div>'
                f'<div class="veredicto {"ok" if n >= lote else "pend"}">{n} guardadas · van juntas a su vaso</div></div>'
            )
            continue
        alto = min(1.0, n / capacidad) * 100
        marca = min(1.0, lote / capacidad) * 100
        listo = n >= lote
        color = VERDE if listo else AMBAR
        partes.append(
            f'<div class="casilla" style="min-height:120px"><div class="est">tubo {pesos(int(d))}</div>'
            f'<div style="position:relative;width:34px;height:70px;border:2px solid #9aa4b1;border-top:none;'
            f'border-radius:0 0 6px 6px;margin-top:6px;overflow:hidden">'
            f'<div style="position:absolute;bottom:0;left:0;right:0;height:{alto:.0f}%;background:{color}"></div>'
            f'<div style="position:absolute;bottom:{marca:.0f}%;left:-4px;right:-4px;border-top:2px dashed #e6e8eb"></div></div>'
            f'<div class="veredicto {"ok" if listo else "pend"}">{n} guardadas{" · lote listo" if listo else ""}</div></div>'
        )
    partes.append("</div>")
    return "".join(partes)


def html_leds(pares: list[tuple[str, bool, bool]]) -> str:
    """(nombre, encendido, es_alarma)"""
    items = []
    for nombre, encendido, alarma in pares:
        clase = "led on" + (" alarma" if alarma else "") if encendido else "led"
        items.append(f'<span class="{clase}"><i></i>{nombre}</span>')
    return f'<div class="leds">{"".join(items)}</div>'


# ---------------------------------------------------------------------
# eventos en palabras simples (para quien no conoce el sistema)
# ---------------------------------------------------------------------

NOMBRE_TIPO_REAL = {"moneda": "moneda", "boton_plastico": "botón de plástico", "boton_metalico": "botón metálico",
                    "bloque": "bloque", "vacia": "casilla vacía", "mano": "mano"}
ESTADO_VASO_TXT = {"vacia": "vacío", "valida": "listo para llenar", "invalida": "no sirve", "llenando": "llenándose",
                   "llena": "lleno", "tapada": "tapado", "rechazada": "rechazado", "entregada": "entregado"}


def frase_evento(ev: dict) -> tuple[str, str] | None:
    """Evento -> (icono, frase en palabras simples). None = no se muestra en
    el resumen (detalle interno)."""
    d = json.loads(ev["payload"])
    t = ev["tipo"]
    if t == "elemento_final":
        if d["veredicto"] == "aceptada":
            return "✅", f'Moneda de <b>{pesos(d.get("denominacion"))}</b> aceptada: va a su tubo del almacén.'
        causa = d.get("causa") or d.get("motivo")
        return "🚫", (f'Pieza rechazada: <b>{NOMBRE_CAUSA.get(causa, causa)}</b> '
                      f'({QUE_FILTRA.get(causa, "no pasó los filtros")}). Sale a la bandeja de rechazo.')
    if t == "embalado":
        return "📦", (f'Se juntó un lote: {d["cantidad"]} monedas de {nombre_denominacion(d["denominacion"])} '
                      f'caen al vaso {d["vaso"]} ({pesos(d["valor"])}).')
    if t == "descarga":
        if d["destino"] == "entrega":
            return "🥤", f'El vaso {d["vaso"]} (tapado, {pesos(d["valor"])}) pasa a la canaleta de entrega.'
        if d["destino"] == "vacio":
            return "♻️", f'El vaso {d["vaso"]} llegó vacío: se desecha.'
        return "🚫", f'El vaso {d["vaso"]} sale a la bandeja de rechazo de vasos.'
    if t == "sabotaje_detectado":
        return "🛡️", f'<b>Sabotaje detectado</b> en el vaso {d["vaso"]} ({d["motivo"].replace("_", " ")}): se saca de la línea.'
    if t == "cortina":
        return ("🖐️", "<b>Mano en la zona de tapa y prensa</b>: la prensa sube y la cinta de vasos se detiene."
                if d["activa"] else "La zona de tapa y prensa quedó libre: la línea sigue.")
    if t == "alarma":
        return "⚠️", f'Alarma: {d.get("tipo", "").replace("_", " ")}.'
    if ev["origen"] == "carro":
        textos = {
            "carga": f'El carro se lleva el vaso {d.get("vaso")}.',
            "salida": "El carro sale del muelle.",
            "obstaculo": "El carro ve un obstáculo adelante.",
            "evasion": "El carro esquiva el obstáculo.",
            "linea_recuperada": "El carro vuelve a la línea.",
            "meta": "El carro llegó a la meta: espera que saquen el vaso.",
            "vaso_retirado": "Sacaron el vaso en la meta (lo vio el infrarrojo de la cuna): el carro vuelve.",
            "entregado": f'<b>Vaso {d.get("vaso")} entregado en la meta.</b>',
            "en_muelle": "El carro volvió al muelle.",
            "sin_enlace": "<b>El carro perdió la radio</b>: termina la vuelta solo y no se le carga otro vaso.",
            "enlace_recuperado": "La radio del carro volvió: llegan los mensajes que guardó.",
            "vuelve_con_vaso": "Sin radio y nadie sacó el vaso: el carro vuelve con él.",
            "devuelto": f'El vaso {d.get("vaso")} volvió al muelle y lo sacaron a mano.',
            # Ordenes (fase 7: asistente o botones)
            "orden": f'El carro recibió una orden: <b>{NOMBRE_ORDEN_CARRO.get(d.get("accion"), d.get("accion"))}</b>.',
            "orden_cumplida": "El carro cumplió la orden y espera otra.",
            "llego_al_punto": "El carro llegó al punto pedido.",
            "punto_con_error": f'El carro quedó a {d.get("error_m", 0) * 100:.0f} cm del punto (error de odometría).',
            "camino_bloqueado": "<b>El carro no se movió</b>: vio algo en el camino (así no choca).",
            "no_se_movio": "El carro se quedó quieto esperando otra orden.",
            "bloqueado": "<b>El carro se detuvo</b>: algo adelante.",
            "detenido_por_obstaculo": "El carro quedó quieto frente al obstáculo.",
            "atascado": "<b>El carro se detuvo</b>: una rueda patinaba (algo lo sujetaba).",
            "detenido_atascado": "El carro quedó quieto (estaba atascado).",
            "detenido_por_orden": "El carro se detuvo por orden.",
            "ruta_retomada": "El carro encontró la línea y retomó el recorrido.",
        }
        return ("🚗", textos[t]) if t in textos else None
    if t == "sabotaje":
        return "🧪", f'Prueba del operador: {str(d.get("tipo", "")).replace("_", " ")}.'
    if t == "respuesta" and d.get("origen") == "asistente":
        return ("🗣️" if d["ok"] else "✋"), f'Orden del asistente: {html.escape(d["detalle"])}.'
    return None


def frases_recientes(limite: int = 10) -> list[tuple[str, str, str]]:
    filas = conexion().execute(
        "SELECT ts, origen, tipo, payload FROM eventos WHERE tipo NOT IN ('tel', 'paso', 'orden') "
        "ORDER BY id DESC LIMIT 300").fetchall()
    out = []
    for f in filas:
        r = frase_evento(dict(f))
        if r:
            out.append((f["ts"][11:19], *r))
        if len(out) >= limite:
            break
    return out


def html_frases(frases: list[tuple[str, str, str]]) -> str:
    if not frases:
        return '<div class="nota">Todavía no pasó nada.</div>'
    return "".join(f'<div class="frase"><span class="hora">{h}</span><span class="ico">{i}</span><span>{t}</span></div>'
                   for h, i, t in frases)


def describir_evento(ev: dict) -> str:
    """Bitácora técnica (pestaña Línea en vivo): la frase simple si la hay;
    si no, el evento tal cual."""
    r = frase_evento(ev)
    hora = ev["ts"][11:19]
    if r:
        return f'<span style="color:#586069">{hora}</span> {r[0]} {r[1]}'
    datos = json.loads(ev["payload"])
    txt = ", ".join(f"{k}={v}" for k, v in datos.items() if k not in ("src", "ev", "tick"))
    return f'<span style="color:#586069">{hora}</span> <span style="color:{AMBAR}">{ev["origen"]}</span> {ev["tipo"]} <span style="color:#586069">{html.escape(txt)[:140]}</span>'


# ---------------------------------------------------------------------
# cabecera y barra lateral (control)
# ---------------------------------------------------------------------

ESTADO_LINEA_TXT = {"corriendo": "La línea está trabajando", "pausada": "La línea está en pausa",
                    "paro": "PARO de emergencia: todo detenido", "terminada": "La corrida terminó",
                    "detenida": "La línea está detenida"}


def simulacion_viva() -> bool:
    """True si el supervisor (simulacion o puente al ESP32) esta corriendo en este PC.
    Se le pregunta a su servidor local: con la corrida terminada deja de escribir
    telemetria, asi que la edad del ultimo dato no alcanza para saberlo."""
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PARAMETROS['supervisor']['puerto_http']}/api/estado",
                                    timeout=0.6) as r:
            return r.status == 200
    except OSError:
        return False


def origen_datos(tel: dict) -> tuple[str, str]:
    """(texto, clase) del chip que dice de donde salen los datos."""
    if tel.get("backend") == "real":
        if (tel.get("hardware") or {}).get("emulada"):
            return "🧪 ESP32 EMULADO (sin placa)", "origen"
        return "🔌 ESP32 REAL", "real"
    return "🖥 SIMULACIÓN (PyBullet)", "origen"


@st.fragment(run_every=REFRESCO_S)
def cabecera() -> None:
    from app.asistente import hay_internet

    tel = telemetria()
    viva = simulacion_viva()
    internet = hay_internet()
    estado = tel["linea"] if tel else "sin supervisor"
    origen, clase = origen_datos(tel) if tel else ("", "")
    st.markdown(
        f'<div class="cabecera"><h1>🪙 Logística de monedas inteligentes</h1>'
        f'<span class="chip {estado if viva else ""}">{ESTADO_LINEA_TXT.get(estado, estado)}</span>'
        + (f'<span class="chip">ciclo {tel.get("tick", "—")}</span><span class="chip {clase}">{origen}</span>' if tel else "")
        + (f'<span class="chip">🌐 con internet</span>' if internet else '<span class="chip sinred">📴 SIN INTERNET</span>')
        + '</div><div class="nota">Clasifica monedas colombianas, las empaca en vasos de una sola denominación y '
        "un carro autónomo los lleva a la meta · Elemento 7: detector de monedas y vasos · Micros y Laboratorio, UMNG</div>",
        unsafe_allow_html=True,
    )
    if tel is None:
        st.markdown(
            '<div class="aviso ambar">No hay datos todavía. Abra <b>visor.bat</b> (arranca todo) o, en una '
            "terminal, <code>python -m app.lanzar</code>.</div>", unsafe_allow_html=True)
        return
    from sim.carga_escenarios import prueba_de_un_filtro

    prueba = prueba_de_un_filtro(tel.get("escenario") or "")
    if prueba:
        piezas = consulta("SELECT causa FROM elementos WHERE veredicto != 'vacia'")
        bien = int((piezas["causa"] == prueba["causa"]).sum()) if len(piezas) else 0
        st.markdown(
            f'<div class="aviso ambar"><b>🧪 Prueba de un filtro: {prueba["nombre"]}</b> ({prueba["estacion"]}). '
            f'{prueba["espera"]} Van {len(piezas)} piezas decididas; {bien} rechazadas por '
            f'<code>{prueba["causa"]}</code>' + ("." if bien == len(piezas) else " (<b>ojo: otras causas</b>).")
            + "</div>", unsafe_allow_html=True)
    if not viva:
        hora = datetime.fromisoformat(tel["ts"])
        st.markdown(
            '<div class="aviso-grande demo"><b class="titulo">⏸ NO ES EN VIVO</b>La simulación no está corriendo: '
            f"lo que se ve son los datos guardados de la última corrida ({hora:%d/%m %H:%M}). Para verla en vivo, "
            "abra <b>visor.bat</b>.</div>", unsafe_allow_html=True)
    elif tel.get("backend") == "real" and (tel.get("hardware") or {}).get("emulada"):
        st.markdown(
            '<div class="aviso-grande demo"><b class="titulo">🧪 ESP32 EMULADO</b>Está en modo hardware real pero no '
            "hay ninguna placa conectada: responde una estación EMULADA (el mismo firmware con sensores falsos).</div>",
            unsafe_allow_html=True)
    if not internet:
        st.markdown(
            '<div class="aviso-grande offline"><b class="titulo">📴 SIN INTERNET</b>La planta, el carro y este '
            "dashboard siguen funcionando: todo pasa en este PC (ESP32 por USB, carro por ESP-NOW, datos en SQLite). "
            "El asistente responde con el modelo local de la laptop y la voz es la de este PC (Whisper para oír, voz "
            "de Windows para hablar).</div>", unsafe_allow_html=True)


@st.fragment(run_every=REFRESCO_S)
def respuesta_orden() -> None:
    r = (telemetria() or {}).get("ultima_orden")
    if r:
        clase = "ok" if r["ok"] else "no"
        st.markdown(f'<div class="respuesta {clase}">{"✔" if r["ok"] else "✖"} {html.escape(r["detalle"])}</div>',
                    unsafe_allow_html=True)


def barra_control() -> None:
    tel = telemetria() or {}
    with st.sidebar:
        st.markdown("### Controles")
        corre = tel.get("linea") == "corriendo"
        pausada = tel.get("linea") == "pausada"
        if st.button("▶ Empezar una corrida nueva", width="stretch", type="primary",
                     help="Arranca una prueba completa: monedas colombianas y un caso de cada pieza que se debe rechazar."):
            enviar({"cmd": "iniciar", "escenario": "prueba_completa",
                    "confianza_minima": st.session_state.get("confianza", tel.get("confianza_minima", 0.85)),
                    "probabilidad_error": st.session_state.get("ruido", tel.get("probabilidad_error", 0.0)),
                    "conservar_almacen": st.session_state.get("conservar", False)}, "Empezando una corrida nueva")
        c1, c2 = st.columns(2)
        if c1.button("⏸ Pausa", width="stretch", disabled=not corre):
            enviar({"cmd": "pausar"}, "Pausa")
        if c2.button("⏵ Seguir", width="stretch", disabled=not pausada):
            enviar({"cmd": "reanudar"}, "La línea sigue")
        if st.button("⛔ PARO DE EMERGENCIA", width="stretch", disabled=not (corre or pausada),
                     help="Detiene todo donde está. Para salir: empezar una corrida nueva."):
            enviar({"cmd": "paro"}, "Paro de emergencia")
        respuesta_orden()

        # Usuario, 2026-09-27: los filtros se prueban UNO POR UNO en la sustentacion. Cada prueba es
        # un escenario de un solo filtro (los mismos de las pruebas automaticas).
        from sim.carga_escenarios import PIEZAS, PRUEBAS_DE_UN_FILTRO

        st.markdown("### Probar un filtro")
        prueba = st.selectbox("Filtro", PRUEBAS_DE_UN_FILTRO, format_func=lambda p: f"{p['estacion']} · {p['nombre']}",
                              key="prueba_filtro", label_visibility="collapsed")
        st.caption(prueba["espera"])
        if st.button("🧪 Probar solo este filtro", width="stretch",
                     help="Empieza una corrida nueva con piezas que SOLO este filtro debe rechazar."):
            enviar({"cmd": "iniciar", "escenario": prueba["escenario"]}, f"Prueba de un filtro: {prueba['nombre']}")

        st.markdown("### Colocar una pieza")
        pieza = st.selectbox("Pieza", list(PIEZAS), format_func=lambda k: PIEZAS[k]["nombre"], key="pieza",
                             label_visibility="collapsed")
        if st.button("⬇ Ponerla en la próxima carga", width="stretch",
                     disabled=tel.get("linea") not in ("corriendo", "terminada"),
                     help="Como si el operador la pusiera a mano en la casilla de carga: entra antes que lo que "
                          "falta de la corrida (si la corrida terminó, sigue solo para procesarla)."):
            enviar({"cmd": "colocar", "pieza": pieza}, f"{PIEZAS[pieza]['nombre']}: a la carga")

        st.markdown("### Cómo trabaja")
        velocidad = st.select_slider(
            "Velocidad de la simulación", options=[0.25, 0.5, 1.0, 2.0, 4.0], value=float(tel.get("velocidad", 1.0)),
            format_func=lambda v: f"×{v:g}" + (" (tiempo real)" if v == 1 else ""),
            help="×1 es el ritmo real del montaje; más rápido sirve para ver una corrida completa en menos tiempo.")
        if velocidad != float(tel.get("velocidad", 1.0)) and st.session_state.get("vel_enviada") != velocidad:
            st.session_state["vel_enviada"] = velocidad
            enviar({"cmd": "velocidad", "valor": velocidad}, f"Velocidad ×{velocidad:g}")
        lote_actual = int(tel.get("monedas_por_vaso") or PARAMETROS["planta"]["monedas_por_vaso"])
        capacidad = int(tel.get("capacidad_tubo") or PARAMETROS["planta"]["capacidad_tubo"])
        lote = st.number_input("Monedas por vaso", 1, capacidad, min(lote_actual, capacidad), 1,
                               help="Cuando un tubo del almacén junta este número de monedas, las suelta a un vaso.")
        if lote != lote_actual and st.session_state.get("lote_enviado") != lote:
            st.session_state["lote_enviado"] = lote
            enviar({"cmd": "lote", "valor": int(lote)}, f"{lote} monedas por vaso")

        with st.expander("Ajustes avanzados (se aplican al empezar)"):
            st.slider("Confianza mínima del reconocimiento", 0.50, 0.99, float(tel.get("confianza_minima", 0.85)), 0.01,
                      key="confianza",
                      help="Si el reconocimiento de la moneda está menos seguro que esto, la pieza se rechaza "
                           "como 'no reconocida'.")
            st.slider("Errores forzados del reconocimiento", 0.0, 0.5, float(tel.get("probabilidad_error", 0.0)), 0.05,
                      key="ruido",
                      help="Para probar: probabilidad de que el reconocimiento se equivoque con una moneda buena.")
            st.checkbox("Empezar con lo que quedó guardado en los tubos",
                        value=bool(PARAMETROS["planta"].get("conservar_almacen_entre_turnos", False)), key="conservar",
                        help="Si el turno anterior no empacó lo guardado, el nuevo arranca con esas monedas.")
            st.caption("Hoy corre en simulación. El hardware real (dos ESP32, fase 8) ya está hecho en software: "
                       "`hardware.backend: real` en config/parametros.yaml; falta probarlo en las placas.")
        st.markdown('<div class="nota">Los botones dejan una orden que el programa de la línea toma en menos de '
                    "medio segundo; la respuesta aparece arriba, en verde o en rojo.</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------
# pestaña Resumen
# ---------------------------------------------------------------------


def datos_corrida() -> dict:
    elementos = consulta("SELECT * FROM elementos ORDER BY id")
    vasos = consulta("SELECT * FROM vasos")
    return {"elementos": elementos, "vasos": vasos,
            "aceptadas": elementos[elementos["veredicto"] == "aceptada"],
            "rechazadas": elementos[elementos["veredicto"] == "rechazada"]}


def tarjeta(titulo: str, estado: str, color: str, detalle: str) -> str:
    return (f'<div class="tarjeta" style="border-left-color:{color}"><div class="t-titulo">{titulo}</div>'
            f'<div class="t-estado" style="color:{color}">{estado}</div><div class="t-detalle">{detalle}</div></div>')


@st.fragment(run_every=REFRESCO_S)
def pestana_resumen() -> None:
    tel = telemetria()
    if not tel:
        st.info("Cuando la línea arranque, aquí se ve todo lo importante de un vistazo.")
        return
    d = datos_corrida()
    aceptadas, rechazadas = d["aceptadas"], d["rechazadas"]
    entregados = [v for v in tel.get("vasos_salida") or [] if v["destino"] == "entrega"]
    k = st.columns(5)
    k[0].metric("💰 Valor aceptado", pesos(aceptadas["valor"].sum()),
                help="Suma del valor de todas las monedas colombianas aceptadas en esta corrida.")
    k[1].metric("🪙 Monedas aceptadas", len(aceptadas))
    k[2].metric("🚫 Piezas rechazadas", len(rechazadas),
                help="Botones, bloques, monedas extranjeras y todo lo que no pasó los filtros.")
    k[3].metric("🥤 Vasos entregados", len(entregados), help="Vasos tapados que el carro llevó a la meta.")
    k[4].metric("⚖️ Peso estimado", f'{aceptadas["masa_estimada_g"].sum():.0f} g',
                help="Estimado por conteo: masa nominal de cada moneda reconocida (no hay balanza).")

    # Estado de cada parte, en una línea.
    c = tel.get("carro") or {}
    radio = c.get("radio") or {}
    alarmas = tel.get("alarmas") or []
    tarjetas = [
        tarjeta("Cinta de monedas", "trabajando" if tel["linea"] == "corriendo" else ESTADO_LINEA_TXT.get(tel["linea"], tel["linea"]).lower(),
                VERDE if tel["linea"] == "corriendo" else GRIS,
                f'{tel.get("pendientes", 0)} piezas por cargar' + (" · una moneda espera en la descarga" if tel.get("moneda_en_espera") else "")),
        tarjeta("Almacén", pesos(tel.get("almacen_valor", 0)) + " guardado", AMBAR,
                f'lotes de {tel.get("monedas_por_vaso")} monedas por vaso'),
        tarjeta("Cinta de vasos", "detenida por la cortina" if tel.get("cortina_activa") else "normal",
                ROJO if tel.get("cortina_activa") else VERDE,
                f'{tel.get("tapas_restantes", 0)} tapas en el tubo · {len(tel.get("canaleta") or [])} vasos esperando al carro'),
        tarjeta("Carro", ESTADO_CARRO.get(c.get("estado"), "—") if c else "reemplazo simulado",
                AZUL if c else GRIS,
                (("📡 con radio" if radio.get("enlace") else "📡 <b style='color:#e5534b'>sin radio</b>")
                 + (f' · lleva el vaso {c["vaso_id"]}' if c.get("vaso_id") else "")) if c else "sin carro con física"),
    ]
    st.markdown(f'<div class="tarjetas">{"".join(tarjetas)}</div>', unsafe_allow_html=True)
    if alarmas:
        st.markdown('<div class="aviso ambar">⚠️ ' + " · ".join(str(a).replace("_", " ") for a in alarmas) + "</div>",
                    unsafe_allow_html=True)

    izq, der = st.columns([1.35, 1])
    with izq:
        st.markdown("**Recorrido de las piezas** <span class='nota'>· de lo que se cargó en la cinta, qué pasó con "
                    "cada cosa (el grosor es la cantidad)</span>", unsafe_allow_html=True)
        st.plotly_chart(figura_recorrido(d, tel), width="stretch", config={"displayModeBar": False})
    with der:
        st.markdown("**Qué está pasando**", unsafe_allow_html=True)
        st.markdown(f'<div class="frases">{html_frases(frases_recientes(11))}</div>', unsafe_allow_html=True)


def figura_recorrido(d: dict, tel: dict) -> go.Figure:
    """Diagrama de flujo (Sankey): cargadas -> aceptadas / rechazadas por
    etapa -> tubos / vasos -> entregadas."""
    aceptadas, rechazadas = d["aceptadas"], d["rechazadas"]
    n_mat = int((rechazadas["causa"] == reglas.CAUSA_NO_METALICO).sum())
    n_vis = len(rechazadas) - n_mat
    entregadas = int(sum(v["cantidad"] for v in tel.get("vasos_salida") or [] if v["destino"] == "entrega"))
    en_vasos = entregadas + int(sum((v or {}).get("cantidad", 0) for v in tel.get("casillas_vasos") or [] if v))
    # Lo de esta corrida que no esta en vasos sigue en los tubos (los tubos
    # pueden traer, ademas, monedas del turno anterior).
    en_vasos = min(en_vasos, len(aceptadas))
    guardadas = len(aceptadas) - en_vasos
    nodos = ["Cargadas en la cinta", "Aceptadas", "Rechazo por material", "Rechazo por visión",
             "Guardadas en los tubos", "En vasos", "Entregadas en la meta"]
    colores = [GRIS, VERDE, AZUL, MORADO, AMBAR, AMBAR, VERDE]
    enlaces = [(0, 1, len(aceptadas)), (0, 2, n_mat), (0, 3, n_vis), (1, 4, guardadas), (1, 5, en_vasos),
               (5, 6, min(entregadas, en_vasos))]
    enlaces = [e for e in enlaces if e[2] > 0]
    fig = figura_base(330)
    if not enlaces:
        fig.add_annotation(text="todavía no hay piezas procesadas", showarrow=False, font=dict(color=GRIS))
        return fig
    fig.add_trace(go.Sankey(
        arrangement="snap",
        node=dict(label=[f"{n}" for n in nodos], color=colores, pad=18, thickness=16, line=dict(width=0)),
        link=dict(source=[e[0] for e in enlaces], target=[e[1] for e in enlaces], value=[e[2] for e in enlaces],
                  color="rgba(139,148,158,0.28)", hovertemplate="%{value} piezas<extra></extra>"),
        textfont=dict(color="#e6e8eb", size=13)))
    return fig


# ---------------------------------------------------------------------
# pestaña Monedas y vasos
# ---------------------------------------------------------------------


@st.fragment(run_every=REFRESCO_S)
def pestana_produccion() -> None:
    d = datos_corrida()
    aceptadas, vasos = d["aceptadas"], d["vasos"]
    tel = telemetria() or {}
    izq, der = st.columns(2)
    with izq:
        st.markdown("**Monedas aceptadas por denominación**", unsafe_allow_html=True)
        conteo = aceptadas.groupby("denominacion").size().reindex(DENOMINACIONES, fill_value=0)
        valor = aceptadas.groupby("denominacion")["valor"].sum().reindex(DENOMINACIONES, fill_value=0)
        fig = figura_base(300)
        fig.add_bar(x=[pesos(x) for x in conteo.index], y=conteo.values, marker_color=AMBAR,
                    text=[f"{n} · {pesos(v)}" for n, v in zip(conteo.values, valor.values)], textposition="outside",
                    hovertemplate="%{x}: %{y} monedas<extra></extra>")
        fig.update_yaxes(dtick=1, rangemode="tozero", title="monedas")
        fig.update_xaxes(type="category")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with der:
        st.markdown("**Valor acumulado en el tiempo**", unsafe_allow_html=True)
        fig = figura_base(300)
        if len(aceptadas):
            serie = aceptadas.assign(ts=pd.to_datetime(aceptadas["ts"]), acumulado=aceptadas["valor"].cumsum())
            fig.add_scatter(x=serie["ts"], y=serie["acumulado"], mode="lines", line_shape="hv", fill="tozeroy",
                            line=dict(color=VERDE, width=3), fillcolor="rgba(63,182,139,0.12)",
                            hovertemplate="%{x|%H:%M:%S}: %{y:$,.0f}<extra></extra>")
            fig.update_yaxes(tickprefix="$", rangemode="tozero")
        else:
            fig.add_annotation(text="todavía no hay monedas aceptadas", showarrow=False, font=dict(color=GRIS))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.markdown(f"**Almacén: cuánto hay en cada tubo** <span class='nota'>· la línea punteada es el lote "
                f"({tel.get('monedas_por_vaso', '—')} monedas): al llegar, el tubo suelta las monedas a un vaso</span>",
                unsafe_allow_html=True)
    almacen = tel.get("almacen") or {}
    claves = ["50", "100", "200", "500", "1000", "otras"]
    fig = figura_base(230)
    fig.add_bar(x=[pesos(int(c)) if c != "otras" else "otras" for c in claves], y=[int(almacen.get(c, 0)) for c in claves],
                marker_color=[VERDE if int(almacen.get(c, 0)) >= (tel.get("monedas_por_vaso") or 99) else AMBAR for c in claves],
                text=[int(almacen.get(c, 0)) for c in claves], textposition="outside")
    if tel.get("monedas_por_vaso"):
        fig.add_hline(y=tel["monedas_por_vaso"], line_dash="dot", line_color="#e6e8eb")
    fig.update_xaxes(type="category")
    fig.update_yaxes(rangemode="tozero", range=[0, max(tel.get("capacidad_tubo") or 25, 1)], title="monedas")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    if len(vasos):
        st.markdown("**Vasos de esta corrida**", unsafe_allow_html=True)
        tabla = pd.DataFrame({
            "Vaso": vasos["id"],
            "Estado": [ESTADO_VASO_TXT.get(e, e) for e in vasos["estado"]],
            "De": [nombre_denominacion(x) if pd.notna(x) else "—" for x in vasos["denominacion"]],
            "Monedas": vasos["cantidad_monedas"],
            "Valor": [pesos(x) for x in vasos["valor_total"]],
            "Llenado": vasos["ts_llenado"].str.slice(11, 19).fillna("—"),
            "Entregado": vasos["ts_entrega"].str.slice(11, 19).fillna("—"),
        })
        st.dataframe(tabla, hide_index=True, width="stretch")


# ---------------------------------------------------------------------
# pestaña Calidad del filtro
# ---------------------------------------------------------------------

DECISIONES = ["Aceptada", "No metálico", "Fuera de rango", "No circular", "Perforado", "No reconocida", "Incoherente"]


def matriz_aciertos() -> pd.DataFrame:
    """Qué era cada pieza (lo sabe la simulación) contra qué decidió la línea."""
    filas = conexion().execute(
        "SELECT tipo, payload FROM eventos WHERE tipo IN ('presencia', 'elemento_final') ORDER BY id").fetchall()
    real, decision = {}, {}
    for f in filas:
        p = json.loads(f["payload"])
        if f["tipo"] == "presencia" and p.get("tipo_real"):
            real[p["casilla"]] = (p["tipo_real"], p.get("clase_real"))
        elif f["tipo"] == "elemento_final":
            decision[p["casilla"]] = "Aceptada" if p["veredicto"] == "aceptada" else NOMBRE_CAUSA.get(p.get("causa"), "No reconocida")
    datos = []
    for casilla, dec in decision.items():
        tipo, clase = real.get(casilla, ("?", None))
        if tipo == "moneda":
            cat = "Moneda colombiana" if clase and tabla_monedas.reconocible(clase) else "Moneda que debe rechazarse"
        else:
            cat = NOMBRE_TIPO_REAL.get(tipo, tipo).capitalize()
        datos.append({"real": cat, "decision": dec})
    return pd.DataFrame(datos)


@st.fragment(run_every=REFRESCO_S)
def pestana_calidad() -> None:
    m = matriz_aciertos()
    if not len(m):
        st.info("Cuando empiecen a pasar piezas, aquí se ve qué tan bien separa la línea lo bueno de lo malo.")
        return
    bien = ((m["real"] == "Moneda colombiana") & (m["decision"] == "Aceptada")) | \
           ((m["real"] != "Moneda colombiana") & (m["decision"] != "Aceptada"))
    k = st.columns(4)
    k[0].metric("🎯 Decisiones correctas", f"{bien.mean() * 100:.0f} %", help="Monedas colombianas aceptadas y todo lo demás rechazado.")
    k[1].metric("Monedas buenas rechazadas", int(((m["real"] == "Moneda colombiana") & (m["decision"] != "Aceptada")).sum()),
                help="Quedan en la bandeja de rechazo: se recuperan, no se pierden.")
    k[2].metric("Piezas malas aceptadas", int(((m["real"] != "Moneda colombiana") & (m["decision"] == "Aceptada")).sum()),
                help="Lo más grave: algo que no es una moneda colombiana termina en un vaso.")
    k[3].metric("Piezas procesadas", len(m))

    izq, der = st.columns([1.4, 1])
    with izq:
        st.markdown("**Qué era cada pieza y qué decidió la línea** <span class='nota'>· en verde, los aciertos</span>",
                    unsafe_allow_html=True)
        filas = [r for r in ["Moneda colombiana", "Moneda que debe rechazarse", "Botón de plástico", "Botón metálico", "Bloque", "Mano"]
                 if r in set(m["real"])]
        tabla = pd.crosstab(m["real"], m["decision"]).reindex(index=filas, columns=DECISIONES, fill_value=0)
        z = tabla.values
        acierto = [[(r == "Moneda colombiana") == (c == "Aceptada") for c in DECISIONES] for r in filas]
        colz = [[(1 if a else -1) * (v > 0) for a, v in zip(fila_a, fila_v)] for fila_a, fila_v in zip(acierto, z)]
        fig = figura_base(80 + 46 * len(filas))
        fig.add_trace(go.Heatmap(z=colz, x=DECISIONES, y=filas, text=z, texttemplate="%{text}",
                                 colorscale=[[0, "rgba(229,83,75,0.55)"], [0.5, "#161b22"], [1, "rgba(63,182,139,0.55)"]],
                                 zmin=-1, zmax=1, showscale=False, xgap=3, ygap=3, hoverinfo="skip",
                                 textfont=dict(color="#ffffff", size=15)))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with der:
        st.markdown("**Por qué se rechaza cada cosa**", unsafe_allow_html=True)
        rechazos = consulta("SELECT causa, COUNT(*) AS n FROM elementos WHERE veredicto = 'rechazada' GROUP BY causa")
        conteo = {c: 0 for c in reglas.CAUSAS_VALIDAS}
        conteo.update(dict(zip(rechazos["causa"], rechazos["n"])))
        for c in reglas.CAUSAS_VALIDAS:
            etapa = "sensores de material" if ETAPA_DE_CAUSA.get(c) == "material" else "cámara"
            st.markdown(f"- **{NOMBRE_CAUSA[c]}** — {conteo[c]} · {QUE_FILTRA[c]} <span class='nota'>({etapa})</span>",
                        unsafe_allow_html=True)
        sin = [NOMBRE_CAUSA[c] for c, n in conteo.items() if n == 0]
        if sin and sum(conteo.values()):
            st.caption("Filtros que no actuaron en esta corrida: " + ", ".join(sin) + ".")

    filas_v = conexion().execute("SELECT payload FROM eventos WHERE tipo = 'vision' ORDER BY id DESC LIMIT 15").fetchall()
    if filas_v:
        with st.expander("Detalle de la cámara: las últimas 15 piezas medidas"):
            datos = [json.loads(f["payload"]) for f in filas_v]
            st.dataframe(pd.DataFrame([{
                "Pieza": x["casilla"], "Diámetro": f'{x["diametro_mm"]:.2f} mm', "Redondez": f'{x["circularidad"]:.2f}',
                "Agujeros": x["contornos_internos"], "La cámara cree que es": x["clase"],
                "Seguridad": f'{x["confianza"] * 100:.0f} %',
                "Decisión": "aceptada" if x["veredicto"] == "aceptada" else NOMBRE_CAUSA.get(x.get("causa"), x.get("causa")),
            } for x in datos]), hide_index=True, width="stretch")
            st.caption("Hoy la cámara es simulada (el reconocimiento sabe qué es cada pieza y se le puede forzar "
                       "error); la visión real con el modelo entrenado llega en la fase 5.")


# ---------------------------------------------------------------------
# pestaña Línea en vivo
# ---------------------------------------------------------------------


def boton_orden(etiqueta: str, orden: dict, aviso: str, activa: bool, ayuda: str, clave: str) -> None:
    if st.button(etiqueta, width="stretch", disabled=not activa, help=ayuda, key=clave):
        enviar(orden, aviso)


@st.fragment(run_every=REFRESCO_S)
def pestana_linea() -> None:
    tel = telemetria()
    if not tel or not tel.get("casillas_monedas"):
        st.info("La línea todavía no arrancó. Use **▶ Empezar una corrida nueva** en la barra de la izquierda.")
        return
    if tel.get("cortina_activa"):
        st.markdown('<div class="aviso rojo">🖐 <b>Mano en la zona de tapa y prensa</b>: la prensa subió y se detuvo; '
                    "la cinta de vasos no avanza. La cinta de monedas sigue.</div>", unsafe_allow_html=True)
    s = tel["sensores"]
    st.markdown(f"**Cinta de monedas** <span class='nota'>· quedan {tel['pendientes']} piezas por cargar</span>",
                unsafe_allow_html=True)
    st.markdown(html_cinta_monedas(tel), unsafe_allow_html=True)
    st.markdown(html_leds([("infrarrojo de presencia (1)", s["presencia"], False),
                           ("capacitivo, bajo la cinta (2)", s["capacitivo"], False),
                           ("inductivo, bajo la cinta (3)", s["inductivo"], False)]), unsafe_allow_html=True)
    st.markdown("**Almacén tipo revólver** <span class='nota'>· cada moneda aceptada va al tubo de su "
                f"denominación; con {tel['monedas_por_vaso']} se suelta el lote a un vaso</span>", unsafe_allow_html=True)
    st.markdown(html_almacen(tel), unsafe_allow_html=True)
    st.markdown(f"**Cinta de vasos** <span class='nota'>· tapas en el tubo: {tel['tapas_restantes']} · "
                f"prensadas: {tel['ciclos_prensa']}</span>", unsafe_allow_html=True)
    st.markdown(html_cinta_vasos(tel), unsafe_allow_html=True)
    st.markdown(html_leds([("cortina de seguridad (8)", s["cortina"], True),
                           ("sensor del interior del vaso (5)", s.get("sensor_interior", False), False),
                           ("Hall del carrusel (6)", s.get("hall_carrusel", False), False)]), unsafe_allow_html=True)

    izq, der = st.columns([1, 1.4])
    with izq:
        st.markdown("**Pruebas: hágale algo a la línea**", unsafe_allow_html=True)
        st.markdown('<div class="nota">La línea se tiene que dar cuenta sola, con sus sensores.</div>',
                    unsafe_allow_html=True)
        activa = tel["linea"] in ("corriendo", "pausada")
        cv = tel.get("casillas_vasos") or []
        hay_vl = activa and bool(cv and (cv[0] or (len(cv) > 1 and cv[1])))
        a, b = st.columns(2)
        with a:
            boton_orden("Retirar un vaso", {"cmd": "sabotaje", "tipo": "retirar_vaso"}, "Vaso retirado", hay_vl,
                        "Alguien se lleva un vaso de la verificación o del llenado.", "s1")
            boton_orden("Cambiar por un vaso igual", {"cmd": "sabotaje", "tipo": "vaso_igual"}, "Vaso cambiado", hay_vl,
                        "Mismo tamaño, otro marcador: lo detecta la cámara de vasos.", "s2")
            boton_orden("✋ Mano en la carga", {"cmd": "sabotaje", "tipo": "mano_carga"}, "Mano en la carga", activa,
                        "El infrarrojo la ve; la casilla viaja vacía y sale al rechazo.", "s3")
            boton_orden("✋ Mano que saca un vaso", {"cmd": "sabotaje", "tipo": "mano_saca_vaso"}, "Una mano se llevó un vaso",
                        activa, "La cortina congela la zona y la cámara encuentra el vaso que falta.", "s4")
        with b:
            boton_orden("Cambiar por una figura", {"cmd": "sabotaje", "tipo": "cambiar_vaso"}, "Vaso cambiado por figura",
                        hay_vl, "Otra forma: la silueta no coincide.", "s5")
            boton_orden("Vaso con algo adentro", {"cmd": "sabotaje", "tipo": "vaso_con_algo"}, "El próximo vaso trae algo",
                        activa, "Lo detecta el sensor que mira al interior del vaso.", "s6")
            boton_orden("✋ Quitar la mano" if tel.get("intruso") else "✋ Mano en tapa/prensa",
                        {"cmd": "sabotaje", "tipo": "intruso_off" if tel.get("intruso") else "intruso_on"},
                        "Mano quitada" if tel.get("intruso") else "Mano en la zona", activa,
                        "Activa la cortina de seguridad.", "s7")
            radio = ((tel.get("carro") or {}).get("radio") or {})
            boton_orden("📡 Reconectar la radio" if radio and not radio.get("conectada") else "📡 Cortar la radio del carro",
                        {"cmd": "sabotaje", "tipo": "radio_on" if radio and not radio.get("conectada") else "radio_off"},
                        "Radio del carro", activa and bool(radio),
                        "El carro termina la vuelta solo y guarda sus mensajes; no se le carga otro vaso a ciegas.", "s8")
        boton_orden("📦 Empacar lo guardado en los tubos (fin de turno)", {"cmd": "embalar_parciales"}, "Empacando",
                    bool(tel.get("almacen_valor")), "Empaca también los tubos que no completaron un lote.", "s9")
    with der:
        st.markdown("**Bitácora detallada**", unsafe_allow_html=True)
        lineas = "<br>".join(describir_evento(e) for e in eventos_recientes(16))
        st.markdown(f'<div class="bitacora">{lineas}</div>', unsafe_allow_html=True)


@st.fragment(run_every=REFRESCO_S)
def costos_proyecto() -> None:
    """Costo en Colombia por subsistema y dónde abaratar (config/precios.yaml)."""
    from app import costos

    datos = costos.cargar()
    subs = costos.por_subsistema(datos)
    st.markdown(f"**Costo del proyecto en Colombia: {costos.pesos(costos.total(datos))}** "
                f"<span class='nota'>· precios del {datos['consultado']}, sin el portátil; detalle en "
                "<code>docs/costos.md</code></span>", unsafe_allow_html=True)
    fig = figura_base(240)
    orden = sorted(subs.items(), key=lambda x: x[1])
    fig.add_bar(x=[v for _, v in orden], y=[n for n, _ in orden], orientation="h", marker_color=AMBAR,
                text=[costos.pesos(v) for _, v in orden], textposition="outside",
                hovertemplate="%{y}: %{text}<extra></extra>")
    fig.update_xaxes(tickprefix="$", rangemode="tozero")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.dataframe(pd.DataFrame([{"Dónde abaratar (propuesta)": a["titulo"], "Ahorro": costos.pesos(a["ahorro"]),
                                "Riesgo": a["riesgo"]} for a in costos.ahorros(datos)]),
                 hide_index=True, width="stretch")


def pestana_replicacion() -> None:
    """Lo que hay que saber para construirlo de verdad: si los tiempos
    caben, cuanto tardaria esta corrida en el montaje real y cuantas veces
    se equivocaron los sensores simulados con su error individual."""
    tel = telemetria() or {}
    t = PARAMETROS["tiempos_ms"]
    r = presupuesto(t, lote=PARAMETROS["planta"]["monedas_por_vaso"],
                    lecturas_por_decision=PARAMETROS["planta"]["lecturas_por_decision"],
                    fotos_por_moneda=PARAMETROS["planta"]["fotos_por_moneda"],
                    reaccion_cortina_max_ms=PARAMETROS["cortina_seguridad"]["reaccion_max_ms"])
    st.markdown('<div class="nota">Todos los valores son PROVISIONALES (hojas de datos): se reemplazan por lo '
                "que se mida en el montaje. Detalle completo y cómo medir cada cosa en "
                "<code>docs/replicacion.md</code>.</div>", unsafe_allow_html=True)
    k = st.columns(4)
    k[0].metric("Ciclo de la cinta de monedas", f"{r['ciclo_monedas_ms']} ms")
    k[1].metric("Ritmo", f"{r['elementos_por_minuto']:.0f} elem/min")
    k[2].metric("Esta corrida en el montaje real", f"≈ {tiempo_real_estimado_s(tel.get('tick', 0), t):.0f} s",
                help="Ticks de la corrida × (avance + pausa). Cota inferior: no cuenta esperas por tubos llenos.")
    k[3].metric("Reacción de la cortina", f"{r['reaccion_cortina_ms']} ms")

    st.markdown("**Presupuesto de tiempos: ¿cabe cada acción en su hueco?**")
    tabla = pd.DataFrame([{
        "Chequeo": c.nombre, "Necesita (ms)": round(c.necesita_ms), "Disponible (ms)": round(c.disponible_ms),
        "Margen (ms)": round(c.margen_ms), "Estado": "OK" if c.ok else "NO CABE", "Por qué": c.explicacion,
    } for c in r["chequeos"]])
    st.dataframe(tabla, hide_index=True, width="stretch")
    justos = [c.nombre for c in r["chequeos"] if c.ok and c.margen_ms < 0.15 * c.disponible_ms]
    if justos:
        st.warning("Margen justo (menos del 15 %): " + "; ".join(justos) + ". Medirlo primero en el montaje.")

    izq, der = st.columns(2)
    with izq:
        st.markdown("**Errores de los sensores en esta corrida**")
        errores = tel.get("errores_filtrado", {})
        if not tel.get("errores_sensores_activos"):
            st.info("Esta corrida usa sensores perfectos (config: simulacion.errores_sensores = false).")
        e1, e2 = st.columns(2)
        e1.metric("Monedas colombianas rechazadas por error", errores.get("falsos_rechazos", 0),
                  help="Quedan en la bandeja de rechazo: se pueden recuperar, no se pierden.")
        e2.metric("Piezas no colombianas aceptadas", errores.get("falsas_aceptaciones", 0))
        st.metric("Monedas en el vaso equivocado (clase confundida)", errores.get("clase_equivocada", 0),
                  help="Moneda colombiana reconocida como otra denominación: la atajan las dos fotos y la "
                       "regla de coherencia con el diámetro.")
        st.markdown(f'<div class="nota">Cada estación lee su sensor {PARAMETROS["planta"]["lecturas_por_decision"]} '
                    "veces y decide por mayoría. Error por lectura de cada sensor: bloque "
                    "<code>errores_sensores</code> de la configuración.</div>", unsafe_allow_html=True)
    with der:
        costos_proyecto()
        pendientes = tabla_monedas.sin_verificar()
        st.markdown(f"**Monedas por medir** <span class='nota'>· {len(pendientes)} clases con medidas "
                    "provisionales</span>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([{"Clase": m.clase, "Diámetro (mm)": m.diametro_mm, "Masa (g)": m.masa_g,
                                    "Material": m.material} for m in pendientes]),
                     hide_index=True, width="stretch", height=240)


@st.cache_data(ttl=30, show_spinner=False)
def geometria_pista() -> dict | None:
    """La pista (linea, muros, meta, muelle) la da el supervisor por HTTP (el
    dashboard no importa PyBullet); si no esta corriendo, la de la demo."""
    import urllib.request

    try:
        with urllib.request.urlopen(f"{URL_VISOR}/api/geometria", timeout=1.5) as r:
            return json.loads(r.read())["pista"]
    except (OSError, ValueError, KeyError):
        demo = RAIZ / "app" / "visor3d" / "demo" / "geometria.json"
        return json.loads(demo.read_text(encoding="utf-8"))["pista"] if demo.exists() else None


ESTADO_CARRO = {"siguiendo": "sigue la línea", "maniobra": "maniobrando", "en_meta": "en la meta",
                "esperando_carga": "en el muelle", "detenido": "detenido", "manual": "cumpliendo una orden",
                "esperando_orden": "quieto, espera otra orden"}
NOMBRE_ORDEN_CARRO = {"detener": "detenerse", "avanzar": "avanzar", "retroceder": "retroceder", "girar": "girar",
                      "ir_a": "ir a un punto", "ir_meta": "ir a la meta", "volver_muelle": "volver al muelle",
                      "seguir_linea": "retomar la línea"}
NOMBRE_EVENTO_RUTA = {"obstaculo": "obstáculo visto", "evasion": "esquiva", "linea_recuperada": "vuelve a la línea",
                      "meta": "meta", "en_muelle": "en el muelle", "marca_giro": "marca de giro",
                      "linea_perdida": "perdió la línea", "error": "detenido", "orden": "orden recibida",
                      "camino_bloqueado": "camino bloqueado: no se movió", "bloqueado": "se detuvo: algo adelante",
                      "atascado": "atascado: se detuvo", "llego_al_punto": "llegó al punto",
                      "ruta_retomada": "retomó la línea"}


def pestana_ruta() -> None:
    """Punto 14: mapa de la pista con el recorrido real del carro (tabla
    `ruta`), los muros, los eventos de evasion y el estado del carro."""
    pista = geometria_pista()
    tel = telemetria() or {}
    carro = tel.get("carro")
    ruta = consulta("SELECT posicion_x AS x, posicion_y AS y, evento_obstaculo AS ev, estado_vehiculo AS estado "
                    "FROM ruta ORDER BY id")
    traza = ruta[ruta["ev"].isna()]
    hitos = ruta[ruta["ev"].notna()]
    entregados = consulta("SELECT COUNT(*) AS n FROM eventos WHERE origen = 'carro' AND tipo = 'entregado'")["n"][0]
    evasiones = int((hitos["ev"] == "evasion").sum())
    distancia = float(((traza["x"].diff() ** 2 + traza["y"].diff() ** 2) ** 0.5).sum()) if len(traza) > 1 else 0.0

    k = st.columns(3)
    k[0].metric("Vasos entregados en la meta", int(entregados))
    k[1].metric("Obstáculos esquivados", evasiones)
    k[2].metric("Distancia recorrida", f"{distancia:.1f} m")

    if pista is None:
        st.info("No hay geometría de la pista: arranque el supervisor.")
        return
    fig = figura_base(620)
    lx = [q[0] for q in pista["linea"]]
    ly = [q[1] for q in pista["linea"]]
    fig.add_scatter(x=lx, y=ly, mode="lines", line=dict(color="#d8d3c6", width=16), hoverinfo="skip")
    fig.add_scatter(x=lx, y=ly, mode="lines", line=dict(color="#0a0a0a", width=3), hoverinfo="skip")
    for i, o in enumerate(pista["obstaculos"]):
        nx, ny = -math.sin(o["rumbo"]) * o["largo"] / 2, math.cos(o["rumbo"]) * o["largo"] / 2
        fig.add_scatter(x=[o["x"] - nx, o["x"] + nx], y=[o["y"] - ny, o["y"] + ny], mode="lines",
                        line=dict(color=ROJO, width=7), hovertext=f"Muro {i + 1}", hoverinfo="text")
    for clave, color, texto, lado in (("franja_meta", VERDE, "META", "top center"),
                                      ("franja_giro", GRIS, "marca de giro", "middle left")):
        f = pista.get(clave)
        if f:
            fig.add_scatter(x=[f["x"]], y=[f["y"]], mode="markers+text", text=[texto], textposition=lado,
                            marker=dict(color=color, size=11, symbol="square"), hoverinfo="skip")
    sal = pista["salida"]
    fig.add_scatter(x=[sal["x"]], y=[sal["y"]], mode="markers+text", text=["muelle"], textposition="middle left",
                    marker=dict(color=AMBAR, size=12, symbol="diamond"), hoverinfo="skip")
    if len(traza):
        fig.add_scatter(x=traza["x"], y=traza["y"], mode="lines", line=dict(color=AMBAR, width=2),
                        hoverinfo="skip")
    for ev, color, simbolo in (("obstaculo", ROJO, "x"), ("evasion", MORADO, "triangle-up"),
                               ("linea_recuperada", VERDE, "circle"), ("error", ROJO, "octagon")):
        h = hitos[hitos["ev"] == ev]
        if len(h):
            fig.add_scatter(x=h["x"], y=h["y"], mode="markers", marker=dict(color=color, size=9, symbol=simbolo),
                            hovertext=[f"{NOMBRE_EVENTO_RUTA[ev]} ({e})" for e in h["estado"]], hoverinfo="text")
    if carro and carro.get("odometria"):
        # Donde CREE el carro que esta (encoders): la distancia a la flecha
        # azul es el error que acumula la odometria (vuelve a 0 en el muelle).
        ox, oy, _ = carro["odometria"]
        fig.add_scatter(x=[ox], y=[oy], mode="markers", marker=dict(color="rgba(0,0,0,0)", size=15, symbol="circle",
                                                                    line=dict(color=AZUL, width=2)),
                        hovertext=f"donde cree que está (odometría): error "
                                  f"{math.hypot(ox - carro['x'], oy - carro['y']) * 1000:.0f} mm", hoverinfo="text")
    for ev, color, simbolo in (("orden", AMBAR, "star"), ("camino_bloqueado", ROJO, "square-x"),
                               ("bloqueado", ROJO, "square-x"), ("atascado", ROJO, "hexagon")):
        h = hitos[hitos["ev"] == ev]
        if len(h):
            fig.add_scatter(x=h["x"], y=h["y"], mode="markers", marker=dict(color=color, size=10, symbol=simbolo),
                            hovertext=[NOMBRE_EVENTO_RUTA.get(ev, ev)] * len(h), hoverinfo="text")
    if carro:
        fig.add_scatter(x=[carro["x"]], y=[carro["y"]], mode="markers",
                        marker=dict(color=AZUL, size=16, symbol="triangle-up", angle=90 - math.degrees(carro["rumbo"]),
                                    line=dict(color="#ffffff", width=1)),
                        hovertext=f"carro: {carro['fase']} · {carro['estado']}", hoverinfo="text")
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown(f'<div class="nota">Línea amarilla: recorrido real del carro (simulación con física). '
                f'<span style="color:{ROJO}">✕</span> obstáculo visto (3 lecturas seguidas del ultrasónico) · '
                f'<span style="color:{MORADO}">▲</span> empieza a esquivar · '
                f'<span style="color:{VERDE}">●</span> vuelve a la línea · '
                f'<span style="color:{AMBAR}">★</span> orden recibida · '
                f'<span style="color:{AZUL}">○</span> donde cree el carro que está (odometría).</div>',
                unsafe_allow_html=True)
    if len(hitos):
        st.markdown("**Eventos del recorrido**")
        st.dataframe(pd.DataFrame({"evento": [NOMBRE_EVENTO_RUTA.get(e, e) for e in hitos["ev"]],
                                   "tramo": hitos["estado"], "x (m)": hitos["x"].round(3), "y (m)": hitos["y"].round(3)})
                     .iloc[::-1], hide_index=True, width="stretch", height=260)


def viajes_del_carro() -> pd.DataFrame:
    """Cada viaje del carro: cuando salio, llego a la meta, le sacaron el
    vaso y volvio (eventos del carro)."""
    filas = conexion().execute(
        "SELECT ts, tipo, payload FROM eventos WHERE origen = 'carro' AND tipo IN "
        "('carga', 'meta', 'vaso_retirado', 'en_muelle', 'entregado', 'vuelve_con_vaso') ORDER BY id").fetchall()
    viajes, actual = [], None
    for f in filas:
        t = datetime.fromisoformat(f["ts"])
        p = json.loads(f["payload"])
        if f["tipo"] == "carga":
            actual = {"Vaso": p.get("vaso"), "Sale": t, "Meta": None, "Entregado": "—", "Vuelve": None}
            viajes.append(actual)
        elif actual is not None:
            if f["tipo"] == "meta" and actual["Meta"] is None:
                actual["Meta"] = t
            elif f["tipo"] == "entregado":
                actual["Entregado"] = "sí"
            elif f["tipo"] == "vuelve_con_vaso":
                actual["Entregado"] = "no (volvió con él)"
            elif f["tipo"] == "en_muelle" and actual["Meta"] is not None and actual["Vuelve"] is None:
                actual["Vuelve"] = t
    return pd.DataFrame([{
        "Viaje": i + 1, "Vaso": v["Vaso"], "Sale": v["Sale"].strftime("%H:%M:%S"),
        "Ida (s)": f'{(v["Meta"] - v["Sale"]).total_seconds():.0f}' if v["Meta"] else "en camino",
        "¿Entregado?": v["Entregado"],
        "Viaje completo (s)": f'{(v["Vuelve"] - v["Sale"]).total_seconds():.0f}' if v["Vuelve"] else "—",
    } for i, v in enumerate(viajes)])


def estado_del_carro() -> None:
    tel = telemetria() or {}
    c = tel.get("carro")
    if not c:
        st.info("En esta corrida no hay carro con física: un carro de reemplazo se lleva los vasos.")
        return
    radio = c.get("radio") or {}
    cuna = radio.get("cuna_reportada")
    st.markdown(
        '<div class="tarjetas">'
        + tarjeta("Qué hace", ESTADO_CARRO.get(c["estado"], c["estado"]), AZUL, f'tramo: {"ida" if c["fase"] == "ida" else "vuelta"}')
        + tarjeta("Carga", f'vaso {c["vaso_id"]}' if c.get("vaso_id") else "vacío", AMBAR if c.get("vaso_id") else GRIS,
                  f'inclinación del vaso: {abs(c.get("inclinacion_vaso_grados", 0)):.1f}°')
        + tarjeta("Radio (ESP-NOW)", "con enlace" if radio.get("enlace") else "sin enlace", VERDE if radio.get("enlace") else ROJO,
                  (f'{radio.get("en_espera", 0)} mensajes guardados en el carro' if radio.get("en_espera") else "sin mensajes pendientes"))
        + tarjeta("Cuna (infrarrojo 12)", "sin saber" if cuna is None else ("ocupada" if cuna else "vacía"),
                  GRIS if cuna is None else (AMBAR if cuna else VERDE),
                  "no se le carga otro vaso sin saber esto" + ("" if radio.get("enlace") else " (último dato)"))
        + (tarjeta("Odometría", f'{math.hypot(c["odometria"][0] - c["x"], c["odometria"][1] - c["y"]) * 1000:.0f} mm de error',
                   MORADO, "donde cree que está vs. donde está; vuelve a 0 en el muelle") if c.get("odometria") else "")
        + "</div>", unsafe_allow_html=True)


@st.fragment(run_every=REFRESCO_S)
def carro_en_vivo() -> None:
    """Todo lo del carro se refresca solo (antes solo el estado lo hacia y el
    mapa quedaba quieto hasta recargar la pagina)."""
    estado_del_carro()
    pestana_ruta()
    viajes = viajes_del_carro()
    if len(viajes):
        st.markdown("**Viajes del carro**", unsafe_allow_html=True)
        st.dataframe(viajes, hide_index=True, width="stretch")


def ordenes_al_carro() -> None:
    """Botones para mover el carro a mano (las mismas ordenes que puede dar
    el asistente). Van por la radio: sin enlace, no llegan."""
    with st.expander("🕹️ Mover el carro con órdenes (lo mismo que se le puede pedir al asistente)", expanded=False):
        st.markdown('<div class="nota">Antes de moverse el carro mira el camino (láser al frente y a ±15°); si ve algo '
                    "se queda quieto, y si en el camino aparece algo, se detiene. Atrás no tiene sensor: la reversa es "
                    "corta. Una orden nueva reemplaza a la anterior.</div>", unsafe_allow_html=True)
        f = st.columns(4)
        if f[0].button("⏹ Detener", width="stretch", key="c_det"):
            enviar({"cmd": "carro", "accion": "detener"}, "Carro: detener")
        if f[1].button("⤴ Retomar la línea", width="stretch", key="c_lin"):
            enviar({"cmd": "carro", "accion": "seguir_linea"}, "Carro: retomar la línea")
        if f[2].button("🏁 Ir a la meta", width="stretch", key="c_meta"):
            enviar({"cmd": "carro", "accion": "ir_meta"}, "Carro: ir a la meta")
        if f[3].button("🏠 Volver al muelle", width="stretch", key="c_mue"):
            enviar({"cmd": "carro", "accion": "volver_muelle"}, "Carro: volver al muelle")
        g = st.columns(4)
        dist = g[0].number_input("Distancia (cm)", 1, 150, 20, 5, key="c_dist")
        if g[1].button("⬆ Avanzar", width="stretch", key="c_av"):
            enviar({"cmd": "carro", "accion": "avanzar", "distancia_m": dist / 100}, f"Carro: avanzar {dist} cm")
        if g[1].button("⬇ Retroceder (máx. 30)", width="stretch", key="c_re"):
            enviar({"cmd": "carro", "accion": "retroceder", "distancia_m": min(dist, 30) / 100},
                   f"Carro: retroceder {min(dist, 30)} cm")
        grados = g[2].number_input("Giro (°)", 5, 180, 45, 5, key="c_gr")
        if g[3].button("↶ Izquierda", width="stretch", key="c_gi"):
            enviar({"cmd": "carro", "accion": "girar", "grados": grados}, f"Carro: girar {grados}° a la izquierda")
        if g[3].button("↷ Derecha", width="stretch", key="c_gd"):
            enviar({"cmd": "carro", "accion": "girar", "grados": -grados}, f"Carro: girar {grados}° a la derecha")
        h = st.columns([1, 1, 2])
        x = h[0].number_input("x (m)", -1.0, 4.0, 1.20, 0.05, key="c_x")
        y = h[1].number_input("y (m)", -3.0, 2.0, -0.30, 0.05, key="c_y")
        h[2].markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if h[2].button("📍 Ir al punto (x, y)", width="stretch", key="c_ir"):
            enviar({"cmd": "carro", "accion": "ir_a", "x": x, "y": y}, f"Carro: ir a ({x:.2f}, {y:.2f})")
        respuesta_orden()


def pestana_carro() -> None:
    ordenes_al_carro()
    carro_en_vivo()


EJEMPLOS_ASISTENTE = [
    "¿Cuánto dinero se ha aceptado y de qué monedas?",
    "¿Por qué se rechazan las piezas y qué filtro actuó más?",
    "¿Dónde está el carro y cuántos obstáculos esquivó?",
    "¿Qué sensor detecta si una moneda es de metal y en qué pin va?",
    "Avanza el carro 30 cm",
    "Gira el carro 90 grados a la derecha",
    "Lleva el carro a la meta",
    "Vuelve al muelle",
]


def _atender_frase(frase: str) -> None:
    """Pregunta al asistente y deja en la tabla `ordenes` las ordenes que
    salieron validas (el supervisor las vuelve a validar)."""
    from app import asistente

    with st.spinner("Pensando…"):
        r = asistente.atender(frase, conexion(), usar=st.session_state.get("proveedor", "auto"))
    for orden in r.ordenes:
        db.insertar_orden(conexion(), orden)
    st.session_state["asistente_ultima"] = r
    if st.session_state.get("hablar") and r.texto:
        st.session_state["asistente_audio"] = asistente.voz(r.texto)   # (audio, "mp3"|"wav") o None


def _sin_error(funcion) -> None:
    try:
        funcion()
    except Exception:  # sin faster-whisper o sin el modelo descargado: se avisa al usarlo
        pass


def pestana_asistente() -> None:
    from app import asistente

    con = conexion()
    hay_clave = asistente.cliente_deepseek() is not None
    hay_local = asistente.cliente_local() is not None
    if hay_local and not st.session_state.get("local_precargado"):
        # La primera respuesta del modelo local tarda ~1 min si no esta en la GPU.
        st.session_state["local_precargado"] = True
        asistente.precargar_local()
    estado_html = (f'<span class="chip {"corriendo" if hay_clave else ""}">DeepSeek {"✓" if hay_clave else "sin clave"}</span>'
                   f'<span class="chip {"corriendo" if hay_local else ""}">local {asistente.MODELO_LOCAL} '
                   f'{"✓" if hay_local else "apagado"}</span><span class="chip">reglas ✓</span>')
    st.markdown(f'<div class="cabecera"><h1 style="font-size:1.2rem">💬 Asistente del proyecto</h1>{estado_html}</div>'
                '<div class="nota">Pregúntele en palabras normales por las cifras de la corrida o por cualquier '
                "parte del proyecto (sensores, pines, decisiones), o pídale que mueva el carro o la línea. Responde "
                "con los datos reales de la base de datos y la documentación del proyecto; si no tiene un dato, lo "
                "dice.</div>", unsafe_allow_html=True)
    if not hay_clave and not hay_local:
        st.markdown('<div class="aviso ambar">Sin DeepSeek ni modelo local: entiende órdenes y preguntas básicas, y '
                    "para lo demás muestra la parte de la documentación más relacionada. DeepSeek: archivo "
                    "<code>.env</code> con <code>DEEPSEEK_API_KEY=sk-...</code>. Local: instalar Ollama y "
                    f"<code>ollama pull {asistente.MODELO_LOCAL}</code> (ver README).</div>", unsafe_allow_html=True)

    izq, der = st.columns([1.6, 1])
    with der:
        st.markdown("**Cómo hablarle**")
        audio = st.audio_input("🎤 Dígale algo", key="microfono",
                               help="Con internet lo oye Google (como el tema 4); sin internet, Whisper en este PC.")
        if not st.session_state.get("voz_precargada"):
            # Whisper tarda unos segundos en cargarse: se carga por detras al abrir la pestaña.
            st.session_state["voz_precargada"] = True
            import threading

            threading.Thread(target=lambda: _sin_error(asistente._whisper_modelo), daemon=True).start()
        if audio is not None:
            datos = audio.getvalue()
            if st.session_state.get("audio_procesado") != hash(datos):
                st.session_state["audio_procesado"] = hash(datos)
                with st.spinner("Escuchando…"):
                    texto, detalle = asistente.transcribir(datos)
                if texto:
                    st.session_state["frase_pendiente"] = texto
                    st.session_state["oido_por"] = detalle
                else:
                    st.warning(detalle)
        if st.session_state.get("oido_por"):
            st.caption(f"Última frase oída con: {st.session_state['oido_por']}")
        c1, c2 = st.columns(2)
        c1.toggle("🔊 Responder en voz alta", key="hablar")
        c2.selectbox("Quién responde", ["auto", "deepseek", "ollama", "reglas"], key="proveedor",
                     format_func=lambda v: {"auto": "Automático", "deepseek": "Solo DeepSeek",
                                            "ollama": "Solo el modelo local", "reglas": "Solo reglas"}[v],
                     help="Automático: DeepSeek; si no hay, el modelo local (Ollama); si tampoco, las reglas. "
                          "Las órdenes claras (avanza 20 cm, gira...) siempre las decide el intérprete de reglas "
                          "cuando no responde DeepSeek.")
        st.markdown("**Ejemplos** <span class='nota'>· clic para preguntar</span>", unsafe_allow_html=True)
        for i, ej in enumerate(EJEMPLOS_ASISTENTE):
            if st.button(ej, key=f"ej{i}", width="stretch"):
                st.session_state["frase_pendiente"] = ej
        ordenes_del_asistente()
        if st.button("🗑 Borrar la conversación", width="stretch"):
            asistente.borrar_conversacion(con)
            st.session_state.pop("asistente_ultima", None)

    with izq:
        frase = st.chat_input("Escríbale al asistente… (p. ej. «avanza 20 cm» o «¿cuánto dinero hay?»)")
        frase = frase or st.session_state.pop("frase_pendiente", None)
        if frase:
            _atender_frase(frase)
        r = st.session_state.get("asistente_ultima")
        if r is not None:
            if r.aviso:
                st.caption("⚠️ " + r.aviso)
            if r.descartadas:
                st.caption("Órdenes descartadas (fuera de lo permitido): " + "; ".join(r.descartadas))
            if r.documentos:
                with st.expander("Documentos que consultó para responder"):
                    st.markdown("\n".join(f"- {d}" for d in r.documentos))
        historial = asistente.conversacion(con, 30)
        if not historial:
            st.markdown('<div class="nota" style="margin:24px 0">Todavía no le ha preguntado nada.</div>',
                        unsafe_allow_html=True)
        # Lo mas nuevo ARRIBA, pegado a donde se escribe (usuario, 2026-09-27):
        # cada pregunta con su respuesta debajo, y los pares de mas nuevo a
        # mas viejo.
        pares, actual = [], []
        for m in historial:
            if m["rol"] == "usuario" and actual:
                pares.append(actual)
                actual = []
            actual.append(m)
        if actual:
            pares.append(actual)
        for m in [m for par in reversed(pares) for m in par]:
            with st.chat_message("user" if m["rol"] == "usuario" else "assistant",
                                 avatar="🧑" if m["rol"] == "usuario" else "🪙"):
                # "$" sin escapar se lee como formula de LaTeX ($0 ... $12.500).
                st.markdown(m["texto"].replace("$", r"\$"))
                if m["acciones"]:
                    st.caption("Órdenes enviadas: " + " · ".join(
                        NOMBRE_ORDEN_CARRO.get(o.get("accion"), o.get("accion")) if o["cmd"] == "carro"
                        else o["cmd"] for o in m["acciones"]))
                if m["rol"] == "asistente" and m.get("modo"):
                    st.caption("respondió: " + {"deepseek": "DeepSeek", "ollama": f"modelo local ({asistente.MODELO_LOCAL})"}
                               .get(m["modo"], "intérprete de reglas"))
        audio_resp = st.session_state.pop("asistente_audio", None)
        if audio_resp:
            st.audio(audio_resp[0], format=f"audio/{audio_resp[1]}", autoplay=True)


@st.fragment(run_every=REFRESCO_S)
def ordenes_del_asistente() -> None:
    """Que paso con cada orden que dio el asistente (la respuesta del
    supervisor y, para el carro, lo que hizo despues)."""
    filas = conexion().execute(
        "SELECT ts, origen, tipo, payload FROM eventos WHERE (tipo = 'respuesta' AND payload LIKE '%\"asistente\"%') "
        "OR (origen = 'carro' AND tipo IN ('orden_cumplida', 'camino_bloqueado', 'bloqueado', 'atascado', "
        "'llego_al_punto', 'punto_con_error', 'ruta_retomada', 'detenido_por_orden', 'meta', 'en_muelle')) "
        "ORDER BY id DESC LIMIT 8").fetchall()
    if filas:
        st.markdown("**Qué pasó con las órdenes**", unsafe_allow_html=True)
        st.markdown(f'<div class="frases">{html_frases([(f["ts"][11:19], *frase_evento(dict(f))) for f in filas if frase_evento(dict(f))])}</div>',
                    unsafe_allow_html=True)


def pestana_ayuda() -> None:
    st.markdown("### ❓ Cómo leer este tablero")
    st.markdown("""
**Qué hace el sistema**, en tres pasos:

1. **Clasificar.** Se pone una pieza por casilla en la **cinta de monedas**. Un infrarrojo la ve, dos sensores
   debajo de la cinta dicen si es de metal y una cámara la mide y la reconoce. Solo pasan las monedas
   colombianas: todo lo demás sale a la bandeja de rechazo.
2. **Empacar.** Cada moneda aceptada va al **almacén tipo revólver**: un tubo por denominación. Cuando un
   tubo junta un lote, suelta las monedas a un **vaso**, y cada vaso lleva una sola denominación. El vaso se
   tapa, se prensa y pasa a la **canaleta**.
3. **Entregar.** Un **carro autónomo** recibe el vaso, sigue la línea de la pista, esquiva tres obstáculos,
   lo lleva a la meta y vuelve solo al muelle.

**Las pestañas**
- **Resumen**: lo más importante de un vistazo. Muestra cuánto dinero se ha aceptado, cómo está cada parte y
  qué pasó hace un momento.
- **Monedas y vasos**: cuántas monedas hay de cada denominación, qué hay guardado en cada tubo y los vasos
  de la corrida.
- **Calidad del filtro**: qué tan bien separa la línea las monedas buenas del resto, y por qué rechazó cada
  cosa.
- **Línea en vivo**: las dos cintas en este momento y las pruebas que se le pueden hacer (sacar un vaso,
  meter una mano, cortar la radio del carro).
- **Carro y ruta**: el recorrido real del carro por la pista, su radio y sus viajes, y botones para moverlo
  con órdenes (avanzar, girar, ir a un punto, ir a la meta, volver al muelle).
- **Montaje real**: los tiempos y los errores de los sensores para construirlo de verdad.
- **Asistente**: se le pregunta por escrito o por voz por las cifras de la corrida o por cualquier parte del
  proyecto, y se le puede pedir que mueva el carro o la línea (DeepSeek; sin internet, un intérprete local).

**Palabras que aparecen**
- **Lote**: cuántas monedas lleva cada vaso.
- **Cortina de seguridad**: un sensor que detecta una mano en la zona de tapa y prensa, y detiene esa zona.
- **Rechazo por material**: no es de metal (botones, bloques).
- **Rechazo por visión**: la cámara no la reconoce o sus medidas no cuadran.
- **Radio del carro**: el carro y la estación hablan por radio (ESP-NOW). Si se corta, el carro termina la vuelta
  solo, y no se le carga otro vaso hasta saber, con su infrarrojo, que la cuna está vacía.
- **Peso estimado**: se calcula con la masa nominal de cada moneda reconocida (no hay balanza).
- **Odometría**: dónde cree el carro que está, contando las vueltas de sus ruedas. Acumula error; se vuelve a
  poner en cero cada vez que entra al muelle.

Para ver la planta en 3D, con cada sensor, cable y pin, abra **visor.bat**.
""")


# ---------------------------------------------------------------------

cabecera()
barra_control()
NOMBRES_PESTANAS = ["🏠 Resumen", "🪙 Monedas y vasos", "🎯 Calidad del filtro", "🏭 Línea en vivo", "🚗 Carro y ruta",
                    "🛠️ Montaje real", "💬 Asistente", "❓ Ayuda"]
_CLAVES_PESTANAS = {"resumen": 0, "produccion": 1, "monedas": 1, "calidad": 2, "rechazos": 2, "inspeccion": 2,
                    "linea": 3, "ruta": 4, "carro": 4, "replicacion": 5, "asistente": 6, "ayuda": 7}
_pedida = _CLAVES_PESTANAS.get(st.query_params.get("pestana", ""), 0)
tabs = st.tabs(NOMBRES_PESTANAS, default=NOMBRES_PESTANAS[_pedida])
with tabs[0]:
    pestana_resumen()
with tabs[1]:
    pestana_produccion()
with tabs[2]:
    pestana_calidad()
with tabs[3]:
    pestana_linea()
with tabs[4]:
    pestana_carro()
with tabs[5]:
    pestana_replicacion()
with tabs[6]:
    pestana_asistente()
with tabs[7]:
    pestana_ayuda()
