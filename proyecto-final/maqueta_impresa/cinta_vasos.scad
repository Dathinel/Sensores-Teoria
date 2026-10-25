// =====================================================================================
// Subsistema "cinta_vasos" (prefijo vas_): cinta de vasos impresa en PLA (ver CONVENCIONES.md).
// Lo incluye maqueta.scad; este archivo NO hace include de nada.
//
// Lo funcional (inventario_maqueta.md §5, §9, §10, §18) NO se movio:
//   estaciones x 40/120/200/280/360 en y -100, superficie de la banda z 122, rodillos Ø22 con eje en
//   x 0 y x 400 a z 111, camara de vasos (160,-400,211.77) mirando a (160,-100,173.97), cortina VL53L0X
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
//                   el buje del 608 de x 400.
//   vas_lat_n_a/b   placa lateral +y, partida en x 200, con los bujes de los dos 608 y los tacos a los tubos.
//   vas_bancada_a/b bancada (cama de la banda): piel de 4 mm arriba y nervios; va DENTRO del lazo de la
//                   banda (la vuelta pasa por debajo, z 100..102) y se remacha a las 4 laterales (partida
//                   en x 150, desfasada de la union de las laterales: la bancada b hace de cubrejunta).
//   vas_placa_motor placa del NEMA 17, remachada a los 4 postes de vas_lat_s_a.
//   vas_taco_i_a/b  tacos de casilla (7 x 2 mitades): una mitad pegada a cada cara del separador (con tol).
//                   Sin grapa por encima: asi lo mas alto que recorre la banda es el separador (z 137) y no
//                   entra en la zona de la paleta del empujador (z 138).
//   vas_panel_a/b   panel de luz: caja de luz de PLA blanco (frente de 1.6 = difusor, marco de 2.4, atras
//                   abierto para la tira LED), partida en x 150 y remachada; cada mitad con una oreja a la
//                   cara -y de su columna del portico (x -50 y x 315).
//   vas_placa_camara collar sobre la punta del poste (160,-422) con la repisa inclinada de la webcam.
//   vas_cortina     brida + brazo + poste + escuadra del VL53L0X, remachada a la cara -y del tubo (315,-152.5).
//   vas_bandeja     bandeja de rechazo con el labio (rampa) integrado.
// Lo que se mueve: MOVILES_VAS / vas_barrido = envolvente de banda + separadores + tacos en todo el lazo.
// =====================================================================================

// ----------------------------------------------------------------- funcional (no se mueve)
vas_y = -100;                 // eje de la cinta
vas_z_banda = 122;            // superficie de la banda
vas_e_banda = 2;              // espesor de la banda
vas_x_rod = [0, 400];         // ejes de los rodillos
vas_z_rod = 111;
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
vas_banc_x = [13, 387];
vas_banc_z = [104, 119.9];    // abajo: 2 mm sobre la vuelta de la banda; arriba: 0.1 bajo la banda
vas_banc_y = [vas_ys[1] + tol, vas_yn[0] - tol];
vas_pared_banc = 3;
vas_r_buje = 13.5;            // buje del 608 (Ø22.4 + 2 x 2.3)
vas_x_rem_banc_s = [60, 120, 175, 230, 280];        // remaches laterales <-> bancada, a z 110 (en x 355 el
                                                    // vaso de la canaleta no deja meterlo desde -y)
vas_x_rem_banc_n = [45, 120, 175, 230, 280, 355];
vas_nervios_banc = [40, 90, 202, 255, 318, 345];   // a >= 5 mm de cada remache (la una abre en la celda)
vas_piel_banc = 2;            // piel de arriba de la bancada (con nervios cada <= 70 en x y 40 en y)
vas_nervio = 1.6;             // nervios y paredes que no llevan remaches (4 perimetros)
// apoyos en la estructura: tubos verticales con punta a z 120
vas_postes_s = [40, 315];     // x de los tubos del lado -y (y -152.5, cara +y en y -144.5)
vas_postes_n = [30, 315];     // x de los tubos del lado +y (y -40.5, cara -y en y -48.5)
vas_z_rem_poste = [80, 94];
// motor
vas_postes = [[-25, 96], [-25, 126], [25, 96], [25, 126]];   // (x, z) de los 4 separadores
vas_y_placa_motor = [-178.5, -173.5];

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
// 6 arriba (x 0..400, uno por separador) y el 7.o en la vuelta de abajo (cara de afuera a z 100), boca abajo.
VAS_TACOS = concat([for (i = [0:5]) [i * vas_paso, vas_y, vas_z_banda, 0]], [[200, vas_y, vas_z_rod - vas_d_rod / 2, 180]]);
VAS_N_TACOS = [for (i = [1:7], m = ["a", "b"]) str("vas_taco_", i, "_", m)];

// ----------------------------------------------------------------- piezas
PIEZAS_VAS = concat(["vas_lat_s_a", "vas_lat_s_b", "vas_lat_n_a", "vas_lat_n_b", "vas_bancada_a", "vas_bancada_b",
  "vas_placa_motor"], VAS_N_TACOS,
  ["vas_panel_a", "vas_panel_b", "vas_placa_camara", "vas_cortina", "vas_bandeja"]);

// lo que se mueve: el lazo de la banda (los tacos van con ella)
// (lista escrita entera: moviles_por_defecto.scad ya asigna MOVILES_VAS y OpenSCAD evalua la reasignacion
// en el lugar de la primera, donde VAS_N_TACOS todavia no existe)
// tap_emp_paleta: el empujador solo se mueve con la cinta parada (descarga), nunca a la vez que la banda
MOVILES_VAS = [["vas_vuelta_banda", concat([for (i = [1:7], m = ["a", "b"]) str("vas_taco_", i, "_", m)], ["tap_emp_paleta"])]];

// ----------------------------------------------------------------- remaches [nombre, agarre, cabeza, eje]
// agarre = suma de lo que atraviesa (+0.2 por holgura); la una abre al aire o al hueco de un tubo.
REM_VAS = concat(
  // laterales <-> bancada: lateral 4 + 0.2 + pared de la bancada 3; la una abre en una celda de la bancada
  [for (x = vas_x_rem_banc_s) [str("r_vas_banc_s_", x), 7.2, [x, vas_ys[0], 110], [0, 1, 0]]],
  [for (x = vas_x_rem_banc_n) [str("r_vas_banc_n_", x), 7.2, [x, vas_yn[1], 110], [0, -1, 0]]],
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
  // placa de la camara <-> poste: collar 2.4 + 0.2 + pared 1.6
  [["r_vas_cam_x1", 4.2, [170.6, -422, 172], [-1, 0, 0]], ["r_vas_cam_x0", 4.2, [149.4, -422, 180], [1, 0, 0]]]
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
      for (p = vas_postes) translate([p[0] - 6, -173.3, p[1] - 6]) cube([12, 173.3 + vas_ys[0], 12]);
    }
    if (x1 > 400) vas_cil_y([400, vas_z_rod], 2 * vas_r_buje, vas_ys[0] - 4, vas_ys[1]);
  }
  if (x0 < 0) {
    vas_cil_y([0, vas_z_rod], 12, vas_ys[0] - 1, vas_ys[1] + 1);                       // paso del eje motriz
    for (x = [-18, 18]) vas_cil_y([x, vas_z_rod], 5.5, vas_ys[0] - 1, vas_ys[1] + 1);  // tornillos del KFL08
    for (p = vas_postes) translate([p[0] - 3.6, -171.3, p[1] - 3.6]) cube([7.2, 171.3 + vas_ys[0], 7.2]);  // tapa de 2
  }
  if (x1 > 400) vas_cil_y([400, vas_z_rod], vas_608[1] + 2 * tol, vas_ys[0] - 5, vas_ys[1] + 1);
  if (x1 > 400) vas_muesca_vaso_lat();
  vas_ventanas_lat(x0, x1, vas_ys,
    concat([for (x = vas_x_rem_banc_s) [x, 110]], [for (x = vas_postes_s, z = vas_z_rem_poste) [x, z]]),
    concat([[-40, 34]], x1 > 400 ? [[400 - vas_r_buje - 3, 415]] : []));
}
// Muescas por donde baja el vaso a los rieles de la canaleta (can_vasos[0], y -187.05, inclinado 15):
// lo que ocupa ese vaso en el bastidor (x 336.8..383.2, z >= 114.2; en la bancada hasta y -134.4) + 1.5.
// Atraviesan la pieza de punta a punta en la direccion de impresion: no dejan voladizo.
module vas_muesca_vaso_lat() translate([335, vas_ys[0] - 5, 112.5]) cube([50, 15, 20]);
module vas_muesca_vaso_banc() translate([340, vas_banc_y[0] - 1, vas_banc_z[0] - 1]) cube([40, 8.1, 20]);

module vas_lat_n(x0, x1) difference() {
  union() {
    translate([x0, vas_yn[0], vas_z_lat[0]]) cube([x1 - x0, vas_e_lat, vas_z_lat[1] - vas_z_lat[0]]);
    for (x = vas_x_rod) if (x > x0 && x < x1) vas_cil_y([x, vas_z_rod], 2 * vas_r_buje, vas_yn[0], vas_yn[1] + 4);
    // taco que llena el hueco hasta la cara -y del tubo (y -48.5, con 0.2 de holgura)
    for (x = vas_postes_n) if (x > x0 && x < x1) translate([x - 8, vas_yn[1], vas_z_lat[0]]) cube([16, 6.8, 30]);
  }
  for (x = vas_x_rod) if (x > x0 && x < x1) vas_cil_y([x, vas_z_rod], vas_608[1] + 2 * tol, vas_yn[0] - 1, vas_yn[1] + 5);
  vas_ventanas_lat(x0, x1, vas_yn, [for (x = vas_x_rem_banc_n) [x, 110]],
    concat([[-20, vas_r_buje + 3], [400 - vas_r_buje - 3, 420]], [for (x = vas_postes_n) [x - 10, x + 10]]));
}

// Ventanas de las laterales (aligerado): cercha de triangulos alternados en la franja z 77..105, con
// largueros de 5 (abajo) y 15 (arriba, ahi van los remaches de la bancada) y diagonales de 5. Se
// respetan 5 mm alrededor de cada remache (rem: [x, z]) y las zonas tapadas (tapa: [x0, x1]: bujes,
// postes del motor y tacos de apoyo). La placa se imprime acostada: las ventanas quedan verticales.
module vas_ventanas_lat(x0, x1, ys, rem, tapa) let(zb = 77, zt = 105, L = 36)
  vas_en_y(ys[0] - 1, ys[1] + 1) difference() {
    intersection() {
      translate([x0 + 5, zb]) square([x1 - x0 - 10, zt - zb]);
      for (i = [0:ceil((x1 - x0) / (L / 2))]) let(a = x0 + i * L / 2 - L / 2) offset(delta = -2.5)
        polygon(i % 2 == 0 ? [[a, zb], [a + L, zb], [a + L / 2, zt]] : [[a, zt], [a + L, zt], [a + L / 2, zb]]);
    }
    for (r = rem) translate(r) circle(r = rem_agujero / 2 + 5);
    for (t = tapa) translate([t[0], 0]) square([t[1] - t[0], 200]);
  }

// ----------------------------------------------------------------- bancada (se imprime boca abajo)
module vas_bancada(x0, x1) {
  ly = vas_banc_y[1] - vas_banc_y[0];
  h = vas_banc_z[1] - vas_banc_z[0];
  // piel con agujeros de Ø10 (paso 20 en x; con Ø14 un vaso lleno de ~300 g marcaria la banda de 2 mm): la banda de 2 mm sigue apoyada en una rejilla plana; se saltan
  // los que caen a < 9 de un nervio y los de la muesca del vaso (x 331..389, fila y -127)
  difference() {
    translate([x0, vas_banc_y[0], vas_banc_z[1] - vas_piel_banc]) cube([x1 - x0, ly, vas_piel_banc]);
    for (x = [x0 + 10 : 20 : x1 - 9], y = [-127, -111, -89, -73])
      if (min([for (xr = vas_nervios_banc) abs(x - xr)]) >= 9 && !(y == -127 && x > 331 && x < 389))
        translate([x, y, vas_banc_z[1] - vas_piel_banc - 1]) cylinder(d = 10, h = vas_piel_banc + 2, $fn = 24);
  }
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
  vas_cil_y([0, vas_z_rod], 22 + 2 * tol, vas_y_placa_motor[0] - 1, vas_y_placa_motor[1] + 1);   // centrador del NEMA
  for (x = [-15.5, 15.5], z = [-15.5, 15.5]) vas_cil_y([x, vas_z_rod + z], 3.4, vas_y_placa_motor[0] - 1, vas_y_placa_motor[1] + 1);
}

// ----------------------------------------------------------------- media taco de casilla (marco local: pie del separador)
// Cara concava de R = base del vaso + 0.8 centrada a +-40 (abraza la base de la casilla); la cara plana
// va pegada al separador (3 + 2 tol entre las dos mitades). lado = -1 (mitad "a", hacia -x local) o +1.
module vas_taco_local(lado) translate([0, 0, 0.1]) intersection() {
  R = vas_r_base_vaso + 0.8; w = 22; c = vas_paso / 2;
  linear_extrude(10) polygon(concat([for (i = [0:14]) let(y = w - 2 * w * i / 14) [c - sqrt(R * R - y * y), y]],
                                    [for (i = [0:14]) let(y = -w + 2 * w * i / 14) [-(c - sqrt(R * R - y * y)), y]]));
  translate([lado > 0 ? vas_sep[0] / 2 + tol : -50, -w - 1, -1]) cube([50 - vas_sep[0] / 2 - tol, 2 * w + 2, 12]);
}
module vas_en_taco(t) translate([t[0], t[1], t[2]]) rotate([0, t[3], 0]) children();

// ----------------------------------------------------------------- panel de luz (caja de luz)
// Marco de 1.6 (4 perimetros), salvo la pared de la union (e0 / e1 = 2.4: la atraviesan los remaches).
module vas_panel(x0, x1, e0 = vas_nervio, e1 = vas_nervio) difference() {
  translate([x0, -60, 125]) cube([x1 - x0, 10, 97]);
  translate([x0 + e0, -58.4, 125 + vas_nervio]) cube([x1 - x0 - e0 - e1, 9, 97 - 2 * vas_nervio]);
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
    // agujeros de Ø24 en el piso (la base del vaso es Ø53: no cae)
    for (x = [478, 502], y = [-140, -114, -86, -60]) translate([x, y, -1]) cylinder(d = 24, h = e + 2);
  }
  // labio: rampa a -0.9 rad por (450, -100, 78) (visor). Sin mejillas: la rampa crece al imprimir desde su
  // pared de apoyo (x 465.5) con 38 grados desde la vertical, y el chaflan a 45 desde la pared -x.
  perfil = [[x0, 0], [465.5, 0], [465.5, 58.4], [434.5, 97.6], [x0, 85.2]];
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
    translate([-58, -60, 140]) cube([16, 11.3, 35]);                     // oreja maciza sobre la columna x -50
    // brazo hasta la caja: canal abierto hacia atras (frente de 1.6 y alas de 1.6; al imprimir abre hacia arriba)
    translate([-42.1, -60, 140]) cube([38.2, vas_nervio, 35]);
    for (z = [140, 175 - vas_nervio]) translate([-42.1, -60, z]) cube([38.2, 11.3, vas_nervio]);
  }
  else if (n == "vas_panel_b") difference() {
    union() { vas_panel(vas_x_union_banc + 0.1, 305, 2.4, vas_nervio); translate([304, -60, 140]) cube([19, 11.3, 35]); }
    translate([315 - 10.8, -51.3, 205.3 - 24.2]) cube([30, 30, 48.4]);   // muesca para el empalme e_F5-P2_1
  }
  else if (n == "vas_placa_camara") vas_placa_camara();
  else if (n == "vas_cortina") vas_cortina();
  else if (n == "vas_bandeja") vas_bandeja();
  else for (i = [1:7], m = ["a", "b"]) if (n == str("vas_taco_", i, "_", m))
    vas_en_taco(VAS_TACOS[i - 1]) vas_taco_local(m == "a" ? -1 : 1);
}

// ----------------------------------------------------------------- orientacion de impresion
module vas_a_cama(n) {
  if (n == "vas_lat_s_a" || n == "vas_lat_s_b") rotate([-90, 0, 0]) children();     // cara de adentro en la cama
  else if (n == "vas_lat_n_a" || n == "vas_lat_n_b" || n == "vas_placa_motor" || n == "vas_panel_a" || n == "vas_panel_b")
    rotate([90, 0, 0]) children();                                                     // lateral +y adentro abajo; panel de frente
  else if (n == "vas_bancada_a" || n == "vas_bancada_b") rotate([180, 0, 0]) children();  // boca abajo
  else if (n == "vas_cortina") rotate([0, -90, 0]) children();                          // acostada, cara x 301.8 en la cama
  else if (n == "vas_taco_7_a" || n == "vas_taco_7_b") rotate([0, 180, 0]) children();
  else children();
}

// ----------------------------------------------------------------- lo que se mueve: envolvente del lazo
// Separadores (15 sobre la banda, 75 de ancho) alrededor de todo el lazo: estadio de r 11 + 15.
// Tacos (10 de alto, +-23.6 a lo largo, 44 de ancho): al dar la vuelta al rodillo sus esquinas llegan a
// r = hypot(21.1, 23.6) = 31.7 del eje. Se resta el interior del lazo (banda, bancada y rodillos).
module vas_barrido(n) if (n == "vas_vuelta_banda") difference() {
  union() {
    vas_en_y(-100 - vas_ancho_banda / 2 + vas_recorte_sep, -100 + vas_ancho_banda / 2)
      hull() for (x = vas_x_rod) translate([x, vas_z_rod]) circle(r = vas_d_rod / 2 + vas_sep[2], $fn = 72);
    vas_en_y(-122, -78) for (x = vas_x_rod) translate([x, vas_z_rod]) circle(r = 31.8, $fn = 72);
  }
  vas_en_y(-140, -60) hull() for (x = vas_x_rod) translate([x, vas_z_rod]) circle(r = vas_d_rod / 2 + 0.05, $fn = 72);
}

// ----------------------------------------------------------------- comprado (forma aproximada, entra en los choques)
// Los separadores no van aqui: los cubre el barrido (se mueven con la banda).
module vas_comprados() {
  // banda: lazo de 2 mm cuya cara de arriba queda a z 122 (ver el informe: con rodillo Ø22 a z 111 no cierra)
  vas_en_y(vas_y - vas_ancho_banda / 2, vas_y + vas_ancho_banda / 2) difference() {
    hull() for (x = vas_x_rod) translate([x, vas_z_rod]) circle(r = vas_d_rod / 2, $fn = 60);
    hull() for (x = vas_x_rod) translate([x, vas_z_rod]) circle(r = vas_d_rod / 2 - vas_e_banda, $fn = 60);
  }
  // rodillos Ø22 x 79 y ejes Ø8
  for (x = vas_x_rod) vas_cil_y([x, vas_z_rod], vas_d_rod, -139.5, -60.5);
  vas_cil_y([400, vas_z_rod], 8, -149, -51.5);
  vas_cil_y([0, vas_z_rod], 8, -160, -51.5);
  // 608: lateral -y en x 400; lateral +y en x 0 y x 400
  vas_cil_y([400, vas_z_rod], vas_608[1], vas_ys[1] - vas_608[2], vas_ys[1]);
  for (x = vas_x_rod) vas_cil_y([x, vas_z_rod], vas_608[1], vas_yn[0], vas_yn[0] + vas_608[2]);
  // KFL08 (brida 48 x 14) en la cara de afuera de la lateral -y, acople Ø19 x 20
  translate([-24, -147.5, 104]) cube([48, 2.9, 14]);
  vas_cil_y([0, vas_z_rod], 20, -151.5, -146.5);
  vas_cil_y([0, vas_z_rod], 19, -171.5, -151.5);
  // NEMA 17 con la cara en y -178.5 (cuerpo hacia -y), centrador Ø22 x 2, eje Ø5 x 24
  translate([-vas_nema / 2, -218.5, vas_z_rod - vas_nema / 2]) cube([vas_nema, 39.9, vas_nema]);
  vas_cil_y([0, vas_z_rod], 22, -178.6, -176.5);
  vas_cil_y([0, vas_z_rod], 5, -176.5, -154.5);
  // webcam 720p 42 x 42 x 20 (mira a +y, inclinada hacia la cinta) con su objetivo
  vas_marco_cam() { translate([-21, -10, -21]) cube([42, 20, 42]); translate([0, 10, 0]) rotate([-90, 0, 0]) cylinder(d = 14, h = 4); }
  // VL53L0X (GY-530) de la cortina: placa en x 300..301.6, sensor hacia -x
  translate([300, vas_cortina[1] - vas_gy530[0] / 2, vas_cortina[2] - vas_gy530[1] / 2]) cube([vas_gy530[2], vas_gy530[0], vas_gy530[1]]);
  translate([299, vas_cortina[1] - 2.5, vas_cortina[2] - 1.5]) cube([1, 5, 3]);
  // tira LED (dos tramos, uno por mitad del panel), en el fondo de la caja de luz
  for (x = [[-2.5, 147.4], [152.6, 302.5]]) translate([x[0], -58.2, 127.5]) cube([x[1] - x[0], vas_led[0], vas_led[1]]);
}
