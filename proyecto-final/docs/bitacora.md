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

