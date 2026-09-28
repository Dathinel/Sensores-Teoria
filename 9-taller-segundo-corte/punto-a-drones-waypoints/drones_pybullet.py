# Punto a) del taller: mover los drones de un lugar A a un lugar B y a un lugar C, con el control
# gestionado desde el ESP32 (teclado matricial). Basado en gym-pybullet-drones
# (github.com/utiasDSL/gym-pybullet-drones), sin sus dependencias pesadas (gymnasium,
# stable-baselines3: son para ENTRENAR controladores con redes neuronales).
#
# FISICA REAL, no cinematica: cada dron es un cuerpo con masa y gravedad, y lo sostienen y mueven
# SOLO las fuerzas de sus 4 motores, aplicadas en la punta de cada brazo, como en
# gym-pybullet-drones. Para ir de un punto a otro el dron tiene que INCLINARSE (un cuadricoptero no
# tiene otra forma de empujarse hacia un lado) y se ve frenar, pasarse un poco y corregir, como uno
# de verdad. La version anterior fijaba la posicion en cada cuadro (resetBasePositionAndOrientation,
# sin gravedad): se veia como un objeto arrastrado, no como un dron volando.
#
# Control en cascada (el mismo esquema de los controladores PID de gym-pybullet-drones):
#   1. POSICION: con la distancia al objetivo y la velocidad se calcula que aceleracion hace falta
#      (un PD: "resorte" hacia el objetivo + "amortiguador" para no pasarse).
#   2. INCLINACION: esa aceleracion, sumada a la que hace falta para vencer la gravedad, dice hacia
#      donde tiene que apuntar el empuje total -> cuanto inclinarse (roll/pitch) y cuanto empujar.
#   3. ACTITUD: otro PD convierte "estoy inclinado X, quiero Y" en torques (girar sobre cada eje).
#   4. MEZCLADOR: empuje total + 3 torques -> fuerza de cada uno de los 4 motores (cada motor solo
#      puede empujar hacia arriba de su helice, entre 0 y su maximo).
#
# Un solo teclado matricial 4x4 controla todo (../esp32_teclado.py, el mismo firmware del punto b):
#   8/2 = adelante/atras (Y+/Y-)      4/6 = izquierda/derecha (X-/X+)
#   9/7 = subir/bajar (Z+/Z-)        5   = detener (congela el objetivo donde esta)
#   A/B/C = volar al punto A/B/C      D = volver al origen (home)
#   *   = despegar                    # = aterrizar
#   0   = mision automatica A -> B -> C (lo que pide el enunciado, de una)
#   (1 y 3 no se usan)
# El dron lider (rojo) va al objetivo y los demas (azules) vuelan en formacion detras de el, cada
# uno con su propio controlador y sus propios motores.
#
# Sin ESP32 conectado, la ventana de PyBullet trae los mismos botones (jog + saltos + mision).
#   python drones_pybullet.py                  # ventana, ESP32 en COM7
#   python drones_pybullet.py --puerto COM5
#   python drones_pybullet.py --prueba         # sin ventana: vuela la mision A->B->C y la mide

import argparse
import math
import os
import time

import pybullet as p
import pybullet_data
import serial

CARPETA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
BAUDIOS = 115200

# ------------------------------------------------------------------
# Puntos del enunciado, origen (home) y alturas
# ------------------------------------------------------------------
PUNTOS = {
    "A": (0.0, 0.9, 1.2),
    "B": (1.4, -0.6, 1.6),
    "C": (-1.3, 0.4, 0.9),
}
ORIGEN = (0.0, 0.0, 0.03)
ALTURA_VUELO = 1.0
ALTURA_SUELO = 0.03          # objetivo "en el piso": la caja de colision mide 4 cm de alto
PASO_JOG = 0.10              # metros que se mueve el objetivo por tecla/clic
# Formacion: el lider adelante y 4 seguidores en V detras (separados mas que el ancho de un dron,
# 0,56 m, para que no se toquen ni al inclinarse).
OFFSET_SEGUIDORES = [(-0.7, -0.6, 0.0), (0.7, -0.6, 0.0), (-1.4, -1.2, 0.0), (1.4, -1.2, 0.0)]

# ------------------------------------------------------------------
# Dron (mismos valores que dron.urdf)
# ------------------------------------------------------------------
G = 9.81
MASA = 0.35                  # kg
BRAZO = 0.24                 # m: cada motor esta en (+-BRAZO, +-BRAZO)
# Motores en X, vistos desde arriba: 1 adelante-izquierda, 2 atras-izquierda, 3 atras-derecha,
# 4 adelante-derecha ("adelante" = +x). Giran alternados (1 y 3 en un sentido, 2 y 4 en el otro):
# asi sus torques de arrastre se anulan en vuelo estacionario, y para girar sobre z (yaw) basta con
# acelerar un par y frenar el otro.
MOTORES = [(BRAZO, BRAZO), (-BRAZO, BRAZO), (-BRAZO, -BRAZO), (BRAZO, -BRAZO)]
GIRO = [1, -1, 1, -1]
KM_KF = 0.025                # torque de arrastre / empuje de una helice (del orden del Crazyflie de gym-pybullet-drones)
F_MAX = 2.5 * MASA * G / 4   # empuje maximo por motor: relacion empuje/peso de 2,5 (un dron de hobby tipico)

# Ganancias. Posicion: "frecuencia natural" ~2,5 rad/s y poco amortiguada (se pasa un poco y
# corrige, como un dron real). Actitud: ~20 rad/s, bastante mas rapida que la posicion -- la
# regla de oro del control en cascada: el lazo de adentro tiene que ser mucho mas rapido.
KP_POS, KD_POS = 6.0, 4.0
KP_ALT, KD_ALT = 8.0, 5.0
ACC_MAX_XY, ACC_MAX_Z = 4.0, 4.0     # m/s2: limita la inclinacion (~22 grados) y la subida
INCLINACION_MAX = math.radians(30)
I_XY = 0.0045
KP_ATT, KD_ATT = I_XY * 20 ** 2, 2 * 0.9 * I_XY * 20
KP_YAW, KD_YAW = 0.02, 0.01


def _recortar(v, lim):
    return max(-lim, min(lim, v))


class Dron:
    """Un cuadricoptero con su controlador en cascada. `paso()` se llama en CADA paso de fisica:
    PyBullet borra las fuerzas externas despues de cada stepSimulation."""

    def __init__(self, cuerpo, objetivo):
        self.id = cuerpo
        self.objetivo = list(objetivo)
        self.inclinacion_max_vista = 0.0

    def estado(self):
        pos, orn = p.getBasePositionAndOrientation(self.id)
        vel, w = p.getBaseVelocity(self.id)
        return pos, orn, vel, w

    def paso(self):
        pos, orn, vel, w_mundo = self.estado()
        if self.objetivo[2] <= ALTURA_SUELO and pos[2] < ALTURA_SUELO + 0.02 and abs(vel[2]) < 0.2:
            # Aterrizado: se apagan los motores (si no, se quedaria flotando a ras del piso) y se
            # apoya con su peso. Al pedirle subir otra vez, el controlador los vuelve a prender.
            return pos, vel
        R = p.getMatrixFromQuaternion(orn)            # 3x3 por filas: columnas = ejes del dron en el mundo
        roll, pitch, yaw = p.getEulerFromQuaternion(orn)

        # 1) Posicion -> aceleracion deseada (PD), recortada.
        ax = _recortar(KP_POS * (self.objetivo[0] - pos[0]) - KD_POS * vel[0], ACC_MAX_XY)
        ay = _recortar(KP_POS * (self.objetivo[1] - pos[1]) - KD_POS * vel[1], ACC_MAX_XY)
        az = _recortar(KP_ALT * (self.objetivo[2] - pos[2]) - KD_ALT * vel[2], ACC_MAX_Z)

        # 2) Fuerza total que hace falta = masa x (aceleracion deseada + la que anula la gravedad).
        fx, fy, fz = MASA * ax, MASA * ay, MASA * (az + G)
        # Pasada al marco del dron girado solo en yaw, para saber si inclinarse "hacia su adelante"
        # (pitch) o "hacia su costado" (roll).
        fx_d = math.cos(yaw) * fx + math.sin(yaw) * fy
        fy_d = -math.sin(yaw) * fx + math.cos(yaw) * fy
        # Inclinarse en +pitch lleva el empuje hacia +x del dron; en +roll, hacia -y.
        pitch_des = _recortar(math.atan2(fx_d, fz), INCLINACION_MAX)
        roll_des = _recortar(math.atan2(-fy_d, fz), INCLINACION_MAX)
        # Empuje total: la parte de la fuerza pedida que cae sobre el eje z del DRON (columna 3 de R).
        # Si esta mas inclinado de lo pedido, empuja menos y no se dispara hacia arriba.
        z_dron = (R[2], R[5], R[8])
        empuje = max(0.0, fx * z_dron[0] + fy * z_dron[1] + fz * z_dron[2])

        # 3) Actitud -> torques (PD). La velocidad angular llega en el marco del mundo: se pasa al
        # del dron multiplicando por la transpuesta de R.
        w = [R[0] * w_mundo[0] + R[3] * w_mundo[1] + R[6] * w_mundo[2],
             R[1] * w_mundo[0] + R[4] * w_mundo[1] + R[7] * w_mundo[2],
             R[2] * w_mundo[0] + R[5] * w_mundo[1] + R[8] * w_mundo[2]]
        err_yaw = math.atan2(math.sin(-yaw), math.cos(-yaw))      # objetivo: yaw 0 (mirando a +x)
        tx = KP_ATT * (roll_des - roll) - KD_ATT * w[0]
        ty = KP_ATT * (pitch_des - pitch) - KD_ATT * w[1]
        tz = KP_YAW * err_yaw - KD_YAW * w[2]

        # 4) Mezclador: empuje y torques -> 4 motores. Un motor en (x, y) que empuja f produce un
        # torque (y*f, -x*f) sobre los ejes x e y, y KM_KF*f sobre z segun su sentido de giro.
        # Como las 4 combinaciones son ortogonales, se invierte sumando (sin resolver un sistema).
        fuerzas = []
        for (x, y), s in zip(MOTORES, GIRO):
            f = empuje / 4 + tx * y / (4 * BRAZO ** 2) - ty * x / (4 * BRAZO ** 2) + tz * s / (4 * KM_KF)
            fuerzas.append(max(0.0, min(F_MAX, f)))

        # Cada fuerza va en la punta de su brazo, en el marco DEL DRON (se inclina con el); asi el
        # torque sale de la geometria, igual que en el real. El arrastre de las helices va aparte.
        for (x, y), f in zip(MOTORES, fuerzas):
            p.applyExternalForce(self.id, -1, [0, 0, f], [x, y, 0], p.LINK_FRAME)
        p.applyExternalTorque(self.id, -1, [0, 0, KM_KF * sum(f * s for f, s in zip(fuerzas, GIRO))], p.LINK_FRAME)
        self.inclinacion_max_vista = max(self.inclinacion_max_vista, abs(roll), abs(pitch))
        return pos, vel


def crear_mundo(con_ventana):
    p.connect(p.GUI if con_ventana else p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setGravity(0, 0, -G)
    p.setTimeStep(1 / 240)
    p.loadURDF("plane.urdf")
    if con_ventana:
        p.resetDebugVisualizerCamera(cameraDistance=4.2, cameraYaw=35, cameraPitch=-30, cameraTargetPosition=[0, -0.3, 0.8])
    # marcadores de los 3 puntos (esferas semitransparentes, sin colision)
    colores = {"A": [0.3, 0.7, 1, 0.5], "B": [1, 0.6, 0.2, 0.5], "C": [0.6, 1, 0.4, 0.5]}
    for nombre, pos in PUNTOS.items():
        forma = p.createVisualShape(p.GEOM_SPHERE, radius=0.08, rgbaColor=colores[nombre])
        p.createMultiBody(baseVisualShapeIndex=forma, basePosition=pos)
        if con_ventana:
            p.addUserDebugText(nombre, [pos[0], pos[1], pos[2] + 0.15], textColorRGB=[1, 1, 1], textSize=1.4)
    ruta = os.path.join(CARPETA_SCRIPT, "dron.urdf")   # absoluta: PyBullet busca relativo al cwd
    lider = Dron(p.loadURDF(ruta, ORIGEN), ORIGEN)
    seguidores = []
    for dx, dy, dz in OFFSET_SEGUIDORES:
        inicio = (ORIGEN[0] + dx, ORIGEN[1] + dy, ORIGEN[2])
        d = Dron(p.loadURDF(ruta, inicio), inicio)
        p.changeVisualShape(d.id, 0, rgbaColor=[0.2, 0.5, 0.9, 1])   # cuerpo azul (el primer visual)
        p.changeVisualShape(d.id, -1, rgbaColor=[0.2, 0.5, 0.9, 1])
        seguidores.append(d)
    return lider, seguidores


class Mando:
    """Lo que hace cada tecla (del ESP32 o de los botones): mueve el OBJETIVO del lider; los
    seguidores copian ese objetivo + su offset (no la posicion del lider: asi la formacion no se
    deforma cuando el lider se inclina o se pasa)."""

    def __init__(self, lider):
        self.lider = lider
        self.mision = []          # puntos que faltan de la mision A -> B -> C
        self.trazo_reiniciar = False

    def tecla(self, t):
        o = self.lider.objetivo
        pos = p.getBasePositionAndOrientation(self.lider.id)[0]
        if t != "0" and t in "82469757ABCD*#":
            self.mision = []          # cualquier otra orden cancela la mision automatica
        if t == "8":
            o[1] += PASO_JOG
        elif t == "2":
            o[1] -= PASO_JOG
        elif t == "4":
            o[0] -= PASO_JOG
        elif t == "6":
            o[0] += PASO_JOG
        elif t == "9":
            o[2] += PASO_JOG
        elif t == "7":
            o[2] = max(ALTURA_SUELO, o[2] - PASO_JOG)
        elif t == "5":
            o[:] = list(pos)
        elif t in PUNTOS:
            o[:] = list(PUNTOS[t])
            self.trazo_reiniciar = True
        elif t == "D":
            o[:] = list(ORIGEN)
            self.trazo_reiniciar = True
        elif t == "*":
            o[2] = ALTURA_VUELO
        elif t == "#":
            o[2] = ALTURA_SUELO
        elif t == "0":
            self.mision = ["A", "B", "C"]
            o[:] = list(PUNTOS["A"])
            self.trazo_reiniciar = True

    def avanzar_mision(self, pos, vel):
        """Pasa al siguiente punto cuando el lider llego (a 12 cm y casi quieto)."""
        if not self.mision:
            return None
        destino = PUNTOS[self.mision[0]]
        cerca = math.dist(pos, destino) < 0.12 and math.hypot(*vel) < 0.3
        if cerca:
            llegado = self.mision.pop(0)
            if self.mision:
                self.lider.objetivo[:] = list(PUNTOS[self.mision[0]])
            return llegado
        return None


def conectar_esp32(puerto):
    try:
        ser = serial.Serial(puerto, BAUDIOS, timeout=0)
        time.sleep(2)   # abrir el puerto reinicia el ESP32 (DTR): esperar a que arranque
        print(f"ESP32 conectado en {puerto}: el teclado mueve los drones.")
        return ser
    except serial.SerialException:
        print(f"No se encontro el ESP32 en {puerto}: usa los botones de la ventana.")
        return None


def leer_teclas(ser, buffer):
    """Drena TODO lo que llego (no una linea por vuelta: se quedaria atras) sin bloquear nunca la
    simulacion (un readline() con timeout frenaba todo el bucle a ~20 Hz, ver CLAUDE.md). Devuelve
    (teclas, ultima linea cruda) -- la linea cruda es el mejor diagnostico si "no llega nada"."""
    teclas, cruda = [], None
    if ser is None or not ser.in_waiting:
        return teclas, cruda, buffer
    buffer += ser.read(ser.in_waiting).decode(errors="ignore")
    *lineas, buffer = buffer.split("\n")      # la ultima puede venir cortada: se guarda para despues
    for linea in lineas:
        linea = linea.strip()
        if linea:
            cruda = linea
        if linea.startswith("TECLA:"):
            teclas.append(linea.split(":", 1)[1][:1])
    return teclas, cruda, buffer


def volar(con_ventana=True, puerto="COM7", mision_automatica=False, max_segundos=None):
    lider, seguidores = crear_mundo(con_ventana)
    mando = Mando(lider)
    ser = conectar_esp32(puerto) if con_ventana else None
    botones = {}
    if con_ventana:
        # Botones FIJOS (creados una vez): PyBullet no borra bien los addUserDebugParameter viejos.
        for nombre, t in [("Adelante (Y+)", "8"), ("Atras (Y-)", "2"), ("Izquierda (X-)", "4"), ("Derecha (X+)", "6"),
                          ("Subir (Z+)", "9"), ("Bajar (Z-)", "7"), ("Detener", "5"), ("Ir a A", "A"), ("Ir a B", "B"),
                          ("Ir a C", "C"), ("Home (origen)", "D"), ("Despegar", "*"), ("Aterrizar", "#"),
                          ("Mision A -> B -> C", "0")]:
            botones[p.addUserDebugParameter(nombre, 1, 0, 0)] = [t, 0]
    if mision_automatica:
        mando.tecla("*")
    buffer, ultima_cruda, texto_id, trazo = "", "(nada todavia)", None, []
    pos_anterior = None
    paso, llegadas, t0_mision = 0, [], None
    print("Cierra la ventana o Ctrl+C para salir.")
    try:
        while True:
            teclas, cruda, buffer = leer_teclas(ser, buffer)
            ultima_cruda = cruda or ultima_cruda
            for boton, estado in botones.items():
                cuenta = p.readUserDebugParameter(boton)
                if cuenta != estado[1]:
                    estado[1] = cuenta
                    teclas.append(estado[0])
            for t in teclas:
                mando.tecla(t)
            # Mision de prueba: despega y, a 1 s, arranca A -> B -> C.
            if mision_automatica and paso == 240 and t0_mision is None:
                mando.tecla("0")
                t0_mision = paso

            pos, vel = lider.paso()
            for d, (dx, dy, dz) in zip(seguidores, OFFSET_SEGUIDORES):
                o = lider.objetivo
                d.objetivo[:] = [o[0] + dx, o[1] + dy, max(ALTURA_SUELO, o[2] + dz)]
                d.paso()
            llegado = mando.avanzar_mision(pos, vel)
            if llegado:
                llegadas.append((llegado, round((paso - (t0_mision or 0)) / 240, 1)))
                print(f"Llego a {llegado} a los {llegadas[-1][1]} s de empezar la mision")
                if mision_automatica and not mando.mision:
                    break

            if con_ventana:
                if mando.trazo_reiniciar:
                    for i in trazo:
                        p.removeUserDebugItem(i)
                    trazo.clear()
                    mando.trazo_reiniciar = False
                if paso % 8 == 0:     # trazo del lider (cada 8 pasos: suficiente y liviano)
                    if pos_anterior and math.dist(pos, pos_anterior) > 0.01:
                        trazo.append(p.addUserDebugLine(pos_anterior, pos, [1, 1, 0], 2))
                        if len(trazo) > 400:
                            p.removeUserDebugItem(trazo.pop(0))
                    pos_anterior = pos
                if paso % 24 == 0:    # 10 veces por segundo: posicion, objetivo y la linea cruda
                    o = lider.objetivo
                    texto = (f"lider ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})  objetivo ({o[0]:.2f}, {o[1]:.2f}, "
                             f"{o[2]:.2f})" + (f"  mision: {' -> '.join(mando.mision)}" if mando.mision else "")
                             + f"   serial: {ultima_cruda if ser else 'sin ESP32'}")
                    texto_id = p.addUserDebugText(texto, [-2.2, -2.2, 2.3], [1, 1, 1], 1.1,
                                                  replaceItemUniqueId=texto_id if texto_id is not None else -1)
            p.stepSimulation()
            paso += 1
            if con_ventana:
                time.sleep(1 / 240)
            if max_segundos and paso > max_segundos * 240:
                break
    except (KeyboardInterrupt, p.error):
        pass   # Ctrl+C o ventana cerrada
    finally:
        if ser is not None:
            ser.close()
    resultado = {"llegadas": llegadas, "inclinacion_max_grados": round(math.degrees(
        max(d.inclinacion_max_vista for d in [lider] + seguidores)), 1),
        "posicion_final": [round(v, 3) for v in p.getBasePositionAndOrientation(lider.id)[0]]}
    if p.isConnected():
        p.disconnect()
    return resultado


if __name__ == "__main__":
    analizador = argparse.ArgumentParser(description="Drones A -> B -> C controlados desde el ESP32 (fisica real).")
    analizador.add_argument("--puerto", default="COM7", help="puerto serial del ESP32 (Administrador de dispositivos)")
    analizador.add_argument("--prueba", action="store_true",
                            help="sin ventana: despega, vuela la mision A -> B -> C y muestra tiempos e inclinacion")
    args = analizador.parse_args()
    if args.prueba:
        r = volar(con_ventana=False, mision_automatica=True, max_segundos=60)
        print(r)
        ok = [n for n, _ in r["llegadas"]] == ["A", "B", "C"] and r["inclinacion_max_grados"] < 35
        print("PRUEBA OK" if ok else "PRUEBA FALLIDA")
        raise SystemExit(0 if ok else 1)
    volar(puerto=args.puerto)
