"""Medidas de cada moneda detectada: diámetro en mm, figura y detalles (docs/especificacion.md §12).

Solo usa numpy y OpenCV, sin YOLO: recibe la foto y, por cada moneda, su caja (y su máscara si el
modelo es de segmentación). Así se puede probar sin modelo (ver `__main__` al final).

La escala (píxeles por mm) sale, en este orden:
1. de un cuadrado ArUco impreso de lado conocido (`yolo_monedas.aruco_lado_mm`) — medida real;
2. si no hay ArUco, de las mismas monedas: cada clase tiene su diámetro nominal en
   `config/monedas.yaml`, y la mediana de (diámetro en px / nominal) da la escala. Con varias
   monedas, cada una se mide contra las demás; con una sola, el diámetro es el nominal (se avisa).
"""

from __future__ import annotations

import math

import cv2
import numpy as np


def escala_aruco(imagen: np.ndarray, lado_mm: float) -> float | None:
    """Píxeles por mm si en la foto hay un marcador ArUco 4x4 (cualquiera del DICT_4X4_50)."""
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50))
    esquinas, ids, _ = detector.detectMarkers(gris)
    if ids is None or not len(esquinas):
        return None
    c = esquinas[0].reshape(4, 2)
    lado_px = np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)])
    return float(lado_px / lado_mm)


def mascara_de_caja(imagen: np.ndarray, caja: tuple[int, int, int, int]) -> np.ndarray:
    """Máscara de la moneda dentro de su caja cuando el modelo no trae segmentación:
    Otsu sobre el recorte y el contorno más grande (la moneda llena casi toda su caja)."""
    x1, y1, x2, y2 = caja
    recorte = cv2.GaussianBlur(cv2.cvtColor(imagen[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY), (5, 5), 0)
    _, bin_ = cv2.threshold(recorte, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # El fondo es lo que toca el borde del recorte: si quedó blanco, se invierte.
    borde = np.concatenate([bin_[0], bin_[-1], bin_[:, 0], bin_[:, -1]])
    if borde.mean() > 127:
        bin_ = 255 - bin_
    contornos, _ = cv2.findContours(bin_, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    mascara = np.zeros(imagen.shape[:2], np.uint8)
    if contornos:
        mayor = max(contornos, key=cv2.contourArea)
        if cv2.contourArea(mayor) > 0.3 * bin_.size:
            cv2.drawContours(mascara[y1:y2, x1:x2], [mayor], -1, 255, cv2.FILLED)
            return mascara
    # Otsu no separó (moneda del mismo tono que el fondo): el círculo inscrito en la caja.
    cv2.ellipse(mascara, ((x1 + x2) // 2, (y1 + y2) // 2), ((x2 - x1) // 2, (y2 - y1) // 2), 0, 0, 360, 255, -1)
    return mascara


def figura(mascara: np.ndarray) -> dict:
    """Diámetro equivalente en px, circularidad (1 = círculo perfecto) y elongación de la elipse."""
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(contornos, key=cv2.contourArea)
    area, perimetro = cv2.contourArea(c), cv2.arcLength(c, True)
    (cx, cy), _ = cv2.minEnclosingCircle(c)
    ejes = sorted(cv2.fitEllipse(c)[1]) if len(c) >= 5 else (1.0, 1.0)
    return {"centro": (cx, cy), "diametro_px": 2 * math.sqrt(area / math.pi),
            "circularidad": 4 * math.pi * area / perimetro ** 2 if perimetro else 0.0,
            "elongacion": ejes[1] / ejes[0] if ejes[0] else 1.0}


def _color(lab: np.ndarray, hsv: np.ndarray) -> str:
    """Nombre del color medio: plateado (poca saturación), dorado o cobrizo (por el tono)."""
    if hsv[1] < 45:
        return "plateado"
    return "dorado" if 15 <= hsv[0] <= 35 else "cobrizo"


def detalles(imagen: np.ndarray, mascara: np.ndarray, centro, diametro_px: float, delta_e_bimetal: float) -> dict:
    """Bandera bimetálica (§12): contraste del disco central contra el anillo exterior de la misma
    moneda, en Lab. Es relativo a la propia pieza, así sobrevive al desgaste y a la luz."""
    alto, ancho = mascara.shape
    yy, xx = np.ogrid[:alto, :ancho]
    r = np.hypot(xx - centro[0], yy - centro[1]) / (diametro_px / 2)
    dentro = mascara > 0
    lab = cv2.cvtColor(imagen, cv2.COLOR_BGR2LAB).astype(float)
    hsv = cv2.cvtColor(imagen, cv2.COLOR_BGR2HSV).astype(float)
    centro_lab = lab[dentro & (r < 0.45)].mean(axis=0)
    anillo = dentro & (r > 0.75) & (r < 0.92)
    anillo_lab = lab[anillo].mean(axis=0)
    # Solo el color (a, b) y con la mediana: el brillo (L) cambia con el relieve y los reflejos, y
    # con él una de 50 o de 100 salía "bimetálica". Medido en fotos de test: bimetálicas 17-21, las demás 0-3.
    delta = float(np.linalg.norm(np.median(lab[dentro & (r < 0.45)][:, 1:], axis=0)
                                 - np.median(lab[anillo][:, 1:], axis=0)))
    return {"delta_e": delta, "bimetalica": delta >= delta_e_bimetal,
            "color_centro": _color(centro_lab, hsv[dentro & (r < 0.45)].mean(axis=0)),
            "color_anillo": _color(anillo_lab, hsv[anillo].mean(axis=0))}


def croma(imagen: np.ndarray, mascara: np.ndarray, centro, diametro_px: float) -> float:
    """Qué tan "de color" es el metal (a, b de Lab, mediana): dorada ~33, plateada 7-16 (foto real S24)."""
    alto, ancho = mascara.shape
    yy, xx = np.ogrid[:alto, :ancho]
    r = np.hypot(xx - centro[0], yy - centro[1]) / (diametro_px / 2)
    lab = cv2.cvtColor(imagen, cv2.COLOR_BGR2LAB).astype(float)
    ab = np.median(lab[(mascara > 0) & (r < 0.85)][:, 1:], axis=0) - 128
    return float(np.hypot(*ab))


def agujeros(imagen: np.ndarray, centro, diametro_px: float) -> int:
    """Cuántos agujeros pasantes tiene la pieza: manchas redondas DENTRO del disco que tienen el color
    del FONDO (se ve la mesa a través). Una moneda colombiana no tiene ninguno; un botón tiene 2 o 4 y
    una arandela uno al centro. El relieve de una moneda (el "50", el escudo) es del color del metal
    con sombra, no del fondo, y por eso no cuenta."""
    alto, ancho = imagen.shape[:2]
    R = diametro_px / 2
    yy, xx = np.ogrid[:alto, :ancho]
    r = np.hypot(xx - centro[0], yy - centro[1]) / R
    lab = cv2.cvtColor(cv2.GaussianBlur(imagen, (3, 3), 0), cv2.COLOR_BGR2LAB).astype(float)
    fondo_zona = (r > 1.15) & (r < 1.4)
    if fondo_zona.sum() < 20:
        return 0  # la pieza llena la foto: no hay fondo con qué comparar
    fondo = np.median(lab[fondo_zona], axis=0)
    metal = np.median(lab[r < 0.8], axis=0)
    if np.linalg.norm(fondo - metal) < 25:
        return 0  # fondo del mismo color que la pieza: no se puede decir
    # Píxel "de fondo": más cerca del color del fondo que del metal, y dentro del disco.
    parecido = (np.linalg.norm(lab - fondo, axis=2) < 0.5 * np.linalg.norm(fondo - metal)) & (r < 0.75)
    n, etiquetas, stats, _ = cv2.connectedComponentsWithStats(parecido.astype(np.uint8), connectivity=8)
    area_disco = np.pi * R * R
    cuenta = 0
    for i in range(1, n):
        a, w, h = stats[i, cv2.CC_STAT_AREA], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        redondo = a / (np.pi * (max(w, h) / 2) ** 2 + 1e-9) > 0.55 and max(w, h) <= 1.6 * min(w, h)
        if 0.004 * area_disco <= a <= 0.15 * area_disco and redondo:
            cuenta += 1
    return cuenta


def escala_por_monedas(piezas: list[dict]) -> float | None:
    """Mediana de px/mm usando el diámetro nominal de la clase detectada de cada moneda."""
    razones = [p["diametro_px"] / p["nominal_mm"] for p in piezas if p.get("nominal_mm")]
    return float(np.median(razones)) if razones else None


if __name__ == "__main__":
    # Autoprueba sin modelo: disco bimetálico sintético de 200 px sobre fondo negro.
    img = np.zeros((400, 400, 3), np.uint8)
    cv2.circle(img, (200, 200), 100, (60, 180, 210), -1)   # anillo dorado (BGR)
    cv2.circle(img, (200, 200), 55, (190, 190, 190), -1)   # centro plateado
    m = mascara_de_caja(img, (95, 95, 305, 305))
    f = figura(m)
    d = detalles(img, m, f["centro"], f["diametro_px"], 10.0)
    assert abs(f["diametro_px"] - 200) < 4 and f["circularidad"] > 0.85, f
    assert d["bimetalica"] and d["color_centro"] == "plateado" and d["color_anillo"] == "dorado", d
    assert escala_por_monedas([{"diametro_px": 200, "nominal_mm": 20.0}]) == 10.0
    assert agujeros(img, f["centro"], f["diametro_px"]) == 0, "la moneda bimetálica no tiene agujeros"
    # Botón de 4 agujeros sobre mesa blanca: por los agujeros se ve la mesa.
    boton = np.full((400, 400, 3), 235, np.uint8)
    cv2.circle(boton, (200, 200), 100, (40, 60, 140), -1)
    for dx, dy in ((-25, -25), (25, -25), (-25, 25), (25, 25)):
        cv2.circle(boton, (200 + dx, 200 + dy), 11, (235, 235, 235), -1)
    assert agujeros(boton, (200, 200), 200) == 4
    arandela = np.full((400, 400, 3), 235, np.uint8)
    cv2.circle(arandela, (200, 200), 100, (150, 150, 150), -1)
    cv2.circle(arandela, (200, 200), 35, (235, 235, 235), -1)
    assert agujeros(arandela, (200, 200), 200) == 1
    print("medir.py OK", round(f["diametro_px"], 1), round(f["circularidad"], 3), d)
