"""Puerto del visor 3D (app/puertos.py): configurable y, si otro programa lo tiene, el siguiente
libre. Con sockets reales en 127.0.0.1 (sin red)."""

import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app import puertos, servidor


def _puerto_con_siguiente_libre() -> int:
    """Un puerto libre cuyo siguiente tambien esta libre."""
    for _ in range(50):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            p = s.getsockname()[1]
        if p < 65000 and puertos.libre(p) and puertos.libre(p + 1):
            return p
    pytest.skip("no se encontraron dos puertos libres seguidos")


class _OtroPrograma(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        cuerpo = b"<html>otro programa</html>"
        self.send_response(200)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)


@pytest.fixture
def otro_programa():
    p = _puerto_con_siguiente_libre()
    srv = ThreadingHTTPServer(("127.0.0.1", p), _OtroPrograma)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield p
    srv.shutdown()
    srv.server_close()


def test_la_variable_de_entorno_manda_sobre_la_configuracion(monkeypatch):
    monkeypatch.setenv(puertos.VARIABLE, "9123")
    assert puertos.puerto_pedido({"supervisor": {"puerto_http": 8765}}) == 9123
    monkeypatch.setenv(puertos.VARIABLE, "no-es-numero")
    assert puertos.puerto_pedido({"supervisor": {"puerto_http": 8765}}) == 8765


def test_si_otro_programa_tiene_el_puerto_usa_el_siguiente_y_lo_dice(otro_programa):
    puerto, como, ocupados = puertos.elegir(otro_programa)
    assert (puerto, como, ocupados) == (otro_programa + 1, "libre", [otro_programa])
    texto = puertos.mensaje(otro_programa, puerto, como, ocupados)
    assert str(otro_programa) in texto and f"http://127.0.0.1:{puerto}/" in texto
    assert not puertos.es_nuestro(otro_programa)


def test_una_corrida_de_este_proyecto_se_reutiliza(tmp_path):
    p = _puerto_con_siguiente_libre()
    compartido = servidor.EstadoCompartido({"cinta_monedas": {}}, tmp_path / "x.db")
    srv = servidor.arrancar(compartido, p)
    try:
        assert puertos.elegir(p) == (p, "nuestro", [])
        # El supervisor necesita ABRIR el puerto: para el, la corrida vieja tambien ocupa.
        assert puertos.elegir(p, reutilizar=False)[:2] == (p + 1, "libre")
    finally:
        srv.shutdown()
        srv.server_close()


def test_sin_conflicto_no_hay_mensaje():
    p = _puerto_con_siguiente_libre()
    assert puertos.elegir(p) == (p, "libre", [])
    assert puertos.mensaje(p, p, "libre", []) == ""
