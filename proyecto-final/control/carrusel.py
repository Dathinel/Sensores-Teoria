"""Carrusel del almacen tipo revolver (docs/especificacion.md, seccion 5, pasos 8 y 10):
DONDE esta y CUANDO llega. Python puro, sin PyBullet ni pyserial.

Por que existe (pedido del usuario 2026-09-28, "la moneda pasa sin que se
espere a que de la vuelta"): la simulacion guardaba la moneda en su tubo en
el mismo instante en que llegaba a la descarga, sin girar nada, y el visor
3D animaba el giro por su cuenta, en una cola que se iba atrasando. El
carrusel real es un 28BYJ-48 que da un medio paso cada 2 ms: media vuelta
tarda `tiempos_ms.carrusel_giro` (4096 ms) y un tubo vecino (60 grados)
1365 ms, mas que el ciclo de la cinta de monedas (1600 ms) menos lo que
tarda la vision. Este modulo lleva la cuenta de ese giro con el tiempo real
para que la planta (sim/planta.py) sepa si el tubo YA esta bajo la carga
antes de soltar la moneda, y si no, cuanto falta.

Geometria (la misma de sim/mundo.py, que la pasa como argumentos):

- 6 posiciones en hexagono: `posiciones[k]` (50, 100, 200, 500, 1000,
  "otras"). Con el carrusel en reposo (angulo 0, justo despues del homing
  con el Hall) la posicion k queda en `angulo_carga + k * 60` grados: la 0
  (el tubo de $50) bajo la carga.
- Dos lugares fijos en la placa: la CARGA (donde cae la moneda que viene de
  la cinta, `angulo_carga` = 90) y el AGUJERO sobre el vaso de llenado
  (`angulo_agujero` = 300). Entre los dos hay 210 grados, que no es multiplo
  de 60: cuando un tubo esta en la carga el agujero queda ENTRE dos tubos, y
  al reves.
- `angulo` es cuanto giro el disco desde el reposo, en grados, positivo
  antihorario visto desde arriba (el mismo sentido que usa el visor 3D para
  `rotation.y`). Es ACUMULADO (puede pasar de 360 o ser negativo), como la
  cuenta de medios pasos del firmware.

Tiempo: el firmware (firmware/fijo/hw.py, `Carrusel`) va por el camino mas
corto a velocidad constante (un medio paso cada `carrusel_ms_por_paso`, sin
rampas), asi que la duracion de un giro es proporcional al angulo:
`giro_media_vuelta_ms * |angulo| / 180`. Un pedido nuevo en mitad de un giro
arranca desde donde va el disco en ese instante (igual que el firmware, que
solo cambia su objetivo).

Ocupado (revision visual 2026-09-29): el disco tampoco puede arrancar mientras
algo CAE a traves de el. Una moneda guardada tarda `tiempos_ms.caida_moneda_tubo`
en bajar por el canal corto hasta el fondo de su tubo, y un lote cae con el
obturador abierto (`compuerta_tubo`): quien suelta algo llama a `ocupar(hasta)`
y todo `pedir` posterior arranca recien en ese instante. Antes el giro hacia el
tubo de la siguiente moneda salia en el MISMO instante en que caia la anterior
y la moneda caia 15-37 mm fuera de la boca.

Este archivo sigue las reglas de control/protocolo.py para poder correr en
MicroPython: sin dataclasses, sin {**d} ni [*x].
"""

from __future__ import annotations

CARGA = "carga"
AGUJERO = "agujero"
LUGARES = (CARGA, AGUJERO)


def _normalizar_180(grados: float) -> float:
    """El mismo angulo llevado a (-180, 180]: el camino mas corto."""
    d = grados % 360.0
    if d > 180.0:
        d -= 360.0
    return d


class Carrusel:
    """Estado y tiempos del carrusel. Todos los instantes son milisegundos
    de un reloj que elige quien lo usa (la planta: ticks x ciclo de la cinta
    de monedas; el firmware: ticks_ms)."""

    def __init__(self, posiciones, giro_media_vuelta_ms: float, angulo_carga: float = 90.0,
                 angulo_agujero: float = 300.0):
        self.posiciones = tuple(posiciones)
        if not self.posiciones:
            raise ValueError("el carrusel necesita al menos una posicion")
        self.paso_grados = 360.0 / len(self.posiciones)
        self.giro_media_vuelta_ms = float(giro_media_vuelta_ms)
        self.angulos_lugar = {CARGA: float(angulo_carga), AGUJERO: float(angulo_agujero)}
        # Reposo tras el homing: la posicion 0 bajo la carga, quieto.
        self.tubo = self.posiciones[0]
        self.lugar = CARGA
        self._desde = 0.0
        self._hasta = 0.0
        self._t_inicio = 0.0
        self._t_llegada = 0.0
        # Hasta cuando el disco no puede arrancar: una moneda cayendo a su
        # tubo o el obturador abierto soltando un lote (`ocupar`).
        self._ocupado_hasta = 0.0
        self.giros = 0
        self.ultimo_giro = None

    # ------------------------------------------------------------------
    # geometria
    # ------------------------------------------------------------------

    def indice(self, tubo) -> int:
        if tubo not in self.posiciones:
            raise ValueError("tubo desconocido: %r" % (tubo,))
        return self.posiciones.index(tubo)

    def angulo_para(self, tubo, lugar: str) -> float:
        """Angulo del disco (grados, en [0, 360)) que deja `tubo` en `lugar`."""
        if lugar not in self.angulos_lugar:
            raise ValueError("lugar desconocido: %r" % (lugar,))
        casa = self.angulos_lugar[CARGA] + self.indice(tubo) * self.paso_grados
        return (self.angulos_lugar[lugar] - casa) % 360.0

    def duracion_ms(self, grados: float) -> float:
        """Lo que tarda el motor en girar `grados` (a velocidad constante)."""
        return self.giro_media_vuelta_ms * abs(grados) / 180.0

    # ------------------------------------------------------------------
    # tiempo
    # ------------------------------------------------------------------

    def angulo_en(self, t_ms: float) -> float:
        """Angulo acumulado del disco en el instante `t_ms`: interpolacion
        LINEAL (velocidad constante, como el Timer del firmware)."""
        if t_ms <= self._t_inicio:
            return self._desde
        if t_ms >= self._t_llegada:
            return self._hasta
        u = (t_ms - self._t_inicio) / (self._t_llegada - self._t_inicio)
        return self._desde + (self._hasta - self._desde) * u

    @property
    def llegada_ms(self) -> float:
        """Instante en que termina (o termino) el ultimo giro pedido."""
        return self._t_llegada

    def listo(self, t_ms: float) -> bool:
        """True si en `t_ms` el carrusel esta quieto."""
        return t_ms >= self._t_llegada

    def va_a(self, tubo, lugar: str) -> bool:
        """True si el ultimo pedido fue justo ese (quieto ahi o en camino)."""
        return self.tubo == tubo and self.lugar == lugar

    def en(self, tubo, lugar: str, t_ms: float) -> bool:
        """True si en `t_ms` `tubo` esta QUIETO en `lugar`: la unica condicion
        para soltar una moneda en su boca o abrir el obturador bajo el."""
        return self.va_a(tubo, lugar) and self.listo(t_ms)

    def ocupar(self, hasta_ms: float) -> None:
        """Algo cae a traves del carrusel hasta `hasta_ms` (una moneda por el
        canal a su tubo, o un lote por el obturador): ningun giro pedido
        despues puede arrancar antes de ese instante."""
        if hasta_ms > self._ocupado_hasta:
            self._ocupado_hasta = float(hasta_ms)

    @property
    def ocupado_hasta_ms(self) -> float:
        return self._ocupado_hasta

    def falta_ms(self, t_ms: float) -> float:
        return max(0.0, self._t_llegada - t_ms)

    def pedir(self, tubo, lugar: str, t_ms: float) -> float:
        """Manda el carrusel a dejar `tubo` en `lugar` a partir de `t_ms`.
        Devuelve el instante (ms) en que llega. Si ya iba (o estaba) ahi, no
        hay giro nuevo y devuelve la llegada que ya tenia. Un pedido nunca
        puede arrancar antes que el giro anterior (el reloj no va hacia
        atras) ni mientras algo cae a traves del disco (`ocupar`): se toma el
        mayor de los tres instantes."""
        objetivo = self.angulo_para(tubo, lugar)
        if self.va_a(tubo, lugar):
            return self._t_llegada
        t = max(float(t_ms), self._t_inicio, self._ocupado_hasta)
        actual = self.angulo_en(t)
        dif = _normalizar_180(objetivo - actual)
        dur = self.duracion_ms(dif)
        self._desde = actual
        self._hasta = actual + dif
        self._t_inicio = t
        self._t_llegada = t + dur
        self.tubo = tubo
        self.lugar = lugar
        self.giros += 1
        self.ultimo_giro = {"tubo": tubo, "lugar": lugar, "desde_grados": round(self._desde, 2),
                            "hasta_grados": round(self._hasta, 2), "dur_ms": int(round(dur)),
                            "t_inicio_ms": t, "t_llegada_ms": self._t_llegada}
        return self._t_llegada

    def tubo_en(self, lugar: str, t_ms: float):
        """Que tubo esta QUIETO en `lugar` en `t_ms` (None si el disco se
        mueve o si en ese lugar queda el hueco entre dos tubos)."""
        if not self.listo(t_ms):
            return None
        rel = (self.angulos_lugar[lugar] - self.angulos_lugar[CARGA] - self.angulo_en(t_ms)) % 360.0
        k = rel / self.paso_grados
        cercano = int(round(k)) % len(self.posiciones)
        if abs(k - round(k)) > 1e-6:
            return None
        return self.posiciones[cercano]

    def estado(self, t_ms: float) -> dict:
        """Para la telemetria (estado() de la planta, visor y dashboard)."""
        girando = not self.listo(t_ms)
        return {
            "tubo_en_carga": self.tubo_en(CARGA, t_ms),
            "tubo": self.tubo,
            "lugar": self.lugar,
            "angulo_grados": round(self.angulo_en(t_ms), 2),
            "girando": girando,
            "llega_en_ms": int(round(self.falta_ms(t_ms))),
            "giros": self.giros,
        }
