"""Parte electrica SIMULADA, punto por punto (pedido 10-c del usuario, 2026-09-28).

Que hace este modulo (Python puro: numpy; el informe, si esta, matplotlib; NO usa PyBullet):

1. Modela cada RIEL de alimentacion (12 V de la fuente, 6 V de los servos, 5 V de
   la caja, 3,3 V del ESP32 fijo, 5 V del USB, bateria 2S del carro y su 5 V) y cada
   CARGA con su corriente de reposo, nominal y pico (valores de hoja de datos,
   marcados como tales: todavia no se midieron en el montaje).
2. Recorre en el tiempo, con paso de 10 ms, un ciclo REAL de la planta (las dos
   cintas con los tiempos de `config/parametros.yaml`, los servos en el orden de la
   seccion 5 de docs/especificacion.md, prensa y empujador nunca a la vez) y un recorrido del
   carro (arranque, rectas, curvas, evasion de los 3 muros, meta, vuelta, muelle).
   Resultado: corriente de cada riel contra el tiempo, pico, promedio, margen del
   fusible principal y de cada regulador, disipacion (y el calor dentro de la caja, que
   decide el ventilador), consumo desde la red y autonomia.
3. Asigna a CADA hilo de `sim/conexiones.py` (la fuente unica del conexionado) su
   voltaje, su corriente nominal y pico, su calibre (AWG), su largo, su caida de
   tension y la proteccion que lo cubre.
4. Calcula los pasivos (Vref del A4988, divisor del ECHO, pull-ups, entrada NPN con
   diodo, condensadores, PWM de los motores TT) con la formula a la vista.
5. El informe va aparte, en `sim/electrica_informe.py`: `generar_markdown()` arma
   `docs/electrica.md`; `python -m sim.electrica` lo escribe junto con las graficas
   `docs/capturas/electrica-ciclo-*.png`.

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

import numpy as np

from control.configuracion import cargar_parametros
from sim import conexiones as cx

DT = 0.010   # paso de la simulacion en el tiempo: 10 ms (el tiempo de reaccion de un fusible es >> 10 ms)


def _n(x, d=2):
    """Numero con coma decimal (como el resto de la documentacion)."""
    return f"{x:.{d}f}".replace(".", ",")


# ===========================================================================
# 1. Cables: resistencia por calibre y largo de cada tramo
# ===========================================================================

# Resistencia de UN hilo de cobre a 20 °C, en ohm por metro (tabla AWG estandar).
# La caida de un circuito es ida + vuelta: por eso en la tabla de cargas se suma
# la del hilo positivo y la del GND.
OHM_POR_M = {18: 0.021, 20: 0.033, 22: 0.053, 24: 0.084, 26: 0.134, 28: 0.213}

# Largos de los USB al portatil (sin hub, 2026-10-24): recorrido del visor (boton Cables: 1,48 / 1,74 /
# 0,73 m) + 20 % de holgura. La webcam de vasos necesita su extension USB de 1 m (su cable trae ~1,5 m).
LARGO_USB_CENITAL, LARGO_USB_VASOS, LARGO_USB_ESP = 1.78, 2.09, 0.88

# Largo de los cables de CAMPO medido en el modelo 3D con 20 % de holgura
# (docs/revision-final.md §4, tabla "Largos de cable"). Es un texto en un .md, no un
# dato de Python: se copia aqui con la cita, en metros, por id de cable de conexiones.py.
LARGOS_CAMPO_M = {
    "motor_monedas": 1.38, "motor_vasos": 0.76, "motor_carrusel": 0.94,
    "servo_0": 0.63, "servo_1": 1.19, "servo_2": 1.11, "servo_3": 0.59, "servo_4": 0.26, "servo_5": 0.70,
    "presencia": 1.18, "capacitivo": 1.18, "inductivo": 1.14, "hall": 0.88,
    "vl53_interior": 1.20, "vl53_cortina": 0.50, "panel_luz": 0.29, "anillo": 1.03,
    # USB (2026-10-24, sin hub): del conector de cada uno al puerto del portatil, medido en el visor.
    "usb_cenital": LARGO_USB_CENITAL, "usb_vasos": LARGO_USB_VASOS, "usb_esp": LARGO_USB_ESP, "red": 1.50,
}
# Dentro de la caja: 18,7 m de hilo en 47 hilos (revision-final §4) = 0,40 m de promedio
# por hilo de potencia; los Dupont de logica son jumpers de 20 cm. Carro: 6,0 m en 42
# hilos = ~0,15 m por hilo.
LARGO_INTERNO_M = 0.40
LARGO_DUPONT_M = 0.20
LARGO_CARRO_M = 0.15

# Calibre por tipo de cable (el `tipo` de cada cable de conexiones.py). Por que cada uno:
# - potencia interna 18 AWG: la bornera V+ del PCA9685 ya va en 18 AWG (conexiones.py), por
#   la salida del buck de 6 V pasan hasta ~4 A y el fusible principal es de 5 A: 18 AWG aguanta
#   ~7 A en haz sin calentarse;
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
    "12V": Riel("12V", "12 V de la fuente", 12.0, "Fuente conmutada 12 V 5 A de 60 W (110 V AC → 12 V DC)", 5.0,
                "5 A de la fuente (60 W)", "Drivers A4988 (VMOT), sensores capacitivo e inductivo y la entrada de los dos buck, "
                "todo detrás del fusible principal."),
    "6V": Riel("6V", "6 V de los servos", 6.0, "Buck XL4015 desde el +12 V", 5.0,
               "5 A del XL4015 (límite de corriente ajustado a ~4,5 A; ≈4 A continuos sin disipador extra)",
               "Solo los 6 servos, por la bornera V+ del PCA9685 (con 1000 µF)."),
    "5V": Riel("5V", "5 V de la caja", 5.0, "Buck LM2596 desde el +12 V", 3.0,
               "3 A del LM2596 (≈2 A continuos sin disipador)", "28BYJ-48 del carrusel por el ULN2003, panel de luz, anillo de la cámara, ventilador."),
    "3V3F": Riel("3V3F", "3,3 V del ESP32 fijo", 3.3, "Regulador lineal AMS1117-3.3 del DevKit, desde el USB", 0.6,
                 "≈0,6 A (1 A del AMS1117, limitado por temperatura: 1,7 V de caída)",
                 "El ESP32 y toda la lógica de 3,3 V: sensores de 3 hilos, VL53L0X, lógica del PCA9685 y de los A4988, pull-ups."),
    "USB": Riel("USB", "5 V del USB del ESP32 fijo", 5.0, "Puerto USB del portátil (sin hub desde 2026-10-24)", 0.5,
                "0,5 A de un puerto USB 2.0 (un USB 3 da 0,9 A)",
                "ESP32 fijo (datos y alimentación) y su lógica de 3,3 V. Cada webcam va a su propio puerto del portátil."),
    "BAT": Riel("BAT", "Batería 2S del carro", 7.4, "2 × 18650 2500 mAh con BMS 2S (6,0-8,4 V)", 3.0,
                "3 A del fusible del carro (el BMS 2S típico corta en 3-5 A)", "Motores TT por el TB6612 y el regulador de 5 V de la placa."),
    "5VC": Riel("5VC", "5 V del carro", 5.0, "Regulador de la placa GVS (lineal tipo AMS1117-5.0) desde la batería", 1.0,
                "1 A del AMS1117; por CALOR ≈0,3 A continuos con 8,4 V (disipa 3,4 V × I; ~1 W en SOT-223)",
                "ESP32 del carro (VIN) y el HC-SR04; del 3,3 V del ESP32 salen los demás sensores."),
}

# Panel de luz (auditoria 2026-10-25, maqueta_impresa/informes/esfuerzos.md): 2 tiras 2835 de 20 LED a ~20 mA son 0,40 A
# por tira a 5 V, 4 W las dos, y el marco de PLA de 1,6 mm de la caja de luz llegaria a ~65 °C (Tg del PLA
# 55-60 °C). Por eso el +5 V del panel pasa por UNA resistencia en serie, soldada en linea del lado de la caja
# (lejos del PLA), que deja las tiras en <= 1,5 W (~40 °C). Equivale a 6,8 Ω por tira (las dos en paralelo).
# No se usa un MOSFET con PWM del ESP32: el fijo no tiene GPIO libres fuera de los de arranque (0, 2, 5, 12,
# 15; test_sin_pines_de_arranque_ni_de_memoria) y el PCA9685 trabaja a 50 Hz (los servos), que la camara
# de vasos veria como parpadeo y franjas en el contraluz.
# Modelo de cada tira: la rodilla de los LED blancos (PANEL_V_RODILLA) mas la resistencia que trae cada LED
# (las 20 en paralelo), ajustada para que a 5 V pida PANEL_I_TIRA_5V. PROVISIONAL: medir la corriente real.
PANEL_TIRAS = 2
PANEL_I_TIRA_5V = 0.40     # A por tira a 5 V, sin resistencia (20 LED x ~20 mA)
PANEL_V_RODILLA = 2.8      # V: rodilla de un LED blanco 2835 a pocos mA (2,6-3,0 segun el lote)
PANEL_R_SERIE = 3.3        # Ω, 1 W, en linea en el +5 V del panel
PANEL_P_MAX_W = 1.5        # potencia maxima en las tiras (esfuerzos.md: <= 40 °C en el marco de PLA)


def panel_luz(r_serie: float = PANEL_R_SERIE, v_rodilla: float = PANEL_V_RODILLA) -> dict:
    """Corriente del panel, voltaje y potencia en las tiras y en la resistencia en serie."""
    r_tiras = (5.0 - v_rodilla) / PANEL_I_TIRA_5V / PANEL_TIRAS          # las dos tiras en paralelo
    i = (5.0 - v_rodilla) / (r_tiras + r_serie)
    v = 5.0 - i * r_serie
    return {"i": i, "v_tiras": v, "p_tiras": v * i, "p_resistencia": i * i * r_serie, "r_tiras": r_tiras}


_I_PANEL = round(panel_luz()["i"], 3)

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
    # --- 5 V de la caja ---
    "byj48": ("5V", 0.0, 0.15, 0.24, "28BYJ-48 5 V: 50 Ω/bobina → 0,1 A por bobina; medio paso = 1 o 2 bobinas; + LEDs del ULN2003"),
    "panel": ("5V", _I_PANEL, _I_PANEL, round(panel_luz(v_rodilla=2.6)["i"], 3),
              "Panel LED difuso ~33 × 11 cm: 2 tiras 2835 de 20 LED (0,80 A a 5 V) detrás de una resistencia de "
              "3,3 Ω en serie: ≤ 1,5 W en las tiras (PROVISIONAL)"),
    "anillo": ("5V", 0.35, 0.35, 0.40, "Anillo de luz difusa 5 V para webcam (PROVISIONAL)"),
    "ventilador": ("5V", 0.10, 0.10, 0.15, "Ventilador 4010 5 V: 0,1 A (conexiones.py)"),
    # --- 3,3 V del ESP32 fijo ---
    "esp32": ("3V3F", 0.100, 0.110, 0.240, "ESP32 con la radio encendida (ESP-NOW escuchando ~100 mA; transmitiendo ~240 mA)"),
    "vl53": ("3V3F", 0.019, 0.019, 0.040, "VL53L0X: 19 mA midiendo (promedio); pulsos del láser ~40 mA"),
    "fc51": ("3V3F", 0.012, 0.012, 0.015, "FC-51 a 3,3 V: LED IR ~10 mA + LM393 + LEDs del módulo"),
    "ky003": ("3V3F", 0.005, 0.005, 0.010, "KY-003: A3144 ~4,4 mA (máx 9 mA) + LED del módulo"),
    "pca_logica": ("3V3F", 0.006, 0.006, 0.010, "PCA9685: lógica ~6 mA (VCC)"),
    "a4988_logica": ("3V3F", 0.005, 0.005, 0.008, "A4988: VDD de lógica ≤ 8 mA cada uno"),
    "pullups": ("3V3F", 0.002, 0.003, 0.004, "Pull-ups: I2C 2,2 kΩ (1,5 mA con la línea en bajo), 10 kΩ del Hall y de las dos entradas NPN (0,33 mA)"),
    "uln_entradas": ("3V3F", 0.0, 0.0014, 0.0028, "Entradas del ULN2003 (2,7 kΩ internas): ~0,7 mA por entrada encendida"),
    # --- USB ---
    "cam_1080": ("USB", 0.25, 0.25, 0.35, "Webcam 1080p con autoenfoque en MJPEG: 0,25-0,35 A"),
    "cam_720": ("USB", 0.20, 0.20, 0.25, "Webcam 720p en MJPEG: ~0,2 A"),
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
        linea.tramo(t0 + dur, trabado_final_s, trab)             # apretando al final de la carrera (la prensa contra la tapa)
    return dur + trabado_final_s


def simular_planta(p: dict | None = None, duracion_s: float = 20.0) -> dict:
    """Ciclo real de la planta con las dos cintas corriendo a la vez.

    Cinta de monedas (cada `avance + pausa` = 1,6 s): avanza, el desvio se pone para
    una moneda aceptada (una de cada dos), y en la pausa el carrusel gira un tubo (60°).
    Cinta de vasos (avance 1 s): tapa; prensa 0→180→0 con la leva apretando la tapa
    (0,5 mm de apriete al final de la carrera, sin resorte limitador); DESPUES el empujador
    (nunca a la vez que la prensa: regla de diseño), asi que su ciclo dura avance + prensa + empujador = 3,3 s. Cada servo gira su
    recorrido de firmware.servos (activo - reposo), que es el de su pieza impresa. En la ventana
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
    # Grados de cada servo = recorrido de su pieza impresa (firmware.servos: activo - reposo).
    ang = {s: abs(v["activo"] - v["reposo"]) for s, v in fw["servos"].items()}
    # El carrusel lo mueve el FIRMWARE a un medio paso cada `carrusel_ms_por_paso`, con una rampa que
    # suma lo mismo a cada giro (carrusel_giro - media vuelta a velocidad de crucero = 127 ms): un tubo
    # (60°) son 4096/6 = 683 medios pasos → 1,37 s + 0,13 = 1,49 s; media vuelta 4,22 s.
    s_por_grado = fw["carrusel_pasos_por_vuelta"] / 360 * fw["carrusel_ms_por_paso"] / 1000
    rampa_carrusel = t["carrusel_giro"] / 1000 - 180 * s_por_grado
    k = 0
    while k * tm < duracion_s:
        t0 = k * tm
        L["nema_m"].tramo(t0, 0.06, corriente_nema_12v("monedas", True, p, arrancando=True), "set")
        L["nema_m"].tramo(t0 + 0.06, av_m - 0.06, corriente_nema_12v("monedas", True, p), "set")
        if k % 2 == 0:                                   # moneda aceptada: desvio al almacen y vuelta
            d = mover_servo(L["servo_desvio"], "SG90", t0, ang["desvio"])
            mover_servo(L["servo_desvio"], "SG90", t0 + av_m + 0.3, ang["desvio"])
        if not (6.0 <= t0 < 12.0):                        # (entre 6 y 12 s el carrusel suelta un lote)
            L["carrusel"].tramo(t0 + av_m, 60 * s_por_grado + rampa_carrusel, CARGAS["byj48"][2])
        k += 1

    # --- lote: el carrusel lleva el tubo lleno al agujero (hasta 180°) y abre el obturador ---
    t_lote = 6.2
    giro = 180 * s_por_grado
    L["carrusel"].tramo(t_lote, giro, CARGAS["byj48"][2])
    ob = t_lote + giro
    mover_servo(L["servo_obturador"], "SG90", ob, ang["obturador"])
    mover_servo(L["servo_obturador"], "SG90", ob + t["compuerta_tubo"] / 2000, ang["obturador"])

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
        mover_servo(L["servo_tapas"], "SG90", tp, ang["tapas"])
        mover_servo(L["servo_tapas"], "SG90", tp + t["tapa_caida"] / 2000, ang["tapas"])
        # Prensa: baja con la leva (mas lenta con carga), aprieta 0,2 s la tapa (0,5 mm de
        # apriete contra la rigidez de la estructura, sin resorte limitador; servo casi trabado:
        # es el pico de diseño) y sube sin carga.
        mover_servo(L["servo_prensa"], "MG996R", tp, ang["prensa"], factor_vel=1.6, trabado_final_s=0.2)
        mover_servo(L["servo_prensa"], "MG996R", tp + prensa / 2, ang["prensa"], extra_a=-0.3)
        te = tp + prensa                                   # el empujador espera a que la prensa termine
        mover_servo(L["servo_empujador"], "MG996R", te, ang["empujador"], extra_a=0.3, factor_vel=1.3)   # empuja el vaso
        mover_servo(L["servo_empujador"], "MG996R", te + emp / 2, ang["empujador"], extra_a=-0.3)
        j += 1

    # --- canaleta: suelta un vaso al carro ---
    mover_servo(L["servo_canaleta"], "SG90", 12.5, ang["canaleta"])
    mover_servo(L["servo_canaleta"], "SG90", 12.5 + t["empujador"] / 2000, ang["canaleta"])

    # --- ESP32 fijo: latido de la radio cada 250 ms (transmite ~5 ms) ---
    periodo = p["protocolo"]["carro_latido_ms"] / 1000
    for tx in np.arange(0, duracion_s, periodo):
        L["esp32"].tramo(tx, DT, CARGAS["esp32"][3])

    return _rieles_planta(tiempo, {k: v.i for k, v in L.items()}, p)


# Eficiencias (hoja de datos, en el punto de trabajo de este montaje):
ETA_XL4015 = 0.88       # 12 → 6 V a 1-4 A (hoja del XL4015: 88-92 % en ese rango; se toma el bajo)
ETA_LM2596 = 0.82       # 12 → 5 V a ~1,5 A (el LM2596 rinde menos que el XL4015)
IQ_BUCK = 0.008         # A que cada buck consume en vacio desde 12 V
ETA_FUENTE = 0.82       # fuente generica de 60 W al ~40-60 % de su carga (las de 12 V 5 A rinden 80-85 %)
P_VACIO_FUENTE = 1.0    # W de la fuente sin carga (generica: ~0,5-1 W; PROVISIONAL)
V_RED = 110.0
FACTOR_POTENCIA = 0.55  # una fuente de 60 W no tiene PFC: factor de potencia ~0,5-0,6


def _rieles_planta(tiempo, I: dict, p: dict) -> dict:
    servos = sum(I["servo_" + s] for s in SERVO_MODELO)
    cinco = I["carrusel"] + I["panel"] + I["anillo"] + I["ventilador"]
    sens12 = 2 * CARGAS["sensor_m18"][2]                     # sin optoacopladores: solo los dos M18
    uln = np.where(I["carrusel"] > 0, CARGAS["uln_entradas"][2], 0.0)
    tres3 = (I["esp32"] + 2 * CARGAS["vl53"][2] + CARGAS["fc51"][2] + CARGAS["ky003"][2] + CARGAS["pca_logica"][2]
             + 2 * CARGAS["a4988_logica"][2] + CARGAS["pullups"][2] + uln)
    usb_esp = tres3 + 0.005                                                   # lineal: entra lo que sale + reposo
    drivers = I["nema_m"] + I["nema_v"]
    # Ramas del +12 V (todas detras del fusible principal: ya no hay un fusible por rama).
    b6 = servos * 6.0 / (ETA_XL4015 * 12.0) + IQ_BUCK        # potencia que sale / rendimiento / 12 V
    b5 = cinco * 5.0 / (ETA_LM2596 * 12.0) + IQ_BUCK
    sens = np.full_like(tiempo, sens12)
    doce = b6 + b5 + drivers + sens
    p_red = doce * 12.0 / ETA_FUENTE + P_VACIO_FUENTE
    series = {"6V": servos, "5V": cinco, "3V3F": tres3, "USB": usb_esp, "USB_ESP": usb_esp, "12V": doce,
              "rama_buck6": b6, "rama_buck5": b5, "rama_drivers": drivers, "rama_sensores": sens,
              "red_W": p_red, "red_A": p_red / (V_RED * FACTOR_POTENCIA)}
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


# Ahorro 2026-10-24: UN fusible principal (lento) en el +12 V a la salida de la fuente, en vez de
# cuatro (uno por rama). Se dimensiona con esta simulacion: el pico del ciclo y el peor caso con el
# limite de corriente del XL4015 (`peor_caso_12v`) quedan bajo 5 A; un corto o un motor trabado
# de forma sostenida lo abren. La fuente de 5 A tiene ademas su propia proteccion de sobrecarga.
FUSIBLE_PRINCIPAL_A = 5.0
FUSIBLES = {  # nombre: (A, serie de la simulacion, que protege)
    "Fusible principal": (FUSIBLE_PRINCIPAL_A, "12V", "todo el +12 V: los dos buck, los drivers y los sensores M18"),
    "F carro": (3.0, "BAT", "todo el carro (después del interruptor)"),
}
LIMITE_CC_XL4015_A = 4.5   # A: el trimmer de corriente del XL4015 se deja aqui (bajo sus 5 A)


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
    reg["XL4015 (6 V)"] = {"sale_W": p6, "eta": ETA_XL4015, "disipa_W": tuple(x * (1 / ETA_XL4015 - 1) for x in p6)}
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
    calor = calor_caja(sp, reg)
    return {"rieles": rieles, "fusibles": fus, "reguladores": reg, "red_W": red_w, "red_A": red_a,
            "autonomia": autonomia, "planta": planta, "carro": carro, "peores": peores_casos(sp), "calor": calor,
            "peor_12v": peor_caso_12v(sp)}


def peor_caso_12v(sp: dict) -> float:
    """Lo maximo que puede pedir el +12 V (A): el buck de los servos en su limite de corriente
    (pase lo que pase en el riel de 6 V, el XL4015 no entrega mas que eso) + el pico de las otras
    ramas en el ciclo. Es lo que tiene que aguantar el fusible principal sin abrir."""
    b6 = LIMITE_CC_XL4015_A * 6.0 / (ETA_XL4015 * 12.0) + IQ_BUCK
    return b6 + float(np.max(sp["rama_buck5"])) + float(np.max(sp["rama_drivers"])) + float(np.max(sp["rama_sensores"]))


# --- Calor dentro de la caja: decide si hace falta el ventilador ------------------------------
# Caja de acrilico de 3 mm, 360 x 240 x 80 mm, cerrada con su tapa. Coeficiente global de
# transferencia (conveccion natural + radiacion por dentro y por fuera, el acrilico casi no suma):
# 1 / (1/8 + 0,003/0,19 + 1/10) ≈ 4 W/(m²·K). ESTIMADO (sin medir).
U_CAJA = 4.0
AREA_CAJA_M2 = 2 * (0.36 * 0.24 + 0.36 * 0.08 + 0.24 * 0.08)
P_A4988_W = I_TRIP ** 2 * A4988_RDS          # 0,75 W en los transistores de cada driver (siempre, con ENABLE)
# Pololu (hoja del A4988): "hasta ~1 A por fase sin disipador ni aire forzado", a temperatura de
# laboratorio (~25 °C). Este montaje usa justo 1 A por fase (I_TRIP).
I_A4988_SIN_AIRE = 1.0


def calor_caja(sp: dict, reg: dict) -> dict:
    """Calor que se queda dentro de la caja (W, promedio) y cuanto sube la temperatura del aire
    de adentro sin ventilador: ΔT = P / (U · A)."""
    p12_sale = float(np.mean(sp["12V"])) * 12.0
    partes = {
        "Fuente 12 V 5 A (pérdidas)": p12_sale * (1 / ETA_FUENTE - 1) + P_VACIO_FUENTE,
        "2 × A4988 (1 A por fase)": 2 * P_A4988_W,
        "XL4015 (6 V)": reg["XL4015 (6 V)"]["disipa_W"][0],
        "LM2596 (5 V)": reg["LM2596 (5 V)"]["disipa_W"][0],
        "AMS1117 del ESP32": reg["AMS1117-3.3 (ESP32 fijo)"]["disipa_W"][0],
    }
    total = sum(partes.values())
    dT = total / (U_CAJA * AREA_CAJA_M2)
    return {"partes": partes, "total_W": total, "dT_sin_ventilador": dT,
            "a4988_al_limite": I_TRIP >= I_A4988_SIN_AIRE, "ventilador": True}


def peores_casos(sp: dict | None = None) -> list[dict]:
    """Casos que la simulacion normal no recorre, calculados a mano (condiciones limite)."""
    sg, mg = CARGAS["SG90"][3], CARGAS["MG996R"][3]
    todos = 2 * mg + 4 * sg
    con_regla = mg + 4 * sg
    resto = 0.0 if sp is None else (float(np.max(sp["rama_buck5"])) + float(np.max(sp["rama_drivers"]))
                                    + float(np.max(sp["rama_sensores"])))
    def f12(i6):
        # Lo que pide al +12 V: el XL4015 no entrega mas que su limite de corriente.
        return min(i6, LIMITE_CC_XL4015_A) * 6 / (ETA_XL4015 * 12) + IQ_BUCK + resto
    motor_100 = 8.4 / (TT_R + TB6612_R)
    motor_70 = 0.70 * 8.4 / (TT_R + TB6612_R)
    lim6 = RIELES["6V"].limite_a
    return [
        {"caso": "Los 6 servos trabados a la vez (sin la regla prensa/empujador)", "riel": "6 V",
         "i": todos, "limite": lim6,
         "fusible": f"principal: {_n(f12(todos))} A de {_n(FUSIBLE_PRINCIPAL_A, 0)} A (el XL4015 se queda en su límite de "
                    f"{_n(LIMITE_CC_XL4015_A, 1)} A y el riel de 6 V se hunde: los servos se frenan, nada se quema)"},
        {"caso": "Prensa trabada + los 4 SG90 trabados en los mismos 30 ms (respetando la regla)", "riel": "6 V",
         "i": con_regla, "limite": lim6,
         "fusible": f"principal: {_n(f12(con_regla))} A de {_n(FUSIBLE_PRINCIPAL_A, 0)} A (igual que arriba: el XL4015 "
                    f"lo corta en {_n(LIMITE_CC_XL4015_A, 1)} A unos ms)"},
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


# Entrada NPN sin optoacoplador (2026-10-24): GPIO con pull-up de 10 kΩ a 3,3 V y un diodo en serie
# hacia la salida del sensor (catodo al sensor). Al detectar, el NPN conduce y el pin queda en
# V_ce(sat) + V_f del diodo: tiene que ser < 0,825 V (VIL del ESP32). Con el sensor libre el diodo
# queda en inverso aunque el sensor traiga su resistencia a 12 V: al pin solo llega la fuga.
# V_f a ~0,3 mA (curva V_f-I_f de la hoja de cada diodo):
DIODOS_ENTRADA = {"BAT85": {"vf": 0.27, "fuga_ua": 2.0, "nota": "Schottky de señal: V_f ≤ 0,24 V a 0,1 mA y ≤ 0,32 V a 1 mA"},
                  "1N4148": {"vf": 0.55, "fuga_ua": 0.025, "nota": "de silicio: ~0,5 V a 0,1 mA y ~0,62 V a 1 mA"}}
DIODO_ENTRADA = "BAT85"
V_CE_NPN = 0.3      # V: salida NPN del M18 conduciendo ~0,3 mA (la hoja da ≤ 1,5 V a su corriente nominal de 200 mA)


def entrada_npn(diodo: str = DIODO_ENTRADA, r_pullup: float = 10000, v_ce: float = V_CE_NPN) -> dict:
    d = DIODOS_ENTRADA[diodo]
    i = (3.3 - v_ce - d["vf"]) / r_pullup
    v_bajo = v_ce + d["vf"]
    return {"diodo": diodo, "v_bajo": v_bajo, "margen_v": VIL_MAX - v_bajo, "lee_cero": v_bajo < VIL_MAX,
            "i_ma": i * 1000, "v_alto": 3.3 + d["fuga_ua"] * 1e-6 * r_pullup, "nota": d["nota"]}


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
    FP = f"fusible principal {_n(FUSIBLE_PRINCIPAL_A, 0)} A"
    if cid == "p_red":
        if "tierra" in fl:
            return {"v": 0.0, "nivel": "tierra de protección (PE)", "i": (0.0, 0.0), "prot": "—"}
        return {"v": 0.0 if "neutro" in fl else V_RED, "nivel": "110 V AC" if "fase" in fl else "neutro (≈0 V)",
                "i": _i(sp["red_A"]), "prot": "fusible interno de entrada de la fuente (y el de la multitoma, si trae)"}
    if cid == "p_12":
        if "+12" in f:
            return {"v": 12.0, "nivel": "+12 V DC", "i": _i(sp["12V"]), "prot": "límite de la fuente (5 A), antes del fusible"}
        serie = sp["rama_sensores"] if "egnd_s" in a else sp["12V"] - sp["rama_sensores"]
        return gnd_o(12.0, "+12 V DC", _i(serie), FP)
    if cid == "p_e12":
        return {"v": 12.0, "nivel": "+12 V DC", "i": _i(sp["rama_sensores"] if "e12s" in a else sp["12V"]), "prot": FP}
    if cid == "p_buck6":
        return gnd_o(12.0, "+12 V DC", _i(sp["rama_buck6"]), FP)
    if cid == "p_buck5":
        if "IN" in de or "IN" in a:
            return gnd_o(12.0, "+12 V DC", _i(sp["rama_buck5"]), FP)
        return gnd_o(5.0, "+5 V DC", _i(sp["5V"]), FP + " (del lado de 12 V)")
    if cid == "p_pca":
        return gnd_o(6.0, "+6 V DC", _i(sp["6V"]), f"límite de corriente del XL4015 ({_n(LIMITE_CC_XL4015_A, 1)} A) + " + FP)
    if cid == "p_drv":
        return gnd_o(12.0, "+12 V DC", _i(sp["rama_drivers"]), FP)
    if cid == "p_uln":
        return gnd_o(5.0, "+5 V DC", _i(sp["carrusel"]), FP + " (del lado de 12 V)")
    if cid == "p_vent":
        return gnd_o(5.0, "+5 V DC", _i(sp["ventilador"]), FP + " (del lado de 12 V)")
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
    if cid == "l_npn":
        e = entrada_npn()
        if "pull-up" in fl:
            return {"v": 3.3, "nivel": "+3,3 V por la pull-up de 10 kΩ", "i": mA(e["i_ma"], e["i_ma"]), "prot": "regulador del ESP32"}
        return {"v": 3.3, "nivel": f"0/3,3 V (activo en bajo: ~{_n(e['v_bajo'])} V al detectar)", "i": mA(0.01, e["i_ma"]),
                "prot": f"diodo {e['diodo']} (bloquea los 12 V del sensor)"}
    if cid == "l_i2c1":
        if "pull-up" in fl:
            return {"v": 3.3, "nivel": "+3,3 V por la pull-up de 2,2 kΩ", "i": mA(0.5, 1.5), "prot": "regulador del ESP32"}
        if "3,3" in f or "gnd" in fl:
            return gnd_o(3.3, "+3,3 V", mA(38, 80), "regulador del ESP32")
        return {"v": 3.3, "nivel": "I2C 0/3,3 V, 100 kHz (pull-ups 2,2 kΩ)", "i": mA(0.5, 1.5), "prot": "—"}
    if cid == "presencia":
        if "señal" in fl:
            return {"v": 3.3, "nivel": "0/3,3 V (activo en bajo)", "i": mA(0.01, 0.33), "prot": "—"}
        return gnd_o(3.3, "+3,3 V", mA(12, 15), "regulador del ESP32")
    if cid in ("capacitivo", "inductivo"):
        e = entrada_npn()
        if "npn" in fl:
            return {"v": 12.0, "nivel": f"salida NPN: hasta 12 V libre (el diodo {e['diodo']} la bloquea) / "
                                        f"~{_n(V_CE_NPN, 1)} V al detectar", "i": mA(0.01, e["i_ma"]),
                    "prot": f"diodo {e['diodo']} en línea"}
        if "+12" in f:
            return {"v": 12.0, "nivel": "+12 V DC", "i": mA(8, 15), "prot": FP}
        return {"v": 0.0, "nivel": "0 V", "i": mA(8, 15), "prot": FP}
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
                "i": (I_TRIP / math.sqrt(2), I_TRIP), "prot": FP + " (VMOT)"}
    if cid == "motor_carrusel":
        if "+5" in f:
            return {"v": 5.0, "nivel": "+5 V común de las bobinas", "i": (0.15, 0.24), "prot": FP}
        return {"v": 5.0, "nivel": "5 V / 0 V (el ULN2003 la lleva a GND)", "i": (0.05, 0.1), "prot": FP}
    if cid.startswith("servo_"):
        nombre = de.split(".")[0].replace("servo_", "")      # "servo_prensa.CABLE" -> "prensa"
        serie = sp["servo_" + nombre]
        if "pwm" in fl:
            return {"v": 3.3, "nivel": "PWM 50 Hz, 0,5-2,5 ms, 0/3,3 V (del PCA9685)", "i": mA(0.05, 0.1), "prot": "—"}
        return gnd_o(6.0, "+6 V DC", _i(serie), f"límite del XL4015 ({_n(LIMITE_CC_XL4015_A, 1)} A)")
    if cid in ("panel_luz", "anillo"):
        nivel = "+5 V DC"
        if cid == "panel_luz":
            nivel += f" (~{_n(panel_luz()['v_tiras'], 1)} V en las tiras, detrás de la resistencia de {_n(PANEL_R_SERIE, 1)} Ω)"
        return gnd_o(5.0, nivel, _i(sp["panel" if cid == "panel_luz" else "anillo"]), FP + " (del lado de 12 V)")
    if cid.startswith("usb_"):
        corr = {"usb_cenital": (0.25, 0.35), "usb_vasos": (0.20, 0.25), "usb_esp": _i(sp["USB_ESP"])}[cid]
        return {"v": 5.0, "nivel": "USB 2.0: VBUS 5 V + datos diferenciales", "i": corr,
                "prot": "limitador del puerto del portátil (0,5 A en USB 2.0)"}
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
                            ("panel_luz", 5.0, PANEL_V_RODILLA), ("anillo", 5.0, 4.5), ("capacitivo", 12.0, 10.0),
                            ("hall", 3.3, 3.0), ("vl53_interior", 3.3, 2.6), ("presencia", 3.3, 3.0)):
        hs = por_cable[cid]
        ida = max(h["caida"] for h in hs if h["v"] > 0 and "señal" not in h["funcion"] and "PWM" not in h["funcion"]
                  and h["funcion"] not in ("SCL", "SDA") and "NPN" not in h["funcion"] and "XSHUT" not in h["funcion"])
        vuelta = max(h["caida"] for h in hs if h["v"] == 0)
        extra = 0.0
        if cid.startswith("servo"):
            # + la bornera V+ del PCA9685 (18 AWG, ida y vuelta) con toda la corriente de 6 V.
            extra = sum(h["caida"] for h in por_cable["p_pca"])
        elif cid == "panel_luz":
            # + la resistencia en serie, a proposito (deja las tiras en <= 1,5 W): el minimo es que los LED prendan.
            extra = max(h["i_pico"] for h in hs) * PANEL_R_SERIE
        out.append({"carga": hs[0]["nombre"], "v_nom": v_nom, "caida": ida + vuelta + extra,
                    "v_carga": v_nom - ida - vuelta - extra, "minimo": tol})
    # Webcams: VBUS + GND del cable USB (28 AWG) de ida y vuelta. USB 2.0: el PUERTO da 4,75-5,25 V y
    # el aparato tiene que funcionar con 4,40 V en SU conector (la norma deja 350 mV para el cable).
    for cid, nombre in (("usb_cenital", "Webcam cenital"), ("usb_vasos", "Webcam de vasos")):
        f = por_cable[cid][0]
        out.append({"carga": nombre + " (cable USB)", "v_nom": 5.0, "caida": 2 * f["caida"],
                    "v_carga": 5.0 - 2 * f["caida"], "minimo": 4.40})
    return out


def main() -> None:
    """`python -m sim.electrica`: escribe docs/electrica.md y sus graficas (sim/electrica_informe.py)."""
    from sim import electrica_informe   # aqui y no arriba: el informe importa este modulo

    electrica_informe.main()


if __name__ == "__main__":
    main()
