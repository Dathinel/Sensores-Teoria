# Punto b) del taller: consola de mandos con el ESP32 para mover con
# fluidez el brazo de un robot y que pueda coger y mover un objeto. El
# punto c) (locomocion con las 4 patas) es otro robot y otro problema
# de control -- ver ../punto-c-locomocion-laikago/.
#
# El enunciado pide el robot Baxter (ver enunciado-actividad.png), usando
# como base
# github.com/erwincoumans/pybullet_robots/blob/master/baxter_ik_demo.py.
# Ese script carga "baxter_common/baxter_description/urdf/toms_baxter.urdf",
# que NO viene en ese repo ni en el paquete pip de pybullet_data: son los
# mesh/URDF de RethinkRobotics/baxter_common (~50 MB de mallas), fuera de
# lugar en un repo de apuntes de clase liviano como este.
#
# Se usa en su lugar el brazo KUKA IIWA + pinza WSG50 que SI trae
# pybullet_data (kuka_iiwa/kuka_with_gripper2.sdf), con exactamente la
# misma tecnica de baxter_ik_demo.py (calculateInverseKinematics hacia
# una posicion XYZ del efector final) y los mismos indices de
# articulacion/pinza que usa el propio ejemplo oficial de pybullet para
# este modelo (pybullet_envs/bullet/kuka.py): un solo brazo alcanza para
# demostrar lo que pide el punto b) -- movimiento fluido, posicionamiento
# real y coger/mover un objeto -- sin descargar mallas pesadas.
#
# Un solo teclado matricial 4x4 controla todo (ver esp32_teclado.py, el
# mismo firmware que usa punto-a-drones-waypoints): esta es la
# "configuracion" de brazo, con este mapeo de teclas:
#
#   8/2 = adelante/atras (Y+/Y-)      4/6 = izquierda/derecha (X-/X+)
#   9/7 = subir/bajar (Z+/Z-)         5   = home (postura neutra)
#   A = Abrir pinza                   C = Cerrar pinza
#   D = Demo: coger el cubo y moverlo solo al destino
#   B = Demo: recorrer los 3 ejes (solo para mostrar el rango de movimiento)
#   0 = reset (reubica el cubo, cancela cualquier demo)
#   (1, 3, *, # no se usan en esta configuracion)
#
# Si no hay ESP32 conectado, la ventana de PyBullet trae los mismos
# botones (jog de paso fijo + abrir/cerrar/home/demo/reset), igual que en
# los temas 7 y 8.

import math
import time

import pybullet as p
import pybullet_data
import serial

PUERTO_SERIAL = "COM7"
BAUDIOS = 115200

try:
    ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.05)
    time.sleep(2)  # da tiempo a que el ESP32 termine de reiniciar tras abrir el puerto
    print(f"ESP32 conectado en {PUERTO_SERIAL}: el teclado mueve el brazo.")
except serial.SerialException:
    ser = None
    print(f"No se encontro el ESP32 en {PUERTO_SERIAL}: usa los botones de la ventana.")

physics_client = p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -10)
p.loadURDF("plane.urdf", [0, 0, -0.65], useFixedBase=True)
p.resetDebugVisualizerCamera(cameraDistance=1.3, cameraYaw=50, cameraPitch=-35, cameraTargetPosition=[0.5, 0, -0.2])

# ------------------------------------------------------------------
# Brazo KUKA IIWA + pinza WSG50 (kuka_with_gripper2.sdf), con la misma
# pose inicial "de reposo" que usa pybullet_envs/bullet/kuka.py -- ya
# probada y alcanzable, evita empezar en una postura rara.
# ------------------------------------------------------------------
brazo_id = p.loadSDF("kuka_iiwa/kuka_with_gripper2.sdf")[0]
p.resetBasePositionAndOrientation(brazo_id, [-0.1, 0.0, 0.07], [0, 0, 0, 1])

POSE_INICIAL = [0.006418, 0.413184, -0.011401, -1.589317, 0.005379, 1.137684, -0.006539,
                0.000048, -0.299912, 0.0, -0.000043, 0.29996, 0.0, -0.0002]
for indice_junta, valor in enumerate(POSE_INICIAL):
    p.resetJointState(brazo_id, indice_junta, valor)

INDICE_EFECTOR = 6   # muñeca (posicion XYZ para la IK)
INDICE_MUNECA = 7    # giro de la pinza (no se usa en esta actividad, queda fijo en 0)
DEDO_A, DEDO_B = 8, 11        # las 2 pinzas principales (signos opuestos)
PUNTA_A, PUNTA_B = 10, 13     # puntas de los dedos, siempre en 0

# limites de nulo espacio para la IK, iguales a los del ejemplo oficial
LIM_INF = [-.967, -2, -2.96, 0.19, -2.96, -2.09, -3.05]
LIM_SUP = [.967, 2, 2.96, 2.29, 2.96, 2.09, 3.05]
RANGO_JUNTAS = [5.8, 4, 5.8, 4, 5.8, 4, 6]
POSE_REPOSO = [0, 0, 0, 0.5 * math.pi, 0, -math.pi * 0.5 * 0.66, 0]

# ------------------------------------------------------------------
# Bandeja de origen (con el cubo a agarrar, tray/tray.urdf del ejemplo
# oficial) y una plataforma chica de destino. El destino NO es otra
# bandeja igual: la malla de tray.urdf es mucho mas ancha de lo que
# parece por su posicion (~0.6 m) y dos bandejas completas a menos de
# esa distancia terminan con las mallas encimadas -- se probo primero
# asi y el choque entre las dos hacia que el cubo saliera disparado a un
# punto aleatorio de la escena apenas arrancaba la simulacion. La
# plataforma de destino es chica a proposito para no repetir el problema.
# ------------------------------------------------------------------
POS_ORIGEN = (0.55, 0.20, -0.19)
POS_DESTINO = (0.55, -0.30, -0.17)
p.loadURDF("tray/tray.urdf", POS_ORIGEN, useFixedBase=True)
_col_destino = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.01])
_vis_destino = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.08, 0.08, 0.01], rgbaColor=[0.5, 0.5, 0.55, 1])
p.createMultiBody(baseMass=0, baseCollisionShapeIndex=_col_destino, baseVisualShapeIndex=_vis_destino, basePosition=POS_DESTINO)
p.addUserDebugText("ORIGEN", [POS_ORIGEN[0], POS_ORIGEN[1], 0.05], textColorRGB=[0.3, 0.8, 1], textSize=1.2)
p.addUserDebugText("DESTINO", [POS_DESTINO[0], POS_DESTINO[1], 0.05], textColorRGB=[0.4, 1, 0.4], textSize=1.2)

POS_INICIAL_CUBO = (POS_ORIGEN[0], POS_ORIGEN[1], 0.05)


def reset_cubo():
    global cubo_id
    try:
        p.removeBody(cubo_id)
    except NameError:
        pass
    cubo_id = p.loadURDF("cube_small.urdf", POS_INICIAL_CUBO)
    return cubo_id


cubo_id = reset_cubo()

# El efector (INDICE_EFECTOR=6, la muneca) queda ~0.24 por encima de las
# puntas de la pinza una vez que la IK converge con la pinza mirando hacia
# abajo -- medido probando distintos valores de z contra la posicion real
# de los dedos (getLinkState). El cubo se asienta en z=-0.159 sobre la
# bandeja y en z=-0.135 sobre la plataforma de destino (mas alta, por eso
# cada apoyo tiene su propia altura de agarre).
OFFSET_PINZA_SOBRE_CUBO = 0.24
ALTURA_AGARRE_ORIGEN = -0.159 + OFFSET_PINZA_SOBRE_CUBO
ALTURA_AGARRE_DESTINO = -0.135 + OFFSET_PINZA_SOBRE_CUBO
ALTURA_VIAJE = 0.35    # z del efector al trasladarse entre bandeja y plataforma, sin chocar contra ninguna

# Midiendo la separacion real entre las puntas de los dedos (getLinkState)
# para cada angulo: en 0.0 los dedos casi se tocan (separacion ~0.04 m,
# MENOS que el cubo de 0.05 m -> ahi es donde agarran) y al subir el
# angulo se van abriendo (en 0.15, separacion ~0.08 m, ya con espacio de
# sobra para pasar por encima del cubo sin rozarlo).
ANGULO_PINZA_ABIERTA = 0.15
ANGULO_PINZA_CERRADA = 0.0

HOME_EFECTOR = (0.537, 0.0, ALTURA_VIAJE)  # XYZ de la pose de reposo (misma que usa pybullet_envs/bullet/kuka.py)
posicion_objetivo = list(HOME_EFECTOR)
angulo_pinza = ANGULO_PINZA_ABIERTA
demo_en_curso = False

PASO_JOG = 0.015


def mover_brazo(pos_xyz):
    """Mueve SOLO las 7 articulaciones del brazo (IK hacia pos_xyz). No
    toca la pinza -- llamarla de nuevo con el mismo pos_xyz vuelve a
    resolver la IK desde el estado actual y, al ser un brazo redundante
    (7 GDL), a veces converge a otra postura valida pero distinta de la
    anterior. Por eso, para abrir/cerrar la pinza SIN mover el brazo, se
    usa mover_pinza() en vez de llamar esta funcion de nuevo."""
    orientacion = p.getQuaternionFromEuler([0, -math.pi, 0])  # pinza siempre mirando hacia abajo
    poses_juntas = p.calculateInverseKinematics(brazo_id, INDICE_EFECTOR, pos_xyz, orientacion,
                                                 LIM_INF, LIM_SUP, RANGO_JUNTAS, POSE_REPOSO)
    for i in range(INDICE_EFECTOR + 1):
        p.setJointMotorControl2(brazo_id, i, p.POSITION_CONTROL, targetPosition=poses_juntas[i],
                                 force=200, maxVelocity=1.2, positionGain=0.5, velocityGain=1)
    p.setJointMotorControl2(brazo_id, INDICE_MUNECA, p.POSITION_CONTROL, targetPosition=0, force=200)


def mover_pinza(pinza):
    """Abre/cierra la pinza sin tocar las articulaciones del brazo."""
    p.setJointMotorControl2(brazo_id, DEDO_A, p.POSITION_CONTROL, targetPosition=-pinza, force=15)
    p.setJointMotorControl2(brazo_id, DEDO_B, p.POSITION_CONTROL, targetPosition=pinza, force=15)
    p.setJointMotorControl2(brazo_id, PUNTA_A, p.POSITION_CONTROL, targetPosition=0, force=10)
    p.setJointMotorControl2(brazo_id, PUNTA_B, p.POSITION_CONTROL, targetPosition=0, force=10)


def esperar(segundos=1.0):
    for _ in range(int(segundos * 240)):
        p.stepSimulation()
        time.sleep(1 / 240)


# ------------------------------------------------------------------
# Agarrar solo por friccion/contacto de la pinza (como en baxter_ik_demo.py)
# resulto poco confiable en las pruebas: la pinza es liviana y el cubo se
# escapaba o quedaba mal sujeto en cuanto el brazo empezaba a moverse en
# vez de quedarse quieto sosteniendolo. La solucion es la misma que usan
# muchos tutoriales de pick-and-place en PyBullet: al cerrar la pinza
# CERCA del cubo, se crea un p.JOINT_FIXED entre el efector y el cubo
# (una "soldadura" temporal) que lo mantiene pegado a la pinza mientras
# viaja, y se elimina al abrir la pinza para soltarlo.
# ------------------------------------------------------------------
# el efector queda a ~OFFSET_PINZA_SOBRE_CUBO (0.24) del cubo incluso
# bien posicionado para agarrarlo (la pinza cuelga por debajo de la
# muneca), asi que el umbral tiene que ser mayor a eso
UMBRAL_AGARRE = 0.32  # distancia maxima efector-cubo para poder "agarrarlo"
restriccion_agarre = None


def intentar_agarrar():
    """En vez de asumir un offset fijo pinza-cubo (la orientacion real de
    la muneca varia un poco segun como convergio la IK), se calcula la
    transformacion relativa EXACTA entre el efector y el cubo en el
    instante del agarre (invertTransform + multiplyTransforms) y esa es
    la que se fija en la restriccion -- el cubo queda exactamente donde
    estaba respecto a la pinza, sin importar el angulo con el que llego."""
    global restriccion_agarre
    if restriccion_agarre is not None:
        return
    pos_efector, orn_efector = p.getLinkState(brazo_id, INDICE_EFECTOR)[:2]
    pos_cubo, orn_cubo = p.getBasePositionAndOrientation(cubo_id)
    distancia = sum((pos_efector[i] - pos_cubo[i]) ** 2 for i in range(3)) ** 0.5
    if distancia <= UMBRAL_AGARRE:
        inv_pos, inv_orn = p.invertTransform(pos_efector, orn_efector)
        pos_relativa, orn_relativa = p.multiplyTransforms(inv_pos, inv_orn, pos_cubo, orn_cubo)
        restriccion_agarre = p.createConstraint(
            parentBodyUniqueId=brazo_id, parentLinkIndex=INDICE_EFECTOR,
            childBodyUniqueId=cubo_id, childLinkIndex=-1,
            jointType=p.JOINT_FIXED, jointAxis=[0, 0, 0],
            parentFramePosition=pos_relativa, parentFrameOrientation=orn_relativa,
            childFramePosition=[0, 0, 0])


def soltar():
    global restriccion_agarre
    if restriccion_agarre is not None:
        p.removeConstraint(restriccion_agarre)
        restriccion_agarre = None


def ejecutar_demo():
    """Secuencia automatica: baja al cubo, cierra la pinza, lo levanta,
    lo lleva a la bandeja de destino y lo suelta. Bloquea el programa
    mientras corre (igual que dibujar_digito() en el tema 8)."""
    global posicion_objetivo, angulo_pinza, demo_en_curso
    demo_en_curso = True
    print("Demo: cogiendo el cubo...")

    x_cubo, y_cubo, _ = p.getBasePositionAndOrientation(cubo_id)[0]
    encima_origen = (x_cubo, y_cubo, ALTURA_VIAJE)
    sobre_cubo = (x_cubo, y_cubo, ALTURA_AGARRE_ORIGEN)
    encima_destino = (POS_DESTINO[0], POS_DESTINO[1], ALTURA_VIAJE)
    sobre_destino = (POS_DESTINO[0], POS_DESTINO[1], ALTURA_AGARRE_DESTINO)

    # cada mover_brazo() es un movimiento real del brazo; mover_pinza() por
    # su lado solo abre/cierra sin recalcular la IK, para no arriesgarse a
    # que el brazo "salte" a otra postura valida por las suyas mientras
    # solo se queria abrir o cerrar la pinza en el mismo lugar
    mover_pinza(ANGULO_PINZA_ABIERTA); esperar(0.4)
    mover_brazo(encima_origen); esperar(1.1)              # encima del cubo
    mover_brazo(sobre_cubo); esperar(1.1)                  # baja hasta el cubo
    mover_pinza(ANGULO_PINZA_CERRADA); esperar(0.6)        # cierra la pinza
    intentar_agarrar()                                     # lo "suelda" al efector
    mover_brazo(encima_origen); esperar(1.1)               # lo levanta
    mover_brazo(encima_destino); esperar(1.4)              # viaja al destino
    mover_brazo(sobre_destino); esperar(1.1)               # baja
    soltar()                                                # lo desengancha del efector
    mover_pinza(ANGULO_PINZA_ABIERTA); esperar(0.6)        # suelta el cubo
    mover_brazo(encima_destino); esperar(1.1)              # se aleja

    posicion_objetivo = list(encima_destino)
    angulo_pinza = ANGULO_PINZA_ABIERTA
    print("Demo: listo, el cubo quedo en el destino.")
    demo_en_curso = False


def ejecutar_demo_recorrido():
    """Demo separada de la de coger el cubo: solo pasea el efector por los
    3 ejes (X, Y y Z, cada uno a su turno) para mostrar el rango de
    movimiento del brazo, sin tocar el cubo ni la pinza."""
    global posicion_objetivo, demo_en_curso
    demo_en_curso = True
    print("Demo: recorriendo los 3 ejes...")

    x0, y0, z0 = HOME_EFECTOR
    recorrido = [
        HOME_EFECTOR,
        (x0 + 0.13, y0, z0),   # X+
        (x0 - 0.19, y0, z0),   # X-
        HOME_EFECTOR,
        (x0, y0 + 0.3, z0),    # Y+
        (x0, y0 - 0.3, z0),    # Y-
        HOME_EFECTOR,
        (x0, y0, 0.55),        # Z+ (arriba)
        (x0, y0, 0.08),        # Z- (abajo, casi tocando la bandeja)
        HOME_EFECTOR,
    ]
    for punto in recorrido:
        mover_brazo(punto)
        esperar(0.9)

    posicion_objetivo = list(HOME_EFECTOR)
    print("Demo: recorrido listo.")
    demo_en_curso = False


# ------------------------------------------------------------------
# Botones de la ventana (fijos, sin ESP32), mismo patron que en los
# temas 7 y 8: jog + abrir/cerrar/home/demo/reset.
# ------------------------------------------------------------------
botones = {
    "adelante": p.addUserDebugParameter("Adelante (Y+)", 1, 0, 0),
    "atras": p.addUserDebugParameter("Atras (Y-)", 1, 0, 0),
    "izquierda": p.addUserDebugParameter("Izquierda (X-)", 1, 0, 0),
    "derecha": p.addUserDebugParameter("Derecha (X+)", 1, 0, 0),
    "subir": p.addUserDebugParameter("Subir (Z+)", 1, 0, 0),
    "bajar": p.addUserDebugParameter("Bajar (Z-)", 1, 0, 0),
    "home": p.addUserDebugParameter("Home", 1, 0, 0),
    "abrir": p.addUserDebugParameter("Abrir pinza", 1, 0, 0),
    "cerrar": p.addUserDebugParameter("Cerrar pinza", 1, 0, 0),
    "demo": p.addUserDebugParameter("Demo: coger y mover", 1, 0, 0),
    "recorrido": p.addUserDebugParameter("Demo: recorrer los 3 ejes", 1, 0, 0),
    "reset": p.addUserDebugParameter("Reset cubo", 1, 0, 0),
}
contadores_anteriores = {nombre: 0 for nombre in botones}


def procesar_tecla(tecla):
    global posicion_objetivo, angulo_pinza
    if tecla == "8":
        posicion_objetivo[1] += PASO_JOG
    elif tecla == "2":
        posicion_objetivo[1] -= PASO_JOG
    elif tecla == "4":
        posicion_objetivo[0] -= PASO_JOG
    elif tecla == "6":
        posicion_objetivo[0] += PASO_JOG
    elif tecla == "9":
        posicion_objetivo[2] += PASO_JOG
    elif tecla == "7":
        posicion_objetivo[2] -= PASO_JOG
    elif tecla == "5":
        posicion_objetivo = list(HOME_EFECTOR)
    elif tecla == "A":
        angulo_pinza = ANGULO_PINZA_ABIERTA
        soltar()
    elif tecla == "C":
        angulo_pinza = ANGULO_PINZA_CERRADA
        intentar_agarrar()
    elif tecla == "D":
        ejecutar_demo()
    elif tecla == "B":
        ejecutar_demo_recorrido()
    elif tecla == "0":
        soltar()
        reset_cubo()


print("Ventana de PyBullet abierta. Cierra la ventana o Ctrl+C en la terminal para salir.")

while True:
    if not demo_en_curso:
        # teclado fisico (ESP32): llega "TECLA:x" sin parar. OJO: leer con
        # ser.readline() a secas (con timeout) bloqueaba hasta 50ms cuando
        # no habia linea todavia, capando TODO el bucle -- incluida la
        # simulacion -- a ~20 cuadros/seg en vez de 240. Por eso se lee
        # solo si YA hay datos esperando (in_waiting): la simulacion nunca
        # se frena esperando al ESP32, y el movimiento manual se ve fluido.
        if ser is not None and ser.in_waiting:
            linea = ser.readline().decode(errors="ignore").strip()
            if linea.startswith("TECLA:"):
                procesar_tecla(linea.split(":", 1)[1])

        # botones de la ventana (sin ESP32): un salto fijo por click
        for nombre, boton in botones.items():
            contador = p.readUserDebugParameter(boton)
            if contador != contadores_anteriores[nombre]:
                contadores_anteriores[nombre] = contador
                if nombre == "adelante":
                    posicion_objetivo[1] += PASO_JOG
                elif nombre == "atras":
                    posicion_objetivo[1] -= PASO_JOG
                elif nombre == "izquierda":
                    posicion_objetivo[0] -= PASO_JOG
                elif nombre == "derecha":
                    posicion_objetivo[0] += PASO_JOG
                elif nombre == "subir":
                    posicion_objetivo[2] += PASO_JOG
                elif nombre == "bajar":
                    posicion_objetivo[2] -= PASO_JOG
                elif nombre == "home":
                    posicion_objetivo = list(HOME_EFECTOR)
                elif nombre == "abrir":
                    angulo_pinza = ANGULO_PINZA_ABIERTA
                    soltar()
                elif nombre == "cerrar":
                    angulo_pinza = ANGULO_PINZA_CERRADA
                    intentar_agarrar()
                elif nombre == "demo":
                    ejecutar_demo()
                elif nombre == "recorrido":
                    ejecutar_demo_recorrido()
                elif nombre == "reset":
                    soltar()
                    reset_cubo()

        mover_brazo(posicion_objetivo)
        mover_pinza(angulo_pinza)

    p.stepSimulation()
    time.sleep(1 / 240)
