// =====================================================================================
// Subsistema "canaleta_muelle" (prefijo can_): canaleta de entrega (4 cabezales + 4 prisioneros que toman
// las 2 varillas Ø4 con PTFE), escape de dos dedos (soporte del SG90 + balancin) y muelle de carga del carro
// (topes sobre el travesano M1-M2 y guias en V). Todo PLA, modelado EN SU LUGAR (mm, marco de sim/mundo.py).
// Lo funcional sale del inventario (§11, §18.9) y NO se mueve: rieles de (360,-137.5,207) a (360,-417.5,131.97)
// a 15 grados, separacion 69 (73 en la boca, embudo de 40), curva r 15 en el fin del embudo, pivote del escape
// (410,-375.97,98.10), carro estacionado en (360,-507.5) con rumbo -90.
// =====================================================================================

can_c = cos(15);
can_s = sin(15);
function can_zr(y) = 207 + (y + 137.5) * tan(15);           // eje de los rieles (recta en el plano y-z)
can_r_riel = 2.13;                                          // varilla Ø4 + cinta PTFE 0,13
can_r_ranura = can_r_riel + tol;                            // cuna de la varilla en el cabezal
// Marco de un punto del riel: x = x del mundo, y = aguas ARRIBA a lo largo del riel, z = normal (arriba).
module can_en_riel(p) translate(p) rotate([15, 0, 0]) children();
module can_espejo() translate([720, 0, 0]) mirror([1, 0, 0]) children();   // lado +x = espejo en x = 360

// ----------------------------------------------------------------- rieles (comprados)
function can_u(v) = v / norm(v);
function can_pts_riel(s) = let(
    e = [360 + s * 36.5, -137.5, 207], m = [360 + s * 34.5, -177.5, can_zr(-177.5)],
    b = [360 + s * 34.5, -417.5, can_zr(-417.5)],
    a = m + 15 * can_u(e - m), d = m + 15 * can_u(b - m))
  concat([e], [for (i = [0:8]) let(t = i / 8) (1 - t) * (1 - t) * a + 2 * (1 - t) * t * m + t * t * d], [b]);
module can_varilla(s) let(P = can_pts_riel(s))
  for (i = [0:len(P) - 2]) hull() { translate(P[i]) sphere(r = can_r_riel, $fn = 16); translate(P[i + 1]) sphere(r = can_r_riel, $fn = 16); }

// ----------------------------------------------------------------- vaso (comprado): Ø62 x 90, pestana Ø78 sobre los rieles
// MEDIR: espesor de la pestana (1 mm).
module can_vaso_en(yc, e = 0, parte = "todo") can_en_riel([360, yc, can_zr(yc)]) {
  if (parte != "cuerpo") translate([0, 0, can_r_riel + 0.05 - e]) cylinder(d = 78 + 2 * e, h = 1 + 2 * e, $fn = 64);
  if (parte != "pestana") translate([0, 0, can_r_riel + 0.05 - 90 - e]) cylinder(d = 62 + 2 * e, h = 90 + 2 * e, $fn = 64);
}
// El pivote queda 45 mm BAJO el punto medio (en z del mundo, no en la normal): en el plano de los dedos el
// escape esta 11,65 mm aguas abajo de lo que sugiere visor.js, asi que el vaso retenido descansa contra el dedo
// A ~17 mm mas abajo que "primero" (visor.js:2051), con la pestana ya asomada sobre el embudo de la cuna.
can_y_primero = -417.5 + 40 * can_c;
can_y_ret = can_y_primero - 17 * can_c;
// Vasos quietos: entregado, a mitad de camino y segundo de la fila (el retenido por A no se dibuja quieto:
// tapa el pasillo de los remaches de la viga de topes, que se meten antes de cargar vasos; su posicion la
// cubre el barrido del vaso).
can_vasos = [-187.05, -255, can_y_ret + 82 * can_c];
can_y_fin_barrido = -417.5;   // hasta que el centro llega al fin de los rieles (sigue en la cuna del carro)

// ----------------------------------------------------------------- cabezales (lado -x; el +x es su espejo)
// Funda de 22 sobre la punta del poste (2 remaches por la cara de afuera, la una abre en el hueco del tubo),
// tapa con techo en piramide de 45 (sale sin soportes) y bloque inclinado a 15 con la cuna de la varilla:
// la cuna abraza la varilla por abajo y por afuera hasta 40 grados sobre el eje (uña) y por adentro no pasa de
// x_riel + 1.9 (a la sombra de la varilla: el cuerpo del vaso nunca la toca). Arriba de la varilla no hay nada:
// por ahi pasa la pestana (el bloque queda <= 1,5 sobre el eje; la pestana a 2,13).
// El prisionero impreso aprieta la varilla desde afuera contra la cuna y la una: la traba (en el centro del
// bloque la una se corta para dejarlo pasar).
can_px = 297.5;
can_xr = can_px + 28;              // 325.5
can_postes = [["c1", -211.1, 175.28], ["c3", -309.5, 148.91]];
can_paso = 3; can_exc = 0.45; can_r_tor = 2.5;               // rosca de los prisioneros (flanco de 43 grados)
can_largo_pris = 38.8 - can_r_riel;                          // de la varilla a la cara de afuera (+0,2)
function can_rp(py) = [can_xr, py, can_zr(py)];

module can_rosca(L, r) linear_extrude(height = L, twist = -360 * L / can_paso, slices = ceil(L / 0.25))
  translate([can_exc, 0]) circle(r = r, $fn = 24);
module can_en_pris(py) can_en_riel(can_rp(py)) translate([-can_r_riel, 0, -1.7]) rotate([0, -90, 0]) children();

module can_cabezal_izq(py, ptop) {
  R = can_rp(py);
  difference() {
    intersection() {
      translate([can_px - 10.6, py - 10.6, ptop - 22]) cube([can_xr + 1.9 - can_px + 10.6, 21.2, 60]);
      can_en_riel(R) union() {                                   // cara de arriba (escalones a lo ancho)
        translate([-60, -20, -60]) cube([60 - 6.5, 40, 64]);     // afuera de la pestana: alto 4
        translate([-6.5, -20, -60]) cube([5.5, 40, 61.5]);       // una: 1,5
        translate([-1, -20, -60]) cube([2.9, 40, 61]);
      }
      union() {                                                  // por dentro de la funda, fondo a 50 grados
        translate([can_px - 12, py - 20, ptop - 22]) cube([22.6, 40, 80]);
        translate([can_px + 10.6, py - 20, ptop - 22]) rotate([0, -50, 0]) cube([200, 40, 200]);
      }
    }
    hull() { translate([can_px - 8.2, py - 8.2, ptop - 23]) cube([16.4, 16.4, 23]); translate([can_px, py, ptop + 8.2]) cube(0.01, center = true); }
    can_en_riel(R) rotate([90, 0, 0]) cylinder(r = can_r_ranura, h = 60, center = true, $fn = 40);
    can_en_riel(R) translate([-6.6, -4, -0.2]) cube([4.6, 8, 5]);
    can_en_pris(py) can_rosca(can_largo_pris + 1, can_r_tor + tol);
  }
}
module can_prisionero_izq(py) can_en_pris(py) {
  can_rosca(can_largo_pris, can_r_tor);
  translate([0, 0, can_largo_pris - 0.01]) cylinder(d = 10, h = 4, $fn = 6);   // cabeza hexagonal (a mano)
}

// ----------------------------------------------------------------- escape de dos dedos
// Marco del escape: X = a lo largo del riel (aguas abajo), Y = normal al plano de los rieles (eje del SG90),
// Z = hacia adentro (-x). Origen = pivote (visor.js:2040-2091).
can_piv = [410, -417.5 + 43 * can_c, can_zr(-417.5) + 43 * can_s - 45];
CAN_ME = [[0, 0, -1, can_piv[0]], [-can_c, -can_s, 0, can_piv[1]], [-can_s, can_c, 0, can_piv[2]], [0, 0, 0, 1]];
function can_inv(M) = let(R = [[M[0][0], M[1][0], M[2][0]], [M[0][1], M[1][1], M[2][1]], [M[0][2], M[1][2], M[2][2]]],
  q = -(R * [M[0][3], M[1][3], M[2][3]])) [concat(R[0], q[0]), concat(R[1], q[1]), concat(R[2], q[2]), [0, 0, 0, 1]];
can_th0 = asin(7 / 38);          // dedo 7 mm adentro / afuera (visor.js:2112)
can_th_ret = -can_th0;           // retener: dedo A (aguas abajo) adentro

// Balancin: barra de 82 x 6 x 5 con los dedos de 5 x 5 a +-38, 21 mm hacia el eje de la canaleta (visor: 23;
// con 23 el dedo A, al soltar, pasa 1 mm detras de la cola del carro y toca la pared de la cuna).
// Va sobre el brazo simple del SG90 (MEDIR: agujeros del brazo a 8 y 13 mm del eje, tornillos del kit).
module can_bal_parte(k) {
  if (k == 0) translate([-41, -2.5, -3]) cube([82, 5, 6]);
  if (k == 1) rotate([-90, 0, 0]) translate([0, 0, -2.5]) cylinder(r = 6, h = 5);
  if (k >= 2) translate([(k == 2 ? 38 : -38) - 2.5, -2.5, 0]) cube([5, 5, 21]);
}
module can_balancin_loc() difference() {
  union() for (k = [0:3]) can_bal_parte(k);
  rotate([-90, 0, 0]) cylinder(d = 2.6, h = 20, center = true);
  for (x = [8, 13]) translate([x, 0, 0]) rotate([-90, 0, 0]) cylinder(d = 1.6, h = 20, center = true);
}
// SG90 (MEDIR: eje a 5,85 de la punta del cuerpo; orejas de 32,2 a 4,5 bajo la tapa; agujeros a 27,6)
module can_sg90_loc() {
  translate([-16.65, -30.2, -5.9]) cube([22.5, 22.7, 11.8]);
  translate([-21.5, -14.5, -5.9]) cube([32.2, 2.5, 11.8]);
  rotate([-90, 0, 0]) translate([0, 0, -7.5]) cylinder(r = 5.9, h = 3);
  rotate([0, can_th_ret, 0]) {   // brazo simple (del kit)
    rotate([-90, 0, 0]) translate([0, 0, -4.5]) cylinder(r = 3.5, h = 2);
    translate([0, -4, -2.5]) cube([15, 1.5, 5]);
  }
}
// Soporte del SG90: cuna inclinada (las orejas apoyan arriba y se atornillan con los tornillos del kit) unida
// con un casco a una base remachada a la cara -x del tubo C4-M2 (entre los nodos, 2 remaches). El tunel
// deja meter los remaches. Se imprime acostado sobre la cara x = 401.5.
module can_soporte_escape() difference() {
  union() {
    hull() {
      multmatrix(CAN_ME) translate([-23.5, -33, -6.1]) cube([36.2, 18.5, 14.6]);
      translate([401.5, -361.8, 14.1]) cube([7.5, 19.3, 4.5]);
    }
    difference() {
      translate([401.5, -362, 0]) cube([12.8, 19.5, 18.6]);
      translate([395, -363, 7.1]) cube([16.3, 22, 7]);
    }
  }
  multmatrix(CAN_ME) {
    translate([-16.85, -30.4, -10]) cube([22.9, 31, 16.1]);
    for (x = [-19.2, 8.4]) translate([x, -14.49, 0]) rotate([90, 0, 0]) cylinder(d = 1.8, h = 8, $fn = 12);
  }
}

// ----------------------------------------------------------------- muelle de carga
// Marco del carro estacionado (geometria.py:314-338): xi adelante (= -y del mundo), eta a la izquierda (= +x).
// Guias: cara interna a eta 88 + 5 + 3 = 96, rectas de xi -94 a 15.1, boca en V de 200 que abre 45.
// Alto 16 (el inventario dice 20): el brazo del rodillo guia del carro real (chasis.scad, r 6 en z 17.5)
// sobresale 1 mm mas que el rodamiento y con 20 se montaria sobre la guia.
// Topes: cara a xi -93 (y -414.5) con espuma de 6, a eta +-52 (22 de ancho), alto hasta 44.5: los empujan los
// bloques de los rodillos (z 17.5-46). Van en una viga que pasa por ENCIMA de los nodos M1/M2 (sin tocarlos)
// y se remacha arriba del tubo M1-M2.
module can_topes() union() {
  translate([296, -408.5, 24.8]) cube([128, 18.5, 5.2]);      // los nodos llegan a z 24.4 (alero)
  for (x = [297, 401]) translate([x, -408.5, 24.8]) cube([22, 18.5, 19.7]);
  translate([330.5, -408.5, 18.8]) cube([59, 18.5, 11.2]);
  translate([330.5, -408.5, 0]) cube([59, 5.3, 18.8]);
}
// Guia recta del lado +x: placa remachada a la cara +x del tubo C4-M2 (entre nodos), losa baja (deja pasar
// los remaches por encima), pared + ala hasta y -522.6 y el hueco de la cola de milano de la boca.
module can_cola_2d(o = 0) offset(delta = o) polygon([[466, -522.6], [472, -522.6], [474, -512.6], [464, -512.6]]);
module can_guia_recta() difference() {
  union() {
    translate([430.7, -362, 0]) cube([4, 19.5, 18.6]);
    translate([434.7, -362, 0]) cube([41.3, 19.5, 6]);
    translate([456, -522.4, 0]) cube([6, 160.4, 16]);
    translate([462, -522.4, 0]) cube([14, 160.4, 4]);
  }
  translate([0, 0, -1]) linear_extrude(6) offset(delta = tol) union() {
    can_cola_2d(); translate([464, -530]) square([10, 7.5]);
  }
}
module can_guia_v() union() {
  linear_extrude(16) polygon([[456, -522.6], [501, -722.6], [507, -722.6], [462, -522.6]]);
  linear_extrude(4) polygon([[462, -522.6], [507, -722.6], [521, -722.6], [476, -522.6]]);
  linear_extrude(4) can_cola_2d();
}

// ----------------------------------------------------------------- listas
PIEZAS_CAN = ["can_cabezal_c1", "can_cabezal_c3", "can_cabezal_c2", "can_cabezal_c4",
  "can_prisionero_c1", "can_prisionero_c3", "can_prisionero_c2", "can_prisionero_c4",
  "can_soporte_escape", "can_balancin", "can_topes",
  "can_guia_recta_xn", "can_guia_recta_xp", "can_guia_v_xn", "can_guia_v_xp"];

REM_CAN = concat(
  [for (p = can_postes, dz = [8, 17], s = [-1, 1])
    [str("r_can_cab_", s < 0 ? p[0] : (p[0] == "c1" ? "c2" : "c4"), "_", dz), 4.2, [360 + s * (360 - can_px + 10.6), p[1], p[2] - dz], [-s, 0, 0]]],
  [for (y = [-347.5, -357.0]) [str("r_can_escape_", -y), 4.8, [411.3, y, 10.6], [1, 0, 0]]],
  [for (y = [-347.5, -357.0], s = [-1, 1]) [str("r_can_guia_", s < 0 ? "xn" : "xp", "_", y), 5.8, [360 + s * 74.7, y, 10.6], [-s, 0, 0]]],
  [for (x = [345, 375]) [str("r_can_topes_", x), 13.0, [x, -395, 30], [0, 0, -1]]]);

// lo que se mueve (lista LITERAL: la lee moviles_por_defecto.scad antes que este archivo)
MOVILES_CAN = [["can_balancin", []], ["can_vaso", ["can_balancin"]]];

module can_pieza(n) {
  if (n == "can_cabezal_c1") can_cabezal_izq(-211.1, 175.28);
  else if (n == "can_cabezal_c3") can_cabezal_izq(-309.5, 148.91);
  else if (n == "can_cabezal_c2") can_espejo() can_cabezal_izq(-211.1, 175.28);
  else if (n == "can_cabezal_c4") can_espejo() can_cabezal_izq(-309.5, 148.91);
  else if (n == "can_prisionero_c1") can_prisionero_izq(-211.1);
  else if (n == "can_prisionero_c3") can_prisionero_izq(-309.5);
  else if (n == "can_prisionero_c2") can_espejo() can_prisionero_izq(-211.1);
  else if (n == "can_prisionero_c4") can_espejo() can_prisionero_izq(-309.5);
  else if (n == "can_soporte_escape") can_soporte_escape();
  else if (n == "can_balancin") multmatrix(CAN_ME) rotate([0, can_th_ret, 0]) can_balancin_loc();
  else if (n == "can_topes") can_topes();
  else if (n == "can_guia_recta_xp") can_guia_recta();
  else if (n == "can_guia_recta_xn") can_espejo() can_guia_recta();
  else if (n == "can_guia_v_xp") can_guia_v();
  else if (n == "can_guia_v_xn") can_espejo() can_guia_v();
}

// Para imprimir: cabezales y guias como estan; prisionero parado sobre la cabeza; soporte acostado sobre su
// cara -x; balancin plano; viga de topes sobre su cara -y.
function can_py_pris(n) = (n == "can_prisionero_c1" || n == "can_prisionero_c2") ? -211.1 : -309.5;
module can_a_cama(n) {
  if (n == "can_prisionero_c1" || n == "can_prisionero_c3")
    rotate([180, 0, 0]) rotate([0, 90, 0]) translate([can_r_riel, 0, 1.7]) rotate([-15, 0, 0]) translate(-can_rp(can_py_pris(n))) children();
  else if (n == "can_prisionero_c2" || n == "can_prisionero_c4")
    rotate([180, 0, 0]) rotate([0, -90, 0]) translate([-can_r_riel, 0, 1.7]) rotate([-15, 0, 0])
      translate(-[720 - can_xr, can_py_pris(n), can_zr(can_py_pris(n))]) children();
  else if (n == "can_soporte_escape") rotate([0, -90, 0]) children();
  else if (n == "can_balancin") rotate([90, 0, 0]) multmatrix(can_inv(CAN_ME)) children();
  else if (n == "can_topes") rotate([90, 0, 0]) children();
  else children();
}

// Barridos: el balancin de soltar a retener (cada parte en pasos, para no rellenar entre los dedos) y el vaso
// de la entrega hasta la cola del carro (pestana y cuerpo por separado; se restan los 3 vasos quietos).
module can_barrido(n) {
  if (n == "can_balancin") {
    N = 6;
    for (k = [0:3], i = [0:N - 1]) hull() for (j = [i, i + 1])
      multmatrix(CAN_ME) rotate([0, -can_th0 + 2 * can_th0 * j / N, 0]) can_bal_parte(k);
  } else if (n == "can_vaso") difference() {
    union() for (p = ["pestana", "cuerpo"]) hull() { can_vaso_en(can_vasos[0], 0, p); can_vaso_en(can_y_fin_barrido, 0, p); }
    for (y = can_vasos) can_vaso_en(y, 0.3);
  }
}

// Comprado: varillas, SG90 con su brazo, vasos, espuma de los topes (MEDIR: EVA de 6) y el carro como caja
// (180 x 120 x 140) menos el hueco de la cuna.
module can_comprados() {
  for (s = [-1, 1]) can_varilla(s);
  multmatrix(CAN_ME) can_sg90_loc();
  for (y = can_vasos) can_vaso_en(y);
  for (x = [297, 401]) translate([x, -414.5, 22]) cube([22, 6, 22.5]);
  difference() {   // carro: caja simple con el hueco de la cuna (por ahi entra el vaso colgado)
    translate([300, -597.5, 0]) cube([120, 180, 140]);
    translate([318, -600, 38]) cube([84, 190, 110]);
  }
}
