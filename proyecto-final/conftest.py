"""Hace que `control` y `app` sean importables desde tests/ sin instalar el
paquete. pytest no agrega automaticamente la raiz del repo a sys.path
cuando tests/ no tiene __init__.py (y no debe tenerlo, para que pytest use
nombres de test simples)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
