// prueba_equivalencia.cpp - Corre el MISMO aco_core.h del firmware en el PC.
//
// Simula los tres nodos del enjambre en orden sincronico (igual que aco.simular_enjambre):
// cada iteracion, cada nodo suelta sus hormigas, y luego los tres aplican los depositos de los
// tres en orden de nodo. Imprime, por iteracion y por nodo, la mejor ruta y la longitud, y al
// final la feromona con 17 cifras. comparar_equivalencia.py compila esto con g++, lo corre y
// compara linea por linea contra Python: si el C++ y el Python eligen distinto en cualquier paso,
// la salida difiere.
//
// Uso: prueba_equivalencia <semilla> [alfa beta rho q hormigas iteraciones tau0 solo_mejor(1/0)]
// (maze_data.h se toma del directorio que se pase con -I al compilar)
#include <stdio.h>
#include <stdlib.h>

#include "aco_core.h"

int main(int argc, char** argv) {
  AcoParametros p;
  if (argc > 1) p.semilla = (uint32_t)strtoul(argv[1], nullptr, 10);
  if (argc > 8) {
    p.alfa = atof(argv[2]);
    p.beta = atof(argv[3]);
    p.rho = atof(argv[4]);
    p.q = atof(argv[5]);
    p.hormigas = atoi(argv[6]);
    p.iteraciones = atoi(argv[7]);
    p.tau0 = atof(argv[8]);
  }
  if (argc > 9) p.solo_mejor = atoi(argv[9]) != 0;
  static AcoNodo nodos[ACO_MAX_NODOS + 1];
  for (int n = 1; n <= ACO_MAX_NODOS; n++) nodos[n].iniciar(p, n);

  for (int k = 1; k <= p.iteraciones; k++) {
    for (int n = 1; n <= ACO_MAX_NODOS; n++) nodos[n].iteracionLocal();
    const AcoDeposito* por_nodo[ACO_MAX_NODOS + 1] = {nullptr};
    int cuantos[ACO_MAX_NODOS + 1] = {0};
    // Copia de los depositos: cada nodo aplica los de todos, y aplicar no debe pisar el arreglo
    // que todavia lee el siguiente.
    static AcoDeposito copia[ACO_MAX_NODOS + 1][MAZE_N_ARISTAS];
    for (int n = 1; n <= ACO_MAX_NODOS; n++) {
      cuantos[n] = nodos[n].n_depositos;
      for (int i = 0; i < cuantos[n]; i++) copia[n][i] = nodos[n].depositos[i];
      por_nodo[n] = copia[n];
    }
    for (int n = 1; n <= ACO_MAX_NODOS; n++) nodos[n].aplicarIteracion(por_nodo, cuantos);
    for (int n = 1; n <= ACO_MAX_NODOS; n++) {
      AcoNodo& a = nodos[n];
      printf("IT %d N %d EX %d DES %d L %.17g C ", k, n, a.exitosas, a.descartadas,
             a.mejor_n ? a.mejor_longitud : -1.0);
      for (int i = 0; i < a.mejor_n; i++) printf(i ? "-%d" : "%d", a.mejor_camino[i]);
      printf("\n");
    }
  }
  for (int n = 1; n <= ACO_MAX_NODOS; n++) {
    printf("TAU %d", n);
    for (int e = 0; e < MAZE_N_ARISTAS; e++) printf(" %.17g", nodos[n].tau[e]);
    printf("\n");
  }
  return 0;
}
