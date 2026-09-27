# Costo del proyecto en Colombia

> Generado por `python -m app.documentos` desde `config/precios.yaml`: no editar a mano.
> Precios consultados el 2026-09-27 en pesos colombianos, sin envío. Cambian:
> verificarlos antes de comprar.

**Total del proyecto: $1.680.746** (sin el portátil, que es del grupo). De eso, $486.000 (28 %) son **estimados** (materiales sin un producto
igual publicado: banda de las cintas, tornillería, cables, tubos): el resto es precio de tienda.

## Por subsistema

| Subsistema | Costo | % |
|---|---:|---:|
| Cinta de monedas | $244.346 | 15 % |
| Cinta de vasos | $274.000 | 16 % |
| Canaleta y muelle | $36.000 | 2 % |
| Carro | $245.300 | 15 % |
| Control y potencia | $312.600 | 19 % |
| Estructura | $568.500 | 34 % |

## Dónde abaratar (propuestas, NO aplicadas)

El diseño no se cambia sin que el grupo lo apruebe. Riesgo bajo = mismo comportamiento; medio = funciona pero hay que medir algo; alto = cambia el diseño.

| Propuesta | Ahorro | Riesgo | Por qué |
|---|---:|---|---|
| Pórtico en tubo cuadrado de aluminio de ferretería en vez de perfil 2020 | $120.000 | medio | 3 m de perfil V-Slot cuestan ~170 700; tubo cuadrado de 3/4" cuesta ~15 000/m en ferretería. Se pierde lo modular (tuercas en T): hay que taladrar y ajustar alturas a mano. |
| NEMA 17 en Mercado Libre y no en tienda especializada | $41.800 | bajo | El mismo 17HS4401 cuesta 59 000 en Mercado Libre y 79 900 en Electronilab (x2). Ya está contado al precio bajo. |
| Quitar el sensor capacitivo | $40.606 | medio | Con el filtro total, que haya pieza ya lo dice el infrarrojo de presencia (E1); no metálico = presencia sí e inductivo no. Se ahorran el LJC18A3 (32 606) y un canal del optoacoplador (~8 000). Se pierde la segunda confirmación de que la pieza sigue en la casilla en E2. |
| Servos directo al PWM del ESP32 (sin PCA9685) | $29.500 | alto | El ESP32 tiene 16 canales LEDC, pero el fijo ya usa 19 de sus ~25 pines útiles: 6 servos más no caben sin quitar otra cosa. No recomendado. |
| Buck de 5 A (XL4015) en vez del XL4016 de 9 A para los servos | $16.900 | medio | Alcanza si prensa y empujador (MG996R, ~2,5 A de arranque cada uno) no arrancan a la vez; hoy la lógica los mueve en momentos distintos, pero hay que medir el pico real. |
| Webcam de 720p también en la cámara cenital | $15.000 | medio | La cámara cenital mide diámetros de monedas (±0,5 mm): con 720p a la misma altura la resolución baja de ~0,05 a ~0,08 mm/píxel. Probar con fotos reales antes (fase 5). |
| Comprar las 18650 en par | $4.000 | bajo | El par cuesta 60 000 contra 2 x 32 000. Ya está contado al precio del par. |

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

### Canaleta y muelle

| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |
|---|---|---:|---:|---:|---|
| Servo del escape de la canaleta | Servomotor SG90 | 1 | $11.000 | $11.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Canaleta de entrega | 2 varillas de 4 mm + cinta de PTFE *(estimado)* | 1 | $25.000 | $25.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Muelle de carga del carro | Impreso en 3D (el PLA va en extras) *(estimado)* | 1 | $0 | $0 | — |

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
| Cuna de carga (rieles) | Impresa en 3D (el PLA va en extras) *(estimado)* | 1 | $0 | $0 | — |
| Pista con 3 obstáculos y meta | Cinta aislante negra 3M 18 mm x 18 m | 1 | $11.000 | $11.000 | [Ferretrónica (Tunja](https://www.ferretronica.com) |
| Rueda loca | Rueda loca de bola de acero 3/4" | 1 | $9.500 | $9.500 | [Ferretrónica (Tunja](https://www.ferretronica.com) |

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
| Canaletas y prensaestopas | Canaleta ranurada 25 x 30 mm (1 m) + prensaestopas PG *(estimado)* | 1 | $25.000 | $25.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Portátil | El portátil del grupo (no se compra) | 1 | $0 | $0 | — |
| Cables | Cables dupont, cable 18 AWG, termoencogible, conectores JST *(estimado)* | 1 | $30.000 | $30.000 | — |

### Estructura

| Componente | Qué se compra | Cant. | Precio | Subtotal | Dónde |
|---|---|---:|---:|---:|---|
| Estructura de perfil de aluminio | Perfil V-Slot 2020 de 1 m (estimado: 3 m para patas y pórtico) | 3 | $56.900 | $170.700 | [Electronilab (Bogotá)](https://electronilab.co) |
| Cinta de monedas y su mesa | Banda de caucho negra mate 55 mm + 2 rodillos *(estimado)* | 1 | $40.000 | $40.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Cinta de vasos y su mesa | Banda de caucho 75 mm + 2 rodillos *(estimado)* | 1 | $45.000 | $45.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Almacén tipo revólver | 6 tubos de acrílico de 29 mm (el disco y la placa van en PLA) *(estimado)* | 1 | $30.000 | $30.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Tubo vertical de tapas | Tubo de acrílico de 78 mm *(estimado)* | 1 | $15.000 | $15.000 | [Mercado Libre Colombia](https://www.mercadolibre.com.co) |
| Bandeja de rechazo de monedas | Impresa en 3D (el PLA va en extras) *(estimado)* | 1 | $0 | $0 | — |
| Bandeja de rechazo de vasos | Impresa en 3D (el PLA va en extras) *(estimado)* | 1 | $0 | $0 | — |
| Embudo y canales de la descarga | Impreso en 3D (el PLA va en extras) *(estimado)* | 1 | $0 | $0 | — |
| Pla | Filamento PLA 1,75 mm 1 kg (estimado: 2 kg para todas las piezas impresas) | 2 | $93.900 | $187.800 | [Electronilab (Bogotá)](https://electronilab.co) |
| Tornilleria | Tornillos M3/M4/M5, tuercas en T, escuadras 2020 *(estimado)* | 1 | $40.000 | $40.000 | — |
| Base | Tablero MDF de 9 mm para la base y la pista *(estimado)* | 1 | $40.000 | $40.000 | — |

