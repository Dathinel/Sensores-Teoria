// aco_core.h - Nucleo del ACO (colonia de hormigas) que corre dentro de cada ESP32.
//
// Es C++ puro: no usa nada de Arduino, para poder compilarlo tambien en el PC
// (pruebas/equivalencia/prueba_equivalencia.cpp) y comprobar que, con la misma semilla, elige
// EXACTAMENTE los mismos caminos que aco.py. Cada decision de este archivo tiene su gemela en
// aco.py, en el mismo orden:
//   - el grafo sale de maze_data.h, generado desde maze.json por generar_maze_h.py;
//   - el azar sale de un xorshift32 (no de random() de Arduino, que da otra secuencia);
//   - las probabilidades se calculan en double (en el ESP32 el double es por software: es mas
//     lento que float, pero el laberinto es tan chico que una iteracion tarda milisegundos);
//   - los depositos de los tres nodos se aplican en orden nodo 1, 2, 3.
#pragma once

#include <math.h>
#include <stdint.h>
#include <string.h>

#include "maze_data.h"

// Maximo de nodos del enjambre (los ESP32 1, 2 y 3; el indice 0 no se usa).
#define ACO_MAX_NODOS 3

struct AcoParametros {
  double alfa = 1.0;      // peso de la feromona
  double beta = 2.0;      // peso de la visibilidad 1/d
  double rho = 0.5;       // evaporacion: queda (1 - rho) al final de cada iteracion
  double q = 100.0;       // constante de deposito: cada hormiga deja q / L
  int hormigas = 4;       // hormigas por nodo por iteracion
  int iteraciones = 30;   // iteraciones del enjambre
  uint32_t semilla = 12345;
  double tau0 = 1.0;      // feromona inicial
  // true = en cada iteracion deposita SOLO la mejor hormiga de este nodo (la de ruta mas corta;
  // si empatan, la primera). false = deposita toda hormiga que llego (Ant System original).
  // Igual que Parametros.deposito ("mejor" / "todas") en aco.py.
  bool solo_mejor = true;
};

// ---------------------------------------------------------------------------------------------
// xorshift32 (Marsaglia, 2003): tres desplazamientos y tres XOR. Igual que Xorshift32 en aco.py.
// ---------------------------------------------------------------------------------------------
struct Xorshift32 {
  uint32_t estado = 1;
  void sembrar(uint32_t s) { estado = s ? s : 1; }
  uint32_t siguiente() {
    uint32_t x = estado;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    estado = x;
    return x;
  }
  // [0, 1) con los 24 bits altos: entran exactos en un double, asi la division no redondea
  // distinto que en Python.
  double uniforme() { return (double)(siguiente() >> 8) / 16777216.0; }
};

static inline uint32_t aco_semilla_de_nodo(uint32_t base, int nodo) {
  uint32_t s = base + 0x9E3779B9u * (uint32_t)nodo;
  return s ? s : 1;
}

// Deposito de un nodo sobre una arista en una iteracion (lo que viaja en un mensaje PHER).
struct AcoDeposito {
  int16_t arista;    // indice de la arista en MAZE_ARISTAS (-1 = libre)
  int16_t origen;    // como la cruzo la primera hormiga de este nodo que paso por ahi
  int16_t destino;
  double valor;      // suma de q / L de las hormigas de este nodo que la cruzaron
};

class AcoNodo {
 public:
  AcoParametros p;
  int nodo = 1;
  double tau[MAZE_N_ARISTAS];
  double eta_beta[MAZE_N_ARISTAS];   // (1/d)^beta, se calcula una vez

  // Mejor ruta de las hormigas de ESTE nodo.
  int16_t mejor_camino[MAZE_N_CELDAS];
  int mejor_n = 0;                   // nodos en mejor_camino (0 = aun no hay)
  double mejor_longitud = INFINITY;

  // Depositos de la ultima iteracion local (uno por arista tocada, en orden de arista).
  AcoDeposito depositos[MAZE_N_ARISTAS];
  int n_depositos = 0;
  int exitosas = 0, descartadas = 0;
  int iteracion = 0;                 // iteraciones ya aplicadas (0..p.iteraciones)

  Xorshift32 rng;

  void iniciar(const AcoParametros& params, int id_nodo) {
    p = params;
    nodo = id_nodo;
    rng.sembrar(aco_semilla_de_nodo(p.semilla, nodo));
    for (int e = 0; e < MAZE_N_ARISTAS; e++) {
      tau[e] = p.tau0;
      eta_beta[e] = pow(1.0 / MAZE_LONGITUD[e], p.beta);
    }
    mejor_n = 0;
    mejor_longitud = INFINITY;
    n_depositos = exitosas = descartadas = 0;
    iteracion = 0;
  }

  // Una hormiga camina de MAZE_INICIO a MAZE_META. Devuelve cuantos nodos tiene su camino, o 0
  // si quedo atrapada (callejon o celdas ya visitadas alrededor): se descarta sin depositar.
  //   p(i -> j) = tau_ij^alfa * eta_ij^beta / suma de lo mismo sobre los vecinos permitidos
  int construirHormiga(int16_t* camino) {
    bool visitado[MAZE_N_CELDAS];
    memset(visitado, 0, sizeof(visitado));
    int actual = MAZE_INICIO;
    int n = 0;
    camino[n++] = actual;
    visitado[actual] = true;
    while (actual != MAZE_META) {
      int cand[4];
      double peso[4];
      int nc = 0;
      double total = 0.0;
      // Vecinos en el orden fijo +x, +y, -x, -y (MAZE_VECINOS lo trae ya ordenado).
      for (int k = 0; k < MAZE_N_VECINOS[actual]; k++) {
        int v = MAZE_VECINOS[actual][k][0];
        int e = MAZE_VECINOS[actual][k][1];
        if (visitado[v]) continue;
        cand[nc] = v;
        peso[nc] = pow(tau[e], p.alfa) * eta_beta[e];
        total += peso[nc];
        nc++;
      }
      if (nc == 0) return 0;  // atrapada
      // Ruleta. Siempre se gasta un aleatorio por paso, como en aco.py.
      double r = rng.uniforme() * total;
      int elegido = cand[nc - 1];
      double acumulado = 0.0;
      for (int k = 0; k < nc; k++) {
        acumulado += peso[k];
        if (r < acumulado) {
          elegido = cand[k];
          break;
        }
      }
      actual = elegido;
      visitado[actual] = true;
      camino[n++] = actual;
    }
    return n;
  }

  // Suelta p.hormigas hormigas con la feromona actual y deja en depositos[] lo que dejaria cada
  // arista. NO toca tau: eso se hace en aplicarIteracion cuando ya llegaron los otros nodos.
  void iteracionLocal() {
    double dep[MAZE_N_ARISTAS];
    int16_t org[MAZE_N_ARISTAS], dst[MAZE_N_ARISTAS];
    bool tocada[MAZE_N_ARISTAS];
    memset(tocada, 0, sizeof(tocada));
    exitosas = descartadas = 0;
    int16_t camino[MAZE_N_CELDAS];
    // Mejor hormiga de ESTA iteracion (solo se usa con p.solo_mejor).
    int16_t camino_iter[MAZE_N_CELDAS];
    int n_iter = 0;
    double L_iter = INFINITY;
    for (int h = 0; h < p.hormigas; h++) {
      int n = construirHormiga(camino);
      if (n == 0) {
        descartadas++;
        continue;
      }
      exitosas++;
      // Longitud real: suma de las aristas recorridas (sumadas en orden, igual que Python).
      double L = longitudCamino(camino, n);
      if (L < mejor_longitud - 1e-12) {
        mejor_longitud = L;
        mejor_n = n;
        memcpy(mejor_camino, camino, n * sizeof(int16_t));
      }
      if (p.solo_mejor) {
        if (L < L_iter - 1e-12) {  // estrictamente menor: en empate se queda la primera
          L_iter = L;
          n_iter = n;
          memcpy(camino_iter, camino, n * sizeof(int16_t));
        }
      } else {
        depositar(camino, n, L, dep, org, dst, tocada);
      }
    }
    if (p.solo_mejor && n_iter > 0) depositar(camino_iter, n_iter, L_iter, dep, org, dst, tocada);
    n_depositos = 0;
    for (int e = 0; e < MAZE_N_ARISTAS; e++) {
      if (!tocada[e]) continue;
      depositos[n_depositos++] = {(int16_t)e, org[e], dst[e], dep[e]};
    }
  }

  // Fin de iteracion:  tau <- (1 - rho) tau  y despues  tau += depositos de cada nodo.
  // por_nodo[n] apunta a los depositos del nodo n (1..3) y cuantos[n] dice cuantos son; un nodo
  // que no llego (apagado o paquete perdido) va con cuantos[n] = 0. Se suma en orden de nodo, y
  // dentro de cada nodo en el orden del arreglo: quien llama debe pasarlo ORDENADO POR ARISTA
  // (los propios ya salen asi de iteracionLocal; los recibidos los ordena el .ino), porque asi
  // suma aco.py y sumar en otro orden cambia el ultimo bit del double.
  void aplicarIteracion(const AcoDeposito* const por_nodo[ACO_MAX_NODOS + 1],
                        const int cuantos[ACO_MAX_NODOS + 1]) {
    const double f = 1.0 - p.rho;
    for (int e = 0; e < MAZE_N_ARISTAS; e++) tau[e] *= f;
    for (int n = 1; n <= ACO_MAX_NODOS; n++) {
      for (int i = 0; i < cuantos[n]; i++) {
        const AcoDeposito& d = por_nodo[n][i];
        if (d.arista >= 0 && d.arista < MAZE_N_ARISTAS) tau[d.arista] += d.valor;
      }
    }
    iteracion++;
  }

  // Camino que sale de seguir siempre la arista con mas feromona (sin azar).
  int caminoCodicioso(int16_t* camino) const {
    bool vis[MAZE_N_CELDAS];
    memset(vis, 0, sizeof(vis));
    int actual = MAZE_INICIO, n = 0;
    camino[n++] = actual;
    vis[actual] = true;
    while (actual != MAZE_META) {
      int mejor = -1;
      double mt = -1.0;
      for (int k = 0; k < MAZE_N_VECINOS[actual]; k++) {
        int v = MAZE_VECINOS[actual][k][0];
        int e = MAZE_VECINOS[actual][k][1];
        if (vis[v]) continue;
        if (tau[e] > mt) {
          mt = tau[e];
          mejor = v;
        }
      }
      if (mejor < 0) return 0;
      actual = mejor;
      vis[actual] = true;
      camino[n++] = actual;
    }
    return n;
  }

  // Suma de las longitudes de las aristas del camino, de izquierda a derecha (como aco.py).
  static double longitudCamino(const int16_t* camino, int n) {
    double L = 0.0;
    for (int i = 0; i + 1 < n; i++) L += MAZE_LONGITUD[aristaEntre(camino[i], camino[i + 1])];
    return L;
  }

  // Agrega q / L en cada arista del camino. origen/destino quedan como la cruzo la primera
  // hormiga que paso por esa arista (solo informativo: la feromona es la misma en los dos sentidos).
  void depositar(const int16_t* camino, int n, double L, double* dep, int16_t* org, int16_t* dst,
                 bool* tocada) const {
    double aporte = p.q / L;
    for (int i = 0; i + 1 < n; i++) {
      int e = aristaEntre(camino[i], camino[i + 1]);
      if (tocada[e]) {
        dep[e] += aporte;
      } else {
        tocada[e] = true;
        dep[e] = aporte;
        org[e] = camino[i];
        dst[e] = camino[i + 1];
      }
    }
  }

  static int aristaEntre(int u, int v) {
    for (int k = 0; k < MAZE_N_VECINOS[u]; k++)
      if (MAZE_VECINOS[u][k][0] == v) return MAZE_VECINOS[u][k][1];
    return -1;
  }
};
