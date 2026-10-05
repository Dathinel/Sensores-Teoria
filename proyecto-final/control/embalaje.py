"""Maquina de estados de la cinta de vasos (docs/especificacion.md, seccion 5, pasos 9 a
14, y seccion 7 tabla de estados).

Codigo puro, igual que `linea.py`. Cada estacion relee sus sensores antes
de actuar y puede degradar el estado a INVALIDA en cualquier momento; nadie
confia en lo que dijo una estacion anterior. El "no hay paro de linea, solo
un salto de casilla" del paso 10 lo resuelve el llamador: `intentar_llenar`
devuelve False cuando la casilla no se puede llenar, y quien orquesta las
dos cintas es responsable de avanzar a la siguiente casilla valida.
"""

from .registro import CasillaVaso, EstadoVaso, RegistroCasillas, registro_vasos


class EmbalajeVasos:
    def __init__(self):
        self.registro: RegistroCasillas[CasillaVaso] = registro_vasos()
        # Paso 14: mientras esta activa, tapa/prensa/empujador quedan
        # congelados pero la cinta de monedas sigue funcionando (eso lo
        # decide el orquestador, no esta clase).
        self.cortina_activa = False

    @staticmethod
    def _vaso_valido(media_bloqueada: bool, borde_libre: bool) -> bool:
        """Paso 9: franja de media altura ocupada Y franja de borde libre
        (las dos "barreras virtuales" de la camara de vasos). Cualquier otra
        combinacion es invalida."""
        return media_bloqueada and borde_libre

    def verificar_antes_de_llenado(
        self, indice: int, *, presente: bool, media_bloqueada: bool, borde_libre: bool,
        marcador: int | None = None, objeto_adentro: bool = False,
    ) -> CasillaVaso:
        """Paso 9, antes del llenado. `marcador` es el numero ArUco que leyo la
        camara de vasos (None si no lo pudo leer): queda registrado para
        compararlo en el llenado y en la tapa. `objeto_adentro`: el sensor que
        mira al interior del vaso vio algo; un vaso que ya trae algo no entra
        (cada vaso arranca de cero; los vasos son opacos)."""
        casilla = self.registro.obtener(indice)
        casilla.marcador = marcador
        if not presente:
            casilla.degradar(EstadoVaso.VACIA)
        elif objeto_adentro:
            casilla.degradar(EstadoVaso.INVALIDA)
        elif self._vaso_valido(media_bloqueada, borde_libre):
            casilla.degradar(EstadoVaso.VALIDA)
        else:
            casilla.degradar(EstadoVaso.INVALIDA)
        return casilla

    def intentar_llenar(self, indice: int, *, valor: int, masa_g: float, denominacion: int | None = None) -> bool:
        """Paso 10. Si la casilla esta vacia o invalida no se llena: el
        llamador debe saltar a la siguiente casilla valida en vez de
        detener la cinta de monedas. Si el vaso ya tiene monedas de otra
        denominacion tampoco: un vaso = una sola denominacion."""
        casilla = self.registro.obtener(indice)
        if casilla.estado not in (EstadoVaso.VALIDA, EstadoVaso.LLENANDO):
            return False
        if denominacion is not None and casilla.denominacion not in (None, denominacion):
            return False
        casilla.degradar(EstadoVaso.LLENANDO)
        if denominacion is not None:
            casilla.denominacion = denominacion
        casilla.acumular_moneda(valor, masa_g)
        return True

    def llenar_lote(self, indice: int, *, denominacion: int, monedas: list[tuple[int, float]]) -> bool:
        """Descarga de un lote completo de UNA denominacion (desde su tubo
        del almacen) en un vaso VALIDO y VACIO, que queda LLENO. Si el vaso
        no es valido o ya tiene algo, no se echa nada: las monedas siguen
        guardadas en el tubo, nunca se pierden."""
        casilla = self.registro.obtener(indice)
        if casilla.estado != EstadoVaso.VALIDA or casilla.cantidad_monedas > 0 or not monedas:
            return False
        for valor, masa_g in monedas:
            self.intentar_llenar(indice, valor=valor, masa_g=masa_g, denominacion=denominacion)
        self.cerrar_llenado(indice)
        return True

    def cerrar_llenado(self, indice: int) -> None:
        """Marca la casilla como LLENA cuando el embudo ya no le va a
        aportar mas monedas en este ciclo."""
        casilla = self.registro.obtener(indice)
        if casilla.estado == EstadoVaso.LLENANDO:
            casilla.degradar(EstadoVaso.LLENA)

    @staticmethod
    def es_el_mismo_vaso(casilla: CasillaVaso, marcador_leido: int | None) -> bool:
        """False solo si hay DOS lecturas y no coinciden (vaso cambiado por
        otro igual). Si alguna no se pudo leer, no hay evidencia de cambio: se
        decide solo con la silueta (y queda registrado en los eventos)."""
        return casilla.marcador is None or marcador_leido is None or casilla.marcador == marcador_leido

    def tapar(
        self, indice: int, *, presente: bool, media_bloqueada: bool, borde_libre: bool,
        marcador: int | None = None,
    ) -> bool:
        """Paso 11. No se confia en el estado registrado antes: se repite
        la verificacion en este instante. Si el vaso fue retirado o
        cambiado, no se suelta tapa. Congelado si la cortina esta activa.
        Un vaso vacio no se tapa ni se prensa: se desecha en la descarga
        (grupo, 2026-09-25: la cinta queda libre y cada corrida arranca de
        cero)."""
        if self.cortina_activa:
            return False
        casilla = self.registro.obtener(indice)
        if casilla.estado != EstadoVaso.LLENA:
            return False
        if not presente or not self._vaso_valido(media_bloqueada, borde_libre) \
                or not self.es_el_mismo_vaso(casilla, marcador):
            casilla.degradar(EstadoVaso.INVALIDA)
            return False
        casilla.degradar(EstadoVaso.TAPADA)
        return True

    def prensar(self, indice: int) -> bool:
        """Paso 12. La leva y el resorte que limita la fuerza son detalle
        mecanico; aqui solo se valida que haya una tapa que prensar.
        Congelado si la cortina esta activa."""
        if self.cortina_activa:
            return False
        casilla = self.registro.obtener(indice)
        return casilla.estado == EstadoVaso.TAPADA

    def descargar(self, indice: int) -> str:
        """Paso 13. Devuelve 'entrega' si el vaso llega tapado, 'vacio' si es
        un vaso valido que nunca recibio monedas (se desecha: no se tapa ni se
        prensa) o 'rechazo' en cualquier otro caso. Los dos ultimos no se
        empujan: la cinta los deja caer por su extremo a la bandeja. El
        empujador queda congelado si la cortina esta activa: el llamador
        debe reintentar mas tarde."""
        if self.cortina_activa:
            raise RuntimeError("cortina de seguridad activa: el empujador esta congelado")
        casilla = self.registro.obtener(indice)
        if casilla.estado == EstadoVaso.TAPADA:
            casilla.degradar(EstadoVaso.ENTREGADA)
            return "entrega"
        if casilla.estado == EstadoVaso.VALIDA and casilla.cantidad_monedas == 0:
            # Vaso bueno al que no le cayo ningun lote: se desecha (no es un
            # rechazo por sabotaje; queda contado aparte por el destino
            # "vacio" del evento `descarga`). Su estado pasa a RECHAZADA: antes
            # quedaba VALIDA ("listo para llenar") en la tabla `vasos` aunque ya
            # estaba en la bandeja, y el dashboard y el asistente lo contaban
            # como un vaso que todavia se podia llenar.
            casilla.degradar(EstadoVaso.RECHAZADA)
            return "vacio"
        casilla.degradar(EstadoVaso.RECHAZADA)
        return "rechazo"

    def activar_cortina(self) -> None:
        """Paso 14: algo mas alto que un vaso (p. ej. una mano) invadio la
        zona de tapa y prensa."""
        self.cortina_activa = True

    def despejar_cortina(self) -> None:
        """Al despejarse, la linea retoma donde iba; no hay reset de estado."""
        self.cortina_activa = False
