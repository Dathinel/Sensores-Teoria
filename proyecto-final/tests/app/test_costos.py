"""Costos en Colombia (config/precios.yaml -> docs/costos.md)."""

from app import costos
from sim.catalogos import CATALOGO_SENSORES, COMPONENTES


def test_todo_lo_del_catalogo_tiene_precio():
    datos = costos.cargar()
    ids = set(datos["items"])
    faltan = [c["id"] for c in COMPONENTES + CATALOGO_SENSORES if c["id"] not in ids]
    assert faltan == []
    sobran = ids - {c["id"] for c in COMPONENTES + CATALOGO_SENSORES}
    assert not sobran


def test_el_total_es_la_suma_de_precio_por_cantidad():
    fs = costos.filas()
    assert costos.total() == sum(f["precio"] * f["cantidad"] for f in fs)
    assert sum(costos.por_subsistema().values()) == costos.total()
    assert all(f["fuente"] in ("tienda", "estimado") for f in fs)


def test_el_documento_trae_total_y_ahorros_ordenados():
    md = costos.generar_md()
    assert costos.pesos(costos.total()) in md and "Dónde abaratar" in md
    a = costos.ahorros()
    assert [x["ahorro"] for x in a] == sorted((x["ahorro"] for x in a), reverse=True)
    assert all(x["riesgo"] in ("bajo", "medio", "alto") for x in a)
