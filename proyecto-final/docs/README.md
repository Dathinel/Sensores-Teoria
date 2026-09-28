# Documentos del proyecto

Qué hay en `docs/`. Hay dos clases de documento: los **generados** (salen de una fuente única del
código o de un YAML; no se editan a mano, se regeneran) y los **escritos a mano**.

## Generados (no editar a mano)

Se rehacen todos con `entorno\Scripts\python -m app.documentos`:

- `paso-a-paso.md` — los 17 puntos del sistema con su estado de revisión. Sale de `paso-a-paso.yaml`.
- `sensores.md` — los sensores numerados: qué miden, dónde van y cómo se prueban. Sale de
  `sim/catalogos.py` y de `paso-a-paso.yaml`.
- `componentes.md` — lista de materiales (lo que se compra o se imprime). Sale de `sim/catalogos.py`.
- `conexiones.md` — conexionado pin a pin: módulos, pines y cada hilo. Sale de `sim/conexiones.py`.
- `replicacion.md` — cómo pasar del simulador al montaje real (errores, calibración, tiempos).
- `costos.md` — costo en Colombia por subsistema y ahorros propuestos. Sale de `config/precios.yaml`.

Con su propio comando:

- `pruebas-asistente.md` — batería REAL del asistente: cada frase se le pregunta de verdad al
  modelo y la respuesta se revisa. Se rehace con `python -m app.evaluar_asistente`.

## Escritos a mano

- `paso-a-paso.yaml` — fuente única de los 17 puntos (de aquí salen `paso-a-paso.md` y parte de
  `sensores.md`).
- `bitacora.md` — avance y decisiones sesión por sesión. Es el historial: las rutas viejas que
  menciona se dejan como estaban en su fecha.
- `revision-final.md` — revisión total del diseño antes del protocolo (espacio físico, alcance de
  cada sensor).
- `interfaz-visor.md` — inventario de todas las funciones de la interfaz del visor 3D (lista de
  verificación al rehacerla).
- `interfaz-dashboard.md` — inventario de todas las funciones del dashboard de Streamlit (lista de
  verificación al rehacerlo).

## Carpetas

- `enunciado/` — la guía del parcial (`segundo-parcial-umng.pdf`) y sus figuras numeradas, con su
  propio `README.md`.
- `capturas/` — capturas del visor y del dashboard que usa el `README.md` del proyecto.
