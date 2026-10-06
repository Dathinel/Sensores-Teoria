"""Arranca la linea simulada: el supervisor (simulacion + visor 3D) y el
dashboard de Streamlit, cada uno en su proceso (seccion 8). Lo usa
`visor.bat` (doble clic): el .bat abre el visor portable y esto arranca la
simulacion (si no estaba andando) y abre el dashboard de Streamlit apenas responde.

    python -m app.lanzar --auto prueba_completa --abrir-dashboard   # lo que hace visor.bat
    python -m app.lanzar --auto prueba_completa --abrir         # abre el visor en vivo
    python -m app.lanzar --auto prueba_completa --reemplazar    # reinicia con el codigo actual
    python -m app.lanzar --auto prueba_completa --puerto-visor 9000   # otro puerto para el visor

Puertos (app/puertos.py): el visor 3D usa el 8765 (config/parametros.yaml) o el de
PLANTA_PUERTO_VISOR / --puerto-visor; si lo tiene OTRO programa, usa el siguiente libre y lo
dice, y abre el navegador en ese puerto. Igual el dashboard (8501, --puerto).

Ctrl+C (o cerrar la ventana) cierra los dos procesos.
"""

from __future__ import annotations

import argparse
import http.client
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _cerrar_instancia_anterior(puertos: list[int]) -> None:
    """Si otra corrida de ESTE proyecto (supervisor o dashboard) tiene los
    puertos ocupados, la cierra para que la nueva arranque con el codigo
    actual; tambien cierra el `app.lanzar` que la vigilaba (si no, la
    volveria a levantar). Solo toca procesos de este proyecto; si el puerto
    lo tiene otro programa, no lo toca. Solo Windows (usa PowerShell, sin
    librerias extra)."""
    if sys.platform != "win32":
        return
    import os
    lista = ",".join(str(p) for p in puertos)
    raiz = str(RAIZ).replace("'", "''")
    script = (
        f"Get-NetTCPConnection -LocalPort {lista} -State Listen -ErrorAction SilentlyContinue | "
        "ForEach-Object { $p = Get-CimInstance Win32_Process -Filter \"ProcessId=$($_.OwningProcess)\"; "
        f"if ($p.CommandLine -and $p.CommandLine.Contains('{raiz}') -and "
        "($p.CommandLine.Contains('app.supervisor') -or $p.CommandLine.Contains('app/dashboard'))) { "
        # 'app/dashboard' reconoce el dashboard viejo (app/dashboard.py) y el nuevo (app/dashboard/inicio.py).
        # Con el entorno virtual hay un proceso intermedio (el python.exe de
        # entorno/Scripts relanza al real), asi que se sube hasta 4 niveles
        # buscando el app.lanzar; nunca el de esta misma corrida.
        "$q = $p; for ($i = 0; $i -lt 4; $i++) { "
        "$q = Get-CimInstance Win32_Process -Filter \"ProcessId=$($q.ParentProcessId)\"; if (-not $q) { break }; "
        f"if ($q.ProcessId -ne {os.getpid()} -and $q.ProcessId -ne {os.getppid()} -and $q.CommandLine -and "
        "$q.CommandLine.Contains('app.lanzar')) { Stop-Process -Id $q.ProcessId -Force "
        "-ErrorAction SilentlyContinue } }; "
        "Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue; "
        "Write-Output \"cerrada la instancia anterior (pid $($p.ProcessId))\" } }"
    )
    salida = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True)
    if salida.stdout.strip():
        print(salida.stdout.strip())
        time.sleep(1.0)   # que Windows libere los puertos


def _esperar(url: str, segundos: float = 60) -> bool:
    fin = time.time() + segundos
    while time.time() < fin:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (OSError, http.client.HTTPException):   # HTTPException no es OSError (respuesta rota)
            time.sleep(0.5)
    return False


def main() -> None:
    analizador = argparse.ArgumentParser(description="Supervisor + dashboard en un solo comando.")
    analizador.add_argument("--auto", metavar="ESCENARIO")
    analizador.add_argument("--puerto", type=int, default=8501)
    analizador.add_argument("--reemplazar", action="store_true",
                            help="cerrar antes una instancia anterior de este proyecto que ocupe los puertos")
    analizador.add_argument("--abrir", action="store_true", help="abrir el visor 3D y el dashboard en el navegador")
    analizador.add_argument("--abrir-dashboard", action="store_true",
                            help="abrir el dashboard de Streamlit en el navegador cuando responda")
    analizador.add_argument("--ver", default="", help="parametros de la URL del visor, p. ej. 'sensor=cortina'")
    analizador.add_argument("--puerto-visor", type=int, default=None,
                            help="puerto del visor 3D (por defecto PLANTA_PUERTO_VISOR o config/parametros.yaml, "
                                 "8765); si lo tiene otro programa se usa el siguiente libre")
    args = analizador.parse_args()

    from app import puertos

    pedido = args.puerto_visor or puertos.puerto_pedido()
    if args.reemplazar:
        # La corrida anterior pudo quedar en un puerto corrido (8766...) si el pedido estaba ocupado.
        _cerrar_instancia_anterior(list(range(pedido, pedido + puertos.INTENTOS + 1))
                                   + list(range(args.puerto, args.puerto + puertos.INTENTOS + 1)))
    puerto_visor, como, ocupados = puertos.elegir(pedido)
    aviso = puertos.mensaje(pedido, puerto_visor, como, ocupados)
    if aviso:
        print(aviso)
    if como == "nuestro":
        # Ya hay una corrida andando (por ejemplo la que se deja en segundo
        # plano): no se arranca otra, solo se abre el visor (en SU puerto).
        print(f"La simulacion ya esta corriendo: visor 3D en http://127.0.0.1:{puerto_visor}/")
        anotados = puertos.leer()
        puerto_dash = anotados.get("dashboard", args.puerto) if anotados.get("visor") == puerto_visor else args.puerto
        # La app de la practica (app-practica) saca de esta linea el enlace del dashboard.
        print(f"Dashboard en http://127.0.0.1:{puerto_dash}")
        if args.abrir:
            webbrowser.open(f"http://127.0.0.1:{puerto_visor}/" + (f"?{args.ver}" if args.ver else ""))
        if args.abrir_dashboard and _esperar(f"http://127.0.0.1:{puerto_dash}/", segundos=5):
            webbrowser.open(f"http://127.0.0.1:{puerto_dash}/")
        return

    # El dashboard tambien: si el 8501 lo tiene otro programa, Streamlit no arranca.
    pedido_dash = args.puerto
    args.puerto, ocupados_dash = puertos.primer_libre(pedido_dash)
    if ocupados_dash:
        print(f"AVISO: el puerto {', '.join(map(str, ocupados_dash))} esta ocupado; el dashboard usa el "
              f"{args.puerto}: http://127.0.0.1:{args.puerto}/")
    puertos.guardar(puerto_visor, args.puerto)
    # El supervisor y el dashboard leen el puerto real del visor de aqui (app/puertos.py).
    entorno = dict(os.environ, **{puertos.VARIABLE: str(puerto_visor)})

    cmd_supervisor = [sys.executable, "-m", "app.supervisor"]
    if args.auto:
        cmd_supervisor += ["--auto", args.auto]
    # Solo IPv4 local (127.0.0.1): en Windows, escuchando en "::" (IPv6) un cliente que corta la
    # conexion de golpe (Chrome sin ventana de las capturas) deja el bucle que acepta conexiones de
    # Streamlit roto (OSError WinError 64): el proceso sigue vivo pero ya no atiende a nadie. Ademas
    # asi el tablero no queda expuesto a la red del salon.
    cmd_dashboard = [sys.executable, "-m", "streamlit", "run", "app/dashboard/inicio.py",
                     "--server.port", str(args.puerto), "--server.address", "127.0.0.1"]

    comandos = {"supervisor": cmd_supervisor, "dashboard": cmd_dashboard}
    procesos = {nombre: subprocess.Popen(cmd, cwd=RAIZ, env=entorno) for nombre, cmd in comandos.items()}
    url_visor = f"http://127.0.0.1:{puerto_visor}/" + (f"?{args.ver}" if args.ver else "")
    url_dashboard = f"http://127.0.0.1:{args.puerto}"
    print(f"Visor 3D en {url_visor}")
    print(f"Dashboard en {url_dashboard}  (Ctrl+C para cerrar todo)")
    if args.abrir and _esperar(f"http://127.0.0.1:{puerto_visor}/"):
        webbrowser.open(url_visor)
    if args.abrir_dashboard and _esperar(url_dashboard + "/"):
        webbrowser.open(url_dashboard)
    reinicios = {nombre: 0 for nombre in comandos}
    # Salud del dashboard: un proceso VIVO que no atiende (ver arriba) no se detecta con poll().
    # Cada 10 s se le pregunta a /_stcore/health; 3 fallos seguidos (~30 s) = se reinicia.
    salud = {"proxima": time.monotonic() + 60, "fallos": 0}
    try:
        while True:
            time.sleep(0.5)
            if time.monotonic() >= salud["proxima"]:
                salud["proxima"] = time.monotonic() + 10
                p = procesos["dashboard"]
                if p.poll() is None:
                    if _esperar(f"http://127.0.0.1:{args.puerto}/_stcore/health", segundos=3):
                        salud["fallos"] = 0
                    else:
                        salud["fallos"] += 1
                        if salud["fallos"] >= 3:
                            print("dashboard vivo pero sin responder; reiniciando...")
                            salud["fallos"] = 0
                            salud["proxima"] = time.monotonic() + 60
                            p.kill()
                            p.wait(timeout=10)
            for nombre, p in procesos.items():
                if p.poll() is None:
                    continue
                # Si uno de los dos se cae solo, se vuelve a levantar en vez
                # de tumbar el otro: con Python 3.14 en Windows se vio a
                # Streamlit morir una vez con "Fatal Python error:
                # _PySemaphore_Wakeup" (fallo del interprete, no del
                # proyecto), y no puede tumbar la linea en plena
                # sustentacion. El supervisor, al reiniciarse, espera la
                # orden de iniciar (sin --auto) para no borrar la corrida.
                if reinicios[nombre] >= 5:
                    print(f"{nombre} se cayo 5 veces; cierro todo.")
                    raise KeyboardInterrupt
                reinicios[nombre] += 1
                print(f"{nombre} termino (codigo {p.returncode}); reiniciando ({reinicios[nombre]}/5)...")
                cmd = [c for c in comandos[nombre] if c != "--auto" and c != args.auto] if nombre == "supervisor" else comandos[nombre]
                procesos[nombre] = subprocess.Popen(cmd, cwd=RAIZ, env=entorno)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procesos.values():
            if p.poll() is None:
                p.terminate()
        for p in procesos.values():
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
