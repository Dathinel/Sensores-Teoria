# Guardar este archivo en el ESP32 con el nombre main.py
# para que se ejecute automaticamente al encender o reiniciar el chip.
#
# Los LEDs mantienen su estado hasta que llegue una orden nueva, no se
# apagan solos por falta de mensajes, porque el control es por voz
# puntual y no por deteccion continua de una camara.
#
# Lineas esperadas por el puerto serial:
#   "10"   enciende el led rojo, apaga el azul
#   "01"   apaga el led rojo, enciende el azul
#   "11"   enciende los dos
#   "00"   apaga los dos
#   "SHOW" corre un show de luces corto y despues vuelve al estado anterior

from machine import Pin
import sys
import select
import time

LED_ROJO = Pin(25, Pin.OUT)
LED_AZUL = Pin(26, Pin.OUT)

LED_ROJO.value(0)
LED_AZUL.value(0)

sondeo = select.poll()
sondeo.register(sys.stdin, select.POLLIN)


def hacer_show():
    estado_rojo_previo = LED_ROJO.value()
    estado_azul_previo = LED_AZUL.value()

    for _ in range(6):
        LED_ROJO.value(1)
        LED_AZUL.value(0)
        time.sleep(0.2)
        LED_ROJO.value(0)
        LED_AZUL.value(1)
        time.sleep(0.2)

    LED_ROJO.value(estado_rojo_previo)
    LED_AZUL.value(estado_azul_previo)


print("Esperando comandos de voz por serial...")

while True:
    eventos = sondeo.poll(100)

    if eventos:
        linea = sys.stdin.readline().strip()

        if linea == "SHOW":
            hacer_show()
        elif len(linea) == 2 and linea[0] in "01" and linea[1] in "01":
            LED_ROJO.value(int(linea[0]))
            LED_AZUL.value(int(linea[1]))
