"""Arma lo que se sube a cada ESP32 (fase 8), en firmware/salida/<placa>/.

    python -m firmware.preparar            # las dos placas
    python -m firmware.preparar carro      # una

Que hace, y por que:

1. `pines.py` desde sim/conexiones.py: el MISMO conexionado que dibuja los
   cables en el visor 3D y genera docs/conexiones.md. Si alguien cambia un
   cable ahi, el firmware se entera; nunca hay dos tablas de pines.
2. `config_placa.py` desde config/parametros.yaml: tiempos, angulos, umbrales
   y protocolo (secciones `firmware`, `tiempos_ms`, `protocolo`, `vehiculo`).
3. La logica COMPARTIDA con la simulacion (control/protocolo.py y, en el
   carro, control/vehiculo.py) se compila con mpy-cross, el compilador de
   MicroPython: si algo no es compatible con el ESP32, falla aqui en el PC y
   no en la placa. Todo se entrega como .mpy (ocupa menos RAM que compilar
   el .py en el ESP32); solo main.py y config_placa.py quedan como .py.
4. El driver del VL53L0X se descarga (su repositorio no tiene licencia, asi
   que no se guarda en este repo) y queda en cache en firmware/salida/.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FIRMWARE = RAIZ / "firmware"
SALIDA = FIRMWARE / "salida"
URL_VL53L0X = "https://raw.githubusercontent.com/uceeatz/VL53L0X/master/VL53L0X.py"

# Archivos de cada placa: (origen, nombre en la placa).
ARCHIVOS = {
    "fijo": [("firmware/fijo/main.py", "main.py"), ("firmware/fijo/estacion.py", "estacion.py"),
             ("firmware/fijo/hw.py", "hw.py"), ("firmware/comun/enlaces.py", "enlaces.py"),
             ("firmware/comun/distancia.py", "distancia.py"), ("control/protocolo.py", "protocolo.py")],
    "carro": [("firmware/carro/main.py", "main.py"), ("firmware/carro/logica.py", "logica.py"),
              ("firmware/carro/hw.py", "hw.py"), ("firmware/comun/enlaces.py", "enlaces.py"),
              ("firmware/comun/distancia.py", "distancia.py"), ("control/protocolo.py", "protocolo.py"),
              ("control/vehiculo.py", "vehiculo.py")],
}
SIN_COMPILAR = {"main.py"}
PLACA = {"fijo": "esp32_fijo", "carro": "esp32_carro"}


def pines(placa: str) -> dict[str, int]:
    """GPIO de senal de la placa: {"DRIVERS_M_STEP": 25, ...} (sim/conexiones.py)."""
    sys.path.insert(0, str(RAIZ))
    from sim.conexiones import CABLES

    out = {}
    for cable in CABLES:
        for h in cable["hilos"]:
            for a, b in ((h["de"], h["a"]), (h["a"], h["de"])):
                m = re.match(PLACA[placa] + r"\.G(\d+)\.S$", a)
                if m:
                    out[re.sub(r"[^A-Za-z0-9]+", "_", b).upper()] = int(m.group(1))
    return dict(sorted(out.items()))


def config_fijo(p: dict) -> dict:
    f = p["firmware"]
    return {
        "protocolo": p["protocolo"],
        "tiempos": p["tiempos_ms"],
        "cinta_monedas_mm": p["cinta_monedas"]["separacion_casilla_mm"],
        "cinta_vasos_mm": p["vasos"]["separacion_casilla_mm"],
        "micropasos": f["micropasos_firmware"], "mm_por_vuelta_cinta": f["mm_por_vuelta_cinta"],
        "carrusel_pasos_por_vuelta": f["carrusel_pasos_por_vuelta"], "carrusel_ms_por_paso": f["carrusel_ms_por_paso"],
        "servos": f["servos"], "cortina_umbral_mm": f["cortina_umbral_mm"], "activo_bajo": f["activo_bajo"],
        "telemetria_ms": f["telemetria_ms"],
    }


def config_carro(p: dict) -> tuple[dict, list, tuple]:
    """(CFG, LINEA, POSE_MUELLE). La linea de la pista va cada 2 puntos
    (~4 cm): la usa solo para llegar CERCA de ella; despues la siguen los
    infrarrojos. Asi ocupa ~1/2 de RAM."""
    sys.path.insert(0, str(RAIZ))
    from sim.geometria import geometria_completa
    from sim.pista import generar_linea_central

    f = p["firmware"]
    vehiculo = dict(p["vehiculo"])
    vehiculo["_muro_largo_mm"] = p["pista"]["obstaculo_largo_mm"]
    vehiculo["_muro_grueso_mm"] = p["pista"].get("obstaculo_grueso_mm", 30)
    s = geometria_completa(p)["pista"]["salida"]
    pose = (round(s["x"], 4), round(s["y"], 4), round(s["rumbo"], 4))
    linea = generar_linea_central(p["pista"]["tramos"], pose)
    puntos = [(round(q.x, 3), round(q.y, 3), round(q.rumbo, 3), round(q.s, 3)) for q in linea[::2]]
    if puntos[-1][3] != round(linea[-1].s, 3):
        q = linea[-1]
        puntos.append((round(q.x, 3), round(q.y, 3), round(q.rumbo, 3), round(q.s, 3)))
    cfg = {"protocolo": p["protocolo"], "vehiculo": vehiculo, "largo_linea_m": round(linea[-1].s, 4),
           "activo_bajo": f["activo_bajo"], "carro_v_max_m_s": f["carro_v_max_m_s"],
           "carro_ganancia_ki": f["carro_ganancia_ki"]}
    return cfg, puntos, pose


def _vl53l0x() -> Path:
    cache = SALIDA / "_descargas" / "vl53l0x.py"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL_VL53L0X, timeout=30) as r:
            cache.write_bytes(r.read())
    return cache


def compilar(origen: Path, destino: Path) -> None:
    """mpy-cross para el ESP32 (xtensawin). Error = no es MicroPython valido."""
    r = subprocess.run([sys.executable, "-m", "mpy_cross", "-march=xtensawin", "-o", str(destino), str(origen)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"{origen} no compila para MicroPython:\n{r.stderr}")


def preparar(placa: str, parametros: dict | None = None, *, descargar: bool = True) -> Path:
    if parametros is None:
        sys.path.insert(0, str(RAIZ))
        from app.configuracion import cargar_parametros

        parametros = cargar_parametros()
    destino = SALIDA / placa
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    fuentes = [(RAIZ / o, n) for o, n in ARCHIVOS[placa]]
    if descargar:
        fuentes.append((_vl53l0x(), "vl53l0x.py"))

    lineas = ["# GENERADO por firmware/preparar.py desde sim/conexiones.py: no editar a mano.\n"]
    lineas += [f"{k} = {v}\n" for k, v in pines(placa).items()]
    (destino / "pines.py").write_text("".join(lineas), encoding="utf-8")
    fuentes.append((destino / "pines.py", "pines.py"))

    encabezado = "# GENERADO por firmware/preparar.py desde config/parametros.yaml: no editar a mano.\n"
    if placa == "fijo":
        texto = encabezado + f"CFG = {config_fijo(parametros)!r}\n"
    else:
        cfg, linea, pose = config_carro(parametros)
        texto = encabezado + f"CFG = {cfg!r}\nLINEA = {linea!r}\nPOSE_MUELLE = {pose!r}\n"
    (destino / "config_placa.py").write_text(texto, encoding="utf-8")
    fuentes.append((destino / "config_placa.py", "config_placa.py"))

    for origen, nombre in fuentes:
        if nombre in SIN_COMPILAR:
            shutil.copy(origen, destino / nombre)
        else:
            compilar(origen, destino / nombre.replace(".py", ".mpy"))
    for generado in ("pines.py", "config_placa.py"):   # ya quedaron como .mpy
        (destino / generado).unlink()
    return destino


def main() -> None:
    placas = sys.argv[1:] or ["fijo", "carro"]
    for placa in placas:
        d = preparar(placa)
        print(f"{placa}: {d.relative_to(RAIZ)} -> " + ", ".join(sorted(x.name for x in d.iterdir())))


if __name__ == "__main__":
    main()
