// Escenas del manual de armado y del modelo 3D (las llaman manual.py y modelo_3d.py).
//   modo = "paso":  lo armado antes en gris, lo impreso que se agrega en este paso en naranja y lo
//                   comprado con sus colores. Los pasos van en el orden de las tandas de impresion.
//   modo = "pieza": el carro entero en gris con una pieza (todas sus copias) en naranja: donde va.
//   modo = "solo":  solo esa pieza (todas sus copias) en su lugar del ensamble (para el GLB).
//   modo = "paso_rem": lo armado hasta ese paso en gris, con los remaches del paso en color.
//   modo = "remaches": el carro en gris con TODOS los remaches en su lugar, un color por medida.
include <chasis.scad>
pieza = "nada";   // que chasis.scad no dibuje nada por su cuenta
modo = "paso";
paso = 1;
cual = "chasis";
ocultar = [];     // modo "pieza": piezas o grupos de componentes que no se dibujan (los que tapan la pieza)

// Todas las copias de una pieza en su lugar del ensamble.
module instancias(n) {
  if (n == "zapata_guia") { for (s = [-1, 1], x = zapatas_x) zapata_ens(x, s); }
  else pieza_ens(n);
}
EN_EL_CARRO = ["chasis", "barra_tcrt5000", "porta_baterias", "pared_cuna_izq", "pared_cuna_der", "mampara",
  "zapata_guia", "lengueta", "soporte_motor_izq", "soporte_motor_der", "soporte_encoder_izq", "soporte_encoder_der",
  "torre_rueda_loca", "soporte_rodillo_izq", "soporte_rodillo_der", "caja_interruptor", "caja_fusible",
  "escuadra_frontal", "piso2_esp32", "soporte_tb6612"];

GRUPOS = ["motores", "ruedas", "rodillos", "encoders", "baterias", "esp32", "tb", "frente", "ir", "loca", "cajas", "vaso", "espumas"];
function esta(x, l) = len([for (y = l) if (y == x) 1]) > 0;

// Pasos (mismo orden que PASOS en manual.py): que piezas impresas y que compradas se agregan.
module impresas(n) {
  if (n == 0) chasis_ens();
  if (n == 1) barra_ir_ens();                                                              // tanda 1
  if (n == 2) porta_bateria_ens();                                                         // tanda 1
  if (n == 3) { for (s = [-1, 1]) { pared_cuna_ens(s); for (x = zapatas_x) zapata_ens(x, s); } lengueta_ens(); mampara_ens(); }   // tanda 2
  if (n == 4) for (s = [-1, 1]) { soporte_motor_ens(s); if (con_encoders) soporte_encoder_ens(s); }   // tanda 3
  if (n == 6) { torre_loca_ens(); for (s = [-1, 1]) soporte_rodillo_ens(s); }               // tanda 3
  if (n == 8) { caja_int_ens(1); caja_int_ens(-1); }                                       // tanda 4
  if (n == 9) escuadra_frontal_ens();                                                      // tanda 4
  if (n == 10) { piso2_ens(); soporte_tb_ens(); }                                          // tanda 4
}
module compradas(n) {
  if (n == 1) componentes("ir");
  if (n == 3) componentes("espumas");
  if (n == 4) componentes("motores");
  if (n == 5) componentes("encoders");
  if (n == 6) { componentes("loca"); componentes("rodillos"); }
  if (n == 7) componentes("ruedas");
  if (n == 8) { componentes("cajas"); componentes("baterias"); }
  if (n == 9) componentes("frente");
  if (n == 10) { componentes("esp32"); componentes("tb"); }
  if (n == 11) componentes("vaso");
}

// Remaches de cada paso en su lugar, con una flecha que entra por el lado de la cabeza (por donde
// se meten). Un color por medida: los mismos de COLOR_REM en manual.py.
COLOR_REM = [["remache_6", "#ff2fa0"], ["remache_9_5", "#8a2be2"], ["remache_10_5", "#e0001b"],
             ["remache_11", "#0077ff"], ["remache_14", "#00a651"], ["remache_37", "#00c8d7"]];
function rem_agarre(n) = REMACHES[search([n], [for (r = REMACHES) r[0]])[0]][1];
function rem_color(n) = COLOR_REM[search([n], [for (c = COLOR_REM) c[0]])[0]][1];
module rem(n, flecha) color(flecha ? rem_color(n) : "#a7adb3") {
  remache(rem_agarre(n));
  if (flecha) translate([0, 0, -rem_cabeza[1] - 2]) mirror([0, 0, 1]) {
    cylinder(d1 = 0, d2 = 6, h = 7); cylinder(d = 2, h = 28); }
}
// Cada remache: [paso, medida, punto donde apoya la cabeza, eje de la cabeza hacia la una]. La una sale
// por la cara de enfrente: bajo el chasis (z_abajo) si entra desde arriba, sobre el chasis (z_plano) si
// entra desde abajo. La usan tambien revisar_remaches.py y el dibujo de cada paso.
function arriba(p, x, y, n) = [p, n, [x, y, z_abajo + rem_agarre(n)], [0, 0, -1]];
function abajo(p, x, y, n) = [p, n, [x, y, z_plano - rem_agarre(n)], [0, 0, 1]];
REM_LISTA = concat(
  [for (s = [-1, 1]) arriba(2, x_bateria, s * 22, "remache_10_5")],
  [for (s = [-1, 1], x = x_pie_pared) arriba(3, x, s * 42, "remache_11")],
  [for (s = [-1, 1]) arriba(3, 12, s * 24, "remache_11")],
  [for (s = [-1, 1], z = z_rem_mampara) [3, "remache_9_5", [x_mampara + e_mampara, s * y_rem_mampara, z], [-1, 0, 0]]],
  [[3, "remache_6", [piv_leng[0], -(y_pared + e_pared) - 6, piv_leng[1] + 3.3], [0, 0, -1]]],
  [for (s = [-1, 1]) abajo(4, x_eje - 15, s * y_motor, "remache_14")],
  [for (s = [-1, 1]) abajo(4, x_oreja_del, s * y_motor, "remache_10_5")],
  [for (s = [-1, 1], x = [rodillo_x + 3, rodillo_x + 11]) abajo(6, x, s * 54, "remache_37")],
  [for (s = [-1, 1], x = [x_caja_int[0] + 4, x_caja_int[1] - 4]) arriba(8, x, s * 51, "remache_10_5")],
  [for (s = [-1, 1]) arriba(9, x_frente - 14, s * 16, "remache_11")]
);
module en_eje(r) translate(r[2]) { if (r[3][2] < 0) mirror([0, 0, 1]) children(); else if (r[3][2] > 0) children(); else rotate([0, -90, 0]) children(); }
module remaches(n, f = true) for (r = REM_LISTA) if (r[0] == n) en_eje(r) rem(r[1], f);

if (modo == "paso") {
  color("#a7adb3") for (k = [0:max(0, paso - 1)]) if (k < paso) impresas(k);
  for (k = [1:max(1, paso - 1)]) if (k < paso) { compradas(k); remaches(k, false); }
  color("#ff7a1a") impresas(paso);
  compradas(paso);
  remaches(paso);
} else if (modo == "paso_rem") {   // igual que "paso" pero todo en gris: solo resaltan los remaches del paso
  color("#c9cdd1") for (k = [0:paso]) impresas(k);
  for (k = [1:paso]) { compradas(k); remaches(k, k == paso); }
} else if (modo == "remaches") {
  color("#c9cdd1") for (k = [0:10]) impresas(k);
  for (k = [0:10]) remaches(k);
} else if (modo == "pieza") {
  color("#c9cdd1") for (n = EN_EL_CARRO) if (n != cual && !esta(n, ocultar)) instancias(n);
  color("#ff7a1a") instancias(cual);
  for (g = GRUPOS) if (!esta(g, ocultar)) componentes(g);
} else if (modo == "solo") {
  instancias(cual);
}
