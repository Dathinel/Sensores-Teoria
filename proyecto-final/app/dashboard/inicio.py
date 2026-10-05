"""Punto de entrada del dashboard de Streamlit (docs/especificacion.md, sección 13).

Este proceso SOLO LEE de SQLite y escribe órdenes en la tabla `ordenes`
(sección 8). No importa PyBullet ni abre la simulación: la línea la corre
`app/supervisor.py` en otro proceso. Por eso se puede refrescar, recargar o
abrir en varias pestañas del navegador sin que la línea se entere.

Refresco en vivo con `st.fragment(run_every=...)`: solo se reejecuta el bloque
de la pestaña ABIERTA cada `dashboard.refresco_s` segundos (las pestañas se
dibujan solo cuando están abiertas), y no hay ningún bucle infinito.

Uso, desde la raíz del repo (con el supervisor corriendo en otra terminal):
    streamlit run app/dashboard/inicio.py      (o python -m app.dashboard)
o todo junto con:
    python -m app.lanzar
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit agrega al path la carpeta del script (app/dashboard/), no la raíz del repo;
# sin esto no se encuentran los paquetes `app`, `control` y `sim`.
RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Monedas inteligentes", page_icon="🪙", layout="wide")

from app.dashboard import estilo  # noqa: E402
from app.dashboard.cabecera import cabecera  # noqa: E402
from app.dashboard.controles import barra_lateral  # noqa: E402
from app.dashboard.pestanas import (asistente, ayuda, calidad, carro, linea, monedas, montaje,  # noqa: E402
                                    pruebas, resumen)

# (etiqueta, módulo, claves de ?pestana= que la abren)
PESTANAS = [
    (":material/dashboard: Resumen", resumen, ("resumen",)),
    (":material/paid: Monedas y vasos", monedas, ("monedas", "produccion")),
    (":material/verified: Calidad del filtro", calidad, ("calidad", "rechazos", "inspeccion")),
    (":material/conveyor_belt: Línea en vivo", linea, ("linea",)),
    (":material/science: Pruebas", pruebas, ("pruebas",)),
    (":material/local_shipping: Carro y ruta", carro, ("carro", "ruta")),
    (":material/construction: Montaje real", montaje, ("montaje", "replicacion")),
    (":material/forum: Asistente", asistente, ("asistente",)),
    (":material/help: Ayuda", ayuda, ("ayuda",)),
]


def main() -> None:
    estilo.aplicar()
    cabecera()
    barra_lateral()
    pedida = st.query_params.get("pestana", "")
    etiqueta_pedida = next((e for e, _, claves in PESTANAS if pedida in claves), PESTANAS[0][0])
    # on_change="rerun": solo la pestaña abierta se dibuja (y se refresca), no las nueve.
    tabs = st.tabs([e for e, _, _ in PESTANAS], default=etiqueta_pedida, key="pestana_abierta", on_change="rerun")
    for tab, (_, modulo, _) in zip(tabs, PESTANAS):
        # `.open` es None si Streamlit no sabe cuál está abierta: entonces se dibujan todas.
        if tab.open is False:
            continue
        with tab:
            modulo.pestana()


main()
