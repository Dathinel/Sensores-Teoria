# Costo del proyecto en Colombia

> Generado por `python -m app.documentos` desde `config/precios.yaml`: no editar a mano.
> Precios consultados el 2026-09-27 en pesos colombianos, sin envío. Cambian:
> verificarlos antes de comprar.

**Total del proyecto: $1.387.143** (sin el portátil, que es del grupo). De eso, $688.197 (49 %) son **estimados** (materiales sin un producto
igual publicado: banda de las cintas, tornillería, cables, piezas impresas, la fuente de 5 A y el buck XL4015): el resto es precio de tienda.

La **estructura 3D** (la maqueta impresa, las piezas impresas del carro y de la caja y la tornillería) cuesta **$306.197** (22 % del total): detalle más abajo.

## Por subsistema

| Subsistema | Costo | % |
|---|---:|---:|
| Cinta de monedas | $292.937 | 21 % |
| Cinta de vasos | $351.656 | 25 % |
| Canaleta y muelle | $55.283 | 4 % |
| Carro | $253.036 | 18 % |
| Control y potencia | $197.152 | 14 % |
| Estructura | $237.079 | 17 % |
| **Total** | **$1.387.143** | **100 %** |

## Ahorros ya aplicados (aprobados el 2026-10-24)

"Es un proyecto universitario, no un sistema industrial": lo que el usuario aprobó ya está en el diseño, en la simulación eléctrica, en el firmware y en el total de arriba.

| Cambio | Ahorro | Riesgo | Por qué alcanza |
|---|---:|---|---|
| Estructura impresa (maqueta_impresa/) en vez de perfil 2020, escuadras, pies, placas de aluminio, acrílico y MDF | $495.478 | medio | Antes: 7 barras de V-Slot (398 300), tornillería con 24 escuadras, 15 pies y tuercas en T (219 280), las piezas impresas sueltas de la planta (90 507), tubos de acrílico (45 000) y tablero MDF (40 000) = 793 087. Ahora: la maqueta impresa (los gramos y horas de maqueta_impresa/piezas.json, a precio de PLA + energía) y la tornillería que no va remachada (12 150). Lo funcional no cambia; los remaches se prueban al imprimir (maqueta_impresa/README.md). |
| Fuente de 12 V 5 A en vez de 10 A | $31.000 | bajo | Pico simulado del +12 V: 3,3 A; peor caso con el XL4015 en su límite de corriente: 4,1 A. El precio de la de 5 A es estimado. |
| Empalmes soldados en vez de la bornera X2, los optoacopladores y el reparto I2C | $27.000 | bajo | Misma topología (GND en estrella en los bornes -V de la fuente). Los M18 van al GPIO con un diodo BAT85 y una pull-up de 10 kΩ (sigue activo en bajo); el bus I2C 1 con sus dos pull-ups de 2,2 kΩ en línea. Se pierde el aislamiento del optoacoplador y desarmar es con cautín. |
| Sin hub USB: ESP32 y webcams directo al portátil | $23.500 | bajo | Hacen falta 3 puertos USB libres en el portátil; ninguno pide más de 0,35 A (un USB 2.0 da 0,5 A). |
| Buck de 5 A (XL4015) en vez del XL4016 de 9 A para los servos | $16.900 | medio | Pico simulado del riel de 6 V: 3,9 A (prensa apretando la tapa). Prensa y empujador nunca arrancan a la vez (firmware/fijo/estacion.py, EXCLUYENTES, con su prueba). Medir el pico real en el montaje. |
| Bridas con bases adhesivas en vez de canaletas ranuradas y prensaestopas | $11.000 | bajo | 25 000 de canaleta y prensaestopas contra 14 000 de bridas, bases y el ventilador (que antes no estaba contado). El ventilador se queda: los A4988 van a 1 A por fase, el límite sin aire forzado (docs/electrica.md). |
| Un fusible principal y cable de poder a una multitoma con interruptor (sin IEC ni 4 portafusibles) | $6.900 | bajo | 9 200 de 4 portafusibles + 6 000 de la entrada IEC contra 2 300 de un portafusible + 6 000 del cable con enchufe. El fusible de 5 A cubre el pico simulado del +12 V (3,3 A) y el peor caso (4,1 A). |
| **Total ahorrado** | **$611.778** | | |

## Dónde abaratar (propuestas, NO aplicadas)

El diseño no se cambia sin que el grupo lo apruebe. Riesgo bajo = mismo comportamiento; medio = funciona pero hay que medir algo; alto = cambia el diseño.

| Propuesta | Ahorro | Riesgo | Por qué |
|---|---:|---|---|
| NEMA 17 en Mercado Libre y no en tienda especializada | $41.800 | bajo | El mismo 17HS4401 cuesta 59 000 en Mercado Libre y 79 900 en Electronilab (x2). Ya está contado al precio bajo. |
| Quitar el sensor capacitivo | $40.606 | medio | Con el filtro total, que haya pieza ya lo dice el infrarrojo de presencia (E1); no metálico = presencia sí e inductivo no. Se ahorran el LJC18A3 (32 606) y un canal del optoacoplador (~8 000). Se pierde la segunda confirmación de que la pieza sigue en la casilla en E2. |
| Servos directo al PWM del ESP32 (sin PCA9685) | $29.500 | alto | El ESP32 tiene 16 canales LEDC, pero el fijo ya usa 19 de sus ~25 pines útiles: 6 servos más no caben sin quitar otra cosa. No recomendado. |
| Webcam de 720p también en la cámara cenital | $15.000 | medio | La cámara cenital mide diámetros de monedas (±0,5 mm): con 720p a la misma altura la resolución baja de ~0,05 a ~0,08 mm/píxel. Probar con fotos reales antes (fase 5). |
| Comprar las 18650 en par | $4.000 | bajo | El par cuesta 60 000 contra 2 x 32 000. Ya está contado al precio del par. |

## Estructura 3D (maqueta impresa, piezas impresas y tornillería)

Desde el 2026-10-24 la estructura de la planta es la **maqueta impresa** ([maqueta_impresa/](../maqueta_impresa/README.md)): mesas, pórtico, soportes, almacén, mecanismos y canaleta en PLA, unidos con remaches impresos. Ya no hay perfil 2020, escuadras, pies niveladores, placas de aluminio, acrílico ni tablero MDF (la maqueta va sobre la mesa y la pista sobre el piso o la mesa). Lo comprado sigue comprado: bandas, rodillos, ejes, rodamientos, varillas, motores, servos, sensores y cámaras. Ya está dentro del total de arriba (en su subsistema).

| Parte | Qué es | Costo | % de la estructura 3D |
|---|---|---:|---:|
| Maqueta impresa | 539 piezas (con los remaches), 2.681 g de PLA, 81,0 h de impresora | $285.459 | 93 % |
| Otras piezas impresas (carro y caja) | 11 piezas, 83 g de PLA, 8,3 h de impresora | $8.588 | 3 % |
| Tornillería | 77 unidades (con repuesto) | $12.150 | 4 % |
| **Total estructura 3D** | | **$306.197** | 100 % |

### Maqueta impresa por grupo

Gramos y horas del exportador de la maqueta (`maqueta_impresa/piezas.json`, la masa de cada pieza con sus parámetros de capa, paredes y relleno; el tiempo real lo da el laminador). Costo = gramos x (1 + desperdicio) x $93.900/kg + horas x (1 + desperdicio) x 0,12 kWh/h x $800/kWh, con el 10% de desperdicio (purga e impresiones fallidas).

| Grupo | Subsistema | Piezas | Gramos | Horas | Filamento | Energía | Costo |
|---|---|---:|---:|---:|---:|---:|---:|
| Estructura: nodos | Estructura | 22 | 400 | 12,0 | $41.368 | $1.269 | $42.637 |
| Estructura: tubos de 16 x 16 | Estructura | 46 | 747 | 19,3 | $77.116 | $2.035 | $79.152 |
| Estructura: empalmes y tacos | Estructura | 11 | 114 | 3,4 | $11.806 | $364 | $12.170 |
| Remaches impresos | Estructura | 369 | 50 | 8,1 | $5.119 | $851 | $5.970 |
| Cinta de monedas | Cinta de monedas | 22 | 284 | 8,9 | $29.314 | $936 | $30.250 |
| Almacén de monedas | Cinta de monedas | 9 | 173 | 4,6 | $17.859 | $482 | $18.341 |
| Cinta de vasos | Cinta de vasos | 26 | 524 | 13,1 | $54.165 | $1.388 | $55.554 |
| Tapas, prensa y empujador | Cinta de vasos | 19 | 208 | 6,0 | $21.464 | $638 | $22.102 |
| Canaleta y muelle | Canaleta y muelle | 15 | 181 | 5,6 | $18.695 | $587 | $19.283 |
| **Total** | | **539** | **2.681** | **81,0** | **$276.906** | **$8.552** | **$285.458** |

Filamento de todo lo impreso (maqueta + carro + caja, con el desperdicio): 3,03 kg → **4 rollo(s) de 1 kg**.

### Cómo se calcula una pieza impresa suelta (carro y caja)

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

### Piezas impresas sueltas (carro y caja de control)

| Pieza | Dónde | Cant. | Medidas (mm) | Volumen (cm³) | Llenado | g c/u | h c/u | Costo c/u | Subtotal |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| Cuna del vaso (mampara, postes, brazos, asientos, lengüeta) | Carro | 1 | 111 x 112 x 89 | 37,5 | 100% | 51,2 | 5,12 | $5.294 | $5.294 |
| Escuadra frontal del HC-SR04 y el VL53L0X | Carro | 1 | 51 x 20 x 34 | 6,3 | 100% | 8,6 | 0,86 | $889 | $889 |
| Soporte del encoder H206 | Carro | 2 | 11 x 9 x 32 | 1,0 | 100% | 1,4 | 0,14 | $141 | $282 |
| Brazo del rodillo guía trasero | Carro | 2 | 40 x 14 x 12 | 3,0 *(est.)* | 100% | 4,1 | 0,41 | $424 | $847 |
| Caja del interruptor y el fusible | Carro | 1 | 36 x 16 x 12 | 3,0 *(est.)* | 100% | 4,1 | 0,41 | $424 | $424 |
| Taco de esquina de la tapa de la caja | Caja de control | 4 | 14 x 14 x 15 | 2,9 | 52% | 2,1 | 0,21 | $213 | $852 |
| **Total** | | **11** | | | | **83 g** | **8,3 h** | | **$8.588** |

**Cómo** (piezas con volumen estimado o sumado de varias mallas):

- Cuna del vaso (mampara, postes, brazos, asientos, lengüeta): suma de las mallas impresas de la cuna: mampara 19,3 + base 1,8 + 2 x 6,5 de postes y asientos + lengüeta 0,6 + 2,8 de detalles.
- Brazo del rodillo guía trasero: bloque atornillado + brazo de 4 mm (la malla incluye los rodamientos).
- Caja del interruptor y el fusible: caja de 36 x 16 x 12 hueca con pared de 2 mm (la malla es un sólido).

### Tornillería

La maqueta va remachada (sin escuadras, pies ni tuercas en T): solo se atornilla lo comprado que lo pide (los NEMA 17 y los rodamientos KFL08; los servos traen los tornillos de su kit) y las piezas impresas del carro y de la caja (columna `tornillos` en precios.yaml). Se compra un 10% de repuesto.

| Qué | Contados | A comprar | Precio | Subtotal |
|---|---:|---:|---:|---:|
| Tornillo M5 x 16 cabeza Allen (rodamientos KFL08) *(estimado)* | 8 | 9 | $400 | $3.600 |
| Tuerca M5 *(estimado)* | 8 | 9 | $100 | $900 |
| Tornillo M4 x 12 *(estimado)* | 4 | 5 | $250 | $1.250 |
| Tuerca M4 *(estimado)* | 4 | 5 | $80 | $400 |
| Tornillo M3 x 10 *(estimado)* | 24 | 27 | $150 | $4.050 |
| Tornillo M3 x 30 *(estimado)* | 2 | 3 | $250 | $750 |
| Tuerca M3 *(estimado)* | 12 | 14 | $50 | $700 |
| Tornillo M2 x 8 autorroscante (servos, placas) *(estimado)* | 4 | 5 | $100 | $500 |
| **Total** | **66** | **77** | | **$12.150** |

Por zona (contados, sin repuesto):

- Cinta de monedas: 4 tornillo m3 x 10
- Cinta de vasos: 4 tornillo m3 x 10, 8 tornillo m5 x 16 cabeza allen, 8 tuerca m5
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
| Bandeja de rechazo de monedas | Impresa en la maqueta: canal y bandeja (fila Maqueta impresa de la cinta de monedas) *(estimado)* | 1 | $0 | $0 | — |
| Embudo y canales de la descarga | Impreso en la maqueta: embudo y canales (fila Maqueta impresa de la cinta de monedas) *(estimado)* | 1 | $0 | $0 | — |
| Maqueta impresa | Piezas de PLA de la maqueta impresa: cinta de monedas (284 g), almacén de monedas (173 g); 13,4 h de impresora *(estimado)* | 1 | $48.591 | $48.591 | [Electronilab (Bogotá)](https://electronilab.co) |
| **Subtotal** | | | | **$292.937** | |

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
| Bandeja de rechazo de vasos | Impresa en la maqueta (fila Maqueta impresa de la cinta de vasos) *(estimado)* | 1 | $0 | $0 | — |
| Maqueta impresa | Piezas de PLA de la maqueta impresa: cinta de vasos (524 g), tapas, prensa y empujador (208 g); 19,2 h de impresora *(estimado)* | 1 | $77.656 | $77.656 | [Electronilab (Bogotá)](https://electronilab.co) |
| **Subtotal** | | | | **$351.656** | |

### Canaleta y muelle

| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |
|---|---|---:|---:|---:|---|
| Servo del escape de la canaleta | Servomotor SG90 | 1 | $11.000 | $11.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Canaleta de entrega | 2 varillas de 4 mm + cinta de PTFE *(estimado)* | 1 | $25.000 | $25.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Muelle de carga del carro | Impreso en la maqueta: guías en V y topes (fila Maqueta impresa de la canaleta) *(estimado)* | 1 | $0 | $0 | — |
| Maqueta impresa | Piezas de PLA de la maqueta impresa: canaleta y muelle (181 g); 5,6 h de impresora *(estimado)* | 1 | $19.283 | $19.283 | [Electronilab (Bogotá)](https://electronilab.co) |
| **Subtotal** | | | | **$55.283** | |

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
| Fuente de 12 V | Fuente conmutada 12 V 5 A 60 W de caja metálica (genérica; VERIFICAR el precio) *(estimado)* | 1 | $38.000 | $38.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Regulador de 6 V (servos) | Convertidor XL4015 5 A CC/CV (el de la propuesta de ahorro; VERIFICAR) *(estimado)* | 1 | $13.000 | $13.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Regulador de 5 V | Módulo LM2596 (sin voltímetro) | 1 | $7.000 | $7.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Fusible principal | 1 portafusible (el mismo de 2 300 de antes) con fusible de 5 A lento | 1 | $2.300 | $2.300 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Empalmes soldados | 2 diodos Schottky BAT85 + 2 resistencias de 10 kΩ + 2 de 2,2 kΩ (el estaño y el termoencogible van en Cables) *(estimado)* | 1 | $1.000 | $1.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Cable de poder de la fuente | Cable de poder de 3 hilos con enchufe, 1,5 m (o el de un aparato viejo); va a una multitoma con interruptor del grupo *(estimado)* | 1 | $6.000 | $6.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Driver del carrusel | Viene con el 28BYJ-48 (ya contado en el motor del carrusel) | 1 | $0 | $0 | — |
| Bridas y ventilador | 100 bridas de 10 cm (~4 000) + 10 bases adhesivas (~4 000) + ventilador 4010 de 5 V (~6 000) *(estimado)* | 1 | $14.000 | $14.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Portátil | El portátil del grupo (no se compra) | 1 | $0 | $0 | — |
| Cables | Cables dupont, cable 18 AWG, termoencogible, conectores JST *(estimado)* | 1 | $30.000 | $30.000 | — |
| Otras piezas impresas | 4 piezas en PLA (8 g, 0,8 h de impresora): soportes, bridas, bloques (tabla de piezas impresas) *(estimado)* | 1 | $852 | $852 | [Electronilab (Bogotá)](https://electronilab.co) |
| **Subtotal** | | | | **$197.152** | |

### Estructura

| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |
|---|---|---:|---:|---:|---|
| Estructura impresa (maqueta_impresa/) | Maqueta impresa: tubos, nodos, empalmes y remaches de PLA: 1.311 g de PLA, 42,8 h de impresora *(estimado)* | 1 | $139.929 | $139.929 | [Electronilab (Bogotá)](https://electronilab.co) |
| Cinta de monedas y su mesa | Banda de caucho negra mate 55 mm + 2 rodillos *(estimado)* | 1 | $40.000 | $40.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Cinta de vasos y su mesa | Banda de caucho 75 mm + 2 rodillos *(estimado)* | 1 | $45.000 | $45.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Almacén tipo revólver | Impreso en la maqueta (tubos, disco, placa, obturador y embudo: ya no hay acrílico) *(estimado)* | 1 | $0 | $0 | — |
| Tubo vertical de tapas | Impreso en la maqueta (ya no es de acrílico) *(estimado)* | 1 | $0 | $0 | — |
| Tornillo M5 x 16 cabeza Allen (rodamientos KFL08) | 8 contados + 10% de repuesto *(estimado)* | 9 | $400 | $3.600 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tuerca M5 | 8 contados + 10% de repuesto *(estimado)* | 9 | $100 | $900 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tornillo M4 x 12 | 4 contados + 10% de repuesto *(estimado)* | 5 | $250 | $1.250 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tuerca M4 | 4 contados + 10% de repuesto *(estimado)* | 5 | $80 | $400 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tornillo M3 x 10 | 24 contados + 10% de repuesto *(estimado)* | 27 | $150 | $4.050 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tornillo M3 x 30 | 2 contados + 10% de repuesto *(estimado)* | 3 | $250 | $750 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tuerca M3 | 12 contados + 10% de repuesto *(estimado)* | 14 | $50 | $700 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Tornillo M2 x 8 autorroscante (servos, placas) | 4 contados + 10% de repuesto *(estimado)* | 5 | $100 | $500 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| **Subtotal** | | | | **$237.079** | |

