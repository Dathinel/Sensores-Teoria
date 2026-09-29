"""Carrusel del almacen (control/carrusel.py): donde queda cada tubo y
CUANDO llega, con el tiempo real del 28BYJ-48 (media vuelta = 4096 ms)."""

import pytest

from control.carrusel import AGUJERO, CARGA, Carrusel

POS = (50, 100, 200, 500, 1000, "otras")
MEDIA_VUELTA = 4096


def nuevo():
    return Carrusel(POS, MEDIA_VUELTA, angulo_carga=90.0, angulo_agujero=300.0)


def test_arranca_con_el_tubo_de_50_quieto_bajo_la_carga():
    c = nuevo()
    assert c.en(50, CARGA, 0) and c.listo(0)
    assert c.tubo_en(CARGA, 0) == 50
    # El agujero queda ENTRE dos tubos (210 grados no es multiplo de 60).
    assert c.tubo_en(AGUJERO, 0) is None


def test_angulos_de_carga_y_agujero():
    c = nuevo()
    assert c.angulo_para(100, CARGA) == pytest.approx(300.0)      # -60
    assert c.angulo_para(500, CARGA) == pytest.approx(180.0)
    assert c.angulo_para(50, AGUJERO) == pytest.approx(210.0)
    assert c.angulo_para("otras", AGUJERO) == pytest.approx((210 - 300) % 360)


def test_un_tubo_vecino_tarda_un_tercio_de_media_vuelta_por_el_camino_corto():
    c = nuevo()
    llegada = c.pedir(100, CARGA, 1000)
    assert llegada == pytest.approx(1000 + MEDIA_VUELTA / 3)      # 1365 ms
    assert c.ultimo_giro["hasta_grados"] - c.ultimo_giro["desde_grados"] == pytest.approx(-60)
    assert not c.en(100, CARGA, 1000 + 1300)                        # todavia girando
    assert c.tubo_en(CARGA, 1000 + 1300) is None
    assert c.en(100, CARGA, llegada) and c.tubo_en(CARGA, llegada) == 100


def test_el_tubo_opuesto_tarda_media_vuelta():
    c = nuevo()
    assert c.pedir(500, CARGA, 0) == pytest.approx(MEDIA_VUELTA)
    assert c.duracion_ms(180) == MEDIA_VUELTA


def test_ir_al_agujero_y_volver():
    c = nuevo()
    llegada = c.pedir(200, AGUJERO, 0)
    # 200 es la posicion 2: de 0 a 210-120 = 90 grados -> media vuelta / 2.
    assert llegada == pytest.approx(MEDIA_VUELTA / 2)
    assert c.tubo_en(AGUJERO, llegada) == 200
    assert c.tubo_en(CARGA, llegada) is None                        # hueco entre tubos
    vuelta = c.pedir(200, CARGA, llegada + 600)
    assert c.tubo_en(CARGA, vuelta) == 200


def test_pedir_lo_mismo_no_gira_otra_vez():
    c = nuevo()
    llegada = c.pedir(1000, CARGA, 0)
    giros = c.giros
    assert c.pedir(1000, CARGA, 500) == llegada
    assert c.giros == giros


def test_un_pedido_nuevo_a_mitad_de_giro_arranca_desde_donde_va():
    """Como el firmware: solo cambia el objetivo, el disco no salta."""
    c = nuevo()
    c.pedir(500, CARGA, 0)                   # 180 grados en 4096 ms
    mitad = MEDIA_VUELTA / 2
    assert c.angulo_en(mitad) == pytest.approx(90.0) or c.angulo_en(mitad) == pytest.approx(-90.0)
    desde = c.angulo_en(mitad)
    c.pedir(50, CARGA, mitad)                # volver al de 50
    assert c.ultimo_giro["desde_grados"] == pytest.approx(desde)
    assert c.llegada_ms == pytest.approx(mitad + MEDIA_VUELTA / 2)


def test_el_reloj_no_va_hacia_atras():
    c = nuevo()
    c.pedir(100, CARGA, 5000)
    c.pedir(200, CARGA, 1000)                # pedido "en el pasado": arranca en 5000
    assert c.ultimo_giro["t_inicio_ms"] == 5000


def test_estado_para_la_telemetria():
    c = nuevo()
    c.pedir(1000, CARGA, 0)
    e = c.estado(100)
    assert e["girando"] and e["tubo"] == 1000 and e["lugar"] == CARGA and e["tubo_en_carga"] is None
    assert e["llega_en_ms"] == round(c.llegada_ms - 100)
    fin = c.estado(c.llegada_ms)
    assert not fin["girando"] and fin["tubo_en_carga"] == 1000 and fin["llega_en_ms"] == 0


def test_errores_claros():
    c = nuevo()
    with pytest.raises(ValueError):
        c.pedir(20, CARGA, 0)
    with pytest.raises(ValueError):
        c.pedir(50, "tolva", 0)


def test_sin_cosas_que_micropython_no_tiene():
    """Mismas reglas que control/protocolo.py: puede ir al firmware."""
    import ast
    import pathlib
    arbol = ast.parse(pathlib.Path("control/carrusel.py").read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        assert not isinstance(nodo, ast.Starred), "[*x] no existe en MicroPython"
        if isinstance(nodo, ast.Dict):
            assert None not in nodo.keys, "{**d} no existe en MicroPython"
        if isinstance(nodo, (ast.Import, ast.ImportFrom)):
            assert "dataclasses" not in ast.dump(nodo)


def test_presupuesto_dice_cuanto_baja_la_produccion():
    """control/tiempos.py: el carrusel sigue en NO CABE (decision aceptada) y ademas
    dice cuanto espera la cinta y cuanto baja el ritmo."""
    from app.configuracion import cargar_parametros
    from control.tiempos import elementos_por_minuto_medidos, presupuesto

    p = cargar_parametros()
    t = p["tiempos_ms"]
    r = presupuesto(t, lote=p["planta"]["monedas_por_vaso"], lecturas_por_decision=3,
                    reaccion_cortina_max_ms=250, fotos_por_moneda=p["planta"]["fotos_por_moneda"])
    c = r["carrusel"]
    ciclo = t["avance_casilla_monedas"] + t["pausa_casilla_monedas"]
    hueco = ciclo - p["planta"]["fotos_por_moneda"] * t["vision_captura_inferencia"] - t["serial_ida_vuelta"]
    assert c["hueco_ms"] == hueco                                        # 780 ms con los valores de hoy
    assert c["espera_peor_ms"] == pytest.approx(t["carrusel_giro"] - hueco)     # 3316 ms
    assert c["espera_tubo_vecino_ms"] == pytest.approx(t["carrusel_giro"] / 3 - hueco)
    assert c["elementos_por_minuto_peor"] < c["elementos_por_minuto_tubo_vecino"] < r["elementos_por_minuto"]
    assert elementos_por_minuto_medidos(40, 50, t) == pytest.approx(60 * 40 / (50 * ciclo / 1000))


def test_la_duracion_sigue_al_firmware():
    """tiempos_ms.carrusel_giro = medio paso x ms por paso x media vuelta."""
    from app.configuracion import cargar_parametros
    p = cargar_parametros()
    f = p["firmware"] if "firmware" in p else p["tiempos_ms"]
    pasos = f.get("carrusel_pasos_por_vuelta", p["tiempos_ms"].get("carrusel_pasos_por_vuelta"))
    ms = f.get("carrusel_ms_por_paso", p["tiempos_ms"].get("carrusel_ms_por_paso"))
    c = Carrusel(POS, p["tiempos_ms"]["carrusel_giro"])
    assert c.duracion_ms(180) == pytest.approx(pasos / 2 * ms)
