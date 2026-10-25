// =====================================================================================
// Subsistema "cinta_vasos" (prefijo vas_): cinta de vasos impresa en PLA (ver CONVENCIONES.md).
// Lo incluye maqueta.scad; este archivo NO hace include de nada.
//
// Lo funcional (inventario_maqueta.md §5, §9, §10, §18) NO se movio:
//   estaciones x 40/120/200/280/360 en y -100, superficie de la banda z 122, rodillos Ø22 con eje en
//   x 0 y x 400 a z 109 (2026-10-25, antes 111: la banda de 2 los envuelve y su cara de abajo queda en
//   z 120, sobre la bancada; con 111 la banda real quedaba en 124), camara de vasos (160,-400,211.77) mirando a (160,-100,173.97), cortina VL53L0X
//   en (300,-185,187) mirando a -x, panel de luz con su cara en y -60 (x -5..305, z 125..222),
//   bandeja de rechazo centrada en (470,-100) en el piso.
//
// Apoyos (estructura del 2026-10-24, segunda version): nada de la estructura pasa bajo la banda. El bastidor
// se remacha a 4 tubos verticales con la punta a z 120: (40,-152.5) y (315,-152.5) del lado -y (su cara
// +y toca la cara de afuera de la lateral -y) y (30,-40.5) y la columna (315,-40.5) del lado +y (cara -y
// en y -48.5: la lateral +y lleva ahi un taco de 6.8 que llena el hueco).
//
// Piezas (todas PLA):
//   vas_lat_s_a/b   placa lateral -y (antes aluminio 430x34x4; aqui z 72..120), partida en x 200. La "a"
//                   lleva 4 postes huecos (los separadores del NEMA 17) y los agujeros del KFL08; la "b"
//                   la corredera del 608 de x 400 con el tope del tensor.
//   vas_lat_n_a/b   placa lateral +y, partida en x 200, con el buje del 608 de x 0, la corredera y el tope del
//                   tensor del de x 400 y los tacos a los tubos.
//   vas_bancada_a/b bancada (cama de la banda): piel de 4 mm arriba y nervios; va DENTRO del lazo de la
//                   banda (la vuelta pasa por debajo, z 96..98) y se remacha a las 4 laterales (partida
//                   en x 150, desfasada de la union de las laterales: la bancada b hace de cubrejunta).
//   vas_placa_motor placa del NEMA 17, remachada a los 4 postes de vas_lat_s_a.
//   vas_taco_i_a/b  tacos de casilla (11 x 2 mitades, uno por separador): una mitad pegada a cada cara del separador (con tol).
//                   Sin grapa por encima: asi lo mas alto que recorre la banda es el separador (z 137) y no
//                   entra en la zona de la paleta del empujador (z 138).
//   vas_panel_a/b   panel de luz: caja de luz de PLA blanco (frente de 1.6 = difusor, marco de 2.4, atras
//                   abierto para la tira LED), partida en x 150 y remachada; cada mitad con una oreja a la
//                   cara -y de su columna del portico (x -50 y x 315).
//   vas_placa_camara collar sobre la punta del poste (160,-422) con la repisa inclinada de la webcam.
//   vas_cortina     brida + brazo + poste + escuadra del VL53L0X, remachada a la cara -y del tubo (315,-152.5).
//   vas_bandeja     bandeja de rechazo con el labio (rampa) integrado.
// Lo que se mueve: MOVILES_VAS / vas_barrido = envolvente de banda + separadores + tacos en todo el lazo, y el
// vaso de pie por la cinta; SINCRONOS_VAS / vas_fase = el vaso empujado a la canaleta entre sus tacos.
// =====================================================================================

// ----------------------------------------------------------------- funcional (no se mueve)
vas_y = -100;                 // eje de la cinta
vas_z_banda = 122;            // superficie de la banda
vas_e_banda = 2;              // espesor de la banda
vas_x_rod = [0, 400];         // ejes de los rodillos
vas_z_rod = 109;              // arriba del rodillo (120) = cara de abajo de la banda; la de arriba en vas_z_banda
vas_d_rod = 22;
vas_ancho_banda = 75;
vas_paso = 80;
vas_cam = [160, -400, 211.77];      // centro de la carcasa de la webcam
vas_cam_obj = [160, -100, 173.97];  // a donde mira
vas_cam_incl = atan2(vas_cam_obj[2] - vas_cam[2], vas_cam_obj[1] - vas_cam[1]);  // -7.18 grados
vas_cortina = [300, -185, 187];
vas_bandeja_c = [470, -100];

// ----------------------------------------------------------------- bastidor
vas_e_lat = 4;
vas_ys = [-144.5, -140.5];    // lateral -y (cara de afuera, cara de adentro)
vas_yn = [-59.5, -55.5];      // lateral +y (cara de adentro, cara de afuera)
vas_z_lat = [72, 120];
vas_x_union_lat = 200;        // union de las laterales
vas_x_union_banc = 150;       // union de las bancadas
vas_banc_x = [13, 383];       // a 2 del rodillo de x 400 cuando esta en x 396 (armado, tensor flojo); antes 387
vas_banc_z = [104, 119.9];    // abajo: 6 mm sobre la vuelta de la banda (z 98); arriba: 0.1 bajo la banda
vas_banc_y = [vas_ys[1] + tol, vas_yn[0] - tol];
vas_pared_banc = 3;
vas_r_buje = 13.5;            // buje del 608 (Ø22.4 + 2 x 2.3)
vas_x_rem_banc_s = [60, 120, 175, 230, 280];        // remaches laterales <-> bancada, a z 110 (en x 355 el
                                                    // vaso de la canaleta no deja meterlo desde -y)
vas_x_rem_banc_n = [45, 120, 175, 242, 280, 355];   // 242 (antes 230): el puntal del portico (tap_puntal_inf, x 218..234,
                                                    // y -48.5..-32.5) le tapaba el pasillo; libre desde x 239
vas_nervios_banc = [40, 90, 202, 255, 290, 318, 345];   // a >= 5 mm de cada remache (la una abre en la celda); vanos <= 60
vas_piel_banc = 1.6;          // piel de arriba de la bancada, MACIZA (apoya en la cama): nervios cada <= 60 en x y 40 en y
vas_nervio = 1.6;             // nervios y paredes que no llevan remaches (4 perimetros)
// apoyos en la estructura: tubos verticales con punta a z 120
vas_postes_s = [40, 315];     // x de los tubos del lado -y (y -152.5, cara +y en y -144.5)
vas_postes_n = [30, 315];     // x de los tubos del lado +y (y -40.5, cara -y en y -48.5)
vas_z_rem_poste = [80, 101];  // el de arriba: entre la vuelta de la banda (z 98) y la bancada (z 104). 2026-10-25: en z 91
                              // el taco de abajo de x 40 (z 85.9..95.9) le tapaba el paso para meterlo (antes 94: la banda)
// motor
vas_postes = [[-25.4, 96], [-25.4, 126], [25.4, 96], [25.4, 126]];   // (x, z) de los 4 separadores (en +-25 la punta de la cabeza
                                                                     // del remache pisaba 0,15 el NEMA en todo su pasillo)
vas_y_placa_motor = [-182.5, -177.5];   // 2026-10-25: 4 mm mas hacia -y (antes -178.5): con los separadores de 3
                                        // la punta del eje del motor queda en y -161.5, el medio del acople
// tensor del rodillo de x 400 (2026-10-25): el 608 de cada lateral va en una corredera de x 396 a 400. Se arma en
// x 396 (la banda entra floja) y un prisionero M3 x 10, roscado en un tope de la cara de afuera, empuja el aro de
// afuera del 608 hacia +x hasta el fin de la corredera (x 400, la posicion funcional). El prisionero va 1.5 afuera
// de la placa, dentro del ancho del 608: la llave Allen de 1.5 llega a lo largo de x por fuera de la placa. Va 2 bajo
// el eje (z 107): por fuera de la placa -y el vaso que baja a la canaleta (can_vasos[0]) llega hasta z 112.46.
vas_x_ten = [396, 400];
vas_x_tope = 372;             // cara -x del tope: el prisionero queda de x 375 a 385 armado y de 379 a 389 tensado
vas_z_ten = vas_z_rod - 2;    // eje del prisionero; toca el aro del 608 a 10.8 de su eje
vas_m3_rosca = 2.5;           // MEDIR: agujero donde rosca el prisionero M3 en el PLA

// ----------------------------------------------------------------- comprado (MEDIR lo que no esta en el inventario)
vas_608 = [8, 22, 7];
vas_nema = 42.3;              // NEMA 17 17HS4401: 42.3 x 42.3 x 40, eje Ø5 x 24, M3 a 31
vas_r_base_vaso = 26.66;      // radio de la base del vaso (linea_vasos.js; MEDIR en el vaso real)
vas_sep = [3, 75, 15];        // separador de la banda (comprado con la banda; MEDIR)
vas_recorte_sep = 3;          // se recortan 3 mm del extremo -y de cada separador: el vaso entregado a la
                              // canaleta (can_vasos[0]) asoma 1.7 mm sobre el borde -y de la banda
vas_gy530 = [25, 13, 1.6];    // MEDIR: placa GY-530 del VL53L0X (inventario: ~25 x 13)
vas_led = [8, 2];             // MEDIR: tira LED 5 V, ancho x alto
vas_cam_tornillo = 6.6;       // MEDIR: la webcam se sujeta con tornillo 1/4" (si trae clip, cambiar)

// ----------------------------------------------------------------- tacos de casilla: [x, y, z, giro en y]
// La banda cerrada mide 2 x 400 + 2 pi x 12 (linea media) = 875.4: con un separador cada 80 la ultima casilla no
// cerraba. 2026-10-25: 11 separadores a L/11 = 79.58 a lo largo de todo el lazo, contados desde el empalme, uno con
// sus dos medios tacos (antes 7: 6 arriba cada 80 y uno abajo, con dos huecos de 238). Fase: la casilla del empujador
// (entre el 5.o y el 6.o) centrada en x 360; las otras estaciones quedan corridas 0.42 por casilla (x 40: 1.67), lo
// que corrige la resincronizacion por camara. Con esta fase quedan 6 arriba (x 1.9..399.8) y 5 en el ramal de abajo.
vas_n_sep = 11;
vas_L = 2 * (vas_x_rod[1] - vas_x_rod[0]) + PI * (vas_d_rod + vas_e_banda);
vas_paso_sep = vas_L / vas_n_sep;
vas_u0 = 4.5 * (vas_paso - vas_paso_sep);    // u del 1.er separador: (u0 + 4.5 paso_sep) = x 360
// pie del separador a u mm de la tangente de arriba del rodillo de x 0, en el sentido de avance (+x arriba): en la cara
// de afuera de la banda, con el giro en y del marco del taco (arriba 0, abajo 180; en las vueltas, alrededor del eje)
function vas_lazo(u) = let(D = vas_x_rod[1] - vas_x_rod[0], r = (vas_d_rod + vas_e_banda) / 2, ra = vas_d_rod / 2 + vas_e_banda,
                           s = PI * r, w = u % vas_L, g = (w - D) / r * 180 / PI, g2 = (w - 2 * D - s) / r * 180 / PI)
  w < D ? [vas_x_rod[0] + w, vas_y, vas_z_rod + ra, 0]
  : w < D + s ? [vas_x_rod[1] + ra * sin(g), vas_y, vas_z_rod + ra * cos(g), g]
  : w < 2 * D + s ? [vas_x_rod[1] - (w - D - s), vas_y, vas_z_rod - ra, 180]
  : [vas_x_rod[0] - ra * sin(g2), vas_y, vas_z_rod - ra * cos(g2), 180 + g2];
VAS_TACOS = [for (i = [0:vas_n_sep - 1]) vas_lazo(vas_u0 + i * vas_paso_sep)];
VAS_N_TACOS = [for (i = [1:vas_n_sep], m = ["a", "b"]) str("vas_taco_", i, "_", m)];
// tap_fase("tap_descarga") y vas_descarga usan vas_taco_5_b y vas_taco_6_a: la casilla del empujador, arriba y en x 360
assert(VAS_TACOS[4][3] == 0 && VAS_TACOS[5][3] == 0 && abs(VAS_TACOS[4][0] + VAS_TACOS[5][0] - 720) < 1e-6,
       "vas: la casilla del empujador (taco 5 y 6) tiene que quedar arriba y centrada en x 360");

// ----------------------------------------------------------------- piezas
PIEZAS_VAS = concat(["vas_lat_s_a", "vas_lat_s_b", "vas_lat_n_a", "vas_lat_n_b", "vas_bancada_a", "vas_bancada_b",
  "vas_placa_motor"], VAS_N_TACOS,
  ["vas_panel_a", "vas_panel_b", "vas_placa_camara", "vas_cortina", "vas_bandeja"]);

// lo que se mueve: el lazo de la banda (los tacos van con ella)
// (lista escrita entera: moviles_por_defecto.scad ya asigna MOVILES_VAS y OpenSCAD evalua la reasignacion
// en el lugar de la primera, donde VAS_N_TACOS todavia no existe)
// tap_emp_paleta: el empujador solo se mueve con la cinta parada (descarga), nunca a la vez que la banda
// vas_vaso: el vaso de pie de x 0 a 360 (con tapa desde x 200). Lo llevan los tacos y la banda (vas_vuelta_banda);
// la paleta del empujador y el plato de la prensa lo tocan a proposito con la cinta parada (x 360 y x 280).
MOVILES_VAS = [["vas_vuelta_banda", concat([for (i = [1:11], m = ["a", "b"]) str("vas_taco_", i, "_", m)], ["tap_emp_paleta"])],
  ["vas_vaso", concat([for (i = [1:11], m = ["a", "b"]) str("vas_taco_", i, "_", m)],
                      ["vas_vuelta_banda", "tap_emp_paleta", "tap_pre_plato"])]];
// Descarga (2026-10-25): el vaso en x 360 empujado hacia -y los 54.6 que lo lleva la paleta (a 180 grados), contra
// los dos medios tacos de su casilla. Antes los arcos lo trababan a los 0.5 mm.
SINCRONOS_VAS = [["vas_descarga", 0]];

// ----------------------------------------------------------------- remaches [nombre, agarre, cabeza, eje]
// agarre = suma de lo que atraviesa (+0.2 por holgura; +0.4 donde la pieza de adentro queda en una U y el remache,
// al entrar, la corre hasta el otro lado); la una abre al aire o al hueco de un tubo.
REM_VAS = concat(
  // laterales <-> bancada: lateral 4 + 0.4 + pared de la bancada 3 (la bancada tiene 0.4 de juego entre las dos
  // laterales); la una abre en una celda de la bancada
  [for (x = vas_x_rem_banc_s) [str("r_vas_banc_s_", x), 7.4, [x, vas_ys[0], 110], [0, 1, 0]]],
  [for (x = vas_x_rem_banc_n) [str("r_vas_banc_n_", x), 7.4, [x, vas_yn[1], 110], [0, -1, 0]]],
  // lateral -y <-> tubos (40,-152.5) y (315,-152.5): desde adentro, lateral 4 + pared 1.6 (se tocan)
  [for (x = vas_postes_s, z = vas_z_rem_poste) [str("r_vas_poste_s_", x, "_", z), 5.6, [x, vas_ys[1], z], [0, -1, 0]]],
  // lateral +y (con su taco) <-> tubos (30,-40.5) y (315,-40.5): desde adentro, lateral 4 + taco 6.8 + 0.2 + pared 1.6
  [for (x = vas_postes_n, z = vas_z_rem_poste) [str("r_vas_poste_n_", x, "_", z), 12.6, [x, vas_yn[0], z], [0, 1, 0]]],
  // placa del motor <-> postes: placa 5 + 0.2 + tapa del poste 2; la una abre dentro del poste hueco
  [for (p = vas_postes) [str("r_vas_motor_", p[0], "_", p[1]), 7.2, [p[0], vas_y_placa_motor[0], p[1]], [0, 1, 0]]],
  // cortina <-> cara -y del tubo (315,-152.5): brida 3 + 0.2 + pared 1.6
  [for (z = [104, 112]) [str("r_vas_cortina_", z), 4.8, [315, -163.7, z], [0, 1, 0]]],
  // panel <-> columnas del portico (cara -y, y -48.5): oreja 11.3 + 0.2 + pared 1.6
  [for (x = [-50, 315], z = [150, 165]) [str("r_vas_panel_col_", x, "_", z), 13.1, [x, -60, z], [0, 1, 0]]],
  // union de las dos mitades del panel: pared 2.4 + 0.2 + pared 2.4, por dentro de la caja
  [for (z = [150, 200]) [str("r_vas_panel_union_", z), 5.0, [147.5, -54.2, z], [1, 0, 0]]],
  // placa de la camara <-> poste: collar 2.4 + 0.4 + pared 1.6 (el tubo tiene 0.4 de juego en el collar)
  [["r_vas_cam_x1", 4.4, [170.6, -422, 172], [-1, 0, 0]], ["r_vas_cam_x0", 4.4, [149.4, -422, 180], [1, 0, 0]]]
);

// ----------------------------------------------------------------- ayudas
module vas_cil_y(c, d, y0, y1) translate([c[0], y1, c[1]]) rotate([90, 0, 0]) cylinder(d = d, h = y1 - y0);
module vas_marco_cam() translate(vas_cam) rotate([vas_cam_incl, 0, 0]) children();
// perfil (x,z) extruido en y entre y0 e y1
module vas_en_y(y0, y1) translate([0, y1, 0]) rotate([90, 0, 0]) linear_extrude(y1 - y0) children();

// ----------------------------------------------------------------- laterales
module vas_lat_s(x0, x1) difference() {
  union() {
    translate([x0, vas_ys[0], vas_z_lat[0]]) cube([x1 - x0, vas_e_lat, vas_z_lat[1] - vas_z_lat[0]]);
    if (x0 < 0) {
      translate([-36, vas_ys[0], vas_z_lat[0]]) cube([72, vas_e_lat, 136 - vas_z_lat[0]]);   // sube a z 136 por los postes
      for (p = vas_postes) vas_poste_motor(p, 6, vas_y_placa_motor[1] + tol);
      for (p = vas_postes) vas_nervio_poste(p, 6, vas_y_placa_motor[1] + tol, p[1] < vas_z_rod ? vas_z_lat[0] : vas_postes[0][1] + 6);
    }
    if (x1 > 400) { vas_buje_y(vas_x_ten, 2 * vas_r_buje, vas_ys[0] - 4, vas_ys[1]); vas_tope_ten(vas_ys[0], -1); }
  }
  if (x0 < 0) {
    vas_cil_y([0, vas_z_rod], 12, vas_ys[0] - 1, vas_ys[1] + 1);                       // paso del eje motriz
    for (z = [-18, 18]) vas_cil_y([0, vas_z_rod + z], 5.5, vas_ys[0] - 1, vas_ys[1] + 1);  // tornillos del KFL08 (brida vertical)
    for (p = vas_postes) vas_poste_motor(p, 3.6, vas_y_placa_motor[1] + tol + 2);          // hueco; tapa de 2 al lado del motor
  }
  if (x1 > 400) { vas_ojal_y(vas_x_ten, vas_608[1] + 2 * tol, vas_ys[0] - 5, vas_ys[1] + 1); vas_rosca_ten(vas_ys[0] - 1.5); }
  if (x1 > 400) { vas_muesca_vaso_lat(); vas_muesca_ten(); }
  vas_ventanas_lat(x0, x1, vas_ys,
    concat([for (x = vas_x_rem_banc_s) [x, 110]], [for (x = vas_postes_s, z = vas_z_rem_poste) [x, z]]),
    // sin ventanas a +-10 de los tubos (como en la lateral +y): con el remache de arriba en z 101 su disco de material
    // quedaba suelto dentro de un rombo y nacia en el aire en z 93.8
    concat([[-40, 34]], x1 > 400 ? [[vas_x_tope - 3, 415]] : [], [for (x = vas_postes_s) [x - 10, x + 10]]));
}
// Corredera del 608 de x 400 (buje o agujero): hull en x de vas_x_ten
// techo en gota (punta arriba): las laterales y la placa del motor se imprimen de pie y un agujero horizontal de 22,4
// sin gota es un techo de 22 en el aire (el 608 asienta en el resto del circulo)
module vas_gota_y(c, d, y0, y1) hull() { vas_cil_y(c, d, y0, y1); vas_cil_y([c[0], c[1] + d / 2 * sqrt(2) - 0.5], 1, y0, y1); }
// En las laterales la punta de la gota (z 124.8) pasaba el anillo del buje (arriba en 122.5) y lo abria con filos de
// 0.15: se corta plana en vas_z_techo_608 (puente de 8 en x 0 y de 12 en la corredera, con pared en las dos puntas)
vas_z_techo_608 = 121;
module vas_ojal_y(xs, d, y0, y1) intersection() {
  hull() for (x = xs) vas_gota_y([x, vas_z_rod], d, y0, y1);
  translate([xs[0] - d, y0 - 1, 0]) cube([xs[len(xs) - 1] - xs[0] + 2 * d, y1 - y0 + 2, vas_z_techo_608]);
}
// El buje (macizo) sigue redondo de lado, con dos agregados para imprimirlo de pie: abajo en gota (punta abajo, 45),
// porque sale 4 de la placa y su panza colgaba; arriba plano en z 122.5 (el mismo alto) sobre el techo del 608, para
// que queden 1.5 encima en todo el puente (redondo, en las puntas del puente quedaban 0.9).
module vas_buje_y(xs, d, y0, y1) hull() for (x = xs) {
  vas_cil_y([x, vas_z_rod], d, y0, y1);
  vas_cil_y([x, vas_z_rod - d / 2 * sqrt(2) + 0.5], 1, y0, y1);
  translate([x - 5.6, y0, vas_z_techo_608]) cube([11.2, y1 - y0, vas_z_rod + d / 2 - vas_z_techo_608]);
}
// Tope del tensor: prisma en x de vas_x_tope al borde de la corredera, pegado a la cara de afuera de la lateral
// (y = f, afuera hacia s), con el fondo a 45 (la lateral se imprime de pie: no vuela) y arriba en z 110.5.
module vas_tope_ten(f, s) translate([vas_x_tope, 0, 0]) rotate([90, 0, 90])
  linear_extrude(vas_x_ten[0] - vas_608[1] / 2 - tol - vas_x_tope)
    polygon([[f - s, vas_z_ten - 9.5], [f, vas_z_ten - 9.5], [f + 6 * s, vas_z_ten - 3.5], [f + 6 * s, vas_z_ten + 3.5], [f - s, vas_z_ten + 3.5]]);
// Rosca del prisionero del tensor, en (y, vas_z_ten) a lo largo de x hasta la corredera
module vas_rosca_ten(y) translate([vas_x_tope - 1, y, vas_z_ten]) rotate([0, 90, 0]) cylinder(d = vas_m3_rosca, h = vas_x_ten[0] - vas_x_tope + 1, $fn = 24);
// Lo que se saca de la corredera de la lateral -y junto al vaso de la canaleta (llega a x 387.2 y z 112.46 por fuera
// de la placa): por fuera, el buje de x 380 a 388.7 sobre z 111 (1.5 de luz). En la placa queda la lamina entre la
// muesca del vaso y la corredera (0.66 en z 112.5, se ensancha con el arco): de pie es lo que sostiene desde abajo el
// lado -x del techo de la corredera. 2026-10-25: cortada de z 112.5 a 115.5, el pedazo de arriba nacia en el aire
// (5.5 mm); cortada hasta z 120.5, nacia en el aire el anillo del buje de afuera (z 117.7) y el techo colgaba de un lado.
module vas_muesca_ten() translate([380, vas_ys[0] - 5, 111]) cube([8.7, 5, 25]);
// Poste del motor (separador): prisma en y de seccion "casa" invertida (cuadrado de 2a con fondo en V a 45):
// la lateral se imprime DE PIE y los postes quedan horizontales; con el fondo en V no hay cara hacia abajo.
module vas_poste_motor(p, a, y0) translate([p[0], y0, p[1]]) rotate([-90, 0, 0]) linear_extrude(vas_ys[0] - y0)
  polygon([[-a, -a], [a, -a], [a, a], [0, 2 * a], [-a, a]]);   // (z local = -y mundo; el vertice [0, 2a] queda ABAJO)
// Nervio bajo la punta de un poste (2026-10-25: de pie, la punta en V salia 32.8 de la placa sin nada abajo): placa de
// vas_nervio en el plano del poste, de la placa al extremo del poste, desde z0 (la cama para los postes de abajo, la cara
// de arriba del poste de abajo para los de arriba) hasta 2 adentro de la V (el hueco del poste empieza 4.8 mas arriba).
module vas_nervio_poste(p, a, y0, z0) translate([p[0] - vas_nervio / 2, y0, z0]) cube([vas_nervio, vas_ys[0] - y0, p[1] - 2 * a + 2 - z0]);
// Muescas por donde baja el vaso a los rieles de la canaleta (can_vasos[0], y -187.05, inclinado 15):
// lo que ocupa ese vaso en el bastidor (x 336.8..383.2, z >= 114.2; en la bancada hasta y -134.4) + 1.5.
// Atraviesan la pieza de punta a punta en la direccion de impresion: no dejan voladizo.
module vas_muesca_vaso_lat() translate([335, vas_ys[0] - 5, 112.5]) cube([49.7, 15, 20]);   // hasta x 384.7 (antes 385)
module vas_muesca_vaso_banc() translate([340, vas_banc_y[0] - 1, vas_banc_z[0] - 1]) cube([40, 8.1, 20]);

module vas_lat_n(x0, x1) difference() {
  union() {
    translate([x0, vas_yn[0], vas_z_lat[0]]) cube([x1 - x0, vas_e_lat, vas_z_lat[1] - vas_z_lat[0]]);
    for (x = vas_x_rod) if (x > x0 && x < x1) vas_buje_y(x > 0 ? vas_x_ten : [x], 2 * vas_r_buje, vas_yn[0], vas_yn[1] + 4);
    if (x1 > 400) vas_tope_ten(vas_yn[1], 1);
    // taco que llena el hueco hasta la cara -y del tubo (y -48.5, con 0.2 de holgura)
    for (x = vas_postes_n) if (x > x0 && x < x1) translate([x - 8, vas_yn[1], vas_z_lat[0]]) cube([16, 6.8, 36]);   // hasta z 108: 7 sobre el remache de z 101
  }
  for (x = vas_x_rod) if (x > x0 && x < x1) vas_ojal_y(x > 0 ? vas_x_ten : [x], vas_608[1] + 2 * tol, vas_yn[0] - 1, vas_yn[1] + 5);
  if (x1 > 400) vas_rosca_ten(vas_yn[1] + 1.5);
  vas_ventanas_lat(x0, x1, vas_yn, [for (x = vas_x_rem_banc_n) [x, 110]],
    concat([[-20, vas_r_buje + 3], [vas_x_tope - 3, 420]], [for (x = vas_postes_n) [x - 10, x + 10]]));
}

// Ventanas de las laterales (aligerado): rombos de 26 (lados a 45) centrados en z 91, paso 32, en la franja
// z 78..104: largueros de 6 (abajo) y 16 (arriba, ahi van los remaches de la bancada) y diagonales de >= 6.
// Se respetan 5 mm alrededor de cada remache (rem: [x, z]) y las zonas tapadas (tapa: [x0, x1]: bujes,
// motor y tacos de apoyo). La placa se imprime DE PIE (canto de 4 en la cama, con brim): las ventanas y
// todos los agujeros quedan horizontales, y el techo de cada rombo son dos caras a 45.
module vas_ventanas_lat(x0, x1, ys, rem, tapa) let(zc = 91, d = 13, L = 32)
  vas_en_y(ys[0] - 1, ys[1] + 1) difference() {
    intersection() {
      translate([x0 + 5, zc - d]) square([x1 - x0 - 10, 2 * d]);
      for (i = [0:ceil((x1 - x0) / L)]) let(a = x0 + L / 2 + i * L)
        polygon([[a - d, zc], [a, zc - d], [a + d, zc], [a, zc + d]]);
    }
    for (r = rem) translate(r) circle(r = rem_agujero / 2 + 5);
    for (t = tapa) translate([t[0], 0]) square([t[1] - t[0], 200]);
  }

// ----------------------------------------------------------------- bancada (se imprime boca abajo)
module vas_bancada(x0, x1) {
  ly = vas_banc_y[1] - vas_banc_y[0];
  h = vas_banc_z[1] - vas_banc_z[0];
  translate([x0, vas_banc_y[0], vas_banc_z[1] - vas_piel_banc]) cube([x1 - x0, ly, vas_piel_banc]);
  // bordes en y: 3 (los atraviesan los remaches a las laterales)
  for (y = [vas_banc_y[0], vas_banc_y[1] - vas_pared_banc]) translate([x0, y, vas_banc_z[0]]) cube([x1 - x0, vas_pared_banc, h]);
  // nervios interiores de 10 de alto (z 110..120): los bordes en y, que llevan los remaches, van enteros
  zn = vas_banc_z[1] - 10;
  for (x = [x0, x1 - vas_nervio]) translate([x, vas_banc_y[0], zn]) cube([vas_nervio, ly, 10]);
  translate([x0, vas_y - vas_nervio / 2, zn]) cube([x1 - x0, vas_nervio, 10]);
  for (x = vas_nervios_banc) if (x > x0 + 2 && x < x1 - 2) translate([x - vas_nervio / 2, vas_banc_y[0], zn]) cube([vas_nervio, ly, 10]);
}

// ----------------------------------------------------------------- placa del motor
module vas_placa_motor() difference() {
  translate([-34, vas_y_placa_motor[0], 88]) cube([68, 5, 46]);
  vas_gota_y([0, vas_z_rod], 22 + 2 * tol, vas_y_placa_motor[0] - 1, vas_y_placa_motor[1] + 1);   // paso del eje (con los separadores de 3 el centrador ya no llega)
  for (x = [-15.5, 15.5], z = [-15.5, 15.5]) vas_cil_y([x, vas_z_rod + z], 3.4, vas_y_placa_motor[0] - 1, vas_y_placa_motor[1] + 1);
}

// ----------------------------------------------------------------- media taco de casilla (marco local: pie del separador)
// Cara concava de R = base del vaso + 0.8 centrada a +-c = media casilla (39.79: abraza la base) solo del lado +y; del
// lado -y (la canaleta) es plana a c - R = 12.33 del separador (la casilla queda igual que con paso 80 y c 40), para
// que la paleta saque el vaso (2026-10-25: con el arco a los dos lados el vaso se trababa a los 0.5 mm de empujarlo).
// La cara plana del otro lado va pegada al
// separador (3 + 2 tol entre las dos mitades). lado = -1 (mitad "a", hacia -x local) o +1.
module vas_taco_local(lado) translate([0, 0, 0.1]) intersection() {
  R = vas_r_base_vaso + 0.8; w = 22; c = vas_paso_sep / 2;   // arcos centrados en la casilla (79.58)
  linear_extrude(10) polygon(concat([for (i = [0:14]) let(y = w - 2 * w * i / 14) [c - (y < 0 ? R : sqrt(R * R - y * y)), y]],
                                    [for (i = [0:14]) let(y = -w + 2 * w * i / 14) [-(c - (y < 0 ? R : sqrt(R * R - y * y))), y]]));
  translate([lado > 0 ? vas_sep[0] / 2 + tol : -50, -w - 1, -1]) cube([50 - vas_sep[0] / 2 - tol, 2 * w + 2, 12]);
}
module vas_en_taco(t) translate([t[0], t[1], t[2]]) rotate([0, t[3], 0]) children();

// ----------------------------------------------------------------- panel de luz (caja de luz)
// Marco de 1.6 (4 perimetros), salvo la pared de la union (e0 / e1 = 2.4: la atraviesan los remaches).
module vas_panel(x0, x1, e0 = vas_nervio, e1 = vas_nervio) {
  difference() {
    translate([x0, -60, 125]) cube([x1 - x0, 10, 97]);
    translate([x0 + e0, -58.4, 125 + vas_nervio]) cube([x1 - x0 - e0 - e1, 9, 97 - 2 * vas_nervio]);
  }
  // chaflan a 45 bajo el marco de arriba: de pie, el marco colgaba 8,4 de la pared de atras en todo el largo (voladizo).
  // Sube hasta z 222 (dentro del marco): con la cara de arriba justo en 220.4 la union dejaba la cara de abajo del marco
  // adentro de la malla y seguia contando como colgada (1267.6 mm2)
  translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(x1 - x0)
    polygon([[-58.5, 222 - vas_nervio - 8.5], [-50, 222 - vas_nervio], [-50, 222], [-58.5, 222]]);
}

// ----------------------------------------------------------------- placa de la camara de vasos
module vas_placa_camara() difference() {
  union() {
    translate([149.4, -432.6, 160]) cube([21.2, 21.2, 29]);                         // collar (punta del poste: z 190)
    hull() {
      translate([149.4, -413.8, 160]) cube([21.2, 2.4, 29]);
      vas_marco_cam() translate([-16, -9, -21 - 0.2 - 4]) cube([32, 19, 4]);         // repisa bajo la webcam
    }
  }
  translate([160 - 8.2, -422 - 8.2, 150]) cube([16.4, 16.4, 50]);
  vas_marco_cam() translate([0, 0, -70]) cylinder(d = vas_cam_tornillo, h = 50);
}

// ----------------------------------------------------------------- cortina VL53L0X (prisma en x: se imprime acostada)
// Llega solo hasta x 320 (x 317 sobre z 175): por x >= 321 baja la pestaña del vaso por la canaleta (can_vaso).
module vas_cortina() difference() {
  vas_cortina_prisma();
  translate([317, -210, 175]) cube([10, 50, 30]);
}
module vas_cortina_prisma() translate([301.8, 0, 0]) rotate([90, 0, 90]) linear_extrude(320 - 301.8) union() {
  translate([-163.7, 86]) square([3, 32]);          // brida a la cara -y del tubo (315,-152.5)
  translate([-199.5, 86]) square([36, 10]);         // brazo
  translate([-199.5, 86]) square([8.5, 109]);       // poste
  translate([-199.5, 179]) square([27, 16]);        // escuadra: la placa GY-530 apoya en x 301.8
}

// ----------------------------------------------------------------- bandeja de rechazo con labio
vas_band = [95.8, 115.8, 60];
module vas_bandeja() {
  x0 = vas_bandeja_c[0] - vas_band[0] / 2; y0 = vas_bandeja_c[1] - vas_band[1] / 2;
  e = vas_nervio;   // paredes y piso de 1.6: no carga mas que los vasos rechazados
  difference() {
    translate([x0, y0, 0]) cube(vas_band);
    translate([x0 + e, y0 + e, e]) cube([vas_band[0] - 2 * e, vas_band[1] - 2 * e, vas_band[2]]);
    // ventanas en rombo (lados a 45: sin puentes) en las paredes y, +x; por un rombo de 27 no pasa un vaso (Ø62)
    for (x = [440, 470, 500]) translate([x, vas_y, 30]) rotate([90, 45, 0]) cube([19, 19, 300], center = true);
    for (y = [-130, -100, -70]) translate([x0 + vas_band[0], y, 30]) rotate([45, 0, 0]) cube([10, 19, 19], center = true);
  }
  // labio: rampa a -0.9 rad por (450, -100, 78) (visor). Sin mejillas: la rampa crece al imprimir desde su
  // pared de apoyo (x 465.5) con 38 grados desde la vertical, y el chaflan a 37 desde la pared -x. El chaflan
  // baja a z 81 en la pared (antes 85.2, a 45): con el eje del rodillo en z 109 la punta +y de los tacos pasa a
  // r 33.0 del eje x 400 y lo rozaba 0.3 mm; ahora queda a 34.5 (la rampa no se mueve).
  perfil = [[x0, 0], [465.5, 0], [465.5, 58.4], [434.5, 97.6], [x0, 81]];
  difference() {
    vas_en_y(-137.5, -62.5) polygon(perfil);
    vas_en_y(-140, -60) offset(delta = -e) polygon(perfil);
  }
}

// ----------------------------------------------------------------- una pieza en su lugar
module vas_pieza(n) {
  if (n == "vas_lat_s_a") vas_lat_s(-36, vas_x_union_lat - 0.1);
  else if (n == "vas_lat_s_b") vas_lat_s(vas_x_union_lat + 0.1, 415);
  else if (n == "vas_lat_n_a") vas_lat_n(-15, vas_x_union_lat - 0.1);
  else if (n == "vas_lat_n_b") vas_lat_n(vas_x_union_lat + 0.1, 415);
  else if (n == "vas_bancada_a") vas_bancada(vas_banc_x[0], vas_x_union_banc - 0.1);
  else if (n == "vas_bancada_b") difference() { vas_bancada(vas_x_union_banc + 0.1, vas_banc_x[1]); vas_muesca_vaso_banc(); }
  else if (n == "vas_placa_motor") vas_placa_motor();
  else if (n == "vas_panel_a") {
    vas_panel(-5, vas_x_union_banc - 0.1, vas_nervio, 2.4);
    // oreja maciza sobre la columna x -50 (z 140..175) con la cara de abajo a 37 grados hasta el frente (de pie no vuela)
    translate([-58, 0, 0]) rotate([90, 0, 90]) linear_extrude(16) polygon([[-60, 125], [-48.7, 140], [-48.7, 175], [-60, 175]]);
    translate([-42.1, -60, 125]) cube([38.2, vas_nervio, 50]);           // brazo: placa de 1.6 que apoya en la cama
  }
  else if (n == "vas_panel_b") difference() {
    union() {
      vas_panel(vas_x_union_banc + 0.1, 305, 2.4, vas_nervio);
      // oreja sobre la columna x 315 (z 143..178): por debajo baja a 45 hasta el canto de la caja (x 305, z 125)
      vas_en_y(-60, -48.7) polygon([[304, 125], [305, 125], [323, 143], [323, 178], [304, 178]]);
    }
    translate([315 - 10.8, -51.3, 205.3 - 24.2]) cube([30, 30, 48.4]);   // muesca para el empalme e_F5-P2_1
  }
  else if (n == "vas_placa_camara") vas_placa_camara();
  else if (n == "vas_cortina") vas_cortina();
  else if (n == "vas_bandeja") vas_bandeja();
  else for (i = [1:len(VAS_TACOS)], m = ["a", "b"]) if (n == str("vas_taco_", i, "_", m))
    vas_en_taco(VAS_TACOS[i - 1]) vas_taco_local(m == "a" ? -1 : 1);
}

// ----------------------------------------------------------------- orientacion de impresion
module vas_a_cama(n) {
  // Primera capa (CONVENCIONES.md): la cara de la cama es maciza. Laterales, placa del motor y paneles van DE PIE sobre
  // su canto de abajo (como estan en el mundo): todos sus agujeros quedan horizontales. Las paredes altas llevan brim
  // propio (primera_capa.BRIM_OBJETO). Acostados, los paneles sumaban 2 circulos chicos en la cama y de pie ya eran
  // estables (0,007 MPa de despegue con 0,2 N en la punta, auditoria 2026-10-25).
  if (n == "vas_bancada_a" || n == "vas_bancada_b") rotate([180, 0, 0]) children();  // boca abajo: piel maciza en la cama
  else if (n == "vas_cortina") rotate([0, -90, 0]) children();                          // acostada, cara x 301.8 en la cama
  else rotate([0, -vas_giro_taco(n), 0]) children();   // los tacos de abajo (giro 180), boca arriba como los de arriba
}
function vas_giro_taco(n) = let(g = [for (i = [1:len(VAS_TACOS)], m = ["a", "b"]) if (n == str("vas_taco_", i, "_", m)) VAS_TACOS[i - 1][3]])
  len(g) ? g[0] : 0;

// ----------------------------------------------------------------- lo que se mueve: envolvente del lazo
// Separadores (15 sobre la banda, 75 de ancho) alrededor de todo el lazo: estadio de r 11 + 2 + 15.
// Tacos (10 de alto, +-23.4 a lo largo, 44 de ancho), los 11 en cualquier punto del lazo: al dar la vuelta al rodillo
// sus esquinas llegan a r = hypot(23.1, 23.4) = 32.9 del eje. Se resta el interior del lazo (banda, bancada y rodillos).
module vas_barrido(n) if (n == "vas_vuelta_banda") difference() {
  union() {
    vas_en_y(-100 - vas_ancho_banda / 2 + vas_recorte_sep, -100 + vas_ancho_banda / 2)
      hull() for (x = vas_x_rod) translate([x, vas_z_rod]) circle(r = vas_d_rod / 2 + vas_e_banda + vas_sep[2], $fn = 72);
    vas_en_y(-122, -78) for (x = vas_x_rod) translate([x, vas_z_rod]) circle(r = 33.1, $fn = 72);
  }
  vas_en_y(-140, -60) hull() for (x = vas_x_rod) translate([x, vas_z_rod]) circle(r = vas_d_rod / 2 + vas_e_banda + 0.05, $fn = 72);
}
// Vaso de pie (comprado, como can_vaso_en: Ø62 x 90, base r vas_r_base_vaso, pestana Ø78 x 1 en la boca, z 211)
// de x 0 a 360, y desde x 200 con la tapa sin prensar (ala Ø78 de z 213.5 a 217 y el tapon que asoma sobre la
// boca: se dibuja un disco de z 212 a 217). Cada parte con su hull: el hull del conjunto rellenaria de mas.
else if (n == "vas_vaso") {
  hull() for (x = [0, 360]) translate([x, vas_y, vas_z_banda]) cylinder(r1 = vas_r_base_vaso, r2 = 31, h = 89, $fn = 96);
  hull() for (x = [0, 360]) translate([x, vas_y, vas_z_banda + 89]) cylinder(r = 39, h = 1, $fn = 96);
  hull() for (x = [200, 360]) translate([x, vas_y, vas_z_banda + 90]) cylinder(r = 39, h = 5, $fn = 96);
}

// ----------------------------------------------------------------- mecanismos fase por fase (revisar.py)
// vas_descarga: lado 0 = los medios tacos de la casilla de x 360; lado 1 = el vaso corrido de y -100 a -154.6.
module vas_fase(n, k, lado) if (n == "vas_descarga") {
  if (lado == 0) { vas_pieza("vas_taco_5_b"); vas_pieza("vas_taco_6_a"); }
  else hull() for (y = [vas_y, vas_y - 54.6]) translate([360, y, vas_z_banda]) cylinder(r1 = vas_r_base_vaso, r2 = 31, h = 89, $fn = 120);
}

// ----------------------------------------------------------------- comprado (forma aproximada, entra en los choques)
// Los separadores no van aqui: los cubre el barrido (se mueven con la banda).
module vas_comprados() {
  // banda: lazo de 2 mm que envuelve los rodillos (cara de arriba a z 122, de abajo en la vuelta a z 96)
  vas_en_y(vas_y - vas_ancho_banda / 2, vas_y + vas_ancho_banda / 2) difference() {
    hull() for (x = vas_x_rod) translate([x, vas_z_rod]) circle(r = vas_d_rod / 2 + vas_e_banda, $fn = 60);
    hull() for (x = vas_x_rod) translate([x, vas_z_rod]) circle(r = vas_d_rod / 2, $fn = 60);
  }
  // rodillos Ø22 x 79 y ejes Ø8
  for (x = vas_x_rod) vas_cil_y([x, vas_z_rod], vas_d_rod, -139.5, -60.5);
  vas_cil_y([400, vas_z_rod], 8, -149, -51.5);
  vas_cil_y([0, vas_z_rod], 8, -160.5, -51.5);     // cortado a 109: entra 9 en el acople y queda a 1 del eje del motor
  // 608: lateral -y en x 400; lateral +y en x 0 y x 400
  vas_cil_y([400, vas_z_rod], vas_608[1], vas_ys[1] - vas_608[2], vas_ys[1]);
  for (x = vas_x_rod) vas_cil_y([x, vas_z_rod], vas_608[1], vas_yn[0], vas_yn[0] + vas_608[2]);
  // KFL08 (brida 48 x 14) en la cara de afuera de la lateral -y, acople Ø19 x 20
  translate([-7, -147.5, vas_z_rod - 24]) cube([14, 2.9, 48]);   // brida vertical: sus tornillos a vas_z_rod +-18
  vas_cil_y([0, vas_z_rod], 20, -151.5, -146.5);
  vas_cil_y([0, vas_z_rod], 19, -171.5, -151.5);
  // NEMA 17 con la cara en y -185.5 (separadores de nailon de 3 entre la placa y el motor; cuerpo hacia -y),
  // centrador Ø22 x 2 (ya no entra en la placa: queda a 1 de ella), eje Ø5 x 24 desde la cara (punta en y -161.5,
  // el medio del acople: entra 10)
  translate([-vas_nema / 2, -225.5, vas_z_rod - vas_nema / 2]) cube([vas_nema, 39.9, vas_nema]);
  vas_cil_y([0, vas_z_rod], 22, -185.6, -183.5);
  vas_cil_y([0, vas_z_rod], 5, -183.5, -161.5);
  // webcam 720p 42 x 42 x 20 (mira a +y, inclinada hacia la cinta) con su objetivo
  vas_marco_cam() { translate([-21, -10, -21]) cube([42, 20, 42]); translate([0, 10, 0]) rotate([-90, 0, 0]) cylinder(d = 14, h = 4); }
  // VL53L0X (GY-530) de la cortina: placa en x 300..301.6, sensor hacia -x
  translate([300, vas_cortina[1] - vas_gy530[0] / 2, vas_cortina[2] - vas_gy530[1] / 2]) cube([vas_gy530[2], vas_gy530[0], vas_gy530[1]]);
  translate([299, vas_cortina[1] - 2.5, vas_cortina[2] - 1.5]) cube([1, 5, 3]);
  // tira LED (dos tramos, uno por mitad del panel), en el fondo de la caja de luz
  for (x = [[-2.5, 147.4], [152.6, 302.5]]) translate([x[0], -58.2, 127.5]) cube([x[1] - x[0], vas_led[0], vas_led[1]]);
}
