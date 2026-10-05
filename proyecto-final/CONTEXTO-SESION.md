# Contexto de sesión — LEER ANTES DE TOCAR NADA

Este archivo existe para que una sesión nueva sepa en qué va el proyecto sin gastar miles de
tokens buscando, y sobre todo **qué NO hacer**. Se actualiza al final de cada sesión.

## 0. Pedido EN CURSO (se escribe AL EMPEZAR cada sesión, antes de tocar código)

Por qué existe: dos veces se cerró una sesión a la fuerza a mitad de trabajo y se perdió el
último mensaje del usuario. Regla: al empezar, copiar aquí el pedido textual y la lista de
puntos; al terminar cada punto, marcarlo. Si se pierde un mensaje, está completo en el
transcript de Claude Code: `~/.claude/projects/D--cosas-uni-Micros/<sesion>.jsonl`
(líneas con `"type":"user"`; el más reciente por fecha de modificación).

### Reglas permanentes del usuario

**Reglas permanentes del usuario (2026-09-27):** responder SIEMPRE en español; dejar SIEMPRE la
app corriendo escondida (`python -m app.lanzar --auto prueba_completa --reemplazar` en segundo plano)
para que él vea visor y Streamlit cuando quiera; ahorrar tokens: antes de escribir lógica desde
cero, revisar el repo `Sensores-Teoria` (temas 1-9) que ya tiene patrones resueltos.

- (2026-09-29) Regla nueva: al cerrar cada cambio grande, revisión lógica + visual + docs con agentes.
- Forma de trabajar (usuario, 2026-09-26): dejar SIEMPRE una corrida escondida con el código
  actual (`python -m app.lanzar --auto prueba_completa --reemplazar` en segundo plano; cierra la
  anterior y su consola). El usuario la mira cuando quiere con `visor.bat` (un clic). NO
  abrir consolas visibles ni el navegador del usuario, y NO mandarle links.

**DECIDIDO por el usuario (2026-09-28): ACEPTAR LA ESPERA.** El carrusel real (28BYJ-48 a 500 Hz de medio paso)
tarda 4,1 s en media vuelta (`tiempos_ms.carrusel_giro: 4096`): los 2 chequeos del carrusel en
`control/tiempos.py` quedan NO CABE a propósito (la cinta de monedas espera al carrusel). No cambiar motor ni orden de tubos.

- (2026-09-28, pedido 15) "pase varias revisiones exhaustivas a todo el proyecto, tanto visual como
  lógico, siempre es importante". (Regla permanente: después de cada cambio grande, revisión visual + lógica.)
- Ronda 2 VISUAL: el carrusel todavía soltaba monedas a tubos en movimiento (8 de 15 en vivo, 15-37 mm, 22-40°):
  la planta arrancaba el giro siguiente en el mismo ciclo en que guardaba la moneda (en_ms 0), sin esperar su
  caída. Las pruebas no lo veían (miraban el tubo al guardar, no el giro siguiente). En arreglo: la caída ocupa
  el carrusel (`tiempos_ms.caida_moneda_tubo`), visor respeta en_ms y la pila crece al caer, obturador con tubo
  quieto; medición visual cuadro a cuadro antes/después. Otro agente: detalles del dashboard.
  LECCIÓN: la verificación del timing tiene que ser VISUAL/cuadro a cuadro, no solo con eventos.

**Pedido EN CURSO del 2026-10-02:** "busque Plan orden contextos y haga todo lo que dice ahi" →
`D:\cosas uni\Micros\PLAN-ORDEN-CONTEXTOS.md`. Punto A aprobado por el usuario (plan en
`~\.claude\plans\busque-plan-orden-contextos-giggly-spindle.md`). - [x] A, B1-B5 y C1-C6 TERMINADOS (detalle en `docs/bitacora.md`, 2026-10-02). Sin commit: el usuario decide cuándo se sube.

**Pedido EN CURSO del 2026-10-05 (agente P9 del plan `github\PLAN-APPS-PRACTICAS.md`).** Textual del usuario:
> "corrija eso, y el tema de que se abran con un solo click tiene que ser por practica, y no que mire, un acceso
> directo, tiene que ser mas amigable para un usuario, un tipo programa por practica que dentro tenga todos los
> componentes que se piden de una forma amigable, cada interfaz tiene que ir acomodada a su logica de la practica, si
> es investigacion simplemente leer o que lo mande el repo, si es la camara o asi que sea un tipo aplicacion que diga
> que hace, como se conecta todo amigable y no, abra este .py para saber la simulacion, asi, mas amigable, que con un
> click se puede ver todo lo que pide la practica y que se lleve al usuario mas de la mano igual el tema de los agentes"

Puntos de este proyecto ("corrija eso" = hallazgos del proyecto final + su app):
- [x] 1a. `visor.bat` sin `entorno\` abre la demo grabada sin avisar → que avise; README "Cómo verlo": instalar primero (qué y cuánto tarda); instalador mínimo vs completo.
- [x] 1b. Puerto 8765 fijo (en este PC lo ocupa otro programa) → configurable y, si está ocupado, otro libre automático, dicho claro, y el navegador/dashboard usan el puerto real.
- [x] 1c. Cifras que no coinciden (asistente 50/50, 39 preguntas, 60/60; "más de 850" / "590+" / 928 pruebas) → unificar con el dato real y su fuente.
- [x] 2. App amigable del proyecto en `app-practica/index.html` (portada, recorrido de una moneda, Pruébalo, escenas, asistente, visor portable, resultados, estado honesto, checklist).
  TERMINADOS (P9, 2026-10-05; detalle en `docs/bitacora.md`): `app/puertos.py` (8765 ocupado → siguiente libre, probado aquí: 8766),
  `visor.bat` avisa sin entorno, `instalar.bat` mínima/completa (`requirements-minimo.txt`), cifras 60/60 y 936 pruebas,
  `app/charla.py` + `app-practica/`. Sin commit. La app escondida NO se relanzó (lo hace la sesión principal).

Pedidos cerrados (2 a 17): `docs/historial-pedidos.md`.

## 1. Reglas estrictas del usuario (no negociables)

1. **Si el usuario dice que NO se haga algo, no se hace.** Nunca "mejorarlo" por cuenta propia.
2. **Leer el mensaje del usuario punto por punto**, listar cada pedido y verificar que TODOS
   quedaron atendidos antes de responder. Cada punto está escrito a propósito.
3. **Hacer solo lo que se pidió.** Nada de refactors grandes, mecanismos nuevos o sensores
   nuevos sin pedirlo. Si algo pedido implica un cambio grande o ambiguo: proponerlo en 2-3
   líneas y preguntar ANTES de implementar.
4. **Mundo real, no mundo perfecto:** el montaje se hace en Colombia, con sensores mal
   alineados, alturas distintas, ruido eléctrico, errores de tiempo y de movimiento, brisa,
   aceleraciones que tumban monedas y vasos. Diseñar para el error.
5. Si el usuario pregunta "¿puede asegurarme que X funciona?", responder con honestidad (los
   riesgos reales), no implementar primero.
6. Todo lo que exista en el diseño se modela en el 3D con su soporte (patas de servos,
   escuadras, tornillería visible si hace falta) para juzgar si es realista.
7. No hacer commit ni push sin que el usuario lo pida.

## 2. Prohibido (el usuario lo dijo explícitamente)

- **Celdas de carga** (y HX711): prohibidas. Son difíciles de acondicionar y dan problemas.
- Sensores difíciles de instalar, muy sensibles, caros o poco conocidos.
- Vasos transparentes (el usuario no los quiere).
- Agregar sensores "por si acaso" (el usuario quiere MENOS sensores y MENOS servos).

Preferidos (baratos y conocidos): TCRT5000/FC-51, VL53L0X, HC-SR04, webcam, SG90/MG90S/MG996R.

## 3. Estado actual (2026-09-29, fin de sesión)

**Cierre del 2026-09-29:** pedidos 10 a 17 TERMINADOS y subidos (commit `cb7c86d` en `main`). Solo quedó sin
subir este archivo (el usuario dijo que no hace falta). App escondida corriendo con el código final.
Decisiones vigentes nuevas: carrusel 28BYJ-48 con espera aceptada (media vuelta 4,1 s; la moneda espera en
E4 y además la caída, `caida_moneda_tubo: 400`, ocupa el carrusel); pausa de vasos 1400 ms; rodillo Ø22
(69,1 mm/vuelta); vaso lleno 133 g; prensa 60 N; llanta 26 mm y muelle +4 mm; "detén la línea" = pausa y
PARO solo con "paro"/urgencia; asistente 60/60. Dashboard en 127.0.0.1 con chequeo de salud (antes se caía).
Siguiente (cuando el usuario diga): montaje físico, medir los PROVISIONALES, visión real (fase 5), clave
válida de DeepSeek.

- Pruebas: `entorno/Scripts/python -m pytest -q` → todas deben pasar (936 el 2026-10-05, ~4 min).
  Están por capa en `tests/control`, `tests/sim`, `tests/visor`, `tests/app` y `tests/firmware`
  (una sola capa: `... -m pytest -q tests/control`).
- Paso a paso (`docs/paso-a-paso.yaml`, 17 puntos): 1-15 aprobados; **16 y 17 en pausa (montaje real)**.
- Decisiones vigentes: filtro total (cinta de monedas de 4 estaciones: presencia, material,
  visión, descarga; UNA bandeja de rechazo por la compuerta de desvío); cámara de vasos
  reemplaza barreras IR y sensores de ranura, y además vigila en cada avance que no falte ningún
  vaso en sus 4 casillas; marcador ArUco en CINTA alrededor del vaso; vasos OPACOS; qué hay
  dentro del vaso lo dice un **sensor que apunta hacia el interior del vaso** en la verificación
  (VL53L0X); vasos vacíos se desechan; canaleta llena → el vaso espera y la cinta de vasos se
  detiene; almacén revólver con Hall (aprobado); **cortina de UN solo VL53L0X a media altura,
  con su cono real; al activarse la prensa SUBE y se detiene**; prensa con servo MG996R;
  carro 2 ruedas + rueda loca con rodillos guía, va y vuelve solo (física real en PyBullet).
- Fase 7 (2026-09-27): asistente en `app/asistente.py` (DeepSeek con JSON como el tema 4 del repo;
  busca en toda la documentación; estado en vivo; lista blanca de órdenes; voz; intérprete local sin
  internet). Órdenes al carro por la radio: detener, avanzar, retroceder, girar, ir_a, ir_meta,
  volver_muelle, seguir_linea; odometría (a cero en el muelle), revisa el camino a 0/±15° y no choca;
  desde el muelle sale derecho antes de girar. Evasión automática: `margen_pasar_muro_mm: 70`
  (rozaba el muro con 1 de 11 semillas). Visor: nube de la API + pestaña Asistente (solo lectura).
- **Clave de DeepSeek:** la del tema 4 (`Sensores-Teoria/4-chatbot-asistente-voz/.env`) fue RECHAZADA
  (401). El `.env` del proyecto final tiene la clave que dio el usuario, que también dio 401: hay que
  poner una válida (`.env.example`); mientras tanto responde el modelo local.

Pendientes que quedaron sin cerrar (copiados del historial):
- PENDIENTE tras el carrusel: `;` en el sequenceDiagram de docs/logica-interna.md (~l.346), E5/E7 en
  comentarios de sim/planta.py (l.50, 166, 1313) y "E5" en control/tiempos.py:64 → E3; regenerar docs.
- Pendiente: videos embalaje_vasos/todo_junto sin rellenar las esperas.

## 4. Pendiente de decisión del usuario (no implementar sin respuesta)

(Vacía. Lo que había el 2026-09-29 quedó superado; está en `docs/historial-pedidos.md`.)

## 5. Dónde está cada cosa (para no buscar)

- Instrucciones para Claude Code: `CLAUDE.md` (este mismo directorio). Especificación del proyecto (arquitectura, secciones 1-19): `docs/especificacion.md`. Pedidos cerrados: `docs/historial-pedidos.md`.
- Historial de decisiones: `docs/bitacora.md`. Paso a paso: `docs/paso-a-paso.yaml` (el `.md`
  se genera con `python -m app.documentos`).
- Lógica pura: `control/` (linea.py, embalaje.py, reglas.py, almacen.py, tiempos.py, vehiculo.py).
- Asistente: `app/asistente.py` (+ pestaña en `app/dashboard/pestanas/asistente.py`, `/api/asistente` en `app/servidor.py`,
  pestaña y nube en `app/visor3d/visor.js`). Guía del parcial: `docs/enunciado/`.
- Simulación: `sim/planta.py` (todo el flujo tick a tick), `sim/mundo.py` (PyBullet y medidas),
  `sim/sensores_sim.py`, `control/hal/backend_sim.py`, `sim/geometria.py` (lo que ve el visor).
- Catálogos: `sim/catalogos.py` (13 sensores + lista de materiales).
- Configuración y valores provisionales: `config/parametros.yaml`.
- Pruebas: `tests/<capa>/` (índice en `docs/especificacion.md` §9); escenarios de un solo filtro en
  `sim/escenarios/pruebas_aisladas/`. Índice de los documentos: `docs/README.md`.
- Visor 3D: `app/visor3d/visor.js`. Demo grabada: `python -m app.grabar_demo`.
- Capturas en tiempo real para revisar el 3D (no usar `--virtual-time-budget`, engaña):
  script `captura.mjs` con Chrome headless por CDP (ver bitácora 2026-09-25).
