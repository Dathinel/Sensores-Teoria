"""Maqueta impresa en 3D para el visor: app/visor3d/maqueta_impresa.glb.

Un nodo por pieza impresa (todas las de maqueta.scad, modo "lista"), EN SU LUGAR del ensamble: metros y el
marco del visor (sim (x, y, z) -> glTF/three (x, z, -y)). Las partes que se mueven son nodos separados con
`extras.movil` = de que conjunto movil son y `extras.pivote` / `extras.eje` / `extras.recorrido` (marco de la
simulacion, metros y grados): el visor las cuelga del objeto que ya anima (carrusel, obturador, aleta E4,
dedos de tapas, leva y piston de la prensa, empujador, escape de la canaleta, tacos de la banda de vasos).
Lo comprado (motores, servos, bandas, sensores...) NO va: lo sigue dibujando el visor.
Los remaches impresos (los de REM_TODOS) van en su lugar como un nodo por subsistema (`rem_<sub>`, extras.tipo "remache", rojo
#d1001f como en los manuales): el visor los muestra u oculta con la casilla "Remaches" (usuario, 2026-10-24).

En las extras de la escena va `funcional_mm`: las medidas funcionales tal como las define cada .scad
(leidas con echo de OpenSCAD), que tests/sim/test_maqueta_impresa.py compara con sim/geometria.py.

Uso: python modelo_3d.py      (antes: python revisar.py, que deja los STL de cada pieza en _cache/ens/)
"""
import json
import re
import struct
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import revisar as R                    # listas() (modo "lista"), OPENSCAD, CACHE y leer_stl del carro

AQUI = R.AQUI
SALIDA = AQUI.parent / "app" / "visor3d" / "maqueta_impresa.glb"
ENS = R.CACHE / "ens"

# color de cada grupo (PLA): estructura gris, cada subsistema el suyo
COLORES = {"est_tubos": "#8a919b", "est_nodos": "#5f6672", "est_uniones": "#6f7782", "alm": "#2f9e8f",
           "mon": "#3d7cc9", "vas": "#d39236", "tap": "#8a63c9", "can": "#c4553f"}
COLOR_PIEZA = {"vas_panel_a": "#f4f6f8", "vas_panel_b": "#f4f6f8"}   # caja de luz en PLA blanco (difusor)
COLOR_REMACHE = "#d1001f"
REM_SUB = {"estructura": "REM_ESTRUCTURA", "alm": "REM_ALM", "mon": "REM_MON", "vas": "REM_VAS", "tap": "REM_TAP", "can": "REM_CAN"}

# Medidas funcionales que se leen de los .scad (echo). Expresiones de OpenSCAD.
ECO = {
    "mon_xE": "mon_xE", "mon_z_sup": "mon_z_sup", "mon_z_m18": "mon_z_m18", "mon_fc": "mon_fc",
    "mon_lente": "mon_lente", "mon_piv": "mon_piv", "mon_reposo": "mon_reposo",
    "mon_rodillos": "[mon_x_mot, mon_x_ten, mon_z_rod]",
    "vas_y": "vas_y", "vas_z_banda": "vas_z_banda", "vas_x_rod": "vas_x_rod", "vas_z_rod": "vas_z_rod",
    "vas_paso": "vas_paso", "vas_cam": "vas_cam", "vas_cam_obj": "vas_cam_obj", "vas_cortina": "vas_cortina",
    "vas_bandeja_c": "vas_bandeja_c", "vas_recorte_sep": "vas_recorte_sep", "vas_sep": "vas_sep",
    "alm_C": "alm_C", "alm_Rt": "alm_Rt", "alm_angs": "alm_angs", "alm_H": "alm_H", "alm_L": "alm_L",
    "alm_r_int": "alm_r_int", "alm_z_fondo": "alm_z_fondo", "alm_z_boca": "alm_z_boca", "alm_hall": "alm_hall",
    "alm_P": "alm_P", "alm_abre": "alm_abre", "alm_cie_s": "alm_cie_s", "alm_byj_c": "alm_byj_c",
    "alm_emb_z0": "alm_emb_z0", "alm_tolva_z_r": "[[230, alm_tol_r(230)], [262, alm_tol_r(262)]]",
    "alm_sg": "[alm_P[0], alm_P[1], alm_z_sg, alm_v]",
    "tap_tubo_c": "tap_tubo_c", "tap_z_cab": "tap_z_cab", "tap_pre_c": "tap_pre_c", "tap_z_plato": "tap_z_plato",
    "tap_z_leva": "tap_z_leva", "tap_exc": "tap_exc", "tap_emp": "[tap_emp_x, tap_emp_ys, tap_emp_r, tap_emp_L]",
    "tap_sens": "tap_sens", "tap_carrera_dedo": "tap_carrera_dedo", "tap_sg": "[tap_sg_eje[0], tap_sg_eje[1], tap_sg_z]",
    "can_riel_m": "can_pts_riel(-1)", "can_riel_p": "can_pts_riel(1)", "can_piv": "can_piv", "can_ME": "CAN_ME",
    "can_th0": "can_th0", "can_y_primero": "can_y_primero", "can_y_ret": "can_y_ret",
    "n_remaches": "[" + ", ".join(f"len({v})" for v in REM_SUB.values()) + "]",
}


def leer_eco():
    """Valores de ECO evaluados por OpenSCAD con todo maqueta.scad incluido (nada se copia a mano)."""
    with tempfile.TemporaryDirectory(dir=R.CACHE) as t:       # en C: OpenSCAD daba avisos falsos (como revisar.scad)
        scad, eco = Path(t) / "eco.scad", Path(t) / "eco.echo"
        scad.write_text(f'include <{(AQUI / "maqueta.scad").as_posix()}>\n'
                        + "".join(f"echo({k} = {v});\n" for k, v in ECO.items()))
        r = subprocess.run([str(R.OPENSCAD), "-D", 'modo="nada"', "-o", str(eco), str(scad)],
                           capture_output=True, text=True)
        if not eco.exists():
            raise SystemExit("OpenSCAD fallo al leer las medidas:\n" + (r.stdout + r.stderr)[-2000:])
        txt = eco.read_text()
    vals = {m[1]: json.loads(m[2]) for m in re.finditer(r"ECHO: (\w+) = (.*)", txt)}
    faltan = [k for k in ECO if k not in vals]
    assert not faltan, f"OpenSCAD no devolvio {faltan}"
    return vals


def mm_a_m(p):
    return [round(v / 1000, 6) for v in p]


def stl_remaches(sub, lista, tmp):
    """STL con los remaches de un subsistema en su lugar (remache_en de comun.scad sobre su lista REM_*)."""
    scad, stl = Path(tmp) / f"rem_{sub}.scad", Path(tmp) / f"rem_{sub}.stl"
    scad.write_text(f'include <{(AQUI / "maqueta.scad").as_posix()}>\nmodo = "nada";\nfor (r = {lista}) remache_en(r);\n')
    r = subprocess.run([str(R.OPENSCAD), "-o", str(stl), str(scad)], capture_output=True, text=True)
    if not stl.exists():
        raise SystemExit(f"OpenSCAD fallo con los remaches de {sub}:\n" + (r.stdout + r.stderr)[-2000:])
    return stl


def moviles(F, piezas):
    """Cada parte que se mueve: a que objeto del visor sigue y su movimiento (marco sim, m y grados)."""
    C, P = F["alm_C"], F["alm_P"]
    x_emp, ys_emp = F["tap_emp"][0], F["tap_emp"][1]
    me = np.array(F["can_ME"])
    eje_escape = me[:3, 1].tolist()            # eje del SG90 del escape: Y local del marco CAN_ME
    d = {
        "alm_disco": ("carrusel", "giro", [C[0], C[1], 0], [0, 0, 1], [0, 360]),
        "alm_tambor": ("carrusel", "giro", [C[0], C[1], 0], [0, 0, 1], [0, 360]),
        # obturador corredera (2026-10-25): la corredera corre alm_cie_s mm hacia 300 grados (radial desde el agujero) y
        # la palanca del SG90 gira alm_abre grados (horario visto desde arriba) sobre su eje
        "alm_obturador": ("obturador", "lineal", [0, 0, 0], [0.5, -0.8660254, 0], [0, F["alm_cie_s"]]),
        "alm_palanca": ("obturador", "giro", [P[0], P[1], 0], [0, 0, -1], [0, F["alm_abre"]]),
        "mon_aleta": ("desvio", "giro", F["mon_piv"], [1, 0, 0], [-F["mon_reposo"], F["mon_reposo"]]),
        "tap_dedo_a": ("dedo_a", "lineal", [0, 0, 0], [0, -1, 0], [0, F["tap_carrera_dedo"]]),
        "tap_dedo_b": ("dedo_b", "lineal", [0, 0, 0], [0, 1, 0], [0, F["tap_carrera_dedo"]]),
        "tap_pre_leva": ("leva", "giro", [F["tap_pre_c"][0], 0, F["tap_z_leva"]], [0, 1, 0], [0, 180]),
        "tap_pre_plato": ("piston", "lineal", [0, 0, 0], [0, 0, -1], [0, 2 * F["tap_exc"]]),
        "tap_pre_horquilla": ("piston", "lineal", [0, 0, 0], [0, 0, -1], [0, 2 * F["tap_exc"]]),
        "tap_pre_rodillo": ("piston", "lineal", [0, 0, 0], [0, 0, -1], [0, 2 * F["tap_exc"]]),
        "tap_emp_paleta": ("paleta", "lineal", [0, 0, 0], [0, -1, 0], [0, 2 * F["tap_emp"][2]]),
        "tap_emp_carro": ("paleta", "lineal", [0, 0, 0], [0, -1, 0], [0, 2 * F["tap_emp"][2]]),
        "tap_emp_manivela": ("manivela", "giro", [x_emp, ys_emp, 0], [0, 0, -1], [0, 180]),
        "tap_emp_biela": ("biela", "biela", [x_emp, ys_emp, 0], [0, 0, -1], [0, 180]),
        "can_balancin": ("escape", "giro", F["can_piv"], eje_escape, [-np.degrees(np.arcsin(7 / 38)), np.degrees(np.arcsin(7 / 38))]),
    }
    # Tacos de la banda de vasos: los que haya en cinta_vasos.scad (11 pares desde 2026-10-25, uno por separador a L/11;
    # los del ramal de abajo corren hacia -x: el visor los cuelga de su separador de abajo). El paso de la animacion
    # queda en vas_paso (80): la casilla real mide 79,6 (diferencia < 1,2 mm por casilla, la corrige la camara).
    for n in piezas:
        if n.startswith("vas_taco_"):
            d[n] = ("banda_vasos", "banda", [0, 0, 0], [1, 0, 0], [0, F["vas_paso"]])
    out = {}
    for n, (sigue, tipo, piv, eje, rec) in d.items():
        out[n] = {"movil": sigue, "movimiento": tipo, "pivote": mm_a_m(piv) if tipo != "lineal" else [0, 0, 0],
                  "eje": [round(float(v), 6) for v in eje],
                  "recorrido": [round(float(v), 4) for v in rec],
                  "unidad_recorrido": "mm" if tipo in ("lineal", "banda") else "grados"}
    return out


def grupo_de(n):
    pre = n.split("_", 1)[0]
    if pre in ("alm", "mon", "vas", "tap", "can"):
        return pre
    return {"t": "est_tubos", "e": "est_uniones", "taco": "est_uniones"}.get(pre, "est_nodos")


def malla(ruta):
    """STL (mm, z arriba) -> vertices unicos (m, marco glTF: y arriba) e indices."""
    tri = R.ex_carro.leer_stl(ruta)
    v, idx = np.unique(np.round(tri.reshape(-1, 3), 3), axis=0, return_inverse=True)
    v = np.c_[v[:, 0], v[:, 2], -v[:, 1]] / 1000.0
    idx = idx.reshape(-1)
    return v.astype(np.float32), idx.astype(np.uint16 if len(v) < 65536 else np.uint32), tri


def color(hexa):
    return [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)] + [1.0]


def escribir_glb(ruta, objetos, extras_escena):
    """objetos: [(nombre, vertices, indices, color_hex, extras)] -> GLB con un nodo (y una malla) por objeto."""
    binario, vistas, accesores, mallas, materiales, nodos = bytearray(), [], [], [], [], []

    def agregar(datos, destino):
        while len(binario) % 4:
            binario.append(0)
        vistas.append({"buffer": 0, "byteOffset": len(binario), "byteLength": len(datos), "target": destino})
        binario.extend(datos)
        return len(vistas) - 1

    mat_de = {}
    for nombre, v, i, col, extras in objetos:
        if col not in mat_de:
            mat_de[col] = len(materiales)
            materiales.append({"name": col, "pbrMetallicRoughness": {"baseColorFactor": color(col), "metallicFactor": 0.0,
                                                                     "roughnessFactor": 0.72}})
        vp = agregar(v.tobytes(), 34962)
        accesores.append({"bufferView": vp, "componentType": 5126, "count": len(v), "type": "VEC3",
                          "min": v.min(0).tolist(), "max": v.max(0).tolist()})
        vi = agregar(i.tobytes(), 34963)
        accesores.append({"bufferView": vi, "componentType": 5123 if i.dtype == np.uint16 else 5125,
                          "count": len(i), "type": "SCALAR"})
        mallas.append({"name": nombre, "primitives": [{"attributes": {"POSITION": len(accesores) - 2},
                                                       "indices": len(accesores) - 1, "material": mat_de[col]}]})
        nodos.append({"name": nombre, "mesh": len(mallas) - 1, "extras": extras})
    while len(binario) % 4:
        binario.append(0)
    gltf = {"asset": {"version": "2.0", "generator": "maqueta_impresa/modelo_3d.py"}, "scene": 0,
            "scenes": [{"name": "maqueta_impresa", "nodes": list(range(len(nodos))), "extras": extras_escena}],
            "nodes": nodos, "meshes": mallas, "materials": materiales,
            "accessors": accesores, "bufferViews": vistas, "buffers": [{"byteLength": len(binario)}]}
    js = json.dumps(gltf, ensure_ascii=False).encode("utf-8")
    js += b" " * (-len(js) % 4)
    datos = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binario))
    datos += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binario), 0x004E4942) + bytes(binario)
    Path(ruta).write_bytes(datos)
    return datos


def leer_glb(ruta):
    """El JSON de un GLB (lo usa tambien la prueba)."""
    datos = Path(ruta).read_bytes()
    magia, version, largo = struct.unpack("<III", datos[:12])
    n_js = struct.unpack("<I", datos[12:16])[0]
    assert magia == 0x46546C67 and version == 2 and largo == len(datos), "GLB mal formado"
    return json.loads(datos[20:20 + n_js])


def vertices_mm(ruta, nombre):
    """Vertices de la pieza `nombre` del GLB en el marco de la simulacion, en mm (lo usa la prueba)."""
    datos = Path(ruta).read_bytes()
    n_js = struct.unpack("<I", datos[12:16])[0]
    g = json.loads(datos[20:20 + n_js])
    binario = datos[20 + n_js + 8:]
    nodo = next(n for n in g["nodes"] if n["name"] == nombre)
    acc = g["accessors"][g["meshes"][nodo["mesh"]]["primitives"][0]["attributes"]["POSITION"]]
    vista = g["bufferViews"][acc["bufferView"]]
    v = np.frombuffer(binario, dtype="<f4", count=acc["count"] * 3, offset=vista["byteOffset"]).reshape(-1, 3)
    return np.c_[v[:, 0], -v[:, 2], v[:, 1]].astype(np.float64) * 1000.0


def main():
    piezas, rem, _ = R.listas()
    # el visor tiene que ser lo fisico: con un STL que falta o que se dibujo con otros .scad no se escribe nada
    # (2026-10-25: antes solo avisaba, por fecha, y seguia)
    viejas = [r.stem for r in R.viejos([ENS / f"{n}.stl" for n in piezas])]
    if viejas:
        raise SystemExit(f"{len(viejas)} STL de _cache/ens faltan o se dibujaron con otros .scad ({viejas[:5]}...): "
                         "correr antes python revisar.py")
    F = leer_eco()
    mov = moviles(F, piezas)
    objetos, cajas = [], {}
    for n in piezas:
        v, i, tri = malla(ENS / f"{n}.stl")
        g = grupo_de(n)
        extras = {"tipo": "impresa", "pieza": n, "grupo": g, **mov.get(n, {})}
        objetos.append((n, v, i, COLOR_PIEZA.get(n, COLORES[g]), extras))
        p = tri.reshape(-1, 3)
        cajas[n] = [np.round(p.min(0), 2).tolist(), np.round(p.max(0), 2).tolist()]
    assert sum(F["n_remaches"]) == len(rem), f"REM_TODOS tiene {len(rem)} remaches y las listas suman {sum(F['n_remaches'])}"
    with tempfile.TemporaryDirectory(dir=R.CACHE) as t, ThreadPoolExecutor(R.HILOS) as ej:
        stls = list(ej.map(lambda s: stl_remaches(s[0], s[1], t), REM_SUB.items()))
        for sub, n_rem, stl in zip(REM_SUB, F["n_remaches"], stls):
            v, i, _ = malla(stl)
            objetos.append((f"rem_{sub}", v, i, COLOR_REMACHE, {"tipo": "remache", "grupo": sub, "cantidad": n_rem}))
    extras_escena = {"marco": "visor: sim (x, y, z) en m -> three (x, z, -y)", "piezas": len(piezas),
                     "remaches": len(rem), "funcional_mm": F, "cajas_mm": cajas,
                     "moviles": sorted({m["movil"] for m in mov.values()})}
    datos = escribir_glb(SALIDA, objetos, extras_escena)
    leido = leer_glb(SALIDA)       # autocomprobacion: un nodo por pieza (mas uno de remaches por subsistema)
    assert len(leido["nodes"]) == len(piezas) + len(REM_SUB) and len(piezas) == len(set(piezas))
    assert all(n["name"] in mov for n in leido["nodes"] if "movil" in n["extras"])
    assert set(mov) <= set(piezas), f"moviles sin pieza: {set(mov) - set(piezas)}"
    print(f"GLB: {SALIDA} ({len(datos) / 1e6:.2f} MB, {len(piezas)} piezas, {len(rem)} remaches en {len(REM_SUB)} nodos, "
          f"{len(mov)} moviles, {sum(len(o[2]) for o in objetos) // 3} triangulos)")


if __name__ == "__main__":
    main()
