// =====================================================================================
// Subsistema "cinta_monedas" (prefijo mon_): todo lo que va sobre la mesa de monedas impresa (los dos rieles
// de tubo 16 x 16 con eje en y = +-40.5, z = 440), la compuerta E4 y los canales. Ver CONVENCIONES.md.
// Lo incluye maqueta.scad (este archivo no hace include de nada). Marco del mundo en mm, z = 0 el piso.
//
// FUNCIONAL (no se mueve, inventario_maqueta.md §1-3, §18): estaciones E1..E4 en x -50, -10, 30, 70 (paso 40),
// superficie de la banda z 452 (bancada hasta z 450 + banda de 2), rodillos motriz x -110 y tensor x 90 con eje
// en z 441, retorno A (-113, 344), B (11, 344), C (65, 418.8), cara activa de los M18 a z 449.5, rayo del FC-51
// desde (-50, 0, 502), vidrio de la webcam en (30, 0, 602), embudo E4 en x 105 (boca z 446 Ø40, salida z 420
// Ø20), pivote de la aleta (105, 0, 418), SG90 en x 138, bocas de los canales en z ~400.
//
// Piezas (todas PLA):
//   mon_bancada         placa entre los rieles con las ventanas de E1/E2; pestanas sobre los rieles (impresa boca abajo)
//   mon_guia_m/_p       guias laterales de la banda (L: pared + pata que va sobre la pestana de la bancada)
//   mon_platina_e1/_e2  platinas de los M18 (Ø18.5) remachadas bajo la bancada
//   mon_rod_mot_m       bloque del 608 del rodillo motriz, lado -y (labio bajo el riel)
//   mon_jaula_nema      bloque del 608 motriz +y + jaula en U del NEMA 17 (una sola pieza)
//   mon_rod_ten_m/_p    bloques de los 608 del tensor (labio SOBRE el riel, que sigue mas alla de la punta
//                       y sostiene la compuerta)
//   mon_ret_{a,b,c}_{m,p}  placas colgantes de los rodillos de retorno, remachadas a la cara interior de los rieles
//   mon_fc51            columna + brazo + bandera del FC-51 (cara exterior del riel -y)
//   mon_camara          abrazadera de la webcam cenital en la punta del brazo t_Q2-L
//   mon_e4              compuerta E4: placa colgada de los labios del tensor + embudo + oreja de la bisagra +
//                       brida del SG90 + canal A entero + tramo de arriba del canal B
//   mon_aleta           aleta de desvio con su pasador, barril y cubo al cuerno del SG90
//   mon_canal_b         tramo de abajo del canal B (manguito sobre el de arriba, 2 remaches) hasta la bandeja
//   mon_bandeja         bandeja de rechazo de monedas (suelta en el piso)
//
// PIDE A LA ESTRUCTURA (no lo puedo hacer yo): agujeros Ø9 pasantes (las dos paredes y en y) en los rieles para los
// ejes Ø8 de los rodillos motriz y tensor: t_T1-L_1 y t_T2-T3 en x -110, t_T1-L_2 y t_T3-L en x 90, en z 441.
// El eje en z 441 cae dentro del tubo (z 432-448): sin esos agujeros el eje comprado choca con el riel.
// =====================================================================================

// ----------------------------------------------------------------- funcional
mon_xE = [-50, -10, 30, 70];        // estaciones (mundo.py:175-181)
mon_z_sup = 452;                    // superficie de la banda
mon_z_banc = 450;                   // cara de arriba de la bancada
mon_x_mot = -110; mon_x_ten = 90; mon_z_rod = 441;   // ejes de los rodillos
mon_ret = [[-113, 344], [11, 344], [65, 418.8]];     // rodillos de retorno A, B, C (x, z)
mon_z_m18 = 449.5;                  // cara activa de los M18 (2.5 bajo la superficie)
mon_fc = [-50, 0, 502];             // origen del rayo del FC-51
mon_lente = [30, 0, 602];           // vidrio de la webcam cenital
mon_x_e4 = 105; mon_piv = [105, 0, 418];
mon_reposo = 28.65;                 // 0.5 rad hacia rechazo (+y)

// ----------------------------------------------------------------- comprado (MEDIR: de ficha o del visor)
mon_banda = [200, 55, 2];
mon_d_rod = 22; mon_l_rod = 59;     // MEDIR: largo de los rodillos (visor: ancho de la banda + 4)
mon_d_eje = 8;
mon_608 = [22, 7];
mon_nema = 42.3; mon_nema_l = 40; mon_y_nema = 97;   // cara de montaje en y 97 (visor.js:1168-1195)
mon_acople = [19, 25, 73];          // Ø, largo, centro en y
mon_m18 = [18, 68, 60];             // Ø, largo capacitivo (E1), largo inductivo (E2)
mon_sg = [22.7, 22.5, 11.8];        // SG90 con el eje en x: largo segun el eje, ancho, espesor (MEDIR: eje centrado)
mon_sep_alto = 4;                   // separadores de la banda (visor 4 mm)

// ----------------------------------------------------------------- impreso
mon_yi = 29.7;                      // cara interior de las placas colgantes (rodillo hasta 29.5)
mon_yr = 32.5;                      // cara interior de los rieles
mon_yo = 48.5;                      // cara exterior de los rieles
mon_xb = [-97, 73.5];               // largo de la bancada (entre los rodillos con la banda)
mon_e_banc = 6;                     // espesor de la bancada (z 444-450)
// donde NO hay pestana (empalme e_T1-L_1 en -y, nodo T3 en +y; sobresalen 2.6 hacia adentro del riel)
mon_sin_pest_m = [-50.9, -2.5];
mon_sin_pest_p = [-2.8, 62.8];
mon_vent = [36, 24];                // ventanas de E1 y E2 (x, y)

// ----------------------------------------------------------------- utilidades
function mon_inv(M) = let(Rt = [for (i = [0:2]) [for (j = [0:2]) M[j][i]]], q = -(Rt * [M[0][3], M[1][3], M[2][3]]))
  [[Rt[0][0], Rt[0][1], Rt[0][2], q[0]], [Rt[1][0], Rt[1][1], Rt[1][2], q[1]], [Rt[2][0], Rt[2][1], Rt[2][2], q[2]], [0, 0, 0, 1]];
function mon_pt(M, v) = [for (i = [0:2]) M[i] * [v[0], v[1], v[2], 1]];
// gota con la punta en +x (truncada a 1.2 r): techo de un agujero horizontal sin soportes
module mon_gota(r) intersection() {
  hull() { circle(r); translate([r * sqrt(2), 0]) circle(0.01); }
  translate([-r - 1, -r - 1]) square([2.2 * r + 1, 2 * r + 2]);
}
// agujero de eje y (de y0 a y1) con perfil 2D en (x, z); s = +1/-1: hacia donde va la punta de la gota
module mon_en_y(cx, cz, y0, y1, s = 1) multmatrix([[s, 0, 0, cx], [0, 0, 1, y0], [0, 1, 0, cz], [0, 0, 0, 1]])
  linear_extrude(y1 - y0) children();
module mon_cil_y(c, d, y0, y1) translate([c[0], y0, c[1]]) rotate([-90, 0, 0]) cylinder(d = d, h = y1 - y0);
module mon_cil_x(c, d, x0, x1) translate([x0, c[0], c[1]]) rotate([0, 90, 0]) cylinder(d = d, h = x1 - x0);
module mon_caja(a, b) translate(a) cube(b - a);
// canal en U en su marco local (z a lo largo, y hacia arriba): ancho interior w, paredes de h sobre el piso
module mon_u(w, h, e, z0, z1, piso = 0) translate([0, 0, z0]) linear_extrude(z1 - z0) difference() {
  translate([-(w / 2 + e), piso - e]) square([w + 2 * e, h + e]);
  translate([-w / 2, piso]) square([w, h + 1]);
}

// ----------------------------------------------------------------- canales
mon_A0 = [105, 0, 401]; mon_A1 = [105, -30, 354];   // canal A: suelta a 352-354 sobre el embudo de carga
mon_B0 = [105, 0, 401]; mon_B1 = [105, 105, 50];    // canal B: termina sobre la bandeja de rechazo
mon_MA = marco(mon_A0, mon_A1, [0, 0, 1]);
mon_MB = marco(mon_B0, mon_B1, [0, 0, 1]);
mon_LA = norm(mon_A1 - mon_A0);
mon_LB = norm(mon_B1 - mon_B0);
mon_LBu = mon_LB * (401 - 250) / 351;                // el canal B se parte en z 250 (cama de 240)
mon_solape = 15;

// ----------------------------------------------------------------- remaches
// agarres: bancada 5.6 = pata de la guia 2 + pestana 2 + pared 1.6; platina 5.5 = 3 + 2.5 (la una abre en un
// rebaje de 3.5 en la cara de arriba de la bancada); labios 4.6 = 3 + 1.6; placa E4 6 = labio 3 + placa 3;
// colgantes 4.4 = 2.6 + 0.2 + 1.6; FC-51 4.6 = 3 + 1.6; camara 4.2 = 2.4 + 0.2 + 1.6; canal B 3.4 = 1.6 + 0.2 + 1.6;
// apoyo del canal B: poste 4.6 = 3 + 1.6, canal 4.6 = 3 + 1.6
mon_rb_m = [-88, -68, 20, 50];       // remaches de la bancada en el riel -y (fuera del empalme y lejos de los tacos)
mon_rb_p = [-88, -60, -15, 68];      // en el riel +y (fuera del nodo T3)
mon_colg = [  // [pieza, x eje, z eje, x0, x1, lado, radio alrededor del eje, [[x, z] de los remaches]]
  ["mon_ret_a_m", -113, 344, -136, -120, -1, 7, [[-128, 436], [-128, 440.5]]],
  ["mon_ret_a_p", -113, 344, -136, -120, 1, 7, [[-128, 436], [-128, 440.5]]],
  ["mon_ret_b_m", 11, 344, -1, 18, -1, 7, [[4, 436], [14, 436]]],
  ["mon_ret_b_p", 11, 344, -38, -22, 1, 7, [[-34, 436], [-26, 436]]],
  ["mon_ret_c_m", 65, 418.8, 66, 80, -1, 6.5, [[72, 436], [72, 440.5]]],
  ["mon_ret_c_p", 65, 418.8, 66, 80, 1, 6.5, [[72, 436], [72, 440.5]]]
];
REM_MON = concat(
  [for (x = mon_rb_m) [str("r_mon_banc_m", x), 5.6, [x, -40.5, 452], [0, 0, -1]]],
  [for (x = mon_rb_p) [str("r_mon_banc_p", x), 5.6, [x, 40.5, 452], [0, 0, -1]]],
  [for (i = [0, 1]) for (s = [-1, 1]) [str("r_mon_plat", i + 1, s < 0 ? "_m" : "_p"), 5.5, [mon_xE[i], s * 18, 441], [0, 0, 1]]],
  [for (x = [-124, -96]) for (s = [-1, 1]) [str(s < 0 ? "r_mon_rmot_m" : "r_mon_jaula_", x), 4.6, [x, s * 40.5, 429], [0, 0, 1]]],
  [for (x = [79, 100]) for (s = [-1, 1]) [str("r_mon_rten", s < 0 ? "_m" : "_p", x), 4.6, [x, s * 40.5, 451], [0, 0, -1]]],
  [for (x = [110, 117]) for (s = [-1, 1]) [str("r_mon_e4", s < 0 ? "_m" : "_p", x), 6, [x, s * 40.5, 451], [0, 0, -1]]],
  [for (c = mon_colg) for (k = [0, 1]) [str("r_", c[0], "_", k), 4.4, [c[7][k][0], c[5] * mon_yi, c[7][k][1]], [0, c[5], 0]]],
  [for (z = [436, 442]) [str("r_mon_fc51_", z), 4.6, [-62, -51.5, z], [0, 1, 0]]],
  [["r_mon_cam_m", 4.2, [19.4, -6, 682], [1, 0, 0]], ["r_mon_cam_p", 4.2, [40.6, 1, 682], [-1, 0, 0]]],
  [["r_mon_sopb_poste1", 4.6, [41, 40.5, 150], [-1, 0, 0]], ["r_mon_sopb_poste2", 4.6, [41, 40.5, 160], [-1, 0, 0]],
   ["r_mon_sopb_canal1", 4.6, mon_pt(mon_MB, [21.4, 6, 232]), [1, 0, 0]], ["r_mon_sopb_canal2", 4.6, mon_pt(mon_MB, [21.4, 6, 250]), [1, 0, 0]]],
  [["r_mon_canalb_1", 3.4, mon_pt(mon_MB, [18.4, 5, mon_LBu - 7.5]), [1, 0, 0]],
   ["r_mon_canalb_2", 3.4, mon_pt(mon_MB, [-18.4, 5, mon_LBu - 7.5]), [-1, 0, 0]]]
);

PIEZAS_MON = ["mon_bancada", "mon_guia_m", "mon_guia_p", "mon_platina_e1", "mon_platina_e2",
  "mon_rod_mot_m", "mon_jaula_nema", "mon_rod_ten_m", "mon_rod_ten_p",
  "mon_ret_a_m", "mon_ret_a_p", "mon_ret_b_m", "mon_ret_b_p", "mon_ret_c_m", "mon_ret_c_p",
  "mon_fc51", "mon_camara", "mon_e4", "mon_aleta", "mon_canal_b", "mon_soporte_b", "mon_bandeja"];

// lo que se mueve (literal: ver moviles_por_defecto.scad)
MOVILES_MON = [["mon_aleta", ["mon_aleta"]], ["mon_vuelta_banda", []]];

// ----------------------------------------------------------------- bancada y guias
// zonas de x con pestana sobre el riel (lado s)
function mon_zonas(s) = let(n = s < 0 ? mon_sin_pest_m : mon_sin_pest_p) [[mon_xb[0], n[0]], [n[1], mon_xb[1]]];
// bancada aligerada (2026-10-24, ahorrar PLA): piel de 2 mm (z 448-450, plana bajo la banda; incluye las
// pestanas sobre los rieles) y nervios de 1.6 x 4 por debajo (borde, marcos de las ventanas, 2 largueros en y +-12.8,
// 3 travesanos y bujes de Ø10 en los remaches de las platinas). Boca abajo en la cama: los nervios crecen hacia arriba.
module mon_banc_2d() for (s = [-1, 1]) {
  n = s < 0 ? mon_sin_pest_m : mon_sin_pest_p;
  for (z = mon_zonas(s)) translate([z[0], s < 0 ? -32.3 : 0]) square([z[1] - z[0], 32.3]);
  translate([n[0], s < 0 ? -mon_yi : 0]) square([n[1] - n[0], mon_yi]);
}
module mon_vent_2d(d = 0) for (x = [mon_xE[0], mon_xE[1]]) translate([x - mon_vent[0] / 2 - d, -mon_vent[1] / 2 - d]) square([mon_vent[0] + 2 * d, mon_vent[1] + 2 * d]);
module mon_bancada() difference() {
  union() {
    translate([0, 0, 448]) linear_extrude(2) {
      mon_banc_2d();
      for (s = [-1, 1]) for (z = mon_zonas(s)) translate([z[0], s < 0 ? -48.3 : 32.3]) square([z[1] - z[0], 16]);
    }
    translate([0, 0, 444]) linear_extrude(4.01) intersection() {
      mon_banc_2d();
      union() {
        difference() { mon_banc_2d(); offset(delta = -1.6) mon_banc_2d(); }
        mon_vent_2d(1.6);
        for (s = [-1, 1]) translate([mon_xb[0], s * 12.8 - 0.8]) square([mon_xb[1] - mon_xb[0], 1.6]);
        for (x = [-84, 30, 52]) translate([x - 0.8, -40]) square([1.6, 80]);
        for (x = [mon_xE[0], mon_xE[1]]) for (s = [-1, 1]) translate([x, s * 18]) circle(d = 10);
      }
    }
  }
  translate([0, 0, 440]) linear_extrude(20) mon_vent_2d();
  // rebajes para la una de los remaches de las platinas
  for (x = [mon_xE[0], mon_xE[1]]) for (s = [-1, 1]) translate([x, s * 18, 446.5]) cylinder(d = 8, h = 5);
}
module mon_guia(s) {
  // pared (y 27.8-29.6, z 450-458) a todo lo largo; pata sobre la pestana (z 450-452) donde hay pestana
  mon_caja([mon_xb[0], s < 0 ? -29.6 : 27.8, 450], [mon_xb[1], s < 0 ? -27.8 : 29.6, 458]);
  for (z = mon_zonas(s)) mon_caja([z[0], s < 0 ? -48.3 : 29.6, 450], [z[1], s < 0 ? -29.6 : 48.3, 452]);
}
module mon_platina(i) let(x = mon_xE[i]) difference() {
  mon_caja([x - 18, -24, 441], [x + 18, 24, 444]);
  translate([x, 0, 440]) cylinder(d = 18.5, h = 5, $fn = 60);
}

// ----------------------------------------------------------------- bloques de los 608 y jaula
module mon_bolsillo(x, s, punta) {   // s = lado; el 608 entra desde la cara del riel
  y0 = s > 0 ? mon_yo - 0.01 : -(mon_yo + 7.2);
  mon_en_y(x, mon_z_rod, y0, y0 + 7.21, punta) mon_gota(mon_608[0] / 2 + tol);
  mon_cil_y([x, mon_z_rod], mon_d_eje + 1, -60, 60);
}
module mon_rod_mot_m() difference() {
  union() {
    mon_caja([-135, -57.5, 426], [-85, -mon_yo, 456]);
    mon_caja([-135, -mon_yo, 429], [-85, -34, 432]);          // labio bajo el riel (2 remaches desde abajo)
  }
  mon_bolsillo(mon_x_mot, -1, 1);
}
module mon_jaula_nema() difference() {
  union() {
    // aligerada: bloque del 608 solo de z 426 a 456, placa de fondo de 3 para la U, paredes de 3 y ventana en el costado
    mon_caja([-135, mon_yo, 426], [-85, 57.5, 456]);
    mon_caja([-135, 54.5, 416], [-85, 57.5, 466]);
    mon_caja([-135, 34, 429], [-85, mon_yo, 432]);
    difference() {
      mon_caja([-135, 57.5, 416], [-132, mon_y_nema, 466]);      // costado (cara de la cama)
      mon_caja([-136, 63, 424], [-131, 89, 458]);
    }
    mon_caja([-135, 57.5, 463], [-85, mon_y_nema, 466]);         // techo
    mon_caja([-135, 57.5, 416], [-85, mon_y_nema, 419]);         // piso
    mon_caja([-135, mon_y_nema - 4, 416], [-85, mon_y_nema, 466]); // placa del motor 50 x 50 x 4
  }
  mon_bolsillo(mon_x_mot, 1, 1);
  mon_en_y(mon_x_mot, mon_z_rod, mon_y_nema - 5, mon_y_nema + 1, 1) mon_gota(11.5);   // resalte Ø22 del NEMA
  for (dx = [-15.5, 15.5]) for (dz = [-15.5, 15.5]) mon_cil_y([mon_x_mot + dx, mon_z_rod + dz], 3.4, mon_y_nema - 5, mon_y_nema + 1);
}
module mon_rod_ten(s) difference() {
  union() {
    mon_caja([73.7, s < 0 ? -57.5 : mon_yo, 426], [105.8, s < 0 ? -mon_yo : 57.5, 456]);
    mon_caja([73.7, s < 0 ? -57.5 : 34, 448], [120, s < 0 ? -34 : 57.5, 451]);   // labio sobre el riel (y la placa E4)
  }
  mon_bolsillo(mon_x_ten, s, 1);
}

// ----------------------------------------------------------------- rodillos de retorno: placas colgantes
module mon_colgante(c) let(r = c[6], y0 = c[5] > 0 ? mon_yi : -mon_yi - 2.6)
  multmatrix([[1, 0, 0, 0], [0, 0, 1, y0], [0, 1, 0, 0], [0, 0, 0, 1]]) linear_extrude(2.6) difference() {
    union() {
      translate([c[3], 431]) square([c[4] - c[3], 12.8]);
      hull() { translate([c[3], 431]) square([c[4] - c[3], 2]); translate([c[1], c[2]]) circle(r); }
    }
    translate([c[1], c[2]]) circle(d = mon_d_eje + 2 * tol);
  }

// ----------------------------------------------------------------- FC-51
module mon_fc51() {
  mon_caja([-68, -51.5, 434], [-56, -mon_yo, 545]);               // columna en la cara exterior del riel -y
  mon_caja([-68, -51.5, 540], [-42.9, 8, 545]);                   // brazo sobre la banda
  difference() {
    mon_caja([-45.9, -8, 510], [-42.9, 8, 540]);                  // bandera: la placa del FC-51 va atornillada (M3)
    mon_cil_x([0, 530], 3.2, -47, -42);
  }
}

// ----------------------------------------------------------------- camara cenital
module mon_camara() difference() {
  union() {
    mon_caja([15, -15, 639.3], [45, 12, 643.3]);                  // placa sobre la carcasa (tornillo 1/4")
    mon_caja([19.4, -14.8, 643.3], [40.6, 7.7, 673.8]);            // columna
    mon_caja([19.4, -14.8, 673.8], [40.6, 7.7, 689]);              // montura en U del tubo
  }
  mon_caja([30 - 8.2, -16, 673.8], [30 + 8.2, 9, 700]);
  translate([30, 0, 636]) cylinder(d = 6.5, h = 20);              // MEDIR: rosca 1/4" de la webcam (arriba)
}

// ----------------------------------------------------------------- compuerta E4
mon_r_corte = 17.5;     // libre alrededor del tensor: rodillo 11 + banda 2 + separadores 4 + 0.5
// Salida Ø29 (coordinador, 2026-10-24): con Ø20 (la del visor) la moneda mas grande, de 26,7 mm, no pasa acostada.
module mon_embudo_solido() translate([mon_x_e4, 0, 420]) cylinder(h = 28, r1 = 16.5, r2 = 22.91, $fn = 72);
module mon_embudo_hueco() translate([mon_x_e4, 0, 419]) cylinder(h = 30, r1 = 14.5, r2 = 10 + 29 * 10 / 26, $fn = 72);
module mon_e4() difference() {
  union() {
    difference() {   // placa bajo los labios de los tensores (sin las esquinas +x, que no cargan)
      mon_caja([106.2, -57.5, 445], [137, 57.5, 448]);
      for (s = [-1, 1]) mon_caja([122, s < 0 ? -60 : 24, 444], [138, s < 0 ? -24 : 60, 449]);
    }
    mon_embudo_solido();
    mon_caja([120, -12, 398], [122, 12, 445]);                    // pared +x (la cuelga de la placa)
    mon_caja([133.85, -20, 406], [136.85, 20, 445]);              // brida del SG90
    // canales A y B: se alargan hacia atras y se cortan en el plano y = 0 (la cumbrera entre los dos), asi el
    // arranque queda en una cara vertical comun y no hay tapas mirando hacia la cama
    intersection() { multmatrix(mon_MA) mon_u(30, 10, 1.6, -15, mon_LA); mon_caja([60, -100, 300], [160, 0, 500]); }
    intersection() { multmatrix(mon_MB) mon_u(30, 12, 1.6, -15, mon_LBu); mon_caja([60, 0, 200], [160, 100, 500]); }
  }
  mon_embudo_hueco();
  mon_en_y(0, 0, -60, 60) mon_lazo(mon_r_corte);                 // por donde da la vuelta la banda (con separadores)
  mon_caja([80, -30, 421.6], [96, 30, 450]);                      // lado -x del embudo: lo tapa el tensor (sin voladizo)
  mon_caja([93, -4.5, 413], [119.9, 4.5, 422.5]);                 // pasa el barril de la aleta bajo la salida
  mon_cil_x([0, 418], 7 + 2 * tol, 119, 124);                     // bisagra: el cubo gira en la pared +x (la oreja)
  mon_caja([133, -(mon_sg[1] / 2 + tol), 405], [138, mon_sg[1] / 2 + tol, 418 + mon_sg[2] / 2 + tol]);  // ventana abierta abajo
  for (s = [-1, 1]) mon_cil_x([s * 13.9, 418], 2, 132, 138);      // MEDIR: tornillos M2 de las alas del SG90
}
module mon_aleta_quieta() {   // vertical; en el ensamble se gira mon_reposo
  mon_caja([96, -1, 402], [116, 1, 418]);                        // 20 de ancho bajo la salida Ø29 (moneda de 26.7)
  mon_cil_x([0, 418], 5, 96, 115.5);
  mon_cil_x([0, 418], 7, 115.5, 122.4);
}
module mon_aleta_en(a) translate(mon_piv) rotate([a, 0, 0]) translate(-mon_piv) mon_aleta_quieta();

// ----------------------------------------------------------------- canal B (abajo) y bandeja
module mon_canal_b() multmatrix(mon_MB) mon_u(30 + 2 * (1.6 + tol), 12, 1.6, mon_LBu - mon_solape, mon_LB, -(1.6 + tol));
// apoyo del canal B: placa en la cara +x del poste t_F3-T3_1 (x 38), brazo a z 135-145 y placa contra la pared
// -x del canal (x 85.8); se imprime derecha (el brazo y el pie de las dos placas en z 135 apoyan en la cama)
module mon_soporte_b() {
  mon_caja([38, 32.5, 135], [41, 48.5, 165]);
  intersection() {
    multmatrix(mon_MB) translate([18.4, 0, 225]) cube([3, 12, 60]);
    mon_caja([60, 0, 135], [120, 200, 300]);
  }
  hull() { mon_caja([38, 37.5, 135], [44, 43.5, 145]); mon_caja([80, 79.3, 135], [85, 85.3, 145]); }
}
module mon_bandeja() difference() {
  mon_caja([55, 85, 0], [145, 175, 35]);
  mon_caja([56.6, 86.6, 2], [143.4, 173.4, 40]);   // paredes 1.6, piso 2
}

// ----------------------------------------------------------------- piezas
module mon_pieza(n) {
  if (n == "mon_bancada") mon_bancada();
  else if (n == "mon_guia_m") mon_guia(-1);
  else if (n == "mon_guia_p") mon_guia(1);
  else if (n == "mon_platina_e1") mon_platina(0);
  else if (n == "mon_platina_e2") mon_platina(1);
  else if (n == "mon_rod_mot_m") mon_rod_mot_m();
  else if (n == "mon_jaula_nema") mon_jaula_nema();
  else if (n == "mon_rod_ten_m") mon_rod_ten(-1);
  else if (n == "mon_rod_ten_p") mon_rod_ten(1);
  else if (n == "mon_fc51") mon_fc51();
  else if (n == "mon_camara") mon_camara();
  else if (n == "mon_e4") mon_e4();
  else if (n == "mon_aleta") mon_aleta_en(mon_reposo);
  else if (n == "mon_canal_b") mon_canal_b();
  else if (n == "mon_soporte_b") mon_soporte_b();
  else if (n == "mon_bandeja") mon_bandeja();
  else for (c = mon_colg) if (c[0] == n) mon_colgante(c);
}
// orientacion de impresion (revisar.py / exportar.py la apoyan en la cama)
module mon_a_cama(n) {
  if (n == "mon_bancada" || n == "mon_fc51" || n == "mon_e4") rotate([180, 0, 0]) children();
  else if (n == "mon_rod_mot_m" || n == "mon_jaula_nema" || n == "mon_rod_ten_m" || n == "mon_rod_ten_p")
    rotate([0, -90, 0]) children();                               // cara -x en la cama, la gota apunta arriba
  else if (len([for (c = mon_colg) if (c[0] == n) 1]) > 0) rotate([90, 0, 0]) children();   // acostada en su cara
  else if (n == "mon_aleta") rotate([0, -90, 0]) translate(mon_piv) rotate([-mon_reposo, 0, 0]) translate(-mon_piv) children();
  else if (n == "mon_canal_b") rotate([90, 0, 0]) multmatrix(mon_inv(mon_MB)) children();
  else children();
}

// ----------------------------------------------------------------- lo que se mueve
// la banda: envolvente del lazo (convexo: los 5 rodillos quedan en el casco) de 2 de banda + 4 de separadores,
// y 2 hacia adentro (la banda corre sobre la bancada en z 450 y no en la cima de los rodillos, 452)
mon_rodillos = concat([[mon_x_mot, mon_z_rod], [mon_x_ten, mon_z_rod]], mon_ret);
module mon_lazo(r) hull() for (p = mon_rodillos) translate(p) circle(r, $fn = 64);
module mon_barrido(n) {
  if (n == "mon_aleta") for (a = [-mon_reposo:4:mon_reposo + 0.1]) mon_aleta_en(a);
  else if (n == "mon_vuelta_banda") difference() {
    mon_en_y(0, 0, -mon_banda[1] / 2, mon_banda[1] / 2) difference() {
      mon_lazo(mon_d_rod / 2 + 2 + mon_sep_alto);
      mon_lazo(mon_d_rod / 2 - 2);
    }
    // los rodillos sobre los que corre y la banda comprada dibujada quieta
    for (p = mon_rodillos) mon_cil_y(p, mon_d_rod + 0.4, -40, 40);
    mon_caja([-110.1, -27.6, 449.9], [90.1, 27.6, 452.1]);
  }
}

// ----------------------------------------------------------------- comprados
module mon_comprados() {
  color("#222") mon_caja([-110, -27.5, 450], [90, 27.5, 452]);                     // banda 200 x 55 x 2
  color("#aaa") {
    for (p = mon_rodillos) mon_cil_y(p, mon_d_rod, -mon_l_rod / 2, mon_l_rod / 2);
    for (p = mon_ret) mon_cil_y(p, mon_d_eje, -32.3, 32.3);                        // ejes de retorno (fijos)
    mon_cil_y([mon_x_mot, mon_z_rod], mon_d_eje, -57.5, mon_acople[2]);            // eje motriz hasta el acople
    mon_cil_y([mon_x_ten, mon_z_rod], mon_d_eje, -57.5, 57.5);
    for (x = [mon_x_mot, mon_x_ten]) for (s = [-1, 1])
      mon_cil_y([x, mon_z_rod], mon_608[0], s > 0 ? 48.7 : -55.7, s > 0 ? 55.7 : -48.7);   // 608
    mon_cil_y([mon_x_mot, mon_z_rod], mon_acople[0], mon_acople[2] - mon_acople[1] / 2, mon_acople[2] + mon_acople[1] / 2);
    mon_cil_y([mon_x_mot, mon_z_rod], 5, mon_acople[2], mon_y_nema);               // eje del motor
  }
  color("#333") mon_caja([mon_x_mot - mon_nema / 2, mon_y_nema, mon_z_rod - mon_nema / 2],
                         [mon_x_mot + mon_nema / 2, mon_y_nema + mon_nema_l, mon_z_rod + mon_nema / 2]);
  // M18: capacitivo bajo E1, inductivo bajo E2, cara activa en z 449.5
  color("#c80") for (i = [0, 1]) translate([mon_xE[i], 0, mon_z_m18 - mon_m18[i + 1]]) cylinder(d = mon_m18[0], h = mon_m18[i + 1]);
  // FC-51: placa vertical detras de los LED, LED Ø5 a y +-3.5 mirando -z desde z 502
  color("#048") {
    mon_caja([-47.5, -7, 506], [-45.9, 7, 538]);
    for (s = [-1, 1]) translate([mon_fc[0], s * 3.5, mon_fc[2]]) cylinder(d = 5, h = 7);
  }
  // webcam: carcasa 42 x 42 x 20 con centro 27.3 sobre el vidrio, lente y anillo LED 60/40
  color("#111") {
    mon_caja([9, -21, 619.3], [51, 21, 639.3]);
    translate(mon_lente) cylinder(d = 14, h = 17.4);
    translate(mon_lente + [0, 0, 3]) difference() { cylinder(d = 60, h = 3); translate([0, 0, -1]) cylinder(d = 40, h = 5); }
  }
  // SG90 de la compuerta: eje en x sobre la bisagra, alas contra la brida
  color("#36c") {
    mon_caja([126.65, -mon_sg[1] / 2, 418 - mon_sg[2] / 2], [126.65 + mon_sg[0], mon_sg[1] / 2, 418 + mon_sg[2] / 2]);
    mon_caja([131.35, -16.1, 418 - mon_sg[2] / 2], [133.85, 16.1, 418 + mon_sg[2] / 2]);
    mon_cil_x([0, 418], 4.8, 122.65, 126.65);
  }
}

// Paso de los ejes Ø8 de los rodillos motriz (x -110) y tensor (x 90) por los rieles de la estructura (eje z 441,
// dentro del tubo de z 432 a 448): Ø9 de lado a lado (coordinador, 2026-10-24; lo pidio el agente de monedas).
AGUJEROS_MON = [[[-110, -60, 441], [-110, 60, 441], 9], [[90, -60, 441], [90, 60, 441], 9]];
