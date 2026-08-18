# Guardar este archivo en el ESP32 con el nombre main.py
# para que se ejecute automaticamente al encender o reiniciar el chip.
#
# Escucha el puerto serial, el mismo cable USB usado para programar,
# esperando lineas de dos caracteres como "10" o "01".
# El primer caracter controla el LED de la silla, el segundo el del celular.
# Si no llega ningun mensaje en 2 segundos, apaga los dos LEDs por seguridad.

from machine import Pin
import sys
import select
import time

LED_SILLA = Pin(25, Pin.OUT)
LED_CELULAR = Pin(26, Pin.OUT)

LED_SILLA.value(0)
LED_CELULAR.value(0)

sondeo = select.poll()
sondeo.register(sys.stdin, select.POLLIN)

ultimo_mensaje = time.ticks_ms()
TIEMPO_LIMITE_MS = 2000

print("Esperando datos de deteccion por serial...")

while True:
    eventos = sondeo.poll(100)

    if eventos:
        linea = sys.stdin.readline().strip()
        if len(linea) == 2 and linea[0] in "01" and linea[1] in "01":
            LED_SILLA.value(int(linea[0]))
            LED_CELULAR.value(int(linea[1]))
            ultimo_mensaje = time.ticks_ms()

    if time.ticks_diff(time.ticks_ms(), ultimo_mensaje) > TIEMPO_LIMITE_MS:
        LED_SILLA.value(0)
        LED_CELULAR.value(0)
