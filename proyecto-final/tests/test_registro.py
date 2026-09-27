from control.registro import CasillaMoneda, EstadoVaso, registro_monedas, registro_vasos


def test_obtener_crea_una_sola_vez_y_reutiliza():
    registro = registro_monedas()
    casilla_a = registro.obtener(3)
    casilla_a.ocupada = True
    casilla_b = registro.obtener(3)
    assert casilla_a is casilla_b
    assert casilla_b.ocupada is True


def test_casillas_distintas_son_independientes():
    registro = registro_monedas()
    registro.obtener(1).ocupada = True
    assert registro.obtener(2).ocupada is False


def test_rechazar_no_revierte_causa_previa():
    casilla = CasillaMoneda(indice=1)
    casilla.rechazar("no_metalico")
    casilla.rechazar("fuera_de_rango")
    assert casilla.causa == "no_metalico"


def test_rechazada_y_aceptada_son_consistentes():
    casilla = CasillaMoneda(indice=1)
    assert casilla.rechazada is False
    casilla.rechazar("perforado")
    assert casilla.rechazada is True
    assert casilla.aceptada is False


def test_casilla_vaso_arranca_vacia_y_acumula_monedas():
    registro = registro_vasos()
    vaso = registro.obtener(0)
    assert vaso.estado == EstadoVaso.VACIA
    vaso.acumular_moneda(valor=500, masa_g=7.1)
    vaso.acumular_moneda(valor=200, masa_g=4.6)
    assert vaso.cantidad_monedas == 2
    assert vaso.valor_total == 700
    assert abs(vaso.masa_estimada_g - 11.7) < 1e-9


def test_casilla_vaso_se_puede_degradar_en_cualquier_momento():
    registro = registro_vasos()
    vaso = registro.obtener(0)
    vaso.degradar(EstadoVaso.LLENA)
    vaso.degradar(EstadoVaso.INVALIDA)
    assert vaso.estado == EstadoVaso.INVALIDA


def test_eliminar_borra_la_casilla():
    registro = registro_monedas()
    registro.obtener(5)
    assert registro.existe(5)
    registro.eliminar(5)
    assert not registro.existe(5)
