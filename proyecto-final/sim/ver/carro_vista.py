"""Lo que se agrega para VER el mundo del carro (sim/vehiculo_sim.py).

El mundo del carro tiene piso, muros, muelle y carro con fisica real, pero la
pista (el piso claro, la linea negra, las franjas de meta y de giro) NO es un
cuerpo: los infrarrojos de linea se emulan midiendo la distancia de cada
sensor a la linea central (`sim/pista.py`). Para que se vea, aqui se dibujan
como piezas SOLO VISUALES (sin forma de colision): ningun `rayTest` del
ultrasonico o del laser las ve y las ruedas no las tocan, asi que no cambian
nada de la fisica. Salen de la misma linea central que usa el control.
"""

from __future__ import annotations

import math

import numpy as np
import pybullet as p

from sim.geometria import geometria_completa
from sim.pista import generar_linea_central
from sim.ver.comun import Camara, Vista, caja_visual


def decorar_pista(cliente: int, parametros: dict) -> dict:
    """Pista, linea, franjas y rotulos de los muros. Devuelve la geometria."""
    geo = geometria_completa(parametros)
    pista = parametros["pista"]
    s = geo["pista"]["salida"]
    linea = generar_linea_central(pista["tramos"], (s["x"], s["y"], s["rumbo"]))
    medio_ancho = pista["ancho_mm"] / 2000
    medio_linea = pista["ancho_linea_mm"] / 2000
    paso = 4   # muestras de 1 cm: un tramo recto cada 4 cm sigue bien las curvas de 30 cm
    for i in range(0, len(linea) - 1, paso):
        a, b = linea[i], linea[min(i + paso, len(linea) - 1)]
        largo = math.hypot(b.x - a.x, b.y - a.y)
        if largo < 1e-6:
            continue
        rumbo = math.atan2(b.y - a.y, b.x - a.x)
        centro = ((a.x + b.x) / 2, (a.y + b.y) / 2)
        caja_visual(cliente, (*centro, 0.0005), (largo / 2 + 0.003, medio_ancho, 0.0005), (0.86, 0.86, 0.83, 1), rumbo)
        caja_visual(cliente, (*centro, 0.0012), (largo / 2 + 0.001, medio_linea, 0.0003), (0.03, 0.03, 0.03, 1), rumbo)
    for clave, color in (("franja_meta", (0.05, 0.05, 0.05, 1)), ("franja_giro", (0.05, 0.05, 0.05, 1))):
        f = geo["pista"][clave]
        caja_visual(cliente, (f["x"], f["y"], 0.0014), (f["ancho"] / 2, medio_ancho, 0.0003), color, f["rumbo"])
    return geo


def camara_siguiendo(carro, distancia=0.95, yaw=35.0, pitch=-38.0) -> Camara:
    x, y, _ = carro.pose()
    return Camara((x, y, 0.03), distancia, yaw, pitch)


class PanelCarro:
    """Rotulo del carro: estado del control, evasiones, sensores y el vaso."""

    def __init__(self, vista: Vista, carro, geo: dict, *, en_ventana: bool = True):
        self.vista = vista
        self.carro = carro
        self.geo = geo
        self.eventos: list[str] = []
        self.evasiones = 0
        self.en_ventana = en_ventana
        if en_ventana:
            for i, o in enumerate(geo["pista"]["obstaculos"]):
                vista.rotulo(f"muro_{i}", f"MURO {i + 1}", (o["x"], o["y"], o["alto"] + 0.04), (1, 0.5, 0.4), 1.2)
            m = geo["pista"]["meta"]
            vista.rotulo("meta", "META", (m["x"], m["y"], 0.08), (1, 0.85, 0.2), 1.4)
            s = geo["pista"]["salida"]
            vista.rotulo("muelle", "MUELLE", (s["x"] + 0.12, s["y"], 0.08), (0.4, 0.85, 1), 1.2)

    def eventos_nuevos(self, eventos: list[dict]) -> None:
        for e in eventos:
            if e["ev"] == "evasion":
                self.evasiones += 1
            self.eventos.append(f"{e['ev']} ({e.get('ts', 0):.0f} s)")
        self.eventos = self.eventos[-4:]

    def sincronizar_vaso(self) -> None:
        """En `sim/vehiculo_sim.py` el vaso es un link del carro que SIEMPRE
        esta (al sacarlo solo cambia su masa: el control lo sabe por el
        infrarrojo de la cuna). Para que en la ventana y el video no se vea un
        vaso que ya no esta, se vuelve invisible (solo el color: la fisica no
        cambia)."""
        c = self.carro
        if getattr(self, "_vaso_visible", None) != c.vaso_cargado:
            self._vaso_visible = c.vaso_cargado
            p.changeVisualShape(c.carro, c.junta_vaso, rgbaColor=[0.95, 0.95, 0.95, 1 if c.vaso_cargado else 0],
                                physicsClientId=c.cli)

    def renglones(self) -> list:
        c = self.carro
        us, tof = c._distancia_us, c._distancia_tof     # los dos ya vienen en mm (None: nada al frente)
        return [
            (f"Carro: {c.control.estado}  (fase {c.control.fase})   vaso: {'sí' if c.vaso_cargado else 'no'}",
             (255, 230, 120)),
            (f"Láser: {'-' if tof is None else f'{tof:.0f} mm'}   ultrasónico: {'-' if us is None else f'{us:.0f} mm'}"
             f"   evasiones: {self.evasiones}", (230, 230, 230)),
            (f"Toques de muro: {c.toques_muro}   cabeceo máx. del vaso: {math.degrees(c.inclinacion_max_vaso):.1f} grados",
             (230, 230, 230)),
            ("Últimos eventos: " + ", ".join(self.eventos), (160, 220, 255)),
        ]

    def rotular_carro(self) -> None:
        if self.en_ventana:
            x, y, _ = self.carro.pose()
            self.vista.rotulo("carro", f"{self.carro.control.estado}", (x, y, 0.16), (1, 0.9, 0.4), 1.1)


def minimapa(img: np.ndarray, geo: dict, carro, lado: int = 170) -> np.ndarray:
    """Mapa chico de toda la pista en la esquina (dibujo de la geometria, no
    un render): linea, muros, meta y el rastro real del carro."""
    import cv2

    linea = np.array(geo["pista"]["linea"])
    xs, ys = linea[:, 0], linea[:, 1]
    x0, x1, y0, y1 = xs.min() - 0.15, xs.max() + 0.15, ys.min() - 0.15, ys.max() + 0.15
    escala = (lado - 10) / max(x1 - x0, y1 - y0)

    def px(x, y):
        return int(5 + (x - x0) * escala), int(lado - 5 - (y - y0) * escala)

    mapa = np.full((lado, lado, 3), 40, np.uint8)
    cv2.polylines(mapa, [np.array([px(x, y) for x, y in linea])], False, (200, 200, 200), 1, cv2.LINE_AA)
    for o in geo["pista"]["obstaculos"]:
        cv2.circle(mapa, px(o["x"], o["y"]), 4, (60, 90, 220), -1)
    m = geo["pista"]["meta"]
    cv2.circle(mapa, px(m["x"], m["y"]), 4, (40, 210, 250), -1)
    if len(carro.traza) > 1:
        cv2.polylines(mapa, [np.array([px(x, y) for x, y in carro.traza])], False, (90, 220, 120), 1, cv2.LINE_AA)
    x, y, _ = carro.pose()
    cv2.circle(mapa, px(x, y), 5, (255, 255, 255), -1)
    h, w = img.shape[:2]
    img[h - lado - 30:h - 30, w - lado - 10:w - 10] = mapa
    return img
