"""Capturas PNG de los modelos reales del taller (Baxter y Atlas), sin
ventana: PyBullet en modo DIRECT + getCameraImage con el renderizador por
software (ER_TINY_RENDERER), que funciona en cualquier PC aunque no haya GPU.

Uso (desde la carpeta del taller):

    entorno\\Scripts\\python capturar_modelos.py            # las dos
    entorno\\Scripts\\python capturar_modelos.py --baxter   # solo Baxter
    entorno\\Scripts\\python capturar_modelos.py --atlas    # solo Atlas

Genera:
    punto-b-brazo-tipo-baxter/img/baxter-home.png
    punto-b-brazo-tipo-baxter/img/baxter-agarra-cubo.png
    punto-c-atlas/img/atlas-de-pie-asistente.png
    punto-c-atlas/img/atlas-caminando.png
    punto-c-atlas/img/atlas-sin-asistente.png

Por que un proceso por robot: los modulos brazo_pybullet y atlas_pybullet
usan la conexion POR DEFECTO de PyBullet (p.connect sin guardar el id en
cada llamada), y solo puede haber una por proceso. Sin argumentos, este
script se relanza a si mismo dos veces con subprocess (--baxter y --atlas),
cada una en su propio interprete de Python.

Los PNG se escriben a mano (zlib + struct, sin Pillow): el formato es una
firma de 8 bytes y tres bloques (IHDR con el tamano, IDAT con los pixeles
comprimidos, IEND), cada uno con su largo y su CRC32.
"""

import math
import struct
import subprocess
import sys
import zlib
from pathlib import Path

sys.dont_write_bytecode = True   # no dejar __pycache__ al importar los modulos del taller

import numpy as np
import pybullet as p

TALLER = Path(__file__).resolve().parent
CARPETA_BAXTER = TALLER / "punto-b-brazo-tipo-baxter"
CARPETA_ATLAS = TALLER / "punto-c-atlas"

ANCHO, ALTO = 960, 640


# ======================================================================
# PNG a mano
# ======================================================================
def guardar_png(ruta, rgb):
    """Guarda un arreglo (alto, ancho, 3) uint8 como PNG RGB de 8 bits."""
    alto, ancho, _ = rgb.shape

    def bloque(tipo, datos):
        # largo (4 bytes) + tipo + datos + CRC32 de (tipo + datos)
        return (struct.pack(">I", len(datos)) + tipo + datos
                + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))

    # IHDR: ancho, alto, 8 bits por canal, tipo de color 2 (RGB),
    # compresion 0, filtro 0, sin entrelazado
    ihdr = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    # Cada fila lleva delante un byte con el filtro usado (0 = ninguno)
    filas = np.hstack([np.zeros((alto, 1), np.uint8), rgb.reshape(alto, ancho * 3)])
    idat = zlib.compress(filas.tobytes(), 9)
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", ihdr) + bloque(b"IDAT", idat) + bloque(b"IEND", b""))
    nombre = ruta.relative_to(TALLER) if ruta.is_relative_to(TALLER) else ruta
    print(f"  {nombre}  ({ruta.stat().st_size // 1024} KB)")


def capturar(ruta, objetivo, distancia, yaw, pitch, luz=(-0.6, -0.4, 1.0)):
    """Saca una foto con una camara orbital (las mismas 4 cifras que
    resetDebugVisualizerCamera de la ventana) y la guarda en `ruta`."""
    vista = p.computeViewMatrixFromYawPitchRoll(cameraTargetPosition=objetivo, distance=distancia,
                                                yaw=yaw, pitch=pitch, roll=0, upAxisIndex=2)
    proyeccion = p.computeProjectionMatrixFOV(fov=50, aspect=ANCHO / ALTO, nearVal=0.05, farVal=30)
    _, _, rgba, _, _ = p.getCameraImage(
        ANCHO, ALTO, vista, proyeccion,
        renderer=p.ER_TINY_RENDERER,
        shadow=1,                       # sombras proyectadas sobre el piso / la mesa
        lightDirection=list(luz),       # de donde viene la luz (desde arriba, un poco de frente)
        lightColor=[1.0, 1.0, 1.0],
        lightDistance=6,
        lightAmbientCoeff=0.55,         # luz ambiente alta: sin ella las caras en sombra quedan negras
        lightDiffuseCoeff=0.55,
        lightSpecularCoeff=0.08)
    imagen = np.reshape(np.asarray(rgba, np.uint8), (ALTO, ANCHO, 4))[:, :, :3]
    guardar_png(ruta, np.ascontiguousarray(imagen))


# ======================================================================
# Baxter (punto b)
# ======================================================================
def capturas_baxter():
    sys.path.insert(0, str(CARPETA_BAXTER))
    import brazo_pybullet as B

    print("Baxter:")
    estado = B.crear_mundo(p.DIRECT)        # Baxter en home, cubo en el origen (azul)
    img = CARPETA_BAXTER / "img"
    # Vista general: la misma camara que abre la ventana del script
    capturar(img / "baxter-home.png", [0.30, 0, -0.15], 2.9, 135, -30)

    # Coger el cubo con el brazo izquierdo (el activo al arrancar), con los
    # mismos pasos que la demo D: encima, bajar, cerrar, "soldar" y subir.
    brazo = estado.activo
    x, y, _ = p.getBasePositionAndOrientation(estado.cubo)[0]
    B.mover_pinza(estado, brazo, abierta=True)
    B.mover_a(estado, brazo, (x, y, B.Z_VIAJE), 360)
    B.mover_a(estado, brazo, (x, y, B.Z_AGARRE + 0.05), 180)
    B.mover_a(estado, brazo, (x, y, B.Z_AGARRE), 180)
    B.mover_pinza(estado, brazo, abierta=False)
    B.avanzar(estado, 120)
    agarro = B.intentar_agarrar(estado, brazo)
    B.mover_a(estado, brazo, (x, y, B.Z_VIAJE), 240)
    cubo = p.getBasePositionAndOrientation(estado.cubo)[0]
    print(f"  agarro: {agarro}, cubo en z = {cubo[2]:.3f} (mesa en {B.Z_MESA})")
    # Camara mas cerca, mirando el brazo izquierdo y la mesa
    capturar(img / "baxter-agarra-cubo.png", [cubo[0], cubo[1], cubo[2] + 0.12], 0.85, 150, -14)
    p.disconnect()


# ======================================================================
# Atlas (punto c)
# ======================================================================
def foto_atlas(A, e, ruta):
    """Camara de 3/4 de frente apuntando a la pelvis, con Atlas entero."""
    x, y, z = A.leer_estado(e)["pos"]
    # Atlas mira a +x: yaw 50 deja la camara por delante y a su izquierda
    capturar(ruta, [x, y, max(z, 0.3) - 0.15], 3.0, 50, -12, luz=(0.6, 0.5, 1.0))


def capturas_atlas():
    sys.path.insert(0, str(CARPETA_ATLAS))
    import atlas_pybullet as A

    print("Atlas:")
    img = CARPETA_ATLAS / "img"
    e = A.crear_mundo(p.DIRECT)        # de pie, asentado, asistente ON
    A.simular(e, 2.0)                  # Escena 1: de pie con asistente
    foto_atlas(A, e, img / "atlas-de-pie-asistente.png")
    A.simular(e, 6.0, "8")             # Escena 2: caminando (termina en x~0.71)
    print(f"  caminando: x = {A.leer_estado(e)['pos'][0]:.2f} m")
    foto_atlas(A, e, img / "atlas-caminando.png")
    A.reiniciar_todo(e)
    A.asistente(e, False)
    A.simular(e, 2.4, "4")             # Escena 3: sin asistente, en plena caida
    est = A.leer_estado(e)
    print(f"  sin asistente: inclinacion {est['inclinacion']:.2f} rad, caido {est['caido']}")
    foto_atlas(A, e, img / "atlas-sin-asistente.png")
    p.disconnect()


# ======================================================================
if __name__ == "__main__":
    if "--baxter" in sys.argv:
        capturas_baxter()
    elif "--atlas" in sys.argv:
        capturas_atlas()
    else:
        # Proceso principal: un subproceso (un Python nuevo) por robot.
        for opcion in ("--baxter", "--atlas"):
            subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), opcion], check=True)
