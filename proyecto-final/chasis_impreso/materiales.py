"""Lista de materiales del carro (usuario, 2026-10-22): piezas impresas con gramos y tiempo, electronica
con precio, cables por calibre y ferreteria. Sale de los datos que ya hay, para que no se desfase:
  - piezas.json (lo escribe exportar.py): gramos y minutos de cada pieza impresa
  - ../config/precios.yaml: componentes del carro con su precio y el precio del PLA
  - ../docs/electrica.md: un renglon por hilo del carro (grupo c_*), con calibre y largo
  - README.md, seccion "Lo que hay que comprar": ferreteria y consumibles

Uso: python materiales.py -> lista_materiales.md. manual.py usa tablas() para la seccion del PDF.
"""
import json
import re
from collections import defaultdict

import yaml

import exportar as ex

AQUI = ex.AQUI
RAIZ = AQUI.parent
FUERA_DEL_CARRO = {"cuna_carro", "pista", "rodillos_guia"}   # cuna: impresa; pista: no va en el carro; rodamientos: en ferreteria (son 4, no 2)
MARGEN_CABLE = 1.3                           # 30 % de mas para curvas, pelado y errores


def pesos(v):
    return f"${v:,.0f}".replace(",", ".")


def impresas():
    piezas = json.loads((AQUI / "piezas.json").read_text(encoding="utf-8"))["piezas"]
    filas, g_tot, min_tot = [], 0.0, 0
    for p in piezas:
        if p["tanda"] == 0:
            continue   # la pieza de prueba va aparte (no queda en el carro)
        g, m = p["cantidad"] * p["gramos"], p["cantidad"] * p["minutos"]
        g_tot, min_tot = g_tot + g, min_tot + m
        filas.append([p["pieza"], p["tanda"], p["cantidad"], f'{p["gramos"]:.1f}', f'{p["minutos"]}', f"{g:.1f}",
                      f"{m // 60} h {m % 60:02d} min"])
    return filas, g_tot, min_tot


def electronica(precios):
    filas, total = [], 0
    for k, it in precios["items"].items():
        if it.get("subsistema") != "Carro" or k in FUERA_DEL_CARRO:
            continue
        cant = it.get("cantidad", 1)
        total += cant * it["precio"]
        filas.append([it["producto"], cant, pesos(it["precio"]), pesos(cant * it["precio"]),
                      "estimado" if it["fuente"] == "estimado" else precios["tiendas"][it["tienda"]]["nombre"].split(" (")[0]])
    # shortcut: la placa GVS no esta en precios.yaml; si se agrega alla, quitar esta fila
    filas.append(["Placa de expansión GVS para ESP32 DevKit 30 pines", 1, "sin precio", "—", "verificar"])
    return filas, total


def cables():
    """Hilos del carro en docs/electrica.md: [(calibre, hilos, metros)] y los conectores que piden."""
    por_calibre = defaultdict(lambda: [0, 0.0])
    for linea in (RAIZ / "docs" / "electrica.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| \d+ \| c_\w+ \|.*\| (\d+) AWG [^|]*\| ([\d,]+) m \|", linea)
        if m:
            por_calibre[int(m[1])][0] += 1
            por_calibre[int(m[1])][1] += float(m[2].replace(",", "."))
    assert por_calibre, "no se encontraron los hilos del carro en docs/electrica.md"
    return sorted(por_calibre.items())


def ferreteria():
    """Tabla 'Lo que hay que comprar' del README: [(item, cantidad, donde)]."""
    txt = (AQUI / "README.md").read_text(encoding="utf-8")
    seccion = txt.split("## Lo que hay que comprar", 1)[1].split("\n## ", 1)[0]
    filas = [[c.strip().replace("`", "") for c in l.strip("|").split("|")] for l in seccion.splitlines() if l.startswith("|")]
    return [f for f in filas[2:] if len(f) == 3]


def tablas():
    """[(titulo, encabezado, filas, nota)] para el PDF y el markdown."""
    precios = yaml.safe_load((RAIZ / "config" / "precios.yaml").read_text(encoding="utf-8"))
    imp, g_tot, min_tot = impresas()
    pla = precios["estructura_3d"]["impresion"]["precio_kg"]
    imp.append(["Total", "", sum(f[2] for f in imp), "", "", f"{g_tot:.0f}", f"{min_tot // 60} h {min_tot % 60:02d} min"])
    ele, total_ele = electronica(precios)
    ele.append(["Total electrónica", "", "", pesos(total_ele), ""])
    cab = cables()
    filas_cab = [[f"{awg} AWG", n, f"{m:.2f}", f"{m * MARGEN_CABLE:.1f}",
                  "batería, interruptor, TB6612 y motores (rojo/negro)" if awg <= 22 else
                  "señales y alimentación de sensores: Dupont hembra-hembra de 20 cm"] for awg, (n, m) in cab]
    filas_cab += [["Condensador cerámico 100 nF", 2, "", "", "en los bornes de cada motor TT"],
                  ["Plug DC 5,5 × 2,1 mm con cable", 1, "", "", "jack de la GVS: +7,4 V del interruptor y GND de la batería"],
                  ["Resistencias 1 kΩ y 2 kΩ", "1 + 1", "", "", "divisor del ECHO del HC-SR04 (en termoencogible)"],
                  ["Termoencogible 2-4 mm", "~50 cm", "", "", "empalmes y el divisor"]]
    return [
        ("Piezas impresas (PLA)", ["Pieza", "Tanda", "Cant.", "g c/u", "min c/u", "g total", "Tiempo total"], imp,
         f"Estimado de exportar.py (±30 % en el tiempo; Creality Print da el real al laminar). PLA: {g_tot:.0f} g "
         f"≈ {pesos(g_tot * pla / 1000)} a {pesos(pla)}/kg. Sin la pieza de prueba (tanda 0) ni los remaches de repuesto."),
        ("Electrónica", ["Componente", "Cant.", "Precio c/u", "Subtotal", "Tienda"], ele,
         "Precios de config/precios.yaml (consultados el 2026-09-27, COP, sin envío): verificarlos antes de comprar."),
        ("Cables y componentes sueltos", ["Calibre / ítem", "Hilos", "m (modelo)", "m a comprar", "Para qué"], filas_cab,
         "Hilos y largos de docs/electrica.md (cada hilo del carro mide 0,15 m en el modelo); se compra un 30 % de más."),
        ("Ferretería y consumibles", ["Ítem", "Cant.", "Dónde"], ferreteria(),
         "De la tabla de compras del README del chasis. Los remaches y pasadores son impresos (tanda 5)."),
    ]


def main():
    salida = ["# Lista de materiales del carro", "",
              "> Generado por `python materiales.py` (no editar a mano): sale de piezas.json, config/precios.yaml, "
              "docs/electrica.md y la tabla de compras del README.", ""]
    for titulo, enc, filas, nota in tablas():
        salida += [f"## {titulo}", "", "| " + " | ".join(enc) + " |", "|" + "---|" * len(enc)]
        salida += ["| " + " | ".join(str(c) for c in f) + " |" for f in filas]
        salida += ["", nota, ""]
    (AQUI / "lista_materiales.md").write_text("\n".join(salida), encoding="utf-8")
    print("lista:", AQUI / "lista_materiales.md")


if __name__ == "__main__":
    main()
