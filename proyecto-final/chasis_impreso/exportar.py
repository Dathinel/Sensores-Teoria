"""Exporta el chasis impreso: un STL por pieza (ya acostada para imprimir), un 3MF por tanda que
cabe en la cama, la revision de choques entre piezas y la tabla de masa / tiempo aproximados.

Uso (Python 3.14 global, solo numpy):
    python exportar.py              # todo
    python exportar.py --sin-choques
    python exportar.py --solo prueba_tolerancias
Cambiar medidas: en chasis.scad (o -D) y volver a correr. Salida en stl/, 3mf/ y piezas.md.
"""
import argparse
import json
import re
import struct
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
SCAD = AQUI / "chasis.scad"
OPENSCAD = Path(r"D:\cosas uni\Micros\instalados\openscad\openscad.com")
CAMA = (260.0, 260.0, 300.0)
MARGEN = 10.0          # borde libre en la cama
SEPARACION = 6.0       # entre piezas de una tanda
PLA_G_CM3 = 1.24
# Caudal medio realista del Hi con PLA a 0.2 mm (perfil estandar): ~10 mm3/s contando
# perimetros lentos y viajes; + ~2.5 s por capa (cambio de capa, z-hop). Es una estimacion
# (+-30 %): el laminador da el numero bueno.
CAUDAL_MM3_S = 10.0
S_POR_CAPA = 2.5

# nombre: (cantidad, tanda, capa, paredes, relleno %, patron, orientacion, esfuerzo)
PIEZAS = {
    "prueba_tolerancias": (1, 0, 0.2, 3, 20, "giroide", "plana, como sale", "ninguno: solo mide encajes"),
    "chasis": (1, 1, 0.2, 3, 25, "giroide", "piel abajo, nervios y columnas hacia arriba", "flexion y torsion; lleva todo"),
    "barra_tcrt5000": (1, 1, 0.2, 3, 15, "rejilla", "de costado (la U acostada, sin puentes)", "bajo (golpes leves en el piso)"),
    "porta_baterias": (1, 1, 0.2, 3, 20, "giroide", "piso contra la cama", "medio (pack de ~95 g, aceleraciones)"),
    "pared_cuna_izq": (1, 2, 0.2, 3, 20, "giroide", "acostada, cara del vaso contra la cama", "medio: cuelga el vaso (133 g)"),
    "pared_cuna_der": (1, 2, 0.2, 3, 20, "giroide", "acostada, cara del vaso contra la cama", "medio: cuelga el vaso (133 g)"),
    "mampara": (1, 2, 0.2, 3, 20, "giroide", "cara delantera contra la cama", "medio: amarra las dos paredes"),
    "zapata_guia": (4, 2, 0.2, 2, 15, "rejilla", "cara del vaso contra la cama (lisa para la PTFE)", "bajo"),
    "lengueta": (1, 2, 0.2, 4, 40, "giroide", "plana", "bajo, pero gira en un tornillo"),
    "soporte_motor_izq": (1, 3, 0.2, 5, 50, "giroide", "techo contra la cama, mejillas hacia arriba", "alto: par del motor y peso del carro"),
    "soporte_motor_der": (1, 3, 0.2, 5, 50, "giroide", "techo contra la cama, mejillas hacia arriba", "alto: par del motor y peso del carro"),
    "soporte_encoder_izq": (1, 3, 0.2, 4, 40, "giroide", "como va montado: repisa contra la cama", "bajo (sostiene el H206)"),
    "soporte_encoder_der": (1, 3, 0.2, 4, 40, "giroide", "como va montado: repisa contra la cama", "bajo (sostiene el H206)"),
    "torre_rueda_loca": (1, 3, 0.2, 5, 50, "giroide", "brida contra la cama", "alto: ~40 % del peso"),
    "soporte_rodillo_izq": (1, 3, 0.2, 5, 50, "giroide", "brazo contra la cama, bloque hacia arriba", "alto: empuje lateral del muelle"),
    "soporte_rodillo_der": (1, 3, 0.2, 5, 50, "giroide", "brazo contra la cama, bloque hacia arriba", "alto: empuje lateral del muelle"),
    "piso2_esp32": (1, 4, 0.2, 3, 15, "rejilla", "placa contra la cama, separadores arriba", "bajo"),
    "soporte_tb6612": (1, 4, 0.2, 2, 15, "rejilla", "de costado (patas y marco suben derecho)", "bajo"),
    "caja_interruptor": (1, 4, 0.2, 2, 15, "rejilla", "panel contra la cama", "bajo (pulsar el interruptor)"),
    "caja_fusible": (1, 4, 0.2, 2, 15, "rejilla", "panel contra la cama", "bajo (cambiar el fusible)"),
    "escuadra_frontal": (1, 4, 0.2, 3, 15, "rejilla", "de costado (cara y pie de pie)", "bajo (sensores livianos)"),
    # Uniones (usuario, 2026-10-21: sin tornillos). Macizas: las patas tienen que flexar sin romperse.
    "pasador_tt": (4, 5, 0.12, 4, 100, "solido", "acostado sobre su cara plana", "alto: sujeta la caja TT"),
    "remache_6": (1, 5, 0.12, 4, 100, "solido", "acostado sobre su cara plana", "pivote de la lengueta"),
    "remache_9_5": (4, 5, 0.12, 4, 100, "solido", "acostado sobre su cara plana", "mampara a las paredes"),
    "remache_10_5": (8, 5, 0.12, 4, 100, "solido", "acostado sobre su cara plana", "motores (adelante), porta baterias, caja"),
    "remache_11": (8, 5, 0.12, 4, 100, "solido", "acostado sobre su cara plana", "paredes, mampara, escuadra"),
    "remache_14": (2, 5, 0.12, 4, 100, "solido", "acostado sobre su cara plana", "motores (atras)"),
    "remache_37": (4, 5, 0.12, 4, 100, "solido", "acostado sobre su cara plana", "rodillos guia"),
}
NOMBRE_TANDA = {0: "tanda0_prueba", 1: "tanda1_chasis", 2: "tanda2_cuna", 3: "tanda3_motores_uniones", 4: "tanda4_electronica",
                5: "tanda5_remaches_pasadores"}


# ----------------------------------------------------------------- STL
def leer_stl(ruta):
    datos = Path(ruta).read_bytes()
    if datos[:5] == b"solid" and b"facet" in datos[:300]:
        v = [list(map(float, l.split()[1:4])) for l in datos.decode().splitlines() if l.strip().startswith("vertex")]
        return np.array(v, dtype=np.float64).reshape(-1, 3, 3)
    n = struct.unpack("<I", datos[80:84])[0]
    reg = np.frombuffer(datos, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]), count=n, offset=84)
    return reg["v"].astype(np.float64)


def escribir_stl(ruta, tri):
    with open(ruta, "wb") as f:
        f.write(b"chasis_impreso".ljust(80, b" "))
        f.write(struct.pack("<I", len(tri)))
        reg = np.zeros(len(tri), dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
        a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
        n = np.cross(b - a, c - a)
        n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
        reg["n"], reg["v"] = n, tri
        f.write(reg.tobytes())


def volumen_area(tri):
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    vol = np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum()
    return abs(vol), area


def openscad(salida, pieza, extra=()):
    r = subprocess.run([str(OPENSCAD), "-D", f'pieza="{pieza}"', *extra, "-o", str(salida), str(SCAD)],
                       capture_output=True, text=True)
    log = r.stdout + r.stderr
    if r.returncode != 0 or not Path(salida).exists():
        sys.exit(f"OpenSCAD fallo con {pieza}:\n{log[-2000:]}")
    return log


# ----------------------------------------------------------------- tandas (estantes, con giro de 90 grados)
def acomodar(rects, ancho, alto):
    """rects: [(nombre, sx, sy)] -> [(nombre, x, y, girada)] o None si no caben (estantes, mas alto primero)."""
    orden = sorted(rects, key=lambda r: -max(r[1], r[2]))
    puestos, x, y, alto_estante = [], 0.0, 0.0, 0.0
    for nom, sx, sy in orden:
        opciones = [(sx, sy, False), (sy, sx, True)]
        # en el estante actual, la orientacion que deja el estante mas bajo
        puesto = None
        for w, h, g in sorted(opciones, key=lambda o: o[1]):
            if x + w <= ancho and y + h <= alto and (alto_estante == 0 or h <= alto_estante or x == 0):
                puesto = (w, h, g)
                break
        if puesto is None:
            y += alto_estante + SEPARACION
            x, alto_estante = 0.0, 0.0
            for w, h, g in sorted(opciones, key=lambda o: -o[0]):
                if w <= ancho and y + h <= alto:
                    puesto = (w, h, g)
                    break
            if puesto is None:
                return None
        w, h, g = puesto
        puestos.append((nom, x, y, g, w, h))
        x += w + SEPARACION
        alto_estante = max(alto_estante, h)
    return puestos


def escribir_3mf(ruta, objetos):
    """objetos: [(nombre, tri, (tx, ty), girada)] -> 3MF con un objeto por pieza, ya ubicado en la cama."""
    obj_xml, items = [], []
    for i, (nom, tri, (tx, ty), girada) in enumerate(objetos, start=1):
        v, idx = np.unique(np.round(tri.reshape(-1, 3), 5), axis=0, return_inverse=True)
        t = idx.reshape(-1, 3)
        verts = "".join(f'<vertex x="{a:.5f}" y="{b:.5f}" z="{c:.5f}"/>' for a, b, c in v)
        tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t)
        obj_xml.append(f'<object id="{i}" name="{nom}" type="model"><mesh><vertices>{verts}</vertices>'
                       f'<triangles>{tris}</triangles></mesh></object>')
        m = "0 1 0 -1 0 0 0 0 1" if girada else "1 0 0 0 1 0 0 0 1"
        items.append(f'<item objectid="{i}" transform="{m} {tx:.3f} {ty:.3f} 0"/>')
    modelo = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="es-CO" '
              'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
              f'<resources>{"".join(obj_xml)}</resources><build>{"".join(items)}</build></model>')
    tipos = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", tipos)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", modelo)


# ----------------------------------------------------------------- choques
def choques(dir_ens, nombres):
    """Interseccion de cada par de piezas en su lugar del ensamble (y de cada pieza con los
    componentes comprados). Mas de 1 mm3 = choque."""
    pares = [(a, b) for i, a in enumerate(nombres) for b in nombres[i + 1:]] + [(a, "componentes") for a in nombres]

    def uno(par):
        a, b = par
        scad = dir_ens / f"_x_{a}_{b}.scad"
        stl = dir_ens / f"_x_{a}_{b}.stl"
        scad.write_text(f'intersection() {{ import("{a}.stl"); import("{b}.stl"); }}\n')
        r = subprocess.run([str(OPENSCAD), "-o", str(stl), str(scad)], capture_output=True, text=True)
        vol = 0.0
        if stl.exists():
            tri = leer_stl(stl)
            vol = volumen_area(tri)[0] if len(tri) else 0.0
            stl.unlink()
        scad.unlink()
        return a, b, vol, r.returncode

    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(uno, pares))
    # A proposito: los pernos que atraviesan los agujeros de las placas (el modelo de la placa no tiene agujeros).
    esperados = {("barra_tcrt5000", "componentes"), ("piso2_esp32", "componentes"), ("escuadra_frontal", "componentes")}
    return [(a, b, v) for a, b, v, _ in res if v > 1.0 and not ((a, b) in esperados and v < 60)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-choques", action="store_true")
    ap.add_argument("--solo")
    args = ap.parse_args()
    # Dos versiones (usuario, 2026-10-21): con la membrana de la primera capa (sin saltos, hay que abrir los
    # agujeros despues: guia_corte.py) y sin ella (los agujeros salen abiertos, la primera capa tiene saltos).
    d_stl, d_3mf = AQUI / "stl_con_membrana", AQUI / "3mf_con_membrana"
    d_stl_sin, d_3mf_sin = AQUI / "stl_sin_membrana", AQUI / "3mf_sin_membrana"
    d_ens = d_stl_sin / "_ensamble"
    for d in (d_stl, d_3mf, d_stl_sin, d_3mf_sin, d_ens):
        d.mkdir(parents=True, exist_ok=True)
    nombres = [args.solo] if args.solo else list(PIEZAS)

    def exportar(nom):
        bruto = d_stl / f"_{nom}_bruto.stl"
        log = openscad(bruto, nom)
        tri = leer_stl(bruto)
        bruto.unlink()
        lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
        tri = tri - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
        escribir_stl(d_stl / f"{nom}.stl", tri)
        escribir_stl(d_stl_sin / f"{nom}.stl", tri)
        sin_membrana[nom] = tri
        if not nom.startswith(("remache", "pasador")):
            # primera capa de un solo contorno (sin saltos): ver primera_capa.scad
            cerrada = d_stl / f"_{nom}_capa.stl"
            r = subprocess.run([str(OPENSCAD), "-D", f'archivo="{(d_stl / f"{nom}.stl").as_posix()}"', "-o", str(cerrada),
                                str(AQUI / "primera_capa.scad")], capture_output=True, text=True)
            if r.returncode != 0 or not cerrada.exists():
                sys.exit(f"OpenSCAD fallo cerrando la primera capa de {nom}:\n{(r.stdout + r.stderr)[-2000:]}")
            tri = leer_stl(cerrada)
            cerrada.unlink()
            escribir_stl(d_stl / f"{nom}.stl", tri)
        if not nom.startswith(("prueba", "remache", "pasador")):
            # misma pieza en su lugar del ensamble (para los choques y el render)
            openscad(d_ens / f"{nom}.stl", "ensamble_pieza", ["-D", f'cual="{nom}"'])
        return nom, tri, "Status:     NoError" in log or "PolySet" in log

    sin_membrana = {}
    with ThreadPoolExecutor(6) as ex:
        hechas = {n: (t, ok) for n, t, ok in ex.map(exportar, nombres)}

    # Si el chasis no cabe en la cama (L o W agrandados en chasis.scad), se reemplaza por sus dos
    # mitades con colas de milano y la plaquita de union (mismos parametros de impresion).
    if "chasis" in hechas:
        ext = np.ptp(hechas["chasis"][0].reshape(-1, 3), axis=0)
        if ext[0] > CAMA[0] - 2 * MARGEN or ext[1] > CAMA[1] - 2 * MARGEN:
            del hechas["chasis"]
            (d_stl / "chasis.stl").unlink()
            (d_stl_sin / "chasis.stl").unlink()
            nombres.remove("chasis")
            for n in ("chasis_a", "chasis_b", "union_corte"):
                PIEZAS[n] = PIEZAS["chasis"] if n != "union_corte" else (1, 3, 0.2, 5, 50, "giroide", "plana", "alto: une el corte")
                nombres.append(n)
                hechas[n] = exportar(n)[1:]
            PIEZAS["remache_12"] = (4, 5, 0.12, 4, 100, "solido", "acostado sobre su cara plana", "plaquita del corte")
            nombres.append("remache_12")
            hechas["remache_12"] = exportar("remache_12")[1:]

    filas, avisos = [], []
    for nom in nombres:
        tri, ok = hechas[nom]
        cant, tanda, capa, paredes, relleno, patron, orient, esfuerzo = PIEZAS[nom]
        ext = np.ptp(tri.reshape(-1, 3), axis=0)
        vol, area = volumen_area(tri)
        cascara = min(vol, area * paredes * 0.42 * 0.5 + area * 0.5 * 4 * capa * 0.5)
        v_ext = cascara + relleno / 100 * (vol - cascara)
        gramos = v_ext / 1000 * PLA_G_CM3
        minutos = (v_ext / CAUDAL_MM3_S + ext[2] / capa * S_POR_CAPA) / 60
        if ext[0] > CAMA[0] - 2 * MARGEN or ext[1] > CAMA[1] - 2 * MARGEN or ext[2] > CAMA[2]:
            avisos.append(f"{nom}: {ext.round(1)} NO cabe en la cama")
        if not ok:
            avisos.append(f"{nom}: OpenSCAD no confirmo un solido cerrado (revisar)")
        filas.append(dict(pieza=nom, cantidad=cant, tanda=tanda, medidas=ext.round(1).tolist(), volumen_cm3=round(vol / 1000, 1),
                          gramos=round(gramos, 1), minutos=round(minutos), capa=capa, paredes=paredes, relleno=relleno,
                          patron=patron, orientacion=orient, esfuerzo=esfuerzo, masa_maciza_g=round(vol / 1000 * PLA_G_CM3, 1)))

    if not args.solo:
        # tandas -> 3MF
        for tanda, nombre in NOMBRE_TANDA.items():
            rects, mallas = [], {}
            for f in filas:
                if f["tanda"] != tanda:
                    continue
                for k in range(f["cantidad"]):
                    clave = f["pieza"] if f["cantidad"] == 1 else f"{f['pieza']}_{k + 1}"
                    rects.append((clave, f["medidas"][0], f["medidas"][1]))
                    mallas[clave] = hechas[f["pieza"]][0]
            puestos = acomodar(rects, CAMA[0] - 2 * MARGEN, CAMA[1] - 2 * MARGEN)
            if puestos is None:
                avisos.append(f"{nombre}: las piezas no caben juntas en la cama")
                continue
            objetos = [(n, mallas[n], (MARGEN + x + w / 2, MARGEN + y + h / 2), g) for n, x, y, g, w, h in puestos]
            escribir_3mf(d_3mf / f"{nombre}.3mf", objetos)
            base = {n: re.sub(r"_\d+$", "", n) if n not in sin_membrana else n for n in mallas}
            escribir_3mf(d_3mf_sin / f"{nombre}.3mf", [(n, sin_membrana[base[n]], c, g) for n, _, c, g in objetos])
        # que todo salga sin soportes (usuario, 2026-10-21): ver revisar_voladizos.py
        import revisar_voladizos
        for d in (d_stl_sin, d_stl):
            for ruta in sorted(d.glob("*.stl")):
                r = revisar_voladizos.revisar(ruta)
                if r["voladizo"] > 0 or r["puente_largo"] > revisar_voladizos.PUENTE_MAX:
                    avisos.append(f"{d.name}/{ruta.name}: necesita soporte ({r['voladizo']} mm2 en el aire, puente de {r['puente_largo']} mm)")
        if not args.sin_choques:
            openscad(d_ens / "componentes.stl", "componentes")
            hallados = choques(d_ens, [n for n in nombres if not n.startswith(("prueba", "remache", "pasador"))])
            for a, b, v in hallados:
                avisos.append(f"choque {a} <-> {b}: {v:.1f} mm3")
    (AQUI / "piezas.json").write_text(json.dumps(dict(piezas=filas, avisos=avisos), indent=1, ensure_ascii=False), encoding="utf-8")
    tot_g = sum(f["gramos"] * f["cantidad"] for f in filas if f["pieza"] != "prueba_tolerancias")
    tot_min = sum(f["minutos"] * f["cantidad"] for f in filas if f["pieza"] != "prueba_tolerancias")
    for f in filas:
        print(f"{f['pieza']:22s} x{f['cantidad']} T{f['tanda']} {str(f['medidas']):24s} {f['gramos']:6.1f} g {f['minutos']:4d} min")
    print(f"TOTAL (sin la prueba): {tot_g:.0f} g, {tot_min / 60:.1f} h")
    for a in avisos:
        print("AVISO:", a)


if __name__ == "__main__":
    main()
