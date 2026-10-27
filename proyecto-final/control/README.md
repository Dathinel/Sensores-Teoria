# `control/`: la lógica que decide (Python puro)

Aquí está todo lo que se decide: qué hace cada estación con lo que lee, el registro de casillas, el
almacén y su carrusel, la cinta de vasos, el carro, el protocolo y el presupuesto de tiempos.
`control/` no sabe si del otro lado está PyBullet o un ESP32. Por eso el mismo código corre en la
simulación ([`sim/`](../sim/README.md)), en las pruebas y contra el hardware real, y dos de sus
archivos van tal cual a las placas.

Especificación: [§7 Reglas de decisión](../docs/especificacion.md#7-reglas-de-decisión-del-filtrado),
[§8 Arquitectura de software](../docs/especificacion.md#8-arquitectura-de-software) y
[§10.2 Veredicto de visión](../docs/especificacion.md#102-veredicto-de-visión).

## La regla de esta carpeta

`control/` **no importa PyBullet, pyserial ni OpenCV**, y tampoco nada de `sim/` ni de `app/`
([regla 17](../CLAUDE.md#17-reglas-para-el-agente)). Si hace falta hardware o percepción desde aquí,
lo que falta es un método en la HAL (`hal/interfaces.py`), no un import. Para comprobarlo, este
comando, corrido desde `proyecto-final/`, no tiene que mostrar nada:

```
git grep -nE "^\s*(import|from) (pybullet|serial|cv2|sim|app)\b" -- control/
```

## Qué hace cada archivo

| Archivo | Qué hace |
|---|---|
| `reglas.py` | Las 6 causas de rechazo de monedas (`no_metalico`, `fuera_de_rango`, `no_circular`, `perforado`, `no_reconocida`, `incoherente`). `evaluar_moneda` las encadena y se detiene en la primera que rechaza; `combinar_fotos` junta las dos fotos. Los valores por defecto de `ParametrosFiltrado` solo existen para las pruebas. |
| `linea.py` | La cinta de monedas (`LineaMonedas`): qué hace cada estación (E1 presencia, E2 material, E3 visión) y a dónde va cada casilla en la descarga (`Destino`). |
| `registro.py` | El registro de casillas de las dos cintas, con la regla de que ninguna estación revierte un rechazo, y los estados del vaso (`EstadoVaso`). |
| `almacen.py` | Los tubos por denominación (`AlmacenDenominaciones`): guarda cada moneda, avisa cuando un tubo se llena y saca un lote. |
| `carrusel.py` | El carrusel tipo revólver: dónde está cada tubo y cuándo llega, con el tiempo real del 28BYJ-48. Está escrito con lo que tiene MicroPython (sin dataclasses, `{**d}` ni `[*x]`), y `tests/control/test_carrusel.py` lo comprueba. |
| `embalaje.py` | La cinta de vasos como máquina de estados (`EmbalajeVasos`): verificar, llenar, tapar, prensar y descargar. La cortina lo congela todo. |
| `monedas.py` | Lee `config/monedas.yaml` y da el diámetro, la masa, el valor y la denominación de cada clase. |
| `vehiculo.py` | El carro (`ControlCarro`): sigue la línea, esquiva, llega a la meta, vuelve al muelle, recibe órdenes y lleva la odometría. También define las zonas por las que puede ir. **Va a la placa del carro.** |
| `protocolo.py` | Mensajes JSON numerados con ack, el latido, la parada sin PC y la regla para soltar un vaso al carro (`puede_soltar_vaso`). **Va a las dos placas.** |
| `tiempos.py` | El presupuesto de tiempos del montaje real: si cada acción cabe en su hueco y cuánto produce la línea por minuto. |
| `configuracion.py` | El único lector de `config/parametros.yaml` (`cargar_parametros`) y de los umbrales del filtro (`parametros_filtrado`). `app/configuracion.py` lo reexporta y agrega `ruta_bd`. |
| `hal/interfaces.py` | Las interfaces abstractas que usa la lógica: `SensorDiscreto`, `SensorDistancia`, `Camara`, `BandaIndexada`, `Servo`, `MotorPrensa` y `DispensadorTapas`. |
| `hal/backend_real.py` | Las mismas interfaces sobre el ESP32 fijo: lee la telemetría y manda comandos numerados a través de un puente que ya llega abierto (`app.puente_serial.PuenteESP32`). Por eso no importa pyserial. |

El backend de simulación de la HAL no está aquí: está en [`sim/backend_sim.py`](../sim/backend_sim.py),
porque depende de PyBullet.

## Lo que va a las placas: `protocolo.py` y `vehiculo.py`

`firmware/preparar.py` copia `control/protocolo.py` a las dos placas y `control/vehiculo.py` a la del
carro, **con esos mismos nombres**, y los compila con `mpy-cross`. En la placa, el firmware los importa
como `import protocolo` y `from vehiculo import ...`; en el PC usa como respaldo
`from control import protocolo`. De ahí salen tres reglas:

- No se renombran, no se mueven y no se parten.
- Solo usan lo que tiene MicroPython: nada de dataclasses, `{**d}`, `[*x]` ni `json.dumps(ensure_ascii=...)`.
- Si cambian, hay que volver a subir el firmware (`entorno\Scripts\python -m firmware.subir fijo|carro`),
  como explica [`firmware/README.md`](../firmware/README.md).

## Pruebas

```
entorno\Scripts\python -m pytest -q tests/control
```

`tests/control/` cubre las reglas de decisión, el registro, las dos cintas, el almacén, el carrusel,
las monedas, el protocolo, los tiempos y el carro con física real (más en [`tests/`](../tests/README.md)).
`tests/firmware/` compila `protocolo.py` y `vehiculo.py` con mpy-cross y los corre dentro del
firmware emulado. Toda regla nueva de esta carpeta lleva su prueba (regla 17).

## Quién usa `control/`

| Desde | Usa |
|---|---|
| `sim/planta.py` | `reglas`, `linea`, `registro`, `almacen`, `carrusel`, `embalaje`, `monedas`, `protocolo`, `configuracion` |
| `sim/backend_sim.py` | `hal.interfaces`, `configuracion` |
| `sim/sensores_sim.py` | `hal.interfaces`, `monedas` |
| `sim/carga_escenarios.py` | `monedas` |
| `sim/vehiculo_sim.py` | `vehiculo` |
| `sim/mundo.py`, `sim/electrica.py`, `sim/electrica_informe.py`, `sim/ver/` | `configuracion` (y `mundo` también `almacen` y `monedas`) |
| `app/supervisor.py` | `hal.backend_real` (con `hardware.backend: real`) |
| `app/puente_serial.py` | `protocolo` |
| `app/configuracion.py` | `configuracion` (la reexporta) |
| `app/dashboard/`, `app/documentos.py` | `reglas`, `monedas`, `tiempos` |
| `app/asistente/reglas.py` | `vehiculo` |
| `firmware/` | `protocolo` y `vehiculo` (copiados a la placa), `configuracion` (en `preparar.py`) |
| `vision/capturar_dataset.py` | `monedas` |
