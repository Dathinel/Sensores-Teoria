"""Auditoria completa de cada pieza de la maqueta, con TODOS los criterios juntos (usuario, 2026-10-24: "haga otra vez
una auditoria completa y arreglelo"): los que se usaron para el carro y los que salieron de la maqueta.

Por cada STL en orientacion de cama (_cache/cama, lo escribe revisar.py):
  A. Primera capa (lo que fallo en el carro y en alm_1): islas, agujeros chicos (< 8 mm), ranuras y tiras de menos de
     1,2 mm (cuentan como agujeros chicos), tiras finas, y la HUELLA:
     cuanta cama toca la pieza (area de la primera capa) y que tan alta es respecto de lo angosto de su base
     (una placa de pie de 4 mm y 64 mm de alto necesita brim ancho o se tumba).
  B. Sin soportes: voladizos > 50 grados, puentes > 12 mm y agujeros horizontales > Ø12 sin gota, y capa por capa (cada
     0,2 mm) nada que nazca en el aire ni que cuelgue de una sola punta (voladizos.py, el de la maqueta, el mismo de
     revisar.py).
  C. Paredes finas en TODA la altura: un corte cada CORTE_PASO mm desde 1 mm hasta 1 mm bajo la punta (antes 4
     alturas y el cuarto de arriba no se miraba; el ultimo mm no, porque la arista de arriba de una cuna o un chaflan
     siempre es mas fina que 1,1 en sus ultimos 0,7 mm); material de menos de PARED_MIN se marca (una pared asi sale
     debil o no sale).
  D. Cabe en la cama (240 x 240 x 290 con margen).
Remaches, choques, barridos y mecanismos NO se revisan aqui: los mide revisar.py (TODO OK antes de exportar). Aqui
solo cada pieza sola, sobre los STL de _cache/cama, que tienen que estar vigentes (si no, sale sin escribir nada).

Uso: python auditar.py  -> auditoria.md (tabla por pieza) y sale con 1 si alguna pieza falla en algo.
"""
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

import primera_capa as PC
import revisar as R
from revisar import CACHE, ex_carro, volad      # volad = voladizos.py de la maqueta

AQUI = R.AQUI
PARED_MIN = 1.1            # mm: una pared de 1,2 (3 perimetros de 0,4) tiene que pasar; menos de eso no sale
CORTE_PASO = 1.0           # mm entre cortes de las paredes finas
HUELLA_MIN = 0.15          # area NETA de la primera capa / area del rectangulo que ocupa: menos, se despega (patas sueltas)
# brim por pieza y esbeltez maxima: los de primera_capa.py (los mismos que usa revisar.py)


def finos_por_altura(ruta, alto, ancho_y):
    """{z: mm2 de material mas fino que PARED_MIN en la seccion a la altura z}, un corte cada CORTE_PASO en toda la
    altura, todos en una sola corrida de OpenSCAD (cada corte corrido en y para separarlos en el SVG)."""
    zs = list(np.arange(1.0, alto - 1.0, CORTE_PASO)) + [alto - 1.0]
    paso = ancho_y + 20
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        cuerpo = []
        for i, z in enumerate(zs):
            sec = f'projection(cut = true) translate([0, 0, -{z:.3f}]) import("{Path(ruta).resolve().as_posix()}");'
            cuerpo.append(f"translate([0, {i * paso}]) difference() {{ {sec} offset(r = {PARED_MIN / 2}) offset(delta = -{PARED_MIN / 2}) {sec} }}")
        finos = PC.poligonos(" ".join(cuerpo), tmp)
    out = {z: 0.0 for z in zs}
    for q in finos:      # cada camino al corte de su franja en y (los exteriores suman y los agujeros restan)
        i = int(round(q[:, 1].mean() / paso))
        if 0 <= i < len(zs):
            out[zs[i]] -= PC.firmada(q)
    return out


def auditar(n):
    ruta = CACHE / "cama" / f"{n}.stl"
    tri = ex_carro.leer_stl(ruta)
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    alto = hi[2] - lo[2]
    pc = PC.medir(ruta)
    vol = volad.revisar(tri)
    # huella (con el area neta, sin los agujeros) y esbeltez con la base que toca la cama, no con la caja (2026-10-25:
    # tap_pre_placa daba 3,8 con la caja y 9,3 con su base real de 6)
    ancho_min = float(min(hi[0] - lo[0], hi[1] - lo[1]))
    huella = pc["area"] / max((hi[0] - lo[0]) * (hi[1] - lo[1]), 1)
    esbeltez = PC.esbeltez(n, pc)
    # paredes finas en toda la altura (la primera capa la mide primera_capa.py)
    por_z = finos_por_altura(ruta, alto, hi[1] - lo[1]) if alto > 2.0 else {}
    z_finos, finos = max(por_z.items(), key=lambda kv: kv[1]) if por_z else (0.0, 0.0)
    cabe = ancho_min <= R.CAMA_UTIL[0] and max(hi[0] - lo[0], hi[1] - lo[1]) <= R.CAMA_UTIL[1] and alto <= R.CAMA_UTIL[2]
    fallas = []
    if pc["islas"] > 1:
        fallas.append(f"{pc['islas']} islas en la primera capa")
    if pc["chicos"] + pc["angostas"] > PC.CHICOS_MAX:
        fallas.append(f"{pc['chicos']} agujeros chicos y {pc['angostas']} ranuras o tiras < {PC.ANCHO_MIN:g} mm en la primera capa")
    if pc["finos_mm2"] > 20:
        fallas.append(f"{pc['finos_mm2']:.0f} mm2 de tiras finas en la primera capa")
    if huella < HUELLA_MIN and alto > 20 and esbeltez <= PC.ESBELTEZ_MAX:   # una placa de pie ya sale como esbelta
        avisos_huella = f"huella {huella:.0%} del rectangulo: revisar que apoye bien (brim)"
    else:
        avisos_huella = None
    fallas += volad.mal(vol, n)
    if finos > 60:            # 60 mm2: las crestas de una rosca impresa (prisioneros) dan ~40 y no son un defecto
        fallas.append(f"{finos:.0f} mm2 de paredes < {PARED_MIN} mm en z {z_finos:.1f}")
    if not cabe:
        fallas.append("no cabe en la cama")
    avisos = [avisos_huella] if avisos_huella else []
    avisos += [f"puente de {c['puente']} mm aceptado a mano" for c in vol.get("colgados", []) if volad.aceptado(c, n)]
    if esbeltez > PC.ESBELTEZ_MAX or pc["cdm_margen"] < -3.0:
        fallas.append(f"de pie: {alto:.0f} de alto sobre {pc['base_min']:.1f} de base (esbeltez {esbeltez:.1f}), centro de masa a "
                      f"{pc['cdm_margen']:+.1f} del borde")
    elif pc["despegue_mpa"] > PC.DESPEGUE_MAX and n not in PC.BRIM_OBJETO:
        fallas.append(f"despegue de {pc['despegue_mpa']:.2f} MPa en la base sin brim propio")
    elif pc["despegue_mpa"] > PC.DESPEGUE_MAX:
        avisos.append(f"despegue de {pc['despegue_mpa']:.2f} MPa (brim propio de {PC.BRIM_OBJETO[n]:g})")
    elif pc["cdm_margen"] < 0:
        avisos.append(f"centro de masa {-pc['cdm_margen']:.1f} mm fuera de la base (brim {PC.BRIM_OBJETO.get(n, PC.BRIM_DEF):g})")
    if 0 < pc["chicos"] + pc["angostas"] <= PC.CHICOS_MAX:
        avisos.append(f"{pc['chicos']} agujero(s) chico(s) y {pc['angostas']} ranura(s) o tira(s) angosta(s) en la primera capa")
    return dict(pieza=n, medidas=f"{hi[0] - lo[0]:.0f} × {hi[1] - lo[1]:.0f} × {alto:.0f}", islas=pc["islas"], chicos=pc["chicos"] + pc["angostas"],
                huella=huella, esbeltez=esbeltez, voladizo=vol["voladizo"], puente=vol["puente_largo"], finos=finos,
                aire=len(vol["islas"]) + len(vol["colgados"]),
                fallas=fallas, avisos=avisos)


def main():
    piezas, rem, _ = R.listas()
    viejos = R.viejos([CACHE / "cama" / f"{n}.stl" for n in piezas])
    if viejos:      # 2026-10-25: auditaba orientaciones que ya habian cambiado
        print(f"{len(viejos)} STL de _cache/cama faltan o se dibujaron con otros .scad: "
              f"{', '.join(r.stem for r in viejos[:12])}{' ...' if len(viejos) > 12 else ''}. Correr antes python revisar.py")
        return 1
    with ThreadPoolExecutor(R.HILOS) as ej:
        filas = list(ej.map(auditar, piezas))
    malas = [f for f in filas if f["fallas"]]
    L = ["# Auditoría de cada pieza (GENERADO por auditar.py)", "",
         f"{len(filas)} piezas. Criterios: primera capa (1 isla, ≤ {PC.CHICOS_MAX} entre agujeros < {PC.D_CHICO:g} mm y ranuras o tiras < {PC.ANCHO_MIN:g} mm, sin tiras finas, "
         f"huella ≥ {HUELLA_MIN:.0%}), sin soportes (voladizos > {volad.ANGULO_MAX}°, puentes > {volad.PUENTE_MAX} mm y agujeros "
         f"horizontales > Ø{volad.D_HORIZ_MAX:g} sin gota; capa por capa cada {volad.CAPA:g} mm, nada que nazca en el aire ni que "
         f"empiece a más de {volad.ZONA_MAX:g} mm de la capa de abajo salvo un puente ≤ {volad.PUENTE_MAX} apoyado en las dos puntas), paredes ≥ {PARED_MIN} mm en toda la altura (un corte cada "
         f"{CORTE_PASO:g} mm), cabe en la cama; de pie: alto / (base mínima de la primera capa + 2 × brim) "
         f"≤ {PC.ESBELTEZ_MAX:g}, el centro de masa a menos de 3 mm fuera de la base y despegue (0,2 N en la punta + inercia "
         f"de la cama, sobre el módulo resistente de la primera capa) ≤ {PC.DESPEGUE_MAX:g} MPa o brim propio. "
         "Los remaches, choques y barridos los mide revisar.py (TODO OK antes de exportar).", "",
         f"**{len(malas)} piezas con fallas; {sum(1 for f in filas if f['avisos'])} con avisos.**", "",
         "| Pieza | Medidas en la cama (mm) | Islas | Agujeros chicos y angostas | Huella | Esbeltez | Voladizo (mm²) | Puente (mm) | Sin apoyo abajo | Paredes finas (mm²) | Fallas | Avisos |",
         "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    for f in sorted(filas, key=lambda f: (-len(f["fallas"]), -len(f["avisos"]), f["pieza"])):
        L.append(f"| {f['pieza']} | {f['medidas']} | {f['islas']} | {f['chicos']} | {f['huella']:.0%} | {f['esbeltez']:.1f} | "
                 f"{f['voladizo']:.0f} | {f['puente']:.1f} | {f['aire']} | {f['finos']:.0f} | {'; '.join(f['fallas']) or '—'} | {'; '.join(f['avisos']) or '—'} |")
    (AQUI / "auditoria.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    for f in malas:
        print(f"MAL  {f['pieza']:24s} {'; '.join(f['fallas'])}")
    for f in filas:
        if f["avisos"] and not f["fallas"]:
            print(f"aviso {f['pieza']:23s} {'; '.join(f['avisos'])}")
    print(f"auditoria.md: {len(malas)} piezas con fallas de {len(filas)}")
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main())
