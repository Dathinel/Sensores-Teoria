"""
protocolo.py - Mensajes UDP del enjambre (los mismos que arma y lee el firmware).

Todos los mensajes son texto ASCII, campos separados por punto y coma, una linea por mensaje.
Un datagrama UDP puede llevar varias lineas separadas por salto de linea (asi un nodo manda
todos sus depositos de una iteracion en uno o dos paquetes, y no en treinta).

Entre nodos (UDP 4210, unicast a la IP fija de cada companero):
  HELLO;nodo;crc;iter;fase                    presencia, cada segundo
  PHER;nodo;iter;origen;destino;deposito      feromona depositada en la arista origen-destino
  FIN;nodo;iter;n_pher;exitosas;descartadas   cierra la iteracion: cuantos PHER mando
  PATH;nodo;longitud;c0,c1,...,cn             mejor ruta del nodo (longitud en metros)
  TAU;nodo;iter;t0,t1,...                     feromona completa, para un nodo que se reinicio
  PING;origen;seq;t_us  /  PONG;origen;seq;t_us;rssi   prueba de latencia ida y vuelta

Del nodo al computador (UDP 4211 a 192.168.4.100): copia de HELLO, PHER, FIN y PATH, y ademas
  ESTADO;nodo;fase;iter;mejor_long;celda;rssi;vivos;uptime_ms   cada segundo
  RTT;nodo;destino;enviados;recibidos;min_ms;prom_ms;max_ms;p95_ms;rssi
  LOG;nodo;texto

Del computador al nodo (UDP 4210):
  CMD;INICIAR                      arranca la busqueda aunque falte algun nodo
  CMD;RTT;destino;n;intervalo_ms   el nodo hace n PING a 'destino' y reporta RTT
  CMD;REINICIAR                    el nodo se reinicia (prueba 5)

HELLO, PHER y PATH son los del enunciado. FIN, TAU, PING/PONG, ESTADO, RTT, LOG y CMD se
agregaron: FIN para saber que llegaron TODOS los depositos de una iteracion, TAU para que un nodo
reiniciado retome la memoria comun, y los demas para las pruebas y la telemetria.
"""

from __future__ import annotations

import math

import aco

# ---------------------------------------------------------------------------------------------
# Red (iguales a firmware/esp32_aco_nodo/config.h)
# ---------------------------------------------------------------------------------------------
SSID = "ENJAMBRE_ACO"
CLAVE = "hormigas123"
IP_NODO = {1: "192.168.4.1", 2: "192.168.4.2", 3: "192.168.4.3"}
IP_PC = "192.168.4.100"
PUERTO_NODOS = 4210
PUERTO_TELEMETRIA = 4211
MAX_DATAGRAMA = 1200  # bytes: por debajo de la MTU de WiFi (1500) para que nunca se fragmente

# Tiempos (iguales en el firmware, para que el gemelo se mueva al ritmo de los carritos)
PERIODO_HELLO_S = 1.0
PERIODO_ESTADO_S = 1.0
VIVO_S = 4.0              # un nodo del que no se oye nada en 4 s se da por apagado
BARRERA_S = 3.0           # cuanto se espera el FIN de los demas antes de seguir sin ellos
PAUSA_ITER_S = 0.3        # pausa entre iteraciones (para que se vea en el gemelo)
T_CELDA_S = 1.0           # el carrito avanza una celda (20 cm) en 1 s
T_GIRO90_S = 0.6          # y gira 90 grados en 0,6 s
ESCALON_RECORRIDO_S = 8.0  # el carrito n arranca (n-1)*8 s despues, para no chocar

FASES = ("ESPERA", "BUSQUEDA", "RECORRIDO", "TERMINADO")


# ---------------------------------------------------------------------------------------------
# Armar mensajes
# ---------------------------------------------------------------------------------------------
def num(x: float) -> str:
    """Double con 17 cifras significativas: es lo minimo que garantiza que al leerlo de vuelta
    (strtod en el ESP32, float() en Python) se recupere EXACTAMENTE el mismo numero. Con menos
    cifras las copias de la feromona de cada nodo se irian separando en el ultimo bit."""
    return format(x, ".17g")


def hello(nodo, crc, it, fase):
    return f"HELLO;{nodo};{crc:08X};{it};{fase}"


def pher(nodo, it, origen, destino, deposito):
    return f"PHER;{nodo};{it};{origen};{destino};{num(deposito)}"


def fin(nodo, it, n_pher, exitosas, descartadas):
    return f"FIN;{nodo};{it};{n_pher};{exitosas};{descartadas}"


def path(nodo, longitud, camino):
    lon = -1.0 if (longitud is None or math.isinf(longitud)) else longitud
    return f"PATH;{nodo};{lon:.3f};{','.join(str(c) for c in (camino or []))}"


def tau(nodo, it, valores):
    return f"TAU;{nodo};{it};{','.join(num(v) for v in valores)}"


def estado(nodo, fase, it, mejor, celda, rssi, vivos, uptime_ms):
    m = -1.0 if (mejor is None or math.isinf(mejor)) else mejor
    return (f"ESTADO;{nodo};{fase};{it};{m:.3f};{celda};{rssi};"
            f"{','.join(str(v) for v in sorted(vivos))};{int(uptime_ms)}")


def empaquetar(lineas, maximo=MAX_DATAGRAMA):
    """Junta lineas en datagramas de hasta 'maximo' bytes (sin partir ninguna linea)."""
    paquetes, actual = [], ""
    for ln in lineas:
        candidato = ln if not actual else actual + "\n" + ln
        if len(candidato.encode()) > maximo and actual:
            paquetes.append(actual)
            actual = ln
        else:
            actual = candidato
    if actual:
        paquetes.append(actual)
    return paquetes


# ---------------------------------------------------------------------------------------------
# Leer mensajes
# ---------------------------------------------------------------------------------------------
def leer(linea: str) -> dict | None:
    """Convierte una linea en un dict con 'tipo' y sus campos. Devuelve None si no se entiende
    (en vez de lanzar una excepcion: un paquete raro en la red no debe tumbar al gemelo)."""
    try:
        c = linea.strip().split(";")
        t = c[0]
        if t == "HELLO":
            return {"tipo": t, "nodo": int(c[1]), "crc": int(c[2], 16), "iter": int(c[3]),
                    "fase": c[4] if len(c) > 4 else "?"}
        if t == "PHER":
            return {"tipo": t, "nodo": int(c[1]), "iter": int(c[2]), "origen": int(c[3]),
                    "destino": int(c[4]), "deposito": float(c[5])}
        if t == "FIN":
            return {"tipo": t, "nodo": int(c[1]), "iter": int(c[2]), "n_pher": int(c[3]),
                    "exitosas": int(c[4]), "descartadas": int(c[5])}
        if t == "PATH":
            camino = [int(x) for x in c[3].split(",") if x != ""]
            lon = float(c[2])
            return {"tipo": t, "nodo": int(c[1]), "longitud": None if lon < 0 else lon,
                    "camino": camino}
        if t == "TAU":
            return {"tipo": t, "nodo": int(c[1]), "iter": int(c[2]),
                    "tau": [float(x) for x in c[3].split(",") if x != ""]}
        if t == "ESTADO":
            m = float(c[4])
            return {"tipo": t, "nodo": int(c[1]), "fase": c[2], "iter": int(c[3]),
                    "mejor": None if m < 0 else m, "celda": int(c[5]), "rssi": int(c[6]),
                    "vivos": [int(x) for x in c[7].split(",") if x != ""],
                    "uptime_ms": int(c[8])}
        if t == "RTT":
            return {"tipo": t, "nodo": int(c[1]), "destino": int(c[2]), "enviados": int(c[3]),
                    "recibidos": int(c[4]), "min_ms": float(c[5]), "prom_ms": float(c[6]),
                    "max_ms": float(c[7]), "p95_ms": float(c[8]), "rssi": int(c[9])}
        if t in ("PING", "PONG"):
            d = {"tipo": t, "origen": int(c[1]), "seq": int(c[2]), "t_us": int(c[3])}
            if t == "PONG" and len(c) > 4:
                d["rssi"] = int(c[4])
            return d
        if t == "LOG":
            return {"tipo": t, "nodo": int(c[1]), "texto": ";".join(c[2:])}
        if t == "CMD":
            return {"tipo": t, "orden": c[1], "args": c[2:]}
    except (IndexError, ValueError):
        return None
    return None


def leer_datagrama(datos: bytes) -> list:
    """Un datagrama puede traer varias lineas: devuelve la lista de mensajes que se entendieron."""
    salida = []
    for ln in datos.decode("ascii", errors="replace").splitlines():
        m = leer(ln)
        if m is not None:
            salida.append(m)
    return salida


# ---------------------------------------------------------------------------------------------
# Flujo de telemetria simulado (modo sin hardware)
# ---------------------------------------------------------------------------------------------
def tiempo_recorrido(lab, camino) -> list:
    """Instantes (s, desde que arranca) en que el carrito llega a cada celda del camino, con los
    mismos tiempos que usa el firmware para mover los motores: T_CELDA_S por celda y T_GIRO90_S
    por cada giro de 90 grados (180 grados = dos giros). Arranca mirando hacia +x."""
    t, tiempos = 0.0, [0.0]
    rumbo = (1, 0)
    for a, b in zip(camino, camino[1:]):
        ax, ay = lab.celda(a)
        bx, by = lab.celda(b)
        nuevo = (bx - ax, by - ay)
        if nuevo != rumbo:
            giros = 2 if (nuevo[0] == -rumbo[0] and nuevo[1] == -rumbo[1]) else 1
            t += giros * T_GIRO90_S
            rumbo = nuevo
        t += T_CELDA_S
        tiempos.append(t)
    return tiempos


def flujo_simulado(lab, params, nodos=(1, 2, 3), caidas=None, t_iter=None):
    """Genera, sin hardware, la misma secuencia de lineas de telemetria que mandarian los tres
    ESP32 al puerto 4211, con su instante en segundos: lista de (t, linea).

    Corre aco.simular_enjambre (la misma logica del firmware) y la 'narra' como lo haria la red:
    HELLO al arrancar, PHER y FIN de cada nodo vivo en cada iteracion, PATH cuando mejora,
    ESTADO cada segundo, y al terminar la busqueda el recorrido de cada carrito escalonado.
    caidas = {nodo: iteracion} apaga ese nodo desde esa iteracion (prueba 14)."""
    caidas = caidas or {}
    t_iter = PAUSA_ITER_S if t_iter is None else t_iter
    crc = lab.crc()
    eventos = []
    t0 = 1.0  # primer segundo: los nodos se anuncian
    for n in nodos:
        eventos.append((0.0, hello(n, crc, 0, "ESPERA")))
    mejor_previo = {n: math.inf for n in nodos}
    fin_busqueda = {}
    estado_iter = {n: (0, math.inf) for n in nodos}
    marcas = []  # (t, {nodo: (iter, mejor)}) para armar los ESTADO

    def al_iterar(k, info):
        t = t0 + k * t_iter
        for n in info["vivos"]:
            d = info["por_nodo"][n]
            lineas = [pher(n, k, o, de, v) for _, (o, de, v) in sorted(d["depositos"].items())]
            lineas.append(fin(n, k, len(lineas), d["exitosas"], d["descartadas"]))
            for ln in lineas:
                eventos.append((t, ln))
            if d["mejor_longitud"] < mejor_previo[n] - 1e-12:
                mejor_previo[n] = d["mejor_longitud"]
                eventos.append((t, path(n, d["mejor_longitud"], d["mejor_camino"])))
            estado_iter[n] = (k, d["mejor_longitud"])
        marcas.append((t, dict(estado_iter)))

    r = aco.simular_enjambre(lab, params, nodos=nodos, caidas=caidas, al_iterar=al_iterar)
    t_fin_busqueda = t0 + params.iteraciones * t_iter
    # Recorrido de cada carrito vivo por SU mejor ruta, escalonado para que no choquen.
    recorridos = {}
    for n in nodos:
        if caidas.get(n, math.inf) <= params.iteraciones:
            continue
        camino = r["por_nodo"][n]["mejor_camino"]
        if not camino:
            continue
        inicio = t_fin_busqueda + (n - 1) * ESCALON_RECORRIDO_S
        recorridos[n] = (inicio, camino, tiempo_recorrido(lab, camino))
        fin_busqueda[n] = inicio + recorridos[n][2][-1]
    t_total = max(fin_busqueda.values(), default=t_fin_busqueda) + 2.0

    # ESTADO de cada nodo vivo cada segundo.
    s = 0.0
    while s <= t_total:
        ultimo = {n: (0, math.inf) for n in nodos}
        for tm, est in marcas:
            if tm <= s:
                ultimo = est
        def apagado(m):
            return m in caidas and s >= t0 + caidas[m] * t_iter

        for n in nodos:
            if apagado(n):
                continue  # apagado: ya no manda nada
            it, mejor = ultimo[n]
            celda, fase = lab.inicio, ("ESPERA" if s < t0 else "BUSQUEDA")
            if s >= t_fin_busqueda:
                fase = "RECORRIDO"
                if n in recorridos:
                    ini, cam, tiempos = recorridos[n]
                    pasos = [c for c, tc in zip(cam, tiempos) if ini + tc <= s]
                    celda = pasos[-1] if pasos else lab.inicio
                    if s >= ini + tiempos[-1]:
                        fase = "TERMINADO"
            vivos = [m for m in nodos if not apagado(m)]
            eventos.append((s, estado(n, fase, it, mejor, celda, -50, vivos, s * 1000)))
        s += PERIODO_ESTADO_S
    eventos.sort(key=lambda e: e[0])
    return eventos, r
