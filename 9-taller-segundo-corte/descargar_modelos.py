"""Descarga los modelos 3D REALES de Baxter y Atlas que usan los puntos b) y c).

Los URDF y las mallas vienen del repositorio que compartió el profesor
(https://github.com/erwincoumans/pybullet_robots, carpeta data/). No vienen en el
paquete pip `pybullet_data` y pesan decenas de MB, así que NO se suben a este
repositorio: este script los baja una sola vez a la carpeta `modelos/` (que
`.gitignore` excluye) y los dos scripts de PyBullet los buscan ahí.

    entorno\\Scripts\\python descargar_modelos.py

Solo usa la biblioteca estándar (urllib): no hay que instalar nada más.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = "erwincoumans/pybullet_robots"
RAMA = "master"
ARBOL = f"https://api.github.com/repos/{REPO}/git/trees/{RAMA}?recursive=1"
CRUDO = f"https://raw.githubusercontent.com/{REPO}/{RAMA}/"

# Carpeta destino: 9-taller-segundo-corte/modelos/ (la misma que leen los scripts).
DESTINO = Path(__file__).resolve().parent / "modelos"

# Cada robot: su URDF (ruta dentro de data/) y la carpeta desde donde se
# resuelven las mallas que el URDF nombra.
#  - Baxter nombra sus mallas como "package://baxter_description/meshes/...":
#    PyBullet quita el "package://" y busca el resto dentro de las rutas de
#    búsqueda, por eso la raíz de esas rutas es data/baxter_common/.
#  - Atlas nombra sus mallas relativas a su propio URDF (meshes_unplugged/...).
ROBOTS = {
    "Baxter": ("baxter_common/baxter_description/urdf/toms_baxter.urdf", "baxter_common/"),
    "Atlas": ("atlas/atlas_v4_with_multisense.urdf", "atlas/"),
}


def bajar(url: str) -> bytes:
    """Baja una URL completa (con un timeout generoso: las mallas pesan varios MB)."""
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def mallas_del_urdf(texto_urdf: str) -> set[str]:
    """Todos los archivos que el URDF pide con filename="..." (mallas .DAE / .obj)."""
    return set(re.findall(r'filename="([^"]+)"', texto_urdf))


def main() -> None:
    print(f"Leyendo la lista de archivos de {REPO}...")
    arbol = json.loads(bajar(ARBOL))["tree"]
    tamanos = {x["path"]: x.get("size", 0) for x in arbol if x["type"] == "blob"}

    # 1) Primero se arma la lista completa de los dos robots (sin bajar nada todavía): así se sabe
    #    de antemano cuántos MB faltan y se puede mostrar el avance real ("bajando 12.3/37.0 MB"),
    #    que la app del tema 9 convierte en una barra de progreso.
    por_robot = {}
    for robot, (urdf, raiz_mallas) in ROBOTS.items():
        texto = bajar(CRUDO + "data/" + urdf).decode("utf-8")
        pedidos = {urdf}
        for nombre in mallas_del_urdf(texto):
            if nombre.startswith("package://"):
                # package://baxter_description/meshes/x.DAE -> baxter_common/baxter_description/meshes/x.DAE
                pedidos.add(raiz_mallas + nombre[len("package://"):])
            else:
                # relativo a la carpeta del URDF
                pedidos.add(str(Path(urdf).parent.as_posix()) + "/" + nombre)
        # Los .obj de Atlas traen su material (.mtl) y texturas (.png) al lado:
        # se bajan también para que el modelo se vea con sus colores.
        extra = {p[len("data/"):] for p in tamanos
                 if p.startswith("data/" + raiz_mallas) and p.lower().endswith((".mtl", ".png"))}
        pedidos |= extra

        faltan = sorted(p for p in pedidos if "data/" + p not in tamanos)
        if faltan:
            print(f"  ! {robot}: el repositorio ya no tiene {len(faltan)} archivo(s): {faltan[:3]}...")
        por_robot[robot] = sorted(pedidos - set(faltan))

    def ya_esta(rel):
        destino = DESTINO / rel
        return destino.exists() and destino.stat().st_size == tamanos["data/" + rel]

    por_bajar = sum(tamanos["data/" + r] for lista in por_robot.values() for r in lista if not ya_esta(r)) / 1e6
    if por_bajar:
        print(f"Hay que bajar {por_bajar:.2f} MB (solo esta vez).")
    else:
        print("Los modelos ya estaban completos: no se baja nada.")

    # 2) Ahora sí se baja lo que falta, archivo por archivo, contando los MB.
    total, bajado = 0.0, 0.0
    for robot, lista in por_robot.items():
        bajados = 0
        for rel in lista:
            if ya_esta(rel):
                continue  # ya estaba: no se vuelve a bajar
            destino = DESTINO / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(bajar(CRUDO + "data/" + rel))
            bajados += 1
            bajado += tamanos["data/" + rel] / 1e6
            print(f"  bajando {bajado:.2f}/{por_bajar:.2f} MB  {Path(rel).name}", flush=True)
        mb = sum(tamanos["data/" + r] for r in lista) / 1e6
        total += mb
        print(f"  {robot}: {len(lista)} archivos ({mb:.1f} MB), {bajados} descargados ahora")

    print(f"Listo: {total:.1f} MB en {DESTINO}")


if __name__ == "__main__":
    try:
        main()
    except OSError as e:  # sin internet, GitHub caído, límite de la API...
        print("No se pudo descargar:", e)
        sys.exit(1)
