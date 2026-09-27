"""Interfaces abstractas de la capa de abstraccion de hardware (HAL).

`control/` no importa PyBullet, pyserial ni OpenCV directamente (CLAUDE.md,
seccion 17). Todo acceso a sensores o actuadores pasa por estas interfaces;
las implementaciones concretas viven en `backend_sim.py` (fase 3, traduce a
PyBullet) y `backend_real.py` (fase 8, traduce a mensajes seriales hacia el
ESP32). Si algo en `control/` necesita hardware o percepcion y no hay un
metodo aqui que lo cubra, falta agregarlo a esta interfaz, no importar la
libreria directamente.
"""

from abc import ABC, abstractmethod
from typing import Any


class SensorDiscreto(ABC):
    """Sensor de todo/nada: infrarrojo de presencia, barrera de vaso,
    capacitivo, inductivo, cortina de seguridad."""

    @abstractmethod
    def leer(self) -> bool:
        """True si el sensor esta activo/bloqueado en este instante."""


class SensorDistancia(ABC):
    """Sensor de distancia continua: ultrasonico del vehiculo, cortina de
    seguridad si se implementa por distancia en vez de por umbral."""

    @abstractmethod
    def leer_mm(self) -> float:
        """Distancia medida, en milimetros."""


class Camara(ABC):
    @abstractmethod
    def capturar(self) -> Any:
        """Devuelve una imagen. El tipo concreto (array de OpenCV, render de
        PyBullet) lo define cada backend; la capa de control nunca lo abre,
        solo se la pasa al pipeline de vision."""


class BandaIndexada(ABC):
    """Cinta transportadora indexada: modo avanzar y detener (seccion 4)."""

    @abstractmethod
    def avanzar_casilla(self) -> None:
        """Avanza exactamente una casilla y respeta la pausa configurada
        antes de devolver el control."""

    @property
    @abstractmethod
    def casilla_actual(self) -> int:
        """Indice de la casilla que quedo bajo la estacion de referencia."""


class Servo(ABC):
    """Paleta de expulsion, escape de tapas, empujador de descarga."""

    @abstractmethod
    def activar(self) -> None:
        """Ejecuta el movimiento y vuelve a la posicion de reposo."""


class MotorPrensa(ABC):
    @abstractmethod
    def ciclo(self) -> None:
        """Una vuelta completa de la leva excentrica con la cinta detenida."""

    @abstractmethod
    def subir(self) -> None:
        """Cortina activa: lleva la leva a 0 grados (piston ARRIBA, lejos del
        vaso), aunque este a mitad de un ciclo, y la deja ahi detenida."""


class DispensadorTapas(ABC):
    @abstractmethod
    def soltar_tapa(self) -> bool:
        """Suelta una tapa por gravedad. False si el tubo vertical esta vacio."""
