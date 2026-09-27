# Hardware del ESP32 FIJO (solo MicroPython). Los numeros de pin salen de
# `pines.py`, que firmware/preparar.py genera desde sim/conexiones.py (la
# misma fuente que dibuja los cables en el visor 3D): nunca se escriben aca.
#
# Motores paso a paso (A4988): los pasos los genera el PWM del ESP32 en el pin
# STEP (frecuencia = pasos por segundo) y se corta cuando pasa el tiempo
# justo. Un bucle de Python no alcanza a dar un paso cada ~0,2 ms con
# precision; el PWM es hardware y si. Puede sobrar o faltar algun paso: por
# eso la camara de cada cinta mide donde quedaron los separadores y corrige
# (desfase_corregido, ya decidido en el diseno).

import time
from machine import Pin, PWM, I2C, SoftI2C

import pines
from distancia import Laser, apagar_todos

_SECUENCIA_28BYJ = ((1, 0, 0, 0), (1, 1, 0, 0), (0, 1, 0, 0), (0, 1, 1, 0),
                    (0, 0, 1, 0), (0, 0, 1, 1), (0, 0, 0, 1), (1, 0, 0, 1))   # medio paso


class PCA9685:
    """Controlador de 16 servos por I2C (ahorra pines y da pulsos estables)."""

    def __init__(self, i2c, direccion=0x40, hz=50):
        self.i2c, self.dir = i2c, direccion
        self.i2c.writeto_mem(self.dir, 0x00, b"\x10")                 # dormir para cambiar la frecuencia
        pre = round(25_000_000 / (4096 * hz)) - 1
        self.i2c.writeto_mem(self.dir, 0xFE, bytes([pre]))
        self.i2c.writeto_mem(self.dir, 0x00, b"\x20")                 # despertar, auto-incremento
        time.sleep_ms(5)
        self.hz = hz

    def pulso_us(self, canal, us):
        cuenta = int(us * self.hz * 4096 / 1_000_000)
        self.i2c.writeto_mem(self.dir, 0x06 + 4 * canal, bytes([0, 0, cuenta & 0xFF, cuenta >> 8]))


class Cinta:
    def __init__(self, pin_step, pin_dir, cfg):
        self.step = PWM(Pin(pin_step), freq=1000, duty=0)
        self.dir = Pin(pin_dir, Pin.OUT, value=1)
        self.pasos_por_mm = 200 * cfg["micropasos"] / cfg["mm_por_vuelta"]
        self.fin = None

    def avanzar(self, mm, ms):
        pasos = mm * self.pasos_por_mm
        self.step.freq(max(1, int(pasos * 1000 / ms)))
        self.step.duty(512)                          # 50 %: un paso por periodo
        self.fin = time.ticks_add(time.ticks_ms(), ms)

    def detener(self):
        self.step.duty(0)
        self.fin = None

    def actualizar(self):
        if self.fin is not None and time.ticks_diff(time.ticks_ms(), self.fin) >= 0:
            self.detener()

    def moviendose(self):
        return self.fin is not None


class Carrusel:
    """28BYJ-48 + ULN2003: un medio paso cada `ms_por_paso`, desde el bucle."""

    def __init__(self, cfg, hall):
        self.bobinas = [Pin(p, Pin.OUT, value=0) for p in (pines.ULN2003_IN1, pines.ULN2003_IN2,
                                                            pines.ULN2003_IN3, pines.ULN2003_IN4)]
        self.por_vuelta = cfg["carrusel_pasos_por_vuelta"]
        self.ms_por_paso = cfg["carrusel_ms_por_paso"]
        self.hall = hall
        self.posicion = 0                            # en medios pasos desde la referencia
        self.objetivo = 0
        self.buscando = False
        self.fase = 0
        self._prox = time.ticks_ms()

    def a_tubo(self, tubo):
        # Camino mas corto (el carrusel puede girar para los dos lados).
        destino = tubo * self.por_vuelta // 6
        d = (destino - self.posicion) % self.por_vuelta
        self.objetivo = self.posicion + (d if d <= self.por_vuelta // 2 else d - self.por_vuelta)

    def buscar_referencia(self):
        self.buscando = True
        self.objetivo = self.posicion + self.por_vuelta   # una vuelta como mucho

    def actualizar(self, hall_activo):
        if time.ticks_diff(time.ticks_ms(), self._prox) < 0:
            return
        self._prox = time.ticks_add(time.ticks_ms(), self.ms_por_paso)
        if self.buscando and hall_activo:
            self.buscando = False
            self.posicion = self.objetivo = 0
        if self.posicion == self.objetivo:
            for b in self.bobinas:                   # sin corriente quieto (no calienta)
                b.value(0)
            return
        sentido = 1 if self.objetivo > self.posicion else -1
        self.posicion += sentido
        self.fase = (self.fase + sentido) % 8
        for b, v in zip(self.bobinas, _SECUENCIA_28BYJ[self.fase]):
            b.value(v)


class Hardware:
    def __init__(self, cfg):
        self.cfg = cfg
        self.activo_bajo = cfg["activo_bajo"]
        self.en = Pin(pines.DRIVERS_EN, Pin.OUT, value=0)         # A4988: ENABLE activo en bajo
        mc = {"micropasos": cfg["micropasos"], "mm_por_vuelta": cfg["mm_por_vuelta_cinta"]}
        self.cintas = {"monedas": Cinta(pines.DRIVERS_M_STEP, pines.DRIVERS_M_DIR, mc),
                       "vasos": Cinta(pines.DRIVERS_V_STEP, pines.DRIVERS_V_DIR, mc)}
        self.entradas = {"presencia": Pin(pines.PRESENCIA_OUT, Pin.IN),
                         "capacitivo": Pin(pines.OPTO_OUT1, Pin.IN),
                         "inductivo": Pin(pines.OPTO_OUT2, Pin.IN),
                         "hall": Pin(pines.HALL_S, Pin.IN)}
        self.carrusel = Carrusel(cfg, self.entradas["hall"])
        # Bus 1 (G21/G22): PCA9685. Bus 2 (G16/G17, reparto I2C): los dos VL53L0X.
        self.pca = PCA9685(I2C(0, sda=Pin(21), scl=Pin(22), freq=400_000))
        bus2 = SoftI2C(sda=Pin(pines.HUB_I2C_SDA), scl=Pin(pines.HUB_I2C_SCL), freq=400_000)
        xshut = [Pin(pines.VL53_INTERIOR_XSHUT, Pin.OUT), Pin(pines.VL53_CORTINA_XSHUT, Pin.OUT)]
        apagar_todos(xshut)
        self.interior = Laser(bus2, 0x30, xshut[0])
        self.cortina = Laser(bus2, 0x31, xshut[1])

    def _digital(self, nombre):
        v = self.entradas[nombre].value()
        return (v == 0) if self.activo_bajo.get(nombre, True) else (v == 1)

    # --- lo que usa estacion.py ---
    def leer(self):
        self.cortina.actualizar()
        self.interior.actualizar()
        hall = self._digital("hall")
        self.carrusel.actualizar(hall)
        for c in self.cintas.values():
            c.actualizar()
        return {"presencia": self._digital("presencia"), "capacitivo": self._digital("capacitivo"),
                "inductivo": self._digital("inductivo"), "hall": hall,
                "cortina_mm": self.cortina.ultima, "interior_mm": self.interior.ultima,
                "carrusel": self.carrusel.posicion}

    def avanzar_cinta(self, nombre, mm, ms):
        self.cintas[nombre].avanzar(mm, ms)

    def cinta_moviendose(self, nombre):
        return self.cintas[nombre].moviendose()

    def detener_cinta(self, nombre):
        self.cintas[nombre].detener()

    def detener_cintas(self):
        for c in self.cintas.values():
            c.detener()

    def servo(self, nombre, angulo):
        # 0-180 grados -> 500-2500 us (SG90, MG90S y MG996R aceptan ese rango).
        self.pca.pulso_us(self.cfg["servos"][nombre]["canal"], 500 + angulo * 2000 // 180)

    def carrusel_a(self, tubo):
        self.carrusel.a_tubo(tubo)

    def carrusel_buscar_referencia(self):
        self.carrusel.buscar_referencia()
