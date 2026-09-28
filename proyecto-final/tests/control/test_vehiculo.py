"""Punto 14: el carro sigue la linea, esquiva los tres muros, llega a la
meta, espera que le saquen el vaso y vuelve SOLO al muelle, entrando de
reversa (sim/vehiculo_sim.py con fisica real, control/vehiculo.py).

Cada viaje de ida y vuelta son ~4-5 minutos simulados (~7 s de reloj)."""

import copy
import math

import pytest

from app.configuracion import cargar_parametros
from sim.vehiculo_sim import SimCarro


def _viaje(carro: SimCarro, limite_s: float = 500) -> list[dict]:
    """Carga el vaso, lo lleva a la meta, lo "retira" a los 4 s y vuelve."""
    eventos = []
    carro.cargar_vaso()
    llegada = None
    while carro.tiempo < limite_s:
        eventos += carro.avanzar(1.0)
        c = carro.control
        if c.estado == "en_meta":
            llegada = llegada or carro.tiempo
            if carro.tiempo - llegada >= carro.cfg["espera_descarga_meta_s"]:
                carro.retirar_vaso()
        if c.estado == "detenido" or (c.estado == "esperando_carga" and c.fase == "vuelta"):
            break
    return eventos


def _revisar_viaje(carro: SimCarro, eventos: list[dict]) -> None:
    nombres = [e["ev"] for e in eventos]
    assert "error" not in nombres, [e for e in eventos if e["ev"] == "error"]
    assert carro.control.estado == "esperando_carga" and carro.control.fase == "vuelta"
    assert nombres.count("meta") == 1
    # 3 muros a la ida y los mismos 3 a la vuelta, sin tocar ninguno.
    assert nombres.count("evasion") == 6
    assert carro.toques_muro == 0
    # Quedo en el muelle: la cuna bajo el final de la canaleta.
    x, y, r = carro.pose()
    assert abs(x - carro.salida[0]) < 0.005
    assert abs(y - carro.salida[1]) < 0.008
    assert abs(math.degrees(r - carro.salida[2])) < 2
    # El vaso casi no cabecea (arranques y frenadas con rampa).
    assert math.degrees(carro.inclinacion_max_vaso) < 5


def test_ida_y_vuelta_sin_errores():
    carro = SimCarro(cargar_parametros())
    try:
        _revisar_viaje(carro, _viaje(carro))
    finally:
        carro.cerrar()


@pytest.mark.parametrize("semilla", [1, 2, 3])
def test_ida_y_vuelta_con_los_errores_de_la_configuracion(semilla):
    """Motores distintos entre si, ruido del ultrasonico, lecturas cambiadas
    de los infrarrojos (errores_sensores.carro)."""
    carro = SimCarro(cargar_parametros(), errores=True, semilla=semilla)
    try:
        _revisar_viaje(carro, _viaje(carro))
    finally:
        carro.cerrar()


def test_ida_y_vuelta_con_el_doble_de_error():
    parametros = copy.deepcopy(cargar_parametros())
    parametros["errores_sensores"]["carro"] = {"diferencia_motores": 0.10, "ruido_ultrasonico_mm": 10,
                                               "error_linea": 0.03}
    carro = SimCarro(parametros, errores=True, semilla=6)
    try:
        _revisar_viaje(carro, _viaje(carro))
    finally:
        carro.cerrar()


def test_esquiva_hacia_el_lado_con_mas_espacio():
    """Una caja a la izquierda del primer muro: el carro mira a los dos lados
    y esquiva por la derecha, sin tocar nada."""
    parametros = cargar_parametros()
    carro = SimCarro(parametros)
    try:
        muro = __import__("sim.geometria", fromlist=["x"]).geometria_completa(parametros)["pista"]["obstaculos"][0]
        # A la izquierda del muro (19 cm afuera de la linea), donde mira el
        # ultrasonico cuando el carro gira 30 grados a la izquierda: justo por
        # donde pasaria esquivando por ese lado.
        izq = (-math.sin(muro["rumbo"]), math.cos(muro["rumbo"]))
        adelante = (math.cos(muro["rumbo"]), math.sin(muro["rumbo"]))
        carro.agregar_objeto(muro["x"] + 0.19 * izq[0] + 0.03 * adelante[0], muro["y"] + 0.19 * izq[1] + 0.03 * adelante[1])
        eventos = []
        carro.cargar_vaso()
        while carro.tiempo < 60 and not any(e["ev"] == "linea_recuperada" for e in eventos):
            eventos += carro.avanzar(1.0)
        evasion = next(e for e in eventos if e["ev"] == "evasion")
        assert evasion["lado"] == "derecha"
        assert evasion["izq_mm"] is not None and evasion["der_mm"] is None
        assert any(e["ev"] == "linea_recuperada" for e in eventos)
        assert carro.toques_muro == 0
    finally:
        carro.cerrar()


# ---------------------------------------------------------------------
# Fase 7: ordenes al carro (asistente o botones)
# ---------------------------------------------------------------------


def _cumplir(carro: SimCarro, orden: dict, limite_s: float = 60) -> list[dict]:
    ok, detalle = carro.control.ordenar(orden)
    assert ok, detalle
    eventos = []
    inicio = carro.tiempo
    while carro.tiempo - inicio < limite_s:
        eventos += carro.avanzar(0.5)
        if carro.control.estado in ("esperando_orden", "detenido", "esperando_carga", "en_meta"):
            break
    return eventos


def test_ordenes_invalidas_se_rechazan_sin_moverse():
    carro = SimCarro(cargar_parametros())
    try:
        c = carro.control
        assert not c.ordenar({"accion": "avanzar", "distancia_m": 5})[0]
        assert not c.ordenar({"accion": "retroceder", "distancia_m": 1})[0]   # atras no hay sensor
        assert not c.ordenar({"accion": "girar", "grados": 400})[0]
        assert not c.ordenar({"accion": "volar"})[0]
        assert not c.ordenar({"accion": "volver_muelle"})[0]                  # ya esta en el muelle
        assert c.estado == "esperando_carga"
    finally:
        carro.cerrar()


def test_avanzar_y_girar_con_odometria():
    carro = SimCarro(cargar_parametros())
    try:
        x0, y0, r0 = carro.pose()
        _cumplir(carro, {"accion": "avanzar", "distancia_m": 0.4})
        x1, y1, r1 = carro.pose()
        assert abs(math.hypot(x1 - x0, y1 - y0) - 0.4) < 0.03
        _cumplir(carro, {"accion": "girar", "grados": 90})
        assert abs(math.degrees(carro.pose()[2] - r1) - 90) < 10
        # La odometria sabe mas o menos donde esta.
        ox, oy, _ = carro.control.posicion_estimada()
        x, y, _ = carro.pose()
        assert math.hypot(ox - x, oy - y) < 0.04
        assert carro.control.estado == "esperando_orden"
    finally:
        carro.cerrar()


def test_no_choca_si_el_camino_pasa_por_un_muro():
    """Un punto detras del primer muro: el carro mira el camino (+-15
    grados) y no se mueve, o se detiene frente al muro; nunca lo toca."""
    carro = SimCarro(cargar_parametros(), errores=True, semilla=3)
    try:
        for orden in ({"accion": "avanzar", "distancia_m": 0.4}, {"accion": "girar", "grados": 90},
                      {"accion": "avanzar", "distancia_m": 0.3}, {"accion": "retroceder", "distancia_m": 0.1}):
            _cumplir(carro, orden)
        nombres = [e["ev"] for e in _cumplir(carro, {"accion": "ir_a", "x": 1.26, "y": -0.5075})]
        assert {"camino_bloqueado", "bloqueado"} & set(nombres)
        assert carro.toques_muro == 0
    finally:
        carro.cerrar()


def test_desde_fuera_de_la_linea_va_a_la_meta_y_vuelve_al_muelle():
    carro = SimCarro(cargar_parametros(), errores=True, semilla=3)
    try:
        _cumplir(carro, {"accion": "avanzar", "distancia_m": 0.4})
        _cumplir(carro, {"accion": "girar", "grados": 90})
        _cumplir(carro, {"accion": "avanzar", "distancia_m": 0.2})
        eventos = _cumplir(carro, {"accion": "ir_meta"}, limite_s=300)
        assert carro.control.estado == "en_meta", [e["ev"] for e in eventos][-8:]
        eventos = _cumplir(carro, {"accion": "volver_muelle"}, limite_s=300)
        assert carro.control.estado == "esperando_carga", [e["ev"] for e in eventos][-8:]
        assert carro.toques_muro == 0
        # En el muelle la odometria se vuelve a poner en la posicion conocida.
        ox, oy, _ = carro.control.posicion_estimada()
        assert math.hypot(ox - carro.salida[0], oy - carro.salida[1]) < 0.01
        x, y, _ = carro.pose()
        assert abs(x - carro.salida[0]) < 0.01 and abs(y - carro.salida[1]) < 0.01
    finally:
        carro.cerrar()


def test_desde_el_muelle_sale_derecho_antes_de_girar():
    """En el muelle las guias en V dejan 3 mm de holgura: una orden de girar
    (o de ir a un punto) primero lo saca derecho, sin rozar las guias."""
    import pybullet as p

    carro = SimCarro(cargar_parametros(), errores=True, semilla=5)
    try:
        ok, detalle = carro.control.ordenar({"accion": "girar", "grados": 90})
        assert ok and "sale del muelle" in detalle
        roces = 0
        while carro.control.estado != "esperando_orden" and carro.tiempo < 40:
            carro.avanzar(0.05)
            if carro.tiempo > 1.0:   # al principio apoya en los topes (normal)
                # por lado: guia recta, boca en V y tope (los topes no cuentan)
                roces += sum(bool(p.getContactPoints(carro.carro, m, physicsClientId=carro.cli))
                             for i, m in enumerate(carro.muelle) if i % 3 != 2)
        assert carro.control.estado == "esperando_orden"
        assert roces == 0
    finally:
        carro.cerrar()


# ---------------------------------------------------------------------
# Destinos imposibles (usuario, 2026-09-27): el asistente mando el carro "a
# donde esta el filtro de monedas" -> ir_a (-0.5, 0.0) y se trabo contra el
# muelle. El laser y el ultrasonico no ven lo bajo (guias de 2 cm, topes de
# 4,5): el carro revisa destino y camino contra el mapa fijo (zonas_carro).
# ---------------------------------------------------------------------


def _hasta_media_reversa(carro: SimCarro, y_min: float = -0.66) -> None:
    """Un viaje completo hasta que, de vuelta, esta entrando de reversa al
    muelle (a medio camino, en la boca): donde estaba el carro del incidente."""
    c = carro.control
    carro.cargar_vaso()
    llegada = None
    while carro.tiempo < 500:
        carro.avanzar(0.2)
        if c.estado == "en_meta":
            llegada = llegada or carro.tiempo
            if carro.tiempo - llegada >= carro.cfg["espera_descarga_meta_s"]:
                carro.retirar_vaso()
        if c._acciones and c._acciones[0]["tipo"] == "reversa_tope" and carro.pose()[1] > y_min:
            return
    raise AssertionError("no llego a entrar de reversa al muelle")


def test_zonas_salen_de_la_geometria():
    from sim.geometria import zonas_carro
    from control.vehiculo import distancia_a_zona, en_zona_libre

    z = zonas_carro(cargar_parametros())
    claves = {p["clave"] for p in z["prohibidas"]}
    assert {"planta", "canaleta", "muelle", "poste_camara"} <= claves
    planta = next(p for p in z["prohibidas"] if p["clave"] == "planta")
    # El filtro de monedas (E1-E4, en y = 0) queda dentro de la planta.
    assert distancia_a_zona(planta, 0.0, 0.0) < 0 and distancia_a_zona(planta, 0.07, 0.0) < 0
    # El carro estacionado esta DENTRO del rectangulo del muelle pero no pisa
    # ninguna de sus paredes; la pista entera esta en el piso libre.
    s = cargar_parametros()
    carro = SimCarro(s)
    try:
        x, y, _ = carro.salida
        assert distancia_a_zona(z["muelle"], x, y) < 0
        assert all(distancia_a_zona(p, x, y) > 0 for p in z["prohibidas"])
        assert all(en_zona_libre(z, q.x, q.y) for q in carro.linea)
    finally:
        carro.cerrar()


def test_ir_a_la_planta_desde_el_muelle_se_rechaza_sin_moverse():
    """El caso real: ir_a (-0.5, 0.0) desde el muelle."""
    carro = SimCarro(cargar_parametros(), errores=True, semilla=3)
    try:
        c = carro.control
        x0, y0, _ = carro.pose()
        ok, motivo = c.ordenar({"accion": "ir_a", "x": -0.5, "y": 0.0})
        assert not ok
        assert "fuera del piso" in motivo and "la planta" in motivo and "no puede atravesarla" in motivo
        ok, motivo = c.ordenar({"accion": "ir_a", "x": 0.0, "y": 0.0})       # el filtro de monedas
        assert not ok and "dentro de la planta" in motivo and "no puede ir ahí ni atravesarla" in motivo
        ok, motivo = c.ordenar({"accion": "ir_a", "x": 0.36, "y": -0.3})     # bajo la canaleta
        assert not ok and "canaleta" in motivo
        carro.avanzar(3.0)
        x, y, _ = carro.pose()
        assert c.estado == "esperando_carga" and math.hypot(x - x0, y - y0) < 0.005
    finally:
        carro.cerrar()


def test_camino_por_el_muelle_se_rechaza_y_propone_rodeo():
    from control.vehiculo import holguras_carro, ruta_libre, tramo_bloqueado
    from sim.geometria import zonas_carro

    p = cargar_parametros()
    z = zonas_carro(p)
    lateral, _, giro = holguras_carro(p["vehiculo"])
    # De un lado del muelle al otro, derecho, pasa por encima de sus guias.
    assert tramo_bloqueado(z, 0.05, -0.55, 0.70, -0.55, lateral)["clave"] == "muelle"
    ruta = ruta_libre(z, 0.05, -0.55, 0.70, -0.55, lateral, giro)
    assert ruta and len(ruta) > 1 and ruta[-1] == (0.70, -0.55)
    puntos = [(0.05, -0.55)] + ruta
    assert all(tramo_bloqueado(z, a[0], a[1], b[0], b[1], lateral) is None for a, b in zip(puntos, puntos[1:]))


def test_desde_el_muelle_un_punto_valido_se_sigue_cumpliendo_sin_rozar():
    import pybullet as pb

    carro = SimCarro(cargar_parametros(), errores=True, semilla=3)
    try:
        eventos = _cumplir(carro, {"accion": "ir_a", "x": 0.0, "y": -0.9})
        assert "llego_al_punto" in [e["ev"] for e in eventos]
        x, y, _ = carro.pose()
        assert math.hypot(x - 0.0, y + 0.9) < 0.06
        assert not any(pb.getContactPoints(carro.carro, m, physicsClientId=carro.cli) for m in carro.muelle)
    finally:
        carro.cerrar()


def test_la_odometria_se_corrige_en_la_marca_de_giro():
    """Tras una vuelta con 6 evasiones la odometria se corria ~30 cm; las
    franjas (meta y marca de giro) son puntos fijos: se vuelve a poner ahi."""
    carro = SimCarro(cargar_parametros(), errores=True, semilla=3)
    try:
        _hasta_media_reversa(carro)
        ox, oy, _ = carro.control.posicion_estimada()
        x, y, _ = carro.pose()
        assert math.hypot(ox - x, oy - y) < 0.05
    finally:
        carro.cerrar()


def test_a_medio_muelle_la_orden_del_incidente_se_rechaza():
    carro = SimCarro(cargar_parametros(), errores=True, semilla=1)
    try:
        _hasta_media_reversa(carro)
        ok, motivo = carro.control.ordenar({"accion": "ir_a", "x": -0.5, "y": 0.0})
        assert not ok and "planta" in motivo
    finally:
        carro.cerrar()


def test_tras_detenido_atascado_volver_muelle_lo_saca():
    """El incidente tal cual (sin el mapa, como antes): a medio entrar de
    reversa, ir_a (-0.5, 0.0) lo mete contra la boca del muelle y da
    `atascado` (-41 mm, igual que en la base real). Se aparta deshaciendo el
    tramo y `volver_muelle` lo endereza con la linea y lo vuelve a entrar."""
    carro = SimCarro(cargar_parametros(), errores=True, semilla=1)
    try:
        c = carro.control
        # Un poco antes en la V que el incidente (-0,68 y no -0,66): desde que
        # la reversa deja de corregir adentro de la V (2026-09-27) el carro
        # llega ahi en otra pose, y mas adentro las dos ruedas patinan parejo
        # contra el muelle (sin `atascado`; con el mapa esta orden ni se acepta).
        _hasta_media_reversa(carro, y_min=-0.68)
        zonas, c.zonas = c.zonas, None           # como antes del arreglo
        eventos = _cumplir(carro, {"accion": "ir_a", "x": -0.5, "y": 0.0}, limite_s=40)
        nombres = [e["ev"] for e in eventos]
        assert "atascado" in nombres and "detenido_atascado" in nombres, nombres
        c.zonas = zonas
        eventos = _cumplir(carro, {"accion": "volver_muelle"}, limite_s=120)
        assert c.estado == "esperando_carga", [e["ev"] for e in eventos]
        x, y, r = carro.pose()
        assert abs(x - carro.salida[0]) < 0.01 and abs(y - carro.salida[1]) < 0.01
    finally:
        carro.cerrar()


# ---------------------------------------------------------------------
# Reversa al muelle con tiempo limite (2026-09-27): se vio al carro 35 s
# trabado en la boca del muelle avanzando de a milimetros. Falso minimo: los
# encoders cuentan lo que se pide a los motores, salvo en la boca trabada
# (un pulso suelto cada 2,5 s) y contra el tope (nada).
# ---------------------------------------------------------------------


def _reversa_trabada(trabas: int):
    """Corre SOLO la entrada de reversa. `trabas`: cuantos intentos de
    reversa quedan trabados en la boca (a 12 cm de haber empezado)."""
    from control.vehiculo import ControlCarro, LecturaCarro

    cfg = cargar_parametros()["vehiculo"]
    c = ControlCarro(cfg, largo_linea_m=5.0)
    c.estado = "maniobra"
    c._acciones = [{"tipo": "reversa_tope", "hecho": 0.0, "quieto": 0.0},
                   {"tipo": "estado", "estado": "esperando_carga", "evento": "en_muelle"}]
    dt, t = 1 / cfg["control_hz"], 0.0
    pulsos, acumulado, atras, intentos, ultimo_pulso = 0, 0.0, 0.0, 0, 0.0
    previo = None
    while t < 60 and c.estado == "maniobra":
        a = c._acciones[0] if c._acciones else {}
        if a.get("tipo") == "reversa_tope" and a is not previo:
            intentos += 1
            previo = a
        trabado = a.get("tipo") == "reversa_tope" and intentos <= trabas and atras >= 0.12
        v = (c._cmd[0] + c._cmd[1]) / 2
        if trabado:
            if t - ultimo_pulso >= 2.5:      # avanza de a milimetros
                pulsos, ultimo_pulso = pulsos + 1, t
                atras += c.m_por_pulso
        elif not (v < 0 and atras >= 0.44):  # contra el tope no cuenta nada
            acumulado += abs(v) * dt
            while acumulado >= c.m_por_pulso:
                acumulado -= c.m_por_pulso
                pulsos += 1
                atras += -c.m_por_pulso if v > 0 else c.m_por_pulso
        c.paso(LecturaCarro((0, 0, 1, 0, 0), None, pulsos, pulsos), dt)
        t += dt
    return c, t, [e["ev"] for e in c.eventos], intentos


def test_reversa_trabada_reintenta_una_vez_y_entra():
    c, t, eventos, intentos = _reversa_trabada(1)
    assert intentos == 2 and eventos.count("reversa_reintento") == 1
    assert c.estado == "esperando_carga" and "en_muelle" in eventos
    assert "error" not in eventos


def test_reversa_trabada_dos_veces_se_detiene_con_error():
    c, t, eventos, intentos = _reversa_trabada(2)
    assert intentos == 2 and eventos.count("reversa_reintento") == 1
    assert c.estado == "detenido"
    assert [e["motivo"] for e in c.eventos if e["ev"] == "error"] == ["no_llego_al_tope"]
    # Termina mucho antes que los 35 s del incidente por intento (sin
    # quedarse avanzando de a milimetros): dos esperas + la salida.
    assert t < 2 * c.reversa_max_s
    assert not c.pwm_bajo


def test_reversa_normal_no_se_corta():
    c, t, eventos, intentos = _reversa_trabada(0)
    assert intentos == 1 and "reversa_reintento" not in eventos
    assert c.estado == "esperando_carga" and t < c.reversa_max_s


# ---------------------------------------------------------------------
# Entrada al muelle sin reintentos (2026-09-27). La reversa corregia el
# rumbo con los pulsos "hasta 25 cm", suponiendo que empezaba en la marca de
# giro; empieza tras enderezarse, a ~32-35 cm del tope, con la cola a 2-5 cm
# de la boca: la correccion seguia ~20 cm DENTRO de la V peleando con la
# guia y, con 2-3 grados de entrada, lo trababa (semilla 2: parado en la V a
# 3,4 grados, reintento). Ahora corrige solo hasta que la cola llega a la boca.
# ---------------------------------------------------------------------


def test_boca_del_muelle_coincide_con_la_simulacion():
    from sim.vehiculo_sim import LARGO_BOCA_MUELLE

    v = cargar_parametros()["vehiculo"]
    largo, r = v["largo_mm"] / 1000, v["diametro_rueda_mm"] / 2000
    boca = -0.18 * largo + r + 0.015 + LARGO_BOCA_MUELLE        # sim/vehiculo_sim.py, _crear_muelle
    assert abs(v["boca_muelle_mm"] / 1000 - (boca + largo / 2)) < 0.002


def test_la_reversa_no_corrige_el_rumbo_dentro_de_la_v():
    """Reversa desde 33 cm del tope (donde queda tras enderezarse) con la
    rueda izquierda contando de mas: pasada la boca, las dos ruedas reciben lo
    mismo (manda la guia). Con el codigo viejo seguia corrigiendo."""
    from control.vehiculo import ControlCarro, LecturaCarro

    cfg = cargar_parametros()["vehiculo"]
    mx, my, mr = 1.0, 2.0, 0.5
    c = ControlCarro(cfg, largo_linea_m=5.0, pose_muelle=(mx, my, mr))
    afuera = 0.33
    c.fijar_pose(mx + (afuera + c.x_eje) * math.cos(mr), my + (afuera + c.x_eje) * math.sin(mr), mr)
    c.estado = "maniobra"
    c._acciones = [{"tipo": "reversa_tope", "hecho": 0.0, "quieto": 0.0}]
    dt = 1 / cfg["control_hz"]
    izq = der = 0
    acum = [0.0, 0.0]
    desiguales_en_la_v = 0
    for _ in range(int(8 / dt)):
        cmd = c.paso(LecturaCarro((0, 0, 1, 0, 0), None, izq, der), dt)
        # La izquierda cuenta un 10 % mas (motor distinto).
        acum[0] += abs(cmd[0]) * dt * 1.10
        acum[1] += abs(cmd[1]) * dt
        while acum[0] >= c.m_por_pulso:
            acum[0] -= c.m_por_pulso
            izq += 1
        while acum[1] >= c.m_por_pulso:
            acum[1] -= c.m_por_pulso
            der += 1
        # Afuera: centro del carro respecto al estacionado, a lo largo del muelle.
        x, y, _ = c.posicion_estimada()
        dentro = (x - mx) * math.cos(mr) + (y - my) * math.sin(mr)
        if dentro < c.boca_muelle and abs(c._objetivo[0] - c._objetivo[1]) > 1e-9:
            desiguales_en_la_v += 1
    assert desiguales_en_la_v == 0
    assert c._acciones[0]["hasta_boca"] < afuera - c.boca_muelle


@pytest.mark.parametrize("semilla, doble", [(1, False), (2, False), (3, False), (6, False), (6, True)])
def test_entra_al_muelle_sin_reintento(semilla, doble):
    """Viaje completo con la fisica real: entra al muelle al primer intento
    (el reintento queda como red de seguridad). Con el codigo viejo la
    semilla 2 se trababa en la V y reintentaba."""
    parametros = copy.deepcopy(cargar_parametros())
    if doble:
        parametros["errores_sensores"]["carro"] = {"diferencia_motores": 0.10, "ruido_ultrasonico_mm": 10,
                                                   "error_linea": 0.03}
    carro = SimCarro(parametros, errores=True, semilla=semilla)
    try:
        eventos = _viaje(carro)
        _revisar_viaje(carro, eventos)
        assert "reversa_reintento" not in [e["ev"] for e in eventos]
    finally:
        carro.cerrar()
