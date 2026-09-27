"""Fase 8: firmware de los dos ESP32 probado en el PC.

La logica de cada placa (firmware/fijo/estacion.py, firmware/carro/logica.py)
no toca pines: aqui corre con un hardware falso. La del carro usa el MISMO
ControlCarro de la simulacion. Y todo lo que va a la placa se compila con
mpy-cross (el compilador de MicroPython): si algo no es MicroPython valido,
falla aqui y no en el ESP32."""

import json
import math

import pytest

from app.configuracion import cargar_parametros
from app.puente_serial import EstacionEmulada, HardwareEmulado, PuenteESP32
from control import protocolo
from control.vehiculo import ControlCarro, LecturaCarro
from firmware.carro.logica import CarroFirmware
from firmware.fijo.estacion import Estacion
from firmware.preparar import config_carro, config_fijo, pines, preparar

P = cargar_parametros()


# ---------------------------------------------------------------------
# lo que va a la placa
# ---------------------------------------------------------------------


def test_pines_salen_del_conexionado():
    fijo, carro = pines("fijo"), pines("carro")
    assert fijo["DRIVERS_M_STEP"] == 25 and fijo["VL53_CORTINA_XSHUT"] == 19 and fijo["HALL_S"] == 39
    assert carro["TB6612_PWMA"] == 25 and carro["IR_LINEA_OUT3"] == 36 and carro["HCSR04_ECHO"] == 23
    assert len(set(fijo.values())) == len(fijo) and len(set(carro.values())) == len(carro)   # sin pines repetidos


@pytest.mark.parametrize("placa", ["fijo", "carro"])
def test_todo_compila_para_micropython(placa, tmp_path, monkeypatch):
    pytest.importorskip("mpy_cross")
    import firmware.preparar as prep

    monkeypatch.setattr(prep, "SALIDA", tmp_path)
    d = preparar(placa, P, descargar=False)       # sin internet: sin el driver del VL53L0X
    nombres = {f.name for f in d.iterdir()}
    assert "main.py" in nombres and "protocolo.mpy" in nombres and "config_placa.mpy" in nombres
    if placa == "carro":
        assert "vehiculo.mpy" in nombres           # el ControlCarro de la simulacion va al ESP32


# ---------------------------------------------------------------------
# ESP32 fijo
# ---------------------------------------------------------------------


class Fijo:
    def __init__(self):
        self.hw = HardwareEmulado()
        self.al_pc, self.al_carro = [], []
        self.est = Estacion(self.hw, config_fijo(P), self.al_pc.append, self.al_carro.append)
        self.id = 0

    def mensajes(self):
        out = [json.loads(x) for x in self.al_pc]
        self.al_pc.clear()
        return out

    def cmd(self, dst, act, t, **datos):
        self.id += 1
        m = {"t": "cmd", "id": self.id, "dst": dst, "act": act}
        m.update(datos)
        self.est.linea_del_pc(protocolo.linea(m), t)
        return [x for x in self.mensajes() if x["t"] == "ack" and x["id"] == self.id]

    def correr(self, desde, hasta, paso=50, latido=True):
        for t in range(desde, hasta, paso):
            self.hw.t_ms = t
            if latido and t % 500 == 0:
                self.est.linea_del_pc('{"t":"hb"}', t)
            self.est.tick(t)


def test_arranca_en_parada_segura_hasta_oir_al_pc():
    f = Fijo()
    assert f.hw.servos["prensa"] == 0 and f.hw.servos["desvio"] == 0      # prensa arriba, desvio al rechazo
    assert f.cmd("linea", "avanzar", 0)[0]["ok"] is False
    f.correr(0, 600)
    ack = f.cmd("linea", "avanzar", 600)[0]
    assert ack["ok"] is True and f.hw.pasos["monedas"] == 1


def test_comando_repetido_se_confirma_pero_no_se_ejecuta_dos_veces():
    f = Fijo()
    f.correr(0, 600)
    m = protocolo.linea({"t": "cmd", "id": 7, "dst": "linea", "act": "avanzar"})
    f.est.linea_del_pc(m, 600)
    f.est.linea_del_pc(m, 700)
    acks = [x for x in f.mensajes() if x["t"] == "ack"]
    assert len(acks) == 2 and f.hw.pasos["monedas"] == 1


def test_linea_con_basura_no_la_tumba():
    f = Fijo()
    for basura in ("", "{roto", "\x00\xff", '{"sin":"tipo"}', '{"t":"cmd"}'):
        f.est.linea_del_pc(basura, 0)
    assert f.est.errores == 5                              # se cuentan todas y sigue vivo


def test_cortina_reacciona_sola_sin_esperar_al_pc():
    f = Fijo()
    f.correr(0, 600)
    f.cmd("vasos", "prensar", 600)
    assert f.hw.servos["prensa"] == 180
    f.hw.sensores["cortina_mm"] = 60                       # una mano en la zona
    f.correr(650, 700)
    assert f.hw.servos["prensa"] == 0                      # prensa ARRIBA en el mismo ciclo
    assert any(m.get("ev") == "cortina" and m["activa"] for m in f.mensajes())
    assert "cortina" in f.cmd("vasos", "avanzar", 700)[0]["error"]
    assert f.cmd("linea", "avanzar", 700)[0]["ok"]         # la cinta de monedas sigue


def test_sin_latido_del_pc_para_seguro():
    f = Fijo()
    f.correr(0, 1000)
    f.cmd("linea", "avanzar", 1000)
    f.correr(1000, 3500, latido=False)
    assert f.est.parada_segura and not f.hw.fin            # cintas quietas
    assert any(m.get("ev") == "parada_segura" for m in f.mensajes())


def test_puente_con_el_carro_ack_y_sin_repetidos():
    f = Fijo()
    evt = protocolo.linea({"t": "evt", "src": "carro", "id": 5, "ev": "meta"})
    f.est.mensaje_del_carro(evt, 100)
    f.est.mensaje_del_carro(evt, 200)                      # reenvio: su ack se perdio
    acks = [json.loads(x) for x in f.al_carro if '"ack"' in x]
    assert len(acks) == 2 and acks[0]["dst"] == "carro" and acks[0]["id"] == 5
    assert [m["ev"] for m in f.mensajes() if m.get("src") == "carro"] == ["meta"]   # al PC una sola vez


# ---------------------------------------------------------------------
# ESP32 del carro (ControlCarro de verdad, hardware falso)
# ---------------------------------------------------------------------


class HwCarro:
    def __init__(self):
        self.motores_pedidos = (0, 0)

    def leer(self):
        return LecturaCarro((0, 0, 1, 0, 0), None, 0, 0, 0, None, 0, False)

    def motores(self, i, d, bajo):
        self.motores_pedidos = (i, d)


def _carro():
    cfg, linea, pose = config_carro(P)
    control = ControlCarro(cfg["vehiculo"], largo_linea_m=cfg["largo_linea_m"], linea=linea, pose_muelle=pose)
    salida = []
    return CarroFirmware(HwCarro(), control, cfg, salida.append), salida


def test_orden_por_radio_llega_al_control_y_responde():
    c, salida = _carro()
    c.mensaje('{"t":"hb","src":"estacion"}', 0)
    c.mensaje(protocolo.linea({"t": "cmd", "id": 3, "dst": "carro", "act": "girar", "grados": 90}), 0)
    c.mensaje(protocolo.linea({"t": "cmd", "id": 3, "dst": "carro", "act": "girar", "grados": 90}), 10)
    resp = [json.loads(x) for x in salida if "respuesta_orden" in x]
    assert len(resp) == 1 and resp[0]["ok"] and "sale del muelle" in resp[0]["detalle"]
    assert c.control.estado == "manual"


def test_eventos_numerados_se_reenvian_hasta_el_ack():
    c, salida = _carro()
    c.mensaje('{"t":"hb","src":"estacion"}', 0)
    c.control.ordenar({"accion": "detener"})
    c.tick(0, 0.02)
    ids = [json.loads(x)["id"] for x in salida if '"evt"' in x]
    assert ids                                             # el evento "orden" salio numerado
    salida.clear()
    c.tick(600, 0.02)                                      # sin ack: se reenvia
    assert any(json.loads(x).get("id") == ids[0] for x in salida)
    c.mensaje(protocolo.linea({"t": "ack", "dst": "carro", "id": ids[0], "ok": True}), 650)
    assert ids[0] not in c.emisor.pendientes


def test_sin_radio_el_carro_lo_sabe():
    c, _ = _carro()
    c.mensaje('{"t":"hb","src":"estacion"}', 0)
    c.tick(100, 0.02)
    assert c.control.enlace_vivo
    c.tick(1500, 0.02)                                     # 1,5 s sin oir a la estacion
    assert not c.control.enlace_vivo


# ---------------------------------------------------------------------
# PC <-> ESP32 fijo, de punta a punta (el firmware de verdad, emulado)
# ---------------------------------------------------------------------


def test_puente_de_punta_a_punta_con_la_estacion_emulada():
    puente = PuenteESP32(P, puerto_serial=EstacionEmulada(P))
    puente.emulada = puente.ser                            # que el puente haga correr su reloj
    for t in range(0, 1200, 20):
        puente.atender(t)
    i = puente.comando("linea", "avanzar", 1200)
    for t in range(1200, 2000, 20):
        puente.atender(t)
    assert puente.respuestas[i]["ok"] is True
    assert puente.tel["t"] == "tel" and puente.secuencia.perdidos == 0
    assert puente.ultima_linea_cruda.startswith("{")
    assert puente.ser.hw.pasos["monedas"] == 1


def test_sin_esp32_no_se_cae():
    puente = PuenteESP32(P, puerto="COM_QUE_NO_EXISTE_99")
    assert puente.conectado is False and puente.emulada is not None
