from control import monedas


def test_nueve_clases_verificadas_de_las_dos_ultimas_familias():
    verificadas = [m for m in monedas.TABLA_MONEDAS if m.verificado]
    assert len(verificadas) == 9
    assert {m.familia for m in verificadas} == {"nueva", "antigua"}


def test_cuatro_generaciones():
    assert {m.familia for m in monedas.TABLA_MONEDAS} == set(monedas.FAMILIAS)
    assert len(monedas.clases_colombianas()) == len(monedas.TABLA_MONEDAS)


def test_generaciones_viejas_marcadas_como_provisionales():
    assert monedas.sin_verificar()
    assert all(m.familia in ("muy_antigua", "historica") for m in monedas.sin_verificar())


def test_clases_unicas():
    clases = [m.clase for m in monedas.TABLA_MONEDAS]
    assert len(clases) == len(set(clases))


def test_clase_tiene_formato_denominacion_familia():
    moneda = monedas.buscar_por_clase("500_nueva")
    assert moneda is not None
    assert moneda.denominacion == 500
    assert moneda.familia == "nueva"
    assert moneda.bimetalica is True


def test_clase_otro_no_esta_en_la_tabla():
    assert monedas.buscar_por_clase(monedas.CLASE_OTRO) is None
    assert monedas.diametro_nominal_mm(monedas.CLASE_OTRO) is None


def test_clase_desconocida_devuelve_none():
    assert monedas.buscar_por_clase("1_euro") is None


def test_diametro_y_masa_nominal_coinciden_con_la_tabla():
    assert monedas.diametro_nominal_mm("1000_nueva") == 26.7
    assert monedas.masa_nominal_g("1000_nueva") == 10.0
    assert monedas.valor_pesos("1000_nueva") == 1000


def test_todas_las_monedas_caben_en_el_rango_de_filtrado():
    """Si una moneda colombiana real quedara fuera del rango de diametro,
    el filtro de geometria la rechazaria antes de reconocerla."""
    for m in monedas.TABLA_MONEDAS:
        assert 16.5 <= m.diametro_mm <= 27.5, m.clase


def test_tubos_son_de_denominaciones_existentes():
    existentes = {m.denominacion for m in monedas.TABLA_MONEDAS}
    assert set(monedas.DENOMINACIONES_CON_TUBO) <= existentes
