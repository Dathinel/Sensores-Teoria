# `app/`: lo que corre la línea, la muestra y la guarda

El paquete de Python de la aplicación: el supervisor (el proceso que corre la línea y escribe en
SQLite), lo que la muestra (visor 3D, dashboard de Streamlit, asistente) y las herramientas que
escriben archivos generados (los `.md` de `docs/`, la demo del visor y el visor portable). Por qué
son dos procesos y no uno: [§8 de la especificación](../docs/especificacion.md#8-arquitectura-de-software).

No confundir con [`app-practica/`](../app-practica/README.md): esa es la página que abre `ABRIR.bat`
(va aparte justamente porque `app/` es el paquete).

Todo se corre desde `proyecto-final/` con el Python del entorno (`entorno\Scripts\python`, lo crea
`instalar.bat`): `python -m app.<módulo>`.

## Cómo arranca

`python -m app.lanzar --auto prueba_completa` levanta dos procesos y los vigila:

- **supervisor** (`python -m app.supervisor --auto prueba_completa`): corre la simulación tick a tick
  (o habla con el ESP32 fijo por `puente_serial.py` si `hardware.backend: real`), escribe en
  `datos/planta.db` y, en un hilo, sirve el visor 3D y `/api/*` (`servidor.py`) en el 8765.
- **dashboard** (`streamlit run app/dashboard/inicio.py`, en el 8501): solo lee la base y deja
  órdenes en la tabla `ordenes`, que el supervisor consume.

Si el 8765 o el 8501 los tiene otro programa, se usa el siguiente libre (`puertos.py`, hasta 20 más)
y el puerto real queda en `datos/puertos.json`.

| Quién lo llama | Qué corre |
|---|---|
| `visor.bat` | `app.portable --silencioso`, `app.puertos`, abre `visor-portable.html` y, en otra consola, `app.lanzar --auto prueba_completa --abrir-dashboard` |
| `ABRIR.bat` (app de la práctica, acciones de `probar.json`) | `app.lanzar --auto prueba_completa --abrir --abrir-dashboard`, `app.charla` y `app.chequeo --rapido` |
| `instalar.bat` (opción completa) | `app.asistente --preparar-local` (si hay Ollama), `app.asistente --preparar-voz` y `app.chequeo` |

## Qué hace cada módulo

| Módulo | Qué hace | Se corre / lo usa |
|---|---|---|
| `lanzar.py` | Arranca supervisor + dashboard en procesos separados, abre el navegador apenas responden, los reinicia si se caen y cierra la corrida anterior con `--reemplazar`. | `python -m app.lanzar --auto prueba_completa [--abrir] [--abrir-dashboard] [--reemplazar] [--puerto-visor N]` |
| `supervisor.py` | El único proceso que toca la simulación (o las placas): consume órdenes, da un tick de la planta, guarda eventos y telemetría. | `lanzar.py`; solo: `python -m app.supervisor --auto prueba_completa [--bd RUTA]` |
| `servidor.py` | HTTP del supervisor (biblioteca estándar): el visor 3D, `/api/estado`, `/api/geometria`, `/api/pasos`, `/api/internet`, `/api/asistente` y `POST /api/orden`. | hilo dentro del supervisor |
| `db.py` | Esquema de SQLite (eventos, elementos, vasos, ruta, órdenes, asistente, almacén entre turnos), `conectar`, `copiar_base`, `reiniciar_corrida`. | supervisor, dashboard, asistente, charla, evaluar_asistente |
| `puertos.py` | Qué puerto usa el visor en vivo (`--puerto-visor`, `PLANTA_PUERTO_VISOR` o `supervisor.puerto_http`) y el siguiente libre si está ocupado. | `python -m app.puertos` (código 2 si alguno cambia) |
| `puente_serial.py` | PC ↔ ESP32 fijo por USB, con la lógica de `control/protocolo.py`; sin placa, una estación emulada. | supervisor en modo real; diagnóstico: `python -m app.puente_serial` |
| `asistente/` | El asistente (paquete). Ver [su README](asistente/README.md). | pestaña Asistente, `charla.py`, `evaluar_asistente.py`, `servidor.py` |
| `charla.py` | Charla por consola con el asistente sobre una COPIA de la base (las órdenes no llegan a la línea). | `python -m app.charla [--ollama]`; acción "asistente" de `probar.json` |
| `evaluar_asistente.py` | Batería de preguntas reales al asistente → `docs/pruebas-asistente.md`. | `python -m app.evaluar_asistente [--usar reglas\|ollama\|deepseek\|auto]` |
| `dashboard/` | El Streamlit. Ver [su README](dashboard/README.md). | `lanzar.py` |
| `visor3d/` | El visor 3D (Three.js, sin build). Ver [su README](visor3d/README.md). | `servidor.py`, `portable.py` |
| `configuracion.py` | `ruta_bd()` (la base; `PLANTA_BD` la cambia en las pruebas) y la reexportación de `control/configuracion.py`. | casi todo `app/` |
| `rutas.py` | `RAIZ`, `CONFIG`, `DATOS`, `DOCS`, `VISOR`: las carpetas del proyecto en un solo lugar, sin dependencias. | todo `app/` |
| `costos.py`, `masas.py` | Costo en Colombia (`config/precios.yaml`) y peso con comprobaciones de par (`config/masas.yaml`). | `documentos.py`, pestaña Montaje real, asistente; `python -m app.masas` imprime el resumen |
| `documentos.py` | Escribe 8 `.md` de `docs/` desde sus fuentes (paso a paso, replicación, componentes, sensores, conexiones, costos, peso, eléctrica). No se editan a mano. | `python -m app.documentos` |
| `grabar_demo.py` | Corre la planta sin ventana y guarda la corrida que reproduce el visor sin servidor → `visor3d/demo/*.json`. | `python -m app.grabar_demo` |
| `portable.py` | Arma `visor-portable.html` (~9,4 MB): el visor, Three.js, los dos GLB y la demo en un solo archivo. | `python -m app.portable [--silencioso]`; `visor.bat` |
| `chequeo.py` | Revisa sin cambiar nada lo que puede fallar antes de presentar (versiones, puertos, Ollama, voz, internet, placas, portable al día). | `python -m app.chequeo [--rapido]` |

## Reglas

- **Rutas**: todo módulo de `app/` toma sus carpetas de `app/rutas.py`
  (`from app.rutas import RAIZ, DOCS, VISOR`), nunca de `Path(__file__).parent.parent`: así un
  módulo se puede mover dentro de `app/` sin romper nada. La única excepción es
  `dashboard/inicio.py`, que arma la raíz a mano porque corre antes de que `app` sea importable.
- **Configuración**: `config/parametros.yaml` se lee con `control/configuracion.py`
  (`cargar_parametros`, `parametros_filtrado`). `app/configuracion.py` lo reexporta y agrega
  `ruta_bd`. Desde `sim/`, `control/` o `firmware/` se importa `control.configuracion`, no
  `app.configuracion`: esas carpetas no dependen de `app/`.
- **Dos procesos** (§8): solo el supervisor toca la simulación y el puerto serial. El dashboard no
  importa PyBullet ni pyserial y escribe en la base únicamente por la tabla `ordenes`.
- **Generados iguales**: `python -m app.grabar_demo` y `python -m app.documentos` tienen que dejar
  `visor3d/demo/` y `docs/` sin cambios si no cambió el comportamiento
  (`git diff --stat -- app/visor3d/demo docs` vacío). `docs/paso-a-paso.yaml` es la fuente de
  `docs/paso-a-paso.md` y de `visor3d/demo/pasos.json`: si se toca, se corren los dos.
- **Nombres que se usan desde afuera**: los `-m app.<módulo>` de `visor.bat`, `instalar.bat` y
  `probar.json`; `lanzar.py` reconoce una corrida vieja buscando `app.supervisor`, `app/dashboard`
  y `app.lanzar` en la línea de comandos (lo exige `tests/app/test_dashboard.py`). Renombrar un
  módulo obliga a cambiarlos todos.

Pruebas: `tests/app/` y `tests/visor/` (`entorno\Scripts\python -m pytest -q tests/app tests/visor`).
