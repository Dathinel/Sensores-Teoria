"""Charla de prueba con el asistente, por consola (la usa la app de la práctica,
app-practica/index.html, con una caja de texto). Sin clave y sin internet: responde
el interprete de reglas (app/asistente.py, `responder_local`), con las cifras de la
ultima corrida guardada en datos/planta.db.

    python -m app.charla            # reglas (siempre funciona)
    python -m app.charla --ollama   # el modelo local, si Ollama esta corriendo

Trabaja sobre una COPIA de la base: no toca la corrida ni la conversacion del
dashboard, y las ordenes ("avanza 20 cm") se muestran pero NO se mandan a la linea
(para eso esta la pestaña Asistente del dashboard, con la simulacion corriendo).
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from app import asistente, configuracion, db


def _copia_de_la_base(carpeta: Path) -> sqlite3.Connection:
    """Copia de datos/planta.db en una carpeta temporal (con la API de respaldo de
    SQLite: sirve aunque la simulacion este escribiendo). Si no hay base, una vacia."""
    destino = carpeta / "planta.db"
    origen = configuracion.ruta_bd()
    copia = db.conectar(destino)
    if origen.exists():
        fuente = sqlite3.connect(f"file:{origen}?mode=ro", uri=True)
        try:
            fuente.backup(copia)
        finally:
            fuente.close()
    return copia


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    usar = "ollama" if "--ollama" in sys.argv else "reglas"
    # Junto a la base (en D:, no en el temporal de C:); git ignora los *.db. Si una charla anterior se
    # cerro a la fuerza (Detener mata el proceso y no llega al finally), su copia se borra ahora.
    for vieja in configuracion.ruta_bd().parent.glob("charla-*"):
        shutil.rmtree(vieja, ignore_errors=True)
    carpeta = Path(tempfile.mkdtemp(prefix="charla-", dir=configuracion.ruta_bd().parent))
    conexion = _copia_de_la_base(carpeta)
    try:
        _charlar(conexion, usar)
    finally:
        conexion.close()
        shutil.rmtree(carpeta, ignore_errors=True)   # la copia se borra al terminar


def _charlar(conexion: sqlite3.Connection, usar: str) -> None:
    print(f"Asistente listo (responde: {'modelo local de Ollama' if usar == 'ollama' else 'reglas, sin internet'}).")
    print("Escriba una pregunta o una orden y pulse Enter. 'salir' para terminar.")
    for linea in sys.stdin:
        frase = linea.strip()
        if not frase:
            continue
        if frase.lower() in ("salir", "chao", "adios", "adiós"):
            break
        r = asistente.atender(frase, conexion, usar=usar, usar_deepseek=(usar != "reglas"))
        print(r.texto)
        if r.ordenes:
            print("  (es una ORDEN: aquí es solo una prueba y NO se manda a la línea; en la pestaña "
                  "Asistente del dashboard, con la simulación corriendo, sí se ejecuta)")
        if r.aviso:
            print(f"  aviso: {r.aviso}")
        print(f"  [respondió: {r.modo}]")
    print("Fin de la charla.")


if __name__ == "__main__":
    main()
