// Display de siete segmentos (catodo comun) en C/C++ via Arduino, el mismo
// codigo de la captura wokwi-arduino-c.png. Dibuja un "2": segmentos
// a, b, g, e y d encendidos; c y f apagados (ver siete_segmentos.py).

// Definicion de los pines GPIO para los segmentos
const int sA = 17;
const int sB = 16;
const int sC = 32;
const int sD = 33;
const int sE = 25;
const int sF = 14;
const int sG = 12;

void setup() {
  // Configuramos los siete pines como salidas digitales
  pinMode(sA, OUTPUT);
  pinMode(sB, OUTPUT);
  pinMode(sC, OUTPUT);
  pinMode(sD, OUTPUT);
  pinMode(sE, OUTPUT);
  pinMode(sF, OUTPUT);
  pinMode(sG, OUTPUT);
}

// loop() lo repite el propio framework de Arduino: no hace falta un while(true).
void loop() {
  // HIGH = 3,3 V = segmento encendido (catodo comun)
  digitalWrite(sA, HIGH);
  digitalWrite(sB, HIGH);
  digitalWrite(sC, LOW);
  digitalWrite(sD, HIGH);
  digitalWrite(sE, HIGH);
  digitalWrite(sF, LOW);
  digitalWrite(sG, HIGH);
}
