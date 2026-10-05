"""Charla de prueba con el asistente (python -m app.charla): sin clave, sobre una copia de la base."""

import io

from app import charla


def test_responde_sin_clave_y_no_toca_la_base(monkeypatch, tmp_path, capsys):
    base = tmp_path / "no-existe.db"
    monkeypatch.setenv("PLANTA_BD", str(base))
    monkeypatch.setattr("sys.argv", ["charla"])
    monkeypatch.setattr("sys.stdin", io.StringIO("avanza 20 cm\nsalir\n"))
    charla.main()
    salida = capsys.readouterr().out
    assert "20 cm" in salida and "NO se manda a la línea" in salida and "[respondió: local]" in salida
    assert not base.exists()
