"""Esquema y acceso a SQLite (CLAUDE.md, seccion 10.3).

Este modulo solo abre la conexion y crea el esquema si falta. El proceso
supervisor es el unico que escribe eventos aqui; el dashboard de Streamlit
solo lee y escribe comandos en `ordenes` (seccion 8: mezclar la camara y el
puerto serial dentro de Streamlit lo vuelve inestable, por eso la
separacion de procesos no es negociable).
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    origen TEXT NOT NULL,
    tipo TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS elementos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    casilla INTEGER NOT NULL,
    veredicto TEXT NOT NULL,
    causa TEXT,
    denominacion INTEGER,
    valor INTEGER,
    masa_estimada_g REAL,
    imagen_ruta TEXT,
    ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vasos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estado TEXT NOT NULL,
    denominacion INTEGER,
    cantidad_monedas INTEGER NOT NULL DEFAULT 0,
    valor_total INTEGER NOT NULL DEFAULT 0,
    masa_estimada_g REAL NOT NULL DEFAULT 0,
    ts_llenado TEXT,
    ts_tapado TEXT,
    ts_entrega TEXT
);

CREATE TABLE IF NOT EXISTS ruta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    posicion_x REAL,
    posicion_y REAL,
    evento_obstaculo TEXT,
    estado_vehiculo TEXT
);

-- Lo que quedo en los tubos al terminar un turno (una sola fila, id=1).
-- NO es tabla de corrida: sobrevive a reiniciar_corrida para que el turno
-- siguiente arranque con esas monedas (planta.conservar_almacen_entre_turnos).
CREATE TABLE IF NOT EXISTS almacen_turno (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    ts TEXT NOT NULL,
    monedas TEXT NOT NULL
);

-- Conversacion con el asistente (fase 7). La escribe el dashboard y la
-- leen el dashboard y el visor 3D. No es tabla de corrida: sobrevive a
-- reiniciar_corrida (se borra con el boton "Borrar conversacion").
CREATE TABLE IF NOT EXISTS asistente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    rol TEXT NOT NULL,
    texto TEXT NOT NULL,
    modo TEXT,
    acciones TEXT
);

CREATE TABLE IF NOT EXISTS ordenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    comando TEXT NOT NULL,
    consumida INTEGER NOT NULL DEFAULT 0
);
"""


def _migrar(conexion: sqlite3.Connection) -> None:
    """Columnas agregadas despues de crear la base (CREATE TABLE IF NOT
    EXISTS no toca una tabla que ya existe). `vasos.denominacion`: cada vaso
    lleva una sola denominacion (regla del grupo)."""
    columnas = {f[1] for f in conexion.execute("PRAGMA table_info(vasos)")}
    if "denominacion" not in columnas:
        conexion.execute("ALTER TABLE vasos ADD COLUMN denominacion INTEGER")
        conexion.commit()


def conectar(ruta_bd: str | Path) -> sqlite3.Connection:
    """Abre (o crea) la base de datos y asegura que el esquema exista."""
    conexion = sqlite3.connect(ruta_bd)
    conexion.row_factory = sqlite3.Row
    conexion.executescript(ESQUEMA)
    _migrar(conexion)
    return conexion


def nombres_de_tablas(conexion: sqlite3.Connection) -> set[str]:
    filas = conexion.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {fila["name"] for fila in filas}


# ---------------------------------------------------------------------
# Escritura (solo la usa el supervisor) y lectura (dashboard). La
# telemetria periodica -- el mensaje `t: tel` de la seccion 10.1 -- va a
# la tabla `eventos` con tipo 'tel' y el estado completo de la planta en el
# payload; el dashboard lee siempre la ultima. No hace falta una tabla
# propia para eso.
# ---------------------------------------------------------------------

TABLAS_DE_CORRIDA = ("eventos", "elementos", "vasos", "ruta")


def ahora() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def conectar_lectura(ruta_bd: str | Path) -> sqlite3.Connection:
    """Conexion para el dashboard. `check_same_thread=False` porque
    Streamlit puede reusar la conexion desde hilos distintos entre
    reejecuciones; solo se lee y se inserta en `ordenes`, que SQLite
    serializa por su cuenta."""
    Path(ruta_bd).parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta_bd, check_same_thread=False, timeout=5)
    conexion.row_factory = sqlite3.Row
    conexion.executescript(ESQUEMA)
    return conexion


def activar_wal(conexion: sqlite3.Connection) -> None:
    """Modo WAL: el dashboard puede leer mientras el supervisor escribe sin
    que ninguno de los dos se bloquee con 'database is locked'."""
    conexion.execute("PRAGMA journal_mode=WAL")


def reiniciar_corrida(conexion: sqlite3.Connection) -> None:
    """Borra lo de la corrida anterior (no las ordenes: puede haber una
    pendiente que llego junto con el 'iniciar')."""
    for tabla in TABLAS_DE_CORRIDA:
        conexion.execute(f"DELETE FROM {tabla}")
    conexion.commit()


def guardar_almacen_turno(conexion: sqlite3.Connection, monedas: list[dict]) -> None:
    conexion.execute(
        "INSERT OR REPLACE INTO almacen_turno (id, ts, monedas) VALUES (1, ?, ?)",
        (ahora(), json.dumps(monedas, ensure_ascii=False)),
    )


def leer_almacen_turno(conexion: sqlite3.Connection) -> list[dict]:
    fila = conexion.execute("SELECT monedas FROM almacen_turno WHERE id = 1").fetchone()
    return json.loads(fila["monedas"]) if fila else []


def registrar_evento(conexion: sqlite3.Connection, origen: str, tipo: str, payload: dict) -> None:
    conexion.execute(
        "INSERT INTO eventos (ts, origen, tipo, payload) VALUES (?, ?, ?, ?)",
        (ahora(), origen, tipo, json.dumps(payload, ensure_ascii=False)),
    )


def registrar_ruta(conexion: sqlite3.Connection, x: float, y: float, evento_obstaculo: str | None,
                   estado_vehiculo: str) -> None:
    """Un punto del recorrido del carro (tabla `ruta`, seccion 10.3)."""
    conexion.execute(
        "INSERT INTO ruta (ts, posicion_x, posicion_y, evento_obstaculo, estado_vehiculo) VALUES (?, ?, ?, ?, ?)",
        (ahora(), x, y, evento_obstaculo, estado_vehiculo),
    )


def registrar_elemento(conexion: sqlite3.Connection, evento: dict) -> None:
    """Un evento `elemento_final` de sim/planta.py (o del backend real)."""
    conexion.execute(
        """INSERT INTO elementos (casilla, veredicto, causa, denominacion, valor,
                                  masa_estimada_g, imagen_ruta, ts)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            evento["casilla"],
            evento["veredicto"],
            evento.get("causa"),
            evento.get("denominacion"),
            evento.get("valor"),
            evento.get("masa_g"),
            None,  # la imagen capturada llega con la vision real (fase 5)
            ahora(),
        ),
    )


def guardar_vaso(conexion: sqlite3.Connection, id_vaso: int, **campos) -> None:
    """Inserta el vaso si no existe y actualiza los campos dados."""
    conexion.execute("INSERT OR IGNORE INTO vasos (id, estado) VALUES (?, 'vacia')", (id_vaso,))
    if campos:
        asignaciones = ", ".join(f"{k} = ?" for k in campos)
        conexion.execute(f"UPDATE vasos SET {asignaciones} WHERE id = ?", (*campos.values(), id_vaso))


def insertar_orden(conexion: sqlite3.Connection, comando: dict) -> None:
    conexion.execute(
        "INSERT INTO ordenes (ts, comando) VALUES (?, ?)", (ahora(), json.dumps(comando, ensure_ascii=False))
    )
    conexion.commit()


def tomar_ordenes_pendientes(conexion: sqlite3.Connection) -> list[dict]:
    """Devuelve las ordenes no consumidas, en orden de llegada, y las marca
    como consumidas."""
    filas = conexion.execute("SELECT id, comando FROM ordenes WHERE consumida = 0 ORDER BY id").fetchall()
    if filas:
        conexion.executemany("UPDATE ordenes SET consumida = 1 WHERE id = ?", [(f["id"],) for f in filas])
        conexion.commit()
    return [json.loads(f["comando"]) for f in filas]


def ultima_telemetria(conexion: sqlite3.Connection) -> dict | None:
    fila = conexion.execute(
        "SELECT ts, payload FROM eventos WHERE tipo = 'tel' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if fila is None:
        return None
    datos = json.loads(fila["payload"])
    datos["ts"] = fila["ts"]
    return datos
