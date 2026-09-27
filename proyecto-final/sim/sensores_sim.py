"""Emulacion de sensores sobre el mundo de PyBullet (CLAUDE.md, seccion 11).

Implementa `control.hal.interfaces.SensorDiscreto` contra `sim/mundo.py`.
Dos familias:

- `SensorRayo`: infrarrojo de presencia y franjas de medida de la camara de
  vasos. Todos son el mismo truco -- `rayTest` entre dos puntos fijos
  del mundo; si el rayo golpea algo que no sea la propia cinta (o el
  cuerpo que se le diga ignorar), el sensor esta bloqueado.
- `SensorCono`: el VL53L0X de la cortina de seguridad, con su cono real
  (varios `rayTest` repartidos dentro del cono, no un solo rayo).
- `CamaraOraculo`: la camara cenital de monedas en modo oraculo (al final
  del archivo).
- `SensorMaterial`: el par capacitivo/inductivo. No hay forma fisica real
  de "sentir" material con un rayo, asi que en vez de rayTest consulta la
  bandera `metal` que cada cuerpo trae desde que se creo en
  `sim/mundo.py` (seccion 11: "el capacitivo responde a cualquier cuerpo
  presente, el inductivo solo a los marcados como metalicos").
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pybullet as p

from control import monedas
from control.hal.interfaces import SensorDiscreto

from .mundo import Elemento, EscenaEstacion


def _con_error(real: bool, falso_negativo: float, falso_positivo: float, rng: random.Random) -> bool:
    """Aplica el error individual del sensor a la lectura real: a veces no
    ve lo que hay (falso negativo) y a veces ve algo que no hay (falso
    positivo). Probabilidades por lectura, de config/parametros.yaml
    (errores_sensores)."""
    if real and falso_negativo > 0 and rng.random() < falso_negativo:
        return False
    if not real and falso_positivo > 0 and rng.random() < falso_positivo:
        return True
    return real


@dataclass
class SensorRayo(SensorDiscreto):
    origen: tuple[float, float, float]
    destino: tuple[float, float, float]
    ignorar_body_id: int | None = None
    probabilidad_falso_negativo: float = 0.0
    probabilidad_falso_positivo: float = 0.0
    rng: random.Random = field(default_factory=random.Random)

    def leer(self) -> bool:
        cuerpo_golpeado = p.rayTest(self.origen, self.destino)[0][0]
        bloqueado = cuerpo_golpeado != -1 and cuerpo_golpeado != self.ignorar_body_id
        return _con_error(bloqueado, self.probabilidad_falso_negativo, self.probabilidad_falso_positivo, self.rng)

    def configurar_error(self, falso_negativo: float, falso_positivo: float, rng: random.Random) -> None:
        self.probabilidad_falso_negativo = falso_negativo
        self.probabilidad_falso_positivo = falso_positivo
        self.rng = rng


class SensorMaterial(SensorDiscreto):
    """`requiere_metal=False` es el capacitivo (cualquier cuerpo presente),
    `requiere_metal=True` es el inductivo (solo cuerpos metalicos)."""

    def __init__(self, escena: EscenaEstacion, lista: str, casilla: int, *, requiere_metal: bool):
        self._escena = escena
        self._lista = lista
        self._casilla = casilla
        self._requiere_metal = requiere_metal
        self.probabilidad_falso_negativo = 0.0
        self.probabilidad_falso_positivo = 0.0
        self.rng = random.Random()

    def configurar_error(self, falso_negativo: float, falso_positivo: float, rng: random.Random) -> None:
        self.probabilidad_falso_negativo = falso_negativo
        self.probabilidad_falso_positivo = falso_positivo
        self.rng = rng

    def _elemento_presente(self) -> Elemento | None:
        elementos = self._escena.elementos_monedas if self._lista == "monedas" else self._escena.elementos_vasos
        for elemento in elementos:
            if elemento.activo and elemento.casilla == self._casilla:
                return elemento
        return None

    def leer(self) -> bool:
        elemento = self._elemento_presente()
        real = False if elemento is None else (elemento.metal if self._requiere_metal else True)
        return _con_error(real, self.probabilidad_falso_negativo, self.probabilidad_falso_positivo, self.rng)


class CamaraVasos:
    """Webcam al costado de la cinta de vasos, con un panel de luz detras
    (los vasos se ven como silueta a contraluz). Ve a la vez verificacion,
    llenado y tapa, y reemplaza a las 6 barreras IR que habia antes (grupo,
    2026-09-25). En cada estacion mide:

    - la silueta en dos franjas horizontales ("barreras virtuales", ver
      `franja_silueta_vaso`): media altura y justo por encima del borde;
    - el numero del marcador ArUco impreso en el vaso (`leer`);
    - si hay una tapa sobre la boca (`leer_tapa`), despues de soltarla;
    - la posicion de la cinta (ver `PosicionCintaCamara`).

    El marcador va impreso en una CINTA que rodea todo el vaso (el mismo
    ArUco repetido 6 veces alrededor): siempre hay uno de frente a la camara,
    gire como gire el vaso. Lo que hay ADENTRO de un vaso opaco no lo ve: eso
    lo resuelve el sensor que mira al interior (`SensorInteriorVaso`).

    Las franjas son `SensorRayo` aparte (las arma el backend) porque en la
    simulacion la silueta se emula con un rayo a esa altura: lo que corta el
    rayo es exactamente lo que taparia esa franja de la imagen."""

    def __init__(self, escena: EscenaEstacion):
        self._escena = escena
        self.probabilidad_no_lee = 0.0        # marcador ArUco
        self.probabilidad_no_ve_tapa = 0.0    # tapa sobre la boca
        self.rng = random.Random()

    def marcador_en(self, casilla: int) -> int | None:
        """Lo que hay de verdad en la casilla, sin error (para la telemetria;
        la estacion decide con `leer`)."""
        for vaso in self._escena.elementos_vasos:
            if vaso.activo and vaso.casilla == casilla:
                return vaso.marcador
        return None

    def leer(self, casilla: int) -> int | None:
        marcador = self.marcador_en(casilla)
        if marcador is not None and self.probabilidad_no_lee > 0 and self.rng.random() < self.probabilidad_no_lee:
            return None
        return marcador

    def tapa_en(self, casilla: int) -> bool:
        """Verdad de terreno: hay un vaso con tapa en esa casilla."""
        return any(v.activo and v.casilla == casilla and v.tapado for v in self._escena.elementos_vasos)

    def leer_tapa(self, casilla: int) -> bool:
        """La tapa se ve como una franja naranja sobre el reborde, por
        encima de la silueta del vaso. Es mucho mas facil de ver que el
        marcador (una franja de color grande, no un patron chico): tiene su
        propio error, `probabilidad_no_ve_tapa`."""
        real = self.tapa_en(casilla)
        if real and self.probabilidad_no_ve_tapa > 0 and self.rng.random() < self.probabilidad_no_ve_tapa:
            return False
        return real


class PosicionCintaCamara(SensorDiscreto):
    """Posicion de una cinta medida con su camara (grupo, 2026-09-25: reemplaza
    al sensor de ranura). Con la cinta quieta, la camara ve los separadores
    (la de E5 los de su casilla; la de vasos los de sus 4 casillas, a
    contraluz) y mide cuantos milimetros quedaron corridos respecto de donde
    deberian estar. `leer()` es True si quedo en su lugar; si no, el PC le
    manda al motor los micropasos que faltan (re-sincroniza) en la misma
    pausa. Da mas informacion que la ranura (cuanto se corrio, no solo si) y
    no es un sensor mas. En la simulacion la cinta nunca se desfasa sola:
    `probabilidad_desfase` modela el patinaje (config: errores_actuadores.cinta)
    y los falsos, que la camara no vea bien el separador."""

    def __init__(self):
        self.probabilidad_desfase = 0.0
        self.probabilidad_falso_negativo = 0.0
        self.probabilidad_falso_positivo = 0.0
        self.rng = random.Random()
        # El desfase es de la CINTA, no de la lectura: se sortea una vez por
        # avance (`nuevo_avance`) y dura hasta que el firmware re-sincroniza.
        self.desfasada = False

    def nuevo_avance(self) -> None:
        if self.probabilidad_desfase > 0 and self.rng.random() < self.probabilidad_desfase:
            self.desfasada = True

    def resincronizar(self) -> None:
        self.desfasada = False

    def configurar_error(self, falso_negativo: float, falso_positivo: float, rng: random.Random) -> None:
        self.probabilidad_falso_negativo = falso_negativo
        self.probabilidad_falso_positivo = falso_positivo
        self.rng = rng

    def leer(self) -> bool:
        return _con_error(not self.desfasada, self.probabilidad_falso_negativo, self.probabilidad_falso_positivo, self.rng)


class SensorInteriorVaso(SensorDiscreto):
    """VL53L0X (el mismo modelo de la cortina) sobre la casilla de
    verificacion, mirando hacia ABAJO, al interior del vaso. Los vasos son
    opacos (la camara no ve adentro): si la distancia al fondo es menor que
    la de un vaso vacio menos un margen, el vaso trae algo y no entra. Cada
    vaso arranca de cero. En la simulacion: el vaso tiene `objeto_adentro`,
    mas su error individual."""

    def __init__(self, escena: EscenaEstacion, casilla: int):
        self._escena = escena
        self._casilla = casilla
        self.probabilidad_falso_negativo = 0.0
        self.probabilidad_falso_positivo = 0.0
        self.rng = random.Random()

    def configurar_error(self, falso_negativo: float, falso_positivo: float, rng: random.Random) -> None:
        self.probabilidad_falso_negativo = falso_negativo
        self.probabilidad_falso_positivo = falso_positivo
        self.rng = rng

    def leer(self) -> bool:
        real = any(v.activo and v.casilla == self._casilla and v.objeto_adentro
                   for v in self._escena.elementos_vasos)
        return _con_error(real, self.probabilidad_falso_negativo, self.probabilidad_falso_positivo, self.rng)


class SensorCunaCarro(SensorDiscreto):
    """Infrarrojo de la cuna del carro (TCRT5000/FC-51), mirando al costado
    del vaso cargado. En la simulacion la cuna tiene o no un vaso
    (`ocupada`, la mueve la planta al soltar y cuando el carro se va), mas su
    error individual."""

    def __init__(self):
        self.ocupada = False
        self.probabilidad_falso_negativo = 0.0
        self.probabilidad_falso_positivo = 0.0
        self.rng = random.Random()

    def configurar_error(self, falso_negativo: float, falso_positivo: float, rng: random.Random) -> None:
        self.probabilidad_falso_negativo = falso_negativo
        self.probabilidad_falso_positivo = falso_positivo
        self.rng = rng

    def leer(self) -> bool:
        return _con_error(self.ocupada, self.probabilidad_falso_negativo, self.probabilidad_falso_positivo, self.rng)


class SensorHallCarrusel(SensorDiscreto):
    """Sensor Hall (A3144) y un iman en el carrusel del almacen: marca su
    posicion de referencia. El motor paso a paso del carrusel no sabe donde
    esta al encender; gira hasta que el Hall ve el iman (homing) y desde ahi
    cuenta pasos. En la simulacion el carrusel siempre encuentra su
    referencia."""

    def leer(self) -> bool:
        return True


class SensorCono(SensorDiscreto):
    """Sensor de distancia de tiempo de vuelo (VL53L0X) con su CONO real, no
    un rayo delgado: el chip emite y recibe en un cono de ~25 grados, asi que
    "ve" cualquier cosa que entre en ese cono, no solo lo que cruza el eje.
    Se emula con varios `rayTest` repartidos dentro del cono (el eje, un
    anillo a medio angulo y otro en el borde) hasta `alcance_m`.

    `alcance_m` es la ventana de distancia que usa el firmware: una lectura
    mas corta que eso es algo DENTRO de la zona (una mano); una mas larga (o
    "fuera de rango") es lo que hay mas alla de la zona y se ignora. Por eso
    no hace falta receptor ni tope al final."""

    def __init__(self, origen, direccion, *, angulo_cono_grados: float, alcance_m: float,
                 ignorar_body_id: int | None = None, rayos_por_anillo: int = 12):
        import math
        self.origen = tuple(origen)
        d = [float(c) for c in direccion]
        n = math.sqrt(sum(c * c for c in d))
        self.direccion = tuple(c / n for c in d)
        self.semiangulo = math.radians(angulo_cono_grados) / 2
        self.alcance_m = alcance_m
        self.destino = tuple(o + c * alcance_m for o, c in zip(self.origen, self.direccion))
        self.radio_final_m = alcance_m * math.tan(self.semiangulo)
        self.ignorar_body_id = ignorar_body_id
        self.probabilidad_falso_negativo = 0.0
        self.probabilidad_falso_positivo = 0.0
        self.rng = random.Random()
        # Dos vectores perpendiculares al eje para repartir los rayos.
        aux = (0.0, 0.0, 1.0) if abs(self.direccion[2]) < 0.9 else (1.0, 0.0, 0.0)
        u = _cruz(self.direccion, aux)
        nu = math.sqrt(sum(c * c for c in u))
        u = tuple(c / nu for c in u)
        v = _cruz(self.direccion, u)
        self._destinos = [self.destino]
        for frac, cantidad in ((0.5, rayos_por_anillo // 2), (1.0, rayos_por_anillo)):
            r = self.radio_final_m * frac
            for k in range(cantidad):
                t = 2 * math.pi * k / cantidad
                self._destinos.append(tuple(self.destino[i] + r * (math.cos(t) * u[i] + math.sin(t) * v[i])
                                            for i in range(3)))

    def rayos(self) -> list[tuple[tuple, tuple]]:
        return [(self.origen, d) for d in self._destinos]

    def leer(self) -> bool:
        resultados = p.rayTestBatch([self.origen] * len(self._destinos), self._destinos)
        real = any(r[0] != -1 and r[0] != self.ignorar_body_id for r in resultados)
        return _con_error(real, self.probabilidad_falso_negativo, self.probabilidad_falso_positivo, self.rng)

    def configurar_error(self, falso_negativo: float, falso_positivo: float, rng: random.Random) -> None:
        self.probabilidad_falso_negativo = falso_negativo
        self.probabilidad_falso_positivo = falso_positivo
        self.rng = rng


def _cruz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


# ---------------------------------------------------------------------
# Fabricas: arman el SensorRayo/SensorMaterial correcto para cada estacion,
# a partir de la geometria que ya conoce sim/mundo.py.
# ---------------------------------------------------------------------


def sensor_presencia_monedas(escena: EscenaEstacion, casilla: int, *, probabilidad_falso_negativo: float = 0.0) -> SensorRayo:
    """Rayo vertical desde arriba de la casilla hasta la cinta: cualquier
    elemento apoyado ahi lo intercepta antes de llegar a la banda."""
    x, y, z = escena.posicion_estacion_monedas(casilla)
    return SensorRayo(
        origen=(x, y, z + 0.05),
        destino=(x, y, z),
        ignorar_body_id=escena.id_cinta_monedas,
        probabilidad_falso_negativo=probabilidad_falso_negativo,
    )


def sensor_capacitivo(escena: EscenaEstacion, casilla: int) -> SensorMaterial:
    return SensorMaterial(escena, "monedas", casilla, requiere_metal=False)


def sensor_inductivo(escena: EscenaEstacion, casilla: int) -> SensorMaterial:
    return SensorMaterial(escena, "monedas", casilla, requiere_metal=True)


def presencia_silueta_vasos(escena: EscenaEstacion, casilla: int) -> SensorMaterial:
    """Presencia de CUALQUIER cosa en la casilla, vista por la camara de
    vasos (silueta a ras de la cinta). En la simulacion basta la bandera
    "cualquier cuerpo presente" (seccion 11), sin otro rayTest."""
    return SensorMaterial(escena, "vasos", casilla, requiere_metal=False)


def franja_silueta_vaso(
    escena: EscenaEstacion, casilla: int, *, altura_frac: float, altura_vaso_mm: float = 90.0
) -> SensorRayo:
    """Franja horizontal de la imagen de la camara de vasos a una fraccion de
    la altura del vaso (seccion 5, paso 9: media altura debe estar ocupada,
    borde debe estar libre). Se emula con un rayo que cruza la casilla a esa
    altura, de la camara hacia el panel de luz."""
    x, y, z = escena.posicion_estacion_vasos(casilla)
    altura = (altura_vaso_mm / 1000) * altura_frac
    ancho_barrido = 0.08
    return SensorRayo(
        origen=(x, y - ancho_barrido / 2, z + altura),
        destino=(x, y + ancho_barrido / 2, z + altura),
        ignorar_body_id=escena.id_cinta_vasos,
    )


# Posicion del VL53L0X de la cortina respecto del eje de la prensa (+x) y
# fondo de su soporte detras de la placa (el visor lo dibuja con estas
# medidas).
X_SENSOR_CORTINA_M = 0.020
FONDO_SOPORTE_CORTINA_M = 0.013


class ZonaIntrusion(SensorDiscreto):
    """Camara de vasos: zona de la imagen POR ENCIMA de la boca del vaso de
    llenado, por donde cae el lote desde el almacen (punto 11, usuario
    2026-09-26). Ahi no tiene que haber nada: cualquier objeto (una mano) es
    una intrusion. Se emula con varios rayos que cruzan la casilla a esa
    altura, de la camara hacia el panel de luz."""

    def __init__(self, rayos: list[SensorRayo]):
        self.rayos = rayos

    def leer(self) -> bool:
        return any(r.leer() for r in self.rayos)

    def configurar_error(self, falso_negativo: float, falso_positivo: float, rng: random.Random) -> None:
        for r in self.rayos:
            r.configurar_error(falso_negativo, falso_positivo / len(self.rayos), rng)


def zona_intrusion_llenado(escena: EscenaEstacion, casilla: int, *, altura_vaso_mm: float = 90.0) -> ZonaIntrusion:
    x, y, z = escena.posicion_estacion_vasos(casilla)
    boca = altura_vaso_mm / 1000
    return ZonaIntrusion([
        # Desde el lado de la camara (afuera de donde puede estar una mano: un
        # rayo que nace dentro de un cuerpo no lo detecta) hasta el panel.
        SensorRayo(origen=(x + dx, y - 0.20, z + boca + dz), destino=(x + dx, y + 0.06, z + boca + dz),
                   ignorar_body_id=escena.id_cinta_vasos)
        for dx in (-0.03, 0.0, 0.03) for dz in (0.015, 0.04)
    ])


def sensor_cortina(
    escena: EscenaEstacion,
    casilla_inicio: int,
    casilla_fin: int,
    *,
    altura_mm: float = 65.0,
    angulo_cono_grados: float = 25.0,
    desplazamiento_lateral_m: float = 0.085,
) -> SensorCono:
    """Cortina de la zona de tapa y prensa (paso a paso, punto 11): UN
    VL53L0X a media altura (`altura_mm` sobre la cinta), del lado del
    OPERADOR, en el extremo de la prensa mirando hacia la tapa (-x), a lo
    largo de la zona. Va corrido `desplazamiento_lateral_m` del eje de la
    cinta para que su cono (que se abre con la distancia) no toque los vasos,
    la tapa ni la prensa, que estan sobre el eje: si los tocara, se
    dispararia sola en cada ciclo. Su soporte queda fuera de la vista que la
    camara de vasos necesita."""
    x0, y, z = escena.posicion_estacion_vasos(casilla_inicio)
    x1, _, _ = escena.posicion_estacion_vasos(casilla_fin)
    yc = y - desplazamiento_lateral_m
    # 20 mm pasado el eje de la prensa, no mas: el vaso que el empujador pasa
    # de la descarga a la canaleta ocupa desde ~44 mm pasado la prensa, y el
    # sensor y su poste (que va detras de la placa) no pueden estorbarle.
    origen = (x1 + X_SENSOR_CORTINA_M, yc, z + altura_mm / 1000)
    # La ventana termina a media casilla antes de la tapa: lo que este mas
    # lejos (los vasos de llenado y verificacion) no cuenta.
    alcance = origen[0] - (x0 - 0.04)
    return SensorCono(origen, (-1.0, 0.0, 0.0), angulo_cono_grados=angulo_cono_grados, alcance_m=alcance)


# ---------------------------------------------------------------------
# Camara de monedas (E3) en modo oraculo
# ---------------------------------------------------------------------
#
# Clasificador en modo oraculo (CLAUDE.md, seccion 11 y seccion 12).
#
# "Para las fases tempranas, el clasificador corre en modo oraculo: lee la
# clase real del cuerpo y le aplica un ruido configurable de confusion, de
# modo que la linea completa se puede probar antes de tener el modelo
# entrenado." Este modulo hace exactamente eso. El veredicto que devuelve
# `observar()` tiene el mismo contrato que mas adelante (fase 5) va a
# producir `vision/clasificador.py` a partir de una imagen real, y que ya
# consume `control.linea.LineaMonedas.estacion_5_vision`: diametro medido,
# circularidad, contornos internos, clase y confianza.
#
# El diametro/circularidad/contornos_internos de un elemento son medidas
# geometricas: en esta simulacion se conocen exactas desde que el cuerpo se
# creo (no hay ruido de segmentacion todavia, eso tambien es fase 5). El
# unico ruido configurable aqui es el de CLASIFICACION -- que es, ademas, el
# que de verdad importa probar: la geometria sola no distingue una moneda
# colombiana de una extranjera de diametro parecido (CLAUDE.md, seccion 6).





@dataclass
class VeredictoOraculo:
    diametro_mm: float
    circularidad: float
    contornos_internos: int
    clase: str
    confianza: float


@dataclass
class CamaraOraculo:
    """`probabilidad_error` es la probabilidad de que una moneda
    colombiana genuina salga mal clasificada (como 'otro', con confianza
    baja) -- el ruido de confusion de la seccion 11. En 0.0 el oraculo es
    perfecto para clase/confianza (la geometria sigue siendo la real del
    cuerpo, eso nunca tiene ruido aqui)."""

    probabilidad_error: float = 0.0
    # Probabilidad de reconocer la cara como OTRA clase colombiana (con
    # confianza alta): el error peligroso, el que dejaria pasar una moneda
    # a un vaso que no es el suyo. Lo atajan las dos fotos y la coherencia.
    probabilidad_confusion: float = 0.0
    confianza_correcta: float = 0.95
    confianza_error: float = 0.40
    # Error de MEDICION (fase 5 lo reemplaza por la segmentacion real):
    # desviacion estandar del diametro medido y de la circularidad.
    ruido_diametro_mm: float = 0.0
    ruido_circularidad: float = 0.0
    rng: random.Random = field(default_factory=random.Random)

    def observar(self, elemento: Elemento) -> VeredictoOraculo:
        clase_real = elemento.clase_real

        # Una familia con la que no se entreno el modelo (muy_antigua e
        # historica, TEMPORAL) no se reconoce: sale como 'otro'.
        no_entrenada = clase_real is not None and not monedas.reconocible(clase_real)
        se_confunde = clase_real is None or no_entrenada or (
            self.probabilidad_error > 0 and self.rng.random() < self.probabilidad_error
        )

        if se_confunde:
            clase = monedas.CLASE_OTRO
            confianza = self.confianza_error
        elif self.probabilidad_confusion > 0 and self.rng.random() < self.probabilidad_confusion:
            otras = [c for c in monedas.clases_colombianas() if c != clase_real and monedas.reconocible(c)]
            clase = self.rng.choice(otras)
            confianza = 0.90
        else:
            clase = clase_real
            confianza = self.confianza_correcta

        diametro = elemento.diametro_mm
        circularidad = elemento.circularidad
        if self.ruido_diametro_mm > 0:
            diametro = round(diametro + self.rng.gauss(0, self.ruido_diametro_mm), 2)
        if self.ruido_circularidad > 0:
            circularidad = round(min(1.0, circularidad + self.rng.gauss(0, self.ruido_circularidad)), 3)
        return VeredictoOraculo(
            diametro_mm=diametro,
            circularidad=circularidad,
            contornos_internos=elemento.contornos_internos,
            clase=clase,
            confianza=confianza,
        )
