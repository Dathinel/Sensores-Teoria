"""Página sola del detector, para abrirla desde el celular (S24 Ultra) en la misma red Wi-Fi.

No se corre directo: `python -m vision.yolo_monedas` la arranca escuchando en la red local.
"""

import sys
from pathlib import Path

# Streamlit pone en sys.path la carpeta del script, no proyecto-final/ (igual que app/dashboard/inicio.py).
RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Detector de monedas", page_icon="🪙", layout="centered")

from app.dashboard import estilo  # noqa: E402
from vision.yolo_monedas import vista  # noqa: E402

estilo.aplicar()
vista.dibujar()
