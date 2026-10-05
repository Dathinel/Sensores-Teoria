"""Escena 1 (la parte del grupo 7): el filtro de monedas en ventana.

    python -m sim.ver.filtro_monedas                  ventana de PyBullet, tiempo real
    python -m sim.ver.filtro_monedas --sin-ventana --segundos 30   verificar sin abrir nada

Corre el escenario `pruebas_aisladas/mixto_20` (20 elementos: las 6 causas de
rechazo de docs/especificacion.md seccion 7, dos casillas vacias y 8 monedas validas) con
la MISMA planta del supervisor (`sim/planta.py`): E1 presencia, E2 material
(capacitivo e inductivo), E3 vision (oraculo con su ruido) y E4 descarga, que
manda lo aceptado al tubo de su denominacion en el carrusel del almacen y
todo lo demas a la unica bandeja de rechazo.

Sobre cada estacion hay un texto con lo que leyo y lo que decidio; sobre cada
tubo, cuantas monedas tiene. La camara mira la cinta de monedas, el almacen y
la bandeja de rechazo. El carro aqui es el "de reemplazo" (mas liviano): esta
escena es la del filtro; el carro esta en `carro_pista` y en `todo_junto`.
"""

from __future__ import annotations

from sim.ver.comun import Camara, Vista, ejecutar, salir_limpio
from sim.ver.planta_vista import PanelMonedas, armar_planta

ESCENARIO = "mixto_20"
TITULO = "Filtro de monedas (grupo 7) - escenario mixto_20"
# Desde el lado del operador (-y) y bien desde arriba: la cinta de monedas
# (x -0.05 a 0.07, z 0.45) arriba en el cuadro y el carrusel de tubos debajo de
# su descarga (la bandeja de rechazo, en el piso, lleva su rotulo en la ventana).
# 2026-09-29: antes la camara iba mas baja (pitch -35) y mas cerca (0,30 m): el
# carrusel (tubos blancos, y ~-0,07, z 0,27-0,33) y la pieza naranja de la cinta
# de vasos quedaban ENTRE la camara y la cinta, enormes, y tapaban el frente.
# Mirando casi hacia abajo, los tubos (y la cinta de vasos) quedan debajo de
# la cinta en el cuadro, sin taparla.
CAMARA = Camara(objetivo=(0.04, -0.03, 0.40), distancia=0.32, yaw=0, pitch=-65)
LIMITE_TICKS = 400


def correr(vista: Vista) -> None:
    _, escena, planta = armar_planta(vista, ESCENARIO, CAMARA, carro_fisico=False)
    try:
        panel = PanelMonedas(vista, planta)
        vista.componer = lambda: panel.dibujar_en_foto(CAMARA.foto(escena.cliente, vista.ancho, vista.alto), CAMARA)
        while not planta.terminado and planta.ticks < LIMITE_TICKS:
            desde = escena.pasos_dados
            panel.actualizar(planta.paso())
            # Ciclos en que la moneda espera al carrusel: la cinta queda quieta
            # pero el tiempo corre (lo que tarda el giro de verdad).
            escena.completar_ciclo(desde)
        e = planta.errores_filtrado
        vista.fin(f"FIN: {panel.aceptadas} al almacén, {panel.rechazadas} a rechazo, "
                  f"falsos rechazos {len(e['falsos_rechazos'])}, falsas aceptaciones {len(e['falsas_aceptaciones'])}")
    finally:
        planta.cerrar()
        salir_limpio(escena.cliente)


def main(argv=None) -> None:
    ejecutar("filtro_monedas", TITULO, correr, argv)


if __name__ == "__main__":
    main()
