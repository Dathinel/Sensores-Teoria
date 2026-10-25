"""Exporta la maqueta impresa: un STL por pieza (ya girada y apoyada en la cama), las tandas en 3MF (camas
llenas de la Creality Hi, agrupadas por subsistema) y la cuenta de material (gramos, horas y rollos).

Usa las mismas listas que revisar.py (maqueta.scad, modo "lista") y los mismos parametros de masa y tiempo
que el carro (chasis_impreso/exportar.py): masa = cascara + relleno, tiempo = caudal + tiempo por capa (+-30 %).
Los remaches se agrupan por agarre (cada medida es un STL) con 10 % de repuesto (minimo 2 de mas).

Uso: python exportar.py   (correr antes python revisar.py: si no da TODO OK, no se exporta)
Salida: stl/<pieza>.stl, 3mf/<tanda>.3mf, piezas.json y material.md
"""
import json
import math
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import revisar as R
from revisar import ex_carro

AQUI = R.AQUI
D_STL, D_3MF = AQUI / "stl", AQUI / "3mf"
CAMA = ex_carro.CAMA
MARGEN = ex_carro.MARGEN
PLA = ex_carro.PLA_G_CM3
CAUDAL = ex_carro.CAUDAL_MM3_S
S_CAPA = ex_carro.S_POR_CAPA
PRECIO_KG = 93900      # COP, config/precios.yaml (estructura_3d.impresion.precio_kg)
SUBSISTEMAS = {"alm": "Almacén de monedas", "mon": "Cinta de monedas", "vas": "Cinta de vasos",
               "tap": "Tapas, prensa y empujador", "can": "Canaleta y muelle", "rem": "Remaches"}


def subsistema(n):
    if n.startswith("rem_"):
        return "rem"
    pre = n.split("_", 1)[0]
    if pre in SUBSISTEMAS:
        return pre
    return {"t": "est_tubos", "e": "est_uniones", "taco": "est_uniones"}.get(pre, "est_nodos")


NOMBRE_GRUPO = {"est_tubos": "Estructura: tubos", "est_nodos": "Estructura: nodos", "est_uniones": "Estructura: empalmes y tacos",
                **SUBSISTEMAS}
# parametros de impresion por grupo: (capa, paredes, relleno %)
# (2026-10-24, "aligerar pero que siga manteniendo un gran esfuerzo"): la fuerza esta en las paredes, no en el
# relleno. Tubos: pared de 1,6 = 4 perimetros (el hueco ya es hueco; con 1,2 la viga pasaba el limite de flecha).
# Nodos y empalmes: 4 perimetros (dejan macizas las paredes de 2,4 de las cajeras y 1,6 alrededor de cada remache)
# y 20 % en el nucleo (con 6 perimetros salian MAS pesados: 647 g contra 520). Lo demas: 4 perimetros y 15 %.
PARAM = {"est_tubos": (0.2, 4, 15), "est_nodos": (0.2, 4, 20), "est_uniones": (0.2, 4, 20), "rem": (0.12, 4, 100)}
PARAM_DEF = (0.2, 4, 15)


def masa_tiempo(tri, grupo):
    capa, paredes, relleno = PARAM.get(grupo, PARAM_DEF)
    vol, area = ex_carro.volumen_area(tri)
    alto = np.ptp(tri.reshape(-1, 3)[:, 2])
    cascara = min(vol, area * paredes * 0.42 * 0.5 + area * 0.5 * 4 * capa * 0.5)
    v = cascara + relleno / 100 * (vol - cascara)
    return v / 1000 * PLA, (v / CAUDAL + alto / capa * S_CAPA) / 60


def cama(tri):
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    return tri - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])


def remaches_stl(rem):
    """Un STL por medida de remache (agarre redondeado a 0,1) y cuantos hacen falta."""
    cuenta = Counter(round(a, 1) for _, a, _, _ in rem)
    out = {}
    for a, n in sorted(cuenta.items()):
        nombre = f"rem_{str(a).replace('.', '_')}"
        with tempfile.TemporaryDirectory() as t:
            s, o = Path(t) / "r.scad", Path(t) / "r.stl"
            s.write_text(f'include <{(AQUI / "comun.scad").as_posix()}>\nrotate([90, 0, 0]) remache({a});\n')
            subprocess.run([str(R.OPENSCAD), "-o", str(o), str(s)], capture_output=True)
            out[nombre] = (cama(ex_carro.leer_stl(o)), n + max(2, math.ceil(n * 0.1)), a, n)
    return out


def camas(rects):
    """Reparte piezas en camas: llena una con acomodar() y lo que no entra pasa a la siguiente."""
    resto, salida = list(rects), []
    ancho, alto = CAMA[0] - 2 * MARGEN, CAMA[1] - 2 * MARGEN
    while resto:
        puestos = None
        for k in range(len(resto), 0, -1):
            puestos = ex_carro.acomodar(resto[:k], ancho, alto)
            if puestos:
                break
        assert puestos, f"{resto[0][0]} no cabe solo en la cama"
        salida.append(puestos)
        usados = {p[0] for p in puestos}
        resto = [r for r in resto if r[0] not in usados]
    return salida


def main():
    piezas, rem, _ = R.listas()
    D_STL.mkdir(exist_ok=True)
    D_3MF.mkdir(exist_ok=True)
    for f in list(D_STL.glob("*.stl")) + list(D_3MF.glob("*.3mf")):
        f.unlink()

    def una(n):
        ruta = D_STL / f"{n}.stl"
        R.scad(ruta, modo="cama", cual=n)
        tri = cama(ex_carro.leer_stl(ruta))
        ex_carro.escribir_stl(ruta, tri)
        return n, tri

    with ThreadPoolExecutor(R.HILOS) as ej:
        mallas = dict(ej.map(una, piezas))
    filas = []
    for n, tri in mallas.items():
        g = subsistema(n)
        gramos, minutos = masa_tiempo(tri, g)
        filas.append(dict(pieza=n, grupo=g, cantidad=1, medidas=np.ptp(tri.reshape(-1, 3), 0).round(1).tolist(),
                          gramos=round(gramos, 1), minutos=round(minutos, 1), parametros=PARAM.get(g, PARAM_DEF)))
    for n, (tri, cant, agarre, usados) in remaches_stl(rem).items():
        ex_carro.escribir_stl(D_STL / f"{n}.stl", tri)
        mallas[n] = tri
        gramos, minutos = masa_tiempo(tri, "rem")
        filas.append(dict(pieza=n, grupo="rem", cantidad=cant, usados=usados, agarre=agarre,
                          medidas=np.ptp(tri.reshape(-1, 3), 0).round(1).tolist(), gramos=round(gramos, 2),
                          minutos=round(minutos, 1), parametros=PARAM["rem"]))
    # tandas por grupo
    por_grupo = defaultdict(list)
    for f in filas:
        for k in range(f["cantidad"]):
            clave = f["pieza"] if f["cantidad"] == 1 else f"{f['pieza']}__{k + 1}"
            por_grupo[f["grupo"]].append((clave, f["medidas"][0] + 2, f["medidas"][1] + 2))
    tandas = []
    for g in sorted(por_grupo):
        for i, puestos in enumerate(camas(por_grupo[g]), start=1):
            nombre = f"{g}_{i}"
            objetos = [(n, mallas[n.split("__")[0]], (MARGEN + x + w / 2, MARGEN + y + h / 2), gir) for n, x, y, gir, w, h in puestos]
            ex_carro.escribir_3mf(D_3MF / f"{nombre}.3mf", objetos)
            g_t = sum(next(f["gramos"] for f in filas if f["pieza"] == n.split("__")[0]) for n, *_ in puestos)
            m_t = sum(next(f["minutos"] for f in filas if f["pieza"] == n.split("__")[0]) for n, *_ in puestos)
            tandas.append(dict(tanda=nombre, grupo=NOMBRE_GRUPO[g], piezas=len(puestos), gramos=round(g_t), horas=round(m_t / 60, 1)))
            for n, *_ in puestos:
                fila = next(f for f in filas if f["pieza"] == n.split("__")[0])
                fila.setdefault("tandas", [])
                if nombre not in fila["tandas"]:
                    fila["tandas"].append(nombre)
    total_g = sum(f["gramos"] * f["cantidad"] for f in filas)
    total_h = sum(f["minutos"] * f["cantidad"] for f in filas) / 60
    (AQUI / "piezas.json").write_text(json.dumps(dict(piezas=filas, tandas=tandas, total_gramos=round(total_g),
                                                      total_horas=round(total_h, 1)), indent=1, ensure_ascii=False), encoding="utf-8")
    # material.md
    L = ["# Material de la maqueta impresa (GENERADO por exportar.py)", "",
         f"**Total: {total_g / 1000:.2f} kg de PLA ({math.ceil(total_g * 1.1 / 1000)} rollos de 1 kg con 10 % de "
         f"desperdicio), ≈ {total_h:.0f} h de impresora (±30 %), ≈ ${total_g * 1.1 / 1000 * PRECIO_KG:,.0f} de filamento.**".replace(",", "."),
         "", "Masa = cáscara + relleno con los parámetros de cada grupo; tiempo = caudal de 10 mm³/s + 2,5 s por capa "
         "(los mismos del carro). El tiempo real lo da Creality Print al laminar.", "",
         "| Grupo | Piezas | Gramos | Horas | Capa / paredes / relleno |", "|---|---:|---:|---:|---|"]
    por = defaultdict(lambda: [0, 0.0, 0.0])
    for f in filas:
        por[f["grupo"]][0] += f["cantidad"]
        por[f["grupo"]][1] += f["gramos"] * f["cantidad"]
        por[f["grupo"]][2] += f["minutos"] * f["cantidad"] / 60
    for g in sorted(por):
        c, gr, h = por[g]
        L.append(f"| {NOMBRE_GRUPO[g]} | {c} | {gr:.0f} | {h:.1f} | {' / '.join(map(str, PARAM.get(g, PARAM_DEF)))} |")
    L += ["", "## Tandas (una cama llena cada una)", "", "| Tanda (3mf/) | Grupo | Piezas | Gramos | Horas |", "|---|---|---:|---:|---:|"]
    L += [f"| {t['tanda']}.3mf | {t['grupo']} | {t['piezas']} | {t['gramos']} | {t['horas']} |" for t in tandas]
    L += ["", "## Remaches (se imprimen acostados; 10 % de repuesto, mínimo 2)", "", "| STL | Agarre (mm) | Van | A imprimir |", "|---|---:|---:|---:|"]
    L += [f"| {f['pieza']}.stl | {f['agarre']} | {f['usados']} | {f['cantidad']} |" for f in filas if f["grupo"] == "rem"]
    L += ["", "## Piezas", "", "| Pieza | Medidas en la cama (mm) | Gramos | Minutos |", "|---|---|---:|---:|"]
    L += [f"| {f['pieza']} | {' × '.join(f'{m:g}' for m in f['medidas'])} | {f['gramos']} | {f['minutos']} |"
          for f in sorted(filas, key=lambda f: f["pieza"]) if f["grupo"] != "rem"]
    (AQUI / "material.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(filas)} STL, {len(tandas)} tandas, {total_g / 1000:.2f} kg, {total_h:.0f} h")


if __name__ == "__main__":
    sys.exit(main())
