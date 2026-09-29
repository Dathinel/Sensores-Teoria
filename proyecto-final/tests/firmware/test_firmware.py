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
    # La placa vota (2026-09-28): `lecturas_por_decision` lecturas seguidas
    # (3 x 50 ms aqui; en la placa 3 x 33 ms del VL53L0X, lo que presupuesta
    # control/tiempos.py).
    f.correr(650, 650 + 50 * P["planta"]["lecturas_por_decision"])
    assert f.hw.servos["prensa"] == 0                      # prensa ARRIBA sin esperar al PC
    assert any(m.get("ev") == "cortina" and m["activa"] for m in f.mensajes())
    assert "cortina" in f.cmd("vasos", "avanzar", 800)[0]["error"]
    assert f.cmd("linea", "avanzar", 800)[0]["ok"]         # la cinta de monedas sigue


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
    control = ControlCarro(cfg["vehiculo"], largo_linea_m=cfg["largo_linea_m"], linea=linea, pose_muelle=pose,
                           zonas=cfg["zonas"])
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


# ---------------------------------------------------------------------
# backend real de la HAL y supervisor con `hardware.backend: real`
# ---------------------------------------------------------------------


def test_backend_real_mueve_y_lee_a_traves_del_firmware():
    from control.hal.backend_real import BackendReal

    puente = PuenteESP32(P, puerto_serial=EstacionEmulada(P))
    puente.emulada = puente.ser
    reloj = {"t": 0}
    hw = BackendReal(puente, lambda: reloj["t"])
    for t in range(0, 1200, 20):
        reloj["t"] = t
        puente.atender(t)
    hw.banda_monedas.avanzar_casilla()
    puente.ser.hw.sensores["presencia"] = True
    puente.ser.hw.sensores["cortina_mm"] = 80
    puente.ser.hw.sensores["interior_mm"] = 60          # algo adentro del vaso (vacio: ~105 mm)
    for t in range(1200, 1800, 20):
        reloj["t"] = t
        puente.atender(t)
    assert puente.ser.hw.pasos["monedas"] == 1
    assert hw.sensor_presencia.leer() is True
    assert hw.distancia_cortina.leer_mm() == 80
    assert hw.sensor_cortina.leer() is True           # lo decidio el ESP32 (seguridad = cortina)
    assert hw.sensor_interior.leer() is True          # 60 mm < 105 - 10: hay algo adentro
    puente.ser.hw.sensores["interior_mm"] = 104
    for t in range(1800, 2000, 20):
        puente.atender(t)
    assert hw.sensor_interior.leer() is False         # vaso vacio


def test_supervisor_en_modo_real_sin_placa(tmp_path):
    import copy

    from app import db
    from app.supervisor import PARO, Supervisor

    p = copy.deepcopy(P)
    p["hardware"] = {"backend": "real", "puerto": "COM_QUE_NO_EXISTE_99"}
    s = Supervisor(tmp_path / "real.db", parametros=p)
    try:
        assert s.puente.emulada is not None
        s.aplicar_orden({"cmd": "iniciar"})
        for _ in range(40):
            s.vuelta()
            s.puente.emulada.hw.t_ms += 0
        s.aplicar_orden({"cmd": "carro", "accion": "avanzar", "distancia_m": 0.2, "origen": "asistente"})
        assert s.ultima_orden["ok"] and "radio" in s.ultima_orden["detalle"]
        assert any('"dst":"carro"' in x for x in s.puente.emulada.al_carro)   # salio por ESP-NOW
        s.aplicar_orden({"cmd": "paro"})
        assert s.estado_linea == PARO
        # En paro no pasan actuadores (revision 2026-09-29), salvo una prueba explicita.
        s.aplicar_orden({"cmd": "hardware", "dst": "vasos", "act": "prensar"})
        assert not s.ultima_orden["ok"]
        s.aplicar_orden({"cmd": "hardware", "dst": "vasos", "act": "prensar", "prueba": True})
        assert s.ultima_orden["ok"]
        s.vuelta()
        tel = db.ultima_telemetria(s.conexion)
        assert tel["backend"] == "real" and "hardware" in tel
    finally:
        s.cerrar()


# ---------------------------------------------------------------------
# 2026-09-28: reglas del diseno que ahora cumple la PLACA (docs/electrica.md)
# ---------------------------------------------------------------------


def _eventos_servo(msgs, servo):
    return [m for m in msgs if m.get("t") == "evt" and m.get("src") == "servo" and m.get("ev") == servo]


@pytest.mark.parametrize("primero,segundo", [("prensar", "empujar"), ("empujar", "prensar")])
def test_prensa_y_empujador_nunca_se_mueven_a_la_vez(primero, segundo):
    """Antes la placa solo impedia repetir el MISMO servo: si el PC (o un boton
    de prueba) mandaba empujar con la prensa bajando, se movian los dos MG996R
    a la vez (riel de 6 V al limite). Ahora el segundo ESPERA a que el primero
    termine su ciclo completo (ida y vuelta) y arranca solo."""
    nombre = {"prensar": "prensa", "empujar": "empujador"}
    s1, s2 = nombre[primero], nombre[segundo]
    t = P["tiempos_ms"]
    ciclo1 = t["prensa_ciclo"] if s1 == "prensa" else t["empujador"]
    f = Fijo()
    f.correr(0, 600)
    assert f.cmd("vasos", primero, 600)[0]["ok"]
    assert f.hw.servos[s1] == P["firmware"]["servos"][s1]["activo"]
    f.est.linea_del_pc(protocolo.linea({"t": "cmd", "id": 99, "dst": "vasos", "act": segundo}), 650)
    msgs = f.mensajes()
    ack = [m for m in msgs if m["t"] == "ack" and m["id"] == 99][0]
    assert ack["ok"] is True                                   # aceptado: queda en espera, no se pierde
    assert f.hw.servos[s2] == 0                                # ...pero NO se mueve todavia
    espera = _eventos_servo(msgs, s2)
    assert espera and espera[0]["ciclo"] == "en_espera" and espera[0]["espera_a"] == s1
    # Mientras el primero VUELVE a reposo (segunda mitad del ciclo) el segundo sigue quieto.
    f.correr(650, 600 + ciclo1)
    assert f.hw.servos[s1] == 0 and f.hw.servos[s2] == 0
    f.correr(600 + ciclo1, 600 + ciclo1 + 50)
    assert f.hw.servos[s2] == P["firmware"]["servos"][s2]["activo"]
    assert any(m["ciclo"] == "arranca" for m in _eventos_servo(f.mensajes(), s2))


def test_la_orden_en_espera_se_cancela_con_la_cortina():
    f = Fijo()
    f.correr(0, 600)
    f.cmd("vasos", "prensar", 600)
    f.cmd("vasos", "empujar", 650)                             # espera a la prensa
    f.hw.sensores["cortina_mm"] = 60                           # una mano
    f.correr(700, 3000)
    assert f.hw.servos["prensa"] == 0 and f.hw.servos["empujador"] == 0   # nada se movio despues
    assert any(m["ciclo"] == "cancelado" for m in _eventos_servo(f.mensajes(), "empujador"))


def test_otros_servos_no_esperan_a_la_prensa():
    f = Fijo()
    f.correr(0, 600)
    f.cmd("vasos", "prensar", 600)
    ack = f.cmd("vasos", "tapar", 620)[0]
    assert ack["ok"] and f.hw.servos["tapas"] == P["firmware"]["servos"]["tapas"]["activo"]   # solo prensa/empujador


# --- hw.py de cada placa, con un `machine` falso (el de verdad solo existe en el ESP32) ---


class _Reloj:
    """time de MicroPython (ticks_ms, ticks_diff...) sobre un contador propio."""

    def __init__(self):
        self.ms = 0

    def ticks_ms(self):
        return self.ms

    def ticks_us(self):
        return self.ms * 1000

    def ticks_add(self, a, b):
        return a + b

    def ticks_diff(self, a, b):
        return a - b

    def sleep_ms(self, n):
        self.ms += n

    def sleep_us(self, n):
        pass


def _machine_falso():
    import types

    maq = types.ModuleType("machine")

    class Pin:
        IN, OUT, IRQ_RISING, IRQ_FALLING = 1, 2, 4, 8

        def __init__(self, n, modo=None, value=None):
            self.n, self._v = n, value or 0

        def value(self, v=None):
            if v is None:
                return self._v
            self._v = v

        def irq(self, **_):
            pass

    class PWM:
        def __init__(self, pin, freq=0, duty=0):
            self._f, self._d = freq, duty

        def freq(self, f=None):
            if f is None:
                return self._f
            self._f = f

        def duty(self, d=None):
            if d is None:
                return self._d
            self._d = d

    class I2C:
        def __init__(self, *a, sda=None, scl=None, freq=None):
            self.freq = freq

        def writeto_mem(self, *a):
            pass

        def readfrom_mem(self, *a):
            return b"\x00"

    class SoftI2C(I2C):
        pass

    class Timer:
        PERIODIC = 1

        def __init__(self, n):
            self.callback = None
            self.period = None

        def init(self, period=None, mode=None, callback=None):
            self.period, self.callback = period, callback

    maq.Pin, maq.PWM, maq.I2C, maq.SoftI2C, maq.Timer = Pin, PWM, I2C, SoftI2C, Timer
    return maq


@pytest.fixture
def importar_hw(monkeypatch):
    """Importa firmware/<placa>/hw.py con machine, pines y distancia falsos, y lo
    saca de sys.modules al terminar (para que no quede pegado a los falsos)."""
    import importlib
    import sys
    import types

    importados = []

    def _importar(placa):
        reloj = _Reloj()
        monkeypatch.setitem(sys.modules, "machine", _machine_falso())
        pin_mod = types.ModuleType("pines")
        for k, v in pines(placa).items():
            setattr(pin_mod, k, v)
        monkeypatch.setitem(sys.modules, "pines", pin_mod)
        dist = types.ModuleType("distancia")

        class Laser:
            def __init__(self, i2c, *a, **k):
                self.i2c, self.ultima, self.medidas = i2c, None, 0

            def actualizar(self):
                return False

        dist.Laser, dist.apagar_todos = Laser, lambda pines_: None
        monkeypatch.setitem(sys.modules, "distancia", dist)
        nombre = "firmware." + placa + ".hw"
        sys.modules.pop(nombre, None)
        mod = importlib.import_module(nombre)
        importados.append(nombre)
        mod.time = reloj                                   # time de MicroPython, no el de CPython
        return mod, reloj

    yield _importar
    for nombre in importados:
        sys.modules.pop(nombre, None)


def test_carro_pwm_topado_aunque_la_integral_empuje(importar_hw):
    """Rueda trabada: la velocidad medida es 0 y la integral crece hasta +0,3.
    Antes el PWM llegaba a 1023 (100 %: 8,4 V en un motor de 6 V)."""
    mod, _ = importar_hw("carro")
    cfg, _, _ = config_carro(P)
    assert cfg["carro_pwm_max"] == P["firmware"]["carro_pwm_max"] == 0.70
    m = mod.Motor(25, 26, 27, cfg)
    for _ in range(200):
        m.mover(cfg["carro_v_max_m_s"], 0.0, False)
    assert m.pwm.duty() == int(0.70 * 1023)
    m.mover(0.2, 0.0, True)                                    # PWM bajo (entrar al muelle) sigue en 0,35
    assert m.pwm.duty() <= int(0.35 * 1023)


def test_fijo_i2c_largo_a_100khz_y_rodillo_de_22mm(importar_hw):
    mod, _ = importar_hw("fijo")
    cfg = config_fijo(P)
    hw = mod.Hardware(cfg)
    assert hw.interior.i2c.freq == hw.cortina.i2c.freq == P["firmware"]["i2c_bus_largo_hz"] == 100_000
    assert hw.pca.i2c.freq == 400_000                         # el bus corto de la caja sigue a 400 kHz
    # Rodillo O22 del 3D: pi x 22 = 69,1 mm por vuelta -> 800 / 69,1 = 11,58 micropasos por mm.
    assert abs(P["firmware"]["mm_por_vuelta_cinta"] - math.pi * 22) < 0.1
    assert abs(40 * hw.cintas["monedas"].pasos_por_mm - 463) < 1
    assert abs(80 * hw.cintas["vasos"].pasos_por_mm - 926) < 1


def test_fijo_suelta_los_a4988_solo_en_esperas_largas(importar_hw):
    mod, reloj = importar_hw("fijo")
    cfg = config_fijo(P)
    t = cfg["tiempos"]
    hw = mod.Hardware(cfg)
    assert hw.en.value() == 0                                  # ENABLE activo (en bajo) al arrancar

    def correr(hasta):
        while reloj.ms < hasta:
            reloj.ms += 10
            hw.leer()

    # Ciclo normal de la linea: avance + pausa, varias veces. Nunca se sueltan.
    for _ in range(4):
        hw.avanzar_cinta("monedas", 40, t["avance_casilla_monedas"])
        correr(reloj.ms + t["avance_casilla_monedas"] + t["pausa_casilla_monedas"])
        assert hw.en.value() == 0
    # Espera larga: pasado a4988_reposo_ms con las dos cintas quietas, ENABLE alto.
    correr(reloj.ms + cfg["a4988_reposo_ms"])
    assert hw.en.value() == 1 and not hw.drivers_activos
    # La siguiente orden vuelve a dar corriente ANTES de mandar pasos.
    hw.avanzar_cinta("vasos", 80, t["avance_casilla_vasos"])
    assert hw.en.value() == 0 and hw.cintas["vasos"].step.duty() == 512


def test_carrusel_por_timer_y_su_tiempo_es_el_de_la_config(importar_hw):
    """El tiempo del carrusel en tiempos_ms tiene que ser el que de verdad
    tarda el firmware (antes: 500 ms en la config y 4,1 s en la placa)."""
    mod, _ = importar_hw("fijo")
    cfg = config_fijo(P)
    hw = mod.Hardware(cfg)
    car = hw.carrusel
    assert car._timer.period == cfg["carrusel_ms_por_paso"]   # el paso lo da el Timer, no el bucle
    car.a_tubo(3)                                              # tubo opuesto: media vuelta
    pasos = 0
    while car.moviendose():
        car._timer.callback(car._timer)
        pasos += 1
    assert pasos == cfg["carrusel_pasos_por_vuelta"] // 2
    assert pasos * cfg["carrusel_ms_por_paso"] == P["tiempos_ms"]["carrusel_giro"]



# ---------------------------------------------------------------------
# Revision del protocolo (2026-09-28): sesion, tamano, basura por radio,
# latido ajeno y el bucle del carro que no se muere
# ---------------------------------------------------------------------


def test_pc_reiniciado_el_fijo_vuelve_a_ejecutar_el_id_1():
    """Bug: el PC se reinicia (ids desde 1) sin reiniciar el ESP32 fijo: el
    fijo confirmaba `linea.avanzar id=1` pero NO lo ejecutaba (0 pasos)."""
    em = EstacionEmulada(P)
    viejo = PuenteESP32(P, puerto_serial=em)
    viejo.emulada = em                                    # que el puente haga correr su reloj
    for t in range(0, 1000, 50):
        viejo.atender(t)
    viejo.comando("linea", "avanzar", 1000)
    for t in range(1000, 2000, 50):
        viejo.atender(t)
    assert em.hw.pasos["monedas"] == 1
    nuevo = PuenteESP32(P, puerto_serial=em)             # el PC arranco de nuevo; el ESP32 no
    nuevo.emulada = em
    while nuevo.emisor.sesion == viejo.emisor.sesion:     # (1 en 65535: que no coincidan en la prueba)
        nuevo.emisor.sesion = protocolo.nueva_sesion()
    for t in range(2000, 2600, 50):
        nuevo.atender(t)
    i = nuevo.comando("linea", "avanzar", 2600)
    for t in range(2600, 3200, 50):
        nuevo.atender(t)
    assert i == 1 and nuevo.respuestas[1]["ok"] is True
    assert em.hw.pasos["monedas"] == 2


def test_latido_del_pc_lleva_n_y_sesion():
    em = EstacionEmulada(P)
    puente = PuenteESP32(P, puerto_serial=em)
    enviados = []
    puente._escribir = enviados.append
    puente.atender(0)
    hb = [m for m in enviados if m["t"] == "hb"][0]
    assert hb["n"] == 0 and hb["s"] == puente.emisor.sesion


def test_esp32_reiniciado_no_cuenta_perdidos_falsos():
    em = EstacionEmulada(P)
    puente = PuenteESP32(P, puerto_serial=em)
    puente.emulada = em
    for t in range(0, 3000, 50):
        puente.atender(t)
    assert puente.secuencia.perdidos == 0 and puente.secuencia.ultimo > 3
    em2 = EstacionEmulada(P)                               # la placa se reinicio (n desde 1, otra sesion)
    puente.ser = em2
    puente.emulada = em2
    for t in range(3000, 6000, 50):
        puente.atender(t)
    assert puente.secuencia.perdidos == 0 and puente.secuencia.reinicios >= 1


def test_carro_reiniciado_la_estacion_acepta_sus_eventos():
    f = Fijo()
    for sesion in (10, 20):                                # 20 = el carro arranco de nuevo (ids desde 1)
        e = protocolo.Emisor(500, None, sesion=sesion)
        f.est.mensaje_del_carro(protocolo.linea(e.enviar({"t": "evt", "src": "carro", "ev": "estado"}, 0)), 0)
    assert [m["ev"] for m in f.mensajes() if m.get("src") == "carro"] == ["estado", "estado"]


def _ordenes_de_prueba():
    return [{"act": "ir_a", "x": 1.2, "y": -0.3}, {"act": "ir_a", "x": -0.5, "y": 0.0},
            {"act": "ir_a", "x": 9.0, "y": 9.0}, {"act": "ir_a", "x": 0.6, "y": 0.4},
            {"act": "ir_a", "x": "a", "y": 0}, {"act": "avanzar", "distancia_m": 1.4},
            {"act": "avanzar", "distancia_m": 3.0}, {"act": "avanzar"}, {"act": "retroceder", "distancia_m": 0.5},
            {"act": "retroceder", "distancia_m": 0.2}, {"act": "girar", "grados": 90},
            {"act": "girar", "grados": -270}, {"act": "ir_meta"}, {"act": "volver_muelle"},
            {"act": "seguir_linea"}, {"act": "detener"}, {"act": "bailar"}]


def test_todos_los_mensajes_del_carro_caben_en_un_paquete_esp_now():
    """Bug: `respuesta_orden` de un ir_a rechazado media 396 B. ESP-NOW lleva
    250: el paquete no salia nunca y el Emisor lo reintentaba cada 500 ms para
    siempre, ocupando un lugar de la cola de 32."""
    cfg, linea, pose = config_carro(P)
    poses = [pose, (pose[0], pose[1], pose[2] + 0.8), (0.6, 0.1, 0.0), (1.5, -0.2, 3.0)]
    todas = []
    for pose_i in poses:
        for estado in ("esperando_carga", "esperando_orden", "en_meta"):
            for orden in _ordenes_de_prueba():
                c, salida = _carro()
                c.mensaje('{"t":"hb","src":"estacion"}', 0)
                c.control.fijar_pose(*pose_i)
                c.control.estado = estado
                m = {"t": "cmd", "id": 1, "dst": "carro", "s": 65535}
                m.update(orden)
                c.mensaje(protocolo.linea(m), 0)
                for t in (20, 40, 60):                     # los eventos que produce la orden
                    c.tick(t, 0.02)
                todas += salida
                assert c.emisor.grandes == 0
                assert all(protocolo.tamano(p[0]) <= protocolo.RADIO_MAX_BYTES for p in c.emisor.pendientes.values())
    # Los eventos del recorrido automatico, con sus datos mas largos.
    c, salida = _carro()
    for ev in ({"ev": "evasion", "lado": "izquierda", "izq_mm": 1234, "der_mm": 1234},
               {"ev": "camino_bloqueado", "distancias_mm": [1234, 1234, 1234]},
               {"ev": "atascado", "diferencia_mm": 12345}, {"ev": "muro", "sensor": "ultrasonico", "distancia_mm": 123.4},
               {"ev": "reversa_reintento", "retrocedido_m": 0.123, "tiempo_s": 12.3},
               {"ev": "punto_con_error", "error_m": 0.123}, {"ev": "error", "motivo": "no_llego_al_tope"},
               {"ev": "estado", "estado": "esperando_orden", "fase": "vuelta"}, {"ev": "vuelve_con_vaso"},
               {"ev": "linea_no_encontrada"}, {"ev": "ruta_retomada"}):
        e = {"fase": "vuelta"}
        e.update(ev)
        c.lectura = HwCarro().leer()
        c._evento(e, 0)
    todas += salida
    grandes = [x for x in todas if len(x.encode()) > protocolo.RADIO_MAX_BYTES]
    assert not grandes, grandes[:2]
    recortados = [json.loads(x) for x in todas if '"rec":true' in x]
    assert recortados and all(r["detalle"].endswith("...") for r in recortados)


def test_basura_por_radio_no_tumba_al_carro(monkeypatch):
    """Bug: un paquete ESP-NOW de otro grupo que no es UTF-8 hacia
    `bytes(msg).decode()` -> UnicodeError -> main.py muerto con el ultimo PWM."""
    import importlib
    import sys
    import types

    paquetes = [b"\xff\xfe\x00\x81", b'{"t":"hb","src":"estacion"}', b"\xc3("]

    class ESPNow:
        def active(self, v):
            pass

        def add_peer(self, mac):
            pass

        def irecv(self, t):
            return (b"\x01" * 6, paquetes.pop(0)) if paquetes else (None, None)

    class WLAN:
        def __init__(self, i):
            pass

        def active(self, v):
            pass

        def disconnect(self):
            pass

    net = types.ModuleType("network")
    net.WLAN, net.STA_IF = WLAN, 0
    esp = types.ModuleType("espnow")
    esp.ESPNow = ESPNow
    monkeypatch.setitem(sys.modules, "network", net)
    monkeypatch.setitem(sys.modules, "espnow", esp)
    sys.modules.pop("firmware.comun.enlaces", None)
    enlaces = importlib.import_module("firmware.comun.enlaces")
    try:
        radio = enlaces.Radio()
        c, _ = _carro()
        recibidos = radio.recibir()
        assert len(recibidos) == 3 and all(isinstance(x, bytes) for x in recibidos)
        for datos in recibidos:
            c.mensaje(datos, 0)                            # no lanza
        assert c.latido.ultimo_oido == 0                   # el latido bueno si conto
        f = Fijo()
        for datos in (b"\xff\xfe", b"\xc3("):
            f.est.mensaje_del_carro(datos, 0)              # la estacion tampoco se cae
    finally:
        sys.modules.pop("firmware.comun.enlaces", None)


def test_esp_now_de_otro_grupo_no_cuenta_como_latido():
    """Bug: cualquier mensaje que no fuera `src:carro` contaba como latido de
    la estacion: el ESP-NOW de otro grupo mantenia vivo el enlace con la
    estacion apagada (y el carro no aplicaba sus reglas sin enlace)."""
    c, _ = _carro()
    c.mensaje('{"t":"hb","src":"estacion"}', 0)
    for t in range(100, 1600, 100):
        c.mensaje('{"t":"hb","src":"robot_grupo3"}', t)
        c.mensaje('{"t":"evt","src":"otro","id":5,"ev":"x"}', t)
    c.tick(1600, 0.02)
    assert not c.control.enlace_vivo
    c.mensaje(protocolo.linea({"t": "ack", "dst": "carro", "id": 99, "ok": True}), 1700)
    c.tick(1700, 0.02)
    assert c.control.enlace_vivo                           # lo dirigido al carro si cuenta


class _FinBucle(BaseException):
    pass


def test_main_del_carro_sobrevive_a_una_excepcion_y_para_los_motores(monkeypatch):
    """El bucle de firmware/carro/main.py: una excepcion en una vuelta deja
    los motores en 0, se registra y el bucle sigue; el WDT se alimenta."""
    import runpy
    import sys
    import types
    from pathlib import Path

    cfg, linea, pose = config_carro(P)
    reloj = {"t": 0, "vueltas": 0}
    motores, alimentado = [], []

    class Hardware(HwCarro):
        def __init__(self, cfg_):
            super().__init__()

        def motores(self, i, d, bajo):
            motores.append((reloj["vueltas"], i, d))

    class Radio:
        def enviar(self, texto):
            return True

        def recibir(self):
            if reloj["vueltas"] == 3:
                raise OSError("sensor muerto")             # una vuelta que falla
            if reloj["vueltas"] == 0:
                # El perro se arma con el primer mensaje de la estacion (2026-09-29).
                return [b'{"t":"hb","src":"estacion"}']
            return [b"\xff\xfe basura"]

    class WDT:
        def __init__(self, timeout):
            self.timeout = timeout

        def feed(self):
            alimentado.append(reloj["t"])

    def sleep_ms(ms):
        reloj["t"] += 20
        reloj["vueltas"] += 1
        if reloj["vueltas"] > 10:
            raise _FinBucle

    tiempo = types.SimpleNamespace(ticks_ms=lambda: reloj["t"], ticks_diff=lambda a, b: a - b,
                                   ticks_add=lambda a, b: a + b, sleep_ms=sleep_ms)
    modulos = {
        "time": tiempo,
        "config_placa": types.SimpleNamespace(CFG=cfg, LINEA=linea, POSE_MUELLE=pose),
        "enlaces": types.SimpleNamespace(Radio=Radio),
        "hw": types.SimpleNamespace(Hardware=Hardware),
        "logica": types.SimpleNamespace(CarroFirmware=CarroFirmware),
        "vehiculo": types.SimpleNamespace(ControlCarro=ControlCarro),
        "machine": types.SimpleNamespace(WDT=WDT),
    }
    for k, v in modulos.items():
        monkeypatch.setitem(sys.modules, k, v)
    monkeypatch.setattr(sys, "print_exception", lambda e: None, raising=False)
    main = Path(__file__).resolve().parents[2] / "firmware" / "carro" / "main.py"
    with pytest.raises(_FinBucle):
        runpy.run_path(str(main), run_name="__main__")
    # En la vuelta 3 la excepcion salta ANTES del tick: la unica orden a los
    # motores de esa vuelta es la de seguridad (0, 0).
    assert [(i, d) for v, i, d in motores if v == 3] == [(0, 0)]
    assert len(alimentado) == 11                           # el perro se alimento en cada vuelta, tambien la que fallo



# ---------------------------------------------------------------------
# Revision logica del firmware del fijo (2026-09-28): cada prueba de aqui
# FALLABA con el firmware anterior (ver docs/bitacora.md).
# ---------------------------------------------------------------------


class HwConLaser(HardwareEmulado):
    """HardwareEmulado + lo que el hw.py de verdad agrega: el contador de
    mediciones del VL53L0X de la cortina (una cada 33 ms mientras el sensor
    este vivo) y el freno del carrusel."""

    def __init__(self):
        super().__init__()
        self.laser_vivo = True             # False: el sensor deja de medir (o se mide a mano)
        self.medidas = 0
        self._prox_medida = 0

    def leer(self):
        while self.laser_vivo and self.t_ms >= self._prox_medida:
            self.medidas += 1
            self._prox_medida += 33
        d = super().leer()
        d["cortina_medidas"] = self.medidas
        return d

    def carrusel_detener(self):
        self.carrusel_fin = self.t_ms


class FijoLaser(Fijo):
    def __init__(self):
        super().__init__()
        self.hw = HwConLaser()
        self.al_pc.clear()
        self.est = Estacion(self.hw, config_fijo(P), self.al_pc.append, self.al_carro.append)

    def correr(self, desde, hasta, paso=10, latido=True):
        for t in range(desde, hasta, paso):
            self.hw.t_ms = t
            if latido and t % 500 == 0:
                self.est.linea_del_pc('{"t":"hb"}', t)
            self.est.tick(t)

    def medicion(self, t, mm):
        """UNA medicion nueva del VL53L0X de la cortina (con laser_vivo False)."""
        self.hw.sensores["cortina_mm"] = mm
        self.hw.medidas += 1
        self.hw.t_ms = t
        self.est.tick(t)


# --- 1. el paro queda enclavado ---


def test_el_paro_no_se_borra_cuando_vuelve_el_latido():
    """Bug: el paro del dashboard (`estado.parar`) ponia parada_segura, pero si
    despues se cortaba y volvia el latido (cable USB flojo), el tick la borraba
    sola y la linea aceptaba comandos otra vez sin que nadie pidiera seguir."""
    f = Fijo()
    f.correr(0, 600)
    assert f.cmd("estado", "parar", 600)[0]["ok"]
    f.correr(600, 3600, latido=False)                      # se pierde el PC...
    f.correr(3600, 5000)                                   # ...y vuelve
    assert f.est.parada_segura and f.est.motivo_parada == "paro"
    ack = f.cmd("linea", "avanzar", 5000)[0]
    assert ack["ok"] is False and "paro" in ack["error"] and f.hw.pasos["monedas"] == 0
    assert f.cmd("estado", "reanudar", 5000)[0]["ok"]     # Iniciar/Reanudar del PC
    assert not f.est.parada_segura
    assert f.cmd("linea", "avanzar", 5000)[0]["ok"] and f.hw.pasos["monedas"] == 1


def test_la_parada_por_falta_de_pc_si_se_levanta_sola():
    f = Fijo()
    f.correr(0, 600)
    f.correr(600, 3600, latido=False)
    assert f.est.parada_segura and f.est.motivo_parada == "sin_pc"
    f.correr(3600, 4100)
    assert not f.est.parada_segura
    assert f.cmd("linea", "avanzar", 4100)[0]["ok"]


# --- 2 y 3. cortina: falla del lado seguro y vota ---


def test_cortina_sin_mediciones_nuevas_queda_activa():
    """Bug: con el I2C flojo `Laser.actualizar` tragaba el OSError y `ultima`
    quedaba congelada (None = "libre"): la cortina no veia la mano."""
    f = FijoLaser()
    f.correr(0, 600)
    assert not f.est.cortina_activa
    f.hw.laser_vivo = False                                # cable suelto: ya no hay mediciones
    t0 = f.est._t_cortina                                  # la ultima medicion buena
    limite = P["firmware"]["cortina_sin_lectura_ms"]
    f.correr(600, t0 + limite + 1)
    assert not f.est.cortina_activa                        # todavia dentro del plazo
    f.correr(t0 + limite + 1, t0 + limite + 30)
    assert f.est.cortina_activa and f.est.cortina_motivo == "sin_lectura"
    msgs = f.mensajes()
    assert any(m.get("ev") == "cortina_sin_lectura" for m in msgs)
    assert any(m.get("ev") == "cortina" and m["activa"] and m["motivo"] == "sin_lectura" for m in msgs)
    assert "cortina" in f.cmd("vasos", "avanzar", 1000)[0]["error"]
    # Vuelve a medir y la zona esta libre: se despeja tras N mediciones seguidas.
    n = P["planta"]["lecturas_por_decision"]
    for i in range(n - 1):
        f.medicion(1000 + 33 * i, None)
    assert f.est.cortina_activa                            # despejar tambien vota
    f.medicion(1000 + 33 * n, None)
    assert not f.est.cortina_activa


def test_la_cortina_vota_y_no_se_dispara_con_una_lectura_suelta():
    """Bug: una sola lectura bajo el umbral paraba la cinta de vasos. Con el
    falso positivo configurado (0,2 % a 30 Hz) era una cortina falsa cada ~17 s."""
    n = P["planta"]["lecturas_por_decision"]
    f = FijoLaser()
    f.correr(0, 600)
    f.hw.laser_vivo = False                                # desde aqui, cada medicion a mano
    f.medicion(610, 60)                                    # UNA medicion con ruido...
    f.medicion(643, None)                                  # ...y la siguiente, libre
    for t in range(676, 800, 33):
        f.medicion(t, None)
    assert not f.est.cortina_activa
    assert not [m for m in f.mensajes() if m.get("ev") == "cortina"]
    for i in range(n - 1):                                 # una mano de verdad: N seguidas
        f.medicion(800 + 33 * i, 60)
    assert not f.est.cortina_activa
    f.medicion(800 + 33 * (n - 1), 60)
    assert f.est.cortina_activa and f.est.cortina_motivo == "mano"
    # Despejar tambien vota: una lectura libre suelta no la apaga (no parpadea).
    f.medicion(1000, None)
    for t in range(1033, 1200, 33):
        f.medicion(t, 60)
    assert f.est.cortina_activa


def test_el_umbral_de_la_cortina_es_la_ventana_de_la_simulacion():
    """Una sola fuente: el alcance del cono simulado y el umbral del firmware
    (antes 140 mm en la simulacion y 150 en config/parametros.yaml)."""
    from sim.sensores_sim import ventana_cortina_mm

    assert config_fijo(P)["cortina_umbral_mm"] == ventana_cortina_mm() == 140
    assert "cortina_umbral_mm" not in P["firmware"]


# --- 4. main.py del fijo no se muere con una excepcion ---


def test_main_del_fijo_sobrevive_a_una_excepcion_y_para_seguro(monkeypatch):
    """Bug: el bucle de firmware/fijo/main.py no tenia try: una excepcion
    mataba main.py con las cintas y los servos en su ultimo estado."""
    import runpy
    import sys
    import types
    from pathlib import Path

    cfg = config_fijo(P)
    assert cfg["fijo_wdt_ms"] == P["firmware"]["fijo_wdt_ms"] > 0
    reloj = {"t": 0, "vueltas": 0}
    alimentado, al_pc = [], []
    hws = []

    class Hardware(HardwareEmulado):
        def __init__(self, cfg_):
            super().__init__()
            hws.append(self)

    class SerialUSB:
        def enviar(self, texto):
            al_pc.append(texto)

        def lineas(self):
            v = reloj["vueltas"]
            if v == 0:
                return ['{"t":"hb"}']
            if v == 1:
                return [protocolo.linea({"t": "cmd", "id": 1, "dst": "linea", "act": "avanzar"})]
            if v == 3:
                raise OSError("I2C muerto")               # una vuelta que falla
            return []

    class Radio:
        def enviar(self, texto):
            return True

        def recibir(self):
            return []

    class WDT:
        def __init__(self, timeout):
            self.timeout = timeout

        def feed(self):
            alimentado.append(reloj["t"])

    def sleep_ms(ms):
        reloj["t"] += 20
        reloj["vueltas"] += 1
        if hws:
            hws[0].t_ms = reloj["t"]
        if reloj["vueltas"] > 10:
            raise _FinBucle

    tiempo = types.SimpleNamespace(ticks_ms=lambda: reloj["t"], ticks_diff=lambda a, b: a - b,
                                   ticks_add=lambda a, b: a + b, sleep_ms=sleep_ms)
    modulos = {
        "time": tiempo,
        "config_placa": types.SimpleNamespace(CFG=cfg),
        "enlaces": types.SimpleNamespace(SerialUSB=SerialUSB, Radio=Radio),
        "estacion": types.SimpleNamespace(Estacion=Estacion),
        "hw": types.SimpleNamespace(Hardware=Hardware),
        "machine": types.SimpleNamespace(WDT=WDT),
    }
    for k, v in modulos.items():
        monkeypatch.setitem(sys.modules, k, v)
    monkeypatch.setattr(sys, "print_exception", lambda e: None, raising=False)
    main = Path(__file__).resolve().parents[2] / "firmware" / "fijo" / "main.py"
    with pytest.raises(_FinBucle):
        runpy.run_path(str(main), run_name="__main__")
    hw = hws[0]
    assert hw.pasos["monedas"] == 1 and not hw.fin         # la cinta que andaba quedo QUIETA
    assert hw.servos["prensa"] == 0 and hw.servos["desvio"] == 0
    msgs = [json.loads(x) for x in al_pc]
    paradas = [m for m in msgs if m.get("ev") == "parada_segura" and m.get("motivo") == "error"]
    assert paradas and "I2C" in paradas[0]["error"]
    assert any(m["t"] == "tel" and m["motivo_parada"] == "error" for m in msgs)   # el bucle siguio
    assert len(alimentado) == 11                           # el perro se alimento en cada vuelta


def test_preparar_pasa_el_perro_del_fijo_a_la_placa():
    cfg = config_fijo(P)
    assert cfg["fijo_wdt_ms"] == 2000 and cfg["lecturas_por_decision"] == P["planta"]["lecturas_por_decision"]
    assert cfg["cortina_sin_lectura_ms"] == P["firmware"]["cortina_sin_lectura_ms"]


# --- 5. la canaleta solo suelta con el carro en el muelle y la cuna vacia ---


def _carro_dice(f, emisor, t, **evt):
    m = {"t": "evt", "src": "carro"}
    m.update(evt)
    f.est.mensaje_del_carro(protocolo.linea(emisor.enviar(m, t)), t)


def _cmd_con_eventos(f, dst, act, t, **datos):
    """Como Fijo.cmd, pero devuelve tambien los eventos que salieron con el
    comando (Fijo.cmd se queda solo con el ack)."""
    f.hw.t_ms = t
    f.id += 1
    m = {"t": "cmd", "id": f.id, "dst": dst, "act": act}
    m.update(datos)
    f.est.linea_del_pc(protocolo.linea(m), t)
    msgs = f.mensajes()
    return [x for x in msgs if x["t"] == "ack" and x["id"] == f.id][0], msgs


def _soltar(f, t):
    return _cmd_con_eventos(f, "canaleta", "soltar", t)[0]


def test_la_canaleta_no_suelta_sin_carro_en_el_muelle_con_la_cuna_vacia():
    """Bug: `_soltar_vaso` soltaba siempre (y el PC en modo real no revisaba):
    un vaso al piso si el carro no estaba, o encima de otro vaso."""
    f = Fijo()
    carro = protocolo.Emisor(500, None, sesion=10)
    f.correr(0, 600)
    ack = _soltar(f, 600)                                  # no se oye al carro
    assert ack["ok"] is False and "sin_enlace" in ack["error"]
    assert f.hw.servos["canaleta"] == 0                    # el escape no se movio
    _carro_dice(f, carro, 650, ev="en_muelle", cuna=True)  # en el muelle... con algo en la cuna
    ack, msgs = _cmd_con_eventos(f, "canaleta", "soltar", 660)
    assert ack["ok"] is False and "cuna_ocupada" in ack["error"]
    assert any(m.get("ev") == "alarma" and m.get("tipo") == "cuna_ocupada" for m in msgs)
    _carro_dice(f, carro, 700, ev="vaso_retirado", cuna=False)
    ack = _soltar(f, 710)
    assert ack["ok"] is True and f.hw.servos["canaleta"] == P["firmware"]["servos"]["canaleta"]["activo"]
    # Recien soltado: la cuna es desconocida hasta que el carro hable. No se
    # suelta un segundo vaso encima (aunque el escape ya haya vuelto).
    f.correr(710, 1600)
    assert "cuna_desconocida" in _soltar(f, 1600)["error"]


def test_la_canaleta_espera_el_estado_del_carro_despues_de_reconectar():
    f = Fijo()
    carro = protocolo.Emisor(500, None, sesion=10)
    f.correr(0, 600)
    _carro_dice(f, carro, 600, ev="en_muelle", cuna=False)
    f.correr(600, 2000)                                    # 1,4 s sin oir al carro: enlace perdido
    _carro_dice(f, carro, 2000, ev="ruta_retomada", cuna=False)   # vuelve, pero no manda su estado
    assert "estado_viejo" in _soltar(f, 2010)["error"]
    _carro_dice(f, carro, 2020, ev="estado", estado="esperando_carga", fase="vuelta", cuna=False)
    assert _soltar(f, 2030)["ok"] is True


def test_la_canaleta_no_suelta_si_el_carro_salio_por_una_orden():
    f = Fijo()
    carro = protocolo.Emisor(500, None, sesion=10)
    f.correr(0, 600)
    _carro_dice(f, carro, 600, ev="en_muelle", cuna=False)
    f.cmd("carro", "avanzar", 610, distancia_m=0.3)       # el PC lo mueve por la radio
    assert "no_esta_en_muelle" in _soltar(f, 620)["error"]
    _carro_dice(f, carro, 700, ev="en_muelle", cuna=False)
    assert _soltar(f, 710)["ok"] is True


# --- 6. la parada segura frena el carrusel ---


def test_la_parada_segura_frena_el_carrusel():
    """Bug: la parada segura no tocaba el Timer del carrusel: el revolver
    seguia girando hasta 4 s (y avisaba `llego` como si nada)."""
    f = FijoLaser()
    f.correr(0, 600)
    assert f.cmd("carrusel", "ir", 600, tubo=3)[0]["ok"]
    f.correr(600, 1000)
    assert f.hw.carrusel_moviendose()
    _, msgs = _cmd_con_eventos(f, "estado", "parar", 1000)
    assert not f.hw.carrusel_moviendose()
    det = [m for m in msgs if m.get("src") == "carrusel" and m.get("ev") == "detenido"]
    assert det and det[0]["motivo"] == "paro" and det[0]["tubo"] == 3
    f.correr(1000, 6000)
    assert not [m for m in f.mensajes() if m.get("ev") == "llego"]   # no avisa una llegada falsa


def test_el_carrusel_de_hw_py_se_detiene_donde_esta(importar_hw):
    mod, _ = importar_hw("fijo")
    hw = mod.Hardware(config_fijo(P))
    car = hw.carrusel
    car.a_tubo(3)
    for _ in range(100):
        car._timer.callback(car._timer)
    assert car.moviendose()
    hw.carrusel_detener()
    assert not car.moviendose() and car.posicion == 100
    car._timer.callback(car._timer)
    assert car.posicion == 100                             # el Timer ya no da pasos
    assert "cortina_medidas" in hw.leer()                  # hw.py manda el contador del VL53L0X
