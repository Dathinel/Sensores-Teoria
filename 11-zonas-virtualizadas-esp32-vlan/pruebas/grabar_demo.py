"""Graba el video de la práctica funcionando con el stack real (docker compose --profile emulado up -d).

No graba la pantalla: arma cada cuadro con lo que los propios contenedores publican.
  - Arriba, la pista (visor HTTP del track-server, puerto 8010) y abajo los tres robots (8011-8013):
    es el `/cuadro.jpg` que cada simulación renderiza dentro de su contenedor.
  - Una barra inferior con los 6 "LEDs" de la ESP32 esclava y la latencia de cada servicio, leídos
    por MQTT del broker del admin (lab/estado/+ y lab/admin/resumen): es lo mismo que ve la esclava.
  - A mitad del video detiene sim-pepper (docker stop) y lo vuelve a arrancar, para que se vea cómo el
    admin lo marca CAIDO, su LED se apaga, las otras zonas siguen, y cómo vuelve a OK.

Uso (desde la carpeta del tema, con el stack arriba):
    entorno\\Scripts\\python pruebas\\grabar_demo.py --segundos 60 --salida video\\demo-stack.mp4
Necesita: pillow, imageio, imageio-ffmpeg y paho-mqtt (están en el entorno del tema).
"""

import argparse
import io
import json
import subprocess
import threading
import time
import urllib.request

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

LEDS = ["player-1", "player-2", "player-3", "sim-spot", "sim-pepper", "sim-nao"]
VISORES = {"pista": 8010, "sim-spot": 8011, "sim-pepper": 8012, "sim-nao": 8013}
COLOR = {"OK": (60, 200, 110), "LENTO": (240, 190, 40), "CAIDO": (70, 70, 78), "?": (120, 120, 130)}
ANCHO = 1344          # el ancho del cuadro de la pista: así no se reescala
FPS = 10


def fuente(tam):
    for nombre in ("consola.ttf", "DejaVuSansMono.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(nombre, tam)
        except OSError:
            pass
    return ImageFont.load_default()


class Visor:
    """Baja el último cuadro de un visor HTTP en un hilo; si el contenedor está caído, se queda con
    el último que tuvo y lo marca como congelado (así se ve en el video que esa zona se detuvo)."""

    def __init__(self, puerto):
        self.url = f"http://localhost:{puerto}/cuadro.jpg"
        self.img = None
        self.t_ok = 0.0
        threading.Thread(target=self._bucle, daemon=True).start()

    def _bucle(self):
        while True:
            try:
                with urllib.request.urlopen(self.url, timeout=1) as r:
                    self.img = Image.open(io.BytesIO(r.read())).convert("RGB")
                    self.t_ok = time.monotonic()
            except OSError:
                pass
            time.sleep(1.0 / FPS)

    def congelado(self):
        return time.monotonic() - self.t_ok > 1.5


def mqtt_estados():
    """Estados y resumen del admin por MQTT (mismo broker que usa la esclava)."""
    import paho.mqtt.client as mqtt
    datos = {"estado": {}, "resumen": {}}

    def al_mensaje(c, u, m):
        if m.topic.startswith("lab/estado/"):
            datos["estado"][m.topic.split("/")[2]] = m.payload.decode()
        elif m.topic == "lab/admin/resumen":
            try:
                datos["resumen"] = json.loads(m.payload)
            except ValueError:
                pass

    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="grabar-demo")
    c.on_message = al_mensaje
    c.on_connect = lambda c, u, f, rc, p=None: c.subscribe([("lab/estado/+", 1), ("lab/admin/resumen", 0)])
    c.connect("localhost", 1883, 10)
    c.loop_start()
    return datos


def pegar(lienzo, img, caja, congelado, f):
    x, y, w, h = caja
    if img is None:
        ImageDraw.Draw(lienzo).text((x + 10, y + 10), "sin imagen", font=f, fill=(200, 200, 200))
        return
    im = img.copy()
    im.thumbnail((w, h))
    if congelado:
        # Contenedor detenido: se oscurece la última imagen que llegó y se rotula.
        im = Image.blend(im, Image.new("RGB", im.size, (0, 0, 0)), 0.6)
        ImageDraw.Draw(im).text((12, 12), "CONTENEDOR DETENIDO", font=fuente(28), fill=(255, 90, 90))
    lienzo.paste(im, (x, y))


def barra(lienzo, y, datos, t, evento, f, fg):
    d = ImageDraw.Draw(lienzo)
    d.rectangle([0, y, ANCHO, lienzo.size[1]], fill=(18, 19, 24))
    d.text((14, y + 8), "ESP32 esclava (lab/estado/<servicio>)  ·  admin 192.168.30.10, ping ICMP a través del router",
           font=f, fill=(170, 170, 180))
    serv = datos["resumen"].get("servicios", {}) if isinstance(datos["resumen"], dict) else {}
    paso = ANCHO // len(LEDS)
    for i, n in enumerate(LEDS):
        e = datos["estado"].get(n, "?")
        c = COLOR.get(e, COLOR["?"])
        if e == "LENTO" and int(t * 4) % 2:      # parpadeo a 2 Hz, como el LED físico
            c = (60, 50, 20)
        cx = i * paso + 30
        d.ellipse([cx, y + 38, cx + 34, y + 72], fill=c, outline=(90, 90, 100), width=2)
        d.text((cx + 46, y + 36), n, font=fg, fill=(235, 235, 240))
        rtt = serv.get(n, {}).get("ping", {}).get("rtt_prom_ms")
        # Caído: no se muestra el RTT (sería el último que se midió antes de la caída, no uno actual).
        txt = f"{e}" + (f"  {rtt:.2f} ms" if isinstance(rtt, (int, float)) and e != "CAIDO" else "")
        d.text((cx + 46, y + 60), txt, font=f, fill=c if e != "CAIDO" else (220, 90, 90))
    d.text((14, y + 92), f"t = {t:5.1f} s   {evento}", font=fg, fill=(250, 210, 120))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segundos", type=float, default=60)
    ap.add_argument("--salida", default="video/demo-stack.mp4")
    ap.add_argument("--caer", default="sim-pepper", help="servicio a detener a mitad ('' = ninguno)")
    ap.add_argument("--caer-en", type=float, default=20)
    ap.add_argument("--volver-en", type=float, default=38)
    a = ap.parse_args()

    visores = {k: Visor(p) for k, p in VISORES.items()}
    datos = mqtt_estados()
    f, fg = fuente(15), fuente(19)
    alto_pista = 576
    alto_robot = int((ANCHO // 3) * 480 / 960)
    alto = alto_pista + alto_robot + 124
    alto += alto % 2                           # H.264 pide ancho y alto pares
    escritor = imageio.get_writer(a.salida, fps=FPS, codec="libx264", quality=7,
                                  macro_block_size=1, pixelformat="yuv420p")
    time.sleep(2)                              # primeros cuadros y estados retenidos
    t0 = time.monotonic()
    evento, hecho = "stack completo funcionando: 16 contenedores, 7 ESP32 emulados", set()

    def docker(*args):
        subprocess.Popen(["docker", "compose", *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    n = 0
    while True:
        t = time.monotonic() - t0
        if t >= a.segundos:
            break
        if a.caer and t >= a.caer_en and "caer" not in hecho:
            docker("stop", a.caer); hecho.add("caer")
            evento = f"docker stop {a.caer}: el admin lo marca CAIDO y su LED se apaga; las demás zonas siguen"
        if a.caer and t >= a.volver_en and "volver" not in hecho:
            docker("start", a.caer); hecho.add("volver")
            evento = f"docker start {a.caer}: vuelve a latir y el admin lo pasa a OK"
        lienzo = Image.new("RGB", (ANCHO, alto), (10, 10, 14))
        pegar(lienzo, visores["pista"].img, (0, 0, ANCHO, alto_pista), visores["pista"].congelado(), f)
        for i, k in enumerate(("sim-spot", "sim-pepper", "sim-nao")):
            pegar(lienzo, visores[k].img, (i * (ANCHO // 3), alto_pista, ANCHO // 3, alto_robot),
                  visores[k].congelado(), f)
        barra(lienzo, alto_pista + alto_robot, datos, t, evento, f, fg)
        escritor.append_data(np.asarray(lienzo))
        n += 1
        # Ritmo fijo de FPS contra el reloj (si un cuadro tarda, el siguiente no se atrasa más).
        time.sleep(max(0.0, t0 + n / FPS - time.monotonic()))
    escritor.close()
    print(f"{n} cuadros, {a.salida}")


if __name__ == "__main__":
    main()
