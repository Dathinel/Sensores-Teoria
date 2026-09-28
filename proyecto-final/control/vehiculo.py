"""Control del carro (paso a paso, punto 14): seguir la linea, esquivar los
tres muros, llegar a la meta y volver SOLO al muelle.

Es logica pura (sin PyBullet ni pyserial, CLAUDE.md seccion 17): cada
`paso()` recibe lo que leen los sensores del carro -- 5 infrarrojos de linea,
el ultrasonico y los pulsos de los dos encoders -- y devuelve la velocidad
que se le pide a cada rueda. La misma clase corre contra la simulacion
(sim/vehiculo_sim.py) y, en la fase 8, en el PC hablando con el ESP32 del
carro (o traducida al firmware).

Decisiones del usuario (2026-09-26) y por que:

- Se puede esquivar como sea, con tal de llegar a la meta y volver solo.
- Esquiva hacia el lado con MAS espacio: antes de maniobrar gira sobre su
  eje +-30 grados y mide con el mismo ultrasonico (no hace falta un servo
  que lo mueva). Si los dos lados estan libres, por la izquierda: siempre
  igual, repetible.
- La maniobra es "girar hacia un lado y devolver el giro pasado el
  obstaculo": sale a 45 grados, pasa derecho, vuelve a 60 grados hacia la
  linea. Lo que la hace confiable con errores reales (ruedas que patinan un
  poco, un motor mas rapido que el otro, encoders de 10 mm por pulso) es
  que NO vuelve a la linea contando pulsos: avanza hasta que el infrarrojo
  del centro la VE, sigue hasta que el eje de las ruedas queda sobre ella y
  recien ahi gira. Los pulsos solo tienen que ser "mas o menos" buenos.
- Varias lecturas y maniobras lentas: un obstaculo cuenta solo con N
  lecturas seguidas; todo cambio de velocidad pasa por una rampa
  (`aceleracion_max_m_s2`) para que el vaso colgado no se balancee.

Ordenes de afuera (fase 7, usuario 2026-09-27): el asistente (o un boton del
dashboard) le puede pedir al carro que se detenga, avance, retroceda, gire,
vaya a un punto (x, y), vaya a la meta, vuelva al muelle o retome la linea
(`ordenar`). Tres ideas para que sirva con errores reales:

- Donde esta el carro lo sabe por ODOMETRIA (integrando los pulsos de los
  dos encoders), no por una camara: se acumula error (una rueda que patina,
  10 mm por pulso), por eso cada vez que entra al muelle -- un punto fijo y
  medido -- la posicion se vuelve a poner en el valor conocido.
- "No chocar": en todo movimiento hacia adelante pedido por una orden, el
  laser y el ultrasonico vigilan igual que siguiendo la linea; con un
  obstaculo confirmado (varias mediciones seguidas) el carro se DETIENE y
  avisa `bloqueado` (no esquiva por su cuenta en modo de ordenes). Hacia
  atras no tiene sensor: la reversa por orden es corta y lenta.
- Para ir a la meta, volver al muelle o retomar la linea no se confia en la
  odometria para seguir la pista: solo se usa para llegar CERCA de la linea
  y mirar hacia el lado correcto; despues la busca con los infrarrojos y la
  sigue con el control de siempre (con su evasion de muros).

Convenciones: metros, segundos, radianes. Infrarrojos ordenados de
izquierda a derecha. Angulos positivos = a la izquierda (antihorario).
"""

from __future__ import annotations

import math


# Lecturas filtradas seguidas del infrarrojo del centro para dar por
# encontrada la linea al volver de una evasion o al buscarla girando.
CONFIRMAR_LINEA = 4

# Ordenes que acepta el carro (fase 7) y sus limites. La reversa es corta
# porque atras no hay sensor; un punto (x, y) mas lejos que eso se pide por
# partes (la odometria acumula error con la distancia).
ORDENES = ("detener", "avanzar", "retroceder", "girar", "ir_a", "ir_meta", "volver_muelle", "seguir_linea")
AVANCE_MAX_M = 1.5
REVERSA_MAX_M = 0.30
IR_A_MAX_M = 2.5
# Llego a un punto (x, y) si queda a menos de esto; si no, corrige otra vez
# (como mucho INTENTOS_IR_A veces).
TOLERANCIA_IR_A_M = 0.03
INTENTOS_IR_A = 3
# Si el carro esta mas lejos que esto de la linea, primero va al punto mas
# cercano de ella (con la odometria) y despues la busca con los infrarrojos.
LEJOS_DE_LA_LINEA_M = 0.05
# Antes de moverse por una orden mira el camino: al frente y a +-este angulo
# (el laser ve un cono de ~25 grados; a los lados cubre las esquinas del
# carro, que el cono solo no ve de cerca). Y si en una recta una rueda cuenta
# mucho mas que la otra, algo lo esta sujetando: se detiene (atascado).
ANGULO_REVISAR_CAMINO = math.radians(15)
# En el muelle las guias en V llegan ~21 cm delante del centro del carro: para
# girar o ir a un punto primero sale derecho esto (la cola pasa las guias).
SALIR_DEL_MUELLE_M = 0.35
# Dentro del muelle (o de su boca) solo se sale DERECHO y de frente: si el
# carro mira hacia afuera con un error de hasta esto, sale avanzando; si mira
# hacia adentro, no hay como salir sin rozar las guias.
ANGULO_SALIR_MUELLE = math.radians(30)
DIFERENCIA_ATASCADO_M = 0.04
# Estados del modo de ordenes (se agregan a los del recorrido automatico).
MANUAL = "manual"                    # cumpliendo una orden
ESPERANDO_ORDEN = "esperando_orden"  # la cumplio (o lo bloqueo algo) y espera otra


def _angulo(a: float) -> float:
    """Angulo equivalente entre -pi y pi."""
    return (a + math.pi) % (2 * math.pi) - math.pi


# ----------------------------------------------------------------------
# Donde PUEDE andar el carro (usuario, 2026-09-27): el asistente lo mando a
# (-0,5; 0), "a donde esta el filtro de monedas", y el carro se trabo contra
# el muelle. Su revision del camino (laser a 7,4 cm del piso y ultrasonico a
# 5,7 cm) no ve lo BAJO -- las guias del muelle miden 2 cm y los topes 4,5 --
# y la planta entera (mesas, patas, canaleta, postes de camaras) no esta en
# la pista. Por eso, antes de moverse por una orden, el carro compara el
# destino y el camino recto con un mapa FIJO y medido (como el trazado de la
# pista): un rectangulo de piso libre y las huellas prohibidas (planta,
# canaleta, muelle, poste de la camara). Las arma sim/geometria.py
# (`zonas_carro`) desde la misma geometria del visor y la simulacion.
#
# Formato (sin dataclasses: corre tambien en el ESP32 del carro):
#   {"libre": [xmin, ymin, xmax, ymax],
#    "muelle": {...},        rectangulo que encierra el muelle (estar adentro)
#    "prohibidas": [{"clave", "nombre", "atravesar", "cx", "cy", "rumbo",
#                    "ml", "ma"}, ...]}
# Cada huella es un rectangulo girado `rumbo`, de medio largo `ml` (a lo
# largo de su rumbo) y medio ancho `ma`. El muelle va como paredes sueltas
# (guias, boca y topes): el carro estacionado esta ADENTRO y sale por el canal.
# ----------------------------------------------------------------------

# Muestreo del camino recto al revisarlo contra las huellas (1 cm).
PASO_REVISION_M = 0.01
# Partiendo YA cerca de una huella (dentro del muelle, entre sus guias), el
# camino vale mientras no se le acerque mas que esto: saliendo derecho por el
# canal la distancia a la boca en V cambia unos milimetros.
TOLERANCIA_ACERCARSE_M = 0.01


def holguras_carro(v: dict) -> tuple[float, float, float]:
    """(lateral, destino, giro) en metros: lo que tiene que quedar entre el
    CENTRO del carro y una huella prohibida.

    - lateral: andando derecho, a cada lado lo barre su medio ancho (los
      rodillos guia de atras son lo mas ancho) + `margen_evasion_mm`;
    - destino: parado ahi (y con las correcciones cortas al llegar), el
      punto del carro mas lejano del centro (esquinas, rodillos, llantas) +
      el margen;
    - giro: en un punto de paso de un rodeo gira sobre el eje de las ruedas:
      el circulo que barre, visto desde el centro, + el margen.
    Mismas medidas que ControlCarro y sim/vehiculo_sim.py (llantas 24 mm
    afuera del chasis, rodillos 8 mm delante de la cola)."""
    largo = v["largo_mm"] / 1000
    ancho = v["ancho_mm"] / 1000
    x_eje = -0.18 * largo
    r_rueda = v["diametro_rueda_mm"] / 2000
    y_rueda = ancho / 2 + 0.024
    y_rodillo = (v.get("rodillo_guia_y_mm", 0) + v.get("rodillo_guia_radio_mm", 0)) / 1000
    puntos = ((largo / 2, ancho / 2), (-largo / 2, ancho / 2), (x_eje + r_rueda, y_rueda),
              (x_eje - r_rueda, y_rueda), (-largo / 2 + 0.008, y_rodillo))
    medio_ancho = max(py for _, py in puntos)
    r_centro = max(math.hypot(px, py) for px, py in puntos)
    r_eje = max(math.hypot(px - x_eje, py) for px, py in puntos)
    margen = v["margen_evasion_mm"] / 1000
    return medio_ancho + margen, r_centro + margen, r_eje + abs(x_eje) + margen


def distancia_a_zona(z: dict, x: float, y: float) -> float:
    """Distancia del punto a la huella (negativa = adentro)."""
    c, s = math.cos(z["rumbo"]), math.sin(z["rumbo"])
    dx, dy = x - z["cx"], y - z["cy"]
    ex = abs(dx * c + dy * s) - z["ml"]
    ey = abs(-dx * s + dy * c) - z["ma"]
    if ex <= 0 and ey <= 0:
        return max(ex, ey)
    return math.hypot(max(ex, 0.0), max(ey, 0.0))


def en_zona_libre(zonas: dict, x: float, y: float) -> bool:
    x0, y0, x1, y1 = zonas["libre"]
    return x0 <= x <= x1 and y0 <= y <= y1


def tramo_bloqueado(zonas: dict, x0: float, y0: float, x1: float, y1: float, holgura: float) -> dict | None:
    """La primera huella que el tramo recto (x0, y0) -> (x1, y1) pasa a menos
    de `holgura`, o None. Si el carro YA esta cerca de una huella (saliendo del
    muelle, o parado junto a una estructura), cuenta solo si el tramo se le
    ACERCA: alejarse de ella siempre se puede."""
    largo = math.hypot(x1 - x0, y1 - y0)
    n = max(1, int(largo / PASO_REVISION_M))
    for z in zonas["prohibidas"]:
        d0 = distancia_a_zona(z, x0, y0)
        tolerancia = TOLERANCIA_ACERCARSE_M if d0 < holgura else 0.0
        for i in range(1, n + 1):
            t = i / n
            d = distancia_a_zona(z, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
            if d < holgura and d < d0 - tolerancia:
                return z
    return None


def _de(nombre: str) -> str:
    """"de" + nombre, con la contraccion del espanol ("del muelle")."""
    return "del " + nombre[3:] if nombre.startswith("el ") else "de " + nombre


def motivo_destino(zonas: dict, x: float, y: float, holgura: float) -> str:
    """"" si el carro puede quedar en (x, y); si no, el motivo en palabras
    (la huella mas cercana: la que lo contiene, o la que no le deja lugar)."""
    cerca, d_cerca = None, math.inf
    for z in zonas["prohibidas"]:
        d = distancia_a_zona(z, x, y)
        if d < d_cerca:
            cerca, d_cerca = z, d
    if cerca is not None and d_cerca <= 0:
        return (f"ese punto ({x:.2f}, {y:.2f}) está dentro {_de(cerca['nombre'])}: el carro no puede ir ahí "
                f"ni {cerca['atravesar']}")
    if cerca is not None and d_cerca < holgura:
        texto = (f"ese punto ({x:.2f}, {y:.2f}) queda a {d_cerca * 100:.0f} cm {_de(cerca['nombre'])}: el carro "
                 f"no cabe ahí (necesita {holgura * 100:.0f} cm desde su centro)")
        if cerca.get("clave") == "muelle":
            texto += "; para entrar al muelle pídale que vuelva al muelle (entra solo, de reversa)"
        return texto
    if not en_zona_libre(zonas, x, y):
        x0, y0, x1, y1 = zonas["libre"]
        return (f"ese punto ({x:.2f}, {y:.2f}) está fuera del piso por el que anda el carro "
                f"(x de {x0:.2f} a {x1:.2f} m, y de {y0:.2f} a {y1:.2f} m, alrededor de la pista)")
    return ""


def ruta_libre(zonas: dict, x0: float, y0: float, x1: float, y1: float, holgura_lateral: float,
               holgura_giro: float) -> list | None:
    """Puntos de paso [(x, y), ..., (x1, y1)] para ir de (x0, y0) a (x1, y1)
    sin pasar por ninguna huella: derecho si se puede y, si no, rodeando por
    las esquinas de las huellas (agrandadas lo que barre el carro girando: en
    cada punto de paso gira sobre su eje). Camino mas corto con Dijkstra sobre
    esas esquinas (son pocas: 4 por huella). None si no hay camino."""
    if tramo_bloqueado(zonas, x0, y0, x1, y1, holgura_lateral) is None:
        return [(x1, y1)]
    h = holgura_giro * 1.02
    nodos = [(x0, y0), (x1, y1)]
    # Esquinas de cada huella y del rectangulo que encierra el muelle (sus
    # paredes sueltas estan tan juntas que las esquinas de cada una quedan
    # pegadas a la de al lado: el rodeo util es el del muelle entero).
    rodear = zonas["prohibidas"] + ([zonas["muelle"]] if "muelle" in zonas else [])
    for z in rodear:
        c, s = math.cos(z["rumbo"]), math.sin(z["rumbo"])
        for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            lx, ly = sx * (z["ml"] + h), sy * (z["ma"] + h)
            px, py = z["cx"] + lx * c - ly * s, z["cy"] + lx * s + ly * c
            if en_zona_libre(zonas, px, py) and all(distancia_a_zona(o, px, py) >= holgura_giro
                                                    for o in zonas["prohibidas"]):
                nodos.append((px, py))
    n = len(nodos)
    dist = [math.inf] * n
    previo = [-1] * n
    hecho = [False] * n
    dist[0] = 0.0
    for _ in range(n):
        i = -1
        for k in range(n):
            if not hecho[k] and (i < 0 or dist[k] < dist[i]):
                i = k
        if i < 0 or dist[i] == math.inf:
            break
        if i == 1:
            break
        hecho[i] = True
        for k in range(n):
            if hecho[k] or k == i:
                continue
            (ax, ay), (bx, by) = nodos[i], nodos[k]
            if tramo_bloqueado(zonas, ax, ay, bx, by, holgura_lateral) is not None:
                continue
            d = dist[i] + math.hypot(bx - ax, by - ay)
            if d < dist[k]:
                dist[k] = d
                previo[k] = i
    if dist[1] == math.inf:
        return None
    ruta = []
    k = 1
    while k != 0:
        ruta.append(nodos[k])
        k = previo[k]
    ruta.reverse()
    return ruta


class LecturaCarro:
    """Lo que el carro lee en un ciclo de control.

    - linea: 5 bits, izquierda -> derecha (1 = ve negro)
    - distancia_mm: ultrasonico; None = nada en rango
    - pulsos_izq / pulsos_der: acumulados desde el encendido (encoder de un
      canal: no sabe el sentido)
    - medida_us: numero de medicion del ultrasonico (cambia con cada disparo)
    - tof_mm: laser VL53L0X frontal; None = nada hasta su alcance
    - medida_tof: numero de medicion del laser
    - cuna: infrarrojo de la cuna (sensor 12); None = no se lee
    (Clase normal y no dataclass: corre tambien en el ESP32 del carro.)
    """

    def __init__(self, linea, distancia_mm, pulsos_izq, pulsos_der, medida_us=0, tof_mm=None, medida_tof=0,
                 cuna=None):
        self.linea = linea
        self.distancia_mm = distancia_mm
        self.pulsos_izq = pulsos_izq
        self.pulsos_der = pulsos_der
        self.medida_us = medida_us
        self.tof_mm = tof_mm
        self.medida_tof = medida_tof
        self.cuna = cuna


class ControlCarro:
    def __init__(self, cfg: dict, *, largo_linea_m: float,
                 linea: list[tuple[float, float, float, float]] | None = None,
                 pose_muelle: tuple[float, float, float] | None = None,
                 zonas: dict | None = None):
        """`linea`: puntos (x, y, rumbo, s) de la linea de la pista, desde el
        muelle hasta la meta (el trazado de la pista es fijo y medido: el
        firmware del carro lo lleva igual). `pose_muelle`: donde queda el
        CENTRO del carro dentro del muelle. Sin estos dos, el carro sigue la
        linea como siempre pero no acepta ordenes que necesiten saber donde
        esta. `zonas`: piso libre y huellas prohibidas (ver `holguras_carro`
        arriba); sin ellas no revisa destinos contra el mapa."""
        v = cfg
        self.radio = v["diametro_rueda_mm"] / 2000
        self.via = v["ancho_mm"] / 1000 + 0.026          # entre centros de las ruedas (ruedas afuera del chasis)
        self.m_por_pulso = 2 * math.pi * self.radio / v["encoder_pulsos_por_vuelta"]
        self.sep_ir = v["separacion_sensores_linea_mm"] / 1000
        largo = v["largo_mm"] / 1000
        self.x_eje = -0.18 * largo                        # eje de las ruedas, desde el centro del carro
        self.x_ir = largo / 2 - 0.012                     # arreglo de infrarrojos
        self.x_us = largo / 2 + 0.002                     # ultrasonico
        self.eje_a_ir = self.x_ir - self.x_eje
        self.eje_a_us = self.x_us - self.x_eje
        self.eje_a_cola = largo / 2 + self.x_eje
        # Parte mas ancha: las ruedas o los rodillos guia de atras.
        self.medio_ancho = max(v["ancho_mm"] / 2000 + 0.024,
                               (v.get("rodillo_guia_y_mm", 0) + v.get("rodillo_guia_radio_mm", 0)) / 1000)
        self.v_linea = v["velocidad_linea_m_s"]
        self.v_maniobra = v["velocidad_maniobra_m_s"]
        self.v_giro = v["velocidad_giro_rueda_m_s"]
        self.a_max = v["aceleracion_max_m_s2"]
        self.umbral_obst = v["distancia_obstaculo_mm"]
        self.umbral_frenado = v.get("distancia_frenado_mm", 0)
        self.n_obst = v["lecturas_obstaculo"]
        self.ang_mirar = math.radians(v["angulo_mirar_grados"])
        self.libre_mm = v["distancia_libre_mm"]
        self.margen = v["margen_evasion_mm"] / 1000
        self.margen_pasar = v.get("margen_pasar_muro_mm", v["margen_evasion_mm"]) / 1000
        # Reversa al muelle con tiempo limite (se vio 35 s trabado en la boca,
        # avanzando de a milimetros): ver la accion "reversa_tope".
        self.reversa_max_s = v.get("reversa_tope_max_s", 15.0)
        self.reversa_sin_avance_s = v.get("reversa_tope_sin_avance_s", 3.0)
        self.reversa_avance_min = v.get("reversa_tope_avance_min_mm", 20) / 1000
        self.reversa_salida = v.get("reversa_tope_salida_mm", 150) / 1000
        self.reversa_fuerte_extra = v.get("reversa_tope_pwm_normal_mm", 50) / 1000
        self.ang_regreso = math.radians(v.get("angulo_regreso_grados", 45))
        self.largo_linea = largo_linea_m
        self.muro_medio_ancho = v.get("_muro_largo_mm", 100) / 2000
        self.muro_grueso = v.get("_muro_grueso_mm", 30) / 1000

        self.estado = "esperando_carga"
        self.fase = "ida"
        self.eventos: list[dict] = []
        self._acciones: list[dict] = []
        self._cmd = [0.0, 0.0]            # velocidad pedida HOY a cada rueda (despues de la rampa)
        self._objetivo = [0.0, 0.0]
        self._pulsos_prev: tuple[int, int] | None = None
        self.d_izq = 0.0                  # odometria con signo (el signo lo pone el comando)
        self.d_der = 0.0
        self.s_fase = 0.0                 # distancia recorrida en esta fase (ida o vuelta)
        self._cuenta_obst = 0
        self._cuenta_franja = 0
        self._sin_linea = 0.0
        self._ultimo_error = 0.0
        self._err_prev = 0.0
        self.medidas: dict[str, float] = {}
        self._movio = False
        # PWM bajo al entrar de reversa al muelle: con poco torque el motor se
        # ahoga contra el tope y las ruedas se DETIENEN (con torque completo
        # patinan contra el piso y el encoder sigue contando: nunca "llega").
        self.pwm_bajo = False
        # Ultimas 3 lecturas de cada infrarrojo: cada uno decide por mayoria
        # (una lectura suelta cambiada no mueve el volante ni "encuentra" una
        # linea que no esta).
        self._historia_linea: list[tuple[int, ...]] = []
        self._ultima_medida_us = -1
        self._us_nueva = True
        self._ultima_medida_tof = -1
        self._tof_nueva = True
        self._cuenta_obst_us = 0
        # Infrarrojo de la cuna (punto 15): el carro decide SOLO, sin esperar
        # a la radio, que ya lo cargaron (sale del muelle) y que en la meta
        # ya le sacaron el vaso (vuelve). 3 lecturas iguales seguidas.
        self._historia_cuna: list[bool] = []
        # Enlace por radio con la estacion (lo actualiza quien maneja la
        # radio). Sin enlace, el carro sigue solo: termina la vuelta; en la
        # meta espera que saquen el vaso, pero como mucho
        # `espera_meta_sin_enlace_s` (usuario, 2026-09-26: no es grave que
        # vuelva con el vaso; al reconectar la estacion no le carga otro
        # sin saber si trae uno).
        self.enlace_vivo = True
        self.espera_meta_sin_enlace = v.get("espera_meta_sin_enlace_s", 20.0)
        self._t_meta = 0.0

        # Ordenes (fase 7). La pose estimada es la del punto medio del EJE de
        # las ruedas (lo que da la odometria de un carro diferencial); hacia
        # afuera se informa la del centro del carro.
        self.linea = list(linea) if linea else []
        self.s_giro = v.get("marca_giro_mm", 170) / 1000
        self.ancho_giro = v.get("franja_giro_ancho_mm", 20) / 1000
        self.ancho_meta = v.get("franja_meta_ancho_mm", 50) / 1000
        self.pose_muelle = pose_muelle
        self.zonas = zonas
        self.holgura_lateral, self.holgura_destino, self.holgura_giro = holguras_carro(v)
        # Atascado en una orden: antes de quedarse quieto se aparta un poco por
        # donde vino (ese lado estaba libre), para no quedar apretado contra lo
        # que lo trabo y poder girar despues (usuario, 2026-09-27).
        self.apartarse_atascado = v.get("apartarse_atascado_mm", 50) / 1000
        self.pose_odo: list[float] | None = None
        if pose_muelle is not None:
            self.fijar_pose(*pose_muelle)
        self.ultima_orden: dict | None = None

    # ------------------------------------------------------------------
    # odometria: donde cree el carro que esta
    # ------------------------------------------------------------------

    def fijar_pose(self, x: float, y: float, rumbo: float) -> None:
        """Pone la posicion estimada en un valor conocido (el centro del
        carro): al encender en el muelle y cada vez que vuelve a entrar."""
        self.pose_odo = [x + self.x_eje * math.cos(rumbo), y + self.x_eje * math.sin(rumbo), rumbo]

    def posicion_estimada(self) -> tuple[float, float, float] | None:
        """Centro del carro segun la odometria (x, y, rumbo)."""
        if self.pose_odo is None:
            return None
        x, y, r = self.pose_odo
        return x - self.x_eje * math.cos(r), y - self.x_eje * math.sin(r), r

    # ------------------------------------------------------------------
    # ordenes (fase 7): el asistente o un boton del dashboard
    # ------------------------------------------------------------------

    def ordenar(self, orden: dict) -> tuple[bool, str]:
        """Valida una orden y, si se puede, la empieza a cumplir. Devuelve
        (aceptada, explicacion en palabras simples). Una orden nueva
        reemplaza a la anterior; `detener` se acepta siempre."""
        accion = orden.get("accion")
        if accion not in ORDENES:
            return False, f"Orden desconocida para el carro: {accion}"
        try:
            if accion == "detener":
                return self._orden_detener()
            if accion in ("avanzar", "retroceder"):
                return self._orden_recta(accion, float(orden.get("distancia_m", 0)))
            if accion == "girar":
                return self._orden_girar(float(orden.get("grados", 0)))
            if accion == "ir_a":
                return self._orden_ir_a(float(orden["x"]), float(orden["y"]))
        except (KeyError, TypeError, ValueError):
            return False, "Faltan datos o no son números en la orden del carro"
        return self._orden_linea(accion)

    def _empezar(self, acciones: list[dict], orden: dict) -> None:
        self.estado = MANUAL
        self.pwm_bajo = False
        self._acciones = acciones
        self.ultima_orden = orden
        self._evento("orden", **orden)

    def _fin_orden(self, evento: str = "orden_cumplida") -> dict:
        return {"tipo": "estado", "estado": ESPERANDO_ORDEN, "evento": evento}

    def _orden_detener(self) -> tuple[bool, str]:
        if self.estado in ("esperando_carga", ESPERANDO_ORDEN, "detenido") and max(abs(c) for c in self._cmd) < 1e-4:
            return True, "El carro ya está quieto"
        self._empezar([self._parar(), self._fin_orden("detenido_por_orden")], {"accion": "detener"})
        return True, "El carro frena (con su rampa, para no tumbar el vaso) y espera otra orden"

    def _orden_recta(self, accion: str, distancia: float) -> tuple[bool, str]:
        maximo = AVANCE_MAX_M if accion == "avanzar" else REVERSA_MAX_M
        if not 0 < distancia <= maximo:
            return False, (f"Para {accion} la distancia tiene que estar entre 0 y {maximo:g} m"
                           + (" (atrás no tiene sensor: solo reversas cortas)" if accion == "retroceder" else ""))
        if accion == "avanzar":
            pos = self.posicion_estimada()
            if self.zonas is not None and pos is not None:
                # Lo bajo (guias y topes del muelle) y la planta no los ve el
                # laser: se revisan contra el mapa antes de moverse.
                fx, fy = pos[0] + distancia * math.cos(pos[2]), pos[1] + distancia * math.sin(pos[2])
                z = tramo_bloqueado(self.zonas, pos[0], pos[1], fx, fy, self.holgura_lateral)
                if z is not None:
                    return False, (f"Avanzar {distancia * 100:.0f} cm lo lleva contra {z['nombre']}: el carro no "
                                   f"puede {z['atravesar']} (sus sensores no ven lo bajo)")
                if not en_zona_libre(self.zonas, fx, fy):
                    return False, (f"Avanzar {distancia * 100:.0f} cm lo saca del piso por el que anda el carro "
                                   "(alrededor de la pista)")
            paso = self._avanzar(distancia, self.v_maniobra)
            paso["vigilar"] = True
            pasos = self._revisar_camino(distancia) + [paso]
            texto = (f"Avanza {distancia * 100:.0f} cm despacio: antes mira el camino, y si ve algo adelante "
                     "se detiene")
        else:
            pasos = [{"tipo": "reversa", "distancia": distancia}]
            texto = f"Retrocede {distancia * 100:.0f} cm despacio (atrás no tiene sensor)"
        self._empezar([self._parar()] + pasos + [self._fin_orden()], {"accion": accion, "distancia_m": distancia})
        return True, texto

    def _salir_del_muelle(self, enderezar: bool = False):
        """Dentro del muelle no puede girar (lo encierran las guias): primero
        sale derecho, mirando el camino como en cualquier avance. Vale tambien
        si quedo a medio entrar o trabado en la boca: sale lo que le falte.
        Devuelve (pasos, (x, y) del centro al salir). Si esta dentro pero
        torcido (mas de ANGULO_SALIR_MUELLE respecto al canal): con `enderezar`
        primero gira sobre su eje hasta mirar hacia afuera (puede rozar las
        guias forradas con PTFE: es la unica salida); sin el, (None, None)."""
        pos = self.posicion_estimada()
        if pos is None:
            return [], None
        pasos = []
        rumbo = pos[2]
        if self.estado == "esperando_carga":
            falta = SALIR_DEL_MUELLE_M
        else:
            z = self.zonas.get("muelle") if self.zonas is not None else None
            if z is None or self.pose_muelle is None or distancia_a_zona(z, pos[0], pos[1]) > 0:
                return [], (pos[0], pos[1])
            mx, my, mr = self.pose_muelle
            if abs(_angulo(pos[2] - mr)) > ANGULO_SALIR_MUELLE:
                if not enderezar:
                    return None, None
                pasos.append({"tipo": "orientar", "rumbo": mr})
                rumbo = mr
            falta = SALIR_DEL_MUELLE_M - ((pos[0] - mx) * math.cos(mr) + (pos[1] - my) * math.sin(mr))
            if falta < 0.01:
                return pasos, (pos[0], pos[1])
        paso = self._avanzar(falta, self.v_maniobra)
        paso["vigilar"] = True
        # Solo mira al frente: girar +-15 grados para mirar a los lados rozaria
        # las guias (3 mm de holgura). El muelle es un canal recto.
        return (pasos + [self._medir("c0"), {"tipo": "camino", "distancia": falta, "solo_frente": True}, paso],
                (pos[0] + falta * math.cos(rumbo), pos[1] + falta * math.sin(rumbo)))

    MUELLE_AL_REVES = ("El carro está dentro del muelle y torcido: no puede salir de frente sin rozar las guías. "
                       "Pídale primero que vuelva al muelle (se endereza, sale derecho y entra de reversa)")

    def _orden_girar(self, grados: float) -> tuple[bool, str]:
        if not 0 < abs(grados) <= 180:
            return False, "El giro tiene que estar entre -180 y 180 grados (positivo = izquierda)"
        salir, _ = self._salir_del_muelle()
        if salir is None:
            return False, self.MUELLE_AL_REVES
        self._empezar([self._parar()] + salir + [self._girar(math.radians(grados)), self._fin_orden()],
                      {"accion": "girar", "grados": grados})
        return True, ((f"Primero sale del muelle ({SALIR_DEL_MUELLE_M * 100:.0f} cm derecho); después " if salir else "")
                      + f"gira {abs(grados):.0f}° a la {'izquierda' if grados > 0 else 'derecha'} sobre su eje")

    def revisar_ir_a(self, x: float, y: float, desde: tuple | None) -> str:
        """"" si el carro puede ir derecho de `desde` (su centro despues de
        salir del muelle, si estaba ahi) a (x, y); si no, el motivo. Un destino
        dentro de la planta, del muelle o de otra estructura, fuera del piso
        de la pista, o con el camino recto por encima de una huella, no se
        intenta: el laser no ve lo bajo y la planta no esta en la pista."""
        if self.zonas is None:
            return ""
        motivo = motivo_destino(self.zonas, x, y, self.holgura_destino)
        if motivo and desde is not None and not en_zona_libre(self.zonas, x, y):
            z = tramo_bloqueado(self.zonas, desde[0], desde[1], x, y, self.holgura_lateral)
            if z is not None:
                motivo += f"; además, el camino recto pasa por {z['nombre']} y el carro no puede {z['atravesar']}"
        if motivo:
            return motivo[0].upper() + motivo[1:]
        if desde is None:
            return ""
        z = tramo_bloqueado(self.zonas, desde[0], desde[1], x, y, self.holgura_lateral)
        if z is None:
            return ""
        texto = (f"El camino recto hasta ({x:.2f}, {y:.2f}) pasa por {z['nombre']}: el carro no puede "
                 f"{z['atravesar']} (el láser y el ultrasónico no ven lo bajo, y la planta no está en la pista)")
        ruta = ruta_libre(self.zonas, desde[0], desde[1], x, y, self.holgura_lateral, self.holgura_giro)
        if ruta and len(ruta) > 1:
            texto += (f". Rodeando sí se puede: pídale primero ir a ({ruta[0][0]:.2f}, {ruta[0][1]:.2f}) m "
                      "y después al punto")
        return texto

    def _orden_ir_a(self, x: float, y: float) -> tuple[bool, str]:
        pos = self.posicion_estimada()
        if pos is None:
            return False, "El carro no sabe dónde está (sin odometría): no puede ir a un punto"
        d = math.hypot(x - pos[0], y - pos[1])
        if d > IR_A_MAX_M:
            return False, (f"El punto está a {d:.2f} m: más de {IR_A_MAX_M:g} m de una vez acumula mucho error "
                           "de odometría; pídalo por partes")
        salir, desde = self._salir_del_muelle()
        if salir is None:
            return False, self.MUELLE_AL_REVES
        motivo = self.revisar_ir_a(x, y, desde)
        if motivo:
            return False, motivo
        destino = self._a_eje(x, y)
        self._empezar([self._parar()] + salir + [{"tipo": "ir_a", "x": destino[0], "y": destino[1], "intento": 1},
                       self._fin_orden("llego_al_punto")], {"accion": "ir_a", "x": x, "y": y})
        return True, (("Primero sale del muelle derecho; después " if salir else "")
                      + f"va a ({x:.2f}, {y:.2f}) m, a {d:.2f} m: gira hacia el punto y avanza vigilando adelante")

    def _en_el_muelle(self) -> bool:
        """Segun la odometria, el carro esta dentro del muelle o pegado a el
        (a menos de su holgura lateral): a medio entrar, trabado en la boca o
        atascado contra una guia."""
        z = self.zonas.get("muelle") if self.zonas is not None else None
        pos = self.posicion_estimada()
        if z is None or pos is None or self.pose_muelle is None:
            return False
        return distancia_a_zona(z, pos[0], pos[1]) < self.holgura_lateral

    def _reentrar_al_muelle(self) -> tuple[bool, str]:
        """Volver al muelle estando en el muelle (usuario, 2026-09-27: el
        carro se trabo contra la boca y quedo "atascado"). Tras rozar las guias
        la odometria no sirve (en la simulacion quedo 9 cm y 20 grados
        corrida), asi que NO se navega con ella: la linea de la pista pasa por
        el centro del muelle. Se endereza hacia afuera, busca la linea con los
        infrarrojos, se centra sobre ella, la sigue hacia afuera hasta pasar la
        boca y entra de reversa como siempre (las guias en V lo centran)."""
        mx, my, mr = self.pose_muelle
        pos = self.posicion_estimada()
        adentro = (pos[0] - mx) * math.cos(mr) + (pos[1] - my) * math.sin(mr)
        # Afuera hasta dejar la cola fuera de la boca: la reversa hasta el tope
        # tiene que ser de mas de 25 cm para contar como llegada.
        afuera = max(0.15, SALIR_DEL_MUELLE_M - adentro)
        acciones = [self._parar(), {"tipo": "orientar", "rumbo": mr},
                    self._girar(0.5, busca_linea=True), self._girar(-1.0, busca_linea=True),
                    {"tipo": "error", "motivo": "sin_linea"},
                    {"tipo": "alinear", "centrado": 0},
                    {"tipo": "seguir_corto", "distancia": afuera, "v": self.v_maniobra / 3},
                    self._parar(),
                    {"tipo": "reversa_tope", "hecho": 0.0, "quieto": 0.0},
                    {"tipo": "estado", "estado": "esperando_carga", "evento": "en_muelle"}]
        self._empezar(acciones, {"accion": "volver_muelle"})
        return True, ("Está en el muelle o pegado a él: se endereza, busca la línea con los infrarrojos, sale "
                      f"{afuera * 100:.0f} cm siguiéndola y vuelve a entrar de reversa")

    def _orden_linea(self, accion: str) -> tuple[bool, str]:
        if not self.linea or self.pose_odo is None:
            return False, "El carro no conoce el trazado de la pista: solo sigue la línea en su recorrido normal"
        if accion == "volver_muelle" and self.estado == "esperando_carga":
            return False, "El carro ya está en el muelle"
        if accion == "volver_muelle" and self._en_el_muelle():
            return self._reentrar_al_muelle()
        # En el muelle en reposo la linea esta justo debajo (se retoma alli);
        # a medio entrar (p. ej. trabado en la boca) primero sale derecho.
        salir, _ = ([], None) if self.estado == "esperando_carga" else self._salir_del_muelle(enderezar=True)
        if accion == "seguir_linea":
            fase = self.fase
        else:
            fase = "ida" if accion == "ir_meta" else "vuelta"
        x, y, r = self.pose_odo
        if salir:
            if salir[0]["tipo"] == "orientar":
                r = salir[0]["rumbo"]
            if salir[-1]["tipo"] == "avanzar":
                falta = salir[-1]["distancia"]
                x, y = x + falta * math.cos(r), y + falta * math.sin(r)
        i = min(range(len(self.linea)), key=lambda k: (self.linea[k][0] - x) ** 2 + (self.linea[k][1] - y) ** 2)
        s = self._s_de(i)
        if fase == "vuelta" and s < self.s_giro + 0.2:
            # Entre el muelle y la marca de giro: volviendo por la linea no
            # veria la marca. Se va primero a un punto de la linea pasada la marca.
            i = self._indice_en(self.s_giro + 0.25)
            s = self._s_de(i)
        lx, ly, lr = self.linea[i][:3]
        acciones = [self._parar()] + salir
        if math.hypot(lx - x, ly - y) > LEJOS_DE_LA_LINEA_M:
            # Hasta la linea con la odometria, sin cruzar ninguna huella (muelle,
            # planta): derecho si se puede y, si no, rodeandola por sus esquinas.
            ruta = [(lx, ly)]
            if self.zonas is not None:
                ruta = ruta_libre(self.zonas, x, y, lx, ly, self.holgura_lateral, self.holgura_giro)
                if ruta is None:
                    return False, ("No hay un camino libre hasta la línea desde donde cree estar el carro "
                                   f"({x:.2f}, {y:.2f}): muévalo con órdenes cortas (retroceder, girar) y pruebe otra vez")
            for px, py in ruta:
                acciones.append({"tipo": "ir_a", "x": px, "y": py, "intento": 1})
        acciones += [{"tipo": "orientar", "rumbo": lr if fase == "ida" else lr + math.pi},
                     self._girar(0.5, busca_linea=True), self._girar(-1.0, busca_linea=True),
                     {"tipo": "error", "motivo": "sin_linea"},
                     # Lo recorrido en esta fase = donde esta sobre la linea: asi
                     # la meta (o la marca de giro) se reconoce aunque este cerca,
                     # y la franja que tiene debajo al empezar se ignora.
                     {"tipo": "retomar", "fase": fase, "s_fase": s if fase == "ida" else self.largo_linea - s}]
        self._empezar(acciones, {"accion": accion})
        texto = {"ir_meta": "Va a la línea y la sigue hasta la meta (esquivando los muros como siempre)",
                 "volver_muelle": "Va a la línea, la sigue de vuelta y entra de reversa al muelle",
                 "seguir_linea": f"Busca la línea y retoma el recorrido ({'ida' if fase == 'ida' else 'vuelta'})"}
        return True, texto[accion]

    def _revisar_camino(self, distancia: float) -> list[dict]:
        """Mirar el camino antes de moverse: frente, +15 y -15 grados."""
        a = ANGULO_REVISAR_CAMINO
        return [self._medir("c0"), self._girar(a), self._medir("c+"), self._girar(-2 * a), self._medir("c-"),
                self._girar(a), {"tipo": "camino", "distancia": distancia}]

    def _atascado(self, diferencia: float, *, en_reversa: bool = False, recorrido: float = 0.0) -> None:
        """En una recta, una rueda conto mucho mas que la otra: algo sujeta
        el carro (una esquina contra un muro) y la otra rueda patina. Frena y
        DESHACE el tramo por donde vino (ese camino estaba libre: ahi acababa
        de girar), como mucho la reversa maxima y al menos
        `apartarse_atascado_mm`: asi no queda apretado contra lo que lo trabo,
        la odometria se corre poco (vuelve por sus propias huellas) y la orden
        siguiente (volver al muelle, girar) puede girar sin rozarlo."""
        self._evento("atascado", diferencia_mm=round(diferencia * 1000))
        distancia = min(REVERSA_MAX_M, max(self.apartarse_atascado, abs(recorrido)))
        if en_reversa:
            apartarse = self._avanzar(distancia, self.v_maniobra)
            apartarse["vigilar"] = True
        else:
            apartarse = {"tipo": "reversa", "distancia": distancia}
        # Apartandose no se vuelve a revisar el atasco (la rueda que patinaba
        # puede seguir contando distinto un momento).
        apartarse["sin_atasco"] = True
        self._acciones = [self._parar(), apartarse, self._parar(), self._fin_orden("detenido_atascado")]

    def _a_eje(self, x: float, y: float) -> tuple[float, float]:
        """Punto pedido para el centro del carro -> punto para el eje (con el
        rumbo de llegada = direccion desde donde esta ahora)."""
        ex, ey, _ = self.pose_odo
        r = math.atan2(y - ey, x - ex)
        return x + self.x_eje * math.cos(r), y + self.x_eje * math.sin(r)

    def _pose_en_linea(self, s: float, media_vuelta: float) -> None:
        """El CENTRO del carro esta sobre la linea en `s` (siguiendola: el
        arreglo de infrarrojos va centrado en ella), mirando a lo largo de la
        linea (`media_vuelta` = pi de vuelta)."""
        if not self.linea or self.pose_odo is None:
            return
        lx, ly, lr = self.linea[self._indice_en(s)][:3]
        self.fijar_pose(lx, ly, _angulo(lr + media_vuelta))

    def _s_de(self, i: int) -> float:
        """Distancia sobre la linea desde el muelle hasta el punto i."""
        return self.linea[i][3]

    def _indice_en(self, s: float) -> int:
        return min(range(len(self.linea)), key=lambda k: abs(self.linea[k][3] - s))

    # ------------------------------------------------------------------
    # ordenes de afuera (la planta)
    # ------------------------------------------------------------------

    def cargar(self) -> None:
        """El infrarrojo de la cuna confirmo el vaso: sale del muelle."""
        if self.estado == "esperando_carga":
            self.fase = "ida"
            self.s_fase = 0.0
            self.estado = "siguiendo"
            self._evento("salida")

    def vaso_retirado(self) -> None:
        """En la meta sacaron el vaso: media vuelta y regreso."""
        if self.estado == "en_meta":
            self.estado = "maniobra"
            self._acciones = [self._girar(math.pi), {"tipo": "fase", "fase": "vuelta"}]

    # ------------------------------------------------------------------
    # ciclo de control
    # ------------------------------------------------------------------

    def paso(self, lectura: LecturaCarro, dt: float) -> tuple[float, float]:
        self._odometria(lectura)
        self._historia_linea = (self._historia_linea + [tuple(lectura.linea)])[-3:]
        votos = [sum(h[i] for h in self._historia_linea) for i in range(len(lectura.linea))]
        mitad = len(self._historia_linea) / 2
        lectura = LecturaCarro(tuple(1 if v > mitad else 0 for v in votos), lectura.distancia_mm,
                               lectura.pulsos_izq, lectura.pulsos_der, lectura.medida_us,
                               lectura.tof_mm, lectura.medida_tof, lectura.cuna)
        self._tof_nueva = lectura.medida_tof != self._ultima_medida_tof
        self._ultima_medida_tof = lectura.medida_tof
        # El ultrasonico da una medicion nueva cada ~60 ms: los votos y las
        # medianas cuentan MEDICIONES, no ciclos de control.
        self._us_nueva = lectura.medida_us != self._ultima_medida_us
        self._ultima_medida_us = lectura.medida_us
        if lectura.cuna is not None:
            self._historia_cuna = (self._historia_cuna + [bool(lectura.cuna)])[-3:]
            if len(self._historia_cuna) == 3 and len(set(self._historia_cuna)) == 1:
                if self.estado == "esperando_carga" and self._historia_cuna[0]:
                    self.cargar()
                elif self.estado == "en_meta" and not self._historia_cuna[0]:
                    self._evento("vaso_retirado")
                    self.vaso_retirado()
        if self.estado == "en_meta":
            self._t_meta = self._t_meta + dt if not self.enlace_vivo else 0.0
            if self._t_meta >= self.espera_meta_sin_enlace:
                self._evento("vuelve_con_vaso")
                self.vaso_retirado()
                self._t_meta = 0.0
        if self.estado == "siguiendo":
            self._seguir(lectura, dt)
        elif self.estado in ("maniobra", MANUAL):
            self._maniobrar(lectura, dt)
        else:   # esperando_carga, en_meta, esperando_orden, detenido
            self._objetivo = [0.0, 0.0]
        return self._rampa(dt)

    def _odometria(self, l: LecturaCarro) -> None:
        if self._pulsos_prev is None:
            self._pulsos_prev = (l.pulsos_izq, l.pulsos_der)
            return
        di = (l.pulsos_izq - self._pulsos_prev[0]) * self.m_por_pulso
        dd = (l.pulsos_der - self._pulsos_prev[1]) * self.m_por_pulso
        self._pulsos_prev = (l.pulsos_izq, l.pulsos_der)
        # Encoder de un solo canal: el sentido lo da lo que se le esta
        # pidiendo al motor.
        di *= 1 if self._cmd[0] >= 0 else -1
        dd *= 1 if self._cmd[1] >= 0 else -1
        self.d_izq += di
        self.d_der += dd
        self.s_fase += abs(di + dd) / 2
        self._movio = (di != 0 or dd != 0)
        if self.pose_odo is not None:
            # Carro diferencial: el eje avanza el promedio de las dos ruedas y
            # gira la diferencia dividida por la trocha.
            ds, dth = (di + dd) / 2, (dd - di) / self.via
            x, y, r = self.pose_odo
            self.pose_odo = [x + ds * math.cos(r + dth / 2), y + ds * math.sin(r + dth / 2), _angulo(r + dth)]

    def _rampa(self, dt: float) -> tuple[float, float]:
        """Ninguna rueda cambia de velocidad mas rapido que `a_max`: arranques
        y frenadas suaves (el vaso colgado no se balancea)."""
        paso = self.a_max * dt
        for i in (0, 1):
            d = self._objetivo[i] - self._cmd[i]
            self._cmd[i] += max(-paso, min(paso, d))
        return self._cmd[0], self._cmd[1]

    def _frenado(self, v: float) -> float:
        """Distancia que recorre una rueda frenando desde `v` con la rampa."""
        return v * v / (2 * self.a_max)

    # ------------------------------------------------------------------
    # seguir la linea
    # ------------------------------------------------------------------

    def _posicion_linea(self, bits) -> float | None:
        activos = [i for i, b in enumerate(bits) if b]
        if not activos:
            return None
        # +: la linea esta a la izquierda del centro del arreglo.
        return sum((2 - i) * self.sep_ir for i in activos) / len(activos)

    def _seguir(self, l: LecturaCarro, dt: float) -> None:
        # Franja transversal (meta o marca de giro): 4 o 5 infrarrojos a la
        # vez, dos lecturas seguidas. Se ignora al principio de cada fase
        # (el carro sale del muelle pasando sobre la marca de giro).
        if sum(l.linea) >= 4:
            self._cuenta_franja += 1
        else:
            self._cuenta_franja = 0
        if self._cuenta_franja >= 2 and self.s_fase > 0.5:
            self._cuenta_franja = 0
            # Las franjas son puntos FIJOS y medidos de la pista, como el muelle:
            # al verlas la odometria se vuelve a poner en su lugar. Sin esto, tras
            # una vuelta con tres evasiones el carro "creia" estar a ~30 cm de
            # donde estaba (se vio en la simulacion, 2026-09-27) y las ordenes que
            # usan el mapa (no pisar el muelle ni la planta) partian de ahi.
            if self.fase == "ida":
                self._pose_en_linea(self.largo_linea - self.ancho_meta - self.x_ir, 0.0)
            else:
                self._pose_en_linea(self.s_giro + self.ancho_giro / 2 + self.x_ir, math.pi)
            if self.fase == "ida":
                self.estado = "maniobra"
                self._acciones = [self._parar(), {"tipo": "estado", "estado": "en_meta", "evento": "meta"}]
            else:
                # Marca de giro: media vuelta sobre el eje y de reversa al muelle.
                self.estado = "maniobra"
                self._acciones = [self._parar(), {"tipo": "evento", "ev": "marca_giro"}, self._girar(math.pi),
                                  {"tipo": "alinear", "centrado": 0},
                                  # Enderezarse: 15 cm siguiendo la linea hacia adelante
                                  # (el eje de las ruedas vuelve sobre ella, como un
                                  # remolque); asi entra DERECHO de reversa.
                                  {"tipo": "seguir_corto", "distancia": 0.15},
                                  self._parar(),
                                  {"tipo": "reversa_tope", "hecho": 0.0, "quieto": 0.0},
                                  {"tipo": "estado", "estado": "esperando_carga", "evento": "en_muelle"}]
            return

        if self._obstaculo_confirmado(l):
            self.estado = "maniobra"
            a = self.ang_mirar
            self._acciones = [self._parar(), self._medir("frente"), self._girar(a), self._medir("izq"),
                              self._girar(-2 * a), self._medir("der"), self._girar(a), {"tipo": "decidir"}]
            return

        e = self._posicion_linea(l.linea)
        if e is None:
            self._sin_linea += dt
            if self._sin_linea > 0.15:
                # Se perdio la linea: buscarla girando hacia donde se vio por
                # ultima vez, y si no, hacia el otro lado.
                self._evento("linea_perdida")
                lado = 1 if self._ultimo_error >= 0 else -1
                self.estado = "maniobra"
                self._acciones = [self._parar(), self._girar(lado * 1.0, busca_linea=True),
                                  self._girar(-lado * 2.0, busca_linea=True), {"tipo": "error", "motivo": "sin_linea"}]
            e = self._ultimo_error
        else:
            self._sin_linea = 0.0
            self._ultimo_error = e
        # Control proporcional-derivativo sobre la posicion de la linea; mas
        # lento cuanto mas desviado (en las curvas).
        de = (e - self._err_prev) / dt if dt > 0 else 0.0
        self._err_prev = e
        w = 28.0 * e + 1.2 * de
        v = self.v_linea * max(0.4, 1 - abs(e) / (2 * self.sep_ir))
        # Zona de frenado: algo adelante a menos de `distancia_frenado_mm` ->
        # velocidad de maniobra (llega despacio al muro aunque vaya rapido).
        cerca = [d for d in (l.tof_mm, l.distancia_mm) if d is not None]
        if cerca and min(cerca) < self.umbral_frenado:
            v = min(v, self.v_maniobra)
        self._objetivo = [v - w * self.via / 2, v + w * self.via / 2]

    def _obstaculo_confirmado(self, l: LecturaCarro, evento: str = "obstaculo") -> bool:
        """N mediciones seguidas del laser por debajo del umbral, o 2 del
        ultrasonico (respaldo, mide mas lento). Si se confirma, deja el evento."""
        if self._tof_nueva:
            cerca = l.tof_mm is not None and l.tof_mm < self.umbral_obst
            self._cuenta_obst = self._cuenta_obst + 1 if cerca else 0
        if self._us_nueva:
            cerca = l.distancia_mm is not None and l.distancia_mm < self.umbral_obst
            self._cuenta_obst_us = self._cuenta_obst_us + 1 if cerca else 0
        if self._cuenta_obst >= self.n_obst or self._cuenta_obst_us >= 2:
            por_laser = self._cuenta_obst >= self.n_obst
            self._cuenta_obst = self._cuenta_obst_us = 0
            self._evento(evento, sensor="laser" if por_laser else "ultrasonico",
                         distancia_mm=round(l.tof_mm if por_laser else l.distancia_mm, 1))
            return True
        return False

    # ------------------------------------------------------------------
    # maniobras: una cola de acciones sencillas medidas con los encoders
    # ------------------------------------------------------------------

    def _parar(self) -> dict:
        return {"tipo": "parar", "quieto": 0.0}

    def _girar(self, angulo: float, *, busca_linea: bool = False) -> dict:
        return {"tipo": "girar", "angulo": angulo, "busca_linea": busca_linea}

    def _avanzar(self, distancia: float, v: float, *, hasta_linea: bool = False) -> dict:
        return {"tipo": "avanzar", "distancia": distancia, "v": v, "hasta_linea": hasta_linea}

    def _medir(self, nombre: str, n: int = 5) -> dict:
        return {"tipo": "medir", "nombre": nombre, "n": n, "lecturas": []}

    def _maniobrar(self, l: LecturaCarro, dt: float) -> None:
        if not self._acciones:
            self.estado = "siguiendo"
            self._err_prev = self._ultimo_error = 0.0
            return
        a = self._acciones[0]
        t = a["tipo"]
        if "inicio" not in a:
            a["inicio"] = (self.d_izq, self.d_der)
        di, dd = self.d_izq - a["inicio"][0], self.d_der - a["inicio"][1]
        hecho = False

        if t == "parar":
            self._objetivo = [0.0, 0.0]
            a["quieto"] = a["quieto"] + dt if max(abs(c) for c in self._cmd) < 1e-4 else 0.0
            hecho = a["quieto"] > 0.2

        elif t == "girar":
            signo = 1 if a["angulo"] > 0 else -1
            girado = (dd - di) / self.via
            falta = abs(a["angulo"]) - abs(girado)
            # Se corta antes lo que la rampa va a seguir girando al frenar.
            if falta - 2 * self._frenado(abs(self._cmd[1])) / self.via <= 0:
                self._objetivo = [0.0, 0.0]
                hecho = max(abs(c) for c in self._cmd) < 1e-4
            else:
                self._objetivo = [-signo * self.v_giro, signo * self.v_giro]
            # Buscando la linea: cuenta como encontrada solo si se ve en
            # CONFIRMAR_LINEA lecturas seguidas (no por un reflejo).
            a["vista"] = a.get("vista", 0) + 1 if self._posicion_linea(l.linea) is not None else 0
            if a["busca_linea"] and a["vista"] >= CONFIRMAR_LINEA:
                # Encontrada: se quitan SOLO los pasos de la busqueda (y el
                # "error" que venia si no aparecia); lo que seguia despues (por
                # ejemplo enderezarse y entrar de reversa al muelle) se hace igual.
                while self._acciones and (self._acciones[0].get("busca_linea") or self._acciones[0]["tipo"] == "error"):
                    self._acciones.pop(0)
                self._objetivo = [0.0, 0.0]
                return

        elif t == "avanzar":
            if a.get("vigilar") and self._obstaculo_confirmado(l, "bloqueado"):
                # Orden de avanzar con algo adelante: se detiene y avisa (no
                # esquiva por su cuenta en modo de ordenes).
                self._acciones = [self._parar(), self._fin_orden("detenido_por_obstaculo")]
                return
            if a.get("vigilar") and not a.get("sin_atasco") and abs(di - dd) > DIFERENCIA_ATASCADO_M:
                self._atascado(di - dd, recorrido=(di + dd) / 2)
                return
            recorrido = (di + dd) / 2
            if a["hasta_linea"]:
                # El infrarrojo del centro sobre la linea en CONFIRMAR_LINEA
                # lecturas seguidas (cruzando la linea de verdad la ve en ~18;
                # dos lecturas malas seguidas no alcanzan).
                if l.linea[2]:
                    a.setdefault("desde", recorrido)
                    a["vista"] = a.get("vista", 0) + 1
                else:
                    a.pop("desde", None)
                    a["vista"] = 0
                if a["vista"] >= CONFIRMAR_LINEA:
                    # Seguir hasta que el EJE de las ruedas quede sobre la linea
                    # (el carro gira sobre su eje).
                    a["distancia"] = a["desde"] + self.eje_a_ir
                    a["hasta_linea"] = False
            if recorrido + self._frenado(abs(self._cmd[0])) >= a["distancia"]:
                if a.get("hasta_linea"):
                    # Se llego al maximo sin ver la linea: buscarla.
                    self._acciones = [self._parar(), self._girar(1.0, busca_linea=True),
                                      self._girar(-2.0, busca_linea=True), {"tipo": "error", "motivo": "sin_linea"}]
                    self._evento("linea_no_encontrada")
                    return
                self._objetivo = [0.0, 0.0]
                hecho = max(abs(c) for c in self._cmd) < 1e-4
            else:
                # Derecho: se corrige con la diferencia de pulsos de las dos ruedas.
                corr = 2.0 * (di - dd)
                self._objetivo = [a["v"] - corr, a["v"] + corr]

        elif t == "alinear":
            # Despues de la media vuelta el eje de las ruedas sigue sobre la
            # linea y el arreglo de infrarrojos quedo adelante, cerca de ella:
            # girar sobre el eje hasta centrar el infrarrojo del medio deja
            # el carro DERECHO sobre la linea (+-4 grados) para entrar al muelle.
            e = self._posicion_linea(l.linea)
            if e is None:
                self._acciones[0:1] = [self._girar(0.35, busca_linea=True), self._girar(-0.7, busca_linea=True),
                                       {"tipo": "alinear", "centrado": 0}]
                return
            a["centrado"] = a["centrado"] + 1 if abs(e) < 0.004 else 0
            if a["centrado"] >= 3:
                self._objetivo = [0.0, 0.0]
                hecho = max(abs(c) for c in self._cmd) < 1e-4
            else:
                w = max(0.012, min(self.v_giro, 1.5 * abs(e))) * (1 if e > 0 else -1)
                self._objetivo = [-w, w]

        elif t == "seguir_corto":
            e = self._posicion_linea(l.linea)
            e = self._ultimo_error if e is None else e
            self._ultimo_error = e
            recorrido = (di + dd) / 2
            if recorrido + self._frenado(abs(self._cmd[0])) >= a["distancia"]:
                self._objetivo = [0.0, 0.0]
                hecho = True
            else:
                w = 28.0 * e
                # Mas despacio (`v`) el mismo giro endereza en menos camino: sirve
                # cuando arranca torcido respecto a la linea (reentrar al muelle).
                v = a.get("v", self.v_maniobra)
                self._objetivo = [v - w * self.via / 2, v + w * self.via / 2]

        elif t == "reversa_tope":
            # De reversa al muelle: las guias en V lo centran y los topes lo
            # paran. Llego cuando las ruedas dejan de dar pulsos contra el tope.
            # Derecho con los encoders solo hasta la boca del muelle; adentro
            # manda la guia: si el control peleara por mantener el rumbo, el
            # carro se trabaria torcido contra ella (se vio en la simulacion).
            # `previo`: lo que ya retrocedio en el intento anterior (menos la
            # salida hacia adelante), para medir siempre desde la misma marca.
            atras = abs((di + dd) / 2) + a.get("previo", 0.0)
            # PWM bajo: contra el tope el motor se ahoga antes de que la llanta
            # patine. En el reintento va con el PWM normal hasta pasar el punto
            # donde se trabo (con el bajo no alcanza a correr el rodillo por la
            # guia en V) y vuelve al bajo antes de llegar al tope.
            self.pwm_bajo = atras >= a.get("fuerte_hasta", 0.0)
            corr = 2.0 * (di - dd) if atras < 0.25 else 0.0
            v = -0.04
            self._objetivo = [v - corr, v + corr]
            a["quieto"] = 0.0 if self._movio else a["quieto"] + dt
            # Solo cuenta como llegada si ya hizo casi toda la reversa (desde la
            # marca de giro son ~44 cm): trabado antes = no llego.
            hecho = atras > 0.25 and a["quieto"] > 0.6
            # Tiempo limite: en total (`reversa_tope_max_s`) y sin avanzar
            # (menos de `reversa_tope_avance_min_mm` en `reversa_tope_sin_avance_s`,
            # sin estar ya a fondo). Un pulso suelto cada tanto (trabado contra
            # la guia, avanzando de a milimetros) no cuenta como avanzar.
            a["t"] = a.get("t", 0.0) + dt
            if atras - a.get("marca", 0.0) >= self.reversa_avance_min:
                a["marca"], a["t_marca"] = atras, 0.0
            else:
                a["t_marca"] = a.get("t_marca", 0.0) + dt
            trabado = not hecho and (a["t"] > self.reversa_max_s
                                     or (atras <= 0.25 and a["t_marca"] > self.reversa_sin_avance_s))
            if hecho:
                self._objetivo = [0.0, 0.0]
                self._cmd = [0.0, 0.0]
                self.pwm_bajo = False
            elif abs(atras) > 0.6:
                self.pwm_bajo = False
                self._acciones = [{"tipo": "error", "motivo": "no_llego_al_tope"}]
                return
            elif trabado:
                self.pwm_bajo = False
                if a.get("reintento"):
                    # Segundo intento tambien trabado: se detiene y avisa.
                    self._acciones = [self._parar(), {"tipo": "error", "motivo": "no_llego_al_tope"}]
                    return
                # Primer intento: sale derecho hacia adelante y vuelve a entrar
                # de reversa UNA vez; lo que seguia (quedar esperando la carga)
                # se conserva. Se endereza sobre la linea (como tras la media
                # vuelta): trabado, la guia lo dejo torcido, y salir con los
                # pulsos repetiria el mismo angulo y la misma trabada.
                self._evento("reversa_reintento", retrocedido_m=round(atras, 3), tiempo_s=round(a["t"], 1))
                salida = self.reversa_salida
                self._acciones[0:1] = [self._parar(), {"tipo": "alinear", "centrado": 0},
                                       {"tipo": "seguir_corto", "distancia": salida, "v": self.v_maniobra / 3},
                                       self._parar(),
                                       {"tipo": "reversa_tope", "hecho": 0.0, "quieto": 0.0, "reintento": True,
                                        "previo": max(0.0, atras - salida),
                                        "fuerte_hasta": atras + self.reversa_fuerte_extra}]
                return

        elif t == "reversa":
            # Reversa por orden: lenta y derecha (corrigiendo con los pulsos).
            atras = -(di + dd) / 2
            if not a.get("sin_atasco") and abs(di - dd) > DIFERENCIA_ATASCADO_M:
                self._atascado(di - dd, en_reversa=True, recorrido=(di + dd) / 2)
                return
            if atras + self._frenado(abs(self._cmd[0])) >= a["distancia"]:
                self._objetivo = [0.0, 0.0]
                hecho = max(abs(c) for c in self._cmd) < 1e-4
            else:
                corr = 2.0 * (di - dd)
                v = -self.v_maniobra / 2
                self._objetivo = [v - corr, v + corr]

        elif t == "ir_a":
            # Hacia un punto con la odometria: girar hacia el, avanzar vigilando
            # y volver a mirar; con error, corrige hasta INTENTOS_IR_A veces.
            x, y, r = self.pose_odo
            dx, dy = a["x"] - x, a["y"] - y
            d = math.hypot(dx, dy)
            if d < TOLERANCIA_IR_A_M or a["intento"] > INTENTOS_IR_A:
                self._acciones.pop(0)
                if d >= TOLERANCIA_IR_A_M:
                    self._evento("punto_con_error", error_m=round(d, 3))
                return
            giro = _angulo(math.atan2(dy, dx) - r)
            pasos = [self._girar(giro)] if abs(giro) > math.radians(2) else []
            avance = self._avanzar(d, self.v_maniobra)
            avance["vigilar"] = True
            # El camino se revisa la primera vez; las correcciones son cortas.
            revisar = self._revisar_camino(d) if a["intento"] == 1 else []
            siguiente = dict(a)
            siguiente["intento"] = a["intento"] + 1
            self._acciones[0:1] = pasos + revisar + [avance, siguiente]
            return

        elif t == "camino":
            # Con las 3 medidas (frente, +15, -15): algo DENTRO del ancho del
            # carro y antes del final del recorrido bloquea el camino.
            ancho = self.medio_ancho + self.margen
            largo = a["distancia"] + self.margen
            bloqueos = []
            direcciones = (("c0", 0.0),) if a.get("solo_frente") else (
                ("c0", 0.0), ("c+", ANGULO_REVISAR_CAMINO), ("c-", -ANGULO_REVISAR_CAMINO))
            for nombre, ang in direcciones:
                d = self.medidas.get(nombre, math.inf) / 1000
                if d * math.cos(ang) < largo and abs(d * math.sin(ang)) < ancho:
                    bloqueos.append(round(d * 1000))
            self._acciones.pop(0)
            if bloqueos:
                self._evento("camino_bloqueado", distancias_mm=bloqueos)
                self._acciones = [self._parar(), self._fin_orden("no_se_movio")]
            return

        elif t == "orientar":
            # Mirar hacia un rumbo absoluto (segun la odometria).
            giro = _angulo(a["rumbo"] - self.pose_odo[2])
            self._acciones[0:1] = [self._girar(giro)] if abs(giro) > math.radians(2) else []
            return

        elif t == "retomar":
            # Ya ve la linea: vuelve al recorrido automatico en esa fase.
            self._acciones.pop(0)
            self.fase = a["fase"]
            self.s_fase = a["s_fase"]
            self.estado = "siguiendo"
            self._err_prev = self._ultimo_error = 0.0
            self._evento("ruta_retomada")
            return

        elif t == "medir":
            self._objetivo = [0.0, 0.0]
            # Mediciones del laser (cada 33 ms); si no ve nada hasta su
            # alcance, vale la del ultrasonico (ve mas lejos).
            if not self._tof_nueva:
                return
            d = l.tof_mm if l.tof_mm is not None else l.distancia_mm
            a["lecturas"].append(d if d is not None else math.inf)
            if len(a["lecturas"]) >= a["n"]:
                lec = sorted(a["lecturas"])
                self.medidas[a["nombre"]] = lec[len(lec) // 2]     # mediana
                hecho = True

        elif t == "decidir":
            self._planear_evasion()
            return

        elif t == "fase":
            self.fase = a["fase"]
            self.s_fase = 0.0
            self._evento("vuelta" if a["fase"] == "vuelta" else a["fase"])
            hecho = True

        elif t == "estado":
            self._acciones.pop(0)
            self.estado = a["estado"]
            self._objetivo = [0.0, 0.0]
            if a["estado"] == "esperando_carga" and self.pose_muelle is not None:
                # Entro al muelle: la posicion se vuelve a poner en la conocida
                # (se borra el error que acumulo la odometria en la vuelta).
                self.fijar_pose(*self.pose_muelle)
            self._evento(a["evento"])
            return

        elif t == "evento":
            self._evento(a["ev"])
            hecho = True

        elif t == "error":
            self.estado = "detenido"
            self._objetivo = [0.0, 0.0]
            self._acciones = []
            self._evento("error", motivo=a["motivo"])
            return

        if hecho:
            self._acciones.pop(0)

    def _planear_evasion(self) -> None:
        izq, der = self.medidas.get("izq", math.inf), self.medidas.get("der", math.inf)
        if izq >= self.libre_mm and der >= self.libre_mm:
            lado = 1                                  # empate: siempre por la izquierda
        else:
            lado = 1 if izq >= der else -1
        frente = self.medidas.get("frente", self.umbral_obst)
        frente = self.umbral_obst if math.isinf(frente) else frente
        # Geometria medida desde el eje de las ruedas (el carro gira sobre el).
        lateral = self.muro_medio_ancho + self.medio_ancho + self.margen
        d1 = lateral / math.sin(math.pi / 4)
        muro = frente / 1000 + self.eje_a_us                  # cara del muro, desde el eje
        d2 = muro + self.muro_grueso + self.eje_a_cola + self.margen_pasar - lateral
        self._evento("evasion", lado="izquierda" if lado > 0 else "derecha",
                     izq_mm=None if math.isinf(izq) else round(izq), der_mm=None if math.isinf(der) else round(der))
        q, qr = math.pi / 4, self.ang_regreso
        self._acciones = [
            self._girar(lado * q),
            self._avanzar(d1, self.v_maniobra),
            self._girar(-lado * q),
            self._avanzar(d2, self.v_maniobra),
            self._girar(-lado * qr),
            self._avanzar(lateral / math.sin(qr) + 0.15, self.v_maniobra, hasta_linea=True),
            self._girar(lado * qr),
            {"tipo": "evento", "ev": "linea_recuperada"},
        ]

    def _evento(self, ev: str, **datos) -> None:
        e = {"ev": ev, "fase": self.fase}
        e.update(datos)
        self.eventos.append(e)
