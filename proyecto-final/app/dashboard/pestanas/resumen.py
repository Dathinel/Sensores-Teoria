"""Pestaña Resumen: lo más importante de un vistazo (cifras, estado de cada
parte, el recorrido de las piezas y qué acaba de pasar)."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from control import reglas

from .. import datos
from ..datos import pesos
from ..estilo import (AMBAR, AZUL, GRIS, MORADO, ROJO, TEXTO, VERDE, aviso, figura, figura_vacia, html_frases,
                      html_tarjeta, kpis, mostrar, nota, pintar, seccion, tarjetas)
from ..textos import ESTADO_CARRO, ESTADO_LINEA_TXT, MOTIVO_PARADA_TXT


@st.fragment(run_every=datos.REFRESCO_S)
def pestana() -> None:
    tel = datos.telemetria()
    if not tel:
        st.info("Cuando la línea arranque, aquí se ve todo lo importante de un vistazo.")
        return
    d = datos.datos_corrida()
    aceptadas, rechazadas = d["aceptadas"], d["rechazadas"]
    entregados = [v for v in tel.get("vasos_salida") or [] if v["destino"] == "entrega"]
    # Las mismas cuentas que usan el diagrama y la pestaña Monedas y vasos (datos.cuentas_de_monedas):
    # cada cifra dice si es de ESTA corrida o si viene guardada del turno anterior.
    cuentas = datos.cuentas_de_monedas(d, tel)
    kpis([
        ("Valor aceptado", pesos(aceptadas["valor"].sum()),
         "monedas que pasaron los filtros en esta corrida"
         + (f' · aparte, {pesos(cuentas["valor_anteriores"])} venían del turno anterior' if cuentas["anteriores"] else ""),
         AMBAR),
        ("Monedas aceptadas", str(len(aceptadas)), "pasaron todos los filtros en esta corrida", VERDE),
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
                     f'{cuentas["en_tubos"]} monedas en los tubos ahora (de esta corrida y del turno anterior) · '
                     f'lotes de {tel.get("monedas_por_vaso")} por vaso'),
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
        texto = " · ".join(str(a).replace("_", " ") for a in alarmas)
        if tel.get("motivo_parada"):
            # Montaje real: por qué está parada la placa y cómo se sale (revisión 2026-09-29).
            texto += " — " + MOTIVO_PARADA_TXT.get(tel["motivo_parada"], str(tel["motivo_parada"]))
        aviso("⚠️ " + texto, "rojo")

    izq, der = st.columns([1.35, 1], gap="large")
    with izq:
        seccion("Recorrido de las piezas", "de lo que se cargó en la cinta, qué pasó con cada cosa (el grosor es la cantidad)")
        mostrar(figura_recorrido(d, cuentas))
        nota(datos.explicar_cuentas(cuentas))
    with der:
        seccion("Qué está pasando", "lo último, en palabras simples")
        pintar(html_frases(datos.frases_recientes(11)))


def figura_recorrido(d: dict, c: dict) -> go.Figure:
    """Diagrama de flujo (Sankey): cargadas → rechazadas por etapa / aceptadas → tubos / vasos →
    entregadas. Las monedas que venían guardadas del turno anterior entran como una SEGUNDA fuente
    ("Del turno anterior"): así "En vasos" es el total real de monedas en los vasos (cuadra con la
    tabla de vasos y con el visor) y se ve cuántas de ellas son de esta corrida. `c` son las cuentas
    de `datos.cuentas_de_monedas`."""
    rechazadas = d["rechazadas"]
    n_mat = int((rechazadas["causa"] == reglas.CAUSA_NO_METALICO).sum())
    n_vis = len(rechazadas) - n_mat
    vasos_ant = c["en_vasos_anteriores"]
    vasos_hoy = max(c["en_vasos"] - vasos_ant, 0)
    # Lo de esta corrida que no está en vasos sigue en los tubos (o va camino a ellos por la cinta).
    tubos_hoy = max(c["aceptadas"] - vasos_hoy, 0)
    tubos_ant = max(c["anteriores"] - vasos_ant, 0)
    # (nombre, color, columna x, altura y). Columnas fijas y lógicas: los rechazos salen de la
    # cinta al mismo tiempo que las aceptadas (columna 2), no al final; con el acomodo automático
    # Plotly los mandaba a la derecha y las etiquetas "En vasos" y "Entregadas" se encimaban.
    nodos = [("Cargadas", GRIS, 0.001, 0.4), ("Rechazo por material", AZUL, 0.3, 0.04),
             ("Rechazo por visión", MORADO, 0.3, 0.17), ("Aceptadas (esta corrida)", VERDE, 0.3, 0.5),
             ("Del turno anterior", GRIS, 0.3, 0.93), ("En los tubos ahora", AMBAR, 0.6, 0.3),
             ("En vasos", AMBAR, 0.6, 0.78), ("Entregadas", VERDE, 0.999, 0.78)]
    # En orden de arriba abajo, para que los enlaces no se crucen.
    enlaces = [(0, 1, n_mat), (0, 2, n_vis), (0, 3, c["aceptadas"]), (3, 5, tubos_hoy), (3, 6, vasos_hoy),
               (4, 5, tubos_ant), (4, 6, vasos_ant), (6, 7, min(c["entregadas"], c["en_vasos"]))]
    enlaces = [e for e in enlaces if e[2] > 0]
    if not enlaces:
        return figura_vacia(330, "todavía no hay piezas procesadas")
    # Solo los nodos que tienen piezas (un nodo vacío deja una etiqueta suelta).
    usados = sorted({i for e in enlaces for i in e[:2]})
    nuevo_indice = {viejo: n for n, viejo in enumerate(usados)}
    # Cantidad de cada nodo: lo que le entra, o lo que sale si es una fuente (Cargadas, Del turno anterior).
    cantidad = {i: sum(e[2] for e in enlaces if e[1] == i) or sum(e[2] for e in enlaces if e[0] == i)
                for i in usados}
    # Las etiquetas de la columna del medio van en DOS renglones: a 900 px con la barra lateral abierta
    # "Aceptadas (esta corrida) · 23" en uno solo llegaba hasta el nodo "En los tubos ahora" y quedaba
    # pegado a él, y "En vasos · 10" chocaba con "Entregadas · 10" (revisión visual 2026-09-29; por eso también
    # la tercera columna pasó de x=0,64 a 0,6). El tooltip usa el nombre en un renglón (customdata).
    partidas = {"Aceptadas (esta corrida)": "Aceptadas<br>(esta corrida)", "Del turno anterior": "Del turno<br>anterior",
                "Rechazo por material": "Rechazo por<br>material", "Rechazo por visión": "Rechazo por<br>visión",
                "En vasos": "En<br>vasos"}
    fig = figura(380)
    fig.update_layout(margin=dict(l=10, r=10, t=14, b=14))
    fig.add_trace(go.Sankey(
        arrangement="fixed",
        node=dict(label=[f"{partidas.get(nodos[i][0], nodos[i][0])} · {cantidad[i]}" for i in usados],
                  customdata=[f"{nodos[i][0]} · {cantidad[i]}" for i in usados], color=[nodos[i][1] for i in usados],
                  x=[nodos[i][2] for i in usados], y=[nodos[i][3] for i in usados],
                  pad=14, thickness=14, line=dict(width=0), hovertemplate="%{customdata} piezas<extra></extra>"),
        link=dict(source=[nuevo_indice[e[0]] for e in enlaces], target=[nuevo_indice[e[1]] for e in enlaces],
                  value=[e[2] for e in enlaces], color=[_rgba(nodos[e[1]][1], 0.25) for e in enlaces],
                  hovertemplate="%{value} piezas<extra></extra>"),
        textfont=dict(color=TEXTO, size=13)))
    return fig


def _rgba(hex_color: str, alfa: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alfa})"
