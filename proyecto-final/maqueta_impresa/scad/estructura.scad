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
// El bloque es tan ancho como la placa (30): se imprime parado sobre su punta x y la punta es una T maciza (con
// 16 de ancho el bloque empezaba 7 mm sobre la cama y quedaba en el aire, 2026-10-24).
e_placa_taco = 3;
module taco(n) {
  x = _buscar(TACOS, n)[1];
  difference() {
    union() {
      translate([x - 15, Y_A - lado_tubo / 2, Z_VIGA + lado_tubo / 2]) cube([30, lado_tubo, Z_RIEL - Z_VIGA - lado_tubo]);
      translate([x - 15, Y_A - lado_tubo / 2 - e_placa_taco, Z_VIGA - lado_tubo / 2]) cube([30, e_placa_taco, Z_RIEL - Z_VIGA + lado_tubo]);
    }
    // hueco: pared de 4 del lado de la banda (ahi remacha el colgante del rodillo B de la cinta de monedas y la una
    // abre adentro) y de 3 en el resto. Impreso parado sobre la punta x, el techo del hueco es un puente de 9.
    translate([x - 12, Y_A - lado_tubo / 2 + 3, Z_VIGA + lado_tubo / 2 + 3]) cube([24, lado_tubo - 7, Z_RIEL - Z_VIGA - lado_tubo - 6]);
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
// Giro de un tubo sobre su eje para imprimirlo: en la cama, el eje queda en x, el `arriba` local en +z y la cara
// local -y abajo. Cada remache que atraviesa el tubo deja su agujero en la cara por donde entra (la opuesta a su
// eje). Se busca el giro (0, 90, 180 o 270) con el que ninguna cara con agujeros queda abajo (el hueco es
// octogonal: cualquier giro se imprime igual). Si las 4 caras tienen agujeros, se deja el giro 0.
// Cuenta un remache si su vastago CRUZA el tubo (la cabeza puede estar lejos, sobre la pieza que se sujeta):
// a lo largo de su eje, el punto mas cercano al eje del tubo queda dentro del tubo y antes de que termine el agarre.
function _caras_tubo(e) = let(z = unit(e[2] - e[1]), y = _y(z, e[3]), x = cross(y, z), L = norm(e[2] - e[1]))
  [for (r = REM_TODOS) let(d = unit(r[3]), c = r[2] - e[1], t = c * z, p = c - t * z, s = -(p * d))
     if (t > -1 && t < L + 1 && abs(d * z) < 0.5 && s > 0 && norm(p + s * d) < lado_tubo / 2 + 0.5
         && norm(p) - lado_tubo / 2 < r[1] + 3)
       [-(d * x), -(d * y)]];
function _abajo(f, k) = f[0] * sin(90 * k) + f[1] * cos(90 * k) < -0.7;
// Si las 4 caras tienen agujeros (un riel: remaches desde arriba, desde abajo y el eje del rodillo por los
// costados), gana la cara con MENOS agujeros chicos abajo (los agujeros grandes de AGUJEROS no cuentan).
function _n_abajo(fs, k) = len([for (f = fs) if (_abajo(f, k)) 1]);
function giro_tubo(e) = let(fs = _caras_tubo(e), ns = [for (k = [0:3]) _n_abajo(fs, k)], m = min(ns))
  [for (k = [0:3]) if (ns[k] == m) k][0];

module estructura_a_cama(n) {
  if (es_de(NODOS, n)) let(t = _buscar(NODOS, n)[4])   // gira el techo del nodo hacia +z
    rotate(t[2] < -0.5 ? [180, 0, 0] : t[1] > 0.5 ? [90, 0, 0] : t[1] < -0.5 ? [-90, 0, 0] : t[0] > 0.5 ? [0, -90, 0] : t[0] < -0.5 ? [0, 90, 0] : [0, 0, 0]) children();
  else if (es_de(TUBOS, n)) let(e = _buscar(TUBOS, n)) rotate([90 * giro_tubo(e), 0, 0]) multmatrix(e[4]) children();
  else if (es_de(EMPALMES, n)) multmatrix(_buscar(EMPALMES, n)[4]) children();
  else if (es_de(TACOS, n)) rotate([0, 90, 0]) children();   // parado sobre su punta: los agujeros quedan horizontales
}
PIEZAS_ESTRUCTURA = concat([for (e = NODOS) e[0]], [for (e = TUBOS) e[0]], [for (e = EMPALMES) e[0]], [for (e = TACOS) e[0]]);
