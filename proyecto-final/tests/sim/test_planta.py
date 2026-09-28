"""Pruebas de la planta integrada (sim/planta.py): las dos cintas funcionando
juntas con el almacen por denominacion, incluidos los sabotajes de la
seccion 2 disparados a mitad de corrida. Modo DIRECT, oraculo sin ruido.

Reglas del grupo que se verifican aqui:
- ninguna moneda colombiana aceptada se descarta (esta en un vaso o
  guardada en su tubo);
- cada vaso lleva UNA sola denominacion;
- una figura o un vaso retirado nunca reciben monedas.
"""

import pytest

from control.embalaje import EmbalajeVasos
from control.hal.backend_sim import EstacionBackendSim
from control.linea import Destino, LineaMonedas
from sim.sensores_sim import CamaraOraculo
from sim.carga_escenarios import cargar_escenario
from sim.mundo import EscenaEstacion
from sim.planta import PlantaSimulada

LOTE = 5


@pytest.fixture
def crear_planta():
    escenas = []

    def _crear(nombre="prueba_completa", lote=LOTE):
        escena = EscenaEstacion()
        escenas.append(escena)
        backend = EstacionBackendSim(escena, camara=CamaraOraculo(probabilidad_error=0.0))
        return PlantaSimulada(escena, backend, LineaMonedas(), EmbalajeVasos(), cargar_escenario(nombre),
                              monedas_por_vaso=lote)

    yield _crear
    for e in escenas:
        e.cerrar()


def _correr(planta, sabotajes=None, max_ticks=300):
    """`sabotajes`: {tick: funcion(planta)} que se ejecuta antes de ese tick."""
    eventos = []
    sabotajes = sabotajes or {}
    while not planta.terminado and planta.ticks < max_ticks:
        if planta.ticks in sabotajes:
            sabotajes[planta.ticks](planta)
        eventos.extend(planta.paso())
    return eventos


def _destinos(planta):
    return [planta.destinos_finales.get(i) for i in planta.orden_ids]


def _embalados(eventos):
    return [e for e in eventos if e["ev"] == "embalado"]


def _conservacion(planta, eventos):
    """Valor aceptado == valor en vasos (entregados o no) + valor en tubos."""
    aceptado = sum(e["valor"] for e in eventos if e["ev"] == "elemento_final" and e["destino"] == Destino.VASO)
    en_vasos = sum(e["valor"] for e in _embalados(eventos))
    return aceptado, en_vasos + planta.almacen.valor_total()


def test_cada_elemento_llega_a_su_destino(crear_planta):
    planta = crear_planta()
    _correr(planta)
    assert planta.terminado
    assert _destinos(planta) == [e.destino_esperado for e in planta.escenario.elementos]


def test_cada_vaso_lleva_una_sola_denominacion(crear_planta):
    planta = crear_planta()
    eventos = _correr(planta)
    embalados = _embalados(eventos)
    assert len(embalados) == 4
    assert sorted(e["denominacion"] for e in embalados) == [50, 100, 200, 500]
    for e in embalados:
        assert e["cantidad"] == LOTE and e["valor"] == LOTE * e["denominacion"]
    assert set(planta.vasos_finales.values()) <= {"entrega", "vacio"}
    # La cinta de vasos termina vacia: la corrida siguiente arranca de cero.
    assert planta.estado()["casillas_vasos"] == [None] * 5


def test_ninguna_moneda_aceptada_se_pierde(crear_planta):
    planta = crear_planta()
    eventos = _correr(planta)
    aceptado, guardado = _conservacion(planta, eventos)
    assert aceptado == guardado
    # Lo que no completo lote queda en su tubo, no se descarta. Las de series
    # viejas no llegan a "otras" mientras el modelo no las conozca (TEMPORAL:
    # salen como no_reconocida a la cubeta 2).
    assert planta.almacen.contenido()[1000] == 3 and planta.almacen.contenido()[500] == 1
    assert planta.almacen.cantidad_otras() == 0


def test_embalar_parciales_al_final_vacia_los_tubos(crear_planta):
    planta = crear_planta()
    eventos = _correr(planta)
    planta.pedir_embalar_parciales()
    eventos += _correr(planta)
    assert planta.almacen.total() == 0
    parciales = [e for e in _embalados(eventos) if e["cantidad"] < LOTE]
    assert sorted((str(e["denominacion"]), e["cantidad"]) for e in parciales) == [("1000", 3), ("500", 1)]


def test_mano_en_la_carga_sale_por_rechazo(crear_planta):
    planta = crear_planta()
    eventos = _correr(planta)
    manos = [i for i in planta.orden_ids if planta._tipo_real.get(i) == "mano"]
    assert len(manos) == 2
    for i in manos:
        assert planta.destinos_finales[i] == Destino.RECHAZO
    # El infrarrojo SI la vio (casilla registrada como ocupada).
    assert all(e["ocupada"] for e in eventos if e["ev"] == "presencia" and e["casilla"] in manos)


def test_figura_en_llenado_no_recibe_monedas(crear_planta):
    """El caso de la captura del usuario: cambian el vaso de llenado por una
    figura. La camara de vasos lo detecta en llenado antes de abrir la compuerta."""
    planta = crear_planta()
    eventos = _correr(planta, {3: lambda p: p.sabotaje_cambiar_vaso()})
    detectado = [e for e in eventos if e["ev"] == "sabotaje_detectado"]
    assert detectado and detectado[0]["estacion"] == "llenado"
    id_figura = detectado[0]["vaso"]
    assert not any(e["vaso"] == id_figura for e in _embalados(eventos))
    assert planta.vasos_finales[id_figura] == "rechazo"
    aceptado, guardado = _conservacion(planta, eventos)
    assert aceptado == guardado


def test_vaso_retirado_en_llenado_no_recibe_monedas(crear_planta):
    planta = crear_planta()
    eventos = _correr(planta, {3: lambda p: p.sabotaje_retirar_vaso()})
    detectado = [e for e in eventos if e["ev"] == "sabotaje_detectado"]
    assert detectado
    assert not any(e["vaso"] == detectado[0]["vaso"] for e in _embalados(eventos))
    assert len(_embalados(eventos)) == 4  # la linea siguio: salto de casilla, sin paro


def test_vaso_cambiado_despues_de_llenarse_no_recibe_tapa(crear_planta):
    """Si lo cambian cuando ya tiene su lote (entre llenado y tapa), lo
    detecta la re-verificacion de la estacion de tapa."""
    planta = crear_planta()
    eventos = []
    cambiado = False
    while not planta.terminado and planta.ticks < 300:
        nuevos = planta.paso()
        eventos += nuevos
        if not cambiado and any(e["ev"] == "embalado" for e in nuevos):
            planta.sabotaje_cambiar_vaso()
            cambiado = True
    detectados = [e for e in eventos if e["ev"] == "sabotaje_detectado"]
    assert any(e.get("motivo") == "figura_distinta" for e in detectados)
    vaso = next(e["vaso"] for e in detectados if e.get("motivo") == "figura_distinta")
    assert not any(e["ev"] == "tapa" and e["vaso"] == vaso and e["tapado"] for e in eventos)
    assert planta.vasos_finales[vaso] == "rechazo"


def test_mano_en_la_cortina_congela_vasos_pero_no_monedas(crear_planta):
    planta = crear_planta()
    eventos = _correr(planta, {8: lambda p: p.sabotaje_poner_intruso(), 16: lambda p: p.sabotaje_quitar_intruso()})
    cortina = [e for e in eventos if e["ev"] == "cortina"]
    assert [e["activa"] for e in cortina] == [True, False]
    inicio, fin = cortina[0]["tick"], cortina[1]["tick"]
    assert not any(e["ev"] == "paso" and e["src"] == "vasos" and inicio <= e["tick"] < fin for e in eventos)
    assert any(e["ev"] == "paso" and e["src"] == "linea" and inicio <= e["tick"] < fin for e in eventos)
    assert planta.terminado
    assert _destinos(planta) == [e.destino_esperado for e in planta.escenario.elementos]


def test_ids_de_registro_no_se_reciclan_al_borrar_cuerpos(crear_planta):
    """PyBullet reutiliza body_id al borrar cuerpos; el registro no."""
    planta = crear_planta()
    _correr(planta, {3: lambda p: p.sabotaje_retirar_vaso()})
    assert planta.orden_ids == list(range(1, len(planta.escenario.elementos) + 1))


def test_escenarios_de_filtros_siguen_iguales(crear_planta):
    planta = crear_planta("mixto_20", lote=3)
    _correr(planta)
    assert _destinos(planta) == [e.destino_esperado for e in planta.escenario.elementos]


def test_con_errores_de_sensor_ninguna_moneda_se_pierde_y_votar_ayuda():
    """Con el error individual de cada sensor encendido (config), la linea
    se equivoca a veces -- pero ninguna moneda aceptada desaparece, y leer 3
    veces por decision (voto de mayoria) no empeora nada respecto a 1."""
    from app.configuracion import cargar_parametros

    import copy

    errores = copy.deepcopy(cargar_parametros()["errores_sensores"])
    # El voto por lecturas es para los sensores discretos; el error del
    # clasificador (que no se vota asi) se apaga para medir solo lo que el
    # voto puede mejorar.
    errores["camara"]["probabilidad_error_clase"] = 0.0
    errores["camara"]["probabilidad_confusion_clase"] = 0.0
    escenario = cargar_escenario("prueba_completa")
    base = EscenaEstacion()
    try:
        conteo = {}
        for lecturas in (1, 3):
            conteo[lecturas] = 0
            for semilla in range(12):
                escena = EscenaEstacion(reusar_cliente=base.cliente)
                backend = EstacionBackendSim(escena, camara=CamaraOraculo())
                backend.aplicar_errores(errores, semilla)
                planta = PlantaSimulada(escena, backend, LineaMonedas(), EmbalajeVasos(), escenario,
                                        monedas_por_vaso=LOTE, lecturas_por_decision=lecturas)
                eventos = _correr(planta)
                aceptado, guardado = _conservacion(planta, eventos)
                assert aceptado == guardado
                assert not planta.errores_filtrado["falsas_aceptaciones"]
                conteo[lecturas] += len(planta.errores_filtrado["falsos_rechazos"])
        assert conteo[3] <= conteo[1]
    finally:
        base.cerrar()


# ---------------------------------------------------------------------------
# filtro total (grupo, 2026-09-25): una sola salida de rechazo
# ---------------------------------------------------------------------------


def test_todo_rechazo_va_a_la_misma_bandeja_con_su_causa(crear_planta):
    """Sin expulsores: todo lo que no es una moneda aceptada llega a la
    descarga y la compuerta de desvio lo manda a la unica bandeja. Cada
    rechazo conserva su causa (asi se demuestran los filtros por separado)."""
    from control.almacen import OTRAS

    planta = crear_planta("mixto_20")
    eventos = _correr(planta)
    rechazos = [e for e in eventos if e["ev"] == "elemento_final" and e["destino"] == Destino.RECHAZO]
    assert len(rechazos) == 10
    assert {e["causa"] for e in rechazos} == {"no_metalico", "fuera_de_rango", "no_circular", "perforado",
                                               "no_reconocida", "incoherente"}
    assert len(planta.salidas[Destino.RECHAZO]) == 10
    assert planta.almacen.cantidad(OTRAS) == 0


def test_familias_no_entrenadas_salen_como_no_reconocidas(crear_planta):
    """TEMPORAL (grupo, 2026-09-22): sin piezas de las series muy_antigua e
    historica no hay fotos para entrenar el modelo; esas monedas salen como
    no_reconocida y van a la bandeja de rechazo."""
    planta = crear_planta()
    eventos = _correr(planta)
    viejas = [e for e in eventos if e["ev"] == "presencia"
              and e.get("clase_real") in ("20_historica", "10_muy_antigua")]
    assert len(viejas) == 2
    for e in viejas:
        final = next(x for x in eventos if x["ev"] == "elemento_final" and x["casilla"] == e["casilla"])
        assert final["causa"] == "no_reconocida" and final["destino"] == Destino.RECHAZO


# --- punto 8: identidad del vaso (marcador ArUco) y posicion de las cintas ---


def test_vaso_igual_en_llenado_no_recibe_monedas(crear_planta):
    """Lo cambian por otro vaso del MISMO tamano: la silueta lo da por
    bueno, pero el marcador ya no es el de la verificacion."""
    planta = crear_planta()
    eventos = _correr(planta, {3: lambda p: p.sabotaje_cambiar_por_vaso_igual()})
    detectado = [e for e in eventos if e["ev"] == "sabotaje_detectado"]
    assert detectado and detectado[0]["motivo"] == "vaso_cambiado"
    assert not any(e["vaso"] == detectado[0]["vaso"] for e in _embalados(eventos))
    aceptado, guardado = _conservacion(planta, eventos)
    assert aceptado == guardado


def test_vaso_igual_despues_de_llenarse_no_recibe_tapa(crear_planta):
    planta = crear_planta()
    eventos = []
    cambiado = False
    while not planta.terminado and planta.ticks < 300:
        nuevos = planta.paso()
        eventos += nuevos
        if not cambiado and any(e["ev"] == "embalado" for e in nuevos):
            planta.sabotaje_cambiar_por_vaso_igual()
            cambiado = True
    detectados = [e for e in eventos if e["ev"] == "sabotaje_detectado" and e.get("motivo") == "vaso_cambiado"]
    assert detectados and detectados[0]["estacion"] == "tapa"
    vaso = detectados[0]["vaso"]
    assert not any(e["ev"] == "tapa" and e["vaso"] == vaso and e["tapado"] for e in eventos)
    assert planta.vasos_finales[vaso] == "rechazo"


def test_si_la_camara_de_vasos_no_lee_el_marcador_decide_la_silueta(crear_planta):
    """Sin lecturas del marcador no hay evidencia de cambio: la linea sigue
    igual que siempre (no se para ni rechaza vasos buenos)."""
    base = crear_planta()
    _correr(base)
    planta = crear_planta()
    planta.backend.camara_vasos.probabilidad_no_lee = 1.0
    _correr(planta)
    assert planta.vasos_finales == base.vasos_finales


def test_desfase_de_la_cinta_se_detecta_y_no_cambia_el_resultado(crear_planta):
    import random

    base = crear_planta()
    _correr(base)
    planta = crear_planta()
    for sensor in (planta.backend.posicion_monedas, planta.backend.posicion_vasos):
        sensor.probabilidad_desfase = 0.2
        sensor.rng = random.Random(3)
    eventos = _correr(planta)
    assert planta.desfases["monedas"] > 0 and planta.desfases["vasos"] > 0
    assert sum(e["ev"] == "desfase_corregido" for e in eventos) == sum(planta.desfases.values())
    assert _destinos(planta) == _destinos(base)


# ---------------------------------------------------------------------------
# revision 2026-09-25: mano que saca un vaso, fondo del vaso, alarmas
# ---------------------------------------------------------------------------


def test_mano_que_saca_un_vaso_dispara_la_cortina_y_se_detecta(crear_planta):
    """Alguien mete la mano a media altura y se lleva el vaso de prensa (o
    tapa): la cortina congela la zona y, al despejarse, la camara encuentra
    el vaso que falta; ese vaso no se cuenta como entregado."""
    planta = crear_planta()
    eventos = []
    sacado = None
    for _ in range(400):
        if planta.terminado:
            break
        eventos += planta.paso()
        if sacado is None and planta.ticks > 30:
            sacado = planta.sabotaje_mano_saca_vaso()
    assert sacado is not None
    assert any(e["ev"] == "cortina" and e["activa"] for e in eventos)
    detectado = [e for e in eventos if e["ev"] == "sabotaje_detectado" and e["vaso"] == sacado]
    assert detectado and detectado[0]["motivo"] in ("retirado_con_mano", "retirado")
    assert planta.vasos_finales[sacado] == "rechazo"


def test_vaso_con_algo_adentro_lo_detecta_el_sensor_del_interior(crear_planta):
    """Los vasos son opacos: un vaso que ya trae algo se ve igual por fuera.
    El sensor que mira al interior del vaso lo ve en la verificacion: no se
    llena y sale por rechazo."""
    planta = crear_planta()
    eventos = []
    for _ in range(400):
        if planta.terminado:
            break
        if planta.ticks == 10:
            planta.sabotaje_vaso_con_contenido()
        eventos += planta.paso()
    detectados = [e for e in eventos if e["ev"] == "sabotaje_detectado" and e.get("motivo") == "vaso_con_contenido"]
    assert len(detectados) == 1 and detectados[0]["estacion"] == "verificacion"
    vaso = detectados[0]["vaso"]
    assert not any(e["ev"] == "embalado" and e["vaso"] == vaso for e in eventos)
    assert planta.vasos_finales[vaso] == "rechazo"


def test_canaleta_llena_detiene_la_cinta_de_vasos_y_no_la_de_monedas(crear_planta):
    """Punto 12: si el carro no viene, el vaso tapado espera en la descarga y
    la cinta de vasos se detiene; las monedas se siguen guardando."""
    planta = crear_planta()
    planta.capacidad_canaleta = 1
    planta.carro_retira_cada_ticks = 10_000   # el carro nunca llega
    eventos = []
    for _ in range(120):
        eventos += planta.paso()
    assert any(e["ev"] == "canaleta_llena" for e in eventos)
    assert len(planta.canaleta) == 1
    assert planta.estado()["vaso_esperando_canaleta"] is not None
    # la cinta de monedas siguio: casi todo el escenario ya entro
    assert len(planta._pendientes) < 5


# ---------------------------------------------------------------------------
# punto 11 (usuario, 2026-09-26): un solo sensor en la cortina, la prensa
# sube, y la camara vigila en cada tick que no falte ningun vaso
# ---------------------------------------------------------------------------


def test_la_cortina_sube_la_prensa_y_la_deja_detenida(crear_planta):
    planta = crear_planta()
    eventos = _correr(planta, {8: lambda p: p.sabotaje_poner_intruso(), 16: lambda p: p.sabotaje_quitar_intruso()})
    activa = [e for e in eventos if e["ev"] == "cortina" and e["activa"]]
    assert activa and activa[0]["prensa"] == "arriba"
    assert planta.backend.prensa.subidas == 1
    inicio, fin = activa[0]["tick"], next(e["tick"] for e in eventos if e["ev"] == "cortina" and not e["activa"])
    assert not any(e["ev"] == "prensa" and inicio <= e["tick"] < fin for e in eventos)


def test_la_camara_ve_un_vaso_sacado_sin_cruzar_la_cortina(crear_planta):
    """Alguien saca el vaso de prensa (o tapa) por encima, sin cortar el haz:
    la cortina no se entera, pero la camara ve la casilla sin su vaso en los
    ticks siguientes y lo invalida."""
    from sim.mundo import ESTACION_PRENSA_VASOS, ESTACION_TAPA_VASOS

    planta = crear_planta()
    eventos = []
    sacado = None
    for _ in range(300):
        if planta.terminado:
            break
        eventos += planta.paso()
        if sacado is None and planta.ticks > 30:
            for casilla in (ESTACION_PRENSA_VASOS, ESTACION_TAPA_VASOS):
                id_vaso = planta._vaso_en(casilla)
                if id_vaso is not None and planta._vasos[id_vaso][0] is not None:
                    planta.escena.retirar_vaso(planta._vasos[id_vaso][0])
                    planta._vasos[id_vaso][0] = None
                    sacado, tick_sacado = id_vaso, planta.ticks
                    break
    assert sacado is not None
    assert not any(e["ev"] == "cortina" for e in eventos)
    detectado = [e for e in eventos if e["ev"] == "sabotaje_detectado" and e["vaso"] == sacado]
    assert detectado[0]["estacion"] == "camara" and detectado[0]["motivo"] == "retirado"
    assert detectado[0]["tick"] == tick_sacado + 1
    assert planta.vasos_finales[sacado] == "rechazo"


def test_la_vigilancia_de_la_camara_no_invalida_vasos_por_error_de_sensor():
    """Con el error normal de la camara de vasos, revisar las 4 casillas en
    cada tick no debe dar por retirado un vaso que sigue ahi (un "no esta"
    se confirma con un segundo voto de cuadros nuevos)."""
    from app.configuracion import cargar_parametros

    errores = cargar_parametros()["errores_sensores"]
    escenario = cargar_escenario("prueba_completa")
    base = EscenaEstacion()
    try:
        for semilla in range(12):
            escena = EscenaEstacion(reusar_cliente=base.cliente)
            backend = EstacionBackendSim(escena, camara=CamaraOraculo())
            backend.aplicar_errores(errores, semilla)
            planta = PlantaSimulada(escena, backend, LineaMonedas(), EmbalajeVasos(), escenario,
                                    monedas_por_vaso=LOTE, lecturas_por_decision=3)
            eventos = _correr(planta)
            assert not [e for e in eventos if e["ev"] == "sabotaje_detectado" and e.get("estacion") == "camara"]
    finally:
        base.cerrar()


def test_la_prueba_completa_cubre_todos_los_filtros(crear_planta):
    """La unica prueba de la interfaz trae un caso de cada causa de rechazo,
    casillas vacias y las manos en la carga, y cada elemento llega a donde
    debe."""
    from control import reglas

    planta = crear_planta("prueba_completa")
    eventos = _correr(planta, max_ticks=400)
    assert planta.terminado
    assert _destinos(planta) == [e.destino_esperado for e in planta.escenario.elementos]
    causas = {e["causa"] for e in eventos if e["ev"] == "rechazo" and e.get("causa")}
    assert set(reglas.CAUSAS_VALIDAS) <= causas
    tipos = [e.tipo for e in planta.escenario.elementos]
    assert tipos.count("vacia") == 2 and tipos.count("mano") == 2


def test_el_carro_carga_con_la_secuencia_segura(crear_planta):
    """Punto 13: en_muelle -> cuna vacia -> soltar UN vaso -> la cuna lo
    confirma (carga). Cada vaso soltado es uno que estaba en la canaleta."""
    planta = crear_planta()
    eventos = _correr(planta)
    orden = [e["ev"] for e in eventos if e["ev"] in ("en_muelle", "soltar", "carga")]
    assert orden and orden[:3] == ["en_muelle", "soltar", "carga"]
    soltados = [e["vaso"] for e in eventos if e["ev"] == "soltar"]
    cargados = [e["vaso"] for e in eventos if e["ev"] == "carga"]
    assert soltados == cargados
    assert all(planta.vasos_finales[v] == "entrega" for v in soltados)


def test_si_la_cuna_no_confirma_no_se_suelta_otro_vaso(crear_planta):
    """El infrarrojo de la cuna no ve el vaso soltado: alarma, el carro no se
    va y el escape no suelta otro hasta que la cuna lo confirme."""
    planta = crear_planta()
    sensor = planta.backend.sensor_cuna
    leer_real = sensor.leer
    ciego = {"lecturas": 0}

    def leer():
        # Desde el primer vaso soltado, las siguientes 6 lecturas (2 ticks
        # con voto de 3) no lo ven.
        if sensor.ocupada and ciego["lecturas"] < 6:
            ciego["lecturas"] += 1
            return False
        return leer_real()

    sensor.leer = leer
    eventos = _correr(planta)
    alarma = [e for e in eventos if e["ev"] == "alarma" and e["tipo"] == "carga_no_confirmada"]
    assert alarma
    t0 = alarma[0]["tick"]
    confirmada = next(e["tick"] for e in eventos if e["ev"] == "carga" and e["vaso"] == alarma[0]["vaso"])
    assert confirmada > t0
    assert not any(e["ev"] == "soltar" and t0 < e["tick"] < confirmada for e in eventos)


def test_con_el_carro_fisico_un_vaso_llega_a_la_meta_y_el_carro_vuelve():
    """Punto 14 dentro de la planta: el escape suelta un vaso a la cuna del
    carro (secuencia segura), el carro lo lleva a la meta esquivando los
    muros, lo sacan, y vuelve solo al muelle listo para el siguiente."""
    escena = EscenaEstacion()
    planta = None
    try:
        backend = EstacionBackendSim(escena, camara=CamaraOraculo(probabilidad_error=0.0))
        planta = PlantaSimulada(escena, backend, LineaMonedas(), EmbalajeVasos(), cargar_escenario("prueba_completa"),
                                monedas_por_vaso=LOTE, carro_fisico=True)
        carro = []
        while planta.ticks < 600:
            carro += [e for e in planta.paso() if e["src"] == "carro"]
            nombres = [e["ev"] for e in carro]
            if "entregado" in nombres and "en_muelle" in nombres[nombres.index("entregado"):]:
                break
        nombres = [e["ev"] for e in carro]
        # Primer viaje: de la primera carga hasta que vuelve al muelle.
        viaje = nombres[nombres.index("carga"):nombres.index("en_muelle", nombres.index("entregado")) + 1]
        carga = next(e for e in carro if e["ev"] == "carga")
        entregado = next(e for e in carro if e["ev"] == "entregado")
        assert entregado["vaso"] == carga["vaso"]
        assert planta.vasos_finales[carga["vaso"]] == "entrega"
        assert viaje.count("evasion") == 6 and "error" not in viaje
        assert planta.carro.toques_muro == 0
    finally:
        if planta is not None:
            planta.cerrar()
        escena.cerrar()


def test_la_cinta_de_monedas_no_avanza_vacia_y_sin_carga(crear_planta):
    """Usuario, 2026-09-26: si la cinta no lleva nada y el infrarrojo de la
    carga no ve nada, la cinta se queda quieta (evento 'espera'); cuando el
    operador pone algo, arranca."""
    from sim.carga_escenarios import Escenario, EspecificacionElemento

    planta = crear_planta()
    planta._pendientes.clear()
    planta._pendientes.extend([EspecificacionElemento("vacia", "vacia"), EspecificacionElemento("vacia", "vacia"),
                               EspecificacionElemento("boton_plastico", "rechazo")])
    eventos = []
    for _ in range(3):
        eventos.append(planta.paso())
    pasos = [any(e["ev"] == "paso" and e["src"] == "linea" for e in t) for t in eventos]
    esperas = [any(e["ev"] == "espera" for e in t) for t in eventos]
    assert pasos == [False, False, True]
    assert esperas == [True, True, False]


def test_la_camara_ve_una_mano_sobre_el_llenado_y_no_se_suelta_el_lote(crear_planta):
    """Punto 11 (usuario, 2026-09-26): la cortina cubre tapa y prensa; la zona
    por donde cae el lote al vaso de llenado la vigila la camara de vasos. Con
    una mano ahi se detiene la cinta de vasos (prensa arriba) y el almacen no
    suelta ningun lote hasta que se va."""
    planta = crear_planta()
    eventos = []
    puesta = None
    for _ in range(400):
        if planta.terminado:
            break
        t = planta.paso()
        eventos += t
        if puesta is None and planta.ticks > 20:
            if planta.sabotaje_mano_en_llenado():
                puesta = planta.ticks
    activa = next(e for e in eventos if e["ev"] == "cortina" and e["activa"])
    assert activa["fuente"] == "camara_llenado"
    fin = next(e["tick"] for e in eventos if e["ev"] == "cortina" and not e["activa"])
    assert not any(e["ev"] == "embalado" and activa["tick"] <= e["tick"] < fin for e in eventos)
    assert not any(e["ev"] == "paso" and e["src"] == "vasos" and activa["tick"] <= e["tick"] < fin for e in eventos)
    assert planta.terminado


def test_la_zona_de_caida_no_se_dispara_sola(crear_planta):
    """Sin nadie metiendo la mano, la vigilancia de la zona de caida no ve
    nada en toda la corrida (ni los vasos, ni las tapas, ni los lotes)."""
    planta = crear_planta()
    eventos = []
    while not planta.terminado and planta.ticks < 400:
        eventos += planta.paso()
    assert not any(e["ev"] == "cortina" for e in eventos)


def test_sin_radio_el_carro_termina_la_vuelta_y_no_le_cargan_otro_a_ciegas():
    """Punto 15 (usuario, 2026-09-26): si el carro pierde la radio termina la
    vuelta y queda en el muelle; sus mensajes quedan guardados y llegan en
    orden al volver el enlace; la estacion no le suelta otro vaso hasta que
    el carro diga (con su infrarrojo) que la cuna esta vacia."""
    escena = EscenaEstacion()
    planta = None
    try:
        backend = EstacionBackendSim(escena, camara=CamaraOraculo(probabilidad_error=0.0))
        planta = PlantaSimulada(escena, backend, LineaMonedas(), EmbalajeVasos(), cargar_escenario("prueba_completa"),
                                monedas_por_vaso=LOTE, carro_fisico=True)
        eventos, corte, volvio, reconexion = [], None, None, None
        while planta.ticks < 1200:
            nuevos = planta.paso()
            eventos += nuevos
            if corte is None and any(e["ev"] == "carga" for e in nuevos):
                assert planta.sabotaje_cortar_radio()
                corte = planta.ticks
            elif corte and volvio is None and planta.ticks > corte + 3 and planta.carro.control.estado == "esperando_carga":
                volvio = planta.ticks
            elif volvio and reconexion is None and planta.ticks >= volvio + 3:
                assert planta.sabotaje_reconectar_radio()
                reconexion = planta.ticks
            elif reconexion and any(e["ev"] == "soltar" for e in nuevos):
                break
        assert corte and volvio and reconexion, (corte, volvio, reconexion)
        sin_radio = [e for e in eventos if corte < e["tick"] < reconexion]
        assert any(e["ev"] == "sin_enlace" for e in sin_radio)
        assert not any(e["ev"] == "soltar" for e in sin_radio)
        assert not any(e["src"] == "carro" and e["ev"] in ("meta", "en_muelle", "vaso_retirado") for e in sin_radio)
        despues = [e for e in eventos if e["tick"] >= reconexion]
        del_carro = [e["ev"] for e in despues if e["src"] == "carro"]
        assert "enlace_recuperado" in del_carro
        # Lo guardado llega en orden: meta antes que en_muelle.
        assert del_carro.index("meta") < del_carro.index("en_muelle")
        estado = next(e for e in despues if e["ev"] == "estado")
        soltar = next(e for e in despues if e["ev"] == "soltar")
        assert estado["cuna"] is False and estado["tick"] <= soltar["tick"]
    finally:
        if planta is not None:
            planta.cerrar()
        escena.cerrar()
