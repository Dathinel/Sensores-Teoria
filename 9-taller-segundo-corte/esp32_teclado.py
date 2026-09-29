# Firmware UNICO para todo el taller: lee el teclado matricial 4x4 por I2C
# (el mismo modulo PCF8574 que ya se usa en los temas 7 y 8) y manda por
# serial, sin parar, la tecla que este presionada en ese instante:
#
#   TECLA:8      -> se esta sosteniendo la tecla "8"
#   TECLA:-      -> ninguna tecla presionada
#
# Este archivo NO sabe nada de drones, brazos ni patas: es el mismo
# programa para las tres simulaciones del taller (drones_pybullet.py,
# brazo_pybullet.py y laikago_pybullet.py), cada una interpreta las
# teclas a su manera. Es lo
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
# esp32_brazo.py (tema 7). (En el tema 8 el teclado va directo a 8 GPIO.)

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
    """Escaneo clasico de un teclado matricial: se "enciende" (pone en 0)
    UNA fila a la vez y se miran las 4 columnas. Si una tecla de esa fila
    esta presionada, conecta su fila con su columna y esa columna tambien
    se lee en 0; las demas quedan en 1 por el pull-up. Fila activa +
    columna en 0 = tecla exacta. Devuelve la primera encontrada o None."""
    for fila in range(4):
        # nibble alto (P4-P7) = filas: todas en 1 salvo la que se escanea.
        # Ej. fila 1 -> 0b1101 -> P5 en 0.
        filas = 0x0F & ~(1 << fila)
        # nibble bajo (P0-P3) = columnas: se ESCRIBEN en 1 porque el
        # PCF8574 no tiene registro de direccion -- un pin "en 1" queda
        # como entrada con pull-up debil, que es lo que permite leerlo
        byte_salida = (filas << 4) | 0x0F
        i2c.writeto(DIR_TECLADO, bytes([byte_salida]))
        byte_entrada = i2c.readfrom(DIR_TECLADO, 1)[0]
        columnas = byte_entrada & 0x0F   # solo interesan P0-P3
        if columnas != 0x0F:             # alguna columna bajo a 0 -> hay tecla en esta fila
            for col in range(4):
                if not (columnas & (1 << col)):
                    return MAPA_TECLAS[fila][col]
    return None


# ------------------------------------------------------------------
# Programa principal: manda la tecla actual cada ~50ms, sin importar
# que simulacion la vaya a leer del otro lado. Se manda SIEMPRE, aunque
# no cambie (y "TECLA:-" cuando no hay nada): asi "sostener" una tecla
# llega al PC como una repeticion continua (20 por segundo), que es lo
# que usa el jog, y el PC puede detectar cuando se suelta. 50 ms es
# rapido para que el jog se sienta continuo y lento para no saturar el
# puerto (~10 bytes por linea -> ~200 bytes/s de 11.500 posibles).
# ------------------------------------------------------------------
while True:
    tecla = leer_tecla()
    print("TECLA:{}".format(tecla if tecla is not None else "-"))
    time.sleep_ms(50)
