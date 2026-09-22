# ESP-A (maestro): recibe por USB, de reconocer_digito.py en el PC, el
# digito reconocido ("DIGIT:n") y se lo reenvia al ESP-B (esclavo) por
# DOS caminos a la vez: UART2 y SPI real. El ESP-B escucha los dos al
# mismo tiempo y usa el que le llegue de verdad segun como este
# cableado -- asi no hace falta saber de antemano cual de los dos cables
# se conecto, y si uno falla (por ejemplo un cable SPI mal puesto) el
# otro sigue funcionando. Ver la seccion "Dos caminos: UART2 y SPI" del
# README para el detalle completo.
#
# Nota sobre "SPI esclavo": el esquema de la actividad pide comunicar
# los dos ESP32 por SPI (maestro/esclavo). El puerto machine.SPI de
# MicroPython para el ESP32 solo implementa el modo maestro: no expone
# modo esclavo, asi que el ESP-B (el que tiene que escuchar SPI) no
# puede quedarse en MicroPython -- corre un sketch de Arduino/C++ en su
# lugar (ver esp-b-esclavo/esp_b_esclavo.ino). El ESP-A, en cambio, solo
# necesita hablar SPI en modo MAESTRO, que machine.SPI SI soporta, asi
# que se queda en MicroPython sin problema.
#
# Este archivo debe guardarse como main.py en el ESP-A.
# UART2: TX=GPIO17, RX=GPIO16 -> al RX/TX (cruzados) del ESP-B.
# SPI (VSPI, maestro): SCK=GPIO18, MOSI=GPIO23, MISO=GPIO19, CS=GPIO5 ->
# a los mismos pines (sin cruzar) del ESP-B.
#
# Como diagnosticar si esto no esta funcionando (por ejemplo, si
# reconocer_digito.py se queda en "esperando confirmacion..." sin
# avanzar nunca):
#
#   1. Conectar Thonny a este ESP32 por USB (con reconocer_digito.py
#      CERRADO, porque los dos no pueden usar el mismo puerto COM al
#      mismo tiempo) SOLO para ver que al reiniciar la placa aparezca
#      "ESP-A listo...". Si no aparece nada, main.py no esta corriendo
#      (revisar que se haya guardado con ese nombre exacto en la
#      placa, no solo abierto en el editor).
#
#   2. NO escribir DIGIT:5 a mano en la consola de Thonny: cuando
#      main.py ya esta bloqueado en sys.stdin.readline(), Thonny no
#      puede mandarle texto suelto por su Shell (tira "Could not get
#      raw-paste confirmation" y termina interrumpiendo main.py con un
#      KeyboardInterrupt) — ese error es una limitacion de como
#      interactua Thonny con un programa que ya esta corriendo, no
#      dice nada sobre si este archivo esta bien o mal.
#
#      En vez de eso, cerrar Thonny (para liberar el puerto) y correr
#      `python probar_esp_a.py` (en la carpeta de arriba) — abre el
#      puerto igual que reconocer_digito.py, manda DIGIT:5 de verdad
#      y muestra todo lo que responda. Si ahi aparece "REENVIADO:5",
#      el ESP-A esta perfecto y el problema esta en otro lado (revisar
#      PUERTO_SERIAL en reconocer_digito.py, o el cableado hacia el
#      ESP-B). Si no aparece nada, el problema esta en este archivo o
#      en el cable USB.

from machine import UART, SPI, Pin
import sys

uart_a_esclavo = UART(2, baudrate=115200, tx=17, rx=16)

# SPI maestro (VSPI, pines por defecto de esta interfaz en el ESP32).
# machine.SPI no maneja el CS solo -- se controla a mano con un Pin,
# igual que en cualquier ejemplo de SPI maestro con MicroPython.
spi_a_esclavo = SPI(2, baudrate=1000000, polarity=0, phase=0,
                     sck=Pin(18), mosi=Pin(23), miso=Pin(19))
cs_esclavo = Pin(5, Pin.OUT)
cs_esclavo.value(1)  # CS en reposo en alto (activo en bajo)

print("ESP-A listo, esperando 'DIGIT:n' por USB...")

while True:
    # sys.stdin.readline() se queda esperando (bloqueado) hasta que
    # llegue una linea completa terminada en '\n' por el mismo USB que
    # se usa para programar la placa — el mismo patron que ya usa el
    # ESP32 en el tema 4 (comando_voz) para recibir ordenes del PC.
    linea = sys.stdin.readline()
    if linea:
        digito = linea.strip()
        if digito.startswith("DIGIT:"):
            valor = int(digito.split(":", 1)[1])

            # Camino 1: UART2 (protocolo de texto, igual que antes).
            uart_a_esclavo.write((digito + "\n").encode())

            # Camino 2: SPI real, un solo byte con el CS bajado a mano
            # alrededor de la transferencia.
            cs_esclavo.value(0)
            spi_a_esclavo.write(bytes([valor]))
            cs_esclavo.value(1)

            # eco por el mismo USB: confirma que el ESP-A de verdad
            # recibio el DIGIT y lo reenvio por los dos caminos, aunque
            # todavia no dice si el ESP-B lo recibio del otro lado (para
            # eso esta el print("OLED:n") de esp_b_esclavo.ino, que se
            # revisa aparte, conectando el ESP-B directo a su propio
            # Monitor Serie de Arduino).
            print("REENVIADO:" + digito.split(":", 1)[1])
