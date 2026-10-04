Resultados reales de pruebas_algoritmo.py (2.5 s). 20 semillas (1 a 20), 3 nodos x 4 hormigas x 30 iteraciones = 360 hormigas por corrida. Regla de deposito: mejor.

### Prueba 6, laberinto abierto

Criterio: Con la semilla fija el camino de maxima feromona mide 8 pasos (1,60 m) y en al menos 95 % de 20 semillas se halla una ruta de 8 pasos.

| Caso | Halla el optimo | Iteracion media del hallazgo | Converge (max. feromona = optimo) | Iteracion media de convergencia | Hormigas descartadas (media de 360) |
|---|---|---|---|---|---|
| 20 semillas | 90 % | 1.78 | 90 % | 2.39 | 24 |

Semilla fija 12345: camino de maxima feromona de 8 pasos, 28 hormigas descartadas.

Con la regla anterior (depositan todas las hormigas que llegan):

| Caso | Halla el optimo | Iteracion media del hallazgo | Converge (max. feromona = optimo) | Iteracion media de convergencia | Hormigas descartadas (media de 360) |
|---|---|---|---|---|---|
| 20 semillas | 95 % | 2.21 | 90 % | 10.89 | 73.7 |

Semilla fija 12345 con la regla anterior: 12 pasos.

**Cumple: no**

### Prueba 7, unico camino

Criterio: En las 20 semillas se halla la unica ruta (12 pasos, 2,40 m), las hormigas que entran a un callejon se descartan, y las aristas de los callejones terminan sin ningun deposito (solo evaporacion).

| Caso | Halla el optimo | Iteracion media del hallazgo | Converge (max. feromona = optimo) | Iteracion media de convergencia | Hormigas descartadas (media de 360) |
|---|---|---|---|---|---|
| 20 semillas | 100 % | 1.4 | 100 % | 1.4 | 16.1 |

Semilla fija 12345: camino de maxima feromona de 12 pasos, 23 hormigas descartadas.

**Cumple: si**

### Prueba 8, dos caminos

Criterio: El camino de maxima feromona es el corto (8 pasos) con la semilla fija y en al menos 90 % de 20 semillas.

| Caso | Halla el optimo | Iteracion media del hallazgo | Converge (max. feromona = optimo) | Iteracion media de convergencia | Hormigas descartadas (media de 360) |
|---|---|---|---|---|---|
| 20 semillas | 100 % | 1 | 100 % | 1 | 0 |

Semilla fija 12345: camino de maxima feromona de 8 pasos, 0 hormigas descartadas.
Feromona media por arista al final (semilla fija): corto 375.00, largo 9.31e-10.

**Cumple: si**

### Prueba 9, maze.json

Criterio: Reportar tasa de convergencia e iteraciones medias en 20 semillas. Se acepta si la tasa de hallazgo del optimo es al menos 90 %.

| Caso | Halla el optimo | Iteracion media del hallazgo | Converge (max. feromona = optimo) | Iteracion media de convergencia | Hormigas descartadas (media de 360) |
|---|---|---|---|---|---|
| 20 semillas | 95 % | 1 | 95 % | 1.47 | 28.4 |

Con la regla anterior (depositan todas las hormigas que llegan):

| Caso | Halla el optimo | Iteracion media del hallazgo | Converge (max. feromona = optimo) | Iteracion media de convergencia | Hormigas descartadas (media de 360) |
|---|---|---|---|---|---|
| 20 semillas | 100 % | 1.05 | 95 % | 2.05 | 49.2 |

**Cumple: si**

### Prueba 10, barrido de rho (maze.json)

| Caso | Halla el optimo | Iteracion media del hallazgo | Converge (max. feromona = optimo) | Iteracion media de convergencia | Hormigas descartadas (media de 360) |
|---|---|---|---|---|---|
| rho = 0.1 | 95 % | 1 | 95 % | 1.37 | 60.2 |
| rho = 0.5 | 95 % | 1 | 95 % | 1.47 | 28.4 |
| rho = 0.9 | 95 % | 1 | 95 % | 1.47 | 16.6 |

### Prueba 11, barrido de alfa y beta (maze.json)

| Caso | Halla el optimo | Iteracion media del hallazgo | Converge (max. feromona = optimo) | Iteracion media de convergencia | Hormigas descartadas (media de 360) |
|---|---|---|---|---|---|
| alfa = 1.0, beta = 2.0 | 95 % | 1 | 95 % | 1.47 | 28.4 |
| alfa = 0.5, beta = 2.0 | 100 % | 1.1 | 100 % | 1.5 | 87.0 |
| alfa = 2.0, beta = 2.0 | 95 % | 1 | 95 % | 1.47 | 12.3 |
| alfa = 1.0, beta = 0.0 | 95 % | 1 | 95 % | 1.47 | 28.4 |
| alfa = 1.0, beta = 5.0 | 95 % | 1 | 95 % | 1.47 | 28.4 |
| alfa = 3.0, beta = 1.0 | 95 % | 1 | 90 % | 1.28 | 9.2 |
