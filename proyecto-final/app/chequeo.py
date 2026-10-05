"""Chequeo previo a la sustentación (usuario, 2026-09-27: "guardar todo lo necesario para la
ejecución bien del proyecto"). Revisa, SIN cambiar nada, todo lo que puede fallar el día de la
presentación y dice cómo arreglar cada cosa:

    python -m app.chequeo            # todo (tarda unos segundos: prueba internet y DeepSeek)
    python -m app.chequeo --rapido   # sin llamadas por internet

Cada línea sale como  ✓ bien,  ! aviso (funciona, pero conviene mirarlo)  o  ✗ falla (arreglar antes).
Termina con código 1 si hay alguna ✗ (sirve para scripts).
"""

from __future__ import annotations

import importlib.metadata
import os
import platform
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BIEN, AVISO, FALLA = "✓", "!", "✗"


def _version_fija() -> tuple[str, dict[str, str]]:
    """(versión de Python, {paquete: versión}) de requirements-lock.txt."""
    lock = RAIZ / "requirements-lock.txt"
    python, paquetes = "", {}
    if not lock.exists():
        return python, paquetes
    for linea in lock.read_text(encoding="utf-8").splitlines():
        if linea.startswith("#") and "Python " in linea:
            python = linea.split("Python ", 1)[1].split(",")[0].strip()
        elif "==" in linea and not linea.startswith("#"):
            nombre, version = linea.split("==", 1)
            paquetes[nombre.strip().lower()] = version.strip()
    return python, paquetes


def python_y_paquetes() -> list[tuple[str, str, str]]:
    esperado, paquetes = _version_fija()
    out = []
    actual = platform.python_version()
    if not esperado:
        out.append((FALLA, "requirements-lock.txt", "No existe: sin él no se sabe con qué versiones se probó."))
    elif actual != esperado:
        out.append((AVISO, f"Python {actual}", f"Se probó con {esperado}. Puede andar igual; si algo falla, usar {esperado}."))
    else:
        out.append((BIEN, f"Python {actual}", "igual al de las pruebas"))
    faltan, distintas = [], []
    for nombre, version in paquetes.items():
        try:
            instalada = importlib.metadata.version(nombre)
        except importlib.metadata.PackageNotFoundError:
            faltan.append(nombre)
            continue
        if instalada != version:
            distintas.append(f"{nombre} {instalada} (se probó {version})")
    if faltan:
        out.append((FALLA, f"{len(faltan)} paquetes sin instalar", ", ".join(faltan[:8])
                    + (" …" if len(faltan) > 8 else "") + " → instalar.bat (o pip install -r requirements-lock.txt)"))
    elif paquetes:
        out.append((BIEN, f"{len(paquetes)} paquetes instalados", "todos los de requirements-lock.txt"))
    if distintas:
        out.append((AVISO, f"{len(distintas)} con otra versión", "; ".join(distintas[:5])))
    return out


def puertos() -> list[tuple[str, str, str]]:
    """El del visor 3D (8765 o PLANTA_PUERTO_VISOR) y el del dashboard (8501). Si los tiene otro
    programa ya no es una falla: app.lanzar usa el siguiente libre y lo dice (app/puertos.py)."""
    from app import puertos as p

    out = []
    pedido = p.puerto_pedido()
    puerto, como, ocupados = p.elegir(pedido)
    que = f"Puerto {pedido} (visor 3D)"
    if como == "nuestro":
        out.append((BIEN, f"Puerto {puerto} (visor 3D)", "ya lo usa esta app (la simulación está corriendo)"
                    + (f"; el {pedido} lo tiene otro programa" if ocupados else "")))
    elif como == "ninguno":
        out.append((FALLA, que, f"del {pedido} al {pedido + p.INTENTOS} todos ocupados por otros programas: "
                    f"cerrar alguno o elegir otro con la variable {p.VARIABLE}"))
    elif ocupados:
        out.append((AVISO, que, f"lo ocupa OTRO programa: visor.bat usará solo el {puerto} (y lo dice en su "
                    f"ventana); para fijar uno, la variable {p.VARIABLE} o --puerto-visor"))
    else:
        out.append((BIEN, que, "libre: visor.bat lo va a usar"))
    anotado = p.leer().get("dashboard") if como == "nuestro" else None
    if anotado:
        out.append((BIEN, f"Puerto {anotado} (dashboard)", "lo usa la corrida en marcha"))
    else:
        dash, ocupados_dash = p.primer_libre(8501)
        if not ocupados_dash:
            out.append((BIEN, "Puerto 8501 (dashboard)", "libre: visor.bat lo va a usar"))
        elif dash != 8501:
            out.append((AVISO, "Puerto 8501 (dashboard)", f"ocupado: el dashboard usará el {dash}"))
        else:
            out.append((FALLA, "Puerto 8501 (dashboard)", "ocupado, y los siguientes también"))
    return out


def asistente(rapido: bool) -> list[tuple[str, str, str]]:
    from app import asistente as a

    out = []
    local = a.cliente_local()
    if local is None:
        out.append((FALLA, "Modelo local (Ollama)", "no responde: abrir Ollama y `ollama pull qwen2.5:3b` (ver README)"))
    elif a.MODELO_LOCAL != "qwen2.5-proyecto":
        out.append((AVISO, "Modelo local (Ollama)", f"usa {a.MODELO_LOCAL}: para respuestas más completas, "
                    "`python -m app.asistente --preparar-local`"))
    else:
        out.append((BIEN, "Modelo local (Ollama)", "qwen2.5-proyecto listo. Hacerle una pregunta de calentamiento antes"))
    cache = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    if (cache / f"models--Systran--faster-whisper-{a.MODELO_VOZ}").exists():
        out.append((BIEN, "Voz sin internet (Whisper)", f"modelo '{a.MODELO_VOZ}' descargado"))
    else:
        out.append((FALLA, "Voz sin internet (Whisper)", "falta el modelo: `python -m app.asistente --preparar-voz` (con internet)"))
    try:
        import pyttsx3

        motor = pyttsx3.init()
        voces = [v.name for v in motor.getProperty("voices")
                 if any(n in v.name.lower() for n in ("spanish", "helena", "sabina", "laura", "pablo", "raul"))]
        out.append((BIEN, "Voz de Windows en español", voces[0]) if voces
                   else (AVISO, "Voz de Windows en español", "no hay: Configuración > Hora e idioma > Voz > agregar español"))
    except Exception as error:
        out.append((AVISO, "Voz de Windows", f"no se pudo revisar ({type(error).__name__})"))
    if rapido:
        return out
    internet = a.hay_internet()
    out.append((BIEN, "Internet", "hay: responde DeepSeek (si la clave sirve)") if internet
               else (AVISO, "Internet", "no hay: todo sigue funcionando; el asistente usa el modelo local"))
    cliente = a.cliente_deepseek()
    if cliente is None:
        out.append((AVISO, "Clave de DeepSeek", "no hay (.env): responde el modelo local"))
    elif internet:
        try:
            cliente.with_options(timeout=10, max_retries=0).models.list()
            out.append((BIEN, "Clave de DeepSeek", "válida"))
        except Exception as error:
            out.append((AVISO, "Clave de DeepSeek", f"rechazada ({type(error).__name__}): poner una válida en .env; "
                        "mientras, responde el modelo local"))
    try:
        os.environ.setdefault("KERAS_BACKEND", "torch")
        import keras  # noqa: F401  (Keras 3 sobre torch: entrenar el clasificador sin TensorFlow)

        out.append((BIEN, "Entrenamiento (Keras + torch)", f"listo, motor {keras.backend.backend()}"))
    except Exception as error:
        out.append((AVISO, "Entrenamiento (Keras + torch)", f"no está ({type(error).__name__}): solo hace falta "
                    "para entrenar la visión; instalar con requirements-lock.txt"))
    return out


def hardware() -> list[tuple[str, str, str]]:
    from serial.tools import list_ports

    # CP210x (Silicon Labs) y CH340 (WCH): los puentes USB de los ESP32 DevKit.
    placas = [f"{p.device} ({p.description})" for p in list_ports.comports() if p.vid in (0x10C4, 0x1A86)]
    out = [(BIEN, "ESP32 por USB", ", ".join(placas)) if placas else
           (AVISO, "ESP32 por USB", "ninguno conectado: en simulación no hace falta (hardware.backend: sim)")]
    driver = RAIZ / "firmware" / "salida" / "_descargas" / "vl53l0x.py"
    out.append((BIEN, "Driver del VL53L0X", "descargado: el firmware se arma sin internet") if driver.exists()
               else (AVISO, "Driver del VL53L0X", "no está: armar el firmware una vez CON internet "
                     "(`python -m firmware.preparar`)"))
    return out


def archivos() -> list[tuple[str, str, str]]:
    out = []
    bd = RAIZ / "datos" / "planta.db"
    if bd.exists():
        mb = sum(f.stat().st_size for f in bd.parent.glob("planta.db*")) / 1e6
        out.append((AVISO if mb > 50 else BIEN, "Base de datos", f"{mb:.1f} MB"
                    + (": empezar una corrida nueva antes de presentar" if mb > 50 else "")))
    else:
        out.append((BIEN, "Base de datos", "se crea sola al arrancar"))
    portable = RAIZ / "visor-portable.html"
    visor = RAIZ / "app" / "visor3d"
    fuentes = [visor / "index.html"] + list(visor.glob("*.js")) + list(visor.glob("*.css")) + \
        list((visor / "piezas").glob("*.js")) + list((visor / "demo").glob("*.json"))
    if not portable.exists():
        out.append((AVISO, "visor-portable.html", "no está: lo arma visor.bat (o `python -m app.portable`)"))
    elif portable.stat().st_mtime < max(f.stat().st_mtime for f in fuentes):
        out.append((AVISO, "visor-portable.html", "más viejo que el visor: visor.bat lo rehace solo"))
    else:
        out.append((BIEN, "visor-portable.html", "al día"))
    if not (RAIZ / "entorno" / "Scripts" / "python.exe").exists() and os.name == "nt":
        out.append((FALLA, "entorno/", "no existe: correr instalar.bat"))
    return out


def revisar(rapido: bool = False) -> list[tuple[str, str, str]]:
    filas = []
    for grupo in (python_y_paquetes, puertos, lambda: asistente(rapido), hardware, archivos):
        try:
            filas += grupo()
        except Exception as error:  # un grupo que falla no tapa a los demas
            filas.append((FALLA, getattr(grupo, "__name__", "chequeo"), f"{type(error).__name__}: {error}"))
    return filas


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    filas = revisar(rapido="--rapido" in sys.argv)
    ancho = max(len(f[1]) for f in filas)
    print("Chequeo previo a la sustentación\n")
    for marca, que, detalle in filas:
        print(f"  {marca}  {que.ljust(ancho)}  {detalle}")
    fallas = sum(1 for f in filas if f[0] == FALLA)
    avisos = sum(1 for f in filas if f[0] == AVISO)
    print(f"\n{fallas} fallas, {avisos} avisos." + (" Listo para presentar." if not fallas else ""))
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
