"""Pestaña Línea en vivo: las dos cintas en este momento (cada pieza avanzando
estación por estación), el almacén tipo revólver, los LEDs de los sensores y
la bitácora detallada. Solo mira: lo que se le HACE a la línea está en la
pestaña Pruebas."""

from __future__ import annotations

import streamlit as st

from .. import datos, dibujos
from ..estilo import aviso, html_leds, nota, pintar, seccion
from ..textos import describir_evento


@st.fragment(run_every=datos.REFRESCO_S)
def pestana() -> None:
    tel = datos.telemetria()
    if not tel or not tel.get("casillas_monedas"):
        st.info("La línea todavía no arrancó. Use **Empezar una corrida nueva** en la barra de la izquierda.")
        return
    if tel.get("cortina_activa"):
        aviso("🖐 <b>Mano en la zona de tapa y prensa</b>: la prensa subió y se detuvo; la cinta de vasos no avanza. "
              "La cinta de monedas sigue.", "rojo")
    s = tel["sensores"]
    izq, der = st.columns([2.3, 1], gap="large")
    with izq:
        seccion("Cinta de monedas", f"quedan {tel['pendientes']} piezas por cargar · una pieza por casilla",
                primera=True)
        pintar(dibujos.cinta_monedas(tel))
        pintar(html_leds([("infrarrojo de presencia (1)", s["presencia"], False),
                          ("capacitivo, bajo la cinta (2)", s["capacitivo"], False),
                          ("inductivo, bajo la cinta (3)", s["inductivo"], False)]))

        seccion("Almacén tipo revólver", "cada moneda aceptada va al tubo de su denominación; con "
                f"{tel['monedas_por_vaso']} se suelta el lote a un vaso")
        pintar(dibujos.almacen(tel))

        seccion("Cinta de vasos", f"tapas en el tubo: {tel['tapas_restantes']} · prensadas: {tel['ciclos_prensa']}")
        pintar(dibujos.cinta_vasos(tel))
        pintar(html_leds([("cortina de seguridad (8)", s["cortina"], True),
                          ("sensor del interior del vaso (5)", s.get("sensor_interior", False), False),
                          ("Hall del carrusel (6)", s.get("hall_carrusel", False), False)]))
        nota("¿Quiere ver si la línea se da cuenta sola? En la pestaña <b>Pruebas</b> se le puede sacar un vaso, "
             "meter una mano, cortar la radio del carro o probar un filtro.")
    with der:
        seccion("Bitácora detallada", "los últimos 16 eventos", primera=True)
        lineas = "<br>".join(describir_evento(e) for e in datos.eventos_recientes(16))
        pintar(f'<div class="bitacora">{lineas}</div>')
