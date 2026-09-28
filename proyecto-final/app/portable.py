"""Arma `visor-portable.html`: el visor 3D en UN solo archivo (usuario, 2026-09-27).

Lo que hace visor.bat: abre este archivo al instante y arranca la simulación por detrás.

- Abierto solo (doble clic, otro PC, sin Python ni internet): muestra la demo grabada
  (app/visor3d/demo/, la graba `python -m app.grabar_demo`).
- Mientras tanto le pregunta cada 3 s a la simulación de ESTE PC (127.0.0.1, el puerto de
  config/parametros.yaml). Cuando responde, la pestaña pasa sola al visor en vivo.

Por qué un solo archivo: el navegador no deja que una página abierta como archivo (file://)
cargue módulos de JavaScript sueltos ni lea .json de la carpeta. Aquí va todo adentro: Three.js
y OrbitControls como módulos embebidos (data: URLs en el importmap), las piezas de
app/visor3d/piezas/*.js (también en el importmap, como `piezas/<archivo>.js`), el visor y la demo.

    python -m app.portable            # escribe visor-portable.html en la raíz del proyecto
"""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
VISOR = RAIZ / "app" / "visor3d"
SALIDA = RAIZ / "visor-portable.html"


def _modulo(codigo: str) -> str:
    return "data:text/javascript;base64," + base64.b64encode(codigo.encode("utf-8")).decode("ascii")


# `from './piezas/x.js'` (en visor.js) o `from './x.js'` (entre piezas) -> `from 'piezas/x.js'`:
# un módulo que viene de una data: URL no puede resolver rutas relativas, así que todo import
# local pasa a ser un nombre del importmap. `three` ya es un nombre del importmap.
_IMPORT_LOCAL = re.compile(r"""(\bfrom\s*|\bimport\s*\(?\s*)(['"])\./(?:piezas/)?([\w-]+\.js)\2""")


def _a_importmap(codigo: str) -> str:
    return _IMPORT_LOCAL.sub(lambda m: f"{m.group(1)}{m.group(2)}piezas/{m.group(3)}{m.group(2)}", codigo)


def _json_en_script(datos) -> str:
    # Un "</script>" dentro de los datos cerraria la etiqueta antes de tiempo.
    return json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def generar() -> Path:
    puerto = yaml.safe_load((RAIZ / "config" / "parametros.yaml").read_text(encoding="utf-8"))["supervisor"]["puerto_http"]
    html = (VISOR / "index.html").read_text(encoding="utf-8")
    visor = (VISOR / "visor.js").read_text(encoding="utf-8")
    visor = visor.replace("from './vendor/OrbitControls.js'", "from 'three/addons/OrbitControls.js'")
    visor = _a_importmap(visor)
    three = (VISOR / "vendor" / "three.module.min.js").read_text(encoding="utf-8")
    orbit = (VISOR / "vendor" / "OrbitControls.js").read_text(encoding="utf-8")
    piezas = {f"piezas/{r.name}": _modulo(_a_importmap(r.read_text(encoding="utf-8")))
              for r in sorted((VISOR / "piezas").glob("*.js"))}
    demo = {n: json.loads((VISOR / "demo" / f"{n}.json").read_text(encoding="utf-8"))
            for n in ("geometria", "pasos", "grabacion")}

    inicio = html.index('<script type="importmap">')
    fin = html.index("</script>", html.index('<script type="module"')) + len("</script>")
    scripts = (
        "<!-- visor-portable.html: GENERADO por `python -m app.portable` (no editar a mano). -->\n"
        f"<script>window.__URL_VIVO = 'http://127.0.0.1:{puerto}/';\n"
        f"window.__DEMO = {_json_en_script(demo)};</script>\n"
        '<script type="importmap">\n'
        + json.dumps({"imports": {"three": _modulo(three), "three/addons/OrbitControls.js": _modulo(orbit), **piezas}})
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
