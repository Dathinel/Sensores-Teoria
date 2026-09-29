"""Costo del proyecto en Colombia (config/precios.yaml, fuente única).

Lo usan `app.documentos` (genera docs/costos.md), el dashboard (pestaña Montaje real), el
asistente (lee docs/costos.md y responde "cuánto cuesta" con el intérprete local) y
`app.masas` (reusa los gramos de las piezas impresas y los tramos de perfil).

La estructura 3D (usuario, 2026-09-28: "costos en estructura 3D completos, en tablas y todo") ya
no es un "2 kg de PLA y 3 m de perfil estimados": sale de `estructura_3d` en precios.yaml, con
cada pieza impresa, cada tramo de perfil y cada tornillo contados sobre el modelo 3D del visor.
Aquí solo está la cuenta; los datos (y de dónde salió cada uno) están en el YAML.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import yaml

RUTA = Path(__file__).resolve().parent.parent / "config" / "precios.yaml"
ORDEN_SUBSISTEMAS = ["Cinta de monedas", "Cinta de vasos", "Canaleta y muelle", "Carro", "Control y potencia",
                     "Estructura"]


def cargar() -> dict:
    return yaml.safe_load(RUTA.read_text(encoding="utf-8"))


def pesos(v: int) -> str:
    return f"${int(round(v)):,}".replace(",", ".")


def _num(v: float, dec: int = 1) -> str:
    """Número con coma decimal (como se escribe en Colombia): 12.5 -> '12,5'."""
    return f"{v:,.{dec}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")


# ---------------------------------------------------------------------------------------------
# Piezas impresas
# ---------------------------------------------------------------------------------------------

def factor_llenado(pieza: dict, imp: dict) -> float:
    """Fracción del volumen de la pieza que de verdad se llena de plástico.

    Una pieza impresa no es maciza: el laminador hace una cáscara sólida (perímetros, pisos y
    techos) y adentro un relleno en rejilla (20 %). Si la pieza es delgada (pared de 3 mm o
    menos) los 3 perímetros ya la llenan toda y el relleno no existe: factor 1. Si es gruesa, la
    cáscara ocupa `paredes` (~40 %) del volumen y el resto va al `relleno`:
        f = paredes + (1 - paredes) x relleno   ->  0,40 + 0,60 x 0,20 = 0,52
    """
    if pieza.get("maciza"):
        return 1.0
    return imp["paredes"] + (1 - imp["paredes"]) * imp["relleno"]


def piezas_impresas(datos: dict | None = None) -> list[dict]:
    """Cada pieza impresa con sus gramos, horas y costo (por unidad y por la cantidad).

    gramos = volumen x densidad x factor de llenado x (1 + desperdicio)
    horas  = gramos / gramos_por_hora
    costo  = gramos x precio_kg / 1000 (filamento) + horas x kWh por hora x tarifa (energía)
    """
    datos = datos or cargar()
    e3d = datos["estructura_3d"]
    imp = e3d["impresion"]
    out = []
    for p in e3d["piezas_impresas"]:
        f = factor_llenado(p, imp)
        gramos = p["volumen_cm3"] * imp["densidad_g_cm3"] * f * (1 + imp["desperdicio"])
        horas = gramos / imp["gramos_por_hora"]
        filamento = gramos * imp["precio_kg"] / 1000
        energia = horas * imp["kwh_por_hora"] * imp["tarifa_kwh"]
        n = p.get("cantidad", 1)
        out.append({**p, "cantidad": n, "zona": p.get("zona", p["subsistema"]), "factor": f,
                    "gramos": gramos, "horas": horas, "costo_filamento": filamento, "costo_energia": energia,
                    "costo": filamento + energia,
                    "gramos_total": gramos * n, "horas_total": horas * n, "costo_total": (filamento + energia) * n})
    return out


# ---------------------------------------------------------------------------------------------
# Perfil 2020: despiece en barras de 1 m
# ---------------------------------------------------------------------------------------------

def despiece_perfil(datos: dict | None = None) -> dict:
    """Acomoda los tramos medidos en barras de 1 m (el perfil se vende así).

    Método "primero el más largo" (first-fit decreasing): se ordenan los tramos de mayor a menor
    y cada uno va a la primera barra donde todavía cabe (su largo + el corte de la sierra); si no
    cabe en ninguna, se abre una barra nueva. No es el óptimo matemático, pero es lo que haría
    cualquiera en el taller con un metro y una sierra, y para ~30 tramos queda a 1 barra o menos
    del óptimo. Devuelve los tramos, las barras (lista de largos por barra) y el sobrante.
    """
    datos = datos or cargar()
    per = datos["estructura_3d"]["perfil"]
    L, corte = per["largo_barra_mm"], per["corte_mm"]
    tramos = [{**t, "cantidad": t.get("cantidad", 1)} for t in per["tramos"]]
    largos = sorted((t["largo_mm"] for t in tramos for _ in range(t["cantidad"])), reverse=True)
    barras: list[list[int]] = []
    for largo in largos:
        if largo > L:
            raise ValueError(f"un tramo de {largo} mm no cabe en una barra de {L} mm")
        for b in barras:
            usado = sum(b) + corte * len(b)          # cada tramo ya puesto se llevó un corte
            if usado + largo <= L:
                b.append(largo)
                break
        else:
            barras.append([largo])
    total_mm = sum(largos)
    return {"tramos": tramos, "barras": barras, "n_barras": len(barras), "total_mm": total_mm,
            "sobrante_mm": len(barras) * L - total_mm - corte * len(largos), "kg_por_m": per["kg_por_m"]}


# ---------------------------------------------------------------------------------------------
# Tornillería contada
# ---------------------------------------------------------------------------------------------

def conteo_tornilleria(datos: dict | None = None) -> dict[str, dict]:
    """Cuántos de cada tipo hay en el montaje: las uniones de la estructura de perfil más lo que
    lleva cada pieza impresa (por su cantidad). Devuelve por tipo: contados, a comprar (con el
    repuesto, redondeado hacia arriba), precio, subtotal y de dónde salen (para la tabla)."""
    datos = datos or cargar()
    tor = datos["estructura_3d"]["tornilleria"]
    tipos = tor["tipos"]
    cuenta: dict[str, int] = {t: 0 for t in tipos}
    origen: dict[str, list[str]] = {t: [] for t in tipos}
    for u in tor["uniones"]:
        for t, n in u["tornillos"].items():
            cuenta[t] += n
            origen[t].append(f"{u['zona']}: {n}")
    for p in datos["estructura_3d"]["piezas_impresas"]:
        for t, n in (p.get("tornillos") or {}).items():
            cuenta[t] += n * p.get("cantidad", 1)
    out = {}
    for t, d in tipos.items():
        contados = cuenta[t]
        comprar = math.ceil(contados * (1 + tor["repuesto"])) if contados else 0
        out[t] = {**d, "tipo": t, "contados": contados, "comprar": comprar, "subtotal": comprar * d["precio"]}
    return out


def tornillos_por_zona(datos: dict | None = None) -> dict[str, dict[str, int]]:
    """Tornillería contada (sin repuesto) por zona del peso: {zona: {tipo: cantidad}}."""
    datos = datos or cargar()
    e3d = datos["estructura_3d"]
    out: dict[str, dict[str, int]] = {}
    for u in e3d["tornilleria"]["uniones"]:
        z = out.setdefault(u["zona"], {})
        for t, n in u["tornillos"].items():
            z[t] = z.get(t, 0) + n
    for p in e3d["piezas_impresas"]:
        z = out.setdefault(p.get("zona", p["subsistema"]), {})
        for t, n in (p.get("tornillos") or {}).items():
            z[t] = z.get(t, 0) + n * p.get("cantidad", 1)
    return out


# ---------------------------------------------------------------------------------------------
# Filas de costo (lo que se compra)
# ---------------------------------------------------------------------------------------------

def filas(datos: dict | None = None) -> list[dict]:
    """Una fila por cosa que se compra, con su cantidad y subtotal. La cantidad
    que no esté en precios.yaml sale del catálogo (sim/catalogos.py).

    Filas calculadas (no escritas a mano):
      - `calculado: impresas` (un componente del catálogo que es una pieza impresa): su precio es
        la suma del costo de sus piezas en estructura_3d.piezas_impresas;
      - `calculado: perfileria`: la cantidad son las barras de 1 m del despiece;
      - "Otras piezas impresas" de cada subsistema: las piezas sin componente `calculado: impresas`;
      - una fila por tipo de tornillo/escuadra/pie, con lo contado + el repuesto.
    """
    from sim.catalogos import CATALOGO_SENSORES, COMPONENTES

    datos = datos or cargar()
    catalogo = {c["id"]: c for c in COMPONENTES}
    catalogo.update({s["id"]: s for s in CATALOGO_SENSORES})
    impresas = piezas_impresas(datos)
    imp = datos["estructura_3d"]["impresion"]
    out = []

    def fila(id_, nombre, subsistema, producto, cantidad, precio, fuente, tienda=None, grupo="items"):
        t = datos["tiendas"].get(tienda, {}) if tienda else {}
        out.append({"id": id_, "nombre": nombre, "subsistema": subsistema, "producto": producto,
                    "cantidad": cantidad, "precio": precio, "subtotal": precio * cantidad, "fuente": fuente,
                    "tienda": t.get("nombre", "—"), "url": t.get("url", ""), "grupo": grupo})

    for grupo in ("items", "extras"):
        for id_, d in (datos.get(grupo) or {}).items():
            c = catalogo.get(id_, {})
            cantidad = d.get("cantidad", c.get("cantidad", 1))
            precio = d.get("precio", 0)
            if d.get("calculado") == "impresas":
                mias = [p for p in impresas if p.get("componente") == id_]
                if not mias:
                    raise ValueError(f"{id_}: calculado: impresas, pero ninguna pieza impresa lo tiene de componente")
                precio, cantidad = round(sum(p["costo_total"] for p in mias)), 1
                gramos = sum(p["gramos_total"] for p in mias)
                d = {**d, "producto": f"{d['producto']}: {_num(gramos, 0)} g de PLA", "tienda": imp.get("tienda")}
            elif d.get("calculado") == "perfileria":
                cantidad = despiece_perfil(datos)["n_barras"]
            fila(id_, c.get("nombre", id_.replace("_", " ").capitalize()), d["subsistema"], d["producto"], cantidad,
                 precio, d["fuente"], d.get("tienda"), grupo)

    # Piezas impresas que no suman en la fila de un componente `calculado: impresas` (no tienen
    # componente, o su componente se compra aparte, como los tubos del almacén): una fila por
    # subsistema. Así cada pieza impresa queda contada UNA vez.
    con_fila = {i for i, d in (datos.get("items") or {}).items() if d.get("calculado") == "impresas"}
    for s in ORDEN_SUBSISTEMAS:
        sueltas = [p for p in impresas if p.get("componente") not in con_fila and p["subsistema"] == s]
        if not sueltas:
            continue
        n = sum(p["cantidad"] for p in sueltas)
        g = sum(p["gramos_total"] for p in sueltas)
        fila(f"impresas_{_slug(s)}", "Otras piezas impresas", s,
             f"{n} piezas en PLA ({_num(g, 0)} g, {_num(sum(p['horas_total'] for p in sueltas))} h de impresora): "
             "soportes, bridas, bloques (tabla de piezas impresas)",
             1, round(sum(p["costo_total"] for p in sueltas)), "estimado", imp.get("tienda"), "estructura_3d")
    # Tornillería, escuadras y pies: contados en el modelo.
    for t, d in conteo_tornilleria(datos).items():
        if d["comprar"]:
            fila(f"tornilleria_{t}", d["nombre"], "Estructura",
                 f"{d['contados']} contados en el modelo + {datos['estructura_3d']['tornilleria']['repuesto']:.0%} de repuesto",
                 d["comprar"], d["precio"], d["fuente"], d.get("tienda"), "estructura_3d")
    return out


def por_subsistema(datos: dict | None = None) -> dict[str, int]:
    tot = {s: 0 for s in ORDEN_SUBSISTEMAS}
    for f in filas(datos):
        tot[f["subsistema"]] = tot.get(f["subsistema"], 0) + f["subtotal"]
    return tot


def total(datos: dict | None = None) -> int:
    return sum(f["subtotal"] for f in filas(datos))


def costo_estructura_3d(datos: dict | None = None) -> dict:
    """Lo que cuesta la estructura 3D completa: piezas impresas (filamento + energía), perfil 2020
    en barras y tornillería/escuadras/pies. Es parte del total (no se suma aparte)."""
    datos = datos or cargar()
    fs = filas(datos)
    impresas = sum(f["subtotal"] for f in fs
                   if f["id"].startswith("impresas_") or (datos["items"].get(f["id"], {}).get("calculado") == "impresas"))
    perfil = sum(f["subtotal"] for f in fs if datos["items"].get(f["id"], {}).get("calculado") == "perfileria")
    tornilleria = sum(f["subtotal"] for f in fs if f["id"].startswith("tornilleria_"))
    ps = piezas_impresas(datos)
    return {"impresas": impresas, "perfil": perfil, "tornilleria": tornilleria,
            "total": impresas + perfil + tornilleria,
            "gramos_pla": sum(p["gramos_total"] for p in ps), "horas": sum(p["horas_total"] for p in ps),
            "piezas": sum(p["cantidad"] for p in ps)}


def ahorros(datos: dict | None = None) -> list[dict]:
    datos = datos or cargar()
    return sorted(datos.get("ahorros") or [], key=lambda a: -a["ahorro"])


# ---------------------------------------------------------------------------------------------
# docs/costos.md
# ---------------------------------------------------------------------------------------------

def _md_estructura_3d(datos: dict) -> list[str]:
    """Secciones de la estructura 3D: resumen, piezas impresas, perfilería y tornillería."""
    e3d = datos["estructura_3d"]
    imp = e3d["impresion"]
    ps = piezas_impresas(datos)
    c3d = costo_estructura_3d(datos)
    desp = despiece_perfil(datos)
    tor = conteo_tornilleria(datos)
    f_hueca = imp["paredes"] + (1 - imp["paredes"]) * imp["relleno"]
    L = [
        "## Estructura 3D (piezas impresas, perfil 2020 y tornillería)", "",
        f"Contada sobre el modelo 3D del visor (medido el {e3d['consultado']}): cada pieza impresa con su volumen, cada "
        "tramo de perfil con su largo y cada tornillo por pieza. Ya está dentro del total de arriba (en su subsistema).", "",
        "| Parte | Qué es | Costo | % de la estructura 3D |", "|---|---|---:|---:|",
        f"| Piezas impresas | {c3d['piezas']} piezas, {_num(c3d['gramos_pla'], 0)} g de PLA, "
        f"{_num(c3d['horas'])} h de impresora | {pesos(c3d['impresas'])} | {c3d['impresas'] * 100 / max(c3d['total'], 1):.0f} % |",
        f"| Perfil 2020 | {_num(desp['total_mm'] / 1000, 2)} m en {len([1 for t in desp['tramos'] for _ in range(t['cantidad'])])} "
        f"tramos → {desp['n_barras']} barras de 1 m | {pesos(c3d['perfil'])} | {c3d['perfil'] * 100 / max(c3d['total'], 1):.0f} % |",
        f"| Tornillería, escuadras y pies | {sum(d['comprar'] for d in tor.values())} unidades (con repuesto) | "
        f"{pesos(c3d['tornilleria'])} | {c3d['tornilleria'] * 100 / max(c3d['total'], 1):.0f} % |",
        f"| **Total estructura 3D** | | **{pesos(c3d['total'])}** | 100 % |", "",
        "### Cómo se calcula una pieza impresa", "",
        "```",
        "gramos = V x ρ x f x (1 + desperdicio)",
        f"  V   = volumen de material de la pieza en el modelo (cm³)",
        f"  ρ   = {_num(imp['densidad_g_cm3'], 2)} g/cm³ (PLA)",
        f"  f   = 1 si la pieza es maciza (pared ≤ 3 mm: los 3 perímetros la llenan)",
        f"      = paredes + (1 - paredes) x relleno = {_num(imp['paredes'], 2)} + {_num(1 - imp['paredes'], 2)} x "
        f"{_num(imp['relleno'], 2)} = {_num(f_hueca, 2)} si es gruesa",
        f"  desperdicio = {imp['desperdicio']:.0%} (purga, falda, soportes, alguna fallida)",
        f"horas = gramos / {imp['gramos_por_hora']} g/h",
        f"costo = gramos x {pesos(imp['precio_kg'])}/kg  +  horas x {_num(imp['kwh_por_hora'], 2)} kWh/h x "
        f"{pesos(imp['tarifa_kwh'])}/kWh",
        "```", "",
        f"*Estimados*: el {imp['paredes']:.0%} de cáscara, {imp['gramos_por_hora']} g/h, "
        f"{_num(imp['kwh_por_hora'], 2)} kWh/h y la tarifa de {pesos(imp['tarifa_kwh'])}/kWh (mírela en su recibo). "
        "Volumen \"malla\" = medido sumando los tetraedros de la malla del visor; \"estimado\" = calculado a mano "
        "con superficie x pared (la columna *Cómo* dice la cuenta).", "",
        "### Piezas impresas", "",
        "| Pieza | Dónde | Cant. | Medidas (mm) | Volumen (cm³) | Llenado | g c/u | h c/u | Costo c/u | Subtotal |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for p in ps:
        med = " x ".join(str(m) for m in p["medidas_mm"])
        vol = f"{_num(p['volumen_cm3'])}" + ("" if p["origen"] == "malla" else " *(est.)*")
        L.append(f"| {p['nombre']} | {p['zona']} | {p['cantidad']} | {med} | {vol} | {p['factor']:.0%} | "
                 f"{_num(p['gramos'])} | {_num(p['horas'], 2)} | {pesos(p['costo'])} | {pesos(p['costo_total'])} |")
    L.append(f"| **Total** | | **{c3d['piezas']}** | | | | **{_num(c3d['gramos_pla'], 0)} g** | "
             f"**{_num(c3d['horas'])} h** | | **{pesos(sum(p['costo_total'] for p in ps))}** |")
    estimadas = [p for p in ps if p.get("como")]
    if estimadas:
        L += ["", "**Cómo** (piezas con volumen estimado o sumado de varias mallas):", ""]
        L += [f"- {p['nombre']}: {p['como']}." for p in estimadas]
    kg = c3d["gramos_pla"] / 1000
    L += ["", f"Filamento: {_num(kg, 2)} kg → **{math.ceil(kg)} rollo(s) de 1 kg** (antes se estimaban 2).", ""]
    # Perfil
    L += ["### Perfil 2020 por tramo", "",
          f"Largo medido en el modelo; se compra en barras de {datos['estructura_3d']['perfil']['largo_barra_mm']} mm "
          f"con {datos['estructura_3d']['perfil']['corte_mm']} mm por corte de sierra.", "",
          "| Tramo | Zona | Cant. | Largo (mm) | Subtotal (mm) |", "|---|---|---:|---:|---:|"]
    for t in desp["tramos"]:
        L.append(f"| {t['nombre']} | {t['zona']} | {t['cantidad']} | {t['largo_mm']} | {t['largo_mm'] * t['cantidad']} |")
    L += [f"| **Total** | | **{sum(t['cantidad'] for t in desp['tramos'])}** | | **{desp['total_mm']}** |", "",
          f"**Despiece** (primero el tramo más largo, en la primera barra donde quepa): {desp['n_barras']} barras, "
          f"sobran {desp['sobrante_mm']} mm en total.", ""]
    for i, b in enumerate(desp["barras"], 1):
        L.append(f"- Barra {i}: {' + '.join(str(x) for x in b)} mm")
    # Tornillería
    L += ["", "### Tornillería, escuadras y pies niveladores", "",
          f"Contado por pieza: las uniones de la estructura (escuadras con 2 tornillos M5 y 2 tuercas en T cada una; "
          f"un pie nivelador por pata o poste) y los tornillos de cada pieza impresa (columna `tornillos` en "
          f"precios.yaml). Se compra un {datos['estructura_3d']['tornilleria']['repuesto']:.0%} de repuesto.", "",
          "| Qué | Contados | A comprar | Precio | Subtotal |", "|---|---:|---:|---:|---:|"]
    for d in tor.values():
        if d["contados"]:
            L.append(f"| {d['nombre']} *(estimado)* | {d['contados']} | {d['comprar']} | {pesos(d['precio'])} | {pesos(d['subtotal'])} |")
    L.append(f"| **Total** | **{sum(d['contados'] for d in tor.values())}** | **{sum(d['comprar'] for d in tor.values())}** | | "
             f"**{pesos(sum(d['subtotal'] for d in tor.values()))}** |")
    L += ["", "Por zona (contados, sin repuesto):", ""]
    for z, cnt in tornillos_por_zona(datos).items():
        L.append(f"- {z}: " + ", ".join(f"{n} {tor[t]['nombre'].split(' (')[0].lower()}" for t, n in cnt.items()))
    L.append("")
    return L


def generar_md() -> str:
    datos = cargar()
    fs = filas(datos)
    t = total(datos)
    estimado = sum(f["subtotal"] for f in fs if f["fuente"] == "estimado")
    c3d = costo_estructura_3d(datos)
    lineas = [
        "# Costo del proyecto en Colombia",
        "",
        "> Generado por `python -m app.documentos` desde `config/precios.yaml`: no editar a mano.",
        f"> Precios consultados el {datos['consultado']} en pesos colombianos, sin envío. Cambian:",
        "> verificarlos antes de comprar.",
        "",
        f"**Total del proyecto: {pesos(t)}** (sin el portátil, que es del grupo). De eso, "
        f"{pesos(estimado)} ({estimado * 100 // max(t, 1)} %) son **estimados** (materiales sin un producto",
        "igual publicado: banda de las cintas, tornillería, cables, tubos, piezas impresas): el resto es precio de tienda.",
        "",
        f"La **estructura 3D** (piezas impresas, perfil 2020 y tornillería, contadas en el modelo) cuesta "
        f"**{pesos(c3d['total'])}** ({c3d['total'] * 100 / max(t, 1):.0f} % del total): detalle más abajo.",
        "",
        "## Por subsistema",
        "",
        "| Subsistema | Costo | % |",
        "|---|---:|---:|",
    ]
    for s, v in por_subsistema(datos).items():
        lineas.append(f"| {s} | {pesos(v)} | {v * 100 / max(t, 1):.0f} % |")
    lineas.append(f"| **Total** | **{pesos(t)}** | **100 %** |")
    lineas += ["", "## Dónde abaratar (propuestas, NO aplicadas)", "",
               "El diseño no se cambia sin que el grupo lo apruebe. Riesgo bajo = mismo comportamiento; medio = "
               "funciona pero hay que medir algo; alto = cambia el diseño.", "",
               "| Propuesta | Ahorro | Riesgo | Por qué |", "|---|---:|---|---|"]
    for a in ahorros(datos):
        lineas.append(f"| {a['titulo']} | {pesos(a['ahorro'])} | {a['riesgo']} | {a['detalle']} |")
    lineas += [""] + _md_estructura_3d(datos)
    lineas += ["## Detalle", ""]
    for s in ORDEN_SUBSISTEMAS:
        del_sub = [f for f in fs if f["subsistema"] == s]
        if not del_sub:
            continue
        lineas += [f"### {s}", "", "| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |",
                   "|---|---|---:|---:|---:|---|"]
        for f in del_sub:
            donde = f"[{f['tienda']}]({f['url']})" if f["url"] else f["tienda"]
            marca = " *(estimado)*" if f["fuente"] == "estimado" else ""
            lineas.append(f"| {f['nombre']} | {f['producto']}{marca} | {f['cantidad']} | {pesos(f['precio'])} | "
                          f"{pesos(f['subtotal'])} | {donde} |")
        lineas.append(f"| **Subtotal** | | | | **{pesos(sum(f['subtotal'] for f in del_sub))}** | |")
        lineas.append("")
    return "\n".join(lineas) + "\n"
