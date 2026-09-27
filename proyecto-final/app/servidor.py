"""Servidor HTTP del supervisor: visor 3D + estado en vivo.

Corre en un hilo aparte DENTRO del proceso supervisor (no en Streamlit),
con la libreria estandar de Python (`http.server`), sin dependencias nuevas.

Rutas:
    GET  /                  el visor 3D (app/visor3d/index.html)
    GET  /<archivo>         archivos estaticos del visor (js, vendor/...)
    GET  /api/estado        ultimo estado de la planta (lo mismo que la
                            telemetria 'tel' de SQLite, pero en memoria, para
                            que el 3D pueda preguntar 10 veces por segundo sin
                            tocar la base de datos)
    GET  /api/geometria     geometria completa + catalogo de sensores
                            (sim/geometria.py)
    GET  /api/pasos         el paso a paso (docs/paso-a-paso.yaml), releido en
                            cada consulta para que una revision se vea al tiro
    GET  /api/asistente     la conversacion con el asistente (fase 7) y que
                            paso con sus ordenes, para mostrarla en el visor
                            (solo lectura: se le escribe desde el dashboard)
    POST /api/orden         deja una orden en la tabla `ordenes` (mismo
                            camino que los botones del dashboard)

Por que un servidor y no solo SQLite: el visor 3D es JavaScript en el
navegador y no puede abrir un archivo SQLite; necesita una URL. Y este es el
mismo punto de entrada que va a usar el puente con los dos ESP32 (fase 8):
el ESP32 fijo por serial y, a traves de el por ESP-NOW, el del carro.
"""

from __future__ import annotations

import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

from app import db

DIRECTORIO_VISOR = Path(__file__).resolve().parent / "visor3d"
RUTA_PASOS = Path(__file__).resolve().parent.parent / "docs" / "paso-a-paso.yaml"

# Windows a veces no conoce el tipo de los .js y los sirve como text/plain,
# y el navegador se niega a ejecutar un modulo ES asi.
mimetypes.add_type("text/javascript", ".js")


class EstadoCompartido:
    """El supervisor escribe, los hilos del servidor leen. Un candado basta:
    son lecturas y escrituras de un solo diccionario ya serializado."""

    def __init__(self, geometria: dict, ruta_bd: Path):
        self._candado = threading.Lock()
        self._estado_json = b"{}"
        self.geometria_json = json.dumps(geometria, ensure_ascii=False).encode("utf-8")
        self.ruta_bd = ruta_bd

    def publicar(self, estado: dict) -> None:
        datos = json.dumps(estado, ensure_ascii=False).encode("utf-8")
        with self._candado:
            self._estado_json = datos

    def estado_json(self) -> bytes:
        with self._candado:
            return self._estado_json


def _asistente_json(ruta_bd: Path) -> bytes:
    """Ultimos mensajes del asistente y las respuestas a sus ordenes."""
    conexion = db.conectar_lectura(ruta_bd)
    try:
        mensajes = [dict(f) for f in conexion.execute(
            "SELECT ts, rol, texto, modo, acciones FROM asistente ORDER BY id DESC LIMIT 16").fetchall()][::-1]
        respuestas = [json.loads(f["payload"]) | {"ts": f["ts"]} for f in conexion.execute(
            "SELECT ts, payload FROM eventos WHERE tipo = 'respuesta' AND payload LIKE '%\"asistente\"%' "
            "ORDER BY id DESC LIMIT 6").fetchall()]
        f = conexion.execute("SELECT proveedor, pregunta, desde FROM asistente_pensando WHERE id = 1").fetchone()
        pensando = dict(f) if f and f["proveedor"] else None
    finally:
        conexion.close()
    for m in mensajes:
        m["acciones"] = json.loads(m["acciones"] or "[]")
    return json.dumps({"mensajes": mensajes, "respuestas": respuestas, "pensando": pensando},
                      ensure_ascii=False).encode("utf-8")


def _crear_manejador(compartido: EstadoCompartido):
    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, *args):  # sin una linea de log por cada consulta
            pass

        def _responder(self, codigo: int, cuerpo: bytes, tipo: str) -> None:
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(cuerpo)

        def do_GET(self):
            ruta = self.path.split("?", 1)[0]
            if ruta == "/api/estado":
                return self._responder(200, compartido.estado_json(), "application/json")
            if ruta == "/api/geometria":
                return self._responder(200, compartido.geometria_json, "application/json")
            if ruta == "/api/pasos":
                with open(RUTA_PASOS, encoding="utf-8") as archivo:
                    pasos = yaml.safe_load(archivo)["pasos"]
                return self._responder(200, json.dumps(pasos, ensure_ascii=False).encode("utf-8"), "application/json")

            if ruta == "/api/asistente":
                return self._responder(200, _asistente_json(compartido.ruta_bd), "application/json")

            relativa = "index.html" if ruta in ("/", "") else ruta.lstrip("/")
            archivo = (DIRECTORIO_VISOR / relativa).resolve()
            # Nada fuera de la carpeta del visor (evita ../../ en la URL).
            if DIRECTORIO_VISOR not in archivo.parents and archivo != DIRECTORIO_VISOR / "index.html":
                return self._responder(404, b"no encontrado", "text/plain")
            if not archivo.is_file():
                return self._responder(404, b"no encontrado", "text/plain")
            tipo = mimetypes.guess_type(archivo.name)[0] or "application/octet-stream"
            return self._responder(200, archivo.read_bytes(), tipo)

        def do_POST(self):
            if self.path != "/api/orden":
                return self._responder(404, b"no encontrado", "text/plain")
            largo = int(self.headers.get("Content-Length", 0))
            try:
                orden = json.loads(self.rfile.read(largo))
                conexion = db.conectar_lectura(compartido.ruta_bd)
                try:
                    db.insertar_orden(conexion, orden)
                finally:
                    conexion.close()
            except (ValueError, OSError) as error:
                return self._responder(400, str(error).encode(), "text/plain")
            return self._responder(200, b'{"ok":true}', "application/json")

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    return Manejador


def arrancar(compartido: EstadoCompartido, puerto: int) -> ThreadingHTTPServer | None:
    """Arranca el servidor en un hilo daemon (muere con el supervisor). Si
    el puerto esta ocupado, el supervisor sigue funcionando sin 3D en vez de
    caerse."""
    try:
        # Solo esta maquina: nadie en la red del salon puede mandarle
        # ordenes a la linea por POST /api/orden.
        servidor = ThreadingHTTPServer(("127.0.0.1", puerto), _crear_manejador(compartido))
    except OSError as error:
        print(f"No se pudo abrir el puerto {puerto} para el visor 3D ({error}); sigo sin el.")
        return None
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor
