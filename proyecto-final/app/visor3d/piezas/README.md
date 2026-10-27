# Piezas del visor 3D

Cada pieza detallada del visor (sensores, placas, mecanismos) vive en un módulo de esta carpeta,
no dentro de `visor.js` (~6300 líneas). Así varias personas (o sesiones) pueden modelar a la vez
sin tocar el mismo archivo, y la misma pieza se puede reutilizar en otro visor. Aquí van solo
piezas: el resto del visor (la escena, la interfaz, `optimizar.js`, el lector de los GLB impresos)
está en la carpeta de arriba, [`app/visor3d/`](../README.md).

## Convención

- **Un módulo por grupo de piezas**: `electronica.js`, `sensores.js`, `linea_vasos.js`... Si el
  grupo ya existe, se agregan funciones AL FINAL de ese archivo; no se crea uno por pieza.
- **Importa `three` y `./base.js`** (y, si reutiliza una pieza, el módulo de esta carpeta que la
  tiene: `linea_vasos.js` toma el servo y el NEMA17 de `electronica.js` y la webcam de `sensores.js`):
  ```js
  import * as THREE from 'three';
  import { MM, COLOR, METAL, P, mat, caja, cilindro, ancla, instancias, planoDibujado, terminar } from './base.js';
  ```
  Nada de `visor.js` (ni `G`, ni `PIN`, ni `escena`): la pieza no sabe dónde se va a usar.
  Imports locales siempre con la forma `from './archivo.js'` (una ruta simple, sin subcarpetas):
  `app/chequeo.py` solo mira `piezas/*.js` (no subcarpetas) para saber si el portable quedó viejo
  (`app/portable.py` sí sigue subcarpetas y `../`).
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
3. Verificar: `node --input-type=module --check < archivo.js` con `visor.js` y con el módulo (uno por llamada; `node --check` a secas no ve errores en ESM), `entorno\Scripts\python -m app.portable` y
   `entorno\Scripts\python -m pytest -q tests/visor`, y una captura del
   visor (servido con `?demo` y el `visor-portable.html`) sin errores de consola.

`app/portable.py` sigue los imports desde `visor.js` y mete cada módulo que alcanza en el
importmap del HTML de un solo archivo (como `piezas/<archivo>.js`, en data: URLs), reescribiendo los
imports locales: un módulo que nadie importa no entra, y no hay que tocar `portable.py` al agregar
uno nuevo.

Para que una pieza nueva se vea bien después de `optimizar.js` (que une las mallas quietas al
terminar la escena; ver [el README del visor](../README.md#optimizarjs)): lo que se anima tiene que
quedar referenciado (en `P`, en `userData` o con `name` buscado en vivo), si no se une con lo quieto
y deja de moverse; y nada de caras en el MISMO plano con otra de distinto color (parpadean): separar
0,2–0,5 mm o usar `polygonOffset` en calcomanías (`planoDibujado` ya lo trae).

## Copia fuera del repositorio

Cada módulo terminado se copia tal cual (con `base.js`) a
`D:\cosas uni\Modelado 3D\piezas-threejs\` (también `optimizar.js`, que ya no es pieza: su fuente es
`app/visor3d/optimizar.js`) y se agrega
su fila en `CATALOGO_COMPONENTES.md`, sección "Piezas Three.js": función, qué es, medidas
(y de dónde salen), origen y anclas.

## Piezas

| Módulo | Función | Qué es |
|---|---|---|
| `base.js` | `MM`, `COLOR`, `METAL`, `PLASTICO`, `P`, `mat`, `caja`, `cilindro`, `ancla`, `instancias`, `planoDibujado`, `terminar` | Lo común a todas las piezas (no dibuja nada): unidades, colores, el paso del marco de la simulación al de Three, materiales, primitivas con sombra, anclas, instancias y texto impreso. |
| `sensores.js` | `crearFC51`, `crearCapacitivoLJC18A3`, `crearInductivoLJ18A3`, `crearWebcam`, `crearVL53L0X`, `crearHallKY003`, `crearIman6x3`, `crearHCSR04`, `crearArregloTCRT5000`, `crearIRCuna`, `crearEncoderH206`, `crearDiscoEncoder20`, `SENSORES` | Los sensores del catálogo (`sim/catalogos.py`) con medidas de ficha técnica; `SENSORES` dice cómo construir cada uno por su id. Los módulos en placa usan el mismo marco local que `construirModulo` de `visor.js`. Se usa en la planta (presencia, cámara, capacitivo, inductivo) y en el carro (`PIEZAS_SENSORES_CARRO`). |
| `electronica.js` | `crearESP32DevKit({ pines: 30 \| 38 })` (y `…30P`/`…38P`), `crearPlacaGVS` (`…30P`/`…38P`); drivers: `crearTB6612FNG`, `crearDriverPasoAPaso`, `crearA4988`/`crearTMC2208`, `crearPlacaDriversPasoAPaso`, `crearPCA9685`, `crearULN2003`, `crearPlacaOptoPC817`; energía: `crearBuck*`, `crearFuente*`, `crearPortafusible*`, `crearInterruptorFusible`, `crearEntradaIEC`, `crearPortaBaterias18650x2`; cableado: `crearBorneraDIN16`, `crearRepartoI2C`, `crearHubUSB4`; motores: `crearNEMA17`, `crear28BYJ48`, `crearServo` (`crearServoSG90`, `crearServoMG996R`) | Placas, drivers, fuentes, motores y servos de la caja de control, la planta y el carro. El ESP32 DevKit V1 lleva WROOM y antena, CP2102, AMS1117, EN/BOOT, micro-USB (o USB-C), LEDs, dos filas de pines con serigrafía y anclas `pin_ESP32_<PIN>` con el pinout real; va en las dos placas GVS (caja de control y carro). |
| `pista.js` | `crearPista(...)`, `crearMuroLadrillo`, `crearBanderaMeta` | Pista del carro sobre la línea central de la simulación (`G.pista.linea`, sin cambiarla): lámina blanca con borde, cinta de 19 mm con costuras, franjas de meta/giro de cinta, rótulos en el margen, muros de ladrillo 100×30×80, bandera de meta y piso de baldosa alrededor. Se usa en `construirPista`. |
| `estructura.js` | `mallaPerfil2020`, `crearPerfil2020(largo, orientacion)`, `perfil2020Entre`, `crearEscuadra2020({ejeA, ejeB})`, `crearTornilloT`, `crearPieNivelador`, `crearMesaPerfil`, `crearPortico2020`, `crearRielCanaleta`, `crearCabezalRiel`, `crearSoporteCanaleta` | Perfil 2020 con su sección ranurada real (una geometría compartida; `perfil()` de visor.js la usa para todo perfil de 20 mm alineado), escuadras con tornillos M5, pies niveladores, mesa y pórtico de 2020, y la canaleta de entrega: varilla de 4 mm doblada con PTFE sobre postes 2020 con cabezal impreso inclinado. |
| `control.js` | `crearGabineteControl(...)`, `crearPasoConBrida({ tipo })`, `crearPrensaestopas({ tipo })`, `crearVentilador4010`, `crearLaptopTUFA15`, `cajaRedonda` | Caja de control de acrílico 360 × 240 × 80 mm (placa de montaje, esquineros de aluminio, tapa de policarbonato atornillada, pasos de cable con brida —`conBridas: true`, ahorro 2026-10-24; antes prensaestopas PG7/PG9/PG16—, ventilador 40 mm, rejilla) y el portátil ASUS TUF A15 con la pantalla del asistente. Las placas de la caja son las de `electronica.js` (en `construirCajaControl`, con `conPieza`). |
| `linea_monedas.js` | `crearRodilloCinta`, `crearCojinete608`, `crearAcople`, `crearSoporteNEMA17`, `crearPlatinaM18`, `crearCompuertaDesvio`, `crearOrejaBisagra`, `crearBridaServo`, `crearBandejaRechazo`, `crearPlacaFijaAlmacen`, `crearDiscoCarrusel`, `crearTuboMonedas`, `crearObturadorAlmacen`, `crearSoporteMotorCarrusel`, `crearListon`, `crearPosteCamaraCenital` | Cinta de monedas (rodillo motriz con goma y tensor, 608ZZ en bloques impresos, jaula del NEMA17 con acople flexible, platinas M18 bajo E1/E2), descarga (compuerta en Y coaxial con el SG90, bandeja de rechazo) y almacén revólver (placa fija con un agujero, disco de acrílico con imán, 6 tubos de policarbonato rotulados, obturador coaxial con su SG90, placa del 28BYJ-48). Se usa en `construirCintaMonedas`, `construirBanda` y `construirAlmacen`. |
| `linea_vasos.js` | `crearVaso`, `crearTapa`, `crearTacoCasilla`, `crearTuboTapas`, `crearPrensaLeva`, `crearEmpujador`, `crearAccionamientoCinta`, `crearPanelLuz`, `crearPosteCamara`, `crearCamaraVasos`, `crearPortaVL53Interior` | Cinta de vasos: vaso con pestaña y cinta ArUco, tapa con cono (apilable), tacos de casilla, tubo de tapas con escape de SG90, prensa de leva en MG996R (resorte que se comprime en vivo), empujador biela-manivela, NEMA17 con acople, panel de luz, cámara de vasos en su poste, porta del VL53L0X del interior. Los que se mueven traen `userData.poner(u)`. |
| `carro.js` | `disposicionCarro`, `crearChasisCarro`, `crearPerfboard`, `crearSeparadorM3`, `crearMotorTT`, `crearRuedaTT`, `crearRuedaLocaBola`, `crearRodilloGuia623`, `crearSoporteEncoder`, `crearEscuadraFrontal`, `crearCunaCarro`, `crearMuelleCarga` | Carro de entrega y muelle de carga: chasis de acrílico con hueco del vaso y ranuras, motorreductores TT en soportes en T, ruedas de 65 mm con dibujo, disco de encoder en el eje, rueda loca de bola, rodillos 623, escuadra de los sensores del frente, cuna (rieles con PTFE, mampara con espumas, lengüeta) y guías en V con topes. Cotas en `disposicionCarro` (placa 11,5 mm sobre el eje). **Desde el 2026-10-24 el carro se dibuja con el chasis impreso** (`carro_armado.glb`, ver [los GLB impresos](../README.md#los-glb-impresos-maqueta-y-carro)): de aquí siguen en uso `disposicionCarro` (las cotas que comparte con la física), `crearMotorTT` (sin soportes), `crearRuedaTT` y `crearMuelleCarga`; el resto queda de respaldo si el GLB no carga (`?sinmaqueta`). |
