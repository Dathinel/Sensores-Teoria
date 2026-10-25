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


def test_maqueta_impresa_desde_su_exportador():
    """La estructura de la planta es la maqueta impresa (2026-10-24): sus gramos y horas son los de
    maqueta_impresa/piezas.json y el costo es gramos x PLA + energia, con el desperdicio."""
    import json

    datos = costos.cargar()
    imp = datos["estructura_3d"]["impresion"]
    pj = json.loads((costos.RAIZ / datos["estructura_3d"]["maqueta"]["archivo"]).read_text(encoding="utf-8"))
    mq = costos.maqueta(datos)
    assert math.isclose(sum(g["gramos"] for g in mq), pj["total_gramos"], abs_tol=1)
    assert math.isclose(sum(g["horas"] for g in mq), pj["total_horas"], abs_tol=0.1)
    k = 1 + imp["desperdicio"]
    for g in mq:
        assert g["subsistema"] in costos.ORDEN_SUBSISTEMAS
        assert math.isclose(g["costo"], g["gramos"] * k * imp["precio_kg"] / 1000
                            + g["horas"] * k * imp["kwh_por_hora"] * imp["tarifa_kwh"])
    # Cada grupo esta en UNA fila del total (la de la estructura o la "Maqueta impresa" de su subsistema).
    fs = costos.filas(datos)
    filas_mq = sum(f["subtotal"] for f in fs if f["id"] == "estructura" or f["id"].startswith("maqueta_"))
    assert abs(filas_mq - sum(g["costo"] for g in mq)) <= len(costos.ORDEN_SUBSISTEMAS)
    # Ya no se compra perfil, escuadras, pies, acrilico ni MDF.
    assert "perfil" not in datos["estructura_3d"] and "base" not in (datos.get("extras") or {})
    assert {"escuadra_2020", "pie_nivelador", "tuerca_t"}.isdisjoint(datos["estructura_3d"]["tornilleria"]["tipos"])
    for i in ("almacen", "tubo_tapas", "canaletas_rechazo", "bandeja_rechazo_vasos", "canal_e7", "muelle_carga"):
        assert datos["items"][i]["precio"] == 0 and datos["items"][i]["incluido"] == "maqueta", i


def test_ahorros_aplicados_son_la_diferencia_con_el_total_anterior():
    datos = costos.cargar()
    aplicados = costos.ahorros_aplicados(datos)
    assert sum(a["ahorro"] for a in aplicados) == datos["total_antes_de_ahorros"] - costos.total(datos)
    assert not {a["id"] for a in costos.ahorros(datos)} & {a["id"] for a in aplicados}
    # Lo quitado ya no se compra.
    assert {"bornera_x2", "entrada_red", "optoacopladores", "reparto_i2c", "hub_usb", "canaletas_caja"}.isdisjoint(datos["items"])


def test_tornilleria_contada():
    datos = costos.cargar()
    t = costos.conteo_tornilleria(datos)
    # La maqueta va remachada: solo los NEMA 17 (4 M3 c/u) y los 4 KFL08 (2 M5 con tuerca c/u).
    assert t["m5x16"]["contados"] == t["tuerca_m5"]["contados"] == 8
    for d in t.values():
        if d["contados"]:
            assert d["comprar"] >= d["contados"] and d["subtotal"] == d["comprar"] * d["precio"] > 0
    # Por zona suma lo mismo que el total.
    por_zona = costos.tornillos_por_zona(datos)
    for tipo, d in t.items():
        assert sum(z.get(tipo, 0) for z in por_zona.values()) == d["contados"]


def test_la_estructura_3d_esta_dentro_del_total_y_en_el_documento():
    c = costos.costo_estructura_3d()
    assert c["total"] == c["impresas"] + c["maqueta"] + c["tornilleria"]
    assert 0 < c["total"] < costos.total()
    md = costos.generar_md()
    for texto in ("## Estructura 3D", "### Maqueta impresa por grupo", "### Piezas impresas sueltas", "### Tornillería",
                  "## Ahorros ya aplicados", costos.pesos(c["total"])):
        assert texto in md, texto
