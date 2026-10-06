# Simula el brazo de brazo.urdf en PyBullet y lo mueve con los datos
# reales del ESP32 (esp32_brazo.py: solo el teclado matricial, sin
# potenciometro ni ningun sensor analogico) leidos por el puerto
# serial, o con los mismos botones de jog pero dentro de la propia
# ventana de PyBullet cuando no hay ESP32 conectado.
#
# Ajustar PUERTO_SERIAL segun el puerto que use el ESP32 en el
# Administrador de dispositivos, por ejemplo "COM7" en Windows o
# "/dev/ttyUSB0" en Linux (o pasarlo al correrlo, sin tocar el archivo:
# "python brazo_pybullet.py COM5"). Si el puerto no existe o no
# responde, el script sigue funcionando solo con los botones; y si el
# ESP32 se desenchufa a mitad de la simulacion, tampoco se cae: sigue
# con los botones e intenta volver a abrir el puerto cada pocos segundos.

import os
import re
import sys
import time

import pybullet as p
import pybullet_data
import serial

# El puerto se puede pasar como primer argumento; si no, COM7 (el de la
# placa con la que se armo el tema).
PUERTO_SERIAL = sys.argv[1] if len(sys.argv) > 1 else "COM7"
BAUDIOS = 115200  # tiene que coincidir con el del ESP32 (115200 es el de la consola USB de MicroPython)
REINTENTO_S = 3.0  # cada cuanto se vuelve a probar el puerto si el ESP32 se desenchufo

# ------------------------------------------------------------------
# Conexion con el ESP32 (opcional)
# ------------------------------------------------------------------
# Se intenta abrir el puerto dentro de un try: si el ESP32 no esta
# conectado (o el puerto lo tiene ocupado Thonny), el script NO se cae,
# solo avisa y sigue con los botones de la ventana. Asi se puede
# mostrar la simulacion sin tener el hardware a la mano.
try:
    # timeout=0: readline() nunca se queda esperando. Igual solo se lee
    # cuando in_waiting > 0 (ver leer_esp32), pero asi queda doblemente
    # garantizado que la lectura serial no frena la simulacion.
    ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0)
    # Abrir el puerto baja la linea DTR y eso reinicia el ESP32; se le da
    # tiempo a que vuelva a arrancar main.py antes de empezar a leer.
    time.sleep(2)
    ser.reset_input_buffer()  # descarta el texto de arranque de MicroPython
    print(f"ESP32 conectado en {PUERTO_SERIAL}: usando los datos reales del teclado.")
except serial.SerialException:
    ser = None
    print(f"No se encontro el ESP32 en {PUERTO_SERIAL}: se usan los botones de jog de PyBullet.")

# Solo si el ESP32 estaba conectado al empezar se intenta reconectarlo
# cuando se pierde (cable desenchufado, placa reiniciada a mano...). Sin
# ESP32 desde el principio el script no vuelve a tocar el puerto: asi el
# modo "solo botones" queda exactamente igual que siempre.
reconectar = ser is not None
proximo_intento = 0.0

# Formato exacto que imprime esp32_brazo.py: "J1:0.150,J2:-0.300,G:0.020".
# -?[\d.]+ acepta numeros con signo y decimales.
PATRON_LINEA = re.compile(r"J1:(-?[\d.]+),J2:(-?[\d.]+),G:(-?[\d.]+)")

# Lo que llega por serial no siempre viene en lineas completas: un
# pedazo puede llegar en una lectura y el resto en la siguiente. Se
# acumula aqui hasta que aparezca el "\n" que cierra la linea.
buffer_serial = b""
ultima_linea_cruda = "(sin datos todavia)"


def perder_esp32(error):
    """El puerto dejo de responder (ESP32 desenchufado): pasa a modo botones.

    pyserial avisa con SerialException (o un OSError del sistema) en la
    primera operacion sobre un puerto que ya no existe, normalmente
    in_waiting. Sin esto, desenchufar la placa a mitad de la simulacion
    tumbaria todo el script con un traceback.
    """
    global ser, buffer_serial, ultima_linea_cruda, proximo_intento
    print(f"Se perdio el ESP32 en {PUERTO_SERIAL} ({error.__class__.__name__}): "
          "se siguen usando los botones de jog; se reintenta cada "
          f"{REINTENTO_S:.0f} s.")
    try:
        ser.close()
    except Exception:
        pass  # el puerto ya no existe: cerrarlo puede fallar y da igual
    ser = None
    buffer_serial = b""
    ultima_linea_cruda = f"ESP32 desconectado: modo botones (reintentando {PUERTO_SERIAL})"
    proximo_intento = time.monotonic() + REINTENTO_S


def intentar_reconectar():
    """Si el ESP32 se perdio, prueba a abrir de nuevo el puerto (sin bloquear).

    Abrir un COM que no existe falla en milisegundos, asi que probar cada
    REINTENTO_S segundos no frena la simulacion. Al reabrir NO se espera
    los 2 s del arranque: el texto de arranque de MicroPython no cumple el
    patron J1/J2/G y simplemente se ignora. Ojo: abrir el puerto reinicia
    el ESP32 (DTR), asi que la placa vuelve a empezar en 0, 0, 0.
    """
    global ser, proximo_intento, ultima_linea_cruda
    if ser is not None or not reconectar or time.monotonic() < proximo_intento:
        return
    proximo_intento = time.monotonic() + REINTENTO_S
    try:
        ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0)
    except (serial.SerialException, OSError):
        return  # sigue desenchufado: se vuelve a probar en REINTENTO_S
    ultima_linea_cruda = "(reconectado, esperando datos)"
    print(f"ESP32 reconectado en {PUERTO_SERIAL}: vuelven a mandar los datos del teclado.")


def leer_esp32():
    """Devuelve (j1, j2, g) de la ULTIMA linea valida que haya llegado, o None.

    Nunca bloquea: solo lee lo que ya esta en el buffer del puerto
    (in_waiting). Un readline() "a secas" con timeout dentro del bucle
    de la simulacion la frenaria a la velocidad a la que llegan los
    datos del ESP32 (~10 lineas/s) en vez de los 240 pasos/s de la
    fisica, y el brazo se veria trabado.
    """
    global buffer_serial, ultima_linea_cruda
    intentar_reconectar()
    if ser is None:
        return None
    try:
        esperando = ser.in_waiting
        if esperando == 0:
            return None
        # Drena TODO lo acumulado de una vez: si solo se leyera una linea por
        # vuelta, las lineas se irian apilando y el brazo reaccionaria con
        # cada vez mas retraso respecto al teclado.
        buffer_serial += ser.read(esperando)
    except (serial.SerialException, OSError) as error:
        perder_esp32(error)
        return None
    *lineas_completas, buffer_serial = buffer_serial.split(b"\n")

    ultimo_valido = None
    for linea_bytes in lineas_completas:
        linea = linea_bytes.decode(errors="ignore").strip()
        if not linea:
            continue
        ultima_linea_cruda = linea
        coincidencia = PATRON_LINEA.match(linea)
        if coincidencia:
            # Solo importa la mas reciente: es la posicion actual del jog.
            # (float() de algo como "1.2.3" fallaria: se descarta esa linea.)
            try:
                ultimo_valido = tuple(float(valor) for valor in coincidencia.groups())
            except ValueError:
                pass
    return ultimo_valido


# ------------------------------------------------------------------
# Mundo de PyBullet
# ------------------------------------------------------------------
physics_client = p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())  # de ahi sale plane.urdf
p.setGravity(0, 0, -9.8)
p.loadURDF("plane.urdf")
# useFixedBase=True: la base queda atornillada al piso; si no, al mover
# el brazo el conjunto entero se volcaria por su propio peso.
# Ruta absoluta (la carpeta de este script) en vez de solo "brazo.urdf":
# asi el URDF se encuentra aunque el script se lance desde otra carpeta
# (por ejemplo desde el lanzador de la raiz del repo o con doble clic).
RUTA_URDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brazo.urdf")
robot_id = p.loadURDF(RUTA_URDF, [0, 0, 0.15], useFixedBase=True)

# Los indices y los limites de cada articulacion se leen del propio URDF
# en vez de copiarlos a mano: si brazo.urdf cambia, este script se
# adapta solo. getJointInfo devuelve el nombre en [1] y el <limit>
# lower/upper en [8] y [9].
indices = {}
limites_urdf = {}
for i in range(p.getNumJoints(robot_id)):
    info = p.getJointInfo(robot_id, i)
    nombre = info[1].decode("utf-8")
    indices[nombre] = i
    limites_urdf[nombre] = (info[8], info[9])

p.resetDebugVisualizerCamera(cameraDistance=0.9, cameraYaw=40, cameraPitch=-30, cameraTargetPosition=[0, 0, 0.5])
p.addUserDebugText(
    "Teclado fisico: 8/2=joint_1  6/4=joint_2  9/7=pinza  5=home  |  sin ESP32: usa los botones",
    [-0.3, 0.0, 1.0], textColorRGB=[1, 1, 1], textSize=1.2,
)
# Diagnostico: ultima linea CRUDA que llego del ESP32 (tal cual, sin
# interpretar). Si nunca cambia, el ESP32 no esta mandando nada; si
# cambia pero no es "J1:..,J2:..,G:..", el problema es de formato.
id_texto_serial = p.addUserDebugText(
    "Serial: " + ("sin ESP32 (modo botones)" if ser is None else ultima_linea_cruda),
    [-0.3, 0.0, 0.93], textColorRGB=[0.6, 0.9, 0.6], textSize=1.0,
)
texto_serial_mostrado = None

# Mismo esquema de jog que esp32_brazo.py: cada boton mueve UN paso
# fijo a la articulacion correspondiente. Son botones fijos, creados
# una sola vez (nunca se recrean ni se borran), asi que no hay riesgo
# de que se acumulen sliders viejos en el panel (removeUserDebugItem no
# borra bien los parametros de depuracion).
LIMITES_LOCAL = {
    "j1": limites_urdf["joint_1"],        # (-2.5, 2.5) rad
    "j2": limites_urdf["joint_2"],        # (-2.0, 2.0) rad
    "g": limites_urdf["joint_gripper"],   # (0.0, 0.15) m
}
# Mismos pasos que el ESP32 (PASO_J1, PASO_J2, PASO_G): 0.05 rad son
# ~2.9 grados por click, fino pero sin tener que dar cien clicks.
PASO_LOCAL = {"j1": 0.05, "j2": 0.05, "g": 0.005}

# addUserDebugParameter con min=1 y max=0 (min > max) es la forma de
# PyBullet de crear un BOTON en vez de un slider; su "valor" es un
# contador que sube en 1 cada vez que se hace click.
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

# Posicion objetivo actual del brazo. La actualizan tanto las lineas del
# ESP32 como los botones: asi el brazo nunca "salta" entre dos fuentes
# distintas (con el ESP32 conectado, en las vueltas en que no llega
# linea se mantiene la ultima posicion recibida, no se vuelve a 0).
valores = {"j1": 0.0, "j2": 0.0, "g": 0.0}


def limitar(valor, limite):
    minimo, maximo = limite
    return max(minimo, min(maximo, valor))


def leer_botones():
    """Aplica los clicks nuevos de los botones de jog sobre `valores`."""
    for nombre, boton in botones_jog.items():
        contador = p.readUserDebugParameter(boton)
        if contador == contadores_anteriores[nombre]:
            continue
        # Si se hicieron varios clicks entre dos vueltas, se aplican todos.
        clicks = int(round(contador - contadores_anteriores[nombre]))
        contadores_anteriores[nombre] = contador
        if nombre == "home":
            valores.update(j1=0.0, j2=0.0, g=0.0)
        else:
            articulacion, signo = nombre[:-1], nombre[-1]
            paso = PASO_LOCAL[articulacion] * clicks * (1 if signo == "+" else -1)
            valores[articulacion] = limitar(valores[articulacion] + paso, LIMITES_LOCAL[articulacion])


print("Ventana de PyBullet abierta. Cierra la ventana o Ctrl+C en la terminal para salir.")

try:
    # p.isConnected() pasa a False cuando se cierra la ventana: el script
    # termina limpio en vez de tirar un error en la siguiente llamada
    # (y si se cierra justo a mitad de una vuelta, ver "except p.error").
    while p.isConnected():
        dato_esp32 = leer_esp32()
        if dato_esp32 is not None:
            # El ESP32 es la fuente "de verdad" cuando manda algo: su
            # posicion reemplaza a la local.
            valores["j1"], valores["j2"], valores["g"] = dato_esp32
        leer_botones()
        j1, j2, g = valores["j1"], valores["j2"], valores["g"]

        # Solo se reescribe el texto cuando cambia: recrearlo 240 veces
        # por segundo haria parpadear la ventana.
        # (Solo si el ESP32 estuvo conectado alguna vez: sin el, el texto
        # se queda en "sin ESP32 (modo botones)" desde el principio.)
        if reconectar and ultima_linea_cruda != texto_serial_mostrado:
            texto_serial_mostrado = ultima_linea_cruda
            id_texto_serial = p.addUserDebugText(
                "Serial: " + ultima_linea_cruda, [-0.3, 0.0, 0.93],
                textColorRGB=[0.6, 0.9, 0.6], textSize=1.0, replaceItemUniqueId=id_texto_serial,
            )

        # POSITION_CONTROL: se le da a cada motor un angulo/posicion
        # objetivo y PyBullet calcula la fuerza para llegar ahi (limitada
        # por el effort del URDF), en vez de teletransportar el link.
        p.setJointMotorControl2(robot_id, indices["joint_1"], p.POSITION_CONTROL, targetPosition=j1)
        p.setJointMotorControl2(robot_id, indices["joint_2"], p.POSITION_CONTROL, targetPosition=j2)
        p.setJointMotorControl2(robot_id, indices["joint_gripper"], p.POSITION_CONTROL, targetPosition=g)
        # Las dos puntas de la pinza se abren en proporcion a "g": el maximo
        # de cada una (0.05) es exactamente un tercio del maximo de
        # joint_gripper (0.15), asi que g/3 las lleva de cerradas a abiertas
        # al mismo ritmo que la extension, con una sola variable de control.
        p.setJointMotorControl2(robot_id, indices["joint_dedo_izq"], p.POSITION_CONTROL, targetPosition=g / 3)
        p.setJointMotorControl2(robot_id, indices["joint_dedo_der"], p.POSITION_CONTROL, targetPosition=g / 3)

        p.stepSimulation()
        time.sleep(1 / 240)  # 240 Hz es el paso de tiempo por defecto de PyBullet: va a tiempo real
except KeyboardInterrupt:
    pass
except p.error:
    # Si la ventana se cierra justo en medio de una vuelta (despues del
    # isConnected() de arriba), la siguiente llamada a PyBullet tira
    # "Not connected to physics server". No es un fallo: es la salida.
    # Cualquier otro error de PyBullet (con la ventana todavia abierta)
    # se deja ver tal cual, para no esconder un fallo de verdad.
    if p.isConnected():
        raise
finally:
    if ser is not None:
        try:
            ser.close()  # libera el COM para que Thonny u otro programa lo puedan abrir
        except (serial.SerialException, OSError):
            pass  # el ESP32 ya no estaba: no hay nada que liberar
    print("Simulacion terminada.")
