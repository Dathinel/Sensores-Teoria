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


def nueva_sesion() -> int:
    """Numero de SESION de un emisor (1..65535), sorteado al arrancar.

    Por que: los `id` de los comandos (PC) y de los eventos del carro vuelven
    a 1 cada vez que ese lado se reinicia. Si el otro lado sigue encendido,
    recordaria esos ids como "ya vistos" y confirmaria los nuevos SIN
    ejecutarlos (probado: el PC reiniciado manda linea.avanzar id=1 -> ack ok,
    0 pasos). Con la sesion en cada mensaje (campo corto `"s"`), el receptor
    ve que el otro lado arranco de nuevo y olvida los ids viejos. Se sortea
    (no se cuenta) porque ninguna placa guarda nada entre reinicios."""
    try:
        import os
        b = os.urandom(2)                  # en el ESP32: generador de hardware
        v = (b[0] << 8) | b[1]
    except (ImportError, AttributeError, NotImplementedError):
        import time
        v = int(time.time() * 1000)
    return v % 65535 + 1


def linea(mensaje: dict) -> str:
    """Mensaje -> linea JSON compacta terminada en salto de linea."""
    try:
        return json.dumps(mensaje, separators=(",", ":"), ensure_ascii=False) + "\n"
    except TypeError:
        # MicroPython: su json.dumps no conoce `ensure_ascii` (y ya escribe los
        # acentos tal cual, en UTF-8, que es lo mismo que se pide aqui).
        return json.dumps(mensaje, separators=(",", ":")) + "\n"


# Un paquete de ESP-NOW lleva como mucho 250 bytes. Un mensaje mas largo no
# sale nunca por la radio: si quedara en la cola del carro, se reintentaria
# cada 500 ms para siempre ocupando uno de sus 32 lugares.
RADIO_MAX_BYTES = 250


def tamano(mensaje: dict) -> int:
    """Bytes que ocupa el mensaje como linea (lo que viaja)."""
    return len(linea(mensaje).encode())


def recortar(mensaje: dict, limite: int = RADIO_MAX_BYTES) -> dict | None:
    """El mensaje, con su texto `detalle` recortado si hace falta para caber
    en `limite` bytes (y `"rec": true` para que el PC sepa que falta el
    final). None si ni sin texto cabe (entonces no se manda)."""
    exceso = tamano(mensaje) - limite
    if exceso <= 0:
        return mensaje
    d = mensaje.get("detalle")
    if not isinstance(d, str):
        return None
    m = dict(mensaje)
    m["rec"] = True
    while d:
        # Cada caracter ocupa 1 byte o mas: quitar `exceso` caracteres (mas
        # los 3 de los puntos suspensivos) achica al menos lo que sobra; el
        # bucle solo repite si "rec" y los "..." empujaron por encima.
        d = d[:max(0, len(d) - exceso - 3)]
        m["detalle"] = d + "..."
        exceso = tamano(m) - limite
        if exceso <= 0:
            return m
    return None


class Emisor:
    """Numera los mensajes y los guarda hasta su ack. `reintentos` = None
    reintenta sin limite (el carro: no pierde eventos aunque el enlace se
    corte un rato); un numero = reintentos y despues fallo (el PC).

    `sesion` (ver `nueva_sesion`): si se da, cada mensaje lleva `"s"` para
    que el receptor note que este lado se reinicio. None = sin el campo (la
    simulacion de la planta, donde nadie se reinicia)."""

    def __init__(self, reintento_ms, reintentos=None, cola_max=32, sesion=None):
        self.reintento_ms = reintento_ms
        self.reintentos = reintentos
        self.cola_max = cola_max
        self.sesion = sesion
        self._siguiente = 1
        self.pendientes = {}     # id -> [mensaje, t_envio, intentos]
        self.fallidos = []
        self.descartados = 0
        self.grandes = 0         # mensajes que no cabian en `limite` (no se guardaron)

    def enviar(self, mensaje: dict, t_ms: int, limite: int | None = None) -> dict | None:
        """Numera y guarda el mensaje. Con `limite` (bytes: la radio), si no
        cabe se recorta su `detalle` (`recortar`); si ni asi cabe NO se
        guarda (nunca saldria) y devuelve None (se cuenta en `grandes`)."""
        m = dict(mensaje)
        m["id"] = self._siguiente
        if self.sesion is not None:
            m["s"] = self.sesion
        if limite is not None:
            m = recortar(m, limite)
            if m is None:
                self.grandes += 1
                return None
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
    repetidos (un reenvio cuyo ack se perdio no se ejecuta dos veces).

    - Sesion: si el mensaje trae `"s"` distinta de la ultima, el emisor se
      reinicio (sus ids volvieron a 1): se olvidan los ids vistos.
    - Memoria acotada: guarda solo los ultimos `ventana` ids (antes crecia
      sin tope, y en el ESP32 eso es RAM que se acaba). Como los ids de una
      sesion solo crecen, uno MENOR que el mas viejo de la ventana es un
      reenvio muy atrasado: se trata como repetido (ack, sin ejecutar)."""

    def __init__(self, ventana=64):
        self.ventana = ventana
        self.vistos = set()
        self.sesion = None
        self.repetidos = 0
        self.reinicios = 0       # veces que el otro lado arranco una sesion nueva

    def ver_sesion(self, sesion) -> bool:
        """True (y olvida los ids) si `sesion` es nueva."""
        if sesion is None or sesion == self.sesion:
            return False
        if self.sesion is not None:
            self.reinicios += 1
        self.sesion = sesion
        self.vistos = set()
        return True

    def recibir(self, mensaje: dict) -> tuple[bool, dict]:
        id_ = mensaje["id"]
        self.ver_sesion(mensaje.get("s"))
        ack = {"t": "ack", "id": id_, "ok": True}
        if id_ in self.vistos or (len(self.vistos) >= self.ventana and id_ < min(self.vistos)):
            self.repetidos += 1
            return False, ack
        self.vistos.add(id_)
        if len(self.vistos) > self.ventana:
            self.vistos.discard(min(self.vistos))
        return True, ack

    def olvidar(self, id_: int) -> None:
        """Des-marca un id: el comando NO se llego a ejecutar (el ESP32 fijo lanzo
        una excepcion a mitad, p. ej. OSError del PCA9685). Si el PC lo reenvia,
        se vuelve a intentar en vez de contestar "ok" sin haber hecho nada."""
        self.vistos.discard(id_)


class Secuencia:
    """Eventos con numero de secuencia `n` (ESP32 fijo -> PC): detecta huecos.

    Si el ESP32 se reinicia, `n` vuelve a empezar: se reinicia la cuenta al
    ver una sesion nueva (`ver_sesion`, con la `"s"` de su latido) o, si no
    llego ese latido, al ver que `n` retrocede (por USB no se reordena nada:
    un `n` que baja solo puede ser un arranque nuevo)."""

    def __init__(self, ultimo=0, perdidos=0):
        self.ultimo = ultimo
        self.perdidos = perdidos
        self.sesion = None
        self.reinicios = 0

    def ver_sesion(self, sesion) -> bool:
        if sesion is None or sesion == self.sesion:
            return False
        if self.sesion is not None:
            self.reinicios += 1
            self.ultimo = 0
        self.sesion = sesion
        return True

    def recibir(self, n: int) -> int:
        """Devuelve cuantos se perdieron antes de este (0 si ninguno)."""
        if self.ultimo and n <= self.ultimo:
            self.reinicios += 1          # el ESP32 arranco de nuevo sin avisar
            self.ultimo = 0
        hueco = max(0, n - self.ultimo - 1) if self.ultimo else 0
        self.perdidos += hueco
        self.ultimo = n
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


class LimiteAvisos:
    """Avisos de un error que se REPITE (el mismo sensor muerto en cada vuelta del
    bucle, cada ~2 ms): se avisa la primera vez y despues como mucho uno cada
    `cada_ms`; los que se callan se cuentan y van en el aviso siguiente. Antes el
    main.py del fijo mandaba ~500 eventos por segundo al USB (y el PC a SQLite)."""

    def __init__(self, cada_ms=1000):
        self.cada_ms = cada_ms
        self.ultimo = None       # t_ms del ultimo aviso que si salio
        self.callados = 0        # errores desde entonces que no se avisaron

    def debe_avisar(self, t_ms: int) -> bool:
        if self.ultimo is None or t_ms - self.ultimo >= self.cada_ms:
            self.ultimo = t_ms
            return True
        self.callados += 1
        return False

    def tomar_callados(self) -> int:
        n = self.callados
        self.callados = 0
        return n


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
