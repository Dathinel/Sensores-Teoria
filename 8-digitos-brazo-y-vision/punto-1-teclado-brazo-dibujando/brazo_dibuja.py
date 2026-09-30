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

# Patron "sin necesidad de estar conectado": se INTENTA abrir el puerto,
# y si no hay ESP32 (o el COM es otro) no se truena el programa, se sigue
# con ser = None y los botones de la ventana hacen de teclado.
try:
    # timeout=0.05: por si alguna vez se llama readline() con una linea a
    # medio llegar, que no se quede colgado mas de 50 ms. En el bucle
    # principal igual solo se lee cuando ya hay bytes esperando (ver
    # leer_serial()), asi que este timeout casi nunca entra en juego.
    ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.05)
    # Abrir el puerto mueve la linea DTR del adaptador USB-serial y eso
    # REINICIA el ESP32; durante ~1-2 s esta arrancando y no manda nada.
    time.sleep(2)
    print(f"ESP32 conectado en {PUERTO_SERIAL}: se dibuja cada digito que llegue del teclado.")
except serial.SerialException as error:
    ser = None
    # Se muestra el motivo real: "Acceso denegado" / PermissionError casi
    # siempre significa que OTRO programa tiene el puerto abierto (Thonny
    # conectado a la placa, u otra copia de este script): Windows deja
    # abrir un COM a un solo programa a la vez. "No se encuentra el
    # archivo" significa que ese COM no existe (otro numero de puerto u
    # otro PC): se listan los que si hay para corregir PUERTO_SERIAL.
    import serial.tools.list_ports
    print(f"No se pudo abrir {PUERTO_SERIAL}: {error}")
    if "denegado" in str(error).lower() or "permission" in str(error).lower():
        print("  -> el puerto esta ocupado: cierra Thonny (o desconectalo con Stop) y vuelve a correr esto.")
    puertos = [f"{x.device} ({x.description})" for x in serial.tools.list_ports.comports()]
    print("  Puertos disponibles:", ", ".join(puertos) if puertos else "ninguno")
    print("Sigue sin ESP32: usa los botones 0-9 de la ventana.")

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
    """Pasa un punto (u, v) del cuadrado unitario a los dos angulos del
    brazo. (u - 0.5) va de -0.5 a 0.5; por 2 * RANGO queda de -RANGO a
    +RANGO alrededor del centro: u = 0 es el borde izquierdo del dibujo
    (base girada -RANGO_J1), u = 1 el derecho; v = 0 abajo, v = 1 arriba.
    Ojo con el signo de v: doblar MAS el codo (j2 mayor) BAJA la punta, asi
    que para que v = 1 quede arriba hay que RESTAR. Con el signo al reves
    (lo que teniamos antes) cada digito salia reflejado de arriba a abajo:
    el 7 parecia una L invertida y el 2 una S."""
    j1 = CENTRO_J1 + (u - 0.5) * 2 * RANGO_J1
    j2 = CENTRO_J2 - (v - 0.5) * 2 * RANGO_J2
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
# deformarse por la perspectiva. yaw=90 la pone del lado +X mirando hacia
# el brazo: el ancho del digito (el giro de la base) queda de izquierda a
# derecha en pantalla. Con yaw=0 la camara miraba a lo largo de ese ancho
# y veia el digito de canto, como un garabato.
p.resetDebugVisualizerCamera(cameraDistance=0.95, cameraYaw=90, cameraPitch=-15, cameraTargetPosition=[0.28, 0, 0.8])

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
    # 6 pasos de fisica por punto: el motor de posicion de PyBullet no
    # llega al angulo pedido en un solo paso, necesita unos cuantos. Con
    # 8 puntos por tramo el objetivo cambia muy poco de un punto a otro,
    # asi que 6 pasos (~25 ms simulados) alcanzan para que la punta lo
    # siga de cerca sin que el dibujo se haga eterno. time.sleep(1/240)
    # hace que eso se vea a velocidad real (PyBullet simula a 240 Hz).
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


# ------------------------------------------------------------------
# Lectura serial SIN bloquear la simulacion
# ------------------------------------------------------------------
# Un ser.readline() "a secas" dentro del bucle principal se queda
# esperando hasta el timeout cada vez que no hay nada nuevo, y como el
# mismo bucle es el que llama stepSimulation(), toda la ventana quedaria
# limitada a la velocidad a la que llegan datos del ESP32 (se ve trabada).
# Por eso: solo se lee si in_waiting > 0 (ya hay bytes en el buffer), y
# se lee TODO lo que haya (while, no if), para no quedarse atras si
# llegaron varias lineas juntas mientras el brazo dibujaba.
#
# Ademas se muestra en la ventana la ULTIMA LINEA CRUDA recibida (sea o
# no un "DIGIT:n" valido): si nunca cambia, el ESP32 no esta mandando
# nada (cable, puerto, main.py no corre); si cambia pero no es lo
# esperado, el problema es de formato, no de conexion.
id_texto_crudo = p.addUserDebugText("Ultima linea del ESP32: (nada todavia)" if ser is not None
                                    else "Sin ESP32: usa los botones 0-9",
                                    [0.0, 0.0, 1.08], textColorRGB=[0.7, 0.7, 0.7], textSize=1.1)


def leer_serial():
    """Devuelve la lista de digitos ("0".."9") que llegaron del ESP32
    desde la ultima llamada, sin bloquear nunca."""
    global ser, id_texto_crudo
    digitos = []
    if ser is None:
        return digitos
    try:
        while ser.in_waiting > 0:
            linea = ser.readline().decode(errors="ignore").strip()
            if not linea:
                continue
            print(f"[SERIAL] recibido: {linea!r}")
            # replaceItemUniqueId reemplaza el texto anterior en vez de
            # apilar uno encima del otro
            id_texto_crudo = p.addUserDebugText(f"Ultima linea del ESP32: {linea}", [0.0, 0.0, 1.08],
                                                textColorRGB=[0.7, 0.7, 0.7], textSize=1.1,
                                                replaceItemUniqueId=id_texto_crudo)
            if linea.startswith("DIGIT:"):
                digitos.append(linea.split(":", 1)[1])
    except serial.SerialException:
        # se desconecto el cable con el programa corriendo: en vez de
        # tronar, se sigue solo con los botones
        print("Se perdio la conexion con el ESP32: sigue con los botones de la ventana.")
        ser = None
    return digitos


print("Ventana de PyBullet abierta. Cierra la ventana o Ctrl+C en la terminal para salir.")

try:
    # p.isConnected() pasa a False cuando el usuario cierra la ventana de
    # PyBullet: asi el script termina solo en vez de tirar un error de
    # "Not connected to physics server" en la siguiente llamada.
    while p.isConnected():
        # digitos que llegan del ESP32 (teclado fisico)
        for digito in leer_serial():
            dibujar_digito(digito)

        # digito elegido a mano con los botones, sin necesidad de ESP32.
        # Un boton de PyBullet (addUserDebugParameter con min > max) no
        # devuelve True/False: devuelve un CONTADOR que sube en 1 con cada
        # click. Por eso se compara contra el valor anterior en vez de
        # preguntar "esta apretado".
        for digito, boton in botones_digitos.items():
            contador = p.readUserDebugParameter(boton)
            if contador != contadores_anteriores[digito]:
                contadores_anteriores[digito] = contador
                dibujar_digito(digito)

        p.stepSimulation()
        time.sleep(1 / 240)
except (KeyboardInterrupt, p.error):
    pass  # Ctrl+C o ventana cerrada a mitad de un dibujo: salir sin traza de error
finally:
    if ser is not None:
        ser.close()
