"""Todo lo que el dashboard lee (SQLite, el servidor del supervisor, la
configuración) y la única forma de escribir: `enviar()` deja una orden en la
tabla `ordenes` (CLAUDE.md §8: este proceso NO corre la línea).

Las pestañas no escriben SQL: piden aquí lo que necesitan.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from app import configuracion, db
from control import monedas as tabla_monedas

from .textos import NOMBRE_CAUSA, NOMBRE_TIPO_REAL, TUBOS, frase_evento

RAIZ = Path(__file__).resolve().parents[2]


def parametros() -> dict:
    """config/parametros.yaml (se lee en cada ejecución: si cambia, se nota al recargar)."""
    return configuracion.cargar_parametros()


PARAMETROS = parametros()
REFRESCO_S = PARAMETROS["dashboard"]["refresco_s"]
# Tolerancia de la regla "clase y diámetro que no cuadran" (control/reglas.py), de la configuración.
TOLERANCIA_COHERENCIA_MM = float(PARAMETROS["filtrado"]["tolerancia_coherencia_mm"])


def url_supervisor() -> str:
    return f"http://127.0.0.1:{PARAMETROS['supervisor']['puerto_http']}"


# ---------------------------------------------------------------------------
# base de datos
# ---------------------------------------------------------------------------


@st.cache_resource
def _conexion(ruta: str):
    return db.conectar_lectura(ruta)


def conexion():
    # Una conexión por base: si cambia la ruta (PLANTA_BD en las pruebas), no se reusa la anterior.
    return _conexion(str(configuracion.ruta_bd(PARAMETROS)))


def consulta(sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, conexion(), params=params)


def telemetria() -> dict | None:
    """El último estado completo de la planta (evento `tel`, CLAUDE.md §10.4)."""
    return db.ultima_telemetria(conexion())


def enviar(comando: dict, aviso: str) -> None:
    """Deja una orden para el supervisor (la toma en menos de medio segundo)."""
    db.insertar_orden(conexion(), comando)
    st.toast(aviso)


# ---------------------------------------------------------------------------
# el supervisor: ¿está vivo?, geometría de la pista
# ---------------------------------------------------------------------------


def simulacion_viva() -> bool:
    """True si el supervisor (simulación o puente al ESP32) está corriendo en este PC.
    Se le pregunta a su servidor local: con la corrida terminada deja de escribir
    telemetría, así que la edad del último dato no alcanza para saberlo."""
    import urllib.request

    try:
        with urllib.request.urlopen(f"{url_supervisor()}/api/estado", timeout=0.6) as r:
            return r.status == 200
    except OSError:
        return False


@st.cache_data(ttl=30, show_spinner=False)
def geometria_pista() -> dict | None:
    """La pista (línea, muros, meta, muelle) la da el supervisor por HTTP (el
    dashboard no importa PyBullet); si no está corriendo, la de la demo grabada."""
    import urllib.request

    try:
        with urllib.request.urlopen(f"{url_supervisor()}/api/geometria", timeout=1.5) as r:
            return json.loads(r.read())["pista"]
    except (OSError, ValueError, KeyError):
        demo = RAIZ / "app" / "visor3d" / "demo" / "geometria.json"
        return json.loads(demo.read_text(encoding="utf-8"))["pista"] if demo.exists() else None


# ---------------------------------------------------------------------------
# formato
# ---------------------------------------------------------------------------


def pesos(valor) -> str:
    return f"${int(valor or 0):,}".replace(",", ".")


def nombre_denominacion(d) -> str:
    """'$500', o 'otras denominaciones' para el vaso de las que ya no circulan."""
    return "otras denominaciones" if d == "otras" else pesos(d)


# ---------------------------------------------------------------------------
# consultas de cada pestaña
# ---------------------------------------------------------------------------


def datos_corrida() -> dict:
    elementos = consulta("SELECT * FROM elementos ORDER BY id")
    vasos = consulta("SELECT * FROM vasos")
    if len(vasos):
        # Un vaso vacío desechado queda RECHAZADO en la tabla `vasos` (control/embalaje.py); lo que
        # lo distingue de un rechazo por sabotaje es el destino "vacio" de su evento `descarga`.
        vacios = {f[0] for f in conexion().execute(
            "SELECT json_extract(payload, '$.vaso') FROM eventos WHERE tipo = 'descarga' "
            "AND json_extract(payload, '$.destino') = 'vacio'").fetchall()}
        vasos["vacio_desechado"] = vasos["id"].isin(vacios)
    return {"elementos": elementos, "vasos": vasos,
            "aceptadas": elementos[elementos["veredicto"] == "aceptada"],
            "rechazadas": elementos[elementos["veredicto"] == "rechazada"]}


def _tubo(denominacion) -> str:
    """El tubo del almacén de una denominación: "500", o "otras" para las que no tienen tubo propio."""
    if isinstance(denominacion, float) and denominacion == denominacion:
        denominacion = int(denominacion)
    t = str(denominacion)
    return t if t in TUBOS[:-1] else "otras"


def monedas_del_turno_anterior(d: dict, tel: dict) -> dict:
    """Lo que la corrida encontró guardado en los tubos al arrancar (del turno anterior, que no se
    empacó), por tubo: {"500": 3, "otras": 1}. Vacío si arrancó con los tubos vacíos.

    La ÚNICA fuente es el evento `almacen_precargado` que la planta emite al arrancar si encontró
    monedas guardadas (sim/planta.py; va con `eventos_arranque`, que el supervisor guarda justo al
    iniciar, y `eventos` se borra en cada corrida nueva, así que el que está es de esta corrida). Si
    no está, la corrida arrancó con los tubos vacíos: 0, sin deducir nada.

    Antes, sin el evento, se DEDUCÍA por conservación (vasos + tubos + camino al tubo − aceptadas), y
    eso inventaba monedas "del turno anterior" en corridas que arrancaron vacías (revisión lógica
    2026-09-29, 49 ticks de `prueba_completa`): `d["aceptadas"]` (tabla `elementos`) solo trae las
    FINALIZADAS, mientras que una aceptada que va de la cámara a la descarga, o espera en E4 a que
    gire el carrusel, ya contaba del otro lado. `d` y `tel` se dejan en la firma por compatibilidad."""
    fila = conexion().execute(
        "SELECT payload FROM eventos WHERE tipo = 'almacen_precargado' ORDER BY id DESC LIMIT 1").fetchone()
    if fila is None:
        return {}
    p = json.loads(fila["payload"])
    tubos = {str(k): int(v) for k, v in (p.get("contenido") or {}).items() if int(v)}
    if p.get("otras"):
        tubos["otras"] = int(p["otras"])
    return tubos


def cuentas_de_monedas(d: dict, tel: dict) -> dict:
    """Las cifras de monedas que se muestran en Resumen y en Monedas y vasos, todas del mismo lado
    y separadas por su ORIGEN, para que cuadren entre pestañas (antes el diagrama recortaba "En
    vasos" a las aceptadas de esta corrida y no cuadraba con la tabla de vasos):

    - `aceptadas`/`valor_aceptado`: monedas que pasaron por la cinta y los filtros EN ESTA CORRIDA;
    - `anteriores`/`valor_anteriores`: las que ya estaban en los tubos al arrancar (turno anterior);
    - `en_vasos`: todas las monedas que cayeron a un vaso en esta corrida (tabla `vasos`), y de
      ellas cuántas eran del turno anterior (`en_vasos_anteriores`). Los tubos sueltan primero las
      más antiguas (control/almacen.py, `sacar`), así que en cada tubo las del turno anterior son
      las primeras en salir;
    - `entregadas`: monedas de los vasos que el carro entregó;
    - `en_tubos`/`valor_en_tubos`: lo que hay AHORA en los tubos (de los dos orígenes).
    Conservación: aceptadas + anteriores = en_vasos + en_tubos (+ la moneda que va camino al tubo).
    """
    aceptadas, vasos = d["aceptadas"], d["vasos"]
    anteriores = monedas_del_turno_anterior(d, tel)
    valor_anteriores = sum(int(t) * n for t, n in anteriores.items() if t != "otras")
    llenos = vasos[vasos["cantidad_monedas"] > 0] if len(vasos) else vasos
    salieron: dict[str, int] = {}
    if len(llenos):
        for den, n_vaso in zip(llenos["denominacion"], llenos["cantidad_monedas"]):
            salieron[_tubo(den)] = salieron.get(_tubo(den), 0) + int(n_vaso)
    en_vasos_anteriores = sum(min(n, salieron.get(tubo, 0)) for tubo, n in anteriores.items())
    entregados = vasos[vasos["estado"] == "entregada"] if len(vasos) else vasos
    almacen = tel.get("almacen") or {}
    return {
        "aceptadas": len(aceptadas), "valor_aceptado": int(aceptadas["valor"].sum()) if len(aceptadas) else 0,
        "anteriores": sum(anteriores.values()), "valor_anteriores": valor_anteriores,
        "otras_anteriores": anteriores.get("otras", 0),
        "en_vasos": int(llenos["cantidad_monedas"].sum()) if len(llenos) else 0,
        "valor_en_vasos": int(llenos["valor_total"].sum()) if len(llenos) else 0,
        "en_vasos_anteriores": en_vasos_anteriores,
        "entregadas": int(entregados["cantidad_monedas"].sum()) if len(entregados) else 0,
        "valor_entregado": int(entregados["valor_total"].sum()) if len(entregados) else 0,
        "en_tubos": sum(int(v) for v in almacen.values()), "valor_en_tubos": int(tel.get("almacen_valor") or 0),
    }


def explicar_cuentas(c: dict) -> str:
    """Una o dos frases que explican por qué las cifras no son iguales entre sí (HTML corto)."""
    partes = []
    if c["anteriores"]:
        partes.append(
            f'La corrida arrancó con <b>{c["anteriores"]} monedas ({pesos(c["valor_anteriores"])})</b> guardadas en '
            "los tubos del turno anterior"
            + (f' (y {c["otras_anteriores"]} de otras denominaciones)' if c["otras_anteriores"] else "") + ". "
            f'De las <b>{c["en_vasos"]}</b> monedas que cayeron a los vasos, <b>{c["en_vasos"] - c["en_vasos_anteriores"]}</b> '
            f'son de esta corrida y <b>{c["en_vasos_anteriores"]}</b> venían del turno anterior.')
    else:
        partes.append("La corrida arrancó con los tubos vacíos: todas las monedas de los vasos pasaron por la cinta "
                      "en esta corrida.")
    partes.append(
        f'«Valor aceptado» ({pesos(c["valor_aceptado"])}) cuenta solo lo que pasó por los filtros en esta corrida; '
        f'«guardado» ({pesos(c["valor_en_tubos"])}) es lo que hay ahora en los tubos, esperando a juntar un lote'
        + (", incluidas las del turno anterior que todavía no salieron" if c["anteriores"] else "") + ".")
    # "$" como entidad HTML: dos "$" en el mismo texto de st.markdown pueden leerse como fórmula (LaTeX).
    return " ".join(partes).replace("$", "&#36;")


def eventos_recientes(limite: int = 16) -> list[dict]:
    filas = conexion().execute(
        "SELECT ts, origen, tipo, payload FROM eventos WHERE tipo NOT IN ('tel', 'paso') "
        "ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return [dict(f) for f in filas]


def frases_recientes(limite: int = 10) -> list[tuple[str, str, str, str]]:
    """Los últimos eventos que tienen frase simple: (hora, tono, ícono, texto)."""
    filas = conexion().execute(
        "SELECT ts, origen, tipo, payload FROM eventos WHERE tipo NOT IN ('tel', 'paso', 'orden') "
        "ORDER BY id DESC LIMIT 300").fetchall()
    out = []
    for f in filas:
        r = frase_evento(dict(f))
        if r:
            out.append((f["ts"][11:19], *r))
        if len(out) >= limite:
            break
    return out


def frases_de_ordenes(limite: int = 8) -> list[tuple[str, str, str, str]]:
    """Qué pasó con las órdenes del asistente (respuesta del supervisor y lo que hizo el carro)."""
    filas = conexion().execute(
        "SELECT ts, origen, tipo, payload FROM eventos WHERE (tipo = 'respuesta' AND payload LIKE '%\"asistente\"%') "
        "OR (origen = 'carro' AND tipo IN ('orden_cumplida', 'camino_bloqueado', 'bloqueado', 'atascado', "
        "'llego_al_punto', 'punto_con_error', 'ruta_retomada', 'detenido_por_orden', 'meta', 'en_muelle')) "
        "ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    out = []
    for f in filas:
        r = frase_evento(dict(f))
        if r:
            out.append((f["ts"][11:19], *r))
    return out


def piezas_decididas() -> pd.DataFrame:
    return consulta("SELECT causa FROM elementos WHERE veredicto != 'vacia'")


def rechazos_por_causa() -> pd.DataFrame:
    return consulta("SELECT causa, COUNT(*) AS n FROM elementos WHERE veredicto = 'rechazada' GROUP BY causa")


def ultimas_mediciones(limite: int = 15) -> list[dict]:
    filas = conexion().execute("SELECT payload FROM eventos WHERE tipo = 'vision' ORDER BY id DESC LIMIT ?",
                               (limite,)).fetchall()
    return [json.loads(f["payload"]) for f in filas]


def categoria_real(tipo: str | None, apariencia: str | None, clase: str | None,
                   diametro_medido: float | None = None, diametro_real: float | None = None) -> str:
    """La fila de la matriz de Calidad para una pieza: se agrupa por lo que la pieza ES
    (su `tipo_real` en la simulación), no por cómo se dibuja (`apariencia`). Antes se usaba la
    apariencia primero y salían filas como "Disco metálico" o "Moneda extranjera" que la tabla no
    tenía, y esas piezas se perdían (la matriz sumaba 32 de 35).

    Dos excepciones, porque para quien lee la tabla importa si la pieza es una moneda:
    - una moneda extranjera (en la simulación es un botón metálico que se dibuja como moneda) va a
      "Moneda que debe rechazarse": es una moneda, pero no colombiana;
    - una "moneda" colombiana cuyo diámetro real no le corresponde (la pieza de prueba "cara de $500
      con otro diámetro") también debe rechazarse. La planta publica el diámetro REAL del cuerpo en
      el evento `presencia` (`diametro_real_mm`, verdad de terreno): con ese se compara contra la
      tolerancia de la regla de coherencia (revisión 2026-09-29; antes se usaba el de la cámara, que
      es justo lo que se está evaluando). Solo si no viene (bases viejas) se usa el que midió la
      cámara, y entonces cuenta como falsa si se aleja más del DOBLE de la tolerancia (una moneda
      buena con el ruido normal de la medida nunca llega ahí)."""
    if tipo == "moneda":
        if not (clase and tabla_monedas.reconocible(clase)):
            return "Moneda que debe rechazarse"
        nominal = tabla_monedas.diametro_nominal_mm(clase)
        if nominal and diametro_real:
            if abs(nominal - diametro_real) > TOLERANCIA_COHERENCIA_MM:
                return "Moneda que debe rechazarse"
        elif nominal and diametro_medido and abs(nominal - diametro_medido) > 2 * TOLERANCIA_COHERENCIA_MM:
            return "Moneda que debe rechazarse"
        return "Moneda colombiana"
    if apariencia == "moneda_extranjera":
        return "Moneda que debe rechazarse"
    if tipo is None:
        return "Pieza sin identificar"
    return NOMBRE_TIPO_REAL.get(tipo, tipo.replace("_", " ")).capitalize()


def matriz_aciertos() -> pd.DataFrame:
    """Qué era cada pieza (lo sabe la simulación) contra qué decidió la línea: UNA fila por
    pieza decidida (el total cuadra con "Piezas procesadas" y con la tabla `elementos`).

    Se empareja por el orden de los eventos: `presencia` dice qué entró a la casilla y el
    `elemento_final` siguiente de esa casilla dice qué se decidió; si un número de casilla se
    reusara, cada decisión toma la última pieza que entró ahí (no se pisa una ya decidida).

    Una pieza que el infrarrojo de E1 NO vio (`presencia` con `ocupada: false`) y que después
    recuperó E2 (`presencia_recuperada`) sí se decide: su verdad de terreno viene en ese primer
    evento `presencia`, así que se guarda aparte y se usa al recuperarla (antes quedaba como "Pieza
    sin identificar" aunque el evento traía `tipo_real`)."""
    filas = conexion().execute(
        "SELECT tipo, payload FROM eventos WHERE tipo IN ('presencia', 'presencia_recuperada', 'vision', "
        "'elemento_final') ORDER BY id").fetchall()
    real: dict = {}
    no_vistas: dict = {}          # casilla -> verdad de terreno de una pieza que E1 no vio
    datos = []
    for f in filas:
        p = json.loads(f["payload"])
        casilla = p.get("casilla")
        if f["tipo"] == "presencia":
            verdad = {"tipo": p.get("tipo_real"), "apariencia": p.get("apariencia"),
                      "clase": p.get("clase_real"), "diametro": None, "diametro_real": p.get("diametro_real_mm")}
            if p.get("ocupada", True):
                real[casilla] = verdad
            else:
                no_vistas[casilla] = verdad
        elif f["tipo"] == "presencia_recuperada":
            if casilla not in real:
                real[casilla] = no_vistas.pop(casilla, {})
        elif f["tipo"] == "vision":
            if casilla in real:
                real[casilla]["diametro"] = p.get("diametro_mm")
        elif p.get("veredicto") in ("aceptada", "rechazada"):
            r = real.pop(casilla, {})
            datos.append({
                "real": categoria_real(r.get("tipo"), r.get("apariencia"), r.get("clase"),
                                       r.get("diametro") or p.get("diametro_mm"), r.get("diametro_real")),
                "decision": ("Aceptada" if p["veredicto"] == "aceptada"
                             else NOMBRE_CAUSA.get(p.get("causa"), "Rechazada (otra causa)")),
            })
    return pd.DataFrame(datos, columns=["real", "decision"])


def ruta_del_carro() -> pd.DataFrame:
    return consulta("SELECT posicion_x AS x, posicion_y AS y, evento_obstaculo AS ev, estado_vehiculo AS estado "
                    "FROM ruta ORDER BY id")


def vasos_entregados_por_el_carro() -> int:
    return int(consulta("SELECT COUNT(*) AS n FROM eventos WHERE origen = 'carro' AND tipo = 'entregado'")["n"][0])


def viajes_del_carro() -> pd.DataFrame:
    """Cada viaje del carro: cuándo salió, llegó a la meta, le sacaron el vaso y volvió."""
    filas = conexion().execute(
        "SELECT ts, tipo, payload FROM eventos WHERE origen = 'carro' AND tipo IN "
        "('carga', 'meta', 'vaso_retirado', 'en_muelle', 'entregado', 'vuelve_con_vaso') ORDER BY id").fetchall()
    viajes, actual = [], None
    for f in filas:
        t = datetime.fromisoformat(f["ts"])
        p = json.loads(f["payload"])
        if f["tipo"] == "carga":
            actual = {"Vaso": p.get("vaso"), "Sale": t, "Meta": None, "Entregado": "—", "Vuelve": None}
            viajes.append(actual)
        elif actual is not None:
            if f["tipo"] == "meta" and actual["Meta"] is None:
                actual["Meta"] = t
            elif f["tipo"] == "entregado":
                actual["Entregado"] = "sí"
            elif f["tipo"] == "vuelve_con_vaso":
                actual["Entregado"] = "no (volvió con él)"
            elif f["tipo"] == "en_muelle" and actual["Meta"] is not None and actual["Vuelve"] is None:
                actual["Vuelve"] = t
    return pd.DataFrame([{
        "Viaje": i + 1, "Vaso": v["Vaso"], "Sale": v["Sale"].strftime("%H:%M:%S"),
        "Ida (s)": f'{(v["Meta"] - v["Sale"]).total_seconds():.0f}' if v["Meta"] else "en camino",
        "¿Entregado?": v["Entregado"],
        "Viaje completo (s)": f'{(v["Vuelve"] - v["Sale"]).total_seconds():.0f}' if v["Vuelve"] else "—",
    } for i, v in enumerate(viajes)])
