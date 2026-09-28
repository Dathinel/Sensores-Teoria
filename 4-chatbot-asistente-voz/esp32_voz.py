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
#
# Respuestas que devuelve por el mismo puerto (las lee comando_voz.py y las
# muestra como "ESP32 dice: ..."; sirven para saber si la orden llego bien):
#   "OK 10" / "OK SHOW" / "IGNORADO <linea>"

from machine import Pin
import sys
import select
import time

# GPIO25 y GPIO26: pines de proposito general sin funcion especial en el
# arranque (no son strapping pins), seguros para manejar un LED.
LED_ROJO = Pin(25, Pin.OUT)
LED_AZUL = Pin(26, Pin.OUT)

# Se apagan de entrada para no arrancar con un estado indefinido.
LED_ROJO.value(0)
LED_AZUL.value(0)

# En MicroPython el USB del ESP32 es sys.stdin/sys.stdout. select.poll()
# permite PREGUNTAR si ya llego algo sin quedarse bloqueado esperando.
sondeo = select.poll()
sondeo.register(sys.stdin, select.POLLIN)

# Cuantas veces se alternan los LEDs en el show y cuanto dura cada paso.
# 6 vueltas x 2 pasos x 0.2 s = 2.4 s de show en total.
VUELTAS_SHOW = 6
PASO_SHOW_S = 0.2


def hacer_show():
    # Se guarda el estado actual para devolverlo tal cual al terminar: si el
    # rojo ya estaba encendido, debe seguir encendido despues del show.
    estado_rojo_previo = LED_ROJO.value()
    estado_azul_previo = LED_AZUL.value()

    for _ in range(VUELTAS_SHOW):
        LED_ROJO.value(1)
        LED_AZUL.value(0)
        time.sleep(PASO_SHOW_S)
        LED_ROJO.value(0)
        LED_AZUL.value(1)
        time.sleep(PASO_SHOW_S)

    LED_ROJO.value(estado_rojo_previo)
    LED_AZUL.value(estado_azul_previo)


print("Esperando comandos de voz por serial...")

while True:
    # Espera como maximo 100 ms a que llegue algo; si no llega nada, da la
    # vuelta y vuelve a preguntar (no se queda pegado para siempre).
    eventos = sondeo.poll(100)

    if eventos:
        linea = sys.stdin.readline().strip()

        if linea == "SHOW":
            # Se contesta ANTES del show para que la PC no espere los 2.4 s.
            print("OK SHOW")
            hacer_show()
        elif len(linea) == 2 and linea[0] in "01" and linea[1] in "01":
            # Primer caracter = rojo, segundo = azul.
            LED_ROJO.value(int(linea[0]))
            LED_AZUL.value(int(linea[1]))
            print("OK " + linea)
        elif linea:
            # Cualquier otra cosa se ignora (no se adivina un mensaje corrupto),
            # pero se avisa para poder diagnosticar un problema de formato.
            print("IGNORADO " + linea)
