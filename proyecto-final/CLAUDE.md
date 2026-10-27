# Sistema de Logística de Monedas Inteligentes — instrucciones para Claude Code

> **LEER PRIMERO `CONTEXTO-SESION.md`** (mismo directorio): reglas estrictas del usuario, lo
> PROHIBIDO (celdas de carga, sensores difíciles o sensibles, cambios grandes no pedidos) y
> en qué quedó el trabajo. Revisar cada punto del mensaje del usuario uno por uno.

Este archivo vive en la raíz de `proyecto-final/` y se lee al inicio de cada sesión de trabajo. La
fuente de verdad del proyecto es `docs/especificacion.md` (secciones 1-19, misma numeración de
siempre). Si una instrucción puntual del usuario contradice la especificación, gana la
instrucción puntual y se actualiza la especificación al terminar.

---

## Cómo usar la especificación (antes sección 0)

Lea primero las secciones 1 a 3 para entender qué se entrega y por qué. La sección 5 es la
descripción funcional completa del sistema y es la referencia contra la cual se valida
cualquier implementación. Las secciones 8 a 15 definen la arquitectura de software y los
contratos que no se deben romper. La sección 16 es el plan de trabajo por fases: antes de
escribir código, identifique en qué fase está el repositorio y trabaje solo sobre la fase
actual. La sección 17 (reglas del agente) está abajo, en este archivo.

Estado real de las fases: sección 16 de la especificación (fases 7 y 8 hechas en software; la 5, visión real, pendiente).

## Grupo 7

Elemento 7: detector de elementos de monedas y vasos (sección 2 de la especificación). No implementar los elementos de los otros grupos del PDF.

## Dónde leer según lo que se toque

Secciones (§) de `docs/especificacion.md`. Cada carpeta tiene su `README.md` (qué hay, cómo se corre, contratos).

| Si se toca | Leer |
|---|---|
| `app/` (supervisor, servidor, puente serial, lanzar, puertos, db, rutas, documentos) | `app/README.md`, §8, §10.1, §10.3 |
| `app/asistente/` | `app/asistente/README.md`, §14, `docs/modelo-local.md` |
| `app/dashboard/` | `app/dashboard/README.md`, §13, `docs/interfaz-dashboard.md` |
| `app/visor3d/` | `app/visor3d/README.md`, `docs/interfaz-visor.md` |
| `app/visor3d/piezas/` | `app/visor3d/piezas/README.md` |
| `app-practica/` | `app-practica/README.md`, `probar.json`, `../_lanzador/LEEME.md` |
| `chasis_impreso/` | `chasis_impreso/CLAUDE.md` (ya impreso: no regenerar) y `chasis_impreso/README.md` |
| `config/` | `config/README.md`, §6, regla 17 |
| `control/` | `control/README.md`, §7, §8, §10.2 y la regla 17 de abajo |
| `docs/` | `docs/README.md` (qué se genera y qué se escribe a mano) |
| `firmware/` | `firmware/README.md`, §15 y §10.1 |
| `maqueta_impresa/` | `maqueta_impresa/CLAUDE.md` (orden de trabajo, sello, `3mf/`), `maqueta_impresa/README.md` y `CONVENCIONES.md` |
| `sim/` | `sim/README.md`, §11, §10.4, §5 |
| `simulaciones/` | `simulaciones/README.md` |
| `tests/` | `tests/README.md`, §11 y `pytest.ini` |
| `vision/` | `vision/README.md`, §12 |
| `wokwi/` | `wokwi/README.md` |

## Lo que no se mueve ni se renombra

| Qué | Por qué |
|---|---|
| `proyecto-final/` y su `README.md` (y los títulos de sus secciones) | El Word entregado a la universidad enlaza `.../blob/main/proyecto-final/README.md`; otras páginas y `docs/` enlazan sus anclas. |
| `ABRIR.bat`, `abrir.sh`, `probar.json` | Lanzador común del repo: los `.bat`/`.sh` llaman a `../_lanzador/lanzador.py` y el lanzador busca `*/probar.json`; `../.gitattributes` fija los fines de línea de `*.bat` y `abrir.sh`. |
| `pytest.ini`, `.streamlit/` | Configuración de pytest (`tests/`, raíz importable) y tema del dashboard; `app/lanzar.py` arranca con `cwd` en esta carpeta. |
| `visor-portable.html` | Lo nombran `visor.bat`, `probar.json`, `../.gitattributes` y la regla `visor-animacion.md`. |
| `CLAUDE.md`, `CONTEXTO-SESION.md` | Los nombra `D:\cosas uni\Micros\CLAUDE.md` (qué leer al tocar el proyecto). |
| `app/`, `app/visor3d/` (con `piezas/`, `vendor/`, `demo/`), `app/dashboard/` | Paquetes que se corren con `-m`; rutas en `../.gitattributes` (`demo/*.json`, `vendor/**`) y globs de las reglas (`**/visor3d/**`, `**/visor3d/piezas/**`, `**/dashboard/**`, `**/app/**`). Las piezas tienen copia en `Modelado 3D/piezas-threejs`. |
| `app-practica/` | Campo `"app"` de `probar.json` (no se llama `app/` porque esa es el paquete). |
| `firmware/` (`fijo/`, `carro/`, `comun/`, `preparar.py`, `subir.py`) | `python -m firmware.subir fijo/carro`, `instalar.bat` y la regla `micropython-esp32.md` (`**/firmware/**`). |
| `wokwi/` | Glob `**/wokwi/**` de la regla de MicroPython; los proyectos de wokwi.com. |
| `sim/ver/` | `simulaciones/*.bat` y `probar.json` corren `-m sim.ver.*`. |
| `sim/conexiones.py` | 8 scripts de `D:\cosas uni\Modelado 3D` lo leen por ruta absoluta. |
| `docs/` sin subcarpetas nuevas | Enlaces con ancla, el corpus del asistente (`app/asistente/conocimiento.py`, lista fija de `docs/*.md`) y los generadores escriben ahí. |
| `control/protocolo.py`, `control/vehiculo.py` | `firmware/preparar.py` los copia a la placa con ese nombre. |
| `maqueta_impresa/3mf/` | El usuario imprime desde ahí; `alm_1/2/3.3mf` los guardó Creality Print sin commit: no se tocan ni se restauran. |
| `chasis_impreso/` | El carro ya está impreso y armado: no se regenera nada ni cambia la geometría. |
| `app/visor3d/visor.js` entero | Las pruebas lo leen con regex: no se parte. |

## Quién nos nombra desde afuera

| Quién (fuera de `proyecto-final/`) | Qué nombra |
|---|---|
| El Word entregado a la universidad (`Enlace README - Proyecto final.docx`, local) | `.../blob/main/proyecto-final/README.md` |
| `../_lanzador/` (lanzador común) | `probar.json` (acciones, `"app": "app-practica/index.html"`), `entorno/` de esta carpeta; `ABRIR.bat` y `abrir.sh` lo llaman |
| `../.gitattributes` | `visor-portable.html`, `app/visor3d/demo/*.json`, `app/visor3d/vendor/**`, `maqueta_impresa/scad/estructura_gen.scad`, `maqueta_impresa/salida/piezas.json`, `chasis_impreso/salida/piezas.json` |
| `../4-chatbot-asistente-voz/README.md` | `app/asistente/` |
| `../README.md` y `../1-esp32-investigacion/README.md` | `proyecto-final/`, `ABRIR.bat`, `chasis_impreso/`, `maqueta_impresa/`, `docs/enunciado/1-arquitectura-general.png`; `firmware/` |
| `D:\cosas uni\Micros\.claude\rules\*.md` (globs) | `**/visor3d/piezas/**` (blender), `**/asistente*.py`, `**/*asistente*/**`, `**/evaluar_asistente.py`, `**/modelo-local.md` (modelos locales), `**/app/**`, `**/dashboard/**` (Streamlit), `**/firmware/**`, `**/wokwi/**` (MicroPython), `**/visor3d/**`, `**/visor-portable.html` (visor) |
| 8 scripts de `D:\cosas uni\Modelado 3D` (`blender_helpers.py`, `herramientas/importar_pieza.py`, `componentes/**/revisar_pines.py`, `componentes/**/aplicar_ajustes.py`) | `sim/conexiones.py` (ruta absoluta) |
| Las placas (vía `firmware/preparar.py`) | `control/protocolo.py` y `control/vehiculo.py` |

Si se cambia algo de esta tabla, se corrige también del otro lado (o se avisa si está fuera del repo).

## Reglas de código

- Las carpetas, en `app/`, salen de `app/rutas.py` (`RAIZ`, `CONFIG`, `DATOS`, `DOCS`, `VISOR`): nada de `Path(__file__).parent.parent`
  (única excepción: `app/dashboard/inicio.py`, que pone la raíz en `sys.path` antes de poder importar `app`).
- La configuración se lee con `control/configuracion.py` (`cargar_parametros`, umbrales del filtro). `app/configuracion.py`
  solo agrega `ruta_bd` y lo reexporta; `sim/`, `control/` y `firmware/` no importan de `app/`.
- Pruebas del asistente: se parchea el submódulo donde se busca el nombre (`asistente.llm.cliente_local`,
  `preguntar_deepseek`, `preguntar_llm`; `asistente.audio.hay_internet`, `transcribir_local`, `voz_local`, `_whisper_modelo`),
  no el paquete. `asistente.MODELO_LOCAL` se lee siempre de `llm`.
- Qué Python: el entorno (`entorno\Scripts\python`) para pytest y todo `-m app.*`, `-m sim.*`; el del sistema (`python`, con
  scipy y reportlab, que el entorno no tiene) para `maqueta_impresa/` y `chasis_impreso/` (revisores, exportadores y
  manuales PDF), corridos desde su carpeta: esos scripts agregan `proyecto-final/` al `sys.path` solos.

## Antes de dar algo por terminado

- [ ] `entorno\Scripts\python -m pytest -q` completo (951 pruebas, ~4-5 min).
- [ ] Si se tocó la maqueta, desde `maqueta_impresa/`: `python revisar.py --sin-render` (TODO OK y sello vigente) y `python probar_revisor.py`.
- [ ] Desde la raíz del repo: `python _lanzador/revisar_enlaces.py proyecto-final` y `python _lanzador/lanzador.py --comprobar`.
- [ ] `entorno\Scripts\python -m app.documentos` y `git diff --stat docs`: solo cambia lo que se quiso cambiar.
- [ ] Si cambia la demo o `docs/paso-a-paso.yaml`: `entorno\Scripts\python -m app.grabar_demo` (rehace `pasos.json` y el portable).
- [ ] Nunca `git add -A` a secas (los `alm_*.3mf` del usuario): `git add -A -- proyecto-final ':!proyecto-final/maqueta_impresa/3mf'`
  desde la raíz del repo, y solo si el usuario pidió commit.

---

## 17. Reglas para el agente

Trabaje siempre sobre la fase actual. Si encuentra trabajo pendiente de una fase anterior,
termínelo antes de avanzar.

No importe PyBullet, pyserial ni OpenCV desde `control/`. Si necesita hardware o percepción
desde ahí, es señal de que falta un método en la HAL.

No invente valores de hardware. Si falta un dato físico, como la altura del vaso o el
diámetro del rodillo, escríbalo en `config/parametros.yaml` con un valor provisional
claramente marcado y menciónelo al usuario en vez de enterrarlo en el código.

Todo número mágico va a configuración: umbrales de confianza, rangos de diámetro,
tolerancia de coherencia, duración de pausas, velocidades.

Escriba pruebas para la capa de control y para las reglas de decisión. La simulación no
sustituye a las pruebas: es lenta y visual, las pruebas son rápidas y verificables.

Comentarios y documentación en español. Nombres de variables y funciones en español
también, para que el código sea legible en la sustentación.

No hacer commit ni push sin que el usuario lo pida (regla 7 de `CONTEXTO-SESION.md`).

No agregue dependencias pesadas sin justificarlas. El proyecto debe correr en un portátil
de estudiante sin GPU.

Cuando una decisión de diseño tenga alternativas reales, expóngalas con sus ventajas y
desventajas antes de implementar, en lugar de elegir en silencio.
