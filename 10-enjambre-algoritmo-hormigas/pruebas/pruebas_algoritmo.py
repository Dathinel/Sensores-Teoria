"""
pruebas_algoritmo.py - Pruebas 6 a 11 del enjambre (las de software, sin hardware).

Corre el mismo ACO del firmware (aco.py, equivalente bit a bit al C++: ver
pruebas/equivalencia/) con los tres nodos compartiendo feromona, y guarda los numeros reales en
pruebas/resultados/pruebas_algoritmo.json y una tabla en pruebas/resultados/pruebas_algoritmo.md.

Medidas que se reportan en cada corrida:
  hallo      : alguna hormiga del enjambre recorrio una ruta optima (la longitud de la BFS).
  it_hallazgo: en que iteracion paso eso por primera vez.
  convergio  : al terminar, el camino de MAXIMA feromona (sin azar) es optimo y no depende de
               ningun empate (criterio estricto de aco.camino_codicioso). Es la medida dura:
               significa que la memoria comun "apunta" a la ruta mas corta.
  it_conv    : primera iteracion desde la cual el camino de maxima feromona es optimo y ya no
               cambia hasta el final.

Uso:
    entorno\\Scripts\\python pruebas\\pruebas_algoritmo.py
"""

import json
import os
import statistics
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
TEMA = os.path.dirname(AQUI)
sys.path.insert(0, TEMA)

import aco  # noqa: E402

SEMILLAS = list(range(1, 21))      # 20 corridas con semillas distintas
SEMILLA_FIJA = 12345
RESULTADOS = os.path.join(AQUI, "resultados")


def camino_codicioso(lab, tau):
    nodo = aco.NodoACO(lab, aco.Parametros(), 1)
    nodo.tau = list(tau)
    return nodo.camino_codicioso(estricto=True)


def corrida(lab, params):
    r = aco.simular_enjambre(lab, params)
    L_opt = r["longitud_optima"]
    # Iteracion de convergencia: desde cuando el camino de maxima feromona es optimo sin cambiar.
    it_conv = None
    for info in r["historial"]:
        c = camino_codicioso(lab, info["tau"])
        ok = c is not None and abs(lab.longitud_camino(c) - L_opt) < 1e-9
        if ok and it_conv is None:
            it_conv = info["iteracion"]
        elif not ok:
            it_conv = None
    exitosas = sum(d["exitosas"] for i in r["historial"] for d in i["por_nodo"].values())
    descartadas = sum(d["descartadas"] for i in r["historial"] for d in i["por_nodo"].values())
    return {
        "semilla": params.semilla,
        "hallo": r["iteracion_primer_optimo"] is not None,
        "it_hallazgo": r["iteracion_primer_optimo"],
        "convergio": r["convergio"],
        "it_conv": it_conv if r["convergio"] else None,
        "mejor_longitud": round(r["mejor_longitud"], 6),
        "camino_codicioso": r["camino_codicioso"],
        "pasos_codicioso": len(r["camino_codicioso"]) - 1 if r["camino_codicioso"] else None,
        "hormigas_exitosas": exitosas,
        "hormigas_descartadas": descartadas,
        "tau_final": r["tau_final"][1],
    }


def resumen(corridas):
    n = len(corridas)
    its_h = [c["it_hallazgo"] for c in corridas if c["hallo"]]
    its_c = [c["it_conv"] for c in corridas if c["convergio"]]
    return {
        "corridas": n,
        "tasa_hallazgo": sum(c["hallo"] for c in corridas) / n,
        "tasa_convergencia": sum(c["convergio"] for c in corridas) / n,
        "it_media_hallazgo": round(statistics.mean(its_h), 2) if its_h else None,
        "it_media_convergencia": round(statistics.mean(its_c), 2) if its_c else None,
        "descartadas_media": round(statistics.mean(c["hormigas_descartadas"] for c in corridas), 1),
    }


def barrido(lab, **cambios):
    corr = [corrida(lab, aco.Parametros(semilla=s, **cambios)) for s in SEMILLAS]
    return {"parametros": cambios, "resumen": resumen(corr),
            "corridas": [{k: v for k, v in c.items() if k != "tau_final"} for c in corr]}


def main():
    t0 = time.time()
    lab_maze = aco.cargar_laberinto(os.path.join(TEMA, "maze.json"))
    lab_abierto = aco.cargar_laberinto(os.path.join(TEMA, "laberintos", "abierto.json"))
    lab_unico = aco.cargar_laberinto(os.path.join(TEMA, "laberintos", "unico_camino.json"))
    lab_dos = aco.cargar_laberinto(os.path.join(TEMA, "laberintos", "dos_caminos.json"))
    out = {"parametros_por_defecto": aco.Parametros().__dict__, "semillas": SEMILLAS}

    # --- Prueba 6: sin paredes interiores, optimo de 8 pasos -----------------------------------
    fija = corrida(lab_abierto, aco.Parametros(semilla=SEMILLA_FIJA))
    b = barrido(lab_abierto)
    ok6 = fija["pasos_codicioso"] == 8 and b["resumen"]["tasa_hallazgo"] >= 0.95
    antes = barrido(lab_abierto, deposito="todas")
    fija_antes = corrida(lab_abierto, aco.Parametros(semilla=SEMILLA_FIJA, deposito="todas"))
    out["prueba_6"] = {"regla_anterior_todas_depositan": {"resumen": antes["resumen"],
                                                          "pasos_semilla_fija": fija_antes["pasos_codicioso"]},
                       "criterio": "Con la semilla fija el camino de maxima feromona mide 8 pasos "
                                   "(1,60 m) y en al menos 95 % de 20 semillas se halla una ruta de 8 pasos.",
                       "semilla_fija": {k: v for k, v in fija.items() if k != "tau_final"},
                       **b, "cumple": ok6}

    # --- Prueba 7: un unico camino -----------------------------------------------------------
    fija = corrida(lab_unico, aco.Parametros(semilla=SEMILLA_FIJA))
    b = barrido(lab_unico)
    unico = aco.camino_optimo(lab_unico)
    en_ruta = {lab_unico.arista_entre(a, c) for a, c in zip(unico, unico[1:])}
    p = aco.Parametros()
    tau_sin_deposito = p.tau0 * (1 - p.rho) ** p.iteraciones
    # Las aristas de las ramas ciegas nunca deben recibir feromona: solo se evaporan.
    ramas_limpias = all(abs(t - tau_sin_deposito) < 1e-15
                        for e, t in enumerate(fija["tau_final"]) if e not in en_ruta)
    ok7 = (b["resumen"]["tasa_hallazgo"] == 1.0 and b["resumen"]["tasa_convergencia"] == 1.0
           and ramas_limpias and fija["hormigas_descartadas"] > 0)
    out["prueba_7"] = {"criterio": "En las 20 semillas se halla la unica ruta (12 pasos, 2,40 m), las "
                                   "hormigas que entran a un callejon se descartan, y las aristas de los "
                                   "callejones terminan sin ningun deposito (solo evaporacion).",
                       "semilla_fija": {k: v for k, v in fija.items() if k != "tau_final"},
                       "ramas_sin_deposito": ramas_limpias,
                       "tau_esperada_sin_deposito": tau_sin_deposito, **b, "cumple": ok7}

    # --- Prueba 8: dos caminos de distinta longitud ------------------------------------------
    fija = corrida(lab_dos, aco.Parametros(semilla=SEMILLA_FIJA))
    b = barrido(lab_dos)
    corto = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (4, 1), (4, 2), (4, 3), (4, 4)]
    largo = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 4), (1, 3), (1, 2), (2, 2), (2, 3),
             (2, 4), (3, 4), (4, 4)]

    def tau_media(tau, celdas):
        ids = [lab_dos.nodo(*c) for c in celdas]
        es = [lab_dos.arista_entre(a, c) for a, c in zip(ids, ids[1:])]
        return sum(tau[e] for e in es) / len(es)

    t_c, t_l = tau_media(fija["tau_final"], corto), tau_media(fija["tau_final"], largo)
    ok8 = fija["pasos_codicioso"] == 8 and b["resumen"]["tasa_convergencia"] >= 0.9
    out["prueba_8"] = {"criterio": "El camino de maxima feromona es el corto (8 pasos) con la semilla "
                                   "fija y en al menos 90 % de 20 semillas.",
                       "semilla_fija": {k: v for k, v in fija.items() if k != "tau_final"},
                       "tau_media_corto": t_c, "tau_media_largo": t_l, **b, "cumple": ok8}

    # --- Prueba 9: 20 semillas en el laberinto de la actividad --------------------------------
    b = barrido(lab_maze)
    antes9 = barrido(lab_maze, deposito="todas")
    out["prueba_9"] = {"regla_anterior_todas_depositan": {"resumen": antes9["resumen"]},
                       "criterio": "Reportar tasa de convergencia e iteraciones medias en 20 semillas. "
                                   "Se acepta si la tasa de hallazgo del optimo es al menos 90 %.",
                       **b, "cumple": b["resumen"]["tasa_hallazgo"] >= 0.9}

    # --- Prueba 10: barrido de rho -----------------------------------------------------------
    out["prueba_10"] = {"criterio": "Correr rho = 0,1, 0,5 y 0,9 con 20 semillas cada uno y registrar.",
                        "barrido": [barrido(lab_maze, rho=r) for r in (0.1, 0.5, 0.9)]}

    # --- Prueba 11: barrido de alfa y beta ---------------------------------------------------
    combos = [(1.0, 2.0), (0.5, 2.0), (2.0, 2.0), (1.0, 0.0), (1.0, 5.0), (3.0, 1.0)]
    out["prueba_11"] = {"criterio": "Correr al menos 4 combinaciones de alfa y beta con 20 semillas y registrar.",
                        "barrido": [barrido(lab_maze, alfa=a, beta=be) for a, be in combos]}
    out["duracion_s"] = round(time.time() - t0, 1)

    os.makedirs(RESULTADOS, exist_ok=True)
    with open(os.path.join(RESULTADOS, "pruebas_algoritmo.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    escribir_tabla(out)
    print(open(os.path.join(RESULTADOS, "pruebas_algoritmo.md"), encoding="utf-8").read())


def pct(x):
    return f"{100 * x:.0f} %"


def fila_resumen(etiqueta, r):
    return (f"| {etiqueta} | {pct(r['tasa_hallazgo'])} | {r['it_media_hallazgo']} | "
            f"{pct(r['tasa_convergencia'])} | {r['it_media_convergencia']} | {r['descartadas_media']} |")


def escribir_tabla(out):
    enc = ("| Caso | Halla el optimo | Iteracion media del hallazgo | Converge (max. feromona = optimo) "
           "| Iteracion media de convergencia | Hormigas descartadas (media de 360) |\n|---|---|---|---|---|---|")
    L = [f"Resultados reales de pruebas_algoritmo.py ({out['duracion_s']} s). 20 semillas (1 a 20), "
         "3 nodos x 4 hormigas x 30 iteraciones = 360 hormigas por corrida. Regla de deposito: "
         f"{out['parametros_por_defecto']['deposito']}.\n"]
    for k, titulo in (("prueba_6", "Prueba 6, laberinto abierto"), ("prueba_7", "Prueba 7, unico camino"),
                      ("prueba_8", "Prueba 8, dos caminos"), ("prueba_9", "Prueba 9, maze.json")):
        d = out[k]
        L += [f"### {titulo}", "", f"Criterio: {d['criterio']}", "", enc, fila_resumen("20 semillas", d["resumen"])]
        if "semilla_fija" in d:
            sf = d["semilla_fija"]
            L.append(f"\nSemilla fija {SEMILLA_FIJA}: camino de maxima feromona de {sf['pasos_codicioso']} pasos, "
                     f"{sf['hormigas_descartadas']} hormigas descartadas.")
        if "regla_anterior_todas_depositan" in d:
            ra = d["regla_anterior_todas_depositan"]
            L.append("\nCon la regla anterior (depositan todas las hormigas que llegan):\n")
            L += [enc, fila_resumen("20 semillas", ra["resumen"])]
            if "pasos_semilla_fija" in ra:
                L.append(f"\nSemilla fija {SEMILLA_FIJA} con la regla anterior: {ra['pasos_semilla_fija']} pasos.")
        if k == "prueba_8":
            L.append(f"Feromona media por arista al final (semilla fija): corto {d['tau_media_corto']:.2f}, "
                     f"largo {d['tau_media_largo']:.3g}.")
        L.append(f"\n**Cumple: {'si' if d['cumple'] else 'no'}**\n")
    L += ["### Prueba 10, barrido de rho (maze.json)", "", enc]
    L += [fila_resumen(f"rho = {b['parametros']['rho']}", b["resumen"]) for b in out["prueba_10"]["barrido"]]
    L += ["", "### Prueba 11, barrido de alfa y beta (maze.json)", "", enc]
    L += [fila_resumen(f"alfa = {b['parametros']['alfa']}, beta = {b['parametros']['beta']}", b["resumen"])
          for b in out["prueba_11"]["barrido"]]
    with open(os.path.join(RESULTADOS, "pruebas_algoritmo.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
