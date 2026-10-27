# `config/`: todos los números del diseño

Cuatro YAML. Aquí van los números que el código usa, para que no queden escritos dentro del código
([regla 17](../CLAUDE.md#17-reglas-para-el-agente)). Especificación:
[§6 Datos de referencia de las monedas](../docs/especificacion.md#6-datos-de-referencia-de-las-monedas).

## Las dos reglas

- **Todo número mágico va aquí**: umbrales de confianza, rangos de diámetro, tolerancias, pausas,
  tiempos y velocidades. El código los lee; no los copia.
- **Un dato físico que todavía no se midió** se escribe aquí con un **valor provisional claramente
  marcado**, y se le avisa al usuario en vez de dejarlo escondido. Cada archivo lo marca a su modo:
  `PROVISIONAL` en el comentario (`parametros.yaml`), `verificado: false` (`monedas.yaml`) y
  `fuente: estimado` (`precios.yaml` y `masas.yaml`). Las medidas que faltan tomar en el montaje salen
  en `docs/replicacion.md`, que se genera.

## Qué guarda cada archivo y quién lo lee

| Archivo | Qué guarda | Quién lo lee |
|---|---|---|
| `parametros.yaml` | El filtro (`filtrado`), las cintas, los vasos, el motor paso a paso, la cortina, la planta, el supervisor (puerto, ruta de la base), el dashboard, la canaleta, la pista, el carro (`vehiculo`, `zonas_carro`), el puesto del PC, el protocolo, `tiempos_ms`, el error de cada sensor y actuador, la `simulacion` (semilla), el `firmware` y el `hardware` (`backend: sim` o `real`). | Solo lo abre `control/configuracion.py` (`cargar_parametros`, `parametros_filtrado`). Todos los demás pasan por ahí: `sim/` y `firmware/preparar.py` directo, y `app/` a través de `app/configuracion.py`, que lo reexporta. |
| `monedas.yaml` | La tabla de monedas colombianas en 4 generaciones: denominación, familia, diámetro, masa, material, si es ferromagnética o bimetálica, y `verificado`. | `control/monedas.py`. |
| `precios.yaml` | El precio en Colombia (COP) de cada componente, con el mismo `id` que tiene en `sim/catalogos.py`. También los extras, la estructura 3D (`estructura_3d`: precio del PLA, piezas impresas, la maqueta, tornillería) y las propuestas de ahorro. | `app/costos.py` (lo usan `docs/costos.md`, la pestaña "Montaje real" del dashboard y el asistente) y `app/masas.py` (piezas impresas y tornillería ya contadas). También `maqueta_impresa/exportar.py` (`PRECIO_KG`, el precio del PLA), `chasis_impreso/materiales.py` y `chasis_impreso/manual.py`. |
| `masas.yaml` | La masa por unidad de lo que no está en `precios.yaml`, las densidades y las comprobaciones de par. | `app/masas.py` (lo usa `docs/peso.md`) y `maqueta_impresa/esfuerzos.py` (`comprobaciones.nema17.tension_banda_n`). |

Además, el asistente busca texto en `parametros.yaml` y `monedas.yaml` para responder
(`app/asistente/conocimiento.py`): los comentarios también cuentan.

Excepciones a tener en cuenta:

- `wokwi/fijo/main.py` no lee la config: copia a mano algunos `tiempos_ms` y el umbral de la cortina.
  Ninguna prueba compara esos valores con la config.
- `tests/sim/test_backend_sim.py`: abre `parametros.yaml` directamente, sin pasar por `control/configuracion.py`.
- `precios.yaml` nombra un archivo: `estructura_3d.maqueta.archivo: maqueta_impresa/salida/piezas.json`.
  `app/costos.py` lo lee desde ahí.

## Qué regenerar después de cambiar algo

| Si cambia | Correr |
|---|---|
| Un precio o una masa | `entorno\Scripts\python -m app.documentos`, que reescribe `docs/costos.md` y `docs/peso.md` (y los demás `.md` que se generan). El dashboard y el asistente leen los YAML en el momento: no hay que regenerarlos. |
| El precio del PLA | Lo anterior, más los informes de la maqueta: lo dice [`maqueta_impresa/README.md`](../maqueta_impresa/README.md). |
| Una medida o un tiempo de `parametros.yaml` | `entorno\Scripts\python -m app.documentos` (`docs/replicacion.md`, `docs/electrica.md`). Si se ve en el 3D, también `entorno\Scripts\python -m app.grabar_demo`, que vuelve a grabar la demo y arma de nuevo `visor-portable.html`. |
| `firmware:`, o algo que lleva la placa (`tiempos_ms`, `protocolo`, `cinta_monedas`, `vasos`, `motor_paso_a_paso`, `planta`, `pista`, `vehiculo`, `zonas_carro` y lo que use `sim.geometria.geometria_completa`) | Volver a subir a la placa: `entorno\Scripts\python -m firmware.subir fijo` (o `carro`). `preparar.py` arma `config_placa.py` con esas secciones. |
| `hardware:` (`backend: sim` o `real`) | Nada que regenerar: el supervisor la lee al arrancar. Hay que reiniciar la corrida: cerrar su consola y abrir `visor.bat`, o `entorno\Scripts\python -m app.lanzar --auto prueba_completa --reemplazar`. |

El carro (`chasis_impreso/`) ya está impreso y armado: si se cambia un precio del carro, sus `salida/`
no se regeneran.

Pruebas que vigilan estos archivos: `tests/app/test_costos.py` y `test_masas.py` (todo lo del catálogo
tiene precio y masa, los totales y las comprobaciones de par), `tests/control/test_monedas.py` (la
tabla) y `tests/control/test_tiempos.py`. Esta última exige que el código de `control/`, `sim/`, `app/`
y `firmware/` use cada clave de `tiempos_ms` y de `errores_sensores`: no se agregan claves que nadie
lee.
