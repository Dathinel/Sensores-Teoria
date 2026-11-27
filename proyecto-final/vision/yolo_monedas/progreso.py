"""¿YOLO está aprendiendo bien? Puntaje de detección de monedas época por época, de cada intento.

    entorno\\Scripts\\python -m vision.yolo_monedas.progreso            # tabla en la consola
    entorno\\Scripts\\python -m vision.yolo_monedas.progreso --grafica  # + vision/resultados/yolo_monedas/progreso.png

Lee `vision/modelos/runs/<variante>/results.csv`, que Ultralytics escribe al final de cada época
(se puede correr mientras entrena). Qué mirar:
- mAP50 (cajas): de 0 a 1, cuántas monedas encuentra con la denominación correcta; >0,8 es bueno.
- mAP50-95: lo mismo pero exigiendo que la caja calce justo; es la que decide el ganador.
- Máscara mAP50: lo mismo para la silueta (con ella se mide el diámetro).
- Pérdidas (box/cls de validación): deben bajar; si suben mientras las de entrenamiento bajan, memoriza.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

RUNS = Path(__file__).resolve().parents[1] / "modelos" / "runs"
SALIDA = Path(__file__).resolve().parents[1] / "resultados" / "yolo_monedas" / "progreso.png"


def leer(carpeta: Path) -> list[dict]:
    with open(carpeta / "results.csv", newline="", encoding="utf-8") as f:
        return [{k.strip(): float(v) for k, v in fila.items()} for fila in csv.DictReader(f)]


def tendencia(valores: list[float], n: int = 5) -> str:
    """Compara el promedio de las últimas n épocas con las n anteriores."""
    if len(valores) < 2 * n:
        return "pocas épocas aún"
    antes, ahora = sum(valores[-2 * n:-n]) / n, sum(valores[-n:]) / n
    if ahora > antes + 0.02:
        return f"mejorando (+{ahora - antes:.2f})"
    return "estancado" if ahora > antes - 0.02 else f"empeorando ({ahora - antes:.2f})"


def resumen(nombre: str, filas: list[dict]) -> str:
    m50 = [f["metrics/mAP50(B)"] for f in filas]
    m95 = [f["metrics/mAP50-95(B)"] for f in filas]
    mejor = max(range(len(filas)), key=lambda i: m95[i])
    ult = filas[-1]
    seg = ult["time"] / ult["epoch"]
    lineas = [f"== {nombre}: {int(ult['epoch'])} épocas, {seg:.0f} s por época",
              f"   ahora : mAP50 {m50[-1]:.3f} | mAP50-95 {m95[-1]:.3f} | máscara mAP50 "
              f"{ult.get('metrics/mAP50(M)', 0):.3f} | precisión {ult['metrics/precision(B)']:.3f} | "
              f"recall {ult['metrics/recall(B)']:.3f}",
              f"   mejor : época {int(filas[mejor]['epoch'])}, mAP50 {m50[mejor]:.3f}, mAP50-95 {m95[mejor]:.3f}",
              f"   tendencia mAP50: {tendencia(m50)} | pérdida cls validación {filas[0]['val/cls_loss']:.2f} -> "
              f"{ult['val/cls_loss']:.2f}",
              "   época : " + " ".join(f"{int(f['epoch']):>4}" for f in filas[-12:]),
              "   mAP50 : " + " ".join(f"{v:4.2f}" for v in m50[-12:])]
    return "\n".join(lineas)


def grafica(datos: dict[str, list[dict]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4))
    for nombre, filas in datos.items():
        e = [f["epoch"] for f in filas]
        a.plot(e, [f["metrics/mAP50(B)"] for f in filas], label=f"{nombre} mAP50")
        a.plot(e, [f["metrics/mAP50-95(B)"] for f in filas], "--", label=f"{nombre} mAP50-95")
        b.plot(e, [f["val/cls_loss"] for f in filas], label=f"{nombre} validación")
        b.plot(e, [f["train/cls_loss"] for f in filas], ":", label=f"{nombre} entrenamiento")
    a.set(title="Detección de monedas (validación)", xlabel="época", ylabel="mAP", ylim=(0, 1))
    b.set(title="Pérdida de clasificación", xlabel="época")
    for ax in (a, b):
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
    fig.tight_layout()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SALIDA, dpi=120)
    print(f"Gráfica: {SALIDA}")


def main() -> None:
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--grafica", action="store_true")
    args = a.parse_args()
    datos = {c.name: leer(c) for c in sorted(RUNS.glob("*")) if (c / "results.csv").exists()}
    if not datos:
        print("Todavía no hay ninguna época terminada.")
        return
    for nombre, filas in datos.items():
        print(resumen(nombre, filas) + "\n")
    if args.grafica:
        grafica(datos)


if __name__ == "__main__":
    main()
