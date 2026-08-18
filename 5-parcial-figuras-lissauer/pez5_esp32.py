# ============================================================
# TRES PECES EN OSCILOSCOPIO - MODO XY
# ESP32 + MicroPython
# ============================================================

from machine import Pin, DAC
import math
import utime

# ============================================================
# CONFIGURACION DAC
# ============================================================

dac_x = DAC(Pin(25))
dac_y = DAC(Pin(26))

# ============================================================
# CONFIGURACION GENERAL
# ============================================================

DRAW_US = 1

DAC_MIN = 10
DAC_MAX = 245

INVERT_X = False
INVERT_Y = False

# Desplazamiento global de todo el grupo
DESPLAZAMIENTO_X = -0.03
DESPLAZAMIENTO_Y = 0.00

ESCRIBIR_DAC = True
ENVIAR_SERIAL = False

# ============================================================
# UTILIDADES
# ============================================================

def limitar(valor):
    if valor < 0:
        return 0
    if valor > 1:
        return 1
    return valor


def convertir_x(x):
    x = x + DESPLAZAMIENTO_X
    x = limitar(x)

    if INVERT_X:
        x = 1.0 - x

    return int(DAC_MIN + x * (DAC_MAX - DAC_MIN))


def convertir_y(y):
    y = y + DESPLAZAMIENTO_Y
    y = limitar(y)

    if INVERT_Y:
        y = 1.0 - y

    return int(DAC_MIN + y * (DAC_MAX - DAC_MIN))


def convertir_punto(x, y):
    return (convertir_x(x), convertir_y(y))


# ============================================================
# GENERADORES DE GEOMETRIA
# ============================================================

def crear_elipse(cx, cy, rx, ry, puntos, angulo_inicio=0, angulo_final=360):
    trayectoria = []

    inicio = math.radians(angulo_inicio)
    final = math.radians(angulo_final)

    for i in range(puntos + 1):
        t = inicio + (final - inicio) * i / puntos
        x = cx + rx * math.cos(t)
        y = cy + ry * math.sin(t)
        trayectoria.append((x, y))

    return trayectoria


def crear_linea(x1, y1, x2, y2, puntos):
    trayectoria = []

    for i in range(puntos + 1):
        t = i / puntos
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        trayectoria.append((x, y))

    return trayectoria


def crear_bezier(x0, y0, x1, y1, x2, y2, puntos):
    trayectoria = []

    for i in range(puntos + 1):
        t = i / puntos
        u = 1.0 - t

        x = u*u*x0 + 2*u*t*x1 + t*t*x2
        y = u*u*y0 + 2*u*t*y1 + t*t*y2

        trayectoria.append((x, y))

    return trayectoria


def transformar(trayectoria, centro_x, centro_y, escala):
    resultado = []

    for x, y in trayectoria:
        x = x * escala + centro_x
        y = y * escala + centro_y
        resultado.append(convertir_punto(x, y))

    return resultado


# ============================================================
# MODELO BASE DEL PEZ
# ============================================================

# Cuerpo
cuerpo_base = crear_elipse(
    0.00,
    0.00,
    0.24,
    0.18,
    110
)

# Cola
P1 = (0.24, 0.00)
P2 = (0.44, 0.19)
P3 = (0.44, -0.19)

cola_base = []
cola_base += crear_linea(P1[0], P1[1], P2[0], P2[1], 25)
cola_base += crear_linea(P2[0], P2[1], P3[0], P3[1], 35)
cola_base += crear_linea(P3[0], P3[1], P1[0], P1[1], 25)

# Ojo
ojo_base = crear_elipse(
    -0.08,
     0.070,
     0.035,
     0.040,
     30
)

# Pupila
pupila_base = crear_elipse(
    -0.08,
     0.078,
     0.011,
     0.013,
     14
)

# Boca
boca_base = crear_elipse(
    -0.10,
    -0.050,
     0.060,
     0.035,
     30,
     200,
     340
)

# Aleta
aleta_base = []
aleta_base += crear_bezier(
     0.10,  0.015,
     0.055, 0.020,
     0.020,-0.015,
     18
)

aleta_base += crear_bezier(
     0.020,-0.015,
     0.055,-0.055,
     0.105,-0.040,
     18
)

# ============================================================
# CREAR PEZ COMPLETO
# ============================================================

def crear_pez(centro_x, centro_y, escala):
    pez = {}

    pez["cuerpo"] = transformar(cuerpo_base, centro_x, centro_y, escala)
    pez["cola"]   = transformar(cola_base,   centro_x, centro_y, escala)
    pez["ojo"]    = transformar(ojo_base,    centro_x, centro_y, escala)
    pez["pupila"] = transformar(pupila_base, centro_x, centro_y, escala)
    pez["boca"]   = transformar(boca_base,   centro_x, centro_y, escala)
    pez["aleta"]  = transformar(aleta_base,  centro_x, centro_y, escala)

    return pez


# ============================================================
# POSICION DE LOS 3 PECES - NUEVA DISTRIBUCION
# ============================================================

pez1 = crear_pez(
    0.18,   # X
    0.73,   # Y
    0.72    # tamaño
)

pez2 = crear_pez(
    0.74,   # X
    0.72,   # Y
    0.56    # tamaño
)

pez3 = crear_pez(
    0.72,   # X
    0.24,   # Y
    0.62    # tamaño
)

# ============================================================
# DIBUJO
# ============================================================

def dibujar(trayectoria, velocidad=DRAW_US):
    x, y = trayectoria[0]

    if ESCRIBIR_DAC:
        dac_x.write(x)
        dac_y.write(y)

    if ENVIAR_SERIAL:
        print(x, y)

    for i in range(1, len(trayectoria)):
        x, y = trayectoria[i]

        if ESCRIBIR_DAC:
            dac_x.write(x)
            dac_y.write(y)

        if ENVIAR_SERIAL:
            print(x, y)

        utime.sleep_us(velocidad)


def dibujar_un_pez(pez):
    dibujar(pez["cuerpo"])
    dibujar(pez["cola"])
    dibujar(pez["ojo"])
    dibujar(pez["pupila"], 40)
    dibujar(pez["boca"])
    dibujar(pez["aleta"])


def dibujar_tres_peces():
    dibujar_un_pez(pez1)
    dibujar_un_pez(pez2)
    dibujar_un_pez(pez3)


# ============================================================
# BUCLE PRINCIPAL
# ============================================================

while True:
    dibujar_tres_peces()