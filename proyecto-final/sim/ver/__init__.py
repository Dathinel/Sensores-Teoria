"""Escenas de PyBullet EN VENTANA para el evaluador (y los videos de docs/videos/).

No hay logica nueva aqui: cada escena arma la MISMA simulacion que usan las
pruebas y el supervisor (`sim/planta.py`, `sim/mundo.py`, `sim/vehiculo_sim.py`),
solo que conectada con `p.GUI` en vez de `p.DIRECT`, con una camara encuadrada,
rotulos de depuracion y el ritmo de tiempo real.

    python -m sim.ver.filtro_monedas     cinta de monedas + almacen (mixto_20)
    python -m sim.ver.embalaje_vasos     llenado, tapa, prensa, empujador, canaleta
    python -m sim.ver.carro_pista        el carro con fisica real en la pista
    python -m sim.ver.todo_junto         prueba_completa: planta + carro
    python -m sim.ver.grabar             graba las 4 en docs/videos/ (sin ventana)

Cada una acepta `--sin-ventana --segundos N` (mismo codigo en DIRECT, para
verificarla sin abrir nada) y `--velocidad X`. En la ventana: espacio pausa,
r reinicia, q sale.
"""
