"""Puente PC <-> ESP32 fijo por USB serial (fase 8, docs/especificacion.md 10.1).

Del lado del PC hace lo mismo que el firmware del otro lado, con la misma
logica (control/protocolo.py):

- `comando(dst, act, **datos)`: numera el comando, lo manda y lo guarda hasta
  su ack; sin ack en `pc_reintento_ms` lo reenvia UNA vez y despues lo marca
  como `fallo_comunicacion`.
- `atender(t_ms)`: DRENA todo lo que haya en el puerto (no una sola linea por
  vuelta: si no, se va quedando atras; ver la regla de comunicacion serial de la
  carpeta Micros, `.claude/rules/serial.md`), cuenta los
  mensajes perdidos por huecos en `n`, guarda la ultima telemetria, los
  eventos y la ultima linea CRUDA recibida (la mejor herramienta cuando "no
  llega nada": si la linea cruda no cambia, el ESP32 no esta mandando; si
  cambia pero no se entiende, es formato, no cables).
- Latido: manda el suyo y avisa si deja de oir al ESP32 (`sin_esp32`).

Sin ESP32 conectado (patron del repo: nunca "tronar"): si el puerto no
abre, el puente usa una ESTACION EMULADA que corre el firmware de verdad
(firmware/fijo/estacion.py) con un hardware falso, para probar todo el
camino sin la placa. `conectado` dice cual de los dos es.
"""

from __future__ import annotations

import json
import time

from control import protocolo

BAUDIOS = 115200
MAX_LINEA = 4096     # bytes sin "\n" a partir de los cuales se descarta el buffer


class HardwareEmulado:
    """Lo minimo que el firmware le pide al hardware, en memoria: cintas que
    tardan lo que tardan, servos que quedan donde se los manda y sensores que
    se pueden fijar desde afuera (pruebas o `probar_hardware`)."""

    def __init__(self):
        self.t_ms = 0
        self.fin = {}                         # cinta -> t_ms en que termina
        self.servos = {}
        self.carrusel = 0                     # tubo pedido (0 a 5)
        self.carrusel_lugar = "carga"
        self.carrusel_fin = -1                # t_ms en que el carrusel termina de girar
        self.sensores = {"presencia": False, "capacitivo": False, "inductivo": False, "hall": False,
                         "cortina_mm": None, "interior_mm": 120}
        self.pasos = {"monedas": 0, "vasos": 0}

    def leer(self):
        d = dict(self.sensores)
        d["carrusel"] = self.carrusel
        return d

    def avanzar_cinta(self, nombre, mm, ms):
        self.fin[nombre] = self.t_ms + ms
        self.pasos[nombre] += 1

    def cinta_moviendose(self, nombre):
        return self.t_ms < self.fin.get(nombre, -1)

    def detener_cinta(self, nombre):
        self.fin.pop(nombre, None)

    def detener_cintas(self):
        self.fin.clear()

    def servo(self, nombre, angulo):
        self.servos[nombre] = angulo

    def carrusel_a(self, tubo, lugar="carga"):
        # El giro tarda lo que en la placa (2026-09-28): medio paso cada 2 ms,
        # 4096 medios pasos por vuelta, por el camino corto (hasta media vuelta =
        # 4,1 s). El agujero esta 210 grados despues de la carga.
        def grados(k, l):
            # Angulo del disco (como control/carrusel.py y firmware/fijo/hw.py): el
            # tubo k llega a la carga girando -60 k; al agujero, 210 grados mas.
            return (-k * 60 + (210 if l == "agujero" else 0)) % 360

        dif = abs((grados(tubo, lugar) - grados(self.carrusel, self.carrusel_lugar) + 180) % 360 - 180)
        self.carrusel_fin = self.t_ms + round(dif / 360 * 4096) * 2
        self.carrusel = tubo
        self.carrusel_lugar = lugar

    def carrusel_detener(self):
        # Parada segura: el carrusel se queda donde esta (igual que Carrusel.detener() de hw.py).
        self.carrusel_fin = self.t_ms

    def carrusel_moviendose(self):
        return self.t_ms < self.carrusel_fin

    def carrusel_buscar_referencia(self):
        self.carrusel = 0
        self.carrusel_lugar = "carga"


class EstacionEmulada:
    """Se comporta como el puerto serial de un ESP32 fijo con su firmware."""

    def __init__(self, parametros: dict):
        from firmware.fijo.estacion import Estacion
        from firmware.preparar import config_fijo

        self.hw = HardwareEmulado()
        self._salida: list[bytes] = []
        self.al_carro: list[str] = []
        self.estacion = Estacion(self.hw, config_fijo(parametros), self._al_pc, self.al_carro.append)

    def _al_pc(self, texto: str) -> None:
        self._salida.append(texto.encode())

    def correr_hasta(self, t_ms: int) -> None:
        self.hw.t_ms = t_ms
        self.estacion.tick(t_ms)

    # --- interfaz de pyserial que usa el puente ---
    @property
    def in_waiting(self) -> int:
        return sum(len(x) for x in self._salida)

    def readline(self) -> bytes:
        return self._salida.pop(0) if self._salida else b""

    def read(self, n: int) -> bytes:
        """Como pyserial: hasta `n` bytes de lo que haya (el puente lee asi, no por lineas)."""
        todo = b"".join(self._salida)
        self._salida = [todo[n:]] if todo[n:] else []
        return todo[:n]

    def write(self, datos: bytes) -> None:
        for linea in datos.decode().splitlines():
            self.estacion.linea_del_pc(linea, self.hw.t_ms)

    def close(self) -> None:
        pass


def buscar_puerto() -> str | None:
    from serial.tools import list_ports

    for p in list_ports.comports():
        if p.vid in (0x10C4, 0x1A86):        # CP2102 / CH340 de las placas de los labs
            return p.device
    return None


class PuenteESP32:
    def __init__(self, parametros: dict, puerto: str | None = None, *, puerto_serial=None):
        p = parametros["protocolo"]
        self.parametros = parametros
        self.conectado = False
        self.emulada: EstacionEmulada | None = None
        if puerto_serial is not None:
            self.ser = puerto_serial
        else:
            self.ser = None
            try:
                import serial

                nombre = puerto or buscar_puerto()
                if nombre:
                    self.ser = serial.Serial(nombre, BAUDIOS, timeout=0)
                    self.conectado = True
            except (ImportError, OSError, ValueError):
                self.ser = None
            if self.ser is None:
                # Sin ESP32: la estacion emulada (mismo firmware, hardware falso).
                self.emulada = EstacionEmulada(parametros)
                self.ser = self.emulada
        # Sesion (docs/especificacion.md 10.1): va en cada comando y en el latido; si el PC
        # se reinicia y el ESP32 no, sus ids vuelven a 1 y sin esto el ESP32
        # los tomaria por repetidos (ack sin ejecutar).
        self.emisor = protocolo.Emisor(p["pc_reintento_ms"], p.get("pc_reintentos", 1),
                                       sesion=protocolo.nueva_sesion())
        self.secuencia = protocolo.Secuencia()
        self.latido = protocolo.Latido(p["pc_latido_ms"], p["pc_sin_latido_ms"])
        self.tel: dict = {}
        self.eventos: list[dict] = []
        self.respuestas: dict[int, dict] = {}   # id -> ack
        self.fallidos: list[dict] = []
        self.ultima_linea_cruda = ""
        self.lineas_malas = 0
        # Bytes recibidos que todavia no completan una linea (ver `atender`).
        self._buf = b""

    def _escribir(self, mensaje: dict) -> None:
        self.ser.write(protocolo.linea(mensaje).encode())

    def comando(self, dst: str, act: str, t_ms: int, **datos) -> int:
        m = {"t": "cmd", "dst": dst, "act": act}
        m.update(datos)
        m = self.emisor.enviar(m, t_ms)
        self._escribir(m)
        return m["id"]

    def atender(self, t_ms: int) -> None:
        if self.emulada is not None:
            self.emulada.correr_hasta(t_ms)
        # Se DRENA todo lo que haya (no una sola linea por vuelta) a un buffer propio y se parte por
        # "\n". NO se usa `readline()`: con timeout=0 (para no frenar el bucle; ver la regla de comunicacion serial de la carpeta Micros,
        # `.claude/rules/serial.md`)
        # devuelve lo que haya llegado aunque la linea este a medias, y esa media linea se contaba
        # como mala y se perdia (el resto llegaba en la vuelta siguiente, tambien "malo"). A 115200
        # baudios una linea de 150 bytes tarda ~13 ms: que llegue partida entre dos vueltas del
        # supervisor (cada 20 ms) es lo normal, no un error. Lo que no termina en "\n" se guarda
        # para la vuelta siguiente.
        n = self.ser.in_waiting
        if n > 0:
            self._buf += self.ser.read(n)
        if len(self._buf) > MAX_LINEA and b"\n" not in self._buf:
            # Basura sin fin de linea (baudios equivocados, ruido): se descarta para no crecer sin tope.
            self.ultima_linea_cruda = self._buf[-120:].decode("utf-8", errors="replace")
            self._buf = b""
            self.lineas_malas += 1
        while b"\n" in self._buf:
            cruda, self._buf = self._buf.split(b"\n", 1)
            if not cruda.strip():
                continue
            self.ultima_linea_cruda = cruda.decode("utf-8", errors="replace").strip()
            m = protocolo.parsear_linea(cruda)
            if m is None:
                self.lineas_malas += 1
                continue
            self.latido.oido(t_ms)
            if m["t"] == "ack" and "dst" not in m:
                self.emisor.ack(m["id"])
                self.respuestas[m["id"]] = m
                continue
            if m["t"] == "hb":
                self.secuencia.ver_sesion(m.get("s"))   # ESP32 reiniciado: `n` empieza de nuevo
            if "n" in m and m["t"] != "hb":
                self.secuencia.recibir(m["n"])
            if m["t"] == "tel":
                self.tel = m
            elif m["t"] == "evt":
                self.eventos.append(m)
        for m in self.emisor.a_reenviar(t_ms):
            self._escribir(m)
        for m in self.emisor.fallidos:
            self.fallidos.append(m)
            self.eventos.append({"t": "evt", "src": "pc", "ev": "fallo_comunicacion", "cmd": m})
        self.emisor.fallidos.clear()
        if self.latido.debe_enviar(t_ms):
            # `n` = ultimo id mandado (el contrato pide `n` en el latido) y `s`
            # la sesion, para que el ESP32 olvide los ids de un PC anterior.
            self._escribir({"t": "hb", "n": self.emisor._siguiente - 1, "s": self.emisor.sesion})
        cambio = self.latido.cambio(t_ms)
        if cambio:
            self.eventos.append({"t": "evt", "src": "pc", "ev": "sin_esp32" if cambio == "perdido" else "esp32_ok"})

    def estado(self) -> dict:
        return {"conectado": self.conectado, "emulada": self.emulada is not None, "tel": self.tel,
                "perdidos": self.secuencia.perdidos, "lineas_malas": self.lineas_malas,
                "ultima_linea_cruda": self.ultima_linea_cruda, "pendientes": len(self.emisor.pendientes),
                "fallidos": len(self.fallidos)}

    def cerrar(self) -> None:
        self.ser.close()


def main() -> None:
    """Diagnostico rapido: se conecta (o emula), da unos latidos, avanza una
    casilla de cada cinta y muestra lo que llega, con la ultima linea cruda."""
    from app.configuracion import cargar_parametros

    puente = PuenteESP32(cargar_parametros())
    print("ESP32 conectado" if puente.conectado else "Sin ESP32: estacion EMULADA (mismo firmware, hardware falso)")
    t0 = time.monotonic()
    ahora = lambda: int((time.monotonic() - t0) * 1000)  # noqa: E731
    fin = ahora() + 4000
    enviados = False
    while ahora() < fin:
        puente.atender(ahora())
        if not enviados and ahora() > 800:
            puente.comando("linea", "avanzar", ahora())
            puente.comando("vasos", "avanzar", ahora())
            enviados = True
        time.sleep(0.01)
    print(json.dumps(puente.estado(), ensure_ascii=False, indent=2))
    for e in puente.eventos[-8:]:
        print("evento:", e)
    puente.cerrar()


if __name__ == "__main__":
    main()
