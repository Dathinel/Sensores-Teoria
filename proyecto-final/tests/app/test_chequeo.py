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


def test_un_puerto_ocupado_por_otro_programa_es_falla(monkeypatch):
    monkeypatch.setattr(chequeo, "_abierto", lambda puerto: True)

    def nadie(*a, **k):
        raise OSError("no es nuestro")

    monkeypatch.setattr(chequeo.urllib.request, "urlopen", nadie)
    assert all(marca == chequeo.FALLA for marca, _, _ in chequeo.puertos())
