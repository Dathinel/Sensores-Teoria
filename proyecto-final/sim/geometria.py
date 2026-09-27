"""Geometria completa del sistema y catalogo de sensores, en un solo JSON.

Lo consume el visor 3D (`app/visor3d/`, via `GET /api/geometria` del
supervisor) y la pestana "Sensores" del dashboard. Todo sale de las MISMAS
fuentes que usa la simulacion:

- posiciones de estaciones: `sim.mundo.posicion_estacion_*`;
- rayos de los sensores: los propios `SensorRayo` que arma
  `control.hal.backend_sim.EstacionBackendSim` (origen y destino exactos del
  `rayTest`), construidos sobre una escena "solo geometria" que no abre
  PyBullet;
- pista, canaleta y vehiculo: `config/parametros.yaml` + `sim/pista.py`.

Asi el 3D no puede mostrar un sensor en un lugar distinto al que la
simulacion realmente consulta.

A cada sensor del catalogo numerado (sim/catalogos.py) se le pega
aqui su geometria, para que el visor lo dibuje donde de verdad esta.
"""

from __future__ import annotations

import math

from control.hal.backend_sim import EstacionBackendSim
from sim import conexiones, mundo
from sim.catalogos import CATEGORIAS, COMPONENTES
from sim.catalogos import CATALOGO_SENSORES
from sim.pista import generar_linea_central, punto_en


# Ancho de la banda de cada cinta (las bancadas son 5 mm mas anchas). La de
# vasos deja pasar la pestana del reborde.
ANCHO_CINTA_MONEDAS_M = 0.055
ANCHO_CINTA_VASOS_M = 0.075
# La cuna del carro arranca en su extremo trasero (medio largo detras del
# centro): ahi termina la canaleta cuando el carro esta en la parada.
CUNA_ATRAS_FRAC = 0.5


class _EscenaSoloGeometria:
    """Lo minimo de `EscenaEstacion` que necesitan las fabricas de sensores
    para construir sus rayos: las posiciones de estacion y los ids de las
    cintas (que solo se usan al LEER el sensor, nunca aqui)."""

    id_cinta_monedas = None
    id_cinta_vasos = None
    elementos_monedas: list = []
    elementos_vasos: list = []

    posicion_estacion_monedas = staticmethod(mundo.posicion_estacion_monedas)
    posicion_estacion_vasos = staticmethod(mundo.posicion_estacion_vasos)


def _vec(t) -> list[float]:
    return [round(float(v), 5) for v in t]


def _rayos_de_sensores(vasos: dict | None = None) -> dict[str, dict]:
    """Geometria REAL de cada sensor, sacada del backend sim."""
    b = EstacionBackendSim(_EscenaSoloGeometria())
    geo: dict[str, dict] = {}
    geo["presencia"] = {"tipo": "rayo", "origen": _vec(b.sensor_presencia.origen),
                        "destino": _vec(b.sensor_presencia.destino)}
    # Cortina: un VL53L0X con su cono real (el mismo que consulta la
    # simulacion); `destino` es el centro del final de la ventana de
    # distancia y `radio_final` el radio del cono ahi.
    c = b.sensor_cortina
    from sim.sensores_sim import FONDO_SOPORTE_CORTINA_M
    geo["cortina"] = {"tipo": "cono", "origen": _vec(c.origen), "destino": _vec(c.destino),
                      "radio_final": round(c.radio_final_m, 5), "fondo_soporte": FONDO_SOPORTE_CORTINA_M}

    # Sensores de material, DEBAJO de la cinta y mirando hacia arriba: leen
    # la pieza a traves de la banda (2 mm). `posicion` es el centro de la
    # CARA activa, 0,5 mm bajo la banda (roza el inserto impreso de la
    # bancada, no la banda). Cada uno centrado bajo su casilla: el capacitivo
    # bajo E1 y el inductivo bajo E2 (una moneda de 17 mm no tapa dos caras
    # de 18 mm a la vez; descentrado, el inductivo pierde la mitad del
    # alcance y con monedas no ferrosas no llega).
    for sensor, estacion in (("capacitivo", mundo.ESTACION_PRESENCIA_MONEDAS),
                             ("inductivo", mundo.ESTACION_MATERIAL_MONEDAS)):
        x, y, z = mundo.posicion_estacion_monedas(estacion)
        geo[sensor] = {"tipo": "proximidad", "posicion": _vec((x, y, z - 0.0025)), "mira": [0, 0, 1],
                       "bajo_cinta": True}
    # Sensor del interior del vaso: sobre la verificacion, mirando hacia
    # abajo, 1,5 cm por encima del borde (revision final 2026-09-26: a 3 cm su
    # cono de 25 grados llegaba al fondo con 2,5 mm de margen a la pared;
    # asi quedan ~6 mm). Y el Hall del carrusel.
    x, y, z = mundo.posicion_estacion_vasos(mundo.ESTACION_VERIFICACION_VASOS)
    vasos = vasos or {"altura_mm": 90, "sensor_interior_sobre_boca_mm": 15}
    alto = vasos["altura_mm"] / 1000
    sobre = vasos.get("sensor_interior_sobre_boca_mm", 15) / 1000
    geo["sensor_interior"] = {"tipo": "proximidad", "posicion": _vec((x, y, z + alto + sobre)), "mira": [0, 0, -1]}
    cx, cy = mundo.centro_carrusel()
    # Hall: encima del iman (6 x 3 mm, en el disco del carrusel a R+15 mm,
    # a 0 grados: entre los tubos de 330 y 30), mirando hacia abajo con 4 mm
    # de aire. `posicion` es la cara del sensor: disco (3 mm) + iman (3 mm) +
    # 4 mm.
    geo["hall_carrusel"] = {"tipo": "proximidad",
                            "posicion": _vec((cx + mundo.CARRUSEL_RADIO_M + 0.015, cy,
                                              mundo.TUBO_BASE_Z + mundo.TUBO_ALTO_M + 0.010)),
                            "mira": [0, 0, -1]}
    x, y, z = mundo.posicion_estacion_monedas(mundo.ESTACION_VISION_MONEDAS)
    # A 15 cm de la cinta (revision final: a 9 cm casi ninguna webcam enfoca;
    # con autoenfoque a 15 cm quedan ~0,1 mm por pixel).
    geo["camara"] = {"tipo": "camara", "posicion": _vec((x, y, z + 0.15)), "mira": [0, 0, -1],
                     "objetivo": _vec((x, y, z))}


    # Camara de vasos: al costado de la cinta, del lado del operador (-y), a
    # la altura de la boca del vaso, mirando horizontal hacia el panel de luz
    # que esta detras (+y). Ve verificacion, llenado y tapa a la vez; el
    # almacen y el tubo de tapas quedan arriba, fuera de su vista. Sus
    # "franjas" son las lineas de medida de cada estacion (los mismos rayos
    # que consulta la simulacion: media altura y borde).
    x0 = mundo.posicion_estacion_vasos(mundo.ESTACION_VERIFICACION_VASOS)[0]
    x3, y, z = mundo.posicion_estacion_vasos(mundo.ESTACION_PRENSA_VASOS)
    xc = (x0 + x3) / 2
    franjas = []
    for zona in (b.zona_verificacion, b.zona_llenado, b.zona_tapa, b.zona_prensa):
        for nombre, rayo in (("media", zona.media_altura), ("borde", zona.borde)):
            franjas.append({"nivel": nombre, "origen": _vec(rayo.origen), "destino": _vec(rayo.destino)})
    alto_vaso = franjas[1]["origen"][2] - z
    # A 30 cm de la cinta ve las 4 casillas (~31 cm) con ~56 grados de campo
    # horizontal (una webcam comun tiene ~60-70), sin que la canaleta ni sus
    # postes le tapen la prensa.
    geo["camara_vasos"] = {"tipo": "camara", "posicion": _vec((xc, y - 0.30, z + alto_vaso * 0.95)),
                           "mira": [0, 1, 0], "objetivo": _vec((xc, y, z + alto_vaso * 0.55)),
                           "franjas": franjas}
    return geo


def _franja(linea, s: float, ancho_mm: float) -> dict:
    pto = punto_en(linea, s)
    return {"x": round(pto.x, 4), "y": round(pto.y, 4), "rumbo": pto.rumbo, "ancho": ancho_mm / 1000}


def geometria_completa(parametros: dict) -> dict:
    vaso = parametros["vasos"]
    estaciones_m = [
        {"indice": i, "posicion": _vec(mundo.posicion_estacion_monedas(i))}
        for i in range(mundo.NUM_ESTACIONES_MONEDAS)
    ]
    estaciones_v = [
        {"indice": i, "posicion": _vec(mundo.posicion_estacion_vasos(i))}
        for i in range(mundo.NUM_ESTACIONES_VASOS)
    ]

    # Canaleta de entrega: los rieles arrancan en el borde de la cinta de
    # vasos (del lado del operador), a la altura de la pestana del reborde:
    # el empujador pasa el vaso de lado, la pestana se sube a los rieles y el
    # cuerpo queda colgando entre ellos. Baja a la inclinacion configurada
    # hasta la cuna del carro.
    xd, yd, zd = mundo.posicion_estacion_vasos(mundo.ESTACION_DESCARGA_VASOS)
    inclinacion = math.radians(parametros["canaleta_entrega"]["inclinacion_grados"])
    largo = parametros["canaleta"]["largo_mm"] / 1000
    diametro_riel = parametros["canaleta"]["diametro_riel_mm"] / 1000
    # Tope del riel unos mm por debajo de la boca del vaso (entrada en
    # embudo): la pestana cae sobre los rieles en vez de chocar con su punta.
    caida = parametros["canaleta"]["caida_entrada_mm"] / 1000
    z_ini = zd + vaso["altura_mm"] / 1000 - diametro_riel / 2 - caida
    y_ini = yd - ANCHO_CINTA_VASOS_M / 2
    canaleta = {
        "inicio": _vec((xd, y_ini, z_ini)),
        "fin": _vec((xd, y_ini - largo, z_ini - largo * math.tan(inclinacion))),
        "separacion_rieles": parametros["canaleta"]["separacion_rieles_mm"] / 1000,
        "separacion_entrada": parametros["canaleta"]["separacion_entrada_mm"] / 1000,
        "largo_embudo": parametros["canaleta"]["largo_embudo_mm"] / 1000,
        "caida_entrada": parametros["canaleta"]["caida_entrada_mm"] / 1000,
        "diametro_riel": diametro_riel,
        "capacidad": parametros["canaleta"]["capacidad_vasos"],
    }

    # La pista sale justo debajo del final de la canaleta, con el carro
    # apuntando hacia -y (alejandose de la planta). El carro se para con el
    # extremo trasero de su cuna pegado al final de la canaleta: sus rieles
    # continuan los de la canaleta y el vaso pasa deslizando (seccion 4).
    veh = parametros["vehiculo"]
    pista_cfg = parametros["pista"]
    largo_carro = veh["largo_mm"] / 1000
    salida = (canaleta["fin"][0], canaleta["fin"][1] - largo_carro * CUNA_ATRAS_FRAC, -math.pi / 2)
    linea = generar_linea_central(pista_cfg["tramos"], salida)
    obstaculos = []
    for s_mm in pista_cfg["obstaculos_mm"]:
        pto = punto_en(linea, s_mm / 1000)
        obstaculos.append({"s": s_mm / 1000, "x": pto.x, "y": pto.y, "rumbo": pto.rumbo,
                           "largo": pista_cfg["obstaculo_largo_mm"] / 1000,
                           "alto": pista_cfg["obstaculo_alto_mm"] / 1000})
    meta = linea[-1]

    rayos = _rayos_de_sensores(parametros["vasos"])
    sensores = [dict(s, geometria=rayos.get(s["id"])) for s in CATALOGO_SENSORES]

    return {
        "unidades": "metros",
        "altura_superficie": mundo.ALTURA_SUPERFICIE,
        "cinta_monedas": {
            "estaciones": estaciones_m,
            "separacion": mundo.SEPARACION_CASILLA_M,
        },
        "cinta_vasos": {"estaciones": estaciones_v, "separacion": mundo.SEPARACION_CASILLA_VASOS_M},
        # Almacen tipo revolver: 6 tubos en un carrusel que gira sobre una
        # placa fija con UN agujero (sobre el vaso de llenado, con obturador).
        # Angulos en grados, medidos como en la simulacion (desde +x hacia +y).
        "almacen": {
            "centro": _vec(mundo.centro_carrusel()),
            "radio_carrusel": mundo.CARRUSEL_RADIO_M,
            "angulo_carga": mundo.ANGULO_CARGA_CARRUSEL,
            "angulo_agujero": mundo.ANGULO_AGUJERO_CARRUSEL,
            "punto_carga": _vec(mundo.punto_carga_carrusel()),
            "tubos": [
                {"denominacion": d, "base": _vec(mundo.posicion_tubo(d)), "radio": mundo.TUBO_RADIO_M,
                 "alto": mundo.TUBO_ALTO_M}
                for d in mundo.POSICIONES_CARRUSEL  # la ultima es "otras"
            ],
            "grosor_moneda": mundo.GROSOR_PILA_M,
            "tubo_z_arriba": mundo.TUBO_BASE_Z + mundo.TUBO_ALTO_M,
            "tolva": {"z_arriba": mundo.TUBO_BASE_Z - 0.008, "z_abajo": mundo.TUBO_BASE_Z - 0.04, "radio": 0.019,
                      "salida": _vec(mundo.salida_tolva())},
            # Compuerta de desvio de la descarga y la UNICA bandeja de rechazo.
            "rechazo_final": _vec(mundo.posicion_rechazo_final()),
        },
        "vaso": {"diametro": vaso["diametro_mm"] / 1000, "altura": vaso["altura_mm"] / 1000,
                 "reborde": vaso["reborde_mm"] / 1000},
        "bandeja_rechazo_vasos": _vec(mundo.posicion_bandeja_rechazo_vasos()),
        "ancho_cinta_monedas": ANCHO_CINTA_MONEDAS_M,
        "ancho_cinta_vasos": ANCHO_CINTA_VASOS_M,
        # Duraciones reales (config: tiempos_ms): el visor anima cada avance,
        # barrido y caida con lo mismo que tarda en el montaje.
        "tiempos_ms": parametros["tiempos_ms"],
        "canaleta": canaleta,
        "pista": {
            "linea": [[round(q.x, 4), round(q.y, 4)] for q in linea[::2]],
            "largo": round(linea[-1].s, 3),
            "ancho": pista_cfg["ancho_mm"] / 1000,
            "ancho_linea": pista_cfg["ancho_linea_mm"] / 1000,
            "obstaculos": obstaculos,
            "salida": {"x": salida[0], "y": salida[1], "rumbo": salida[2]},
            "meta": {"x": meta.x, "y": meta.y, "rumbo": meta.rumbo},
            # Franjas negras transversales que ven los 5 infrarrojos del carro
            # (sim/vehiculo_sim.py): la meta (al final de la linea) y la marca
            # de giro antes del muelle.
            "franja_meta": _franja(linea, linea[-1].s - veh["franja_meta_ancho_mm"] / 2000, veh["franja_meta_ancho_mm"]),
            "franja_giro": _franja(linea, veh["marca_giro_mm"] / 1000, veh["franja_giro_ancho_mm"]),
        },
        "vehiculo": {
            "cuna_atras_frac": CUNA_ATRAS_FRAC,
            "largo": veh["largo_mm"] / 1000, "ancho": veh["ancho_mm"] / 1000, "alto": veh["alto_mm"] / 1000,
            "diametro_rueda": veh["diametro_rueda_mm"] / 1000,
            "sensores_linea": veh["sensores_linea"],
            "separacion_sensores_linea": veh["separacion_sensores_linea_mm"] / 1000,
            "distancia_obstaculo": veh["distancia_obstaculo_mm"] / 1000,
            "distancia_frenado": veh["distancia_frenado_mm"] / 1000,
            "rodillo_guia_y": veh["rodillo_guia_y_mm"] / 1000,
            "rodillo_guia_radio": veh["rodillo_guia_radio_mm"] / 1000,
        },
        "sensores": sensores,
        "componentes": COMPONENTES,
        "conexiones": conexiones.datos_visor(),
        "categorias_componentes": list(CATEGORIAS),
    }
