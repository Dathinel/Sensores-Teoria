"""Videos (MP4 + GIF) de los tres puntos del taller, sin ventana.

PyBullet en modo DIRECT + getCameraImage con el renderizador por software
(ER_TINY_RENDERER, el mismo de capturar_modelos.py): funciona aunque no haya
GPU. Cada cuadro se manda crudo (RGB) por una tuberia a ffmpeg.

Las teclas son de VERDAD: el script simula al ESP32 mandando "TECLA:x" cada
50 ms (o "TECLA:-" si no hay nada pulsado) y esas lineas pasan por las MISMAS
funciones del modulo de cada punto que procesan el teclado (Mando.tecla en
los drones, procesar_linea en Baxter, procesar_tecla en Atlas). Asi el video
muestra exactamente lo que hace el teclado, con sus flancos y repeticiones.

Uso (desde la carpeta del taller):

    entorno\\Scripts\\python grabar_videos.py                 # los cuatro
    entorno\\Scripts\\python grabar_videos.py drones          # solo uno:
    entorno\\Scripts\\python grabar_videos.py baxter          #   drones, baxter,
    entorno\\Scripts\\python grabar_videos.py atlas-con       #   atlas-con,
    entorno\\Scripts\\python grabar_videos.py atlas-sin       #   atlas-sin

Genera:
    punto-a-drones-waypoints/video/drones-mision.mp4 (+ .gif)
    punto-b-brazo-tipo-baxter/video/baxter-demo.mp4 (+ .gif)
    punto-c-atlas/video/atlas-con-asistente.mp4 (+ .gif)
    punto-c-atlas/video/atlas-sin-asistente.mp4 (+ .gif)

Por que un proceso por video: los modulos del taller usan la conexion POR
DEFECTO de PyBullet y solo puede haber una por proceso. Sin argumentos, el
script se relanza a si mismo una vez por video (como capturar_modelos.py).

Rotulos: los textos de depuracion (addUserDebugText) no salen en
getCameraImage. Por eso se graban en dos pasadas: 1) la simulacion manda los
cuadros a un MP4 intermedio y anota en que segundo cambia cada rotulo
("TECLA 8: caminar adelante", "ASISTENTE OFF"...); 2) ffmpeg quema esos
rotulos con drawtext (uno por tramo, con enable entre el segundo a y el b) y saca el
MP4 final (H.264, yuv420p) y el GIF (paleta propia; si pasa de ~3,5 MB se
repite con menos cuadros por segundo y menos resolucion).
"""

import glob
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True   # no dejar __pycache__ al importar los modulos del taller

import numpy as np
import pybullet as p

TALLER = Path(__file__).resolve().parent
CARPETA_DRONES = TALLER / "punto-a-drones-waypoints"
CARPETA_BAXTER = TALLER / "punto-b-brazo-tipo-baxter"
CARPETA_ATLAS = TALLER / "punto-c-atlas"

ANCHO, ALTO, FPS = 800, 500, 25
GIF_MAX_MB = 3.5
# (cuadros por segundo, ancho en px, colores) del GIF, de mejor a mas liviano
GIF_INTENTOS = [(12, 560, 128), (10, 520, 96), (8, 480, 96), (8, 420, 64), (6, 400, 64), (5, 360, 48)]
FUENTE = "C\\:/Windows/Fonts/arialbd.ttf"      # ':' escapado para el filtro de ffmpeg
INTERVALO_TECLA = 0.05                         # el ESP32 manda una linea cada 50 ms


def buscar_ffmpeg():
    """ffmpeg (instalado con winget): primero el PATH, despues la carpeta de winget."""
    ruta = shutil.which("ffmpeg")
    if ruta:
        return ruta
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
    candidatos = sorted(glob.glob(os.path.join(base, "Gyan.FFmpeg*", "*", "bin", "ffmpeg.exe")))
    return candidatos[-1] if candidatos else None


def duracion(ruta):
    """Duracion en segundos (con ffprobe, que viene junto a ffmpeg)."""
    ffprobe = str(Path(buscar_ffmpeg()).with_name("ffprobe" + Path(buscar_ffmpeg()).suffix))
    salida = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ruta)],
                            capture_output=True, text=True).stdout.strip()
    try:
        return float(salida)
    except ValueError:
        return float("nan")


# ======================================================================
# Camara
# ======================================================================
def matrices(objetivo, distancia, yaw, pitch):
    vista = p.computeViewMatrixFromYawPitchRoll(cameraTargetPosition=list(objetivo), distance=distancia,
                                                yaw=yaw, pitch=pitch, roll=0, upAxisIndex=2)
    proy = p.computeProjectionMatrixFOV(fov=50, aspect=ANCHO / ALTO, nearVal=0.05, farVal=40)
    return vista, proy


def foto(vista, proy, luz):
    """Un cuadro RGB (alto, ancho, 3) con los mismos ajustes de luz de capturar_modelos.py."""
    _, _, rgba, _, _ = p.getCameraImage(
        ANCHO, ALTO, vista, proy, renderer=p.ER_TINY_RENDERER, shadow=1,
        lightDirection=list(luz), lightColor=[1.0, 1.0, 1.0], lightDistance=6,
        lightAmbientCoeff=0.55, lightDiffuseCoeff=0.55, lightSpecularCoeff=0.08)
    return np.reshape(np.asarray(rgba, np.uint8), (ALTO, ANCHO, 4))[:, :, :3].copy()


def proyectar(punto, vista, proy):
    """Pixel (x, y) donde cae un punto del mundo, o None si esta detras de la camara."""
    V = np.array(vista).reshape(4, 4, order="F")
    P = np.array(proy).reshape(4, 4, order="F")
    c = P @ V @ np.array([*punto, 1.0])
    if c[3] <= 0:
        return None
    x, y = c[0] / c[3], c[1] / c[3]
    return int((x + 1) / 2 * ANCHO), int((1 - y) / 2 * ALTO)


class Seguir:
    """Camara que sigue al robot con una "zona muerta": mientras el robot
    este a menos de `radio` metros del centro del encuadre, la camara no se
    mueve; si se sale, el centro se desliza (suave, pasa-bajos) lo justo
    para alcanzarlo. Asi no tiembla con cada paso, y como entre cuadros
    seguidos casi todo el fondo queda igual, el GIF pesa mucho menos (con
    una camara que se mueve siempre, cada cuadro del GIF es nuevo entero)."""

    def __init__(self, radio=0.5, alfa=0.08):
        self.radio, self.alfa, self.v, self.meta = radio, alfa, None, None

    def __call__(self, valor):
        valor = np.asarray(valor, float)
        if self.v is None:
            self.v, self.meta = valor.copy(), valor.copy()
            return self.v
        lejos = valor - self.meta
        d = float(np.linalg.norm(lejos))
        if d > self.radio:
            self.meta = self.meta + lejos * (1 - self.radio / d)
        paso = self.meta - self.v
        if float(np.linalg.norm(paso)) > 1e-3:
            self.v = self.v + self.alfa * paso
        return self.v


# Letras 5x7 para marcar los puntos A, B, C de los drones sobre la imagen
LETRAS = {
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"],
}


def letra(img, ch, centro, escala=4, color=(255, 255, 255)):
    """Dibuja una letra de LETRAS centrada en `centro`, con borde negro."""
    filas = LETRAS[ch]
    x0 = centro[0] - 5 * escala // 2
    y0 = centro[1] - 7 * escala // 2
    for capa, (col, borde) in enumerate((((0, 0, 0), 2), (color, 0))):
        for i, fila in enumerate(filas):
            for j, c in enumerate(fila):
                if c != "#":
                    continue
                a, b = y0 + i * escala - borde, x0 + j * escala - borde
                a2, b2 = a + escala + 2 * borde, b + escala + 2 * borde
                a, b, a2, b2 = max(a, 0), max(b, 0), min(a2, ALTO), min(b2, ANCHO)
                if a < a2 and b < b2:
                    img[a:a2, b:b2] = col


# ======================================================================
# Grabadora: cuadros por tuberia a ffmpeg + rotulos por tramos
# ======================================================================
class Grabadora:
    """`tick(dt)` se llama en CADA paso de fisica; cuando el reloj simulado
    alcanza el siguiente cuadro, llama a `componer()` (que devuelve la
    imagen) y lo manda a ffmpeg. `rotulo(lugar, texto)` abre un tramo de
    texto desde el segundo actual (y cierra el anterior de ese lugar)."""

    # lugar -> (x, y, tamano, color por defecto)
    LUGARES = {"tecla": ("14", "12", 25, "yellow"),
               "estado": ("14", "50", 22, "white"),
               "titulo": ("14", "h-th-12", 17, "white")}

    def __init__(self, mp4, componer):
        self.mp4 = Path(mp4)
        self.componer = componer
        self.ffmpeg = buscar_ffmpeg()
        if self.ffmpeg is None:
            sys.exit("No se encontro ffmpeg (winget install Gyan.FFmpeg)")
        self.tmp = Path(tempfile.mkdtemp(prefix="taller_video_"))
        self.crudo = self.tmp / "crudo.mp4"
        self.proc = subprocess.Popen(
            [self.ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{ANCHO}x{ALTO}", "-r", str(FPS), "-i", "-",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", str(self.crudo)],
            stdin=subprocess.PIPE)
        self.t_sim = 0.0
        self.proximo = 0.0
        self.cuadros = 0
        self.tramos = []          # [lugar, t0, t1, texto, color]
        self.abiertos = {}        # lugar -> indice en tramos

    @property
    def t(self):
        return self.cuadros / FPS

    def tick(self, dt):
        self.t_sim += dt
        while self.t_sim >= self.proximo:
            self.proximo += 1.0 / FPS
            img = self.componer()
            self.proc.stdin.write(np.ascontiguousarray(img, np.uint8).tobytes())
            self.cuadros += 1
            if self.cuadros % (FPS * 5) == 0:
                print(f"  {self.t:5.1f} s de video", flush=True)

    def rotulo(self, lugar, texto, color=None):
        if lugar in self.abiertos:
            tramo = self.tramos[self.abiertos[lugar]]
            if tramo[3] == texto and tramo[4] == (color or self.LUGARES[lugar][3]):
                return
            tramo[2] = self.t
            del self.abiertos[lugar]
        if texto:
            self.abiertos[lugar] = len(self.tramos)
            self.tramos.append([lugar, self.t, None, texto, color or self.LUGARES[lugar][3]])

    def cerrar(self):
        """Cierra la tuberia, quema los rotulos y hace el MP4 final y el GIF."""
        self.proc.stdin.close()
        self.proc.wait()
        fin = self.t
        filtros = []
        for k, (lugar, t0, t1, texto, color) in enumerate(self.tramos):
            t1 = fin + 1 if t1 is None else t1
            if t1 <= t0:
                continue
            # el texto va en un archivo (textfile): asi no hay que escapar ':', '#', '*'...
            (self.tmp / f"r{k}.txt").write_text(texto, encoding="utf-8")
            x, y, tam, _ = self.LUGARES[lugar]
            filtros.append(
                f"drawtext=fontfile='{FUENTE}':textfile='r{k}.txt':expansion=none:x={x}:y={y}:"
                f"fontsize={tam}:fontcolor={color}:box=1:boxcolor=black@0.55:boxborderw=7:"
                f"enable='gte(t,{t0:.3f})*lt(t,{t1:.3f})'")
        self.mp4.parent.mkdir(parents=True, exist_ok=True)
        vf = ",".join(filtros) or "null"
        # cwd = carpeta temporal: los textfile van con ruta relativa (sin 'C:')
        subprocess.run([self.ffmpeg, "-y", "-loglevel", "error", "-i", str(self.crudo), "-vf", vf,
                        "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(self.mp4)], check=True, cwd=self.tmp)
        gif = self.mp4.with_suffix(".gif")
        for fps, ancho, colores in GIF_INTENTOS:
            filtro = (f"fps={fps},scale={ancho}:-1:flags=lanczos,split[a][b];"
                      f"[a]palettegen=max_colors={colores}:stats_mode=diff[pal];"
                      f"[b][pal]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle")
            subprocess.run([self.ffmpeg, "-y", "-loglevel", "error", "-i", str(self.mp4), "-vf", filtro,
                            "-loop", "0", str(gif)], check=True)
            if gif.stat().st_size / 1e6 <= GIF_MAX_MB:
                break
        shutil.rmtree(self.tmp, ignore_errors=True)
        print(f"  listo: {self.mp4.name} ({self.mp4.stat().st_size / 1e6:.2f} MB, {fin:.1f} s), "
              f"{gif.name} ({gif.stat().st_size / 1e6:.2f} MB, {fps} fps, {ancho} px)")


# ======================================================================
# a) Drones: despegue y mision A -> B -> C
# ======================================================================
DESCRIPCION_DRONES = {"*": "despegar", "0": "mision automatica A -> B -> C", "#": "aterrizar", "-": ""}


def video_drones():
    sys.path.insert(0, str(CARPETA_DRONES))
    import drones_pybullet as D

    lider, seguidores = D.crear_mundo(con_ventana=False)
    mando = D.Mando(lider)
    drones = [lider] + seguidores
    seguir = Seguir(radio=0.7, alfa=0.05)
    marcas = []       # rastro del lider (esferitas amarillas, solo visuales)
    forma_rastro = p.createVisualShape(p.GEOM_SPHERE, radius=0.018, rgbaColor=[1, 0.85, 0.1, 1])

    def componer():
        pos = np.array([p.getBasePositionAndOrientation(d.id)[0] for d in drones])
        centro = seguir([pos[:, 0].mean(), pos[:, 1].mean(), 0.6])
        vista, proy = matrices(centro, 4.8, 30, -26)
        img = foto(vista, proy, (-0.6, -0.4, 1.0))
        for nombre, punto in D.PUNTOS.items():
            px = proyectar((punto[0], punto[1], punto[2] + 0.30), vista, proy)
            if px and 0 <= px[0] < ANCHO and 0 <= px[1] < ALTO:
                letra(img, nombre, px)
        return img

    g = Grabadora(CARPETA_DRONES / "video" / "drones-mision.mp4", componer)
    g.rotulo("titulo", "Punto a - 5 drones en V (lider rojo). Teclas del ESP32 simuladas: TECLA:x cada 50 ms")
    estado = {"paso": 0, "llegadas": []}

    def un_paso():
        pos, vel = lider.paso()
        o = lider.objetivo
        for d, (dx, dy, dz) in zip(seguidores, D.OFFSET_SEGUIDORES):
            d.objetivo[:] = [o[0] + dx, o[1] + dy, max(D.ALTURA_SUELO, o[2] + dz)]
            d.paso()
        llegado = mando.avanzar_mision(pos, vel)
        if llegado:
            estado["llegadas"].append((llegado, round(g.t, 1)))
            print(f"  llego a {llegado} (video t = {g.t:.1f} s)")
        if mando.trazo_reiniciar:
            for m in marcas:
                p.removeBody(m)
            marcas.clear()
            mando.trazo_reiniciar = False
        if estado["paso"] % 24 == 0 and pos[2] > 0.15:
            marcas.append(p.createMultiBody(baseVisualShapeIndex=forma_rastro, basePosition=pos))
        p.stepSimulation()
        estado["paso"] += 1
        g.tick(1 / 240)

    def estado_texto():
        o = lider.objetivo
        if mando.mision:
            return f"Mision: rumbo a {mando.mision[0]}  (faltan {' -> '.join(mando.mision)})", "white"
        llegados = " , ".join(f"{n}" for n, _ in estado["llegadas"])
        extra = f"  |  llego a: {llegados}" if llegados else ""
        return f"Objetivo del lider ({o[0]:.1f}, {o[1]:.1f}, {o[2]:.1f}){extra}", "white"

    def tecla(t, segundos, texto=None, sostener=0.2):
        """Pulsa `t` durante `sostener` s (lineas TECLA:t cada 50 ms) y
        despues TECLA:- hasta completar `segundos`."""
        if texto is not None:
            g.rotulo("tecla", texto)
        pasos_linea = round(INTERVALO_TECLA * 240)
        for k in range(round(segundos / INTERVALO_TECLA)):
            linea = f"TECLA:{t if k * INTERVALO_TECLA < sostener else '-'}"
            if linea.startswith("TECLA:"):           # igual que leer_teclas() del modulo
                mando.tecla(linea.split(":", 1)[1][:1])
            for _ in range(pasos_linea):
                un_paso()
            g.rotulo("estado", *estado_texto())

    tecla("-", 1.5, "Drones en el piso (home)")
    tecla("*", 3.0, "TECLA * : despegar (sube a 1 m)")
    g.rotulo("tecla", "TECLA 0 : mision automatica A -> B -> C")
    tecla("0", 0.5)
    limite = 40
    while (mando.mision or len(estado["llegadas"]) < 3) and limite > 0:
        tecla("-", 0.5)
        limite -= 0.5
    tecla("-", 2.0, "Mision completa: llego a A, B y C")
    tecla("#", 4.0, "TECLA # : aterrizar")
    g.cerrar()
    print(f"  llegadas: {estado['llegadas']}")
    p.disconnect()


# ======================================================================
# b) Baxter: demo D, cambio de brazo, jog del derecho y reponer el cubo
# ======================================================================
def video_baxter():
    sys.path.insert(0, str(CARPETA_BAXTER))
    import brazo_pybullet as B

    estado = B.crear_mundo(p.DIRECT)
    estado.tiempo_real = False
    if not hasattr(estado, "ser"):
        estado.ser = None
    # Baxter tiene la base fija: camara fija (se ven los dos brazos y la mesa)
    vista, proy = matrices([0.60, 0.0, -0.04], 1.9, 115, -28)

    def componer():
        return foto(vista, proy, (-0.6, -0.4, 1.0))

    g = Grabadora(CARPETA_BAXTER / "video" / "baxter-demo.mp4", componer)
    g.rotulo("titulo", "Punto b - Baxter (toms_baxter.urdf). Teclas del ESP32 simuladas: TECLA:x cada 50 ms")

    # Todo lo que simula el modulo pasa por avanzar(): se reemplaza por una
    # version que ademas graba (mover_a, la demo D, etc. la buscan por nombre).
    def avanzar(est, pasos):
        for _ in range(pasos):
            p.stepSimulation()
            g.tick(1 / B.PASOS_POR_SEGUNDO)
            if g.cuadros and g.cuadros % 5 == 0:
                g.rotulo("estado", f"Brazo activo: {est.activo.upper()}")
    B.avanzar = avanzar

    def tecla(t, segundos, texto=None, sostener=0.2):
        if texto is not None:
            g.rotulo("tecla", texto)
        for k in range(round(segundos / INTERVALO_TECLA)):
            B.procesar_linea(estado, f"TECLA:{t if k * INTERVALO_TECLA < sostener else '-'}")
            B.avanzar(estado, round(INTERVALO_TECLA * B.PASOS_POR_SEGUNDO))

    g.rotulo("estado", f"Brazo activo: {estado.activo.upper()}")
    tecla("-", 1.5, "Home: cubo blanco en el ORIGEN (azul), DESTINO verde")
    tecla("D", 1.0, "TECLA D : demo - coge el cubo y lo lleva al DESTINO")
    tecla("-", 1.0, "Demo lista: cubo en el destino")
    tecla("*", 1.2, "TECLA * : cambiar de brazo activo")
    jogs = [("9", "subir (Z+)"), ("8", "Y+ (hacia su izquierda)"), ("4", "X- (hacia el robot)"),
            ("6", "X+ (hacia afuera)"), ("2", "Y- (hacia su derecha)"), ("7", "bajar (Z-)")]
    for t, que in jogs:
        tecla(t, 1.2, f"TECLA {t} (sostenida) : jog {que}", sostener=0.9)
    tecla("5", 1.5, "TECLA 5 : home del brazo activo")
    tecla("0", 2.0, "TECLA 0 : reponer el cubo en el origen")
    g.cerrar()
    p.disconnect()


# ======================================================================
# c) Atlas con y sin asistente
# ======================================================================
def preparar_atlas(nombre_mp4, titulo):
    sys.path.insert(0, str(CARPETA_ATLAS))
    import atlas_pybullet as A

    e = A.crear_mundo(p.DIRECT)
    seguir = Seguir(radio=0.35, alfa=0.06)

    def componer():
        x, y, _ = A.leer_estado(e)["pos"]
        objetivo = seguir([x, y, 0.85])
        vista, proy = matrices(objetivo, 3.6, 50, -10)
        return foto(vista, proy, (0.6, 0.5, 1.0))

    g = Grabadora(CARPETA_ATLAS / "video" / nombre_mp4, componer)
    g.rotulo("titulo", titulo)
    original = A.paso

    # Todo lo que simula el modulo pasa por paso() (tambien poner_de_pie y
    # reiniciar_todo): se reemplaza por una version que ademas graba.
    def paso(est):
        original(est)
        g.tick(A.PASO_FISICA)
        if g.cuadros % 3 == 0:
            s = A.leer_estado(est)
            marcha = est.marcha or "quieto"
            texto = (f"ASISTENTE {'ON' if est.asistente else 'OFF'}   |   "
                     f"{'CAIDO' if s['caido'] else 'de pie'}   |   marcha: {marcha}")
            rojo = s["caido"] or not est.asistente
            g.rotulo("estado", texto, "0xff6060" if rojo else "0x60ff60")
    A.paso = paso

    def tecla(t, segundos, texto=None, sostener=0.2):
        """Linea TECLA:t cada 50 ms durante `sostener` s, despues TECLA:-."""
        if texto is not None:
            g.rotulo("tecla", texto)
        for k in range(round(segundos / INTERVALO_TECLA)):
            A.simular(e, INTERVALO_TECLA, t if k * INTERVALO_TECLA < sostener - 1e-9 else "-")

    return A, e, g, tecla


def video_atlas_con():
    A, e, g, tecla = preparar_atlas("atlas-con-asistente.mp4",
                                    "Punto c - Atlas CON asistente de equilibrio. Teclas del ESP32 simuladas")
    tecla("-", 1.5, "Atlas de pie, asistente ON")
    tecla("8", 5.0, "TECLA 8 (sostenida) : caminar adelante", sostener=5.0)
    tecla("-", 1.0, "Suelta la tecla: frena")
    tecla("4", 4.0, "TECLA 4 (sostenida) : girar a la izquierda", sostener=4.0)
    tecla("-", 1.0, "Suelta la tecla: frena")
    tecla("C", 3.5, "TECLA C : saludar")
    tecla("D", 3.0, "TECLA D : agacharse")
    tecla("#", 3.0, "TECLA # : brazos arriba")
    tecla("5", 2.5, "TECLA 5 : pose de pie")
    g.cerrar()
    print(f"  final: {A.leer_estado(e)}")
    p.disconnect()


def video_atlas_sin():
    A, e, g, tecla = preparar_atlas("atlas-sin-asistente.mp4",
                                    "Punto c - Atlas SIN asistente: misma fisica, sin arnes virtual")
    tecla("-", 1.0, "Atlas de pie, asistente ON")
    tecla("A", 1.5, "TECLA A : asistente OFF")
    # Medido (2026-10-02): sin asistente, caminar derecho aguanta unos 3-4 s
    # (a los ~4,7 s sostenidos se va de lado). La caida al girar es caotica
    # (depende de en que punto del paso se suelta la tecla): con esta
    # secuencia exacta (3 s caminando, 1 s quieto) se cae a los ~2,6 s de girar.
    tecla("8", 3.0, "TECLA 8 (sostenida) : caminar derecho - aguanta", sostener=3.0)
    tecla("-", 1.0, "Suelta la tecla: frena, sigue de pie")
    g.rotulo("tecla", "TECLA 4 (sostenida) : girar en el lugar - se cae")
    limite = 0.0
    while not A.leer_estado(e)["caido"] and limite < 12.0:
        tecla("4", INTERVALO_TECLA, sostener=1.0)
        limite += INTERVALO_TECLA
    if A.leer_estado(e)["caido"]:
        print(f"  se cayo a los {limite:.2f} s de girar")
    else:
        print(f"  AVISO: no se cayo en {limite:.0f} s de girar (cambio la fisica del modulo?)")
    tecla("4", 0.6, sostener=0.6)
    tecla("-", 3.0, "En el piso: sin asistente no se levanta solo")
    tecla("B", 0.2, "TECLA B : ponerlo de pie (grua)")
    tecla("-", 2.5, "De pie otra vez (asistente sigue OFF)")
    g.cerrar()
    print(f"  final: {A.leer_estado(e)}")
    p.disconnect()


# ======================================================================
VIDEOS = {
    "drones": (video_drones, CARPETA_DRONES / "video" / "drones-mision.mp4"),
    "baxter": (video_baxter, CARPETA_BAXTER / "video" / "baxter-demo.mp4"),
    "atlas-con": (video_atlas_con, CARPETA_ATLAS / "video" / "atlas-con-asistente.mp4"),
    "atlas-sin": (video_atlas_sin, CARPETA_ATLAS / "video" / "atlas-sin-asistente.mp4"),
}

if __name__ == "__main__":
    pedidos = [a for a in sys.argv[1:] if a in VIDEOS]
    if len(sys.argv) > 1 and not pedidos:
        sys.exit(f"Uso: grabar_videos.py [{' | '.join(VIDEOS)}]")
    if len(pedidos) == 1 and "--hijo" in sys.argv:
        print(f"Grabando {pedidos[0]}...", flush=True)
        VIDEOS[pedidos[0]][0]()
        sys.exit(0)
    # Proceso principal: un Python nuevo por video (una conexion de PyBullet por proceso).
    for nombre in pedidos or list(VIDEOS):
        subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), nombre, "--hijo"], check=True)
    print("\nResumen:")
    for nombre in pedidos or list(VIDEOS):
        mp4 = VIDEOS[nombre][1]
        for archivo in (mp4, mp4.with_suffix(".gif")):
            if archivo.exists():
                print(f"  {archivo.relative_to(TALLER)}  {archivo.stat().st_size / 1e6:6.2f} MB  "
                      f"{duracion(archivo):5.1f} s")
