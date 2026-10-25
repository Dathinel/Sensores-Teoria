"""Revisor de la maqueta impresa (usuario, 2026-10-24: "revise todo multiples veces para no cometer el mismo error").

Lo que se le escapo al carro (remaches de 10,5 que no pasaban, de 37 que no agarraban nada) aqui se MIDE en el
ensamble, pieza por pieza y remache por remache:

  0. _cache: cada STL lleva al lado la huella de los .scad con que se dibujo; lo que falte o este viejo se vuelve a
     dibujar, sea del subsistema que sea (con --sin-render no se dibuja: lo viejo sale como MAL).
  1. remaches: a lo largo del eje de cada uno, con rayos contra las mallas de TODAS las piezas en su lugar:
       - hay material alrededor del agujero (8 rayos a 2,7 mm: si falta en uno, queda al canto) y empieza en la cabeza;
       - CADA pata (+-x local, donde engancha la una) sale entre agarre - 0,3 y agarre + 0,15 (hombro en + 0,2);
       - el agujero esta libre (eje y r 1,9) y detras de cada pata quedan >= 3 mm para que la una abra;
       - la cabeza (estadio de 8 x 3,2) apoya, no se monta sobre nada y tiene pasillo para meterla; agarre <= 20 mm;
       - dos remaches no se cruzan.
  2. choques: cada par de piezas cuyas cajas se tocan se intersecta (> 1 mm3 = choque); tambien contra lo comprado
     (un STL por subsistema, cruzados entre si). Lo que se mueve (> 0,05 mm3 = choque): su barrido contra todo lo fijo,
     contra los otros barridos y contra los remaches que no van con ella; lo que lleva cada barrido tiene que quedar
     DENTRO de el en todo su recorrido, extremos incluidos (RECORRIDOS); los mecanismos (leva y seguidor, manivela y
     carro, escape y vasos) fase por fase, con cada lado medido aparte (un lado vacio es MAL), y los que tienen que
     tocarse (CONTACTOS: leva y rodillo, escape y vasos) tienen que tocarse. Un OpenSCAD que falla es MAL, no 0 mm3.
  3. sin soportes: cada pieza en su orientacion de impresion (voladizos.py, el de la maqueta): las caras que miran abajo
     y, corte por corte cada 0,2 mm, nada que nazca en el aire ni que cuelgue de una sola punta (2026-10-25).
  4. cama y primera capa: cabe en la Creality Hi (240 x 240 x 290), islas, agujeros chicos y ranuras o tiras de menos
     de 1,2 mm en la cara que apoya, y la base (esbeltez, centro de masa, despegue) con primera_capa.py.

Uso: python revisar.py            (todo; si da TODO OK deja el sello _cache/revision_ok.huella que pide exportar.py)
     python revisar.py --sub alm  (solo las piezas cuyo nombre empieza por alm_ y sus remaches; no sella)
Sale con codigo 1 si algo falla. Deja los STL en _cache/ (los usan auditar.py, modelo_3d.py y manual_maqueta.py, que
no corren con STL viejos).
"""
import argparse
import hashlib
import json
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
# Ya cargado, se saca chasis_impreso de la ruta y se suelta el nombre "exportar": si no, un `import exportar`
# posterior (el de ESTA carpeta) devolvia el del carro (2026-10-24, les paso a los agentes al medir gramos).
sys.path.remove(str(AQUI.parent / "chasis_impreso"))
del sys.modules["exportar"]
import voladizos as volad              # noqa: E402  (el de la maqueta; revisar_voladizos.py del carro no se toca)

OPENSCAD = ex_carro.OPENSCAD
SCAD = AQUI / "maqueta.scad"
CACHE = AQUI / "_cache"
# cara de salida de cada pata entre agarre - TOL_MENOS y agarre + TOL_MAS: el hombro de la una esta en agarre + 0,2
# (2026-10-25: con +-0,3 pasaba una pila que deja el hombro adentro de la pared)
TOL_MAS, TOL_MENOS = 0.15, 0.3
HUECO_UNA = 3.0
# Choque: mm3 de interseccion. Entre piezas fijas 1 (lo que esconde no pasa de 0,09); lo que se mueve no puede ni rozar
# (2026-10-25: el balancin de la canaleta entraba 0,36 mm en el carro, 0,17 mm3, y el umbral de 1 lo escondia).
UMBRAL_FIJO, UMBRAL_MOVIL = 1.0, 0.05
AGARRE_MAX = 20.0
CAMA_UTIL = (240.0, 240.0, 290.0)
HILOS = int(os.environ.get("REVISAR_HILOS", "6"))   # OpenSCAD a la vez (bajarlo si hay agentes usando la CPU)
SUBSISTEMAS = ("alm_", "mon_", "vas_", "tap_", "can_")   # prefijos de las piezas que se montan despues de la estructura


# ----------------------------------------------------------------- OpenSCAD
class ErrorOpenSCAD(RuntimeError):
    """OpenSCAD fallo: dijo ERROR o WARNING, o no dibujo nada donde tenia que dibujar algo."""


def huella():
    """Huella de todos los .scad de la carpeta. maqueta.scad los incluye todos y cualquiera puede cambiar los agujeros
    de cualquier pieza (REM_TODOS y AGUJEROS_* se restan en todas): un STL de _cache vale solo con la misma huella."""
    h = hashlib.sha1()
    for f in sorted(AQUI.glob("*.scad")):
        h.update(f.name.encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


def sello(ruta):
    return Path(ruta).with_suffix(".huella")


def vigente(ruta, h):
    """El STL existe y se dibujo con los .scad de ahora (2026-10-25: 18 STL viejos de _cache daban MAL falsos, escondian
    otros y auditar.py auditaba orientaciones que ya habian cambiado)."""
    try:
        return Path(ruta).exists() and sello(ruta).read_text() == h
    except FileNotFoundError:
        return False


def scad(salida, opcional=False, codigo=None, **defs):
    """OpenSCAD a un archivo temporal y despues se reemplaza: varios revisar.py a la vez (un agente por
    subsistema) escribian el mismo STL de _cache y daba PermissionError (2026-10-24).
    codigo: en vez de un modo de maqueta.scad, ese codigo con maqueta.scad incluido (modo "nada").
    ErrorOpenSCAD si la salida dice ERROR o WARNING: un import que no abre o un modulo mal escrito solo dan un WARNING
    y un resultado vacio, que contaba como 0 mm3 = sin choque (2026-10-25). Un resultado vacio sin avisos: con opcional
    deja un STL de 0 triangulos; sin opcional tambien es error. En _cache deja al lado la huella de los .scad."""
    args = [str(OPENSCAD)]
    for k, v in defs.items():
        args += ["-D", f'{k}="{v}"' if isinstance(v, str) else (f"{k}={json.dumps(v)}" if isinstance(v, list) else f"{k}={v}")]
    salida = Path(salida)
    h = huella() if CACHE in salida.resolve().parents else None    # antes de dibujar: si un .scad cambia mientras, queda vieja
    if h:
        sello(salida).unlink(missing_ok=True)
    tmp = salida.with_name(f"{salida.stem}.{os.getpid()}.{threading.get_ident()}{salida.suffix}")
    # el .scad temporal en el mismo disco que maqueta.scad (2026-10-25: con el temporal en C: y el proyecto en D:,
    # OpenSCAD avisa reasignaciones que no existen, '"pared_nodo" was assigned on line 86 of ""', y todo lo dibujado con
    # codigo, lo comprado, los recorridos y las fases, salia MAL)
    CACHE.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=CACHE) as t:
        fuente = SCAD
        if codigo is not None:
            fuente = Path(t) / "x.scad"
            fuente.write_text(f'include <{SCAD.as_posix()}>\nmodo = "nada";\n{codigo}\n', encoding="utf-8")
        r = subprocess.run(args + ["-o", str(tmp), str(fuente)], capture_output=True, text=True)
    log = r.stdout + r.stderr
    que = codigo if codigo is not None else defs
    if "ERROR:" in log or "WARNING:" in log:
        tmp.unlink(missing_ok=True)
        raise ErrorOpenSCAD(f"OpenSCAD fallo ({que}):\n{log[-2500:]}")
    if not tmp.exists():
        if not (opcional and "top level object is empty" in log):
            raise ErrorOpenSCAD(f"OpenSCAD no dibujo nada ({que}):\n{log[-2500:]}")
        ex_carro.escribir_stl(tmp, np.zeros((0, 3, 3)))
    for _ in range(40):
        try:
            os.replace(tmp, salida)
            break
        except PermissionError:
            time.sleep(0.5)
    else:
        tmp.unlink(missing_ok=True)
        raise ErrorOpenSCAD(f"no se pudo escribir {salida} (abierto por otro proceso)")
    if h:
        sello(salida).write_text(h)
    return log


REM_PATRON = r'ECHO: REM = \["([^"]+)", ([-+\d.e]+), \[([^\]]+)\], \[([^\]]+)\]\]'


def listas():
    """Piezas y remaches tal como los arma maqueta.scad."""
    with tempfile.TemporaryDirectory() as t:
        eco = Path(t) / "l.echo"
        scad(eco, modo="lista")
        txt = eco.read_text()
    piezas, rem, hay_comprados = leer_listas(txt)
    # un subsistema con <sub>_barrido(n) tiene que declarar al menos un movil (si no, se salto sin avisar)
    for sub in SUBS:
        archivo = next((f for f in AQUI.glob("*.scad") if f"module {sub}_barrido(" in f.read_text(encoding="utf-8")), None)
        if archivo and not any(n.startswith(sub) for n, _ in MOVILES):
            raise SystemExit(f"{archivo.name} define {sub}_barrido pero MOVILES_{sub.upper()} salio vacia "
                             "(escribirla como lista literal: ver CONVENCIONES.md)")
    return piezas, rem, hay_comprados


def leer_listas(txt):
    """Lo mismo que listas() a partir del eco de OpenSCAD (separado para probarlo con un eco hecho a mano)."""
    piezas = re.findall(r'ECHO: PIEZA = "([^"]+)"', txt)
    rem = []
    for m in re.finditer(REM_PATRON, txt):
        rem.append((m[1], float(m[2]), np.array([float(x) for x in m[3].split(",")]),
                    np.array([float(x) for x in m[4].split(",")])))
    # un REM con agarre, cabeza o eje undef no se dibuja, no se agujerea y no entra en ninguna revision (2026-10-25)
    raros = [l for l in txt.splitlines() if l.startswith("ECHO: REM =") and not re.match(REM_PATRON, l)]
    assert not raros, f"remaches mal formados (undef?): {raros[:3]}"
    hay_comprados = "ECHO: COMPRADOS = true" in txt
    global MOVILES, SINCRONOS
    SINCRONOS = [(m[1], int(m[2])) for m in re.finditer(r'ECHO: SINCRONO = \["([^"]+)", (\d+)\]', txt)]
    raros = [l for l in txt.splitlines() if l.startswith("ECHO: SINCRONO =") and not re.match(r'ECHO: SINCRONO = \["[^"]+", \d+\]', l)]
    assert not raros, f"lista de mecanismos mal formada (undef?): {raros[:3]}"
    MOVILES = [(m[1], re.findall(r'"([^"]+)"', m[2]))
               for m in re.finditer(r'ECHO: MOVIL = \["([^"]+)", \[([^\]]*)\]\]', txt)]
    raros = [l for l in txt.splitlines() if l.startswith("ECHO: MOVIL =") and not re.match(r'ECHO: MOVIL = \["', l)]
    assert not raros, f"lista de moviles mal formada (undef?): {raros[:3]}"
    assert piezas, "maqueta.scad no listo piezas (modo lista)"
    return piezas, rem, hay_comprados


MOVILES = []      # [(pieza o barrido, [lo que se mueve con ella])]: lo llena listas()
SINCRONOS = []    # [(mecanismo, pasos)]: lo llena listas()
SUBS = ("alm", "mon", "vas", "tap", "can")
COMPRADOS = [f"_comprados_{s}" for s in SUBS]   # lo comprado, un STL por subsistema: asi tambien se cruzan entre si


def de_sub(n, sub):
    """La pieza (o lo comprado) n es del subsistema sub ('' = todos)."""
    return not sub or n.startswith(sub) or n == f"_comprados_{sub}"


def rutas_cache(piezas, hay_comprados):
    """Todos los STL de _cache que usan las revisiones."""
    out = [CACHE / c / f"{n}.stl" for n in piezas for c in ("ens", "cama")]
    out += [CACHE / "ens" / f"{n}.stl" for n in COMPRADOS] if hay_comprados else []
    return out + [CACHE / "barr" / f"{n}.stl" for n, _ in MOVILES]


def viejos(rutas):
    """Los que faltan o se dibujaron con otros .scad."""
    h = huella()
    return [r for r in rutas if not vigente(r, h)]


# Sello de la ultima revision COMPLETA que dio TODO OK: la huella de los .scad que reviso. exportar.py no exporta si no
# coincide con la de ahora (2026-10-25: decia "si no da TODO OK, no se exporta" y no lo comprobaba nadie).
SELLO_OK = CACHE / "revision_ok.huella"


def revision_ok():
    """La ultima revision completa dio TODO OK con los .scad de ahora."""
    try:
        return SELLO_OK.read_text() == huella()
    except FileNotFoundError:
        return False


def renderizar(piezas, hay_comprados):
    """Dibuja en _cache todo lo que falte o este viejo (otra huella de los .scad), sea del subsistema que sea: un
    --sub ya no usa las piezas y barridos viejos de los otros (2026-10-25). Lo vigente no se vuelve a dibujar.
    Devuelve los que OpenSCAD no pudo dibujar."""
    for c in ("ens", "cama", "barr"):
        (CACHE / c).mkdir(parents=True, exist_ok=True)
    rutas = viejos(rutas_cache(piezas, hay_comprados))
    trabajos = []
    for r in rutas:
        n, c = r.stem, r.parent.name
        trabajos.append((r, dict(codigo=f"{n[len('_comprados_'):]}_comprados();", opcional=True) if n.startswith("_comprados_")
                         else dict(modo={"ens": "pieza", "cama": "cama", "barr": "barrido"}[c], cual=n)))
    for s, _ in trabajos:   # si otro revisar.py lo tiene abierto no importa: scad() lo reemplaza de forma atomica
        try:
            s.unlink(missing_ok=True)
        except PermissionError:
            pass
    errores = []

    def uno(t):
        try:
            scad(t[0], **t[1])
        except ErrorOpenSCAD as e:
            errores.append(f"{t[0].parent.name}/{t[0].name}: {queja(e)}")
    with ThreadPoolExecutor(HILOS) as ej:
        list(ej.map(uno, trabajos))
    # en la cama: apoyada en z = 0 y centrada (lo mismo que hace exportar.py)
    for r in rutas:
        if r.parent.name == "cama" and r.exists():
            tri = ex_carro.leer_stl(r)
            if len(tri):
                lo, hi = caja(tri)
                ex_carro.escribir_stl(r, tri - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]]))
    print(f"(dibujados {len(trabajos)} STL de _cache que faltaban o estaban viejos)")
    return errores


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


# Puntos de la cabeza (estadio de 8 x 3,2 en el marco local: largo en x), un poco adentro del borde: la cabeza, su
# apoyo y el pasillo para meterla se miden en todos (2026-10-25: con 6 puntos una cabeza que pisaba el NEMA pasaba).
_g = [(px, py) for px in np.linspace(-3.9, 3.9, 9) for py in (-1.5, 0.0, 1.5)
      if abs(px) <= 2.4 or (abs(px) - 2.4) ** 2 + py ** 2 <= 1.55 ** 2]
PUNTOS_CABEZA = np.array(_g + [(-3.95, 0.0), (3.95, 0.0)])


def revisar_remaches(rem, mallas, cajas):
    """mallas: {nombre: triangulos} de las piezas en su lugar (y lo comprado)."""
    malos = []
    for nombre, agarre, cab, eje in rem:
        x, y, d = marco_remache(eje)        # las patas se abren en +-x (la ranura es el plano x = 0)
        cerca = [m for n, m in mallas.items() if np.all(cajas[n][0] - 30 < cab + 30) and np.all(cajas[n][1] + 30 > cab - 30)]

        def rayo(px, py, atras, contra=cerca):
            """Tramos con material a lo largo del eje por el punto (px, py) del marco local, en mm desde la cara de la
            cabeza (t < 0: del lado de la cabeza)."""
            o = cab + px * x + py * y - d * atras
            return [[a - atras, b - atras] for a, b in intervalos(o, d, contra)]

        def junta(juntos):
            return next(([a, b] for a, b in juntos if a <= 0.5 and b > 0.5), None)
        problemas = []
        if agarre > AGARRE_MAX:
            problemas.append(f"agarre {agarre} > {AGARRE_MAX}")
        # canto: material en los 8 rayos a 2,7 mm del eje (fuera del agujero de 4,4): si falta en alguno el agujero
        # queda abierto de costado (2026-10-25: con la mediana pasaban 3 de 8 sin material)
        tramos = [junta(rayo(2.7 * np.cos(a), 2.7 * np.sin(a), 5.0)) for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)]
        sin = sum(t is None for t in tramos)
        if sin == 8:
            problemas.append("no agarra nada")
        elif sin:
            problemas.append(f"el agujero queda al canto ({sin} de 8 rayos a 2,7 mm del eje sin material)")
        elif np.median([t[0] for t in tramos]) < -TOL_MENOS:
            problemas.append(f"hay material {-np.median([t[0] for t in tramos]):.1f} mm por encima de la cabeza (la cabeza queda enterrada)")
        # cada pata por separado, donde engancha la una (r 2,25-2,45 en +-x): la cara de salida entre agarre - 0,3 y
        # agarre + 0,15 (el hombro de la una esta en agarre + 0,2). 2026-10-25: la mediana de 8 rayos dejaba pasar una
        # pata sobre el chaflan del hueco del tubo (r_tap_colg: salia en 7,75 con el hombro en 6,0)
        for lado, txt in ((1, "+x"), (-1, "-x")):
            fines = [junta(rayo(lado * r, 0.0, 5.0)) for r in (2.25, 2.35, 2.45)]
            if any(f is None for f in fines):
                if sin < 8:
                    problemas.append(f"la pata {txt} no tiene donde trabar")
                continue
            fin = max(f[1] for f in fines)
            if fin > agarre + TOL_MAS:
                problemas.append(f"la pata {txt} sale en {fin:.2f} y el remache es de {agarre:.2f} (el hombro de la una queda adentro)")
            elif fin < agarre - TOL_MENOS:
                problemas.append(f"junta {fin:.2f} mm (pata {txt}) y el remache es de {agarre:.2f}")
            if material_en(rayo(lado * 2.35, 0.0, 5.0), agarre + 0.25, agarre + HUECO_UNA):
                problemas.append("sin hueco para la una (agujero ciego o pieza detras)")
        # agujero libre hasta donde abre la una: por el eje y adentro del agujero (r 1,9 hacia +-x, que es donde la pata
        # podia pegar en el chaflan, y r 1,8 en diagonal)
        for px, py in ((0.0, 0.0), (1.9, 0.0), (-1.9, 0.0), (1.2, 1.4), (-1.2, 1.4), (1.2, -1.4), (-1.2, -1.4)):
            if material_en(rayo(px, py, 0.01), 0.05, agarre + HUECO_UNA):
                problemas.append("el agujero esta tapado")
                break
        # que se pueda meter: detras de la cabeza tiene que haber espacio libre del largo del remache
        # (con la cabeza adentro de un tubo cerrado mide bien pero no hay como meterlo), con el contorno de la cabeza.
        # Orden de armado: la estructura se remacha ANTES de montar los subsistemas y lo comprado, asi que
        # para un remache de la estructura no estorba lo que se monta despues (los de un subsistema, si).
        pasillo = agarre + 1.6 + 2.8 + 15.0     # el remache entero mas 15 mm para empujarlo con el dedo
        bajo_piso = cab[2] - d[2] * pasillo < 0 or cab[2] < 0
        de_estructura = not nombre.startswith(tuple("r_" + s for s in SUBSISTEMAS))
        antes = [m for n, m in mallas.items() if not (de_estructura and (n.startswith(SUBSISTEMAS) or n.startswith("_comprados")))
                 and np.all(cajas[n][0] - 30 < cab + 30) and np.all(cajas[n][1] + 30 > cab - 30)]
        tapado = any(material_en(rayo(px, py, pasillo + 2, antes), -pasillo - 1.7, -1.7) for px, py in PUNTOS_CABEZA)
        if bajo_piso or tapado:
            problemas.append(f"no hay {pasillo:.0f} mm libres detras de la cabeza para meterlo" + (" (el piso)" if bajo_piso else ""))
        # cabeza: estadio de 8 x 3,2 x 1,6 encima de la cara; que nada la pise y que apoye (fuera del agujero, el
        # material tiene que empezar a <= 0,1 de la cabeza en algun punto: 2026-10-25, una cabeza 0,5 mm en el aire pasaba)
        juntos = [rayo(px, py, 6.0) for px, py in PUNTOS_CABEZA]
        if any(material_en(j, -1.7, -0.05) for j in juntos):
            problemas.append("la cabeza choca con algo")
        apoyos = [next((a for a, b in j if b > 0.05), np.inf) for (px, py), j in zip(PUNTOS_CABEZA, juntos) if np.hypot(px, py) > 2.4]
        if sin < 8 and min(apoyos) > 0.1:
            problemas.append(f"la cabeza queda {min(apoyos):.2f} mm en el aire")
        if problemas:
            malos.append((nombre, sorted(set(problemas))))
    return malos


# medidas del remache (comun.scad): cabeza 8 x 3,2 x 1,6, vastago 4, una de 0,45 en 2,6 de largo, ranura 1,2 desde 0,3 agarre
# (desde z -0,6, dentro de la cabeza, si el agarre es menor de 8)
REM_D, REM_PLANO, REM_CAB, REM_GARRA, REM_RANURA = 4.0, 3.2, (8.0, 1.6), 0.45, 1.2


def marco_remache(eje):
    """Ejes locales x, y, z del remache (los de en_marco con no_paralelo en comun.scad): la cabeza es larga en x."""
    z = eje / np.linalg.norm(eje)
    arriba = np.array([0, 0, 1.0]) if abs(z[2]) < 0.9 else np.array([1.0, 0, 0])
    y = arriba - (arriba @ z) * z
    y /= np.linalg.norm(y)
    return np.cross(y, z), y, z


def dentro_remache(p, agarre):
    """p (N,3) en el marco local: True donde hay remache (cabeza, vastago o una, sin la ranura)."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    r_cab, l2 = REM_PLANO / 2, (REM_CAB[0] - REM_PLANO) / 2
    plano = np.abs(y) <= REM_PLANO / 2
    cab = (z >= -REM_CAB[1]) & (z <= 0) & ((np.abs(x) <= l2) | ((np.abs(x) - l2) ** 2 + y ** 2 <= r_cab ** 2))
    ranura = (np.abs(x) < REM_RANURA / 2) & (z > (-0.6 if agarre < 8 else 0.3 * agarre))
    vas = (z > 0) & (z <= agarre + 0.2) & (x ** 2 + y ** 2 <= (REM_D / 2) ** 2)
    rz = REM_D / 2 + REM_GARRA - (REM_D / 2 + REM_GARRA - (REM_D - 0.8) / 2) * (z - agarre - 0.2) / 2.6
    una = (z > agarre + 0.2) & (z <= agarre + 2.8) & (x ** 2 + y ** 2 <= rz ** 2)
    return plano & (cab | ((vas | una) & ~ranura))


def remaches_entre_si(rem, paso=0.2):
    """Pares de remaches cuyos solidos se cruzan (2026-10-25: 6 pares de cabezas se pisaban y ninguna revision lo veia)."""
    malos = []
    g = np.arange(-4.1, 4.11, paso)
    gy = np.arange(-1.7, 1.71, paso)
    for i, (na, aa, ca, ea) in enumerate(rem):
        xa, ya, za = marco_remache(ea)
        X, Y, Z = np.meshgrid(g, gy, np.arange(-1.7, aa + 2.9, paso), indexing="ij")
        loc = np.c_[X.ravel(), Y.ravel(), Z.ravel()]
        loc = loc[dentro_remache(loc, aa)]
        mundo = ca + loc[:, :1] * xa + loc[:, 1:2] * ya + loc[:, 2:] * za
        for nb, ab, cb, eb in rem[i + 1:]:
            if np.linalg.norm(cb - ca) > aa + ab + 12:
                continue
            xb, yb, zb = marco_remache(eb)
            q = mundo - cb
            n = dentro_remache(np.c_[q @ xb, q @ yb, q @ zb], ab).sum()
            if n * paso ** 3 > 0.5:
                malos.append((na, nb, round(n * paso ** 3, 1)))
    return malos


def caja(tri):
    p = tri.reshape(-1, 3)
    return p.min(0), p.max(0)


def choques(nombres, cajas, solo_con=None, umbral=UMBRAL_FIJO):
    """Pares (a, b, mm3) que se meten mas de umbral; mm3 = None si OpenSCAD fallo o falta un STL (2026-10-25: eso
    contaba como 0 mm3, o sea sin choque)."""
    pares = [(a, b) for i, a in enumerate(nombres) for b in nombres[i + 1:]
             if (solo_con is None or solo_con in (a, b))
             and np.all(cajas[a][0] < cajas[b][1] - 0.05) and np.all(cajas[b][0] < cajas[a][1] - 0.05)]

    def uno(par):
        a, b = par
        stl = [CACHE / "ens" / f"{n}.stl" for n in par]
        if not all(s.exists() for s in stl):
            return a, b, None
        with tempfile.TemporaryDirectory() as t:
            s, o = Path(t) / "x.scad", Path(t) / "x.stl"
            s.write_text(f'intersection() {{ import("{stl[0].as_posix()}"); import("{stl[1].as_posix()}"); }}\n')
            r = subprocess.run([str(OPENSCAD), "-o", str(o), str(s)], capture_output=True, text=True)
            log = r.stdout + r.stderr
            if "ERROR:" in log or "WARNING:" in log or not (o.exists() or "top level object is empty" in log):
                return a, b, None
            tri = ex_carro.leer_stl(o) if o.exists() else np.zeros((0, 3, 3))
            return a, b, (ex_carro.volumen_area(tri)[0] if len(tri) else 0.0)

    with ThreadPoolExecutor(HILOS) as ej:
        res = list(ej.map(uno, pares))
    return [(a, b, v) for a, b, v in res if v is None or v > umbral], len(pares)


def mm3(v):
    return "OpenSCAD fallo o falta un STL (no se pudo medir)" if v is None else f"{v:.2f} mm3"


def queja(e):
    """La linea que importa de un ErrorOpenSCAD."""
    lineas = str(e).splitlines()
    return next((l for l in lineas if "ERROR:" in l or "WARNING:" in l), lineas[0])[:200]


def rem_scad(r):
    """Un remache (nombre, agarre, cabeza, eje) como literal de OpenSCAD."""
    v = lambda p: "[" + ", ".join(f"{float(c):.4f}" for c in p) + "]"
    return f'["{r[0]}", {r[1]}, {v(r[2])}, {v(r[3])}]'


def remaches_contra_barrido(ruta, grupo, rem):
    """Remaches de rem que quedan cerca del barrido (STL en ruta) y no van con lo que se mueve (su vastago no atraviesa
    ninguna malla de grupo: esos se mueven con ella), cruzados con el. Devuelve (nombres, mm3 o None si OpenSCAD fallo)."""
    lo_b, hi_b = caja(ex_carro.leer_stl(ruta))
    incl = []
    for r in rem:
        nombre, agarre, cab, eje = r
        x, _, d = marco_remache(eje)
        fin = cab + d * (agarre + 2.8)
        if not (np.all(np.minimum(cab, fin) - 4.5 < hi_b) and np.all(np.maximum(cab, fin) + 4.5 > lo_b)):
            continue
        juntos = [[a - 5.0, b - 5.0] for a, b in intervalos(cab + 2.7 * x - d * 5.0, d, grupo)] if grupo else []
        if not material_en(juntos, 0.05, agarre - 0.05):
            incl.append(r)
    if not incl:
        return [], 0.0
    with tempfile.TemporaryDirectory() as tmp:
        o = Path(tmp) / "x.stl"
        try:
            scad(o, opcional=True, codigo=f'intersection() {{ import("{Path(ruta).as_posix()}"); union() {{ '
                                          + " ".join(f"remache_en({rem_scad(r)});" for r in incl) + " } }")
        except ErrorOpenSCAD:
            return [r[0] for r in incl], None
        return [r[0] for r in incl], ex_carro.volumen_area(ex_carro.leer_stl(o))[0]


DX_FASE = 3000.0   # en una sola corrida de OpenSCAD: lado 0 en su lugar, lado 1 corrido DX y la interseccion corrida 2 DX

# Mecanismos cuyos lados TIENEN que tocarse (2026-10-25: la revision por fases solo miraba que no se metieran, y el vaso
# del escape quedaba a 2 mm del dedo A y a 10 del B sin que nada lo marcara: ni el escape ni el visor eran lo fisico).
# {mecanismo: (pasos donde se tocan o None = todos, direccion en que el lado 1 va hacia el lado 0)}. En cada uno de
# esos pasos, el lado 1 corrido D_TOQUE en esa direccion tiene que meterse en el lado 0 mas de UMBRAL_MOVIL.
# D_TOQUE: el dibujo puede dejar hasta 0,3 de luz a proposito (can_fase: "0,3 antes de apoyar") y aun asi meterse 0,3.
D_TOQUE = 0.6
CONTACTOS = {
    "tap_prensa": (None, (0.0, 0.0, 1.0)),                 # el rodillo (lado 1) sube contra la leva en toda la vuelta
    "can_escape": (None, (0.0, -0.96593, -0.25882)),       # los vasos (lado 1) bajan por los rieles (15 grados) hasta el dedo
}


def medir_fase(lado0, lado1, toque=None):
    """(mm3 del lado 0, del lado 1, de la interseccion, caja de la interseccion, mm3 con el lado 1 corrido toque o None),
    o un texto si OpenSCAD fallo. lado0 y lado1: codigo OpenSCAD de cada lado. Cada lado se mide aparte: un nombre mal
    escrito o un lado que no se dibujo daba 0 mm3 de interseccion, o sea 'sin choque' (2026-10-25)."""
    c = f"{lado0} translate([{DX_FASE}, 0, 0]) {{ {lado1} }} translate([{2 * DX_FASE}, 0, 0]) intersection() {{ {{ {lado0} }} {{ {lado1} }} }}"
    if toque is not None:
        c += (f" translate([{3 * DX_FASE}, 0, 0]) intersection() {{ {{ {lado0} }} "
              f"translate([{toque[0]:.4f}, {toque[1]:.4f}, {toque[2]:.4f}]) {{ {lado1} }} }}")
    with tempfile.TemporaryDirectory() as tmp:
        o = Path(tmp) / "x.stl"
        try:
            scad(o, opcional=True, codigo=c)
        except ErrorOpenSCAD as e:
            return queja(e)
        tri = ex_carro.leer_stl(o)
    cx = tri.mean(axis=1)[:, 0] if len(tri) else np.zeros(0)
    partes = [tri[np.abs(cx - i * DX_FASE) < DX_FASE / 2] - np.array([i * DX_FASE, 0, 0]) for i in range(4)]
    v = [ex_carro.volumen_area(p)[0] if len(p) else 0.0 for p in partes]
    return v[0], v[1], v[2], (caja(partes[2]) if len(partes[2]) else None), (v[3] if toque is not None else None)


def juzgar_fase(n, kk, r):
    """La linea MAL/CHOQUE de un paso medido con medir_fase, o None si esta bien."""
    if isinstance(r, str):
        return f"MAL {n}, paso {kk}: OpenSCAD fallo ({r})"
    if min(r[0], r[1]) <= 0.0:
        return (f"MAL {n}, paso {kk}: el lado {0 if r[0] <= 0 else 1} salio vacio (nombre mal escrito o <sub>_fase no lo "
                "dibuja): no se revisa nada")
    if r[2] > UMBRAL_MOVIL:
        return f"CHOQUE en {n}, paso {kk}: {r[2]:.2f} mm3 entre {r[3][0].round(1)} y {r[3][1].round(1)}"
    if r[4] is not None and r[4] <= UMBRAL_MOVIL:
        return (f"MAL {n}, paso {kk}: los lados no se tocan (el lado 1 corrido {D_TOQUE:g} mm hacia el lado 0 se mete "
                f"{r[4]:.2f} mm3): queda luz de mas, el mecanismo no hace su trabajo o esta dibujado en otro lugar")
    return None


def revisar_fases(sincs):
    """Lineas MAL/CHOQUE de los mecanismos, paso por paso (vacio = todo bien) y cuantos pasos se revisaron."""
    trabajos = [(n, kk) for n, p in sincs for kk in range(p + 1)]

    def toque(n, kk):
        pasos, d = CONTACTOS.get(n, ([], None))
        return None if d is None or (pasos is not None and kk not in pasos) else D_TOQUE * np.array(d)
    with ThreadPoolExecutor(HILOS) as ej:
        res = list(ej.map(lambda t: medir_fase(f'fase("{t[0]}", {t[1]}, 0);', f'fase("{t[0]}", {t[1]}, 1);', toque(*t)), trabajos))
    lineas = [juzgar_fase(n, kk, r) for (n, kk), r in zip(trabajos, res)]
    return [l for l in lineas if l], len(trabajos)


# Recorrido de lo que se mueve (2026-10-25: el barrido de mon_aleta terminaba antes del final del recorrido y nada lo
# miraba). {barrido: lo que lleva en la posicion f del recorrido, f de 0 a 1}, en OpenSCAD con las variables del
# subsistema; pieza("x") es la pieza x en su lugar (el STL de _cache/ens). Lo que lleva tiene que quedar DENTRO de su
# barrido en los dos extremos y en F_RECORRIDO, y la pieza que se mueve tambien en su lugar.
RECORRIDOS = {
    'alm_rotor': 'translate([alm_C[0], alm_C[1], 0]) rotate([0, 0, 360 * f]) translate([-alm_C[0], -alm_C[1], 0]) { pieza("alm_disco"); pieza("alm_tambor"); }',
    'alm_obturador': 'alm_obturador(alm_cie_s * f);',
    'alm_palanca': 'alm_palanca(alm_abre * f);',
    'mon_aleta': 'mon_aleta_en(-mon_reposo + 2 * mon_reposo * f);',
    'tap_dedo_a': 'difference() { translate([0, -tap_carrera_dedo * f, 0]) pieza("tap_dedo_a"); tap_quietos("tap_dedo_a"); }',
    'tap_dedo_b': 'difference() { translate([0, tap_carrera_dedo * f, 0]) pieza("tap_dedo_b"); tap_quietos("tap_dedo_b"); }',
    'tap_pre_leva': 'translate([tap_pre_c[0], 0, tap_z_leva]) rotate([0, 360 * f, 0]) translate([-tap_pre_c[0], 0, -tap_z_leva]) pieza("tap_pre_leva");',
    'tap_pre_plato': 'difference() { translate([0, 0, -2 * tap_exc * f]) { pieza("tap_pre_plato"); pieza("tap_pre_horquilla"); pieza("tap_pre_rodillo"); } tap_quietos("tap_pre_plato"); }',
    'tap_emp_paleta': 'difference() { translate([0, -67.5 * f, 0]) { pieza("tap_emp_paleta"); pieza("tap_emp_carro"); } tap_quietos("tap_emp_paleta"); }',
    'tap_emp_manivela': 'difference() { translate([tap_emp_x, tap_emp_ys, 0]) rotate([0, 0, -180 * f]) translate([-tap_emp_x, -tap_emp_ys, 0]) pieza("tap_emp_manivela"); tap_quietos("tap_emp_manivela"); }',
    'can_balancin': 'multmatrix(CAN_ME) rotate([0, -can_th0 + 2 * can_th0 * f, 0]) can_balancin_loc();',
    'can_vaso': 'can_vaso_en(can_y_entra + (can_y_fin_barrido - can_y_entra) * f);'
}
# los extremos y 7 posiciones que no caen en las copias de los barridos hechos a pasos (entre copia y copia queda aire)
F_RECORRIDO = (0.0, 1 / 14, 3 / 14, 5 / 14, 7 / 14, 9 / 14, 11 / 14, 13 / 14, 1.0)
# Lo que queda fuera se erosiona 0,3 mm antes de medirlo: las restas a proposito del barrido (estria, pernos, goma, lo
# comprado que va con la pieza, con 0,1-0,15 de holgura) y las facetas dejan astillas de menos de 0,4 mm de espesor
EROSION = 0.3
_EROS = [EROSION * np.array(v) / np.linalg.norm(v) for v in
         [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)] + [(a, b, c) for a in (-1, 1) for b in (-1, 1) for c in (-1, 1)]]


def medir_recorrido(n, piezas):
    """[(donde, mm3 fuera del barrido, caja o None)] de lo que lleva el barrido n, o un texto si OpenSCAD fallo."""
    ens = lambda p: f'import("{(CACHE / "ens" / f"{p}.stl").as_posix()}");'
    pos = [("en su lugar", ens(n))] if n in piezas else []
    if n in RECORRIDOS:
        cod = re.sub(r'(?<!\w)pieza\("([^"]+)"\);', lambda m: ens(m[1]), RECORRIDOS[n])
        pos += [(f"en f = {f:.2f} del recorrido", f"let(f = {f}) {{ {cod} }}") for f in F_RECORRIDO]
    if not pos:
        return []
    sub = n.split("_")[0]
    comp = CACHE / "ens" / f"_comprados_{sub}.stl"
    quitar = f'import("{(CACHE / "barr" / f"{n}.stl").as_posix()}");' + (f' import("{comp.as_posix()}");' if comp.exists() else "")
    fuera = " ".join(f"translate([{i * DX_FASE}, 0, 0]) difference() {{ {{ {p} }} {quitar} }}" for i, (_, p) in enumerate(pos))
    c = "intersection() { " + " ".join(f"translate([{v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f}]) {{ {fuera} }}" for v in _EROS) + " }"
    with tempfile.TemporaryDirectory() as tmp:
        o = Path(tmp) / "x.stl"
        try:
            scad(o, opcional=True, codigo=c)
        except ErrorOpenSCAD as e:
            return queja(e)
        tri = ex_carro.leer_stl(o)
    cx = tri.mean(axis=1)[:, 0] if len(tri) else np.zeros(0)
    out = []
    for i, (donde, _) in enumerate(pos):
        p = tri[np.abs(cx - i * DX_FASE) < DX_FASE / 2] - np.array([i * DX_FASE, 0, 0])
        out.append((donde, ex_carro.volumen_area(p)[0] if len(p) else 0.0, caja(p) if len(p) else None))
    return out


def revisar_recorridos(movs, piezas):
    """Lineas MAL de lo que se mueve que queda fuera de su propio barrido (vacio = todo bien) y cuantas posiciones."""
    with ThreadPoolExecutor(HILOS) as ej:
        res = list(ej.map(lambda m: medir_recorrido(m[0], piezas), movs))
    lineas, n_pos = [], 0
    for (n, _), r in zip(movs, res):
        if isinstance(r, str):
            lineas.append(f"MAL {n}: OpenSCAD fallo al ponerlo en su recorrido ({r})")
            continue
        n_pos += len(r)
        malas = [x for x in r if x[1] > UMBRAL_MOVIL]
        if malas:
            donde, v, cj = max(malas, key=lambda x: x[1])
            lineas.append(f"MAL {n}: queda FUERA de su barrido en {len(malas)} de {len(r)} posiciones (mas de {2 * EROSION:g} mm de "
                          f"espesor; peor {donde}: {v:.2f} mm3 entre {cj[0].round(1)} y {cj[1].round(1)}): el barrido no "
                          "cubre todo el recorrido y lo que choque ahi no se ve")
    return lineas, n_pos


def revisar_cama(tri, n=None):
    """(fallas, avisos) de la pieza n en la orientacion de la cama: sin soportes y que quepa."""
    lo, hi = caja(tri)
    med = hi - lo
    r = volad.revisar(tri)
    fallas = volad.mal(r, n)
    if not (min(med[:2]) <= CAMA_UTIL[0] and max(med[:2]) <= CAMA_UTIL[1] and med[2] <= CAMA_UTIL[2]):
        fallas.append(f"no cabe en la cama: {med.round(1)}")
    avisos = [f"angosta colgada de una pared a lo largo ({c['mm2']} mm2 en z {c['z']}, x {c['x']}, y {c['y']}): "
              "puede quedar algo caida" for c in r["colgadas"][:2]]
    avisos += [f"puente de {c['puente']} mm en z {c['z']}, x {c['x']}, y {c['y']}, aceptado a mano (voladizos.PUENTES_ACEPTADOS): "
               "puede quedar algo caido" for c in r.get("colgados", []) if volad.aceptado(c, n)]
    return fallas, avisos


def revisar_primera_capa(n, m, PC):
    """(fallas, avisos) de la cara que apoya (m = primera_capa.medir de la pieza n)."""
    fallas, avisos = [], []
    # una ranura o tira de menos de 1,2 mm es tan mala como un agujero chico (2026-10-25): cuentan juntas
    bucles = m["chicos"] + m["angostas"]
    txt = (f"{m['chicos']} agujero(s) < {PC.D_CHICO:g} mm (d min {m['d_min']}) y {m['angostas']} ranura(s) o tira(s) "
           f"< {PC.ANCHO_MIN:g} mm")
    if m["islas"] > 1 or bucles > PC.CHICOS_MAX:
        fallas.append(f"{m['islas']} islas, {txt} (maximo {PC.CHICOS_MAX} entre los dos)")
    elif bucles:
        avisos.append(f"en la primera capa: {txt}")
    # la base (2026-10-25): de pie sobre un canto angosto se tambalea con la boquilla y se despega
    esb = PC.esbeltez(n, m)
    if esb > PC.ESBELTEZ_MAX or m["cdm_margen"] < -3.0:
        fallas.append(f"{m['alto']:.0f} de alto sobre una base de {m['base_min']:.1f} (esbeltez {esb:.1f} con brim de "
                      f"{PC.BRIM_OBJETO.get(n, PC.BRIM_DEF):g}; maximo {PC.ESBELTEZ_MAX:g}), centro de masa a {m['cdm_margen']:+.1f} del borde de la base")
    elif m["despegue_mpa"] > PC.DESPEGUE_MAX and n not in PC.BRIM_OBJETO:
        fallas.append(f"despegue de {m['despegue_mpa']:.2f} MPa en la base (> {PC.DESPEGUE_MAX:g}): necesita brim propio "
                      "(primera_capa.BRIM_OBJETO) o acostarla")
    elif m["despegue_mpa"] > PC.DESPEGUE_MAX:
        avisos.append(f"despegue de {m['despegue_mpa']:.2f} MPa en la base (va con brim propio de {PC.BRIM_OBJETO[n]:g})")
    elif m["cdm_margen"] < 0:
        avisos.append(f"el centro de masa cae {-m['cdm_margen']:.1f} mm fuera de la base (va con brim de "
                      f"{PC.BRIM_OBJETO.get(n, PC.BRIM_DEF):g})")
    return fallas, avisos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", default="", help="prefijo de las piezas a revisar (alm, mon, vas, can, ...)")
    ap.add_argument("--sin-render", action="store_true", help="usar los STL que ya estan en _cache (avisa si estan viejos)")
    args = ap.parse_args()
    sub = args.sub
    h0 = huella()          # lo que se revisa: si un .scad cambia durante la corrida, no se sella
    piezas, rem, hay_comprados = listas()
    fallas = 0
    print("== _cache ==")
    if args.sin_render:
        v = viejos(rutas_cache(piezas, hay_comprados))
        if v:
            print(f"  MAL {len(v)} STL de _cache faltan o se dibujaron con otros .scad (correr sin --sin-render): "
                  f"{', '.join(f'{r.parent.name}/{r.stem}' for r in v[:12])}{' ...' if len(v) > 12 else ''}")
            fallas += 1
    else:
        for e in renderizar(piezas, hay_comprados):
            print(f"  MAL no se pudo dibujar {e}")
            fallas += 1
    todos = piezas + (COMPRADOS if hay_comprados else [])
    todos = [n for n in todos if (CACHE / "ens" / f"{n}.stl").exists()]
    mallas = {n: ex_carro.leer_stl(CACHE / "ens" / f"{n}.stl") for n in todos}
    mallas = {n: m for n, m in mallas.items() if len(m)}
    cajas = {n: caja(m) for n, m in mallas.items()}
    mias = [n for n in piezas if n.startswith(sub)]
    rem_mios = [r for r in rem if sub == "" or r[0].startswith(f"r_{sub}")]

    print(f"== remaches ({len(rem_mios)} de {len(rem)}) ==")
    malos = revisar_remaches(rem_mios, mallas, cajas)
    for n, p in malos:
        print(f"  MAL {n}: {'; '.join(p)}")
    fallas += len(malos)

    for a, b, vol in remaches_entre_si(rem if not sub else [r for r in rem if any(
            np.linalg.norm(r[2] - m[2]) < 40 for m in rem_mios)]):
        if sub == "" or a.startswith(f"r_{sub}") or b.startswith(f"r_{sub}"):
            print(f"  MAL {a} y {b}: los remaches se cruzan ({vol} mm3)")
            fallas += 1

    print(f"== choques ({len(mias)} piezas) ==")
    nombres = sorted(set(mias) | ({f"_comprados_{sub}"} if sub else set(COMPRADOS)))
    if sub:   # contra todo lo demas tambien
        nombres = sorted(set(nombres) | set(todos))
    malos, n_pares = choques([n for n in nombres if n in mallas], cajas)
    malos = [m for m in malos if de_sub(m[0], sub) or de_sub(m[1], sub)]
    for a, b, vol in malos:
        print(f"  CHOQUE {a} con {b}: {mm3(vol)}")
    print(f"  ({n_pares} pares que se tocan revisados; lo comprado va en un STL por subsistema)")
    fallas += len(malos)

    # piezas que se mueven: su BARRIDO (todo el recorrido) no puede chocar con nada que no se mueva con ella
    movs = [(n, ex) for n, ex in MOVILES if not sub or n.startswith(sub)]
    print(f"== piezas que se mueven, barridas en todo su recorrido ({len(movs)} de {len(MOVILES)}) ==")
    for n, excluir in movs:
        if not (CACHE / "barr" / f"{n}.stl").exists():
            continue        # ya salio como MAL al dibujar
        tri = ex_carro.leer_stl(CACHE / "barr" / f"{n}.stl")
        clave = f"~barrido~{n}"
        ex_carro.escribir_stl(CACHE / "ens" / f"{clave}.stl", tri)      # choques() las busca en ens/
        cajas_b = dict(cajas)
        cajas_b[clave] = caja(tri)
        otros = [o for o in cajas if o != n and o not in excluir and not o.startswith("~")]
        malos_b, _ = choques([clave] + otros, cajas_b, solo_con=clave, umbral=UMBRAL_MOVIL)
        for a, b, vol in malos_b:
            print(f"  CHOQUE al moverse {n} con {b if a == clave else a}: {mm3(vol)}")
        fallas += len(malos_b)
        (CACHE / "ens" / f"{clave}.stl").unlink(missing_ok=True)
    # barrido contra barrido: con los barridos que haya en _cache/barr (los de los otros subsistemas tambien, vigentes)
    excl = dict(MOVILES)
    hay = [n for n, _ in MOVILES if (CACHE / "barr" / f"{n}.stl").exists()]
    pares = [(a, b) for i, a in enumerate(hay) for b in hay[i + 1:]
             if (not sub or a.startswith(sub) or b.startswith(sub))
             and b not in excl.get(a, []) and a not in excl.get(b, [])]
    if pares:
        for a, b in pares:
            for n in (a, b):
                ex_carro.escribir_stl(CACHE / "ens" / f"~b~{n}.stl", ex_carro.leer_stl(CACHE / "barr" / f"{n}.stl"))
        cajas_bb = {f"~b~{n}": caja(ex_carro.leer_stl(CACHE / "barr" / f"{n}.stl")) for n in hay}
        malos_bb = []
        for a, b in pares:
            m, _ = choques([f"~b~{a}", f"~b~{b}"], cajas_bb, umbral=UMBRAL_MOVIL)
            malos_bb += m
        for a, b, vol in malos_bb:
            print(f"  CHOQUE entre dos cosas que se mueven: {a[3:]} con {b[3:]}: {mm3(vol)} "
                  "(si nunca se mueven a la vez, declararlo en la lista de excluidos de MOVILES)")
        fallas += len(malos_bb)
        for n in hay:
            (CACHE / "ens" / f"~b~{n}.stl").unlink(missing_ok=True)
        print(f"  ({len(pares)} pares de barridos revisados)")

    # lo que se mueve dentro de su propio barrido, en todo el recorrido (si no, lo que choca ahi no se ve)
    print("== lo que se mueve, dentro de su propio barrido (extremos incluidos) ==")
    lineas, n_pos = revisar_recorridos([m for m in movs if (CACHE / "barr" / f"{m[0]}.stl").exists()], piezas)
    lineas += [f"MAL revisar.RECORRIDOS nombra {n}, que no esta en MOVILES (nombre mal escrito?): no se revisa"
               for n in RECORRIDOS if (not sub or n.startswith(sub)) and n not in dict(MOVILES)]
    for l in lineas:
        print("  " + l)
    fallas += len(lineas)
    sin = [n for n, _ in movs if n not in RECORRIDOS]
    print(f"  ({n_pos} posiciones revisadas" + (f"; sin recorrido declarado en revisar.RECORRIDOS, solo la pieza en su lugar: "
                                               f"{', '.join(sin)}" if sin else "") + ")")

    # remaches contra lo que se mueve (2026-10-24: no entraban en ningun choque)
    print("== remaches contra lo que se mueve ==")
    n_rb = 0
    for n, excluir in movs:
        if not (CACHE / "barr" / f"{n}.stl").exists():
            continue
        incl, vol = remaches_contra_barrido(CACHE / "barr" / f"{n}.stl", [mallas[g] for g in [n] + list(excluir) if g in mallas], rem)
        n_rb += len(incl)
        if vol is None or vol > UMBRAL_MOVIL:
            print(f"  CHOQUE al moverse {n} con remaches ({mm3(vol)}; cerca: {', '.join(incl[:6])})")
            fallas += 1
    print(f"  ({n_rb} remaches cerca de lo que se mueve revisados)")

    # mecanismos fase por fase: lado 0 (lo que mueve) contra lado 1 (lo que lo sigue) en cada paso
    sincs = [(n, p) for n, p in SINCRONOS if not sub or n.startswith(sub)]
    print(f"== mecanismos, fase por fase ({len(sincs)} de {len(SINCRONOS)}; que se toquen: {', '.join(CONTACTOS)}) ==")
    lineas, n_pasos = revisar_fases(sincs)
    lineas += [f"MAL revisar.CONTACTOS nombra {n}, que no esta en SINCRONOS (nombre mal escrito?): no se revisa"
               for n in CONTACTOS if (not sub or n.startswith(sub)) and n not in dict(SINCRONOS)]
    for l in lineas:
        print("  " + l)
    fallas += len(lineas)
    print(f"  ({n_pasos} pasos revisados)")

    print("== sin soportes y cama (caras que miran abajo y capa por capa: nada nace en el aire ni cuelga de una punta) ==")
    with ThreadPoolExecutor(HILOS) as ej:      # capa por capa tarda ~1 s por pieza (numpy suelta el GIL)
        camas = dict(zip(mias, ej.map(lambda n: revisar_cama(ex_carro.leer_stl(CACHE / "cama" / f"{n}.stl"), n), mias)))
    for n in mias:
        mal, av = camas[n]
        for t in av:
            print(f"  aviso {n}: {t}")
        if mal:
            print(f"  MAL {n}: {'; '.join(mal)}")
            fallas += 1
    # primera capa (2026-10-24): islas sueltas y agujeros chicos en la cara de apoyo se levantan (ver primera_capa.py)
    import primera_capa as PC
    print("== primera capa: islas, agujeros chicos y base de la cara que apoya ==")
    with ThreadPoolExecutor(HILOS) as ej:
        medidas = dict(zip(mias, ej.map(PC.medir, [CACHE / "cama" / f"{n}.stl" for n in mias])))
    for n in mias:
        mal, av = revisar_primera_capa(n, medidas[n], PC)
        for t in mal:
            print(f"  MAL {n}: {t}")
        for t in av:
            print(f"  aviso {n}: {t}")
        fallas += len(mal)
    if not sub:      # solo una revision completa sella (o borra el sello) para exportar.py
        if not fallas and huella() == h0:
            SELLO_OK.write_text(h0)
        else:
            SELLO_OK.unlink(missing_ok=True)
            if not fallas:
                print("  MAL un .scad cambio durante la revision: no se sella para exportar.py (correrla otra vez)")
                fallas += 1
    print("TODO OK" if not fallas else f"{fallas} problemas")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
