"""Prueba de UN filtro y "colocar pieza X" desde la interfaz (usuario, 2026-09-27): el enunciado
dice que los filtros se prueban uno por uno en la sustentacion."""

import json

import pytest

from app import db
from app.supervisor import CORRIENDO, TERMINADA, Supervisor
from sim.carga_escenarios import PIEZAS, PRUEBAS_DE_UN_FILTRO, especificacion_pieza


@pytest.fixture
def supervisor(tmp_path):
    from app.configuracion import cargar_parametros

    p = cargar_parametros()
    p["simulacion"]["errores_sensores"] = False   # causas exactas
    p["simulacion"]["carro"] = "reemplazo"
    p["planta"]["conservar_almacen_entre_turnos"] = False
    s = Supervisor(tmp_path / "planta.db", parametros=p)
    yield s
    s.conexion.close()


def _hasta_terminar(s, max_vueltas=400):
    s.vuelta()
    for _ in range(max_vueltas):
        if s.estado_linea == TERMINADA:
            return
        s.vuelta()
    raise AssertionError("la corrida no termino")


def _respuestas(s):
    return [json.loads(f["payload"]) for f in s.conexion.execute(
        "SELECT payload FROM eventos WHERE tipo = 'respuesta' ORDER BY id")]


@pytest.mark.parametrize("prueba", PRUEBAS_DE_UN_FILTRO, ids=[p["escenario"] for p in PRUEBAS_DE_UN_FILTRO])
def test_cada_prueba_rechaza_por_su_causa(supervisor, prueba):
    db.insertar_orden(supervisor.conexion, {"cmd": "iniciar", "escenario": prueba["escenario"]})
    _hasta_terminar(supervisor)
    causas = [f["causa"] for f in supervisor.conexion.execute("SELECT causa FROM elementos WHERE veredicto != 'vacia'")]
    assert causas and set(causas) == {prueba["causa"]}
    assert _respuestas(supervisor)[-1]["detalle"] == f"Prueba de un filtro: {prueba['nombre']}"
    tel = db.ultima_telemetria(supervisor.conexion)
    assert [p["escenario"] for p in tel["pruebas_filtro"]] == [p["escenario"] for p in PRUEBAS_DE_UN_FILTRO]


def test_un_escenario_que_no_existe_no_se_abre(supervisor):
    db.insertar_orden(supervisor.conexion, {"cmd": "iniciar", "escenario": "../../config/parametros"})
    supervisor.vuelta()
    r = _respuestas(supervisor)[-1]
    assert r["ok"] is False and "desconocido" in r["detalle"]


def test_todas_las_piezas_se_pueden_construir():
    for pieza in PIEZAS:
        especificacion_pieza(pieza)
    with pytest.raises(ValueError):
        especificacion_pieza("no_existe")


def test_colocar_pieza_va_en_la_proxima_carga_y_reanuda(supervisor):
    db.insertar_orden(supervisor.conexion, {"cmd": "iniciar", "escenario": "no_metalico"})
    _hasta_terminar(supervisor)
    antes = supervisor.conexion.execute("SELECT COUNT(*) FROM elementos").fetchone()[0]
    db.insertar_orden(supervisor.conexion, {"cmd": "colocar", "pieza": "500_nueva"})
    supervisor.vuelta()
    assert supervisor.estado_linea == CORRIENDO
    assert "va en la próxima carga" in _respuestas(supervisor)[-1]["detalle"]
    _hasta_terminar(supervisor)
    ultima = supervisor.conexion.execute("SELECT veredicto, denominacion FROM elementos ORDER BY id DESC").fetchone()
    assert supervisor.conexion.execute("SELECT COUNT(*) FROM elementos").fetchone()[0] == antes + 1
    assert ultima["veredicto"] == "aceptada" and ultima["denominacion"] == 500


def test_colocar_una_pieza_desconocida_se_rechaza(supervisor):
    db.insertar_orden(supervisor.conexion, {"cmd": "iniciar", "escenario": "no_metalico"})
    supervisor.vuelta()
    db.insertar_orden(supervisor.conexion, {"cmd": "colocar", "pieza": "tornillo"})
    supervisor.vuelta()
    assert _respuestas(supervisor)[-1]["ok"] is False
