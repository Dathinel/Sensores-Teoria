"""Carga de `config/parametros.yaml` (CLAUDE.md, regla 17: "todo numero
magico va a configuracion").

`control/reglas.py` trae valores por defecto en `ParametrosFiltrado` solo
para que las pruebas unitarias no dependan de un archivo; en ejecucion real
(supervisor, dashboard) los umbrales salen siempre de aqui.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from control.reglas import ParametrosFiltrado

RAIZ_REPO = Path(__file__).resolve().parent.parent
RUTA_PARAMETROS = RAIZ_REPO / "config" / "parametros.yaml"


def cargar_parametros(ruta: str | Path = RUTA_PARAMETROS) -> dict:
    with open(ruta, encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)


def parametros_filtrado(parametros: dict | None = None, **sobrescribir) -> ParametrosFiltrado:
    """`sobrescribir` permite cambiar un umbral en caliente (p. ej. la
    confianza minima desde la pestana de Control del dashboard) sin tocar
    el YAML."""
    parametros = parametros if parametros is not None else cargar_parametros()
    f = parametros["filtrado"]
    base = ParametrosFiltrado(
        diametro_min_mm=f["diametro_min_mm"],
        diametro_max_mm=f["diametro_max_mm"],
        circularidad_minima=f["circularidad_minima"],
        confianza_minima=f["confianza_minima"],
        tolerancia_coherencia_mm=f["tolerancia_coherencia_mm"],
    )
    return replace(base, **{k: v for k, v in sobrescribir.items() if v is not None})


def ruta_bd(parametros: dict | None = None) -> Path:
    # PLANTA_BD permite apuntar el dashboard a otra base (las pruebas).
    import os

    if os.environ.get("PLANTA_BD"):
        return Path(os.environ["PLANTA_BD"])
    parametros = parametros if parametros is not None else cargar_parametros()
    ruta = Path(parametros["supervisor"]["ruta_bd"])
    return ruta if ruta.is_absolute() else RAIZ_REPO / ruta
