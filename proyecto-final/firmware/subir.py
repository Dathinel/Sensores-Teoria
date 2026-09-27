"""Sube el firmware a un ESP32 con MicroPython, sin abrir Thonny.

    python -m firmware.subir fijo              # busca el puerto solo
    python -m firmware.subir carro --puerto COM7

Primero arma firmware/salida/<placa>/ (firmware.preparar), despues copia
todos los archivos a la raiz de la placa con `mpremote` y la reinicia: el
main.py nuevo arranca solo.

Antes, UNA vez por placa: grabarle MicroPython 1.29 (el .mpy lo compila
mpy-cross 1.29; una version muy vieja no lo lee):
    python -m esptool --chip esp32 erase_flash
    python -m esptool --chip esp32 write_flash -z 0x1000 ESP32_GENERIC-v1.29.bin
(el .bin se descarga de micropython.org/download/ESP32_GENERIC).

Ojo, como en el tema 8: con Thonny abierto sobre el mismo puerto, mpremote no
puede conectarse (el puerto queda ocupado). Cerrar Thonny primero.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

from firmware.preparar import preparar

# Chips USB-serial de las placas de los labs (CP2102 y CH340).
USB_ESP32 = {0x10C4, 0x1A86}


def buscar_puerto() -> str | None:
    from serial.tools import list_ports

    for p in list_ports.comports():
        if p.vid in USB_ESP32:
            return p.device
    return None


def main() -> None:
    a = argparse.ArgumentParser(description="Sube el firmware a un ESP32.")
    a.add_argument("placa", choices=["fijo", "carro"])
    a.add_argument("--puerto", help="COMx; si no se da, se busca un ESP32 conectado")
    args = a.parse_args()
    puerto = args.puerto or buscar_puerto()
    if puerto is None:
        sys.exit("No encontre ningun ESP32 conectado por USB (CP2102/CH340). Use --puerto COMx.")
    carpeta = preparar(args.placa)
    archivos = sorted(str(f) for f in carpeta.iterdir())
    print(f"Subiendo {len(archivos)} archivos a {puerto}…")
    subprocess.run([sys.executable, "-m", "mpremote", "connect", puerto, "cp", *archivos, ":", "+", "reset"],
                   check=True)
    print("Listo: la placa se reinicio con el firmware nuevo.")


if __name__ == "__main__":
    main()
