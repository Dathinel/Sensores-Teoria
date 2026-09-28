"""Construccion de la escena de PyBullet (CLAUDE.md, seccion 11, fase 2).

Este modulo es el unico lugar de todo el proyecto, junto con el resto de
`sim/`, que puede importar `pybullet`. La capa de control (`control/`) no lo
conoce (seccion 8 y regla 17): `mundo.py` solo construye cuerpos y los
mueve; quien decide QUE hacer con cada elemento (aceptarlo o rechazarlo)
vive en `control/linea.py` y `control/embalaje.py`.

Filosofia de movimiento (seccion 11): no se simula una banda flexible. Los
elementos se mueven entre posiciones de estacion fijas por control de
posicion, interpolando durante un numero fijo de pasos de fisica y haciendo
una pausa despues -- igual que el motor paso a paso real, que avanza
exactamente una casilla y se detiene. Los servos de expulsion se animan
visualmente (el joint sí gira) pero el desplazamiento real
del elemento rechazado se hace por el mismo control de posicion directo, no
por contacto fisico: confiar en que un paddle delgado empuje de forma
confiable a un cilindro pequeño en cada corrida es fragil, y aqui lo que
importa demostrar es la logica de enrutamiento, no la dinamica de contacto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

import pybullet as p
import pybullet_data

from control.almacen import OTRAS
from control.monedas import DENOMINACIONES_CON_TUBO

DIRECTORIO_URDF = Path(__file__).parent / "urdf"

# --- Geometria de las cintas, en metros. Debe coincidir con los <origin> de
# sim/urdf/cinta_monedas.urdf y sim/urdf/cinta_vasos.urdf; si se cambia un
# valor aqui hay que cambiarlo tambien alla. ---
SEPARACION_CASILLA_M = 0.04
# La cinta de vasos tiene su propia separacion: cada casilla encaja la base
# de un vaso de 62 mm (PROVISIONAL), asi que no puede ser la misma de 40 mm
# de la cinta de monedas -- dos vasos en casillas vecinas quedarian
# encimados. Ver config/parametros.yaml (vasos.separacion_casilla_mm).
SEPARACION_CASILLA_VASOS_M = 0.08

# Grupo (2026-09-25): "filtro total". 4 estaciones y una sola salida de
# rechazo (la compuerta de desvio de la descarga); sin expulsores laterales.
NUM_ESTACIONES_MONEDAS = 4
ESTACION_PRESENCIA_MONEDAS = 0  # E1
ESTACION_MATERIAL_MONEDAS = 1   # E2
ESTACION_VISION_MONEDAS = 2     # E3
ESTACION_DESCARGA_MONEDAS = 3   # E4 (desvio: almacen o bandeja de rechazo)

NUM_ESTACIONES_VASOS = 5  # verificacion, llenado, tapa, prensa, descarga
ESTACION_VERIFICACION_VASOS = 0
ESTACION_LLENADO_VASOS = 1
ESTACION_TAPA_VASOS = 2
ESTACION_PRENSA_VASOS = 3
ESTACION_DESCARGA_VASOS = 4

_ALTO_BANCADA = 0.02
_ESPESOR_CINTA = 0.002
ALTURA_SUPERFICIE = _ALTO_BANCADA + _ESPESOR_CINTA  # 0.022 m, top de ambas cintas

_ORIGEN_X_MONEDAS = -0.06  # estacion 0 de cinta_monedas, en su marco local
_ORIGEN_X_VASOS = -0.16    # estacion 0 de cinta_vasos, en su marco local

# Alturas de las mesas (PROVISIONALES, config/parametros.yaml no las fija
# todavia porque dependen del vaso). Se encadenan de abajo hacia arriba:
#  - La canaleta de entrega baja 15 grados colgando el vaso del reborde, y al
#    final el vaso tiene que seguir por encima del piso (y de la cuna del
#    carro). Con 28 cm de riel se pierden ~7,5 cm de altura, asi que la
#    cinta de vasos va sobre una mesa de 10 cm.
#  - Entre la cinta de monedas y la boca del vaso van el selector y los 5
#    tubos del almacen por denominacion (ver TUBOS_* abajo) y la tolva que
#    los descarga al vaso; todo cae por gravedad, asi que la cinta de
#    monedas va arriba de todo. Mesa de 43 cm: la moneda cae por el extremo
#    de la cinta a un embudo y de ahi a un canal que baja ~30 grados hasta el
#    selector (con la mesa de 34 cm el canal quedaba a ~8 grados y una
#    moneda no desliza).
# En la fase 2 las dos cintas estaban al ras del piso; ninguna de las dos
# cosas era posible fisicamente.
ALTURA_MESA_VASOS = 0.10
ALTURA_MESA_MONEDAS = 0.43
# Corrida para que su extremo (la descarga) quede justo encima del punto de
# carga del carrusel del almacen: la moneda cae casi en vertical.
CINTA_MONEDAS_POS = (0.01, 0.0, ALTURA_MESA_MONEDAS)
# Desplazada para que su estacion de llenado (indice 1) quede a la misma x
# que la estacion de descarga de monedas (x local -0.08 + 0.20 = 0.12, igual
# a la estacion 7 de monedas) -- asi el "embudo corto" del paso 8 de la
# seccion 5 conecta ambas cintas en linea recta.
CINTA_VASOS_POS = (0.20, -0.10, ALTURA_MESA_VASOS)

# Grosor aproximado de una moneda real, solo para que el cilindro se vea
# como una ficha delgada en el render. No es un criterio de filtrado (la
# tabla de la seccion 6 no reporta espesor) y no afecta ninguna regla de
# decision.
_GROSOR_MONEDA_M = 0.0018

# --- Almacen por denominacion (regla del grupo: ninguna moneda aceptada se
# descarta y cada vaso lleva UNA denominacion). Cinco tubos verticales en
# pentagono alrededor del eje de la estacion de llenado; un selector
# giratorio (servo) en el centro manda cada moneda al tubo que le toca, y
# cada tubo tiene una compuerta abajo que suelta el lote a la tolva y de
# ahi al vaso. PROVISIONAL: diametros y alturas a confirmar con el CAD. ---
TUBOS_DENOMINACIONES = DENOMINACIONES_CON_TUBO
# Seis posiciones en hexagono: los 5 tubos + el compartimiento "otras" (las
# denominaciones aceptadas sin tubo: $1, $2, $5, $10, $20 de las series
# viejas). Arranca en 90 grados para que ninguna posicion quede hacia +x,
# donde esta el tubo de tapas de la estacion vecina.
POSICIONES_CARRUSEL = (*TUBOS_DENOMINACIONES, OTRAS)
TUBO_RADIO_M = 0.0145          # interior de 29 mm: entra la de 1000 (26,7 mm)
TUBO_ALTO_M = 0.058            # 25 monedas apiladas (capacidad_tubo) + margen
TUBO_BASE_Z = 0.27             # fondo de los tubos (compuerta)
CARRUSEL_RADIO_M = 0.033       # distancia del eje a cada tubo
GROSOR_PILA_M = 0.0022         # lo que sube la pila por cada moneda

# Pasos de fisica (240 por segundo) de cada movimiento. La simulacion corre
# sin ventana: el ritmo real (config: tiempos_ms) lo pone el supervisor entre
# ciclos, y el visor 3D anima cada movimiento con esa duracion.
PASOS_AVANCE_CASILLA = 60
PASOS_PAUSA_CASILLA = 30
PASOS_SERVO = 40
PASOS_POR_SEGUNDO = 240

TipoElemento = Literal["moneda", "boton_plastico", "boton_metalico", "bloque", "vaso"]
Destino = Literal["entrega", "rechazo"]


@dataclass
class Elemento:
    """Un cuerpo fisico sobre una cinta, mas su verdad de terreno (seccion
    11: "cada cuerpo lleva un diccionario de verdad de terreno con su clase
    real"). `diametro_mm`, `circularidad` y `contornos_internos` son las
    medidas que en la vida real saldrian de segmentar la imagen; aqui se
    conocen de antemano porque el cuerpo se creo con ellas, y son las que
    lee la camara oraculo (sim/sensores_sim.py) (fase 3) hasta que exista el
    pipeline real de vision (fase 5)."""

    body_id: int
    tipo: TipoElemento
    clase_real: str | None
    metal: bool
    casilla: int
    diametro_mm: float = 0.0
    circularidad: float = 1.0
    contornos_internos: int = 0
    activo: bool = True
    apariencia: str | None = None   # solo para dibujarlo/nombrarlo (ver sim/carga_escenarios.py)
    # Cuerpos que viajan pegados a este (solo para vasos): las monedas que
    # cayeron adentro y la tapa. Se mueven con el vaso en cada avance y en
    # la descarga, para que se vea el vaso llenarse de verdad.
    contenido: list[int] = field(default_factory=list)
    altura_mm: float = 0.0
    # Identidad persistente del elemento para el registro de casillas. NO
    # usar body_id para eso cuando haya cuerpos que se borran (retirar o
    # cambiar un vaso): PyBullet reutiliza los body_id liberados, y un
    # elemento nuevo terminaria heredando el registro de uno viejo. La
    # asigna quien orquesta la linea (sim/planta.py).
    id_registro: int | None = None
    # Numero del marcador ArUco impreso en un vaso personalizado (solo vasos).
    marcador: int | None = None
    # Tiene la tapa puesta (solo vasos). Lo lee la camara de vasos para
    # confirmar que la tapa de verdad cayo sobre la boca.
    tapado: bool = False
    # Solo vasos: masa del vaso y si alguien le metio un objeto antes de
    # ponerlo en la linea (lo ve el sensor que mira al interior del vaso).
    masa_g: float = 0.0
    objeto_adentro: bool = False


def _interpolar(inicio: tuple[float, float, float], fin: tuple[float, float, float], t: float) -> tuple[float, float, float]:
    return tuple(a + (b - a) * t for a, b in zip(inicio, fin))


def posicion_estacion_monedas(casilla: float) -> tuple[float, float, float]:
    """Centro de la casilla `casilla` de la cinta de monedas, a ras de la
    superficie de la cinta, en coordenadas del mundo (metros). Es funcion de
    modulo (no solo metodo) para que sim/geometria.py -- y a traves de el el
    visor 3D -- use exactamente las mismas posiciones sin abrir PyBullet."""
    x0, y0, z0 = CINTA_MONEDAS_POS
    return (x0 + _ORIGEN_X_MONEDAS + casilla * SEPARACION_CASILLA_M, y0, z0 + ALTURA_SUPERFICIE)


def posicion_estacion_vasos(casilla: float) -> tuple[float, float, float]:
    x0, y0, z0 = CINTA_VASOS_POS
    return (x0 + _ORIGEN_X_VASOS + casilla * SEPARACION_CASILLA_VASOS_M, y0, z0 + ALTURA_SUPERFICIE)


def posicion_rechazo_final() -> tuple[float, float, float]:
    """La UNICA bandeja de rechazo de monedas (grupo, 2026-09-25): en el piso,
    del lado +y de la descarga. La compuerta de desvio en reposo manda ahi
    todo lo que no sea una moneda registrada y aceptada."""
    x, y, _ = posicion_estacion_monedas(ESTACION_DESCARGA_MONEDAS)
    return (x + 0.03, y + 0.13, 0.004)


# --- Almacen tipo revolver (grupo, 2026-09-25: el selector giratorio con un
# pico no era creible -- la moneda llega con velocidad y un pico corto no la
# desvia). Los 6 tubos van en un carrusel que GIRA (un motor paso a paso)
# sobre una placa fija. La placa tiene un solo agujero, sobre el vaso de
# llenado, con un obturador (un servo). Asi:
#  - guardar: el carrusel pone el tubo de la moneda bajo el punto de carga
#    (angulo 90 grados) y la moneda cae casi vertical desde el extremo de la
#    cinta, por un canal corto, directo a la boca del tubo;
#  - soltar un lote: el carrusel pone ese tubo sobre el agujero (angulo 300
#    grados), se abre el obturador y la pila entera cae al vaso.
# Entre carga y agujero hay 210 grados: cuando un tubo esta en la carga, el
# agujero queda ENTRE dos tubos (y al reves), asi que nunca se cargan y se
# sueltan monedas a la vez. Se reemplazan el servo del selector y los 6
# servos de compuerta por un motor y un servo. ---
ANGULO_CARGA_CARRUSEL = 90.0
ANGULO_AGUJERO_CARRUSEL = 300.0


def centro_carrusel() -> tuple[float, float]:
    """Centro del carrusel: tal que el agujero de la placa quede justo sobre
    el vaso de la estacion de llenado."""
    import math

    x, y, _ = posicion_estacion_vasos(ESTACION_LLENADO_VASOS)
    a = math.radians(ANGULO_AGUJERO_CARRUSEL)
    return x - CARRUSEL_RADIO_M * math.cos(a), y - CARRUSEL_RADIO_M * math.sin(a)


def punto_carga_carrusel() -> tuple[float, float]:
    """(x, y) donde cae la moneda que viene de la cinta: la boca del tubo que
    esta en el angulo de carga."""
    import math

    cx, cy = centro_carrusel()
    a = math.radians(ANGULO_CARGA_CARRUSEL)
    return cx + CARRUSEL_RADIO_M * math.cos(a), cy + CARRUSEL_RADIO_M * math.sin(a)


def salida_tolva() -> tuple[float, float]:
    """Punto (x, y) por donde sale el lote: justo sobre el vaso de llenado."""
    x, y, _ = posicion_estacion_vasos(ESTACION_LLENADO_VASOS)
    return x, y


def posicion_bandeja_rechazo_vasos() -> tuple[float, float, float]:
    """Bandeja de rechazo de vasos: al final de la cinta de vasos. Lo que no
    se empuja a la canaleta sigue en la cinta y cae por el extremo (un solo
    empujador no puede empujar hacia los dos lados)."""
    x, y, _ = posicion_estacion_vasos(ESTACION_DESCARGA_VASOS)
    return (x + 0.11, y, 0.004)


def posicion_tubo(clave: int | str) -> tuple[float, float, float]:
    """Centro del FONDO del tubo de esa denominacion, o del compartimiento
    OTRAS (mundo, metros), con el carrusel en su posicion de reposo (el tubo
    de $50 en la carga). PyBullet deja el carrusel quieto ahi; el visor 3D lo
    gira."""
    import math

    k = POSICIONES_CARRUSEL.index(clave)
    cx, cy = centro_carrusel()
    angulo = math.pi / 2 + k * 2 * math.pi / len(POSICIONES_CARRUSEL)
    return (cx + CARRUSEL_RADIO_M * math.cos(angulo), cy + CARRUSEL_RADIO_M * math.sin(angulo), TUBO_BASE_Z)


class EscenaEstacion:
    """Escena con la cinta de monedas y la cinta de vasos cargadas."""

    def __init__(self, *, reusar_cliente: int | None = None):
        self._pasos = {"avance_monedas": PASOS_AVANCE_CASILLA, "pausa_monedas": PASOS_PAUSA_CASILLA,
                       "avance_vasos": PASOS_AVANCE_CASILLA, "pausa_vasos": PASOS_PAUSA_CASILLA,
                       "empujador": PASOS_SERVO}

        # `reusar_cliente`: para reiniciar la escena (nueva corrida) se vacia
        # el mundo de la conexion existente en vez de abrir otra.
        if reusar_cliente is not None and p.isConnected(reusar_cliente):
            self.cliente = reusar_cliente
            p.resetSimulation()
        else:
            self.cliente = p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        p.setPhysicsEngineParameter(fixedTimeStep=1 / 240)
        p.loadURDF("plane.urdf")

        self.id_cinta_monedas = p.loadURDF(
            str(DIRECTORIO_URDF / "cinta_monedas.urdf"),
            basePosition=CINTA_MONEDAS_POS,
            useFixedBase=True,
        )
        self.id_cinta_vasos = p.loadURDF(
            str(DIRECTORIO_URDF / "cinta_vasos.urdf"),
            basePosition=CINTA_VASOS_POS,
            useFixedBase=True,
        )

        self._junta_empujador_vasos = self._indice_junta(self.id_cinta_vasos, "junta_empujador_descarga")

        self.elementos_monedas: list[Elemento] = []
        self.elementos_vasos: list[Elemento] = []


    # ------------------------------------------------------------------
    # geometria
    # ------------------------------------------------------------------

    @staticmethod
    def _indice_junta(body_id: int, nombre_junta: str) -> int:
        for i in range(p.getNumJoints(body_id)):
            info = p.getJointInfo(body_id, i)
            if info[1].decode("utf-8") == nombre_junta:
                return i
        raise ValueError(f"no se encontro la junta '{nombre_junta}'")

    def _paso_fisica(self) -> None:
        p.stepSimulation()

    def posicion_estacion_monedas(self, casilla: float) -> tuple[float, float, float]:
        return posicion_estacion_monedas(casilla)

    def posicion_estacion_vasos(self, casilla: float) -> tuple[float, float, float]:
        return posicion_estacion_vasos(casilla)

    # ------------------------------------------------------------------
    # fabrica de elementos (seccion 11: cilindros para monedas y botones,
    # cajas para bloques, cada uno con su bandera de material)
    # ------------------------------------------------------------------

    def crear_elemento(
        self,
        *,
        tipo: TipoElemento,
        casilla: int = 0,
        clase_real: str | None = None,
        metal: bool = False,
        diametro_mm: float | None = None,
        masa_g: float | None = None,
        circularidad: float | None = None,
        contornos_internos: int | None = None,
    ) -> Elemento:
        """`diametro_mm`, `circularidad` y `contornos_internos` son la
        verdad de terreno geometrica del elemento (lo que en la vida real
        saldria de segmentar la imagen). Tienen un valor por defecto
        razonable segun `tipo`, pero se pueden forzar para armar los
        escenarios de cada filtro (p. ej. una "moneda" con circularidad
        baja para probar la causa `no_circular`)."""
        pos = self.posicion_estacion_monedas(casilla)

        if tipo == "moneda":
            if diametro_mm is None or masa_g is None:
                raise ValueError("una moneda necesita diametro_mm y masa_g (control.monedas)")
            radio = diametro_mm / 2 / 1000
            altura = _GROSOR_MONEDA_M
            masa = masa_g / 1000
            color = (0.80, 0.68, 0.35, 1.0)
            circularidad = 1.0 if circularidad is None else circularidad
            contornos_internos = 0 if contornos_internos is None else contornos_internos
        elif tipo == "boton_plastico":
            diametro_mm = 18.0 if diametro_mm is None else diametro_mm
            radio = diametro_mm / 2 / 1000
            altura = 0.003
            masa = 0.0008
            color = (0.85, 0.15, 0.65, 1.0)
            circularidad = 0.95 if circularidad is None else circularidad
            contornos_internos = 1 if contornos_internos is None else contornos_internos
        elif tipo == "boton_metalico":
            diametro_mm = 20.0 if diametro_mm is None else diametro_mm
            radio = diametro_mm / 2 / 1000
            altura = 0.003
            masa = 0.003
            color = (0.55, 0.55, 0.60, 1.0)
            circularidad = 0.97 if circularidad is None else circularidad
            contornos_internos = 1 if contornos_internos is None else contornos_internos
        else:
            raise ValueError(f"tipo de elemento desconocido para la cinta de monedas: {tipo}")

        col = p.createCollisionShape(p.GEOM_CYLINDER, radius=radio, height=altura)
        vis = p.createVisualShape(p.GEOM_CYLINDER, radius=radio, length=altura, rgbaColor=color)
        cuerpo = p.createMultiBody(
            baseMass=masa,
            baseCollisionShapeIndex=col,
            baseVisualShapeIndex=vis,
            basePosition=[pos[0], pos[1], pos[2] + altura / 2],
        )

        elemento = Elemento(
            body_id=cuerpo,
            tipo=tipo,
            clase_real=clase_real,
            metal=metal,
            casilla=casilla,
            diametro_mm=diametro_mm,
            circularidad=circularidad,
            contornos_internos=contornos_internos,
        )
        self.elementos_monedas.append(elemento)
        return elemento

    def crear_bloque(
        self,
        *,
        casilla: int = 0,
        lado_m: float = 0.02,
        masa: float = 0.004,
        circularidad: float = 0.55,
        metal: bool = False,
    ) -> Elemento:
        """`metal=True` sirve para armar un escenario aislado del filtro
        `no_circular` (seccion 7): un bloque metalico pasa la estacion de
        material y llega a vision, donde lo rechaza la circularidad baja.
        Un bloque de plastico (el `metal=False` por defecto) ya queda
        rechazado por material sin necesitar este filtro -- que es
        exactamente el punto de poder demostrar cada etapa aislada."""
        pos = self.posicion_estacion_monedas(casilla)
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[lado_m / 2] * 3)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[lado_m / 2] * 3, rgbaColor=(0.2, 0.5, 0.85, 1.0))
        cuerpo = p.createMultiBody(
            baseMass=masa,
            baseCollisionShapeIndex=col,
            baseVisualShapeIndex=vis,
            basePosition=[pos[0], pos[1], pos[2] + lado_m / 2],
        )
        elemento = Elemento(
            body_id=cuerpo,
            tipo="bloque",
            clase_real=None,
            metal=metal,
            casilla=casilla,
            diametro_mm=lado_m * 1000,
            circularidad=circularidad,
            contornos_internos=0,
        )
        self.elementos_monedas.append(elemento)
        return elemento

    def crear_vaso(self, *, casilla: int = 0, diametro_mm: float = 62.0, altura_mm: float = 90.0,
                   marcador: int | None = None, masa_g: float = 18.0) -> Elemento:
        radio = diametro_mm / 2 / 1000
        altura = altura_mm / 1000
        pos = self.posicion_estacion_vasos(casilla)

        col = p.createCollisionShape(p.GEOM_CYLINDER, radius=radio, height=altura)
        vis = p.createVisualShape(p.GEOM_CYLINDER, radius=radio, length=altura, rgbaColor=(0.85, 0.9, 0.95, 0.55))
        cuerpo = p.createMultiBody(
            baseMass=0.04,
            baseCollisionShapeIndex=col,
            baseVisualShapeIndex=vis,
            basePosition=[pos[0], pos[1], pos[2] + altura / 2],
        )
        elemento = Elemento(
            body_id=cuerpo, tipo="vaso", clase_real=None, metal=False, casilla=casilla, altura_mm=altura_mm,
            marcador=marcador, masa_g=masa_g,
        )
        self.elementos_vasos.append(elemento)
        return elemento

    # ------------------------------------------------------------------
    # llenado y tapa (seccion 5, pasos 8 y 11). Solo cambian lo que se VE:
    # la decision de si se llena o se tapa ya la tomo control/embalaje.py.
    # ------------------------------------------------------------------

    def depositar_en_vaso(self, moneda: Elemento, vaso: Elemento) -> None:
        """Pasa la moneda de la estacion 7 al fondo del vaso. La moneda se
        vuelve estatica y sin colision (masa 0, filtro de colision en 0):
        si siguiera siendo un cuerpo dinamico dentro del cilindro solido
        del vaso, PyBullet la expulsaria del vaso en el siguiente paso de
        fisica por la interpenetracion. A partir de aqui viaja con el vaso
        (`Elemento.contenido`)."""
        x, y, z = p.getBasePositionAndOrientation(vaso.body_id)[0]
        base_vaso = z - vaso.altura_mm / 2000
        n = len(vaso.contenido)
        p.changeDynamics(moneda.body_id, -1, mass=0)
        p.setCollisionFilterGroupMask(moneda.body_id, -1, 0, 0)
        # Pila levemente desordenada, como caen de verdad por el embudo.
        dx = 0.008 * ((n * 37) % 5 - 2) / 2
        dy = 0.008 * ((n * 53) % 5 - 2) / 2
        p.resetBasePositionAndOrientation(
            moneda.body_id, [x + dx, y + dy, base_vaso + 0.004 + n * 0.0022], [0, 0, 0, 1]
        )
        moneda.activo = False
        vaso.contenido.append(moneda.body_id)

    def guardar_en_tubo(self, moneda: Elemento, denominacion: int | str, posicion_en_pila: int) -> None:
        """La moneda aceptada sale de la cinta por el selector y queda
        apilada en el tubo de su denominacion (estatica, sin colision, igual
        que dentro del vaso: el tubo no es un cuerpo fisico)."""
        x, y, z = posicion_tubo(denominacion)
        p.changeDynamics(moneda.body_id, -1, mass=0)
        p.setCollisionFilterGroupMask(moneda.body_id, -1, 0, 0)
        p.resetBasePositionAndOrientation(
            moneda.body_id, [x, y, z + 0.002 + posicion_en_pila * GROSOR_PILA_M], [0, 0, 0, 1]
        )
        moneda.activo = False

    def enviar_a_rechazo_final(self, elemento: Elemento, posicion_en_pila: int) -> None:
        """La compuerta de desvio de la descarga (en reposo) manda la pieza a
        la bandeja de rechazo en vez de al almacen."""
        x, y, z = posicion_rechazo_final()
        p.changeDynamics(elemento.body_id, -1, mass=0)
        p.setCollisionFilterGroupMask(elemento.body_id, -1, 0, 0)
        dx = 0.018 * ((posicion_en_pila % 3) - 1)
        p.resetBasePositionAndOrientation(elemento.body_id, [x + dx, y, z + 0.004 * (posicion_en_pila // 3)],
                                          [0, 0, 0, 1])
        elemento.activo = False

    def reacomodar_tubo(self, monedas: list[Elemento], denominacion: int) -> None:
        """Tras abrir la compuerta y soltar un lote, las que quedan bajan."""
        x, y, z = posicion_tubo(denominacion)
        for i, moneda in enumerate(monedas):
            p.resetBasePositionAndOrientation(moneda.body_id, [x, y, z + 0.002 + i * GROSOR_PILA_M], [0, 0, 0, 1])

    def crear_mano_en_carga(self) -> int:
        """Una mano apoyada un instante en la casilla de carga (sabotaje del
        punto 1): la ve el infrarrojo de presencia, pero se retira antes del
        avance, asi que la casilla viaja registrada como ocupada y vacia."""
        x, y, z = self.posicion_estacion_monedas(ESTACION_PRESENCIA_MONEDAS)
        # Mas baja que el origen del rayo de presencia (5 cm): si el rayo
        # naciera DENTRO de la mano, PyBullet no reportaria el choque.
        mitad = [0.015, 0.018, 0.015]
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=mitad)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=mitad, rgbaColor=(0.9, 0.7, 0.55, 1.0))
        return p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col, baseVisualShapeIndex=vis,
                                 basePosition=[x, y, z + mitad[2]])

    def colocar_tapa(self, vaso: Elemento) -> None:
        """Tapa visual (sin colision, para no ocupar la franja de borde de
        la camara de vasos ni la cortina) apoyada sobre la boca del vaso.
        Del mismo diametro que la boca (78 mm): con casillas de 80 mm, dos
        vasos tapados vecinos no se tocan."""
        x, y, z = p.getBasePositionAndOrientation(vaso.body_id)[0]
        vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.039, length=0.004, rgbaColor=(0.95, 0.55, 0.15, 1.0))
        tapa = p.createMultiBody(
            baseMass=0,
            baseCollisionShapeIndex=-1,
            baseVisualShapeIndex=vis,
            basePosition=[x, y, z + vaso.altura_mm / 2000 + 0.002],
        )
        vaso.contenido.append(tapa)
        vaso.tapado = True

    # ------------------------------------------------------------------
    # sabotaje (seccion 11: "para las pruebas de sabotaje, un script
    # inyecta un cuerpo intruso en la escena a mitad de linea, retira un
    # vaso o lo sustituye por un cilindro de otra altura")
    # ------------------------------------------------------------------

    def retirar_vaso(self, elemento: Elemento) -> None:
        """Saca fisicamente un vaso de la escena, como si alguien lo
        hubiera tomado de la linea a mitad de proceso."""
        p.removeBody(elemento.body_id)
        for cuerpo in elemento.contenido:
            p.removeBody(cuerpo)
        elemento.contenido.clear()
        elemento.tapado = False
        elemento.objeto_adentro = False
        elemento.activo = False
        if elemento in self.elementos_vasos:
            self.elementos_vasos.remove(elemento)

    def sustituir_por_vaso_igual(self, elemento: Elemento, nuevo_marcador: int) -> None:
        """Sabotaje del profesor: se lleva el vaso (con lo que tenga adentro) y
        pone OTRO vaso identico y vacio en la misma casilla. Las barreras no lo
        notan (misma altura); solo el marcador ArUco es distinto."""
        pos = p.getBasePositionAndOrientation(elemento.body_id)[0]
        for cuerpo in elemento.contenido:
            p.removeBody(cuerpo)
        elemento.contenido.clear()
        elemento.tapado = False
        elemento.objeto_adentro = False
        p.removeBody(elemento.body_id)
        radio, altura = 0.031, elemento.altura_mm / 1000
        col = p.createCollisionShape(p.GEOM_CYLINDER, radius=radio, height=altura)
        vis = p.createVisualShape(p.GEOM_CYLINDER, radius=radio, length=altura, rgbaColor=(0.85, 0.9, 0.95, 0.55))
        elemento.body_id = p.createMultiBody(baseMass=0.04, baseCollisionShapeIndex=col,
                                             baseVisualShapeIndex=vis, basePosition=list(pos))
        elemento.marcador = nuevo_marcador

    def sustituir_vaso(self, elemento: Elemento, *, altura_mm: float = 35.0) -> None:
        """Cambia el vaso por "una figura distinta" (seccion 2): un
        cilindro de otra altura en la misma casilla. Se modifica el mismo
        `Elemento` en su lugar (cambia `body_id`, conserva la identidad) para
        que quien lo este siguiendo no pierda la pista; es la estacion de
        tapa la que tiene que darse cuenta con sus barreras, no el
        orquestador. Con la altura por defecto (35 mm) la barrera de media
        altura (45 mm) queda libre y la re-verificacion lo marca invalido."""
        pos = p.getBasePositionAndOrientation(elemento.body_id)[0]
        base = pos[2] - elemento.altura_mm / 2000
        p.removeBody(elemento.body_id)
        for cuerpo in elemento.contenido:
            p.removeBody(cuerpo)
        elemento.contenido.clear()
        elemento.tapado = False
        elemento.objeto_adentro = False
        altura = altura_mm / 1000
        col = p.createCollisionShape(p.GEOM_CYLINDER, radius=0.028, height=altura)
        vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.028, length=altura, rgbaColor=(0.55, 0.3, 0.75, 1.0))
        elemento.body_id = p.createMultiBody(
            baseMass=0.05,
            baseCollisionShapeIndex=col,
            baseVisualShapeIndex=vis,
            basePosition=[pos[0], pos[1], base + altura / 2],
        )
        elemento.altura_mm = altura_mm
        elemento.masa_g = 50.0  # la figura pesa distinto que un vaso

    def crear_intruso(
        self, *, casilla_vasos: float, altura_vaso_mm: float = 90.0, altura_mano_m: float | None = None
    ) -> int:
        """Una mano con antebrazo que entra desde el lado del operador (-y)
        por encima de los vasos, para disparar la cortina de seguridad (paso
        14 de la seccion 5). No es un `Elemento` de la linea: no lo cuenta
        ninguna estacion, solo lo ve la cortina. Queda quieta en el aire
        (masa 0: alguien la sostiene). `casilla_vasos` acepta valores no
        enteros (p. ej. 2.5) para ubicarla a mitad de camino entre dos
        estaciones, en vez de justo encima de una -- si coincide con el
        origen de un rayo de sensor, el rayo puede nacer dentro del cuerpo
        y PyBullet no reporta ese choque."""
        x, y, z = self.posicion_estacion_vasos(casilla_vasos)
        # 10 cm de largo hacia afuera, 4 cm de ancho y de grueso. Por defecto
        # 1 a 5 cm por encima del borde del vaso; `altura_mano_m` la pone a
        # otra altura (por ejemplo a media altura, agarrando un vaso).
        mitad = [0.02, 0.05, 0.02]
        zc = altura_mano_m if altura_mano_m is not None else altura_vaso_mm / 1000 + 0.03
        centro = [x, y - 0.06, z + zc]
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=mitad)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=mitad, rgbaColor=(0.9, 0.7, 0.55, 1.0))
        return p.createMultiBody(baseMass=0, baseCollisionShapeIndex=col, baseVisualShapeIndex=vis,
                                 basePosition=centro)

    def quitar_intruso(self, body_id: int) -> None:
        p.removeBody(body_id)

    # ------------------------------------------------------------------
    # avance indexado (seccion 11: interpolacion + pausa, como el motor
    # paso a paso real en modo avanzar y detener)
    # ------------------------------------------------------------------

    def _avanzar_lista(
        self,
        elementos: list[Elemento],
        posicion_de: Callable[[int], tuple[float, float, float]],
        num_estaciones: int,
        pasos_avance: int = PASOS_AVANCE_CASILLA,
        pasos_pausa: int = PASOS_PAUSA_CASILLA,
    ) -> None:
        activos = [e for e in elementos if e.activo and e.casilla < num_estaciones - 1]
        if not activos:
            self.step(pasos_avance + pasos_pausa)
            return

        origenes = {e.body_id: p.getBasePositionAndOrientation(e.body_id)[0] for e in activos}
        destinos = {}
        for e in activos:
            origen_estacion = posicion_de(e.casilla)
            destino_estacion = posicion_de(e.casilla + 1)
            delta_z = origenes[e.body_id][2] - origen_estacion[2]
            destinos[e.body_id] = (
                destino_estacion[0],
                destino_estacion[1],
                destino_estacion[2] + delta_z,
            )

        # Lo que viaja dentro de cada vaso (monedas, tapa) se mueve con el
        # mismo desplazamiento que su vaso.
        origenes_contenido = {
            c: p.getBasePositionAndOrientation(c)[0] for e in activos for c in e.contenido
        }

        for paso in range(1, pasos_avance + 1):
            t = paso / pasos_avance
            for e in activos:
                nueva_pos = _interpolar(origenes[e.body_id], destinos[e.body_id], t)
                orn = p.getBasePositionAndOrientation(e.body_id)[1]
                p.resetBasePositionAndOrientation(e.body_id, nueva_pos, orn)
                delta = [n - o for n, o in zip(nueva_pos, origenes[e.body_id])]
                for c in e.contenido:
                    pos_c = [o + d for o, d in zip(origenes_contenido[c], delta)]
                    p.resetBasePositionAndOrientation(c, pos_c, p.getBasePositionAndOrientation(c)[1])
            self._paso_fisica()

        for e in activos:
            e.casilla += 1

        self.step(pasos_pausa)

    def avanzar_casilla_monedas(self) -> None:
        self._avanzar_lista(self.elementos_monedas, self.posicion_estacion_monedas, NUM_ESTACIONES_MONEDAS,
                            self._pasos["avance_monedas"], self._pasos["pausa_monedas"])

    def avanzar_casilla_vasos(self) -> None:
        self._avanzar_lista(self.elementos_vasos, self.posicion_estacion_vasos, NUM_ESTACIONES_VASOS,
                            self._pasos["avance_vasos"], self._pasos["pausa_vasos"])

    # ------------------------------------------------------------------
    # empujador de descarga de vasos (seccion 5, paso 13)
    # ------------------------------------------------------------------

    def _animar_junta(self, body_id: int, indice_junta: int, pasos_ida: int = PASOS_SERVO,
                      pasos_vuelta: int = PASOS_SERVO) -> None:
        p.setJointMotorControl2(body_id, indice_junta, p.POSITION_CONTROL, targetPosition=1.45, force=5)
        for _ in range(pasos_ida):
            self._paso_fisica()
        p.setJointMotorControl2(body_id, indice_junta, p.POSITION_CONTROL, targetPosition=0.0, force=5)
        for _ in range(pasos_vuelta):
            self._paso_fisica()

    def activar_empujador_vasos(self, elemento: Elemento, destino: Destino) -> None:
        """Anima el empujador de la cinta de vasos y saca el vaso hacia la
        canaleta de entrega o la bandeja de rechazo (seccion 5, paso 13)."""
        x, y0, z = self.posicion_estacion_vasos(ESTACION_DESCARGA_VASOS)

        self._animar_junta(self.id_cinta_vasos, self._junta_empujador_vasos,
                           self._pasos["empujador"], self._pasos["empujador"])

        pos_antes, orn = p.getBasePositionAndOrientation(elemento.body_id)
        # Se deja estatico, para que la fisica no lo tumbe y el contenido,
        # que es estatico, no quede flotando fuera. Entrega: de lado, colgado
        # del reborde al inicio de la canaleta. Rechazo: no hay otro
        # empujador; la cinta lo deja caer por su extremo a la bandeja.
        if destino == "entrega":
            pos_despues = [x, y0 - 0.10, z + elemento.altura_mm / 2000 + 0.002]
        else:
            xb, yb, zb = posicion_bandeja_rechazo_vasos()
            pos_despues = [xb, yb, zb + elemento.altura_mm / 2000]
        p.resetBasePositionAndOrientation(elemento.body_id, pos_despues, orn)
        p.changeDynamics(elemento.body_id, -1, mass=0)
        delta = [a - b for a, b in zip(pos_despues, pos_antes)]
        for c in elemento.contenido:
            pos_c = [o + d for o, d in zip(p.getBasePositionAndOrientation(c)[0], delta)]
            p.resetBasePositionAndOrientation(c, pos_c, p.getBasePositionAndOrientation(c)[1])

        elemento.activo = False

    # ------------------------------------------------------------------

    def step(self, pasos: int = 1) -> None:
        for _ in range(pasos):
            self._paso_fisica()

    def cerrar(self) -> None:
        if p.isConnected(self.cliente):      # idempotente: el supervisor puede cerrar dos veces
            p.disconnect(self.cliente)
