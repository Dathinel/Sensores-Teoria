"""Carro armado en 3D: carro_armado.glb (cada pieza impresa y cada grupo de componentes es un objeto con su
nombre, tanda y donde va) y visor_carro.html (lo abre en el navegador, con el GLB adentro).

Uso: python modelo_3d.py
El GLB tambien se abre con el Visor 3D de Windows, Blender o cualquier visor de glTF.
"""
import base64
import json
import struct
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import exportar as ex
import manual

AQUI = ex.AQUI
# color de cada tanda en el visor (los mismos del render del ensamble no sirven: aqui se agrupa por tanda)
COLOR_TANDA = {1: "#e4572e", 2: "#4c9f70", 3: "#f3a712", 4: "#3a6ea5"}
COMPONENTES = {   # grupo de componentes(): (nombre que se muestra, color)
    "motores": ("Motores TT", "#e8c547"), "ruedas": ("Ruedas", "#2b2b2b"), "rodillos": ("Rodamientos 623", "#c9ccd1"),
    "encoders": ("Encoders H206", "#1e5aa8"), "baterias": ("Pack 2S 18650", "#3a3a3a"), "esp32": ("ESP32 en GVS", "#1b1d22"),
    "tb": ("TB6612FNG", "#7a2a8c"), "frente": ("HC-SR04 y VL53L0X", "#5b6b8c"), "ir": ("5 x TCRT5000", "#1b2b5a"),
    "loca": ("Rueda loca", "#c9ccd1"), "cajas": ("Interruptor y portafusible", "#111111"), "vaso": ("Vaso", "#e8e2d0"),
    "espumas": ("Espumas", "#ffd8a8"),
}


def stl_de(scad_txt, salida, tmp):
    scad = tmp / (salida.stem + ".scad")
    scad.write_text(scad_txt)
    r = subprocess.run([str(ex.OPENSCAD), "-o", str(salida), str(scad)], capture_output=True, text=True)
    if not salida.exists():
        raise SystemExit(f"OpenSCAD fallo con {salida.stem}:\n{(r.stdout + r.stderr)[-1500:]}")
    return salida


def malla(ruta):
    """STL -> vertices unicos (en el marco de glTF: y arriba, metros) e indices."""
    tri = ex.leer_stl(ruta)
    v, idx = np.unique(np.round(tri.reshape(-1, 3), 4), axis=0, return_inverse=True)
    v = np.c_[v[:, 0], v[:, 2], -v[:, 1]] / 1000.0          # z arriba (mm) -> y arriba (m)
    return v.astype(np.float32), idx.astype(np.uint32).reshape(-1)


def color(hexa):
    return [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)] + [1.0]


def escribir_glb(ruta, objetos):
    """objetos: [(nombre, vertices, indices, color_hex, extras)] -> GLB con un nodo por objeto."""
    binario, vistas, accesores, mallas, materiales, nodos = bytearray(), [], [], [], [], []
    def agregar(datos, destino):
        while len(binario) % 4:
            binario.append(0)
        vistas.append({"buffer": 0, "byteOffset": len(binario), "byteLength": len(datos), "target": destino})
        binario.extend(datos)
        return len(vistas) - 1
    for nombre, v, i, col, extras in objetos:
        vp = agregar(v.tobytes(), 34962)
        accesores.append({"bufferView": vp, "componentType": 5126, "count": len(v), "type": "VEC3",
                          "min": v.min(0).tolist(), "max": v.max(0).tolist()})
        vi = agregar(i.tobytes(), 34963)
        accesores.append({"bufferView": vi, "componentType": 5125, "count": len(i), "type": "SCALAR"})
        materiales.append({"name": nombre, "pbrMetallicRoughness": {"baseColorFactor": color(col), "metallicFactor": 0.0,
                                                                    "roughnessFactor": 0.7}})
        mallas.append({"name": nombre, "primitives": [{"attributes": {"POSITION": len(accesores) - 2},
                                                       "indices": len(accesores) - 1, "material": len(materiales) - 1}]})
        nodos.append({"name": nombre, "mesh": len(mallas) - 1, "extras": extras})
    while len(binario) % 4:
        binario.append(0)
    gltf = {"asset": {"version": "2.0", "generator": "chasis_impreso/modelo_3d.py"}, "scene": 0,
            "scenes": [{"nodes": list(range(len(nodos)))}], "nodes": nodos, "meshes": mallas, "materials": materiales,
            "accessors": accesores, "bufferViews": vistas, "buffers": [{"byteLength": len(binario)}]}
    js = json.dumps(gltf, ensure_ascii=False).encode("utf-8")
    js += b" " * (-len(js) % 4)
    datos = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binario))
    datos += struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binario), 0x004E4942) + bytes(binario)
    Path(ruta).write_bytes(datos)


def main():
    incluir = f'include <{(AQUI / "manual.scad").as_posix()}>\n'
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        trabajos = [(n, f'{incluir}modo = "solo";\ncual = "{n}";\n') for n in manual.PIEZAS_INFO]
        trabajos += [(f"comp_{g}", f'{incluir}modo = "nada";\ncomponentes("{g}");\n') for g in COMPONENTES]
        with ThreadPoolExecutor(6) as ej:
            rutas = dict(zip([n for n, _ in trabajos],
                             ej.map(lambda a: stl_de(a[1], tmp / f"{a[0]}.stl", tmp), trabajos)))
        objetos = []
        for n, (donde, _, _) in manual.PIEZAS_INFO.items():
            cant, tanda = ex.PIEZAS[n][:2]
            v, i = malla(rutas[n])
            objetos.append((n, v, i, COLOR_TANDA[tanda], {"tipo": "impresa", "pieza": n, "tanda": tanda,
                                                           "cantidad": cant, "donde": donde}))
        for g, (nombre, col) in COMPONENTES.items():
            v, i = malla(rutas[f"comp_{g}"])
            objetos.append((f"comp_{g}", v, i, col, {"tipo": "comprada", "pieza": nombre, "tanda": 0, "cantidad": 1,
                                                     "donde": "Componente comprado."}))
    glb = AQUI / "carro_armado.glb"
    escribir_glb(glb, objetos)
    # autocomprobacion: el GLB se vuelve a leer y tiene un nodo por objeto con su malla
    datos = glb.read_bytes()
    magia, version, largo = struct.unpack("<III", datos[:12])
    n_js = struct.unpack("<I", datos[12:16])[0]
    leido = json.loads(datos[20:20 + n_js])
    assert magia == 0x46546C67 and version == 2 and largo == len(datos) and len(leido["nodes"]) == len(objetos)
    print(f"GLB: {glb} ({len(datos) / 1e6:.1f} MB, {len(objetos)} objetos, "
          f"{sum(len(o[2]) for o in objetos) // 3} triangulos)")
    plantilla = (AQUI / "visor_carro_plantilla.html").read_text(encoding="utf-8")
    (AQUI / "visor_carro.html").write_text(plantilla.replace("__GLB_BASE64__", base64.b64encode(datos).decode()),
                                           encoding="utf-8")
    print("visor:", AQUI / "visor_carro.html")


if __name__ == "__main__":
    main()
