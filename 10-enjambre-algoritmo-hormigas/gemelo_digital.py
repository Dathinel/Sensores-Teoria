"""
gemelo_digital.py - Gemelo digital en PyBullet del enjambre de 3 carritos ESP32 que resuelven un
laberinto con ACO (optimizacion por colonia de hormigas).

Un "gemelo digital" es una copia virtual que se mueve igual que el sistema real porque se alimenta
de los mismos datos. Aqui los datos son la telemetria UDP que cada ESP32 manda al computador
(puerto 4211): los depositos de feromona (PHER), el cierre de cada iteracion (FIN), la mejor ruta
de cada nodo (PATH) y su estado (ESTADO: fase, celda donde va el carrito, nodos vivos...).

Con eso el gemelo:
  1. Reconstruye la feromona EXACTAMENTE como la calcula cada nodo: al cerrar la iteracion k evapora
     (tau <- (1 - rho) * tau) y suma, en orden de nodo, los depositos de los nodos cuyo FIN de esa
     iteracion llego completo. Usa la misma funcion de aco.py (NodoACO.aplicar_iteracion), asi que
     la suma se hace en el mismo orden y da el mismo double, bit a bit.
  2. Muestra en 3D el laberinto, la feromona de cada arista (una franja cuyo color cambia con tau),
     la mejor ruta de cada nodo y los 3 carritos moviendose por las celdas con los tiempos reales
     del firmware (T_CELDA_S por celda y T_GIRO90_S por cada giro de 90 grados).
  3. Graba un video (mp4), la imagen final, la telemetria cruda (jsonl) y un resumen (json).

PyBullet corre en modo DIRECT (sin ventana): las imagenes salen de getCameraImage con el
renderizador por software (ER_TINY_RENDERER), que funciona igual en Windows y dentro de Docker,
donde no hay pantalla ni tarjeta grafica. OJO: getCameraImage NO captura addUserDebugLine ni
addUserDebugText, por eso todo lo que se ve (feromona, rutas, marcas) es geometria real
(createVisualShape) y los textos se dibujan con Pillow encima de cada cuadro.

Modos:
  --modo hardware      (por defecto) escucha UDP 0.0.0.0:4211 en tiempo real. El PC debe estar
                       conectado al WiFi ENJAMBRE_ACO con la IP 192.168.4.100 (se la da el nodo 1
                       por DHCP; si no, se pone fija a mano).
  --modo sin-hardware  genera la telemetria con protocolo.flujo_simulado (la misma logica del
                       firmware) y la consume en tiempo virtual: no espera, solo renderiza cuadros
                       a fps fijos, asi que termina mas rapido que en tiempo real.

Ejemplos:
  entorno\\Scripts\\python gemelo_digital.py --modo sin-hardware
  entorno\\Scripts\\python gemelo_digital.py --modo sin-hardware --apagar-nodo 3 --en-iteracion 10
  entorno\\Scripts\\python gemelo_digital.py --modo hardware --timeout 300
"""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import socket
import sys
import time
from dataclasses import asdict

import numpy as np
import pybullet as p
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio

import aco
import protocolo

AQUI = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------------------------
# Constantes de la escena
# ---------------------------------------------------------------------------------------------
NODOS = (1, 2, 3)
COLOR_NODO = {1: (0.88, 0.16, 0.14), 2: (0.16, 0.38, 0.92), 3: (0.98, 0.82, 0.10)}
NOMBRE_COLOR = {1: "rojo", 2: "azul", 3: "amarillo"}
GRIS_APAGADO = (0.62, 0.62, 0.64)

ALTO_PARED = 0.08        # 8 cm: mas alto que el carrito, como las estanterias del enunciado
GROSOR_PARED = 0.015     # 1,5 cm
COLOR_PARED = (0.22, 0.24, 0.30, 1.0)
COLOR_BALDOSA = ((0.90, 0.87, 0.80), (0.84, 0.81, 0.74))  # dos tonos, para que se vea la grilla

# Capas en z (de abajo hacia arriba). Todo es casi plano porque la camara mira desde arriba: lo que
# importa es que cada capa quede ENCIMA de la anterior para que no "parpadee" (z-fighting).
Z_BALDOSA = 0.004        # cara superior de las baldosas
Z_MARCA = 0.006          # cara superior de la marca de inicio y de la bandera de meta
Z_FEROMONA = 0.008       # cara superior de la franja de feromona minima (sube hasta +4 mm)
Z_RUTA = 0.014           # cara superior de los marcadores de ruta

# Carrito: 10 cm de largo y unos 5,6 cm de ancho con las ruedas. Es angosto a proposito: asi los
# tres caben uno al lado del otro en la celda de inicio (20 cm) mientras esperan su turno.
LARGO_CARRO, ANCHO_CUERPO, ALTO_CUERPO = 0.10, 0.040, 0.024
RADIO_RUEDA, ANCHO_RUEDA = 0.017, 0.008
SEPARACION_ESTACIONADO = 0.06   # desplazamiento lateral de cada carrito cuando esta quieto

# Feromona: de lila palido (poca) a violeta intenso (mucha). Violeta porque no se confunde con
# los colores de los nodos (rojo, azul, amarillo) ni con el verde del inicio. Por debajo de
# FEROMONA_MINIMA la franja se esconde: asi no aparecen barras "fantasma" del color del piso.
FEROMONA_BAJA = np.array([0.88, 0.80, 0.95])
FEROMONA_MEDIO = np.array([0.72, 0.48, 0.90])
FEROMONA_ALTA = np.array([0.42, 0.04, 0.58])
FEROMONA_MINIMA = 0.04


def color_feromona(a: float) -> np.ndarray:
    """Color de una franja con feromona normalizada a en [0, 1] (dos tramos lineales)."""
    if a < 0.5:
        return FEROMONA_BAJA + (FEROMONA_MEDIO - FEROMONA_BAJA) * (a / 0.5)
    return FEROMONA_MEDIO + (FEROMONA_ALTA - FEROMONA_MEDIO) * ((a - 0.5) / 0.5)

# Imagen
LADO_3D = 720            # la vista 3D es cuadrada (el laberinto tambien lo es)
ANCHO_PANEL = 400        # panel de texto a la derecha -> lienzo de 1120 x 720
ANCHO_LIENZO = LADO_3D + ANCHO_PANEL

FASES_TXT = {"ESPERA": "espera", "BUSQUEDA": "búsqueda", "RECORRIDO": "recorrido",
             "TERMINADO": "terminado"}


def suave(s: float) -> float:
    """Curva 'smoothstep': va de 0 a 1 arrancando y frenando despacio (velocidad 0 en los dos
    extremos). Se usa para que el carrito acelere y frene en cada tramo en vez de saltar de
    velocidad, como lo hace un carrito real con sus motores."""
    s = min(1.0, max(0.0, s))
    return s * s * (3.0 - 2.0 * s)


def ajustar_angulo(a: float) -> float:
    """Lleva un angulo a (-pi, pi]."""
    while a <= -math.pi:
        a += 2 * math.pi
    while a > math.pi:
        a -= 2 * math.pi
    return a


# ---------------------------------------------------------------------------------------------
# Trayectoria de un carrito
# ---------------------------------------------------------------------------------------------
class Trayectoria:
    """Convierte una ruta de celdas en una animacion: una lista de tramos (t_ini, t_fin, pose_ini,
    pose_fin), cada uno o un giro en el sitio o un avance de una celda.

    Los instantes de llegada a cada celda son EXACTAMENTE los de protocolo.tiempo_recorrido (los
    mismos con que el firmware mueve los motores), asi el carrito virtual llega a cada celda al
    mismo tiempo que el real."""

    def __init__(self, lab: aco.Laberinto, camino: list):
        self.camino = list(camino)
        self.tiempos = protocolo.tiempo_recorrido(lab, self.camino)
        self.tramos = []
        rumbo = 0.0  # el firmware arranca mirando hacia +x (rumbo 0)
        for i, (a, b) in enumerate(zip(self.camino, self.camino[1:])):
            ax, ay = lab.celda(a)
            bx, by = lab.celda(b)
            pa, pb = centro_celda(ax, ay), centro_celda(bx, by)
            # Rumbo "continuo": se suma el giro (-90, +90 o 180 grados) al rumbo anterior en vez
            # de usar atan2 directo, para que la interpolacion no de una vuelta entera de mas.
            nuevo = rumbo + ajustar_angulo(math.atan2(by - ay, bx - ax) - rumbo)
            t_llega_a, t_llega_b = self.tiempos[i], self.tiempos[i + 1]
            t_arranca = t_llega_b - protocolo.T_CELDA_S
            if t_arranca > t_llega_a + 1e-9:
                # Hubo giro: el tiempo entre llegar a 'a' y arrancar hacia 'b' es el giro.
                self.tramos.append((t_llega_a, t_arranca, (pa[0], pa[1], rumbo), (pa[0], pa[1], nuevo)))
            self.tramos.append((t_arranca, t_llega_b, (pa[0], pa[1], nuevo), (pb[0], pb[1], nuevo)))
            rumbo = nuevo
        self.duracion = self.tiempos[-1]
        x0, y0 = lab.celda(self.camino[0])
        self.pose_inicial = (*centro_celda(x0, y0), 0.0)
        self.pose_final = self.tramos[-1][3] if self.tramos else self.pose_inicial

    def pose(self, s: float) -> tuple:
        """Pose (x, y, rumbo) a los s segundos de haber arrancado."""
        if s <= 0 or not self.tramos:
            return self.pose_inicial
        for t0, t1, a, b in self.tramos:
            if s <= t1:
                f = suave((s - t0) / (t1 - t0))
                return tuple(a[j] + (b[j] - a[j]) * f for j in range(3))
        return self.pose_final

    def indice_celda(self, s: float) -> int:
        """Indice (en el camino) de la ultima celda a la que ya llego a los s segundos."""
        i = 0
        for j, tj in enumerate(self.tiempos):
            if tj <= s + 1e-9:
                i = j
        return i


def centro_celda(x: int, y: int) -> tuple:
    """Celda (x, y) -> centro en metros. Celdas de 20 cm con la esquina del laberinto en (0, 0)."""
    return (x * 0.2 + 0.1, y * 0.2 + 0.1)


# ---------------------------------------------------------------------------------------------
# Estado del gemelo (lo alimentan los dos modos con los mismos mensajes)
# ---------------------------------------------------------------------------------------------
class EstadoGemelo:
    """Todo lo que el gemelo sabe del enjambre, armado SOLO con los mensajes recibidos.

    Los dos modos (hardware y sin-hardware) llaman a recibir(mensaje, t) con cada mensaje y a
    actualizar(t) una vez por vuelta del bucle; asi la logica es una sola y lo que se prueba sin
    hardware es lo mismo que corre con los ESP32."""

    def __init__(self, lab: aco.Laberinto, params: aco.Parametros, modo: str):
        self.lab = lab
        self.params = params
        self.modo = modo
        self.crc_esperado = lab.crc()
        # Copia de la feromona: un NodoACO "espectador" (nodo 0). Solo se usan su tau, su
        # aplicar_iteracion (la MISMA suma que hace cada ESP32) y su camino_codicioso.
        self.ref = aco.NodoACO(lab, params, 0)
        self.iter_aplicada = 0
        self.pher = {}          # (nodo, iter) -> {arista: (origen, destino, deposito)}
        self.fin = {}           # (nodo, iter) -> mensaje FIN
        self.t_primer_fin = {}  # iter -> instante del primer FIN recibido de esa iteracion
        self.nodos = {}         # nodo -> dict con lo ultimo que se sabe de el
        self.robots = {}        # nodo -> dict con su trayectoria y su arranque
        self.conteo = {}        # tipo de mensaje -> cuantos llegaron
        self.avisos = []        # textos que se muestran en el panel del video
        self.incompletas = []   # (iter, nodo) cuyo FIN llego pero faltaron PHER
        self.ultima_linea = ""
        self.t_ultimo_mensaje = None

    # ----------------------------------------------------------------- nodos
    def _nodo(self, n: int) -> dict:
        if n not in self.nodos:
            self.nodos[n] = {"visto": None, "fase": "ESPERA", "iter": 0, "mejor": None,
                             "celda": self.lab.inicio, "vivos_rep": None, "t_estado": None,
                             "crc": None, "crc_ok": None, "ruta": None, "longitud": None,
                             "t_recorrido": None, "rssi": None}
            self.robots[n] = {"tray": None, "t_inicio": None, "pose": None, "apagado": False}
        return self.nodos[n]

    def apagado(self, n: int, t: float) -> bool:
        """Un nodo se da por apagado si (a) no se oye nada de el hace mas de VIVO_S (4 s, igual
        que en el firmware), o (b) otro nodo vivo mando un ESTADO DESPUES del ultimo mensaje de
        este y en su lista de vivos ya no aparece. La regla (b) avisa antes que la (a): los
        propios ESP32 son los primeros en notar que un companero se callo."""
        d = self.nodos.get(n)
        if d is None or d["visto"] is None:
            return True
        if d.get("fase") == "TERMINADO":
            return False  # ya termino su trabajo: que se calle despues no es una caida
        if t - d["visto"] > protocolo.VIVO_S:
            return True
        for m, e in self.nodos.items():
            if m == n or e["vivos_rep"] is None or e["t_estado"] is None:
                continue
            if t - e["visto"] > protocolo.VIVO_S:
                continue  # la opinion de un nodo que tambien se callo no cuenta
            if e["t_estado"] >= d["visto"] and n not in e["vivos_rep"]:
                return True
        return False

    def vivos(self, t: float) -> list:
        return [n for n in sorted(self.nodos) if not self.apagado(n, t)]

    # ----------------------------------------------------------------- mensajes
    def recibir(self, m: dict, t: float, linea: str = "") -> None:
        tipo = m["tipo"]
        self.conteo[tipo] = self.conteo.get(tipo, 0) + 1
        self.ultima_linea = linea or self.ultima_linea
        self.t_ultimo_mensaje = t
        if "nodo" not in m or tipo == "CMD":
            return  # PING/PONG/CMD: no cambian el estado del gemelo
        n = m["nodo"]
        d = self._nodo(n)
        d["visto"] = t

        if tipo == "HELLO":
            d["crc"] = m["crc"]
            ok = m["crc"] == self.crc_esperado
            if d["crc_ok"] is not False and not ok:
                aviso = (f"CRC del nodo {n} = {m['crc']:08X} distinto del de maze.json "
                         f"({self.crc_esperado:08X}): ese ESP32 tiene otro laberinto")
                print("AVISO:", aviso)
                self.avisos.append(aviso)
            d["crc_ok"] = ok if d["crc_ok"] is None else (d["crc_ok"] and ok)
        elif tipo == "PHER":
            k = m["iter"]
            if k <= self.iter_aplicada:
                return  # llego tarde: esa iteracion ya se cerro (igual que en el nodo)
            try:
                e = self.lab.arista_entre(m["origen"], m["destino"])
            except KeyError:
                print(f"AVISO: PHER del nodo {n} sobre una arista que no existe "
                      f"({m['origen']}-{m['destino']})")
                return
            # Se GUARDA (no se suma) por arista: si un datagrama llega repetido, no cuenta doble.
            self.pher.setdefault((n, k), {})[e] = (m["origen"], m["destino"], m["deposito"])
        elif tipo == "FIN":
            k = m["iter"]
            if k > self.iter_aplicada:
                self.fin[(n, k)] = m
                self.t_primer_fin.setdefault(k, t)
            d["iter"] = max(d["iter"], k)
        elif tipo == "PATH":
            d["ruta"] = m["camino"]
            d["longitud"] = m["longitud"]
            r = self.robots[n]
            if r["t_inicio"] is None and m["camino"]:
                # La ruta solo se puede cambiar mientras el carrito no haya arrancado.
                r["tray"] = Trayectoria(self.lab, m["camino"])
        elif tipo == "ESTADO":
            d["fase"] = m["fase"]
            d["iter"] = max(d["iter"], m["iter"])
            d["mejor"] = m["mejor"]
            d["celda"] = m["celda"]
            d["vivos_rep"] = m["vivos"]
            d["t_estado"] = t
            d["rssi"] = m["rssi"]
            if m["fase"] in ("RECORRIDO", "TERMINADO"):
                self._seguir_carrito(n, t)
        elif tipo == "TAU":
            # Un nodo reiniciado pide/recibe la feromona completa: si es mas nueva, se adopta.
            if m["iter"] > self.iter_aplicada and len(m["tau"]) == len(self.ref.tau):
                self.ref.tau = list(m["tau"])
                self.iter_aplicada = m["iter"]
                self.ref.iteracion = m["iter"]

    def _seguir_carrito(self, n: int, t: float) -> None:
        """Decide cuando arranca el carrito virtual y lo corrige con la celda que reporta el real.

        - Sin hardware: arranca cuando el nodo pasa a RECORRIDO mas el escalonado del protocolo
          ((n-1) * ESCALON_RECORRIDO_S), que es lo mismo que hace el firmware.
        - Con hardware: no se adivina; arranca cuando la celda reportada ya va adelante del inicio.
        - En los dos: si el carrito real reporta una celda a la que el virtual aun no llego, se
          adelanta el virtual; si el virtual va mas de una celda por delante del real (el real se
          atraso, p. ej. por una rueda que patina), se frena esperando en la celda siguiente."""
        d, r = self.nodos[n], self.robots[n]
        if d["t_recorrido"] is None:
            d["t_recorrido"] = t
            if r["tray"] is None and d["ruta"]:
                r["tray"] = Trayectoria(self.lab, d["ruta"])
            if r["tray"] is None:
                self.avisos.append(f"Nodo {n} en RECORRIDO sin ruta (no llego su PATH)")
                return
            if self.modo == "sin-hardware":
                r["t_inicio"] = t + (n - 1) * protocolo.ESCALON_RECORRIDO_S
        tray = r["tray"]
        if tray is None or d["celda"] not in tray.camino:
            return
        i = tray.camino.index(d["celda"])
        if i == 0:
            return
        if r["t_inicio"] is None or tray.indice_celda(t - r["t_inicio"]) < i:
            r["t_inicio"] = t - tray.tiempos[i]          # atrasado: alcanza la celda reportada
        elif i + 1 < len(tray.tiempos) and t - r["t_inicio"] > tray.tiempos[i + 1]:
            r["t_inicio"] = t - tray.tiempos[i + 1]      # adelantado: espera en la siguiente

    # ----------------------------------------------------------------- feromona
    def actualizar(self, t: float) -> None:
        """Cierra las iteraciones que ya se pueden cerrar, en orden (k, k+1, ...), como la
        'barrera' del firmware: la iteracion k se cierra cuando llego el FIN completo de todos los
        nodos vivos, o cuando pasaron BARRERA_S desde el primer FIN (se sigue sin los que faltan)."""
        while True:
            k = self.iter_aplicada + 1
            con_fin = [n for (n, kk) in self.fin if kk == k]
            if not con_fin:
                return
            completos = [n for n in sorted(con_fin)
                         if len(self.pher.get((n, k), {})) >= self.fin[(n, k)]["n_pher"]]
            esperados = set(self.vivos(t))
            vencida = t - self.t_primer_fin[k] >= protocolo.BARRERA_S
            if not (esperados <= set(completos) or vencida):
                return
            for n in sorted(con_fin):
                if n not in completos:
                    self.incompletas.append((k, n))
            # La MISMA funcion que usa cada ESP32: evapora y suma en orden de nodo y de arista.
            self.ref.aplicar_iteracion({n: self.pher.get((n, k), {}) for n in completos})
            self.iter_aplicada = k
            for n in con_fin:
                self.fin.pop((n, k), None)
                self.pher.pop((n, k), None)
            self.t_primer_fin.pop(k, None)

    # ----------------------------------------------------------------- carritos
    def pose_carrito(self, n: int, t: float):
        """Pose (x, y, rumbo) del carrito n en el instante t, o None si no hay nada que mostrar.

        Mientras espera (antes de arrancar) y cuando ya llego, el carrito se corre a un costado
        de la celda (SEPARACION_ESTACIONADO * (n - 2)): asi los tres caben juntos en el inicio y
        en la meta sin taparse. Ese corrimiento entra y sale suave en el primer y ultimo tramo."""
        r = self.robots.get(n)
        if r is None:
            return None
        tray = r["tray"]
        if tray is None:
            x, y = centro_celda(*self.lab.celda(self.lab.inicio))
            base, w = (x, y, 0.0), 1.0
        else:
            s = -1.0 if r["t_inicio"] is None else t - r["t_inicio"]
            base = tray.pose(s)
            w_ini = 1.0 - suave(s / 0.8)
            w_fin = suave((s - (tray.duracion - 0.8)) / 0.8)
            w = max(w_ini, w_fin)
        x, y, rumbo = base
        lado = SEPARACION_ESTACIONADO * (n - 2) * w
        # Corrimiento perpendicular al rumbo (a la izquierda del carrito = (-sen, cos)).
        return (x - math.sin(rumbo) * lado, y + math.cos(rumbo) * lado, rumbo)

    def carrito_termino(self, n: int, t: float) -> bool:
        r = self.robots.get(n)
        if r is None or r["tray"] is None:
            return True
        return r["t_inicio"] is not None and t - r["t_inicio"] >= r["tray"].duracion

    # ----------------------------------------------------------------- resumen
    def convergio(self):
        """La colonia convergio si siguiendo siempre la arista de mas feromona (sin azar) se
        llega a la meta por un camino de longitud optima Y en ningun paso hubo empate de feromona.
        Es el mismo criterio de aco.simular_enjambre y de las pruebas (camino_codicioso con
        estricto=True), el que explica el README.

        Devuelve (convergio, camino): el camino es el codicioso SIN la condicion de empate, para
        poder dibujarlo siempre (en el video y en la app), aunque todavia no cuente como decidido."""
        cod = self.ref.camino_codicioso()
        decidido = self.ref.camino_codicioso(estricto=True)
        opt = aco.camino_optimo(self.lab)
        # Sin ninguna iteracion aplicada toda la feromona vale tau0 y el camino "codicioso" sale
        # solo del orden de desempate (+x, +y, ...): podria coincidir con el optimo por suerte.
        if self.iter_aplicada == 0 or decidido is None or opt is None:
            return False, cod
        return abs(self.lab.longitud_camino(decidido) - self.lab.longitud_camino(opt)) < 1e-9, cod


# ---------------------------------------------------------------------------------------------
# Escena PyBullet
# ---------------------------------------------------------------------------------------------
def caja(medias, pos, rgba, orn=(0, 0, 0, 1)) -> int:
    """Cuerpo estatico solo visual (sin colision: los carritos se mueven cinematicamente con
    resetBasePositionAndOrientation, no hace falta que la fisica calcule choques)."""
    vis = p.createVisualShape(p.GEOM_BOX, halfExtents=medias, rgbaColor=rgba)
    return p.createMultiBody(baseMass=0, baseCollisionShapeIndex=-1, baseVisualShapeIndex=vis,
                             basePosition=pos, baseOrientation=orn)


ESCONDIDO = (0.0, 0.0, -1.0)  # los marcadores que no se usan se guardan bajo el piso


class Escena:
    def __init__(self, lab: aco.Laberinto):
        self.lab = lab
        p.connect(p.DIRECT)
        p.resetSimulation()
        cols, fils = lab.columnas, lab.filas
        ancho, alto = cols * 0.2, fils * 0.2
        self.centro = (ancho / 2, alto / 2)

        # Piso grande y oscuro alrededor del laberinto.
        caja((ancho, alto, 0.005), (self.centro[0], self.centro[1], -0.005), (0.30, 0.31, 0.33, 1))

        # Baldosas: una por celda, apenas mas chicas que 20 cm para que se vea la junta.
        for y in range(fils):
            for x in range(cols):
                cx, cy = centro_celda(x, y)
                c = COLOR_BALDOSA[(x + y) % 2]
                caja((0.097, 0.097, Z_BALDOSA / 2), (cx, cy, Z_BALDOSA / 2), (*c, 1))

        # Inicio A: cuadro verde.
        ix, iy = lab.celda(lab.inicio)
        cx, cy = centro_celda(ix, iy)
        caja((0.085, 0.085, 0.001), (cx, cy, Z_MARCA - 0.001), (0.20, 0.72, 0.30, 1))

        # Meta: 4 x 4 cuadros blancos y negros, como la bandera de llegada de una carrera.
        mx, my = lab.celda(lab.meta)
        cx, cy = centro_celda(mx, my)
        lado = 0.17 / 4
        for i in range(4):
            for j in range(4):
                c = (0.97, 0.97, 0.97, 1) if (i + j) % 2 == 0 else (0.05, 0.05, 0.05, 1)
                caja((lado / 2, lado / 2, 0.001),
                     (cx - 0.085 + lado * (i + 0.5), cy - 0.085 + lado * (j + 0.5), Z_MARCA - 0.001), c)

        # Paredes internas: cada par de celdas de maze.json es una pared en el borde comun.
        g, h = GROSOR_PARED, ALTO_PARED
        for a, b in lab.paredes:
            (ax, ay), (bx, by) = a, b
            if ay == by:   # vecinas en x -> pared vertical (paralela a y) en x = max(ax, bx) * 0.2
                caja((g / 2, 0.1 + g / 2, h / 2), (max(ax, bx) * 0.2, ay * 0.2 + 0.1, h / 2), COLOR_PARED)
            else:          # vecinas en y -> pared horizontal en y = max(ay, by) * 0.2
                caja((0.1 + g / 2, g / 2, h / 2), (ax * 0.2 + 0.1, max(ay, by) * 0.2, h / 2), COLOR_PARED)
        # Borde exterior: cuatro paredes largas.
        caja((ancho / 2 + g / 2, g / 2, h / 2), (ancho / 2, 0, h / 2), COLOR_PARED)
        caja((ancho / 2 + g / 2, g / 2, h / 2), (ancho / 2, alto, h / 2), COLOR_PARED)
        caja((g / 2, alto / 2 + g / 2, h / 2), (0, alto / 2, h / 2), COLOR_PARED)
        caja((g / 2, alto / 2 + g / 2, h / 2), (ancho, alto / 2, h / 2), COLOR_PARED)

        # Feromona: una franja plana de centro a centro sobre cada arista (en el orden de aco.py,
        # asi la franja i corresponde a tau[i]). Mide 4 mm de alto; se sube hasta 4 mm segun tau.
        self.franjas = []
        for u, v in lab.aristas:
            (ux, uy), (vx, vy) = centro_celda(*lab.celda(u)), centro_celda(*lab.celda(v))
            horizontal = uy == vy
            medias = (0.1, 0.013, 0.002) if horizontal else (0.013, 0.1, 0.002)
            pos = ((ux + vx) / 2, (uy + vy) / 2, Z_FEROMONA - 0.002)
            self.franjas.append((caja(medias, pos, (*COLOR_BALDOSA[0], 1)), pos))

        # Rutas: por cada nodo, un marcador en cada celda y una barrita en cada arista, todos
        # escondidos bajo el piso hasta que esa celda/arista entra en la mejor ruta del nodo. Se
        # crean una sola vez y se mueven (crear y borrar cuerpos en cada cuadro es lento y PyBullet
        # reutiliza los ids de los borrados). Cada nodo usa una esquina distinta de la celda para
        # que se vean las tres rutas aunque pasen por las mismas celdas. Ningun par de nodos
        # comparte desfase en x ni en y: si dos barras quedaran sobre la misma linea se pisarian
        # (z-fighting) y se verian cortadas a trozos.
        self.desfase = {1: (-0.06, 0.06), 2: (0.06, 0.035), 3: (-0.035, -0.06)}
        self.marcas = {}
        self.barras = {}
        for n in NODOS:
            dx, dy = self.desfase[n]
            rgba = (*COLOR_NODO[n], 1)
            self.marcas[n] = {}
            for c in range(cols * fils):
                cx, cy = centro_celda(*lab.celda(c))
                b = caja((0.017, 0.017, 0.002), ESCONDIDO, rgba)
                self.marcas[n][c] = (b, (cx + dx, cy + dy, Z_RUTA - 0.002))
            self.barras[n] = {}
            for e, (u, v) in enumerate(lab.aristas):
                (ux, uy), (vx, vy) = centro_celda(*lab.celda(u)), centro_celda(*lab.celda(v))
                medias = (0.1, 0.005, 0.0015) if uy == vy else (0.005, 0.1, 0.0015)
                b = caja(medias, ESCONDIDO, rgba)
                self.barras[n][e] = (b, ((ux + vx) / 2 + dx, (uy + vy) / 2 + dy, Z_RUTA - 0.003))
        self.ruta_mostrada = {n: None for n in NODOS}

        # Carritos.
        self.carros = {n: self._crear_carrito(COLOR_NODO[n]) for n in NODOS}
        self.carro_gris = {n: False for n in NODOS}
        for n in NODOS:
            p.resetBasePositionAndOrientation(self.carros[n], ESCONDIDO, (0, 0, 0, 1))

        # Camara cenital casi ortogonal: muy alta (6 m) y con un campo de vision chico (~11
        # grados). Con perspectiva normal, desde cerca, las paredes se verian inclinadas hacia
        # afuera y taparian las celdas del borde; desde lejos y con zoom se ven como un plano.
        self.altura_cam = 6.0
        ver = max(ancho, alto) + 0.20     # 10 cm de margen alrededor (ahi van "A" y "META")
        fov = math.degrees(2 * math.atan((ver / 2) / self.altura_cam))
        self.vista = p.computeViewMatrix(cameraEyePosition=[self.centro[0], self.centro[1], self.altura_cam],
                                         cameraTargetPosition=[self.centro[0], self.centro[1], 0],
                                         cameraUpVector=[0, 1, 0])  # +y queda hacia arriba en la imagen
        self.proy = p.computeProjectionMatrixFOV(fov=fov, aspect=1.0, nearVal=5.5, farVal=6.5)
        # Las matrices de PyBullet vienen como listas de 16 en orden de columnas (estilo OpenGL):
        # se transponen para poder proyectar puntos 3D a pixeles y escribir textos encima.
        self._pv = np.array(self.proy).reshape(4, 4).T @ np.array(self.vista).reshape(4, 4).T

    def _crear_carrito(self, color) -> int:
        """Carrito armado con createMultiBody: el cuerpo es la base y las 4 ruedas (cilindros) y
        una 'tapa' blanca adelante (para que se vea hacia donde mira) van como links fijos."""
        z_base = RADIO_RUEDA + 0.010   # el centro del cuerpo queda 1 cm por encima del eje
        cuerpo = p.createVisualShape(p.GEOM_BOX, halfExtents=[LARGO_CARRO / 2, ANCHO_CUERPO / 2, ALTO_CUERPO / 2],
                                     rgbaColor=[*color, 1])
        rueda = p.createVisualShape(p.GEOM_CYLINDER, radius=RADIO_RUEDA, length=ANCHO_RUEDA,
                                    rgbaColor=[0.08, 0.08, 0.08, 1])
        tapa = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.012, ANCHO_CUERPO / 2 - 0.004, 0.002],
                                   rgbaColor=[0.97, 0.97, 0.97, 1])
        # El cilindro de PyBullet tiene su eje en z: se gira 90 grados sobre x para que quede
        # como eje de rueda (a lo largo de y, el ancho del carrito).
        eje_y = p.getQuaternionFromEuler([math.pi / 2, 0, 0])
        dx, dy, dz = 0.032, ANCHO_CUERPO / 2 + ANCHO_RUEDA / 2, RADIO_RUEDA - z_base
        posiciones = [[dx, dy, dz], [dx, -dy, dz], [-dx, dy, dz], [-dx, -dy, dz],
                      [LARGO_CARRO / 2 - 0.014, 0, ALTO_CUERPO / 2 + 0.002]]
        visuales = [rueda] * 4 + [tapa]
        orient = [eje_y] * 4 + [[0, 0, 0, 1]]
        k = len(visuales)
        cid = p.createMultiBody(
            baseMass=0, baseCollisionShapeIndex=-1, baseVisualShapeIndex=cuerpo,
            basePosition=[0, 0, z_base],
            linkMasses=[0] * k, linkCollisionShapeIndices=[-1] * k, linkVisualShapeIndices=visuales,
            linkPositions=posiciones, linkOrientations=orient,
            linkInertialFramePositions=[[0, 0, 0]] * k, linkInertialFrameOrientations=[[0, 0, 0, 1]] * k,
            linkParentIndices=[0] * k, linkJointTypes=[p.JOINT_FIXED] * k, linkJointAxis=[[0, 0, 1]] * k)
        self.z_carro = z_base
        return cid

    # ----------------------------------------------------------------- actualizar geometria
    def actualizar(self, g: EstadoGemelo, t: float) -> None:
        # Feromona normalizada entre la minima y la maxima del momento. Al principio todas valen
        # tau0 (no hay informacion) y no se pinta nada; a medida que la evaporacion borra las
        # aristas poco usadas y las hormigas refuerzan las buenas, aparece el camino.
        tau = np.array(g.ref.tau)
        lo, hi = float(tau.min()), float(tau.max())
        tn = (tau - lo) / (hi - lo) if hi - lo > 1e-12 else np.zeros_like(tau)
        for i, (b, pos) in enumerate(self.franjas):
            a = float(tn[i]) ** 0.7   # gamma < 1: que las aristas medianas tambien se noten
            if a < FEROMONA_MINIMA:
                # Casi sin feromona: se esconde bajo el piso. Es la "opacidad 0"; el renderizador
                # por software no mezcla transparencias de forma confiable, asi que la opacidad se
                # simula con el color (de lila palido a violeta) y escondiendo las mas debiles.
                p.resetBasePositionAndOrientation(b, ESCONDIDO, (0, 0, 0, 1))
                continue
            p.changeVisualShape(b, -1, rgbaColor=[*color_feromona(a).tolist(), 1])
            # Alto: la franja sube hasta 4 mm segun tau (las mas cargadas quedan encima).
            p.resetBasePositionAndOrientation(b, (pos[0], pos[1], pos[2] + 0.004 * a), (0, 0, 0, 1))

        # Rutas: solo se mueven marcadores si la ruta del nodo cambio.
        for n in NODOS:
            d = g.nodos.get(n)
            ruta = tuple(d["ruta"]) if d and d["ruta"] else None
            if ruta == self.ruta_mostrada[n]:
                continue
            celdas = set(ruta or ())
            aristas = set()
            if ruta:
                for a, b in zip(ruta, ruta[1:]):
                    try:
                        aristas.add(self.lab.arista_entre(a, b))
                    except KeyError:
                        pass
            for c, (b, pos) in self.marcas[n].items():
                p.resetBasePositionAndOrientation(b, pos if c in celdas else ESCONDIDO, (0, 0, 0, 1))
            for e, (b, pos) in self.barras[n].items():
                p.resetBasePositionAndOrientation(b, pos if e in aristas else ESCONDIDO, (0, 0, 0, 1))
            self.ruta_mostrada[n] = ruta

        # Carritos: un nodo apagado deja su carrito quieto (ultima pose) y gris.
        for n in NODOS:
            if n not in g.nodos:
                continue
            r = g.robots[n]
            apagado = g.apagado(n, t)
            if not apagado or r["pose"] is None:
                r["pose"] = g.pose_carrito(n, t)
            x, y, rumbo = r["pose"]
            p.resetBasePositionAndOrientation(self.carros[n], (x, y, self.z_carro),
                                              p.getQuaternionFromEuler([0, 0, rumbo]))
            if apagado != self.carro_gris[n]:
                color = GRIS_APAGADO if apagado else COLOR_NODO[n]
                p.changeVisualShape(self.carros[n], -1, rgbaColor=[*color, 0.55 if apagado else 1])
                self.carro_gris[n] = apagado

    def a_pixel(self, x, y, z=0.0) -> tuple:
        """Punto 3D -> pixel de la imagen (para escribir textos encima con Pillow)."""
        c = self._pv @ np.array([x, y, z, 1.0])
        nx, ny = c[0] / c[3], c[1] / c[3]
        return ((nx + 1) / 2 * LADO_3D, (1 - ny) / 2 * LADO_3D)

    def renderizar(self) -> Image.Image:
        w, h, rgba, _, _ = p.getCameraImage(LADO_3D, LADO_3D, self.vista, self.proy,
                                            renderer=p.ER_TINY_RENDERER,
                                            lightDirection=[0.4, -0.3, 1.0], shadow=0)
        img = np.reshape(np.array(rgba, dtype=np.uint8), (h, w, 4))[:, :, :3]
        return Image.fromarray(img)


# ---------------------------------------------------------------------------------------------
# Composicion del cuadro (vista 3D + panel) con Pillow
# ---------------------------------------------------------------------------------------------
def fuente(tam: int, estilo: str = ""):
    """DejaVuSans (viene en Windows si se instalo, y en Docker con fonts-dejavu-core). Si no esta,
    la fuente por defecto de Pillow, que desde Pillow 10.1 acepta tamano."""
    nombre = {"": "DejaVuSans.ttf", "negrita": "DejaVuSans-Bold.ttf", "mono": "DejaVuSansMono.ttf"}[estilo]
    rutas = [nombre, os.path.join("/usr/share/fonts/truetype/dejavu", nombre),
             os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", nombre),
             "DejaVuSans.ttf"]
    for r in rutas:
        try:
            return ImageFont.truetype(r, tam)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:
        return ImageFont.load_default()


class Compositor:
    FONDO = (22, 24, 30)
    TEXTO = (232, 233, 238)
    TENUE = (150, 155, 168)
    ROJO = (255, 95, 85)
    VERDE = (110, 210, 120)

    def __init__(self, escena: Escena, gemelo: EstadoGemelo, info_modo: str):
        self.escena = escena
        self.g = gemelo
        self.info_modo = info_modo
        self.f_titulo = fuente(24, "negrita")
        self.f_sub = fuente(14, "negrita")
        self.f = fuente(15)
        self.f_chico = fuente(13)
        self.f_mono = fuente(11, "mono")
        self.f_celda = fuente(11)
        self.f_marca = fuente(20, "negrita")
        self.opt = aco.camino_optimo(gemelo.lab)
        self.L_opt = gemelo.lab.longitud_camino(self.opt) if self.opt else None

    def cuadro(self, t: float, total_iter=None) -> Image.Image:
        g, esc, lab = self.g, self.escena, self.g.lab
        vista = esc.renderizar()
        d3 = ImageDraw.Draw(vista)
        # Numero de cada celda en su esquina inferior derecha (ayuda a leer las rutas del json).
        for c in range(lab.columnas * lab.filas):
            cx, cy = centro_celda(*lab.celda(c))
            px, py = esc.a_pixel(cx + 0.062, cy - 0.072, Z_BALDOSA)
            d3.text((px, py), str(c), font=self.f_celda, fill=(120, 115, 105), anchor="mm")
        ix, iy = centro_celda(*lab.celda(lab.inicio))
        # "A" y "META" van en el margen, fuera del laberinto, cuando la celda esta en el borde:
        # asi no tapan a los carritos estacionados en esas celdas.
        if lab.celda(lab.inicio)[0] == 0:
            px, py = esc.a_pixel(ix - 0.135, iy, 0.01)
        else:
            px, py = esc.a_pixel(ix + 0.06, iy + 0.065, 0.01)
        d3.text((px, py), "A", font=self.f_marca, fill=(255, 255, 255), anchor="mm",
                stroke_width=2, stroke_fill=(20, 80, 30))
        mx, my = centro_celda(*lab.celda(lab.meta))
        if lab.celda(lab.meta)[1] == lab.filas - 1:
            px, py = esc.a_pixel(mx, my + 0.135, 0.01)
        else:
            px, py = esc.a_pixel(mx, my, 0.01)
        d3.text((px, py), "META", font=self.f_sub, fill=(255, 220, 60), anchor="mm",
                stroke_width=3, stroke_fill=(0, 0, 0))
        # Numero de nodo sobre cada carrito.
        for n, r in g.robots.items():
            if r["pose"] is None:
                continue
            x, y, _ = r["pose"]
            px, py = esc.a_pixel(x, y, 0.05)
            d3.text((px, py), str(n), font=self.f_sub, fill=(255, 255, 255), anchor="mm",
                    stroke_width=2, stroke_fill=(0, 0, 0))

        lienzo = Image.new("RGB", (ANCHO_LIENZO, LADO_3D), self.FONDO)
        lienzo.paste(vista, (0, 0))
        d = ImageDraw.Draw(lienzo)
        x0, y = LADO_3D + 22, 18

        def linea(texto, f=None, color=None, alto=21):
            nonlocal y
            d.text((x0, y), texto, font=f or self.f, fill=color or self.TEXTO)
            y += alto

        linea("Gemelo digital ACO", self.f_titulo, alto=32)
        linea(f"Enjambre de 3 carritos ESP32 - {lab.nombre}", self.f_chico, self.TENUE, alto=24)
        for i, ren in enumerate(self.info_modo.split("\n")):
            linea(("Modo: " if i == 0 else "      ") + ren, self.f_chico)
        linea(f"Tiempo: {t:6.1f} s", self.f_chico)
        it_txt = f"{g.iter_aplicada}" + (f" / {total_iter}" if total_iter else "")
        linea(f"Iteración (feromona del gemelo): {it_txt}", self.f_chico, alto=28)

        linea("NODOS", self.f_sub, self.TENUE, alto=22)
        for n in NODOS:
            dn = g.nodos.get(n)
            apagado = g.apagado(n, t) if dn else True
            color = GRIS_APAGADO if (apagado and dn) else COLOR_NODO[n]
            rgb = tuple(int(255 * c) for c in color)
            d.rectangle([x0, y + 3, x0 + 14, y + 17], fill=rgb)
            if dn is None:
                estado = "sin noticias"
            elif apagado:
                estado = f"APAGADO (última fase: {FASES_TXT.get(dn['fase'], dn['fase'])})"
            else:
                estado = FASES_TXT.get(dn["fase"], dn["fase"])
            d.text((x0 + 22, y), f"Nodo {n} ({NOMBRE_COLOR[n]}): {estado}", font=self.f_chico,
                   fill=self.TENUE if apagado else self.TEXTO)
            y += 19
            if dn:
                L = dn["longitud"] if dn["longitud"] is not None else dn["mejor"]
                L_txt = f"{L:.2f} m ({round(L / lab.tam_celda)} celdas)" if L else "--"
                d.text((x0 + 22, y), f"mejor ruta {L_txt}   celda {dn['celda']}   it {dn['iter']}",
                       font=self.f_chico, fill=self.TENUE)
            y += 22
        vivos = g.vivos(t)
        linea(f"Nodos vivos: {', '.join(map(str, vivos)) if vivos else 'ninguno'}", self.f_chico, alto=26)

        if self.opt:
            linea(f"Ruta óptima (BFS): {self.L_opt:.2f} m, {len(self.opt) - 1} pasos", self.f_chico)
        conv, _ = g.convergio()
        linea("Camino de máxima feromona: " + ("ÓPTIMO (convergió)" if conv else "todavía no"),
              self.f_chico, self.VERDE if conv else self.TEXTO, alto=26)

        pr = g.params
        linea("PARÁMETROS", self.f_sub, self.TENUE, alto=22)
        linea(f"alfa = {pr.alfa:g}   beta = {pr.beta:g}   rho = {pr.rho:g}   Q = {pr.q:g}", self.f_chico)
        linea(f"hormigas/nodo = {pr.hormigas}   CRC maze = {g.crc_esperado:08X}", self.f_chico, alto=26)

        # Leyenda.
        linea("LEYENDA", self.f_sub, self.TENUE, alto=22)
        # Barra de feromona con los mismos colores que las franjas.
        for i in range(160):
            c = color_feromona(i / 159)
            d.line([x0 + i, y + 3, x0 + i, y + 15], fill=tuple(int(255 * v) for v in c))
        d.text((x0 + 170, y), "feromona (baja -> alta)", font=self.f_chico, fill=self.TEXTO)
        y += 22
        for n in NODOS:
            rgb = tuple(int(255 * c) for c in COLOR_NODO[n])
            d.rectangle([x0 + 3, y + 5, x0 + 11, y + 13], fill=rgb)
            d.line([x0 + 14, y + 9, x0 + 34, y + 9], fill=rgb, width=3)
            d.text((x0 + 42, y), f"carrito y mejor ruta del nodo {n}", font=self.f_chico, fill=self.TEXTO)
            y += 19
        d.rectangle([x0, y + 3, x0 + 14, y + 17], fill=(51, 184, 77))
        d.text((x0 + 22, y), "inicio A", font=self.f_chico, fill=self.TEXTO)
        for i in range(2):
            for j in range(2):
                d.rectangle([x0 + 110 + 7 * i, y + 3 + 7 * j, x0 + 116 + 7 * i, y + 9 + 7 * j],
                            fill=(245, 245, 245) if (i + j) % 2 == 0 else (10, 10, 10))
        d.text((x0 + 132, y), "meta", font=self.f_chico, fill=self.TEXTO)
        d.rectangle([x0 + 190, y + 3, x0 + 204, y + 17], fill=tuple(int(255 * c) for c in GRIS_APAGADO))
        d.text((x0 + 212, y), "nodo apagado", font=self.f_chico, fill=self.TEXTO)
        y += 28

        # Avisos (CRC distinto, falta de datos) y ultima linea cruda en modo hardware.
        if g.modo == "hardware":
            if g.t_ultimo_mensaje is None:
                linea(f"Sin datos UDP hace {t:.0f} s", self.f_chico, self.ROJO)
            elif t - g.t_ultimo_mensaje > 10:
                linea(f"Sin datos UDP hace {t - g.t_ultimo_mensaje:.0f} s", self.f_chico, self.ROJO)
            ult = g.ultima_linea[:52] + ("..." if len(g.ultima_linea) > 52 else "")
            linea("Ultima linea: " + (ult or "(ninguna)"), self.f_mono, self.TENUE, alto=16)
        for a in g.avisos[-3:]:
            # Se parte en renglones de ~48 caracteres para que quepa en el panel.
            palabras, ren = a.split(), ""
            for w in palabras:
                if len(ren) + len(w) + 1 > 48:
                    linea(ren, self.f_chico, self.ROJO, alto=17)
                    ren = w
                else:
                    ren = (ren + " " + w).strip()
            if ren:
                linea(ren, self.f_chico, self.ROJO, alto=19)
        return lienzo


# ---------------------------------------------------------------------------------------------
# Salidas
# ---------------------------------------------------------------------------------------------
class Salidas:
    """Video, telemetria y resumen. Todo se escribe con 'w' (sobrescribe la corrida anterior)."""

    def __init__(self, carpeta: str, modo: str, fps: int):
        os.makedirs(carpeta, exist_ok=True)
        self.carpeta, self.modo, self.fps = carpeta, modo, fps
        self.ruta_mp4 = os.path.join(carpeta, f"gemelo_{modo}.mp4")
        self.ruta_png = os.path.join(carpeta, f"ruta_final_{modo}.png")
        self.ruta_jsonl = os.path.join(carpeta, f"telemetria_{modo}.jsonl")
        self.ruta_json = os.path.join(carpeta, f"resumen_{modo}.json")
        # H.264 (libx264) con pixeles yuv420p: el formato que reproducen GitHub, Windows y los
        # celulares. Con yuv444p (lo que elegiria ffmpeg solo a partir de RGB) muchos no lo abren.
        self.video = imageio.get_writer(self.ruta_mp4, fps=fps, codec="libx264",
                                        pixelformat="yuv420p", quality=7, macro_block_size=16)
        self.telemetria = open(self.ruta_jsonl, "w", encoding="utf-8")
        self.cuadros = 0
        self.ultimo = None

    def agregar_cuadro(self, img: Image.Image, veces: int = 1) -> None:
        arr = np.asarray(img)
        for _ in range(max(1, veces)):
            self.video.append_data(arr)
            self.cuadros += 1
        self.ultimo = img

    def registrar(self, t: float, linea: str, msg) -> None:
        self.telemetria.write(json.dumps({"t": round(t, 3), "linea": linea, "mensaje": msg},
                                         ensure_ascii=True) + "\n")

    def cerrar(self, resumen: dict) -> None:
        self.video.close()
        self.telemetria.close()
        if self.ultimo is not None:
            self.ultimo.save(self.ruta_png)
        with open(self.ruta_json, "w", encoding="utf-8") as f:
            json.dump(resumen, f, indent=2, ensure_ascii=False)


class EstadoEnVivo:
    """Foto del gemelo para la app del tema (app/): resultados/vivo_<modo>.json.

    El video mp4 recien se puede ver al final; mientras tanto la app lee este json chiquito
    (unas 2 veces por segundo) y dibuja el laberinto con la feromona de cada arista y la posicion
    de los 3 carritos. Es solo una ventana para mirar: el gemelo no lo vuelve a leer.

    Se escribe a un .tmp y despues se renombra (os.replace) para que la app nunca lea un json a
    medio escribir. En Windows el renombrado falla si justo en ese instante el servidor de la app
    tiene el archivo abierto: en ese caso se salta esa foto (llega otra enseguida)."""

    CADA_S = 0.4   # segundos de reloj entre una foto y la siguiente

    def __init__(self, carpeta: str, modo: str, t_total):
        self.ruta = os.path.join(carpeta, f"vivo_{modo}.json")
        self.modo = modo
        self.t_total = t_total        # tiempo virtual total (sin hardware) o None (hardware)
        self.inicio = time.time()     # la app descarta fotos de una corrida anterior con esto
        self.proxima = 0.0

    def escribir(self, g: EstadoGemelo, t: float, cuadros: int, terminado: bool = False,
                 forzar: bool = False) -> None:
        ahora = time.monotonic()
        if not (forzar or terminado) and ahora < self.proxima:
            return
        self.proxima = ahora + self.CADA_S
        lab = g.lab
        nodos = {}
        for n in sorted(g.nodos):
            d = g.nodos[n]
            pose = g.pose_carrito(n, t)
            nodos[str(n)] = {
                "fase": d["fase"], "iter": d["iter"], "ruta": d["ruta"], "longitud": d["longitud"],
                "celda": d["celda"], "apagado": g.apagado(n, t),
                "pose": [round(v, 4) for v in pose] if pose else None,
            }
        conv, cod = g.convergio()
        foto = {
            "modo": self.modo, "inicio": self.inicio, "reloj_s": round(time.time() - self.inicio, 1),
            "t": round(t, 2), "t_total": self.t_total, "iter": g.iter_aplicada,
            "iteraciones": g.params.iteraciones, "columnas": lab.columnas, "filas": lab.filas,
            "tam_celda": lab.tam_celda, "inicio_celda": lab.inicio, "meta_celda": lab.meta,
            "aristas": [list(a) for a in lab.aristas], "tau": [round(x, 4) for x in g.ref.tau],
            "camino_feromona": cod, "convergio": conv, "nodos": nodos, "vivos": g.vivos(t),
            "ultima_linea": g.ultima_linea[:120], "cuadros": cuadros, "terminado": terminado,
        }
        tmp = self.ruta + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(foto, f, ensure_ascii=False)
            os.replace(tmp, self.ruta)
        except OSError:
            pass  # el archivo estaba abierto por la app justo ahora: se escribe en la proxima


def armar_resumen(g: EstadoGemelo, t_final: float, sal: Salidas, extra: dict) -> dict:
    lab = g.lab
    opt = aco.camino_optimo(lab)
    L_opt = lab.longitud_camino(opt) if opt else None
    conv, cod = g.convergio()
    por_nodo = {}
    for n in sorted(g.nodos):
        d = g.nodos[n]
        L = d["longitud"]
        por_nodo[str(n)] = {
            "mejor_ruta": d["ruta"],
            "longitud_m": L,
            "es_optima": (L is not None and L_opt is not None and abs(L - L_opt) < 1e-6),
            "fase_final": d["fase"],
            "apagado_al_final": g.apagado(n, t_final),
            "ultima_iteracion_reportada": d["iter"],
            "crc": f"{d['crc']:08X}" if d["crc"] is not None else None,
            "crc_coincide": d["crc_ok"],
            "carrito_termino_recorrido": g.carrito_termino(n, t_final),
        }
    return {
        "modo": g.modo,
        "laberinto": lab.nombre,
        "crc_maze": f"{g.crc_esperado:08X}",
        "parametros": asdict(g.params),
        "ruta_optima_bfs": opt,
        "longitud_optima_m": L_opt,
        "por_nodo": por_nodo,
        "iteraciones_aplicadas_por_el_gemelo": g.iter_aplicada,
        "camino_maxima_feromona": cod,
        # Feromona reconstruida, en el orden de las aristas de aco.py (sirve para compararla con
        # la que imprime un nodo o con aco.simular_enjambre: deberia ser identica bit a bit).
        "feromona_final": g.ref.tau,
        "aristas": [list(a) for a in lab.aristas],
        "convergio": conv,
        "fin_incompletos": [{"iteracion": k, "nodo": n} for k, n in g.incompletas],
        "mensajes_por_tipo": g.conteo,
        "duracion_s": round(t_final, 2),
        "cuadros_video": sal.cuadros,
        "fps": sal.fps,
        "avisos": g.avisos,
        "archivos": {k: os.path.basename(v) for k, v in
                     (("video", sal.ruta_mp4), ("imagen", sal.ruta_png),
                      ("telemetria", sal.ruta_jsonl))},
        **extra,
    }


# ---------------------------------------------------------------------------------------------
# Modo sin hardware: telemetria simulada en tiempo virtual
# ---------------------------------------------------------------------------------------------
def correr_sin_hardware(args, lab, params) -> int:
    caidas = {args.apagar_nodo: args.en_iteracion} if args.apagar_nodo else None
    eventos, r = protocolo.flujo_simulado(lab, params, caidas=caidas)
    t_fin = eventos[-1][0] if eventos else 0.0
    print(f"Telemetria simulada: {len(eventos)} lineas, {t_fin:.1f} s de tiempo virtual"
          + (f", nodo {args.apagar_nodo} se apaga tras la iteracion {args.en_iteracion}" if caidas else ""))

    g = EstadoGemelo(lab, params, "sin-hardware")
    escena = Escena(lab)
    modo_txt = "sin hardware (telemetría simulada)"
    if caidas:
        modo_txt += f"\nprueba 14: nodo {args.apagar_nodo} se apaga tras la it {args.en_iteracion}"
    comp = Compositor(escena, g, modo_txt)
    # Con un nodo apagado los archivos llevan un sufijo, para no pisar la corrida normal.
    sal = Salidas(args.salida, "sin-hardware" + (f"_apagado{args.apagar_nodo}" if caidas else ""), args.fps)
    vivo = EstadoEnVivo(args.salida, sal.modo, round(t_fin, 2))
    vivo.escribir(g, 0.0, 0, forzar=True)

    dt = 1.0 / args.fps
    i, cuadro, t = 0, 0, 0.0
    reloj = time.monotonic()
    proximo_aviso = 2.5
    while True:
        # Tiempo virtual: el cuadro numero 'cuadro' corresponde a t = cuadro / fps. No se duerme:
        # se procesan todos los mensajes con instante <= t y se renderiza.
        t = cuadro * dt
        while i < len(eventos) and eventos[i][0] <= t + 1e-9:
            te, ln = eventos[i]
            for m in protocolo.leer_datagrama(ln.encode("ascii")):
                g.recibir(m, te, ln)
                sal.registrar(te, ln, m)
            i += 1
        g.actualizar(t)
        escena.actualizar(g, t)
        sal.agregar_cuadro(comp.cuadro(t, params.iteraciones))
        vivo.escribir(g, t, sal.cuadros)
        if t >= proximo_aviso:
            # "t = X s de Y s": la app (y el campo progreso_regex de probar.json) saca de aqui la
            # barra de avance; Y es el tiempo virtual total, conocido desde el principio.
            print(f"  t = {t:5.1f} s de {t_fin:.1f} s  iteracion {g.iter_aplicada:2d}  cuadros {sal.cuadros}")
            proximo_aviso += 2.5
        terminado = i >= len(eventos) and t >= t_fin and \
            all(g.carrito_termino(n, t) or g.apagado(n, t) for n in g.nodos)
        if terminado:
            break
        cuadro += 1
    sal.agregar_cuadro(sal.ultimo, veces=args.fps * 2)  # 2 s quieto al final para ver el resultado

    # Comprobacion: la feromona reconstruida por el gemelo debe ser IDENTICA (bit a bit) a la que
    # tienen los nodos que siguieron vivos hasta el final.
    vivos_fin = [n for n in NODOS if not caidas or caidas.get(n, math.inf) > params.iteraciones]
    identica = all(g.ref.tau == r["tau_final"][n] for n in vivos_fin)
    print(f"Feromona reconstruida igual a la de los nodos {vivos_fin}: {'si' if identica else 'NO'}")
    resumen = armar_resumen(g, t, sal, {
        "nodo_apagado": args.apagar_nodo, "apagado_en_iteracion": args.en_iteracion if caidas else None,
        "feromona_identica_a_los_nodos": identica,
        "segundos_de_computo": round(time.monotonic() - reloj, 1)})
    sal.cerrar(resumen)
    vivo.escribir(g, t, sal.cuadros, terminado=True)
    imprimir_final(resumen, sal)
    return 0 if identica else 1


# ---------------------------------------------------------------------------------------------
# Modo hardware: UDP en tiempo real
# ---------------------------------------------------------------------------------------------
def correr_hardware(args, lab, params) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", args.puerto))
    # No bloqueante: recvfrom devuelve enseguida (o lanza BlockingIOError si no hay nada), asi el
    # bucle nunca se queda esperando un paquete y el video sigue a ritmo constante.
    sock.setblocking(False)
    print(f"Escuchando telemetria UDP en 0.0.0.0:{args.puerto} (timeout {args.timeout:.0f} s, Ctrl+C para terminar)")
    print(f"Recordatorio: el PC debe estar en el WiFi {protocolo.SSID} con IP {protocolo.IP_PC}, "
          f"y el firewall debe dejar pasar UDP {args.puerto}.")

    g = EstadoGemelo(lab, params, "hardware")
    escena = Escena(lab)
    comp = Compositor(escena, g, f"hardware (UDP {args.puerto})")
    sal = Salidas(args.salida, "hardware", args.fps)
    vivo = EstadoEnVivo(args.salida, "hardware", None)
    vivo.escribir(g, 0.0, 0, forzar=True)

    t0 = time.monotonic()
    t = 0.0
    proximo_aviso_silencio = 10.0
    proximo_cruda = 5.0
    t_todo_terminado = None
    motivo = "timeout"
    try:
        while True:
            t = time.monotonic() - t0
            # Drenar TODO lo que haya en el buffer en cada vuelta (no un solo paquete): si solo se
            # leyera uno por cuadro, con 3 nodos mandando rafagas de PHER el gemelo se atrasaria.
            while True:
                try:
                    datos, _ = sock.recvfrom(4096)
                except BlockingIOError:
                    break
                except ConnectionResetError:
                    continue  # Windows lo lanza en UDP tras un ICMP "puerto inalcanzable"
                texto = datos.decode("ascii", errors="replace")
                for ln in texto.splitlines():
                    if not ln.strip():
                        continue
                    msgs = protocolo.leer_datagrama(ln.encode("ascii", errors="replace"))
                    sal.registrar(t, ln, msgs[0] if msgs else None)
                    g.ultima_linea = ln
                    for m in msgs:
                        g.recibir(m, t, ln)
            g.actualizar(t)
            vivo.escribir(g, t, sal.cuadros)

            # Diagnostico en consola cada 5 s ("it k/N" = iteraciones aplicadas). La barra de la app en
            # este modo sale de vivo_hardware.json (busqueda + recorridos), no de esta linea.
            if t >= proximo_cruda:
                if g.ultima_linea:
                    print(f"  t = {t:5.1f} s  it {g.iter_aplicada:2d}/{params.iteraciones}  vivos {g.vivos(t)}  ultima linea: {g.ultima_linea[:90]}")
                proximo_cruda += 5.0
            silencio = t if g.t_ultimo_mensaje is None else t - g.t_ultimo_mensaje
            if silencio >= proximo_aviso_silencio - 1e-6 and silencio >= 10.0:
                print(f"AVISO: no llega nada por UDP {args.puerto} hace {silencio:.0f} s. Revisa que el PC este "
                      f"en el WiFi {protocolo.SSID} con IP {protocolo.IP_PC} y que el firewall deje pasar UDP {args.puerto}.")
                proximo_aviso_silencio = silencio + 10.0
            elif silencio < 10.0:
                proximo_aviso_silencio = 10.0

            # Video a fps fijos de tiempo REAL: si renderizar tarda mas que 1/fps, se repite el
            # cuadro las veces necesarias para que el video dure lo mismo que la prueba.
            debidos = int(t * args.fps) + 1 - sal.cuadros
            if debidos > 0:
                escena.actualizar(g, t)
                sal.agregar_cuadro(comp.cuadro(t), veces=debidos)

            # Fin: todos los nodos vistos terminaron (o se apagaron) y sus carritos llegaron.
            vistos = list(g.nodos)
            listos = vistos and any(g.nodos[n]["fase"] == "TERMINADO" for n in vistos) and all(
                g.apagado(n, t) or (g.nodos[n]["fase"] == "TERMINADO" and g.carrito_termino(n, t))
                for n in vistos)
            if listos:
                t_todo_terminado = t_todo_terminado or t
                if t - t_todo_terminado >= 1.0:   # 1 s mas para que el video muestre la llegada
                    motivo = "todos terminaron"
                    break
            else:
                t_todo_terminado = None
            if t >= args.timeout:
                break
            time.sleep(0.002)  # cede la CPU un instante; el socket ya no bloquea
    except KeyboardInterrupt:
        motivo = "Ctrl+C"
        print("\nInterrumpido con Ctrl+C: guardando salidas...")
    finally:
        sock.close()
    if sal.ultimo is None:
        escena.actualizar(g, t)
        sal.agregar_cuadro(comp.cuadro(t))
    sal.agregar_cuadro(sal.ultimo, veces=args.fps)
    print(f"Fin del modo hardware ({motivo}) a los {t:.1f} s")
    resumen = armar_resumen(g, t, sal, {"motivo_fin": motivo, "puerto_udp": args.puerto,
                                        "nota_parametros": "rho se toma de --rho; debe ser el mismo "
                                                           "del firmware para reconstruir bien la feromona"})
    sal.cerrar(resumen)
    vivo.escribir(g, t, sal.cuadros, terminado=True)
    imprimir_final(resumen, sal)
    return 0


def imprimir_final(resumen: dict, sal: Salidas) -> None:
    print(f"Ruta optima (BFS): {resumen['longitud_optima_m']} m")
    for n, d in resumen["por_nodo"].items():
        L = f"{d['longitud_m']:.2f} m" if d["longitud_m"] is not None else "--"
        print(f"  nodo {n}: {L}  fase {d['fase_final']}{'  (apagado)' if d['apagado_al_final'] else ''}")
    print(f"Convergio (camino de maxima feromona = optimo): {'si' if resumen['convergio'] else 'no'}")
    print(f"Salidas en {sal.carpeta}:")
    for ruta in (sal.ruta_mp4, sal.ruta_png, sal.ruta_jsonl, sal.ruta_json):
        print(f"  {os.path.basename(ruta)}  ({os.path.getsize(ruta) / 1024:.0f} KB)")


# ---------------------------------------------------------------------------------------------
def main() -> int:
    defecto = aco.Parametros()
    ap = argparse.ArgumentParser(description="Gemelo digital (PyBullet, sin pantalla) del enjambre ACO")
    ap.add_argument("--modo", choices=("hardware", "sin-hardware"), default="hardware")
    ap.add_argument("--maze", default="maze.json", help="laberinto (relativo a esta carpeta si no existe en la actual)")
    for nombre, tipo in (("alfa", float), ("beta", float), ("rho", float), ("q", float),
                         ("hormigas", int), ("iteraciones", int), ("semilla", int)):
        ap.add_argument(f"--{nombre}", type=tipo, default=getattr(defecto, nombre))
    ap.add_argument("--deposito", choices=("mejor", "todas"), default=defecto.deposito,
                    help="sin-hardware: mejor = solo la mejor hormiga de cada nodo deposita")
    ap.add_argument("--apagar-nodo", type=int, choices=NODOS, default=None,
                    help="prueba 14: este nodo deja de existir (solo sin-hardware)")
    ap.add_argument("--en-iteracion", type=int, default=10,
                    help="iteracion K: el ultimo FIN del nodo apagado es el de la iteracion K")
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--timeout", type=float, default=240.0, help="segundos maximos en modo hardware")
    ap.add_argument("--puerto", type=int, default=protocolo.PUERTO_TELEMETRIA)
    ap.add_argument("--salida", default=os.environ.get("RESULTADOS", os.path.join(AQUI, "resultados")))
    args = ap.parse_args()

    # "docker stop" (y Ctrl+C sobre "docker compose up") manda SIGTERM, no SIGINT: se convierte en
    # el mismo KeyboardInterrupt de Ctrl+C para que el gemelo alcance a guardar sus salidas.
    def _terminar(_sig, _frame):
        raise KeyboardInterrupt
    try:
        signal.signal(signal.SIGTERM, _terminar)
    except (ValueError, OSError):
        pass

    ruta_maze = args.maze if os.path.exists(args.maze) else os.path.join(AQUI, args.maze)
    lab = aco.cargar_laberinto(ruta_maze)
    params = aco.Parametros(alfa=args.alfa, beta=args.beta, rho=args.rho, q=args.q,
                            hormigas=args.hormigas, iteraciones=args.iteraciones, semilla=args.semilla,
                            deposito=args.deposito)
    print(f"Laberinto {lab.nombre} ({lab.columnas}x{lab.filas}), {len(lab.aristas)} aristas, CRC {lab.crc():08X}")
    try:
        if args.modo == "sin-hardware":
            return correr_sin_hardware(args, lab, params)
        return correr_hardware(args, lab, params)
    finally:
        if p.isConnected():
            p.disconnect()


if __name__ == "__main__":
    sys.exit(main())
