# `app-practica/`: la app del proyecto (la que abre `ABRIR.bat`)

La página amigable del proyecto, organizada como Docker Desktop: barra lateral con las vistas
(Inicio, Prueba visual, Programas, Cómo funciona, Visor sin instalar, Resultados, Qué pide el parcial,
Estado y documentos), la lista de programas con su estado y su salida, y la prueba visual (el recorrido
animado de una pieza por las 4 estaciones junto al estado real de la simulación). No es el paquete de
Python: ese es [`app/`](../app/README.md), y por eso esta carpeta se llama distinto.

## Cómo se abre

Doble clic en `ABRIR.bat` (Linux/Mac: `sh abrir.sh`). Por dentro, desde la raíz del repo:

```
python _lanzador/lanzador.py --practica proyecto-final
```

El lanzador común del repo ([`_lanzador/LEEME.md`](../../_lanzador/LEEME.md)) levanta un servidor solo
en `127.0.0.1` y sirve esta carpeta en `/app/proyecto-final/`, los archivos del proyecto en
`/repo/proyecto-final/...` y su API común en `/comun/app.js` y `/comun/app.css`. Lo encuentra por el
campo `"app": "app-practica/index.html"` de [`probar.json`](../probar.json).

## Archivos

| Archivo | Qué hace |
|---|---|
| `index.html` | Las vistas y sus textos; carga `/comun/app.css`, `./monedas.css`, `/comun/app.js` y `./monedas.js`. |
| `monedas.js` | El comportamiento: vistas, la animación del recorrido, el estado real de la simulación (`/api/estado` del visor), la lista de programas (cada uno es una acción de `probar.json`) y los trozos del README que muestra. |
| `monedas.css` | El estilo propio (dorado de moneda sobre el fondo oscuro común del repo). |

No lleva build ni dependencias: se edita el archivo y se recarga la página.

## Contratos con el resto del proyecto

- **Acciones de `probar.json`** por su `id`: `vivo`, `asistente`, `sim-filtro`, `sim-vasos`, `sim-carro`,
  `sim-todo`, `pruebas`, `chequeo` (lista `PROGRAMAS` de `monedas.js`) y `enunciado` (el botón
  "Enunciado (PDF)" de `index.html`). Cambiar un `id` allá obliga a cambiarlo aquí.
- **Títulos del README** del proyecto que se muestran con `App.markdown`: `## La idea general`,
  `### El recorrido de una moneda` y `## Estado del proyecto`.
- **Puertos de la simulación**: primero lee el real de `datos/puertos.json` (lo escribe
  `app/puertos.py`); si no está, prueba los 4 fijos de `monedas.js`: 8765 (`supervisor.puerto_http` de
  `config/parametros.yaml`) y 8766-8768 (el principio del rango de `app/puertos.py`). La página no lee
  la configuración (no hay build): si el puerto cambia allá, se cambia también aquí.
- **Enlace del dashboard**: sale de las líneas `Visor 3D en http://...` y `Dashboard en http://...` que
  imprime `app.lanzar`.
- **Rutas fijas** `/repo/proyecto-final/...` en `index.html` (videos, capturas): dependen del nombre de
  la carpeta del proyecto.
- El lanzador **no sirve** `.env*`, bases `.db`, `entorno/` ni los PDF `*umng.pdf`
  (`archivo_prohibido`): por eso el enunciado no se abre con `data-abrir` sino con la acción
  `enunciado`, que lo abre con el lector de PDF del sistema.

Revisar después de cambiar algo: `python _lanzador/lanzador.py --comprobar` (desde la raíz del repo)
y abrir la app a 1366x768 y 1920x1080 sin errores en la consola del navegador.
