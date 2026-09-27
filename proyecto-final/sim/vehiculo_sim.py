"""Carro en PyBullet con fisica real (paso a paso, punto 14).

Mundo PROPIO (otro cliente de PyBullet, separado de la planta): piso, los
tres muros, el muelle de carga con sus guias en V y sus topes, y el carro:
chasis, dos ruedas motrices con motor (control de velocidad con torque
limitado, como un motorreductor TT), rueda loca de bola (sin roce) y el
vaso colgado de la cuna, que puede cabecear sobre los rieles entre la
espuma de adelante y la lengueta de atras. Nada se mueve "a mano": el carro
avanza porque sus ruedas empujan el piso, esquiva porque el control
(control/vehiculo.py) decide a partir de lo que leen sus sensores, y entra
al muelle porque las guias lo empujan y el tope lo para.

Sensores emulados, con su error (config: errores_sensores.carro):

- 5 infrarrojos de linea: distancia del punto de cada sensor a la linea
  central de la pista (sim/pista.py), mas las dos franjas transversales
  (meta y marca de giro). A veces una lectura sale cambiada.
- Ultrasonico: abanico de 5 `rayTest` en +-7,5 grados (el HC-SR04 no es un
  rayo) a su altura real, con ruido.
- Encoders: disco de 20 ranuras: se cuentan pulsos enteros del giro REAL
  de cada rueda (si patina, cuenta de mas, como en la vida real).
- Cada motor gira un poco distinto al otro con el mismo pedido
  (`diferencia_motores`), fijo por corrida.
"""

from __future__ import annotations

import math
import random

import numpy as np
import pybullet as p
import pybullet_data

from control.vehiculo import ControlCarro, LecturaCarro
from sim.pista import generar_linea_central

G = 9.81
PASO_FISICA = 1 / 240
# Muelle: boca de las guias en V (mismas medidas en el visor). 4,5 cm de
# apertura en 20 cm: ~13 grados (con 9 cm quedaba a 27 y empujaba de lado).
LARGO_BOCA_MUELLE = 0.20
ABRE_BOCA_MUELLE = 0.045
HOLGURA_MUELLE = 0.003       # por lado: la cuna en embudo tolera ~+-5 mm
# Rodillos guia (rodamiento 623, 10 mm) en las esquinas traseras del chasis,
# un poco mas afuera que las llantas (84 mm): las guias del muelle empujan
# ESTOS, 5 cm detras del eje, y el carro gira hacia el centro al retroceder
# (como un carrito de supermercado). Si la guia empujara la llanta, justo en
# el eje, el carro no podria correrse de lado (la llanta se agarra al piso) y
# se trababa torcido: se vio en la simulacion (2026-09-26).

ROCE_PTFE = 0.12
# Torque maximo del motorreductor TT (~0,8 kg.cm) y con PWM bajo (entrada al
# muelle): con el bajo, el motor se ahoga contra el tope antes de que la
# llanta patine (hace falta ~0,09 N.m para que patine con el peso del carro).
TORQUE_MOTOR = 0.1
Z_TOF = 0.074  # altura del laser frontal, sobre el ultrasonico (el visor lo dibuja ahi)
TORQUE_BAJO = 0.035


class SimCarro:
    def __init__(self, parametros: dict, *, errores: bool = False, semilla: int | None = None):
        from sim.geometria import geometria_completa

        self.cfg = dict(parametros["vehiculo"])
        pista = parametros["pista"]
        self.cfg["_muro_largo_mm"] = pista["obstaculo_largo_mm"]
        self.cfg["_muro_grueso_mm"] = pista.get("obstaculo_grueso_mm", 30)
        geo = geometria_completa(parametros)
        s = geo["pista"]["salida"]
        self.salida = (s["x"], s["y"], s["rumbo"])
        self.linea = generar_linea_central(pista["tramos"], self.salida)
        self._lx = np.array([q.x for q in self.linea])
        self._ly = np.array([q.y for q in self.linea])
        self._ls = np.array([q.s for q in self.linea])
        self._lr = np.array([q.rumbo for q in self.linea])
        self.largo_linea = float(self._ls[-1])
        self.medio_ancho_linea = pista["ancho_linea_mm"] / 2000
        self.medio_ancho_pista = pista["ancho_mm"] / 2000
        self.s_giro = self.cfg["marca_giro_mm"] / 1000
        self.ancho_giro = self.cfg["franja_giro_ancho_mm"] / 1000
        self.ancho_meta = self.cfg["franja_meta_ancho_mm"] / 1000

        self.rng = random.Random(semilla)
        e = parametros.get("errores_sensores", {}).get("carro", {}) if errores else {}
        dif = e.get("diferencia_motores", 0.0)
        self.ganancia = (1 + self.rng.uniform(-dif, dif), 1 + self.rng.uniform(-dif, dif))
        self.ruido_us = e.get("ruido_ultrasonico_mm", 0.0) / 1000
        self.ruido_tof = e.get("ruido_tof", 0.0)
        self.error_linea = e.get("error_linea", 0.0)

        self.cli = p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.cli)
        p.setGravity(0, 0, -G, physicsClientId=self.cli)
        p.setTimeStep(PASO_FISICA, physicsClientId=self.cli)
        self.piso = p.loadURDF("plane.urdf", physicsClientId=self.cli)
        p.changeDynamics(self.piso, -1, lateralFriction=1.0, physicsClientId=self.cli)
        self.muros = [self._muro(o) for o in geo["pista"]["obstaculos"]]
        self.muelle = self._crear_muelle()
        self._crear_carro()

        # El trazado de la pista y el muelle son fijos y medidos: el control
        # los usa para las ordenes (ir a la meta, volver al muelle) y para
        # volver a poner su odometria en cero cada vez que entra al muelle.
        self.control = ControlCarro(self.cfg, largo_linea_m=self.largo_linea,
                                    linea=[(q.x, q.y, q.rumbo, q.s) for q in self.linea],
                                    pose_muelle=self.salida)
        n = max(1, round(1 / (self.cfg["control_hz"] * PASO_FISICA)))
        self.pasos_por_control = n
        self.dt_control = n * PASO_FISICA
        self.tiempo = 0.0
        self._giro_acum = [0.0, 0.0]
        self._ang_prev = [self._angulo_rueda(j) for j in self.juntas_ruedas]
        self.traza: list[tuple[float, float]] = []
        self.inclinacion_max_vaso = 0.0
        self.vaso_cargado = False
        self.toques_muro = 0
        self._proximo_us = 0.0
        self._distancia_us = None
        self._n_medida_us = 0
        self._proximo_tof = 0.0
        self._distancia_tof = None
        self._n_medida_tof = 0

    # ------------------------------------------------------------------
    # mundo
    # ------------------------------------------------------------------

    def _caja(self, pos_xy, rumbo, medio, *, z=None, color=(0.4, 0.4, 0.45, 1)):
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=medio, physicsClientId=self.cli)
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=medio, rgbaColor=color, physicsClientId=self.cli)
        return p.createMultiBody(0, col, vis, [pos_xy[0], pos_xy[1], medio[2] if z is None else z],
                                 p.getQuaternionFromEuler([0, 0, rumbo]), physicsClientId=self.cli)

    def _muro(self, o):
        # Delgado a lo largo de la pista, `largo` a lo ancho.
        medio = (self.cfg["_muro_grueso_mm"] / 2000, o["largo"] / 2, o["alto"] / 2)
        return self._caja((o["x"], o["y"]), o["rumbo"], medio, color=(0.6, 0.25, 0.2, 1))

    def _local_a_mundo(self, lx, ly, pose=None):
        x0, y0, r = pose or self.salida
        return x0 + lx * math.cos(r) - ly * math.sin(r), y0 + lx * math.sin(r) + ly * math.cos(r)

    def _crear_muelle(self) -> list[int]:
        """Mismas medidas que el visor (app/visor3d/visor.js, construirMuelle):
        guias en V por fuera de las ruedas y dos topes a los lados de la cola."""
        v = self.cfg
        largo, ancho, r = v["largo_mm"] / 1000, v["ancho_mm"] / 1000, v["diametro_rueda_mm"] / 2000
        # Las guias tocan los RODILLOS de las esquinas traseras, nunca las llantas.
        guia_y = (v["rodillo_guia_y_mm"] + v["rodillo_guia_radio_mm"]) / 1000 + HOLGURA_MUELLE
        alto, esp = 0.02, 0.006
        x_rueda = -0.18 * largo
        # Tramo recto desde la cola (ahi quedan los rodillos con el carro en
        # el muelle) hasta pasar las ruedas; despues la boca.
        x0, x1 = -largo / 2 - 0.004, x_rueda + r + 0.015
        x2 = x1 + LARGO_BOCA_MUELLE
        cuerpos = []
        r0 = self.salida[2]
        for lado in (-1, 1):
            cx, cy = self._local_a_mundo((x0 + x1) / 2, lado * (guia_y + esp / 2))
            cuerpos.append(self._caja((cx, cy), r0, ((x1 - x0) / 2, esp / 2, alto / 2), color=(0.22, 0.26, 0.31, 1)))
            ax, ay = x1, lado * (guia_y + esp / 2)
            bx, by = x2, lado * (guia_y + ABRE_BOCA_MUELLE + esp / 2)
            ang = math.atan2(by - ay, bx - ax)
            cx, cy = self._local_a_mundo((ax + bx) / 2, (ay + by) / 2)
            cuerpos.append(self._caja((cx, cy), r0 + ang, (math.hypot(bx - ax, by - ay) / 2, esp / 2, alto / 2),
                                      color=(0.22, 0.26, 0.31, 1)))
            xt = -largo / 2 - 0.006
            cx, cy = self._local_a_mundo(xt - 0.004, lado * 0.052)
            cuerpos.append(self._caja((cx, cy), r0, (0.007, 0.011, (r + 0.012) / 2), color=(0.9, 0.8, 0.4, 1)))
        # Guias forradas con cinta de PTFE: la llanta de goma RESBALA por la
        # guia y el carro se corre al centro. Con el plastico pelado la llanta
        # se agarra a la guia y el carro gira sobre si mismo en vez de
        # centrarse (se vio en la simulacion, 2026-09-26).
        for c in cuerpos:
            p.changeDynamics(c, -1, lateralFriction=ROCE_PTFE, physicsClientId=self.cli)
        return cuerpos

    def _crear_carro(self) -> None:
        v = self.cfg
        L, W, r = v["largo_mm"] / 1000, v["ancho_mm"] / 1000, v["diametro_rueda_mm"] / 2000
        self.radio = r
        x_eje = -0.18 * L
        y_rueda = W / 2 + 0.013
        cli = self.cli
        chasis_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[L / 2, W / 2, 0.012], physicsClientId=cli)
        chasis_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[L / 2, W / 2, 0.012],
                                         rgbaColor=(0.1, 0.16, 0.25, 1), physicsClientId=cli)
        rueda_col = p.createCollisionShape(p.GEOM_CYLINDER, radius=r, height=0.022, physicsClientId=cli)
        rueda_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=r, length=0.022, rgbaColor=(0.05, 0.05, 0.05, 1),
                                        physicsClientId=cli)
        bola_col = p.createCollisionShape(p.GEOM_SPHERE, radius=0.008, physicsClientId=cli)
        y_rod, r_rod = v["rodillo_guia_y_mm"] / 1000, v["rodillo_guia_radio_mm"] / 1000
        rodillo_col = p.createCollisionShape(p.GEOM_CYLINDER, radius=r_rod, height=0.01, physicsClientId=cli)
        # Vaso colgado: sin colision (no toca nada fuera de la cuna); su masa
        # queda 4,5 cm por debajo del eje de cabeceo, que esta en los rieles.
        z_riel = 0.132 - r
        vaso_vis = p.createVisualShape(p.GEOM_CYLINDER, radius=0.031, length=0.09, rgbaColor=(0.95, 0.95, 0.95, 1),
                                       visualFramePosition=[0, 0, -0.045], physicsClientId=cli)
        eje_y = p.getQuaternionFromEuler([math.pi / 2, 0, 0])
        x, y = self.salida[0], self.salida[1]
        self.carro = p.createMultiBody(
            baseMass=v["masa_kg"], baseCollisionShapeIndex=chasis_col, baseVisualShapeIndex=chasis_vis,
            basePosition=[x, y, r], baseOrientation=p.getQuaternionFromEuler([0, 0, self.salida[2]]),
            linkMasses=[0.05, 0.05, 0.01, 0.001, 0.004, 0.004],
            linkCollisionShapeIndices=[rueda_col, rueda_col, bola_col, -1, rodillo_col, rodillo_col],
            linkVisualShapeIndices=[rueda_vis, rueda_vis, -1, vaso_vis, -1, -1],
            linkPositions=[[x_eje, y_rueda, 0], [x_eje, -y_rueda, 0], [0.30 * L, 0, -(r - 0.008)], [-0.025, 0, z_riel],
                           [-L / 2 + 0.008, y_rod, 0.012 - r], [-L / 2 + 0.008, -y_rod, 0.012 - r]],
            linkOrientations=[eje_y, eje_y, [0, 0, 0, 1], [0, 0, 0, 1], [0, 0, 0, 1], [0, 0, 0, 1]],
            linkInertialFramePositions=[[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, -0.045], [0, 0, 0], [0, 0, 0]],
            linkInertialFrameOrientations=[[0, 0, 0, 1]] * 6,
            linkParentIndices=[0, 0, 0, 0, 0, 0],
            linkJointTypes=[p.JOINT_REVOLUTE, p.JOINT_REVOLUTE, p.JOINT_FIXED, p.JOINT_REVOLUTE, p.JOINT_FIXED,
                            p.JOINT_FIXED],
            linkJointAxis=[[0, 0, 1], [0, 0, 1], [0, 0, 0], [0, 1, 0], [0, 0, 0], [0, 0, 0]],
            physicsClientId=cli,
        )
        # Rueda 0 = izquierda (+y local), rueda 1 = derecha. El eje de la junta
        # quedo apuntando a -y: para avanzar, la junta gira en NEGATIVO
        # (ver `_motores`).
        self.juntas_ruedas = (0, 1)
        self.junta_vaso = 3
        for j in self.juntas_ruedas:
            p.changeDynamics(self.carro, j, lateralFriction=1.0, rollingFriction=0.0, physicsClientId=cli)
        p.changeDynamics(self.carro, 2, lateralFriction=0.0, rollingFriction=0.0, spinningFriction=0.0,
                         physicsClientId=cli)
        for j in (4, 5):   # los rodillos ruedan contra la guia: casi sin roce
            p.changeDynamics(self.carro, j, lateralFriction=0.02, physicsClientId=cli)
        # Soporte de 4 puntos a media altura (espuma adelante, lengueta atras,
        # guias a los costados): el vaso solo tiene el juego de ~1 mm de las
        # piezas, +-0,6 grados.
        p.changeDynamics(self.carro, self.junta_vaso, jointLowerLimit=-0.01, jointUpperLimit=0.01,
                         jointDamping=0.002, physicsClientId=cli)
        p.setJointMotorControl2(self.carro, self.junta_vaso, p.VELOCITY_CONTROL, targetVelocity=0, force=0.0005,
                                physicsClientId=cli)
        self.x_ir = L / 2 - 0.012
        self.sep_ir = v["separacion_sensores_linea_mm"] / 1000
        self.x_us = L / 2 + 0.002
        self.z_us = r + 0.004 + 0.02
        self._asentar()

    def _asentar(self) -> None:
        for _ in range(120):
            self._motores(0.0, 0.0)
            p.stepSimulation(physicsClientId=self.cli)

    # ------------------------------------------------------------------
    # sensores y motores
    # ------------------------------------------------------------------

    def pose(self) -> tuple[float, float, float]:
        pos, orn = p.getBasePositionAndOrientation(self.carro, physicsClientId=self.cli)
        return pos[0], pos[1], p.getEulerFromQuaternion(orn)[2]

    def _angulo_rueda(self, j) -> float:
        return p.getJointState(self.carro, j, physicsClientId=self.cli)[0]

    def _motores(self, v_izq: float, v_der: float) -> None:
        for j, v, g in ((0, v_izq, self.ganancia[0]), (1, v_der, self.ganancia[1])):
            # Eje de la junta hacia -y: avanzar es velocidad de junta negativa.
            p.setJointMotorControl2(self.carro, j, p.VELOCITY_CONTROL, targetVelocity=-v / self.radio * g,
                                    force=TORQUE_BAJO if self.control_pwm_bajo() else TORQUE_MOTOR,
                                    physicsClientId=self.cli)

    def control_pwm_bajo(self) -> bool:
        return getattr(self, "control", None) is not None and self.control.pwm_bajo

    def _linea(self, pose) -> tuple[int, ...]:
        bits = []
        for i in range(5):
            ly = (2 - i) * self.sep_ir
            x, y = self._local_a_mundo(self.x_ir, ly, pose)
            d2 = (self._lx - x) ** 2 + (self._ly - y) ** 2
            k = int(np.argmin(d2))
            tx, ty = math.cos(self._lr[k]), math.sin(self._lr[k])
            dx, dy = x - self._lx[k], y - self._ly[k]
            s = self._ls[k] + dx * tx + dy * ty
            lat = abs(-dx * ty + dy * tx)
            negro = False
            if 0 <= s <= self.largo_linea and lat < self.medio_ancho_linea:
                negro = True
            if lat < self.medio_ancho_pista and abs(s - self.s_giro) < self.ancho_giro / 2:
                negro = True
            if lat < self.medio_ancho_pista and self.largo_linea - self.ancho_meta <= s <= self.largo_linea:
                negro = True
            if self.error_linea and self.rng.random() < self.error_linea:
                negro = not negro
            bits.append(1 if negro else 0)
        return tuple(bits)

    def _ultrasonico(self, pose) -> float | None:
        x, y = self._local_a_mundo(self.x_us + 0.004, 0, pose)
        desde, hasta = [], []
        for grados in (-7.5, -3.75, 0, 3.75, 7.5):
            a = pose[2] + math.radians(grados)
            desde.append([x, y, self.z_us])
            hasta.append([x + 4 * math.cos(a), y + 4 * math.sin(a), self.z_us])
        mejor = None
        for r in p.rayTestBatch(desde, hasta, physicsClientId=self.cli):
            if r[0] in (-1, self.carro):
                continue
            d = r[2] * 4
            mejor = d if mejor is None else min(mejor, d)
        if mejor is None:
            return None
        mejor = max(0.02, mejor + self.rng.gauss(0, self.ruido_us)) if self.ruido_us else max(0.02, mejor)
        return mejor * 1000

    def _tof(self, pose) -> float | None:
        """Laser VL53L0X frontal (sobre el ultrasonico, a 7,4 cm del piso): cono
        de ~25 grados (5 rayos en +-12,5), hasta `tof_rango_max_mm`; ruido
        proporcional (+-3 %)."""
        alcance = self.cfg["tof_rango_max_mm"] / 1000
        x, y = self._local_a_mundo(self.x_us + 0.004, 0, pose)
        desde, hasta = [], []
        for grados in (-12.5, -6.25, 0, 6.25, 12.5):
            a = pose[2] + math.radians(grados)
            desde.append([x, y, Z_TOF])
            hasta.append([x + alcance * math.cos(a), y + alcance * math.sin(a), Z_TOF])
        mejor = None
        for r in p.rayTestBatch(desde, hasta, physicsClientId=self.cli):
            if r[0] in (-1, self.carro):
                continue
            d = r[2] * alcance
            mejor = d if mejor is None else min(mejor, d)
        if mejor is None:
            return None
        if self.ruido_tof:
            mejor *= 1 + self.rng.gauss(0, self.ruido_tof)
        return max(0.03, mejor) * 1000

    def _encoders(self) -> tuple[int, int]:
        paso = 2 * math.pi / self.cfg["encoder_pulsos_por_vuelta"]
        return int(self._giro_acum[0] / paso), int(self._giro_acum[1] / paso)

    def agregar_objeto(self, x: float, y: float, *, medio=(0.025, 0.025, 0.04)) -> int:
        """Un objeto mas en el piso (una caja, una mochila): para probar que el
        carro esquiva hacia el lado con MAS espacio. Cuenta como muro (si lo
        toca, suma en `toques_muro`)."""
        cuerpo = self._caja((x, y), 0.0, medio, color=(0.3, 0.5, 0.8, 1))
        self.muros.append(cuerpo)
        return cuerpo

    # ------------------------------------------------------------------
    # carga y descarga del vaso
    # ------------------------------------------------------------------

    # Con `sensor_cuna` (el infrarrojo de la cuna, sensor 12) el CONTROL del
    # carro decide solo que lo cargaron o que le sacaron el vaso (punto 15);
    # sin el, se le avisa directo (pruebas del carro solo).
    sensor_cuna = None

    def cargar_vaso(self) -> None:
        p.changeDynamics(self.carro, self.junta_vaso, mass=self.cfg["masa_vaso_lleno_kg"], physicsClientId=self.cli)
        self.vaso_cargado = True
        if self.sensor_cuna is not None:
            self.sensor_cuna.ocupada = True
        else:
            self.control.cargar()

    def retirar_vaso(self) -> None:
        p.changeDynamics(self.carro, self.junta_vaso, mass=0.001, physicsClientId=self.cli)
        self.vaso_cargado = False
        if self.sensor_cuna is not None:
            self.sensor_cuna.ocupada = False
        else:
            self.control.vaso_retirado()

    # ------------------------------------------------------------------
    # simular
    # ------------------------------------------------------------------

    def avanzar(self, segundos: float) -> list[dict]:
        """Corre `segundos` de simulacion (control a `control_hz`). Devuelve
        los eventos del control en ese lapso, con la pose del carro."""
        eventos = []
        fin = self.tiempo + segundos
        # Trayectoria de este lapso, una muestra cada 0,1 s: el visor la
        # reproduce a su ritmo real (el carro no "salta" de ciclo en ciclo).
        x, y, r = self.pose()
        self.camino = [(round(x, 4), round(y, 4), round(r, 4))]
        proxima_muestra = self.tiempo + 0.1
        while self.tiempo < fin - 1e-9:
            pose = self.pose()
            # El ultrasonico dispara cada `ultrasonico_periodo_ms`; entre disparos
            # el ESP32 sigue entregando la ultima medicion.
            if self.tiempo + 1e-9 >= self._proximo_us:
                self._distancia_us = self._ultrasonico(pose)
                self._n_medida_us += 1
                self._proximo_us = self.tiempo + self.cfg["ultrasonico_periodo_ms"] / 1000
            if self.tiempo + 1e-9 >= self._proximo_tof:
                self._distancia_tof = self._tof(pose)
                self._n_medida_tof += 1
                self._proximo_tof = self.tiempo + self.cfg["tof_periodo_ms"] / 1000
            lectura = LecturaCarro(self._linea(pose), self._distancia_us, *self._encoders(), self._n_medida_us,
                                   self._distancia_tof, self._n_medida_tof,
                                   self.sensor_cuna.leer() if self.sensor_cuna is not None else None)
            v_izq, v_der = self.control.paso(lectura, self.dt_control)
            self._motores(v_izq, v_der)
            for _ in range(self.pasos_por_control):
                p.stepSimulation(physicsClientId=self.cli)
                for i, j in enumerate(self.juntas_ruedas):
                    a = self._angulo_rueda(j)
                    self._giro_acum[i] += abs(a - self._ang_prev[i])
                    self._ang_prev[i] = a
            self.tiempo += self.dt_control
            if self.tiempo + 1e-9 >= proxima_muestra:
                x, y, r = self.pose()
                self.camino.append((round(x, 4), round(y, 4), round(r, 4)))
                proxima_muestra += 0.1
            incl = abs(p.getJointState(self.carro, self.junta_vaso, physicsClientId=self.cli)[0])
            if self.vaso_cargado:
                self.inclinacion_max_vaso = max(self.inclinacion_max_vaso, incl)
            for m in self.muros:
                if p.getContactPoints(self.carro, m, physicsClientId=self.cli):
                    self.toques_muro += 1
            if not self.traza or math.hypot(pose[0] - self.traza[-1][0], pose[1] - self.traza[-1][1]) > 0.02:
                self.traza.append((pose[0], pose[1]))
            for ev in self.control.eventos:
                x, y, r = self.pose()
                eventos.append({**ev, "x": round(x, 4), "y": round(y, 4), "t": round(self.tiempo, 2)})
            self.control.eventos.clear()
        return eventos

    def estado(self) -> dict:
        x, y, r = self.pose()
        odo = self.control.posicion_estimada()
        return {"x": round(x, 4), "y": round(y, 4), "rumbo": round(r, 4), "estado": self.control.estado,
                # Donde CREE el carro que esta (odometria): la diferencia con la
                # pose real es el error que acumulan los encoders.
                "odometria": [round(odo[0], 4), round(odo[1], 4), round(odo[2], 4)] if odo else None,
                "ultima_orden": self.control.ultima_orden,
                "camino": getattr(self, "camino", []),
                "fase": self.control.fase, "vaso": self.vaso_cargado,
                "inclinacion_vaso_grados": round(math.degrees(
                    p.getJointState(self.carro, self.junta_vaso, physicsClientId=self.cli)[0]), 2)}

    def cerrar(self) -> None:
        p.disconnect(self.cli)
