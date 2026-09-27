# Hardware del ESP32 del CARRO (solo MicroPython). Pines desde pines.py
# (generado de sim/conexiones.py).
#
# - Motores: TB6612 (puente H doble). El control pide VELOCIDAD de cada rueda
#   (m/s), no PWM: aqui se convierte con un adelanto (v / v_max) mas una
#   correccion con los encoders medida cada 200 ms (con 20 ranuras por vuelta
#   llegan pocos pulsos por ciclo; medir mas seguido seria puro ruido).
# - Encoders: interrupcion en cada ranura (el conteo no depende del bucle).
# - Ultrasonico HC-SR04: tambien por interrupciones (subida y bajada del ECHO),
#   para no bloquear con time_pulse_us: un disparo cada 60 ms.
# - Laser VL53L0X al frente, en el bus I2C principal (G21/G22).

import time
from machine import Pin, PWM, I2C

import pines
from distancia import Laser

try:
    from vehiculo import LecturaCarro
except ImportError:
    from control.vehiculo import LecturaCarro


class Motor:
    def __init__(self, pwm, in1, in2, cfg):
        self.pwm = PWM(Pin(pwm), freq=1000, duty=0)
        self.in1 = Pin(in1, Pin.OUT, value=0)
        self.in2 = Pin(in2, Pin.OUT, value=0)
        self.v_max = cfg["carro_v_max_m_s"]
        self.ki = cfg["carro_ganancia_ki"]
        self.integral = 0.0

    def mover(self, v, v_medida, pwm_bajo):
        if abs(v) < 1e-3:
            self.in1.value(0), self.in2.value(0), self.pwm.duty(0)
            self.integral = 0.0
            return
        self.integral += self.ki * (abs(v) - v_medida) * 0.02
        self.integral = max(-0.3, min(0.3, self.integral))
        u = abs(v) / self.v_max + self.integral
        # PWM bajo para entrar de reversa al muelle: con poco torque el motor
        # se ahoga contra el tope y el encoder deja de contar (asi sabe que llego).
        u = max(0.0, min(0.35 if pwm_bajo else 1.0, u))
        self.in1.value(1 if v > 0 else 0)
        self.in2.value(0 if v > 0 else 1)
        self.pwm.duty(int(u * 1023))


class Encoder:
    def __init__(self, pin):
        self.pulsos = 0
        self._pin = Pin(pin, Pin.IN)
        self._pin.irq(trigger=Pin.IRQ_RISING, handler=self._contar)

    def _contar(self, _):
        self.pulsos += 1


class Ultrasonico:
    def __init__(self, trig, echo, periodo_ms, alcance_mm, minimo_mm=20):
        self.trig = Pin(trig, Pin.OUT, value=0)
        self.echo = Pin(echo, Pin.IN)
        self.echo.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self._flanco)
        self.periodo = periodo_ms
        self.alcance = alcance_mm
        self.minimo = minimo_mm
        self._t_subida = 0
        self._prox = time.ticks_ms()
        self.ultima = None
        self.medidas = 0

    def _flanco(self, pin):
        if pin.value():
            self._t_subida = time.ticks_us()
        else:
            mm = time.ticks_diff(time.ticks_us(), self._t_subida) * 0.1715   # 343 m/s, ida y vuelta
            self.ultima = mm if self.minimo <= mm <= self.alcance else None
            self.medidas += 1

    def actualizar(self):
        if time.ticks_diff(time.ticks_ms(), self._prox) >= 0:
            self._prox = time.ticks_add(time.ticks_ms(), self.periodo)
            self.trig.value(1)
            time.sleep_us(10)
            self.trig.value(0)


class Hardware:
    def __init__(self, cfg):
        v = cfg["vehiculo"]
        self.cfg = cfg
        Pin(pines.TB6612_STBY, Pin.OUT, value=1)
        self.izq = Motor(pines.TB6612_PWMA, pines.TB6612_AIN1, pines.TB6612_AIN2, cfg)
        self.der = Motor(pines.TB6612_PWMB, pines.TB6612_BIN1, pines.TB6612_BIN2, cfg)
        self.enc = (Encoder(pines.ENC_IZQ_D0), Encoder(pines.ENC_DER_D0))
        self.linea = [Pin(p, Pin.IN) for p in (pines.IR_LINEA_OUT1, pines.IR_LINEA_OUT2, pines.IR_LINEA_OUT3,
                                                pines.IR_LINEA_OUT4, pines.IR_LINEA_OUT5)]
        self.cuna = Pin(pines.IR_CUNA_DO, Pin.IN)
        self.us = Ultrasonico(pines.HCSR04_TRIG, pines.HCSR04_ECHO, v["ultrasonico_periodo_ms"],
                              v["ultrasonico_rango_max_mm"], v["ultrasonico_rango_min_mm"])
        self.tof = Laser(I2C(0, sda=Pin(21), scl=Pin(22), freq=400_000), 0x29, None, v["tof_periodo_ms"],
                         v["tof_rango_max_mm"])
        self.m_por_pulso = 3.14159 * v["diametro_rueda_mm"] / 1000 / v["encoder_pulsos_por_vuelta"]
        self._ventana = [time.ticks_ms(), 0, 0]
        self.v_medida = [0.0, 0.0]
        ab = cfg["activo_bajo"]
        self._negro = 1 if ab.get("linea_negro_alto", True) else 0
        self._cuna_activa = 0 if ab.get("cuna", True) else 1

    def leer(self):
        self.us.actualizar()
        self.tof.actualizar()
        t = time.ticks_ms()
        dt = time.ticks_diff(t, self._ventana[0])
        if dt >= 200:                                # velocidad real de cada rueda
            for i in (0, 1):
                self.v_medida[i] = (self.enc[i].pulsos - self._ventana[1 + i]) * self.m_por_pulso * 1000 / dt
            self._ventana = [t, self.enc[0].pulsos, self.enc[1].pulsos]
        return LecturaCarro(tuple(1 if p.value() == self._negro else 0 for p in self.linea), self.us.ultima,
                            self.enc[0].pulsos, self.enc[1].pulsos, self.us.medidas, self.tof.ultima,
                            self.tof.medidas, self.cuna.value() == self._cuna_activa)

    def motores(self, v_izq, v_der, pwm_bajo):
        self.izq.mover(v_izq, self.v_medida[0], pwm_bajo)
        self.der.mover(v_der, self.v_medida[1], pwm_bajo)
