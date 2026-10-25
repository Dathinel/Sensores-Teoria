"""Lamina cada tanda (3mf/*.3mf) con el CLI de Creality Print 7.3 y revisa el G-code (2026-10-25).

Comprueba lo que fallo en alm_1: que use el proceso y el filamento "maqueta" (no los del sistema), un solo filamento,
cama a 65, sin repaso en seco (;WIPE_START) en la primera capa, y que la capa sea la de su grupo. De paso saca del
G-code el tiempo y los gramos que calcula el laminador (los de material.md son una estimacion de +-30 %).

El CLI corre con --datadir en _cache/cp_datadir: NO usa ni toca los perfiles del usuario. Nunca abrir
CrealityPrint.exe sin --cli: la interfaz se sincroniza con la nube y borro los perfiles hechos a mano.

Uso: python laminar.py [3mf/alm_1.3mf ...]   (sin argumentos, todas)  -> laminado.json y sale con 1 si algo falla
"""
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EXE = Path(r"C:\Program Files\Creality\Creality Print 7.0\CrealityPrint.exe")
DATADIR = AQUI / "_cache" / "cp_datadir"
CAPA = {"rem": 0.12}          # capa por grupo (el resto 0,2): la misma de PARAM en exportar.py
A_LA_VEZ = 2                  # el laminador usa todos los nucleos: dos a la vez ya cargan la CPU


def ajustes(gcode):
    """Las lineas '; clave = valor' del final del G-code (la configuracion con que se lamino)."""
    return dict(re.findall(r"^; ([a-z_0-9]+) = (.*)$", gcode, flags=re.M))


def primera_capa(gcode):
    ini = gcode.find(";LAYER_CHANGE")
    fin = gcode.find(";LAYER_CHANGE", ini + 1)
    return gcode[ini:fin]


def revisar_gcode(nombre, gcode):
    a = ajustes(gcode)
    grupo = nombre.rsplit("_", 1)[0]
    problemas = []
    if a.get("print_settings_id", "").strip('"') != "0.20mm Standard @dathi 0.4 maqueta":
        problemas.append(f"proceso {a.get('print_settings_id')}")
    if "humedo maqueta" not in a.get("filament_settings_id", "") or "Creality Hi 0.4 nozzle" in a.get("filament_settings_id", ""):
        problemas.append(f"filamento {a.get('filament_settings_id')}")
    if a.get("wipe_on_loops") != "0":
        problemas.append(f"wipe_on_loops {a.get('wipe_on_loops')}")
    if abs(float(a.get("layer_height", 0)) - CAPA.get(grupo, 0.2)) > 1e-6:
        problemas.append(f"capa {a.get('layer_height')}")
    herramientas = set(re.findall(r"^T(\d)\s*$", gcode, flags=re.M))
    if len(herramientas) > 1:
        problemas.append(f"usa los filamentos {sorted(herramientas)}")
    m = re.search(r"START_PRINT EXTRUDER_TEMP=(\d+) BED_TEMP=(\d+)", gcode)
    if not m or m[2] != "65":
        problemas.append(f"cama {m[2] if m else '?'}")
    c1 = primera_capa(gcode)
    if ";WIPE_START" in c1:
        problemas.append(f"{c1.count(';WIPE_START')} repasos en seco en la primera capa")
    tiempo = re.search(r"^; estimated printing time \(normal mode\) = (.+)$", gcode, flags=re.M)
    gramos = re.search(r"^; total filament used \[g\] = ([\d.]+)", gcode, flags=re.M)
    return dict(tanda=nombre, problemas=problemas, tiempo=tiempo[1].strip() if tiempo else None,
                gramos=float(gramos[1]) if gramos else None, retracciones_capa1=c1.count("G1 E-"))


def laminar(ruta):
    DATADIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        r = subprocess.run([str(EXE), "--cli", "--datadir", str(DATADIR), "--slice", "1", "--need-gcode-file",
                            "--outputdir", t, str(ruta)], capture_output=True, text=True, errors="replace", timeout=900)
        g = Path(t) / "plate_1.gcode"
        if not g.exists():
            return dict(tanda=ruta.stem, problemas=[f"no lamino (rc {r.returncode}): {(r.stdout + r.stderr)[-300:]}"])
        return revisar_gcode(ruta.stem, g.read_text(encoding="utf-8", errors="replace"))


def main():
    assert EXE.exists(), f"no esta {EXE}"
    rutas = [Path(a) for a in sys.argv[1:]] or sorted((AQUI / "3mf").glob("*.3mf"))
    with ThreadPoolExecutor(A_LA_VEZ) as ej:
        res = list(ej.map(laminar, rutas))
    for r in res:
        print(f"{'MAL ' if r['problemas'] else 'ok  '} {r['tanda']:16s} {r.get('tiempo') or '':>14s} {r.get('gramos') or 0:7.1f} g  "
              f"{'; '.join(r['problemas'])}")
    (AQUI / "laminado.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    malas = [r for r in res if r["problemas"]]
    print(f"{len(res) - len(malas)} de {len(res)} tandas bien laminadas")
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main())
