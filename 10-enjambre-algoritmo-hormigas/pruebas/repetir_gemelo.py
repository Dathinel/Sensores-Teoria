"""
repetir_gemelo.py - Prueba 15: correr el gemelo varias veces con la semilla fija y comparar.

Cada corrida escribe en su propia carpeta (pruebas/resultados/repeticiones/<modo>_<i>/) y al
final se compara la ruta de cada nodo, la longitud y la feromona final de todas las corridas.
Si todas son iguales, el gemelo es reproducible: misma semilla, mismo resultado.

Uso:
    entorno\\Scripts\\python pruebas\\repetir_gemelo.py                 (nativo, 10 corridas)
    entorno\\Scripts\\python pruebas\\repetir_gemelo.py --docker        (docker compose run, 10 corridas)
    entorno\\Scripts\\python pruebas\\repetir_gemelo.py --n 3 --paralelo 3

En modo nativo se pueden correr varias a la vez (--paralelo); con Docker van de a una, porque
todas usan la misma carpeta montada (resultados/) y se copian antes de la siguiente.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
TEMA = os.path.dirname(AQUI)
SALIDA = os.path.join(AQUI, "resultados", "repeticiones")


def corrida_nativa(i, extra):
    carpeta = os.path.join(SALIDA, f"nativo_{i:02d}")
    os.makedirs(carpeta, exist_ok=True)
    entorno = dict(os.environ, RESULTADOS=carpeta, PYTHONIOENCODING="utf-8")
    t0 = time.time()
    p = subprocess.run([sys.executable, os.path.join(TEMA, "gemelo_digital.py"), "--modo", "sin-hardware",
                        *extra], cwd=TEMA, env=entorno, capture_output=True, text=True)
    return i, p.returncode, time.time() - t0, carpeta, p.stdout[-400:] + p.stderr[-400:]


def corrida_docker(i, extra):
    carpeta = os.path.join(SALIDA, f"docker_{i:02d}")
    t0 = time.time()
    p = subprocess.run(["docker", "compose", "run", "--rm", "simulacion", "--modo", "sin-hardware", *extra],
                       cwd=TEMA, capture_output=True, text=True)
    # El contenedor escribe en resultados/ (volumen); se copia el resumen a la carpeta de la corrida.
    os.makedirs(carpeta, exist_ok=True)
    for nombre in ("resumen_sin-hardware.json", "ruta_final_sin-hardware.png"):
        origen = os.path.join(TEMA, "resultados", nombre)
        if os.path.exists(origen):
            shutil.copy(origen, carpeta)
    return i, p.returncode, time.time() - t0, carpeta, p.stdout[-400:] + p.stderr[-400:]


def huella(carpeta):
    with open(os.path.join(carpeta, "resumen_sin-hardware.json"), encoding="utf-8") as f:
        r = json.load(f)
    return {"rutas": {n: d["mejor_ruta"] for n, d in r["por_nodo"].items()},
            "longitudes": {n: d["longitud_m"] for n, d in r["por_nodo"].items()},
            "feromona_final": r.get("feromona_final"),
            "convergio": r.get("convergio")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--paralelo", type=int, default=4)
    ap.add_argument("--docker", action="store_true")
    ap.add_argument("--semilla", type=int, default=12345)
    a = ap.parse_args()
    extra = ["--semilla", str(a.semilla)]
    os.makedirs(SALIDA, exist_ok=True)
    t0 = time.time()
    if a.docker:
        res = [corrida_docker(i, extra) for i in range(1, a.n + 1)]
    else:
        with ThreadPoolExecutor(max_workers=a.paralelo) as ex:
            res = list(ex.map(lambda i: corrida_nativa(i, extra), range(1, a.n + 1)))
    filas, huellas = [], []
    for i, rc, dur, carpeta, cola in res:
        h = huella(carpeta) if rc == 0 else None
        huellas.append(h)
        filas.append({"corrida": i, "codigo_salida": rc, "duracion_s": round(dur, 1),
                      "rutas": h["rutas"] if h else None, "convergio": h["convergio"] if h else None,
                      "error": None if rc == 0 else cola})
        print(f"corrida {i:2d}: salida {rc}, {dur:6.1f} s, rutas {h['rutas'] if h else '-'}")
    ok = all(h is not None for h in huellas) and all(h == huellas[0] for h in huellas)
    informe = {"modo": "docker" if a.docker else "nativo", "semilla": a.semilla, "n": a.n,
               "todas_iguales": ok, "duracion_total_s": round(time.time() - t0, 1), "corridas": filas}
    nombre = f"repetir_gemelo_{'docker' if a.docker else 'nativo'}.json"
    with open(os.path.join(AQUI, "resultados", nombre), "w", encoding="utf-8") as f:
        json.dump(informe, f, indent=1, ensure_ascii=False)
    print(("\nLAS %d CORRIDAS DAN EXACTAMENTE LO MISMO" % a.n) if ok else "\nHAY DIFERENCIAS ENTRE CORRIDAS")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
