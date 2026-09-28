"""Las palabras del tablero: nombres en español simple de cada estado, causa y
evento, y la frase que cuenta cada evento para quien no conoce el sistema.

Las frases son las mismas de la versión anterior del dashboard, palabra por
palabra (docs/interfaz-dashboard.md); lo nuevo es el TONO de cada una (el color
del borde de la frase: verde bien, rojo rechazo/alarma, azul carro, ámbar
vasos/lotes, morado pruebas del operador).
"""

from __future__ import annotations

import html
import json

from control import reglas

ESTACIONES_MONEDAS = ("Presencia", "Material", "Visión", "Descarga")
ESTACIONES_VASOS = ("Verificación", "Llenado", "Tapa", "Prensa", "Descarga")
DENOMINACIONES = (50, 100, 200, 500, 1000)
TUBOS = ("50", "100", "200", "500", "1000", "otras")

# Qué etapa detecta cada causa (todas salen por la misma bandeja: filtro total).
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
DECISIONES = ["Aceptada", "No metálico", "Fuera de rango", "No circular", "Perforado", "No reconocida", "Incoherente"]

NOMBRE_TIPO_REAL = {"moneda": "moneda", "boton_plastico": "botón de plástico", "boton_metalico": "botón metálico",
                    "bloque": "bloque", "vacia": "casilla vacía", "mano": "mano",
                    # apariencia (la pieza es "metal redondo" para los sensores, pero no se llama botón)
                    "moneda_extranjera": "moneda extranjera", "disco": "disco metálico",
                    "bloque_metalico": "bloque metálico"}
ESTADO_VASO_TXT = {"vacia": "vacío", "valida": "listo para llenar", "invalida": "no sirve", "llenando": "llenándose",
                   "llena": "lleno", "tapada": "tapado", "rechazada": "rechazado", "entregada": "entregado"}
ESTADO_LINEA_TXT = {"corriendo": "La línea está trabajando", "pausada": "La línea está en pausa",
                    "paro": "PARO de emergencia: todo detenido", "terminada": "La corrida terminó",
                    "detenida": "La línea está detenida"}
TONO_ESTADO_LINEA = {"corriendo": "verde", "pausada": "ambar", "paro": "rojo", "terminada": "azul"}
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


def _pesos(valor) -> str:
    return f"${int(valor or 0):,}".replace(",", ".")


def _denominacion(d) -> str:
    return "otras denominaciones" if d == "otras" else _pesos(d)


# Eventos del carro que son un problema (borde rojo) en vez de información (azul).
_CARRO_PROBLEMA = {"sin_enlace", "camino_bloqueado", "bloqueado", "atascado", "vuelve_con_vaso", "punto_con_error"}


def frase_evento(ev: dict) -> tuple[str, str, str] | None:
    """Evento → (tono, ícono, frase en palabras simples). None = no se muestra
    en el resumen (detalle interno)."""
    d = json.loads(ev["payload"])
    t = ev["tipo"]
    if t == "elemento_final":
        if d["veredicto"] == "aceptada":
            return "verde", "✅", f'Moneda de <b>{_pesos(d.get("denominacion"))}</b> aceptada: va a su tubo del almacén.'
        causa = d.get("causa") or d.get("motivo")
        return "rojo", "🚫", (f'Pieza rechazada: <b>{NOMBRE_CAUSA.get(causa, causa)}</b> '
                              f'({QUE_FILTRA.get(causa, "no pasó los filtros")}). Sale a la bandeja de rechazo.')
    if t == "embalado":
        return "ambar", "📦", (f'Se juntó un lote: {d["cantidad"]} monedas de {_denominacion(d["denominacion"])} '
                               f'caen al vaso {d["vaso"]} ({_pesos(d["valor"])}).')
    if t == "descarga":
        if d["destino"] == "entrega":
            return "verde", "🥤", f'El vaso {d["vaso"]} (tapado, {_pesos(d["valor"])}) pasa a la canaleta de entrega.'
        if d["destino"] == "vacio":
            return "gris", "♻️", f'El vaso {d["vaso"]} llegó vacío: se desecha.'
        return "rojo", "🚫", f'El vaso {d["vaso"]} sale a la bandeja de rechazo de vasos.'
    if t == "sabotaje_detectado":
        return "rojo", "🛡️", (f'<b>Sabotaje detectado</b> en el vaso {d["vaso"]} ({d["motivo"].replace("_", " ")}): '
                              "se saca de la línea.")
    if t == "cortina":
        if d["activa"]:
            return "rojo", "🖐️", "<b>Mano en la zona de tapa y prensa</b>: la prensa sube y la cinta de vasos se detiene."
        return "verde", "🖐️", "La zona de tapa y prensa quedó libre: la línea sigue."
    if t == "alarma":
        return "rojo", "⚠️", f'Alarma: {d.get("tipo", "").replace("_", " ")}.'
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
            # Órdenes (fase 7: asistente o botones)
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
        if t not in textos:
            return None
        tono = "rojo" if t in _CARRO_PROBLEMA else ("verde" if t == "entregado" else "azul")
        return tono, "🚗", textos[t]
    if t == "sabotaje":
        return "morado", "🧪", f'Prueba del operador: {str(d.get("tipo", "")).replace("_", " ")}.'
    if t == "respuesta" and d.get("origen") == "asistente":
        return ("verde" if d["ok"] else "ambar"), ("🗣️" if d["ok"] else "✋"), \
            f'Orden del asistente: {html.escape(d["detalle"])}.'
    return None


def describir_evento(ev: dict) -> str:
    """Bitácora técnica (Línea en vivo): la frase simple si la hay; si no, el evento tal cual."""
    r = frase_evento(ev)
    hora = ev["ts"][11:19]
    if r:
        return f'<span class="h">{hora}</span> {r[1]} {r[2]}'
    datos = json.loads(ev["payload"])
    txt = ", ".join(f"{k}={v}" for k, v in datos.items() if k not in ("src", "ev", "tick"))
    return (f'<span class="h">{hora}</span> <span class="o">{ev["origen"]}</span> {ev["tipo"]} '
            f'<span class="h">{html.escape(txt)[:140]}</span>')
