"""
generar_maze_h.py - Convierte maze.json en firmware/esp32_aco_nodo/maze_data.h.

Por que existe: el mapa se escribe UNA sola vez, en maze.json, y de ahi lo toman los dos mundos.
La simulacion (Python) lo lee directo. El ESP32 no tiene donde leer un archivo del PC, asi que
este script lo traduce a un encabezado de C++ con las mismas aristas, en el mismo orden, que
arma aco.cargar_laberinto. Ademas guarda el CRC del mapa: el ESP32 lo manda en cada HELLO y el
gemelo digital lo compara con el de su maze.json; si no coinciden, avisa que el ESP32 se flasheo
con otro mapa.

Uso (cada vez que se cambie maze.json, antes de compilar el firmware):
    entorno\\Scripts\\python generar_maze_h.py
    entorno\\Scripts\\python generar_maze_h.py --maze laberintos/dos_caminos.json
"""

import argparse
import os

import aco

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "firmware", "esp32_aco_nodo", "maze_data.h")


def generar(ruta_maze: str, salida: str = SALIDA) -> str:
    lab = aco.cargar_laberinto(ruta_maze)
    n_celdas = lab.columnas * lab.filas
    lineas = [
        "// maze_data.h - GENERADO por generar_maze_h.py a partir de "
        f"{os.path.basename(ruta_maze)}. No editar a mano:",
        "// cambiar el .json y volver a correr el script.",
        "#pragma once",
        "#include <stdint.h>",
        "",
        f'#define MAZE_NOMBRE "{lab.nombre}"',
        f"#define MAZE_COLUMNAS {lab.columnas}",
        f"#define MAZE_FILAS {lab.filas}",
        f"#define MAZE_N_CELDAS {n_celdas}",
        f"#define MAZE_N_ARISTAS {len(lab.aristas)}",
        f"#define MAZE_INICIO {lab.inicio}",
        f"#define MAZE_META {lab.meta}",
        f"#define MAZE_TAM_CELDA_M {lab.tam_celda:.3f}",
        f"#define MAZE_CRC 0x{lab.crc():08X}u",
        "",
        "// Aristas (u, v) con u < v en el orden canonico de aco.py.",
        "static const int16_t MAZE_ARISTAS[MAZE_N_ARISTAS][2] = {",
    ]
    lineas += [f"  {{{u}, {v}}}," for u, v in lab.aristas]
    lineas += ["};", "", "// Longitud real de cada arista en metros (distancia entre centros de celdas).",
               "static const double MAZE_LONGITUD[MAZE_N_ARISTAS] = {"]
    # repr() da el double exacto (17 cifras si hace falta), el mismo valor que usa Python.
    lineas += [f"  {repr(d)}," for d in lab.longitud]
    lineas += ["};", "", "// Vecinos de cada celda en orden +x, +y, -x, -y: {celda vecina, indice de arista}.",
               "static const uint8_t MAZE_N_VECINOS[MAZE_N_CELDAS] = {"]
    lineas.append("  " + ", ".join(str(len(v)) for v in lab.vecinos))
    lineas += ["};", "static const int16_t MAZE_VECINOS[MAZE_N_CELDAS][4][2] = {"]
    for u, vs in enumerate(lab.vecinos):
        celdas = [f"{{{v}, {e}}}" for v, e in vs] + ["{-1, -1}"] * (4 - len(vs))
        lineas.append(f"  {{{', '.join(celdas)}}},  // celda {u} = {lab.celda(u)}")
    lineas.append("};")
    texto = "\n".join(lineas) + "\n"
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    with open(salida, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    return f"{salida}  ({len(lab.aristas)} aristas, CRC {lab.crc():08X})"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--maze", default=aco.MAZE_POR_DEFECTO)
    ap.add_argument("--salida", default=SALIDA)
    a = ap.parse_args()
    print("Generado:", generar(a.maze, a.salida))
