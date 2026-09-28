"""Pestaña 🧪 Pruebas: TODO lo que se le hace a la planta para ver si se da
cuenta sola, en un solo lugar y en el mismo orden que el visor 3D:

    1 Probar un filtro   (una corrida con piezas que SOLO ese filtro debe rechazar)
    2 Colocar una pieza  (como si el operador la pusiera a mano en la carga)
    3 Sabotajes          (vasos, manos y la radio del carro)
    4 Fin de turno       (empacar lo guardado en los tubos)

A la derecha, lo que contestó la línea y lo que pasó después, para ver el
efecto sin cambiar de pestaña. Antes estos controles estaban repartidos entre
la barra lateral y la pestaña Línea en vivo (docs/interfaz-dashboard.md).
"""

from __future__ import annotations

import streamlit as st

from .. import datos
from ..cabecera import mostrar_respuesta
from ..estilo import html_frases, nota, pintar, seccion, subgrupo


def boton_orden(etiqueta: str, orden: dict, aviso: str, activa: bool, ayuda: str, clave: str, icono: str | None = None) -> None:
    if st.button(etiqueta, width="stretch", disabled=not activa, help=ayuda, key=clave, icon=icono):
        datos.enviar(orden, aviso)


@st.fragment(run_every=datos.REFRESCO_S)
def pestana() -> None:
    from sim.carga_escenarios import PIEZAS, PRUEBAS_DE_UN_FILTRO

    tel = datos.telemetria() or {}
    linea = tel.get("linea")
    activa = linea in ("corriendo", "pausada")
    izq, der = st.columns([2.3, 1], gap="large")
    with izq:
        nota("Cada prueba deja una orden para la línea. La idea es que la planta se dé cuenta <b>sola</b>, con sus "
             "sensores, y reaccione sin parar toda la producción.")
        a, b = st.columns(2, gap="medium")
        # 1. Usuario, 2026-09-27: los filtros se prueban UNO POR UNO en la sustentación. Cada prueba es
        # un escenario de un solo filtro (los mismos de las pruebas automáticas).
        with a.container(border=True, key="panel_filtro", height="stretch"):
            seccion("Probar un filtro", "empieza una corrida nueva", numero=1, primera=True)
            prueba = st.selectbox("Filtro", PRUEBAS_DE_UN_FILTRO, key="prueba_filtro", label_visibility="collapsed",
                                  format_func=lambda p: f"{p['estacion']} · {p['nombre']}")
            nota(prueba["espera"])
            if st.button("Probar solo este filtro", icon=":material/science:", width="stretch", type="primary",
                         key="probar_filtro",
                         help="Empieza una corrida nueva con piezas que SOLO este filtro debe rechazar."):
                datos.enviar({"cmd": "iniciar", "escenario": prueba["escenario"]},
                             f"Prueba de un filtro: {prueba['nombre']}")
        # 2. "Colocar pieza X".
        with b.container(border=True, key="panel_pieza", height="stretch"):
            seccion("Colocar una pieza", "entra en la próxima carga", numero=2, primera=True)
            pieza = st.selectbox("Pieza", list(PIEZAS), format_func=lambda k: PIEZAS[k]["nombre"], key="pieza",
                                 label_visibility="collapsed")
            nota("Como si el operador la pusiera a mano en la casilla de carga: entra antes que lo que falta de "
                       "la corrida (si la corrida terminó, la línea sigue solo para procesarla).")
            boton_orden("Ponerla en la próxima carga", {"cmd": "colocar", "pieza": pieza},
                        f"{PIEZAS[pieza]['nombre']}: a la carga", linea in ("corriendo", "terminada"),
                        "Solo con la línea trabajando o con la corrida terminada.", "colocar",
                        ":material/download:")

        # 3. Sabotajes: se le hace algo a la línea y ella tiene que notarlo.
        with st.container(border=True, key="panel_sabotajes"):
            seccion("Sabotajes", "hágale algo a la línea: se tiene que dar cuenta sola" +
                    ("" if activa else " · <b>necesitan la línea trabajando o en pausa</b>"), numero=3, primera=True)
            cv = tel.get("casillas_vasos") or []
            hay_vaso = activa and bool(cv and (cv[0] or (len(cv) > 1 and cv[1])))
            radio = (tel.get("carro") or {}).get("radio") or {}
            vasos, manos = st.columns(2, gap="medium")
            with vasos:
                subgrupo("Vasos", "los vigila la cámara de vasos")
                boton_orden("Retirar un vaso", {"cmd": "sabotaje", "tipo": "retirar_vaso"}, "Vaso retirado", hay_vaso,
                            "Alguien se lleva un vaso de la verificación o del llenado.", "s1")
                boton_orden("Cambiar por un vaso igual", {"cmd": "sabotaje", "tipo": "vaso_igual"}, "Vaso cambiado",
                            hay_vaso, "Mismo tamaño, otro marcador: lo detecta la cámara de vasos.", "s2")
                boton_orden("Cambiar por una figura", {"cmd": "sabotaje", "tipo": "cambiar_vaso"},
                            "Vaso cambiado por figura", hay_vaso, "Otra forma: la silueta no coincide.", "s5")
                boton_orden("Vaso con algo adentro", {"cmd": "sabotaje", "tipo": "vaso_con_algo"},
                            "El próximo vaso trae algo", activa, "Lo detecta el sensor que mira al interior del vaso.", "s6")
            with manos:
                subgrupo("Manos", "infrarrojo, cortina y cámara")
                boton_orden("✋ Mano en la carga", {"cmd": "sabotaje", "tipo": "mano_carga"}, "Mano en la carga", activa,
                            "El infrarrojo la ve; la casilla viaja vacía y sale al rechazo.", "s3")
                boton_orden("✋ Mano que saca un vaso", {"cmd": "sabotaje", "tipo": "mano_saca_vaso"},
                            "Una mano se llevó un vaso", activa,
                            "La cortina congela la zona y la cámara encuentra el vaso que falta.", "s4")
                intruso = bool(tel.get("intruso"))
                boton_orden("✋ Quitar la mano" if intruso else "✋ Mano en tapa/prensa",
                            {"cmd": "sabotaje", "tipo": "intruso_off" if intruso else "intruso_on"},
                            "Mano quitada" if intruso else "Mano en la zona", activa,
                            "Activa la cortina de seguridad.", "s7")
            subgrupo("Carro", "la radio ESP-NOW entre el carro y la estación")
            r1, r2 = st.columns([1.2, 1], gap="medium", vertical_alignment="center")
            with r1:
                cortada = bool(radio) and not radio.get("conectada")
                boton_orden("📡 Reconectar la radio" if cortada else "📡 Cortar la radio del carro",
                            {"cmd": "sabotaje", "tipo": "radio_on" if cortada else "radio_off"},
                            "Radio del carro", activa and bool(radio),
                            "El carro termina la vuelta solo y guarda sus mensajes; no se le carga otro vaso a ciegas.",
                            "s8")
            with r2:
                nota("El carro termina la vuelta solo y guarda sus mensajes. Para moverlo con órdenes: pestaña "
                           "Carro y ruta." if radio else "En esta corrida no hay carro con física (carro de reemplazo).")

        # 4. Fin de turno.
        with st.container(border=True, key="panel_turno"):
            seccion("Fin de turno", "lo que quedó en los tubos sin completar un lote", numero=4, primera=True)
            boton_orden("📦 Empacar lo guardado en los tubos (fin de turno)", {"cmd": "embalar_parciales"}, "Empacando",
                        bool(tel.get("almacen_valor")), "Empaca también los tubos que no completaron un lote.", "s9")
    with der:
        seccion("Qué contestó la línea", primera=True)
        mostrar_respuesta()
        seccion("Qué pasó después", "lo último, en palabras simples")
        pintar(html_frases(datos.frases_recientes(9)))
