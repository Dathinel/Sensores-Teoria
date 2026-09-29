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
from machine import Pin, PWM, I2C, SoftI2C, Timer

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
        self.pasos_por_mm = cfg["pasos_por_vuelta"] * cfg["micropasos"] / cfg["mm_por_vuelta"]
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
    """28BYJ-48 + ULN2003: un medio paso cada `ms_por_paso`, dado por un Timer.

    Antes el paso lo daba el bucle principal (`leer()` en cada vuelta), pero
    cada vuelta del bucle ya duerme 2 ms y ademas lee I2C, arma JSON y drena
    el USB: el paso real quedaba en 3-5 ms y el carrusel tardaba mas de lo
    que dice la configuracion. Con un Timer periodico el paso sale cada
    `ms_por_paso` exactos y `tiempos_ms.carrusel_giro` (2048 medios pasos x
    ms_por_paso = media vuelta) es el tiempo de verdad. La callback solo
    cambia 4 pines y dos enteros: corta, sin esperas."""

    def __init__(self, cfg, hall_activo):
        self.bobinas = [Pin(p, Pin.OUT, value=0) for p in (pines.ULN2003_IN1, pines.ULN2003_IN2,
                                                            pines.ULN2003_IN3, pines.ULN2003_IN4)]
        self.por_vuelta = cfg["carrusel_pasos_por_vuelta"]
        self.ms_por_paso = cfg["carrusel_ms_por_paso"]
        # El agujero de la placa esta `carrusel_agujero_grados` (210) antihorario
        # desde la carga (sim/mundo.py): en medios pasos, redondeado.
        self.agujero_pasos = (cfg.get("carrusel_agujero_grados", 210) * self.por_vuelta + 180) // 360
        self.hall_activo = hall_activo               # funcion: True si el Hall ve el iman
        self.posicion = 0                            # en medios pasos desde la referencia
        self.objetivo = 0
        self.buscando = False
        self.fase = 0
        self._timer = Timer(0)
        self._timer.init(period=self.ms_por_paso, mode=Timer.PERIODIC, callback=self._paso)

    def a_tubo(self, tubo, lugar="carga"):
        # El tubo k queda bajo la CARGA en k * por_vuelta / 6 (la posicion crece
        # en sentido horario visto desde arriba: asi el tubo siguiente llega a la
        # carga). Sobre el AGUJERO, que esta 210 grados antihorario desde la
        # carga, hacen falta esos pasos MENOS.
        destino = tubo * self.por_vuelta // 6
        if lugar == "agujero":
            destino -= self.agujero_pasos
        # Camino mas corto (el carrusel puede girar para los dos lados).
        d = (destino - self.posicion) % self.por_vuelta
        self.objetivo = self.posicion + (d if d <= self.por_vuelta // 2 else d - self.por_vuelta)

    def buscar_referencia(self):
        self.buscando = True
        self.objetivo = self.posicion + self.por_vuelta   # una vuelta como mucho

    def moviendose(self):
        return self.posicion != self.objetivo

    def detener(self):
        """Parada segura: el objetivo pasa a ser donde esta ahora y el Timer
        deja de dar pasos (y apaga las bobinas) en su proxima llamada. Si el
        Timer justo da un paso entre las dos lecturas, en la siguiente vuelve
        ese medio paso: inofensivo (0,09 grados)."""
        self.buscando = False
        self.objetivo = self.posicion

    def _paso(self, _timer):
        if self.buscando and self.hall_activo():
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
        # A4988: ENABLE activo en BAJO, un solo pin (G13) para los dos drivers.
        # Con ENABLE en 0 el A4988 mantiene la corriente plena en las bobinas
        # aunque el motor este quieto (~0,2 A de 12 V cada uno, casi lo mismo
        # que andando): el A4988 no tiene "corriente de reposo reducida" propia.
        # Lo que si se puede hacer, y se hace: soltar los drivers (ENABLE en 1)
        # cuando las dos cintas llevan `a4988_reposo_ms` quietas. Por que no
        # compromete la posicion:
        #   - la cinta indexada no tiene carga que la arrastre: banda tensa sobre
        #     la cama, fricción y el par de retencion sin corriente del NEMA17
        #     (detent) la sostienen; el empujador y la prensa empujan de lado y
        #     hacia abajo, no a lo largo de la banda;
        #   - el A4988 NO se reinicia al soltar ENABLE (eso lo hace RESET): guarda
        #     su micropaso y al volver a habilitar el rotor vuelve a esa posicion
        #     (como mucho medio paso = 0,9 grados = 0,17 mm de banda);
        #   - y aunque algo se corriera, la camara de cada cinta mide los
        #     separadores despues de cada avance y re-sincroniza (desfase_corregido).
        # El tiempo es mas largo que las pausas normales entre casillas: con la
        # linea andando nunca se sueltan; solo en las esperas largas (pausa,
        # parada segura, sin piezas), que es donde calientan sin hacer nada.
        self.en = Pin(pines.DRIVERS_EN, Pin.OUT, value=0)
        self.drivers_activos = True
        self.reposo_ms = cfg["a4988_reposo_ms"]
        self._quietas_desde = time.ticks_ms()
        mc = {"micropasos": cfg["micropasos"], "mm_por_vuelta": cfg["mm_por_vuelta_cinta"],
              "pasos_por_vuelta": cfg["pasos_por_vuelta_motor"]}
        self.cintas = {"monedas": Cinta(pines.DRIVERS_M_STEP, pines.DRIVERS_M_DIR, mc),
                       "vasos": Cinta(pines.DRIVERS_V_STEP, pines.DRIVERS_V_DIR, mc)}
        self.entradas = {"presencia": Pin(pines.PRESENCIA_OUT, Pin.IN),
                         "capacitivo": Pin(pines.OPTO_OUT1, Pin.IN),
                         "inductivo": Pin(pines.OPTO_OUT2, Pin.IN),
                         "hall": Pin(pines.HALL_S, Pin.IN)}
        self.carrusel = Carrusel(cfg, lambda: self._digital("hall"))
        # I2C 0, bus corto (G21/G22): PCA9685, cable corto dentro de la caja: 400 kHz.
        # I2C 1, bus largo (G16/G17, reparto I2C): los dos VL53L0X, con cables LARGOS hasta la
        # cinta de vasos (~170 pF). A 400 kHz la subida con 2,2 kOhm (~317 ns) pasa
        # los 300 ns que pide la norma; a 100 kHz (1000 ns) cumple con margen. Los
        # VL53L0X leen cada 33 ms: 100 kHz sobra. Valor en firmware.i2c_bus_largo_hz.
        self.pca = PCA9685(I2C(0, sda=Pin(21), scl=Pin(22), freq=400_000))
        bus2 = SoftI2C(sda=Pin(pines.HUB_I2C_SDA), scl=Pin(pines.HUB_I2C_SCL), freq=cfg["i2c_bus_largo_hz"])
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
        for c in self.cintas.values():
            c.actualizar()
        self._revisar_enable()
        return {"presencia": self._digital("presencia"), "capacitivo": self._digital("capacitivo"),
                "inductivo": self._digital("inductivo"), "hall": hall,
                "cortina_mm": self.cortina.ultima, "interior_mm": self.interior.ultima,
                # Contador de mediciones de la cortina: si no crece, `cortina_mm`
                # es una lectura VIEJA (estacion.py la trata como cortina activa).
                "cortina_medidas": self.cortina.medidas,
                "carrusel": self.carrusel.posicion}

    def _revisar_enable(self):
        """Suelta los A4988 tras `reposo_ms` con las dos cintas quietas."""
        if any(c.moviendose() for c in self.cintas.values()):
            self._quietas_desde = time.ticks_ms()
            return
        if self.drivers_activos and time.ticks_diff(time.ticks_ms(), self._quietas_desde) >= self.reposo_ms:
            self.en.value(1)                         # ENABLE alto: bobinas sin corriente
            self.drivers_activos = False

    def avanzar_cinta(self, nombre, mm, ms):
        if not self.drivers_activos:
            # Volver a dar corriente ANTES del primer paso: la corriente de la
            # bobina tarda ~1 ms en subir (inductancia); 5 ms de margen, solo
            # la primera vez despues de una espera larga.
            self.en.value(0)
            self.drivers_activos = True
            time.sleep_ms(5)
        self._quietas_desde = time.ticks_ms()
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

    def carrusel_a(self, tubo, lugar="carga"):
        self.carrusel.a_tubo(tubo, lugar)

    def carrusel_moviendose(self):
        return self.carrusel.moviendose()

    def carrusel_buscar_referencia(self):
        self.carrusel.buscar_referencia()

    def carrusel_detener(self):
        self.carrusel.detener()
