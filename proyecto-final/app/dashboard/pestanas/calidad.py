"""Pestaña Calidad del filtro (Inspección y Rechazos de CLAUDE.md §13): qué tan
bien separa la línea las monedas colombianas del resto, por qué rechazó cada
cosa (evidencia de que los filtros se complementan) y lo que midió la cámara."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from control import reglas

from .. import datos
from ..estilo import AZUL, MORADO, ROJO, VERDE, figura, kpis, mostrar, nota, pintar, seccion, tabla
from ..textos import DECISIONES, ETAPA_DE_CAUSA, NOMBRE_CAUSA, QUE_FILTRA

FILAS = ["Moneda colombiana", "Moneda que debe rechazarse", "Botón de plástico", "Botón metálico", "Bloque", "Mano"]


@st.fragment(run_every=datos.REFRESCO_S)
def pestana() -> None:
    m = datos.matriz_aciertos()
    if not len(m):
        st.info("Cuando empiecen a pasar piezas, aquí se ve qué tan bien separa la línea lo bueno de lo malo.")
        return
    buena = m["real"] == "Moneda colombiana"
    aceptada = m["decision"] == "Aceptada"
    bien = (buena & aceptada) | (~buena & ~aceptada)
    malas_aceptadas = int((~buena & aceptada).sum())
    kpis([
        ("Decisiones correctas", f"{bien.mean() * 100:.0f} %", "monedas colombianas aceptadas y todo lo demás rechazado",
         VERDE),
        ("Monedas buenas rechazadas", str(int((buena & ~aceptada).sum())),
         "quedan en la bandeja de rechazo: se recuperan, no se pierden", AZUL),
        ("Piezas malas aceptadas", str(malas_aceptadas),
         "lo más grave: algo que no es una moneda colombiana termina en un vaso", ROJO if malas_aceptadas else VERDE),
        ("Piezas procesadas", str(len(m)), "con su decisión final", MORADO),
    ])

    izq, der = st.columns([1.4, 1], gap="large")
    with izq:
        seccion("Qué era cada pieza y qué decidió la línea", "en verde los aciertos, en rojo los errores")
        filas = [r for r in FILAS if r in set(m["real"])]
        cruce = pd.crosstab(m["real"], m["decision"]).reindex(index=filas, columns=DECISIONES, fill_value=0)
        z = cruce.values
        acierto = [[(r == "Moneda colombiana") == (c == "Aceptada") for c in DECISIONES] for r in filas]
        colz = [[(1 if a else -1) * (v > 0) for a, v in zip(fila_a, fila_v)] for fila_a, fila_v in zip(acierto, z)]
        fig = figura(90 + 46 * len(filas))
        fig.add_trace(go.Heatmap(z=colz, x=DECISIONES, y=filas, text=[[v or "" for v in f] for f in z],
                                 texttemplate="%{text}",
                                 colorscale=[[0, "rgba(229,83,75,0.6)"], [0.5, "#161b22"], [1, "rgba(63,182,139,0.6)"]],
                                 zmin=-1, zmax=1, showscale=False, xgap=3, ygap=3, hoverinfo="skip",
                                 textfont=dict(color="#ffffff", size=15, family="IBM Plex Mono, monospace")))
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(side="top", showgrid=False)
        mostrar(fig)
    with der:
        seccion("Por qué se rechaza cada cosa", "cada causa la detecta una sola etapa")
        rechazos = datos.rechazos_por_causa()
        conteo = {c: 0 for c in reglas.CAUSAS_VALIDAS}
        conteo.update(dict(zip(rechazos["causa"], rechazos["n"])))
        filas_html = []
        for c in reglas.CAUSAS_VALIDAS:
            material = ETAPA_DE_CAUSA.get(c) == "material"
            etapa = (f'<span class="etiqueta" style="--c:{AZUL if material else MORADO}">'
                     f'{"sensores de material" if material else "cámara"}</span>')
            filas_html.append(f'<div class="causa{" cero" if not conteo[c] else ""}"><span class="n">{conteo[c]}</span>'
                              f'<span class="t"><b>{NOMBRE_CAUSA[c]}</b>{etapa}<small>{QUE_FILTRA[c]}</small></span></div>')
        pintar(f'<div class="causas">{"".join(filas_html)}</div>')
        sin = [NOMBRE_CAUSA[c] for c, n in conteo.items() if n == 0]
        if sin and sum(conteo.values()):
            nota("Filtros que no actuaron en esta corrida: " + ", ".join(sin) + ".")

    medidas = datos.ultimas_mediciones(15)
    if medidas:
        with st.expander("Detalle de la cámara: las últimas 15 piezas medidas", icon=":material/photo_camera:"):
            tabla(pd.DataFrame([{
                "Pieza": x["casilla"], "Diámetro": f'{x["diametro_mm"]:.2f} mm', "Redondez": f'{x["circularidad"]:.2f}',
                "Agujeros": x["contornos_internos"], "La cámara cree que es": x["clase"],
                "Seguridad": f'{x["confianza"] * 100:.0f} %',
                "Decisión": "aceptada" if x["veredicto"] == "aceptada" else NOMBRE_CAUSA.get(x.get("causa"), x.get("causa")),
            } for x in medidas]))
            st.caption("Hoy la cámara es simulada (el reconocimiento sabe qué es cada pieza y se le puede forzar "
                       "error); la visión real con el modelo entrenado llega en la fase 5.")
