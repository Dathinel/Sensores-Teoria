"""Tabla de referencia de las monedas colombianas y utilidades asociadas.

La tabla vive en config/monedas.yaml (cuatro generaciones: nueva, antigua,
muy_antigua e historica); aqui solo se carga y se consulta. Los valores son
nominales; el desgaste real mueve decimas de milimetro en diametro y algo
mas en masa (CLAUDE.md, seccion 6). Se usan para el calculo de peso
estimado y como compuerta previa de la vision, nunca como criterio unico de
aceptacion: con monedas extranjeras y varias generaciones en juego el
diametro deja de ser discriminante (una moneda de un euro cae dentro del
rango de las de 500), por eso la decision final es por reconocimiento de la
cara.

Las filas con `verificado: false` son PROVISIONALES: medidas aproximadas
sin comprobar, puestas para poder simular. Hay que medir monedas reales
antes de entrenar el clasificador (docs/replicacion.md).
"""

from dataclasses import dataclass
from pathlib import Path

import yaml

RUTA_TABLA = Path(__file__).resolve().parent.parent / "config" / "monedas.yaml"

# Clase reservada para lo que el clasificador no reconoce como moneda
# colombiana: monedas extranjeras, botones metalicos, confianza insuficiente.
CLASE_OTRO = "otro"

FAMILIAS = ("nueva", "antigua", "muy_antigua", "historica")


@dataclass(frozen=True)
class Moneda:
    denominacion: int
    familia: str
    diametro_mm: float
    masa_g: float
    ferromagnetica: bool
    bimetalica: bool
    material: str = ""
    verificado: bool = True

    @property
    def clase(self) -> str:
        """Identificador usado por el clasificador de vision, p. ej. '500_nueva'
        (mismo formato del contrato de datos de la seccion 10.2)."""
        return f"{self.denominacion}_{self.familia}"


def _cargar(ruta: Path = RUTA_TABLA) -> tuple[tuple[Moneda, ...], tuple[int, ...], tuple[str, ...]]:
    with open(ruta, encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo)
    tabla = tuple(Moneda(**fila) for fila in datos["monedas"])
    for m in tabla:
        if m.familia not in FAMILIAS:
            raise ValueError(f"familia desconocida en {ruta.name}: {m.familia!r}")
    return tabla, tuple(datos["denominaciones_con_tubo"]), tuple(datos["familias_entrenadas"])


TABLA_MONEDAS, DENOMINACIONES_CON_TUBO, FAMILIAS_ENTRENADAS = _cargar()

_POR_CLASE: dict[str, Moneda] = {m.clase: m for m in TABLA_MONEDAS}


def clases_colombianas() -> tuple[str, ...]:
    """Todas las clases que puede predecir el clasificador, sin contar 'otro'."""
    return tuple(_POR_CLASE.keys())


def buscar_por_clase(clase: str) -> Moneda | None:
    """Moneda de referencia para una clase, o None si es 'otro' o desconocida."""
    return _POR_CLASE.get(clase)


def diametro_nominal_mm(clase: str) -> float | None:
    moneda = buscar_por_clase(clase)
    return moneda.diametro_mm if moneda else None


def valor_pesos(clase: str) -> int | None:
    moneda = buscar_por_clase(clase)
    return moneda.denominacion if moneda else None


def masa_nominal_g(clase: str) -> float | None:
    moneda = buscar_por_clase(clase)
    return moneda.masa_g if moneda else None


def reconocible(clase: str) -> bool:
    """Si el clasificador fue entrenado con la familia de esta clase."""
    moneda = buscar_por_clase(clase)
    return moneda is not None and moneda.familia in FAMILIAS_ENTRENADAS


def sin_verificar() -> tuple[Moneda, ...]:
    """Clases cuyas medidas son PROVISIONALES (hay que medirlas)."""
    return tuple(m for m in TABLA_MONEDAS if not m.verificado)
