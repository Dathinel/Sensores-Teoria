"""Pestaña Carro y ruta (punto 14): estado del carro, el mapa de la pista con
su recorrido real (tabla `ruta`), los muros y los eventos de evasión, sus
viajes, y al lado del mapa el panel para moverlo con órdenes (las mismas que
se le pueden pedir al asistente; van por la radio: sin enlace no llegan)."""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from .. import datos
from ..cabecera import respuesta_orden
from ..estilo import (AMBAR, AZUL, GRIS, MORADO, ROJO, VERDE, figura, html_leyenda, html_tarjeta, kpis,
                      mostrar, nota, pintar, seccion, subgrupo, tabla, tarjetas)
from ..textos import ESTADO_CARRO, NOMBRE_EVENTO_RUTA


def pestana() -> None:
    estado_del_carro()
    # 3:2 (antes 2:1): con 2:1 el panel de órdenes cortaba el texto de sus botones.
    izq, der = st.columns([3, 2], gap="large")
    with izq:
        mapa()
    with der:
        ordenes_al_carro()
    historial()


@st.fragment(run_every=datos.REFRESCO_S)
def estado_del_carro() -> None:
    tel = datos.telemetria() or {}
    c = tel.get("carro")
    ruta = datos.ruta_del_carro()
    traza = ruta[ruta["ev"].isna()]
    hitos = ruta[ruta["ev"].notna()]
    distancia = float(((traza["x"].diff() ** 2 + traza["y"].diff() ** 2) ** 0.5).sum()) if len(traza) > 1 else 0.0
    kpis([
        ("Vasos entregados en la meta", str(datos.vasos_entregados_por_el_carro()), "el carro los llevó y se los sacaron",
         VERDE),
        ("Obstáculos esquivados", str(int((hitos["ev"] == "evasion").sum())), "tres muros en la pista, en cada viaje",
         MORADO),
        ("Distancia recorrida", f"{distancia:.1f} m", "según la simulación con física", AZUL),
    ])
    if not c:
        st.info("En esta corrida no hay carro con física: un carro de reemplazo se lleva los vasos.")
        return
    radio = c.get("radio") or {}
    cuna = radio.get("cuna_reportada")
    tarjetas([
        html_tarjeta("Qué hace", ESTADO_CARRO.get(c["estado"], c["estado"]), AZUL,
                     f'tramo: {"ida" if c["fase"] == "ida" else "vuelta"}'),
        html_tarjeta("Carga", f'vaso {c["vaso_id"]}' if c.get("vaso_id") else "vacío",
                     AMBAR if c.get("vaso_id") else GRIS,
                     f'inclinación del vaso: {abs(c.get("inclinacion_vaso_grados", 0)):.1f}°'),
        html_tarjeta("Radio (ESP-NOW)", "con enlace" if radio.get("enlace") else "sin enlace",
                     VERDE if radio.get("enlace") else ROJO,
                     f'{radio.get("en_espera", 0)} mensajes guardados en el carro' if radio.get("en_espera")
                     else "sin mensajes pendientes"),
        html_tarjeta("Cuna (infrarrojo 12)", "sin saber" if cuna is None else ("ocupada" if cuna else "vacía"),
                     GRIS if cuna is None else (AMBAR if cuna else VERDE),
                     "no se le carga otro vaso sin saber esto" + ("" if radio.get("enlace") else " (último dato)")),
        html_tarjeta("Odometría",
                     f'{math.hypot(c["odometria"][0] - c["x"], c["odometria"][1] - c["y"]) * 1000:.0f} mm de error',
                     MORADO, "donde cree que está vs. donde está; vuelve a 0 en el muelle") if c.get("odometria") else "",
    ])


@st.fragment(run_every=datos.REFRESCO_S)
def mapa() -> None:
    """El mapa se refresca solo (antes quedaba quieto hasta recargar la página)."""
    seccion("Mapa de la pista", "vista desde arriba; x e y en metros", primera=True)
    pista = datos.geometria_pista()
    if pista is None:
        st.info("No hay geometría de la pista: arranque el supervisor.")
        return
    tel = datos.telemetria() or {}
    carro = tel.get("carro")
    ruta = datos.ruta_del_carro()
    traza = ruta[ruta["ev"].isna()]
    hitos = ruta[ruta["ev"].notna()]

    fig = figura(600)
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
                            textfont=dict(color=color), marker=dict(color=color, size=11, symbol="square"),
                            hoverinfo="skip")
    sal = pista["salida"]
    fig.add_scatter(x=[sal["x"]], y=[sal["y"]], mode="markers+text", text=["muelle"], textposition="middle left",
                    textfont=dict(color=AMBAR), marker=dict(color=AMBAR, size=12, symbol="diamond"), hoverinfo="skip")
    if len(traza):
        fig.add_scatter(x=traza["x"], y=traza["y"], mode="lines", line=dict(color=AMBAR, width=2), hoverinfo="skip")
    for ev, color, simbolo in (("obstaculo", ROJO, "x"), ("evasion", MORADO, "triangle-up"),
                               ("linea_recuperada", VERDE, "circle"), ("error", ROJO, "octagon"),
                               ("orden", AMBAR, "star"), ("camino_bloqueado", ROJO, "square-x"),
                               ("bloqueado", ROJO, "square-x"), ("atascado", ROJO, "hexagon")):
        h = hitos[hitos["ev"] == ev]
        if len(h):
            fig.add_scatter(x=h["x"], y=h["y"], mode="markers", marker=dict(color=color, size=9, symbol=simbolo),
                            hovertext=[f"{NOMBRE_EVENTO_RUTA.get(ev, ev)} ({e})" for e in h["estado"]],
                            hoverinfo="text")
    if carro and carro.get("odometria"):
        # Dónde CREE el carro que está (encoders): la distancia a la flecha azul es el error que
        # acumula la odometría (vuelve a 0 en el muelle).
        ox, oy, _ = carro["odometria"]
        fig.add_scatter(x=[ox], y=[oy], mode="markers",
                        marker=dict(color="rgba(0,0,0,0)", size=15, symbol="circle", line=dict(color=AZUL, width=2)),
                        hovertext=f"donde cree que está (odometría): error "
                                  f"{math.hypot(ox - carro['x'], oy - carro['y']) * 1000:.0f} mm", hoverinfo="text")
    if carro:
        fig.add_scatter(x=[carro["x"]], y=[carro["y"]], mode="markers",
                        marker=dict(color=AZUL, size=16, symbol="triangle-up", angle=90 - math.degrees(carro["rumbo"]),
                                    line=dict(color="#ffffff", width=1)),
                        hovertext=f"carro: {carro['fase']} · {carro['estado']}", hoverinfo="text")
    # Un poco de aire alrededor: las etiquetas del muelle y de la marca de giro van a la izquierda.
    xs = lx + [sal["x"]]
    fig.update_xaxes(range=[min(xs) - 0.35, max(xs) + 0.15])
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    mostrar(fig)
    pintar(html_leyenda([
        ("━", AMBAR, "recorrido real del carro (simulación con física)"),
        ("✕", ROJO, "obstáculo visto (3 lecturas seguidas del ultrasónico)"),
        ("▲", MORADO, "empieza a esquivar"),
        ("●", VERDE, "vuelve a la línea"),
        ("★", AMBAR, "orden recibida"),
        ("○", AZUL, "donde cree el carro que está (odometría)"),
        ("▲", AZUL, "el carro ahora"),
    ]))


def ordenes_al_carro() -> None:
    """Botones para mover el carro a mano (las mismas órdenes que puede dar el asistente)."""
    with st.container(border=True, key="panel_ordenes"):
        seccion("Mover el carro", "lo mismo que se le puede pedir al asistente", primera=True)
        nota("Antes de moverse el carro mira el camino (láser al frente y a ±15°); si ve algo se queda quieto, y si "
             "en el camino aparece algo, se detiene. Atrás no tiene sensor: la reversa es corta. Una orden nueva "
             "reemplaza a la anterior.")
        subgrupo("Recorridos")
        f = st.columns(2)
        if f[0].button("Detener", icon=":material/stop:", width="stretch", key="c_det"):
            datos.enviar({"cmd": "carro", "accion": "detener"}, "Carro: detener")
        if f[1].button("Retomar la línea", icon=":material/route:", width="stretch", key="c_lin"):
            datos.enviar({"cmd": "carro", "accion": "seguir_linea"}, "Carro: retomar la línea")
        if f[0].button("Ir a la meta", icon=":material/flag:", width="stretch", key="c_meta"):
            datos.enviar({"cmd": "carro", "accion": "ir_meta"}, "Carro: ir a la meta")
        if f[1].button("Volver al muelle", icon=":material/home:", width="stretch", key="c_mue"):
            datos.enviar({"cmd": "carro", "accion": "volver_muelle"}, "Carro: volver al muelle")

        subgrupo("Avanzar o retroceder")
        dist = st.number_input("Distancia (cm)", 1, 150, 20, 5, key="c_dist",
                               help="Avanzar: hasta 150 cm. Retroceder: máximo 30 cm (atrás no hay sensor).")
        g = st.columns(2)
        if g[0].button("Avanzar", icon=":material/arrow_upward:", width="stretch", key="c_av"):
            datos.enviar({"cmd": "carro", "accion": "avanzar", "distancia_m": dist / 100}, f"Carro: avanzar {dist} cm")
        if g[1].button("Retroceder (máx. 30)", icon=":material/arrow_downward:", width="stretch", key="c_re"):
            datos.enviar({"cmd": "carro", "accion": "retroceder", "distancia_m": min(dist, 30) / 100},
                         f"Carro: retroceder {min(dist, 30)} cm")

        subgrupo("Girar en su sitio")
        grados = st.number_input("Giro (°)", 5, 180, 45, 5, key="c_gr")
        g = st.columns(2)
        if g[0].button("Izquierda", icon=":material/rotate_left:", width="stretch", key="c_gi"):
            datos.enviar({"cmd": "carro", "accion": "girar", "grados": grados}, f"Carro: girar {grados}° a la izquierda")
        if g[1].button("Derecha", icon=":material/rotate_right:", width="stretch", key="c_gd"):
            datos.enviar({"cmd": "carro", "accion": "girar", "grados": -grados}, f"Carro: girar {grados}° a la derecha")

        subgrupo("Ir a un punto del mapa", "x e y como en el mapa")
        h = st.columns(2)
        x = h[0].number_input("x (m)", -1.0, 4.0, 1.20, 0.05, key="c_x")
        y = h[1].number_input("y (m)", -3.0, 2.0, -0.30, 0.05, key="c_y")
        if st.button("Ir al punto (x, y)", icon=":material/location_on:", width="stretch", key="c_ir"):
            datos.enviar({"cmd": "carro", "accion": "ir_a", "x": x, "y": y}, f"Carro: ir a ({x:.2f}, {y:.2f})")
        respuesta_orden()


@st.fragment(run_every=datos.REFRESCO_S)
def historial() -> None:
    ruta = datos.ruta_del_carro()
    hitos = ruta[ruta["ev"].notna()]
    viajes = datos.viajes_del_carro()
    if not len(hitos) and not len(viajes):
        return
    a, b = st.columns(2, gap="large")
    with a:
        if len(viajes):
            seccion("Viajes del carro", f"{len(viajes)} viajes")
            tabla(viajes)
    with b:
        if len(hitos):
            seccion("Eventos del recorrido", "lo más nuevo arriba")
            tabla(pd.DataFrame({"evento": [NOMBRE_EVENTO_RUTA.get(e, e) for e in hitos["ev"]],
                                "tramo": hitos["estado"], "x (m)": hitos["x"].round(3),
                                "y (m)": hitos["y"].round(3)}).iloc[::-1], height=260)
