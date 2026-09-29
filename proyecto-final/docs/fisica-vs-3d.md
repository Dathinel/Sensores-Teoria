# Física vs 3D

Qué tan igual es lo que **simula PyBullet** (lo que se mueve y choca de verdad) a lo que **dibuja el
visor 3D** (el boceto que ve el evaluador). Lo genera `python tests/sim/test_fisica_vs_3d.py`; las mismas
medidas son pruebas en `tests/sim/test_fisica_vs_3d.py` (corren con el resto de la suite).

Cómo se mide cada lado:

- **PyBullet**: se le PREGUNTA a PyBullet (formas de colisión, cajas envolventes, formas visuales de
  los URDF, masa de cada cuerpo) sobre los mismos mundos que usan las pruebas y el supervisor:
  `sim/urdf/*.urdf` + `sim/mundo.py` (cintas, monedas, vasos) y `sim/vehiculo_sim.py` (carro, muros,
  muelle). No se leen las constantes: se mide lo que quedó construido.
- **Visor**: lo que manda `sim/geometria.py` al visor (`/api/geometria`) y, donde el visor tiene
  números fijos (`app/visor3d/piezas/carro.js`, `visor.js`), esos números leídos con regex.
- **Física**: mundos chicos en `p.DIRECT` con las piezas reales: una moneda que cae a un tubo hueco
  del tamaño del del carrusel, el vaso colgando de los rieles de la canaleta, y el viaje completo
  del carro con el vaso lleno midiendo balanceo y cabeceo en cada paso de control.

## Tabla

| Medida | PyBullet | Visor / fuente | ¿Coincide? | Nota |
|---|---|---|---|---|
| Cinta de monedas: ancho de la banda | 55.0 mm | 55.0 mm | sí |  |
| Cinta de monedas: largo de la banda | 200.0 mm | 200.0 mm | sí | corregido el URDF (antes 160 mm) |
| Cinta de monedas: paso de casilla | 40.0 mm | 40.0 mm | sí |  |
| Cinta de vasos: ancho de la banda | 75.0 mm | 75.0 mm | sí |  |
| Cinta de vasos: largo de la banda | 395.0 mm | 400.0 mm | sí | URDF: 5 mm mas corta que la bancada (dentro de tolerancia) |
| Cinta de vasos: paso de casilla | 80.0 mm | 80.0 mm | sí |  |
| Estaciones de monedas (moneda real avanzada E1 -> E4) | error máx. 0.017 mm | sim/geometria.py | sí |  |
| Estaciones de vasos (vaso real avanzado 1 -> 5) | error máx. 0.056 mm | sim/geometria.py | sí |  |
| Tubos del carrusel (6): posición del fondo | error máx. 0.00 mm | posicion_tubo() | sí | corregido el URDF (antes centrados en el llenado) |
| Tubos del carrusel: radio exterior / alto | 15.5 mm / 58.0 mm | 15.5 mm / 58.0 mm | sí | corregido el alto (antes 65 mm) |
| Tolva: radio | 19.0 mm | 19.0 mm | sí | corregido el URDF (antes 50 mm) |
| Bandeja de rechazo de vasos (x, y) | (0.470, -0.100) m | (0.470, -0.100) m | sí | corregido el URDF (estaba al costado, a 10 cm de altura) |
| Moneda 50_nueva: masa / diámetro | 2.00 g / 17.00 mm | 2.00 g / 17.00 mm (monedas.yaml) | sí |  |
| Moneda 100_nueva: masa / diámetro | 3.30 g / 20.30 mm | 3.30 g / 20.30 mm (monedas.yaml) | sí |  |
| Moneda 200_nueva: masa / diámetro | 4.60 g / 22.40 mm | 4.60 g / 22.40 mm (monedas.yaml) | sí |  |
| Moneda 500_nueva: masa / diámetro | 7.10 g / 23.70 mm | 7.10 g / 23.70 mm (monedas.yaml) | sí |  |
| Moneda 1000_nueva: masa / diámetro | 10.00 g / 26.70 mm | 10.00 g / 26.70 mm (monedas.yaml) | sí |  |
| Moneda 50_antigua: masa / diámetro | 4.50 g / 21.50 mm | 4.50 g / 21.50 mm (monedas.yaml) | sí |  |
| Moneda 100_antigua: masa / diámetro | 5.30 g / 23.00 mm | 5.30 g / 23.00 mm (monedas.yaml) | sí |  |
| Moneda 200_antigua: masa / diámetro | 7.10 g / 24.40 mm | 7.10 g / 24.40 mm (monedas.yaml) | sí |  |
| Moneda 500_antigua: masa / diámetro | 7.40 g / 23.50 mm | 7.40 g / 23.50 mm (monedas.yaml) | sí |  |
| Física: 50_nueva soltada sobre el tubo | queda a 2.9 mm del eje, 1.0 mm sobre el fondo | tubo de 29 mm | sí |  |
| Física: 100_nueva soltada sobre el tubo | queda a 0.1 mm del eje, 1.0 mm sobre el fondo | tubo de 29 mm | sí |  |
| Física: 200_nueva soltada sobre el tubo | queda a 0.1 mm del eje, 0.9 mm sobre el fondo | tubo de 29 mm | sí |  |
| Física: 500_nueva soltada sobre el tubo | queda a 0.1 mm del eje, 1.0 mm sobre el fondo | tubo de 29 mm | sí |  |
| Física: 1000_nueva soltada sobre el tubo | queda a 0.1 mm del eje, 1.0 mm sobre el fondo | tubo de 29 mm | sí |  |
| Física: 50_antigua soltada sobre el tubo | queda a 2.4 mm del eje, 1.0 mm sobre el fondo | tubo de 29 mm | sí |  |
| Física: 100_antigua soltada sobre el tubo | queda a 0.1 mm del eje, 0.9 mm sobre el fondo | tubo de 29 mm | sí |  |
| Física: 200_antigua soltada sobre el tubo | queda a 0.1 mm del eje, 1.0 mm sobre el fondo | tubo de 29 mm | sí |  |
| Física: 500_antigua soltada sobre el tubo | queda a 0.1 mm del eje, 1.0 mm sobre el fondo | tubo de 29 mm | sí |  |
| Canaleta: separación entre rieles | 69.0 mm | 69 mm (config; el visor lee la geometría) | sí |  |
| Física: vaso (62 mm, pestaña 78 mm) en los rieles | boca -0.3 mm sobre el riel; desliza 144 mm en 0,35 s | cuelga y baja por la pendiente | sí |  |
| Física: el mismo vaso SIN pestaña | cae 593 mm entre los rieles | el cuerpo pasa entre los rieles | sí |  |
| Vaso entregado (donde lo deja sim/mundo.py) | boca +1.2 mm sobre el riel, inclinado 15.0° | apoyado en los rieles, canaleta a 15° | sí | corregido el 2026-09-28 (antes 21,7 mm por encima y derecho) |
| Carro: chasis largo × ancho | 180.0 mm × 120.0 mm | 180.0 mm × 120.0 mm | sí |  |
| Carro: diámetro de rueda | 65.0 mm | 65.0 mm | sí |  |
| Carro: ancho de rueda (banda de rodadura) | 26.0 mm (20.0 mm) | 26.0 mm (crearRuedaTT, config) | sí | corregido el 2026-09-28 (antes 22 mm) |
| Carro: eje de ruedas (x) | -32.4 mm | -32.4 mm (piezas/carro.js) | sí |  |
| Carro: centro de rueda (y) | 73.0 mm | 73.0 mm (piezas/carro.js) | sí |  |
| Carro: rueda loca (x) | 54.0 mm | 54.0 mm (piezas/carro.js) | sí |  |
| Carro: infrarrojos de línea (x) | 78.0 mm | 78.0 mm (piezas/carro.js) | sí |  |
| Carro: ultrasónico (z) | 56.5 mm | 56.5 mm (piezas/carro.js) | sí |  |
| Carro: láser VL53L0X (z) | 74.0 mm | 74.0 mm (piezas/carro.js) | sí |  |
| Muelle: largo de boca / apertura / holgura | 200.0 mm / 45.0 mm / 3.0 mm | 200.0 mm / 45.0 mm / 3.0 mm (config, visor.js la lee) | sí |  |
| Pista: largo de la línea central | 6.327 m | 6.327 m | sí |  |
| Muro 1: posición / grueso × largo × alto | (0.960, -0.658) / 30.0 mm × 100.0 mm × 80.0 mm | (0.960, -0.658) / 30.0 mm × 100.0 mm × 80.0 mm | sí |  |
| Muro 2: posición / grueso × largo × alto | (1.560, -0.657) / 30.0 mm × 100.0 mm × 80.0 mm | (1.560, -0.657) / 30.0 mm × 100.0 mm × 80.0 mm | sí |  |
| Muro 3: posición / grueso × largo × alto | (2.160, -0.659) / 30.0 mm × 100.0 mm × 80.0 mm | (2.160, -0.659) / 30.0 mm × 100.0 mm × 80.0 mm | sí |  |
| Física: viaje completo con el vaso lleno (semilla 7) | 6 evasiones, 0 toques, balanceo máx. 0.01°, cabeceo máx. 0.03°, vaso 0.72° | no vuelca, no toca muros | sí |  |

## Qué se corrigió (2026-09-28)

Todo en `sim/urdf/`, que son piezas que la simulación no usaba para decidir nada (visuales o una
banda más larga donde no hay nada) — la fuente de las medidas sigue siendo `sim/mundo.py` /
`sim/geometria.py`, y los URDF ahora las copian:

- **Tubos del carrusel** (`cinta_vasos.urdf`): estaban dibujados en un hexágono centrado en la
  estación de llenado y 7 mm más altos; `sim/mundo.py` guarda las monedas alrededor de
  `centro_carrusel()` (el agujero de la placa queda sobre el llenado, no el centro del carrusel).
  En la ventana de PyBullet las monedas guardadas quedaban FUERA de sus tubos. Ahora cada tubo está
  en `posicion_tubo()`, con 58 mm de alto (`TUBO_ALTO_M`) y 29 + 2 mm de diámetro, como el visor.
- **Tolva** (`cinta_vasos.urdf`): 50 mm de radio → 19 mm, entre las mismas alturas del visor.
- **Bandeja de rechazo de vasos** (`cinta_vasos.urdf`): estaba al costado de la descarga, a 10 cm de
  altura e inclinada (diseño viejo); ahora en el piso al final de la cinta, donde `sim/mundo.py`
  pone los vasos rechazados y donde la dibuja el visor.
- **Banda de la cinta de monedas** (`cinta_monedas.urdf`): 160 → 200 mm; arranca una casilla antes
  de E1, como el visor desde la revisión del 2026-09-26 (espacio para el capacitivo bajo E1).

Y después, en `sim/vehiculo_sim.py`, `sim/mundo.py` y la configuración (antes figuraban abajo, en lo
que NO se corrigió):

- **Llanta del carro y muelle (pedido 13a, 2026-09-28)**: PyBullet usaba una llanta de 22 mm y el
  visor la TT real de 26. Ahora las dos leen `vehiculo.ancho_rueda_mm: 26` de la configuración, y el
  muelle (largo de boca, apertura, holgura) también sale de ahí (`vehiculo.muelle_*`) en vez de
  estar copiado a mano en `visor.js`. Lo que se midió al pasar a 26 mm (56 viajes de ida y vuelta:
  44 semillas, 11 con el doble de error y uno sin error):
  - **El muelle no era el problema**: con 26 mm el carro entró al primer intento en los 56 (0
    reintentos) y la llanta nunca tocó una guía. Las "3 pruebas del muelle" que fallaban
    (`test_entra_al_muelle_sin_reintento` 1 y 6-doble, `test_ida_y_vuelta_con_...[1]`) fallaban por
    tocar un **muro** en la evasión, y la del atasco por llegar en otra pose.
  - **La causa**: un cilindro plano en PyBullet apoya en el piso por UNO de sus bordes y salta de
    uno al otro (contactos medidos a 60 y 86 mm del centro, nunca a 73). Con 26 mm el salto es de
    26 mm, la trocha efectiva cambia de un paso a otro y la odometría se corría más (error medio de
    `ir_a` desde el muelle: 46 → 62 mm en 16 semillas); con eso el carro volvía a la línea torcido
    y rozaba el extremo del muro. Arreglo físico: la llanta es una **banda de rodadura de 20 mm**
    (radio completo) con **hombros de 3 mm** 1,5 mm más chicos (`vehiculo.rodadura_rueda_mm`), como
    una goma real, y sigue midiendo 26 mm de cara a cara para los choques de costado. Con eso la
    odometría volvió a la de antes (46 mm) y 55 de 56 viajes no tocan nada (con la llanta vieja,
    53 de 56).
  - **Holgura en el muelle**: con la llanta 2 mm más ancha por lado, la llanta pasaba a 3,7 mm de la
    guía (antes 6,5). Se corrieron los **rodillos guía 2 mm por lado** (`rodillo_guia_y_mm` 86 → 88)
    y con ellos las guías (se ubican desde el rodillo): vuelven los 7 mm de diseño entre llanta y
    rodillo y la llanta pasa a ≥ 5,6 mm de la guía. La boca en V (20 cm, 4,5 cm por lado) no cambió:
    no hizo falta. El muelle queda 4 mm más ancho en total; en el visor no choca con la canaleta
    (el poste del escape queda 37 mm detrás del final de las guías).
- **Vaso entregado (pedido 13b, 2026-09-28)**: `sim/mundo.py` lo dejaba derecho y ~2 cm por encima
  de los rieles. Ahora lo apoya con la pestaña (78 mm) sobre los rieles (69 mm) a la distancia de
  siempre de la descarga, con la canaleta calculada de la configuración (`geometria_canaleta`, la
  misma que usa el visor) e **inclinado 15°**: así queda en la prueba física (la pestaña se acuesta
  sobre los dos rieles; medido 14,9°). Monedas y tapa se mueven con él. Es una pose colocada, no
  soltada: el vaso de la escena es un cilindro de 62 mm sin pestaña y la canaleta ahí es solo
  visual; que cuelga y desliza lo muestra la prueba física.

## Qué NO se corrigió (y por qué)

- **Chasis del carro**: en PyBullet es una caja de 180 × 120 × 24 mm centrada en el eje de las ruedas
  (una simplificación para la masa y los choques); en el visor la placa va 11,5 mm por encima del eje
  y encima va la electrónica. Largo y ancho coinciden; la altura no se compara porque la caja no es
  la placa.
- **Pestaña del vaso**: la configuración y el visor usan 62 + 2 × 8 = **78 mm**; el texto de
  `CLAUDE.md` (sección 6, "Modelo físico") decía "la pestaña del reborde, 72 mm" (corregido el 2026-09-28). Era un error del
  texto, no de la simulación (la prueba física usa 78 mm y el vaso cuelga).
- **Banda de la cinta de vasos**: 395 mm en el URDF y 400 mm en el visor (de separador a
  separador): 2,5 mm por lado, dentro de la tolerancia.
- **`control/vehiculo.py` sigue suponiendo la cara de afuera de la llanta a 84 mm** (`ancho / 2 +
  0.024`, en `holguras_carro` y `medio_ancho`) y no lee `ancho_rueda_mm`. No cambia nada hoy: lo más
  ancho del carro son los rodillos guía (93 mm), que sí lee de la configuración. Queda anotado para
  cuando se toque el control (fuera del alcance de este cambio).
