"""Escena 4: todo junto, `prueba_completa` con el carro de fisica real.

    python -m sim.ver.todo_junto
    python -m sim.ver.todo_junto --sin-ventana --segundos 120

Por que DOS ventanas y no un solo mundo: en `sim/planta.py` el carro vive en
su PROPIO mundo de PyBullet (`sim/vehiculo_sim.py`, otro cliente de fisica):
la planta y la pista no comparten cuerpos, se comunican solo por la "radio"
(mensajes numerados, `control/protocolo.py`), igual que en el montaje real por
ESP-NOW. Y PyBullet solo permite UNA ventana GUI por proceso. Asi que:

- la ventana de PyBullet muestra la planta (cintas, almacen, canaleta), con
  sus rotulos;
- una segunda ventana (OpenCV) muestra el mundo del carro, renderizado con
  `getCameraImage` desde su propio cliente, siguiendo al carro.

No se inventa un mundo nuevo que junte los dos: seria otra simulacion distinta
de la que corre el supervisor.

Como se sincronizan: cada tick de la planta es un ciclo de la cinta de
monedas (1,6 s); en ese tick la planta hace avanzar al carro esos 1,6 s de
una vez (`PlantaSimulada._carro_fisico`) y despues mueve las cintas. La vista
guarda los cuadros del carro de ese ciclo y los muestra al mismo ritmo que se
mueve la cinta, asi los dos se ven a la vez. Si el tick de la planta dura mas
(avanza tambien la cinta de vasos), el carro se queda en su ultimo cuadro.

Sabotajes: el mismo guion de la demo grabada (`app/grabar_demo.py`).
"""

from __future__ import annotations

import numpy as np

from sim.ver.carro_vista import PanelCarro, camara_siguiendo, decorar_pista, minimapa
from sim.ver.comun import Camara, Vista, ejecutar, escribir, salir_limpio
from sim.ver.embalaje_vasos import GUION, LOTE
from sim.ver.planta_vista import PanelMonedas, PanelVasos, armar_planta

TITULO = "Todo junto: prueba_completa (planta + carro con física real)"
# Toda la planta: cinta de monedas arriba, almacen, cinta de vasos y canaleta.
# (2026-09-28: antes a 0,95 m, la planta ocupaba menos de un tercio del ancho
# del cuadro; a 0,66 m y centrada en la cinta de vasos se leen los vasos, la
# tapa y el vaso colgado en la canaleta, y todavia entra el portico de arriba.)
CAMARA_PLANTA = Camara(objetivo=(0.21, -0.16, 0.22), distancia=0.66, yaw=22, pitch=-24)
LIMITE_TICKS = 1200


def correr(vista: Vista) -> None:
    import cv2

    parametros, escena, planta = armar_planta(vista, "prueba_completa", CAMARA_PLANTA, carro_fisico=True,
                                              monedas_por_vaso=LOTE)
    carro = planta.carro
    ventana_carro = "Carro (su propio mundo de PyBullet)"
    try:
        geo = decorar_pista(carro.cli, parametros)
        monedas = PanelMonedas(vista, planta)
        vasos = PanelVasos(vista, planta, renglones_propios=False)
        panel_carro = PanelCarro(vista, carro, geo, en_ventana=False)
        # Cuadros del carro en este ciclo. Grabando se toma uno por cuadro de
        # video, del tamano del video; en la ventana, 4 por segundo y mas
        # chicos (el render por software cuesta: con 10 grandes por segundo la
        # ventana no alcanzaba el tiempo real).
        intervalo = vista.acelerar / vista.fps if vista.grabar else 0.25
        tam_carro = (vista.ancho, vista.alto) if vista.grabar else (448, 252)
        ciclo = {"t0": 0.0, "t0_carro": 0.0, "cuadros": [], "mostrado": -1}

        def foto_carro() -> np.ndarray:
            panel_carro.sincronizar_vaso()
            img = minimapa(camara_siguiendo(carro).foto(carro.cli, *tam_carro), geo, carro,
                           lado=170 if vista.grabar else 120)
            # Banda oscura semitransparente detras del texto (2026-09-28): el
            # piso de PyBullet es blanco y celeste, y el texto claro encima casi
            # no se leia. Mismo fondo que la banda de arriba del video.
            # (2026-09-29: con PIL, letra mas grande y con tildes, como la banda de arriba.)
            renglones = panel_carro.renglones()[:2]
            k = img.shape[1] / 800
            alto_banda = int((36 + 25 * len(renglones)) * k)
            fondo = img.copy()
            cv2.rectangle(fondo, (0, 0), (img.shape[1], alto_banda), (24, 22, 20), -1)
            img = cv2.addWeighted(fondo, 0.8, img, 0.2, 0)
            textos = [("Carro: su propio mundo de PyBullet (física real)", (int(10 * k), int(6 * k)),
                       (120, 230, 255), int(20 * k), True)]
            textos += [(texto, (int(10 * k), int((36 + 25 * i) * k)), color, int(18 * k), False)
                       for i, (texto, color) in enumerate(renglones)]
            return escribir(img, textos)

        def al_paso_carro(c) -> None:
            if c.tiempo - ciclo["t0_carro"] + 1e-9 >= len(ciclo["cuadros"]) * intervalo:
                ciclo["cuadros"].append(foto_carro())

        # Sin ventana y sin grabar (verificacion) nadie mira los cuadros: no se renderizan.
        if vista.ventana or vista.grabar:
            carro.al_paso_control = al_paso_carro

        def cuadro_carro_actual():
            if not ciclo["cuadros"]:
                return None, -1
            k = min(int((vista.t - ciclo["t0"]) / intervalo), len(ciclo["cuadros"]) - 1)
            return ciclo["cuadros"][k], k

        def componer():
            img_carro, _ = cuadro_carro_actual()
            if img_carro is None:
                img_carro = foto_carro()
            return np.vstack([CAMARA_PLANTA.foto(escena.cliente, vista.ancho, vista.alto), img_carro])

        def mostrar_carro() -> None:
            img, k = cuadro_carro_actual()
            if img is not None and k != ciclo["mostrado"]:
                ciclo["mostrado"] = k
                cv2.imshow(ventana_carro, img)
                cv2.waitKey(1)

        vista.componer = componer
        if vista.ventana:
            vista.al_paso = mostrar_carro

        ya_entrego = False
        while not planta.terminado and planta.ticks < LIMITE_TICKS:
            if planta.ticks in GUION:
                getattr(planta, GUION[planta.ticks])()
            ciclo.update(t0=vista.t, t0_carro=carro.tiempo, cuadros=[], mostrado=-1)
            desde = escena.pasos_dados
            eventos = planta.paso()
            # El carro ya avanzo su ciclo entero; si la planta no ocupo ese
            # tiempo (cinta quieta esperando al carrusel o a la canaleta), el
            # tiempo igual pasa: lo mismo que en filtro_monedas y embalaje_vasos
            # (un ciclo real de la cinta de monedas, avance + pausa = 1,6 s).
            escena.completar_ciclo(desde)
            monedas.actualizar(eventos)
            vasos.actualizar(eventos)
            panel_carro.eventos_nuevos([e for e in eventos if e["src"] == "carro"])
            vista.textos = (monedas.renglones_resumen() + vasos.renglones[-2:] + panel_carro.renglones()[:1])
            # Igual que la demo grabada: termina cuando el carro vuelve al
            # muelle despues de entregar su primer vaso.
            ya_entrego = ya_entrego or any(e["ev"] == "entregado" for e in eventos)
            if ya_entrego and any(e["ev"] == "en_muelle" for e in eventos):
                break
        vista.fin(f"FIN: {vasos.entregados} vaso(s) cargados al carro; carro {carro.control.estado}")
    finally:
        if vista.ventana:
            cv2.destroyAllWindows()
        planta.cerrar()
        salir_limpio(escena.cliente)


def main(argv=None) -> None:
    ejecutar("todo_junto", TITULO, correr, argv)


if __name__ == "__main__":
    main()
