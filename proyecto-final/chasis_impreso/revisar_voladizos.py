"""Revisa que cada pieza, en la orientacion en que se imprime, salga SIN soportes.

Para cada cara que mira hacia abajo con mas de ANGULO_MAX grados desde la vertical (y que no esta en la
cama), lanza un rayo hacia abajo desde su centro:
  - si llega a la cama sin tocar la pieza -> VOLADIZO: queda en el aire, necesita soporte.
  - si toca la pieza -> PUENTE (techo de un agujero o una ranura): sale si es corto (PUENTE_MAX mm).
Las zonas angostas (lado corto < ZONA_MAX) se ignoran: son techos de agujeros o pernos acostados.

Uso: python revisar_voladizos.py [carpeta]   (por defecto stl_sin_membrana; sale 1 si alguna pieza falla)
"""
import sys
from pathlib import Path

import numpy as np

import exportar as ex

ANGULO_MAX = 50      # grados desde la vertical que el PLA aguanta sin soporte (45-55 es lo normal)
PUENTE_MAX = 12      # mm de puente que una Hi hace bien con PLA
ZONA_MAX = 5.0       # mm: una zona sin apoyo mas angosta que esto la salva la pared (techo de agujero, perno acostado)
Z_CAMA = 0.35        # lo que esta mas abajo que esto apoya en la cama


def rayos_abajo(origenes, tri, d=(0.0, 0.0, -1.0)):
    """Para cada origen, distancia al primer triangulo en la direccion d (np.inf si no hay). Moller-Trumbore."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    e1, e2 = b - a, c - a
    d = np.array(d, dtype=float)
    p = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-9
    a, e1, e2, p, det = a[ok], e1[ok], e2[ok], p[ok], det[ok]
    inv = 1.0 / det
    salida = np.full(len(origenes), np.inf)
    for k in range(0, len(origenes), 256):
        o = origenes[k:k + 256][:, None, :]
        s = o - a[None]
        u = np.einsum("nij,ij->ni", s, p) * inv
        q = np.cross(s, e1[None])
        v = (q @ d) * inv
        t = np.einsum("nij,ij->ni", q, e2) * inv
        golpe = (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0.05)
        t = np.where(golpe, t, np.inf)
        salida[k:k + 256] = t.min(axis=1)
    return salida


def revisar(ruta):
    tri = ex.leer_stl(ruta)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(n, axis=1) / 2
    n = n / np.maximum(2 * area, 1e-12)[:, None]
    centro = tri.mean(axis=1)
    # una cara inclinada phi desde la vertical tiene n_z = -sin(phi): cuenta si phi > ANGULO_MAX
    # (hasta el 2026-10-24 decia sin(90 - ANGULO_MAX): marcaba desde 40 grados, mas estricto que lo escrito)
    abajo = (n[:, 2] < -np.sin(np.radians(ANGULO_MAX))) & (centro[:, 2] > Z_CAMA) & (area > 1e-4)
    idx = np.nonzero(abajo)[0]
    if not len(idx):
        return dict(voladizo=0.0, puente_largo=0.0, zonas=[], caras=[])
    dist = rayos_abajo(centro[idx] + np.array([0, 0, -1e-3]), tri)
    al_aire = ~np.isfinite(dist) | (dist >= centro[idx, 2] - 1e-3)
    zonas = agrupar(idx, centro, tri)
    voladizo, largo, malas = 0.0, 0.0, []
    for g in zonas:
        pts = tri[g].reshape(-1, 3)
        corto = float(min(np.ptp(pts[:, 0]), np.ptp(pts[:, 1])))   # lo que de verdad queda sin apoyo
        en_aire = al_aire[np.searchsorted(idx, g)]
        if en_aire.mean() > 0.5 and corto <= PUENTE_MAX:
            # techo abierto hacia la cama (ranura pasante o cajera): es un PUENTE si tiene pared en las dos puntas
            # de una direccion y ese largo es <= PUENTE_MAX (2026-10-24: antes pedia pared en los 4 lados y
            # marcaba como voladizo un puente de 10 mm sobre una ranura pasante, que si sale)
            c = pts.mean(axis=0) - np.array([0, 0, 0.1])
            lados = [rayos_abajo(c[None], tri, d)[0] for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0))]
            ext = (np.ptp(pts[:, 0]), np.ptp(pts[:, 1]))
            tramo = [ext[k] for k in (0, 1) if lados[2 * k] + lados[2 * k + 1] <= ext[k] + 1 and ext[k] <= PUENTE_MAX]
            if tramo:
                en_aire = np.zeros_like(en_aire)
                largo = max(largo, min(tramo))
        if en_aire.mean() > 0.5 and corto > ZONA_MAX:              # voladizo de verdad
            voladizo += area[g].sum()
            malas.append(dict(z=[round(float(pts[:, 2].min()), 1), round(float(pts[:, 2].max()), 1)],
                              x=[round(float(pts[:, 0].min()), 1), round(float(pts[:, 0].max()), 1)],
                              y=[round(float(pts[:, 1].min()), 1), round(float(pts[:, 1].max()), 1)], mm2=round(float(area[g].sum()), 1)))
        elif en_aire.mean() <= 0.5:
            largo = max(largo, corto)
    return dict(voladizo=round(voladizo, 1), puente_largo=round(largo, 1), zonas=malas, caras=[i for g in zonas for i in g])


def agrupar(idx, centro, tri):
    """Zonas de caras hacia abajo conectadas (comparten vertice)."""
    v = np.round(tri[idx].reshape(-1, 3), 3)
    _, inv = np.unique(v, axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    padre = list(range(len(idx)))
    def raiz(a):
        while padre[a] != a:
            padre[a] = padre[padre[a]]
            a = padre[a]
        return a
    por_vertice = {}
    for k, fila in enumerate(inv):
        for vv in fila:
            if vv in por_vertice:
                ra, rb = raiz(k), raiz(por_vertice[vv])
                if ra != rb:
                    padre[ra] = rb
            else:
                por_vertice[vv] = k
    grupos = {}
    for k in range(len(idx)):
        grupos.setdefault(raiz(k), []).append(idx[k])
    return list(grupos.values())


def main():
    carpeta = ex.AQUI / (sys.argv[1] if len(sys.argv) > 1 else "stl_sin_membrana")
    malas = []
    for ruta in sorted(carpeta.glob("*.stl")):
        r = revisar(ruta)
        mal = r["voladizo"] > 0 or r["puente_largo"] > PUENTE_MAX
        print(f"{'FALLA' if mal else 'ok   '} {ruta.stem:22s} voladizo {r['voladizo']:7.1f} mm2   puente mas largo {r['puente_largo']:5.1f} mm"
              + (f"   zona {r['zonas'][0]}" if r["zonas"] else ""))
        if mal:
            malas.append(ruta.stem)
    print("sin soportes:", "TODAS" if not malas else f"fallan {len(malas)}: {', '.join(malas)}")
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main())
