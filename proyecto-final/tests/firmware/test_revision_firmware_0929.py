"""Segunda revision logica del firmware (2026-09-29). Cada prueba de aqui
FALLABA con el firmware anterior (ver docs/bitacora.md, entrada del
2026-09-29): se reproduce el caso con la estacion (firmware/fijo/estacion.py)
o el main.py real de cada placa, con hardware y modulos falsos."""

import json
import runpy
import sys
import types
from pathlib import Path

import pytest

from app.configuracion import cargar_parametros
from app.puente_serial import EstacionEmulada, HardwareEmulado, PuenteESP32
from control import protocolo
from control.vehiculo import ControlCarro, LecturaCarro
from firmware.carro.logica import CarroFirmware
from firmware.fijo.estacion import Estacion
from firmware.preparar import config_carro, config_fijo

P = cargar_parametros()
RAIZ = Path(__file__).resolve().parents[2]
MEDIA_VUELTA = P["tiempos_ms"]["carrusel_giro"]


class Fijo:
    def __init__(self, hw=None):
        self.hw = hw or HardwareEmulado()
        self.al_pc, self.al_carro = [], []
        self.est = Estacion(self.hw, config_fijo(P), self.al_pc.append, self.al_carro.append)
        self.id = 0

    def mensajes(self):
        out = [json.loads(x) for x in self.al_pc]
        self.al_pc.clear()
        return out

    def mandar(self, m, t):
        self.hw.t_ms = t
        self.est.linea_del_pc(protocolo.linea(m), t)

    def cmd(self, dst, act, t, **datos):
        self.id += 1
        m = {"t": "cmd", "id": self.id, "dst": dst, "act": act}
        m.update(datos)
        self.mandar(m, t)
        msgs = self.mensajes()
        return [x for x in msgs if x["t"] == "ack" and x["id"] == self.id][0], msgs

    def correr(self, desde, hasta, paso=50):
        vistos = []
        for t in range(desde, hasta, paso):
            self.hw.t_ms = t
            if t % 500 == 0:
                self.est.linea_del_pc('{"t":"hb"}', t)
            self.est.tick(t)
            vistos.extend(self.mensajes())
        return vistos


def _carro_dice(f, emisor, t, **evt):
    m = {"t": "evt", "src": "carro"}
    m.update(evt)
    f.est.mensaje_del_carro(protocolo.linea(emisor.enviar(m, t)), t)


def _ordenes_al_carro(f):
    return [json.loads(x) for x in f.al_carro if '"cmd"' in x]


# --- 1. una orden RECHAZADA por el carro no lo saca del muelle ---


def test_orden_rechazada_por_el_carro_no_bloquea_la_canaleta():
    """Bug: el fijo ponia en_muelle=False al reenviar la orden, ANTES de que el
    carro la validara. Si el carro la rechazaba (solo manda respuesta_orden
    ok:false) seguia quieto en el muelle y nunca volvia a decir en_muelle:
    todos los canaleta.soltar siguientes daban `no_esta_en_muelle`."""
    f = Fijo()
    carro = protocolo.Emisor(500, None, sesion=10)
    f.correr(0, 600)
    _carro_dice(f, carro, 600, ev="en_muelle", cuna=False)
    f.cmd("carro", "avanzar", 610, distancia_m=9.0)          # fuera de rango: el carro la rechaza
    orden = _ordenes_al_carro(f)[-1]["id"]
    _carro_dice(f, carro, 640, ev="respuesta_orden", orden=orden, ok=False, detalle="fuera de rango", cuna=False)
    ack, _ = f.cmd("canaleta", "soltar", 650)
    assert ack["ok"] is True, ack                             # sigue en el muelle: suelta el vaso


def test_orden_aceptada_si_saca_al_carro_del_muelle():
    f = Fijo()
    carro = protocolo.Emisor(500, None, sesion=10)
    f.correr(0, 600)
    _carro_dice(f, carro, 600, ev="en_muelle", cuna=False)
    f.cmd("carro", "avanzar", 610, distancia_m=0.3)
    assert "no_esta_en_muelle" in f.cmd("canaleta", "soltar", 620)[0]["error"]   # entre orden y respuesta: seguro
    orden = _ordenes_al_carro(f)[-1]["id"]
    _carro_dice(f, carro, 640, ev="respuesta_orden", orden=orden, ok=True, detalle="avanza", cuna=False)
    assert "no_esta_en_muelle" in f.cmd("canaleta", "soltar", 650)[0]["error"]


def test_rechazo_no_pisa_un_estado_mas_nuevo_del_carro():
    """Si entre la orden y su rechazo el carro dijo algo nuevo de si mismo
    (salio por su cuenta), vale lo nuevo: no se restaura el muelle viejo."""
    f = Fijo()
    carro = protocolo.Emisor(500, None, sesion=10)
    f.correr(0, 600)
    _carro_dice(f, carro, 600, ev="en_muelle", cuna=False)
    f.cmd("carro", "girar", 610, grados=30)
    orden = _ordenes_al_carro(f)[-1]["id"]
    _carro_dice(f, carro, 620, ev="salida", cuna=True)
    _carro_dice(f, carro, 630, ev="respuesta_orden", orden=orden, ok=False, detalle="x", cuna=True)
    assert f.est.estado_carro["en_muelle"] is False


# --- 9. la orden al carro se reintenta hasta su respuesta ---


def test_orden_al_carro_se_reintenta_y_avisa_si_no_contesta():
    """Bug: el fijo mandaba la orden por ESP-NOW UNA vez; si el paquete se
    perdia, la orden desaparecia sin aviso (el reenvio del PC se descartaba
    como repetido porque el fijo ya la habia confirmado)."""
    f = Fijo()
    f.correr(0, 600)
    f.al_carro.clear()
    f.cmd("carro", "avanzar", 600, distancia_m=0.3)
    vistos = f.correr(650, 4000)
    copias = [m for m in _ordenes_al_carro(f) if m["act"] == "avanzar"]
    assert len(copias) == P["protocolo"]["carro_orden_intentos"]       # la primera + los reintentos
    assert len({m["id"] for m in copias}) == 1                          # el mismo id: el carro no la repite
    avisos = [m for m in vistos if m.get("ev") == "carro_sin_respuesta"]
    assert len(avisos) == 1 and avisos[0]["act"] == "avanzar"


def test_orden_contestada_no_se_reintenta_y_el_carro_no_la_ejecuta_dos_veces():
    f = Fijo()
    cfg, linea, pose = config_carro(P)
    control = ControlCarro(cfg["vehiculo"], largo_linea_m=cfg["largo_linea_m"], linea=linea, pose_muelle=pose,
                           zonas=cfg["zonas"])
    radio_carro = []
    carro = CarroFirmware(types.SimpleNamespace(), control, cfg, radio_carro.append)
    f.correr(0, 600)
    f.al_carro.clear()
    f.cmd("carro", "girar", 600, grados=45)
    perdido = f.al_carro.pop()                                          # el primer paquete se pierde
    assert '"girar"' in perdido
    f.correr(650, 1200)                                                 # el fijo lo reintenta...
    reintento = [x for x in f.al_carro if '"girar"' in x]
    assert reintento
    carro.mensaje(reintento[0], 1150)                                   # ...y ese si llega
    for x in reintento[1:]:
        carro.mensaje(x, 1160)                                          # copias de mas: no se ejecutan otra vez
    respuestas = [x for x in radio_carro if "respuesta_orden" in x]
    assert len(respuestas) == 1
    f.est.mensaje_del_carro(respuestas[0], 1170)
    f.al_carro.clear()
    vistos = f.correr(1200, 4000)
    assert not [x for x in f.al_carro if '"girar"' in x]                # ya contesto: no se reintenta
    assert not [m for m in vistos if m.get("ev") == "carro_sin_respuesta"]


# --- 3. una excepcion a mitad de un comando: ack ok:false y el id no queda "visto" ---


class HwI2CFlojo(HardwareEmulado):
    def __init__(self):
        super().__init__()
        self.roto = False

    def servo(self, nombre, angulo):
        if self.roto and nombre == "prensa" and angulo != 0:     # bajar falla; volver a reposo (0) si anda
            raise OSError("PCA9685 sin respuesta")
        super().servo(nombre, angulo)


def test_excepcion_en_un_comando_da_ack_falso_y_el_reenvio_no_da_ok_sin_ejecutar():
    """Bug: `receptor.recibir` marcaba el id ANTES de `_ejecutar`; si este
    lanzaba (OSError del PCA9685) no salia ack, y el reenvio del PC recibia
    ack ok:true sin que nada se hubiera ejecutado."""
    hw = HwI2CFlojo()
    f = Fijo(hw)
    f.correr(0, 600)
    hw.roto = True
    m = {"t": "cmd", "id": 50, "dst": "vasos", "act": "prensar"}
    with pytest.raises(OSError):
        f.mandar(m, 600)                                  # la excepcion sigue hacia main.py
    acks = [x for x in f.mensajes() if x["t"] == "ack"]
    assert len(acks) == 1 and acks[0]["ok"] is False and "PCA9685" in acks[0]["error"]
    # main.py hace la parada segura por error; el PC reenvia (su ack pudo perderse).
    f.est.aplicar_parada_segura("error", 610)
    f.mandar(m, 620)
    ack = [x for x in f.mensajes() if x["t"] == "ack"][0]
    assert ack["ok"] is False and "error" in ack["error"]          # NO un "ok" sin haber prensado
    # Arreglado el cable y reanudada la placa, el mismo id se ejecuta de verdad.
    hw.roto = False
    f.cmd("estado", "reanudar", 700)
    f.mandar(m, 710)
    ack = [x for x in f.mensajes() if x["t"] == "ack"][0]
    assert ack["ok"] is True and hw.servos["prensa"] == P["firmware"]["servos"]["prensa"]["activo"]


# --- 7. carrusel y obturador no se estorban ---


def test_obturador_espera_a_que_el_carrusel_pare():
    """Bug: la placa abria el obturador con el disco girando (el lote caeria
    entre dos tubos)."""
    f = Fijo()
    f.correr(0, 600)
    f.cmd("carrusel", "ir", 600, tubo=3)
    ack, msgs = f.cmd("carrusel", "abrir", 700)
    assert ack["ok"] is True                                        # se acepta, pero espera
    assert f.hw.servos.get("obturador", 0) == 0
    assert any(m.get("ev") == "obturador" and m.get("ciclo") == "en_espera" and m.get("espera_a") == "carrusel"
               for m in msgs)
    vistos = f.correr(750, 600 + MEDIA_VUELTA + 300, paso=10)
    llego = [i for i, m in enumerate(vistos) if m.get("ev") == "llego"][0]
    arranca = [i for i, m in enumerate(vistos) if m.get("ev") == "obturador" and m.get("ciclo") == "arranca"][0]
    assert arranca > llego                                          # abre DESPUES de que el disco paro


def test_carrusel_espera_a_que_el_obturador_cierre():
    """Bug: `carrusel.ir` giraba el disco con el obturador abierto."""
    f = Fijo()
    f.correr(0, 600)
    f.cmd("carrusel", "abrir", 600)
    assert f.hw.servos["obturador"] == P["firmware"]["servos"]["obturador"]["activo"]
    ack, msgs = f.cmd("carrusel", "ir", 650, tubo=2)
    assert ack["ok"] is True and not f.hw.carrusel_moviendose()
    assert any(m.get("src") == "carrusel" and m.get("ev") == "en_espera" for m in msgs)
    assert "obturador" in f.cmd("carrusel", "referencia", 660)[0]["error"]
    ciclo = P["tiempos_ms"]["compuerta_tubo"]
    vistos = f.correr(700, 600 + ciclo + 200, paso=10)
    assert any(m.get("src") == "carrusel" and m.get("ev") == "arranca" for m in vistos)
    assert f.hw.carrusel_moviendose() and f.hw.carrusel == 2


# --- 8. `llego` lleva el id del pedido y el backend lo compara ---


def test_backend_no_cree_un_llego_de_otro_pedido():
    from control.hal.backend_real import BackendReal

    puente = PuenteESP32(P, puerto_serial=EstacionEmulada(P))
    puente.emulada = puente.ser
    reloj = {"t": 0}
    hw = BackendReal(puente, lambda: reloj["t"])
    for t in range(0, 1000, 20):
        reloj["t"] = t
        puente.atender(t)
    hw.carrusel_a(4, "carga")
    # El aviso de un giro ANTERIOR al mismo tubo llega tarde por el serial.
    puente.eventos.append({"t": "evt", "src": "carrusel", "ev": "llego", "tubo": 4, "lugar": "carga",
                           "pedido": hw._carrusel["pedido"] - 1})
    assert not hw.carrusel_en(4, "carga")
    for t in range(1000, 4500, 20):
        reloj["t"] = t
        puente.atender(t)
    llegadas = [e for e in puente.eventos if e.get("ev") == "llego" and "giro_ms" in e]
    assert llegadas and llegadas[-1]["pedido"] == hw._carrusel["pedido"]
    assert hw.carrusel_en(4, "carga")


# --- 6 (placa). la pausa del PC queda enclavada ---


def test_la_pausa_del_pc_no_se_levanta_sola_al_volver_el_latido():
    f = Fijo()
    f.correr(0, 600)
    f.cmd("estado", "parar", 600, motivo="pausa")
    assert f.est.motivo_parada == "pausa"
    f.hw.t_ms = 700
    for t in range(700, 3700, 50):                                  # cable suelto: sin latido
        f.hw.t_ms = t
        f.est.tick(t)
    f.correr(3700, 5000)                                            # vuelve
    assert f.est.parada_segura and f.est.motivo_parada == "pausa"
    assert "pausa" in f.cmd("linea", "avanzar", 5000)[0]["error"]
    assert f.cmd("estado", "reanudar", 5000)[0]["ok"] and not f.est.parada_segura


def test_un_paro_sobre_una_pausa_queda_como_paro():
    f = Fijo()
    f.correr(0, 600)
    f.cmd("estado", "parar", 600, motivo="pausa")
    f.cmd("estado", "parar", 610)
    assert f.est.motivo_parada == "paro"
    f.cmd("estado", "parar", 620, motivo="pausa")                   # no se rebaja
    assert f.est.motivo_parada == "paro"


# --- 2 y 4. main.py: perro armado con el primer latido; errores repetidos limitados ---


class _FinBucle(BaseException):
    pass


def _correr_main_fijo(monkeypatch, lineas_por_vuelta, vueltas, paso_ms=20):
    """Corre firmware/fijo/main.py de verdad con modulos falsos. Devuelve
    (wdts creados, alimentaciones, mensajes al PC)."""
    cfg = config_fijo(P)
    reloj = {"t": 0, "vueltas": 0}
    wdts, alimentado, al_pc, hws = [], [], [], []

    class Hardware(HardwareEmulado):
        def __init__(self, cfg_):
            super().__init__()
            hws.append(self)

    class SerialUSB:
        def enviar(self, texto):
            al_pc.append(texto)

        def lineas(self):
            return lineas_por_vuelta(reloj["vueltas"])

    class Radio:
        def enviar(self, texto):
            return True

        def recibir(self):
            return []

    class WDT:
        def __init__(self, timeout):
            wdts.append((reloj["vueltas"], timeout))

        def feed(self):
            alimentado.append(reloj["vueltas"])

    def sleep_ms(ms):
        reloj["t"] += paso_ms
        reloj["vueltas"] += 1
        if hws:
            hws[0].t_ms = reloj["t"]
        if reloj["vueltas"] >= vueltas:
            raise _FinBucle

    tiempo = types.SimpleNamespace(ticks_ms=lambda: reloj["t"], ticks_diff=lambda a, b: a - b,
                                   ticks_add=lambda a, b: a + b, sleep_ms=sleep_ms)
    modulos = {"time": tiempo, "config_placa": types.SimpleNamespace(CFG=cfg),
               "enlaces": types.SimpleNamespace(SerialUSB=SerialUSB, Radio=Radio),
               "estacion": types.SimpleNamespace(Estacion=Estacion),
               "hw": types.SimpleNamespace(Hardware=Hardware), "machine": types.SimpleNamespace(WDT=WDT)}
    for k, v in modulos.items():
        monkeypatch.setitem(sys.modules, k, v)
    monkeypatch.setattr(sys, "print_exception", lambda e: None, raising=False)
    with pytest.raises(_FinBucle):
        runpy.run_path(str(RAIZ / "firmware" / "fijo" / "main.py"), run_name="__main__")
    return wdts, alimentado, [json.loads(x) for x in al_pc]


def test_main_del_fijo_arma_el_perro_recien_con_el_primer_latido(monkeypatch):
    """Bug: el WDT se armaba al arrancar main.py; `python -m firmware.subir`
    (mpremote: Ctrl-C y copia de .mpy) interrumpe main.py y el perro reiniciaba
    la placa A MITAD de la copia. mpremote nunca manda un latido."""

    def lineas(v):
        if v < 50:
            return ["\x03\x03", "\x01", "import os"]       # lo que manda mpremote: no es un latido
        return ['{"t":"hb"}'] if v == 50 else []

    wdts, alimentado, _ = _correr_main_fijo(monkeypatch, lineas, 60)
    assert wdts == [(50, P["firmware"]["fijo_wdt_ms"])]      # un solo perro, armado con el latido
    assert alimentado and min(alimentado) == 50 and len(alimentado) == 10


def test_main_del_fijo_no_inunda_el_usb_con_un_error_repetido(monkeypatch):
    """Bug: una excepcion que se repite en cada vuelta (~2 ms) mandaba un
    evento parada_segura por vuelta: ~500 lineas/s al USB y a SQLite."""

    def lineas(v):
        if v == 0:
            return ['{"t":"hb"}']
        raise OSError("I2C muerto")

    _, _, msgs = _correr_main_fijo(monkeypatch, lineas, 1500, paso_ms=2)   # 3 s de errores
    avisos = [m for m in msgs if m.get("ev") == "parada_segura" and m.get("motivo") == "error"]
    assert 3 <= len(avisos) <= 4                                    # la primera + 1 por segundo
    assert avisos[1]["repetidos"] > 400 and avisos[-1]["errores"] >= 1000


def _correr_main_carro(monkeypatch, radio_por_vuelta, vueltas, paso_ms=20):
    cfg, linea, pose = config_carro(P)
    reloj = {"t": 0, "vueltas": 0}
    wdts, alimentado, motores, impresos = [], [], [], []

    class Hardware:
        def __init__(self, cfg_):
            pass

        def leer(self):
            return LecturaCarro((0, 0, 1, 0, 0), None, 0, 0, 0, None, 0, False)

        def motores(self, i, d, bajo):
            motores.append((reloj["vueltas"], i, d))

    class Radio:
        def enviar(self, texto):
            return True

        def recibir(self):
            return radio_por_vuelta(reloj["vueltas"])

    class WDT:
        def __init__(self, timeout):
            wdts.append((reloj["vueltas"], timeout))

        def feed(self):
            alimentado.append(reloj["vueltas"])

    def sleep_ms(ms):
        reloj["t"] += paso_ms
        reloj["vueltas"] += 1
        if reloj["vueltas"] >= vueltas:
            raise _FinBucle

    tiempo = types.SimpleNamespace(ticks_ms=lambda: reloj["t"], ticks_diff=lambda a, b: a - b,
                                   ticks_add=lambda a, b: a + b, sleep_ms=sleep_ms)
    modulos = {"time": tiempo, "config_placa": types.SimpleNamespace(CFG=cfg, LINEA=linea, POSE_MUELLE=pose),
               "enlaces": types.SimpleNamespace(Radio=Radio), "hw": types.SimpleNamespace(Hardware=Hardware),
               "logica": types.SimpleNamespace(CarroFirmware=CarroFirmware),
               "vehiculo": types.SimpleNamespace(ControlCarro=ControlCarro),
               "machine": types.SimpleNamespace(WDT=WDT)}
    for k, v in modulos.items():
        monkeypatch.setitem(sys.modules, k, v)
    monkeypatch.setattr(sys, "print_exception", lambda e: impresos.append(e), raising=False)
    with pytest.raises(_FinBucle):
        runpy.run_path(str(RAIZ / "firmware" / "carro" / "main.py"), run_name="__main__")
    return wdts, alimentado, motores, impresos


def test_main_del_carro_arma_el_perro_con_el_primer_mensaje_de_la_estacion(monkeypatch):
    def radio(v):
        if v < 30:
            return [b'{"t":"hb","src":"otro_grupo"}', b"\xff basura"]   # nada de NUESTRA estacion
        return [b'{"t":"hb","src":"estacion"}'] if v == 30 else []

    wdts, alimentado, _, _ = _correr_main_carro(monkeypatch, radio, 40)
    assert wdts == [(30, P["firmware"]["carro_wdt_ms"])]
    assert min(alimentado) == 30


def test_main_del_carro_no_imprime_un_error_repetido_en_cada_vuelta(monkeypatch):
    def radio(v):
        if v == 0:
            return [b'{"t":"hb","src":"estacion"}']
        raise OSError("sensor muerto")

    _, _, motores, impresos = _correr_main_carro(monkeypatch, radio, 2500, paso_ms=1)   # 2,5 s de errores
    assert 2 <= len(impresos) <= 3                                  # no 2500 tracebacks
    assert motores[-1][1:] == (0, 0)                               # los motores siguen en 0 cada vez
