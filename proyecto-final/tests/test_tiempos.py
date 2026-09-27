"""Presupuesto de tiempos del montaje real (control/tiempos.py)."""

from app.configuracion import cargar_parametros
from control.tiempos import presupuesto, tiempo_real_estimado_s


def _presupuesto(t=None):
    p = cargar_parametros()
    return presupuesto(t or p["tiempos_ms"], lote=p["planta"]["monedas_por_vaso"],
                       lecturas_por_decision=p["planta"]["lecturas_por_decision"],
                       fotos_por_moneda=p["planta"]["fotos_por_moneda"],
                       reaccion_cortina_max_ms=p["cortina_seguridad"]["reaccion_max_ms"])


def test_los_tiempos_configurados_caben():
    r = _presupuesto()
    fallan = [c.nombre for c in r["chequeos"] if not c.ok]
    assert r["todo_ok"], fallan


def test_ritmo_de_la_linea():
    r = _presupuesto()
    assert r["ciclo_monedas_ms"] == 1600
    assert round(r["elementos_por_minuto"]) == 38


def test_vision_lenta_no_cabe_y_lo_dice():
    t = dict(cargar_parametros()["tiempos_ms"], vision_captura_inferencia=1000)
    r = _presupuesto(t)
    malos = [c for c in r["chequeos"] if not c.ok]
    assert [c.nombre for c in malos] == ["La vision decide con la cinta quieta"]
    assert malos[0].margen_ms == 1000 - (2 * 1000 + 20)


def test_tiempo_real_de_una_corrida():
    assert tiempo_real_estimado_s(40, cargar_parametros()["tiempos_ms"]) == 64.0
