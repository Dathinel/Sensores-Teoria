"""Exporta la maqueta impresa: un STL por pieza (ya girada y apoyada en la cama), las tandas en 3MF (camas
llenas de la Creality Hi, agrupadas por subsistema) y la cuenta de material (gramos, horas y rollos).

Usa las mismas listas que revisar.py (maqueta.scad, modo "lista") y los mismos parametros de masa y tiempo
que el carro (chasis_impreso/exportar.py): masa = cascara + relleno, tiempo = caudal + tiempo por capa (+-30 %).
Los remaches se agrupan por agarre (cada medida es un STL) con 10 % de repuesto (minimo 2 de mas).

Cada 3MF lleva ADENTRO la configuracion de Creality Print 7.3 (perfil_creality.json: proceso "0.20mm Standard @dathi
0.4 maqueta" y filamento "Hyper PLA @dathi 0.4 humedo maqueta" en los 3 huecos), con la capa, paredes y relleno de su
grupo y el brim propio de las piezas que lo necesitan (2026-10-25: alm_1 se lamino con el filamento del hueco 2, el
del sistema, y la sincronizacion con la nube borro los perfiles hechos a mano). Asi no depende de elegir el perfil.

Uso: python exportar.py   (correr antes python revisar.py completo: si su ultima corrida no dio TODO OK con los .scad
                           de ahora, no se exporta; revisar.py deja el sello en _cache/revision_ok.huella)
Salida: stl/<pieza>.stl, 3mf/<tanda>.3mf, piezas.json y material.md
"""
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import primera_capa as PC
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
PERFIL = AQUI / "perfil_creality.json"   # project_settings de Creality Print 7.3 (sin la MAC de la impresora)
VERSION_CP = "Creality_Print V7.3.0.6157 Release"
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


def config_tanda(g):
    """La configuracion del perfil con la capa, paredes y relleno del grupo. Las claves que cambian van tambien en
    different_settings_to_system: si no, Creality Print 7.3 las devuelve al valor del sistema (medido con su CLI)."""
    cfg = json.loads(PERFIL.read_text(encoding="utf-8"))
    capa, paredes, relleno = PARAM.get(g, PARAM_DEF)
    # filter_out_gap_fill (2026-10-25, segunda opinion): sin el, la primera capa de alm_1 llevaba 93 rellenos de hueco de
    # 0,1-0,3 mm, 83 con retraccion y salto; los de menos de 0,5 mm no rellenan nada y con PLA humedo dejan babas
    cambios = {"layer_height": f"{capa:g}", "wall_loops": str(paredes), "sparse_infill_density": f"{relleno}%",
               "filter_out_gap_fill": "0.5"}
    if g == "rem":   # 3,2 de alto sobre 1,6-6 de base: no se tumban; con la pata de elefante sus patas de 0,77 se pierden
        cambios.update(brim_type="no_brim", elefant_foot_compensation="0")
    for k, v in cambios.items():
        assert k in cfg, k
        cfg[k] = v
    dif = cfg["different_settings_to_system"]
    dif[0] = ";".join(sorted(set(filter(None, dif[0].split(";"))) | set(cambios)))
    return cfg


def escribir_3mf_proyecto(ruta, objetos, cfg):
    """ex_carro.escribir_3mf en formato de proyecto de Creality Print 7.3: con la configuracion, cada objeto en el
    filamento 1 y el brim propio de las piezas de PC.BRIM_OBJETO. Sin la metadata Application el laminador reacomoda
    los objetos; sin model_settings no lamina ("Filament nozzle mapping is incomplete")."""
    ex_carro.escribir_3mf(ruta, objetos)
    with zipfile.ZipFile(ruta) as z:
        partes = {n: z.read(n) for n in z.namelist()}
    modelo = partes["3D/3dmodel.model"].decode("utf-8")
    modelo = modelo.replace('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
                            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
                            'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">'
                            f'<metadata name="Application">{VERSION_CP}</metadata>'
                            '<metadata name="BambuStudio:3mfVersion">1</metadata>'
                            '<metadata name="Designer">maqueta_impresa/exportar.py</metadata>', 1)
    partes["3D/3dmodel.model"] = modelo.encode("utf-8")
    ids = re.findall(r'<object id="(\d+)" name="([^"]+)"', modelo)
    obj = []
    for i, n in ids:
        brim = PC.BRIM_OBJETO.get(n.split("__")[0])
        # brim propio y PEGADO a la pared: con el hueco de 0,1 y la compensacion de 0,15 quedaba a 0,22 de aire y no
        # anclaba nada (medido en el G-code por la auditoria)
        extra = (f'<metadata key="brim_width" value="{brim:g}"/><metadata key="brim_object_gap" value="0"/>'
                 '<metadata key="elefant_foot_compensation" value="0"/>') if brim else ""
        obj.append(f'<object id="{i}"><metadata key="name" value="{n}"/><metadata key="extruder" value="1"/>{extra}'
                   f'<part id="{i}" subtype="normal_part"><metadata key="name" value="{n}"/></part></object>')
    inst = "".join(f'<model_instance><metadata key="object_id" value="{i}"/><metadata key="instance_id" value="0"/>'
                   '</model_instance>' for i, _ in ids)
    partes["Metadata/model_settings.config"] = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>' + "".join(obj) +
                                                '<plate><metadata key="plater_id" value="1"/>' + inst + '</plate></config>\n').encode("utf-8")
    partes["Metadata/project_settings.config"] = json.dumps(cfg, indent=4, ensure_ascii=False).encode("utf-8")
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in partes.items():
            z.writestr(n, d)


def guardar_proyectos_del_usuario():
    """Un 3MF que el usuario guardo desde Creality Print (trae Metadata/slice_info.config) no se borra: es el registro de
    con que configuracion imprimio (asi se supo lo de alm_1). Se mueve a 3mf/guardados/ con la fecha."""
    for f in D_3MF.glob("*.3mf"):
        try:
            with zipfile.ZipFile(f) as z:
                del_usuario = "Metadata/slice_info.config" in z.namelist()
        except zipfile.BadZipFile:
            del_usuario = False
        if del_usuario:
            (D_3MF / "guardados").mkdir(exist_ok=True)
            fecha = time.strftime("%Y%m%d-%H%M", time.localtime(f.stat().st_mtime))
            shutil.move(str(f), str(D_3MF / "guardados" / f"{f.stem}_{fecha}.3mf"))


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
    # solo lo revisado (2026-10-25: el docstring lo pedia y nadie lo comprobaba): la ultima revision completa tiene
    # que haber dado TODO OK con estos mismos .scad
    huella0 = R.huella()
    if not R.revision_ok():
        raise SystemExit("NO SE EXPORTA: la ultima corrida completa de revisar.py no dio TODO OK con los .scad de ahora "
                         "(o un .scad cambio despues). Correr python revisar.py (sin --sub) hasta TODO OK.")
    piezas, rem, _ = R.listas()
    D_STL.mkdir(exist_ok=True)
    D_3MF.mkdir(exist_ok=True)
    guardar_proyectos_del_usuario()
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
    # tandas por grupo. Entre piezas: dos brims de 5 y ~1,5 mm de aire (el rectangulo ya suma 1 por lado; con 6 los brims
    # vecinos se juntaban); una pieza con brim propio mas ancho (PC.BRIM_OBJETO) ocupa ese brim de mas por cada lado. Los
    # remaches van sin brim: 3 mm.
    por_grupo = defaultdict(list)
    for f in filas:
        extra = 2 * (PC.BRIM_OBJETO.get(f["pieza"], PC.BRIM_DEF) - PC.BRIM_DEF)
        for k in range(f["cantidad"]):
            clave = f["pieza"] if f["cantidad"] == 1 else f"{f['pieza']}__{k + 1}"
            por_grupo[f["grupo"]].append((clave, f["medidas"][0] + 2 + extra, f["medidas"][1] + 2 + extra))
    tandas = []
    for g in sorted(por_grupo):
        cfg = config_tanda(g)
        ex_carro.SEPARACION = 3.0 if g == "rem" else 2 * PC.BRIM_DEF - 1
        for i, puestos in enumerate(camas(por_grupo[g]), start=1):
            nombre = f"{g}_{i}"
            # centrada en la cama (acomodar llena desde la esquina): el centro es lo mas parejo
            dx = (CAMA[0] - 2 * MARGEN - max(x + w for _, x, _, _, w, _ in puestos)) / 2
            dy = (CAMA[1] - 2 * MARGEN - max(y + h for _, _, y, _, _, h in puestos)) / 2
            objetos = [(n, mallas[n.split("__")[0]], (MARGEN + dx + x + w / 2, MARGEN + dy + y + h / 2), gir)
                       for n, x, y, gir, w, h in puestos]
            escribir_3mf_proyecto(D_3MF / f"{nombre}.3mf", objetos, cfg)
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
         f"**Total: {total_g / 1000:.2f} kg de PLA ({math.ceil(total_g * 1.1 / 1000)} rollos de 1 kg con 10 % de ".replace(".", ",") +
         f"desperdicio), ≈ {total_h:.0f} h de impresora (±30 %), ≈ " +
         f"${total_g * 1.1 / 1000 * PRECIO_KG:,.0f} de filamento.**".replace(",", "."),   # coma decimal y punto de miles
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
    L += ["", "## Tandas (una cama llena cada una)", "",
          "Cada 3MF ya trae la configuración de Creality Print (proceso «0.20mm Standard @dathi 0.4 maqueta» y filamento "
          "«Hyper PLA @dathi 0.4 humedo maqueta» en los 3 huecos, con la capa, paredes y relleno de su grupo). Al abrirlo, "
          "cargarlo **como proyecto, con su configuración** (no «solo geometría») y revisar que todas las piezas estén en "
          "el filamento 1 y que ese filamento sea «Hyper PLA @dathi 0.4 humedo maqueta» (no aceptar «sincronizar filamentos "
          f"del CFS» si cambia el perfil). Brim de {PC.BRIM_DEF:g} mm; con brim propio, pegado a la pieza: "
          f"{', '.join(f'{n} {b:g} mm' for n, b in sorted(PC.BRIM_OBJETO.items()))}. Los remaches van sin brim y sin "
          "compensación de pata de elefante.", "",
          "| Tanda (3mf/) | Grupo | Piezas | Gramos | Horas |", "|---|---|---:|---:|---:|"]
    L += [f"| {t['tanda']}.3mf | {t['grupo']} | {t['piezas']} | {t['gramos']} | {t['horas']} |" for t in tandas]
    L += ["", "## Remaches (se imprimen acostados; 10 % de repuesto, mínimo 2)", "", "| STL | Agarre (mm) | Van | A imprimir |", "|---|---:|---:|---:|"]
    L += [f"| {f['pieza']}.stl | {f['agarre']} | {f['usados']} | {f['cantidad']} |" for f in filas if f["grupo"] == "rem"]
    L += ["", "## Piezas", "", "| Pieza | Medidas en la cama (mm) | Gramos | Minutos |", "|---|---|---:|---:|"]
    L += [f"| {f['pieza']} | {' × '.join(f'{m:g}' for m in f['medidas'])} | {f['gramos']} | {f['minutos']} |"
          for f in sorted(filas, key=lambda f: f["pieza"]) if f["grupo"] != "rem"]
    (AQUI / "material.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(filas)} STL, {len(tandas)} tandas, {total_g / 1000:.2f} kg, {total_h:.0f} h")
    if R.huella() != huella0:
        raise SystemExit("MAL: un .scad cambio mientras se exportaba: stl/ y 3mf/ pueden mezclar dos versiones. Revisar y exportar otra vez.")


if __name__ == "__main__":
    sys.exit(main())
