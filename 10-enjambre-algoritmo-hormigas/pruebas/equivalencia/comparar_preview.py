"""
comparar_preview.py - Comprueba que el ACO de preview.html (JavaScript) es el mismo de aco.py.

Genera con aco.simular_enjambre la referencia de 24 casos (maze.json y laberintos/abierto.json,
semillas 1, 2 y 12345, sin caidas y con el nodo 2 apagado desde la iteracion 10, con las dos
reglas de deposito), la guarda en un
json temporal y llama a comparar_preview.mjs con node, que corre el nucleo JS sacado del propio
HTML y compara todo con igualdad exacta.

Uso:
    entorno\\Scripts\\python pruebas\\equivalencia\\comparar_preview.py     (necesita node)
"""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
TEMA = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, TEMA)

import aco  # noqa: E402


def sin_inf(x):
    return None if isinstance(x, float) and math.isinf(x) else x


def referencia():
    out = {}
    for maze in ("maze.json", "laberintos/abierto.json"):
        lab = aco.cargar_laberinto(os.path.join(TEMA, maze))
        for semilla in (1, 2, 12345):
            for caidas in (None, {2: 10}):
              for deposito in ("mejor", "todas"):
                r = aco.simular_enjambre(lab, aco.Parametros(semilla=semilla, deposito=deposito), caidas=caidas)
                out[f"{maze}|{semilla}|{json.dumps(caidas)}|{deposito}"] = {
                    "crc": lab.crc(),
                    "historial": [{"it": h["iteracion"],
                                   "por_nodo": {str(n): [d["mejor_camino"], sin_inf(d["mejor_longitud"]),
                                                         d["exitosas"], d["descartadas"]]
                                                for n, d in h["por_nodo"].items()},
                                   "tau": h["tau"]} for h in r["historial"]],
                    "tau_final": {str(n): t for n, t in r["tau_final"].items()},
                    "codicioso": r["camino_codicioso"], "convergio": r["convergio"],
                    "primera": r["iteracion_primer_optimo"],
                }
    return out


def main():
    node = shutil.which("node")
    if not node:
        print("No se encontro node en el PATH.")
        sys.exit(2)
    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "ref.json")
        with open(ruta, "w") as f:
            json.dump(referencia(), f)
        p = subprocess.run([node, os.path.join(AQUI, "comparar_preview.mjs"), ruta])
    sys.exit(p.returncode)


if __name__ == "__main__":
    main()
