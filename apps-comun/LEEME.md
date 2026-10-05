# apps-comun: la base de las apps por práctica

Cada práctica tiene una app (una página web local) que se abre con doble clic en `<carpeta>/ABRIR.bat`. Por dentro,
`ABRIR.bat` corre `probar.py --practica <carpeta>`: el lanzador de la raíz levanta su servidor en `127.0.0.1` (o
reutiliza uno ya abierto) y abre `http://127.0.0.1:<puerto>/app/<carpeta>/` en una ventana tipo programa (Edge o
Chrome en modo `--app`; si no hay, el navegador por defecto).

Esta carpeta trae lo común a todas las apps:

| Archivo | Qué es |
|---|---|
| `app.js` | la API `window.App` (habla con el lanzador; versión en `App.version`) |
| `app.css` | estilo del repo (fondo oscuro, Space Grotesk + IBM Plex Mono) y los componentes |

## Qué sirve el lanzador

| URL | Qué es |
|---|---|
| `/app/<carpeta>/...` | la carpeta de la app: `<carpeta>/app/` por defecto, o la carpeta del archivo que diga el campo `"app"` del `probar.json` |
| `/comun/...` | esta carpeta (`/comun/app.js`, `/comun/app.css`) |
| `/repo/<carpeta>/...` | cualquier archivo del repo (imágenes, videos, README, previews). Nunca `.env`, `*.db`, `entorno/`, `.git` |
| `/readme/<carpeta>` | el README de la práctica renderizado |

A cada `.html` servido por `/app/` el lanzador le inyecta `<meta name="probar-token">` y `<meta name="probar-carpeta">`:
`app.js` los usa solo; la app no tiene que hacer nada con el token.

### Dónde va la app (campo `"app"` del probar.json)

Por defecto `<carpeta>/app/index.html`. Si la carpeta `app/` ya es otra cosa (en `proyecto-final/` es el paquete de
Python), se declara en el nivel superior del `probar.json`:

```json
{ "id": "★", "titulo": "...", "app": "app-practica/index.html", "acciones": [ ... ] }
```

La ruta es relativa a la carpeta de la práctica; `/app/<carpeta>/` sirve la carpeta de ese archivo. El hub muestra el
botón "Abrir la app de esta práctica" en cuanto el archivo existe, y `--practica <carpeta>` lo abre. Mientras no exista,
`--practica` abre la tarjeta de esa práctica en el hub.

### Campos nuevos (opcionales) de cada acción en probar.json

| Campo | Para qué |
|---|---|
| `"entrada": true` | el programa lee del teclado (`input()`): el panel muestra una caja de texto que le escribe a su stdin |
| `"ventana": true` | el programa abre su propia ventana (PyBullet, OpenCV): el panel avisa "se abrirá una ventana aparte" |
| `"si_falla": "texto"` | qué hacer si ESTA acción falla; sale en el recuadro de error de la app, debajo del resumen automático (p. ej. en un script que existe para probar la placa: "Conecta el ESP-A por USB y cierra Thonny") |
| `"oculta": true` (o `"solo_app": true`) | acción interna de la app (p. ej. un lector de estado): no sale como botón en el hub |
| `"vida": "app"` | si la app se cierra, la acción se detiene sola: el servidor la para cuando pasan 90 s sin latido de ninguna página de esa app (las apps hacen ping cada 20 s; el margen es por el frenado de temporizadores de Chrome en pestañas ocultas) o 10 s después de que la página avise que se cierra (`pagehide`) sin volver. Una recarga no la para (la página vuelve antes de 10 s) |
| `"modo": "app"` (por defecto) o `"consola"` | `app`: desde la app, el programa corre SIN consola y su salida sale en la página. `consola`: como antes, en una ventana de consola aparte (para programas que leen teclas sueltas con `msvcrt`, menús de consola, etc.) |

Desde el hub (`PROBAR.bat`) las acciones python siguen abriéndose en su consola, como siempre.

Detalles de la salida en modo app: stdout y stderr van juntos y en orden (con `PYTHONUNBUFFERED=1` y UTF-8); cada
línea se corta a 2000 caracteres; el servidor guarda las últimas 5000 líneas por trabajo y la página muestra las
últimas 3000. Lo que el programa escribe sin salto de línea (la pregunta de un `input()`) se muestra al final, en
amarillo, y al contestar queda en la misma línea que la respuesta. Una línea que se reescribe con `\r` (barra de
progreso) queda solo con su último estado. Sin `"entrada": true`, el stdin del programa está cerrado: un `input()`
recibe EOF.

Detener mata el programa y todos sus procesos hijos. Si se pulsa mientras se prepara el entorno, se corta pip y el
programa ya no arranca. Si se recarga la página mientras la acción corre, el panel vuelve a mostrar su salida.

## Ejemplo mínimo de `<carpeta>/app/index.html`

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Brazo robótico</title>
<link rel="stylesheet" href="/comun/app.css">
<style> :root { --acento: #e8823a; } </style>
</head>
<body>
<header class="app-encabezado"><span class="app-num">7</span><h1>Brazo robótico en PyBullet</h1></header>
<main class="app-contenedor">
  <div class="app-portada">
    <div>
      <h2>Un brazo que se mueve con el teclado</h2>
      <p class="app-lema">Qué hace la práctica en una frase sencilla.</p>
    </div>
    <img src="/repo/7-brazo-robotico-urdf/img/demo.gif" alt="El brazo en movimiento">
  </div>
  <div id="pide"></div>

  <div id="pasos">
    <section class="paso" data-titulo="Qué es">
      <h2>Qué es y cómo funciona</h2>
      <div id="teoria"></div>
    </section>
    <section class="paso" data-titulo="Cómo se conecta">
      <h2>Cómo se conecta</h2>
      <div class="app-aviso">Para probarlo NO hace falta montar nada.</div>
      <div class="app-tabla-scroll"><table class="app-pines">
        <tr><th>Pin ESP32</th><th>Va a</th><th>Por qué</th></tr>
        <tr><td>GPIO 21</td><td>SDA de la LCD</td><td>I2C por defecto</td></tr>
      </table></div>
    </section>
    <section class="paso" data-titulo="Pruébalo">
      <h2>Pruébalo</h2>
      <div id="sim"></div>
    </section>
  </div>
</main>
<script src="/comun/app.js"></script>
<script>
(async () => {
  await App.iniciar();
  App.checklist("#pide");
  App.markdown("#teoria", "README.md", { desde: "## Qué es un URDF" });
  App.pasos("#pasos");
  App.panelEjecucion("#sim", "sim", {
    queHacer: ["Usa los botones del panel derecho de PyBullet", "Cierra la ventana para terminar"],
    queDeberiasVer: "El brazo moviéndose al pulsar cada botón.",
  });
  App.imagen(document.body);
})();
</script>
</body>
</html>
```

Imágenes y archivos de la práctica: `/repo/<carpeta>/img/foto.png` (o `App.url("img/foto.png")`). Archivos propios de la
app (css, js, imágenes): rutas relativas (`./estilo.css`), que se sirven desde la carpeta de la app.

## API (`window.App`)

Todas las funciones que reciben un elemento aceptan el elemento o un selector (`"#sim"`).

### `await App.iniciar()`
Lee la práctica de la URL y devuelve su manifiesto normalizado (lo de `probar.json`: `titulo`, `resumen`, `pide`,
`notas`, `python`, `acciones[]`, `compila`...) más `entorno` (`{estado: "listo"|"nuevo"|"faltan"|"sin-python"|"roto"|"subcarpetas", detalle}`),
`sistema` (`"windows"|"linux"|"mac"`), `build_tools` (true/false/null), `pythons` y `trabajos` (lo que ya está en
marcha). Se puede llamar varias veces (devuelve lo mismo). Después quedan `App.practica`, `App.carpeta`, `App.entorno`.
Las demás funciones llaman a `iniciar()` solas si hace falta.

### `App.panelEjecucion(elemento, accionId, opciones)` → `{iniciar(), detener(), enviar(texto), estado, accion}`
Rellena el elemento con el componente completo para una acción del `probar.json`:
- título (el `nombre` de la acción) y bloques "Qué va a pasar" (por defecto la `descripcion`), "Se abrirá una ventana
  aparte: úsala así" (si la acción tiene `"ventana": true`) y "Qué deberías ver";
- aviso de entorno antes de pulsar: "la primera vez se prepara solo…", PyBullet/Build Tools (con el comando para
  copiar), "necesita Python X y no está instalado";
- botón grande "Iniciar: <nombre>" (Abrir / Levantar según el tipo), Detener mientras corre;
- estado (preparando / en marcha / terminó bien / no funcionó / detenido) con el tiempo;
- preparación del entorno con barra de progreso y lo que está haciendo pip traducido ("Descargando numpy…",
  "Compilando PyBullet…"); el registro crudo de pip, plegado;
- "Lo que dice el programa": la salida EN VIVO (seguir al final activable). Si la acción tiene `"entrada": true`, caja de
  texto para escribirle al programa (Enter envía);
- al fallar: resumen en lenguaje humano (falta un paquete, puerto serie ocupado, cámara, Docker cerrado, sin internet…)
  + las últimas líneas; la salida completa con la traza, plegada;
- "Detalles técnicos" plegado (comando, archivo, qué cubre).

`html`/`url`/`info` abren en una pestaña; `archivo` lo abre con el programa del sistema; `docker` muestra la salida de
`docker compose` en la página (comprueba Docker Desktop antes) y, si la acción tiene `"abrir"`, al terminar aparece el
botón para abrir esa dirección; su Detener corre el `"detener"` del probar.json. Si se recarga la página mientras la
acción corre, el panel se vuelve a enganchar a su salida.

Opciones (todas opcionales; los textos pueden ser texto, lista de textos o un nodo DOM):

| Opción | Qué |
|---|---|
| `titulo` | en vez del `nombre` de la acción |
| `queVaAPasar` | en vez de la `descripcion` (pon `""` para no mostrarlo) |
| `queHacer` | instrucciones de uso (teclas, botones de la ventana) |
| `queDeberiasVer` | qué debería verse si todo va bien |
| `alTerminarBien` | texto extra en el recuadro verde al terminar bien |
| `siFalla` | igual que `"si_falla"` del probar.json, pero desde la app (tiene prioridad) |
| `botonTexto` | texto del botón principal |
| `sugerencias` | lista de textos que salen como botones rápidos junto a la caja de entrada (p. ej. `["enciende el led"]`) |
| `alLinea(texto, tipo)` | cada línea (`tipo`: `prog` del programa, `sis` del lanzador, `in` lo que se envió) |
| `alEstado(trabajo)`, `alTerminar(trabajo)` | cambios de estado / final (`trabajo.estado`, `codigo`, `mensaje`) |

### Bajo nivel
- `App.accion(id, {alLinea, alEstado})` → promesa con el trabajo final (`estado`: `terminada`/`error`/`detenida`).
  `alLinea(texto, tipo, n)` recibe la salida en vivo. html/url se abren en el mismo clic.
- `App.detener(id)` → para la acción (mata el programa y sus hijos; en docker corre el `"detener"`).
- `App.entrada(id, texto)` → escribe `texto` + Enter en el stdin del programa (solo acciones con `"entrada": true`).
- `App.on("ok", f)` (una acción terminó bien: `f(accionId)`), `App.on("fin", f)`, `App.on("paso", f)`.
- `App.url("img/x.png")` → `/repo/<carpeta>/img/x.png`.

### `App.markdown(elemento, ruta, {desde, hasta, sinTitulo})`
Renderiza un trozo de un `.md` de la práctica (ruta relativa a su carpeta, p. ej. `"README.md"` o
`"punto-1/README.md"`). `desde: "## Qué es X"` empieza en ese título (basta el comienzo del texto, sin tildes ni
mayúsculas exactas); sin `hasta`, termina en el siguiente título del mismo nivel o mayor; `hasta: "## Otro"` corta
antes de ese. Arregla las rutas de imágenes y enlaces, dibuja los `mermaid` y deja las imágenes ampliables. Usa marked
y mermaid desde CDN; sin internet muestra el texto tal cual.

### `App.pasos(contenedor, {inicio, alCambiar})` → `{ir(i), siguiente(), anterior(), actual}`
Convierte los `<section class="paso" data-titulo="...">` del contenedor en un asistente: índice lateral numerado,
barra "Paso 2 de 5", Anterior / Siguiente. Recuerda el paso (localStorage) y acepta `#paso-3` en la URL.

### `App.checklist(elemento, {puntos})` → `{marcar(texto)}`
La lista `pide` del manifiesto con casillas. Un punto se marca solo cuando termina bien una acción que lo `cubre`
(o a mano). Se guarda en localStorage. Muestra "N de M probados" y con qué acción se prueba cada punto.

### `App.abrir(rutaOUrl)`, `App.imagen(elemento)`, `App.aviso(texto, tipo)`
- `abrir`: una URL `http(s)` o una ruta relativa a la práctica (`"img/montaje.jpg"`, `"README.md"`) en pestaña nueva.
- `imagen`: la imagen (o todas las de dentro del elemento) se amplía al hacer clic; Esc cierra.
- `aviso`: mensaje flotante; `tipo` = `"info"`, `"ok"`, `"aviso"` o `"error"`.

## Componentes CSS (`app.css`)

`.app-encabezado` (barra superior fija; `.app-num` y `h1`), `.app-contenedor`, `.app-portada` (texto + imagen),
`.app-seccion`, `.app-tarjetas` > `.app-tarjeta`, `.app-btn` (`.primario`, `.peligro`, `.app-btn-grande`,
`.app-btn-mini`), `.app-botones`, `.app-aviso` (`.ok`, `.error`, `.atencion`), `table.app-pines` dentro de
`.app-tabla-scroll`, `.app-chip`, `details.app-plegado`, `.app-etiqueta`, `.app-tenue`, `kbd`. Variables para la
identidad de cada app: `--acento`, `--acento-suave`, `--acento-fondo` (y el resto de `:root`).

## El lanzador es uno solo para todas las apps

Si ya hay un `probar.py` abierto con la misma carpeta raíz (en los puertos 8099-8108), `--practica` lo reutiliza: varias
apps y el hub comparten el mismo servidor. Consecuencias: (1) tras cambiar `probar.py` hay que cerrar el lanzador
abierto para que el código nuevo entre en uso (un lanzador viejo sin apps, sin `"api": 2` en `/api/ping`, no se
reutiliza); (2) "Cerrar lanzador" del hub avisa si hay acciones en marcha; (3) abierto con `--practica` y sin
`--no-navegador`, se cierra solo tras 10 minutos sin ninguna petición de ninguna página y sin nada en marcha. Los
archivos estáticos (`/repo/`, `/app/`) se sirven por bloques y con `Range` (206), así los `<video>` mp4 se reproducen y
se pueden adelantar.

## Probarla

```
python probar.py --practica <carpeta> --no-navegador      (imprime la URL)
node "D:\cosas uni\Micros\.claude\herramientas\captura-chrome.mjs" <url> captura.png 8000
```
