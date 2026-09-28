"""Pestaña Monedas y vasos (la "Producción" de CLAUDE.md §13): cuántas monedas
de cada denominación, el valor acumulado, qué hay en cada tubo del almacén y
los vasos de la corrida."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import datos
from ..datos import nombre_denominacion, pesos
from ..estilo import AMBAR, TEXTO, VERDE, figura, figura_vacia, mostrar, seccion, tabla
from ..textos import DENOMINACIONES, ESTADO_VASO_TXT, TUBOS


@st.fragment(run_every=datos.REFRESCO_S)
def pestana() -> None:
    d = datos.datos_corrida()
    aceptadas, vasos = d["aceptadas"], d["vasos"]
    tel = datos.telemetria() or {}

    izq, der = st.columns(2, gap="large")
    with izq:
        seccion("Monedas aceptadas por denominación", "cantidad · valor", primera=True)
        conteo = aceptadas.groupby("denominacion").size().reindex(DENOMINACIONES, fill_value=0)
        valor = aceptadas.groupby("denominacion")["valor"].sum().reindex(DENOMINACIONES, fill_value=0)
        fig = figura(300)
        fig.add_bar(x=[pesos(x) for x in conteo.index], y=conteo.values, marker_color=AMBAR,
                    marker_line_width=0, text=[f"{n} · {pesos(v)}" for n, v in zip(conteo.values, valor.values)],
                    textposition="outside", cliponaxis=False, hovertemplate="%{x}: %{y} monedas<extra></extra>")
        fig.update_yaxes(dtick=1 if conteo.max() <= 12 else None, rangemode="tozero", title="monedas")
        fig.update_xaxes(type="category")
        mostrar(fig)
    with der:
        seccion("Valor acumulado en el tiempo", "cada escalón es una moneda aceptada", primera=True)
        if len(aceptadas):
            serie = aceptadas.assign(ts=pd.to_datetime(aceptadas["ts"]), acumulado=aceptadas["valor"].cumsum())
            fig = figura(300)
            fig.add_scatter(x=serie["ts"], y=serie["acumulado"], mode="lines", line_shape="hv", fill="tozeroy",
                            line=dict(color=VERDE, width=3), fillcolor="rgba(63,182,139,0.12)",
                            hovertemplate="%{x|%H:%M:%S}: %{y:$,.0f}<extra></extra>")
            fig.update_yaxes(tickprefix="$", rangemode="tozero")
        else:
            fig = figura_vacia(300, "todavía no hay monedas aceptadas")
        mostrar(fig)

    lote = tel.get("monedas_por_vaso")
    seccion("Almacén: cuánto hay en cada tubo",
            f"la línea punteada es el lote ({lote or '—'} monedas): al llegar, el tubo suelta las monedas a un vaso")
    guardado = tel.get("almacen") or {}
    n = [int(guardado.get(c, 0)) for c in TUBOS]
    fig = figura(230)
    fig.add_bar(x=[pesos(int(c)) if c != "otras" else "otras" for c in TUBOS], y=n, marker_line_width=0,
                marker_color=[VERDE if x >= (lote or 99) else AMBAR for x in n], text=n, textposition="outside",
                cliponaxis=False, hovertemplate="%{x}: %{y} monedas<extra></extra>")
    if lote:
        fig.add_hline(y=lote, line_dash="dot", line_color=TEXTO)
    fig.update_xaxes(type="category")
    fig.update_yaxes(rangemode="tozero", range=[0, max(tel.get("capacidad_tubo") or 25, 1)], title="monedas")
    mostrar(fig)

    if len(vasos):
        seccion("Vasos de esta corrida", f"{len(vasos)} vasos")
        tabla(pd.DataFrame({
            "Vaso": vasos["id"],
            "Estado": [ESTADO_VASO_TXT.get(e, e) for e in vasos["estado"]],
            "De": [nombre_denominacion(x) if pd.notna(x) else "—" for x in vasos["denominacion"]],
            "Monedas": vasos["cantidad_monedas"],
            "Valor": [pesos(x) for x in vasos["valor_total"]],
            "Llenado": vasos["ts_llenado"].str.slice(11, 19).fillna("—"),
            "Entregado": vasos["ts_entrega"].str.slice(11, 19).fillna("—"),
        }))
