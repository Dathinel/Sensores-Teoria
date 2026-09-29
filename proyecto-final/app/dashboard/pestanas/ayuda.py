"""Pestaña Ayuda: cómo leer el tablero, para quien no conoce el sistema."""

from __future__ import annotations

import streamlit as st

from ..estilo import seccion

TEXTO = """
**Qué hace el sistema**, en tres pasos:

1. **Clasificar.** Se pone una pieza por casilla en la **cinta de monedas**. Un infrarrojo la ve, dos sensores
   debajo de la cinta dicen si es de metal y una cámara la mide y la reconoce. Solo pasan las monedas
   colombianas: todo lo demás sale a la bandeja de rechazo.
2. **Empacar.** Cada moneda aceptada va al **almacén tipo revólver**: un tubo por denominación. Cuando un
   tubo junta un lote, suelta las monedas a un **vaso**, y cada vaso lleva una sola denominación. El vaso se
   tapa, se prensa y pasa a la **canaleta**.
3. **Entregar.** Un **carro autónomo** recibe el vaso, sigue la línea de la pista, esquiva tres obstáculos,
   lo lleva a la meta y vuelve solo al muelle.
"""

PESTANAS = """
- **Barra de la izquierda**: manejar la línea. Empezar una corrida, pausa, seguir, paro de emergencia, la
  velocidad de la simulación y cuántas monedas lleva cada vaso.
- **Resumen**: lo más importante de un vistazo. Muestra cuánto dinero se ha aceptado, cómo está cada parte y
  qué pasó hace un momento.
- **Monedas y vasos**: cuántas monedas hay de cada denominación, qué hay guardado en cada tubo y los vasos
  de la corrida.
- **Calidad del filtro**: qué tan bien separa la línea las monedas buenas del resto, y por qué rechazó cada
  cosa.
- **Línea en vivo**: las dos cintas en este momento, el almacén, los sensores encendidos y la bitácora.
- **Pruebas**: todo lo que se le puede hacer a la planta para ver si se da cuenta sola. Probar un filtro por
  separado, colocar una pieza a mano, sacar un vaso, meter una mano, cortar la radio del carro y empacar lo
  guardado al final del turno.
- **Carro y ruta**: el recorrido real del carro por la pista, su radio y sus viajes, y al lado los botones para
  moverlo con órdenes (avanzar, girar, ir a un punto, ir a la meta, volver al muelle).
- **Montaje real**: los tiempos, los errores de los sensores y los costos para construirlo de verdad.
- **Asistente**: se le pregunta por escrito o por voz por las cifras de la corrida o por cualquier parte del
  proyecto, y se le puede pedir que mueva el carro o la línea. Responde, en este orden, DeepSeek (en la nube,
  con internet); si no está, el modelo local qwen2.5 que corre en este PC con Ollama (sin internet), y si
  tampoco, las reglas. Venga de quien venga, una orden solo sale si está en la lista de órdenes permitidas, y
  una pregunta nunca mueve nada.
"""

PALABRAS = """
- **Lote**: cuántas monedas lleva cada vaso.
- **Cortina de seguridad**: un sensor que detecta una mano en la zona de tapa y prensa, y detiene esa zona.
- **Rechazo por material**: no es de metal (botones, bloques).
- **Rechazo por visión**: la cámara no la reconoce o sus medidas no cuadran.
- **Radio del carro**: el carro y la estación hablan por radio (ESP-NOW). Si se corta, el carro termina la vuelta
  solo, y no se le carga otro vaso hasta saber, con su infrarrojo, que la cuna está vacía.
- **Peso estimado**: se calcula con la masa nominal de cada moneda reconocida (no hay balanza).
- **Del turno anterior**: monedas que quedaron guardadas en los tubos al terminar la corrida pasada y que la
  corrida nueva encuentra al arrancar. Van a los vasos como cualquier otra, pero no cuentan en el «valor
  aceptado», que es solo lo que pasó por los filtros en esta corrida.
- **Espera aceptada**: cuando el carrusel no alcanza a girar en un ciclo, la cinta de monedas lo espera. Baja
  un poco la producción, pero no se pierde ninguna moneda.
- **Odometría**: dónde cree el carro que está, contando las vueltas de sus ruedas. Acumula error; se vuelve a
  poner en cero cada vez que entra al muelle.
"""

COLORES = """
- **Verde**: bien, aceptado, trabajando.
- **Ámbar**: lo principal, en proceso, guardado.
- **Rojo**: rechazo, alarma, sin internet.
- **Azul**: el carro e información.
- **Morado**: la cámara, el hardware real y las pruebas del operador.
"""


def pestana() -> None:
    izq, der = st.columns([1.3, 1], gap="large")
    with izq:
        seccion("Cómo leer este tablero", primera=True)
        st.markdown(TEXTO)
        seccion("Las partes del tablero")
        st.markdown(PESTANAS)
    with der:
        seccion("Palabras que aparecen", primera=True)
        st.markdown(PALABRAS)
        seccion("Qué quiere decir cada color")
        st.markdown(COLORES)
        st.info("Para ver la planta en 3D, con cada sensor, cable y pin, abra **visor.bat**.")
