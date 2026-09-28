"""Reglas del grupo: ninguna moneda aceptada se descarta (se guarda por
denominacion) y cada vaso lleva UNA sola denominacion."""

import pytest

from control.almacen import AlmacenDenominaciones, MonedaAlmacenada, TuboLleno
from control.embalaje import EmbalajeVasos
from control.registro import EstadoVaso


def _moneda(i, valor=500):
    return MonedaAlmacenada(id_registro=i, clase=f"{valor}_nueva", valor=valor, masa_g=7.1)


def test_guarda_por_denominacion_sin_mezclar():
    a = AlmacenDenominaciones()
    a.guardar(500, _moneda(1, 500))
    a.guardar(50, _moneda(2, 50))
    a.guardar(500, _moneda(3, 500))
    assert a.contenido() == {50: 1, 100: 0, 200: 0, 500: 2, 1000: 0}
    assert a.total() == 3


def test_lote_listo_solo_con_tubo_completo():
    a = AlmacenDenominaciones()
    for i in range(2):
        a.guardar(200, _moneda(i, 200))
    assert a.lote_listo(3) is None
    a.guardar(200, _moneda(9, 200))
    assert a.lote_listo(3) == 200


def test_lote_listo_prefiere_el_tubo_mas_lleno():
    a = AlmacenDenominaciones()
    for i in range(3):
        a.guardar(100, _moneda(i, 100))
    for i in range(5):
        a.guardar(500, _moneda(10 + i, 500))
    assert a.lote_listo(3) == 500


def test_parciales_al_final_de_turno():
    a = AlmacenDenominaciones()
    a.guardar(1000, _moneda(1, 1000))
    assert a.lote_listo(5) is None
    assert a.lote_listo(5, aceptar_parciales=True) == 1000


def test_sacar_en_orden_de_llegada():
    a = AlmacenDenominaciones()
    for i in (7, 8, 9):
        a.guardar(50, _moneda(i, 50))
    assert [m.id_registro for m in a.sacar(50, 2)] == [7, 8]
    assert a.cantidad(50) == 1


def test_tubo_lleno_no_descarta_avisa():
    a = AlmacenDenominaciones(capacidad=2)
    a.guardar(500, _moneda(1))
    a.guardar(500, _moneda(2))
    assert not a.puede_recibir(500)
    with pytest.raises(TuboLleno):
        a.guardar(500, _moneda(3))
    assert a.cantidad(500) == 2


def test_vaso_no_acepta_otra_denominacion():
    e = EmbalajeVasos()
    e.verificar_antes_de_llenado(0, presente=True, media_bloqueada=True, borde_libre=True)
    assert e.intentar_llenar(0, valor=500, masa_g=7.1, denominacion=500)
    assert not e.intentar_llenar(0, valor=50, masa_g=2.0, denominacion=50)
    c = e.registro.obtener(0)
    assert (c.denominacion, c.cantidad_monedas, c.valor_total) == (500, 1, 500)


def test_llenar_lote_deja_el_vaso_lleno_de_una_denominacion():
    e = EmbalajeVasos()
    e.verificar_antes_de_llenado(0, presente=True, media_bloqueada=True, borde_libre=True)
    assert e.llenar_lote(0, denominacion=200, monedas=[(200, 4.6), (200, 7.1), (200, 4.6)])
    c = e.registro.obtener(0)
    assert c.estado == EstadoVaso.LLENA
    assert (c.denominacion, c.cantidad_monedas, c.valor_total) == (200, 3, 600)


def test_llenar_lote_rechaza_vaso_invalido_o_no_vacio():
    e = EmbalajeVasos()
    e.verificar_antes_de_llenado(0, presente=True, media_bloqueada=False, borde_libre=True)  # figura baja
    assert not e.llenar_lote(0, denominacion=500, monedas=[(500, 7.1)])
    assert e.registro.obtener(0).cantidad_monedas == 0
    e.verificar_antes_de_llenado(1, presente=True, media_bloqueada=True, borde_libre=True)
    e.llenar_lote(1, denominacion=500, monedas=[(500, 7.1)])
    assert not e.llenar_lote(1, denominacion=500, monedas=[(500, 7.1)])  # ya esta lleno


def test_vaso_vacio_valido_no_se_tapa_y_se_desecha():
    """Grupo, 2026-09-25: un vaso al que no le cayo lote no se tapa ni se
    prensa; se desecha para que la cinta quede libre y cada corrida arranque
    de cero."""
    e = EmbalajeVasos()
    e.verificar_antes_de_llenado(0, presente=True, media_bloqueada=True, borde_libre=True)
    assert not e.tapar(0, presente=True, media_bloqueada=True, borde_libre=True)
    assert not e.prensar(0)
    assert e.descargar(0) == "vacio"

    e.verificar_antes_de_llenado(1, presente=True, media_bloqueada=False, borde_libre=True)
    assert e.descargar(1) == "rechazo"


def test_denominaciones_sin_tubo_van_juntas_a_su_propio_vaso():
    from control.almacen import OTRAS

    a = AlmacenDenominaciones()
    for i, (d, clase) in enumerate([(20, "20_historica"), (10, "10_muy_antigua"), (5, "5_historica")]):
        assert a.destino(d) == OTRAS
        a.guardar(d, MonedaAlmacenada(i, clase, d, 4.0))
    assert a.cantidad_otras() == 3 and a.valor_total() == 35
    assert a.lote_listo(5) is None
    assert a.lote_listo(3) == OTRAS
    assert [m.clase for m in a.sacar(OTRAS, 3)] == ["20_historica", "10_muy_antigua", "5_historica"]
