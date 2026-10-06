"""Punto c) del taller: consola de mandos con el ESP32 para el humanoide Atlas.

Basado en atlas.py del repositorio que compartio el profesor
(https://github.com/erwincoumans/pybullet_robots/blob/master/atlas.py): ese
ejemplo solo carga atlas_v4_with_multisense.urdf, deja todas las juntas en 0
con POSITION_CONTROL y pone la gravedad. Aca se le agrega todo lo que hace
falta para "una movilidad real" manejada desde el teclado 4x4 del ESP32:

  * mover el cuerpo junta por junta (grupos: brazo izq, brazo der,
    torso+cabeza, piernas),
  * poses de un golpe con rampa (saludar, brazos arriba, agacharse, de pie),
  * caminar hacia adelante / atras y girar dando pasos en el lugar, con
    fisica real (solo motores de las juntas + contacto de los pies),
  * un ASISTENTE DE EQUILIBRIO que se prende y se apaga (como el arnes con
    el que se prueban los humanoides reales), para comparar la misma fisica
    con ayuda y sin ayuda,
  * "ponerlo de pie" (como levantarlo con la grua) cuando se cae.

Nada mueve la base del robot a mano mientras camina (no hay "root motion"):
el unico empujon externo es el del asistente, que se ve en pantalla, se
puede apagar y por construccion NO empuja en horizontal (ver asistente()).

Mapa de teclas (ver README):
  A  asistente ON/OFF (flanco)        B  ponerlo de pie (flanco)
  C  saludar (flanco)                 D  agacharse (flanco)
  #  brazos arriba (flanco)           5  pose de pie / detener (flanco)
  *  siguiente grupo de juntas        0  reiniciar todo (flanco)
  1/3  junta A del grupo -/+ (cada repeticion)
  7/9  junta B del grupo -/+ (cada repeticion)
  8  caminar adelante (sostenida)     2  caminar atras (sostenida)
  4/6  girar a la izquierda/derecha dando pasos en el lugar (sostenida)

Uso como modulo (por ejemplo para sacar capturas sin ventana, en DIRECT):

    import pybullet as p
    import atlas_pybullet as A
    e = A.crear_mundo(p.DIRECT)          # Atlas de pie, asentado, asistente ON

    # Escena 1: de pie con el asistente
    A.simular(e, 2.0)                    # 2 s de pie quieto (tecla "-")

    # Escena 2: caminando (con asistente)
    A.simular(e, 6.0, "8")               # 6 s sosteniendo la tecla 8 (avanza ~0,7 m)

    # Escena 3: sin asistente, cayendo. Caminar derecho sin asistente esta al
    # borde (recien creado se cae a los ~5,4 s; tras otras pruebas aguanto 15 s);
    # girar en el lugar lo tira mas rapido: medido, con la tecla 4 la
    # inclinacion de la pelvis llega a 0,5 rad a los 2,4 s y toca el piso
    # a los ~2,8 s. La simulacion es determinista: siempre igual.
    A.reiniciar_todo(e)                  # origen, asistente ON
    A.asistente(e, False)
    A.simular(e, 2.4, "4")               # en plena caida (2,8 s: ya en el piso)
    A.leer_estado(e)["caido"]            # True cuando ya esta caido

    # Otras: A.procesar_tecla(e, "C") (saludar), "D" (agacharse), "#"...
    # A.poner_de_pie(e) lo levanta de nuevo. La camara la elige quien captura
    # (posicion de la pelvis en A.leer_estado(e)["pos"]).

Solo puede haber UNA conexion de PyBullet por proceso (se usa la conexion
por defecto); crear_mundo() la abre.
"""

import math
import sys
import time
from pathlib import Path

import pybullet as p
import pybullet_data

# ----------------------------------------------------------------------
# Rutas y constantes generales
# ----------------------------------------------------------------------
# Las mallas de Atlas NO vienen en pybullet_data: las baja
# ../descargar_modelos.py a 9-taller-segundo-corte/modelos/ (ignorada por
# git). Se cargan con ruta absoluta para que el script funcione sin
# importar desde que carpeta se lo corra.
MODELOS = Path(__file__).resolve().parent.parent / "modelos"
URDF_ATLAS = MODELOS / "atlas" / "atlas_v4_with_multisense.urdf"
URDF_PISO = Path(pybullet_data.getDataPath()) / "plane.urdf"

PUERTO_SERIAL = "COM7"
BAUDIOS = 115200

# Paso de fisica de 1/500 s (el mismo del cuadrupedo de la version anterior): con dos pies de caja que
# golpean y se despegan del piso todo el tiempo, y 182 kg encima, un paso
# fino mantiene los contactos estables. Con 1/240 los pies "rebotan" mas.
PASO_FISICA = 1.0 / 500
GRAVEDAD = 9.8
RAMPA = 0.6                 # s: arrancar/frenar la marcha y pasar de una pose a otra
PASOS_ASENTAR = 300         # 0,6 s de fisica tras ponerlo de pie, antes de devolver el control
INTERVALO_TECLA = 0.05      # s: el ESP32 manda "TECLA:x" cada ~50 ms

# Estado "caido": la pelvis de pie queda a ~0,95 m (agachado, a ~0,78 m);
# tirado en el piso queda a 0,1-0,3 m. La inclinacion es el angulo entre
# el eje vertical de la pelvis y la vertical del mundo.
ALTURA_MIN_DE_PIE = 0.55
INCLINACION_MAX = 0.6       # rad (~34 grados)

# ----------------------------------------------------------------------
# Fuerzas de los motores
# ----------------------------------------------------------------------
# El URDF trae limites de esfuerzo por junta (columna maxForce de
# getJointInfo). Los de los brazos, cuello y munecas alcanzan de sobra, pero
# los del tobillo (aky 92 N*m, akx 45 N*m) y los del torso (bkx 300 N*m) no
# sostienen 182 kg: probado en DIRECT, con esos valores y solo inclinar las
# dos caderas 0,1 rad hacia un costado el robot se fue al piso (el tobillo
# no aguanto el torque). Por eso en piernas y torso se usa como minimo
# FUERZA_PIERNA / FUERZA_TORSO (el valor del URDF si es mayor, como la
# rodilla con 890). Se eligieron probando caminatas de 20 s en DIRECT.
FUERZA_PIERNA = 800.0       # N*m
FUERZA_TORSO = 1000.0       # N*m

# ----------------------------------------------------------------------
# Asistente de equilibrio ("arnes virtual")
# ----------------------------------------------------------------------
# Hace dos cosas, ninguna horizontal:
#  1. Sostiene una fraccion fija del peso (ALFA_PESO) con una fuerza
#     vertical sobre la pelvis, como los arneses de "body weight support"
#     con los que se ensaya la marcha (en rehabilitacion y con humanoides).
#     Se le suma un amortiguador vertical para que no rebote.
#  2. Endereza la pelvis: un torque proporcional a la inclinacion (roll y
#     pitch) mas un amortiguador. El yaw (rumbo) queda LIBRE: girar sale de
#     los pasos, igual con o sin asistente.
# Por que no un createConstraint(JOINT_FIXED) "blando": se probo, moviendo
# su pivote a la x,y actual de la pelvis en cada paso, y el solver de
# Bullet igual frena la VELOCIDAD horizontal (una restriccion fija pide
# velocidad relativa cero en los 6 ejes): con maxForce 2000 N el robot
# avanzo -1,7 cm en 10 s de caminata (con este arnes de fuerzas, 1,21 m);
# con 500 N avanzo 1,13 m, pero 500 N es menos de un tercio del peso: ya
# no es un arnes que lo sostenga. Con fuerzas externas la componente
# horizontal es cero por construccion: todo el avance sale de la friccion
# de los pies.
ALFA_PESO = 0.5             # fraccion del peso que sostiene el arnes
AMORT_VERTICAL = 400.0      # N por m/s
KP_ENDEREZAR = 4000.0       # N*m por rad de inclinacion
KD_ENDEREZAR = 400.0        # N*m por rad/s
TORQUE_MAX_ASISTENTE = 2500.0   # N*m (tope, para que no sea un "brazo de dios")

# ----------------------------------------------------------------------
# Marcha (patron de pasos generado con senos, un "CPG", como el del cuadrupedo de la version anterior)
# ----------------------------------------------------------------------
# Valores encontrados con barridos en DIRECT (ver README). Los que dejan
# caminar 20 s SIN asistente sin caerse son pocos y estan juntos: zancada
# de cadera chica (0,05 rad), levantar el pie con la rodilla 0,4 rad y un
# balanceo lateral de 0,05 rad. Con zancada 0,07-0,08 o balanceo 0,055-0,06
# sin asistente se cae entre los 3 y los 10 s. Se usa el MISMO patron con y
# sin asistente, para que la comparacion sea justa.
FLEXION_DE_PIE = 0.25       # rad: rodilla doblada 2x esto, cadera y tobillo -1x (pie plano)
FRECUENCIA_PASO = 0.8       # ciclos por segundo (cada ciclo = un paso con cada pie)
AMPLITUD_ZANCADA = 0.05     # rad de cadera (hpy) hacia adelante/atras
AMPLITUD_LEVANTAR = 0.4     # rad extra de rodilla (kny) en la pierna que va por el aire
AMPLITUD_LATERAL = 0.05     # rad de cadera (hpx) para pasar el peso al pie de apoyo
AMPLITUD_GIRO = 0.15        # rad de cadera (hpz) por paso al girar en el lugar

# ----------------------------------------------------------------------
# Jog (mover juntas a mano) y grupos
# ----------------------------------------------------------------------
PASO_JOG = 0.03             # rad por repeticion de tecla (20 por s -> 0,6 rad/s)
JOG_POR_CLICK = 5           # un click de boton = 5 repeticiones (0,15 rad)

# Cada grupo tiene dos "juntas" de jog, A (teclas 1/3) y B (7/9). Una junta
# de jog puede mover varias juntas reales a la vez con un coeficiente: en
# las piernas, "agachar" dobla cadera, rodilla y tobillo de las dos piernas
# a la vez para que los pies queden planos y el robot no se vaya de lado.
# El signo esta elegido para que "+" (3 y 9) sea subir el brazo / doblar el
# codo / girar el torso a la izquierda / mirar abajo / agacharse / cargar el
# peso en el pie derecho, a los dos lados por igual.
GRUPOS = [
    ("brazo izquierdo",
     ("hombro", [("l_arm_shx", 1.0)]),
     ("codo", [("l_arm_elx", 1.0)])),
    ("brazo derecho",
     ("hombro", [("r_arm_shx", -1.0)]),
     ("codo", [("r_arm_elx", -1.0)])),
    ("torso y cabeza",
     ("giro del torso", [("back_bkz", 1.0)]),
     ("cabeza", [("neck_ry", 1.0)])),
    ("piernas",
     ("agachar", [("l_leg_hpy", -1.0), ("l_leg_kny", 2.0), ("l_leg_aky", -1.0),
                  ("r_leg_hpy", -1.0), ("r_leg_kny", 2.0), ("r_leg_aky", -1.0)]),
     ("peso a la derecha", [("l_leg_hpx", 1.0), ("l_leg_akx", -1.0),
                            ("r_leg_hpx", 1.0), ("r_leg_akx", -1.0)])),
]


# ======================================================================
# Poses
# ======================================================================
def pose_de_pie(flexion=FLEXION_DE_PIE):
    """Pose de pie: brazos abajo y rodillas un poco dobladas.

    Con las piernas rectas el robot queda "trabado" y cualquier empujon lo
    tumba; con las rodillas algo dobladas los motores tienen margen para
    corregir. Cadera y tobillo van con -flexion y la rodilla con +2*flexion,
    asi el muslo y la canilla forman un triangulo isosceles: la pelvis queda
    justo encima de los pies y la planta del pie queda plana en el piso.
    El URDF carga a Atlas en "T" (brazos horizontales); hombro shx -1,3
    (izq) / +1,3 (der) los baja (el eje del hombro izquierdo apunta a -x).
    """
    pose = {"l_arm_shx": -1.3, "r_arm_shx": 1.3}
    for lado in "lr":
        pose[lado + "_leg_hpy"] = -flexion
        pose[lado + "_leg_kny"] = 2 * flexion
        pose[lado + "_leg_aky"] = -flexion
    return pose


def pose_brazos_arriba():
    pose = pose_de_pie()
    pose.update({"l_arm_shx": 1.3, "r_arm_shx": -1.3})
    return pose


def pose_saludar():
    """Brazo derecho arriba con el codo doblado (el vaiven del saludo lo
    agrega objetivos_motores() mientras esta pose este activa)."""
    pose = pose_de_pie()
    pose.update({"r_arm_shx": -1.2, "r_arm_elx": -0.6})
    return pose


def pose_agachado():
    """Rodillas bien dobladas (flexion 0,75: la pelvis baja de ~0,95 a
    ~0,78 m) con el torso casi derecho. Como cadera y tobillo se doblan
    lo mismo, la pelvis sigue justo encima de los pies, y el torso (84 kg,
    casi la mitad del robot) tambien. Probado en DIRECT sin asistente:
    inclinar el torso hacia adelante 0,3 rad o mas (back_bky) lo tira de
    cara a los ~2 s; con 0,15 o menos se sostiene."""
    pose = pose_de_pie(0.75)
    pose["back_bky"] = 0.15
    pose.update({"l_arm_shx": -0.9, "r_arm_shx": 0.9})
    return pose


POSES = {
    "de pie": pose_de_pie,
    "saludar": pose_saludar,
    "brazos arriba": pose_brazos_arriba,
    "agachado": pose_agachado,
}


# ======================================================================
# Estado y mundo
# ======================================================================
class Estado:
    """Todo lo que cambia mientras corre la simulacion (sin globales, para
    que otro script pueda importar el modulo y manejar el robot)."""

    def __init__(self):
        self.atlas = None
        self.juntas = {}            # nombre -> indice (buscadas por NOMBRE, no por numero)
        self.indices = []           # indices de las 30 juntas, en orden
        self.fuerzas = []           # fuerza maxima por junta (mismo orden)
        self.limites = {}           # nombre -> (inferior, superior)
        self.masa = 0.0
        self.t = 0.0                # reloj de la simulacion (s)
        # asistente
        self.asistente = True
        # poses con rampa: se interpola de pose_desde a pose_hacia
        self.nombre_pose = "de pie"
        self.pose_desde = pose_de_pie()
        self.pose_hacia = pose_de_pie()
        self.avance_pose = 1.0      # 0 = pose_desde, 1 = pose_hacia
        self.ajustes = {}           # offsets de jog (nombre junta -> rad)
        self.grupo = 0
        # marcha
        self.marcha = None          # None, "adelante", "atras", "izquierda", "derecha"
        self.intensidad = 0.0       # 0 = quieto de pie, 1 = marcha completa (rampa)
        self.avance = 0.0           # -1..1: direccion de la zancada (rampa)
        self.giro = 0.0             # -1..1: giro por paso (rampa)
        self.t_marcha = 0.0         # reloj del patron de pasos
        # teclado
        self.tecla_anterior = "-"
        self.ultima_tecla = "-"
        self.mensaje = ""


def crear_mundo(modo=p.DIRECT):
    """Conecta PyBullet (p.GUI o p.DIRECT), carga piso y Atlas, y lo deja
    de pie, asentado y con el asistente prendido. Devuelve el Estado.
    Si faltan los modelos, intenta bajarlos una vez con
    ../descargar_modelos.py; si no se puede (sin internet), avisa y sale."""
    if not URDF_ATLAS.exists():
        # Primera vez (por ejemplo, recien clonado): se corre el descargador
        # en un proceso aparte con el MISMO Python, para no repetir su codigo.
        import subprocess
        print("Faltan los modelos de Atlas: bajandolos una vez con descargar_modelos.py ...", flush=True)
        subprocess.run([sys.executable, str(MODELOS.parent / "descargar_modelos.py")])
    if not URDF_ATLAS.exists():
        print("Faltan los modelos: corra `entorno\\Scripts\\python descargar_modelos.py` "
              "en la carpeta del taller")
        sys.exit(1)
    p.connect(modo)
    if modo == p.GUI:
        # se oculta el panel de imagenes de camara (no se usan) y se deja el de botones
        p.configureDebugVisualizer(p.COV_ENABLE_RGB_BUFFER_PREVIEW, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_DEPTH_BUFFER_PREVIEW, 0)
        p.configureDebugVisualizer(p.COV_ENABLE_SEGMENTATION_MARK_PREVIEW, 0)
    p.setGravity(0, 0, -GRAVEDAD)
    p.setTimeStep(PASO_FISICA)
    piso = p.loadURDF(str(URDF_PISO))

    e = Estado()
    e.atlas = p.loadURDF(str(URDF_ATLAS), [0, 0, 1.0])
    # Friccion 1,0 en el piso y en las suelas (por defecto el piso trae 1,0
    # y los links 0,5): con 0,5 las suelas patinan un poco al empujar.
    p.changeDynamics(piso, -1, lateralFriction=1.0)

    # Masa total = la de la base (pelvis) + la de cada link. Se suma dentro del
    # bucle de las juntas de giro: en este URDF TODAS las juntas son de giro
    # (no hay juntas fijas que dejen links afuera), asi que da la masa
    # completa, 182,4 kg (comprobado sumando todos los links).
    e.masa = p.getDynamicsInfo(e.atlas, -1)[0]
    for j in range(p.getNumJoints(e.atlas)):
        info = p.getJointInfo(e.atlas, j)
        if info[2] != p.JOINT_REVOLUTE:
            continue
        nombre = info[1].decode()
        e.juntas[nombre] = j
        e.indices.append(j)
        e.limites[nombre] = (info[8], info[9])
        fuerza = info[10]
        if "_leg_" in nombre:
            fuerza = max(fuerza, FUERZA_PIERNA)
        elif nombre.startswith("back_"):
            fuerza = max(fuerza, FUERZA_TORSO)
        e.fuerzas.append(fuerza)
        e.masa += p.getDynamicsInfo(e.atlas, j)[0]
    for lado in "lr":
        p.changeDynamics(e.atlas, e.juntas[lado + "_leg_akx"], lateralFriction=1.0)

    reiniciar_todo(e)
    return e


def junta(e, nombre):
    """Indice de una junta por su nombre (p. ej. 'l_leg_kny')."""
    return e.juntas[nombre]


# ======================================================================
# Lectura del estado del robot
# ======================================================================
def leer_estado(e):
    """Devuelve un dict con pos (x,y,z de la pelvis), yaw (grados),
    inclinacion (rad) y caido (bool)."""
    pos, orn = p.getBasePositionAndOrientation(e.atlas)
    m = p.getMatrixFromQuaternion(orn)
    # m[8] es la componente z del eje z de la pelvis: 1 si esta derecha.
    inclinacion = math.acos(max(-1.0, min(1.0, m[8])))
    caido = pos[2] < ALTURA_MIN_DE_PIE or inclinacion > INCLINACION_MAX
    yaw = math.degrees(p.getEulerFromQuaternion(orn)[2])
    return {"pos": pos, "yaw": yaw, "inclinacion": inclinacion, "caido": caido}


# ======================================================================
# Asistente de equilibrio
# ======================================================================
def asistente(e, activo):
    """Prende (True) o apaga (False) el asistente de equilibrio."""
    e.asistente = bool(activo)
    e.mensaje = "Asistente " + ("ON" if e.asistente else "OFF")


def aplicar_asistente(e):
    """Fuerzas del arnes virtual para ESTE paso de fisica (PyBullet borra
    las fuerzas externas despues de cada stepSimulation, por eso se llama
    en cada paso).

    Solo actua si el robot esta de pie: un arnes no levanta del piso a un
    robot tirado (para eso esta "ponerlo de pie"), y empujar con 2500 N*m a
    un cuerpo acostado lo haria dar vueltas sobre el piso.
    """
    if not e.asistente:
        return
    estado = leer_estado(e)
    if estado["caido"]:
        return
    pos, orn = p.getBasePositionAndOrientation(e.atlas)
    vel, w = p.getBaseVelocity(e.atlas)

    # 1. fuerza vertical: fraccion del peso + amortiguador. Cero en x e y.
    fz = ALFA_PESO * e.masa * GRAVEDAD - AMORT_VERTICAL * vel[2]
    p.applyExternalForce(e.atlas, -1, [0, 0, fz], pos, p.WORLD_FRAME)

    # 2. torque para enderezar: el eje de giro es up x z_mundo (perpendicular
    # a los dos), y el angulo es la inclinacion. up x (0,0,1) = (uy, -ux, 0):
    # nunca tiene componente z, asi que el yaw queda libre.
    m = p.getMatrixFromQuaternion(orn)
    up = (m[2], m[5], m[8])            # eje z de la pelvis en el mundo
    eje = (up[1], -up[0], 0.0)
    norma = math.hypot(eje[0], eje[1])
    angulo = estado["inclinacion"]
    if norma > 1e-9:
        error = (eje[0] / norma * angulo, eje[1] / norma * angulo)
    else:
        error = (0.0, 0.0)
    tx = KP_ENDEREZAR * error[0] - KD_ENDEREZAR * w[0]
    ty = KP_ENDEREZAR * error[1] - KD_ENDEREZAR * w[1]
    modulo = math.hypot(tx, ty)
    if modulo > TORQUE_MAX_ASISTENTE:
        tx, ty = tx * TORQUE_MAX_ASISTENTE / modulo, ty * TORQUE_MAX_ASISTENTE / modulo
    p.applyExternalTorque(e.atlas, -1, [tx, ty, 0], p.WORLD_FRAME)


# ======================================================================
# Poses con rampa y jog
# ======================================================================
def _suave(s):
    """Rampa en S (smoothstep): arranca y termina con velocidad cero, asi
    los motores no reciben un escalon ni al empezar ni al terminar."""
    return s * s * (3 - 2 * s)


def pose_actual(e):
    """Pose base que se esta pidiendo ahora (rampa entre dos poses + jog),
    sin la marcha encima."""
    s = _suave(e.avance_pose)
    nombres = set(e.pose_desde) | set(e.pose_hacia) | set(e.ajustes)
    pose = {}
    for n in nombres:
        a = e.pose_desde.get(n, 0.0)
        b = e.pose_hacia.get(n, 0.0)
        pose[n] = a + (b - a) * s + e.ajustes.get(n, 0.0)
    return pose


def pedir_pose(e, nombre):
    """Cambia a una pose con rampa. Lo que se haya movido a mano (jog) se
    funde en el punto de partida y se borra, asi no hay salto."""
    e.pose_desde = pose_actual(e)
    e.pose_hacia = POSES[nombre]()
    e.ajustes = {}
    e.avance_pose = 0.0
    e.nombre_pose = nombre
    e.mensaje = "Pose: " + nombre


def jog(e, cual, signo, veces=1):
    """Mueve la junta A (cual=0) o B (cual=1) del grupo activo."""
    _, *juntas_jog = GRUPOS[e.grupo]
    nombre_jog, lista = juntas_jog[cual]
    pose = pose_actual(e)
    for _ in range(veces):
        for nombre, coef in lista:
            nuevo = e.ajustes.get(nombre, 0.0) + signo * coef * PASO_JOG
            # no pasar del limite del URDF (el motor lo pediria y la junta
            # quedaria apretada contra el tope)
            inf, sup = e.limites[nombre]
            base = pose.get(nombre, 0.0) - e.ajustes.get(nombre, 0.0)
            nuevo = min(max(nuevo, inf - base), sup - base)
            e.ajustes[nombre] = nuevo
    e.mensaje = f"{GRUPOS[e.grupo][0]}: {nombre_jog} {'+' if signo > 0 else '-'}"


def siguiente_grupo(e):
    """Pasa al siguiente grupo de juntas (brazo izq -> brazo der -> torso y
    cabeza -> piernas -> brazo izq ...)."""
    e.grupo = (e.grupo + 1) % len(GRUPOS)
    e.mensaje = "Grupo: " + GRUPOS[e.grupo][0]


# ======================================================================
# Marcha
# ======================================================================
def avanzar_marcha(e):
    """Un paso de fisica de las rampas de la marcha: la intensidad sube a 1
    en RAMPA segundos mientras haya una marcha pedida y baja a 0 al
    soltarla; la zancada (avance) y el giro tambien se mueven con rampa, asi
    que pasar de caminar a girar no da tirones."""
    d = PASO_FISICA / RAMPA
    objetivo_avance = {"adelante": 1.0, "atras": -1.0}.get(e.marcha, 0.0)
    objetivo_giro = {"izquierda": 1.0, "derecha": -1.0}.get(e.marcha, 0.0)
    if e.marcha is not None:
        e.intensidad = min(1.0, e.intensidad + d)
    else:
        e.intensidad = max(0.0, e.intensidad - d)
    e.avance += max(-d, min(d, objetivo_avance - e.avance))
    e.giro += max(-d, min(d, objetivo_giro - e.giro))
    if e.intensidad > 0:
        e.t_marcha += PASO_FISICA


def sumar_marcha(e, pose):
    """Suma a la pose base el patron de pasos (en el instante t_marcha).

    Con fase = 2*pi*f*t, la pierna izquierda va por el aire cuando
    sin(fase) > 0 y la derecha cuando sin(fase) < 0 (fase opuesta):
      - rodilla (kny): se dobla AMPLITUD_LEVANTAR solo en el vuelo -> levanta el pie;
        la cadera se flexiona la mitad para que el pie suba derecho.
      - cadera (hpy): +/- AMPLITUD_ZANCADA*cos(fase): en el vuelo la pierna va
        de atras hacia adelante, en el apoyo de adelante hacia atras (empuja).
      - tobillo (aky): compensa cadera+rodilla para que la suela quede plana.
      - cadera y tobillo laterales (hpx/akx): llevan la pelvis encima del pie
        de apoyo ANTES de levantar el otro (si no, el robot cae hacia el lado
        del pie levantado). hpx positivo corre la pelvis hacia -y (derecha).
      - cadera vertical (hpz), solo al girar: la pierna que vuela se abre
        hacia el lado del giro y, apoyada, vuelve: eso rota la pelvis sobre
        el pie plantado. Asi se gira con los pies, no rotando la base.
    Con intensidad 0 todo lo sumado vale 0, sea cual sea la fase.
    """
    i = e.intensidad
    if i <= 0:
        return pose
    fase = 2 * math.pi * FRECUENCIA_PASO * e.t_marcha
    lateral = i * AMPLITUD_LATERAL * math.sin(fase)
    for lado, signo in (("l", 1.0), ("r", -1.0)):
        vuelo = max(0.0, math.sin(fase) * signo)
        d_cadera = i * (e.avance * AMPLITUD_ZANCADA * math.cos(fase) * signo
                        - 0.5 * AMPLITUD_LEVANTAR * vuelo)
        d_rodilla = i * AMPLITUD_LEVANTAR * vuelo
        pose[lado + "_leg_hpy"] = pose.get(lado + "_leg_hpy", 0.0) + d_cadera
        pose[lado + "_leg_kny"] = pose.get(lado + "_leg_kny", 0.0) + d_rodilla
        pose[lado + "_leg_aky"] = pose.get(lado + "_leg_aky", 0.0) - (d_cadera + d_rodilla)
        pose[lado + "_leg_hpx"] = pose.get(lado + "_leg_hpx", 0.0) + lateral
        pose[lado + "_leg_akx"] = pose.get(lado + "_leg_akx", 0.0) - lateral
        pose[lado + "_leg_hpz"] = (pose.get(lado + "_leg_hpz", 0.0)
                                   - i * e.giro * AMPLITUD_GIRO * math.cos(fase) * signo)
    return pose


def pedir_marcha(e, marcha):
    """marcha: 'adelante', 'atras', 'izquierda', 'derecha' o None (parar).
    Para caminar hace falta estar de pie y en la pose "de pie": si estaba
    agachado o con brazos/piernas movidos, vuelve a la pose de pie (con
    rampa) al mismo tiempo que arranca la marcha."""
    if marcha is not None:
        if leer_estado(e)["caido"]:
            e.mensaje = "Esta en el piso: B para ponerlo de pie"
            return
        if e.nombre_pose not in ("de pie", "saludar", "brazos arriba") or any(
                "_leg_" in n or n.startswith("back_") for n in e.ajustes):
            pedir_pose(e, "de pie")
        e.mensaje = "Marcha: " + marcha
    e.marcha = marcha


# ======================================================================
# Ponerlo de pie / reiniciar
# ======================================================================
def _colocar_de_pie(e, x, y, yaw):
    """Pone las juntas en la pose de pie y la pelvis justo a la altura en
    que las suelas tocan el piso (medida con el AABB de los pies, no
    adivinada), sin velocidad."""
    pose = pose_de_pie()
    for nombre, j in e.juntas.items():
        p.resetJointState(e.atlas, j, pose.get(nombre, 0.0), 0.0)
    orn = p.getQuaternionFromEuler([0, 0, yaw])
    p.resetBasePositionAndOrientation(e.atlas, [x, y, 1.5], orn)
    suela = min(p.getAABB(e.atlas, e.juntas[l + "_leg_akx"])[0][2] for l in "lr")
    p.resetBasePositionAndOrientation(e.atlas, [x, y, 1.5 - suela + 0.002], orn)
    p.resetBaseVelocity(e.atlas, [0, 0, 0], [0, 0, 0])


def _reset_control(e):
    e.marcha = None
    e.intensidad = e.avance = e.giro = 0.0
    e.t_marcha = 0.0
    e.nombre_pose = "de pie"
    e.pose_desde = pose_de_pie()
    e.pose_hacia = pose_de_pie()
    e.avance_pose = 1.0
    e.ajustes = {}


def poner_de_pie(e):
    """"Grua": lo levanta en el lugar donde esta (misma x, y y rumbo), en la
    pose de pie, y lo deja asentarse PASOS_ASENTAR pasos con el asistente
    prendido (aunque estuviera apagado). Despues el asistente vuelve a como
    lo tenia el usuario: asi, con el asistente OFF, se puede volver a
    probar si se sostiene solo."""
    estado = leer_estado(e)
    x, y, _ = estado["pos"]
    _reset_control(e)
    _colocar_de_pie(e, x, y, math.radians(estado["yaw"]))
    guardado = e.asistente
    e.asistente = True
    for _ in range(PASOS_ASENTAR):
        paso(e)
    e.asistente = guardado
    e.mensaje = "De pie (asentado)"


def reiniciar_todo(e):
    """Vuelve al origen, mirando a +x, asistente ON, grupo 0, asentado."""
    _reset_control(e)
    e.grupo = 0
    e.asistente = True
    _colocar_de_pie(e, 0.0, 0.0, 0.0)
    for _ in range(PASOS_ASENTAR):
        paso(e)
    e.mensaje = "Reiniciado"


# ======================================================================
# Un paso de fisica
# ======================================================================
def objetivos_motores(e):
    """Angulo pedido a cada una de las 30 juntas en este instante."""
    pose = pose_actual(e)
    if e.nombre_pose == "saludar" and e.avance_pose >= 1.0:
        # vaiven del saludo: el codo derecho oscila 1,5 veces por segundo
        pose["r_arm_elx"] = pose.get("r_arm_elx", 0.0) + 0.35 * math.sin(2 * math.pi * 1.5 * e.t)
    pose = sumar_marcha(e, pose)
    return [pose.get(n, 0.0) for n in e.juntas]


def paso(e):
    """Un paso de fisica (1/500 s): rampas, motores, asistente y step."""
    e.avance_pose = min(1.0, e.avance_pose + PASO_FISICA / RAMPA)
    avanzar_marcha(e)
    # Seguridad: si se cayo, se deja de pedir la marcha (solo lo
    # arrastraria por el piso), como un robot real que detecta la caida.
    if e.marcha is not None and leer_estado(e)["caido"]:
        e.marcha = None
        e.mensaje = "Se cayo: B para ponerlo de pie"
    # POSITION_CONTROL en las 30 juntas de una vez (setJointMotorControlArray
    # es una sola llamada en vez de 30).
    p.setJointMotorControlArray(e.atlas, e.indices, p.POSITION_CONTROL,
                                targetPositions=objetivos_motores(e), forces=e.fuerzas)
    aplicar_asistente(e)
    p.stepSimulation()
    e.t += PASO_FISICA


# ======================================================================
# Teclas
# ======================================================================
TECLAS_MARCHA = {"8": "adelante", "2": "atras", "4": "izquierda", "6": "derecha"}


def procesar_tecla(e, tecla):
    """Interpreta UNA linea "TECLA:x" del ESP32 (llegan cada ~50 ms
    mientras se sostiene la tecla; "-" = ninguna).

      - Acciones de un golpe (A, B, C, D, #, *, 5, 0): solo en el FLANCO,
        cuando la tecla cambia. Si no, sostener A 1 s la conmutaria 20 veces.
      - Jog (1, 3, 7, 9): en CADA repeticion; sostener = seguir moviendo.
      - Marcha (8, 2, 4, 6): en el flanco al empezar a sostenerla se arranca
        y en el flanco al soltarla se frena (con rampa). Por eso el boton
        "Caminar" de la ventana sigue sirviendo con el ESP32 conectado: las
        "TECLA:-" repetidas no son flancos y no lo apagan.
    """
    anterior, e.tecla_anterior = e.tecla_anterior, tecla
    e.ultima_tecla = tecla
    flanco = tecla != anterior

    # marcha sostenida
    if flanco and anterior in TECLAS_MARCHA and e.marcha == TECLAS_MARCHA[anterior]:
        pedir_marcha(e, None)
    if flanco and tecla in TECLAS_MARCHA:
        pedir_marcha(e, TECLAS_MARCHA[tecla])

    # jog en cada repeticion
    if tecla in ("1", "3", "7", "9"):
        jog(e, 0 if tecla in "13" else 1, -1 if tecla in "17" else 1)

    if not flanco:
        return
    if tecla == "A":
        asistente(e, not e.asistente)
    elif tecla == "B":
        poner_de_pie(e)
    elif tecla == "C":
        pedir_pose(e, "saludar")
    elif tecla == "D":
        e.marcha = None
        pedir_pose(e, "agachado")
    elif tecla == "#":
        pedir_pose(e, "brazos arriba")
    elif tecla == "5":
        e.marcha = None
        pedir_pose(e, "de pie")
    elif tecla == "*":
        siguiente_grupo(e)
    elif tecla == "0":
        reiniciar_todo(e)


def simular(e, segundos, tecla="-"):
    """Simula `segundos` como si el ESP32 mandara "TECLA:<tecla>" cada 50 ms
    (para pruebas y capturas en DIRECT)."""
    pasos_por_tecla = round(INTERVALO_TECLA / PASO_FISICA)
    for k in range(round(segundos / PASO_FISICA)):
        if k % pasos_por_tecla == 0:
            procesar_tecla(e, tecla)
        paso(e)


def texto_estado(e, linea_cruda=None):
    """Las 3 lineas que se muestran arriba del robot."""
    caido = leer_estado(e)["caido"]
    nombre, (a, _), (b, _) = GRUPOS[e.grupo]
    lineas = [
        f"ASISTENTE: {'ON' if e.asistente else 'OFF'}   |   ESTADO: {'CAIDO' if caido else 'de pie'}",
        f"Grupo: {nombre} (1/3 {a}, 7/9 {b})   |   Marcha: {e.marcha or 'quieto'}",
        f"Tecla: {e.ultima_tecla}   |   ESP32: {linea_cruda if linea_cruda is not None else 'no conectado (usa los botones)'}",
    ]
    return lineas, caido


# ======================================================================
# Programa con ventana (GUI)
# ======================================================================
def main():
    import serial

    try:
        ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.05)
        time.sleep(2)  # el ESP32 se reinicia al abrir el puerto
        print(f"ESP32 conectado en {PUERTO_SERIAL}: el teclado maneja a Atlas.")
        linea_cruda = "esperando datos..."
    except serial.SerialException:
        ser = None
        linea_cruda = None
        print(f"No se encontro el ESP32 en {PUERTO_SERIAL}: usa los botones de la ventana.")

    e = crear_mundo(p.GUI)
    p.resetDebugVisualizerCamera(cameraDistance=3.2, cameraYaw=50, cameraPitch=-15,
                                 cameraTargetPosition=[0, 0, 0.9])

    # Botones: se crean UNA sola vez (crearlos dentro del bucle llenaria el
    # panel). Un boton de addUserDebugParameter (min 1 > max 0) es un
    # contador de clicks: se detecta el click cuando el valor cambia.
    acciones = [
        ("Asistente ON/OFF (A)", lambda: asistente(e, not e.asistente)),
        ("Ponerlo de pie (B)", lambda: poner_de_pie(e)),
        ("Saludar (C)", lambda: pedir_pose(e, "saludar")),
        ("Agacharse (D)", lambda: (pedir_marcha(e, None), pedir_pose(e, "agachado"))),
        ("Brazos arriba (#)", lambda: pedir_pose(e, "brazos arriba")),
        ("De pie / detener (5)", lambda: (pedir_marcha(e, None), pedir_pose(e, "de pie"))),
        ("Caminar adelante on/off (8)",
         lambda: pedir_marcha(e, None if e.marcha == "adelante" else "adelante")),
        ("Caminar atras on/off (2)",
         lambda: pedir_marcha(e, None if e.marcha == "atras" else "atras")),
        ("Girar izquierda on/off (4)",
         lambda: pedir_marcha(e, None if e.marcha == "izquierda" else "izquierda")),
        ("Girar derecha on/off (6)",
         lambda: pedir_marcha(e, None if e.marcha == "derecha" else "derecha")),
        ("Siguiente grupo (*)", lambda: siguiente_grupo(e)),
        ("Junta A - (1)", lambda: jog(e, 0, -1, JOG_POR_CLICK)),
        ("Junta A + (3)", lambda: jog(e, 0, 1, JOG_POR_CLICK)),
        ("Junta B - (7)", lambda: jog(e, 1, -1, JOG_POR_CLICK)),
        ("Junta B + (9)", lambda: jog(e, 1, 1, JOG_POR_CLICK)),
        ("Reiniciar todo (0)", lambda: reiniciar_todo(e)),
    ]
    botones = [(p.addUserDebugParameter(nombre, 1, 0, 0), accion) for nombre, accion in acciones]
    clicks = [0] * len(botones)

    ids_texto = [None, None, None]
    textos_previos = [None, None, None]
    print("Ventana abierta. Cierra la ventana o Ctrl+C en la terminal para salir.")

    # Cada vuelta del bucle simula PASOS_POR_VUELTA pasos (20 ms) y despues
    # lee teclado, botones, texto y camara: leer 16 botones 500 veces por
    # segundo frenaria la ventana sin ganar nada.
    PASOS_POR_VUELTA = 10
    reloj = time.perf_counter()
    try:
        while p.isConnected():
            # 1) teclado fisico: solo si YA hay datos (in_waiting), nunca un
            #    readline() a secas que bloquee la fisica; y se drena TODO el
            #    buffer (while) para no quedar atrasado.
            try:
                while ser is not None and ser.in_waiting:
                    linea = ser.readline().decode(errors="ignore").strip()
                    linea_cruda = linea
                    if linea.startswith("TECLA:"):
                        procesar_tecla(e, linea.split(":", 1)[1])
            except serial.SerialException:
                print("Se perdio la conexion con el ESP32: sigue con los botones de la ventana.")
                ser = None
                linea_cruda = None

            # 2) botones de la ventana (se leen siempre, haya o no ESP32)
            for k, (boton, accion) in enumerate(botones):
                valor = p.readUserDebugParameter(boton)
                if valor != clicks[k]:
                    clicks[k] = valor
                    accion()

            # 3) fisica
            for _ in range(PASOS_POR_VUELTA):
                paso(e)

            # 4) texto arriba del robot (solo se reescribe si cambio o si el
            #    robot se movio: addUserDebugText es caro) y camara que lo sigue
            estado = leer_estado(e)
            x, y, z = estado["pos"]
            lineas, caido = texto_estado(e, linea_cruda)
            for k, texto in enumerate(lineas):
                posicion = [x, y, 2.35 - 0.17 * k]
                clave = (texto, round(x, 1), round(y, 1))
                if clave != textos_previos[k]:
                    textos_previos[k] = clave
                    color = [1, 0.25, 0.25] if (k == 0 and (caido or not e.asistente)) else \
                            [0.2, 0.9, 0.3] if k == 0 else [1, 1, 0.4] if k == 2 else [1, 1, 1]
                    opciones = dict(textColorRGB=color, textSize=1.3)
                    if ids_texto[k] is not None:
                        opciones["replaceItemUniqueId"] = ids_texto[k]
                    ids_texto[k] = p.addUserDebugText(texto, posicion, **opciones)
            camara = p.getDebugVisualizerCamera()
            p.resetDebugVisualizerCamera(camara[10], camara[8], camara[9], [x, y, 0.9])

            # 5) tiempo real: dormir solo lo que sobre (si la fisica va
            #    atrasada, no se duerme nada)
            reloj += PASOS_POR_VUELTA * PASO_FISICA
            espera = reloj - time.perf_counter()
            if espera > 0:
                time.sleep(espera)
            else:
                reloj = time.perf_counter()
    except KeyboardInterrupt:
        pass
    except p.error:
        # al cerrar la ventana, la siguiente llamada a PyBullet falla
        print("Ventana cerrada.")
    finally:
        if ser is not None:
            ser.close()
        if p.isConnected():
            p.disconnect()


if __name__ == "__main__":
    main()
