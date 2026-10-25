# Piezas del visor 3D

Cada pieza detallada del visor (sensores, placas, mecanismos) vive en un módulo de esta carpeta,
no dentro de `visor.js` (4700 líneas). Así varias personas (o sesiones) pueden modelar a la vez
sin tocar el mismo archivo, y la misma pieza se puede reutilizar en otro visor.

## Convención

- **Un módulo por grupo de piezas**: `electronica.js`, `sensores.js`, `mecanismos.js`... Si el
  grupo ya existe, se agregan funciones AL FINAL de ese archivo; no se crea uno por pieza.
- **Importa solo `three` y `./base.js`**:
  ```js
  import * as THREE from 'three';
  import { MM, COLOR, METAL, P, mat, caja, cilindro, ancla, instancias, planoDibujado, terminar } from './base.js';
  ```
  Nada de `visor.js` (ni `G`, ni `PIN`, ni `escena`): la pieza no sabe dónde se va a usar.
  Imports locales siempre con la forma `from './archivo.js'` (una ruta simple, sin subcarpetas):
  `app/portable.py` los reescribe para el HTML de un solo archivo.
- **Exporta `crearX(opciones) → THREE.Group`**, con un comentario arriba que diga las medidas
  y DE DÓNDE salen (ficha técnica, `CATALOGO_COMPONENTES.md`, `config/parametros.yaml`).
- **Metros**, y el marco de la simulación: x a lo largo, y a lo ancho, z hacia arriba.
  `P(x, y, z)` lo pasa a Three (y arriba); `caja(sx, sy, sz, ...)` y `cilindro(...)` ya lo
  hacen. Una medida en mm se escribe `18 * MM`.
- **Origen = el punto de montaje que ya usa el visor** para esa cosa (por ejemplo, el ESP32:
  centro de sus pines, en la cara de abajo del PCB). Así integrarla es solo `position.copy(...)`.
  El comentario de la función dice cuál es el origen y hacia dónde mira cada eje.
- **Nombres**: todo lo que se mueve o se enciende lleva `name` (`rueda_izq`, `carrusel`, `leva`,
  `compuerta`, `empujador`, `escape`, `led_gpio2`...). Para cables y soportes, `Object3D` vacíos
  hechos con `ancla(...)`: `pin_<MODULO>_<PIN>` (p. ej. `pin_ESP32_G34`, los repetidos con
  `_2`, `_3`) y `ancla_<nombre>` (`ancla_usb`, `ancla_montaje`...). El visor los encuentra con
  `grupo.getObjectByName(...)` y lee su posición con `getWorldPosition`.
- **Datos del visor**: `opciones.sensorId` / `opciones.idComponente` van a `userData` de todas
  las mallas (`terminar(grupo, { datos })`): el clic en un sensor y el panel de componentes los
  leen de ahí.
- **Sombras**: `caja` y `cilindro` ya ponen `castShadow`; `terminar` lo pone en el resto. Las
  piezas chicas repetidas (pines, tornillos) van con `instancias(...)` (una sola InstancedMesh,
  sin sombra).
- **Materiales**: `mat(...)` crea uno nuevo en cada llamada A PROPÓSITO: el resaltado de
  componentes del visor cambia el `emissive` de cada material y uno compartido encendería
  también las piezas vecinas. Luces que no deben apagarse con el resaltado (LEDs): material
  básico (`MeshBasicMaterial`), que no tiene `emissive`.
- **Texto impreso** (serigrafía, rótulos, pantallas): `planoDibujado(largo, ancho, dibujar)`, un
  canvas pegado en un plano horizontal; fuentes "IBM Plex Mono" / "Space Grotesk" como el visor.
- Comentarios y nombres en español, como el resto del proyecto.

## Cómo se integra una pieza en `visor.js`

1. Arriba de `visor.js`, junto al de electrónica, un import por módulo (uno por línea, con la
   ruta `./piezas/<archivo>.js`):
   ```js
   import * as PIEZAS_SENSORES from './piezas/sensores.js';
   ```
2. En el `construir*` de su zona, cambiar SOLO las líneas que dibujaban esa cosa: crear la
   pieza, ponerla en el mismo lugar y conservar lo que dependía del dibujo viejo (`registrar`
   para el resaltado, `pinSuelto` para los cables, las referencias que usan las animaciones),
   dentro de un `try/catch` que deja el modelo actual si la pieza falla:
   ```js
   try {
     const s = PIEZAS_SENSORES.crearLJ18A3({ sensorId: 'inductivo' });
     s.position.copy(pos);
     grupo.add(s);
     // Punto del ancla en el marco de `grupo` (vale aunque la pieza esté girada):
     s.updateMatrix();
     const salida = s.getObjectByName('ancla_cable').position.clone().applyMatrix4(s.matrix);
     pinSuelto('inductivo.CAFE', grupo, salida);
   } catch (e) {
     console.warn('pieza LJ18A3: se usa el modelo simple', e);
     /* ... las líneas de antes, sin cambios ... */
   }
   ```
   Ejemplo real: el ESP32 de las placas GVS, en `construirModulo` (busca `PIEZAS_ELECTRONICA`).
3. Verificar: `node --check` de `visor.js` y del módulo, `python -m app.portable` y
   `python -m pytest -q tests/visor/test_portable.py tests/visor/test_visualizacion.py`, y una captura del
   visor (servido con `?demo` y el `visor-portable.html`) sin errores de consola.

`app/portable.py` mete TODOS los `.js` de esta carpeta en el importmap del HTML de un solo
archivo (como `piezas/<archivo>.js`, en data: URLs) y reescribe los imports locales; no hay que
tocarlo al agregar un módulo nuevo.

## Copia fuera del repositorio

Cada módulo terminado se copia tal cual (con `base.js`) a
`D:\cosas uni\Modelado 3D\piezas-threejs\` y se agrega
su fila en `CATALOGO_COMPONENTES.md`, sección "Piezas Three.js": función, qué es, medidas
(y de dónde salen), origen y anclas.

## Piezas

| Módulo | Función | Qué es |
|---|---|---|
| `electronica.js` | `crearESP32DevKit({ pines: 30 \| 38 })`, `crearESP32DevKit30P`, `crearESP32DevKit38P` | ESP32 DevKit V1 con WROOM y antena, CP2102, AMS1117, EN/BOOT, micro-USB (o USB-C), LEDs, dos filas de pines con serigrafía y anclas `pin_ESP32_<PIN>` con el pinout real. Se usa en las dos placas GVS (caja de control y carro). |
| `pista.js` | `crearPista(...)`, `crearMuroLadrillo`, `crearBanderaMeta` | Pista del carro sobre la línea central de la simulación (`G.pista.linea`, sin cambiarla): lámina blanca con borde, cinta de 19 mm con costuras, franjas de meta/giro de cinta, rótulos en el margen, muros de ladrillo 100×30×80, bandera de meta y piso de baldosa alrededor. Se usa en `construirPista`. |
| `estructura.js` | `mallaPerfil2020`, `crearPerfil2020(largo, orientacion)`, `perfil2020Entre`, `crearEscuadra2020({ejeA, ejeB})`, `crearTornilloT`, `crearPieNivelador`, `crearMesaPerfil`, `crearPortico2020`, `crearRielCanaleta`, `crearCabezalRiel`, `crearSoporteCanaleta` | Perfil 2020 con su sección ranurada real (una geometría compartida; `perfil()` de visor.js la usa para todo perfil de 20 mm alineado), escuadras con tornillos M5, pies niveladores, mesa y pórtico de 2020, y la canaleta de entrega: varilla de 4 mm doblada con PTFE sobre postes 2020 con cabezal impreso inclinado. |
| `control.js` | `crearGabineteControl(...)`, `crearPasoConBrida({ tipo })`, `crearPrensaestopas({ tipo })`, `crearVentilador4010`, `crearLaptopTUFA15`, `cajaRedonda` | Caja de control de acrílico 360 × 240 × 80 mm (placa de montaje, esquineros de aluminio, tapa de policarbonato atornillada, pasos de cable con brida —`conBridas: true`, ahorro 2026-10-24; antes prensaestopas PG7/PG9/PG16—, ventilador 40 mm, rejilla) y el portátil ASUS TUF A15 con la pantalla del asistente. Las placas de la caja son las de `electronica.js` (en `construirCajaControl`, con `conPieza`). |
| `linea_monedas.js` | `crearRodilloCinta`, `crearCojinete608`, `crearAcople`, `crearSoporteNEMA17`, `crearPlatinaM18`, `crearCompuertaDesvio`, `crearOrejaBisagra`, `crearBridaServo`, `crearBandejaRechazo`, `crearPlacaFijaAlmacen`, `crearDiscoCarrusel`, `crearTuboMonedas`, `crearObturadorAlmacen`, `crearSoporteMotorCarrusel`, `crearListon`, `crearPosteCamaraCenital` | Cinta de monedas (rodillo motriz con goma y tensor, 608ZZ en bloques impresos, jaula del NEMA17 con acople flexible, platinas M18 bajo E1/E2), descarga (compuerta en Y coaxial con el SG90, bandeja de rechazo) y almacén revólver (placa fija con un agujero, disco de acrílico con imán, 6 tubos de policarbonato rotulados, obturador coaxial con su SG90, placa del 28BYJ-48). Se usa en `construirCintaMonedas`, `construirBanda` y `construirAlmacen`. |
| `linea_vasos.js` | `crearVaso`, `crearTapa`, `crearTacoCasilla`, `crearTuboTapas`, `crearPrensaLeva`, `crearEmpujador`, `crearAccionamientoCinta`, `crearPanelLuz`, `crearPosteCamara`, `crearCamaraVasos`, `crearPortaVL53Interior` | Cinta de vasos: vaso con pestaña y cinta ArUco, tapa con cono (apilable), tacos de casilla, tubo de tapas con escape de SG90, prensa de leva en MG996R (resorte que se comprime en vivo), empujador biela-manivela, NEMA17 con acople, panel de luz, cámara de vasos en su poste, porta del VL53L0X del interior. Los que se mueven traen `userData.poner(u)`. |
| `carro.js` | `disposicionCarro`, `crearChasisCarro`, `crearPerfboard`, `crearSeparadorM3`, `crearMotorTT`, `crearRuedaTT`, `crearRuedaLocaBola`, `crearRodilloGuia623`, `crearSoporteEncoder`, `crearEscuadraFrontal`, `crearCunaCarro`, `crearMuelleCarga` | Carro de entrega y muelle de carga: chasis de acrílico con hueco del vaso y ranuras, motorreductores TT en soportes en T, ruedas de 65 mm con dibujo, disco de encoder en el eje, rueda loca de bola, rodillos 623, escuadra de los sensores del frente, cuna (rieles con PTFE, mampara con espumas, lengüeta) y guías en V con topes. Cotas en `disposicionCarro` (placa 11,5 mm sobre el eje). **Desde el 2026-10-24 el carro se dibuja con el chasis impreso** (`carro_armado.glb`, abajo): de aquí siguen en uso `disposicionCarro` (las cotas que comparte con la física), `crearMotorTT` (sin soportes), `crearRuedaTT` y `crearMuelleCarga`; el resto queda de respaldo si el GLB no carga (`?sinmaqueta`). |

## `maqueta_impresa.js` (no es una pieza)

`leerMaquetaGLB(buffer)`: lee `app/visor3d/maqueta_impresa.glb` (lo genera `python maqueta_impresa/modelo_3d.py`
desde los STL de la maqueta impresa) y devuelve un grupo con una malla por pieza de PLA, ya en su lugar y en
metros, con las extras del GLB en `userData` (`movil`, `pivote`, `eje`, `recorrido` en las que se mueven).
`visor.js` (`cargarMaqueta` / `montarMaqueta`) la pone en la escena, cuelga cada parte movil del objeto que ya
anima (carrusel, aleta E4, dedos, leva, piston, paleta, manivela, biela, escape, separadores de vasos; el
obturador gira en horizontal) y saca lo que la maqueta reemplaza (perfil 2020, escuadras, pies, aluminio,
acrilico, soportes: lo marcado con `reemplazar()`). En `visor-portable.html` va en base64 (`window.__MAQUETA`).
`?sinmaqueta` en la URL deja el modelo de antes.

El GLB trae ademas los **310 remaches impresos** en su lugar (un nodo por subsistema, `rem_<sub>`,
`userData.tipo = 'remache'`, rojo `#d1001f` como en los manuales): `visor.js` los junta en `REMACHES` y la
casilla **Remaches** de la barra (`interfaz.js`, `iniciarRemaches`) los muestra u oculta.

### `carro_armado.glb` (el carro impreso, 2026-10-24)

El mismo lector lee `app/visor3d/carro_armado.glb` (lo genera `python chasis_impreso/modelo_3d.py`, que lo deja
también en `chasis_impreso/`): las 20 piezas de PLA del carro (`userData.tipo = 'impresa'`), lo comprado en
grupos `comp_*` y el nodo `remaches` (los 27 de `REM_LISTA`), ya en el marco del carro (origen en el piso bajo el
centro del chasis, x adelante). `construirCarro` (`visor.js`) agrega las impresas (en `COLOR.impreso`), las
espumas, la rueda loca, los rodamientos 623 y el interruptor/portafusible del GLB, cuelga la lengüeta de un
grupo en su pivote (`extras.pivote`, la anima `abrirLengueta`) y pone lo que sigue dibujando el visor (ruedas,
motores TT sin soportes, encoders, pack 2S, GVS con el ESP32, TB6612, TCRT5000, HC-SR04, VL53L0X, vaso) donde
lo pone el chasis impreso, con las cotas de `chasis.scad` que vienen en `extras.funcional_mm` (mm). Sin GLB
queda el carro dibujado a mano de `carro.js`. `tests/sim/test_carro_impreso.py` comprueba que esas cotas son
las de `disposicionCarro` y de la simulación. En el portable va como `window.__CARRO`.

## `optimizar.js` (no es una pieza)

`optimizarEscena(escena, {...})`: el paso que `visor.js` corre al terminar de construir la escena.
Une las mallas quietas que se ven igual (por ancla, componente y material; color y rugosidad por
vértice) y deja una malla "solo sombra" por ancla: ~3.200 mallas → ~700 y de ~3.000 a < 500
llamadas de dibujo, con el mismo detalle. Vive aquí porque `app/portable.py` embebe esta carpeta.
Para una pieza nueva: lo que se anime tiene que quedar referenciado (en `P`, en `userData` o con
`name` buscado en vivo); si no, se une con lo quieto y deja de moverse. `?sinoptimizar` en la URL
deja la escena sin unir (para comparar) y `?auditar` revisa que nada toque las mallas unidas.
Las piezas deben evitar caras en el MISMO plano con otra de distinto color (parpadean): separar
0,2–0,5 mm o usar `polygonOffset` en calcomanías (`planoDibujado` ya lo trae).
