"""Carro impreso (chasis_impreso/) en el visor, pedido del 2026-10-24: "tiene que estar igual al impreso irl".

El visor dibuja el carro con app/visor3d/carro_armado.glb (lo genera `python chasis_impreso/modelo_3d.py`). Aqui
se comprueba que el GLB esta al dia y que lo FUNCIONAL del chasis impreso (eje y centro de las ruedas, rueda
loca, infrarrojos de linea, alturas del HC-SR04 y del VL53L0X, rieles de la cuna, vaso) es lo mismo que dibuja
el visor (`piezas/carro.js`, disposicionCarro) y que usa la simulacion (sim/geometria.py); el visor contra la
fisica ya lo compara tests/sim/test_fisica_vs_3d.py. El GLB se lee aqui mismo (struct + json) para no importar
`exportar`/`modelo_3d`, que existen con el mismo nombre en maqueta_impresa/ y en chasis_impreso/.
"""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
GLB = RAIZ / "app" / "visor3d" / "carro_armado.glb"
CHASIS = RAIZ / "chasis_impreso"
CARRO_JS = RAIZ / "app" / "visor3d" / "piezas" / "carro.js"
TOL_MM = 0.5


def leer_glb(ruta):
    datos = ruta.read_bytes()
    magia, version, largo = struct.unpack("<III", datos[:12])
    assert magia == 0x46546C67 and version == 2 and largo == len(datos), "GLB mal formado"
    return json.loads(datos[20:20 + struct.unpack("<I", datos[12:16])[0]])


@pytest.fixture(scope="module")
def glb():
    assert GLB.exists(), "falta app/visor3d/carro_armado.glb: correr python chasis_impreso/modelo_3d.py"
    return leer_glb(GLB)


@pytest.fixture(scope="module")
def F(glb):
    return glb["scenes"][0]["extras"]["funcional_mm"]


def _js(patron):
    m = re.search(patron, CARRO_JS.read_text(encoding="utf-8"))
    assert m, f"no encontre /{patron}/ en piezas/carro.js"
    return float(m.group(1))


def test_el_glb_tiene_las_piezas_impresas_del_carro_y_sus_remaches(glb):
    scad = (CHASIS / "manual.scad").read_text(encoding="utf-8")
    en_el_carro = re.findall(r'"(\w+)"', re.search(r"EN_EL_CARRO = \[(.*?)\];", scad, re.S).group(1))
    impresas = [n["name"] for n in glb["nodes"] if n["extras"]["tipo"] == "impresa"]
    assert sorted(impresas) == sorted(en_el_carro), "el GLB no esta al dia: correr python chasis_impreso/modelo_3d.py"
    rem = next(n for n in glb["nodes"] if n["name"] == "remaches")
    assert rem["extras"]["tipo"] == "remache" and rem["extras"]["cantidad"] == 27     # REMACHES de chasis.scad, sin el del corte
    assert glb["accessors"][glb["meshes"][rem["mesh"]]["primitives"][0]["indices"]]["count"] > 27 * 3 * 20
    color = glb["materials"][glb["meshes"][rem["mesh"]]["primitives"][0]["material"]]["pbrMetallicRoughness"]["baseColorFactor"]
    assert [round(c * 255) for c in color[:3]] == [0xD1, 0x00, 0x1F]
    # el GLB de la carpeta del carro es el mismo que el del visor
    assert (CHASIS / "carro_armado.glb").read_bytes() == GLB.read_bytes()


def test_la_lengueta_gira_sobre_su_remache(glb, F):
    leng = next(n for n in glb["nodes"] if n["name"] == "lengueta")["extras"]
    assert leng["movil"] == "lengueta" and leng["eje"] == [0, 0, 1]
    assert [round(1000 * v, 3) for v in leng["pivote"]] == pytest.approx(F["piv_leng"], abs=0.01)


def test_lo_funcional_del_chasis_impreso_es_lo_del_visor_y_la_simulacion(F):
    from app import configuracion
    from sim.geometria import geometria_completa

    geo = geometria_completa(configuracion.cargar_parametros())
    v, c = geo["vehiculo"], geo["canaleta"]
    L, W, r = 1000 * v["largo"], 1000 * v["ancho"], 500 * v["diametro_rueda"]
    medidas = [   # (medida, impreso, visor / simulacion)
        ("chasis largo x ancho", [F["L"], F["W"]], [L, W]),
        ("eje de las ruedas (x)", [F["x_eje"]], [-_js(r"d\.xRueda = -([\d.]+) \* L;") * L]),
        ("centro de cada rueda (y)", [F["y_rueda"]], [W / 2 + 1000 * _js(r"d\.yRueda = W / 2 \+ ([\d.]+);")]),
        ("rueda loca (x)", [F["x_loca"]], [_js(r"d\.xLoca = ([\d.]+) \* L;") * L]),
        ("infrarrojos de linea (x)", [F["x_ir"]], [L / 2 - 1000 * _js(r"d\.xIr = L / 2 - ([\d.]+);")]),
        ("HC-SR04 (z)", [F["z_us"]], [r + 1000 * sum(float(x) for x in re.findall(r"[\d.]+", re.search(
            r"d\.zUs = r \+ ([\d.]+ \+ [\d.]+);", CARRO_JS.read_text(encoding="utf-8")).group(1)))]),
        ("VL53L0X (z)", [F["z_tof"]], [1000 * _js(r"d\.zTof = ([\d.]+);")]),
        ("vaso (x)", [F["x_vaso"]], [1000 * _js(r"d\.xVaso = (-?[\d.]+);")]),
        ("rieles de la cuna (z) = fin de la canaleta - caida", [F["z_riel"]], [1000 * (c["fin"][2] - c["caida_entrada"])]),
        ("infrarrojo de la cuna (x, z)", [F["x_ir_cuna"], F["z_ir_cuna"]], [-L / 4 + 12, 1000 * (c["fin"][2] - c["caida_entrada"]) - 30]),
    ]
    malas = [f"  {n}: impreso {a} mm, visor/simulacion {[round(x, 2) for x in b]} mm"
             for n, a, b in medidas if max(abs(x - y) for x, y in zip(a, b)) > TOL_MM]
    assert not malas, "el chasis impreso no coincide (tolerancia 0,5 mm):\n" + "\n".join(malas)


def test_el_visor_y_el_portable_llevan_el_carro_impreso():
    visor = (RAIZ / "app" / "visor3d" / "visor.js").read_text(encoding="utf-8")
    assert "cargarGLB('carro_armado.glb', '__CARRO')" in visor
    portable = (RAIZ / "app" / "portable.py").read_text(encoding="utf-8")
    assert '"carro_armado.glb", "__CARRO"' in portable
