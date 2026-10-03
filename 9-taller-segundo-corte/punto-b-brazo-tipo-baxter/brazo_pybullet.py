"""Punto b) del taller: consola de mandos con el ESP32 para mover el robot
Baxter (el modelo 3D real, toms_baxter.urdf) con movilidad real de los dos
brazos y posicionamiento, y que pueda coger y mover un objeto.

Base: github.com/erwincoumans/pybullet_robots/blob/master/baxter_ik_demo.py
(el ejemplo que compartio el profesor). De ese script se conserva la idea
central: cargar toms_baxter.urdf con la base fija y mover el efector final
con p.calculateInverseKinematics, mapeando la respuesta por qIndex. Lo que
se cambia (y por que) esta comentado en cada funcion.

Los modelos 3D NO vienen en pybullet_data: los baja una sola vez
../descargar_modelos.py a la carpeta ../modelos/ (que git ignora).

Teclado (el mismo firmware de todo el taller, ../esp32_teclado.py, que
manda "TECLA:x" cada 50 ms, o "TECLA:-" si no hay nada pulsado):

    8/2 = Y+/Y- (jog)        4/6 = X-/X+ (jog)        9/7 = Z+/Z- (jog)
    5   = home del brazo activo
    A   = abrir la pinza (y soltar el cubo si esa pinza lo tenia)
    C   = cerrar la pinza (y agarrar el cubo si esta entre los dedos)
    D   = demo: coger el cubo del ORIGEN y dejarlo en el DESTINO
    B   = demo: recorrer los 3 ejes con el brazo activo
    0   = reponer el cubo en el origen
    *   = cambiar de brazo activo (izquierdo <-> derecho)
    (1, 3, # no se usan)

Sin ESP32 conectado, la ventana de PyBullet trae un boton por tecla.

Funciones publicas (para importar el modulo, por ejemplo para sacar
capturas con getCameraImage en modo DIRECT, sin ventana):

    estado = crear_mundo(p.DIRECT)        # conecta, arma la escena, Baxter en home
    mover_a(estado, "izquierdo", (x, y, z), pasos=240)
                                          # la pinza va EN LINEA RECTA a (x, y, z)
                                          # (IK + motores), simulando `pasos`
                                          # pasos; devuelve el error final (m)
    mover_pinza(estado, "izquierdo", abierta=True/False)
    intentar_agarrar(estado, "izquierdo"); soltar(estado)
    ejecutar_demo(estado)                 # D completa con el brazo activo; deja el
                                          # cubo en el destino y el brazo encima
    ejecutar_demo_recorrido(estado)       # B
    procesar_linea(estado, "TECLA:8")     # lo mismo que hace una linea del ESP32
    avanzar(estado, pasos)                # solo simular

`estado.activo` es el nombre del brazo activo ("izquierdo" o "derecho");
`estado.cubo` el id del cubo; `estado.brazos[nombre]` trae los indices.
"""

import math
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pybullet as p
import pybullet_data

PUERTO_SERIAL = "COM7"
BAUDIOS = 115200

# Carpeta donde descargar_modelos.py dejo las mallas de Baxter.
CARPETA_MODELOS = Path(__file__).resolve().parent.parent / "modelos"
URDF_BAXTER = CARPETA_MODELOS / "baxter_common" / "baxter_description" / "urdf" / "toms_baxter.urdf"

PASOS_POR_SEGUNDO = 240   # PyBullet simula por defecto a 240 Hz

# ----------------------------------------------------------------------
# Geometria de la escena (metros, en el sistema de Baxter: origen en el
# torso, +X hacia el frente del robot, +Y hacia su IZQUIERDA, +Z arriba).
# ----------------------------------------------------------------------
# El pedestal de Baxter llega hasta z = -0.926 (medido con getAABB del
# link "pedestal"): ahi va el piso.
Z_PISO = -0.926
# Mesa: un bloque fijo delante del robot, de x = 0.47 a x = 1.0. Empieza
# por delante del pedestal (que llega hasta x = 0.42), asi el brazo nunca
# tiene que pasar por encima del pedestal para trabajar sobre ella. La
# altura (20 cm por debajo del origen del torso) es la de una mesa de
# trabajo frente a Baxter: le llega mas o menos a la cintura.
Z_MESA = -0.20
MESA_CENTRO_XY = (0.735, 0.0)
MESA_MEDIAS = (0.265, 0.50)   # medio largo en X y medio ancho en Y

# cube_small.urdf mide 5 cm, pero la pinza paralela de Baxter (dedos
# prismaticos de 0 a 2 cm cada uno) solo abre 5.6 cm entre las puntas
# (medido con getClosestPoints entre los links de las puntas): con 5 cm
# quedaria 3 mm de holgura por lado y cualquier error de la IK lo
# empujaria. Se carga a escala 0.7 (3.5 cm): entra holgado con la pinza
# abierta y la pinza cerrada (1.6 cm entre puntas) lo aprieta de verdad.
ESCALA_CUBO = 0.7
LADO_CUBO = 0.05 * ESCALA_CUBO
Z_CUBO = Z_MESA + LADO_CUBO / 2          # centro del cubo apoyado en la mesa

# Origen y destino del cubo: a los dos lados del centro de la mesa, en
# una zona que alcanzan LOS DOS brazos (cada brazo puede cruzar un poco
# hacia el lado del otro). Se eligieron probando la IK en una grilla de
# puntos con la pinza vertical: hasta x = 0.70 y cruzando hasta 15-20 cm
# al lado del otro brazo, la IK queda a menos de 1 cm; mas lejos (x = 0.8)
# la pinza vertical ya no llega (errores de 5 a 12 cm).
POS_ORIGEN = (0.65, 0.15)    # lado izquierdo de Baxter (+Y)
POS_DESTINO = (0.65, -0.15)  # lado derecho de Baxter (-Y)

# El link "endpoint" de la pinza (el que usa la IK) queda a la altura de
# las puntas de los dedos: las cajas de colision de las puntas van de
# 3.5 mm por debajo a 3.35 cm por encima de el (medido en el marco de la
# pinza). Bajandolo 8 mm por debajo del centro del cubo, las puntas
# abrazan el cubo por los costados sin tocar la mesa (quedan ~1 cm arriba).
BAJADA_AGARRE = 0.008
Z_AGARRE = Z_CUBO - BAJADA_AGARRE
Z_VIAJE = Z_MESA + 0.20    # altura para trasladar el cubo sin arrastrarlo

# Home de cada brazo: abiertos a los costados, por encima de la mesa.
HOME = {"izquierdo": (0.60, 0.40, 0.05), "derecho": (0.60, -0.40, 0.05)}

# Caja de trabajo del jog, POR BRAZO. Cada brazo puede cruzar 20 cm al
# lado del otro (lo justo para alcanzar origen y destino), no mas: mas
# alla la IK ya no llega con la pinza vertical y el brazo quedaria
# estirado "persiguiendo" un objetivo imposible (y al volver, el objetivo
# tardaria lo mismo en regresar: se siente como que la tecla no responde).
# El piso de la caja es la altura de agarre (la pinza no puede bajar a
# atravesar la mesa) y X empieza en 0.50, por delante del pedestal.
LIMITES_JOG = {
    "izquierdo": ((0.50, 0.72), (-0.20, 0.50), (Z_AGARRE, 0.20)),
    "derecho": ((0.50, 0.72), (-0.50, 0.20), (Z_AGARRE, 0.20)),
}
PASO_JOG = 0.015   # metros por linea "TECLA:x" (20 lineas/s sostenida = 30 cm/s) o por click

# Motores: fuerza maxima y velocidad maxima de cada junta. La fuerza es
# la del propio URDF (campo effort: 50 N*m hombro/codo, 15 N*m muneca)
# con margen, porque varios links de toms_baxter.urdf no traen inercia y
# PyBullet les pone 1 kg a cada uno: el brazo simulado pesa mas que el
# real. La velocidad maxima es la que hace que el movimiento sea SUAVE
# aunque el objetivo salte de golpe (el motor no "teletransporta").
FUERZA_HOMBRO_CODO = 120.0
FUERZA_MUNECA = 40.0
VELOCIDAD_MAX = 1.2   # rad/s
FUERZA_DEDOS = 20.0   # N (effort del URDF para los dedos)

# Distancia maxima entre el endpoint de la pinza y el centro del cubo
# para considerar que el cubo esta ENTRE los dedos al cerrar.
UMBRAL_AGARRE = 0.04

# Pose "de descanso" para el espacio nulo de la IK (ver resolver_ik):
# hombro un poco hacia abajo, codo doblado, muneca doblada. Con 7 juntas
# hay infinitas soluciones para un mismo punto; la IK elige la mas
# parecida a esta, y asi el brazo no se retuerce. El giro del hombro (s0)
# NO es fijo: se calcula para cada objetivo (ver s0_hacia), porque con un
# s0 fijo la IK fallaba por 5-20 cm al cruzar al lado del otro brazo.
POSE_DESCANSO = {"s0": 0.0, "s1": -0.6, "e0": 0.0, "e1": 1.6, "w0": 0.0, "w1": 0.6, "w2": 0.0}
ITERACIONES_IK = 10      # vueltas de afuera (ver resolver_ik)
ITERACIONES_INTERNAS = 20   # maxNumIterations de cada llamada

# Pinza mirando hacia abajo: el eje Z local del endpoint es la direccion
# en la que apunta la pinza (medido: con todas las juntas en 0 apunta
# horizontal, hacia afuera). Girar pi alrededor de X lo deja apuntando a
# -Z del mundo, y los dedos (que se mueven sobre el Y local) cierran a lo
# largo del eje Y del mundo, alineados con las caras del cubo.
# El segundo pi (giro alrededor de Z) no cambia nada para agarrar (la
# pinza es simetrica), pero si para la IK: sin el, la muneca (w2) tenia
# que quedar en -3.06 rad, justo en su limite, y al cruzar al lado del
# otro brazo la IK fallaba por 7 cm; con el, w2 queda cerca de 0, en el
# medio de su rango.
ORIENTACION_ABAJO = p.getQuaternionFromEuler([math.pi, 0, math.pi])

TECLAS_JOG = {"8", "2", "4", "6", "9", "7"}

BOTON_A_TECLA = {
    "Adelante (Y+) [8]": "8",
    "Atras (Y-) [2]": "2",
    "Izquierda (X-) [4]": "4",
    "Derecha (X+) [6]": "6",
    "Subir (Z+) [9]": "9",
    "Bajar (Z-) [7]": "7",
    "Home [5]": "5",
    "Abrir pinza [A]": "A",
    "Cerrar pinza [C]": "C",
    "Demo: coger y mover [D]": "D",
    "Demo: recorrer los 3 ejes [B]": "B",
    "Reponer cubo [0]": "0",
    "Cambiar de brazo [*]": "*",
}


# ======================================================================
# Construccion del mundo
# ======================================================================
def indice_por_nombre(robot):
    """Diccionario nombre de junta -> indice. Los indices de Baxter (12,
    48, 49...) no se escriben a mano en ningun lado: si el URDF cambia,
    el script sigue funcionando porque todo se busca por NOMBRE."""
    return {p.getJointInfo(robot, i)[1].decode(): i for i in range(p.getNumJoints(robot))}


def _datos_brazo(robot, nombres, lado):
    """Junta los indices de un brazo. `lado` es el prefijo del URDF
    ("left"/"right"); los dedos se llaman l_gripper_... / r_gripper_..."""
    letra = lado[0]
    juntas = [nombres[f"{lado}_{k}"] for k in ("s0", "s1", "e0", "e1", "w0", "w1", "w2")]
    dedo_l = nombres[f"{letra}_gripper_l_finger_joint"]   # limites 0 .. 0.02
    dedo_r = nombres[f"{letra}_gripper_r_finger_joint"]   # limites -0.02 .. 0
    return SimpleNamespace(
        juntas=juntas,
        efector=nombres[f"{lado}_endpoint"],
        # (indice, posicion abierta) de cada dedo: se leen los limites
        # del URDF para saber hacia que lado abre cada uno.
        dedos=[(dedo_l, p.getJointInfo(robot, dedo_l)[9]), (dedo_r, p.getJointInfo(robot, dedo_r)[8])],
    )


def crear_mundo(modo=p.GUI):
    """Conecta PyBullet en `modo` (p.GUI o p.DIRECT), arma la escena y
    deja a Baxter en su pose inicial. Devuelve el `estado` (un
    SimpleNamespace con todos los ids, indices y variables del control).
    Si faltan los modelos, avisa y termina con codigo 1."""
    if not URDF_BAXTER.exists():
        print("Faltan los modelos: corra `entorno\\Scripts\\python descargar_modelos.py` en la carpeta del taller")
        sys.exit(1)

    cliente = p.connect(modo)
    if modo == p.GUI:
        # sin los paneles laterales de PyBullet (sombras, rgb, depth...):
        # solo la escena y los botones
        p.configureDebugVisualizer(p.COV_ENABLE_RGB_BUFFER_PREVIEW, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_DEPTH_BUFFER_PREVIEW, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SEGMENTATION_MARK_PREVIEW, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0)   # no dibujar mientras carga (va mas rapido)
    p.setGravity(0, 0, -10)

    # PyBullet guarda UNA sola ruta de busqueda adicional (cada llamada
    # pisa la anterior). Las mallas de Baxter se nombran en el URDF como
    # "package://baxter_description/meshes/...": PyBullet quita el
    # "package://" y busca el resto en esa ruta, asi que la ruta tiene
    # que ser modelos/baxter_common. Por eso el piso y el cubo (de
    # pybullet_data) se cargan con su ruta ABSOLUTA, sin search path.
    p.setAdditionalSearchPath(str(CARPETA_MODELOS / "baxter_common"))
    datos = pybullet_data.getDataPath()
    p.loadURDF(os.path.join(datos, "plane.urdf"), [0, 0, Z_PISO], useFixedBase=True)

    # Baxter con la base fija (igual que baxter_ik_demo.py): es un robot
    # de pedestal, no se tiene que caer ni deslizar. Se deja en el origen
    # mirando a +X (el demo del profesor lo gira y lo corre; aca no hace
    # falta y las coordenadas quedan mas faciles de leer). PyBullet avisa
    # "No inertial data" por varios links: con la base fija no importa.
    robot = p.loadURDF(str(URDF_BAXTER), useFixedBase=True)
    nombres = indice_por_nombre(robot)

    # Juntas MOVILES en el orden de qIndex (jointInfo[3]). calculateInverse
    # Kinematics devuelve UN valor por cada junta movil en ese orden
    # (incluye head_pan y los 4 dedos, no solo los 7 del brazo), asi que
    # para saber que valor va en que junta hay que mapear por qIndex, como
    # hace el demo (alli con "qIndex - 7"; aca con la posicion en la lista).
    moviles = sorted((i for i in range(p.getNumJoints(robot)) if p.getJointInfo(robot, i)[3] > -1),
                     key=lambda i: p.getJointInfo(robot, i)[3])
    # Limites REALES de cada junta, leidos del URDF (el demo usa -2..2
    # para todas, que deja afuera parte del rango del codo y la muneca y
    # permite posturas imposibles en el hombro s1, que va de -2.15 a 1.05).
    limite_inf = [p.getJointInfo(robot, i)[8] for i in moviles]
    limite_sup = [p.getJointInfo(robot, i)[9] for i in moviles]
    rangos = [s - i for i, s in zip(limite_inf, limite_sup)]

    brazos = {"izquierdo": _datos_brazo(robot, nombres, "left"),
              "derecho": _datos_brazo(robot, nombres, "right")}
    for nombre, brazo in brazos.items():
        brazo.nombre = nombre
        brazo.descanso = {j: POSE_DESCANSO[k] for j, k in zip(brazo.juntas, POSE_DESCANSO)}
        # Donde esta el hombro y hacia donde apunta el brazo con s0 = 0:
        # el soporte del brazo (link "left_arm_mount"/"right_arm_mount")
        # esta girado +-45 grados respecto del frente del robot.
        lado = "left" if nombre == "izquierdo" else "right"
        soporte = [i for i in range(p.getNumJoints(robot))
                   if p.getJointInfo(robot, i)[12].decode() == f"{lado}_arm_mount"][0]
        pos_soporte, orn_soporte = p.getLinkState(robot, soporte)[4:6]
        brazo.hombro_xy = pos_soporte[:2]
        brazo.giro_soporte = p.getEulerFromQuaternion(orn_soporte)[2]

    # Mesa: un bloque fijo desde el piso hasta Z_MESA.
    alto = (Z_MESA - Z_PISO) / 2
    medias = [MESA_MEDIAS[0], MESA_MEDIAS[1], alto]
    mesa = p.createMultiBody(
        baseMass=0,
        baseCollisionShapeIndex=p.createCollisionShape(p.GEOM_BOX, halfExtents=medias),
        baseVisualShapeIndex=p.createVisualShape(p.GEOM_BOX, halfExtents=medias, rgbaColor=[0.55, 0.42, 0.30, 1]),
        basePosition=[MESA_CENTRO_XY[0], MESA_CENTRO_XY[1], Z_MESA - alto])

    # Marcas de origen (azul) y destino (verde): cuadrados finos SOLO
    # visuales (sin colision), apoyados sobre la mesa. Se ven tambien en
    # getCameraImage, a diferencia de los addUserDebugText.
    for (x, y), color in ((POS_ORIGEN, [0.2, 0.5, 1.0, 1]), (POS_DESTINO, [0.2, 0.85, 0.3, 1])):
        p.createMultiBody(baseMass=0,
                          baseVisualShapeIndex=p.createVisualShape(p.GEOM_BOX, halfExtents=[0.05, 0.05, 0.001],
                                                                   rgbaColor=color),
                          basePosition=[x, y, Z_MESA + 0.001])
    p.addUserDebugText("ORIGEN", [POS_ORIGEN[0], POS_ORIGEN[1], Z_MESA + 0.08], textColorRGB=[0.3, 0.6, 1], textSize=1.2)
    p.addUserDebugText("DESTINO", [POS_DESTINO[0], POS_DESTINO[1], Z_MESA + 0.08], textColorRGB=[0.3, 0.9, 0.4], textSize=1.2)

    cubo = p.loadURDF(os.path.join(datos, "cube_small.urdf"), [POS_ORIGEN[0], POS_ORIGEN[1], Z_CUBO],
                      globalScaling=ESCALA_CUBO)
    # friccion alta en el cubo para que los dedos lo sujeten mejor
    p.changeDynamics(cubo, -1, lateralFriction=1.0)

    estado = SimpleNamespace(
        cliente=cliente, tiempo_real=(modo == p.GUI), robot=robot, nombres=nombres, moviles=moviles,
        limite_inf=limite_inf, limite_sup=limite_sup, rangos=rangos, brazos=brazos, mesa=mesa, cubo=cubo,
        activo="izquierdo", objetivo={}, agarre=None, tecla_anterior="-", ser=None,
        ultima_linea="", ultima_tecla="-", id_texto=None, botones={}, demo_en_curso=False)

    # Pose inicial: aca SI se usa resetJointState (una sola vez, antes de
    # simular): se resuelve la IK hacia el home de cada brazo y se coloca
    # el robot ahi directamente, para no arrancar con los brazos estirados
    # a los costados (la pose con todas las juntas en 0).
    for j in moviles:
        p.resetJointState(robot, j, 0.0)
    for nombre, brazo in brazos.items():
        for j, v in brazo.descanso.items():
            p.resetJointState(robot, j, v)
        for _ in range(5):   # varias pasadas: cada una arranca desde la anterior
            angulos = resolver_ik(estado, nombre, HOME[nombre])
            for j, v in angulos.items():
                p.resetJointState(robot, j, v)
        for indice, abierta in brazo.dedos:
            p.resetJointState(robot, indice, abierta)
    # Motores en esa misma pose (sin esto, los brazos caerian por gravedad).
    p.setJointMotorControl2(robot, nombres["head_pan"], p.POSITION_CONTROL, targetPosition=0, force=50)
    for nombre in brazos:
        fijar_objetivo(estado, nombre, HOME[nombre])
        mover_pinza(estado, nombre, abierta=True)

    if modo == p.GUI:
        p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 1)
        # camara en diagonal por delante de Baxter, un poco desde arriba
        p.resetDebugVisualizerCamera(cameraDistance=2.2, cameraYaw=120, cameraPitch=-28,
                                     cameraTargetPosition=[0.45, 0, -0.05])
    estado.id_texto = p.addUserDebugText("", [0.2, 0, 0.95], textColorRGB=[1, 1, 0.4], textSize=1.3)
    actualizar_texto(estado)
    avanzar(estado, 60)   # que el cubo se asiente en la mesa
    return estado


# ======================================================================
# Movimiento: IK, motores y pinza
# ======================================================================
def resolver_ik(estado, nombre_brazo, xyz):
    """Angulos de las 7 juntas del brazo para llevar su endpoint a `xyz`
    con la pinza mirando hacia abajo. Devuelve {indice_junta: angulo}.

    Diferencias con accurateIK() del demo del profesor:
    - el demo itera llamando a resetJointState (teletransporta el robot
      en cada iteracion para medir el error): eso rompe la fisica si se
      hace en el bucle. Aca se usa maxNumIterations/residualThreshold,
      que hacen esas mismas iteraciones DENTRO de PyBullet, sobre una
      copia interna del robot, sin tocar la simulacion;
    - se pasan los limites reales de cada junta y una pose de descanso
      (restPoses): eso activa el "espacio nulo" (null space) de la IK,
      que entre las infinitas soluciones elige la mas parecida a esa pose;
    - para las juntas que NO son de este brazo, la pose de descanso es su
      posicion actual: asi la IK no "quiere" mover el otro brazo (y de
      todos modos solo se aplican las 7 juntas del brazo pedido)."""
    robot = estado.robot
    brazo = estado.brazos[nombre_brazo]
    actuales = [p.getJointState(robot, j)[0] for j in estado.moviles]
    descanso_brazo = dict(brazo.descanso)
    descanso_brazo[brazo.juntas[0]] = s0_hacia(estado, nombre_brazo, xyz)
    descanso = [descanso_brazo.get(j, actual) for j, actual in zip(estado.moviles, actuales)]

    # Iteraciones "a lo accurateIK" pero sin tocar el robot: cada vuelta
    # arranca la IK desde la solucion anterior (currentPositions) en vez
    # de desde la pose real. Con una sola llamada, lejos de la pose actual
    # la IK se queda a varios cm; con 10 vueltas converge (medido).
    posiciones = list(actuales)
    for _ in range(ITERACIONES_IK):
        resultado = p.calculateInverseKinematics(
            robot, brazo.efector, xyz, ORIENTACION_ABAJO,
            lowerLimits=estado.limite_inf, upperLimits=estado.limite_sup,
            jointRanges=estado.rangos, restPoses=descanso, currentPositions=posiciones,
            maxNumIterations=ITERACIONES_INTERNAS, residualThreshold=1e-4)
        # resultado[k] es el angulo de la k-esima junta movil (orden
        # qIndex). Solo se actualizan las 7 juntas de este brazo: el resto
        # (cabeza, el otro brazo, los dedos) queda donde esta.
        cambio = 0.0
        for k, j in enumerate(estado.moviles):
            if j in brazo.juntas:
                cambio = max(cambio, abs(resultado[k] - posiciones[k]))
                posiciones[k] = resultado[k]
        if cambio < 1e-3:   # ya no cambia: convergio (en el jog pasa en 1-4 vueltas, medido)
            break
    return {j: posiciones[estado.moviles.index(j)] for j in brazo.juntas}


def s0_hacia(estado, nombre_brazo, xyz):
    """Angulo del hombro (s0) que apunta el brazo hacia el objetivo, visto
    desde arriba: el angulo de la recta hombro -> objetivo menos el giro
    del soporte del brazo (+-45 grados). Se usa como pose de descanso del
    hombro: la IK sigue libre de elegir otro, pero arranca 'mirando' al
    objetivo, sobre todo cuando cruza al lado del otro brazo."""
    brazo = estado.brazos[nombre_brazo]
    angulo = math.atan2(xyz[1] - brazo.hombro_xy[1], xyz[0] - brazo.hombro_xy[0]) - brazo.giro_soporte
    k = estado.moviles.index(brazo.juntas[0])
    return limitar(angulo, estado.limite_inf[k], estado.limite_sup[k])


def fijar_objetivo(estado, nombre_brazo, xyz):
    """Resuelve la IK hacia `xyz` y le manda a cada motor del brazo su
    angulo. NO simula: los motores llevan el brazo hacia ahi en los
    siguientes stepSimulation(). POSITION_CONTROL es un motor con fuerza
    y velocidad maximas, no un teletransporte: el brazo empuja contra la
    gravedad y contra lo que toque (mesa, cubo), con fisica real."""
    estado.objetivo[nombre_brazo] = tuple(xyz)
    brazo = estado.brazos[nombre_brazo]
    for k, (junta, angulo) in enumerate(resolver_ik(estado, nombre_brazo, xyz).items()):
        fuerza = FUERZA_HOMBRO_CODO if k < 4 else FUERZA_MUNECA   # s0 s1 e0 e1 | w0 w1 w2
        p.setJointMotorControl2(estado.robot, junta, p.POSITION_CONTROL, targetPosition=angulo,
                                force=fuerza, maxVelocity=VELOCIDAD_MAX)


def mover_pinza(estado, nombre_brazo, abierta):
    """Abre o cierra los dos dedos prismaticos de verdad (motor de
    posicion con la fuerza del URDF), sin tocar el resto del brazo."""
    for indice, posicion_abierta in estado.brazos[nombre_brazo].dedos:
        p.setJointMotorControl2(estado.robot, indice, p.POSITION_CONTROL,
                                targetPosition=posicion_abierta if abierta else 0.0, force=FUERZA_DEDOS)


def avanzar(estado, pasos):
    """Simula `pasos` pasos de fisica. En la ventana (GUI) duerme 1/240 s
    por paso para verlo a velocidad real; en DIRECT corre a toda maquina."""
    for _ in range(pasos):
        p.stepSimulation()
        if estado.tiempo_real:
            time.sleep(1 / PASOS_POR_SEGUNDO)


def posicion_efector(estado, nombre_brazo):
    return p.getLinkState(estado.robot, estado.brazos[nombre_brazo].efector, computeForwardKinematics=True)[4]


def mover_a(estado, nombre_brazo, xyz, pasos=PASOS_POR_SEGUNDO):
    """Lleva el endpoint del brazo a `xyz` EN LINEA RECTA y simula `pasos`
    pasos en total. Devuelve el error final en metros.

    Por que en linea recta: si se le da a los motores directamente el
    angulo final, cada junta gira a su velocidad maxima por su cuenta y
    la pinza describe una CURVA, no una recta. Medido: al subir despues
    de soltar el cubo, la pinza se corria 3 cm de lado todavia abajo,
    golpeaba el cubo y lo giraba 57 grados. Por eso el tramo se parte en
    pedacitos de 1 cm (IK para cada uno, igual que el jog con el
    teclado), repartidos en el 70 % de los pasos; el 30 % restante es
    para que el brazo termine de asentarse en el punto final."""
    inicio = estado.objetivo.get(nombre_brazo, posicion_efector(estado, nombre_brazo))
    tramos = max(1, math.ceil(math.dist(inicio, xyz) / 0.01))
    pasos_tramo = max(1, int(pasos * 0.7) // tramos)
    for k in range(1, tramos + 1):
        intermedio = [a + (b - a) * k / tramos for a, b in zip(inicio, xyz)]
        fijar_objetivo(estado, nombre_brazo, intermedio)
        avanzar(estado, pasos_tramo)
    avanzar(estado, max(0, pasos - pasos_tramo * tramos))
    return math.dist(posicion_efector(estado, nombre_brazo), xyz)


# ======================================================================
# Agarre con constraint
# ======================================================================
def intentar_agarrar(estado, nombre_brazo):
    """Si el cubo esta entre los dedos, lo "suelda" a la pinza con un
    constraint JOINT_FIXED (ver README: los dedos de verdad tambien se
    cierran, pero el contacto de dos dedos chicos contra un cubo liviano
    es inestable en la simulacion y el cubo se resbala al acelerar).

    La transformacion relativa entre pinza y cubo se mide en el instante
    del agarre (invertTransform + multiplyTransforms), en vez de suponer
    un offset fijo: asi el cubo queda exactamente como estaba respecto a
    la pinza y no "salta" al pegarse. Devuelve True si agarro."""
    if estado.agarre is not None:
        return False
    efector = estado.brazos[nombre_brazo].efector
    pos_ef, orn_ef = p.getLinkState(estado.robot, efector, computeForwardKinematics=True)[4:6]
    pos_cubo, orn_cubo = p.getBasePositionAndOrientation(estado.cubo)
    if math.dist(pos_ef, pos_cubo) > UMBRAL_AGARRE:
        return False
    inv_pos, inv_orn = p.invertTransform(pos_ef, orn_ef)
    pos_rel, orn_rel = p.multiplyTransforms(inv_pos, inv_orn, pos_cubo, orn_cubo)
    # OJO: el marco del link en createConstraint es el del centro de masa
    # del link (getLinkState[0:2]) y no el del link (getLinkState[4:6]);
    # el endpoint no tiene inercia propia, asi que coinciden. Se usa el
    # mismo marco (4:6) que para medir, por claridad.
    restriccion = p.createConstraint(
        parentBodyUniqueId=estado.robot, parentLinkIndex=efector,
        childBodyUniqueId=estado.cubo, childLinkIndex=-1,
        jointType=p.JOINT_FIXED, jointAxis=[0, 0, 0],
        parentFramePosition=pos_rel, parentFrameOrientation=orn_rel,
        childFramePosition=[0, 0, 0])
    estado.agarre = (restriccion, nombre_brazo)
    return True


def soltar(estado, nombre_brazo=None):
    """Borra el constraint (el cubo vuelve a quedar suelto, con gravedad).
    Con `nombre_brazo`, solo suelta si es ESE brazo el que lo tiene."""
    if estado.agarre is not None and nombre_brazo in (None, estado.agarre[1]):
        p.removeConstraint(estado.agarre[0])
        estado.agarre = None


def abrir_y_soltar(estado, nombre_brazo):
    """Abre los dedos y DESPUES borra el constraint. En ese orden a
    proposito: con la pinza cerrada los dedos estan apretando el cubo (se
    quedan en ~0.009 de 0.02, contra sus caras); si se borra el constraint
    con los dedos todavia apretando, el motor de fisica resuelve de golpe
    esa interpenetracion y el cubo sale despedido (medido: caia 2.7 cm
    corrido del destino). Abriendo primero, cae derecho (0.2 cm)."""
    mover_pinza(estado, nombre_brazo, abierta=True)
    if estado.agarre is not None and estado.agarre[1] == nombre_brazo:
        avanzar(estado, 30)   # 1/8 s: los dedos ya se separaron del cubo
    soltar(estado, nombre_brazo)


def reponer_cubo(estado):
    """Suelta el cubo y lo vuelve a poner en el origen. Se mueve el MISMO
    cuerpo (resetBasePositionAndOrientation) en vez de borrarlo y crear
    otro: PyBullet reutiliza los ids de cuerpos borrados y es mas facil
    equivocarse con ids viejos."""
    soltar(estado)
    p.resetBasePositionAndOrientation(estado.cubo, [POS_ORIGEN[0], POS_ORIGEN[1], Z_CUBO], [0, 0, 0, 1])
    p.resetBaseVelocity(estado.cubo, [0, 0, 0], [0, 0, 0])


# ======================================================================
# Demos (bloqueantes, como en los temas 7 y 8)
# ======================================================================
def ejecutar_demo(estado):
    """D: con el brazo activo, coge el cubo donde este y lo deja en el
    destino. Cada tramo es un mover_a() (IK + motores + simular): el
    brazo se mueve con fisica real, no se teletransporta."""
    brazo = estado.activo
    estado.demo_en_curso = True
    print(f"Demo D con el brazo {brazo}: cogiendo el cubo...")
    x, y, _ = p.getBasePositionAndOrientation(estado.cubo)[0]
    xd, yd = POS_DESTINO

    mover_pinza(estado, brazo, abierta=True)
    mover_a(estado, brazo, (x, y, Z_VIAJE), 360)          # encima del cubo
    mover_a(estado, brazo, (x, y, Z_AGARRE + 0.05), 180)   # se acerca
    mover_a(estado, brazo, (x, y, Z_AGARRE), 180)          # baja despacio hasta el cubo
    mover_pinza(estado, brazo, abierta=False)              # cierra los dedos
    avanzar(estado, 120)
    if not intentar_agarrar(estado, brazo):                 # y lo "suelda" a la pinza
        print("Demo: el cubo no quedo entre los dedos (se movio?). Pulsa 0 para reponerlo.")
    mover_a(estado, brazo, (x, y, Z_VIAJE), 240)          # lo levanta
    mover_a(estado, brazo, (xd, yd, Z_VIAJE), 360)        # viaja hasta encima del destino
    mover_a(estado, brazo, (xd, yd, Z_AGARRE + 0.003), 300)   # baja (3 mm de aire: no lo aplasta)
    abrir_y_soltar(estado, brazo)                           # abre los dedos y borra el constraint
    avanzar(estado, 60)
    mover_a(estado, brazo, (xd, yd, Z_VIAJE), 240)        # se aleja hacia arriba
    print("Demo D: listo, el cubo quedo en el destino.")
    estado.demo_en_curso = False


def ejecutar_demo_recorrido(estado):
    """B: pasea el endpoint del brazo activo por X, Y y Z (cada eje a su
    turno, volviendo al centro), para mostrar el rango de movimiento."""
    brazo = estado.activo
    estado.demo_en_curso = True
    print(f"Demo B con el brazo {brazo}: recorriendo los 3 ejes...")
    (x0, x1), (y0, y1), (z0, z1) = LIMITES_JOG[brazo]
    centro = ((x0 + x1) / 2, (y0 + y1) / 2, Z_VIAJE)
    cx, cy, cz = centro
    recorrido = [centro, (x1, cy, cz), (x0, cy, cz), centro,
                 (cx, y1, cz), (cx, y0, cz), centro,
                 (cx, cy, z1), (cx, cy, Z_AGARRE + 0.05), centro]
    for punto in recorrido:
        mover_a(estado, brazo, punto, 300)
    print("Demo B: recorrido listo.")
    estado.demo_en_curso = False


# ======================================================================
# Teclas: que hace cada una, y el filtro jog / flanco
# ======================================================================
def limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def ejecutar_tecla(estado, tecla):
    """La UNICA funcion que decide que hace cada tecla. La usan el ESP32
    y los botones de la ventana: asi nunca se desincronizan."""
    brazo = estado.activo
    objetivo = list(estado.objetivo.get(brazo, HOME[brazo]))
    jog = {"8": (1, +1), "2": (1, -1), "4": (0, -1), "6": (0, +1), "9": (2, +1), "7": (2, -1)}
    if tecla in jog:
        eje, signo = jog[tecla]
        objetivo[eje] += signo * PASO_JOG
        # el jog nunca deja el objetivo fuera de la caja de trabajo
        objetivo = [limitar(objetivo[e], *LIMITES_JOG[brazo][e]) for e in range(3)]
        fijar_objetivo(estado, brazo, objetivo)
    elif tecla == "5":
        fijar_objetivo(estado, brazo, HOME[brazo])
    elif tecla == "A":
        abrir_y_soltar(estado, brazo)
    elif tecla == "C":
        mover_pinza(estado, brazo, abierta=False)
        intentar_agarrar(estado, brazo)
    elif tecla == "D":
        ejecutar_demo(estado)
    elif tecla == "B":
        ejecutar_demo_recorrido(estado)
    elif tecla == "0":
        reponer_cubo(estado)
    elif tecla == "*":
        # El otro brazo NO necesita nada: sus motores siguen con el ultimo
        # objetivo que recibieron y lo sostienen quieto contra la gravedad.
        estado.activo = "derecho" if brazo == "izquierdo" else "izquierdo"
        print(f"Brazo activo: {estado.activo}")
    estado.ultima_tecla = tecla
    actualizar_texto(estado)


def procesar_tecla(estado, tecla):
    """Filtro para lo que llega del ESP32. El firmware repite la tecla
    sostenida cada 50 ms: las de JOG actuan en cada repeticion (sostener
    = moverse de corrido); todas las demas actuan solo en el FLANCO (la
    tecla recibida es distinta de la anterior). Sin esto, un toque de *
    (unas 4 lineas) cambiaria de brazo 4 veces, y uno de D correria la
    demo 4 veces seguidas."""
    anterior, estado.tecla_anterior = estado.tecla_anterior, tecla
    if tecla == "-":
        return
    if tecla in TECLAS_JOG or tecla != anterior:
        ejecutar_tecla(estado, tecla)
    if tecla in ("D", "B") and estado.ser is not None:
        # lo que llego MIENTRAS corria la demo (bloqueante) son lineas
        # viejas: se descartan en vez de ejecutarlas todas juntas al final
        estado.ser.reset_input_buffer()


def procesar_linea(estado, linea):
    """Una linea cruda del ESP32 (o simulada en la prueba)."""
    linea = linea.strip()
    if linea != estado.ultima_linea:
        estado.ultima_linea = linea
        actualizar_texto(estado)
    if linea.startswith("TECLA:"):
        procesar_tecla(estado, linea.split(":", 1)[1])


def actualizar_texto(estado):
    """Linea de estado arriba en la ventana: brazo activo, ultima tecla y
    ultima linea CRUDA del ESP32 (si nunca cambia, el ESP32 no manda nada;
    si cambia pero no dice TECLA:x, el problema es de formato, no de cable)."""
    if estado.id_texto is None:
        return
    serial_txt = estado.ultima_linea or ("esperando datos..." if estado.ser else "no conectado (usa los botones)")
    texto = f"Brazo activo: {estado.activo.upper()}  |  tecla: {estado.ultima_tecla}  |  ESP32: {serial_txt}"
    estado.id_texto = p.addUserDebugText(texto, [0.2, 0, 0.95], textColorRGB=[1, 1, 0.4], textSize=1.3,
                                         replaceItemUniqueId=estado.id_texto)


# ======================================================================
# Entrada: serial y botones
# ======================================================================
def abrir_serial():
    """Intenta abrir el puerto; sin ESP32 devuelve None y todo sigue con
    los botones de la ventana."""
    import serial
    try:
        ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.05)
        time.sleep(2)   # el ESP32 se reinicia al abrir el puerto: darle tiempo
        print(f"ESP32 conectado en {PUERTO_SERIAL}: el teclado mueve a Baxter.")
        return ser
    except serial.SerialException:
        print(f"No se encontro el ESP32 en {PUERTO_SERIAL}: usa los botones de la ventana.")
        return None


def leer_serial(estado):
    """Lee SOLO si ya hay datos esperando (in_waiting) y drena TODO el
    buffer (while, no if). Un readline() a secas con timeout bloquearia
    el bucle hasta 50 ms cuando no hay linea, y con el toda la simulacion
    (quedaria a ~20 cuadros/s en vez de 240)."""
    import serial
    try:
        while estado.ser is not None and estado.ser.in_waiting:
            procesar_linea(estado, estado.ser.readline().decode(errors="ignore"))
    except serial.SerialException:
        print("Se perdio la conexion con el ESP32: sigue con los botones de la ventana.")
        estado.ser = None
        actualizar_texto(estado)


def crear_botones(estado):
    """Un boton por tecla, creados UNA sola vez (PyBullet no borra bien
    los botones/sliders: recrearlos los deja duplicados en el panel)."""
    estado.botones = {etiqueta: [p.addUserDebugParameter(etiqueta, 1, 0, 0), 0] for etiqueta in BOTON_A_TECLA}


def leer_botones(estado):
    """Un boton de PyBullet es un contador que sube con cada click: si
    cambio, es una pulsacion (un paso de jog o una accion)."""
    for etiqueta, datos in estado.botones.items():
        contador = p.readUserDebugParameter(datos[0])
        if contador != datos[1]:
            datos[1] = contador
            ejecutar_tecla(estado, BOTON_A_TECLA[etiqueta])


def bucle_principal(estado):
    print("Ventana de PyBullet abierta. Cierra la ventana o Ctrl+C en la terminal para salir.")
    while p.isConnected(estado.cliente):
        leer_serial(estado)
        leer_botones(estado)
        avanzar(estado, 1)


if __name__ == "__main__":
    estado = crear_mundo(p.GUI)
    estado.ser = abrir_serial()
    actualizar_texto(estado)
    crear_botones(estado)
    try:
        bucle_principal(estado)
    except (KeyboardInterrupt, p.error):
        pass
    finally:
        if estado.ser is not None:
            estado.ser.close()
