"""Lo comun a todas las escenas en ventana: modo (ventana o sin ventana),
ritmo de tiempo real, teclado, camara, rotulos y grabacion de video.

Por que existe una "Vista" aparte de la simulacion: la simulacion (planta,
escena, carro) NO sabe que alguien la esta mirando. Lo unico que se le pide
es un gancho que se llama despues de cada paso de fisica (`_paso_fisica` en
`EscenaEstacion`, `al_paso_control` en `SimCarro`); desde ahi la Vista:

- duerme lo justo para que 1 s simulado dure 1 s de reloj (en la ventana);
- lee el teclado (espacio pausa, r reinicia, q sale);
- si esta grabando, cada 1/fps s simulados toma una foto con
  `p.getCameraImage` (render por software, ER_TINY_RENDERER: funciona sin
  ventana ni tarjeta de video) y la escribe en el video.

Limitacion conocida de PyBullet (regla de PyBullet de la carpeta Micros,
`.claude/rules/pybullet.md`): los textos
y lineas de depuracion (`addUserDebugText/Line`) se ven en la ventana pero NO
salen en `getCameraImage`. Por eso en los videos el rotulo (estacion, causa,
destino) se dibuja encima de cada fotograma, con el mismo contenido que los
textos de la ventana. Se dibuja con PIL (`ImageDraw`) y una fuente TTF de
Windows, no con `cv2.putText`: las fuentes de cv2 (Hershey) solo traen ASCII y
"decision" salia sin tilde (o "??" si se le dejaba la tilde).
"""

from __future__ import annotations

import argparse
import glob
import math
import os
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

from functools import lru_cache

import numpy as np
import pybullet as p

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_VIDEOS = RAIZ / "docs" / "videos"
PASO_FISICA = 1 / 240

# Teclas (codigos que devuelve p.getKeyboardEvents).
TECLA_ESPACIO = 32
TECLA_ESC = 27
# Renglones de la banda de texto de cada cuadro del video (titulo incluido).
RENGLONES_VIDEO = 8
# Letra de los videos (en pixeles del video de 800 de ancho). El GIF del README
# se reduce a 640 px (x0,8): 19 px quedan en ~15 px, que se leen sin zoom en
# GitHub (con la letra de 11 px de antes, reducida a 480 px, casi no se leia).
LETRA_TITULO = 21
LETRA_RENGLON = 19
ALTO_RENGLON = 25
# Fuentes TTF (tienen tildes y enie). Segoe UI viene con Windows; si no esta
# (otro sistema), se prueba DejaVu y al final la fuente por defecto de PIL.
FUENTES = {False: (r"C:\Windows\Fonts\segoeui.ttf", "DejaVuSans.ttf"),
           True: (r"C:\Windows\Fonts\seguisb.ttf", r"C:\Windows\Fonts\segoeuib.ttf", "DejaVuSans-Bold.ttf")}


class Reiniciar(Exception):
    """El usuario pidio reiniciar la escena (tecla r)."""


class Terminar(Exception):
    """Salir: tecla q/Esc, ventana cerrada o se cumplio `--segundos`."""


def sin_acentos(texto: str) -> str:
    """Los textos de depuracion de la ventana de PyBullet (addUserDebugText)
    solo dibujan ASCII: una "o" con tilde saldria como un simbolo raro. Los
    videos SI llevan tildes (se escriben con PIL, ver `escribir`)."""
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto)) if not unicodedata.combining(c))


@lru_cache(maxsize=None)
def fuente(tam: int, negrita: bool = False):
    """Fuente TTF de `tam` pixeles (se carga una vez por tamano: abrir el
    archivo en cada cuadro seria lento)."""
    from PIL import ImageFont

    for ruta in FUENTES[negrita]:
        try:
            return ImageFont.truetype(ruta, tam)
        except OSError:
            continue
    return ImageFont.load_default(size=tam)


def medir(texto: str, tam: int, negrita: bool = False) -> tuple[int, int]:
    """Ancho y alto (px) que ocupa `texto` con esa letra."""
    x0, y0, x1, y1 = fuente(tam, negrita).getbbox(str(texto))
    return x1 - x0, y1 - y0


def escribir(img: np.ndarray, textos) -> np.ndarray:
    """Escribe varios textos sobre una imagen BGR (la de cv2) con PIL, que si
    dibuja tildes y letra suavizada. `textos`: lista de
    (texto, (x, y) de la esquina de arriba a la izquierda, color BGR, tam, negrita)
    o, con `fondo` como sexto elemento, un recuadro de ese color BGR detras
    (para que se lea sobre el piso claro de PyBullet). Se convierte UNA vez por
    cuadro (BGR -> RGB -> BGR), no una vez por texto."""
    from PIL import Image, ImageDraw

    if not textos:
        return img
    lienzo = Image.fromarray(np.ascontiguousarray(img[:, :, ::-1]))
    dibujo = ImageDraw.Draw(lienzo)
    for t in textos:
        texto, (x, y), color, tam, negrita = t[:5]
        letra = fuente(tam, negrita)
        if len(t) > 5 and t[5] is not None:
            # getbbox mide desde el origen del texto: el recuadro se ajusta a
            # la tinta de verdad, con 4 px de margen.
            x0, y0, x1, y1 = dibujo.textbbox((x, y), str(texto), font=letra)
            b, g, r = t[5]
            dibujo.rectangle((x0 - 4, y0 - 3, x1 + 4, y1 + 4), fill=(r, g, b))
        b, g, r = color
        dibujo.text((x, y), str(texto), font=letra, fill=(r, g, b))
    return np.ascontiguousarray(np.asarray(lienzo)[:, :, ::-1])


class Camara:
    """Encuadre de una escena: el mismo para la ventana (resetDebugVisualizer
    Camera) y para las fotos del video (computeViewMatrixFromYawPitchRoll usa
    la misma convencion de yaw/pitch)."""

    def __init__(self, objetivo, distancia: float, yaw: float, pitch: float, fov: float = 50.0):
        self.objetivo = list(objetivo)
        self.distancia = distancia
        self.yaw = yaw
        self.pitch = pitch
        self.fov = fov

    def aplicar_ventana(self, cliente: int) -> None:
        p.resetDebugVisualizerCamera(self.distancia, self.yaw, self.pitch, self.objetivo, physicsClientId=cliente)

    def _matrices(self, ancho: int, alto: int):
        vista = p.computeViewMatrixFromYawPitchRoll(self.objetivo, self.distancia, self.yaw, self.pitch, 0, 2)
        proy = p.computeProjectionMatrixFOV(self.fov, ancho / alto, 0.01, 30.0)
        return vista, proy

    def proyectar(self, punto, ancho: int, alto: int) -> tuple[int, int] | None:
        """Pixel (u, v) donde cae un punto 3D en la foto de esta camara. Sirve
        para escribir en el video, al lado de cada pieza, lo que se decidio
        de ella (los textos de depuracion no salen en getCameraImage). Las
        matrices de PyBullet vienen por columnas: reshape + transpuesta."""
        vista, proy = self._matrices(ancho, alto)
        m = np.array(proy).reshape(4, 4).T @ np.array(vista).reshape(4, 4).T
        c = m @ np.array([*punto, 1.0])
        if c[3] <= 0:
            return None                      # detras de la camara
        x, y = c[0] / c[3], c[1] / c[3]
        return int((x + 1) / 2 * ancho), int((1 - y) / 2 * alto)

    def foto(self, cliente: int, ancho: int, alto: int) -> np.ndarray:
        vista, proy = self._matrices(ancho, alto)
        _, _, rgb, _, _ = p.getCameraImage(ancho, alto, vista, proy, renderer=p.ER_TINY_RENDERER,
                                           shadow=1, lightDirection=[0.5, -0.8, 1.6],
                                           physicsClientId=cliente)
        img = np.reshape(np.asarray(rgb, dtype=np.uint8), (alto, ancho, 4))[:, :, :3]
        return np.ascontiguousarray(img[:, :, ::-1])   # RGB -> BGR (lo que espera cv2)


def buscar_ffmpeg() -> str | None:
    """ffmpeg (instalado con winget): primero el PATH, despues la carpeta de
    winget del usuario (la consola de Python no siempre hereda el PATH nuevo)."""
    ruta = shutil.which("ffmpeg")
    if ruta:
        return ruta
    base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    candidatos = glob.glob(os.path.join(base, "Gyan.FFmpeg*", "*", "bin", "ffmpeg.exe"))
    return candidatos[0] if candidatos else None


class Vista:
    """Ventana o sin ventana, ritmo, teclado, rotulos y grabacion.

    `grabar`: ruta del .mp4 a escribir (solo sin ventana).
    `acelerar`: cuantos segundos simulados dura cada segundo de video (1 = tiempo real).
    `segundos`: corta la escena tras N segundos simulados (verificar sin ventana).
    """

    def __init__(self, nombre: str, *, ventana: bool, segundos: float | None = None,
                 velocidad: float = 1.0, grabar: Path | None = None, fps: int = 10,
                 acelerar: float = 1.0, tam: tuple[int, int] = (800, 450)):
        self.nombre = nombre
        self.ventana = ventana
        self.modo = p.GUI if ventana else p.DIRECT
        self.segundos = segundos
        self.velocidad = max(0.05, velocidad)
        self.grabar = Path(grabar) if grabar else None
        self.fps = fps
        self.acelerar = acelerar
        self.ancho, self.alto = tam
        self.t = 0.0                    # segundos simulados desde que empezo la escena
        self.cliente: int | None = None  # el cliente con ventana (o el principal sin ventana)
        self.camara: Camara | None = None
        self.titulo = ""
        self.textos: list[tuple[str, tuple[int, int, int]]] = []   # renglones del rotulo (video)
        self.componer = None            # funcion -> imagen BGR del cuadro (la pone la escena)
        self.al_paso = None             # funcion opcional de la escena, tras cada paso (p. ej. otra ventana)
        self.teclas_extra: dict = {}    # tecla -> funcion (p. ej. "c": seguir o no al carro)
        self._rotulos: dict[str, tuple[int, str]] = {}
        self._t0_reloj = time.perf_counter()
        self._pasos = 0
        self._proximo_cuadro = 0.0
        self._escritor = None
        self._ruta_cruda: Path | None = None
        self.cuadros = 0
        self.pausado = False
        self.mensaje_fin = ""

    # ------------------------------------------------------------------
    # conexion
    # ------------------------------------------------------------------

    def preparar(self, cliente: int, camara: Camara) -> None:
        """Se llama con el cliente ya conectado (y la escena cargada)."""
        self.cliente = cliente
        self.camara = camara
        if self.ventana:
            # Sin el panel lateral de PyBullet (sliders que aqui no se usan) y
            # con sombras: se entiende mejor la altura de cada cosa.
            p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=cliente)
            p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1, physicsClientId=cliente)
            camara.aplicar_ventana(cliente)
        self._t0_reloj = time.perf_counter()

    def rotulo(self, clave: str, texto: str, posicion, color=(1, 1, 1), tam: float = 1.1,
               pegado_a: int | None = None) -> None:
        """Texto de depuracion en la ventana (se reemplaza en su lugar, sin
        parpadear). Sin ventana no hace nada: ahi el rotulo va en `textos`."""
        if not self.ventana or self.cliente is None:
            return
        texto = sin_acentos(texto)
        anterior = self._rotulos.get(clave)
        if anterior is not None and anterior[1] == texto:
            return
        kw = {"replaceItemUniqueId": anterior[0]} if anterior is not None else {}
        if pegado_a is not None:
            # El texto viaja con el cuerpo (posicion relativa a el).
            kw["parentObjectUniqueId"] = pegado_a
        uid = p.addUserDebugText(texto, list(posicion), textColorRGB=list(color), textSize=tam,
                                 physicsClientId=self.cliente, **kw)
        self._rotulos[clave] = (uid, texto)

    # ------------------------------------------------------------------
    # el gancho de cada paso
    # ------------------------------------------------------------------

    def avanzar(self, dt: float = PASO_FISICA) -> None:
        """Lo llama la simulacion despues de cada paso (de fisica o de control)."""
        self.t += dt
        self._pasos += 1
        if self.segundos is not None and self.t >= self.segundos:
            raise Terminar
        if self.al_paso is not None:
            self.al_paso()
        if self.ventana and self._pasos % 8 == 0:
            self.teclado()
            self._ritmo()
        if self.grabar is not None and self.t + 1e-9 >= self._proximo_cuadro:
            self.cuadro()
            self._proximo_cuadro += self.acelerar / self.fps

    def _ritmo(self) -> None:
        """Duerme lo que haga falta para que el tiempo simulado vaya al paso
        del reloj (dividido por `velocidad`)."""
        adelanto = self.t / self.velocidad - (time.perf_counter() - self._t0_reloj)
        if adelanto > 0.002:
            time.sleep(min(adelanto, 0.25))
        elif adelanto < -0.5:
            # La simulacion se atraso (un tick pesado): no se intenta
            # "recuperar" corriendo a toda velocidad, se sigue desde aqui.
            self._t0_reloj = time.perf_counter() - self.t / self.velocidad

    def teclado(self) -> None:
        try:
            eventos = p.getKeyboardEvents(physicsClientId=self.cliente)
        except p.error as e:            # se cerro la ventana
            raise Terminar from e
        if not p.isConnected(self.cliente):
            raise Terminar
        for tecla, estado in eventos.items():
            if not estado & p.KEY_WAS_TRIGGERED:
                continue
            if tecla in (ord("q"), TECLA_ESC):
                raise Terminar
            if tecla == ord("r"):
                raise Reiniciar
            if tecla == TECLA_ESPACIO:
                self._pausa()
            elif tecla in self.teclas_extra:
                self.teclas_extra[tecla]()

    def _pausa(self) -> None:
        """Congela la simulacion (la camara de la ventana se sigue moviendo)."""
        self.pausado = True
        self.rotulo("_pausa", "PAUSA (espacio sigue)", self.camara.objetivo if self.camara else [0, 0, 0],
                    color=(1, 0.3, 0.3), tam=1.6)
        inicio = time.perf_counter()
        try:
            while True:
                time.sleep(0.03)
                try:
                    eventos = p.getKeyboardEvents(physicsClientId=self.cliente)
                except p.error as e:
                    raise Terminar from e
                if not p.isConnected(self.cliente):
                    raise Terminar
                for tecla, estado in eventos.items():
                    if not estado & p.KEY_WAS_TRIGGERED:
                        continue
                    if tecla in (ord("q"), TECLA_ESC):
                        raise Terminar
                    if tecla == ord("r"):
                        raise Reiniciar
                    if tecla == TECLA_ESPACIO:
                        return
        finally:
            self.pausado = False
            self.rotulo("_pausa", " ", [0, 0, 0])
            # El tiempo en pausa no cuenta para el ritmo.
            self._t0_reloj += time.perf_counter() - inicio

    # ------------------------------------------------------------------
    # video
    # ------------------------------------------------------------------

    def cuadro(self) -> None:
        """Un fotograma: la imagen de la escena + el rotulo encima."""
        if self.componer is None:
            return
        img = self.componer()
        if img is None:
            return
        img = self._rotular(img)
        if self._escritor is None:
            import cv2

            self.grabar.parent.mkdir(parents=True, exist_ok=True)
            # cv2 escribe MPEG-4 parte 2 (mp4v), que GitHub y los navegadores
            # no reproducen: se escribe crudo y al final ffmpeg lo pasa a H.264.
            self._ruta_cruda = self.grabar.with_name(self.grabar.stem + "_crudo.mp4")
            alto, ancho = img.shape[:2]
            self._escritor = cv2.VideoWriter(str(self._ruta_cruda), cv2.VideoWriter_fourcc(*"mp4v"),
                                             self.fps, (ancho, alto))
        self._escritor.write(img)
        self.cuadros += 1

    def _rotular(self, img: np.ndarray) -> np.ndarray:
        """Banda de texto ENCIMA de la imagen (no sobre ella: no tapa nada de
        la escena), de alto fijo para que todos los cuadros midan lo mismo."""
        renglones = [(self.titulo, (255, 255, 255))] + list(self.textos)
        renglones = [(t, c) for t, c in renglones if t][:RENGLONES_VIDEO]
        ancho = img.shape[1]
        k = ancho / 800                                     # la letra escala con el ancho del video
        alto_renglon = int(ALTO_RENGLON * k)
        alto_banda = int(10 * k) + alto_renglon * RENGLONES_VIDEO
        alto_banda += (alto_banda + img.shape[0]) % 2        # H.264 (yuv420p) pide alto par
        banda = np.full((alto_banda, ancho, 3), (24, 22, 20), np.uint8)
        textos = []
        for i, (texto, color) in enumerate(renglones):
            tam = int((LETRA_TITULO if i == 0 else LETRA_RENGLON) * k)
            textos.append((self._recortar(texto, tam, ancho - int(20 * k)), (int(10 * k), int(6 * k) + alto_renglon * i),
                           color, tam, i == 0))
        banda = escribir(banda, textos)
        # Reloj simulado abajo a la derecha: se ve cuanto dura de verdad cada cosa.
        reloj = f"t = {self.t:6.1f} s simulados" + (f"  (video ×{self.acelerar:g})" if self.acelerar != 1 else "")
        tam = int(LETRA_RENGLON * k)
        w, h = medir(reloj, tam)
        img = escribir(img.copy(), [(reloj, (ancho - w - int(12 * k), img.shape[0] - h - int(14 * k)), (235, 235, 235),
                                     tam, False, (24, 22, 20))])
        return np.vstack([banda, img])

    @staticmethod
    def _recortar(texto: str, tam: int, maximo: int) -> str:
        """Si un renglon no cabe en el ancho del video, se corta con "…" (con
        la letra mas grande, algunos renglones largos se salian del cuadro)."""
        negrita = False
        if medir(texto, tam, negrita)[0] <= maximo:
            return texto
        while texto and medir(texto + "…", tam, negrita)[0] > maximo:
            texto = texto[:-1]
        return texto.rstrip() + "…"

    def sostener(self, segundos: float) -> None:
        """Al final del video: repite el ultimo cuadro un rato (se alcanza a leer)."""
        if self.grabar is None:
            return
        for _ in range(int(segundos * self.fps)):
            self.cuadro()

    def cerrar_video(self) -> dict | None:
        """Pasa el video crudo a H.264 (mp4 que se ve en GitHub) y devuelve su info."""
        if self._escritor is None:
            return None
        self._escritor.release()
        self._escritor = None
        ffmpeg = buscar_ffmpeg()
        if ffmpeg is None:
            shutil.move(self._ruta_cruda, self.grabar)
        else:
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(self._ruta_cruda), "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-crf", "26", "-preset", "medium", "-movflags", "+faststart",
                            str(self.grabar)], check=True)
            self._ruta_cruda.unlink(missing_ok=True)
        return {"mp4": self.grabar, "cuadros": self.cuadros, "segundos_video": self.cuadros / self.fps}

    # ------------------------------------------------------------------

    def fin(self, mensaje: str = "FIN") -> None:
        """La escena termino. En la ventana se queda quieta mostrando el
        resultado hasta que el usuario reinicie (r) o salga (q / cerrar)."""
        self.mensaje_fin = mensaje
        if not self.ventana:
            self.sostener(2.5)
            return
        self.rotulo("_fin", f"{mensaje}   (r: reiniciar, q: salir)",
                    self.camara.objetivo if self.camara else [0, 0, 0], color=(1, 0.85, 0.2), tam=1.5)
        while True:
            time.sleep(0.05)
            self.teclado()


# ----------------------------------------------------------------------
# piezas solo visuales (sin colision: no las ve ningun rayTest de sensor)
# ----------------------------------------------------------------------

def caja_visual(cliente: int, centro, medio, color, rumbo: float = 0.0, cabeceo: float = 0.0) -> int:
    vis = p.createVisualShape(p.GEOM_BOX, halfExtents=list(medio), rgbaColor=list(color), physicsClientId=cliente)
    return p.createMultiBody(0, -1, vis, list(centro), p.getQuaternionFromEuler([0, cabeceo, rumbo]),
                             physicsClientId=cliente)


def barra_visual(cliente: int, a, b, radio: float, color) -> int:
    """Cilindro visual de `a` a `b` (rieles de la canaleta)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = b - a
    largo = float(np.linalg.norm(d))
    # El cilindro de PyBullet apunta en z: se inclina (pitch) y se gira (yaw).
    yaw = math.atan2(d[1], d[0])
    pitch = math.atan2(math.hypot(d[0], d[1]), d[2])
    vis = p.createVisualShape(p.GEOM_CYLINDER, radius=radio, length=largo, rgbaColor=list(color),
                              physicsClientId=cliente)
    return p.createMultiBody(0, -1, vis, list((a + b) / 2), p.getQuaternionFromEuler([0, pitch, yaw]),
                             physicsClientId=cliente)


# ----------------------------------------------------------------------
# linea de comandos comun
# ----------------------------------------------------------------------

def argumentos(descripcion: str, argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=descripcion)
    ap.add_argument("--sin-ventana", action="store_true",
                    help="corre la MISMA escena en p.DIRECT (sin abrir nada), para verificarla")
    ap.add_argument("--segundos", type=float, default=None, help="corta tras N segundos simulados")
    ap.add_argument("--velocidad", type=float, default=1.0, help="1 = tiempo real, 2 = el doble de rapido")
    return ap.parse_args(argv)


def ejecutar(nombre: str, titulo: str, correr, argv=None) -> None:
    """Bucle de una escena: la corre, y con r la vuelve a armar desde cero."""
    args = argumentos(titulo, argv)
    ventana = not args.sin_ventana
    if ventana:
        print(f"{titulo}\n  espacio: pausa   r: reinicia   q (o cerrar la ventana): sale\n"
              f"  El mouse mueve la camara (rueda: zoom; ctrl + arrastrar: girar).")
    while True:
        vista = Vista(nombre, ventana=ventana, segundos=args.segundos, velocidad=args.velocidad)
        vista.titulo = titulo
        t0 = time.perf_counter()
        try:
            correr(vista)
            if not ventana:
                print(f"{nombre}: termino sola en {vista.t:.1f} s simulados ({time.perf_counter() - t0:.1f} s de reloj)"
                      f" -> {sin_acentos(vista.mensaje_fin)}")
            return
        except Reiniciar:
            print("reiniciando la escena...")
            continue
        except Terminar:
            if not ventana:
                print(f"{nombre}: {vista.t:.1f} s simulados sin errores ({time.perf_counter() - t0:.1f} s de reloj)")
            return
        except p.error:
            # La ventana se cerro con la X a mitad de un paso de fisica.
            if ventana:
                return
            raise


def salir_limpio(*clientes: int) -> None:
    for c in clientes:
        try:
            if c is not None and p.isConnected(c):
                p.disconnect(c)
        except p.error:
            pass
    sys.stdout.flush()
