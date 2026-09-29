"""La parte electrica simulada (sim/electrica.py) y el circuito de Wokwi (wokwi/):

- en el ciclo real de la planta y el recorrido del carro ningun riel pasa su limite ni
  ningun fusible su corriente;
- cada hilo de sim/conexiones.py tiene voltaje, corriente y proteccion asignados;
- los divisores y pull-ups dejan los GPIO por debajo de 3,6 V y dentro de la norma I2C;
- los diagram.json de Wokwi son JSON valido y usan los MISMOS GPIO que el firmware.
"""

import json
import re
from pathlib import Path

import pytest

from firmware.preparar import pines
from sim import conexiones as cx
from sim import electrica as el

RAIZ = Path(__file__).resolve().parents[2]
WOKWI = RAIZ / "wokwi"


@pytest.fixture(scope="module")
def R():
    return el.resumen()


@pytest.fixture(scope="module")
def filas(R):
    return el.tabla_hilos(R)


# --------------------------------------------------------------------- rieles y fusibles

def test_ningun_riel_pasa_su_limite(R):
    for rid, d in R["rieles"].items():
        assert d["pico"] <= d["limite"], f"{rid}: {d['pico']:.2f} A de {d['limite']} A"


def test_ningun_fusible_pasa_su_corriente(R):
    for nombre, d in R["fusibles"].items():
        assert d["pico"] < d["amperios"], f"{nombre}: {d['pico']:.2f} A de {d['amperios']} A"


def test_la_simulacion_recorre_el_ciclo_con_carga_real(R):
    sp = R["planta"]["series"]
    # La prensa apretando (2,5 A) aparece, y prensa y empujador nunca piden corriente de
    # movimiento a la vez (la regla de diseno se respeta en la secuencia simulada).
    assert sp["servo_prensa"].max() >= 2.5
    ambos = (sp["servo_prensa"] > 0.1) & (sp["servo_empujador"] > 0.1)
    assert not ambos.any()
    assert R["autonomia"]["h_recorriendo"] > 1.0


def test_peor_caso_con_la_regla_cabe_en_f1():
    con_regla = el.peores_casos()[1]
    assert con_regla["i"] < 8.0


# ----------------------------------------------------------------------- cada hilo

def test_cada_hilo_de_conexiones_tiene_voltaje_y_corriente(filas):
    total = sum(len(c["hilos"]) for c in cx.CABLES)
    assert len(filas) == total
    for f in filas:
        assert isinstance(f["v"], float), f
        assert f["nivel"], f
        assert f["i_pico"] + 1e-9 >= f["i_nom"] >= 0, f
        assert f["prot"], f
        assert f["awg"] in el.OHM_POR_M and f["largo"] > 0


def test_ningun_gpio_recibe_mas_de_36_v(filas):
    for f in filas:
        for extremo in (f["de"], f["a"]):
            if extremo.startswith("esp32_") and extremo.endswith(".S") and f["cable"] != "c_us":
                assert f["v"] <= 3.3, f
    assert el.divisor_echo()["v_gpio"] < el.V_GPIO_MAX


def test_caidas_dejan_a_cada_carga_sobre_su_minimo(filas):
    for c in el.caidas_por_carga(filas):
        assert c["v_carga"] >= c["minimo"], c


# ------------------------------------------------------------------------- pasivos

def test_pasivos():
    d = el.divisor_echo()
    assert el.VIH_MIN < d["v_gpio"] < el.V_GPIO_MAX
    assert el.VIH_MIN < d["v_gpio_echo_bajo"]
    assert el.pullup_i2c(2200, 170)["tr_ns"] < 1000            # bus largo a 100 kHz
    assert abs(el.vref_a4988()[0.068] - 0.544) < 1e-9
    o = el.opto_pc817()
    assert o["satura"] and 3 < o["i_f_ma"] < 20                 # PC817: I_F dentro de 50 mA
    assert el.pullup_hall()["v_bajo"] < el.VIL_MAX
    assert el.pwm_motor_tt()[8.4] == pytest.approx(0.714, abs=0.01)


def test_markdown_se_genera_sin_graficas():
    texto = el.generar_markdown(graficas=False)
    assert "## 6. Cada conexión, punto por punto" in texto
    assert texto.count("\n| ") > sum(len(c["hilos"]) for c in cx.CABLES)


# --------------------------------------------------------------------------- Wokwi

NOMBRE_GPIO = {"VP": 36, "VN": 39}
# Pines que en el montaje real van por un modulo que Wokwi no tiene (I2C del PCA9685 y de
# los VL53L0X): no aparecen en el diagrama.
SUSTITUIDOS = {"fijo": {"HUB_I2C_SDA", "HUB_I2C_SCL", "VL53_INTERIOR_XSHUT", "VL53_CORTINA_XSHUT"}, "carro": set()}
# GPIO que SOLO usa Wokwi (servos directos y potenciometros en lugar del PCA9685 y los VL53L0X).
EXTRA_WOKWI = {"fijo": {2, 5, 12, 15}, "carro": {2}}
# Que parte del diagrama tiene que estar en cada pin del firmware.
PARTE = {
    "fijo": {"DRIVERS_M_STEP": "drv_m:STEP", "DRIVERS_M_DIR": "drv_m:DIR", "DRIVERS_V_STEP": "drv_v:STEP",
             "DRIVERS_V_DIR": "drv_v:DIR", "DRIVERS_EN": "drv_m:ENABLE", "ULN2003_IN1": "r_uln_in1:1",
             "ULN2003_IN2": "r_uln_in2:1", "ULN2003_IN3": "r_uln_in3:1", "ULN2003_IN4": "r_uln_in4:1",
             "PRESENCIA_OUT": "btn_presencia:1.l", "OPTO_OUT1": "btn_capacitivo:1.l",
             "OPTO_OUT2": "btn_inductivo:1.l", "HALL_S": "btn_hall:1.l"},
    "carro": {"TB6612_PWMA": "r_led_pwma:1", "TB6612_AIN1": "r_led_ain1:1", "TB6612_AIN2": "r_led_ain2:1",
              "TB6612_PWMB": "r_led_pwmb:1", "TB6612_BIN1": "r_led_bin1:1", "TB6612_BIN2": "r_led_bin2:1",
              "TB6612_STBY": "r_led_stby:1", "ENC_IZQ_D0": "btn_enc_izq:1.l", "ENC_DER_D0": "btn_enc_der:1.l",
              "IR_LINEA_OUT1": "ir_linea:1a", "IR_LINEA_OUT2": "ir_linea:2a", "IR_LINEA_OUT3": "ir_linea:3a",
              "IR_LINEA_OUT4": "ir_linea:4a", "IR_LINEA_OUT5": "ir_linea:5a", "HCSR04_TRIG": "hcsr04:TRIG",
              "HCSR04_ECHO": "hcsr04:ECHO", "IR_CUNA_DO": "btn_cuna:1.l"},
}
# Tipos de parte que existen en Wokwi (los que usa el diagrama).
TIPOS_WOKWI = {"board-esp32-devkit-c-v4", "wokwi-a4988", "wokwi-stepper-motor", "wokwi-servo", "wokwi-hc-sr04",
               "wokwi-pushbutton", "wokwi-potentiometer", "wokwi-led", "wokwi-resistor", "wokwi-dip-switch-8"}


def _gpio_de_diagrama(diagrama):
    """{gpio: {extremos conectados}} de las conexiones del ESP32 (esp:NN o esp:VP/VN)."""
    uso = {}
    for a, b, *_ in diagrama["connections"]:
        for x, y in ((a, b), (b, a)):
            if x.startswith("esp:"):
                n = x.split(":", 1)[1]
                g = NOMBRE_GPIO.get(n, int(n) if n.isdigit() else None)
                if g is not None:
                    uso.setdefault(g, set()).add(y)
    return uso


@pytest.mark.parametrize("placa", ["fijo", "carro"])
def test_diagram_json_valido_y_con_los_gpio_del_firmware(placa):
    diagrama = json.loads((WOKWI / placa / "diagram.json").read_text(encoding="utf-8"))
    tipos = {p["type"] for p in diagrama["parts"]}
    assert tipos <= TIPOS_WOKWI, tipos - TIPOS_WOKWI
    ids = {p["id"] for p in diagrama["parts"]}
    for a, b, *_ in diagrama["connections"]:
        for x in (a, b):
            if not x.startswith("$"):
                assert x.split(":")[0] in ids, x
    uso = _gpio_de_diagrama(diagrama)
    firmware = pines(placa)
    for nombre, gpio in firmware.items():
        if nombre in SUSTITUIDOS[placa]:
            continue
        assert gpio in uso, f"{nombre} (GPIO {gpio}) no esta en el diagrama de Wokwi"
        assert PARTE[placa][nombre] in uso[gpio], f"{nombre}: GPIO {gpio} -> {uso[gpio]}"
    esperados = {g for n, g in firmware.items() if n not in SUSTITUIDOS[placa]}
    assert set(uso) - esperados == EXTRA_WOKWI[placa]


@pytest.mark.parametrize("placa", ["fijo", "carro"])
def test_main_py_de_wokwi_usa_los_gpio_del_diagrama(placa):
    texto = (WOKWI / placa / "main.py").read_text(encoding="utf-8")
    numeros = {int(n) for n in re.findall(r"\b\d+\b", texto)}
    diagrama = json.loads((WOKWI / placa / "diagram.json").read_text(encoding="utf-8"))
    assert set(_gpio_de_diagrama(diagrama)) <= numeros
