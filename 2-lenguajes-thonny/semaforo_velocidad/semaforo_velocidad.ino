// Comparacion de velocidad MicroPython vs. C/C++ (version Arduino / C++).
// Mismo circuito y misma medicion que semaforo_velocidad.py:
// LED rojo en GPIO5, amarillo en GPIO17 y verde en GPIO16.
//
// Se sube con el Arduino IDE (placa "ESP32 Dev Module"). Ojo: grabar esto
// BORRA el firmware de MicroPython; para volver a Thonny hay que reinstalarlo.
// El resultado sale por el Monitor Serie a 115200 baudios.

const int ROJO = 5;
const int AMARILLO = 17;
const int VERDE = 16;

// Mismo numero de repeticiones que en MicroPython, para comparar igual con igual.
const long REPETICIONES = 10000;

void setup() {
  Serial.begin(115200);
  pinMode(ROJO, OUTPUT);
  pinMode(AMARILLO, OUTPUT);
  pinMode(VERDE, OUTPUT);

  // 1. Secuencia visible: con pausas de cientos de ms no se nota diferencia
  // entre lenguajes, por eso hace falta la medicion de abajo.
  for (int i = 0; i < 3; i++) {
    digitalWrite(VERDE, HIGH);    delay(1500); digitalWrite(VERDE, LOW);
    digitalWrite(AMARILLO, HIGH); delay(500);  digitalWrite(AMARILLO, LOW);
    digitalWrite(ROJO, HIGH);     delay(1500); digitalWrite(ROJO, LOW);
  }

  // 2. Medicion con micros(), el equivalente de time.ticks_us().
  unsigned long inicio = micros();
  for (long i = 0; i < REPETICIONES; i++) {
    digitalWrite(ROJO, HIGH);
    digitalWrite(ROJO, LOW);
  }
  unsigned long total_us = micros() - inicio;  // resta sin signo: tolera la vuelta del contador

  Serial.print("C/C++: ");
  Serial.print(2 * REPETICIONES);
  Serial.print(" cambios en ");
  Serial.print(total_us);
  Serial.print(" us -> ");
  Serial.print((float)total_us / (2 * REPETICIONES), 3);
  Serial.println(" us por cambio");
}

void loop() {
  // Nada: la medicion se hace una sola vez al arrancar (boton EN para repetir).
}
