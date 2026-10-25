// =====================================================================================
// Piezas de la ESTRUCTURA (nodos, tubos, empalmes y tacos), dibujadas desde las listas que genera
// estructura.py en estructura_gen.scad. Cada modulo dibuja la pieza EN SU LUGAR del ensamble y con
// los agujeros de TODOS los remaches que la atraviesan (REM_TODOS, de maqueta.scad).
// =====================================================================================
include <estructura_gen.scad>

function _buscar(lista, n) = lista[search([n], [for (e = lista) e[0]])[0]];
function es_de(lista, n) = search([n], [for (e = lista) e[0]])[0] != [];

// Brazo de un nodo: prisma de la seccion del brazo desde el centro (lo cubre) hasta la punta.
module _prisma_brazo(c, d, techo) en_marco(c, c + d, techo)
  translate([0, 0, -(lado_tubo / 2 + tol + pared_nodo)]) linear_extrude(brazo_nodo + lado_tubo / 2 + tol + pared_nodo) brazo_2d();
module _cajera_brazo(c, d, techo) en_marco(c, c + d, techo)
  translate([0, 0, brazo_nodo - hondo_cajera]) linear_extrude(hondo_cajera + 1) cajera_2d();
// arriba de una cajera: el techo del nodo (lo de arriba en la cama) si el brazo queda acostado en la cama;
// si queda parado, cualquiera (igual que en estructura.py)
function techo_brazo(d, techo) = abs(d * techo) < 0.9 ? techo : (abs(d[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0]);

module nodo(n) {
  e = _buscar(NODOS, n);
  c = e[1]; ds = e[2]; pas = e[3]; techo = e[4];
  difference() {
    union() {
      for (d = ds) _prisma_brazo(c, d, techo_brazo(d, techo));
      for (d = pas) for (s = [-1, 1]) _prisma_brazo(c, s * d, techo_brazo(d, techo));
    }
    for (d = ds) _cajera_brazo(c, d, techo_brazo(d, techo));
    // tubo pasante: cajera de punta a punta
    for (d = pas) en_marco(c - d * (brazo_nodo + 1), c + d, techo_brazo(d, techo))
      linear_extrude(2 * brazo_nodo + 2) cajera_2d();
    for (r = REM_TODOS) agujero_rem_en(r);
  }
}

module tubo_pieza(n) {
  e = _buscar(TUBOS, n);
  difference() { tubo(e[1], e[2], e[3]); for (r = REM_TODOS) agujero_rem_en(r); }
}

// Empalme: manguito con cajera de punta a punta y un tope de 4 mm al medio (donde se encuentran los tubos).
module empalme(n) {
  e = _buscar(EMPALMES, n);
  c = e[1]; d = e[2];
  difference() {
    en_marco(c - d * (largo_empalme / 2), c + d, e[3]) linear_extrude(largo_empalme) brazo_2d();
    for (s = [-1, 1]) en_marco(c + s * d * 2, c + s * d * 3, e[3]) linear_extrude(largo_empalme / 2) cajera_2d();
    for (r = REM_TODOS) agujero_rem_en(r);
  }
}

// Taco: separador entre el riel -y de la mesa de monedas (eje z Z_RIEL) y la viga del portico (Z_VIGA):
// un bloque entre los dos tubos y una placa de 3 mm por la cara -y que se remacha a los dos.
e_placa_taco = 3;
module taco(n) {
  x = _buscar(TACOS, n)[1];
  difference() {
    union() {
      translate([x - 8, Y_A - lado_tubo / 2, Z_VIGA + lado_tubo / 2]) cube([16, lado_tubo, Z_RIEL - Z_VIGA - lado_tubo]);
      translate([x - 15, Y_A - lado_tubo / 2 - e_placa_taco, Z_VIGA - lado_tubo / 2]) cube([30, e_placa_taco, Z_RIEL - Z_VIGA + lado_tubo]);
    }
    for (r = REM_TODOS) agujero_rem_en(r);
  }
}

// Todas las piezas de la estructura en su lugar
module estructura_ens() {
  for (e = NODOS) nodo(e[0]);
  for (e = TUBOS) tubo_pieza(e[0]);
  for (e = EMPALMES) empalme(e[0]);
  for (e = TACOS) taco(e[0]);
}

// Una pieza de la estructura (en su lugar) y su orientacion en la cama
module estructura_pieza(n) {
  if (es_de(NODOS, n)) nodo(n);
  else if (es_de(TUBOS, n)) tubo_pieza(n);
  else if (es_de(EMPALMES, n)) empalme(n);
  else if (es_de(TACOS, n)) taco(n);
}
module estructura_a_cama(n) {
  if (es_de(NODOS, n)) let(t = _buscar(NODOS, n)[4])   // gira el techo del nodo hacia +z
    rotate(t[2] < -0.5 ? [180, 0, 0] : t[1] > 0.5 ? [90, 0, 0] : t[1] < -0.5 ? [-90, 0, 0] : t[0] > 0.5 ? [0, -90, 0] : t[0] < -0.5 ? [0, 90, 0] : [0, 0, 0]) children();
  else if (es_de(TUBOS, n)) multmatrix(_buscar(TUBOS, n)[4]) children();
  else if (es_de(EMPALMES, n)) multmatrix(_buscar(EMPALMES, n)[4]) children();
  else if (es_de(TACOS, n)) rotate([90, 0, 0]) children();
}
PIEZAS_ESTRUCTURA = concat([for (e = NODOS) e[0]], [for (e = TUBOS) e[0]], [for (e = EMPALMES) e[0]], [for (e = TACOS) e[0]]);
