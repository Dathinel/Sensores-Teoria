"""Prueba del revisor con errores puestos a proposito (usuario, 2026-10-24: "mande mas pruebas de errores por si
acaso se le pasaron mas cosas").

Un revisor que nunca se vio fallar no prueba nada: cada caso mete UN error conocido y exige que revisar.py (o
estructura.py, voladizos.py, primera_capa.py, auditar.py) lo atrape; los casos "bueno" exigen que NO marque nada (para
que no grite por todo). Hay al menos un caso malo y uno bueno por cada revision (2026-10-25: faltaban la primera capa,
las fases, los remaches contra lo que se mueve, la cache, listas(), auditar, remache contra remache...).
Usa las piezas ya dibujadas en _cache/ (correr antes: python revisar.py) y no escribe nada fuera de carpetas temporales
(salvo un STL de prueba en _cache/ens que borra al terminar).

Uso: python probar_revisor.py   -> tabla de casos y sale con 1 si alguno no dio lo esperado.
"""
import subprocess
import tempfile
from pathlib import Path

import numpy as np

import auditar as A
import estructura as est
import primera_capa as PC
import revisar as R
from revisar import CACHE, ex_carro

resultados = []


def caso(nombre, detecto, esperado=True):
    ok = bool(detecto) == esperado
    resultados.append((nombre, ok, detecto))
    print(f"{'ok ' if ok else 'FALLA'}  {nombre:66s} -> {str(detecto)[:150] if detecto else 'no marca nada'}")


def stl_de(codigo, carpeta=None):
    t = Path(carpeta) if carpeta else Path(tempfile.mkdtemp())
    (t / "p.scad").write_text("$fn = 40;\n" + codigo)
    subprocess.run([str(R.OPENSCAD), "-o", str(t / "p.stl"), str(t / "p.scad")], capture_output=True)
    return t / "p.stl"


def tri_de(codigo):
    return ex_carro.leer_stl(stl_de(codigo))


# ----------------------------------------------------------------- mallas hechas a mano (sin OpenSCAD)
def caja_malla(lo, hi):
    """Malla cerrada de una caja (12 triangulos, normales hacia afuera)."""
    lo, hi = np.array(lo, float), np.array(hi, float)
    v = np.array([[lo[0] if i & 1 == 0 else hi[0], lo[1] if i & 2 == 0 else hi[1], lo[2] if i & 4 == 0 else hi[2]] for i in range(8)])
    f = [(0, 2, 1), (1, 2, 3), (4, 5, 6), (5, 7, 6), (0, 1, 4), (1, 5, 4), (2, 6, 3), (3, 6, 7), (0, 4, 2), (2, 4, 6), (1, 3, 5), (3, 7, 5)]
    return v[np.array(f)]


def placa_con_agujero(lo, hi, c=(0, 0), r=2.2, n=24):
    """Placa (caja de lo a hi) con un agujero pasante en z de radio r en c (x, y), como malla cerrada."""
    lo, hi = np.array(lo, float), np.array(hi, float)
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    circ = np.c_[c[0] + r * np.cos(ang), c[1] + r * np.sin(ang)]

    def borde(p):
        d = p - np.array(c)
        t = min(((hi[0] if d[0] > 0 else lo[0]) - c[0]) / d[0] if abs(d[0]) > 1e-12 else np.inf,
                ((hi[1] if d[1] > 0 else lo[1]) - c[1]) / d[1] if abs(d[1]) > 1e-12 else np.inf)
        return np.array(c) + d * t
    ext = np.array([borde(p) for p in circ])
    p3 = lambda q, z: np.array([q[0], q[1], z])
    tri = []
    for i in range(n):
        j = (i + 1) % n
        for z, s in ((lo[2], -1), (hi[2], 1)):
            q = [p3(circ[i], z), p3(ext[i], z), p3(ext[j], z), p3(circ[j], z)]
            t1, t2 = (q[0], q[1], q[2]), (q[0], q[2], q[3])
            tri += [t1, t2] if s > 0 else [t1[::-1], t2[::-1]]
        tri += [(p3(circ[i], lo[2]), p3(circ[j], hi[2]), p3(circ[j], lo[2])), (p3(circ[i], lo[2]), p3(circ[i], hi[2]), p3(circ[j], hi[2]))]
        tri += [(p3(ext[i], lo[2]), p3(ext[j], lo[2]), p3(ext[j], hi[2])), (p3(ext[i], lo[2]), p3(ext[j], hi[2]), p3(ext[i], hi[2]))]
    return np.array(tri)


def rem_a_mano(mallas, agarre, cab=(0, 0, 100.0), eje=(0, 0, 1.0)):
    """revisar_remaches de UN remache contra mallas hechas a mano (placas a z 100: la cabeza no toca el piso)."""
    cajas = {n: R.caja(m) for n, m in mallas.items()}
    m = R.revisar_remaches([("r_prueba", agarre, np.array(cab, float), np.array(eje, float))], mallas, cajas)
    return m[0][1] if m else []


def main():
    piezas, rem, _ = R.listas()
    mallas = {n: ex_carro.leer_stl(CACHE / "ens" / f"{n}.stl") for n in piezas + R.COMPRADOS if (CACHE / "ens" / f"{n}.stl").exists()}
    mallas = {n: m for n, m in mallas.items() if len(m)}
    cajas = {n: R.caja(m) for n, m in mallas.items()}
    rr = lambda r: (R.revisar_remaches([r], mallas, cajas) or [(None, [])])[0][1]
    lateral = next(r for r in rem if r[0].startswith("r_F1_"))
    taco = next(r for r in rem if "taco" in r[0])
    nodo_T3 = np.array(est.NODOS["T3"], float)
    ag = lateral[1]
    assert abs(ag - 4.4) < 1e-6, f"el remache de nodo deberia ser de 4,4 (AGARRE), es de {ag}"

    print("== remaches (la pila del nodo mide 4,2: pared 2,4 + 0,2 + tubo 1,6; el agarre es 4,4) ==")
    caso("bueno: remache lateral de un nodo (agarre 4,4, sale en 4,2)", rr(lateral), False)
    caso("bueno: remache de un taco", rr(taco), False)
    caso("agarre mas largo que lo que junta (6 en vez de 4,4)", rr((lateral[0], 6.0, lateral[2], lateral[3])))
    caso("agarre mas corto (3): la una queda adentro de la pared", rr((lateral[0], 3.0, lateral[2], lateral[3])))
    print("   tolerancia asimetrica: la cara de salida (4,2) de agarre - 0,3 a agarre + 0,15")
    caso("agarre 4,0: sale 0,2 mas alla, el hombro de la una queda adentro", rr((lateral[0], 4.0, lateral[2], lateral[3])))
    caso("bueno: agarre 4,1 (sale 0,1 mas alla)", rr((lateral[0], 4.1, lateral[2], lateral[3])), False)
    caso("bueno: agarre 4,45 (0,25 de juego)", rr((lateral[0], 4.45, lateral[2], lateral[3])), False)
    caso("agarre 4,55 (0,35 de juego)", rr((lateral[0], 4.55, lateral[2], lateral[3])))
    caso("remache en el aire (no agarra nada)", rr((lateral[0], ag, lateral[2] + np.array([0, 0, 300.0]), lateral[3])))
    caso("al reves: cabeza adentro del tubo", rr((lateral[0], ag, lateral[2] + lateral[3] * 4.2, -lateral[3])))
    caso("agarre de 30 (se dobla al meterlo)", rr((lateral[0], 30.0, lateral[2], lateral[3])))
    caso("cabeza contra el piso (nodo del piso, desde abajo)",
         rr(("x", ag, np.array([-170 + 22, -40.5, 0.0]), np.array([0, 0, 1.0]))))
    caso("cabeza enterrada 1 mm en la pared", rr((lateral[0], ag, lateral[2] + lateral[3] * 1.0, lateral[3])))
    caso("cabeza corrida 3 mm afuera de la cara (no apoya)", rr((lateral[0], ag, lateral[2] - lateral[3] * 3.0, lateral[3])))
    # agujero ciego: por la placa del taco hacia el bloque macizo del medio (z entre riel y viga)
    x_taco = est.TACOS_X[0]
    cab = np.array([x_taco, est.Y_A - 8 - 3.0, (est.Z_RIEL + est.Z_VIGA) / 2])
    caso("agujero ciego (sale a un bloque macizo, la una no abre)", rr(("x", 3.0, cab, np.array([0, 1.0, 0]))))
    caso("eje torcido 90 grados (a lo largo de la pared)", rr((lateral[0], ag, lateral[2], np.array([0, 0, 1.0]))))
    caso("sale pegado a otra pieza (sin hueco para la una)",
         rr(("x", ag, nodo_T3 + np.array([0, 0, est.BRAZO + 30]), np.array([0, 0, -1.0]))))

    print("== remaches a mano: placa de 4 + 0,2 + placa de 1,6 a z 100, agarre 5,8 ==")
    P = lambda z0, z1, c=(0, 0), r=2.2, x1=20.0: placa_con_agujero((-20, -20, 100 + z0), (x1, 20, 100 + z1), c, r)
    buenas = {"a": P(0, 4), "b": P(4.2, 5.8)}
    caso("bueno: las dos placas, agarre 5,8", rem_a_mano(buenas, 5.8), False)
    caso("eje a 1,0 mm del canto (agujero abierto de costado)", rem_a_mano({"a": P(0, 4, x1=1.0), "b": P(4.2, 5.8, x1=1.0)}, 5.8))
    caso("cabeza 0,5 mm en el aire con el agarre que incluye ese aire",
         rem_a_mano({"a": P(0.5, 4.5), "b": P(4.7, 6.3)}, 6.3))
    caso("nervio de 1 mm bajo la cabeza, entre los puntos viejos",
         rem_a_mano(dict(buenas, nervio=caja_malla((-1.4, -2.4, 98.4), (1.4, -1.4, 100))), 5.8))
    caso("tapa con agujero de 6,4 a 6 mm detras de la cabeza (no pasa)", rem_a_mano(dict(buenas, tapa=P(-8, -6, r=3.2)), 5.8))
    caso("bueno: tapa con agujero de 10 a 6 mm detras de la cabeza", rem_a_mano(dict(buenas, tapa=P(-8, -6, r=5.0)), 5.8), False)
    caso("bloque macizo detras, del lado de una pata", rem_a_mano(dict(buenas, bloque=caja_malla((-10, 0.6, 105.8), (10, 10, 112))), 5.8))

    print("== peor pata: r_tap_colg viejo (y -37,5, 3 mm del eje del tubo: una pata sobre el chaflan del hueco) ==")
    # en la viga de hoy, con su agujero agregado, en x 200 y 225 (entre y lejos de los r_tap_colg de hoy, x 187,5 y 212,5)
    viga = "t_P1-P2_2"
    viejos = [("r_tap_colg_1_viejo", 5.8, np.array([200.0, -37.5, 387.8]), np.array([0, 0, 1.0])),
              ("r_tap_colg_bueno", 5.8, np.array([225.0, -40.5, 387.8]), np.array([0, 0, 1.0]))]
    with tempfile.TemporaryDirectory() as t:
        o = Path(t) / "viga.stl"
        R.scad(o, codigo=f'difference() {{ pieza("{viga}"); for (r = [{", ".join(R.rem_scad(r) for r in viejos)}]) agujero_rem_en(r); }}')
        tubo = ex_carro.leer_stl(o)
    placa = lambda c: placa_con_agujero((c[0] - 10, -48, 387.8), (c[0] + 10, -33, 391.8), c[:2])
    for r, esperado, txt in ((viejos[0], True, "r_tap_colg_1 viejo: la pata -x sale en 7,75 y el hombro esta en 6,0"),
                             (viejos[1], False, "bueno: el mismo remache sobre el eje del tubo (y -40,5)")):
        m = {viga: tubo, "colgante": placa(r[2])}
        malos = R.revisar_remaches([r], m, {n: R.caja(v) for n, v in m.items()})
        caso(txt, malos[0][1] if malos else [], esperado)

    print("== remache contra remache ==")
    a = ("r_a", 5.8, np.array([0, 0, 100.0]), np.array([0, 0, 1.0]))      # eje z: el largo de la cabeza va en y
    caso("dos cabezas a 6 mm con el largo alineado", R.remaches_entre_si([a, ("r_b", 5.8, np.array([0, 6.0, 100.0]), np.array([0, 0, 1.0]))]))
    caso("bueno: dos cabezas a 10 mm", R.remaches_entre_si([a, ("r_b", 5.8, np.array([0, 10.0, 100.0]), np.array([0, 0, 1.0]))]), False)

    print("== listas(): un REM mal formado no se puede perder ==")
    eco = 'ECHO: PIEZA = "x"\nECHO: REM = ["r_bueno", 4.4, [0, 0, 0], [0, 0, 1]]\n'
    for txt, esperado, nombre in ((eco, False, "bueno: REM bien formado"),
                                  (eco + 'ECHO: REM = ["r_malo", undef, [0, 0, 0], [0, 0, 1]]\n', True, "REM con agarre undef"),
                                  (eco + 'ECHO: REM = ["r_exp", 4.4, [1e+06, 0, 0], [0, 0, 1]]\n', False, "bueno: REM con 1e+06 (no es undef)")):
        guardar = (R.MOVILES, R.SINCRONOS)
        try:
            R.leer_listas(txt); err = None
        except AssertionError as e:
            err = str(e)
        R.MOVILES, R.SINCRONOS = guardar
        caso(nombre, err, esperado)

    print("== orden de armado (la estructura se remacha antes que los subsistemas) ==")
    est_tapado = next((r for r in rem if r[0] == "r_M1_0_b"), None)
    if est_tapado is not None:
        caso("bueno: remache de la estructura tapado por una pieza que se monta despues", rr(est_tapado), False)
    sub_rem = next((r for r in rem if r[0].startswith("r_mon_")), None)
    caso("remache de un subsistema al reves (cabeza adentro de la pieza)",
         rr((sub_rem[0], sub_rem[1], sub_rem[2] + sub_rem[3] / np.linalg.norm(sub_rem[3]) * sub_rem[1], -sub_rem[3])))
    caso("remache de un subsistema con agarre mal (+1 mm)", rr((sub_rem[0], sub_rem[1] + 1.0, sub_rem[2], sub_rem[3])))

    print("== choques (piezas fijas: > 1 mm3; lo que se mueve: > 0,05 mm3; OpenSCAD que falla = MAL) ==")
    tri = mallas["t_F1-F4"]
    for nombre, desp, esperado in (("bueno: copia corrida 30 mm (no se tocan)", 30.0, False),
                                   ("bueno: copia a 0,3 mm (holgura de encaje)", 16.3, False),
                                   ("copia montada 2 mm", 14.0, True), ("copia en el mismo lugar", 0.0, True)):
        b = CACHE / "ens" / "_prueba_copia.stl"
        ex_carro.escribir_stl(b, tri + np.array([0, 0, desp]))
        cajas2 = {"t_F1-F4": R.caja(tri), "_prueba_copia": R.caja(tri + np.array([0, 0, desp]))}
        malos, _ = R.choques(["t_F1-F4", "_prueba_copia"], cajas2)
        caso(nombre, malos, esperado)
        b.unlink()
    a_ = CACHE / "ens" / "_prueba_a.stl"
    b_ = CACHE / "ens" / "_prueba_b.stl"
    ex_carro.escribir_stl(a_, tri_de("cube(10);"))
    ex_carro.escribir_stl(b_, tri_de("translate([9.7, 0, 0]) cube([10, 3, 1]);"))     # se meten 0,3 x 3 x 1 = 0,9 mm3
    cj = {n: R.caja(ex_carro.leer_stl(CACHE / "ens" / f"{n}.stl")) for n in ("_prueba_a", "_prueba_b")}
    caso("bueno: 0,9 mm3 entre piezas fijas (bajo el umbral de 1)", R.choques(["_prueba_a", "_prueba_b"], cj)[0], False)
    caso("0,9 mm3 al moverse (roza)", R.choques(["_prueba_a", "_prueba_b"], cj, umbral=R.UMBRAL_MOVIL)[0])
    b_.unlink()
    cj["_prueba_b"] = cj["_prueba_a"]
    caso("el otro STL no esta (no cuenta como 0 mm3)", R.choques(["_prueba_a", "_prueba_b"], cj)[0])
    a_.unlink()

    print("== barridos (lo que se mueve) ==")
    viga = next(n for n in mallas if n.startswith("t_P1-P2"))
    tri_v = mallas[viga]
    for nombre, desp, esperado in (("barrido que pasa por adentro de la viga", (0, 0, 0), True),
                                   ("bueno: barrido 40 mm debajo de la viga", (0, 0, -40), False)):
        lo, hi = R.caja(tri_v)
        c = (lo + hi) / 2 + np.array(desp)
        caja_b = tri_de(f"translate([{c[0]},{c[1]},{c[2]}]) cube([30, 30, 10], center = true);")
        ex_carro.escribir_stl(CACHE / "ens" / "~barrido~prueba.stl", caja_b)
        cajas_b = dict(cajas)
        cajas_b["~barrido~prueba"] = R.caja(caja_b)
        malos, _ = R.choques(["~barrido~prueba", viga], cajas_b, solo_con="~barrido~prueba", umbral=R.UMBRAL_MOVIL)
        caso(nombre, malos, esperado)
        (CACHE / "ens" / "~barrido~prueba.stl").unlink(missing_ok=True)
    caso("bueno: hay barridos declarados y salieron en la lista (no undef)", not R.MOVILES, False)

    print("== remaches contra lo que se mueve ==")
    r_suelto = ("r_prueba", 5.8, np.array([0, 0, 100.0]), np.array([0, 0, 1.0]))
    with tempfile.TemporaryDirectory() as t:
        barr = Path(t) / "barrido.stl"
        for nombre, centro, grupo, esperado in (
                ("un remache dentro del barrido (no va con lo que se mueve)", (0, 0, 104), [], True),
                ("bueno: el barrido 20 mm al lado del remache", (25, 0, 104), [], False),
                ("bueno: el remache va con lo que se mueve (atraviesa su pieza)", (0, 0, 104), [placa_con_agujero((-10, -10, 100), (10, 10, 104))], False)):
            ex_carro.escribir_stl(barr, caja_malla(np.array(centro) - 5, np.array(centro) + 5))
            incl, vol = R.remaches_contra_barrido(barr, grupo, [r_suelto])
            caso(nombre, (vol is None or vol > R.UMBRAL_MOVIL) and f"{vol} mm3 con {incl}", esperado)

    print("== mecanismos fase por fase ==")
    caso("lado 1 vacio (no se dibujo)", R.juzgar_fase("x", 0, R.medir_fase("cube(10);", "")))
    caso("los dos lados se meten 5 mm", R.juzgar_fase("x", 0, R.medir_fase("cube(10);", "translate([5, 0, 0]) cube(10);")))
    caso("bueno: los dos lados apenas se tocan (cara con cara)", R.juzgar_fase("x", 0, R.medir_fase("cube(10);", "translate([10, 0, 0]) cube(10);")), False)
    caso("OpenSCAD falla (modulo que no existe)", R.juzgar_fase("x", 0, R.medir_fase("cube(10);", "no_existe();")))
    if R.SINCRONOS:
        n0 = R.SINCRONOS[0][0]
        caso(f"nombre de mecanismo mal escrito ({n0}x)", R.revisar_fases([(n0 + "x", 0)])[0])
        caso(f"bueno: {n0} paso 0 tal cual", R.revisar_fases([(n0, 0)])[0], False)
    print("   que se toquen (CONTACTOS: el lado 1 corrido 0,6 hacia el lado 0 se tiene que meter)")
    hacia = R.D_TOQUE * np.array([-1.0, 0, 0])
    caso("bueno: a 0,3 de tocarse (lo que deja can_fase a proposito)",
         R.juzgar_fase("x", 0, R.medir_fase("cube(10);", "translate([10.3, 0, 0]) cube(10);", hacia)), False)
    caso("a 2 mm: no se tocan (el vaso lejos del dedo)", R.juzgar_fase("x", 0, R.medir_fase("cube(10);", "translate([12, 0, 0]) cube(10);", hacia)))
    caso("a 0,3 pero corrido al otro lado (direccion al reves)",
         R.juzgar_fase("x", 0, R.medir_fase("cube(10);", "translate([10.3, 0, 0]) cube(10);", -hacia)))
    if "tap_prensa" in dict(R.SINCRONOS):
        sube = R.D_TOQUE * np.array(R.CONTACTOS["tap_prensa"][1])
        caso("bueno: la leva toca el rodillo (tap_prensa, paso 0)",
             R.juzgar_fase("tap_prensa", 0, R.medir_fase('fase("tap_prensa", 0, 0);', 'fase("tap_prensa", 0, 1);', sube)), False)
        caso("el rodillo 2 mm debajo de la leva (no la sigue)",
             R.juzgar_fase("tap_prensa", 0, R.medir_fase('fase("tap_prensa", 0, 0);', 'translate([0, 0, -2]) fase("tap_prensa", 0, 1);', sube)))

    print("== lo que se mueve dentro de su barrido (RECORRIDOS, extremos incluidos) ==")
    barr = CACHE / "barr" / "_prueba.stl"
    cubo, placa = "translate([20 * f, 0, 100]) cube(10);", "translate([20 * f, 0, 100]) cube([1.5, 10, 10]);"   # de x 0 a 20
    try:
        for nombre, recorrido, barrido, esperado in (
                ("bueno: barrido hecho con hull de punta a punta", cubo, "hull() for (x = [0, 20]) translate([x, 0, 100]) cube(10);", False),
                ("barrido que termina antes del final (x 15 de 20)", cubo, "hull() for (x = [0, 15]) translate([x, 0, 100]) cube(10);", True),
                ("barrido de copias sueltas cada 10 (aire entre copias)", placa, "for (x = [0, 10, 20]) translate([x, 0, 100]) cube([1.5, 10, 10]);", True)):
            R.RECORRIDOS["_prueba"] = recorrido
            R.scad(barr, codigo=barrido)
            caso(nombre, R.revisar_recorridos([("_prueba", [])], [])[0], esperado)
    finally:
        del R.RECORRIDOS["_prueba"]
        barr.unlink(missing_ok=True)
        R.sello(barr).unlink(missing_ok=True)

    print("== _cache vieja (cada STL lleva la huella de los .scad con que se dibujo) ==")
    prueba = CACHE / "ens" / "_prueba_cache.stl"
    try:
        R.scad(prueba, codigo="cube(1);")
        caso("bueno: recien dibujado", R.viejos([prueba]), False)
        R.sello(prueba).write_text("otra huella")
        caso("dibujado con otros .scad", R.viejos([prueba]))
        R.sello(prueba).unlink()
        caso("sin huella (de antes de este control)", R.viejos([prueba]))
        caso("no esta", R.viejos([CACHE / "ens" / "_no_existe.stl"]))
    finally:
        prueba.unlink(missing_ok=True)
        R.sello(prueba).unlink(missing_ok=True)
    caso("bueno: _cache de la maqueta al dia (si falla: correr python revisar.py)", R.viejos(R.rutas_cache(piezas, True)), False)

    print("== sin soportes (voladizos.py) ==")
    H = lambda hueco: f"difference() {{ cube([40, 20, 40]); translate([20, -1, 18]) rotate([-90, 0, 0]) {hueco} }}"
    for nombre, codigo, esperado in (
            ("bueno: cubo", "cube(20);", False),
            ("bueno: techo a 45 grados", "hull() { cube([20,20,1]); translate([0,0,15]) cube([20,35,1]); }", False),
            ("voladizo: T con ala de 20 mm en el aire", "cube([10,10,20]); translate([-20,0,20]) cube([50,10,4]);", True),
            ("T con alas de 25 sobre una base de la misma pieza", "cube([60, 10, 3]); translate([25, 0, 0]) cube([10, 10, 40]); translate([0, 0, 40]) cube([60, 10, 4]);", True),
            ("puente de 25 mm", "difference() { cube([35,10,20]); translate([5,-1,-1]) cube([25,12,15]); }", True),
            ("bueno: puente de 10 mm", "difference() { cube([20,10,20]); translate([5,-1,-1]) cube([10,12,15]); }", False),
            ("voladizo a 60 grados de la vertical", "hull() { cube([20,10,1]); translate([0,0,10]) cube([20+17.3,10,1]); }", True),
            ("bandera de 3 x 30 al aire, apoyada en una punta", "cube([10, 16, 50]); translate([10, 0, 40]) cube([30, 3, 16]);", True),
            ("perno de 6 en voladizo de 20", "cube([10, 20, 20]); translate([10, 10, 10]) rotate([0, 90, 0]) cylinder(d = 6, h = 20);", True),
            ("bueno: labio de 2 colgado de su pared a todo lo largo", "cube([60, 10, 20]); translate([0, 10, 18]) cube([60, 2, 2]);", False),
            ("bueno: rosca de pie (filetes colgados del nucleo)", "for (i=[0:30]) translate([0,0,i]) cylinder(d1=6, d2=4.8, h=0.6, $fn=24); cylinder(d=4.8, h=31, $fn=24);", False),
            ("agujero horizontal de 20 sin gota", H("cylinder(d = 20, h = 22);"), True),
            ("bueno: agujero horizontal de 12", H("cylinder(d = 12, h = 22);"), False),
            ("bueno: agujero horizontal de 20 con gota", H("hull() { cylinder(d = 20, h = 22); translate([0, -14.14, 0]) cylinder(d = 0.1, h = 22); }"), False),
            ("bueno: ranura de 5 agujeros de 9 cada 1 mm", "difference() { cube([40, 20, 40]); for (x = [16:1:20]) translate([x, -1, 18]) rotate([-90, 0, 0]) cylinder(d = 9, h = 22); }", False)):
        caso(nombre, R.revisar_cama(tri_de(codigo))[0], esperado)
    # capa por capa (2026-10-25, segunda opinion): todas las caras a 35-45 grados, el criterio de las caras no las ve
    print("   capa por capa: nada nace en el aire ni cuelga de una punta (caras a <= 45 grados)")
    V = lambda x0, largo, y=20, z=20: f"translate([{x0}, {y}, {z}]) rotate([45, 0, 0]) translate([0, -3, -3]) cube([{largo}, 6, 6]);"   # poste en V
    for nombre, codigo, esperado in (
            ("placa a 38 grados que nace en el aire a 20 mm del resto (mon_e4)",
             "cube([10, 30, 50]); hull() { translate([30, 0, 20]) cube([0.01, 30, 0.01]); translate([8.4, 0, 48]) cube([1.6, 30, 2]); }", True),
            ("bueno: la misma placa con una pared debajo de su canto",
             "cube([10, 30, 50]); hull() { translate([30, 0, 20]) cube([0.01, 30, 0.01]); translate([8.4, 0, 48]) cube([1.6, 30, 2]); } translate([29, 0, 0]) cube([1.6, 30, 20.5]);", False),
            ("punta de un cono a 45 grados que nace en un punto (tap_pre_placa)",
             "cube([6, 30, 50]); translate([20, 15, 20]) cylinder(r1 = 0, r2 = 15, h = 15);", True),
            ("poste en V de 30 colgado de una pared (vas_lat_s_a)", "cube([5, 40, 40]); " + V(5, 30), True),
            ("bueno: el mismo poste con un nervio de 1,6 hasta la cama", "cube([5, 40, 40]); " + V(5, 30) + " translate([5, 19.2, 0]) cube([30, 1.6, 17]);", False),
            ("bueno: poste en V de 4 (colgado de su pared, <= 5)", "cube([5, 40, 40]); " + V(5, 4), False),
            ("V de 30 entre dos paredes (puente de 30: la cumbrera de mon_e4)", "cube([5, 40, 40]); translate([35, 0, 0]) cube([5, 40, 40]); " + V(4, 32), True),
            ("bueno: V de 10 entre dos paredes (puente de 10)", "cube([5, 40, 40]); translate([15, 0, 0]) cube([5, 40, 40]); " + V(4, 12), False)):
        caso(nombre, R.revisar_cama(tri_de(codigo))[0], esperado)
    # la excepcion de voladizos.PUENTES_ACEPTADOS (mon_e4), probada con una pieza de prueba: el puente sale en z 15,9
    puente30 = tri_de("cube([5, 40, 40]); translate([35, 0, 0]) cube([5, 40, 40]); " + V(4, 32))
    R.volad.PUENTES_ACEPTADOS["prueba"] = dict(largo=30.5, z=(15.3, 16.5))
    try:
        caso("bueno: el puente de 30 aceptado a mano en su altura", R.revisar_cama(puente30, "prueba")[0], False)
        caso("el mismo puente en otra pieza (no aceptado)", R.revisar_cama(puente30, "mon_e3")[0])
        caso("puente de 40 (mas largo que lo aceptado)",
             R.revisar_cama(tri_de("cube([5, 40, 40]); translate([45, 0, 0]) cube([5, 40, 40]); " + V(4, 42)), "prueba")[0])
        R.volad.PUENTES_ACEPTADOS["prueba"] = dict(largo=30.5, z=(40, 41))
        caso("el puente de 30 a otra altura que la aceptada", R.revisar_cama(puente30, "prueba")[0])
    finally:
        del R.volad.PUENTES_ACEPTADOS["prueba"]

    print("== cama ==")
    caso("pieza de 300 mm (no cabe)", R.revisar_cama(tri_de("cube([300, 20, 10]);"))[0])
    caso("bueno: pieza de 200 mm", R.revisar_cama(tri_de("cube([200, 20, 10]);"))[0], False)

    print("== primera capa: islas, agujeros chicos y la base ==")
    for nombre, codigo, esperado in (
            ("bueno: placa maciza", "cube([60, 40, 5]);", False),
            ("dos islas (un disco suelto dentro de un anillo)", "difference() { cylinder(d = 40, h = 5); translate([0, 0, -1]) cylinder(d = 30, h = 7); } cylinder(d = 20, h = 5);", True),
            ("3 agujeros chicos de 4,4 en la cara de apoyo", "difference() { cube([60, 40, 5]); for (x = [15, 30, 45]) translate([x, 20, -1]) cylinder(d = 4.4, h = 7); }", True),
            ("placa de 3 x 60 x 100 de pie (esbeltez)", "cube([60, 3, 100]);", True),
            ("placa de 2 x 60 x 40 de pie (despegue)", "cube([60, 2, 40]);", True),
            ("centro de masa fuera de la base (L que cuelga)", "cube([10, 10, 30]); translate([0, 0, 30]) cube([60, 10, 10]);", True),
            ("bueno: placa de 6 x 60 x 30 de pie", "cube([60, 6, 30]);", False),
            ("3 ranuras de 1 mm desde el borde (cuentan como agujeros chicos)", "difference() { cube([60, 40, 5]); for (x = [15, 30, 45]) translate([x, -1, -1]) cube([1, 11, 7]); }", True),
            ("2 agujeros de 4,4 y una tira de 1 x 20 que sale", "difference() { cube([60, 40, 5]); for (x = [20, 40]) translate([x, 20, -1]) cylinder(d = 4.4, h = 7); } translate([60, 10, 0]) cube([20, 1, 5]);", True),
            ("3 ranuras cerradas de 4,4 x 16 (4 A / P = 7,2: agujeros chicos)", "difference() { cube([60, 40, 5]); for (y = [8, 20, 32]) hull() for (x = [20, 31.6]) translate([x, y, -1]) cylinder(d = 4.4, h = 7); }", True),
            ("bueno: 3 ranuras de 1,6 desde el borde y una tira de 1,6", "difference() { cube([60, 40, 5]); for (x = [15, 30, 45]) translate([x, -1, -1]) cube([1.6, 11, 7]); } translate([60, 10, 0]) cube([20, 1.6, 5]);", False)):
        m = PC.medir(stl_de(codigo))
        caso(nombre, R.revisar_primera_capa("pieza_de_prueba", m, PC)[0], esperado)
    for nombre, codigo, que, esperado in (
            ("ranura de 1 mm desde el borde", "difference() { cube([60, 40, 5]); translate([30, -1, -1]) cube([1, 11, 7]); }", "angostas", True),
            ("dos islas a 0,8 mm (ranura entre las dos)", "cube([30, 40, 5]); translate([30.8, 0, 0]) cube([30, 40, 5]);", "angostas", True),
            ("bueno: placa girada 17 grados con un agujero de 10 (bordes en escalera)", "rotate(17) difference() { cube([60, 40, 5]); translate([30, 20, -1]) cylinder(d = 10, h = 7); }", "angostas", False),
            ("bueno: disco de 40", "cylinder(d = 40, h = 5, $fn = 120);", "angostas", False)):
        caso(f"{nombre}: {que}", PC.medir(stl_de(codigo))[que], esperado)

    print("== auditar.py (paredes finas en toda la altura) ==")
    with tempfile.TemporaryDirectory() as t:
        viejo = A.CACHE
        A.CACHE = Path(t)
        (Path(t) / "cama").mkdir()
        try:
            for nombre, codigo, esperado in (     # 0,8 x 90 = 72 mm2 de pared fina por corte (falla con > 60)
                    ("aleta de 0,8 x 90 en el cuarto de arriba (z 31 a 40)", "cube([100, 40, 31]); translate([5, 20, 0]) cube([90, 0.8, 40]);", True),
                    ("bueno: cubo de 40", "cube(40);", False)):
                ex_carro.escribir_stl(Path(t) / "cama" / "p.stl", tri_de(codigo))
                f = A.auditar("p")
                caso(nombre, [x for x in f["fallas"] if "paredes" in x], esperado)
        finally:
            A.CACHE = viejo

    print("== exportar.py, modelo_3d.py y manual_maqueta.py no corren con lo no revisado ==")
    import exportar as ex
    import modelo_3d as m3
    sello, listas, viejos = R.SELLO_OK, R.listas, R.viejos

    def no_pasa(*a, **k):      # si el freno falla, que tampoco exporte ni escriba nada
        raise RuntimeError("paso el freno")

    def frena(fn):
        try:
            fn()
        except SystemExit as e:
            return str(e)[:100]
        except RuntimeError as e:
            return None if "paso el freno" in str(e) else str(e)
        return None
    with tempfile.TemporaryDirectory() as t:
        R.SELLO_OK = Path(t) / "revision_ok.huella"
        R.listas = no_pasa
        try:
            caso("exportar sin sello de una revision completa", frena(ex.main))
            R.SELLO_OK.write_text("otra huella")
            caso("exportar con el sello de otros .scad", frena(ex.main))
            R.SELLO_OK.write_text(R.huella())
            caso("bueno: sello de la revision completa con los .scad de ahora", R.revision_ok())
            caso("bueno: con el sello al dia exportar pasa el freno", frena(ex.main), False)
            R.listas = lambda: (piezas, rem, True)
            R.viejos = lambda rutas: list(rutas)[:1]
            m3.leer_eco = no_pasa
            caso("modelo_3d con un STL de _cache viejo", frena(m3.main))
            try:
                import manual_maqueta as mm
                mm.estructura_por_altura = no_pasa
                caso("manual_maqueta con un STL de _cache viejo", frena(mm.main))
            except ImportError as e:      # en una copia sin sim/ no se puede importar
                print(f"  (manual_maqueta no se pudo importar aqui: {e}; su freno no se prueba)")
        finally:
            R.SELLO_OK, R.listas, R.viejos = sello, listas, viejos

    print("== estructura (estructura.py) ==")
    nodos, tubos, empalmes, tacos, rem2 = est.generar()
    caso("bueno: la estructura tal cual", est.comprobar(nodos, tubos, empalmes, tacos, rem2), False)
    caso("taco encima de un empalme", est.comprobar(nodos, tubos, empalmes, [("taco_x", -26.7)], rem2))
    caso("taco encima de un nodo", est.comprobar(nodos, tubos, empalmes, [("taco_x", -50.0)], rem2))
    for nombre, zona in (("tubo dentro de una zona libre", (0, 10, -45, -35, 435, 445)),
                         ("manguito de un empalme en una zona libre (0,5 a 2 mm fuera del tubo)", None),
                         ("placa de un taco en una zona libre", None),
                         ("cabeza de un remache de la estructura en una zona libre", None)):
        if "empalme" in nombre:
            e = empalmes[0]
            u = np.cross(e[2], e[3])      # costado del manguito (sobresale 2,6 del tubo)
            p = e[1] + u * (est.LADO / 2 + 1.2)
            zona = (p[0] - 1, p[0] + 1, p[1] - 0.7, p[1] + 0.7, p[2] - 0.7, p[2] + 0.7) if abs(u[1]) > 0.5 else \
                   (p[0] - 0.7, p[0] + 0.7, p[1] - 1, p[1] + 1, p[2] - 0.7, p[2] + 0.7)
        elif "taco" in nombre:
            x = est.TACOS_X[0]
            zona = (x - 2, x + 2, est.Y_A - 10.5, est.Y_A - 8.5, 395, 397)
        elif "cabeza" in nombre:
            r = next(r for r in rem2 if r[0].startswith("r_F1_"))
            p = r[2] - est.unit(r[3]) * 0.8
            zona = (p[0] - 0.5, p[0] + 0.5, p[1] - 0.5, p[1] + 0.5, p[2] - 0.5, p[2] + 0.5)
        viejo = dict(est.ZONAS_LIBRES)
        est.ZONAS_LIBRES["zona de prueba"] = zona
        caso(nombre, est.comprobar(nodos, tubos, empalmes, tacos, rem2))
        est.ZONAS_LIBRES.clear(); est.ZONAS_LIBRES.update(viejo)
    viejas = dict(est.CARGAS)
    est.CARGAS[("P1", "P2")] = 20000
    caso("carga de 20 kg en la viga (flecha alta)", est.comprobar(nodos, tubos, empalmes, tacos, rem2))
    est.CARGAS.clear(); est.CARGAS.update(viejas)
    viejo_nodos = dict(est.NODOS)
    est.NODOS["F6"] = (-20, est.Y_A, est.Z_PISO)        # a 30 mm de F4: tramo imposible
    try:
        est.generar(); err = None
    except AssertionError as e:
        err = str(e)
    caso("dos nodos demasiado cerca", err)
    est.NODOS.clear(); est.NODOS.update(viejo_nodos)
    # nodo aparte, lejos de todo: brazos arriba, abajo, +x y +y (no estan en un plano)
    est.NODOS["X"] = (900, 900, 300)
    nuevos = [("X", (900, 900, 500)), ("X", (900, 900, 100)), ("X", (1100, 900, 300)), ("X", (900, 1100, 300))]
    est.MIEMBROS.extend(nuevos)
    try:
        est.generar(); err = None
    except AssertionError as e:
        err = str(e)
    del est.MIEMBROS[-len(nuevos):]
    del est.NODOS["X"]
    caso("nodo con brazos arriba y abajo fuera de un plano", err)

    fallas = [n for n, ok, _ in resultados if not ok]
    print(f"\n{len(resultados) - len(fallas)} de {len(resultados)} casos dieron lo esperado")
    for n in fallas:
        print("  NO DIO LO ESPERADO:", n)
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
