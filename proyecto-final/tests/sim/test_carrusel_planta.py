"""Carrusel del almacen con tiempo real dentro de la planta (sim/planta.py).

Usuario, 2026-09-28: "la moneda pasa sin que se espere a que de la vuelta y
se coloque bien, tema de timing". Antes la moneda se guardaba en su tubo en
el mismo tick en que llegaba a E4, sin ningun giro: en prueba_completa 21 de
24 monedas caian con el carrusel todavia girando (y el visor animaba el giro
por su cuenta, hasta 6,5 s atrasado). Aqui se exige:

- cada moneda cae a la boca de su tubo con el tubo YA quieto bajo la carga;
- cada lote cae con su tubo quieto sobre el agujero;
- mientras tanto la moneda espera en la descarga (sin alarma de tubo lleno)
  y la cinta de vasos no se mueve con el lote en camino.

Las revisiones se hacen SOLO con los eventos (lo mismo que recibe el visor 3D)
y ademas con lo que la planta sabe por dentro. Modo DIRECT, oraculo sin ruido.
"""

import pytest

from app.configuracion import cargar_parametros
from control.embalaje import EmbalajeVasos
from control.hal.backend_sim import EstacionBackendSim
from control.linea import LineaMonedas
from sim.carga_escenarios import cargar_escenario
from sim.mundo import EscenaEstacion
from sim.planta import PlantaSimulada
from sim.sensores_sim import CamaraOraculo

LOTE = 5
_T = cargar_parametros()["tiempos_ms"]
CICLO_MS = _T["avance_casilla_monedas"] + _T["pausa_casilla_monedas"]


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


def _correr(planta, max_ticks=400):
    eventos = []
    while not planta.terminado and planta.ticks < max_ticks:
        eventos.extend(planta.paso())
    return eventos


def _instante(e):
    """ms del reloj de la planta: cada tick es un ciclo de la cinta de monedas."""
    return (e["tick"] - 1) * CICLO_MS + e.get("en_ms", 0)


def _giros_y_caidas(eventos):
    giros, caidas = [], []
    for e in eventos:
        if e["ev"] == "gira" and e["src"] == "carrusel":
            t = _instante(e)
            giros.append((t, t + e["dur_ms"], e["tubo"], e["lugar"]))
        elif e["ev"] == "almacen" and e["src"] == "e4":
            caidas.append((_instante(e), e["tubo"], "carga", e["casilla"]))
        elif e["ev"] == "embalado":
            caidas.append((_instante(e), e["denominacion"], "agujero", e["vaso"]))
    return sorted(giros, key=lambda g: g[0]), caidas


def _caidas_a_destiempo(eventos):
    giros, caidas = _giros_y_caidas(eventos)
    assert caidas
    malas = []
    for t, tubo, lugar, quien in caidas:
        # Un giro que arranca JUSTO al caer es el que va a la siguiente moneda.
        antes = [g for g in giros if g[0] < t]
        # En reposo (tras el homing con el Hall) el tubo de $50 esta en la carga.
        _, llegada, g_tubo, g_lugar = antes[-1] if antes else (0, 0, 50, "carga")
        if (g_tubo, g_lugar) != (tubo, lugar) or llegada > t:
            malas.append((quien, tubo, lugar, t, g_tubo, g_lugar, llegada))
    return malas


@pytest.mark.parametrize("nombre,lote", [("prueba_completa", LOTE), ("prueba_completa", 10), ("mixto_20", LOTE)])
def test_nada_cae_antes_de_que_su_tubo_llegue(crear_planta, nombre, lote):
    planta = crear_planta(nombre, lote)
    eventos = _correr(planta)
    assert planta.terminado, "la corrida se quedo trabada"
    assert _caidas_a_destiempo(eventos) == []
    # Lo mismo visto desde adentro: el tubo que habia DE VERDAD bajo la carga.
    assert planta.guardados and all(g["tubo_bajo_carga"] == g["tubo_pedido"] and not g["girando"]
                                    for g in planta.guardados)
    # Y cada elemento sigue terminando donde dice el escenario.
    assert [planta.destinos_finales.get(i) for i in planta.orden_ids] == \
        [e.destino_esperado for e in planta.escenario.elementos]


def test_la_moneda_espera_al_carrusel_en_la_descarga_sin_alarma(crear_planta):
    planta = crear_planta("mixto_20")
    eventos = _correr(planta)
    esperas = [e for e in eventos if e["ev"] == "espera" and e["src"] == "e4"]
    assert esperas and all(e["motivo"] == "carrusel_girando" for e in esperas)
    assert all(e["falta_ms"] > 0 and e["tubo_bajo_carga"] != e["tubo"] for e in esperas if "falta_ms" in e)
    # Esperar al carrusel es normal: no es la alarma de tubo lleno.
    assert not any(e["ev"] == "alarma" and e.get("tipo") == "tubo_lleno" for e in eventos)
    # Mientras espera, la cinta de monedas no avanza: la moneda sigue en E4.
    for e in esperas:
        siguiente = [x for x in eventos if x["tick"] == e["tick"] + 1]
        if not any(x["ev"] == "almacen" and x["casilla"] == e["casilla"] for x in siguiente):
            assert not any(x["ev"] == "paso" and x["src"] == "linea" for x in siguiente)


def test_el_lote_cae_con_el_tubo_sobre_el_agujero_y_los_vasos_esperan(crear_planta):
    planta = crear_planta("prueba_completa", LOTE)
    eventos = _correr(planta)
    lotes = [e for e in eventos if e["ev"] == "embalado"]
    assert lotes and all(e["tubo_sobre_agujero"] == e["denominacion"] for e in lotes)
    # Entre que el tubo sale hacia el agujero y se cierra el obturador, la
    # cinta de vasos no se mueve (el vaso de llenado tiene que estar quieto).
    for g in (e for e in eventos if e["ev"] == "gira" and e["lugar"] == "agujero"):
        lote = next(e for e in lotes if e["tick"] >= g["tick"] and e["denominacion"] == g["tubo"])
        cierra = _instante(lote) + lote["obturador_ms"]
        movidas = [e for e in eventos if e["src"] == "vasos" and e["ev"] == "paso"
                   and _instante(g) <= (e["tick"] - 1) * CICLO_MS < cierra]
        assert movidas == []


def test_el_tablero_cuenta_el_giro_y_la_espera():
    """Las frases del dashboard (app/dashboard/textos.py) para los eventos nuevos."""
    import json

    from app.dashboard.textos import frase_evento

    def frase(origen, tipo, **d):
        return frase_evento({"origen": origen, "tipo": tipo, "payload": json.dumps(d)})

    tono, _, texto = frase("carrusel", "gira", tubo=500, lugar="carga", dur_ms=4096)
    assert "carrusel" in texto and "$500" in texto and "4.1 s" in texto
    tono, _, texto = frase("e4", "espera", motivo="carrusel_girando", tubo=100, denominacion=100, falta_ms=765)
    assert "espera" in texto and "carrusel" in texto and "0.8 s" in texto and tono == "gris"
    tono, _, texto = frase("e4", "espera", motivo="tubo_lleno", tubo=200, denominacion=200)
    assert "lleno" in texto and tono == "ambar"


def test_el_estado_trae_el_carrusel(crear_planta):
    planta = crear_planta("mixto_20")
    vistos = set()
    while not planta.terminado and planta.ticks < 300:
        planta.paso()
        c = planta.estado()["carrusel"]
        assert set(c) >= {"tubo_en_carga", "lugar", "angulo_grados", "girando", "llega_en_ms"}
        vistos.add(c["girando"])
        if c["girando"]:
            assert c["tubo_en_carga"] is None and c["llega_en_ms"] > 0
    assert vistos == {True, False}


# ---------------------------------------------------------------------------
# La CAIDA ocupa el carrusel (revision visual en vivo, 2026-09-29): de 15
# llegadas, 8 caian a un tubo 15-37 mm fuera de la boca con el disco girando
# 22-40 grados. Causa: la moneda que esperaba en la descarga caia al empezar
# el ciclo (e4/almacen en_ms=0) y en el MISMO instante arrancaba el giro hacia
# el tubo de la siguiente (carrusel/gira en_ms=0): el disco se iba mientras la
# moneda todavia bajaba por el canal. Una moneda guardada ocupa el carrusel
# hasta que termina de caer (`tiempos_ms.caida_moneda_tubo`); un lote, desde
# que abre el obturador hasta que cierra.
# ---------------------------------------------------------------------------

CAIDA_MS = _T["caida_moneda_tubo"]


def _giros_durante_caidas(eventos):
    giros, caidas = _giros_y_caidas(eventos)
    malos = []
    for t, tubo, lugar, quien in caidas:
        if lugar == "carga":
            ocupado = (t, t + CAIDA_MS)
        else:
            lote = next(e for e in eventos if e["ev"] == "embalado" and e["vaso"] == quien
                        and e["denominacion"] == tubo)
            ocupado = (t, t + lote["obturador_ms"])
        for inicio, fin, g_tubo, g_lugar in giros:
            # Un giro que ARRANCA mientras la moneda (o el lote) cae, o que
            # todavia no termino cuando empieza a caer.
            if ocupado[0] <= inicio < ocupado[1] or inicio < ocupado[0] < fin:
                malos.append((quien, tubo, lugar, ocupado, (inicio, fin, g_tubo, g_lugar)))
    return malos


@pytest.mark.parametrize("nombre,lote", [("prueba_completa", LOTE), ("prueba_completa", 10), ("mixto_20", LOTE)])
def test_el_carrusel_no_gira_mientras_cae_una_moneda_o_un_lote(crear_planta, nombre, lote):
    planta = crear_planta(nombre, lote)
    eventos = _correr(planta)
    assert planta.terminado, "la corrida se quedo trabada"
    assert _giros_durante_caidas(eventos) == []
    # Y cada elemento sigue terminando donde dice el escenario.
    assert [planta.destinos_finales.get(i) for i in planta.orden_ids] == \
        [e.destino_esperado for e in planta.escenario.elementos]


def test_el_giro_a_la_siguiente_espera_el_fin_de_la_caida(crear_planta):
    """El caso exacto de la demo: la moneda que esperaba cae al empezar el
    ciclo y el siguiente giro sale `caida_moneda_tubo` despues, no a la vez."""
    planta = crear_planta("prueba_completa", LOTE)
    eventos = _correr(planta)
    giros, caidas = _giros_y_caidas(eventos)
    vistos = 0
    for t, _, lugar, _ in caidas:
        if lugar != "carga":
            continue
        siguiente = [g for g in giros if g[0] >= t]
        if siguiente and siguiente[0][0] < t + CAIDA_MS + 1:
            vistos += 1
            assert siguiente[0][0] >= t + CAIDA_MS
    assert vistos > 0, "la corrida no tuvo ningun giro pegado a una caida"


def test_la_caida_del_config_alcanza_a_la_fisica():
    """`caida_moneda_tubo` no puede ser menor que la caida libre desde la cinta
    hasta el fondo de un tubo vacio (sin contar el roce del canal, que la
    alarga): t = sqrt(2 h / g)."""
    import math

    from sim import mundo

    z_cinta = mundo.posicion_estacion_monedas(mundo.ESTACION_DESCARGA_MONEDAS)[2]
    h = z_cinta - mundo.TUBO_BASE_Z
    t_libre_ms = 1000 * math.sqrt(2 * h / 9.81)
    assert CAIDA_MS >= t_libre_ms
    # Y cabe en la pausa: si no, la cinta esperaria en cada moneda.
    assert CAIDA_MS < _T["pausa_casilla_monedas"]
