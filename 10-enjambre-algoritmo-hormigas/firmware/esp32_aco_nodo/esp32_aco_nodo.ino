// esp32_aco_nodo.ino - Un carrito del enjambre de 3 que resuelve el laberinto con ACO
// (optimizacion por colonia de hormigas) compartiendo la feromona por WiFi.
//
// El MISMO sketch va en los tres ESP32; solo cambia NODO_ID (ver config.h). Cada nodo:
//   1. Arma la red: el nodo 1 es el punto de acceso "ENJAMBRE_ACO" (192.168.4.1) y ADEMAS es
//      una hormiga como los otros; los nodos 2 y 3 se conectan como estaciones con IP fija
//      (192.168.4.2 y .3). El PC se conecta a la misma red y recibe la 192.168.4.100.
//   2. Espera a los companeros (fase ESPERA), y cuando estan todos corre las iteraciones del
//      ACO (fase BUSQUEDA): suelta sus hormigas con SU copia de la feromona, manda lo que
//      depositaron (PHER + FIN), espera lo de los otros (barrera) y aplica todo en orden de
//      nodo 1, 2, 3. Como los tres parten de la misma feromona y aplican los mismos depositos en
//      el mismo orden, sus tres copias quedan identicas bit a bit: es una memoria comun sin
//      servidor central (la misma idea que aco.simular_enjambre en el PC).
//   3. Al terminar recorre fisicamente SU mejor ruta, celda por celda, en lazo abierto (fase
//      RECORRIDO), escalonado con los otros para que no choquen, y queda en TERMINADO.
// Mientras tanto manda telemetria al PC (ESTADO cada segundo, copia de HELLO/PHER/FIN/PATH) y
// atiende comandos (CMD;INICIAR, CMD;REINICIAR, CMD;RTT).
//
// El protocolo completo (tipos de mensaje, campos, puertos, tiempos) esta en el docstring de
// protocolo.py; este archivo arma y lee exactamente esas lineas.
//
// Todo el programa es NO bloqueante: loop() da vueltas de pocos milisegundos y cada tarea
// (red, sincronizacion, motores, LED, prueba de latencia) es una maquina de estados que mira
// millis(). Asi el carrito puede estar girando y al mismo tiempo seguir contestando HELLO,
// PING y la barrera de los otros nodos. No hay ningun delay() largo.
//
// Compilar (arduino-cli, nucleo esp32 3.x; placa "ESP32 Dev Module"):
//   arduino-cli compile -b esp32:esp32:esp32
//     --build-property "compiler.cpp.extra_flags=-DNODO_ID=2" firmware/esp32_aco_nodo
//   (todo en una sola linea; firmware/compilar.ps1 compila los tres nodos de una vez)
// o desde el Arduino IDE cambiando NODO_ID en config.h antes de subir a cada placa.
//
// Depuracion: Monitor Serie a 115200 baudios. Se ve la fase, cada iteracion (cuantas hormigas
// llegaron, de que nodos se aplicaron depositos, mejor ruta) y cada celda del recorrido.

#include <WiFi.h>
#include <WiFiUdp.h>
#include <esp_wifi.h>   // esp_wifi_ap_get_sta_list: RSSI de las estaciones (nodo 1)

#include "config.h"
#include "aco_core.h"   // nucleo del ACO (C++ puro, gemelo de aco.py)

// =============================================================================================
// Tipos y estado global
// (todo se declara antes de la primera funcion: el preprocesador del .ino genera prototipos de
// las funciones arriba del primer cuerpo de funcion, y esos prototipos necesitan ver los tipos)
// =============================================================================================

// Fases del nodo. Los textos son los de protocolo.FASES (van en HELLO y ESTADO).
enum Fase { F_ESPERA = 0, F_BUSQUEDA = 1, F_RECORRIDO = 2, F_TERMINADO = 3 };
const char* const NOMBRE_FASE[] = {"ESPERA", "BUSQUEDA", "RECORRIDO", "TERMINADO"};

// Dentro de BUSQUEDA, cada iteracion pasa por tres pasos.
enum PasoBusqueda {
  PB_CALCULAR,   // soltar las hormigas propias y mandar PHER + FIN
  PB_BARRERA,    // esperar los FIN de los companeros vivos (o hasta BARRERA_MS)
  PB_PAUSA       // pausa corta antes de la siguiente iteracion
};

// Lo que se sabe de cada companero (indices 1..3; el propio tambien existe pero no se usa).
struct InfoNodo {
  bool oido = false;            // alguna vez se recibio algo suyo
  uint32_t ultimoMs = 0;        // ultimo mensaje de cualquier tipo (para "vivo")
  bool helloOk = false;         // hay una racha de HELLO con el CRC correcto
  uint32_t primerHelloOkMs = 0; // inicio de esa racha (para exigir HELLO_ESTABLE_MS)
  uint32_t ultimoHelloOkMs = 0;
  int faseHello = F_ESPERA;     // fase que anuncio en su ultimo HELLO
  int iterHello = 0;            // iteraciones aplicadas segun su ultimo HELLO
  uint32_t ultimoAvisoCrcMs = 0;  // para no inundar de LOG si tiene otro mapa
  bool avisadoCrc = false;
};

// Depositos recibidos de UN companero para UNA iteracion. Se guardan indexados por arista (no
// en el orden en que llegaron): asi, aunque los datagramas lleguen desordenados, al aplicarlos
// se recorren en orden de arista, que es el orden en que los suma aco.py. Un PHER repetido cae
// en la misma casilla y no se cuenta dos veces.
struct BufIter {
  int iter = -1;                        // iteracion que guarda esta casilla (-1 = libre)
  bool presente[MAZE_N_ARISTAS];
  int16_t origen[MAZE_N_ARISTAS];
  int16_t destino[MAZE_N_ARISTAS];
  double valor[MAZE_N_ARISTAS];
  int recibidos = 0;                    // PHER distintos que llegaron
  bool invalido = false;                // llego un PHER con una arista que no existe
  bool fin = false;                     // llego su FIN de esta iteracion
  int finNPher = 0, finExitosas = 0, finDescartadas = 0;
};

// Junta lineas en un datagrama de hasta MAX_DATAGRAMA bytes (igual que protocolo.empaquetar):
// cuando la siguiente linea no cabe, se manda lo acumulado y se empieza otro.
struct Empaquetador {
  char buf[MAX_DATAGRAMA + 1];
  size_t len = 0;
  uint8_t mascara = 0;   // a quien va: bit 0 = PC (puerto 4211), bit n = nodo n (puerto 4210)
};

// Movimiento del carrito en RECORRIDO.
enum PasoMovimiento {
  MV_ESCALON,    // esperando su turno: (NODO_ID - 1) * ESCALON_RECORRIDO_MS
  MV_SIGUIENTE,  // decidir el siguiente tramo (girar o avanzar)
  MV_GIRANDO,
  MV_AVANZANDO,
  MV_FIN
};

// Prueba de latencia ida y vuelta (CMD;RTT).
#define RTT_MAX 200
struct EstadoRtt {
  bool activo = false;
  int destino = 0;
  int n = 0;                    // PING a mandar
  uint32_t intervaloMs = 100;
  int enviados = 0;
  int recibidos = 0;
  uint32_t primerSeq = 0;       // seq del primer PING de esta prueba (descarta PONG viejos)
  uint32_t tUltimoEnvioMs = 0;
  float ms[RTT_MAX];            // RTT de cada PING que volvio, en el orden en que volvieron
  bool llego[RTT_MAX];
};

// ---------------------------------------------------------------------------------------------
// Variables globales
// ---------------------------------------------------------------------------------------------
AcoNodo ac;                      // la colonia de este nodo (feromona, rng, mejor ruta)
WiFiUDP udp;

Fase fase = F_ESPERA;
PasoBusqueda pasoBusqueda = PB_CALCULAR;
uint32_t tBarreraMs = 0;         // cuando empezo la barrera de la iteracion en curso
uint32_t tPausaMs = 0;
double mejorAnunciada = INFINITY;  // ultima mejor longitud que se mando en un PATH

InfoNodo nodos[ACO_MAX_NODOS + 1];
// Dos casillas por companero: la iteracion en curso (k) y la siguiente (k+1), porque un
// companero mas rapido puede mandar la k+1 antes de que este nodo cierre la k. La casilla se
// elige por paridad de la iteracion (k & 1), asi k y k+1 nunca se pisan.
BufIter buffers[ACO_MAX_NODOS + 1][2];

// Red
bool redArribaAntes = false;     // estado de la red en la vuelta anterior (para ver cambios)
bool redVistaArriba = false;     // la red estuvo arriba al menos una vez (habilita motores)
uint32_t tRedCaidaMs = 0;
uint32_t tUltimoReintentoMs = 0;
uint32_t tUltimoHelloMs = 0;
uint32_t tUltimoEstadoMs = 0;
char rx[1501];                   // datagrama recibido (+1 para el '\0')

// Recorrido
PasoMovimiento pasoMov = MV_ESCALON;
int16_t ruta[MAZE_N_CELDAS];     // ruta que va a recorrer el carrito
int rutaN = 0;
int rutaIdx = 0;                 // indice de la celda en la que esta
int celdaActual = MAZE_INICIO;
int rumboX = 1, rumboY = 0;      // arranca mirando hacia +x (igual que protocolo.tiempo_recorrido)
uint32_t tRecorridoMs = 0;       // cuando entro a RECORRIDO
uint32_t tMovMs = 0;             // cuando empezo el tramo actual (se acumula, no se reinicia)
uint32_t durMovMs = 0;           // duracion del tramo actual

// Motores
int motorSentIzq = 0, motorSentDer = 0;  // +1 adelante, -1 atras, 0 parado
int motorDutyObjetivo = 0;
uint32_t tArranqueMotorMs = 0;   // inicio de la rampa del tramo actual

EstadoRtt rtt;
uint32_t seqPing = 1;

// ---------------------------------------------------------------------------------------------
// Prototipos (el .ino los generaria solo, pero asi queda explicito el orden de dependencias)
// ---------------------------------------------------------------------------------------------
void enviarMascara(uint8_t mascara, const char* datos, size_t len);
void enviarLog(const char* fmt, ...);
void iniciarBusqueda(const char* motivo);
void entrarRecorrido();
void pararMotores();
bool esperandoRed();

// =============================================================================================
// Utilidades de red
// =============================================================================================

IPAddress ipNodo(int n) { return IPAddress(IP_RED_0, IP_RED_1, IP_RED_2, n); }
IPAddress ipPc() { return IPAddress(IP_RED_0, IP_RED_1, IP_RED_2, IP_PC_ULTIMO); }

// "Red arriba": el nodo 1 es el punto de acceso, su red existe desde que se levanto el AP.
// Una estacion esta arriba solo si esta asociada al AP (y con su IP fija ya puesta).
bool redArriba() {
#if NODO_ID == 1
  return true;
#else
  return WiFi.status() == WL_CONNECTED;
#endif
}

// Vivo = se oyo CUALQUIER mensaje suyo en los ultimos VIVO_MS. La resta de uint32_t funciona
// aunque millis() de la vuelta (a los 49 dias): la diferencia sale bien en aritmetica modular.
bool vivo(int n) {
  if (n == NODO_ID) return true;
  if (n < 1 || n > ACO_MAX_NODOS || !nodos[n].oido) return false;
  return (uint32_t)(millis() - nodos[n].ultimoMs) < VIVO_MS;
}

void marcarOido(int n) {
  if (n < 1 || n > ACO_MAX_NODOS || n == NODO_ID) return;
  nodos[n].oido = true;
  nodos[n].ultimoMs = millis();
}

// Mascara con los companeros (sin incluirse a si mismo). soloVivos = solo los que se oyen.
uint8_t mascaraCompaneros(bool soloVivos) {
  uint8_t m = 0;
  for (int n = 1; n <= ACO_MAX_NODOS; n++) {
    if (n == NODO_ID) continue;
    if (soloVivos && !vivo(n)) continue;
    m |= (uint8_t)(1u << n);
  }
  return m;
}

// Envio UNICAST a cada destino de la mascara. No se usa broadcast a proposito: en WiFi un
// broadcast se manda una sola vez, a la velocidad mas baja, sin ACK ni reintentos de la capa
// MAC, asi que se pierde bastante mas; un unicast lo reintenta el propio radio hasta ~7 veces.
void enviarMascara(uint8_t mascara, const char* datos, size_t len) {
  if (len == 0) return;
  // Primero la red: lo que esperan los companeros (PHER/FIN de la barrera) sale sin demora. El
  // eco por USB va despues, porque si el buffer del Serial se llena, Serial.write espera.
  if (redArriba()) {
    for (int n = 0; n <= ACO_MAX_NODOS; n++) {
      if (!(mascara & (1u << n))) continue;
      if (n == NODO_ID) continue;
      IPAddress ip = (n == 0) ? ipPc() : ipNodo(n);
      uint16_t puerto = (n == 0) ? PUERTO_TELEMETRIA : PUERTO_NODOS;
      udp.beginPacket(ip, puerto);
      udp.write((const uint8_t*)datos, len);
      udp.endPacket();  // si el destino no esta (ARP sin respuesta) falla en silencio: es UDP
    }
  }
#if ECO_SERIAL_TELEMETRIA
  // Copia por USB de todo lo que va al PC, una linea por mensaje con el prefijo "TEL ". La lee
  // preview.html por Web Serial (modo conectado) con UN solo carrito enchufado al PC; sale
  // aunque el WiFi no este arriba (por eso no depende de redArriba()).
  if (mascara & 1u) {
    Serial.print("TEL ");
    for (size_t i = 0; i < len; i++) {
      Serial.write(datos[i]);
      if (datos[i] == '\n') Serial.print("TEL ");
    }
    Serial.print('\n');
  }
#endif
}

void enviarLinea(uint8_t mascara, const char* linea) { enviarMascara(mascara, linea, strlen(linea)); }

void paqIniciar(Empaquetador& p, uint8_t mascara) {
  p.len = 0;
  p.mascara = mascara;
  p.buf[0] = '\0';
}

void paqVaciar(Empaquetador& p) {
  if (p.len == 0) return;
  enviarMascara(p.mascara, p.buf, p.len);
  p.len = 0;
  p.buf[0] = '\0';
}

// Agrega una linea; si con ella el datagrama pasaria de MAX_DATAGRAMA, primero manda lo que
// habia. Las lineas se separan con '\n' y no se parte ninguna (igual que protocolo.empaquetar).
void paqAgregar(Empaquetador& p, const char* linea) {
  size_t n = strlen(linea);
  if (n == 0 || n > MAX_DATAGRAMA) return;  // ninguna linea del protocolo llega a ese tamano
  size_t necesario = p.len ? p.len + 1 + n : n;
  if (necesario > MAX_DATAGRAMA) paqVaciar(p);
  if (p.len) p.buf[p.len++] = '\n';
  memcpy(p.buf + p.len, linea, n);
  p.len += n;
  p.buf[p.len] = '\0';
}

// LOG;nodo;texto al PC y tambien por Serial (es lo primero que uno mira cuando algo falla).
void enviarLog(const char* fmt, ...) {
  char texto[200];
  va_list args;
  va_start(args, fmt);
  vsnprintf(texto, sizeof(texto), fmt, args);
  va_end(args);
  // ';' separa campos: si el texto trajera uno, el PC igual lo junta (LOG toma el resto de la
  // linea), pero un '\n' partiria el mensaje en dos, asi que se reemplaza.
  for (char* c = texto; *c; c++)
    if (*c == '\n' || *c == '\r') *c = ' ';
  char linea[240];
  snprintf(linea, sizeof(linea), "LOG;%d;%s", NODO_ID, texto);
  enviarLinea(1u, linea);
  Serial.printf("[LOG] %s\n", texto);
}

// RSSI que se reporta en ESTADO, PONG y RTT.
//  - Estacion: la potencia con que oye al AP (WiFi.RSSI()).
//  - Nodo 1 (AP): no tiene "un" enlace sino uno por estacion; se promedia el RSSI con que oye a
//    cada estacion asociada (incluido el PC). 0 si no hay nadie conectado.
int rssiPropio() {
#if NODO_ID == 1
  wifi_sta_list_t lista;
  if (esp_wifi_ap_get_sta_list(&lista) != ESP_OK || lista.num <= 0) return 0;
  int suma = 0;
  for (int i = 0; i < lista.num; i++) suma += lista.sta[i].rssi;
  return suma / lista.num;
#else
  return redArriba() ? (int)WiFi.RSSI() : 0;
#endif
}

// Camino "0,1,2,..." en un buffer (para PATH y para el Serial).
void formatearCamino(const int16_t* c, int n, char* out, size_t tam) {
  size_t len = 0;
  out[0] = '\0';
  for (int i = 0; i < n && len + 8 < tam; i++) {
    len += snprintf(out + len, tam - len, i ? ",%d" : "%d", (int)c[i]);
  }
}

// Divide una linea en campos separados por ';' (modifica la linea, cambia ';' por '\0').
// Devuelve cuantos campos hay. Si hay mas de 'max', el ultimo se queda con el resto.
int partirCampos(char* s, char** campos, int max) {
  int n = 0;
  campos[n++] = s;
  for (char* c = s; *c && n < max; c++) {
    if (*c == ';') {
      *c = '\0';
      campos[n++] = c + 1;
    }
  }
  return n;
}

// =============================================================================================
// Mensajes que manda el nodo
// =============================================================================================

// HELLO;nodo;crc;iter;fase  a los dos companeros (vivos o no: es justamente como se descubren)
// y una copia al PC. El CRC es la huella del mapa (maze_data.h): si un companero se flasheo con
// otro laberinto, sus depositos no tendrian sentido aqui, y por eso un HELLO con otro CRC se
// ignora.
void enviarHello() {
  char linea[64];
  snprintf(linea, sizeof(linea), "HELLO;%d;%08lX;%d;%s", NODO_ID, (unsigned long)MAZE_CRC,
           ac.iteracion, NOMBRE_FASE[fase]);
  enviarLinea((uint8_t)(mascaraCompaneros(false) | 1u), linea);
}

// PATH;nodo;longitud;c0,...,cn  (longitud en metros con 3 decimales, -1.000 si aun no hay).
void armarPath(char* linea, size_t tam) {
  char camino[MAZE_N_CELDAS * 4 + 4];
  formatearCamino(ac.mejor_camino, ac.mejor_n, camino, sizeof(camino));
  double lon = (ac.mejor_n > 0 && !isinf(ac.mejor_longitud)) ? ac.mejor_longitud : -1.0;
  snprintf(linea, tam, "PATH;%d;%.3f;%s", NODO_ID, lon, camino);
}

// ESTADO;nodo;fase;iter;mejor_long;celda;rssi;vivos;uptime_ms  + PATH (si ya hay ruta) en el
// mismo datagrama al PC. Repetir el PATH cada segundo hace que el gemelo lo tenga aunque se
// haya perdido el que se mando cuando mejoro (o aunque el PC se conecte tarde).
void enviarEstado() {
  char vivos[16];
  size_t len = 0;
  vivos[0] = '\0';
  for (int n = 1; n <= ACO_MAX_NODOS; n++) {
    if (!vivo(n)) continue;
    len += snprintf(vivos + len, sizeof(vivos) - len, len ? ",%d" : "%d", n);
  }
  double mejor = (ac.mejor_n > 0 && !isinf(ac.mejor_longitud)) ? ac.mejor_longitud : -1.0;
  char linea[160];
  snprintf(linea, sizeof(linea), "ESTADO;%d;%s;%d;%.3f;%d;%d;%s;%lu", NODO_ID, NOMBRE_FASE[fase],
           ac.iteracion, mejor, celdaActual, rssiPropio(), vivos, (unsigned long)millis());
  Empaquetador p;
  paqIniciar(p, 1u);
  paqAgregar(p, linea);
  if (ac.mejor_n > 0) {
    char path[MAZE_N_CELDAS * 4 + 48];
    armarPath(path, sizeof(path));
    paqAgregar(p, path);
  }
  paqVaciar(p);
}

// TAU;nodo;iter;t0,...,t28  a un companero que se reinicio, para que retome la feromona comun.
// Cada valor con 17 cifras significativas: es lo minimo que garantiza que strtod del otro lado
// reconstruya EXACTAMENTE el mismo double (con menos, las copias se separarian en el ultimo bit
// y mas adelante una hormiga podria elegir distinto en cada nodo).
void enviarTau(int destino) {
  static char linea[MAX_DATAGRAMA + 1];
  size_t len = snprintf(linea, sizeof(linea), "TAU;%d;%d;", NODO_ID, ac.iteracion);
  for (int e = 0; e < MAZE_N_ARISTAS && len < sizeof(linea); e++) {
    len += snprintf(linea + len, sizeof(linea) - len, e ? ",%.17g" : "%.17g", ac.tau[e]);
  }
  if (len >= sizeof(linea)) return;  // no pasa con 29 aristas (~700 bytes), pero por si acaso
  enviarLinea((uint8_t)(1u << destino), linea);
  enviarLog("TAU a nodo %d (iteracion %d) para que retome la feromona", destino, ac.iteracion);
}

// =============================================================================================
// Recepcion de depositos (PHER / FIN) y barrera
// =============================================================================================

int iterEnCurso() { return ac.iteracion + 1; }

// Casilla del companero n para la iteracion it; si tenia otra iteracion vieja, se limpia.
BufIter& casilla(int n, int it) {
  BufIter& b = buffers[n][it & 1];
  if (b.iter != it) {
    b.iter = it;
    memset(b.presente, 0, sizeof(b.presente));
    b.recibidos = 0;
    b.invalido = false;
    b.fin = false;
    b.finNPher = b.finExitosas = b.finDescartadas = 0;
  }
  return b;
}

// Decide si un PHER/FIN de la iteracion 'it' se guarda. Solo sirven la iteracion en curso y la
// siguiente; las viejas ya se aplicaron (o se dieron por perdidas) y no se pueden "deshacer".
bool iteracionAceptable(int it) {
  if (fase != F_ESPERA && fase != F_BUSQUEDA) return false;
  int k = iterEnCurso();
  return it == k || it == k + 1;
}

// Un nodo en ESPERA (recien encendido, ac.iteracion == 0) que ve depositos de la iteracion 1
// sabe que los demas ya arrancaron: arranca de inmediato para no quedarse fuera de la barrera.
void quizasArrancarPorDepositos(int it) {
  if (fase == F_ESPERA && ac.iteracion == 0 && it == 1) {
    iniciarBusqueda("llegaron depositos de la iteracion 1 (los otros ya empezaron)");
  }
}

void recibirPher(int n, int it, int origen, int destino, double valor) {
  quizasArrancarPorDepositos(it);
  if (!iteracionAceptable(it)) return;
  BufIter& b = casilla(n, it);
  // Validar ANTES de buscar la arista: aristaEntre indexa MAZE_N_VECINOS[origen] y un numero
  // fuera de rango leeria memoria cualquiera.
  if (origen < 0 || origen >= MAZE_N_CELDAS || destino < 0 || destino >= MAZE_N_CELDAS) {
    b.invalido = true;
    return;
  }
  int e = AcoNodo::aristaEntre(origen, destino);
  if (e < 0) {
    b.invalido = true;  // arista inexistente: seguramente otro mapa; no se aplica nada de el
    return;
  }
  if (b.presente[e]) return;  // repetido
  b.presente[e] = true;
  b.origen[e] = (int16_t)origen;
  b.destino[e] = (int16_t)destino;
  b.valor[e] = valor;
  b.recibidos++;
}

void recibirFin(int n, int it, int nPher, int exitosas, int descartadas) {
  quizasArrancarPorDepositos(it);
  if (!iteracionAceptable(it)) return;
  BufIter& b = casilla(n, it);
  b.fin = true;
  b.finNPher = nPher;
  b.finExitosas = exitosas;
  b.finDescartadas = descartadas;
}

// Paso 1 de la iteracion k: soltar las hormigas propias y mandar lo que depositaron.
void calcularIteracion() {
  const int k = iterEnCurso();
  ac.iteracionLocal();  // NO toca la feromona: deja los depositos en ac.depositos[]

  // PHER de cada arista tocada + FIN que dice cuantos PHER eran. Van a los companeros vivos y
  // al PC (el PC los usa para animar la feromona en el gemelo). Todo empaquetado en datagramas
  // de hasta 1200 bytes; el FIN va al final del ultimo, asi cuando el otro lee el FIN ya
  // recibio (si nada se perdio) todos los PHER anteriores.
  Empaquetador p;
  paqIniciar(p, (uint8_t)(mascaraCompaneros(true) | 1u));
  char linea[96];
  for (int i = 0; i < ac.n_depositos; i++) {
    const AcoDeposito& d = ac.depositos[i];
    snprintf(linea, sizeof(linea), "PHER;%d;%d;%d;%d;%.17g", NODO_ID, k, (int)d.origen,
             (int)d.destino, d.valor);
    paqAgregar(p, linea);
  }
  snprintf(linea, sizeof(linea), "FIN;%d;%d;%d;%d;%d", NODO_ID, k, ac.n_depositos, ac.exitosas,
           ac.descartadas);
  paqAgregar(p, linea);
  paqVaciar(p);

  // La mejor ruta propia cambia en iteracionLocal: si mejoro, se avisa ya (al PC y a los
  // companeros) sin esperar al proximo ESTADO.
  if (ac.mejor_n > 0 && ac.mejor_longitud < mejorAnunciada - 1e-12) {
    mejorAnunciada = ac.mejor_longitud;
    char path[MAZE_N_CELDAS * 4 + 48];
    armarPath(path, sizeof(path));
    enviarLinea((uint8_t)(mascaraCompaneros(false) | 1u), path);
    Serial.printf("  nueva mejor ruta propia: %s\n", path);
  }

  tBarreraMs = millis();
  pasoBusqueda = PB_BARRERA;
}

// Paso 2: la barrera esta lista cuando llego el FIN k de cada companero vivo. Un companero que
// no se oye hace VIVO_MS ya no se espera (prueba 14: si se apaga uno, los otros siguen), y uno
// que ya anuncia RECORRIDO o TERMINADO tampoco: termino su busqueda y no va a mandar mas FIN.
// Llegar el FIN no basta: si los PHER venian en dos datagramas y el segundo (con el FIN) llego
// antes que el primero, faltan PHER todavia. Se da por completo cuando la cuenta coincide con
// n_pher (o cuando ya se sabe que ese nodo no se va a poder aplicar: un PHER invalido).
bool barreraCompleta(int k) {
  for (int n = 1; n <= ACO_MAX_NODOS; n++) {
    if (n == NODO_ID || !vivo(n)) continue;
    if (nodos[n].faseHello >= F_RECORRIDO) continue;
    const BufIter& b = buffers[n][k & 1];
    if (!(b.iter == k && b.fin && (b.recibidos == b.finNPher || b.invalido))) return false;
  }
  return true;
}

// Paso 2 (cierre): evaporar y sumar los depositos de cada nodo, en orden 1, 2, 3.
void aplicarIteracion(int k) {
  static AcoDeposito recibidos[ACO_MAX_NODOS + 1][MAZE_N_ARISTAS];
  const AcoDeposito* porNodo[ACO_MAX_NODOS + 1] = {nullptr, nullptr, nullptr, nullptr};
  int cuantos[ACO_MAX_NODOS + 1] = {0, 0, 0, 0};

  // Los propios: exactamente los mismos double que se mandaron en los PHER (y como "%.17g" +
  // strtod es exacto, los otros nodos suman el mismo numero bit a bit).
  porNodo[NODO_ID] = ac.depositos;
  cuantos[NODO_ID] = ac.n_depositos;

  char aplicados[16] = "";
  size_t lenAp = 0;
  for (int n = 1; n <= ACO_MAX_NODOS; n++) {
    if (n == NODO_ID) {
      lenAp += snprintf(aplicados + lenAp, sizeof(aplicados) - lenAp, lenAp ? ",%d" : "%d", n);
      continue;
    }
    BufIter& b = buffers[n][k & 1];
    bool hayAlgo = (b.iter == k) && (b.fin || b.recibidos > 0);
    // Todo o nada: se aplica un companero solo si llego su FIN y la cuenta de PHER coincide.
    // Aplicar la mitad de sus depositos dejaria esta copia de la feromona distinta de la de los
    // nodos a los que si les llego todo, y la "memoria comun" se partiria.
    if (b.iter == k && b.fin && !b.invalido && b.recibidos == b.finNPher) {
      int c = 0;
      for (int e = 0; e < MAZE_N_ARISTAS; e++) {   // en orden de arista, como aco.py
        if (!b.presente[e]) continue;
        recibidos[n][c].arista = (int16_t)e;
        recibidos[n][c].origen = b.origen[e];
        recibidos[n][c].destino = b.destino[e];
        recibidos[n][c].valor = b.valor[e];
        c++;
      }
      porNodo[n] = recibidos[n];
      cuantos[n] = c;
      lenAp += snprintf(aplicados + lenAp, sizeof(aplicados) - lenAp, lenAp ? ",%d" : "%d", n);
    } else if (hayAlgo) {
      if (!b.fin) {
        enviarLog("iter %d: del nodo %d llegaron %d PHER pero no su FIN; no se aplica", k, n,
                  b.recibidos);
      } else if (b.invalido) {
        enviarLog("iter %d: el nodo %d mando un PHER con una arista que no existe; no se aplica",
                  k, n);
      } else {
        enviarLog("iter %d: del nodo %d llegaron %d de %d PHER; no se aplica", k, n, b.recibidos,
                  b.finNPher);
      }
    } else if (vivo(n)) {
      enviarLog("iter %d: el nodo %d esta vivo pero no llego nada suyo en %d ms", k, n,
                BARRERA_MS);
    }
    if (b.iter == k) b.iter = -1;  // casilla libre para la iteracion k + 2
  }

  ac.aplicarIteracion(porNodo, cuantos);

  char camino[MAZE_N_CELDAS * 4 + 4];
  formatearCamino(ac.mejor_camino, ac.mejor_n, camino, sizeof(camino));
  Serial.printf("[iter %d/%d] hormigas ok=%d descartadas=%d | aplicados nodos {%s} | mejor %s m: %s\n",
                ac.iteracion, ac.p.iteraciones, ac.exitosas, ac.descartadas, aplicados,
                ac.mejor_n ? String(ac.mejor_longitud, 3).c_str() : "-", camino);

  tPausaMs = millis();
  pasoBusqueda = PB_PAUSA;
}

// Devuelve true mientras la busqueda tiene que quedarse quieta esperando la red. Caso tipico:
// se reinicia el nodo 1 (que es el AP) y los nodos 2 y 3 quedan sin red. Si siguieran iterando
// cada uno por su cuenta, sus copias de la feromona se separarian y al volver la red ya no
// serian una memoria comun. Por eso se congelan hasta SIN_RED_MAX_MS; si la red no vuelve en
// ese tiempo, se asume que no va a volver pronto y el nodo sigue solo (mejor una ruta propia
// que un carrito parado para siempre). En el nodo 1 redArriba() es siempre true.
bool esperandoRed() {
  static bool esperando = false;   // hay una espera en curso
  static bool rendido = false;     // se paso el tope en esta caida: seguir solo
  static uint32_t desdeMs = 0;
  if (redArriba()) {
    if (esperando || rendido) enviarLog("volvio la red: la busqueda sigue normalmente");
    esperando = rendido = false;
    return false;
  }
  if (rendido) return false;
  if (!esperando) {
    esperando = true;
    desdeMs = millis();
    Serial.printf("Sin red en BUSQUEDA: iteracion %d en pausa (hasta %d ms)\n", iterEnCurso(),
                  SIN_RED_MAX_MS);
  }
  if ((uint32_t)(millis() - desdeMs) >= SIN_RED_MAX_MS) {
    rendido = true;
    esperando = false;
    enviarLog("sin red hace %d ms: sigo la busqueda solo", SIN_RED_MAX_MS);
    return false;
  }
  return true;
}

void actualizarBusqueda() {
  switch (pasoBusqueda) {
    case PB_CALCULAR:
      if (esperandoRed()) break;  // sin red no se empieza una iteracion que nadie va a recibir
      calcularIteracion();
      break;
    case PB_BARRERA: {
      const int k = iterEnCurso();
      if (esperandoRed()) {
        // Mientras no haya red, la barrera se congela: se reinicia su reloj para que, cuando
        // vuelva, los companeros tengan los BARRERA_MS completos para mandar su FIN.
        tBarreraMs = millis();
        break;
      }
      if (barreraCompleta(k) || (uint32_t)(millis() - tBarreraMs) >= BARRERA_MS) {
        aplicarIteracion(k);
      }
      break;
    }
    case PB_PAUSA:
      if ((uint32_t)(millis() - tPausaMs) >= PAUSA_ITER_MS) {
        if (ac.iteracion >= ac.p.iteraciones) {
          entrarRecorrido();
        } else {
          pasoBusqueda = PB_CALCULAR;
        }
      }
      break;
  }
}

void iniciarBusqueda(const char* motivo) {
  if (fase != F_ESPERA) return;
  fase = F_BUSQUEDA;
  pasoBusqueda = PB_CALCULAR;
  enviarLog("BUSQUEDA desde la iteracion %d: %s", iterEnCurso(), motivo);
}

// Condicion (a) para salir de ESPERA: los otros dos mandaron HELLO con el mismo CRC sin cortes
// durante al menos HELLO_ESTABLE_MS. Si alguno ya anuncia BUSQUEDA, este nodo es el que se
// reinicio a mitad de camino: no debe arrancar desde la iteracion 1 por su cuenta, sino esperar
// el TAU (que llega al segundo, en cuanto los otros oyen su HELLO) o los depositos de la
// iteracion 1 si justo estan empezando.
bool companerosListos() {
  uint32_t ahora = millis();
  for (int n = 1; n <= ACO_MAX_NODOS; n++) {
    if (n == NODO_ID) continue;
    const InfoNodo& in = nodos[n];
    if (!in.helloOk) return false;
    if ((uint32_t)(ahora - in.ultimoHelloOkMs) >= VIVO_MS) return false;
    if ((uint32_t)(ahora - in.primerHelloOkMs) < HELLO_ESTABLE_MS) return false;
    // Lo mismo si ya anuncia RECORRIDO o TERMINADO: la busqueda termino sin este nodo (que se
    // reinicio, p. ej. por un brownout en pleno recorrido). Arrancar de cero lo haria buscar
    // solo ~100 s y repetir el recorrido desde la celda 0; en cambio espera el TAU final.
    if (in.faseHello >= F_BUSQUEDA) return false;
  }
  return true;
}

// Puede contestar un TAU el nodo que tiene la feromona comun al dia: el que esta en BUSQUEDA, o
// el que ya la termino completa (RECORRIDO/TERMINADO con todas las iteraciones aplicadas).
bool puedeDarTau(int faseNodo, int iterNodo) {
  if (faseNodo == F_BUSQUEDA) return true;
  return faseNodo >= F_RECORRIDO && iterNodo >= ac.p.iteraciones;
}

// Reingreso: de los nodos que pueden dar el TAU, solo el vivo de menor id lo manda (si
// contestaran todos, el reiniciado recibiria dos TAU iguales; no pasa nada, pero es trafico).
bool soyMenorEnBusqueda() {
  for (int n = 1; n < NODO_ID; n++) {
    if (vivo(n) && puedeDarTau(nodos[n].faseHello, nodos[n].iterHello)) return false;
  }
  return true;
}

// Un nodo en ESPERA adopta la feromona comun que le manda un companero y sigue desde ahi.
void recibirTau(int n, int it, char* lista) {
  if (fase != F_ESPERA) return;
  double t[MAZE_N_ARISTAS];
  int c = 0;
  char* p = lista;
  while (*p && c < MAZE_N_ARISTAS + 1) {
    char* fin = nullptr;
    double v = strtod(p, &fin);  // strtod lee exacto lo que escribio "%.17g"
    if (fin == p) break;
    if (c < MAZE_N_ARISTAS) t[c] = v;
    c++;
    p = fin;
    if (*p == ',') p++;
  }
  if (c != MAZE_N_ARISTAS || it < 0) {
    enviarLog("TAU del nodo %d con %d valores (se esperaban %d); se ignora", n, c,
              MAZE_N_ARISTAS);
    return;
  }
  memcpy(ac.tau, t, sizeof(t));
  ac.iteracion = it;
  enviarLog("adopto la feromona del nodo %d (iteracion %d)", n, it);
  if (ac.iteracion >= ac.p.iteraciones) {
    // La busqueda ya termino: este nodo se reinicio despues (p. ej. por un brownout en pleno
    // recorrido). NO se vuelve a recorrer: el carrito quedo en algun lugar del laberinto que no
    // se conoce (lazo abierto, sin sensores), y salir "desde la celda 0" lo haria chocar. Se
    // queda en TERMINADO con los motores apagados, y como mejor ruta reporta la que marca la
    // feromona comun (camino codicioso), que es lo que el enjambre aprendio.
    int16_t camino[MAZE_N_CELDAS];
    int nc = ac.caminoCodicioso(camino);
    if (nc > 0) {
      double L = 0.0;
      for (int i = 0; i + 1 < nc; i++) L += MAZE_LONGITUD[AcoNodo::aristaEntre(camino[i], camino[i + 1])];
      memcpy(ac.mejor_camino, camino, nc * sizeof(int16_t));
      ac.mejor_n = nc;
      ac.mejor_longitud = L;
      mejorAnunciada = L;
    }
    pararMotores();
    pasoMov = MV_FIN;
    fase = F_TERMINADO;
    enviarLog("reinicio con la busqueda ya terminada: paso a TERMINADO sin mover el carrito "
              "(no se sabe en que celda quedo); mi ruta es la del camino codicioso");
    if (ac.mejor_n > 0) {
      char path[MAZE_N_CELDAS * 4 + 48];
      armarPath(path, sizeof(path));
      enviarLinea((uint8_t)(mascaraCompaneros(false) | 1u), path);
    }
  } else {
    iniciarBusqueda("reingreso con TAU");
  }
}

// =============================================================================================
// Motores (TB6612FNG)
// =============================================================================================

void iniciarMotores() {
  // STBY en LOW lo primero de todo: mientras el ESP32 arranca los pines quedan flotando o con
  // pulsos del bootloader, y con el driver dormido nada de eso llega a los motores.
  pinMode(PIN_STBY, OUTPUT);
  digitalWrite(PIN_STBY, LOW);
  pinMode(PIN_AIN1, OUTPUT);
  pinMode(PIN_AIN2, OUTPUT);
  pinMode(PIN_BIN1, OUTPUT);
  pinMode(PIN_BIN2, OUTPUT);
  digitalWrite(PIN_AIN1, LOW);
  digitalWrite(PIN_AIN2, LOW);
  digitalWrite(PIN_BIN1, LOW);
  digitalWrite(PIN_BIN2, LOW);
  // API LEDC del nucleo 3.x: el canal lo asigna solo el nucleo, se trabaja por pin.
  ledcAttach(PIN_PWMA, PWM_FREC_HZ, PWM_RESOLUCION);
  ledcAttach(PIN_PWMB, PWM_FREC_HZ, PWM_RESOLUCION);
  ledcWrite(PIN_PWMA, 0);
  ledcWrite(PIN_PWMB, 0);
}

// Sentido de una rueda en el TB6612: IN1=H IN2=L adelante, IN1=L IN2=H atras, L/L libre.
void sentidoRueda(int in1, int in2, int sentido) {
  digitalWrite(in1, sentido > 0 ? HIGH : LOW);
  digitalWrite(in2, sentido < 0 ? HIGH : LOW);
}

// Empieza un movimiento nuevo. El duty no se aplica de golpe: actualizarMotores() lo sube en
// una rampa de RAMPA_MS. El arranque de dos motores TT a pleno pide un pico de corriente que
// hace caer la bateria, y si el ESP32 comparte esa alimentacion el detector de brownout lo
// reinicia en medio del recorrido.
//
// Si el tramo nuevo es igual al anterior (dos celdas rectas seguidas: mismo sentido en las dos
// ruedas y mismo duty) no se toca nada y el carrito sigue de largo. Poner PWM en 0 con IN1/IN2
// ya fijados es FRENO CORTO en el TB6612 (cortocircuita el motor): frenaria en seco en cada
// celda y volveria a arrancar con rampa, perdiendo distancia y tirones de corriente.
void moverRuedas(int sentIzq, int sentDer, int duty) {
  if ((sentIzq || sentDer) && sentIzq == motorSentIzq && sentDer == motorSentDer &&
      duty == motorDutyObjetivo) {
    return;
  }
  motorSentIzq = sentIzq;
  motorSentDer = sentDer;
  motorDutyObjetivo = duty;
  tArranqueMotorMs = millis();
#if MOVER_CARRITO
  if (!redVistaArriba) return;  // nunca se energizan antes de que la red este arriba
  ledcWrite(PIN_PWMA, 0);       // la rampa empieza en 0 (tambien al cambiar de sentido)
  ledcWrite(PIN_PWMB, 0);
  sentidoRueda(PIN_AIN1, PIN_AIN2, sentIzq);
  sentidoRueda(PIN_BIN1, PIN_BIN2, sentDer);
  digitalWrite(PIN_STBY, (sentIzq || sentDer) ? HIGH : LOW);
#endif
}

void pararMotores() {
  motorSentIzq = motorSentDer = 0;
  motorDutyObjetivo = 0;
#if MOVER_CARRITO
  ledcWrite(PIN_PWMA, 0);
  ledcWrite(PIN_PWMB, 0);
  sentidoRueda(PIN_AIN1, PIN_AIN2, 0);
  sentidoRueda(PIN_BIN1, PIN_BIN2, 0);
  digitalWrite(PIN_STBY, LOW);  // driver dormido: no consume ni deja pasar nada
#endif
}

// Rampa: duty = objetivo * (tiempo desde el arranque / RAMPA_MS), hasta llegar al objetivo.
void actualizarMotores() {
#if MOVER_CARRITO
  if (!redVistaArriba || (motorSentIzq == 0 && motorSentDer == 0)) return;
  uint32_t dt = millis() - tArranqueMotorMs;
  uint32_t duty = (dt >= RAMPA_MS) ? (uint32_t)motorDutyObjetivo
                                   : (uint32_t)motorDutyObjetivo * dt / RAMPA_MS;
  ledcWrite(PIN_PWMA, motorSentIzq ? duty : 0);
  ledcWrite(PIN_PWMB, motorSentDer ? duty : 0);
#endif
}

// =============================================================================================
// Recorrido de la mejor ruta (lazo abierto, mismos tiempos que protocolo.tiempo_recorrido)
// =============================================================================================

void entrarRecorrido() {
  fase = F_RECORRIDO;
  if (ac.mejor_n > 0) {
    rutaN = ac.mejor_n;
    memcpy(ruta, ac.mejor_camino, rutaN * sizeof(int16_t));
  } else {
    // Ninguna hormiga propia llego a la meta (p. ej. el nodo entro con TAU al final): se usa el
    // camino que marca la feromona comun, que es lo que el enjambre "sabe".
    rutaN = ac.caminoCodicioso(ruta);
  }
  rutaIdx = 0;
  celdaActual = MAZE_INICIO;
  rumboX = 1;
  rumboY = 0;
  tRecorridoMs = millis();
  pasoMov = MV_ESCALON;
  char camino[MAZE_N_CELDAS * 4 + 4];
  formatearCamino(ruta, rutaN, camino, sizeof(camino));
  enviarLog("RECORRIDO: arranca en %d ms por %s", (NODO_ID - 1) * ESCALON_RECORRIDO_MS, camino);
}

void terminarRecorrido() {
  pararMotores();
  pasoMov = MV_FIN;
  fase = F_TERMINADO;
  enviarLog("TERMINADO en la celda %d", celdaActual);
}

void actualizarRecorrido() {
  // Bucle porque un tramo que termina puede encadenar de inmediato el siguiente en la misma
  // vuelta de loop() (sin perder ni un milisegundo frente a los tiempos del gemelo).
  for (int guarda = 0; guarda < 4; guarda++) {
    uint32_t ahora = millis();
    switch (pasoMov) {
      case MV_ESCALON:
        // Escalonado: el carrito n espera (n-1)*8 s, asi no estan dos en la misma celda.
        if ((uint32_t)(ahora - tRecorridoMs) < (uint32_t)(NODO_ID - 1) * ESCALON_RECORRIDO_MS)
          return;
        // El tramo arranca en el instante teorico del escalon (no en 'ahora'), para que unos ms
        // de atraso de esta vuelta de loop() no corran todas las llegadas del recorrido.
        tMovMs = tRecorridoMs + (uint32_t)(NODO_ID - 1) * ESCALON_RECORRIDO_MS;
        durMovMs = 0;
        pasoMov = MV_SIGUIENTE;
        break;

      case MV_SIGUIENTE: {
        if (rutaIdx + 1 >= rutaN) {
          terminarRecorrido();
          return;
        }
        int a = ruta[rutaIdx], b = ruta[rutaIdx + 1];
        int nx = (b % MAZE_COLUMNAS) - (a % MAZE_COLUMNAS);
        int ny = (b / MAZE_COLUMNAS) - (a / MAZE_COLUMNAS);
        if (nx != rumboX || ny != rumboY) {
          // Producto cruz z = rumbo x nuevo: > 0 giro antihorario (izquierda), < 0 horario
          // (derecha), 0 con rumbo opuesto = media vuelta (dos giros de 90 seguidos).
          int cruz = rumboX * ny - rumboY * nx;
          int giros = (cruz == 0) ? 2 : 1;
          if (cruz < 0) {
            moverRuedas(+1, -1, VEL_GIRO);   // derecha: izquierda adelante, derecha atras
          } else {
            moverRuedas(-1, +1, VEL_GIRO);   // izquierda (y media vuelta)
          }
          durMovMs = (uint32_t)giros * T_GIRO90_MS;
          rumboX = nx;
          rumboY = ny;
          pasoMov = MV_GIRANDO;
        } else {
          moverRuedas(+1, +1, VEL_AVANCE);
          durMovMs = T_CELDA_MS;
          pasoMov = MV_AVANZANDO;
        }
        break;
      }

      case MV_GIRANDO:
        if ((uint32_t)(ahora - tMovMs) < durMovMs) return;
        // tMovMs se ACUMULA (no se toma millis() de nuevo): asi un retraso de unos ms en una
        // vuelta de loop() no se va sumando celda tras celda, y la llegada a cada celda queda
        // en el mismo instante que calcula protocolo.tiempo_recorrido.
        tMovMs += durMovMs;
        moverRuedas(+1, +1, VEL_AVANCE);
        durMovMs = T_CELDA_MS;
        pasoMov = MV_AVANZANDO;
        break;

      case MV_AVANZANDO:
        if ((uint32_t)(ahora - tMovMs) < durMovMs) return;
        tMovMs += durMovMs;
        rutaIdx++;
        celdaActual = ruta[rutaIdx];
        Serial.printf("  carrito en la celda %d (%d de %d)\n", celdaActual, rutaIdx, rutaN - 1);
        pasoMov = MV_SIGUIENTE;
        break;

      case MV_FIN:
        return;
    }
  }
}

// =============================================================================================
// Prueba de latencia (CMD;RTT;destino;n;intervalo_ms)
// =============================================================================================

void iniciarRtt(int destino, int n, int intervalo) {
  if (destino < 1 || destino > ACO_MAX_NODOS || destino == NODO_ID) {
    enviarLog("CMD;RTT con destino invalido (%d)", destino);
    return;
  }
  if (n < 1) n = 1;
  if (n > RTT_MAX) n = RTT_MAX;
  if (intervalo < 5) intervalo = 5;
  rtt.activo = true;
  rtt.destino = destino;
  rtt.n = n;
  rtt.intervaloMs = (uint32_t)intervalo;
  rtt.enviados = 0;
  rtt.recibidos = 0;
  rtt.primerSeq = seqPing;
  memset(rtt.llego, 0, sizeof(rtt.llego));
  enviarLog("RTT: %d PING al nodo %d cada %d ms", n, destino, intervalo);
}

void recibirPong(uint32_t seq, uint32_t tUs) {
  if (!rtt.activo) return;
  uint32_t i = seq - rtt.primerSeq;
  if (i >= (uint32_t)rtt.enviados || rtt.llego[i]) return;  // de otra prueba o repetido
  rtt.llego[i] = true;
  // El PONG devuelve el micros() que puso este mismo nodo en el PING: la resta es el tiempo de
  // ida y vuelta completo con un solo reloj (no hace falta que los relojes esten sincronizados).
  uint32_t dt = micros() - tUs;
  rtt.ms[rtt.recibidos++] = dt / 1000.0f;
}

void reportarRtt() {
  float minimo = -1, maximo = -1, prom = -1, p95 = -1;
  int c = rtt.recibidos;
  if (c > 0) {
    // Orden por insercion (son a lo sumo 200 numeros) para sacar el percentil 95.
    for (int i = 1; i < c; i++) {
      float v = rtt.ms[i];
      int j = i - 1;
      while (j >= 0 && rtt.ms[j] > v) {
        rtt.ms[j + 1] = rtt.ms[j];
        j--;
      }
      rtt.ms[j + 1] = v;
    }
    double suma = 0;
    for (int i = 0; i < c; i++) suma += rtt.ms[i];
    minimo = rtt.ms[0];
    maximo = rtt.ms[c - 1];
    prom = (float)(suma / c);
    // p95 por "rango mas cercano": el valor en la posicion ceil(0,95 * c) de la lista ordenada.
    int idx = (int)ceil(0.95 * c) - 1;
    if (idx < 0) idx = 0;
    p95 = rtt.ms[idx];
  }
  char linea[160];
  snprintf(linea, sizeof(linea), "RTT;%d;%d;%d;%d;%.3f;%.3f;%.3f;%.3f;%d", NODO_ID, rtt.destino,
           rtt.enviados, c, minimo, prom, maximo, p95, rssiPropio());
  enviarLinea(1u, linea);
  Serial.printf("[RTT] %s\n", linea);
  rtt.activo = false;
}

void actualizarRtt() {
  if (!rtt.activo) return;
  uint32_t ahora = millis();
  if (rtt.enviados < rtt.n) {
    if (rtt.enviados == 0 || (uint32_t)(ahora - rtt.tUltimoEnvioMs) >= rtt.intervaloMs) {
      char linea[64];
      snprintf(linea, sizeof(linea), "PING;%d;%lu;%lu", NODO_ID, (unsigned long)seqPing,
               (unsigned long)micros());
      enviarLinea((uint8_t)(1u << rtt.destino), linea);
      seqPing++;
      rtt.enviados++;
      rtt.tUltimoEnvioMs = ahora;
    }
    return;
  }
  // Todos enviados: se reporta cuando volvieron todos o 1 s despues del ultimo PING.
  if (rtt.recibidos >= rtt.enviados || (uint32_t)(ahora - rtt.tUltimoEnvioMs) >= 1000) {
    reportarRtt();
  }
}

// =============================================================================================
// Procesar lo que llega por UDP
// =============================================================================================

void procesarHello(char** c, int nc) {
  if (nc < 5) return;
  int n = atoi(c[1]);
  if (n < 1 || n > ACO_MAX_NODOS || n == NODO_ID) return;
  uint32_t crc = (uint32_t)strtoul(c[2], nullptr, 16);
  uint32_t ahora = millis();
  InfoNodo& in = nodos[n];
  if (crc != MAZE_CRC) {
    // Otro mapa: no se cuenta como companero. Se avisa al PC, pero a lo sumo cada 10 s.
    if (!in.avisadoCrc || (uint32_t)(ahora - in.ultimoAvisoCrcMs) >= 10000) {
      in.avisadoCrc = true;
      in.ultimoAvisoCrcMs = ahora;
      enviarLog("HELLO del nodo %d con CRC %08lX distinto del mio (%08lX): se ignora", n,
                (unsigned long)crc, (unsigned long)MAZE_CRC);
    }
    return;
  }
  marcarOido(n);
  // Racha de HELLO: si el anterior fue hace mas de VIVO_MS (el nodo se apago o se reinicio),
  // la racha empieza de nuevo.
  if (!in.helloOk || (uint32_t)(ahora - in.ultimoHelloOkMs) >= VIVO_MS) {
    in.primerHelloOkMs = ahora;
  }
  in.helloOk = true;
  in.ultimoHelloOkMs = ahora;
  in.iterHello = atoi(c[3]);
  in.faseHello = F_ESPERA;
  for (int f = 0; f < 4; f++)
    if (strcmp(c[4], NOMBRE_FASE[f]) == 0) in.faseHello = f;

  // Reingreso (pruebas 5 y 14): un companero en ESPERA con iter 0 mientras este nodo esta en
  // BUSQUEDA es uno que se reinicio. Se le manda la feromona comun para que no empiece de cero.
  // Tambien si este nodo ya termino la busqueda completa (RECORRIDO/TERMINADO): asi el que se
  // reinicio en pleno recorrido recibe el TAU final y pasa a TERMINADO en vez de buscar solo.
  if (puedeDarTau(fase, ac.iteracion) && in.faseHello == F_ESPERA && in.iterHello == 0 &&
      soyMenorEnBusqueda()) {
    enviarTau(n);
  }
}

void procesarCmd(char** c, int nc, IPAddress ip) {
  if (nc < 2) return;
  if (strcmp(c[1], "INICIAR") == 0) {
    if (fase == F_ESPERA) {
      iniciarBusqueda("CMD;INICIAR desde el PC");
    } else {
      enviarLog("CMD;INICIAR ignorado: ya estoy en %s", NOMBRE_FASE[fase]);
    }
  } else if (strcmp(c[1], "REINICIAR") == 0) {
    enviarLog("CMD;REINICIAR: reiniciando");
    pararMotores();
    delay(50);  // unico delay: deja salir el LOG por el radio antes de reiniciar
    ESP.restart();
  } else if (strcmp(c[1], "RTT") == 0) {
    if (nc < 5) {
      enviarLog("CMD;RTT necesita destino;n;intervalo_ms");
      return;
    }
    iniciarRtt(atoi(c[2]), atoi(c[3]), atoi(c[4]));
  } else {
    enviarLog("comando desconocido: %s (desde %s)", c[1], ip.toString().c_str());
  }
}

void procesarLinea(char* linea, IPAddress ip, uint16_t puerto) {
  char* c[8];
  int nc = partirCampos(linea, c, 8);
  const char* t = c[0];

  if (strcmp(t, "HELLO") == 0) {
    procesarHello(c, nc);
  } else if (strcmp(t, "PHER") == 0) {
    if (nc < 6) return;
    int n = atoi(c[1]);
    if (n < 1 || n > ACO_MAX_NODOS || n == NODO_ID) return;
    marcarOido(n);
    recibirPher(n, atoi(c[2]), atoi(c[3]), atoi(c[4]), strtod(c[5], nullptr));
  } else if (strcmp(t, "FIN") == 0) {
    if (nc < 6) return;
    int n = atoi(c[1]);
    if (n < 1 || n > ACO_MAX_NODOS || n == NODO_ID) return;
    marcarOido(n);
    recibirFin(n, atoi(c[2]), atoi(c[3]), atoi(c[4]), atoi(c[5]));
  } else if (strcmp(t, "PATH") == 0) {
    if (nc < 4) return;
    int n = atoi(c[1]);
    if (n < 1 || n > ACO_MAX_NODOS || n == NODO_ID) return;
    marcarOido(n);
    Serial.printf("  nodo %d anuncia mejor ruta %s m: %s\n", n, c[2], c[3]);
  } else if (strcmp(t, "TAU") == 0) {
    if (nc < 4) return;
    int n = atoi(c[1]);
    if (n < 1 || n > ACO_MAX_NODOS || n == NODO_ID) return;
    marcarOido(n);
    recibirTau(n, atoi(c[2]), c[3]);
  } else if (strcmp(t, "PING") == 0) {
    // Se contesta SIEMPRE, en cualquier fase, al que lo mando (IP y puerto de origen: asi
    // tambien funciona si el PING lo manda un script desde el PC).
    if (nc < 4) return;
    marcarOido(atoi(c[1]));
    char resp[80];
    snprintf(resp, sizeof(resp), "PONG;%s;%s;%s;%d", c[1], c[2], c[3], rssiPropio());
    if (redArriba()) {
      udp.beginPacket(ip, puerto);
      udp.write((const uint8_t*)resp, strlen(resp));
      udp.endPacket();
    }
  } else if (strcmp(t, "PONG") == 0) {
    if (nc < 4) return;
    if (atoi(c[1]) != NODO_ID) return;  // no es la respuesta a un PING mio
    if (ip[0] == IP_RED_0 && ip[1] == IP_RED_1 && ip[2] == IP_RED_2) marcarOido(ip[3]);
    recibirPong((uint32_t)strtoul(c[2], nullptr, 10), (uint32_t)strtoul(c[3], nullptr, 10));
  } else if (strcmp(t, "CMD") == 0) {
    procesarCmd(c, nc, ip);
  }
  // ESTADO, RTT y LOG son para el PC: si llegan aqui (otro nodo mal configurado) se ignoran.
}

void atenderUdp() {
  // A lo sumo 8 datagramas por vuelta: si llega una rafaga, el resto se lee en la siguiente
  // vuelta y los motores y temporizadores no se quedan sin atender.
  for (int i = 0; i < 8; i++) {
    int tam = udp.parsePacket();
    if (tam <= 0) return;
    IPAddress ip = udp.remoteIP();
    uint16_t puerto = udp.remotePort();
    int n = udp.read((uint8_t*)rx, sizeof(rx) - 1);
    if (n <= 0) continue;
    rx[n] = '\0';
    // Un datagrama puede traer varias lineas separadas por '\n'.
    char* linea = rx;
    while (linea && *linea) {
      char* sig = strchr(linea, '\n');
      if (sig) *sig++ = '\0';
      size_t L = strlen(linea);
      if (L && linea[L - 1] == '\r') linea[L - 1] = '\0';
      if (*linea) procesarLinea(linea, ip, puerto);
      linea = sig;
    }
  }
}

// =============================================================================================
// WiFi
// =============================================================================================

void iniciarWifi() {
  WiFi.persistent(false);  // no guardar la configuracion en flash en cada arranque
#if NODO_ID == 1
  WiFi.mode(WIFI_AP);
  WiFi.softAP(WIFI_SSID, WIFI_CLAVE, WIFI_CANAL, 0, WIFI_MAX_CLIENTES);
  // IP fija 192.168.4.1 y el reparto de DHCP empezando en .100: el primer cliente que pida
  // direccion (el PC) recibe la 192.168.4.100, que es a donde va la telemetria, y nadie toma por
  // DHCP las .2/.3 de los otros carritos.
  WiFi.softAPConfig(ipNodo(1), ipNodo(1), IPAddress(255, 255, 255, 0), ipPc());
  WiFi.setSleep(false);
  Serial.printf("AP \"%s\" en %s, canal %d\n", WIFI_SSID, WiFi.softAPIP().toString().c_str(),
                WIFI_CANAL);
  udp.begin(PUERTO_NODOS);
#else
  WiFi.mode(WIFI_STA);
  // Modem sleep apagado: con el ahorro de energia la estacion "duerme" entre beacons y un
  // paquete puede esperar hasta ~100 ms en el AP; sin el, la latencia queda en pocos ms.
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  // WiFi.config ANTES de begin: asi no se pide DHCP y la IP es siempre la misma (los otros
  // nodos mandan unicast a 192.168.4.<NODO_ID> sin tener que descubrirla).
  WiFi.config(ipNodo(NODO_ID), ipNodo(1), IPAddress(255, 255, 255, 0));
  WiFi.begin(WIFI_SSID, WIFI_CLAVE, WIFI_CANAL);  // con el canal se salta el escaneo
  Serial.printf("Conectando a \"%s\" como %s ...\n", WIFI_SSID, ipNodo(NODO_ID).toString().c_str());
#endif
}

// Vigila la red en cada vuelta. En el nodo 1 no hay nada que hacer (el AP no se cae). En una
// estacion: al conectar se (re)abre el socket UDP, y si se cae (por ejemplo porque se reinicio
// el nodo 1, prueba 5) se deja trabajar al auto-reconnect y, si a los REINTENTO_WIFI_MS sigue
// caida, se reintenta a mano (el auto-reconnect a veces se rinde tras varios fallos seguidos).
void gestionarRed() {
  bool arriba = redArriba();
  uint32_t ahora = millis();
  if (arriba && !redArribaAntes) {
    redVistaArriba = true;
#if NODO_ID != 1
    udp.stop();
    udp.begin(PUERTO_NODOS);
    Serial.printf("WiFi conectado: IP %s, RSSI %d dBm\n", WiFi.localIP().toString().c_str(),
                  (int)WiFi.RSSI());
#endif
    tUltimoHelloMs = ahora - PERIODO_HELLO_MS;  // anunciarse ya, sin esperar un segundo
  } else if (!arriba && redArribaAntes) {
    tRedCaidaMs = ahora;
    tUltimoReintentoMs = ahora;
    Serial.println("WiFi caido, esperando reconexion...");
  }
#if NODO_ID != 1
  // Solo en estados "quietos" (desconectado, AP no encontrado, fallo de conexion). Si el driver
  // esta en medio de una asociacion (WL_IDLE_STATUS, etc.), cortarlo con disconnect() haria que
  // nunca termine de conectar.
  wl_status_t st = WiFi.status();
  bool quieto = (st == WL_DISCONNECTED || st == WL_NO_SSID_AVAIL || st == WL_CONNECT_FAILED);
  if (!arriba && quieto && (uint32_t)(ahora - tUltimoReintentoMs) >= REINTENTO_WIFI_MS) {
    tUltimoReintentoMs = ahora;
    Serial.println("Reintentando la conexion WiFi a mano");
    WiFi.disconnect();
    WiFi.config(ipNodo(NODO_ID), ipNodo(1), IPAddress(255, 255, 255, 0));
    WiFi.begin(WIFI_SSID, WIFI_CLAVE, WIFI_CANAL);
  }
#endif
  redArribaAntes = arriba;
}

// =============================================================================================
// LED de estado
// =============================================================================================
// ESPERA: parpadeo lento (1 Hz). BUSQUEDA: rapido (5 Hz). RECORRIDO: fijo. TERMINADO: un
// destello corto cada 2 s. Sin red (estacion): muy rapido (10 Hz).
void actualizarLed() {
  uint32_t t = millis();
  bool on = false;
  if (!redArriba()) {
    on = (t / 50) % 2;
  } else {
    switch (fase) {
      case F_ESPERA:    on = (t / 500) % 2; break;
      case F_BUSQUEDA:  on = (t / 100) % 2; break;
      case F_RECORRIDO: on = true; break;
      case F_TERMINADO: on = (t % 2000) < 100; break;
    }
  }
  digitalWrite(PIN_LED, on ? HIGH : LOW);
}

// =============================================================================================
// setup / loop
// =============================================================================================

void setup() {
  iniciarMotores();   // primero: deja el driver dormido (STBY en LOW)
  pinMode(PIN_LED, OUTPUT);
  // Buffer de salida grande (antes de begin): el eco TEL de una iteracion son ~1-2 kB, y con el
  // buffer por defecto Serial.write se queda esperando a que salgan los bytes a 115200 baudios
  // (~100 ms), frenando el loop justo en la barrera.
  Serial.setTxBufferSize(4096);
  Serial.begin(115200);
  Serial.printf("\n=== Enjambre ACO - nodo %d - mapa %s (CRC %08lX) ===\n", NODO_ID, MAZE_NOMBRE,
                (unsigned long)MAZE_CRC);

  AcoParametros p;
  p.alfa = ACO_ALFA;
  p.beta = ACO_BETA;
  p.rho = ACO_RHO;
  p.q = ACO_Q;
  p.hormigas = ACO_HORMIGAS;
  p.iteraciones = ACO_ITERACIONES;
  p.semilla = ACO_SEMILLA;
  p.tau0 = ACO_TAU0;
  p.solo_mejor = (ACO_SOLO_MEJOR != 0);
  ac.iniciar(p, NODO_ID);
  Serial.printf("ACO: alfa=%.2f beta=%.2f rho=%.2f Q=%.1f hormigas=%d iteraciones=%d semilla=%lu deposita=%s\n",
                p.alfa, p.beta, p.rho, p.q, p.hormigas, p.iteraciones, (unsigned long)p.semilla,
                p.solo_mejor ? "solo la mejor" : "todas");
#if !MOVER_CARRITO
  Serial.println("MOVER_CARRITO = 0: el recorrido se simula sin energizar los motores");
#endif

  iniciarWifi();
  Serial.println("Fase ESPERA: buscando a los companeros...");
}

void loop() {
  uint32_t ahora = millis();

  gestionarRed();
  if (redArriba()) atenderUdp();

  // Presencia y telemetria periodicas. Se suma el periodo (en vez de tomar 'ahora') para que
  // el ritmo medio sea exacto; si el atraso es grande se resincroniza. No dependen de la red:
  // enviarMascara ya omite el UDP si no hay WiFi, y asi el eco TEL por USB sigue saliendo.
  if ((uint32_t)(ahora - tUltimoHelloMs) >= PERIODO_HELLO_MS) {
    tUltimoHelloMs = ((uint32_t)(ahora - tUltimoHelloMs) > 3 * PERIODO_HELLO_MS)
                         ? ahora : tUltimoHelloMs + PERIODO_HELLO_MS;
    enviarHello();
  }
  if ((uint32_t)(ahora - tUltimoEstadoMs) >= PERIODO_ESTADO_MS) {
    tUltimoEstadoMs = ((uint32_t)(ahora - tUltimoEstadoMs) > 3 * PERIODO_ESTADO_MS)
                          ? ahora : tUltimoEstadoMs + PERIODO_ESTADO_MS;
    enviarEstado();
  }

  switch (fase) {
    case F_ESPERA:
      // (c) a los 30 s del arranque se sale aunque falte alguien (la busqueda tambien funciona
      // con uno o dos nodos); (a) antes, si los otros dos ya se ven estables.
      if (ahora >= ARRANQUE_SOLO_MS) {
        iniciarBusqueda("pasaron 30 s desde el arranque");
      } else if (companerosListos()) {
        iniciarBusqueda("los otros dos nodos estan presentes con el mismo mapa");
      }
      break;
    case F_BUSQUEDA:
      actualizarBusqueda();
      break;
    case F_RECORRIDO:
      actualizarRecorrido();
      break;
    case F_TERMINADO:
      break;
  }

  actualizarMotores();
  actualizarRtt();
  actualizarLed();
  delay(1);  // cede la CPU un instante a las tareas del WiFi (no frena nada: 1 ms por vuelta)
}
