# Mueve el brazo de brazo.urdf para "dibujar" el digito recibido del
# ESP32 (esp32_teclado_lcd.py) por UART, trazando su recorrido con
# lineas de depuracion de PyBullet. Igual que en el tema 7, si no hay
# ESP32 conectado el script sigue funcionando: 10 botones (uno por
# digito) lo dibujan sin necesidad de hardware.
#
# Ajustar PUERTO_SERIAL segun el puerto que use el ESP32 en el
# Administrador de dispositivos, por ejemplo "COM7" en Windows o
# "/dev/ttyUSB0" en Linux.

import time

import pybullet as p
import pybullet_data
import serial

PUERTO_SERIAL = "COM7"
BAUDIOS = 115200

try:
    ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.05)
    time.sleep(2)  # da tiempo a que el ESP32 termine de reiniciar tras abrir el puerto
    print(f"ESP32 conectado en {PUERTO_SERIAL}: se dibuja cada digito que llegue del teclado.")
except serial.SerialException:
    ser = None
    print(f"No se encontro el ESP32 en {PUERTO_SERIAL}: usa los botones 0-9 de la ventana.")

# ------------------------------------------------------------------
# Trazos de cada digito, como una lista de puntos (u, v) en un
# cuadrado unitario (u = horizontal 0..1, v = vertical 0..1, v=1
# arriba). Son trazos de un solo recorrido (como si nunca se
# levantara el lapiz), simplificados para que el brazo los pueda
# seguir de corrido: no son una tipografia real, solo una
# aproximacion reconocible de cada digito.
# ------------------------------------------------------------------
TRAZOS_DIGITOS = {
    "0": [(0.2, 0), (0, 0.2), (0, 0.8), (0.2, 1), (0.8, 1), (1, 0.8), (1, 0.2), (0.2, 0)],
    "1": [(0.3, 0.8), (0.5, 1), (0.5, 0)],
    "2": [(0, 0.8), (0.3, 1), (0.7, 1), (1, 0.8), (1, 0.55), (0, 0.2), (0, 0), (1, 0)],
    "3": [(0, 1), (1, 1), (0.5, 0.55), (1, 0.15), (0.6, 0), (0.1, 0.1)],
    "4": [(0.7, 0), (0.7, 1), (0, 0.35), (1, 0.35)],
    "5": [(1, 1), (0, 1), (0, 0.55), (0.8, 0.55), (1, 0.35), (0.8, 0), (0, 0.1)],
    "6": [(0.9, 0.9), (0.3, 1), (0, 0.6), (0, 0.2), (0.3, 0), (0.7, 0), (1, 0.25), (0.7, 0.5), (0.2, 0.5)],
    "7": [(0, 1), (1, 1), (0.4, 0)],
    "8": [(0.5, 0.5), (0.2, 0.65), (0.2, 0.9), (0.5, 1), (0.8, 0.9), (0.8, 0.65), (0.5, 0.5),
          (0.2, 0.35), (0.2, 0.1), (0.5, 0), (0.8, 0.1), (0.8, 0.35), (0.5, 0.5)],
    "9": [(0.3, 0.1), (0.7, 0), (1, 0.35), (1, 0.75), (0.7, 1), (0.3, 0.9), (0.3, 0.5), (0.8, 0.5)],
}

# joint_1 (giro de la base) y joint_2 (codo) no describen un plano
# cartesiano: joint_1 es un giro acimutal sobre Z y joint_2 es una
# inclinacion sobre Y en el extremo del primer brazo, asi que la punta
# del brazo (sin contar la pinza) solo puede tocar los puntos de una
# ESFERA centrada en el codo (radio = largo de brazo2). Un mapeo
# u,v -> joint_1,joint_2 con un rango amplio (como se hizo al
# principio) deforma mucho los digitos, porque intenta estirar un
# dibujo plano sobre una superficie curva.
#
# La solucion: usar un rango de angulos CHICO (unos pocos grados a
# cada lado), centrado en una pose comoda y lejos de posiciones
# degeneradas (con el codo doblado, no estirado). En un parche chico
# de esfera la curvatura casi no se nota, asi que el mapeo lineal
# u,v -> joint_1,joint_2 sale casi plano — igual que un mapa de una
# ciudad no se ve deformado aunque la Tierra sea una esfera. Ademas,
# cada segmento del trazo se subdivide en varios puntos intermedios
# (DENSIFICAR) para que la interpolacion entre ellos siga de cerca la
# linea recta original, en vez de "cortar camino" por la curvatura.
CENTRO_J1 = 0.0
CENTRO_J2 = 1.0   # codo doblado ~57°, lejos del "brazo estirado" (0) y de los limites
RANGO_J1 = 0.35   # radianes a cada lado del centro (limite real de joint_1: 2.5)
RANGO_J2 = 0.35   # radianes a cada lado del centro (limite real de joint_2: 2.0)
PUNTOS_POR_TRAMO = 8  # subdivisiones entre cada dos puntos del trazo original


def angulos_articulaciones(u, v):
    j1 = CENTRO_J1 + (u - 0.5) * 2 * RANGO_J1
    j2 = CENTRO_J2 + (v - 0.5) * 2 * RANGO_J2
    return j1, j2


def densificar(trazo):
    """Agrega puntos intermedios (interpolados en u,v) entre cada par
    de puntos consecutivos del trazo original."""
    denso = [trazo[0]]
    for (u0, v0), (u1, v1) in zip(trazo, trazo[1:]):
        for i in range(1, PUNTOS_POR_TRAMO + 1):
            t = i / PUNTOS_POR_TRAMO
            denso.append((u0 + (u1 - u0) * t, v0 + (v1 - v0) * t))
    return denso


physics_client = p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
p.loadURDF("plane.urdf")
robot_id = p.loadURDF("brazo.urdf", [0, 0, 0.15], useFixedBase=True)

indices = {}
for i in range(p.getNumJoints(robot_id)):
    nombre = p.getJointInfo(robot_id, i)[1].decode("utf-8")
    indices[nombre] = i

EFECTOR = indices["joint_gripper"]  # extremo del segundo brazo, ahi "esta" el lapiz

# la camara arranca mirando de frente la zona donde se dibuja (no desde
# arriba): con joint_2 doblado, ahi es donde se ve el digito sin
# deformarse por la perspectiva
p.resetDebugVisualizerCamera(cameraDistance=0.6, cameraYaw=0, cameraPitch=-10, cameraTargetPosition=[0.25, 0, 0.8])

p.addUserDebugText("Presiona un boton 0-9 (o el teclado fisico) para dibujar ese digito",
                    [0.0, 0.0, 1.15], textColorRGB=[1, 1, 1], textSize=1.3)

# un boton por digito (0-9): en vez de un slider + "Dibujar" aparte,
# cada boton dibuja su digito directo al apretarlo
botones_digitos = {str(d): p.addUserDebugParameter(str(d), 1, 0, 0) for d in range(10)}
contadores_anteriores = {digito: 0 for digito in botones_digitos}

# el trazo no se dibuja justo en el origen del link (que queda ADENTRO
# del bloque de la pinza), sino un poco mas alla, a lo largo de su
# propio eje Z: asi el trazo se ve como una punta de lapiz saliendo de
# la pinza, separado de su geometria, en vez de enterrado dentro de
# ella y tapado por los bloques rojo/gris.
OFFSET_PLUMA = [0, 0, 0.09]


def punto_pluma():
    pos_link, orn_link = p.getLinkState(robot_id, EFECTOR, computeForwardKinematics=True)[4:6]
    punto_mundo, _ = p.multiplyTransforms(pos_link, orn_link, OFFSET_PLUMA, [0, 0, 0, 1])
    return punto_mundo


def mover_a(u, v):
    j1, j2 = angulos_articulaciones(u, v)
    p.setJointMotorControl2(robot_id, indices["joint_1"], p.POSITION_CONTROL, targetPosition=j1)
    p.setJointMotorControl2(robot_id, indices["joint_2"], p.POSITION_CONTROL, targetPosition=j2)
    for _ in range(6):
        p.stepSimulation()
        time.sleep(1 / 240)


ids_trazo_actual = []  # lineas de depuracion del ultimo digito dibujado


def borrar_trazo_anterior():
    for id_linea in ids_trazo_actual:
        p.removeUserDebugItem(id_linea)
    ids_trazo_actual.clear()


def dibujar_digito(digito):
    trazo = TRAZOS_DIGITOS.get(digito)
    if trazo is None:
        print(f"'{digito}' no es un digito 0-9, se ignora.")
        return

    # se borra el trazo del digito anterior antes de dibujar el nuevo;
    # si no, se van acumulando uno sobre otro y no se entiende ninguno
    borrar_trazo_anterior()

    print(f"Dibujando el digito {digito}...")
    punto_anterior = None
    for u, v in densificar(trazo):
        mover_a(u, v)
        punto_actual = punto_pluma()
        if punto_anterior is not None:
            id_linea = p.addUserDebugLine(punto_anterior, punto_actual, lineColorRGB=[1, 1, 0], lineWidth=6, lifeTime=0)
            ids_trazo_actual.append(id_linea)
        punto_anterior = punto_actual
    print("Listo.")


print("Ventana de PyBullet abierta. Cierra la ventana o Ctrl+C en la terminal para salir.")

while True:
    # digito que llega del ESP32 (teclado fisico)
    if ser is not None:
        linea = ser.readline().decode(errors="ignore").strip()
        if linea.startswith("DIGIT:"):
            dibujar_digito(linea.split(":", 1)[1])

    # digito elegido a mano con los botones, sin necesidad de ESP32
    for digito, boton in botones_digitos.items():
        contador = p.readUserDebugParameter(boton)
        if contador != contadores_anteriores[digito]:
            contadores_anteriores[digito] = contador
            dibujar_digito(digito)

    p.stepSimulation()
    time.sleep(1 / 240)
