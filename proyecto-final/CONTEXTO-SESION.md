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
transcript de Claude Code: `~/.claude/projects/D--cosas-uni-Micros/<sesion>.jsonl`
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

**Pedido del 2026-09-28 (8):** "revise esas 2 cosas que quedaron pendientes, me gustaría que optimizara
un poco el visor 3d, ya que quedó algo pesado pero sin quitarle detalle, y también algunos materiales
o zonas como la parte interna del teclado o los muros quedaron parpadeando, de resto quedó excelente
... también utilice ese nivel de orden y detalle para rehacer la parte gráfica del visor y del
streamlit sin perder funcionalidades, ya que fue hecho por tantas partes que se pierde la línea y por
tantos prototipos que se mira feo, si la quiere rehacer de 0 hágala, pero que no se pierdan
funcionalidades, igual con streamlit, tanto las pruebas que están desordenadas como los componentes,
y así, trate de darle orden a todo, igual que a los archivos del proyecto ... revisiones de cómo queda
todo, lo de siempre, posiblemente se quede sin tokens a mitad, pero lo sigue haciendo hasta que vuelva
a tener". Plan: `~/.claude/plans/complete-todo-lo-que-snappy-liskov.md`. Medido: 3.257 mallas,
2.629 materiales, 0,62 M triángulos; cámara near 0,005 / far 30 (causa del parpadeo).
- [x] B. Pendientes: laptop y hub en el mapa de zonas del carro (config `puesto_pc`, el visor los lee de ahí); cable del obturador con brazo portacables (revisar su captura en F).
- [x] A. Rendimiento (< 500 draw calls, mismo detalle) y parpadeos (near dinámico, caras coplanares).
- [x] C. Streamlit rehecho (paquete `app/dashboard/`, mismo diseño que el visor, nada perdido).
- [x] D. Interfaz del visor rehecha (`interfaz.js`, controles de prueba ordenados, componentes).
- [x] E. Orden del proyecto: tests por capa (control/sim/visor/app/firmware), escenarios de un filtro en `sim/escenarios/pruebas_aisladas/`, `pytest.ini` + `tests/conftest.py`, `docs/README.md`, árbol en CLAUDE.md/README (659 pruebas pasan).
- [x] F. Revisión final (capturas de todo, inventarios de funciones), commit, app escondida.

**Pedido del 2026-09-28 (9):** "arregle los pendientes menores que quedaron".
- [x] a. `Supervisor.cerrar()`: soltar su conexión de PyBullet (la planta y el carro).
- [x] b. Vista "Material" y foco de los M18 (2 y 3): se ven chicos y entre vigas.
- [x] c. Etiquetas 3D que quedan bajo la barra de vistas / botones cerca del borde de arriba.
- [x] d. Streamlit a 900 px con la barra lateral abierta: el mapa del carro se aplasta; columnas angostas; tablas de Montaje con desplazamiento horizontal.
- [x] e. Aviso `Recording error: Container not found` del micrófono en la primera carga del Asistente.

**Pedido del 2026-09-28 (10):** "para el proyecto final haga estas cositas de arreglos hablados con el
equipo, peso total de la cinta, costos en estructura 3d completos, en tablas y todo, prioridad con el
filtrado de monedas, nuestra parte, no tanto el transporte, llm enfocado a la parte de monedas y
movimiento de el carro pero sin dejar de lado lo demas, arquitectura de diagrama del modelo qwen2.5,
como se uso el modelo local, porque, su estructura, todo, tabla de costos, parte eléctrica punto por
punto con voltajes, valores, cada conexion, como si fuera simulado, lógica usada interna bien explicada
y detallada, simulaciones de pybullet con física para visualización de el evaluador y revisar que la
física si cumple con la parte 3d, mas que todo son cosas que pedia el profe".
Respuestas: todo en docs del repo + README; eléctrica = simulación Python + tablas + Wokwi; peso = TODO
el montaje; PyBullet = todo (GUI por escena, todo junto, videos) con el video en el README y fácil de
abrir (.bat / carpeta para elegir). Plan: `~/.claude/plans/para-el-proyecto-final-goofy-puffin.md`.
- [x] a. Costos de la estructura 3D completos (piezas impresas, perfil, tornillería) en tablas. Total
  nuevo $1.998.921; estructura 3D $716.675 (73 piezas, 957 g PLA; perfil medido 6,10 m).
- [x] b. Peso total del montaje (`config/masas.yaml` → `docs/peso.md`) + chequeos de par. 13,38 kg.
  PREGUNTAR: MG996R de la prensa NO alcanza los 150 N del catálogo (sí 50 N); rodillo Ø22 del 3D vs
  `mm_por_vuelta_cinta: 40` (= Ø12,7); masa_vaso_lleno_kg 0,10 vs 0,133 sumado.
- [x] c. Eléctrica simulada (`sim/electrica.py` → `docs/electrica.md`) + `wokwi/`. Encontró 6 diferencias
  firmware ↔ diseño (sin corregir, PREGUNTAR): prensa+empujador a la vez no bloqueado en firmware; PWM del
  carro sin tope de 70 %; I2C largo a 400 kHz (diseño 100 kHz); A4988 sin corriente de reposo reducida;
  5 V del carro lineal vs buck; carrusel 1,37 s por tubo vs `carrusel_giro: 500`.
- [x] d. Asistente con foco en monedas y carro (sin dejar lo demás) + batería.
- [x] e. `docs/modelo-local.md` (qwen2.5: arquitectura, por qué local, cómo se usó).
- [x] f. PyBullet GUI por escena + `simulaciones.bat` + videos/GIF.
- [x] g. Física vs 3D (prueba + `docs/fisica-vs-3d.md`).
- [x] h. `docs/logica-interna.md` (filtrado de monedas primero).
- [x] i. README con prioridad al filtrado, links y videos; índices.
- [x] j. Revisión final (revisor-final + correcciones), 740 pruebas, demo/portable regenerados, app escondida. Sin git.

**Pedido del 2026-09-28 (11), en paralelo al (10):** "recuerde que todo tiene que estar bien explicado en
el readme de el proyecto, igual que los readme de todas las demas practicas subidas a github, todo se
tiene que entender perfectamente, como funciona, conexiones, que se hizo, que hace cada archivo, su
logica, y varios archivos de el github que le dije que los mejorara no toco eso, tiene habilitado 5
agentes mas unicamente para mejorar los read me de las demas actividades subidas a github, tendria que
manejar 2 ideas al mismo tiempo, le recomiendo que haga un paso a paso para no confundirse".

PASO A PASO (dos líneas de trabajo, no mezclarlas):
- LÍNEA A — proyecto final (pedido 10, 4 agentes + sesión principal): puntos a-j de arriba. El README
  del proyecto final debe explicar TODO: cómo funciona, conexiones, qué se hizo, qué hace cada archivo,
  su lógica (sección "qué hace cada archivo" completa, no solo el árbol).
- LÍNEA B — READMEs de los temas 1-9 (5 agentes `documentador-readme`, SOLO README.md de su tema):
  - [x] B1. 1-esp32-investigacion + 2-lenguajes-thonny (duda para el usuario: ¿display de 7 segmentos
    de cátodo o ánodo común en Wokwi?)
  - [x] B2. 3-deteccion-objetos + 4-chatbot-asistente-voz (encontrado, sin tocar código: tema 4 reglas
    "enciende rojo y apaga azul" apaga los dos; Wokwi del tema 4 con pines 27/26 ≠ código 25/26)
  - [x] B3. 5-parcial-figuras-lissauer + 6-control-de-led-mediante-gestos (encontrado, sin tocar código:
    en gesture_control.html modo persistente, puño → pulgar → puño no reenvía FIST; resistencias del
    tema 6 sin valor conocido; pez1 de pez5 se sale 19 puntos del borde)
  - [x] B4. 7-brazo-robotico-urdf + 8-digitos-brazo-y-vision (README raíz del tema y de sus 2 puntos)
  - [x] B5. 9-taller-segundo-corte (README raíz del tema y de sus 3 puntos)
  - [x] B6. Sesión principal

**Pedido del 2026-09-28 (12):** "tema 2, catodo comun, error en tema 6, arregle el error, 330 ohmios, tema 4,
corrijalo, y justifique porque cambia la imagen con lo montado, corrija los errores del tema 7 y 8, ajuste
el firware del proyecto final, el tema de el rodillo es como propiamente lo tomo calude, se basa en lo
registrado y los valores dados, segun mi logica tendria que ser igual al de el 3d, tome el vaor de el vaso
mas logico, depende de como sea el sellado de la tapa al vaso, tambien sacado por la propia logica de claude".
- [x] 12a. Tema 2: display de cátodo común (README).
- [x] 12b. Tema 6: arreglar puño→pulgar→puño en gesture_control.html; resistencias 330 Ω en README.
- [x] 12c. Tema 4: arreglar "enciende rojo y apaga azul" en las reglas; README: por qué la imagen de Wokwi difiere del montaje.
- [x] 12d. (+ el mismo comentario en el tema 9) Temas 7 y 8: comentarios desactualizados.
- [x] 12e. Firmware proyecto final: bloqueo prensa+empujador, tope PWM 70 % carro, I2C largo a 100 kHz,
  reposo del A4988, tiempo real del carrusel.
- [x] 12f. Rodillo = el del 3D (Ø22 → mm_por_vuelta 69,1). Vaso lleno y fuerza de prensa: valor lógico según
  el sellado de la tapa (decidir y justificar).: revisar los 9 READMEs y el índice raíz `Sensores-Teoria/README.md`.

## 3. Estado actual (2026-09-27, fin de sesión)

- Pruebas: `entorno/Scripts/python -m pytest -q` → todas deben pasar (740 el 2026-09-28, ~3 min).
  Están por capa en `tests/control`, `tests/sim`, `tests/visor`, `tests/app` y `tests/firmware`
  (una sola capa: `... -m pytest -q tests/control`).
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
  `tests/sim/test_conexiones.py`). Punto 15 hecho y APROBADO (protocolo en
  `control/protocolo.py`, contrato en CLAUDE.md 10.1).
  Mejora de interfaz hecha el 2026-09-27 (dashboard para cualquier persona, visor con
  encuadre automático, componentes completos). Fase 7 hecha el 2026-09-27. Siguiente: que el
  usuario apruebe el 15 y el 16, ponga la clave de DeepSeek, y elija la próxima fase (5 visión real,
  8 firmware o 9 documentación para la entrega del 29-09).
- UNA corrida normal en la interfaz: `prueba_completa`. Las de un solo filtro (y el mixto de 20)
  están en `sim/escenarios/pruebas_aisladas/`: las usan pytest y la "prueba de un filtro" de la interfaz.
- Soportes de servos (cuna con torres y tornillos), Hall a 4 mm del imán y poste de la cortina corregidos el 2026-09-26; revisar con el usuario.

## 5. Dónde está cada cosa (para no buscar)

- Reglas del proyecto y arquitectura: `CLAUDE.md` (este mismo directorio).
- Historial de decisiones: `docs/bitacora.md`. Paso a paso: `docs/paso-a-paso.yaml` (el `.md`
  se genera con `python -m app.documentos`).
- Lógica pura: `control/` (linea.py, embalaje.py, reglas.py, almacen.py, tiempos.py, vehiculo.py).
- Asistente: `app/asistente.py` (+ pestaña en `app/dashboard/pestanas/asistente.py`, `/api/asistente` en `app/servidor.py`,
  pestaña y nube en `app/visor3d/visor.js`). Guía del parcial: `docs/enunciado/`.
- Simulación: `sim/planta.py` (todo el flujo tick a tick), `sim/mundo.py` (PyBullet y medidas),
  `sim/sensores_sim.py`, `control/hal/backend_sim.py`, `sim/geometria.py` (lo que ve el visor).
- Catálogos: `sim/catalogos.py` (13 sensores + lista de materiales).
- Configuración y valores provisionales: `config/parametros.yaml`.
- Pruebas: `tests/<capa>/` (índice en CLAUDE.md §9); escenarios de un solo filtro en
  `sim/escenarios/pruebas_aisladas/`. Índice de los documentos: `docs/README.md`.
- Visor 3D: `app/visor3d/visor.js`. Demo grabada: `python -m app.grabar_demo`.
- Capturas en tiempo real para revisar el 3D (no usar `--virtual-time-budget`, engaña):
  script `captura.mjs` con Chrome headless por CDP (ver bitácora 2026-09-25).

**DECIDIDO por el usuario (2026-09-28): ACEPTAR LA ESPERA.** El carrusel real (28BYJ-48 a 500 Hz de medio paso)
tarda 4,1 s en media vuelta (`tiempos_ms.carrusel_giro: 4096`): los 2 chequeos del carrusel en
`control/tiempos.py` quedan NO CABE a propósito (la cinta de monedas espera al carrusel). No cambiar motor ni orden de tubos.

**Pedido del 2026-09-28 (13), respuestas del usuario:** llanta del carro = 26 mm (la TT real) en la física
Y ensanchar la boca/guías del muelle lo necesario para que las pruebas pasen (3D desde la misma config);
el vaso entregado tiene que quedar colgado de los rieles de la canaleta en PyBullet (regrabar videos).
- [x] 13a. Llanta 26 mm + muelle ensanchado, pruebas del carro en verde, xfail quitado.
- [x] 13b. Vaso entregado sobre los rieles (15°), xfail quitado, videos regrabados (y cámara de todo_junto).

**Cierre del 2026-09-28:** todo lo del pedido 10-13 hecho; 740 pruebas pasan; demo y portable
regenerados; revisión final aplicada (150 N, 500 ms del carrusel, 24/24, tapas de 78 mm, hub USB, reglas
del firmware en el README). Nada subido a GitHub: esperar a que el usuario lo pida.

**Pedido del 2026-09-28 (14):** "revise el tema de carrusel que pasa la moneda sin que se espera a que de
la vuelta y se coloque bien, tema de timing".
- [x] 14a. Reproducir: la moneda cae al tubo antes de que el carrusel termine de girar (sim y/o visor).
- [x] 14b. Arreglar el timing: la descarga (y la cinta de monedas) espera a que el carrusel llegue al tubo
  (y vuelva del agujero tras soltar un lote), con los tiempos reales (media vuelta 4,1 s).
- [x] 14c. Pruebas, visor revisado con capturas, docs, app escondida.

**Pedido del 2026-09-28 (15):** "pase varias revisiones exhaustivas a todo el proyecto, tanto visual como
lógico, siempre es importante". (Regla permanente: después de cada cambio grande, revisión visual + lógica.)
- [x] 15a. Ronda 1 (en paralelo al arreglo del carrusel, solo lectura): lógica de control/firmware/protocolo/carro/asistente;
  visual del visor y del dashboard (captura de la app en vivo); documentación contra el código.
- [x] 15b. Aplicar lo encontrado (priorizado).
- [x] 15c. Ronda 2 después del carrusel: planta + visor + demo, pruebas completas, capturas.
- 15b (parcial): aplicadas las correcciones de la revisión de documentación (mermaid del tema 1, 69,1 mm en
  firmware/README, docs generados vs escritos, comandos con el entorno, capacitivo bajo E1 / 6-36 V, cuna,
  I2C 0 corto / I2C 1 largo, "apaga todo" en el tema 4, COM99 explicado, entornos de los temas 7 y 8).
  PENDIENTE tras el carrusel: `;` en el sequenceDiagram de docs/logica-interna.md (~l.346), E5/E7 en
  comentarios de sim/planta.py (l.50, 166, 1313) y "E5" en control/tiempos.py:64 → E3; regenerar docs.
- 15b: revisión LÓGICA encontró 22 hallazgos (informe en la conversación del 2026-09-28). Reparto:
  - Grupo A (ya): asistente (frases sin "?" que mueven/paran), puente serial (líneas partidas), supervisor/servidor
    (órdenes mal formadas, CORS, lote > capacidad, modo real sin_esp32/paro), vaso desechado en estado valida.
  - Grupo B (ya): carro (sale de nuevo con el vaso), ids del protocolo por sesión, respuestas > 250 B por ESP-NOW,
    enlace del carro con tráfico ajeno, try/WDT en main del carro, decode UTF-8 en enlaces, "t"→"ts".
  - Grupo C (después del carrusel): firmware fijo (paro enclavado, cortina insegura sin lecturas y sin voto,
    puede_soltar_vaso, try/WDT en main, parada segura frena el carrusel), reintento de tapa en tiempos.py,
    causa NULL de sin_registro, valores de config sin uso.
- 14 HECHO: carrusel con tiempo real (`control/carrusel.py`), 0 monedas/lotes a destiempo; prueba_completa pasa de
  70,4 s a 100,8 s (31,5 → 22 elem/min; peor caso tubo opuesto 12,2 elem/min). Firmware: `carrusel ir lugar` y
  evento `carrusel/llego`. 841 pruebas. Pendiente: videos embalaje_vasos/todo_junto sin rellenar las esperas.
- 15b hecho: grupo A (asistente 50/50; puente con buffer; supervisor tolera órdenes malas; CORS; lote ≤ capacidad;
  modo real pausa con sin_esp32; vaso vacío RECHAZADA), grupo B (carro/protocolo/radio), dashboard (matriz 35/35,
  cifras con "del turno anterior", mapa, textos, 900 px), db.ultima_telemetria tolerante. Ajuste de la sesión
  principal: "detén la línea" = PAUSA; PARO solo con "paro" o urgencia explícita ("para todo ya").
  En curso: firmware fijo (grupo C) y visor 3D. Luego: ronda 2 + capturas/GIF del README.
- 15b terminado (firmware fijo y visor 3D incluidos): 873 pruebas. App relanzada. Pregunta abierta al usuario:
  reintento de tapa (1,36 s) no cabe en la pausa de vasos (0,8 s): ¿espera aceptada o alargar la pausa?
- 15c EN CURSO: ronda 2 (lógica sobre lo cambiado + batería del asistente; visual en vivo con el carrusel;
  capturas y GIF del README regenerados).
- Ronda 2 lógica: carrusel SIN regresiones (estrés con lotes 1-25, sabotajes, tubo lleno). Hallazgos nuevos en
  arreglo (2 agentes): canaleta trabada tras orden rechazada, WDT que reinicia en la subida, ack de comando
  fallido, eventos de error sin límite, salida de parada por error, pausa sin_esp32 sin avisar a la placa,
  carrusel vs obturador, llego viejo, orden al carro perdida | asistente ("sigue la línea de producción",
  "la moneda avanza", "detén todo", "que vaya a la meta"), evaluador con copias distintas, dashboard que
  inventa monedas del turno anterior, matriz con diámetro real.
- Ronda 2 arreglada: asistente 60/60 (local y reglas), dashboard sin monedas inventadas; firmware/supervisor
  (canaleta tras rechazo, WDT con el primer latido, ack de comando fallido, límite de avisos, motivo de parada
  visible y reanudable, pausa que para la placa, carrusel↔obturador, llego con id, reintento de órdenes al carro).
- CAUSA de que el dashboard se cayera 2 veces: Streamlit escuchaba en IPv6 (::) y en Windows un cliente que
  corta de golpe (Chrome sin ventana) rompe su bucle de accept (WinError 64): proceso vivo que no atiende.
  Arreglo: `--server.address 127.0.0.1` en app/lanzar.py + chequeo de salud cada 10 s (3 fallos = reinicio);
  servidor.py ignora cortes del cliente. Usar http://127.0.0.1:8501.
- Ronda 2 VISUAL: el carrusel todavía soltaba monedas a tubos en movimiento (8 de 15 en vivo, 15-37 mm, 22-40°):
  la planta arrancaba el giro siguiente en el mismo ciclo en que guardaba la moneda (en_ms 0), sin esperar su
  caída. Las pruebas no lo veían (miraban el tubo al guardar, no el giro siguiente). En arreglo: la caída ocupa
  el carrusel (`tiempos_ms.caida_moneda_tubo`), visor respeta en_ms y la pila crece al caer, obturador con tubo
  quieto; medición visual cuadro a cuadro antes/después. Otro agente: detalles del dashboard.
  LECCIÓN: la verificación del timing tiene que ser VISUAL/cuadro a cuadro, no solo con eventos.
- CIERRE 15 (2026-09-29): carrusel verificado cuadro a cuadro (22 monedas y 4 lotes a 0 mm / 0°, en vivo y demo);
  caida_moneda_tubo 400 ms; prueba_completa 113,6 s (19,5 elem/min). Dashboard sin caídas (127.0.0.1 + salud).
  930 pruebas. App relanzada. Sin git. PENDIENTE del usuario: ¿reintento de tapa (1,36 s > pausa 0,8 s) como
  espera aceptada o alargar la pausa de vasos?

**Pedido del 2026-09-29 (16):** "Alargar la pausa de vasos, total, no van a bajar a la suficiente velocidad para
que el carrusel se sature". → `tiempos_ms.pausa_casilla_vasos` de 800 a 1400 ms (cabe el reintento de tapa, 1360).
- [x] 16a. Config + chequeo de tiempos OK + docs/README/wokwi con el valor nuevo + pruebas + app relanzada.
