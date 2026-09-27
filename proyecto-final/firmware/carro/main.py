# ESP32 del CARRO: se ejecuta solo al encender. Ciclo de control a
# `control_hz` (50 Hz): leer, decidir (ControlCarro), mover, radio.

import time

from config_placa import CFG, LINEA, POSE_MUELLE
from enlaces import Radio
from hw import Hardware
from logica import CarroFirmware
from vehiculo import ControlCarro

radio = Radio()
control = ControlCarro(CFG["vehiculo"], largo_linea_m=CFG["largo_linea_m"], linea=LINEA, pose_muelle=POSE_MUELLE)
carro = CarroFirmware(Hardware(CFG), control, CFG, radio.enviar)
periodo = 1000 // CFG["vehiculo"]["control_hz"]
prox = time.ticks_ms()

while True:
    t = time.ticks_ms()
    for texto in radio.recibir():
        carro.mensaje(texto, t)
    if time.ticks_diff(t, prox) >= 0:
        prox = time.ticks_add(prox, periodo)
        carro.tick(t, periodo / 1000)
    time.sleep_ms(1)
