"""Configuracion comun de todas las pruebas (tests/ y sus subcarpetas).

La raiz del proyecto se vuelve importable desde `pytest.ini` (`pythonpath = .`), no desde aqui.

Por que existe este archivo: la escena de PyBullet (`sim/mundo.py`) llama a pybullet SIN
`physicsClientId`, o sea, siempre sobre la conexion 0. Varias pruebas de `tests/app/` crean un
`Supervisor` (que abre su propio mundo) y no lo cierran al terminar. Si ese mundo queda abierto,
las pruebas de `tests/sim/` que corren despues abren una conexion nueva pero siguen dibujando y
leyendo sensores en la vieja (con los vasos y monedas de otra corrida) y fallan sin razon. Con
los archivos en una sola carpeta el orden alfabetico lo escondia; al pasar a subcarpetas por capa
(2026-09-28) `tests/app/` corre primero y aparecio. Solucion: al terminar cada archivo de prueba
se cierran los mundos de PyBullet que hayan quedado abiertos. No cambia lo que prueba ninguna
prueba: solo limpia entre un archivo y otro.
"""

import sys

import pytest

# Mas conexiones de las que cualquier prueba abre a la vez (pybullet no expone cuantas hay).
_MAX_CONEXIONES = 64


@pytest.fixture(autouse=True, scope="module")
def _cerrar_mundos_de_pybullet_al_terminar_el_archivo():
    yield
    p = sys.modules.get("pybullet")
    if p is None:   # el archivo ni siquiera uso PyBullet
        return
    for cliente in range(_MAX_CONEXIONES):
        if p.isConnected(cliente):
            p.disconnect(cliente)
