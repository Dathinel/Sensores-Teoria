"""Pestaña Resumen: lo más importante de un vistazo (cifras, estado de cada
parte, el recorrido de las piezas y qué acaba de pasar)."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from control import reglas

from .. import datos
from ..datos import pesos
from ..estilo import (AMBAR, AZUL, GRIS, MORADO, ROJO, TEXTO, VERDE, aviso, figura, figura_vacia, html_frases,
                      html_tarjeta, kpis, mostrar, pintar, seccion, tarjetas)
from ..textos import ESTADO_CARRO, ESTADO_LINEA_TXT


@st.fragment(run_every=datos.REFRESCO_S)
def pestana() -> None:
    tel = datos.telemetria()
    if not tel:
        st.info("Cuando la línea arranque, aquí se ve todo lo importante de un vistazo.")
        return
    d = datos.datos_corrida()
    aceptadas, rechazadas = d["aceptadas"], d["rechazadas"]
    entregados = [v for v in tel.get("vasos_salida") or [] if v["destino"] == "entrega"]
    kpis([
        ("Valor aceptado", pesos(aceptadas["valor"].sum()),
         "suma de las monedas colombianas aceptadas en esta corrida", AMBAR),
        ("Monedas aceptadas", str(len(aceptadas)), "pasaron todos los filtros", VERDE),
        ("Piezas rechazadas", str(len(rechazadas)),
         "botones, bloques, monedas extranjeras y todo lo que no pasó los filtros", ROJO),
        ("Vasos entregados", str(len(entregados)), "vasos tapados que el carro llevó a la meta", AZUL),
        ("Peso estimado", f'{aceptadas["masa_estimada_g"].sum():.0f} g',
         "masa nominal de cada moneda reconocida (no hay balanza)", MORADO),
    ])

    # Estado de cada parte, en una línea.
    c = tel.get("carro") or {}
    radio = c.get("radio") or {}
    corre = tel["linea"] == "corriendo"
    tarjetas([
        html_tarjeta("Cinta de monedas", "trabajando" if corre else ESTADO_LINEA_TXT.get(tel["linea"], tel["linea"]).lower(),
                     VERDE if corre else GRIS,
                     f'{tel.get("pendientes", 0)} piezas por cargar'
                     + (" · una moneda espera en la descarga" if tel.get("moneda_en_espera") else "")),
        html_tarjeta("Almacén", pesos(tel.get("almacen_valor", 0)) + " guardado", AMBAR,
                     f'lotes de {tel.get("monedas_por_vaso")} monedas por vaso'),
        html_tarjeta("Cinta de vasos", "detenida por la cortina" if tel.get("cortina_activa") else "normal",
                     ROJO if tel.get("cortina_activa") else VERDE,
                     f'{tel.get("tapas_restantes", 0)} tapas en el tubo · {len(tel.get("canaleta") or [])} vasos '
                     "esperando al carro"),
        html_tarjeta("Carro", ESTADO_CARRO.get(c.get("estado"), "—") if c else "reemplazo simulado",
                     AZUL if c else GRIS,
                     (("📡 con radio" if radio.get("enlace") else f"📡 <b style='color:{ROJO}'>sin radio</b>")
                      + (f' · lleva el vaso {c["vaso_id"]}' if c.get("vaso_id") else "")) if c else "sin carro con física"),
    ])
    alarmas = tel.get("alarmas") or []
    if alarmas:
        aviso("⚠️ " + " · ".join(str(a).replace("_", " ") for a in alarmas), "rojo")

    izq, der = st.columns([1.35, 1], gap="large")
    with izq:
        seccion("Recorrido de las piezas", "de lo que se cargó en la cinta, qué pasó con cada cosa (el grosor es la cantidad)")
        mostrar(figura_recorrido(d, tel))
    with der:
        seccion("Qué está pasando", "lo último, en palabras simples")
        pintar(html_frases(datos.frases_recientes(11)))


def figura_recorrido(d: dict, tel: dict) -> go.Figure:
    """Diagrama de flujo (Sankey): cargadas → aceptadas / rechazadas por etapa → tubos / vasos → entregadas."""
    aceptadas, rechazadas = d["aceptadas"], d["rechazadas"]
    n_mat = int((rechazadas["causa"] == reglas.CAUSA_NO_METALICO).sum())
    n_vis = len(rechazadas) - n_mat
    entregadas = int(sum(v["cantidad"] for v in tel.get("vasos_salida") or [] if v["destino"] == "entrega"))
    en_vasos = entregadas + int(sum((v or {}).get("cantidad", 0) for v in tel.get("casillas_vasos") or [] if v))
    # Lo de esta corrida que no está en vasos sigue en los tubos (los tubos pueden traer,
    # además, monedas del turno anterior).
    en_vasos = min(en_vasos, len(aceptadas))
    guardadas = len(aceptadas) - en_vasos
    # (nombre, color, columna x, altura y). Columnas fijas y lógicas: los rechazos salen de la
    # cinta al mismo tiempo que las aceptadas (columna 2), no al final; con el acomodo automático
    # Plotly los mandaba a la derecha y las etiquetas "En vasos" y "Entregadas" se encimaban.
    nodos = [("Cargadas", GRIS, 0.001, 0.5), ("Rechazo por material", AZUL, 0.27, 0.05),
             ("Rechazo por visión", MORADO, 0.27, 0.2), ("Aceptadas", VERDE, 0.27, 0.66),
             ("Guardadas en los tubos", AMBAR, 0.54, 0.42), ("En vasos", AMBAR, 0.54, 0.8),
             ("Entregadas", VERDE, 0.999, 0.8)]
    # En orden de arriba abajo, para que los enlaces no se crucen.
    enlaces = [(0, 1, n_mat), (0, 2, n_vis), (0, 3, len(aceptadas)), (3, 4, guardadas), (3, 5, en_vasos),
               (5, 6, min(entregadas, en_vasos))]
    enlaces = [e for e in enlaces if e[2] > 0]
    if not enlaces:
        return figura_vacia(330, "todavía no hay piezas procesadas")
    # Solo los nodos que tienen piezas (un nodo vacío deja una etiqueta suelta).
    usados = sorted({i for e in enlaces for i in e[:2]})
    nuevo_indice = {viejo: n for n, viejo in enumerate(usados)}
    cantidad = {i: sum(e[2] for e in enlaces if e[1] == i) for i in usados}
    cantidad[0] = sum(e[2] for e in enlaces if e[0] == 0)
    fig = figura(330)
    fig.add_trace(go.Sankey(
        arrangement="fixed",
        node=dict(label=[f"{nodos[i][0]} · {cantidad[i]}" for i in usados], color=[nodos[i][1] for i in usados],
                  x=[nodos[i][2] for i in usados], y=[nodos[i][3] for i in usados],
                  pad=14, thickness=14, line=dict(width=0), hovertemplate="%{label} piezas<extra></extra>"),
        link=dict(source=[nuevo_indice[e[0]] for e in enlaces], target=[nuevo_indice[e[1]] for e in enlaces],
                  value=[e[2] for e in enlaces], color=[_rgba(nodos[e[1]][1], 0.25) for e in enlaces],
                  hovertemplate="%{value} piezas<extra></extra>"),
        textfont=dict(color=TEXTO, size=13)))
    return fig


def _rgba(hex_color: str, alfa: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alfa})"
