"""visor-portable.html: un solo archivo que funciona sin servidor y pasa solo al visor en vivo."""

import base64
import json
import re

from app import portable


def _html():
    return portable.generar().read_text(encoding="utf-8")


def test_todo_va_adentro_del_archivo():
    html = _html()
    # Nada que el navegador tenga que ir a buscar a la carpeta (file:// no lo deja).
    assert "./vendor/" not in html and "src=\"./visor.js\"" not in html
    mapa = json.loads(re.search(r'<script type="importmap">\s*(.*?)\s*</script>', html, re.S).group(1))
    assert set(mapa["imports"]) == {"three", "three/addons/OrbitControls.js"}
    orbit = base64.b64decode(mapa["imports"]["three/addons/OrbitControls.js"].split(",", 1)[1]).decode()
    assert "OrbitControls" in orbit
    assert "from 'three/addons/OrbitControls.js'" in html


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
    assert "--abrir" not in bat   # la pestaña ya esta abierta: pasa sola al visor en vivo
