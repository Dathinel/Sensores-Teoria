"""
comparar_equivalencia.py - Comprueba que el ACO del firmware (C++) y el de aco.py son el mismo.

Para cada laberinto y cada semilla:
  1. genera el maze_data.h de ese laberinto en una carpeta temporal (generar_maze_h.py),
  2. compila prueba_equivalencia.cpp + firmware/esp32_aco_nodo/aco_core.h con g++ del PC,
  3. corre el ejecutable y corre aco.simular_enjambre con los mismos parametros,
  4. compara linea por linea: mejor ruta y longitud de cada nodo en cada iteracion, y la
     feromona final de cada nodo con igualdad EXACTA (17 cifras).

No es el ESP32 (es g++ en x86), pero es el mismo codigo fuente del firmware: si aqui coincide,
la unica diferencia posible en la placa es la libreria matematica (pow) en el ultimo bit.

Uso:
    entorno\\Scripts\\python pruebas\\equivalencia\\comparar_equivalencia.py
    (necesita g++ en el PATH o en D:\\cosas uni\\Micros\\instalados\\w64devkit\\bin)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
TEMA = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, TEMA)

import aco  # noqa: E402
import generar_maze_h  # noqa: E402

GXX_RESPALDO = r"D:\cosas uni\Micros\instalados\w64devkit\bin\g++.exe"
FIRMWARE = os.path.join(TEMA, "firmware", "esp32_aco_nodo")


def buscar_gxx():
    return shutil.which("g++") or (GXX_RESPALDO if os.path.exists(GXX_RESPALDO) else None)


def salida_python(lab, params):
    r = aco.simular_enjambre(lab, params)
    lineas = []
    for info in r["historial"]:
        k = info["iteracion"]
        for n in (1, 2, 3):
            d = info["por_nodo"][n]
            L = d["mejor_longitud"]
            cam = "-".join(str(c) for c in d["mejor_camino"]) if d["mejor_camino"] else ""
            lineas.append(f"IT {k} N {n} EX {d['exitosas']} DES {d['descartadas']} "
                          f"L {format(L if L != float('inf') else -1.0, '.17g')} C {cam}")
    for n in (1, 2, 3):
        lineas.append("TAU %d %s" % (n, " ".join(format(t, ".17g") for t in r["tau_final"][n])))
    return lineas


def main():
    gxx = buscar_gxx()
    if not gxx:
        print("No se encontro g++. Instalar w64devkit en D:\\cosas uni\\Micros\\instalados.")
        sys.exit(2)
    casos = [
        ("maze.json", [1, 2, 3, 7, 12345]),
        ("laberintos/abierto.json", [1, 2, 12345]),
        ("laberintos/dos_caminos.json", [1, 12345]),
        ("laberintos/unico_camino.json", [1, 12345]),
    ]
    # Las dos reglas de deposito: solo la mejor hormiga (por defecto) y todas (Ant System).
    variantes = [aco.Parametros(), aco.Parametros(alfa=2.0, beta=1.0, rho=0.1),
                 aco.Parametros(deposito="todas"),
                 aco.Parametros(alfa=2.0, beta=1.0, rho=0.1, deposito="todas")]
    resultados, todo_bien = [], True
    with tempfile.TemporaryDirectory() as tmp:
        for maze, semillas in casos:
            ruta = os.path.join(TEMA, maze)
            generar_maze_h.generar(ruta, os.path.join(tmp, "maze_data.h"))
            exe = os.path.join(tmp, "equiv.exe")
            # Se copia aco_core.h a la carpeta temporal para que tome ESE maze_data.h y no el
            # que esta junto al firmware.
            shutil.copy(os.path.join(FIRMWARE, "aco_core.h"), tmp)
            subprocess.run([gxx, "-O2", "-std=c++17", "-I", tmp, "-o", exe,
                            os.path.join(AQUI, "prueba_equivalencia.cpp")], check=True)
            lab = aco.cargar_laberinto(ruta)
            for params0 in variantes:
                for s in semillas:
                    params = aco.Parametros(**{**params0.__dict__, "semilla": s})
                    args = [exe, str(s), repr(params.alfa), repr(params.beta), repr(params.rho),
                            repr(params.q), str(params.hormigas), str(params.iteraciones),
                            repr(params.tau0), "1" if params.deposito == "mejor" else "0"]
                    c = subprocess.run(args, capture_output=True, text=True, check=True)
                    lc = c.stdout.strip().splitlines()
                    lp = salida_python(lab, params)
                    difs = [i for i, (a, b) in enumerate(zip(lc, lp)) if a != b]
                    iguales = not difs and len(lc) == len(lp)
                    todo_bien &= iguales
                    resultados.append({"laberinto": maze, "semilla": s,
                                       "alfa": params.alfa, "beta": params.beta, "rho": params.rho,
                                       "deposito": params.deposito,
                                       "lineas": len(lp), "iguales": iguales,
                                       "primera_diferencia": None if iguales else
                                       {"cpp": lc[difs[0]] if difs else None,
                                        "py": lp[difs[0]] if difs else None}})
                    print(f"{maze:30s} semilla {s:6d} alfa {params.alfa} beta {params.beta} "
                          f"rho {params.rho} deposito {params.deposito}: {'IGUALES' if iguales else 'DISTINTOS'} "
                          f"({len(lp)} lineas)")
    os.makedirs(os.path.join(TEMA, "pruebas", "resultados"), exist_ok=True)
    with open(os.path.join(TEMA, "pruebas", "resultados", "equivalencia_cpp_python.json"), "w",
              encoding="utf-8") as f:
        json.dump({"compilador": gxx, "casos": resultados, "todo_igual": todo_bien}, f, indent=2)
    print("\nTODOS IGUALES" if todo_bien else "\nHAY DIFERENCIAS")
    sys.exit(0 if todo_bien else 1)


if __name__ == "__main__":
    main()
