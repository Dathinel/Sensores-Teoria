"""La conversacion (tabla `asistente`: la ven el dashboard y el visor 3D) y quien esta pensando."""

from __future__ import annotations

import json
import sqlite3


def guardar_mensaje(conexion: sqlite3.Connection, rol: str, texto: str, *, modo: str = "",
                    acciones: list | None = None) -> None:
    from app import db

    conexion.execute("INSERT INTO asistente (ts, rol, texto, modo, acciones) VALUES (?, ?, ?, ?, ?)",
                     (db.ahora(), rol, texto, modo, json.dumps(acciones or [], ensure_ascii=False)))
    conexion.commit()


def marcar_pensando(conexion: sqlite3.Connection, proveedor: str | None, pregunta: str = "") -> None:
    """Deja escrito quien esta pensando (el visor lo anima); None = nadie."""
    from app import db

    conexion.execute("INSERT OR REPLACE INTO asistente_pensando (id, proveedor, pregunta, desde) VALUES (1, ?, ?, ?)",
                     (proveedor, pregunta[:200], db.ahora()))
    conexion.commit()


def pensando(conexion: sqlite3.Connection) -> dict | None:
    f = conexion.execute("SELECT proveedor, pregunta, desde FROM asistente_pensando WHERE id = 1").fetchone()
    return dict(f) if f and f["proveedor"] else None


def conversacion(conexion: sqlite3.Connection, limite: int = 40) -> list[dict]:
    filas = conexion.execute("SELECT ts, rol, texto, modo, acciones FROM asistente ORDER BY id DESC LIMIT ?",
                             (limite,)).fetchall()
    return [dict(f, acciones=json.loads(f["acciones"] or "[]")) for f in reversed(filas)]


def borrar_conversacion(conexion: sqlite3.Connection) -> None:
    conexion.execute("DELETE FROM asistente")
    conexion.commit()
