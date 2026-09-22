# Firmware UNICO para todo el taller: lee el teclado matricial 4x4 por I2C
# (el mismo modulo PCF8574 que ya se usa en los temas 7 y 8) y manda por
# serial, sin parar, la tecla que este presionada en ese instante:
#
#   TECLA:8      -> se esta sosteniendo la tecla "8"
#   TECLA:-      -> ninguna tecla presionada
#
# Este archivo NO sabe nada de drones ni de brazos: es el mismo binario
# para las dos simulaciones del taller (drones_pybullet.py y
# brazo_pybullet.py), cada una interpreta las teclas a su manera. Es lo
# que permite usar un solo teclado fisico con "multiples configuraciones"
# -- la configuracion (que hace cada tecla) vive del lado del PC, no en
# el ESP32.
#
# Este archivo debe guardarse como main.py en el ESP32. El puerto USB
# queda libre para pyserial en el PC sin necesidad de tener Thonny
# conectado.
#
# Conexion I2C del teclado (SDA=GPIO21, SCL=GPIO22): expansor PCF8574,
# direccion 0x20 (todos los pines de direccion a GND) -- igual que en
# esp32_brazo.py (tema 7) y esp32_teclado_lcd.py (tema 8).

from machine import I2C, Pin
import time

I2C_SDA = 21
I2C_SCL = 22
DIR_TECLADO = 0x20

i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=100000)

# ------------------------------------------------------------------
# Teclado matricial 4x4 por I2C (P4-P7 = filas, salidas; P0-P3 =
# columnas, entradas con pull-up del propio PCF8574) -- mismo escaneo
# que en los temas 7 y 8.
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


# ------------------------------------------------------------------
# Programa principal: manda la tecla actual cada ~50ms, sin importar
# que simulacion la vaya a leer del otro lado.
# ------------------------------------------------------------------
while True:
    tecla = leer_tecla()
    print("TECLA:{}".format(tecla if tecla is not None else "-"))
    time.sleep_ms(50)
