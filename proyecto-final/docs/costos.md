# Costo del proyecto en Colombia

> Generado por `python -m app.documentos` desde `config/precios.yaml`: no editar a mano.
> Precios consultados el 2026-09-27 en pesos colombianos, sin envío. Cambian:
> verificarlos antes de comprar.

**Total del proyecto: $1.998.921** (sin el portátil, que es del grupo). De eso, $764.375 (38 %) son **estimados** (materiales sin un producto
igual publicado: banda de las cintas, tornillería, cables, tubos, piezas impresas): el resto es precio de tienda.

La **estructura 3D** (piezas impresas, perfil 2020 y tornillería, contadas en el modelo) cuesta **$716.675** (36 % del total): detalle más abajo.

## Por subsistema

| Subsistema | Costo | % |
|---|---:|---:|
| Cinta de monedas | $276.058 | 14 % |
| Cinta de vasos | $312.373 | 16 % |
| Canaleta y muelle | $56.422 | 3 % |
| Carro | $253.036 | 13 % |
| Control y potencia | $313.452 | 16 % |
| Estructura | $787.580 | 39 % |
| **Total** | **$1.998.921** | **100 %** |

## Dónde abaratar (propuestas, NO aplicadas)

El diseño no se cambia sin que el grupo lo apruebe. Riesgo bajo = mismo comportamiento; medio = funciona pero hay que medir algo; alto = cambia el diseño.

| Propuesta | Ahorro | Riesgo | Por qué |
|---|---:|---|---|
| Pórtico en tubo cuadrado de aluminio de ferretería en vez de perfil 2020 | $290.000 | medio | Los 6,1 m de perfil medidos en el modelo 3D salen en 7 barras de V-Slot (398 300); 7 m de tubo cuadrado de 3/4" cuestan ~105 000 en ferretería (~15 000/m, estimado). Se pierde lo modular (tuercas en T): hay que taladrar y ajustar alturas a mano, y las escuadras de fundición ya no sirven tal cual. |
| NEMA 17 en Mercado Libre y no en tienda especializada | $41.800 | bajo | El mismo 17HS4401 cuesta 59 000 en Mercado Libre y 79 900 en Electronilab (x2). Ya está contado al precio bajo. |
| Quitar el sensor capacitivo | $40.606 | medio | Con el filtro total, que haya pieza ya lo dice el infrarrojo de presencia (E1); no metálico = presencia sí e inductivo no. Se ahorran el LJC18A3 (32 606) y un canal del optoacoplador (~8 000). Se pierde la segunda confirmación de que la pieza sigue en la casilla en E2. |
| Servos directo al PWM del ESP32 (sin PCA9685) | $29.500 | alto | El ESP32 tiene 16 canales LEDC, pero el fijo ya usa 19 de sus ~25 pines útiles: 6 servos más no caben sin quitar otra cosa. No recomendado. |
| Buck de 5 A (XL4015) en vez del XL4016 de 9 A para los servos | $16.900 | medio | Alcanza si prensa y empujador (MG996R, ~2,5 A de arranque cada uno) no arrancan a la vez; hoy la lógica los mueve en momentos distintos, pero hay que medir el pico real. |
| Webcam de 720p también en la cámara cenital | $15.000 | medio | La cámara cenital mide diámetros de monedas (±0,5 mm): con 720p a la misma altura la resolución baja de ~0,05 a ~0,08 mm/píxel. Probar con fotos reales antes (fase 5). |
| Comprar las 18650 en par | $4.000 | bajo | El par cuesta 60 000 contra 2 x 32 000. Ya está contado al precio del par. |

## Estructura 3D (piezas impresas, perfil 2020 y tornillería)

Contada sobre el modelo 3D del visor (medido el 2026-09-28): cada pieza impresa con su volumen, cada tramo de perfil con su largo y cada tornillo por pieza. Ya está dentro del total de arriba (en su subsistema).

| Parte | Qué es | Costo | % de la estructura 3D |
|---|---|---:|---:|
| Piezas impresas | 73 piezas, 957 g de PLA, 95,7 h de impresora | $99.095 | 14 % |
| Perfil 2020 | 6,10 m en 31 tramos → 7 barras de 1 m | $398.300 | 56 % |
| Tornillería, escuadras y pies | 446 unidades (con repuesto) | $219.280 | 31 % |
| **Total estructura 3D** | | **$716.675** | 100 % |

### Cómo se calcula una pieza impresa

```
gramos = V x ρ x f x (1 + desperdicio)
  V   = volumen de material de la pieza en el modelo (cm³)
  ρ   = 1,24 g/cm³ (PLA)
  f   = 1 si la pieza es maciza (pared ≤ 3 mm: los 3 perímetros la llenan)
      = paredes + (1 - paredes) x relleno = 0,40 + 0,60 x 0,20 = 0,52 si es gruesa
  desperdicio = 10% (purga, falda, soportes, alguna fallida)
horas = gramos / 10 g/h
costo = gramos x $93.900/kg  +  horas x 0,12 kWh/h x $800/kWh
```

*Estimados*: el 40% de cáscara, 10 g/h, 0,12 kWh/h y la tarifa de $800/kWh (mírela en su recibo). Volumen "malla" = medido sumando los tetraedros de la malla del visor; "estimado" = calculado a mano con superficie x pared (la columna *Cómo* dice la cuenta).

### Piezas impresas

| Pieza | Dónde | Cant. | Medidas (mm) | Volumen (cm³) | Llenado | g c/u | h c/u | Costo c/u | Subtotal |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| Bloque del rodamiento 608 (rodillo motriz) | Cinta de monedas | 2 | 30 x 22 x 12 | 6,6 | 52% | 4,7 | 0,47 | $485 | $969 |
| Bloque tensor del rodamiento 608 | Cinta de monedas | 2 | 44 x 22 x 12 | 8,0 | 52% | 5,7 | 0,57 | $587 | $1.175 |
| Jaula del NEMA 17 de la cinta de monedas | Cinta de monedas | 1 | 78 x 50 x 47 | 27,8 | 52% | 19,7 | 1,97 | $2.041 | $2.041 |
| Guía lateral de la banda de monedas | Cinta de monedas | 2 | 200 x 6 x 2 | 2,4 | 100% | 3,3 | 0,33 | $339 | $678 |
| Brazo de las platinas M18 (capacitivo e inductivo) | Cinta de monedas | 4 | 14 x 95 x 3 | 4,0 | 100% | 5,5 | 0,55 | $565 | $2.259 |
| Taco de las platinas M18 | Cinta de monedas | 2 | 14 x 20 x 3 | 0,8 | 100% | 1,1 | 0,11 | $113 | $226 |
| Abrazadera de la cámara cenital | Cinta de monedas | 1 | 30 x 24 x 6 | 4,3 *(est.)* | 100% | 5,9 | 0,59 | $607 | $607 |
| Aleta de la compuerta de desvío (E4) | Cinta de monedas | 1 | 34 x 26 x 19 | 1,5 | 100% | 2,0 | 0,20 | $212 | $212 |
| Brida de servo SG90 (desvío y obturador) | Cinta de monedas | 2 | 12 x 40 x 19 | 1,5 | 100% | 2,0 | 0,20 | $212 | $424 |
| Taco del poste de la compuerta E4 | Cinta de monedas | 1 | 20 x 20 x 4 | 1,6 | 100% | 2,2 | 0,22 | $226 | $226 |
| Embudo de la descarga de la cinta | Cinta de monedas | 1 | 40 x 40 x 26 | 5,0 *(est.)* | 100% | 6,8 | 0,68 | $706 | $706 |
| Canal corto al carrusel / al rechazo | Cinta de monedas | 2 | 60 x 20 x 15 | 6,0 *(est.)* | 100% | 8,2 | 0,82 | $847 | $1.694 |
| Oreja de la bisagra de la compuerta | Cinta de monedas | 1 | 3 x 12 x 7 | 0,2 | 100% | 0,3 | 0,03 | $35 | $35 |
| Canal largo a la bandeja de rechazo | Cinta de monedas | 1 | 38 x 353 x 105 | 39,1 | 100% | 53,3 | 5,33 | $5.520 | $5.520 |
| Bandeja de rechazo de monedas | Cinta de monedas | 1 | 90 x 90 x 35 | 51,0 *(est.)* | 100% | 69,6 | 6,96 | $7.200 | $7.200 |
| Placa fija del almacén (con el agujero) | Almacén | 1 | 116 x 116 x 15 | 57,1 | 52% | 40,5 | 4,05 | $4.192 | $4.192 |
| Disco del carrusel (6 agujeros y cubo) | Almacén | 1 | 146 x 146 x 11 | 18,2 | 52% | 12,9 | 1,29 | $1.336 | $1.336 |
| Obturador del almacén | Almacén | 1 | 46 x 59 x 6 | 2,6 | 100% | 3,5 | 0,35 | $367 | $367 |
| Placa del motor del carrusel (28BYJ-48) | Almacén | 1 | 42 x 56 x 13 | 11,9 | 52% | 8,4 | 0,84 | $874 | $874 |
| Embudo corto del almacén al vaso | Almacén | 1 | 38 x 38 x 32 | 6,0 *(est.)* | 100% | 8,2 | 0,82 | $847 | $847 |
| Portacables del servo del obturador | Almacén | 1 | 11 x 10 x 35 | 0,9 | 100% | 1,2 | 0,12 | $127 | $127 |
| Taco separador de la banda de vasos | Cinta de vasos | 7 | 47 x 75 x 15 | 17,4 | 52% | 12,3 | 1,23 | $1.277 | $8.941 |
| Placa del NEMA 17 de la cinta de vasos | Cinta de vasos | 1 | 50 x 48 x 6 | 12,0 *(est.)* | 52% | 8,5 | 0,85 | $881 | $881 |
| Cabezal del escape de tapas | Cinta de vasos | 1 | 92 x 92 x 16 | 21,8 | 52% | 15,5 | 1,55 | $1.600 | $1.600 |
| Abrazadera del tubo con el servo de tapas | Cinta de vasos | 1 | 94 x 94 x 10 | 11,3 | 52% | 8,0 | 0,80 | $830 | $830 |
| Balancín y dedos del escape de tapas | Cinta de vasos | 1 | 34 x 31 x 9 | 2,1 | 100% | 2,9 | 0,29 | $296 | $296 |
| Leva excéntrica de la prensa | Cinta de vasos | 1 | 44 x 44 x 8 | 12,1 | 52% | 8,6 | 0,86 | $888 | $888 |
| Pistón de la prensa | Cinta de vasos | 1 | 62 x 62 x 96 | 27,3 | 52% | 19,4 | 1,94 | $2.004 | $2.004 |
| Buje guía del pistón | Cinta de vasos | 1 | 22 x 20 x 16 | 7,0 | 52% | 5,0 | 0,50 | $514 | $514 |
| Bloque de las varillas guía de la prensa | Cinta de vasos | 1 | 57 x 18 x 10 | 10,3 | 52% | 7,3 | 0,73 | $756 | $756 |
| Orejas y bridas del MG996R de la prensa | Cinta de vasos | 1 | 42 x 25 x 29 | 16,9 | 100% | 23,1 | 2,31 | $2.386 | $2.386 |
| Manivela del empujador | Cinta de vasos | 1 | 15 x 46 x 11 | 3,0 | 100% | 4,1 | 0,41 | $424 | $424 |
| Paleta del empujador | Cinta de vasos | 1 | 60 x 18 x 130 | 34,3 | 52% | 24,3 | 2,43 | $2.518 | $2.518 |
| Porta-sensor del VL53L0X del interior | Cinta de vasos | 1 | 30 x 7 x 14 | 1,1 | 100% | 1,5 | 0,15 | $155 | $155 |
| Placa de la cámara de vasos (sobre su poste) | Cinta de vasos | 1 | 24 x 36 x 4 | 3,3 *(est.)* | 100% | 4,5 | 0,45 | $466 | $466 |
| Bandeja de rechazo de vasos | Cinta de vasos | 1 | 104 x 124 x 60 | 100,0 *(est.)* | 100% | 136,4 | 13,64 | $14.117 | $14.117 |
| Soporte de la bandeja de rechazo de vasos | Cinta de vasos | 1 | 33 x 41 x 75 | 11,3 | 100% | 15,4 | 1,54 | $1.595 | $1.595 |
| Cabezal del riel de la canaleta | Canaleta y muelle | 4 | 41 x 20 x 15 | 9,5 | 52% | 6,7 | 0,67 | $697 | $2.790 |
| Balancín de dos dedos del escape | Canaleta y muelle | 1 | 42 x 27 x 85 | 3,6 | 100% | 4,9 | 0,49 | $508 | $508 |
| Soporte del SG90 del escape | Canaleta y muelle | 1 | 18 x 29 x 38 | 5,3 | 100% | 7,2 | 0,72 | $748 | $748 |
| Guía en V del muelle (tramo recto + V) | Canaleta y muelle | 2 | 61 x 204 x 20 | 46,6 | 100% | 63,6 | 6,36 | $6.579 | $13.157 |
| Tope del muelle con refuerzo | Canaleta y muelle | 2 | 34 x 45 x 28 | 11,4 | 100% | 15,5 | 1,55 | $1.609 | $3.219 |
| Cuna del vaso (mampara, postes, brazos, asientos, lengüeta) | Carro | 1 | 111 x 112 x 89 | 37,5 | 100% | 51,2 | 5,12 | $5.294 | $5.294 |
| Escuadra frontal del HC-SR04 y el VL53L0X | Carro | 1 | 51 x 20 x 34 | 6,3 | 100% | 8,6 | 0,86 | $889 | $889 |
| Soporte del encoder H206 | Carro | 2 | 11 x 9 x 32 | 1,0 | 100% | 1,4 | 0,14 | $141 | $282 |
| Brazo del rodillo guía trasero | Carro | 2 | 40 x 14 x 12 | 3,0 *(est.)* | 100% | 4,1 | 0,41 | $424 | $847 |
| Caja del interruptor y el fusible | Carro | 1 | 36 x 16 x 12 | 3,0 *(est.)* | 100% | 4,1 | 0,41 | $424 | $424 |
| Taco de esquina de la tapa de la caja | Caja de control | 4 | 14 x 14 x 15 | 2,9 | 52% | 2,1 | 0,21 | $213 | $852 |
| **Total** | | **73** | | | | **957 g** | **95,7 h** | | **$99.095** |

**Cómo** (piezas con volumen estimado o sumado de varias mallas):

- Abrazadera de la cámara cenital: bloque de 30 x 24 x 6 mm (medidas del modelo) = 4,3 cm³.
- Embudo de la descarga de la cinta: cono de Ø40 a Ø12 en 26 mm con pared de 2 mm: π·(20 + 6)·29 mm² x 2 mm ≈ 4,7 cm³ (la malla no es cerrada).
- Canal corto al carrusel / al rechazo: U de 60 mm de largo, fondo de 20 y alas de 15, pared de 2 mm: 60 x (20 + 2·15) x 2 = 6 cm³.
- Bandeja de rechazo de monedas: fondo de 90 x 90 + 4 paredes de 90 x 35, pared de 2,5 mm: (8100 + 12600) mm² x 2,5 ≈ 51 cm³ (la malla cuenta también el rótulo).
- Embudo corto del almacén al vaso: cono de Ø38 a Ø30 en 32 mm, pared de 2 mm: π·(19 + 15)·32 x 2 ≈ 6,8 cm³ (la malla es un sólido).
- Placa del NEMA 17 de la cinta de vasos: placa de 50 x 48 x 6 menos el agujero Ø23 del motor: 14,4 - 2,5 ≈ 12 cm³ (la malla del grupo incluye el motor).
- Orejas y bridas del MG996R de la prensa: suma de las 8 mallas impresas del soporte: 2 x 2,9 + 4,6 + 1,9 + 0,7 + 2 x 0,3 + 3,3.
- Placa de la cámara de vasos (sobre su poste): 24 x 36 x 4 mm menos el agujero del tornillo de 1/4 de pulgada.
- Bandeja de rechazo de vasos: fondo de 104 x 124 + paredes de 2·(104 + 124) x 60, pared de 2,5 mm: 40 300 mm² x 2,5 ≈ 100 cm³ (la malla del grupo cuenta el rótulo).
- Guía en V del muelle (tramo recto + V): malla del tramo en V (30,4) + la del tramo recto (16,2).
- Tope del muelle con refuerzo: bloque 7,8 + pie 2,9 + refuerzo 0,7.
- Cuna del vaso (mampara, postes, brazos, asientos, lengüeta): suma de las mallas impresas de la cuna: mampara 19,3 + base 1,8 + 2 x 6,5 de postes y asientos + lengüeta 0,6 + 2,8 de detalles.
- Brazo del rodillo guía trasero: bloque atornillado + brazo de 4 mm (la malla incluye los rodamientos).
- Caja del interruptor y el fusible: caja de 36 x 16 x 12 hueca con pared de 2 mm (la malla es un sólido).

Filamento: 0,96 kg → **1 rollo(s) de 1 kg** (antes se estimaban 2).

### Perfil 2020 por tramo

Largo medido en el modelo; se compra en barras de 1000 mm con 3 mm por corte de sierra.

| Tramo | Zona | Cant. | Largo (mm) | Subtotal (mm) |
|---|---|---:|---:|---:|
| Larguero del riel de la cinta de monedas | Cinta de monedas | 2 | 251 | 502 |
| Pata de la mesa de monedas | Cinta de monedas | 3 | 418 | 1254 |
| Travesaño de la cola (a lo ancho) | Cinta de monedas | 1 | 61 | 61 |
| Travesaño lateral (a lo largo) | Cinta de monedas | 1 | 155 | 155 |
| Poste de la compuerta de desvío E4 | Cinta de monedas | 1 | 377 | 377 |
| Poste de la cámara cenital | Cinta de monedas | 1 | 240 | 240 |
| Brazo de la cámara cenital | Cinta de monedas | 1 | 70 | 70 |
| Pata de la mesa de vasos | Cinta de vasos | 4 | 88 | 352 |
| Larguero de la mesa de vasos | Cinta de vasos | 2 | 340 | 680 |
| Travesaño de la mesa de vasos | Cinta de vasos | 2 | 40 | 80 |
| Poste de la cámara de vasos | Cinta de vasos | 1 | 190 | 190 |
| Columna del pórtico | Pórtico | 2 | 398 | 796 |
| Viga del pórtico (a 40 cm) | Pórtico | 1 | 330 | 330 |
| Poste alto de la canaleta | Canaleta y muelle | 2 | 163 | 326 |
| Poste bajo de la canaleta | Canaleta y muelle | 2 | 137 | 274 |
| Travesaño de la canaleta | Canaleta y muelle | 2 | 105 | 210 |
| Larguero de la canaleta | Canaleta y muelle | 2 | 78 | 156 |
| Poste del escape de la canaleta | Canaleta y muelle | 1 | 43 | 43 |
| **Total** | | **31** | | **6096** |

**Despiece** (primero el tramo más largo, en la primera barra donde quepa): 7 barras, sobran 811 mm en total.

- Barra 1: 418 + 418 + 155 mm
- Barra 2: 418 + 398 + 163 mm
- Barra 3: 398 + 377 + 190 mm
- Barra 4: 340 + 340 + 251 + 43 mm
- Barra 5: 330 + 251 + 240 + 163 mm
- Barra 6: 137 + 137 + 105 + 105 + 88 + 88 + 88 + 88 + 78 + 40 mm
- Barra 7: 78 + 70 + 61 + 40 mm

### Tornillería, escuadras y pies niveladores

Contado por pieza: las uniones de la estructura (escuadras con 2 tornillos M5 y 2 tuercas en T cada una; un pie nivelador por pata o poste) y los tornillos de cada pieza impresa (columna `tornillos` en precios.yaml). Se compra un 10% de repuesto.

| Qué | Contados | A comprar | Precio | Subtotal |
|---|---:|---:|---:|---:|
| Escuadra 2020 de fundición *(estimado)* | 24 | 27 | $2.500 | $67.500 |
| Pie nivelador M6 Ø26 con contratuerca *(estimado)* | 15 | 17 | $3.500 | $59.500 |
| Tuerca en T M5 (martillo) para 2020 *(estimado)* | 71 | 79 | $450 | $35.550 |
| Tornillo M5 x 8 ISO 7380 (escuadras) *(estimado)* | 48 | 53 | $300 | $15.900 |
| Tornillo M5 x 10 cabeza Allen *(estimado)* | 29 | 32 | $350 | $11.200 |
| Tornillo M4 x 12 (o autorroscante para MDF) *(estimado)* | 24 | 27 | $250 | $6.750 |
| Tuerca M4 *(estimado)* | 10 | 11 | $80 | $880 |
| Tornillo M3 x 10 *(estimado)* | 80 | 88 | $150 | $13.200 |
| Tornillo M3 x 30 *(estimado)* | 8 | 9 | $250 | $2.250 |
| Tuerca M3 *(estimado)* | 68 | 75 | $50 | $3.750 |
| Tornillo M2 x 8 autorroscante (servos, placas) *(estimado)* | 25 | 28 | $100 | $2.800 |
| **Total** | **402** | **446** | | **$219.280** |

Por zona (contados, sin repuesto):

- Cinta de monedas: 5 escuadra 2020 de fundición, 10 tornillo m5 x 8 iso 7380, 24 tuerca en t m5, 4 pie nivelador m6 ø26 con contratuerca, 15 tornillo m5 x 10 cabeza allen, 2 tornillo m3 x 30, 26 tuerca m3, 28 tornillo m3 x 10, 6 tornillo m2 x 8 autorroscante
- Cinta de vasos: 9 escuadra 2020 de fundición, 18 tornillo m5 x 8 iso 7380, 21 tuerca en t m5, 4 pie nivelador m6 ø26 con contratuerca, 30 tornillo m3 x 10, 30 tuerca m3, 4 tornillo m3 x 30, 11 tornillo m2 x 8 autorroscante, 6 tornillo m4 x 12, 4 tuerca m4, 3 tornillo m5 x 10 cabeza allen
- Pórtico: 2 escuadra 2020 de fundición, 4 tornillo m5 x 8 iso 7380, 4 tuerca en t m5, 2 pie nivelador m6 ø26 con contratuerca
- Canaleta y muelle: 8 escuadra 2020 de fundición, 16 tornillo m5 x 8 iso 7380, 16 tuerca en t m5, 5 pie nivelador m6 ø26 con contratuerca, 5 tornillo m5 x 10 cabeza allen, 4 tornillo m3 x 10, 3 tornillo m2 x 8 autorroscante, 12 tornillo m4 x 12
- Almacén: 6 tornillo m5 x 10 cabeza allen, 6 tuerca en t m5, 2 tornillo m3 x 10, 1 tornillo m2 x 8 autorroscante, 2 tornillo m4 x 12, 2 tuerca m4
- Carro: 16 tornillo m3 x 10, 12 tuerca m3, 4 tornillo m2 x 8 autorroscante, 2 tornillo m3 x 30
- Caja de control: 4 tornillo m4 x 12, 4 tuerca m4

## Detalle

### Cinta de monedas

| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |
|---|---|---:|---:|---:|---|
| Motor de la cinta de monedas | Motor NEMA 17 17HS4401 1,7 A | 1 | $59.000 | $59.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Infrarrojo de presencia | Módulo de proximidad infrarrojo (FC-51) | 1 | $5.000 | $5.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Sensor capacitivo | Sensor capacitivo LJC18A3-B-Z/BX NPN | 1 | $32.606 | $32.606 | [Didácticas Electrónicas (Medellín)](https://www.didacticaselectronicas.com) |
| Sensor inductivo | Sensor inductivo LJ18A3-8 (8 mm, M18, NPN) | 1 | $21.740 | $21.740 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Cámara cenital | Webcam USB 1080p (~60 000) + anillo de luz LED (~20 000) *(estimado)* | 1 | $80.000 | $80.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Servo de la compuerta de desvío (E4) | Servomotor SG90 | 1 | $11.000 | $11.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Motor del carrusel del almacén | Motor 28BYJ-48 + driver ULN2003 | 1 | $19.000 | $19.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Sensor Hall del carrusel | Módulo efecto Hall 3144 (+ imán de neodimio ~1 000) | 1 | $5.000 | $5.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Servo del obturador del almacén | Servomotor SG90 | 1 | $11.000 | $11.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Bandeja de rechazo de monedas | Impresa en 3D: canal y bandeja (estructura_3d.piezas_impresas): 123 g de PLA *(estimado)* | 1 | $12.720 | $12.720 | [Electronilab (Bogotá)](https://electronilab.co) |
| Embudo y canales de la descarga | Impreso en 3D: embudo, canales cortos y oreja (estructura_3d.piezas_impresas): 24 g de PLA *(estimado)* | 1 | $2.435 | $2.435 | [Electronilab (Bogotá)](https://electronilab.co) |
| Otras piezas impresas | 24 piezas en PLA (160 g, 16,0 h de impresora): soportes, bridas, bloques (tabla de piezas impresas) *(estimado)* | 1 | $16.557 | $16.557 | [Electronilab (Bogotá)](https://electronilab.co) |
| **Subtotal** | | | | **$276.058** | |

### Cinta de vasos

| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |
|---|---|---:|---:|---:|---|
| Motor de la cinta de vasos | Motor NEMA 17 17HS4401 1,7 A | 1 | $59.000 | $59.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Cámara de vasos (silueta, ArUco y tapa) | Webcam USB 720p *(estimado)* | 1 | $45.000 | $45.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Panel de luz de la cámara de vasos | Tira LED 5 V blanca 1 m + acrílico opalino 33 x 11 cm *(estimado)* | 1 | $35.000 | $35.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Sensor del interior del vaso | Sensor de distancia VL53L0X | 1 | $25.000 | $25.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Cortina de seguridad | Sensor de distancia VL53L0X | 1 | $25.000 | $25.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Servo del escape de tapas | Servomotor SG90 | 1 | $11.000 | $11.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Servo de la prensa | Servomotor MG996R | 1 | $37.000 | $37.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Servo del empujador de descarga | Servomotor MG996R | 1 | $37.000 | $37.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Bandeja de rechazo de vasos | Impresa en 3D (estructura_3d.piezas_impresas): 152 g de PLA *(estimado)* | 1 | $15.713 | $15.713 | [Electronilab (Bogotá)](https://electronilab.co) |
| Otras piezas impresas | 20 piezas en PLA (219 g, 21,9 h de impresora): soportes, bridas, bloques (tabla de piezas impresas) *(estimado)* | 1 | $22.660 | $22.660 | [Electronilab (Bogotá)](https://electronilab.co) |
| **Subtotal** | | | | **$312.373** | |

### Canaleta y muelle

| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |
|---|---|---:|---:|---:|---|
| Servo del escape de la canaleta | Servomotor SG90 | 1 | $11.000 | $11.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Canaleta de entrega | 2 varillas de 4 mm + cinta de PTFE *(estimado)* | 1 | $25.000 | $25.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Muelle de carga del carro | Impreso en 3D: guías en V y topes (estructura_3d.piezas_impresas): 158 g de PLA *(estimado)* | 1 | $16.376 | $16.376 | [Electronilab (Bogotá)](https://electronilab.co) |
| Otras piezas impresas | 6 piezas en PLA (39 g, 3,9 h de impresora): soportes, bridas, bloques (tabla de piezas impresas) *(estimado)* | 1 | $4.046 | $4.046 | [Electronilab (Bogotá)](https://electronilab.co) |
| **Subtotal** | | | | **$56.422** | |

### Carro

| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |
|---|---|---:|---:|---:|---|
| ESP32 del carro | ESP32 DevKit 30 pines CH340 | 1 | $34.900 | $34.900 | [Electronilab (Bogotá)](https://electronilab.co) |
| Motorreductores del carro | Motorreductor TT amarillo 1:48 con llanta | 2 | $12.000 | $24.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Encoders de las ruedas | Sensor de herradura F249 (6 000) + disco de 20 ranuras (1 500) | 2 | $7.500 | $15.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Arreglo de 5 infrarrojos de línea | Módulo de seguimiento TCRT5000 de 5 canales | 1 | $15.900 | $15.900 | [Electronilab (Bogotá)](https://electronilab.co) |
| Ultrasónico frontal (respaldo) | HC-SR04 | 1 | $7.500 | $7.500 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Láser de distancia frontal | Sensor de distancia VL53L0X | 1 | $25.000 | $25.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Infrarrojo de la cuna de carga | Módulo TCRT5000 | 1 | $6.000 | $6.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Puente H del carro | Módulo puente H TB6612FNG | 1 | $15.000 | $15.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Batería del carro | Par de 18650 2500 mAh (60 000) + portapilas 2S (3 500) + BMS 2S (8 000) | 1 | $71.500 | $71.500 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Interruptor y fusible del carro | Interruptor de palanca + portafusible aéreo con fusible 3 A *(estimado)* | 1 | $4.000 | $4.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Rodillos guía traseros | Rodamiento 623 (10 mm) *(estimado)* | 2 | $3.000 | $6.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Cuna de carga (rieles) | Impresa en 3D: sus piezas en estructura_3d.piezas_impresas: 51 g de PLA *(estimado)* | 1 | $5.294 | $5.294 | [Electronilab (Bogotá)](https://electronilab.co) |
| Pista con 3 obstáculos y meta | Cinta aislante negra 3M 18 mm x 18 m | 1 | $11.000 | $11.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Rueda loca | Rueda loca de bola de acero 3/4" | 1 | $9.500 | $9.500 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Otras piezas impresas | 6 piezas en PLA (24 g, 2,4 h de impresora): soportes, bridas, bloques (tabla de piezas impresas) *(estimado)* | 1 | $2.442 | $2.442 | [Electronilab (Bogotá)](https://electronilab.co) |
| **Subtotal** | | | | **$253.036** | |

### Control y potencia

| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |
|---|---|---:|---:|---:|---|
| ESP32 fijo (estación) | ESP32 DevKit 38 pines CH9102F | 1 | $39.500 | $39.500 | [Electronilab (Bogotá)](https://electronilab.co) |
| Drivers de las dos cintas (M y V) | Driver A4988 | 2 | $8.000 | $16.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Controlador de servos | Controlador de 16 servos PCA9685 | 1 | $29.500 | $29.500 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Fuente de 12 V | Fuente conmutada 12 V 10 A 120 W | 1 | $69.000 | $69.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Regulador de 6 V (servos) | Convertidor XL4016 9 A 300 W | 1 | $29.900 | $29.900 | [Electronilab (Bogotá)](https://electronilab.co) |
| Regulador de 5 V | Módulo LM2596 (sin voltímetro) | 1 | $7.000 | $7.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Portafusibles | 4 portafusibles de chasis (2 300 c/u) con sus fusibles | 1 | $9.200 | $9.200 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Bornera X2 (carril DIN) | Regleta de 16 bornes con puentes *(estimado)* | 1 | $15.000 | $15.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Entrada de red con interruptor | Conector IEC C14 con interruptor y portafusible *(estimado)* | 1 | $6.000 | $6.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Optoacopladores | Módulo optoacoplador PC817 de 2 canales | 1 | $8.000 | $8.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Reparto del bus I2C 1 | Placa perforada + resistencias 2,2 kΩ + conectores *(estimado)* | 1 | $5.000 | $5.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Driver del carrusel | Viene con el 28BYJ-48 (ya contado en el motor del carrusel) | 1 | $0 | $0 | — |
| Hub USB con fuente | Hub USB de 4 puertos con entrada de alimentación | 1 | $23.500 | $23.500 | [Electronilab (Bogotá)](https://electronilab.co) |
| Canaletas, prensaestopas y ventilador | Canaleta ranurada 25 x 30 mm (1 m) + prensaestopas PG *(estimado)* | 1 | $25.000 | $25.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Portátil | El portátil del grupo (no se compra) | 1 | $0 | $0 | — |
| Cables | Cables dupont, cable 18 AWG, termoencogible, conectores JST *(estimado)* | 1 | $30.000 | $30.000 | — |
| Otras piezas impresas | 4 piezas en PLA (8 g, 0,8 h de impresora): soportes, bridas, bloques (tabla de piezas impresas) *(estimado)* | 1 | $852 | $852 | [Electronilab (Bogotá)](https://electronilab.co) |
| **Subtotal** | | | | **$313.452** | |

### Estructura

| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |
|---|---|---:|---:|---:|---|
| Estructura de perfil de aluminio | Perfil V-Slot 2020 en barras de 1 m (despiece de los tramos medidos en el modelo 3D) | 7 | $56.900 | $398.300 | [Electronilab (Bogotá)](https://electronilab.co) |
| Cinta de monedas y su mesa | Banda de caucho negra mate 55 mm + 2 rodillos *(estimado)* | 1 | $40.000 | $40.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Cinta de vasos y su mesa | Banda de caucho 75 mm + 2 rodillos *(estimado)* | 1 | $45.000 | $45.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Almacén tipo revólver | 6 tubos de acrílico de 29 mm (el disco y la placa van en PLA) *(estimado)* | 1 | $30.000 | $30.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Tubo vertical de tapas | Tubo de acrílico de 82 mm de diámetro interior (tapa de 78 mm + 4) *(estimado)* | 1 | $15.000 | $15.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Base | Tablero MDF de 9 mm para la base y la pista *(estimado)* | 1 | $40.000 | $40.000 | — |
| Escuadra 2020 de fundición | 24 contados en el modelo + 10% de repuesto *(estimado)* | 27 | $2.500 | $67.500 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Pie nivelador M6 Ø26 con contratuerca | 15 contados en el modelo + 10% de repuesto *(estimado)* | 17 | $3.500 | $59.500 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Tuerca en T M5 (martillo) para 2020 | 71 contados en el modelo + 10% de repuesto *(estimado)* | 79 | $450 | $35.550 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Tornillo M5 x 8 ISO 7380 (escuadras) | 48 contados en el modelo + 10% de repuesto *(estimado)* | 53 | $300 | $15.900 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tornillo M5 x 10 cabeza Allen | 29 contados en el modelo + 10% de repuesto *(estimado)* | 32 | $350 | $11.200 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tornillo M4 x 12 (o autorroscante para MDF) | 24 contados en el modelo + 10% de repuesto *(estimado)* | 27 | $250 | $6.750 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tuerca M4 | 10 contados en el modelo + 10% de repuesto *(estimado)* | 11 | $80 | $880 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tornillo M3 x 10 | 80 contados en el modelo + 10% de repuesto *(estimado)* | 88 | $150 | $13.200 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tornillo M3 x 30 | 8 contados en el modelo + 10% de repuesto *(estimado)* | 9 | $250 | $2.250 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tuerca M3 | 68 contados en el modelo + 10% de repuesto *(estimado)* | 75 | $50 | $3.750 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tornillo M2 x 8 autorroscante (servos, placas) | 25 contados en el modelo + 10% de repuesto *(estimado)* | 28 | $100 | $2.800 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| **Subtotal** | | | | **$787.580** | |

