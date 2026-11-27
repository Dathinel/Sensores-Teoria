"""Lo que se ve del detector: subir/tomar la foto, la foto anotada, la tabla de medidas y la descarga.

Lo usan dos páginas con el mismo código:
- la pestaña "Detector de monedas" del tablero (app/dashboard/pestanas/detector.py), en el PC;
- la página para el celular (`python -m vision.yolo_monedas`), abierta en la red Wi-Fi.
La última detección se guarda en vision/capturas/ultima/, así lo que se toma con el celular
aparece también en el tablero del PC (son dos procesos de Streamlit distintos).
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps

from app.dashboard.estilo import aviso, nota, seccion, tabla
from vision.yolo_monedas import detector

ULTIMA = Path(__file__).resolve().parents[1] / "capturas" / "ultima"
LADO_MAX = 1600  # px: la foto del S24 (4000x3000) se reduce; la escala es relativa, la medida no cambia


def _leer(archivo) -> np.ndarray:
    # exif_transpose: el celular guarda la foto acostada y marca el giro en el EXIF.
    img = ImageOps.exif_transpose(Image.open(archivo)).convert("RGB")
    img.thumbnail((LADO_MAX, LADO_MAX))
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)


def _filas(r: dict) -> list[dict]:
    return [{
        "#": n, "Moneda": f"${pz['valor']:,}".replace(",", ".") if pz["es_moneda"] else "no es moneda",
        "Familia": pz["clase"].split("_")[1] if pz["es_moneda"] else "—",
        "Confianza": f"{pz['confianza']:.0%}",
        "Diámetro medido": f"{pz['diametro_mm']:.1f} mm" if pz["diametro_mm"] else "—",
        "Nominal": f"{pz['nominal_mm']:.1f} mm" if pz["nominal_mm"] else "—",
        "Diferencia": f"{pz['error_mm']:+.1f} mm" if pz["error_mm"] is not None else "—",
        "Figura": f"{pz['figura']} ({pz['circularidad']:.2f})",
        "Color": pz["color_anillo"] if not pz["bimetalica"] else f"{pz['color_centro']} / {pz['color_anillo']}",
        "Bimetálica (vista / tabla)": f"{'sí' if pz['bimetalica'] else 'no'} / {'sí' if pz['bimetalica_tabla'] else 'no'}",
        "Material (tabla)": pz["material_tabla"],
        "Nota": pz.get("nota", ""),
    } for n, pz in enumerate(r["piezas"], 1)]


def _guardar(anotada: np.ndarray, filas: list[dict], r: dict, zip_: bytes, original: np.ndarray) -> None:
    ULTIMA.mkdir(parents=True, exist_ok=True)
    # La foto SIN anotar queda también en capturas/: sirve para etiquetarla y reentrenar el clasificador.
    cv2.imwrite(str(ULTIMA.parent / f"original_{len(list(ULTIMA.parent.glob('original_*.jpg'))) + 1:03d}.jpg"), original)
    cv2.imwrite(str(ULTIMA / "anotada.jpg"), anotada)
    (ULTIMA / "recortes.zip").write_bytes(zip_)
    (ULTIMA / "medidas.json").write_text(json.dumps(
        {"filas": filas, "escala": r["escala"], "fuente_escala": r["fuente_escala"]}, ensure_ascii=False),
        encoding="utf-8")


def _mostrar_ultima() -> None:
    if not (ULTIMA / "medidas.json").exists():
        nota("Todavía no hay ninguna foto analizada.")
        return
    m = json.loads((ULTIMA / "medidas.json").read_text(encoding="utf-8"))
    st.image(str(ULTIMA / "anotada.jpg"), width="stretch")
    total = sum(int(f["Moneda"].strip("$").replace(".", "")) for f in m["filas"] if f["Moneda"].startswith("$"))
    seccion("Medidas de cada moneda", f"{sum(f['Moneda'].startswith('$') for f in m['filas'])} monedas · total ${total:,}".replace(",", ".")
            + f" · escala: {m['fuente_escala']}")
    if m["filas"]:
        tabla(pd.DataFrame(m["filas"]))
    else:
        aviso("No se encontró ninguna moneda colombiana en la foto.", "ambar")
    st.download_button("Descargar las imágenes de las monedas (ZIP)", (ULTIMA / "recortes.zip").read_bytes(),
                       file_name="monedas_detectadas.zip", mime="application/zip", icon=":material/download:")


def dibujar() -> None:
    seccion("Detector de monedas colombianas (YOLO)",
            "aparte de la línea: no usa sensores ni manda órdenes", primera=True)
    if not detector.hay_modelo():
        aviso("Falta el modelo entrenado (vision/modelos/yolo_monedas.pt): corra "
              "<code>python -m vision.yolo_monedas.entrenar</code> con el dataset en vision/dataset/yolo_monedas.", "rojo")
        return
    nota("En el celular, «Tomar foto» abre la cámara. Para medir en mm de verdad, ponga junto a las monedas el "
         "cuadrado ArUco impreso de 5 cm; sin él, cada moneda se mide contra las demás de la misma foto.")
    archivo = st.file_uploader("Tomar o subir una foto de las monedas", type=["jpg", "jpeg", "png", "webp"],
                               key="foto_monedas")
    if archivo is not None and st.session_state.get("_foto_vista") != archivo.file_id:
        with st.spinner("Buscando monedas..."):
            img = _leer(archivo)
            r = detector.detectar(img)
            anotada = detector.anotar(img, r["piezas"])
            _guardar(anotada, _filas(r), r, detector.zip_recortes(img, r["piezas"], anotada), img)
        st.session_state["_foto_vista"] = archivo.file_id
    _mostrar_ultima()
