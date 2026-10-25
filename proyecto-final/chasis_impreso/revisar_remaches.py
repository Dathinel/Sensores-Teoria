"""Mide en el carro armado lo que junta de verdad cada remache (usuario, 2026-10-24: el del porta baterias
no pasaba y 2 de los rodillos no agarraban nada; el agarre se habia sacado de formulas, nunca del modelo).

Por cada remache de REM_LISTA (manual.scad) corta todas las piezas impresas con un tubo alrededor de su eje
y mide el tramo de material continuo que termina en la cara donde sale la una. Ese largo es el agarre real.
Uso: python revisar_remaches.py   (sale con error si algun remache no coincide)
"""
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import exportar as ex

AQUI = ex.AQUI
HUECO = 0.4      # dos piezas que se tocan quedan a menos de esto
TOLERA = 0.3     # diferencia aceptable entre el agarre del remache y lo que junta
# Casos revisados a mano que no son error (remache, paso): por que
CONOCIDOS = {
    ("remache_9_5", 3): "a presion: el agujero de la pared es ciego y la una no sale (va con una gota de pegante)",
    ("remache_10_5", 8): "lo de arriba es la pared de la caja al lado de la cabeza: la cabeza va girada a lo largo de la pared",
    # carro armado el 2026-10-24: estos no agarraban y se pegaron con pegante instantaneo
    ("remache_10_5", 2): "NO PASA: el divisor del porta mide 10,4 + 8 del chasis (haria falta uno de 18,4). En el carro: PEGADO",
    ("remache_37", 6): "el bloque solo cubre el agujero de atras; el de adelante cae fuera y sobra. En el carro: PEGADO",
}


def lista():
    with tempfile.TemporaryDirectory() as t:
        scad, eco = Path(t) / "l.scad", Path(t) / "l.echo"
        scad.write_text(f'include <{(AQUI / "manual.scad").as_posix()}>\nmodo = "nada";\n'
                        'for (r = REM_LISTA) echo(REM = r, AGARRE = rem_agarre(r[1]));\n')
        subprocess.run([str(ex.OPENSCAD), "-o", str(eco), str(scad)], capture_output=True)
        txt = eco.read_text()
    filas = []
    for m in re.finditer(r'REM = \[(\d+), "(\w+)", \[([^\]]+)\], \[([^\]]+)\]\], AGARRE = ([\d.]+)', txt):
        filas.append((int(m[1]), m[2], np.array([float(v) for v in m[3].split(",")]),
                      np.array([float(v) for v in m[4].split(",")]), float(m[5])))
    assert filas, "REM_LISTA no salio en el eco de OpenSCAD"
    return filas


def tramos(tri, p, d):
    """Intervalos (a lo largo del eje, desde la cabeza) ocupados por material, con las caras paralelas al eje."""
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    t = (tri - p) @ d
    par = np.abs(n @ d) < 0.2
    iv = sorted(zip(t[par].min(1), t[par].max(1)))
    juntos = []
    for a, b in iv:
        if juntos and a <= juntos[-1][1] + HUECO:
            juntos[-1][1] = max(juntos[-1][1], b)
        else:
            juntos.append([a, b])
    return juntos


def medir(i, r, tmp):
    paso, nombre, p, d, agarre = r
    stl = tmp / f"r{i}.stl"
    scad = tmp / f"r{i}.scad"
    scad.write_text(f'include <{(AQUI / "manual.scad").as_posix()}>\nmodo = "nada";\n'
                    f'intersection() {{ union() for (n = EN_EL_CARRO) instancias(n);\n'
                    f'  en_eje(REM_LISTA[{i}]) translate([0, 0, -60]) difference() {{ cylinder(r = 2.9, h = 120, $fn = 24);'
                    f' translate([0, 0, -1]) cylinder(r = 2.4, h = 122, $fn = 24); }} }}\n')
    subprocess.run([str(ex.OPENSCAD), "-o", str(stl), str(scad)], capture_output=True)
    if not stl.exists() or stl.stat().st_size < 200:
        return i, None
    sale = agarre   # la cara de la una, donde se diseno
    for a, b in tramos(ex.leer_stl(stl), p, d):
        if a - 0.5 <= sale <= b + 0.5:
            return i, (a, b)
    return i, None


def main():
    filas = lista()
    with tempfile.TemporaryDirectory() as t, ThreadPoolExecutor(6) as ej:
        res = dict(ej.map(lambda a: medir(*a, Path(t)), enumerate(filas)))
    malos = 0
    print(f"{'#':>2} paso {'remache':<13} {'donde (x, y, z)':<22} agarre  junta real")
    for i, (paso, nombre, p, d, agarre) in enumerate(filas):
        iv = res[i]
        if iv is None:
            estado, real = "NO AGARRA NADA", "-"
        else:
            real = f"{iv[1] - iv[0]:.1f} (de {iv[0]:.1f} a {iv[1]:.1f})"
            estado = "ok" if abs(iv[0]) <= TOLERA and abs(iv[1] - agarre) <= TOLERA else "NO COINCIDE"
        if estado != "ok" and (nombre, paso) in CONOCIDOS:
            estado = "ok, " + CONOCIDOS[(nombre, paso)]
        malos += estado != "ok"
        print(f"{i:>2} {paso:>4} {nombre:<13} {str(np.round(p, 1)):<22} {agarre:6.2f}  {real}  {estado}")
    sys.exit(1 if malos else 0)


if __name__ == "__main__":
    main()
