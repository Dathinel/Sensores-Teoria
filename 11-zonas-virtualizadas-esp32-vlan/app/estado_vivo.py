"""Puente del estado en vivo para la app del tema 11.

Por qué existe: la app se abre desde el lanzador (http://127.0.0.1:<puerto>/app/...) y el
dashboard del admin vive en otro origen (http://localhost:8080). El admin no manda cabeceras
CORS, así que el navegador no deja que la app lea /api/resumen.json directamente. Este script sí
puede: lo pide cada segundo y escribe una línea corta por cada lectura, que la app recibe por la
salida en vivo del lanzador y dibuja (los 6 LED, la latencia y el estado de cada servicio).

Solo LEE el dashboard (un GET a /api/resumen.json, lo mismo que hace la página del admin): no se
conecta al broker MQTT ni toca ningún contenedor. Usa solo la biblioteca estándar.

Formato: el lanzador corta las líneas largas (2000 caracteres), así que cada lectura sale en
varias líneas cortas que la app junta:
    VIVO_GEN {t, en_marcha_s, mqtt, leds, umbrales}
    VIVO_SVC {nombre, estado, rtt...}        (una por servicio)
    VIVO_LAT [{origen, ip, edad, perdidos}...]
    VIVO_OK                                   (fin de la lectura: la app dibuja)
o bien  SIN_ADMIN <motivo>  y, al terminar,  FIN <motivo>.
Se cierra con Ctrl+C, con el botón Detener de la app o solo al pasar --minutos.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

URL = "http://localhost:8080/api/resumen.json"


def resumir(datos):
    """Del resumen completo del admin (unos 19 kB, con el historial de pings) se queda con lo que
    la app muestra, para que cada línea sea corta."""
    servicios = {}
    for nombre, s in (datos.get("servicios") or {}).items():
        ping = s.get("ping") or {}
        hb = s.get("hb") or {}
        servicios[nombre] = {
            "vlan": s.get("vlan"),
            "ip": s.get("ip"),
            "estado": s.get("estado"),
            "motivo": s.get("motivo"),
            "led": s.get("led"),
            "rtt": ping.get("rtt_ultimo_ms"),
            "prom": ping.get("rtt_prom_ms"),
            "p95": ping.get("rtt_p95_ms"),
            "jit": ping.get("jitter_ms"),
            "disp": ping.get("disp_60s_pct"),
            "disp_total": ping.get("disp_total_pct"),
            "hb_edad": hb.get("edad_s"),
            "perdidos": hb.get("perdidos"),
        }
    latidos = [{"origen": o.get("origen"), "ip": o.get("ip"), "edad": o.get("edad_s"),
                "perdidos": o.get("perdidos")} for o in (datos.get("otros_origenes") or [])]
    return {
        "t": datos.get("t"),
        "en_marcha_s": datos.get("en_marcha_s"),
        "mqtt": datos.get("mqtt_conectado"),
        "leds": datos.get("leds") or [],
        "umbrales": datos.get("umbrales") or {},
        "servicios": servicios,
        "latidos": latidos,
    }


def compacto(objeto):
    """JSON en una línea, sin espacios y solo ASCII (las tildes van escapadas)."""
    return json.dumps(objeto, ensure_ascii=True, separators=(",", ":"))


def main():
    # La salida la lee el lanzador como texto UTF-8; en Windows, sin esto, una tubería usa cp1252.
    # El JSON va además con ensure_ascii=True (las tildes viajan escapadas, á), a prueba de todo.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=URL)
    ap.add_argument("--cada", type=float, default=1.0, help="segundos entre lecturas")
    ap.add_argument("--minutos", type=float, default=30.0, help="se cierra solo después de esto")
    ap.add_argument("--rendirse", type=float, default=20.0,
                    help="si el admin nunca respondió, se cierra tras estos segundos (0 = nunca)")
    a = ap.parse_args()

    inicio = time.time()
    fin = inicio + a.minutos * 60
    ultimo_error = None
    alguna_vez = False   # después de la primera lectura buena ya no se rinde: el admin puede
                         # reiniciarse (la prueba de disponibilidad lo apaga 30 s) y se espera
    while time.time() < fin:
        if not alguna_vez and a.rendirse and time.time() - inicio > a.rendirse:
            print(f"FIN el admin no respondió en {a.rendirse:g} s: levanta el laboratorio y vuelve a pulsar.", flush=True)
            return
        try:
            with urllib.request.urlopen(a.url, timeout=3) as r:
                datos = json.loads(r.read().decode("utf-8"))
            res = resumir(datos)
            lineas = ["VIVO_GEN " + compacto({k: res[k] for k in ("t", "en_marcha_s", "mqtt", "leds", "umbrales")})]
            lineas += ["VIVO_SVC " + compacto(dict(nombre=n, **v)) for n, v in res["servicios"].items()]
            lineas += ["VIVO_LAT " + compacto(res["latidos"]), "VIVO_OK"]
            for linea in lineas:
                print(linea)
            sys.stdout.flush()
            ultimo_error = None
            alguna_vez = True
        except (urllib.error.URLError, OSError, ValueError) as e:
            motivo = getattr(e, "reason", e)
            texto = f"no responde {a.url} ({motivo}). ¿Está levantado el laboratorio?"
            # Se repite cada vez (la app la usa como latido), pero sin inundar: una cada 3 s.
            print("SIN_ADMIN " + texto, flush=True)
            if texto == ultimo_error:
                time.sleep(2)
            ultimo_error = texto
        time.sleep(a.cada)
    print("FIN se cumplió el tiempo; vuelve a pulsar para seguir mirando.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
