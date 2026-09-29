"""Revision 2026-09-28: POST /api/orden del servidor del supervisor (app/servidor.py).
- Una orden mal formada se contesta 400 con el motivo y NO llega a la tabla `ordenes` (antes pasaba
  y tumbaba el supervisor al aplicarla).
- Sin CORS en las ordenes y solo con Content-Type: application/json: una pagina de otro sitio
  abierta en el mismo PC no puede mandarle ordenes a 127.0.0.1."""

import json
import socket
import urllib.error
import urllib.request

import pytest

from app import db, servidor


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def srv(tmp_path):
    ruta = tmp_path / "planta.db"
    db.conectar(ruta).close()
    puerto = _puerto_libre()
    s = servidor.arrancar(servidor.EstadoCompartido({}, ruta), puerto)
    yield f"http://127.0.0.1:{puerto}", ruta
    s.shutdown()


def _post(url, cuerpo: bytes, tipo="application/json"):
    pedido = urllib.request.Request(url + "/api/orden", data=cuerpo, method="POST",
                                    headers={"Content-Type": tipo} if tipo else {})
    try:
        with urllib.request.urlopen(pedido) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def _pendientes(ruta):
    c = db.conectar(ruta)
    try:
        return db.tomar_ordenes_pendientes(c)
    finally:
        c.close()


@pytest.mark.parametrize("orden", [
    {"cmd": "velocidad", "valor": "rapido"},
    {"cmd": "lote", "valor": "10.5"},
    {"cmd": "lote", "valor": 10.5},
    {"cmd": "lote", "valor": True},
    ["hola"],
    {"valor": 3},
    {"cmd": "colocar", "pieza": ["a"]},
])
def test_orden_mal_formada_da_400_y_no_llega_a_la_tabla(srv, orden):
    url, ruta = srv
    codigo, _, cuerpo = _post(url, json.dumps(orden).encode())
    assert codigo == 400 and json.loads(cuerpo)["error"]
    assert _pendientes(ruta) == []


def test_orden_buena_pasa_sin_permiso_de_cors(srv):
    url, ruta = srv
    codigo, cabeceras, _ = _post(url, json.dumps({"cmd": "lote", "valor": 8}).encode())
    assert codigo == 200 and "Access-Control-Allow-Origin" not in cabeceras
    assert _pendientes(ruta) == [{"cmd": "lote", "valor": 8}]


@pytest.mark.parametrize("tipo", ["text/plain", "application/x-www-form-urlencoded", None])
def test_sin_content_type_json_no_se_acepta(srv, tipo):
    """Lo que un <form> o un fetch "simple" de otro sitio puede mandar sin pedir permiso."""
    url, ruta = srv
    codigo, _, _ = _post(url, b'{"cmd":"paro"}', tipo)
    assert codigo == 415 and _pendientes(ruta) == []


def test_el_preflight_no_da_permiso_y_las_lecturas_si(srv):
    url, _ = srv
    pedido = urllib.request.Request(url + "/api/orden", method="OPTIONS",
                                    headers={"Origin": "https://otro-sitio.example", "Access-Control-Request-Method": "POST"})
    with urllib.request.urlopen(pedido) as r:
        assert "Access-Control-Allow-Origin" not in r.headers
    # El visor portable (file://) sigue pudiendo LEER el estado.
    with urllib.request.urlopen(url + "/api/estado") as r:
        assert r.headers["Access-Control-Allow-Origin"] == "*"
