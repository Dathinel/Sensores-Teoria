# Circuito en Wokwi (los dos ESP32)

[Wokwi](https://wokwi.com) es un simulador de electrónica en el navegador: se arma el circuito con un
ESP32 y sus piezas, se le carga el programa y corre como si fuera la placa real (se ven los motores
girar, los servos moverse, se pueden apretar botones y girar potenciómetros). Aquí sirve para **ver
el conexionado funcionando** sin tener el montaje: cada pieza va en el MISMO GPIO que usa el
firmware real (`firmware/fijo/hw.py` y `firmware/carro/hw.py`, cuyos pines salen de
`sim/conexiones.py`).

Lo que Wokwi no simula es la parte de potencia (voltajes, corrientes, fusibles, reguladores): eso
está calculado en [docs/electrica.md](../docs/electrica.md), con la simulación de `sim/electrica.py`.

## Cómo abrirlo

1. Entrar a <https://wokwi.com> → **New Project** → **MicroPython on ESP32** (plantilla con el
   ESP32 DevKit-C V4).
2. En la pestaña `diagram.json` borrar todo y pegar el contenido de `fijo/diagram.json` (o
   `carro/diagram.json`).
3. En la pestaña `main.py` pegar `fijo/main.py` (o `carro/main.py`).
4. Botón verde ▶. El monitor serial de abajo muestra las mismas líneas JSON que manda el firmware
   real (`{"t":"evt",...}`, `{"t":"tel",...}`).

Sin cuenta el proyecto no se guarda, pero no hace falta: los archivos están aquí.

**Qué probar en `fijo/`:** las dos cintas avanzan cada una a su ritmo (los steppers cuentan pasos);
los 4 LEDs azules muestran la secuencia de medio paso del carrusel; la prensa baja y sube y
DESPUÉS se mueve el empujador (nunca a la vez); girar el potenciómetro de la cortina por debajo de
la mitad (< 150 mm) simula una mano: la prensa sube, la cinta de vasos se detiene y se ve el evento
`cortina`. Los 4 pulsadores son presencia, capacitivo, inductivo y Hall.

**Qué probar en `carro/`:** en el interruptor DIP, los 5 primeros son los infrarrojos de línea
(ABIERTO = ve negro). Con solo el del centro abierto los dos LEDs de PWM brillan igual; abriendo uno
de un lado, un PWM sube y el otro baja (corrige hacia la línea). Haciendo clic en el HC-SR04 se
cambia la distancia: por debajo de 200 mm el carro se detiene (los PWM se apagan); el potenciómetro
hace lo mismo como láser. Los pulsadores verdes son los encoders (cuentan en la telemetría) y el rojo,
el infrarrojo de la cuna.

## Qué representa cada parte

| En Wokwi | Pieza real | GPIO | Por qué así |
|---|---|---|---|
| **ESP32 fijo** (`fijo/`) | | | |
| `wokwi-a4988` + `wokwi-stepper-motor` (×2) | A4988 + NEMA17 de cada cinta | STEP/DIR 25/26 (monedas), 27/14 (vasos), ENABLE 13 | Existen en Wokwi. Con MS1-MS3 al aire Wokwi da paso completo; el montaje va a 1/4 de paso |
| 4 LEDs azules | ULN2003 + 28BYJ-48 del carrusel | 32, 33, 23, 4 | Wokwi no tiene ULN2003 ni motor unipolar: los LEDs muestran qué bobina está energizada |
| Pulsador + 10 kΩ a 3,3 V | FC-51 de presencia | 34 | Pulsado = detecta (salida activa en bajo). 34-39 no tienen pull-up interno |
| Pulsador + 10 kΩ | Capacitivo por el PC817 | 35 | El sensor de 12 V + optoacoplador se ven desde el ESP32 como un contacto a GND con pull-up de 10 kΩ: exactamente esto |
| Pulsador + 10 kΩ | Inductivo por el PC817 | 36 (VP) | Igual que el capacitivo |
| Pulsador + 10 kΩ | Hall KY-003 (A3144, colector abierto) | 39 (VN) | Es el mismo pull-up de 10 kΩ del montaje |
| `wokwi-servo` prensa y empujador | MG996R por el PCA9685 (canales 3 y 4) | **5 y 12, solo en Wokwi** | Wokwi no tiene PCA9685: dos servos directos a GPIO libres. En el montaje van por I2C 21/22 al PCA9685 (con los otros 4 SG90) y esos GPIO no se usan (el 12 es de arranque) |
| Potenciómetro "cortina" | VL53L0X de la cortina | **2, solo en Wokwi** | Wokwi no tiene VL53L0X: el potenciómetro da la distancia (0-300 mm). En el montaje: I2C 16/17, XSHUT 19 |
| Potenciómetro "interior" | VL53L0X del interior del vaso | **15, solo en Wokwi** | Igual (0-150 mm). En el montaje: I2C 16/17, XSHUT 18 |
| **ESP32 del carro** (`carro/`) | | | |
| 7 LEDs (PWMA, AIN1, AIN2, PWMB, BIN1, BIN2, STBY) | TB6612FNG + 2 motores TT | 25, 26, 27, 33, 32, 13, 4 | Wokwi no tiene el TB6612: el brillo del LED de PWM es la velocidad de la rueda y los de IN el sentido. El PWM se recorta a 70 % (motores de 6 V con batería de 8,4 V) |
| Interruptor DIP (5 de 8) + 10 kΩ | 5 infrarrojos TCRT5000 de línea | 34, 35, 36, 39, 16 | Abierto = negro (1), como `linea_negro_alto` |
| `wokwi-hc-sr04` | HC-SR04 | TRIG 17, ECHO 23 | Existe en Wokwi. En el montaje el ECHO (5 V) pasa por el divisor 1 kΩ / 2 kΩ → 3,33 V; Wokwi trabaja con niveles lógicos y se conecta directo |
| Potenciómetro "láser" | VL53L0X frontal | **2, solo en Wokwi** | En el montaje: I2C 21/22. Ojo: con ESP-NOW encendido el ADC2 (GPIO 2) no funciona; aquí no hay radio |
| 2 pulsadores verdes | Encoders H206 | 18, 19 | Cada pulsación = una ranura del disco |
| Pulsador rojo | Infrarrojo de la cuna (TCRT5000) | 14 | Pulsado = vaso en la cuna |

Los servos de Wokwi se alimentan del 5 V de la placa; en el montaje van a 6 V desde el buck XL4016
por la bornera V+ del PCA9685 (nunca desde el ESP32: un MG996R trabado pide 2,5 A).

**Ojo con los pines extra.** Como Wokwi no tiene PCA9685 ni VL53L0X, sus sustitutos van a pines que el
montaje real NO usa: los servos de prensa y empujador a los GPIO 5 y 12, y los potenciómetros al 2 y al
15. Varios de esos son pines de arranque del ESP32 (el proyecto real los evita, ver la tabla de pines del
README): en Wokwi da igual porque la placa simulada siempre arranca, pero no hay que copiar esos pines al
circuito físico. En el montaje los servos van al PCA9685 y los VL53L0X al I2C largo (16/17).

`tests/sim/test_electrica.py` comprueba que los dos `diagram.json` son JSON válido y que usan los
mismos GPIO que el firmware (y que los únicos pines extra son los sustitutos de esta tabla).
