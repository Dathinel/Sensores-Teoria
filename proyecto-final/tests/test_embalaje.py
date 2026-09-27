import pytest

from control.embalaje import EmbalajeVasos
from control.registro import EstadoVaso


def test_ciclo_completo_feliz_vaso_llega_a_entregada():
    embalaje = EmbalajeVasos()
    embalaje.verificar_antes_de_llenado(0, presente=True, media_bloqueada=True, borde_libre=True)
    assert embalaje.registro.obtener(0).estado == EstadoVaso.VALIDA

    assert embalaje.intentar_llenar(0, valor=500, masa_g=7.1) is True
    assert embalaje.intentar_llenar(0, valor=200, masa_g=4.6) is True
    embalaje.cerrar_llenado(0)
    assert embalaje.registro.obtener(0).estado == EstadoVaso.LLENA
    assert embalaje.registro.obtener(0).valor_total == 700

    assert embalaje.tapar(0, presente=True, media_bloqueada=True, borde_libre=True) is True
    assert embalaje.prensar(0) is True
    assert embalaje.descargar(0) == "entrega"
    assert embalaje.registro.obtener(0).estado == EstadoVaso.ENTREGADA


def test_casilla_vacia_no_se_llena_y_el_llamador_debe_saltar():
    embalaje = EmbalajeVasos()
    embalaje.verificar_antes_de_llenado(0, presente=False, media_bloqueada=False, borde_libre=False)
    assert embalaje.intentar_llenar(0, valor=500, masa_g=7.1) is False
    assert embalaje.registro.obtener(0).cantidad_monedas == 0


def test_vaso_invalido_por_silueta_no_se_llena():
    embalaje = EmbalajeVasos()
    # figura distinta: bloquea el borde en vez de la media altura
    embalaje.verificar_antes_de_llenado(0, presente=True, media_bloqueada=False, borde_libre=False)
    assert embalaje.registro.obtener(0).estado == EstadoVaso.INVALIDA
    assert embalaje.intentar_llenar(0, valor=500, masa_g=7.1) is False


def test_vaso_retirado_despues_de_llenado_no_recibe_tapa():
    embalaje = EmbalajeVasos()
    embalaje.verificar_antes_de_llenado(0, presente=True, media_bloqueada=True, borde_libre=True)
    embalaje.intentar_llenar(0, valor=500, masa_g=7.1)
    embalaje.cerrar_llenado(0)

    # entre el llenado y la estacion de tapa, retiraron el vaso de la linea
    tapo = embalaje.tapar(0, presente=False, media_bloqueada=False, borde_libre=False)

    assert tapo is False
    assert embalaje.registro.obtener(0).estado == EstadoVaso.INVALIDA
    # y por lo tanto tampoco se puede prensar ni descargar como entrega
    assert embalaje.prensar(0) is False
    assert embalaje.descargar(0) == "rechazo"


def test_vaso_sustituido_por_figura_distinta_se_detecta_en_tapa():
    embalaje = EmbalajeVasos()
    embalaje.verificar_antes_de_llenado(0, presente=True, media_bloqueada=True, borde_libre=True)
    embalaje.intentar_llenar(0, valor=1000, masa_g=10.0)
    embalaje.cerrar_llenado(0)

    # la re-verificacion en la estacion de tapa no confia en el estado
    # registrado antes (paso 11): ahora el borde tambien esta bloqueado
    # (figura mas alta, p. ej.)
    tapo = embalaje.tapar(0, presente=True, media_bloqueada=True, borde_libre=False)
    assert tapo is False
    assert embalaje.registro.obtener(0).estado == EstadoVaso.INVALIDA


def test_cortina_de_seguridad_congela_tapa_prensa_y_empujador():
    embalaje = EmbalajeVasos()
    embalaje.verificar_antes_de_llenado(0, presente=True, media_bloqueada=True, borde_libre=True)
    embalaje.intentar_llenar(0, valor=500, masa_g=7.1)
    embalaje.cerrar_llenado(0)

    embalaje.activar_cortina()  # una mano invadio la zona de tapa/prensa

    assert embalaje.tapar(0, presente=True, media_bloqueada=True, borde_libre=True) is False
    assert embalaje.prensar(0) is False
    with pytest.raises(RuntimeError):
        embalaje.descargar(0)

    # el estado del vaso no cambio mientras la cortina estuvo activa
    assert embalaje.registro.obtener(0).estado == EstadoVaso.LLENA

    embalaje.despejar_cortina()
    assert embalaje.tapar(0, presente=True, media_bloqueada=True, borde_libre=True) is True
    assert embalaje.descargar(0) == "entrega"


def test_casilla_invalida_puede_recuperarse_si_en_el_siguiente_ciclo_es_valida():
    embalaje = EmbalajeVasos()
    embalaje.verificar_antes_de_llenado(0, presente=True, media_bloqueada=False, borde_libre=True)
    assert embalaje.registro.obtener(0).estado == EstadoVaso.INVALIDA

    embalaje.verificar_antes_de_llenado(0, presente=True, media_bloqueada=True, borde_libre=True)
    assert embalaje.registro.obtener(0).estado == EstadoVaso.VALIDA
    assert embalaje.intentar_llenar(0, valor=200, masa_g=4.6) is True



# --- marcador ArUco del vaso personalizado ---


def _lleno(embalaje, marcador):
    embalaje.verificar_antes_de_llenado(0, presente=True, media_bloqueada=True, borde_libre=True, marcador=marcador)
    embalaje.llenar_lote(0, denominacion=500, monedas=[(500, 7.1)] * 5)


def test_vaso_cambiado_por_otro_igual_no_recibe_tapa():
    """Mismo tamano (la silueta lo da por bueno) pero otro marcador."""
    e = EmbalajeVasos()
    _lleno(e, marcador=17)
    assert e.tapar(0, presente=True, media_bloqueada=True, borde_libre=True, marcador=23) is False
    assert e.registro.obtener(0).estado == EstadoVaso.INVALIDA


def test_mismo_marcador_se_tapa():
    e = EmbalajeVasos()
    _lleno(e, marcador=17)
    assert e.tapar(0, presente=True, media_bloqueada=True, borde_libre=True, marcador=17) is True


def test_marcador_ilegible_no_bloquea_decide_con_la_silueta():
    e = EmbalajeVasos()
    _lleno(e, marcador=17)
    assert e.tapar(0, presente=True, media_bloqueada=True, borde_libre=True, marcador=None) is True
