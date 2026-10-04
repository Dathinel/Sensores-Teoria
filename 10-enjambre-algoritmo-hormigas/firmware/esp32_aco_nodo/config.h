// config.h - Todo lo que se puede ajustar del nodo del enjambre, en un solo lugar.
//
// El MISMO sketch (esp32_aco_nodo.ino) se sube a los tres ESP32; lo unico que cambia entre
// ellos es NODO_ID. Hay dos formas de elegirlo:
//   1. Cambiar el valor de abajo antes de subir desde el Arduino IDE.
//   2. Compilar desde la linea de comandos con
//        arduino-cli compile ... --build-property "compiler.cpp.extra_flags=-DNODO_ID=2"
//      (por eso el #define va dentro de #ifndef: si el compilador ya trae NODO_ID, gana ese).
//
// Los parametros del ACO y los tiempos tienen que ser LOS MISMOS que en aco.py (Parametros) y
// protocolo.py: el gemelo digital del PC corre la misma simulacion y anima los carritos con
// esos tiempos; si aqui se cambia uno, hay que cambiarlo alla tambien.
#pragma once

// =============================================================================================
// Identidad del nodo
// =============================================================================================
#ifndef NODO_ID
#define NODO_ID 3   // 1 = punto de acceso (y tambien hormiga), 2 y 3 = estaciones
#endif

#if (NODO_ID < 1) || (NODO_ID > 3)
#error "NODO_ID tiene que ser 1, 2 o 3"
#endif

// =============================================================================================
// Parametros del ACO (mismos valores por defecto que aco.Parametros)
// =============================================================================================
#define ACO_ALFA         1.0     // peso de la feromona
#define ACO_BETA         2.0     // peso de la visibilidad 1/d
#define ACO_RHO          0.5     // evaporacion: queda (1 - rho) por iteracion
#define ACO_Q            100.0   // cada hormiga deja Q / L en cada arista de su camino
#define ACO_HORMIGAS     4       // hormigas por nodo por iteracion
#define ACO_ITERACIONES  30      // iteraciones del enjambre
#define ACO_SEMILLA      12345u  // semilla base (cada nodo deriva la suya con aco_semilla_de_nodo)
#define ACO_TAU0         1.0     // feromona inicial de todas las aristas
#define ACO_SOLO_MEJOR   1       // 1 = solo la mejor hormiga de cada iteracion deposita (por
                                 // defecto); 0 = depositan todas las que llegan (Ant System original)

// =============================================================================================
// Red (iguales a protocolo.py)
// =============================================================================================
#define WIFI_SSID        "ENJAMBRE_ACO"
#define WIFI_CLAVE       "hormigas123"   // WPA2 exige al menos 8 caracteres
#define WIFI_CANAL       1
#define WIFI_MAX_CLIENTES 4              // nodos 2 y 3 + el PC + uno de reserva
// IP fija de cada nodo: 192.168.4.<n>. El PC recibe por DHCP la 192.168.4.100 (el nodo 1
// arranca el reparto de direcciones en .100 justamente para que el PC no tome la .2 o la .3,
// que estan reservadas para los otros carritos).
#define IP_RED_0 192
#define IP_RED_1 168
#define IP_RED_2 4
#define IP_PC_ULTIMO     100
#define PUERTO_NODOS     4210   // entre nodos y comandos del PC
#define PUERTO_TELEMETRIA 4211  // del nodo hacia el PC
#define MAX_DATAGRAMA    1200   // bytes; por debajo de la MTU de WiFi (1500) para no fragmentar
#define REINTENTO_WIFI_MS 5000  // estacion: si sigue desconectada tanto tiempo, se reintenta a mano

// =============================================================================================
// Tiempos del protocolo (iguales a protocolo.py)
// =============================================================================================
#define PERIODO_HELLO_MS      1000
#define PERIODO_ESTADO_MS     1000
#define VIVO_MS               4000   // sin oir nada de un nodo en 4 s, se da por apagado
#define BARRERA_MS            3000   // espera maxima de los FIN de los demas en cada iteracion
#define PAUSA_ITER_MS         300    // pausa entre iteraciones (para que se vea en el gemelo)
#define ARRANQUE_SOLO_MS      30000  // si en 30 s no aparecen los demas, arranca solo
#define HELLO_ESTABLE_MS      2000   // los otros dos tienen que verse al menos este tiempo
#define T_CELDA_MS            1000   // avanzar una celda (20 cm)
#define T_GIRO90_MS           600    // girar 90 grados sobre su eje
#define ESCALON_RECORRIDO_MS  8000   // el carrito n arranca (n-1)*8 s despues, para no chocar
// Si la estacion pierde la red en plena BUSQUEDA (p. ej. se reinicio el nodo 1, que es el AP),
// la iteracion se congela hasta este tope esperando que vuelva; seguir solo de inmediato haria
// que su copia de la feromona se separe de la de los otros. Pasado el tope, sigue solo.
#define SIN_RED_MAX_MS        15000

// =============================================================================================
// Carrito: driver TB6612FNG + dos motores TT
// =============================================================================================
// 1 = mueve los motores de verdad; 0 = hace todo igual (fases, tiempos, celda en ESTADO) pero
// sin energizar el driver. Sirve para probar la red y el ACO con la placa sola en el escritorio.
#ifndef MOVER_CARRITO
#define MOVER_CARRITO 1
#endif

// 1 = ademas de mandarla por UDP, imprime por USB cada linea de telemetria con el prefijo
// "TEL " (la usa preview.html en modo conectado, por Web Serial, con un solo carrito al PC).
#ifndef ECO_SERIAL_TELEMETRIA
#define ECO_SERIAL_TELEMETRIA 1
#endif

// Motor A = rueda IZQUIERDA, motor B = rueda DERECHA.
// Criterio para elegir los pines:
//   - GPIO 12 NO: es pin de strapping (MTDI). Al arrancar fija el voltaje de la flash; si un
//     driver lo deja en alto, el ESP32 elige 1,8 V para una flash de 3,3 V y no arranca.
//   - GPIO 0, 2 y 15 NO para motores: tambien son de strapping (modo de arranque y mensajes del
//     bootloader). Un motor o el driver tirando de ellos en el reset puede dejar la placa en modo
//     descarga o colgada.
//   - GPIO 34-39 NO: son solo de entrada.
//   - GPIO 6-11 NO: van a la flash interna.
#define PIN_PWMA  25   // PWM rueda izquierda (LEDC). Salida libre, sin funcion de arranque
#define PIN_AIN1  26   // sentido rueda izquierda
#define PIN_AIN2  27   // sentido rueda izquierda
#define PIN_PWMB  33   // PWM rueda derecha (LEDC). Salida libre, sin funcion de arranque
#define PIN_BIN1  14   // sentido rueda derecha (en el arranque saca un pulso PWM breve, pero
                       // con STBY en LOW el driver lo ignora: por eso STBY va en otro pin)
#define PIN_BIN2  13   // sentido rueda derecha
#define PIN_STBY  32   // STBY del TB6612: en LOW el puente H queda apagado. Se deja en LOW hasta
                       // que la red esta arriba y fuera de los movimientos
#define PIN_LED   2    // LED azul de la placa. Es de strapping: tiene que estar en bajo o al aire
                       // para poder programar, y el LED con su resistencia a GND lo deja en bajo,
                       // asi que no molesta. Si la placa no trae LED (varias de 38 pines), poner
                       // uno con 330 ohm de GPIO 2 a GND

#define PWM_FREC_HZ     20000  // 20 kHz: fuera del rango audible (los motores no "chillan")
#define PWM_RESOLUCION  8      // 8 bits -> duty 0..255 (a 20 kHz el LEDC admite hasta ~11 bits)
#define VEL_AVANCE      200    // duty al avanzar (0..255). Calibrar con T_CELDA_MS = 20 cm
#define VEL_GIRO        170    // duty al girar sobre su eje. Calibrar con T_GIRO90_MS = 90 grados
#define RAMPA_MS        150    // arranque suave: el duty sube de 0 al valor final en este tiempo
