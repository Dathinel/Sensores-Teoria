# Contexto de sesión — LEER ANTES DE TOCAR NADA

Este archivo existe para que una sesión nueva sepa en qué va el proyecto sin gastar miles de
tokens buscando, y sobre todo **qué NO hacer**. Se actualiza al final de cada sesión.

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

## 0. Pedido EN CURSO (se escribe AL EMPEZAR cada sesión, antes de tocar código)

Por qué existe: dos veces se cerró una sesión a la fuerza a mitad de trabajo y se perdió el
último mensaje del usuario. Regla: al empezar, copiar aquí el pedido textual y la lista de
puntos; al terminar cada punto, marcarlo. Si se pierde un mensaje, está completo en el
transcript de Claude Code: `~/.claude/projects/C--Users-danie-OneDrive-Escritorio-Micors-teoria/<sesion>.jsonl`
(líneas con `"type":"user"`; el más reciente por fecha de modificación).

**Reglas permanentes del usuario (2026-09-27):** responder SIEMPRE en español; dejar SIEMPRE la
app corriendo escondida (`python -m app.lanzar --auto prueba_completa --reemplazar` en segundo plano)
para que él vea visor y Streamlit cuando quiera; ahorrar tokens: antes de escribir lógica desde
cero, revisar el repo `Sensores-Teoria` (temas 1-9) que ya tiene patrones resueltos.

**Pedido del 2026-09-27 (2):** "que el .bat abra un html y, si la simulación está (localhost),
se abra sola sin hacer nada". Es decir: visor.bat abre `visor-portable.html` (un solo archivo:
visor + Three.js + demo grabada, funciona sin servidor ni internet); ese archivo pregunta cada
pocos segundos por `127.0.0.1:8765` y, cuando la simulación responde, la pestaña pasa sola al
visor en vivo.
- [x] a. Generador del HTML portable (python -m app.portable) + demo embebida.
- [x] b. visor.js: base de URLs para file://, datos embebidos, vigía que pasa a vivo solo.
- [x] c. visor.bat abre el portable y arranca la simulación por detrás.
- [x] d. Probar con Chrome headless (file://, con y sin supervisor), pruebas, docs, commit.

**Pedido del 2026-09-27 (3):** "si, haga el cambio de voz, y label o que sea mas evidente en el
visor y en el streamlit que no tiene internet, o esta viendo una demo".
- [x] a. Voz sin internet: reconocimiento local (respaldo del de Google) y voz de respuesta local
  (voces de Windows) cuando gTTS no puede.
- [x] b. Streamlit: aviso grande y visible de "sin internet" (qué sigue funcionando) y de si los
  datos son de la simulación, del hardware real o de una corrida vieja (simulación detenida).
- [x] c. Visor 3D: aviso grande de "DEMO GRABADA" (no en vivo) y de "sin internet" (la nube).
- [x] d. Pruebas, docs, commit.

**Pedido del 2026-09-27 (4):** "cuando abro el bat aparece sin internet en el visor 3d en la parte
de nube de deepseek ... no será porque no está haciendo bien el cambio de html a puerto local, o
porque está sobrepuesto el label de sin internet sobre lo demás, además podría colocarlo en el
label principal, como al lado de los ticks como en streamlit ... creo que ese html cuando se abre
desde el bat está dando problemas adicionales".
- [x] a. Falso "sin internet": el visor revisaba con UN intento al arrancar (escena cargando). En
  vivo decide el supervisor (`/api/internet`, el mismo chequeo que Streamlit); en la demo, varios
  sitios y 2 fallos seguidos.
- [x] b. Chip de internet al lado de los ticks; quitar el letrero encimado de la nube.
- [x] c. Revisar el paso HTML → en vivo desde el .bat (que en vivo todo se actualice).
- [x] d. Pruebas, docs, commit.

**Pedido del 2026-09-27 (5):** "cuando se desconecta de la red, la nube, el visor y streamlit lo
avisan, pero el label de api de deepseek no cambia de estado; me gustaría menos zoom en el visor
del carro y los componentes que lo componen (demasiado cerca); le pedí a ollama 'ahora haga que
vaya a donde está el filtro de monedas, lo atraviese y que el propio sistema lo pase por el lado
con sus sensores' y atoró el carro, revise eso; mejore el README de GitHub, más a detalle de todo
lo que conlleva el proyecto, características especiales, cualidades, cada parte, como si lo
hubiera hecho durante semanas (eso hicimos); que el streamlit se abra con el .bat; revisión final
y dígame qué le falta, qué ve incompleto (sin contar las fotos de las monedas 3D) o qué se le
podría agregar; use multiagentes/subagentes (máximo 4 a la vez) y guárdelos en el contexto para
futuros usos con prácticas que pueda utilizar (tengo uno en mente: modelado de objetos, guardado
en 'Blender with claude'); el resto revíselos".
Datos del atasco: ollama → `ir_a (-0.5, 0.0)` (dentro de la planta) y respondió que "cruzará" el
filtro; el carro salió del muelle y a los 11 s `atascado` → `detenido_atascado` en (0.24, -0.38).
- [x] a. Etiqueta "API de DeepSeek" de la nube cambia con internet (sin encimarse).
- [x] b. Menos zoom en la vista del carro y en sus componentes.
- [x] c. Asistente/carro: rechazar destinos dentro de la planta u obstáculos (y no prometer lo
  imposible); revisar por qué se atoró.
- [x] d. README del repo mucho más completo.
- [x] e. visor.bat abre también el Streamlit.
- [x] f. Revisión final: qué falta, qué está incompleto, qué agregar.
- [x] g. Agentes reutilizables (.claude/agents) + práctica en CLAUDE.md, incl. modelado 3D en
  "Blender with claude".
- [x] h. Pruebas, docs, commit, relanzar.

**Pedido del 2026-09-27 (6):** "haga el punto 2, y en la parte de los sensores del visor 3d, un botón
o algo que se pueda visualizar la prueba única del sensor, y el punto 6 arréglelo también, el de
colocar pieza x me gusta, y guardar todo lo necesario para la ejecución bien del proyecto, y hacer los
scripts también, el resto colóquelos también en lo que falta o pendiente por hacer junto a los demás,
y con esta ayuda de agentes revise las demás prácticas ... crear más agentes de revisar prácticas
anteriores y mejorarlas ... una revisada a cada parámetro de cada práctica nunca viene mal".
Decisión del usuario: prácticas → "Mejorar a fondo". Plan: `~/.claude/plans/complete-todo-lo-que-snappy-liskov.md`.
- [x] a. Prueba de un filtro (dashboard: selector; visor: botón "ver la prueba de este sensor").
- [x] b. "Colocar pieza X" (orden `colocar`, botones en visor y dashboard).
- [x] c. `reversa_tope` con tiempo límite + reintento (agente).
- [x] d. Scripts: `requirements-lock.txt`, `python -m app.chequeo`, `instalar.bat`, `vision/capturar_dataset.py`, `vision/entrenar.py`.
- [x] e. Pendientes de la revisión en README y CONTEXTO.
- [x] f. Agente `revisor-practica` + revisión y mejora a fondo de los temas 1-9 (≤4 agentes a la vez).
- [x] g. Pruebas, capturas, docs, commit, relanzar.

**Pedido del 2026-09-27 (7):** "resuelva la causa de fondo del muelle, como haría el entorno aparte, o
actualizaría todos los .env para que no se tenga que hacer por aparte ... ahora tiene la libertad de
colocar 5 agentes a la vez y la obligación de ayudarlos si se demoran demasiado, revise el tema de
colocar una pieza, hay algo mal ... mejore absolutamente todos los componentes, sensores, objetos,
estructuras y en general todo lo del visor 3d ... con múltiples agentes de modelado ... el carro, la
pista, la laptop, los sensores, y los guarda como modelos reutilizables en blender with claude ...
verificar ... que no se sobrepongan ... y colocar de la forma correcta los cables de todo, cambiando
las posiciones si hace falta, solo en este prompt puede usar 10 agentes máx, lo normal serán 5".
Aclaración del usuario: **NO modelar en Blender ni abrir Blender** (al menos hoy): seguir modelando en
Three.js como hasta ahora, con el contexto de `Blender with claude/`, y guardar las piezas ahí como se
vienen guardando. Plan: `~/.claude/plans/complete-todo-lo-que-snappy-liskov.md`.
- [x] a. Muelle: causa de fondo (0 reintentos en ≥10 semillas).
- [x] b. Keras 3 + torch en el mismo `entorno` (sin `vision/entorno`).
- [x] c. Colocar pieza: el visor dibujaba el euro y el disco como botones perforados; nombres.
- [x] d. Piezas reutilizables en `app/visor3d/piezas/` (+ copia y catálogo en `Blender with claude/`).
- [x] e. Remodelado por zonas: carro+muelle, pista, cinta de monedas+almacén, cinta de vasos, canaleta+pórtico, caja+laptop.
- [x] f. Verificación: solapes, cables, capturas.
- [x] g. Pruebas, docs, commit, relanzar.

## 3. Estado actual (2026-09-27, fin de sesión)

- Pruebas: `entorno/Scripts/python -m pytest -q` → todas deben pasar (623, ~6 min).
- Forma de trabajar (usuario, 2026-09-26): dejar SIEMPRE una corrida escondida con el código
  actual (`python -m app.lanzar --auto prueba_completa --reemplazar` en segundo plano; cierra la
  anterior y su consola). El usuario la mira cuando quiere con `visor.bat` (un clic). NO
  abrir consolas visibles ni el navegador del usuario, y NO mandarle links.
- Correr y mostrar: `entorno/Scripts/python -m app.lanzar --auto prueba_completa` y abrir
  `http://localhost:8765` (visor 3D) y `http://localhost:8501` (dashboard). **NO publicarlo como
  artefacto de Claude**: se abre en el navegador del PC. Si los puertos ya están ocupados es que
  el usuario lo tiene abierto: no cerrarlo; para verificar, levantar una copia en otro puerto.
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

## 4. Pendiente de decisión del usuario (no implementar sin respuesta)

- Revisión final hecha (`docs/revision-final.md`). Sensores de material bajo la cinta APROBADOS.
  Conexionado pin a pin en `sim/conexiones.py` (fuente única → visor, `docs/conexiones.md`,
  `tests/test_conexiones.py`). Punto 15 hecho y APROBADO (protocolo en
  `control/protocolo.py`, contrato en CLAUDE.md 10.1).
  Mejora de interfaz hecha el 2026-09-27 (dashboard para cualquier persona, visor con
  encuadre automático, componentes completos). Fase 7 hecha el 2026-09-27. Siguiente: que el
  usuario apruebe el 15 y el 16, ponga la clave de DeepSeek, y elija la próxima fase (5 visión real,
  8 firmware o 9 documentación para la entrega del 29-09).
- UNA sola prueba en la interfaz: `prueba_completa` (las aisladas quedan en
  `tests/escenarios/`, solo para pytest).
- Soportes de servos (cuna con torres y tornillos), Hall a 4 mm del imán y poste de la cortina corregidos el 2026-09-26; revisar con el usuario.

## 5. Dónde está cada cosa (para no buscar)

- Reglas del proyecto y arquitectura: `CLAUDE.md` (este mismo directorio).
- Historial de decisiones: `docs/bitacora.md`. Paso a paso: `docs/paso-a-paso.yaml` (el `.md`
  se genera con `python -m app.documentos`).
- Lógica pura: `control/` (linea.py, embalaje.py, reglas.py, almacen.py, tiempos.py, vehiculo.py).
- Asistente: `app/asistente.py` (+ pestaña en `app/dashboard.py`, `/api/asistente` en `app/servidor.py`,
  pestaña y nube en `app/visor3d/visor.js`). Guía del parcial: `docs/enunciado/`.
- Simulación: `sim/planta.py` (todo el flujo tick a tick), `sim/mundo.py` (PyBullet y medidas),
  `sim/sensores_sim.py`, `control/hal/backend_sim.py`, `sim/geometria.py` (lo que ve el visor).
- Catálogos: `sim/catalogos.py` (13 sensores + lista de materiales).
- Configuración y valores provisionales: `config/parametros.yaml`.
- Visor 3D: `app/visor3d/visor.js`. Demo grabada: `python -m app.grabar_demo`.
- Capturas en tiempo real para revisar el 3D (no usar `--virtual-time-budget`, engaña):
  script `captura.mjs` con Chrome headless por CDP (ver bitácora 2026-09-25).
