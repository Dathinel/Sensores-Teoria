"""Configuracion del lado de la aplicacion: la ruta de la base (`ruta_bd`).

La carga de `config/parametros.yaml` y los umbrales del filtro viven en
`control/configuracion.py` (los usan tambien sim/ y control/, que no deben
depender de app/); aqui se reexportan para no tocar a sus usuarios.
"""

from __future__ import annotations

from pathlib import Path

from app.rutas import RAIZ
from control.configuracion import RUTA_PARAMETROS, cargar_parametros, parametros_filtrado  # noqa: F401


def ruta_bd(parametros: dict | None = None) -> Path:
    # PLANTA_BD permite apuntar el dashboard a otra base (las pruebas).
    import os

    if os.environ.get("PLANTA_BD"):
        return Path(os.environ["PLANTA_BD"])
    parametros = parametros if parametros is not None else cargar_parametros()
    ruta = Path(parametros["supervisor"]["ruta_bd"])
    return ruta if ruta.is_absolute() else RAIZ / ruta
