"""Protocolo del punto 15: numeracion, ack, reintentos, latido y la regla de
soltar un vaso al carro."""

from control import protocolo as pr


def test_parsear_linea_tolerante():
    assert pr.parsear_linea('{"t":"evt","ev":"paso"}\n') == {"t": "evt", "ev": "paso"}
    for mala in ['', '{"t":"evt","ev":"pa', 'basura', '{"sin":"tipo"}', b'\xff\xfe{']:
        assert pr.parsear_linea(mala) is None
    assert pr.parsear_linea(pr.linea({"t": "hb", "n": 3})) == {"t": "hb", "n": 3}


def test_pc_reintenta_una_vez_y_despues_marca_fallo():
    e = pr.Emisor(reintento_ms=300, reintentos=1)
    m = e.enviar({"t": "cmd", "dst": "linea", "act": "avanzar"}, t_ms=0)
    assert m["id"] == 1
    assert e.a_reenviar(100) == []
    assert e.a_reenviar(300) == [m]          # un reintento
    assert e.a_reenviar(700) == []           # sin ack: fallo
    assert e.fallidos == [m] and not e.pendientes


def test_ack_saca_el_mensaje_de_la_cola():
    e = pr.Emisor(reintento_ms=300, reintentos=1)
    m = e.enviar({"t": "cmd"}, 0)
    e.ack(m["id"])
    assert e.a_reenviar(1000) == [] and not e.fallidos


def test_el_carro_guarda_sus_eventos_mientras_no_hay_enlace_y_los_reenvia_en_orden():
    e = pr.Emisor(reintento_ms=500, reintentos=None)
    ms = [e.enviar({"t": "evt", "ev": ev}, t) for t, ev in ((0, "meta"), (100, "vaso_retirado"), (200, "en_muelle"))]
    for t in range(500, 5000, 500):
        e.a_reenviar(t)                      # sin ack: se siguen guardando
    assert [m["ev"] for m, *_ in e.pendientes.values()] == ["meta", "vaso_retirado", "en_muelle"]
    r = pr.Receptor()
    recibidos = []
    for m in e.a_reenviar(6000):
        nuevo, ack = r.recibir(m)
        if nuevo:
            recibidos.append(m["ev"])
        e.ack(ack["id"])
    assert recibidos == ["meta", "vaso_retirado", "en_muelle"] and not e.pendientes


def test_un_reenvio_repetido_no_se_ejecuta_dos_veces():
    r = pr.Receptor()
    m = {"t": "evt", "id": 7, "ev": "carga"}
    assert r.recibir(m)[0] is True
    assert r.recibir(m)[0] is False and r.repetidos == 1


def test_secuencia_detecta_mensajes_perdidos():
    s = pr.Secuencia()
    assert [s.recibir(n) for n in (1, 2, 5, 6)] == [0, 0, 2, 0]
    assert s.perdidos == 2


def test_latido_perdido_y_recuperado():
    l = pr.Latido(periodo_ms=250, perdido_ms=1000)
    l.oido(0)
    assert l.cambio(500) == "recuperado"
    assert l.cambio(900) is None
    assert l.cambio(1600) == "perdido"
    l.oido(2000)
    assert l.cambio(2000) == "recuperado"


def test_no_se_suelta_un_vaso_sin_saber_si_el_carro_trae_uno():
    ok = {"fresco": True, "en_muelle": True, "cuna": False}
    assert pr.puede_soltar_vaso(ok, True) == (True, "ok")
    assert pr.puede_soltar_vaso(ok, False) == (False, "sin_enlace")
    assert pr.puede_soltar_vaso({**ok, "fresco": False}, True) == (False, "estado_viejo")
    assert pr.puede_soltar_vaso({**ok, "cuna": True}, True) == (False, "cuna_ocupada")
    assert pr.puede_soltar_vaso({**ok, "cuna": None}, True) == (False, "cuna_desconocida")
    assert pr.puede_soltar_vaso({**ok, "en_muelle": False}, True) == (False, "no_esta_en_muelle")


def test_parada_segura_sin_pc():
    a = pr.accion_sin_pc()
    assert a["cintas"] == "detenidas" and a["prensa"] == "arriba" and a["desvio"] == "rechazo"


# ---------------------------------------------------------------------
# Sesion y memoria acotada (un lado se reinicia y el otro no)
# ---------------------------------------------------------------------

def test_emisor_reiniciado_con_sesion_nueva_se_ejecuta():
    """Bug: el PC (o el carro) se reinicia, sus ids vuelven a 1 y el otro
    lado, que siguio encendido, los tomaba por repetidos: ack sin ejecutar."""
    r = pr.Receptor()
    viejo = pr.Emisor(300, 1, sesion=111)
    for _ in range(3):
        assert r.recibir(viejo.enviar({"t": "cmd", "dst": "linea", "act": "avanzar"}, 0))[0]
    nuevo = pr.Emisor(300, 1, sesion=222)              # reiniciado: vuelve a id 1
    m = nuevo.enviar({"t": "cmd", "dst": "linea", "act": "avanzar"}, 0)
    assert m["id"] == 1 and m["s"] == 222
    assert r.recibir(m)[0] is True and r.reinicios == 1
    assert r.recibir(m)[0] is False                    # un reenvio de la sesion nueva sigue siendo repetido


def test_receptor_guarda_una_ventana_acotada_de_ids():
    r = pr.Receptor(ventana=64)
    for i in range(1, 1001):
        assert r.recibir({"t": "cmd", "id": i})[0]
    assert len(r.vistos) == 64                         # antes: 1000 (crecia sin tope)
    assert r.recibir({"t": "cmd", "id": 1000})[0] is False
    assert r.recibir({"t": "cmd", "id": 3})[0] is False    # muy viejo: repetido, no se ejecuta


def test_sin_sesion_se_comporta_como_antes():
    e = pr.Emisor(300, 1)
    assert "s" not in e.enviar({"t": "cmd"}, 0)


def test_secuencia_se_reinicia_con_el_esp32():
    s = pr.Secuencia()
    s.ver_sesion(5)
    assert [s.recibir(n) for n in (1, 2, 3)] == [0, 0, 0]
    s.ver_sesion(9)                                    # el ESP32 se reinicio (latido con otra `s`)
    assert s.recibir(1) == 0 and s.perdidos == 0
    # Sin el latido: `n` que retrocede = arranque nuevo, no 0 perdidos falsos ni `ultimo` pegado.
    s2 = pr.Secuencia()
    for n in (1, 2, 1500):
        s2.recibir(n)
    perdidos = s2.perdidos
    assert s2.recibir(1) == 0 and s2.recibir(3) == 1 and s2.perdidos == perdidos + 1


def test_nueva_sesion_en_rango():
    for _ in range(50):
        assert 1 <= pr.nueva_sesion() <= 65535


# ---------------------------------------------------------------------
# Tamano: un paquete de ESP-NOW lleva 250 bytes
# ---------------------------------------------------------------------

def test_detalle_largo_se_recorta_para_la_radio():
    e = pr.Emisor(500, None, sesion=65535)
    largo = "El camino recto hasta (1.20, -0.30) pasa por el muelle de carga (guías y topes): " * 5
    m = e.enviar({"t": "evt", "src": "carro", "ev": "respuesta_orden", "orden": 57, "ok": False,
                  "detalle": largo, "cuna": False, "x": 0.361, "y": -0.512}, 0, pr.RADIO_MAX_BYTES)
    assert pr.tamano(m) <= 250 and m["rec"] is True and m["detalle"].endswith("...")
    assert m["id"] in e.pendientes


def test_lo_que_no_cabe_ni_recortado_no_queda_en_la_cola():
    e = pr.Emisor(500, None)
    m = e.enviar({"t": "evt", "ev": "x", "datos": "a" * 400}, 0, pr.RADIO_MAX_BYTES)
    assert m is None and not e.pendientes and e.grandes == 1
    assert e.enviar({"t": "evt", "ev": "y"}, 0, pr.RADIO_MAX_BYTES)["id"] == 1   # no gasto un id
