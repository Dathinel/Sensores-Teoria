# Sistema de Logística de Monedas Inteligentes — instrucciones para Claude Code

> **LEER PRIMERO `CONTEXTO-SESION.md`** (mismo directorio): reglas estrictas del usuario, lo
> PROHIBIDO (celdas de carga, sensores difíciles o sensibles, cambios grandes no pedidos) y
> en qué quedó el trabajo. Revisar cada punto del mensaje del usuario uno por uno.

Este archivo vive en la raíz del repositorio y se lee al inicio de cada sesión de trabajo. La
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

Secciones (§) de `docs/especificacion.md`.

| Si se toca | Leer |
|---|---|
| `firmware/**` | §15 y §10.1, `firmware/README.md` |
| `control/**` | §7, §8, §10.2 y la regla 17 de abajo |
| `sim/**` | §11, §10.4, §5 |
| `app/visor3d/**` | `app/visor3d/piezas/README.md`, `docs/interfaz-visor.md` |
| `app/dashboard/**` | §13, `docs/interfaz-dashboard.md` |
| `app/asistente.py` | §14, `docs/modelo-local.md` |
| `app/puente_serial.py`, `app/supervisor.py`, `app/servidor.py` | §10.1, §8 |
| `vision/**` | §12 |
| `config/**` | §6, regla 17 |
| `tests/**` | §11 y `pytest.ini` |
| `docs/**` | `docs/README.md` |
| `wokwi/**` | `wokwi/README.md` |

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
