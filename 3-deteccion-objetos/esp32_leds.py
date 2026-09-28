# Guardar este archivo en el ESP32 con el nombre main.py
# para que se ejecute automaticamente al encender o reiniciar el chip.
#
# Escucha el puerto serial, el mismo cable USB usado para programar,
# esperando lineas de dos caracteres como "10" o "01".
# El primer caracter controla el LED de GPIO25 (silla, o carro con
# --carro-moto), el segundo el de GPIO26 (celular, o moto).
# Si no llega ningun mensaje en 2 segundos, apaga los dos LEDs por seguridad.
#
# Contesta por el mismo cable, para que el PC pueda confirmar que llego:
#   "LEDS 10"            -> aplico el mensaje "10"
#   "APAGADO_SEGURIDAD"  -> paso el tiempo limite sin mensajes y apago todo

from machine import Pin
import sys
import select
import time

# GPIO25 y GPIO26: pines de proposito general sin funcion de arranque
# (strapping) ni conectados a la flash, asi que no molestan al encender.
LED_SILLA = Pin(25, Pin.OUT)
LED_CELULAR = Pin(26, Pin.OUT)

# Se apagan de entrada para no dejar los LEDs en un estado indefinido.
LED_SILLA.value(0)
LED_CELULAR.value(0)

# En MicroPython el USB-serial es a la vez la consola (REPL) y sys.stdin.
# select.poll() permite preguntar "hay algo para leer?" con un tiempo maximo
# de espera, en vez de quedarse bloqueado en readline() sin poder vigilar el
# reloj del apagado de seguridad.
sondeo = select.poll()
sondeo.register(sys.stdin, select.POLLIN)

# El PC repite el estado cada 500 ms mientras esta corriendo; 2000 ms sin
# nada (4 mensajes perdidos seguidos) significa que el script se cerro o se
# desconecto el cable.
TIEMPO_LIMITE_MS = 2000
ultimo_mensaje = time.ticks_ms()
apagado_avisado = True  # al arrancar ya esta todo apagado, no hace falta avisar

print("Esperando datos de deteccion por serial...")

while True:
    # Espera como maximo 100 ms a que llegue algo; si no llega, sigue de largo
    # para poder revisar el tiempo limite.
    eventos = sondeo.poll(100)

    if eventos:
        linea = sys.stdin.readline().strip()
        # Solo se aceptan exactamente dos caracteres "0"/"1": una linea
        # cortada o con ruido se ignora en vez de hacer fallar el programa.
        if len(linea) == 2 and linea[0] in "01" and linea[1] in "01":
            LED_SILLA.value(int(linea[0]))
            LED_CELULAR.value(int(linea[1]))
            ultimo_mensaje = time.ticks_ms()
            apagado_avisado = False
            print("LEDS", linea)

    # ticks_diff y no una resta: el contador de milisegundos da la vuelta
    # (vuelve a cero) cada cierto tiempo y ticks_diff lo tiene en cuenta.
    if time.ticks_diff(time.ticks_ms(), ultimo_mensaje) > TIEMPO_LIMITE_MS:
        LED_SILLA.value(0)
        LED_CELULAR.value(0)
        if not apagado_avisado:
            # Se avisa una sola vez por corte, no 10 veces por segundo.
            print("APAGADO_SEGURIDAD")
            apagado_avisado = True
