"""Revisa que cada pieza, en la orientacion en que se imprime, salga SIN soportes. Es la de la maqueta: copia mejorada de
..\\chasis_impreso\\revisar_voladizos.py (esa sigue siendo la del carro y no se toca).

Cada zona de caras que miran hacia abajo a mas de ANGULO_MAX grados de la vertical (y que no esta en la cama):
  - techo curvo de un agujero horizontal redondo: Ø <= D_HORIZ_MAX o techo en gota (CONVENCIONES). Antes un Ø20
    pasaba como puente de 11,8 y el Ø22,4 de un 608 como puente de 8.
  - PUENTE si tiene pared de la pieza en las DOS puntas de una direccion (x o y) y ese largo es <= PUENTE_MAX: sale.
  - Una zona chica (lado corto <= ZONA_MAX y largo <= PUENTE_MAX) sale.
  - Una colgada de una pared (cada cara a <= ZONA_MAX en horizontal de una pared de la pieza que baja al menos
    ZONA_MAX o hasta la cama: la salva la pared, CONVENCIONES 'salvo zonas de menos de 5 mm') sale; si es mas larga
    que PUENTE_MAX va como aviso (puede quedar algo caida). Asi pasan un labio de 2 a lo largo de su pared o los
    filetes de una rosca, y no la bandera de 3 x 30 del FC-51 (al aire, apoyada en una sola punta: 2026-10-25 pasaba
    por angosta), un perno en voladizo ni un techo a 60 grados (su material esta al lado de la cara pero no baja).
  - Lo demas es VOLADIZO, tenga o no la misma pieza debajo (2026-10-25: un ala de 120 x 12 sobre la base de la propia
    pieza pasaba como 'puente' porque el rayo pegaba en la base).

Y CAPA POR CAPA (capas(); 2026-10-25, segunda opinion: mon_e4, tap_pre_placa y vas_lat_s_b tenian partes que nacian en
el aire y vas_lat_s_a postes en V colgados de una sola punta, con todas sus caras a 40-45 grados: el criterio de las caras
no las ve y el laminador las imprime sobre nada). La pieza se corta cada CAPA mm y cada corte se compara con el de abajo:
  - NACE EN EL AIRE: un pedazo del corte que no toca (a menos de APOYO) nada apoyado de la capa de abajo. Lo que nace
    suelto sigue suelto hasta que se une con lo apoyado (asi una punta en V que empieza en un punto se marca al crecer).
  - CUELGA DE UNA PUNTA: lo nuevo del corte (fuera de la capa de abajo + APOYO) a mas de ZONA_MAX de la capa de abajo,
    salvo un puente de <= PUENTE_MAX con la capa de abajo en las dos puntas: lo mismo que perdonan las caras.
"""
import numpy as np

ANGULO_MAX = 50      # grados desde la vertical que el PLA aguanta sin soporte (45-55 es lo normal)
PUENTE_MAX = 12      # mm de puente que una Hi hace bien con PLA
ZONA_MAX = 5.0       # mm: una zona sin apoyo mas angosta que esto (corta, o colgada de una pared) la salva la pared
Z_CAMA = 0.35        # lo que esta mas abajo que esto apoya en la cama
D_HORIZ_MAX = 12.5   # mm: agujero horizontal sin gota (CONVENCIONES pide Ø12; +0,5 por el juego de 2 tol de un eje de 12)
# capa por capa
CAPA = 0.2           # mm entre cortes (la capa de la maqueta)
PIXEL = 0.2          # mm por pixel al rasterizar cada corte
APOYO = 0.4          # mm: lo que queda a menos de esto de la capa de abajo apoya (a 50 grados cada capa corre 0,24)
AREA_ISLA = 0.5      # mm2: un pedazo suelto mas chico es ruido del rasterizado (si es una punta real, se marca al crecer)
Z0_CORTE = 0.1137    # altura del primer corte: el desfase evita cortar justo sobre una cara horizontal de cota redonda
# Puentes de mas de PUENTE_MAX aceptados a mano, pieza por pieza (largo maximo en mm). 2026-10-25, decision del usuario: en
# mon_e4 (boca abajo) la cumbrera entre los pisos de los canales A y B arranca como un puente de 30 apoyado en las dos
# paredes; acortarlo mete material en el canal de 30 de la moneda de 26,7 o bajo la aleta. Va como aviso: puede quedar caida.
# Atado tambien a la altura en la cama (z del corte, mm): otro puente largo en otra parte de la pieza sigue siendo MAL.
PUENTES_ACEPTADOS = {"mon_e4": dict(largo=30.5, z=(46.5, 47.7))}


def aceptado(c, n):
    """True si el colgado c (de capas()) es el puente que PUENTES_ACEPTADOS deja pasar en la pieza n."""
    a = PUENTES_ACEPTADOS.get(n)
    return bool(a) and c.get("puente", np.inf) <= a["largo"] and a["z"][0] <= c["z"] <= a["z"][1]


def rayos(origenes, tri, d=(0.0, 0.0, -1.0)):
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


def dentro(puntos, tri):
    """True donde el punto queda dentro de la pieza (paridad de cortes de un rayo casi vertical)."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    e1, e2 = b - a, c - a
    d = np.array([1e-3, 2e-3, 1.0]) / np.linalg.norm([1e-3, 2e-3, 1.0])
    p = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-12
    a, e1, e2, p, inv = a[ok], e1[ok], e2[ok], p[ok], 1.0 / det[ok]
    salida = np.zeros(len(puntos), bool)
    for k in range(0, len(puntos), 256):
        s = puntos[k:k + 256][:, None, :] - a[None]
        u = np.einsum("nij,ij->ni", s, p) * inv
        q = np.cross(s, e1[None])
        v = (q @ d) * inv
        t = np.einsum("nij,ij->ni", q, e2) * inv
        salida[k:k + 256] = ((u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)).sum(axis=1) % 2 == 1
    return salida


def colgada(g, tri, centro, area):
    """Fraccion del area de la zona g con una pared al lado: a <= ZONA_MAX en horizontal (8 direcciones) hay pieza
    0,3 mm bajo la cara, y sigue habiendo ZONA_MAX mas abajo (o ya es la cama). Que la pared baje: el material de un
    techo inclinado a 60 grados tambien queda 'al lado' de su propia cara."""
    lo, hi = centro[g].min(axis=0) - ZONA_MAX - 1, centro[g].max(axis=0) + ZONA_MAX + 1
    cerca = tri[(tri[:, :, 0].max(axis=1) >= lo[0]) & (tri[:, :, 0].min(axis=1) <= hi[0])
                & (tri[:, :, 1].max(axis=1) >= lo[1]) & (tri[:, :, 1].min(axis=1) <= hi[1])]
    pegada = np.zeros(len(g), bool)
    for s in (0.3, 0.8, 1.5, 2.5, 3.5, 4.5, ZONA_MAX + 0.3):
        for a in np.radians(np.arange(0, 360, 45)):
            falta = np.nonzero(~pegada)[0]
            if not len(falta):
                break
            p = centro[g][falta] + s * np.array([np.cos(a), np.sin(a), 0]) - np.array([0, 0, 0.3])
            ok = dentro(p, cerca)
            hondo = p[ok] - np.array([0, 0, ZONA_MAX])
            ok[ok] = (hondo[:, 2] < 0) | dentro(hondo, cerca)
            pegada[falta[ok]] = True
    return float((area[g] * pegada).sum() / area[g].sum())


def diametro_techo(g, tri, n, centro):
    """Diametro de un techo curvo CONCAVO (agujero horizontal) con el radio local de cada arista entre dos caras de la
    zona: ancho de las facetas (de la arista al vertice de enfrente) / giro de la normal. Se toma la mediana: una
    ranura de circulos solapados (Ø9 cada 1 mm) da Ø9 y no el de un ajuste global. None si es plano o convexo (la
    panza de un perno acostado: eso lo mide el voladizo)."""
    u, inv = np.unique(np.round(tri[g].reshape(-1, 3), 3), axis=0, return_inverse=True)
    inv = inv.reshape(-1, 3)
    aristas = {}
    for k, f in enumerate(inv):
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            aristas.setdefault((min(a, b), max(a, b)), []).append(k)
    radios = []
    for (a, b), ks in aristas.items():
        if len(ks) != 2:
            continue
        i, j = g[ks[0]], g[ks[1]]
        dn = n[j] - n[i]
        if dn @ dn < np.sin(np.radians(2)) ** 2:      # casi coplanares (las dos mitades de una faceta)
            continue
        e = (u[b] - u[a]) / max(np.linalg.norm(u[b] - u[a]), 1e-12)
        ancho = 0.0
        for k in ks:      # distancia del vertice de enfrente a la arista (el ancho de la faceta; vale con las dos mitades)
            q = u[next(t for t in inv[k] if t not in (a, b))] - u[a]
            ancho += np.linalg.norm(q - (q @ e) * e) / 2
        concavo = (centro[j] - centro[i]) @ dn < 0      # el eje esta en c - r n
        radios.append((1 if concavo else -1) * ancho / np.sqrt(dn @ dn))
    radios = np.array(radios)
    if (radios > 0).sum() < 3 or (radios > 0).mean() < 0.5:
        return None
    return 2 * float(np.median(radios[radios > 0]))


def revisar(tri):
    """tri: triangulos (N, 3, 3) de la pieza en la orientacion de la cama, apoyada en z = 0."""
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = np.linalg.norm(n, axis=1) / 2
    n = n / np.maximum(2 * area, 1e-12)[:, None]
    centro = tri.mean(axis=1)
    # una cara inclinada phi desde la vertical tiene n_z = -sin(phi): cuenta si phi > ANGULO_MAX
    abajo = (n[:, 2] < -np.sin(np.radians(ANGULO_MAX))) & (centro[:, 2] > Z_CAMA) & (area > 1e-4)
    idx = np.nonzero(abajo)[0]
    voladizo, largo, malas, agujeros, colgadas = 0.0, 0.0, [], [], []
    for g in (agrupar(idx, tri) if len(idx) else []):
        g = np.array(g)
        pts = tri[g].reshape(-1, 3)
        ext = (float(np.ptp(pts[:, 0])), float(np.ptp(pts[:, 1])))
        corto, largo_zona = min(ext), max(ext)
        donde = dict(z=[round(float(pts[:, 2].min()), 1), round(float(pts[:, 2].max()), 1)],
                     x=[round(float(pts[:, 0].min()), 1), round(float(pts[:, 0].max()), 1)],
                     y=[round(float(pts[:, 1].min()), 1), round(float(pts[:, 1].max()), 1)], mm2=round(float(area[g].sum()), 1))
        d = diametro_techo(g, tri, n, centro)
        if d is not None and d > D_HORIZ_MAX:
            agujeros.append(dict(donde, d=round(d, 1)))
            continue
        # pared en las dos puntas de x o de y: rayos desde 0,1 mm bajo la cara de la zona mas cercana a su centro (el
        # centro mismo de una zona curva, como la panza de un perno, puede caer dentro del material)
        f0 = g[np.argmin(np.linalg.norm(centro[g, :2] - pts[:, :2].mean(axis=0), axis=1))]
        c = centro[f0] - np.array([0, 0, 0.1])
        lados = [rayos(c[None], tri, dd)[0] for dd in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0))]
        tramo = [ext[k] for k in (0, 1) if lados[2 * k] + lados[2 * k + 1] <= ext[k] + 1 and ext[k] <= PUENTE_MAX]
        if tramo:
            largo = max(largo, min(tramo))
            continue
        if corto <= ZONA_MAX and largo_zona <= PUENTE_MAX:
            continue
        if colgada(g, tri, centro, area) >= 0.9:
            if largo_zona > PUENTE_MAX:
                colgadas.append(donde)
            continue
        voladizo += area[g].sum()
        malas.append(donde)
    islas, colgados = capas(tri)
    return dict(voladizo=round(voladizo, 1), puente_largo=round(largo, 1), zonas=malas, agujeros=agujeros,
                colgadas=colgadas, caras=idx.tolist(), islas=islas, colgados=colgados)


def corte(tri, z, x0, y0, nx, ny):
    """Seccion de la malla cerrada en z: imagen (ny, nx) de pixeles PIXEL desde (x0, y0), por paridad en cada fila, mas
    los pixeles por donde pasa el borde: el filo de una cuna mas fino que un pixel aparecia y desaparecia de una capa a
    la otra y lo de arriba parecia nacer en el aire."""
    t = tri[(tri[:, :, 2].min(axis=1) < z) & (tri[:, :, 2].max(axis=1) >= z)]
    if not len(t):
        return np.zeros((ny, nx), bool)
    a, b = t, np.roll(t, -1, axis=1)                       # las aristas 0-1, 1-2 y 2-0
    cruza = (a[:, :, 2] < z) != (b[:, :, 2] < z)           # semiabierto: un vertice en el plano cuenta arriba, 2 por triangulo
    f = (z - a[:, :, 2]) / np.where(cruza, b[:, :, 2] - a[:, :, 2], 1.0)
    p = (a[:, :, :2] + f[:, :, None] * (b[:, :, :2] - a[:, :, :2]))[cruza].reshape(-1, 2, 2)
    xa, ya, xb, yb = p[:, 0, 0], p[:, 0, 1], p[:, 1, 0], p[:, 1, 1]
    # filas cuyo centro y cumple min < y <= max (semiabierto otra vez) y en cada una la x donde cruza el segmento
    j0 = np.floor((np.minimum(ya, yb) - y0) / PIXEL - 0.5).astype(int) + 1
    n = np.maximum(np.floor((np.maximum(ya, yb) - y0) / PIXEL - 0.5).astype(int) - j0 + 1, 0)
    s = np.repeat(np.arange(len(p)), n)
    j = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n) + j0[s]
    x = xa[s] + (y0 + (j + 0.5) * PIXEL - ya[s]) * (xb[s] - xa[s]) / (yb[s] - ya[s])
    c = np.clip(np.floor((x - x0) / PIXEL - 0.5).astype(int) + 1, 0, nx)
    # cada cruce cambia de lado a todos los pixeles a su derecha: adentro = cantidad impar de cruces a la izquierda
    cuenta = np.bincount(j * (nx + 1) + c, minlength=ny * (nx + 1)).reshape(ny, nx + 1)
    img = (np.cumsum(cuenta, axis=1)[:, :nx] % 2).astype(bool)
    # el borde: puntos cada medio pixel sobre cada segmento
    n = np.ceil(np.hypot(xb - xa, yb - ya) / (PIXEL / 2)).astype(int) + 1
    s = np.repeat(np.arange(len(p)), n)
    f = (np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)) / np.maximum(n[s] - 1, 1)
    img[np.clip(((ya[s] + f * (yb[s] - ya[s]) - y0) / PIXEL).astype(int), 0, ny - 1),
        np.clip(((xa[s] + f * (xb[s] - xa[s]) - x0) / PIXEL).astype(int), 0, nx - 1)] = True
    return img


def capas(tri):
    """([islas], [colgados]) de la pieza en la orientacion de la cama, corte por corte (ver el encabezado). Cada uno con
    la altura del corte, donde esta y a cuantos mm queda de lo de abajo."""
    from scipy import ndimage      # aqui y no arriba: revisar.py (y modelo_3d.py) se importan en el entorno del proyecto, sin scipy
    lo, hi = tri.reshape(-1, 3).min(axis=0), tri.reshape(-1, 3).max(axis=0)
    x0, y0 = lo[0] - 1.0, lo[1] - 1.0
    nx, ny = int((hi[0] - lo[0] + 2) / PIXEL) + 1, int((hi[1] - lo[1] + 2) / PIXEL) + 1
    k = int(round(APOYO / PIXEL))
    ocho = np.ones((3, 3), bool)
    margen = int(PUENTE_MAX / PIXEL) + 2
    islas, colgados = [], []
    def donde(m, z, **kw):
        jj, ii = np.nonzero(m)
        return dict(z=round(float(z - lo[2]), 1), x=[round(float(x0 + PIXEL * (i + 0.5)), 1) for i in (ii.min(), ii.max())],
                    y=[round(float(y0 + PIXEL * (j + 0.5)), 1) for j in (jj.min(), jj.max())], **kw)
    abajo = apoyado = suelto_visto = None
    for z in np.arange(lo[2] + Z0_CORTE, hi[2], CAPA):
        s = corte(tri, z, x0, y0, nx, ny)
        if abajo is None or z - lo[2] < Z_CAMA:          # la primera capa apoya en la cama
            abajo, apoyado, suelto_visto = s, s, np.zeros_like(s)
            continue
        lab, n = ndimage.label(s, ocho)
        ids = np.unique(lab[s & ndimage.binary_dilation(apoyado, ocho, k)]) if apoyado.any() else np.zeros(0, int)
        anc = np.isin(lab, ids[ids > 0])
        suelto = s & ~anc
        # nace en el aire: lo suelto que no sigue de un pedazo ya marcado, cuando pasa de AREA_ISLA
        visto = np.zeros_like(s)
        if suelto.any():
            sig = set(np.unique(lab[suelto & ndimage.binary_dilation(suelto_visto, ocho, k)]).tolist()) if suelto_visto.any() else set()
            area = np.bincount(lab.ravel(), minlength=n + 1) * PIXEL ** 2
            for i in np.unique(lab[suelto]):
                if i not in sig and area[i] >= AREA_ISLA:
                    m = lab == i
                    d = ndimage.distance_transform_edt(~apoyado)[m].min() * PIXEL if apoyado.any() else np.inf
                    islas.append(donde(m, z, mm2=round(float(area[i]), 1), a=round(float(d), 1)))
                    sig.add(i)
            visto = np.isin(lab, list(sig)) & suelto
        # cuelga: lo nuevo apoyado (fuera de la capa de abajo + APOYO), mirado en una ventana alrededor
        nuevo = anc & ~ndimage.binary_dilation(abajo, ocho, k)
        if nuevo.any():
            jj, ii = np.nonzero(nuevo)
            v = (slice(max(jj.min() - margen, 0), jj.max() + margen + 1), slice(max(ii.min() - margen, 0), ii.max() + margen + 1))
            ab, nu = abajo[v], nuevo[v]
            if ab.any():
                dist, cerca = ndimage.distance_transform_edt(~ab, return_indices=True)
            else:
                dist, cerca = np.full(ab.shape, np.inf), None
            if (nu & (dist * PIXEL > ZONA_MAX)).any():
                labn, _ = ndimage.label(nu, ocho)
                q = np.argwhere(ab)
                for i in np.unique(labn[nu & (dist * PIXEL > ZONA_MAX)]):
                    m = labn == i
                    p = np.unravel_index(np.argmax(np.where(m, dist, -1)), m.shape)
                    d = float(dist[p]) * PIXEL
                    # puente: la capa de abajo tambien del otro lado del punto mas lejano (fuera de la ventana no se ve:
                    # sale como colgado de una punta, que tambien es MAL)
                    # shortcut: solo mira el punto mas lejano; si un puente con un brazo suelto de 5-6 mm pasa, mirar cada punto
                    largo = None
                    if cerca is not None:
                        w = q - np.array(p)
                        otro = (w @ (cerca[:, p[0], p[1]] - np.array(p))) < 0
                        if otro.any():
                            largo = d + float(np.hypot(w[otro, 0], w[otro, 1]).min()) * PIXEL
                    if largo is None or largo > PUENTE_MAX + APOYO:
                        mm = np.zeros_like(s)
                        mm[v] = m
                        colgados.append(donde(mm, z, a=round(d, 1), **({"puente": round(largo, 1)} if largo else {})))
        abajo, apoyado, suelto_visto = s, anc, visto
    return islas, colgados


def agrupar(idx, tri):
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


def mal(r, n=None):
    """Lo que hace fallar la pieza n (lista vacia = sale sin soportes)."""
    out = []
    colgados = [c for c in r.get("colgados", []) if not aceptado(c, n)]
    if r["voladizo"] > 0:
        out.append(f"voladizo {r['voladizo']} mm2 en {r['zonas'][:2]}")
    if r["puente_largo"] > PUENTE_MAX:
        out.append(f"puente de {r['puente_largo']} mm")
    for a in r["agujeros"][:2]:
        out.append(f"agujero horizontal de {a['d']} mm de diametro sin gota (max {D_HORIZ_MAX:g}), techo en z {a['z']} x {a['x']} y {a['y']}")
    if r.get("islas"):
        out.append(f"{len(r['islas'])} parte(s) nacen en el aire, sin nada debajo (z, donde y a cuantos mm de lo de abajo): {r['islas'][:2]}")
    if colgados:
        out.append(f"{len(colgados)} parte(s) empiezan sin nada debajo a mas de {ZONA_MAX:g} mm de la capa de abajo, colgadas de "
                   f"una punta o en un puente de mas de {PUENTE_MAX} ('puente': su largo; 'a': mm hasta lo de abajo): {colgados[:2]}")
    return out
