"""Almacen de monedas aceptadas, separado por denominacion.

Reglas del grupo (revision del paso a paso, 2026-09-22):

- Ninguna moneda colombiana aceptada se descarta: si todavia no tiene vaso,
  se GUARDA.
- Cada vaso lleva UNA sola denominacion (un vaso de 500, otro de 50...),
  sin importar la familia: una de 500 nueva y una de 500 antigua van al
  mismo vaso.

Por eso la estacion 7 ya no echa cada moneda al vaso que este en llenado
(asi se mezclaban denominaciones): un selector la manda al tubo de su
denominacion, y cuando un tubo junta un lote completo se descarga entero en
un vaso vacio y verificado. Este modulo es solo la contabilidad de esos
tubos (codigo puro, sin PyBullet): que hay en cada uno, cuando hay un lote
listo y sacar el lote en orden de llegada.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .monedas import DENOMINACIONES_CON_TUBO

DENOMINACIONES = DENOMINACIONES_CON_TUBO
# Compartimiento para las denominaciones aceptadas que NO tienen tubo (las
# de $1, $2, $5, $10 y $20 de las series viejas, que ya no circulan): se
# guardan y, al completar un lote, se empacan JUNTAS en su propio vaso de
# "otras denominaciones" (decision del grupo, 2026-09-22: separarlas mas
# seria ineficiente). Es la unica excepcion a "un vaso = una denominacion".
OTRAS = "otras"


@dataclass(frozen=True)
class MonedaAlmacenada:
    id_registro: int
    clase: str
    valor: int
    masa_g: float


class TuboLleno(Exception):
    """El tubo de esa denominacion no tiene espacio: la moneda no se puede
    descartar, asi que quien llama tiene que esperar (detener la cinta de
    monedas) hasta que se embale un lote y se libere espacio."""


class AlmacenDenominaciones:
    def __init__(self, denominaciones: tuple[int, ...] = DENOMINACIONES, capacidad: int = 25,
                 capacidad_otras: int = 40):
        self.capacidad = capacidad
        self.capacidad_otras = capacidad_otras
        self._tubos: dict[int, deque[MonedaAlmacenada]] = {d: deque() for d in denominaciones}
        self._otras: deque[MonedaAlmacenada] = deque()

    @property
    def denominaciones(self) -> tuple[int, ...]:
        return tuple(self._tubos)

    def cantidad(self, denominacion: int | str) -> int:
        return len(self._otras) if denominacion == OTRAS else len(self._tubos[denominacion])

    def contenido(self) -> dict[int, int]:
        return {d: len(t) for d, t in self._tubos.items()}

    def cantidad_otras(self) -> int:
        return len(self._otras)

    def total(self) -> int:
        return sum(len(t) for t in self._tubos.values()) + len(self._otras)

    def valor_total(self) -> int:
        return sum(m.valor for t in self._tubos.values() for m in t) + sum(m.valor for m in self._otras)

    def destino(self, denominacion: int) -> int | str:
        """Tubo (la denominacion) o el compartimiento OTRAS."""
        return denominacion if denominacion in self._tubos else OTRAS

    def puede_recibir(self, denominacion: int) -> bool:
        if self.destino(denominacion) == OTRAS:
            return len(self._otras) < self.capacidad_otras
        return len(self._tubos[denominacion]) < self.capacidad

    def guardar(self, denominacion: int, moneda: MonedaAlmacenada) -> int:
        """Guarda la moneda (en su tubo o en OTRAS) y devuelve cuantas hay
        ahora en ese lugar."""
        if not self.puede_recibir(denominacion):
            raise TuboLleno(denominacion)
        lugar = self._otras if self.destino(denominacion) == OTRAS else self._tubos[denominacion]
        lugar.append(moneda)
        return len(lugar)

    def lote_listo(self, tamano: int, *, aceptar_parciales: bool = False) -> int | None:
        """Denominacion con un lote completo (>= `tamano` monedas) para
        embalar, o None. Si hay varias, la que tiene mas monedas (la que mas
        se acerca a llenar su tubo). `aceptar_parciales` sirve para el final
        de turno: embala lo que haya aunque no complete el lote."""
        minimo = 1 if aceptar_parciales else tamano
        orden = (*self.denominaciones, OTRAS)
        candidatos = [(len(t), d) for d, t in self._tubos.items() if len(t) >= minimo]
        if len(self._otras) >= minimo:
            candidatos.append((len(self._otras), OTRAS))
        if not candidatos:
            return None
        return max(candidatos, key=lambda c: (c[0], -orden.index(c[1])))[1]

    def exportar(self) -> list[dict]:
        """Lo que hay en los tubos, moneda por moneda, para guardarlo al
        terminar el turno y cargarlo en el siguiente (`PlantaSimulada.precargar_almacen`)."""
        return [
            {"clase": m.clase, "valor": m.valor, "masa_g": m.masa_g}
            for tubo in (*self._tubos.values(), self._otras) for m in tubo
        ]

    def sacar(self, denominacion: int | str, cantidad: int) -> list[MonedaAlmacenada]:
        """Saca hasta `cantidad` monedas (de un tubo o de OTRAS), las mas
        antiguas primero."""
        tubo = self._otras if denominacion == OTRAS else self._tubos[denominacion]
        return [tubo.popleft() for _ in range(min(cantidad, len(tubo)))]
