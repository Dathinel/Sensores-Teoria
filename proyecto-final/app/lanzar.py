"""Arranca la linea simulada: el supervisor (simulacion + visor 3D) y el
dashboard de Streamlit, cada uno en su proceso (seccion 8). Lo usa
`visor.bat` (doble clic): si ya hay una corrida andando solo abre el visor;
si no, la arranca y lo abre.

    python -m app.lanzar --auto prueba_completa --abrir         # lo que hace visor.bat
    python -m app.lanzar --auto prueba_completa --reemplazar    # reinicia con el codigo actual

Ctrl+C (o cerrar la ventana) cierra los dos procesos.
"""

from __future__ import annotations

import argparse
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
        "($p.CommandLine.Contains('app.supervisor') -or $p.CommandLine.Contains('app/dashboard.py'))) { "
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
        except OSError:
            time.sleep(0.5)
    return False


def main() -> None:
    analizador = argparse.ArgumentParser(description="Supervisor + dashboard en un solo comando.")
    analizador.add_argument("--auto", metavar="ESCENARIO")
    analizador.add_argument("--puerto", type=int, default=8501)
    analizador.add_argument("--reemplazar", action="store_true",
                            help="cerrar antes una instancia anterior de este proyecto que ocupe los puertos")
    analizador.add_argument("--abrir", action="store_true", help="abrir el visor 3D y el dashboard en el navegador")
    analizador.add_argument("--ver", default="", help="parametros de la URL del visor, p. ej. 'sensor=cortina'")
    args = analizador.parse_args()

    import yaml
    puerto_visor = yaml.safe_load((RAIZ / "config" / "parametros.yaml").read_text(encoding="utf-8"))[
        "supervisor"]["puerto_http"]
    if args.reemplazar:
        _cerrar_instancia_anterior([puerto_visor, args.puerto])
    elif _esperar(f"http://localhost:{puerto_visor}/", segundos=1):
        # Ya hay una corrida andando (por ejemplo la que se deja en segundo
        # plano): no se arranca otra, solo se abre el visor.
        print("La simulacion ya esta corriendo.")
        if args.abrir:
            webbrowser.open(f"http://localhost:{puerto_visor}/" + (f"?{args.ver}" if args.ver else ""))
        return

    cmd_supervisor = [sys.executable, "-m", "app.supervisor"]
    if args.auto:
        cmd_supervisor += ["--auto", args.auto]
    cmd_dashboard = [sys.executable, "-m", "streamlit", "run", "app/dashboard.py",
                     "--server.port", str(args.puerto)]

    comandos = {"supervisor": cmd_supervisor, "dashboard": cmd_dashboard}
    procesos = {nombre: subprocess.Popen(cmd, cwd=RAIZ) for nombre, cmd in comandos.items()}
    url_visor = f"http://localhost:{puerto_visor}/" + (f"?{args.ver}" if args.ver else "")
    url_dashboard = f"http://localhost:{args.puerto}"
    print(f"Visor 3D en {url_visor}")
    print(f"Dashboard en {url_dashboard}  (Ctrl+C para cerrar todo)")
    if args.abrir and _esperar(f"http://localhost:{puerto_visor}/"):
        webbrowser.open(url_visor)
    reinicios = {nombre: 0 for nombre in comandos}
    try:
        while True:
            time.sleep(0.5)
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
                procesos[nombre] = subprocess.Popen(cmd, cwd=RAIZ)
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
