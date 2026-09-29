"""La planta (sim/planta.py) armada igual que en el supervisor, pero vista.

`EscenaVisible` es `EscenaEstacion` con dos diferencias que NO tocan la
logica:

1. Se conecta con el modo de la Vista (p.GUI en la ventana, p.DIRECT sin ella).
2. Cada movimiento dura lo mismo que en el montaje (config: tiempos_ms). La
   escena normal anima un avance en 60 pasos de fisica (0,25 s) porque sin
   ventana el ritmo lo pone el supervisor entre ciclos; aqui el que mira es
   una persona, asi que el avance de la cinta de monedas dura sus 600 ms y la
   pausa sus 1000 ms, a 240 pasos por segundo.

Despues de cada paso de fisica llama a `vista.avanzar()` (ritmo, teclado,
fotos del video).
"""

from __future__ import annotations

import pybullet as p

from app import configuracion
from control.embalaje import EmbalajeVasos
from control.hal.backend_sim import EstacionBackendSim
from control.linea import LineaMonedas
from sim import mundo
from sim.carga_escenarios import cargar_escenario
from sim.geometria import geometria_completa
from sim.mundo import PASOS_POR_SEGUNDO, EscenaEstacion
from sim.planta import PlantaSimulada, opciones_desde_config
from sim.sensores_sim import CamaraOraculo
from sim.ver.comun import Camara, Vista, barra_visual, caja_visual, escribir, medir

# Colores de los rotulos: (r, g, b) 0-1 para la ventana; el video usa BGR 0-255.
VERDE, ROJO, AMARILLO, BLANCO, CIAN = (0.3, 1, 0.4), (1, 0.35, 0.3), (1, 0.85, 0.2), (1, 1, 1), (0.4, 0.85, 1)


def bgr(color) -> tuple[int, int, int]:
    return int(color[2] * 255), int(color[1] * 255), int(color[0] * 255)


class EscenaVisible(EscenaEstacion):
    def __init__(self, vista: Vista, parametros: dict, *, tiempo_real: bool = True):
        self.vista = vista
        super().__init__(conexion=vista.modo)
        if tiempo_real:
            t = parametros["tiempos_ms"]
            pasos = lambda ms: max(1, round(ms / 1000 * PASOS_POR_SEGUNDO))
            self._pasos = {"avance_monedas": pasos(t["avance_casilla_monedas"]),
                           "pausa_monedas": pasos(t["pausa_casilla_monedas"]),
                           "avance_vasos": pasos(t["avance_casilla_vasos"]),
                           "pausa_vasos": pasos(t["pausa_casilla_vasos"]),
                           "empujador": self._pasos["empujador"]}

    pasos_dados = 0

    def _paso_fisica(self) -> None:
        super()._paso_fisica()
        self.pasos_dados += 1
        self.vista.avanzar()

    def completar_ciclo(self, desde: int) -> None:
        """Un ciclo de la planta dura al menos un ciclo real de la cinta de
        monedas (avance + pausa), como en el supervisor. Hace falta desde que la
        cinta ESPERA al carrusel (2026-09-28): en esos ciclos no se mueve nada y,
        sin esto, la espera no gastaria tiempo en la ventana ni en el video."""
        ciclo = self._pasos["avance_monedas"] + self._pasos["pausa_monedas"]
        while self.pasos_dados - desde < ciclo:
            self._paso_fisica()


def decorar_planta(cliente: int, parametros: dict) -> None:
    """Piezas SOLO VISUALES (sin colision, ningun sensor las ve) que en la
    escena de PyBullet no existen como cuerpos porque la simulacion mueve lo
    que cae a ellas por control de posicion: la bandeja de rechazo de monedas
    y los dos rieles de la canaleta. Salen de sim/geometria.py, la misma
    fuente del visor 3D."""
    geo = geometria_completa(parametros)
    x, y, _ = mundo.posicion_rechazo_final()
    gris = (0.45, 0.2, 0.2, 1)
    caja_visual(cliente, (x, y, 0.001), (0.045, 0.035, 0.001), gris)
    for dx, dy, mx, my in ((0.045, 0, 0.002, 0.035), (-0.045, 0, 0.002, 0.035),
                           (0, 0.035, 0.045, 0.002), (0, -0.035, 0.045, 0.002)):
        caja_visual(cliente, (x + dx, y + dy, 0.008), (mx, my, 0.008), gris)
    c = geo["canaleta"]
    s = c["separacion_rieles"] / 2
    for lado in (-1, 1):
        a = (c["inicio"][0] + lado * s, c["inicio"][1], c["inicio"][2])
        b = (c["fin"][0] + lado * s, c["fin"][1], c["fin"][2])
        barra_visual(cliente, a, b, c["diametro_riel"] / 2, (0.95, 0.95, 0.95, 1))
    # La placa verde `marca_salida_entrega` del URDF de la cinta de vasos era
    # la marca de "por aqui sale el vaso" de la fase 2, cuando la canaleta no
    # existia. Con los rieles dibujados sobra, y el vaso entregado (que ahora
    # cuelga inclinado de los rieles, sim/mundo.py) la atravesaba: en la
    # ventana y los videos se oculta (solo visual, no cambia la simulacion).
    for cuerpo in range(p.getNumBodies(physicsClientId=cliente)):
        cuerpo = p.getBodyUniqueId(cuerpo, physicsClientId=cliente)
        for j in range(p.getNumJoints(cuerpo, physicsClientId=cliente)):
            if p.getJointInfo(cuerpo, j, physicsClientId=cliente)[12] == b"marca_salida_entrega":
                p.changeVisualShape(cuerpo, j, rgbaColor=[0, 0, 0, 0], physicsClientId=cliente)


def armar_planta(vista: Vista, escenario: str, camara: Camara, *, carro_fisico: bool,
                 monedas_por_vaso: int | None = None):
    """Igual que `app/supervisor.py` (iniciar) y `app/grabar_demo.py`: backend
    simulado con la camara oraculo, errores de sensores de la configuracion
    (semilla fija: la misma corrida cada vez), filtro con los parametros de
    config. Devuelve (parametros, escena, planta)."""
    parametros = configuracion.cargar_parametros()
    escena = EscenaVisible(vista, parametros)
    vista.preparar(escena.cliente, camara)
    decorar_planta(escena.cliente, parametros)
    backend = EstacionBackendSim(escena, camara=CamaraOraculo())
    sim = parametros.get("simulacion", {})
    if sim.get("errores_sensores"):
        backend.aplicar_errores(parametros["errores_sensores"], sim.get("semilla"),
                                errores_actuadores=parametros.get("errores_actuadores"))
    opciones = dict(opciones_desde_config(parametros), carro_fisico=carro_fisico)
    if monedas_por_vaso is not None:
        opciones["monedas_por_vaso"] = monedas_por_vaso
    planta = PlantaSimulada(escena, backend, LineaMonedas(configuracion.parametros_filtrado(parametros)),
                            EmbalajeVasos(), cargar_escenario(escenario), **opciones,
                            errores_carro=bool(sim.get("errores_sensores")), semilla_carro=sim.get("semilla"))
    return parametros, escena, planta


def nombre_lugar(lugar) -> str:
    return "compartimiento OTRAS" if isinstance(lugar, str) else f"tubo de ${lugar}"


# ----------------------------------------------------------------------
# rotulos de la cinta de monedas
# ----------------------------------------------------------------------

class PanelMonedas:
    """Lo que dice cada estacion de la cinta de monedas, en la ventana
    (addUserDebugText sobre la estacion) y en el video (renglones arriba)."""

    NOMBRES = ("E1 Presencia", "E2 Material", "E3 Visión", "E4 Descarga")

    def __init__(self, vista: Vista, planta: PlantaSimulada):
        self.vista = vista
        self.planta = planta
        self.textos = {i: ("esperando", BLANCO) for i in range(4)}
        # Lo ultimo que se decidio de cada pieza (por id de registro, no por
        # body_id: PyBullet reutiliza los body_id). Se escribe AL LADO de la
        # pieza: el texto de una estacion describe la pieza que acaba de
        # decidir, y esa pieza avanza a la estacion siguiente en el ciclo
        # que viene (se decide al final de la pausa y luego la cinta avanza).
        self.por_pieza: dict[int, tuple[str, tuple]] = {}
        self._con_rotulo: dict[int, int] = {}
        self.aceptadas = 0
        self.rechazadas = 0
        self.dibujar()

    def actualizar(self, eventos: list[dict]) -> None:
        for e in eventos:
            ev, src = e["ev"], e["src"]
            i = e.get("casilla")
            if src == "e1" and ev == "presencia":
                que = e.get("tipo_real") or "?"
                if e.get("clase_real"):
                    que = e["clase_real"]
                self.textos[0] = (f"#{i}: {'ocupada' if e['ocupada'] else 'vacía'}"
                                  + (f" ({que})" if e["ocupada"] else ""), BLANCO)
                self.por_pieza[i] = (f"#{i}", BLANCO)
            elif src == "e2" and ev == "material":
                metal = e.get("metal")
                self.textos[1] = (f"#{i}: capacitivo {'sí' if e['capacitivo'] else 'no'}, inductivo "
                                  f"{'sí' if e['inductivo'] else 'no'} -> {'METAL' if metal else 'NO metal'}",
                                  BLANCO if metal else ROJO)
                self.por_pieza[i] = (f"#{i} {'metal' if metal else 'NO metal'}", BLANCO if metal else ROJO)
            elif src == "e3" and ev == "vision":
                if e["veredicto"] == "aceptada":
                    self.textos[2] = (f"#{i}: {e['clase']} ({e['confianza']:.2f}), {e['diametro_mm']:.1f} mm"
                                      f" -> aceptada", VERDE)
                    self.por_pieza[i] = (f"#{i} {e['clase']} OK", VERDE)
                else:
                    self.textos[2] = (f"#{i}: {e['diametro_mm']:.1f} mm, circ. {e['circularidad']:.2f}"
                                      f" -> RECHAZO: {e['causa']}", ROJO)
                    self.por_pieza[i] = (f"#{i} {e['causa']}", ROJO)
            elif src == "e4" and ev == "almacen":
                self.aceptadas += 1
                self.textos[3] = (f"#{i}: {e['clase']} -> {nombre_lugar(e['tubo'])} ({e['en_tubo']} adentro)", VERDE)
            elif src == "e4" and ev == "rechazo":
                self.rechazadas += 1
                self.textos[3] = (f"#{i}: -> BANDEJA DE RECHAZO (causa: {e.get('causa') or e.get('motivo')})", ROJO)
            elif src == "e4" and ev == "espera":
                if e.get("motivo") == "carrusel_girando":
                    # 2026-09-28: el carrusel tiene su tiempo real (hasta 4,1 s por media
                    # vuelta) y la moneda NO cae hasta que su tubo este quieto en la carga.
                    falta = f", faltan {e['falta_ms'] / 1000:.1f} s" if "falta_ms" in e else ""
                    self.textos[3] = (f"#{i}: espera al carrusel ({nombre_lugar(e['tubo'])}{falta}): "
                                      "la cinta espera", AMARILLO)
                else:
                    self.textos[3] = (f"#{i}: tubo de ${e['denominacion']} lleno: la cinta espera", AMARILLO)
        self.dibujar()

    def piezas_en_cinta(self):
        """(id, cuerpo, texto, color) de cada pieza que sigue sobre la cinta."""
        for el in self.planta.escena.elementos_monedas:
            if el.activo and el.id_registro in self.por_pieza:
                texto, color = self.por_pieza[el.id_registro]
                yield el.id_registro, el.body_id, texto, color, el.casilla

    def dibujar_en_foto(self, img, camara: Camara):
        """Para el video: el rotulo de cada pieza escrito junto a ella (con PIL:
        lleva tildes y se lee mejor que cv2.putText)."""
        import pybullet as p

        alto, ancho = img.shape[:2]
        tam = round(16 * ancho / 800)
        textos = []
        for _, cuerpo, texto, color, casilla in self.piezas_en_cinta():
            pos = p.getBasePositionAndOrientation(cuerpo, physicsClientId=self.planta.escena.cliente)[0]
            uv = camara.proyectar((pos[0], pos[1], pos[2] + 0.004), ancho, alto)
            if uv is None:
                continue
            w, h = medir(texto, tam, True)
            # Alternados arriba/abajo: los de casillas vecinas no se enciman.
            x0, y0 = uv[0] - w // 2, uv[1] + (-h - 20 if casilla % 2 == 0 else 14)
            textos.append((texto, (x0, y0), bgr(color), tam, True, (24, 22, 20)))
        return escribir(img, textos)

    def dibujar(self) -> None:
        v = self.vista
        if v.ventana:
            vivos = set()
            for id_, cuerpo, texto, color, _ in self.piezas_en_cinta():
                vivos.add(id_)
                v.rotulo(f"pieza_{id_}", texto, (0, 0, 0.012), color, 0.9, pegado_a=cuerpo)
                self._con_rotulo[id_] = cuerpo
            for id_ in [i for i in self._con_rotulo if i not in vivos]:
                v.rotulo(f"pieza_{id_}", " ", (0, 0, 0.012), BLANCO, 0.9, pegado_a=self._con_rotulo.pop(id_))
        renglones = []
        for k in range(4):
            texto, color = self.textos[k]
            x, y, z = mundo.posicion_estacion_monedas(k)
            v.rotulo(f"m_nombre_{k}", self.NOMBRES[k], (x - 0.015, y + 0.035, z + 0.05), CIAN, 1.0)
            v.rotulo(f"m_texto_{k}", texto, (x - 0.015, y + 0.035, z + 0.035 - 0.004 * k), color, 0.9)
            renglones.append((f"{self.NOMBRES[k]} (última decisión): {texto}", bgr(color)))
        # Tubos del almacen: cuantas monedas tiene cada uno.
        alm = self.planta.almacen
        for lugar in mundo.POSICIONES_CARRUSEL:
            n = alm.cantidad_otras() if isinstance(lugar, str) else alm.cantidad(lugar)
            x, y, z = mundo.posicion_tubo(lugar)
            nombre = "otras" if isinstance(lugar, str) else f"${lugar}"
            v.rotulo(f"tubo_{lugar}", f"{nombre}: {n}", (x, y, z + mundo.TUBO_ALTO_M + 0.012), AMARILLO, 0.8)
        x, y, z = mundo.posicion_rechazo_final()
        v.rotulo("bandeja", f"Bandeja de rechazo: {self.rechazadas}", (x - 0.04, y, z + 0.03), ROJO, 1.0)
        contenido = ", ".join(f"${d}:{n}" for d, n in alm.contenido().items() if n)
        self._resumen = (f"Monedas aceptadas al almacén: {self.aceptadas} ({contenido or 'vacío'})   |   "
                         f"rechazadas: {self.rechazadas}", bgr(AMARILLO))
        # Donde esta el carrusel al terminar este ciclo (PyBullet deja los tubos
        # quietos; el giro lo lleva control/carrusel.py con su tiempo real).
        c = self.planta.estado_carrusel()
        if c["girando"]:
            txt = f"Carrusel: girando hacia el {nombre_lugar(c['tubo'])} ({c['lugar']}), llega en {c['llega_en_ms'] / 1000:.1f} s"
        else:
            txt = (f"Carrusel: {nombre_lugar(c['tubo'])} quieto "
                   f"{'bajo la carga' if c['lugar'] == 'carga' else 'sobre el agujero'}")
        v.textos = renglones + [(txt, bgr(CIAN)), self._resumen]

    def renglones_resumen(self) -> list:
        return [self._resumen]


# ----------------------------------------------------------------------
# rotulos de la cinta de vasos
# ----------------------------------------------------------------------

class PanelVasos:
    NOMBRES = ("Verificación", "Llenado", "Tapa", "Prensa", "Descarga")
    _EV_ESTACION = {"verificacion": 0, "embalado": 1, "salto_casilla": 1, "llenado_cerrado": 1, "tapa": 2,
                    "tapa_no_confirmada": 2, "prensa": 3, "descarga": 4, "canaleta_llena": 4}

    def __init__(self, vista: Vista, planta: PlantaSimulada, *, renglones_propios: bool = True):
        self.vista = vista
        self.planta = planta
        self.textos = {i: ("", BLANCO) for i in range(5)}
        self.alarma = ("", BLANCO)
        self.cortina = False
        self.entregados = 0
        self.renglones_propios = renglones_propios
        self.renglones: list = []
        self.dibujar()

    def actualizar(self, eventos: list[dict]) -> None:
        for e in eventos:
            ev, src = e["ev"], e["src"]
            if src == "seguridad" and ev == "cortina":
                self.cortina = e["activa"]
                self.alarma = (("CORTINA: mano en la zona -> cinta de vasos detenida, prensa arriba"
                                if e["activa"] else "Cortina libre: la cinta de vasos sigue"),
                               ROJO if e["activa"] else VERDE)
            elif src == "vasos" and ev == "sabotaje_detectado":
                self.alarma = (f"SABOTAJE detectado en {e.get('estacion')}: vaso {e.get('vaso')} "
                               f"({e.get('motivo')})", ROJO)
            elif src == "carro" and ev in ("carga", "entregado"):
                self.entregados += ev == "carga"
            elif src == "vasos" and ev in self._EV_ESTACION:
                k = self._EV_ESTACION[ev]
                v = e.get("vaso")
                if ev == "verificacion":
                    txt = f"vaso {v}: {e['estado']}" + (" (algo adentro)" if e.get("objeto_adentro") else "")
                    col = VERDE if e["estado"] in ("valida", "VALIDA") else ROJO
                elif ev == "embalado":
                    txt, col = f"vaso {v}: {e['cantidad']} x ${e['denominacion']} = ${e['valor']}", VERDE
                elif ev == "salto_casilla":
                    txt, col = f"vaso {v}: no es un vaso válido -> salta", ROJO
                elif ev == "llenado_cerrado":
                    txt, col = f"vaso {v}: sale con {e['cantidad']} monedas", BLANCO
                elif ev == "tapa":
                    txt = f"vaso {v}: " + ("tapado" if e.get("tapado") else "sin tapa" if e.get("presente") else "NO ESTÁ")
                    col = VERDE if e.get("tapado") else AMARILLO
                elif ev == "tapa_no_confirmada":
                    txt, col = f"vaso {v}: tapa no confirmada", ROJO
                elif ev == "prensa":
                    txt, col = f"vaso {v}: prensado", VERDE
                elif ev == "descarga":
                    destino = e["destino"]
                    txt = f"vaso {v} -> " + ("CANALETA (entrega)" if destino == "entrega" else
                                             "vacío: BANDEJA (desechado)" if destino == "vacio" else
                                             "BANDEJA de rechazo")
                    col = VERDE if destino == "entrega" else ROJO
                else:
                    txt, col = f"vaso {v}: canaleta llena, espera", AMARILLO
                self.textos[k] = (txt, col)
        self.dibujar()

    def dibujar(self) -> None:
        v = self.vista
        renglones = []
        for k in range(5):
            texto, color = self.textos[k]
            x, y, z = mundo.posicion_estacion_vasos(k)
            v.rotulo(f"v_nombre_{k}", self.NOMBRES[k], (x - 0.03, y + 0.05, z + 0.20 + 0.012 * (k % 2)), CIAN, 1.0)
            v.rotulo(f"v_texto_{k}", texto or " ", (x - 0.03, y + 0.05, z + 0.19 + 0.012 * (k % 2)), color, 0.9)
            if texto:
                renglones.append((f"{self.NOMBRES[k]} (última decisión): {texto}", bgr(color)))
        x, y, z = mundo.posicion_estacion_vasos(4)
        v.rotulo("canaleta", f"Canaleta: {len(self.planta.canaleta)} vaso(s)", (x + 0.02, y - 0.25, z + 0.05),
                 AMARILLO, 1.0)
        x0, y0, z0 = mundo.posicion_estacion_vasos(2)
        v.rotulo("alarma", self.alarma[0] or " ", (x0 - 0.12, y0 - 0.10, z0 + 0.26), self.alarma[1], 1.1)
        if self.alarma[0]:
            renglones.append((self.alarma[0], bgr(self.alarma[1])))
        renglones.append((f"Canaleta: {len(self.planta.canaleta)} vaso(s)   |   cargados al carro: {self.entregados}",
                          bgr(AMARILLO)))
        self.renglones = renglones
        if self.renglones_propios:
            v.textos = renglones
