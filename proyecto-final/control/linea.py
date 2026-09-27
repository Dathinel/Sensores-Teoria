"""Maquina de estados de la cinta de monedas (CLAUDE.md, seccion 5, pasos
1 a 8).

Grupo (2026-09-25): "filtro total". La cinta tiene 4 estaciones --
presencia, material, vision y descarga -- y UNA sola salida de rechazo: todo
lo que no pase todos los filtros sale por la compuerta de desvio de la
descarga a la bandeja de rechazo; solo lo aceptado va al almacen. Ya no hay
expulsores laterales (se quitan 2 servos y 2 sensores de confirmacion y la
cinta es mas corta). Los filtros se siguen pudiendo demostrar uno por uno:
cada rechazo queda registrado con su causa (dashboard y visor).

Codigo puro: no conoce PyBullet, pyserial ni el ESP32 (seccion 8 y regla 17).
Recibe lo que cada estacion "vio" para una casilla dada y va acumulando el
registro; `destino` responde a donde se enruta el elemento segun lo
acumulado hasta ese momento. Las fases 2 y 3 son las que deciden CUANDO
llamar a cada metodo, sincronizado con el avance real de la cinta (sim o
real); esta clase solo sabe QUE hacer con cada lectura.
"""

from . import monedas
from .registro import CasillaMoneda, RegistroCasillas, registro_monedas
from .reglas import (
    ParametrosFiltrado,
    evaluar_clasificacion,
    evaluar_coherencia,
    evaluar_geometria,
    evaluar_material,
)


class Destino:
    """A donde puede ir una casilla una vez que se conoce su veredicto."""

    VACIA = "vacia"
    RECHAZO = "rechazo"
    VASO = "vaso"


class LineaMonedas:
    """Aplica las estaciones de presencia, material y vision sobre una
    casilla, en orden, sin saltarse ninguna ni revertir un rechazo previo."""

    def __init__(self, params: ParametrosFiltrado = ParametrosFiltrado()):
        self._params = params
        self.registro: RegistroCasillas[CasillaMoneda] = registro_monedas()

    @property
    def params(self) -> ParametrosFiltrado:
        return self._params

    def estacion_1_presencia(self, indice: int, ocupada: bool) -> CasillaMoneda:
        """Si esta vacia, la casilla se marca vacia y las demas estaciones
        la ignoran durante todo su recorrido (no se vuelve a escribir)."""
        casilla = self.registro.obtener(indice)
        casilla.ocupada = ocupada
        return casilla

    def estacion_2_material(self, indice: int, capacitivo: bool, inductivo: bool) -> CasillaMoneda:
        """Capacitivo activo e inductivo inactivo es no metalico; ambos
        activos es metal. Lo no metalico queda rechazado aqui y la camara ni
        lo mira (no gasta un ciclo de vision); sale en la descarga."""
        casilla = self.registro.obtener(indice)
        if not casilla.ocupada:
            return casilla
        # El inductivo SOLO reacciona a metal, asi que si el ve metal, es
        # metal, aunque el capacitivo haya fallado (falso negativo). Tabla:
        #   cap=1 ind=0 -> no metalico (plastico, bloque)
        #   cap=1 ind=1 -> metal
        #   cap=0 ind=1 -> metal (el capacitivo fallo; se confia en el inductivo)
        #   cap=0 ind=0 -> nada o no metalico (p. ej. la mano que se retiro)
        metal = inductivo
        casilla.metal = metal
        causa = evaluar_material(metal)
        if causa:
            casilla.rechazar(causa)
        return casilla

    def estacion_5_vision(
        self,
        indice: int,
        *,
        diametro_mm: float,
        circularidad: float,
        contornos_internos: int,
        clase: str,
        confianza: float,
    ) -> CasillaMoneda:
        """Solo corre si la casilla sigue viva (ocupada y no rechazada por
        material): no vale la pena gastar un ciclo de camara en algo que ya
        va para la bandeja de rechazo."""
        casilla = self.registro.obtener(indice)
        if not casilla.ocupada or casilla.rechazada:
            return casilla

        casilla.diametro_mm = diametro_mm
        casilla.circularidad = circularidad
        casilla.contornos_internos = contornos_internos
        casilla.clase = clase
        casilla.confianza = confianza

        causa = evaluar_geometria(diametro_mm, circularidad, contornos_internos, self._params)
        if causa is None:
            causa = evaluar_clasificacion(clase, confianza, self._params)
        if causa is None:
            causa = evaluar_coherencia(clase, diametro_mm, self._params)

        if causa:
            casilla.rechazar(causa)
        else:
            moneda = monedas.buscar_por_clase(clase)
            assert moneda is not None
            casilla.aceptada = True
            casilla.denominacion = moneda.denominacion
            casilla.valor = moneda.denominacion
            casilla.masa_estimada_g = moneda.masa_g
        return casilla

    def destino(self, indice: int) -> str:
        """Descarga: a donde se enruta la casilla segun lo acumulado. Todo
        rechazo, sea cual sea su causa, va a la misma bandeja; la causa queda
        en el registro."""
        casilla = self.registro.obtener(indice)
        if not casilla.ocupada:
            return Destino.VACIA
        if casilla.rechazada:
            return Destino.RECHAZO
        if casilla.aceptada:
            return Destino.VASO
        raise ValueError(f"la casilla {indice} todavia no tiene veredicto")

    def procesar_elemento(
        self,
        indice: int,
        *,
        ocupada: bool,
        capacitivo: bool = False,
        inductivo: bool = False,
        diametro_mm: float | None = None,
        circularidad: float | None = None,
        contornos_internos: int | None = None,
        clase: str | None = None,
        confianza: float | None = None,
    ) -> str:
        """Atajo para pruebas y para el modo oraculo: corre las tres
        estaciones con todas las lecturas de una sola vez y devuelve el
        destino final. En la simulacion/hardware real cada estacion se
        llama por separado, sincronizada con el avance de la cinta."""
        self.estacion_1_presencia(indice, ocupada)
        if not ocupada:
            return self.destino(indice)

        self.estacion_2_material(indice, capacitivo, inductivo)
        casilla = self.registro.obtener(indice)
        if not casilla.rechazada:
            self.estacion_5_vision(
                indice,
                diametro_mm=diametro_mm,
                circularidad=circularidad,
                contornos_internos=contornos_internos,
                clase=clase,
                confianza=confianza,
            )
        return self.destino(indice)
