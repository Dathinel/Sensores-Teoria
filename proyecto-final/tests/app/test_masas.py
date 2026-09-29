"""Peso del montaje (config/masas.yaml + precios.yaml -> docs/peso.md) y comprobaciones de par."""

import math

from app import costos, masas
from sim.catalogos import CATALOGO_SENSORES, COMPONENTES


def test_todo_lo_del_catalogo_tiene_masa_o_es_impreso():
    datos = masas.cargar()
    ids = set(datos["componentes"])
    catalogo = {c["id"] for c in COMPONENTES + CATALOGO_SENSORES}
    assert catalogo - ids == set(), "componentes del catálogo sin masa"
    assert ids - catalogo == set(), "masas de componentes que no existen"
    for id_, d in datos["componentes"].items():
        assert d["zona"] in masas.ORDEN_ZONAS, id_
        if not d.get("impreso"):
            assert d["masa_g"] >= 0 and d["fuente"] in ("hoja_de_datos", "estimado"), id_
    # Lo marcado como impreso de verdad tiene piezas en precios.yaml (si no, pesaría 0 sin avisar).
    piezas = {p.get("componente") for p in costos.cargar()["estructura_3d"]["piezas_impresas"]}
    for id_, d in datos["componentes"].items():
        if d.get("impreso"):
            assert id_ in piezas, id_


def test_el_total_es_la_suma_de_las_filas_y_de_las_zonas():
    fs = masas.filas()
    assert all(f["zona"] in masas.ORDEN_ZONAS for f in fs)
    assert all(f["total_g"] >= 0 and f["fuente"] in ("hoja_de_datos", "estimado") for f in fs)
    assert math.isclose(masas.total(), sum(f["total_g"] for f in fs))
    assert math.isclose(sum(masas.por_zona().values()), masas.total())
    # Todas las zonas tienen algo (ninguna quedó vacía por un nombre mal escrito).
    assert all(v > 0 for v in masas.por_zona().values())


def test_reusa_piezas_perfil_y_tornilleria_de_precios():
    precios = costos.cargar()
    fs = masas.filas(precios=precios)
    imp = precios["estructura_3d"]["impresion"]
    # Las piezas impresas pesan lo de la pieza, SIN el desperdicio de la impresora.
    impresas = sum(f["total_g"] for f in fs if f["origen"] == "impresa")
    gramos_costo = sum(p["gramos_total"] for p in costos.piezas_impresas(precios))
    assert math.isclose(impresas * (1 + imp["desperdicio"]), gramos_costo)
    # El perfil pesa largo x kg/m, tramo por tramo.
    per = precios["estructura_3d"]["perfil"]
    perfil = sum(f["total_g"] for f in fs if f["origen"] == "perfil")
    assert math.isclose(perfil, costos.despiece_perfil(precios)["total_mm"] / 1000 * per["kg_por_m"] * 1000)
    # La tornillería contada (sin repuesto) está toda.
    n = sum(f["cantidad"] for f in fs if f["origen"] == "tornillería")
    assert n == sum(d["contados"] for d in costos.conteo_tornilleria(precios).values())


def test_las_masas_de_hoja_de_datos_que_pidio_el_usuario():
    c = masas.cargar()["componentes"]
    assert c["motor_cinta_monedas"]["masa_g"] == 280 and c["motor_cinta_vasos"]["masa_g"] == 280
    assert c["motor_prensa"]["masa_g"] == 55 and c["servo_empujador"]["masa_g"] == 55
    assert c["servo_desvio_e7"]["masa_g"] == 9
    assert c["esp32_carro"]["masa_g"] == 10


def test_comprobaciones_de_par():
    co = masas.comprobaciones()
    # Las dos cintas: el par pedido es positivo, menor que el de retención, y manda el peor radio.
    for cc in (co["monedas"], co["vasos"]):
        assert cc["peor"]["par_nm"] == max(x["par_nm"] for x in cc["casos"]) > 0
        assert cc["alcanza"] == (cc["peor"]["margen"] >= masas.FACTOR_SEGURIDAD)
    # La de vasos (5 vasos llenos) pide más que la de monedas.
    assert co["vasos"]["peor"]["par_nm"] > co["monedas"]["peor"]["par_nm"]
    # Prensa: T = F·e con la fuerza de la tapa y con la del catálogo.
    mg = masas.cargar()["comprobaciones"]["mg996r"]
    p50, p150 = co["prensa"]
    assert p50["par_nm"] < p150["par_nm"]
    assert math.isclose(p150["par_nm"] - p50["par_nm"], (p150["fuerza_n"] - p50["fuerza_n"]) * mg["excentricidad_m"])
    # Carro: la masa con el vaso es la del subsistema + el vaso lleno.
    ca = co["carro"]
    assert math.isclose(ca["m_total"], ca["m_carro"] + co["vaso_lleno_g"] / 1000)
    assert math.isclose(ca["m_carro"] * 1000, masas.por_zona()["Carro"])


def test_lo_que_no_alcanza_se_dice_en_el_documento():
    md = masas.generar_md()
    assert "# Peso del montaje" in md and "## Por subsistema" in md and "## Comprobaciones" in md
    total = masas._kg(masas.total())
    assert total in md
    alertas = masas.alertas()
    if alertas:
        assert "NO ALCANZA" in md
    else:
        assert "todos los motores alcanzan" in md
    # La cinta de monedas va primero en el detalle.
    detalle = md[md.index("## Detalle por subsistema"):]
    assert detalle.index("### Cinta de monedas") < detalle.index("### Cinta de vasos")


def test_vaso_lleno_de_la_simulacion_es_el_peor_caso_sumado():
    """2026-09-28: vehiculo.masa_vaso_lleno_kg (lo que carga el carro simulado) era 0,10 y
    la suma del peor caso (vaso + tapa + lote de la moneda mas pesada) da 0,133."""
    from app.configuracion import cargar_parametros

    p = cargar_parametros()
    assert math.isclose(p["vehiculo"]["masa_vaso_lleno_kg"], masas.vaso_lleno_g() / 1000, abs_tol=0.001)


def test_prensa_objetivo_realista_y_el_mg996r_alcanza():
    """La prensa apunta a asentar un snap-fit (la tapa mas dura x1,2), no a los 150 N
    del catalogo viejo; con eso el MG996R alcanza con margen x2 y el rodillo es uno solo."""
    mg = masas.cargar()["comprobaciones"]["mg996r"]
    assert mg["fuerza_prensa_objetivo_n"] == 60 >= max(mg["fuerza_tapa_n"]) * 1.2
    co = masas.comprobaciones()
    assert all(p["margen_6v"] >= masas.FACTOR_SEGURIDAD for p in co["prensa"])
    assert [c["radio"] for c in co["monedas"]["casos"]] == ["modelo 3D (Ø22)"]
    md = masas.generar_md()
    assert "150 N del catálogo NO" not in md and "no coincide" not in md
