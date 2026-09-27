"""Pruebas del supervisor (fase 4): consume ordenes de la tabla `ordenes`
y deja en SQLite lo que el dashboard necesita leer."""

import pytest

from app import db
from app.supervisor import CORRIENDO, PARO, PAUSADA, TERMINADA, Supervisor


@pytest.fixture
def supervisor(tmp_path):
    from app.configuracion import cargar_parametros

    parametros = cargar_parametros()
    parametros["simulacion"]["errores_sensores"] = False  # cifras exactas
    parametros["simulacion"]["carro"] = "reemplazo"         # el carro fisico tiene sus propias pruebas
    # Las cifras de abajo son con lotes de 5 y tubos vacios al arrancar,
    # sin importar lo que el grupo tenga hoy en config/parametros.yaml.
    parametros["planta"]["monedas_por_vaso"] = 5
    parametros["planta"]["conservar_almacen_entre_turnos"] = False
    s = Supervisor(tmp_path / "planta.db", parametros=parametros)
    yield s
    s.conexion.close()


def _hasta_terminar(s, max_vueltas=300):
    s.vuelta()  # consume la orden pendiente aunque la corrida anterior ya haya terminado
    for _ in range(max_vueltas):
        if s.estado_linea == TERMINADA:
            return
        s.vuelta()


def test_sin_orden_la_linea_no_arranca(supervisor):
    supervisor.vuelta()
    assert supervisor.estado_linea == "detenida"
    assert db.ultima_telemetria(supervisor.conexion)["linea"] == "detenida"


def test_corrida_completa_llena_las_tablas(supervisor):
    db.insertar_orden(supervisor.conexion, {"cmd": "iniciar", "escenario": "mixto_20"})
    _hasta_terminar(supervisor)
    c = supervisor.conexion
    assert supervisor.estado_linea == TERMINADA
    assert c.execute("SELECT COUNT(*) FROM elementos").fetchone()[0] == 18  # 20 menos 2 vacias
    assert c.execute("SELECT SUM(valor) FROM elementos WHERE veredicto = 'aceptada'").fetchone()[0] == 2500
    causas = {f[0] for f in c.execute("SELECT DISTINCT causa FROM elementos WHERE causa IS NOT NULL")}
    assert len(causas) == 6
    tel = db.ultima_telemetria(c)
    assert tel["linea"] == TERMINADA and len(tel["casillas_monedas"]) == 4  # filtro total: 4 estaciones


def test_produccion_llena_vasos_de_una_denominacion(supervisor):
    db.insertar_orden(supervisor.conexion, {"cmd": "iniciar", "escenario": "prueba_completa"})
    _hasta_terminar(supervisor)
    c = supervisor.conexion
    filas = c.execute("SELECT denominacion, cantidad_monedas, valor_total FROM vasos WHERE estado = 'entregada'").fetchall()
    assert sorted(f["denominacion"] for f in filas) == [50, 100, 200, 500]
    assert all(f["valor_total"] == f["denominacion"] * f["cantidad_monedas"] for f in filas)
    tel = db.ultima_telemetria(c)
    assert tel["almacen"] == {"50": 0, "100": 0, "200": 0, "500": 1, "1000": 3, "otras": 0}
    # Fin de turno: embalar lo que quedo guardado.
    db.insertar_orden(c, {"cmd": "embalar_parciales"})
    _hasta_terminar(supervisor)
    assert db.ultima_telemetria(c)["almacen_valor"] == 0


def test_pausar_reanudar_y_paro(supervisor):
    c = supervisor.conexion
    db.insertar_orden(c, {"cmd": "iniciar", "escenario": "mixto_20"})
    supervisor.vuelta()
    assert supervisor.estado_linea == CORRIENDO

    db.insertar_orden(c, {"cmd": "pausar"})
    supervisor.vuelta()
    tick = supervisor.planta.ticks
    supervisor.vuelta()
    assert supervisor.estado_linea == PAUSADA and supervisor.planta.ticks == tick

    db.insertar_orden(c, {"cmd": "reanudar"})
    supervisor.vuelta()
    assert supervisor.estado_linea == CORRIENDO and supervisor.planta.ticks == tick + 1

    db.insertar_orden(c, {"cmd": "paro"})
    supervisor.vuelta()
    supervisor.vuelta()
    assert supervisor.estado_linea == PARO and supervisor.planta.ticks == tick + 1
    # Del paro no se sale con "reanudar", solo con una corrida nueva.
    db.insertar_orden(c, {"cmd": "reanudar"})
    supervisor.vuelta()
    assert supervisor.estado_linea == PARO


def test_iniciar_de_nuevo_borra_la_corrida_anterior(supervisor):
    c = supervisor.conexion
    db.insertar_orden(c, {"cmd": "iniciar", "escenario": "mixto_20"})
    _hasta_terminar(supervisor)
    db.insertar_orden(c, {"cmd": "iniciar", "escenario": "no_metalico"})
    _hasta_terminar(supervisor)
    causas = {f[0] for f in c.execute("SELECT DISTINCT causa FROM elementos WHERE causa IS NOT NULL")}
    assert causas == {"no_metalico"}


def test_umbral_de_confianza_desde_el_dashboard(supervisor):
    """Con un umbral por encima de la confianza del oraculo (0.95), ninguna
    moneda se acepta: todo sale como no_reconocida."""
    db.insertar_orden(supervisor.conexion, {"cmd": "iniciar", "escenario": "mixto_20", "confianza_minima": 0.99})
    _hasta_terminar(supervisor)
    c = supervisor.conexion
    assert c.execute("SELECT COUNT(*) FROM elementos WHERE veredicto = 'aceptada'").fetchone()[0] == 0


def test_lote_se_cambia_en_caliente(supervisor):
    """Punto 9: las monedas por vaso dependen de cuantas traiga el profesor
    ese dia; se cambian desde el dashboard sin reiniciar la corrida."""
    c = supervisor.conexion
    db.insertar_orden(c, {"cmd": "iniciar", "escenario": "prueba_completa"})
    supervisor.vuelta()
    db.insertar_orden(c, {"cmd": "lote", "valor": 3})
    supervisor.vuelta()
    assert supervisor.planta.monedas_por_vaso == 3
    assert db.ultima_telemetria(c)["monedas_por_vaso"] == 3
    # Fuera de rango se recorta a la capacidad de un tubo.
    db.insertar_orden(c, {"cmd": "lote", "valor": 999})
    supervisor.vuelta()
    assert supervisor.planta.monedas_por_vaso == supervisor.parametros["planta"]["capacidad_tubo"]
    _hasta_terminar(supervisor)
    cantidades = {f[0] for f in c.execute("SELECT cantidad_monedas FROM vasos WHERE estado = 'entregada'")}
    assert cantidades <= {3}  # los que se llenaron alcanzaron a salir con lote de 3


def test_turno_nuevo_arranca_con_lo_guardado(supervisor):
    """Punto 9: lo que no se empaco al final del turno sigue en los tubos
    cuando arranca el siguiente (tabla almacen_turno)."""
    c = supervisor.conexion
    db.insertar_orden(c, {"cmd": "iniciar", "escenario": "prueba_completa"})
    _hasta_terminar(supervisor)
    guardado = db.ultima_telemetria(c)["almacen"]
    assert guardado["500"] == 1 and guardado["1000"] == 3

    db.insertar_orden(c, {"cmd": "iniciar", "escenario": "no_metalico", "conservar_almacen": True})
    supervisor.vuelta()
    assert supervisor.planta.almacen.cantidad(500) == 1
    assert supervisor.planta.almacen.cantidad(1000) == 3

    # Sin conservar, el turno arranca con los tubos vacios.
    db.insertar_orden(c, {"cmd": "iniciar", "escenario": "no_metalico", "conservar_almacen": False})
    supervisor.vuelta()
    assert supervisor.planta.almacen.total() == 0


def test_cada_boton_responde_si_hizo_algo_o_por_que_no(supervisor):
    """Usuario, 2026-09-26: "unos botones funcionan y otros no". Cada orden
    queda respondida (ultima_orden: ok + detalle), tambien cuando no puede
    hacer nada (por ejemplo, no hay un vaso donde el sabotaje lo necesita)."""
    s = supervisor
    s.aplicar_orden({"cmd": "pausar"})
    assert s.ultima_orden["ok"] is False and "no está corriendo" in s.ultima_orden["detalle"]
    s.aplicar_orden({"cmd": "iniciar", "escenario": "prueba_completa"})
    assert s.ultima_orden["ok"] is True
    for _ in range(12):
        s.tick()
    vistos = {}
    for tipo in ("mano_carga", "vaso_con_algo", "retirar_vaso", "cambiar_vaso", "vaso_igual", "mano_saca_vaso",
                 "intruso_on", "intruso_on", "intruso_off", "intruso_off", "mano_llenado"):
        s.aplicar_orden({"cmd": "sabotaje", "tipo": tipo})
        r = s.ultima_orden
        assert r["tipo"] == tipo and isinstance(r["ok"], bool) and r["detalle"]
        vistos.setdefault(tipo, []).append(r["ok"])
        s.tick()
    assert vistos["intruso_on"] == [True, False] and vistos["intruso_off"] == [True, False]
    assert vistos["mano_carga"] == [True] and vistos["vaso_con_algo"] == [True]
    s.aplicar_orden({"cmd": "pausar"})
    assert s.ultima_orden["ok"] is True
    s.aplicar_orden({"cmd": "sabotaje", "tipo": "retirar_vaso"})
    assert s.ultima_orden["ok"] is False and "no está corriendo" in s.ultima_orden["detalle"]
    s.aplicar_orden({"cmd": "reanudar"})
    assert s.ultima_orden["ok"] is True


def test_ordenes_al_carro_van_por_la_radio(tmp_path):
    """Fase 7: la orden del asistente (o de un boton) llega al carro fisico
    por la radio; sin radio, no llega; con el carro de reemplazo, se explica."""
    from app.configuracion import cargar_parametros

    p = cargar_parametros()
    p["simulacion"]["carro"] = "reemplazo"
    s = Supervisor(tmp_path / "r.db", parametros=p)
    s.aplicar_orden({"cmd": "carro", "accion": "avanzar", "distancia_m": 0.2})
    assert s.ultima_orden["ok"] is False and "No hay corrida" in s.ultima_orden["detalle"]
    s.aplicar_orden({"cmd": "iniciar"})
    s.aplicar_orden({"cmd": "carro", "accion": "avanzar", "distancia_m": 0.2})
    assert s.ultima_orden["ok"] is False and "reemplazo" in s.ultima_orden["detalle"]
    s.conexion.close()

    p = cargar_parametros()
    p["simulacion"]["carro"] = "fisico"
    s = Supervisor(tmp_path / "f.db", parametros=p)
    try:
        s.aplicar_orden({"cmd": "iniciar"})
        s.aplicar_orden({"cmd": "sabotaje", "tipo": "radio_off"})
        s.aplicar_orden({"cmd": "carro", "accion": "girar", "grados": 90, "origen": "asistente"})
        assert s.ultima_orden["ok"] is False and "radio" in s.ultima_orden["detalle"]
        s.aplicar_orden({"cmd": "sabotaje", "tipo": "radio_on"})
        s.aplicar_orden({"cmd": "carro", "accion": "girar", "grados": 90, "origen": "asistente"})
        assert s.ultima_orden["ok"] is True and s.ultima_orden["origen"] == "asistente"
        for _ in range(6):
            s.tick()
        eventos = [f["tipo"] for f in s.conexion.execute("SELECT tipo FROM eventos WHERE origen = 'carro'")]
        assert "orden" in eventos and "orden_cumplida" in eventos
        # Cada respuesta queda como evento (el asistente muestra que paso).
        n = s.conexion.execute("SELECT COUNT(*) FROM eventos WHERE tipo = 'respuesta'").fetchone()[0]
        assert n >= 4
    finally:
        s.planta.cerrar()
        s.conexion.close()
