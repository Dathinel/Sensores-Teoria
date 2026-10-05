"""Fisica vs 3D (punto g, 2026-09-28): lo que SIMULA PyBullet tiene las mismas
medidas que lo que DIBUJA el visor 3D, y la fisica real cumple lo que el 3D
promete.

Tres fuentes que tienen que coincidir:

- PyBullet: los URDF de `sim/urdf/`, los cuerpos que crea `sim/mundo.py`
  (monedas, vasos) y el mundo del carro de `sim/vehiculo_sim.py` (carro,
  muros, muelle). Se MIDEN con PyBullet (getCollisionShapeData, getAABB,
  getVisualShapeData, getDynamicsInfo), no se leen de las constantes.
- El visor: lee `sim/geometria.py` (JSON de /api/geometria) y, donde tiene
  numeros fijos en `app/visor3d/piezas/*.js` o `visor.js`, se leen con regex.
- La configuracion: `config/parametros.yaml` y `config/monedas.yaml`.

Y chequeos de fisica en DIRECT: cada moneda con su masa y diametro, una
moneda soltada sobre el tubo del carrusel cae adentro, el vaso cuelga de su
pestana en los rieles de la canaleta (y sin pestana se cae entre ellos), y el
carro con el vaso no vuelca en las evasiones.

`python tests/sim/test_fisica_vs_3d.py` escribe el informe docs/fisica-vs-3d.md
con la tabla de todas las medidas.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

import pybullet as p
import pytest

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:          # para correrlo como script (informe)
    sys.path.insert(0, str(RAIZ))

from app import configuracion  # noqa: E402
from control.monedas import TABLA_MONEDAS  # noqa: E402
from sim import mundo  # noqa: E402
from sim.geometria import ANCHO_CINTA_MONEDAS_M, ANCHO_CINTA_VASOS_M, geometria_completa  # noqa: E402

VISOR = RAIZ / "app" / "visor3d"
TOL = 0.0005   # 0,5 mm


@pytest.fixture(scope="module")
def parametros():
    return configuracion.cargar_parametros()


@pytest.fixture(scope="module")
def geo(parametros):
    return geometria_completa(parametros)


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------

def _js(archivo: str, patron: str) -> str:
    """Primer grupo del patron en un archivo del visor (numeros fijos del 3D)."""
    texto = (VISOR / archivo).read_text(encoding="utf-8")
    m = re.search(patron, texto)
    assert m, f"no encontre /{patron}/ en {archivo}: ¿cambio el visor?"
    return m.group(1)


def _cajas_de_colision(cliente, cuerpo, link=-1):
    """[(medidas completas xyz, posicion local)] de las cajas de colision."""
    return [(d[3], d[5]) for d in p.getCollisionShapeData(cuerpo, link, physicsClientId=cliente)
            if d[2] == p.GEOM_BOX]


def _visuales(cliente, cuerpo, tipo):
    return [d for d in p.getVisualShapeData(cuerpo, physicsClientId=cliente) if d[2] == tipo]


def _escena():
    """EscenaEstacion SIN otra conexion abierta: sim/mundo.py llama a PyBullet
    sin physicsClientId (conexion 0)."""
    return mundo.EscenaEstacion()


# ---------------------------------------------------------------------------
# cintas: ancho, largo, paso de casilla, estaciones
# ---------------------------------------------------------------------------

def medir_cintas(geo) -> dict:
    escena = _escena()
    try:
        c = escena.cliente
        out = {}
        for nombre, cuerpo, pos, ancho in (("monedas", escena.id_cinta_monedas, mundo.CINTA_MONEDAS_POS,
                                            geo["ancho_cinta_monedas"]),
                                           ("vasos", escena.id_cinta_vasos, mundo.CINTA_VASOS_POS,
                                            geo["ancho_cinta_vasos"])):
            # La banda es la caja de colision delgada (2 mm); la otra, la bancada.
            banda = [b for b in _cajas_de_colision(c, cuerpo) if abs(b[0][2] - 0.002) < 1e-6][0]
            est = geo[f"cinta_{nombre}"]["estaciones"]
            paso = geo[f"cinta_{nombre}"]["separacion"]
            # Lo que dibuja el visor (visor.js: construirCintaMonedas/Vasos).
            if nombre == "monedas":
                antes = float(_js("visor.js", r"const x0 = est\[0\]\[0\] - ([\d.]+) \* paso, x1 = est\[n - 1\]\[0\] \+ paso / 2"))
            else:
                antes = 0.5 if "const x0 = est[0][0] - paso / 2, x1 = est[4][0] + paso / 2" in (
                    VISOR / "visor.js").read_text(encoding="utf-8") else None
            x0_v, x1_v = est[0]["posicion"][0] - antes * paso, est[-1]["posicion"][0] + paso / 2
            x0_pb = pos[0] + banda[1][0] - banda[0][0] / 2
            out[nombre] = {"ancho_pb": banda[0][1], "ancho_visor": ancho, "largo_pb": banda[0][0],
                           "largo_visor": x1_v - x0_v, "x0_pb": x0_pb, "x0_visor": x0_v}
            # Separadores del URDF (visuales, 3 mm): su paso.
            # (Con regex y no con un parser XML: los comentarios del URDF llevan "--", que
            # PyBullet acepta pero el XML estricto no.)
            urdf = (mundo.DIRECTORIO_URDF / f"cinta_{nombre}.urdf").read_text(encoding="utf-8")
            xs = sorted(float(x) for x in re.findall(
                r'<box size="0\.003 [\d.]+ [\d.]+"/></geometry><origin xyz="(-?[\d.]+) 0 ', urdf))
            out[nombre]["paso_urdf"] = {round(b - a, 5) for a, b in zip(xs, xs[1:])}
            out[nombre]["paso_visor"] = paso
        # Una moneda puesta en E1 y avanzada: queda justo en cada estacion del visor.
        m = TABLA_MONEDAS[0]
        el = escena.crear_elemento(tipo="moneda", clase_real=m.clase, metal=True, diametro_mm=m.diametro_mm,
                                   masa_g=m.masa_g)
        recorrido = []
        for k in range(mundo.NUM_ESTACIONES_MONEDAS):
            x, y, _ = p.getBasePositionAndOrientation(el.body_id)[0]
            ex, ey, _ = geo["cinta_monedas"]["estaciones"][k]["posicion"]
            recorrido.append(math.hypot(x - ex, y - ey))
            if k < mundo.NUM_ESTACIONES_MONEDAS - 1:
                escena.avanzar_casilla_monedas()
        out["error_estaciones_monedas"] = max(recorrido)
        v = escena.crear_vaso(casilla=0)
        recorrido = []
        for k in range(mundo.NUM_ESTACIONES_VASOS):
            x, y, _ = p.getBasePositionAndOrientation(v.body_id)[0]
            ex, ey, _ = geo["cinta_vasos"]["estaciones"][k]["posicion"]
            recorrido.append(math.hypot(x - ex, y - ey))
            if k < mundo.NUM_ESTACIONES_VASOS - 1:
                escena.avanzar_casilla_vasos()
        out["error_estaciones_vasos"] = max(recorrido)
        return out
    finally:
        escena.cerrar()


def test_cintas_mismo_ancho_largo_y_paso(geo, parametros):
    m = medir_cintas(geo)
    for nombre in ("monedas", "vasos"):
        assert abs(m[nombre]["ancho_pb"] - m[nombre]["ancho_visor"]) < TOL, nombre
        # La banda de vasos del URDF es 5 mm mas corta que la bancada (la del visor va de
        # separador a separador): se acepta hasta 5 mm.
        assert abs(m[nombre]["largo_pb"] - m[nombre]["largo_visor"]) <= 0.005 + 1e-9, nombre
        assert abs(m[nombre]["x0_pb"] - m[nombre]["x0_visor"]) <= 0.0025 + 1e-9, nombre
    assert m["monedas"]["paso_urdf"] == {0.04} == {parametros["cinta_monedas"]["separacion_casilla_mm"] / 1000}
    assert m["vasos"]["paso_urdf"] == {0.08} == {parametros["vasos"]["separacion_casilla_mm"] / 1000}
    assert m["monedas"]["paso_visor"] == 0.04


def test_las_piezas_pasan_exactamente_por_las_estaciones_del_visor(geo):
    m = medir_cintas(geo)
    assert m["error_estaciones_monedas"] < 1e-4
    assert m["error_estaciones_vasos"] < 1e-4


# ---------------------------------------------------------------------------
# almacen: tubos del carrusel, tolva, bandeja de rechazo de vasos
# ---------------------------------------------------------------------------

def medir_almacen(geo) -> dict:
    escena = _escena()
    try:
        c = escena.cliente
        base = mundo.CINTA_VASOS_POS
        cil = _visuales(c, escena.id_cinta_vasos, p.GEOM_CYLINDER)
        # dims de un cilindro visual: (largo, radio, -); posicion relativa al link.
        tubos_pb = sorted(((base[0] + d[5][0], base[1] + d[5][1], base[2] + d[5][2] - d[3][0] / 2), d[3][1], d[3][0])
                          for d in cil if abs(d[3][0] - mundo.TUBO_ALTO_M) < 0.004 and d[3][1] < 0.02)
        tubos_visor = sorted((tuple(t["base"]), t["radio"], t["alto"]) for t in geo["almacen"]["tubos"])
        tolva = [d for d in cil if abs(d[5][0] - (mundo.salida_tolva()[0] - base[0])) < 1e-4 and d[3][1] > 0.017]
        # Bandeja de rechazo de vasos: link fijo del URDF.
        j = mundo.EscenaEstacion._indice_junta(escena.id_cinta_vasos, "junta_bandeja_rechazo")
        bandeja = p.getLinkState(escena.id_cinta_vasos, j)[4]
        return {"tubos_pb": tubos_pb, "tubos_visor": tubos_visor,
                "tolva_radio_pb": tolva[0][3][1] if tolva else None, "tolva_radio_visor": geo["almacen"]["tolva"]["radio"],
                "tolva_z_pb": (base[2] + tolva[0][5][2] - tolva[0][3][0] / 2, base[2] + tolva[0][5][2] + tolva[0][3][0] / 2)
                if tolva else None,
                "tolva_z_visor": (geo["almacen"]["tolva"]["z_abajo"], geo["almacen"]["tolva"]["z_arriba"]),
                "bandeja_pb": bandeja, "bandeja_visor": geo["bandeja_rechazo_vasos"]}
    finally:
        escena.cerrar()


def test_tubos_del_carrusel_en_el_mismo_lugar_en_pybullet_y_en_el_visor(geo):
    """Antes (hasta 2026-09-28) el URDF dibujaba los 6 tubos centrados en el
    llenado y 7 mm mas altos: las monedas guardadas (sim/mundo.py,
    posicion_tubo) quedaban FUERA de sus tubos en la ventana de PyBullet."""
    a = medir_almacen(geo)
    assert len(a["tubos_pb"]) == len(a["tubos_visor"]) == 6
    for (pb, r_pb, h_pb), (vi, r_vi, h_vi) in zip(a["tubos_pb"], a["tubos_visor"]):
        assert math.dist(pb, vi) < TOL
        assert abs(r_pb - (r_vi + 0.001)) < 1e-6      # visor: radio interior + 1 mm de pared
        assert abs(h_pb - h_vi) < TOL


def test_tolva_y_bandeja_de_rechazo_de_vasos_coinciden(geo):
    a = medir_almacen(geo)
    assert a["tolva_radio_pb"] is not None and abs(a["tolva_radio_pb"] - a["tolva_radio_visor"]) < TOL
    assert abs(a["tolva_z_pb"][0] - a["tolva_z_visor"][0]) < TOL and abs(a["tolva_z_pb"][1] - a["tolva_z_visor"][1]) < TOL
    assert math.dist(a["bandeja_pb"][:2], a["bandeja_visor"][:2]) < TOL
    assert a["bandeja_pb"][2] < 0.01                    # en el piso, como en el visor


# ---------------------------------------------------------------------------
# monedas y vasos: masa y medidas de cada cuerpo
# ---------------------------------------------------------------------------

def medir_monedas() -> list[dict]:
    escena = _escena()
    try:
        filas = []
        for m in TABLA_MONEDAS:
            el = escena.crear_elemento(tipo="moneda", clase_real=m.clase, metal=True, diametro_mm=m.diametro_mm,
                                       masa_g=m.masa_g)
            masa = p.getDynamicsInfo(el.body_id, -1)[0]
            forma = p.getCollisionShapeData(el.body_id, -1)[0]
            filas.append({"clase": m.clase, "masa_pb_g": masa * 1000, "masa_yaml_g": m.masa_g,
                          "diam_pb_mm": forma[3][1] * 2000, "diam_yaml_mm": m.diametro_mm})
            p.removeBody(el.body_id)
            escena.elementos_monedas.remove(el)
        return filas
    finally:
        escena.cerrar()


def test_cada_moneda_con_la_masa_y_el_diametro_de_monedas_yaml():
    for f in medir_monedas():
        assert abs(f["masa_pb_g"] - f["masa_yaml_g"]) < 1e-6, f
        assert abs(f["diam_pb_mm"] - f["diam_yaml_mm"]) < 1e-6, f


def test_el_vaso_de_pybullet_mide_lo_de_la_configuracion(parametros, geo):
    escena = _escena()
    try:
        v = escena.crear_vaso()
        forma = p.getCollisionShapeData(v.body_id, -1)[0]
        largo, radio = forma[3][0], forma[3][1]
    finally:
        escena.cerrar()
    assert abs(radio * 2 - geo["vaso"]["diametro"]) < TOL
    assert abs(largo - geo["vaso"]["altura"]) < TOL
    assert abs(geo["vaso"]["diametro"] - parametros["vasos"]["diametro_mm"] / 1000) < 1e-9


# ---------------------------------------------------------------------------
# fisica: una moneda soltada sobre el tubo cae adentro
# ---------------------------------------------------------------------------

def _tubo_hueco(cliente, centro_base, radio_interior, alto, pared=0.001, lados=16):
    """Tubo hueco de verdad (PyBullet no tiene cilindros huecos): `lados`
    tablillas alrededor del radio interior, mas el fondo (el obturador)."""
    cuerpos = []
    x, y, z = centro_base
    ancho = 2 * (radio_interior + pared) * math.tan(math.pi / lados) + 0.0005
    for k in range(lados):
        a = 2 * math.pi * k / lados
        r = radio_interior + pared / 2
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[pared / 2, ancho / 2, alto / 2], physicsClientId=cliente)
        cuerpos.append(p.createMultiBody(0, col, -1, [x + r * math.cos(a), y + r * math.sin(a), z + alto / 2],
                                         p.getQuaternionFromEuler([0, 0, a]), physicsClientId=cliente))
    col = p.createCollisionShape(p.GEOM_CYLINDER, radius=radio_interior + pared, height=0.002, physicsClientId=cliente)
    cuerpos.append(p.createMultiBody(0, col, -1, [x, y, z - 0.001], physicsClientId=cliente))
    return cuerpos


def soltar_moneda_en_tubo(moneda, inclinacion_grados=12.0) -> dict:
    """Mundo propio: el tubo que esta en la carga del carrusel, hueco, y la
    moneda soltada 2 cm sobre su boca desde el punto de carga, algo inclinada
    (llega por el canal corto). Devuelve donde quedo."""
    c = p.connect(p.DIRECT)
    try:
        p.setGravity(0, 0, -9.81, physicsClientId=c)
        p.setPhysicsEngineParameter(fixedTimeStep=1 / 240, numSubSteps=4, physicsClientId=c)
        clave = mundo.POSICIONES_CARRUSEL[0]           # el tubo que queda en la carga en reposo
        base = mundo.posicion_tubo(clave)
        _tubo_hueco(c, base, mundo.TUBO_RADIO_M, mundo.TUBO_ALTO_M)
        cx, cy = mundo.punto_carga_carrusel()
        r, h = moneda.diametro_mm / 2000, 0.0018       # mismo cilindro que sim/mundo.py
        col = p.createCollisionShape(p.GEOM_CYLINDER, radius=r, height=h, physicsClientId=c)
        cuerpo = p.createMultiBody(moneda.masa_g / 1000, col, -1,
                                   [cx, cy, base[2] + mundo.TUBO_ALTO_M + 0.02],
                                   p.getQuaternionFromEuler([math.radians(inclinacion_grados), 0, 0]),
                                   physicsClientId=c)
        p.changeDynamics(cuerpo, -1, lateralFriction=0.3, physicsClientId=c)
        for _ in range(480):
            p.stepSimulation(physicsClientId=c)
        (x, y, z), _ = p.getBasePositionAndOrientation(cuerpo, physicsClientId=c)
        return {"clase": moneda.clase, "dist_eje_mm": math.hypot(x - base[0], y - base[1]) * 1000,
                "altura_sobre_fondo_mm": (z - base[2]) * 1000, "carga_vs_tubo_mm": math.hypot(cx - base[0], cy - base[1]) * 1000}
    finally:
        p.disconnect(c)


@pytest.mark.parametrize("moneda", [m for m in TABLA_MONEDAS if m.verificado], ids=lambda m: m.clase)
def test_una_moneda_soltada_sobre_el_tubo_cae_adentro(moneda):
    r = soltar_moneda_en_tubo(moneda)
    assert r["carga_vs_tubo_mm"] < 0.5                      # el punto de carga es la boca del tubo
    assert r["dist_eje_mm"] < mundo.TUBO_RADIO_M * 1000     # adentro del tubo
    assert r["altura_sobre_fondo_mm"] < moneda.diametro_mm  # llego al fondo (acostada o de canto), no quedo arriba


# ---------------------------------------------------------------------------
# fisica: el vaso cuelga de la pestana en los rieles de la canaleta
# ---------------------------------------------------------------------------

def colgar_vaso_en_rieles(geo, parametros, *, con_pestana=True, segundos=0.35) -> dict:
    """Mundo propio: los dos rieles de la canaleta (geometria del visor: 69 mm
    entre ejes, 4 mm de diametro, 15 grados) forrados en PTFE (roce 0,1), y el
    vaso de config (cuerpo de 62 mm + pestana de 78 mm arriba) apoyado al
    principio. Devuelve si quedo colgado y cuanto bajo por la pendiente."""
    c = p.connect(p.DIRECT)
    try:
        p.setGravity(0, 0, -9.81, physicsClientId=c)
        p.setPhysicsEngineParameter(fixedTimeStep=1 / 240, numSubSteps=4, physicsClientId=c)
        k = geo["canaleta"]
        a, b = k["inicio"], k["fin"]
        largo = math.dist(a, b)
        pend = math.atan2(a[2] - b[2], math.hypot(b[0] - a[0], b[1] - a[1]))
        rumbo = math.atan2(b[1] - a[1], b[0] - a[0])
        rr = k["diametro_riel"] / 2
        s = k["separacion_rieles"] / 2
        # Riel: cilindro acostado a lo largo de la canaleta.
        orn = p.getQuaternionFromEuler([0, math.pi / 2 + pend, rumbo])
        for lado in (-1, 1):
            nx, ny = -math.sin(rumbo) * lado * s, math.cos(rumbo) * lado * s
            col = p.createCollisionShape(p.GEOM_CYLINDER, radius=rr, height=largo, physicsClientId=c)
            riel = p.createMultiBody(0, col, -1, [(a[0] + b[0]) / 2 + nx, (a[1] + b[1]) / 2 + ny, (a[2] + b[2]) / 2],
                                     orn, physicsClientId=c)
            p.changeDynamics(riel, -1, lateralFriction=0.1, physicsClientId=c)
        v = parametros["vasos"]
        r_cuerpo, alto = v["diametro_mm"] / 2000, v["altura_mm"] / 1000
        r_boca = r_cuerpo + v["reborde_mm"] / 1000
        formas = [p.createCollisionShape(p.GEOM_CYLINDER, radius=r_cuerpo, height=alto, physicsClientId=c)]
        pos = [[0, 0, 0]]
        if con_pestana:
            formas.append(p.createCollisionShape(p.GEOM_CYLINDER, radius=r_boca, height=0.0012, physicsClientId=c))
            pos.append([0, 0, alto / 2 - 0.0006])
        # Cuerpo compuesto: el vaso y su pestana son una sola pieza.
        col = p.createCollisionShapeArray([p.GEOM_CYLINDER] * len(formas),
                                          radii=[r_cuerpo, r_boca][:len(formas)],
                                          lengths=[alto, 0.0012][:len(formas)],
                                          collisionFramePositions=pos, physicsClientId=c)
        d0 = 0.05                                       # 5 cm despues del embudo de entrada
        ux, uy = math.cos(rumbo), math.sin(rumbo)
        arriba_riel = a[2] - d0 * math.tan(pend) + rr
        # La pestana (arriba del vaso) 1 mm por encima de los rieles; el cuerpo
        # ya metido entre ellos. Vaso lleno: la masa de config (vehiculo).
        vaso = p.createMultiBody(parametros["vehiculo"]["masa_vaso_lleno_kg"], col, -1,
                                 [a[0] + ux * d0, a[1] + uy * d0, arriba_riel + 0.001 + 0.0012 - alto / 2],
                                 physicsClientId=c)
        p.changeDynamics(vaso, -1, lateralFriction=0.1, physicsClientId=c)
        z_arriba_min = 1.0
        for _ in range(int(segundos * 240)):
            p.stepSimulation(physicsClientId=c)
            (x, y, z), _ = p.getBasePositionAndOrientation(vaso, physicsClientId=c)
            # Altura de la boca respecto del riel en ese punto de la canaleta.
            d = (x - a[0]) * ux + (y - a[1]) * uy
            z_arriba_min = min(z_arriba_min, z + alto / 2 - (a[2] - d * math.tan(pend) + rr))
        return {"boca_sobre_riel_mm": z_arriba_min * 1000, "avanzo_mm": (d - d0) * 1000, "z_final": z}
    finally:
        p.disconnect(c)


def test_el_vaso_cuelga_de_la_pestana_en_los_rieles_y_desliza(geo, parametros):
    r = colgar_vaso_en_rieles(geo, parametros)
    # La boca (pestana) sigue apoyada ENCIMA de los rieles (tolerancia de contacto 1,5 mm)...
    assert r["boca_sobre_riel_mm"] > -1.5, r
    # ...y baja por la pendiente de 15 grados sobre el PTFE (no se queda trabado).
    assert r["avanzo_mm"] > 20, r


def test_sin_pestana_el_cuerpo_del_vaso_pasa_entre_los_rieles(geo, parametros):
    """Contraprueba: lo que lo sostiene es la pestana, no el cuerpo (62 mm
    entre rieles a 69 mm: 3,5 mm de holgura, menos 2 mm de radio del riel)."""
    r = colgar_vaso_en_rieles(geo, parametros, con_pestana=False)
    assert r["boca_sobre_riel_mm"] < -20, r


# ---------------------------------------------------------------------------
# carro, ruedas, muelle, pista y muros
# ---------------------------------------------------------------------------

def medir_carro(parametros, geo) -> dict:
    from sim.vehiculo_sim import Z_TOF, SimCarro, medidas_muelle

    carro = SimCarro(parametros)
    try:
        c = carro.cli
        chasis = _cajas_de_colision(c, carro.carro)[0][0]
        # La llanta es compuesta (banda de rodadura al centro + dos hombros, sim/vehiculo_sim.py):
        # el ancho es de cara a cara de todas sus partes, y el radio el de la banda (la mas grande).
        partes = p.getCollisionShapeData(carro.carro, 0, physicsClientId=c)
        rueda = max(partes, key=lambda d: d[3][1])
        ancho_llanta = 2 * max(abs(d[5][2]) + d[3][0] / 2 for d in partes)
        # Posicion de la rueda y de la rueda loca en el marco del carro (links 0 y 2).
        info = [p.getJointInfo(carro.carro, j, physicsClientId=c) for j in range(p.getNumJoints(carro.carro, physicsClientId=c))]
        muros = []
        for m, o in zip(carro.muros, geo["pista"]["obstaculos"]):
            lo, hi = p.getAABB(m, physicsClientId=c)
            (x, y, _), _ = p.getBasePositionAndOrientation(m, physicsClientId=c)
            dx, dy = abs(math.cos(o["rumbo"])), abs(math.sin(o["rumbo"]))
            # Largo del muro medido a lo ANCHO de la pista y grueso a lo largo (AABB alineada si el
            # muro esta en una recta paralela a un eje).
            a_lo_largo = (hi[0] - lo[0]) if dx > dy else (hi[1] - lo[1])
            a_lo_ancho = (hi[1] - lo[1]) if dx > dy else (hi[0] - lo[0])
            muros.append({"pos_pb": (x, y), "pos_visor": (o["x"], o["y"]), "grueso_pb": a_lo_largo,
                          "grueso_visor": o["grueso"], "largo_pb": a_lo_ancho, "largo_visor": o["largo"],
                          "alto_pb": hi[2] - lo[2], "alto_visor": o["alto"]})
        return {"L_pb": chasis[0], "W_pb": chasis[1], "L_visor": geo["vehiculo"]["largo"], "W_visor": geo["vehiculo"]["ancho"],
                "r_rueda_pb": rueda[3][1], "r_rueda_visor": geo["vehiculo"]["diametro_rueda"] / 2,
                "ancho_rueda_pb": ancho_llanta, "rodadura_pb": rueda[3][0],
                # El visor dibuja la llanta con `v.ancho_rueda` de la geometria (pedido 13a: antes un 26
                # fijo en visor.js); se comprueba que el JS lo lea de ahi y se compara con ese numero.
                "ancho_rueda_visor": geo["vehiculo"]["ancho_rueda"] if _js(
                    "visor.js", r"crearRuedaTT\(\{ diametro: v\.diametro_rueda / MM, ancho: \((v\.ancho_rueda) \?\? [\d.]+\) / MM") else None,
                "x_eje_pb": info[0][14][0], "y_rueda_pb": abs(info[0][14][1]), "x_loca_pb": info[2][14][0],
                "x_ir_pb": carro.x_ir, "z_us_pb": carro.z_us, "z_tof_pb": Z_TOF,
                "muelle_pb": medidas_muelle(carro.cfg),
                "muros": muros, "salida_pb": carro.salida, "salida_visor": geo["pista"]["salida"],
                "largo_linea_pb": carro.largo_linea, "largo_linea_visor": geo["pista"]["largo"]}
    finally:
        carro.cerrar()


def disposicion_visor(L, W, r) -> dict:
    """Los numeros fijos de piezas/carro.js (disposicionCarro) y visor.js (construirMuelle)."""
    f = lambda pat: float(_js("piezas/carro.js", pat))
    return {"x_eje": -f(r"d\.xRueda = -([\d.]+) \* L;") * L, "y_rueda": W / 2 + f(r"d\.yRueda = W / 2 \+ ([\d.]+);"),
            "x_loca": f(r"d\.xLoca = ([\d.]+) \* L;") * L, "x_ir": L / 2 - f(r"d\.xIr = L / 2 - ([\d.]+);"),
            "z_us": r + sum(float(x) for x in re.findall(r"[\d.]+", _js("piezas/carro.js", r"d\.zUs = r \+ ([\d.]+ \+ [\d.]+);"))),
            "z_tof": f(r"d\.zTof = ([\d.]+);"),
            # Muelle (pedido 13a): visor.js lee largo de boca, apertura y holgura de la geometria
            # (vehiculo.muelle_*); aqui se comprueba que las lea y se devuelven esos valores.
            "muelle": _muelle_visor()}


def _muelle_visor() -> tuple[float, float, float]:
    for patron in (r"x2 = x1 \+ (largoBoca);", r"abre: (abreBoca),", r"v\.rodillo_guia_radio \+ \((v\.muelle_holgura) \?\?"):
        _js("visor.js", patron)
    v = geometria_completa(configuracion.cargar_parametros())["vehiculo"]
    return v["muelle_largo_boca"], v["muelle_abre_boca"], v["muelle_holgura"]


def test_carro_y_muelle_iguales_en_pybullet_y_en_el_visor(parametros, geo):
    m = medir_carro(parametros, geo)
    L, W, r = m["L_visor"], m["W_visor"], m["r_rueda_visor"]
    d = disposicion_visor(L, W, r)
    assert abs(m["L_pb"] - L) < TOL and abs(m["W_pb"] - W) < TOL
    assert abs(m["r_rueda_pb"] - r) < TOL
    for clave in ("x_eje", "y_rueda", "x_loca", "x_ir", "z_us", "z_tof"):
        assert abs(m[f"{clave}_pb"] - d[clave]) < TOL, clave
    assert all(abs(a - b) < 1e-9 for a, b in zip(m["muelle_pb"], d["muelle"]))


def test_ruedas_del_mismo_ancho_que_la_rueda_tt_del_visor(parametros, geo):
    """Pedido 13a (2026-09-28): la llanta TT real mide 26 mm; PyBullet tenia 22.
    Ahora las dos salen de config (vehiculo.ancho_rueda_mm)."""
    m = medir_carro(parametros, geo)
    assert abs(m["ancho_rueda_pb"] - parametros["vehiculo"]["ancho_rueda_mm"] / 1000) < TOL
    assert abs(m["ancho_rueda_pb"] - m["ancho_rueda_visor"]) < TOL


def test_pista_y_muros_iguales(parametros, geo):
    m = medir_carro(parametros, geo)
    assert math.dist(m["salida_pb"][:2], (m["salida_visor"]["x"], m["salida_visor"]["y"])) < 1e-9
    assert abs(m["largo_linea_pb"] - m["largo_linea_visor"]) < 0.001
    assert len(m["muros"]) == 3
    for mu in m["muros"]:
        assert math.dist(mu["pos_pb"], mu["pos_visor"]) < TOL
        assert abs(mu["grueso_pb"] - mu["grueso_visor"]) < 0.001
        assert abs(mu["largo_pb"] - mu["largo_visor"]) < 0.001
        assert abs(mu["alto_pb"] - mu["alto_visor"]) < 0.001


def viaje_con_vaso(parametros, semilla=7) -> dict:
    """El viaje completo con el vaso lleno (errores de la configuracion) y el
    peor balanceo/cabeceo del chasis en cada paso de control."""
    from sim.vehiculo_sim import SimCarro

    carro = SimCarro(parametros, errores=True, semilla=semilla)
    peor = {"roll": 0.0, "pitch": 0.0, "z_min": 1.0}

    def medir(c):
        (x, y, z), q = p.getBasePositionAndOrientation(c.carro, physicsClientId=c.cli)
        roll, pitch, _ = p.getEulerFromQuaternion(q)
        peor["roll"] = max(peor["roll"], abs(math.degrees(roll)))
        peor["pitch"] = max(peor["pitch"], abs(math.degrees(pitch)))
        peor["z_min"] = min(peor["z_min"], z)

    carro.al_paso_control = medir
    try:
        carro.cargar_vaso()
        eventos, llegada = [], None
        while carro.tiempo < 500:
            eventos += carro.avanzar(1.0)
            c = carro.control
            if c.estado == "en_meta":
                llegada = llegada or carro.tiempo
                if carro.vaso_cargado and carro.tiempo - llegada >= carro.cfg["espera_descarga_meta_s"]:
                    carro.retirar_vaso()
            if c.estado == "detenido" or (c.estado == "esperando_carga" and c.fase == "vuelta"):
                break
        return dict(peor, evasiones=sum(e["ev"] == "evasion" for e in eventos), toques=carro.toques_muro,
                    vaso=math.degrees(carro.inclinacion_max_vaso), estado=carro.control.estado, r=carro.radio)
    finally:
        carro.cerrar()


def test_el_carro_con_el_vaso_no_vuelca_en_las_evasiones(parametros):
    r = viaje_con_vaso(parametros)
    assert r["evasiones"] == 6 and r["toques"] == 0 and r["estado"] == "esperando_carga", r
    assert r["roll"] < 5 and r["pitch"] < 5, r               # las 3 ruedas siempre en el piso
    assert r["z_min"] > r["r"] - 0.005, r                    # nunca se hunde ni se levanta de lado
    assert r["vaso"] < 5, r


# ---------------------------------------------------------------------------
# canaleta: donde deja PyBullet el vaso entregado
# ---------------------------------------------------------------------------

def medir_vaso_entregado(geo, parametros) -> dict:
    """Donde deja sim/mundo.py el vaso entregado (pedido 13b): cuanto queda su
    boca por encima de la cara de arriba de los rieles (medido perpendicular
    al plano de los rieles, que baja a 15 grados), cuanto esta inclinado y
    cuanto se corre de lado respecto del centro de la canaleta. Los rieles son
    los del visor (geo["canaleta"]), no los de mundo.py."""
    escena = _escena()
    try:
        v = escena.crear_vaso(casilla=mundo.ESTACION_DESCARGA_VASOS)
        escena.activar_empujador_vasos(v, "entrega")
        pos, q = p.getBasePositionAndOrientation(v.body_id)
        eje = p.getMatrixFromQuaternion(q)[2::3]            # columna z: el eje del vaso
    finally:
        escena.cerrar()
    k = geo["canaleta"]
    a, b = k["inicio"], k["fin"]
    u = [(b[i] - a[i]) / math.dist(a, b) for i in range(3)]
    h = math.hypot(u[0], u[1])
    lat = (-u[1] / h, u[0] / h, 0.0)
    n = (lat[1] * u[2] - lat[2] * u[1], lat[2] * u[0] - lat[0] * u[2], lat[0] * u[1] - lat[1] * u[0])
    n = n if n[2] > 0 else tuple(-c for c in n)
    alto = geo["vaso"]["altura"]
    boca = [pos[i] + eje[i] * alto / 2 for i in range(3)]
    rel = [boca[i] - a[i] for i in range(3)]
    sobre_eje = sum(rel[i] * n[i] for i in range(3))
    return {"boca_sobre_riel_mm": (sobre_eje - k["diametro_riel"] / 2) * 1000,
            "inclinacion_grados": math.degrees(math.acos(max(-1.0, min(1.0, eje[2])))),
            "inclinacion_canaleta_grados": parametros["canaleta_entrega"]["inclinacion_grados"],
            "lateral_mm": sum(rel[i] * lat[i] for i in range(3)) * 1000,
            "d_mm": sum(rel[i] * u[i] for i in range(3)) * 1000,
            "eje_perpendicular_a_rieles": abs(sum(eje[i] * u[i] for i in range(3))) < 1e-3}


def test_el_vaso_entregado_queda_apoyado_en_los_rieles(geo, parametros):
    """Pedido 13b (2026-09-28). Antes: derecho y ~2 cm por encima de los
    rieles (xfail). Ahora la pestana (78 mm) queda acostada sobre los rieles
    (69 mm), con la boca el espesor de la pestana por encima, inclinado lo
    mismo que la canaleta (como queda en la prueba fisica de arriba) y en el
    centro de la canaleta, pasado el embudo de entrada."""
    r = medir_vaso_entregado(geo, parametros)
    assert abs(r["boca_sobre_riel_mm"]) < 2, r
    assert abs(r["inclinacion_grados"] - r["inclinacion_canaleta_grados"]) < 0.5, r
    assert r["eje_perpendicular_a_rieles"] and abs(r["lateral_mm"]) < 0.5, r
    assert geo["canaleta"]["largo_embudo"] * 1000 < r["d_mm"] < parametros["canaleta"]["largo_mm"], r


def test_el_vaso_colgado_se_inclina_como_la_canaleta(geo, parametros):
    """La pose que usa sim/mundo.py para el vaso entregado sale de la fisica:
    con la pestana apoyada y deslizando, el vaso se inclina con la canaleta
    (la pestana se acuesta sobre los dos rieles), no cuelga derecho."""
    q = {}
    original = p.getBasePositionAndOrientation

    def espiar(cuerpo, physicsClientId=0):
        r = original(cuerpo, physicsClientId=physicsClientId)
        q["q"] = r[1]
        return r

    p.getBasePositionAndOrientation = espiar
    try:
        colgar_vaso_en_rieles(geo, parametros)
    finally:
        p.getBasePositionAndOrientation = original
    inclinacion = math.degrees(math.acos(p.getMatrixFromQuaternion(q["q"])[8]))
    assert abs(inclinacion - parametros["canaleta_entrega"]["inclinacion_grados"]) < 1.0, inclinacion


# ---------------------------------------------------------------------------
# informe
# ---------------------------------------------------------------------------

def _fila(medida, pb, visor, ok, nota=""):
    return f"| {medida} | {pb} | {visor} | {'sí' if ok else '**NO**'} | {nota} |"


def informe() -> str:
    parametros = configuracion.cargar_parametros()
    geo = geometria_completa(parametros)
    mm = lambda v: f"{v * 1000:.1f} mm"
    filas = []
    ci = medir_cintas(geo)
    for n in ("monedas", "vasos"):
        c = ci[n]
        filas.append(_fila(f"Cinta de {n}: ancho de la banda", mm(c["ancho_pb"]), mm(c["ancho_visor"]),
                           abs(c["ancho_pb"] - c["ancho_visor"]) < TOL))
        filas.append(_fila(f"Cinta de {n}: largo de la banda", mm(c["largo_pb"]), mm(c["largo_visor"]),
                           abs(c["largo_pb"] - c["largo_visor"]) <= 0.005,
                           "URDF: 5 mm mas corta que la bancada (dentro de tolerancia)" if n == "vasos" else
                           "corregido el URDF (antes 160 mm)"))
        filas.append(_fila(f"Cinta de {n}: paso de casilla", ", ".join(mm(x) for x in c["paso_urdf"]),
                           mm(c["paso_visor"]), {round(c["paso_visor"], 5)} == c["paso_urdf"]))
    filas.append(_fila("Estaciones de monedas (moneda real avanzada E1 -> E4)", f"error máx. {ci['error_estaciones_monedas'] * 1000:.3f} mm",
                       "sim/geometria.py", ci["error_estaciones_monedas"] < 1e-4))
    filas.append(_fila("Estaciones de vasos (vaso real avanzado 1 -> 5)", f"error máx. {ci['error_estaciones_vasos'] * 1000:.3f} mm",
                       "sim/geometria.py", ci["error_estaciones_vasos"] < 1e-4))
    al = medir_almacen(geo)
    err = max(math.dist(a[0], b[0]) for a, b in zip(al["tubos_pb"], al["tubos_visor"]))
    filas.append(_fila("Tubos del carrusel (6): posición del fondo", f"error máx. {err * 1000:.2f} mm", "posicion_tubo()",
                       err < TOL, "corregido el URDF (antes centrados en el llenado)"))
    filas.append(_fila("Tubos del carrusel: radio exterior / alto", f"{mm(al['tubos_pb'][0][1])} / {mm(al['tubos_pb'][0][2])}",
                       f"{mm(al['tubos_visor'][0][1] + 0.001)} / {mm(al['tubos_visor'][0][2])}",
                       abs(al["tubos_pb"][0][2] - al["tubos_visor"][0][2]) < TOL, "corregido el alto (antes 65 mm)"))
    filas.append(_fila("Tolva: radio", mm(al["tolva_radio_pb"]), mm(al["tolva_radio_visor"]),
                       abs(al["tolva_radio_pb"] - al["tolva_radio_visor"]) < TOL, "corregido el URDF (antes 50 mm)"))
    filas.append(_fila("Bandeja de rechazo de vasos (x, y)", f"({al['bandeja_pb'][0]:.3f}, {al['bandeja_pb'][1]:.3f}) m",
                       f"({al['bandeja_visor'][0]:.3f}, {al['bandeja_visor'][1]:.3f}) m",
                       math.dist(al["bandeja_pb"][:2], al["bandeja_visor"][:2]) < TOL,
                       "corregido el URDF (estaba al costado, a 10 cm de altura)"))
    for f in medir_monedas():
        if f["clase"].split("_")[1] in ("nueva", "antigua"):
            filas.append(_fila(f"Moneda {f['clase']}: masa / diámetro", f"{f['masa_pb_g']:.2f} g / {f['diam_pb_mm']:.2f} mm",
                               f"{f['masa_yaml_g']:.2f} g / {f['diam_yaml_mm']:.2f} mm (monedas.yaml)",
                               abs(f["masa_pb_g"] - f["masa_yaml_g"]) < 1e-6 and abs(f["diam_pb_mm"] - f["diam_yaml_mm"]) < 1e-6))
    for m in [x for x in TABLA_MONEDAS if x.verificado]:
        r = soltar_moneda_en_tubo(m)
        filas.append(_fila(f"Física: {m.clase} soltada sobre el tubo", f"queda a {r['dist_eje_mm']:.1f} mm del eje, "
                           f"{r['altura_sobre_fondo_mm']:.1f} mm sobre el fondo", f"tubo de {mundo.TUBO_RADIO_M * 2000:.0f} mm",
                           r["dist_eje_mm"] < mundo.TUBO_RADIO_M * 1000 and r["altura_sobre_fondo_mm"] < m.diametro_mm))
    k = geo["canaleta"]
    con = colgar_vaso_en_rieles(geo, parametros)
    sin = colgar_vaso_en_rieles(geo, parametros, con_pestana=False)
    boca = parametros["vasos"]["diametro_mm"] + 2 * parametros["vasos"]["reborde_mm"]
    filas.append(_fila("Canaleta: separación entre rieles", mm(k["separacion_rieles"]),
                       f"{parametros['canaleta']['separacion_rieles_mm']} mm (config; el visor lee la geometría)", True))
    filas.append(_fila(f"Física: vaso (62 mm, pestaña {boca} mm) en los rieles", f"boca {con['boca_sobre_riel_mm']:+.1f} mm "
                       f"sobre el riel; desliza {con['avanzo_mm']:.0f} mm en 0,35 s", "cuelga y baja por la pendiente",
                       con["boca_sobre_riel_mm"] > -1.5 and con["avanzo_mm"] > 20))
    filas.append(_fila("Física: el mismo vaso SIN pestaña", f"cae {-sin['boca_sobre_riel_mm']:.0f} mm entre los rieles",
                       "el cuerpo pasa entre los rieles", sin["boca_sobre_riel_mm"] < -20))
    ve = medir_vaso_entregado(geo, parametros)
    filas.append(_fila("Vaso entregado (donde lo deja sim/mundo.py)",
                       f"boca {ve['boca_sobre_riel_mm']:+.1f} mm sobre el riel, inclinado {ve['inclinacion_grados']:.1f}°",
                       f"apoyado en los rieles, canaleta a {ve['inclinacion_canaleta_grados']}°",
                       abs(ve["boca_sobre_riel_mm"]) < 2
                       and abs(ve["inclinacion_grados"] - ve["inclinacion_canaleta_grados"]) < 0.5,
                       "corregido el 2026-09-28 (antes 21,7 mm por encima y derecho)"))
    ca = medir_carro(parametros, geo)
    d = disposicion_visor(ca["L_visor"], ca["W_visor"], ca["r_rueda_visor"])
    filas.append(_fila("Carro: chasis largo × ancho", f"{mm(ca['L_pb'])} × {mm(ca['W_pb'])}", f"{mm(ca['L_visor'])} × {mm(ca['W_visor'])}",
                       abs(ca["L_pb"] - ca["L_visor"]) < TOL and abs(ca["W_pb"] - ca["W_visor"]) < TOL))
    filas.append(_fila("Carro: diámetro de rueda", mm(ca["r_rueda_pb"] * 2), mm(ca["r_rueda_visor"] * 2),
                       abs(ca["r_rueda_pb"] - ca["r_rueda_visor"]) < TOL))
    filas.append(_fila("Carro: ancho de rueda (banda de rodadura)", f"{mm(ca['ancho_rueda_pb'])} ({mm(ca['rodadura_pb'])})",
                       mm(ca["ancho_rueda_visor"]) + " (crearRuedaTT, config)",
                       abs(ca["ancho_rueda_pb"] - ca["ancho_rueda_visor"]) < TOL, "corregido el 2026-09-28 (antes 22 mm)"))
    for clave, nombre in (("x_eje", "eje de ruedas (x)"), ("y_rueda", "centro de rueda (y)"), ("x_loca", "rueda loca (x)"),
                          ("x_ir", "infrarrojos de línea (x)"), ("z_us", "ultrasónico (z)"), ("z_tof", "láser VL53L0X (z)")):
        filas.append(_fila(f"Carro: {nombre}", mm(ca[f'{clave}_pb']), mm(d[clave]) + " (piezas/carro.js)",
                           abs(ca[f"{clave}_pb"] - d[clave]) < TOL))
    filas.append(_fila("Muelle: largo de boca / apertura / holgura", " / ".join(mm(x) for x in ca["muelle_pb"]),
                       " / ".join(mm(x) for x in d["muelle"]) + " (config, visor.js la lee)",
                       all(abs(a - b) < 1e-9 for a, b in zip(ca["muelle_pb"], d["muelle"]))))
    filas.append(_fila("Pista: largo de la línea central", f"{ca['largo_linea_pb']:.3f} m", f"{ca['largo_linea_visor']:.3f} m",
                       abs(ca["largo_linea_pb"] - ca["largo_linea_visor"]) < 0.001))
    for i, mu in enumerate(ca["muros"]):
        filas.append(_fila(f"Muro {i + 1}: posición / grueso × largo × alto",
                           f"({mu['pos_pb'][0]:.3f}, {mu['pos_pb'][1]:.3f}) / {mm(mu['grueso_pb'])} × {mm(mu['largo_pb'])} × {mm(mu['alto_pb'])}",
                           f"({mu['pos_visor'][0]:.3f}, {mu['pos_visor'][1]:.3f}) / {mm(mu['grueso_visor'])} × {mm(mu['largo_visor'])} × {mm(mu['alto_visor'])}",
                           math.dist(mu["pos_pb"], mu["pos_visor"]) < TOL and abs(mu["grueso_pb"] - mu["grueso_visor"]) < 0.001
                           and abs(mu["largo_pb"] - mu["largo_visor"]) < 0.001 and abs(mu["alto_pb"] - mu["alto_visor"]) < 0.001))
    vj = viaje_con_vaso(parametros)
    filas.append(_fila("Física: viaje completo con el vaso lleno (semilla 7)",
                       f"{vj['evasiones']} evasiones, {vj['toques']} toques, balanceo máx. {vj['roll']:.2f}°, "
                       f"cabeceo máx. {vj['pitch']:.2f}°, vaso {vj['vaso']:.2f}°",
                       "no vuelca, no toca muros", vj["evasiones"] == 6 and vj["toques"] == 0 and vj["roll"] < 5
                       and vj["pitch"] < 5 and vj["vaso"] < 5))
    return "\n".join(filas)


ENCABEZADO = """# Física vs 3D

Qué tan igual es lo que **simula PyBullet** (lo que se mueve y choca de verdad) a lo que **dibuja el
visor 3D** (el boceto que ve el evaluador). Lo genera `python tests/sim/test_fisica_vs_3d.py`; las mismas
medidas son pruebas en `tests/sim/test_fisica_vs_3d.py` (corren con el resto de la suite).

Cómo se mide cada lado:

- **PyBullet**: se le PREGUNTA a PyBullet (formas de colisión, cajas envolventes, formas visuales de
  los URDF, masa de cada cuerpo) sobre los mismos mundos que usan las pruebas y el supervisor:
  `sim/urdf/*.urdf` + `sim/mundo.py` (cintas, monedas, vasos) y `sim/vehiculo_sim.py` (carro, muros,
  muelle). No se leen las constantes: se mide lo que quedó construido.
- **Visor**: lo que manda `sim/geometria.py` al visor (`/api/geometria`) y, donde el visor tiene
  números fijos (`app/visor3d/piezas/carro.js`, `visor.js`), esos números leídos con regex.
- **Física**: mundos chicos en `p.DIRECT` con las piezas reales: una moneda que cae a un tubo hueco
  del tamaño del del carrusel, el vaso colgando de los rieles de la canaleta, y el viaje completo
  del carro con el vaso lleno midiendo balanceo y cabeceo en cada paso de control.

## Tabla

| Medida | PyBullet | Visor / fuente | ¿Coincide? | Nota |
|---|---|---|---|---|
"""

PIE = """
## Qué se corrigió (2026-09-28)

Todo en `sim/urdf/`, que son piezas que la simulación no usaba para decidir nada (visuales o una
banda más larga donde no hay nada) — la fuente de las medidas sigue siendo `sim/mundo.py` /
`sim/geometria.py`, y los URDF ahora las copian:

- **Tubos del carrusel** (`cinta_vasos.urdf`): estaban dibujados en un hexágono centrado en la
  estación de llenado y 7 mm más altos; `sim/mundo.py` guarda las monedas alrededor de
  `centro_carrusel()` (el agujero de la placa queda sobre el llenado, no el centro del carrusel).
  En la ventana de PyBullet las monedas guardadas quedaban FUERA de sus tubos. Ahora cada tubo está
  en `posicion_tubo()`, con 58 mm de alto (`TUBO_ALTO_M`) y 29 + 2 mm de diámetro, como el visor.
- **Tolva** (`cinta_vasos.urdf`): 50 mm de radio → 19 mm, entre las mismas alturas del visor.
- **Bandeja de rechazo de vasos** (`cinta_vasos.urdf`): estaba al costado de la descarga, a 10 cm de
  altura e inclinada (diseño viejo); ahora en el piso al final de la cinta, donde `sim/mundo.py`
  pone los vasos rechazados y donde la dibuja el visor.
- **Banda de la cinta de monedas** (`cinta_monedas.urdf`): 160 → 200 mm; arranca una casilla antes
  de E1, como el visor desde la revisión del 2026-09-26 (espacio para el capacitivo bajo E1).

Y después, en `sim/vehiculo_sim.py`, `sim/mundo.py` y la configuración (antes figuraban abajo, en lo
que NO se corrigió):

- **Llanta del carro y muelle (pedido 13a, 2026-09-28)**: PyBullet usaba una llanta de 22 mm y el
  visor la TT real de 26. Ahora las dos leen `vehiculo.ancho_rueda_mm: 26` de la configuración, y el
  muelle (largo de boca, apertura, holgura) también sale de ahí (`vehiculo.muelle_*`) en vez de
  estar copiado a mano en `visor.js`. Lo que se midió al pasar a 26 mm (56 viajes de ida y vuelta:
  44 semillas, 11 con el doble de error y uno sin error):
  - **El muelle no era el problema**: con 26 mm el carro entró al primer intento en los 56 (0
    reintentos) y la llanta nunca tocó una guía. Las "3 pruebas del muelle" que fallaban
    (`test_entra_al_muelle_sin_reintento` 1 y 6-doble, `test_ida_y_vuelta_con_...[1]`) fallaban por
    tocar un **muro** en la evasión, y la del atasco por llegar en otra pose.
  - **La causa**: un cilindro plano en PyBullet apoya en el piso por UNO de sus bordes y salta de
    uno al otro (contactos medidos a 60 y 86 mm del centro, nunca a 73). Con 26 mm el salto es de
    26 mm, la trocha efectiva cambia de un paso a otro y la odometría se corría más (error medio de
    `ir_a` desde el muelle: 46 → 62 mm en 16 semillas); con eso el carro volvía a la línea torcido
    y rozaba el extremo del muro. Arreglo físico: la llanta es una **banda de rodadura de 20 mm**
    (radio completo) con **hombros de 3 mm** 1,5 mm más chicos (`vehiculo.rodadura_rueda_mm`), como
    una goma real, y sigue midiendo 26 mm de cara a cara para los choques de costado. Con eso la
    odometría volvió a la de antes (46 mm) y 55 de 56 viajes no tocan nada (con la llanta vieja,
    53 de 56).
  - **Holgura en el muelle**: con la llanta 2 mm más ancha por lado, la llanta pasaba a 3,7 mm de la
    guía (antes 6,5). Se corrieron los **rodillos guía 2 mm por lado** (`rodillo_guia_y_mm` 86 → 88)
    y con ellos las guías (se ubican desde el rodillo): vuelven los 7 mm de diseño entre llanta y
    rodillo y la llanta pasa a ≥ 5,6 mm de la guía. La boca en V (20 cm, 4,5 cm por lado) no cambió:
    no hizo falta. El muelle queda 4 mm más ancho en total; en el visor no choca con la canaleta
    (el poste del escape queda 37 mm detrás del final de las guías).
- **Vaso entregado (pedido 13b, 2026-09-28)**: `sim/mundo.py` lo dejaba derecho y ~2 cm por encima
  de los rieles. Ahora lo apoya con la pestaña (78 mm) sobre los rieles (69 mm) a la distancia de
  siempre de la descarga, con la canaleta calculada de la configuración (`geometria_canaleta`, la
  misma que usa el visor) e **inclinado 15°**: así queda en la prueba física (la pestaña se acuesta
  sobre los dos rieles; medido 14,9°). Monedas y tapa se mueven con él. Es una pose colocada, no
  soltada: el vaso de la escena es un cilindro de 62 mm sin pestaña y la canaleta ahí es solo
  visual; que cuelga y desliza lo muestra la prueba física.

## Qué NO se corrigió (y por qué)

- **Chasis del carro**: en PyBullet es una caja de 180 × 120 × 24 mm centrada en el eje de las ruedas
  (una simplificación para la masa y los choques); en el visor la placa va 11,5 mm por encima del eje
  y encima va la electrónica. Largo y ancho coinciden; la altura no se compara porque la caja no es
  la placa.
- **Pestaña del vaso**: la configuración y el visor usan 62 + 2 × 8 = **78 mm**; el texto de
  `docs/especificacion.md` (sección 6, "Modelo físico") decía "la pestaña del reborde, 72 mm" (corregido el 2026-09-28). Era un error del
  texto, no de la simulación (la prueba física usa 78 mm y el vaso cuelga).
- **Banda de la cinta de vasos**: 395 mm en el URDF y 400 mm en el visor (de separador a
  separador): 2,5 mm por lado, dentro de la tolerancia.
- **`control/vehiculo.py` sigue suponiendo la cara de afuera de la llanta a 84 mm** (`ancho / 2 +
  0.024`, en `holguras_carro` y `medio_ancho`) y no lee `ancho_rueda_mm`. No cambia nada hoy: lo más
  ancho del carro son los rodillos guía (93 mm), que sí lee de la configuración. Queda anotado para
  cuando se toque el control (fuera del alcance de este cambio).
"""


if __name__ == "__main__":
    destino = RAIZ / "docs" / "fisica-vs-3d.md"
    destino.write_text(ENCABEZADO + informe() + chr(10) + PIE, encoding="utf-8")
    print(f"escrito {destino}")
