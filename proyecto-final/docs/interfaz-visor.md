# Interfaz del visor 3D: inventario de funciones

Lista de TODO lo que hace la interfaz del visor (`app/visor3d/`), sacada leyendo el código antes
de rehacerla (2026-09-28). Es la lista de verificación: cada punto se revisó en el visor rehecho
(capturas con Chrome sin ventana, en vivo, demo y portable). La escena 3D (piezas, render,
cámara, animaciones) no es parte de la interfaz: vive en `visor.js` y `piezas/`.

Dónde está cada cosa después de rehacerla:

- `app/visor3d/index.html` — solo el esqueleto (barra, vistas, panel, avisos, bitácora, leyenda).
- `app/visor3d/estilo.css` — el sistema de diseño (variables, componentes, responsive).
- `app/visor3d/interfaz.js` — todo el comportamiento de la interfaz (pestañas, controles, avisos,
  internet, bitácora, leyenda de cables, parámetros de URL, vigía del portable).
- `app/visor3d/visor.js` — la escena; le pasa a la interfaz lo que necesita (`crearInterfaz(ctx)`).

## Barra superior

- [x] Título de la planta.
- [x] Chip de estado de la línea (`#chipEstado`): corriendo (verde), pausada (ámbar), paro/error
  (rojo), terminada (azul); en la demo SIEMPRE ámbar ("demo grabada · …", nunca verde); en el
  portable: "demo grabada · esperando la simulación de este PC"; "sin conexión con el supervisor"
  en rojo tras 4 fallos seguidos; "simulación encontrada · abriendo en vivo…" al pasar a vivo.
- [x] Chip del tick (`#chipTick`).
- [x] Chip de internet (`#chipRed`) al lado de los ticks: "revisando…", "con internet",
  "SIN INTERNET" (rojo). Lógica de `revisarInternet`: en vivo decide la simulación
  (`GET /api/internet`, el mismo chequeo del asistente y del Streamlit); si no responde (demo o
  supervisor viejo), prueba el navegador (`navigator.onLine` + api.deepseek.com o
  google.com/generate_204, `no-cors`, 8 s) y solo dice "sin internet" tras 2 fallos seguidos
  (reintenta a los 4 s). Primera revisión a los 1,5 s (la escena se arma), luego cada 20 s y con
  los eventos `online`/`offline` del navegador. Tooltip: sin internet solo cambia el asistente.
- [x] Sin internet también cambia la nube 3D del asistente (gris, línea roja, etiqueta "sin
  internet"): la interfaz avisa a la escena (`ctx.alCambiarInternet`).
- [x] Botón **Cables** (muestra/oculta todo el cableado 3D y su leyenda; se recuerda en
  `localStorage.verCables`; `?cables` en la URL lo abre).
- [x] Botón **Panel** (muestra/oculta el panel lateral).

## Vistas y cámara

- [x] Botones de vista `[data-vista]`: Todo, Planta · Monedas, Material, Almacén · Vasos, Tapa y
  prensa, Canaleta · Carro, Pista · Caja de control · Asistente. El activo queda marcado.
- [x] Vuelo suave de la cámara a cada vista (0,9 s).
- [x] Vista Carro: la cámara sigue al carro mientras avanza, hasta que el usuario mueve la vista.
- [x] Con el panel abierto, a CUALQUIER ancho, TODA toma (vistas, enfocar sensor, encuadrar
  componente, paso a paso) se corre en el plano de la pantalla (de lado y de alto) para que lo
  enfocado quede en el centro de la parte libre que mide la interfaz (`zonaLibre`: debajo de las
  vistas y a la derecha del panel; en pantalla angosta, entre las vistas y la hoja de abajo), y se
  aleja según la dimensión más recortada (de lado hasta ×1,4; con la hoja de abajo hasta ×1,9).
  Antes solo se corría de lado con el panel lateral: a 900 px la hoja tapaba el carro y las
  estaciones (revisión visual, 2026-09-28). La vista Asistente de lado no se aleja (la laptop está
  detrás de la cinta y la taparía); con la hoja de abajo se aleja hasta ×1,45 para que la
  pantalla quepa. Al enfocar un sensor o componente se suelta el botón de vista marcado.
- [x] Tomas revisadas (2026-09-28): Monedas desde la esquina de la carga, 40° desde arriba (de
  frente la pantalla del portátil quedaba justo detrás de la cinta); Material desde atrás y
  abajo, ~24° bajo la horizontal y más lejos (buscada por raycast: los dos M18 enteros a
  cualquier distancia de 0,28 a 0,52 m; antes la cámara quedaba metida entre las vigas).
- [x] Etiquetas 3D sin encimarse: en cada cuadro se proyectan a la pantalla y se reparten por
  prioridad (la del sensor resaltado, después la más cercana al foco de la vista; las estaciones
  E1..E4 y las de la cinta de vasos con ventaja); si una choca con otra ya puesta o con la
  interfaz (barras, panel, avisos, bitácora, leyenda) se corre media etiqueta arriba o abajo, y si
  no cabe se oculta. Se ocultan también las que quedan detrás de una pieza sólida (rayo cámara →
  etiqueta, pocos por cuadro), las muy lejos del foco (de lado o detrás de lo enfocado; META y la
  nube se quedan) y, cerca del foco, se leen enteras aunque su alcance las desvanecía (Caja de
  control). Aparecen y desaparecen con un fundido corto.
- [x] Clic en la escena: sobre la laptop/nube del asistente → vista Asistente; sobre un sensor →
  lo selecciona (abre el panel en Sensores, lo resalta y lo encuadra). Gana lo más cercano (antes
  la laptop ganaba aunque estuviera detrás del sensor: en la vista Monedas no se podía elegir un
  sensor de la cinta).
- [x] `?vista=vision` y el paso 3 (zona `vision`) apuntaban a la estación 5 de la cinta, que ya no
  existe desde el filtro total (4 estaciones) y daban error: ahora apuntan a E3.
- [x] Ayuda de ratón (arrastrar: girar · rueda: zoom · clic derecho: mover · clic en un sensor).
- [x] Pantalla del portátil (vista Asistente): la pregunta y la respuesta se dibujan SIN los
  símbolos de markdown (`sinMarkdown`: comillas invertidas, negritas, títulos, listas, enlaces);
  antes se veían sueltos (`` `qwen2.5-proyecto` ``).

## Panel lateral (pestañas)

- [x] **En vivo**: escenario y cuántas quedan por cargar; monedas y valor en vasos; guardado en
  tubos por denominación (lote de N) y su valor; rechazos por causa; errores de sensor simulados
  (falsos rechazos, falsas aceptaciones, vaso equivocado) o "sensores perfectos"; vasos
  entregados/rechazados/vacíos desechados; canaleta (N de capacidad, vaso esperando); estado del
  carro (fase, estado, vaso que lleva) o "sin carro simulado"; radio del carro (con/sin enlace,
  mensajes guardados, cuna según el carro); LED en vivo de cada sensor de la planta (verde activo,
  rojo en alarma). Se repinta como mucho una vez por segundo.
- [x] **Pruebas** (NUEVA: todos los controles de prueba en UN lugar, antes mezclados con los datos
  de En vivo), en este orden:
  - [x] Línea: Iniciar (corrida nueva `prueba_completa`), Pausa, Seguir, Paro de emergencia.
  - [x] Probar un filtro: lista de `estado.pruebas_filtro` (estación · nombre) + botón
    (`iniciar` con ese escenario).
  - [x] Colocar una pieza: lista de `estado.piezas` + botón (`colocar`: entra en la próxima carga).
  - [x] Sabotajes a los vasos: retirar, cambiar por figura, cambiar por vaso igual, vaso con algo.
  - [x] Manos en la línea: en la carga, sobre el llenado, en tapa/prensa (el botón cambia a
    "Quitar la mano" mientras está), saca un vaso.
  - [x] Carro/radio: cortar/reconectar la radio (el texto cambia según `carro.radio.conectada`).
  - [x] Fin de turno: embalar lo guardado.
  - [x] Cada botón se habilita solo cuando puede hacer algo; si no, dice por qué al pasar el
    ratón (línea no corre, falta vaso en verificación/llenado o tapa/prensa, ya hay una mano,
    tubos vacíos, sin carro simulado, corrida sin andar, simulación sin pruebas de filtro).
    Pausa/Seguir/Paro según el estado de la línea.
  - [x] Las listas se llenan una vez con lo que manda el supervisor (no se cierran solas mientras
    se usan: los controles se arman una sola vez).
- [x] Respuesta del supervisor a cada orden (`estado.ultima_orden`, ✔ verde / ✖ ámbar con el
  detalle), 7 s; ahora al pie del panel, visible desde cualquier pestaña (también las órdenes
  del Streamlit/asistente). La que ya estaba al abrir el visor no se muestra (no es noticia).
- [x] **Paso a paso**: los puntos de la secuencia con su estado de revisión (aprobado, cambiar,
  simulado, pendiente, preaprobado, pausa, efecto); al elegir uno: cámara a su zona, sus sensores
  resaltados, detalle (qué pasa, sensores, entra, decide, sale, mensaje, cómo está hoy,
  replicación, preguntas, nota de revisión) y botones ← anterior / siguiente →.
- [x] **Sensores**: agrupados por subsistema, LED en vivo; al elegir uno: se resalta y se
  encuadra, ficha completa (dónde, modelo, qué lo activa, recibe, entrega, lectura ahora, mensaje
  al PC, cómo se simula, rango, tiempo de respuesta, error típico, mitigación, conexión) y
  "Ver la prueba de este sensor" (una o varias órdenes que hacen trabajar SOLO a ese sensor, la
  cámara se queda mirándolo) con la respuesta del supervisor a esa prueba.
- [x] **Componentes**: lista de materiales (total de piezas, sensores, servos en el PCA9685),
  leyenda de etiquetas (simulado / efecto simulado / solo visual, 3D, N hilos —"1 hilo" en singular—, sin 3D); AHORA
  agrupados por subsistema (línea de monedas, almacén, línea de vasos, canaleta y muelle, carro y
  pista, caja de control y PC) con sensores y componentes juntos; clic en un componente → se
  resalta (pulso ámbar) y se encuadra, detalle (modelo, para qué sirve, estado en la simulación,
  conexión pin a pin); clic otra vez lo suelta; clic en un sensor → se resalta y se encuadra, con
  enlace a su ficha en Sensores. Cada subsistema tiene "ver zona" (lleva la cámara a su vista).

## Avisos

- [x] Aviso grande **DEMO GRABADA** (ámbar) — texto distinto en el portable ("cuando la
  simulación de este PC arranque, esta pestaña pasa sola a en vivo").
- [x] Aviso grande **SIN CONEXIÓN CON LA SIMULACIÓN** (rojo) tras 4 fallos; se quita al volver.
- [x] A los 10 s los avisos grandes quedan en una sola línea (no tapan la pantalla de la laptop).
- [x] Centrados sobre la parte libre de la escena (a la derecha del panel si está abierto), debajo
  de la barra; se recolocan al cambiar el tamaño de la ventana o abrir/cerrar el panel.
- [x] Avisos de la línea (arriba a la derecha): cortina activa (rojo), tubo lleno / moneda en
  espera (ámbar), faltan vasos (ámbar). Van debajo del aviso grande si lo hay (antes se encimaban).
  Desde 2026-09-28 cada uno es UNA línea (título corto, p. ej. "Cortina activa · prensa
  detenida") y el detalle sale al pasar el ratón (y en la bitácora): el globo completo tapaba el
  cartel META en la vista Todo. En el tubo lleno decía "espera en E7" (quedaban 4 estaciones):
  ahora "en la descarga (E4)".

## Bitácora de eventos

- [x] Últimos 12 eventos de la simulación, el más nuevo arriba, con su fuente; alarmas en rojo;
  texto de cada evento (`describirEvento`, ~40 tipos). "sin eventos todavía" si no hay. Se borra
  al empezar una corrida nueva. AHORA se puede plegar (se recuerda).

## Leyenda de cables

- [x] Solo con los cables a la vista: total de cables, hilos y metros de campo (+20 %), por tipo
  (color, cantidad, largo de cada cable) y "pin a pin" (cada hilo con su color, de → a y función).
- [x] A la derecha, debajo de las vistas y de los avisos de la línea, sin bajar más allá de la
  bitácora (o de la hoja del panel en pantalla angosta); arranca PLEGADA en una línea con los
  totales y el botón Abrir/Plegar (se recuerda en `localStorage.leyendaPlegada`). Antes se abría a
  la izquierda, en medio de la escena, y tapaba la planta en la vista Todo (2026-09-28).

## Modo demo y portable

- [x] `?demo`, o abierto como archivo (`file://`), o sin supervisor que responda
  `/api/geometria`: reproduce la corrida grabada (`demo/*.json` o embebida en
  `window.__DEMO`), a un tick por ciclo de la cinta.
- [x] En la demo todos los controles quedan desactivados (con aviso "abrir visor.bat") y no se
  manda ninguna orden; tampoco los botones de "Ver la prueba de este sensor".
- [x] Portable (`file://`): si la simulación de este PC ya corre, va directo a en vivo; si no,
  pregunta cada 3 s (`vigilarSimulacion`, 1,5 s de espera) y pasa sola cuando responde (conserva
  los parámetros de la URL).

## Parámetros de URL

- [x] `?demo`, `?cables`, `?panel=0` (panel cerrado), `?vista=<nombre>` (incluye `carga` y
  `vision`, que no tienen botón), `?paso=<n>`, `?sensor=<id>`, `?componente=<id>`,
  `?cam=x,y,z&mira=x,y,z` (toma exacta, en coordenadas de la simulación), `?auditar`
  (`window.__visor` con la escena para scripts de revisión).

## Pantalla angosta (< 900 px)

- [x] El panel pasa a una hoja abajo (45 % de la altura, todo el ancho); se ocultan la bitácora y
  la ayuda; las vistas se desplazan de lado en vez de amontonarse.

## Verificación (2026-09-28)

Capturas con Chrome sin ventana (`.claude/herramientas/captura-chrome.mjs` y
`capturar-vistas.mjs`), sin errores de consola: en vivo (cada pestaña, con un elemento elegido),
las 12 vistas con el panel abierto, respuesta del supervisor al pie del panel y en "Ver la prueba
de este sensor" (orden rechazada: la línea estaba terminada, no se cambió la corrida), clic en un
sensor de la escena, cables con su leyenda y el panel cerrado, `?componente=`, `?sensor=` +
`?cables` a 800 px, `?paso=12&panel=0`, demo (`?demo`, controles desactivados), demo sin red (chip
SIN INTERNET), sin conexión con el supervisor (4 fallos: chip rojo y aviso grande), portable como
`file://` con la simulación corriendo (pasa solo a `http://127.0.0.1:8765/` en ~5 s) y una copia
apuntando a un puerto muerto (se queda en la demo, "esperando la simulación de este PC", botones
desactivados).
