// ESP-B (esclavo): recibe el digito reenviado por el ESP-A por DOS
// caminos a la vez -- UART2 y SPI real -- y lo muestra grande en una
// pantalla OLED I2C SSD1306 128x64. Escucha los dos caminos sin
// bloquear en el mismo loop(): el que de verdad este cableado es el
// que entrega datos, el otro simplemente no recibe nada nunca (no hace
// falta saber de antemano cual cable se conecto). Ver la seccion "Dos
// caminos: UART2 y SPI" del README para el detalle completo.
//
// Por que este archivo es un sketch de Arduino (C++) y no MicroPython
// como el resto de los ESP32 del repositorio: escuchar SPI en modo
// ESCLAVO es justo lo que le falta a machine.SPI de MicroPython (solo
// implementa maestro). El camino UART2 si se podria haber dejado en
// MicroPython (como en la version anterior de este archivo), pero
// entonces UART2 y SPI habrian quedado en dos placas/lenguajes
// distintos y no se podrian combinar en un solo firmware -- por eso
// todo el ESP-B (los dos caminos juntos) esta en Arduino.
//
// Requiere instalar, desde el Gestor de Librerias del Arduino IDE:
//   - "ESP32SPISlave" (hideakitai) - el modo esclavo de SPI en si.
//   - "Adafruit SSD1306" + "Adafruit GFX Library" - la OLED (la version
//     anterior en MicroPython usaba un driver propio vendoreado,
//     ssd1306.py; aca se usa la libreria estandar de Arduino).
//
// Compilar y subir este sketch con el Arduino IDE (placa "ESP32 Dev
// Module" o la que corresponda al ESP-B) -- YA NO se guarda como
// main.py con Thonny, a diferencia del ESP-A y del resto de los ESP32
// de este repositorio.
//
// Pines:
//   UART2:        TX=GPIO17, RX=GPIO16 -> al RX/TX (cruzados) del ESP-A.
//   SPI esclavo:  SCK=GPIO14, MISO=GPIO12, MOSI=GPIO13, SS=GPIO15 ->
//                 a los mismos pines (sin cruzar) del ESP-A.
//   OLED I2C:     SDA=GPIO21, SCL=GPIO22, direccion 0x3C.
//
// Cuidado con GPIO12 (MISO): es un pin de strapping del ESP32 (decide
// el voltaje de la flash al arrancar, espera leerlo en LOW). Si el
// ESP-B no arranca o entra en bootloop al conectar el cable de MISO,
// resetear primero el ESP-A y esperar a que termine de arrancar antes
// de resetear el ESP-B (ver detalle en el README).
//
// Como diagnosticar si la OLED no muestra nada: conectar el ESP-B
// directo al PC por su propio cable USB y abrir el Monitor Serie del
// Arduino IDE a 115200 baudios. Deberia aparecer "ESP-B listo..." al
// reiniciar. Si nunca aparece "OLED:n" por ninguno de los dos caminos,
// revisar el cableado (UART2 cruzado + GND comun, o los 4 cables de
// SPI sin cruzar + GND comun) entre el ESP-A y el ESP-B. Si "OLED:n"
// si aparece pero la pantalla no cambia, es la direccion I2C de la
// OLED (probar 0x3D si 0x3C no funciona).

#include <ESP32SPISlave.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ------------------------------------------------------------------
// Camino 1: UART2, protocolo de texto "DIGIT:n\n" (igual que la
// version anterior en MicroPython).
// ------------------------------------------------------------------
HardwareSerial uartDeMaestro(2);
String bufferLinea = "";

// ------------------------------------------------------------------
// Camino 2: SPI real, un solo byte con el digito. hasTransactions...()
// + queue()/trigger() es el patron NO bloqueante oficial de la
// libreria ESP32SPISlave (ver ejemplo "transfer_in_the_background" en
// su repositorio) -- necesario aca porque el loop() tambien tiene que
// revisar UART2 en la misma vuelta, sin quedarse esperando a que
// llegue algo por SPI.
// ------------------------------------------------------------------
ESP32SPISlave slave;
static constexpr size_t QUEUE_SIZE = 1;
uint8_t rx_buf[1] = {0};

Adafruit_SSD1306 oled(128, 64, &Wire, -1);

void mostrarDigito(uint8_t digito, const char *camino) {
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.println("Digito reconocido:");
  oled.setTextSize(5);
  oled.setCursor(40, 16);
  oled.print(digito);
  oled.display();

  // print de depuracion: confirma por cual de los dos caminos llego
  // este digito en particular, ademas de la confirmacion que ya daba
  // la version anterior (el "OLED:n" en si).
  Serial.print("OLED:");
  Serial.print(digito);
  Serial.print(" (");
  Serial.print(camino);
  Serial.println(")");
}

void setup() {
  Serial.begin(115200);

  uartDeMaestro.begin(115200, SERIAL_8N1, 16, 17); // RX=16, TX=17

  Wire.begin(21, 22); // SDA, SCL
  oled.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  oled.clearDisplay();
  oled.display();

  slave.setDataMode(SPI_MODE0);
  slave.setQueueSize(QUEUE_SIZE);
  slave.begin(); // HSPI por defecto: SCK=14, MISO=12, MOSI=13, SS=15

  Serial.println("ESP-B listo, esperando 'DIGIT:n' por UART2 o por SPI...");
}

void loop() {
  // --- Camino 1: UART2. El UART2 puede entregar los bytes de una
  // linea repartidos entre varias lecturas, asi que se va acumulando
  // todo en bufferLinea hasta encontrar un '\n' -- recien ahi se
  // procesa esa linea completa. ---
  while (uartDeMaestro.available()) {
    char c = (char) uartDeMaestro.read();
    if (c == '\n') {
      bufferLinea.trim();
      if (bufferLinea.startsWith("DIGIT:")) {
        mostrarDigito((uint8_t) bufferLinea.substring(6).toInt(), "UART2");
      }
      bufferLinea = "";
    } else {
      bufferLinea += c;
    }
  }

  // --- Camino 2: SPI esclavo, sin bloquear. Si no hay ninguna
  // transaccion en curso, deja una nueva en cola lista para recibir 1
  // byte; si una transaccion ya en cola se completo (el ESP-A de
  // verdad hablo por SPI), toma ese byte y lo muestra. ---
  if (slave.hasTransactionsCompletedAndAllResultsHandled()) {
    slave.queue(NULL, rx_buf, 1);
    slave.trigger();
  }
  if (slave.hasTransactionsCompletedAndAllResultsReady(QUEUE_SIZE)) {
    slave.numBytesReceived();
    mostrarDigito(rx_buf[0], "SPI");
  }
}
