"""
graficar_convergencia.py - Figura de la prueba 10: que tan rapido converge el enjambre segun rho.

Para cada rho (0,1, 0,5 y 0,9) corre las mismas 20 semillas de pruebas_algoritmo.py sobre
maze.json y cuenta, en cada iteracion, en que porcentaje de las corridas el camino de MAXIMA
feromona ya es una ruta optima. Guarda img/convergencia-rho.png.

Uso:
    entorno\\Scripts\\python pruebas\\graficar_convergencia.py
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")  # sin ventana: solo se guarda el PNG
import matplotlib.pyplot as plt  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
TEMA = os.path.dirname(AQUI)
sys.path.insert(0, TEMA)
sys.path.insert(0, AQUI)

import aco  # noqa: E402
from pruebas_algoritmo import SEMILLAS, camino_codicioso  # noqa: E402

# Colores categoricos fijos (azul, naranja, verde agua): se distinguen tambien con daltonismo.
COLORES = {0.1: "#2a78d6", 0.5: "#eb6834", 0.9: "#1baf7a"}


def curva(lab, rho):
    p0 = aco.Parametros(rho=rho)
    L_opt = lab.longitud_camino(aco.camino_optimo(lab))
    conteo = [0] * p0.iteraciones
    for s in SEMILLAS:
        r = aco.simular_enjambre(lab, aco.Parametros(rho=rho, semilla=s))
        for i, info in enumerate(r["historial"]):
            c = camino_codicioso(lab, info["tau"])
            if c is not None and abs(lab.longitud_camino(c) - L_opt) < 1e-9:
                conteo[i] += 1
    return [100.0 * c / len(SEMILLAS) for c in conteo]


def main():
    lab = aco.cargar_laberinto(os.path.join(TEMA, "maze.json"))
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=130)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    its = list(range(1, aco.Parametros().iteraciones + 1))
    for rho, color in COLORES.items():
        y = curva(lab, rho)
        ax.plot(its, y, color=color, linewidth=2, label=f"rho = {rho}")
        # Etiqueta directa al final de cada linea (ademas de la leyenda).
        ax.annotate(f"rho = {rho}", (its[-1], y[-1]), xytext=(6, {0.1: -10, 0.5: 0, 0.9: 10}[rho]),
                    textcoords="offset points", va="center", fontsize=9, color="#52514e")
    ax.set_xlim(1, its[-1] + 4)
    ax.set_ylim(0, 102)
    ax.set_xlabel("Iteración", color="#52514e")
    ax.set_ylabel("% de corridas convergidas", color="#52514e")
    ax.set_title("Camino de máxima feromona igual al óptimo (maze.json, 20 semillas)",
                 fontsize=11, color="#0b0b0b", loc="left")
    ax.grid(axis="y", color="#e4e3df", linewidth=0.8)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#c3c2b7")
    ax.tick_params(colors="#52514e")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    salida = os.path.join(TEMA, "img", "convergencia-rho.png")
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    fig.savefig(salida, facecolor=fig.get_facecolor())
    print("Guardado:", salida)


if __name__ == "__main__":
    main()
