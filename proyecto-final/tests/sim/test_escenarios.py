"""Cada filtro por separado y el escenario mixto de 20 elementos (docs/especificacion.md,
seccion 16, fase 3): corridos en la planta completa, en modo DIRECT y con la
camara oraculo sin ruido, cada elemento tiene que terminar donde dice el
escenario. Los escenarios estan en sim/escenarios/pruebas_aisladas/ (la
interfaz solo los corre como "prueba de un filtro"; la corrida normal es la
prueba completa)."""

import pytest

from control import reglas
from control.embalaje import EmbalajeVasos
from control.hal.backend_sim import EstacionBackendSim
from control.linea import Destino, LineaMonedas
from sim.sensores_sim import CamaraOraculo
from sim.carga_escenarios import cargar_escenario, listar_escenarios
from sim.mundo import EscenaEstacion
from sim.planta import PlantaSimulada

NOMBRES_ESCENARIOS_POR_FILTRO = ["no_metalico", "fuera_de_rango", "no_circular", "perforado", "no_reconocida",
                                 "incoherente"]


def _correr(nombre: str):
    escenario = cargar_escenario(nombre)
    escena = EscenaEstacion()
    try:
        backend = EstacionBackendSim(escena, camara=CamaraOraculo(probabilidad_error=0.0))
        planta = PlantaSimulada(escena, backend, LineaMonedas(), EmbalajeVasos(), escenario, monedas_por_vaso=5)
        while not planta.terminado and planta.ticks < 300:
            planta.paso()
        obtenidos = [planta.destinos_finales.get(i) for i in planta.orden_ids]
        return obtenidos, [e.destino_esperado for e in escenario.elementos], planta
    finally:
        escena.cerrar()


def test_en_la_interfaz_queda_una_sola_prueba():
    """Usuario, 2026-09-26: una sola prueba con todo."""
    assert listar_escenarios() == ["prueba_completa"]
    for nombre in NOMBRES_ESCENARIOS_POR_FILTRO + ["mixto_20"]:
        assert cargar_escenario(nombre).elementos


@pytest.mark.parametrize("nombre", NOMBRES_ESCENARIOS_POR_FILTRO)
def test_escenario_de_un_filtro_aislado(nombre):
    obtenidos, esperados, _ = _correr(nombre)
    assert obtenidos == esperados


def test_escenario_mixto_20_cubre_las_seis_causas():
    obtenidos, esperados, planta = _correr("mixto_20")
    assert len(esperados) == 20 and obtenidos == esperados
    causas = {c.causa for c in planta.linea.registro._casillas.values() if c.causa is not None}
    assert causas == set(reglas.CAUSAS_VALIDAS)
    assert esperados.count(Destino.VASO) == 8
    assert esperados.count(Destino.RECHAZO) == 10   # una sola bandeja de rechazo
    assert esperados.count(Destino.VACIA) == 2
