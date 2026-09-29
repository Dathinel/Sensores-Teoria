"""Costos en Colombia (config/precios.yaml -> docs/costos.md), con la estructura 3D contada."""

import math

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
    # Los subsistemas de las filas son los del orden de la tabla (ninguno se pierde del resumen).
    assert {f["subsistema"] for f in fs} <= set(costos.ORDEN_SUBSISTEMAS)


def test_el_documento_trae_total_y_ahorros_ordenados():
    md = costos.generar_md()
    assert costos.pesos(costos.total()) in md and "Dónde abaratar" in md
    a = costos.ahorros()
    assert [x["ahorro"] for x in a] == sorted((x["ahorro"] for x in a), reverse=True)
    assert all(x["riesgo"] in ("bajo", "medio", "alto") for x in a)


# ------------------------------------------------------------------ estructura 3D


def test_cada_pieza_impresa_tiene_costo_y_datos_completos():
    datos = costos.cargar()
    ids = [p["id"] for p in datos["estructura_3d"]["piezas_impresas"]]
    assert len(ids) == len(set(ids)), "id de pieza impresa repetido"
    tipos = set(datos["estructura_3d"]["tornilleria"]["tipos"])
    for p in costos.piezas_impresas(datos):
        assert p["subsistema"] in costos.ORDEN_SUBSISTEMAS, p["id"]
        assert p["volumen_cm3"] > 0 and p["gramos"] > 0 and p["horas"] > 0, p["id"]
        assert p["costo"] > 0 and p["costo_filamento"] > 0 and p["costo_energia"] > 0, p["id"]
        assert len(p["medidas_mm"]) == 3 and p["origen"] in ("malla", "estimado"), p["id"]
        # Lo estimado dice cómo se calculó.
        if p["origen"] == "estimado":
            assert p.get("como"), p["id"]
        assert set(p.get("tornillos") or {}) <= tipos, p["id"]
        # El volumen de material no puede ser mayor que la caja que ocupa la pieza.
        caja_cm3 = math.prod(p["medidas_mm"]) / 1000
        assert p["volumen_cm3"] <= caja_cm3 * 1.01, p["id"]


def test_la_formula_de_una_pieza_impresa():
    datos = costos.cargar()
    imp = datos["estructura_3d"]["impresion"]
    maciza = {"volumen_cm3": 10.0, "maciza": True}
    gruesa = {"volumen_cm3": 10.0, "maciza": False}
    assert costos.factor_llenado(maciza, imp) == 1.0
    assert math.isclose(costos.factor_llenado(gruesa, imp), imp["paredes"] + (1 - imp["paredes"]) * imp["relleno"])
    p = next(x for x in costos.piezas_impresas(datos) if x["maciza"])
    g = p["volumen_cm3"] * imp["densidad_g_cm3"] * (1 + imp["desperdicio"])
    assert math.isclose(p["gramos"], g)
    horas = g / imp["gramos_por_hora"]
    assert math.isclose(p["costo"], g * imp["precio_kg"] / 1000 + horas * imp["kwh_por_hora"] * imp["tarifa_kwh"])


def test_cada_pieza_impresa_cuenta_una_sola_vez_en_el_total():
    """La suma de las filas de piezas impresas (componentes `calculado: impresas` + "Otras piezas
    impresas" por subsistema) es la suma del costo de todas las piezas: ninguna se pierde ni se repite."""
    datos = costos.cargar()
    fs = costos.filas(datos)
    calculadas = {i for i, d in datos["items"].items() if d.get("calculado") == "impresas"}
    filas_impresas = sum(f["subtotal"] for f in fs if f["id"].startswith("impresas_") or f["id"] in calculadas)
    piezas = sum(p["costo_total"] for p in costos.piezas_impresas(datos))
    assert abs(filas_impresas - piezas) <= len(calculadas) + len(costos.ORDEN_SUBSISTEMAS)   # redondeo a pesos
    # Cada componente impreso del catálogo tiene al menos una pieza y un precio mayor que 0.
    for i in calculadas:
        f = next(x for x in fs if x["id"] == i)
        assert f["precio"] > 0, i


def test_despiece_del_perfil():
    datos = costos.cargar()
    per = datos["estructura_3d"]["perfil"]
    d = costos.despiece_perfil(datos)
    tramos = [t["largo_mm"] for t in per["tramos"] for _ in range(t.get("cantidad", 1))]
    # Todos los tramos quedan en alguna barra, exactamente una vez.
    assert sorted(x for b in d["barras"] for x in b) == sorted(tramos)
    # Ninguna barra se pasa de 1 m contando el corte de cada tramo.
    for b in d["barras"]:
        assert sum(b) + per["corte_mm"] * len(b) <= per["largo_barra_mm"]
    # No se compran barras de más que el mínimo teórico + 1.
    minimo = math.ceil(sum(t + per["corte_mm"] for t in tramos) / per["largo_barra_mm"])
    assert minimo <= d["n_barras"] <= minimo + 1
    # La fila del perfil compra exactamente esas barras.
    f = next(x for x in costos.filas(datos) if x["id"] == "estructura")
    assert f["cantidad"] == d["n_barras"]


def test_tornilleria_contada():
    datos = costos.cargar()
    t = costos.conteo_tornilleria(datos)
    # En el modelo hay 22 escuadras (+2 de los postes de las cámaras) y 15 pies niveladores.
    assert t["escuadra_2020"]["contados"] == 24
    assert t["pie_nivelador"]["contados"] == 15
    # Cada escuadra lleva 2 tornillos M5 x 8 con su tuerca en T.
    assert t["m5x8"]["contados"] == 2 * t["escuadra_2020"]["contados"]
    for d in t.values():
        if d["contados"]:
            assert d["comprar"] >= d["contados"] and d["subtotal"] == d["comprar"] * d["precio"] > 0
    # Por zona suma lo mismo que el total.
    por_zona = costos.tornillos_por_zona(datos)
    for tipo, d in t.items():
        assert sum(z.get(tipo, 0) for z in por_zona.values()) == d["contados"]


def test_la_estructura_3d_esta_dentro_del_total_y_en_el_documento():
    c = costos.costo_estructura_3d()
    assert c["total"] == c["impresas"] + c["perfil"] + c["tornilleria"]
    assert 0 < c["total"] < costos.total()
    md = costos.generar_md()
    for texto in ("## Estructura 3D", "### Piezas impresas", "### Perfil 2020 por tramo", "Despiece",
                  "### Tornillería", costos.pesos(c["total"])):
        assert texto in md, texto
