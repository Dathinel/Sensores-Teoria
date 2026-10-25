"""Verificacion mecanica y termica de la maqueta impresa (usuario, 2026-10-24: "verifico que la deformacion del
plastico, el esfuerzo realizado y el calor generado no derrita o deforme permanentemente el plastico?").

Lo que se comprueba, con formulas de resistencia de materiales (no hay elementos finitos):
  1. Tubos cargados: esfuerzo de flexion y flecha. La viga del portico P1-P2, continua sobre P1, el puntal (x 226,
     tap_puntal_inf/_sup, 2026-10-25) y P2, con las cargas en su x: P1 y P2 como apoyos simples (el tubo entra con 0,2 de
     holgura por lado en 22 de cajera y gira libre hasta 2 x 0,2 / 22 = 0,018 rad, mas que el giro de la viga ahi; los 2
     remaches de la cajera son un pasador de eje y). Criterio: flecha elastica sostenida <= L/500 de cada tramo. Ademas,
     el asiento por holgura al armarla (manguito del empalme y punta de P2), que no es elastico: se informa aparte.
  2. Columnas: pandeo de Euler con la carga que llevan (el puntal, con la union del medio medida en sus mallas).
  3. Remaches: el MAS cargado de cada union, a cortante en el vastago o a arranque de la una (traccion), con el
     momento de la carga cuando la hay (contacto que solo empuja + remaches que solo tiran).
  4. Piezas: la seccion mas debil donde la carga las flexiona, medida CORTANDO su malla del ensamble (_cache/ens).
  5. Banda: la tension de montaje T de config/masas.yaml repartida en los rodillos segun la geometria del lazo.
  6. Cajeras de los nodos: aplastamiento del tubo contra la pared de la cajera.
  7. Calor: cada fuente que toca PLA, su potencia, la temperatura estimada y el margen contra la Tg.

PLA impreso (valores publicados para PLA FDM, con 4 perimetros, a 20-25 C):
  E = 3500 MPa; rotura 50 MPa en el plano de las capas, 30 MPa entre capas (Z);
  fluencia: a carga SOSTENIDA el PLA se deforma con el tiempo; por debajo de ~5 MPa es despreciable (ref. ensayos
  de creep de PLA impreso: < 1 % en un ano a 5 MPa y 23 C); Tg 55-60 C: desde ~45 C la fluencia se dispara y
  a 60 C se deforma con el peso propio.
Admisibles usados: corta duracion 10 MPa (SF 3 sobre la rotura entre capas); sostenida 5 MPa; la una de un remache
trabaja entre capas: 0,6 de eso; temperatura de cualquier PLA cargado <= 45 C.

Uso: python esfuerzos.py  -> esfuerzos.md y sale con 1 si algo no cumple. Necesita _cache/ens (revisar.py) y
../config/masas.yaml.
"""
import math
from pathlib import Path

import numpy as np

import estructura as E

AQUI = Path(__file__).resolve().parent
CONFIG = AQUI.parent / "config"
G = 9.81e-3                     # N por gramo
E_PLA = 3500.0                  # MPa
ADM_CORTA = 10.0                # MPa, cargas de poco tiempo (prensa, choque del carro)
ADM_SOST = 5.0                  # MPa, cargas que estan siempre (pesos colgados, tension de la banda)
T_MAX_PLA = 45.0                # C, temperatura maxima de PLA que carga algo
T_AMB = 25.0
PLA = 1.24e-3                   # g/mm3

# seccion del tubo 16 x 16, pared 1,6, hueco octogonal: chaflanes de 3 en las CUATRO esquinas (comun.scad, chaflan_hueco).
# Cortando la malla de t_P1-P2_2 da lo mismo: A 110,2 mm2, I 3758 mm4.
LADO, PARED, CHAFLAN = E.LADO, E.PARED, 3.0
_h = LADO / 2 - PARED
A_TUBO = LADO ** 2 - ((2 * _h) ** 2 - 4 * CHAFLAN ** 2 / 2)                                          # 110,2 mm2
I_TUBO = (LADO ** 4 - (2 * _h) ** 4) / 12 + 4 * (CHAFLAN ** 4 / 36 + CHAFLAN ** 2 / 2 * (_h - CHAFLAN / 3) ** 2)   # 3758 mm4
# remache: vastago O4 con caras planas a +-1,6 (3,2 de ancho) y ranura de 1,2 que lo cruza -> area de cortante
# (comun.scad; en los de agarre < 8 la ranura llega a la cabeza: toda la pata es seccion ranurada); una de 0,45 -> arranque
A_REM_CORTE = math.pi * 2 ** 2 - 2 * (4 * math.acos(0.8) - 1.6 * 1.2) - 1.2 * 3.2   # 7,42 mm2
A_REM_UNA = math.pi * 4 * 0.45 * 0.6                                          # 3.4 mm2 (la una no rodea todo)


def largo(a, b):
    return float(np.linalg.norm(np.array(E.NODOS[a], float) - np.array(E.NODOS[b], float)))


def c(v, d=2):
    """Numero con coma decimal, para el texto de esfuerzos.md."""
    return f"{v:.{d}f}".replace(".", ",")


def fila(que, carga, esfuerzo, adm, nota, largo_="-", flecha=0.0, f_adm=math.inf, sost=True):
    return dict(que=que, carga=carga, largo=largo_, esfuerzo=esfuerzo, adm=adm, flecha=flecha, sost=sost,
                ok=esfuerzo <= adm and flecha <= f_adm, nota=nota)


def malla(pieza):
    import revisar as R      # solo para leer el STL del ensamble
    ruta = R.CACHE / "ens" / f"{pieza}.stl"
    assert ruta.exists(), f"falta {ruta}: correr revisar.py antes"
    return R.ex_carro.leer_stl(ruta)


def seccion(tri, valor, eje=2):
    """Corte de la malla en coord[eje] = valor, con (u, v) las otras dos en orden ciclico (eje z: u = x, v = y).
    Green sobre los segmentos del corte, cada uno orientado con la normal de su triangulo (afuera a la derecha): no
    hace falta armar los poligonos. Devuelve A, centroide (u, v), I_u = integral (v - v0)^2 (flexion que estira a lo
    largo de v), I_v = integral (u - u0)^2 y la distancia mayor del centroide a la fibra extrema en v y en u."""
    t = np.roll(tri, -(eje + 1), axis=2)
    w = t[:, :, 2] - valor
    w = np.where(np.abs(w) < 1e-9, 1e-9, w)
    arriba = w > 0
    cruza = arriba.any(1) & ~arriba.all(1)
    t, w, arriba = t[cruza], w[cruza], arriba[cruza]
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    pts = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        corta = arriba[:, i] != arriba[:, j]
        s = np.where(corta, w[:, i] / np.where(corta, w[:, i] - w[:, j], 1), 0)
        pts.append((t[:, i, :2] + s[:, None] * (t[:, j, :2] - t[:, i, :2]), corta))
    a = np.where(pts[0][1][:, None], pts[0][0], pts[1][0])
    b = np.where(pts[0][1][:, None] & pts[1][1][:, None], pts[1][0], pts[2][0])
    d = b - a
    al_reves = d[:, 0] * n[:, 1] - d[:, 1] * n[:, 0] > 0
    a[al_reves], b[al_reves] = b[al_reves].copy(), a[al_reves].copy()
    (x1, y1), (x2, y2) = a.T, b.T
    cr = x1 * y2 - x2 * y1
    A = cr.sum() / 2
    u0, v0 = (cr * (x1 + x2)).sum() / 6 / A, (cr * (y1 + y2)).sum() / 6 / A
    Iu = (cr * (y1 ** 2 + y1 * y2 + y2 ** 2)).sum() / 12 - A * v0 ** 2
    Iv = (cr * (x1 ** 2 + x1 * x2 + x2 ** 2)).sum() / 12 - A * u0 ** 2
    p = np.vstack([a, b])
    return dict(A=A, u0=u0, v0=v0, Iu=Iu, Iv=Iv, cv=np.abs(p[:, 1] - v0).max(), cu=np.abs(p[:, 0] - u0).max())


def tension_banda():
    import yaml
    return yaml.safe_load((CONFIG / "masas.yaml").read_text(encoding="utf-8"))["comprobaciones"]["nema17"]["tension_banda_n"]


# ----------------------------------------------------------------- 1. viga del portico P1-P2
# Lo que cuelga de la viga [g] y en que x del mundo:
#  - almacen: impreso 183 (piezas.json) + comprado 95 (28BYJ, eje, 608, acople, SG90, iman) + monedas, 25 por tubo con la
#    mas pesada de cada uno (config/monedas.yaml: 4,8 / 8,0 / 7,1 / 7,4 / 10,0 / 6,0 g); cuelga de las horquillas de
#    x 78,2 y 174 (almacen.scad, r_alm_viga) y se reparte entre ellas por palanca desde el centro del carrusel (x 103,5);
#  - tapas en x 200: tubo 52 + abrazaderas 29 + colgante 13 + dedos 1 + SG90 9 + 10 tapas de 8 = 184;
#  - prensa en x 258: impresa ~88 (la placa crecio a 82 cm3) + MG996R 55 + vastago 31 + resorte 3 = 177, toda a la viga
#    (el amarre a la columna la alivia);
#  - porta del VL53L0X interior en x 41,5: 12;
#  - riel -y de monedas por los tacos (x 20 y 58): el riel (530 g, centro en x -32) apoya en T1 (x -170) y en los tacos
#    (x 39): 530 x (-32 + 170) / (39 + 170) = 350.
ALM_G = 183 + 95 + 25 * (4.8 + 8.0 + 7.1 + 7.4 + 10.0 + 6.0)
RIEL_TACOS_G = 530 * (-32 + 170) / (39 + 170)
VIGA_CARGAS = [(78.2, ALM_G * (174 - 103.5) / (174 - 78.2)), (174.0, ALM_G * (103.5 - 78.2) / (174 - 78.2)),
               (200.0, 184), (258.0, 177), (41.5, 12), (20.0, RIEL_TACOS_G / 2), (58.0, RIEL_TACOS_G / 2)]
HOLGURA_GIRO = 2 * E.TOL / E.HONDO      # giro libre del tubo en su cajera (0,018 rad)
X_EMPALME = 132.5                       # e_P1-P2_1 (estructura_resumen.md); sus pasadores a +-13 (boca 2 + 11)
X_PIN = {"P1": -28.4, "emp_P1": 119.5, "emp_P2": 145.5, "P2": 293.4}   # pasadores (REM_ESTRUCTURA: r_P1_1, r_e_P1-P2_1_*, r_P2_1)
# Puntal (tapas_prensa_empujador.scad, tap_puntal_inf / _sup): tubo 16 x 16 en x 226 del tubo del piso (cara de arriba z 18,6)
# a la viga (cara de abajo z 392), con la union del medio en z 190..220. Apoya a contacto en los dos tubos (sillas) y entre
# sus tramos; sus 5 remaches solo trabajan si tira: 2 de la silla de arriba a la viga, 1 de la de abajo al tubo del piso, 2
# de la union.
X_PUNTAL = 226.0
Z_PUNTAL = (18.6, 392.0)
Z_UNION_PUNTAL = 205.0
X_PIN_PISO = (185.5, 293.4)             # pasadores del tubo del piso t_F6-F5_2: empalme e_F6-F5_1 (sobre la mesa) y F5


def viga_portico():
    """Filas de la viga P1-P2 continua sobre P1, el puntal y P2 (cargas de siempre y la prensa), del puntal (pandeo y
    remaches), del tubo del piso bajo el puntal y de los pasadores de P2; reacciones en P1 y P2 [N] y el texto."""
    x0, L = E.NODOS["P1"][0], largo("P1", "P2")
    X = np.linspace(0, L, 3651)
    w = A_TUBO * PLA * G                                      # peso propio, N/mm
    P = [(x - x0, g * G) for x, g in VIGA_CARGAS]
    EI = E_PLA * I_TUBO

    def apoyada(a, F):          # flecha con F en a, viga simplemente apoyada en P1 y P2
        b = L - a
        return np.where(X <= a, F * b * X * (L ** 2 - b ** 2 - X ** 2), F * a * (L - X) * (L ** 2 - a ** 2 - (L - X) ** 2)) / (6 * EI * L)

    def momento(a, F):
        return F * np.where(X <= a, (L - a) * X / L, a * (L - X) / L)

    a_p = X_PUNTAL - x0
    u, mu = apoyada(a_p, 1.0), momento(a_p, 1.0)

    def con_puntal(d, M, F_total, F_mom):
        """El puntal como tercer apoyo: la reaccion R (+ = empuja hacia arriba) que deja la flecha en 0 en a_p, por
        superposicion. Devuelve R, flecha, momento y las reacciones en P1 y P2 (+ = hacia arriba)."""
        R = np.interp(a_p, X, d) / np.interp(a_p, X, u)
        r2 = (F_mom - R * a_p) / L
        return R, d - R * u, M - R * mu, F_total - R - r2, r2

    # cargas de siempre (+ = hacia abajo)
    d_ss = sum(apoyada(a, F) for a, F in P) + w * X * (L ** 3 - 2 * L * X ** 2 + X ** 3) / (24 * EI)
    M_ss = sum(momento(a, F) for a, F in P) + w * X * (L - X) / 2
    total = sum(F for _, F in P) + w * L
    R_p, d, M, r_p1, r_p2 = con_puntal(d_ss, M_ss, total, sum(F * a for a, F in P) + w * L * L / 2)
    # la prensa asentando una tapa: 60 N hacia ARRIBA en x 280 (toda a la viga, aunque el amarre a la columna se lleva parte)
    F_pr, a_pr = -60.0, 280.0 - x0
    R_pr, d_pr, M_pr, r1_pr, r2_pr = con_puntal(apoyada(a_pr, F_pr), momento(a_pr, F_pr), F_pr, F_pr * a_pr)
    tramos = [("P1-puntal", X <= a_p, a_p), ("puntal-P2", X > a_p, L - a_p)]
    cargas = ", ".join(f"{g:.0f} g en x {x:.0f}" for x, g in VIGA_CARGAS)
    filas = []
    for nom, t, Lt in tramos:
        filas.append(fila(f"tubo P1-P2, tramo {nom} (continua sobre P1, puntal y P2)", f"{total:.1f} N",
                          np.abs(M[t]).max() * (LADO / 2) / I_TUBO, ADM_SOST,
                          f"cargas en su x ({cargas}) + peso propio; P1 y P2 apoyos simples (giro {abs(np.gradient(d, X)[0]):.4f} "
                          f"y {abs(np.gradient(d, X)[-1]):.4f} rad, menos que el libre de la cajera, {HOLGURA_GIRO:.4f}); "
                          f"flecha mayor en x {X[t][np.abs(d[t]).argmax()] + x0:.0f}, admisible L/500 = {Lt / 500:.2f} mm",
                          f"{Lt:.0f} mm", np.abs(d[t]).max(), Lt / 500))
    t_pr = max(tramos, key=lambda tr: np.abs(d_pr[tr[1]]).max())
    filas.append(fila("tubo P1-P2 con la prensa (continua sobre P1, puntal y P2)", f"{-F_pr:.1f} N", np.abs(M + M_pr).max() * (LADO / 2) / I_TUBO,
                      ADM_CORTA, f"la prensa asentando una tapa: {-F_pr:.0f} N hacia arriba en x 280, toda a la viga, sumada a las "
                      f"cargas de siempre; flecha de la prensa sola {np.abs(d_pr).max():.2f} mm en x {X[np.abs(d_pr).argmax()] + x0:.0f} "
                      f"(tramo {t_pr[0]}), admisible L/200 = {t_pr[2] / 200:.2f} mm (vuelve al soltar)",
                      f"{t_pr[2]:.0f} mm", np.abs(d_pr).max(), t_pr[2] / 200, sost=False))
    # puntal: columna con las cargas de siempre (compresion). La union del medio es la seccion mas debil: las dos medias
    # (maciza del tramo de abajo y caja del de arriba) medidas en sus mallas y sumadas SIN trabajar juntas (cota baja de I)
    Lp = Z_PUNTAL[1] - Z_PUNTAL[0]
    s = [seccion(malla(n), Z_UNION_PUNTAL) for n in ("tap_puntal_inf", "tap_puntal_sup")]
    A_u, I_u = sum(x["A"] for x in s), min(sum(x["Iu"] for x in s), sum(x["Iv"] for x in s))
    F_suelta = R_p / (R_pr / F_pr)            # fuerza de la prensa con la que el puntal deja de estar comprimido
    tira = -(R_p + R_pr)                       # traccion del puntal con la prensa a 60 N (si sale > 0)
    pu = pandeo("puntal tap_puntal_inf/_sup (x 226)", Lp, R_p, 1.0,
                f"reaccion de la viga continua (las cargas de siempre); I {I_u:.0f} mm4 de la union del medio (z {Z_UNION_PUNTAL:.0f}, "
                f"{A_u:.0f} mm2: las dos medias sin trabajar juntas) en todo el largo, en vez de {I_TUBO:.0f} del tubo. Comprimido "
                f"hasta {F_suelta:.0f} N de prensa; con {-F_pr:.0f} tira {max(tira, 0):.1f} N", A=A_u, I=I_u)
    filas.append(pu)
    # remaches del puntal: solo si tira. El mas cargado es el unico de la silla de abajo (los de arriba y los de la union van de a 2)
    filas.append(fila("remaches: puntal (el de la silla de abajo, solo)", f"{max(tira, 0):.1f} N", max(tira, 0) / A_REM_CORTE, ADM_CORTA,
                      f"a compresion el puntal apoya a contacto (sillas y union); tira solo con mas de {F_suelta:.0f} N de prensa: "
                      f"con {-F_pr:.0f} N, {max(tira, 0):.1f} N a cortante en r_tap_punt_inf_1 (los otros 4 van de a 2) (corte)", sost=False))
    # tubo del piso bajo el puntal: carga puntual entre sus pasadores (empalme sobre la mesa y F5)
    Lf = X_PIN_PISO[1] - X_PIN_PISO[0]
    af = min(X_PUNTAL - X_PIN_PISO[0], X_PIN_PISO[1] - X_PUNTAL)
    filas.append(fila("tubo F6-F5 bajo el puntal", f"{R_p:.1f} N", R_p * af * (Lf - af) / Lf * (LADO / 2) / I_TUBO, ADM_SOST,
                      f"el puntal apoya en x {X_PUNTAL:.0f}: viga apoyada entre los pasadores del empalme e_F6-F5_1 (x 185,5, sobre la "
                      f"mesa) y de F5 (x 293,4); flecha admisible L/500 = {Lf / 500:.2f} mm", f"{Lf:.0f} mm",
                      R_p * af * (Lf ** 2 - af ** 2) ** 1.5 / (9 * math.sqrt(3) * EI * Lf), Lf / 500))
    # P2 ahora SUJETA la viga hacia abajo (la viga gira sobre el puntal): sus 2 remaches r_P2_1 a cortante. Con la prensa, la
    # peor de las dos cotas: puntal sin holgura (superposicion) o puntal flojo (la viga apoyada en P1 y P2, como sin puntal)
    baja_p2 = max(-(r_p2 + r2_pr), F_pr * a_pr / L * -1 - (sum(F * a for a, F in P) + w * L * L / 2) / L)
    filas.append(fila("remaches: cajera P2 sujetando la viga hacia abajo", f"{baja_p2 / 2:.1f} N c/u (2)", baja_p2 / 2 / A_REM_CORTE, ADM_CORTA,
                      f"con el puntal P2 tira de la viga hacia abajo: {-r_p2:.1f} N siempre, hasta {baja_p2:.1f} N con la prensa (la peor "
                      "de: puntal firme, o puntal flojo y la viga apoyada en P1 y P2) (corte)", sost=False))

    # asiento por holgura (no es elastico, no crece con el tiempo: se informa aparte). El tramo P2 de la viga queda entre el
    # puntal (a contacto) y el pasador de P2; el manguito del empalme gira sobre su pasador del lado del puntal (x 145,5) lo que
    # deja su cajera. Si la punta de P2 sube lo que dejan su cajera y los agujeros de r_P2_1 (2 x 0,2: P2 ahora sujeta hacia
    # abajo), la viga gira sobre el puntal y el empalme baja mas.
    as_emp = HOLGURA_GIRO * (X_PIN["emp_P2"] - X_PIN["emp_P1"])
    giro_p2 = 2 * E.TOL / (X_PIN["P2"] - X_PUNTAL)
    as_p2 = giro_p2 * (X_PUNTAL - X_PIN["emp_P2"])
    as_peor = as_p2 + (giro_p2 + HOLGURA_GIRO) * (X_PIN["emp_P2"] - X_PIN["emp_P1"])
    sin_puntal = d_ss.max()

    def en(x, a):                # cuanto baja x (en el tramo P1-empalme) si el pasador del empalme baja a
        return a * (x - X_PIN["P1"]) / (X_PIN["emp_P1"] - X_PIN["P1"])
    f1 = filas[0]
    texto = [f"**Viga del pórtico P1-P2.** Lleva {c(total, 1)} N en total y desde el 2026-10-25 un puntal en x {X_PUNTAL:.0f} "
             f"(tap_puntal_inf / _sup: tubo 16 × 16 del tubo del piso F6-F5 a la cara de abajo de la viga). Sin él, apoyada en P1 y "
             f"P2, flectaba **{c(sin_puntal)} mm** en x {X[d_ss.argmax()] + x0:.0f} contra {c(L / 500)} admisibles. Continua sobre "
             f"P1, el puntal y P2 la flecha mayor es **{c(f1['flecha'])} mm** en el tramo P1-puntal ({a_p:.0f} mm, admite "
             f"{c(a_p / 500)}) y {c(filas[1]['flecha'], 3)} mm en el tramo puntal-P2 ({L - a_p:.0f} mm, admite {c((L - a_p) / 500)}); "
             f"el esfuerzo mayor, {c(max(f1['esfuerzo'], filas[1]['esfuerzo']))} MPa. El puntal toma {c(R_p, 1)} N, P1 "
             f"{c(r_p1, 1)} N y P2 {c(r_p2, 1)} N: la viga gira sobre el puntal y P2 la **sujeta hacia abajo** (sus 2 remaches "
             "a cortante). P1 y P2 siguen como apoyos simples: el giro de la viga ahí no llega al libre de la cajera.",
             f"**Prensa.** Sus {-F_pr:.0f} N hacia arriba en x 280 los toman el puntal ({c(-R_pr, 1)} N, tirando), P2 "
             f"({c(-r2_pr, 1)} N) y P1 ({c(r1_pr, 1)} N). El puntal sigue comprimido (a contacto, sin holgura) mientras la prensa no "
             f"pase de {F_suelta:.0f} N; con {-F_pr:.0f} N tira {c(max(tira, 0), 1)} N y la holgura de sus remaches (agujero 4,4 "
             "para 4) puede abrirse: la prensa pierde parte del apriete de 0,5 solo por encima de "
             f"{F_suelta:.0f} N. Sin el puntal, P2 cargaba {c((sum(F * a for a, F in P) + w * L * L / 2) / L, 1)} N y la prensa "
             f"levantaba la punta de la viga en su cajera desde "
             f"{(sum(F * a for a, F in P) + w * L * L / 2) / L / (-F_pr * a_pr / L) * -F_pr:.0f} N.",
             f"**Asiento por holgura (al armarla; no es elástico ni crece con el tiempo).** Antes, P1, el empalme e_P1-P2_1 y P2 eran "
             f"pasadores en línea y el empalme podía bajar {c(HOLGURA_GIRO * (X_EMPALME - x0), 1)} mm. Ahora el tubo t_P1-P2_2 queda "
             f"entre el puntal (a contacto) y el pasador de P2, y el manguito gira sobre su pasador del lado del puntal (x 145,5) lo "
             f"que deja su cajera: {c(HOLGURA_GIRO, 4)} × 26 = **{c(as_emp)} mm** en el pasador de x 119,5 (con la holgura nominal; "
             f"con lo que encogen las cajeras al imprimir, menos). Como P2 sujeta hacia abajo, si su punta sube lo que dejan la "
             f"cajera y los agujeros de r_P2_1 (2 × 0,2) la viga gira sobre el puntal y el empalme baja {c(as_p2)} mm más: en el "
             f"peor caso **{c(as_peor)} mm** en x 119,5, que en el tramo P1-empalme queda en {c(en(78.2, as_peor))} mm en la "
             f"horquilla del almacén (x 78,2) y {c(en(58, as_peor))} / {c(en(20, as_peor))} mm en los tacos del riel (x 58 / 20). "
             f"El tubo t_P1-P2_2 solo gira con la punta de P2: en el peor caso baja {c(giro_p2 * (X_PUNTAL - 200))} mm en x 200 "
             f"(tapas) y sube {c(giro_p2 * (280 - X_PUNTAL))} en x 280 (prensa; desde el ensamble, con el tubo centrado en la "
             f"cajera, la mitad: {c(giro_p2 * (280 - X_PUNTAL) / 2)} de los 0,5 de apriete). El puntal se monta con la viga "
             "levantada a mano en x 226 hasta que quede recta: así la deja en su lugar y no se suma la flecha que ya tenía."]
    return filas, r_p1, r_p2, texto


# ----------------------------------------------------------------- tubos en flexion (el resto)
# (miembro, carga [N], tipo: "rep" repartida o "pun" puntual en a mm del apoyo, sostenida?, de donde sale la carga)
VIGAS = [
    ("T2-T3", 530 * G, ("rep", None), True, "riel +y de monedas: mitad de la cinta + NEMA 17 (280 g) + jaula"),
    ("T1-L", 530 * G, ("rep", None), True, "riel -y de monedas: mitad de la cinta + compuerta E4 + FC-51"),
    ("M1-M2", 0.64 * 0.12 ** 2 / 2 / 0.003 * 1.0, ("pun", 52.0), False,
     "tope del muelle: carro de 0,64 kg a 0,12 m/s frenado en 3 mm de espuma (F = m v^2 / 2 d = 1,5 N)"),
    ("Q2-L", 110 * G, ("pun", 55.0), True, "brazo de la camara cenital: webcam + anillo (110 g) en la punta (voladizo de 55 mm)"),
]


def flexion(miembro, F, carga, sostenida, nota):
    a_, b_ = miembro.split("-")
    L = largo(a_, b_) if b_ != "L" else {"T1": 276.0, "Q2": 55.0}[a_]      # puntas libres: largo del voladizo/tramo
    tipo, a = carga
    if miembro == "Q2-L":                     # voladizo empotrado en el nodo
        M = F * L
        d = F * L ** 3 / (3 * E_PLA * I_TUBO)
    elif tipo == "rep":
        w = F / L
        M = w * L ** 2 / 8
        d = 5 * w * L ** 4 / (384 * E_PLA * I_TUBO)
    else:
        b = L - a
        M = F * a * b / L
        c = min(a, b)                       # flecha maxima de una viga apoyada con carga descentrada (c = tramo corto)
        d = F * c * (L ** 2 - c ** 2) ** 1.5 / (9 * math.sqrt(3) * E_PLA * I_TUBO * L)
    sigma = M * (LADO / 2) / I_TUBO
    # flecha admisible: L/500 si la carga esta siempre, L/200 si es momentanea (vuelve al descargar); voladizo L/100
    f_adm = L / 100 if miembro == "Q2-L" else (L / 500 if sostenida else L / 200)
    return fila(f"tubo {miembro}", f"{F:.1f} N", sigma, ADM_SOST if sostenida else ADM_CORTA,
                f"{nota}; flecha admisible {f_adm:.1f} mm", f"{L:.0f} mm", d, f_adm, sostenida)


# ----------------------------------------------------------------- 2. columnas (pandeo)
def pandeo(miembro, L, P, K, nota, A=A_TUBO, I=I_TUBO):
    """P > 0 comprime; P <= 0 es traccion (no pandea: solo el esfuerzo)."""
    pcr = math.pi ** 2 * E_PLA * I / (K * L) ** 2
    sigma = abs(P) / A
    return dict(que=f"columna {miembro}", carga=f"{abs(P):.1f} N" + (" (tracción)" if P < 0 else ""), largo=f"{L:.0f} mm",
                esfuerzo=sigma, adm=ADM_SOST, sost=True, flecha=0.0, ok=(P <= 0 or P * 3 <= pcr) and sigma <= ADM_SOST,
                nota=f"{nota}; " + ("a traccion: no pandea" if P <= 0 else f"pandeo critico {pcr:.0f} N (SF {pcr / P:.0f})"))


VIGA_FILAS, R_P1, R_P2, VIGA_TEXTO = viga_portico()
# (miembro, largo, carga axial [N], K de pandeo, nota[, A, I]). K = 1 si arriba esta amarrada a una viga (patas de la
# mesa de monedas, columnas del portico); K = 2 si la punta queda libre (postes). La prensa NO carga las columnas: empuja
# la tapa hacia abajo y su reaccion tira de la viga hacia ARRIBA (las alivia).
COLUMNAS = [
    ("F2-T2", 430.0, (1060 + 280) / 3 * G, 1.0, "pata de la mesa de monedas: un tercio de la cinta y el NEMA"),
    ("F4-P1", 400.0, R_P1, 1.0, "columna del portico: su reaccion de la viga continua sobre el puntal"),
    # con el puntal P2 sujeta la viga hacia abajo (R_P2 < 0): la columna tira, menos el empujador que cuelga de ella
    ("F5-P2", 400.0, R_P2 + 200 * G, 1.0, "columna del portico, lado +x: su reaccion de la viga (que ahora tira de ella hacia "
     "arriba) y el empujador (MG996R y paleta)"),
    ("V2-L", 110.0, 1400 / 4 * G, 2.0, "poste de la cinta de vasos (un cuarto del bastidor con 5 vasos llenos), punta libre"),
    ("C1-L", 170.0, 250 / 4 * G, 2.0, "poste de la canaleta, punta libre"),
]


# ----------------------------------------------------------------- 5. banda (antes que los remaches: los carga)
# Rodillos de la cinta de monedas (x, z), todos O22 (cinta_monedas.scad: mon_x_mot, mon_x_ten, mon_z_rod, mon_ret). Con el
# mismo radio cada tramo de banda es paralelo a la recta entre centros y el rodillo recibe T por cada ramal:
# R = T (u_hacia_el_anterior + u_hacia_el_siguiente). El lazo es el casco de los centros (sentido horario en x-z).
# (El retorno C, en (65; 418,8), quedaba 6,3 mm dentro del lazo y no tocaba la banda: se quito, 2026-10-25.)
RODILLOS = {"motriz": (-110, 439), "tensor": (90, 439), "B": (11, 344), "A": (-113, 344)}
LAZO = ["motriz", "tensor", "B", "A"]
QUIEN = {"motriz": "bloques del motriz (con A: se anulan en z)", "tensor": "bloques del tensor (tornillo de empuje)",
         "B": "colgantes b_m (taco_1) y b_p (labio)", "A": "bajadas de los bloques del motriz"}


def banda():
    """Resultante por rodillo, en unidades de T: {rodillo: (Rx, Rz)}."""
    p = {k: np.array(v, float) for k, v in RODILLOS.items()}
    R = {}
    for i, k in enumerate(LAZO):
        a, b = p[LAZO[i - 1]] - p[k], p[LAZO[(i + 1) % len(LAZO)]] - p[k]
        R[k] = a / np.linalg.norm(a) + b / np.linalg.norm(b)
    return R


def grupo(F, p, rems):
    """Cortante del remache mas cargado de un grupo en el plano de F (x, z) aplicado en p: F/n + el momento repartido
    por la distancia al centroide del grupo (metodo elastico)."""
    F, p, rems = np.array(F, float), np.array(p, float), np.array(rems, float)
    c = rems.mean(0)
    r = rems - c
    M = (p - c)[0] * F[1] - (p - c)[1] * F[0]
    f = F / len(rems) + M * np.c_[-r[:, 1], r[:, 0]] / (r ** 2).sum()
    return np.linalg.norm(f, axis=1).max()


def uniones_banda(T):
    """Filas de lo que carga la tension de la banda, en las dos cintas, y la tabla de resultantes."""
    R = banda()
    filas = []
    # motriz + A sobre los bloques mon_rod_mot_m y mon_jaula_nema (cinta_monedas.scad): la z de A (+1,00 T) y la del
    # motriz (-1,00 T) se anulan en el bloque; queda x, que toman a cortante sus 2 remaches de abajo (x -124 / -96). El
    # momento de esa x (a 96 bajo el riel) y el del NEMA colgado (a 76 del riel) lo cierran los labios de arriba y de
    # abajo apoyados en el riel (C que lo abraza): los remaches no trabajan a traccion.
    F = (R["motriz"] + R["A"]) * T / 2
    filas.append(fila("remaches: bloques del motriz al riel (banda)", f"{np.linalg.norm(F) / 2:.1f} N c/u (2 por bloque)",
                      np.linalg.norm(F) / 2 / A_REM_CORTE, ADM_SOST,
                      f"por bloque {np.round(F, 1).tolist()} N (motriz + retorno A, T = {T:.0f} N); el momento lo toman "
                      "los labios sobre y bajo el riel (corte)"))
    # bajada del retorno A en mon_rod_mot_m: su raiz en z 426 (seccion medida en la malla), A en (-113, 344)
    s = seccion(malla("mon_rod_mot_m"), 425.5)
    FA = R["A"] * T / 2
    r = np.array(RODILLOS["A"], float) - (s["u0"], 426.0)
    M = abs(r[0] * FA[1] - r[1] * FA[0])
    filas.append(fila("bajada del retorno A (raiz en z 426)", f"{np.round(FA, 1).tolist()} N",
                      M * s["cu"] / s["Iv"] + abs(FA[1]) / s["A"], ADM_SOST,
                      f"seccion medida en mon_rod_mot_m: {s['A']:.0f} mm2, I {s['Iv']:.0f} mm4; momento {M:.0f} N mm. Se "
                      "imprime sobre la cara -x: la flexion estira en el plano de las capas"))
    # tensor: el M3 de empuje toma la x del 608 (mon_ten_tor: entra a 12 grados de la vertical y toca el aro a 21,4 grados
    # del eje x con el 608 en 90, la posicion de trabajo); los 2 remaches de cada bloque la pasan al riel a cortante
    Fx = abs(R["tensor"][0]) * T / 2
    filas.append(fila("remaches: bloques del tensor al riel (banda)", f"{Fx / 2:.1f} N c/u (2 por bloque)", Fx / 2 / A_REM_CORTE,
                      ADM_SOST, "la x del rodillo tensor; su z (hacia abajo) apoya el labio en el riel (corte)"))
    n = np.array([math.cos(math.radians(21.4)), -math.sin(math.radians(21.4))])
    d = np.array([math.sin(math.radians(12)), -math.cos(math.radians(12))])
    N = Fx / n[0]
    axial, lateral = N * n @ d, N * math.sqrt(1 - (n @ d) ** 2)
    rosca = 8.6                                    # mm de rosca en el PLA (agujero O2,6, MEDIR)
    filas.append(fila("rosca del M3 de empuje del tensor de monedas", f"{axial:.1f} N axial, {lateral:.1f} N lateral",
                      max(axial / (math.pi * 3 * rosca / 2), lateral / (3 * rosca)), ADM_SOST,
                      f"autorroscante en {rosca} mm de PLA: corte en la rosca y apoyo del costado; empuja el 608 con {N:.1f} N"))
    # B: el rodillo (y -29,5..29,5) apoya en b_m (placa en y -31) y b_p (por fuera del riel +y, y 50): palanca
    FB = R["B"] * T * 50 / (50 + 31)
    filas.append(fila("remaches: colgante b_m del retorno B al taco_1 (banda)", f"{grupo(FB, RODILLOS['B'], [(14, 414), (26, 426)]):.1f} N",
                      grupo(FB, RODILLOS["B"], [(14, 414), (26, 426)]) / A_REM_CORTE, ADM_SOST,
                      f"{np.round(FB, 1).tolist()} N en el eje de B, 2 remaches de costado a 17 mm; b_p apoya su labio en el "
                      "riel (sin traccion) (corte)"))
    # cinta de vasos: 2 rodillos en x 0 y 400, los dos ramales paralelos: 2 T por rodillo, T por lateral
    filas.append(fila("rosca del prisionero M3 del tensor de vasos", f"{T:.1f} N por lateral", T / (math.pi * 3 * 5.8 / 2), ADM_SOST,
                      "el prisionero empuja el 608 de x 400 hasta el fin de la corredera; rosca de 5,8 mm en el PLA (O2,5, MEDIR)"))
    filas.append(pandeo("lateral de la cinta de vasos (4 x 48)", 120.0, T, 1.0,
                        "la banda junta los dos rodillos con 2 T: T por lateral; tramo libre mas largo, del ultimo remache a la "
                        "bancada (x 280) al rodillo de x 400", A=4 * 48, I=48 * 4 ** 3 / 12))
    tabla = [(k, np.linalg.norm(R[k]), np.linalg.norm(R[k]) * T, QUIEN[k]) for k in ("motriz", "tensor", "A", "B")]
    return filas, tabla


# ----------------------------------------------------------------- 3. remaches por union
def placa_prensa(F=60.0):
    """Placa de la prensa (tapas_prensa_empujador.scad): la reaccion de la prensa sube por el eje (280, -100), 51,3 delante
    de la cara de atras de la placa (y -48,7). Remaches: la placa gira sobre su borde de arriba (z 406) contra la viga y el
    momento lo toman a traccion los 3 de z 400 y los 4 de la columna (x 315, z 265/288/308/345), cada uno con su brazo.
    Placa: se imprime de pie, asi que la flexion de sus secciones horizontales tira ENTRE capas; la mas debil entre el
    servo (z 349,35) y la viga (z 392), cortando la malla, con la reaccion entera aunque parte va a la columna."""
    d = [406 - z for z in (400, 400, 400, 265, 288, 308, 345)]
    t_max = F * 51.3 * max(d) / sum(x * x for x in d)
    tri = malla("tap_pre_placa")
    z, s = min(((z, seccion(tri, z)) for z in np.arange(349.5, 392.0, 0.25)), key=lambda t: t[1]["Iu"])
    sigma = F / s["A"] + F * abs(s["v0"] + 100) * s["cv"] / s["Iu"] + F * abs(280 - s["u0"]) * s["cu"] / s["Iv"]
    return [fila("remaches: placa de la prensa a la viga y a la columna", f"{t_max:.1f} N (el mas cargado de 7)", t_max / A_REM_UNA,
                 ADM_CORTA * 0.6, f"{F:.0f} N de prensa: M = F x 51,3 repartido como F x 51,3 x d / suma d2, d = 406 - z; cortante "
                 f"F/7 = {F / 7:.1f} N (traccion)", sost=False),
            fila(f"placa de la prensa, entre capas (z {z:.1f})", f"{F:.0f} N", sigma, ADM_CORTA,
                 f"seccion mas debil medida en _cache/ens/tap_pre_placa.stl: {s['A']:.0f} mm2, I {s['Iu']:.0f} mm4 fuera del "
                 f"plano (centroide en y {s['v0']:.1f}) e {s['Iv']:.0f} en el plano; flexion de los dos lados + axial", sost=False)]


def colgante_tapas():
    """tap_colgante: el ala va bajo la viga (y -52,7..-32,7) con 2 remaches verticales en y -40,5. El peso W cuelga en el eje
    del tubo de tapas (y -100): el ala gira sobre su borde +y (y -32,7) y los remaches tiran con brazo 7,8."""
    W = 184 * G
    t = W * (100 - 32.7) / (2 * (40.5 - 32.7))
    return fila("remaches: colgante del tubo de tapas a la viga", f"{t:.1f} N c/u (2)", t / A_REM_UNA, ADM_SOST * 0.6,
                f"tubo + abrazaderas + colgante + dedos + SG90 + 10 tapas (184 g) en y -100, pivote en el borde +y del ala "
                "(traccion)")


def nema_vasos():
    """NEMA de vasos (290 g con el acople): cara en y -185,5 (separadores de 3), cuerpo hasta -225,5, centro en -205,5,
    61 afuera de la cara de la lateral (y -144,5). Cuelga de vas_placa_motor (y -182,5..-177,5), remachada a 4 postes de
    la lateral (x +-25, z 96 / 126). Remaches: la placa gira sobre la fila de abajo y tiran los 2 de arriba (brazo 30);
    postes: el momento en su raiz, con la seccion de los 4 medida cortando vas_lat_s_a en y -150."""
    W = 290 * G
    t = W * (205.5 - 177.5) / (2 * 30)
    s = seccion(malla("vas_lat_s_a"), -150.0, eje=1)          # u = z, v = x
    sigma = W * (205.5 - 144.5) * s["cu"] / s["Iv"]
    return [fila("remaches: placa del motor de vasos a sus postes", f"{t:.1f} N c/u (2 de arriba)", t / A_REM_UNA, ADM_SOST * 0.6,
                 "momento del NEMA (centro 28 detras de la placa) (traccion)"),
            fila("postes del NEMA de vasos (raiz en la lateral)", f"{W:.1f} N", sigma, ADM_SOST,
                 f"momento {W * 61:.0f} N mm (centro del NEMA a 61 de la lateral); los 4 postes de 32,8: {s['A']:.0f} mm2, "
                 f"I {s['Iv']:.0f} mm4 en z")]


# (union, remaches, fuerza en el MAS cargado [N], en cortante o en traccion (arranque de la una), sostenida, nota)
REMACHES = [
    ("puente del almacen a la viga", 6, ALM_G * G / 6, "corte", True,
     f"almacen impreso + comprado + monedas ({ALM_G:.0f} g): cuelga de 6 remaches en cortante"),
    ("laterales de vasos a los postes", 8, 1400 * G / 8, "corte", True, "bastidor con banda, motor y 5 vasos llenos (133 g c/u)"),
    ("bancada de monedas a los rieles", 6, 400 * G / 6, "corte", True, "6 remaches de costado a la cara interior de los rieles"),
    ("cabezales de la canaleta a los postes", 8, (55 + 4 * 133) * G / 8, "corte", True, "varillas con 4 vasos llenos"),
    ("tubo en su cajera (cualquier nodo)", 2, 1400 / 4 * G / 2, "corte", True, "el poste mas cargado: un cuarto del bastidor de vasos"),
    ("topes del muelle a M1-M2", 2, 1.5 / 2, "corte", False, "choque del carro (1,5 N)"),
]


def remache(union, n, F, modo, sostenida, nota):
    area = A_REM_CORTE if modo == "corte" else A_REM_UNA
    adm = (ADM_SOST if sostenida else ADM_CORTA) * (1.0 if modo == "corte" else 0.6)   # la una trabaja entre capas
    return fila(f"remaches: {union}", f"{F:.1f} N c/u ({n})", F / area, adm, f"{nota} ({modo})", sost=sostenida)


# ----------------------------------------------------------------- 6. aplastamiento en la cajera
def cajera():
    # el tubo apoya en el piso de la cajera (16 x 22 mm) con la carga del poste mas cargado + el momento del riel
    F = 1400 / 4 * G + 60
    return fila("cajera del nodo (aplastamiento)", f"{F:.1f} N", F / (LADO * E.HONDO), ADM_SOST,
                "tubo apoyado en el piso de la cajera, 2,4 mm de pared alrededor", "16 x 22 mm")


# ----------------------------------------------------------------- 7. calor
# (fuente, potencia media [W], potencia pico [W], Rth a ambiente [C/W], toca PLA?, que PLA toca, mitigacion)
# NEMA 17: con micropaso el A4988 regula 1 A por fase: I^2 R = 1^2 x 1,5 ohm = 1,5 W, y CONTINUOS mientras la linea anda
# (el firmware suelta el ENABLE a los a4988_reposo_ms = 3000 de config/parametros.yaml, mas que las pausas de 1000-1400 ms:
# firmware/fijo/hw.py:136-160). Rth de un NEMA 17 al aire ~7 C/W (hoja: 80 C de subida a 11 W).
# Panel de luz: 2 tiras 2835 de 20 LED a 20 mA = 0,8 A x 5 V = 4 W sin nada en serie; el circuito (sim/electrica.py,
# panel_luz) le pone una resistencia de 3,3 ohm 1 W en linea, del lado de la caja, que lo deja en ~1,4 W en las tiras (no
# un MOSFET con PWM: el ESP32 fijo no tiene GPIO libres y el PCA9685 va a 50 Hz). Anillo de la camara cenital: 0,35 A x
# 5 V = 1,75 W (CARGAS["anillo"]).
import sys                                                                         # noqa: E402
sys.path.insert(0, str(AQUI.parent))
from sim.electrica import PANEL_R_SERIE, PANEL_P_MAX_W, panel_luz                  # noqa: E402
P_PANEL = panel_luz()["p_tiras"]
CALOR = [
    ("NEMA 17 de cada cinta (17HS4401 a 1 A/fase)", 1.5, 1.5, 7.0, True, "mon_jaula_nema / vas_placa_motor",
     "la brida NO toca la placa: 4 separadores de nailon de 3 mm en los M3 (aire entre medio). Prueba de banco con un "
     "termometro en la carcasa (manual, «Antes de encender»): si pasa de 45 C, bajar Vref a 0,8 A (o esas dos piezas en PETG)"),
    ("28BYJ-48 (5 V, medio paso: 0,1-0,2 A)", 0.15 * 5 * 0.3, 0.15 * 5 * 0.3, 25.0, True, "alm_puente (pestanas del motor)",
     "ninguna: la carcasa queda tibia (~35 C)"),
    ("SG90 (desvio, obturador, tapas, escape)", 0.2, 0.2, 30.0, True, "bridas y cunas impresas", "ninguna"),
    ("MG996R de la prensa (0,2 s trabado cada ciclo)", 0.4, 0.4, 15.0, True, "tap_pre_placa (costillas)",
     "ninguna mientras la prensa no quede trabada: el firmware la suelta a los 200 ms (tiempos_ms); trabado 15 W lo "
     "quemaria a el antes que al PLA"),
    ("MG996R del empujador", 0.3, 0.3, 15.0, True, "tap_emp_placa_servo", "ninguna"),
    ("tira LED del panel de luz (5 V, 2 tramos) con resistencia en serie, sobre cinta de aluminio", P_PANEL,
     P_PANEL, 10.0, True, "vas_panel_a/_b (marco de 1,6 mm)",
     f"OBLIGATORIO: la resistencia de {c(PANEL_R_SERIE, 1)} Ω 1 W en línea en el +5 V (del lado de la caja, lejos del PLA) y "
     "la tira sobre cinta de aluminio pegada al marco (reparte el calor). Sin la resistencia (4 W) y pegada al PLA llega a "
     f"~65 C. Prueba (manual, «Antes de encender»): I × V_tiras ≤ {c(PANEL_P_MAX_W, 1)} W; se esperan "
     f"~{c(panel_luz()['i'])} A con ~{c(panel_luz()['v_tiras'], 1)} V en las tiras; si pasa, 4,7 Ω"),
    ("anillo LED de la camara cenital (en la webcam)", 1.75, 1.75, 15.0, False,
     "ninguno directo: rodea el lente (z ~602) y la abrazadera mon_camara agarra la carcasa por arriba (z 639 a 689)",
     "medir la abrazadera con el termometro en la prueba de banco; si pasa de 45 C, el anillo tambien con una resistencia "
     "en serie, en linea del lado de la caja"),
    ("fuente, bucks, A4988, ESP32, ventilador", 9.0, 9.0, 0.0, False, "nada: van en la caja de control (acrilico y aluminio)",
     "ninguna"),
]


def calor(fuente, p_med, p_pico, rth, pla, toca, mit):
    t_med = T_AMB + p_med * rth
    t_pico = T_AMB + p_pico * rth          # a plena potencia / al 100 % (prueba de banco continua)
    return dict(que=fuente, p=f"{p_med:.2f} W" + (f" / {p_pico:.1f} W pleno" if p_pico != p_med else ""),
                t=f"{t_med:.0f} °C" + (f" / {t_pico:.0f} °C pleno" if p_pico != p_med else "") + ("" if pla else " (no toca PLA)"),
                ok=not pla or t_med <= T_MAX_PLA, ok_continuo=not pla or t_pico <= T_MAX_PLA, toca=toca, mit=mit)


def main():
    s = seccion(malla("t_P1-P2_2"), 200.0, eje=0)      # control del corte de mallas: el tubo tiene que dar la formula
    assert abs(s["A"] / A_TUBO - 1) < 0.01 and abs(s["Iu"] / I_TUBO - 1) < 0.01, f"el corte no da la seccion del tubo: {s}"
    T = tension_banda()
    f_banda, tabla_banda = uniones_banda(T)
    filas = (VIGA_FILAS + [flexion(*v) for v in VIGAS] + [pandeo(*c) for c in COLUMNAS] + [colgante_tapas()] + placa_prensa()
             + [remache(*r) for r in REMACHES] + f_banda + nema_vasos() + [cajera()])
    termicas = [calor(*c) for c in CALOR]
    malos = [f for f in filas if not f["ok"]] + [t for t in termicas if not t["ok"]]
    L = ["# Esfuerzos, deformación y calor en la maqueta impresa (GENERADO por esfuerzos.py)", "",
         f"PLA impreso: E = {E_PLA:.0f} MPa, admisible {ADM_CORTA:.0f} MPa en cargas cortas y {ADM_SOST:.0f} MPa en cargas que están "
         f"siempre (por fluencia); la uña de un remache, 0,6 de eso (trabaja entre capas); ningún PLA que cargue algo por encima de "
         f"{T_MAX_PLA:.0f} °C (Tg 55-60 °C). Modelos de resistencia de materiales, no elementos finitos; las secciones de piezas "
         "se miden cortando su malla del ensamble (_cache/ens). Tubo 16 × 16 pared 1,6 con hueco octogonal: "
         f"A = {c(A_TUBO, 1)} mm², I = {I_TUBO:.0f} mm⁴. Tensión de la banda T = {T:.0f} N por ramal (config/masas.yaml, "
         "PROVISIONAL: se mide al montar).", "",
         f"**Resultado: {'todo cumple' if not malos else 'NO todo cumple: ' + ', '.join(f['que'] for f in malos)}.**", "",
         "## Mecánica", "", "| Qué | Carga | Largo | Esfuerzo (MPa) | Admisible | Flecha (mm) | ¿Cumple? | De dónde sale |",
         "|---|---|---|---:|---:|---:|---|---|"]
    L += [f"| {f['que']} | {f['carga']} | {f['largo']} | {f['esfuerzo']:.2f} | {f['adm']:.0f} | {f['flecha']:.2f} | "
          f"{'sí' if f['ok'] else 'NO'} | {f['nota']} |" for f in filas]
    peor = max(filas, key=lambda f: f["esfuerzo"] / f["adm"])
    sost = max((f for f in filas if f["sost"]), key=lambda f: f["esfuerzo"] / f["adm"])
    L += ["", f"El esfuerzo más exigido es **{peor['que']}**: {c(peor['esfuerzo'])} MPa de {c(peor['adm'], 1)} admisibles "
          f"(factor {c(peor['adm'] / peor['esfuerzo'], 1)} sobre el admisible, que ya lleva factor 3 sobre la rotura entre capas).", ""]
    L += [t + "\n" for t in VIGA_TEXTO]
    L += [f"**Deformación permanente (fluencia):** la carga sostenida más exigida es {sost['que']}, {c(sost['esfuerzo'])} MPa de "
          f"{c(sost['adm'], 1)}: " + ("todas quedan por debajo del umbral en que el PLA impreso fluye de forma medible a temperatura "
                                    "ambiente." if sost["esfuerzo"] <= sost["adm"] else "PASA el umbral de fluencia."), "",
          f"**Banda de monedas** (rodillos de cinta_monedas.scad, T = {T:.0f} N): cada rodillo recibe T por ramal, en la "
          "bisectriz de los dos tramos.", "", "| Rodillo | Resultante (× T) | Con T (N) | La toma |", "|---|---:|---:|---|"]
    L += [f"| {k} | {r:.2f} | {n:.1f} | {q} |" for k, r, n, q in tabla_banda]
    L += ["", "La de vasos (rodillos en x 0 y 400) junta los dos rodillos con 2 T: T en cada prisionero del tensor y T de "
          "compresión en cada lateral. Con el tensor a tope, la T real sale del largo del empalme de la banda: se mide con una "
          "balanza de gancho en un ramal (manual).", "",
          "## Calor", "", "| Fuente | Potencia | Temperatura estimada | ¿Cumple? | Qué PLA toca | Qué hacer |", "|---|---|---|---|---|---|"]
    L += [f"| {t['que']} | {t['p']} | {t['t']} | {'sí' if t['ok'] else 'NO'}{'' if t['ok_continuo'] else ' (a plena potencia: NO)'} | "
          f"{t['toca']} | {t['mit']} |" for t in termicas]
    L += ["", "**Puntos calientes.** El NEMA 17 disipa 1,5 W (I²R con micropaso) todo el tiempo que la línea anda, porque el "
          "firmware no suelta los A4988 en las pausas: la carcasa queda en ~36 °C, debajo del límite, pero igual no apoya en el "
          "PLA (separadores de nailon de 3 mm) y se mide en la prueba de banco: si pasa de 45 °C, Vref a 0,8 A (la cinta sobra "
          "par: margen ×10 y ×2,2 en peso.md). El panel de luz pide 4 W sin nada en serie (0,8 A a 5 V): pegado al marco de "
          "1,6 llegaría a ~65 °C, más que la Tg. Por eso va con una resistencia de "
          f"{c(PANEL_R_SERIE, 1)} Ω 1 W en línea en su +5 V, del lado de la caja (sim/electrica.py, docs/electrica.md): las "
          f"tiras quedan en {c(P_PANEL)} W (~{T_AMB + P_PANEL * 10:.0f} °C) sobre cinta de aluminio, y la resistencia "
          f"disipa {c(panel_luz()['p_resistencia'])} W fuera del PLA. No va un MOSFET con PWM.", "",
          "## Lo que NO cubre", "",
          "- No es un análisis por elementos finitos: cada pieza se redujo a su modelo de viga, columna, sección o unión más simple.",
          "- La torsión de la viga del pórtico por lo que cuelga delante (almacén, tapas y prensa a 31-60 mm del eje): con nodos "
          "rígidos la viga gira ~0,4-0,5° (pórtico 3D de la auditoría del 2026-10-25) y la holgura de las cajeras suma giro "
          "(las paredes de la silla de arriba del puntal la frenan en x 226).",
          "- El asiento por holgura sale de la holgura nominal (0,2 por lado en las cajeras y en los agujeros de los remaches); "
          "el real depende de cómo quede armada. El puntal se toma como apoyo rígido (se acorta 0,02 mm y el tubo del piso "
          "baja 0,04 bajo él) y sin cargas de costado.",
          "- Las cargas son las de config/masas.yaml, config/monedas.yaml y piezas.json (estimadas: pesar al armar); T de la "
          "banda es la de montaje (medirla), sin la diferencia de tensión que suma el par del motor.",
          "- Los valores del PLA son los publicados para piezas impresas con 4 perímetros a 20-25 °C; el filamento húmedo o "
          "las capas mal pegadas bajan la resistencia entre capas (por eso el factor 3). El arranque real de la uña no está medido.",
          "- Las temperaturas son estimadas con resistencias térmicas típicas; hay que MEDIR la carcasa del NEMA 17 y el panel."]
    (AQUI / "esfuerzos.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    for f in filas:
        print(f"{'ok ' if f['ok'] else 'MAL'} {f['que'][:60]:60s} {f['esfuerzo']:6.2f} / {f['adm']:.1f} MPa  flecha {f['flecha']:.2f} mm")
    for t in termicas:
        print(f"{'ok ' if t['ok'] else 'MAL'} {t['que'][:60]:60s} {t['t']}")
    print("esfuerzos.md:", "con problemas" if malos else "todo cumple")
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(main())
