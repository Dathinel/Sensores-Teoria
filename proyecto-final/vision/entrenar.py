"""Entrenamiento del clasificador de monedas (fase 5, CLAUDE.md sección 12): Keras + MobileNetV2.

Se corre UNA vez, cuando ya hay fotos (python -m vision.capturar_dataset), y en el entorno de
visión (TensorFlow no tiene versión para Python 3.14; ver vision/README.md):

    vision\\entorno\\Scripts\\python -m vision.entrenar

Genera (y se versionan en git, porque son material del informe):
    vision/resultados/matriz_confusion.png    qué clase real terminó predicha como qué
    vision/resultados/curva_confianza.png     aciertos y errores según la confianza del modelo
    vision/resultados/metricas.json           exactitud por clase y la confianza mínima sugerida
y el modelo en vision/modelos/monedas.keras (NO se versiona: pesa; ver .gitignore).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "vision" / "dataset"
MODELOS = RAIZ / "vision" / "modelos"
RESULTADOS = RAIZ / "vision" / "resultados"

# 96x96 píxeles (CLAUDE.md sección 12): la cámara, la distancia y la luz son siempre las mismas, así
# que el modelo no necesita ver la moneda en grande; con 96 px una moneda de 17 mm (la más chica)
# todavía muestra su cara, y la red corre en el portátil en unos pocos milisegundos.
LADO = 96
# Del cuadro de 1080p se recorta un cuadrado alrededor del centro (donde la casilla deja la pieza):
# 40 mm de lado a ~0,1 mm/px = 400 px. Deja margen para la moneda más grande (26,7 mm).
RECORTE_PX = 400
SEMILLA = 7
PROPORCION_VALIDACION = 0.2


def cargar_imagenes():
    """(imágenes 96x96x3 en float 0-255, etiquetas enteras, nombres de clase) desde vision/dataset/."""
    import cv2
    import numpy as np

    nombres = sorted(p.name for p in DATASET.iterdir() if p.is_dir() and any(p.glob("*.jpg")))
    if len(nombres) < 2:
        sys.exit("Hacen falta fotos de al menos 2 clases en vision/dataset/ (python -m vision.capturar_dataset).")
    imagenes, etiquetas = [], []
    for i, nombre in enumerate(nombres):
        for ruta in sorted((DATASET / nombre).glob("*.jpg")):
            cuadro = cv2.imread(str(ruta))
            alto, ancho = cuadro.shape[:2]
            cy, cx, m = alto // 2, ancho // 2, min(RECORTE_PX, alto, ancho) // 2
            recorte = cuadro[cy - m:cy + m, cx - m:cx + m]
            # OpenCV lee en BGR; MobileNetV2 se preentrenó con imágenes RGB.
            recorte = cv2.cvtColor(cv2.resize(recorte, (LADO, LADO), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
            imagenes.append(recorte)
            etiquetas.append(i)
    return np.array(imagenes, dtype="float32"), np.array(etiquetas), nombres


def separar(imagenes, etiquetas):
    """80/20 ESTRATIFICADO: cada clase aporta la misma proporción a validación. Si no, una clase con
    pocas fotos podría quedar sin ninguna en validación y su exactitud no se mediría."""
    import numpy as np

    rng = random.Random(SEMILLA)
    ent, val = [], []
    for clase in np.unique(etiquetas):
        indices = list(np.where(etiquetas == clase)[0])
        rng.shuffle(indices)
        corte = max(1, int(len(indices) * PROPORCION_VALIDACION))
        val += indices[:corte]
        ent += indices[corte:]
    return (imagenes[ent], etiquetas[ent]), (imagenes[val], etiquetas[val])


def construir_modelo(n_clases: int):
    import tensorflow as tf

    # Aumento de datos: SOLO lo que de verdad cambia en el montaje. La moneda cae con cualquier
    # giro (rotación completa), se corre unos milímetros dentro de la casilla (traslación chica) y
    # la luz varía un poco entre días (brillo/contraste). No se voltea: una cara espejada no existe.
    aumento = tf.keras.Sequential([
        tf.keras.layers.RandomRotation(0.5, fill_mode="constant"),   # 0,5 = ±180°
        tf.keras.layers.RandomTranslation(0.05, 0.05, fill_mode="constant"),
        tf.keras.layers.RandomBrightness(0.15, value_range=(0, 255)),
        tf.keras.layers.RandomContrast(0.15),
    ], name="aumento")
    # Transferencia de aprendizaje: MobileNetV2 ya sabe reconocer bordes, texturas y formas (la
    # entrenaron con millones de fotos de ImageNet); solo le falta aprender NUESTRAS clases. Se
    # congela ("trainable = False") para que las pocas fotos del dataset no la desarmen, y encima
    # se entrena una capa chica. alpha=0.35: la versión más liviana, de sobra para 10 clases.
    base = tf.keras.applications.MobileNetV2(input_shape=(LADO, LADO, 3), include_top=False,
                                             weights="imagenet", alpha=0.35)
    base.trainable = False
    entrada = tf.keras.Input((LADO, LADO, 3))
    x = aumento(entrada)
    # preprocess_input lleva los píxeles de 0-255 a -1..1, la escala con la que se preentrenó.
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
    x = base(x, training=False)
    # Promedio de cada mapa de características: de 3x3x1280 a un vector de 1280 números.
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    # Dropout: apaga al azar el 30 % de esos números al entrenar, para que no memorice las fotos.
    x = tf.keras.layers.Dropout(0.3)(x)
    # Softmax: una probabilidad por clase, que suman 1. Esa probabilidad es la "confianza" que la
    # línea compara con 0,85 (config: filtrado.confianza_minima).
    salida = tf.keras.layers.Dense(n_clases, activation="softmax")(x)
    return tf.keras.Model(entrada, salida), base


def entrenar(modelo, base, datos_ent, datos_val):
    import tensorflow as tf

    parar = tf.keras.callbacks.EarlyStopping(patience=6, restore_best_weights=True, monitor="val_accuracy")
    # Fase 1: solo la capa nueva, con un paso de aprendizaje normal.
    modelo.compile(tf.keras.optimizers.Adam(1e-3), "sparse_categorical_crossentropy", ["accuracy"])
    modelo.fit(*datos_ent, validation_data=datos_val, epochs=40, batch_size=16, callbacks=[parar])
    # Fase 2 (ajuste fino): se descongelan las últimas 30 capas de MobileNetV2 con un paso 100 veces
    # más chico, para que se adapten a las caras de las monedas sin olvidar lo que ya sabían.
    base.trainable = True
    for capa in base.layers[:-30]:
        capa.trainable = False
    modelo.compile(tf.keras.optimizers.Adam(1e-5), "sparse_categorical_crossentropy", ["accuracy"])
    modelo.fit(*datos_ent, validation_data=datos_val, epochs=20, batch_size=16, callbacks=[parar])


def informe(modelo, datos_val, nombres):
    """Matriz de confusión, curva de confianza y métricas: el material del informe (sección 12)."""
    import matplotlib
    matplotlib.use("Agg")   # sin ventana: solo archivos
    import matplotlib.pyplot as plt
    import numpy as np

    RESULTADOS.mkdir(parents=True, exist_ok=True)
    x, y = datos_val
    prob = modelo.predict(x, verbose=0)
    pred, conf = prob.argmax(1), prob.max(1)
    n = len(nombres)
    matriz = np.zeros((n, n), dtype=int)
    for real, p in zip(y, pred):
        matriz[real, p] += 1
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.imshow(matriz, cmap="Blues")
    ax.set_xticks(range(n), nombres, rotation=60, ha="right")
    ax.set_yticks(range(n), nombres)
    for i in range(n):
        for j in range(n):
            ax.text(j, i, matriz[i, j], ha="center", va="center", color="white" if matriz[i, j] > matriz.max() / 2 else "black")
    ax.set_xlabel("predicha")
    ax.set_ylabel("real")
    ax.set_title("Matriz de confusión (validación)")
    fig.tight_layout()
    fig.savefig(RESULTADOS / "matriz_confusion.png", dpi=150)

    # Curva de confianza: para cada umbral, qué fracción de las buenas se aceptaría y cuántas
    # equivocadas pasarían. Es lo que justifica (o corrige) el 0,85 de config/parametros.yaml.
    umbrales = np.linspace(0.3, 0.99, 70)
    bien = pred == y
    aceptadas_bien = [(bien & (conf >= u)).sum() / max(1, bien.sum()) for u in umbrales]
    pasan_mal = [((~bien) & (conf >= u)).sum() / max(1, len(y)) for u in umbrales]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(umbrales, aceptadas_bien, label="aciertos que se aceptan")
    ax.plot(umbrales, pasan_mal, label="errores que pasan (sobre el total)")
    ax.axvline(0.85, ls="--", color="gray", label="umbral actual 0,85")
    ax.set_xlabel("confianza mínima")
    ax.legend()
    ax.set_title("Curva de confianza (validación)")
    fig.tight_layout()
    fig.savefig(RESULTADOS / "curva_confianza.png", dpi=150)

    # Umbral sugerido: el más bajo con el que NINGÚN error de validación pasaría.
    errores = conf[~bien]
    sugerido = float(min(0.99, errores.max() + 0.01)) if len(errores) else 0.5
    metricas = {
        "exactitud": float(bien.mean()),
        "por_clase": {nombres[i]: float(matriz[i, i] / max(1, matriz[i].sum())) for i in range(n)},
        "fotos_validacion": int(len(y)),
        "confianza_minima_sugerida": round(sugerido, 2),
    }
    (RESULTADOS / "metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
    return metricas


def main() -> None:
    try:
        import tensorflow  # noqa: F401
    except ImportError:
        sys.exit("Falta TensorFlow: usar el entorno de visión (Python 3.12), ver vision/README.md.")
    imagenes, etiquetas, nombres = cargar_imagenes()
    datos_ent, datos_val = separar(imagenes, etiquetas)
    print(f"{len(nombres)} clases, {len(datos_ent[1])} fotos de entrenamiento y {len(datos_val[1])} de validación")
    modelo, base = construir_modelo(len(nombres))
    entrenar(modelo, base, datos_ent, datos_val)
    MODELOS.mkdir(parents=True, exist_ok=True)
    modelo.save(MODELOS / "monedas.keras")
    (MODELOS / "clases.json").write_text(json.dumps(nombres, ensure_ascii=False), encoding="utf-8")
    metricas = informe(modelo, datos_val, nombres)
    print(json.dumps(metricas, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
