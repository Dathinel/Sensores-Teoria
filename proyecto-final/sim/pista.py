"""Trazado de la pista del vehiculo (docs/especificacion.md, seccion 4 y fase 6).

La pista se describe en `config/parametros.yaml` (bloque `pista`) como una
lista de tramos -- rectas y curvas de radio constante --, igual que se
arma una pista real con cinta aislante: "300 mm derecho, media vuelta a la
izquierda de radio 300 mm, 600 mm derecho...". Este modulo convierte esa
lista en la linea central muestreada cada centimetro.

Es Python puro (sin PyBullet ni Three.js) a proposito: la misma linea la
usan el visor 3D (via sim/geometria.py), la simulacion del carro en
PyBullet y las pruebas, y asi los tres no se pueden desalinear.

Convenciones: metros y radianes; `rumbo` es el angulo de avance medido
desde el eje +x hacia +y (antihorario); una curva con angulo positivo gira
a la izquierda; `s` es la distancia recorrida desde la salida.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PuntoPista:
    x: float
    y: float
    rumbo: float
    s: float


def generar_linea_central(
    tramos: list[dict], inicio: tuple[float, float, float], paso_m: float = 0.01
) -> list[PuntoPista]:
    """`inicio` = (x, y, rumbo) de la salida. Cada tramo se muestrea con
    pasos de ~`paso_m`; el ultimo punto de cada tramo es exacto (no se
    acumula error de redondeo de un tramo al siguiente)."""
    x, y, rumbo = inicio
    s = 0.0
    puntos = [PuntoPista(x, y, rumbo, s)]

    for tramo in tramos:
        if tramo["tipo"] == "recta":
            largo = tramo["largo_mm"] / 1000
            n = max(1, round(largo / paso_m))
            x0, y0, s0 = x, y, s
            for i in range(1, n + 1):
                d = largo * i / n
                puntos.append(PuntoPista(x0 + d * math.cos(rumbo), y0 + d * math.sin(rumbo), rumbo, s0 + d))
            x, y, s = puntos[-1].x, puntos[-1].y, puntos[-1].s

        elif tramo["tipo"] == "curva":
            radio = tramo["radio_mm"] / 1000
            angulo = math.radians(tramo["angulo_grados"])
            signo = 1 if angulo > 0 else -1
            # El centro de giro queda a la izquierda (curva positiva) o a la
            # derecha (negativa) del sentido de avance, a un radio de
            # distancia.
            cx = x - signo * radio * math.sin(rumbo)
            cy = y + signo * radio * math.cos(rumbo)
            largo = radio * abs(angulo)
            n = max(1, round(largo / paso_m))
            rumbo0, s0 = rumbo, s
            for i in range(1, n + 1):
                r = rumbo0 + angulo * i / n
                puntos.append(PuntoPista(
                    cx + signo * radio * math.sin(r), cy - signo * radio * math.cos(r), r, s0 + largo * i / n
                ))
            x, y, rumbo, s = puntos[-1].x, puntos[-1].y, puntos[-1].rumbo, puntos[-1].s
        else:
            raise ValueError(f"tramo de pista desconocido: {tramo!r}")
    return puntos


def punto_en(linea: list[PuntoPista], s: float) -> PuntoPista:
    """Punto de la linea central a distancia `s` de la salida (interpolado
    entre las dos muestras vecinas)."""
    if s <= 0:
        return linea[0]
    for a, b in zip(linea, linea[1:]):
        if b.s >= s:
            t = (s - a.s) / (b.s - a.s) if b.s > a.s else 0
            return PuntoPista(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.rumbo + (b.rumbo - a.rumbo) * t, s)
    return linea[-1]
