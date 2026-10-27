# Contexto de sesión — LEER ANTES DE TOCAR NADA

Este archivo existe para que una sesión nueva sepa en qué va el proyecto sin gastar miles de
tokens buscando, y sobre todo **qué NO hacer**. Se actualiza al final de cada sesión.

## 0. Pedido EN CURSO (se escribe AL EMPEZAR cada sesión, antes de tocar código)

Por qué existe: dos veces se cerró una sesión a la fuerza a mitad de trabajo y se perdió el
último mensaje del usuario. Regla: al empezar, copiar aquí el pedido textual y la lista de
puntos; al terminar cada punto, marcarlo. Si se pierde un mensaje, está completo en el
transcript de Claude Code: `~/.claude/projects/D--cosas-uni*/<sesion>.jsonl` (la carpeta depende de dónde se
abrió la sesión; la del pedido del 2026-10-26 está en `D--cosas-uni`)
(líneas con `"type":"user"`; el más reciente por fecha de modificación).

### Pedido EN CURSO del 2026-10-26 — orden de carpetas, nombres y código de todo el proyecto

Textual del usuario:
> "haga un orden tanto de código como de nombres en todas las carpetas de el proyecto, revisando que ninguna ruta se rompa al cambiar el nombre y la ubicación, hay demasiadas carpetas con demasiadas cosas, deje los .md de el general y el .md de cada carpeta para que claude también sepa de forma ordenada y organizar de forma profesional tanto los archivos como el código, deje el paso a paso por si se corta a mitad de la tarea, después los borra"

Alcance tomado: `proyecto-final/` (no Sensores, Proteus ni Word). Puntos:
- [x] 1. Mapa de qué hay y qué depende de cada ruta (imports, rutas en código, .bat, pruebas, enlaces de docs y de
  GitHub, visor, portable, firmware, CLAUDE.md y reglas de afuera).
- [x] 2. Plan de orden (carpetas, nombres, código) escrito en `ORDEN-PASO-A-PASO.md`; aprobado con: código "Todo, incluso
  asistente.py", "README + CLAUDE.md con reglas", "Borrarlos", "Commit local por tanda"; mostrárselo ANTES de mover nada
  (regla del usuario: "primero digame antes de hacer cualquier cambio").
- [x] 3. Mover y renombrar por tandas, arreglando cada ruta; pruebas después de cada tanda.
  HECHO (2026-10-26): tandas A, B y C (commits locales 04130e1 y 4def362, sin push).
- [x] 4. Ordenar el código sin cambiar lo que hace.
  HECHO (2026-10-26): tanda D (commit local 37347d9, sin push); 951 pruebas.
- [x] 5. CLAUDE.md general y uno por carpeta.
  HECHO (2026-10-26): tanda E. README.md en cada carpeta (app/, app/asistente/, app/dashboard/, app/visor3d/,
  app-practica/, sim/, control/, config/, tests/, simulaciones/); CLAUDE.md general al día y CLAUDE.md en maqueta_impresa/
  y chasis_impreso/; pedidos cerrados a docs/historial-pedidos.md.
- [ ] 6. Verificar todo (pytest, revisor de la maqueta, visor, portable, enlaces) y borrar `ORDEN-PASO-A-PASO.md`.

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
Hoy son 4,22 s (`carrusel_giro: 4223`: la rampa del 2026-10-25 suma 127 ms por giro); la decisión sigue igual.

- (2026-09-28, pedido 15) "pase varias revisiones exhaustivas a todo el proyecto, tanto visual como
  lógico, siempre es importante". (Regla permanente: después de cada cambio grande, revisión visual + lógica.)
- LECCIÓN (ronda 2 visual del carrusel, 2026-09-28): la verificación del timing tiene que ser VISUAL/cuadro a cuadro,
  no solo con eventos.

Pedidos cerrados (del 2026-09-27 al 2026-10-24, con las palabras del usuario): [docs/historial-pedidos.md](docs/historial-pedidos.md).

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

### Restricciones vigentes de trabajo

Salen de pedidos ya cerrados (textuales en `docs/historial-pedidos.md`) y de lo que pasó; siguen valiendo.

- **Git:** commit y push solo cuando el usuario lo pida (regla 7). Nunca se suben `.env` (clave de DeepSeek),
  `entorno/` ni `datos/*.db*`; revisar con `git add -n` antes de cada commit.
- **El carro ya está impreso y armado** (usuario, 2026-10-24: "el carro ya no lo toque"): en `chasis_impreso/` no se
  regenera nada ni cambia la geometría.
- **No mandar a imprimir:** imprime el usuario, desde `maqueta_impresa/3mf/`. Los `alm_1.3mf`, `alm_2.3mf` y `alm_3.3mf`
  que guardó Creality Print (25 y 26/10) están sin commit: no se tocan, no se restauran y no entran en un `git add -A`.
- `maqueta_impresa/3mf/guardados/` (proyectos de Creality Print con la MAC de la impresora) nunca se sube (está en
  `maqueta_impresa/.gitignore`).
- **Creality Print solo con `--cli --datadir`** (como `maqueta_impresa/laminar.py`); nunca la interfaz ni `--help`: el
  2026-10-25 un agente la abrió con `--help`, se sincronizó con la nube y borró los perfiles "maqueta".
- Maqueta (usuario, 2026-10-24 y 25): todo impreso, sin perfil 2020; si digital y físico difieren mandan las piezas
  físicas; nada de membrana, capa de sacrificio ni balsa ("la membrana es horrible, esa no es solución"); no tocar la
  orientación en Y ni los agujeros ciegos ("Déjelo como esta", "Déjalos así"); el puente de 30 mm de `mon_e4` es la
  única excepción aceptada (`voladizos.PUENTES_ACEPTADOS`). Toda unión se mide en el ensamble con el revisor
  (`maqueta_impresa/revisar.py`) antes de entregar.
- Ahorro de costos (usuario, 2026-10-24): NO cambiar la webcam cenital y DEJAR el PCA9685.
- **Agentes:** sin máximo fijo, pero sin cargar la CPU: ~6-8 a la vez y como mucho 2 OpenSCAD por agente
  (usuario, 2026-10-25; detalle en `D:\cosas uni\Micros\CLAUDE.md`).

## 3. Estado actual

Al 2026-10-26: el carro (`chasis_impreso/`) está impreso y armado; el usuario imprime la maqueta desde
`maqueta_impresa/3mf/`; el orden de carpetas va por el punto 5 (§0).

Decisiones vigentes (2026-09-29): carrusel 28BYJ-48 con espera aceptada (media vuelta 4,22 s desde el 2026-10-25; la moneda espera en
E4 y además la caída, `caida_moneda_tubo: 400`, ocupa el carrusel); pausa de vasos 1400 ms; rodillo Ø22
(69,1 mm/vuelta); vaso lleno 133 g; prensa 60 N; llanta 26 mm y muelle +4 mm; "detén la línea" = pausa y
PARO solo con "paro"/urgencia; asistente 60/60. Dashboard en 127.0.0.1 con chequeo de salud (antes se caía).
Siguiente (cuando el usuario diga): montaje físico, medir los PROVISIONALES, visión real (fase 5), clave
válida de DeepSeek.

- Pruebas: `entorno/Scripts/python -m pytest -q` → todas deben pasar (951 el 2026-10-26, ~4-5 min).
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
- Fase 7 (2026-09-27): asistente en `app/asistente/` (DeepSeek con JSON como el tema 4 del repo;
  busca en toda la documentación; estado en vivo; lista blanca de órdenes; voz; intérprete local sin
  internet). Órdenes al carro por la radio: detener, avanzar, retroceder, girar, ir_a, ir_meta,
  volver_muelle, seguir_linea; odometría (a cero en el muelle), revisa el camino a 0/±15° y no choca;
  desde el muelle sale derecho antes de girar. Evasión automática: `margen_pasar_muro_mm: 70`
  (rozaba el muro con 1 de 11 semillas). Visor: nube de la API + pestaña Asistente (solo lectura).
- **Clave de DeepSeek:** la del tema 4 (`Sensores-Teoria/4-chatbot-asistente-voz/.env`) fue RECHAZADA
  (401). El `.env` del proyecto final tiene la clave que dio el usuario, que también dio 401: hay que
  poner una válida (`.env.example`); mientras tanto responde el modelo local.

Pendientes que quedaron sin cerrar (copiados del historial):
- Pendiente: videos embalaje_vasos/todo_junto sin rellenar las esperas.

## 4. Pendiente de decisión del usuario (no implementar sin respuesta)

(Vacía. Lo que había el 2026-09-29 quedó superado; está en `docs/historial-pedidos.md`.)

## 5. Dónde está cada cosa (para no buscar)

- Instrucciones para Claude Code: `CLAUDE.md` (este mismo directorio). Especificación del proyecto (arquitectura, secciones 1-19): `docs/especificacion.md`. Pedidos cerrados: `docs/historial-pedidos.md`.
- Historial de decisiones: `docs/bitacora.md`. Paso a paso: `docs/paso-a-paso.yaml` (el `.md`
  se genera con `python -m app.documentos`).
- Lógica pura: `control/` (linea.py, embalaje.py, reglas.py, almacen.py, tiempos.py, vehiculo.py).
- Asistente: `app/asistente/` (paquete; + pestaña en `app/dashboard/pestanas/asistente.py`, `/api/asistente` en `app/servidor.py`,
  pestaña y nube en `app/visor3d/visor.js`). Guía del parcial: `docs/enunciado/`.
- Simulación: `sim/planta.py` (todo el flujo tick a tick), `sim/mundo.py` (PyBullet y medidas),
  `sim/sensores_sim.py`, `sim/backend_sim.py` (la HAL sobre PyBullet), `sim/geometria.py` (lo que ve el visor).
- Catálogos: `sim/catalogos.py` (13 sensores + lista de materiales).
- Configuración y valores provisionales: `config/parametros.yaml`.
- Pruebas: `tests/<capa>/` (índice en `docs/especificacion.md` §9); escenarios de un solo filtro en
  `sim/escenarios/pruebas_aisladas/`. Índice de los documentos: `docs/README.md`.
- Visor 3D: `app/visor3d/visor.js`. Demo grabada: `python -m app.grabar_demo`.
- Maqueta impresa: `maqueta_impresa/` (fuentes en `scad/`, informes en `informes/`, STL, piezas y manual en `salida/`;
  su `README.md`). Carro impreso: `chasis_impreso/` (STL, 3MF, lista de materiales y manual en `salida/`).
- Capturas en tiempo real para revisar el 3D (no usar `--virtual-time-budget`, engaña):
  `node "D:\cosas uni\Micros\.claude\herramientas\captura-chrome.mjs" <url> <salida.png>` (Chrome sin ventana por
  DevTools; no abre el navegador del usuario).
