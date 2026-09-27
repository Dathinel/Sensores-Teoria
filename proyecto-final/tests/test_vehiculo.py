"""Punto 14: el carro sigue la linea, esquiva los tres muros, llega a la
meta, espera que le saquen el vaso y vuelve SOLO al muelle, entrando de
reversa (sim/vehiculo_sim.py con fisica real, control/vehiculo.py).

Cada viaje de ida y vuelta son ~4-5 minutos simulados (~7 s de reloj)."""

import copy
import math

import pytest

from app.configuracion import cargar_parametros
from sim.vehiculo_sim import SimCarro


def _viaje(carro: SimCarro, limite_s: float = 500) -> list[dict]:
    """Carga el vaso, lo lleva a la meta, lo "retira" a los 4 s y vuelve."""
    eventos = []
    carro.cargar_vaso()
    llegada = None
    while carro.tiempo < limite_s:
        eventos += carro.avanzar(1.0)
        c = carro.control
        if c.estado == "en_meta":
            llegada = llegada or carro.tiempo
            if carro.tiempo - llegada >= carro.cfg["espera_descarga_meta_s"]:
                carro.retirar_vaso()
        if c.estado == "detenido" or (c.estado == "esperando_carga" and c.fase == "vuelta"):
            break
    return eventos


def _revisar_viaje(carro: SimCarro, eventos: list[dict]) -> None:
    nombres = [e["ev"] for e in eventos]
    assert "error" not in nombres, [e for e in eventos if e["ev"] == "error"]
    assert carro.control.estado == "esperando_carga" and carro.control.fase == "vuelta"
    assert nombres.count("meta") == 1
    # 3 muros a la ida y los mismos 3 a la vuelta, sin tocar ninguno.
    assert nombres.count("evasion") == 6
    assert carro.toques_muro == 0
    # Quedo en el muelle: la cuna bajo el final de la canaleta.
    x, y, r = carro.pose()
    assert abs(x - carro.salida[0]) < 0.005
    assert abs(y - carro.salida[1]) < 0.008
    assert abs(math.degrees(r - carro.salida[2])) < 2
    # El vaso casi no cabecea (arranques y frenadas con rampa).
    assert math.degrees(carro.inclinacion_max_vaso) < 5


def test_ida_y_vuelta_sin_errores():
    carro = SimCarro(cargar_parametros())
    try:
        _revisar_viaje(carro, _viaje(carro))
    finally:
        carro.cerrar()


@pytest.mark.parametrize("semilla", [1, 2, 3])
def test_ida_y_vuelta_con_los_errores_de_la_configuracion(semilla):
    """Motores distintos entre si, ruido del ultrasonico, lecturas cambiadas
    de los infrarrojos (errores_sensores.carro)."""
    carro = SimCarro(cargar_parametros(), errores=True, semilla=semilla)
    try:
        _revisar_viaje(carro, _viaje(carro))
    finally:
        carro.cerrar()


def test_ida_y_vuelta_con_el_doble_de_error():
    parametros = copy.deepcopy(cargar_parametros())
    parametros["errores_sensores"]["carro"] = {"diferencia_motores": 0.10, "ruido_ultrasonico_mm": 10,
                                               "error_linea": 0.03}
    carro = SimCarro(parametros, errores=True, semilla=6)
    try:
        _revisar_viaje(carro, _viaje(carro))
    finally:
        carro.cerrar()


def test_esquiva_hacia_el_lado_con_mas_espacio():
    """Una caja a la izquierda del primer muro: el carro mira a los dos lados
    y esquiva por la derecha, sin tocar nada."""
    parametros = cargar_parametros()
    carro = SimCarro(parametros)
    try:
        muro = __import__("sim.geometria", fromlist=["x"]).geometria_completa(parametros)["pista"]["obstaculos"][0]
        # A la izquierda del muro (19 cm afuera de la linea), donde mira el
        # ultrasonico cuando el carro gira 30 grados a la izquierda: justo por
        # donde pasaria esquivando por ese lado.
        izq = (-math.sin(muro["rumbo"]), math.cos(muro["rumbo"]))
        adelante = (math.cos(muro["rumbo"]), math.sin(muro["rumbo"]))
        carro.agregar_objeto(muro["x"] + 0.19 * izq[0] + 0.03 * adelante[0], muro["y"] + 0.19 * izq[1] + 0.03 * adelante[1])
        eventos = []
        carro.cargar_vaso()
        while carro.tiempo < 60 and not any(e["ev"] == "linea_recuperada" for e in eventos):
            eventos += carro.avanzar(1.0)
        evasion = next(e for e in eventos if e["ev"] == "evasion")
        assert evasion["lado"] == "derecha"
        assert evasion["izq_mm"] is not None and evasion["der_mm"] is None
        assert any(e["ev"] == "linea_recuperada" for e in eventos)
        assert carro.toques_muro == 0
    finally:
        carro.cerrar()


# ---------------------------------------------------------------------
# Fase 7: ordenes al carro (asistente o botones)
# ---------------------------------------------------------------------


def _cumplir(carro: SimCarro, orden: dict, limite_s: float = 60) -> list[dict]:
    ok, detalle = carro.control.ordenar(orden)
    assert ok, detalle
    eventos = []
    inicio = carro.tiempo
    while carro.tiempo - inicio < limite_s:
        eventos += carro.avanzar(0.5)
        if carro.control.estado in ("esperando_orden", "detenido", "esperando_carga", "en_meta"):
            break
    return eventos


def test_ordenes_invalidas_se_rechazan_sin_moverse():
    carro = SimCarro(cargar_parametros())
    try:
        c = carro.control
        assert not c.ordenar({"accion": "avanzar", "distancia_m": 5})[0]
        assert not c.ordenar({"accion": "retroceder", "distancia_m": 1})[0]   # atras no hay sensor
        assert not c.ordenar({"accion": "girar", "grados": 400})[0]
        assert not c.ordenar({"accion": "volar"})[0]
        assert not c.ordenar({"accion": "volver_muelle"})[0]                  # ya esta en el muelle
        assert c.estado == "esperando_carga"
    finally:
        carro.cerrar()


def test_avanzar_y_girar_con_odometria():
    carro = SimCarro(cargar_parametros())
    try:
        x0, y0, r0 = carro.pose()
        _cumplir(carro, {"accion": "avanzar", "distancia_m": 0.4})
        x1, y1, r1 = carro.pose()
        assert abs(math.hypot(x1 - x0, y1 - y0) - 0.4) < 0.03
        _cumplir(carro, {"accion": "girar", "grados": 90})
        assert abs(math.degrees(carro.pose()[2] - r1) - 90) < 10
        # La odometria sabe mas o menos donde esta.
        ox, oy, _ = carro.control.posicion_estimada()
        x, y, _ = carro.pose()
        assert math.hypot(ox - x, oy - y) < 0.04
        assert carro.control.estado == "esperando_orden"
    finally:
        carro.cerrar()


def test_no_choca_si_el_camino_pasa_por_un_muro():
    """Un punto detras del primer muro: el carro mira el camino (+-15
    grados) y no se mueve, o se detiene frente al muro; nunca lo toca."""
    carro = SimCarro(cargar_parametros(), errores=True, semilla=3)
    try:
        for orden in ({"accion": "avanzar", "distancia_m": 0.4}, {"accion": "girar", "grados": 90},
                      {"accion": "avanzar", "distancia_m": 0.3}, {"accion": "retroceder", "distancia_m": 0.1}):
            _cumplir(carro, orden)
        nombres = [e["ev"] for e in _cumplir(carro, {"accion": "ir_a", "x": 1.26, "y": -0.5075})]
        assert {"camino_bloqueado", "bloqueado"} & set(nombres)
        assert carro.toques_muro == 0
    finally:
        carro.cerrar()


def test_desde_fuera_de_la_linea_va_a_la_meta_y_vuelve_al_muelle():
    carro = SimCarro(cargar_parametros(), errores=True, semilla=3)
    try:
        _cumplir(carro, {"accion": "avanzar", "distancia_m": 0.4})
        _cumplir(carro, {"accion": "girar", "grados": 90})
        _cumplir(carro, {"accion": "avanzar", "distancia_m": 0.2})
        eventos = _cumplir(carro, {"accion": "ir_meta"}, limite_s=300)
        assert carro.control.estado == "en_meta", [e["ev"] for e in eventos][-8:]
        eventos = _cumplir(carro, {"accion": "volver_muelle"}, limite_s=300)
        assert carro.control.estado == "esperando_carga", [e["ev"] for e in eventos][-8:]
        assert carro.toques_muro == 0
        # En el muelle la odometria se vuelve a poner en la posicion conocida.
        ox, oy, _ = carro.control.posicion_estimada()
        assert math.hypot(ox - carro.salida[0], oy - carro.salida[1]) < 0.01
        x, y, _ = carro.pose()
        assert abs(x - carro.salida[0]) < 0.01 and abs(y - carro.salida[1]) < 0.01
    finally:
        carro.cerrar()


def test_desde_el_muelle_sale_derecho_antes_de_girar():
    """En el muelle las guias en V dejan 3 mm de holgura: una orden de girar
    (o de ir a un punto) primero lo saca derecho, sin rozar las guias."""
    import pybullet as p

    carro = SimCarro(cargar_parametros(), errores=True, semilla=5)
    try:
        ok, detalle = carro.control.ordenar({"accion": "girar", "grados": 90})
        assert ok and "sale del muelle" in detalle
        roces = 0
        while carro.control.estado != "esperando_orden" and carro.tiempo < 40:
            carro.avanzar(0.05)
            if carro.tiempo > 1.0:   # al principio apoya en los topes (normal)
                # por lado: guia recta, boca en V y tope (los topes no cuentan)
                roces += sum(bool(p.getContactPoints(carro.carro, m, physicsClientId=carro.cli))
                             for i, m in enumerate(carro.muelle) if i % 3 != 2)
        assert carro.control.estado == "esperando_orden"
        assert roces == 0
    finally:
        carro.cerrar()
