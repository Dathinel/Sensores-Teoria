# ESP32 del CARRO en Wokwi (MicroPython). Version MINIMA del firmware real
# (firmware/carro/): sigue la linea con los 5 infrarrojos y se detiene ante un obstaculo,
# por los MISMOS GPIO. No lleva la evasion, la odometria ni la radio (eso esta en
# control/vehiculo.py, que corre tal cual en la placa). Sustitutos (ver wokwi/README.md):
#   - TB6612 y motores TT -> 7 LEDs: el brillo de PWMA/PWMB es la velocidad de cada rueda,
#     AIN1/AIN2 y BIN1/BIN2 el sentido, STBY encendido = puente H habilitado;
#   - 5 infrarrojos de linea -> interruptor DIP de 8 (se usan 5): ABIERTO = negro (1);
#   - encoders H206 y la cuna -> pulsadores (cada pulsacion = una ranura / vaso en la cuna);
#   - VL53L0X frontal (I2C 21/22) -> potenciometro en el GPIO 2 (0-1200 mm).
# El HC-SR04 SI existe en Wokwi (se le cambia la distancia haciendo clic en el).

import time
from machine import Pin, PWM, ADC, time_pulse_us

# --- Mismos GPIO que firmware/carro/hw.py ---
PWMA, AIN1, AIN2 = 25, 26, 27
PWMB, BIN1, BIN2 = 33, 32, 13
STBY = 4
ENC_IZQ, ENC_DER = 18, 19
IR_LINEA = (34, 35, 36, 39, 16)
TRIG, ECHO = 17, 23             # en el montaje, ECHO pasa por el divisor 1 k / 2 k (5 V -> 3,33 V)
CUNA = 14
# --- Solo en Wokwi ---
POT_LASER = 2

PWM_MAX = 0.70        # motores TT de 6 V con bateria 2S de 8,4 V: 0,70 * 8,4 = 5,9 V (docs/electrica.md)
PWM_BASE = 0.55
GANANCIA = 0.08
OBSTACULO_MM = 200

pwm_a = PWM(Pin(PWMA), freq=1000, duty=0)
pwm_b = PWM(Pin(PWMB), freq=1000, duty=0)
dir_pins = [Pin(p, Pin.OUT, value=0) for p in (AIN1, AIN2, BIN1, BIN2)]
Pin(STBY, Pin.OUT, value=1)
linea = [Pin(p, Pin.IN, Pin.PULL_UP) if p == 16 else Pin(p, Pin.IN) for p in IR_LINEA]
cuna = Pin(CUNA, Pin.IN, Pin.PULL_UP)
trig = Pin(TRIG, Pin.OUT, value=0)
echo = Pin(ECHO, Pin.IN)
laser = ADC(Pin(POT_LASER))
laser.atten(ADC.ATTN_11DB)
pulsos = [0, 0]


def contar(i):
    def _h(_):
        pulsos[i] += 1
    return _h


for i, p in enumerate((ENC_IZQ, ENC_DER)):
    Pin(p, Pin.IN, Pin.PULL_UP).irq(trigger=Pin.IRQ_FALLING, handler=contar(i))


def motores(izq, der):
    """Velocidad de cada rueda en fraccion de PWM (0-1), SIEMPRE recortada a PWM_MAX."""
    for pwm, v, (p1, p2) in ((pwm_a, izq, dir_pins[0:2]), (pwm_b, der, dir_pins[2:4])):
        v = max(-PWM_MAX, min(PWM_MAX, v))
        p1.value(1 if v > 0 else 0)
        p2.value(1 if v < 0 else 0)
        pwm.duty(int(abs(v) * 1023))


def ultrasonico_mm():
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    t = time_pulse_us(echo, 1, 30000)              # hasta ~5 m
    return None if t < 0 else t * 0.1715           # 343 m/s, ida y vuelta


prox_tel = time.ticks_ms()
en_cuna = None
print('{"t":"info","msg":"carro en Wokwi: sigue la linea y frena ante obstaculos"}')
while True:
    bits = [p.value() for p in linea]              # 1 = negro (interruptor abierto)
    pesos = (-2, -1, 0, 1, 2)
    negros = sum(bits)
    us = ultrasonico_mm()
    tof = laser.read() * 1200 // 4095
    cerca = min(tof, us) if us is not None else tof   # el mas cercano de los dos sensores
    if cerca < OBSTACULO_MM:
        motores(0, 0)
        estado = "obstaculo"
    elif negros == 0:
        motores(0, 0)
        estado = "sin_linea"
    else:
        error = sum(w * b for w, b in zip(pesos, bits)) / negros      # -2 (izq) .. 2 (der)
        motores(PWM_BASE + GANANCIA * error * 2, PWM_BASE - GANANCIA * error * 2)
        estado = "siguiendo"
    c = cuna.value() == 0
    if c != en_cuna:
        en_cuna = c
        print('{"t":"evt","src":"carro","ev":"cuna","cuna":%s}' % ("true" if c else "false"))
    if time.ticks_diff(time.ticks_ms(), prox_tel) >= 0:
        prox_tel = time.ticks_add(time.ticks_ms(), 500)
        print('{"t":"tel","estado":"%s","linea":"%s","us_mm":%s,"laser_mm":%d,"enc":[%d,%d]}'
              % (estado, "".join(str(b) for b in bits), "null" if us is None else int(us), tof, pulsos[0], pulsos[1]))
    time.sleep_ms(20)                              # 50 Hz, como control_hz
