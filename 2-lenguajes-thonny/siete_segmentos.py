# Display de siete segmentos (catodo comun) en MicroPython, el mismo codigo
# de la captura wokwi-micropython.png. Se puede pegar tal cual en Wokwi
# (proyecto "MicroPython on ESP32") o correr en Thonny con el circuito real.
#
# Segmentos de un display de 7 segmentos:
#      aaa
#     f   b
#      ggg
#     e   c
#      ddd
# Encendiendo a, b, g, e y d (y dejando c y f apagados) se dibuja un "2".

from machine import Pin
import time

# Un pin por segmento, cada uno con su resistencia (220 ohm) hacia el display.
sA = Pin(17, Pin.OUT)
sB = Pin(16, Pin.OUT)
sC = Pin(32, Pin.OUT)
sD = Pin(33, Pin.OUT)
sE = Pin(25, Pin.OUT)
sF = Pin(14, Pin.OUT)
sG = Pin(12, Pin.OUT)  # GPIO12 es pin de arranque: sin nada que lo fuerce a 1 al encender, no molesta

# A diferencia de Arduino, aqui no hay un loop() que el framework repita
# solo: el bucle principal lo escribe uno mismo.
while True:
    # 1 = nivel alto (3,3 V) = segmento encendido, en un display de catodo comun.
    sA.value(1)
    sB.value(1)
    sC.value(0)
    sD.value(1)
    sE.value(1)
    sF.value(0)
    sG.value(1)
    # Sin esta pausa el bucle gira sin parar reescribiendo lo mismo; no hace
    # dano, pero ocupa el procesador y deja la consola de Thonny lenta.
    time.sleep_ms(100)
