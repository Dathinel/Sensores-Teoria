"""Cabecera: título, chips de estado (línea, ciclo, origen de los datos,
internet) y los avisos que se tienen que ver de lejos (usuario, 2026-09-27):
NO ES EN VIVO, ESP32 EMULADO, SIN INTERNET y la prueba de un filtro en curso.
Se refresca sola."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from . import datos
from .estilo import esc, html_aviso, html_aviso_grande, html_chip, pintar
from .textos import ESTADO_LINEA_TXT, TONO_ESTADO_LINEA


def origen_datos(tel: dict) -> tuple[str, str, bool]:
    """(texto, tono, lleno) del chip que dice de dónde salen los datos."""
    if tel.get("backend") == "real":
        if (tel.get("hardware") or {}).get("emulada"):
            return "🧪 ESP32 EMULADO (sin placa)", "azul", False
        return "🔌 ESP32 REAL", "morado", True
    return "🖥 SIMULACIÓN (PyBullet)", "azul", False


@st.fragment(run_every=datos.REFRESCO_S)
def cabecera() -> None:
    from app import asistente   # se busca en cada llamada: las pruebas cambian hay_internet

    tel = datos.telemetria()
    viva = datos.simulacion_viva()
    internet = asistente.hay_internet()
    estado = tel["linea"] if tel else "sin supervisor"

    chips = [html_chip(ESTADO_LINEA_TXT.get(estado, estado), TONO_ESTADO_LINEA.get(estado, "") if viva else "")]
    if tel:
        texto, tono, lleno = origen_datos(tel)
        chips += [html_chip(f'ciclo {tel.get("tick", "—")}'), html_chip(texto, tono, lleno=lleno)]
    chips.append(html_chip("🌐 con internet", "verde", lleno=False) if internet
                 else html_chip("📴 SIN INTERNET", "rojo"))
    pintar(
        f'<div class="cabecera"><span class="moneda"></span><h1>Logística de monedas inteligentes</h1>{"".join(chips)}</div>'
        '<div class="subtitulo">Clasifica monedas colombianas, las empaca en vasos de una sola denominación y un '
        "carro autónomo los lleva a la meta · Elemento 7: detector de monedas y vasos · Micros y Laboratorio, UMNG</div>")

    if tel is None:
        pintar(html_aviso("No hay datos todavía. Abra <b>visor.bat</b> (arranca todo) o, en una terminal, "
                          "<code>python -m app.lanzar</code>."))
        return
    avisos = []
    from sim.carga_escenarios import prueba_de_un_filtro

    prueba = prueba_de_un_filtro(tel.get("escenario") or "")
    if prueba:
        piezas = datos.piezas_decididas()
        bien = int((piezas["causa"] == prueba["causa"]).sum()) if len(piezas) else 0
        avisos.append(html_aviso(
            f'<b>🧪 Prueba de un filtro: {prueba["nombre"]}</b> ({prueba["estacion"]}). {prueba["espera"]} '
            f'Van {len(piezas)} piezas decididas; {bien} rechazadas por <code>{prueba["causa"]}</code>'
            + ("." if bien == len(piezas) else " (<b>ojo: otras causas</b>)."), "morado" if bien == len(piezas) else "ambar"))
    if not viva:
        hora = datetime.fromisoformat(tel["ts"])
        avisos.append(html_aviso_grande(
            "⏸", "NO ES EN VIVO", "La simulación no está corriendo: lo que se ve son los datos guardados de la "
            f"última corrida ({hora:%d/%m %H:%M}). Para verla en vivo, abra <b>visor.bat</b>.", "demo"))
    elif tel.get("backend") == "real" and (tel.get("hardware") or {}).get("emulada"):
        avisos.append(html_aviso_grande(
            "🧪", "ESP32 EMULADO", "Está en modo hardware real pero no hay ninguna placa conectada: responde una "
            "estación EMULADA (el mismo firmware con sensores falsos).", "demo"))
    if not internet:
        avisos.append(html_aviso_grande(
            "📴", "SIN INTERNET", "La planta, el carro y este dashboard siguen funcionando: todo pasa en este PC "
            "(ESP32 por USB, carro por ESP-NOW, datos en SQLite). El asistente responde con el modelo local de la "
            "laptop y la voz es la de este PC (Whisper para oír, voz de Windows para hablar).", "offline"))
    if avisos:
        pintar("".join(avisos))


def mostrar_respuesta() -> None:
    """Qué contestó la línea a la última orden (de un botón o del asistente)."""
    r = (datos.telemetria() or {}).get("ultima_orden")
    if r:
        pintar(f'<div class="respuesta {"ok" if r["ok"] else "no"}"><span class="de">respuesta de la línea</span>'
               f'{"✔" if r["ok"] else "✖"} {esc(r["detalle"])}</div>')


# La misma respuesta, refrescándose sola donde no hay ya un fragmento alrededor (barra lateral).
respuesta_orden = st.fragment(run_every=datos.REFRESCO_S)(mostrar_respuesta)
