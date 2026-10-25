# Contexto de sesión — LEER ANTES DE TOCAR NADA

Este archivo existe para que una sesión nueva sepa en qué va el proyecto sin gastar miles de
tokens buscando, y sobre todo **qué NO hacer**. Se actualiza al final de cada sesión.

## 0. Pedido EN CURSO (se escribe AL EMPEZAR cada sesión, antes de tocar código)

Por qué existe: dos veces se cerró una sesión a la fuerza a mitad de trabajo y se perdió el
último mensaje del usuario. Regla: al empezar, copiar aquí el pedido textual y la lista de
puntos; al terminar cada punto, marcarlo. Si se pierde un mensaje, está completo en el
transcript de Claude Code: `~/.claude/projects/D--cosas-uni-Micros/<sesion>.jsonl`
(líneas con `"type":"user"`; el más reciente por fecha de modificación).

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

### Pedido EN CURSO del 2026-10-16 — auditoría de prácticas 1–11 y proyecto final

Textual del usuario:
> "codex, ud es el lider, revise en el disco D cosas uni, micros, organice esas carpetas actualice el repo en github si va a cambiar los nombres, y separe la carpeta y todo lo referente a modelado 3d fuera de la carpeta y coloquele un nombre acorde a todo el modelaje, arregle rutas dañadas de todas las practicas talleres etc, y arregle cualquier error que encuentre, organice tambien el repo con su logica respectiva, puede usar los agentes ia en el chat, exepto claude y modelos que usan claude de mi cuenta, tiene acceso a el github, si no lo tiene hagalo junto a las herramientas necesarias, recuerde arreglar cualquier ruta y si encuentra algun fallo lo arregla"
>
> Aclaración posterior: "no movio la carpeta de micros entorno de pruebas que le dije dentro de micros, y tampoco reviso las practicas de la 1 a la 11 con talleres y proyectos los errores logicos que pudierantener, por eso le dije que usara varios agentes por si acaso, es bastante trabajo"

Puntos:
- [x] Mover `D:\micros entorno de pruebas` dentro de `D:\cosas uni\Micros` (destino `Micros entorno de pruebas`); preservar su entorno y datos.
- [x] Auditar prácticas 1–11, talleres y proyecto final por lógica y rutas con agentes que no usen Claude. Prácticas 1–8: enlaces locales Markdown verificados, sintaxis Python válida y revisión de flujos/rutas; 9–11: Compose válido, 40/40 pruebas de protocolo y enlaces Markdown; proyecto final: 937/937 tests pasaron en la ejecución desde `proyecto-final`. Sin ejecutar prácticas que requieren hardware/servicios externos.
- [x] Corregir fallos reproducibles, revisar cambios y dejar registro de lo que quede pendiente. Se corrigió la ruta del activador del venv tras mover `Micros entorno de pruebas` y referencias operativas del nombre del modelado 3D. Un fallo adicional de pytest fue por ejecutar desde el directorio raíz; aislado desde `proyecto-final`, pasó. Tema 10 prueba 6 sigue documentada como 90% frente al criterio de 95%; no se cambió la configuración porque es un resultado conocido, no una ruta rota ni una regresión.
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

- Pruebas: `entorno/Scripts/python -m pytest -q` → todas deben pasar (937 el 2026-10-06, ~5 min).
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
