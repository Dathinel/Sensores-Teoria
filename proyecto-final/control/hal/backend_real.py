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


class SensorInteriorReal(_ConPuente, SensorDiscreto):
    """El VL53L0X que mira al fondo del vaso, como sensor de SI/NO (igual que en la
    simulacion): hay algo adentro si la distancia es menor que la del fondo de un vaso
    vacio menos `vasos.margen_interior_mm`."""

    def __init__(self, puente, reloj, fondo_mm: float, margen_mm: float):
        super().__init__(puente, reloj)
        self.umbral_mm = fondo_mm - margen_mm

    def leer(self) -> bool:
        d = self.puente.tel.get("interior_mm")
        return d is not None and d < self.umbral_mm


class SensorCortinaReal(_ConPuente, SensorDiscreto):
    """La cortina la decide el ESP32 fijo (la seguridad no depende del PC): aqui solo se
    lee lo que el ESP32 ya decidio (`seguridad` = "cortina")."""

    def leer(self) -> bool:
        return self.puente.tel.get("seguridad") == "cortina"


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
    """Todo el hardware de la estacion, como lo ve la capa de control. Los nombres y
    los tipos son los MISMOS de backend_sim.EstacionBackendSim (auditoria 2026-09-27:
    antes el sensor del interior era una distancia aqui y un si/no alla)."""

    def __init__(self, puente, reloj, vasos: dict | None = None):
        v = vasos or {"altura_mm": 90, "margen_interior_mm": 10, "sensor_interior_sobre_boca_mm": 15}
        self.puente = puente
        self.sensor_presencia = SensorDiscretoReal(puente, reloj, "presencia")
        self.sensor_capacitivo = SensorDiscretoReal(puente, reloj, "capacitivo")
        self.sensor_inductivo = SensorDiscretoReal(puente, reloj, "inductivo")
        self.sensor_hall_carrusel = SensorDiscretoReal(puente, reloj, "hall")
        self.sensor_cortina = SensorCortinaReal(puente, reloj)
        self.sensor_interior = SensorInteriorReal(puente, reloj, v["altura_mm"] + v.get("sensor_interior_sobre_boca_mm", 15),
                                                  v["margen_interior_mm"])
        # Las distancias crudas, para diagnostico (el dashboard y el puente las muestran).
        self.distancia_cortina = SensorDistanciaReal(puente, reloj, "cortina_mm")
        self.distancia_interior = SensorDistanciaReal(puente, reloj, "interior_mm")
        self.banda_monedas = BandaReal(puente, reloj, "monedas")
        self.banda_vasos = BandaReal(puente, reloj, "vasos")
        self.prensa = PrensaReal(puente, reloj)
        self.dispensador_tapas = DispensadorReal(puente, reloj)
        self.servo_empujador_entrega = ServoReal(puente, reloj, "empujador")
        self.obturador = ServoReal(puente, reloj, "obturador")
        self.escape_canaleta = ServoReal(puente, reloj, "canaleta")
        self._reloj = reloj
        self._carrusel: dict | None = None     # ultimo giro pedido (ver carrusel_en)

    def desvio(self, al_almacen: bool) -> None:
        self.puente.comando("desvio", "almacen" if al_almacen else "rechazo", self._reloj())

    def carrusel_a(self, tubo: int, lugar: str = "carga") -> None:
        """Pide el giro (tubo 0 a 5 bajo la `carga` o sobre el `agujero`). NO espera:
        el 28BYJ-48 tarda hasta 4,1 s (media vuelta) y el ESP32 avisa con el evento
        `carrusel/llego` cuando el motor para. Quien suelta la moneda o abre el
        obturador pregunta antes `carrusel_en(tubo, lugar)` (2026-09-28: la moneda
        no puede caer a un tubo que todavia no llego)."""
        desde = len(self.puente.eventos)
        pedido = self.puente.comando("carrusel", "ir", self._reloj(), tubo=tubo, lugar=lugar)
        self._carrusel = {"tubo": tubo, "lugar": lugar, "desde": desde, "pedido": pedido}

    def carrusel_en(self, tubo: int, lugar: str = "carga") -> bool:
        """True solo si el ULTIMO giro pedido fue a ese tubo y lugar y el ESP32 ya
        aviso que llego POR ESE PEDIDO: el evento `llego` trae el id del comando
        que pidio el giro (`pedido`, revision 2026-09-29). Antes bastaba con que el
        aviso fuera posterior al pedido y del mismo tubo y lugar: el `llego` de un
        giro ANTERIOR al mismo tubo que llegaba tarde por el serial (o despues de
        un pedido intermedio a otro tubo) daba el tubo por puesto con el disco
        todavia girando."""
        c = self._carrusel
        if c is None or (c["tubo"], c["lugar"]) != (tubo, lugar):
            return False
        return any(e.get("src") == "carrusel" and e.get("ev") == "llego" and e.get("pedido") == c["pedido"]
                   for e in self.puente.eventos[c["desde"]:])
