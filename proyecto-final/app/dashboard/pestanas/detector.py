"""Pestaña Detector de monedas: YOLO con la foto del celular, aparte de la línea (vision/yolo_monedas)."""

from __future__ import annotations


def pestana() -> None:
    from vision.yolo_monedas import vista  # perezoso: OpenCV solo se carga al abrir esta pestaña

    vista.dibujar()
