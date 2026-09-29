"""Presupuesto de tiempos del montaje real (control/tiempos.py)."""

from app.configuracion import cargar_parametros
from control.tiempos import presupuesto, tiempo_real_estimado_s


def _presupuesto(t=None):
    p = cargar_parametros()
    return presupuesto(t or p["tiempos_ms"], lote=p["planta"]["monedas_por_vaso"],
                       lecturas_por_decision=p["planta"]["lecturas_por_decision"],
                       fotos_por_moneda=p["planta"]["fotos_por_moneda"],
                       reaccion_cortina_max_ms=p["cortina_seguridad"]["reaccion_max_ms"])


CARRUSEL = ["El carrusel pone el tubo bajo la carga antes de que caiga la moneda",
            "El carrusel suelta un lote y vuelve entre dos monedas"]
TAPA = "Reintento de la tapa (peor caso: dos tapas)"


def test_los_tiempos_configurados_caben_salvo_el_carrusel():
    """Todo cabe menos el carrusel (2026-09-28): `carrusel_giro` es ahora el tiempo
    REAL del firmware (media vuelta del 28BYJ-48 a 2 ms por medio paso = 4,1 s) y no
    entra en el ciclo de 1,6 s. No se esconde: los dos chequeos quedan en NO CABE y
    su explicacion dice que se ajusta (la cinta de monedas espera al carrusel)."""
    r = _presupuesto()
    fallan = [c for c in r["chequeos"] if not c.ok]
    assert [c.nombre for c in fallan] == CARRUSEL  # la tapa ya cabe: pausa de vasos 1400 ms (2026-09-29)
    assert not r["todo_ok"]
    for c in fallan[:2]:
        assert "ESPERA" in c.explicacion and "cinta de monedas" in c.explicacion


def test_carrusel_giro_es_el_tiempo_real_del_firmware():
    """Antes: 500 ms en la config y ~4,1 s en la placa. Ahora uno sale del otro."""
    p = cargar_parametros()
    fw = p["firmware"]
    media_vuelta = fw["carrusel_pasos_por_vuelta"] // 2 * fw["carrusel_ms_por_paso"]
    assert p["tiempos_ms"]["carrusel_giro"] == media_vuelta == 4096


def test_con_un_carrusel_que_si_alcanza_todo_cabe():
    """La cuenta no esta amanada: con un giro que quepa, los chequeos pasan."""
    t = dict(cargar_parametros()["tiempos_ms"], carrusel_giro=450, pausa_casilla_vasos=1400)
    assert _presupuesto(t)["todo_ok"]


def test_ritmo_de_la_linea():
    r = _presupuesto()
    assert r["ciclo_monedas_ms"] == 1600
    assert round(r["elementos_por_minuto"]) == 38


def test_vision_lenta_no_cabe_y_lo_dice():
    t = dict(cargar_parametros()["tiempos_ms"], vision_captura_inferencia=1000)
    r = _presupuesto(t)
    malos = [c for c in r["chequeos"] if not c.ok and c.nombre not in CARRUSEL + [TAPA]]
    assert [c.nombre for c in malos] == ["La visión decide con la cinta quieta"]
    assert malos[0].margen_ms == 1000 - (2 * 1000 + 20)


def test_tiempo_real_de_una_corrida():
    assert tiempo_real_estimado_s(40, cargar_parametros()["tiempos_ms"]) == 64.0


def test_el_reintento_de_la_tapa_es_el_peor_caso_y_dice_que_pasa():
    """Bug (revision 2026-09-28): solo se media UN intento de tapa (680 ms en
    una pausa de 800). El paso 11 suelta otra tapa si la camara no ve la
    primera: dos intentos = 2 x (tapa_caida + N x camara_vasos_cuadro) = 1360 ms,
    que NO caben. El chequeo lo dice y explica que la cinta de vasos espera una
    pausa mas (y que la simulacion no cuenta ese tiempo)."""
    p = cargar_parametros()
    t, n = p["tiempos_ms"], p["planta"]["lecturas_por_decision"]
    r = _presupuesto()
    por_nombre = {c.nombre: c for c in r["chequeos"]}
    uno = por_nombre["La tapa cae y la cámara la confirma en la misma pausa"]
    dos = por_nombre[TAPA]
    assert uno.ok and uno.necesita_ms == t["tapa_caida"] + n * t["camara_vasos_cuadro"]
    assert dos.necesita_ms == 2 * uno.necesita_ms == 1360 and dos.disponible_ms == t["pausa_casilla_vasos"]
    # Grupo, 2026-09-29: la pausa de vasos se alargó (1400 ms) para que el peor caso quepa.
    assert dos.ok
    assert "alargó" in dos.explicacion and "simulación" in dos.explicacion


def test_los_textos_usan_las_estaciones_de_hoy_y_con_tildes():
    """Los chequeos se muestran al usuario (dashboard y docs/replicacion.md):
    la vision es E3 desde el filtro total (antes decia E5) y van con tildes."""
    textos = " ".join(c.nombre + " " + c.explicacion for c in _presupuesto()["chequeos"])
    for viejo in ("E5", "E6", "E7", " vision ", " camara ", " posicion ", " estacion "):
        assert viejo not in textos, viejo
    assert "E3" in textos and "visión" in textos and "cámara" in textos


def test_ningun_tiempo_ni_error_de_sensor_queda_sin_uso():
    """Revision 2026-09-28: `tiempos_ms.esp_now_latencia` y
    `errores_sensores.camara_vasos.error_fondo` estaban en la configuracion
    (y en docs/replicacion.md como si se usaran) pero no los leia nadie."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    codigo = " ".join(f.read_text(encoding="utf-8") for d in ("control", "sim", "app", "firmware")
                      for f in (raiz / d).rglob("*.py") if "salida" not in f.parts)
    p = cargar_parametros()
    sin_uso = [k for k in p["tiempos_ms"] if k not in codigo]
    for sensor, errores in p["errores_sensores"].items():
        sin_uso += [f"{sensor}.{k}" for k in errores if f'"{k}"' not in codigo and f"'{k}'" not in codigo]
    assert not sin_uso
