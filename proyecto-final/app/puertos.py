"""Puerto del visor 3D (servidor HTTP del supervisor): cual se usa y que
hacer si esta ocupado.

Antes el 8765 era fijo: si otro programa del PC ya lo tenia (pasa: un panel
de Node, Docker...), el supervisor seguia sin visor y la pestaña en vivo
nunca aparecia, sin un error claro. Ahora:

1. El puerto pedido sale, en este orden, de `--puerto-visor` (app.lanzar o
   app.supervisor), de la variable de entorno PLANTA_PUERTO_VISOR o de
   config/parametros.yaml (supervisor.puerto_http, 8765).
2. Si ese puerto lo tiene ESTA app (una corrida anterior), se reutiliza.
   Si lo tiene otro programa, se prueba el siguiente (hasta 20 mas) y se
   avisa cual se uso.
3. app.lanzar le pasa el puerto elegido al supervisor y al dashboard por
   PLANTA_PUERTO_VISOR, y abre el navegador en ESE puerto. El visor
   portable (file://) busca la simulacion en el rango 8765-8784.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.request
from pathlib import Path

VARIABLE = "PLANTA_PUERTO_VISOR"
# Cuantos puertos seguidos se prueban despues del pedido (el visor portable
# busca en el mismo rango: app/visor3d/interfaz.js, PUERTOS_EXTRA).
INTENTOS = 20


def puerto_pedido(parametros: dict | None = None) -> int:
    """El de PLANTA_PUERTO_VISOR si es un numero valido; si no, el de
    config/parametros.yaml."""
    valor = os.environ.get(VARIABLE, "").strip()
    if valor.isdigit() and 0 < int(valor) < 65536:
        return int(valor)
    if parametros is None:
        from app.configuracion import cargar_parametros
        parametros = cargar_parametros()
    return int(parametros["supervisor"]["puerto_http"])


def escuchando(puerto: int) -> bool:
    """¿Algun programa acepta conexiones en 127.0.0.1:puerto?"""
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def libre(puerto: int) -> bool:
    """¿Se puede abrir 127.0.0.1:puerto ahora (como lo abre app/servidor.py)?"""
    if escuchando(puerto):
        return False
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", puerto))
        except OSError:
            return False
    return True


def es_nuestro(puerto: int) -> bool:
    """¿Lo que responde en ese puerto es el supervisor de ESTE proyecto? Se
    reconoce por /api/geometria (JSON con la cinta de monedas): otro
    programa no la tiene."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/geometria", timeout=1.5) as r:
            datos = json.loads(r.read().decode("utf-8"))
        return isinstance(datos, dict) and "cinta_monedas" in datos
    except (OSError, ValueError):
        return False


def elegir(pedido: int, intentos: int = INTENTOS, *, reutilizar: bool = True) -> tuple[int, str, list[int]]:
    """Devuelve (puerto, como, ocupados):
    como = "nuestro" (ya corre esta app ahi), "libre" (se puede abrir) o
    "ninguno" (todos ocupados: se devuelve el pedido); ocupados = los que
    tenia otro programa antes del elegido. Con reutilizar=False (el
    supervisor, que necesita ABRIR el puerto) una corrida nuestra tambien
    cuenta como ocupado."""
    ocupados: list[int] = []
    for puerto in range(pedido, min(pedido + intentos + 1, 65536)):
        if escuchando(puerto):
            if reutilizar and es_nuestro(puerto):
                return puerto, "nuestro", ocupados
            ocupados.append(puerto)
            continue
        if libre(puerto):
            return puerto, "libre", ocupados
        ocupados.append(puerto)
    return pedido, "ninguno", ocupados


def primer_libre(pedido: int, intentos: int = INTENTOS) -> tuple[int, list[int]]:
    """Para el dashboard de Streamlit: el primer puerto libre desde el pedido
    (si todos estan ocupados, el pedido) y los ocupados antes de el."""
    ocupados: list[int] = []
    for puerto in range(pedido, min(pedido + intentos + 1, 65536)):
        if libre(puerto):
            return puerto, ocupados
        ocupados.append(puerto)
    return pedido, ocupados


# La corrida en marcha deja anotados sus puertos reales (lo leen app.lanzar
# cuando la simulacion ya estaba corriendo y app.chequeo). No se versiona.
ARCHIVO = Path(__file__).resolve().parent.parent / "datos" / "puertos.json"


def guardar(visor: int, dashboard: int) -> None:
    try:
        ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
        ARCHIVO.write_text(json.dumps({"visor": visor, "dashboard": dashboard}), encoding="utf-8")
    except OSError:
        pass


def leer() -> dict:
    try:
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def mensaje(pedido: int, puerto: int, como: str, ocupados: list[int]) -> str:
    """Frase para la consola (vacia si se usa el pedido sin problema)."""
    if como == "ninguno":
        return (f"AVISO: los puertos {pedido} a {pedido + INTENTOS} estan todos ocupados por otros programas: "
                f"el visor 3D en vivo no va a abrir. Cierre alguno o elija otro con "
                f"--puerto-visor N (o la variable {VARIABLE}).")
    if not ocupados:
        return ""
    lista = ", ".join(str(p) for p in ocupados)
    return (f"AVISO: el puerto {lista} lo tiene OTRO programa de este PC; el visor 3D usa el {puerto}: "
            f"http://127.0.0.1:{puerto}/ (para fijar uno: --puerto-visor N o la variable {VARIABLE}).")


def main() -> None:
    """`python -m app.puertos`: dice que puertos va a usar visor.bat (codigo 2 si alguno cambia)."""
    pedido = puerto_pedido()
    puerto, como, ocupados = elegir(pedido)
    if como == "nuestro":
        print(f"La simulacion ya esta corriendo: visor 3D en http://127.0.0.1:{puerto}/")
    elif como == "libre" and not ocupados:
        print(f"Visor 3D en http://127.0.0.1:{puerto}/")
    else:
        print(mensaje(pedido, puerto, como, ocupados))
    cambia = bool(ocupados) or como == "ninguno"
    if como != "nuestro":
        dash, ocupados_dash = primer_libre(8501)
        if ocupados_dash:
            print(f"AVISO: el puerto 8501 esta ocupado; el dashboard usa el {dash}: http://127.0.0.1:{dash}/")
            cambia = True
    raise SystemExit(2 if cambia else 0)


if __name__ == "__main__":
    main()
