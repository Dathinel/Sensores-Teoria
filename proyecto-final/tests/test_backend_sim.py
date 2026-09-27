"""Pruebas de la emulacion de sensores (fase 3), en modo DIRECT."""

import math

import pytest

from control.hal.backend_sim import EstacionBackendSim
from sim.mundo import (
    ESTACION_MATERIAL_MONEDAS,
    ESTACION_PRESENCIA_MONEDAS,
    ESTACION_TAPA_VASOS,
    NUM_ESTACIONES_VASOS,
    EscenaEstacion,
)


@pytest.fixture
def escena():
    e = EscenaEstacion()
    yield e
    e.cerrar()


@pytest.fixture
def backend(escena):
    return EstacionBackendSim(escena)


def test_sensor_presencia_detecta_elemento_en_su_casilla(escena, backend):
    assert backend.sensor_presencia.leer() is False
    escena.crear_elemento(tipo="boton_plastico", casilla=ESTACION_PRESENCIA_MONEDAS)
    assert backend.sensor_presencia.leer() is True


def test_sensor_presencia_ignora_elementos_en_otra_casilla(escena, backend):
    escena.crear_elemento(tipo="boton_plastico", casilla=3)
    assert backend.sensor_presencia.leer() is False


def test_capacitivo_responde_a_cualquier_elemento_inductivo_solo_a_metalicos(escena, backend):
    # Los dos van bajo la cinta, cada uno centrado bajo su casilla: el
    # capacitivo bajo E1 y el inductivo bajo E2.
    escena.crear_elemento(tipo="boton_plastico", casilla=ESTACION_PRESENCIA_MONEDAS, metal=False)
    escena.crear_elemento(tipo="boton_plastico", casilla=ESTACION_MATERIAL_MONEDAS, metal=False)
    assert backend.sensor_capacitivo.leer() is True
    assert backend.sensor_inductivo.leer() is False


def test_inductivo_activo_con_elemento_metalico(escena, backend):
    escena.crear_elemento(tipo="boton_metalico", casilla=ESTACION_MATERIAL_MONEDAS, metal=True)
    assert backend.sensor_capacitivo.leer() is False   # E1 vacia
    assert backend.sensor_inductivo.leer() is True


def test_camara_vasos_franja_media_ocupada_con_vaso_valido(escena, backend):
    escena.crear_vaso(casilla=0)
    media, borde = backend.zona_verificacion.leer()
    assert media is True
    assert borde is False  # el borde de un vaso normal no llega a esa altura


def test_camara_vasos_franjas_libres_sin_vaso(escena, backend):
    media, borde = backend.zona_verificacion.leer()
    assert media is False
    assert borde is False


def test_camara_vasos_presencia(escena, backend):
    assert backend.zona_verificacion.presencia.leer() is False
    escena.crear_vaso(casilla=0)
    assert backend.zona_verificacion.presencia.leer() is True


def test_cortina_libre_sin_intrusos(escena, backend):
    assert backend.sensor_cortina.leer() is False


def test_cortina_se_dispara_con_una_mano_a_media_altura(escena, backend):
    # a mitad de camino entre la estacion de tapa y la de prensa, no justo
    # en el origen del sensor (ver docstring de crear_intruso).
    intruso = escena.crear_intruso(casilla_vasos=ESTACION_TAPA_VASOS + 0.5, altura_mano_m=0.065)
    assert backend.sensor_cortina.leer() is True
    escena.quitar_intruso(intruso)
    assert backend.sensor_cortina.leer() is False


def test_una_mano_por_encima_de_los_vasos_no_la_ve_la_cortina(escena, backend):
    """Usuario, 2026-09-26: un solo sensor a media altura. Una mano que pasa
    por encima de los vasos puede evadirlo; ese caso lo cubre la camara de
    vasos, que revisa en cada tick que no falte ningun vaso."""
    intruso = escena.crear_intruso(casilla_vasos=ESTACION_TAPA_VASOS + 0.5)
    assert backend.sensor_cortina.leer() is False
    escena.quitar_intruso(intruso)


def test_la_cortina_es_un_cono_no_un_rayo(escena, backend):
    """El VL53L0X ve en un cono de ~25 grados: algo que entra por el borde
    del cono (lejos del eje) tambien lo dispara, cosa que un rayo delgado no
    veria."""
    import pybullet as p
    c = backend.sensor_cortina
    assert c.radio_final_m == pytest.approx(c.alcance_m * math.tan(math.radians(12.5)), rel=1e-6)
    x = c.destino[0] + 0.02
    radio = (c.origen[0] - x) * math.tan(math.radians(12.5))
    col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.01, 0.01, 0.005])
    dedo = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col,
                             basePosition=[x, c.origen[1], c.origen[2] + radio * 0.9])
    assert backend.sensor_cortina.leer() is True
    p.removeBody(dedo)


def test_retirar_vaso_lo_saca_de_la_escena_y_de_la_camara(escena, backend):
    vaso = escena.crear_vaso(casilla=0)
    assert backend.zona_verificacion.leer()[0] is True

    escena.retirar_vaso(vaso)

    assert vaso not in escena.elementos_vasos
    media, _ = backend.zona_verificacion.leer()
    assert media is False


def test_camara_vasos_ve_la_tapa(escena, backend):
    vaso = escena.crear_vaso(casilla=ESTACION_TAPA_VASOS)
    assert backend.camara_vasos.leer_tapa(ESTACION_TAPA_VASOS) is False
    escena.colocar_tapa(vaso)
    assert backend.camara_vasos.leer_tapa(ESTACION_TAPA_VASOS) is True


def test_una_mano_que_agarra_un_vaso_dispara_la_cortina(escena, backend):
    """Una mano que entra a agarrar el vaso de prensa cruza el cono a media altura."""
    mano = escena.crear_intruso(casilla_vasos=ESTACION_TAPA_VASOS + 1, altura_mano_m=0.045)
    assert backend.sensor_cortina.leer() is True
    escena.quitar_intruso(mano)


def test_la_prensa_y_la_tapa_no_cortan_la_cortina(escena, backend):
    """La cortina va del lado del operador, afuera del borde de los vasos:
    con vasos (tapados) en todas las casillas, el cono no los toca y no se
    dispara sola en cada ciclo."""
    for casilla in range(NUM_ESTACIONES_VASOS):
        vaso = escena.crear_vaso(casilla=casilla)
        escena.colocar_tapa(vaso)
    assert backend.sensor_cortina.leer() is False


def test_el_cono_de_la_cortina_no_toca_vasos_ni_cinta(backend):
    """Cuenta geometrica con el REBORDE del vaso (la simulacion usa un
    cilindro liso): en cada casilla dentro del alcance el cono queda a mas
    de 10 mm del reborde, y por abajo a mas de 20 mm de la cinta."""
    import yaml
    from pathlib import Path
    from sim.mundo import posicion_estacion_vasos
    vaso = yaml.safe_load((Path(__file__).resolve().parents[1] / "config" / "parametros.yaml")
                          .read_text(encoding="utf-8"))["vasos"]
    radio_reborde = (vaso["diametro_mm"] / 2 + vaso["reborde_mm"]) / 1000
    c = backend.sensor_cortina
    tg = math.tan(c.semiangulo)
    for casilla in range(NUM_ESTACIONES_VASOS):
        x, y, z = posicion_estacion_vasos(casilla)
        d = c.origen[0] - x
        if d - radio_reborde > c.alcance_m or d + radio_reborde < 0:
            continue
        # El punto del reborde mas lejano al sensor es donde el cono esta
        # mas abierto.
        d_max = min(d + radio_reborde, c.alcance_m)
        separacion = abs(c.origen[1] - y) - d_max * tg - radio_reborde
        assert separacion > 0.010, (casilla, separacion)
    assert c.origen[2] - c.radio_final_m - z > 0.020
