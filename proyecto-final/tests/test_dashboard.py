"""El dashboard corre sin errores, sin datos y con una corrida completa
(prueba de humo con el AppTest de Streamlit)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.supervisor import TERMINADA, Supervisor

SCRIPT = str(Path(__file__).resolve().parent.parent / "app" / "dashboard.py")
PESTANAS = ["Resumen", "Monedas y vasos", "Calidad del filtro", "Línea en vivo", "Carro y ruta", "Montaje real",
            "Asistente", "Ayuda"]


def _correr(monkeypatch, bd):
    monkeypatch.setenv("PLANTA_BD", str(bd))
    at = AppTest.from_file(SCRIPT, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def test_sin_datos_explica_como_arrancar(monkeypatch, tmp_path):
    from app import db

    db.conectar(tmp_path / "vacia.db").close()
    at = _correr(monkeypatch, tmp_path / "vacia.db")
    assert any("No hay datos" in m.value for m in at.markdown)


def test_con_una_corrida_completa_todas_las_pestanas_funcionan(monkeypatch, tmp_path):
    from app.configuracion import cargar_parametros

    p = cargar_parametros()
    p["simulacion"]["carro"] = "reemplazo"
    p["planta"]["conservar_almacen_entre_turnos"] = False
    s = Supervisor(tmp_path / "planta.db", parametros=p)
    s.aplicar_orden({"cmd": "iniciar"})
    for _ in range(400):
        if s.estado_linea == TERMINADA:
            break
        s.vuelta()
    s.conexion.close()
    at = _correr(monkeypatch, tmp_path / "planta.db")
    assert [t.label.split(" ", 1)[1] for t in at.tabs] == PESTANAS
    texto = " ".join(m.value for m in at.markdown)
    assert "Recorrido de las piezas" in texto and "Qué está pasando" in texto
    assert any(m.label.endswith("Decisiones correctas") for m in at.metric)


def test_el_asistente_responde_en_el_dashboard_sin_deepseek(monkeypatch, tmp_path):
    """Fase 7: sin clave (o sin internet) responde el interprete local y la
    orden queda en la tabla `ordenes` para el supervisor."""
    from app import db

    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    from app import asistente

    monkeypatch.setattr(asistente, "cliente_local", lambda: None)
    db.conectar(tmp_path / "a.db").close()
    at = _correr(monkeypatch, tmp_path / "a.db")
    at.chat_input[0].set_value("avanza el carro 25 cm").run()
    assert not at.exception, at.exception
    c = db.conectar(tmp_path / "a.db")
    ordenes = db.tomar_ordenes_pendientes(c)
    c.close()
    assert ordenes == [{"cmd": "carro", "accion": "avanzar", "distancia_m": 0.25, "origen": "asistente"}]
    assert any("25 cm" in m.value for m in at.markdown)
    # los pesos no se leen como formula de LaTeX ("$500 ... $1.000")
    from app import asistente

    c = db.conectar(tmp_path / "a.db")
    asistente.guardar_mensaje(c, "asistente", "Hay $500 y $1.000")
    c.close()
    at.run()
    assert any(r"Hay \$500 y \$1.000" in m.value for m in at.markdown)
