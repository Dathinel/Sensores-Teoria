# ESP32 FIJO: se ejecuta solo al encender (main.py en la raiz de la placa).
# Bucle sin delay() largos: cada vuelta drena el USB y la radio, deja que la
# estacion decida y le da ~2 ms al resto. Toda la logica esta en estacion.py.

import time

from config_placa import CFG
from enlaces import SerialUSB, Radio
from estacion import Estacion
from hw import Hardware

usb = SerialUSB()
radio = Radio()
estacion = Estacion(Hardware(CFG), CFG, usb.enviar, radio.enviar)

while True:
    t = time.ticks_ms()
    for linea in usb.lineas():
        estacion.linea_del_pc(linea, t)
    for texto in radio.recibir():
        estacion.mensaje_del_carro(texto, t)
    estacion.tick(t)
    time.sleep_ms(2)
