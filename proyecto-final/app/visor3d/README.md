# `app/visor3d/`: el visor 3D (Three.js)

La planta, el carro y la pista en 3D, con el estado de la corrida en vivo, las pruebas, el paso a
paso, los sensores y los componentes. JavaScript de módulos sin build ni CDN: Three.js va en
`vendor/`. Inventario de lo que hace la interfaz (pestañas, controles, parámetros de URL):
[`docs/interfaz-visor.md`](../../docs/interfaz-visor.md).

## Cómo se ve

| Cómo | Qué muestra |
|---|---|
| `python -m app.lanzar --auto prueba_completa --abrir` (o `visor.bat`) | En vivo: lo sirve `app/servidor.py` desde el proceso supervisor en `http://127.0.0.1:8765/` (o el siguiente puerto libre) y pregunta `/api/estado` cada 200 ms. |
| La misma URL con `?demo` | La corrida grabada de `demo/`, sin supervisor detrás. |
| `visor-portable.html` (raíz del proyecto, `python -m app.portable`) | Todo en un solo archivo (~9,4 MB) que se abre con doble clic, sin Python ni internet: muestra la demo y pasa solo al vivo si la simulación de este PC responde. |

Otros parámetros de la URL: `?sinmaqueta` (el modelo dibujado a mano en vez de los GLB impresos),
`?sinoptimizar` (sin unir mallas, para comparar), `?auditar` (revisa que nada toque las mallas unidas
y expone la escena en `window.__visor`), `?cables`, `?sinremaches`.

## Archivos

| Archivo | Qué es |
|---|---|
| `index.html` | El esqueleto de la interfaz (barra, vistas, panel, avisos) y el importmap de `three`. |
| `estilo.css` | El sistema de diseño del visor (el mismo lenguaje visual que el dashboard). |
| `interfaz.js` | Todo el comportamiento de la interfaz: pestañas, controles, avisos, internet, bitácora, leyenda de cables, parámetros de URL y el vigía del portable. `visor.js` le pasa lo que necesita con `crearInterfaz(ctx)`. |
| `visor.js` | La escena: construcción de cada zona, cámara, animación con el estado en vivo o la demo (~6300 líneas). |
| `optimizar.js` | `optimizarEscena`: une las mallas quietas al terminar de construir la escena (abajo). |
| `maqueta_impresa.js` | `leerMaquetaGLB`: lector propio de los dos GLB impresos (abajo). |
| `piezas/` | Un módulo por grupo de piezas detalladas (sensores, placas, mecanismos), reutilizables fuera del visor. Convención y lista: [`piezas/README.md`](piezas/README.md). |
| `vendor/` | `three.module.min.js` y `OrbitControls.js`, copiados tal cual (no son código propio). |
| `demo/` | `geometria.json`, `pasos.json` y `grabacion.json`: la corrida grabada que reproduce el visor sin servidor. GENERADOS por `python -m app.grabar_demo` (no editar). |
| `maqueta_impresa.glb` | La planta impresa en PLA (3,9 MB). GENERADO por `python maqueta_impresa/modelo_3d.py`. |
| `carro_armado.glb` | El carro impreso armado (1,1 MB). GENERADO por `python chasis_impreso/modelo_3d.py`. |

## Los GLB impresos (maqueta y carro)

`leerMaquetaGLB(buffer)` (`maqueta_impresa.js`) lee `maqueta_impresa.glb` y devuelve un grupo con una
malla por pieza de PLA (183), ya en su lugar y en metros, con las extras del GLB en `userData`
(`movil`, `pivote`, `eje`, `recorrido` en las que se mueven). `visor.js` (`cargarGLB` /
`montarMaqueta`) la pone en la escena, cuelga cada parte móvil del objeto que ya anima (carrusel,
aleta E4, dedos, leva, pistón, paleta, manivela, biela, escape, separadores de vasos; el obturador gira
en horizontal) y saca lo que la maqueta reemplaza (perfil 2020, escuadras, pies, aluminio, acrílico,
soportes: lo marcado con `reemplazar()`).

El GLB trae además los **316 remaches impresos** en su lugar, un nodo por subsistema (`rem_<grupo>`,
`userData.tipo = 'remache'`, rojo `#d1001f` como en los manuales): `visor.js` los junta en `REMACHES` y
el botón **Remaches** de la barra (`interfaz.js`, `iniciarRemaches`) los muestra u oculta.

El mismo lector lee `carro_armado.glb`: las 20 piezas de PLA del carro (`userData.tipo = 'impresa'`),
lo comprado en 13 grupos `comp_*` y el nodo `remaches` (los 27 de `REM_LISTA`), en el marco del carro
(origen en el piso bajo el centro del chasis, x adelante). `construirCarro` agrega las impresas, cuelga
la lengüeta de su pivote (la anima `abrirLengueta`) y pone lo que sigue dibujando el visor (ruedas,
motores TT, encoders, batería, ESP32, TB6612, sensores, vaso) donde lo pone el chasis impreso, con las
cotas de `chasis.scad` que vienen en `extras.funcional_mm`. `tests/sim/test_carro_impreso.py` comprueba
que esas cotas son las de `disposicionCarro` (`piezas/carro.js`) y de la simulación.

En el portable los dos van en base64 (`window.__MAQUETA` y `window.__CARRO`). Sin GLB, o con
`?sinmaqueta`, queda el modelo dibujado a mano de `piezas/`.

## `optimizar.js`

`optimizarEscena(escena, {...})`: el paso que `visor.js` corre al terminar de construir la escena.
Une las mallas quietas que se ven igual (por ancla, componente y material; color y rugosidad por
vértice) y deja una malla "solo sombra" por ancla: medido el 2026-09-28 (antes de los GLB impresos),
~3.200 mallas → ~700 y de ~3.000 a menos de 500 llamadas de dibujo, con el mismo detalle (con `?auditar`,
`window.__visor.info()` da las de hoy). Lo que se anima tiene que quedar referenciado (en `P`, en
`userData` o con `name` buscado en vivo); si no, se une con lo quieto y deja de moverse.

## Reglas

- **`visor.js` no se parte**: las pruebas lo leen con regex (`tests/sim/test_fisica_vs_3d.py`,
  `tests/sim/test_carro_impreso.py`, `tests/visor/`). Lo nuevo y grande va en un módulo aparte.
- **Imports locales uno por línea y con ruta simple** (`./interfaz.js`, `./piezas/sensores.js`):
  `app/portable.py` sigue los imports desde `visor.js` y mete cada módulo que alcanza en el importmap
  del portable, con su ruta dentro de esta carpeta como nombre. Un módulo que nadie importa no entra; uno
  nuevo no obliga a tocar `portable.py`. `optimizar.js` y `maqueta_impresa.js` viven aquí, junto a
  `visor.js` (no son piezas; en `visor.js` se importan como `OPTIMIZAR` y `GLB_IMPRESOS`).
- **Después de cambiar algo**: `node --input-type=module --check < archivo.js` (`node --check archivo.js` sale con 0 aunque haya errores: son módulos ESM), `python -m app.portable` (`visor.bat` lo hace
  solo al arrancar; `python -m app.chequeo` avisa si el portable quedó más viejo que el visor, código o `.glb`) y
  `entorno\Scripts\python -m pytest -q tests/visor`. Si cambió lo que se graba, `python -m app.grabar_demo`.
- **No editar a mano** `demo/`, los `.glb` ni `vendor/`: se regeneran o se copian de su fuente.

Quién nombra esta carpeta desde afuera: `app/servidor.py`, `app/portable.py`, `app/grabar_demo.py`
(`demo/`), `app/dashboard/datos.py` (`demo/geometria.json`, si el supervisor no corre), `app/chequeo.py`,
`maqueta_impresa/modelo_3d.py` y `chasis_impreso/modelo_3d.py` (los GLB), `../.gitattributes` del repo
(`demo/*.json`, `vendor/**`) y las reglas de `D:\cosas uni\Micros\.claude\rules\` por glob
(`**/visor3d/**`, `**/visor3d/piezas/**`).
