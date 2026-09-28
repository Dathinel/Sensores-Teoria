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

# El ESP32 clasico trae dos conversores digital-analogico (DAC) de 8 bits,
# fijos en GPIO25 y GPIO26. dac.write(n) con n entre 0 y 255 saca un voltaje
# continuo de aprox. n/255 * 3.3 V. Con el osciloscopio en modo XY, el voltaje
# del canal 1 mueve el punto en horizontal y el del canal 2 en vertical: cada
# par (x, y) escrito en los DAC es un punto de la figura en la pantalla.

dac_x = DAC(Pin(25))   # Eje X -> canal 1 del osciloscopio
dac_y = DAC(Pin(26))   # Eje Y -> canal 2 del osciloscopio

# ============================================================
# CONFIGURACION GENERAL
# ============================================================

# Tiempo de espera entre un punto y el siguiente, en microsegundos. Cuanto
# mas corto, mas rapido se repite la figura completa y menos parpadea (la
# figura "solida" es persistencia de la vision: el ojo funde los puntos si
# el ciclo completo se repite muchas veces por segundo). 1 us es casi nada:
# en la practica el limite real es lo que tarda MicroPython en cada dac.write().
DRAW_US = 1

# No se usa el rango completo 0-255: se deja un margen de 10 a cada lado
# para que la figura no quede pegada al borde de la pantalla, donde el
# osciloscopio suele recortar o distorsionar el trazo.

DAC_MIN = 10
DAC_MAX = 245

# Por si las puntas quedan al reves o el osciloscopio muestra la figura
# espejada: en vez de recablear, se invierte el eje en software.
INVERT_X = False
INVERT_Y = False

# Desplazamiento global de todo el grupo
DESPLAZAMIENTO_X = -0.03
DESPLAZAMIENTO_Y = 0.00

# True = escribir en los DAC (funcionamiento normal)
ESCRIBIR_DAC = True
# ENVIAR_SERIAL = True imprime cada punto como "x y" (dos enteros 0-255) por
# el USB. Sirve para ver la figura sin osciloscopio: cualquier programa que
# lea esas lineas del puerto serial y las pinte como puntos XY la reconstruye.
# Imprimir es MUCHO mas lento que escribir en el DAC, asi que con esto activo
# la figura en el osciloscopio se ve parpadeando: dejarlo en False para la demo.
ENVIAR_SERIAL = False

# ============================================================
# UTILIDADES
# ============================================================

# Todas las piezas del pez se piensan en un espacio normalizado de 0 a 1
# (0 = borde izquierdo/inferior, 1 = borde derecho/superior). Solo aqui, al
# final, se pasa a enteros del DAC. Asi mover o escalar la figura es sumar o
# multiplicar numeros simples, sin pensar en 10-245 hasta el ultimo paso.

def limitar(valor):
    # Recorta a 0-1: un punto que se salga del area se queda en el borde
    # en vez de mandarle al DAC un valor fuera de 0-255 (que daria error).
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

# A diferencia de pez3_esp32.py, estos generadores devuelven puntos del
# MODELO BASE (centrado en 0,0, sin convertir al DAC). La conversion se hace
# despues en transformar(), una vez por cada pez con su propio centro y escala.

# Una elipse es un circulo estirado: x = cx + rx*cos(t), y = cy + ry*sin(t).
# Recorriendo t solo entre dos angulos (por ejemplo 200 a 340 grados) se
# obtiene un ARCO, que es como se dibuja la boca (la parte de abajo de una
# elipse, una sonrisa). `puntos` decide la resolucion: mas puntos = trazo mas
# liso pero ciclo mas largo (la figura completa parpadea mas).
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


# Curva de Bezier cuadratica: sale de (x0, y0), llega a (x2, y2) y el punto
# de control (x1, y1) la "jala" hacia su lado sin que la curva pase por el.
# Formula: B(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2, con t de 0 a 1.
# Con t=0 queda P0 y con t=1 queda P2; en medio, una mezcla suave de los tres.
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
    # Escala y traslada el modelo base: primero se multiplica (el pez crece o
    # se achica alrededor de su propio centro 0,0) y DESPUES se suma el centro.
    # En el orden inverso, la escala tambien agrandaria la distancia al
    # origen y el pez terminaria en otra posicion.
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

# Cola: P1 es el extremo derecho del cuerpo (radio horizontal 0.24), para
# que la cola nazca justo del borde de la elipse.
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

# Centro (x, y) en el espacio 0-1 y escala de cada pez: uno grande arriba a
# la izquierda y dos mas chicos a la derecha, repartidos para que no se
# toquen. Para agregar otro pez basta otra llamada a crear_pez.

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

# Recorre una lista de puntos ya convertidos y los va escribiendo en los
# DAC. El haz del osciloscopio "viaja" de un punto al siguiente; entre pieza
# y pieza (del cuerpo a la cola, por ejemplo) se ve un trazo de salto muy
# tenue porque ese recorrido dura un solo punto y el ojo casi no lo registra.

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
    # Pupila con mas espera por punto: tiene pocos puntos y, a la velocidad
    # del resto, se veria mas tenue que las demas piezas.
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