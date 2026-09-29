"""Revision 2026-09-28: el puente serial (app/puente_serial.py) no pierde una linea que llega
partida entre dos vueltas. Con `readline()` y timeout=0 la media linea se contaba como "mala" y se
perdia (y el resto tambien). Se prueba con el puerto de pyserial `loop://` (lo que se escribe se
lee), sin placa."""

import serial

from app.configuracion import cargar_parametros
from app.puente_serial import EstacionEmulada, PuenteESP32


def _puente_loop():
    ser = serial.serial_for_url("loop://", timeout=0)
    p = PuenteESP32(cargar_parametros(), puerto_serial=ser)
    p.latido.debe_enviar(0)       # que su latido no se escriba en el loop durante la prueba
    return p, ser


def test_una_linea_en_dos_trozos_llega_entera():
    p, ser = _puente_loop()
    ser.write(b'{"t":"evt","n":1,"src":"linea","ev":"pa')
    p.atender(10)
    assert p.eventos == [] and p.lineas_malas == 0          # media linea: se espera el resto
    ser.write(b'so","casilla":3}\n{"t":"tel","n":2,"linea":"run"}\n')
    p.atender(20)
    assert [e["ev"] for e in p.eventos if e.get("src") == "linea"] == ["paso"]
    assert p.tel.get("linea") == "run" and p.lineas_malas == 0
    assert p.secuencia.perdidos == 0
    p.cerrar()


def test_la_basura_se_cuenta_y_no_tapa_lo_siguiente():
    p, ser = _puente_loop()
    ser.write(b'xx basura \x00\xff\n{"t":"evt","n":1,"src":"e2","ev":"material"}\n')
    p.atender(10)
    assert p.lineas_malas == 1
    assert [e["ev"] for e in p.eventos if e.get("src") == "e2"] == ["material"]
    p.cerrar()


def test_la_estacion_emulada_se_lee_igual_que_un_puerto_real():
    em = EstacionEmulada(cargar_parametros())
    em._salida = [b'{"a":1}\n', b'{"b":2}\n']
    assert em.read(3) == b'{"a' and em.read(100) == b'":1}\n{"b":2}\n' and em.in_waiting == 0
