"""Genera la documentacion para GitHub a partir de sus fuentes unicas:

- docs/paso-a-paso.md          <- docs/paso-a-paso.yaml
- docs/replicacion.md          <- config/*.yaml + catalogo + presupuesto de tiempos
- docs/componentes.md          <- sim/catalogos.py (lista de materiales)
- docs/sensores.md             <- sim/catalogos.py (un apartado por sensor)

No editar esos .md a mano: se sobrescriben. Se corre despues de cambiar el
YAML del paso a paso (por ejemplo, al aprobar un punto) o el catalogo:

    python -m app.documentos
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from sim.catalogos import CATALOGO_SENSORES

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
AVISO = "<!-- Generado por `python -m app.documentos`. No editar a mano. -->\n\n"
ICONO = {"pendiente": "⏳ pendiente", "preaprobado": "🔵 preaprobado", "aprobado": "✅ aprobado", "cambiar": "✏️ por cambiar", "pausa": "⏸️ en pausa (montaje real)"}


def _ancla(paso: dict) -> str:
    """Ancla que GitHub le da al titulo `## N. Titulo`: minusculas, fuera la
    puntuacion, espacios a guiones. OJO: GitHub CONSERVA los acentos
    ("estación"), por eso no se puede reusar `_slug`, que los quita."""
    texto = f"{paso['numero']}. {paso['titulo']}".lower()
    return re.sub(r"[^\w\- ]", "", texto).replace(" ", "-")


def ancla_sensor(sensor: dict) -> str:
    """Ancla del titulo `## N. Nombre` en docs/sensores.md (GitHub conserva
    los acentos)."""
    texto = f"{sensor['numero']}. {sensor['nombre']}".lower()
    return re.sub(r"[^\w\- ]", "", texto).replace(" ", "-")


def _cargar_pasos() -> list[dict]:
    with open(DOCS / "paso-a-paso.yaml", encoding="utf-8") as archivo:
        return yaml.safe_load(archivo)["pasos"]


def generar_paso_a_paso(pasos: list[dict]) -> str:
    catalogo = {s["numero"]: s for s in CATALOGO_SENSORES}
    lineas = [AVISO, "# Paso a paso del sistema\n",
              "Cada punto de la secuencia de operación (sección 5 de `CLAUDE.md`), con el sensor que usa, "
              "qué entra, qué decide y qué sale. El estado de revisión dice si el grupo ya confirmó la lógica.\n",
              "Para verlo en 3D: doble clic en `visor.bat` (pestaña Paso a paso del visor).\n",
              "| # | Punto | Sensores | Revisión |", "|---|---|---|---|"]
    for p in pasos:
        sens = ", ".join(
            f"[{n}](sensores.md#{ancla_sensor(catalogo[n])})" for n in p.get("sensores", []) if n in catalogo
        ) or "—"
        lineas.append(f"| {p['numero']} | [{p['titulo']}](#{_ancla(p)}) | {sens} | "
                      f"{ICONO.get(p['revision'], p['revision'])} |")
    lineas.append("")
    for p in pasos:
        lineas += [f"## {p['numero']}. {p['titulo']}\n", f"**Revisión:** {ICONO.get(p['revision'], p['revision'])}\n",
                   p["que_pasa"].strip() + "\n",
                   f"- **Entra:** {p['entra']}", f"- **Decide:** {p['decide'].strip()}", f"- **Sale:** {p['sale']}"]
        sens = [catalogo[n] for n in p.get("sensores", []) if n in catalogo]
        if sens:
            lineas.append("- **Sensores:** " + ", ".join(
                f"[{s['numero']}. {s['nombre']}](sensores.md#{ancla_sensor(s)})" for s in sens))
        lineas.append("")
        if p.get("mensaje"):
            lineas += ["```json", p["mensaje"], "```", ""]
        if p.get("como_esta_hoy"):
            lineas += [f"**Cómo está implementado hoy:** {p['como_esta_hoy'].strip()}", ""]
        if p.get("replicacion"):
            lineas += [f"**Para replicarlo en la vida real:** {p['replicacion'].strip()} "
                       "(detalle en [replicacion.md](replicacion.md))", ""]
        if p.get("preguntas"):
            lineas += ["**Por revisar con el grupo:**", ""] + [f"- {q}" for q in p["preguntas"]] + [""]
        if p.get("nota_revision"):
            lineas += [f"**Nota de revisión:** {p['nota_revision'].strip()}", ""]
    return "\n".join(lineas)


def generar_sensores(pasos: list[dict]) -> str:
    """docs/sensores.md: un apartado por sensor, numerados igual que en el
    visor 3D (pestaña Sensores)."""
    lineas = [AVISO, "# Sensores del proyecto\n",
              "Numerados igual que en el visor 3D (pestaña Sensores). Qué lo activa, qué recibe y entrega, "
              "qué mensaje manda al PC, cómo se replica y cómo se simula.\n",
              "| # | Sensor | Subsistema | Modelo propuesto |", "|---|---|---|---|"]
    for s in CATALOGO_SENSORES:
        lineas.append(f"| {s['numero']} | [{s['nombre']}](#{ancla_sensor(s)}) | {s['subsistema']} | {s['modelo']} |")
    lineas.append("")
    for sensor in CATALOGO_SENSORES:
        en_pasos = [p for p in pasos if sensor["numero"] in p.get("sensores", [])]
        lineas += [f"## {sensor['numero']}. {sensor['nombre']}\n",
                   f"**Subsistema:** {sensor['subsistema']} · **Dónde:** {sensor['estacion']} · "
                   f"**Modelo propuesto:** {sensor['modelo']}\n",
                   f"- **Qué lo activa:** {sensor['fenomeno']}",
                   f"- **Recibe:** {sensor['entrada']}", f"- **Entrega:** {sensor['salida']}",
                   f"- **Rango:** {sensor['rango']} · **Respuesta:** {sensor['tiempo_respuesta']}",
                   f"- **Error típico:** {sensor['error_tipico']}", f"- **Cómo mitigarlo:** {sensor['mitigacion']}",
                   f"- **Conexión:** {sensor['conexion']}",
                   f"- **Cómo se simula:** {sensor['simulacion']}"]
        if en_pasos:
            lineas.append("- **Pasos:** " + ", ".join(
                f"[{p['numero']}. {p['titulo']}](paso-a-paso.md#{_ancla(p)})" for p in en_pasos))
        lineas += ["", "```json", sensor["mensaje"], "```", ""]
    lineas.append("Valores PROVISIONALES (hoja de datos): se miden como dice [replicacion.md](replicacion.md).")
    return "\n".join(lineas) + "\n"


# ---------------------------------------------------------------------
# docs/replicacion.md: todo lo que hay que medir para construirlo de verdad
# ---------------------------------------------------------------------

def _medidas_provisionales(p: dict) -> list[tuple[str, str, str, str]]:
    """(que, valor actual, donde se cambia, como medirlo)."""
    from sim import mundo

    v, c, veh, pl = p["vasos"], p["canaleta"], p["vehiculo"], p["planta"]
    return [
        ("Altura del vaso", f"{v['altura_mm']} mm", "config/parametros.yaml · vasos.altura_mm",
         "Calibrador sobre 3 vasos del lote que se va a usar."),
        ("Diámetro exterior del vaso", f"{v['diametro_mm']} mm", "vasos.diametro_mm",
         "Calibrador en la boca y en la base (se usa el mayor)."),
        ("Separación entre casillas de la cinta de vasos", f"{v['separacion_casilla_mm']} mm",
         "vasos.separacion_casilla_mm + sim/urdf/cinta_vasos.urdf", "Diámetro del vaso + 15 mm de margen, en el CAD."),
        ("Altura del separador de la cinta de vasos", f"{v['separador_altura_mm']} mm", "vasos.separador_altura_mm",
         "Del CAD: por debajo del reborde para que el vaso pueda colgarse en la canaleta."),
        ("Motor paso a paso de las cintas", v.get("modelo", p["motor_paso_a_paso"]["modelo"]), "motor_paso_a_paso.modelo",
         "Confirmar el torque con la cinta cargada antes de elegir driver."),
        ("Altura de la mesa de la cinta de monedas", f"{mundo.ALTURA_MESA_MONEDAS * 1000:.0f} mm",
         "sim/mundo.py · ALTURA_MESA_MONEDAS", "Del CAD: tiene que quedar sobre el selector y los tubos."),
        ("Altura de la mesa de la cinta de vasos", f"{mundo.ALTURA_MESA_VASOS * 1000:.0f} mm",
         "sim/mundo.py · ALTURA_MESA_VASOS", "Del CAD: el vaso colgado al final de la canaleta no puede tocar el piso."),
        ("Tubos del almacén (diámetro interior y alto)",
         f"{mundo.TUBO_RADIO_M * 2000:.0f} mm x {mundo.TUBO_ALTO_M * 1000:.0f} mm", "sim/mundo.py · TUBO_*",
         "Interior 2 mm mayor que la moneda más grande (1000 nueva, 26,7 mm)."),
        ("Capacidad de cada tubo", f"{pl['capacidad_tubo']} monedas", "planta.capacidad_tubo",
         "Alto útil del tubo / 2,2 mm por moneda (medir la pila real)."),
        ("Monedas por vaso (lote)", f"{pl['monedas_por_vaso']}", "planta.monedas_por_vaso",
         "Decisión del grupo; el enunciado no lo fija."),
        ("Largo de la canaleta de entrega", f"{c['largo_mm']} mm", "canaleta.largo_mm",
         "Del CAD; con 15° cada 100 mm baja 27 mm."),
        ("Separación entre rieles de la canaleta", f"{c['separacion_rieles_mm']} mm", "canaleta.separacion_rieles_mm",
         "Mayor que el cuerpo del vaso y menor que su reborde."),
        ("Trazado de la pista", f"{len(p['pista']['tramos'])} tramos, muros en {p['pista']['obstaculos_mm']} mm",
         "pista.tramos / pista.obstaculos_mm", "Medir la pista real con cinta métrica (radios y largos)."),
        ("Dimensiones del carro", f"{veh['largo_mm']} x {veh['ancho_mm']} mm, rueda {veh['diametro_rueda_mm']} mm",
         "vehiculo.*", "Del chasis comprado o del CAD."),
        ("Tiempo máximo de reacción de la cortina", f"{p['cortina_seguridad']['reaccion_max_ms']} ms",
         "cortina_seguridad.reaccion_max_ms", "Con la velocidad real de la leva de la prensa."),
    ]


def generar_replicacion() -> str:
    from app.configuracion import cargar_parametros
    from control import monedas as tabla
    from control.tiempos import presupuesto

    p = cargar_parametros()
    t, errores = p["tiempos_ms"], p["errores_sensores"]
    r = presupuesto(t, lote=p["planta"]["monedas_por_vaso"],
                    lecturas_por_decision=p["planta"]["lecturas_por_decision"],
                    fotos_por_moneda=p["planta"]["fotos_por_moneda"],
                    reaccion_cortina_max_ms=p["cortina_seguridad"]["reaccion_max_ms"])
    L = [AVISO, "# Replicación en la vida real\n",
         "Todo lo que la simulación supone y que hay que **medir en el montaje real** antes de dar el diseño "
         "por cerrado: medidas físicas, monedas, sensores con su error individual y tiempos. Cada valor tiene "
         "su lugar en la configuración: al medirlo, se cambia ahí y se vuelve a generar este documento "
         "(`python -m app.documentos`).\n",
         "Estado de hoy: **todos los valores de esta página son PROVISIONALES** salvo las 9 monedas marcadas "
         "como verificadas. Salen de hojas de datos y valores típicos, no de mediciones propias.\n",
         "## 1. Medidas físicas por confirmar\n",
         "| Qué | Valor provisional | Dónde se cambia | Cómo medirlo |", "|---|---|---|---|"]
    for que, valor, donde, como in _medidas_provisionales(p):
        L.append(f"| {que} | {valor} | `{donde}` | {como} |")

    L += ["", "## 2. Monedas\n",
          f"{len(tabla.TABLA_MONEDAS)} clases en 4 generaciones (`config/monedas.yaml`). Las no verificadas hay que "
          "medirlas: diámetro con calibrador (+-0,02 mm) en 3 direcciones y masa con báscula de 0,01 g, al menos 5 "
          "piezas por clase, incluidas gastadas. Van al tubo de su denominación; las denominaciones sin tubo "
          f"(todas menos {', '.join('$' + str(d) for d in tabla.DENOMINACIONES_CON_TUBO)}) van al compartimiento "
          "\"otras\": se guardan, no se empacan.\n",
          "| Clase | Familia | Diámetro (mm) | Masa (g) | Material | Estado |", "|---|---|---|---|---|---|"]
    for m in tabla.TABLA_MONEDAS:
        estado = "verificada" if m.verificado else "**PROVISIONAL: medir**"
        L.append(f"| {m.clase} | {m.familia} | {m.diametro_mm} | {m.masa_g} | {m.material} | {estado} |")

    L += ["", "## 3. Sensores: error individual y cómo medirlo\n",
          "La simulación reproduce el error de cada sensor con las probabilidades de `errores_sensores` "
          "(por lectura). Cada estación lee su sensor "
          f"{p['planta']['lecturas_por_decision']} veces durante la pausa y decide por mayoría, lo que baja "
          "una probabilidad p por lectura a ~3p² por decisión.\n",
          "**Prueba de banco (200 pasadas):** pasar el mismo elemento 200 veces por el sensor y contar las "
          "veces que no lo ve (falsos negativos / 200); pasar 200 veces la casilla vacia y contar las veces que "
          "ve algo (falsos positivos / 200). Repetir con cada tipo de pieza (moneda de cada familia, botón de "
          "plástico, botón metálico, vaso) y anotar el peor caso.\n",
          "| # | Sensor | Rango | Respuesta | Error típico | Error simulado | Mitigación | Conexión |",
          "|---|---|---|---|---|---|---|---|"]
    for s in CATALOGO_SENSORES:
        e = errores.get(s.get("error_config") or "", {})
        if "falso_negativo" in e:
            simulado = f"FN {e['falso_negativo']:.1%}, FP {e['falso_positivo']:.1%}"
        elif "no_lee" in e:
            simulado = f"no lee el marcador {e['no_lee']:.0%} (2 intentos por lectura)"
        elif "ruido_g" in e:
            simulado = f"ruido ±{e['ruido_g']} g por lectura (se promedian varias)"
        elif "ruido_diametro_mm" in e:
            simulado = (f"diámetro ±{e['ruido_diametro_mm']} mm, clase {e['probabilidad_error_clase']:.0%}")
        elif s.get("subsistema") == "carro":
            simulado = "pendiente (puntos 13-14)"
        else:
            simulado = "sin error simulado"
        L.append(f"| {s['numero']} | [{s['nombre']}](sensores.md#{ancla_sensor(s)}) | {s['rango']} | "
                 f"{s['tiempo_respuesta']} | {s['error_tipico']} | {simulado} | {s['mitigacion']} | {s['conexion']} |")

    L += ["", "## 4. Tiempos\n",
          "Valores de `tiempos_ms`. **Cómo medirlos:** en el firmware, marcar con `millis()`/`micros()` el inicio y "
          "fin de cada acción y mandarlo en el campo `ms` de los eventos (sección 10.1); para la ida y vuelta por "
          "serial, un `ping` desde el PC con marca de tiempo.\n",
          "| Acción | Tiempo (ms) |", "|---|---|"]
    for clave, valor in t.items():
        L.append(f"| {clave.replace('_', ' ')} | {valor} |")
    L += ["", "### Presupuesto: ¿cabe cada acción en su hueco?\n",
          f"Ciclo de la cinta de monedas: **{r['ciclo_monedas_ms']} ms** (≈ {r['elementos_por_minuto']:.0f} elementos "
          f"por minuto). Ciclo mínimo de la cinta de vasos: **{r['ciclo_vasos_ms']} ms**. Reacción de la cortina: "
          f"**{r['reaccion_cortina_ms']} ms**.\n",
          "| Chequeo | Necesita (ms) | Disponible (ms) | Margen | Estado | Por qué |", "|---|---|---|---|---|---|"]
    for ch in r["chequeos"]:
        L.append(f"| {ch.nombre} | {ch.necesita_ms:.0f} | {ch.disponible_ms:.0f} | {ch.margen_ms:+.0f} | "
                 f"{'OK' if ch.ok else '**NO CABE**'} | {ch.explicacion} |")
    L += ["", "Si al medir un tiempo real algún chequeo queda en **NO CABE**, las salidas son: alargar la pausa "
          "(`pausa_casilla_monedas`, baja la producción), un servo más rápido, o bajar `lecturas_por_decision`."]
    return "\n".join(L) + "\n"


def generar_componentes() -> str:
    from sim.catalogos import CATEGORIAS, COMPONENTES

    total = sum(c["cantidad"] for c in COMPONENTES)
    servos = sum(c["cantidad"] for c in COMPONENTES if c["id"].startswith("servo"))
    L = [AVISO, "# Componentes (lista de materiales)\n",
         f"{total} piezas más los {len(CATALOGO_SENSORES)} sensores de [sensores.md](sensores.md). "
         f"Son {servos} servos: caben en un solo PCA9685 de 16 canales (sobran {16 - servos}). En el visor 3D, "
         "pestaña **Componentes**, cada uno se resalta en la escena "
         "(`http://localhost:8765/?componente=<id>`).\n",
         "**Estado en la simulación** (calculado en `sim/catalogos.py`, no escrito a mano): *simulado* = la "
         "simulación hace lo que hace la pieza; *efecto simulado* = su efecto lo hace otra pieza en la "
         "simulación (los drivers: la cinta avanza igual); *solo visual* = nada en la simulación depende de "
         "ella. La columna **Hilos** cuenta su conexionado pin a pin ([conexiones.md](conexiones.md)).\n"]
    for cat in CATEGORIAS:
        if cat == "Sensores":
            L += [f"## Sensores\n", f"Ver [sensores.md](sensores.md) ({len(CATALOGO_SENSORES)} sensores numerados).\n"]
            continue
        L += [f"## {cat}\n", "| Componente | Cant. | Modelo propuesto | Para qué sirve | Estado | Hilos |", "|---|---|---|---|---|---|"]
        for c in COMPONENTES:
            if c["categoria"] == cat:
                L.append(f"| {c['nombre']} (`{c['id']}`) | {c['cantidad']} | {c['modelo']} | {c['funcion']} | {c['estado']} | {c['hilos'] or '—'} |")
        L.append("")
    return "\n".join(L) + "\n"


def generar_conexiones() -> str:
    """Tabla de cada cable, hilo por hilo (como `conexiones.md` de los labs)."""
    from sim import conexiones as cx

    nombre = lambda ref: f"{cx.DISPOSITIVOS[ref.split('.', 1)[0]]['nombre']} · **{ref.split('.', 1)[1]}**"
    L = [AVISO, "# Conexiones (pin a pin)\n",
         "Fuente única: `sim/conexiones.py`. De ahí salen los cables del visor 3D (botón **Cables**) y esta "
         "tabla; `tests/test_conexiones.py` verifica que cada pin exista, que ningún pin de header reciba "
         "dos hilos, que los bornes lleven como mucho dos y que los GPIO sean los de la tabla de pines de "
         "[revision-final.md](revision-final.md).\n",
         "Convenciones: placas GVS con el jumper en 3,3 V (**G** = GND, **V** = 3,3 V, **S** = señal del GPIO). "
         "Bornera X2 con puentes 2-3 (+12 V sensores), 5-6 (+5 V) y 7 a 13 (GND en estrella).\n"]
    for zona, titulo in (("caja", "Caja de control"), ("planta", "Planta (campo)"), ("carro", "Carro")):
        L.append(f"## {titulo}\n")
        for c in cx.CABLES:
            devs = {e.split(".", 1)[0] for h in c["hilos"] for e in (h["de"], h["a"])}
            zonas = {cx.DISPOSITIVOS[d]["zona"] for d in devs}
            principal = "carro" if "carro" in zonas else "planta" if "planta" in zonas else "caja"
            if principal != zona or not c["hilos"]:
                continue
            extra = f" · conector {c['conector']}" if c.get("conector") else ""
            L += [f"### {c['nombre']}{extra}\n", "| Hilo | De | A | Función |", "|---|---|---|---|"]
            for h in c["hilos"]:
                L.append(f"| <span style=\"color:{h['color']}\">■</span> | {nombre(h['de'])} | {nombre(h['a'])} | {h['funcion']} |")
            L.append("")
    return "\n".join(L) + "\n"


def generar_todo() -> list[Path]:
    pasos = _cargar_pasos()
    escritos = []
    destino = DOCS / "paso-a-paso.md"
    destino.write_text(generar_paso_a_paso(pasos), encoding="utf-8")
    escritos.append(destino)
    destino = DOCS / "replicacion.md"
    destino.write_text(generar_replicacion(), encoding="utf-8")
    escritos.append(destino)
    destino = DOCS / "componentes.md"
    destino.write_text(generar_componentes(), encoding="utf-8")
    escritos.append(destino)
    destino = DOCS / "sensores.md"
    destino.write_text(generar_sensores(pasos), encoding="utf-8")
    escritos.append(destino)
    destino = DOCS / "conexiones.md"
    destino.write_text(generar_conexiones(), encoding="utf-8")
    escritos.append(destino)
    from app import costos

    destino = DOCS / "costos.md"
    destino.write_text(costos.generar_md(), encoding="utf-8")
    escritos.append(destino)
    return escritos


if __name__ == "__main__":
    for ruta in generar_todo():
        print(ruta.relative_to(RAIZ))
