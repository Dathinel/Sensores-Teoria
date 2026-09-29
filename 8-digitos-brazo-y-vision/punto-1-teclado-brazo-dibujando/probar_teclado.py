# Prueba aislada del teclado matricial 4x4 (sin LCD, sin PC).
# Se corre desde Thonny con el boton de "Run" (NO se guarda como main.py).
# Cada vez que se aprieta una tecla imprime la fila y la columna que se
# cerraron. Sirve para separar un problema de cableado de uno del
# programa principal:
#   - No sale nada con ninguna tecla: revisar GND/cables del teclado o
#     que los 8 cables esten realmente en esos GPIO.
#   - Sale una tecla distinta a la apretada: el teclado tiene sus pines
#     en otro orden; cambiar ROW_PINS/COL_PINS (aqui y en main.py).

from machine import Pin
import time

ROW_PINS = [14, 27, 26, 25]   # R1..R4
COL_PINS = [33, 32, 18, 19]   # C1..C4

MAPA_TECLAS = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"],
]

filas = [Pin(p, Pin.OUT, value=1) for p in ROW_PINS]
columnas = [Pin(p, Pin.IN, Pin.PULL_UP) for p in COL_PINS]

# Con todas las filas en alto, todas las columnas deberian leer 1. Si
# alguna ya lee 0 sin tocar nada, esa columna esta en corto a GND o mal
# conectada.
print("Columnas en reposo (deben ser todas 1):", [c.value() for c in columnas])
print("Aprieta teclas (Ctrl+C para salir)...")

anterior = None
while True:
    actual = None
    for f in range(4):
        filas[f].value(0)
        time.sleep_us(10)
        for c in range(4):
            if columnas[c].value() == 0:
                actual = (f, c)
        filas[f].value(1)
    if actual is not None and actual != anterior:
        f, c = actual
        print("Tecla {}  (fila R{} = GPIO{}, columna C{} = GPIO{})".format(
            MAPA_TECLAS[f][c], f + 1, ROW_PINS[f], c + 1, COL_PINS[c]))
    anterior = actual
    time.sleep_ms(30)
