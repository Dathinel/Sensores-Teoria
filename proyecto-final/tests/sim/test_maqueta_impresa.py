"""Maqueta impresa (maqueta_impresa/) vs simulacion (sim/geometria.py), pedido del 2026-10-24.

"Mandan las piezas fisicas": el visor dibuja la maqueta con app/visor3d/maqueta_impresa.glb (lo genera
`python maqueta_impresa/modelo_3d.py` desde los STL que deja `python maqueta_impresa/revisar.py`). Aqui se
comprueba que:

- lo FUNCIONAL de la maqueta fisica (estaciones de las dos cintas, carrusel y tubos, tolva, canaleta,
  carro estacionado en el muelle, camaras y sensores) es lo mismo que usa la simulacion. Los valores fisicos
  salen de los .scad (OpenSCAD los evalua con echo al generar el GLB y quedan en sus extras) o de la malla de
  la pieza dentro del GLB; los digitales, de `sim/geometria.py`. Si algo no coincide, la prueba dice que
  medida, cuanto da cada lado y la diferencia;
- el GLB esta al dia: las mismas piezas que `maqueta.scad` (modo "lista") y cada malla igual a su STL de
  `_cache/ens/` (cantidad de triangulos y caja), y las partes moviles con su pivote.
"""

from __future__ import annotations

import importlib.util
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[2]
MAQUETA = RAIZ / "maqueta_impresa"
GLB = RAIZ / "app" / "visor3d" / "maqueta_impresa.glb"
OPENSCAD = Path(r"D:\cosas uni\Micros\instalados\openscad\openscad.com")
TOL_MM = 0.5
ESPUMA_TOPE_MM = 6   # EVA de los topes del muelle (canaleta_muelle.scad, can_comprados: MEDIR)

# Se carga por ruta y con otro nombre: chasis_impreso/ tambien tiene un modelo_3d.py.
if str(MAQUETA) not in sys.path:
    sys.path.append(str(MAQUETA))
_spec = importlib.util.spec_from_file_location("maqueta_modelo_3d", MAQUETA / "modelo_3d.py")
modelo_3d = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(modelo_3d)

from app import configuracion  # noqa: E402
from sim.geometria import geometria_completa  # noqa: E402


@pytest.fixture(scope="module")
def glb():
    assert GLB.exists(), "falta app/visor3d/maqueta_impresa.glb: correr python maqueta_impresa/modelo_3d.py"
    return modelo_3d.leer_glb(GLB)


@pytest.fixture(scope="module")
def F(glb):
    return glb["scenes"][0]["extras"]["funcional_mm"]


@pytest.fixture(scope="module")
def geo():
    return geometria_completa(configuracion.cargar_parametros())


def _mm(v):
    return [round(1000 * float(x), 3) for x in v]


def _sensor(geo, ident):
    return next(s for s in geo["sensores"] if s["id"] == ident)["geometria"]


def _medidas(F, geo):
    """[(medida, fisico en mm, digital en mm)]: lo funcional de la maqueta contra la simulacion."""
    m = []
    for i, e in enumerate(geo["cinta_monedas"]["estaciones"]):
        m.append((f"cinta de monedas: estacion E{i + 1}", [F["mon_xE"][i], 0, F["mon_z_sup"]], _mm(e["posicion"])))
    xs = F["vas_x_rod"][0]
    for i, e in enumerate(geo["cinta_vasos"]["estaciones"]):
        # las casillas de vasos van centradas entre separadores: x del rodillo de entrada + paso * (i + 1/2)
        m.append((f"cinta de vasos: estacion {i + 1}", [xs + F["vas_paso"] * (i + 0.5), F["vas_y"], F["vas_z_banda"]],
                  _mm(e["posicion"])))
    m.append(("cinta de vasos: paso de casilla", [F["vas_paso"]], _mm([geo["cinta_vasos"]["separacion"]])))
    al = geo["almacen"]
    m.append(("carrusel: centro", F["alm_C"], _mm(al["centro"])))
    m.append(("carrusel: radio eje -> tubo", [F["alm_Rt"]], _mm([al["radio_carrusel"]])))
    m.append(("carrusel: radio interior del tubo", [F["alm_r_int"]], _mm([al["tubos"][0]["radio"]])))
    m.append(("carrusel: fondo de los tubos (z)", [F["alm_z_fondo"]], _mm([al["tubos"][0]["base"][2]])))
    m.append(("carrusel: boca de los tubos (z)", [F["alm_z_boca"]], _mm([al["tubo_z_arriba"]])))
    m.append(("carrusel: punto de carga", F["alm_L"], _mm(al["punto_carga"])))
    cx, cy = F["alm_C"]
    for t, a in zip(al["tubos"], F["alm_angs"]):
        p = [cx + F["alm_Rt"] * math.cos(math.radians(a)), cy + F["alm_Rt"] * math.sin(math.radians(a))]
        m.append((f"carrusel: tubo {t['denominacion']} en reposo", p, _mm(t["base"][:2])))
    tv = al["tolva"]
    (z0, _), (z1, r1) = F["alm_tolva_z_r"]
    m.append(("tolva: eje (= agujero de la placa fija)", F["alm_H"], _mm(tv["salida"])))
    m.append(("tolva: boca (z) y radio", [z1, r1], _mm([tv["z_arriba"], tv["radio"]])))
    m.append(("tolva: salida (z)", [z0], _mm([tv["z_abajo"]])))
    c = geo["canaleta"]
    rm, rp = np.array(F["can_riel_m"]), np.array(F["can_riel_p"])
    m.append(("canaleta: inicio (centro de la boca)", ((rm[0] + rp[0]) / 2).tolist(), _mm(c["inicio"])))
    m.append(("canaleta: fin", ((rm[-1] + rp[-1]) / 2).tolist(), _mm(c["fin"])))
    m.append(("canaleta: separacion de entrada / de rieles", [rp[0][0] - rm[0][0], rp[-1][0] - rm[-1][0]],
              _mm([c["separacion_entrada"], c["separacion_rieles"]])))
    # carro estacionado: lo centran las guias del muelle (cara interna de las paredes de 16 mm) y lo para la
    # espuma de los topes (sim/vehiculo_sim.py: el tope toca la cola del chasis 3 mm detras, a L/2 + 3)
    s, v = geo["pista"]["salida"], geo["vehiculo"]
    paredes = [modelo_3d.vertices_mm(GLB, f"can_guia_recta_{l}") for l in ("xn", "xp")]
    caras = [p[(p[:, 2] > 8) & (p[:, 1] < -400)][:, 0] for p in paredes]   # la pared, lejos de la placa al tubo
    caras = [caras[0].max(), caras[1].min()]                 # cara interna de cada pared
    guia_y = 1000 * (v["rodillo_guia_y"] + v["rodillo_guia_radio"] + v["muelle_holgura"])
    m.append(("carro estacionado: centro entre las guias del muelle (x) y medio canal",
              [(caras[0] + caras[1]) / 2, (caras[1] - caras[0]) / 2], [1000 * s["x"], guia_y]))
    topes = modelo_3d.vertices_mm(GLB, "can_topes")
    cara_tope = topes[topes[:, 2] > 31][:, 1].min() - ESPUMA_TOPE_MM
    m.append(("carro estacionado: donde lo para el tope (y)", [cara_tope],
              [1000 * (s["y"] + v["largo"] / 2 + 0.003)]))
    m.append(("carro estacionado: rumbo (grados)", [-90], [round(math.degrees(s["rumbo"]), 3)]))
    m.append(("camara cenital: vidrio", F["mon_lente"], _mm(_sensor(geo, "camara")["posicion"])))
    m.append(("camara de vasos: carcasa", F["vas_cam"], _mm(_sensor(geo, "camara_vasos")["posicion"])))
    m.append(("camara de vasos: a donde mira", F["vas_cam_obj"], _mm(_sensor(geo, "camara_vasos")["objetivo"])))
    m.append(("FC-51 de presencia: origen del rayo", F["mon_fc"], _mm(_sensor(geo, "presencia")["origen"])))
    for ident, i in (("capacitivo", 0), ("inductivo", 1)):
        m.append((f"{ident} M18: cara activa", [F["mon_xE"][i], 0, F["mon_z_m18"]], _mm(_sensor(geo, ident)["posicion"])))
    m.append(("Hall del carrusel: cara del A3144", F["alm_hall"], _mm(_sensor(geo, "hall_carrusel")["posicion"])))
    m.append(("VL53L0X interior: cara", F["tap_sens"], _mm(_sensor(geo, "sensor_interior")["posicion"])))
    m.append(("VL53L0X de la cortina: cara", F["vas_cortina"], _mm(_sensor(geo, "cortina")["origen"])))
    m.append(("bandeja de rechazo de vasos (x, y)", F["vas_bandeja_c"], _mm(geo["bandeja_rechazo_vasos"][:2])))
    return m


def test_lo_funcional_de_la_maqueta_fisica_es_lo_de_la_simulacion(F, geo):
    malas = []
    for nombre, fisico, digital in _medidas(F, geo):
        d = max(abs(a - b) for a, b in zip(fisico, digital))
        if len(fisico) != len(digital) or d > TOL_MM:
            malas.append(f"  {nombre}: fisico {np.round(fisico, 2).tolist()} mm, simulacion "
                         f"{np.round(digital, 2).tolist()} mm (diferencia {d:.2f} mm)")
    assert not malas, "no coinciden (tolerancia 0,5 mm):\n" + "\n".join(malas)


@pytest.fixture(scope="module")
def lista():
    """Salida (echo) de maqueta.scad en modo "lista": una linea PIEZA por pieza y una REM por remache."""
    if not OPENSCAD.exists() and not shutil.which("openscad"):
        pytest.skip("sin OpenSCAD en este PC")
    exe = str(OPENSCAD if OPENSCAD.exists() else shutil.which("openscad"))
    return subprocess.run([exe, "-D", 'modo="lista"', "-o", "-", "--export-format", "echo",
                           str(MAQUETA / "maqueta.scad")], capture_output=True, text=True).stdout


def test_el_glb_tiene_las_piezas_de_maqueta_scad(glb, lista):
    piezas = re.findall(r'ECHO: PIEZA = "([^"]+)"', lista)
    assert piezas, "OpenSCAD no listo piezas"
    en_glb = [n["name"] for n in glb["nodes"] if n["extras"]["tipo"] == "impresa"]
    assert sorted(en_glb) == sorted(piezas), (
        f"el GLB no esta al dia (correr python maqueta_impresa/modelo_3d.py): faltan "
        f"{sorted(set(piezas) - set(en_glb))[:8]}, sobran {sorted(set(en_glb) - set(piezas))[:8]}")


def _triangulos_stl(ruta):
    datos = ruta.read_bytes()
    if datos[:5] == b"solid" and b"facet" in datos[:300]:
        return datos.count(b"facet normal")
    return int.from_bytes(datos[80:84], "little")


def test_cada_malla_del_glb_es_su_stl(glb):
    ens = MAQUETA / "_cache" / "ens"
    if not ens.is_dir():
        pytest.skip("sin _cache/ens (correr python maqueta_impresa/revisar.py)")
    cajas = glb["scenes"][0]["extras"]["cajas_mm"]
    malas = []
    for n in glb["nodes"]:
        if n["extras"]["tipo"] != "impresa":   # los remaches no tienen STL propio en _cache/ens
            continue
        stl = ens / f"{n['name']}.stl"
        if not stl.exists():
            malas.append(f"{n['name']}: no hay STL")
            continue
        acc = glb["accessors"][glb["meshes"][n["mesh"]]["primitives"][0]["indices"]]
        tri = _triangulos_stl(stl)
        # caja de la malla del GLB (accesor de posiciones, three en m) vuelta al marco sim en mm
        pos = glb["accessors"][glb["meshes"][n["mesh"]]["primitives"][0]["attributes"]["POSITION"]]
        lo = [pos["min"][0] * 1000, -pos["max"][2] * 1000, pos["min"][1] * 1000]
        if acc["count"] // 3 != tri or max(abs(a - b) for a, b in zip(lo, cajas[n["name"]][0])) > 0.05:
            malas.append(f"{n['name']}: {acc['count'] // 3} triangulos en el GLB, {tri} en el STL")
    assert not malas, "GLB viejo respecto de los STL (correr python maqueta_impresa/modelo_3d.py):\n" + "\n".join(malas[:10])


def test_el_glb_trae_todos_los_remaches_en_rojo(glb, F, lista):
    """Usuario (2026-10-24): los remaches son parte de como se vera la maqueta; el visor los muestra con la
    casilla "Remaches". Un nodo por subsistema, con cuantos trae, y entre todos los de REM_TODOS (los que
    maqueta.scad lista hoy: la cuenta cambia cuando se agrega o quita uno, por eso no va escrita aqui)."""
    rem = [n for n in glb["nodes"] if n["extras"]["tipo"] == "remache"]
    assert sorted(n["extras"]["grupo"] for n in rem) == ["alm", "can", "estructura", "mon", "tap", "vas"]
    n_scad = len(re.findall(r"ECHO: REM = ", lista))
    assert n_scad > 0, "OpenSCAD no listo remaches"
    assert sum(n["extras"]["cantidad"] for n in rem) == sum(F["n_remaches"]) == glb["scenes"][0]["extras"]["remaches"] == n_scad
    for n in rem:
        prim = glb["meshes"][n["mesh"]]["primitives"][0]
        assert glb["accessors"][prim["indices"]]["count"] >= n["extras"]["cantidad"] * 3 * 20, n["name"]
        color = glb["materials"][prim["material"]]["pbrMetallicRoughness"]["baseColorFactor"]
        assert [round(c * 255) for c in color[:3]] == [0xD1, 0x00, 0x1F]


def test_las_partes_moviles_traen_su_pivote(glb, F):
    mov = {n["name"]: n["extras"] for n in glb["nodes"] if "movil" in n["extras"]}
    # lo que el visor anima con las piezas impresas (MOVILES_* de cada .scad)
    assert {"alm_disco", "alm_tambor", "alm_obturador", "alm_palanca", "mon_aleta", "tap_dedo_a", "tap_dedo_b", "tap_pre_leva",
            "tap_pre_plato", "tap_emp_paleta", "tap_emp_manivela", "tap_emp_biela", "can_balancin"} <= set(mov)
    assert sum(1 for n in mov if n.startswith("vas_taco_")) == 22      # 11 separadores a L/11, dos medios tacos c/u
    assert _mm(mov["alm_disco"]["pivote"])[:2] == pytest.approx(F["alm_C"], abs=0.01)
    # Obturador (almacen.scad, 2026-10-25): corredera enrasada que corre 30 mm (alm_cie_s) hacia los 300 grados,
    # llevada por la palanca del SG90, que gira alm_abre (90) grados en sentido horario visto desde arriba sobre
    # alm_P. El visor cuelga las dos del obturador y mueve cada una con su movimiento (visor.js, montarMaqueta).
    assert mov["alm_obturador"]["movil"] == mov["alm_palanca"]["movil"] == "obturador"
    assert mov["alm_obturador"]["movimiento"] == "lineal" and mov["alm_obturador"]["recorrido"] == [0, 30]
    assert mov["alm_obturador"]["eje"] == pytest.approx([math.cos(math.radians(300)), math.sin(math.radians(300)), 0], abs=1e-5)
    assert mov["alm_palanca"]["movimiento"] == "giro" and mov["alm_palanca"]["eje"] == [0, 0, -1]
    assert _mm(mov["alm_palanca"]["pivote"])[:2] == pytest.approx(F["alm_P"], abs=0.01)
    assert mov["alm_palanca"]["recorrido"] == [0, F["alm_abre"]] == [0, 90]
    assert _mm(mov["mon_aleta"]["pivote"]) == pytest.approx([105, 0, 418], abs=0.01)
    assert _mm(mov["can_balancin"]["pivote"]) == pytest.approx(F["can_piv"], abs=0.01)


def test_los_angulos_del_firmware_son_los_recorridos_de_las_piezas(glb, F):
    """Cada pieza va directo en la estria o en el cuerno de su servo, asi que activo - reposo de
    firmware.servos (config/parametros.yaml) tiene que ser el recorrido de la pieza impresa. Auditoria del
    2026-10-25: eran 30/60/120/45 y con eso el escape de tapas se trababa, el de la canaleta pegaba en el carro
    y el empujador no sacaba el vaso de la banda."""
    mov = {n["name"]: n["extras"] for n in glb["nodes"] if "movil" in n["extras"]}

    def rec(n):
        return mov[n]["recorrido"][1] - mov[n]["recorrido"][0]

    fisico = {"desvio": rec("mon_aleta"), "obturador": rec("alm_palanca"), "prensa": rec("tap_pre_leva"),
              "empujador": rec("tap_emp_manivela"), "canaleta": rec("can_balancin"),
              # los pernos del cuerno de tapas van a 12,4 mm del eje (tapas_prensa_empujador.scad, tap_pinA/B)
              "tapas": 2 * math.degrees(math.asin(F["tap_carrera_dedo"] / (2 * 12.4)))}
    servos = configuracion.cargar_parametros()["firmware"]["servos"]
    malos = {k: (abs(servos[k]["activo"] - servos[k]["reposo"]), round(v, 2)) for k, v in fisico.items()
             if abs(abs(servos[k]["activo"] - servos[k]["reposo"]) - v) > 1}
    assert set(fisico) == set(servos)
    assert not malos, f"firmware contra pieza impresa (grados): {malos}"
