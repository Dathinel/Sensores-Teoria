"""Parte electrica SIMULADA, punto por punto (pedido 10-c del usuario, 2026-09-28).

Que hace este modulo (Python puro: numpy y, si esta, matplotlib; NO usa PyBullet):

1. Modela cada RIEL de alimentacion (12 V de la fuente, 6 V de los servos, 5 V de
   la caja, 3,3 V del ESP32 fijo, 5 V del USB, bateria 2S del carro y su 5 V) y cada
   CARGA con su corriente de reposo, nominal y pico (valores de hoja de datos,
   marcados como tales: todavia no se midieron en el montaje).
2. Recorre en el tiempo, con paso de 10 ms, un ciclo REAL de la planta (las dos
   cintas con los tiempos de `config/parametros.yaml`, los servos en el orden de la
   seccion 5 de docs/especificacion.md, prensa y empujador nunca a la vez) y un recorrido del
   carro (arranque, rectas, curvas, evasion de los 3 muros, meta, vuelta, muelle).
   Resultado: corriente de cada riel contra el tiempo, pico, promedio, margen de
   cada fusible y regulador, disipacion, consumo desde la red y autonomia.
3. Asigna a CADA hilo de `sim/conexiones.py` (la fuente unica del conexionado) su
   voltaje, su corriente nominal y pico, su calibre (AWG), su largo, su caida de
   tension y la proteccion que lo cubre.
4. Calcula los pasivos (Vref del A4988, divisor del ECHO, pull-ups, optoacoplador,
   condensadores, PWM de los motores TT) con la formula a la vista.
5. `generar_markdown()` arma `docs/electrica.md`; `python -m sim.electrica` lo
   escribe junto con las graficas `docs/capturas/electrica-ciclo-*.png`.

Por que una simulacion "de corrientes" y no un SPICE: lo que hay que decidir aqui
es si cada fuente, regulador, fusible y cable AGUANTA lo que le piden en el peor
momento real del ciclo (dos servos arrancando a la vez, un motor trabado, el carro
girando), y eso depende de CUANDO se prende cada cosa. Un modelo de corriente por
carga contra el tiempo responde exactamente eso, con datos que se pueden revisar a
mano; un SPICE pediria modelos de cada modulo que no existen.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from sim import conexiones as cx

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
CAPTURAS = DOCS / "capturas"
DT = 0.010   # paso de la simulacion en el tiempo: 10 ms (el tiempo de reaccion de un fusible es >> 10 ms)


def cargar_parametros() -> dict:
    with open(RAIZ / "config" / "parametros.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ===========================================================================
# 1. Cables: resistencia por calibre y largo de cada tramo
# ===========================================================================

# Resistencia de UN hilo de cobre a 20 °C, en ohm por metro (tabla AWG estandar).
# La caida de un circuito es ida + vuelta: por eso en la tabla de cargas se suma
# la del hilo positivo y la del GND.
OHM_POR_M = {18: 0.021, 20: 0.033, 22: 0.053, 24: 0.084, 26: 0.134, 28: 0.213}

# Largo de los cables de CAMPO medido en el modelo 3D con 20 % de holgura
# (docs/revision-final.md §4, tabla "Largos de cable"). Es un texto en un .md, no un
# dato de Python: se copia aqui con la cita, en metros, por id de cable de conexiones.py.
LARGOS_CAMPO_M = {
    "motor_monedas": 1.38, "motor_vasos": 0.76, "motor_carrusel": 0.94,
    "servo_0": 0.63, "servo_1": 1.19, "servo_2": 1.11, "servo_3": 0.59, "servo_4": 0.26, "servo_5": 0.70,
    "presencia": 1.18, "capacitivo": 1.18, "inductivo": 1.14, "hall": 0.88,
    "vl53_interior": 1.20, "vl53_cortina": 0.50, "panel_luz": 0.29, "anillo": 1.03,
    "usb_cenital": 1.30, "usb_vasos": 1.23, "usb_esp": 0.38, "usb_pc": 0.07, "red": 0.28,
}
# Dentro de la caja: 18,7 m de hilo en 47 hilos (revision-final §4) = 0,40 m de promedio
# por hilo de potencia; los Dupont de logica son jumpers de 20 cm. Carro: 6,0 m en 42
# hilos = ~0,15 m por hilo.
LARGO_INTERNO_M = 0.40
LARGO_DUPONT_M = 0.20
LARGO_CARRO_M = 0.15

# Calibre por tipo de cable (el `tipo` de cada cable de conexiones.py). Por que cada uno:
# - potencia interna 18 AWG: la bornera V+ del PCA9685 ya va en 18 AWG (conexiones.py) y
#   por la rama de F1 pueden pasar ~4 A: 18 AWG aguanta ~7 A en haz sin calentarse;
# - servos 22 AWG: la extension que dice revision-final §4;
# - sensores de 12 V: el cable propio del M18 (3 x 0,34 mm² ≈ 22 AWG);
# - señal / I2C de campo 24 AWG (cable de 3-4 hilos apantallado o trenzado);
# - Dupont 26 AWG (jumper comun); USB: los hilos de VBUS/GND de un cable USB comun
#   son de 28 AWG (por eso una webcam lejos pierde voltaje: se calcula abajo).
AWG_POR_TIPO = {"red": 18, "interno": 18, "dupont": 26, "senal": 24, "sensor12": 22, "i2c": 24,
                "paso": 22, "servo": 22, "cinco": 22, "usb": 28, "carro": 26}


def cable_fisico(cable: dict, hilo: dict) -> tuple[int, float]:
    """(AWG, largo en m) de un hilo."""
    tipo = cable["tipo"]
    awg = AWG_POR_TIPO.get(tipo, 24)
    if cable["id"] == "motor_carrusel":
        awg = 26                     # el cable propio del 28BYJ-48 es delgado (~26 AWG)
    if tipo == "carro" and cable["id"] in ("c_bat", "c_mot"):
        awg = 22                     # potencia del carro: bateria y motores en 22 AWG
    if tipo in ("interno", "red"):
        largo = LARGOS_CAMPO_M.get(cable["id"], LARGO_INTERNO_M)
    elif tipo == "dupont":
        largo = LARGO_DUPONT_M
    elif tipo == "carro":
        largo = LARGO_CARRO_M
    else:
        largo = LARGOS_CAMPO_M.get(cable["id"], LARGO_INTERNO_M)
    return awg, largo


# ===========================================================================
# 2. Rieles y cargas (hoja de datos)
# ===========================================================================

@dataclass(frozen=True)
class Riel:
    id: str
    nombre: str
    tension: float          # V nominal
    origen: str             # quien lo genera
    limite_a: float         # corriente maxima que se le permite (A)
    limite_texto: str
    para_que: str


RIELES = {
    "12V": Riel("12V", "12 V de la fuente", 12.0, "Fuente conmutada LRS-150-12 (110 V AC → 12 V DC)", 10.0,
                "10 A de la fuente (150 W)", "Drivers A4988 (VMOT), sensores capacitivo e inductivo y la entrada de los dos buck."),
    "6V": Riel("6V", "6 V de los servos", 6.0, "Buck XL4016 desde F1", 8.0,
               "8 A del XL4016 (≈5 A continuos sin ventilación extra)", "Solo los 6 servos, por la bornera V+ del PCA9685 (con 1000 µF)."),
    "5V": Riel("5V", "5 V de la caja", 5.0, "Buck LM2596 desde F2", 3.0,
               "3 A del LM2596 (≈2 A continuos sin disipador)", "28BYJ-48 del carrusel por el ULN2003, panel de luz, anillo de la cámara, ventilador."),
    "3V3F": Riel("3V3F", "3,3 V del ESP32 fijo", 3.3, "Regulador lineal AMS1117-3.3 del DevKit, desde el USB", 0.6,
                 "≈0,6 A (1 A del AMS1117, limitado por temperatura: 1,7 V de caída)",
                 "El ESP32 y toda la lógica de 3,3 V: sensores de 3 hilos, VL53L0X, lógica del PCA9685 y de los A4988, pull-ups."),
    "USB": Riel("USB", "5 V del hub USB", 5.0, "Hub USB 2.0 con fuente propia (adaptador 5 V 2 A, PROVISIONAL)", 2.0,
                "2 A del adaptador del hub; 0,5 A por puerto (USB 2.0)", "ESP32 fijo (datos y alimentación) y las dos webcams."),
    "BAT": Riel("BAT", "Batería 2S del carro", 7.4, "2 × 18650 2500 mAh con BMS 2S (6,0-8,4 V)", 3.0,
                "3 A del fusible del carro (el BMS 2S típico corta en 3-5 A)", "Motores TT por el TB6612 y el regulador de 5 V de la placa."),
    "5VC": Riel("5VC", "5 V del carro", 5.0, "Regulador de la placa GVS (lineal tipo AMS1117-5.0) desde la batería", 1.0,
                "1 A del AMS1117; por CALOR ≈0,3 A continuos con 8,4 V (disipa 3,4 V × I; ~1 W en SOT-223)",
                "ESP32 del carro (VIN) y el HC-SR04; del 3,3 V del ESP32 salen los demás sensores."),
}

# Cargas: (riel, reposo A, nominal A, pico A, de donde sale el dato). Corrientes medidas EN
# SU riel (un servo en el de 6 V, el ESP32 en el de 3,3 V...). Todo es de hoja de datos o
# de mediciones tipicas publicadas: PROVISIONAL hasta medir con el multimetro en el montaje.
CARGAS = {
    # --- 6 V: servos (a 6 V corren un poco mas y piden un poco mas que a 4,8 V) ---
    "SG90": ("6V", 0.006, 0.25, 0.70, "SG90: ~6 mA quieto, ~0,25 A moviéndose, ~0,7 A trabado (arranque)"),
    "MG996R": ("6V", 0.010, 0.90, 2.50, "MG996R: ~10 mA quieto, 0,5-0,9 A moviéndose, 2,5 A trabado (hoja: 2,5 A a 6 V)"),
    # --- 12 V ---
    "nema17": ("12V", 0.19, 0.30, 0.45, "17HS4401 (1,5 Ω/fase) a 1 A/fase con A4988: ver modelo del paso a paso"),
    "sensor_m18": ("12V", 0.008, 0.008, 0.015, "LJC18A3 / LJ18A3-8: consumo sin carga ≤ 10-15 mA"),
    "opto_led": ("12V", 0.0, 0.0045, 0.0047, "LED del PC817 con 2,2 kΩ desde 12 V (cálculo en pasivos)"),
    # --- 5 V de la caja ---
    "byj48": ("5V", 0.0, 0.15, 0.24, "28BYJ-48 5 V: 50 Ω/bobina → 0,1 A por bobina; medio paso = 1 o 2 bobinas; + LEDs del ULN2003"),
    "panel": ("5V", 0.80, 0.80, 0.85, "Panel LED difuso ~33 × 11 cm: 2 tiras 2835 de 20 LED a ~20 mA (PROVISIONAL)"),
    "anillo": ("5V", 0.35, 0.35, 0.40, "Anillo de luz difusa 5 V para webcam (PROVISIONAL)"),
    "ventilador": ("5V", 0.10, 0.10, 0.15, "Ventilador 4010 5 V: 0,1 A (conexiones.py)"),
    # --- 3,3 V del ESP32 fijo ---
    "esp32": ("3V3F", 0.100, 0.110, 0.240, "ESP32 con la radio encendida (ESP-NOW escuchando ~100 mA; transmitiendo ~240 mA)"),
    "vl53": ("3V3F", 0.019, 0.019, 0.040, "VL53L0X: 19 mA midiendo (promedio); pulsos del láser ~40 mA"),
    "fc51": ("3V3F", 0.012, 0.012, 0.015, "FC-51 a 3,3 V: LED IR ~10 mA + LM393 + LEDs del módulo"),
    "ky003": ("3V3F", 0.005, 0.005, 0.010, "KY-003: A3144 ~4,4 mA (máx 9 mA) + LED del módulo"),
    "pca_logica": ("3V3F", 0.006, 0.006, 0.010, "PCA9685: lógica ~6 mA (VCC)"),
    "a4988_logica": ("3V3F", 0.005, 0.005, 0.008, "A4988: VDD de lógica ≤ 8 mA cada uno"),
    "pullups": ("3V3F", 0.002, 0.003, 0.004, "Pull-ups: I2C 2,2 kΩ (1,5 mA con la línea en bajo), 10 kΩ del Hall y del opto (0,33 mA)"),
    "uln_entradas": ("3V3F", 0.0, 0.0014, 0.0028, "Entradas del ULN2003 (2,7 kΩ internas): ~0,7 mA por entrada encendida"),
    # --- USB ---
    "cam_1080": ("USB", 0.25, 0.25, 0.35, "Webcam 1080p con autoenfoque en MJPEG: 0,25-0,35 A"),
    "cam_720": ("USB", 0.20, 0.20, 0.25, "Webcam 720p en MJPEG: ~0,2 A"),
    "hub": ("USB", 0.05, 0.05, 0.05, "Controlador del hub USB"),
    # --- Carro (lógica del 3,3 V del ESP32 del carro) ---
    "esp32_carro": ("5VC", 0.100, 0.110, 0.240, "ESP32 con ESP-NOW (igual que el fijo)"),
    "ir5": ("5VC", 0.050, 0.050, 0.060, "5 TCRT5000 a 3,3 V: ~10 mA por LED IR"),
    "tcrt_cuna": ("5VC", 0.012, 0.012, 0.015, "Módulo TCRT5000 de la cuna a 3,3 V"),
    "h206": ("5VC", 0.012, 0.012, 0.015, "Encoder H206 a 3,3 V: LED IR + LM393"),
    "tb6612_logica": ("5VC", 0.002, 0.002, 0.002, "TB6612: VCC de lógica ~2 mA"),
    "hcsr04": ("5VC", 0.015, 0.015, 0.015, "HC-SR04 a 5 V: 15 mA"),
}


# ===========================================================================
# 3. Modelos fisicos de los actuadores
# ===========================================================================

# --- Paso a paso NEMA17 17HS4401 con A4988 -------------------------------------------
# Por que la corriente que sale de la fuente de 12 V es MUCHO menor que 1 A por fase: el
# A4988 es un "chopper": conecta la bobina a 12 V solo el tiempo justo para que la
# corriente suba a 1 A y despues la deja circular sin tomar de la fuente (como un buck).
# Lo que la fuente entrega es POTENCIA: cobre + perdidas del driver + trabajo mecanico.
# Con micropaso los dos devanados siguen seno y coseno: I1² + I2² = I_trip² siempre, asi
# que el cobre disipa I_trip² · R_fase constante (quieto o moviendose).
NEMA_R_FASE = 1.5         # ohm por fase del 17HS4401
A4988_RDS = 0.75          # ohm: DMOS de arriba (0,32) + de abajo (0,43) del A4988, por fase
I_TRIP = 1.0              # A por fase (Vref ≈ 0,54 V; ver pasivos)
# Par de carga PROVISIONAL (el peso real lo calcula docs/peso.md): la cinta de monedas
# casi no lleva peso; la de vasos arrastra hasta 4 vasos con monedas.
PAR_CINTA_NM = {"monedas": 0.05, "vasos": 0.12}
PERDIDAS_HIERRO_W = 0.5   # histeresis y corrientes parasitas del motor girando (estimado)


def corriente_nema_12v(cinta: str, moviendose: bool, p: dict, arrancando: bool = False) -> float:
    """Corriente que un NEMA17 con su A4988 saca del riel de 12 V (A)."""
    cobre = I_TRIP ** 2 * NEMA_R_FASE              # 1,5 W: SIEMPRE (el A4988 no baja la corriente quieto)
    driver = I_TRIP ** 2 * A4988_RDS               # 0,75 W en los transistores del driver
    potencia = cobre + driver
    if moviendose:
        t = p["tiempos_ms"]
        mm = p["cinta_monedas"]["separacion_casilla_mm"] if cinta == "monedas" else p["vasos"]["separacion_casilla_mm"]
        ms = t["avance_casilla_monedas"] if cinta == "monedas" else t["avance_casilla_vasos"]
        vueltas = mm / p["firmware"]["mm_por_vuelta_cinta"]
        omega = vueltas * 2 * math.pi / (ms / 1000)  # rad/s del eje
        potencia += PAR_CINTA_NM[cinta] * omega + PERDIDAS_HIERRO_W
        if arrancando:
            potencia *= 1.5                        # rampa de arranque: acelerar el rodillo y la banda
    return potencia / 12.0


# --- Servos ---------------------------------------------------------------------------
# Un servo que arranca pide su corriente de TRABADO durante unos 30 ms (el motor parte
# de velocidad cero: no hay fuerza contraelectromotriz que limite la corriente). Despues
# baja a la corriente de movimiento y, al llegar, a la de reposo. Velocidad a 6 V sin
# carga: SG90 0,09 s/60°, MG996R 0,14 s/60° (con carga, mas lento).
T_ARRANQUE_S = 0.03
SERVO_S_60 = {"SG90": 0.09, "MG996R": 0.14}
SERVO_MODELO = {"desvio": "SG90", "obturador": "SG90", "tapas": "SG90", "prensa": "MG996R",
                "empujador": "MG996R", "canaleta": "SG90"}


# --- Motor TT del carro (1:48) ----------------------------------------------------------
# Modelo de motor DC visto desde la rueda: V = I·R + Ke·ω y par = Kt·I·η_caja.
# Datos tipicos del TT 1:48 a 6 V: ~200 rpm y 0,15 A sin carga, trabado ~1,2 A.
TT_R = 5.0                 # ohm del inducido (6 V / 1,2 A trabado)
TT_I0 = 0.15               # A sin carga (roce de la caja reductora)
TT_KE = (6.0 - TT_I0 * TT_R) / (200 * 2 * math.pi / 60)   # V·s/rad en la rueda ≈ 0,25
TT_ETA_CAJA = 0.6          # rendimiento de la caja de engranajes plasticos
TB6612_R = 0.5             # ohm de los MOSFET del TB6612 (alto + bajo) por canal
TB6612_I_CONT = 1.2        # A continuos por canal (hoja), 3,2 A pico
CRR = 0.03                 # coeficiente de rodadura (llanta de goma en piso liso)
R_BATERIA = 0.045 * 2 + 0.04 + 0.03 + 0.02   # 2 celdas + BMS + fusible + interruptor (ohm)
CAPACIDAD_MAH = 2500
FRACCION_UTIL = 0.85       # no se descarga por debajo de ~3,2 V por celda (vida de la celda)


# ===========================================================================
# 4. Simulacion en el tiempo
# ===========================================================================

class Linea:
    """Serie de corriente de una carga, con utilidades para escribir tramos."""

    def __init__(self, n: int, reposo: float):
        self.i = np.full(n, reposo, dtype=float)
        self.n = n

    def tramo(self, t0: float, dur: float, valor: float, modo: str = "max"):
        a, b = int(round(t0 / DT)), int(round((t0 + dur) / DT))
        a, b = max(0, a), min(self.n, max(b, a + 1))
        if a >= self.n:
            return
        if modo == "max":
            self.i[a:b] = np.maximum(self.i[a:b], valor)
        else:
            self.i[a:b] = valor


def mover_servo(linea: Linea, modelo: str, t0: float, grados: float, *, extra_a: float = 0.0,
                trabado_final_s: float = 0.0, factor_vel: float = 1.0) -> float:
    """Escribe el perfil de un movimiento de servo y devuelve cuanto dura (s)."""
    _, _, mov, trab, _ = CARGAS[modelo]
    dur = max(T_ARRANQUE_S + 0.02, grados / 60 * SERVO_S_60[modelo] * factor_vel)
    linea.tramo(t0, T_ARRANQUE_S, trab)                          # arranque: corriente de trabado
    linea.tramo(t0 + T_ARRANQUE_S, dur - T_ARRANQUE_S, mov + extra_a)
    if trabado_final_s:
        linea.tramo(t0 + dur, trabado_final_s, trab)             # empujando contra el resorte
    return dur + trabado_final_s


def simular_planta(p: dict | None = None, duracion_s: float = 20.0) -> dict:
    """Ciclo real de la planta con las dos cintas corriendo a la vez.

    Cinta de monedas (cada `avance + pausa` = 1,6 s): avanza, el desvio se pone para
    una moneda aceptada (una de cada dos), y en la pausa el carrusel gira un tubo (60°).
    Cinta de vasos (avance 1 s): tapa; prensa 0→180→0 con la leva apretando la tapa
    contra el resorte; DESPUES el empujador (nunca a la vez que la prensa: regla de
    diseño), asi que su ciclo dura avance + prensa + empujador = 3,1 s. En la ventana
    ademas se suelta un lote (carrusel media vuelta + obturador) y la canaleta suelta
    un vaso al carro.
    """
    p = p or cargar_parametros()
    t = p["tiempos_ms"]
    n = int(round(duracion_s / DT))
    tiempo = np.arange(n) * DT
    L = {}
    for nombre, modelo in SERVO_MODELO.items():
        L["servo_" + nombre] = Linea(n, CARGAS[modelo][1])
    L["nema_m"] = Linea(n, corriente_nema_12v("monedas", False, p))
    L["nema_v"] = Linea(n, corriente_nema_12v("vasos", False, p))
    L["carrusel"] = Linea(n, 0.0)                                    # sin corriente quieto (firmware)
    for k in ("panel", "anillo", "ventilador"):
        L[k] = Linea(n, CARGAS[k][2])
    L["esp32"] = Linea(n, CARGAS["esp32"][1])

    # --- cinta de monedas ---
    tm = (t["avance_casilla_monedas"] + t["pausa_casilla_monedas"]) / 1000
    av_m = t["avance_casilla_monedas"] / 1000
    fw = p["firmware"]
    # El carrusel lo mueve el FIRMWARE a un medio paso cada `carrusel_ms_por_paso`: un tubo
    # (60°) son 4096/6 = 683 medios pasos → 1,37 s; media vuelta 4,1 s.
    s_por_grado = fw["carrusel_pasos_por_vuelta"] / 360 * fw["carrusel_ms_por_paso"] / 1000
    k = 0
    while k * tm < duracion_s:
        t0 = k * tm
        L["nema_m"].tramo(t0, 0.06, corriente_nema_12v("monedas", True, p, arrancando=True), "set")
        L["nema_m"].tramo(t0 + 0.06, av_m - 0.06, corriente_nema_12v("monedas", True, p), "set")
        if k % 2 == 0:                                   # moneda aceptada: desvio al almacen y vuelta
            d = mover_servo(L["servo_desvio"], "SG90", t0, 30)
            mover_servo(L["servo_desvio"], "SG90", t0 + av_m + 0.3, 30)
        if not (6.0 <= t0 < 12.0):                        # (entre 6 y 12 s el carrusel suelta un lote)
            L["carrusel"].tramo(t0 + av_m, 60 * s_por_grado, CARGAS["byj48"][2])
        k += 1

    # --- lote: el carrusel lleva el tubo lleno al agujero (hasta 180°) y abre el obturador ---
    t_lote = 6.2
    giro = 180 * s_por_grado
    L["carrusel"].tramo(t_lote, giro, CARGAS["byj48"][2])
    ob = t_lote + giro
    mover_servo(L["servo_obturador"], "SG90", ob, 90)
    mover_servo(L["servo_obturador"], "SG90", ob + t["compuerta_tubo"] / 2000, 90)

    # --- cinta de vasos: avance, tapa + prensa, luego empujador (secuencial) ---
    av_v = t["avance_casilla_vasos"] / 1000
    prensa = t["prensa_ciclo"] / 1000
    emp = t["empujador"] / 1000
    tv = av_v + prensa + emp
    j = 0
    while j * tv < duracion_s:
        t0 = j * tv
        L["nema_v"].tramo(t0, 0.06, corriente_nema_12v("vasos", True, p, arrancando=True), "set")
        L["nema_v"].tramo(t0 + 0.06, av_v - 0.06, corriente_nema_12v("vasos", True, p), "set")
        tp = t0 + av_v
        mover_servo(L["servo_tapas"], "SG90", tp, 60)
        mover_servo(L["servo_tapas"], "SG90", tp + t["tapa_caida"] / 2000, 60)
        # Prensa: baja con la leva (mas lenta con carga), aprieta 0,2 s contra el resorte
        # (servo casi trabado: es el pico de diseño) y sube sin carga.
        mover_servo(L["servo_prensa"], "MG996R", tp, 180, factor_vel=1.6, trabado_final_s=0.2)
        mover_servo(L["servo_prensa"], "MG996R", tp + prensa / 2, 180, extra_a=-0.3)
        te = tp + prensa                                   # el empujador espera a que la prensa termine
        mover_servo(L["servo_empujador"], "MG996R", te, 120, extra_a=0.3, factor_vel=1.3)   # empuja el vaso
        mover_servo(L["servo_empujador"], "MG996R", te + emp / 2, 120, extra_a=-0.3)
        j += 1

    # --- canaleta: suelta un vaso al carro ---
    mover_servo(L["servo_canaleta"], "SG90", 12.5, 45)
    mover_servo(L["servo_canaleta"], "SG90", 12.5 + t["empujador"] / 2000, 45)

    # --- ESP32 fijo: latido de la radio cada 250 ms (transmite ~5 ms) ---
    periodo = p["protocolo"]["carro_latido_ms"] / 1000
    for tx in np.arange(0, duracion_s, periodo):
        L["esp32"].tramo(tx, DT, CARGAS["esp32"][3])

    return _rieles_planta(tiempo, {k: v.i for k, v in L.items()}, p)


# Eficiencias (hoja de datos, en el punto de trabajo de este montaje):
ETA_XL4016 = 0.90       # 12 → 6 V a 1-4 A
ETA_LM2596 = 0.82       # 12 → 5 V a ~1,5 A (el LM2596 rinde menos que el XL4016)
IQ_BUCK = 0.008         # A que cada buck consume en vacio desde 12 V
ETA_FUENTE = 0.84       # LRS-150-12 trabajando al ~20-30 % de su carga (a plena carga rinde ~89 %)
P_VACIO_FUENTE = 0.75   # W de la fuente sin carga (hoja: < 0,75 W)
V_RED = 110.0
FACTOR_POTENCIA = 0.55  # la LRS-150 no tiene PFC: factor de potencia ~0,5-0,6


def _rieles_planta(tiempo, I: dict, p: dict) -> dict:
    servos = sum(I["servo_" + s] for s in SERVO_MODELO)
    cinco = I["carrusel"] + I["panel"] + I["anillo"] + I["ventilador"]
    sens12 = 2 * CARGAS["sensor_m18"][2] + 2 * CARGAS["opto_led"][2] * 0.5   # los opto prendidos la mitad del tiempo
    uln = np.where(I["carrusel"] > 0, CARGAS["uln_entradas"][2], 0.0)
    tres3 = (I["esp32"] + 2 * CARGAS["vl53"][2] + CARGAS["fc51"][2] + CARGAS["ky003"][2] + CARGAS["pca_logica"][2]
             + 2 * CARGAS["a4988_logica"][2] + CARGAS["pullups"][2] + uln)
    usb_esp = tres3 + 0.005                                                   # lineal: entra lo que sale + reposo
    hub = usb_esp + CARGAS["cam_1080"][2] + CARGAS["cam_720"][2] + CARGAS["hub"][2]
    drivers = I["nema_m"] + I["nema_v"]
    f1 = servos * 6.0 / (ETA_XL4016 * 12.0) + IQ_BUCK        # potencia que sale / rendimiento / 12 V
    f2 = cinco * 5.0 / (ETA_LM2596 * 12.0) + IQ_BUCK
    f3 = drivers
    f4 = np.full_like(tiempo, sens12)
    doce = f1 + f2 + f3 + f4
    p_red = doce * 12.0 / ETA_FUENTE + P_VACIO_FUENTE
    series = {"6V": servos, "5V": cinco, "3V3F": tres3, "USB": hub, "USB_ESP": usb_esp, "12V": doce,
              "F1": f1, "F2": f2, "F3": f3, "F4": f4, "red_W": p_red, "red_A": p_red / (V_RED * FACTOR_POTENCIA)}
    series.update(I)
    return {"t": tiempo, "series": series}


# --- Carro -------------------------------------------------------------------------------

def _perfil_carro(p: dict) -> list[tuple[float, float, float, str]]:
    """Recorrido como tramos (duracion s, v_izq, v_der m/s, nombre) a partir de la pista y
    de las velocidades de `vehiculo` (parametros.yaml). Es un perfil REPRESENTATIVO (no la
    corrida de PyBullet): distancias de la pista, velocidades y angulos del control."""
    v = p["vehiculo"]
    vl, vm, vg = v["velocidad_linea_m_s"], v["velocidad_maniobra_m_s"], v["velocidad_giro_rueda_m_s"]
    b = 2 * 0.073                          # trocha: centro de cada llanta a ±73 mm (60 de medio chasis + 13)
    tramos = []

    def recta(dist_mm, vel, nombre):
        tramos.append((dist_mm / 1000 / vel, vel, vel, nombre))

    def curva(grados, radio_mm, vel):
        r = radio_mm / 1000
        dur = abs(math.radians(grados)) * r / vel
        dentro, fuera = vel * (1 - b / 2 / r), vel * (1 + b / 2 / r)
        tramos.append((dur, dentro, fuera, "curva") if grados > 0 else (dur, fuera, dentro, "curva"))

    def pivote(grados, nombre="giro sobre su eje"):
        dur = abs(math.radians(grados)) * (b / 2) / vg
        s = 1 if grados > 0 else -1
        tramos.append((dur, -s * vg, s * vg, nombre))

    def parar(dur, nombre="detenido"):
        tramos.append((dur, 0.0, 0.0, nombre))

    def muro():
        recta(250, vm, "frena ante el muro")
        parar(0.3)
        pivote(v["angulo_mirar_grados"], "mira a los lados")
        pivote(-2 * v["angulo_mirar_grados"], "mira a los lados")
        pivote(v["angulo_mirar_grados"], "mira a los lados")
        pivote(45, "evasión")
        recta(280, vm, "evasión")
        pivote(-45, "evasión")
        recta(400, vm, "evasión")
        pivote(-60, "evasión")
        recta(230, vm, "evasión")
        pivote(60, "evasión")

    parar(2.0, "en el muelle (cargando)")
    for sentido in (1, -1):
        recta(600, vl, "recta")
        for i, c in enumerate(p["pista"]["tramos"][1::2]):
            curva(c["angulo_grados"] * sentido, c["radio_mm"], vl)
            muro()
        recta(450, vl, "recta")
        if sentido == 1:
            parar(5.0, "en la meta (sacan el vaso)")
            pivote(180, "media vuelta")
    pivote(180, "media vuelta en la marca")
    tramos.append((2.5, -vm, -vm, "reversa al muelle"))
    tramos.append((0.8, -0.001, -0.001, "contra el tope (PWM bajo)"))
    parar(3.0, "en el muelle")
    return tramos


def simular_carro(p: dict | None = None, v_bateria: float = 7.4) -> dict:
    p = p or cargar_parametros()
    v = p["vehiculo"]
    r = v["diametro_rueda_mm"] / 2000
    masa = v["masa_kg"] + v["masa_vaso_lleno_kg"]
    a_max = v["aceleracion_max_m_s2"]
    tramos = _perfil_carro(p)
    total = sum(d for d, *_ in tramos)
    n = int(math.ceil(total / DT))
    tiempo = np.arange(n) * DT
    obj = np.zeros((n, 2))
    contra_tope = np.zeros(n, dtype=bool)
    nombres = [""] * n
    t = 0.0
    for dur, vi, vd, nombre in tramos:
        a, b_ = int(round(t / DT)), min(n, int(round((t + dur) / DT)))
        obj[a:b_] = (vi, vd)
        contra_tope[a:b_] = nombre.startswith("contra el tope")
        for k in range(a, b_):
            nombres[k] = nombre
        t += dur
    vel = np.zeros((n, 2))
    i_mot = np.zeros((n, 2))
    duty = np.zeros((n, 2))
    actual = np.zeros(2)
    for k in range(n):
        antes = actual.copy()
        # Rampa: el control limita la aceleracion a `aceleracion_max_m_s2` (no patina ni golpea el vaso).
        actual = actual + np.clip(obj[k] - actual, -a_max * DT, a_max * DT)
        acel = (actual - antes) / DT
        vel[k] = actual
        for w in (0, 1):
            if contra_tope[k]:
                # Entra de reversa con el PWM bajo (0,35) y se ahoga contra el tope: rueda quieta,
                # sin fuerza contraelectromotriz → I = D·V / (R + R_TB6612).
                d = 0.35
                im = d * v_bateria / (TT_R + TB6612_R)
            elif abs(actual[w]) < 1e-4 and abs(obj[k][w]) < 1e-4:
                d, im = 0.0, 0.0                                     # motor apagado
            else:
                omega = abs(actual[w]) / r
                # Par en la rueda: rodadura (media masa por rueda) + acelerar (solo si acelera).
                fuerza = CRR * masa * 9.81 / 2 + max(0.0, masa / 2 * acel[w] * np.sign(actual[w] or 1))
                par = fuerza * r
                im = TT_I0 + par / (TT_KE * TT_ETA_CAJA)
                d = min(1.0, (im * (TT_R + TB6612_R) + TT_KE * omega) / v_bateria)
            i_mot[k, w], duty[k, w] = im, d
    # Logica: ESP32 con latido cada 250 ms, sensores, HC-SR04 (5 V). Regulador lineal: lo
    # que entra desde la bateria es lo mismo que sale (+ ~5 mA de reposo de cada regulador).
    logica = np.full(n, CARGAS["esp32_carro"][1] + CARGAS["ir5"][1] + CARGAS["tcrt_cuna"][1] + 2 * CARGAS["h206"][1]
                     + CARGAS["vl53"][1] + CARGAS["tb6612_logica"][1] + CARGAS["hcsr04"][1] + 0.010)
    for tx in np.arange(0, total, 0.25):
        a = int(round(tx / DT))
        if a < n:
            logica[a] += CARGAS["esp32_carro"][3] - CARGAS["esp32_carro"][1]
    bat_motores = (duty * i_mot).sum(axis=1)       # corriente media de bateria de un puente PWM = D · I_motor
    bateria = bat_motores + logica
    return {"t": tiempo, "tramos": tramos, "nombres": nombres, "v_bateria": v_bateria,
            "series": {"BAT": bateria, "motores": bat_motores, "5VC": logica, "motor_izq": i_mot[:, 0],
                       "motor_der": i_mot[:, 1], "duty_izq": duty[:, 0], "duty_der": duty[:, 1],
                       "v_izq": vel[:, 0], "v_der": vel[:, 1]}}


# ===========================================================================
# 5. Resumen: picos, promedios, margenes
# ===========================================================================

def estad(serie) -> tuple[float, float]:
    """(promedio, pico) de una serie."""
    return float(np.mean(serie)), float(np.max(serie))


FUSIBLES = {  # nombre: (A, rama de la simulacion, que protege)
    "F1": (5.0, "F1", "rama de 12 V del buck de 6 V (servos)"),
    "F2": (2.0, "F2", "rama de 12 V del buck de 5 V"),
    "F3": (3.0, "F3", "VMOT de los dos A4988"),
    "F4": (1.0, "F4", "sensores de 12 V y LEDs de los optoacopladores"),
    "F carro": (3.0, "BAT", "todo el carro (después del interruptor)"),
}


def resumen(planta: dict | None = None, carro: dict | None = None) -> dict:
    p = cargar_parametros()
    planta = planta or simular_planta(p)
    carro = carro or simular_carro(p)
    sp, sc = planta["series"], carro["series"]
    rieles = {}
    for rid, serie in (("12V", sp["12V"]), ("6V", sp["6V"]), ("5V", sp["5V"]), ("3V3F", sp["3V3F"]),
                       ("USB", sp["USB"]), ("BAT", sc["BAT"]), ("5VC", sc["5VC"])):
        prom, pico = estad(serie)
        lim = RIELES[rid].limite_a
        rieles[rid] = {"promedio": prom, "pico": pico, "limite": lim, "uso_pico": pico / lim,
                       "margen": 1 - pico / lim}
    fus = {}
    for nombre, (amp, rama, que) in FUSIBLES.items():
        prom, pico = estad(sp[rama] if rama in sp else sc[rama])
        fus[nombre] = {"amperios": amp, "promedio": prom, "pico": pico, "que": que, "margen": 1 - pico / amp}
    # Reguladores: potencia que sale, rendimiento, lo que se calienta.
    reg = {}
    p6, p5 = estad(sp["6V"] * 6.0), estad(sp["5V"] * 5.0)
    reg["XL4016 (6 V)"] = {"sale_W": p6, "eta": ETA_XL4016, "disipa_W": tuple(x * (1 / ETA_XL4016 - 1) for x in p6)}
    reg["LM2596 (5 V)"] = {"sale_W": p5, "eta": ETA_LM2596, "disipa_W": tuple(x * (1 / ETA_LM2596 - 1) for x in p5)}
    i33 = estad(sp["3V3F"])
    reg["AMS1117-3.3 (ESP32 fijo)"] = {"sale_W": tuple(3.3 * x for x in i33), "eta": 3.3 / 5.0,
                                       "disipa_W": tuple((5.0 - 3.3) * x for x in i33)}
    i5c = estad(sc["5VC"])
    reg["5 V lineal del carro (8,4 V, batería llena)"] = {"sale_W": tuple(5 * x for x in i5c), "eta": 5 / 8.4,
                                                        "disipa_W": tuple((8.4 - 5.0) * x for x in i5c)}
    reg["5 V lineal del carro (7,4 V)"] = {"sale_W": tuple(5 * x for x in i5c), "eta": 5 / 7.4,
                                         "disipa_W": tuple((7.4 - 5.0) * x for x in i5c)}
    # Red y bateria.
    red_w, red_a = estad(sp["red_W"]), estad(sp["red_A"])
    bat_prom = rieles["BAT"]["promedio"]
    espera = CARGAS["esp32_carro"][1] + CARGAS["ir5"][1] + CARGAS["tcrt_cuna"][1] + 2 * CARGAS["h206"][1] + \
        CARGAS["vl53"][1] + CARGAS["tb6612_logica"][1] + CARGAS["hcsr04"][1] + 0.010
    util_ah = CAPACIDAD_MAH / 1000 * FRACCION_UTIL
    duracion_recorrido = float(carro["t"][-1] + DT)
    autonomia = {"util_mah": util_ah * 1000, "recorrido_s": duracion_recorrido, "i_recorrido": bat_prom,
                 "h_recorriendo": util_ah / bat_prom, "i_espera": espera, "h_esperando": util_ah / espera,
                 "recorridos_por_carga": util_ah / bat_prom * 3600 / duracion_recorrido,
                 "v_min_pico": carro["v_bateria"] - rieles["BAT"]["pico"] * R_BATERIA,
                 "duty_max": float(max(np.max(sc["duty_izq"]), np.max(sc["duty_der"]))),
                 "i_motor_max": float(max(np.max(sc["motor_izq"]), np.max(sc["motor_der"])))}
    return {"rieles": rieles, "fusibles": fus, "reguladores": reg, "red_W": red_w, "red_A": red_a,
            "autonomia": autonomia, "planta": planta, "carro": carro, "peores": peores_casos()}


def peores_casos() -> list[dict]:
    """Casos que la simulacion normal no recorre, calculados a mano (condiciones limite)."""
    sg, mg = CARGAS["SG90"][3], CARGAS["MG996R"][3]
    todos = 2 * mg + 4 * sg
    con_regla = mg + 4 * sg
    def f1(i6):
        return i6 * 6 / (ETA_XL4016 * 12) + IQ_BUCK
    motor_100 = 8.4 / (TT_R + TB6612_R)
    motor_70 = 0.70 * 8.4 / (TT_R + TB6612_R)
    return [
        {"caso": "Los 6 servos trabados a la vez (sin la regla prensa/empujador)", "riel": "6 V",
         "i": todos, "limite": 8.0, "fusible": f"F1: {_n(f1(todos))} A de 5 A"},
        {"caso": "Prensa trabada + los 4 SG90 trabados (respetando la regla)", "riel": "6 V",
         "i": con_regla, "limite": 8.0, "fusible": f"F1: {_n(f1(con_regla))} A de 5 A"},
        {"caso": "Un motor TT trabado con PWM 100 % y batería llena (8,4 V)", "riel": "TB6612 (por canal)",
         "i": motor_100, "limite": TB6612_I_CONT, "fusible": f"2 motores: {_n(2 * motor_100 + 0.4)} A de 3 A"},
        {"caso": "Un motor TT trabado con PWM limitado a 70 %", "riel": "TB6612 (por canal)",
         "i": motor_70, "limite": TB6612_I_CONT, "fusible": f"2 motores: {_n(2 * 0.7 * motor_70 + 0.4)} A de 3 A (batería)"},
    ]


# ===========================================================================
# 6. Pasivos calculados
# ===========================================================================

V_GPIO_MAX = 3.6    # V: maximo absoluto de un GPIO del ESP32 (VDD + 0,3 V)
VIH_MIN = 0.75 * 3.3   # 2,475 V: lo minimo que el ESP32 lee como "1"
VIL_MAX = 0.25 * 3.3   # 0,825 V: lo maximo que lee como "0"


def vref_a4988(i_fase: float = I_TRIP) -> dict:
    """I_trip = Vref / (8 · Rs): la resistencia de sensado Rs depende del fabricante del modulo."""
    return {rs: 8 * rs * i_fase for rs in (0.050, 0.068, 0.100)}


def divisor_echo(v_echo: float = 5.0, r_arriba: float = 1000, r_abajo: float = 2000) -> dict:
    v = v_echo * r_abajo / (r_arriba + r_abajo)
    return {"v_gpio": v, "v_gpio_echo_bajo": 4.5 * r_abajo / (r_arriba + r_abajo), "i_ma": v_echo / (r_arriba + r_abajo) * 1000,
            "r_thevenin": r_arriba * r_abajo / (r_arriba + r_abajo),
            "tau_ns": r_arriba * r_abajo / (r_arriba + r_abajo) * 20e-12 * 1e9}


def pullup_i2c(r: float = 2200, c_pf: float = 170) -> dict:
    """Tiempo de subida 30 %→70 %: t_r = 0,8473 · R · C (formula de la norma I2C)."""
    tr = 0.8473 * r * c_pf * 1e-12 * 1e9
    return {"tr_ns": tr, "max_100k_ns": 1000, "max_400k_ns": 300, "r_min": (3.3 - 0.4) / 0.003,
            "i_bajo_ma": 3.3 / r * 1000}


def pullup_hall(r: float = 10000) -> dict:
    return {"i_ma": 3.3 / r * 1000, "v_bajo": 0.15, "vil_max": VIL_MAX}


def opto_pc817(v: float = 12.0, r: float = 2200, vf: float = 1.2, v_npn: float = 1.0, ctr_min: float = 0.5,
               r_pullup: float = 10000) -> dict:
    i_f = (v - vf - v_npn) / r
    i_f_peor = (v * 0.95 - vf - 1.5) / r          # fuente 5 % baja y el NPN del sensor con 1,5 V
    i_c_disp = i_f_peor * ctr_min
    i_c_nec = 3.3 / r_pullup
    return {"i_f_ma": i_f * 1000, "i_f_peor_ma": i_f_peor * 1000, "ic_disp_ma": i_c_disp * 1000,
            "ic_nec_ma": i_c_nec * 1000, "satura": i_c_disp > 2 * i_c_nec, "p_r_mw": (v - vf - v_npn) ** 2 / r * 1000}


def condensadores() -> dict:
    """ΔV = I · Δt / C: cuanto cae el riel mientras el regulador reacciona."""
    return {"pca_1000uF": {"i": 2.5, "dt_us": 100, "dv": 2.5 * 100e-6 / 1000e-6},
            "vmot_100uF": {"i": 1.0, "dt_us": 20, "dv": 1.0 * 20e-6 / 100e-6}}


def filtro_motor_tt(c: float = 100e-9, v: float = 8.4) -> dict:
    z_pwm = 1 / (2 * math.pi * 1000 * c)
    z_1mhz = 1 / (2 * math.pi * 1e6 * c)
    p_pwm = c * v ** 2 * 1000                   # ½CV² por flanco, 2 flancos por periodo a 1 kHz
    return {"z_1khz": z_pwm, "z_1mhz": z_1mhz, "p_mw_1khz": p_pwm * 1000, "p_mw_20khz": c * v ** 2 * 20000 * 1000}


def pwm_motor_tt(v_motor: float = 6.0) -> dict:
    return {vb: v_motor / vb for vb in (8.4, 7.4, 6.4)}


# ===========================================================================
# 7. Cada hilo de conexiones.py: voltaje, corriente, cable, caida, proteccion
# ===========================================================================

def _i(serie) -> tuple[float, float]:
    return estad(serie)


def electrica_hilo(cable: dict, hilo: dict, R: dict) -> dict:
    """Voltaje, nivel, corriente (nominal, pico) y proteccion de un hilo. `R` son las
    series de la simulacion. Si un cable nuevo de conexiones.py no calza en ninguna
    regla, lanza KeyError: la prueba lo detecta (asi nadie agrega un hilo sin voltaje)."""
    sp, sc = R["planta"]["series"], R["carro"]["series"]
    cid, f = cable["id"], hilo["funcion"]
    fl = f.lower()
    de, a = hilo["de"], hilo["a"]
    ctx = (cid, f)

    def gnd_o(v, nivel, corr, prot):
        if "gnd" in fl or fl in ("0 v",) or "−" == fl or "neutro" in fl:
            return {"v": 0.0, "nivel": "0 V (retorno)", "i": corr, "prot": prot}
        return {"v": v, "nivel": nivel, "i": corr, "prot": prot}

    mA = lambda n, p_: (n / 1000, p_ / 1000)
    if cid == "p_red":
        if "tierra" in fl:
            return {"v": 0.0, "nivel": "tierra de protección (PE)", "i": (0.0, 0.0), "prot": "—"}
        return {"v": 0.0 if "neutro" in fl else V_RED, "nivel": "110 V AC" if "fase" in fl else "neutro (≈0 V)",
                "i": _i(sp["red_A"]), "prot": "fusible de la entrada IEC"}
    if cid == "p_12":
        i = _i(sp["12V"])
        if "gnd" in fl:
            i = (i[0] / 2, i[1] / 2)                   # dos hilos de GND en paralelo (-V1 y -V2)
        return gnd_o(12.0, "+12 V DC", i, "límite de la fuente (10 A)")
    if cid == "p_buck6":
        if "IN" in de or "IN" in a:
            return gnd_o(12.0, "+12 V DC", _i(sp["F1"]), "F1 5 A")
        return gnd_o(6.0, "+6 V DC", _i(sp["6V"]), "F1 5 A (del lado de 12 V)")
    if cid == "p_buck5":
        if "IN" in de or "IN" in a:
            return gnd_o(12.0, "+12 V DC", _i(sp["F2"]), "F2 2 A")
        return gnd_o(5.0, "+5 V DC", _i(sp["5V"] - sp["ventilador"]), "F2 2 A (del lado de 12 V)")
    if cid == "p_f3f4":
        return {"v": 12.0, "nivel": "+12 V DC", "i": _i(sp["F3"] if "F3" in de else sp["F4"]),
                "prot": "F3 3 A" if "F3" in de else "F4 1 A"}
    if cid == "p_pca":
        return gnd_o(6.0, "+6 V DC", _i(sp["6V"]), "F1 5 A")
    if cid == "p_drv":
        return gnd_o(12.0, "+12 V DC", _i(sp["F3"]), "F3 3 A")
    if cid == "p_uln":
        return gnd_o(5.0, "+5 V DC", _i(sp["carrusel"]), "F2 2 A")
    if cid == "p_opto":
        return {"v": 12.0, "nivel": "+12 V DC", "i": mA(4.5, 9.4), "prot": "F4 1 A"}
    if cid == "p_vent":
        return gnd_o(5.0, "+5 V DC", _i(sp["ventilador"]), "F2 2 A")
    if cid == "p_gnd":
        return {"v": 0.0, "nivel": "0 V (une el GND del USB con el de la fuente)", "i": mA(5, 20),
                "prot": "— (solo retornos de señal)"}
    if cid == "l_i2c0":
        if "3,3" in f:
            return {"v": 3.3, "nivel": "+3,3 V", "i": mA(6, 10), "prot": "regulador del ESP32"}
        if "gnd" in fl:
            return {"v": 0.0, "nivel": "0 V", "i": mA(6, 10), "prot": "regulador del ESP32"}
        return {"v": 3.3, "nivel": "I2C 0/3,3 V, 400 kHz (colector abierto)", "i": mA(0.3, 1.5), "prot": "—"}
    if cid == "l_drv":
        if "3,3" in f or "gnd" in fl:
            return gnd_o(3.3, "+3,3 V", mA(10, 16), "regulador del ESP32")
        return {"v": 3.3, "nivel": "lógica 0/3,3 V (STEP: pulsos ~1,3 kHz)" if "STEP" in f else "lógica 0/3,3 V",
                "i": mA(0.01, 0.02), "prot": "—"}
    if cid == "l_uln":
        return {"v": 3.3, "nivel": "lógica 0/3,3 V → base del Darlington", "i": mA(0.7, 0.7), "prot": "—"}
    if cid == "l_opto":
        if "3,3" in f or "gnd" in fl:
            return gnd_o(3.3, "+3,3 V (pull-ups)", mA(0.66, 0.66), "regulador del ESP32")
        return {"v": 3.3, "nivel": "0/3,3 V (activo en bajo)", "i": mA(0.33, 0.33), "prot": "—"}
    if cid == "l_i2c1":
        if "3,3" in f or "gnd" in fl:
            return gnd_o(3.3, "+3,3 V", mA(38, 80), "regulador del ESP32")
        return {"v": 3.3, "nivel": "I2C 0/3,3 V, 100 kHz (pull-ups 2,2 kΩ)", "i": mA(0.5, 1.5), "prot": "—"}
    if cid == "presencia":
        if "señal" in fl:
            return {"v": 3.3, "nivel": "0/3,3 V (activo en bajo)", "i": mA(0.01, 0.33), "prot": "—"}
        return gnd_o(3.3, "+3,3 V", mA(12, 15), "regulador del ESP32")
    if cid in ("capacitivo", "inductivo"):
        if "npn" in fl:
            return {"v": 12.0, "nivel": "salida NPN: ~11 V libre / <1,5 V al detectar", "i": mA(4.5, 4.7), "prot": "F4 1 A"}
        if "+12" in f:
            return {"v": 12.0, "nivel": "+12 V DC", "i": mA(8, 15), "prot": "F4 1 A"}
        return {"v": 0.0, "nivel": "0 V", "i": mA(12.5, 19.7), "prot": "F4 1 A"}
    if cid == "hall":
        if "señal" in fl:
            return {"v": 3.3, "nivel": "0/3,3 V (colector abierto, pull-up 10 kΩ)", "i": mA(0.33, 0.33), "prot": "—"}
        return gnd_o(3.3, "+3,3 V", mA(5, 10), "regulador del ESP32")
    if cid in ("vl53_interior", "vl53_cortina"):
        if "xshut" in fl:
            return {"v": 3.3, "nivel": "lógica 0/3,3 V", "i": mA(0.01, 0.33), "prot": "—"}
        if f in ("SCL", "SDA"):
            return {"v": 3.3, "nivel": "I2C 0/3,3 V, 100 kHz", "i": mA(0.5, 1.5), "prot": "—"}
        return gnd_o(3.3, "+3,3 V", mA(19, 40), "regulador del ESP32")
    if cid in ("motor_monedas", "motor_vasos"):
        return {"v": 12.0, "nivel": "bobina: 12 V troceado por el A4988 (±12 V, ~1,5 V medio)",
                "i": (I_TRIP / math.sqrt(2), I_TRIP), "prot": "F3 3 A (VMOT)"}
    if cid == "motor_carrusel":
        if "+5" in f:
            return {"v": 5.0, "nivel": "+5 V común de las bobinas", "i": (0.15, 0.24), "prot": "F2 2 A"}
        return {"v": 5.0, "nivel": "5 V / 0 V (el ULN2003 la lleva a GND)", "i": (0.05, 0.1), "prot": "F2 2 A"}
    if cid.startswith("servo_"):
        nombre = de.split(".")[0].replace("servo_", "")      # "servo_prensa.CABLE" -> "prensa"
        serie = sp["servo_" + nombre]
        if "pwm" in fl:
            return {"v": 3.3, "nivel": "PWM 50 Hz, 0,5-2,5 ms, 0/3,3 V (del PCA9685)", "i": mA(0.05, 0.1), "prot": "—"}
        return gnd_o(6.0, "+6 V DC", _i(serie), "F1 5 A")
    if cid in ("panel_luz", "anillo"):
        return gnd_o(5.0, "+5 V DC", _i(sp["panel" if cid == "panel_luz" else "anillo"]), "F2 2 A")
    if cid.startswith("usb_"):
        corr = {"usb_cenital": (0.25, 0.35), "usb_vasos": (0.20, 0.25), "usb_esp": _i(sp["USB_ESP"]),
                "usb_pc": (0.0, 0.05)}[cid]
        return {"v": 5.0, "nivel": "USB 2.0: VBUS 5 V + datos diferenciales", "i": corr,
                "prot": "limitador del puerto del hub (0,5 A)"}
    if cid == "c_bat":
        if "jack" in a.lower():
            return gnd_o(7.4, "+7,4 V (6,0-8,4 V)", _i(sc["5VC"]), "fusible del carro 3 A")
        if "motores" in fl or "potencia" in fl:
            return gnd_o(7.4, "+7,4 V (6,0-8,4 V)", _i(sc["motores"]), "fusible del carro 3 A")
        return {"v": 7.4, "nivel": "+7,4 V (6,0-8,4 V)", "i": _i(sc["BAT"]), "prot": "fusible del carro 3 A"}
    if cid == "c_tb":
        if "3,3" in f or "gnd" in fl:
            return gnd_o(3.3, "+3,3 V", mA(2, 2), "regulador del ESP32")
        return {"v": 3.3, "nivel": "PWM 1 kHz 0/3,3 V" if "PWM" in f else "lógica 0/3,3 V", "i": mA(0.01, 0.02),
                "prot": "—"}
    if cid == "c_mot":
        serie = sc["motor_izq"] if "A" in f else sc["motor_der"]
        return {"v": 7.4, "nivel": "PWM 1 kHz de 0 a V_batería (medio ≤ ~6 V)", "i": _i(serie),
                "prot": "TB6612 (1,2 A por canal) + fusible 3 A"}
    if cid == "c_enc":
        if "pulsos" in fl:
            return {"v": 3.3, "nivel": "pulsos 0/3,3 V (hasta ~120 por s)", "i": mA(0.01, 0.33), "prot": "—"}
        return gnd_o(3.3, "+3,3 V", mA(12, 15), "regulador del ESP32")
    if cid == "c_ir":
        if fl.startswith("ir"):
            return {"v": 3.3, "nivel": "0/3,3 V (1 = negro)", "i": mA(0.01, 0.33), "prot": "—"}
        return gnd_o(3.3, "+3,3 V", mA(50, 60), "regulador del ESP32")
    if cid == "c_us":
        if "ECHO" in f:
            d = divisor_echo()
            return {"v": 5.0, "nivel": f"5 V en el sensor → {_n(d['v_gpio'])} V en el GPIO (divisor)",
                    "i": mA(0, d["i_ma"]), "prot": "divisor 1 kΩ / 2 kΩ"}
        if "TRIG" in f:
            return {"v": 3.3, "nivel": "pulso de 10 µs a 3,3 V (el HC-SR04 lo lee como 1)", "i": mA(0.01, 0.05), "prot": "—"}
        return gnd_o(5.0, "+5 V", mA(15, 15), "regulador 5 V del carro")
    if cid == "c_tof":
        if "SCL" in f or "SDA" in f:
            return {"v": 3.3, "nivel": "I2C 0/3,3 V, 400 kHz (bus corto)", "i": mA(0.3, 1.5), "prot": "—"}
        return gnd_o(3.3, "+3,3 V", mA(19, 40), "regulador del ESP32")
    if cid == "c_cuna":
        if "vaso" in fl:
            return {"v": 3.3, "nivel": "0/3,3 V (activo en bajo)", "i": mA(0.01, 0.33), "prot": "—"}
        return gnd_o(3.3, "+3,3 V", mA(12, 15), "regulador del ESP32")
    raise KeyError(f"sin regla eléctrica para el hilo {ctx}")


def tabla_hilos(R: dict | None = None) -> list[dict]:
    """Una fila por hilo de conexiones.py con todo lo electrico."""
    R = R or resumen()
    filas = []
    for cable in cx.CABLES:
        for hilo in cable["hilos"]:
            e = electrica_hilo(cable, hilo, R)
            awg, largo = cable_fisico(cable, hilo)
            ohm = OHM_POR_M[awg] * largo
            filas.append({"cable": cable["id"], "nombre": cable["nombre"], "de": hilo["de"], "a": hilo["a"],
                          "funcion": hilo["funcion"], "v": e["v"], "nivel": e["nivel"], "i_nom": e["i"][0],
                          "i_pico": e["i"][1], "awg": awg, "largo": largo, "ohm": ohm,
                          "caida": e["i"][1] * ohm, "prot": e["prot"]})
    return filas


def caidas_por_carga(filas: list[dict]) -> list[dict]:
    """Caida ida + vuelta (hilo positivo + GND) de las cargas de potencia, en su pico, y el
    voltaje que le queda a la carga."""
    por_cable = {}
    for f in filas:
        por_cable.setdefault(f["cable"], []).append(f)
    out = []
    for cid, v_nom, tol in (("servo_3", 6.0, 4.8), ("servo_4", 6.0, 4.8), ("servo_1", 6.0, 4.8),
                            ("panel_luz", 5.0, 4.5), ("anillo", 5.0, 4.5), ("capacitivo", 12.0, 10.0),
                            ("hall", 3.3, 3.0), ("vl53_interior", 3.3, 2.6), ("presencia", 3.3, 3.0)):
        hs = por_cable[cid]
        ida = max(h["caida"] for h in hs if h["v"] > 0 and "señal" not in h["funcion"] and "PWM" not in h["funcion"]
                  and h["funcion"] not in ("SCL", "SDA") and "NPN" not in h["funcion"] and "XSHUT" not in h["funcion"])
        vuelta = max(h["caida"] for h in hs if h["v"] == 0)
        extra = 0.0
        if cid.startswith("servo"):
            # + la bornera V+ del PCA9685 (18 AWG, ida y vuelta) con toda la corriente de 6 V.
            extra = sum(h["caida"] for h in por_cable["p_pca"])
        out.append({"carga": hs[0]["nombre"], "v_nom": v_nom, "caida": ida + vuelta + extra,
                    "v_carga": v_nom - ida - vuelta - extra, "minimo": tol})
    # Webcams: VBUS + GND del cable USB (28 AWG) de ida y vuelta.
    for cid, nombre in (("usb_cenital", "Webcam cenital"), ("usb_vasos", "Webcam de vasos")):
        f = por_cable[cid][0]
        out.append({"carga": nombre + " (cable USB)", "v_nom": 5.0, "caida": 2 * f["caida"],
                    "v_carga": 5.0 - 2 * f["caida"], "minimo": 4.75})
    return out


# ===========================================================================
# 8. Graficas y documento
# ===========================================================================

# Paleta categorica de referencia (skill de visualizacion): orden fijo, nunca ciclado.
COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]


def generar_graficas(R: dict) -> dict[str, Path] | None:
    """PNG de los dos recorridos. Sin matplotlib devuelve None (el .md usa mermaid)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#8a8a86", "axes.labelcolor": "#52514e", "xtick.color": "#52514e",
                         "ytick.color": "#52514e", "axes.titlesize": 10, "axes.titleweight": "bold"})
    salidas = {}
    sp, t = R["planta"]["series"], R["planta"]["t"]
    # Un panel por riel (una sola escala por panel: nada de doble eje), con su limite.
    paneles = [("12V", "12 V de la fuente (A)", "12V", 10.0), ("6V", "6 V de los servos (A)", "6V", 8.0),
               ("5V", "5 V de la caja (A)", "5V", 3.0), ("USB", "5 V del hub USB (A)", "USB", 2.0)]
    fig, ejes = plt.subplots(len(paneles), 1, figsize=(10, 9), sharex=True, facecolor="#fcfcfb")
    for eje, (clave, titulo, rid, lim), color in zip(ejes, paneles, COLORES):
        eje.set_facecolor("#fcfcfb")
        eje.plot(t, sp[clave], color=color, lw=1.4)
        prom, pico = estad(sp[clave])
        eje.axhline(prom, color="#52514e", lw=0.8, ls=":")
        eje.set_title(f"{titulo}   pico {_n(pico)} A · promedio {_n(prom)} A · límite {lim:g} A", loc="left")
        eje.set_ylim(0, max(pico * 1.25, 0.1))
        eje.grid(axis="y", color="#e4e3df", lw=0.6)
    ejes[-1].set_xlabel("tiempo (s) — ciclo real de la planta, paso de 10 ms")
    fig.tight_layout()
    ruta = CAPTURAS / "electrica-ciclo-planta.png"
    fig.savefig(ruta, dpi=110)
    plt.close(fig)
    salidas["planta"] = ruta

    sc, tc = R["carro"]["series"], R["carro"]["t"]
    fig, ejes = plt.subplots(3, 1, figsize=(10, 7.5), sharex=True, facecolor="#fcfcfb")
    datos = [(sc["BAT"], "Corriente de la batería (A)", COLORES[0]),
             (sc["motor_izq"], "Corriente del motor izquierdo (A)", COLORES[1]),
             (sc["motor_der"], "Corriente del motor derecho (A)", COLORES[2])]
    for eje, (serie, titulo, color) in zip(ejes, datos):
        eje.set_facecolor("#fcfcfb")
        eje.plot(tc, serie, color=color, lw=0.8)
        prom, pico = estad(serie)
        eje.set_title(f"{titulo}   pico {_n(pico)} A · promedio {_n(prom)} A", loc="left")
        eje.grid(axis="y", color="#e4e3df", lw=0.6)
        eje.set_ylim(0, max(pico * 1.25, 0.1))
    # Marcas de las fases del recorrido (texto en tinta neutra, no en el color de la serie).
    # Una marca por muro (el "detenido" de 0,3 s parte la maniobra en dos: se ignora lo que
    # cae a menos de 8 s de la marca anterior).
    t0, ultima = 0.0, -99.0
    for dur, _, _, nombre in R["carro"]["tramos"]:
        texto = {"frena ante el muro": "muro: evasión", "en la meta (sacan el vaso)": "meta",
                 "contra el tope (PWM bajo)": "tope del muelle"}.get(nombre)
        if texto and t0 - ultima > 8:
            ejes[0].axvline(t0, color="#b5b4ae", lw=0.6)
            ejes[0].text(t0 + 0.4, ejes[0].get_ylim()[1] * 0.9, texto, fontsize=7, color="#52514e")
            ultima = t0
        t0 += dur
    ejes[-1].set_xlabel(f"tiempo (s) — recorrido completo del carro con la batería a {_n(R['carro']['v_bateria'], 1)} V")
    fig.tight_layout()
    ruta = CAPTURAS / "electrica-ciclo-carro.png"
    fig.savefig(ruta, dpi=110)
    plt.close(fig)
    salidas["carro"] = ruta
    return salidas


def _n(x, d=2):
    """Numero con coma decimal (como el resto de la documentacion)."""
    return f"{x:.{d}f}".replace(".", ",")


def _ma(a):
    if a == 0:
        return "0"
    if a < 0.001:
        return f"{a * 1e6:.0f} µA"
    return f"{a * 1000:.0f} mA" if a < 1 else f"{_n(a)} A"


def _xychart(t, serie, titulo, paso=50) -> str:
    vals = ", ".join(_n(v, 2).replace(",", ".") for v in serie[::paso])
    return (f"```mermaid\nxychart-beta\n  title \"{titulo}\"\n  x-axis \"tiempo (x{paso * DT:g} s)\" 0 --> {len(serie[::paso])}\n"
            f"  y-axis \"A\"\n  line [{vals}]\n```\n")


def generar_markdown(graficas: bool = True) -> str:
    p = cargar_parametros()
    R = resumen()
    filas = tabla_hilos(R)
    img = generar_graficas(R) if graficas else None
    ri, fu, rg, au = R["rieles"], R["fusibles"], R["reguladores"], R["autonomia"]
    L = []
    w = L.append
    w("# Parte eléctrica, punto por punto (simulada)\n")
    w("> Generado por `python -m sim.electrica` desde `sim/electrica.py`, que lee el conexionado de "
      "`sim/conexiones.py` (la fuente única de cada hilo) y los tiempos de `config/parametros.yaml`. "
      "No editar a mano. Las corrientes son de hoja de datos (**PROVISIONALES** hasta medirlas con el "
      "multímetro en el montaje); la lista de lo que hay que medir está al final.\n")
    w("Esta página responde, para cada fuente, regulador, fusible y cable: **¿aguanta lo que le piden en el "
      "peor momento real del ciclo?** Para eso se recorre en el tiempo, con paso de 10 ms, un ciclo real de la "
      "planta y un recorrido completo del carro, sumando la corriente de cada carga en su riel. El circuito "
      "también se puede ver y mover en el simulador Wokwi: [wokwi/](../wokwi/README.md).\n")

    w("## 1. Qué es un riel de alimentación y cuáles hay\n")
    w("Un **riel** es una línea de voltaje fijo de la que se alimentan varias cargas (como una regleta). No se "
      "usa un solo voltaje para todo porque cada pieza pide el suyo: los servos se queman o se vuelven erráticos "
      "por encima de 6-7,2 V, el ESP32 trabaja a 3,3 V (sus pines no aguantan más de 3,6 V), los sensores "
      "industriales M18 piden 6-36 V y los paso a paso rinden mejor con 12 V (la corriente sube más rápido en la "
      "bobina). Separar rieles además aísla el ruido: el golpe de corriente de un servo que arranca no llega al "
      "ESP32.\n")
    w("| Riel | Lo genera | Para qué | Límite |")
    w("|---|---|---|---|")
    for r in RIELES.values():
        w(f"| **{r.nombre}** | {r.origen} | {r.para_que} | {r.limite_texto} |")
    w("")
    w("Un **buck** (XL4016, LM2596) es un regulador conmutado: prende y apaga un transistor miles de veces por "
      "segundo y filtra con una bobina, así que baja el voltaje perdiendo solo ~10-20 % en calor. Un regulador "
      "**lineal** (el AMS1117 del ESP32) quema como calor TODA la diferencia de voltaje por la corriente: sirve "
      "para corrientes chicas o diferencias chicas.\n")

    w("## 2. Diagrama de bloques de potencia\n")
    w("```mermaid\nflowchart LR\n"
      "  RED[\"Red 110 V AC\"] --> IEC[\"Entrada IEC<br/>interruptor + fusible\"] --> FTE[\"Fuente LRS-150<br/>12 V 10 A\"]\n"
      "  FTE --> FUS{{\"Portafusibles\"}}\n"
      "  FUS -- \"F1 5 A\" --> B6[\"Buck XL4016<br/>6 V\"] --> PCA[\"PCA9685 V+<br/>1000 µF\"] --> SERV[\"6 servos<br/>2 MG996R + 4 SG90\"]\n"
      "  FUS -- \"F2 2 A\" --> B5[\"Buck LM2596<br/>5 V\"] --> X5[\"Bornera 5 V\"]\n"
      "  X5 --> ULN[\"ULN2003 → 28BYJ-48\"]\n  X5 --> LUZ[\"Panel de luz + anillo\"]\n  B5 --> VEN[\"Ventilador\"]\n"
      "  FUS -- \"F3 3 A\" --> DRV[\"2 × A4988<br/>100 µF c/u\"] --> NEMA[\"2 × NEMA17\"]\n"
      "  FUS -- \"F4 1 A\" --> S12[\"Capacitivo + inductivo<br/>+ LEDs PC817\"]\n"
      "  HUB[\"Hub USB con fuente<br/>5 V\"] --> ESP[\"ESP32 fijo<br/>AMS1117 → 3,3 V\"] --> L33[\"Lógica 3,3 V:<br/>FC-51, KY-003, 2 VL53L0X,<br/>PCA9685, A4988, pull-ups\"]\n"
      "  HUB --> CAMS[\"2 webcams\"]\n  PC[\"Portátil\"] -. datos .- HUB\n"
      "  FTE -. \"GND en estrella (bornera X2)\" .- ESP\n"
      "  BAT[\"2 × 18650 + BMS<br/>6,0-8,4 V\"] --> SW[\"Interruptor + fusible 3 A\"]\n"
      "  SW --> TB[\"TB6612<br/>PWM ≤ 70 %\"] --> TT[\"2 motores TT<br/>100 nF c/u\"]\n"
      "  SW --> R5[\"Regulador 5 V<br/>de la placa GVS\"] --> ESPC[\"ESP32 carro → 3,3 V\"] --> LC[\"IR ×5, cuna, encoders, VL53L0X\"]\n"
      "  R5 --> US[\"HC-SR04\"]\n```\n")

    w("## 3. Cómo se simuló\n")
    w("- **Paso de 10 ms.** Un fusible necesita cientos de ms de sobrecorriente para abrir; un regulador reacciona "
      "en ~0,1 ms (eso lo cubren los condensadores, sección 7). 10 ms basta para ver cada arranque de servo.")
    w("- **Planta**: las dos cintas a la vez, con los tiempos de `tiempos_ms`: cinta de monedas cada "
      f"{p['tiempos_ms']['avance_casilla_monedas']} + {p['tiempos_ms']['pausa_casilla_monedas']} ms (desvío en una de cada dos "
      "piezas, carrusel un tubo en cada pausa); cinta de vasos: avance, tapa y prensa 0→180→0 (la leva aprieta la tapa 0,2 s "
      "contra el resorte: el servo casi trabado), y **después** el empujador (la regla de diseño: prensa y empujador nunca a la "
      "vez). En la ventana se suelta además un lote (carrusel media vuelta + obturador) y la canaleta le suelta un vaso al carro.")
    w("- **Servos**: al arrancar piden su corriente de trabado ~30 ms (el motor parte de cero y nada limita la corriente), "
      "después la de movimiento y al llegar la de reposo.")
    w(f"- **Paso a paso**: el A4988 es un *chopper*: saca de 12 V solo la POTENCIA (cobre I²·R = {_n(I_TRIP**2*NEMA_R_FASE)} W, "
      f"driver {_n(I_TRIP**2*A4988_RDS)} W, más el trabajo mecánico), no 1 A por fase. Quieto sigue a corriente plena "
      "(el A4988 no la reduce solo).")
    w("- **Carro**: modelo de motor DC (V = I·R + Ke·ω, par = Kt·I·η de la caja) con los datos típicos del TT 1:48 "
      f"(R ≈ {_n(TT_R,1)} Ω, {_n(TT_I0)} A sin carga, Ke ≈ {_n(TT_KE,3)} V·s/rad en la rueda); PWM necesario D = "
      "(I·R + Ke·ω)/V_batería y corriente de batería = D·I. Perfil del recorrido a partir de la pista y de las "
      "velocidades del control (arranque con rampa de 1 m/s², rectas a 0,40 m/s, curvas, 3 evasiones con giros "
      "sobre su eje, meta, media vuelta, vuelta y entrada de reversa contra el tope con PWM 35 %).\n")
    w("Cargas usadas (corriente en su propio riel):\n")
    w("| Carga | Riel | Reposo | Nominal | Pico | Dato |")
    w("|---|---|---|---|---|---|")
    for k, (riel, rep, nom, pic, dato) in CARGAS.items():
        w(f"| {k} | {RIELES[riel].nombre} | {_ma(rep)} | {_ma(nom)} | {_ma(pic)} | {dato} |")
    w("")

    w("## 4. Ciclo de la planta: corriente de cada riel\n")
    if img:
        w("![Corriente de cada riel durante un ciclo real de la planta](capturas/electrica-ciclo-planta.png)\n")
    else:
        w(_xychart(R["planta"]["t"], R["planta"]["series"]["6V"], "Riel de 6 V (servos)"))
    w("Los picos del riel de 6 V son los arranques de los servos y la prensa apretando la tapa; la base del de 12 V "
      "son los dos NEMA17 sosteniendo su posición. Presupuesto por riel:\n")
    w("| Riel | Promedio | Pico | Límite | Uso en el pico | Margen |")
    w("|---|---|---|---|---|---|")
    for rid, d in ri.items():
        w(f"| {RIELES[rid].nombre} | {_ma(d['promedio'])} | {_ma(d['pico'])} | {_n(d['limite'])} A | "
          f"{d['uso_pico']*100:.0f} % | {d['margen']*100:.0f} % |")
    w("")
    w(f"**Consumo desde la red**: {_n(R['red_W'][0],1)} W promedio y {_n(R['red_W'][1],1)} W de pico (fuente al "
      f"{ETA_FUENTE*100:.0f} % de rendimiento a esta carga baja, más {_n(P_VACIO_FUENTE)} W en vacío) → "
      f"{_n(R['red_A'][0])} A promedio a 110 V (factor de potencia ~{_n(FACTOR_POTENCIA)}: la LRS-150 no tiene PFC). "
      "Sin contar el portátil ni el adaptador del hub.\n")

    w("### Fusibles\n")
    w("Un fusible de cuchilla aguanta su corriente nominal indefinidamente y abre con ~2 veces en segundos: los "
      "picos de 30 ms de un servo no lo abren; lo que protege es un corto o un motor trabado de forma sostenida.\n")
    w("| Fusible | Protege | Promedio | Pico en el ciclo | Margen en el pico |")
    w("|---|---|---|---|---|")
    for nombre, d in fu.items():
        w(f"| {nombre} ({_n(d['amperios'],0)} A) | {d['que']} | {_ma(d['promedio'])} | {_ma(d['pico'])} | {d['margen']*100:.0f} % |")
    w("")
    w("### Reguladores: rendimiento y calor\n")
    w("| Regulador | Potencia que entrega (prom. / pico) | Rendimiento | Calor (prom. / pico) |")
    w("|---|---|---|---|")
    for nombre, d in rg.items():
        w(f"| {nombre} | {_n(d['sale_W'][0])} / {_n(d['sale_W'][1])} W | {d['eta']*100:.0f} % | "
          f"{_n(d['disipa_W'][0])} / {_n(d['disipa_W'][1])} W |")
    w("")
    w("### Peores casos (no ocurren en el ciclo normal; calculados)\n")
    w("| Caso | Riel | Corriente | Límite | Fusible |")
    w("|---|---|---|---|---|")
    for c in R["peores"]:
        ok = "✔" if c["i"] <= c["limite"] else "✘"
        w(f"| {c['caso']} | {c['riel']} | {_n(c['i'])} A {ok} | {_n(c['limite'])} A | {c['fusible']} |")
    w("")

    w("## 5. Recorrido del carro\n")
    if img:
        w("![Corriente de la batería y de cada motor durante un recorrido completo](capturas/electrica-ciclo-carro.png)\n")
    else:
        w(_xychart(R["carro"]["t"], R["carro"]["series"]["BAT"], "Corriente de la batería"))
    w(f"- Recorrido completo (salida, 3 evasiones, meta, vuelta, muelle): **{_n(au['recorrido_s'],0)} s**, "
      f"{_ma(au['i_recorrido'])} promedio de la batería, {_ma(ri['BAT']['pico'])} de pico.")
    w(f"- Motor: hasta {_ma(au['i_motor_max'])} (arranques y el tope del muelle); el PWM más alto pedido con la batería a "
      f"7,4 V fue {au['duty_max']*100:.0f} %.")
    w(f"- Voltaje de la batería en el pico: {_n(au['v_min_pico'])} V (resistencia interna + BMS + fusible + interruptor ≈ "
      f"{_n(R_BATERIA*1000,0)} mΩ).")
    w(f"- **Autonomía** con {CAPACIDAD_MAH} mAh útiles al {FRACCION_UTIL*100:.0f} % ({_n(au['util_mah'],0)} mAh): "
      f"**{_n(au['h_recorriendo'],1)} h andando** (≈ {au['recorridos_por_carga']:.0f} recorridos) o "
      f"**{_n(au['h_esperando'],1)} h esperando** en el muelle con la radio encendida ({_ma(au['i_espera'])}). "
      "La sustentación dura mucho menos: una carga alcanza sobrada.\n")

    w("## 6. Cada conexión, punto por punto\n")
    w("Una fila por hilo de `sim/conexiones.py` (la misma lista que dibuja el visor 3D y `docs/conexiones.md`). "
      "Corriente nominal = promedio en la simulación (o el consumo típico si la carga no cambia); pico = el máximo. "
      "Caída = corriente pico × resistencia de ESE hilo (la del circuito es ida + vuelta: sección 6.1). "
      "Calibre: 18 AWG potencia de la caja, 22 AWG servos/motores/M18, 24 AWG señales e I2C de campo, 26 AWG Dupont, "
      "28 AWG los hilos de alimentación de un cable USB.\n")
    w("| # | Cable | De → A | Señal | Voltaje | I nom / pico | Cable | Largo | Caída | Protección |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(filas, 1):
        w(f"| {i} | {f['cable']} | `{f['de']}` → `{f['a']}` | {f['funcion']} | {f['nivel']} | "
          f"{_ma(f['i_nom'])} / {_ma(f['i_pico'])} | {f['awg']} AWG ({_n(OHM_POR_M[f['awg']],3)} Ω/m) | "
          f"{_n(f['largo'])} m | {f['caida']*1000:.0f} mV | {f['prot']} |")
    w("")
    w("### 6.1 Caída de ida y vuelta en las cargas que importan\n")
    w("| Carga | Nominal | Caída total en el pico | Le llega | Mínimo que acepta |")
    w("|---|---|---|---|---|")
    for c in caidas_por_carga(filas):
        ok = "✔" if c["v_carga"] >= c["minimo"] else "✘"
        w(f"| {c['carga']} | {_n(c['v_nom'],1)} V | {c['caida']*1000:.0f} mV | {_n(c['v_carga'])} V {ok} | {_n(c['minimo'])} V |")
    w("")

    w("## 7. Valores de los pasivos, con su cálculo\n")
    vr = vref_a4988()
    w("**Vref del A4988 (1 A por fase).** El driver corta la corriente cuando la caída en su resistencia de sensado "
      "Rs llega a Vref/8: I_trip = Vref / (8·Rs) → Vref = 8·Rs·I. Rs está impresa en el módulo (R050, R068 o R100):\n")
    w("| Rs del módulo | Vref para 1 A |")
    w("|---|---|")
    for rs, v in vr.items():
        w(f"| {_n(rs,3)} Ω | **{_n(v,3)} V** |")
    w("\nSe mide con el multímetro entre el potenciómetro del módulo y GND, con el driver alimentado y sin pasos. "
      "1 A (el motor admite 1,7 A) deja el motor tibio (1,5 W de cobre) y al A4988 sin disipador forzado.\n")
    d = divisor_echo()
    w(f"**Divisor del ECHO del HC-SR04 (1 kΩ arriba, 2 kΩ abajo).** V_GPIO = 5 V · 2k/(1k+2k) = **{_n(d['v_gpio'])} V** "
      f"(< {_n(V_GPIO_MAX,1)} V máximo del pin y > {_n(VIH_MIN)} V que el ESP32 lee como 1). Si el ECHO de un clon sale "
      f"con 4,5 V: {_n(d['v_gpio_echo_bajo'])} V, sigue siendo 1. Consume {_n(d['i_ma'])} mA solo mientras ECHO está alto; "
      f"la resistencia vista es {d['r_thevenin']:.0f} Ω y con ~20 pF el retardo es {d['tau_ns']:.0f} ns (despreciable: "
      "1 mm de distancia son 5,8 µs).\n")
    for nombre, c in (("bus I2C 1 (largo, 1,7 m)", 170), ("bus I2C 0 (corto, al PCA9685, 10 kΩ del módulo)", 35)):
        r = 2200 if "largo" in nombre else 10000
        q = pullup_i2c(r, c)
        w(f"**Pull-ups del {nombre}: {_n(r / 1000, 1)} kΩ con ~{c} pF.** t_r = 0,8473·R·C = **{q['tr_ns']:.0f} ns** "
          f"(máximo 1000 ns a 100 kHz, 300 ns a 400 kHz). R mínima = (3,3 − 0,4 V)/3 mA = {q['r_min']:.0f} Ω: "
          f"{'cumple' if r >= q['r_min'] else 'NO cumple'}; con la línea en bajo circula {_n(q['i_bajo_ma'])} mA.\n")
    h = pullup_hall()
    w(f"**Pull-up de 10 kΩ del Hall en el GPIO 39** (el 39 no tiene pull-up interno). Con el A3144 conduciendo "
      f"pasan {_n(h['i_ma'])} mA y el pin queda en ~{_n(h['v_bajo'])} V (< {_n(h['vil_max'])} V = 0 seguro); suelto, 3,3 V.\n")
    o = opto_pc817()
    w(f"**Optoacoplador PC817 a 12 V (2,2 kΩ).** I_F = (12 − 1,2 V del LED − ~1 V del NPN del sensor)/2,2 kΩ = "
      f"**{_n(o['i_f_ma'])} mA** (peor caso, fuente 5 % baja y NPN con 1,5 V: {_n(o['i_f_peor_ma'])} mA). Con el CTR "
      f"mínimo del PC817 (50 %) el transistor puede llevar {_n(o['ic_disp_ma'])} mA y el pull-up de 10 kΩ solo pide "
      f"{_n(o['ic_nec_ma'])} mA: queda **saturado** (salida < 0,2 V) con {o['ic_disp_ma']/o['ic_nec_ma']:.0f}× de margen, "
      f"aunque el LED envejezca. La resistencia disipa {o['p_r_mw']:.0f} mW (una de 1/4 W sobra).\n")
    cd = condensadores()
    w(f"**1000 µF en la bornera V+ del PCA9685.** Cuando la prensa arranca pide 2,5 A de golpe; el buck tarda ~100 µs "
      f"en reaccionar y mientras tanto la corriente sale del condensador: ΔV = I·Δt/C = 2,5 A · 100 µs / 1000 µF = "
      f"**{_n(cd['pca_1000uF']['dv'])} V** (sin él, el pico viaja por el cable y el voltaje se hunde lo suficiente para "
      "reiniciar un servo). Voltaje nominal ≥ 10 V (16 V recomendado).\n")
    w(f"**100 µF en VMOT de cada A4988.** El chopper toma pulsos de hasta 1 A durante ~20 µs: ΔV = 1 A · 20 µs / 100 µF = "
      f"**{_n(cd['vmot_100uF']['dv'])} V** de rizado; además absorbe el pico LC al enchufar los 12 V (sin él puede subir a "
      "~2× y pasar los 35 V del A4988). Voltaje nominal ≥ 25 V.\n")
    fm = filtro_motor_tt()
    w(f"**100 nF en los bornes de cada motor TT.** Las escobillas generan chispas de MHz: a 1 MHz el condensador es "
      f"{_n(fm['z_1mhz'],1)} Ω (las cortocircuita), a la frecuencia del PWM (1 kHz) es {fm['z_1khz']:.0f} Ω (casi no carga "
      f"al TB6612). En cada flanco del PWM se carga y descarga: C·V²·f = {_n(fm['p_mw_1khz'],1)} mW a 1 kHz "
      f"({fm['p_mw_20khz']:.0f} mW si el PWM fuera de 20 kHz): por eso el PWM se deja en 1 kHz.\n")
    pw = pwm_motor_tt()
    w("**PWM de los motores TT (de 3-6 V) con la batería 2S.** El voltaje medio en el motor es D·V_batería, así que el "
      "PWM máximo para no pasar de 6 V depende de la carga de la batería:\n")
    w("| Batería | PWM máximo para 6 V medios |")
    w("|---|---|")
    for vb, dd in pw.items():
        w(f"| {_n(vb,1)} V | {dd*100:.0f} % |")
    w("\nCon el límite fijo de ~70 % el motor nunca pasa de 5,9 V (batería llena) y, trabado, pide "
      f"{_n(0.7*8.4/(TT_R+TB6612_R))} A: dentro de los 1,2 A continuos del TB6612.\n")

    w("## 8. Conclusiones (honestas)\n")
    for texto in conclusiones(R, filas):
        w(f"- {texto}")
    w("")
    w("## 9. Qué medir en el montaje para reemplazar lo provisional\n")
    w("- Corriente de cada servo moviéndose y trabado (multímetro en serie en el V+ del canal, o pinza DC).")
    w("- Rs de los A4988 (mirar la serigrafía) y su Vref ya ajustado.")
    w("- Consumo real del panel de luz y del anillo (el dato más incierto de la tabla).")
    w("- Qué regulador trae la placa GVS del carro (lineal o conmutado) y su temperatura tras 10 min.")
    w("- Corriente de la batería con el carro andando (pinza o multímetro en serie en el fusible).")
    w("- Voltaje que le llega a cada webcam (5 V en el conector del hub y en la cámara).")
    return "\n".join(L) + "\n"


def conclusiones(R: dict, filas: list[dict]) -> list[str]:
    ri, fu, rg, au = R["rieles"], R["fusibles"], R["reguladores"], R["autonomia"]
    c = []
    ok_rieles = [RIELES[k].nombre for k, d in ri.items() if d["pico"] <= d["limite"]]
    mal = [RIELES[k].nombre for k, d in ri.items() if d["pico"] > d["limite"]]
    c.append(f"En el ciclo simulado **{len(ok_rieles)} de {len(ri)} rieles** quedan bajo su límite en el pico"
             + (f"; NO alcanzan: {', '.join(mal)}." if mal else "."))
    # Peor caso de 12 V: los 6 servos trabados (F1) + el pico de las otras tres ramas.
    peor12 = 7.8 * 6 / (ETA_XL4016 * 12) + IQ_BUCK + fu["F2"]["pico"] + fu["F3"]["pico"] + fu["F4"]["pico"]
    c.append(f"La fuente de 12 V 10 A está sobrada en el ciclo normal ({ri['12V']['uso_pico']*100:.0f} % en el pico): "
             f"se eligió por el peor caso (6 servos trabados + lo demás ≈ {_n(peor12,1)} A). Una de 5 A alcanzaría "
             "para el ciclo normal pero no para ese peor caso.")
    c.append(f"El riel de 6 V llega a {_ma(ri['6V']['pico'])} por la prensa apretando la tapa. Sin la regla "
             "prensa/empujador, los 6 servos trabados a la vez pedirían 7,8 A: justo bajo los 8 A del XL4016 y 4,4 A en F1 "
             "(5 A): queda **justo**. Por eso la regla vive en la placa (2026-09-28): `firmware/fijo/estacion.py` "
             "(`EXCLUYENTES`) no deja mover prensa y empujador a la vez aunque el PC los pida juntos: el segundo "
             "espera a que el primero vuelva a reposo.")
    fw0 = cargar_parametros()["firmware"]
    c.append("Los NEMA17 consumen casi lo mismo quietos que andando (~0,2 A cada uno de 12 V): el A4988 mantiene la "
             "corriente plena mientras ENABLE esté activo (no tiene corriente de reposo reducida propia). El firmware "
             f"suelta ENABLE (G13 en 1) cuando las dos cintas llevan {fw0['a4988_reposo_ms']} ms quietas: más que las "
             "pausas normales, así que con la línea andando nunca se sueltan (este ciclo no cambia); ahorra en las "
             "esperas largas. La cinta indexada no tiene carga que la arrastre y la cámara re-sincroniza igual.")
    lm = rg["LM2596 (5 V)"]
    c.append(f"El LM2596 disipa {_n(lm['disipa_W'][1])} W en el pico con el panel y el anillo prendidos: tibio-caliente "
             "sin disipador; queda en el flujo del ventilador de la caja, que es donde debe ir.")
    ams = rg["AMS1117-3.3 (ESP32 fijo)"]
    c.append(f"El regulador del ESP32 fijo carga con toda la lógica de 3,3 V ({_ma(ri['3V3F']['pico'])} de pico, "
             f"{_n(ams['disipa_W'][0])} W de calor): bien, pero no conviene colgarle más sensores de 3,3 V.")
    l5 = rg["5 V lineal del carro (8,4 V, batería llena)"]
    c.append(f"**Carro, regulador de 5 V: queda justo.** `sim/conexiones.py` lleva la batería al jack de la placa GVS "
             f"(regulador lineal), mientras `docs/revision-final.md` §4 habla de un buck de 5 V. Con el lineal y la batería "
             f"llena disipa {_n(l5['disipa_W'][0])} W promedio y {_n(l5['disipa_W'][1])} W en los picos de la radio: "
             "cerca del límite de un SOT-223. Recomendado: el mini-buck (MP1584 o similar) que dice la revisión, "
             "o comprobar la temperatura en el montaje.")
    c.append(f"**Límite de PWM de los motores TT:** `firmware/carro/hw.py` recorta el PWM a "
             f"{_n(fw0['carro_pwm_max'], 2)} (`firmware.carro_pwm_max`) también después de la corrección integral (antes "
             "podía llegar a 1,0: trabado, 1,53 A por motor, más que los 1,2 A continuos del TB6612). Con el tope quedan "
             f"1,07 A por motor. En el recorrido normal el control pide {au['duty_max']*100:.0f} % con 7,4 V: con la "
             "batería a medio cargar el carro va apenas más lento que `velocidad_linea_m_s`.")
    c.append(f"**Bus I2C largo:** `firmware/fijo/hw.py` crea el `SoftI2C` del bus largo (I2C 1) a "
             f"{fw0['i2c_bus_largo_hz'] // 1000} kHz (`firmware.i2c_bus_largo_hz`), como dice la revisión final. Con "
             f"2,2 kΩ y 170 pF la subida es de {pullup_i2c()['tr_ns']:.0f} ns: cumple a 100 kHz (1000 ns); a 400 kHz "
             "(300 ns) no cumpliría.")
    fw = cargar_parametros()["firmware"]
    un_tubo = fw["carrusel_pasos_por_vuelta"] / 6 * fw["carrusel_ms_por_paso"] / 1000
    c.append(f"**Tiempo del carrusel:** el firmware da un medio paso cada {fw['carrusel_ms_por_paso']} ms con un Timer "
             f"(500 Hz, bajo los 600 Hz de arranque de la hoja de datos) → un tubo (60°) tarda {_n(un_tubo)} s y media "
             f"vuelta {_n(3 * un_tubo)} s; `tiempos_ms.carrusel_giro` ya dice eso ({cargar_parametros()['tiempos_ms']['carrusel_giro']} ms). "
             "Eléctricamente no cambia nada (0,24 A). En `control/tiempos.py` los dos chequeos del carrusel quedan en "
             "NO CABE a propósito: la cinta de monedas espera al carrusel en esos ciclos (~2,5 s de más al girar al "
             "tubo opuesto y ~7 s una vez por lote).")
    peor_caida = max(caidas_por_carga(filas), key=lambda x: x["caida"])
    c.append(f"Caídas en los cables: la peor es {peor_caida['carga']} con {peor_caida['caida']*1000:.0f} mV en su pico; "
             "todas las cargas reciben más de su mínimo. Las webcams con su cable USB de 28 AWG quedan cerca de "
             "los 4,75 V del estándar: por eso van a un hub con fuente propia y no al portátil.")
    c.append(f"Carro: con 2 × 18650 de {CAPACIDAD_MAH} mAh hay {_n(au['h_recorriendo'],1)} h de marcha; la batería no "
             "es un problema para la sustentación.")
    c.append("Todo esto está calculado con corrientes de hoja de datos: son cotas razonables, no mediciones. Los números "
             "que más pueden moverse son el panel de luz, el anillo y la corriente real de los servos con su carga.")
    return c


def main() -> None:
    texto = generar_markdown()
    (DOCS / "electrica.md").write_text(texto, encoding="utf-8")
    R = resumen()
    print("docs/electrica.md escrito.")
    for rid, d in R["rieles"].items():
        print(f"  {RIELES[rid].nombre:28s} pico {d['pico']:.2f} A de {d['limite']:.2f} A (margen {d['margen']*100:.0f} %)")
    for nombre, d in R["fusibles"].items():
        print(f"  fusible {nombre:8s} pico {d['pico']:.2f} A de {d['amperios']:.0f} A")


if __name__ == "__main__":
    main()
