"""El carrusel en el firmware del ESP32 fijo y en el backend real (2026-09-28).

La simulacion ya espera al carrusel (tests/sim/test_carrusel_planta.py). En el
montaje real el PC tiene que saber CUANDO llego: el firmware avisa con el
evento `carrusel/llego` (una vez por pedido, con lo que tardo de verdad) y el
backend real no da el tubo por puesto hasta ese aviso. Tambien se puede pedir
el tubo sobre el AGUJERO (antes el firmware solo sabia ponerlo en la carga)."""

import json
import sys
import types

import pytest

from app.configuracion import cargar_parametros
from app.puente_serial import EstacionEmulada, HardwareEmulado, PuenteESP32
from control import protocolo
from firmware.fijo.estacion import Estacion
from firmware.preparar import config_fijo

P = cargar_parametros()
MEDIA_VUELTA = P["tiempos_ms"]["carrusel_giro"]


class Fijo:
    def __init__(self):
        self.hw = HardwareEmulado()
        self.al_pc = []
        self.est = Estacion(self.hw, config_fijo(P), self.al_pc.append, lambda _l: None)
        self.id = 0

    def mensajes(self):
        out = [json.loads(x) for x in self.al_pc]
        self.al_pc.clear()
        return out

    def cmd(self, dst, act, t, **datos):
        self.hw.t_ms = t
        self.id += 1
        m = {"t": "cmd", "id": self.id, "dst": dst, "act": act}
        m.update(datos)
        self.est.linea_del_pc(protocolo.linea(m), t)
        return [x for x in self.mensajes() if x["t"] == "ack" and x["id"] == self.id]

    def correr(self, desde, hasta, paso=50):
        vistos = []
        for t in range(desde, hasta, paso):
            self.hw.t_ms = t
            if t % 500 == 0:
                self.est.linea_del_pc('{"t":"hb"}', t)
            self.est.tick(t)
            vistos.extend((t, m) for m in self.mensajes())
        return vistos


def _llegadas(vistos):
    return [(t, m) for t, m in vistos if m.get("src") == "carrusel" and m.get("ev") == "llego"]


def test_el_firmware_avisa_cuando_el_carrusel_llego_y_no_antes():
    f = Fijo()
    f.correr(0, 1000)                                   # oye al PC: sale de la parada segura
    ack = f.cmd("carrusel", "ir", 1000, tubo=3)          # tubo opuesto: media vuelta
    assert ack and ack[0]["ok"]
    vistos = f.correr(1000, 1000 + MEDIA_VUELTA + 400)
    llegadas = _llegadas(vistos)
    assert len(llegadas) == 1                            # una sola vez por pedido
    t, m = llegadas[0]
    assert t >= 1000 + MEDIA_VUELTA and m["tubo"] == 3 and m["lugar"] == "carga"
    assert MEDIA_VUELTA <= m["giro_ms"] <= MEDIA_VUELTA + 100
    # Mientras giraba, la telemetria lo decia.
    tel = [m for t, m in vistos if m["t"] == "tel" and t < 1000 + MEDIA_VUELTA]
    assert tel and all(m["carrusel_mov"] for m in tel)


def test_el_tubo_sobre_el_agujero_y_lugar_invalido():
    f = Fijo()
    f.correr(0, 1000)
    assert f.cmd("carrusel", "ir", 1000, tubo=2, lugar="agujero")[0]["ok"]
    llegadas = _llegadas(f.correr(1000, 1000 + MEDIA_VUELTA + 400))
    assert llegadas and llegadas[0][1]["lugar"] == "agujero"
    # 0 -> tubo 2 sobre el agujero: |210 - 120| = 90 grados = media vuelta / 2.
    assert abs(llegadas[0][1]["giro_ms"] - MEDIA_VUELTA / 2) <= 60
    mal = f.cmd("carrusel", "ir", 9000, tubo=2, lugar="tolva")
    assert mal and mal[0]["ok"] is False


def test_backend_real_no_da_el_tubo_por_puesto_hasta_el_aviso():
    from control.hal.backend_real import BackendReal

    puente = PuenteESP32(P, puerto_serial=EstacionEmulada(P))
    puente.emulada = puente.ser
    reloj = {"t": 0}
    hw = BackendReal(puente, lambda: reloj["t"])
    for t in range(0, 1000, 20):
        reloj["t"] = t
        puente.atender(t)
    hw.carrusel_a(4, "carga")                            # 4 tubos = 120 grados (camino corto): 2,7 s
    for t in range(1000, 2000, 20):
        reloj["t"] = t
        puente.atender(t)
    assert not hw.carrusel_en(4, "carga")               # todavia girando
    for t in range(2000, 4500, 20):
        reloj["t"] = t
        puente.atender(t)
    assert hw.carrusel_en(4, "carga")
    assert not hw.carrusel_en(4, "agujero") and not hw.carrusel_en(3, "carga")
    hw.carrusel_a(4, "agujero")                          # pedido nuevo: el aviso viejo no cuenta
    assert not hw.carrusel_en(4, "agujero")


def test_hw_de_la_placa_calcula_el_agujero(monkeypatch):
    """firmware/fijo/hw.py (la clase que corre en el ESP32) con machine falso."""
    maq = types.ModuleType("machine")

    class Pin:
        OUT = 1

        def __init__(self, *a, **k):
            pass

        def value(self, v=None):
            return 0

    class Timer:
        PERIODIC = 1

        def __init__(self, n):
            pass

        def init(self, **k):
            pass

    maq.Pin, maq.Timer = Pin, Timer
    maq.PWM = maq.I2C = maq.SoftI2C = object
    pin_mod = types.ModuleType("pines")
    for k in ("ULN2003_IN1", "ULN2003_IN2", "ULN2003_IN3", "ULN2003_IN4"):
        setattr(pin_mod, k, 0)
    dist = types.ModuleType("distancia")
    dist.Laser, dist.apagar_todos = object, lambda *_: None
    monkeypatch.setitem(sys.modules, "machine", maq)
    monkeypatch.setitem(sys.modules, "pines", pin_mod)
    monkeypatch.setitem(sys.modules, "distancia", dist)
    sys.modules.pop("firmware.fijo.hw", None)
    try:
        import firmware.fijo.hw as hw
        cfg = config_fijo(P)
        car = hw.Carrusel(cfg, lambda: False)
        n = cfg["carrusel_pasos_por_vuelta"]
        car.a_tubo(1, "carga")
        assert car.objetivo == n // 6
        car.posicion = car.objetivo
        car.a_tubo(1, "agujero")
        # 210 grados antihorario desde la carga = 2389 medios pasos MENOS.
        assert (car.objetivo - (n // 6 - round(210 * n / 360))) % n == 0
        assert abs(car.objetivo - car.posicion) <= n // 2        # camino corto
    finally:
        sys.modules.pop("firmware.fijo.hw", None)


@pytest.mark.parametrize("tubo", range(6))
def test_emulado_y_modelo_puro_tardan_lo_mismo(tubo):
    """La estacion emulada (app/puente_serial.py) y control/carrusel.py dan el
    mismo tiempo de giro desde el reposo (el del firmware)."""
    from control.carrusel import CARGA, Carrusel

    hw = HardwareEmulado()
    hw.carrusel_a(tubo)
    modelo = Carrusel(range(6), MEDIA_VUELTA)
    assert abs(hw.carrusel_fin - modelo.pedir(tubo, CARGA, 0)) <= 2


def test_el_carrusel_no_gira_mientras_cae_la_moneda():
    """Revision visual 2026-09-29: el giro hacia el tubo de la SIGUIENTE moneda
    arrancaba mientras la anterior todavia caia por el canal (caia 15-37 mm
    fuera de la boca). La placa lo sabe sola: con el desvio hacia el almacen,
    la moneda cae al terminar el avance de la cinta y tarda
    `caida_moneda_tubo` en llegar al fondo; un `carrusel ir` que llega en ese
    lapso ESPERA (ack ok + `en_espera` con `espera_a: moneda`) y arranca
    despues."""
    t = P["tiempos_ms"]
    fin_caida = 1000 + t["avance_casilla_monedas"] + t["caida_moneda_tubo"]
    f = Fijo()
    f.correr(0, 1000)
    assert f.cmd("desvio", "almacen", 950)[0]["ok"]
    assert f.cmd("linea", "avanzar", 1000)[0]["ok"]
    f.hw.t_ms = 1100
    f.id += 1
    f.est.linea_del_pc(protocolo.linea({"t": "cmd", "id": f.id, "dst": "carrusel", "act": "ir", "tubo": 1}), 1100)
    msgs = f.mensajes()
    assert any(m["t"] == "ack" and m["id"] == f.id and m["ok"] for m in msgs)
    espera = [m for m in msgs if m.get("src") == "carrusel" and m.get("ev") == "en_espera"]
    assert espera and espera[0]["espera_a"] == "moneda"
    vistos = f.correr(1100, fin_caida + MEDIA_VUELTA)
    arranca = [tt for tt, m in vistos if m.get("src") == "carrusel" and m.get("ev") == "arranca"]
    assert arranca and fin_caida <= arranca[0] <= fin_caida + 50
    llegadas = _llegadas(vistos)
    assert llegadas and llegadas[0][0] >= fin_caida + MEDIA_VUELTA / 3

    # Con el desvio al rechazo no cae nada al almacen: el disco gira enseguida.
    g = Fijo()
    g.correr(0, 1000)
    assert g.cmd("desvio", "rechazo", 950)[0]["ok"]
    assert g.cmd("linea", "avanzar", 1000)[0]["ok"]
    g.hw.t_ms = 1100
    g.id += 1
    g.est.linea_del_pc(protocolo.linea({"t": "cmd", "id": g.id, "dst": "carrusel", "act": "ir", "tubo": 1}), 1100)
    assert not any(m.get("ev") == "en_espera" for m in g.mensajes())
