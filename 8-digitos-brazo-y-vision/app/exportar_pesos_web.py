# Exporta los pesos de la CNN (punto-2-reconocimiento-oled-spi/modelo_mnist_cnn.h5) a
# app/cnn-pesos.bin, para que la app del tema 8 corra LA MISMA red en el navegador (cnn.js),
# sin instalar TensorFlow. Solo hace falta volver a correrlo si se reentrena el modelo:
#
#   cd 8-digitos-brazo-y-vision
#   punto-2-reconocimiento-oled-spi\entorno\Scripts\python app\exportar_pesos_web.py
#
# Formato (todo little-endian), capa por capa en este orden: conv2d, conv2d_1, dense, dense_1.
# Por capa: los pesos en int8 (cuantizados por neurona de salida: peso ~= int8 * escala),
# despues las escalas (float32, una por salida) y los sesgos (float32, uno por salida).
# Orden de los pesos dentro de cada salida:
#   conv: [salida][fila 3][columna 3][canal de entrada]   dense: [salida][entrada]
# Cuantizar a int8 deja el archivo en ~220 KB (en float32 serian ~880 KB) y no cambia la
# clase que gana: el script lo comprueba al final contra TensorFlow con imágenes al azar.
import os
import sys

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import numpy as np
import h5py

AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO = os.path.join(AQUI, "..", "punto-2-reconocimiento-oled-spi", "modelo_mnist_cnn.h5")
SALIDA = os.path.join(AQUI, "cnn-pesos.bin")

capas = ["conv2d", "conv2d_1", "dense", "dense_1"]
with h5py.File(MODELO, "r") as f:
    pesos = {c: (f[f"model_weights/{c}/sequential/{c}/kernel"][()], f[f"model_weights/{c}/sequential/{c}/bias"][()]) for c in capas}

partes = []
for c in capas:
    k, b = pesos[c]
    if k.ndim == 4:                       # (3, 3, entrada, salida) -> (salida, 3, 3, entrada)
        k = np.transpose(k, (3, 0, 1, 2))
    else:                                 # (entrada, salida) -> (salida, entrada)
        k = k.T
    k = k.reshape(k.shape[0], -1).astype(np.float32)
    escala = np.abs(k).max(axis=1) / 127.0
    escala[escala == 0] = 1.0
    q = np.clip(np.round(k / escala[:, None]), -127, 127).astype(np.int8)
    partes += [q.tobytes(), escala.astype("<f4").tobytes(), b.astype("<f4").tobytes()]
    print(f"{c}: {k.shape[0]} salidas x {k.shape[1]} entradas")

with open(SALIDA, "wb") as f:
    f.write(b"".join(partes))
print("Escrito", SALIDA, os.path.getsize(SALIDA), "bytes")

# Comprobación contra TensorFlow (si está instalado en el entorno que corre esto)
if "--sin-comprobar" in sys.argv:
    sys.exit()
import tensorflow as tf
modelo = tf.keras.models.load_model(MODELO)
x = np.random.rand(200, 28, 28, 1).astype(np.float32) ** 3
# misma cuenta que cnn.js, en numpy, con los pesos cuantizados
def adelante(img):
    a = img[:, :, 0]
    datos = open(SALIDA, "rb").read(); pos = 0
    def leer(n_sal, n_ent):
        nonlocal pos
        w = np.frombuffer(datos, np.int8, n_sal * n_ent, pos).reshape(n_sal, n_ent).astype(np.float32); pos += n_sal * n_ent
        e = np.frombuffer(datos, "<f4", n_sal, pos); pos += 4 * n_sal
        b = np.frombuffer(datos, "<f4", n_sal, pos); pos += 4 * n_sal
        return w * e[:, None], b
    def conv(x, w, b):            # x (H, W, C), w (S, 9*C)
        H, W, C = x.shape
        parches = np.stack([x[i:i + H - 2, j:j + W - 2, :] for i in range(3) for j in range(3)], axis=2)
        return np.maximum(parches.reshape(H - 2, W - 2, -1) @ w.T + b, 0)
    def pool(x):
        H, W, C = x.shape; H2, W2 = H // 2, W // 2
        return x[:H2 * 2, :W2 * 2].reshape(H2, 2, W2, 2, C).max(axis=(1, 3))
    w, b = leer(32, 9); y = pool(conv(a[:, :, None], w, b))
    w, b = leer(64, 288); y = pool(conv(y, w, b))
    w, b = leer(128, 1600); y = np.maximum(y.ravel() @ w.T + b, 0)
    w, b = leer(10, 128); z = y @ w.T + b
    z = np.exp(z - z.max()); return z / z.sum()
tf_p = modelo(x, training=False).numpy()
mio = np.stack([adelante(i) for i in x])
print("misma clase ganadora:", int((tf_p.argmax(1) == mio.argmax(1)).sum()), "de", len(x),
      "| diferencia máxima de probabilidad:", float(np.abs(tf_p - mio).max()))
