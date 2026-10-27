"""Las ordenes permitidas (lista blanca): lo unico que el asistente puede mandar a la linea o al
carro, venga de las reglas, del modelo local o de DeepSeek, y como se le cuentan a la persona."""

from __future__ import annotations

import math

ACCIONES_CARRO = {
    "detener": {},
    "avanzar": {"distancia_m": (0.01, 1.5)},
    "retroceder": {"distancia_m": (0.01, 0.30)},
    "girar": {"grados": (-180.0, 180.0)},
    "ir_a": {"x": (-1.0, 4.0), "y": (-3.0, 2.0)},
    "ir_meta": {},
    "volver_muelle": {},
    "seguir_linea": {},
}
def _capacidad_tubo() -> int:
    """El lote no puede pasar de lo que cabe en un tubo (config: planta.capacidad_tubo). Antes el
    tope era un 25 escrito a mano: si el tubo del CAD cambia, el asistente seguia aceptando lotes
    que nunca se completan (un lote de 40 en un tubo de 25 = `tubo_lleno` para siempre)."""
    try:
        from app.configuracion import cargar_parametros

        return int(cargar_parametros()["planta"]["capacidad_tubo"])
    except Exception:   # sin config legible, el valor documentado (docs/especificacion.md, seccion 5)
        return 25


ORDENES_LINEA = {
    "iniciar": {},
    "pausar": {},
    "reanudar": {},
    "paro": {},
    "embalar_parciales": {},
    "lote": {"valor": (1, _capacidad_tubo())},
    "velocidad": {"valor": (0.25, 8.0)},
}


def validar_accion(a: dict) -> tuple[dict | None, str]:
    """Devuelve (orden lista para la tabla `ordenes`, "") o (None, motivo).
    Todo numero fuera de rango o accion desconocida se descarta."""
    if not isinstance(a, dict):
        return None, "no es un objeto"
    cmd = a.get("cmd")
    if cmd == "carro":
        accion = a.get("accion")
        if accion not in ACCIONES_CARRO:
            return None, f"acción del carro desconocida: {accion}"
        limpia = {"cmd": "carro", "accion": accion}
        campos = ACCIONES_CARRO[accion]
    elif cmd in ORDENES_LINEA:
        limpia = {"cmd": cmd}
        campos = ORDENES_LINEA[cmd]
    else:
        return None, f"orden desconocida: {cmd}"
    for nombre, (minimo, maximo) in campos.items():
        try:
            valor = float(a[nombre])
        except (KeyError, TypeError, ValueError):
            return None, f"a '{cmd} {a.get('accion', '')}' le falta '{nombre}'"
        if not math.isfinite(valor) or not minimo <= valor <= maximo:
            return None, f"'{nombre}' = {valor:g} está fuera de {minimo:g}…{maximo:g}"
        if cmd == "lote" and valor != int(valor):
            # "10.5 monedas por vaso" no existe: se rechaza en vez de truncar en silencio.
            return None, f"el lote tiene que ser un número entero de monedas (llegó {valor:g})"
        limpia[nombre] = int(valor) if cmd == "lote" else round(valor, 3)
    if cmd == "carro" and accion == "girar" and limpia["grados"] == 0:
        return None, "un giro de 0 grados no hace nada"
    if cmd == "iniciar":
        limpia["escenario"] = "prueba_completa"
    limpia["origen"] = "asistente"
    return limpia, ""


def describir_ordenes(ordenes: list[dict]) -> str:
    textos = []
    for o in ordenes:
        if o["cmd"] == "carro":
            a = o["accion"]
            textos.append({
                "detener": "Detengo el carro.",
                "avanzar": f"El carro avanza {float(o.get('distancia_m', 0)) * 100:.0f} cm (mira el camino antes).",
                "retroceder": f"El carro retrocede {float(o.get('distancia_m', 0)) * 100:.0f} cm.",
                "girar": f"El carro gira {abs(float(o.get('grados', 0))):.0f}° a la "
                         f"{'izquierda' if float(o.get('grados', 0)) > 0 else 'derecha'}.",
                "ir_a": f"El carro va al punto ({o.get('x')}, {o.get('y')}) m.",
                "ir_meta": "El carro va a la meta siguiendo la línea.",
                "volver_muelle": "El carro vuelve al muelle.",
                "seguir_linea": "El carro retoma la línea.",
            }.get(a, a))
        else:
            textos.append({"pausar": "Pauso la línea.", "reanudar": "La línea sigue.", "paro": "PARO de emergencia.",
                           "iniciar": "Empiezo una corrida nueva.", "embalar_parciales": "Empaco lo guardado.",
                           "lote": f"Lote de {o.get('valor')} monedas por vaso.",
                           "velocidad": f"Velocidad ×{o.get('valor')}."}.get(o["cmd"], o["cmd"]))
    return " ".join(textos)
