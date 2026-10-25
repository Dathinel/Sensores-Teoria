"""Revisor de la maqueta impresa (usuario, 2026-10-24: "revise todo multiples veces para no cometer el mismo error").

Lo que se le escapo al carro (remaches de 10,5 que no pasaban, de 37 que no agarraban nada) aqui se MIDE en el
ensamble, pieza por pieza y remache por remache:

  1. remaches: a lo largo del eje de cada uno, con rayos contra las mallas de TODAS las piezas en su lugar:
       - el material que junta empieza en la cabeza y termina justo en su agarre (+-0,3 mm);
       - el agujero esta libre (nada en el camino del vastago);
       - detras queda hueco >= 3 mm para que la una abra (si no, no traba: agujero ciego);
       - la cabeza no se monta sobre nada; agarre <= 20 mm (mas largo se dobla al meterlo).
  2. choques: cada par de piezas cuyas cajas se tocan se intersecta (> 1 mm3 = choque); tambien contra lo comprado.
  3. sin soportes: cada pieza en su orientacion de impresion (revisar_voladizos.py del carro).
  4. cama: cada pieza cabe en la Creality Hi (260 x 260 x 300 con margen).

Uso: python revisar.py            (todo)
     python revisar.py --sub alm  (solo las piezas cuyo nombre empieza por alm_ y sus remaches)
Sale con codigo 1 si algo falla. Deja los STL en _cache/ (los usa exportar.py).
"""
import argparse
import os
import threading
import time
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "chasis_impreso"))
import exportar as ex_carro            # noqa: E402  (leer_stl, volumen_area, OpenSCAD)
import revisar_voladizos as volad      # noqa: E402
# Ya cargados, se saca chasis_impreso de la ruta y se suelta el nombre "exportar": si no, un `import exportar`
# posterior (el de ESTA carpeta) devolvia el del carro (2026-10-24, les paso a los agentes al medir gramos).
sys.path.remove(str(AQUI.parent / "chasis_impreso"))
del sys.modules["exportar"]

OPENSCAD = ex_carro.OPENSCAD
SCAD = AQUI / "maqueta.scad"
CACHE = AQUI / "_cache"
TOLERA = 0.3
HUECO_UNA = 3.0
AGARRE_MAX = 20.0
CAMA_UTIL = (240.0, 240.0, 290.0)
HILOS = 6
SUBSISTEMAS = ("alm_", "mon_", "vas_", "tap_", "can_")   # prefijos de las piezas que se montan despues de la estructura


# ----------------------------------------------------------------- OpenSCAD
def scad(salida, opcional=False, **defs):
    """OpenSCAD a un archivo temporal y despues se reemplaza: varios revisar.py a la vez (un agente por
    subsistema) escribian el mismo STL de _cache y daba PermissionError (2026-10-24)."""
    args = [str(OPENSCAD)]
    for k, v in defs.items():
        args += ["-D", f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}"]
    salida = Path(salida)
    tmp = salida.with_name(f"{salida.stem}.{os.getpid()}.{threading.get_ident()}{salida.suffix}")
    r = subprocess.run(args + ["-o", str(tmp), str(SCAD)], capture_output=True, text=True)
    if tmp.exists():
        for _ in range(40):
            try:
                os.replace(tmp, salida)
                break
            except PermissionError:
                time.sleep(0.5)
        else:
            tmp.unlink(missing_ok=True)
    if not salida.exists() and not opcional:
        raise SystemExit(f"OpenSCAD fallo ({defs}):\n{(r.stdout + r.stderr)[-2500:]}")
    return r.stdout + r.stderr


def listas():
    """Piezas y remaches tal como los arma maqueta.scad."""
    with tempfile.TemporaryDirectory() as t:
        eco = Path(t) / "l.echo"
        scad(eco, modo="lista")
        txt = eco.read_text()
    piezas = re.findall(r'ECHO: PIEZA = "([^"]+)"', txt)
    rem = []
    for m in re.finditer(r'ECHO: REM = \["([^"]+)", ([-\d.e]+), \[([^\]]+)\], \[([^\]]+)\]\]', txt):
        rem.append((m[1], float(m[2]), np.array([float(x) for x in m[3].split(",")]),
                    np.array([float(x) for x in m[4].split(",")])))
    hay_comprados = "ECHO: COMPRADOS = true" in txt
    global MOVILES
    MOVILES = [(m[1], re.findall(r'"([^"]+)"', m[2]))
               for m in re.finditer(r'ECHO: MOVIL = \["([^"]+)", \[([^\]]*)\]\]', txt)]
    raros = [l for l in txt.splitlines() if l.startswith("ECHO: MOVIL =") and not re.match(r'ECHO: MOVIL = \["', l)]
    assert not raros, f"lista de moviles mal formada (undef?): {raros[:3]}"
    # un subsistema con <sub>_barrido(n) tiene que declarar al menos un movil (si no, se salto sin avisar)
    for sub in ("alm", "mon", "vas", "tap", "can"):
        archivo = next((f for f in AQUI.glob("*.scad") if f"module {sub}_barrido(" in f.read_text(encoding="utf-8")), None)
        if archivo and not any(n.startswith(sub) for n, _ in MOVILES):
            raise SystemExit(f"{archivo.name} define {sub}_barrido pero MOVILES_{sub.upper()} salio vacia "
                             "(escribirla como lista literal: ver CONVENCIONES.md)")
    assert piezas, "maqueta.scad no listo piezas (modo lista)"
    return piezas, rem, hay_comprados


MOVILES = []      # [(pieza o barrido, [lo que se mueve con ella])]: lo llena listas()


def tocadas_por(rem_sub, piezas):
    """Piezas en _cache cuya caja toca el recorrido de algun remache de rem_sub: hay que volver a dibujarlas
    para que tengan sus agujeros (2026-10-24: los tubos de la viga quedaban sin los agujeros nuevos)."""
    out = set()
    for n in piezas:
        ruta = CACHE / "ens" / f"{n}.stl"
        if not ruta.exists():
            continue
        tri = ex_carro.leer_stl(ruta)
        if not len(tri):
            continue
        lo, hi = caja(tri)
        for _, agarre, cab, eje in rem_sub:
            fin = cab + eje / np.linalg.norm(eje) * (agarre + 3)
            if np.all(np.minimum(cab, fin) - 3 < hi) and np.all(np.maximum(cab, fin) + 3 > lo):
                out.add(n)
                break
    return out


def renderizar(piezas, hay_comprados, sub="", rem_sub=()):
    """Con sub: las piezas de ese subsistema, las que tocan sus remaches y las que falten en _cache; sin sub: todas."""
    (CACHE / "ens").mkdir(parents=True, exist_ok=True)
    (CACHE / "cama").mkdir(parents=True, exist_ok=True)
    tocadas = tocadas_por(rem_sub, piezas) if sub else set()
    hacer = [n for n in piezas if not sub or n.startswith(sub) or n in tocadas or not (CACHE / "ens" / f"{n}.stl").exists()
             or not (CACHE / "cama" / f"{n}.stl").exists()]
    trabajos = [(CACHE / "ens" / f"{n}.stl", dict(modo="pieza", cual=n)) for n in hacer]
    trabajos += [(CACHE / "cama" / f"{n}.stl", dict(modo="cama", cual=n)) for n in hacer]
    if hay_comprados:   # puede salir vacio (ningun subsistema dibujo lo comprado todavia)
        trabajos.append((CACHE / "ens" / "_comprados.stl", dict(modo="comprados", opcional=True)))
    for s, _ in trabajos:
        s.unlink(missing_ok=True)
    with ThreadPoolExecutor(HILOS) as ej:
        list(ej.map(lambda t: scad(t[0], **t[1]), trabajos))
    # en la cama: apoyada en z = 0 y centrada (lo mismo que hace exportar.py)
    for n in hacer:
        ruta = CACHE / "cama" / f"{n}.stl"
        tri = ex_carro.leer_stl(ruta)
        if len(tri):
            lo, hi = caja(tri)
            ex_carro.escribir_stl(ruta, tri - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]))


# ----------------------------------------------------------------- rayos
def cortes(o, d, tri):
    """Todos los t donde el rayo o + t d cruza la malla (ordenados)."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    e1, e2 = b - a, c - a
    p = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1), 0)
    s = o - a
    u = np.einsum("ij,ij->i", s, p) * inv
    q = np.cross(s, e1)
    v = (q @ d) * inv
    t = np.einsum("ij,ij->i", q, e2) * inv
    golpe = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)
    return np.unique(np.round(t[golpe], 4))


def intervalos(o, d, mallas):
    """Tramos del rayo que caen dentro de material (cada malla cerrada: par de cortes = entrada y salida)."""
    tramos = []
    for tri in mallas:
        ts = cortes(o, d, tri)
        tramos += [(ts[i], ts[i + 1]) for i in range(0, len(ts) - 1, 2)]
    tramos.sort()
    juntos = []
    for a, b in tramos:
        if juntos and a <= juntos[-1][1] + 0.4:      # dos piezas apoyadas (holgura de encaje) cuentan juntas
            juntos[-1][1] = max(juntos[-1][1], b)
        else:
            juntos.append([a, b])
    return juntos


def material_en(juntos, t0, t1):
    return any(a < t1 and b > t0 for a, b in juntos)


def revisar_remaches(rem, mallas, cajas):
    """mallas: {nombre: triangulos} de las piezas en su lugar (y lo comprado)."""
    malos = []
    for nombre, agarre, cab, eje in rem:
        d = eje / np.linalg.norm(eje)
        cerca = [m for n, m in mallas.items() if np.all(cajas[n][0] - 30 < cab + 30) and np.all(cajas[n][1] + 30 > cab - 30)]
        aux = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
        x = np.cross(aux, d); x /= np.linalg.norm(x)
        y = np.cross(d, x)
        problemas = []
        if agarre > AGARRE_MAX:
            problemas.append(f"agarre {agarre} > {AGARRE_MAX}")
        # el material que junta, medido en 8 rayos a 2,7 mm del eje (fuera del agujero de 4,4)
        fines, inicios = [], []
        for ang in np.linspace(0, 2 * np.pi, 8, endpoint=False):
            o = cab + 2.7 * (np.cos(ang) * x + np.sin(ang) * y) - d * 5.0
            juntos = [[a - 5.0, b - 5.0] for a, b in intervalos(o, d, cerca)]
            tramo = next(([a, b] for a, b in juntos if a <= 0.5 and b > 0.5), None)
            if tramo is None:
                inicios.append(np.inf); fines.append(-np.inf)
                continue
            inicios.append(tramo[0]); fines.append(tramo[1])
            if material_en(juntos, tramo[1] + 0.05, tramo[1] + HUECO_UNA):
                problemas.append("sin hueco para la una (agujero ciego o pieza detras)")
        fin = float(np.median(fines))
        ini = float(np.median(inicios))
        if not np.isfinite(fin):
            problemas.append("no agarra nada")
        else:
            if abs(fin - agarre) > TOLERA:
                problemas.append(f"junta {fin:.2f} mm y el remache es de {agarre:.2f}")
            if ini < -TOLERA:
                problemas.append(f"hay material {-ini:.1f} mm por encima de la cabeza (la cabeza queda enterrada)")
        # agujero libre: rayo por el eje y a 1,6 mm
        for rr in (0.0, 1.6):
            o = cab + rr * x - d * 0.01
            juntos = intervalos(o, d, cerca)
            if material_en(juntos, 0.05, agarre + HUECO_UNA):
                problemas.append("el agujero esta tapado")
                break
        # que se pueda meter: detras de la cabeza tiene que haber espacio libre del largo del remache
        # (con la cabeza adentro de un tubo cerrado mide bien pero no hay como meterlo).
        # Rayos a 3 mm del eje (por el eje mismo puede haber agujeros de otro remache en la pared de enfrente).
        # Orden de armado: la estructura se remacha ANTES de montar los subsistemas y lo comprado, asi que
        # para un remache de la estructura no estorba lo que se monta despues (los de un subsistema, si).
        pasillo = agarre + 1.6 + 2.8 + 15.0     # el remache entero mas 15 mm para empujarlo con el dedo
        bajo_piso = cab[2] - d[2] * pasillo < 0 or cab[2] < 0
        de_estructura = not nombre.startswith(tuple("r_" + s for s in SUBSISTEMAS))
        antes = [m for n, m in mallas.items() if not (de_estructura and (n.startswith(SUBSISTEMAS) or n == "_comprados"))
                 and np.all(cajas[n][0] - 30 < cab + 30) and np.all(cajas[n][1] + 30 > cab - 30)]
        tapado = False
        for ang in np.linspace(0, 2 * np.pi, 4, endpoint=False):
            o = cab + 3.0 * (np.cos(ang) * x + np.sin(ang) * y) - d * (pasillo + 2)
            juntos = [[a - (pasillo + 2), b - (pasillo + 2)] for a, b in intervalos(o, d, antes)]
            tapado = tapado or material_en(juntos, -pasillo - 1.7, -1.7)
        if bajo_piso or tapado:
            problemas.append(f"no hay {pasillo:.0f} mm libres detras de la cabeza para meterlo" + (" (el piso)" if bajo_piso else ""))
        # cabeza: tira de 8 x 3,2 x 1,6 encima de la cara (en el marco de comun.scad: largo en x local)
        for sx in (-3.5, 0, 3.5):
            for sy in (-1.4, 1.4):
                o = cab + sx * x + sy * y - d * 6
                juntos = [[a - 6, b - 6] for a, b in intervalos(o, d, cerca)]
                if material_en(juntos, -1.7, -0.05):
                    problemas.append("la cabeza choca con algo")
                    break
            else:
                continue
            break
        if problemas:
            malos.append((nombre, sorted(set(problemas))))
    return malos


def caja(tri):
    p = tri.reshape(-1, 3)
    return p.min(0), p.max(0)


def choques(nombres, cajas, solo_con=None):
    pares = [(a, b) for i, a in enumerate(nombres) for b in nombres[i + 1:]
             if (solo_con is None or solo_con in (a, b))
             and np.all(cajas[a][0] < cajas[b][1] - 0.05) and np.all(cajas[b][0] < cajas[a][1] - 0.05)]

    def uno(par):
        a, b = par
        with tempfile.TemporaryDirectory() as t:
            s, o = Path(t) / "x.scad", Path(t) / "x.stl"
            s.write_text(f'intersection() {{ import("{(CACHE / "ens" / (a + ".stl")).as_posix()}"); '
                         f'import("{(CACHE / "ens" / (b + ".stl")).as_posix()}"); }}\n')
            subprocess.run([str(OPENSCAD), "-o", str(o), str(s)], capture_output=True)
            if not o.exists():
                return a, b, 0.0
            tri = ex_carro.leer_stl(o)
            return a, b, (ex_carro.volumen_area(tri)[0] if len(tri) else 0.0)

    with ThreadPoolExecutor(8) as ej:
        res = list(ej.map(uno, pares))
    return [(a, b, v) for a, b, v in res if v > 1.0], len(pares)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", default="", help="prefijo de las piezas a revisar (alm, mon, vas, can, ...)")
    ap.add_argument("--sin-render", action="store_true", help="usar los STL que ya estan en _cache")
    args = ap.parse_args()
    piezas, rem, hay_comprados = listas()
    if not args.sin_render:
        renderizar(piezas, hay_comprados, args.sub, [r for r in rem if r[0].startswith(f"r_{args.sub}")] if args.sub else ())
    todos = piezas + (["_comprados"] if hay_comprados else [])
    todos = [n for n in todos if (CACHE / "ens" / f"{n}.stl").exists()]
    mallas = {n: ex_carro.leer_stl(CACHE / "ens" / f"{n}.stl") for n in todos}
    mallas = {n: m for n, m in mallas.items() if len(m)}
    cajas = {n: caja(m) for n, m in mallas.items()}
    mias = [n for n in piezas if n.startswith(args.sub)]
    rem_mios = [r for r in rem if args.sub == "" or r[0].startswith(f"r_{args.sub}")]
    fallas = 0

    print(f"== remaches ({len(rem_mios)} de {len(rem)}) ==")
    malos = revisar_remaches(rem_mios, mallas, cajas)
    for n, p in malos:
        print(f"  MAL {n}: {'; '.join(p)}")
    fallas += len(malos)

    print(f"== choques ({len(mias)} piezas) ==")
    nombres = sorted(set(mias) | ({"_comprados"} if hay_comprados else set()))
    if args.sub:   # contra todo lo demas tambien
        nombres = sorted(set(nombres) | set(todos))
    malos, n_pares = choques([n for n in nombres if n in mallas], cajas)
    malos = [m for m in malos if args.sub == "" or m[0].startswith(args.sub) or m[1].startswith(args.sub)]
    for a, b, vol in malos:
        print(f"  CHOQUE {a} con {b}: {vol:.1f} mm3")
    print(f"  ({n_pares} pares que se tocan revisados)")
    fallas += len(malos)

    # piezas que se mueven: su BARRIDO (todo el recorrido) no puede chocar con nada que no se mueva con ella
    movs = [(n, ex) for n, ex in MOVILES if not args.sub or n.startswith(args.sub)]
    print(f"== piezas que se mueven, barridas en todo su recorrido ({len(movs)} de {len(MOVILES)}) ==")
    (CACHE / "barr").mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(HILOS) as ej:
        list(ej.map(lambda m: scad(CACHE / "barr" / f"{m[0]}.stl", modo="barrido", cual=m[0]), movs))
    for n, excluir in movs:
        tri = ex_carro.leer_stl(CACHE / "barr" / f"{n}.stl")
        clave = f"~barrido~{n}"
        ex_carro.escribir_stl(CACHE / "ens" / f"{clave}.stl", tri)      # choques() las busca en ens/
        cajas_b = dict(cajas)
        cajas_b[clave] = caja(tri)
        otros = [o for o in cajas if o != n and o not in excluir and not o.startswith("~")]
        malos_b, _ = choques([clave] + otros, cajas_b, solo_con=clave)
        for a, b, vol in malos_b:
            print(f"  CHOQUE al moverse {n} con {b if a == clave else a}: {vol:.1f} mm3")
        fallas += len(malos_b)
        (CACHE / "ens" / f"{clave}.stl").unlink(missing_ok=True)
    # barrido contra barrido: con los barridos que haya en _cache/barr (los de los otros subsistemas tambien)
    excl = dict(MOVILES)
    hay = [n for n, _ in MOVILES if (CACHE / "barr" / f"{n}.stl").exists()]
    pares = [(a, b) for i, a in enumerate(hay) for b in hay[i + 1:]
             if (not args.sub or a.startswith(args.sub) or b.startswith(args.sub))
             and b not in excl.get(a, []) and a not in excl.get(b, [])]
    if pares:
        for a, b in pares:
            for n in (a, b):
                ex_carro.escribir_stl(CACHE / "ens" / f"~b~{n}.stl", ex_carro.leer_stl(CACHE / "barr" / f"{n}.stl"))
        cajas_bb = {f"~b~{n}": caja(ex_carro.leer_stl(CACHE / "barr" / f"{n}.stl")) for n in hay}
        malos_bb = []
        for a, b in pares:
            m, _ = choques([f"~b~{a}", f"~b~{b}"], cajas_bb)
            malos_bb += m
        for a, b, vol in malos_bb:
            print(f"  CHOQUE entre dos cosas que se mueven: {a[3:]} con {b[3:]}: {vol:.1f} mm3 "
                  "(si nunca se mueven a la vez, declararlo en la lista de excluidos de MOVILES)")
        fallas += len(malos_bb)
        for n in hay:
            (CACHE / "ens" / f"~b~{n}.stl").unlink(missing_ok=True)
        print(f"  ({len(pares)} pares de barridos revisados)")

    print("== sin soportes y cama ==")
    for n in mias:
        ruta = CACHE / "cama" / f"{n}.stl"
        tri = ex_carro.leer_stl(ruta)
        lo, hi = caja(tri)
        med = hi - lo
        r = volad.revisar(ruta)
        problemas = []
        if r["voladizo"] > 0:
            problemas.append(f"voladizo {r['voladizo']} mm2 en {r['zonas'][:2]}")
        if r["puente_largo"] > volad.PUENTE_MAX:
            problemas.append(f"puente de {r['puente_largo']} mm")
        if not (min(med[:2]) <= CAMA_UTIL[0] and max(med[:2]) <= CAMA_UTIL[1] and med[2] <= CAMA_UTIL[2]):
            problemas.append(f"no cabe en la cama: {med.round(1)}")
        if problemas:
            print(f"  MAL {n}: {'; '.join(problemas)}")
            fallas += 1
    print("TODO OK" if not fallas else f"{fallas} problemas")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
