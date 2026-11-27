"""YOLO por prueba y error: entrena varias variantes con el mismo dataset y se queda con la mejor.

    entorno\\Scripts\\python -m vision.yolo_monedas.entrenar                    # dataset en vision/dataset/yolo_monedas
    entorno\\Scripts\\python -m vision.yolo_monedas.entrenar --epocas 40 --variantes yolo11n-seg yolov8n-seg

El dataset es el export "YOLOv8" de Roboflow (carpetas train/valid/test y data.yaml). Si las
etiquetas traen polígonos se prueban los modelos de segmentación (la máscara da un diámetro más
fino que la caja); si no, los de detección. Los pesos base los baja Ultralytics la primera vez.

Deja:
- vision/modelos/yolo_monedas.pt                   el ganador (no se sube: pesa)
- vision/resultados/yolo_monedas/comparativa.md    tabla de cada intento (sí se sube: es del informe)
- vision/resultados/yolo_monedas/<variante>/       curvas, matriz de confusión y ejemplos de cada intento
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import yaml

AQUI = Path(__file__).resolve().parent
VISION = AQUI.parent
DATASET = VISION / "dataset" / "yolo_monedas"
MODELOS = VISION / "modelos"
RESULTADOS = VISION / "resultados" / "yolo_monedas"


def es_segmentacion(dataset: Path) -> bool:
    """Una etiqueta de segmentación tiene más de 5 números por línea (clase + polígono)."""
    for txt in (dataset / "train" / "labels").glob("*.txt"):
        for linea in txt.read_text().splitlines():
            if linea.strip():
                return len(linea.split()) > 5
    return False


def yaml_absoluto(dataset: Path) -> Path:
    """Roboflow escribe rutas tipo ../train/images que Ultralytics resuelve mal: se reescriben."""
    datos = yaml.safe_load((dataset / "data.yaml").read_text(encoding="utf-8"))
    datos.update(path=str(dataset), train="train/images", val="valid/images")
    datos["test"] = "test/images" if (dataset / "test" / "images").exists() else None
    salida = dataset / "data_local.yaml"
    salida.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    return salida


def elegir(dataset: Path, imgsz: int) -> dict:
    """Mide en test cada intento ya entrenado (runs/<variante>/weights/best.pt) y copia el mejor.
    Va aparte del entrenamiento para que varias variantes se entrenen en paralelo (un proceso cada una)."""
    from ultralytics import YOLO

    datos = yaml_absoluto(dataset)
    intentos = []
    for pesos in sorted((MODELOS / "runs").glob("*/weights/best.pt")):
        v = pesos.parents[1].name
        # Se compara en test (fotos que el entrenamiento nunca vio, ni para parar): valid es muy chico.
        m = YOLO(str(pesos)).val(data=str(datos), imgsz=imgsz, device="cpu", workers=0, plots=False, verbose=False,
                                 split="test" if (dataset / "test").exists() else "val")
        caja = m.box
        epocas = len((pesos.parents[1] / "results.csv").read_text().splitlines()) - 1
        intentos.append({"variante": v, "epocas": epocas, "mAP50": round(float(caja.map50), 4),
                         "mAP50_95": round(float(caja.map), 4), "precision": round(float(caja.mp), 4),
                         "recall": round(float(caja.mr), 4), "pesos": str(pesos)})
        destino = RESULTADOS / v  # lo del informe (gráficas), sin los pesos
        destino.mkdir(parents=True, exist_ok=True)
        for f in pesos.parents[1].glob("*.png"):
            shutil.copy(f, destino / f.name)
        print(intentos[-1])
    ganador = max(intentos, key=lambda i: i["mAP50_95"])
    shutil.copy(ganador["pesos"], MODELOS / "yolo_monedas.pt")
    # El segundo mejor de OTRA arquitectura se usa junto al ganador (detector.candidatos): se complementan.
    base = lambda i: i["variante"].removesuffix("-gpu")
    otros = sorted((i for i in intentos if base(i) != base(ganador)), key=lambda i: -i["mAP50_95"])
    if otros:
        shutil.copy(otros[0]["pesos"], MODELOS / "yolo_monedas_2.pt")
    (RESULTADOS / "comparativa.json").write_text(json.dumps({"ganador": ganador["variante"], "intentos": intentos},
                                                            indent=2), encoding="utf-8")
    filas = "\n".join(f"| {i['variante']}{' **(ganador)**' if i is ganador else ''} | {i['epocas']} | {i['mAP50']:.3f} | "
                      f"{i['mAP50_95']:.3f} | {i['precision']:.3f} | {i['recall']:.3f} |" for i in intentos)
    (RESULTADOS / "comparativa.md").write_text(
        f"# YOLO por prueba y error (imgsz {imgsz}, CPU)\n\nMétricas de cajas en el conjunto test.\n\n"
        "| Variante | Épocas | mAP50 | mAP50-95 | Precisión | Recall |\n|---|---|---|---|---|---|\n" + filas + "\n",
        encoding="utf-8")
    print(f"\nGanador: {ganador['variante']} -> {MODELOS / 'yolo_monedas.pt'}")
    return ganador


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--dataset", type=Path, default=DATASET)
    a.add_argument("--epocas", type=int, default=60)
    a.add_argument("--horas", type=float, default=1.75, help="tope de tiempo por variante (corta y guarda el mejor)")
    a.add_argument("--hilos", type=int, default=0, help="hilos de CPU (0 = todos); en paralelo, repartirlos")
    a.add_argument("--variantes", nargs="*", help="p. ej. yolov8n-seg yolo11n-seg (sin .pt)")
    a.add_argument("--imgsz", type=int, default=640)
    a.add_argument("--dispositivo", default="cpu", help="cpu o 0 (la GPU, con el entorno instalados/entorno-gpu)")
    a.add_argument("--lote", type=int, default=8, help="imágenes por paso (16 en la GPU de 4 GB)")
    a.add_argument("--continuar", metavar="SUFIJO", help="seguir desde runs/<variante>/weights/best.pt; "
                                                        "el intento nuevo se guarda como <variante>-SUFIJO")
    a.add_argument("--sin-elegir", action="store_true", help="solo entrenar (otro proceso elige al final)")
    a.add_argument("--solo-elegir", action="store_true", help="no entrenar: comparar lo ya entrenado")
    args = a.parse_args()

    if args.solo_elegir:
        elegir(args.dataset, args.imgsz)
        return

    import time

    import torch
    from ultralytics import YOLO

    if args.hilos:
        torch.set_num_threads(args.hilos)
    seg = es_segmentacion(args.dataset)
    variantes = args.variantes or (["yolov8n-seg", "yolo11n-seg"] if seg else ["yolov8n", "yolo11n"])
    datos = yaml_absoluto(args.dataset)
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    pesos_base = MODELOS / "base"
    pesos_base.mkdir(parents=True, exist_ok=True)

    for v in variantes:
        print(f"\n=== intento: {v} (hasta {args.epocas} épocas o {args.horas} h, dispositivo {args.dispositivo}) ===", flush=True)
        nombre = v
        if args.continuar:
            # Seguir desde lo mejor que ya aprendió esta variante (p. ej. en el CPU), no desde cero:
            # la GPU complementa ese trabajo en vez de repetirlo (usuario, 2026-11-24).
            modelo, nombre = YOLO(str(MODELOS / "runs" / v / "weights" / "best.pt")), f"{v}-{args.continuar}"
        else:
            modelo = YOLO(str(pesos_base / f"{v}.pt"))  # Ultralytics baja el .pt oficial ahí si no está
        inicio = time.time()

        def tope(entrenador):  # el tiempo del usuario manda: al pasar el tope se para y queda best.pt
            if time.time() - inicio > args.horas * 3600:
                entrenador.stop = True

        modelo.add_callback("on_fit_epoch_end", tope)
        modelo.train(data=str(datos), epochs=args.epocas, imgsz=args.imgsz, device=args.dispositivo, batch=args.lote, workers=0,
                     project=str(MODELOS / "runs"), name=nombre, exist_ok=True, patience=15, plots=True, verbose=False)
    if not args.sin_elegir:
        elegir(args.dataset, args.imgsz)


if __name__ == "__main__":
    main()
