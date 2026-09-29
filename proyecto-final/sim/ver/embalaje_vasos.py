"""Escena 2: la cinta de vasos en ventana (llenado, tapa, prensa, empujador, canaleta).

    python -m sim.ver.embalaje_vasos
    python -m sim.ver.embalaje_vasos --sin-ventana --segundos 60

Corre `prueba_completa` (la corrida normal de la interfaz) con lotes de 5
monedas por vaso, igual que la demo grabada del visor (`app/grabar_demo.py`:
con el lote de config, 10, casi no se llenan vasos en una corrida). Los
sabotajes de vasos NO estan en el YAML del escenario (se disparan con botones
del visor o del dashboard), asi que aqui se disparan con el MISMO guion de la
demo grabada, en el mismo tick:

- tick 6: cambian el vaso por una figura mas baja (la camara lo ve: salta
  la casilla, no se llena);
- tick 12: el proximo vaso trae algo adentro (lo ve el sensor del interior);
- tick 22-27: una mano en la zona de tapa y prensa (cortina: la cinta de
  vasos se detiene y la prensa sube);
- tick 25: cambian un vaso por otro IGUAL (lo delata el marcador ArUco);
- tick 36: una mano saca un vaso por encima (lo ve la camara de vasos).

La prensa en PyBullet es solo visual (la decide `control/embalaje.py`); el
empujador si gira su junta, y el vaso pasa a colgar al inicio de la canaleta.
"""

from __future__ import annotations

from sim.ver.comun import Camara, Vista, ejecutar, salir_limpio
from sim.ver.planta_vista import PanelVasos, armar_planta

ESCENARIO = "prueba_completa"
LOTE = 5
TITULO = "Embalaje de vasos - prueba_completa (lote de 5, sabotajes de la demo)"
# El mismo guion de sabotajes de app/grabar_demo.py (tick -> metodo de la planta).
GUION = {
    6: "sabotaje_cambiar_vaso",
    12: "sabotaje_vaso_con_contenido",
    22: "sabotaje_poner_intruso",
    25: "sabotaje_cambiar_por_vaso_igual",
    27: "sabotaje_quitar_intruso",
    36: "sabotaje_mano_saca_vaso",
}
# Desde el lado del operador (-y), un poco arriba: las 5 estaciones de la
# cinta de vasos (x 0.04 a 0.36), el almacen encima del llenado y el comienzo
# de la canaleta.
CAMARA = Camara(objetivo=(0.21, -0.12, 0.20), distancia=0.62, yaw=5, pitch=-30)
LIMITE_TICKS = 600


def correr(vista: Vista) -> None:
    _, escena, planta = armar_planta(vista, ESCENARIO, CAMARA, carro_fisico=False, monedas_por_vaso=LOTE)
    try:
        panel = PanelVasos(vista, planta)
        vista.componer = lambda: CAMARA.foto(escena.cliente, vista.ancho, vista.alto)
        while not planta.terminado and planta.ticks < LIMITE_TICKS:
            if planta.ticks in GUION:
                getattr(planta, GUION[planta.ticks])()
            desde = escena.pasos_dados
            panel.actualizar(planta.paso())
            # Igual que en filtro_monedas: en los ciclos en que la cinta de
            # monedas espera al carrusel no se mueve nada, pero el tiempo corre
            # (lo que tarda el giro de verdad). Sin esto, en el video esas
            # esperas no duraban nada y el reloj simulado se quedaba atras.
            escena.completar_ciclo(desde)
        vista.fin(f"FIN: {panel.entregados} vasos cargados al carro")
    finally:
        planta.cerrar()
        salir_limpio(escena.cliente)


def main(argv=None) -> None:
    ejecutar("embalaje_vasos", TITULO, correr, argv)


if __name__ == "__main__":
    main()
