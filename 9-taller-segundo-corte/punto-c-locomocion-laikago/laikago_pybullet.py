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

# Valores encontrados probando combinaciones en modo DIRECT (sin ventana)
# con una prueba de estres: 9 tandas de caminar 1.5-5 s y parar, girar a
# los dos lados y caminar otros 6 s, repetida con 4 duraciones distintas,
# mas 30 s de trote seguido. Resultados (caidas / velocidad media):
#   fuerza 35, cadera 0.20, rodilla 0.3, 1.2 Hz (los valores de antes):
#       3 caidas, y se caia tambien caminando derecho a los ~8 s
#   cadera 0.25 (con cualquier fuerza/frecuencia probada): 4-9 caidas
#       -- mas rapido (0.15-0.38 m/s) pero la zancada larga lo desbalancea
#   fuerza 60, cadera 0.20, rodilla 0.4, 1.5 Hz (los que quedaron):
#       0 caidas en las 4 variantes, 30 s derecho sin desviarse, ~0.06 m/s
# Levantar mas el pie (rodilla 0.4 en vez de 0.3) es lo que mas ayudo: con
# 0.3 la pata en el aire a veces rozaba el piso y frenaba de golpe esa
# esquina del robot. Es lento, pero es fisica real de punta a punta.
AMPLITUD_CADERA = 0.2    # cuanto se adelanta/atrasa la pata (rad)
AMPLITUD_RODILLA = 0.4   # cuanto se levanta el pie durante el avance (rad)
FRECUENCIA_TROTE = 1.5   # zancadas por segundo
FUERZA_MOTOR = 60        # torque maximo (N*m) de cada motor para seguir la pose pedida


def objetivos_trote(t, intensidad=1.0):
    """Devuelve (abduccion, cadera, rodilla) para las 4 patas en el
    instante t del reloj del trote. `intensidad` (0 a 1) escala las dos
    amplitudes: con 0 devuelve la pose de pie quieta (todas las patas
    abajo) sea cual sea t; con 1, el trote completo. En t=0 tambien
    coincide con la pose de pie (sin(0) = sin(pi) = 0)."""
    objetivos = []
    for pata in range(4):
        fase = 2 * math.pi * FRECUENCIA_TROTE * t + FASE_PATA[pata]
        cadera = OFFSET_CADERA + intensidad * AMPLITUD_CADERA * math.sin(fase)
        levantar = max(0.0, math.sin(fase))  # solo levanta el pie durante el avance, no al apoyar
        rodilla = OFFSET_RODILLA - intensidad * AMPLITUD_RODILLA * levantar
        objetivos.append((0.0, cadera, rodilla))
    return objetivos


def aplicar_pose(abd_cadera_rodilla_por_pata):
    for pata, (abduccion, cadera, rodilla) in enumerate(abd_cadera_rodilla_por_pata):
        base = pata * 3
        p.setJointMotorControl2(quadruped, JOINT_IDS[base + 0], p.POSITION_CONTROL,
                                 DIR_ABDUCCION[pata] * abduccion, force=FUERZA_MOTOR)
        p.setJointMotorControl2(quadruped, JOINT_IDS[base + 1], p.POSITION_CONTROL, cadera, force=FUERZA_MOTOR)
        p.setJointMotorControl2(quadruped, JOINT_IDS[base + 2], p.POSITION_CONTROL, rodilla, force=FUERZA_MOTOR)


caminando = False          # lo que PIDE el usuario (tecla 8 / boton Caminar)
aviso_caida_mostrado = False  # para avisar UNA vez que se cayo (ver girar_pasos)
tiempo_trote = 0.0         # reloj del CPG (solo corre mientras intensidad_trote > 0)
intensidad_trote = 0.0     # 0 = de pie quieto, 1 = trote completo; ver avanzar_trote()

PASOS_ASENTAR = 250  # ~0.5s a 500Hz

# Arrancar y frenar con rampa: la amplitud del trote sube de 0 a 1 (y
# baja de 1 a 0) en RAMPA_TROTE segundos, igual que un animal o un robot
# real que acelera y frena en unos pasos, no de golpe. Antes, soltar la
# tecla 8 saltaba en un solo paso de fisica de media zancada a la pose
# de pie (y al volver a pulsarla, de vuelta a la fase 0 del seno):
# probado en modo DIRECT, con 2-3 ciclos de soltar/pulsar el robot
# terminaba en el piso -- es un tiron de ~0.2 rad en los 8 motores de
# cadera y rodilla a la vez. Con la rampa la pose pedida es continua
# siempre, y el reloj del trote no vuelve a 0 al reanudar (no hace
# falta: con intensidad 0 cualquier fase da la misma pose de pie).
RAMPA_TROTE = 0.6
ALTURA_MIN_DE_PIE = 0.3  # el torso de pie queda a ~0.56 m; tumbado, a 0.1-0.2 m


def avanzar_trote():
    """Avanza un paso de fisica el reloj y la intensidad del trote."""
    global tiempo_trote, intensidad_trote
    delta = PASO_FISICA / RAMPA_TROTE
    if caminando:
        intensidad_trote = min(1.0, intensidad_trote + delta)
    else:
        intensidad_trote = max(0.0, intensidad_trote - delta)
    if intensidad_trote > 0:
        tiempo_trote += PASO_FISICA


def pose_trote_actual():
    return objetivos_trote(tiempo_trote, intensidad_trote)


def frenar_del_todo():
    """Corre la fisica hasta que la rampa de frenado termine (intensidad
    0, las 4 patas abajo). Se usa antes de girar, para no reorientar el
    torso con un pie en el aire."""
    global caminando
    caminando = False
    while intensidad_trote > 0:
        aplicar_pose(pose_trote_actual())
        avanzar_trote()
        p.stepSimulation()


def esta_de_pie():
    return p.getBasePositionAndOrientation(quadruped)[0][2] > ALTURA_MIN_DE_PIE


def reset_robot():
    """Ademas de reubicar al robot, lo deja PARADO Y ASENTADO en el piso
    (250 pasos de fisica sosteniendo la pose de pie) antes de devolver el
    control. Arrancar a trotar de un salto, recien cargado (sin este
    asentado), lo hacia caer casi de inmediato -- las patas todavia no
    habian hecho contacto real con el piso."""
    global caminando, tiempo_trote, intensidad_trote, aviso_caida_mostrado
    caminando = False
    aviso_caida_mostrado = False
    tiempo_trote = 0.0
    intensidad_trote = 0.0
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
    global aviso_caida_mostrado
    if not esta_de_pie():
        # reorientar un robot tumbado lo "reubica" metido en el piso y la
        # fisica lo expulsa hacia arriba (probado: salia volando a z=2 m).
        # Tirado, lo unico que tiene sentido es el reset (tecla 5). El
        # aviso sale una sola vez, no 20 veces por segundo mientras se
        # sostiene 4/6.
        if not aviso_caida_mostrado:
            print("El robot esta en el piso: usa Reset (tecla 5) antes de girar.")
            aviso_caida_mostrado = True
        return
    frenar_del_todo()
    # yaw positivo = giro ANTIHORARIO visto desde arriba = hacia la
    # IZQUIERDA (regla de la mano derecha sobre el eje Z). Por eso
    # direccion=+1 (derecha) usa un angulo NEGATIVO. Antes era al reves,
    # y 4/6 giraban al contrario de su etiqueta (medido en DIRECT:
    # "derecha" subia el rumbo de 87 a 98 grados = giraba a la izquierda).
    # El giro se aplica SOBRE la orientacion actual del torso (no se
    # reescribe un rumbo absoluto guardado): caminando, el trote se desvia
    # solo un par de grados, y pisar ese rumbo real con uno guardado seria
    # "corregirlo" a mano sin que el usuario lo pida.
    giro = p.getQuaternionFromEuler([0, 0, -direccion * PASO_GIRO * pasos])
    pos_actual, orn_actual = p.getBasePositionAndOrientation(quadruped)
    orn_nueva = p.multiplyTransforms([0, 0, 0], giro, [0, 0, 0], orn_actual)[1]
    p.resetBasePositionAndOrientation(quadruped, pos_actual, orn_nueva)
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


tecla_anterior = "-"   # ultima tecla recibida del ESP32, para detectar flancos


def procesar_tecla(tecla):
    """El ESP32 repite la tecla sostenida cada ~50 ms, asi que aca se
    distingue entre teclas "de mantener" y teclas "de un solo golpe":
      - 8: se reacciona al FLANCO (cuando se empieza a sostener y cuando
        se suelta), no a cada repeticion. Asi el boton "Caminar" de la
        ventana tambien sirve con el ESP32 conectado: antes cada
        "TECLA:-" (20 por segundo) ponia caminando=False y anulaba el click.
      - 4/6: cada repeticion gira un paso (sostener = seguir girando).
      - 5: solo en el flanco (sostenerla no reinicia 20 veces por segundo).
    Girar SIEMPRE detiene el trote primero (ver girar_pasos): combinar
    las dos cosas es lo que hacia caer al robot en las pruebas."""
    global caminando, tecla_anterior
    anterior, tecla_anterior = tecla_anterior, tecla
    if tecla == "8" and anterior != "8":
        caminando = esta_de_pie()
    elif anterior == "8" and tecla != "8":
        caminando = False           # avanzar_trote() frena con rampa, no en seco
    if tecla == "4":
        girar_pasos(-1)
    elif tecla == "6":
        girar_pasos(1)
    elif tecla == "5" and anterior != "5":
        reset_robot()


# Ultima linea CRUDA recibida del ESP32, escrita en la propia ventana:
# si nunca cambia, el ESP32 no esta mandando nada; si cambia pero no es
# "TECLA:x", el problema es de formato, no de cable.
ultima_linea_cruda = None
POS_TEXTO_SERIAL = [0, 0, 1.0]
id_texto_serial = p.addUserDebugText("ESP32: " + ("esperando datos..." if ser else "no conectado (usa los botones)"),
                                     POS_TEXTO_SERIAL, textColorRGB=[1, 1, 0.4], textSize=1.2)

print("Ventana de PyBullet abierta. Cierra la ventana o Ctrl+C en la terminal para salir.")

while True:
    # teclado fisico (ESP32): llega "TECLA:x" sin parar. Se lee solo si
    # YA hay datos esperando (in_waiting) para no bloquear la simulacion
    # -- ver la explicacion en brazo_pybullet.py -- y se drena TODO el
    # buffer (while, no if): un giro corre 80 pasos de fisica por linea,
    # y leyendo una sola linea por vuelta se irian acumulando atrasadas.
    try:
        while ser is not None and ser.in_waiting:
            linea = ser.readline().decode(errors="ignore").strip()
            if linea != ultima_linea_cruda:
                ultima_linea_cruda = linea
                p.addUserDebugText("ESP32: " + linea, POS_TEXTO_SERIAL, textColorRGB=[1, 1, 0.4],
                                   textSize=1.2, replaceItemUniqueId=id_texto_serial)
            if linea.startswith("TECLA:"):
                procesar_tecla(linea.split(":", 1)[1])
    except serial.SerialException:
        print("Se perdio la conexion con el ESP32: sigue con los botones de la ventana.")
        ser = None

    # botones de la ventana: "Caminar" alterna on/off con cada click (no
    # se puede "sostener" un click en addUserDebugParameter), "Girar" gira
    # un paso fijo por click -- se leen SIEMPRE, no solo sin ESP32.
    for nombre, boton in botones.items():
        contador = p.readUserDebugParameter(boton)
        if contador != contadores_anteriores[nombre]:
            contadores_anteriores[nombre] = contador
            if nombre == "caminar":
                caminando = (not caminando) and esta_de_pie()
            elif nombre == "izquierda":
                girar_pasos(-1, pasos=10)   # 10 pasos = 0.15 rad = ~9 grados por click
            elif nombre == "derecha":
                girar_pasos(1, pasos=10)
            elif nombre == "reset":
                reset_robot()

    # red de seguridad: caminar y girar son fisica real (nada de trucos),
    # asi que -- igual que un robot de verdad -- se puede llegar a caer si
    # se encadenan muchos giros grandes seguidos. Si eso pasa, se deja de
    # insistir en caminar (que solo lo arrastraria panza abajo) y se
    # espera al reset en vez de intentar seguir.
    if not esta_de_pie():
        caminando = False

    # caminar: trote real generado con senos (objetivos_trote), con
    # fisica de verdad empujando al robot -- no se teletransporta nada.
    # Parado (intensidad 0), la pose pedida es la de pie quieta, las 4
    # patas abajo; al arrancar/frenar, la amplitud sube/baja con rampa.
    aplicar_pose(pose_trote_actual())
    avanzar_trote()

    p.stepSimulation()
    time.sleep(PASO_FISICA)
