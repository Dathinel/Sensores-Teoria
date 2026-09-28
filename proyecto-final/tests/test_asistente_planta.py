"""El asistente no promete que el carro atraviese la planta (usuario, 2026-09-27: el modelo local
contesto "cruzara por el" y mando al carro a (-0,5; 0), dentro de la planta; se trabo)."""

import pytest

from app import asistente, db

FRASE_REAL = ("ahora haga que vaya a donde esta el filtro de monedas, lo atraviese y que el propio "
              "sistema lo pase por el lado con sus sensores")


@pytest.mark.parametrize("frase", [FRASE_REAL, "cruza la cinta de vasos", "lleva el carro por encima de la planta"])
def test_pedir_atravesar_la_planta_se_detecta(frase):
    assert asistente.pide_atravesar(frase)


@pytest.mark.parametrize("frase", ["avanza 20 cm", "ve a la meta", "¿cómo cruza el carro los muros?",
                                   "¿por qué la moneda pasa por encima de la cinta?", "crucé la cámara con la mano"])
def test_lo_demas_no_se_confunde(frase):
    assert not asistente.pide_atravesar(frase)


@pytest.mark.parametrize("usar", ["auto", "ollama", "deepseek", "reglas"])
def test_con_cualquier_proveedor_dice_que_no_y_no_mueve_nada(monkeypatch, tmp_path, usar):
    def no_llamar(*a, **k):
        raise AssertionError("no hace falta preguntarle a ningun modelo")

    monkeypatch.setattr(asistente, "preguntar_deepseek", no_llamar)
    monkeypatch.setattr(asistente, "preguntar_llm", no_llamar)
    r = asistente.atender(FRASE_REAL, db.conectar(tmp_path / "a.db"), usar=usar)
    assert r.ordenes == [] and "no se puede" in r.texto.lower()


def test_un_destino_dentro_de_la_planta_no_se_manda(monkeypatch, tmp_path):
    """Lo que paso de verdad: el modelo propuso ir_a (-0,5; 0) prometiendo el movimiento."""
    propuesta = {"respuesta": "El carro se moverá a la posición del filtro de monedas.",
                 "acciones": [{"cmd": "carro", "accion": "ir_a", "x": -0.5, "y": 0.0}]}
    monkeypatch.setattr(asistente, "preguntar_deepseek", lambda *a, **k: dict(propuesta))
    r = asistente.atender("vaya al punto -0.5, 0", db.conectar(tmp_path / "a.db"), usar="deepseek", cliente=object())
    assert r.ordenes == []
    assert r.texto.startswith("No lo muevo") and "(-0.50, 0.00)" in r.texto


def test_un_destino_en_la_pista_si_se_manda(monkeypatch, tmp_path):
    propuesta = {"respuesta": "Voy.", "acciones": [{"cmd": "carro", "accion": "ir_a", "x": 1.2, "y": -0.3}]}
    monkeypatch.setattr(asistente, "preguntar_deepseek", lambda *a, **k: dict(propuesta))
    r = asistente.atender("vaya al punto 1.2, -0.3", db.conectar(tmp_path / "a.db"), usar="deepseek", cliente=object())
    assert [o["accion"] for o in r.ordenes] == ["ir_a"]
