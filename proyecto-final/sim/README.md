# `sim/`: el mundo simulado (PyBullet)

Las dos cintas, el almacén, la canaleta y el carro en PyBullet, con sus sensores emulados, más el
modelo de la parte eléctrica. Aquí no se decide nada: lo que hace cada estación con lo que lee está en
[`control/`](../control/README.md). `sim/` le pasa a `control/` lo que leen los sensores y mueve lo
que `control/` ordena.

Especificación: [§11 Simulación en PyBullet](../docs/especificacion.md#11-simulación-en-pybullet),
[§10.4 Telemetría en SQLite](../docs/especificacion.md#104-telemetría-en-sqlite) y
[§5 Secuencia de operación](../docs/especificacion.md#5-secuencia-de-operación-ciclo-completo).

## Qué hace cada archivo

| Archivo | Qué hace |
|---|---|
| `planta.py` | La simulación de la línea, tick a tick. Cada `PlantaSimulada.paso()` es un avance de la cinta de monedas (y, si toca, uno de la de vasos), con las dos cintas, el almacén, la canaleta, el carro, los sabotajes y las alarmas. Lo que pasa sale como eventos con el formato `src`/`ev` del protocolo. `crear_planta_simulada()` la arma igual para el supervisor, la demo grabada y las escenas de `ver/`. `GUION_SABOTAJES` (tick → sabotaje) y `LOTE_DEMO` (5 monedas por vaso) son los de la demo grabada, y las escenas los repiten. |
| `mundo.py` | La escena de las dos cintas (`EscenaEstacion`, con los URDF de `urdf/`). Crea los cuerpos (monedas, botones, bloques, vasos) y los lleva de estación en estación por control de posición, como el motor paso a paso real. |
| `sensores_sim.py` | Los sensores emulados sobre `mundo.py`. Los infrarrojos y las franjas de la cámara de vasos son `rayTest`, la cortina es un cono de rayos y el material se lee de una bandera de cada cuerpo. También emula el Hall, el interior del vaso y la cuna, y la cámara de monedas como oráculo con ruido (`CamaraOraculo`). |
| `backend_sim.py` | La HAL de [`control/hal/interfaces.py`](../control/hal/interfaces.py) sobre PyBullet. `EstacionBackendSim` junta los sensores y actuadores de las dos cintas y les aplica el error de la config (`aplicar_errores`). Antes estaba en `control/hal/` y se movió aquí para que `control/` no dependa de PyBullet. |
| `vehiculo_sim.py` | El carro con física real (`SimCarro`), en un mundo de PyBullet propio: ruedas con torque limitado, muros, muelle con guías en V, el vaso que cabecea y los sensores del carro con su error. |
| `pista.py` | La línea central de la pista, armada con los tramos de `config/parametros.yaml`. Python puro: la usan el visor, el carro y las pruebas. |
| `geometria.py` | La geometría que dibuja el visor 3D (`geometria_completa()`, que el supervisor sirve en `GET /api/geometria`). Sale de las mismas fuentes que la simulación. Aquí también está `zonas_carro()`. |
| `carga_escenarios.py` | Lee los escenarios YAML de `escenarios/`. Define las pruebas de un filtro (`PRUEBAS_DE_UN_FILTRO`) y las piezas sueltas (`PIEZAS`). |
| `catalogos.py` | Los 13 sensores numerados (`CATALOGO_SENSORES`) y la lista de materiales (`COMPONENTES`, `CATEGORIAS`). No depende de nada. |
| `conexiones.py` | El conexionado pin a pin (`PLANTILLAS`, `DISPOSITIVOS`, `CABLES`). Es la fuente única de los cables del visor, de `docs/conexiones.md` y de los pines del firmware. No importa nada (ver reglas). |
| `electrica.py` | El modelo eléctrico: rieles y cargas, la corriente en el tiempo durante un ciclo real de la planta y un viaje del carro, cada hilo con su calibre y su caída, y los pasivos. Usa numpy y no PyBullet. |
| `electrica_informe.py` | Presenta el modelo de `electrica.py`: escribe `docs/electrica.md` y `docs/capturas/electrica-ciclo-*.png`. |
| `escenarios/` | `prueba_completa.yaml` (la corrida normal) y `pruebas_aisladas/` (un escenario por filtro y `mixto_20`). |
| `urdf/` | `cinta_monedas.urdf` y `cinta_vasos.urdf`, que lee `mundo.py` (`DIRECTORIO_URDF`). |
| `ver/` | Las escenas en ventana para quien evalúa y el grabador de videos (abajo). |

## Cómo se usa

Desde `proyecto-final/` y con el Python del entorno (`python -m sim...` solo funciona desde esa carpeta):

```
entorno\Scripts\python -m sim.electrica          # escribe docs/electrica.md y sus dos gráficas
entorno\Scripts\python -m sim.ver.filtro_monedas  # una escena en su ventana
entorno\Scripts\python -m sim.ver.filtro_monedas --sin-ventana --segundos 8   # la misma, sin abrir nada
entorno\Scripts\python -m sim.ver.grabar          # regraba los videos de docs/videos/
```

`planta.py` no se corre sola. La usan el supervisor (`app/supervisor.py`, en vivo), la demo grabada
(`python -m app.grabar_demo`) y las pruebas. `docs/electrica.md` también se regenera con
`python -m app.documentos`.

### Las escenas de `ver/`

| Módulo | Qué muestra | Lanzador |
|---|---|---|
| `sim.ver.filtro_monedas` | La cinta de monedas y el almacén con el escenario `mixto_20` | `simulaciones/1-filtro-monedas.bat` |
| `sim.ver.embalaje_vasos` | Llenado, tapa, prensa, empujador y canaleta, con el guion de sabotajes de la demo | `simulaciones/2-embalaje-vasos.bat` |
| `sim.ver.carro_pista` | El carro con física real: línea, 3 muros, meta y vuelta al muelle | `simulaciones/3-carro-pista.bat` |
| `sim.ver.todo_junto` | `prueba_completa`: la planta en la ventana de PyBullet y el carro en una segunda ventana (OpenCV) | `simulaciones/4-todo-junto.bat` |
| `sim.ver.grabar` | Graba las 4 escenas sin ventana en `docs/videos/` (`.mp4`, y `.gif` de todas menos `todo_junto`) | (ninguno) |

Cada escena acepta `--sin-ventana --segundos N` (el mismo código en `p.DIRECT`, para comprobarla) y
`--velocidad X`. En la ventana: espacio pausa, `r` reinicia y `q` sale. Los demás archivos de `ver/`
son de apoyo: `comun.py` (la `Vista`: ritmo, teclado, cámara, rótulos y video), `planta_vista.py` (la
planta de `crear_planta_simulada` sobre una escena que se ve) y `carro_vista.py` (la pista y la línea,
solo para verlas). El menú está en [`simulaciones/`](../simulaciones/README.md), y lo que muestra cada
escena, en el [README general](../README.md#las-simulaciones-de-pybullet-para-quien-evalúa).

## Reglas

- Fuera de las pruebas, solo `sim/` importa PyBullet. `sim/` usa `control/` y lee la config con
  `control.configuracion`, nunca con `app/`. `control/` no importa nada de `sim/`.
- Las escenas de `ver/` no tienen lógica propia: arman la misma planta y el mismo carro que el
  supervisor y las pruebas, solo que en `p.GUI` y a tiempo real. Las pruebas usan siempre `p.DIRECT`.
- La planta y el carro están en mundos de PyBullet separados y se hablan solo por la "radio"
  (`control/protocolo.py`), como en el montaje por ESP-NOW.
- **`conexiones.py` no se mueve ni se renombra, y no importa nada.** Hay 8 scripts de
  `D:/cosas uni/Modelado 3D` (fuera de este repo) que lo cargan por su ruta absoluta con `importlib`
  para usar `PLANTILLAS` y `CABLES`.
- Los nombres de escenario aparecen como texto en el visor, el dashboard, la demo, las pruebas y
  `probar.json`, así que renombrar un `.yaml` rompe todo eso. `listar_escenarios()` solo mira
  `escenarios/`, y `tests/sim/test_escenarios.py` exige que ahí esté únicamente `prueba_completa`.
  Por eso un escenario nuevo va en `pruebas_aisladas/`.
- Cada escena de `ver/` se llama igual que su video (`grabar.py`), y esos nombres aparecen en el README,
  en `app-practica/` y en `probar.json`.
- Ningún número va en el código: va en [`config/`](../config/README.md). `docs/electrica.md` y
  `docs/conexiones.md` se generan y no se editan a mano.

## Quién usa `sim/` desde afuera

| Desde | Usa |
|---|---|
| `app/supervisor.py`, `app/grabar_demo.py` | `planta`, `mundo`, `geometria`, `carga_escenarios` |
| `app/documentos.py` | `catalogos`, `conexiones`, `mundo`, `electrica_informe` |
| `app/costos.py`, `app/masas.py` | `catalogos` |
| `app/dashboard/` | `carga_escenarios` (pruebas de un filtro) |
| `app/asistente/reglas.py` | `geometria.zonas_carro` |
| `firmware/preparar.py` | `conexiones` (genera `pines.py`), `sensores_sim`, `geometria`, `pista` |
| `chasis_impreso/diagramas.py`, `chasis_impreso/manual.py` | `conexiones` |
| `maqueta_impresa/manual_maqueta.py` | `conexiones` y `electrica` |
| `maqueta_impresa/esfuerzos.py` | `electrica` |
| `tests/sim/` | todo `sim/` (ver [`tests/`](../tests/README.md)) |
