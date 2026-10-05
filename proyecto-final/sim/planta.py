"""Planta completa en simulacion: cinta de monedas + cinta de vasos
funcionando JUNTAS, paso a paso (docs/especificacion.md, seccion 5, pasos 1 a 14).

Es LA simulacion de la linea: las dos cintas, el almacen, la canaleta y el
carro, conectados como en la linea real:

- Lo que la cinta de monedas acepta NO va directo al vaso: en la estacion
  7 un selector giratorio la manda al tubo de SU denominacion (almacen,
  control/almacen.py). Reglas del grupo: ninguna moneda aceptada se
  descarta, y cada vaso lleva una sola denominacion.
- Cuando un tubo junta un lote completo (`monedas_por_vaso`), se abre su
  compuerta y el lote entero cae por la tolva al vaso de la estacion de
  llenado -- solo si la camara de vasos confirma, en ese instante,
  que es un vaso (media altura cortada, borde libre). Despues el vaso
  lleno avanza: tapa (re-verificacion), prensa y descarga.
- Si lo que hay en llenado no es un vaso valido (lo retiraron, lo
  cambiaron por una figura), no se suelta nada: las monedas siguen
  guardadas en su tubo y la cinta de vasos salta a la siguiente casilla
  (paso 10: "no hay paro de linea, solo un salto de casilla").
- Si la cortina de seguridad ve algo mas alto que un vaso (una mano), la
  cinta de vasos se congela pero la de monedas sigue (paso 14).

El avance es por "ticks": cada llamada a `paso()` es un avance de la cinta
de monedas (y, si toca, uno de la de vasos), con todas las lecturas de
sensores y decisiones de ese instante. Asi el supervisor (`app/supervisor.py`)
puede intercalar entre ticks la lectura de ordenes del dashboard (pausar,
paro, sabotajes) y la escritura en SQLite, sin que esta clase sepa que
existe una base de datos. Lo que pasa en cada tick se reporta como una
lista de eventos (diccionarios con el mismo estilo `src`/`ev` del
protocolo serial de la seccion 10.1), que es exactamente lo que el backend
real va a recibir del ESP32 en la fase 8.

El "id de registro" de un elemento NO es su `body_id` de PyBullet sino un contador propio (1, 2, 3... en orden de
entrada): aqui si se borran cuerpos (retirar o cambiar un vaso) y PyBullet
reutiliza esos ids -- ver `Elemento.id_registro`. Los vasos tambien llevan
su propio contador, que es el id con que quedan en la tabla `vasos`.
"""

from __future__ import annotations

from collections import deque

from control import reglas
from control.almacen import OTRAS, AlmacenDenominaciones, MonedaAlmacenada
from control.carrusel import AGUJERO, CARGA, Carrusel
from control.embalaje import EmbalajeVasos
from control.hal.backend_sim import EstacionBackendSim
from control.linea import Destino, LineaMonedas
from control.monedas import buscar_por_clase

# Cubeta de rechazo final en la descarga, E4 (ver `_a_rechazo`).
# Una sola bandeja de rechazo de monedas (grupo, 2026-09-25).
RECHAZO_FINAL = Destino.RECHAZO
from control.registro import EstadoVaso
from sim.carga_escenarios import Escenario, EspecificacionElemento
from sim.mundo import (
    ANGULO_AGUJERO_CARRUSEL,
    ANGULO_CARGA_CARRUSEL,
    POSICIONES_CARRUSEL,
    ESTACION_DESCARGA_MONEDAS,
    ESTACION_DESCARGA_VASOS,
    ESTACION_LLENADO_VASOS,
    ESTACION_MATERIAL_MONEDAS,
    ESTACION_PRENSA_VASOS,
    ESTACION_TAPA_VASOS,
    ESTACION_VERIFICACION_VASOS,
    ESTACION_VISION_MONEDAS,
    NUM_ESTACIONES_MONEDAS,
    NUM_ESTACIONES_VASOS,
    Elemento,
    EscenaEstacion,
)

# Nombres cortos de cada estacion para los eventos (`src`), en el mismo
# estilo del protocolo de la seccion 10.1 ("e2", "e4", "vasos"...).
NOMBRES_ESTACIONES_MONEDAS = ("e1", "e2", "e3", "e4")
ETIQUETAS_ESTACIONES_MONEDAS = ("Presencia", "Material", "Vision", "Descarga")
ETIQUETAS_ESTACIONES_VASOS = ("Verificacion", "Llenado", "Tapa", "Prensa", "Descarga")



def _crear_desde_especificacion(escena: EscenaEstacion, especificacion: EspecificacionElemento) -> Elemento:
    """El cuerpo de PyBullet de un elemento del escenario (moneda, boton,
    bloque), con su verdad de terreno (clase, material, medidas)."""
    elemento = _crear_cuerpo(escena, especificacion)
    elemento.apariencia = especificacion.apariencia
    return elemento


def _crear_cuerpo(escena: EscenaEstacion, especificacion: EspecificacionElemento) -> Elemento:
    if especificacion.tipo == "moneda":
        return escena.crear_elemento(
            tipo="moneda",
            clase_real=especificacion.clase_real,
            metal=especificacion.metal,
            diametro_mm=especificacion.diametro_mm,
            masa_g=especificacion.masa_g,
            circularidad=especificacion.circularidad,
            contornos_internos=especificacion.contornos_internos,
        )
    if especificacion.tipo == "bloque":
        kwargs = {"metal": especificacion.metal}
        if especificacion.circularidad is not None:
            kwargs["circularidad"] = especificacion.circularidad
        return escena.crear_bloque(**kwargs)
    return escena.crear_elemento(
        tipo=especificacion.tipo,
        metal=especificacion.metal,
        diametro_mm=especificacion.diametro_mm,
        circularidad=especificacion.circularidad,
        contornos_internos=especificacion.contornos_internos,
    )

def opciones_desde_config(parametros: dict) -> dict:
    """Argumentos de `PlantaSimulada` que salen de config/parametros.yaml
    (para no repetirlos en el supervisor, la demo grabada y las pruebas)."""
    p = parametros["planta"]
    return {
        "monedas_por_vaso": p["monedas_por_vaso"],
        "altura_figura_sabotaje_mm": p["altura_figura_sabotaje_mm"],
        "capacidad_tubo": p["capacidad_tubo"],
        "lecturas_por_decision": p["lecturas_por_decision"],
        "fotos_por_moneda": p["fotos_por_moneda"],
        "capacidad_canaleta": parametros["canaleta"]["capacidad_vasos"],
        "carro_retira_cada_ticks": parametros.get("simulacion", {}).get("carro_retira_cada_ticks", 6),
        # Punto 14: el carro con fisica real (sim/vehiculo_sim.py) en vez del
        # "carro de reemplazo". Cada tick de la planta es un ciclo real de la
        # cinta de monedas: el carro avanza ese tiempo.
        "carro_fisico": parametros.get("simulacion", {}).get("carro") == "fisico",
        "parametros": parametros,
        "segundos_por_tick": (parametros["tiempos_ms"]["avance_casilla_monedas"]
                              + parametros["tiempos_ms"]["pausa_casilla_monedas"]) / 1000,
    }


class PlantaSimulada:
    def __init__(
        self,
        escena: EscenaEstacion,
        backend: EstacionBackendSim,
        linea: LineaMonedas,
        embalaje: EmbalajeVasos,
        escenario: Escenario,
        *,
        monedas_por_vaso: int = 5,
        altura_figura_sabotaje_mm: float = 35.0,
        capacidad_tubo: int = 25,
        lecturas_por_decision: int = 3,
        fotos_por_moneda: int = 2,
        capacidad_canaleta: int = 4,
        carro_retira_cada_ticks: int = 6,
        carro_fisico: bool = False,
        parametros: dict | None = None,
        segundos_por_tick: float = 1.6,
        errores_carro: bool = False,
        semilla_carro: int | None = None,
    ):
        self.escena = escena
        self.backend = backend
        self.linea = linea
        self.embalaje = embalaje
        self.escenario = escenario
        self.monedas_por_vaso = monedas_por_vaso
        self.altura_figura_sabotaje_mm = altura_figura_sabotaje_mm
        # Cada estacion lee su sensor varias veces durante la pausa de la
        # cinta y decide por mayoria (config: planta.lecturas_por_decision).
        # Con un error de p por lectura, fallar la decision exige fallar la
        # mayoria: con 3 lecturas, ~3p^2 (0,5 % -> 0,0075 %).
        self.lecturas_por_decision = max(1, lecturas_por_decision)
        # Fotos por moneda en E3 (aprobado: 2), combinadas con
        # control.reglas.combinar_fotos.
        self.fotos_por_moneda = max(1, fotos_por_moneda)
        # Verdad del escenario (para contar errores de filtrado) y errores.
        self._esperado: dict[int, str] = {}
        # clase_equivocada: moneda colombiana aceptada como OTRA clase (iria
        # al tubo/vaso de otra denominacion): el error mas caro.
        self.errores_filtrado: dict[str, list[int]] = {"falsos_rechazos": [], "falsas_aceptaciones": [],
                                                       "clase_equivocada": []}

        self._pendientes = deque(escenario.elementos)
        # Almacen por denominacion: la contabilidad (control/) y los cuerpos
        # que estan fisicamente en cada tubo (para moverlos al vaso).
        self.almacen = AlmacenDenominaciones(capacidad=capacidad_tubo)
        self._cuerpos_en_tubo: dict[int | str, list[Elemento]] = {
            d: [] for d in (*self.almacen.denominaciones, OTRAS)
        }
        # Fin de turno: embalar tambien los tubos que no completaron lote.
        self.embalar_parciales = False
        # Casillas registradas como ocupadas pero sin cuerpo (una mano que
        # se puso y se quito en la carga): id -> casilla actual.
        self._fantasmas: dict[int, int] = {}
        # Lectura del capacitivo (bajo la casilla E1) de cada registro: se usa
        # un paso despues, en E2, junto con el inductivo.
        self._capacitivo_e1: dict[int, bool] = {}
        self._mano_pendiente = False
        self._tipo_real: dict[int, str] = {}
        # Id de registro secuencial (1, 2, 3...) en el orden de entrada a la
        # cinta, incluidas las casillas vacias. Ver Elemento.id_registro.
        self._id_elemento_siguiente = 1
        # Orden de entrada de cada elemento (id de registro) y el cuerpo
        # correspondiente (None para una casilla vacia).
        self.orden_ids: list[int] = []
        self._elementos: dict[int, Elemento | None] = {}
        # Destino final de cada elemento, cuando ya salio de la cinta.
        self.destinos_finales: dict[int, str] = {}
        # Lo que se ve fuera de la cinta: elementos en cada canaleta de
        # rechazo (para que el visor 3D los apile donde cayeron).
        self.salidas: dict[str, list[dict]] = {Destino.RECHAZO: []}

        # Vasos en la cinta: id propio -> (Elemento o None si lo retiraron,
        # casilla). Se sigue la casilla aqui y no solo en `Elemento.casilla`
        # porque un vaso retirado ya no tiene cuerpo, pero su registro sigue
        # viajando: la estacion de tapa es la que tiene que darse cuenta de
        # que no esta, leyendo sus sensores.
        self._vasos: dict[int, list] = {}
        self._id_vaso_siguiente = 1
        self.vasos_finales: dict[int, str] = {}
        self.vasos_salida: list[dict] = []

        self._vaso_pide_avance = False
        self.desfases = {"monedas": 0, "vasos": 0}
        self._moneda_en_espera: tuple[Elemento, int] | None = None
        self._intruso: int | None = None
        # Sabotaje "mano que saca un vaso": [cuerpo de la mano, ticks que le
        # quedan, casilla]. La mano se va sola a los pocos ticks.
        self._mano_temporal: list | None = None
        # Alarmas para el operador (se avisan una vez, al aparecer).
        self._alarmas: set[str] = set()
        self._ticks_sin_vaso = 0
        # Canaleta de entrega: fila de vasos colgados (capacidad limitada).
        # Mientras el carro no se simule (puntos 13-14), un "carro de
        # reemplazo" se lleva el primero cada `carro_retira_cada_ticks`.
        self.capacidad_canaleta = capacidad_canaleta
        self.carro_retira_cada_ticks = carro_retira_cada_ticks
        self.canaleta: deque[int] = deque()
        self._vaso_esperando_canaleta: int | None = None
        self._ticks_carro = 0
        # Punto 13: vaso soltado a la cuna que el infrarrojo todavia no confirma.
        self._carga_sin_confirmar: int | None = None
        # Punto 14: carro con fisica real (su propio mundo de PyBullet).
        self.carro = None
        self.segundos_por_tick = segundos_por_tick
        self._vaso_en_carro: int | None = None
        self._t_en_meta = 0.0
        self._carro_anunciado = False
        if parametros is None:
            from app.configuracion import cargar_parametros
            parametros = cargar_parametros()

        # Carrusel del almacen con su TIEMPO REAL (usuario, 2026-09-28: "la
        # moneda pasa sin que se espere a que de la vuelta"). Antes la moneda
        # se guardaba en su tubo en el mismo instante en que llegaba a E4, sin
        # girar nada. Ahora la planta lleva un reloj en ms (cada tick es un
        # ciclo de la cinta de monedas: avance + pausa) y el carrusel
        # (control/carrusel.py) dice cuando llega cada tubo:
        #  - el giro se pide en cuanto la vision ACEPTA una moneda (gira
        #    mientras la moneda viaja de E3 a E4);
        #  - en E4 la moneda solo cae si su tubo ya esta QUIETO bajo la carga;
        #    si no, espera en la descarga y la cinta de monedas se detiene;
        #  - un lote se suelta con el tubo quieto sobre el agujero, el
        #    obturador abre y cierra (`compuerta_tubo`) y recien ahi el
        #    carrusel queda libre para la siguiente moneda;
        #  - una moneda guardada OCUPA el carrusel mientras cae por el canal
        #    hasta el fondo de su tubo (`caida_moneda_tubo`): el giro hacia el
        #    tubo de la siguiente sale recien cuando termino de caer (revision
        #    visual 2026-09-29: salia en el mismo instante y la moneda caia
        #    fuera de la boca). Lo mismo el obturador con un lote.
        t = parametros["tiempos_ms"]
        self._ciclo_ms = t["avance_casilla_monedas"] + t["pausa_casilla_monedas"]
        self._t_avance_ms = t["avance_casilla_monedas"]
        # La vision decide dentro de la pausa en E3: fotos + inferencia + el
        # veredicto por serial. Desde ahi el PC ya sabe a que tubo ir.
        self._t_acepta_ms = (t["avance_casilla_monedas"] + self.fotos_por_moneda * t["vision_captura_inferencia"]
                             + t.get("serial_ida_vuelta", 0))
        self._t_compuerta_ms = t["compuerta_tubo"]
        self._t_caida_tubo_ms = t["caida_moneda_tubo"]
        self._t_avance_vasos_ms = t["avance_casilla_vasos"]
        self.carrusel = Carrusel(POSICIONES_CARRUSEL, t["carrusel_giro"], ANGULO_CARGA_CARRUSEL,
                                 ANGULO_AGUJERO_CARRUSEL)
        # Monedas aceptadas por la vision que todavia no cayeron a su tubo, en
        # orden de llegada: el carrusel atiende siempre a la primera (nunca se
        # va al tubo de la segunda mientras la primera espera en E4).
        self._cola_carga: deque[int] = deque()
        # Lote en camino al agujero: {"denominacion", "vaso", "llegada"}.
        self._embalado: dict | None = None
        # Hasta cuando el obturador esta abierto (el carrusel no se mueve y
        # el vaso de llenado no avanza).
        self._carrusel_ocupado_hasta = 0.0
        # Instante en que la cinta de vasos queda quieta tras su ultimo avance
        # (el obturador no se abre sobre un vaso que todavia viene llegando).
        self._vasos_quietos_ms = 0.0
        self._motivo_espera: str | None = None
        # Para verificar (pruebas, docs): cada moneda guardada con el tubo que
        # habia DE VERDAD bajo la carga en ese instante, y cada espera.
        self.guardados: list[dict] = []
        self.esperas_carrusel: list[dict] = []
        if carro_fisico:
            from sim.vehiculo_sim import SimCarro
            self.carro = SimCarro(parametros, errores=errores_carro, semilla=semilla_carro)
            self._espera_meta = parametros["vehiculo"]["espera_descarga_meta_s"]
            # Punto 15: radio (ESP-NOW) entre el carro y la estacion, con
            # mensajes numerados que el carro guarda hasta su ack y latido en
            # los dos sentidos. `radio_carro_conectada` la corta el sabotaje.
            from control import protocolo as pr
            cp = parametros.get("protocolo", {})
            self.radio_carro_conectada = True
            self._emisor_carro = pr.Emisor(reintento_ms=cp.get("carro_reintento_ms", 500), reintentos=None,
                                           cola_max=cp.get("carro_cola_max", 32))
            self._receptor_estacion = pr.Receptor()
            latido = (cp.get("carro_latido_ms", 250), cp.get("carro_enlace_perdido_ms", 1000))
            self._oye_estacion = pr.Latido(*latido)   # lo que la estacion oye del carro
            self._oye_carro = pr.Latido(*latido)      # lo que el carro oye de la estacion
            # Lo que la estacion sabe del carro (solo por la radio).
            self._estado_carro = {"fresco": False, "en_muelle": False, "cuna": None}
            self._t_ms = 0
            self._ticks_soltado = 0
            self._enlace_perdido_alguna_vez = False
        # Objeto en la casilla de carga que el infrarrojo no vio con la cinta
        # vacia: se vuelve a leer en la pausa siguiente.
        self._en_carga = None
        # Sabotaje: el proximo vaso que ponga el operador trae algo adentro.
        self._proximo_vaso_con_objeto = False
        self._eventos: list[dict] = []
        # Lo que cada estacion LEYO en este tick, en el momento de decidir.
        # No es lo mismo que la lectura "en vivo" de estado()["sensores"]:
        # esa se toma al final del tick, cuando la cinta ya avanzo (por
        # ejemplo, E1 ya quedo vacia porque su elemento paso a E2). Esta es
        # la que el ESP32 mandaria por serial.
        self._lecturas: dict[str, bool] = {}
        self.ticks = 0
        self.terminado = False

        # Arranque: un vaso vacio pasa la verificacion y queda en la
        # estacion de llenado, y otro entra a verificacion detras de el.
        self._colocar_vaso_nuevo()
        self._avanzar_vasos(forzado=True)
        # Lo que paso durante el arranque, para quien quiera persistirlo
        # (el supervisor); los ticks siguientes lo devuelven `paso()`.
        self.eventos_arranque = list(self._eventos)

    # ------------------------------------------------------------------
    # lectura de sensores con voto de mayoria
    # ------------------------------------------------------------------

    def _votar(self, leer) -> bool:
        n = self.lecturas_por_decision
        return sum(bool(leer()) for _ in range(n)) * 2 > n

    def _votar_zona(self, zona) -> tuple[bool, bool, bool]:
        """Camara de vasos en una estacion: varios cuadros votados de la
        presencia y de las dos franjas de medida (media altura, borde)."""
        return (self._votar(zona.presencia.leer), self._votar(zona.media_altura.leer),
                self._votar(zona.borde.leer))

    def _a_rechazo(self, elemento: Elemento | None, id_registro: int, motivo: str) -> None:
        """Descarga (E4) con la compuerta de desvio en reposo: la pieza cae a
        la UNICA bandeja de rechazo. Es lo que pasa con todo lo que no es una
        moneda registrada y aceptada: "filtro total" (grupo, 2026-09-25).
        Tampoco se guarda en "otras" algo que ningun sensor reconocio (no se
        sabria si se guarda una moneda o basura). La causa queda registrada:
        asi se demuestra cada filtro por separado."""
        if elemento is not None:
            self.escena.enviar_a_rechazo_final(elemento, len(self.salidas[Destino.RECHAZO]))
        self._finalizar_elemento(id_registro, Destino.RECHAZO, motivo=motivo)
        self._evento("e4", "rechazo", casilla=id_registro, motivo=motivo,
                     causa=self.linea.registro.obtener(id_registro).causa)

    # ------------------------------------------------------------------
    # eventos
    # ------------------------------------------------------------------

    def _evento(self, src: str, ev: str, **datos) -> None:
        self._eventos.append({"src": src, "ev": ev, "tick": self.ticks, **datos})

    # ------------------------------------------------------------------
    # cinta de vasos
    # ------------------------------------------------------------------

    def _vaso_en(self, casilla: int) -> int | None:
        for id_vaso, (_, c) in self._vasos.items():
            if c == casilla:
                return id_vaso
        return None

    def _colocar_vaso_nuevo(self) -> None:
        """El operador pone un vaso vacio en la casilla de verificacion."""
        if self._vaso_en(ESTACION_VERIFICACION_VASOS) is not None:
            return
        id_vaso = self._id_vaso_siguiente
        self._id_vaso_siguiente += 1
        # Vasos personalizados con marcador ArUco: el numero es el del vaso.
        elemento = self.escena.crear_vaso(casilla=ESTACION_VERIFICACION_VASOS, marcador=100 + id_vaso)
        if self._proximo_vaso_con_objeto:
            elemento.objeto_adentro = True
            self._proximo_vaso_con_objeto = False
        self._vasos[id_vaso] = [elemento, ESTACION_VERIFICACION_VASOS]
        self._evento("vasos", "vaso_nuevo", vaso=id_vaso)

    def _revisar_cortina(self) -> bool:
        """Paso 14. Lee la cortina y congela/descongela la zona de tapa,
        prensa y empujador. Devuelve True si esta bloqueada. Se llama en
        cada tick (no solo al mover vasos) para que el estado que ve el
        dashboard sea el de este instante."""
        # Dos fuentes (usuario, 2026-09-26): el VL53L0X en tapa y prensa, y la
        # camara de vasos en la zona por donde cae el lote al vaso de llenado.
        por_sensor = self._votar(self.backend.sensor_cortina.leer)
        por_camara = self._votar(self.backend.intrusion_llenado.leer)
        bloqueada = por_sensor or por_camara
        self._lecturas["cortina"] = por_sensor
        self._lecturas["intrusion_llenado"] = por_camara
        if bloqueada:
            if not self.embalaje.cortina_activa:
                self.embalaje.activar_cortina()
                # Usuario (2026-09-26): la prensa no se queda congelada donde
                # iba (podria quedar apretando la mano): SUBE y se detiene
                # arriba. Tapa y empujador si quedan congelados; el almacen no
                # suelta ningun lote.
                self.backend.prensa.subir()
                self._evento("seguridad", "cortina", activa=True, prensa="arriba",
                             fuente="camara_llenado" if por_camara and not por_sensor else "sensor")
            return True
        if self.embalaje.cortina_activa:
            self.embalaje.despejar_cortina()
            self._evento("seguridad", "cortina", activa=False)
            self._reverificar_tras_cortina()
        return False

    def _avanzar_vasos(self, *, forzado: bool = False) -> bool:
        """Un avance de la cinta de vasos con todas sus estaciones. Devuelve
        False si la cortina de seguridad lo impidio (la cinta de vasos se
        queda quieta; quien llama reintenta en el siguiente tick). Tampoco
        se mueve mientras el carrusel suelta un lote sobre el vaso de llenado
        (tubo en camino al agujero u obturador abierto)."""
        if self._revisar_cortina():
            return False
        if not self._vasos_libres_del_carrusel():
            return False
        if self._vaso_esperando_canaleta is not None:
            # Un vaso tapado espera en la descarga: si ya hay lugar en la
            # canaleta se empuja; si no, la cinta de vasos no se mueve.
            id_espera = self._vaso_esperando_canaleta
            self._estacion_descarga_vasos(id_espera, self._vasos[id_espera][0])
            if self._vaso_esperando_canaleta is not None:
                return False

        # Antes de mover: el vaso de llenado se cierra (ya no recibe mas
        # monedas en este ciclo) y el de la entrada pasa la verificacion
        # del paso 9 con la camara de vasos (franjas de esa estacion).
        id_llenado = self._vaso_en(ESTACION_LLENADO_VASOS)
        if id_llenado is not None:
            self.embalaje.cerrar_llenado(id_llenado)
            self._evento("vasos", "llenado_cerrado", vaso=id_llenado,
                         cantidad=self.embalaje.registro.obtener(id_llenado).cantidad_monedas)

        id_entrada = self._vaso_en(ESTACION_VERIFICACION_VASOS)
        if id_entrada is not None:
            presente, media, borde_bloqueado = self._votar_zona(self.backend.zona_verificacion)
            marcador = self._leer_marcador(ESTACION_VERIFICACION_VASOS)
            # Sensor que mira al interior: el vaso tiene que llegar vacio.
            objeto = presente and self._votar(self.backend.sensor_interior.leer)
            self._lecturas.update(verif_media=media, verif_borde=borde_bloqueado, sensor_interior=objeto)
            casilla = self.embalaje.verificar_antes_de_llenado(
                id_entrada, presente=presente, media_bloqueada=media, borde_libre=not borde_bloqueado,
                marcador=marcador, objeto_adentro=objeto,
            )
            self._evento("vasos", "verificacion", vaso=id_entrada, media=media, borde=borde_bloqueado,
                         marcador=marcador, objeto_adentro=objeto, estado=casilla.estado.value)
            if objeto:
                self._evento("vasos", "sabotaje_detectado", vaso=id_entrada, motivo="vaso_con_contenido",
                             estacion="verificacion")

        self.escena.avanzar_casilla_vasos()
        self._vasos_quietos_ms = self._t0() + self._t_avance_vasos_ms
        self._verificar_posicion("vasos")
        for datos in self._vasos.values():
            datos[1] += 1
        self._evento("vasos", "paso")

        for id_vaso in sorted(self._vasos, key=lambda i: -self._vasos[i][1]):
            elemento, casilla = self._vasos[id_vaso]
            if casilla == ESTACION_TAPA_VASOS:
                self._estacion_tapa(id_vaso, elemento)
            elif casilla == ESTACION_PRENSA_VASOS:
                self._estacion_prensa(id_vaso)
            elif casilla == ESTACION_DESCARGA_VASOS:
                self._estacion_descarga_vasos(id_vaso, elemento)

        if not forzado or self._pendientes:
            self._colocar_vaso_nuevo()
        return True

    def _estacion_tapa(self, id_vaso: int, elemento: Elemento | None) -> None:
        """Paso 11: se relee presencia y altura EN ESTE INSTANTE; no se
        confia en lo que dijo la verificacion de la entrada."""
        presente, media, borde_bloqueado = self._votar_zona(self.backend.zona_tapa)
        marcador = self._leer_marcador(ESTACION_TAPA_VASOS)
        self._lecturas.update(tapa_media=media, tapa_borde=borde_bloqueado)
        registro = self.embalaje.registro.obtener(id_vaso)
        estado_antes = registro.estado
        mismo = self.embalaje.es_el_mismo_vaso(registro, marcador)
        tapo = self.embalaje.tapar(
            id_vaso, presente=presente, media_bloqueada=media, borde_libre=not borde_bloqueado,
            marcador=marcador,
        )
        tapa_vista = None
        if tapo:
            # El escape suelta una tapa y la camara confirma que quedo sobre
            # la boca (no hace falta otro sensor). Si no la ve, se suelta otra
            # una vez; si tampoco, el vaso no sale como entregado sin tapa.
            for _ in range(2):
                if self.backend.dispensador_tapas.soltar_tapa() and elemento is not None and not elemento.tapado:
                    self.escena.colocar_tapa(elemento)
                tapa_vista = self._votar(lambda: self.backend.camara_vasos.leer_tapa(ESTACION_TAPA_VASOS))
                if tapa_vista:
                    break
            self._lecturas["camara_vasos_tapa"] = bool(tapa_vista)
            if not tapa_vista:
                self.embalaje.registro.obtener(id_vaso).degradar(EstadoVaso.INVALIDA)
                tapo = False
        estado = self.embalaje.registro.obtener(id_vaso).estado
        self._evento("vasos", "tapa", vaso=id_vaso, presente=presente, media=media,
                     borde=borde_bloqueado, marcador=marcador, tapado=tapo, tapa_vista=tapa_vista,
                     vacio=self.embalaje.registro.obtener(id_vaso).cantidad_monedas == 0,
                     estado=estado.value)
        if tapa_vista is False:
            self._evento("vasos", "tapa_no_confirmada", vaso=id_vaso)
        elif estado_antes in (EstadoVaso.LLENA, EstadoVaso.VALIDA) and estado == EstadoVaso.INVALIDA:
            motivo = ("retirado" if not presente else "vaso_cambiado" if not mismo else "figura_distinta")
            self._evento("vasos", "sabotaje_detectado", vaso=id_vaso, motivo=motivo, estacion="tapa")

    def _estacion_prensa(self, id_vaso: int) -> None:
        """Paso 12. La camara de vasos tambien ve esta casilla: antes de
        prensar se revisa que el vaso siga ahi, que sea el mismo y que tenga
        la tapa."""
        registro = self.embalaje.registro.obtener(id_vaso)
        presente, media, borde = self._votar_zona(self.backend.zona_prensa)
        marcador = self._leer_marcador(ESTACION_PRENSA_VASOS)
        self._lecturas.update(prensa_media=media, prensa_borde=borde)
        mismo = self.embalaje.es_el_mismo_vaso(registro, marcador)
        motivo = None
        if registro.estado in (EstadoVaso.TAPADA, EstadoVaso.VALIDA):
            if not presente:
                motivo = "retirado"
            elif not mismo:
                motivo = "vaso_cambiado"
            elif not media or borde:
                motivo = "figura_distinta"
            elif registro.estado == EstadoVaso.TAPADA and not self._votar(
                    lambda: self.backend.camara_vasos.leer_tapa(ESTACION_PRENSA_VASOS)):
                motivo = "sin_tapa"
        if motivo is not None:
            registro.degradar(EstadoVaso.INVALIDA)
            self._evento("vasos", "sabotaje_detectado", vaso=id_vaso, motivo=motivo, estacion="prensa")
            return
        if self.embalaje.prensar(id_vaso):
            self.backend.prensa.ciclo()
            self._evento("vasos", "prensa", vaso=id_vaso)

    def _zonas_camara_vasos(self) -> dict:
        return {ESTACION_VERIFICACION_VASOS: self.backend.zona_verificacion,
                ESTACION_LLENADO_VASOS: self.backend.zona_llenado,
                ESTACION_TAPA_VASOS: self.backend.zona_tapa,
                ESTACION_PRENSA_VASOS: self.backend.zona_prensa}

    def _vigilar_vasos(self) -> None:
        """Usuario (2026-09-26): la cortina es UN solo sensor a media altura;
        alguien puede sacar un vaso sin cruzarlo (por encima). Por eso la
        camara de vasos revisa en CADA tick que cada vaso registrado en sus
        4 casillas siga ahi, no solo cuando se despeja la cortina.

        Una sola lectura "no esta" no basta: revisar 4 casillas en cada tick
        junta muchas lecturas, y con el error normal de la camara (una
        sombra, un reflejo) tarde o temprano un vaso que SI esta daria "no
        esta". Si el primer voto dice que falta, se confirma en la MISMA
        pausa con un segundo voto de cuadros nuevos (~0,2 s mas). No se
        espera al tick siguiente: para entonces el vaso de prensa ya habria
        avanzado a la descarga, fuera de la vista de la camara, y se
        entregaria como si nada. Mientras la cortina esta activa no se revisa
        aqui: la mano esta adentro, y al despejarse se hace la revision
        completa (`_reverificar_tras_cortina`)."""
        if self.embalaje.cortina_activa:
            return
        zonas = self._zonas_camara_vasos()
        for id_vaso, (_, casilla) in list(self._vasos.items()):
            if casilla not in zonas:
                continue
            registro = self.embalaje.registro.obtener(id_vaso)
            if registro.estado in (EstadoVaso.INVALIDA, EstadoVaso.VACIA, EstadoVaso.RECHAZADA):
                continue
            presencia = zonas[casilla].presencia.leer
            if self._votar(presencia) or self._votar(presencia):
                continue
            registro.degradar(EstadoVaso.INVALIDA)
            self._evento("vasos", "sabotaje_detectado", vaso=id_vaso, motivo="retirado", estacion="camara",
                         casilla=casilla, monedas_retiradas=registro.cantidad_monedas)

    def _reverificar_tras_cortina(self) -> None:
        """Cuando se despeja la cortina, alguien pudo haber sacado o cambiado
        un vaso con la mano. Antes de seguir se revisan con la camara todos
        los vasos que ella ve (verificacion, llenado, tapa y prensa): el que
        falte, sea otro o sea una figura queda invalido y sale por rechazo;
        las monedas que tenia se cuentan como retiradas a mano."""
        zonas = self._zonas_camara_vasos()
        for id_vaso, (_, casilla) in list(self._vasos.items()):
            if casilla not in zonas:
                continue
            registro = self.embalaje.registro.obtener(id_vaso)
            if registro.estado in (EstadoVaso.INVALIDA, EstadoVaso.VACIA, EstadoVaso.RECHAZADA):
                continue
            presente, media, borde = self._votar_zona(zonas[casilla])
            marcador = self._leer_marcador(casilla)
            motivo = ("retirado_con_mano" if not presente else
                      "vaso_cambiado" if not self.embalaje.es_el_mismo_vaso(registro, marcador) else
                      "figura_distinta" if (not media or borde) else None)
            if motivo:
                registro.degradar(EstadoVaso.INVALIDA)
                self._evento("vasos", "sabotaje_detectado", vaso=id_vaso, motivo=motivo, estacion="cortina",
                             casilla=casilla, monedas_retiradas=registro.cantidad_monedas if not presente else 0)

    def _estacion_descarga_vasos(self, id_vaso: int, elemento: Elemento | None) -> None:
        # Punto 12 (grupo, 2026-09-25): si la canaleta esta llena (el carro no
        # ha venido), el vaso tapado espera en la descarga y la cinta de vasos
        # se detiene; la de monedas sigue guardando en los tubos.
        if (self.embalaje.registro.obtener(id_vaso).estado == EstadoVaso.TAPADA
                and len(self.canaleta) >= self.capacidad_canaleta):
            if self._vaso_esperando_canaleta != id_vaso:
                self._evento("vasos", "canaleta_llena", vaso=id_vaso, en_canaleta=len(self.canaleta))
            self._vaso_esperando_canaleta = id_vaso
            return
        self._vaso_esperando_canaleta = None
        destino = self.embalaje.descargar(id_vaso)
        if elemento is not None and elemento.activo:
            if destino == "entrega":
                self.backend.servo_empujador_entrega.activar()
            else:  # rechazo o vacio: la cinta lo deja caer por el extremo a la bandeja
                self.backend.salida_fin_de_cinta.activar()
        if destino == "entrega":
            self.canaleta.append(id_vaso)
        casilla = self.embalaje.registro.obtener(id_vaso)
        self.vasos_finales[id_vaso] = destino
        self.vasos_salida.append({"id": id_vaso, "destino": destino, "cantidad": casilla.cantidad_monedas,
                                  "valor": casilla.valor_total, "tapado": destino == "entrega",
                                  "denominacion": casilla.denominacion})
        self._evento("vasos", "descarga", vaso=id_vaso, destino=destino, estado=casilla.estado.value,
                     cantidad=casilla.cantidad_monedas, valor=casilla.valor_total,
                     masa_g=round(casilla.masa_estimada_g, 2))
        del self._vasos[id_vaso]

    # ------------------------------------------------------------------
    # estacion 7 -> almacen por denominacion -> vaso (por lotes)
    # ------------------------------------------------------------------

    def cambiar_lote(self, monedas_por_vaso: int) -> int:
        """Cambia en caliente cuantas monedas lleva cada vaso (depende de
        las monedas que haya ese dia). Entre 1 y la capacidad de un tubo;
        los vasos ya llenos no cambian. Devuelve el valor aplicado."""
        self.monedas_por_vaso = max(1, min(int(monedas_por_vaso), self.almacen.capacidad))
        self._evento("vasos", "lote_cambiado", monedas_por_vaso=self.monedas_por_vaso)
        return self.monedas_por_vaso

    def precargar_almacen(self, monedas: list[dict]) -> int:
        """Turno nuevo que arranca con lo que dejo el anterior en los tubos
        (`AlmacenDenominaciones.exportar`). Cada moneda se crea en su tubo
        con su registro propio, como si hubiera entrado en este turno pero
        sin pasar por la cinta. Devuelve cuantas se cargaron."""
        cargadas = 0
        for m in monedas:
            datos = buscar_por_clase(m["clase"])
            if datos is None or not self.almacen.puede_recibir(m["valor"]):
                continue
            id_registro = self._id_elemento_siguiente
            self._id_elemento_siguiente += 1
            cuerpo = self.escena.crear_elemento(tipo="moneda", clase_real=m["clase"], metal=True,
                                                diametro_mm=datos.diametro_mm, masa_g=datos.masa_g)
            cuerpo.id_registro = id_registro
            n = self.almacen.guardar(m["valor"], MonedaAlmacenada(id_registro, m["clase"], m["valor"], m["masa_g"]))
            lugar = self.almacen.destino(m["valor"])
            self.escena.guardar_en_tubo(cuerpo, lugar, n - 1)
            self._cuerpos_en_tubo[lugar].append(cuerpo)
            cargadas += 1
        if cargadas:
            self._evento("e4", "almacen_precargado", cantidad=cargadas, contenido=self.almacen.contenido(),
                         otras=self.almacen.cantidad_otras())
            if self.ticks == 0:
                # Se llama ANTES del primer tick (app/supervisor.py, iniciar): el
                # primer `paso()` vacia `_eventos` y el aviso se perdia sin llegar
                # a la base. Va con los eventos del arranque, que el supervisor
                # guarda justo despues de precargar.
                self.eventos_arranque.append(self._eventos[-1])
        return cargadas

    # ------------------------------------------------------------------
    # carrusel (tiempo real): reloj de la planta en ms
    # ------------------------------------------------------------------

    def _t0(self) -> float:
        """Instante (ms) en que empezo el tick en curso: cada tick es un ciclo
        de la cinta de monedas (avance + pausa)."""
        return max(0, self.ticks - 1) * self._ciclo_ms

    def _tubo_de(self, id_registro: int):
        """Posicion del carrusel de una moneda aceptada: su tubo u OTRAS."""
        return self.almacen.destino(self.linea.registro.obtener(id_registro).denominacion)

    def _evento_giro(self, motivo: str, **extra) -> None:
        """Evento para el visor: el carrusel empieza un giro. `en_ms` es cuanto
        despues del comienzo de este tick arranca (el visor lo anima con ese
        retraso y esa duracion, a su velocidad)."""
        g = self.carrusel.ultimo_giro
        self._evento("carrusel", "gira", tubo=g["tubo"], lugar=g["lugar"], desde_grados=g["desde_grados"],
                     hasta_grados=g["hasta_grados"], dur_ms=g["dur_ms"],
                     en_ms=int(round(g["t_inicio_ms"] - self._t0())), motivo=motivo, **extra)

    def _mover_carrusel(self, t_ms: float) -> None:
        """Lleva bajo la carga el tubo de la PRIMERA moneda aceptada que falta
        guardar (si el carrusel no esta ocupado soltando un lote). Se llama al
        aceptar una moneda (anticipacion: gira mientras ella viaja a E4), al
        guardar una (va al tubo de la siguiente) y al terminar un lote."""
        if self._embalado is not None or not self._cola_carga:
            return
        id_registro = self._cola_carga[0]
        tubo = self._tubo_de(id_registro)
        giros = self.carrusel.giros
        self.carrusel.pedir(tubo, CARGA, max(t_ms, self._carrusel_ocupado_hasta))
        if self.carrusel.giros != giros:
            self._evento_giro("moneda", casilla=id_registro)

    def _vasos_libres_del_carrusel(self) -> bool:
        """La cinta de vasos no se mueve con un lote en camino o cayendo."""
        return self._embalado is None and self._t0() >= self._carrusel_ocupado_hasta

    def _guardar_o_esperar(self, moneda: Elemento, id_registro: int, t_ms: float) -> bool:
        """Descarga (E4) de una moneda aceptada en el instante `t_ms`: cae a su
        tubo SOLO si el tubo esta lleno de lugar Y quieto bajo la carga. Si
        no, la moneda espera en la descarga (la cinta de monedas se detiene) y
        se avisa por que: `tubo_lleno` o `carrusel_girando` (con cuanto falta).
        Nunca se bota. Devuelve True si quedo guardada."""
        r = self.linea.registro.obtener(id_registro)
        tubo = self.almacen.destino(r.denominacion)
        if id_registro not in self._cola_carga:
            self._cola_carga.append(id_registro)   # por si no paso por la vision de esta planta
        if not self.almacen.puede_recibir(r.denominacion):
            motivo = "tubo_lleno"
        elif not self.carrusel.en(tubo, CARGA, t_ms):
            motivo = "carrusel_girando"
            self._mover_carrusel(t_ms)
        else:
            self._almacenar(moneda, id_registro, t_ms)
            return True
        if self._moneda_en_espera is None or self._motivo_espera != motivo:
            datos = {"casilla": id_registro, "motivo": motivo, "denominacion": r.denominacion, "tubo": tubo,
                     "en_ms": int(round(t_ms - self._t0()))}
            if motivo == "carrusel_girando":
                datos["tubo_bajo_carga"] = self.carrusel.tubo_en(CARGA, t_ms)
                datos["soltando_lote"] = self._embalado is not None or t_ms < self._carrusel_ocupado_hasta
                if self.carrusel.va_a(tubo, CARGA):
                    datos["falta_ms"] = int(round(self.carrusel.falta_ms(t_ms)))
                self.esperas_carrusel.append(dict(datos, tick=self.ticks))
            self._evento("e4", "espera", **datos)
        self._moneda_en_espera = (moneda, id_registro)
        self._motivo_espera = motivo
        return False

    def _almacenar(self, moneda: Elemento, id_registro: int, t_ms: float) -> None:
        """La moneda aceptada cae por el canal corto a la boca del tubo de su
        denominacion, que ya esta quieto bajo la carga (lo comprobo
        `_guardar_o_esperar`)."""
        r = self.linea.registro.obtener(id_registro)
        d = r.denominacion
        n = self.almacen.guardar(d, MonedaAlmacenada(id_registro, r.clase, r.valor, r.masa_estimada_g))
        lugar = self.almacen.destino(d)  # su tubo, o OTRAS si esa denominacion no tiene tubo
        self.escena.guardar_en_tubo(moneda, lugar, n - 1)
        self._cuerpos_en_tubo[lugar].append(moneda)
        self.guardados.append({"tick": self.ticks, "casilla": id_registro, "tubo_pedido": lugar,
                               "tubo_bajo_carga": self.carrusel.tubo_en(CARGA, t_ms),
                               "girando": not self.carrusel.listo(t_ms)})
        self._finalizar_elemento(id_registro, Destino.VASO, almacen=d)
        self._evento("e4", "almacen", casilla=id_registro, clase=r.clase, denominacion=d, tubo=lugar, en_tubo=n,
                     en_ms=int(round(t_ms - self._t0())))
        if id_registro in self._cola_carga:
            self._cola_carga.remove(id_registro)
        # La moneda baja por el canal hasta el fondo del tubo: mientras tanto
        # el disco no se mueve. Recien entonces el carrusel puede ir al tubo de
        # la siguiente (`pedir` arranca despues de `ocupar`).
        self.carrusel.ocupar(t_ms + self._t_caida_tubo_ms)
        self._mover_carrusel(t_ms)

    def _atender_carrusel(self) -> None:
        """Lote en camino al agujero: si en este tick el tubo llega (y el vaso
        de llenado ya esta quieto), justo antes se re-verifica con la camara
        de vasos que abajo haya un vaso valido, se abre el obturador, cae el
        lote y el obturador se cierra (`compuerta_tubo`). Con una mano en la
        zona (cortina) el obturador no se abre: se reintenta el tick
        siguiente."""
        e = self._embalado
        if e is None:
            return
        t_abrir = max(e["llegada"], self._vasos_quietos_ms, self._t0())
        if t_abrir >= self._t0() + self._ciclo_ms or self.embalaje.cortina_activa:
            return
        d, id_vaso = e["denominacion"], e["vaso"]
        self._embalado = None
        reg = self.embalaje.registro.obtener(id_vaso) if id_vaso in self._vasos else None
        _, media, borde = self._votar_zona(self.backend.zona_llenado)
        marcador = self._leer_marcador(ESTACION_LLENADO_VASOS)
        self._lecturas.update(llenado_media=media, llenado_borde=borde)
        mismo = reg is not None and self.embalaje.es_el_mismo_vaso(reg, marcador)
        if (reg is None or self._vaso_en(ESTACION_LLENADO_VASOS) != id_vaso or not (media and not borde and mismo)
                or reg.estado != EstadoVaso.VALIDA):
            # Lo cambiaron o retiraron mientras el tubo giraba: no se suelta
            # nada, el lote sigue guardado y la cinta de vasos salta la casilla.
            if reg is not None and reg.estado == EstadoVaso.VALIDA:
                reg.degradar(EstadoVaso.INVALIDA)
                motivo = ("vaso_cambiado" if not mismo else "figura_alta" if borde else "retirado_o_figura_baja")
                self._evento("vasos", "sabotaje_detectado", vaso=id_vaso, motivo=motivo, estacion="llenado")
            self._evento("vasos", "salto_casilla", vaso=id_vaso, motivo="no_hay_vaso_valido_en_llenado",
                         denominacion_esperando=d)
            self._carrusel_ocupado_hasta = t_abrir
            self._vaso_pide_avance = True
            self._mover_carrusel(t_abrir)
            return

        lote = self.almacen.sacar(d, self.monedas_por_vaso)
        self.embalaje.llenar_lote(id_vaso, denominacion=d, monedas=[(m.valor, m.masa_g) for m in lote])
        cuerpos, self._cuerpos_en_tubo[d] = self._cuerpos_en_tubo[d][:len(lote)], self._cuerpos_en_tubo[d][len(lote):]
        elemento_vaso = self._vasos[id_vaso][0]
        for cuerpo in cuerpos:
            self.escena.depositar_en_vaso(cuerpo, elemento_vaso)
        self.escena.reacomodar_tubo(self._cuerpos_en_tubo[d], d)
        self._carrusel_ocupado_hasta = t_abrir + self._t_compuerta_ms
        self.carrusel.ocupar(self._carrusel_ocupado_hasta)   # obturador abierto: el disco quieto
        self._evento("vasos", "embalado", vaso=id_vaso, denominacion=d, cantidad=reg.cantidad_monedas,
                     valor=reg.valor_total, masa_g=round(reg.masa_estimada_g, 2),
                     monedas=[m.id_registro for m in lote], quedan_en_tubo=self.almacen.cantidad(d),
                     tubo_sobre_agujero=self.carrusel.tubo_en(AGUJERO, t_abrir),
                     en_ms=int(round(t_abrir - self._t0())), obturador_ms=self._t_compuerta_ms)
        self._vaso_pide_avance = True
        # Obturador cerrado: el carrusel vuelve a la carga si alguna moneda lo espera.
        self._mover_carrusel(self._carrusel_ocupado_hasta)

    def _intentar_embalar(self) -> None:
        """Si algun tubo tiene un lote listo y en llenado hay un vaso VALIDO
        y vacio, el carrusel lleva ese tubo al agujero (tiempo real). El
        obturador se abre recien cuando llega (`_atender_carrusel`), despues
        de volver a mirar con la camara de vasos que abajo siga el vaso.
        Aqui ya se mira una vez, para no girar por nada: una figura o un vaso
        retirado no reciben nada."""
        if self._embalado is not None:
            return  # ya hay un lote en camino
        if self._moneda_en_espera is not None and self._motivo_espera == "carrusel_girando":
            # Una moneda ya espera en la descarga a que su tubo llegue a la
            # carga: no se le quita el carrusel (quedaria esperando la ida al
            # agujero y la vuelta, ~8 s). El lote sale apenas ella caiga. Una
            # moneda que todavia viene de la vision si espera al lote (el
            # diseno de control/tiempos.py: la cinta espera una vez por lote).
            return
        if self._vaso_pide_avance:
            return  # el vaso de llenado ya esta lleno, esperando salir
        if self.embalaje.cortina_activa:
            return  # algo (una mano) en la zona: el obturador no se abre
        d = self.almacen.lote_listo(self.monedas_por_vaso, aceptar_parciales=self.embalar_parciales)
        if d is None:
            return
        id_vaso = self._vaso_en(ESTACION_LLENADO_VASOS)
        if id_vaso is None:
            # Hay un lote esperando y no hay vaso bajo la tolva (p. ej. al
            # final del turno): la cinta de vasos avanza y trae uno.
            self._vaso_pide_avance = True
            return
        reg = self.embalaje.registro.obtener(id_vaso)
        if reg.cantidad_monedas > 0:
            self._vaso_pide_avance = True
            return

        _, media, borde = self._votar_zona(self.backend.zona_llenado)
        marcador = self._leer_marcador(ESTACION_LLENADO_VASOS)
        self._lecturas.update(llenado_media=media, llenado_borde=borde)
        mismo = self.embalaje.es_el_mismo_vaso(reg, marcador)
        es_vaso = media and not borde and mismo
        if not es_vaso or reg.estado != EstadoVaso.VALIDA:
            if reg.estado == EstadoVaso.VALIDA:
                reg.degradar(EstadoVaso.INVALIDA)
                motivo = ("vaso_cambiado" if not mismo else "figura_alta" if borde else "retirado_o_figura_baja")
                self._evento("vasos", "sabotaje_detectado", vaso=id_vaso, motivo=motivo, estacion="llenado")
            self._evento("vasos", "salto_casilla", vaso=id_vaso, motivo="no_hay_vaso_valido_en_llenado",
                         denominacion_esperando=d)
            self._vaso_pide_avance = True
            return

        # El tubo del lote va al agujero. Arranca cuando termino lo de este
        # tick en la cinta de monedas (la moneda que tocaba ya cayo) y nunca
        # con el obturador todavia abierto. Si iba hacia una moneda, esa
        # moneda espera: el lote tiene prioridad (libera el tubo).
        t = max(self._t0() + self._t_avance_ms, self._carrusel_ocupado_hasta)
        giros = self.carrusel.giros
        llegada = self.carrusel.pedir(d, AGUJERO, t)
        self._embalado = {"denominacion": d, "vaso": id_vaso, "llegada": llegada}
        if self.carrusel.giros != giros:
            self._evento_giro("lote", vaso=id_vaso)
        self._atender_carrusel()

    # ------------------------------------------------------------------
    # cinta de monedas
    # ------------------------------------------------------------------

    def _finalizar_elemento(self, id_registro: int, destino: str, **extra) -> None:
        c = self.linea.registro.obtener(id_registro)
        self.destinos_finales[id_registro] = destino
        esperado = self._esperado.get(id_registro)
        if esperado == Destino.VASO and destino != Destino.VASO:
            self.errores_filtrado["falsos_rechazos"].append(id_registro)
        elif esperado not in (None, Destino.VASO) and destino == Destino.VASO:
            self.errores_filtrado["falsas_aceptaciones"].append(id_registro)
        if destino == Destino.VASO:
            elemento = self._elementos.get(id_registro)
            if elemento is not None and elemento.clase_real and c.clase != elemento.clase_real:
                self.errores_filtrado["clase_equivocada"].append(id_registro)
        if destino in self.salidas:
            elemento = self._elementos.get(id_registro)
            self.salidas[destino].append({
                "id": id_registro, "causa": c.causa,
                "tipo": self._tipo_real.get(id_registro),
                "clase_real": elemento.clase_real if elemento else None,
            })
        self._evento(
            "linea", "elemento_final", casilla=id_registro, destino=destino,
            veredicto="aceptada" if destino == Destino.VASO else "rechazada",
            causa=c.causa, clase=c.clase, confianza=c.confianza, diametro_mm=c.diametro_mm,
            denominacion=c.denominacion, valor=c.valor, masa_g=c.masa_estimada_g, **extra,
        )

    def _inyectar_siguiente(self) -> bool:
        """El operador pone el siguiente elemento en la casilla de carga y el
        infrarrojo de presencia (E1, en esa casilla) lo lee. Devuelve si lo
        vio. Con la cinta vacia (nada registrado) y nada visto, no se
        registra nada: la cinta espera. Si habia un objeto que el infrarrojo
        no vio (falso negativo), sigue ahi y se vuelve a leer en la pausa
        siguiente (no aparece otro encima)."""
        if self._mano_pendiente:
            self._mano_pendiente = False
            return self._inyectar_mano()
        if self._en_carga is not None:
            especificacion, elemento = self._en_carga
        else:
            especificacion = self._pendientes.popleft()
            if especificacion.tipo == "mano":
                return self._inyectar_mano()
            elemento = None if especificacion.tipo == "vacia" else _crear_desde_especificacion(self.escena, especificacion)

        # Estacion 1: el infrarrojo de presencia decide, no el escenario. El
        # capacitivo (debajo de esta misma casilla) lee en la misma pausa.
        ocupada = self._votar(self.backend.sensor_presencia.leer)
        capacitivo = self._votar(self.backend.sensor_capacitivo.leer)
        self._lecturas.update(presencia=ocupada, capacitivo=capacitivo)
        if not ocupada and not self._hay_registrados_en_cinta():
            # Cinta vacia y nada visto en la carga: no hay nada que registrar
            # y la cinta no avanza. Un objeto que si estaba queda en la carga.
            self._en_carga = (especificacion, elemento) if elemento is not None else None
            return False
        self._en_carga = None

        id_registro = self._id_elemento_siguiente
        self._id_elemento_siguiente += 1
        self._tipo_real[id_registro] = especificacion.tipo
        if elemento is not None:
            elemento.id_registro = id_registro
        self._elementos[id_registro] = elemento
        self.orden_ids.append(id_registro)
        self._esperado[id_registro] = especificacion.destino_esperado
        self._capacitivo_e1[id_registro] = capacitivo
        self.linea.estacion_1_presencia(id_registro, ocupada=ocupada)
        # Verdad de terreno (seccion 11) para la matriz de Calidad del
        # dashboard: el diametro REAL del cuerpo, no el que mide la camara.
        self._evento("e1", "presencia", casilla=id_registro, ocupada=ocupada,
                     tipo_real=especificacion.tipo, clase_real=especificacion.clase_real,
                     diametro_real_mm=round(elemento.diametro_mm, 2) if elemento is not None else None,
                     apariencia=especificacion.apariencia)
        if not ocupada:
            self.destinos_finales[id_registro] = Destino.VACIA
        if especificacion.tipo == "vacia" and ocupada:
            # Falso positivo del infrarrojo en una casilla vacia: viaja
            # registrada y sin cuerpo, igual que la mano retirada, y sale por
            # la bandeja de rechazo (en E2 no hay material).
            self._fantasmas[id_registro] = 0
        return ocupada

    def _inyectar_mano(self) -> None:
        """Sabotaje del punto 1: alguien pone la mano en la casilla de carga
        y la quita antes del avance. El infrarrojo la ve (casilla ocupada),
        pero viaja vacia: en E2 ni el capacitivo ni el inductivo ven nada,
        asi que sale como no_metalico por la bandeja de rechazo."""
        id_registro = self._id_elemento_siguiente
        self._id_elemento_siguiente += 1
        self._tipo_real[id_registro] = "mano"
        self._elementos[id_registro] = None
        self.orden_ids.append(id_registro)
        self._esperado[id_registro] = Destino.RECHAZO
        mano = self.escena.crear_mano_en_carga()
        ocupada = self._votar(self.backend.sensor_presencia.leer)
        capacitivo = self._votar(self.backend.sensor_capacitivo.leer)
        self.escena.quitar_intruso(mano)
        self._lecturas.update(presencia=ocupada, capacitivo=capacitivo)
        self._capacitivo_e1[id_registro] = capacitivo
        self.linea.estacion_1_presencia(id_registro, ocupada=ocupada)
        self._evento("e1", "presencia", casilla=id_registro, ocupada=ocupada, tipo_real="mano", clase_real=None,
                     diametro_real_mm=None)
        if ocupada:
            self._fantasmas[id_registro] = 0
        else:
            self.destinos_finales[id_registro] = Destino.VACIA
        return ocupada

    def _procesar_fantasmas(self) -> None:
        """Casillas registradas como ocupadas que viajan sin cuerpo (una mano
        que se puso y se quito en la carga, o un falso positivo de E1). En E2
        no hay material -> quedan rechazadas; en la descarga no cae nada, pero
        el registro se cierra como rechazo."""
        for id_registro, casilla in list(self._fantasmas.items()):
            if casilla == ESTACION_MATERIAL_MONEDAS:
                capacitivo = self._capacitivo_e1.pop(id_registro, False)
                inductivo = self._votar(self.backend.sensor_inductivo.leer)
                self._lecturas["inductivo"] = inductivo
                self.linea.estacion_2_material(id_registro, capacitivo, inductivo)
                self._evento("e2", "material", casilla=id_registro, capacitivo=capacitivo, inductivo=inductivo,
                             metal=self.linea.registro.obtener(id_registro).metal)
            elif casilla == ESTACION_DESCARGA_MONEDAS:
                self._a_rechazo(None, id_registro, "casilla_sin_pieza")
                del self._fantasmas[id_registro]

    def _procesar_estaciones_monedas(self) -> None:
        """Filtro total (grupo, 2026-09-25): E1 presencia, E2 material, E3
        vision y E4 descarga. Nada se saca de la cinta a mitad de camino: todo
        llega a E4, donde la compuerta de desvio manda lo aceptado al almacen
        y todo lo demas a la unica bandeja de rechazo."""
        for elemento in list(self.escena.elementos_monedas):
            if not elemento.activo:
                continue
            casilla = elemento.casilla
            id_registro = elemento.id_registro
            registro = self.linea.registro.obtener(id_registro)

            if casilla == ESTACION_MATERIAL_MONEDAS:
                # El capacitivo ya leyo esta casilla cuando estaba en E1.
                capacitivo = self._capacitivo_e1.pop(id_registro, False)
                inductivo = self._votar(self.backend.sensor_inductivo.leer)
                self._lecturas["inductivo"] = inductivo
                if not registro.ocupada and (capacitivo or inductivo):
                    # E2 respalda a E1: el infrarrojo de presencia no vio este
                    # elemento (falso negativo), pero el capacitivo/inductivo
                    # si. Se registra aqui y sigue normal por la linea.
                    self.linea.estacion_1_presencia(id_registro, ocupada=True)
                    self.destinos_finales.pop(id_registro, None)
                    self._evento("e2", "presencia_recuperada", casilla=id_registro)
                self.linea.estacion_2_material(id_registro, capacitivo, inductivo)
                self._evento("e2", "material", casilla=id_registro, capacitivo=capacitivo,
                             inductivo=inductivo, metal=registro.metal)

            elif casilla == ESTACION_VISION_MONEDAS:
                # Lo que ya quedo rechazado por material no gasta camara.
                if registro.ocupada and not registro.rechazada:
                    self._lecturas["camara"] = True
                    fotos = [self.backend.camara.observar(elemento) for _ in range(self.fotos_por_moneda)]
                    clase, confianza, motivo = reglas.combinar_fotos(
                        [(v.clase, v.confianza) for v in fotos], self.linea.params)
                    # Geometria: promedio de las fotos (baja el ruido de medicion).
                    diametro = round(sum(v.diametro_mm for v in fotos) / len(fotos), 2)
                    circularidad = round(sum(v.circularidad for v in fotos) / len(fotos), 3)
                    contornos = max(v.contornos_internos for v in fotos)
                    self.linea.estacion_5_vision(
                        id_registro, diametro_mm=diametro, circularidad=circularidad,
                        contornos_internos=contornos, clase=clase, confianza=confianza,
                    )
                    self._evento("e3", "vision", casilla=id_registro, diametro_mm=diametro,
                                 circularidad=circularidad, contornos_internos=contornos,
                                 clase=clase, confianza=confianza,
                                 fotos=[[v.clase, v.confianza] for v in fotos], combinacion=motivo,
                                 veredicto="aceptada" if registro.aceptada else "rechazada",
                                 causa=registro.causa)
                    if registro.aceptada:
                        # Anticipacion: con el veredicto en la mano (fin de la
                        # vision, dentro de la pausa) el carrusel ya puede ir
                        # al tubo de esta moneda mientras ella viaja a E4.
                        self._cola_carga.append(id_registro)
                        self._mover_carrusel(self._t0() + self._t_acepta_ms)

            elif casilla == ESTACION_DESCARGA_MONEDAS:
                destino = self.linea.destino(id_registro)
                if destino == Destino.VASO:
                    # Cae al final del avance que la trajo a la descarga.
                    self._guardar_o_esperar(elemento, id_registro, self._t0() + self._t_avance_ms)
                elif destino == Destino.RECHAZO:
                    self._a_rechazo(elemento, id_registro, registro.causa or "rechazada")
                else:
                    # Ningun sensor registro este cuerpo (fallaron E1 y E2 a
                    # la vez): no se sabe que es, asi que se rechaza. Causa
                    # `no_reconocida` (seccion 7: "rechazar lo que no reconoce"):
                    # antes quedaba NULL en `elementos`, y el conteo por causa
                    # del dashboard lo perdia. Las causas son SOLO las de la
                    # seccion 7 (docs/especificacion.md 10.2); el detalle de que fallaron
                    # los sensores queda en el evento (`motivo: sin_registro`).
                    registro.rechazar(reglas.CAUSA_NO_RECONOCIDA)
                    self._a_rechazo(elemento, id_registro, "sin_registro")

    def _hay_registrados_en_cinta(self) -> bool:
        """Lo que la linea SABE que lleva (registros sin destino final), no lo
        que hay de verdad en la simulacion: es lo que sabria el control real."""
        return any(i not in self.destinos_finales for i in self.orden_ids)

    def _quedan_monedas_en_cinta(self) -> bool:
        return bool(self._fantasmas) or any(e.activo for e in self.escena.elementos_monedas)

    def _avanzar_cinta_monedas(self) -> None:
        self.escena.avanzar_casilla_monedas()
        self._verificar_posicion("monedas")
        for id_registro in self._fantasmas:
            self._fantasmas[id_registro] += 1
        self._evento("linea", "paso")
        self._procesar_estaciones_monedas()
        self._procesar_fantasmas()

    # ------------------------------------------------------------------
    # tick
    # ------------------------------------------------------------------

    def paso(self) -> list[dict]:
        """Un tick de la planta. Devuelve los eventos que ocurrieron."""
        if self.terminado:
            return []
        self.ticks += 1
        self._eventos = []
        self._lecturas = {}
        if self._mano_temporal is not None:
            self._mano_temporal[1] -= 1
            if self._mano_temporal[1] <= 0:
                self.escena.quitar_intruso(self._mano_temporal[0])
                self._mano_temporal = None
        self._revisar_cortina()
        self._vigilar_vasos()
        self._revisar_alarmas()
        if self.carro is not None:
            self._carro_fisico()
        else:
            self._carro_de_reemplazo()

        # 1) Una moneda aceptada que espera en la descarga (su tubo esta lleno,
        #    o el carrusel todavia no lo trajo a la carga) detiene la cinta de
        #    monedas: no se descarta. Cae cuando la cinta vuelve a moverse, al
        #    comienzo de un ciclo, si para entonces el tubo ya esta quieto en
        #    la carga (la simulacion redondea la espera a ciclos enteros; en
        #    el montaje la cinta arranca apenas llega el carrusel).
        if self._moneda_en_espera is not None:
            moneda, id_registro = self._moneda_en_espera
            if self._guardar_o_esperar(moneda, id_registro, self._t0()):
                self._moneda_en_espera = None
                self._motivo_espera = None
            else:
                if self._vaso_pide_avance and self._avanzar_vasos():
                    self._vaso_pide_avance = False
                self._intentar_embalar()
                self._atender_carrusel()
                return self._eventos

        # 2) El vaso de llenado ya recibio su lote (o no era valido y hay que
        #    saltarlo): la cinta de vasos avanza, si la cortina lo permite (y
        #    si el obturador ya se cerro).
        if self._vaso_pide_avance:
            hay_lotes = self.almacen.lote_listo(self.monedas_por_vaso, aceptar_parciales=self.embalar_parciales)
            sin_mas_produccion = not self._pendientes and not self._quedan_monedas_en_cinta() and hay_lotes is None
            if self._avanzar_vasos(forzado=sin_mas_produccion):
                self._vaso_pide_avance = False

        # 3) Cinta de monedas: el operador pone (o no) el siguiente elemento en
        #    la casilla de carga y el infrarrojo de presencia (E1, en esa
        #    misma casilla) lo lee. La banda avanza SOLO si lleva algo
        #    registrado o si el infrarrojo vio algo en la carga (usuario,
        #    2026-09-26): vacia y sin carga, se queda quieta esperando.
        if self._pendientes or self._mano_pendiente or self._en_carga is not None:
            vio_algo = self._inyectar_siguiente()
            if vio_algo or self._hay_registrados_en_cinta():
                self._avanzar_cinta_monedas()
            else:
                self._evento("linea", "espera", motivo="cinta_vacia_sin_carga")
        elif self._quedan_monedas_en_cinta():
            self._avanzar_cinta_monedas()
        # 4) Ya no entra nada: se embalan los lotes que falten y se sacan los
        #    vasos con monedas. Lo que no completo lote queda GUARDADO en su
        #    tubo (no se descarta); "embalar parciales" lo empaca tambien.
        elif self._vaso_pide_avance or self.almacen.lote_listo(
            self.monedas_por_vaso, aceptar_parciales=self.embalar_parciales
        ) is not None:
            pass
        elif self._vasos:
            # Fin de la produccion: la cinta de vasos se vacia (los llenos se
            # entregan y los vacios se desechan), asi la corrida siguiente
            # arranca de cero.
            self._avanzar_vasos(forzado=True)
        elif self.carro is not None and (self.canaleta or self._vaso_en_carro is not None
                                         or self._carga_sin_confirmar is not None
                                         or self.carro.control.estado != "esperando_carga"):
            # Con el carro fisico, la corrida termina cuando entrego todo lo
            # que habia en la canaleta y volvio al muelle.
            pass
        else:
            self.terminado = True
            self._evento("linea", "fin", ticks=self.ticks, en_almacen=self.almacen.contenido())
            return self._eventos

        self._intentar_embalar()
        self._atender_carrusel()
        return self._eventos

    # ------------------------------------------------------------------
    # sabotajes (seccion 2: retirar un vaso, cambiarlo por una figura
    # distinta, meter una mano). Se disparan desde el dashboard; la planta
    # NO se entera por aqui de que hubo sabotaje -- se tiene que dar cuenta
    # con sus sensores, igual que la linea real.
    # ------------------------------------------------------------------

    def _vaso_para_sabotear(self) -> tuple[int, Elemento] | None:
        for casilla in (ESTACION_LLENADO_VASOS, ESTACION_VERIFICACION_VASOS):
            id_vaso = self._vaso_en(casilla)
            if id_vaso is not None and self._vasos[id_vaso][0] is not None:
                return id_vaso, self._vasos[id_vaso][0]
        return None

    def colocar_pieza(self, especificacion: EspecificacionElemento) -> bool:
        """El operador pone ESA pieza en la proxima carga (usuario, 2026-09-27: "colocar pieza X").
        Va antes de lo que falta del escenario; si la corrida ya habia terminado, sigue solo para
        procesarla (la cinta y el carro retoman donde estaban)."""
        self._pendientes.appendleft(especificacion)
        self.terminado = False
        return True

    def sabotaje_retirar_vaso(self) -> int | None:
        objetivo = self._vaso_para_sabotear()
        if objetivo is None:
            return None
        id_vaso, elemento = objetivo
        self.escena.retirar_vaso(elemento)
        self._vasos[id_vaso][0] = None
        return id_vaso

    def _leer_marcador(self, casilla: int) -> int | None:
        """Camara de vasos: dos intentos de leer el marcador ArUco del vaso
        que esta en esa casilla (si el primero no lee por un reflejo)."""
        for _ in range(2):
            marcador = self.backend.camara_vasos.leer(casilla)
            if marcador is not None:
                self._lecturas["camara_vasos"] = True
                return marcador
        self._lecturas["camara_vasos"] = False
        return None

    def _verificar_posicion(self, cinta: str) -> None:
        """Despues de cada avance, la camara de esa cinta mide donde quedaron
        los separadores. Si la cinta quedo corrida (patino, alguien la
        freno), el PC manda los micropasos que faltan en la misma pausa: la
        cinta se re-sincroniza y queda registrado."""
        sensor = self.backend.posicion_monedas if cinta == "monedas" else self.backend.posicion_vasos
        sensor.nuevo_avance()
        en_posicion = self._votar(sensor.leer)
        self._lecturas[f"posicion_{cinta}"] = en_posicion
        if not en_posicion:
            self.desfases[cinta] += 1
            sensor.resincronizar()
            self._evento(cinta if cinta == "vasos" else "linea", "desfase_corregido", cinta=cinta)

    def sabotaje_cambiar_por_vaso_igual(self) -> int | None:
        """El profesor cambia un vaso por OTRO igual (mismo tamano, otro
        marcador). La silueta no lo nota; el marcador ArUco si."""
        objetivo = self._vaso_para_sabotear()
        if objetivo is None:
            return None
        id_vaso, elemento = objetivo
        self.escena.sustituir_por_vaso_igual(elemento, nuevo_marcador=900 + id_vaso)
        return id_vaso

    def sabotaje_cambiar_vaso(self) -> int | None:
        objetivo = self._vaso_para_sabotear()
        if objetivo is None:
            return None
        id_vaso, elemento = objetivo
        self.escena.sustituir_vaso(elemento, altura_mm=self.altura_figura_sabotaje_mm)
        return id_vaso

    def sabotaje_mano_en_carga(self) -> bool:
        """En la proxima carga, en vez del siguiente elemento, alguien pone
        la mano en la casilla y la quita (ver `_inyectar_mano`)."""
        self._mano_pendiente = True
        return True

    def pedir_embalar_parciales(self) -> None:
        """Fin de turno: empacar tambien los tubos que no llegaron a un
        lote completo (cada vaso sigue siendo de una sola denominacion)."""
        self.embalar_parciales = True
        self.terminado = False

    def sabotaje_mano_en_llenado(self) -> bool:
        """Alguien mete la mano en la zona por donde cae el lote al vaso de
        llenado (por encima de la boca). La cortina no llega ahi; la ve la
        camara de vasos. La mano se va sola a los 3 ticks."""
        if self._mano_temporal is not None:
            return False
        mano = self.escena.crear_intruso(casilla_vasos=ESTACION_LLENADO_VASOS, altura_mano_m=0.12)
        self._mano_temporal = [mano, 3, ESTACION_LLENADO_VASOS, 0.12]
        return True

    def sabotaje_mano_saca_vaso(self) -> int | None:
        """Alguien mete la mano a media altura en la zona de tapa y prensa y
        se lleva un vaso (el de prensa, o el de tapa). La cortina la ve y
        congela la zona; la mano se va sola a los 2 ticks y, al despejarse,
        la camara revisa los vasos y encuentra el que falta."""
        if self._mano_temporal is not None:
            return None
        for casilla in (ESTACION_PRENSA_VASOS, ESTACION_TAPA_VASOS):
            id_vaso = self._vaso_en(casilla)
            if id_vaso is not None and self._vasos[id_vaso][0] is not None:
                break
        else:
            return None
        mano = self.escena.crear_intruso(casilla_vasos=casilla, altura_mano_m=0.045)
        self.escena.retirar_vaso(self._vasos[id_vaso][0])
        self._vasos[id_vaso][0] = None
        self._mano_temporal = [mano, 2, casilla, 0.045]
        return id_vaso

    def _carro_de_reemplazo(self) -> None:
        """Hasta que el carro se simule (punto 14): cada
        `carro_retira_cada_ticks` ticks llega un carro al muelle y se lleva
        el primer vaso de la fila de la canaleta, con la secuencia del punto
        13 (usuario, 2026-09-26):

        1. El carro entra de reversa al muelle; sabe que llego porque sus
           encoders dejan de contar contra el tope (`en_muelle`).
        2. El infrarrojo de la cuna tiene que verla VACIA; si ve algo, no se
           suelta nada (`cuna_ocupada`).
        3. El escape de dos dedos suelta UN vaso (`soltar`).
        4. El infrarrojo de la cuna confirma que el vaso llego (`carga`). Si
           no lo ve, alarma `carga_no_confirmada`: el carro no se va y no se
           suelta otro vaso; se vuelve a leer en cada tick."""
        sensor = self.backend.sensor_cuna
        if self._carga_sin_confirmar is not None:
            id_vaso = self._carga_sin_confirmar
            if self._votar(sensor.leer):
                self._carga_sin_confirmar = None
                self._evento("carro", "carga", vaso=id_vaso, ok=True, en_canaleta=len(self.canaleta))
                sensor.ocupada = False   # el carro se va con el vaso
            return
        if not self.canaleta:
            self._ticks_carro = 0
            return
        self._ticks_carro += 1
        if self._ticks_carro < self.carro_retira_cada_ticks:
            return
        self._ticks_carro = 0
        self._evento("carro", "en_muelle")
        if self._votar(sensor.leer):
            self._evento("operador", "alarma", tipo="cuna_ocupada", cortina=self.embalaje.cortina_activa)
            return
        id_vaso = self.canaleta.popleft()
        self._evento("canaleta", "soltar", vaso=id_vaso)
        sensor.ocupada = True
        if self._votar(sensor.leer):
            self._evento("carro", "carga", vaso=id_vaso, ok=True, en_canaleta=len(self.canaleta))
            sensor.ocupada = False
        else:
            self._carga_sin_confirmar = id_vaso
            self._evento("operador", "alarma", tipo="carga_no_confirmada", vaso=id_vaso,
                         cortina=self.embalaje.cortina_activa)

    def _carro_fisico(self) -> None:
        """Puntos 14 y 15 con el carro de verdad. El carro avanza un ciclo de
        la cinta; lo que pasa (llego al muelle, salio, meta, le sacaron el
        vaso...) lo cuenta por la radio con mensajes numerados, y la
        estacion solo sabe lo que le llega por ahi. El carro decide solo con
        su infrarrojo de la cuna cuando salir (lo cargaron) y cuando volver
        (le sacaron el vaso en la meta). La estacion suelta UN vaso solo con
        el enlace vivo, un estado fresco del carro, el carro en el muelle y
        su cuna vacia (`protocolo.puede_soltar_vaso`)."""
        from control import protocolo as pr

        carro, sensor = self.carro, self.backend.sensor_cuna
        if carro.sensor_cuna is None:
            carro.sensor_cuna = sensor
            sensor.ocupada = carro.vaso_cargado
        self._t_ms += int(self.segundos_por_tick * 1000)
        t = self._t_ms

        # 1) Carro: fisica y control. Cada evento sale numerado, con la
        #    lectura de su cuna.
        carro.control.enlace_vivo = self._oye_carro.vivo(t) if self._oye_carro.ultimo_oido is not None else True
        for e in carro.avanzar(self.segundos_por_tick):
            self._emisor_carro.enviar({"t": "evt", "src": "carro", **e, "cuna": self._votar(sensor.leer)}, t)

        # 2) Radio. Con enlace, los dos lados se oyen (latido).
        if self.radio_carro_conectada:
            self._oye_carro.oido(t)
            self._oye_estacion.oido(t)
        if self._oye_carro.cambio(t) == "recuperado":
            # Lo primero al volver el enlace: su estado, con la cuna.
            c = carro.control
            self._emisor_carro.enviar({"t": "evt", "src": "carro", "ev": "estado", "estado": c.estado, "fase": c.fase,
                                       "cuna": self._votar(sensor.leer)}, t)
        cambio = self._oye_estacion.cambio(t)
        if cambio == "perdido":
            self._estado_carro["fresco"] = False
            self._enlace_perdido_alguna_vez = True
            self._evento("carro", "sin_enlace", en_espera=len(self._emisor_carro.pendientes))
        elif cambio == "recuperado" and self._enlace_perdido_alguna_vez:
            self._evento("carro", "enlace_recuperado", en_espera=len(self._emisor_carro.pendientes))
        if self.radio_carro_conectada:
            # Pasa todo lo que el carro tiene sin ack, en orden (lo nuevo y
            # lo que guardo mientras no habia enlace); los repetidos se
            # descartan y cada uno recibe su ack.
            for id_ in sorted(self._emisor_carro.pendientes):
                m = self._emisor_carro.pendientes[id_][0]
                nuevo, ack = self._receptor_estacion.recibir(m)
                self._emisor_carro.ack(ack["id"])
                if nuevo:
                    self._mensaje_del_carro(m)

        # 3) El operador en la meta saca el vaso (un acto fisico: no depende
        #    de la radio). El carro lo ve con su infrarrojo y vuelve.
        c = carro.control
        if c.estado == "en_meta" and carro.vaso_cargado:
            self._t_en_meta += self.segundos_por_tick
            if self._t_en_meta >= self._espera_meta:
                self._t_en_meta = 0.0
                carro.retirar_vaso()
        # Volvio al muelle con el vaso (se perdio el enlace): el operador se
        # lo saca (la estacion ya dio la alarma `cuna_ocupada`).
        if c.estado == "esperando_carga" and carro.vaso_cargado and self._carga_sin_confirmar is None:
            self._t_en_meta += self.segundos_por_tick
            if self._t_en_meta >= self._espera_meta:
                self._t_en_meta = 0.0
                carro.retirar_vaso()
                if self._vaso_en_carro is not None:
                    self._evento("carro", "devuelto", vaso=self._vaso_en_carro)
                    self._vaso_en_carro = None

        # 4) Estacion: soltar UN vaso cuando se puede.
        if self._carga_sin_confirmar is not None:
            # Ya lo solto: espera que el carro diga que salio.
            self._ticks_soltado += 1
            if self._ticks_soltado == 3:
                self._evento("operador", "alarma", tipo="carga_no_confirmada", vaso=self._carga_sin_confirmar,
                             cortina=self.embalaje.cortina_activa)
            return
        if not self.canaleta:
            return
        ok, motivo = pr.puede_soltar_vaso(self._estado_carro, self._oye_estacion.vivo(t))
        if not ok:
            if motivo == "cuna_ocupada" and "cuna_ocupada" not in self._alarmas:
                self._alarmas.add("cuna_ocupada")
                self._evento("operador", "alarma", tipo="cuna_ocupada", cortina=self.embalaje.cortina_activa)
            return
        self._alarmas.discard("cuna_ocupada")
        id_vaso = self.canaleta.popleft()
        self._evento("canaleta", "soltar", vaso=id_vaso)
        self._carga_sin_confirmar = id_vaso
        self._ticks_soltado = 0
        self._estado_carro["cuna"] = None          # hasta que el carro diga
        carro.cargar_vaso()

    def _mensaje_del_carro(self, m: dict) -> None:
        """Un mensaje nuevo del carro, recibido por la radio."""
        ev = m["ev"]
        # Fuera lo que es del transporte, no del evento: tipo, origen, nombre,
        # numero, sesion y `ts` (la hora interna de la simulacion del carro,
        # sim/vehiculo_sim.py: el evento ya lleva la de la planta).
        datos = {k: v for k, v in m.items() if k not in ("t", "src", "ev", "id", "s", "ts")}
        vaso = {"vaso": self._vaso_en_carro} if self._vaso_en_carro else {}
        self._evento("carro", ev, msg=m["id"], **vaso, **datos)
        ec = self._estado_carro
        if ev in ("en_muelle", "estado"):
            ec.update(fresco=True, cuna=m.get("cuna"),
                      en_muelle=(ev == "en_muelle" or m.get("estado") == "esperando_carga"))
        elif ev == "salida":
            ec.update(en_muelle=False, cuna=m.get("cuna"))
            if self._carga_sin_confirmar is not None:
                self._salir_con(self._carga_sin_confirmar)
                self._carga_sin_confirmar = None
        elif ev == "vaso_retirado":
            ec["cuna"] = False
            if self._vaso_en_carro is not None:
                self._evento("carro", "entregado", vaso=self._vaso_en_carro)
                self._vaso_en_carro = None
        elif ev == "vuelve_con_vaso":
            self._evento("operador", "alarma", tipo="vuelve_con_vaso", vaso=self._vaso_en_carro)

    def _salir_con(self, id_vaso: int) -> None:
        self._evento("carro", "carga", vaso=id_vaso, ok=True, en_canaleta=len(self.canaleta))
        self._vaso_en_carro = id_vaso
        self._carro_anunciado = False

    def orden_carro(self, orden: dict) -> tuple[bool, str]:
        """Fase 7: una orden para el carro (del asistente o de un boton). Va
        por el mismo camino que en el montaje: PC -> ESP32 fijo -> radio
        (ESP-NOW) -> carro. Sin enlace no le llega. Devuelve (ok, detalle)."""
        if self.carro is None:
            return False, "En esta corrida no hay carro con física (carro de reemplazo)"
        if not self.radio_carro_conectada:
            return False, "Sin radio con el carro: la orden no le llega (reconecte la radio)"
        if self._carga_sin_confirmar is not None:
            return False, "La estación le está soltando un vaso al carro: espere a que salga"
        ok, detalle = self.carro.control.ordenar(orden)
        if ok:
            # La estacion sabe que el carro va a moverse (ella le mando la
            # orden): no le suelta un vaso hasta que diga que volvio al muelle.
            if orden.get("accion") != "detener":
                self._estado_carro["en_muelle"] = False
            # Si la corrida ya habia terminado, sigue para que el carro se mueva.
            self.terminado = False
        return ok, detalle

    def sabotaje_cortar_radio(self) -> bool:
        """Punto 15: se corta la radio del carro (se ve que termina la vuelta,
        guarda sus mensajes y al volver no le cargan otro vaso a ciegas)."""
        if self.carro is None or not self.radio_carro_conectada:
            return False
        self.radio_carro_conectada = False
        return True

    def sabotaje_reconectar_radio(self) -> bool:
        if self.carro is None or self.radio_carro_conectada:
            return False
        self.radio_carro_conectada = True
        return True

    def cerrar(self) -> None:
        """Cierra el mundo propio del carro (el de la planta es de la escena)."""
        if self.carro is not None:
            self.carro.cerrar()
            self.carro = None

    def sabotaje_vaso_con_contenido(self) -> bool:
        """El proximo vaso que ponga el operador trae algo adentro. Por fuera
        se ve igual (vaso opaco); lo detecta en la verificacion el sensor que
        mira al interior del vaso."""
        self._proximo_vaso_con_objeto = True
        return True

    def _revisar_alarmas(self) -> None:
        """Avisos para el operador. Un tubo lleno sin vaso donde soltarlo NO
        bota monedas: la moneda espera en E4 y la cinta de monedas se detiene
        hasta que llegue un vaso (los vasos son genericos: la denominacion la
        decide el tubo que se abre sobre el). Aqui solo se avisa, para que el
        operador ponga vasos o despeje la cortina."""
        activas = set()
        # Esperar al carrusel es normal (no es alarma): solo el tubo lleno lo es.
        if self._moneda_en_espera is not None and self._motivo_espera == "tubo_lleno":
            activas.add("tubo_lleno")
        hay_lote = self.almacen.lote_listo(self.monedas_por_vaso, aceptar_parciales=self.embalar_parciales)
        id_llenado = self._vaso_en(ESTACION_LLENADO_VASOS)
        vaso_util = id_llenado is not None and self.embalaje.registro.obtener(id_llenado).estado == EstadoVaso.VALIDA
        self._ticks_sin_vaso = self._ticks_sin_vaso + 1 if hay_lote is not None and not vaso_util else 0
        if self._ticks_sin_vaso >= 3:
            activas.add("faltan_vasos")
        for alarma in activas - self._alarmas:
            self._evento("operador", "alarma", tipo=alarma, cortina=self.embalaje.cortina_activa)
        self._alarmas = activas

    def sabotaje_poner_intruso(self) -> bool:
        if self._intruso is not None:
            return False
        # A mitad de camino entre tapa y prensa (ver docstring de
        # `EscenaEstacion.crear_intruso` para el porque del 0.5), a media
        # altura del vaso: ahi esta el haz de la cortina.
        self._intruso = self.escena.crear_intruso(casilla_vasos=ESTACION_TAPA_VASOS + 0.5, altura_mano_m=0.065)
        return True

    def sabotaje_quitar_intruso(self) -> bool:
        if self._intruso is None:
            return False
        self.escena.quitar_intruso(self._intruso)
        self._intruso = None
        return True

    # ------------------------------------------------------------------
    # estado para el dashboard (telemetria, `t: tel` en la seccion 10.1)
    # ------------------------------------------------------------------

    def estado_carrusel(self) -> dict:
        """Donde queda el carrusel al terminar este ciclo (`llega_en_ms`: lo que
        le falta a su giro desde ese instante)."""
        t = self.ticks * self._ciclo_ms
        return dict(self.carrusel.estado(t), soltando_lote=self._embalado is not None
                    or t < self._carrusel_ocupado_hasta, cola=len(self._cola_carga))

    def estado(self) -> dict:
        casillas_monedas = [None] * NUM_ESTACIONES_MONEDAS
        for id_registro, casilla in self._fantasmas.items():
            if casilla < NUM_ESTACIONES_MONEDAS:
                r = self.linea.registro.obtener(id_registro)
                casillas_monedas[casilla] = {"id": id_registro, "tipo": "vacia_registrada", "clase_real": None,
                                             "diametro_mm": 0, "metal": r.metal, "clase": None, "confianza": None,
                                             "causa": r.causa, "aceptada": r.aceptada}
        for elemento in self.escena.elementos_monedas:
            if not elemento.activo:
                continue
            r = self.linea.registro.obtener(elemento.id_registro)
            casillas_monedas[elemento.casilla] = {
                "id": elemento.id_registro,
                "tipo": elemento.tipo,
                "apariencia": elemento.apariencia,
                "contornos_internos": elemento.contornos_internos,
                "clase_real": elemento.clase_real,
                "diametro_mm": elemento.diametro_mm,
                "metal": r.metal,
                "clase": r.clase,
                "confianza": r.confianza,
                "causa": r.causa,
                "aceptada": r.aceptada,
            }

        casillas_vasos = [None] * NUM_ESTACIONES_VASOS
        for id_vaso, (elemento, casilla) in self._vasos.items():
            if 0 <= casilla < NUM_ESTACIONES_VASOS:
                r = self.embalaje.registro.obtener(id_vaso)
                casillas_vasos[casilla] = {
                    "id": id_vaso,
                    "estado": r.estado.value,
                    "cantidad": r.cantidad_monedas,
                    "valor": r.valor_total,
                    "masa_g": round(r.masa_estimada_g, 2),
                    "denominacion": r.denominacion,
                    "marcador": elemento.marcador if elemento is not None else None,
                    "fisico": "ausente" if elemento is None else (
                        "figura" if elemento.altura_mm != 90.0 else "vaso"),
                }

        # Lo que la camara de vasos ve ahora en cada una de sus 3 estaciones.
        zonas_vasos = {}
        for nombre, zona, casilla in (("verificacion", self.backend.zona_verificacion, ESTACION_VERIFICACION_VASOS),
                                      ("llenado", self.backend.zona_llenado, ESTACION_LLENADO_VASOS),
                                      ("tapa", self.backend.zona_tapa, ESTACION_TAPA_VASOS),
                                      ("prensa", self.backend.zona_prensa, ESTACION_PRENSA_VASOS)):
            media, borde = zona.leer()
            zonas_vasos[nombre] = {"presencia": zona.presencia.leer(), "media": media, "borde": borde,
                                   "marcador": self.backend.camara_vasos.marcador_en(casilla),
                                   "tapa": self.backend.camara_vasos.tapa_en(casilla)}
        return {
            "tick": self.ticks,
            "terminado": self.terminado,
            "pendientes": len(self._pendientes),
            "moneda_en_espera": self._moneda_en_espera is not None,
            "motivo_espera": self._motivo_espera if self._moneda_en_espera is not None else None,
            # Donde queda el carrusel al terminar este ciclo (llega_en_ms: lo
            # que le falta a su giro desde ese instante).
            "carrusel": self.estado_carrusel(),
            "cortina_activa": self.embalaje.cortina_activa,
            "intruso": self._intruso is not None,
            "mano_sacando": self._mano_temporal[2] if self._mano_temporal is not None else None,
            "mano_altura": self._mano_temporal[3] if self._mano_temporal is not None else None,
            "alarmas": sorted(self._alarmas),
            "canaleta": list(self.canaleta),
            "carro": (dict(self.carro.estado(), vaso_id=self._vaso_en_carro,
                           radio={"conectada": self.radio_carro_conectada, "enlace": self._oye_estacion.vivo(self._t_ms),
                                  "en_espera": len(self._emisor_carro.pendientes),
                                  "cuna_reportada": self._estado_carro["cuna"]})
                      if self.carro is not None else None),
            "vaso_esperando_canaleta": self._vaso_esperando_canaleta,
            "posicion_cintas": {"monedas": not self.backend.posicion_monedas.desfasada,
                                "vasos": not self.backend.posicion_vasos.desfasada},
            "tapas_restantes": self.backend.dispensador_tapas.reserva,
            "ciclos_prensa": self.backend.prensa.ciclos,
            "casillas_monedas": casillas_monedas,
            "casillas_vasos": casillas_vasos,
            # copias: quien guarda varios estados (la demo) no debe ver
            # todos iguales al final porque comparten la misma lista
            "salidas": {k: list(v) for k, v in self.salidas.items()},
            "vasos_salida": [dict(v) for v in self.vasos_salida],
            "lecturas_tick": dict(self._lecturas),
            "almacen": {**{str(d): n for d, n in self.almacen.contenido().items()},
                        OTRAS: self.almacen.cantidad_otras()},
            "almacen_valor": self.almacen.valor_total(),
            "capacidad_tubo": self.almacen.capacidad,
            "embalar_parciales": self.embalar_parciales,
            "errores_filtrado": {k: len(v) for k, v in self.errores_filtrado.items()},
            "desfases_cinta": dict(self.desfases),
            "errores_sensores_activos": self.backend.errores_activos,
            "sensores": {
                "presencia": self.backend.sensor_presencia.leer(),
                "capacitivo": self.backend.sensor_capacitivo.leer(),
                "inductivo": self.backend.sensor_inductivo.leer(),
                "cortina": self.backend.sensor_cortina.leer(),
                "camara_vasos": any(z["presencia"] for z in zonas_vasos.values()),
                "sensor_interior": self.backend.sensor_interior.leer(),
                "hall_carrusel": self.backend.sensor_hall_carrusel.leer(),
            },
            # Alarma de la camara de vasos: algo mas alto que un vaso en alguna
            # de sus estaciones (la franja de borde ocupada).
            "camara_vasos_alarma": any(z["borde"] for z in zonas_vasos.values()),
            "camara_vasos_zonas": zonas_vasos,
        }
