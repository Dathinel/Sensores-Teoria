"""
herramientas_red.py - Pruebas de red del enjambre desde el PC (con los ESP32 reales o con el
emulador).

Escucha la telemetria que mandan los nodos al puerto UDP 4211 y les manda comandos (CMD) al 4210.
Subcomandos:

    python herramientas_red.py escuchar [--segundos S]
        tabla viva por nodo (fase, iteracion, mejor ruta, RSSI, vivos, ultimo mensaje crudo) y todo
        lo recibido guardado en un .jsonl (una linea JSON por mensaje)
    python herramientas_red.py rtt --origen 1 --destino 2 --n 100 --intervalo-ms 50 --distancia "1 m"
        le pide al nodo origen que haga n PING al destino; guarda el resultado en un JSON y deja la
        fila lista para pegar en la tabla de la prueba
    python herramientas_red.py asociacion [--segundos 20]
        prueba 1: aparecieron los nodos 1, 2 y 3? desde que IP? con que RSSI?
    python herramientas_red.py reinicio --nodo 2
        prueba 5: manda CMD;REINICIAR y mide cuanto tarda en volver a aparecer y a seguir buscando
    python herramientas_red.py iniciar
        manda CMD;INICIAR a los tres (arranca la busqueda aunque falte alguno)

Por defecto los nodos estan en 192.168.4.N puerto 4210 (los ESP32 reales; el PC debe estar
conectado a la red ENJAMBRE_ACO con la IP 192.168.4.100). Con --local se usa el mapa de puertos
del emulador (127.0.0.1:4220/4230/4240). Los archivos que salen con --local llevan el prefijo
'emulador_' y los de la red real 'esp32_', para no confundir nunca una medicion de hardware con
una del emulador.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import socket
import sys
import time

import protocolo as pr

AQUI = os.path.dirname(os.path.abspath(__file__))
CARPETA_RESULTADOS = os.path.join(AQUI, "pruebas", "resultados")
NODOS = (1, 2, 3)


# ---------------------------------------------------------------------------------------------
# Direcciones y archivos
# ---------------------------------------------------------------------------------------------
def direcciones(args):
    """nodo -> (ip, puerto) al que se le mandan los CMD."""
    if args.local:
        # Mismo mapa que emulador_nodos.mapa_por_defecto (4210 + 10*nodo en 127.0.0.1).
        return {n: ("127.0.0.1", pr.PUERTO_NODOS + 10 * n) for n in NODOS}
    return {n: (pr.IP_NODO[n], args.puerto) for n in NODOS}


def prefijo(args):
    return "emulador_" if args.local else "esp32_"


def ruta_salida(args, nombre, extension):
    os.makedirs(CARPETA_RESULTADOS, exist_ok=True)
    fecha = time.strftime("%Y%m%d_%H%M%S")
    return os.path.join(CARPETA_RESULTADOS, f"{prefijo(args)}{nombre}_{fecha}.{extension}")


def guardar_json(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"Guardado en {os.path.relpath(ruta, AQUI)}")


def origen_texto(args):
    return ("EMULADOR (emulador_nodos.py en 127.0.0.1): NO es una medicion de hardware"
            if args.local else "ESP32 reales (red ENJAMBRE_ACO)")


# ---------------------------------------------------------------------------------------------
# Socket del PC
# ---------------------------------------------------------------------------------------------
class Escucha:
    """Socket UDP del PC: recibe la telemetria en el 4211 y manda los CMD desde ese mismo
    socket (el nodo contesta a la telemetria igual, no a la direccion de origen)."""

    def __init__(self, args):
        # Con --local se escucha solo en 127.0.0.1: no hace falta abrir el puerto a la red (y
        # Windows no pregunta por el firewall). Con los ESP32 hay que oir la interfaz WiFi.
        ip = "127.0.0.1" if args.local else ""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((ip, args.puerto_pc))
        except OSError as e:
            raise SystemExit(f"No se pudo abrir el puerto UDP {args.puerto_pc} ({e}). Hay otro "
                             f"programa escuchando (gemelo, otra herramienta)?")
        self.sock.settimeout(0.1)
        self.t0 = time.monotonic()

    def mandar(self, texto, destino):
        try:
            self.sock.sendto(texto.encode("ascii"), destino)
        except OSError as e:
            print(f"  (no se pudo mandar a {destino}: {e})")

    def recibir(self, espera=0.1):
        """Devuelve [(t, ip, puerto, linea_cruda, mensaje_leido)] de un datagrama, o [] si no
        llego nada en 'espera' segundos. t son segundos desde que se abrio la escucha."""
        self.sock.settimeout(espera)
        try:
            datos, (ip, puerto) = self.sock.recvfrom(4096)
        except socket.timeout:
            return []
        except ConnectionResetError:
            # Windows: un CMD mandado a un puerto cerrado vuelve como ICMP y aparece aqui. No es
            # un datagrama recibido; se ignora.
            return []
        t = time.monotonic() - self.t0
        salida = []
        for linea in datos.decode("ascii", errors="replace").splitlines():
            if linea.strip():
                salida.append((t, ip, puerto, linea.strip(), pr.leer(linea)))
        return salida

    def ahora(self):
        return time.monotonic() - self.t0


def nodo_de(msg):
    """Numero de nodo que manda un mensaje de telemetria (None si no aplica)."""
    if msg is None:
        return None
    return msg.get("nodo")


# ---------------------------------------------------------------------------------------------
# escuchar
# ---------------------------------------------------------------------------------------------
def cmd_escuchar(args):
    esc = Escucha(args)
    ruta = args.salida or ruta_salida(args, "escucha", "jsonl")
    os.makedirs(os.path.dirname(os.path.abspath(ruta)), exist_ok=True)
    tabla = {n: {} for n in NODOS}
    contador = 0
    en_terminal = sys.stdout.isatty()
    if en_terminal and os.name == "nt":
        os.system("")  # activa las secuencias ANSI en la consola de Windows (para limpiar)
    proximo = 0.0
    print(f"Escuchando UDP {args.puerto_pc} ({origen_texto(args)}). Ctrl+C para terminar.")
    with open(ruta, "w", encoding="utf-8") as f:
        try:
            while args.segundos is None or esc.ahora() < args.segundos:
                for t, ip, puerto, linea, msg in esc.recibir(0.1):
                    contador += 1
                    f.write(json.dumps({"t": round(t, 4), "fecha": time.strftime("%H:%M:%S"),
                                        "ip": ip, "puerto": puerto, "linea": linea,
                                        "msg": msg}, ensure_ascii=False) + "\n")
                    n = nodo_de(msg)
                    if n in tabla:
                        fila = tabla[n]
                        fila["ip"] = ip
                        fila["crudo"] = linea
                        fila["t"] = t
                        if msg["tipo"] == "ESTADO":
                            fila.update(fase=msg["fase"], iter=msg["iter"], mejor=msg["mejor"],
                                        rssi=msg["rssi"], vivos=msg["vivos"], celda=msg["celda"])
                        elif msg["tipo"] == "HELLO":
                            fila.update(fase=msg["fase"], iter=msg["iter"])
                # Refresco de la tabla: rapido en una terminal, cada 5 s si la salida va a un
                # archivo (si no, el archivo se llenaria de tablas repetidas).
                if esc.ahora() >= proximo:
                    proximo = esc.ahora() + (0.5 if en_terminal else 5.0)
                    imprimir_tabla(tabla, esc.ahora(), contador, en_terminal)
        except KeyboardInterrupt:
            pass
    imprimir_tabla(tabla, esc.ahora(), contador, False)
    print(f"{contador} mensajes guardados en {os.path.relpath(ruta, AQUI)}")


def imprimir_tabla(tabla, t, contador, limpiar):
    if limpiar:
        print("\x1b[H\x1b[2J", end="")
    print(f"t = {t:6.1f} s   mensajes: {contador}")
    print(f"{'nodo':<5}{'ip':<16}{'fase':<11}{'iter':>5}{'mejor':>8}{'rssi':>6}  "
          f"{'vivos':<7}{'hace':>6}  ultimo mensaje")
    for n in NODOS:
        f = tabla[n]
        if not f:
            print(f"{n:<5}(sin datos)")
            continue
        mejor = f"{f['mejor']:.3f}" if f.get("mejor") is not None else "-"
        vivos = ",".join(map(str, f.get("vivos", []))) or "-"
        crudo = f["crudo"] if len(f["crudo"]) <= 60 else f["crudo"][:57] + "..."
        print(f"{n:<5}{f['ip']:<16}{f.get('fase', '?'):<11}{f.get('iter', '-'):>5}{mejor:>8}"
              f"{f.get('rssi', '-'):>6}  {vivos:<7}{t - f['t']:>5.1f}s  {crudo}")
    print(flush=True)


# ---------------------------------------------------------------------------------------------
# rtt
# ---------------------------------------------------------------------------------------------
def cmd_rtt(args):
    esc = Escucha(args)
    dirs = direcciones(args)
    destino_cmd = (args.ip_origen or dirs[args.origen][0], args.puerto_origen or dirs[args.origen][1])
    orden = f"CMD;RTT;{args.destino};{args.n};{args.intervalo_ms}"
    # El nodo tarda n*intervalo en mandar los PING y luego espera los ultimos PONG ~1 s.
    limite = args.n * args.intervalo_ms / 1000.0 + args.margen
    print(f"Mandando {orden} al nodo {args.origen} en {destino_cmd[0]}:{destino_cmd[1]} "
          f"(espera hasta {limite:.0f} s)")
    t_cmd = esc.ahora()
    esc.mandar(orden, destino_cmd)
    resultado, rssi_estado = None, None
    while esc.ahora() - t_cmd < limite and resultado is None:
        for t, ip, puerto, linea, msg in esc.recibir(0.2):
            if not msg:
                continue
            if msg["tipo"] == "ESTADO" and msg["nodo"] == args.origen:
                rssi_estado = msg["rssi"]
            if (msg["tipo"] == "RTT" and msg["nodo"] == args.origen
                    and msg["destino"] == args.destino):
                resultado = dict(msg, linea=linea, ip=ip)
    if resultado is None:
        raise SystemExit(f"No llego la linea RTT del nodo {args.origen} en {limite:.0f} s.")

    env, rec = resultado["enviados"], resultado["recibidos"]
    perdida = 100.0 * (env - rec) / env if env else math.nan
    datos = {
        "origen_de_los_datos": origen_texto(args),
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "distancia": args.distancia,
        "nodo_origen": args.origen,
        "nodo_destino": args.destino,
        "n_pedidos": args.n,
        "intervalo_ms": args.intervalo_ms,
        "enviados": env,
        "recibidos": rec,
        "perdida_pct": perdida,
        "rtt_min_ms": resultado["min_ms"],
        "rtt_prom_ms": resultado["prom_ms"],
        "rtt_max_ms": resultado["max_ms"],
        "rtt_p95_ms": resultado["p95_ms"],
        "rssi_dbm": resultado["rssi"],
        "rssi_ultimo_estado_dbm": rssi_estado,
        "linea_cruda": resultado["linea"],
        "duracion_s": round(esc.ahora() - t_cmd, 3),
    }
    etiqueta = re.sub(r"[^0-9A-Za-z]+", "", args.distancia) or "sin_distancia"
    guardar_json(ruta_salida(args, f"rtt_{args.origen}a{args.destino}_{etiqueta}", "json"), datos)
    print("\nFila para la tabla de la prueba:")
    print("| Distancia | Enviados | Recibidos | Perdida | RTT min (ms) | RTT prom (ms) | "
          "RTT max (ms) | RTT p95 (ms) | RSSI (dBm) |")
    print(f"| {args.distancia} | {env} | {rec} | {perdida:.1f} % | {resultado['min_ms']:.3f} | "
          f"{resultado['prom_ms']:.3f} | {resultado['max_ms']:.3f} | {resultado['p95_ms']:.3f} | "
          f"{resultado['rssi']} |")
    if args.local:
        print("(Medido contra el EMULADOR por 127.0.0.1: no representa la latencia del WiFi.)")


# ---------------------------------------------------------------------------------------------
# asociacion
# ---------------------------------------------------------------------------------------------
def cmd_asociacion(args):
    esc = Escucha(args)
    dirs = direcciones(args)
    vistos = {n: {} for n in NODOS}
    print(f"Esperando HELLO/ESTADO de los nodos 1, 2 y 3 hasta {args.segundos:.0f} s "
          f"({origen_texto(args)})...")
    while esc.ahora() < args.segundos:
        for t, ip, puerto, linea, msg in esc.recibir(0.2):
            if not msg or msg["tipo"] not in ("HELLO", "ESTADO") or msg["nodo"] not in vistos:
                continue
            v = vistos[msg["nodo"]]
            v.setdefault("primera_vez_s", round(t, 3))
            v["ip"], v["puerto"] = ip, puerto
            if msg["tipo"] == "HELLO":
                v["hello"] = True
                v["crc"] = f"{msg['crc']:08X}"
                v["fase"] = msg["fase"]
            else:
                v["estado"] = True
                v["rssi"] = msg["rssi"]
                v["fase"] = msg["fase"]
        # Se termina antes si ya estan los tres con HELLO (CRC) y ESTADO (RSSI).
        if all(v.get("hello") and v.get("estado") for v in vistos.values()):
            break

    informe = {}
    print(f"\n{'nodo':<5}{'aparecio':<10}{'ip':<18}{'ip esperada':<18}{'ip ok':<7}{'rssi':>6}"
          f"  {'crc':<9}fase")
    for n in NODOS:
        v = vistos[n]
        ip_esperada = dirs[n][0]
        if v:
            # En la red real el puerto de origen tambien es el 4210; con el emulador cada nodo
            # sale de su propio puerto, asi que ahi se compara ip y puerto.
            ip_ok = v["ip"] == ip_esperada and (not args.local or v["puerto"] == dirs[n][1])
            dire = f"{v['ip']}:{v['puerto']}"
        else:
            ip_ok, dire = False, "-"
        informe[str(n)] = dict(v, aparecio=bool(v), ip_esperada=ip_esperada, ip_ok=ip_ok)
        print(f"{n:<5}{'SI' if v else 'NO':<10}{dire:<18}{ip_esperada:<18}"
              f"{'SI' if ip_ok else 'NO':<7}{str(v.get('rssi', '-')):>6}  "
              f"{v.get('crc', '-'):<9}{v.get('fase', '-')}")
    crcs = {v["crc"] for v in vistos.values() if "crc" in v}
    if len(crcs) > 1:
        print("OJO: los nodos tienen CRC distintos (no tienen el mismo maze.json).")
    datos = {"origen_de_los_datos": origen_texto(args), "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
             "segundos_esperados": round(esc.ahora(), 3), "mismo_crc": len(crcs) <= 1,
             "todos_aparecieron": all(v for v in vistos.values()), "nodos": informe}
    guardar_json(ruta_salida(args, "asociacion", "json"), datos)


# ---------------------------------------------------------------------------------------------
# reinicio
# ---------------------------------------------------------------------------------------------
def cmd_reinicio(args):
    esc = Escucha(args)
    dirs = direcciones(args)
    n = args.nodo
    # Primero se oye un rato para saber en que estaba el nodo antes del reinicio.
    previo = {}
    t_fin = esc.ahora() + args.previo
    while esc.ahora() < t_fin:
        for t, ip, puerto, linea, msg in esc.recibir(0.1):
            if msg and nodo_de(msg) == n and msg["tipo"] in ("ESTADO", "HELLO"):
                previo = {"fase": msg["fase"], "iter": msg["iter"]}
    print(f"Antes del reinicio el nodo {n} estaba en: {previo or '(no se oyo)'}")

    print(f"Mandando CMD;REINICIAR al nodo {n} en {dirs[n][0]}:{dirs[n][1]}")
    t_cmd = esc.ahora()
    esc.mandar("CMD;REINICIAR", dirs[n])
    eventos = []          # todo lo que mando el nodo despues del CMD: (t relativo, linea)
    t_reset = None        # instante estimado del reinicio (llegada del ESTADO - su uptime)
    hellos, busqueda, primer_pher, logs = [], None, None, []
    while esc.ahora() - t_cmd < args.espera:
        for t, ip, puerto, linea, msg in esc.recibir(0.1):
            if not msg or nodo_de(msg) != n:
                continue
            rel = t - t_cmd
            eventos.append((round(rel, 4), linea))
            tipo = msg["tipo"]
            # Un ESTADO cuyo uptime es menor que el tiempo desde el CMD prueba que el nodo
            # arranco de nuevo DESPUES del comando. De ahi sale el instante del reinicio, que
            # separa los HELLO viejos (que venian en camino) de los nuevos.
            if tipo == "ESTADO" and t_reset is None and msg["uptime_ms"] / 1000.0 < rel + 0.05:
                t_reset = rel - msg["uptime_ms"] / 1000.0
            if tipo == "HELLO":
                hellos.append((rel, msg))
            if tipo == "LOG":
                logs.append((round(rel, 4), msg["texto"]))
            if t_reset is not None and rel >= t_reset:
                if busqueda is None and ((tipo in ("HELLO", "ESTADO") and msg["fase"] == "BUSQUEDA")
                                         or tipo in ("PHER", "FIN")):
                    busqueda = (rel, msg.get("iter"))
                if primer_pher is None and tipo in ("PHER", "FIN"):
                    primer_pher = (rel, msg["iter"])
        if busqueda and primer_pher:
            break

    hello_nuevo = None
    if t_reset is not None:
        hello_nuevo = next(((r, m) for r, m in hellos if r >= t_reset), None)
    elif hellos:
        # Sin ESTADO no se puede fechar el reinicio: se toma el primer HELLO en ESPERA/iter 0.
        hello_nuevo = next(((r, m) for r, m in hellos if m["fase"] == "ESPERA"
                            and m["iter"] == 0), None)

    def ms(x):
        return None if x is None else round(x * 1000.0, 1)

    datos = {
        "origen_de_los_datos": origen_texto(args),
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "nodo": n,
        "antes_del_reinicio": previo,
        "reinicio_estimado_ms_tras_cmd": ms(t_reset),
        "primer_hello_ms_tras_cmd": ms(hello_nuevo[0]) if hello_nuevo else None,
        "primer_hello": ({"fase": hello_nuevo[1]["fase"], "iter": hello_nuevo[1]["iter"]}
                         if hello_nuevo else None),
        "vuelve_a_busqueda_ms_tras_cmd": ms(busqueda[0]) if busqueda else None,
        "iteracion_al_volver": busqueda[1] if busqueda else None,
        "primer_pher_fin_ms_tras_cmd": ms(primer_pher[0]) if primer_pher else None,
        "iteracion_del_primer_pher_fin": primer_pher[1] if primer_pher else None,
        "logs_del_nodo": logs,
        "eventos": eventos[:400],
    }
    print(f"\nNodo {n}:")
    print(f"  reinicio (segun uptime)       : {datos['reinicio_estimado_ms_tras_cmd']} ms tras el CMD")
    print(f"  primer HELLO nuevo            : {datos['primer_hello_ms_tras_cmd']} ms  "
          f"{datos['primer_hello'] or ''}")
    print(f"  vuelve a BUSQUEDA             : {datos['vuelve_a_busqueda_ms_tras_cmd']} ms  "
          f"(iteracion {datos['iteracion_al_volver']})")
    print(f"  primer PHER/FIN tras reiniciar: {datos['primer_pher_fin_ms_tras_cmd']} ms  "
          f"(iteracion {datos['iteracion_del_primer_pher_fin']})")
    for r, texto in logs:
        print(f"  LOG {r * 1000:8.1f} ms: {texto}")
    if busqueda is None:
        print("  No volvio a BUSQUEDA en el tiempo de espera (si el enjambre ya termino, el nodo "
              "se queda en ESPERA hasta 30 s y arranca solo).")
    guardar_json(ruta_salida(args, f"reinicio_nodo{n}", "json"), datos)


# ---------------------------------------------------------------------------------------------
# iniciar
# ---------------------------------------------------------------------------------------------
def cmd_iniciar(args):
    esc = Escucha(args)
    for n, dire in direcciones(args).items():
        esc.mandar("CMD;INICIAR", dire)
        print(f"CMD;INICIAR -> nodo {n} ({dire[0]}:{dire[1]})")


# ---------------------------------------------------------------------------------------------
def main():
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument("--local", action="store_true",
                       help="usar el emulador (127.0.0.1, puertos 4220/4230/4240)")
    comun.add_argument("--puerto", type=int, default=pr.PUERTO_NODOS,
                       help="puerto UDP de los nodos reales (4210)")
    comun.add_argument("--puerto-pc", type=int, default=pr.PUERTO_TELEMETRIA,
                       help="puerto donde escucha el PC (4211)")

    ap = argparse.ArgumentParser(description="Pruebas de red del enjambre ACO (ESP32 o emulador)")
    sub = ap.add_subparsers(dest="orden", required=True)

    p = sub.add_parser("escuchar", parents=[comun], help="tabla viva y registro .jsonl")
    p.add_argument("--segundos", type=float, default=None)
    p.add_argument("--salida", default=None, help="archivo .jsonl (por defecto en pruebas/resultados)")
    p.set_defaults(func=cmd_escuchar)

    p = sub.add_parser("rtt", parents=[comun], help="latencia ida y vuelta entre dos nodos")
    p.add_argument("--origen", type=int, choices=NODOS, required=True)
    p.add_argument("--destino", type=int, choices=NODOS, required=True)
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--intervalo-ms", type=int, default=50)
    p.add_argument("--ip-origen", default=None, help="IP del nodo origen (por defecto 192.168.4.N)")
    p.add_argument("--puerto-origen", type=int, default=None,
                   help="puerto del nodo origen (por defecto 4210, o el del emulador con --local)")
    p.add_argument("--distancia", default="sin dato", help='etiqueta, p. ej. "1 m"')
    p.add_argument("--margen", type=float, default=5.0, help="segundos extra de espera")
    p.set_defaults(func=cmd_rtt)

    p = sub.add_parser("asociacion", parents=[comun], help="prueba 1: nodos, IP y RSSI")
    p.add_argument("--segundos", type=float, default=20.0)
    p.set_defaults(func=cmd_asociacion)

    p = sub.add_parser("reinicio", parents=[comun], help="prueba 5: tiempo de reingreso")
    p.add_argument("--nodo", type=int, choices=NODOS, required=True)
    p.add_argument("--espera", type=float, default=60.0, help="segundos maximos tras el CMD")
    p.add_argument("--previo", type=float, default=2.0, help="segundos de escucha antes del CMD")
    p.set_defaults(func=cmd_reinicio)

    p = sub.add_parser("iniciar", parents=[comun], help="CMD;INICIAR a los tres nodos")
    p.set_defaults(func=cmd_iniciar)

    args = ap.parse_args()
    if args.orden == "rtt" and args.origen == args.destino:
        ap.error("--origen y --destino deben ser nodos distintos")
    args.func(args)


if __name__ == "__main__":
    main()
