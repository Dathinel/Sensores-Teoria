"""Registro de casillas y sus transiciones de estado.

Una casilla es la unidad atomica de cada cinta: una posicion fisica que
puede contener un elemento y acumula lo que cada estacion descubre sobre
el. Ninguna estacion puede revertir un rechazo escrito por una estacion
anterior (docs/especificacion.md, seccion 7).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Generic, TypeVar


class EstadoVaso(str, Enum):
    """Maquina de estados de una casilla de la cinta de vasos (seccion 7)."""

    VACIA = "vacia"
    VALIDA = "valida"
    INVALIDA = "invalida"
    LLENANDO = "llenando"
    LLENA = "llena"
    TAPADA = "tapada"
    RECHAZADA = "rechazada"
    ENTREGADA = "entregada"


@dataclass
class CasillaMoneda:
    """Registro acumulado de una casilla de la cinta de monedas a lo largo
    de las estaciones 1 a 7."""

    indice: int
    ocupada: bool = False
    metal: bool | None = None
    diametro_mm: float | None = None
    circularidad: float | None = None
    contornos_internos: int | None = None
    bimetalica: bool | None = None
    clase: str | None = None
    confianza: float | None = None
    aceptada: bool | None = None
    causa: str | None = None
    denominacion: int | None = None
    valor: int | None = None
    masa_estimada_g: float | None = None

    @property
    def rechazada(self) -> bool:
        return self.causa is not None

    def rechazar(self, causa: str) -> None:
        """Marca la casilla como rechazada con la causa dada. Si ya estaba
        rechazada por una estacion anterior, no hace nada: ese veredicto no
        se revierte ni se sobrescribe."""
        if self.rechazada:
            return
        self.aceptada = False
        self.causa = causa


@dataclass
class CasillaVaso:
    """Registro acumulado de una casilla de la cinta de vasos."""

    indice: int
    estado: EstadoVaso = EstadoVaso.VACIA
    cantidad_monedas: int = 0
    valor_total: int = 0
    masa_estimada_g: float = 0.0
    # Un vaso lleva UNA sola denominacion (regla del grupo): se fija con la
    # primera moneda y ninguna de otra denominacion puede entrar despues. La
    # unica excepcion es el vaso "otras" (denominaciones que ya no circulan).
    denominacion: int | str | None = None
    # Numero del marcador ArUco impreso en el vaso personalizado, leido por
    # la camara de vasos en la verificacion. Si en el llenado o en la tapa se
    # lee otro numero, alguien cambio el vaso por otro igual.
    marcador: int | None = None

    def degradar(self, estado: EstadoVaso) -> None:
        """Cualquier estacion puede degradar el estado en cualquier momento
        (p. ej. a INVALIDA si al reverificar ya no pasa la barrera)."""
        self.estado = estado

    def acumular_moneda(self, valor: int, masa_g: float) -> None:
        self.cantidad_monedas += 1
        self.valor_total += valor
        self.masa_estimada_g += masa_g


_T = TypeVar("_T")


class RegistroCasillas(Generic[_T]):
    """Registro generico indexado por numero de casilla. Crea la casilla la
    primera vez que se pide un indice; las siguientes veces devuelve la
    misma instancia para seguir acumulando sobre ella."""

    def __init__(self, fabrica: Callable[[int], _T]):
        self._fabrica = fabrica
        self._casillas: dict[int, _T] = {}

    def obtener(self, indice: int) -> _T:
        if indice not in self._casillas:
            self._casillas[indice] = self._fabrica(indice)
        return self._casillas[indice]

    def existe(self, indice: int) -> bool:
        return indice in self._casillas

    def eliminar(self, indice: int) -> None:
        self._casillas.pop(indice, None)

    def items(self) -> list[tuple[int, _T]]:
        """Todas las casillas registradas hasta ahora, en orden de indice."""
        return sorted(self._casillas.items())


def registro_monedas() -> RegistroCasillas[CasillaMoneda]:
    return RegistroCasillas(CasillaMoneda)


def registro_vasos() -> RegistroCasillas[CasillaVaso]:
    return RegistroCasillas(CasillaVaso)
