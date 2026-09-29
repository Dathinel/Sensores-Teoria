# Lee un teclado matricial 4x4 conectado directo a 8 GPIOs del ESP32,
# muestra el digito presionado en una pantalla LCD 16x2 (por I2C, con su
# backpack PCF8574) y le manda el digito al PC por UART para que
# brazo_dibuja.py lo dibuje con el brazo robotico.
#
# Este archivo debe guardarse como main.py en el ESP32. El puerto USB
# queda libre para pyserial en el PC sin necesidad de tener Thonny
# conectado.
#
# Conexion del teclado (8 cables: 4 filas R1..R4 y 4 columnas C1..C4):
#   - Filas    R1..R4 -> GPIO14, GPIO27, GPIO26, GPIO25 (salidas)
#   - Columnas C1..C4 -> GPIO33, GPIO32, GPIO18, GPIO19 (entradas con
#     pull-up interno del ESP32)
#
# Conexion de la LCD por I2C (SDA=GPIO21, SCL=GPIO22):
#   - Backpack de la LCD: direccion 0x27 (direccion de fabrica mas
#     comun en los backpacks LCD1602 con PCF8574)

from machine import I2C, Pin
import time

I2C_SDA = 21
I2C_SCL = 22
DIR_LCD = 0x27

# 100 kHz es la velocidad "estandar" de I2C: la que soporta cualquier
# PCF8574 sin problemas (algunos modulos baratos fallan a 400 kHz).
i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=100000)

# Diagnostico al arrancar: i2c.scan() devuelve las direcciones de todos
# los dispositivos que contestan en el bus. En este montaje el unico
# dispositivo I2C es la LCD (el teclado va por GPIO, no por I2C): si
# falta 0x27, el problema es de cableado o de direccion (no del codigo),
# y se ve de una vez en la consola de Thonny. brazo_dibuja.py ignora
# esta linea porque no empieza con "DIGIT:".
encontrados = i2c.scan()
print("I2C encontrados:", [hex(d) for d in encontrados])
if DIR_LCD not in encontrados:
    print("OJO: no responde la LCD en {}".format(hex(DIR_LCD)))


# ------------------------------------------------------------------
# LCD 16x2 por I2C (backpack PCF8574 estandar, mapeo de bits:
# P0=RS, P1=RW, P2=E, P3=Backlight, P4-P7=D4-D7)
# ------------------------------------------------------------------
RS = 0x01
E = 0x04
BACKLIGHT = 0x08


# La LCD tiene un bus de 8 bits, pero el PCF8574 solo tiene 8 pines en
# total y 4 ya se usan para RS/RW/E/luz: por eso la LCD se maneja en
# "modo 4 bits", mandando cada byte en dos mitades (nibbles). La LCD lee
# el dato en el flanco de BAJADA del pin E: por eso cada nibble se
# escribe con E en alto y despues con E en bajo (_lcd_pulso).
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
    # Secuencia de arranque del controlador HD44780 (hoja de datos):
    # al encender no se sabe si quedo en modo 8 o 4 bits, asi que se le
    # manda 0x03 ("modo 8 bits") tres veces para dejarlo en un estado
    # conocido, y recien ahi 0x02 para pasarlo a 4 bits.
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
    # Se rellena con espacios hasta 16 (el ancho de la LCD) para borrar
    # lo que hubiera antes en esa fila. Se hace sumando espacios y
    # cortando, porque MicroPython NO tiene str.ljust() (Python normal
    # si): usarlo tiraba AttributeError y el programa moria antes de
    # llegar al teclado.
    for caracter in (texto + " " * 16)[:16]:
        lcd_dato(ord(caracter))


# La LCD es opcional para que el teclado funcione: si no contesta por
# I2C (direccion distinta, cable flojo, sin alimentacion), cada escritura
# lanza OSError. Sin este try, ese error mataba el programa ANTES de
# llegar al bucle del teclado y no salia nada por el USB, aunque el
# teclado estuviera perfecto. Asi, si la LCD falla se avisa una vez y el
# teclado sigue mandando los digitos al PC igual.
lcd_ok = True


def lcd_mostrar(linea0, linea1):
    global lcd_ok
    if not lcd_ok:
        return
    try:
        lcd_texto(0, linea0)
        lcd_texto(1, linea1)
    except Exception as error:
        lcd_ok = False
        print("OJO: la LCD no responde ({}); sigo sin LCD".format(error))


# ------------------------------------------------------------------
# Teclado matricial 4x4 directo a GPIO (filas = salidas, columnas =
# entradas con pull-up interno)
# ------------------------------------------------------------------
ROW_PINS = [14, 27, 26, 25]   # R1..R4
COL_PINS = [33, 32, 18, 19]   # C1..C4

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
# "flotando" (ni 0 ni 1 definido, lee ruido al azar). La resistencia de
# pull-up interna del ESP32 la mantiene en 1 por defecto, y solo baja a
# 0 cuando una tecla la une con una fila que esta en bajo. Por eso la
# logica es "activa en bajo": 0 = apretada.
columnas = [Pin(p, Pin.IN, Pin.PULL_UP) for p in COL_PINS]


# Barrido de la matriz: las 16 teclas son cruces entre 4 filas y 4
# columnas, pero solo hay 8 cables. Si se bajaran todas las filas a la
# vez, al leer una columna en 0 se sabria la columna pero no cual de
# las 4 filas la bajo. Por eso se baja UNA fila a la vez: si en ese
# momento una columna lee 0, la tecla es justo el cruce de esa fila con
# esa columna (fila en bajo + columna en bajo = la tecla exacta).
#
# El sleep_us(10) despues de bajar la fila: el pin tarda un poco en
# pasar de 1 a 0 de verdad en la columna (capacidad de los cables y del
# teclado contra el pull-up interno, que es una resistencia alta de
# decenas de kOhm y carga/descarga despacio). Si se lee enseguida, la
# columna todavia puede verse en 1 y la tecla se pierde; unos pocos
# microsegundos alcanzan y no frenan el barrido.
#
# Antes de pasar a la siguiente fila (y antes de devolver la tecla) se
# vuelve a subir la fila: asi nunca quedan dos filas en bajo al mismo
# tiempo, y el siguiente barrido arranca con todo en reposo.
def leer_tecla():
    for fila in range(4):
        filas[fila].value(0)
        time.sleep_us(10)
        for col in range(4):
            if columnas[col].value() == 0:
                filas[fila].value(1)
                return MAPA_TECLAS[fila][col]
        filas[fila].value(1)
    return None


# ------------------------------------------------------------------
# Programa principal
# ------------------------------------------------------------------
try:
    lcd_init()
except Exception as error:
    lcd_ok = False
    print("OJO: la LCD no responde ({}); sigo sin LCD".format(error))
lcd_mostrar("Marca un digito", "para dibujar")

# Linea de arranque: si en Thonny (o en el monitor del HTML) no aparece
# esto, el main.py no es este archivo o se cayo antes de llegar aca.
print("ESP32 listo: esperando teclas")

tecla_anterior = None

while True:
    tecla = leer_tecla()
    # tecla != tecla_anterior: mientras se mantiene apretada, el barrido
    # la sigue viendo cada 30 ms; sin esta condicion se mandaria el mismo
    # digito decenas de veces. Solo cuenta cuando CAMBIA (se apreto una
    # nueva).
    if tecla is not None and tecla != tecla_anterior:
        if tecla.isdigit():
            lcd_mostrar("Dibujando:", tecla)
            # print sale por el USB (el mismo puerto que abre pyserial en
            # el PC): "DIGIT:n" es todo el protocolo, una linea por tecla.
            print("DIGIT:{}".format(tecla))
        else:
            # A-D, * y # no son digitos que el brazo sepa dibujar, pero se
            # avisan igual: asi se ve que el teclado SI se esta leyendo
            # (el PC ignora esta linea porque no empieza con "DIGIT:").
            print("tecla ignorada:", tecla)
    tecla_anterior = tecla
    time.sleep_ms(30)  # anti-rebote simple
