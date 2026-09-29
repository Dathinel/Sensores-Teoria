# Revisión final antes del protocolo (2026-09-26)

Revisión total del diseño antes de programar el protocolo de comunicación (punto 15). Se revisó
si **físicamente hay espacio** para cada pieza, si **cada sensor alcanza** lo que tiene que ver
(con su error probable), y toda la **electrónica**: puertos, pines, alimentación, cables, ruido
y conexiones. Lo que se pudo corregir sin cambiar decisiones ya aprobadas quedó corregido en el
modelo 3D y en la simulación. Lo que cambia algo aprobado queda en la última sección, para
decidir.

## 1. Espacio físico

Método: con el visor abierto en modo auditoría, un script mide cada pieza del modelo 3D como
una caja orientada y busca las que se atraviesan más de 1,5 mm (prueba de ejes separadores).
Primera pasada: 29 cruces entre piezas físicas.

**Corregidos:**

| Qué chocaba | Corrección |
|---|---|
| Una pata de la mesa de monedas atravesaba el carrusel del almacén | Las patas del extremo de descarga van 6 cm antes del final |
| La barra de soporte de varios servos subía por dentro del servo (obturador, tapas, escape de la canaleta) | Soporte en "L": baja por debajo del servo y sube por el lado |
| El soporte del servo del desvío atravesaba el rodillo de la cinta de monedas y el canal de rechazo | Poste propio hasta el piso, justo debajo (a los lados bajan los dos canales) |
| El soporte del infrarrojo de presencia atravesaba el motor de la cinta de monedas | Escuadra desde la otra orilla |
| El labio de la bandeja de rechazo de vasos atravesaba el rodillo final | Corrido después del rodillo |
| El servo de tapas tocaba el tubo de tapas | 3 mm más afuera |
| Carro: el soporte de la espuma atravesaba el porta-baterías y el segundo piso | La espuma cuelga del tope delantero |
| Carro: el segundo piso y el ESP32 quedaban en el espacio del vaso colgado | Segundo piso de x = 2 a 8 cm (el vaso ocupa hasta x = 0,6 cm) |
| Carro: el porta-baterías (77 mm) chocaba con el vaso y con la escuadra de sensores | Atravesado, de x = 1,2 a 5,3 cm |
| Carro: los motores TT se metían 4 mm en la placa | Bajados: quedan a 0,5 mm de la placa |
| Carro: la bola de la rueda loca chocaba con la placa de infrarrojos | Rueda loca a 0,30 del largo (también en la física) |
| Hall del carrusel: el sensor quedaba encima del imán (piezas sobrepuestas) | Imán de 6 × 3 mm en una cavidad del disco, a R + 15 mm y a 0° (entre los tubos de 330° y 30°); el módulo KY-003 queda **4 mm por encima**, colgado del pórtico. A 180° su varilla quedaba a 4 mm de la del sensor del interior |
| Servos "posados": la escuadra quedaba 1,5 mm por debajo del cuerpo y nada los sujetaba | Cuna impresa que abraza el cuerpo, con dos torres bajo las orejas y 4 tornillos (los 6 servos) |
| El poste de la cortina arrancaba a la altura de la mesa de vasos pero fuera de ella (flotaba) | Brazo de perfil 10 mm atornillado al costado de la bancada, por debajo de la banda |
| Con los rieles nuevos de la cinta de monedas, una pata atravesaba la viga del pórtico | Ese extremo apoya en la viga con un taco impreso de 2 cm (3 patas) |
| El servo del desvío, con su cuna, tocaba los dos canales de salida | 35 mm detrás del embudo |

**Intencionales (no son errores):** el vástago de la prensa pasa por su buje; la biela del
empujador por su guía; el eje de cada motor entra a su rodillo; el eje del carrusel atraviesa la
placa fija (por un rodamiento); la bola de la rueda loca va en su carcasa; las escuadras y barras
atornilladas al perfil; el disco del encoder pasa por una ranura del chasis (como en los kits).

**Disposición:** la caja de control (30 × 20 × 8 cm: la fuente sola mide 159 × 97 mm) pasa al
costado de la cinta de vasos (0,345, 0,145), el portátil detrás de la mesa de monedas (0,03, 0,38)
y entre los dos un hub USB con fuente propia. Ver las secciones 4 y 6.

## 2. Sensores: alcance real, montaje y error probable

En el visor 3D cada sensor muestra dos conos: el **nominal** (hoja de datos) y, más tenue, el de
**error probable** (el nominal más ~5° de desalineación de montaje).

| # | Sensor | Alcance (hoja de datos) | Montaje | Error probable | Veredicto |
|---|---|---|---|---|---|
| 1 | Presencia | FC-51: 2-30 cm | 5 cm sobre la cinta | cono ~10° (Ø 18 mm en la cinta; Ø 27 mm con error): cabe en la casilla de 40 mm | **Corregido:** era "TCRT5000 o FC-51", pero el TCRT5000 solo ve ~15 mm y tendría que ir tan bajo que los bloques lo golpearían. Queda el FC-51 |
| 2 | Capacitivo | LJC18A3-H-Z: 1-10 mm | **Debajo de la cinta, centrado bajo E1** | pieza a ~2 mm (la banda); se calibra con la banda y los separadores puestos | **Corregido** (sección 5): al costado no veía una moneda chica centrada (~16 mm) |
| 3 | Inductivo | **LJ18A3-8-Z** (M18, 8 mm) | **Debajo de la cinta, centrado bajo E2** | con monedas no ferrosas de 17-27 mm: ~2,2-4,8 mm, contra 2 mm de banda | **Corregido** (sección 5): el M12 de 4 mm no alcanzaba a través de la banda |
| 4 | Cámara cenital | Webcam 1080p | 15 cm sobre E3 | ~0,1 mm/px; diámetro ±0,08 mm con calibración | **Corregido:** estaba a 9 cm y casi ninguna webcam enfoca tan cerca. Tiene que ser de **autoenfoque** |
| 5 | Interior del vaso | VL53L0X: 3 cm-1,2 m, cono 25° | 1,5 cm sobre la boca | margen al fondo ~6 mm: aguanta ~3° torcido | **Corregido:** a 3 cm el margen era 2,5 mm y, torcido, vería la pared (falso "algo adentro"). Collar de centrado |
| 6 | Hall del carrusel | A3144 + imán N35 de 6 × 3 mm | 4 mm sobre el imán | a 4 mm el imán da ~70 mT y el A3144 conmuta con ~10-35 mT; disparo ±1 paso | **Corregido:** estaba sobrepuesto al imán |
| 7 | Cámara de vasos | Webcam 720p, ~60° | 30 cm, a la altura de la boca | ~0,3 mm/px: silueta y ArUco sobrados | OK |
| 8 | Cortina | VL53L0X, cono 25° | 65 mm de alto, 85 mm del eje | aguanta ~6° torcido sin ver los vasos | OK |
| 9 | Línea (carro) | TCRT5000: ~15 mm | 7 mm del piso | — | OK |
| 10 | Ultrasónico (carro) | HC-SR04: 2 cm-4 m, ~15° | Frente, respaldo | lóbulos laterales hasta ~30° | OK |
| 11 | Encoders (carro) | Horquilla H206 | Disco en el eje | ±1 pulso (10 mm) | OK |
| 12 | Cuna (carro) | TCRT5000: ~15 mm | a 6 mm del vaso | — | **Corregido:** estaba a 15,5 mm, al límite |
| 13 | Láser (carro) | VL53L0X: ~1,2 m, 25° | Frente, sobre el ultrasónico | ±3 %; negro/brillante/sol lo confunden (lo cubre el ultrasónico) | OK |

## 3. Electrónica: puertos y pines

### Portátil

Necesita **3 USB**: webcam cenital, webcam de vasos y ESP32 fijo. Recomendado: **hub USB con
alimentación propia**. Las dos webcams comparten el ancho de banda del USB 2.0: usarlas en
**MJPEG** (o la de vasos a 720p), porque dos flujos 1080p sin comprimir no caben. Con el
portátil detrás de la mesa de monedas, las dos webcams llegan con su cable de 1,5 m.

### ESP32 fijo (DevKit V1, 38 pines): 19 de ~25 pines útiles

No se usan los pines de arranque (0, 2, 5, 12, 15), los de la memoria (6-11) ni 1/3 (USB al PC).

| Función | Pines |
|---|---|
| I2C 0 (corto, dentro de la caja): PCA9685 (0x40) | SDA 21, SCL 22 (400 kHz) |
| I2C 1 (largo, por el pórtico): VL53L0X interior (0x30) y cortina (0x31) | SDA 16, SCL 17 (100 kHz) |
| XSHUT de los dos VL53L0X (para cambiarles la dirección al arrancar) | 18, 19 |
| Paso a paso cinta de monedas / vasos (STEP, DIR) y ENABLE común | 25, 26 / 27, 14 / 13 |
| Carrusel 28BYJ-48 por ULN2003 (IN1-IN4) | 32, 33, 23, 4 |
| Infrarrojo de presencia (FC-51) | 34 (solo entrada) |
| Capacitivo e inductivo (por optoacoplador PC817: salen a 12 V) | 35, 36 (solo entrada) |
| Hall A3144 (colector abierto: pull-up externo de 10 kΩ a 3,3 V; el 39 no tiene interno) | 39 (solo entrada) |

**PCA9685** (16 canales): 6 servos. Canal 0 desvío, 1 obturador, 2 escape de tapas, 3 prensa
(MG996R), 4 empujador (MG996R), 5 escape de la canaleta. Quedan 10 libres.

### ESP32 del carro: 19 pines

| Función | Pines |
|---|---|
| TB6612: PWMA, AIN1, AIN2 / PWMB, BIN1, BIN2 / STBY | 25, 26, 27 / 33, 32, 13 / 4 |
| Encoders (interrupción) | 18, 19 |
| 5 infrarrojos de línea (salida digital del módulo) | 34, 35, 36, 39, 16 |
| HC-SR04: TRIG / ECHO (5 V → divisor 1 kΩ/2 kΩ a 3,3 V) | 17 / 23 |
| I2C del láser VL53L0X | SDA 21, SCL 22 |
| Infrarrojo de la cuna | 14 |

**Ojo:** con ESP-NOW encendido (usa la radio Wi-Fi), el **ADC2 no funciona** (pines 0, 2, 4,
12-15, 25-27). Los sensores van a entradas digitales; si algún día se leen en analógico, solo
por el ADC1 (32-39).

## 4. Alimentación, cables, ruido y conexiones seguras

### Alimentación

- **Estación:** fuente de **12 V 10 A**:
  - 12 V directo a los dos drivers de los NEMA17 (A4988: Vref ≈ 0,54 V para ~1 A por fase;
    en reposo el A4988 NO baja la corriente solo: el firmware suelta ENABLE (G13) cuando las dos
    cintas llevan `firmware.a4988_reposo_ms` quietas, más que las pausas normales, así que solo
    ahorra en las esperas largas; 2026-09-28) y a los sensores capacitivo e inductivo (piden 6-36 V).
  - **Buck 6 V 8 A solo para los servos.** Dos MG996R piden hasta 2,5 A cada uno trabados; el
    firmware nunca mueve prensa y empujador a la vez (pico real ~3,5 A). 1000 µF en la bornera V+
    del PCA9685.
  - **Buck 5 V 3 A** para lo demás: panel de luz, anillo de la cámara, 28BYJ-48 y módulos.
  - El ESP32 fijo se alimenta del USB del portátil.
  - **Tierra común en estrella en la fuente.**
  - Fusibles: 5 A en servos, 3 A en pasos a paso, 2 A en 5 V.
- **Carro:** 2 × 18650 (7,4 V nominal, 8,4 V cargadas) con BMS 2S, interruptor y fusible de 3 A.
  El TB6612 aguanta hasta 13,5 V, pero **los motores TT son de 3-6 V**: el firmware limita el
  PWM a ~70 % (~5,9 V con la batería llena). Buck 5 V para el ESP32 (VIN), el HC-SR04 y los
  módulos.

### Largos de cable (medidos en el modelo 3D, con 20 % de holgura)

Cada cable está dibujado en el visor por donde iría de verdad (botón **Cables**) y el largo sale
de ese recorrido, hasta el prensaestopas de la caja; adentro, cada hilo va por las canaletas
hasta su borne o pin (tabla pin a pin en [conexiones.md](conexiones.md)).

| Hasta | Largo |
|---|---|
| Motor cinta monedas / vasos / carrusel (28BYJ-48) | 1,38 / 0,76 / 0,94 m |
| Servos desvío / obturador / tapas | 0,63 / 1,19 / 1,11 m |
| Servos prensa / empujador / escape canaleta | 0,59 / 0,26 / 0,70 m |
| Presencia / capacitivo / inductivo / Hall | 1,18 / 1,18 / 1,14 / 0,88 m |
| VL53L0X interior / cortina (I2C 1) | 1,20 / 0,50 m (bus de 1,7 m: ~170 pF, dentro de los 400 pF del I2C a 100 kHz) |
| Panel de luz / anillo de la cámara | 0,29 / 1,03 m |
| Webcam cenital / de vasos (al hub) | 1,30 / 1,23 m (las webcams traen 1,5 m) |
| ESP32 → hub, hub → portátil, red → caja | 0,38 / 0,07 / 0,28 m |
| **Total de cables de campo** | **18,2 m** |
| Hilos dentro de la caja (47 cables/hilos por las canaletas) | 18,7 m de hilo |
| Carro (42 hilos) | 6,0 m de hilo |

Los cables de servo traen 25 cm: van con **extensión de 22 AWG** enchufada directo al canal del
PCA9685 (la bornera de servos en la columna se quitó: ya no hace falta). Con 22 AWG (0,053 Ω/m por
hilo) el peor caso, el MG996R de la prensa trabado (2,5 A a 0,59 m), pierde ~0,16 V; el SG90 del
obturador (1,19 m, ~0,7 A) ~0,09 V. La corriente de los servos entra al PCA9685 por su bornera
V+ con 18 AWG desde el buck de 6 V, y el firmware nunca mueve prensa y empujador a la vez. El bus I2C largo (0,7-1 m) va a 100 kHz, con pull-ups de
2,2 kΩ y cable trenzado (SDA con GND, SCL con GND) o apantallado de 4 hilos.

### Ruido e interferencias (motores y embobinados)

- **Motores TT del carro** (escobillas: mucho ruido): condensador cerámico de 100 nF entre los
  bornes y 2 × 47 nF a la carcasa; cables del motor trenzados y lejos de los de encoders e
  infrarrojos.
- **NEMA17:** cada bobina en un par trenzado (A+/A-, B+/B-; se identifican con el multímetro,
  ~1,5 Ω por bobina). **100 µF en VMOT de cada driver** (el A4988 se quema sin él por los picos al
  enchufar). Separados del bus I2C. Un TMC2208 es más silencioso, si se prefiere.
- **28BYJ-48:** bobinas de 5 V por ULN2003, que ya trae diodos de rueda libre (COM a 5 V).
- **Servos:** su corriente vuelve directo a la fuente, no por el ESP32; condensador en el PCA9685.
- **Webcams:** ferrita en el cable USB y lejos de los cables de los motores.
- **ESP-NOW:** canal fijo (1); el ESP32 fijo no se conecta a ningún Wi-Fi.

### Conexiones seguras

- Borneras de tornillo para la alimentación.
- JST-XH (con llave, no se enchufan al revés) para sensores y motores. Dupont solo en pruebas.
- Cables sujetos a las ranuras del perfil 2020 con amarras y alivio de tensión en cada conector.
- Cada cable rotulado en los dos extremos.
- Diodo o fusible contra polaridad invertida en cada entrada de alimentación.

## 5. Decidido: sensores de material debajo de la cinta

Al costado, el inductivo (4 mm) y el capacitivo (≤ 10 mm) no veían una moneda chica centrada en
la cinta de 55 mm (~16 mm de distancia), y arriba los golpearían los bloques. Grupo (2026-09-26):
**debajo de la cinta**, mirando hacia arriba, leyendo a través de la banda (2 mm de goma, que no
es metal). Al modelarlo salieron cuatro cosas que no se veían en el papel:

1. **Una moneda de 17 mm no tapa dos caras de 18 mm a la vez.** Uno al lado del otro, cada sensor
   queda descentrado y el inductivo pierde la mitad del alcance (con las no ferrosas no llega).
   Por eso cada uno va **centrado bajo su casilla**: el capacitivo bajo E1 (su lectura viaja en el
   registro de la casilla) y el inductivo bajo E2, donde se decide el material. La lógica no
   cambia (el material se decide en E2 con las dos lecturas); en la simulación el capacitivo lee
   la casilla E1.
2. **El inductivo pasa a M18 de 8 mm (LJ18A3-8-Z/BX).** Una moneda de 17-27 mm da ~70-80 % del
   alcance nominal y una no ferrosa ~40-60 % de eso: con el M12 de 4 mm quedaban ~1,1-1,9 mm,
   menos que los 2 mm de banda. Con el de 8 mm quedan ~2,2-4,8 mm. Mismo precio y misma conexión.
   Es no enrasable: va en un **inserto impreso** de la bancada (nada de metal a ~2 cm de su cara).
3. **El retorno de la banda pasaba justo por donde van los cuerpos (6-7 cm).** El retorno baja
   por dos rodillos hasta 11 cm bajo la cinta en la zona E1-E2 (y un tensor lo lleva de vuelta),
   dejando lugar a los sensores y a la curva de sus cables.
4. **El rodillo de cola quedaba a 2 cm de E1:** no cabía el capacitivo. La banda arranca una
   casilla antes (40 mm más), las patas van por fuera de la banda (rieles laterales de perfil
   2020) y el motor, por fuera del riel.

## 6. Modelo 3D de conexiones (pin a pin)

Fuente única: `sim/conexiones.py`, con cada módulo (su medida y sus pines con nombre), cada
dispositivo y cada hilo de un pin a otro. De ahí salen el visor 3D y
[conexiones.md](conexiones.md), y `tests/sim/test_conexiones.py` verifica:
- que cada pin exista;
- que ningún pin de header reciba dos hilos y que los bornes lleven como mucho dos;
- que los GPIO sean los de la tabla de la sección 3, sin pines de arranque ni de memoria;
- que en 34/35/36/39 (solo entrada) solo haya sensores;
- que cada servo esté en su canal.

- **Botón "Cables"** (barra de arriba): muestra u oculta todo el cableado. La leyenda tiene los
  cables por tipo con su largo y la lista **pin a pin**.
- **Placas GVS** como las de los labs: el ESP32 fijo (DevKit de 38 pines) y el del carro (30
  pines) van sobre su placa de expansión, con el jumper en 3,3 V. Cada sensor de 3 hilos entra en
  la fila de su GPIO: G = GND, V = 3,3 V, S = señal.
- **Cada módulo con sus pines reales y su serigrafía:** FC-51, KY-003, GY-530, H206, TCRT5000,
  HC-SR04, TB6612, PCA9685 (16 canales), A4988, ULN2003, optoacopladores, reguladores, fuente,
  portafusibles y bornera DIN. Cada hilo lleva su color y termina en su pin, con carcasa Dupont en
  los headers y férula en los bornes. No se modela el chip: lo que importa son las entradas y
  salidas.
- **Caja de control ordenada como tablero:**
  - adelante, la fila de lógica; atrás, la de potencia;
  - canaletas ranuradas entre las filas y a los lados: los hilos van por ellas, ninguno cruza por
    encima de otra placa;
  - bornera X2 en carril DIN con puentes: +12 V de sensores, +5 V y GND en estrella;
  - prensaestopas separados para señales y para motores.
- **Recorridos de campo:** lo del pórtico y la cinta de monedas va por encima de la viga y baja
  por la columna derecha. Lo demás va por el piso. Las webcams van por otro camino al hub USB.
- **Carro:** lo de abajo de la placa sube por un agujero junto a su módulo; lo que está entre
  pisos sale por el borde del segundo piso. El divisor 1 kΩ / 2 kΩ del ECHO del HC-SR04 va en
  termorretráctil sobre el hilo.
