"""Fase 7: el asistente (app/asistente.py). Sin internet: DeepSeek se
reemplaza por un cliente falso que devuelve el JSON que devolveria la API."""

import json
from types import SimpleNamespace

import pytest

from app import asistente, db


@pytest.fixture(autouse=True)
def sin_ollama(monkeypatch):
    """Las pruebas no dependen de que Ollama este corriendo en el PC."""
    monkeypatch.setattr(asistente, "cliente_local", lambda: None)


@pytest.fixture
def conexion(tmp_path):
    c = db.conectar(tmp_path / "prueba.db")
    yield c
    c.close()


# ---------------------------------------------------------------------
# interprete local
# ---------------------------------------------------------------------


@pytest.mark.parametrize("frase, esperado", [
    ("avanza 30 cm", {"cmd": "carro", "accion": "avanzar", "distancia_m": 0.3}),
    ("retrocede 5 centímetros", {"cmd": "carro", "accion": "retroceder", "distancia_m": 0.05}),
    ("gira 45 grados a la derecha", {"cmd": "carro", "accion": "girar", "grados": -45.0}),
    ("gira el carro 90 grados", {"cmd": "carro", "accion": "girar", "grados": 90.0}),
    ("da media vuelta", {"cmd": "carro", "accion": "girar", "grados": 180}),
    ("ve a x=1.2 y=-0.5", {"cmd": "carro", "accion": "ir_a", "x": 1.2, "y": -0.5}),
    ("lleva el carro a la meta", {"cmd": "carro", "accion": "ir_meta"}),
    ("vuelve al muelle", {"cmd": "carro", "accion": "volver_muelle"}),
    ("sigue la línea", {"cmd": "carro", "accion": "seguir_linea"}),
    ("detén el carro", {"cmd": "carro", "accion": "detener"}),
    ("pausa la línea", {"cmd": "pausar"}),
    ("paro de emergencia", {"cmd": "paro"}),
    ("pon el lote en 8 monedas por vaso", {"cmd": "lote", "valor": 8.0}),
])
def test_interprete_local_entiende_las_ordenes(frase, esperado):
    assert asistente.interpretar_orden_local(frase) == [esperado]


@pytest.mark.parametrize("frase", ["¿cuántos vasos llegaron a la meta?", "cuanto dinero hay",
                                   "dónde está el carro", "qué sensor detecta el metal"])
def test_una_pregunta_nunca_mueve_nada(frase):
    assert asistente.interpretar_orden_local(frase) == []


# ---------------------------------------------------------------------
# lista blanca
# ---------------------------------------------------------------------


def test_validar_acepta_lo_permitido_y_marca_el_origen():
    orden, motivo = asistente.validar_accion({"cmd": "carro", "accion": "avanzar", "distancia_m": 0.3})
    assert motivo == "" and orden == {"cmd": "carro", "accion": "avanzar", "distancia_m": 0.3, "origen": "asistente"}
    orden, _ = asistente.validar_accion({"cmd": "iniciar"})
    assert orden["escenario"] == "prueba_completa"


@pytest.mark.parametrize("accion", [
    {"cmd": "carro", "accion": "avanzar", "distancia_m": 5},        # demasiado lejos
    {"cmd": "carro", "accion": "retroceder", "distancia_m": 1},     # atras no tiene sensor
    {"cmd": "carro", "accion": "girar", "grados": 0},
    {"cmd": "carro", "accion": "volar"},
    {"cmd": "carro", "accion": "ir_a", "x": 1},                     # falta y
    {"cmd": "borrar_base_de_datos"},
    {"cmd": "lote", "valor": "muchas"},
    "avanzar",
])
def test_validar_descarta_lo_que_no_esta_permitido(accion):
    orden, motivo = asistente.validar_accion(accion)
    assert orden is None and motivo


# ---------------------------------------------------------------------
# documentacion y estado
# ---------------------------------------------------------------------


def test_lee_toda_la_documentacion_y_encuentra_lo_relacionado():
    secciones = asistente.corpus(recargar=True)
    archivos = {s.archivo for s in secciones}
    assert {"README.md", "CLAUDE.md", "docs/sensores.md", "docs/conexiones.md", "config/parametros.yaml"} <= archivos
    encontradas = asistente.buscar("sensor inductivo metal")
    assert any("nductivo" in s.titulo or "nductivo" in s.texto for s in encontradas[:3])
    assert sum(len(s.texto) for s in encontradas) <= asistente.MAX_CARACTERES_DOCS


def test_estado_en_vivo_sale_de_la_base(conexion):
    db.registrar_elemento(conexion, {"casilla": 1, "veredicto": "aceptada", "denominacion": 500, "valor": 500, "masa_g": 7.1})
    db.registrar_elemento(conexion, {"casilla": 2, "veredicto": "aceptada", "denominacion": 500, "valor": 500, "masa_g": 7.1})
    db.registrar_elemento(conexion, {"casilla": 3, "veredicto": "rechazada", "causa": "no_metalico"})
    db.registrar_evento(conexion, "supervisor", "tel", {"linea": "corriendo", "tick": 12})
    conexion.commit()
    e = asistente.estado_en_vivo(conexion)
    assert e["hay_datos"] and e["estado_linea"] == "corriendo"
    assert e["totales"]["valor_aceptado_pesos"] == 1000
    assert e["totales"]["monedas_aceptadas"] == 2
    assert e["aceptadas_por_denominacion"]["500"]["monedas"] == 2
    assert e["rechazos_por_causa"] == {"no_metalico": 1}
    # Las cifras de la respuesta local salen del estado, no se inventan.
    assert "$1.000" in asistente.responder_local("¿cuánto dinero se ha aceptado?", e)


# ---------------------------------------------------------------------
# atender: DeepSeek (falso) y respaldo local
# ---------------------------------------------------------------------


class ClienteFalso:
    """Imita `OpenAI(...).chat.completions.create` y guarda lo que se le mando."""

    def __init__(self, respuesta: dict | Exception):
        self.respuesta = respuesta
        self.enviado = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._crear))

    def _crear(self, **kwargs):
        self.enviado = kwargs
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        mensaje = SimpleNamespace(content=json.dumps(self.respuesta))
        return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


def test_con_deepseek_manda_estado_y_documentos_y_filtra_las_ordenes(conexion):
    cliente = ClienteFalso({"respuesta": "Avanzo 20 cm.", "acciones": [
        {"cmd": "carro", "accion": "avanzar", "distancia_m": 0.2},
        {"cmd": "carro", "accion": "avanzar", "distancia_m": 9}]})
    r = asistente.atender("avanza 20 cm", conexion, cliente=cliente)
    assert r.modo == "deepseek" and r.texto == "Avanzo 20 cm."
    assert r.ordenes == [{"cmd": "carro", "accion": "avanzar", "distancia_m": 0.2, "origen": "asistente"}]
    assert len(r.descartadas) == 1
    ultimo = cliente.enviado["messages"][-1]["content"]
    assert "ESTADO_EN_VIVO" in ultimo and "DOCUMENTACION" in ultimo
    assert cliente.enviado["response_format"] == {"type": "json_object"}
    # La conversacion queda guardada (la ven el dashboard y el visor 3D).
    conv = asistente.conversacion(conexion)
    assert [m["rol"] for m in conv] == ["usuario", "asistente"]
    assert conv[1]["acciones"] == r.ordenes


def test_si_deepseek_falla_responde_el_interprete_local(conexion):
    r = asistente.atender("gira 90 grados", conexion, cliente=ClienteFalso(ConnectionError("sin red")))
    assert r.modo == "local" and "DeepSeek no respondió" in r.aviso
    assert r.ordenes == [{"cmd": "carro", "accion": "girar", "grados": 90.0, "origen": "asistente"}]


def test_sin_deepseek_usa_el_interprete_local(conexion):
    r = asistente.atender("vuelve al muelle", conexion, usar_deepseek=False)
    assert r.modo == "local"
    assert r.ordenes[0]["accion"] == "volver_muelle"


# ---------------------------------------------------------------------
# modelo local (Ollama) y candados de las ordenes
# ---------------------------------------------------------------------


def test_sin_deepseek_pregunta_al_modelo_local(conexion):
    local = ClienteFalso({"respuesta": "Se aceptaron 0 monedas.", "acciones": []})
    r = asistente.atender("¿cuántas monedas hay?", conexion, cliente=ClienteFalso(ConnectionError("401")),
                          cliente_ia_local=local)
    assert r.modo == "ollama" and r.texto == "Se aceptaron 0 monedas."
    assert local.enviado["model"] == asistente.MODELO_LOCAL
    assert len(local.enviado["messages"][-1]["content"]) < 12000        # contexto corto para el modelo chico


def test_una_orden_clara_la_decide_el_interprete_y_no_el_modelo_chico(conexion):
    local = ClienteFalso({"respuesta": "x", "acciones": [{"cmd": "carro", "accion": "detener"}]})
    r = asistente.atender("gira 45 grados a la derecha", conexion, usar="ollama", cliente_ia_local=local)
    assert r.modo == "local" and local.enviado is None
    assert r.ordenes == [{"cmd": "carro", "accion": "girar", "grados": -45.0, "origen": "asistente"}]


def test_una_sola_orden_al_carro_por_mensaje(conexion):
    ds = ClienteFalso({"respuesta": "ok", "acciones": [
        {"cmd": "carro", "accion": "avanzar", "distancia_m": 0.2}, {"cmd": "carro", "accion": "girar", "grados": 90},
        {"cmd": "pausar"}]})
    r = asistente.atender("haz varias cosas", conexion, cliente=ds)
    assert [o.get("accion", o["cmd"]) for o in r.ordenes] == ["avanzar", "pausar"]
    assert r.descartadas


def test_el_signo_del_giro_lo_manda_la_frase():
    assert asistente.corregir_giros("gira a la derecha", [{"cmd": "carro", "accion": "girar", "grados": 45}])[0]["grados"] == -45
    assert asistente.corregir_giros("a la izquierda", [{"cmd": "carro", "accion": "girar", "grados": -30}])[0]["grados"] == 30


def test_costos_con_el_interprete_de_reglas():
    from app import costos

    texto = asistente.responder_local("¿cuánto cuesta el proyecto y dónde se puede ahorrar?", {"hay_datos": False})
    assert costos.pesos(costos.total()) in texto and "ahorrar" in texto



def test_mientras_piensa_se_sabe_quien_y_al_terminar_se_limpia(conexion):
    """El visor anima la nube (DeepSeek) o la laptop (modelo local) segun esto."""
    vistos = []

    class Espia(ClienteFalso):
        def _crear(self, **kwargs):
            vistos.append(asistente.pensando(conexion))
            return super()._crear(**kwargs)

    asistente.atender("¿qué hace la cortina?", conexion, cliente=ClienteFalso(ConnectionError("401")),
                      cliente_ia_local=Espia({"respuesta": "Detiene la zona de tapa y prensa.", "acciones": []}))
    assert vistos and vistos[0]["proveedor"] == "ollama" and "cortina" in vistos[0]["pregunta"]
    assert asistente.pensando(conexion) is None


def test_una_pregunta_nunca_da_ordenes_con_ningun_proveedor(conexion):
    ds = ClienteFalso({"respuesta": "Llegaron 2.", "acciones": [{"cmd": "carro", "accion": "ir_meta"}]})
    r = asistente.atender("¿cuántos vasos llegaron a la meta?", conexion, cliente=ds)
    assert r.ordenes == [] and r.descartadas


def test_medidas_sin_sensor_no_se_inventan(conexion):
    local = ClienteFalso({"respuesta": "La batería está en 7,4 V.", "acciones": []})
    r = asistente.atender("¿cuál es el voltaje de la batería ahora?", conexion, usar="ollama", cliente_ia_local=local)
    assert local.enviado is None and "no" in r.texto.lower() and "7,4" not in r.texto
