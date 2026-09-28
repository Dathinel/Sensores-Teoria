"""El conexionado (sim/conexiones.py) es coherente: cada hilo va de un pin
que existe a otro, ningun pin de header recibe dos hilos, los bornes no
llevan mas de dos, y los GPIO son los de la tabla de pines de la revision
final."""

from collections import Counter

import pytest

from sim import conexiones as cx

EXTREMOS = [(c["id"], e) for c in cx.CABLES for h in c["hilos"] for e in (h["de"], h["a"])]


@pytest.mark.parametrize("cable, extremo", EXTREMOS)
def test_cada_extremo_es_un_pin_que_existe(cable, extremo):
    cx.pin(extremo)


def test_ningun_pin_de_header_tiene_dos_hilos_y_los_bornes_como_mucho_dos():
    cuenta = Counter(e for _, e in EXTREMOS)
    for extremo, n in cuenta.items():
        tipo = cx.pin(extremo)["tipo"]
        if tipo in ("borne", "borne_din"):
            assert n <= 2, f"{extremo}: {n} hilos en un borne"
        elif tipo not in cx.TIPOS_MULTIPLES:
            assert n == 1, f"{extremo}: {n} hilos en un pin de header"


def test_todos_los_dispositivos_estan_conectados():
    usados = {e.split(".", 1)[0] for _, e in EXTREMOS}
    assert set(cx.DISPOSITIVOS) - usados == set()


def test_gpio_de_la_estacion_son_los_de_la_revision_final():
    assert set(cx.gpio_usados("esp32_fijo")) == {
        "G21", "G22", "G16", "G17", "G18", "G19", "G25", "G26", "G27", "G14", "G13",
        "G32", "G33", "G23", "G4", "G34", "G35", "G36", "G39"}


def test_gpio_del_carro_son_los_de_la_revision_final():
    assert set(cx.gpio_usados("esp32_carro")) == {
        "G25", "G26", "G27", "G33", "G32", "G13", "G4", "G18", "G19",
        "G34", "G35", "G36", "G39", "G16", "G17", "G23", "G21", "G22", "G14"}


@pytest.mark.parametrize("esp", ["esp32_fijo", "esp32_carro"])
def test_sin_pines_de_arranque_ni_de_memoria(esp):
    prohibidos = {f"G{n}" for n in (0, 2, 5, 12, 15, 6, 7, 8, 9, 10, 11, 1, 3)}
    assert set(cx.gpio_usados(esp)) & prohibidos == set()


def test_los_pines_solo_entrada_se_usan_solo_para_leer():
    # 34, 35, 36 y 39 no tienen salida: ahi solo van sensores.
    for c in cx.CABLES:
        for h in c["hilos"]:
            for extremo in (h["de"], h["a"]):
                if any(extremo.endswith(f".G{n}.S") for n in (34, 35, 36, 39)):
                    otro = h["a"] if extremo == h["de"] else h["de"]
                    assert otro.split(".")[0] in {"presencia", "opto", "hall", "ir_linea"}, (c["id"], otro)


def test_cada_servo_en_su_canal_del_pca9685():
    canales = {c["hilos"][0]["de"].split(".")[0]: c["hilos"][0]["a"] for c in cx.CABLES if c["tipo"] == "servo"}
    assert canales == {"servo_desvio": "pca9685.PWM0", "servo_obturador": "pca9685.PWM1", "servo_tapas": "pca9685.PWM2",
                       "servo_prensa": "pca9685.PWM3", "servo_empujador": "pca9685.PWM4", "servo_canaleta": "pca9685.PWM5"}


def test_cada_componente_tiene_su_estado_y_sus_dispositivos_existen():
    from sim.catalogos import COMPONENTES, SIMULACION

    assert {c["id"] for c in COMPONENTES} == set(SIMULACION)
    for c in COMPONENTES:
        assert all(d in cx.DISPOSITIVOS for d in c["dispositivos"]), c["id"]


def test_cada_dispositivo_es_de_un_componente_o_de_un_sensor():
    from sim.catalogos import CATALOGO_SENSORES, COMPONENTES, DISPOSITIVOS_DE_SENSOR

    de_componentes = {d for c in COMPONENTES for d in c["dispositivos"]}
    ids_sensores = {s["id"] for s in CATALOGO_SENSORES}
    assert all(v in ids_sensores for v in DISPOSITIVOS_DE_SENSOR.values())
    sueltos = set(cx.DISPOSITIVOS) - de_componentes - set(DISPOSITIVOS_DE_SENSOR)
    assert sueltos == set()


def test_ventilador_de_la_caja_va_al_buck_de_5v():
    hilos = {(h["de"], h["a"]) for c in cx.CABLES for h in c["hilos"] if "ventilador." in h["de"] + h["a"]}
    assert hilos == {("buck5.OUT+", "ventilador.+5V"), ("buck5.OUT-", "ventilador.GND")}


def test_plantillas_con_la_medida_de_las_piezas_reales():
    # Medidas de ficha (las mismas de app/visor3d/piezas/): el cableado sale de sus pines reales.
    tam = {k: cx.PLANTILLAS[k]["tamano"] for k in ("h206", "tcrt_mod", "ir5", "pack2s", "nema17")}
    assert tam == {"h206": [32, 14, 1.6], "tcrt_mod": [32, 14, 1.6], "ir5": [14, 74, 1.6],
                   "pack2s": [41, 76.6, 20.7], "nema17": [42, 42, 40]}
    for k in ("h206", "tcrt_mod", "fc51"):
        assert all(p.get("acodado") == [1, 0] for p in cx.PLANTILLAS[k]["pines"]), k


def test_placa_gvs_38_con_el_pinout_real_del_esp32():
    # Antena a -x, header de EN en -y (el mismo de piezas/electronica.js, crearPlacaGVS38P).
    en = [p for p in cx.PLANTILLAS["shield38"]["pines"] if p["n"] == "esp.EN.1"][0]
    g23 = [p for p in cx.PLANTILLAS["shield38"]["pines"] if p["n"] == "G23.S"][0]
    assert en["y"] < 0 and g23["y"] > 0
