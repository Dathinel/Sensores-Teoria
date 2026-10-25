"""Prueba del revisor con errores puestos a proposito (usuario, 2026-10-24: "mande mas pruebas de errores por si
acaso se le pasaron mas cosas").

Un revisor que nunca se vio fallar no prueba nada: cada caso mete UN error conocido y exige que revisar.py (o
estructura.py) lo atrape; los casos "bueno" exigen que NO marque nada (para que no grite por todo).
Usa las piezas de la estructura ya renderizadas en _cache/ (correr antes: python revisar.py).

Uso: python probar_revisor.py   -> tabla de casos y sale con 1 si alguno no dio lo esperado.
"""
import subprocess
import tempfile
from pathlib import Path

import numpy as np

import estructura as est
import revisar as R
from revisar import CACHE, ex_carro, volad

resultados = []


def caso(nombre, detecto, esperado=True):
    ok = bool(detecto) == esperado
    resultados.append((nombre, ok, detecto))
    print(f"{'ok ' if ok else 'FALLA'}  {nombre:62s} -> {detecto if detecto else 'no marca nada'}")


def stl_de(codigo):
    t = Path(tempfile.mkdtemp())
    (t / "p.scad").write_text(codigo)
    subprocess.run([str(R.OPENSCAD), "-o", str(t / "p.stl"), str(t / "p.scad")], capture_output=True)
    return t / "p.stl"


def main():
    piezas, rem, _ = R.listas()
    mallas = {n: ex_carro.leer_stl(CACHE / "ens" / f"{n}.stl") for n in piezas if (CACHE / "ens" / f"{n}.stl").exists()}
    cajas = {n: R.caja(m) for n, m in mallas.items()}
    rr = lambda r: (R.revisar_remaches([r], mallas, cajas) or [(None, [])])[0][1]
    lateral = next(r for r in rem if r[0].startswith("r_F1_"))
    taco = next(r for r in rem if "taco" in r[0])
    nodo_T3 = np.array(est.NODOS["T3"], float)

    print("== remaches ==")
    caso("bueno: remache lateral de un nodo", rr(lateral), False)
    caso("bueno: remache de un taco", rr(taco), False)
    caso("agarre mas largo que lo que junta (6 en vez de 4,2)", rr((lateral[0], 6.0, lateral[2], lateral[3])))
    caso("agarre mas corto (3 en vez de 4,2): la una queda adentro de la pared", rr((lateral[0], 3.0, lateral[2], lateral[3])))
    caso("diferencia chica pero real (4,7 en vez de 4,2)", rr((lateral[0], 4.7, lateral[2], lateral[3])))
    caso("diferencia dentro de la tolerancia (4,35 en vez de 4,2)", rr((lateral[0], 4.35, lateral[2], lateral[3])), False)
    caso("remache en el aire (no agarra nada)", rr((lateral[0], 4.2, lateral[2] + np.array([0, 0, 300.0]), lateral[3])))
    caso("al reves: cabeza adentro del tubo", rr((lateral[0], 4.2, lateral[2] + lateral[3] * 4.2, -lateral[3])))
    caso("agarre de 30 (se dobla al meterlo)", rr((lateral[0], 30.0, lateral[2], lateral[3])))
    caso("cabeza contra el piso (nodo del piso, desde abajo)",
         rr(("x", 4.2, np.array([-170 + 22, -40.5, 0.0]), np.array([0, 0, 1.0]))))
    caso("cabeza enterrada 1 mm en la pared", rr((lateral[0], 4.2, lateral[2] + lateral[3] * 1.0, lateral[3])))
    caso("cabeza corrida 3 mm afuera de la cara (no apoya)", rr((lateral[0], 4.2, lateral[2] - lateral[3] * 3.0, lateral[3])))
    # agujero ciego: por la placa del taco hacia el bloque macizo del medio (z entre riel y viga)
    x_taco = est.TACOS_X[0]
    cab = np.array([x_taco, est.Y_A - 8 - 3.0, (est.Z_RIEL + est.Z_VIGA) / 2])
    caso("agujero ciego (sale a un bloque macizo, la una no abre)", rr(("x", 3.0, cab, np.array([0, 1.0, 0]))))
    # eje torcido: la cabeza apoya bien pero el eje va de costado
    caso("eje torcido 90 grados (a lo largo de la pared)", rr((lateral[0], 4.2, lateral[2], np.array([0, 0, 1.0]))))
    # remache que atraviesa la pared y sigue en otra pieza (sin hueco para la una)
    caso("sale pegado a otra pieza (sin hueco para la una)",
         rr(("x", 4.2, nodo_T3 + np.array([0, 0, est.BRAZO + 30]), np.array([0, 0, -1.0]))))

    print("== orden de armado (la estructura se remacha antes que los subsistemas) ==")
    est_tapado = next((r for r in rem if r[0] == "r_M1_0_b"), None)
    if est_tapado is not None:
        caso("bueno: remache de la estructura tapado por una pieza que se monta despues", rr(est_tapado), False)
    sub_rem = next((r for r in rem if r[0].startswith("r_mon_")), None)
    if sub_rem is not None:
        caso("remache de un subsistema al reves (cabeza adentro de la pieza)",
             rr((sub_rem[0], sub_rem[1], sub_rem[2] + sub_rem[3] / np.linalg.norm(sub_rem[3]) * sub_rem[1], -sub_rem[3])))
        caso("remache de un subsistema con agarre mal (+1 mm)", rr((sub_rem[0], sub_rem[1] + 1.0, sub_rem[2], sub_rem[3])))

    print("== barridos (lo que se mueve) ==")
    viga = next(n for n in mallas if n.startswith("t_P1-P2"))
    tri_v = mallas[viga]
    for nombre, desp, esperado in (("barrido que pasa por adentro de la viga", (0, 0, 0), True),
                                   ("bueno: barrido 40 mm debajo de la viga", (0, 0, -40), False)):
        lo, hi = R.caja(tri_v)
        c = (lo + hi) / 2 + np.array(desp)
        caja_b = stl_de(f"translate([{c[0]},{c[1]},{c[2]}]) cube([30, 30, 10], center = true);")
        ex_carro.escribir_stl(CACHE / "ens" / "~barrido~prueba.stl", ex_carro.leer_stl(caja_b))
        cajas_b = dict(cajas)
        cajas_b["~barrido~prueba"] = R.caja(ex_carro.leer_stl(caja_b))
        malos, _ = R.choques(["~barrido~prueba", viga], cajas_b, solo_con="~barrido~prueba")
        caso(nombre, malos, esperado)
        (CACHE / "ens" / "~barrido~prueba.stl").unlink(missing_ok=True)
    caso("bueno: hay barridos declarados y salieron en la lista (no undef)", not R.MOVILES, False)

    print("== choques ==")
    a = CACHE / "ens" / "t_F1-F4.stl"
    tri = ex_carro.leer_stl(a)
    for nombre, desp, esperado in (("bueno: copia corrida 30 mm (no se tocan)", 30.0, False),
                                   ("bueno: copia a 0,3 mm (holgura de encaje)", 16.3, False),
                                   ("copia montada 2 mm", 14.0, True), ("copia en el mismo lugar", 0.0, True)):
        b = CACHE / "ens" / "_prueba_copia.stl"
        ex_carro.escribir_stl(b, tri + np.array([0, 0, desp]))
        cajas2 = {"t_F1-F4": R.caja(tri), "_prueba_copia": R.caja(tri + np.array([0, 0, desp]))}
        malos, _ = R.choques(["t_F1-F4", "_prueba_copia"], cajas2)
        caso(nombre, malos, esperado)
        b.unlink()

    print("== sin soportes ==")
    for nombre, codigo, esperado in (
            ("bueno: cubo", "cube(20);", False),
            ("bueno: techo a 45 grados", "rotate([0,0,0]) hull() { cube([20,20,1]); translate([0,0,15]) cube([20,35,1]); }", False),
            ("voladizo: T con ala de 20 mm en el aire", "cube([10,10,20]); translate([-20,0,20]) cube([50,10,4]);", True),
            ("puente de 25 mm", "difference() { cube([35,10,20]); translate([5,-1,-1]) cube([25,12,15]); }", True),
            ("bueno: puente de 10 mm", "difference() { cube([20,10,20]); translate([5,-1,-1]) cube([10,12,15]); }", False),
            ("voladizo a 60 grados de la vertical", "hull() { cube([20,10,1]); translate([0,0,10]) cube([20+17.3,10,1]); }", True)):
        r = volad.revisar(stl_de(codigo))
        caso(nombre, (r["voladizo"] > 0 or r["puente_largo"] > volad.PUENTE_MAX) and r, esperado)

    print("== estructura (estructura.py) ==")
    nodos, tubos, empalmes, tacos, rem2 = est.generar()
    caso("bueno: la estructura tal cual", est.comprobar(nodos, tubos, empalmes, tacos, rem2), False)
    caso("taco encima de un empalme", est.comprobar(nodos, tubos, empalmes, [("taco_x", -26.7)], rem2))
    caso("taco encima de un nodo", est.comprobar(nodos, tubos, empalmes, [("taco_x", -50.0)], rem2))
    viejo = dict(est.ZONAS_LIBRES)
    est.ZONAS_LIBRES["zona de prueba sobre el riel"] = (0, 10, -45, -35, 435, 445)
    caso("tubo dentro de una zona libre", est.comprobar(nodos, tubos, empalmes, tacos, rem2))
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

    print("== cama ==")
    largo = stl_de("cube([300, 20, 10]);")
    tri = ex_carro.leer_stl(largo)
    med = R.caja(tri)[1] - R.caja(tri)[0]
    caso("pieza de 300 mm (no cabe)", not (max(med[:2]) <= R.CAMA_UTIL[1]))
    fallas = [n for n, ok, _ in resultados if not ok]
    print(f"\n{len(resultados) - len(fallas)} de {len(resultados)} casos dieron lo esperado")
    for n in fallas:
        print("  NO DIO LO ESPERADO:", n)
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
