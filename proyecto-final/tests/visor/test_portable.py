"""visor-portable.html: un solo archivo que funciona sin servidor y pasa solo al visor en vivo."""

import base64
import json
import re

from app import portable


def _html():
    return portable.generar().read_text(encoding="utf-8")


def _mapa(html):
    return json.loads(re.search(r'<script type="importmap">\s*(.*?)\s*</script>', html, re.S).group(1))["imports"]


def test_todo_va_adentro_del_archivo():
    html = _html()
    # Nada que el navegador tenga que ir a buscar a la carpeta (file:// no lo deja).
    assert "./vendor/" not in html and "src=\"./visor.js\"" not in html
    assert '<link rel="stylesheet" href="./' not in html
    mapa = _mapa(html)
    fuente = (portable.VISOR / "visor.js").read_text(encoding="utf-8")
    piezas = set(re.findall(r"from '\./(piezas/[\w-]+\.js)'", fuente)) | {"piezas/base.js"}
    assert "piezas/electronica.js" in piezas
    # La interfaz, las piezas y OrbitControls: todo modulo local que visor.js alcanza.
    assert {"three", "interfaz.js", "vendor/OrbitControls.js"} | piezas <= set(mapa)
    orbit = base64.b64decode(mapa["vendor/OrbitControls.js"].split(",", 1)[1]).decode()
    assert "OrbitControls" in orbit
    assert "from 'vendor/OrbitControls.js'" in html
    assert "from 'interfaz.js'" in html


def test_el_estilo_va_adentro():
    # estilo.css (el sistema de diseno de la interfaz) pasa a un <style> dentro del archivo.
    html = _html()
    css = (portable.VISOR / "estilo.css").read_text(encoding="utf-8")
    assert "--ambar: #f2b134" in css
    assert css.strip()[-60:] in html


def test_los_modulos_van_embebidos_sin_rutas_relativas():
    # Un modulo de una data: URL no resuelve './x.js': todo import local pasa al importmap.
    html = _html()
    mapa = _mapa(html)
    visor = html[html.index('<script type="module">'):]
    assert "from 'piezas/electronica.js'" in visor
    assert not re.search(r"""from\s*['"]\.{1,2}/""", visor)
    for nombre, url in mapa.items():
        if nombre == "three":
            continue
        codigo = base64.b64decode(url.split(",", 1)[1]).decode()
        assert not re.search(r"""from\s*['"]\.{1,2}/""", codigo), nombre
        for usado in re.findall(r"""from\s*['"]([^'"]+)['"]""", codigo):
            assert usado in mapa, (nombre, usado)


def test_un_modulo_nuevo_entra_solo(tmp_path, monkeypatch):
    # Generalizado (2026-09-28): no hay lista fija de modulos; se siguen los imports (relativos o
    # por un nombre del importmap de index.html) y cada hoja de estilo local pasa a <style>.
    (tmp_path / "vendor").mkdir()
    (tmp_path / "sub").mkdir()
    (tmp_path / "index.html").write_text(
        '<html><head><link rel="stylesheet" href="./e.css"></head><body>'
        '<script type="importmap">{ "imports": { "three": "./vendor/three.module.min.js", "extra/": "./sub/" } }</script>'
        '<script type="module" src="./visor.js"></script></body></html>', encoding="utf-8")
    (tmp_path / "e.css").write_text("body { color: red; }", encoding="utf-8")
    (tmp_path / "visor.js").write_text(
        "import * as THREE from 'three';\nimport { a } from './sub/a.js';\nimport { c } from 'extra/c.js';\n", encoding="utf-8")
    (tmp_path / "sub" / "a.js").write_text("import { b } from '../b.js';\nexport const a = b;\n", encoding="utf-8")
    (tmp_path / "sub" / "c.js").write_text("export const c = 1;\n", encoding="utf-8")
    (tmp_path / "b.js").write_text("export const b = 1;\n", encoding="utf-8")
    (tmp_path / "vendor" / "three.module.min.js").write_text("export {};", encoding="utf-8")
    monkeypatch.setattr(portable, "VISOR", tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    visor, locales = portable._modulos(html)
    assert set(locales) == {"sub/a.js", "b.js", "sub/c.js"}
    assert "from 'sub/a.js'" in visor and "from 'sub/c.js'" in visor and "from 'three'" in visor
    assert "from 'b.js'" in locales["sub/a.js"]
    assert "body { color: red; }" in portable._estilos_adentro(html)


def test_la_demo_embebida_es_la_grabada():
    html = _html()
    datos = re.search(r"window.__DEMO = (.*?);</script>", html, re.S).group(1)
    demo = json.loads(datos.replace("<\\/", "</"))
    for nombre in ("geometria", "pasos", "grabacion"):
        original = json.loads((portable.VISOR / "demo" / f"{nombre}.json").read_text(encoding="utf-8"))
        assert demo[nombre] == original


def test_apunta_al_puerto_de_la_configuracion():
    from app.configuracion import cargar_parametros
    puerto = cargar_parametros()["supervisor"]["puerto_http"]
    assert f"window.__URL_VIVO = 'http://127.0.0.1:{puerto}/'" in _html()


def test_solo_cierran_los_tres_scripts():
    # Un "</script" dentro de la demo o del visor cortaria la pagina.
    assert _html().count("</script") == 3


def test_el_bat_abre_el_portable_y_arranca_la_simulacion():
    bat = (portable.RAIZ / "visor.bat").read_text(encoding="utf-8")
    assert "visor-portable.html" in bat and "app.lanzar" in bat
    # La pestaña del visor ya esta abierta (pasa sola a en vivo): no se abre otra. Si el dashboard.
    assert not re.search(r"--abrir(?!-)", bat)
    assert "--abrir-dashboard" in bat
