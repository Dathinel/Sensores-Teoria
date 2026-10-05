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
    s.cerrar()


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
    s.cerrar()

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
        s.cerrar()


def test_cerrar_suelta_la_conexion_de_pybullet(tmp_path):
    """El supervisor dejaba abierta su conexion de PyBullet: `sim/mundo.py` dibuja en la conexion 0 y
    un supervisor olvidado le cambiaba los sensores al siguiente (se vio al ordenar las pruebas)."""
    import pybullet as p

    s = Supervisor(tmp_path / "c.db")
    s.aplicar_orden({"cmd": "iniciar", "escenario": "no_metalico"})
    cliente = s._escena.cliente
    assert p.isConnected(cliente)
    s.cerrar()
    assert not p.isConnected(cliente)
    s.cerrar()          # dos veces no falla


# ---------------------------------------------------------------------
# Revision 2026-09-28: ordenes mal formadas, lote con tope y modo real igual al contrato
# ---------------------------------------------------------------------


@pytest.mark.parametrize("orden", [
    {"cmd": "velocidad", "valor": "rapido"},
    {"cmd": "lote", "valor": "10.5"},
    {"cmd": "lote", "valor": [3]},
    ["hola"],
    "pausar",
])
def test_una_orden_mal_formada_no_tumba_el_supervisor(supervisor, orden):
    """Antes cualquiera de estas lanzaba una excepcion dentro de `vuelta` y mataba el bucle."""
    import json

    c = supervisor.conexion
    db.insertar_orden(c, {"cmd": "iniciar", "escenario": "prueba_completa"})
    c.execute("INSERT INTO ordenes (ts, comando) VALUES (?, ?)", (db.ahora(), json.dumps(orden)))
    db.insertar_orden(c, {"cmd": "pausar"})
    supervisor.vuelta()                                   # no lanza
    assert supervisor.estado_linea == PAUSADA             # la orden buena de despues si se cumplio
    respuestas = [json.loads(f[0]) for f in
                  c.execute("SELECT payload FROM eventos WHERE tipo = 'respuesta' ORDER BY id")]
    assert [r["ok"] for r in respuestas] == [True, False, True]   # iniciar, la mala, pausar
    assert supervisor.velocidad == 1.0


def test_el_lote_sin_corrida_tambien_se_recorta_a_la_capacidad_del_tubo(supervisor):
    """Antes, sin corrida abierta, un lote de 40 quedaba tal cual (tubo de 25: tubo_lleno eterno)."""
    capacidad = supervisor.parametros["planta"]["capacidad_tubo"]
    supervisor.aplicar_orden({"cmd": "lote", "valor": capacidad + 15})
    assert supervisor.parametros["planta"]["monedas_por_vaso"] == capacidad
    supervisor.iniciar("prueba_completa")
    assert supervisor.planta.monedas_por_vaso == capacidad


@pytest.fixture
def supervisor_real(tmp_path):
    """Modo `hardware.backend: real` sin placa: el puente usa la estacion emulada."""
    from app.configuracion import cargar_parametros

    p = cargar_parametros()
    p["hardware"] = {"backend": "real", "puerto": "COM_QUE_NO_EXISTE_99"}
    s = Supervisor(tmp_path / "real.db", parametros=p)
    reloj = [0]
    s._ms = lambda: reloj[0]
    s.reloj = reloj
    yield s
    s.cerrar()


def _correr_real(s, hasta_ms, paso=50):
    while s.reloj[0] < hasta_ms:
        s.reloj[0] += paso
        s.vuelta()


def test_real_reanudar_no_saca_del_paro(supervisor_real):
    """Igual que la simulacion: del PARO se sale con Iniciar, no con reanudar."""
    s = supervisor_real
    s.aplicar_orden({"cmd": "iniciar"})
    _correr_real(s, 1000)
    s.aplicar_orden({"cmd": "paro"})
    assert s.estado_linea == PARO
    s.aplicar_orden({"cmd": "reanudar"})
    assert s.estado_linea == PARO and s.ultima_orden["ok"] is False
    s.aplicar_orden({"cmd": "iniciar"})
    assert s.estado_linea == CORRIENDO


def test_real_pausa_y_reanuda(supervisor_real):
    s = supervisor_real
    s.aplicar_orden({"cmd": "iniciar"})
    _correr_real(s, 1000)
    s.aplicar_orden({"cmd": "pausar"})
    assert s.estado_linea == PAUSADA
    s.aplicar_orden({"cmd": "reanudar"})
    assert s.estado_linea == CORRIENDO and s.ultima_orden["ok"]


class _PuertoMudo:
    """Un ESP32 que dejo de contestar (cable suelto, placa colgada)."""
    in_waiting = 0

    def read(self, n):
        return b""

    def write(self, datos):
        pass

    def close(self):
        pass


def test_real_sin_esp32_pausa_la_linea(supervisor_real):
    """docs/especificacion.md 10.1: si el PC no oye al ESP32, pausa la linea y da la alarma sin_esp32 (antes solo
    la alarma: el dashboard seguia diciendo "corriendo")."""
    s = supervisor_real
    s.aplicar_orden({"cmd": "iniciar"})
    _correr_real(s, 1000)
    assert s.estado_linea == CORRIENDO
    s.puente.emulada, s.puente.ser = None, _PuertoMudo()
    _correr_real(s, 1000 + s.puente.latido.perdido_ms + 500)
    assert s.estado_linea == PAUSADA
    tel = db.ultima_telemetria(s.conexion)
    assert "sin_esp32" in tel["alarmas"] and tel["linea"] == PAUSADA
    # Sin la placa no se puede seguir.
    s.aplicar_orden({"cmd": "reanudar"})
    assert s.estado_linea == PAUSADA and s.ultima_orden["ok"] is False


def test_el_aviso_de_almacen_precargado_queda_en_la_base(supervisor):
    """Bug (2026-09-28): `precargar_almacen` emitia `almacen_precargado` antes
    del primer tick y el primer `paso()` vaciaba la lista: el aviso nunca
    llegaba a la tabla `eventos`. Ahora va con los eventos del arranque."""
    c = supervisor.conexion
    db.guardar_almacen_turno(c, [{"clase": "500_nueva", "valor": 500, "masa_g": 7.1},
                                 {"clase": "1000_nueva", "valor": 1000, "masa_g": 10.0}])
    db.insertar_orden(c, {"cmd": "iniciar", "escenario": "no_metalico", "conservar_almacen": True})
    supervisor.vuelta()
    supervisor.vuelta()
    assert supervisor.planta.almacen.cantidad(500) == 1
    filas = c.execute("SELECT payload FROM eventos WHERE tipo = 'almacen_precargado'").fetchall()
    assert len(filas) == 1 and '"cantidad": 2' in filas[0][0]


# ---------------------------------------------------------------------------
# Revision logica 2026-09-29 (modo real con la estacion emulada): cada prueba
# FALLABA antes del arreglo (docs/bitacora.md).
# ---------------------------------------------------------------------------


def test_real_parada_por_error_se_ve_con_su_motivo_y_sale_con_reanudar(supervisor_real):
    """Bug: con la linea CORRIENDO y la placa parada por un error del firmware,
    "reanudar" contestaba "no esta en pausa" (la unica salida era Iniciar, que
    borra la corrida) y la telemetria no decia el motivo."""
    s = supervisor_real
    s.aplicar_orden({"cmd": "iniciar"})
    _correr_real(s, 1000)
    est = s.puente.emulada.estacion
    est.aplicar_parada_segura("error", 1000)            # lo que hace main.py ante una excepcion
    _correr_real(s, 1600)
    tel = db.ultima_telemetria(s.conexion)
    assert tel["motivo_parada"] == "error" and "parada_segura" in tel["alarmas"]
    s.aplicar_orden({"cmd": "reanudar"})
    assert s.ultima_orden["ok"], s.ultima_orden
    _correr_real(s, 2200)
    assert not est.parada_segura
    assert db.ultima_telemetria(s.conexion)["motivo_parada"] is None


class _CableFlojo:
    """El cable USB de una estacion emulada que se puede cortar y volver a
    conectar: cortado, no pasa nada en ningun sentido (la placa sigue andando)."""

    def __init__(self, emulada):
        self.emulada = emulada
        self.cortado = False

    @property
    def in_waiting(self):
        if self.cortado:
            self.emulada._salida.clear()                # lo que la placa manda se pierde
            return 0
        return self.emulada.in_waiting

    def read(self, n):
        return b"" if self.cortado else self.emulada.read(n)

    def write(self, datos):
        if not self.cortado:
            self.emulada.write(datos)

    def close(self):
        pass


def test_real_pausa_por_sin_esp32_tambien_para_la_placa(supervisor_real):
    """Bug: `_pausar_si_no_oye_al_esp32` solo pausaba el PC. La placa, sin oir al
    PC, quedaba en parada "sin_pc", que se levanta SOLA con el latido: al volver
    el cable la placa quedaba lista mientras el PC decia PAUSADA."""
    s = supervisor_real
    s.aplicar_orden({"cmd": "iniciar"})
    _correr_real(s, 1000)
    cable = _CableFlojo(s.puente.emulada)
    s.puente.ser = cable
    cable.cortado = True
    _correr_real(s, 1000 + s.puente.latido.perdido_ms + 800)
    assert s.estado_linea == PAUSADA
    cable.cortado = False                               # vuelve el cable
    _correr_real(s, s.reloj[0] + 1500)
    est = s.puente.emulada.estacion
    assert est.parada_segura and est.motivo_parada == "pausa"
    assert db.ultima_telemetria(s.conexion)["motivo_parada"] == "pausa"
    s.aplicar_orden({"cmd": "reanudar"})
    _correr_real(s, s.reloj[0] + 300)
    assert s.estado_linea == CORRIENDO and not est.parada_segura


def test_real_en_pausa_no_pasan_actuadores_salvo_prueba_explicita(supervisor_real):
    s = supervisor_real
    s.aplicar_orden({"cmd": "iniciar"})
    _correr_real(s, 1000)
    s.aplicar_orden({"cmd": "pausar"})
    _correr_real(s, 1200)
    assert s.puente.emulada.estacion.motivo_parada == "pausa"
    antes = s.puente.emulada.hw.pasos["monedas"]
    s.aplicar_orden({"cmd": "hardware", "dst": "linea", "act": "avanzar"})
    assert s.ultima_orden["ok"] is False and "pausa" in s.ultima_orden["detalle"]
    s.aplicar_orden({"cmd": "carro", "accion": "avanzar", "distancia_m": 0.2})
    assert s.ultima_orden["ok"] is False
    s.aplicar_orden({"cmd": "carro", "accion": "detener"})     # detener el carro, siempre
    assert s.ultima_orden["ok"] is True
    s.aplicar_orden({"cmd": "hardware", "dst": "linea", "act": "avanzar", "prueba": True})
    assert s.ultima_orden["ok"] is True                        # la prueba explicita se manda...
    _correr_real(s, 1400)
    assert s.puente.emulada.hw.pasos["monedas"] == antes      # ...y la placa en pausa no la ejecuta
