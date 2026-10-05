# Bitácora de avance

Se actualiza al cerrar cada fase del plan de trabajo (`CLAUDE.md`, sección 16).

## 2026-09-22 — Fase 0 y Fase 1

**Hecho:**

- Estructura de carpetas completa según `CLAUDE.md` sección 9 (`docs/`, `cad/`, `sim/`,
  `control/`, `vision/`, `app/`, `firmware/`, `tests/`, más `config/`).
- Capturas del enunciado movidas a `docs/enunciado/`.
- `requirements.txt` con las dependencias base de la sección 19, más `pytest` como
  dependencia de desarrollo (no listada en `CLAUDE.md`, se agrega para poder correr las
  pruebas unitarias).
- `config/parametros.yaml` con los umbrales de filtrado de la sección 7 y los valores
  físicos que todavía son provisionales (altura/diámetro del vaso, altura del
  separador, modelo del motor paso a paso), marcados explícitamente.
- `app/db.py` con el esquema de las 5 tablas de la sección 10.3 (`eventos`,
  `elementos`, `vasos`, `ruta`, `ordenes`).
- `control/monedas.py` con la tabla de las 9 denominaciones colombianas de la
  sección 6 y utilidades de búsqueda por clase.
- `control/hal/interfaces.py` con las interfaces abstractas de sensores y actuadores
  (sin implementación todavía; `backend_sim.py` y `backend_real.py` llegan en las
  fases 3 y 8).
- `control/registro.py`, `control/reglas.py`, `control/linea.py` y
  `control/embalaje.py`: capa de control pura (sin PyBullet ni pyserial) con las
  reglas de decisión, la máquina de estados de la cinta de monedas (estaciones 1, 2 y
  5, con los dos expulsores separados) y la máquina de estados de la cinta de vasos
  (verificación, llenado, tapa con re-verificación, prensa, descarga, cortina de
  seguridad).
- 44 pruebas unitarias en `tests/`, incluyendo un escenario mixto de 10 elementos y los
  casos de sabotaje de vasos (retirado, sustituido por figura distinta, mano intrusa
  bajo la cortina de seguridad). Todas pasan (`pytest -q`, Python 3.14, entorno virtual
  `entorno/`).

**Pendiente:**

- Confirmar los tres valores provisionales de `config/parametros.yaml`: dimensiones del
  vaso, altura del separador, modelo del motor paso a paso. Se usaron los valores
  provisionales para construir el URDF de la fase 2; si cambian, hay que regenerar las
  posiciones de estación en `sim/mundo.py` y en los `<origin>` de los URDF.
- Todavía no se ha inicializado el repositorio git ni subido nada a GitHub.

## 2026-09-22 — Fase 2

Se revisó primero el repositorio del profesor (`U_Militar/11) Proyecto_Final/maqueta.urdf`)
antes de escribir nada propio. Es una maqueta decorativa genérica (bancada en L, dos
brazos robóticos fijos, un carrito) sin casillas indexadas, sin servos de expulsión, sin
verificación de vasos ni prensa — no modela ninguno de los mecanismos específicos del
elemento 7 de este grupo, así que no se usó como base más allá de tomar prestada la
paleta de colores/materiales para mantener el estilo. Se documenta el porqué siguiendo
la convención ya establecida en el proyecto para reemplazos de este tipo.

**Hecho:**

- `sim/urdf/cinta_monedas.urdf`: bancada + cinta negra mate con los 8 separadores que
  delimitan las 7 casillas/estaciones de la sección 5 (separación real de 40 mm,
  `config/parametros.yaml`), dos servos de expulsión (juntas revolute) con sus
  canaletas de rechazo laterales independientes (expulsor 1 para `no_metalico`,
  expulsor 2 para el resto de causas de rechazo, para poder demostrar los filtros por
  separado en la sustentación).
- `sim/urdf/cinta_vasos.urdf`: bancada + separadores para las 5 estaciones de embalaje
  (verificación, llenado, tapa, prensa, descarga) + un empujador de descarga que
  reparte hacia una bandeja de rechazo o hacia una marca de salida de entrega. La
  canaleta de entrega real (rieles a 15°) y la prensa/dispensador de tapas completos se
  construyen en las fases 3 y 6, cuando haya sensores simulados que verificar.
- `sim/mundo.py`: construcción de la escena (carga ambas cintas posicionadas en línea,
  con la estación de llenado de vasos justo bajo la estación de descarga de monedas),
  fábrica de elementos por primitivas de PyBullet (moneda, botón plástico, botón
  metálico, bloque, vaso — sin mallas, cilindros y cajas puras, como pide la sección
  11), avance indexado por interpolación de posición + pausa (no se simula banda
  flexible), y activación de servos. Decisión documentada en el módulo: el paddle se
  anima visualmente pero el elemento se desplaza por control de posición directo, no
  por contacto físico, siguiendo el mismo criterio pragmático que ya se usa para el
  avance de la cinta.
- `sim/entorno.py`: pega `sim/mundo.py` con `control/linea.py` sin que ninguno de los
  dos conozca al otro más de lo necesario. `demo_fase2()` corre los tres casos del
  criterio de aceptación (botón plástico → expulsor 1, botón metálico perforado →
  expulsor 2, moneda de 500 válida → vaso) con veredictos de visión inyectados a mano,
  más el avance indexado independiente de la cinta de vasos. Se ejecuta con
  `python -m sim.entorno`.
- Se instaló `pybullet` y `numpy` en `entorno/` (Python 3.14; sí hay wheels
  disponibles) y se verificó a mano que `python -m sim.entorno` abre una ventana GUI
  real (usó la GPU del equipo, `NVIDIA GeForce RTX 3050 Laptop GPU`) sin errores.
- 9 pruebas automatizadas en `tests/test_sim_fase2.py`, en modo DIRECT (sin ventana):
  verifican que el avance indexado mueve los cuerpos la separación exacta, que un
  elemento no avanza más allá de la última estación, que activar un expulsor saca al
  elemento fuera del ancho de la cinta y lo desactiva, y corren el escenario completo
  de la demo de principio a fin. Total del repo: 53 pruebas, todas pasan.

**Pendiente:**

- Fase 3: sensores simulados (rayTest para presencia/barreras/cortina, banderas de
  material para el par capacitivo/inductivo, `getCameraImage` para la estación de
  visión) y el backend `sim` de la HAL que conecta `sim/` con `control/` sin que
  `control/` importe PyBullet.
- `control/embalaje.py` todavía no está conectado a la cinta de vasos simulada (la
  fase 2 solo demuestra el movimiento mecánico); esa conexión es fase 3.

## 2026-09-22 — Cierre de la fase 3

La fase 3 había quedado implementada en la sesión anterior pero sin cerrar aquí. Se
verificó su criterio antes de seguir: `python -c "import sim.entorno as e;
e.demo_fase3(modo_gui=False)"` da **20/20** elementos del escenario `mixto_20` en el
destino esperado, y los 7 escenarios YAML (uno por filtro + el mixto) pasan en
`tests/test_escenarios.py`.

**Hecho (sesión anterior, documentado ahora):** `sim/sensores_sim.py` (rayTest para
presencia, barreras de vaso y cortina; bandera de material para capacitivo/inductivo),
`sim/camara_sim.py` (clasificador en modo oráculo con ruido configurable),
`control/hal/backend_sim.py`, `sim/carga_escenarios.py` + `sim/escenarios/*.yaml`, y
`sim/linea_autonoma.py` (la cinta de monedas corriendo sola).

## 2026-09-22 — Fase 4: persistencia y dashboard

Criterio: "se abre Streamlit mientras la simulación corre y las métricas se mueven en
vivo". **Cumplido** — verificado con capturas reales del navegador (Playwright + Chrome)
mientras el supervisor corría: los indicadores, la cinta de casillas y los vasos se
actualizan cada segundo.

**Correcciones a fases anteriores encontradas en el camino** (regla 17: terminar lo
pendiente antes de avanzar):

- **Vasos encimados.** La cinta de vasos reutilizaba la separación de 40 mm de la cinta
  de monedas, pero el vaso mide 62 mm. No se notaba porque la demo de la fase 2 solo
  ponía un vaso a la vez. Ahora la cinta de vasos tiene su propia separación de **80 mm
  (PROVISIONAL**, se deriva del diámetro del vaso que también lo es):
  `config/parametros.yaml` → `vasos.separacion_casilla_mm`, `SEPARACION_CASILLA_VASOS_M`
  en `sim/mundo.py` y `sim/urdf/cinta_vasos.urdf` regenerado (bancada de 0.40 m).
- **`body_id` reciclados.** PyBullet reutiliza los `body_id` de cuerpos borrados. Al
  retirar un vaso (se borran el vaso y sus monedas) un elemento nuevo heredaba el
  registro de uno viejo y salía con el veredicto equivocado. La planta integrada usa
  ahora un id de registro secuencial propio (`Elemento.id_registro`). `sim/entorno.py` y
  `sim/linea_autonoma.py` siguen usando `body_id` porque ahí nunca se borran cuerpos.

**Hecho:**

- `sim/planta.py` (`PlantaSimulada`): **las dos cintas juntas por primera vez**. Lo que
  acepta la cinta de monedas cae al vaso de la estación de llenado y el registro del vaso
  suma cantidad/valor/masa de esa moneda; al juntar `planta.monedas_por_vaso` (5, decisión
  de operación en el YAML) la cinta de vasos avanza: tapa con re-verificación real,
  prensa, descarga a entrega o rechazo. Implementa el salto de casilla del paso 10 (si no
  hay vaso válido en llenado, la moneda espera y la cinta de vasos avanza, sin paro de
  línea) y la cortina del paso 14 (congela vasos, las monedas siguen). Sabotajes de la
  sección 2 disparables en vivo: retirar vaso, cambiarlo por una figura de 35 mm, meter
  y quitar una "mano". La planta no se entera por el sabotaje: lo descubre con sus
  sensores. Avanza por ticks y reporta eventos con el estilo `src`/`ev` del protocolo
  de la sección 10.1.
- Visual en PyBullet: las monedas aceptadas quedan dentro del vaso y viajan con él, la
  tapa aparece sobre el vaso al taparlo, y hay tubo de tapas, embudo y prensa (solo
  visuales, sin colisión, para no interceptar los rayTest de barreras y cortina).
- `app/supervisor.py`: el único proceso que toca la simulación. Consume la tabla
  `ordenes` (iniciar con escenario/umbral/ruido, pausar, reanudar, paro de emergencia,
  velocidad, sabotajes), escribe `eventos`, `elementos` y `vasos`, y publica la
  telemetría (el `t: tel` de la sección 10.1) como evento `tipo='tel'` con el estado
  completo de ambas cintas y todos los sensores. SQLite en modo WAL para que el
  dashboard lea mientras el supervisor escribe. No hizo falta cambiar el esquema de la
  sección 10.3.
- `app/dashboard.py`: Streamlit que solo lee. Pestañas **Producción** (5 indicadores,
  barras por denominación, valor acumulado, tabla de vasos; la masa rotulada como
  estimada por conteo), **Línea en vivo** (las 7 casillas de monedas y las 5 de vasos con
  su contenido y estado, LEDs de cada sensor, banner de cortina, botones de sabotaje,
  bitácora de eventos), **Inspección** (medidas de visión de los últimos 20 elementos;
  la imagen llega en fase 5), **Rechazos** (las 6 causas separadas por expulsor, avisa
  qué filtro no disparó). Ruta y Asistente quedan como pestañas marcadas para las fases
  6 y 7. Barra lateral de Control (backend, escenario, umbral de confianza, ruido del
  oráculo, iniciar/pausar/reanudar/paro, velocidad). Refresco con
  `st.fragment(run_every=1s)`, sin bucles. `?pestana=linea` abre directo esa pestaña.
- `app/configuracion.py` (carga del YAML; los umbrales en ejecución salen de ahí) y
  `app/lanzar.py` (supervisor + dashboard en un comando, cada uno en su proceso).
- 11 pruebas nuevas (`tests/test_planta.py`, `tests/test_supervisor.py`): los tres
  sabotajes, que el valor aceptado cuadre con el de los vasos, pausar/reanudar/paro,
  umbral de confianza desde el dashboard, y reinicio de corrida. Total: **83 pruebas,
  todas pasan**.
- Dependencias instaladas en `entorno/`: `streamlit`, `plotly`, `pandas` (ya estaban en
  `requirements.txt`). Todas tienen wheels para Python 3.14.

**Pendiente:**

- Fase 5 (visión): render cenital con `getCameraImage`, segmentación, y reemplazar el
  oráculo sin tocar `control/`. Ahí se completa la pestaña de Inspección con la imagen.
- Los sabotajes solo se disparan desde el dashboard; la sección 11 también pide que los
  escenarios YAML puedan listarlos con su instante, para que la sustentación sea
  repetible. Queda para cuando se armen los escenarios de sabotaje.
- Mientras la cortina está activa el vaso de llenado sigue recibiendo monedas aunque ya
  tenga `monedas_por_vaso` (la cinta de monedas no para, como pide el paso 14, y la de
  vasos no puede avanzar). Decisión consciente; revisar si el grupo prefiere otra cosa.
- Valores provisionales nuevos: `vasos.separacion_casilla_mm` (80).

## 2026-09-22 — Visualización 3D, paso a paso y sensores

Pedido del usuario: ver el sistema completo en 3D (planta, sensores, carro, pista con
obstáculos), un paso a paso de cómo funciona para revisarlo **punto por punto** con el
grupo, y la simulación de cada sensor mostrando qué recibe y qué entrega, tanto en la UI
como en carpetas numeradas para GitHub. Decisiones tomadas con el usuario: 3D con
**Three.js en el navegador** (PyBullet sigue haciendo la física), revisión **un punto a la
vez**, sensores **en el dashboard y además en carpetas**.

**Correcciones físicas que el 3D dejó en evidencia** (todas en `sim/mundo.py` y los URDF,
con prueba en `tests/test_visualizacion.py` para que no vuelvan a romperse):

- Las dos cintas estaban al ras del piso: la moneda aceptada habría tenido que *subir* al
  embudo. Ahora la cinta de monedas va sobre una mesa de **26 cm** y la de vasos sobre una
  de **10 cm** (PROVISIONALES), con una rampa corta de E7 al embudo.
- La canaleta de entrega baja 15° con el vaso colgado del reborde: con la cinta de vasos al
  ras del piso, a los 28 cm el vaso ya estaba bajo el suelo. Con la mesa de 10 cm termina
  con el fondo a 5 cm del piso, a la altura de la cuna del carro.

**Hecho:**

- `app/servidor.py`: servidor HTTP (librería estándar) dentro del supervisor, solo en
  `127.0.0.1:8765`. Sirve el visor, `/api/estado` (en memoria, 5 consultas/s sin tocar
  SQLite), `/api/geometria`, `/api/pasos` y `POST /api/orden`. Es el mismo punto de
  entrada que usará el puente con los dos ESP32.
- `sim/geometria.py`: geometría completa sacada de las mismas fuentes que la simulación
  (posiciones de estación de `sim/mundo.py`, rayos reales de los `SensorRayo` del backend
  sim), así el 3D no puede dibujar un sensor donde la simulación no lo consulta.
- `sim/pista.py` + bloque `pista` del YAML: pista en S (3 medias vueltas, 4,93 m) con 3
  muros en las rectas y meta; bloques `canaleta` y `vehiculo` (todo PROVISIONAL).
- `sim/catalogo_sensores.py`: los 14 sensores numerados (10 de la planta, 4 del carro)
  con modelo propuesto, qué lo activa, qué recibe, qué entrega y el mensaje que llega al PC.
- `app/visor3d/` (Three.js en local, sin CDN, para no depender del internet del salón):
  cintas, estaciones, paletas de expulsión, cubetas de rechazo, embudo, tubo de tapas,
  prensa, empujador, canaleta con compuerta, pista, muros, meta y carro (2 ruedas +
  loca, ESP32, 5 IR de línea, ultrasónico con su cono, encoders, cuna con IR). Rayos de
  sensores que se encienden (verde) o alarman (rojo). Animación de fichas, expulsiones,
  caída al vaso, tapas, prensa, vasos a la canaleta o a la bandeja, y la "mano". Panel con
  En vivo (controles y sabotajes), **Paso a paso** (la cámara va a la zona y resalta los
  sensores del punto) y **Sensores** (clic en un sensor en la escena o en la lista).
- `docs/paso-a-paso.yaml`: los 17 puntos, cada uno con qué pasa, sensores, entra, decide,
  sale, mensaje, cómo está hoy, preguntas para el grupo y estado de revisión.
- Dashboard: pestañas **Vista 3D**, **Paso a paso** y **Sensores** (señal del sensor en
  el tiempo y últimos mensajes que generó).
- `sim/planta.py` guarda lo que cada estación **leyó al decidir** (`lecturas_tick`): la
  foto del final del tick se toma con la cinta ya avanzada y mostraba, por ejemplo, la
  presencia de E1 siempre en 0.
- `app/simular_sensor.py`: `python -m app.simular_sensor N` corre la planta sin ventana y
  muestra la señal y los mensajes de un solo sensor (con el sabotaje que lo hace cambiar).
- `app/documentos.py`: genera `docs/paso-a-paso.md` y `docs/sensores/NN-nombre/README.md`
  (14 carpetas numeradas) desde sus fuentes; anclas con acentos como las genera GitHub.
- `app/lanzar.py`: si uno de los dos procesos se cae solo lo reinicia en vez de tumbar el
  otro. Se vio una vez a Streamlit morir con `Fatal Python error: _PySemaphore_Wakeup:
  parking_lot: ReleaseSemaphore failed` (fallo de Python 3.14 en Windows, no del
  proyecto); no se volvió a reproducir en 6 cargas seguidas.
- 16 pruebas nuevas (`tests/test_visualizacion.py`). Total: **99, todas pasan**.

**Pendiente:**

- Revisión punto por punto con el grupo (estado en `docs/paso-a-paso.yaml`); los puntos
  15 y 16 (carro) se simulan cuando se apruebe su lógica.
- Valores provisionales nuevos: alturas de mesas (26 y 10 cm), largo y separación de
  rieles de la canaleta, trazado de la pista, dimensiones del carro.

## 2026-09-22 — Revisión del punto 1 y almacén por denominación

**Revisión con el grupo:** punto 1 **aprobado** (carga manual, sin tolva; un infrarrojo
reflectivo alcanza; una mano puesta y quitada en la carga sale por el primer descarte). En
la misma revisión el grupo reportó y pidió:

1. *El menú de escenarios del visor 3D se cerraba solo.* El panel "En vivo" se reconstruía
   entero cada segundo. Ahora los controles se construyen una vez y solo se actualizan los
   datos.
2. *Las monedas caían en la figura que reemplazaba al vaso.* En el llenado solo había un
   sensor de presencia. Ahora hay dos barreras (media altura y borde, sensores 7 y 8, como en
   la verificación) que se leen justo antes de soltar monedas.
3. *Ninguna moneda colombiana se descarta, pero se puede guardar en otro lado; cada vaso va
   con UNA sola denominación* (500 solo con 500, sin importar la familia). Cambio de diseño:
   - `control/almacen.py`: 5 tubos, uno por denominación, con capacidad (25, PROVISIONAL).
     Si un tubo se llena, la moneda espera en E7 y la cinta de monedas se detiene: nunca se
     bota.
   - E7 ya no echa la moneda al vaso: un selector giratorio (servo) la manda a su tubo. Los
     tubos van en pentágono sobre la estación de llenado, con una compuerta cada uno y una
     tolva debajo. La mesa de monedas sube a 34 cm (PROVISIONAL) para que todo caiga por
     gravedad.
   - Cuando un tubo junta un lote (`planta.monedas_por_vaso`, 5), el lote entero cae a un vaso
     VÁLIDO y VACÍO (`EmbalajeVasos.llenar_lote`); `intentar_llenar` rechaza mezclar
     denominaciones. Sin lote listo, el vaso vacío espera en llenado.
   - Fin de turno: orden `embalar_parciales` (botón "Embalar lo guardado") empaca también los
     tubos incompletos, cada uno en su propio vaso.
   - Un vaso bueno que nunca recibió lote sale como `vacio` (no se cuenta como rechazo).
   - `vasos.denominacion` en SQLite, con migración para bases viejas.
4. Sabotaje nuevo "mano en la carga" (`tipo: mano` en los escenarios y botón en el
   dashboard/visor): la casilla viaja registrada y vacía, y sale como `no_metalico`.

**Otros:** catálogo de sensores renumerado (15: tapa 9-10, cortina 11, carro 12-15);
escenario `produccion_30` (24 monedas en lotes, 4 rechazos, 2 manos en la carga), que es
ahora el predeterminado del lanzador; `app/grabar_demo.py` + modo demo del visor (sin
supervisor, para verlo fuera del PC). Dos bugs de simulación encontrados en el camino: la
mano de 8 cm "tapaba" el origen del rayo de presencia (PyBullet no reporta choques que nacen
dentro de un cuerpo; ahora mide 3 cm) y "embalar parciales" no hacía nada si no quedaba vaso
en llenado (ahora la cinta de vasos avanza y trae uno). Pruebas: **117, todas pasan**.

**Pendiente:** revisión de los puntos 2 a 17; pregunta abierta sobre las monedas "muy
antiguas" (qué denominaciones/medidas, para el clasificador).

## 2026-09-22 — Punto 2 aprobado, generaciones de monedas y replicación real

**Revisión con el grupo:** punto 2 **aprobado**. Pedidos nuevos: agregar un par de
generaciones de monedas más viejas "por si acaso", y que todo pueda replicarse en la vida
real con sus tiempos, medidas y el error individual de cada sensor, anotado.

**Hecho:**

- Tabla de monedas a `config/monedas.yaml` con 4 generaciones (19 clases): nueva y antigua
  verificadas; muy_antigua e historica PROVISIONALES sin verificar (no hay datos confiables:
  hay que medirlas). Los 5 tubos quedan para 50/100/200/500/1000; las demás denominaciones
  aceptadas van a un sexto compartimiento **"otras"** (carrusel hexagonal): se guardan, no se
  empacan en vasos.
- Error individual de cada sensor en la simulación (`errores_sensores`: falsos negativos y
  positivos por lectura, ruido de medida de la cámara) con semilla fija; el supervisor y la
  demo los usan, las pruebas los apagan.
- Robustez que eso hizo necesaria (y que el montaje real también necesita):
  - voto de mayoría de 3 lecturas por decisión (`planta.lecturas_por_decision`);
  - E2 respalda a E1 ("presencia recuperada") si el infrarrojo de presencia falla;
  - el inductivo manda sobre el capacitivo para decidir metal (`control/linea.py`);
  - un falso positivo de presencia en una casilla vacía viaja como casilla vacía registrada y
    sale por el expulsor 1; lo que ningún sensor registró va a "otras" (el selector descansa
    ahí), nunca se pierde;
  - conteo de errores de filtrado contra la verdad del escenario (falsos rechazos / falsas
    aceptaciones), en el estado, el dashboard y el visor.
  Medido en 20 corridas de producción (520 monedas): con 1 lectura, 13 monedas colombianas
  rechazadas por error; con voto de 3, 5 (casi todas por el 2 % de error del clasificador, que
  decide con una sola foto). Ninguna moneda perdida ni falsa aceptación en ningún caso.
- `control/tiempos.py`: presupuesto de tiempos del montaje real (`tiempos_ms`). Todo cabe con
  los valores de hoja de datos: ciclo de 700 ms (≈86 elementos/min), cinta de vasos 2,2 s,
  cortina 119 ms. **Alerta: la visión tiene solo 30 ms de margen** (270 de 300 ms).
- Catálogo de sensores con rango, tiempo de respuesta, error típico, mitigación y conexión
  (los capacitivos/inductivos NPN de 6-36 V van por optoacoplador, nunca directo al ESP32).
- `docs/replicacion.md` generado: medidas por confirmar, monedas por medir, sensores (con la
  prueba de banco de 200 pasadas) y presupuesto de tiempos. Pestaña "Replicación real" en el
  dashboard; datos de replicación en cada punto del paso a paso y en cada sensor del visor.
- Pruebas: **129, todas pasan**.

**Pendiente:** medir monedas de las familias viejas; decidir si las de $1 a $20 van solo a
"otras" o necesitan vasos; revisión de los puntos 3 a 17.

## 2026-09-22 — Punto 3 aprobado, tiempos lentos, vaso de "otras" y componentes

**Revisión con el grupo:** punto 3 **aprobado**, con un sensor que confirme la expulsión
(prefirieron el sensor a apoyarse solo en la cámara). Además pidieron: tiempos más lentos (el
montaje real necesita verificar con calma) y que la simulación funcione igual; las monedas de
denominaciones que ya no circulan, empacadas en su propio vaso (separarlas más sería
ineficiente); ir catalogando los componentes en el 3D. El conexionado y los voltajes de cada
sensor y componente quedan para su sección (fase 8).

**Hecho:**

- `tiempos_ms` más lentos: avance 600 ms, pausa 1000 ms (ciclo 1,6 s, ≈37 elementos/min),
  lecturas separadas 30 ms, visión 400 ms, servos 250 ms, prensa 2 s, etc. La simulación corre
  con esos tiempos: el supervisor espera un ciclo real por tick y la ventana de PyBullet anima
  cada avance, pausa y barrido con su duración real; la demo del visor avanza un tick por ciclo.
  El presupuesto de tiempos detectó que el reintento de expulsión (970 ms) no cabía en 900 ms:
  por eso la pausa quedó en 1000 ms.
- Vaso de "otras": el compartimiento de denominaciones sin tubo ($1-$20 de series viejas) forma
  lotes y se empaca junto en un vaso "otras denominaciones" (única excepción a una denominación
  por vaso).
- Confirmación de expulsión (sensores 4 y 6, catálogo renumerado a 17): barrera en la boca de
  cada canaleta de rechazo, leída por interrupción. Sin confirmación → reintento en la misma
  pausa → la cámara de E5 revisa la casilla (vacía = sí salió) → el expulsor 2 la saca de
  respaldo → en último caso, en E7 va a "otras" para revisión manual. Se simula que el servo
  falle el 3 % de los barridos (`errores_actuadores`). Cuatro pruebas nuevas, una por caso.
- `sim/catalogo_componentes.py` (lista de materiales): 37 piezas en actuadores, control y
  potencia, estructura y carro, con modelo propuesto, función y estado (simulado / solo visual /
  pendiente). 12 servos: caben en un PCA9685. En el visor: pestaña **Componentes** que resalta
  cada pieza en la escena; se dibujaron la caja de control (ESP32, PCA9685, drivers, puente H,
  fuente), el portátil, los NEMA17 de las cintas y los cuerpos de los servos. Se genera
  `docs/componentes.md`.
- Pruebas: **135, todas pasan**.

## 2026-09-22 — Puntos 4 y 5 aprobados

- **Punto 4:** E4 queda libre, como pide la sección 5.
- **Punto 5:** dos fotos por moneda y Keras + MobileNetV2. La regla de combinación que se
  propuso primero ("si las dos coinciden se acepta") duplicaba el rechazo de monedas buenas;
  se implementó `control.reglas.combinar_fotos` (si las fotos que reconocen coinciden → esa
  clase aunque otra foto falle; si reconocen clases distintas → no_reconocida) y se midió en 30
  corridas con errores reales: 1 foto → 20 rechazos falsos y 1 moneda en el vaso equivocado;
  "deben coincidir" → 39 y 0; regla nueva → 7 y 0. Nuevo contador de errores
  `clase_equivocada` (dashboard y visor). El oráculo ahora también confunde clases (0,5 % por
  foto) y promedia la geometría de las dos fotos.
- Las familias muy antigua e histórica quedan **temporalmente** como no_reconocida
  (`familias_entrenadas: [nueva, antigua]` en `config/monedas.yaml`): el grupo no tiene las
  piezas todavía; cuando las consiga, se fotografían, se agregan y se reentrena.
- Pruebas: **140, todas pasan**.

## 2026-09-22 — Puntos 6 y 7 aprobados

- **Punto 6:** una sola cubeta de rechazo 2 (no se separa "revisar" de "descartar"): las
  históricas se reconocerán al entrenarlas, y los filtros existen para que ninguna pieza
  equivocada llegue a los vasos.
- **Punto 7:** lo que ningún sensor o registro reconoce se rechaza directamente, no se guarda en
  "otras" (no se sabría si se guarda una moneda o basura). Se agregó en la rampa de E7 una
  **compuerta de desvío a prueba de fallas** (servo SG90, el 13.º del PCA9685) y una **cubeta
  de rechazo final**: en reposo la compuerta manda todo al rechazo final; solo abre hacia el
  selector para una moneda registrada y aceptada. Así, si se corta la comunicación, nada
  desconocido entra al almacén. "Otras" queda solo para monedas reconocidas de denominaciones
  viejas. Visor: cubeta y compuerta nuevas; prueba automática actualizada.

## 2026-09-22 — Punto 8 aprobado (identidad del vaso y posición de las cintas)

- El profesor también puede cambiar un vaso por **otro igual** (las barreras no lo notan). Se
  agregó la **cámara de vasos** (sensor 16): lee el marcador ArUco impreso en cada vaso
  personalizado en la verificación, y lo vuelve a leer en el llenado y en la tapa; si el número
  cambió, el vaso se invalida (`sabotaje_detectado`, motivo `vaso_cambiado`). Si no lo alcanza
  a leer, deciden las barreras (no se para la línea).
- **Sensores de ranura** (14 y 15) en la marca de referencia de cada cinta: confirman que cada
  avance terminó en una casilla. Si la cinta patinó, se re-sincroniza y queda el evento
  `desfase_corregido`. El desfase se sortea una vez por avance (`errores_actuadores.cinta`).
- Los sensores del carro pasan a ser 17-20. Sabotaje nuevo "Cambiar por un vaso igual" en el
  dashboard y en el visor. Vasos personalizados: medidas siguen PROVISIONALES.

## 2026-09-25 — Punto 9 aprobado (tamaño del lote y fin de turno)

**Revisión con el grupo:** punto 9 **aprobado**. Respuestas a las dos preguntas: 10 monedas por
vaso por defecto, pero depende de cuántas monedas traiga el profesor ese día (tiene que poder
cambiarse); y lo que queda en los tubos al terminar el turno se puede empacar en vasos
incompletos **o** dejar guardado para el turno siguiente.

**Hecho:**

- `planta.monedas_por_vaso: 10`. Orden nueva `lote` (supervisor → `PlantaSimulada.cambiar_lote`),
  entre 1 y `capacidad_tubo`; los vasos ya llenos no cambian. En el dashboard: "Monedas por
  vaso (lote)" en la barra de control.
- Tabla `almacen_turno` en SQLite (una fila, no se borra entre corridas): el supervisor guarda
  el contenido de los tubos en cada tick y, si `planta.conservar_almacen_entre_turnos` (o la
  casilla "Arrancar con lo que quedó en los tubos" del dashboard), el turno nuevo arranca con
  esas monedas (`PlantaSimulada.precargar_almacen`, evento `almacen_precargado`). "Embalar lo
  guardado" sigue disponible para empacarlas en vasos incompletos.
- Pruebas: las del supervisor fijan lote 5 y tubos vacíos (sus cifras no dependen de lo que el
  grupo tenga en la configuración); nuevas: lote en caliente, turno que arranca con lo guardado,
  `almacen_turno` sobrevive a `reiniciar_corrida`. **150, todas pasan.**

**Pendiente:** revisión de los puntos 10 a 17. Medir la capacidad real de los tubos y que un
lote de 10 monedas de $1000 quepa en el vaso personalizado.

## 2026-09-25 — Punto 10 aprobado, sensores optimizados y revisión del modelo 3D

**Revisión con el grupo:** punto 10 **aprobado**. Un vaso que no recibió lote **pasa con tapa**
(no se desecha: es la evidencia de que no se identificaron monedas de ese valor). No hace falta
un sensor que confirme la caída de la tapa; además, hay que **optimizar sensores** reemplazando
por visión lo que se pueda, y **revisar el modelo 3D**: partes móviles, distancias, dimensiones,
cosas que se salen de sus límites, ubicaciones y que todo se pueda construir de verdad (el visor
es también el boceto que se presenta, tiene que estar pulido).

**Hecho — lógica:**

- `EmbalajeVasos.tapar` también tapa un vaso VÁLIDO vacío; `descargar` ya no tiene destino
  "vacio" (un vaso tapado, lleno o vacío, se entrega).
- **Cámara de vasos** (ahora sensor 7) con panel de luz detrás: en verificación, llenado y tapa
  mide presencia y dos franjas de la silueta (media altura y borde, "barreras virtuales"),
  lee el marcador ArUco y confirma la tapa (si no la ve, se suelta otra; si tampoco, inválido).
  Reemplaza a las **6 barreras IR** y a los 2 sensores de presencia de vasos: el catálogo pasa
  de 20 a **14 sensores** (renumerados; `docs/sensores/` se regenera y borra las carpetas
  viejas). Se quedan físicos, a propósito: capacitivo/inductivo, cortina (seguridad sin
  depender del PC), ranuras (el firmware se ubica sin PC), confirmaciones de expulsión (las
  eligió el grupo) y los del carro.
- **Cortina** del lado del operador, 5 cm afuera del borde de los vasos, con el sensor en el
  extremo de la prensa: antes corría sobre el eje de la cinta y la propia prensa la habría
  cortado en cada ciclo. La mano del sabotaje entra desde ese lado.
- Presupuesto de tiempos: dos chequeos nuevos (la cámara de vasos decide con la cinta quieta;
  la tapa cae y se confirma en la misma pausa).

**Hecho — modelo físico (sim/mundo.py, sim/geometria.py, config) y visor 3D:**

- Rieles de la canaleta a **69 mm** (antes 56: el cuerpo del vaso de 62 mm no cabía entre
  ellos) y arrancando en el borde de la cinta, a la altura de la pestaña del reborde (5 mm,
  nuevo dato provisional). La cuna del carro empieza justo donde termina la canaleta.
- Mesa de monedas a **43 cm** (antes 34): la moneda cae por el extremo de la cinta a un embudo
  y un canal baja ~30° al selector (con 34 cm quedaba a ~8°, no desliza).
- Almacén corrido 3 cm hacia la entrada (sus tubos chocaban con el tubo de tapas); la tolva es
  un embudo oblicuo hasta el vaso.
- Un solo empujador no puede empujar hacia los dos lados: empuja los tapados a la canaleta y
  los rechazados caen por el **extremo de la cinta** a la bandeja (movida al final).
- Visor reescrito en su parte 3D: estructura de perfil 2020 (mesa de monedas y pórtico
  trasero) que sostiene almacén, tubo de tapas, prensa y panel de luz; paletas de expulsión
  lineales de 34 mm (caben entre separadores y barren solo su casilla) con manivela; tubo de
  tapas a 13 mm de la boca con escape de dos dedos; prensa con leva excéntrica que gira y
  pistón guiado con resorte; empujador con manivela y buje; compuertas con bisagra bajo cada
  tubo; separadores de las cintas que avanzan de verdad; animaciones con los tiempos reales
  de config (caída con gravedad, llegada con la banda antes de actuar); marcadores ArUco en
  los vasos; etiquetas que aparecen al acercarse; vistas "Planta" y "Almacén";
  `?cam=x,y,z&mira=x,y,z` para tomas exactas. La canaleta muestra solo sus 4 lugares.
- Pruebas: **153, todas pasan.**

**Pendiente:** revisión de los puntos 11 a 17. Medidas reales de vaso, pestaña, tapas, tubo de
tapas y panel de luz.

## 2026-09-25 (2) — Puntos 10 y 11 cerrados; vasos vacíos, cortina baja, fondo del vaso

**Revisión con el grupo:** los cambios gustaron, con correcciones:

- Los vasos vacíos **sí se desechan** (no se tapan ni se prensan): la cinta queda libre en cada
  medición y cada corrida arranca de cero. Al terminar una corrida la cinta de vasos se vacía.
- ¿Cómo se sabe que un vaso está vacío? Antes solo por el registro. Ahora el vaso es
  **translúcido** y la cámara de vasos (con el panel de luz detrás) ve el **fondo**: las monedas
  son una franja oscura. Se usa en la verificación (un vaso que ya trae algo no entra), después
  de soltar un lote (`lote_no_confirmado` si no se ven) y en la prensa (si registro y fondo no
  coinciden, el vaso sale por rechazo: `contenido_inesperado` / `monedas_no_vistas`).
- La cortina estaba muy arriba (una mano que agarra un vaso pasaba por debajo): ahora son **3
  haces** (3 VL53L0X) a 25, 65 y 105 mm. Al despejarse, la cámara revisa todos los vasos que ve
  antes de seguir; sabotaje nuevo **"Mano que saca un vaso"** (`retirado_con_mano`).
- La cámara de vasos ve también la **prensa** (4 casillas, cámara a 30 cm; el panel de luz llega
  hasta la prensa y cierra la zona por detrás). Antes de prensar revisa vaso, marcador, tapa y
  fondo.
- **Posición de las cintas por visión** (idea del grupo): cada cámara mide dónde quedaron los
  separadores después de cada avance y se corrige con micropasos. Se quitan los 2 sensores de
  ranura: el catálogo queda en **12 sensores**.
- **Prensa con servo MG996R** (punto 11 aprobado): con 6,5 mm de excentricidad la leva empuja con
  ≥150 N y una tapa pide ~30-50 N; el servo sabe su ángulo (sin sensor ni puente H). Leva
  0 → 180 → 0 grados, `prensa_ciclo` 1400 ms.
- **Servos de las compuertas** dibujados donde caben: 6 SG90 bajo la placa del almacén,
  acostados hacia afuera, con su eje como bisagra (el panel de luz bajó para dejarles lugar).
- **Tubo lleno sin vaso:** los vasos son genéricos (la denominación la decide el tubo que se
  abre); si un tubo se llena y no hay vaso, la moneda espera en E7 y la cinta de monedas se
  detiene (nada se bota). Alarmas nuevas `tubo_lleno` y `faltan_vasos` en visor y dashboard.
- Pruebas nuevas: mano que saca un vaso, fondo que no coincide con el registro, vaso que ya
  trae algo, cortina baja, cinta de vasos vacía al terminar.

**Pendiente:** revisión de los puntos 12 a 17. Medir la fuerza real para asentar una tapa, que
el vaso sea translúcido y las monedas se vean en el fondo con el panel de luz.

## 2026-09-25 (3) — Filtro total, almacén revólver, vasos opacos con celda de carga

**Revisión con el grupo:** gustaron los cambios, con más correcciones.

- **Identificador del vaso:** en vez de un cuadrado de un lado, una **cinta alrededor de todo el
  vaso** con el mismo ArUco repetido 6 veces (siempre hay uno de frente a la cámara).
- **Vasos opacos:** no les gustó que fueran transparentes (alguien puede poner un vaso con algo
  adentro). Opción sin sensores nuevos (un espejo que le diera a la cámara una vista desde
  arriba): no cabe, encima de verificación, llenado, tapa y prensa están el almacén, el tubo de
  tapas y la prensa. Se agregó **una celda de carga (1 kg + HX711) en el llenado**: pesa el vaso al
  llegar (tiene que pesar como uno vacío → si no, `vaso_con_contenido` y no se llena), confirma
  que el lote cayó entero (`lote_no_confirmado`) y da el **peso real** de cada lote. Sabotaje
  nuevo "Vaso con algo adentro". Se quitó la lectura del "fondo" por la cámara.
- **Distribución de monedas:** el selector con un pico corto no era creíble (la moneda llega con
  velocidad). Ahora el almacén es un **revólver**: los 6 tubos giran (motor 28BYJ-48 con
  referencia por sensor Hall) sobre una placa fija con UN agujero sobre el vaso, con obturador
  (servo). La moneda cae casi vertical a la boca del tubo que está en la carga; para soltar un
  lote, ese tubo va al agujero. Carga y agujero a 210°: nunca se carga y se suelta a la vez.
  Reemplaza al servo del selector y a los 6 servos de compuerta (7 → 2 actuadores).
- **Filtro total en las monedas** (idea del grupo): una sola bandeja de rechazo. Se quitaron los
  dos expulsores (2 servos), sus 2 sensores de confirmación, la estación libre y dos canaletas:
  la cinta pasa de 7 a 4 estaciones (presencia, material, visión, descarga) y la compuerta de
  desvío de la descarga es la única salida de rechazo. Cada rechazo conserva su causa. El paso a
  paso quedó en **15 puntos** (los puntos 3, 4 y 6 viejos se fusionaron en el nuevo 4).
- **Punto 10 (descarga de vasos) aprobado:** canaleta llena → el vaso espera en la descarga y la
  cinta de vasos se detiene (la de monedas sigue); una sola bandeja para rechazados y vacíos.
  Mientras el carro no se simule, un "carro de reemplazo" se lleva un vaso de la canaleta cada 6
  ticks.
- Sensores: 12 (salen las 2 confirmaciones de expulsión; entran la celda de carga y el Hall).
- Pruebas: **156, todas pasan** (nuevas: vaso con algo adentro, peso real del lote, canaleta
  llena, todo rechazo a la misma bandeja, almacén revólver en su lugar).

**Pendiente:** revisión del punto 5 (almacén revólver) y de los puntos 11 a 15. Pesar el vaso
vacío, medir el ruido de la celda con la cinta quieta y la fuerza para asentar una tapa.

## 2026-09-25 (4) — Corrección: fuera la celda de carga

**Error de la sesión (queda registrado para no repetirlo):** se agregó una celda de carga en el
llenado, que el usuario había PROHIBIDO (y CLAUDE.md decía "no hay celda de carga en el diseño"),
y un sensor Hall que no pidió; además se hizo un cambio grande sin confirmar. Reglas estrictas y
lo prohibido quedan en `CONTEXTO-SESION.md` (leerlo al empezar cualquier sesión).

**Hecho:**

- Se quitó la celda de carga de todo (simulación, pruebas, catálogos, textos). En su lugar, lo que
  pidió el usuario: un **sensor que mira hacia el interior del vaso** en la verificación (VL53L0X,
  el mismo modelo de la cortina): un vaso que ya trae algo no entra. Ya no hay "peso real".
- Compuerta de rechazo con su etiqueta de texto en el 3D.
- Soportes ("patas") modelados para todos los servos (escuadra bajo el servo + barra a la
  estructura) y varillas para el sensor del interior y el Hall.
- Punto 10 aprobado (confirmado por el usuario).

**Pendiente de decisión del usuario (no tocar sin respuesta):** almacén carrusel (pregunta: ¿se
puede asegurar llenado y salida impecables con errores reales? Respuesta: no sin probarlo; ver
riesgos en la conversación del 2026-09-25) y el sensor Hall de referencia.

## 2026-09-26 — Punto 5 aprobado; cortina de un solo sensor (punto 11, preaprobado)

**Revisión con el usuario:**

- **Punto 5 (almacén revólver) aprobado**, con su sensor Hall de referencia.
- **Punto 11 (cortina)**: lo que se busca no es un equipo de seguridad certificado sino que el
  sistema se detenga si ve una mano. Cambios pedidos, todos hechos:
  - **Un solo sensor** (VL53L0X) a media altura, 65 mm sobre la cinta (era el del medio de
    los 3). Se quitan los otros dos, y con ellos la interferencia entre sensores.
  - **Cono real** en la simulación: el VL53L0X ve en un cono de ~25°, no en un rayo. Se emula
    con 19 `rayTest` repartidos dentro del cono (`SensorCono`). Ubicado para que no interfiera:
    eje a 85 mm del eje de la cinta (el cono queda a ~19 mm del reborde de los vasos donde más
    se abre, aguanta ~8° de sensor torcido; por abajo, ~34 mm sobre la cinta). Solo cuenta lo
    que esté a menos del largo de la zona (~140 mm); lo de más allá no. El sensor quedó 20 mm
    pasado el eje de la prensa: en la primera ubicación (35 mm) su poste chocaba con el vaso
    que el empujador pasa a la canaleta (visto en las capturas; hay prueba nueva).
  - **La prensa sube y se detiene** al activarse la cortina (antes se quedaba congelada donde
    iba y podía quedar apretando la mano). Tapa y empujador siguen congelados.
  - **La misma lógica de la cámara** al despejarse (revisa los vasos antes de seguir).
  - **La cámara vigila en cada avance** que ninguna de sus 4 casillas haya quedado sin su vaso,
    por si alguien lo saca por encima sin cruzar el haz (`retirado`, estación `camara`). Un "no
    está" se confirma en la misma pausa con un segundo voto de cuadros nuevos: esperar al
    avance siguiente no sirve, porque el vaso de prensa ya se habría ido a la descarga y se
    entregaba como si nada (lo mostró la primera versión de la prueba).
- El sabotaje "Mano en tapa/prensa" ahora entra a media altura (donde está el haz); una mano por
  encima de los vasos ya no la ve la cortina (queda como prueba del límite aceptado).
- Nuevo estado de revisión **preaprobado** (yaml, dashboard, visor, documentos): cambios hechos,
  falta que el usuario diga que sí. **No modificar más el punto 11.**
- Pruebas: **162, todas pasan**. Demo grabada regenerada.

**Pendiente:** confirmación del usuario del punto 11; revisar 12 a 15.

## 2026-09-26 (2) — Una sola prueba; canaleta con embudo, pestaña de 8 mm y escape

- La cortina detiene solo la cinta de vasos (la de monedas sigue): era lo correcto, sin cambios.
- **Una sola prueba** (`sim/escenarios/prueba_completa.yaml`): la de producción más lo que solo
  tenían las pruebas aisladas (fuera de rango de 10 y 32 mm, incoherente, 2 casillas vacías).
  Trae un caso de cada causa de rechazo. Se quitó el selector de escenario del visor y del
  dashboard. Las pruebas aisladas y el mixto de 20 quedan en `sim/escenarios/pruebas_aisladas/`
  solo para las pruebas automáticas (no se listan).
- `ver-en-vivo.bat` y `app.lanzar --reemplazar --abrir --ver ...`: abre una consola visible,
  cierra la corrida anterior de este proyecto y abre visor y dashboard en el navegador.
- **Punto 12 (canaleta)**, pedidos del usuario:
  - **a)** Entrada en embudo: rieles 4 mm más separados (73 mm) y 3 mm por debajo de la boca en el
    arranque, cerrándose a 69 mm en 40 mm.
  - **c)** Pestaña del reborde de 8 mm (boca de 78 mm): queda 4,5 mm más allá del centro de cada
    riel (antes 1,5). Tapas del mismo diámetro que la boca: con casillas de 80 mm quedan 2 mm
    entre vasos vecinos. La cortina sigue libre (cono a ~16 mm del reborde).
  - **d)** Escape de dos dedos con UN servo SG90 (balancín): el dedo de adelante retiene la fila,
    el de atrás entra entre el primer y el segundo vaso al soltar.
  - **b)** Inclinación: pendiente de decisión (ver abajo).
- Pruebas: **165, todas pasan**. Demo grabada regenerada.

**Pendiente:** decisión del usuario sobre la inclinación de la canaleta. Con la mesa actual (la
cinta de vasos a 10 cm), a 25° la canaleta solo puede medir ~16 cm y caben 2 vasos; para 4 vasos
a 25° habría que subir las dos mesas ~6 cm. Alternativa sin cambiar alturas: 15° con los rieles
forrados en tubo de PTFE.

- Decisión del usuario sobre la inclinación: **15° con los rieles forrados en teflón**. Se usa cinta
  adhesiva de PTFE (~0,13 mm) y no tubo: un tubo de 6 mm de diámetro exterior dejaba 0,5 mm entre
  el cuerpo del vaso y cada riel. En el 3D los rieles se ven blancos.
- Forma de trabajar: corrida escondida permanente (`lanzar --reemplazar`, que ahora cierra
  también la consola que vigilaba la anterior) y `abrir-visor.bat` para mirarla con un clic.

## 2026-09-26 (3) — Punto 13: muelle de carga y secuencia segura

Decisión del usuario: el **muelle** (no tiene pérdida y es repetible aunque el carro llegue con
mucho error), más lo de las otras propuestas:

- **Muelle:** el carro entra de reversa. Dos guías en V impresas en el piso lo centran por el
  costado de las ruedas motrices (boca 9 cm más ancha, cierran a 1,5 mm de holgura) y dos topes
  con espuma, a los lados del paso del vaso, paran la cola del chasis con la cuna bajo el final de
  la canaleta. Sabe que llegó porque los encoders dejan de contar: sin sensor nuevo.
- **Cuna:** rieles forrados con PTFE, 3 mm más bajos que la canaleta y con entrada en embudo
  (73 → 69 mm en 20 mm); tope delantero con espuma.
- **Secuencia segura** (simulada con el carro de reemplazo): `en_muelle` → la cuna tiene que
  estar vacía (si no, alarma `cuna_ocupada`) → `soltar` UN vaso → el infrarrojo de la cuna
  confirma (`carga`); si no, alarma `carga_no_confirmada`, el carro no se va y no se suelta otro.
  Error del infrarrojo de la cuna en `errores_sensores.cuna`.
- Pruebas: **167, todas pasan**.

- **Lengüeta trasera** (decisión del usuario): la cuna queda abierta por atrás y sobre teflón el
  vaso se saldría al arrancar (~1 m/s²). Trinquete pasivo con resorte y pasador de tope, del lado
  opuesto al infrarrojo de la cuna; en la meta el vaso se saca levantándolo.

**Pendiente:** aprobación de los puntos 12 y 13; siguiente, punto 14 (ruta del carro).

## 2026-09-26 (4) — Puntos 12 y 13 aprobados; punto 14: el carro va y vuelve solo

- **Aprobados** los puntos 12 (canaleta) y 13 (muelle). El 11 sigue preaprobado: el usuario
  preguntó si la cortina cubre la caída de las monedas al vaso (llenado): NO, cubre tapa y
  prensa (ver conversación).
- **Punto 14**, decisiones del usuario: esquivar como sea con tal de llegar y volver solo;
  hacia el lado con más espacio (girar hacia un lado y devolver el giro pasado el obstáculo);
  3 ruedas si es mejor contra el error; varias lecturas y maniobras lentas; revisar
  estabilidad, optimización, control del vaso y evasión.
- Hecho: `control/vehiculo.py` (control puro) y `sim/vehiculo_sim.py` (física real, mundo
  propio). Carro 2 ruedas + rueda loca. El supervisor usa el carro físico
  (`simulacion.carro: fisico`); el visor lo mueve con la pose de la simulación y deja el
  rastro; la pestaña Ruta del dashboard dejó de estar pendiente.
- Lo que la simulación mostró y se corrigió (pasaría igual en el montaje real):
  - Un muro a 30 cm de la meta: la maniobra ocupa ~80 cm y el carro se salteaba la meta →
    última recta de 1,1 m; rectas con muro de 90 cm (con 60, al volver caía en la curva).
  - Media vuelta en la marca de giro sobre la curva → primera recta de 60 cm y, antes de
    entrar de reversa, 15 cm siguiendo la línea para enderezarse.
  - Las guías del muelle empujaban las llantas y el carro se trababa torcido → **rodillos
    guía** (rodamiento 623) en las esquinas traseras; guías con PTFE, boca de ~13°, 3 mm de
    holgura; en la boca el control deja de corregir el rumbo y manda la guía.
  - Contra el tope la llanta patinaba y el encoder seguía contando → se entra con PWM bajo.
  - Una lectura mala del infrarrojo hacía "encontrar" la línea donde no estaba → cada
    infrarrojo por mayoría de 3 lecturas y 4 seguidas para volver a la línea.
- Resultado: ida y vuelta sin errores, con los errores de la configuración (3 semillas) y con
  el doble de error (6 de 6): 6 muros esquivados sin tocarlos, vuelve al muelle con < 3 mm de
  error, el vaso cabecea < 2°. Pruebas: **174, todas pasan**.

**Pendiente:** aprobación del punto 14; respuesta sobre la cortina y el llenado (punto 11);
punto 15.

## 2026-09-26 (5) — Punto 11 aprobado, carro más rápido y proyecto reorganizado

- **Cinta de monedas:** avanza solo si lleva algo registrado o si el infrarrojo de la carga ve
  algo; vacía y sin carga espera quieta (evento `espera`). Si el infrarrojo no ve un objeto que sí
  está, se vuelve a leer en la pausa siguiente. El visor animaba la cinta en cada ciclo aunque no
  avanzara: ahora solo cuando avanza.
- **Punto 11 aprobado:** la zona por donde cae el lote al vaso de llenado la vigila la cámara de
  vasos (franja por encima de la boca): una mano ahí cuenta como cortina (cinta de vasos quieta,
  prensa arriba, el almacén no suelta el lote). Sabotaje "Mano en el llenado".
- **Carro:** soporte de 4 puntos para el vaso (espuma, lengüeta, guías laterales) → sin cabeceo →
  0,25 m/s en línea, aceleración 0,8 m/s², viaje ~165 s (antes ~250). El ultrasónico se simula
  como el HC-SR04 real (una medición cada 60 ms); umbral de obstáculo 200 mm. Probado con los
  errores de la configuración y con el doble: sin roces, muelle < 2 mm.
- **Visor:** el carro se mueve a velocidad constante (la simulación manda la trayectoria de cada
  ciclo, una muestra cada 0,1 s, y el visor la reproduce en su tiempo real); más liviano
  (sombras 2048 en modo normal, solo las superficies grandes las reciben, resolución máx. 1,5×,
  la escena se sincroniza solo con cada ciclo nuevo).
- **Reorganización** (respaldo previo en `../respaldos/`): fuera `sim/entorno.py`,
  `sim/linea_autonoma.py`, `app/simular_sensor.py` y sus pruebas (la planta hace todo eso);
  `docs/sensores/` (12 carpetas) → `docs/sensores.md`; catálogos en `sim/catalogos.py`; la cámara
  oráculo dentro de `sim/sensores_sim.py`; escenarios de un solo filtro a `tests/escenarios/`;
  carpetas vacías de fases futuras fuera; sin ventana de PyBullet (`--gui`); dashboard sin las
  pestañas que repite el visor (Vista 3D, Paso a paso, Sensores); un solo `visor.bat`. README y
  CLAUDE.md (sección 9) al día.

## 2026-09-26 (6) — Láser frontal, carro a 0,40 m/s y modelo 3D del carro

- El HC-SR04 ve lejos (4 m) pero mide lento (60 ms): decisión (el usuario la delegó): **VL53L0X
  al frente como sensor principal** (cada 33 ms, ~1,2 m; el mismo modelo de la cortina, mismo
  bus I2C, barato) y **el HC-SR04 de respaldo** (no le afectan superficies negras/brillantes ni
  el sol). Un lidar giratorio no hace falta (solo se mira adelante) y es caro. Sensor 13.
- **Zona de frenado:** algo a < 500 mm → velocidad de maniobra; < 200 mm en 3 mediciones del
  láser (o 2 del ultrasónico) → para y esquiva. Así las rectas van a 0,40 m/s (aceleración
  1 m/s²) sin llegar rápido al muro. Viaje de ida y vuelta ~2,5 min.
- **Error encontrado:** al encontrar la línea buscándola, el control borraba toda la maniobra
  pendiente (en la marca de giro se saltaba la entrada al muelle y seguía la línea de vuelta).
  Ahora solo quita los pasos de búsqueda. Con el doble de error: 6 de 6 viajes completos.
- **Modelo 3D del carro:** chasis de acrílico con segundo piso sobre separadores, motorreductores
  TT (caja + motor) con llanta y rin con rayos, encoders (disco + horquilla), rueda loca con
  carcasa, porta-baterías 2×18650 con las celdas, ESP32 DevKit (módulo, antena, USB, pines),
  TB6612, arreglo de TCRT5000 en su soporte, HC-SR04 y VL53L0X en su escuadra con sus conos.

## 2026-09-26 (7) — Punto 14 aprobado; revisión final antes del protocolo

- Punto 15: lógica aprobada por el usuario. Decisiones: (a) mensajes numerados y confirmados;
  (b) latido con parada segura; si el carro pierde contacto termina la vuelta y queda en el
  muelle; al reconectar, no se le carga otro vaso sin saber si trae uno: lo dice el infrarrojo
  de la cuna (sensor 12, ya existe: no hace falta sensor nuevo), que también confirma que en la
  meta sacaron el vaso; (c) actualizar el protocolo, pero DESPUÉS de una revisión total.
- **Revisión final** (detalle en `docs/revision-final.md`): auditoría automática de espacio en el
  visor (`?auditar`: cajas orientadas, prueba de ejes separadores) → 29 cruces, todos los reales
  corregidos; conos nominal + error probable para cada sensor; puertos y pines de los dos ESP32
  y del portátil; alimentación; largos de cable; ruido; conexiones.
- Corregido: FC-51 como sensor de presencia (el TCRT5000 no llega a 5 cm); cámara cenital a 15 cm
  y con autoenfoque; sensor del interior a 1,5 cm de la boca; infrarrojo de la cuna a 6 mm del
  vaso; caja de control y portátil más cerca de la planta (cable total 21 → 15 m; las webcams
  llegan con 1,5 m); especificación de fuentes (12 V 10 A + 6 V 8 A servos + 5 V 3 A).
- **Pendiente de decisión:** sensores de material (E2) debajo de la cinta (a los costados no ven
  una moneda chica centrada).

## 2026-09-26 (8) — Botones, sensores de material bajo la cinta, servos anclados y cables en 3D

- **Botones del visor:** agrupados (Línea / Sabotajes a los vasos / Manos en la línea / Fin de
  turno). Los que "no funcionaban" no hacían nada en silencio cuando no había un vaso en la
  estación que necesitan o la línea no corría. Ahora cada botón se habilita solo cuando puede
  hacer algo (al pasar el mouse dice por qué no) y el supervisor responde cada orden
  (`ultima_orden`: hecho / no se pudo y por qué), que el visor muestra 7 s.
- **Sensores de material (E2) debajo de la cinta** (usuario): capacitivo centrado bajo E1 e
  inductivo bajo E2 (una moneda de 17 mm no tapa dos caras de 18 mm a la vez); inductivo M18 de
  8 mm (LJ18A3-8-Z/BX: el M12 de 4 mm no alcanzaba a través de 2 mm de banda con monedas no
  ferrosas); inserto impreso en la bancada; retorno de la banda bajado por dos rodillos; banda
  una casilla más larga (el rodillo de cola quedaba a 2 cm de E1); rieles laterales y patas por
  fuera de la banda. En la simulación el capacitivo lee la casilla E1 y su lectura se usa en E2.
- **Hall del carrusel:** imán 6 × 3 mm en el disco (0°, entre dos tubos) y el sensor 4 mm encima.
- **Servos revisados uno por uno:** los 6 tenían soporte, pero se veían "posados" (la escuadra
  quedaba 1,5 mm por debajo y nada los sujetaba): cuna con torres bajo las orejas y tornillos.
  Se encontró además flotando el poste de la cortina (arrancaba fuera de la mesa): brazo a la
  bancada. Una pata de la mesa de monedas atravesaba la viga del pórtico: ese extremo apoya en
  la viga con un taco.
- **Modelado:** caja de control con cada pieza en su medida (30 × 20 × 8 cm), hub USB, módulos
  reales (M18 roscados, KY-003, GY-530, servos con orejas y cable, JST de los NEMA).
- **Cables en 3D** (botón "Cables", muestra u oculta todo): 30 cables de la planta por la
  estructura (viga, columna, piso; señales y motores por prensaestopas separados; USB por otro
  camino) y 11 del carro. Largo medido: 21,6 m de la planta con 20 % de holgura (la estimación
  anterior de ~15 m no contaba webcams, anillo ni el interior de la caja).
- Pendiente: actualizar el protocolo (punto 15, c).

## 2026-09-26 (9) — Conexionado pin a pin, caja como tablero y carro con nombres

- Usuario: aprobados los sensores de material debajo de la cinta (capacitivo bajo E1, inductivo
  M18 de 8 mm bajo E2).
- **Conexiones exactas** (pedido principal; referencia: los labs de Blender del usuario, con
  cada cable a un pin con nombre y su `conexiones.md`): nuevo `sim/conexiones.py` como fuente
  única. Tiene las plantillas de 30 módulos con sus pines reales, 46 dispositivos y 45 cables
  con sus 150 hilos. `app.documentos` genera `docs/conexiones.md` y
  `tests/test_conexiones.py` verifica pines existentes, sin repetidos y GPIO según la tabla.
- **Visor:** cada módulo se arma desde esos datos, con pines, bornes, conectores y serigrafía;
  cada hilo va de su pin al otro, con carcasa Dupont o férula.
  - Los ESP32 van sobre placas GVS como las de los labs (fijo 38P, carro 30P).
  - La caja de control (36 × 24 × 8 cm) queda como un tablero: fila de lógica, fila de
    potencia, canaletas ranuradas entre ellas (ningún hilo cruza por encima de una placa),
    bornera DIN X2 con puentes y prensaestopas separados.
  - El carro tiene sus módulos con nombre (lo que faltaba) y su cableado completo.
  - La serigrafía se lee derecha según hacia dónde mira cada placa.
- Se quitó la bornera de servos de la columna: extensiones de 22 AWG directo al PCA9685 (caída
  máxima ~0,16 V).
- Siguiente paso del paso a paso: punto 15 (protocolo), el único pendiente.

## 2026-09-27 — Vistas, cables sin cruces, estados calculados y punto 15

- **Barra de arriba:** vistas agrupadas por sección, agregando las que faltaban (Material bajo
  la cinta, Tapa y prensa, Carro, Caja de control). Las acciones (Cables, Panel) van aparte, con
  otro estilo y su estado encendido/apagado.
- **Cables sin cruzarse ni atravesar piezas:** script de revisión que muestrea cada cable cada
  3 mm. Primera pasada: 34 tramos dentro de piezas y 202 pares de cables encimados.
  - El mazo del pórtico va por el costado -y de la viga (arriba estaba el taco de la mesa de
    monedas), con un lugar fijo por cable, ordenado para que no se crucen, y baja por la cara +x
    de la columna a un prensaestopas grande.
  - En la caja se agregó una canaleta trasera junto a la bornera de la fuente, el ruteo por la
    red de canaletas es el camino más corto y cada hilo tiene su propio lugar.
  - Las webcams van por carriles que no se cruzan (la de vasos da la vuelta por la izquierda y
    necesita una extensión USB de 1 m).
  - En el carro, lo de abajo de la placa sube por dos agujeros al frente.
  - Los cables de servo bajan por fuera de los postes.
  - Resultado: 2 roces leves con piezas (≤ 2 mm). Los contactos que quedan entre cables son
    dentro de canaletas y del agujero del carro, como en un mazo real.
- **Estados de los componentes calculados** (`sim/catalogos.py`): simulado / efecto simulado /
  solo visual, más si están en 3D y cuántos hilos tienen. Se corrigieron los que estaban viejos
  (escape de la canaleta, pista, cuna: simulados). La "conexión" ya no dice "pendiente".
- **Punto 15** (preaprobado):
  - `control/protocolo.py`: mensajes numerados con ack, reintentos, latido, parser tolerante,
    parada segura y la regla para soltar un vaso.
  - El carro decide con su infrarrojo de la cuna cuándo salir y cuándo volver.
  - Radio simulada entre el carro y la estación, con el botón "Cortar la radio del carro".
  - Contrato en CLAUDE.md 10.1. Pruebas en `tests/test_protocolo.py` y `tests/test_planta.py`.

## 2026-09-27 (2) — Dashboard para cualquier persona, carro ordenado, componentes completos

- **Dashboard de Streamlit rehecho** para alguien que no conoce el sistema:
  - Pestañas: Resumen, Monedas y vasos, Calidad del filtro, Línea en vivo, Carro y ruta, Montaje
    real, Asistente (fase 7) y Ayuda (qué hace el sistema y glosario).
  - Resumen: valor, monedas, rechazos, vasos y peso; una tarjeta por parte (cintas, almacén,
    carro con su radio); un diagrama de flujo de las piezas; y "Qué está pasando" en frases
    simples, no en eventos crudos.
  - Calidad del filtro: matriz de lo que era cada pieza contra lo que decidió la línea, con el
    porcentaje de aciertos.
  - Controles simples; los técnicos, en "Ajustes avanzados". Se ve la respuesta a cada orden.
  - Las pruebas de sabotaje son las mismas que en el visor, incluida la radio del carro.
  - El recorrido del carro se guarda cada 0,1 s (antes, un punto por ciclo: se veían
    triángulos).
  - Prueba de humo con el AppTest de Streamlit (`tests/test_dashboard.py`).
- **Visor 3D:**
  - Hilos del carro en tramos rectos, sin diagonales.
  - Etiquetas de tamaño fijo en pantalla: se leen desde lejos y de cerca no tapan todo.
  - Clic en un componente o sensor: encuadre automático al tamaño de la pieza, desde afuera
    de la planta; desde abajo para los que están bajo la cinta; y siguiendo al carro para lo
    que va en él.
- **Componentes completos:** cada módulo por separado (reguladores, fusibles, bornera,
  entrada de red, optoacopladores, reparto I2C, ULN2003, hub USB, canaletas, interruptor del
  carro) y los 13 sensores en la misma lista, con su estado, sus hilos y si están en 3D.

## 2026-09-27 (2) — Fase 7: asistente (DeepSeek) y órdenes al carro

Pedido del usuario (recuperado del transcript: la sesión anterior se cerró a la fuerza cuando
empezó a implementar lo de todos los grupos del PDF; somos solo el grupo 7).

**Hecho:**

- Streamlit: la pestaña del carro (mapa de la ruta, estado, viajes) y la de montaje real ahora se
  refrescan solas (`st.fragment(run_every)`); antes el mapa quedaba quieto hasta recargar.
- Drivers: el de la cinta de vasos es el mismo A4988 que el de monedas, en la misma placa → una
  sola entrada `drivers_cintas` (antes el de vasos salía en la lista sin 3D).
- `app/asistente.py`: la lógica del tema 4 (frase → DeepSeek → JSON → validar → actuar). Lee
  todo el proyecto por búsqueda (secciones de README, CLAUDE.md, docs y configuración), recibe el
  estado en vivo de SQLite, nunca inventa cifras, lista blanca de órdenes con rangos, voz
  (SpeechRecognition es-CO + gTTS), intérprete local sin internet. Una pregunta nunca mueve nada.
- Carro (`control/vehiculo.py`): órdenes `detener`, `avanzar`, `retroceder`, `girar`, `ir_a`,
  `ir_meta`, `volver_muelle`, `seguir_linea`; odometría con los encoders (se pone en cero al
  entrar al muelle); antes de moverse mira el camino a 0 y ±15° (`camino_bloqueado`), en marcha
  se detiene si ve algo (`bloqueado`) o si una rueda patina contra algo (`atascado`). Van por la
  radio: sin enlace no llegan.
- Encontrado al probar: la evasión automática del tercer muro rozaba el extremo del muro al
  volver en diagonal (1 de 11 semillas de error). Nuevo `margen_pasar_muro_mm: 70` (PROVISIONAL):
  pasa un poco más el muro antes de volver. 20 semillas sin tocar muros.
- Dashboard: pestaña Asistente (chat, micrófono, voz, ejemplos, qué pasó con cada orden) y
  botones de órdenes al carro; el mapa muestra dónde cree el carro que está (odometría).
- Visor 3D: nube "API de DeepSeek" sobre el portátil unida por el Wi-Fi (un paquete viaja con
  cada mensaje; clic → pestaña Asistente, de solo lectura), anillo de la odometría y marcador del
  punto pedido en la pista.
- Enunciado ordenado: `docs/enunciado/segundo-parcial-umng.pdf` y las figuras numeradas, con su
  README. Entrega: martes 29-09-2026, 23:59.
- Paso a paso: punto 16 (asistente y órdenes al carro), pendiente de revisión.

**Pendiente:**

- La clave de DeepSeek del tema 4 fue rechazada (401): poner una válida en `.env` y probar las
  respuestas reales.
- Que el usuario revise el punto 16 y apruebe el 15.

## 2026-09-27 (3) — Fase 8: firmware de los dos ESP32 y hardware real

**Hecho:**

- `firmware/` en MicroPython (decisión: el del curso; así el control del carro y el protocolo
  corren tal cual en las placas, compilados con mpy-cross). Estación fija: A4988 por PWM,
  28BYJ-48, PCA9685 con los 6 servos, VL53L0X de cortina e interior con XSHUT, parada segura
  sin latido del PC, cortina que reacciona en la placa, puente ESP-NOW. Carro: `ControlCarro`
  real, TB6612 con corrección por encoders, HC-SR04 por interrupciones, eventos reenviados
  hasta el ack.
- `firmware/preparar.py`: pines desde `sim/conexiones.py` y valores desde la sección nueva
  `firmware:` de `config/parametros.yaml` (PROVISIONALES); `firmware/subir.py` con mpremote.
- `app/puente_serial.py` (drena todo el serial, última línea cruda, estación emulada si no hay
  placa) y `control/hal/backend_real.py`.
- `hardware.backend: sim|real` en `config/parametros.yaml`: la línea que cambia la simulación
  por las placas en el supervisor (monitoreo, paro/reanudar, prueba de actuadores, órdenes al
  carro).
- El proyecto se movió dentro del repo (`Sensores-Teoria/proyecto-final/`) y se sube a GitHub.
- Streamlit: chat con lo más nuevo arriba. Visor: sin pestaña de asistente; panel de solo
  lectura sobre la nube y botón de vista "Asistente".

**Pendiente:** probar en las placas reales; medir los PROVISIONALES; visión real (fase 5, faltan
fotos); clave de DeepSeek válida (la dada da 401).

## 2026-09-27 (4) — Revisión, modelo local, costos y laptop

- Paso a paso: punto 15 **aprobado**; 16 y 17 **en pausa** (estado nuevo `pausa`: necesitan el
  montaje real).
- Asistente con modelo local: Ollama + qwen2.5:3b (fuera del repo), ~5 s por respuesta en la
  RTX 3050. Encontrado al probarlo: con el prompt completo el modelo perdía las instrucciones
  (contexto de Ollama) → contexto corto; inventaba varias órdenes → las órdenes claras las decide
  el intérprete de reglas y va una sola orden al carro por mensaje; se equivocaba en el signo del
  giro → lo manda la frase.
- Costos en Colombia (`config/precios.yaml` → `docs/costos.md`, dashboard "Montaje real" y
  asistente): **$1.680.746**, 28 % estimado; 7 propuestas de ahorro con su riesgo, NO aplicadas.
- Visor: laptop ASUS TUF Gaming A15 con medidas de la ficha oficial (359 × 256 × 24,7 mm,
  teclado, touchpad, bisagra, tapa a ~110°) y el asistente en su pantalla (el panel ya no flota
  sobre la nube).

## 2026-09-27 — Auditoría general, modelo local más completo y laptop ×1,5

- Laptop ASUS TUF Gaming A15 rehecha al nivel de los modelos de Blender de los labs: esquinas
  redondeadas, teclado completo en relieve con letras (WASD translúcidas), touchpad, luces de
  estado, rejillas, puertos con profundidad, bisagras, logo TUF. Medidas reales, dibujada ×1,5 (a
  pedido, para leer la pantalla); movida detrás de la caja de control: la anterior se metía 7 mm en
  la fuente y 3 mm en el ESP32 (auditoría de solapes). Nube centrada sobre ella (0,4 mm).
- Pantalla = el asistente con la letra más grande que cabe; "pensando": con el modelo local se
  anima la laptop (teclado RGB, luz de actividad) y no la nube; con DeepSeek, la nube.
- Modelo local con 8192 tokens y candados nuevos (ver CLAUDE.md §14); batería real 24/24.
- Auditoría: (1) el backend real tenía el sensor del interior como distancia y la simulación como
  sí/no → alineados (umbral con `margen_interior_mm`, que nadie usaba); la cortina la decide el
  ESP32; nombres iguales a los del backend sim. (2) `backend_sim` tenía las franjas de la cámara
  de vasos escritas a mano (0,5 y 1,05) aunque decía que venían de la configuración; `geometria`
  tenía la altura del vaso a mano → ahora de `config/parametros.yaml`. (3) Pausa de la cinta de
  monedas duplicada (300 ms sin uso vs 1000 ms real) → quitada; CLAUDE.md decía 300. (4)
  Micropaso duplicado (16 vs 4) → uno solo (1/4) en `motor_paso_a_paso`; el firmware lee los pasos
  por vuelta y el rango mínimo del ultrasónico de la configuración. (5) Cable USB hub→laptop con
  su recorrido real. (6) Abrazadera del VL53L0X del interior (la varilla parecía atravesar la
  placa). Sin código muerto. Solapes restantes (24): montajes, ejes dentro de rodillos, vasos en
  la bandeja, piezas del carro; la auditoría trata cilindros como cajas y exagera.

## 2026-09-27 — Visor portable que pasa solo al vivo

- `visor.bat` abre `visor-portable.html` (un solo archivo de ~2 MB: Three.js y OrbitControls como
  módulos embebidos en el importmap, el visor y la demo grabada) y arranca la simulación por
  detrás, sin abrir otra pestaña. La página muestra la demo y pregunta cada 3 s a
  `127.0.0.1:8765/api/estado` (el servidor ya permite CORS); cuando responde, la pestaña pasa sola
  al visor en vivo. Si la simulación ya estaba corriendo, va directo (en ~1 s).
- Probado con Chrome sin ventana: con la simulación corriendo → vivo en 1 s; sin ella → demo, y
  al arrancarla 12 s después → vivo a los 22 s, sin errores. Sin Python ni internet (otro PC) se
  queda en la demo. `tests/test_portable.py` (5 pruebas).

## 2026-09-27 — Voz sin internet y avisos de "no es en vivo" / "sin internet"

- Voz: con internet Google (oír) y gTTS (hablar), como el tema 4; sin internet Whisper `small` en
  el PC y la voz de Windows (Helena, es-ES). Probado en cadena (voz de Windows → WAV → Whisper):
  "Avanza 20 centímetros y después vuelve al muelle." y "¿Cuánto dinero hay en los vasos?" exactos,
  ~2,5 s cada una. Sin internet DeepSeek ni se intenta.
- Dashboard: chips de origen de los datos (simulación / ESP32 real / emulado) y de internet; avisos
  grandes "NO ES EN VIVO" (supervisor cerrado: datos de la última corrida), "ESP32 EMULADO" y "SIN
  INTERNET" (qué sigue funcionando).
- Visor: avisos "DEMO GRABADA", "SIN CONEXIÓN CON LA SIMULACIÓN" y "SIN INTERNET" arriba al centro
  (10 s completos, luego una línea para no tapar la pantalla de la laptop); sin internet la nube se
  pone gris con "Sin internet · responde el modelo local". En la demo el chip ya no sale verde.
- Pruebas: `tests/test_voz.py` (5) y 2 del dashboard. Capturas con Chrome sin ventana y la red
  cortada por DevTools.

## 2026-09-27 — Arreglo del falso "sin internet" del visor

- Al abrir `visor.bat` el visor decía "sin internet" con internet (DeepSeek respondía en 0,6 s).
  Causa: probaba UNA vez al arrancar, desde el navegador, mientras armaba la escena 3D; el intento
  se pasaba de los 5 s y quedaba "sin internet" hasta la siguiente revisión, 20 s después. Ahora, en
  vivo, pregunta al supervisor (`/api/internet`, el mismo chequeo que el Streamlit); en la demo,
  varios sitios y 2 fallos seguidos.
- Chip "🌐 con internet" / "📴 SIN INTERNET" al lado de los ticks (como en el dashboard); se quitó el
  letrero de la nube que se encimaba y el recuadro central repetido. El paso del HTML al vivo se
  volvió a probar desde el archivo: vivo en ~1 s, chip "con internet", sin avisos.


## 2026-09-27 — Carro: destinos imposibles, README, revisión final y agentes

- **El carro se atoró** cuando el usuario le pidió al asistente (modelo local) "que vaya a donde está
  el filtro de monedas, lo atraviese…": el modelo prometió "cruzará por él" y mandó `ir_a (-0,5; 0)`.
  Causa: el láser (7,4 cm del piso) y el ultrasónico (5,7 cm) no ven las guías del muelle (2 cm) ni sus
  topes (4,5 cm), y la planta no existe en el mundo del carro; además la odometría llegaba corrida
  ~30 cm tras la vuelta. Reproducido en simulación (mismo `atascado` de -41 mm).
- Arreglo en el carro (`control/vehiculo.py`, compatible con MicroPython): mapa FIJO de dónde puede
  andar (`sim/geometria.py: zonas_carro`, márgenes PROVISIONALES en `config/parametros.yaml`,
  `zonas_carro`): piso libre alrededor de la pista y huellas prohibidas (planta, canaleta, muelle,
  poste de la cámara). `ir_a` y `avanzar` rechazan sin moverse un destino o un camino recto que las
  toque; la odometría se corrige en la meta y en la marca de giro; atascado, se aparta por donde vino;
  `volver_muelle` pegado al muelle se endereza y entra de reversa.
- Arreglo en el asistente: pedir que el carro atraviese la planta se contesta con reglas ("Eso no se
  puede…"), con cualquier proveedor, sin órdenes; un `ir_a` a un punto prohibido ni se manda y la
  respuesta dice por qué (mismo mapa). 14 pruebas en `tests/test_asistente_planta.py` + 7 del carro.
- Pendiente visto al reproducir: el paso `reversa_tope` no tiene tiempo límite (se vio 35 s avanzando
  milímetro a milímetro antes de la orden).
- Visor: la etiqueta "API de DeepSeek" de la nube cambia a "· sin internet". La primera vez no se veía
  bien porque `actualizarEtiquetas` volvía a encender en cada cuadro las etiquetas apagadas: ahora
  respeta `userData.oculta` (también arreglaba el rótulo del vaso del carro). Vista del carro y sus
  componentes al doble de distancia (~0,6 m).
- `visor.bat` abre también el dashboard de Streamlit cuando responde (`lanzar --abrir-dashboard`).
- README del proyecto reescrito a fondo; revisión final (textos desactualizados corregidos: TCRT5000 →
  FC-51, cámara a 15 cm, 6 servos, estados del paso a paso, CLAUDE.md §11/§16). Fechas de estos días
  corregidas a 2026-09-27.
- Se usaron subagentes (máx. 4 a la vez); quedaron guardados para reusar en `Micors-teoria/.claude/agents/`.

## 2026-09-27 — Pruebas de un filtro, "colocar pieza", reversa con límite y scripts de ejecución

- **Filtros uno por uno** (el enunciado lo exige en la sustentación): `sim/carga_escenarios.py`
  (`PRUEBAS_DE_UN_FILTRO`) expone los 6 escenarios de un solo filtro de `tests/escenarios` (los de las
  pruebas automáticas). Dashboard: "Probar un filtro" en la barra lateral y un aviso arriba con lo
  esperado y cuántas piezas ya se rechazaron por esa causa. Visor: selector en "En vivo" y, en la
  pestaña Sensores, **"Ver la prueba de este sensor"** para cada uno de los 13 (un filtro, un sabotaje,
  una pieza o una orden al carro) con la cámara mirándolo. El supervisor solo acepta escenarios por
  nombre (nunca una ruta), porque ahora llegan también por HTTP.
- **Colocar pieza X**: orden `colocar` (15 piezas: cada moneda, euro, botones, bloque, disco de 10 mm,
  cara de $500 con otro diámetro); entra en la próxima carga y, si la corrida había terminado, sigue
  solo para procesarla. Botones en el visor y el dashboard.
- **Reversa al muelle con límite**: la semilla 2 se trababa 79 s contra la guía en V (entra ~3°
  torcido y con PWM bajo no alcanza a correr el rodillo). Ahora, pasado `reversa_tope_max_s` o sin
  avance en 3 s, se endereza, sale 15 cm y reintenta una vez con PWM normal hasta 5 cm más allá de
  donde se trabó; si vuelve a fallar, `no_llego_al_tope`. Evento nuevo `reversa_reintento`. La causa de
  fondo (la entrada algo torcida) sigue pendiente.
- **Ejecución**: `requirements-lock.txt` (versiones exactas, Python 3.14.3), `instalar.bat` (entorno,
  firmware, Ollama, Whisper, chequeo), `python -m app.chequeo` (revisión previa a la sustentación;
  en este PC: 0 fallas, avisos por la clave de DeepSeek y ningún ESP32 conectado), OpenCV instalado.
  El driver del VL53L0X no se incluye (su repositorio no declara licencia): se descarga una vez.
- **Visión lista para cuando haya fotos**: `vision/capturar_dataset.py` y `vision/entrenar.py`
  (MobileNetV2, matriz de confusión, curva de confianza, confianza mínima sugerida), en un entorno
  aparte con Python 3.12 porque TensorFlow no tiene versión para 3.14.
- La cámara decía "E5 · Visión" (de antes del filtro total): ahora E3.
- Prácticas 1-9 del repo revisadas y mejoradas a fondo con subagentes (`revisor-practica`).

## 2026-09-27 — Muelle (causa de fondo), visión en el mismo entorno y "colocar pieza"

- **Muelle, causa de fondo**: el control de reversa suponía que empezaba en la marca de giro (~44 cm)
  y corregía el rumbo con los encoders los primeros 25 cm; pero tras `alinear` + `seguir_corto` la
  reversa empieza a 32-35 cm, así que seguía corrigiendo ~20 cm DENTRO de la guía en V y peleaba
  con ella (semilla 2: llegó a la boca a -2,7° y 5 mm, se trabó a +3,4° y 12 mm). Con 20 ranuras
  (10,2 mm/pulso ≈ 4° por pulso de diferencia) el encoder no puede enderezar más fino, y 5 IR a
  15 mm no ven ±5,5 mm. Arreglo: `_reversa_hasta_boca()` corrige solo hasta la boca (odometría +
  `pose_muelle`, `boca_muelle_mm: 305` verificado contra la simulación, margen 30 mm PROVISIONAL);
  adentro manda la V. **26 viajes completos, 0 reintentos** (semillas 1-16 y doble error 1-14); el
  reintento queda de red de seguridad. Pendientes vistos: `ir_a` puede dar `llego_al_punto` en falso
  si las dos ruedas patinan parejo (sin el mapa); a 40 Hz la semilla 1 maniobra de más en un muro.
- **Visión sin entorno aparte**: Keras 3 corre sobre PyTorch (`KERAS_BACKEND=torch`), que sí tiene
  versión para Python 3.14: `torch` 2.14 (CPU), `keras` 3.15 y `matplotlib` en el mismo `entorno` y
  en `requirements-lock.txt`. Se quitó `vision/entorno` (Python 3.12). Probado: 1 época con 36
  imágenes sintéticas de 3 clases → modelo, matriz de confusión, curva de confianza y métricas.
  (Keras 3 cambió `compile`: el tercer argumento posicional ya no es `metrics`.)
- **Colocar pieza**: la lógica estaba bien, pero el visor dibujaba TODO lo metálico no-moneda como
  botón con 2 ojales: el euro y el disco de 10 mm se veían perforados aunque la cámara (bien) no les
  encontraba agujeros, y el dashboard los llamaba "botón metálico". Ahora cada pieza lleva su
  `apariencia` (moneda extranjera, disco, bloque metálico) y sus `contornos_internos` reales: el euro
  se ve como moneda bimetálica "1 €", el disco liso, y se nombran bien.
- Visor 3D: remodelado por zonas con piezas reutilizables en `app/visor3d/piezas/` (copia y catálogo
  en `Blender with claude/piezas-threejs/`, sin abrir Blender) — en curso.

## 2026-09-28 — Visor 3D remodelado a fondo con piezas reutilizables (13 agentes)

- A pedido del usuario ("mejorar absolutamente todo del visor"), modelado en **Three.js** (el usuario
  pidió no abrir Blender) con el contexto de `Blender with claude/` (catálogo, medidas, lecciones).
  Cada pieza es un módulo en `app/visor3d/piezas/` (convención en su `README.md`: `crearX(opciones)`,
  metros, origen = punto de montaje, anclas `pin_<id>_<PIN>` con `userData.dir`, try/catch con el
  modelo anterior de respaldo) y se guardó una copia en `Blender with claude/piezas-threejs/` con su
  fila en `CATALOGO_COMPONENTES.md`: `base.js`, `sensores.js` (13 sensores con medidas de ficha),
  `electronica.js` (ESP32 30P/38P, placas GVS, TB6612, A4988/TMC2208, PCA9685, fuentes, bucks, hub,
  NEMA17, servos…), `carro.js`, `pista.js`, `linea_monedas.js`, `linea_vasos.js`, `estructura.js`
  (perfil 2020 con su sección real), `control.js` (gabinete, prensaestopas, laptop). El portable
  los embebe.
- Encontrado y corregido en el camino: **pinout del ESP32 espejado** en `sim/conexiones.py`; varias
  plantillas más chicas que el módulo real (H206, TCRT, arreglo de 5 IR, pack 2S, NEMA17: ahora con
  medidas de ficha); **el retorno de la banda de monedas atravesaba los sensores M18** que cuelgan bajo
  la cinta → ahora baja 11 cm con 3 rodillos de desvío (C la tensa por arriba, B y A por debajo);
  7 choques reales corregidos (cortina contra la canaleta, IEC contra la bornera, escape contra el
  muelle, compuerta de desvío contra su canal, tubo de tapas, Hall contra una varilla, lámina de la
  pista bajo el muelle), tubos del almacén con 4 mm entre agujeros; `margen_planta_mm` 150 y
  `medio_ancho_canaleta_mm` 100 en el mapa del carro.
- **Cables rehechos**: salen de las anclas reales de cada pin, van por canaletas/bordes/postes,
  entran por los prensaestopas; cruces cable-pieza de ~110 a 0. Ventilador de la caja agregado a
  `conexiones.py`; placa GVS de 38 pines como pieza real.
- Vistas "Material" (casi desde abajo) y "Caja de control" (desde arriba) reencuadradas: las piezas
  nuevas tapaban lo que mostraban.
- Pendiente: `zonas_carro` no incluye el portátil ni el hub (en el piso, y 0,34–0,47).


## 2026-09-28 — Visor liviano y sin parpadeos, interfaz y Streamlit rehechos, proyecto ordenado

- **Rendimiento del visor** (sin quitar detalle): `piezas/optimizar.js` une las mallas quietas por
  componente y aspecto de material (color por vértice) y hace mallas "solo sombra": de 3.221 mallas
  a 714 y de ~3.000 a **~440 draw calls** en la vista Todo (con sombras, de ~5.200 a ~580). El
  resaltado por componente, el clic en sensores y las animaciones siguen funcionando.
- **Parpadeo**: dos causas. Precisión de profundidad (cámara con near 5 mm / far 30 m) → plano
  cercano dinámico `clamp(distancia/40, 2 mm, 8 cm)` + `polygonOffset` en serigrafías; y caras
  EXACTAMENTE coplanares (teclado de la laptop contra el canto de la cubierta, mortero de los muros
  contra las puntas de los ladrillos, canaletas de la caja, difusor, bandejas, piso del gabinete,
  fuente) → separadas 0,2-0,5 mm. Rótulos de la laptop y la nube con prueba de profundidad (se veían
  encima de otras tomas).
- **Interfaz del visor rehecha** (`interfaz.js` + `estilo.css`, ~550 líneas menos en `visor.js`):
  barra fija, vistas en la parte libre, pestaña **Pruebas** con todos los controles en orden
  (Línea · Probar un filtro · Colocar una pieza · Sabotajes · Carro y radio · Fin de turno), respuesta
  del supervisor al pie, componentes agrupados por zona. Inventario verificado en
  `docs/interfaz-visor.md`. El portable sigue los imports de `visor.js` solo.
- **Streamlit rehecho** como paquete `app/dashboard/` (entrada `inicio.py`, `estilo.py` con el
  sistema de diseño del visor, `datos.py`, una pestaña por módulo, pestaña **Pruebas**); solo se
  refresca la pestaña abierta; Space Grotesk por fin aplicada. 70 funciones inventariadas en
  `docs/interfaz-dashboard.md`; 38 pruebas de AppTest.
- **Pendientes**: el portátil y el hub en el mapa del carro (`config/parametros.yaml: puesto_pc`,
  que también usa el visor); brazo portacables para el cable del obturador.
- **Orden**: `tests/` por capa (`control/`, `sim/`, `visor/`, `app/`, `firmware/`), escenarios de un
  filtro en `sim/escenarios/pruebas_aisladas/`, `pytest.ini`, `docs/README.md` (índice). Al moverlos
  apareció que `Supervisor` no cierra su conexión de PyBullet (`sim/mundo.py` usa la conexión 0):
  `tests/conftest.py` las cierra entre archivos (de ~6 a ~2 min); el `cerrar()` del supervisor queda
  pendiente.
- **Revisión final**: vista Asistente negra (la cámara quedaba dentro del NEMA17), clic en el sensor
  del interior (un campo transparente le robaba el clic), motivos de botones grises, textos de
  botones cortados en el Streamlit y leyenda de cables → corregidos. 13/13 sensores con clic real.
- Queda (menor): vista Material y foco de los M18 entre vigas; etiquetas 3D bajo la barra de vistas
  cerca del borde; a 900 px con la barra lateral abierta el mapa del carro se aplasta; tablas de
  Montaje con desplazamiento horizontal; aviso del micrófono de Streamlit en la primera carga.

## 2026-09-28 — Pendientes menores

- `Supervisor.cerrar()`: suelta el mundo del carro, la conexión de PyBullet de la escena (quedaba
  abierta y, como `sim/mundo.py` dibuja en la conexión 0, le cambiaba los sensores a otro), el
  puente, el servidor y la base; idempotente. Prueba nueva (660).
- Vista "Material" y foco de los M18: la causa era el límite de la órbita
  (`maxPolarAngle = 0,495π` no dejaba bajar la cámara de la horizontal). `limitarPolar()` lo ajusta
  a la altura de la mira sin atravesar el piso; dirección elegida por barrido de rayos (desde atrás,
  50° por debajo: ~92 % de los dos sensores a la vista).
- Etiquetas 3D bajo la barra de vistas o el aviso DEMO: se desvanecen (`interfaz.js` mide esas zonas
  al acomodarse; `visor.js` las usa en `actualizarEtiquetas`).
- Streamlit: columnas principales apiladas en pantallas angostas (media queries), mapa del carro a
  todo el ancho con sus etiquetas enteras, tablas de Montaje en HTML que no necesitan desplazamiento.
  El aviso `Recording error: Container not found` venía de `st.chat_input` (no del micrófono): con un
  texto de ayuda largo el componente se reacomodaba al abrir y la librería de la onda perdía su
  recuadro; ahora el texto cabe en una línea (0 errores en 7 cargas).

## 2026-09-28 — Firmware según el diseño y valores físicos (pedido 12e y 12f)

Hallazgos de `docs/electrica.md` §8 que el firmware no cumplía, y tres valores físicos que no
coincidían entre sí.

- **Prensa y empujador nunca a la vez, en la placa** (`firmware/fijo/estacion.py`, `EXCLUYENTES`).
  Causa: `_ciclo` solo impedía repetir el MISMO servo; la regla la cumplía el orden de comandos del
  PC (un reintento o un botón de prueba la rompían). Ahora, si llega uno mientras el otro está en
  su ciclo COMPLETO (ida y vuelta), la placa lo confirma (`ack ok:true`), avisa `en_espera` y lo
  arranca cuando el otro vuelve a reposo (`arranca`). Se eligió esperar y no rechazar: el PC no
  reintenta un comando confirmado y rechazarlo dejaba una tapa sin prensar. La cortina y la parada
  segura cancelan lo que esperaba. Pruebas: los dos órdenes, cancelación con la cortina y que la tapa
  no espera.
- **Tope de PWM de los TT** (`firmware/carro/hw.py`): `firmware.carro_pwm_max: 0.70`, aplicado
  después de la corrección integral (antes podía llegar a 100 % con una rueda trabada: 8,4 V en un
  motor de 6 V, 1,53 A por canal). Con 7,4 V el carro llega a ~0,39 m/s (la línea pide 0,40): va
  ~4 % más lento, dicho en el YAML.
- **Bus I2C largo a 100 kHz** (`firmware.i2c_bus_largo_hz`); el bus corto del PCA9685 sigue a 400 kHz.
- **A4988**: la "corriente de reposo reducida" no existía (ENABLE siempre en 0). Ahora ENABLE se
  suelta tras `firmware.a4988_reposo_ms: 3000` con las dos cintas quietas (más que las pausas de
  1000/800 ms: con la línea andando nunca se sueltan) y se vuelve a dar 5 ms antes del primer paso.
  Seguro porque la cinta no tiene carga que la arrastre, el A4988 guarda su micropaso (máx. 0,17 mm
  de salto) y la cámara re-sincroniza igual.
- **Carrusel**: `carrusel_giro` decía 500 ms y el firmware tardaba 4,1 s por media vuelta (y más,
  porque el paso lo daba el bucle principal, que ya duerme 2 ms por vuelta). Ahora el medio paso lo
  da un `Timer` cada 2 ms (500 Hz, bajo los 600 Hz de arranque de la hoja de datos del 28BYJ-48;
  1 ms no deja margen con los tubos cargados) y `tiempos_ms.carrusel_giro: 4096` es ese tiempo real
  (una prueba lo ata al firmware). Los dos chequeos del carrusel de `control/tiempos.py` quedan en
  NO CABE a propósito y dicen qué se ajusta: la cinta de monedas espera al carrusel (~2,5 s al tubo
  opuesto, ~7 s una vez por lote). La lógica de control no se tocó. **Pendiente**: que el backend
  real espere de verdad (hoy no hay evento de "carrusel llegó"; la telemetría trae su posición), y
  el visor anima el carrusel con `carrusel_giro` en cola: con 4,1 s puede quedar atrás en corridas
  con muchas denominaciones distintas.
- **Rodillo Ø22** (el del modelo 3D, `crearRodilloCinta`, las dos cintas):
  `firmware.mm_por_vuelta_cinta: 69.1` (π·22; antes 40 = Ø12,7 que no existe). Casilla de monedas =
  463 micropasos, de vasos = 926 (1/4 de micropaso); ~0,8/0,9 kHz de STEP. `docs/peso.md` ya no
  avisa del desacuerdo (lo hace solo si vuelven a separarse).
- **Vaso lleno**: `vehiculo.masa_vaso_lleno_kg: 0.133` = vaso 25 + tapa 8 + 10 monedas de 10 g (la
  misma suma que `config/masas.yaml`; prueba nueva que las compara).
- **Prensa**: la tapa sella por snap-fit (~30-50 N); objetivo **60 N** (la más dura x1,2) y el
  resorte limitador no deja pasar de ahí. Antes "≥150 N", que el MG996R con la leva no sostiene a
  90° y la tapa no necesita. `config/masas.yaml: fuerza_prensa_objetivo_n`, `sim/catalogos.py`,
  CLAUDE.md §5.12; `docs/peso.md`: todos los motores ALCANZAN (prensa x2,76 a 6 V).
- Regenerados `docs/*.md` (`python -m app.documentos`), `docs/electrica.md` (`python -m sim.electrica`,
  conclusiones actualizadas) y `firmware/salida/` (`python -m firmware.preparar`, compila).
- **Una prueba del carro cambió por la masa, y es la física**: `test_tras_detenido_atascado_volver_
  muelle_lo_saca` reproduce el incidente del atasco en la boca del muelle a `y_min=-0.68`. Con el vaso
  de 0,133 kg el carro llega a esa altura MÁS derecho (rumbo −90,4° en vez de −95,5°, 13 mm más
  centrado) y la orden ya no lo atasca: llega al punto. Con 0,10 kg sigue fallando igual que antes en
  −0,66 y atascándose en −0,68/−0,70; con 0,133 kg se atasca en −0,76 y ahí la prueba entera pasa
  (atasco, `volver_muelle`, vuelve a la salida ±1 cm). Arreglo propuesto (archivo fuera del alcance de
  este pedido): `_hasta_media_reversa(carro, y_min=-0.76)` en esa prueba.

## 2026-09-28 — Simulaciones de PyBullet en ventana, videos y física vs 3D (puntos f y g)

**Hecho:**

- `sim/mundo.py` (`EscenaEstacion(conexion=...)`) y `sim/vehiculo_sim.py` (`SimCarro(conexion=...)`,
  gancho opcional `al_paso_control`): parámetro de conexión con `p.DIRECT` por defecto (pruebas,
  supervisor y demo no cambian).
- `sim/ver/`: 4 escenas en ventana GUI que reusan la planta y el carro tal cual —
  `filtro_monedas` (mixto_20; texto por estación y junto a cada pieza, tubos con su cuenta),
  `embalaje_vasos` (prueba_completa, lote 5, guion de sabotajes de la demo), `carro_pista`
  (viaje completo; cámara que sigue al carro, tecla c) y `todo_junto` (prueba_completa con el carro
  físico: ventana de PyBullet para la planta + ventana OpenCV para el mundo propio del carro,
  sincronizadas por ciclo). Tiempo real (tiempos_ms), espacio pausa, r reinicia, q sale.
  `--sin-ventana --segundos N` corre el mismo código en DIRECT.
- `python -m sim.ver.grabar`: `docs/videos/<escena>.mp4` (H.264) y `.gif` (480 px, < 5 MB), con el
  rótulo dibujado con cv2 en una banda arriba (getCameraImage no captura los textos de depuración).
- Lanzadores: `simulaciones.bat` (menú 1-5) y `simulaciones/1..4-*.bat`.
- `tests/sim/test_fisica_vs_3d.py` + `docs/fisica-vs-3d.md`: medidas de PyBullet vs visor y
  chequeos físicos (moneda cae al tubo, vaso cuelga de la pestaña en rieles de 69 mm y sin pestaña
  se cae, carro con vaso no vuelca).

**Causa y arreglo de las diferencias:** los URDF tenían piezas visuales de diseños viejos que nadie
comparaba con `sim/mundo.py`: tubos del carrusel centrados en el llenado (las monedas guardadas
quedaban fuera de sus tubos en la ventana), tolva de 50 mm de radio (visor 19), bandeja de rechazo
de vasos al costado y a 10 cm de altura, banda de monedas de 160 mm (visor 200). Corregidos en
`sim/urdf/`. **No corregidos (reportados, `xfail` estricto):** llanta de 22 mm en PyBullet vs 26 mm
en el visor (con 26 mm fallan 3 pruebas del muelle: la entrada de reversa depende de 4 mm de
llanta, riesgo para el montaje) y el vaso entregado que `sim/mundo.py` deja ~2 cm sobre los rieles.
CLAUDE.md dice pestaña de 72 mm; la configuración y el visor usan 78.

**Decisión del grupo (2026-09-28): el carrusel se queda con el 28BYJ-48 y se ACEPTA la espera.** Media
vuelta real tarda ~4,1 s; cuando una moneda va a un tubo lejano, la cinta de monedas espera al carrusel
(~2,5 s de más al tubo opuesto, ~7 s una vez por lote). No se pierde ninguna moneda, solo baja la
producción en esos casos. Los dos chequeos del carrusel de `control/tiempos.py` quedan en NO CABE a
propósito, con esa explicación.

## 2026-09-28 — Llanta TT de 26 mm en la física, muelle y vaso entregado sobre los rieles (pedido 13)

**Llanta (13a).** `vehiculo.ancho_rueda_mm: 26` en la configuración; lo leen `sim/vehiculo_sim.py`
y el visor (vía `sim/geometria.py`). El muelle (largo de boca, apertura, holgura) también pasó a la
configuración (`vehiculo.muelle_*`, `medidas_muelle()`), en vez de constantes copiadas en `visor.js`.

- **Causa real de las 3 pruebas que fallaban con 26 mm** (reproducido en DIRECT, 56 viajes: semillas
  1-44, 11 con el doble de error y uno sin error): NO era el muelle (0 reintentos, la llanta nunca
  tocó una guía) sino un **muro** en la evasión. Un cilindro plano en PyBullet apoya por uno de sus
  bordes y salta al otro (contactos medidos a 60 y 86 mm del centro, nunca a 73): la trocha efectiva
  varía ±13 mm, la odometría se corre más (`ir_a` desde el muelle: error medio 46 → 62 mm en 16
  semillas) y el carro vuelve a la línea torcido.
- **Arreglo (física, no el control):** la llanta es una banda de rodadura de 20 mm
  (`vehiculo.rodadura_rueda_mm`) con hombros de 3 mm 1,5 mm más chicos, como una goma real; sigue
  midiendo 26 mm para los choques de costado. Odometría de vuelta a 46 mm; 55 de 56 viajes sin tocar
  nada (con la llanta vieja de 22 mm, 53 de 56).
- **Muelle:** la llanta pasaba a 3,7 mm de la guía (antes 6,5). Rodillos guía 86 → 88 mm (y con
  ellos las guías, 2 mm más afuera por lado): vuelven los 7 mm entre llanta y rodillo del diseño y la
  llanta queda a ≥ 5,6 mm de la guía. La V no cambió (no hizo falta). Revisado en el visor con una
  copia del supervisor en otro puerto: sin errores y sin choque con la canaleta.
- Pruebas: quitado el `xfail` de la llanta; `test_boca_del_muelle_coincide_con_la_simulacion` lee el
  largo de boca con `medidas_muelle` (la constante dejó de existir). Las pruebas del carro no se
  tocaron (siguen las mismas semillas y tolerancias).

**Vaso entregado (13b).** `sim/mundo.py` (`geometria_canaleta`, `pose_vaso_en_canaleta`): la canaleta
se calcula de la configuración (la misma cuenta que usa ahora `sim/geometria.py` para el visor) y el
vaso queda con la boca 1,2 mm (la pestaña) sobre los rieles, inclinado 15° como en la prueba física
(la pestaña se acuesta sobre los dos rieles: medido 14,9°), con monedas y tapa movidas con él.
Colocado y no soltado: el vaso de la escena no tiene pestaña y un vaso suelto bajaría por el PTFE sin
el escape. Quitado el `xfail`; prueba nueva de la inclinación. En `sim/ver/` se oculta la placa verde
`marca_salida_entrega` del URDF (marca de la fase 2 que el vaso colgado atravesaba).

**Videos.** `todo_junto`: cámara de la planta a 0,66 m (antes 0,95) y banda oscura detrás del texto
del carro. Regrabados `embalaje_vasos` (0,3 MB mp4 / 0,5 MB gif), `carro_pista` (1,5 / 3,2 MB) y
`todo_junto` (1,9 / 2,8 MB); `filtro_monedas` no cambió. Suite completa: 740 pruebas, sin xfail.

## 2026-09-28 — Revisión lógica: 7 bugs de órdenes, serial y vasos (depurador)

Una revisión lógica encontró 7 fallos; cada uno se reprodujo antes de tocar código y quedó con una
prueba que fallaba antes y pasa ahora.

- **Asistente: pedir información daba órdenes** (`app/asistente.py`). "Dime cuántos vasos llegaron a
  la meta" → `ir_meta`; "Explícame el paro de emergencia" → `paro`; "Cuéntame cómo hace la media
  vuelta el carro" → girar 180°. Causa: `es_pregunta` solo mira el "?" o la primera palabra y Whisper
  no pone signos; el paro saltaba con solo nombrar "paro"; el candado de movimiento era solo para el
  modelo local. Arreglo: `PIDE_INFORMACION`/`es_consulta` (explica, cuéntame, dime, háblame, resume,
  muéstrame, describe, qué es, cómo funciona...) → ninguna orden con ningún proveedor; `PIDE_MOVIMIENTO`
  para reglas, modelo local y DeepSeek; `pide_paro` exige un imperativo ("haz paro", "paro ya", "para
  todo", "detén la línea" o la frase entera "¡paro!"). Batería real con 7 casos nuevos (6 trampas y un
  paro de verdad): ver `docs/pruebas-asistente.md`.
- **Puente serial perdía líneas partidas** (`app/puente_serial.py`). `readline()` con timeout 0 devuelve
  media línea; se contaba como mala y se perdía. Arreglo: buffer propio (`read(in_waiting)`, partir por
  `\n`, guardar el resto; tope de 4096 bytes sin fin de línea). Prueba con `loop://`.
- **Una orden mal formada tumbaba el supervisor** (`{"cmd":"velocidad","valor":"rapido"}`, lote "10.5",
  una lista). Arreglo en dos capas: el servidor revisa tipos y contesta 400 con el motivo
  (`servidor.motivo_orden_invalida`); el supervisor aplica cada orden con `aplicar_orden_segura`
  (ok:false registrado como `respuesta`, el bucle sigue).
- **Cualquier página podía mandar órdenes a 127.0.0.1** (`Access-Control-Allow-Origin: *` también en
  POST). Arreglo: POST y OPTIONS sin CORS y solo `Content-Type: application/json` (415 si no); las
  lecturas GET siguen con CORS para el visor portable. El visor ya manda sus POST con ese header y
  desde el mismo origen: no hubo que tocarlo.
- **Lote sin tope real**: sin corrida abierta un lote de 40 quedaba tal cual (tubo de 25 → `tubo_lleno`
  eterno) y el asistente tenía 25 escrito a mano. Ahora ambos leen `planta.capacidad_tubo`; un lote no
  entero se rechaza.
- **Modo real distinto del contrato**: con `sin_esp32` la línea seguía "corriendo" y "reanudar" sacaba
  del PARO. Ahora pausa (`_pausar_si_no_oye_al_esp32`, con plazo desde el arranque) y reanudar solo
  sale de la pausa y con la placa oyéndose; del paro se sale con Iniciar, igual que en la simulación.
- **Vaso vacío desechado quedaba VALIDA** en la tabla `vasos` (`control/embalaje.py`). Queda RECHAZADA;
  el dashboard lo muestra "vacío desechado" (por el destino `vacio` de su evento `descarga`) y el
  asistente lo cuenta aparte (`vasos_vacios_desechados`). Las cifras del visor salen de los eventos y
  no cambian.

## 2026-09-28 — Revisión del protocolo y del firmware del carro (6 hallazgos)

- **El carro que volvía de la meta con el vaso salía otra vez del muelle** (`control/vehiculo.py`).
  Sin enlace, pasado `espera_meta_sin_enlace_s`, vuelve con el vaso; entraba al muelle con la cuna ya
  en 3×ocupada, quedaba `esperando_carga` y en el mismo ciclo `cargar()` lo sacaba (vueltas meta↔muelle
  con el vaso). Arreglo: al entrar a `esperando_carga` se vacía `_historia_cuna` y la carga se acepta por
  FLANCO: la cuna tiene que verse vacía (3 lecturas) en el muelle antes de verse ocupada.
- **`Receptor.vistos` crecía sin tope y no conocía reinicios** (`control/protocolo.py`). Si el PC (o el
  carro) se reiniciaba y el ESP32 no, los ids volvían a 1 y se confirmaban SIN ejecutarse (ack ok, 0
  pasos). Arreglo: número de sesión `"s"` (`nueva_sesion()`, 1..65535 al azar) en cada comando/evento y
  en el latido; el receptor olvida los ids al ver una sesión nueva y guarda solo los últimos 64.
  `Secuencia` se reinicia con la sesión del latido del fijo o cuando `n` retrocede. El latido del PC
  ahora lleva `n` (último id) y `s`, como pide el contrato.
- **Mensajes de más de 250 B por ESP-NOW quedaban en la cola para siempre**. `respuesta_orden` de un
  `ir_a` rechazado medía 396 B. Arreglo: `Emisor.enviar(..., limite)` recorta `detalle` (con `"rec":
  true` y "...") y lo que ni así cabe no se encola (`grandes`). También `linea()` era incompatible con
  el `json.dumps` de MicroPython (no acepta `ensure_ascii`): ahora cae a `separators` solo.
- **Un paquete ESP-NOW que no es UTF-8 mataba `main.py` del carro** con las ruedas en el último PWM.
  Arreglo: `Radio.recibir` devuelve bytes y `parsear_linea` descarta la basura; el bucle del carro va en
  try/except (motores a 0, imprime y sigue) con `machine.WDT` (`firmware.carro_wdt_ms`, 2000; 0 = sin
  perro para depurar con Thonny).
- **El ESP-NOW de otro grupo contaba como latido de la estación** (`firmware/carro/logica.py`). Ahora
  solo cuenta `src == "estacion"` o `dst == "carro"`.
- **El tiempo del evento del carro pisaba el tipo** (`sim/vehiculo_sim.py`): `{"t": "evt", **e}` con
  `e["t"]` = segundos. Se renombró a `ts`.

Pruebas nuevas en `tests/control/test_protocolo.py`, `tests/control/test_vehiculo.py` y
`tests/firmware/test_firmware.py` (sesión de punta a punta con la estación emulada, tamaño de todos los
mensajes del carro, basura por radio, latido ajeno, bucle de `main.py` con una excepción).

## 2026-09-28 — El carrusel con su tiempo real: la moneda espera a que su tubo llegue (pedido 14)

**Causa (reproducida en DIRECT):** `sim/planta.py` no modelaba el carrusel: `_almacenar` guardaba la
moneda en su tubo en el mismo tick en que llegaba a E4, sin ningún giro, y `_intentar_embalar` soltaba
el lote sin llevar el tubo al agujero. El visor giraba por su cuenta (`girarCarrusel` en una cola con
`c.libre`) mientras animaba la caída sin esperarlo. Con un carrusel "sombra" de 4096 ms por media vuelta:
en `prueba_completa` 21 de 24 monedas caían con el disco girando (faltaban hasta 3,3 s) y en `mixto_20`
8 de 8; la cola del visor llegaba a ir 6,5 s atrasada.

**Arreglo, por capa:**
- `control/carrusel.py` (nuevo, puro, apto MicroPython): 6 posiciones, carga (90°) y agujero (300°),
  camino corto, duración = `carrusel_giro` × ángulo / 180°; `pedir`, `listo`, `en`, `tubo_en`, `estado`.
- `sim/planta.py`: reloj en ms (ticks × ciclo). El giro se pide cuando la visión ACEPTA; en E4 la moneda
  solo cae con su tubo quieto bajo la carga, si no espera en la descarga (`e4 espera
  motivo=carrusel_girando`, con `falta_ms`, sin alarma) y la cinta de monedas se detiene (espera
  redondeada a ciclos). El lote: tubo al agujero, re-verificación con la cámara, obturador
  (`compuerta_tubo`); la cinta de vasos no se mueve mientras. Un lote no le quita el carrusel a una
  moneda que ya espera en la descarga. Eventos `carrusel gira` (con `en_ms`, `dur_ms`, ángulos) y
  `estado()["carrusel"]`. La alarma `tubo_lleno` ya no salta por esperar al carrusel.
- `app/visor3d/visor.js`: el disco sigue los eventos `carrusel/gira` (sin cola propia, arranca desde
  donde esté), la moneda cae cuando la simulación la guarda y la pila crece al terminar la caída;
  `animarEmbalado` abre el obturador en el `en_ms` de la simulación. Frases nuevas en `interfaz.js` y
  `app/dashboard/textos.py`; el aviso grande "Tubo lleno" solo por tubo lleno.
- Firmware: `carrusel ir` acepta `lugar` (carga/agujero), evento `carrusel/llego` con `giro_ms` y
  `carrusel_mov` en la telemetría; `BackendReal.carrusel_en()` solo da el tubo por puesto tras ese aviso.
  La estación emulada (`app/puente_serial.py`) tarda lo mismo que la placa.
- `control/tiempos.py`: los dos chequeos siguen en NO CABE (decisión aceptada) y ahora dicen cuánto
  baja el ritmo: 37,5 → 27,5 elem/min (tubo vecino) o 12,2 (peor caso). `docs/logica-interna.md` §1.7.

**Resultado:** 0 monedas y 0 lotes a destiempo (revisado solo con los eventos, como el visor). La corrida
`prueba_completa` pasa de 44 a 63 ciclos (70,4 → 100,8 s; 31,5 → 22,0 elem/min); `mixto_20`, de 27 a
35. Video `filtro_monedas` regrabado (la escena ahora gasta el tiempo de cada espera), demo y portable
regenerados. Pruebas: `tests/control/test_carrusel.py`, `tests/sim/test_carrusel_planta.py`,
`tests/firmware/test_carrusel_firmware.py`; en `tests/sim/test_planta.py` el carro de reemplazo pasa
cada 2 ciclos en las dos pruebas del muelle (el primer vaso llega a la canaleta cerca del final).
- **Revisión visual (mismo día), asistente**: prometía movimientos sin mandar la orden ("se moverá a tres
  posiciones aleatorias") → `quitar_promesas` saca esas oraciones si no salió ninguna orden al carro y
  dice que no se mueve (más una regla en el prompt); "¿qué tanto se demora el carro?" → `viajes_del_carro`
  (la misma cuenta que la pestaña Carro: carga → meta → en_muelle) en `ruta.tiempos_de_viaje` y en las
  reglas; la respuesta se guarda sin markdown (`limpiar_markdown`: el visor mostraba `qwen2.5-proyecto`
  con comillas invertidas). De paso: "cuántas monedas de mil hay en el almacén" la contestan las reglas
  (el modelo chico repetía las aceptadas aunque el número del tubo iba como dato verificado) y el
  extracto de documentación de las reglas ya no usa la sección que cita la batería.
- **Batería real**: 50 casos (11 nuevos) → **50/50 con el modelo local** (mediana 4,9 s) y **50/50 con
  reglas**.

## 2026-09-28 — Revisión lógica del firmware del fijo: seguridad y canaleta (9 hallazgos, depurador)

Cada punto con una prueba que fallaba antes y pasa ahora (`tests/firmware/test_firmware.py`, contra la
estación con hardware falso; `tests/control/test_tiempos.py`; `tests/sim/test_planta.py`;
`tests/app/test_supervisor.py`).

- **El paro no quedaba enclavado** (`firmware/fijo/estacion.py`). `_parar` ponía `parada_segura`, pero
  si el latido del PC se cortaba y volvía (cable USB flojo), el tick la borraba sola. Arreglo: la parada
  guarda su **motivo** (`motivo_parada`: `sin_pc`, `paro`, `error`). Solo `sin_pc` se levanta sola al
  volver el latido; `paro` y `error` quedan enclavados hasta `estado.reanudar` (que el PC manda con
  Iniciar/Reanudar). Un motivo enclavado no se rebaja; el ack de un comando rechazado dice por qué.
- **La cortina fallaba del lado inseguro** (`firmware/comun/distancia.py`, `fijo/hw.py`,
  `estacion.py`). Con un OSError (I2C flojo) `Laser.actualizar` no medía y `ultima` quedaba congelada,
  casi siempre en None = "libre". Arreglo: `hw.leer()` manda `cortina_medidas` (contador del VL53L0X);
  si pasan más de `firmware.cortina_sin_lectura_ms` (150) sin una medición nueva, la cortina queda
  **activa** con motivo `sin_lectura` y evento `cortina_sin_lectura`.
- **La cortina no votaba**: reaccionaba a UNA lectura, aunque `control/tiempos.py` presupuesta
  `lecturas_por_decision × cortina_lectura`; con el falso positivo de la config salía una cortina falsa
  cada ~17 s. Arreglo: `planta.lecturas_por_decision` mediciones NUEVAS seguidas para activarla y otras
  tantas para despejarla (no parpadea). El presupuesto queda igual al código.
- **`firmware/fijo/main.py` sin try** dejaba cintas y servos andando si algo lanzaba una excepción.
  Arreglo: mismo patrón que el carro (try/except por vuelta → parada segura con motivo `error`, evento con
  el error, el bucle sigue) y `machine.WDT` con `firmware.fijo_wdt_ms` (2000; 0 = sin perro), que
  `firmware/preparar.py` pasa a la placa.
- **La canaleta soltaba sin condiciones** (`_soltar_vaso`; el PC en modo real tampoco revisaba). Arreglo:
  la estación guarda lo último que dijo el carro (`estado_carro`: fresco, en_muelle, cuna; las mismas
  reglas que `sim/planta.py`), lo invalida al perder el enlace y cuando el PC le manda una orden de
  movimiento al carro, y aplica `protocolo.puede_soltar_vaso`. Si no, `ack ok:false` con el motivo
  (`vaso retenido: cuna_ocupada`...) y alarma `cuna_ocupada`. Tras soltar, la cuna queda desconocida
  hasta que el carro hable (no se suelta un segundo vaso encima).
- **La parada segura no frenaba el carrusel** (lo gira un Timer de `fijo/hw.py`). Arreglo:
  `Carrusel.detener()` (objetivo = posición actual) desde `aplicar_parada_segura`, evento
  `carrusel/detenido` y el pedido en curso se descarta (no hay `llego` falso).
- **El reintento de la tapa no estaba presupuestado** (`control/tiempos.py`). Dos intentos =
  2 × (500 + 3 × 60) = 1360 ms en una pausa de 800: chequeo nuevo "Reintento de la tapa" en NO CABE,
  con la explicación de qué pasa (la cinta de vasos espera una pausa más; la de monedas sigue). La
  simulación NO se comporta así: `_estacion_tapa` hace los dos intentos en el mismo tick sin contar ese
  tiempo (queda dicho en la explicación). De paso, los textos de los chequeos con tildes y E3 (decía E5).
- **`sim/planta.py`**: (a) lo que ningún sensor registró (`sin_registro`) grababa causa NULL en
  `elementos`; ahora sale con `no_reconocida` (sección 7) y el evento conserva `motivo: sin_registro`;
  (b) `_mensaje_del_carro` ya no copia `ts` ni `s` del transporte al evento; (c) comentarios con
  estaciones viejas (E5/E7 → E3/E4); (d) el evento `presencia` lleva `diametro_real_mm` (verdad de
  terreno para la matriz de Calidad); (e) `almacen_precargado` se perdía (se emitía antes del primer
  tick y el primer `paso()` vaciaba la lista): ahora va con `eventos_arranque`, que el supervisor ya
  guarda.
- **Configuración sin uso / doble fuente**: se quitaron `tiempos_ms.esp_now_latencia` y
  `errores_sensores.camara_vasos.error_fondo` (nadie los leía; la confirmación del lote por cámara,
  `lote_no_confirmado`, no está modelada todavía) con su comentario, y una prueba exige que todo tiempo y
  error de la config lo lea alguien. La ventana de la cortina tiene una sola fuente:
  `sim/sensores_sim.ventana_cortina_mm()` (140 mm) es el alcance del cono simulado y el umbral del
  firmware (antes 150 en `firmware.cortina_umbral_mm`, que se quitó).

## 2026-09-29 — Segunda revisión lógica: asistente (a quién le habla la frase) y cifras del dashboard (depurador)

Todo reproducido primero con `asistente.atender(..., usar="reglas")` y con una copia de `datos/planta.db`.

- **Asistente, la frase le habla a otra cosa y movía el carro** (`app/asistente.py`). "sigue la línea de
  producción" daba `carro seguir_linea` (la regla de reanudar iba después y nunca se alcanzaba), y "la
  moneda avanza por la cinta", `carro avanzar 0,2 m` ("avanz" pasaba el candado `PIDE_MOVIMIENTO` sin mirar el
  sujeto). Arreglo: `pide_mover_carro()` exige nombrar al carro o empezar con el verbo (imperativo, tras el
  relleno "por favor/que/oye..."), y nunca si una moneda/pieza/cinta/vaso/la planta es el sujeto o lo que se
  mueve ("avanza la cinta"). Vale como candado para los tres proveedores. "línea de producción", "producción"
  y "planta" van a la línea: reanudar (`_REANUDA_LINEA`) o pausar.
- **"detén todo/la planta/la producción" detenían solo el carro, y "para todo"/"para la línea" no daban
  nada.** Regla acordada con el usuario: `pide_pausa_linea()` → PAUSA; PARO solo con "paro", "paro de
  emergencia" o la urgencia explícita ("para todo ya"). "para" cuenta como verbo al inicio o justo antes de
  todo/la línea/la planta/la producción, no después de "sirve", "útil"... ("gira el carro para el lado
  derecho" antes lo DETENÍA: la regla buscaba "para el" en cualquier parte).
- **"que + subjuntivo" se tomaba como pregunta** ("que avance el carro 30 cm", "que el carro vaya a la meta",
  "que vuelva al muelle" no daban orden). `es_pedido_con_que()`: sin tilde y seguido de un subjuntivo de
  la lista es un pedido; "qué" con tilde o seguido de es/hay/tan... sigue siendo pregunta. Se agregaron las
  formas en subjuntivo a las reglas y al candado ("avance" se escribe con c: el candado la quitaba).
- **`quitar_promesas` borraba la descripción del recorrido automático** ("se moverá solo a la meta cuando
  lo carguen") y pegaba "no se mueve". Ahora la primera persona ("lo muevo", "avanzaré") siempre se quita y
  la impersonal ("se moverá") solo si no trae marca de automático/condición (solo, cuando, cada vez...).
- **Evaluador** (`app/evaluar_asistente.py`): cada proveedor sacaba su PROPIA copia de la base con el
  supervisor escribiendo, así que local y reglas se medían contra datos distintos ("¿qué tanto se demora el
  carro?" falló en local porque su copia aún no tenía viajes). Ahora `copiar_base()` una sola vez para todos.
  `_alguna_cifra` sin ninguna cifra en la base fallaba siempre: ahora acepta "no tengo ese dato / no ha hecho
  viajes". 10 casos nuevos (trampas, pausa, pedidos con "que"): **60/60 local (mediana 5,7 s) y 60/60 reglas**.
- **Dashboard, monedas "del turno anterior" inventadas** (`app/dashboard/datos.py`,
  `monedas_del_turno_anterior`): sin el evento `almacen_precargado` se deducía por conservación, pero
  `elementos` solo trae las aceptadas FINALIZADAS y la que iba de la cámara a la descarga (o esperaba en E4 al
  carrusel) ya contaba del otro lado: en 49 ticks de `prueba_completa` salían monedas "de antes" en una
  corrida que arrancó vacía. La planta ya guarda `almacen_precargado` (con `eventos_arranque`): es la única
  fuente, y si no está, 0.
- **Matriz de Calidad** (`matriz_aciertos`, `categoria_real`): usa `diametro_real_mm` del evento `presencia`
  (verdad de terreno, contra la tolerancia de coherencia) en vez del diámetro que midió la cámara (lo que
  se evalúa); y una pieza que el infrarrojo no vio (`ocupada: false`) y recuperó E2 (`presencia_recuperada`)
  toma su `tipo_real` de ese primer evento (antes: "Pieza sin identificar").
- Pruebas nuevas en `tests/app/test_asistente.py` (22 frases de a quién le habla, "qué" interrogativo,
  candado con DeepSeek, recorrido automático) y `tests/app/test_dashboard.py` (turno anterior sin evento = 0,
  matriz con diámetro real y pieza recuperada); fallaban con el código anterior. Dashboard revisado con
  capturas (Resumen, Monedas y vasos, Calidad) en un puerto aparte: la conservación cuadra (24 + 23 = 30 + 17).

## 2026-09-29 — Segunda revisión lógica: firmware, puente y supervisor (10 hallazgos, depurador)

Cada punto se reprodujo con la estación emulada / el `main.py` real con módulos falsos o el
supervisor en modo real; cada prueba nueva FALLABA antes del arreglo
(`tests/firmware/test_revision_firmware_0929.py`, final de `tests/app/test_supervisor.py`).

1. **Orden rechazada por el carro lo "sacaba" del muelle** (`firmware/fijo/estacion.py`). El fijo ponía
   `en_muelle=False` al reenviar; si el carro la rechazaba (solo `respuesta_orden ok:false`) nunca volvía a
   decir `en_muelle` y todo `canaleta.soltar` daba `no_esta_en_muelle`. Ahora se guarda el valor anterior y,
   al llegar el rechazo, se restaura (salvo que el carro haya dicho algo más nuevo). Igual que la sim.
2. **El WDT se armaba al arrancar `main.py`** (fijo y carro): mpremote (`firmware.subir`) interrumpe
   `main.py` y el perro reiniciaba la placa a mitad de la copia (en el ESP32 no se desarma). Ahora el fijo
   lo arma con el PRIMER latido del PC (`Estacion.pc_latidos`) y el carro con el primer mensaje de su
   estación (`latido.ultimo_oido`). Nota: el carro conviene subirlo con la estación apagada.
3. **Excepción a mitad de un comando = ack perdido y reenvío con "ok" falso.** Ahora `try` alrededor de
   la ejecución: ack `ok:false` con el error, el id se des-marca (`protocolo.Receptor.olvidar`) y la
   excepción sigue hacia `main.py` (parada segura "error"). También se des-marca un comando RECHAZADO (no
   ejecutado): si su ack se pierde, el reenvío se vuelve a evaluar en vez de recibir "ok:true".
4. **Error repetido = ~500 eventos/s** al USB y a SQLite. `protocolo.LimiteAvisos`: la primera vez y
   después uno por `firmware.aviso_error_cada_ms` (1 s) con `repetidos`; la parada segura sigue en cada
   vuelta. Igual en el carro (los tracebacks por `print`).
5. **Parada por `error`/`paro` sin salida directa** (`app/supervisor.py`): con la línea CORRIENDO,
   "reanudar" ahora saca a la placa de una parada `error`/`paro`/`pausa`; la telemetría publica
   `motivo_parada`, el resumen del dashboard lo explica (`textos.MOTIVO_PARADA_TXT`, frase del evento
   `parada_segura` y de `carro_sin_respuesta`) y el visor muestra el aviso (`interfaz.js`).
6. **La pausa por `sin_esp32` no paraba la placa**: al volver el cable se levantaba sola ("sin_pc")
   con el PC en PAUSADA. Motivo nuevo **`pausa`** (enclavado; prioridad sin_pc < pausa < paro < error):
   Pausar y `_pausar_si_no_oye_al_esp32` mandan `estado.parar motivo:pausa`, y se repite al volver a oír
   la placa (`esp32_ok`) con la línea en pausa o paro. En pausa/paro no pasan comandos `hardware` salvo
   `"prueba": true`, ni órdenes al carro salvo `detener` (como en la sim).
7. **Carrusel vs obturador** (`BLOQUEOS`): el obturador espera a que el disco pare y el disco espera a
   que el obturador cierre (ack ok + `en_espera`, arranca solo; mismo patrón que `EXCLUYENTES`).
   `carrusel.referencia` con el obturador abierto se rechaza. La cortina solo cancela esperas de su zona.
8. **`llego` viejo** (`control/hal/backend_real.py`): el evento lleva `pedido` (id del comando) y
   `carrusel_en` lo compara con el id de su último pedido.
9. **Orden al carro perdida sin aviso**: el fijo la reenvía cada `carro_reintento_ms` hasta la
   `respuesta_orden` (mismo id: el carro no la repite), como mucho `protocolo.carro_orden_intentos` (4);
   si no llega, evento `carro_sin_respuesta`.
10. `CLAUDE.md` §10.1: el ejemplo del carrusel decía `"tubo":500`; son índices 0-5. §15: WDT armado tarde
    y límite de avisos.

Pruebas: `python -m firmware.preparar` compila las dos placas; `pytest tests/firmware tests/control
tests/app/test_supervisor.py tests/sim` → 647 pasan. `sim/planta.py` no se tocó.

## 2026-09-29 — La caída ocupa el carrusel: el giro siguiente espera a que la moneda llegue (pedido 14, depurador)

**Qué se vio (revisión visual en vivo, `?auditar` cuadro a cuadro):** de 15 llegadas, 8 caían a un tubo
15-37 mm fuera de la boca con el disco girando 22-40° en el segundo previo; la pila de $500 crecía con el
disco quieto en el tubo $200, y un lote de $500 caía a 9 mm del agujero con 15° de giro.

**Causa:** en el MISMO instante la simulación guardaba la moneda que esperaba en la descarga
(`e4/almacen en_ms=0`, al empezar el ciclo) y pedía el giro hacia el tubo de la siguiente
(`carrusel/gira en_ms=0`, `_almacenar` → `_mover_carrusel(t_ms)`): el disco se iba mientras la moneda
todavía bajaba por el embudo y el canal (demo grabada: ticks 6, 7, 9, 18, 26-28, 32-34). En el visor,
`faltaCarrusel()` solo protegía de giros ya pedidos, la caída duraba 0,85 s con horario fijo y la pila de
un lote bajaba en la siguiente consulta (en la demo, hasta 1,6 s tarde, con el disco ya volviendo).

**Arreglo, por capa:**
- `config/parametros.yaml`: `tiempos_ms.caida_moneda_tubo: 400` (PROVISIONAL): 180 mm de la cinta al
  fondo de un tubo vacío; caída libre 0,19 s, por tramos (embudo, compuerta, canal a ~72° con roce 0,3,
  fondo) 0,27 s, + ~0,1 s de rebote → 400 ms. Se mide con video a 240 fps (comentario en el yaml).
- `control/carrusel.py`: `ocupar(hasta_ms)`; `pedir` arranca en `max(t, fin del giro anterior, ocupado)`.
- `sim/planta.py`: `_almacenar` ocupa el carrusel `caida_moneda_tubo`; `_atender_carrusel` lo ocupa con el
  obturador abierto (`compuerta_tubo`). El giro a la siguiente sale ahora con `en_ms = 400`.
- `control/tiempos.py`: chequeo nuevo "la moneda termina de caer antes del giro a la siguiente" (400 ms
  en los 820 ms de la visión: en régimen no cuesta nada; solo cuando la moneda esperó al carrusel).
- `firmware/fijo/estacion.py`: la placa también lo cumple sola: con el desvío hacia el almacén, un avance
  de la cinta de monedas ocupa el carrusel `avance + caida_moneda_tubo`; un `carrusel ir` en ese lapso
  espera (ack ok + `en_espera` con `espera_a: moneda`) y arranca después (`arranca`). El backend real
  no cambia: sigue esperando `llego`, que ahora llega después de la caída.
- `app/visor3d/visor.js`: el orden es por ESTADO, no por reloj (con pocos cuadros por segundo los tramos
  encadenados se estiraban y el horario fijo se adelantaba). Cada moneda al almacén y cada lote se anotan
  "en el aire" con el giro que los deja en su lugar; la moneda no deja la cinta y el obturador no abre
  hasta que ESE giro terminó; un giro pedido después no arranca mientras quede algo anterior cayendo
  (`animar(..., {espera})`, que al soltarse arranca desde 0) ni antes que el giro anterior. La caída dura
  `caida_moneda_tubo` (el último 0,1 s asentada, con el disco quieto). La pila crece solo cuando aterriza
  una moneda de ESE tubo (o de una vez al arrancar / con el disco quieto si la cuenta sube sin caída), y
  la de un lote baja justo al abrir el obturador.

**Pruebas nuevas** (fallaban antes): `tests/sim/test_carrusel_planta.py` (ningún giro arranca durante la
caída de una moneda ni con el obturador abierto, en `prueba_completa` lote 5 y 10 y `mixto_20`; el caso
exacto de la demo; `caida_moneda_tubo` ≥ caída libre y < pausa) y `tests/firmware/test_carrusel_firmware.py`
(el `carrusel ir` espera a la moneda con el desvío al almacén, y no espera con el desvío al rechazo).

**Medición visual** (copia del supervisor en 8797, Chrome sin ventana a ~3 cuadros/s, lote 5): antes 8 de
15 llegadas a 15-37 mm y 22-40°; después, en vivo 22 monedas y 4 lotes, y en la demo 22 monedas y 4
lotes, todos a 0 mm de la boca/agujero y 0° de giro en el segundo previo, sin errores de consola.

**Producción:** `prueba_completa` (lote 10) 63 → 71 ciclos (100,8 → 113,6 s; 22,0 → 19,5 elem/min);
`mixto_20` igual (35). Demo, portable y video `filtro_monedas` regenerados.

**Decisión del grupo (2026-09-29): pausa de la cinta de vasos 1400 ms (antes 800).** Si la cámara no ve la
primera tapa se suelta otra: dos intentos = 2 × (500 + 3 × 60) = 1360 ms, que no cabían en 800. El grupo
prefirió alargar la pausa en vez de hacer esperar a la cinta de vasos: los lotes llegan mucho más lento que
un ciclo de vasos, así que no frena al almacén. El chequeo "Reintento de la tapa" pasa a OK (1360 de 1400).

## 2026-10-02 — Orden de los contextos: la especificación sale de CLAUDE.md (plan PLAN-ORDEN-CONTEXTOS)

**Hecho:** `CLAUDE.md` pasó de 1062 a 77 líneas. La especificación numerada (secciones 1-16, 18 y 19, sin
cambiar texto ni números) vive ahora en `docs/especificacion.md`; `CLAUDE.md` queda con las instrucciones
para Claude Code, una tabla de "dónde leer según lo que se toque" y la sección 17 (reglas del agente; la de
commits pasa a "no hacer commit ni push sin que el usuario lo pida", decisión del usuario).
`CONTEXTO-SESION.md` (379 → 131 líneas) queda en orden 0-5 con las reglas permanentes juntas en la sección 0;
los pedidos cerrados 2-17 están en `docs/historial-pedidos.md`, textuales.

**Referencias:** 80 citas "CLAUDE.md, sección N" en 55 archivos (código, config, escenarios, URDF, pruebas,
docs, README) pasan a `docs/especificacion.md`; las de la regla/sección 17 siguen en `CLAUDE.md`. Esta
bitácora no se tocó (es historial: sus citas viejas se refieren al `CLAUDE.md` de ese momento, con la misma
numeración). `app/asistente.py` indexa `docs/especificacion.md` en lugar de `CLAUDE.md`
(`tests/app/test_asistente.py` ajustado). Regenerados `paso-a-paso.md` y `visor-portable.html`.

**Pruebas:** suite completa 930/930 (3:52). Batería real del asistente (`app.evaluar_asistente`): primera
corrida ollama 59/60 (falló "¿cuál fue la última moneda que revisó la cámara?": el modelo chico no dio las
cifras, es un dato en vivo de la base, no de la documentación) y reglas 60/60; segunda corrida 60/60 y
60/60 (mediana 4,9 s). Al abrir una sesión en el proyecto final se cargan 9,5 k tokens de contexto en vez
de ~25 k. Detalle de qué salió de dónde: `D:\cosas uni\Micros\historial\correspondencia-contextos.md`
(fuera del repo).

## 2026-10-05 — Arreglos para quien lo prueba por primera vez + app de la práctica (plan PLAN-APPS-PRACTICAS, P9)

**Instalar antes de ver.** `visor.bat` sin `entorno\` abría la demo grabada sin decir nada: ahora avisa en su
ventana ("no está instalado: se abre la DEMO GRABADA; para el modo en vivo, instalar.bat") y el README dice
arriba, en "Cómo verlo", que primero hay que instalar, qué instala y cuánto ocupa. `instalar.bat` pregunta:
1, mínima (`requirements-minimo.txt`, los 13 paquetes de `probar.json`: visor en vivo, dashboard, escenas,
asistente escrito y pruebas; medido: 3 min 21 s y 0,7 GB con la caché de pip llena) o 2, completa (el lock, el
firmware, Ollama, Whisper y el chequeo, como antes). Sin preguntar: `instalar.bat minima|completa`. Con la
mínima (entorno temporal) pasan todas menos 2 que se omiten (las que compilan el firmware con `mpy-cross`).

**Puerto 8765 ocupado.** En este PC lo tiene otro programa (`node ...\panel\server.js`, y Docker en IPv6): el
supervisor seguía sin visor y la pestaña en vivo nunca aparecía. Nuevo `app/puertos.py`: el puerto sale de
`--puerto-visor`, `PLANTA_PUERTO_VISOR` o la configuración; si lo tiene OTRO programa se usa el siguiente libre
(hasta +20) y se dice; si lo tiene una corrida de este proyecto (se reconoce por `/api/geometria`) se reutiliza.
`app.lanzar` pasa el puerto real al supervisor y al dashboard (variable de entorno), lo anota en
`datos/puertos.json` (ignorado por git), abre el navegador en ese puerto y hace lo mismo con el 8501 del
dashboard. El visor portable (file://) busca la simulación en 8765-8785 y solo acepta un JSON de estado (el
404 del otro programa no lo engaña). `app.chequeo` ya no marca falla: avisa qué puerto se usará.
Probado de verdad aquí: el visor quedó en 8766, el portable pasó solo a `http://127.0.0.1:8766/` y el
dashboard mostró la línea trabajando.

**Cifras unificadas** con su fuente: asistente 60 de 60 (local, mediana 4,9 s) y 60 de 60 (reglas), de
`docs/pruebas-asistente.md` (2026-10-02); el README decía 50/50 y "39 preguntas". Pruebas: 936, el número real de
`pytest -q` hoy con el entorno del proyecto (README, `logica-interna.md`, lock, `probar.json`); antes decían
"más de 850", "590+" y 928. Suite completa: 936 passed.

**App de la práctica** (`app-practica/`, declarada en `probar.json` con `"app"`): portada con video, checklist
de lo que pide el enunciado, el recorrido interactivo de una pieza por las 4 estaciones (5 piezas, cada una con
su causa de `control/reglas.py`), instalación y puertos, botones para el visor en vivo + dashboard (con los
enlaces del puerto real que dice `app.lanzar`), las 4 escenas de PyBullet, el asistente (nuevo
`app/charla.py`: reglas sin clave sobre una COPIA de la base; las órdenes no se mandan), el visor portable
embebido, resultados (videos, pytest) y el estado del proyecto tal cual está en el README.
