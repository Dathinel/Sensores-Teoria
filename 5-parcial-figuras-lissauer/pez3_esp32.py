# ============================================================
# PEZ EN OSCILOSCOPIO - MODO XY
# ESP32 + MicroPython
#
# GPIO 25 -> Canal X del osciloscopio
# GPIO 26 -> Canal Y del osciloscopio
# GND     -> GND del osciloscopio
#
# Figura:
#   - Cuerpo ovalado
#   - Cola triangular
#   - Ojo circular
#   - Pupila
#   - Boca curva
#   - Aleta curva
#
# Incluye:
#   - Desplazamiento horizontal y vertical
#   - Vista previa por serial opcional
# ============================================================

from machine import Pin, DAC
import math
import utime


# ============================================================
# CONFIGURACION DE LOS DAC
# ============================================================

dac_x = DAC(Pin(25))     # Eje X
dac_y = DAC(Pin(26))     # Eje Y


# ============================================================
# CONFIGURACION GENERAL
# ============================================================

# Tiempo entre puntos
DRAW_US = 1

# Limites utilizados del DAC
DAC_MIN = 10
DAC_MAX = 245

# Inversion de los ejes
INVERT_X = False
INVERT_Y = False


# ============================================================
# POSICION GLOBAL DEL PEZ
# ============================================================

# Horizontal:
# negativo = izquierda
# positivo = derecha

DESPLAZAMIENTO_X = -0.08


# Vertical:
# negativo = abajo
# positivo = arriba

DESPLAZAMIENTO_Y = 0.00


# ============================================================
# VISTA PREVIA
# ============================================================

# True = enviar datos a los DAC
ESCRIBIR_DAC = True

# True = imprimir coordenadas por serial
# False = funcionamiento normal con osciloscopio

ENVIAR_SERIAL = False


# ============================================================
# LIMITAR VALORES ENTRE 0 Y 1
# ============================================================

def limitar(valor):

    if valor < 0:
        return 0

    if valor > 1:
        return 1

    return valor


# ============================================================
# CONVERTIR COORDENADA X AL DAC
# ============================================================

def convertir_x(x):

    # Mover toda la figura horizontalmente
    x = x + DESPLAZAMIENTO_X

    # Limitar entre 0 y 1
    x = limitar(x)

    # Invertir eje si es necesario
    if INVERT_X:
        x = 1.0 - x

    # Convertir a rango del DAC
    return int(
        DAC_MIN +
        x * (DAC_MAX - DAC_MIN)
    )


# ============================================================
# CONVERTIR COORDENADA Y AL DAC
# ============================================================

def convertir_y(y):

    # Mover toda la figura verticalmente
    y = y + DESPLAZAMIENTO_Y

    # Limitar entre 0 y 1
    y = limitar(y)

    # Invertir eje si es necesario
    if INVERT_Y:
        y = 1.0 - y

    # Convertir a rango del DAC
    return int(
        DAC_MIN +
        y * (DAC_MAX - DAC_MIN)
    )


# ============================================================
# CONVERTIR UN PUNTO COMPLETO
# ============================================================

def convertir_punto(x, y):

    return (
        convertir_x(x),
        convertir_y(y)
    )


# ============================================================
# GENERADOR DE ELIPSES Y ARCOS
# ============================================================

def crear_elipse(
    cx,
    cy,
    rx,
    ry,
    puntos,
    angulo_inicio=0,
    angulo_final=360
):

    trayectoria = []

    inicio = math.radians(angulo_inicio)
    final = math.radians(angulo_final)

    for i in range(puntos + 1):

        t = inicio + (final - inicio) * i / puntos

        x = cx + rx * math.cos(t)
        y = cy + ry * math.sin(t)

        trayectoria.append(
            convertir_punto(x, y)
        )

    return trayectoria


# ============================================================
# GENERADOR DE LINEAS
# ============================================================

def crear_linea(
    x1,
    y1,
    x2,
    y2,
    puntos
):

    trayectoria = []

    for i in range(puntos + 1):

        t = i / puntos

        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t

        trayectoria.append(
            convertir_punto(x, y)
        )

    return trayectoria


# ============================================================
# GENERADOR DE CURVAS BEZIER
# ============================================================

def crear_bezier(
    x0,
    y0,
    x1,
    y1,
    x2,
    y2,
    puntos
):

    trayectoria = []

    for i in range(puntos + 1):

        t = i / puntos

        u = 1.0 - t

        x = (
            u * u * x0 +
            2 * u * t * x1 +
            t * t * x2
        )

        y = (
            u * u * y0 +
            2 * u * t * y1 +
            t * t * y2
        )

        trayectoria.append(
            convertir_punto(x, y)
        )

    return trayectoria


# ============================================================
# 1. CUERPO DEL PEZ
# ============================================================

CUERPO_CX = 0.42
CUERPO_CY = 0.52

CUERPO_RX = 0.29
CUERPO_RY = 0.25


cuerpo = crear_elipse(
    CUERPO_CX,
    CUERPO_CY,
    CUERPO_RX,
    CUERPO_RY,
    110
)


# ============================================================
# 2. COLA TRIANGULAR
# ============================================================

# Punto donde se conecta la cola con el cuerpo

P1_X = CUERPO_CX + CUERPO_RX
P1_Y = CUERPO_CY


# Punto superior

P2_X = 0.93
P2_Y = 0.78


# Punto inferior

P3_X = 0.93
P3_Y = 0.26


cola = []


# Linea 1
cola += crear_linea(
    P1_X,
    P1_Y,
    P2_X,
    P2_Y,
    25
)


# Linea 2
cola += crear_linea(
    P2_X,
    P2_Y,
    P3_X,
    P3_Y,
    35
)


# Linea 3
cola += crear_linea(
    P3_X,
    P3_Y,
    P1_X,
    P1_Y,
    25
)


# ============================================================
# 3. OJO
# ============================================================

OJO_X = 0.33
OJO_Y = 0.64

OJO_RX = 0.040
OJO_RY = 0.045


ojo = crear_elipse(
    OJO_X,
    OJO_Y,
    OJO_RX,
    OJO_RY,
    30
)


# ============================================================
# 4. PUPILA
# ============================================================

PUPILA_X = 0.33
PUPILA_Y = 0.65

PUPILA_RX = 0.012
PUPILA_RY = 0.014


pupila = crear_elipse(
    PUPILA_X,
    PUPILA_Y,
    PUPILA_RX,
    PUPILA_RY,
    14
)


# ============================================================
# 5. BOCA
# ============================================================

BOCA_X = 0.31
BOCA_Y = 0.44

BOCA_RX = 0.070
BOCA_RY = 0.045


boca = crear_elipse(
    BOCA_X,
    BOCA_Y,
    BOCA_RX,
    BOCA_RY,
    30,
    200,
    340
)


# ============================================================
# 6. ALETA
#
# Forma similar a:
#
#       <
#
# Se usan dos curvas Bezier.
# ============================================================

aleta = []


# Parte superior

aleta += crear_bezier(
    0.575,
    0.515,

    0.520,
    0.515,

    0.485,
    0.475,

    18
)


# Parte inferior

aleta += crear_bezier(
    0.485,
    0.475,

    0.520,
    0.430,

    0.580,
    0.440,

    18
)


# ============================================================
# FUNCION PARA DIBUJAR
# ============================================================

def dibujar(
    trayectoria,
    velocidad=DRAW_US
):

    # Primer punto

    x, y = trayectoria[0]


    if ESCRIBIR_DAC:

        dac_x.write(x)
        dac_y.write(y)


    if ENVIAR_SERIAL:

        print(x, y)


    # Dibujar los demas puntos

    for i in range(
        1,
        len(trayectoria)
    ):

        x, y = trayectoria[i]


        if ESCRIBIR_DAC:

            dac_x.write(x)
            dac_y.write(y)


        if ENVIAR_SERIAL:

            print(x, y)


        utime.sleep_us(
            velocidad
        )


# ============================================================
# FUNCION PRINCIPAL DEL PEZ
# ============================================================

def dibujar_pez():

    # Cuerpo
    dibujar(cuerpo)

    # Cola
    dibujar(cola)

    # Ojo
    dibujar(ojo)

    # Pupila
    dibujar(
        pupila,
        180
    )

    # Boca
    dibujar(boca)

    # Aleta
    dibujar(aleta)


# ============================================================
# BUCLE INFINITO
# ============================================================

while True:

    dibujar_pez()