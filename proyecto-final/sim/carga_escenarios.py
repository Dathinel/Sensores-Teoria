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
# Usuario (2026-09-26): la corrida normal de la interfaz es UNA (prueba_completa.yaml, con un
# caso de cada filtro). Los escenarios de un solo filtro de tests/escenarios (los de las pruebas
# automaticas) se pueden correr ademas desde la interfaz como "prueba de un filtro"
# (usuario, 2026-09-27: ver PRUEBAS_DE_UN_FILTRO al final).
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


# ---------------------------------------------------------------------------
# Pruebas de UN filtro y "colocar pieza X" (usuario, 2026-09-27)
# ---------------------------------------------------------------------------
# El enunciado dice que los filtros "se van a probar uno por uno" en la sustentacion. La interfaz
# sigue teniendo UNA corrida normal (prueba_completa), y ademas puede correr cada escenario de un
# solo filtro de tests/escenarios (los mismos que usan las pruebas automaticas, asi que lo que se
# muestra es lo que esta probado) o poner una pieza concreta en la proxima carga.

PRUEBAS_DE_UN_FILTRO = [
    {"escenario": "no_metalico", "nombre": "Material: no metálico", "estacion": "E2",
     "sensores": ["capacitivo", "inductivo"], "causa": "no_metalico",
     "espera": "Botones de plástico: el capacitivo los ve y el inductivo no. Salen a la bandeja de "
               "rechazo sin gastar la cámara."},
    {"escenario": "fuera_de_rango", "nombre": "Visión: diámetro fuera de rango", "estacion": "E3",
     "sensores": ["camara"], "causa": "fuera_de_rango",
     "espera": "Discos metálicos redondos de 10 y 32 mm: pasan el material, la cámara mide el diámetro "
               "y queda fuera de 16,5-27,5 mm."},
    {"escenario": "no_circular", "nombre": "Visión: no circular", "estacion": "E3",
     "sensores": ["camara"], "causa": "no_circular",
     "espera": "Bloques metálicos: pasan el material; la circularidad queda por debajo de 0,90."},
    {"escenario": "perforado", "nombre": "Visión: perforado", "estacion": "E3",
     "sensores": ["camara"], "causa": "perforado",
     "espera": "Botones metálicos con agujero: la cámara encuentra un contorno interno."},
    {"escenario": "no_reconocida", "nombre": "Visión: no reconocida", "estacion": "E3",
     "sensores": ["camara"], "causa": "no_reconocida",
     "espera": "Discos del tamaño de una moneda pero sin cara colombiana: el clasificador dice 'otro'."},
    {"escenario": "incoherente", "nombre": "Visión: incoherente", "estacion": "E3",
     "sensores": ["camara"], "causa": "incoherente",
     "espera": "Cara de moneda colombiana con un diámetro que no le corresponde (más de 1,2 mm de "
               "diferencia): la regla que cruza dos medidas la rechaza."},
]

# Piezas que se pueden poner a mano en la proxima carga. Mismos campos que un elemento de los YAML.
PIEZAS = {
    **{f"{d}_{f}": {"nombre": f"Moneda de ${d:,} ({f})".replace(",", "."),
                    "datos": {"tipo": "moneda", "clase_real": f"{d}_{f}", "destino_esperado": "vaso"}}
       for d in (50, 100, 200, 500, 1000) for f in ("nueva", "antigua") if not (d == 1000 and f == "antigua")},
    "euro": {"nombre": "Moneda de 1 euro (extranjera)",
             "datos": {"tipo": "boton_metalico", "metal": True, "diametro_mm": 23.25, "circularidad": 0.98,
                       "contornos_internos": 0, "destino_esperado": "rechazo"}},
    "boton_plastico": {"nombre": "Botón de plástico", "datos": {"tipo": "boton_plastico", "destino_esperado": "rechazo"}},
    "boton_metalico": {"nombre": "Botón metálico con ojales", "datos": {"tipo": "boton_metalico", "destino_esperado": "rechazo"}},
    "bloque": {"nombre": "Bloque de color (metálico)",
               "datos": {"tipo": "bloque", "metal": True, "destino_esperado": "rechazo"}},
    "disco_chico": {"nombre": "Disco metálico de 10 mm",
                    "datos": {"tipo": "boton_metalico", "metal": True, "diametro_mm": 10.0, "circularidad": 0.99,
                              "contornos_internos": 0, "destino_esperado": "rechazo"}},
    "incoherente": {"nombre": "Cara de $500 con otro diámetro",
                    "datos": {"tipo": "moneda", "clase_real": "500_nueva", "diametro_mm": 20.0, "masa_g": 7.1,
                              "destino_esperado": "rechazo"}},
}


def escenarios_validos() -> set[str]:
    """Nombres (nunca rutas) que se pueden pedir por orden: los de la interfaz y los de las pruebas."""
    return {p.stem for d in (DIRECTORIO_ESCENARIOS, DIRECTORIO_PRUEBAS_AISLADAS) for p in d.glob("*.yaml")}


def prueba_de_un_filtro(escenario: str) -> dict | None:
    return next((p for p in PRUEBAS_DE_UN_FILTRO if p["escenario"] == escenario), None)


def especificacion_pieza(pieza: str) -> EspecificacionElemento:
    """La pieza del catalogo lista para la planta (ValueError si no existe)."""
    if pieza not in PIEZAS:
        raise ValueError(f"pieza desconocida: {pieza!r}")
    return _construir_elemento(dict(PIEZAS[pieza]["datos"]))
