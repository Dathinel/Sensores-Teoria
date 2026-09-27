"""Carga de escenarios reproducibles desde YAML (CLAUDE.md, seccion 11):

"Defina archivos YAML de escenario que listen la secuencia de elementos a
inyectar... Asi la sustentacion es repetible y las pruebas automaticas
comparan resultados contra lo esperado. Un escenario por cada filtro que
el profesor va a probar por separado, mas un escenario mixto largo."

Cada item de la lista `elementos` de un YAML es, o bien `tipo: vacia`
(la casilla queda vacia ese ciclo), o bien un elemento con su verdad de
terreno (la misma que consume `sim/mundo.py` al crearlo) y el
`destino_esperado` contra el que se compara el resultado real.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from control import monedas

DIRECTORIO_ESCENARIOS = Path(__file__).parent / "escenarios"
# Usuario (2026-09-26): en la interfaz queda UNA sola prueba
# (prueba_completa.yaml, con un caso de cada filtro). Los escenarios de un
# solo filtro y el mixto de 20 son de las pruebas automaticas (tests/escenarios).
DIRECTORIO_PRUEBAS_AISLADAS = Path(__file__).parent.parent / "tests" / "escenarios"
ESCENARIO_UNICO = "prueba_completa"

TIPOS_VALIDOS = ("vacia", "moneda", "boton_plastico", "boton_metalico", "bloque", "mano")


@dataclass
class EspecificacionElemento:
    tipo: str
    destino_esperado: str
    clase_real: str | None = None
    metal: bool = False
    diametro_mm: float | None = None
    masa_g: float | None = None
    circularidad: float | None = None
    contornos_internos: int | None = None


@dataclass
class Escenario:
    nombre: str
    descripcion: str
    elementos: list[EspecificacionElemento] = field(default_factory=list)


def _construir_elemento(datos: dict) -> EspecificacionElemento:
    tipo = datos.get("tipo")
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo de elemento invalido en escenario: {tipo!r} (validos: {TIPOS_VALIDOS})")

    destino_esperado = datos.get("destino_esperado")
    if destino_esperado is None:
        if tipo == "vacia":
            destino_esperado = "vacia"
        else:
            raise ValueError(f"al elemento de tipo '{tipo}' le falta 'destino_esperado'")

    clase_real = datos.get("clase_real")
    diametro_mm = datos.get("diametro_mm")
    masa_g = datos.get("masa_g")

    if tipo == "moneda" and clase_real is not None:
        # Completa diametro/masa desde la tabla de referencia si el YAML no
        # los fuerza explicitamente (p. ej. el escenario de 'incoherente'
        # SI los fuerza, a proposito, para que no coincidan).
        moneda_ref = monedas.buscar_por_clase(clase_real)
        if moneda_ref is None:
            raise ValueError(f"clase_real desconocida: {clase_real!r}")
        if diametro_mm is None:
            diametro_mm = moneda_ref.diametro_mm
        if masa_g is None:
            masa_g = moneda_ref.masa_g

    metal_por_defecto = tipo in ("moneda", "boton_metalico")

    return EspecificacionElemento(
        tipo=tipo,
        destino_esperado=destino_esperado,
        clase_real=clase_real,
        metal=datos.get("metal", metal_por_defecto),
        diametro_mm=diametro_mm,
        masa_g=masa_g,
        circularidad=datos.get("circularidad"),
        contornos_internos=datos.get("contornos_internos"),
    )


def cargar_escenario(nombre_archivo: str) -> Escenario:
    """`nombre_archivo` es el nombre del YAML dentro de sim/escenarios/ (o de
    tests/escenarios/), con o sin extension (p. ej.
    "prueba_completa" o "mixto_20.yaml")."""
    ruta = DIRECTORIO_ESCENARIOS / nombre_archivo
    if not ruta.suffix:
        ruta = ruta.with_suffix(".yaml")
    if not ruta.exists():
        ruta = DIRECTORIO_PRUEBAS_AISLADAS / ruta.name

    with open(ruta, encoding="utf-8") as archivo:
        datos = yaml.safe_load(archivo)

    elementos = [_construir_elemento(e) for e in datos.get("elementos", [])]
    return Escenario(nombre=datos["nombre"], descripcion=datos.get("descripcion", ""), elementos=elementos)


def listar_escenarios() -> list[str]:
    return sorted(p.stem for p in DIRECTORIO_ESCENARIOS.glob("*.yaml"))
