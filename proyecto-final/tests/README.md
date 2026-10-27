# `tests/`: las pruebas automáticas

951 pruebas, ordenadas por capa. Ninguna abre ventanas: PyBullet corre en modo `p.DIRECT`.
Especificación: [§11 Simulación en PyBullet](../docs/especificacion.md#11-simulación-en-pybullet)
(por qué la simulación no reemplaza a las pruebas). El resumen para quien evalúa está en el
[README general](../README.md#pruebas-automáticas).

## Cómo se corren

Desde `proyecto-final/`, con el Python del entorno:

```
entorno\Scripts\python -m pytest -q                       # todas, unos 4 minutos
entorno\Scripts\python -m pytest -q tests/control         # una capa
entorno\Scripts\python -m pytest -q tests/sim/test_planta.py
```

`pytest.ini` (en la raíz del proyecto, que es donde tiene que estar) define `testpaths = tests` y
`pythonpath = .`. Con eso, `control`, `sim`, `app`, `firmware` y `vision` se importan sin instalar
nada. Ni `tests/` ni sus subcarpetas tienen `__init__.py`, así que **cada `test_*.py` tiene que tener
un nombre que no se repita en todo `tests/`**.

`conftest.py` es el único `.py` en la raíz de `tests/`. Lo único que hace es cerrar, al terminar
cada archivo de prueba, los mundos de PyBullet que hayan quedado abiertos. La escena trabaja siempre
sobre la conexión 0, y un mundo viejo abierto (por ejemplo, el de un `Supervisor` de `tests/app/`)
haría fallar sin razón a las pruebas de `tests/sim/` que corren después.

## Qué cubre cada carpeta

| Carpeta | Pruebas | Qué cubre |
|---|---|---|
| `control/` | 135 | Reglas de decisión, registro de casillas, la cinta de monedas y la de vasos, almacén, carrusel, tabla de monedas, protocolo, presupuesto de tiempos y el carro (`test_vehiculo.py`, con física real: ida y vuelta con los errores de la config, ~7 s por viaje). |
| `sim/` | 433 | Sensores emulados y backend, la planta completa con cada sabotaje, un escenario por filtro y `mixto_20`, el carrusel con tiempo real, el conexionado, la parte eléctrica y los diagramas de Wokwi, física contra 3D, y el carro y la maqueta impresos comparados con la simulación. |
| `app/` | 275 | El asistente (con un DeepSeek falso), la voz sin internet, la charla, el chequeo, costos, masas, el dashboard (AppTest de Streamlit en cada pestaña), la base SQLite, el supervisor, las órdenes del servidor, los puertos, el puente serial y la prueba de un filtro. |
| `firmware/` | 73 | Las dos placas corridas en el PC con hardware falso, todo compilado con `mpy-cross`, el puente de punta a punta, el carrusel en el firmware y en el backend real, y los casos de la revisión del 2026-09-29. |
| `visor/` | 35 | `visor-portable.html`, la geometría que comparten el visor y la simulación, la pista, el servidor HTTP y las anclas de los documentos generados. |

Para contarlas: `entorno\Scripts\python -m pytest --collect-only -q`.

## Convenciones

- Se prueban sobre todo la capa de control y las reglas de decisión
  ([regla 17](../CLAUDE.md#17-reglas-para-el-agente)). La simulación es lenta y visual; las pruebas son
  rápidas y se pueden verificar.
- PyBullet siempre en `p.DIRECT`. Las pruebas de la planta usan la cámara oráculo sin ruido, para que
  cada elemento termine donde dice su escenario.
- Nada sale a la red: DeepSeek es un cliente falso, los puertos se prueban con sockets en `127.0.0.1` y
  el puente serial con `loop://` de pyserial. El dashboard y la charla trabajan sobre una base de
  prueba (variable `PLANTA_BD`).
- **Monkeypatch del asistente**: se reemplaza la función en el submódulo donde se busca, no en el
  paquete: `asistente.llm` (`cliente_local`, `preguntar_deepseek`, `preguntar_llm`) y `asistente.audio`
  (`hay_internet`, `transcribir_local`, `voz_local`, `_whisper_modelo`). Ahí la buscan `atender`, el
  dashboard y el servidor. `asistente.MODELO_LOCAL` se lee siempre de `llm`.
- `visor/test_portable.py` genera el portable en `tmp_path`: no toca el `visor-portable.html`
  versionado (~9,4 MB).
- Un escenario nuevo va en `sim/escenarios/pruebas_aisladas/`. `test_escenarios.py` exige que en
  `sim/escenarios/` haya un solo escenario, `prueba_completa`.

## Pruebas que leen textos o archivos de otras carpetas

Si se cambia uno de estos textos o se mueve uno de estos archivos, la prueba falla:

- `app/test_asistente.py`: el corpus del asistente tiene que incluir `README.md`,
  `docs/especificacion.md`, `docs/sensores.md`, `docs/conexiones.md` y `config/parametros.yaml`, y
  buscar "sensor inductivo metal" tiene que encontrar el apartado del inductivo. Si existe
  `docs/electrica.md`, la respuesta sobre el consumo usa sus cifras.
- `visor/test_visualizacion.py`: las anclas de `docs/paso-a-paso.md` y `docs/sensores.md`.
- `sim/test_fisica_vs_3d.py`, `sim/test_carro_impreso.py` y `visor/test_portable.py` leen
  `app/visor3d/visor.js`, `piezas/*.js` y `app/portable.py` con regex. Por eso `visor.js` no se parte.
- `app/test_dashboard.py` busca textos en `app/lanzar.py`. `control/test_carrusel.py` lee
  `control/carrusel.py` con una ruta relativa, así que pytest se corre desde `proyecto-final/`.
- `control/test_tiempos.py` recorre todo el código de `control/`, `sim/`, `app/` y `firmware/`: cada
  clave de `tiempos_ms` y de `errores_sensores` tiene que usarse en alguna parte.
- `sim/test_electrica.py` lee `wokwi/fijo|carro/diagram.json` y `main.py`.
  `sim/test_carro_impreso.py` lee `chasis_impreso/manual.scad`.
- `sim/test_maqueta_impresa.py` corre OpenSCAD (`maqueta.scad` en modo lista) y lee
  `maqueta_impresa/_cache/ens/`. Si falta alguno de los dos, esas pruebas se saltan; no fallan.
  También deja `maqueta_impresa/` en `sys.path` hasta que termina la sesión de pytest.

`sim/test_fisica_vs_3d.py` sirve además como script: `entorno\Scripts\python tests/sim/test_fisica_vs_3d.py`
reescribe [`docs/fisica-vs-3d.md`](../docs/fisica-vs-3d.md).
