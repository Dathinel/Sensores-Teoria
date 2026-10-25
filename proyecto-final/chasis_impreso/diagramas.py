"""Dibujos de las conexiones del carro para el manual (usuario, 2026-10-24: "las conexiones tienen que tener
un modelo visual, con el nombre de los componentes y un ejemplo del cableado").

Por cada grupo de cables del carro (sim/conexiones.py, el mismo del firmware) sale img/manual/conex_<id>.png:
  - izquierda: el carro visto desde arriba, dibujado con las mallas reales de las piezas (en rayos X: lo que
    esta debajo se ve a traves), con cada componente con su nombre y el recorrido del mazo de cables
    (los de debajo del chasis suben por el pasacables mas cercano);
  - derecha: el esquema pin a pin, cada hilo con su color, de la placa que sale a la que llega.
Y img/manual/conex_general.png: todos los componentes del carro con su nombre.
Las posiciones salen del modelo (chasis.scad), no se escriben a mano. La usa manual.py.
"""
import re
import textwrap
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import numpy as np   # noqa: E402
from matplotlib.collections import PolyCollection   # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle   # noqa: E402
from matplotlib.path import Path as MPath   # noqa: E402
from matplotlib.patches import PathPatch   # noqa: E402

import exportar as ex   # noqa: E402

AQUI = ex.AQUI
sys.path.insert(0, str(AQUI.parent))
from sim import conexiones as cx   # noqa: E402

D_IMG = AQUI / "img" / "manual"
CLAROS = {cx.BLANCO, cx.AMARILLO}   # se dibujan con borde oscuro para que se vean sobre blanco


def medidas():
    """Variables del modelo que ubican cada componente."""
    with tempfile.TemporaryDirectory() as t:
        scad, eco = Path(t) / "v.scad", Path(t) / "v.echo"
        scad.write_text(f'include <{(AQUI / "chasis.scad").as_posix()}>\npieza = "nada";\n'
                        'echo(V = [gvs_centro, gvs, tb_centro, tb, x_ir + 2 - (pcb_perno_d + 0.6)/2, ir_placa, x_frente,'
                        ' hc, vl, x_eje, W, y_motor, tt_largo_caja, tt_espesor, x_bateria, celda_d, x_caja_int,'
                        ' x_ir_cuna + ir_cuna_dx/2, y_pared + e_pared, L, pasacables, x_eje - 8.5, W/2 - 30]);\n')
        subprocess.run([str(ex.OPENSCAD), "-o", str(eco), str(scad)], capture_output=True)
        txt = re.search(r"V = (\[.*\])", eco.read_text())[1]
    v = eval(txt)   # lista de numeros y listas que escribio OpenSCAD
    (gvs_c, gvs, tb_c, tb, x_ir, ir_placa, x_frente, hc, vl, x_eje, W, y_motor, tt_largo, tt_esp, x_bat, celda_d,
     x_caja, x_cuna, ye_cuna, L, pasacables, x_enc, y_enc) = v
    xc = (x_caja[0] + x_caja[1]) / 2
    # nombre: (centro x, centro y, largo x, ancho y, va debajo del chasis)
    disp = {
        "esp32_carro": (gvs_c[0], gvs_c[1], gvs[0], gvs[1], False),
        "tb6612": (tb_c[0], tb_c[1], tb, tb, False),
        "ir_linea": (x_ir, 0, ir_placa[0], ir_placa[1], True),
        "hcsr04": (x_frente + 7, 0, 8, hc[0], False),
        "vl53_frontal": (x_frente + 7, 0, 4, vl[0], False),   # encima del HC-SR04
        "motor_izq": (x_eje + tt_largo / 2, y_motor, tt_largo, tt_esp, True),
        "motor_der": (x_eje + tt_largo / 2, -y_motor, tt_largo, tt_esp, True),
        "enc_izq": (x_enc, y_enc, 32, 14, True),
        "enc_der": (x_enc, -y_enc, 32, 14, True),
        "bateria": (x_bat, 0, 2 * celda_d + 2, 65, False),
        "interruptor": (xc, W / 2 + 2, 13, 4, False),
        "ir_cuna": (x_cuna, ye_cuna + 4, 24, 3, False),
    }
    assert set(disp) == {d for d, x in cx.DISPOSITIVOS.items() if x["zona"] == "carro"}
    return disp, [tuple(p) for p in pasacables], (xc, -W / 2 - 2), L, W


def a_plano(x, y):
    """Carro (x adelante, y izquierda) -> dibujo visto desde arriba con el frente hacia arriba."""
    return -y, x


def fondo(ax):
    """Las piezas impresas armadas, vistas desde arriba en rayos X (lo de abajo se ve a traves)."""
    for stl in sorted((AQUI / "stl_sin_membrana" / "_ensamble").glob("*.stl")):
        if stl.stem == "componentes":
            continue
        tri = ex.leer_stl(stl)
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        tri = tri[n[:, 2] > 1e-6]    # solo las caras que miran hacia arriba
        pts = np.stack([-tri[:, :, 1], tri[:, :, 0]], axis=2)
        ax.add_collection(PolyCollection(pts, facecolors="#9aa3ad", edgecolors="none", alpha=0.10))


def caja_disp(ax, cx_, cy, sx, sy, debajo, resaltado):
    px, py = a_plano(cx_, cy)
    color = "#ff7a1a" if resaltado else "#6c7682"
    ax.add_patch(Rectangle((px - sy / 2, py - sx / 2), sy, sx, facecolor=color, alpha=0.8 if resaltado else 0.3,
                           edgecolor="#222", lw=1.2, ls="--" if debajo else "-", zorder=5))
    return px, py


def etiquetas(ax, items, x_borde):
    """items: [(px, py, texto)] -> nombres a los costados, sin encimarse, con su linea al componente."""
    for lado in (-1, 1):
        fila = sorted([i for i in items if (i[0] >= 0) == (lado > 0)], key=lambda i: -i[1])
        y_prev = None
        for px, py, texto in fila:
            ty = py if y_prev is None else min(py, y_prev - 11)
            y_prev = ty
            ax.annotate(texto, (px, py), (lado * x_borde, ty), fontsize=8, ha="left" if lado > 0 else "right",
                        va="center", zorder=9, bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#ff7a1a", lw=1),
                        arrowprops=dict(arrowstyle="-", color="#333", lw=0.8, shrinkA=0, shrinkB=0))


def mazo(ax, puntos, colores):
    """Recorrido de un mazo de hilos: una linea por hilo, juntas y en sus colores."""
    p = np.array([a_plano(*q) for q in puntos], float)
    n = len(colores)
    for k, c in enumerate(colores):
        off = (k - (n - 1) / 2) * 1.1
        q = p.copy()
        for i in range(len(q)):   # corrimiento perpendicular al tramo
            a, b = p[max(i - 1, 0)], p[min(i + 1, len(p) - 1)]
            t = (b - a) / (np.linalg.norm(b - a) + 1e-9)
            q[i] += off * np.array([-t[1], t[0]])
        if c in CLAROS:
            ax.plot(q[:, 0], q[:, 1], color="#333", lw=2.6, zorder=6, solid_capstyle="round")
        ax.plot(q[:, 0], q[:, 1], color=c, lw=1.6, zorder=7, solid_capstyle="round")


def vista(ax, grupo, xy, pasacables, fusible, L, W):
    ax.set_aspect("equal")
    ax.set_xlim(-W / 2 - 120, W / 2 + 120)
    ax.set_ylim(-L / 2 - 8, L / 2 + 22)
    ax.axis("off")
    fondo(ax)
    usados = {p.split(".")[0] for h in (grupo["hilos"] if grupo else []) for p in (h["de"], h["a"])}
    items = []
    for d in xy:
        res = d in usados or grupo is None
        px, py = caja_disp(ax, *xy[d], res)
        if res:
            items.append((px, py, cx.DISPOSITIVOS[d]["nombre"] + (" (debajo del chasis)" if xy[d][4] else "")))
    if "interruptor" in usados or grupo is None:   # el bloque «Interruptor + fusible» son 2 cajas
        px, py = caja_disp(ax, fusible[0], fusible[1], 4, 15, False, True)
        items.append((px, py, "Portafusible 3 A (mismo bloque que el interruptor)"))
    etiquetas(ax, items, W / 2 + 14)
    for p in pasacables:
        px, py = a_plano(*p)
        ax.add_patch(plt.Circle((px, py), 4, fc="white", ec="#555", lw=1.2, zorder=8))
    ax.annotate("adelante", (-W / 2 - 20, L / 2 + 14), ha="center", fontsize=9, color="#555")
    ax.annotate("", (-W / 2 - 20, L / 2 + 12), (-W / 2 - 20, L / 2 - 8), arrowprops=dict(arrowstyle="->", color="#555"))
    if not grupo:
        return
    # un mazo por par de placas (de -> a), con todos sus hilos
    pares = {}
    for h in grupo["hilos"]:
        pares.setdefault((h["de"].split(".")[0], h["a"].split(".")[0]), []).append(h["color"])
    for (a, b), cols in pares.items():
        pa, pb = xy[a][:2], xy[b][:2]
        ruta = [pa, pb]
        if (a, b) == ("bateria", "interruptor"):   # B+ entra al portafusible y de ahi cruza al interruptor
            ruta = [pa, fusible, pb]
        for extremo in (a, b):
            if xy[extremo][4]:   # debajo del chasis: sube por el pasacables que acorta el camino
                otro = pb if extremo == a else pa
                pas = min(pasacables, key=lambda p: np.hypot(p[0] - xy[extremo][0], p[1] - xy[extremo][1])
                          + np.hypot(p[0] - otro[0], p[1] - otro[1]))
                ruta.insert(1 if extremo == a else len(ruta) - 1, pas)
        mazo(ax, ruta, cols)


def nombre_pin(ref):
    dev, p = ref.split(".", 1)
    if dev == "esp32_carro":
        p = p.replace(".", " · ").replace("5V · 1", "5V").replace("GND · 1", "GND").replace("JACK", "JACK (plug DC)")
    if dev == "interruptor":
        p = {"1": "1 (entrada)", "2": "2 (salida)"}[p]
    return p


def esquema(ax, grupo):
    """Esquema pin a pin: placas en columnas (de izquierda a derecha, en el sentido de los hilos)."""
    ax.axis("off")
    devs, pines = [], {}
    for h in grupo["hilos"]:
        for ref in (h["de"], h["a"]):
            d = ref.split(".")[0]
            if d not in devs:
                devs.append(d)
            pines.setdefault(d, [])
            if ref not in pines[d]:
                pines[d].append(ref)
    nivel = {d: 0 for d in devs}
    for _ in devs:   # nivel = camino mas largo desde una placa que solo manda
        for h in grupo["hilos"]:
            a, b = h["de"].split(".")[0], h["a"].split(".")[0]
            nivel[b] = max(nivel[b], nivel[a] + 1)
    cols = max(nivel.values()) + 1
    fila, ancho_caja = 1.0, 4.4
    xs = {k: k * (ancho_caja + 4.2) for k in range(cols)}
    pos = {}
    for k in range(cols):
        y = 0.0
        for d in [d for d in devs if nivel[d] == k]:
            n = len(pines[d])
            top = y
            ax.add_patch(FancyBboxPatch((xs[k], -top - n * fila - 1.5), ancho_caja, n * fila + 1.5,
                                        boxstyle="round,pad=0.05,rounding_size=0.25", fc="#f3f5f8", ec="#1f3a5f", lw=1.3))
            ax.text(xs[k] + ancho_caja / 2, -top - 0.7, textwrap.fill(cx.DISPOSITIVOS[d]["nombre"], 20),
                    ha="center", va="center", fontsize=8, weight="bold", color="#1f3a5f", linespacing=1.0)
            for i, ref in enumerate(pines[d]):
                yy = -top - 1.5 - (i + 0.5) * fila
                pos[ref] = (xs[k], xs[k] + ancho_caja, yy)
                ax.text(xs[k] + ancho_caja / 2, yy, nombre_pin(ref), ha="center", va="center", fontsize=8.2,
                        family="monospace")
            y = top + n * fila + 1.5 + 0.8
    for h in grupo["hilos"]:
        x0 = pos[h["de"]][1]
        y0 = pos[h["de"]][2]
        x1, y1 = pos[h["a"]][0], pos[h["a"]][2]
        m = (x0 + x1) / 2
        camino = MPath([(x0, y0), (m, y0), (m, y1), (x1, y1)], [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4])
        if h["color"] in CLAROS:
            ax.add_patch(PathPatch(camino, fc="none", ec="#333", lw=3.4))
        ax.add_patch(PathPatch(camino, fc="none", ec=h["color"], lw=2.2))
        ax.plot([x0, x1], [y0, y1], "o", ms=3.5, color="#222")
    alto = max(-p[2] for p in pos.values()) + 1.5
    ax.set_xlim(-0.3, xs[cols - 1] + ancho_caja + 0.3)
    ax.set_ylim(-alto, 0.3)


def dibujar():
    D_IMG.mkdir(parents=True, exist_ok=True)
    xy, pasacables, fusible, L, W = medidas()
    fig, ax = plt.subplots(figsize=(11, 8))
    vista(ax, None, xy, pasacables, fusible, L, W)
    ax.set_title("Componentes del carro, vistos desde arriba (lo punteado va debajo del chasis; círculos: pasacables)",
                 fontsize=10)
    fig.savefig(D_IMG / "conex_general.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    grupos = [c for c in cx.CABLES if c["tipo"] == "carro"]
    for g in grupos:
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(17, 7), gridspec_kw=dict(width_ratios=[1.25, 1]))
        vista(a1, g, xy, pasacables, fusible, L, W)
        a1.set_title("Dónde va y por dónde pasa el mazo", fontsize=10)
        esquema(a2, g)
        a2.set_title("Pin a pin", fontsize=10)
        fig.savefig(D_IMG / f"conex_{g['id']}.png", dpi=130, bbox_inches="tight")
        plt.close(fig)
    print(f"diagramas: conex_general + {len(grupos)} grupos en {D_IMG}")
    return [g["id"] for g in grupos]


if __name__ == "__main__":
    dibujar()
