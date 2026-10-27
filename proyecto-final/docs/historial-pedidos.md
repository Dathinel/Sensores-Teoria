# Historial de pedidos del usuario (proyecto final)

Pedidos ya cerrados, con las palabras del usuario, en orden de fecha. Es historia: se movió tal cual desde
`CONTEXTO-SESION.md` (secciones 0 y 5 el 2026-10-02; los de octubre el 2026-10-26) y no se corrige, así que nombra
rutas, cifras y archivos de cuando se escribió (por ejemplo `app/asistente.py`, `control/hal/backend_sim.py`, los
`.scad` sueltos de `maqueta_impresa/` o 937 pruebas). Lo vigente (pedido en curso, reglas, lo prohibido, restricciones
y pendientes) está en [CONTEXTO-SESION.md](../CONTEXTO-SESION.md).

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

**Pedido del 2026-09-29 (17):** "Súbalo a GitHub". Hecho: commit `cb7c86d` en `main` (155 archivos), push a
github.com/Dathinel/Sensores-Teoria. Incluye los arreglos del tema 8 punto 1 de otra sesión (ljust, puerto).

## Movidos de CONTEXTO-SESION.md el 2026-10-26 (del cierre del 2026-09-29 al 2026-10-24)

**Cierre del 2026-09-29:** pedidos 10 a 17 TERMINADOS y subidos (commit `cb7c86d` en `main`). Solo quedó sin
subir este archivo (el usuario dijo que no hace falta). App escondida corriendo con el código final.

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

**Pedido EN CURSO del 2026-10-05 ~22:15 (agente P del plan `github\PLAN-ORGANIZAR-APPS.md`).** Textual del usuario:
> "en ese puerto esta una app que hicimos hace tiempo, me gusto mucho el tema de apps para mostrar cada practica,
> quitele peso en megabytes a cada practica y trate de hacerlas para que todo quede resumido en una app, que el readme
> se base en, quiere saber como funciona, aqui esta todo, quiere probarlo, aqui esta, sin quitar el contenido que ya
> tiene, ya que quien lo lee es el profe y si tiene que estar todo lo tecnico, pero meter todo en una app explicada paso
> a paso esta muy bien, como un tipo docker, me gusta mucho, y organice el repo porque se ve desorganizado, puede cambiar
> nombres y todo desde que todo quede funcionando, trate de organizar mejor los datos en la app igualmente, abrir en
> pantalla completa, que no se solapen cosas etc, tener barras que cargan o cosas que digan se esta ejecutando se tarda
> tanto en abrir, revise practicas mas complicadas de entender y haga pruebas mas claras como la de las hormigas o como
> funciona el docker, cosas mas explicadas, pruebas visuales, un acompañamiento del tema con su prueba y quitar el probar
> general, para eso esta en cada practica, junto a su logica, adecue todo eso, con los agentes que le di permiso, y haga
> commit de todo"

Puntos de este proyecto (el commit lo hace la sesión principal):
- [x] 1. Peso: GIF de docs/videos re-codificados, sin duplicados gif/mp4 sin uso, imágenes optimizadas, PDF del enunciado, visor-portable.html (medir antes/después).
- [x] 2. Organizar lo suelto sin romper imports/rutas (pytest al final).
- [x] 3. README: "¿Quiere probarlo? → aquí está" y "¿Quiere saber cómo funciona? → aquí está todo" al principio, sin quitar lo técnico.
- [x] 4. App `app-practica/` tipo Docker Desktop, sin solapes (1366x768 y 1920x1080), barras de carga, recorrido de la moneda animado junto al estado real del visor.
- [x] 5. Probar con el lanzador y capturas; lanzar una acción desde la app.
  TERMINADOS (P, 2026-10-05 noche; detalle en `docs/bitacora.md`): 29,0 → 17,0 MB versionados (GIF sin tramado,
  sin `todo_junto.gif`, mp4 CRF 30, PDF y PNG comprimidos; visor portable igual a propósito); la estructura interna
  ya era coherente (no se movió nada); README con las dos entradas al principio; app tipo Docker Desktop con la
  prueba visual junto al estado real (`/api/estado`). Sin commit (lo hace la sesión principal). La app escondida
  NO se relanzó.

**Pedido EN CURSO del 2026-10-06 (agente Q9 del plan `github\PLAN-REVISION-PASOAPASO.md`).** Textual del usuario:
> "ahora actualice los cambios y mejore el repositorio de github sin cambiar los nombres ya que los links se podrian
> perder, igualmente paso por paso de todo y revisiones de multiples partes"

Puntos de este proyecto (NO renombrar ni mover nada; sin git; la corrida escondida 8766/8501 no se toca):
- [x] 1. Paso a paso: cómo se hizo (README conecta `docs/paso-a-paso.md` y la bitácora), cómo probarlo con la app
  (sección por sección, botón por botón, qué hacer si falla), sin la app (comandos) y con el montaje real (qué falta).
- [x] 2. Revisión del README y docs principales: exactitud contra el código, enlaces/anclas, imágenes, mermaid,
  tablas, ortografía, cifras actuales (pytest).
- [x] 3. Revisión de la app `app-practica` con el lanzador (puerto propio 8260-8279) y capturas a 1366x768 y 1920x1080.
- [x] 4. Revisión del código reciente (`app/puertos.py`, `app/charla.py`, `app/lanzar.py`): bugs; `pytest -q` al final.
  TERMINADOS (Q9, 2026-10-06; detalle en `docs/bitacora.md`): 937 pruebas pasan. Sin commit (lo hace la sesión principal).

### Pedido EN CURSO del 2026-10-16 — auditoría de prácticas 1–11 y proyecto final

Textual del usuario:
> "codex, ud es el lider, revise en el disco D cosas uni, micros, organice esas carpetas actualice el repo en github si va a cambiar los nombres, y separe la carpeta y todo lo referente a modelado 3d fuera de la carpeta y coloquele un nombre acorde a todo el modelaje, arregle rutas dañadas de todas las practicas talleres etc, y arregle cualquier error que encuentre, organice tambien el repo con su logica respectiva, puede usar los agentes ia en el chat, exepto claude y modelos que usan claude de mi cuenta, tiene acceso a el github, si no lo tiene hagalo junto a las herramientas necesarias, recuerde arreglar cualquier ruta y si encuentra algun fallo lo arregla"
>
> Aclaración posterior: "no movio la carpeta de micros entorno de pruebas que le dije dentro de micros, y tampoco reviso las practicas de la 1 a la 11 con talleres y proyectos los errores logicos que pudierantener, por eso le dije que usara varios agentes por si acaso, es bastante trabajo"

Puntos:
- [x] Mover `D:\micros entorno de pruebas` dentro de `D:\cosas uni\Micros` (destino `Micros entorno de pruebas`); preservar su entorno y datos.
- [x] Auditar prácticas 1–11, talleres y proyecto final por lógica y rutas con agentes que no usen Claude. Prácticas 1–8: enlaces locales Markdown verificados, sintaxis Python válida y revisión de flujos/rutas; 9–11: Compose válido, 40/40 pruebas de protocolo y enlaces Markdown; proyecto final: 937/937 tests pasaron en la ejecución desde `proyecto-final`. Sin ejecutar prácticas que requieren hardware/servicios externos.
- [x] Corregir fallos reproducibles, revisar cambios y dejar registro de lo que quede pendiente. Se corrigió la ruta del activador del venv tras mover `Micros entorno de pruebas` y referencias operativas del nombre del modelado 3D. Un fallo adicional de pytest fue por ejecutar desde el directorio raíz; aislado desde `proyecto-final`, pasó. Tema 10 prueba 6 sigue documentada como 90% frente al criterio de 95%; no se cambió la configuración porque es un resultado conocido, no una ruta rota ni una regresión.

### Pedido EN CURSO del 2026-10-20 — chasis impreso del carro (carpeta `chasis_impreso/`)

Resumen fiel del pedido (texto completo en el transcript de la sesión): construir el carro de verdad imprimiendo
chasis y soportes (Creality HI, cama 260x260x300, boquilla 0.4, CFS, PLA). Puntos:
- [x] 1. Sacar del visor la disposición del carro (posiciones, alturas, carga, cables) solo como referencia.
- [x] 2. Chasis paramétrico desde cero (OpenSCAD/CadQuery), medidas en variables; medidas dudosas → variable + cómo medir.
- [x] 3. Liviano y rígido (nervaduras, vaciados, carga cerca de ejes) + masa estimada.
- [x] 4. Piezas: soportes TT, porta 18650, base ESP32 (M3), soporte TB6612, HC-SR04, VL53L0X, barra 5 TCRT5000, interruptor+fusible, pasacables, carga.
- [x] 5. Piezas que no quepan → cortes con cola de milano o pines + M3 con tuerca cautiva; tolerancia variable (0.2); sin soportes.
- [x] 6. Tandas que quepan en cama → 3MF por tanda + STL por pieza.
- [x] 7. Por pieza: material, capa, paredes, relleno, orientación, tiempo y gramos.
- [x] 8. Pieza de prueba de tolerancias (cola de milano + M3 con tuerca).
- [x] 9. Tornillería/insertos, orden de ensamble y render del carro completo.
  HECHO (2026-10-20): `chasis_impreso/` (chasis.scad + exportar.py + README con decisiones, medidas MEDIR, tabla de impresion,
  tornilleria y ensamble). 232 g / ~6,5 h estimados, sin choques. Falta imprimir la prueba y medir las piezas reales. Sin commit.

### Pedido EN CURSO del 2026-10-24 — maqueta completa impresa (carpeta nueva `maqueta_impresa/`)

Textual del usuario:
> "Ahora también saque ordenadamente todo el tema del almacenamiento para la impresión en 3d y el chasis para montar toda la maqueta en 3d, como se haría sin con chasis, unidos, pero bien revisado, también cuanto material se gastaría y un manual inspirado en el que ya existe, y revise el modelado el proyecto final para que los modelos sean iguales tanto físicos como digitales, revise todo múltiples veces para no cometer el mismo error, otra instancia está trabajando a la par en el pc, si se cruzan avísele para que no se pisen"

Respuestas del usuario a las preguntas de alcance: estructura **todo impreso, sin perfil 2020** (módulos que caben en la
cama, unidos a presión: remaches impresos y colas de milano; MDF solo como piso); "almacenamiento" = **almacén de monedas**
(carrusel tipo revólver: placa fija, disco, tubos —también impresos—, obturador, soporte del 28BYJ-48, embudo al vaso);
si digital y físico difieren **mandan las piezas físicas** (después se corrigen visor y simulación, con prueba).
Lección del carro (2026-10-24): los remaches salieron mal porque su agarre se sacó de fórmulas y nunca se midió el
ensamble. Aquí TODA unión se mide en el ensamble con un revisor automático antes de entregar.
Puntos:
- [x] 1. Inventario geométrico de la planta (sim/mundo.py, geometria.py, parametros.yaml, visor) y discrepancias.
- [x] 2. Almacén de monedas imprimible (carrusel, tubos, obturador, soporte 28BYJ-48, embudo).
- [x] 3. Estructura impresa de toda la maqueta (mesas, patas, pórtico, canaleta...) en módulos unidos, sin aluminio.
- [x] 4. Revisión automática: choques, voladizos (sin soportes), cada unión medida en el ensamble, que todo quepa en la cama.
- [x] 5. Material: gramos, tiempo y rollos por pieza y total; tandas 3MF + STL por pieza.
  HECHO (2026-10-24): `maqueta_impresa/` (comun.scad, estructura.py -> estructura_gen.scad, un .scad por subsistema
  hecho por agentes, maqueta.scad, revisar.py, probar_revisor.py 39/39, exportar.py). Revisión completa en TODO OK:
  310 remaches medidos, 170 piezas sin choques, 13 móviles barridos (74 pares), sin soportes, todo cabe. 2,74 kg de PLA
  (4 rollos), ~82 h, 25 tandas (material.md). Diferencias funcionales a llevar al visor/sim: paleta 56 de ancho con
  esquina cortada; embudo E4 salida Ø29 y aleta nueva; obturador gira en horizontal; 28BYJ girado 90°; embudo de carga
  termina en z 335; vaso retenido por el escape ~17 mm más abajo que el visor; separadores de vasos recortados 3 mm.
- [x] 6. Manual de armado inspirado en el del carro (tandas, dónde va cada pieza, remaches, componentes y cables).
- [x] 7. Visor y simulación iguales a las piezas físicas (corregir y dejar prueba).
- [x] 8. Ahorro de costos (usuario, 2026-10-24: "entre más se ahorre mejor, tanto para lo impreso como para el proyecto
  final"): sin bornera, sin IEC, un solo fusible, fuente de 5 A, buck XL4015 5 A, sin optoacopladores (M18 con diodo +
  pull-up), sin hub USB, sin reparto I2C en placa, sin canaletas, sin MDF; PCA9685 y webcam 1080p se quedan; el carro no
  se toca. PLA: aligerar manteniendo rigidez.
  HECHO (2026-10-24): manual_maqueta.pdf (27 págs., comprobado: 170 piezas, 310 remaches y 19 dispositivos en un paso);
  visor con maqueta_impresa.glb + tests/sim/test_maqueta_impresa.py; costo $1.998.921 -> $1.387.143 (ahorro $611.778,
  calculado en app/costos.py), diodo Schottky BAT85 en los M18 (con 1N4148 el ESP32 no leía el 0), ventilador se queda;
  maqueta aligerada 2,74 -> 2,68 kg (3 rollos) con revisión completa en TODO OK y probar_revisor 39/39.
  HECHO (2026-10-24): commits 6006bae y 8de40b8 en main (940 pruebas en verde; .gitattributes con PDF/STL/3MF/GLB binarios).
- [x] 9. Actualizar TODA la carpeta proyecto-final (README, docs, contexto) y SUBIRLA a GitHub.
- [x] 11. (usuario, 2026-10-24) "los 3mf... se está levantando la primera capa en los círculos chicos... la membrana es
  horrible, esa no es solución... haga otra vez una auditoría completa y arréglelo": cara de apoyo maciza y agujeros a los
  costados (CONVENCIONES.md "Primera capa"), tubos con hueco octogonal y giro automático, primera_capa.py + auditar.py
  (todos los criterios por pieza) y perfiles nuevos de Creality Print "... maqueta" (una pared en la primera capa, sin wipe).
  EN CURSO (2026-10-25, "dejelo supremamente corregido en todo aspecto"; ultracode; límite de agentes quitado "pero que la
  cpu no se cargue tanto"): auditoría de 10 lentes con 2 verificadores por hallazgo (scratchpad wf/r1_*.md) y 2 rondas de
  arreglos con un agente por subsistema, trabajando en una COPIA (scratchpad pf/maqueta_impresa) que se pasa a la carpeta
  real al final. Causa de alm_1: se laminó con el filamento 2 (sistema) y el proceso "sin saltos" (wipe_on_loops 1, wipe
  con retracción 100 %, Slope Lift) y la placa vieja tenía una rejilla abajo con un puente de 3646 mm² en z 2,4 (el "mismo
  z"). La interfaz de Creality Print (abierta por un agente con --help) borró los perfiles "maqueta" al sincronizar con la
  nube: restaurados con sync_info = create, y ahora cada 3MF trae la configuración ADENTRO (exportar.py + perfil_creality.json)
  y laminar.py lo comprueba con el CLI.
  HECHO (2026-10-25): copia pasada a la carpeta real; segunda opinión aplicada entera (usuario: "A, cambiarlas, B
  cambiarlas, C cambiarlos, todo"): revisión capa por capa (voladizos.capas), islas de mon_e4/tap_pre_placa/vas_lat_s_b
  y postes en V de vas_lat_s_a corregidos, rodillo C quitado, canaleta amarrada, 11 separadores en la banda de vasos,
  precios de lo que el manual manda comprar. Única excepción (usuario: "Acepta el puente de 30 mm de mon_e4 como
  excepción documentada"): voladizos.PUENTES_ACEPTADOS, sale como aviso. Revisión completa en TODO OK (183 piezas, 316
  remaches), probar_revisor 128/128, auditoría 0 fallas de 183, esfuerzos todo cumple, 26 tandas laminadas bien
  (Creality Print: 2,95 kg y 101 h; exportar estima 2,98 kg y 91 h), costo $1.586.033, peso 8,08 kg. No se tocó
  la orientación en Y ni los agujeros ciegos (usuario: "Déjelo como esta", "Déjalos así").
- [x] 10. (usuario, 2026-10-24) El carro del visor igual al impreso; los remaches como parte del modelo (con casilla);
  verificar esfuerzo, deformación permanente (fluencia) y calor del PLA: maqueta_impresa/esfuerzos.py -> esfuerzos.md
  (todo cumple; condiciones nuevas: NEMA 17 con separadores de nailon, tira LED sobre cinta de aluminio a media potencia).
  HECHO: carro_armado.glb en el visor (cotas funcionales = física, tests/sim/test_carro_impreso.py), 337 remaches en los GLB
  con casilla "Remaches", demo regrabada (app.grabar_demo) y portable regenerado (9,3 MB); 945 pruebas. (README, docs, contexto) y SUBIRLA a GitHub (usuario, 2026-10-24:
  "junto a su github no se le olvide"): commit y push al terminar, con la suite en verde.
- Coordinación: la sesión "cambios en general de la carpeta" trabaja en paralelo; se le avisó (mensaje retenido sin leer,
  2026-10-24). Esta sesión solo crea `maqueta_impresa/` y lee lo demás; antes de editar visor/sim/config, avisar.

### Pedido EN CURSO del 2026-10-24 (tarde) — ahorros de costo aprobados (agente de ahorros)

Textual del usuario:
> "también el tema de ahorrar costos pueden ser la eliminación de borneras y swiches, al final es un proyecto universitario, no un sistema industrial, entre más se ahorre mejor, tanto para lo impreso como para el proyecto final"

Eligió: sí buck de 5 A para servos, sí sin optoacopladores, sí sin hub USB; NO cambiar la webcam cenital; DEJAR el
PCA9685; "el carro ya no lo toque"; un solo ESP32 fijo alcanza (19 de 24 GPIO). Puntos (en todas las capas):
- [x] 1. Bornera X2 → empalmes soldados con termoencogible (GND en estrella igual).
- [x] 2. IEC → cable de la fuente a una multitoma con interruptor; 4 fusibles → 1 fusible principal en el +12 V.
- [x] 3. Fuente 12 V 10 A → 12 V 5 A. 4. XL4016 → XL4015 5 A (pico ≈3,9 A; prensa y empujador nunca a la vez).
- [x] 5. Sin optoacopladores: M18 directo al GPIO con diodo + pull-up 10 kΩ (sigue activo en bajo).
- [x] 6. Sin hub USB (ESP32 y 2 webcams al portátil). 7. Reparto I2C → hilos con 2 pull-ups 2,2 kΩ en línea.
- [x] 8. Canaletas y prensaestopas → bridas; ventilador según la térmica. 9. Sin base MDF.
- [x] 10. Estructura = maqueta impresa (gramos × PLA + energía). 11-13. Documentos, visor y pruebas en verde.
HECHO (2026-10-24): total $1.393.790 (antes $1.998.921), peso 7,92 kg; detalle en docs/bitacora.md.
No se toca `maqueta_impresa/`, `chasis_impreso/` ni nada del carro. Sin git.

## Sección 4 de CONTEXTO-SESION (superada, movida el 2026-10-02)

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

## Movido por decisión del usuario (2026-10-02)

Estaba en la sección 3 de `CONTEXTO-SESION.md`. El usuario decidió el 2026-10-02 que el navegador no se abre (la app se deja corriendo escondida y él la mira con `visor.bat`):

- Correr y mostrar: `entorno/Scripts/python -m app.lanzar --auto prueba_completa` y abrir
  `http://localhost:8765` (visor 3D) y `http://localhost:8501` (dashboard). **NO publicarlo como
  artefacto de Claude**: se abre en el navegador del PC. Si los puertos ya están ocupados es que
  el usuario lo tiene abierto: no cerrarlo; para verificar, levantar una copia en otro puerto.
