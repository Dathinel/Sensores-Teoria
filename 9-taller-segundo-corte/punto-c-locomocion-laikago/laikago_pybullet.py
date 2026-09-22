# Punto c) del taller: "movilidad real" con las 4 patas, no solo el
# brazo del punto b). Carga el mismo robot que usa el repositorio del
# profesor (github.com/erwincoumans/pybullet_robots/blob/master/laikago.py):
# laikago_toes.urdf, un cuadrupedo de 12 articulaciones, ya incluido en
# pybullet_data.
#
# Ese script del profesor reproduce una caminata GRABADA (data1.txt, una
# captura real de un robot caminando). Se probo tal cual primero, pero el
# resultado fue un robot que mueve las patas de forma realista sin
# apenas desplazarse -- la friccion/masas con las que se grabo esa
# captura no coinciden con las de este URDF simulado aca, asi que la
# fisica de contacto no llega a empujarlo. La alternativa que SI funciona
# con fisica real de verdad (nada de teletransportar el cuerpo) es un
# "CPG" (*central pattern generator*): un patron de trote generado con
# senos, la misma tecnica que usan los ejemplos oficiales de PyBullet
# para el minitaur. Los parametros (amplitud, frecuencia, fuerza) salieron
# de probar varias combinaciones hasta encontrar una que camina sin
# caerse (ver la explicacion completa en el README).
#
# Un solo teclado matricial 4x4 controla todo (ver esp32_teclado.py, el
# mismo firmware que usan punto-a-drones-waypoints y punto-b-brazo-tipo-baxter):
# esta es la CONFIGURACION de locomocion, con este mapeo de teclas:
#
#   8 (sostenida) = caminar hacia adelante (trote real, fisica de verdad)
#   4 / 6         = girar un poco a la izquierda/derecha (para el trote primero)
#   5             = reset (vuelve a la pose y posicion inicial, parado)
#   (0, 1, 3, 7, 9, A, B, C, D, *, # no se usan en esta configuracion)
#
# Si no hay ESP32 conectado, la ventana de PyBullet trae los mismos
# botones (caminar/girar/reset), igual que en los otros dos puntos.

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
    print(f"ESP32 conectado en {PUERTO_SERIAL}: el teclado hace caminar al robot.")
except serial.SerialException:
    ser = None
    print(f"No se encontro el ESP32 en {PUERTO_SERIAL}: usa los botones de la ventana.")

PASO_FISICA = 1.0 / 500
p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
p.setTimeStep(PASO_FISICA)
p.loadURDF("plane.urdf")
p.resetDebugVisualizerCamera(cameraDistance=1.6, cameraYaw=45, cameraPitch=-25, cameraTargetPosition=[0, 0, 0.3])

POSICION_INICIAL = [0.0, 0.0, 0.5]
ORIENTACION_INICIAL_URDF = [0, 0.5, 0.5, 0]  # misma orientacion de carga que usa laikago.py

URDF_FLAGS = p.URDF_USE_SELF_COLLISION
quadruped = p.loadURDF("laikago/laikago_toes.urdf", POSICION_INICIAL, ORIENTACION_INICIAL_URDF,
                        flags=URDF_FLAGS, useFixedBase=False)

# habilita colision entre las 4 patas inferiores (si no, se atraviesan
# entre ellas al caminar) -- igual que en laikago.py
PATAS_INFERIORES = [2, 5, 8, 11]
for pata_a in PATAS_INFERIORES:
    for pata_b in PATAS_INFERIORES:
        if pata_b > pata_a:
            p.setCollisionFilterPair(quadruped, quadruped, pata_a, pata_b, 1)

JOINT_IDS = []
for junta in range(p.getNumJoints(quadruped)):
    p.changeDynamics(quadruped, junta, linearDamping=0, angularDamping=0)
    info = p.getJointInfo(quadruped, junta)
    if info[2] in (p.JOINT_PRISMATIC, p.JOINT_REVOLUTE):
        JOINT_IDS.append(junta)
# JOINT_IDS queda en grupos de 3 por pata: [abduccion, cadera, rodilla],
# en el orden FR (delantera-derecha), FL (delantera-izquierda),
# RR (trasera-derecha), RL (trasera-izquierda) -- ese es el orden en el
# propio URDF.

# ------------------------------------------------------------------
# CPG (central pattern generator): un trote real generado con senos, en
# vez de repetir una caminata grabada (ver el comentario del encabezado y
# el README para la explicacion completa). FR+RL en fase, FL+RR en fase
# opuesta -- el patron de trote clasico de un cuadrupedo (2 patas en
# diagonal se apoyan mientras las otras 2 avanzan).
# ------------------------------------------------------------------
DIR_ABDUCCION = [-1, 1, -1, 1]   # FR, FL, RR, RL (las patas de la derecha giran al reves)
FASE_PATA = [0, math.pi, math.pi, 0]
OFFSET_CADERA = -0.7
OFFSET_RODILLA = 0.7

# valores encontrados probando varias combinaciones: los primeros que se
# probaron (amplitudes/frecuencias mas altas) hacian caer al robot antes
# de completar un paso; estos caminan de corrido sin caerse
AMPLITUD_CADERA = 0.2    # cuanto se adelanta/atrasa la pata (rad)
AMPLITUD_RODILLA = 0.3   # cuanto se levanta el pie durante el avance (rad)
FRECUENCIA_TROTE = 1.2   # zancadas por segundo
FUERZA_MOTOR = 35


def objetivos_trote(t):
    """Devuelve (abduccion, cadera, rodilla) para las 4 patas en el
    instante t (segundos desde que arranco a caminar). En t=0 coincide
    exactamente con la pose de pie quieta (todas las patas abajo)."""
    objetivos = []
    for pata in range(4):
        fase = 2 * math.pi * FRECUENCIA_TROTE * t + FASE_PATA[pata]
        cadera = OFFSET_CADERA + AMPLITUD_CADERA * math.sin(fase)
        levantar = max(0.0, math.sin(fase))  # solo levanta el pie durante el avance, no al apoyar
        rodilla = OFFSET_RODILLA - AMPLITUD_RODILLA * levantar
        objetivos.append((0.0, cadera, rodilla))
    return objetivos


def aplicar_pose(abd_cadera_rodilla_por_pata):
    for pata, (abduccion, cadera, rodilla) in enumerate(abd_cadera_rodilla_por_pata):
        base = pata * 3
        p.setJointMotorControl2(quadruped, JOINT_IDS[base + 0], p.POSITION_CONTROL,
                                 DIR_ABDUCCION[pata] * abduccion, force=FUERZA_MOTOR)
        p.setJointMotorControl2(quadruped, JOINT_IDS[base + 1], p.POSITION_CONTROL, cadera, force=FUERZA_MOTOR)
        p.setJointMotorControl2(quadruped, JOINT_IDS[base + 2], p.POSITION_CONTROL, rodilla, force=FUERZA_MOTOR)


caminando = False
yaw_actual = 0.0
tiempo_trote = 0.0  # solo avanza mientras se camina, para no "saltar" de fase al reanudar

PASOS_ASENTAR = 250  # ~0.5s a 500Hz


def yaw_a_quaternion_mundo(yaw):
    """Combina el giro manual (yaw, sobre Z del mundo) con la orientacion
    propia del URDF al cargarse (ORIENTACION_INICIAL_URDF)."""
    giro_manual = p.getQuaternionFromEuler([0, 0, yaw])
    return p.multiplyTransforms([0, 0, 0], giro_manual, [0, 0, 0], ORIENTACION_INICIAL_URDF)[1]


def reset_robot():
    """Ademas de reubicar al robot, lo deja PARADO Y ASENTADO en el piso
    (250 pasos de fisica sosteniendo la pose de pie) antes de devolver el
    control. Arrancar a trotar de un salto, recien cargado (sin este
    asentado), lo hacia caer casi de inmediato -- las patas todavia no
    habian hecho contacto real con el piso."""
    global caminando, yaw_actual, tiempo_trote
    caminando = False
    yaw_actual = 0.0
    tiempo_trote = 0.0
    p.resetBasePositionAndOrientation(quadruped, POSICION_INICIAL, ORIENTACION_INICIAL_URDF)
    p.resetBaseVelocity(quadruped, [0, 0, 0], [0, 0, 0])
    for pata, (abduccion, cadera, rodilla) in enumerate(objetivos_trote(0.0)):
        base = pata * 3
        p.resetJointState(quadruped, JOINT_IDS[base + 0], DIR_ABDUCCION[pata] * abduccion)
        p.resetJointState(quadruped, JOINT_IDS[base + 1], cadera)
        p.resetJointState(quadruped, JOINT_IDS[base + 2], rodilla)
    for _ in range(PASOS_ASENTAR):
        aplicar_pose(objetivos_trote(0.0))
        p.stepSimulation()


PASO_GIRO = 0.015          # radianes por linea recibida mientras se sostiene 4/6
PASOS_ASENTAR_GIRO = 80    # se asienta despues de CADA ajuste, no solo al final -- con menos
                           # pasos (se probo con 30) a veces quedaba un resto de velocidad
                           # que quitaba estabilidad al reanudar el trote


def girar_pasos(direccion, pasos=1):
    """direccion: -1 izquierda, +1 derecha. SIEMPRE con el trote detenido
    (ver procesar_tecla): girar caminando de verdad, con zancadas
    asimetricas por lado, se probo primero y el robot se caia con
    bastante frecuencia -- ni siquiera el ejemplo del profesor resuelve
    el equilibrio de un cuadrupedo girando, que es un problema de control
    bastante mas dificil que caminar derecho. Reorientar el torso a mano
    (parado) y asentarlo unos pasos despues de cada ajuste es la unica
    forma que salio confiable en las pruebas."""
    global yaw_actual
    yaw_actual += direccion * PASO_GIRO * pasos
    pos_actual = p.getBasePositionAndOrientation(quadruped)[0]
    p.resetBasePositionAndOrientation(quadruped, pos_actual, yaw_a_quaternion_mundo(yaw_actual))
    p.resetBaseVelocity(quadruped, [0, 0, 0], [0, 0, 0])
    for _ in range(PASOS_ASENTAR_GIRO):
        aplicar_pose(objetivos_trote(0.0))
        p.stepSimulation()


reset_robot()

# ------------------------------------------------------------------
# Botones de la ventana: caminar/girar/reset, mismo patron que en los
# otros 2 puntos del taller.
# ------------------------------------------------------------------
botones = {
    "caminar": p.addUserDebugParameter("Caminar (alternar on/off)", 1, 0, 0),
    "izquierda": p.addUserDebugParameter("Girar izquierda (un paso)", 1, 0, 0),
    "derecha": p.addUserDebugParameter("Girar derecha (un paso)", 1, 0, 0),
    "reset": p.addUserDebugParameter("Reset", 1, 0, 0),
}
contadores_anteriores = {nombre: 0 for nombre in botones}


def procesar_tecla(tecla):
    # Girar SIEMPRE detiene el trote primero (ver girar_pasos): combinar
    # las dos cosas es lo que hacia caer al robot en las pruebas.
    global caminando, tiempo_trote
    if tecla == "4":
        caminando = False
        girar_pasos(-1)
    elif tecla == "6":
        caminando = False
        girar_pasos(1)
    else:
        nuevo_caminando = (tecla == "8")
        if nuevo_caminando and not caminando:
            tiempo_trote = 0.0  # arranca la fase del trote de cero (coincide con la pose de pie quieta)
        caminando = nuevo_caminando
    if tecla == "5":
        reset_robot()


print("Ventana de PyBullet abierta. Cierra la ventana o Ctrl+C en la terminal para salir.")

while True:
    # teclado fisico (ESP32): llega "TECLA:x" sin parar. Se lee solo si
    # YA hay datos esperando (in_waiting) para no bloquear la simulacion
    # -- ver la explicacion en brazo_pybullet.py.
    if ser is not None and ser.in_waiting:
        linea = ser.readline().decode(errors="ignore").strip()
        if linea.startswith("TECLA:"):
            procesar_tecla(linea.split(":", 1)[1])

    # botones de la ventana: "Caminar" alterna on/off con cada click (no
    # se puede "sostener" un click en addUserDebugParameter), "Girar" gira
    # un paso fijo por click -- se leen SIEMPRE, no solo sin ESP32.
    for nombre, boton in botones.items():
        contador = p.readUserDebugParameter(boton)
        if contador != contadores_anteriores[nombre]:
            contadores_anteriores[nombre] = contador
            if nombre == "caminar":
                if not caminando:
                    tiempo_trote = 0.0
                caminando = not caminando
            elif nombre == "izquierda":
                caminando = False
                girar_pasos(-1, pasos=10)
            elif nombre == "derecha":
                caminando = False
                girar_pasos(1, pasos=10)
            elif nombre == "reset":
                reset_robot()

    # red de seguridad: caminar y girar son fisica real (nada de trucos),
    # asi que -- igual que un robot de verdad -- se puede llegar a caer si
    # se encadenan muchos giros grandes seguidos. Si eso pasa, se deja de
    # insistir en caminar (que solo lo arrastraria panza abajo) y se
    # espera al reset en vez de intentar seguir.
    if p.getBasePositionAndOrientation(quadruped)[0][2] < 0.3:
        caminando = False

    # caminar: trote real generado con senos (objetivos_trote), con
    # fisica de verdad empujando al robot -- no se teletransporta nada
    if caminando:
        aplicar_pose(objetivos_trote(tiempo_trote))
        tiempo_trote += PASO_FISICA
    else:
        aplicar_pose(objetivos_trote(0.0))  # pose de pie quieta, las 4 patas abajo

    p.stepSimulation()
    time.sleep(PASO_FISICA)
