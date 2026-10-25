"""Estructura impresa de la maqueta (usuario, 2026-10-24: "todo impreso, sin perfil"; la forma puede cambiar).

Reemplaza los 6,1 m de perfil 2020, las 24 escuadras, los 15 pies niveladores y las tuercas en T por:
  - TUBOS de 20 x 20 impresos acostados (hueco con techo a 45 grados), lisos en las dos puntas;
  - NODOS: cada brazo es una cajera donde entra el tubo entero 22 mm. Un nodo se imprime en una sola
    orientacion (tal cual o dado vuelta) y el techo de 45 grados de cada cajera horizontal mira hacia arriba
    EN LA CAMA: nada queda en el aire. Si por un nodo pasa un montante de largo (arriba y abajo), el nodo es
    un COLLAR que abraza el tubo pasante;
  - EMPALMES: manguito de 44 mm que une dos tramos cuando un tubo pasa de largo_max;
  - TACOS: separador entre el riel de la mesa de monedas y la viga del portico (placa con remaches);
  - REMACHES impresos, todos de agarre corto (pared de nodo 2,4 + holgura 0,2 + pared de tubo 2): la una abre
    dentro del hueco del tubo. revisar.py los MIDE en el ensamble.

Con un piso de tubos (z de 0 a 20) que amarra todo: la maqueta es UNA sola estructura (antes eran mesas
sueltas sobre el MDF). Las posiciones salen del inventario de sim/mundo.py y del visor; lo funcional
(alturas de bandas, carrusel, canaleta) no se mueve, lo de soporte si se movio para que entre.

Uso: python estructura.py -> estructura_gen.scad (lo incluye maqueta.scad) y un resumen con largos,
masa estimada y las comprobaciones (espacio entre nodos, zonas libres, flechas por carga).
"""
import math
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent

# ----------------------------------------------------------------- seccion (igual que comun.scad)
LADO = 16.0
PARED = 1.6
TOL = 0.2
PARED_NODO = 2.4
CAJERA = LADO + 2 * TOL                       # 20,4
BRAZO_ANCHO = CAJERA + 2 * PARED_NODO         # 21,2
HONDO = 22.0                                  # lo que entra el tubo en cada cajera
ALERO = (LADO / 2 + TOL) - 5.0                # alto del alero de 45 grados sobre la cajera (comun.scad: cajera_2d)
BRAZO = BRAZO_ANCHO / 2 + HONDO               # centro -> punta de cada brazo (32,6): la cajera empieza donde
                                              # termina la pared de la cajera perpendicular (12,6 del centro)
LARGO_MAX = 240.0
EMPALME = 2 * HONDO + 4.0                     # manguito de 48 mm (4 de tope al medio)
AGARRE = PARED_NODO + TOL + PARED             # 4,6
PLA = 1.24                                    # g/cm3

# ----------------------------------------------------------------- nodos (mm, marco del mundo)
Z_PISO = BRAZO_ANCHO / 2                      # centro de los nodos del piso: su cara de abajo en el piso
Z_RIEL = 440.0                                # eje de los rieles de la mesa de monedas (banda a 452)
Z_VIGA = 400.0                                # eje de la viga del portico
Z_VASOS = 85.0                                # eje del marco de la mesa de vasos (banda a 122)
Y_A = -40.5                                   # linea del portico y del riel -y de monedas
NODOS = {
    # piso
    "F1": (-170, Y_A, Z_PISO), "F2": (-170, 40.5, Z_PISO), "F3": (30, 40.5, Z_PISO),
    "F4": (-50, Y_A, Z_PISO), "F6": (30, Y_A, Z_PISO), "F5": (315, Y_A, Z_PISO),
    # cinta de vasos (2026-10-24): NADA bajo la banda (la vuelta de abajo con sus separadores baja a z 81). El
    # bastidor se apoya en postes por fuera: lado +y el poste de F6 y la columna del portico (x 315); lado -y
    # los postes de V2 y V4 (y -152,5: su cara toca la lateral -y en -144,5). V2 en x 40 por el NEMA (x <= 21).
    "V2": (40, -152.5, Z_PISO), "K0": (160, -152.5, Z_PISO), "V4": (315, -152.5, Z_PISO),
    "C1": (297.5, -211.1, Z_PISO), "C2": (422.5, -211.1, Z_PISO),
    "C3": (297.5, -309.5, Z_PISO), "C4": (422.5, -309.5, Z_PISO),
    "K1": (160, -422, Z_PISO),
    # anclaje del muelle del carro: detras de la cola del carro estacionado (cola en y -417,5)
    "M1": (297.5, -395, Z_PISO), "M2": (422.5, -395, Z_PISO),
    # mesa de monedas
    "T1": (-170, Y_A, Z_RIEL), "T2": (-170, 40.5, Z_RIEL), "T3": (30, 40.5, Z_RIEL),
    "Q2": (30, 40.5, 682),                    # punta del poste de la camara cenital (sigue de la pata T3)
    # portico
    "P1": (-50, Y_A, Z_VIGA), "P2": (315, Y_A, Z_VIGA),
}
# Miembros: (a, b) entre nodos, o (a, punto) con punta libre. Los verticales que siguen de largo por un
# nodo se declaran como UN miembro que pasa por el (lista de nodos intermedios).
MIEMBROS = [
    # piso
    ("F1", "F4"), ("F4", "F6"), ("F6", "F5"), ("F1", "F2"), ("F2", "F3"), ("F3", "F6"),
    ("F5", "V4"), ("V2", "K0"), ("K0", "V4"), ("K0", "K1"),
    # la canaleta es un marco aparte (sus postes quedan a 59 mm de la linea y -152,5: muy cerca para un tubo)
    ("C1", "C3"), ("C1", "C2"), ("C3", "C4"), ("C2", "C4"),
    ("C3", "M1"), ("C4", "M2"), ("M1", "M2"),
    # mesa de monedas: patas, rieles y amarre de la cola
    ("F1", "T1"), ("F2", "T2"), ("F3", "T3"), ("T3", "Q2"),
    ("T1", (106, Y_A, Z_RIEL)), ("T2", "T3"), ("T3", (106, 40.5, Z_RIEL)), ("T1", "T2"),
    ("Q2", (30, -15, 682)),                   # brazo de la camara cenital (punta libre sobre la banda)
    # portico
    ("F4", "P1"), ("F5", "P2"), ("P1", "P2"),
    # postes del bastidor de la cinta de vasos (punta libre a la altura de la cara de arriba de las laterales)
    ("F6", (30, Y_A, 120)), ("V2", (40, -152.5, 120)), ("V4", (315, -152.5, 120)),
    # postes con punta libre (lo de arriba lo pone cada subsistema)
    ("C1", (297.5, -211.1, 175.28)), ("C2", (422.5, -211.1, 175.28)),
    ("C3", (297.5, -309.5, 148.91)), ("C4", (422.5, -309.5, 148.91)),
    ("K1", (160, -422, 190)),
]
# Tacos entre el riel -y (z 430) y la viga (z 410): x de cada uno. Lejos de los bloques de los rodillos
# (motriz x -110 y tensor x 90, que van en la cara de afuera del riel)
TACOS_X = [20.0, 58.0]

# Zonas que la estructura NO puede ocupar (mecanismos, bandas, carro...), (x0, x1, y0, y1, z0, z1) en mm.
ZONAS_LIBRES = {
    "banda de monedas (arriba)": (-124, 101, -29.5, 29.5, 428, 456),
    "retorno de la banda de monedas": (-124, 76, -29.5, 29.5, 333, 360),
    "subida del retorno (rodillo C)": (0, 101, -29.5, 29.5, 333, 456),
    "motor de la cinta de monedas": (-131, -89, 51, 137, 420, 462),
    "almacen (carrusel, placa, tolva)": (45, 162, -130, -13, 228, 365),
    "cinta de vasos y vasos encima": (-40, 440, -140, -60, 99, 216),
    "vuelta de abajo de la banda de vasos (separadores y tacos)": (-15, 415, -140, -60, 76, 124),
    "motor de la cinta de vasos": (-21, 21, -219, -144, 90, 132),
    "tubo de tapas": (154, 246, -146, -54, 225, 300),
    "prensa": (249, 311, -131, -69, 229, 386),
    "empujador": (330, 390, -123, -55, 138, 260),
    # canaleta: la pestana del vaso (Ø78) va a la altura de los rieles (z 207 -> 132); el cuerpo (Ø62) cuelga 90 mm
    "canaleta: rieles y pestana del vaso": (321, 399, -420, -137, 120, 215),
    "canaleta: cuerpo del vaso colgando": (329, 391, -420, -137, 38, 212),
    "carro estacionado": (290, 430, -600, -410, 0, 150),
    "bandeja de monedas": (55, 145, 85, 175, 0, 36),
    "bandeja de vasos": (422, 518, -158, -42, 0, 80),
    "caja de control": (175, 535, 25, 265, 0, 80),
}

# Cargas (g) para la revision de flechas: masa que cuelga de cada tramo, repartida (config/masas.yaml y precios).
CARGAS = {   # miembro (a, b) -> gramos
    ("P1", "P2"): 900,      # almacen + 28BYJ + tubo de tapas + prensa (MG996R) + sensores colgados
    ("T2", "T3"): 500,      # mitad de la cinta de monedas + NEMA 17 (280 g)
}
E_PLA = 3500.0      # MPa (N/mm2), modulo de PLA impreso (3,0-3,6 GPa)
FLECHA_MAX = 0.6    # mm en el medio de un tramo cargado


def v(p):
    return np.array(p, float)


def unit(d):
    return d / np.linalg.norm(d)


def arriba_de(d):
    """Arriba del tubo: +z si es horizontal, +x si es vertical (en la cama da lo mismo)."""
    return np.array([0, 0, 1.0]) if abs(unit(d)[2]) < 0.9 else np.array([1.0, 0, 0])


def miembros_explicitos():
    """[(id, a, b, pasa_por, punta_libre)] con a, b nombres o puntos."""
    out = []
    for m in MIEMBROS:
        if len(m) == 3:
            a, pasa, b = m
        else:
            (a, b), pasa = m, []
        out.append((f"{a}-{b if isinstance(b, str) else 'L'}", a, b, pasa))
    return out


def punto(n):
    return v(NODOS[n]) if isinstance(n, str) else v(n)


def armar():
    """Brazos de cada nodo, tubos (con cortes y empalmes), collares, tacos y remaches."""
    brazos = {n: [] for n in NODOS}          # nodo -> [dir]
    pasantes = {n: [] for n in NODOS}        # nodo -> [dir del tubo que pasa]
    tubos, empalmes, rem = [], [], []
    for mid, a, b, pasa in miembros_explicitos():
        pa, pb = punto(a), punto(b)
        d = unit(pb - pa)
        brazos[a].append(d)
        if isinstance(b, str):
            brazos[b].append(-d)
        for n in pasa:
            pasantes[n].append(d)
        # el tubo va de fondo de cajera a fondo de cajera (o a la punta libre)
        p0 = pa + d * (BRAZO - HONDO)
        p1 = pb - d * (BRAZO - HONDO) if isinstance(b, str) else pb
        largo = float(np.linalg.norm(p1 - p0))
        k = max(1, math.ceil((largo + EMPALME - 2 * HONDO) / (LARGO_MAX + EMPALME - 2 * HONDO)))
        # tramos: los empalmes dejan 4 mm de tope entre tramo y tramo
        tramo = (largo - (k - 1) * 4.0) / k
        minimo = 2 * HONDO + 4 if isinstance(b, str) else HONDO + 10   # que se vea tubo entre nodo y nodo
        assert tramo >= minimo, f"{mid}: tramo de {tramo:.1f} mm, muy corto (los nodos estan muy cerca)"
        assert tramo <= LARGO_MAX + 0.01, f"{mid}: tramo de {tramo:.1f} mm"
        ini = p0
        for i in range(k):
            fin = ini + d * tramo
            tubos.append((f"t_{mid}_{i + 1}" if k > 1 else f"t_{mid}", ini, fin, arriba_de(d)))
            if i < k - 1:
                c = fin + d * 2.0
                empalmes.append((f"e_{mid}_{i + 1}", c, d, arriba_de(d)))
            ini = fin + d * 4.0
    return brazos, pasantes, tubos, empalmes


def remaches_de_cajera(nombre, boca, d, arr, pasante=False):
    """2 remaches por cajera, uno en cada COSTADO (+-x local), a 11 mm de la boca hacia adentro.
    Ni abajo (en los nodos del piso la cabeza quedaria contra el piso) ni arriba (sobre el tubo esta el hueco
    del alero: la una abriria ahi sin agarrar el tubo).
    boca = punto en el eje donde entra el tubo; d = hacia donde va el tubo (afuera del nodo)."""
    z = unit(d)
    y = unit(arr - np.dot(arr, z) * z)
    x = np.cross(y, z)
    c = boca - z * (HONDO / 2) - y * TOL          # el tubo apoya en el piso de la cajera: su centro 0,2 abajo
    afuera = BRAZO_ANCHO / 2
    return [(f"{nombre}_a", AGARRE, c + x * afuera, -x), (f"{nombre}_b", AGARRE, c - x * afuera, x)]


def generar():
    brazos, pasantes, tubos, empalmes = armar()
    rem = []
    nodos_out = []
    for n, p in NODOS.items():
        p = v(p)
        ds = brazos[n]
        pas = pasantes[n]
        # orientacion de impresion (techo = lo que queda arriba en la cama):
        #  - sin brazos verticales hacia los dos lados: tal cual (techo +z) o dado vuelta (techo -z);
        #  - con brazos arriba Y abajo: todos sus brazos tienen que estar en un plano, y el nodo se imprime
        #    acostado sobre ese plano (techo = la normal): asi todos los brazos quedan horizontales en la cama.
        abajo = any(d[2] < -0.9 for d in ds)
        arriba = any(d[2] > 0.9 for d in ds)
        if abajo and arriba:
            normal = next(np.cross(ds[i], ds[j]) for i in range(len(ds)) for j in range(i + 1, len(ds))
                          if np.linalg.norm(np.cross(ds[i], ds[j])) > 0.5)
            techo = unit(normal)
            assert all(abs(np.dot(d, techo)) < 1e-6 for d in ds), f"{n}: brazos arriba y abajo que no estan en un plano"
        else:
            techo = np.array([0, 0, -1.0]) if abajo else np.array([0, 0, 1.0])
        voltear = techo
        for i, d in enumerate(ds):
            arr = techo if abs(np.dot(d, techo)) < 0.9 else (np.array([1.0, 0, 0]) if abs(d[0]) < 0.9 else np.array([0, 1.0, 0]))
            rem += remaches_de_cajera(f"r_{n}_{i}", p + d * (BRAZO - HONDO), -d, arr)
        for i, d in enumerate(pas):
            # collar: 2 remaches de cada lado del nodo, en el tubo pasante
            for s in (-1, 1):
                rem += remaches_de_cajera(f"r_{n}_p{i}{'ab' if s < 0 else 'ar'}", p + d * s * (BRAZO - HONDO),
                                          -d * s, np.array([1.0, 0, 0]))
        nodos_out.append((n, p, ds, pas, voltear, n[0] in "FVCK" and abs(p[2] - Z_PISO) < 1e-6))
    for nombre, c, d, arr in empalmes:
        for s in (-1, 1):
            rem += remaches_de_cajera(f"r_{nombre}_{'ab' if s < 0 else 'ar'}", c + d * s * 2.0, -d * s, arr)
    tacos = []
    for i, x in enumerate(TACOS_X):
        # placa en la cara -y del riel y de la viga (y = Y_A - 10), de z 390 a 450, con 2 remaches en cada tubo
        tacos.append((f"taco_{i + 1}", x))
        for z, quien in ((Z_RIEL, "riel"), (Z_VIGA, "viga")):
            for dx in (-7.0, 7.0):
                cabeza = v((x + dx, Y_A - LADO / 2 - 3.0, z))
                rem.append((f"r_taco{i + 1}_{quien}_{'m' if dx < 0 else 'p'}", 3.0 + PARED, cabeza, v((0, 1.0, 0))))
    return nodos_out, tubos, empalmes, tacos, rem


def caja_de(p0, p1, ancho=LADO):
    """Caja de un prisma de seccion `ancho` a lo largo de p0-p1 (alineado con un eje o diagonal)."""
    d = p1 - p0
    lado = (1 - np.abs(unit(d) if np.linalg.norm(d) > 0 else np.zeros(3))) * ancho / 2
    if np.linalg.norm(d) == 0:
        lado = np.full(3, ancho / 2)
    return np.minimum(p0, p1) - lado, np.maximum(p0, p1) + lado


def comprobar(nodos, tubos, empalmes, tacos, rem):
    errores = []
    # tacos: su placa (x +- 15) no puede caer sobre un empalme ni un brazo de nodo del riel -y ni de la viga
    for n, x in tacos:
        for en, c, d, _ in empalmes:
            if abs(c[1] - Y_A) < 1 and abs(c[2] - Z_RIEL) < 1 or abs(c[2] - Z_VIGA) < 1 and abs(c[1] - Y_A) < 1:
                if abs(c[0] - x) < 15 + EMPALME / 2 + 3:
                    errores.append(f"{n} (x {x}) cae sobre el empalme {en} (x {c[0]:.1f})")
        for nn, p, ds, _, _, _ in nodos:
            if abs(p[1] - Y_A) < 1 and (abs(p[2] - Z_RIEL) < 1 or abs(p[2] - Z_VIGA) < 1):
                if abs(p[0] - x) < 15 + BRAZO + 3:
                    errores.append(f"{n} (x {x}) cae sobre el nodo {nn}")
    # nodos: brazos que se tocan entre nodos vecinos ya lo atrapa el assert del largo de tramo.
    # zonas libres: cada tubo y cada nodo contra cada zona
    cajas = [(t[0], *caja_de(t[1], t[2])) for t in tubos]
    for n, p, ds, pas, voltear, _ in nodos:
        for d in list(ds) + [s * d for d in pas for s in (-1, 1)] + [np.zeros(3)]:
            lo, hi = caja_de(p, p + d * BRAZO, BRAZO_ANCHO)
            if abs(np.dot(d, voltear)) < 0.9 and np.linalg.norm(d) > 0:   # el alero, del lado del techo
                lo = np.minimum(lo, lo + voltear * ALERO)
                hi = np.maximum(hi, hi + voltear * ALERO)
            cajas.append((f"nodo {n}", lo, hi))
    for nombre, (x0, x1, y0, y1, z0, z1) in ZONAS_LIBRES.items():
        zlo, zhi = v((x0, y0, z0)), v((x1, y1, z1))
        for quien, lo, hi in cajas:
            if np.all(lo < zhi) and np.all(hi > zlo):
                errores.append(f"{quien} entra en la zona libre '{nombre}'")
    # flechas por carga: viga simplemente apoyada (del lado seguro), carga repartida
    sec_i = (LADO ** 4 - (LADO - 2 * PARED) ** 4) / 12     # aprox. con hueco cuadrado (mm4)
    for (a, b), g in CARGAS.items():
        L = float(np.linalg.norm(v(NODOS[a]) - v(NODOS[b])))
        w = g * 9.81e-3 / L                                    # N/mm
        f = 5 * w * L ** 4 / (384 * E_PLA * sec_i)
        sigma = (w * L ** 2 / 8) * (LADO / 2) / sec_i
        estado = "ok" if f <= FLECHA_MAX else "FLECHA ALTA"
        print(f"  carga {a}-{b}: {g} g en {L:.0f} mm -> flecha {f:.2f} mm, esfuerzo {sigma:.1f} MPa ({estado})")
        if f > FLECHA_MAX:
            errores.append(f"{a}-{b}: flecha {f:.2f} mm > {FLECHA_MAX}")
    return errores


def masa(tubos, empalmes, nodos):
    a = 2 * (LADO / 2 - PARED)
    area_tubo = LADO ** 2 - (a ** 2 - 2 * 4.5)                       # hueco cuadrado menos 2 chaflanes de 3 mm
    largo = sum(float(np.linalg.norm(t[2] - t[1])) for t in tubos)
    g_tubos = largo * area_tubo / 1000 * PLA
    return largo, g_tubos


def marco(p0, p1, arriba):
    z = unit(p1 - p0)
    y = unit(arriba - np.dot(arriba, z) * z)
    x = np.cross(y, z)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, p0
    return m


def matriz_cama(p0, p1, arriba):
    """Del mundo a la cama para una pieza acostada: su eje queda en x y su `arriba` en +z."""
    perm = np.array([[0, 0, 1, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]])   # (x, y, z) local -> (z, x, y)
    return perm @ np.linalg.inv(marco(v(p0), v(p1), v(arriba)))


def escribir(nodos, tubos, empalmes, tacos, rem):
    f = lambda p: "[" + ", ".join(f"{c:.3f}" for c in p) + "]"
    lineas = ["// GENERADO por estructura.py: no editar a mano.", "include <comun.scad>", "",
              f"brazo_nodo = {BRAZO:.3f};", f"hondo_cajera = {HONDO:.3f};", f"pared_nodo = {PARED_NODO};",
              f"largo_empalme = {EMPALME:.3f};", ""]
    lineas.append("// [nombre, centro, [brazos], [direcciones de tubos pasantes], techo (lo de arriba en la cama), es pie]")
    lineas.append("NODOS = [")
    lineas += [f'  ["{n}", {f(p)}, [{", ".join(f(d) for d in ds)}], [{", ".join(f(d) for d in pas)}], '
               f'{f(vt)}, {"true" if pie else "false"}],' for n, p, ds, pas, vt, pie in nodos]
    lineas.append("];")
    m4 = lambda m: "[" + ", ".join(f(fila) for fila in m) + "]"
    lineas.append("// [nombre, p0, p1, arriba, matriz del mundo a la cama]")
    lineas.append("TUBOS = [")
    lineas += [f'  ["{n}", {f(a)}, {f(b)}, {f(u)}, {m4(matriz_cama(a, b, u))}],' for n, a, b, u in tubos]
    lineas.append("];")
    lineas.append("// [nombre, centro, direccion, arriba, matriz del mundo a la cama]")
    lineas.append("EMPALMES = [")
    lineas += [f'  ["{n}", {f(c)}, {f(d)}, {f(u)}, {m4(matriz_cama(c - d, c + d, u))}],' for n, c, d, u in empalmes]
    lineas.append("];")
    lineas.append(f"TACOS = [{', '.join(f'[\"{n}\", {x}]' for n, x in tacos)}];")
    lineas.append(f"Y_A = {Y_A}; Z_RIEL = {Z_RIEL}; Z_VIGA = {Z_VIGA};")
    lineas.append("// [nombre, agarre nominal, cabeza, eje]")
    lineas.append("REM_ESTRUCTURA = [")
    lineas += [f'  ["{n}", {a:.2f}, {f(c)}, {f(e)}],' for n, a, c, e in rem]
    lineas.append("];")
    (AQUI / "estructura_gen.scad").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def resumen(nodos, tubos, empalmes, tacos):
    """estructura_resumen.md: para quien monte algo sobre la estructura (los subsistemas)."""
    f = lambda q: "(" + ", ".join(f"{c:.1f}" for c in q) + ")"
    L = ["# Estructura impresa: dónde está cada cosa (GENERADO por estructura.py)", "",
         f"Tubo de {LADO:g} x {LADO:g} mm, pared {PARED:g} mm, hueco de {LADO - 2 * PARED:g} mm (con chaflanes de 3 mm",
         "arriba). Coordenadas del mundo en mm. Un remache que sujeta algo a un tubo atraviesa la pieza y UNA pared",
         f"del tubo: agarre = espesor de la pieza + {PARED:g} (+0,2 si hay holgura de encaje); la una abre dentro del",
         "hueco del tubo. No remachar a menos de 5 mm de la boca de un nodo, de un empalme ni de la punta de un tubo,",
         "ni donde ya hay un remache de la estructura (ver REM_ESTRUCTURA en estructura_gen.scad).", "",
         "## Tubos (eje de p0 a p1; la sección es un cuadrado de 16 centrado en el eje)", "",
         "| Tubo | p0 | p1 | largo |", "|---|---|---|---|"]
    L += [f"| {n} | {f(a)} | {f(b)} | {np.linalg.norm(b - a):.1f} |" for n, a, b, _ in tubos]
    L += ["", f"## Nodos (centro; cada brazo mide {BRAZO:.1f} desde el centro y {BRAZO_ANCHO:.1f} de ancho:"
          " ahí no se puede remachar ni poner nada)", "", "| Nodo | centro | brazos hacia |", "|---|---|---|"]
    L += [f"| {n} | {f(p)} | {', '.join(f(d) for d in ds)} |" for n, p, ds, _, _, _ in nodos]
    L += ["", f"## Empalmes (manguito de {EMPALME:g} mm y {BRAZO_ANCHO:.1f} de ancho centrado en el punto)", "",
          "| Empalme | centro | dirección |", "|---|---|---|"]
    L += [f"| {n} | {f(c)} | {f(d)} |" for n, c, d, _ in empalmes]
    L += ["", "## Tacos entre riel -y de monedas y viga", "", ", ".join(f"{n} en x = {x:g} (x ± 15)" for n, x in tacos), ""]
    (AQUI / "estructura_resumen.md").write_text("\n".join(L), encoding="utf-8")


def main():
    nodos, tubos, empalmes, tacos, rem = generar()
    print(f"nodos {len(nodos)}, tubos {len(tubos)}, empalmes {len(empalmes)}, tacos {len(tacos)}, remaches {len(rem)}")
    errores = comprobar(nodos, tubos, empalmes, tacos, rem)
    largo, g = masa(tubos, empalmes, nodos)
    print(f"  tubo: {largo / 1000:.2f} m, ~{g:.0f} g (sin nodos ni empalmes)")
    escribir(nodos, tubos, empalmes, tacos, rem)
    resumen(nodos, tubos, empalmes, tacos)
    for e in errores:
        print("  ERROR:", e)
    print("estructura_gen.scad", "con errores" if errores else "ok")
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
