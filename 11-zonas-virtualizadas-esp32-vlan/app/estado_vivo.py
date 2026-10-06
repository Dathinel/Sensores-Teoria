"""Puente del estado en vivo para la app del tema 11.

Por qué existe: la app se abre desde el lanzador (http://127.0.0.1:<puerto>/app/...) y el
dashboard del admin vive en otro origen (http://127.0.0.1:8180). El admin no manda cabeceras
CORS, así que el navegador no deja que la app lea /api/resumen.json directamente. Este script sí
puede: lo pide cada segundo y escribe una línea corta por cada lectura, que la app recibe por la
salida en vivo del lanzador y dibuja (los 6 LED, la latencia y el estado de cada servicio).

Solo LEE el dashboard (un GET a /api/resumen.json, lo mismo que hace la página del admin): no se
conecta al broker MQTT ni toca ningún contenedor. Además, cada 3 s pregunta a Docker (solo lectura:
`docker ps`, `docker images`, `docker network ls`) qué contenedores, imágenes y redes del laboratorio
existen y en qué estado están, para que la app los muestre como Docker Desktop. Usa solo la
biblioteca estándar.

Formato: el lanzador corta las líneas largas (2000 caracteres), así que cada lectura sale en
varias líneas cortas que la app junta:
    VIVO_GEN {t, en_marcha_s, mqtt, leds, umbrales}
    VIVO_SVC {nombre, estado, rtt...}        (una por servicio)
    VIVO_LAT [{origen, ip, edad, perdidos}...]
    VIVO_OK                                   (fin de la lectura: la app dibuja)
    VIVO_CONT {nombre, servicio, imagen, estado, salud, texto, puertos}   (una por contenedor)
    VIVO_IMGS [{repo, tag, tamano}...]  VIVO_REDES [{nombre, subred}...]
    VIVO_DOCKER_OK                            (fin de la lectura de Docker)
o bien  SIN_ADMIN <motivo>  y, al terminar,  FIN <motivo>.
Se cierra con Ctrl+C, con el botón Detener de la app o solo al pasar --minutos.
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

URL = "http://127.0.0.1:8180/api/resumen.json"
PROYECTO = "zonas-esp32"            # "name:" del docker-compose.yml: etiqueta de sus contenedores
REDES = ("vlan1_gamer", "vlan2_robotica", "vlan3_admin")
# En Windows, que los "docker ..." de cada lectura no abran una ventana de consola.
SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def docker(*args, timeout=8):
    """Corre un comando de docker de SOLO LECTURA y devuelve su salida (o None si falla)."""
    try:
        r = subprocess.run(["docker", *args], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, creationflags=SIN_VENTANA,
                           stdin=subprocess.DEVNULL)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def lineas_json(texto):
    """`--format "{{json .}}"` escribe un objeto JSON por línea."""
    for linea in (texto or "").splitlines():
        try:
            yield json.loads(linea)
        except ValueError:
            pass


def leer_docker(con_imagenes):
    """Lo que mostraría Docker Desktop del laboratorio: contenedores, imágenes y redes.
    Devuelve None si Docker no responde (Docker Desktop cerrado)."""
    salida = docker("ps", "-a", "--filter", f"label=com.docker.compose.project={PROYECTO}",
                    "--format", "{{json .}}")
    if salida is None:
        return None
    conts = []
    for c in lineas_json(salida):
        etiquetas = dict(e.split("=", 1) for e in (c.get("Labels") or "").split(",") if "=" in e)
        texto = c.get("Status") or ""
        salud = "healthy" if "(healthy)" in texto else "unhealthy" if "(unhealthy)" in texto else                 "starting" if "health: starting" in texto else ""
        # Puertos publicados en el PC, sin repetir IPv4/IPv6: "8180->8080/tcp"
        puertos = []
        for p in (c.get("Ports") or "").split(", "):
            if "->" in p:
                corto = p.split(":")[-1]
                if corto not in puertos:
                    puertos.append(corto)
        conts.append({"nombre": c.get("Names"), "servicio": etiquetas.get("com.docker.compose.service", ""),
                      "imagen": c.get("Image"), "estado": c.get("State"), "salud": salud,
                      "texto": texto, "puertos": puertos})
    datos = {"contenedores": conts}
    if con_imagenes:
        imgs = docker("images", "--filter", "reference=*/zonas-esp32-*", "--format", "{{json .}}")
        datos["imagenes"] = [{"repo": i.get("Repository"), "tag": i.get("Tag"), "tamano": i.get("Size"),
                              "creada": i.get("CreatedSince")} for i in lineas_json(imgs)
                             if i.get("Tag") == "1.0"]   # la etiqueta que usa el compose
        redes = []
        for nombre in REDES:
            sub = docker("network", "inspect", nombre, "--format",
                         "{{range .IPAM.Config}}{{.Subnet}}{{end}}", timeout=5)
            redes.append({"nombre": nombre, "subred": (sub or "").strip(), "existe": sub is not None})
        datos["redes"] = redes
    return datos


def imprimir_docker(d):
    for c in d["contenedores"]:
        print("VIVO_CONT " + compacto(c))
    if "imagenes" in d:
        print("VIVO_IMGS " + compacto(d["imagenes"]))
        print("VIVO_REDES " + compacto(d["redes"]))
    print("VIVO_DOCKER_OK", flush=True)


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
    ap.add_argument("--sin-docker", dest="docker", action="store_false",
                    help="no preguntar a Docker por los contenedores, imágenes y redes")
    ap.add_argument("--cada-docker", type=float, default=3.0, help="segundos entre lecturas de Docker")
    a = ap.parse_args()

    inicio = time.time()
    fin = inicio + a.minutos * 60
    ultimo_error = None
    alguna_vez = False   # después de la primera lectura buena ya no se rinde: el admin puede
                         # reiniciarse (la prueba de disponibilidad lo apaga 30 s) y se espera
    ultimo_docker = 0.0
    vueltas_docker = 0
    hay_contenedores = False   # alguno del laboratorio corriendo (o arrancando): se espera al admin
    while time.time() < fin:
        if a.docker and time.time() - ultimo_docker >= a.cada_docker:
            ultimo_docker = time.time()
            # Imágenes y redes cambian poco: cada 5 lecturas (y en la primera).
            d = leer_docker(con_imagenes=(vueltas_docker % 5 == 0))
            vueltas_docker += 1
            if d is None:
                print("SIN_DOCKER Docker no responde: ¿está abierto Docker Desktop?", flush=True)
                hay_contenedores = False
            else:
                imprimir_docker(d)
                hay_contenedores = any(c["estado"] in ("running", "restarting", "created") for c in d["contenedores"])
        if not alguna_vez and not hay_contenedores and a.rendirse and time.time() - inicio > a.rendirse:
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
