"""Barra lateral: SOLO manejar la línea (empezar, pausa, seguir, paro, velocidad,
monedas por vaso y ajustes avanzados). Las pruebas que se le hacen a la planta
(probar un filtro, colocar una pieza, sabotajes, fin de turno) están juntas en
la pestaña 🧪 Pruebas, y las órdenes al carro al lado del mapa.

Cada botón deja una orden en la tabla `ordenes`; el supervisor la toma y
contesta (la respuesta aparece debajo de los botones)."""

from __future__ import annotations

import streamlit as st

from . import datos
from .cabecera import respuesta_orden
from .estilo import nota, pintar, seccion


def barra_lateral() -> None:
    tel = datos.telemetria() or {}
    planta = datos.PARAMETROS["planta"]
    corre = tel.get("linea") == "corriendo"
    pausada = tel.get("linea") == "pausada"
    with st.sidebar:
        pintar('<div class="lado-marca"><span class="moneda"></span><div><b>Controles de la línea</b>'
               "<span>lo que se le ordena a la planta</span></div></div>")

        seccion("Corrida", primera=True)
        if st.button("Empezar una corrida nueva", icon=":material/play_arrow:", width="stretch", type="primary",
                     key="iniciar",
                     help="Arranca una prueba completa: monedas colombianas y un caso de cada pieza que se debe rechazar."):
            datos.enviar({"cmd": "iniciar", "escenario": "prueba_completa",
                          "confianza_minima": st.session_state.get("confianza", tel.get("confianza_minima", 0.85)),
                          "probabilidad_error": st.session_state.get("ruido", tel.get("probabilidad_error", 0.0)),
                          "conservar_almacen": st.session_state.get("conservar", False)}, "Empezando una corrida nueva")
        c1, c2 = st.columns(2)
        if c1.button("Pausa", icon=":material/pause:", width="stretch", disabled=not corre, key="pausar"):
            datos.enviar({"cmd": "pausar"}, "Pausa")
        if c2.button("Seguir", icon=":material/resume:", width="stretch", disabled=not pausada, key="reanudar"):
            datos.enviar({"cmd": "reanudar"}, "La línea sigue")
        if st.button("PARO DE EMERGENCIA", icon=":material/emergency_home:", width="stretch",
                     disabled=not (corre or pausada), key="paro",
                     help="Detiene todo donde está. Para salir: empezar una corrida nueva."):
            datos.enviar({"cmd": "paro"}, "Paro de emergencia")
        respuesta_orden()

        seccion("Cómo trabaja")
        velocidad_actual = float(tel.get("velocidad", 1.0))
        velocidad = st.select_slider(
            "Velocidad de la simulación", options=[0.25, 0.5, 1.0, 2.0, 4.0], value=velocidad_actual,
            format_func=lambda v: f"×{v:g}" + (" (tiempo real)" if v == 1 else ""),
            help="×1 es el ritmo real del montaje; más rápido sirve para ver una corrida completa en menos tiempo.")
        if velocidad != velocidad_actual and st.session_state.get("vel_enviada") != velocidad:
            st.session_state["vel_enviada"] = velocidad
            datos.enviar({"cmd": "velocidad", "valor": velocidad}, f"Velocidad ×{velocidad:g}")
        lote_actual = int(tel.get("monedas_por_vaso") or planta["monedas_por_vaso"])
        capacidad = int(tel.get("capacidad_tubo") or planta["capacidad_tubo"])
        lote = st.number_input("Monedas por vaso", 1, capacidad, min(lote_actual, capacidad), 1,
                               help="Cuando un tubo del almacén junta este número de monedas, las suelta a un vaso.")
        if lote != lote_actual and st.session_state.get("lote_enviado") != lote:
            st.session_state["lote_enviado"] = lote
            datos.enviar({"cmd": "lote", "valor": int(lote)}, f"{lote} monedas por vaso")

        with st.expander("Ajustes avanzados (se aplican al empezar)", icon=":material/tune:"):
            st.slider("Confianza mínima del reconocimiento", 0.50, 0.99, float(tel.get("confianza_minima", 0.85)), 0.01,
                      key="confianza",
                      help="Si el reconocimiento de la moneda está menos seguro que esto, la pieza se rechaza "
                           "como 'no reconocida'.")
            st.slider("Errores forzados del reconocimiento", 0.0, 0.5, float(tel.get("probabilidad_error", 0.0)), 0.05,
                      key="ruido",
                      help="Para probar: probabilidad de que el reconocimiento se equivoque con una moneda buena.")
            st.checkbox("Empezar con lo que quedó guardado en los tubos",
                        value=bool(planta.get("conservar_almacen_entre_turnos", False)), key="conservar",
                        help="Si el turno anterior no empacó lo guardado, el nuevo arranca con esas monedas.")
            st.caption("Hoy corre en simulación. El hardware real (dos ESP32, fase 8) ya está hecho en software: "
                       "`hardware.backend: real` en config/parametros.yaml; falta probarlo en las placas.")
        nota("Los botones dejan una orden que el programa de la línea toma en menos de medio segundo; la "
             "respuesta aparece debajo de los botones, en verde o en ámbar. Las pruebas (probar un filtro, "
             "colocar una pieza, sabotajes) están en la pestaña <b>Pruebas</b>.")
