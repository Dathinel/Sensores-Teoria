"""Segundo paso: YOLO encuentra la moneda y este clasificador dice CUÁL es, mirando solo su recorte.

Por qué: en test YOLO encuentra 31 de 33 monedas pero acierta la clase en 21. Un clasificador que ve
la moneda sola, centrada y grande, aprende mejor la cara; y como una moneda girada sigue siendo la
misma, cada recorte de entrenamiento se guarda girado 8 veces (YOLO no gira al entrenar).

    entorno\\Scripts\\python -m vision.yolo_monedas.clasificador            # arma recortes, entrena, mide en test

Deja vision/modelos/clasificador_monedas.pt (lo usa detector.py si existe) y
vision/resultados/yolo_monedas/clasificador.md (acierto en test, para el informe).
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml

AQUI = Path(__file__).resolve().parent
DATASET = AQUI.parent / "dataset" / "yolo_monedas"
RECORTES = AQUI.parent / "dataset" / "recortes_monedas"
MODELOS = AQUI.parent / "modelos"
MODELO_CLS = MODELOS / "clasificador_monedas.pt"
RESULTADOS = AQUI.parent / "resultados" / "yolo_monedas"
LADO = 160          # px del recorte guardado
GIROS = 8           # copias giradas por recorte de entrenamiento


def recorte_cuadrado(imagen: np.ndarray, x1: float, y1: float, x2: float, y2: float, margen: float = 0.08) -> np.ndarray:
    """Cuadrado centrado en la moneda, con un poco de borde, rellenando con negro si se sale de la foto.
    El mismo recorte se usa al entrenar y al clasificar, para que el modelo vea siempre lo mismo."""
    cx, cy, lado = (x1 + x2) / 2, (y1 + y2) / 2, max(x2 - x1, y2 - y1) * (1 + 2 * margen)
    m = np.float32([[LADO / lado, 0, LADO / 2 - cx * LADO / lado], [0, LADO / lado, LADO / 2 - cy * LADO / lado]])
    return cv2.warpAffine(imagen, m, (LADO, LADO), flags=cv2.INTER_AREA, borderValue=(0, 0, 0))


def corregir(nombre: str) -> str:
    """Etiqueta cruzada del dataset -> moneda real (config: yolo_monedas.correccion_etiquetas)."""
    from vision.yolo_monedas.detector import corregir_etiqueta

    return corregir_etiqueta(nombre)


def preparar() -> None:
    nombres = yaml.safe_load((DATASET / "data.yaml").read_text(encoding="utf-8"))["names"]
    shutil.rmtree(RECORTES, ignore_errors=True)
    for parte, destino in (("train", "train"), ("valid", "val"), ("test", "test")):
        n = 0
        for img_ruta in sorted((DATASET / parte / "images").glob("*")):
            img = cv2.imread(str(img_ruta))
            h, w = img.shape[:2]
            etiquetas = (DATASET / parte / "labels" / (img_ruta.stem + ".txt")).read_text().split("\n")
            for k, linea in enumerate(l for l in etiquetas if l.strip()):
                v = linea.split()
                xy = np.array(v[1:], float).reshape(-1, 2) * [w, h]
                rec = recorte_cuadrado(img, *xy.min(0), *xy.max(0))
                carpeta = RECORTES / destino / corregir(nombres[int(v[0])])
                carpeta.mkdir(parents=True, exist_ok=True)
                for g in range(GIROS if destino == "train" else 1):
                    giro = cv2.warpAffine(rec, cv2.getRotationMatrix2D((LADO / 2, LADO / 2), g * 360 / GIROS, 1),
                                          (LADO, LADO), borderValue=(0, 0, 0))
                    cv2.imwrite(str(carpeta / f"{img_ruta.stem[:40]}_{k}_{g}.jpg"), giro)
                    n += 1
        print(f"{destino}: {n} recortes")
    # Fotos reales del celular, etiquetadas a mano en vision/pruebas_reales/etiquetas.json: el dataset
    # es de internet y la cámara real se ve distinta; cada moneda real pesa x3 (y girada 8 veces).
    import json
    reales = AQUI.parent / "pruebas_reales" / "etiquetas.json"
    for foto, lista in (json.loads(reales.read_text(encoding="utf-8")).items() if reales.exists() else []):
        img = cv2.imread(str(reales.parent / foto))
        for k, e in enumerate(lista):
            rec = recorte_cuadrado(img, *e["caja"])
            carpeta = RECORTES / "train" / e["clase"]
            carpeta.mkdir(parents=True, exist_ok=True)
            for g in range(GIROS * 3):
                giro = cv2.warpAffine(rec, cv2.getRotationMatrix2D((LADO / 2, LADO / 2), g * 360 / (GIROS * 3), 1),
                                      (LADO, LADO), borderValue=(0, 0, 0))
                cv2.imwrite(str(carpeta / f"real_{Path(foto).stem}_{k}_{g}.jpg"), giro)
    for parte in ("val", "test"):  # Ultralytics pide las mismas carpetas de clase en las tres partes
        for c in map(corregir, nombres):
            (RECORTES / parte / c).mkdir(parents=True, exist_ok=True)


def entrenar(epocas: int, variante: str) -> None:
    from ultralytics import YOLO

    YOLO(str(MODELOS / "base" / f"{variante}.pt")).train(
        data=str(RECORTES), epochs=epocas, imgsz=LADO, device="cpu", batch=32, workers=0, patience=15,
        project=str(MODELOS / "runs"), name=f"cls-{variante}", exist_ok=True, plots=True, verbose=False)
    shutil.copy(MODELOS / "runs" / f"cls-{variante}" / "weights" / "best.pt", MODELO_CLS)


def medir_test() -> float:
    from ultralytics import YOLO

    modelo = YOLO(str(MODELO_CLS))
    bien = total = 0
    for carpeta in sorted((RECORTES / "test").iterdir()):
        for f in carpeta.glob("*.jpg"):
            total += 1
            r = modelo.predict(str(f), verbose=False)[0]
            bien += r.names[int(r.probs.top1)] == carpeta.name
    acierto = bien / total
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    (RESULTADOS / "clasificador.md").write_text(
        f"# Clasificador de recortes (segundo paso)\n\nAcierto de clase en las monedas de test: {bien}/{total} "
        f"({acierto:.0%}). Con solo la clase de YOLO: 21/33.\n", encoding="utf-8")
    print(f"Clasificador en test: {bien}/{total} ({acierto:.0%})")
    return acierto


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--epocas", type=int, default=40)
    a.add_argument("--variante", default="yolo11n-cls")
    args = a.parse_args()
    preparar()
    entrenar(args.epocas, args.variante)
    medir_test()


if __name__ == "__main__":
    main()
