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
    # La frase pide mover el carro (si no, el candado de movimiento quita las del carro).
    r = asistente.atender("avanza, gira y pausa la línea", conexion, cliente=ds)
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


# ---------------------------------------------------------------------
# foco del grupo: monedas y carro (pedido 2026-09-28 (10), punto d)
# ---------------------------------------------------------------------


@pytest.fixture
def corrida(conexion):
    """Una corrida chica: monedas aceptadas y rechazadas, lo que vio la cámara y el carro en el muelle."""
    for i, (den, masa) in enumerate([(500, 7.1), (500, 7.4), (1000, 10.0)], start=1):
        db.registrar_elemento(conexion, {"casilla": i, "veredicto": "aceptada", "denominacion": den,
                                         "valor": den, "masa_g": masa})
    db.registrar_elemento(conexion, {"casilla": 4, "veredicto": "rechazada", "causa": "no_metalico"})
    db.registrar_elemento(conexion, {"casilla": 5, "veredicto": "rechazada", "causa": "perforado"})
    db.registrar_evento(conexion, "e3", "vision", {"casilla": 5, "diametro_mm": 22.1, "circularidad": 0.97,
                                                   "contornos_internos": 4, "clase": "otro", "confianza": 0.3,
                                                   "veredicto": "rechazada", "causa": "perforado"})
    db.registrar_evento(conexion, "carro", "evasion", {})
    db.registrar_evento(conexion, "carro", "en_muelle", {})
    db.registrar_evento(conexion, "supervisor", "tel", {
        "linea": "corriendo", "tick": 40, "almacen": {"50": 0, "100": 0, "200": 0, "500": 2, "1000": 1, "otras": 0},
        "almacen_valor": 2000, "monedas_por_vaso": 10,
        "carro": {"estado": "esperando_carga", "fase": "vuelta", "x": 0.36, "y": -0.5, "rumbo": 0,
                  "radio": {"enlace": True}}})
    conexion.commit()
    return asistente.estado_en_vivo(conexion)


def test_el_estado_pone_monedas_y_carro_antes_que_lo_demas(corrida):
    claves = list(corrida)
    assert claves.index("totales") < claves.index("carro") < claves.index("estado_linea")
    assert claves.index("rechazos_por_causa") < claves.index("carro")
    assert corrida["ultima_inspeccion_camara"]["diametro_mm"] == 22.1
    assert corrida["ultimos_rechazos"][0] == {"casilla": 5, "causa": "perforado", "hora": corrida["ultimos_rechazos"][0]["hora"]}
    assert corrida["carro"]["que_hace"] == "en el muelle"
    assert "en_muelle" in corrida["carro"]["ultimos_eventos"][0]


def test_rechazos_con_su_causa_y_su_estacion(corrida):
    texto = asistente.responder_local("¿cuántas monedas rechazó y por qué?", corrida)
    assert "Piezas rechazadas: 2" in texto and "E2" in texto and "agujeros" in texto
    assert "casilla 5" in texto                      # el último rechazo


@pytest.mark.parametrize("frase, esperado", [
    ("cuanto hay de 500", ["De $500: 2 monedas", "$1.000", "hay 2 guardadas"]),
    # Pregunta por el almacén: la cifra del tubo va primero (el modelo local repetía la primera cifra).
    ("cuantas monedas de mil hay en el almasen", ["tubo de $1.000 del almacén hay 1 monedas", "1 monedas aceptadas"]),
    ("¿qué hay en el almacén?", ["$2.000 guardados", "2 de $500"]),
])
def test_cuanto_hay_de_una_denominacion_y_en_el_almacen(corrida, frase, esperado):
    texto = asistente.responder_local(frase, corrida)
    assert all(e in texto for e in esperado), texto


def test_una_denominacion_no_se_confunde_con_otros_numeros(corrida):
    assert "De $200" not in asistente.responder_local("¿cuántos pasos por vuelta tiene el motor de 200?", corrida)


def test_lo_ultimo_que_vio_la_camara(corrida):
    texto = asistente.responder_local("¿cuál fue la última moneda que revisó la cámara?", corrida)
    assert "22.1 mm" in texto and "4 agujeros" in texto and "perforado" in texto


@pytest.mark.parametrize("frase", ["¿dónde está el carro?", "que esta asiendo el carro",
                                   "¿cuántas evasiones hizo el carro?"])
def test_donde_esta_y_que_hace_el_carro_sin_moverlo(corrida, conexion, frase):
    texto = asistente.responder_local(frase, corrida)
    assert "en el muelle" in texto and "evasiones" in texto and "conectada" in texto
    r = asistente.atender(frase, conexion, usar="reglas")
    assert r.ordenes == []


def test_lleva_el_carro_al_muelle():
    assert asistente.interpretar_orden_local("lleva el carro al muelle porfa") == \
        [{"cmd": "carro", "accion": "volver_muelle"}]


def test_la_busqueda_da_peso_extra_a_monedas_y_carro_sin_excluir_lo_demas():
    secciones = asistente.corpus(recargar=True)
    reglas = next(s for s in secciones if "Reglas de decisión del filtrado" in s.titulo)
    carro = next(s for s in secciones if "carro" in asistente.normalizar(s.titulo))
    assert reglas.foco > 1 and carro.foco > 1
    assert any(s.foco == 1 for s in secciones)                 # hay secciones sin peso extra
    # Lo demás se sigue encontrando: costos trae costos.
    assert "costo" in asistente.normalizar(asistente.buscar("¿Cuánto cuesta construir el proyecto en Colombia?")[0].titulo)
    assert "nductivo" in asistente.buscar("sensor inductivo metal")[0].titulo


def test_el_prompt_tiene_el_foco_y_los_umbrales_de_la_configuracion():
    from app import configuracion

    f = configuracion.cargar_parametros()["filtrado"]
    p = asistente.PROMPT_SISTEMA
    assert "FILTRADO DE MONEDAS" in p and "MOVIMIENTO DEL CARRO" in p and "Lo demás" in p
    assert f"{f['confianza_minima']:g}".replace(".", ",") in p
    assert '{"cmd":"carro","accion":"detener"}' in p            # las llaves del JSON siguen intactas


@pytest.mark.parametrize("frase, esperado", [
    ("como sabe el sistema si una pieza es de metal", "inductivo"),
    ("que filtro saca los votones con uecos", "perforado"),
    ("¿Por qué no se acepta una moneda de un euro si mide casi lo mismo que una de 500?", "CARA"),
    ("¿Por qué el proyecto no usa celdas de carga?", "prohibió"),
])
def test_lo_tecnico_del_filtrado_sin_modelo(frase, esperado):
    # Sin corrida también: no depende de las cifras.
    assert esperado in asistente.responder_local(frase, {"hay_datos": False})


def test_si_la_tabla_de_costos_falla_el_asistente_no_se_cae(monkeypatch, corrida):
    from app import costos

    def roto():
        raise KeyError("precio")

    monkeypatch.setattr(costos, "total", roto)
    texto = asistente.responder_local("¿cuánto cuesta el proyecto?", corrida)
    assert isinstance(texto, str) and texto


def test_peso_del_montaje_no_se_confunde_con_el_de_las_monedas(corrida):
    from app import masas

    kg = f"{masas.total() / 1000:.2f}".replace(".", ",")
    texto = asistente.responder_local("¿cuánto pesa el montaje completo?", corrida)
    assert kg in texto and "monedas aceptadas" not in texto
    # Y el de las monedas sigue siendo el de las monedas.
    assert "24.5 g" in asistente.responder_local("¿cuánto pesan las monedas aceptadas?", corrida)


def test_consumo_calculado_y_medidas_sin_sensor(corrida):
    texto = asistente.responder_local("¿cuánto consume la planta?", corrida)
    if (asistente.RAIZ / "docs" / "electrica.md").exists():
        assert " W " in texto and "CALCULADOS" in texto
    texto = asistente.responder_local("¿cuál es el voltaje de la batería ahora?", corrida)
    assert texto.startswith("No hay un sensor")


# ---------------------------------------------------------------------
# Revision 2026-09-28: pedir informacion NO es dar una orden. Sin "?" (el reconocimiento de voz no
# pone signos) estas frases movian el carro o paraban la linea.
# ---------------------------------------------------------------------

FRASES_TRAMPA = [
    "Dime cuántos vasos llegaron a la meta",            # antes: ir_meta
    "Explícame el paro de emergencia",                   # antes: paro
    "Cuéntame cómo hace la media vuelta el carro",       # antes: girar 180
    "explícame cómo el carro vuelve al muelle",          # antes: volver_muelle
    "Explica por qué el carro gira a la derecha",        # antes: girar -90
    "Muéstrame el lote de 10 monedas",                   # antes: lote 10
    "Resume la velocidad 8 de la simulación",            # antes: velocidad 8
    "el carro avanza 20 cm cuando ve un muro, explícalo",  # antes: avanzar 0,2
    "el paro de emergencia se activa con la cortina",    # antes: paro
]


@pytest.mark.parametrize("frase", FRASES_TRAMPA)
def test_pedir_informacion_no_da_ordenes_con_reglas(frase, conexion):
    assert asistente.interpretar_orden_local(frase) == []
    r = asistente.atender(frase, conexion, usar="reglas")
    assert r.ordenes == []


@pytest.mark.parametrize("frase", FRASES_TRAMPA[:4])
def test_pedir_informacion_no_da_ordenes_aunque_deepseek_las_proponga(frase, conexion):
    ds = ClienteFalso({"respuesta": "Listo.", "acciones": [
        {"cmd": "carro", "accion": "ir_meta"}, {"cmd": "paro"}, {"cmd": "lote", "valor": 10}]})
    r = asistente.atender(frase, conexion, cliente=ds)
    assert r.modo == "deepseek" and r.ordenes == [] and r.descartadas


def test_el_candado_de_movimiento_vale_tambien_para_deepseek(conexion):
    """Antes solo el modelo local tenia el candado: DeepSeek podia mover el carro con una frase
    que no pedia ningun movimiento."""
    ds = ClienteFalso({"respuesta": "ok", "acciones": [{"cmd": "carro", "accion": "girar", "grados": 90},
                                                       {"cmd": "embalar_parciales"}]})
    r = asistente.atender("empaca lo guardado en los tubos", conexion, cliente=ds)
    assert [o["cmd"] for o in r.ordenes] == ["embalar_parciales"]


@pytest.mark.parametrize("frase", ["paro de emergencia", "¡Paro!", "haz paro", "paro ya", "para todo ya",
                                   "detén la línea ahora mismo", "activa el paro de emergencia"])
def test_el_paro_sale_solo_con_un_imperativo(frase, conexion):
    assert asistente.interpretar_orden_local(frase) == [{"cmd": "paro"}]
    assert [o["cmd"] for o in asistente.atender(frase, conexion, usar="reglas").ordenes] == ["paro"]


@pytest.mark.parametrize("frase", ["detén la línea", "pausa la línea"])
def test_detener_la_linea_es_pausa_no_paro(frase, conexion):
    """El paro borra la corrida al salir (Iniciar): "detén la línea" es una PAUSA."""
    assert [o["cmd"] for o in asistente.atender(frase, conexion, usar="reglas").ordenes] == ["pausar"]


def test_deepseek_no_puede_parar_la_linea_sin_imperativo(conexion):
    ds = ClienteFalso({"respuesta": "Paro activado.", "acciones": [{"cmd": "paro"}]})
    assert asistente.atender("hay mucho ruido en el salón", conexion, cliente=ds).ordenes == []


@pytest.mark.parametrize("frase, esperado", [
    ("stop", {"cmd": "carro", "accion": "detener"}),
    ("carro adelante 20 cm", {"cmd": "carro", "accion": "avanzar", "distancia_m": 0.2}),
    ("da la vuelta", {"cmd": "carro", "accion": "girar", "grados": 180}),
    ("atrás 5 cm", {"cmd": "carro", "accion": "retroceder", "distancia_m": 0.05}),
])
def test_el_candado_no_le_quita_ordenes_legitimas_a_las_reglas(frase, esperado, conexion):
    r = asistente.atender(frase, conexion, usar="reglas")
    assert r.ordenes == [dict(esperado, origen="asistente")]


def test_el_lote_no_pasa_de_la_capacidad_del_tubo_de_la_config():
    from app.configuracion import cargar_parametros

    capacidad = cargar_parametros()["planta"]["capacidad_tubo"]
    assert asistente.validar_accion({"cmd": "lote", "valor": capacidad})[0]["valor"] == capacidad
    assert asistente.validar_accion({"cmd": "lote", "valor": capacidad + 15})[0] is None
    assert asistente.validar_accion({"cmd": "lote", "valor": 10.5})[0] is None      # no hay media moneda


# ---------------------------------------------------------------------
# Revision visual 2026-09-28: promesas sin orden, tiempos del carro y markdown
# ---------------------------------------------------------------------


def test_no_promete_mover_el_carro_si_no_manda_la_orden(conexion):
    ds = ClienteFalso({"respuesta": "Claro. El carro se moverá a tres posiciones aleatorias. Es rápido.",
                       "acciones": []})
    r = asistente.atender("llévate el carro a tres posiciones aleatorias", conexion, cliente=ds)
    assert r.ordenes == []
    assert "se moverá" not in r.texto and "no se mueve" in r.texto and "Es rápido." in r.texto


def test_con_la_orden_mandada_la_promesa_se_deja(conexion):
    ds = ClienteFalso({"respuesta": "Lo llevo al muelle.", "acciones": [{"cmd": "carro", "accion": "volver_muelle"}]})
    r = asistente.atender("lleva el carro al muelle", conexion, cliente=ds)
    assert r.texto == "Lo llevo al muelle." and r.ordenes[0]["accion"] == "volver_muelle"


def test_la_respuesta_se_guarda_sin_markdown(conexion):
    ds = ClienteFalso({"respuesta": "Uso **`qwen2.5-proyecto`** en local.", "acciones": []})
    r = asistente.atender("¿qué modelo usas?", conexion, cliente=ds)
    assert r.texto == "Uso qwen2.5-proyecto en local."
    assert asistente.conversacion(conexion)[-1]["texto"] == r.texto


def test_cuanto_se_demora_el_carro_sale_de_sus_eventos(conexion):
    """Misma cuenta que la pestaña Carro: carga -> meta -> en_muelle."""
    filas = [("2026-09-28T10:00:00", "carga"), ("2026-09-28T10:01:00", "meta"), ("2026-09-28T10:02:30", "en_muelle"),
             ("2026-09-28T10:03:00", "carga"), ("2026-09-28T10:04:10", "meta"), ("2026-09-28T10:05:40", "en_muelle")]
    for ts, tipo in filas:
        conexion.execute("INSERT INTO eventos (ts, origen, tipo, payload) VALUES (?, 'carro', ?, '{}')", (ts, tipo))
    conexion.commit()
    v = asistente.viajes_del_carro(conexion)
    assert v["viajes_completos"] == 2 and v["ultimo_viaje_completo_s"] == 160 and v["promedio_viaje_completo_s"] == 155
    assert v["promedio_ida_a_la_meta_s"] == 65
    estado = {"hay_datos": True, "ruta": {"tiempos_de_viaje": v}}
    texto = asistente.responder_local("¿qué tanto se demora el carro?", dict(asistente.estado_en_vivo(conexion), **estado))
    assert "155 s" in texto and "160 s" in texto


# ---------------------------------------------------------------------
# Revision logica 2026-09-29: a quien le habla la frase, pausa de la linea, "que + subjuntivo"
# y descripciones del recorrido automatico
# ---------------------------------------------------------------------


@pytest.mark.parametrize("frase, esperado", [
    # Punto 1: la linea de produccion no es la linea negra del carro, y una moneda que avanza no es el carro.
    ("sigue la línea de producción", [{"cmd": "reanudar"}]),          # antes: carro seguir_linea
    ("que siga la producción", [{"cmd": "reanudar"}]),
    ("retoma la planta", [{"cmd": "reanudar"}]),
    ("la moneda avanza por la cinta", []),                            # antes: carro avanzar 0,2 m
    ("la pieza retrocede", []),                                       # antes: carro retroceder
    ("la cinta gira", []),                                            # antes: carro girar 90
    ("la moneda va a la meta", []),                                   # antes: carro ir_meta
    ("avanza la cinta", []),
    # Punto 2: detener/parar la linea, todo, la planta o la produccion = PAUSA.
    ("detén todo", [{"cmd": "pausar"}]),                              # antes: carro detener
    ("detén la planta", [{"cmd": "pausar"}]),                         # antes: carro detener
    ("detén la producción", [{"cmd": "pausar"}]),                     # antes: carro detener
    ("para todo", [{"cmd": "pausar"}]),                               # antes: nada
    ("para la línea", [{"cmd": "pausar"}]),                           # antes: nada
    ("que pare todo", [{"cmd": "pausar"}]),
    ("para todo ya", [{"cmd": "paro"}]),                              # la urgencia explicita sigue siendo paro
    ("el carro sirve para todo", []),                                 # "para" preposicion
    ("gira el carro para el lado derecho", [{"cmd": "carro", "accion": "girar", "grados": -90.0}]),  # antes: detener
    # Punto 3: "que + subjuntivo" es un pedido.
    ("que avance el carro 30 cm", [{"cmd": "carro", "accion": "avanzar", "distancia_m": 0.3}]),  # antes: nada
    ("que el carro vaya a la meta", [{"cmd": "carro", "accion": "ir_meta"}]),                    # antes: nada
    ("que vuelva al muelle", [{"cmd": "carro", "accion": "volver_muelle"}]),                     # antes: nada
    ("que se detenga el carro", [{"cmd": "carro", "accion": "detener"}]),
    ("que de media vuelta", [{"cmd": "carro", "accion": "girar", "grados": 180}]),
])
def test_a_quien_le_habla_la_frase(frase, esperado, conexion):
    assert asistente.interpretar_orden_local(frase) == esperado
    r = asistente.atender(frase, conexion, usar="reglas")
    assert r.ordenes == [dict(o, origen="asistente") for o in esperado]


@pytest.mark.parametrize("frase", ["qué avance hubo", "que tan lejos está la meta", "que es el lote",
                                   "que hace el carro", "¿que vuelva al muelle?"])
def test_el_que_interrogativo_sigue_siendo_pregunta(frase):
    assert asistente.es_pregunta(frase) and asistente.interpretar_orden_local(frase) == []


@pytest.mark.parametrize("frase", ["la moneda avanza por la cinta", "sigue la línea de producción", "detén la planta"])
def test_deepseek_no_mueve_el_carro_si_la_frase_habla_de_otra_cosa(frase, conexion):
    ds = ClienteFalso({"respuesta": "Hecho.", "acciones": [{"cmd": "carro", "accion": "avanzar", "distancia_m": 0.2},
                                                           {"cmd": "carro", "accion": "seguir_linea"}]})
    r = asistente.atender(frase, conexion, cliente=ds)
    assert not any(o["cmd"] == "carro" for o in r.ordenes) and r.descartadas


def test_la_descripcion_del_recorrido_automatico_no_es_una_promesa(conexion):
    """Punto 4: "se moverá solo a la meta cuando lo carguen" describe el funcionamiento automático;
    antes se borraba y se agregaba "no se mueve"."""
    ds = ClienteFalso({"respuesta": "El carro se moverá solo a la meta cuando lo carguen. Luego vuelve.",
                       "acciones": []})
    r = asistente.atender("¿cómo funciona el carro?", conexion, cliente=ds)
    assert "se moverá solo a la meta" in r.texto and "no se mueve" not in r.texto
    # La promesa de hacerlo AHORA si se quita.
    texto, quito = asistente.quitar_promesas("Lo muevo a la meta. El carro se moverá a la meta.")
    assert quito and texto == ""
