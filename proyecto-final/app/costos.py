"""Costo del proyecto en Colombia (config/precios.yaml, fuente única).

Lo usan `app.documentos` (genera docs/costos.md), el dashboard (pestaña Montaje real) y el
asistente (lee docs/costos.md y responde "cuánto cuesta" con el intérprete local).
"""

from __future__ import annotations

from pathlib import Path

import yaml

RUTA = Path(__file__).resolve().parent.parent / "config" / "precios.yaml"
ORDEN_SUBSISTEMAS = ["Cinta de monedas", "Cinta de vasos", "Canaleta y muelle", "Carro", "Control y potencia",
                     "Estructura"]


def cargar() -> dict:
    return yaml.safe_load(RUTA.read_text(encoding="utf-8"))


def filas(datos: dict | None = None) -> list[dict]:
    """Una fila por cosa que se compra, con su cantidad y subtotal. La cantidad
    que no esté en precios.yaml sale del catálogo (sim/catalogos.py)."""
    from sim.catalogos import CATALOGO_SENSORES, COMPONENTES

    datos = datos or cargar()
    catalogo = {c["id"]: c for c in COMPONENTES}
    catalogo.update({s["id"]: s for s in CATALOGO_SENSORES})
    out = []
    for grupo in ("items", "extras"):
        for id_, d in (datos.get(grupo) or {}).items():
            c = catalogo.get(id_, {})
            cantidad = d.get("cantidad", c.get("cantidad", 1))
            tienda = datos["tiendas"].get(d.get("tienda"), {})
            out.append({"id": id_, "nombre": c.get("nombre", id_.replace("_", " ").capitalize()),
                        "subsistema": d["subsistema"], "producto": d["producto"], "cantidad": cantidad,
                        "precio": d["precio"], "subtotal": d["precio"] * cantidad, "fuente": d["fuente"],
                        "tienda": tienda.get("nombre", "—"), "url": tienda.get("url", "")})
    return out


def por_subsistema(datos: dict | None = None) -> dict[str, int]:
    tot = {s: 0 for s in ORDEN_SUBSISTEMAS}
    for f in filas(datos):
        tot[f["subsistema"]] = tot.get(f["subsistema"], 0) + f["subtotal"]
    return tot


def total(datos: dict | None = None) -> int:
    return sum(f["subtotal"] for f in filas(datos))


def ahorros(datos: dict | None = None) -> list[dict]:
    datos = datos or cargar()
    return sorted(datos.get("ahorros") or [], key=lambda a: -a["ahorro"])


def pesos(v: int) -> str:
    return f"${int(v):,}".replace(",", ".")


def generar_md() -> str:
    datos = cargar()
    fs = filas(datos)
    t = total(datos)
    estimado = sum(f["subtotal"] for f in fs if f["fuente"] == "estimado")
    lineas = [
        "# Costo del proyecto en Colombia",
        "",
        "> Generado por `python -m app.documentos` desde `config/precios.yaml`: no editar a mano.",
        f"> Precios consultados el {datos['consultado']} en pesos colombianos, sin envío. Cambian:",
        "> verificarlos antes de comprar.",
        "",
        f"**Total del proyecto: {pesos(t)}** (sin el portátil, que es del grupo). De eso, "
        f"{pesos(estimado)} ({estimado * 100 // max(t, 1)} %) son **estimados** (materiales sin un producto",
        "igual publicado: banda de las cintas, tornillería, cables, tubos): el resto es precio de tienda.",
        "",
        "## Por subsistema",
        "",
        "| Subsistema | Costo | % |",
        "|---|---:|---:|",
    ]
    for s, v in por_subsistema(datos).items():
        lineas.append(f"| {s} | {pesos(v)} | {v * 100 / max(t, 1):.0f} % |")
    lineas += ["", "## Dónde abaratar (propuestas, NO aplicadas)", "",
               "El diseño no se cambia sin que el grupo lo apruebe. Riesgo bajo = mismo comportamiento; medio = "
               "funciona pero hay que medir algo; alto = cambia el diseño.", "",
               "| Propuesta | Ahorro | Riesgo | Por qué |", "|---|---:|---|---|"]
    for a in ahorros(datos):
        lineas.append(f"| {a['titulo']} | {pesos(a['ahorro'])} | {a['riesgo']} | {a['detalle']} |")
    lineas += ["", "## Detalle", ""]
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
        lineas.append("")
    return "\n".join(lineas) + "\n"
