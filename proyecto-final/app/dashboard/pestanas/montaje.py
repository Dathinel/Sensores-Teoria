"""Pestaña Montaje real: lo que hay que saber para construirlo de verdad. Si
los tiempos caben, cuánto tardaría esta corrida en el montaje real, cuántas
veces se equivocaron los sensores simulados con su error individual, cuánto
cuesta en Colombia y qué monedas faltan por medir."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from control import monedas as tabla_monedas
from control.tiempos import presupuesto, tiempo_real_estimado_s

from .. import datos
from ..estilo import (AMBAR, AZUL, MORADO, ROJO, VERDE, aviso, figura, html_tabla, kpis, mostrar, nota, pintar,
                      seccion, tabla)


@st.fragment(run_every=datos.REFRESCO_S)
def pestana() -> None:
    p = datos.PARAMETROS
    tel = datos.telemetria() or {}
    t = p["tiempos_ms"]
    r = presupuesto(t, lote=p["planta"]["monedas_por_vaso"],
                    lecturas_por_decision=p["planta"]["lecturas_por_decision"],
                    fotos_por_moneda=p["planta"]["fotos_por_moneda"],
                    reaccion_cortina_max_ms=p["cortina_seguridad"]["reaccion_max_ms"])
    aviso("Todos los valores son <b>PROVISIONALES</b> (hojas de datos): se reemplazan por lo que se mida en el "
          "montaje. Detalle completo y cómo medir cada cosa en <code>docs/replicacion.md</code>.", "azul")
    kpis([
        ("Ciclo de la cinta de monedas", f"{r['ciclo_monedas_ms']} ms", "avanzar una casilla + la pausa", AMBAR),
        ("Ritmo", f"{r['elementos_por_minuto']:.0f} elem/min", "piezas que entran por minuto", VERDE),
        ("Esta corrida en el montaje real", f"≈ {tiempo_real_estimado_s(tel.get('tick', 0), t):.0f} s",
         "ciclos × (avance + pausa); no cuenta esperas por tubos llenos", AZUL),
        ("Reacción de la cortina", f"{r['reaccion_cortina_ms']} ms", "de ver la mano a subir la prensa", ROJO),
    ])

    seccion("Presupuesto de tiempos", "¿cabe cada acción en su hueco? · tiempos en milisegundos")
    # Tabla de texto (no st.dataframe): la columna "Por qué" es larga y así se parte en líneas dentro
    # de la celda en vez de pedir desplazamiento horizontal (pantalla de ~900 px).
    pintar(html_tabla([{
        "Chequeo": c.nombre, "Necesita": round(c.necesita_ms), "Disponible": round(c.disponible_ms),
        "Margen": round(c.margen_ms), "Estado": "OK" if c.ok else "NO CABE", "Por qué": c.explicacion,
    } for c in r["chequeos"]], {"Necesita": "num", "Disponible": "num", "Margen": "num",
                                 "Estado": lambda v: "corto ok" if v == "OK" else "corto no"}))
    justos = [c.nombre for c in r["chequeos"] if c.ok and c.margen_ms < 0.15 * c.disponible_ms]
    if justos:
        aviso("Margen justo (menos del 15 %): " + "; ".join(justos) + ". Medirlo primero en el montaje.")

    izq, der = st.columns(2, gap="large")
    with izq:
        seccion("Errores de los sensores en esta corrida", "cada sensor con su error de hoja de datos")
        errores = tel.get("errores_filtrado", {})
        if not tel.get("errores_sensores_activos"):
            st.info("Esta corrida usa sensores perfectos (config: simulacion.errores_sensores = false).")
        kpis([
            ("Monedas colombianas rechazadas por error", str(errores.get("falsos_rechazos", 0)),
             "quedan en la bandeja de rechazo: se recuperan", AZUL),
            ("Piezas no colombianas aceptadas", str(errores.get("falsas_aceptaciones", 0)), "lo más grave", ROJO),
            ("Monedas en el vaso equivocado", str(errores.get("clase_equivocada", 0)),
             "clase confundida: la atajan las dos fotos y la regla de coherencia con el diámetro", MORADO),
        ])
        nota(f'Cada estación lee su sensor {p["planta"]["lecturas_por_decision"]} veces y decide por mayoría. Error '
             "por lectura de cada sensor: bloque <code>errores_sensores</code> de la configuración.")
        pendientes = tabla_monedas.sin_verificar()
        seccion("Monedas por medir", f"{len(pendientes)} clases con medidas provisionales")
        tabla(pd.DataFrame([{"Clase": m.clase, "Diámetro (mm)": m.diametro_mm, "Masa (g)": m.masa_g,
                             "Material": m.material} for m in pendientes]), height=240)
    with der:
        costos_proyecto()


def costos_proyecto() -> None:
    """Costo en Colombia por subsistema y dónde abaratar (config/precios.yaml)."""
    from app import costos

    info = costos.cargar()
    subs = costos.por_subsistema(info)
    seccion(f"Costo del proyecto en Colombia: {costos.pesos(costos.total(info))}",
            f"precios del {info['consultado']}, sin el portátil; detalle en <code>docs/costos.md</code>")
    orden = sorted(subs.items(), key=lambda x: x[1])
    fig = figura(40 + 34 * len(orden))
    fig.add_bar(x=[v for _, v in orden], y=[n for n, _ in orden], orientation="h", marker_color=AMBAR,
                marker_line_width=0, text=[costos.pesos(v) for _, v in orden], textposition="outside",
                cliponaxis=False, hovertemplate="%{y}: %{text}<extra></extra>")
    fig.update_xaxes(tickprefix="$", rangemode="tozero", showgrid=True)
    fig.update_layout(margin=dict(l=10, r=70, t=10, b=10))
    mostrar(fig)
    seccion("Dónde abaratar", "propuestas, con su riesgo")
    pintar(html_tabla([{"Propuesta": a["titulo"], "Ahorro": costos.pesos(a["ahorro"]), "Riesgo": a["riesgo"]}
                       for a in costos.ahorros(info)], {"Ahorro": "num"}))
