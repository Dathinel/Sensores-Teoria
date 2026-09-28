# Comparacion de velocidad MicroPython vs. C/C++ (version MicroPython).
# Circuito: circuito-comparacion-leds.png -> LED rojo en GPIO5, amarillo en
# GPIO17 y verde en GPIO16, cada uno con su resistencia de 220 ohm a GND.
#
# Correrlo desde Thonny (F5) con el ESP32 conectado. Hace dos cosas:
#  1. Una secuencia de semaforo que se ve a simple vista.
#  2. Una medicion: cuantos microsegundos tarda cambiar un pin de estado,
#     repitiendolo muchas veces. Es la misma medicion que hace
#     semaforo_velocidad/semaforo_velocidad.ino en C/C++, para comparar
#     numeros y no impresiones.

from machine import Pin
import time

ROJO = Pin(5, Pin.OUT)
AMARILLO = Pin(17, Pin.OUT)
VERDE = Pin(16, Pin.OUT)
LEDS = (ROJO, AMARILLO, VERDE)

# --- 1. Secuencia visible -----------------------------------------------------
# Con pausas de cientos de milisegundos NO se nota diferencia entre lenguajes:
# el interprete tarda microsegundos en cada instruccion, mil veces menos que
# la pausa. Por eso hace falta la medicion de la parte 2.
for led in LEDS:
    led.value(0)
for _ in range(3):
    for led, pausa_ms in ((VERDE, 1500), (AMARILLO, 500), (ROJO, 1500)):
        led.value(1)
        time.sleep_ms(pausa_ms)
        led.value(0)

# --- 2. Medicion ------------------------------------------------------------
# 10000 cambios: suficientes para que el tiempo total (milisegundos) se mida
# bien con el reloj de microsegundos y el promedio no dependa de un caso raro.
REPETICIONES = 10000

# ticks_us / ticks_diff en vez de restar: el contador da la vuelta y
# ticks_diff calcula bien la diferencia aunque pase eso.
inicio = time.ticks_us()
for _ in range(REPETICIONES):
    ROJO.value(1)
    ROJO.value(0)
total_us = time.ticks_diff(time.ticks_us(), inicio)

# Cada vuelta hace DOS cambios (encender y apagar); el total incluye tambien
# lo que cuesta el propio for, igual que en la version de C/C++.
print("MicroPython: %d cambios en %d us -> %.2f us por cambio"
      % (2 * REPETICIONES, total_us, total_us / (2 * REPETICIONES)))

# Variante "optimizada" tipica de MicroPython: guardar el metodo en una
# variable local evita buscar ROJO.value en cada vuelta. Sirve para ver que
# parte del costo es el interprete buscando nombres, no el pin en si.
encender = ROJO.on
apagar = ROJO.off
inicio = time.ticks_us()
for _ in range(REPETICIONES):
    encender()
    apagar()
total_us = time.ticks_diff(time.ticks_us(), inicio)
print("MicroPython (metodo local): %.2f us por cambio" % (total_us / (2 * REPETICIONES)))
