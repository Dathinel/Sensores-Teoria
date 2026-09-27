"""Protocolo de comunicacion (punto 15): mensajes numerados y confirmados,
latido y reglas del enlace. Python puro: lo usa la simulacion hoy y es la
misma logica que va en el firmware (fase 8). Contrato en CLAUDE.md, 10.1.

Tres enlaces:

- PC <-> ESP32 fijo (USB serial): cada comando lleva `id` y espera su `ack`;
  sin ack en `pc_reintento_ms` se reenvia UNA vez y despues queda como fallo
  de comunicacion. Los eventos del ESP32 llevan `n` (numero de secuencia): un
  hueco en la numeracion es un mensaje perdido. Latido en los dos sentidos:
  si el ESP32 deja de oir al PC por `pc_sin_latido_ms`, se detiene seguro
  (cintas quietas, prensa arriba, desvio al rechazo); si el PC deja de oir al
  ESP32, pausa la linea y avisa.
- Carro <-> ESP32 fijo (ESP-NOW; el fijo lo reenvia al PC con `src:carro`):
  el carro numera sus eventos y los guarda hasta que le llega el ack; si el
  enlace se corta, los reenvia en orden cuando vuelve (el receptor descarta
  los repetidos). Si pierde el enlace, termina la vuelta y queda en el
  muelle; al volver, lo primero que manda es su `estado` (con la cuna). La
  estacion no suelta otro vaso hasta tener ese estado fresco con la cuna
  vacia.
"""

from __future__ import annotations

import json

# Este archivo corre IGUAL en el PC (CPython) y en los dos ESP32 (MicroPython,
# fase 8: firmware/preparar.py lo compila con mpy-cross). Por eso no usa
# dataclasses ni {**dict}: MicroPython no los tiene.


def parsear_linea(linea: str | bytes) -> dict | None:
    """Una linea del serial -> mensaje. Tolerante: una linea cortada, vacia o
    con basura devuelve None (se cuenta y se sigue; nunca se cae)."""
    if isinstance(linea, bytes):
        try:
            linea = linea.decode("utf-8")
        except UnicodeError:   # basura en el serial
            return None
    linea = linea.strip()
    if not linea.startswith("{") or not linea.endswith("}"):
        return None
    try:
        m = json.loads(linea)
    except ValueError:
        return None
    return m if isinstance(m, dict) and "t" in m else None


def linea(mensaje: dict) -> str:
    """Mensaje -> linea JSON compacta terminada en salto de linea."""
    return json.dumps(mensaje, separators=(",", ":"), ensure_ascii=False) + "\n"


class Emisor:
    """Numera los mensajes y los guarda hasta su ack. `reintentos` = None
    reintenta sin limite (el carro: no pierde eventos aunque el enlace se
    corte un rato); un numero = reintentos y despues fallo (el PC)."""

    def __init__(self, reintento_ms, reintentos=None, cola_max=32):
        self.reintento_ms = reintento_ms
        self.reintentos = reintentos
        self.cola_max = cola_max
        self._siguiente = 1
        self.pendientes = {}     # id -> [mensaje, t_envio, intentos]
        self.fallidos = []
        self.descartados = 0

    def enviar(self, mensaje: dict, t_ms: int) -> dict:
        m = dict(mensaje)
        m["id"] = self._siguiente
        self._siguiente += 1
        if len(self.pendientes) >= self.cola_max:
            # Cola llena: se descarta el mas viejo (y se cuenta).
            del self.pendientes[min(self.pendientes)]
            self.descartados += 1
        self.pendientes[m["id"]] = [m, t_ms, 1]
        return m

    def ack(self, id_: int) -> None:
        self.pendientes.pop(id_, None)

    def a_reenviar(self, t_ms: int) -> list[dict]:
        """Los que ya esperaron `reintento_ms` sin ack, en orden."""
        out = []
        for id_ in sorted(self.pendientes):
            m, t0, n = self.pendientes[id_]
            if t_ms - t0 < self.reintento_ms:
                continue
            if self.reintentos is not None and n > self.reintentos:
                self.fallidos.append(m)
                del self.pendientes[id_]
                continue
            self.pendientes[id_] = [m, t_ms, n + 1]
            out.append(m)
        return out


class Receptor:
    """Recibe mensajes numerados: contesta el ack de cada uno y descarta los
    repetidos (un reenvio cuyo ack se perdio no se ejecuta dos veces)."""

    def __init__(self):
        self.vistos = set()
        self.repetidos = 0

    def recibir(self, mensaje: dict) -> tuple[bool, dict]:
        id_ = mensaje["id"]
        ack = {"t": "ack", "id": id_, "ok": True}
        if id_ in self.vistos:
            self.repetidos += 1
            return False, ack
        self.vistos.add(id_)
        return True, ack


class Secuencia:
    """Eventos con numero de secuencia `n` (ESP32 fijo -> PC): detecta huecos."""

    def __init__(self, ultimo=0, perdidos=0):
        self.ultimo = ultimo
        self.perdidos = perdidos

    def recibir(self, n: int) -> int:
        """Devuelve cuantos se perdieron antes de este (0 si ninguno)."""
        hueco = max(0, n - self.ultimo - 1) if self.ultimo else 0
        self.perdidos += hueco
        self.ultimo = max(self.ultimo, n)
        return hueco


class Latido:
    """Estado de un enlace segun lo ultimo que se oyo del otro lado."""

    def __init__(self, periodo_ms, perdido_ms):
        self.periodo_ms = periodo_ms
        self.perdido_ms = perdido_ms
        self.ultimo_oido = None
        self.ultimo_enviado = None
        self._vivo = False

    def oido(self, t_ms: int) -> None:
        self.ultimo_oido = t_ms

    def debe_enviar(self, t_ms: int) -> bool:
        if self.ultimo_enviado is None or t_ms - self.ultimo_enviado >= self.periodo_ms:
            self.ultimo_enviado = t_ms
            return True
        return False

    def vivo(self, t_ms: int) -> bool:
        return self.ultimo_oido is not None and t_ms - self.ultimo_oido <= self.perdido_ms

    def cambio(self, t_ms: int) -> str | None:
        """'perdido' o 'recuperado' la primera vez que cambia; si no, None."""
        v = self.vivo(t_ms)
        if v == self._vivo:
            return None
        self._vivo = v
        return "recuperado" if v else "perdido"


def accion_sin_pc() -> dict:
    """Lo que hace el ESP32 fijo cuando deja de oir al PC: parada segura."""
    return {"cintas": "detenidas", "prensa": "arriba", "desvio": "rechazo", "escape_tapas": "cerrado",
            "empujador": "reposo", "escape_canaleta": "retener"}


def puede_soltar_vaso(estado_carro: dict | None, enlace_vivo: bool) -> tuple[bool, str]:
    """Regla de la estacion para soltar UN vaso al carro (punto 15, b): solo
    con el enlace vivo, un estado del carro FRESCO (recibido despues de la
    ultima reconexion), el carro en el muelle y su cuna vacia."""
    if not enlace_vivo:
        return False, "sin_enlace"
    if not estado_carro or not estado_carro.get("fresco"):
        return False, "estado_viejo"
    if not estado_carro.get("en_muelle"):
        return False, "no_esta_en_muelle"
    if estado_carro.get("cuna") is not False:
        return False, "cuna_ocupada" if estado_carro.get("cuna") else "cuna_desconocida"
    return True, "ok"
