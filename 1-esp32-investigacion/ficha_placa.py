# Comprueba en la placa real los datos de la ficha tecnica del README.
# Se corre desde Thonny (F5) con MicroPython instalado; no necesita nada
# conectado a los pines. Todo lo que imprime lo lee el propio chip.

import esp
import esp32
import gc
import machine
import os
import time
import binascii
from machine import ADC, DAC, Pin

print("== Chip y firmware")
# os.uname() dice que firmware corre y para que chip se compilo.
info = os.uname()
print("Firmware:", info.release, "| maquina:", info.machine)
# La frecuencia de la CPU es configurable (80, 160 o 240 MHz); MicroPython
# arranca en 160 MHz y aqui se sube a 240 para confirmar el maximo de la ficha.
print("CPU a", machine.freq() // 1000000, "MHz")
machine.freq(240000000)
print("CPU subida a", machine.freq() // 1000000, "MHz")
# El identificador unico sale de la MAC grabada de fabrica.
print("ID unico:", binascii.hexlify(machine.unique_id()).decode())

print("== Memoria")
# La flash externa (4 MB en el WROOM-32) guarda el firmware y los archivos.
print("Flash:", esp.flash_size() // (1024 * 1024), "MB")
# De los 520 KB de SRAM, el sistema y el Wi-Fi reservan una parte y el
# interprete otra: lo que queda libre para el programa es bastante menos.
gc.collect()
print("RAM libre para Python:", gc.mem_free() // 1024, "KB")
fs = os.statvfs("/")
print("Sistema de archivos:", fs[0] * fs[3] // 1024, "KB libres de", fs[0] * fs[2] // 1024, "KB")

print("== Sensores internos")
try:
    # Temperatura interna en grados Fahrenheit y poco precisa: sirve para ver
    # tendencias (si el chip se calienta), no como termometro.
    f = esp32.raw_temperature()
    print("Temperatura interna: %d F (~%.0f C)" % (f, (f - 32) / 1.8))
except AttributeError:
    print("Este firmware no expone raw_temperature()")

print("== ADC (12 bits) y DAC (8 bits)")
# GPIO34 es solo entrada y pertenece al ADC1 (el que funciona con Wi-Fi).
# ATTN_11DB amplia el rango de medida hasta ~3,3 V; sin atenuacion llegaria
# solo a ~1,1 V. Suelto, el pin "flota" y da valores al azar: normal.
adc = ADC(Pin(34))
adc.atten(ADC.ATTN_11DB)
print("ADC GPIO34 (0-4095):", [adc.read() for _ in range(5)])
# GPIO25 es uno de los dos DAC: 0-255 -> 0-3,3 V. Si se une con un cable
# GPIO25 a GPIO34, el ADC deberia leer cerca de 128/255*4095 ~ 2000.
dac = DAC(Pin(25))
dac.write(128)
time.sleep_ms(10)
print("DAC GPIO25 en 128 -> ADC GPIO34 lee:", adc.read(), "(cerca de 2000 solo si estan unidos)")

print("== Tactil")
# GPIO4 es el canal tactil T0: al tocarlo con el dedo el valor BAJA.
tactil = machine.TouchPad(Pin(4))
print("Tactil GPIO4 (tocar el pin y volver a correr):", tactil.read())
