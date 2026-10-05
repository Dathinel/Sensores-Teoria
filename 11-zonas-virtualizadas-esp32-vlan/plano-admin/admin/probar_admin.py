"""Prueba del contenedor admin SIN el resto del stack: hace de "todos los demás" desde Windows.

Antes:
    docker build -f plano-admin/admin/Dockerfile -t t11-admin .
    docker run -d --name t11-admin -p 11883:1883 -p 15300:5300/udp -p 18080:8080 ^
        -v "%CD%\\resultados\\admin-prueba:/app/resultados" t11-admin
Luego (desde la raíz del tema):
    entorno\\Scripts\\python.exe plano-admin\\admin\\probar_admin.py [--captura img\\dashboard-admin.png]

Qué simula y qué comprueba (cada paso imprime lo medido y todo queda en resultados/admin-prueba/):
  1. Latidos HB cada 1 s de los 6 servicios con LED, del track-server y de dos "ESP32" (ctrl-1 y
     esclava), más `lab/vivo/<s>=1` y métricas JSON cada 2 s por MQTT, como harían los contenedores.
     -> los 6 servicios deben quedar OK.
  2. PING -> PONG: 50 ecos por UDP; el PONG debe traer el mismo origen/seq/t_ms. Se mide el RTT.
  3. player-2 deja de latir (y su ping nunca respondió, pues no hay stack) -> CAIDO en ~3 s.
  4. sim-nao late con un retardo aleatorio de 0 a 120 ms antes de cada envío (jitter artificial)
     -> LENTO cuando el jitter RFC 3550 pasa de 10 ms.
  5. sim-spot publica vivo=0 (como su testamento LWT) -> CAIDO de inmediato.
  6. player-2 vuelve con la misma secuencia (como tras un corte de red): las secuencias que faltaron
     cuentan como perdidas -> LENTO por pérdida > 5 % en la ventana de 60 s, aunque ya late.
Los pings ICMP del admin a 192.168.x.x fallan en esta prueba aislada: es lo esperado.
"""

import argparse
import json
import os
import random
import socket
import subprocess
import sys
import threading
import time
import urllib.request

T = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, T)
from comun import protocolo  # noqa: E402

import paho.mqtt.client as mqtt  # noqa: E402

HOST = "127.0.0.1"
HB = (HOST, 15300)
MQTT_PUERTO = 11883
API = "http://127.0.0.1:18080/api/resumen.json"
SALIDA = os.path.join(T, "resultados", "admin-prueba")
CAPTURA_JS = r"D:\cosas uni\Micros\.claude\herramientas\captura-chrome.mjs"


def ms():
    return int(time.monotonic() * 1000)


class Emisor:
    """Un emisor de latidos como el Latido de comun/lab.py, pero que se puede pausar y desordenar."""

    def __init__(self, origen):
        self.origen = origen
        self.seq = 0
        self.activo = True
        self.retardo_max_ms = 0       # jitter artificial: espera aleatoria antes de mandar
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        threading.Thread(target=self._bucle, daemon=True).start()

    def _bucle(self):
        siguiente = time.monotonic()
        while True:
            if self.activo:
                # La marca t_ms se toma ANTES del retardo: así el retardo hace de "cola en la red"
                # (el paquete sale a tiempo según el emisor pero llega tarde), que es lo que mide el
                # jitter RFC 3550. Si se esperara antes de tomar la marca, emisor y receptor verían el
                # mismo desfase y D saldría ~0 (eso sería un emisor lento, no una red con jitter).
                linea = protocolo.armar_latido("HB", self.origen, self.seq, ms()).encode()
                if self.retardo_max_ms:
                    time.sleep(random.uniform(0, self.retardo_max_ms) / 1000)
                self.sock.sendto(linea, HB)
            # La secuencia sube aunque esté pausado: así, al volver, el admin ve el hueco como pérdida
            # (lo mismo que pasa si se corta la red y el contenedor sigue vivo).
            self.seq += 1
            siguiente += 1.0
            time.sleep(max(0.0, siguiente - time.monotonic()))


def resumen():
    with urllib.request.urlopen(API, timeout=3) as r:
        return json.loads(r.read())


def esperar_estado(estados_mqtt, servicio, buscado, limite_s=90):
    """Espera a que llegue lab/estado/<servicio>=buscado por MQTT. Devuelve los segundos que tardó."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < limite_s:
        if estados_mqtt.get(servicio) == buscado:
            return time.monotonic() - t0
        time.sleep(0.05)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--captura", help="ruta del PNG del dashboard (se toma con los tres estados a la vista)")
    args = ap.parse_args()
    os.makedirs(SALIDA, exist_ok=True)
    informe = {}

    # --- MQTT: un cliente por servicio (cada uno con su testamento), y uno que escucha los estados.
    estados_mqtt, retenidos = {}, {}

    def al_msg(c, u, m):
        s = m.topic.split("/")[-1]
        estados_mqtt[s] = m.payload.decode()
        retenidos[s] = m.retain

    obs = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="prueba-observador")
    obs.on_message = al_msg
    obs.connect(HOST, MQTT_PUERTO)
    obs.subscribe("lab/estado/+", qos=1)
    obs.loop_start()

    servicios = ["track-server", "player-1", "player-2", "player-3", "sim-spot", "sim-pepper", "sim-nao"]
    clientes = {}
    for s in servicios:
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"prueba-{s}")
        c.will_set(f"lab/vivo/{s}", "0", qos=1, retain=True)
        c.connect(HOST, MQTT_PUERTO, keepalive=5)
        c.loop_start()
        c.publish(f"lab/vivo/{s}", "1", qos=1, retain=True)
        clientes[s] = c
    emisores = {s: Emisor(s) for s in servicios + ["ctrl-1", "esclava"]}

    parar_met = threading.Event()

    def metricas():
        n = 0
        while not parar_met.is_set():
            n += 1
            for s, c in clientes.items():
                if s.startswith("player"):
                    datos = {"recibidos": 40 * n, "perdidos": 0, "fps_ctrl": 20.0, "lat_esp32_ms": round(random.uniform(3, 6), 1)}
                elif s.startswith("sim"):
                    datos = {"fps_fisica": 240, "recibidos": 40 * n, "perdidos": 0, "j1": round(random.uniform(-30, 30), 1)}
                else:
                    datos = {"fps_fisica": 240, "clientes_ws": 3, "carros": 6}
                c.publish(f"lab/metricas/{s}", json.dumps(dict(datos, servicio=s, t_ms=ms())))
            parar_met.wait(2.0)

    threading.Thread(target=metricas, daemon=True).start()

    # --- 1. Todos OK
    print("1) latidos de todos durante 8 s...")
    time.sleep(8)
    r = resumen()
    ok = {s: r["servicios"][s]["estado"] for s in r["leds"]}
    print("   estados:", ok)
    informe["1_todos_ok"] = {"estados": ok, "retenido": all(retenidos.get(s) is not None for s in ok),
                             "jitter_hb_ms": {s: r["servicios"][s]["hb"]["jitter_ms"] for s in r["leds"]},
                             "otros_origenes": [(o["origen"], o["ip"]) for o in r["otros_origenes"]],
                             "ping_track_server": r["servicios"]["track-server"]["ping"]}

    # --- 2. PING/PONG
    print("2) 50 PING -> PONG...")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0)
    rtts, malos = [], 0
    for i in range(50):
        t_ms = ms()
        t0 = time.perf_counter()
        s.sendto(protocolo.armar_latido("PING", "ctrl-1", i, t_ms).encode(), HB)
        try:
            datos, _ = s.recvfrom(256)
            rtts.append((time.perf_counter() - t0) * 1000)
            m = protocolo.leer(datos)
            if not (m and m.tipo == "PONG" and m.origen == "ctrl-1" and m.seq == i and m.t_ms == t_ms):
                malos += 1
        except socket.timeout:
            malos += 1
        time.sleep(0.05)
    rtts.sort()
    informe["2_ping_pong"] = {"enviados": 50, "respondidos": len(rtts), "pong_incorrectos_o_perdidos": malos,
                              "rtt_min_ms": round(rtts[0], 3), "rtt_prom_ms": round(sum(rtts) / len(rtts), 3),
                              "rtt_p95_ms": round(rtts[int(0.95 * len(rtts)) - 1], 3), "rtt_max_ms": round(rtts[-1], 3)}
    print("  ", informe["2_ping_pong"])

    # --- 3. player-2 deja de latir
    print("3) player-2 deja de latir...")
    emisores["player-2"].activo = False
    t_caido = esperar_estado(estados_mqtt, "player-2", "CAIDO")
    informe["3_player2_sin_latido"] = {"segundos_hasta_CAIDO": round(t_caido, 2) if t_caido else None,
                                       "motivo": resumen()["servicios"]["player-2"]["motivo"]}
    print("  ", informe["3_player2_sin_latido"])

    # --- 4. jitter artificial a sim-nao
    print("4) jitter artificial (0-120 ms) en sim-nao...")
    emisores["sim-nao"].retardo_max_ms = 120
    t_lento = esperar_estado(estados_mqtt, "sim-nao", "LENTO")
    r = resumen()
    informe["4_simnao_jitter"] = {"segundos_hasta_LENTO": round(t_lento, 2) if t_lento else None,
                                  "jitter_hb_ms": r["servicios"]["sim-nao"]["hb"]["jitter_ms"],
                                  "motivo": r["servicios"]["sim-nao"]["motivo"]}
    print("  ", informe["4_simnao_jitter"])

    # --- 5. sim-spot vivo=0
    print("5) sim-spot publica vivo=0...")
    t0 = time.monotonic()
    clientes["sim-spot"].publish("lab/vivo/sim-spot", "0", qos=1, retain=True)
    t_spot = esperar_estado(estados_mqtt, "sim-spot", "CAIDO", 10)
    informe["5_simspot_vivo0"] = {"segundos_hasta_CAIDO": round(t_spot, 2) if t_spot else None}
    print("  ", informe["5_simspot_vivo0"])

    if args.captura:
        print("   captura del dashboard con OK / LENTO / CAIDO a la vista...")
        time.sleep(3)
        subprocess.run(["node", CAPTURA_JS, "http://127.0.0.1:18080/", args.captura, "5000",
                        "ancho=1500", "alto=1500"], check=False)

    # --- 6. player-2 vuelve con la secuencia que siguió subiendo -> pérdida
    print("6) player-2 vuelve (hueco de secuencia = pérdida)...")
    emisores["player-2"].activo = True
    t_vuelve = esperar_estado(estados_mqtt, "player-2", "LENTO", 15)
    r = resumen()
    hb = r["servicios"]["player-2"]["hb"]
    informe["6_player2_vuelve"] = {"segundos_hasta_LENTO": round(t_vuelve, 2) if t_vuelve else None,
                                   "perdidos": hb["perdidos"], "recibidos": hb["recibidos"],
                                   "perdida_60s_pct": hb["perdida_60s_pct"],
                                   "motivo": r["servicios"]["player-2"]["motivo"]}
    print("  ", informe["6_player2_vuelve"])

    # Quitar el jitter y ver cuánto tarda sim-nao en volver a OK (el filtro de 1/16 se va olvidando).
    print("7) se quita el jitter de sim-nao: ¿cuánto tarda en volver a OK?")
    emisores["sim-nao"].retardo_max_ms = 0
    t_ok = esperar_estado(estados_mqtt, "sim-nao", "OK", 90)
    informe["7_simnao_vuelve_ok"] = {"segundos_hasta_OK": round(t_ok, 2) if t_ok else None,
                                     "jitter_hb_ms": resumen()["servicios"]["sim-nao"]["hb"]["jitter_ms"]}
    print("  ", informe["7_simnao_vuelve_ok"])

    # Estado final de todo, para el informe
    r = resumen()
    informe["final"] = {n: {"estado": d["estado"], "motivo": d["motivo"]} for n, d in r["servicios"].items()}
    informe["final_ping_router"] = r["servicios"]["router"]["ping"]
    with open(os.path.join(SALIDA, "prueba_admin.json"), "w", encoding="utf-8") as f:
        json.dump(informe, f, ensure_ascii=False, indent=2)
    print("informe en", os.path.join(SALIDA, "prueba_admin.json"))
    parar_met.set()
    for c in clientes.values():
        c.loop_stop()
        c.disconnect()
    obs.loop_stop()


if __name__ == "__main__":
    main()
