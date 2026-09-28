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

from .textos import NOMBRE_CAUSA, NOMBRE_TIPO_REAL, frase_evento

RAIZ = Path(__file__).resolve().parents[2]


def parametros() -> dict:
    """config/parametros.yaml (se lee en cada ejecución: si cambia, se nota al recargar)."""
    return configuracion.cargar_parametros()


PARAMETROS = parametros()
REFRESCO_S = PARAMETROS["dashboard"]["refresco_s"]


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
    return {"elementos": elementos, "vasos": vasos,
            "aceptadas": elementos[elementos["veredicto"] == "aceptada"],
            "rechazadas": elementos[elementos["veredicto"] == "rechazada"]}


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


def matriz_aciertos() -> pd.DataFrame:
    """Qué era cada pieza (lo sabe la simulación) contra qué decidió la línea."""
    filas = conexion().execute(
        "SELECT tipo, payload FROM eventos WHERE tipo IN ('presencia', 'elemento_final') ORDER BY id").fetchall()
    real, decision = {}, {}
    for f in filas:
        p = json.loads(f["payload"])
        if f["tipo"] == "presencia" and p.get("tipo_real"):
            real[p["casilla"]] = (p.get("apariencia") or p["tipo_real"], p.get("clase_real"))
        elif f["tipo"] == "elemento_final":
            decision[p["casilla"]] = ("Aceptada" if p["veredicto"] == "aceptada"
                                      else NOMBRE_CAUSA.get(p.get("causa"), "No reconocida"))
    datos = []
    for casilla, dec in decision.items():
        tipo, clase = real.get(casilla, ("?", None))
        if tipo == "moneda":
            cat = "Moneda colombiana" if clase and tabla_monedas.reconocible(clase) else "Moneda que debe rechazarse"
        else:
            cat = NOMBRE_TIPO_REAL.get(tipo, tipo).capitalize()
        datos.append({"real": cat, "decision": dec})
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
