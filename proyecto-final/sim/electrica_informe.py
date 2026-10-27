"""Informe de la parte electrica: las graficas y `docs/electrica.md`.

Es la seccion 8 que antes estaba al final de `sim/electrica.py`; ese modulo se
queda con el modelo (rieles, cargas, simulacion en el tiempo, pasivos y cada
hilo) y este solo lo presenta. `python -m sim.electrica` llama a `main()`.
"""

from __future__ import annotations

from pathlib import Path

from control.configuracion import cargar_parametros
from sim.electrica import (A4988_RDS, AREA_CAJA_M2, caidas_por_carga, CAPACIDAD_MAH, CARGAS, condensadores,
                           DIODO_ENTRADA, DIODOS_ENTRADA, divisor_echo, DT, entrada_npn, estad, ETA_FUENTE,
                           FACTOR_POTENCIA, filtro_motor_tt, FRACCION_UTIL, FUSIBLE_PRINCIPAL_A, I_TRIP,
                           LARGO_USB_CENITAL, LARGO_USB_VASOS, LIMITE_CC_XL4015_A, NEMA_R_FASE, OHM_POR_M,
                           P_VACIO_FUENTE, PANEL_I_TIRA_5V, panel_luz, PANEL_P_MAX_W, PANEL_R_SERIE, PANEL_TIRAS,
                           PANEL_V_RODILLA, pullup_hall, pullup_i2c, pwm_motor_tt, R_BATERIA, resumen, RIELES,
                           tabla_hilos, TB6612_R, TT_I0, TT_KE, TT_R, U_CAJA, V_CE_NPN, V_GPIO_MAX, VIH_MIN,
                           VIL_MAX, vref_a4988, _n)

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
CAPTURAS = DOCS / "capturas"


# Paleta categorica de referencia (skill de visualizacion): orden fijo, nunca ciclado.
COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]


def generar_graficas(R: dict) -> dict[str, Path] | None:
    """PNG de los dos recorridos. Sin matplotlib devuelve None (el .md usa mermaid)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    CAPTURAS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#8a8a86", "axes.labelcolor": "#52514e", "xtick.color": "#52514e",
                         "ytick.color": "#52514e", "axes.titlesize": 10, "axes.titleweight": "bold"})
    salidas = {}
    sp, t = R["planta"]["series"], R["planta"]["t"]
    # Un panel por riel (una sola escala por panel: nada de doble eje), con su limite.
    paneles = [(k, f"{RIELES[k].nombre} (A)", k, RIELES[k].limite_a) for k in ("12V", "6V", "5V", "USB")]
    fig, ejes = plt.subplots(len(paneles), 1, figsize=(10, 9), sharex=True, facecolor="#fcfcfb")
    for eje, (clave, titulo, rid, lim), color in zip(ejes, paneles, COLORES):
        eje.set_facecolor("#fcfcfb")
        eje.plot(t, sp[clave], color=color, lw=1.4)
        prom, pico = estad(sp[clave])
        eje.axhline(prom, color="#52514e", lw=0.8, ls=":")
        eje.set_title(f"{titulo}   pico {_n(pico)} A · promedio {_n(prom)} A · límite {lim:g} A", loc="left")
        eje.set_ylim(0, max(pico * 1.25, 0.1))
        eje.grid(axis="y", color="#e4e3df", lw=0.6)
    ejes[-1].set_xlabel("tiempo (s) — ciclo real de la planta, paso de 10 ms")
    fig.tight_layout()
    ruta = CAPTURAS / "electrica-ciclo-planta.png"
    fig.savefig(ruta, dpi=110)
    plt.close(fig)
    salidas["planta"] = ruta

    sc, tc = R["carro"]["series"], R["carro"]["t"]
    fig, ejes = plt.subplots(3, 1, figsize=(10, 7.5), sharex=True, facecolor="#fcfcfb")
    datos = [(sc["BAT"], "Corriente de la batería (A)", COLORES[0]),
             (sc["motor_izq"], "Corriente del motor izquierdo (A)", COLORES[1]),
             (sc["motor_der"], "Corriente del motor derecho (A)", COLORES[2])]
    for eje, (serie, titulo, color) in zip(ejes, datos):
        eje.set_facecolor("#fcfcfb")
        eje.plot(tc, serie, color=color, lw=0.8)
        prom, pico = estad(serie)
        eje.set_title(f"{titulo}   pico {_n(pico)} A · promedio {_n(prom)} A", loc="left")
        eje.grid(axis="y", color="#e4e3df", lw=0.6)
        eje.set_ylim(0, max(pico * 1.25, 0.1))
    # Marcas de las fases del recorrido (texto en tinta neutra, no en el color de la serie).
    # Una marca por muro (el "detenido" de 0,3 s parte la maniobra en dos: se ignora lo que
    # cae a menos de 8 s de la marca anterior).
    t0, ultima = 0.0, -99.0
    for dur, _, _, nombre in R["carro"]["tramos"]:
        texto = {"frena ante el muro": "muro: evasión", "en la meta (sacan el vaso)": "meta",
                 "contra el tope (PWM bajo)": "tope del muelle"}.get(nombre)
        if texto and t0 - ultima > 8:
            ejes[0].axvline(t0, color="#b5b4ae", lw=0.6)
            ejes[0].text(t0 + 0.4, ejes[0].get_ylim()[1] * 0.9, texto, fontsize=7, color="#52514e")
            ultima = t0
        t0 += dur
    ejes[-1].set_xlabel(f"tiempo (s) — recorrido completo del carro con la batería a {_n(R['carro']['v_bateria'], 1)} V")
    fig.tight_layout()
    ruta = CAPTURAS / "electrica-ciclo-carro.png"
    fig.savefig(ruta, dpi=110)
    plt.close(fig)
    salidas["carro"] = ruta
    return salidas


def _ma(a):
    if a == 0:
        return "0"
    if a < 0.001:
        return f"{a * 1e6:.0f} µA"
    return f"{a * 1000:.0f} mA" if a < 1 else f"{_n(a)} A"


def _xychart(t, serie, titulo, paso=50) -> str:
    vals = ", ".join(_n(v, 2).replace(",", ".") for v in serie[::paso])
    return (f"```mermaid\nxychart-beta\n  title \"{titulo}\"\n  x-axis \"tiempo (x{paso * DT:g} s)\" 0 --> {len(serie[::paso])}\n"
            f"  y-axis \"A\"\n  line [{vals}]\n```\n")


def generar_markdown(graficas: bool = True) -> str:
    p = cargar_parametros()
    R = resumen()
    filas = tabla_hilos(R)
    img = generar_graficas(R) if graficas else None
    ri, fu, rg, au = R["rieles"], R["fusibles"], R["reguladores"], R["autonomia"]
    L = []
    w = L.append
    w("# Parte eléctrica, punto por punto (simulada)\n")
    w("> Generado por `python -m sim.electrica` desde `sim/electrica.py`, que lee el conexionado de "
      "`sim/conexiones.py` (la fuente única de cada hilo) y los tiempos de `config/parametros.yaml`. "
      "No editar a mano. Las corrientes son de hoja de datos (**PROVISIONALES** hasta medirlas con el "
      "multímetro en el montaje); la lista de lo que hay que medir está al final.\n")
    w("Esta página responde, para cada fuente, regulador, fusible y cable: **¿aguanta lo que le piden en el "
      "peor momento real del ciclo?** Para eso se recorre en el tiempo, con paso de 10 ms, un ciclo real de la "
      "planta y un recorrido completo del carro, sumando la corriente de cada carga en su riel. El circuito "
      "también se puede ver y mover en el simulador Wokwi: [wokwi/](../wokwi/README.md).\n")

    w("## 1. Qué es un riel de alimentación y cuáles hay\n")
    w("Un **riel** es una línea de voltaje fijo de la que se alimentan varias cargas (como una regleta). No se "
      "usa un solo voltaje para todo porque cada pieza pide el suyo: los servos se queman o se vuelven erráticos "
      "por encima de 6-7,2 V, el ESP32 trabaja a 3,3 V (sus pines no aguantan más de 3,6 V), los sensores "
      "industriales M18 piden 6-36 V y los paso a paso rinden mejor con 12 V (la corriente sube más rápido en la "
      "bobina). Separar rieles además aísla el ruido: el golpe de corriente de un servo que arranca no llega al "
      "ESP32.\n")
    w("| Riel | Lo genera | Para qué | Límite |")
    w("|---|---|---|---|")
    for r in RIELES.values():
        w(f"| **{r.nombre}** | {r.origen} | {r.para_que} | {r.limite_texto} |")
    w("")
    w("Un **buck** (XL4015, LM2596) es un regulador conmutado: prende y apaga un transistor miles de veces por "
      "segundo y filtra con una bobina, así que baja el voltaje perdiendo solo ~10-20 % en calor. Un regulador "
      "**lineal** (el AMS1117 del ESP32) quema como calor TODA la diferencia de voltaje por la corriente: sirve "
      "para corrientes chicas o diferencias chicas.\n")

    w("## 2. Diagrama de bloques de potencia\n")
    w("```mermaid\nflowchart LR\n"
      "  RED[\"Multitoma con interruptor<br/>110 V AC\"] --> FTE[\"Fuente 12 V 5 A<br/>con su cable\"]\n"
      "  FTE --> FUS{{\"Fusible principal 5 A\"}} --> E12((\"empalme<br/>+12 V\"))\n"
      "  E12 --> B6[\"Buck XL4015<br/>6 V 5 A\"] --> PCA[\"PCA9685 V+<br/>1000 µF\"] --> SERV[\"6 servos<br/>2 MG996R + 4 SG90\"]\n"
      "  E12 --> B5[\"Buck LM2596<br/>5 V\"] --> X5((\"empalme<br/>+5 V\"))\n"
      "  X5 --> ULN[\"ULN2003 → 28BYJ-48\"]\n  X5 --> LUZ[\"Panel de luz + anillo\"]\n  X5 --> VEN[\"Ventilador\"]\n"
      "  E12 --> DRV[\"2 × A4988<br/>100 µF c/u\"] --> NEMA[\"2 × NEMA17\"]\n"
      "  E12 --> S12[\"Capacitivo + inductivo<br/>(diodo + pull-up al GPIO)\"]\n"
      "  PC[\"Portátil<br/>3 puertos USB\"] --> ESP[\"ESP32 fijo<br/>AMS1117 → 3,3 V\"] --> L33[\"Lógica 3,3 V:<br/>FC-51, KY-003, 2 VL53L0X,<br/>PCA9685, A4988, pull-ups\"]\n"
      "  PC --> CAMS[\"2 webcams<br/>(un puerto cada una)\"]\n"
      "  FTE -. \"GND en estrella (bornes −V)\" .- ESP\n"
      "  BAT[\"2 × 18650 + BMS<br/>6,0-8,4 V\"] --> SW[\"Interruptor + fusible 3 A\"]\n"
      "  SW --> TB[\"TB6612<br/>PWM ≤ 70 %\"] --> TT[\"2 motores TT<br/>100 nF c/u\"]\n"
      "  SW --> R5[\"Regulador 5 V<br/>de la placa GVS\"] --> ESPC[\"ESP32 carro → 3,3 V\"] --> LC[\"IR ×5, cuna, encoders, VL53L0X\"]\n"
      "  R5 --> US[\"HC-SR04\"]\n```\n")

    w("## 3. Cómo se simuló\n")
    w("- **Paso de 10 ms.** Un fusible necesita cientos de ms de sobrecorriente para abrir; un regulador reacciona "
      "en ~0,1 ms (eso lo cubren los condensadores, sección 7). 10 ms basta para ver cada arranque de servo.")
    w("- **Planta**: las dos cintas a la vez, con los tiempos de `tiempos_ms`: cinta de monedas cada "
      f"{p['tiempos_ms']['avance_casilla_monedas']} + {p['tiempos_ms']['pausa_casilla_monedas']} ms (desvío en una de cada dos "
      "piezas, carrusel un tubo en cada pausa); cinta de vasos: avance, tapa y prensa 0→180→0 (la leva aprieta la tapa 0,2 s "
      "con los 0,5 mm de apriete del final de la carrera, sin resorte limitador: el servo casi trabado), y **después** el empujador (la regla de diseño: prensa y empujador nunca a la "
      "vez). En la ventana se suelta además un lote (carrusel media vuelta + obturador) y la canaleta le suelta un vaso al carro.")
    w("- **Servos**: al arrancar piden su corriente de trabado ~30 ms (el motor parte de cero y nada limita la corriente), "
      "después la de movimiento y al llegar la de reposo.")
    w(f"- **Paso a paso**: el A4988 es un *chopper*: saca de 12 V solo la POTENCIA (cobre I²·R = {_n(I_TRIP**2*NEMA_R_FASE)} W, "
      f"driver {_n(I_TRIP**2*A4988_RDS)} W, más el trabajo mecánico), no 1 A por fase. Quieto sigue a corriente plena "
      "(el A4988 no la reduce solo).")
    w("- **Carro**: modelo de motor DC (V = I·R + Ke·ω, par = Kt·I·η de la caja) con los datos típicos del TT 1:48 "
      f"(R ≈ {_n(TT_R,1)} Ω, {_n(TT_I0)} A sin carga, Ke ≈ {_n(TT_KE,3)} V·s/rad en la rueda); PWM necesario D = "
      "(I·R + Ke·ω)/V_batería y corriente de batería = D·I. Perfil del recorrido a partir de la pista y de las "
      "velocidades del control (arranque con rampa de 1 m/s², rectas a 0,40 m/s, curvas, 3 evasiones con giros "
      "sobre su eje, meta, media vuelta, vuelta y entrada de reversa contra el tope con PWM 35 %).\n")
    w("Cargas usadas (corriente en su propio riel):\n")
    w("| Carga | Riel | Reposo | Nominal | Pico | Dato |")
    w("|---|---|---|---|---|---|")
    for k, (riel, rep, nom, pic, dato) in CARGAS.items():
        w(f"| {k} | {RIELES[riel].nombre} | {_ma(rep)} | {_ma(nom)} | {_ma(pic)} | {dato} |")
    w("")

    w("## 4. Ciclo de la planta: corriente de cada riel\n")
    if img:
        w("![Corriente de cada riel durante un ciclo real de la planta](capturas/electrica-ciclo-planta.png)\n")
    else:
        w(_xychart(R["planta"]["t"], R["planta"]["series"]["6V"], "Riel de 6 V (servos)"))
    w("Los picos del riel de 6 V son los arranques de los servos y la prensa apretando la tapa; la base del de 12 V "
      "son los dos NEMA17 sosteniendo su posición. Presupuesto por riel:\n")
    w("| Riel | Promedio | Pico | Límite | Uso en el pico | Margen |")
    w("|---|---|---|---|---|---|")
    for rid, d in ri.items():
        w(f"| {RIELES[rid].nombre} | {_ma(d['promedio'])} | {_ma(d['pico'])} | {_n(d['limite'])} A | "
          f"{d['uso_pico']*100:.0f} % | {d['margen']*100:.0f} % |")
    w("")
    w(f"**Consumo desde la red**: {_n(R['red_W'][0],1)} W promedio y {_n(R['red_W'][1],1)} W de pico (fuente al "
      f"{ETA_FUENTE*100:.0f} % de rendimiento a esta carga baja, más {_n(P_VACIO_FUENTE)} W en vacío) → "
      f"{_n(R['red_A'][0])} A promedio a 110 V (factor de potencia ~{_n(FACTOR_POTENCIA)}: una fuente de 60 W no tiene PFC). "
      "Sin contar el portátil.\n")

    w("### Fusibles\n")
    w("Desde el 2026-10-24 hay **un solo fusible** en el +12 V, a la salida de la fuente (antes eran cuatro, uno por "
      "rama). Un fusible lento aguanta su corriente nominal indefinidamente y abre con ~2 veces en segundos: los "
      "picos de 30 ms de un servo no lo abren; lo que protege es un corto o un motor trabado de forma sostenida. "
      f"Se dimensionó con esta simulación: el pico del ciclo es {_ma(fu['Fusible principal']['pico'])} y el peor caso "
      f"posible del +12 V (el XL4015 en su límite de corriente de {_n(LIMITE_CC_XL4015_A, 1)} A más el pico de las otras "
      f"ramas) es {_n(R['peor_12v'])} A: un fusible lento de **{_n(FUSIBLE_PRINCIPAL_A, 0)} A** no abre en ninguno de los "
      "dos y queda bajo los 7 A que aguanta el 18 AWG de la caja.\n")
    w("| Fusible | Protege | Promedio | Pico en el ciclo | Margen en el pico |")
    w("|---|---|---|---|---|")
    for nombre, d in fu.items():
        w(f"| {nombre} ({_n(d['amperios'],0)} A) | {d['que']} | {_ma(d['promedio'])} | {_ma(d['pico'])} | {d['margen']*100:.0f} % |")
    w("")
    w("### Reguladores: rendimiento y calor\n")
    w("| Regulador | Potencia que entrega (prom. / pico) | Rendimiento | Calor (prom. / pico) |")
    w("|---|---|---|---|")
    for nombre, d in rg.items():
        w(f"| {nombre} | {_n(d['sale_W'][0])} / {_n(d['sale_W'][1])} W | {d['eta']*100:.0f} % | "
          f"{_n(d['disipa_W'][0])} / {_n(d['disipa_W'][1])} W |")
    w("")
    w("### Peores casos (no ocurren en el ciclo normal; calculados)\n")
    w("| Caso | Riel | Corriente | Límite | Fusible |")
    w("|---|---|---|---|---|")
    for c in R["peores"]:
        ok = "✔" if c["i"] <= c["limite"] else "✘"
        w(f"| {c['caso']} | {c['riel']} | {_n(c['i'])} A {ok} | {_n(c['limite'])} A | {c['fusible']} |")
    w("")

    w("## 5. Recorrido del carro\n")
    if img:
        w("![Corriente de la batería y de cada motor durante un recorrido completo](capturas/electrica-ciclo-carro.png)\n")
    else:
        w(_xychart(R["carro"]["t"], R["carro"]["series"]["BAT"], "Corriente de la batería"))
    w(f"- Recorrido completo (salida, 3 evasiones, meta, vuelta, muelle): **{_n(au['recorrido_s'],0)} s**, "
      f"{_ma(au['i_recorrido'])} promedio de la batería, {_ma(ri['BAT']['pico'])} de pico.")
    w(f"- Motor: hasta {_ma(au['i_motor_max'])} (arranques y el tope del muelle); el PWM más alto pedido con la batería a "
      f"7,4 V fue {au['duty_max']*100:.0f} %.")
    w(f"- Voltaje de la batería en el pico: {_n(au['v_min_pico'])} V (resistencia interna + BMS + fusible + interruptor ≈ "
      f"{_n(R_BATERIA*1000,0)} mΩ).")
    w(f"- **Autonomía** con {CAPACIDAD_MAH} mAh útiles al {FRACCION_UTIL*100:.0f} % ({_n(au['util_mah'],0)} mAh): "
      f"**{_n(au['h_recorriendo'],1)} h andando** (≈ {au['recorridos_por_carga']:.0f} recorridos) o "
      f"**{_n(au['h_esperando'],1)} h esperando** en el muelle con la radio encendida ({_ma(au['i_espera'])}). "
      "La sustentación dura mucho menos: una carga alcanza sobrada.\n")

    w("## 6. Cada conexión, punto por punto\n")
    w("Una fila por hilo de `sim/conexiones.py` (la misma lista que dibuja el visor 3D y `docs/conexiones.md`). "
      "Corriente nominal = promedio en la simulación (o el consumo típico si la carga no cambia); pico = el máximo. "
      "Caída = corriente pico × resistencia de ESE hilo (la del circuito es ida + vuelta: sección 6.1). "
      "Calibre: 18 AWG potencia de la caja, 22 AWG servos/motores/M18, 24 AWG señales e I2C de campo, 26 AWG Dupont, "
      "28 AWG los hilos de alimentación de un cable USB.\n")
    w("| # | Cable | De → A | Señal | Voltaje | I nom / pico | Cable | Largo | Caída | Protección |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for i, f in enumerate(filas, 1):
        w(f"| {i} | {f['cable']} | `{f['de']}` → `{f['a']}` | {f['funcion']} | {f['nivel']} | "
          f"{_ma(f['i_nom'])} / {_ma(f['i_pico'])} | {f['awg']} AWG ({_n(OHM_POR_M[f['awg']],3)} Ω/m) | "
          f"{_n(f['largo'])} m | {f['caida']*1000:.0f} mV | {f['prot']} |")
    w("")
    w("### 6.1 Caída de ida y vuelta en las cargas que importan\n")
    w("| Carga | Nominal | Caída total en el pico | Le llega | Mínimo que acepta |")
    w("|---|---|---|---|---|")
    for c in caidas_por_carga(filas):
        ok = "✔" if c["v_carga"] >= c["minimo"] else "✘"
        w(f"| {c['carga']} | {_n(c['v_nom'],1)} V | {c['caida']*1000:.0f} mV | {_n(c['v_carga'])} V {ok} | {_n(c['minimo'])} V |")
    w("")

    w("## 7. Valores de los pasivos, con su cálculo\n")
    vr = vref_a4988()
    w("**Vref del A4988 (1 A por fase).** El driver corta la corriente cuando la caída en su resistencia de sensado "
      "Rs llega a Vref/8: I_trip = Vref / (8·Rs) → Vref = 8·Rs·I. Rs está impresa en el módulo (R050, R068 o R100):\n")
    w("| Rs del módulo | Vref para 1 A |")
    w("|---|---|")
    for rs, v in vr.items():
        w(f"| {_n(rs,3)} Ω | **{_n(v,3)} V** |")
    w("\nSe mide con el multímetro entre el potenciómetro del módulo y GND, con el driver alimentado y sin pasos. "
      "1 A (el motor admite 1,7 A) deja el motor tibio y al A4988 sin disipador forzado. Con micropaso los dos "
      f"devanados siguen seno y coseno: el cobre disipa I² · R = 1² · {_n(NEMA_R_FASE, 1)} Ω = **1,5 W continuos mientras "
      "la línea anda**, porque los drivers no se sueltan entre casillas (`a4988_reposo_ms` = "
      f"{cargar_parametros()['firmware']['a4988_reposo_ms']} ms, más que las pausas de 1000 y 1400 ms); solo se "
      "sueltan en las esperas largas. Con 7-9 °C/W de la carcasa son ~36-39 °C a 25 °C de ambiente (cumple con los "
      "separadores de nailon; si en la prueba de banco pasa de 45 °C, Vref para 0,8 A).\n")
    d = divisor_echo()
    w(f"**Divisor del ECHO del HC-SR04 (1 kΩ arriba, 2 kΩ abajo).** V_GPIO = 5 V · 2k/(1k+2k) = **{_n(d['v_gpio'])} V** "
      f"(< {_n(V_GPIO_MAX,1)} V máximo del pin y > {_n(VIH_MIN)} V que el ESP32 lee como 1). Si el ECHO de un clon sale "
      f"con 4,5 V: {_n(d['v_gpio_echo_bajo'])} V, sigue siendo 1. Consume {_n(d['i_ma'])} mA solo mientras ECHO está alto; "
      f"la resistencia vista es {d['r_thevenin']:.0f} Ω y con ~20 pF el retardo es {d['tau_ns']:.0f} ns (despreciable: "
      "1 mm de distancia son 5,8 µs).\n")
    for nombre, c in (("bus I2C 1 (largo, 1,7 m; las dos de 2,2 kΩ soldadas en línea en los empalmes)", 170),
                      ("bus I2C 0 (corto, al PCA9685, 10 kΩ del módulo)", 35)):
        r = 2200 if "largo" in nombre else 10000
        q = pullup_i2c(r, c)
        w(f"**Pull-ups del {nombre}: {_n(r / 1000, 1)} kΩ con ~{c} pF.** t_r = 0,8473·R·C = **{q['tr_ns']:.0f} ns** "
          f"(máximo 1000 ns a 100 kHz, 300 ns a 400 kHz). R mínima = (3,3 − 0,4 V)/3 mA = {q['r_min']:.0f} Ω: "
          f"{'cumple' if r >= q['r_min'] else 'NO cumple'}; con la línea en bajo circula {_n(q['i_bajo_ma'])} mA.\n")
    h = pullup_hall()
    w(f"**Pull-up de 10 kΩ del Hall en el GPIO 39** (el 39 no tiene pull-up interno). Con el A3144 conduciendo "
      f"pasan {_n(h['i_ma'])} mA y el pin queda en ~{_n(h['v_bajo'])} V (< {_n(h['vil_max'])} V = 0 seguro); suelto, 3,3 V.\n")
    w("**Entradas del capacitivo y del inductivo sin optoacoplador (2026-10-24).** El cable negro (salida NPN) llega "
      "al GPIO por un diodo en serie (cátodo hacia el sensor) y el GPIO tiene una pull-up de 10 kΩ a 3,3 V (G35 y G36 "
      "no tienen pull-up interno). Sensor libre: el diodo queda en inverso aunque el sensor traiga su resistencia a "
      "12 V, y el pin lee 3,3 V. Sensor detectando: el NPN conduce y el pin queda en V_ce + V_f, que tiene que ser "
      f"menor que {_n(VIL_MAX, 3)} V (lo máximo que el ESP32 lee como 0). Con V_ce = {_n(V_CE_NPN, 1)} V (la salida a "
      "0,3 mA; la hoja da ≤ 1,5 V a 200 mA):\n")
    w("| Diodo | V_f a ~0,3 mA | Pin al detectar | Margen contra 0,825 V | Pin libre |")
    w("|---|---|---|---|---|")
    for dd in DIODOS_ENTRADA:
        e = entrada_npn(dd)
        ok = "✔" if e["lee_cero"] else "✘"
        w(f"| {dd}{' (el elegido)' if dd == DIODO_ENTRADA else ''} | {_n(DIODOS_ENTRADA[dd]['vf'])} V ({DIODOS_ENTRADA[dd]['nota']}) | "
          f"{_n(e['v_bajo'])} V {ok} | {e['margen_v'] * 1000:.0f} mV | {_n(e['v_alto'])} V |")
    e = entrada_npn()
    w(f"\nCon un 1N4148 el 0 queda en el borde (cualquier ruido o un sensor con más V_ce lo lee como 1): por eso va un "
      f"**Schottky {e['diodo']}** (mismo precio). La lógica no cambia: sigue **activa en bajo** "
      "(`firmware.activo_bajo`: capacitivo e inductivo en `true`, igual que con el PC817). La pull-up gasta "
      f"{_n(e['i_ma'])} mA mientras el sensor detecta. Lo que se pierde frente al optoacoplador es el aislamiento: un "
      "cable de 12 V pelado tocando el negro llegaría al diodo, no al pin (el diodo lo bloquea).\n")
    pl = panel_luz()
    w(f"**Resistencia de {_n(PANEL_R_SERIE, 1)} Ω 1 W en serie con el panel de luz (en línea en su +5 V, del lado de la "
      f"caja).** Las 2 tiras 2835 de 20 LED piden {_n(PANEL_TIRAS * PANEL_I_TIRA_5V)} A a 5 V: "
      f"{_n(5 * PANEL_TIRAS * PANEL_I_TIRA_5V, 1)} W dentro de la caja de luz de PLA, que llegaría a ~65 °C (esfuerzos.md; "
      "la Tg del PLA es 55-60 °C). Cada tira se modela como la rodilla de los LED blancos "
      f"({_n(PANEL_V_RODILLA, 1)} V) más la resistencia que trae cada LED: las dos en paralelo son "
      f"{_n(pl['r_tiras'])} Ω. Con la resistencia: I = (5 − {_n(PANEL_V_RODILLA, 1)}) / ({_n(pl['r_tiras'])} + "
      f"{_n(PANEL_R_SERIE, 1)}) = **{_n(pl['i'])} A**, {_n(pl['v_tiras'])} V en las tiras y **{_n(pl['p_tiras'])} W** en "
      f"ellas (máximo {_n(PANEL_P_MAX_W, 1)} W); la resistencia disipa {_n(pl['p_resistencia'])} W (por eso de 1 W, y "
      "fuera del PLA). Con una rodilla de 2,6 o 3,0 V quedan "
      f"{_n(panel_luz(v_rodilla=2.6)['p_tiras'])} y {_n(panel_luz(v_rodilla=3.0)['p_tiras'])} W. Equivale a 6,8 Ω por "
      "tira. No va un MOSFET con PWM: el ESP32 fijo no tiene GPIO libres fuera de los de arranque y el PCA9685 "
      "trabaja a 50 Hz (los servos), que la cámara de vasos vería como parpadeo en el contraluz. Se comprueba "
      "midiendo la corriente del panel ya armado: I · V_tiras ≤ 1,5 W; si pasa, 4,7 Ω.\n")
    cd = condensadores()
    w(f"**1000 µF en la bornera V+ del PCA9685.** Cuando la prensa arranca pide 2,5 A de golpe; el buck tarda ~100 µs "
      f"en reaccionar y mientras tanto la corriente sale del condensador: ΔV = I·Δt/C = 2,5 A · 100 µs / 1000 µF = "
      f"**{_n(cd['pca_1000uF']['dv'])} V** (sin él, el pico viaja por el cable y el voltaje se hunde lo suficiente para "
      "reiniciar un servo). Voltaje nominal ≥ 10 V (16 V recomendado).\n")
    w(f"**100 µF en VMOT de cada A4988.** El chopper toma pulsos de hasta 1 A durante ~20 µs: ΔV = 1 A · 20 µs / 100 µF = "
      f"**{_n(cd['vmot_100uF']['dv'])} V** de rizado; además absorbe el pico LC al enchufar los 12 V (sin él puede subir a "
      "~2× y pasar los 35 V del A4988). Voltaje nominal ≥ 25 V.\n")
    fm = filtro_motor_tt()
    w(f"**100 nF en los bornes de cada motor TT.** Las escobillas generan chispas de MHz: a 1 MHz el condensador es "
      f"{_n(fm['z_1mhz'],1)} Ω (las cortocircuita), a la frecuencia del PWM (1 kHz) es {fm['z_1khz']:.0f} Ω (casi no carga "
      f"al TB6612). En cada flanco del PWM se carga y descarga: C·V²·f = {_n(fm['p_mw_1khz'],1)} mW a 1 kHz "
      f"({fm['p_mw_20khz']:.0f} mW si el PWM fuera de 20 kHz): por eso el PWM se deja en 1 kHz.\n")
    pw = pwm_motor_tt()
    w("**PWM de los motores TT (de 3-6 V) con la batería 2S.** El voltaje medio en el motor es D·V_batería, así que el "
      "PWM máximo para no pasar de 6 V depende de la carga de la batería:\n")
    w("| Batería | PWM máximo para 6 V medios |")
    w("|---|---|")
    for vb, dd in pw.items():
        w(f"| {_n(vb,1)} V | {dd*100:.0f} % |")
    w("\nCon el límite fijo de ~70 % el motor nunca pasa de 5,9 V (batería llena) y, trabado, pide "
      f"{_n(0.7*8.4/(TT_R+TB6612_R))} A: dentro de los 1,2 A continuos del TB6612.\n")

    cal = R["calor"]
    w("**Calor dentro de la caja (decide el ventilador).** Lo que se queda adentro, en promedio, y cuánto subiría el aire "
      f"de la caja cerrada SIN ventilador (ΔT = P / (U·A), con U ≈ {_n(U_CAJA, 0)} W/(m²·K) estimado y "
      f"A = {_n(AREA_CAJA_M2)} m²):\n")
    w("| Qué | Calor |")
    w("|---|---|")
    for k, v in cal["partes"].items():
        w(f"| {k} | {_n(v)} W |")
    w(f"| **Total** | **{_n(cal['total_W'])} W** → **+{cal['dT_sin_ventilador']:.0f} °C** sin ventilador |")
    w(f"\n**Se deja el ventilador** (0,1 A, ~6 000 COP): los A4988 van a {_n(I_TRIP, 1)} A por fase, que es justo el límite "
      "que da la hoja para usarlos sin disipador ni aire forzado, y esa cifra es a temperatura de laboratorio; con la caja "
      f"cerrada el aire de adentro sube ~{cal['dT_sin_ventilador']:.0f} °C. Sin aire el driver se protege solo (se apaga "
      "por temperatura a 165 °C), pero la cinta se detendría en plena sustentación. Quitarlo exigiría bajar la "
      "corriente a ~0,8 A (menos par) o probarlo en el montaje.\n")

    w("## 8. Conclusiones (honestas)\n")
    for texto in conclusiones(R, filas):
        w(f"- {texto}")
    w("")
    w("## 9. Qué medir en el montaje para reemplazar lo provisional\n")
    w("- Corriente de cada servo moviéndose y trabado (multímetro en serie en el V+ del canal, o pinza DC).")
    w("- Rs de los A4988 (mirar la serigrafía) y su Vref ya ajustado.")
    w("- Consumo real del panel de luz y del anillo (el dato más incierto de la tabla).")
    w("- Qué regulador trae la placa GVS del carro (lineal o conmutado) y su temperatura tras 10 min.")
    w("- Corriente de la batería con el carro andando (pinza o multímetro en serie en el fusible).")
    w("- Voltaje que le llega a cada webcam (5 V en el puerto del portátil y en la cámara).")
    w("- V_ce real de la salida de cada M18 conduciendo (multímetro en el cable negro con el sensor detectando): con "
      "más de 0,5 V, revisar el margen de la entrada.")
    return "\n".join(L) + "\n"


def conclusiones(R: dict, filas: list[dict]) -> list[str]:
    ri, fu, rg, au = R["rieles"], R["fusibles"], R["reguladores"], R["autonomia"]
    c = []
    ok_rieles = [RIELES[k].nombre for k, d in ri.items() if d["pico"] <= d["limite"]]
    mal = [RIELES[k].nombre for k, d in ri.items() if d["pico"] > d["limite"]]
    c.append(f"En el ciclo simulado **{len(ok_rieles)} de {len(ri)} rieles** quedan bajo su límite en el pico"
             + (f"; NO alcanzan: {', '.join(mal)}." if mal else "."))
    peor12 = R["peor_12v"]
    c.append(f"**Fuente de 12 V 5 A (ahorro 2026-10-24, antes 10 A):** en el ciclo llega a {_ma(ri['12V']['pico'])} "
             f"({ri['12V']['uso_pico']*100:.0f} % en el pico) y el peor caso posible ({_n(peor12, 1)} A: el XL4015 en su "
             f"límite de {_n(LIMITE_CC_XL4015_A, 1)} A + el pico de lo demás) también cabe. Los 10 A de antes se habían "
             "elegido para los 6 servos trabados a la vez (7,8 A en 6 V), que con el buck de 5 A ya no pueden llegar "
             "a la fuente.")
    c.append(f"**Buck de servos XL4015 de 5 A (antes XL4016 de 9 A):** el riel de 6 V llega a {_ma(ri['6V']['pico'])} "
             f"(la prensa apretando la tapa): {ri['6V']['margen']*100:.0f} % de margen. Cabe porque prensa y empujador "
             "nunca arrancan a la vez: en esta simulación nunca piden corriente juntos y en la placa lo impide "
             "`firmware/fijo/estacion.py` (`EXCLUYENTES = {\"prensa\": \"empujador\", \"empujador\": \"prensa\"}`: el "
             "segundo espera a que el primero vuelva a reposo; lo prueba `tests/firmware/test_firmware.py`, "
             "`test_prensa_y_empujador_nunca_se_mueven_a_la_vez`). Los peores casos con todo trabado a la vez (5,3 A "
             f"con la regla) pasan los 5 A unos ms: el trimmer de corriente del XL4015 en {_n(LIMITE_CC_XL4015_A, 1)} A "
             "los corta, el riel de 6 V se hunde y los servos se frenan; nada se quema.")
    fw0 = cargar_parametros()["firmware"]
    c.append("Los NEMA17 consumen casi lo mismo quietos que andando (~0,2 A cada uno de 12 V): el A4988 mantiene la "
             "corriente plena mientras ENABLE esté activo (no tiene corriente de reposo reducida propia). El firmware "
             f"suelta ENABLE (G13 en 1) cuando las dos cintas llevan {fw0['a4988_reposo_ms']} ms quietas: más que las "
             "pausas normales, así que con la línea andando nunca se sueltan (este ciclo no cambia); ahorra en las "
             "esperas largas. La cinta indexada no tiene carga que la arrastre y la cámara re-sincroniza igual.")
    lm = rg["LM2596 (5 V)"]
    c.append(f"El LM2596 disipa {_n(lm['disipa_W'][1])} W en el pico con el panel y el anillo prendidos: tibio-caliente "
             "sin disipador; queda en el flujo del ventilador de la caja, que es donde debe ir (el ventilador se "
             "queda: ver el calor de la caja en la sección 7).")
    e = entrada_npn()
    c.append(f"**Sin optoacopladores:** el capacitivo y el inductivo van al GPIO con un diodo {e['diodo']} y una pull-up "
             f"de 10 kΩ: el pin queda en {_n(e['v_bajo'])} V al detectar ({e['margen_v']*1000:.0f} mV bajo el 0 del ESP32) y "
             "nunca ve los 12 V. Sigue activo en bajo (no cambia nada en el firmware ni en la simulación). Con un 1N4148 el "
             "margen no alcanza: por eso es Schottky.")
    ams = rg["AMS1117-3.3 (ESP32 fijo)"]
    c.append(f"El regulador del ESP32 fijo carga con toda la lógica de 3,3 V ({_ma(ri['3V3F']['pico'])} de pico, "
             f"{_n(ams['disipa_W'][0])} W de calor): bien, pero no conviene colgarle más sensores de 3,3 V.")
    l5 = rg["5 V lineal del carro (8,4 V, batería llena)"]
    c.append(f"**Carro, regulador de 5 V: queda justo.** `sim/conexiones.py` lleva la batería al jack de la placa GVS "
             f"(regulador lineal), mientras `docs/revision-final.md` §4 habla de un buck de 5 V. Con el lineal y la batería "
             f"llena disipa {_n(l5['disipa_W'][0])} W promedio y {_n(l5['disipa_W'][1])} W en los picos de la radio: "
             "cerca del límite de un SOT-223. Recomendado: el mini-buck (MP1584 o similar) que dice la revisión, "
             "o comprobar la temperatura en el montaje.")
    c.append(f"**Límite de PWM de los motores TT:** `firmware/carro/hw.py` recorta el PWM a "
             f"{_n(fw0['carro_pwm_max'], 2)} (`firmware.carro_pwm_max`) también después de la corrección integral (antes "
             "podía llegar a 1,0: trabado, 1,53 A por motor, más que los 1,2 A continuos del TB6612). Con el tope quedan "
             f"1,07 A por motor. En el recorrido normal el control pide {au['duty_max']*100:.0f} % con 7,4 V: con la "
             "batería a medio cargar el carro va apenas más lento que `velocidad_linea_m_s`.")
    c.append(f"**Bus I2C largo:** `firmware/fijo/hw.py` crea el `SoftI2C` del bus largo (I2C 1) a "
             f"{fw0['i2c_bus_largo_hz'] // 1000} kHz (`firmware.i2c_bus_largo_hz`), como dice la revisión final. Con "
             f"2,2 kΩ y 170 pF la subida es de {pullup_i2c()['tr_ns']:.0f} ns: cumple a 100 kHz (1000 ns); a 400 kHz "
             "(300 ns) no cumpliría.")
    fw = cargar_parametros()["firmware"]
    giro = cargar_parametros()["tiempos_ms"]["carrusel_giro"]
    un_tubo = fw["carrusel_pasos_por_vuelta"] / 6 * fw["carrusel_ms_por_paso"] / 1000
    rampa = giro / 1000 - 3 * un_tubo                     # lo que la rampa suma a cada giro
    c.append(f"**Tiempo del carrusel:** el firmware da un medio paso cada {fw['carrusel_ms_por_paso']} ms con un Timer "
             f"(500 Hz), con una rampa de arranque y parada ({fw['carrusel_rampa_ms']} ms bajando a "
             f"{fw['carrusel_ms_por_paso']} en {fw['carrusel_rampa_pasos']} medios pasos: los 600 Hz de la hoja de datos son "
             f"en vacío) → un tubo (60°) tarda {_n(un_tubo + rampa)} s y media "
             f"vuelta {_n(3 * un_tubo + rampa)} s; `tiempos_ms.carrusel_giro` ya dice eso ({giro} ms). "
             "Eléctricamente no cambia nada (0,24 A). En `control/tiempos.py` los dos chequeos del carrusel quedan en "
             "NO CABE a propósito: la cinta de monedas espera al carrusel en esos ciclos (~2,5 s de más al girar al "
             "tubo opuesto y ~7 s una vez por lote).")
    peor_caida = max(caidas_por_carga(filas), key=lambda x: x["caida"])
    c.append(f"Caídas en los cables: la peor es {peor_caida['carga']} con {peor_caida['caida']*1000:.0f} mV en su pico; "
             "todas las cargas reciben más de su mínimo. Sin hub (2026-10-24) cada webcam y el ESP32 van a su propio "
             "puerto del portátil: ninguno pide más de 0,35 A (un USB 2.0 da 0,5 A). El cable de cada webcam es más "
             f"largo que al hub ({_n(LARGO_USB_CENITAL)} m la cenital y {_n(LARGO_USB_VASOS)} m la de vasos, con holgura): la "
             "de vasos necesita su extensión USB de 1 m y la cenital también si su cable trae solo 1,5 m. Con los hilos "
             "de 28 AWG les llegan ~4,7 V: sobre los 4,40 V que la norma USB 2.0 exige que acepte el aparato.")
    c.append(f"Carro: con 2 × 18650 de {CAPACIDAD_MAH} mAh hay {_n(au['h_recorriendo'],1)} h de marcha; la batería no "
             "es un problema para la sustentación.")
    c.append("Todo esto está calculado con corrientes de hoja de datos: son cotas razonables, no mediciones. Los números "
             "que más pueden moverse son el panel de luz, el anillo y la corriente real de los servos con su carga.")
    return c


def main() -> None:
    texto = generar_markdown()
    (DOCS / "electrica.md").write_text(texto, encoding="utf-8")
    R = resumen()
    print("docs/electrica.md escrito.")
    for rid, d in R["rieles"].items():
        print(f"  {RIELES[rid].nombre:28s} pico {d['pico']:.2f} A de {d['limite']:.2f} A (margen {d['margen']*100:.0f} %)")
    for nombre, d in R["fusibles"].items():
        print(f"  fusible {nombre:18s} pico {d['pico']:.2f} A de {d['amperios']:.0f} A")
    print(f"  peor caso del +12 V {R['peor_12v']:.2f} A; calor en la caja {R['calor']['total_W']:.1f} W "
          f"(+{R['calor']['dT_sin_ventilador']:.0f} °C sin ventilador)")


if __name__ == "__main__":
    main()
