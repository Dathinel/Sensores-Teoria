"""Masa (peso) de todo el montaje y comprobaciones de par con esas masas.

Fuente única: config/masas.yaml (componentes del catálogo y lo demás que pesa) y
config/precios.yaml (las piezas impresas, los tramos de perfil 2020 y la tornillería, que ya están
contados ahí para el costo: se reusan, no se copian). `app.documentos` genera docs/peso.md.

Por qué importa el peso (usuario, 2026-09-28: "peso total del montaje"): con las masas se
comprueba si los motores elegidos de verdad alcanzan (NEMA 17 de las cintas, MG996R de la prensa y
del empujador, motores TT del carro con el vaso lleno) en vez de suponerlo. Si algo no alcanza, el
documento lo dice en grande: no se esconde.

    python -m app.masas        imprime el resumen (docs/peso.md lo escribe app.documentos)
"""

from __future__ import annotations

import math
from pathlib import Path

import yaml

from app import costos

RUTA = Path(__file__).resolve().parent.parent / "config" / "masas.yaml"
ORDEN_ZONAS = ["Cinta de monedas", "Almacén", "Cinta de vasos", "Pórtico", "Canaleta y muelle", "Carro",
               "Caja de control", "Pista y base"]
FACTOR_SEGURIDAD = 2.0      # un motor "alcanza" si da al menos el doble de lo que se le pide


def cargar() -> dict:
    return yaml.safe_load(RUTA.read_text(encoding="utf-8"))


def _num(v: float, dec: int = 1) -> str:
    return costos._num(v, dec)


def _kg(gramos: float) -> str:
    return f"{_num(gramos / 1000, 2)} kg"


# ---------------------------------------------------------------------------------------------
# Filas: una por cosa que pesa
# ---------------------------------------------------------------------------------------------

def filas(datos: dict | None = None, precios: dict | None = None) -> list[dict]:
    """Una fila por cosa que pesa: {zona, nombre, cantidad, masa_g (c/u), total_g, fuente, origen}.

    origen dice de dónde salió: "catálogo" (componente de sim/catalogos.py), "impresa" (pieza de
    precios.yaml: volumen x densidad x llenado, SIN el desperdicio, que se queda en la impresora),
    "perfil" (tramo medido x kg/m), "tornillería" (contada por zona) u "otro" (masas.yaml: otros).
    """
    from sim.catalogos import CATALOGO_SENSORES, COMPONENTES

    datos = datos or cargar()
    precios = precios or costos.cargar()
    catalogo = {c["id"]: c for c in COMPONENTES}
    catalogo.update({s["id"]: s for s in CATALOGO_SENSORES})
    mat = datos["materiales"]
    out = []

    def fila(zona, nombre, cantidad, masa_g, fuente, origen, como=""):
        out.append({"zona": zona, "nombre": nombre, "cantidad": cantidad, "masa_g": masa_g,
                    "total_g": masa_g * cantidad, "fuente": fuente, "origen": origen, "como": como or ""})

    # 1. Componentes del catálogo (los impresos se cuentan en el punto 2, por pieza).
    for id_, d in datos["componentes"].items():
        if d.get("impreso") or not d.get("masa_g"):
            continue
        c = catalogo.get(id_, {})
        fila(d["zona"], c.get("nombre", id_), d.get("cantidad", c.get("cantidad", 1)), d["masa_g"], d["fuente"],
             "catálogo", d.get("como", ""))
    # 2. Piezas impresas: la masa de la PIEZA (lo que se desperdicia al imprimir no se monta).
    for p in costos.piezas_impresas(precios):
        imp = precios["estructura_3d"]["impresion"]
        g = p["volumen_cm3"] * imp["densidad_g_cm3"] * p["factor"]
        fila(p["zona"], f"{p['nombre']} (impresa)", p["cantidad"], g, "estimado", "impresa",
             f"{_num(p['volumen_cm3'])} cm³ x {_num(imp['densidad_g_cm3'], 2)} g/cm³ x {p['factor']:.0%} de llenado")
    # 3. Perfil 2020 por tramo: largo x kg/m.
    per = precios["estructura_3d"]["perfil"]
    for t in per["tramos"]:
        fila(t["zona"], f"Perfil 2020: {t['nombre'][0].lower() + t['nombre'][1:]} ({t['largo_mm']} mm)", t.get("cantidad", 1),
             t["largo_mm"] / 1000 * per["kg_por_m"] * 1000, "hoja_de_datos", "perfil",
             f"{t['largo_mm']} mm x {_num(per['kg_por_m'], 2)} kg/m")
    # 4. Tornillería, escuadras y pies, contados por zona (sin el repuesto, que no se monta).
    tipos = precios["estructura_3d"]["tornilleria"]["tipos"]
    for zona, cuenta in costos.tornillos_por_zona(precios).items():
        for t, n in cuenta.items():
            fila(zona, tipos[t]["nombre"], n, tipos[t]["masa_g"], tipos[t]["fuente"], "tornillería")
    # 5. Lo demás que pesa (bandas, rodillos, bastidores, gabinete, chasis, tablero...).
    for o in datos["otros"]:
        if "masa_g" in o:
            masa = o["masa_g"]
        else:
            masa = o["volumen_cm3"] * mat[o["material"]]
        fila(o["zona"], o["nombre"], o.get("cantidad", 1), masa, o["fuente"], "otro", o.get("como", ""))
    return out


def por_zona(datos: dict | None = None, precios: dict | None = None) -> dict[str, float]:
    """Gramos por zona, en el orden de ORDEN_ZONAS."""
    tot = {z: 0.0 for z in ORDEN_ZONAS}
    for f in filas(datos, precios):
        tot[f["zona"]] = tot.get(f["zona"], 0.0) + f["total_g"]
    return tot


def total(datos: dict | None = None, precios: dict | None = None) -> float:
    return sum(f["total_g"] for f in filas(datos, precios))


def _masa_de(fs: list[dict], zona: str, contiene: str) -> float:
    return sum(f["total_g"] for f in fs if f["zona"] == zona and contiene.lower() in f["nombre"].lower())


# ---------------------------------------------------------------------------------------------
# Comprobaciones
# ---------------------------------------------------------------------------------------------

def _parametros() -> dict:
    from app.configuracion import cargar_parametros

    return cargar_parametros()


def vaso_lleno_g(datos: dict | None = None, parametros: dict | None = None) -> float:
    """Peor caso de un vaso lleno: vaso + tapa + un lote entero de la moneda más pesada."""
    datos = datos or cargar()
    parametros = parametros or _parametros()
    c = datos["comprobaciones"]
    return (c["carro"]["masa_vaso_vacio_g"] + c["carro"]["masa_tapa_g"]
            + parametros["planta"]["monedas_por_vaso"] * c["nema17"]["masa_moneda_max_g"])


def _cinta(nombre: str, m_banda: float, m_sep: float, m_carga: float, m_rodillo: float, d_m: float, t_s: float,
           radios: dict[str, float], c: dict, g: float) -> dict:
    """Par que pide una cinta indexada a su NEMA 17 (todo en SI: kg, m, s, N, N·m).

    El avance de una casilla (d en t segundos) se hace con un perfil triangular de velocidad:
    acelera la mitad del tiempo y frena la otra mitad. Así d = a·(t/2)² → a = 4·d / t².
    Lo que tiene que vencer el motor, llevado al radio r del rodillo motriz:
      1. Rozamiento del ramal de arriba contra la cama: F_roz = μ · (m_banda/2 + m_sep/2 + m_carga) · g
      2. Inercia de lo que se traslada:                 F_in = (m_banda + m_sep + m_carga) · a
      3. Rodamientos: cada rodillo carga 2 ramales tensos → T_rod = 2 rodillos · μ_rod · 2·T0 · r_eje
      4. Inercia de lo que gira: (I_rotor + 2·I_rodillo) · α, con α = a / r e I_rodillo ≈ m·r²
    T = (F_roz + F_in) · r + T_rod + T_giro. El disponible es el de retención escalado a la
    corriente que da el driver y a la caída de par con la velocidad (par_util_frac).
    """
    a = 4 * d_m / t_s ** 2
    m_tras = m_banda + m_sep + m_carga
    f_roz = c["mu_banda_cama"] * (m_banda / 2 + m_sep / 2 + m_carga) * g
    f_in = m_tras * a
    t_rod = 2 * c["mu_rodamiento"] * 2 * c["tension_banda_n"] * c["radio_eje_m"]
    disp = c["par_retencion_nm"] * (c["corriente_driver_a"] / c["corriente_nominal_a"]) * c["par_util_frac"]
    casos = []
    for etiqueta, r in radios.items():
        alfa = a / r
        t_giro = (c["inercia_rotor_kg_m2"] + 2 * m_rodillo * r ** 2) * alfa
        t_total = (f_roz + f_in) * r + t_rod + t_giro
        v_pico = 2 * d_m / t_s
        casos.append({"radio": etiqueta, "r_m": r, "par_nm": t_total, "margen": disp / t_total,
                      "rpm_pico": v_pico / (2 * math.pi * r) * 60, "t_roz": f_roz * r, "t_in": f_in * r,
                      "t_rod": t_rod, "t_giro": t_giro})
    peor = max(casos, key=lambda x: x["par_nm"])
    return {"nombre": nombre, "a": a, "m_banda": m_banda, "m_sep": m_sep, "m_carga": m_carga, "m_rodillo": m_rodillo,
            "f_roz": f_roz, "f_in": f_in, "disponible_nm": disp, "casos": casos, "peor": peor,
            "alcanza": peor["margen"] >= FACTOR_SEGURIDAD, "d_m": d_m, "t_s": t_s}


def comprobaciones(datos: dict | None = None, precios: dict | None = None, parametros: dict | None = None) -> dict:
    """Las cuatro comprobaciones de docs/peso.md, con cada número intermedio (para escribir la
    cuenta en el documento, no solo el resultado)."""
    datos = datos or cargar()
    precios = precios or costos.cargar()
    parametros = parametros or _parametros()
    c = datos["comprobaciones"]
    g = c["g"]
    fs = filas(datos, precios)
    n17 = c["nema17"]
    # Radio del rodillo: el del modelo 3D (Ø22) y el que usa el firmware (firmware.mm_por_vuelta_cinta
    # = π·Ø → r = mm / 2π). Desde 2026-09-28 son el mismo (69,1 mm/vuelta); si alguien vuelve a
    # separarlos, se prueban los dos y manda el peor (y docs/peso.md avisa).
    mm_vuelta = parametros["firmware"]["mm_por_vuelta_cinta"]
    r_firmware = mm_vuelta / 1000 / (2 * math.pi)
    radios = {"modelo 3D (Ø22)": n17["radio_rodillo_modelo_m"]}
    if abs(r_firmware - n17["radio_rodillo_modelo_m"]) > 0.0002:
        radios[f"firmware ({_num(mm_vuelta, 1)} mm/vuelta)"] = r_firmware
    tiempos = parametros["tiempos_ms"]
    vl = vaso_lleno_g(datos, parametros)

    # 1. NEMA 17 de la cinta de monedas.
    monedas = _cinta(
        "Cinta de monedas",
        m_banda=_masa_de(fs, "Cinta de monedas", "banda de caucho") / 1000,
        m_sep=_masa_de(fs, "Cinta de monedas", "separadores de casilla") / 1000,
        m_carga=n17["casillas_monedas_cargadas"] * n17["masa_moneda_max_g"] / 1000,
        m_rodillo=_masa_de(fs, "Cinta de monedas", "rodillos") / 2 / 1000,
        d_m=parametros["cinta_monedas"]["separacion_casilla_mm"] / 1000,
        t_s=tiempos["avance_casilla_monedas"] / 1000, radios=radios, c=n17, g=g)
    # 2. NEMA 17 de la cinta de vasos (con todos los vasos llenos: peor caso).
    vasos = _cinta(
        "Cinta de vasos",
        m_banda=_masa_de(fs, "Cinta de vasos", "banda de caucho") / 1000,
        m_sep=_masa_de(fs, "Cinta de vasos", "taco separador") / 1000,
        m_carga=n17["vasos_cargados"] * vl / 1000,
        m_rodillo=_masa_de(fs, "Cinta de vasos", "rodillos") / 2 / 1000,
        d_m=parametros["vasos"]["separacion_casilla_mm"] / 1000,
        t_s=tiempos["avance_casilla_vasos"] / 1000, radios=radios, c=n17, g=g)

    # 3. MG996R de la prensa y del empujador.
    mg = c["mg996r"]
    e = mg["excentricidad_m"]
    m_piston = _masa_de(fs, "Cinta de vasos", "pistón") / 1000
    # Par de la leva: T = F · e · sen(θ). El peor punto es θ = 90° (sen = 1); cerca de 180° (abajo,
    # justo cuando la tapa asienta) sen(θ) → 0 y la misma fuerza pide mucho menos par.
    prensa = []
    for etiqueta, f in (("tapa (máx. provisional)", max(mg["fuerza_tapa_n"])),
                        ("objetivo de la prensa (lo limita el resorte)", mg["fuerza_prensa_objetivo_n"])):
        t = (f + m_piston * g) * e
        prensa.append({"caso": etiqueta, "fuerza_n": f, "par_nm": t, "margen_6v": mg["par_bloqueo_nm_6v"] / t,
                       "margen_4v8": mg["par_bloqueo_nm_4v8"] / t})
    m_paleta = _masa_de(fs, "Cinta de vasos", "paleta del empujador") / 1000
    f_emp = mg["mu_vaso_banda"] * (vl / 1000) * g + m_paleta * g * 0.1   # + roce de la paleta en su guía (~10 % de su peso)
    t_emp = f_emp * mg["radio_manivela_m"]
    empujador = {"fuerza_n": f_emp, "par_nm": t_emp, "margen": mg["par_bloqueo_nm_6v"] / t_emp}

    # 4. Carro: masa total con el vaso lleno contra el par de los dos motores TT.
    ca = c["carro"]
    veh = parametros["vehiculo"]
    r = veh["diametro_rueda_mm"] / 2000
    v_max = parametros["firmware"]["carro_v_max_m_s"]
    v_linea = veh["velocidad_linea_m_s"]
    a_pedida = veh["aceleracion_max_m_s2"]
    m_carro = sum(f["total_g"] for f in fs if f["zona"] == "Carro") / 1000
    m_total = m_carro + vl / 1000
    f_rr = ca["crr"] * m_total * g
    f_necesaria = m_total * a_pedida + f_rr
    t_necesario = f_necesaria * r / 2                                     # por motor
    t_arranque = ca["par_motor_nm"]
    # Motor DC: el par disponible cae en línea recta con la velocidad (máximo parado, cero a la
    # velocidad sin carga): T(v) = T_arranque · (1 - v / v_max).
    def t_disp(v):
        return t_arranque * max(0.0, 1 - v / v_max)
    a_max_motor = (2 * t_arranque / r - f_rr) / m_total                   # arrancando (v = 0)
    v_fin_aceleracion = v_max * (1 - (t_necesario / t_arranque))          # hasta dónde sostiene a_pedida
    a_patina = ca["mu_llanta"] * g * ca["fraccion_peso_ruedas"] - ca["crr"] * g
    a_vuelco_carro = g * ca["distancia_cg_apoyo_m"] / ca["altura_cg_m"]
    a_vuelco_vaso = g * (parametros["vasos"]["diametro_mm"] / 2000) / ca["vaso_altura_cg_m"]
    angulo_vaso = math.degrees(math.atan(a_pedida / g))
    carro = {
        "m_carro": m_carro, "m_vaso": vl / 1000, "m_total": m_total, "masa_sim": veh["masa_kg"],
        "masa_vaso_sim": veh["masa_vaso_lleno_kg"], "r": r, "a_pedida": a_pedida, "f_rr": f_rr,
        "f_necesaria": f_necesaria, "t_necesario": t_necesario, "t_arranque": t_arranque,
        "margen_arranque": t_arranque / t_necesario, "v_linea": v_linea, "v_max": v_max,
        "t_disp_linea": t_disp(v_linea), "t_crucero": f_rr * r / 2, "margen_crucero": t_disp(v_linea) / (f_rr * r / 2),
        "v_fin_aceleracion": v_fin_aceleracion, "a_max_motor": a_max_motor, "a_patina": a_patina,
        "a_vuelco_carro": a_vuelco_carro, "a_vuelco_vaso": a_vuelco_vaso, "angulo_vaso": angulo_vaso,
        "alcanza": (t_arranque / t_necesario >= FACTOR_SEGURIDAD and v_fin_aceleracion >= v_linea
                    and a_pedida < min(a_patina, a_vuelco_carro, a_vuelco_vaso)),
    }
    return {"monedas": monedas, "vasos": vasos, "prensa": prensa, "empujador": empujador, "carro": carro,
            "vaso_lleno_g": vl, "r_firmware": r_firmware}


# ---------------------------------------------------------------------------------------------
# docs/peso.md
# ---------------------------------------------------------------------------------------------

def _veredicto(ok: bool, margen: float | None = None) -> str:
    if ok:
        return "✅ **ALCANZA**" + (f" (margen x{_num(margen)})" if margen else "")
    return "❌ **NO ALCANZA**" + (f" (margen x{_num(margen, 2)})" if margen else "")


def _md_cinta(cc: dict, n17: dict, extra: str) -> list[str]:
    p = cc["peor"]
    L = [f"### {cc['nombre']}: NEMA 17 17HS4401", "",
         f"{extra} Banda {_num(cc['m_banda'] * 1000, 0)} g, separadores {_num(cc['m_sep'] * 1000, 0)} g, carga "
         f"{_num(cc['m_carga'] * 1000, 0)} g, cada rodillo {_num(cc['m_rodillo'] * 1000, 0)} g. Avance de "
         f"{_num(cc['d_m'] * 1000, 0)} mm en {_num(cc['t_s'], 1)} s.", "",
         "```",
         f"a      = 4·d / t²                                  = 4 x {_num(cc['d_m'], 3)} / {_num(cc['t_s'], 1)}² = {_num(cc['a'], 2)} m/s²",
         f"F_roz  = μ·(m_banda/2 + m_sep/2 + m_carga)·g       = {_num(n17['mu_banda_cama'], 2)} x "
         f"{_num(cc['m_banda'] / 2 + cc['m_sep'] / 2 + cc['m_carga'], 3)} x 9,81 = {_num(cc['f_roz'], 2)} N",
         f"F_in   = (m_banda + m_sep + m_carga)·a              = {_num(cc['m_banda'] + cc['m_sep'] + cc['m_carga'], 3)} x "
         f"{_num(cc['a'], 2)} = {_num(cc['f_in'], 3)} N",
         f"T_rod  = 2 rodillos · μ_rod · 2·T0 · r_eje          = 2 x {_num(n17['mu_rodamiento'], 4)} x 2 x {n17['tension_banda_n']} x "
         f"{_num(n17['radio_eje_m'], 3)} = {_num(p['t_rod'], 5)} N·m",
         "T_giro = (I_rotor + 2·m_rodillo·r²) · a / r",
         "T      = (F_roz + F_in)·r + T_rod + T_giro",
         f"T_disp = T_retención · (I_driver / I_nominal) · {_num(n17['par_util_frac'], 2)} = {_num(n17['par_retencion_nm'], 2)} x "
         f"({_num(n17['corriente_driver_a'], 1)} / {_num(n17['corriente_nominal_a'], 1)}) x {_num(n17['par_util_frac'], 2)} = {_num(cc['disponible_nm'], 3)} N·m",
         "```", "",
         "| Radio del rodillo | r (mm) | Par pedido (N·m) | Disponible (N·m) | Margen | rpm pico |",
         "|---|---:|---:|---:|---:|---:|"]
    for x in cc["casos"]:
        L.append(f"| {x['radio']} | {_num(x['r_m'] * 1000, 1)} | {_num(x['par_nm'], 4)} | {_num(cc['disponible_nm'], 3)} | "
                 f"x{_num(x['margen'])} | {_num(x['rpm_pico'], 0)} |")
    L += ["", f"Resultado: {_veredicto(cc['alcanza'], p['margen'])} con el peor radio ({p['radio']}). "
          f"Lo que más pide es el rozamiento de la banda contra la cama ({_num(p['t_roz'], 4)} N·m de "
          f"{_num(p['par_nm'], 4)}).", ""]
    return L


def generar_md() -> str:
    datos = cargar()
    precios = costos.cargar()
    parametros = _parametros()
    fs = filas(datos, precios)
    zonas = por_zona(datos, precios)
    tot = sum(zonas.values())
    est = sum(f["total_g"] for f in fs if f["fuente"] == "estimado")
    co = comprobaciones(datos, precios, parametros)
    n17 = datos["comprobaciones"]["nema17"]
    L = [
        "# Peso del montaje",
        "",
        "> Generado por `python -m app.documentos` desde `config/masas.yaml` y `config/precios.yaml` (piezas",
        "> impresas, perfil y tornillería): no editar a mano. Masas de hoja de datos o estimadas por material",
        f"> x volumen ({datos['consultado']}): PESAR lo marcado *estimado* cuando esté en la mano.",
        "",
        f"**Peso total del montaje: {_kg(tot)}** (sin el portátil). De eso, {_kg(est)} "
        f"({est * 100 / max(tot, 1):.0f} %) son **estimados**; el resto es de hoja de datos.",
        "",
        "No hay celda de carga en el diseño (prohibidas por el grupo): estas masas son para dimensionar "
        "motores y estructura, no se miden en la línea.",
        "",
        "## Por subsistema",
        "",
        "| Subsistema | Masa | % |",
        "|---|---:|---:|",
    ]
    for z, v in zonas.items():
        L.append(f"| {z} | {_kg(v)} | {v * 100 / max(tot, 1):.0f} % |")
    L += [f"| **Total** | **{_kg(tot)}** | **100 %** |", "",
          "## Comprobaciones con estas masas", "",
          f"Criterio: un motor **alcanza** si da al menos {_num(FACTOR_SEGURIDAD, 0)} veces lo que se le pide (margen "
          "x2: cubre lo que no se sabe todavía, como la tensión real de la banda o el roce de una pieza mal alineada). "
          f"Vaso lleno en el peor caso: vaso {datos['comprobaciones']['carro']['masa_vaso_vacio_g']} g + tapa "
          f"{datos['comprobaciones']['carro']['masa_tapa_g']} g + {parametros['planta']['monedas_por_vaso']} monedas de "
          f"{_num(n17['masa_moneda_max_g'], 0)} g = **{_num(co['vaso_lleno_g'], 0)} g**.", ""]
    alertas = []
    # Radio del rodillo: aviso de la inconsistencia (no se cambia el diseño, se documenta).
    alertas_radio = None
    if abs(co["r_firmware"] - n17["radio_rodillo_modelo_m"]) > 0.0002:
        alertas_radio = (f"El radio del rodillo no coincide entre el modelo 3D (Ø22 mm) y el firmware "
                         f"(`firmware.mm_por_vuelta_cinta` = {parametros['firmware']['mm_por_vuelta_cinta']} mm → Ø"
                         f"{_num(co['r_firmware'] * 2000, 1)} mm): con Ø22 una vuelta mueve "
                         f"{_num(math.pi * 22, 0)} mm. Se hacen las cuentas con los dos y manda el peor; hay que "
                         "decidir el rodillo real y corregir el otro dato.")
    L += _md_cinta(co["monedas"], n17, f"Peor caso: las {n17['casillas_monedas_cargadas']} casillas de la banda con "
                   f"una moneda de {_num(n17['masa_moneda_max_g'], 0)} g.")
    L += _md_cinta(co["vasos"], n17, f"Peor caso: {n17['vasos_cargados']} vasos llenos sobre la banda.")
    if alertas_radio:
        L += [f"> ⚠️ {alertas_radio}", ""]
    else:
        L += [f"Rodillo: Ø22 mm, el mismo en el modelo 3D y en el firmware (`firmware.mm_por_vuelta_cinta` = "
              f"{_num(parametros['firmware']['mm_por_vuelta_cinta'], 1)} mm por vuelta = π·22).", ""]
    for cc in (co["monedas"], co["vasos"]):
        if not cc["alcanza"]:
            alertas.append(f"NEMA 17 de la {cc['nombre'].lower()}: margen x{_num(cc['peor']['margen'], 2)}")
    # Prensa y empujador
    mg = datos["comprobaciones"]["mg996r"]
    L += ["### MG996R de la prensa (leva excéntrica)", "",
          "```",
          "T = (F + m_pistón·g) · e · sen(θ)        peor punto: θ = 90° (sen = 1)",
          f"e = {_num(mg['excentricidad_m'] * 1000, 1)} mm;  par de bloqueo MG996R: {_num(mg['par_bloqueo_nm_4v8'], 2)} N·m a 4,8 V, "
          f"{_num(mg['par_bloqueo_nm_6v'], 2)} N·m a 6 V",
          "```", "",
          "| Fuerza en la tapa | Par pedido a 90° | Margen a 6 V | Margen a 4,8 V | Resultado |",
          "|---|---:|---:|---:|---|"]
    for p in co["prensa"]:
        ok = p["margen_6v"] >= FACTOR_SEGURIDAD
        L.append(f"| {p['caso']}: {p['fuerza_n']} N | {_num(p['par_nm'], 3)} N·m | x{_num(p['margen_6v'], 2)} | "
                 f"x{_num(p['margen_4v8'], 2)} | {_veredicto(ok)} |")
        if not ok:
            alertas.append(f"el MG996R de la prensa NO sostiene {p['fuerza_n']} N ({p['caso']}) a 90° de la leva: "
                           f"margen x{_num(p['margen_6v'], 2)} a 6 V, x{_num(p['margen_4v8'], 2)} a 4,8 V (para la tapa "
                           f"real, {max(mg['fuerza_tapa_n'])} N, sí alcanza: x{_num(co['prensa'][0]['margen_6v'], 1)})")
    obj = co["prensa"][1]
    L += ["", f"La tapa sella a presión (snap-fit: el reborde de la tapa salta sobre el labio del vaso), lo que pide "
          f"{mg['fuerza_tapa_n'][0]}-{mg['fuerza_tapa_n'][1]} N (PROVISIONAL hasta medirla); pasado el salto, apretar "
          f"más solo deforma el vaso. Por eso la prensa apunta a **{obj['fuerza_n']} N** (la tapa más dura x1,2) y el "
          f"resorte limitador del plato se elige para no pasar de ahí al final de la carrera. A 90° de la leva (el "
          f"peor punto) eso pide {_num(obj['par_nm'], 2)} N·m, el {obj['par_nm'] * 100 / mg['par_bloqueo_nm_6v']:.0f} % "
          "del bloqueo a 6 V. (Antes el catálogo decía \"≥150 N\": el MG996R con esta leva no lo sostiene en toda "
          "la carrera y la tapa no lo necesita.)", "",
          "### MG996R del empujador (manivela)", "",
          "```",
          "F = μ·m_vaso_lleno·g + roce de la paleta (10 % de su peso);   T = F · r_manivela",
          f"F = {_num(mg['mu_vaso_banda'], 2)} x {_num(co['vaso_lleno_g'] / 1000, 3)} x 9,81 + … = {_num(co['empujador']['fuerza_n'], 2)} N;"
          f"   T = {_num(co['empujador']['fuerza_n'], 2)} x {_num(mg['radio_manivela_m'], 3)} = {_num(co['empujador']['par_nm'], 4)} N·m",
          "```", "",
          f"Resultado: {_veredicto(co['empujador']['margen'] >= FACTOR_SEGURIDAD, co['empujador']['margen'])} (de "
          f"{_num(mg['par_bloqueo_nm_6v'], 2)} N·m a 6 V).", ""]
    # Carro
    ca = co["carro"]
    L += ["### Carro con el vaso lleno: motores TT 1:48", "",
          f"Masa del carro (suma de su subsistema): **{_kg(ca['m_carro'] * 1000)}**; con el vaso lleno: "
          f"**{_kg(ca['m_total'] * 1000)}**. Rueda de {_num(ca['r'] * 2000, 0)} mm; el firmware pide hasta "
          f"{_num(ca['a_pedida'], 1)} m/s² (`vehiculo.aceleracion_max_m_s2`) y {_num(ca['v_linea'], 2)} m/s en la línea.", "",
          "```",
          f"F_rr   = Crr·m·g                    = {_num(datos['comprobaciones']['carro']['crr'], 2)} x {_num(ca['m_total'], 3)} x 9,81 = {_num(ca['f_rr'], 3)} N",
          f"F      = m·a + F_rr                 = {_num(ca['m_total'], 3)} x {_num(ca['a_pedida'], 1)} + {_num(ca['f_rr'], 3)} = {_num(ca['f_necesaria'], 3)} N",
          f"T/motor = F·r / 2                   = {_num(ca['f_necesaria'], 3)} x {_num(ca['r'], 4)} / 2 = {_num(ca['t_necesario'], 4)} N·m",
          f"T_disp(v) = T_arranque·(1 - v/v_max)  (motor DC: el par cae con la velocidad), v_max = {_num(ca['v_max'], 2)} m/s",
          f"a sostenida hasta v = v_max·(1 - T/motor ÷ T_arranque) = {_num(ca['v_fin_aceleracion'], 2)} m/s",
          f"a_max (motores, parado) = (2·T_arranque/r - F_rr)/m  = {_num(ca['a_max_motor'], 1)} m/s²",
          "a_patina  = μ·g·fracción en ruedas - Crr·g           = " + _num(ca["a_patina"], 1) + " m/s²",
          "a_vuelco del carro = g·d_apoyo / h_cg                 = " + _num(ca["a_vuelco_carro"], 1) + " m/s²",
          "a_vuelco del vaso (si estuviera suelto) = g·(D/2)/h_cg = " + _num(ca["a_vuelco_vaso"], 1) + " m/s²",
          "```", "",
          "| Qué | Pedido | Disponible / límite | Margen | Resultado |", "|---|---:|---:|---:|---|",
          f"| Par por motor al arrancar | {_num(ca['t_necesario'], 4)} N·m | {_num(ca['t_arranque'], 2)} N·m | x{_num(ca['margen_arranque'])} | "
          f"{_veredicto(ca['margen_arranque'] >= FACTOR_SEGURIDAD)} |",
          f"| Llegar a {_num(ca['v_linea'], 2)} m/s acelerando a {_num(ca['a_pedida'], 1)} m/s² | {_num(ca['v_linea'], 2)} m/s | "
          f"{_num(ca['v_fin_aceleracion'], 2)} m/s | x{_num(ca['v_fin_aceleracion'] / ca['v_linea'], 2)} | "
          f"{_veredicto(ca['v_fin_aceleracion'] >= ca['v_linea'])} |",
          f"| Par por motor en crucero ({_num(ca['v_linea'], 2)} m/s) | {_num(ca['t_crucero'], 4)} N·m | {_num(ca['t_disp_linea'], 4)} N·m | "
          f"x{_num(ca['margen_crucero'])} | {_veredicto(ca['margen_crucero'] >= FACTOR_SEGURIDAD)} |",
          f"| Que las llantas no patinen | {_num(ca['a_pedida'], 1)} m/s² | {_num(ca['a_patina'], 1)} m/s² | "
          f"x{_num(ca['a_patina'] / ca['a_pedida'])} | {_veredicto(ca['a_patina'] > ca['a_pedida'])} |",
          f"| Que el carro no vuelque al frenar | {_num(ca['a_pedida'], 1)} m/s² | {_num(ca['a_vuelco_carro'], 1)} m/s² | "
          f"x{_num(ca['a_vuelco_carro'] / ca['a_pedida'])} | {_veredicto(ca['a_vuelco_carro'] > ca['a_pedida'])} |",
          f"| Que el vaso no vuelque | {_num(ca['a_pedida'], 1)} m/s² | {_num(ca['a_vuelco_vaso'], 1)} m/s² | "
          f"x{_num(ca['a_vuelco_vaso'] / ca['a_pedida'])} | {_veredicto(ca['a_vuelco_vaso'] > ca['a_pedida'])} |",
          "",
          f"El vaso va colgado del reborde en la cuna (centro de masa bajo el apoyo): a {_num(ca['a_pedida'], 1)} m/s² se inclina "
          f"como mucho {_num(ca['angulo_vaso'], 1)}° y lo frenan la espuma y la lengüeta; ni suelto se volcaría.", ""]
    if ca["m_total"] > ca["masa_sim"] + ca["masa_vaso_sim"] + 0.05:
        L += [f"> ⚠️ La simulación del carro usa `vehiculo.masa_kg` = {_num(ca['masa_sim'], 2)} kg y "
              f"`masa_vaso_lleno_kg` = {_num(ca['masa_vaso_sim'], 2)} kg ({_num(ca['masa_sim'] + ca['masa_vaso_sim'], 2)} kg); "
              f"sumando las piezas da {_num(ca['m_total'], 2)} kg. Los márgenes de arriba ya usan la masa sumada.", ""]
    if not ca["alcanza"]:
        alertas.append("carro con el vaso lleno")
    L[L.index("## Comprobaciones con estas masas") + 1:L.index("## Comprobaciones con estas masas") + 1] = (
        ["", ("> ❌ **NO ALCANZA:** " + "; ".join(alertas) + ". Detalle abajo.") if alertas else
         "> ✅ Con estas masas todos los motores alcanzan con margen x2 o más."])
    # Detalle por zona
    L += ["## Detalle por subsistema", "",
          "La cinta de monedas va primero y con todo su detalle: su NEMA 17 es el que más pasos da por turno."]
    for z in ORDEN_ZONAS:
        del_z = [f for f in fs if f["zona"] == z]
        if not del_z:
            continue
        L += ["", f"### {z}: {_kg(zonas[z])}", "", "| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |",
              "|---|---:|---:|---:|---|---|"]
        for f in sorted(del_z, key=lambda x: -x["total_g"]):
            fuente = "hoja de datos" if f["fuente"] == "hoja_de_datos" else "*estimado*"
            L.append(f"| {f['nombre']} | {f['cantidad']} | {_num(f['masa_g'])} | {_num(f['total_g'])} | {fuente} | {f['como']} |")
        L.append(f"| **Subtotal** | | | **{_num(zonas[z])}** | | |")
    return "\n".join(L) + "\n"


def alertas(datos: dict | None = None, precios: dict | None = None, parametros: dict | None = None) -> list[str]:
    """Lo que NO alcanza (vacío si todo alcanza con margen x2)."""
    co = comprobaciones(datos, precios, parametros)
    out = [f"NEMA 17 de la {c['nombre'].lower()}" for c in (co["monedas"], co["vasos"]) if not c["alcanza"]]
    out += [f"MG996R de la prensa con {p['fuerza_n']} N" for p in co["prensa"] if p["margen_6v"] < FACTOR_SEGURIDAD]
    if co["empujador"]["margen"] < FACTOR_SEGURIDAD:
        out.append("MG996R del empujador")
    if not co["carro"]["alcanza"]:
        out.append("carro con el vaso lleno")
    return out


if __name__ == "__main__":
    zonas = por_zona()
    for z, v in zonas.items():
        print(f"{z:20s} {_kg(v)}")
    print(f"{'TOTAL':20s} {_kg(sum(zonas.values()))}")
    print("No alcanza:", alertas() or "nada")
