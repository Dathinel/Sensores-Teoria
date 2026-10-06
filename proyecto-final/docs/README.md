# Documentos del proyecto

Qué hay en `docs/`. Hay dos clases de documento: los **generados** (salen de una fuente única del
código o de un YAML; no se editan a mano, se regeneran) y los **escritos a mano**.

Para no confundirse con los nombres: **cómo se hizo** el proyecto, en orden y con lo que falló, está en
[`bitacora.md`](bitacora.md) (resumido en el [Paso a paso del README](../README.md#1-cómo-se-hizo-paso-a-paso));
[`paso-a-paso.md`](paso-a-paso.md) son los **17 puntos del funcionamiento** de la máquina; y **cómo probarlo**
(con la app, sin ella y con el montaje real) está en el [README](../README.md#paso-a-paso).

## Generados (no editar a mano)

Se rehacen todos con `entorno\Scripts\python -m app.documentos`:

- `paso-a-paso.md` — los 17 puntos del sistema con su estado de revisión. Sale de `paso-a-paso.yaml`.
- `sensores.md` — los sensores numerados: qué miden, dónde van y cómo se prueban. Sale de
  `sim/catalogos.py` y de `paso-a-paso.yaml`.
- `componentes.md` — lista de materiales (lo que se compra o se imprime). Sale de `sim/catalogos.py`.
- `conexiones.md` — conexionado pin a pin: módulos, pines y cada hilo. Sale de `sim/conexiones.py`.
- `replicacion.md` — cómo pasar del simulador al montaje real (errores, calibración, tiempos).
- `costos.md` — costo en Colombia por subsistema, la estructura 3D pieza por pieza y ahorros
  propuestos. Sale de `config/precios.yaml`.
- `peso.md` — peso de todo el montaje y si cada motor alcanza. Sale de `config/masas.yaml`.
- `electrica.md` — parte eléctrica simulada: corriente de cada riel en un ciclo real, cada hilo con
  su voltaje y corriente, pasivos. Sale de `sim/electrica.py` (también `python -m sim.electrica`).

Con su propio comando:

- `pruebas-asistente.md` — batería REAL del asistente: cada frase se le pregunta de verdad al
  modelo y la respuesta se revisa. Se rehace con `python -m app.evaluar_asistente`.
- `fisica-vs-3d.md` — la física de PyBullet comparada con el 3D, medida por medida. Se rehace con
  `python tests/sim/test_fisica_vs_3d.py`.

## Escritos a mano

- `especificacion.md` — la especificación del proyecto, secciones 1-19 (antes en el `CLAUDE.md` de la raíz).
- `historial-pedidos.md` — pedidos del usuario ya cerrados (salieron de `CONTEXTO-SESION.md`).
- `paso-a-paso.yaml` — fuente única de los 17 puntos (de aquí salen `paso-a-paso.md` y parte de
  `sensores.md`).
- `bitacora.md` — avance y decisiones sesión por sesión. Es el historial: las rutas viejas que
  menciona se dejan como estaban en su fecha.
- `logica-interna.md` — cómo decide el sistema, con el código real; primero el filtrado de monedas.
- `modelo-local.md` — el modelo de lenguaje local (Qwen2.5-3B): arquitectura, cómo se usa y por qué.
- `revision-final.md` — revisión total del diseño antes del protocolo (espacio físico, alcance de
  cada sensor).
- `interfaz-visor.md` — inventario de todas las funciones de la interfaz del visor 3D (lista de
  verificación al rehacerla).
- `interfaz-dashboard.md` — inventario de todas las funciones del dashboard de Streamlit (lista de
  verificación al rehacerlo).

## Carpetas

- `enunciado/` — la guía del parcial (`segundo-parcial-umng.pdf`) y sus figuras numeradas, con su
  propio `README.md`.
- `videos/` — las simulaciones de PyBullet grabadas, con `python -m sim.ver.grabar`: un mp4 por escena y un GIF liviano de las tres que el README muestra en línea (`todo_junto` va solo en mp4).
- `capturas/` — capturas del visor y del dashboard que usa el `README.md` del proyecto.
