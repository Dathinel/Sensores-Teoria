# `simulaciones/`: un `.bat` por escena de PyBullet

Accesos directos de doble clic a las escenas en ventana de [`sim/ver/`](../sim/README.md#las-escenas-de-ver).
Lo normal es abrirlas desde el menú [`simulaciones.bat`](../simulaciones.bat), en la raíz del proyecto.
Necesitan el entorno instalado (`instalar.bat`).

| Archivo | Abre | Qué muestra |
|---|---|---|
| `1-filtro-monedas.bat` | `entorno\Scripts\python -m sim.ver.filtro_monedas` | El filtro de monedas (grupo 7): la cinta de monedas y el almacén con el escenario `mixto_20` |
| `2-embalaje-vasos.bat` | `entorno\Scripts\python -m sim.ver.embalaje_vasos` | Llenado, tapa, prensa, empujador, canaleta y los sabotajes |
| `3-carro-pista.bat` | `entorno\Scripts\python -m sim.ver.carro_pista` | El carro con física real: línea, 3 muros, meta y vuelta al muelle |
| `4-todo-junto.bat` | `entorno\Scripts\python -m sim.ver.todo_junto` | `prueba_completa`: la planta y el carro, en dos ventanas |

En la ventana: espacio pausa, `r` reinicia y `q` sale. Cada `.bat` le pasa sus argumentos a la escena,
y si la escena termina con error deja la consola abierta (`pause`):

```
simulaciones\1-filtro-monedas.bat --velocidad 2                 (el doble de rápido)
simulaciones\1-filtro-monedas.bat --sin-ventana --segundos 30   (comprobar sin abrir nada)
```

`simulaciones.bat` muestra un menú del 1 al 5: cada número del 1 al 4 llama al `.bat` del mismo número,
el 5 abre `docs\videos` (los videos que graba `entorno\Scripts\python -m sim.ver.grabar`) y el 0 sale.

## Reglas

- Cada `.bat` hace `cd /d "%~dp0.."`, así que esta carpeta tiene que quedar **un nivel debajo** de
  `proyecto-final/`. Si se mueve, hay que cambiar esa línea.
- `simulaciones.bat` llama a estos archivos por su nombre (`simulaciones\N-escena.bat`): si se renombra
  uno, hay que cambiarlo también en el menú.
- Los `.bat` se guardan con fin de línea CRLF (`*.bat text eol=crlf` en el `.gitattributes` del repo).
