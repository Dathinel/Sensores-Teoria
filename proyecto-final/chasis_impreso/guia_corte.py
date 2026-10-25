"""Guia de que abrir despues de imprimir: la membrana de la primera capa (primera_capa.scad) tapa
todos los agujeros de la cara que va contra la cama. Por cada tanda dibuja esa cara VISTA DESDE
ABAJO (como se ve al voltear la pieza) y marca en rojo lo que hay que abrir y con que; los
vaciados de aligeramiento pueden quedar tapados.

Uso: python guia_corte.py            -> img/corte_tanda1_chasis.png, ...
     python guia_corte.py 1          -> solo la tanda 1
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon
from matplotlib.path import Path as Path_

import exportar as ex

ABRIR_MAX_MM2 = 100      # agujeros mas chicos que esto son funcionales; los mas grandes, aligeramientos
ABIERTO_MIN_D = 40       # huecos con diametro equivalente mayor ya quedan abiertos (r_abierto de primera_capa.scad)
TODO_SE_ABRE = {"caja_interruptor", "caja_fusible"}   # su ventana y su agujero son grandes pero hacen falta
VENTANA_LARGA = {"pared_cuna_der"}                     # la ventana de la lengueta (36 x 9) es larga y hace falta


def poligonos_svg(scad_txt, tmp):
    scad, svg = tmp / "s.scad", tmp / "s.svg"
    scad.write_text(scad_txt)
    subprocess.run([str(ex.OPENSCAD), "-o", str(svg), str(scad)], capture_output=True)
    if not svg.exists():
        return []
    txt = svg.read_text().replace("\n", " ")
    svg.unlink()
    out = []
    for sub in re.findall(r"M([^z]*)z", txt):
        pts = np.array([list(map(float, p.split(","))) for p in re.findall(r"-?[\d.]+,-?[\d.]+", sub)])
        if len(pts) >= 3:
            out.append(np.c_[-pts[:, 0], -pts[:, 1]])   # SVG invierte y; -x = visto desde abajo
    return out


def area(p):
    x, y = p[:, 0], p[:, 1]
    return abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2


def tipo(p, nom=""):
    a = area(p)
    w, h = np.ptp(p, axis=0)
    d = 2 * np.sqrt(a / np.pi)
    perimetro = np.linalg.norm(np.diff(np.vstack([p, p[:1]]), axis=0), axis=1).sum()
    redondo = 4 * np.pi * a / perimetro ** 2 > 0.85
    rectangulo = a / (w * h) > 0.9
    if d > ABIERTO_MIN_D:
        return "abierto", None
    alargado = nom in VENTANA_LARGA and rectangulo and max(w, h) >= 3 * min(w, h)
    if nom in TODO_SE_ABRE:
        return ("ranura", "bisturí") if rectangulo else ("grande", f"broca {d:.0f} mm")
    # lo funcional es redondo (agujeros) o rectangular (ranuras); lo irregular son pedazos de vaciado
    if (a > ABRIR_MAX_MM2 and not alargado) or a < 3 or not (redondo or rectangulo):
        return "tapado", None
    if rectangulo and not redondo:
        return "ranura", "bisturí"
    if d > 6:
        return "grande", f"broca {d:.0f} mm"
    if d > 4.2:
        return "remache", "broca 4,5 mm"
    if d > 3.3:
        return "perno", "broca 4 mm"
    return "chico", "broca 3 mm o punzón"


COLOR = {"remache": "#d62728", "perno": "#ff7f0e", "grande": "#9467bd", "ranura": "#1f77b4", "chico": "#8c564b"}
NOMBRE = {"remache": "remache (broca 4,5 mm)", "perno": "perno a presión (broca 4 mm)", "grande": "pasacables / agujero grande",
          "ranura": "ranura o ventana (bisturí)", "chico": "agujero chico (broca 3 mm o punzón)"}


def geometria(nom, tmp):
    """Contorno y huecos de la cara que va contra la cama (sin la membrana), visto desde abajo."""
    crudo = tmp / "crudo.stl"
    ex.openscad(crudo, nom)
    tri = ex.leer_stl(crudo)
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    ex.escribir_stl(crudo, tri - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]))
    seccion = f'projection(cut = true) translate([0, 0, -0.05]) import("{crudo.as_posix()}");'
    contorno = poligonos_svg(f"fill() {seccion}", tmp)
    huecos = poligonos_svg(f"difference() {{ fill() {seccion} {seccion} }}", tmp)
    # una torreta maciza dentro de un vaciado sale como otro contorno: es isla, no agujero
    caminos = [Path_(p) for p in huecos]
    huecos = [p for i, p in enumerate(huecos)
              if not any(j != i and area(huecos[j]) > area(p) and caminos[j].contains_point(p.mean(axis=0)) for j in range(len(huecos)))]
    return contorno, huecos


def dibujar(eje, nom, contorno, huecos):
    for p in contorno:
        eje.add_patch(Polygon(p, closed=True, fc="#e8e8e8", ec="#555", lw=1))
    cuenta = {}
    for p in huecos:
        t_, _ = tipo(p, nom)
        if t_ == "abierto":
            eje.add_patch(Polygon(p, closed=True, fc="white", ec="#555", lw=1))
        elif t_ == "tapado":
            eje.add_patch(Polygon(p, closed=True, fc="#d0d0d0", ec="#999", lw=0.6, hatch="///"))
        else:
            eje.add_patch(Polygon(p, closed=True, fc=COLOR[t_], ec=COLOR[t_], lw=1.2))
            eje.plot(*p.mean(axis=0), "o", ms=11, mfc="none", mec=COLOR[t_], mew=1.5)
            cuenta[t_] = cuenta.get(t_, 0) + 1
    todo = np.vstack(contorno) if contorno else np.zeros((1, 2))
    eje.set_xlim(todo[:, 0].min() - 5, todo[:, 0].max() + 5)
    eje.set_ylim(todo[:, 1].min() - 5, todo[:, 1].max() + 5)
    eje.set_aspect("equal")
    eje.set_xticks([]); eje.set_yticks([])
    cant = ex.PIEZAS[nom][0]
    resumen = ", ".join(f"{n} {NOMBRE[k].split(' (')[0]}" for k, n in sorted(cuenta.items())) or "nada que abrir"
    eje.set_title(f"{nom}{f' (x{cant})' if cant > 1 else ''}" + chr(10) + resumen, fontsize=11)
    return cuenta


def guardar(fig, salida, titulo):
    marcas = [plt.Line2D([], [], marker="s", ls="", color=c, ms=10, label=NOMBRE[k]) for k, c in COLOR.items()]
    marcas.append(plt.Line2D([], [], marker="s", ls="", color="#d0d0d0", ms=10, label="aligeramiento: puede quedar tapado"))
    fig.legend(handles=marcas, loc="lower center", ncol=3, fontsize=10, frameon=False)
    fig.suptitle(titulo, fontsize=13)
    fig.tight_layout(rect=(0, 0.1, 1, 0.95))
    salida.parent.mkdir(parents=True, exist_ok=True)
    # Windows a veces no deja sobrescribir una imagen abierta en un visor: se escribe aparte y se reemplaza
    temporal = salida.with_name(salida.stem + "_nuevo.png")
    fig.savefig(temporal, dpi=110)
    temporal.replace(salida)
    plt.close(fig)


def guia(tanda):
    """img/corte_<tanda>.png (toda la tanda) e img/corte/<pieza>.png (una por pieza, para el manual)."""
    nombres = [n for n, v in ex.PIEZAS.items() if v[1] == tanda and not n.startswith(("remache", "pasador"))]
    if not nombres:
        return
    vista = "cara que estuvo contra la cama, vista desde abajo (pieza volteada)"
    with tempfile.TemporaryDirectory() as t:
        geo = {n: geometria(n, Path(t)) for n in nombres}
    fig, ejes = plt.subplots(1, len(nombres), figsize=(6.5 * len(nombres), 6.2), squeeze=False)
    for eje, nom in zip(ejes[0], nombres):
        dibujar(eje, nom, *geo[nom])
    guardar(fig, ex.AQUI / "img" / f"corte_{ex.NOMBRE_TANDA[tanda]}.png", f"{ex.NOMBRE_TANDA[tanda]}: {vista}")
    for nom in nombres:
        fig, eje = plt.subplots(figsize=(11, 7.5))
        salida = ex.AQUI / "img" / "corte" / f"{nom}.png"
        if dibujar(eje, nom, *geo[nom]):
            guardar(fig, salida, vista)
        else:   # nada que abrir: no va al manual
            plt.close(fig)
            salida.unlink(missing_ok=True)
    print("guia:", ex.NOMBRE_TANDA[tanda])


if __name__ == "__main__":
    for t in ([int(a) for a in sys.argv[1:]] or sorted(ex.NOMBRE_TANDA)):
        guia(t)
