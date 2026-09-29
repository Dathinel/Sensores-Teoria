# ESP32 del CARRO: se ejecuta solo al encender. Ciclo de control a
# `control_hz` (50 Hz): leer, decidir (ControlCarro), mover, radio.
#
# Robustez (el carro anda solo, lejos del PC):
# - Cada vuelta del bucle va en try/except: si algo falla (un mensaje raro,
#   un sensor que tira OSError), los motores quedan en 0, se imprime el error
#   (se ve en Thonny) y el bucle SIGUE. Antes una excepcion mataba main.py y
#   las ruedas seguian con el ultimo PWM.
# - Error que se REPITE en cada vuelta: los motores se ponen en 0 cada vez,
#   pero el traceback se imprime la primera vez y despues como mucho uno cada
#   `aviso_error_cada_ms` (1 s), con cuantos se callaron (imprimir cada 1 ms
#   tambien frena el bucle).
# - Perro guardian (machine.WDT, `firmware.carro_wdt_ms`): se alimenta en cada
#   vuelta; si el bucle se traba (no una excepcion: un cuelgue), la placa se
#   reinicia sola. Se ARMA recien con el PRIMER mensaje de la estacion
#   (2026-09-29): en el ESP32 un WDT armado no se puede apagar, y subir el
#   firmware con mpremote (reset, Ctrl-C, copia de .mpy) interrumpe main.py:
#   con el perro armado desde el arranque la placa se reiniciaba a mitad de la
#   copia. Para subir el carro con la estacion ENCENDIDA puede oirla antes del
#   Ctrl-C: subirlo con la estacion apagada (o carro_wdt_ms: 0). Ojo al
#   depurar: una vez armado, detener main.py en Thonny reinicia la placa a los 2 s.

import sys
import time

from config_placa import CFG, LINEA, POSE_MUELLE
from enlaces import Radio
from hw import Hardware
from logica import CarroFirmware
from vehiculo import ControlCarro

try:
    import protocolo
except ImportError:
    from control import protocolo

hw = Hardware(CFG)
radio = Radio()
control = ControlCarro(CFG["vehiculo"], largo_linea_m=CFG["largo_linea_m"], linea=LINEA, pose_muelle=POSE_MUELLE,
                       zonas=CFG.get("zonas"))
carro = CarroFirmware(hw, control, CFG, radio.enviar)
periodo = 1000 // CFG["vehiculo"]["control_hz"]
prox = time.ticks_ms()

wdt = None                                # se arma con el primer mensaje de la estacion
wdt_ms = CFG.get("carro_wdt_ms", 0)
errores = 0
avisos = protocolo.LimiteAvisos(CFG.get("aviso_error_cada_ms", 1000))

while True:
    try:
        t = time.ticks_ms()
        # Bytes crudos: parsear_linea descarta lo que no es UTF-8 ni JSON
        # (ESP-NOW de otros grupos del salon).
        for datos in radio.recibir():
            carro.mensaje(datos, t)
        if time.ticks_diff(t, prox) >= 0:
            prox = time.ticks_add(prox, periodo)
            carro.tick(t, periodo / 1000)
    except Exception as e:                       # KeyboardInterrupt (Thonny) no entra aqui
        errores += 1
        try:
            hw.motores(0, 0, False)              # primero, quieto
        except Exception:
            pass
        if avisos.debe_avisar(time.ticks_ms()):
            print("error en el bucle del carro (", errores, ", callados:", avisos.tomar_callados(), "):")
            sys.print_exception(e)
        prox = time.ticks_add(time.ticks_ms(), periodo)
    # `latido.ultimo_oido` solo cambia con lo que es de NUESTRA estacion (logica.py):
    # un ESP-NOW de otro grupo no arma el perro.
    if wdt is None and wdt_ms > 0 and carro.latido.ultimo_oido is not None:
        from machine import WDT
        wdt = WDT(timeout=wdt_ms)
    if wdt is not None:
        wdt.feed()
    time.sleep_ms(1)
