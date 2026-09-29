# ESP32 FIJO: se ejecuta solo al encender (main.py en la raiz de la placa).
# Bucle sin delay() largos: cada vuelta drena el USB y la radio, deja que la
# estacion decida y le da ~2 ms al resto. Toda la logica esta en estacion.py.
#
# Robustez (mismo patron que firmware/carro/main.py):
# - Cada vuelta del bucle va en try/except: si algo falla (un mensaje raro,
#   un OSError del I2C, un error de programacion), la estacion hace su
#   PARADA SEGURA con motivo "error" (cintas quietas, prensa arriba, desvio al
#   rechazo, escapes cerrados, carrusel frenado), se imprime el error (se ve
#   en Thonny) y el bucle SIGUE: sigue mandando latido y telemetria, y el PC
#   ve `parada_segura` con su motivo. Antes una excepcion mataba main.py con
#   las cintas y los servos en su ultimo estado. La parada por error queda
#   enclavada: sale con `estado.reanudar` (Iniciar/Reanudar del dashboard).
# - Error que se REPITE en cada vuelta (un sensor muerto): la parada segura se
#   aplica en cada vuelta, pero el evento y el traceback salen la primera vez y
#   despues como mucho uno cada `aviso_error_cada_ms` (1 s), con cuantos se
#   callaron (`repetidos`). Antes eran ~500 lineas por segundo al USB (y el PC
#   las guardaba todas en SQLite).
# - Perro guardian (machine.WDT, `firmware.fijo_wdt_ms`): se alimenta en cada
#   vuelta; si el bucle se TRABA (no una excepcion: un cuelgue), la placa se
#   reinicia sola y arranca en parada segura. Se ARMA recien con el PRIMER
#   latido del PC (2026-09-29): en el ESP32 un WDT armado ya no se puede
#   apagar, y `python -m firmware.subir` (mpremote: reset por DTR, Ctrl-C y la
#   copia de varios .mpy) interrumpe main.py; con el perro armado desde el
#   arranque, la placa se reiniciaba a los 2 s A MITAD de la copia. mpremote
#   nunca manda un latido `{"t":"hb"}`, asi que con el reset del inicio de la
#   subida el perro queda sin armar. Ojo al depurar: una vez que el PC hablo,
#   detener main.py en Thonny reinicia la placa (fijo_wdt_ms: 0 para depurar).

import sys
import time

from config_placa import CFG
from enlaces import SerialUSB, Radio
from estacion import Estacion
from hw import Hardware

try:
    import protocolo                      # en el ESP32: protocolo.mpy en la raiz
except ImportError:                       # en el PC (pruebas)
    from control import protocolo

hw = Hardware(CFG)
usb = SerialUSB()
radio = Radio()
estacion = Estacion(hw, CFG, usb.enviar, radio.enviar)

wdt = None                                # se arma con el primer latido del PC (ver arriba)
wdt_ms = CFG.get("fijo_wdt_ms", 0)
errores = 0
avisos = protocolo.LimiteAvisos(CFG.get("aviso_error_cada_ms", 1000))

while True:
    try:
        t = time.ticks_ms()
        for linea in usb.lineas():
            estacion.linea_del_pc(linea, t)
        for texto in radio.recibir():
            estacion.mensaje_del_carro(texto, t)
        estacion.tick(t)
    except Exception as e:                       # KeyboardInterrupt (Thonny) no entra aqui
        errores += 1
        try:
            estacion.aplicar_parada_segura("error", time.ticks_ms())   # primero, todo a seguro
        except Exception:
            try:
                hw.detener_cintas()              # si ni la parada completa se pudo: al menos las cintas
            except Exception:
                pass
        if avisos.debe_avisar(time.ticks_ms()):
            try:
                estacion.evento("esp32", "parada_segura", time.ticks_ms(),
                                {"motivo": "error", "error": str(e)[:60], "errores": errores,
                                 "repetidos": avisos.tomar_callados()})
            except Exception:
                pass
            print("error en el bucle del fijo (", errores, "):")
            sys.print_exception(e)
    if wdt is None and wdt_ms > 0 and estacion.pc_latidos > 0:
        from machine import WDT
        wdt = WDT(timeout=wdt_ms)
    if wdt is not None:
        wdt.feed()
    time.sleep_ms(2)
