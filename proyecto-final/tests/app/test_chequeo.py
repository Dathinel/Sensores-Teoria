"""Chequeo previo a la sustentacion (python -m app.chequeo): corre sin romperse y marca lo que falta."""

from app import chequeo


def test_revisa_todo_sin_romperse():
    filas = chequeo.revisar(rapido=True)
    assert filas and all(marca in (chequeo.BIEN, chequeo.AVISO, chequeo.FALLA) for marca, _, _ in filas)
    nombres = " ".join(que for _, que, _ in filas)
    for parte in ("Python", "Puerto", "Modelo local", "Whisper", "VL53L0X", "visor-portable"):
        assert parte in nombres


def test_el_lock_fija_python_y_paquetes():
    python, paquetes = chequeo._version_fija()
    assert python.count(".") == 2 and "streamlit" in paquetes and "pybullet" in paquetes


def test_todos_los_puertos_ocupados_por_otro_programa_es_falla(monkeypatch):
    from app import puertos
    monkeypatch.setattr(puertos, "escuchando", lambda puerto: True)
    monkeypatch.setattr(puertos, "es_nuestro", lambda puerto: False)
    assert all(marca == chequeo.FALLA for marca, _, _ in chequeo.puertos())


def test_si_otro_programa_tiene_el_8765_avisa_cual_se_usara(monkeypatch):
    from app import puertos
    monkeypatch.delenv(puertos.VARIABLE, raising=False)
    monkeypatch.setattr(puertos, "escuchando", lambda puerto: puerto == 8765)
    monkeypatch.setattr(puertos, "es_nuestro", lambda puerto: False)
    monkeypatch.setattr(puertos, "libre", lambda puerto: puerto != 8765)
    marca, que, detalle = chequeo.puertos()[0]
    assert marca == chequeo.AVISO and "8765" in que and "8766" in detalle
