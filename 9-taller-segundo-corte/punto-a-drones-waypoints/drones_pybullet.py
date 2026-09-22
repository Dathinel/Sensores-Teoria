# Punto a) del taller: mover un dron (con otros dos siguiendolo en
# formacion) entre tres puntos A, B y C, controlado desde el ESP32.
# Basado en la idea de gym-pybullet-drones (github.com/utiasDSL/gym-pybullet-drones)
# pero sin esa dependencia pesada (gymnasium + stable-baselines3): en vez
# de un modelo aerodinamico real, cada dron es un cuerpo cinematico (su
# posicion se fija directamente cada cuadro, sin fisica de vuelo) que
# persigue un "objetivo" con un simple filtro de primer orden -- eso ya
# alcanza para el objetivo del taller, que es la CONSOLA DE MANDOS desde
# el ESP32, no un simulador aerodinamico.
#
# Un solo teclado matricial 4x4 controla todo (ver esp32_teclado.py, el
# mismo firmware que usa punto-b-brazo-tipo-baxter): esta es la
# "configuracion" de drones, con este mapeo de teclas:
#
#   8/2 = adelante/atras (Y+/Y-)      4/6 = izquierda/derecha (X-/X+)
#   9/7 = subir/bajar (Z+/Z-)        5   = detener (congela el objetivo actual)
#   A/B/C = volar directo al punto A/B/C      D = volver al origen (home)
#   *   = despegar (sube a altura de vuelo)   # = aterrizar (baja a ras de piso)
#   (0, 1, 3 no se usan en esta configuracion)
#
# Si no hay ESP32 conectado, la ventana de PyBullet trae los mismos
# botones (jog de paso fijo + saltos a A/B/C/home), igual que en los
# temas 7 y 8.

import os
import time

import pybullet as p
import pybullet_data
import serial

CARPETA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PUERTO_SERIAL = "COM7"
BAUDIOS = 115200

try:
    ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.05)
    time.sleep(2)  # da tiempo a que el ESP32 termine de reiniciar tras abrir el puerto
    print(f"ESP32 conectado en {PUERTO_SERIAL}: el teclado mueve el dron.")
except serial.SerialException:
    ser = None
    print(f"No se encontro el ESP32 en {PUERTO_SERIAL}: usa los botones de la ventana.")

# ------------------------------------------------------------------
# Puntos A, B y C del enunciado, mas el origen (home) y la altura de
# "despegado"/"aterrizado".
# ------------------------------------------------------------------
PUNTOS = {
    "A": (0.0, 0.9, 1.2),
    "B": (1.4, -0.6, 1.6),
    "C": (-1.3, 0.4, 0.9),
}
ORIGEN = (0.0, 0.0, 0.05)
ALTURA_VUELO = 1.0
ALTURA_SUELO = 0.05

PASO_JOG = 0.05          # metros que se suma/resta por tick mientras se sostiene una tecla
SUAVIZADO = 0.08         # que fraccion de la distancia al objetivo se recorre por paso de fisica (mov. fluido)
OFFSET_SEGUIDORES = [(-0.35, -0.25, 0.0), (0.35, -0.25, 0.0)]  # formacion de los otros 2 drones

physics_client = p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, 0)  # los drones son cinematicos: no hace falta gravedad
p.loadURDF("plane.urdf")
p.resetDebugVisualizerCamera(cameraDistance=2.6, cameraYaw=35, cameraPitch=-35, cameraTargetPosition=[0, 0, 0.8])

# marcadores visuales de los 3 puntos (esferas semitransparentes fijas)
COLORES_PUNTO = {"A": [0.3, 0.7, 1, 0.5], "B": [1, 0.6, 0.2, 0.5], "C": [0.6, 1, 0.4, 0.5]}
for nombre, pos in PUNTOS.items():
    marcador_id = p.createVisualShape(p.GEOM_SPHERE, radius=0.08, rgbaColor=COLORES_PUNTO[nombre])
    p.createMultiBody(baseVisualShapeIndex=marcador_id, basePosition=pos)
    p.addUserDebugText(nombre, [pos[0], pos[1], pos[2] + 0.15], textColorRGB=[1, 1, 1], textSize=1.4)


RUTA_DRON = os.path.join(CARPETA_SCRIPT, "dron.urdf")  # ruta absoluta: PyBullet busca relativo al cwd, no a este archivo
lider_id = p.loadURDF(RUTA_DRON, ORIGEN)
seguidores_id = [p.loadURDF(RUTA_DRON, ORIGEN) for _ in OFFSET_SEGUIDORES]
for seguidor_id in seguidores_id:
    p.changeVisualShape(seguidor_id, -1, rgbaColor=[0.2, 0.5, 0.9, 1])  # link base en azul, para distinguirlos del lider (rojo)

posicion_lider = list(ORIGEN)
objetivo_lider = list(ORIGEN)

# ------------------------------------------------------------------
# Botones de la ventana (fijos, sin ESP32): jog + saltos a A/B/C/home,
# mismo patron que en los temas 7 y 8 (nada de sliders: PyBullet no
# borra bien los addUserDebugParameter viejos al recrearlos).
# ------------------------------------------------------------------
botones = {
    "adelante": p.addUserDebugParameter("Adelante (Y+)", 1, 0, 0),
    "atras": p.addUserDebugParameter("Atras (Y-)", 1, 0, 0),
    "izquierda": p.addUserDebugParameter("Izquierda (X-)", 1, 0, 0),
    "derecha": p.addUserDebugParameter("Derecha (X+)", 1, 0, 0),
    "subir": p.addUserDebugParameter("Subir (Z+)", 1, 0, 0),
    "bajar": p.addUserDebugParameter("Bajar (Z-)", 1, 0, 0),
    "detener": p.addUserDebugParameter("Detener", 1, 0, 0),
    "punto_a": p.addUserDebugParameter("Ir a A", 1, 0, 0),
    "punto_b": p.addUserDebugParameter("Ir a B", 1, 0, 0),
    "punto_c": p.addUserDebugParameter("Ir a C", 1, 0, 0),
    "home": p.addUserDebugParameter("Home (origen)", 1, 0, 0),
    "despegar": p.addUserDebugParameter("Despegar", 1, 0, 0),
    "aterrizar": p.addUserDebugParameter("Aterrizar", 1, 0, 0),
}
contadores_anteriores = {nombre: 0 for nombre in botones}

ids_trazo = []  # lineas de depuracion del recorrido del lider


def borrar_trazo():
    for id_linea in ids_trazo:
        p.removeUserDebugItem(id_linea)
    ids_trazo.clear()


def procesar_tecla(tecla):
    global objetivo_lider
    if tecla == "8":
        objetivo_lider[1] += PASO_JOG
    elif tecla == "2":
        objetivo_lider[1] -= PASO_JOG
    elif tecla == "4":
        objetivo_lider[0] -= PASO_JOG
    elif tecla == "6":
        objetivo_lider[0] += PASO_JOG
    elif tecla == "9":
        objetivo_lider[2] += PASO_JOG
    elif tecla == "7":
        objetivo_lider[2] = max(ALTURA_SUELO, objetivo_lider[2] - PASO_JOG)
    elif tecla == "5":
        objetivo_lider = list(posicion_lider)  # se congela donde este ahora
    elif tecla in PUNTOS:
        borrar_trazo()
        objetivo_lider = list(PUNTOS[tecla])
    elif tecla == "D":
        borrar_trazo()
        objetivo_lider = list(ORIGEN)
    elif tecla == "*":
        objetivo_lider[2] = ALTURA_VUELO
    elif tecla == "#":
        objetivo_lider[2] = ALTURA_SUELO


print("Ventana de PyBullet abierta. Cierra la ventana o Ctrl+C en la terminal para salir.")

while True:
    # teclado fisico (ESP32): llega "TECLA:x" sin parar. OJO: ser.readline()
    # con timeout esperaba hasta 50ms cuando no habia linea todavia, y eso
    # capaba TODO el bucle (incluida la simulacion) a ~20 cuadros por
    # segundo en vez de 240 -- se veia trabado aunque el jog en si
    # funcionara bien. Por eso se lee solo si YA hay datos esperando
    # (in_waiting), sin bloquear nunca la simulacion.
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
                objetivo_lider[1] += PASO_JOG
            elif nombre == "atras":
                objetivo_lider[1] -= PASO_JOG
            elif nombre == "izquierda":
                objetivo_lider[0] -= PASO_JOG
            elif nombre == "derecha":
                objetivo_lider[0] += PASO_JOG
            elif nombre == "subir":
                objetivo_lider[2] += PASO_JOG
            elif nombre == "bajar":
                objetivo_lider[2] = max(ALTURA_SUELO, objetivo_lider[2] - PASO_JOG)
            elif nombre == "detener":
                objetivo_lider = list(posicion_lider)
            elif nombre in ("punto_a", "punto_b", "punto_c"):
                borrar_trazo()
                objetivo_lider = list(PUNTOS[nombre[-1].upper()])
            elif nombre == "home":
                borrar_trazo()
                objetivo_lider = list(ORIGEN)
            elif nombre == "despegar":
                objetivo_lider[2] = ALTURA_VUELO
            elif nombre == "aterrizar":
                objetivo_lider[2] = ALTURA_SUELO

    # movimiento fluido: el lider se acerca al objetivo un poco cada paso
    # (filtro de primer orden), en vez de saltar de golpe
    posicion_anterior = tuple(posicion_lider)
    for eje in range(3):
        posicion_lider[eje] += (objetivo_lider[eje] - posicion_lider[eje]) * SUAVIZADO
    p.resetBasePositionAndOrientation(lider_id, posicion_lider, [0, 0, 0, 1])
    if (posicion_lider[0] - posicion_anterior[0]) ** 2 + (posicion_lider[1] - posicion_anterior[1]) ** 2 > 1e-8:
        ids_trazo.append(p.addUserDebugLine(posicion_anterior, posicion_lider, lineColorRGB=[1, 1, 0], lineWidth=2, lifeTime=0))
        if len(ids_trazo) > 400:  # jog sostenido por mucho rato: no dejar crecer el trazo sin limite
            p.removeUserDebugItem(ids_trazo.pop(0))

    # los 2 seguidores mantienen su offset de formacion respecto al lider
    for seguidor_id, (dx, dy, dz) in zip(seguidores_id, OFFSET_SEGUIDORES):
        pos_actual = p.getBasePositionAndOrientation(seguidor_id)[0]
        objetivo_seguidor = (posicion_lider[0] + dx, posicion_lider[1] + dy, posicion_lider[2] + dz)
        nueva_pos = [pos_actual[i] + (objetivo_seguidor[i] - pos_actual[i]) * SUAVIZADO for i in range(3)]
        p.resetBasePositionAndOrientation(seguidor_id, nueva_pos, [0, 0, 0, 1])

    p.stepSimulation()
    time.sleep(1 / 240)
