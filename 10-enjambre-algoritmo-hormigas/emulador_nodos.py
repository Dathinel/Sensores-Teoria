"""
emulador_nodos.py - Los tres ESP32 del enjambre, pero virtuales: tres hilos en el PC que hablan
por UDP de verdad, con los mismos mensajes y las mismas reglas que el firmware.

Para que sirve: probar el protocolo (barrera de FIN, caida de un nodo, reingreso con TAU, PING/PONG,
comandos del PC) y las herramientas de red (herramientas_red.py) sin tener los carritos a la mano.
Lo que mide este emulador NO es una medicion de hardware: la latencia por 127.0.0.1 no tiene nada
que ver con la del WiFi de los ESP32.

Como los tres nodos viven en la misma maquina no pueden usar las IP 192.168.4.1/2/3 ni compartir el
puerto 4210. Por eso cada nodo virtual escucha en 127.0.0.1 en el puerto 4210 + 10*nodo
(4220, 4230, 4240) y le manda a los otros a esos puertos. La telemetria va al PC igual que en los
ESP32: a --pc (127.0.0.1) puerto --puerto-pc (4211), donde escucha herramientas_red.py o el gemelo.

Ejemplos (con el Python global; solo usa la libreria estandar):

    python emulador_nodos.py --semilla 1 --escala-tiempo 0.25 --resumen pruebas/resultados/emulador_semilla_1.json
    python emulador_nodos.py --apagar-nodo 3 --en-iteracion 10 --escala-tiempo 0.25
    python emulador_nodos.py --reiniciar-nodo 2 --en-iteracion 8 --escala-tiempo 0.25
    python emulador_nodos.py --perdida 0.05
    python emulador_nodos.py --reiniciar-nodo-en-recorrido 2 --escala-tiempo 0.25
    python emulador_nodos.py --apagar-ap-en-iteracion 10 --escala-tiempo 0.25

Convencion de iteraciones (importante para comparar con aco.py):
  - En los mensajes (PHER, FIN) la iteracion se cuenta desde 1: la primera que corre el enjambre es
    la 1, igual que en protocolo.flujo_simulado. HELLO/ESTADO/TAU llevan las iteraciones YA
    aplicadas (0 al arrancar).
  - --en-iteracion K usa la misma convencion que caidas={nodo: K} de aco.simular_enjambre: el
    evento ocurre cuando el nodo ya aplico K iteraciones, justo antes de empezar la siguiente
    (la K+1 de los mensajes, la k=K del bucle 'for k in range' de aco.py). Asi la prueba
    '--apagar-nodo 3 --en-iteracion 10' se compara directo con simular_enjambre(caidas={3: 10}).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import select
import socket
import sys
import threading
import time
from dataclasses import asdict

import aco
import protocolo as pr

AQUI = os.path.dirname(os.path.abspath(__file__))
NODOS = (1, 2, 3)

# Valores propios del emulador (el firmware los saca del hardware; aqui se fijan):
RSSI_FIJO = -40            # dBm: no hay radio, se reporta un RSSI fijo de "senal buena"
ARRANQUE_S = 1.0           # silencio tras un reinicio: lo que tarda un ESP32 en volver a tener red
ESPERA_COMPANEROS_S = 2.0  # ver a los otros dos con el mismo CRC durante 2 s antes de arrancar
ESPERA_MAXIMA_S = 30.0     # si en 30 s no aparecen todos, se arranca con los que haya
ESPERA_PONG_S = 1.0        # tras el ultimo PING se esperan los PONG atrasados 1 s (sin escalar)
SIN_RED_MAX_S = 15.0       # sin red (se cayo el AP) se congela la busqueda hasta 15 s; luego solo

# Fases en las que un nodo ya termino de buscar: no se le espera en la barrera ni cuenta para
# arrancar, pero si puede contestar TAU a un companero que vuelve de un reinicio.
FASES_FIN_BUSQUEDA = ("RECORRIDO", "TERMINADO")
FASES_QUE_CONTESTAN_TAU = ("BUSQUEDA", "RECORRIDO", "TERMINADO")


def mapa_por_defecto(ip="127.0.0.1"):
    """Puerto 4210 + 10*nodo para cada nodo virtual (4220, 4230, 4240)."""
    return {n: (ip, pr.PUERTO_NODOS + 10 * n) for n in NODOS}


def leer_mapa(texto: str | None):
    """--mapa '1=127.0.0.1:4220,2=127.0.0.1:4230,3=127.0.0.1:4240' -> {1: (ip, puerto), ...}."""
    if not texto:
        return mapa_por_defecto()
    mapa = {}
    for parte in texto.split(","):
        n, dire = parte.split("=")
        ip, puerto = dire.rsplit(":", 1)
        mapa[int(n)] = (ip.strip(), int(puerto))
    if sorted(mapa) != list(NODOS):
        raise SystemExit("el --mapa debe traer los nodos 1, 2 y 3")
    return mapa


class Tiempos:
    """Todos los tiempos del protocolo multiplicados por la escala (0.25 = cuatro veces mas rapido).
    Se escalan TODOS juntos para que las proporciones se mantengan: si solo se acortara la barrera
    y no el periodo del HELLO, un nodo vivo podria parecer muerto y el resultado cambiaria."""

    def __init__(self, escala: float):
        self.escala = escala
        self.hello = pr.PERIODO_HELLO_S * escala
        self.estado = pr.PERIODO_ESTADO_S * escala
        self.vivo = pr.VIVO_S * escala
        self.barrera = pr.BARRERA_S * escala
        self.pausa = pr.PAUSA_ITER_S * escala
        self.escalon = pr.ESCALON_RECORRIDO_S * escala
        self.arranque = ARRANQUE_S * escala
        self.espera_companeros = ESPERA_COMPANEROS_S * escala
        self.espera_maxima = ESPERA_MAXIMA_S * escala
        self.sin_red_max = SIN_RED_MAX_S * escala


class Fallas:
    """Fallas programadas desde la linea de comandos (una por tipo)."""

    def __init__(self, apagar_nodo=None, apagar_en=None, reiniciar_nodo=None, reiniciar_en=None,
                 reiniciar_recorrido_nodo=None, apagar_ap_en=None):
        self.apagar_nodo, self.apagar_en = apagar_nodo, apagar_en
        self.reiniciar_nodo, self.reiniciar_en = reiniciar_nodo, reiniciar_en
        self.reiniciar_recorrido_nodo = reiniciar_recorrido_nodo
        self.apagar_ap_en = apagar_ap_en
        # El nodo 1 es el punto de acceso WiFi: si se apaga, los nodos 2 y 3 se quedan sin red.
        # Este evento es lo que en el firmware seria WiFi.status() != WL_CONNECTED.
        self.ap_caido = threading.Event()


# ---------------------------------------------------------------------------------------------
# Un ESP32 virtual
# ---------------------------------------------------------------------------------------------
class NodoVirtual(threading.Thread):
    """Un nodo del enjambre en su propio hilo y con su propio socket UDP.

    El bucle de run() imita el loop() del firmware: leer lo que haya llegado, mandar lo periodico
    (HELLO, ESTADO) y avanzar la maquina de estados un paso, sin bloquearse nunca en una espera
    larga. Asi el nodo sigue contestando PING y oyendo HELLO mientras espera la barrera."""

    def __init__(self, nodo, lab, params, mapa, destino_pc, tiempos, fallas, perdida, verboso,
                 consola):
        super().__init__(name=f"nodo{nodo}", daemon=True)
        self.nodo = nodo
        self.lab = lab
        self.params = params
        self.mapa = mapa
        self.otros = [n for n in NODOS if n != nodo]
        # Al reves: (ip, puerto) -> nodo. Sirve para saber de quien viene un datagrama aunque el
        # mensaje no traiga el numero de nodo (PING/PONG), como el firmware lo sabe por la IP.
        self.dir_a_nodo = {dire: n for n, dire in mapa.items()}
        self.destino_pc = destino_pc
        self.T = tiempos
        self.fallas = fallas
        self.perdida = perdida
        self.verboso = verboso
        self.consola = consola
        self.crc = lab.crc()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(mapa[nodo])
        # No bloqueante: se espera con select() unos milisegundos y luego se vacia todo lo que
        # haya (si se leyera un solo datagrama por vuelta, el nodo se iria quedando atras).
        self.sock.setblocking(False)

        # Azar SOLO para la perdida simulada. Es un generador aparte del xorshift del ACO: si se
        # usara el mismo, descartar paquetes cambiaria los caminos de las hormigas.
        self.azar_perdida = random.Random(params.semilla * 1000 + nodo)

        self.detener = threading.Event()
        self.apagado = False          # --apagar-nodo: ya no manda ni recibe nada
        self.apagado_hecho = False
        self.reinicio_hecho = False
        self.reinicios = 0
        # Estadisticas que sobreviven a un reinicio (son del experimento, no del ESP32).
        self.historial = []           # [(iteracion, [nodos cuyos depositos se aplicaron])]
        self.tau_adoptadas = []       # [(iteracion recibida en TAU, nodo que la mando)]
        self.datagramas_recibidos = 0
        self.datagramas_descartados = 0
        self.reinicio_recorrido_hecho = False
        self.t_sin_red = None         # desde cuando no hay red (None = hay red)
        self.solo_sin_red = False     # ya paso SIN_RED_MAX_S: sigue buscando solo
        self.espera_sin_red_s = 0.0   # cuanto estuvo congelado esperando que volviera la red
        self.iteraciones_solo_sin_red = 0
        self.termino_por_tau = False  # volvio de un reinicio con el enjambre ya terminado
        self._reiniciar_estado(silencio=0.0)

    # ------------------------------------------------------------------ estado
    def _reiniciar_estado(self, silencio):
        """Deja el nodo como recien encendido (lo que hace ESP.restart()): feromona inicial,
        generador con la semilla del nodo, sin mejor ruta, fase ESPERA e iteracion 0. Lo unico
        que no se borra son las estadisticas del experimento."""
        ahora = time.monotonic()
        self.aco = aco.NodoACO(self.lab, self.params, self.nodo)
        self.fase = "ESPERA"
        self.sub = None                # dentro de BUSQUEDA: 'calcular', 'barrera' o 'pausa'
        self.t_encendido = ahora       # base del uptime_ms, como millis() del ESP32
        self.silencio_hasta = ahora + silencio
        self.t_red = self.silencio_hasta   # desde aqui cuentan los 30 s de espera maxima
        self.oido = {}                 # nodo -> ultimo instante en que se oyo algo de el
        self.primero_visto = {}        # nodo -> desde cuando se le ve seguido con el mismo CRC
        self.fase_de = {}              # nodo -> ultima fase anunciada en su HELLO
        self.path_de = {}              # nodo -> (longitud, camino) del ultimo PATH recibido
        self.buffer = {}               # iteracion -> nodo -> {'pher': {arista: (o,d,v)}, 'fin': msg}
        self.propios = None            # resultado de iteracion_local de la iteracion en curso
        self.k = 0                     # iteracion en curso (numeracion de los mensajes)
        self.t_barrera = 0.0
        self.t_pausa_fin = 0.0
        self.celda = self.lab.inicio
        self.t_recorrido = 0.0
        self.tiempos_ruta = None
        self.prox_hello = self.silencio_hasta
        self.prox_estado = self.silencio_hasta
        self.rtt = None
        self.tau_enviada_a = {}        # nodo -> instante del ultimo TAU que se le mando
        self.crc_avisado = set()

    def _vivo(self, n, ahora):
        t = self.oido.get(n)
        return t is not None and ahora - t <= self.T.vivo

    def vivos(self, ahora):
        return [self.nodo] + [n for n in self.otros if self._vivo(n, ahora)]

    def _sin_red(self):
        """Los nodos 2 y 3 se conectan al AP del nodo 1: si el AP cayo, no tienen red."""
        return self.nodo != 1 and self.fallas.ap_caido.is_set()

    # ------------------------------------------------------------------ envio
    def _enviar(self, texto, destinos):
        if self._sin_red():
            return  # sin AP no sale nada: ni a los companeros ni al PC
        datos = texto.encode("ascii")
        for d in destinos:
            try:
                self.sock.sendto(datos, d)
            except OSError:
                # En Windows un sendto a un puerto cerrado de 127.0.0.1 puede fallar; en la red
                # real un paquete perdido tampoco detiene al nodo, asi que se ignora.
                pass

    def _a_companeros_y_pc(self, texto):
        self._enviar(texto, [self.mapa[n] for n in self.otros] + [self.destino_pc])

    def _al_pc(self, texto):
        self._enviar(texto, [self.destino_pc])

    def _log(self, texto, consola=True):
        self._al_pc(f"LOG;{self.nodo};{texto}")
        if consola:
            self.consola(f"[nodo {self.nodo}] {texto}")

    # ------------------------------------------------------------------ bucle
    def run(self):
        while not self.detener.is_set():
            self._recibir()
            ahora = time.monotonic()
            if self.apagado or ahora < self.silencio_hasta:
                continue
            self._periodicos(ahora)
            self._paso_fase(ahora)
            self._paso_rtt(ahora)
        self.sock.close()

    def _recibir(self):
        """Espera hasta 5 ms a que llegue algo y luego vacia el socket completo."""
        try:
            listo, _, _ = select.select([self.sock], [], [], 0.005)
        except (OSError, ValueError):
            return
        if not listo:
            return
        for _ in range(500):  # tope por vuelta para no quedarse aqui si llega una avalancha
            try:
                datos, dire = self.sock.recvfrom(4096)
            except BlockingIOError:
                return
            except ConnectionResetError:
                # Windows: un envio anterior a un puerto cerrado (p. ej. nadie escuchando en el
                # 4211) vuelve como ICMP "puerto inalcanzable" y se reporta en el SIGUIENTE
                # recvfrom. No es un error de este datagrama: se sigue leyendo.
                continue
            except OSError:
                return
            ahora = time.monotonic()
            # Desenchufado o arrancando: el datagrama se pierde, como si no hubiera radio.
            if self.apagado or ahora < self.silencio_hasta or self._sin_red():
                continue
            self.datagramas_recibidos += 1
            if self.perdida > 0 and self.azar_perdida.random() < self.perdida:
                self.datagramas_descartados += 1
                continue
            for msg in pr.leer_datagrama(datos):
                self._atender(msg, dire, ahora)
                if self.apagado or time.monotonic() < self.silencio_hasta:
                    break  # un CMD;REINICIAR en medio del datagrama corta el resto

    # ------------------------------------------------------------------ mensajes
    def _atender(self, msg, dire, ahora):
        t = msg["tipo"]
        emisor = self.dir_a_nodo.get(dire)
        if emisor is None and t in ("HELLO", "PHER", "FIN", "PATH", "TAU"):
            emisor = msg["nodo"]
        es_companero = emisor in self.otros
        previo = self.oido.get(emisor) if es_companero else None
        if es_companero:
            self.oido[emisor] = ahora

        if t == "PING":
            # El PONG devuelve origen, seq y t_us tal cual (el que midio es el que pregunto) y
            # agrega el RSSI de quien contesta. Se manda a la direccion de donde vino el PING.
            self._enviar(f"PONG;{msg['origen']};{msg['seq']};{msg['t_us']};{RSSI_FIJO}", [dire])
        elif t == "PONG":
            self._recibir_pong(msg)
        elif t == "CMD":
            self._comando(msg, ahora)
        elif t == "HELLO" and es_companero:
            self._hello(msg, emisor, previo, ahora)
        elif t in ("PHER", "FIN") and es_companero:
            self._pher_fin(msg, emisor)
        elif t == "PATH" and es_companero:
            self.path_de[emisor] = (msg["longitud"], msg["camino"])
        elif t == "TAU" and es_companero:
            self._tau(msg, emisor, ahora)

    def _hello(self, msg, emisor, previo, ahora):
        if msg["crc"] != self.crc:
            # Otro maze.json: no se le cuenta como companero para arrancar.
            self.primero_visto.pop(emisor, None)
            if emisor not in self.crc_avisado:
                self.crc_avisado.add(emisor)
                self._log(f"el nodo {emisor} tiene otro CRC ({msg['crc']:08X} y no {self.crc:08X})")
            return
        # La racha de "lo veo seguido" se corta si estuvo callado mas de VIVO_S.
        if emisor not in self.primero_visto or previo is None or ahora - previo > self.T.vivo:
            self.primero_visto[emisor] = ahora
        self.fase_de[emisor] = msg["fase"]

        # Reingreso: un companero que anuncia ESPERA con iteracion 0 mientras el enjambre ya busca
        # (o ya termino) se reinicio o llego tarde. Le manda la feromona SOLO el vivo de menor id
        # entre los que pueden contestar (BUSQUEDA, RECORRIDO o TERMINADO), para que no le lleguen
        # dos TAU distintos. Con 0 iteraciones aplicadas no hace falta: le bastara con oir el
        # PHER/FIN de la iteracion 1.
        if (self.fase in FASES_QUE_CONTESTAN_TAU and msg["fase"] == "ESPERA"
                and msg["iter"] == 0):
            contestan = [self.nodo] + [n for n in self.otros if n != emisor
                                       and self._vivo(n, ahora)
                                       and self.fase_de.get(n) in FASES_QUE_CONTESTAN_TAU]
            ultimo = self.tau_enviada_a.get(emisor, -math.inf)
            if (min(contestan) == self.nodo and self.aco.iteracion >= 1
                    and ahora - ultimo >= self.T.hello):
                self.tau_enviada_a[emisor] = ahora
                # Si ya termino la busqueda se manda iter = iteraciones: asi el que vuelve sabe
                # que no queda nada por buscar y no arranca una busqueda solo.
                it = (self.params.iteraciones if self.fase in FASES_FIN_BUSQUEDA
                      else self.aco.iteracion)
                self._enviar(pr.tau(self.nodo, it, self.aco.tau), [self.mapa[emisor]])
                self._log(f"manda TAU (iteracion {it}) al nodo {emisor}")

    def _pher_fin(self, msg, emisor):
        it = msg["iter"]
        # Iteraciones ya aplicadas: llegaron tarde y ya no sirven (aplicarlas romperia la
        # igualdad de la feromona entre nodos). Las futuras se guardan para cuando toque.
        if it <= self.aco.iteracion:
            return
        ent = self.buffer.setdefault(it, {}).setdefault(emisor, {"pher": {}, "fin": None})
        if msg["tipo"] == "PHER":
            try:
                e = self.lab.arista_entre(msg["origen"], msg["destino"])
            except KeyError:
                return  # arista que no existe en este laberinto: mensaje invalido
            ent["pher"][e] = (msg["origen"], msg["destino"], msg["deposito"])
        else:
            ent["fin"] = msg
        if self.fase == "ESPERA" and it == 1 and self.aco.iteracion == 0:
            self._empezar_busqueda(f"oyo la iteracion 1 del nodo {emisor}")

    def _tau(self, msg, emisor, ahora):
        if self.fase != "ESPERA" or len(msg["tau"]) != len(self.lab.aristas):
            return
        # Se adopta la memoria comun: la feromona y cuantas iteraciones lleva el enjambre. El
        # generador aleatorio y la mejor ruta propia NO vienen en TAU (son de cada nodo): siguen
        # como quedaron tras el reinicio.
        self.aco.tau = list(msg["tau"])
        self.aco.iteracion = msg["iter"]
        for k in [k for k in self.buffer if k <= msg["iter"]]:
            del self.buffer[k]
        self.tau_adoptadas.append((msg["iter"], emisor))
        if self.aco.iteracion >= self.params.iteraciones:
            # El enjambre ya termino de buscar: este nodo no recorre (los demas ya lo hicieron o
            # lo estan haciendo). Su ruta es la que marca la feromona comun, siguiendo siempre
            # la arista de mas feromona, y se reporta en PATH como cualquier mejora.
            camino = self.aco.camino_codicioso()
            self.aco.mejor_camino = camino
            self.aco.mejor_longitud = self.lab.longitud_camino(camino) if camino else math.inf
            self._a_companeros_y_pc(pr.path(self.nodo, self.aco.mejor_longitud, camino))
            self.fase = "TERMINADO"
            self.sub = None
            self.termino_por_tau = True
            self._log(f"adopta TAU del nodo {emisor} con la busqueda ya terminada: TERMINADO "
                      f"sin recorrer (ruta por maxima feromona, L = "
                      f"{self.aco.mejor_longitud:.3f} m)")
        else:
            self._log(f"adopta TAU del nodo {emisor}: sigue desde la iteracion {msg['iter'] + 1}")
            self._empezar_busqueda("adopto TAU", log=False)

    def _comando(self, msg, ahora):
        orden = msg["orden"]
        if orden == "INICIAR":
            if self.fase == "ESPERA":
                self._empezar_busqueda("CMD;INICIAR")
        elif orden == "REINICIAR":
            self._log("CMD;REINICIAR: reinicio desde cero")
            self._reiniciar()
        elif orden == "RTT":
            try:
                destino, n, intervalo_ms = (int(x) for x in msg["args"][:3])
            except ValueError:
                self._log("CMD;RTT mal formado")
                return
            if destino not in self.mapa or destino == self.nodo or n <= 0:
                self._log(f"CMD;RTT con destino invalido: {destino}")
                return
            self.rtt = {"destino": destino, "n": n, "intervalo": intervalo_ms / 1000.0,
                        "seq": 0, "prox": ahora, "envios": {}, "rtts": [], "t_ultimo": None}
            self._log(f"RTT: {n} PING al nodo {destino} cada {intervalo_ms} ms", consola=False)

    def _reiniciar(self):
        self.reinicios += 1
        self._reiniciar_estado(silencio=self.T.arranque)

    # ------------------------------------------------------------------ periodicos
    def _periodicos(self, ahora):
        if ahora >= self.prox_hello:
            self.prox_hello = ahora + self.T.hello
            self._a_companeros_y_pc(pr.hello(self.nodo, self.crc, self.aco.iteracion, self.fase))
        if ahora >= self.prox_estado:
            self.prox_estado = ahora + self.T.estado
            uptime = (ahora - self.t_encendido) * 1000.0
            self._al_pc(pr.estado(self.nodo, self.fase, self.aco.iteracion,
                                  self.aco.mejor_longitud, self.celda, RSSI_FIJO,
                                  self.vivos(ahora), uptime))

    # ------------------------------------------------------------------ maquina de estados
    def _empezar_busqueda(self, motivo, log=True):
        self.fase = "BUSQUEDA"
        self.sub = "calcular"
        if log:
            self._log(f"empieza la busqueda ({motivo})")

    def _paso_fase(self, ahora):
        if self.fase == "ESPERA":
            # Un companero que ya esta en RECORRIDO/TERMINADO no cuenta para arrancar: arrancar
            # con el seria empezar una busqueda solo cuando el enjambre ya acabo. Ese companero
            # contesta con TAU y este nodo pasa a TERMINADO.
            terminados = [n for n in self.otros if self._vivo(n, ahora)
                          and self.fase_de.get(n) in FASES_FIN_BUSQUEDA]
            listos = all(n in self.primero_visto and self._vivo(n, ahora)
                         and n not in terminados
                         and ahora - self.primero_visto[n] >= self.T.espera_companeros
                         for n in self.otros)
            if listos:
                self._empezar_busqueda("vio a los otros dos con el mismo CRC")
            elif ahora - self.t_red >= self.T.espera_maxima and not terminados:
                self._empezar_busqueda("pasaron 30 s sin todos los companeros")
        elif self.fase == "BUSQUEDA":
            if self._sin_red():
                if self.t_sin_red is None:
                    self.t_sin_red = ahora
                    self.consola(f"[nodo {self.nodo}] SIN RED (se cayo el AP): congela la "
                                 f"busqueda hasta {self.T.sin_red_max:.2f} s")
                if not self.solo_sin_red:
                    # Sin red no se avanza la barrera ni se empieza otra iteracion: si la red
                    # vuelve pronto, el enjambre sigue junto como si nada. Pasado el tope, cada
                    # nodo sigue solo (mejor una ruta propia que un carrito parado para siempre).
                    self.espera_sin_red_s = ahora - self.t_sin_red
                    if self.espera_sin_red_s < self.T.sin_red_max:
                        return
                    self.solo_sin_red = True
                    self.consola(f"[nodo {self.nodo}] {self.espera_sin_red_s:.2f} s sin red: "
                                 f"sigue buscando solo")
            if self.sub == "calcular":
                self._calcular(ahora)
            elif self.sub == "barrera":
                self._barrera(ahora)
            elif self.sub == "pausa" and ahora >= self.t_pausa_fin:
                self.sub = "calcular"
        elif self.fase == "RECORRIDO":
            self._recorrido(ahora)

    def _calcular(self, ahora):
        f = self.fallas
        # Fallas programadas: se revisan justo antes de empezar una iteracion nueva, cuando el
        # nodo ya aplico 'en_iteracion' iteraciones (misma convencion que caidas de aco.py).
        if self.nodo == 1 and f.apagar_ap_en is not None and not self.apagado_hecho \
                and self.aco.iteracion == f.apagar_ap_en:
            self.apagado_hecho = True
            self.apagado = True
            f.ap_caido.set()
            self.consola(f"[nodo 1] SE APAGA EL AP tras aplicar {self.aco.iteracion} "
                         f"iteraciones: los nodos 2 y 3 quedan sin red")
            return
        if f.apagar_nodo == self.nodo and not self.apagado_hecho \
                and self.aco.iteracion == f.apagar_en:
            self.apagado_hecho = True
            self.apagado = True
            self.consola(f"[nodo {self.nodo}] SE DESENCHUFA tras aplicar {self.aco.iteracion} "
                         f"iteraciones (no manda la iteracion {self.aco.iteracion + 1})")
            return
        if f.reiniciar_nodo == self.nodo and not self.reinicio_hecho \
                and self.aco.iteracion == f.reiniciar_en:
            self.reinicio_hecho = True  # una sola vez: tras el TAU podria volver a la misma iteracion
            self.consola(f"[nodo {self.nodo}] SE REINICIA tras aplicar {self.aco.iteracion} "
                         f"iteraciones (como ESP.restart())")
            self._reiniciar()
            return

        self.k = self.aco.iteracion + 1
        antes = self.aco.mejor_longitud
        self.propios = self.aco.iteracion_local()
        # Un PHER por arista tocada, en orden de arista, y al final el FIN con cuantos PHER van:
        # asi el que recibe sabe si se perdio alguno (si no cuadra, no aplica nada de este nodo).
        lineas = [pr.pher(self.nodo, self.k, o, d, v)
                  for _, (o, d, v) in sorted(self.propios["depositos"].items())]
        lineas.append(pr.fin(self.nodo, self.k, len(lineas), self.propios["exitosas"],
                             self.propios["descartadas"]))
        for paquete in pr.empaquetar(lineas):
            self._a_companeros_y_pc(paquete)
        if self.aco.mejor_longitud < antes - 1e-12:
            self._a_companeros_y_pc(pr.path(self.nodo, self.aco.mejor_longitud,
                                            self.aco.mejor_camino))
        self.sub = "barrera"
        self.t_barrera = ahora

    def _barrera(self, ahora):
        k = self.k
        llegados = self.buffer.get(k, {})
        # Solo se espera a los companeros vivos: a uno que no se oye hace VIVO_S no tiene sentido
        # esperarlo (se cayo). A uno vivo se le espera como mucho BARRERA_S.
        # Tampoco se espera a uno que ya esta en RECORRIDO/TERMINADO (ya no manda iteraciones),
        # ni a nadie si no hay red (solo se llega aqui sin red cuando ya se decidio seguir solo).
        esperados = [n for n in self.otros if self._vivo(n, ahora)
                     and self.fase_de.get(n) not in FASES_FIN_BUSQUEDA]
        if self._sin_red():
            esperados = []
        completos = all(llegados.get(n, {}).get("fin") is not None for n in esperados)
        if not completos and ahora - self.t_barrera < self.T.barrera:
            return

        depositos = {self.nodo: self.propios["depositos"]}
        for n in self.otros:
            ent = llegados.get(n)
            if not ent or ent["fin"] is None:
                continue
            if ent["fin"]["n_pher"] == len(ent["pher"]):
                depositos[n] = dict(ent["pher"])
            else:
                self._log(f"iteracion {k}: del nodo {n} llegaron {len(ent['pher'])} de "
                          f"{ent['fin']['n_pher']} PHER, no se aplican", consola=self.verboso)
        # aplicar_iteracion suma en orden de nodo y de arista, sin importar en que orden llegaron
        # los paquetes: por eso todos los nodos quedan con la misma feromona bit a bit.
        self.aco.aplicar_iteracion(depositos)
        for kk in [kk for kk in self.buffer if kk <= k]:
            del self.buffer[kk]
        aplicados = sorted(depositos)
        self.historial.append((k, aplicados))
        if self._sin_red():
            self.iteraciones_solo_sin_red += 1
        if self.verboso or len(aplicados) < len(NODOS):
            faltan = [n for n in NODOS if n not in aplicados]
            extra = f"  (sin el nodo {','.join(map(str, faltan))})" if faltan else ""
            self.consola(f"[nodo {self.nodo}] iteracion {k} aplicada con "
                         f"{','.join(map(str, aplicados))}{extra}")
        if self.aco.iteracion >= self.params.iteraciones:
            self._entrar_recorrido(ahora)
        else:
            self.sub = "pausa"
            self.t_pausa_fin = ahora + self.T.pausa

    def _entrar_recorrido(self, ahora):
        """Fin de la busqueda: el carrito n espera (n-1)*ESCALON_RECORRIDO_S para no chocar con
        los demas y luego recorre su mejor ruta con los tiempos de los motores."""
        f = self.fallas
        if f.reiniciar_recorrido_nodo == self.nodo and not self.reinicio_recorrido_hecho:
            # Prueba del reinicio con el enjambre ya terminado: debe volver con TAU y quedar en
            # TERMINADO sin buscar de nuevo.
            self.reinicio_recorrido_hecho = True
            self.consola(f"[nodo {self.nodo}] SE REINICIA al empezar el recorrido")
            self._reiniciar()
            return
        self.fase = "RECORRIDO"
        self.sub = None
        self.t_recorrido = ahora + (self.nodo - 1) * self.T.escalon
        camino = self.aco.mejor_camino
        self.tiempos_ruta = pr.tiempo_recorrido(self.lab, camino) if camino else None
        self._log(f"fin de la busqueda: L = {self.aco.mejor_longitud:.3f} m, recorre en "
                  f"{(self.nodo - 1) * self.T.escalon:.1f} s")

    def _recorrido(self, ahora):
        camino, tiempos = self.aco.mejor_camino, self.tiempos_ruta
        if not camino:
            self.fase = "TERMINADO"
            self._log("sin ruta para recorrer: TERMINADO")
            return
        if ahora < self.t_recorrido:
            return
        dt = (ahora - self.t_recorrido) / self.T.escala if self.T.escala > 0 else math.inf
        # Celda actual = la ultima a la que ya llego segun los tiempos del motor.
        for c, tc in zip(camino, tiempos):
            if tc <= dt:
                self.celda = c
        if dt >= tiempos[-1]:
            self.celda = camino[-1]
            self.fase = "TERMINADO"
            self._log(f"TERMINADO en la celda {self.celda}")
            # ESTADO inmediato: el PC se entera ya del TERMINADO (un ESP32 real sigue mandando
            # ESTADO cada segundo; el emulador se cierra poco despues y no debe quedar a medias).
            self.prox_estado = 0.0

    # ------------------------------------------------------------------ RTT
    def _paso_rtt(self, ahora):
        r = self.rtt
        if r is None:
            return
        if r["seq"] < r["n"] and ahora >= r["prox"]:
            t_ns = time.perf_counter_ns()
            r["envios"][r["seq"]] = t_ns
            self._enviar(f"PING;{self.nodo};{r['seq']};{t_ns // 1000}", [self.mapa[r["destino"]]])
            r["seq"] += 1
            # prox avanza desde el instante programado (no desde ahora) para que el intervalo
            # medio sea el pedido aunque el bucle se atrase un poco en alguna vuelta.
            r["prox"] += r["intervalo"]
            r["t_ultimo"] = ahora
        elif r["seq"] >= r["n"] and (len(r["rtts"]) >= r["n"]
                                     or ahora - r["t_ultimo"] >= ESPERA_PONG_S):
            self._reportar_rtt()

    def _recibir_pong(self, msg):
        r = self.rtt
        if r is None or msg["origen"] != self.nodo:
            return
        t_envio = r["envios"].pop(msg["seq"], None)  # pop: un PONG duplicado no cuenta dos veces
        if t_envio is not None:
            r["rtts"].append((time.perf_counter_ns() - t_envio) / 1e6)

    def _reportar_rtt(self):
        r, self.rtt = self.rtt, None
        v = sorted(r["rtts"])
        if v:
            # p95 por rango mas cercano: el valor que deja por debajo al 95 % de las muestras.
            p95 = v[max(0, math.ceil(0.95 * len(v)) - 1)]
            mn, prom, mx = v[0], sum(v) / len(v), v[-1]
        else:
            mn = prom = mx = p95 = -1.0  # -1 = sin dato (no volvio ningun PONG)
        linea = (f"RTT;{self.nodo};{r['destino']};{r['seq']};{len(v)};{mn:.3f};{prom:.3f};"
                 f"{mx:.3f};{p95:.3f};{RSSI_FIJO}")
        self._al_pc(linea)
        self.consola(f"[nodo {self.nodo}] {linea}")

    # ------------------------------------------------------------------ resumen
    def resumen(self):
        L = self.aco.mejor_longitud
        sin = [(k, a) for k, a in self.historial if len(a) < len(NODOS)]
        return {
            "fase_final": self.fase,
            "apagado": self.apagado,
            "reinicios": self.reinicios,
            "iteraciones_aplicadas": self.aco.iteracion,
            "aplicaciones_hechas_por_este_nodo": len(self.historial),
            "iteraciones_sin_algun_companero": len(sin),
            "detalle_sin_companero": [{"iteracion": k, "aplicados": a} for k, a in sin],
            "tau_adoptadas": [{"iteracion": i, "de_nodo": n} for i, n in self.tau_adoptadas],
            "termino_por_tau_sin_recorrer": self.termino_por_tau,
            "quedo_sin_red": self.t_sin_red is not None,
            "espera_sin_red_s": round(self.espera_sin_red_s, 3),
            "iteraciones_solo_sin_red": self.iteraciones_solo_sin_red,
            "mejor_camino": self.aco.mejor_camino,
            "mejor_longitud": None if math.isinf(L) else L,
            "celda_final": self.celda,
            "datagramas_recibidos": self.datagramas_recibidos,
            "datagramas_descartados_por_perdida": self.datagramas_descartados,
            "tau_final": list(self.aco.tau),
        }


# ---------------------------------------------------------------------------------------------
# Comparacion con el modelo sincronico de aco.py
# ---------------------------------------------------------------------------------------------
def comparar_con_simulacion(lab, params, nodos_virtuales, caidas):
    """Corre aco.simular_enjambre con la misma semilla y compara, nodo por nodo, la mejor ruta y
    la feromona final con IGUALDAD EXACTA de floats (==, sin tolerancia). Si el protocolo esta
    bien, la red no cambia nada: llegan los mismos depositos y se suman en el mismo orden."""
    ref = aco.simular_enjambre(lab, params, caidas=caidas or None)
    salida, todo_igual = {}, True
    for nv in nodos_virtuales:
        n = nv.nodo
        tau_e, tau_s = nv.aco.tau, ref["tau_final"][n]
        camino_igual = nv.aco.mejor_camino == ref["por_nodo"][n]["mejor_camino"]
        tau_igual = tau_e == tau_s
        dif = max((abs(a - b) for a, b in zip(tau_e, tau_s)), default=0.0)
        salida[str(n)] = {"camino_igual": camino_igual, "tau_igual_exacta": tau_igual,
                          "max_diferencia_tau": dif,
                          "camino_simulacion": ref["por_nodo"][n]["mejor_camino"]}
        todo_igual = todo_igual and camino_igual and tau_igual
    vivos = [nv for nv in nodos_virtuales if not nv.apagado]
    entre_vivos = all(nv.aco.tau == vivos[0].aco.tau for nv in vivos) if vivos else True
    return {"caidas": {str(k): v for k, v in (caidas or {}).items()},
            "identico_a_simular_enjambre": todo_igual,
            "tau_identica_entre_nodos_vivos": entre_vivos,
            "por_nodo": salida}


# ---------------------------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Tres ESP32 virtuales del enjambre ACO hablando por UDP en 127.0.0.1")
    ap.add_argument("--maze", default=aco.MAZE_POR_DEFECTO, help="laberinto (maze.json)")
    base = aco.Parametros()
    for nombre, tipo in (("alfa", float), ("beta", float), ("rho", float), ("q", float),
                         ("hormigas", int), ("iteraciones", int), ("semilla", int),
                         ("tau0", float)):
        ap.add_argument(f"--{nombre}", type=tipo, default=getattr(base, nombre))
    ap.add_argument("--deposito", choices=("mejor", "todas"), default=base.deposito,
                    help="mejor = solo la mejor hormiga de cada nodo deposita (por defecto)")
    ap.add_argument("--pc", default="127.0.0.1", help="IP a la que va la telemetria")
    ap.add_argument("--puerto-pc", type=int, default=pr.PUERTO_TELEMETRIA)
    ap.add_argument("--mapa", default=None,
                    help="direcciones de los nodos, p. ej. '1=127.0.0.1:4220,2=127.0.0.1:4230,"
                         "3=127.0.0.1:4240' (por defecto 4210+10*nodo en 127.0.0.1)")
    ap.add_argument("--apagar-nodo", type=int, choices=NODOS)
    ap.add_argument("--reiniciar-nodo", type=int, choices=NODOS)
    ap.add_argument("--en-iteracion", type=int, action="append", default=[],
                    help="iteraciones ya aplicadas cuando ocurre la falla (una por cada "
                         "--apagar-nodo/--reiniciar-nodo, en ese orden)")
    ap.add_argument("--reiniciar-nodo-en-recorrido", type=int, choices=NODOS,
                    help="ese nodo se reinicia justo al empezar el recorrido (debe volver con "
                         "TAU y quedar en TERMINADO sin buscar)")
    ap.add_argument("--apagar-ap-en-iteracion", type=int, default=None,
                    help="el nodo 1 (AP) desaparece tras aplicar K iteraciones: los nodos 2 y 3 "
                         "quedan sin red (esperan hasta SIN_RED_MAX_S y siguen solos)")
    ap.add_argument("--perdida", type=float, default=0.0,
                    help="fraccion de datagramas recibidos que se descartan al azar (0 a 1)")
    ap.add_argument("--escala-tiempo", type=float, default=1.0,
                    help="multiplica todos los tiempos del protocolo (0.25 = 4 veces mas rapido)")
    ap.add_argument("--resumen", default=None, help="archivo .json con el resumen por nodo")
    ap.add_argument("--timeout", type=float, default=600.0, help="segundos maximos de corrida")
    ap.add_argument("--verboso", action="store_true", help="imprime cada iteracion aplicada")
    args = ap.parse_args()

    # Cada --en-iteracion va con la falla que se pidio, en el orden en que aparecen.
    pedidas = [x for x in ("apagar", "reiniciar") if getattr(args, f"{x}_nodo") is not None]
    if len(args.en_iteracion) != len(pedidas):
        ap.error("pon un --en-iteracion por cada --apagar-nodo / --reiniciar-nodo")
    orden = sorted(pedidas, key=lambda x: sys.argv.index(f"--{x}-nodo"))
    en = dict(zip(orden, args.en_iteracion))
    fallas = Fallas(args.apagar_nodo, en.get("apagar"), args.reiniciar_nodo, en.get("reiniciar"),
                    args.reiniciar_nodo_en_recorrido, args.apagar_ap_en_iteracion)
    if not 0.0 <= args.perdida < 1.0:
        ap.error("--perdida va de 0 a menos de 1")

    params = aco.Parametros(**{k: getattr(args, k) for k in asdict(base)})
    lab = aco.cargar_laberinto(args.maze)
    mapa = leer_mapa(args.mapa)
    tiempos = Tiempos(args.escala_tiempo)
    candado = threading.Lock()
    t0 = time.monotonic()

    def consola(texto):
        # Un candado para que las lineas de los tres hilos no se mezclen a medias.
        with candado:
            print(f"{time.monotonic() - t0:7.2f} s  {texto}", flush=True)

    print(f"Emulador del enjambre: laberinto {lab.nombre}, {len(lab.aristas)} aristas, "
          f"CRC {lab.crc():08X}")
    print(f"Parametros: {params}")
    print(f"Nodos: " + ", ".join(f"{n} -> {ip}:{p}" for n, (ip, p) in mapa.items())
          + f"   telemetria -> {args.pc}:{args.puerto_pc}")
    print(f"Escala de tiempo {args.escala_tiempo}  (barrera {tiempos.barrera:.2f} s, vivo "
          f"{tiempos.vivo:.2f} s, pausa {tiempos.pausa:.3f} s)  perdida {args.perdida:.1%}")

    try:
        nodos = [NodoVirtual(n, lab, params, mapa, (args.pc, args.puerto_pc), tiempos, fallas,
                             args.perdida, args.verboso, consola) for n in NODOS]
    except OSError as e:
        raise SystemExit(f"No se pudo abrir un puerto de nodo ({e}). Hay otro emulador corriendo?")
    for nv in nodos:
        nv.start()

    motivo = "todos los nodos vivos llegaron a TERMINADO"
    try:
        while True:
            time.sleep(0.05)
            activos = [nv for nv in nodos if not nv.apagado]
            if activos and all(nv.fase == "TERMINADO" for nv in activos):
                # Medio segundo mas para que salga el ESTADO final de cada nodo antes de cerrar.
                time.sleep(0.5)
                break
            if time.monotonic() - t0 > args.timeout:
                motivo = f"timeout de {args.timeout:.0f} s"
                break
    except KeyboardInterrupt:
        motivo = "interrumpido con Ctrl+C"
    for nv in nodos:
        nv.detener.set()
    for nv in nodos:
        nv.join(timeout=2.0)
    duracion = time.monotonic() - t0
    print(f"\nFin ({motivo}) en {duracion:.1f} s")

    for nv in nodos:
        r = nv.resumen()
        L = r["mejor_longitud"]
        print(f"  nodo {nv.nodo}: {r['fase_final']:<9} iter {r['iteraciones_aplicadas']:>3}  "
              f"sin companero {r['iteraciones_sin_algun_companero']:>2}  "
              f"L = {('%.3f m' % L) if L is not None else '-':>8}  "
              f"ruta {'-'.join(map(str, r['mejor_camino'] or [])) or '(ninguna)'}"
              + ("  [APAGADO]" if r["apagado"] else "")
              + (f"  [reinicios {r['reinicios']}]" if r["reinicios"] else ""))

    # La comparacion exacta solo tiene sentido si la red no pierde nada y nadie se reinicia: un
    # reinicio cambia el generador aleatorio del nodo y simular_enjambre no modela eso.
    comparacion = None
    # Sin AP los nodos 2 y 3 buscan cada uno por su lado: simular_enjambre tampoco modela eso.
    if (args.perdida == 0 and fallas.reiniciar_nodo is None
            and fallas.reiniciar_recorrido_nodo is None and fallas.apagar_ap_en is None
            and motivo.startswith("todos")):
        caidas = {fallas.apagar_nodo: fallas.apagar_en} if fallas.apagar_nodo else {}
        comparacion = comparar_con_simulacion(lab, params, nodos, caidas)
        print(f"\nComparacion con aco.simular_enjambre(caidas={caidas or None}):")
        for n, c in comparacion["por_nodo"].items():
            print(f"  nodo {n}: ruta igual {'SI' if c['camino_igual'] else 'NO'}, tau igual "
                  f"(exacta) {'SI' if c['tau_igual_exacta'] else 'NO'}  "
                  f"(max dif {c['max_diferencia_tau']:.3g})")
        print(f"  Identico a la simulacion: "
              f"{'SI' if comparacion['identico_a_simular_enjambre'] else 'NO'};  tau identica "
              f"entre nodos vivos: {'SI' if comparacion['tau_identica_entre_nodos_vivos'] else 'NO'}")

    if args.resumen:
        datos = {
            "origen": "EMULADOR (emulador_nodos.py en 127.0.0.1), no es una medicion de hardware",
            "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
            "comando": " ".join(sys.argv),
            "laberinto": lab.nombre,
            "crc": f"{lab.crc():08X}",
            "parametros": asdict(params),
            "escala_tiempo": args.escala_tiempo,
            "perdida": args.perdida,
            "fallas": {"apagar_nodo": fallas.apagar_nodo, "apagar_en_iteracion": fallas.apagar_en,
                       "reiniciar_nodo": fallas.reiniciar_nodo,
                       "reiniciar_en_iteracion": fallas.reiniciar_en,
                       "reiniciar_nodo_en_recorrido": fallas.reiniciar_recorrido_nodo,
                       "apagar_ap_en_iteracion": fallas.apagar_ap_en,
                       "sin_red_max_s_escalado": tiempos.sin_red_max},
            "fin": motivo,
            "duracion_s": round(duracion, 3),
            "nodos": {str(nv.nodo): nv.resumen() for nv in nodos},
            "comparacion": comparacion,
        }
        carpeta = os.path.dirname(os.path.abspath(args.resumen))
        os.makedirs(carpeta, exist_ok=True)
        # json escribe los float con repr(), que se lee de vuelta exacto: la tau del archivo es
        # bit a bit la del nodo.
        with open(args.resumen, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        print(f"\nResumen guardado en {args.resumen}")

    activos = [nv for nv in nodos if not nv.apagado]
    ok = bool(activos) and all(nv.fase == "TERMINADO" for nv in activos)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
