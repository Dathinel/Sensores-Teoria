# Controla el brazo SOLO con el teclado matricial 4x4 (I2C) — sin
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
# Conexion I2C del teclado (SDA=GPIO21, SCL=GPIO22): expansor PCF8574,
# direccion 0x20 (todos los pines de direccion a GND) — igual que en
# esp32_teclado_lcd.py del tema 8.

from machine import I2C, Pin
import time

I2C_SDA = 21
I2C_SCL = 22
DIR_TECLADO = 0x20

i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=100000)

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
# Teclado matricial 4x4 por I2C (igual que en esp32_teclado_lcd.py del
# tema 8: P4-P7 = filas, salidas; P0-P3 = columnas, entradas con
# pull-up del propio PCF8574).
# ------------------------------------------------------------------
MAPA_TECLAS = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"],
]


def leer_tecla():
    for fila in range(4):
        filas = 0x0F & ~(1 << fila)
        byte_salida = (filas << 4) | 0x0F
        i2c.writeto(DIR_TECLADO, bytes([byte_salida]))
        byte_entrada = i2c.readfrom(DIR_TECLADO, 1)[0]
        columnas = byte_entrada & 0x0F
        if columnas != 0x0F:
            for col in range(4):
                if not (columnas & (1 << col)):
                    return MAPA_TECLAS[fila][col]
    return None


def limitar(valor, limite):
    minimo, maximo = limite
    return max(minimo, min(maximo, valor))


# ------------------------------------------------------------------
# Programa principal
# ------------------------------------------------------------------
j1, j2, g = 0.0, 0.0, 0.0

while True:
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

    print("J1:{:.3f},J2:{:.3f},G:{:.3f}".format(j1, j2, g))
    time.sleep(0.1)
