# Lee un teclado matricial 4x4 conectado por un expansor I2C PCF8574,
# muestra el digito presionado en una pantalla LCD 16x2 (tambien por I2C,
# con su propio backpack PCF8574) y le manda el digito al PC por UART
# para que brazo_dibuja.py lo dibuje con el brazo robotico.
#
# Este archivo debe guardarse como main.py en el ESP32. El puerto USB
# queda libre para pyserial en el PC sin necesidad de tener Thonny
# conectado.
#
# Conexion I2C (SDA=GPIO21, SCL=GPIO22, ambos modulos en el mismo bus):
#   - Expansor del teclado: direccion 0x20 (todos los pines de
#     direccion del PCF8574 a GND)
#   - Backpack de la LCD:   direccion 0x27 (direccion de fabrica mas
#     comun en los backpacks LCD1602 con PCF8574)

from machine import I2C, Pin
import time

I2C_SDA = 21
I2C_SCL = 22
DIR_TECLADO = 0x20
DIR_LCD = 0x27

i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=100000)


# ------------------------------------------------------------------
# LCD 16x2 por I2C (backpack PCF8574 estandar, mapeo de bits:
# P0=RS, P1=RW, P2=E, P3=Backlight, P4-P7=D4-D7)
# ------------------------------------------------------------------
RS = 0x01
E = 0x04
BACKLIGHT = 0x08


def _lcd_pulso(byte):
    i2c.writeto(DIR_LCD, bytes([byte | E]))
    time.sleep_us(1)
    i2c.writeto(DIR_LCD, bytes([byte & ~E]))
    time.sleep_us(50)


def _lcd_nibble(nibble, rs):
    byte = (nibble << 4) | BACKLIGHT | (RS if rs else 0)
    i2c.writeto(DIR_LCD, bytes([byte]))
    _lcd_pulso(byte)


def lcd_comando(cmd):
    _lcd_nibble(cmd >> 4, rs=False)
    _lcd_nibble(cmd & 0x0F, rs=False)


def lcd_dato(valor):
    _lcd_nibble(valor >> 4, rs=True)
    _lcd_nibble(valor & 0x0F, rs=True)


def lcd_init():
    time.sleep_ms(50)
    for _ in range(3):
        _lcd_nibble(0x03, rs=False)
        time.sleep_ms(5)
    _lcd_nibble(0x02, rs=False)   # entra a modo 4 bits
    lcd_comando(0x28)             # 4 bits, 2 lineas, fuente 5x8
    lcd_comando(0x0C)             # display on, cursor off, blink off
    lcd_comando(0x06)             # entry mode: incrementa, sin desplazar
    lcd_comando(0x01)             # clear display
    time.sleep_ms(2)


def lcd_texto(fila, texto):
    direccion_fila = 0x80 if fila == 0 else 0xC0
    lcd_comando(direccion_fila)
    for caracter in texto.ljust(16)[:16]:
        lcd_dato(ord(caracter))


# ------------------------------------------------------------------
# Teclado matricial 4x4 por I2C (expansor PCF8574: P4-P7 = filas,
# salidas; P0-P3 = columnas, entradas con pull-up del propio PCF8574)
# ------------------------------------------------------------------
MAPA_TECLAS = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"],
]


def leer_tecla():
    for fila in range(4):
        # esa fila en bajo, las demas en alto, columnas en alto (entrada)
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
# Programa principal
# ------------------------------------------------------------------
lcd_init()
lcd_texto(0, "Marca un digito")
lcd_texto(1, "para dibujar")

tecla_anterior = None

while True:
    tecla = leer_tecla()
    if tecla is not None and tecla != tecla_anterior and tecla.isdigit():
        lcd_texto(0, "Dibujando:")
        lcd_texto(1, tecla)
        print("DIGIT:{}".format(tecla))
    tecla_anterior = tecla
    time.sleep_ms(30)  # anti-rebote simple
