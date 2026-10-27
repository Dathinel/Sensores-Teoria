"""Las carpetas del proyecto, en un solo lugar.

Sin dependencias (ni yaml ni control/): lo puede importar cualquier modulo de app/,
tambien app/lanzar.py, que arranca antes de que haga falta lo demas. Si un modulo se
mueve dentro de app/, sus rutas siguen igual porque no dependen de donde esta el.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent     # proyecto-final/
CONFIG = RAIZ / "config"
DATOS = RAIZ / "datos"
DOCS = RAIZ / "docs"
VISOR = RAIZ / "app" / "visor3d"
