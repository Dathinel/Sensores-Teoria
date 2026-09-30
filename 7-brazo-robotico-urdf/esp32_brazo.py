# Controla el brazo SOLO con el teclado matricial 4x4 — sin
# potenciometro ni ningun otro sensor analogico. Las teclas funcionan
# como un mando de jog (mantener presionado mueve la articulacion
# mientras se sostiene, como un teach pendant real), con el mismo
# diseño de flechas de un teclado numerico:
#
#   8 = joint_1 (base) aumenta       2 = joint_1 (base) disminuye
#   6 = joint_2 (codo) aumenta       4 = joint_2 (codo) disminuye
#   9 = pinza aumenta                7 = pinza disminuye
#   5 = vuelve las 3 articulaciones a 0 (home)
#
# El protocolo por serial no cambia (sigue mandando "J1:..,J2:..,G:..",
# siempre las 3 articulaciones), asi que brazo_pybullet.py no necesita
# tocar nada del lado de la lectura.
#
# Este archivo debe guardarse como main.py en el ESP32. El puerto USB
# queda libre para pyserial en el PC (brazo_pybullet.py) sin necesidad
# de tener Thonny conectado.
#
# Conexion del teclado: directo a 8 GPIO del ESP32 con su cinta de 8
# cables (4 filas R1..R4 y 4 columnas C1..C4), sin ningun modulo en el
# medio. Los mismos pines del tema 8 punto 1 y del taller (tema 9), asi
# el mismo montaje sirve para los tres:
#   - Filas    R1..R4 -> GPIO14, GPIO27, GPIO26, GPIO25 (salidas)
#   - Columnas C1..C4 -> GPIO33, GPIO32, GPIO18, GPIO19 (entradas con
#     pull-up interno del ESP32)

from machine import Pin
import time

# mismos limites definidos en los <limit> de brazo.urdf, en radianes para
# las articulaciones revolute (joint_1, joint_2) y en metros para la
# extension prismatica de la pinza (joint_gripper)
LIM_J1 = (-2.5, 2.5)
LIM_J2 = (-2.0, 2.0)
LIM_G = (0.0, 0.15)

PASO_J1 = 0.05  # radianes por tick (~100ms) mientras se mantiene la tecla
PASO_J2 = 0.05
PASO_G = 0.005

# ------------------------------------------------------------------
# Teclado matricial 4x4 directo a GPIO
# ------------------------------------------------------------------
ROW_PINS = [14, 27, 26, 25]   # R1..R4 (filas: 1 2 3 A / 4 5 6 B / 7 8 9 C / * 0 # D)
COL_PINS = [33, 32, 18, 19]   # C1..C4 (columnas: 1 4 7 * / 2 5 8 0 / 3 6 9 # / A B C D)

MAPA_TECLAS = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"],
]

# Filas como salidas, arrancando en alto (value=1): en reposo ninguna
# fila "tira" hacia abajo, asi que ninguna columna puede leer 0 aunque
# haya una tecla apretada.
filas = [Pin(p, Pin.OUT, value=1) for p in ROW_PINS]

# Columnas como entradas con PULL_UP interno: una tecla es solo un
# contacto que une una fila con una columna, no pone ningun voltaje por
# si misma. Sin pull-up, una columna sin tecla apretada quedaria
# "flotando" y leeria ruido; con el pull-up queda en 1 y solo baja a 0
# cuando una tecla la une con la fila que esta en bajo ("activa en bajo").
columnas = [Pin(p, Pin.IN, Pin.PULL_UP) for p in COL_PINS]


def leer_tecla():
    # Barrido de filas: se baja a 0 UNA fila a la vez (las demas quedan
    # en 1). Si en ese momento alguna columna se lee en 0, es porque hay
    # una tecla presionada justo en el cruce de esa fila con esa columna.
    # Si se bajaran todas las filas juntas se sabria la columna pero no
    # cual de las 4 filas la bajo.
    for i, fila in enumerate(filas):
        fila.value(0)
        # unos microsegundos para que la columna alcance a bajar de
        # verdad (el pull-up interno es una resistencia alta y los cables
        # tienen algo de capacidad); si se lee enseguida la tecla se pierde
        time.sleep_us(10)
        for j, col in enumerate(columnas):
            if col.value() == 0:
                # se vuelve a subir la fila ANTES de salir: asi nunca
                # quedan dos filas en bajo en el siguiente barrido
                fila.value(1)
                return MAPA_TECLAS[i][j]
        fila.value(1)
    return None


def limitar(valor, limite):
    minimo, maximo = limite
    return max(minimo, min(maximo, valor))


# ------------------------------------------------------------------
# Programa principal
# ------------------------------------------------------------------
j1, j2, g = 0.0, 0.0, 0.0

while True:
    # Con el teclado directo a GPIO no hay nada que "no conteste" (a
    # diferencia de un dispositivo I2C): con un cable suelto la tecla
    # simplemente no se detecta, y el ESP32 sigue mandando la ultima
    # posicion.
    tecla = leer_tecla()

    if tecla == "8":
        j1 = limitar(j1 + PASO_J1, LIM_J1)
    elif tecla == "2":
        j1 = limitar(j1 - PASO_J1, LIM_J1)
    elif tecla == "6":
        j2 = limitar(j2 + PASO_J2, LIM_J2)
    elif tecla == "4":
        j2 = limitar(j2 - PASO_J2, LIM_J2)
    elif tecla == "9":
        g = limitar(g + PASO_G, LIM_G)
    elif tecla == "7":
        g = limitar(g - PASO_G, LIM_G)
    elif tecla == "5":
        j1, j2, g = 0.0, 0.0, 0.0

    # Se mandan SIEMPRE las 3 articulaciones (no solo la que cambio): asi
    # cada linea es autosuficiente y si el PC se pierde una, la siguiente
    # ya trae la posicion completa. 3 decimales = milimetros/milirradianes,
    # mas que suficiente para un paso de 0.005.
    print("J1:{:.3f},J2:{:.3f},G:{:.3f}".format(j1, j2, g))
    # 100 ms por vuelta = 10 pasos por segundo mientras se sostiene una
    # tecla: con PASO_J1 = 0.05 rad son ~29 grados/s, rapido pero controlable.
    time.sleep(0.1)
