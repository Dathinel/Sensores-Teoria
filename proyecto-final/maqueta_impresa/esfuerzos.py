"""Verificacion mecanica y termica de la maqueta impresa (usuario, 2026-10-24: "verifico que la deformacion del
plastico, el esfuerzo realizado y el calor generado no derrita o deforme permanentemente el plastico?").

Lo que se comprueba, con formulas de resistencia de materiales (no hay elementos finitos: cada caso es el
modelo mas simple que queda DEL LADO SEGURO: viga simplemente apoyada, carga puntual en el peor punto):
  1. Tubos cargados: esfuerzo de flexion, flecha y esfuerzo de fluencia (carga sostenida).
  2. Columnas: pandeo de Euler con la carga que llevan.
  3. Remaches: cortante en el vastago y arranque de la una (traccion sostenida), por union.
  4. Cajeras de los nodos: aplastamiento del tubo contra la pared de la cajera.
  5. Calor: cada fuente que toca PLA, su potencia, la temperatura estimada y el margen contra la Tg.

PLA impreso (valores publicados para PLA FDM, con 4 perimetros, a 20-25 C):
  E = 3500 MPa; rotura 50 MPa en el plano de las capas, 30 MPa entre capas (Z);
  fluencia: a carga SOSTENIDA el PLA se deforma con el tiempo; por debajo de ~5 MPa es despreciable (ref. ensayos
  de creep de PLA impreso: < 1 % en un ano a 5 MPa y 23 C); Tg 55-60 C: desde ~45 C la fluencia se dispara y
  a 60 C se deforma con el peso propio.
Admisibles usados: corta duracion 10 MPa (SF 3 sobre la rotura entre capas); sostenida 5 MPa; temperatura de
cualquier PLA cargado <= 45 C.

Uso: python esfuerzos.py  -> esfuerzos.md y sale con 1 si algo no cumple.
"""
import math
from pathlib import Path

import numpy as np

import estructura as E

AQUI = Path(__file__).resolve().parent
G = 9.81e-3                     # N por gramo
E_PLA = 3500.0                  # MPa
ADM_CORTA = 10.0                # MPa, cargas de poco tiempo (prensa, choque del carro)
ADM_SOST = 5.0                  # MPa, cargas que estan siempre (pesos colgados)
T_MAX_PLA = 45.0                # C, temperatura maxima de PLA que carga algo
T_AMB = 25.0

# seccion del tubo 16 x 16, pared 1,6, hueco con 2 chaflanes de 3 arriba
LADO, PARED = E.LADO, E.PARED
A_TUBO = LADO ** 2 - ((LADO - 2 * PARED) ** 2 - 2 * 4.5)                     # mm2
I_TUBO = (LADO ** 4 - (LADO - 2 * PARED) ** 4) / 12                          # mm4 (del lado seguro: sin chaflanes)
# remache: vastago O4 con ranura de 1,2 -> area de cortante; una de 0,45 por lado -> area de arranque
A_REM_CORTE = math.pi * 2 ** 2 - 1.2 * 4                                      # 7.8 mm2
A_REM_UNA = math.pi * 4 * 0.45 * 0.6                                          # 3.4 mm2 (la una no rodea todo)


def largo(a, b):
    return float(np.linalg.norm(np.array(E.NODOS[a], float) - np.array(E.NODOS[b], float)))


# ----------------------------------------------------------------- 1. tubos en flexion
# (miembro, carga [N], tipo: "rep" repartida o "pun" puntual en a mm del apoyo, sostenida?, de donde sale la carga)
VIGAS = [
    ("P1-P2", 900 * G, ("rep", None), True, "viga del portico: almacen con 150 monedas, 28BYJ, tubo de tapas, prensa, sensores (masas.yaml)"),
    ("P1-P2", 60.0, ("pun", 330.0), False, "la prensa asentando una tapa: 60 N, reaccion en la viga en x 280 (a 330 mm de P1)"),
    ("T2-T3", 530 * G, ("rep", None), True, "riel +y de monedas: mitad de la cinta + NEMA 17 (280 g) + jaula"),
    ("T1-L", 530 * G, ("rep", None), True, "riel -y de monedas: mitad de la cinta + compuerta E4 + FC-51"),
    ("M1-M2", 0.64 * 0.12 ** 2 / 2 / 0.003 * 1.0, ("pun", 52.0), False,
     "tope del muelle: carro de 0,64 kg a 0,12 m/s frenado en 3 mm de espuma (F = m v^2 / 2 d = 1,5 N)"),
    ("Q2-L", 110 * G, ("pun", 55.0), True, "brazo de la camara cenital: webcam + anillo (110 g) en la punta (voladizo de 55 mm)"),
]


def flexion(miembro, F, carga, sostenida, nota):
    a_, b_ = miembro.split("-")
    L = largo(a_, b_) if b_ != "L" else {"T1": 276.0, "Q2": 55.0}[a_]      # puntas libres: largo del voladizo/tramo
    tipo, a = carga
    if miembro == "Q2-L":                     # voladizo empotrado en el nodo
        M = F * L
        d = F * L ** 3 / (3 * E_PLA * I_TUBO)
    elif tipo == "rep":
        w = F / L
        M = w * L ** 2 / 8
        d = 5 * w * L ** 4 / (384 * E_PLA * I_TUBO)
    else:
        b = L - a
        M = F * a * b / L
        c = min(a, b)                       # flecha maxima de una viga apoyada con carga descentrada (c = tramo corto)
        d = F * c * (L ** 2 - c ** 2) ** 1.5 / (9 * math.sqrt(3) * E_PLA * I_TUBO * L)
    sigma = M * (LADO / 2) / I_TUBO
    adm = ADM_SOST if sostenida else ADM_CORTA
    # flecha admisible: L/500 si la carga esta siempre, L/200 si es momentanea (vuelve al descargar); voladizo L/100
    f_adm = L / 100 if miembro == "Q2-L" else (L / 500 if sostenida else L / 200)
    return dict(que=f"tubo {miembro}", carga=f"{F:.1f} N", largo=f"{L:.0f} mm", esfuerzo=sigma, adm=adm,
                flecha=d, ok=sigma <= adm and d <= f_adm, nota=f"{nota}; flecha admisible {f_adm:.1f} mm")


# ----------------------------------------------------------------- 2. columnas (pandeo)
# (miembro, largo, carga axial [N], K de pandeo, nota). K = 1 si arriba esta amarrada a una viga (patas de la mesa de
# monedas, columnas del portico); K = 2 si la punta queda libre (postes). La prensa NO carga las columnas: empuja la
# tapa hacia abajo y su reaccion tira de la viga hacia ARRIBA (las alivia).
COLUMNAS = [
    ("F2-T2", 430.0, (1060 + 280) / 3 * G, 1.0, "pata de la mesa de monedas: un tercio de la cinta y el NEMA"),
    ("F4-P1", 400.0, 900 / 2 * G, 1.0, "columna del portico: mitad de lo colgado de la viga"),
    ("F5-P2", 400.0, 900 / 2 * G + 200 * G, 1.0, "columna del portico, lado +x: ademas lleva el empujador (MG996R y paleta)"),
    ("V2-L", 110.0, 1400 / 4 * G, 2.0, "poste de la cinta de vasos (un cuarto del bastidor con 5 vasos llenos), punta libre"),
    ("C1-L", 170.0, 250 / 4 * G, 2.0, "poste de la canaleta, punta libre"),
]


def pandeo(miembro, L, P, K, nota):
    pcr = math.pi ** 2 * E_PLA * I_TUBO / (K * L) ** 2
    sigma = P / A_TUBO
    return dict(que=f"columna {miembro}", carga=f"{P:.1f} N", largo=f"{L:.0f} mm", esfuerzo=sigma, adm=ADM_SOST,
                flecha=0.0, ok=P * 3 <= pcr and sigma <= ADM_SOST, nota=f"{nota}; pandeo critico {pcr:.0f} N (SF {pcr / P:.0f})")


# ----------------------------------------------------------------- 3. remaches por union
# (union, remaches, carga total [N], en cortante o en traccion (arranque de la una), sostenida, nota)
REMACHES = [
    ("puente del almacen a la viga", 6, (210 + 30 + 150 * 7.1 / 1000 * 25) * G, "corte", True,
     "almacen impreso + 28BYJ + 150 monedas de hasta 7,1 g: cuelga de 6 remaches en cortante"),
    ("colgante del tubo de tapas a la viga", 4, 130 * G, "corte", True, "tubo + abrazaderas + 10 tapas"),
    ("placa de la prensa a la viga", 3, 60.0, "corte", False, "reaccion de los 60 N de la prensa"),
    ("laterales de vasos a los postes", 4, 1400 * G, "corte", True, "bastidor con banda, motor y 5 vasos llenos (133 g c/u)"),
    ("bancada de monedas a los rieles", 8, 400 * G, "traccion", True, "la bancada cuelga de 8 remaches desde arriba (la una abre abajo)"),
    ("placas colgantes de los rodillos de retorno", 12, 150 * G, "traccion", True, "3 rodillos de aluminio con 608"),
    ("cabezales de la canaleta a los postes", 8, (55 + 4 * 133) * G, "corte", True, "varillas con 4 vasos llenos"),
    ("tubo en su cajera (cualquier nodo)", 2, 1400 / 4 * G, "corte", True, "el poste mas cargado: un cuarto del bastidor de vasos"),
    ("topes del muelle a M1-M2", 2, 1.5, "corte", False, "choque del carro (1,5 N)"),
]


def remache(union, n, F, modo, sostenida, nota):
    area = A_REM_CORTE if modo == "corte" else A_REM_UNA
    sigma = F / n / area
    adm = (ADM_SOST if sostenida else ADM_CORTA) * (1.0 if modo == "corte" else 0.6)   # la una trabaja entre capas
    return dict(que=f"remaches: {union}", carga=f"{F:.1f} N en {n}", largo="-", esfuerzo=sigma, adm=adm, flecha=0.0,
                ok=sigma <= adm, nota=f"{nota} ({modo})")


# ----------------------------------------------------------------- 4. aplastamiento en la cajera
def cajera():
    # el tubo apoya en el piso de la cajera (16 x 22 mm) con la carga del poste mas cargado + el momento del riel
    F = 1400 / 4 * G + 60
    sigma = F / (LADO * E.HONDO)
    return dict(que="cajera del nodo (aplastamiento)", carga=f"{F:.1f} N", largo="16 x 22 mm", esfuerzo=sigma, adm=ADM_SOST,
                flecha=0.0, ok=sigma <= ADM_SOST, nota="tubo apoyado en el piso de la cajera, 2,4 mm de pared alrededor")


# ----------------------------------------------------------------- 5. calor
# (fuente, potencia media [W], potencia pico [W], resistencia termica a ambiente [C/W], que PLA toca, mitigacion)
# NEMA 17: 2 fases x 1 A^2 x 1,5 ohm = 3 W con las bobinas excitadas. Duty: avance 600 ms + pausa 1000 ms (37 %),
# y el firmware suelta los A4988 (ENABLE) tras a4988_reposo_ms con las cintas quietas. Rth de un NEMA 17 al aire
# ~7 C/W (hoja: 80 C de subida a 11 W).
CALOR = [
    ("NEMA 17 de cada cinta (17HS4401 a 1 A/fase)", 3.0 * 0.375, 3.0, 7.0, "mon_jaula_nema / vas_placa_motor (la brida del motor apoya en la placa)",
     "la brida NO debe tocar la placa: 4 separadores de nailon de 3 mm en los M3 (aire entre medio) y correr la "
     "prueba de banco de 200 pasadas con un termometro en la carcasa: si pasa de 45 C, bajar Vref a 0,8 A o imprimir "
     "esas dos piezas en PETG (Tg 80 C)"),
    ("28BYJ-48 (5 V, medio paso: 0,1-0,2 A)", 0.15 * 5 * 0.3, 0.15 * 5 * 0.3, 25.0, "alm_puente (pestanas del motor)",
     "ninguna: la carcasa queda tibia (~35 C)"),
    ("SG90 (desvio, obturador, tapas, escape)", 0.2, 0.2, 30.0, "bridas y cunas impresas", "ninguna"),
    ("MG996R de la prensa (0,2 s trabado cada ciclo)", 0.4, 0.4, 15.0, "tap_pre_placa (separadores)",
     "ninguna mientras la prensa no quede trabada: el firmware la suelta a los 200 ms (tiempos_ms); trabado 15 W lo "
     "quemaria a el antes que al PLA"),
    ("MG996R del empujador", 0.3, 0.3, 15.0, "tap_emp_placa_servo", "ninguna"),
    ("tira LED del panel de luz (5 V, 1 m) A MEDIA POTENCIA sobre cinta de aluminio", 1.0, 2.0, 10.0,
     "vas_panel_a/_b (marco de 1,6 mm)",
     "OBLIGATORIO: la tira va sobre cinta de aluminio pegada al marco (reparte el calor) y alimentada a media potencia "
     "(resistencia en serie o dimmer PWM; la camara solo necesita luz pareja, no maxima). A plena potencia y pegada "
     "directo al PLA llegaria a 45-65 C"),
    ("anillo LED de la camara cenital (en la carcasa de la webcam)", 1.0, 1.0, 15.0, "mon_camara (abrazadera, por la webcam)", "ninguna: ~40 C en el anillo, menos en la abrazadera"),
    ("fuente, bucks, A4988, ESP32, ventilador", 9.0, 9.0, 0.0, "nada: van en la caja de control (acrilico y aluminio)", "ninguna"),
]


def calor(fuente, p_med, p_pico, rth, toca, mit):
    t_med = T_AMB + p_med * rth
    t_pico = T_AMB + p_pico * rth          # si quedara al 100 % (prueba de banco continua)
    return dict(que=fuente, p=f"{p_med:.1f} W medio" + (f" / {p_pico:.1f} W continuo" if p_pico != p_med else ""),
                t=f"{t_med:.0f} °C" + (f" / {t_pico:.0f} °C continuo" if p_pico != p_med else ""),
                ok=t_med <= T_MAX_PLA, ok_continuo=t_pico <= T_MAX_PLA, toca=toca, mit=mit)


def main():
    filas = [flexion(*v) for v in VIGAS] + [pandeo(*c) for c in COLUMNAS] + [remache(*r) for r in REMACHES] + [cajera()]
    termicas = [calor(*c) for c in CALOR]
    malos = [f for f in filas if not f["ok"]] + [t for t in termicas if not t["ok"]]
    L = ["# Esfuerzos, deformación y calor en la maqueta impresa (GENERADO por esfuerzos.py)", "",
         f"PLA impreso: E = {E_PLA:.0f} MPa, admisible {ADM_CORTA:.0f} MPa en cargas cortas y {ADM_SOST:.0f} MPa en cargas que están "
         f"siempre (por fluencia); ningún PLA que cargue algo por encima de {T_MAX_PLA:.0f} °C (Tg 55-60 °C). Modelos simples "
         "del lado seguro (viga apoyada, carga en el peor punto, columna con extremo libre); no es un análisis por elementos "
         "finitos. Tubo 16 × 16 pared 1,6: A = %.0f mm², I = %.0f mm⁴." % (A_TUBO, I_TUBO), "",
         "## Mecánica", "", "| Qué | Carga | Largo | Esfuerzo (MPa) | Admisible | Flecha (mm) | ¿Cumple? | De dónde sale |",
         "|---|---|---|---:|---:|---:|---|---|"]
    L += [f"| {f['que']} | {f['carga']} | {f['largo']} | {f['esfuerzo']:.2f} | {f['adm']:.0f} | {f['flecha']:.2f} | "
          f"{'sí' if f['ok'] else 'NO'} | {f['nota']} |" for f in filas]
    peor = max(filas, key=lambda f: f["esfuerzo"] / f["adm"])
    L += ["", f"El caso más exigido es **{peor['que']}**: {peor['esfuerzo']:.2f} MPa de {peor['adm']:.0f} admisibles "
          f"(factor {peor['adm'] / peor['esfuerzo']:.1f} sobre el admisible, que ya lleva factor 3 sobre la rotura entre capas).", "",
          "**Deformación permanente (fluencia):** todas las cargas sostenidas quedan por debajo de 5 MPa, donde el PLA impreso "
          "no fluye de forma medible a temperatura ambiente. La flecha mayor es elástica (vuelve al descargar).", "",
          "## Calor", "", "| Fuente | Potencia | Temperatura estimada | ¿Cumple? | Qué PLA toca | Qué hacer |", "|---|---|---|---|---|---|"]
    L += [f"| {t['que']} | {t['p']} | {t['t']} | {'sí' if t['ok'] else 'NO'}{'' if t['ok_continuo'] else ' (continuo al 100 %: NO)'} | "
          f"{t['toca']} | {t['mit']} |" for t in termicas]
    L += ["", "**El único punto caliente es el NEMA 17.** A 1 A por fase disipa 3 W mientras las bobinas están excitadas; con el "
          "ciclo normal (37 % del tiempo y los drivers sueltos en reposo) la carcasa queda en ~33 °C, pero en una prueba continua "
          "sube a ~46 °C, justo en el límite. Por eso el motor NO debe apoyar directo en la placa impresa: 4 separadores de "
          "nailon de 3 mm en sus M3 dejan aire entre la brida y el PLA, y hay que medir la carcasa en la prueba de banco. Si "
          "pasa de 45 °C: Vref a 0,8 A (la cinta sobra par: margen ×9 y ×2,3 en peso.md) o esas dos placas en PETG.", "",
          "## Lo que NO cubre", "",
          "- No es un análisis por elementos finitos: cada pieza se redujo a su modelo de viga, columna o unión más simple.",
          "- Las cargas son las de config/masas.yaml y config/parametros.yaml (estimadas: pesar al armar).",
          "- Los valores del PLA son los publicados para piezas impresas con 4 perímetros a 20-25 °C; el filamento húmedo o "
          "las capas mal pegadas bajan la resistencia entre capas (por eso el factor 3).",
          "- Las temperaturas son estimadas con resistencias térmicas típicas; hay que MEDIR la carcasa del NEMA 17."]
    (AQUI / "esfuerzos.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    for f in filas:
        print(f"{'ok ' if f['ok'] else 'MAL'} {f['que']:52s} {f['esfuerzo']:6.2f} / {f['adm']:.0f} MPa  flecha {f['flecha']:.2f} mm")
    for t in termicas:
        print(f"{'ok ' if t['ok'] else 'MAL'} {t['que'][:52]:52s} {t['t']}")
    print("esfuerzos.md:", "con problemas" if malos else "todo cumple")
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(main())
