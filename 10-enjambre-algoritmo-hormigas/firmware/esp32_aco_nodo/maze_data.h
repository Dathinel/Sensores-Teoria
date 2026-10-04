// maze_data.h - GENERADO por generar_maze_h.py a partir de maze.json. No editar a mano:
// cambiar el .json y volver a correr el script.
#pragma once
#include <stdint.h>

#define MAZE_NOMBRE "almacen-5x5"
#define MAZE_COLUMNAS 5
#define MAZE_FILAS 5
#define MAZE_N_CELDAS 25
#define MAZE_N_ARISTAS 29
#define MAZE_INICIO 0
#define MAZE_META 24
#define MAZE_TAM_CELDA_M 0.200
#define MAZE_CRC 0xA85E23EBu

// Aristas (u, v) con u < v en el orden canonico de aco.py.
static const int16_t MAZE_ARISTAS[MAZE_N_ARISTAS][2] = {
  {0, 1},
  {1, 2},
  {2, 3},
  {2, 7},
  {3, 4},
  {4, 9},
  {5, 6},
  {5, 10},
  {6, 7},
  {7, 8},
  {8, 9},
  {8, 13},
  {9, 14},
  {10, 11},
  {10, 15},
  {11, 12},
  {11, 16},
  {12, 13},
  {14, 19},
  {15, 16},
  {15, 20},
  {16, 17},
  {16, 21},
  {17, 18},
  {17, 22},
  {18, 19},
  {20, 21},
  {22, 23},
  {23, 24},
};

// Longitud real de cada arista en metros (distancia entre centros de celdas).
static const double MAZE_LONGITUD[MAZE_N_ARISTAS] = {
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
  0.2,
};

// Vecinos de cada celda en orden +x, +y, -x, -y: {celda vecina, indice de arista}.
static const uint8_t MAZE_N_VECINOS[MAZE_N_CELDAS] = {
  1, 2, 3, 2, 2, 2, 2, 3, 3, 3, 3, 3, 2, 2, 2, 3, 4, 3, 2, 2, 2, 2, 2, 2, 1
};
static const int16_t MAZE_VECINOS[MAZE_N_CELDAS][4][2] = {
  {{1, 0}, {-1, -1}, {-1, -1}, {-1, -1}},  // celda 0 = (0, 0)
  {{2, 1}, {0, 0}, {-1, -1}, {-1, -1}},  // celda 1 = (1, 0)
  {{3, 2}, {7, 3}, {1, 1}, {-1, -1}},  // celda 2 = (2, 0)
  {{4, 4}, {2, 2}, {-1, -1}, {-1, -1}},  // celda 3 = (3, 0)
  {{9, 5}, {3, 4}, {-1, -1}, {-1, -1}},  // celda 4 = (4, 0)
  {{6, 6}, {10, 7}, {-1, -1}, {-1, -1}},  // celda 5 = (0, 1)
  {{7, 8}, {5, 6}, {-1, -1}, {-1, -1}},  // celda 6 = (1, 1)
  {{8, 9}, {6, 8}, {2, 3}, {-1, -1}},  // celda 7 = (2, 1)
  {{9, 10}, {13, 11}, {7, 9}, {-1, -1}},  // celda 8 = (3, 1)
  {{14, 12}, {8, 10}, {4, 5}, {-1, -1}},  // celda 9 = (4, 1)
  {{11, 13}, {15, 14}, {5, 7}, {-1, -1}},  // celda 10 = (0, 2)
  {{12, 15}, {16, 16}, {10, 13}, {-1, -1}},  // celda 11 = (1, 2)
  {{13, 17}, {11, 15}, {-1, -1}, {-1, -1}},  // celda 12 = (2, 2)
  {{12, 17}, {8, 11}, {-1, -1}, {-1, -1}},  // celda 13 = (3, 2)
  {{19, 18}, {9, 12}, {-1, -1}, {-1, -1}},  // celda 14 = (4, 2)
  {{16, 19}, {20, 20}, {10, 14}, {-1, -1}},  // celda 15 = (0, 3)
  {{17, 21}, {21, 22}, {15, 19}, {11, 16}},  // celda 16 = (1, 3)
  {{18, 23}, {22, 24}, {16, 21}, {-1, -1}},  // celda 17 = (2, 3)
  {{19, 25}, {17, 23}, {-1, -1}, {-1, -1}},  // celda 18 = (3, 3)
  {{18, 25}, {14, 18}, {-1, -1}, {-1, -1}},  // celda 19 = (4, 3)
  {{21, 26}, {15, 20}, {-1, -1}, {-1, -1}},  // celda 20 = (0, 4)
  {{20, 26}, {16, 22}, {-1, -1}, {-1, -1}},  // celda 21 = (1, 4)
  {{23, 27}, {17, 24}, {-1, -1}, {-1, -1}},  // celda 22 = (2, 4)
  {{24, 28}, {22, 27}, {-1, -1}, {-1, -1}},  // celda 23 = (3, 4)
  {{23, 28}, {-1, -1}, {-1, -1}, {-1, -1}},  // celda 24 = (4, 4)
};
