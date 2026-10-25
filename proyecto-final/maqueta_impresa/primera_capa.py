"""Primera capa de cada pieza (usuario, 2026-10-24: se levanta y se despega en los circulos chicos; la membrana NO es
solucion). Mide la cara que apoya en la cama de cada STL de stl/: cuantas islas (contornos sueltos: cada una es un
viaje con retraccion), cuantos agujeros chicos (cada circulo chico es un bucle que al cerrarse con retraccion y
limpieza arranca el material), cuantas ranuras de aire o tiras de material de menos de 1,2 mm (igual de malas), el
agujero mas chico y el ancho minimo de material. Con eso se decide pieza por
pieza: girarla (otra cara abajo), sacar los agujeros de esa cara o reforzar la base.

Uso: python primera_capa.py [stl/...]  -> tabla ordenada de peor a mejor y primera_capa.json
"""
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from scipy import ndimage

import revisar as R

AQUI = R.AQUI
D_CHICO = 8.0      # mm: un agujero mas chico que esto es un bucle corto (el que se levanta); diametro por area o 4 A / P
CHICOS_MAX = 2     # revisar.py acepta hasta 2 entre agujeros chicos y angostas (un riel con remaches por las 4 caras no baja de 1 o 2)
# Ranuras de aire y tiras de material mas angostas que ANCHO_MIN en la primera capa (2026-10-25): sus puntas son tan
# cerradas como las de un agujero chico. Se miden sobre la seccion rasterizada a PX (los offset de OpenSCAD dejaban
# astillas a lo largo de cada circulo); menos de A_ANGOSTA es la punta de una esquina de menos de ~45 grados o ruido.
ANCHO_MIN, PX, A_ANGOSTA = 1.2, 0.1, 0.5
Z_CORTE = 0.15     # mitad de la primera capa (0,2 con brim; la capa 1 real va de 0 a 0,3 en el perfil)
# Brim (mm) con que se imprime cada pieza: el del perfil maqueta, y 10 en las paredes altas que van de pie sobre un canto
# (acostadas meterian de 5 a 9 agujeros chicos en la cama). exportar.py lo escribe por objeto en el 3MF.
BRIM_DEF = 5.0
BRIM_OBJETO = {n: 10.0 for n in ("vas_lat_s_b", "vas_lat_n_a", "vas_lat_n_b", "vas_placa_motor", "mon_e4",
                                 "can_prisionero_c1", "can_prisionero_c2", "can_prisionero_c3", "can_prisionero_c4")}
BRIM_OBJETO["vas_lat_s_a"] = 6.0     # mide 236: con 10 no entra en la cama de 260 (esbeltez con 6: 4)
BRIM_OBJETO["tap_pre_placa"] = 15.0  # 149 de alto sobre 6 (esbeltez con 15: 4,1; la tanda sigue en las mismas camas)
ESBELTEZ_MAX = 6.0  # alto / (base minima de la primera capa + 2 brim): mas que esto se tambalea con la boquilla
# Despegue (auditoria 2026-10-25): la boquilla empuja la punta (~0,2 N) y la cama acelera la pieza (6 m/s2); el momento
# en la base sobre el modulo resistente minimo de la primera capa. Mas de esto, brim propio o acostarla.
F_BOQUILLA, A_CAMA, DESPEGUE_MAX = 0.2, 6.0, 0.1   # N, m/s2, MPa


def poligonos(scad_txt, tmp):
    scad, svg = tmp / "s.scad", tmp / "s.svg"
    scad.write_text(scad_txt)
    svg.unlink(missing_ok=True)   # si el resultado es vacio OpenSCAD no escribe nada: que no quede el SVG anterior
    subprocess.run([str(R.OPENSCAD), "-o", str(svg), str(scad)], capture_output=True)
    if not svg.exists():
        return []
    txt = svg.read_text().replace("\n", " ")
    out = []
    for sub in re.findall(r"M([^z]*)z", txt):
        pts = np.array([list(map(float, p.split(","))) for p in re.findall(r"-?[\d.]+,-?[\d.]+", sub)])
        if len(pts) >= 3:
            out.append(np.c_[pts[:, 0], -pts[:, 1]])
    return out


def firmada(p):
    """Area con signo. En el SVG que escribe OpenSCAD los contornos exteriores salen negativos y los agujeros
    positivos (2026-10-24: antes se sumaban todos en valor absoluto y un anillo contaba doble)."""
    x, y = p[:, 0], p[:, 1]
    return (np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2


def area(p):
    return abs(firmada(p))


def area_region(paths):
    """Area neta de una region con agujeros (lista de caminos cerrados del SVG)."""
    return abs(sum(firmada(p) for p in paths))


def casco(pts):
    """Casco convexo 2D (cadena monotona), en sentido antihorario."""
    pts = np.unique(np.round(pts, 4), axis=0)
    if len(pts) < 3:
        return pts
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def mitad(ps):
        h = []
        for q in ps:
            while len(h) >= 2 and np.cross(h[-1] - h[-2], q - h[-2]) <= 0:
                h.pop()
            h.append(q)
        return h
    return np.array(mitad(pts)[:-1] + mitad(pts[::-1])[:-1])


def ancho_minimo(h):
    """Calibre minimo de un poligono convexo: lo angosta que es la base en su direccion mas angosta."""
    if len(h) < 3:
        return 0.0
    mejor = np.inf
    for a, b in zip(h, np.roll(h, -1, axis=0)):
        e = b - a
        n = np.array([-e[1], e[0]]) / max(np.linalg.norm(e), 1e-12)
        pr = h @ n
        mejor = min(mejor, pr.max() - pr.min())
    return float(mejor)


def dentro_de(q, i):
    """El camino q (un agujero) esta dentro del contorno i (prueba de un punto, regla par-impar)."""
    x, y = q[0]
    xs, ys = i[:, 0], i[:, 1]
    xs1, ys1 = np.roll(xs, -1), np.roll(ys, -1)
    cruza = ((ys > y) != (ys1 > y)) & (x < (xs1 - xs) * (y - ys) / np.where(ys1 - ys == 0, 1e-12, ys1 - ys) + xs)
    return bool(cruza.sum() % 2)


def margen_en_casco(h, p):
    """Distancia (con signo) del punto p al borde del casco h: positiva adentro, negativa afuera."""
    if len(h) < 3:
        return -np.inf
    d = []
    for a, b in zip(h, np.roll(h, -1, axis=0)):
        e = b - a
        n = np.array([-e[1], e[0]]) / max(np.linalg.norm(e), 1e-12)   # normal hacia adentro (casco antihorario)
        d.append((p - a) @ n)
    return float(min(d))


def modulo_minimo(caminos):
    """Modulo resistente minimo (mm3) de la region de la primera capa (caminos del SVG: exteriores negativos, agujeros
    positivos), girando el eje de flexion cada 5 grados."""
    if not caminos:
        return 0.0
    A = Sx = Sy = Ixx = Iyy = Ixy = 0.0
    for q in caminos:
        x, y = q[:, 0], q[:, 1]
        x1, y1 = np.roll(x, -1), np.roll(y, -1)
        c = x * y1 - x1 * y                        # producto cruz del poligono: + exteriores, - agujeros (= -firmada)
        A += c.sum() / 2
        Sx += (c * (x + x1)).sum() / 6
        Sy += (c * (y + y1)).sum() / 6
        Ixx += (c * (y * y + y * y1 + y1 * y1)).sum() / 12
        Iyy += (c * (x * x + x * x1 + x1 * x1)).sum() / 12
        Ixy += (c * (x * y1 + 2 * x * y + 2 * x1 * y1 + x1 * y)).sum() / 24
    if A <= 0:
        return 0.0
    cx, cy = Sx / A, Sy / A
    Ixx, Iyy, Ixy = Ixx - A * cy * cy, Iyy - A * cx * cx, Ixy - A * cx * cy
    pts = np.vstack(caminos) - [cx, cy]
    w = np.inf
    for a in np.radians(np.arange(0, 180, 5)):
        n = np.array([np.cos(a), np.sin(a)])      # direccion de la fibra (la flexion es alrededor de su normal)
        I = Ixx * n[1] ** 2 + Iyy * n[0] ** 2 + 2 * Ixy * n[0] * n[1]
        w = min(w, I / max(np.abs(pts @ n).max(), 1e-9))
    return float(w)


def rasterizar(caminos, px=PX):
    """Mascara [y, x] de la region de los caminos del SVG (regla par-impar), con 2 mm de aire alrededor."""
    a = np.vstack(caminos)
    b = np.vstack([np.roll(c, -1, axis=0) for c in caminos])
    lo = a.min(0) - 2.0
    nx, ny = np.ceil((a.max(0) + 2.0 - lo) / px).astype(int)
    xs = lo[0] + (np.arange(nx) + 0.5) * px
    m = np.zeros((ny, nx), bool)
    for i, y in enumerate(lo[1] + (np.arange(ny) + 0.5) * px):
        c = (a[:, 1] > y) != (b[:, 1] > y)
        xc = np.sort(a[c, 0] + (y - a[c, 1]) * (b[c, 0] - a[c, 0]) / (b[c, 1] - a[c, 1]))
        m[i] = np.searchsorted(xc, xs) % 2 == 1
    return m


def angostas(caminos):
    """Cuantas ranuras de aire y tiras de material mas angostas que ANCHO_MIN tiene la region. Las ranuras cerradas son
    agujeros y ya cuentan como chicos (4 A / P): aqui van las que abren al borde y el aire entre dos islas."""
    if not caminos:
        return 0
    m = rasterizar(caminos)
    r = int(round(ANCHO_MIN / 2 / PX))
    disco = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r
    n = 0
    for x in (m & ~ndimage.binary_opening(m, disco), ndimage.binary_closing(m, disco) & ~ndimage.binary_fill_holes(m)):
        x = ndimage.binary_opening(x)         # sin las escaleras de 1 pixel de los bordes inclinados
        lab, k = ndimage.label(x)
        n += int((np.bincount(lab.ravel())[1:] * PX * PX > A_ANGOSTA).sum())
    return n


def centro_de_masa(tri):
    """Centroide del volumen (suma de tetraedros con signo desde el origen)."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    v = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
    return (v[:, None] * (a + b + c) / 4.0).sum(0) / v.sum()


def medir(ruta):
    """Islas, agujeros y anchos de la seccion de la pieza a Z_CORTE sobre la cama; y su base: ancho minimo de la
    primera capa, alto y cuanto adentro de la base cae el centro de masa (2026-10-25: placas de pie sobre cantos
    de 2,6 mm salian OK porque solo se contaban islas y agujeros)."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        # la pieza se apoya en z = 0 (exportar.py lo hace al escribir stl/; un STL suelto puede venir sin apoyar)
        tri = R.ex_carro.leer_stl(ruta)
        tri = tri - np.array([0, 0, tri.reshape(-1, 3)[:, 2].min()])
        apoyada = tmp / "apoyada.stl"
        R.ex_carro.escribir_stl(apoyada, tri)
        sec = f'projection(cut = true) translate([0, 0, -{Z_CORTE}]) import("{apoyada.as_posix()}");'
        islas = poligonos(f"fill() {sec}", tmp)
        huecos = poligonos(f"difference() {{ fill() {sec} {sec} }}", tmp)
        # ancho minimo de material: lo que desaparece al encoger 0,6 mm (una pared de 1,2 o menos)
        finos = poligonos(f"difference() {{ {sec} offset(r = 0.6) offset(delta = -0.6) {sec} }}", tmp)
        region = poligonos(sec, tmp)                # la seccion tal cual (con sus agujeros), para el modulo resistente
    # Agujeros = caminos negativos. Un camino positivo dentro de un hueco es una isla (torreta dentro de un
    # vaciado). Y fill(sec) - sec deja a veces una ASTILLA de area cero a lo largo del contorno (dos caminos
    # casi iguales de signo opuesto): se descartan los pares que se anulan (2026-10-24: contaba un agujero
    # falso del tamano de toda la pieza).
    pos = [h for h in huecos if firmada(h) > 0]
    neg = [h for h in huecos if firmada(h) < 0]

    def par(q, lista):
        return any(abs(area(q) - area(h)) < max(1.0, 0.01 * area(h)) and np.linalg.norm(q[0] - h[0]) < 1.0 for h in lista)
    huecos = [h for h in neg if not par(h, pos)]
    islas_adentro = [q for q in pos if not par(q, neg)]     # un poste dentro de un vaciado: tambien es una isla
    # diametro por area o hidraulico (4 A / P), el menor: una ranura de 4,4 x 16 tiene las puntas de un agujero de 4,4
    # y por area daba 9,2 (2026-10-25)
    perimetro = lambda h: float(np.linalg.norm(np.roll(h, -1, axis=0) - h, axis=1).sum())
    d_huecos = sorted(min(2 * np.sqrt(area(h) / np.pi), 4 * area(h) / perimetro(h)) for h in huecos)
    chicos = [d for d in d_huecos if d < D_CHICO]
    # area NETA de cada isla (sin sus agujeros: un agujero es de la isla que lo encierra)
    def neta(i):
        return area(i) - sum(area(h) for h in huecos if dentro_de(h, i))
    a_islas = sorted([neta(i) for i in islas] + [area(q) for q in islas_adentro], reverse=True)
    area_neta = sum(area(i) for i in islas) - sum(area(h) for h in huecos) + sum(area(q) for q in islas_adentro)
    h = casco(np.vstack(islas)) if islas else np.zeros((0, 2))
    cdm = centro_de_masa(tri)
    vol = abs(R.ex_carro.volumen_area(tri)[0])
    w = modulo_minimo(region)
    momento = F_BOQUILLA * float(tri[:, :, 2].max()) + vol * 1.24e-6 * A_CAMA * float(cdm[2])   # N mm (PLA macizo: cota alta)
    despegue = momento / w if w > 0 else np.inf
    return dict(islas=len(islas) + len(islas_adentro), isla_menor_mm2=round(float(a_islas[-1]), 1) if a_islas else 0.0,
                agujeros=len(huecos), chicos=len(chicos), d_min=round(float(d_huecos[0]), 1) if d_huecos else None,
                angostas=angostas(region),
                finos_mm2=round(float(area_region(finos)), 1), area=round(float(area_neta), 0),
                base_min=round(ancho_minimo(h), 1), alto=round(float(tri[:, :, 2].max()), 1),
                cdm_margen=round(margen_en_casco(h, cdm[:2]), 1), despegue_mpa=round(float(despegue), 3))


def esbeltez(n, m):
    """alto / (base minima + 2 brim) con el brim con que se imprime la pieza n."""
    return m["alto"] / (m["base_min"] + 2 * BRIM_OBJETO.get(n, BRIM_DEF))


def puntaje(m):
    """Mas alto = peor primera capa: cada bucle chico y cada isla suelta cuentan; las islas chicas, mas."""
    return int((m["chicos"] + m["angostas"]) * 3 + (m["islas"] - 1) * 2 + (4 if m["islas"] > 1 and m["isla_menor_mm2"] < 60 else 0) + (m["finos_mm2"] > 20))


def main():
    rutas = [Path(a) for a in sys.argv[1:]] or sorted((AQUI / "stl").glob("*.stl"))
    rutas = [r for r in rutas if not r.stem.startswith("rem_")]
    with ThreadPoolExecutor(R.HILOS) as ej:
        res = dict(zip([r.stem for r in rutas], ej.map(medir, rutas)))
    orden = sorted(res, key=lambda n: -puntaje(res[n]))
    print(f"{'pieza':24s} islas  isla<  agujeros  chicos(<{D_CHICO:g})  angostas(<{ANCHO_MIN:g})  d_min  finos  puntaje")
    for n in orden:
        m = res[n]
        print(f"{n:24s} {m['islas']:5d} {m['isla_menor_mm2']:6.0f} {m['agujeros']:9d} {m['chicos']:12d} {m['angostas']:15d} "
              f"{str(m['d_min']):>6s} {m['finos_mm2']:6.0f} {puntaje(m):7d}")
    malas = [n for n in orden if puntaje(res[n]) > 0]
    print(f"\n{len(malas)} de {len(res)} piezas con bucles chicos, ranuras o tiras angostas o islas en la primera capa")
    (AQUI / "primera_capa.json").write_text(json.dumps({n: dict(res[n], puntaje=puntaje(res[n])) for n in orden},
                                                       indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
