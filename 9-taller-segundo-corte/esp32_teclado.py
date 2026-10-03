# Firmware UNICO para todo el taller: lee el teclado matricial 4x4 por GPIO
# directo (8 pines del ESP32, sin modulo I2C) y manda por serial, sin parar,
# la tecla que este presionada en ese instante:
#
#   TECLA:8      -> se esta sosteniendo la tecla "8"
#   TECLA:-      -> ninguna tecla presionada
#
# Este archivo NO sabe nada de drones, de Baxter ni de Atlas: es el mismo
# programa para las tres simulaciones del taller (drones_pybullet.py,
# brazo_pybullet.py y atlas_pybullet.py), y cada una interpreta las teclas a
# su manera. Eso es lo que permite usar un solo teclado fisico con "multiples
# configuraciones": la configuracion (que hace cada tecla) vive del lado del
# PC, no en el ESP32.
#
# Por que manda la tecla CADA 50 ms y no solo cuando cambia: asi el PC sabe
# en todo momento si la tecla sigue sostenida (para el "jog": mover mientras
# se mantiene presionada) y, si se pierde una linea, la siguiente lo corrige
# sola. Las acciones de "un solo golpe" (una demo, cambiar de brazo, prender el
# asistente de Atlas) las detecta el PC por el FLANCO: cuando la tecla recibida
# es distinta de la anterior.
#
# Este archivo debe guardarse como main.py en el ESP32. El puerto USB queda
# libre para pyserial en el PC sin necesidad de tener Thonny conectado.
from machine import Pin
import time

# Conexiones segun la tabla del montaje (las mismas de los temas 7 y 8):
# Filas: GPIO 14, 27, 26, 25
PINES_FILAS = [14, 27, 26, 25]
# Columnas: GPIO 33, 32, 18, 19
PINES_COLUMNAS = [33, 32, 18, 19]

# Filas como SALIDAS, todas en alto (1) mientras no se esten escaneando.
filas = []
for pin in PINES_FILAS:
    p = Pin(pin, Pin.OUT)
    p.value(1)
    filas.append(p)

# Columnas como ENTRADAS con la resistencia de subida (pull-up) interna del
# ESP32: si nada las toca leen 1; si una tecla une esa columna con una fila
# puesta en 0, la columna baja a 0. Por eso no hacen falta resistencias externas.
columnas = []
for pin in PINES_COLUMNAS:
    p = Pin(pin, Pin.IN, Pin.PULL_UP)
    columnas.append(p)

# Que tecla hay en cada cruce fila/columna (igual a la serigrafia del teclado).
MAPA_TECLAS = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"],
]


def leer_tecla():
    """Escaneo de un teclado matricial con pines GPIO puros.

    Se 'enciende' (pone en 0) UNA fila a la vez y se miran las 4 columnas:
    la columna que lea 0 es la que esta unida a esa fila por la tecla
    presionada. Solo una fila esta en 0 a la vez, asi que se sabe exactamente
    que cruce (tecla) es. Devuelve la primera tecla encontrada o None."""
    for i, fila in enumerate(filas):
        # Activar la fila actual poniendola a 0 (LOW)
        fila.value(0)

        # Leer todas las columnas
        for j, col in enumerate(columnas):
            if col.value() == 0:  # la columna bajo a 0: hay una tecla uniendola con esta fila
                fila.value(1)     # restaurar la fila a 1 antes de salir
                return MAPA_TECLAS[i][j]

        # Desactivar la fila actual devolviendola a 1 (HIGH)
        fila.value(1)

    return None


# Programa principal: manda la tecla actual cada ~50 ms (20 veces por segundo,
# suficiente para que el jog se sienta fluido y sin saturar el puerto USB).
while True:
    tecla = leer_tecla()
    print("TECLA:{}".format(tecla if tecla is not None else "-"))
    time.sleep_ms(50)
