"""
pista.py - Geometría de la pista ovalada y construcción de la escena de PyBullet (pista y carros).

La usan dos procesos distintos:
  - servidor_pista.py (la FÍSICA): necesita las colisiones (piso y muros) y los carros con física.
  - render_pista.py (la CÁMARA): necesita lo visual (asfalto, pianos, línea de meta, adornos de
    cada estilo) y unos carros "títere" que solo se colocan donde dice la física.
Por eso todo está escrito una sola vez aquí, con banderas `visual` y `colision`.

La pista es un "estadio" (como un óvalo de NASCAR): dos rectas de largo L unidas por dos medias
circunferencias de radio R, medidas sobre la LÍNEA CENTRAL. Se recorre en sentido antihorario
(mirada desde arriba), así que la izquierda del piloto siempre apunta hacia el interior del óvalo.

    s = distancia recorrida sobre la línea central desde la meta (0 <= s < P, P = 2L + 2*pi*R)
    d = desplazamiento lateral respecto de la línea central (+ hacia la izquierda = hacia adentro)

Con (s, d) todo se vuelve fácil: contar vueltas (s pasa de casi P a casi 0), ordenar posiciones
(distancia acumulada), el piloto automático (apuntar a s + adelanto) y reaparecer un carro volcado
(ponerlo en su mismo s, en el centro).

Medidas: el racecar de pybullet_data es un carro a escala 1:10 (MIT RACECAR): 0,45 m de largo,
0,29 m de ancho entre ruedas, 0,325 m entre ejes. La pista se dimensionó para él: 2,4 m de ancho
(caben 3 carros lado a lado con margen para adelantar), curvas de 3,5 m de radio (a 2,5 m/s la
aceleración lateral es v^2/R = 1,8 m/s^2, muy lejos del límite de agarre ~9,8 m/s^2 con fricción 1,
así que no derrapa) y rectas de 8 m. Una vuelta mide P = 16 + 22 = 38 m: a ~2 m/s, unos 19 s.
"""

from __future__ import annotations

import math
import os
import tempfile

import pybullet as p
import pybullet_data

# ---------------------------------------------------------------------------------------------
# Medidas de la pista (metros)
# ---------------------------------------------------------------------------------------------
LARGO_RECTA = 8.0        # L: largo de cada recta
RADIO = 3.5              # R: radio de las curvas (sobre la línea central)
ANCHO = 2.4              # ancho del asfalto
ALTO_MURO = 0.15         # muros: más altos que el eje de las ruedas (0,05 m) para que no los trepen
GROSOR_MURO = 0.10
ANCHO_PIANO = 0.14       # "pianos" (kerbs) rojo/blanco al borde de las curvas
PERIMETRO = 2 * LARGO_RECTA + 2 * math.pi * RADIO

# Colores (RGBA de 0 a 1)
C_PASTO = (0.20, 0.42, 0.20, 1)
C_ASFALTO = (0.24, 0.25, 0.27, 1)
C_LINEA = (0.95, 0.95, 0.92, 1)
C_MURO = ((0.85, 0.12, 0.10, 1), (0.95, 0.95, 0.95, 1))    # alterna rojo / blanco
C_MURO_INT = ((0.12, 0.30, 0.75, 1), (0.95, 0.95, 0.95, 1))  # el muro interior en azul / blanco
C_PIANO = ((0.90, 0.10, 0.10, 1), (0.97, 0.97, 0.97, 1))

# Capas en z: todo lo plano se apila unos milímetros para que la cámara no mezcle dos superficies
# a la misma altura (z-fighting: se verían "rayadas"). El piso con colisión tiene su cara de arriba
# en z = 0; lo visual va encima pero tan delgado que las ruedas no lo notan (no tiene colisión).
Z_ASFALTO = 0.002
Z_PIANO = 0.004
Z_LINEA = 0.005


# ---------------------------------------------------------------------------------------------
# Geometría: (s, d) <-> (x, y)
# ---------------------------------------------------------------------------------------------
def envolver(s: float) -> float:
    """Lleva s a [0, P)."""
    return s % PERIMETRO


def envolver_delta(ds: float) -> float:
    """Diferencia de s llevada a (-P/2, P/2]: así cruzar la meta (de 37,9 a 0,1) cuenta +0,2 m y no
    -37,8 m. Es la misma idea que restar ángulos que dan la vuelta en 360 grados."""
    return (ds + PERIMETRO / 2) % PERIMETRO - PERIMETRO / 2


def punto(s: float, d: float = 0.0) -> tuple:
    """(x, y, rumbo) del punto que está a distancia s sobre la línea central, corrido d hacia la
    izquierda. El rumbo es la dirección de avance de la pista en ese punto (radianes).

    Tramos, empezando en la meta (x=0, recta de abajo, y=-R) y en sentido antihorario:
      1) recta de abajo, segunda mitad: x de 0 a L/2, rumbo 0 (hacia +x)
      2) curva derecha, centro (L/2, 0): ángulo de -90 a +90 grados
      3) recta de arriba: x de L/2 a -L/2, rumbo 180 grados
      4) curva izquierda, centro (-L/2, 0): ángulo de 90 a 270 grados
      5) recta de abajo, primera mitad: x de -L/2 a 0 (y otra vez la meta)
    """
    L, R = LARGO_RECTA, RADIO
    s = envolver(s)
    s1, s2, s3, s4 = L / 2, L / 2 + math.pi * R, 1.5 * L + math.pi * R, 1.5 * L + 2 * math.pi * R
    if s < s1:                                   # recta de abajo (después de la meta)
        x, y, rumbo = s, -R, 0.0
    elif s < s2:                                 # curva derecha
        th = (s - s1) / R - math.pi / 2
        x, y, rumbo = L / 2 + R * math.cos(th), R * math.sin(th), th + math.pi / 2
    elif s < s3:                                 # recta de arriba (hacia -x)
        x, y, rumbo = L / 2 - (s - s2), R, math.pi
    elif s < s4:                                 # curva izquierda
        th = (s - s3) / R + math.pi / 2
        x, y, rumbo = -L / 2 + R * math.cos(th), R * math.sin(th), th + math.pi / 2
    else:                                        # recta de abajo (antes de la meta)
        x, y, rumbo = -L / 2 + (s - s4), -R, 0.0
    # La izquierda del rumbo es (-sen, cos): hacia allá se corre d.
    return x - d * math.sin(rumbo), y + d * math.cos(rumbo), rumbo


def proyectar(x: float, y: float) -> tuple:
    """Lo inverso de punto(): el (s, d) del punto de la línea central más cercano a (x, y).

    Es analítico (sin buscar entre puntos): en las rectas basta mirar x; en las curvas, el ángulo
    respecto del centro de la curva da s y la distancia al centro da d (d = R - r: positivo si el
    carro está más adentro que la línea central).
    """
    L, R = LARGO_RECTA, RADIO
    if x > L / 2:                                # zona de la curva derecha
        th = math.atan2(y, x - L / 2)            # en (-90, 90) grados
        return L / 2 + R * (th + math.pi / 2), R - math.hypot(x - L / 2, y)
    if x < -L / 2:                               # zona de la curva izquierda
        th = math.atan2(y, x + L / 2) % (2 * math.pi)   # en (90, 270) grados
        return 1.5 * L + math.pi * R + R * (th - math.pi / 2), R - math.hypot(x + L / 2, y)
    if y < 0:                                    # recta de abajo (va hacia +x: izquierda = +y)
        return envolver(x), y + R
    return L / 2 + math.pi * R + (L / 2 - x), R - y     # recta de arriba (va hacia -x)


def linea_central(paso: float = 0.25) -> list:
    """Puntos [[x, y], ...] de la línea central cada `paso` metros (para el mensaje "pista": así un
    cliente puede hacer pure pursuit sin conocer la forma de la pista de antemano)."""
    n = int(round(PERIMETRO / paso))
    return [[round(v, 3) for v in punto(i * PERIMETRO / n)[:2]] for i in range(n)]


def muestras_borde() -> list:
    """Valores de s donde se parte un borde (muro, asfalto) en tramos rectos: 8 tramos por recta
    (para alternar colores en los muros) y 18 por media curva (10 grados cada uno: con eso el
    polígono ya se ve redondo desde la cámara y el muro no tiene escalones que frenen a un carro)."""
    L, R = LARGO_RECTA, RADIO
    tramos = [(0.0, L / 2, 4), (L / 2, L / 2 + math.pi * R, 18),
              (L / 2 + math.pi * R, 1.5 * L + math.pi * R, 8),
              (1.5 * L + math.pi * R, 1.5 * L + 2 * math.pi * R, 18),
              (1.5 * L + 2 * math.pi * R, PERIMETRO, 4)]
    ss = []
    for a, b, n in tramos:
        ss += [a + (b - a) * k / n for k in range(n)]
    return ss + [PERIMETRO]


def en_curva(s: float) -> bool:
    s = envolver(s)
    L, R = LARGO_RECTA, RADIO
    return L / 2 <= s < L / 2 + math.pi * R or 1.5 * L + math.pi * R <= s < 1.5 * L + 2 * math.pi * R


# ---------------------------------------------------------------------------------------------
# Construcción de la escena
# ---------------------------------------------------------------------------------------------
def caja(medias, pos, rgba=None, yaw=0.0, visual=True, colision=False) -> int:
    """Cuerpo estático (masa 0) en forma de caja. masa 0 = PyBullet no lo mueve nunca: es parte del
    mundo, como el piso. Con colision=False es solo un dibujo (los carros lo atraviesan)."""
    vis = p.createVisualShape(p.GEOM_BOX, halfExtents=medias, rgbaColor=rgba) if visual else -1
    col = p.createCollisionShape(p.GEOM_BOX, halfExtents=medias) if colision else -1
    return p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col, baseVisualShapeIndex=vis,
                             basePosition=pos, baseOrientation=p.getQuaternionFromEuler([0, 0, yaw]))


def _tramos_borde(d: float):
    """Recorre el borde que está corrido d de la línea central y da, por cada tramo, su centro, su
    largo y su rumbo: una caja con esas medidas une dos muestras consecutivas del borde."""
    ss = muestras_borde()
    for k, (a, b) in enumerate(zip(ss, ss[1:])):
        xa, ya, _ = punto(a, d)
        xb, yb, _ = punto(b - 1e-9, d)
        largo = math.hypot(xb - xa, yb - ya)
        yield k, (a + b) / 2, ((xa + xb) / 2, (ya + yb) / 2), largo, math.atan2(yb - ya, xb - xa)


def construir_pista(visual: bool = True, colision: bool = True) -> None:
    """Piso, asfalto, pianos, muros, línea central discontinua y meta a cuadros."""
    # Piso: una caja grande cuya cara de arriba queda en z = 0. Con colisión (en la física) es lo
    # que sostiene a los carros. Se usa caja y no plane.urdf porque plane.urdf trae una textura de
    # cuadrícula que el renderizador por software dibuja lento y que no deja ver el asfalto.
    piso = caja((14, 9, 0.05), (0, 0, -0.05), C_PASTO, visual=visual, colision=colision)
    if colision:
        # Fricción del piso: 1,0 (goma sobre asfalto seco anda por 0,9-1,0). Es el valor por defecto,
        # pero se deja explícito porque de esto depende que el carro no derrape en las curvas.
        p.changeDynamics(piso, -1, lateralFriction=1.0)

    # Muros interior y exterior, partidos en tramos de colores alternados (como las barreras de una
    # pista real). Van justo fuera del asfalto: el borde del muro toca el borde del asfalto.
    for d, colores in ((ANCHO / 2 + GROSOR_MURO / 2, C_MURO_INT), (-(ANCHO / 2 + GROSOR_MURO / 2), C_MURO)):
        for k, _, (cx, cy), largo, rumbo in _tramos_borde(d):
            # +GROSOR_MURO en el largo: en las curvas los tramos se tocan en las esquinas internas
            # pero dejan una ranura en las externas; alargarlos un poco la tapa.
            caja((largo / 2 + GROSOR_MURO / 2, GROSOR_MURO / 2, ALTO_MURO / 2), (cx, cy, ALTO_MURO / 2),
                 colores[k % 2], rumbo, visual=visual, colision=colision)

    if not visual:
        return
    # Asfalto: tramos que cubren todo el ancho (solo dibujo: debajo está el piso con colisión).
    for _, _, (cx, cy), largo, rumbo in _tramos_borde(0.0):
        caja(((largo + 0.6) / 2, ANCHO / 2, Z_ASFALTO / 2), (cx, cy, Z_ASFALTO / 2), C_ASFALTO, rumbo)
    # Pianos solo en las curvas (donde un piloto real los pisa al cortar la curva).
    for d in (ANCHO / 2 - ANCHO_PIANO / 2, -(ANCHO / 2 - ANCHO_PIANO / 2)):
        for k, s, (cx, cy), largo, rumbo in _tramos_borde(d):
            if en_curva(s):
                caja((largo / 2, ANCHO_PIANO / 2, 0.001), (cx, cy, Z_PIANO - 0.001), C_PIANO[k % 2], rumbo)
    # Línea central discontinua: es justo la línea que siguen los autónomos con pure pursuit.
    n = int(PERIMETRO / 1.0)
    for i in range(n):
        s = (i + 0.5) * PERIMETRO / n
        if abs(envolver_delta(s)) < 0.6:
            continue          # no pintar encima de la meta
        x, y, rumbo = punto(s)
        caja((0.20, 0.025, 0.001), (x, y, Z_LINEA - 0.001), C_LINEA, rumbo)
    # Meta: franja a cuadros blancos y negros a lo ancho de la pista, en s = 0 (x = 0).
    filas, lado = 12, ANCHO / 12
    for i in range(filas):
        for j in range(2):
            c = (0.97, 0.97, 0.97, 1) if (i + j) % 2 == 0 else (0.05, 0.05, 0.05, 1)
            caja((lado / 2, lado / 2, 0.001), ((j - 0.5) * lado, -RADIO - ANCHO / 2 + lado * (i + 0.5), Z_LINEA),
                 c)


# ---------------------------------------------------------------------------------------------
# El carro: racecar de pybullet_data
# ---------------------------------------------------------------------------------------------
# Juntas del racecar.urdf (se listaron con p.getJointInfo):
#   0 base_link_joint (fija)        1 chassis_inertia_joint (fija; aquí está la masa: 4 kg)
#   2 left_rear_wheel_joint         3 right_rear_wheel_joint        -> TRACCIÓN (control de velocidad)
#   4 left_steering_hinge_joint     6 right_steering_hinge_joint    -> DIRECCIÓN (control de posición)
#   5 left_front_wheel_joint        7 right_front_wheel_joint       -> ruedas delanteras LIBRES
#   8 hokuyo (lidar), 9-11 cámara ZED (fijas, solo adorno)
RUEDAS_TRACCION = (2, 3)
RUEDAS_LIBRES = (5, 7)
DIRECCION = (4, 6)
JUNTAS_MOVILES = (2, 3, 4, 5, 6, 7)     # las que la cámara necesita copiar para dibujar el carro
RADIO_RUEDA = 0.05
DISTANCIA_EJES = 0.325
GIRO_MAX = 0.5          # rad (~29 grados) de dirección a fondo; el URDF permite 1 rad, pero con más
                        # de ~0,5 las ruedas delanteras empiezan a "arrastrarse" de lado
VEL_MAX = 2.5           # m/s con el acelerador al 100 % (unos 9 km/h: un carro RC 1:10 rápido)
FUERZA_RUEDA = 6.0      # N*m máximos que el motor de cada rueda puede hacer para llegar a la velocidad

_URDF = {}


def urdf_carro(liviano: bool = False) -> str:
    """Ruta a una copia modificada del racecar.urdf de pybullet_data (se escribe en /tmp).

    Cambios, siempre:
      - Una caja de COLISIÓN en el chasis. El URDF original solo tiene colisión en las ruedas y en
        el lidar: el chasis es solo un dibujo, así que dos carros podían quedar "metidos" uno dentro
        del otro al chocar. La caja mide como el chasis (0,45 x 0,18 x 0,08 m) y empieza 5 cm sobre
        el piso (no roza el asfalto).
      - Las mallas con ruta absoluta (la copia vive en otra carpeta).
    Con liviano=True (solo para el proceso de la cámara, que no simula):
      - Las ruedas se dibujan como cilindros (su misma forma de colisión) y se quitan las mallas de
        las bisagras de dirección y del lidar. Esas mallas suman ~11 000 triángulos por carro y el
        renderizador por software transforma TODOS los triángulos de la escena en cada foto, aunque
        el carro quede fuera del recorte: con 6 carros eran ~12 ms fijos por llamada. Desde arriba
        (un carro mide ~25 píxeles) y en la cámara de persecución la diferencia no se nota.
    """
    import copy
    import xml.etree.ElementTree as ET

    if liviano in _URDF and os.path.exists(_URDF[liviano]):
        return _URDF[liviano]
    carpeta = os.path.join(pybullet_data.getDataPath(), "racecar").replace("\\", "/")
    arbol = ET.parse(os.path.join(carpeta, "racecar.urdf"))
    robot = arbol.getroot()
    for malla in robot.iter("mesh"):
        malla.set("filename", f"{carpeta}/{malla.get('filename')}")
    for link in robot.findall("link"):
        nombre = link.get("name")
        if nombre == "chassis":
            col = ET.SubElement(link, "collision")
            ET.SubElement(col, "origin", rpy="0 0 0", xyz="0.16 0 0.04")
            ET.SubElement(ET.SubElement(col, "geometry"), "box", size="0.45 0.18 0.08")
        if not liviano:
            continue
        vis = link.find("visual")
        if vis is None:
            continue
        if nombre.endswith("_wheel"):
            col = link.find("collision")
            link.remove(vis)
            vis = ET.SubElement(link, "visual")
            vis.append(copy.deepcopy(col.find("origin")))
            vis.append(copy.deepcopy(col.find("geometry")))
            mat = ET.SubElement(vis, "material", name="goma")
            ET.SubElement(mat, "color", rgba="0.07 0.07 0.08 1")
        elif nombre.endswith("_steering_hinge"):
            link.remove(vis)
        elif nombre == "laser":
            geo = vis.find("geometry")
            for hijo in list(geo):
                geo.remove(hijo)
            ET.SubElement(geo, "cylinder", radius="0.025", length="0.04")
    fd, ruta = tempfile.mkstemp(prefix="racecar_liviano_" if liviano else "racecar_", suffix=".urdf")
    os.close(fd)
    arbol.write(ruta, encoding="utf-8", xml_declaration=True)
    _URDF[liviano] = ruta
    return ruta


def cargar_carro(x: float, y: float, rumbo: float, color, liviano: bool = False, cli: int = 0) -> int:
    """Carga un racecar parado en (x, y) mirando hacia `rumbo` y le pinta el chasis.
    cli = en qué conexión de PyBullet (el proceso de la cámara usa dos)."""
    cid = p.loadURDF(urdf_carro(liviano), [x, y, 0.0], p.getQuaternionFromEuler([0, 0, rumbo]),
                     physicsClientId=cli)
    # El chasis es el link 0 ("chassis", la malla azul). changeVisualShape cambia el color solo en
    # la imagen; no toca la física.
    p.changeVisualShape(cid, 0, rgbaColor=list(color) + [1] if len(color) == 3 else list(color),
                        physicsClientId=cli)
    return cid


# Adornos por estilo: piezas visuales que se dibujan pegadas al chasis, en el sistema del chasis
# (x hacia adelante, y a la izquierda, z arriba; el origen está a la altura del eje de las ruedas y
# la malla del chasis va de x=-0,04 a 0,365 y de z=-0,03 a 0,03). Cada pieza:
#   (semiejes, posición relativa, color) ; color "carro" = el color del jugador.
NEGRO = (0.06, 0.06, 0.07, 1)
BLANCO = (0.96, 0.96, 0.96, 1)
AMARILLO = (1.0, 0.82, 0.10, 1)
ADORNOS = {
    # clásico: carrocería tipo sedán (cabina baja) con una franja blanca de punta a punta.
    "clasico": [((0.10, 0.075, 0.025), (0.13, 0, 0.055), "carro"),
                ((0.20, 0.022, 0.004), (0.16, 0, 0.082), BLANCO)],
    # deportivo: cabina más baja y larga, dos franjas de carreras y un ALERÓN trasero sobre dos postes.
    "deportivo": [((0.13, 0.08, 0.018), (0.15, 0, 0.048), "carro"),
                  ((0.20, 0.012, 0.003), (0.16, 0.035, 0.068), BLANCO),
                  ((0.20, 0.012, 0.003), (0.16, -0.035, 0.068), BLANCO),
                  ((0.035, 0.13, 0.006), (-0.035, 0, 0.115), NEGRO),
                  ((0.008, 0.008, 0.03), (-0.03, 0.07, 0.08), NEGRO),
                  ((0.008, 0.008, 0.03), (-0.03, -0.07, 0.08), NEGRO)],
    # rally: cabina ALTA (como un todoterreno), parrilla en el techo y barra de 4 faros amarillos.
    "rally": [((0.11, 0.085, 0.045), (0.12, 0, 0.075), "carro"),
              ((0.08, 0.07, 0.006), (0.11, 0, 0.126), NEGRO),
              ((0.012, 0.018, 0.012), (0.21, 0.06, 0.13), AMARILLO),
              ((0.012, 0.018, 0.012), (0.21, 0.02, 0.13), AMARILLO),
              ((0.012, 0.018, 0.012), (0.21, -0.02, 0.13), AMARILLO),
              ((0.012, 0.018, 0.012), (0.21, -0.06, 0.13), AMARILLO)],
    # autónomos: cabina chata con un "sensor" negro en el techo (el lidar del RACECAR del MIT).
    "auto": [((0.10, 0.075, 0.02), (0.13, 0, 0.05), "carro"),
             ((0.03, 0.03, 0.02), (0.13, 0, 0.09), NEGRO)],
}
ESTILOS = ("clasico", "deportivo", "rally")
