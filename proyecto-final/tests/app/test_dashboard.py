"""El dashboard (paquete app/dashboard/) corre sin errores, sin datos y con una
corrida completa, en CADA pestaña, y tiene los avisos y los botones de su
inventario (docs/interfaz-dashboard.md). Pruebas de humo con el AppTest de
Streamlit: el script corre de verdad, en el mismo proceso, contra una base de
prueba (PLANTA_BD)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app import db
from app.supervisor import TERMINADA, Supervisor

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = str(RAIZ / "app" / "dashboard" / "inicio.py")
PESTANAS = ["Resumen", "Monedas y vasos", "Calidad del filtro", "Línea en vivo", "Pruebas", "Carro y ruta",
            "Montaje real", "Asistente", "Ayuda"]
# ?pestana=<clave> → lo que tiene que aparecer en esa pestaña (y no en las demás, que no se dibujan).
CONTENIDO = {
    "resumen": ["Recorrido de las piezas", "Qué está pasando", "Valor aceptado"],
    "monedas": ["Monedas aceptadas por denominación", "Valor acumulado en el tiempo", "Almacén: cuánto hay en cada tubo"],
    "calidad": ["Decisiones correctas", "Qué era cada pieza y qué decidió la línea", "Por qué se rechaza cada cosa"],
    "linea": ["Cinta de monedas", "Almacén tipo revólver", "Cinta de vasos", "Bitácora detallada"],
    "pruebas": ["Probar un filtro", "Colocar una pieza", "Sabotajes", "Fin de turno", "Qué contestó la línea"],
    "carro": ["Mapa de la pista", "Mover el carro", "Vasos entregados en la meta"],
    "montaje": ["Presupuesto de tiempos", "Costo del proyecto en Colombia", "Monedas por medir"],
    "asistente": ["Asistente del proyecto", "Cómo hablarle", "Ejemplos"],
    "ayuda": ["Cómo leer este tablero", "Palabras que aparecen", "visor.bat"],
}


@pytest.fixture(autouse=True)
def _sin_red_ni_modelos(monkeypatch):
    """Sin esperar a Internet, a Ollama ni a cargar Whisper (lo prueban tests/app/test_voz.py y test_asistente*)."""
    from app import asistente

    monkeypatch.setattr(asistente, "hay_internet", lambda *a, **k: True)
    monkeypatch.setattr(asistente, "cliente_local", lambda: None)
    monkeypatch.setattr(asistente, "_whisper_modelo", lambda: None)


def _correr(monkeypatch, bd, pestana: str | None = None) -> AppTest:
    monkeypatch.setenv("PLANTA_BD", str(bd))
    at = AppTest.from_file(SCRIPT, default_timeout=90)
    if pestana:
        at.query_params["pestana"] = pestana
    at.run()
    assert not at.exception, at.exception
    return at


def _texto(at: AppTest) -> str:
    partes = [m.value for m in at.markdown] + [str(c.value) for c in at.caption] + [str(i.value) for i in at.info]
    return " ".join(partes)


def _ordenes(bd) -> list[dict]:
    c = db.conectar(bd)
    try:
        return db.tomar_ordenes_pendientes(c)
    finally:
        c.close()


def _boton(at: AppTest, etiqueta: str):
    return next(b for b in at.button if b.label == etiqueta)


@pytest.fixture(scope="module")
def corrida_completa(tmp_path_factory):
    """Una corrida de punta a punta (carro de reemplazo, más rápido), terminada."""
    from app.configuracion import cargar_parametros

    p = cargar_parametros()
    p["simulacion"]["carro"] = "reemplazo"
    p["planta"]["conservar_almacen_entre_turnos"] = False
    ruta = tmp_path_factory.mktemp("completa") / "planta.db"
    s = Supervisor(ruta, parametros=p)
    s.aplicar_orden({"cmd": "iniciar"})
    for _ in range(400):
        if s.estado_linea == TERMINADA:
            break
        s.vuelta()
    s.cerrar()
    return ruta


@pytest.fixture
def linea_trabajando(tmp_path):
    """Una corrida a medias: la línea está 'corriendo' (los botones de prueba se habilitan)."""
    from app.configuracion import cargar_parametros

    p = cargar_parametros()
    p["simulacion"]["carro"] = "reemplazo"
    ruta = tmp_path / "vivo.db"
    s = Supervisor(ruta, parametros=p)
    s.aplicar_orden({"cmd": "iniciar"})
    for _ in range(40):
        s.vuelta()
    s.cerrar()
    return ruta


def _base_vacia(tmp_path):
    ruta = tmp_path / "vacia.db"
    db.conectar(ruta).close()
    return ruta


def _corrida_corta(tmp_path):
    ruta = tmp_path / "c.db"
    db.conectar(ruta).close()
    s = Supervisor(ruta)
    s.cerrar()
    return ruta


# ---------------------------------------------------------------------------
# cada pestaña carga, con y sin datos
# ---------------------------------------------------------------------------


def test_sin_datos_explica_como_arrancar(monkeypatch, tmp_path):
    at = _correr(monkeypatch, _base_vacia(tmp_path))
    assert any("No hay datos" in m.value for m in at.markdown)


@pytest.mark.parametrize("pestana", list(CONTENIDO))
def test_sin_datos_todas_las_pestanas_cargan(monkeypatch, tmp_path, pestana):
    at = _correr(monkeypatch, _base_vacia(tmp_path), pestana)
    assert [t.label.split(" ", 1)[1] for t in at.tabs] == PESTANAS


@pytest.mark.parametrize("pestana", list(CONTENIDO))
def test_con_una_corrida_completa_todas_las_pestanas_funcionan(monkeypatch, corrida_completa, pestana):
    at = _correr(monkeypatch, corrida_completa, pestana)
    assert [t.label.split(" ", 1)[1] for t in at.tabs] == PESTANAS
    texto = _texto(at)
    for esperado in CONTENIDO[pestana]:
        assert esperado in texto, (pestana, esperado)


@pytest.mark.parametrize("alias, esperado", [("produccion", "Monedas aceptadas por denominación"),
                                             ("rechazos", "Decisiones correctas"),
                                             ("inspeccion", "Decisiones correctas"),
                                             ("ruta", "Mapa de la pista"),
                                             ("replicacion", "Presupuesto de tiempos")])
def test_los_nombres_viejos_de_pestana_siguen_abriendo_la_correcta(monkeypatch, corrida_completa, alias, esperado):
    assert esperado in _texto(_correr(monkeypatch, corrida_completa, alias))


def test_solo_se_dibuja_la_pestana_abierta(monkeypatch, corrida_completa):
    texto = _texto(_correr(monkeypatch, corrida_completa, "ayuda"))
    assert "Cómo leer este tablero" in texto and "Recorrido de las piezas" not in texto


# ---------------------------------------------------------------------------
# cabecera: avisos que se ven de lejos
# ---------------------------------------------------------------------------


def test_sin_internet_y_sin_simulacion_se_ve_de_lejos(monkeypatch, tmp_path):
    """Usuario, 2026-09-27: que sea evidente que no hay internet o que no es en vivo."""
    import urllib.request

    from app import asistente

    ruta = _corrida_corta(tmp_path)
    monkeypatch.setattr(asistente, "hay_internet", lambda *a, **k: False)

    def sin_supervisor(*a, **k):
        raise OSError("nada escuchando")

    monkeypatch.setattr(urllib.request, "urlopen", sin_supervisor)
    texto = _texto(_correr(monkeypatch, ruta))
    assert "📴 SIN INTERNET" in texto and "NO ES EN VIVO" in texto
    assert "SIMULACIÓN (PyBullet)" in texto


def test_con_internet_no_hay_aviso_de_internet(monkeypatch, tmp_path):
    texto = _texto(_correr(monkeypatch, _corrida_corta(tmp_path)))
    assert "con internet" in texto and "📴 SIN INTERNET" not in texto


def test_aviso_esp32_emulado(monkeypatch, tmp_path):
    ruta = _corrida_corta(tmp_path)
    c = db.conectar(ruta)
    tel = db.ultima_telemetria(c)
    tel.update(backend="real", hardware={"emulada": True})
    db.registrar_evento(c, "supervisor", "tel", tel)
    c.commit()
    c.close()
    from app.dashboard import datos

    monkeypatch.setattr(datos, "simulacion_viva", lambda: True)
    texto = _texto(_correr(monkeypatch, ruta))
    assert "ESP32 EMULADO" in texto and "NO ES EN VIVO" not in texto


def test_una_prueba_de_un_filtro_se_anuncia_con_su_resultado(monkeypatch, tmp_path):
    from app.configuracion import cargar_parametros

    p = cargar_parametros()
    p["simulacion"]["carro"] = "reemplazo"
    p["simulacion"]["errores_sensores"] = False
    s = Supervisor(tmp_path / "f.db", parametros=p)
    s.aplicar_orden({"cmd": "iniciar", "escenario": "no_metalico"})
    for _ in range(300):
        if s.estado_linea == TERMINADA:
            break
        s.vuelta()
    s.cerrar()
    at = _correr(monkeypatch, tmp_path / "f.db", "pruebas")
    texto = _texto(at)
    assert "Prueba de un filtro: Material: no metálico" in texto and "otras causas" not in texto
    assert [b.label for b in at.button if "Probar solo este filtro" in b.label]


# ---------------------------------------------------------------------------
# barra lateral: manejar la línea
# ---------------------------------------------------------------------------


def test_barra_lateral_tiene_sus_controles(monkeypatch, corrida_completa):
    at = _correr(monkeypatch, corrida_completa)
    botones = [b.label for b in at.sidebar.button]
    assert botones == ["Empezar una corrida nueva", "Pausa", "Seguir", "PARO DE EMERGENCIA"]
    assert [s.label for s in at.sidebar.select_slider] == ["Velocidad de la simulación"]
    assert [n.label for n in at.sidebar.number_input] == ["Monedas por vaso"]
    assert [s.label for s in at.sidebar.slider] == ["Confianza mínima del reconocimiento",
                                                    "Errores forzados del reconocimiento"]
    assert [c.label for c in at.sidebar.checkbox] == ["Empezar con lo que quedó guardado en los tubos"]
    # Con la corrida terminada: se puede empezar otra, pero no pausar, seguir ni parar.
    assert [b.disabled for b in at.sidebar.button] == [False, True, True, True]


def test_botones_de_control_mandan_sus_ordenes(monkeypatch, linea_trabajando):
    at = _correr(monkeypatch, linea_trabajando)
    assert not _boton(at, "Pausa").disabled and not _boton(at, "PARO DE EMERGENCIA").disabled
    _boton(at, "Pausa").click().run()
    _boton(at, "PARO DE EMERGENCIA").click().run()
    _boton(at, "Empezar una corrida nueva").click().run()
    at.sidebar.number_input[0].set_value(7).run()
    assert not at.exception, at.exception
    ordenes = _ordenes(linea_trabajando)
    assert [o["cmd"] for o in ordenes] == ["pausar", "paro", "iniciar", "lote"]
    assert ordenes[2]["escenario"] == "prueba_completa" and ordenes[3]["valor"] == 7


# ---------------------------------------------------------------------------
# pestaña Pruebas: todo lo que se le hace a la planta, en un lugar
# ---------------------------------------------------------------------------

BOTONES_DE_PRUEBA = ["Probar solo este filtro", "Ponerla en la próxima carga", "Retirar un vaso",
                     "Cambiar por un vaso igual", "Cambiar por una figura", "Vaso con algo adentro", "✋ Mano en la carga",
                     "✋ Mano que saca un vaso", "✋ Mano en tapa/prensa", "📡 Cortar la radio del carro",
                     "📦 Empacar lo guardado en los tubos (fin de turno)"]


def test_pestana_pruebas_tiene_todo(monkeypatch, linea_trabajando):
    at = _correr(monkeypatch, linea_trabajando, "pruebas")
    etiquetas = [b.label for b in at.button]
    for b in BOTONES_DE_PRUEBA:
        assert b in etiquetas, b
    assert {s.label for s in at.selectbox} >= {"Filtro", "Pieza"}
    _boton(at, "Probar solo este filtro").click().run()
    _boton(at, "Ponerla en la próxima carga").click().run()
    _boton(at, "✋ Mano en la carga").click().run()
    assert not at.exception, at.exception
    ordenes = _ordenes(linea_trabajando)
    assert ordenes[0] == {"cmd": "iniciar", "escenario": "no_metalico"}
    assert ordenes[1]["cmd"] == "colocar" and ordenes[1]["pieza"]
    assert ordenes[2] == {"cmd": "sabotaje", "tipo": "mano_carga"}


def test_sin_linea_los_sabotajes_estan_apagados(monkeypatch, corrida_completa):
    at = _correr(monkeypatch, corrida_completa, "pruebas")
    assert _boton(at, "✋ Mano en la carga").disabled and _boton(at, "Retirar un vaso").disabled
    assert not _boton(at, "Probar solo este filtro").disabled   # una prueba de filtro empieza otra corrida


# ---------------------------------------------------------------------------
# Carro y ruta: órdenes al carro
# ---------------------------------------------------------------------------


def test_ordenes_al_carro(monkeypatch, corrida_completa):
    at = _correr(monkeypatch, corrida_completa, "carro")
    for b in ["Detener", "Retomar la línea", "Ir a la meta", "Volver al muelle", "Avanzar", "Retroceder (máx. 30)",
              "Izquierda", "Derecha", "Ir al punto (x, y)"]:
        assert b in [x.label for x in at.button], b
    _boton(at, "Avanzar").click().run()
    _boton(at, "Derecha").click().run()
    _boton(at, "Ir a la meta").click().run()
    assert not at.exception, at.exception
    assert _ordenes(corrida_completa) == [
        {"cmd": "carro", "accion": "avanzar", "distancia_m": 0.2},
        {"cmd": "carro", "accion": "girar", "grados": -45},
        {"cmd": "carro", "accion": "ir_meta"},
    ]


# ---------------------------------------------------------------------------
# Asistente
# ---------------------------------------------------------------------------


def test_pestana_asistente_tiene_sus_controles(monkeypatch, tmp_path):
    at = _correr(monkeypatch, _base_vacia(tmp_path), "asistente")
    etiquetas = [b.label for b in at.button]
    assert sum(1 for e in etiquetas if e.startswith("¿") or e[0].isupper()) >= 9   # 8 ejemplos + borrar
    assert "Borrar la conversación" in etiquetas and "Avanza el carro 30 cm" in etiquetas
    assert [t.label for t in at.toggle] == ["🔊 Responder en voz alta"]
    assert "Quién responde" in [s.label for s in at.selectbox]
    assert len(at.chat_input) == 1
    assert "Todavía no le ha preguntado nada." in _texto(at)


def test_el_asistente_responde_en_el_dashboard_sin_deepseek(monkeypatch, tmp_path):
    """Fase 7: sin clave (o sin internet) responde el intérprete local y la
    orden queda en la tabla `ordenes` para el supervisor."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    ruta = tmp_path / "a.db"
    db.conectar(ruta).close()
    at = _correr(monkeypatch, ruta, "asistente")
    at.chat_input[0].set_value("avanza el carro 25 cm").run()
    assert not at.exception, at.exception
    assert _ordenes(ruta) == [{"cmd": "carro", "accion": "avanzar", "distancia_m": 0.25, "origen": "asistente"}]
    assert any("25 cm" in m.value for m in at.markdown)
    # los pesos no se leen como fórmula de LaTeX ("$500 ... $1.000")
    from app import asistente

    c = db.conectar(ruta)
    asistente.guardar_mensaje(c, "asistente", "Hay $500 y $1.000")
    c.close()
    at.run()
    assert any(r"Hay \$500 y \$1.000" in m.value for m in at.markdown)


def test_un_ejemplo_del_asistente_se_pregunta_con_un_clic(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    ruta = _base_vacia(tmp_path)
    at = _correr(monkeypatch, ruta, "asistente")
    _boton(at, "Lleva el carro a la meta").click().run()
    assert not at.exception, at.exception
    assert _ordenes(ruta) == [{"cmd": "carro", "accion": "ir_meta", "origen": "asistente"}]


# ---------------------------------------------------------------------------
# cómo se arranca
# ---------------------------------------------------------------------------


def test_lanzar_arranca_el_paquete_nuevo():
    fuente = (RAIZ / "app" / "lanzar.py").read_text(encoding="utf-8")
    assert '"app/dashboard/inicio.py"' in fuente
    # --reemplazar reconoce el dashboard viejo (app/dashboard.py) y el nuevo (app/dashboard/inicio.py).
    assert "Contains('app/dashboard')" in fuente
    assert Path(SCRIPT).exists() and not (RAIZ / "app" / "dashboard.py").exists()
