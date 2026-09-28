"""Pruebas de la geometria compartida (visor 3D), la pista, el servidor HTTP
del supervisor y la documentacion generada.

Las de geometria dejan fijas coherencias FISICAS que en la fase 2 no se
cumplian y que el visor 3D dejo en evidencia: si alguien cambia una altura o
un largo en config/parametros.yaml y rompe una, la prueba lo dice."""

import json
import math
import socket
import urllib.request

import pytest

from app import configuracion, documentos, servidor
from sim import mundo
from sim.catalogos import CATALOGO_SENSORES
from sim.geometria import geometria_completa
from sim.pista import generar_linea_central, punto_en


@pytest.fixture(scope="module")
def parametros():
    return configuracion.cargar_parametros()


@pytest.fixture(scope="module")
def geo(parametros):
    return geometria_completa(parametros)


# ---------------------------------------------------------------------------
# pista
# ---------------------------------------------------------------------------


def test_recta_y_media_vuelta():
    tramos = [{"tipo": "recta", "largo_mm": 500}, {"tipo": "curva", "radio_mm": 200, "angulo_grados": 180}]
    linea = generar_linea_central(tramos, (0.0, 0.0, 0.0))
    fin = linea[-1]
    # 0.5 m derecho por +x, media vuelta a la izquierda de radio 0.2: queda
    # 0.4 m mas arriba, en x=0.5, mirando hacia -x.
    assert fin.x == pytest.approx(0.5, abs=1e-6)
    assert fin.y == pytest.approx(0.4, abs=1e-6)
    assert abs(math.cos(fin.rumbo) + 1) < 1e-6
    assert fin.s == pytest.approx(0.5 + math.pi * 0.2, abs=1e-6)


def test_curva_a_la_derecha_baja():
    linea = generar_linea_central([{"tipo": "curva", "radio_mm": 100, "angulo_grados": -90}], (0.0, 0.0, 0.0))
    assert linea[-1].x == pytest.approx(0.1, abs=1e-6)
    assert linea[-1].y == pytest.approx(-0.1, abs=1e-6)


def test_punto_en_interpola():
    linea = generar_linea_central([{"tipo": "recta", "largo_mm": 1000}], (0.0, 0.0, 0.0))
    assert punto_en(linea, 0.255).x == pytest.approx(0.255, abs=1e-6)


def test_obstaculos_caen_sobre_la_pista_y_en_orden(geo):
    obst = geo["pista"]["obstaculos"]
    assert len(obst) == 3
    assert [o["s"] for o in obst] == sorted(o["s"] for o in obst)
    assert all(0 < o["s"] < geo["pista"]["largo"] for o in obst)


# ---------------------------------------------------------------------------
# coherencia fisica de la planta
# ---------------------------------------------------------------------------


def test_la_moneda_puede_caer_al_vaso(geo):
    superficie_monedas = geo["cinta_monedas"]["estaciones"][-1]["posicion"][2]
    boca_vaso = geo["cinta_vasos"]["estaciones"][1]["posicion"][2] + geo["vaso"]["altura"]
    assert superficie_monedas > boca_vaso + 0.02


def test_el_vaso_colgado_no_toca_el_piso(geo):
    """El vaso cuelga del reborde: su fondo queda una altura de vaso por
    debajo de los rieles. Al final de la canaleta tiene que seguir en el
    aire (y pasar a la cuna del carro a esa misma altura)."""
    fin = geo["canaleta"]["fin"]
    assert fin[2] - geo["vaso"]["altura"] > 0.02


def test_la_canaleta_baja_a_la_inclinacion_configurada(geo, parametros):
    ini, fin = geo["canaleta"]["inicio"], geo["canaleta"]["fin"]
    caida = ini[2] - fin[2]
    largo = math.hypot(fin[0] - ini[0], fin[1] - ini[1])
    assert math.degrees(math.atan2(caida, largo)) == pytest.approx(
        parametros["canaleta_entrega"]["inclinacion_grados"], abs=0.1)


def test_el_carro_arranca_bajo_la_canaleta(geo):
    salida, fin = geo["pista"]["salida"], geo["canaleta"]["fin"]
    assert abs(salida["x"] - fin[0]) < 1e-6
    assert abs(salida["y"] - fin[1]) < geo["vehiculo"]["largo"] / 2


def test_los_vasos_no_se_enciman_en_la_cinta(geo):
    assert geo["cinta_vasos"]["separacion"] > geo["vaso"]["diametro"]


# ---------------------------------------------------------------------------
# sensores: el visor dibuja exactamente lo que la simulacion consulta
# ---------------------------------------------------------------------------


def test_catalogo_numerado_sin_huecos():
    assert [s["numero"] for s in CATALOGO_SENSORES] == list(range(1, len(CATALOGO_SENSORES) + 1))
    assert len({s["id"] for s in CATALOGO_SENSORES}) == len(CATALOGO_SENSORES)


def test_rayo_de_presencia_coincide_con_la_estacion_1(geo):
    rayo = next(s for s in geo["sensores"] if s["id"] == "presencia")["geometria"]
    x, y, z = mundo.posicion_estacion_monedas(mundo.ESTACION_PRESENCIA_MONEDAS)
    assert rayo["destino"] == pytest.approx([x, y, z])
    assert rayo["origen"][2] > z


def test_franjas_de_la_camara_de_vasos_a_la_altura_correcta(geo, parametros):
    alto = parametros["vasos"]["altura_mm"] / 1000
    z0 = geo["cinta_vasos"]["estaciones"][0]["posicion"][2]
    por_id = {s["id"]: s["geometria"] for s in geo["sensores"]}
    franjas = por_id["camara_vasos"]["franjas"]
    assert len(franjas) == 8  # media y borde en verificacion, llenado, tapa y prensa
    medias = [f for f in franjas if f["nivel"] == "media"]
    bordes = [f for f in franjas if f["nivel"] == "borde"]
    assert all(f["origen"][2] == pytest.approx(z0 + alto * 0.5, abs=1e-4) for f in medias)
    # La del borde queda POR ENCIMA del vaso: un vaso normal no la ocupa.
    assert all(f["origen"][2] > z0 + alto for f in bordes)
    # La cortina (un solo sensor) queda a media altura del vaso.
    assert z0 < por_id["cortina"]["origen"][2] < z0 + alto


def test_la_cortina_queda_afuera_del_borde_de_los_vasos(geo, parametros):
    """Del lado del operador, afuera del reborde: ni la tapa ni la prensa
    cortan el cono, ni siquiera donde esta mas abierto."""
    radio_boca = (parametros["vasos"]["diametro_mm"] / 2 + parametros["vasos"]["reborde_mm"]) / 1000
    y_cinta = geo["cinta_vasos"]["estaciones"][0]["posicion"][1]
    cortina = next(s for s in geo["sensores"] if s["id"] == "cortina")["geometria"]
    assert cortina["tipo"] == "cono"
    assert abs(cortina["origen"][1] - y_cinta) - cortina["radio_final"] > radio_boca


# ---------------------------------------------------------------------------
# servidor HTTP
# ---------------------------------------------------------------------------


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_servidor_entrega_visor_geometria_estado_y_pasos(tmp_path, geo):
    compartido = servidor.EstadoCompartido(geo, tmp_path / "planta.db")
    compartido.publicar({"tick": 7, "linea": "corriendo"})
    puerto = _puerto_libre()
    srv = servidor.arrancar(compartido, puerto)
    try:
        base = f"http://127.0.0.1:{puerto}"
        with urllib.request.urlopen(base + "/") as r:
            assert b"visor.js" in r.read()
        with urllib.request.urlopen(base + "/visor.js") as r:
            assert r.headers["Content-Type"].startswith("text/javascript")
        with urllib.request.urlopen(base + "/api/estado") as r:
            assert json.loads(r.read())["tick"] == 7
        with urllib.request.urlopen(base + "/api/geometria") as r:
            assert len(json.loads(r.read())["sensores"]) == len(CATALOGO_SENSORES)
        with urllib.request.urlopen(base + "/api/pasos") as r:
            assert json.loads(r.read())[0]["numero"] == 1
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/../config/parametros.yaml")
    finally:
        srv.shutdown()


@pytest.mark.parametrize("hay", [True, False])
def test_servidor_dice_si_hay_internet(tmp_path, geo, monkeypatch, hay):
    """El visor en vivo no decide solo si hay internet: le pregunta al supervisor (el mismo
    chequeo del asistente y el dashboard). Antes decia "sin internet" con internet."""
    from app import asistente

    monkeypatch.setattr(asistente, "hay_internet", lambda *a, **k: hay)
    puerto = _puerto_libre()
    srv = servidor.arrancar(servidor.EstadoCompartido(geo, tmp_path / "planta.db"), puerto)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/internet") as r:
            assert json.loads(r.read()) == {"internet": hay}
    finally:
        srv.shutdown()


def test_servidor_recibe_ordenes(tmp_path, geo):
    from app import db

    ruta = tmp_path / "planta.db"
    db.conectar(ruta).close()
    puerto = _puerto_libre()
    srv = servidor.arrancar(servidor.EstadoCompartido(geo, ruta), puerto)
    try:
        pedido = urllib.request.Request(
            f"http://127.0.0.1:{puerto}/api/orden", data=json.dumps({"cmd": "pausar"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(pedido).read()
        conexion = db.conectar(ruta)
        assert db.tomar_ordenes_pendientes(conexion) == [{"cmd": "pausar"}]
        conexion.close()
    finally:
        srv.shutdown()


# ---------------------------------------------------------------------------
# documentacion generada
# ---------------------------------------------------------------------------


def test_ancla_como_github_conserva_acentos():
    assert documentos._ancla({"numero": 1, "titulo": "Carga del elemento y estación 1 (presencia)"}) == \
        "1-carga-del-elemento-y-estación-1-presencia"


def test_cada_sensor_tiene_su_apartado_en_sensores_md():
    anclas = [documentos.ancla_sensor(s) for s in CATALOGO_SENSORES]
    assert anclas[0].startswith("1-") and len(set(anclas)) == len(anclas)


def test_cadena_de_alturas_del_almacen(geo):
    """Todo cae por gravedad: cinta de monedas > boca de los tubos > placa
    fija > embudo > boca del vaso de llenado."""
    al = geo["almacen"]
    superficie = geo["cinta_monedas"]["estaciones"][-1]["posicion"][2]
    boca_tubos = al["tubo_z_arriba"]
    boca_vaso = geo["cinta_vasos"]["estaciones"][1]["posicion"][2] + geo["vaso"]["altura"]
    assert superficie > boca_tubos + 0.05 > al["tubos"][0]["base"][2]
    assert al["tolva"]["z_arriba"] < al["tubos"][0]["base"][2]
    assert al["tolva"]["z_abajo"] > boca_vaso


def test_el_agujero_del_almacen_queda_sobre_el_vaso_y_la_carga_bajo_la_cinta(geo):
    """Revolver: el agujero de la placa fija cae sobre el vaso de llenado y el
    punto de carga queda casi debajo del extremo de la cinta de monedas (la
    moneda cae casi vertical, sin un pico que la desvie)."""
    import math as m

    al = geo["almacen"]
    llenado = geo["cinta_vasos"]["estaciones"][1]["posicion"]
    a = m.radians(al["angulo_agujero"])
    agujero = (al["centro"][0] + al["radio_carrusel"] * m.cos(a), al["centro"][1] + al["radio_carrusel"] * m.sin(a))
    assert m.dist(agujero, llenado[:2]) < 0.002
    cabeza_x = geo["cinta_monedas"]["estaciones"][-1]["posicion"][0] + geo["cinta_monedas"]["separacion"] / 2
    assert abs(al["punto_carga"][0] - cabeza_x) < 0.03
    # 210 grados entre carga y agujero: con un tubo en la carga, el agujero
    # queda entre dos tubos (nunca se carga y se suelta a la vez).
    diferencia = (al["angulo_agujero"] - al["angulo_carga"]) % 60
    assert 20 < diferencia < 40


def test_un_tubo_por_denominacion_sin_chocar(geo):
    tubos = geo["almacen"]["tubos"]
    assert [t["denominacion"] for t in tubos] == [50, 100, 200, 500, 1000, "otras"]
    for i, a in enumerate(tubos):
        for b in tubos[i + 1:]:
            distancia = math.dist(a["base"][:2], b["base"][:2])
            assert distancia > a["radio"] + b["radio"]
    # La moneda mas grande (1000 nueva, 26,7 mm) entra en el tubo.
    assert tubos[0]["radio"] * 2 > 0.0267


def test_componentes_ids_unicos_y_servos_caben_en_el_pca9685():
    from sim.catalogos import CATEGORIAS, COMPONENTES

    ids = [c["id"] for c in COMPONENTES]
    assert len(ids) == len(set(ids))
    assert all(c["categoria"] in CATEGORIAS for c in COMPONENTES)
    assert all(c["estado"] in ("simulado", "efecto simulado", "solo visual") for c in COMPONENTES)
    servos = sum(c["cantidad"] for c in COMPONENTES if c["id"].startswith("servo"))
    assert servos <= 16  # un solo PCA9685


def test_geometria_lleva_los_componentes(geo):
    assert len(geo["componentes"]) > 20 and "Actuadores" in geo["categorias_componentes"]


def test_el_sensor_de_la_cortina_no_estorba_al_vaso_que_va_a_la_canaleta(geo, parametros):
    """El empujador pasa el vaso de la descarga a la canaleta de lado (-y),
    justo por donde esta la cortina: el sensor y su soporte (detras de la
    placa) tienen que quedar antes del borde de ese vaso, con margen."""
    radio_boca = (parametros["vasos"]["diametro_mm"] / 2 + parametros["vasos"]["reborde_mm"]) / 1000
    x_descarga = geo["cinta_vasos"]["estaciones"][4]["posicion"][0]
    cortina = next(s for s in geo["sensores"] if s["id"] == "cortina")["geometria"]
    fondo = cortina["origen"][0] + cortina["fondo_soporte"]
    assert fondo < x_descarga - radio_boca - 0.005
    assert fondo < geo["canaleta"]["inicio"][0] - geo["canaleta"]["separacion_rieles"] / 2 - 0.005


def test_la_pestana_queda_bien_apoyada_en_los_rieles(geo, parametros):
    """Usuario, 2026-09-26: pestana de 8 mm y entrada en embudo. En la parte
    recta, la pestana pasa al menos 4 mm del centro de cada riel y el cuerpo
    pasa entre ellos; en la boca del embudo todavia se apoya (2 mm o mas) y
    el riel arranca por debajo de la boca del vaso."""
    c = geo["canaleta"]
    radio_cuerpo = parametros["vasos"]["diametro_mm"] / 2000
    radio_boca = radio_cuerpo + parametros["vasos"]["reborde_mm"] / 1000
    r_riel = c["diametro_riel"] / 2
    assert radio_boca - c["separacion_rieles"] / 2 >= 0.004
    assert c["separacion_rieles"] / 2 - r_riel - radio_cuerpo >= 0.001
    assert radio_boca - c["separacion_entrada"] / 2 >= 0.002
    assert c["separacion_entrada"] > c["separacion_rieles"]
    boca = geo["cinta_vasos"]["estaciones"][4]["posicion"][2] + geo["vaso"]["altura"]
    assert c["inicio"][2] + r_riel < boca


def test_las_tapas_de_vasos_vecinos_no_se_tocan(parametros):
    boca = parametros["vasos"]["diametro_mm"] + 2 * parametros["vasos"]["reborde_mm"]
    assert boca < parametros["vasos"]["separacion_casilla_mm"]
