# `app/dashboard/`: el dashboard de Streamlit

El tablero de la corrida: cifras, monedas y vasos, calidad del filtro, la línea en vivo, las pruebas
y sabotajes, el carro con su ruta, el montaje real, el asistente y una ayuda. Qué debe mostrar:
[§13 de la especificación](../../docs/especificacion.md#13-dashboard-en-streamlit). Inventario de
cada función y qué prueba la cubre: [`docs/interfaz-dashboard.md`](../../docs/interfaz-dashboard.md).

## Cómo se abre

Lo normal es con el supervisor, todo junto (desde `proyecto-final/`):

```
python -m app.lanzar --auto prueba_completa --abrir-dashboard   # lo que hace visor.bat
```

Solo el dashboard, con el supervisor corriendo en otra consola (`python -m app.supervisor --auto prueba_completa`):

```
python -m app.dashboard                         # = python -m streamlit run app/dashboard/inicio.py
python -m app.dashboard --server.port 8502      # los argumentos pasan a Streamlit
```

Puerto 8501 (o el siguiente libre, lo elige `app/lanzar.py`). `?pestana=<clave>` en la URL abre una
pestaña: `resumen`, `monedas` (o `produccion`), `calidad` (`rechazos`, `inspeccion`), `linea`,
`pruebas`, `carro` (`ruta`), `montaje` (`replicacion`), `asistente`, `ayuda`. El tema sale de
`.streamlit/config.toml`, que Streamlit lee del directorio de trabajo: por eso `lanzar.py` lo arranca
con `cwd` en `proyecto-final/`.

## Archivos

| Archivo | Qué hace |
|---|---|
| `inicio.py` | Punto de entrada: pone la raíz en `sys.path`, la lista `PESTANAS` y dibuja solo la pestaña abierta. No se llama `app.py`: Streamlit pone su carpeta primera en `sys.path` y taparía al paquete `app`. |
| `__main__.py` | `python -m app.dashboard`: corre `streamlit run inicio.py` con los argumentos que se le pasen. |
| `__init__.py` | El índice de módulos (docstring). |
| `estilo.py` | Sistema de diseño: colores, CSS, tarjetas, chips, avisos, tema de Plotly. El mismo lenguaje visual que `app/visor3d/estilo.css`. |
| `datos.py` | Todo lo que se lee (SQLite, el servidor del supervisor, la configuración) y `enviar()`, la única forma de escribir: una orden en la tabla `ordenes`. |
| `textos.py` | Nombres en español simple de cada estado, causa y evento, y la frase que cuenta cada evento. |
| `dibujos.py` | Las cintas, el almacén y los vasos dibujados en HTML. |
| `cabecera.py` | Título, chips de estado y los avisos grandes (NO ES EN VIVO, ESP32 EMULADO, SIN INTERNET...). |
| `controles.py` | Barra lateral: solo manejar la línea (empezar, pausa, paro, velocidad, monedas por vaso). |
| `pestanas/` | Una pestaña por módulo, cada uno con `pestana()`: `resumen`, `monedas`, `calidad`, `linea`, `pruebas`, `carro`, `montaje`, `asistente`, `ayuda`. |

## Reglas

- Este proceso **solo lee** SQLite y escribe órdenes por `datos.enviar()` (§8). No importa PyBullet
  ni pyserial ni corre la línea: eso es del supervisor, en otro proceso.
- Las pestañas no escriben SQL: piden a `datos.py` lo que necesitan.
- Refresco con `st.fragment(run_every=dashboard.refresco_s)` (1 s, `config/parametros.yaml`), sin
  bucles infinitos; gráficas con Plotly.
- Pestaña nueva: un módulo en `pestanas/` con `pestana()`, una fila en `PESTANAS` de `inicio.py` y su
  entrada en `PESTANAS` y `CONTENIDO` de `tests/app/test_dashboard.py`.
- `app/lanzar.py` reconoce el dashboard de una corrida vieja por `app/dashboard` en la línea de
  comandos: no renombrar la carpeta ni `inicio.py` (la prueba lo exige).
- `lanzar.py` lo arranca con `--server.address 127.0.0.1`: en Windows, escuchando en IPv6, Streamlit
  deja de atender sin morir (y así el tablero no queda abierto a la red del salón).

Pruebas: `entorno\Scripts\python -m pytest -q tests/app/test_dashboard.py` (AppTest de Streamlit,
cada pestaña sin datos y con una corrida completa).
