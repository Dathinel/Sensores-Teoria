# Simula el brazo de brazo.urdf en PyBullet y lo mueve con los datos
# reales del ESP32 (esp32_brazo.py: solo el teclado matricial, sin
# potenciometro ni ningun sensor analogico) leidos por el puerto
# serial, o con los mismos botones de jog pero dentro de la propia
# ventana de PyBullet cuando no hay ESP32 conectado.
#
# Ajustar PUERTO_SERIAL segun el puerto que use el ESP32 en el
# Administrador de dispositivos, por ejemplo "COM7" en Windows o
# "/dev/ttyUSB0" en Linux. Si el puerto no existe o no responde, el
# script sigue funcionando solo con los botones.

import re
import time

import pybullet as p
import pybullet_data
import serial

PUERTO_SERIAL = "COM7"
BAUDIOS = 115200

try:
    ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.05)
    time.sleep(2)  # da tiempo a que el ESP32 termine de reiniciar tras abrir el puerto
    print(f"ESP32 conectado en {PUERTO_SERIAL}: usando los datos reales de los sensores.")
except serial.SerialException:
    ser = None
    print(f"No se encontro el ESP32 en {PUERTO_SERIAL}: se usan los sliders de PyBullet.")

PATRON_LINEA = re.compile(r"J1:(-?[\d.]+),J2:(-?[\d.]+),G:(-?[\d.]+)")


def leer_esp32():
    """Devuelve (j1, j2, g) leidos del ESP32, o None si no hay linea valida."""
    if ser is None:
        return None
    linea = ser.readline().decode(errors="ignore").strip()
    coincidencia = PATRON_LINEA.match(linea)
    if not coincidencia:
        return None
    j1, j2, g = (float(valor) for valor in coincidencia.groups())
    return j1, j2, g


physics_client = p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
p.loadURDF("plane.urdf")
robot_id = p.loadURDF("brazo.urdf", [0, 0, 0.15], useFixedBase=True)

# los indices de articulacion se leen del propio URDF en vez de asumir un
# orden fijo, por si brazo.urdf llega a cambiar
indices = {}
for i in range(p.getNumJoints(robot_id)):
    nombre = p.getJointInfo(robot_id, i)[1].decode("utf-8")
    indices[nombre] = i

p.resetDebugVisualizerCamera(cameraDistance=0.9, cameraYaw=40, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.5])
p.addUserDebugText(
    "Teclado fisico: 8/2=joint_1  6/4=joint_2  9/7=pinza  5=home  |  sin ESP32: usa los botones",
    [-0.3, 0.0, 1.0], textColorRGB=[1, 1, 1], textSize=1.2,
)

# mismo esquema de jog que esp32_brazo.py: cada boton mueve UN paso
# fijo a la articulacion correspondiente. Son botones fijos, creados
# una sola vez (nunca se recrean ni se borran), asi que no hay riesgo
# de que se acumulen sliders viejos en el panel.
LIMITES_LOCAL = {"j1": (-2.5, 2.5), "j2": (-2.0, 2.0), "g": (0.0, 0.15)}
PASO_LOCAL = {"j1": 0.05, "j2": 0.05, "g": 0.005}

botones_jog = {
    "j1+": p.addUserDebugParameter("joint_1 (base) +", 1, 0, 0),
    "j1-": p.addUserDebugParameter("joint_1 (base) -", 1, 0, 0),
    "j2+": p.addUserDebugParameter("joint_2 (codo) +", 1, 0, 0),
    "j2-": p.addUserDebugParameter("joint_2 (codo) -", 1, 0, 0),
    "g+": p.addUserDebugParameter("pinza +", 1, 0, 0),
    "g-": p.addUserDebugParameter("pinza -", 1, 0, 0),
    "home": p.addUserDebugParameter("Home (0, 0, 0)", 1, 0, 0),
}
contadores_anteriores = {nombre: 0 for nombre in botones_jog}
valores_locales = {"j1": 0.0, "j2": 0.0, "g": 0.0}


def limitar(valor, limite):
    minimo, maximo = limite
    return max(minimo, min(maximo, valor))


print("Ventana de PyBullet abierta. Cierra la ventana o Ctrl+C en la terminal para salir.")

while True:
    dato_esp32 = leer_esp32()
    if dato_esp32 is not None:
        j1, j2, g = dato_esp32
    else:
        for nombre, boton in botones_jog.items():
            contador = p.readUserDebugParameter(boton)
            if contador != contadores_anteriores[nombre]:
                contadores_anteriores[nombre] = contador
                if nombre == "home":
                    valores_locales = {"j1": 0.0, "j2": 0.0, "g": 0.0}
                else:
                    articulacion, signo = nombre[:-1], nombre[-1]
                    paso = PASO_LOCAL[articulacion] * (1 if signo == "+" else -1)
                    valores_locales[articulacion] = limitar(
                        valores_locales[articulacion] + paso, LIMITES_LOCAL[articulacion]
                    )
        j1, j2, g = valores_locales["j1"], valores_locales["j2"], valores_locales["g"]

    p.setJointMotorControl2(robot_id, indices["joint_1"], p.POSITION_CONTROL, targetPosition=j1)
    p.setJointMotorControl2(robot_id, indices["joint_2"], p.POSITION_CONTROL, targetPosition=j2)
    p.setJointMotorControl2(robot_id, indices["joint_gripper"], p.POSITION_CONTROL, targetPosition=g)
    # las dos puntas de la pinza se abren en proporcion a "g": el maximo de
    # cada una (0.05) es exactamente un tercio del maximo de joint_gripper (0.15)
    p.setJointMotorControl2(robot_id, indices["joint_dedo_izq"], p.POSITION_CONTROL, targetPosition=g / 3)
    p.setJointMotorControl2(robot_id, indices["joint_dedo_der"], p.POSITION_CONTROL, targetPosition=g / 3)

    p.stepSimulation()
    time.sleep(1 / 240)
