"""El estado en vivo de la corrida, sacado de SQLite. Solo cifras que estan en la base."""

from __future__ import annotations

import json
import math
import sqlite3

# Para completar "El carro está ...": el tablero (app/dashboard/textos.py, ESTADO_CARRO) dice lo
# mismo con otra redacción a propósito ("sigue la línea"), por eso no se comparte.
ESTADO_CARRO = {"siguiendo":"siguiendo la línea", "maniobra": "maniobrando", "en_meta": "en la meta",
                "esperando_carga": "en el muelle", "detenido": "detenido", "manual": "cumpliendo una orden",
                "esperando_orden": "quieto, esperando otra orden"}


def viajes_del_carro(conexion: sqlite3.Connection) -> dict:
    """Cuanto se demora el carro: la MISMA cuenta que la pestana Carro del dashboard
    (app/dashboard/datos.py, viajes_del_carro), sin pandas. Un viaje empieza con `carga` (sale del
    muelle con el vaso), la ida termina en `meta` y el viaje completo en el `en_muelle` siguiente.
    Antes el asistente no tenia este dato y contestaba "¿qué tanto se demora el carro?" con
    vaguedades aunque el dashboard mostraba ~154 s por viaje."""
    from datetime import datetime

    viajes, actual = [], None
    for f in conexion.execute("SELECT ts, tipo FROM eventos WHERE origen = 'carro' AND tipo IN "
                              "('carga', 'meta', 'en_muelle') ORDER BY id").fetchall():
        t = datetime.fromisoformat(f["ts"])
        if f["tipo"] == "carga":
            actual = {"sale": t, "meta": None, "vuelve": None}
            viajes.append(actual)
        elif actual is not None:
            if f["tipo"] == "meta" and actual["meta"] is None:
                actual["meta"] = t
            elif f["tipo"] == "en_muelle" and actual["meta"] is not None and actual["vuelve"] is None:
                actual["vuelve"] = t
    idas = [(v["meta"] - v["sale"]).total_seconds() for v in viajes if v["meta"]]
    completos = [(v["vuelve"] - v["sale"]).total_seconds() for v in viajes if v["vuelve"]]
    return {
        "viajes_empezados": len(viajes),
        "viajes_completos": len(completos),
        "ultimo_viaje_completo_s": round(completos[-1]) if completos else None,
        "promedio_viaje_completo_s": round(sum(completos) / len(completos)) if completos else None,
        "ultima_ida_a_la_meta_s": round(idas[-1]) if idas else None,
        "promedio_ida_a_la_meta_s": round(sum(idas) / len(idas)) if idas else None,
    }


def estado_en_vivo(conexion: sqlite3.Connection) -> dict:
    """Lo que el asistente sabe de la corrida en curso. Solo cifras que
    estan en la base: si algo no esta, no aparece (y el asistente dice que
    no tiene ese dato)."""
    fila = conexion.execute("SELECT ts, payload FROM eventos WHERE tipo = 'tel' ORDER BY id DESC LIMIT 1").fetchone()
    tel = json.loads(fila["payload"]) if fila else {}
    acept = conexion.execute(
        "SELECT denominacion, COUNT(*) AS n, COALESCE(SUM(valor),0) AS v, COALESCE(SUM(masa_estimada_g),0) AS g "
        "FROM elementos WHERE veredicto = 'aceptada' GROUP BY denominacion").fetchall()
    rech = conexion.execute(
        "SELECT causa, COUNT(*) AS n FROM elementos WHERE veredicto = 'rechazada' GROUP BY causa").fetchall()
    vasos = conexion.execute("SELECT estado, COUNT(*) AS n, COALESCE(SUM(valor_total),0) AS v FROM vasos "
                             "GROUP BY estado").fetchall()
    entregados = conexion.execute(
        "SELECT COUNT(*) FROM eventos WHERE origen = 'carro' AND tipo = 'entregado'").fetchone()[0]
    evasiones = conexion.execute("SELECT COUNT(*) FROM ruta WHERE evento_obstaculo = 'evasion'").fetchone()[0]
    puntos = conexion.execute("SELECT posicion_x, posicion_y FROM ruta WHERE evento_obstaculo IS NULL "
                              "ORDER BY id").fetchall()
    distancia = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(puntos, puntos[1:]))
    recientes = conexion.execute(
        "SELECT ts, origen, tipo, payload FROM eventos WHERE tipo NOT IN ('tel', 'paso', 'orden', 'espera') "
        "ORDER BY id DESC LIMIT 25").fetchall()

    # Lo ultimo que vio la camara (E3) y los ultimos rechazos: con esto el asistente puede
    # contestar "que fue lo ultimo que reviso la camara" o "por que rechazo la ultima pieza".
    vision = conexion.execute("SELECT ts, payload FROM eventos WHERE origen = 'e3' AND tipo = 'vision' "
                              "ORDER BY id DESC LIMIT 1").fetchone()
    ultima_vision = None
    if vision:
        v = json.loads(vision["payload"])
        ultima_vision = {k: v.get(k) for k in ("casilla", "diametro_mm", "circularidad", "contornos_internos",
                                               "clase", "confianza", "combinacion", "veredicto", "causa")}
        ultima_vision["hora"] = vision["ts"][11:19]
    ultimos_rechazos = [{"casilla": f["casilla"], "causa": f["causa"], "hora": (f["ts"] or "")[11:19]}
                        for f in conexion.execute("SELECT casilla, causa, ts FROM elementos WHERE veredicto = "
                                                  "'rechazada' ORDER BY id DESC LIMIT 5").fetchall()]
    eventos_carro = [f"{r['ts'][11:19]} {r['tipo']}" for r in conexion.execute(
        "SELECT ts, tipo FROM eventos WHERE origen = 'carro' AND tipo NOT IN ('estado', 'tel') "
        "ORDER BY id DESC LIMIT 6").fetchall()]

    por_denominacion = {str(f["denominacion"]): {"monedas": f["n"], "valor_pesos": f["v"],
                                                 "peso_estimado_g": round(f["g"], 1)} for f in acept}
    carro = tel.get("carro")
    if carro:
        carro = {k: carro.get(k) for k in ("estado", "fase", "x", "y", "rumbo", "odometria", "vaso_id",
                                           "inclinacion_vaso_grados", "ultima_orden", "radio")}
        carro["que_hace"] = ESTADO_CARRO.get(carro["estado"], carro["estado"])
        carro["ultimos_eventos"] = eventos_carro
    # ORDEN de las claves = orden en que el modelo las lee (el JSON va tal cual): primero lo de
    # las monedas (elemento 7, la especialidad del grupo), despues el carro y al final lo demas.
    return {
        "hay_datos": bool(fila),
        "hora_ultimo_dato": fila["ts"] if fila else None,
        # --- monedas: filtrado, rechazos y almacen
        "totales": {
            "monedas_aceptadas": sum(f["n"] for f in acept),
            "valor_aceptado_pesos": sum(f["v"] for f in acept),
            "peso_estimado_g": round(sum(f["g"] for f in acept), 1),
            "nota_peso": "estimado por conteo (masa nominal de cada moneda reconocida); no hay balanza",
            "piezas_rechazadas": sum(f["n"] for f in rech),
            "vasos_entregados_en_meta": entregados,
        },
        "aceptadas_por_denominacion": por_denominacion,
        "rechazos_por_causa": {f["causa"]: f["n"] for f in rech},
        "ultimos_rechazos": ultimos_rechazos,
        "ultima_inspeccion_camara": ultima_vision,
        "confianza_minima": tel.get("confianza_minima"),
        "errores_del_filtro": tel.get("errores_filtrado"),
        "almacen_tubos": tel.get("almacen"),
        "almacen_valor_pesos": tel.get("almacen_valor"),
        "monedas_por_vaso": tel.get("monedas_por_vaso"),
        # --- carro y ruta
        "carro": carro,
        "ruta": {"distancia_recorrida_m": round(distancia, 2), "evasiones": evasiones,
                 "tiempos_de_viaje": viajes_del_carro(conexion)},
        # --- lo demas: linea, vasos, seguridad
        "estado_linea": tel.get("linea"),
        "ciclo": tel.get("tick"),
        "velocidad_simulacion": tel.get("velocidad"),
        "piezas_por_cargar": tel.get("pendientes"),
        "vasos_por_estado": {f["estado"]: {"vasos": f["n"], "valor_pesos": f["v"]} for f in vasos},
        # Los vacios desechados quedan "rechazada" en la tabla vasos: aqui se cuentan aparte.
        "vasos_vacios_desechados": conexion.execute(
            "SELECT COUNT(*) FROM eventos WHERE tipo = 'descarga' "
            "AND json_extract(payload, '$.destino') = 'vacio'").fetchone()[0],
        "canaleta_vasos_esperando": len(tel.get("canaleta") or []),
        "tapas_restantes": tel.get("tapas_restantes"),
        "cortina_activa": tel.get("cortina_activa"),
        "alarmas": tel.get("alarmas"),
        "ultima_orden": tel.get("ultima_orden"),
        "ultimos_eventos": [f"{r['ts'][11:19]} {r['origen']}.{r['tipo']} {r['payload'][:160]}" for r in recientes],
    }
