"""Backend REAL de la HAL (fase 8): las mismas interfaces que backend_sim.py,
pero cada lectura sale de la telemetria del ESP32 fijo y cada accion es un
comando numerado por el USB serial (CLAUDE.md 10.1).

No importa pyserial (regla de `control/`): recibe un "puente" ya abierto
(`app.puente_serial.PuenteESP32`, o cualquier objeto con `tel`, `comando` y
`t_ms`). Los nombres de los campos y de los comandos son los del firmware
(`firmware/fijo/estacion.py`, tabla COMANDOS; telemetria en `_telemetria`).
"""

from __future__ import annotations

from control.hal.interfaces import (BandaIndexada, DispensadorTapas, MotorPrensa, SensorDiscreto,
                                    SensorDistancia, Servo)


class _ConPuente:
    def __init__(self, puente, reloj):
        self.puente = puente
        self.reloj = reloj                 # funcion -> ms actuales (el del supervisor)

    def _cmd(self, dst: str, act: str, **datos) -> int:
        return self.puente.comando(dst, act, self.reloj(), **datos)


class SensorDiscretoReal(_ConPuente, SensorDiscreto):
    def __init__(self, puente, reloj, campo: str):
        super().__init__(puente, reloj)
        self.campo = campo                 # "presencia", "capacitivo", "inductivo", "hall"

    def leer(self) -> bool:
        return bool(self.puente.tel.get(self.campo, False))


class SensorDistanciaReal(_ConPuente, SensorDistancia):
    """VL53L0X de la cortina o del interior del vaso. Sin medicion (nada en
    su alcance) devuelve infinito: "no ve nada"."""

    def __init__(self, puente, reloj, campo: str):
        super().__init__(puente, reloj)
        self.campo = campo                 # "cortina_mm", "interior_mm"

    def leer_mm(self) -> float:
        v = self.puente.tel.get(self.campo)
        return float("inf") if v is None else float(v)


class BandaReal(_ConPuente, BandaIndexada):
    def __init__(self, puente, reloj, nombre: str):
        super().__init__(puente, reloj)
        self.nombre = nombre               # "monedas" o "vasos"
        self._casilla = 0

    def avanzar_casilla(self) -> None:
        # El ESP32 mueve la cinta sin bloquear; el supervisor espera la pausa.
        self._cmd("linea" if self.nombre == "monedas" else "vasos", "avanzar")
        self._casilla += 1

    @property
    def casilla_actual(self) -> int:
        return self._casilla


class ServoReal(_ConPuente, Servo):
    """Un servo que hace su ciclo (activo y vuelta a reposo) en el ESP32."""

    ACCIONES = {"tapas": ("vasos", "tapar"), "empujador": ("vasos", "empujar"),
                "obturador": ("carrusel", "abrir"), "canaleta": ("canaleta", "soltar")}

    def __init__(self, puente, reloj, nombre: str):
        super().__init__(puente, reloj)
        self.dst, self.act = self.ACCIONES[nombre]

    def activar(self) -> None:
        self._cmd(self.dst, self.act)


class PrensaReal(_ConPuente, MotorPrensa):
    def ciclo(self) -> None:
        self._cmd("vasos", "prensar")

    def subir(self) -> None:
        # La cortina la sube el propio ESP32 en el mismo ciclo (no espera al
        # PC); desde aca no hay nada que mandar: solo se deja constancia.
        pass


class DispensadorReal(_ConPuente, DispensadorTapas):
    def __init__(self, puente, reloj, tapas: int = 20):
        super().__init__(puente, reloj)
        self.reserva = tapas               # PROVISIONAL: se cuenta, no hay sensor en el tubo

    def soltar_tapa(self) -> bool:
        if self.reserva <= 0:
            return False
        self._cmd("vasos", "tapar")
        self.reserva -= 1
        return True


class BackendReal:
    """Todo el hardware de la estacion, como lo ve la capa de control."""

    def __init__(self, puente, reloj):
        self.puente = puente
        self.sensor_presencia = SensorDiscretoReal(puente, reloj, "presencia")
        self.sensor_capacitivo = SensorDiscretoReal(puente, reloj, "capacitivo")
        self.sensor_inductivo = SensorDiscretoReal(puente, reloj, "inductivo")
        self.sensor_hall_carrusel = SensorDiscretoReal(puente, reloj, "hall")
        self.cortina = SensorDistanciaReal(puente, reloj, "cortina_mm")
        self.sensor_interior = SensorDistanciaReal(puente, reloj, "interior_mm")
        self.cinta_monedas = BandaReal(puente, reloj, "monedas")
        self.cinta_vasos = BandaReal(puente, reloj, "vasos")
        self.prensa = PrensaReal(puente, reloj)
        self.dispensador_tapas = DispensadorReal(puente, reloj)
        self.empujador = ServoReal(puente, reloj, "empujador")
        self.obturador = ServoReal(puente, reloj, "obturador")
        self.escape_canaleta = ServoReal(puente, reloj, "canaleta")
        self._reloj = reloj

    def desvio(self, al_almacen: bool) -> None:
        self.puente.comando("desvio", "almacen" if al_almacen else "rechazo", self._reloj())

    def carrusel_a(self, tubo: int) -> None:
        self.puente.comando("carrusel", "ir", self._reloj(), tubo=tubo)
