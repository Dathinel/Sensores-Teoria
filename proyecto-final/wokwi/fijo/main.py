# ESP32 FIJO en Wokwi (MicroPython). Version MINIMA del firmware real (firmware/fijo/):
# mueve y lee las mismas piezas por los MISMOS GPIO, para ver el circuito funcionando en el
# navegador sin tener el montaje. No lleva el protocolo con el PC ni la radio: eso esta en
# el firmware real. Lo que Wokwi no tiene se reemplaza (ver wokwi/README.md):
#   - PCA9685 (I2C 21/22) -> la prensa y el empujador van directo a un GPIO libre;
#   - VL53L0X (I2C 16/17 + XSHUT 18/19) -> potenciometros en ADC (cortina e interior);
#   - ULN2003 + 28BYJ-48 -> 4 LEDs que muestran la secuencia de medio paso de las bobinas;
#   - FC-51, capacitivo/inductivo (por PC817), Hall -> pulsadores con pull-up de 10 kOhm
#     (los pines 34-39 no tienen pull-up interno: en el montaje real el pull-up lo pone el
#     modulo o el optoacoplador). Pulsado = el sensor detecta (salida activa en bajo).

import time
from machine import Pin, PWM, ADC

# --- Mismos GPIO que firmware/fijo/hw.py (pines.py se genera de sim/conexiones.py) ---
M_STEP, M_DIR = 25, 26          # A4988 de la cinta de monedas
V_STEP, V_DIR = 27, 14          # A4988 de la cinta de vasos
DRIVERS_EN = 13                 # ENABLE comun, activo en bajo
ULN_IN = (32, 33, 23, 4)        # ULN2003 IN1-IN4 (carrusel)
PRESENCIA, CAPACITIVO, INDUCTIVO, HALL = 34, 35, 36, 39
# --- Solo en Wokwi (sustitutos; en el montaje real estos pines NO se usan) ---
SERVO_PRENSA, SERVO_EMPUJADOR = 5, 12     # en el real: canales 3 y 4 del PCA9685
POT_CORTINA, POT_INTERIOR = 2, 15         # en el real: VL53L0X por I2C

# Tiempos del ciclo (config/parametros.yaml, tiempos_ms).
AVANCE_MONEDAS, PAUSA_MONEDAS = 600, 1000
AVANCE_VASOS, PRENSA_CICLO, EMPUJADOR_CICLO = 1000, 1400, 700
CORTINA_UMBRAL_MM = 140   # el mismo del proyecto: sim/sensores_sim.ventana_cortina_mm()


class Cinta:
    """Como hw.Cinta: el PWM del ESP32 genera los pulsos de STEP (frecuencia = pasos por
    segundo) y se corta al pasar el tiempo. En Wokwi los pines MS1-MS3 quedan al aire =
    paso completo (200 por vuelta); en el montaje van a 1/4 (800 por vuelta)."""

    def __init__(self, step, direccion, pasos_por_casilla):
        self.step = PWM(Pin(step), freq=100, duty=0)
        Pin(direccion, Pin.OUT, value=1)
        self.pasos = pasos_por_casilla
        self.fin = None

    def avanzar(self, ms):
        self.step.freq(max(1, self.pasos * 1000 // ms))
        self.step.duty(512)                       # 50 %: un paso por periodo
        self.fin = time.ticks_add(time.ticks_ms(), ms)

    def actualizar(self):
        if self.fin is not None and time.ticks_diff(time.ticks_ms(), self.fin) >= 0:
            self.step.duty(0)
            self.fin = None

    def detener(self):
        self.step.duty(0)
        self.fin = None


def servo(pwm, grados):
    """0-180 grados -> pulso de 0,5-2,5 ms cada 20 ms (lo mismo que hace el PCA9685)."""
    us = 500 + grados * 2000 // 180
    pwm.duty_u16(us * 65535 // 20000)


def milimetros(adc, maximo):
    """Potenciometro 0-4095 -> distancia 0-maximo mm (reemplaza la lectura del VL53L0X)."""
    return adc.read() * maximo // 4095


def activo(pin):
    return pin.value() == 0                        # activo en bajo, como los modulos reales


Pin(DRIVERS_EN, Pin.OUT, value=0)                  # drivers habilitados
monedas = Cinta(M_STEP, M_DIR, 200)               # 40 mm = 1 vuelta del rodillo
vasos = Cinta(V_STEP, V_DIR, 400)                 # 80 mm = 2 vueltas
bobinas = [Pin(p, Pin.OUT, value=0) for p in ULN_IN]
MEDIO_PASO = ((1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
              (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1))
entradas = {"presencia": Pin(PRESENCIA, Pin.IN), "capacitivo": Pin(CAPACITIVO, Pin.IN),
            "inductivo": Pin(INDUCTIVO, Pin.IN), "hall": Pin(HALL, Pin.IN)}
prensa = PWM(Pin(SERVO_PRENSA), freq=50)
empujador = PWM(Pin(SERVO_EMPUJADOR), freq=50)
servo(prensa, 0)
servo(empujador, 0)
cortina = ADC(Pin(POT_CORTINA))
interior = ADC(Pin(POT_INTERIOR))
for a in (cortina, interior):
    a.atten(ADC.ATTN_11DB)                        # rango completo 0-3,3 V

ahora = time.ticks_ms()
prox_monedas = ahora
t_vasos, fase_vasos = ahora, "avance"
fase_carrusel, pasos_carrusel, prox_paso = 0, 0, ahora
ultimas = {}
prox_tel = ahora
print('{"t":"info","msg":"ESP32 fijo en Wokwi: cintas, carrusel, prensa y empujador"}')

while True:
    ahora = time.ticks_ms()
    monedas.actualizar()
    vasos.actualizar()
    mm_cortina = milimetros(cortina, 300)
    mano = mm_cortina < CORTINA_UMBRAL_MM

    # Cinta de monedas: avanza una casilla, pausa, y en la pausa el carrusel gira un tubo.
    if time.ticks_diff(ahora, prox_monedas) >= 0:
        monedas.avanzar(AVANCE_MONEDAS)
        prox_monedas = time.ticks_add(ahora, AVANCE_MONEDAS + PAUSA_MONEDAS)
        pasos_carrusel = 40                       # pocos pasos: solo para ver la secuencia en los LEDs

    # Carrusel: un medio paso cada 50 ms (en el real, 2 ms; aca mas lento para verlo).
    if pasos_carrusel and time.ticks_diff(ahora, prox_paso) >= 0:
        prox_paso = time.ticks_add(ahora, 50)
        fase_carrusel = (fase_carrusel + 1) % 8
        pasos_carrusel -= 1
        for b, v in zip(bobinas, MEDIO_PASO[fase_carrusel]):
            b.value(v)
        if activo(entradas["hall"]):
            print('{"t":"evt","src":"almacen","ev":"referencia","ok":true}')
    elif not pasos_carrusel:
        for b in bobinas:                         # quieto sin corriente: no calienta
            b.value(0)

    # Cinta de vasos: avance -> prensa (0->180->0) -> empujador. NUNCA prensa y empujador a
    # la vez: los dos MG996R trabados pedirian 5 A (ver docs/electrica.md).
    if mano:
        if fase_vasos != "cortina":
            vasos.detener()
            servo(prensa, 0)                      # la prensa SUBE y se queda arriba
            servo(empujador, 0)
            print('{"t":"evt","src":"seguridad","ev":"cortina","mm":%d}' % mm_cortina)
        fase_vasos = "cortina"
    elif fase_vasos == "cortina":
        fase_vasos, t_vasos = "avance", ahora
        print('{"t":"evt","src":"seguridad","ev":"despejada"}')
    dt = time.ticks_diff(ahora, t_vasos)
    if fase_vasos == "avance" and dt >= 0:
        vasos.avanzar(AVANCE_VASOS)
        fase_vasos, t_vasos = "prensa", time.ticks_add(ahora, AVANCE_VASOS)
    elif fase_vasos == "prensa" and dt >= 0:
        servo(prensa, 180)
        fase_vasos, t_vasos = "prensa_sube", time.ticks_add(ahora, PRENSA_CICLO // 2)
    elif fase_vasos == "prensa_sube" and dt >= 0:
        servo(prensa, 0)
        fase_vasos, t_vasos = "empujar", time.ticks_add(ahora, PRENSA_CICLO // 2)
    elif fase_vasos == "empujar" and dt >= 0:
        servo(empujador, 120)
        fase_vasos, t_vasos = "empujador_vuelve", time.ticks_add(ahora, EMPUJADOR_CICLO // 2)
    elif fase_vasos == "empujador_vuelve" and dt >= 0:
        servo(empujador, 0)
        fase_vasos, t_vasos = "avance", time.ticks_add(ahora, EMPUJADOR_CICLO // 2)

    # Sensores: solo se avisa cuando cambian (como estacion.py).
    for nombre, pin in entradas.items():
        v = activo(pin)
        if ultimas.get(nombre) != v:
            ultimas[nombre] = v
            print('{"t":"evt","src":"sensor","ev":"%s","valor":%s}' % (nombre, "true" if v else "false"))

    if time.ticks_diff(ahora, prox_tel) >= 0:
        prox_tel = time.ticks_add(ahora, 1000)
        print('{"t":"tel","vasos":"%s","cortina_mm":%d,"interior_mm":%d}'
              % (fase_vasos, mm_cortina, milimetros(interior, 150)))
    time.sleep_ms(10)
