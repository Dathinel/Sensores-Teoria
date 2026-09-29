"""Escena 3: el carro con fisica real en la pista (sim/vehiculo_sim.py).

    python -m sim.ver.carro_pista
    python -m sim.ver.carro_pista --sin-ventana --segundos 60
    python -m sim.ver.carro_pista --velocidad 3        (el viaje completo dura ~4-5 min)

Es el mismo mundo de las pruebas del carro (tests/control/test_vehiculo.py):
piso, 3 muros, muelle con guias en V y topes, y el carro de 2 ruedas con motor
de torque limitado + rueda loca, con los errores de sensores y motores de la
configuracion (semilla fija). Nada se mueve "a mano": avanza porque sus ruedas
empujan el piso y esquiva porque `control/vehiculo.py` decide con lo que leen
sus sensores. El viaje: le cargan el vaso en el muelle, sigue la linea, esquiva
los 3 muros, llega a la meta, espera que le saquen el vaso
(`espera_descarga_meta_s`), vuelve esquivando otra vez y entra de reversa al
muelle.

La camara sigue al carro (tecla c: dejar de seguirlo / volver a seguirlo).
"""

from __future__ import annotations

import pybullet as p

from app import configuracion
from sim.vehiculo_sim import SimCarro
from sim.ver.carro_vista import PanelCarro, camara_siguiendo, decorar_pista, minimapa
from sim.ver.comun import Vista, ejecutar, salir_limpio

TITULO = "Carro con física real: línea, 3 muros, meta y vuelta al muelle"
LIMITE_S = 600


def correr(vista: Vista) -> None:
    parametros = configuracion.cargar_parametros()
    sim = parametros.get("simulacion", {})
    carro = SimCarro(parametros, errores=bool(sim.get("errores_sensores")), semilla=sim.get("semilla"),
                     conexion=vista.modo)
    try:
        if vista.ventana:
            p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0, physicsClientId=carro.cli)
        geo = decorar_pista(carro.cli, parametros)
        if vista.ventana:
            p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 1, physicsClientId=carro.cli)
        vista.preparar(carro.cli, camara_siguiendo(carro))
        panel = PanelCarro(vista, carro, geo, en_ventana=vista.ventana)
        seguir = {"si": True}
        vista.teclas_extra[ord("c")] = lambda: seguir.update(si=not seguir["si"])

        def componer():
            cam = camara_siguiendo(carro)
            return minimapa(cam.foto(carro.cli, vista.ancho, vista.alto), geo, carro)

        vista.componer = componer
        cuenta = {"n": 0}

        def al_paso_control(c) -> None:
            # Cada 5 periodos de control (0,1 s): rotulos y camara de la ventana.
            cuenta["n"] += 1
            panel.sincronizar_vaso()
            if cuenta["n"] % 5 == 0:
                vista.textos = panel.renglones()
                panel.rotular_carro()
                if vista.ventana and seguir["si"]:
                    # Se mueve solo el punto al que mira; zoom y giro los deja
                    # como los tenga el usuario.
                    cam = p.getDebugVisualizerCamera(physicsClientId=c.cli)
                    x, y, _ = c.pose()
                    p.resetDebugVisualizerCamera(cam[10], cam[8], cam[9], [x, y, 0.03], physicsClientId=c.cli)
            vista.avanzar(c.dt_control)

        carro.al_paso_control = al_paso_control

        # El mismo viaje de las pruebas (tests/control/test_vehiculo.py, _viaje).
        carro.cargar_vaso()
        llegada = None
        while carro.tiempo < LIMITE_S:
            panel.eventos_nuevos(carro.avanzar(0.5))
            c = carro.control
            if c.estado == "en_meta":
                llegada = llegada or carro.tiempo
                if carro.vaso_cargado and carro.tiempo - llegada >= carro.cfg["espera_descarga_meta_s"]:
                    carro.retirar_vaso()     # el operador en la meta saca el vaso
            if c.estado == "detenido" or (c.estado == "esperando_carga" and c.fase == "vuelta"):
                break
        vista.textos = panel.renglones()
        vista.fin(f"FIN: {c.estado}, {panel.evasiones} evasiones, {carro.toques_muro} toques de muro")
    finally:
        salir_limpio(carro.cli)


def main(argv=None) -> None:
    ejecutar("carro_pista", TITULO, correr, argv)


if __name__ == "__main__":
    main()
