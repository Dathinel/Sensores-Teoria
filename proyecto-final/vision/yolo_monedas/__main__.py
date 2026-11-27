"""`python -m vision.yolo_monedas`: abre la página del detector en la red Wi-Fi para el celular.

Escucha en 0.0.0.0 (IPv4: en IPv6 Streamlit se cuelga en Windows, ver la regla streamlit-windows)
y muestra la dirección que hay que escribir en el navegador del celular. Solo expone el detector:
el tablero de la línea sigue en 127.0.0.1.
"""

import socket
import subprocess
import sys
from pathlib import Path

from control.configuracion import cargar_parametros

PAGINA = Path(__file__).resolve().parent / "pagina.py"


def ip_local() -> str:
    # Un socket UDP "conectado" no manda nada, pero dice qué interfaz sale a la red.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("192.168.1.1", 80))
        return s.getsockname()[0]


if __name__ == "__main__":
    puerto = cargar_parametros()["yolo_monedas"]["puerto"]
    print(f"En el celular (misma Wi-Fi), abra: http://{ip_local()}:{puerto}", flush=True)
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(PAGINA),
                                      "--server.address", "0.0.0.0", "--server.port", str(puerto),
                                      "--server.maxUploadSize", "50", *sys.argv[1:]]))
