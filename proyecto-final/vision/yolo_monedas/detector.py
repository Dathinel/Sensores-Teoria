"""YOLO + medidas: de una foto a la lista de monedas colombianas con su diámetro, figura y detalles.

El modelo (`vision/modelos/yolo_monedas.pt`, lo deja `entrenar.py`) solo conoce las 9 clases
colombianas de las familias nueva y antigua; lo que no se parezca con confianza suficiente
(`yolo_monedas.confianza_min`) no se cuenta. Plástico o metal da igual: se mira la apariencia.
"""

from __future__ import annotations

import io
import zipfile
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from control import monedas
from control.configuracion import cargar_parametros
from vision.yolo_monedas import clasificador, medir

MODELO = Path(__file__).resolve().parents[1] / "modelos" / "yolo_monedas.pt"
MODELO_2 = MODELO.with_name("yolo_monedas_2.pt")  # el segundo de entrenar.py: se fusiona con el ganador


def parametros() -> dict:
    return cargar_parametros()["yolo_monedas"]


def corregir_etiqueta(nombre: str) -> str:
    """Nombre que dio YOLO (entrenado con las etiquetas cruzadas del dataset) -> moneda real."""
    return clase_colombiana(str(parametros()["correccion_etiquetas"].get(str(nombre), nombre)))


def clase_colombiana(nombre: str) -> str:
    """Nombre del dataset → clase de config/monedas.yaml ('1000' solo existe en la familia nueva)."""
    nombre = nombre.strip().lower().replace("-", "_").replace(" ", "_")
    return nombre if "_" in nombre else f"{nombre}_nueva"


@lru_cache(maxsize=4)  # detector ganador, segundo y clasificador
def _modelo(ruta: str, _mtime: float):
    from ultralytics import YOLO  # import perezoso: el tablero carga aunque no esté el modelo

    return YOLO(ruta)


def hay_modelo() -> bool:
    return MODELO.exists()


def _iou(a, b) -> float:
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter + 1e-9)


def candidatos(imagen: np.ndarray, p: dict) -> list[dict]:
    """Las detecciones de TODOS los modelos (el ganador y el segundo), fusionadas: cada uno ve monedas
    que el otro no (en test, juntos encuentran 31 de 33 monedas con 2 falsas; solos, 27-30 con 4-10).
    Si dos cajas son la misma moneda (IoU > 0,5, sin mirar la clase) queda la de más confianza."""
    todas = []
    for ruta in (MODELO, MODELO_2):
        if ruta is not MODELO and not ruta.exists():
            continue
        r = _modelo(str(ruta), ruta.stat().st_mtime).predict(imagen, conf=p["confianza_min"],
                                                              imgsz=p["tamano_imagen"], verbose=False)[0]
        for i, caja in enumerate(r.boxes):
            todas.append({"xyxy": caja.xyxy[0].tolist(), "conf": float(caja.conf),
                          "nombre": corregir_etiqueta(r.names[int(caja.cls)]),
                          "poligono": r.masks.xy[i] if r.masks is not None else None})
    elegidas = []
    for c in sorted(todas, key=lambda c: -c["conf"]):
        igual = next((e for e in elegidas if _iou(c["xyxy"], e["xyxy"]) > 0.5), None)
        if igual is None:
            elegidas.append({**c, "otras": []})
        else:
            igual["otras"].append((c["nombre"], c["conf"]))  # lo que el otro modelo vio en esa moneda
    return elegidas


def _clase(imagen: np.ndarray, c: dict, bimetalica_vista: bool) -> tuple[str, float, str, list[str]]:
    """Clase de la moneda: la opinión MÁS SEGURA entre YOLO y el clasificador de recortes
    (clasificador.py). Medido en las 33 monedas de test: YOLO solo 21, clasificador solo 23, la más
    segura de las dos 24. El color (bimetálica) solo avisa: corregir la clase con él bajaba a 16."""
    clase, conf = c["nombre"], c["conf"]
    opciones = [clase_colombiana(c["nombre"])] + [clase_colombiana(n) for n, _ in c["otras"]]
    if clasificador.MODELO_CLS.exists():
        rec = clasificador.recorte_cuadrado(imagen, *c["xyxy"])
        r = _modelo(str(clasificador.MODELO_CLS), clasificador.MODELO_CLS.stat().st_mtime).predict(rec, verbose=False)[0]
        conf_cls = float(r.probs.top1conf)
        opciones += [clase_colombiana(r.names[int(i)]) for i in r.probs.top5[:3]]
        if conf_cls >= conf:
            clase, conf = r.names[int(r.probs.top1)], conf_cls
    clase = clase_colombiana(clase)
    ref = monedas.buscar_por_clase(clase)
    nota = "revisar: el color no cuadra con la tabla" if ref and ref.bimetalica != bimetalica_vista else ""
    return clase, conf, nota, opciones


def color_de_clase(clase: str) -> str:
    """bimetalica, dorada o plateada, según la tabla (config/monedas.yaml)."""
    ref = monedas.buscar_por_clase(clase)
    if ref.bimetalica:
        return "bimetalica"
    return "dorada" if any(m in ref.material for m in ("bronce", "recubierto", "laton")) else "plateada"


def color_medido(pz: dict, p: dict) -> str:
    if pz["bimetalica"]:
        return "bimetalica"
    return "dorada" if pz["croma"] >= p["dorado_croma_min"] else "plateada"


def ajustar_clases(piezas: list[dict], p: dict, escala_fija: float | None = None) -> float | None:
    """Decide TODAS las monedas de la foto a la vez: busca la escala (px/mm) y la clase de cada una
    que mejor cuadran con (1) los diámetros de la tabla, (2) el color medido y (3) lo que dijo el
    modelo. Con la foto real del S24 el modelo solo acertaba 1 de 5: el tamaño relativo y el color
    no dependen de que la foto se parezca a las de entrenamiento. Devuelve la escala elegida."""
    reales = [pz for pz in piezas if pz["es_moneda"]]
    if not reales:
        return escala_fija
    clases = [c for c in monedas.clases_colombianas() if monedas.reconocible(c)]

    def costo(pz, clase, s):
        nom = monedas.diametro_nominal_mm(clase)
        tam = abs(pz["diametro_px"] / s - nom) / nom / p["tolerancia_diametro"] if s else 0.0
        col = p["castigo_color"] if color_de_clase(clase) != color_medido(pz, p) else 0.0
        mod = 0.0 if clase == pz["clase"] else (p["castigo_modelo"] / 2 if clase in pz["opciones"] else p["castigo_modelo"])
        return tam + col + mod

    if escala_fija:
        escalas = [escala_fija]
    elif len(reales) == 1:
        return None  # una sola moneda y sin ArUco: no hay tamaño con qué comparar, decide el modelo
    else:
        d = [pz["diametro_px"] for pz in reales]
        escalas = np.linspace(min(d) / 28.0, max(d) / 15.0, 600)
    mejor = min(escalas, key=lambda s: sum(min(costo(pz, c, s) for c in clases) for pz in reales))
    if mejor is not None and not escala_fija:
        # Solo si los tamaños cuadran ENTRE SÍ (monedas reales sobre una mesa, misma escala). En un
        # montaje de catálogo cada moneda tiene su propia escala y corregir por tamaño empeoraba
        # (test: 9/33 en vez de 24/33): ahí manda el modelo.
        error = np.mean([min(abs(pz["diametro_px"] / mejor - monedas.diametro_nominal_mm(c)) / monedas.diametro_nominal_mm(c)
                             for c in clases if color_de_clase(c) == color_medido(pz, p)) for pz in reales])
        if error > p["ajuste_error_max"]:
            return None
    for pz in reales:
        nueva = min(clases, key=lambda c: costo(pz, c, mejor))
        if nueva != pz["clase"]:
            pz["nota"] = f"corregida por tamaño y color (el modelo decía {pz['clase']})"
            pz["clase"] = nueva
        pz["valor"], pz["nominal_mm"] = monedas.valor_pesos(nueva), monedas.diametro_nominal_mm(nueva)
    return mejor


def detectar(imagen: np.ndarray) -> dict:
    """Corre YOLO y mide cada moneda. Devuelve {'piezas': [...], 'escala': px/mm, 'fuente_escala': ...}."""
    p = parametros()
    alto, ancho = imagen.shape[:2]
    piezas = []
    for c in candidatos(imagen, p):
        x1, y1, x2, y2 = (int(round(v)) for v in c["xyxy"])
        x1, y1, x2, y2 = max(x1, 0), max(y1, 0), min(x2, ancho), min(y2, alto)
        if x2 - x1 < 8 or y2 - y1 < 8:
            continue
        if c["poligono"] is not None and len(c["poligono"]) >= 3:
            mascara = np.zeros((alto, ancho), np.uint8)
            cv2.fillPoly(mascara, [c["poligono"].astype(np.int32)], 255)
        else:
            mascara = medir.mascara_de_caja(imagen, (x1, y1, x2, y2))
        if not mascara.any():
            continue
        f = medir.figura(mascara)
        det = medir.detalles(imagen, mascara, f["centro"], f["diametro_px"], p["bimetalica_delta_e"])
        clase, conf, nota, opciones = _clase(imagen, c, det["bimetalica"])
        # ¿Es moneda? El dataset solo trae monedas, así que YOLO no aprendió qué NO es una: lo deciden
        # los agujeros (botón, arandela) y la duda del clasificador (extranjera, ficha, otra cosa).
        n_agujeros = medir.agujeros(imagen, f["centro"], f["diametro_px"])
        es_moneda = True
        if f["circularidad"] < p["redonda_circularidad_min"] or f["elongacion"] > p["redonda_elongacion_max"]:
            es_moneda, nota = False, "no es moneda: no es redonda"
        elif n_agujeros:
            es_moneda, nota = False, f"no es moneda: {n_agujeros} agujero(s), botón o arandela"
        elif conf < p["clase_conf_min"]:
            es_moneda, nota = False, f"no reconocida: ninguna moneda colombiana pasa de {p['clase_conf_min']:.0%}"
        piezas.append({"clase": clase, "confianza": conf, "caja": (x1, y1, x2, y2), "mascara": mascara, "nota": nota,
                       "es_moneda": es_moneda, "agujeros": n_agujeros, "opciones": opciones,
                       "croma": medir.croma(imagen, mascara, f["centro"], f["diametro_px"]),
                       "valor": monedas.valor_pesos(clase) if es_moneda else 0,
                       "nominal_mm": monedas.diametro_nominal_mm(clase) if es_moneda else None, **f, **det})

    escala, fuente = medir.escala_aruco(imagen, p["aruco_lado_mm"]), "ArUco"
    escala_monedas = ajustar_clases(piezas, p, escala)
    if escala is None:
        escala = escala_monedas
        fuente = ("tamaño relativo de las monedas (sin ArUco)" if sum(pz["es_moneda"] for pz in piezas) > 1
                  else "nominal (una sola moneda, sin ArUco)")
        if escala is None:
            escala = medir.escala_por_monedas([pz for pz in piezas if pz["es_moneda"]])
    for pz in piezas:
        ref = monedas.buscar_por_clase(pz["clase"])
        pz["diametro_mm"] = pz["diametro_px"] / escala if escala else None
        pz["error_mm"] = pz["diametro_mm"] - pz["nominal_mm"] if pz["diametro_mm"] and pz["nominal_mm"] else None
        pz["figura"] = ("disco" if pz["circularidad"] >= p["circularidad_min"] and pz["elongacion"] < 1.15
                        else "inclinada u ocluida")
        pz["bimetalica_tabla"] = bool(ref and ref.bimetalica)
        pz["material_tabla"] = ref.material if ref else "—"
    return {"piezas": piezas, "escala": escala, "fuente_escala": fuente}


def anotar(imagen: np.ndarray, piezas: list[dict]) -> np.ndarray:
    """La foto con el contorno de cada moneda, su número, clase y diámetro."""
    salida = imagen.copy()
    grosor = max(2, imagen.shape[1] // 400)
    for n, pz in enumerate(piezas, 1):
        contornos, _ = cv2.findContours(pz["mascara"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(salida, contornos, -1, (52, 177, 242) if pz["es_moneda"] else (75, 83, 229), grosor)
        x1, y1 = pz["caja"][:2]
        texto = (f"{n}. ${pz['valor']} {pz['clase'].split('_')[1]}" if pz["es_moneda"] else f"{n}. no es moneda") + (
            f" {pz['diametro_mm']:.1f}mm" if pz["diametro_mm"] else "")
        escala_txt = max(0.5, imagen.shape[1] / 1600)
        cv2.putText(salida, texto, (x1, max(y1 - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, escala_txt, (0, 0, 0), grosor + 3)
        cv2.putText(salida, texto, (x1, max(y1 - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, escala_txt, (255, 255, 255), grosor)
    return salida


def recorte(imagen: np.ndarray, pz: dict, margen: float = 0.1) -> np.ndarray:
    x1, y1, x2, y2 = pz["caja"]
    m = int(margen * max(x2 - x1, y2 - y1))
    return imagen[max(y1 - m, 0):y2 + m, max(x1 - m, 0):x2 + m]


def zip_recortes(imagen: np.ndarray, piezas: list[dict], anotada: np.ndarray) -> bytes:
    """ZIP con la foto anotada y un recorte .jpg por moneda (nombre: n_clase_diametro.jpg)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("foto_anotada.jpg", cv2.imencode(".jpg", anotada)[1].tobytes())
        for n, pz in enumerate(piezas, 1):
            mm = f"_{pz['diametro_mm']:.1f}mm" if pz["diametro_mm"] else ""
            z.writestr(f"{n:02d}_{pz['clase'] if pz['es_moneda'] else 'no_es_moneda'}{mm}.jpg", cv2.imencode(".jpg", recorte(imagen, pz))[1].tobytes())
    return buf.getvalue()


if __name__ == "__main__":
    assert clase_colombiana("1000") == "1000_nueva" and clase_colombiana("100_antigua") == "100_antigua"
    assert all(monedas.buscar_por_clase(clase_colombiana(n)) for n in
               ["1000", "100_antigua", "100_nueva", "200_antigua", "200_nueva", "500_antigua", "500_nueva",
                "50_antigua", "50_nueva"])
    print("detector.py OK (clases del dataset = config/monedas.yaml)")
