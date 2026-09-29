"""Pestaña Asistente (fase 7, CLAUDE.md §14): se le pregunta por escrito o por
voz por las cifras de la corrida o por cualquier parte del proyecto, y se le
puede pedir que mueva el carro o la línea. La lógica está en `app/asistente.py`
(DeepSeek → modelo local → reglas, lista blanca de órdenes, voz); aquí solo
está la conversación en pantalla."""

from __future__ import annotations

import threading

import streamlit as st

from app import db

from .. import datos
from ..estilo import aviso, html_chip, html_frases, nota, pintar, seccion
from ..textos import NOMBRE_ORDEN_CARRO

EJEMPLOS = [
    "¿Cuánto dinero se ha aceptado y de qué monedas?",
    "¿Por qué se rechazan las piezas y qué filtro actuó más?",
    "¿Dónde está el carro y cuántos obstáculos esquivó?",
    "¿Qué sensor detecta si una moneda es de metal y en qué pin va?",
    "Avanza el carro 30 cm",
    "Gira el carro 90 grados a la derecha",
    "Lleva el carro a la meta",
    "Vuelve al muelle",
]
PROVEEDORES = {"auto": "Automático", "deepseek": "Solo DeepSeek", "ollama": "Solo el modelo local",
               "reglas": "Solo reglas"}


def _atender_frase(frase: str) -> None:
    """Pregunta al asistente y deja en la tabla `ordenes` las órdenes que salieron
    válidas (el supervisor las vuelve a validar)."""
    from app import asistente

    with st.spinner("Pensando…"):
        r = asistente.atender(frase, datos.conexion(), usar=st.session_state.get("proveedor", "auto"))
    for orden in r.ordenes:
        db.insertar_orden(datos.conexion(), orden)
    st.session_state["asistente_ultima"] = r
    if st.session_state.get("hablar") and r.texto:
        st.session_state["asistente_audio"] = asistente.voz(r.texto)   # (audio, "mp3"|"wav") o None


def _sin_error(funcion) -> None:
    try:
        funcion()
    except Exception:  # sin faster-whisper o sin el modelo descargado: se avisa al usarlo
        pass


def pestana() -> None:
    from app import asistente

    con = datos.conexion()
    hay_clave = asistente.cliente_deepseek() is not None
    hay_local = asistente.cliente_local() is not None
    if hay_local and not st.session_state.get("local_precargado"):
        # La primera respuesta del modelo local tarda ~1 min si no está en la GPU.
        st.session_state["local_precargado"] = True
        asistente.precargar_local()
    chips = (html_chip(f'DeepSeek {"✓" if hay_clave else "sin clave"}', "verde" if hay_clave else "")
             + html_chip(f'local {asistente.MODELO_LOCAL} {"✓" if hay_local else "apagado"}', "verde" if hay_local else "")
             + html_chip("reglas ✓", "verde", lleno=False))
    pintar(f'<div class="sec primera"><h3>Asistente del proyecto</h3>{chips}</div>')
    nota("Pregúntele en palabras normales por las cifras de la corrida o por cualquier parte del proyecto (sensores, "
         "pines, decisiones), o pídale que mueva el carro o la línea (p. ej. «avanza 20 cm» o «¿cuánto dinero "
         "hay?»). Responde con los datos reales de la base de "
         "datos y la documentación del proyecto; si no tiene un dato, lo dice.")
    if not hay_clave and not hay_local:
        aviso("Sin DeepSeek ni modelo local: entiende órdenes y preguntas básicas, y para lo demás muestra la parte de "
              "la documentación más relacionada. DeepSeek: archivo <code>.env</code> con "
              "<code>DEEPSEEK_API_KEY=sk-...</code>. Local: instalar Ollama y "
              f"<code>ollama pull {asistente.MODELO_LOCAL}</code> (ver README).")

    izq, der = st.columns([1.6, 1], gap="large")
    with der:
        with st.container(border=True, key="panel_voz"):
            seccion("Cómo hablarle", primera=True)
            audio = st.audio_input("🎤 Dígale algo", key="microfono",
                                   help="Con internet lo oye Google (como el tema 4); sin internet, Whisper en este PC.")
            if not st.session_state.get("voz_precargada"):
                # Whisper tarda unos segundos en cargarse: se carga por detrás al abrir la pestaña.
                st.session_state["voz_precargada"] = True
                threading.Thread(target=lambda: _sin_error(asistente._whisper_modelo), daemon=True).start()
            if audio is not None:
                crudo = audio.getvalue()
                if st.session_state.get("audio_procesado") != hash(crudo):
                    st.session_state["audio_procesado"] = hash(crudo)
                    with st.spinner("Escuchando…"):
                        texto, detalle = asistente.transcribir(crudo)
                    if texto:
                        st.session_state["frase_pendiente"] = texto
                        st.session_state["oido_por"] = detalle
                    else:
                        st.warning(detalle)
            if st.session_state.get("oido_por"):
                st.caption(f"Última frase oída con: {st.session_state['oido_por']}")
            st.toggle("🔊 Responder en voz alta", key="hablar")
            st.selectbox("Quién responde", list(PROVEEDORES), key="proveedor", format_func=PROVEEDORES.get,
                         help="Automático: DeepSeek (en la nube, con internet); si no hay, el modelo local "
                              f"{asistente.MODELO_LOCAL} (Ollama, en este PC, sin internet); si tampoco, las reglas. "
                              "Venga de quien venga, una orden solo sale si está en la lista de órdenes permitidas, "
                              "y una pregunta nunca mueve nada.")
        seccion("Ejemplos", "clic para preguntar")
        for i, ej in enumerate(EJEMPLOS):
            if st.button(ej, key=f"ej{i}", width="stretch"):
                st.session_state["frase_pendiente"] = ej
        ordenes_del_asistente()
        if st.button("Borrar la conversación", icon=":material/delete:", width="stretch", key="borrar_chat"):
            asistente.borrar_conversacion(con)
            st.session_state.pop("asistente_ultima", None)

    with izq:
        # Texto de ayuda CORTO a propósito (2026-09-28). El aviso de consola "Recording error: Container
        # not found" que salía al abrir esta pestaña NO venía de st.audio_input sino de este
        # st.chat_input: al montarse carga por detrás la librería de la onda de audio (wavesurfer) y la
        # engancha a un contenedor suyo; si en esos milisegundos el texto de ayuda no cabe en una
        # línea, el componente pasa a su diseño "apilado" (botón de enviar debajo), vuelve a crear ese
        # contenedor y la librería ya no encuentra el viejo. Con un texto que cabe en una línea incluso
        # en la columna más angosta, no cambia de diseño al montarse y el aviso desaparece. Los ejemplos
        # de frases están en la nota de arriba y en los botones de "Ejemplos".
        frase = st.chat_input("Escríbale al asistente…")
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
                with st.expander("Documentos que consultó para responder", icon=":material/description:"):
                    st.markdown("\n".join(f"- {d}" for d in r.documentos))
        historial = asistente.conversacion(con, 30)
        if not historial:
            nota("Todavía no le ha preguntado nada.")
        # Lo más nuevo ARRIBA, pegado a donde se escribe (usuario, 2026-09-27): cada pregunta con su
        # respuesta debajo, y los pares de más nuevo a más viejo.
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
                                 avatar=":material/person:" if m["rol"] == "usuario" else ":material/smart_toy:"):
                # "$" sin escapar se lee como fórmula de LaTeX ($0 ... $12.500).
                st.markdown(m["texto"].replace("$", r"\$"))
                if m["acciones"]:
                    st.caption("Órdenes enviadas: " + " · ".join(
                        NOMBRE_ORDEN_CARRO.get(o.get("accion"), o.get("accion")) if o["cmd"] == "carro"
                        else o["cmd"] for o in m["acciones"]))
                if m["rol"] == "asistente" and m.get("modo"):
                    st.caption("respondió: " + {"deepseek": "DeepSeek",
                                                "ollama": f"modelo local ({asistente.MODELO_LOCAL})"}
                               .get(m["modo"], "intérprete de reglas"))
        audio_resp = st.session_state.pop("asistente_audio", None)
        if audio_resp:
            st.audio(audio_resp[0], format=f"audio/{audio_resp[1]}", autoplay=True)


@st.fragment(run_every=datos.REFRESCO_S)
def ordenes_del_asistente() -> None:
    """Qué pasó con cada orden que dio el asistente (la respuesta del supervisor y,
    para el carro, lo que hizo después)."""
    frases = datos.frases_de_ordenes(8)
    if frases:
        seccion("Qué pasó con las órdenes")
        pintar(html_frases(frases))
