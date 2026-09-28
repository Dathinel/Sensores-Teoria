"""Voz y asistente SIN internet (usuario, 2026-09-27): oir con Whisper local y hablar con la
voz de Windows; DeepSeek ni se intenta (sin esperar su tiempo de espera)."""

from app import asistente, db


def test_sin_internet_oye_con_whisper_local(monkeypatch):
    monkeypatch.setattr(asistente, "hay_internet", lambda *a, **k: False)
    monkeypatch.setattr(asistente, "transcribir_local", lambda audio: "avanza 20 centímetros")
    assert asistente.transcribir(b"RIFF...") == ("avanza 20 centímetros", "Whisper local (sin internet)")


def test_sin_internet_y_audio_mudo_lo_dice(monkeypatch):
    monkeypatch.setattr(asistente, "hay_internet", lambda *a, **k: False)
    monkeypatch.setattr(asistente, "transcribir_local", lambda audio: "")
    texto, motivo = asistente.transcribir(b"RIFF...")
    assert texto is None and "No se entendió" in motivo


def test_sin_internet_habla_con_la_voz_de_windows(monkeypatch):
    monkeypatch.setattr(asistente, "hay_internet", lambda *a, **k: False)
    monkeypatch.setattr(asistente, "voz_local", lambda texto: b"RIFF" + b"0" * 2000)
    audio, formato = asistente.voz("Hola")
    assert formato == "wav" and audio.startswith(b"RIFF")


def test_sin_internet_no_se_consulta_deepseek(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-falsa")
    monkeypatch.setattr(asistente, "hay_internet", lambda *a, **k: False)
    monkeypatch.setattr(asistente, "cliente_local", lambda: None)

    def no_llamar(*a, **k):
        raise AssertionError("sin internet no se pregunta a DeepSeek")

    monkeypatch.setattr(asistente, "preguntar_deepseek", no_llamar)
    con = db.conectar(tmp_path / "a.db")
    r = asistente.atender("avanza 20 cm", con)
    assert r.modo == "local" and r.ordenes and "Sin internet" in r.aviso


def test_hay_internet_recuerda_la_respuesta(monkeypatch):
    import socket

    llamadas = []

    def conectar(*a, **k):
        llamadas.append(a)
        raise OSError("sin red")

    monkeypatch.setattr(socket, "create_connection", conectar)
    monkeypatch.setitem(asistente._internet, "t", 0.0)
    assert asistente.hay_internet() is False
    n = len(llamadas)
    assert asistente.hay_internet() is False and len(llamadas) == n   # no vuelve a probar enseguida
    monkeypatch.setitem(asistente._internet, "t", 0.0)
