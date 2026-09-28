"""Arma `visor-portable.html`: el visor 3D en UN solo archivo (usuario, 2026-09-27).

Lo que hace visor.bat: abre este archivo al instante y arranca la simulación por detrás.

- Abierto solo (doble clic, otro PC, sin Python ni internet): muestra la demo grabada
  (app/visor3d/demo/, la graba `python -m app.grabar_demo`).
- Mientras tanto le pregunta cada 3 s a la simulación de ESTE PC (127.0.0.1, el puerto de
  config/parametros.yaml). Cuando responde, la pestaña pasa sola al visor en vivo.

Por qué un solo archivo: el navegador no deja que una página abierta como archivo (file://)
cargue módulos de JavaScript sueltos, hojas de estilo sueltas ni lea .json de la carpeta. Aquí va
todo adentro:

- TODOS los módulos locales que usa visor.js, siguiendo sus imports (la interfaz `interfaz.js`,
  las piezas `piezas/*.js`, `vendor/OrbitControls.js` y cualquier módulo nuevo) como data: URLs en
  el importmap, con su ruta dentro de app/visor3d como nombre (`interfaz.js`, `piezas/base.js`).
  También los nombres del importmap de index.html que apunten a archivos de la carpeta.
- Three.js (`three`), las hojas de estilo locales (`<link rel="stylesheet" href="./x.css">` pasa
  a `<style>`), el visor y la demo.

    python -m app.portable            # escribe visor-portable.html en la raíz del proyecto
"""

from __future__ import annotations

import base64
import json
import posixpath
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
VISOR = RAIZ / "app" / "visor3d"
SALIDA = RAIZ / "visor-portable.html"


def _modulo(codigo: str) -> str:
    return "data:text/javascript;base64," + base64.b64encode(codigo.encode("utf-8")).decode("ascii")


# Todo import estático o dinámico: `from '...'`, `import '...'`, `import('...')`.
_IMPORT = re.compile(r"""(\bfrom\s*|\bimport\s*\(?\s*)(['"])([^'"\n]+)\2""")
_MAPA = re.compile(r'<script type="importmap">\s*(.*?)\s*</script>', re.S)


def _mapa_de_index(html: str) -> dict[str, str]:
    """Nombres del importmap de index.html que apuntan a archivos locales (salvo `three`)."""
    m = _MAPA.search(html)
    imports = json.loads(m.group(1))["imports"] if m else {}
    return {k: v for k, v in imports.items() if k != "three" and v.startswith("./")}


def _resolver(spec: str, desde: str, mapa: dict[str, str]) -> str | None:
    """Ruta (relativa a app/visor3d) del módulo local `spec` importado desde `desde`, o None."""
    if spec.startswith(("./", "../")):
        return posixpath.normpath(posixpath.join(posixpath.dirname(desde), spec))
    if spec in mapa:
        return posixpath.normpath(mapa[spec][2:])
    for prefijo, destino in mapa.items():   # entradas de carpeta: "three/addons/": "./vendor/"
        if prefijo.endswith("/") and spec.startswith(prefijo):
            return posixpath.normpath(destino[2:] + spec[len(prefijo):])
    return None


def _modulos(html: str) -> tuple[str, dict[str, str]]:
    """visor.js reescrito y {nombre: código} de cada módulo local que alcanza por sus imports.

    Un módulo que viene de una data: URL no puede resolver rutas relativas: cada import local pasa
    a ser su nombre en el importmap (la ruta dentro de app/visor3d, p. ej. `piezas/base.js`).
    """
    mapa = _mapa_de_index(html)
    listos: dict[str, str] = {}
    pendientes = ["visor.js"]
    while pendientes:
        ruta = pendientes.pop()
        if ruta in listos:
            continue
        codigo = (VISOR / ruta).read_text(encoding="utf-8")

        def cambiar(m, ruta=ruta):
            destino = _resolver(m.group(3), ruta, mapa)
            if destino is None:
                return m.group(0)
            if not (VISOR / destino).is_file():
                raise FileNotFoundError(f"{ruta} importa {m.group(3)}: no existe app/visor3d/{destino}")
            pendientes.append(destino)
            return f"{m.group(1)}{m.group(2)}{destino}{m.group(2)}"

        listos[ruta] = _IMPORT.sub(cambiar, codigo)
    visor = listos.pop("visor.js")
    return visor, dict(sorted(listos.items()))


def _estilos_adentro(html: str) -> str:
    """<link rel="stylesheet" href="./x.css"> -> <style> con el contenido del archivo."""
    def poner(m):
        css = (VISOR / m.group(1)).read_text(encoding="utf-8")
        return f"<style>\n/* {m.group(1)} */\n{css.replace('</style', '<' + chr(92) + '/style')}</style>"
    return re.sub(r'<link rel="stylesheet" href="\./([\w/-]+\.css)">', poner, html)


def _json_en_script(datos) -> str:
    # Un "</script>" dentro de los datos cerraria la etiqueta antes de tiempo.
    return json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def generar() -> Path:
    puerto = yaml.safe_load((RAIZ / "config" / "parametros.yaml").read_text(encoding="utf-8"))["supervisor"]["puerto_http"]
    html = (VISOR / "index.html").read_text(encoding="utf-8")
    visor, locales = _modulos(html)
    three = (VISOR / "vendor" / "three.module.min.js").read_text(encoding="utf-8")
    demo = {n: json.loads((VISOR / "demo" / f"{n}.json").read_text(encoding="utf-8"))
            for n in ("geometria", "pasos", "grabacion")}
    importmap = {"three": _modulo(three), **{n: _modulo(c) for n, c in locales.items()}}

    html = _estilos_adentro(html)
    inicio = html.index('<script type="importmap">')
    fin = html.index("</script>", html.index('<script type="module"')) + len("</script>")
    scripts = (
        "<!-- visor-portable.html: GENERADO por `python -m app.portable` (no editar a mano). -->\n"
        f"<script>window.__URL_VIVO = 'http://127.0.0.1:{puerto}/';\n"
        f"window.__DEMO = {_json_en_script(demo)};</script>\n"
        '<script type="importmap">\n'
        + json.dumps({"imports": importmap})
        + "\n</script>\n"
        f'<script type="module">\n{visor.replace("</script", "<" + chr(92) + "/script")}\n</script>'
    )
    SALIDA.write_text(html[:inicio] + scripts + html[fin:], encoding="utf-8")
    return SALIDA


def main() -> None:
    ruta = generar()
    if "--silencioso" not in sys.argv:
        print(f"{ruta.relative_to(RAIZ)} ({ruta.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
