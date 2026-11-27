"""Detector YOLO de monedas (vision/yolo_monedas): medidas y escala, con un YOLO falso (sin pesos)."""

from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from vision.yolo_monedas import detector, medir


def _foto():
    """Dos monedas sobre fondo negro: 500 nueva (23,7 mm, bimetálica) y 100 nueva (20,3 mm), a 10 px/mm."""
    img = np.zeros((600, 900, 3), np.uint8)
    cv2.circle(img, (250, 300), 118, (60, 180, 210), -1)   # 500: anillo dorado
    cv2.circle(img, (250, 300), 65, (190, 190, 190), -1)   # centro plateado
    cv2.circle(img, (650, 300), 101, (40, 165, 215), -1)   # 100 nueva: dorada
    return img


class _Caja:
    def __init__(self, xyxy, cls, conf):
        self.xyxy, self.cls, self.conf = [SimpleNamespace(tolist=lambda: xyxy)], cls, conf


def _yolo_falso(*_a, **_k):
    cajas = [_Caja([131, 181, 369, 419], 0, 0.9), _Caja([548, 198, 752, 402], 1, 0.8)]
    return SimpleNamespace(predict=lambda *a, **k: [SimpleNamespace(boxes=cajas, masks=None,
                                                                    names={0: "200_nueva", 1: "50_nueva"})])  # nombres cruzados del dataset


@pytest.fixture
def con_yolo_falso(monkeypatch):
    monkeypatch.setattr(detector, "_modelo", _yolo_falso)
    monkeypatch.setattr(detector, "MODELO", SimpleNamespace(stat=lambda: SimpleNamespace(st_mtime=0)))
    monkeypatch.setattr(detector, "MODELO_2", SimpleNamespace(exists=lambda: False))
    monkeypatch.setattr(detector.clasificador, "MODELO_CLS", SimpleNamespace(exists=lambda: False))


def test_las_etiquetas_cruzadas_del_dataset_se_corrigen():
    assert detector.corregir_etiqueta("50_antigua") == "1000_nueva"
    assert detector.corregir_etiqueta("1000") == "50_antigua"
    assert detector.corregir_etiqueta("500_antigua") == "500_antigua"


def test_mide_diametro_figura_y_bimetalica_sin_aruco(con_yolo_falso):
    r = detector.detectar(_foto())
    a, b = r["piezas"]
    assert "monedas" in r["fuente_escala"]
    assert a["clase"] == "500_nueva" and a["valor"] == 500 and a["bimetalica"] and a["bimetalica_tabla"]
    assert b["clase"] == "100_nueva" and not b["bimetalica"]
    assert abs(a["diametro_mm"] - 23.7) < 0.8 and abs(b["diametro_mm"] - 20.3) < 0.8
    assert a["figura"] == b["figura"] == "disco"


def test_zip_trae_la_foto_anotada_y_un_recorte_por_moneda(con_yolo_falso):
    import io
    import zipfile

    img = _foto()
    r = detector.detectar(img)
    nombres = zipfile.ZipFile(io.BytesIO(detector.zip_recortes(img, r["piezas"], detector.anotar(img, r["piezas"])))).namelist()
    assert nombres[0] == "foto_anotada.jpg" and len(nombres) == 3 and nombres[1].startswith("01_500_nueva_")


def test_aruco_da_la_escala_real():
    img = np.full((500, 500, 3), 255, np.uint8)
    marca = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), 3, 200)
    img[150:350, 150:350] = cv2.cvtColor(marca, cv2.COLOR_GRAY2BGR)
    assert medir.escala_aruco(img, 50.0) == pytest.approx(4.0, rel=0.03)


def test_todas_las_clases_del_dataset_existen_en_la_tabla():
    for n in ["1000", "100_antigua", "100_nueva", "200_antigua", "200_nueva", "500_antigua", "500_nueva",
              "50_antigua", "50_nueva"]:
        assert detector.monedas.buscar_por_clase(detector.clase_colombiana(n))


def test_un_boton_con_agujeros_no_cuenta_como_moneda(con_yolo_falso):
    img = np.full((600, 900, 3), 235, np.uint8)          # mesa blanca
    cv2.circle(img, (250, 300), 118, (60, 180, 210), -1)   # 500 de verdad
    cv2.circle(img, (250, 300), 65, (190, 190, 190), -1)
    cv2.circle(img, (650, 300), 101, (40, 60, 140), -1)    # botón de 4 agujeros donde YOLO "ve" una de 100
    for dx, dy in ((-25, -25), (25, -25), (-25, 25), (25, 25)):
        cv2.circle(img, (650 + dx, 300 + dy), 11, (235, 235, 235), -1)
    a, b = detector.detectar(img)["piezas"]
    assert a["es_moneda"] and a["valor"] == 500
    assert not b["es_moneda"] and b["valor"] == 0 and b["agujeros"] == 4 and "botón" in b["nota"]
