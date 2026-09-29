<!-- Generado por `python -m app.documentos`. No editar a mano. -->


# Componentes (lista de materiales)

46 piezas más los 13 sensores de [sensores.md](sensores.md). Son 6 servos: caben en un solo PCA9685 de 16 canales (sobran 10). En el visor 3D, pestaña **Componentes**, cada uno se resalta en la escena (`http://localhost:8765/?componente=<id>`).

**Estado en la simulación** (calculado en `sim/catalogos.py`, no escrito a mano): *simulado* = la simulación hace lo que hace la pieza; *efecto simulado* = su efecto lo hace otra pieza en la simulación (los drivers: la cinta avanza igual); *solo visual* = nada en la simulación depende de ella. La columna **Hilos** cuenta su conexionado pin a pin ([conexiones.md](conexiones.md)).

## Actuadores

| Componente | Cant. | Modelo propuesto | Para qué sirve | Estado | Hilos |
|---|---|---|---|---|---|
| Motor de la cinta de monedas (`motor_cinta_monedas`) | 1 | NEMA17 17HS4401 (PROVISIONAL) | Avanza la cinta de monedas una casilla (40 mm) y se detiene (sección 4). | simulado | 4 |
| Motor de la cinta de vasos (`motor_cinta_vasos`) | 1 | NEMA17 17HS4401 (PROVISIONAL) | Avanza la cinta de vasos una casilla (80 mm). | simulado | 4 |
| Servo de la compuerta de desvío (E4) (`servo_desvio_e7`) | 1 | SG90 | Filtro total: es la ÚNICA salida de rechazo de la cinta de monedas. En reposo manda todo a la bandeja de rechazo (a prueba de fallas); solo abre hacia el almacén para una moneda registrada y aceptada. Reemplaza a los dos expulsores laterales (grupo, 2026-09-25). | simulado | 3 |
| Motor del carrusel del almacén (`motor_carrusel`) | 1 | 28BYJ-48 (5 V, con reducción) + driver ULN2003 | Gira el carrusel de 6 tubos: pone el tubo de cada moneda bajo el punto de carga y, para soltar un lote, ese tubo sobre el agujero de la placa. Reemplaza al servo del selector y a los 6 servos de compuerta. | simulado | 5 |
| Servo del obturador del almacén (`servo_obturador`) | 1 | SG90 | Abre el único agujero de la placa fija (sobre el vaso de llenado) para soltar el lote del tubo que el carrusel puso encima; cerrado, el carrusel puede girar sin que se caiga nada. | simulado | 3 |
| Servo del escape de tapas (`servo_tapas`) | 1 | SG90 | Suelta una tapa del tubo vertical sobre el vaso. | simulado | 3 |
| Servo de la prensa (`motor_prensa`) | 1 | MG996R (~10 kg·cm) con leva excéntrica de 6,5 mm y resorte | Gira la leva 0 → 180 → 0 grados: el pistón baja 13 mm y asienta la tapa. Con 6,5 mm de excentricidad apunta a 60 N: la tapa sella a presión (snap-fit) y pide ~30-50 N, PROVISIONAL hasta medirla; 60 N es la más dura con margen x1,2 y el resorte limitador no deja pasar de ahí (el MG996R la sostiene con margen >x2 a 6 V; ver docs/peso.md). Al ser servo, sabe en qué ángulo quedó: no hace falta sensor de posición ni puente H. | simulado | 3 |
| Servo del empujador de descarga (`servo_empujador`) | 1 | MG996R (el vaso lleno pesa más) | Con una manivela (carrera ~70 mm) pasa de lado el vaso tapado a la canaleta de entrega. Los rechazados no se empujan: la cinta los deja caer por su extremo a la bandeja. | simulado | 3 |
| Servo del escape de la canaleta (`servo_compuerta_canaleta`) | 1 | SG90 | Balancín con dos dedos: el de adelante retiene la fila y el de atrás entra entre el primer y el segundo vaso al soltar, así sale UN vaso a la cuna del carro (punto 13). | simulado | 3 |

## Control y potencia

| Componente | Cant. | Modelo propuesto | Para qué sirve | Estado | Hilos |
|---|---|---|---|---|---|
| Drivers de las dos cintas (M y V) (`drivers_cintas`) | 2 | A4988 o TMC2208 (silencioso), en una sola placa | Generan los pasos de los dos NEMA17 (micropaso 1/4, por el PWM del ESP32): el driver M mueve la cinta de monedas y el V la de vasos. Son iguales y comparten placa, 12 V (VMOT, con su condensador de 100 µF cada uno) y la señal ENABLE; cada uno tiene su STEP y su DIR propios en el ESP32 fijo. | efecto simulado | 17 |
| ESP32 fijo (estación) (`esp32_fijo`) | 1 | ESP32 DevKit V1 (38 pines) | Lee los sensores, mueve motores y servos, habla con el PC por USB y con el carro por ESP-NOW. No decide la clasificación: la visión corre en el PC. | efecto simulado | 33 |
| Controlador de servos (`pca9685`) | 1 | PCA9685 (16 canales, I2C) | Maneja los 6 servos con solo 2 pines del ESP32 (I2C; sobran 10 de sus 16 canales). | efecto simulado | 24 |
| Fuente de 12 V (`fuente`) | 1 | Fuente conmutada 12 V 10 A (tipo LRS-150-12, 159 x 97 x 30 mm) | 12 V para los drivers de los pasos a paso, los sensores capacitivo e inductivo y los dos reguladores. Tierra comun en estrella en la bornera X2. El ESP32 fijo va por el USB del portatil. | solo visual | 6 |
| Regulador de 6 V (servos) (`buck_servos`) | 1 | Buck XL4016, 6 V 8 A, con disipadores | Alimenta solo los servos (dos MG996R piden hasta 2,5 A cada uno trabados), a traves de la bornera V+ del PCA9685 con su 1000 uF. | solo visual | 4 |
| Regulador de 5 V (`buck_5v`) | 1 | Buck LM2596, 5 V 3 A | 5 V para el ULN2003 y el 28BYJ-48 del carrusel, el panel de luz y el anillo de la camara. | solo visual | 6 |
| Portafusibles (`fusibles`) | 1 | Portafusibles de 4 vias (cuchilla): F1 5 A, F2 2 A, F3 3 A, F4 1 A | Un fusible por rama de 12 V: regulador de servos, regulador de 5 V, drivers y sensores de 12 V. | solo visual | 5 |
| Bornera X2 (carril DIN) (`bornera_x2`) | 1 | 16 bornes de 2,5 mm² con puentes (2-3 +12 V sensores, 5-6 +5 V, 7 a 13 GND) | Reparte +12 V, +6 V, +5 V y la tierra comun en estrella: ahi llega cada cable de alimentacion. | solo visual | 26 |
| Entrada de red con interruptor (`entrada_red`) | 1 | Conector IEC C14 con interruptor y portafusible | Entrada de 110 V a la fuente, con su interruptor general. | solo visual | 3 |
| Optoacopladores (`optoacopladores`) | 1 | Placa con 2 PC817 (2,2 kΩ de entrada, 10 kΩ de pull-up a 3,3 V) | Pasan las salidas NPN de 12 V del capacitivo y del inductivo a 3,3 V para el ESP32 (nunca directo). | efecto simulado | 7 |
| Reparto del bus I2C 1 (`reparto_i2c`) | 1 | Placa perforada con pull-ups de 2,2 kΩ y 2 conectores | Reparte el bus I2C largo (100 kHz) a los dos VL53L0X (interior del vaso y cortina). | efecto simulado | 12 |
| Driver del carrusel (`uln2003`) | 1 | Placa ULN2003 (con diodos de rueda libre) | Maneja las 4 bobinas del 28BYJ-48 del carrusel desde 4 pines del ESP32. | efecto simulado | 11 |
| Hub USB con fuente (`hub_usb`) | 1 | Hub USB 2.0 de 4 puertos con alimentacion propia | El portatil necesita 3 USB: las dos webcams y el ESP32 fijo. | efecto simulado | 4 |
| Canaletas, prensaestopas y ventilador (`canaletas_caja`) | 1 | Canaleta ranurada 25 x 30 mm, prensaestopas PG y ventilador 4010 de 5 V (0,1 A, del buck de 5 V) | Todo el cableado de la caja va por las canaletas (ningun hilo cruza por encima de una placa); los cables de campo entran por prensaestopas separados. | solo visual | 2 |
| Portátil (`pc`) | 1 | El del grupo (sin GPU) | Visión, supervisor, base de datos, dashboard y visor 3D. | simulado | 1 |

## Estructura

| Componente | Cant. | Modelo propuesto | Para qué sirve | Estado | Hilos |
|---|---|---|---|---|---|
| Cinta de monedas y su mesa (`cinta_monedas`) | 1 | Banda negra mate de 55 mm, separadores cada 40 mm, mesa de 43 cm (PROVISIONAL) | Lleva cada elemento por las 7 estaciones. | simulado | — |
| Cinta de vasos y su mesa (`cinta_vasos`) | 1 | Banda de 75 mm, casillas de 80 mm, mesa de 10 cm (PROVISIONAL) | Lleva los vasos por verificación, llenado, tapa, prensa y descarga. | simulado | — |
| Bandeja de rechazo de monedas (`canaletas_rechazo`) | 1 | Impresión 3D / acrílico | La única salida de rechazo (grupo, 2026-09-25: filtro total): recibe desde la compuerta de desvío todo lo que no es una moneda aceptada. La causa de cada rechazo queda registrada. | simulado | — |
| Almacén tipo revólver (`almacen`) | 1 | 6 tubos de 29 mm interior x 58 mm (PROVISIONAL) en un disco giratorio sobre una placa fija con un agujero; embudo corto al vaso. Impresión 3D | Guarda las monedas por denominación hasta completar un lote. La moneda cae casi vertical a la boca del tubo que está bajo el punto de carga; la pila resbala sobre la placa fija al girar. | simulado | — |
| Tubo vertical de tapas (`tubo_tapas`) | 1 | Tubo de 78 mm interior, termina ~1 cm sobre la boca del vaso | Guarda las tapas; el escape suelta una que cae poco y se centra sola. | simulado | — |
| Bandeja de rechazo de vasos (`bandeja_rechazo_vasos`) | 1 | Impresión 3D, al final de la cinta de vasos | Recibe los vasos inválidos, que caen por el extremo de la cinta. | simulado | — |
| Estructura de perfil de aluminio (`estructura`) | 1 | Perfil 2020 (patas de la mesa de monedas y pórtico trasero de la cinta de vasos) | Sostiene la cinta de monedas, el almacén, el tubo de tapas, la prensa y el panel de luz: nada queda colgando en el aire. | solo visual | — |
| Panel de luz de la cámara de vasos (`panel_luz`) | 1 | Panel LED difuso 5 V (o tira LED detrás de acrílico opalino), ~33 x 11 cm | Contraluz detrás de verificación, llenado, tapa y prensa: la cámara de vasos ve siluetas nítidas y las monedas en el fondo del vaso translúcido. También cierra por detrás la zona de tapa y prensa (una mano solo entra por el lado del operador). | efecto simulado | 2 |
| Embudo y canales de la descarga (`canal_e7`) | 1 | Embudo y dos canales cortos impresos (~60° de inclinación) | Recibe la moneda que cae por el extremo de la cinta; la compuerta de desvío la manda por un canal corto a la boca del tubo del carrusel o por el otro a la bandeja de rechazo. | simulado | — |
| Canaleta de entrega (`canaleta_entrega`) | 1 | 2 rieles de 4 mm a 15°, forrados con cinta adhesiva de PTFE (PROVISIONAL: 280 mm) | Sostiene los vasos colgados del reborde, en fila contra el escape. Entrada en embudo: los rieles arrancan 4 mm más separados y 3 mm más abajo y se cierran en 40 mm. | simulado | — |
| Pista con 3 obstáculos y meta (`pista`) | 1 | Línea de cinta aislante de 19 mm (trazado PROVISIONAL) | Recorrido del carro (punto 14). | simulado | — |
| Muelle de carga del carro (`muelle_carga`) | 1 | 2 guías en V impresas con cinta de PTFE (boca 4,5 cm más ancha por lado en 20 cm, 3 mm de holgura) + 2 topes con espuma | El carro entra de reversa: las guías empujan sus rodillos traseros y lo centran, y los topes lo paran con la cuna justo bajo el final de la canaleta, aunque haya seguido la línea con error. Sabe que llegó porque los encoders dejan de contar contra el tope (entra con PWM bajo). | simulado | — |

## Carro

| Componente | Cant. | Modelo propuesto | Para qué sirve | Estado | Hilos |
|---|---|---|---|---|---|
| ESP32 del carro (`esp32_carro`) | 1 | ESP32 DevKit V1 | Sigue la línea, esquiva, llega a la meta y vuelve solo; avisa por ESP-NOW. | simulado | 35 |
| Motorreductores del carro (`motores_carro`) | 2 | Motor TT 1:48 con encoder | Tracción diferencial (2 ruedas + rueda loca de bola: los 3 apoyos siempre tocan el piso y gira sobre su eje sin patinar). | simulado | 4 |
| Rodillos guía traseros (`rodillos_guia`) | 2 | Rodamiento 623 (10 mm) en un tornillo M3, en cada esquina trasera | Lo que empujan las guías del muelle (no las llantas): el carro gira hacia el centro al entrar de reversa, como un carrito de supermercado. | simulado | — |
| Puente H del carro (`puente_h_carro`) | 1 | TB6612FNG | Controla los dos motores del carro. | efecto simulado | 15 |
| Interruptor y fusible del carro (`interruptor_carro`) | 1 | Interruptor de palanca + fusible de 3 A | Corta la bateria; el fusible protege el cableado. | solo visual | 3 |
| Batería del carro (`bateria_carro`) | 1 | 2 celdas 18650 (7,4 V) | Alimenta motores y ESP32 del carro. | solo visual | 3 |
| Cuna de carga (rieles) (`cuna_carro`) | 1 | Mismos rieles de la canaleta (forrados con cinta de PTFE), 3 mm más bajos, entrada en embudo | Recibe el vaso desde la canaleta sin brazo robótico. Soporte de 4 puntos a media altura: espuma adelante, lengüeta con resorte atrás (el vaso la empuja al entrar y no puede salirse) y dos guías con PTFE a los costados: el vaso no cabecea y el carro puede ir más rápido. | simulado | — |

## Sensores

Ver [sensores.md](sensores.md) (13 sensores numerados).

