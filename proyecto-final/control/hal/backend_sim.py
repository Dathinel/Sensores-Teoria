"""Backend `sim` de la HAL (CLAUDE.md, seccion 8).

Traduce cada interfaz abstracta de `control/hal/interfaces.py` a comandos
sobre `sim/mundo.py`, `sim/sensores_sim.py`. Junto con
el resto de `sim/`, este es el unico lugar del paquete `control` al que se
le permite importar PyBullet (regla 17 de `CLAUDE.md`: la prohibicion es
para la logica de control pura -- `linea.py`, `embalaje.py`, `reglas.py`,
`registro.py`, `monedas.py` -- no para el backend que la conecta con un
mundo concreto).

`EstacionBackendSim` agrupa los sensores y actuadores de las 7 estaciones
de la cinta de monedas y las 5 de la cinta de vasos sobre una escena ya
construida. Quien la usa es la planta (`sim/planta.py`), que la
conecta con `control/linea.py` y `control/embalaje.py` sin que ninguno de
los dos conozca a PyBullet.
"""

from __future__ import annotations

from dataclasses import dataclass

from sim import sensores_sim
from sim.sensores_sim import CamaraOraculo
from sim.mundo import (
    ESTACION_DESCARGA_VASOS,
    ESTACION_LLENADO_VASOS,
    ESTACION_MATERIAL_MONEDAS,
    ESTACION_PRENSA_VASOS,
    ESTACION_PRESENCIA_MONEDAS,
    ESTACION_TAPA_VASOS,
    ESTACION_VERIFICACION_VASOS,
    EscenaEstacion,
)

from .interfaces import BandaIndexada, DispensadorTapas, MotorPrensa, Servo


class BandaIndexadaSim(BandaIndexada):
    def __init__(self, escena: EscenaEstacion, cinta: str):
        if cinta not in ("monedas", "vasos"):
            raise ValueError("cinta debe ser 'monedas' o 'vasos'")
        self._escena = escena
        self._cinta = cinta
        self._casilla_actual = 0

    def avanzar_casilla(self) -> None:
        if self._cinta == "monedas":
            self._escena.avanzar_casilla_monedas()
        else:
            self._escena.avanzar_casilla_vasos()
        self._casilla_actual += 1

    @property
    def casilla_actual(self) -> int:
        return self._casilla_actual


class ServoEmpujadorVasosSim(Servo):
    """Descarga de la ultima casilla de la cinta de vasos. Con destino
    "entrega" es el empujador (servo) que pasa el vaso de lado a la canaleta;
    con destino "rechazo" NO hay otro actuador: la cinta sigue avanzando y el
    vaso cae por el extremo a la bandeja de rechazo (un solo empujador no
    puede empujar hacia los dos lados)."""

    def __init__(self, escena: EscenaEstacion, destino: str):
        self._escena = escena
        self._destino = destino

    def activar(self) -> None:
        for elemento in self._escena.elementos_vasos:
            if elemento.activo and elemento.casilla == ESTACION_DESCARGA_VASOS:
                self._escena.activar_empujador_vasos(elemento, self._destino)
                return


class MotorPrensaSim(MotorPrensa):
    """La leva excentrica todavia no tiene un cuerpo fisico propio en el
    URDF de la cinta de vasos (se documento como pendiente al cerrar la
    fase 2): asentar la tapa a presion no cambia nada observable en la
    escena mas alla de lo que ya decide `control/embalaje.py`. Este
    backend lleva la cuenta de ciclos y cuantas veces se mando a subir por
    la cortina, suficiente para que la logica de control pueda operar y
    probarse."""

    def __init__(self):
        self.ciclos = 0
        self.subidas = 0

    def ciclo(self) -> None:
        self.ciclos += 1

    def subir(self) -> None:
        self.subidas += 1


class DispensadorTapasSim(DispensadorTapas):
    """Mismo caso que la prensa: el tubo vertical de tapas todavia no es
    un cuerpo fisico. Se modela como una reserva contable, suficiente para
    poder probar el caso 'tubo vacio' sin haber modelado el tubo."""

    def __init__(self, reserva: int = 1000):
        self.reserva = reserva

    def soltar_tapa(self) -> bool:
        if self.reserva <= 0:
            return False
        self.reserva -= 1
        return True


@dataclass
class ZonaCamaraVasos:
    """Lo que la camara de vasos mide en UNA estacion (verificacion, llenado
    o tapa): presencia de algo en la casilla y la silueta en dos franjas de
    la imagen, media altura y justo por encima del borde (seccion 5, paso 9:
    media ocupada y borde libre = vaso). Son "barreras virtuales": la misma
    decision que tomaban las barreras IR, sin ningun sensor fisico aparte."""

    presencia: sensores_sim.SensorMaterial
    media_altura: sensores_sim.SensorRayo
    borde: sensores_sim.SensorRayo

    def leer(self) -> tuple[bool, bool]:
        return self.media_altura.leer(), self.borde.leer()

    def sensores(self) -> tuple:
        return self.presencia, self.media_altura, self.borde


class EstacionBackendSim:
    """Backend `sim` completo de una escena ya construida: agrupa bandas,
    servos, sensores discretos, el par capacitivo/inductivo, la camara de
    vasos, la cortina de seguridad y la camara de monedas en modo oraculo."""

    def __init__(self, escena: EscenaEstacion, *, camara: CamaraOraculo | None = None,
                 cortina: dict | None = None, vasos: dict | None = None):
        if cortina is None or vasos is None:
            # config/parametros.yaml: cortina_seguridad (altura, cono y desplazamiento
            # del VL53L0X) y vasos (las dos franjas de la camara de vasos).
            import yaml
            from pathlib import Path
            ruta = Path(__file__).resolve().parents[2] / "config" / "parametros.yaml"
            cfg = yaml.safe_load(ruta.read_text(encoding="utf-8"))
            cortina = cortina or cfg["cortina_seguridad"]
            vasos = vasos or cfg["vasos"]
        # Auditoria 2026-09-28: estaban escritas a mano (0.5 y 1.05) aunque el comentario de
        # abajo decia que venian de la configuracion.
        media_frac, borde_frac = vasos["barrera_media_altura_frac"], vasos["barrera_borde_altura_frac"]
        self.escena = escena
        self.camara = camara or CamaraOraculo()
        self.errores_activos = False

        self.banda_monedas = BandaIndexadaSim(escena, "monedas")
        self.banda_vasos = BandaIndexadaSim(escena, "vasos")

        self.servo_empujador_entrega = ServoEmpujadorVasosSim(escena, "entrega")
        self.salida_fin_de_cinta = ServoEmpujadorVasosSim(escena, "rechazo")

        self.prensa = MotorPrensaSim()
        self.dispensador_tapas = DispensadorTapasSim()

        # Estacion 1 (presencia) y estacion 2 (material) de la cinta de
        # monedas son posiciones fijas en el espacio. Los dos sensores de
        # material van DEBAJO de la cinta, cada uno centrado bajo su casilla:
        # el capacitivo bajo E1 (su lectura viaja en el registro de la
        # casilla) y el inductivo bajo E2, donde se decide el material. Una
        # moneda de 17 mm no tapa dos caras de 18 mm a la vez.
        self.sensor_presencia = sensores_sim.sensor_presencia_monedas(escena, ESTACION_PRESENCIA_MONEDAS)
        self.sensor_capacitivo = sensores_sim.sensor_capacitivo(escena, ESTACION_PRESENCIA_MONEDAS)
        self.sensor_inductivo = sensores_sim.sensor_inductivo(escena, ESTACION_MATERIAL_MONEDAS)

        # Camara de vasos (una sola webcam con panel de luz detras): ve
        # verificacion, llenado y tapa a la vez. Reemplaza a las 6 barreras
        # IR y a los 2 sensores de presencia de vasos que habia antes (grupo,
        # 2026-09-25). altura_frac del borde > 1.0 a proposito: ver
        # config/parametros.yaml (vasos.barrera_borde_altura_frac).
        def zona(casilla: int) -> ZonaCamaraVasos:
            return ZonaCamaraVasos(
                presencia=sensores_sim.presencia_silueta_vasos(escena, casilla),
                media_altura=sensores_sim.franja_silueta_vaso(escena, casilla, altura_frac=media_frac),
                borde=sensores_sim.franja_silueta_vaso(escena, casilla, altura_frac=borde_frac),
            )

        self.zona_verificacion = zona(ESTACION_VERIFICACION_VASOS)
        self.zona_llenado = zona(ESTACION_LLENADO_VASOS)
        self.zona_tapa = zona(ESTACION_TAPA_VASOS)
        # Grupo (2026-09-25): la camara tambien ve la prensa (4 casillas):
        # antes de prensar y despues de que se despeja la cortina se revisa
        # que el vaso siga ahi.
        self.zona_prensa = zona(ESTACION_PRENSA_VASOS)
        self.camara_vasos = sensores_sim.CamaraVasos(escena)
        # Punto 11 (usuario, 2026-09-26): la misma camara vigila la zona por
        # donde cae el lote al vaso de llenado (la cortina cubre tapa y prensa).
        self.intrusion_llenado = sensores_sim.zona_intrusion_llenado(escena, ESTACION_LLENADO_VASOS)
        # Posicion de cada cinta medida por su camara (reemplaza a los
        # sensores de ranura; ver sensores_sim.PosicionCintaCamara).
        self.posicion_monedas = sensores_sim.PosicionCintaCamara()
        self.posicion_vasos = sensores_sim.PosicionCintaCamara()

        # Sensor que mira al interior del vaso en la verificacion (vasos
        # opacos: el vaso tiene que llegar vacio).
        self.sensor_interior = sensores_sim.SensorInteriorVaso(escena, ESTACION_VERIFICACION_VASOS)
        # Referencia del carrusel del almacen (homing del motor paso a paso).
        self.sensor_hall_carrusel = sensores_sim.SensorHallCarrusel()
        # Infrarrojo de la cuna del carro (punto 13): confirma que el vaso
        # soltado por el escape quedo en la cuna.
        self.sensor_cuna = sensores_sim.SensorCunaCarro()

        # Cortina de seguridad: cubre desde la estacion de tapa hasta la
        # de prensa (paso a paso, punto 11), un solo VL53L0X con su cono.
        self.sensor_cortina = sensores_sim.sensor_cortina(
            escena, ESTACION_TAPA_VASOS, ESTACION_PRENSA_VASOS,
            altura_mm=cortina["altura_mm"], angulo_cono_grados=cortina["angulo_cono_grados"],
            desplazamiento_lateral_m=cortina["desplazamiento_lateral_mm"] / 1000)

    def aplicar_errores(self, errores: dict, semilla: int | None = None,
                        errores_actuadores: dict | None = None) -> None:
        """Le pone a cada sensor su error individual (config/parametros.yaml,
        bloque errores_sensores). Un solo generador con semilla fija: la
        misma corrida da el mismo resultado. Sin llamar a esto, los sensores
        son perfectos (lo que usan las pruebas automaticas)."""
        import random

        rng = random.Random(semilla)

        def configurar(sensores, clave):
            e = errores.get(clave, {})
            for sensor in sensores:
                sensor.configurar_error(e.get("falso_negativo", 0.0), e.get("falso_positivo", 0.0), rng)

        configurar([self.sensor_presencia], "presencia")
        configurar([self.sensor_capacitivo], "capacitivo")
        configurar([self.sensor_inductivo], "inductivo")
        configurar([sensor for z in (self.zona_verificacion, self.zona_llenado, self.zona_tapa, self.zona_prensa)
                    for sensor in z.sensores()], "camara_vasos")
        configurar([self.sensor_cortina], "cortina")
        configurar([self.intrusion_llenado], "camara_vasos")
        configurar([self.posicion_monedas, self.posicion_vasos], "posicion_camara")
        configurar([self.sensor_cuna], "cuna")
        self.camara_vasos.probabilidad_no_lee = errores.get("camara_vasos", {}).get("no_lee", 0.0)
        self.camara_vasos.probabilidad_no_ve_tapa = errores.get("camara_vasos", {}).get("no_ve_tapa", 0.0)
        configurar([self.sensor_interior], "sensor_interior")
        self.camara_vasos.rng = rng
        desfase = (errores_actuadores or {}).get("cinta", {}).get("desfase", 0.0)
        for posicion in (self.posicion_monedas, self.posicion_vasos):
            posicion.probabilidad_desfase = desfase
        c = errores.get("camara", {})
        self.camara.ruido_diametro_mm = c.get("ruido_diametro_mm", 0.0)
        self.camara.ruido_circularidad = c.get("ruido_circularidad", 0.0)
        self.camara.probabilidad_error = max(self.camara.probabilidad_error, c.get("probabilidad_error_clase", 0.0))
        self.camara.probabilidad_confusion = c.get("probabilidad_confusion_clase", 0.0)
        self.camara.rng = rng
        self.errores_activos = True
