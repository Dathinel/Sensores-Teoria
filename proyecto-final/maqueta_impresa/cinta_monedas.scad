// =====================================================================================
// Subsistema "cinta_monedas" (prefijo mon_): todo lo que va sobre la mesa de monedas impresa (los dos rieles
// de tubo 16 x 16 con eje en y = +-40.5, z = 440), la compuerta E4 y los canales. Ver CONVENCIONES.md.
// Lo incluye maqueta.scad (este archivo no hace include de nada). Marco del mundo en mm, z = 0 el piso.
//
// FUNCIONAL (no se mueve, inventario_maqueta.md §1-3, §18): estaciones E1..E4 en x -50, -10, 30, 70 (paso 40),
// superficie de la banda z 452 (bancada hasta z 450 + banda de 2), rodillos motriz x -110 y tensor x 90 con eje
// en z 439 (la cima del Ø22 en 450, la cara de la bancada: la banda apoya en los dos), retorno A (-113, 344),
// B (11, 344) (el C de (65, 418.8) se quito: ver mon_ret), cara activa de los M18 a z 449.5, rayo del FC-51 desde
// (-50, 0, 502), vidrio de la webcam en (30, 0, 602), embudo E4 en x 105 (boca z 446 Ø40, salida z 420 Ø29), pivote de
// la aleta (105, 0, 418), SG90 en x 138, bocas de los canales en z ~400.
//
// Piezas (todas PLA):
//   mon_bancada         placa entre los rieles con las ventanas de E1/E2; pestanas sobre los rieles (impresa boca abajo)
//   mon_guia_m/_p       guias laterales de la banda (L: pared + pata que va sobre la pestana de la bancada)
//   mon_platina_e1/_e2  platinas de los M18 (Ø18.5) remachadas bajo la bancada
//   mon_rod_mot_m       bloque del 608 del rodillo motriz, lado -y (abraza el riel: labio bajo y sobre el riel) y
//                       bajada por fuera del riel hasta el eje del retorno A
//   mon_jaula_nema      bloque del 608 motriz +y + jaula en U del NEMA 17 (una sola pieza; abraza el riel y baja a A)
//   mon_casq_a_m/_p     casquillos en el eje de A (ubican el rodillo entre las bajadas de los dos bloques)
//   mon_rod_ten_m/_p    bloques de los 608 del tensor (labio SOBRE el riel, que sigue mas alla de la punta
//                       y sostiene la compuerta); el 608 corre en una ranura de x 86 a 90 con un M3 de empuje
//   mon_ret_b_{m,p}     placas colgantes del rodillo de retorno B, remachadas al labio bajo el riel y al taco_1
//   mon_fc51            columna + brazo + bandera del FC-51 (cara exterior del riel -y)
//   mon_camara          abrazadera de la webcam cenital en la punta del brazo t_Q2-L
//   mon_e4              compuerta E4: placa colgada de los labios del tensor + embudo + oreja de la bisagra +
//                       brida del SG90 + canal A entero + tramo de arriba del canal B
//   mon_aleta           aleta de desvio: placa que sube del pivote dentro del embudo, barril y cubo a la estria del SG90
//   mon_canal_b         tramo de abajo del canal B (manguito sobre el de arriba, 2 remaches) hasta la bandeja
//   mon_bandeja         bandeja de rechazo de monedas (suelta en el piso)
//
// PIDE A LA ESTRUCTURA (no lo puedo hacer yo): agujeros Ø9 pasantes (las dos paredes y en y) en los rieles para los
// ejes Ø8 de los rodillos motriz y tensor: t_T1-L_1 y t_T2-T3 en x -110 (Ø9), t_T1-L_2 y t_T3-L en x 90 (ranura de
// 9 x 13, x 83.5-96.5: el tensor corre de 86 a 90), en z 439 (AGUJEROS_MON, al final; maqueta.scad los resta).
// El eje en z 439 cae dentro del tubo (z 432-448): sin esos agujeros el eje comprado choca con el riel.
// =====================================================================================

// ----------------------------------------------------------------- funcional
mon_xE = [-50, -10, 30, 70];        // estaciones (mundo.py:175-181)
mon_z_sup = 452;                    // superficie de la banda
mon_z_banc = 450;                   // cara de arriba de la bancada
mon_x_mot = -110; mon_x_ten = 90; mon_z_rod = 439;   // ejes de los rodillos: cima del Ø22 en 450 = cara de la bancada
                                                      // (2026-10-25: con 441 la banda pasaba 2 sobre la bancada, en 452-454)
mon_ret = [[-113, 344], [11, 344]];     // rodillos de retorno A, B (x, z)
// El retorno C (65; 418,8) se quito (opinion externa, 2026-10-25): quedaba 6,3 mm DENTRO de la recta tensor-B y la banda
// es el casco de los rodillos, asi que no la tocaba. Con el se fueron mon_ret_c_m/_p, sus 4 remaches, el rodillo y su eje;
// el lazo (y el barrido de la banda) no cambia, porque C estaba adentro.
mon_z_m18 = 449.5;                  // cara activa de los M18 (2.5 bajo la superficie)
mon_fc = [-50, 0, 502];             // origen del rayo del FC-51
mon_lente = [30, 0, 602];           // vidrio de la webcam cenital
mon_x_e4 = 105; mon_piv = [105, 0, 418];
mon_reposo = 45;                    // medio recorrido de la aleta: +45 = rechazo (reposo, punta a -y: la moneda va a +y),
                                    // -45 = almacen; el SG90 gira 90 (antes 28.65 = 0.5 rad, con la aleta colgando)

// ----------------------------------------------------------------- comprado (MEDIR: de ficha o del visor)
mon_banda = [200, 55, 2];
mon_d_rod = 22; mon_l_rod = 59;     // MEDIR: largo de los rodillos (visor: ancho de la banda + 4)
mon_d_eje = 8;
mon_608 = [22, 7];
mon_nema = 42.3; mon_nema_l = 40; mon_y_nema = 97;   // cara de la placa del motor en y 97 (visor.js:1168-1195)
mon_sep_nema = 3;                   // separadores de nailon entre la placa y el motor (manual): la cara del motor en y 100
mon_acople = [19, 25, 73];          // Ø, largo, centro en y
mon_m18 = [18, 68, 60];             // Ø, largo capacitivo (E1), largo inductivo (E2)
mon_sg = [22.7, 22.5, 11.8];        // SG90 con el eje en x: largo segun el eje, ancho, espesor (MEDIR: eje centrado)
mon_estria = [4.8, 4];              // MEDIR: estria del eje del SG90 (diametro, largo sobre la caja), la de almacen.scad
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
mon_vent = [36, 28];                // ventanas de E1 y E2 (x, y): 28 en y para que quepa el pasillo del remache

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
// Primera capa (usuario, 2026-10-24: se despega en los circulos chicos): ningun remache entra por la cara que apoya
// en la cama. Agarres (suma exacta): bancada -> riel 4.4 = pestana colgante 2.6 + 0.2 + pared 1.6 (de costado, la una
// en el hueco del tubo); guia -> riel 5.6 = placa 2 + pata 2 + pared 1.6 (desde arriba; la guia se imprime de
// costado); platina -> marco de la ventana 4.4 = marco 1.6 + 0.2 + pestana 2.6 (la una abre en la ventana);
// bloques 4.6 = 3 + 1.6; E4 -> placas del tensor 6.2 = 3 + 0.2 + 3 (de costado, la una al aire); colgantes 4.6 por el
// labio (b_p) y 6.8 al taco (b_m);
// FC-51 4.6; camara 4.4 = 2.4 + 2 x 0.2 + 1.6; canal B 3.6 = 1.6 + 2 x 0.2 + 1.6; apoyo del canal B 4.6 = 3 + 1.6.
// Camara y canal B (auditoria 2026-10-25): la pieza de adentro va en una U de la misma pieza (16.4 para un tubo de 16,
// 33.6 para un canal de 33.2) y el cono de la una la corre 0.2 hacia el lado de la una: medido, la pila llega a 4.4 / 3.6
// y con el agarre de 4.2 / 3.4 el hombro quedaba justo en la cara (margen 0)
mon_rg_m = [-88, -72, 20, 58];       // guia -y -> riel (fuera del empalme, >= 5 de los remaches de los tacos)
mon_rg_p = [-88, -60, -15, 68];      // guia +y -> riel (fuera del nodo T3)
mon_rf_m = [-84, -74, 28, 50];       // pestanas colgantes de la bancada -y -> cara interior del riel (lejos de las platinas;
                                     // con -72 el pasillo de 24 detras de la cabeza daba en el marco de la ventana de E1, x -69.6)
mon_rf_p = [-92, -80];               // +y: solo antes de la platina de E1 (sus pestanas y el nodo T3 tapan el resto)
mon_fl_m = [[-97, -56], [24, 62]];   // tramos de esas pestanas colgantes (entre el empalme, el colgante b_m y x 62)
mon_fl_p = [[-97, -74]];
mon_z_lat = 440;                     // todo remache que entra de costado a un riel va a la altura del eje: el hueco es
                                     // octogonal (chaflanes de 3 en las 4 esquinas) y solo entre z 438.8 y 441.2 queda
                                     // pared de 1.6 con hueco limpio detras
// Colgantes: [pieza, x eje, z eje, x0, x1, lado, radio alrededor del eje, [x de los remaches], y de la cara de la placa
// mas cercana a y = 0, y donde apoya la cabeza, sentido del remache]. Tiras de arriba de >= 20 mm: es la cara que apoya
// al imprimirlas de pie (> 50 mm2, que primera_capa.py no tome por un circulo chico). Las cabezas lejos de los rodillos
// motriz y tensor y su pasillo (24 mm detras de la cabeza) libre de las platinas: por eso el colgante +y de B va por
// FUERA del riel (y 48.7-51.3; el eje de B se alarga hasta y 52).
// A ya no tiene colgantes (auditoria 2026-10-25): la banda tira de A con (1.03, 1.00)·T y la placa de 96 mm colgada de 2
// remaches a 15 mm daba ~86 N de corte por remache con T = 20 N (6.9 MPa, admisible 5). Su eje cuelga ahora de las
// bajadas de los bloques del motriz (mon_bajada_a): ahi el tiron hacia arriba de A y el de abajo del motriz se anulan.
mon_colg = [
  // remaches de cada colgante a 10 entre centros (2026-10-25: a 6 las cabezas de 8 se pisaban y quedaba 1,6 de pared)
  ["mon_ret_b_m", 11, 344, 8, 32, -1, 7, [14, 26], -32.3, -29.7, -1],   // va al taco_1, no al riel (ver mon_colgante)
  ["mon_ret_b_p", 11, 344, -42, -22, 1, 7, [-38, -26], 48.7, 51.3, -1]
];
mon_y_marco = 14;                    // cara interior del marco de la ventana (ventana de 28 en y)
mon_z_plat = 436;                    // cara de abajo de la platina (3 de espesor; pestanas de z 439 a 448)
REM_MON = concat(
  [for (x = mon_rg_m) [str("r_mon_guia_m", x), 5.6, [x, -40.5, 452], [0, 0, -1]]],
  [for (x = mon_rg_p) [str("r_mon_guia_p", x), 5.6, [x, 40.5, 452], [0, 0, -1]]],
  [for (x = mon_rf_m) [str("r_mon_banc_m", x), 4.4, [x, -mon_yi, mon_z_lat], [0, -1, 0]]],
  [for (x = mon_rf_p) [str("r_mon_banc_p", x), 4.4, [x, mon_yi, mon_z_lat], [0, 1, 0]]],
  [for (i = [0, 1]) for (s = [-1, 1]) [str("r_mon_plat", i + 1, s < 0 ? "_m" : "_p"), 4.4, [mon_xE[i] + s * 13, s * mon_y_marco, 443.5], [0, s, 0]]],
  [for (x = [-124, -96]) for (s = [-1, 1]) [str(s < 0 ? "r_mon_rmot_m" : "r_mon_jaula_", x), 4.6, [x, s * 40.5, 429], [0, 0, 1]]],
  [for (x = [79, 100]) for (s = [-1, 1]) [str("r_mon_rten", s < 0 ? "_m" : "_p", x), 4.6, [x, s * 40.5, 451], [0, 0, -1]]],
  [for (z = [433, 443]) for (s = [-1, 1]) [str("r_mon_e4", s < 0 ? "_m" : "_p", z), 6.2, [113, s * 54.7, z], [0, -s, 0]]],
  // b_m: contra la cara +y del bloque del taco_1 (x 5..35, z 408..432), placa 2,6 + 0,2 + pared del taco 4; la una abre en
  // el hueco del taco. En el riel no cabian dos: entre el pasillo de la platina E2 (x <= 8) y la pestana de la bancada
  // (x >= 24) quedaban a 4 entre centros y los agujeros de 4,4 se pisaban.
  [["r_mon_ret_b_m_0", 6.8, [14, -29.7, 414], [0, -1, 0]], ["r_mon_ret_b_m_1", 6.8, [26, -29.7, 426], [0, -1, 0]]],
  // b_p: labio bajo el riel +y, 2 remaches desde abajo (labio 3 + pared 1,6). De costado sumaban 2 agujeros a la cara +y
  // de t_T2-T3, que ya tiene agujeros en las 4 caras: con estos, ninguna cara le quedaba con menos de 3 (primera capa)
  [for (k = [0, 1]) [str("r_mon_ret_b_p_", k), 4.6, [mon_colg[1][7][k], 40.5, 429], [0, 0, 1]]],
  [for (x = [-66, -58]) [str("r_mon_fc51_", -x), 4.6, [x, -51.5, mon_z_lat], [0, 1, 0]]],
  [["r_mon_cam_m", 4.4, [19.4, -6, 682], [1, 0, 0]], ["r_mon_cam_p", 4.4, [40.6, 1, 682], [-1, 0, 0]]],
  [["r_mon_sopb_poste1", 4.6, [41, 40.5, 150], [-1, 0, 0]], ["r_mon_sopb_poste2", 4.6, [41, 40.5, 160], [-1, 0, 0]],
   ["r_mon_sopb_canal1", 4.6, mon_pt(mon_MB, [21.4, 6, 232]), [1, 0, 0]], ["r_mon_sopb_canal2", 4.6, mon_pt(mon_MB, [21.4, 6, 250]), [1, 0, 0]]],
  [["r_mon_canalb_1", 3.6, mon_pt(mon_MB, [18.4, 5, mon_LBu - 7.5]), [1, 0, 0]],
   ["r_mon_canalb_2", 3.6, mon_pt(mon_MB, [-18.4, 5, mon_LBu - 7.5]), [-1, 0, 0]]]
);

PIEZAS_MON = ["mon_bancada", "mon_guia_m", "mon_guia_p", "mon_platina_e1", "mon_platina_e2",
  "mon_rod_mot_m", "mon_jaula_nema", "mon_casq_a_m", "mon_casq_a_p", "mon_rod_ten_m", "mon_rod_ten_p",
  "mon_ret_b_m", "mon_ret_b_p",
  "mon_fc51", "mon_camara", "mon_e4", "mon_aleta", "mon_canal_b", "mon_soporte_b", "mon_bandeja"];

// lo que se mueve (literal: ver moviles_por_defecto.scad)
MOVILES_MON = [["mon_aleta", ["mon_aleta"]], ["mon_vuelta_banda", []]];

// ----------------------------------------------------------------- bancada y guias
// zonas de x libres de empalme / nodo T3 sobre el riel (lado s)
function mon_zonas(s) = let(n = s < 0 ? mon_sin_pest_m : mon_sin_pest_p) [[mon_xb[0], n[0]], [n[1], mon_xb[1]]];
// Bancada: piel de 2 mm (z 448-450, plana y MACIZA bajo la banda: es la cara que apoya en la cama, boca abajo) entre
// los rieles, nervios de 1.6 por debajo (borde, marcos de las ventanas de 9 de alto, 2 largueros en y +-24 y
// 3 travesanos) y pestanas colgantes de 2.6 (z 432-448) contra la cara interior de los rieles, por donde entran los
// remaches de costado. No apoya en los rieles: la sujetan esas pestanas y, por arriba, la pisan las guias.
module mon_banc_2d() for (s = [-1, 1]) {
  n = s < 0 ? mon_sin_pest_m : mon_sin_pest_p;
  for (z = mon_zonas(s)) translate([z[0], s < 0 ? -32.3 : 0]) square([z[1] - z[0], 32.3]);
  translate([n[0], s < 0 ? -mon_yi : 0]) square([n[1] - n[0], mon_yi]);
}
module mon_vent_2d(d = 0) for (x = [mon_xE[0], mon_xE[1]]) translate([x - mon_vent[0] / 2 - d, -mon_vent[1] / 2 - d]) square([mon_vent[0] + 2 * d, mon_vent[1] + 2 * d]);
module mon_bancada() difference() {
  union() {
    translate([0, 0, 448]) linear_extrude(2) mon_banc_2d();
    translate([0, 0, 444]) linear_extrude(4.01) intersection() {
      mon_banc_2d();
      union() {
        difference() { mon_banc_2d(); offset(delta = -1.6) mon_banc_2d(); }
        for (s = [-1, 1]) translate([mon_xb[0], s * 24 - 0.8]) square([mon_xb[1] - mon_xb[0], 1.6]);   // fuera de las pestanas de las platinas
        for (x = [-84, 30, 52]) translate([x - 0.8, -40]) square([1.6, 80]);
      }
    }
    translate([0, 0, mon_z_plat + 3]) linear_extrude(448 - mon_z_plat - 3 + 0.01) difference() { mon_vent_2d(1.6); mon_vent_2d(); }
    for (s = [-1, 1]) let(fl = s < 0 ? mon_fl_m : mon_fl_p) for (f = fl) mon_caja([f[0], s < 0 ? -32.3 : mon_yi, 432], [f[1], s < 0 ? -mon_yi : 32.3, 448.01]);
  }
  translate([0, 0, 430]) linear_extrude(30) mon_vent_2d();
}
// Guia lateral: pared (y 27.8-29.6, z 450-458), placa de 2 que pisa el borde de la bancada (z 450-452, hasta y 48.5)
// y pata sobre el riel (z 448-450); en las zonas del empalme / nodo T3 solo quedan la pared y la placa hasta y 29.7.
// Se imprime de costado (la cara exterior de la pared en la cama): los remaches le entran por una cara lateral.
// Pata con chaflan a 45 en la arista de adentro (2026-10-25): de costado colgaba 2 de la placa en todo el tramo (46 a
// 94 de largo, a 4.7 de la cama). Debajo no se puede rellenar (hasta y 32.3 esta la piel de la bancada): se le saca la
// arista y apoya en el riel de y 34.5 a 48.3 (los remaches, en y 40.5, no cambian). Sube a 450.5 para fundirse con la placa.
module mon_guia(s) {
  mon_caja([mon_xb[0], s < 0 ? -29.6 : 27.8, 450], [mon_xb[1], s < 0 ? -27.8 : 29.6, 458]);
  mon_caja([mon_xb[0], s < 0 ? -mon_yi : 27.8, 450], [mon_xb[1], s < 0 ? -27.8 : mon_yi, 452]);
  for (z = mon_zonas(s)) {
    mon_caja([z[0], s < 0 ? -48.3 : mon_yi, 450], [z[1], s < 0 ? -mon_yi : 48.3, 452]);
    translate([z[0], 0, 0]) rotate([90, 0, 90]) linear_extrude(z[1] - z[0])
      polygon([[s * 32.5, 450.5], [s * 32.5, 450], [s * 34.5, 448], [s * 48.3, 448], [s * 48.3, 450.5]]);
  }
}
// Platina del M18: placa 36 x 48 x 3 (z 436-439, el Ø18.5 es el unico agujero de la cara de apoyo) con dos pestanas
// que suben pegadas por fuera a los marcos de la ventana; remaches de costado con la una abriendo en la ventana.
module mon_platina(i) let(x = mon_xE[i], y0 = mon_y_marco + 1.6 + tol) difference() {
  union() {
    mon_caja([x - 18, -24, mon_z_plat], [x + 18, 24, mon_z_plat + 3]);
    for (s = [-1, 1]) mon_caja([x - 18, s < 0 ? -y0 - 2.6 : y0, mon_z_plat + 3], [x + 18, s < 0 ? -y0 : y0 + 2.6, 448]);
  }
  translate([x, 0, mon_z_plat - 1]) cylinder(d = 18.5, h = 5, $fn = 60);
}

// ----------------------------------------------------------------- bloques de los 608 y jaula
// s = lado; el 608 entra desde la cara del riel. dx > 0: corredera, el 608 va de x - dx a x (gota alargada: la punta,
// que es el techo al imprimir sobre la cara -x, queda en x) y el eje pasa por una ranura
module mon_bolsillo(x, s, punta, dx = 0) {
  y0 = s > 0 ? mon_yo - 0.01 : -(mon_yo + 7.2);
  mon_en_y(x, mon_z_rod, y0, y0 + 7.21, punta) hull() { mon_gota(mon_608[0] / 2 + tol); translate([-dx, 0]) circle(mon_608[0] / 2 + tol); }
  hull() for (d = [0, dx]) mon_cil_y([x - d, mon_z_rod], mon_d_eje + 1, -60, 60);
}
// Labio sobre el riel de los bloques del motriz (auditoria 2026-10-25): con solo el de abajo, el NEMA (a 76 del riel), el
// rodillo y la banda colgaban de la una de 2 remaches a traccion (19-33 N por remache, 5.6-9.7 MPa contra 3). Abrazando
// el riel el momento lo toma el apoyo. 0.2 de luz sobre el riel (z 448.2) para montarlos deslizando en y; hasta x -98
// (la pata de la guia empieza en -97). Los 2 remaches siguen abajo (x -124 / -96): arriba, en -105, la una quedaba a
// 0.5 del eje motriz.
module mon_labio_sup(s) mon_caja([-135, s < 0 ? -mon_yo : 34, 448.2], [-98, s < 0 ? -34 : mon_yo, 451.2]);
// Bajada al retorno A (auditoria 2026-10-25, reemplaza a los colgantes mon_ret_a_m/_p): por fuera del riel (y 48.5-57.5)
// desde el bloque (z 426) hasta z 336, con el eje de A (Ø8 hasta y +-57) en una gota (se imprime sobre la cara -x: la
// punta queda arriba). Ancha alrededor del eje (hasta x -101) y a 45 grados hasta 18 de ancho (x -117): el tiron de A
// en x (10.3 N por lado con T = 20 N, a 82 de la raiz) da 1.7 MPa en z 426. El tiron hacia arriba de A (10 N) y el de
// abajo del motriz se anulan dentro del bloque; el de x (~20 N por bloque) lo toman los dos labios contra el riel.
// Al imprimir sobre la cara -x todo el perfil nace de la cama (el borde +x es el de arriba): sin voladizos.
module mon_bajada_a(s) mon_en_y(0, 0, s < 0 ? -57.5 : mon_yo, s < 0 ? -mon_yo : 57.5)
  polygon([[-135, 336], [-101, 336], [-101, 352], [-117, 368], [-117, 426.01], [-135, 426.01]]);
module mon_eje_a(s) mon_en_y(mon_ret[0][0], mon_ret[0][1], s < 0 ? -57.51 : mon_yo - 0.01, s < 0 ? -mon_yo + 0.01 : 57.51)
  mon_gota(mon_d_eje / 2 + tol);
// Casquillos en el eje de A, de y 29.6 a 48.4 (0.1 de luz contra el rodillo, que llega a 29.5, y contra la bajada):
// octogono de 14 entre caras con la gota del eje (punta arriba); se imprimen acostados sobre una cara, sin circulos en la cama
module mon_casq_a(s) mon_en_y(mon_ret[0][0], mon_ret[0][1], s < 0 ? -48.4 : 29.6, s < 0 ? -29.6 : 48.4) difference() {
  rotate(22.5) circle(d = 14 / cos(22.5), $fn = 8);
  rotate(90) mon_gota(mon_d_eje / 2 + tol);
}
module mon_rod_mot_m() difference() {
  union() {
    mon_caja([-135, -57.5, 426], [-85, -mon_yo, 456]);
    mon_caja([-135, -mon_yo, 429], [-85, -34, 432]);          // labio bajo el riel (2 remaches desde abajo)
    mon_labio_sup(-1);
    mon_bajada_a(-1);
  }
  mon_bolsillo(mon_x_mot, -1, 1);
  mon_eje_a(-1);
}
module mon_jaula_nema() difference() {
  union() {
    // aligerada: bloque del 608 solo de z 426 a 456, placa de fondo de 3 para la U, paredes de 3 y ventana en el costado
    mon_caja([-135, mon_yo, 426], [-85, 57.5, 456]);
    mon_caja([-135, 54.5, 416], [-85, 57.5, 466]);
    mon_caja([-135, 34, 429], [-85, mon_yo, 432]);
    mon_labio_sup(1);
    mon_bajada_a(1);
    difference() {
      mon_caja([-135, 57.5, 416], [-132, mon_y_nema, 466]);      // costado (cara de la cama)
      mon_caja([-136, 63, 424], [-131, 89, 458]);
    }
    mon_caja([-135, 57.5, 463], [-85, mon_y_nema, 466]);         // techo
    mon_caja([-135, 57.5, 416], [-85, mon_y_nema, 419]);         // piso
    mon_caja([-135, mon_y_nema - 4, 416], [-85, mon_y_nema, 466]); // placa del motor 50 x 50 x 4
  }
  mon_bolsillo(mon_x_mot, 1, 1);
  mon_eje_a(1);
  mon_en_y(mon_x_mot, mon_z_rod, mon_y_nema - 5, mon_y_nema + 1, 1) mon_gota(11.5);   // resalte Ø22 del NEMA
  for (dx = [-15.5, 15.5]) for (dz = [-15.5, 15.5]) mon_cil_y([mon_x_mot + dx, mon_z_rod + dz], 3.4, mon_y_nema - 5, mon_y_nema + 1);
}
// Tensor (auditoria 2026-10-25: con el 608 fijo la banda no se podia volver a tensar y la fluencia la afloja): el 608 corre
// en una ranura de x 86 a 90, solo hacia ADENTRO (pasado 90 los separadores entran en la E4: en 90 queda 0.5 de luz y en
// 86, 3.0). Se monta en 86 con la banda floja; un M3 autorroscante que baja desde la cara de arriba, inclinado
// mon_ten_tor[3] grados hacia +x, empuja el aro de afuera del 608 hacia +x (y algo hacia abajo) hasta el tope de la punta
// de la ranura en 90, la posicion funcional (ahi lo toca a ~21 grados del eje x). No va horizontal: la cara -x es la de
// la cama (seria un agujero chico en la primera capa) y entre ella y el 608 en 86 queda 1.1 mm; tampoco se puede
// ensanchar hacia -x (del lado -y el taco_2 llega a x 73). El piso baja de z 426 a 422 (5.8 bajo la ranura), porque el
// tornillo suma ~6 N hacia abajo a los ~8 N de la banda.
mon_ten_dx = 4;                          // recorrido de la corredera (x 86 a 90)
mon_ten_tor = [77, 52.2, 456, 12];       // tornillo de empuje: entrada (x, |y| = medio del 608, z) y grados desde la vertical
mon_ten_d_tor = 2.6;                     // MEDIR: agujero para el M3 autorroscante en PLA
module mon_ten_tornillo(s) translate([mon_ten_tor[0], s * mon_ten_tor[1], mon_ten_tor[2]]) rotate([0, 180 - mon_ten_tor[3], 0]) children();
module mon_rod_ten(s) difference() {
  union() {
    mon_caja([73.7, s < 0 ? -57.5 : mon_yo, 422], [105.8, s < 0 ? -mon_yo : 57.5, 456]);
    mon_caja([73.7, s < 0 ? -57.5 : 34, 448], [105.8, s < 0 ? -34 : 57.5, 451]);   // labio sobre el riel
    mon_caja([105.8, s < 0 ? -51.5 : mon_yo, 426], [119, s < 0 ? -mon_yo : 51.5, 448]);   // placa que sigue la punta del riel: de ahi cuelga E4
  }
  mon_bolsillo(mon_x_ten, s, 1, mon_ten_dx);
  mon_ten_tornillo(s) translate([0, 0, -1]) cylinder(d = mon_ten_d_tor, h = 20, $fn = 16);
}

// ----------------------------------------------------------------- rodillos de retorno: placas colgantes
module mon_colgante(c) let(r = c[6]) {
  multmatrix([[1, 0, 0, 0], [0, 0, 1, c[8]], [0, 1, 0, 0], [0, 0, 0, 1]]) linear_extrude(2.6) difference() {
    union() {
      if (c[0] == "mon_ret_b_m") {   // placa de 24 x 24 contra el bloque del taco_1, bajo el riel
        translate([c[3], 408]) square([c[4] - c[3], 24]);
        hull() { translate([c[3], 408]) square([c[4] - c[3], 2]); translate([c[1], c[2]]) circle(r); }
      } else {
        translate([c[3], 431]) square([c[4] - c[3], 12.8]);
        hull() { translate([c[3], 431]) square([c[4] - c[3], 2]); translate([c[1], c[2]]) circle(r); }
      }
    }
    translate([c[1], c[2]]) circle(d = mon_d_eje + 2 * tol);
  }
  // b_p: labio bajo el riel (z 429-432) desde la placa hasta y 34; en la cama queda parado sobre la placa
  if (c[0] == "mon_ret_b_p") mon_caja([c[3], 34, 429], [c[4], c[8] + 2.6, 432]);
}

// ----------------------------------------------------------------- FC-51
module mon_fc51() {
  mon_caja([-70, -51.5, 434], [-54, -mon_yo, 545]);               // columna en la cara exterior del riel -y (2 remaches de costado)
  // nervio (T): boca abajo la columna sola era una pared de 3 x 16 y 106 de alto (esbeltez 35); sobre las cabezas y
  // el pasillo de sus remaches (z <= 443)
  mon_caja([-63, -60, 447], [-61, -51.5, 545]);
  mon_caja([-70, -51.5, 540], [-42.9, 8, 545]);                   // brazo sobre la banda
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
  hull() for (x = [30, 10]) translate([x, 0, 636]) cylinder(d = 6.5, h = 20);   // MEDIR: rosca 1/4" de la webcam; ranura abierta a -x (sin circulo en la cama)
}

// ----------------------------------------------------------------- compuerta E4
mon_r_corte = 17.5;     // libre alrededor del tensor: rodillo 11 + banda 2 + separadores 4 + 0.5
// Salida Ø29 (coordinador, 2026-10-24): con Ø20 (la del visor) la moneda mas grande, de 26,7 mm, no pasa acostada.
module mon_embudo_solido() translate([mon_x_e4, 0, 420]) cylinder(h = 28, r1 = 16.5, r2 = 22.91, $fn = 72);
module mon_embudo_hueco() translate([mon_x_e4, 0, 419]) cylinder(h = 30, r1 = 14.5, r2 = 10 + 29 * 10 / 26, $fn = 72);
// Arranque de la pared -x de los canales (opinion externa, 2026-10-25). Boca abajo, el borde de arriba de esa pared
// (x 88.4-90, y -5.5..9.5), recortado por la vuelta de la banda en z ~411, nacia en el aire y quedaba suelto 10 mm hasta
// que el piso lo cosia con la pared +x. No se puede alargar hasta el cono: justo encima pasa la banda con sus separadores
// (en x 89.8, de z 412.2 a 421.6), y bajo la salida Ø29 pasa la moneda. Entonces:
//  - dos puntales (|y| 14-17: fuera de la salida y del paso de la moneda, que sale de la cola de la aleta hacia |y| > 4 y
//    baja) bajo la vuelta de la banda y paralelos a la recta tensor-B (boca abajo, a 40 grados de la vertical), que bajan
//    del anillo del cono (x ~98, z 420) a la pared -x;
//  - la pared -x se alarga en su plano hasta los puntales (por fuera del borde de los canales: la moneda no pasa de x 90) y
//    su borde de arriba baja en V a 45 grados desde ellos hasta un puente de 11 en z 403.4, sobre la cumbrera: boca abajo
//    crece de los puntales y nada empieza en el aire. Lo que pierde la pared en el medio (|y| < 9, de z 403.4 a 411) queda
//    bajo la cola de la aleta, por donde no pasa la moneda, y su punta -x (x >= 90.3) queda a >= 1.5 de los separadores.
// El piso en la cumbrera (z 401, y = 0) sigue empezando como puente de 30 entre las dos paredes, ahora las dos apoyadas
// (sus caras estan a 17-33 grados de la vertical); acortarlo seria rebajar la cumbrera bajo la aleta.
mon_x_pared = [88.4, 90];             // pared -x de los canales (105 - 16.6 .. 105 - 15)
mon_v_fondo = [5.5, 403.4];           // la V: medio ancho del puente de abajo y su z
mon_puntal_y = [14, 17];              // |y| de los puntales
function mon_zv(y) = mon_v_fondo[1] + max(0, abs(y) - mon_v_fondo[0]);
module mon_en_x(x0, x1) multmatrix([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) linear_extrude(x1 - x0) children();
// perfil (y, z) de la V, cerrado en z (abajo o arriba de ella)
module mon_v_2d(z) let(a = mon_puntal_y[1], v = mon_v_fondo)
  polygon([[-a, z], [-a, mon_zv(a)], [-v[0], v[1]], [v[0], v[1]], [a, mon_zv(a)], [a, z]]);
module mon_arranque() {
  // la pared -x hasta la V, desde 2 mm dentro de cada pared (ly 8 en A, 10 en B) hacia afuera del canal
  mon_en_x(mon_x_pared[0], mon_x_pared[1]) intersection() {
    mon_v_2d(370);
    union() for (L = [[mon_MA, 8], [mon_MB, 10]]) let(p = mon_pt(L[0], [0, L[1], -15]), q = mon_pt(L[0], [0, L[1], 40]))
      polygon([[p[1], p[2]], [q[1], q[2]], [q[1], 440], [p[1], 440]]);
  }
  // puntales: franja de 3 entre 16.5 y 19.5 de la recta tensor-B (el corte de la banda, a 17.5, le quita el primer mm)
  for (s = [-1, 1]) difference() {
    mon_en_y(0, 0, s < 0 ? -mon_puntal_y[1] : mon_puntal_y[0], s < 0 ? -mon_puntal_y[0] : mon_puntal_y[1]) intersection() {
      translate([mon_x_ten, mon_z_rod]) rotate(atan2(mon_ret[1][1] - mon_z_rod, mon_ret[1][0] - mon_x_ten))
        translate([0, mon_r_corte - 1]) square([100, 3]);
      translate([mon_x_pared[0], 380]) square([100 - mon_x_pared[0], 50]);
    }
    translate([mon_x_e4, 0, 400]) cylinder(r = 15.5, h = 20.5, $fn = 72);   // bajo el cono, fuera de la salida (r 14.5)
  }
}
module mon_e4() difference() {
  union() {
    difference() {   // placa de arriba (su cara de arriba, z 448, apoya en la cama: sin agujeros), sin las esquinas +x
      mon_caja([106.2, -44.5, 445], [137, 44.5, 448]);
      for (s = [-1, 1]) mon_caja([122, s < 0 ? -60 : 24, 444], [138, s < 0 ? -24 : 60, 449]);
    }
    mon_embudo_solido();
    mon_caja([120, -12, 398], [122, 12, 448]);                    // pared +x: une placa y canales
    mon_caja([120, -54.7, 415], [122, 54.7, 448]);                // ... y las placas laterales (sobre el techo a dos aguas del empalme de la viga, z <= 413.8)
    for (s = [-1, 1]) mon_caja([108, s < 0 ? -54.7 : 51.7, 428], [122, s < 0 ? -51.7 : 54.7, 448]);   // placas laterales: remaches de costado a las placas del tensor
    mon_caja([133.85, -20, 406], [136.85, 20, 445]);              // brida del SG90
    // canales A y B: se alargan hacia atras y se cortan en el plano y = 0 (la cumbrera entre los dos), asi el
    // arranque queda en una cara vertical comun y no hay tapas mirando hacia la cama
    intersection() { multmatrix(mon_MA) mon_u(30, 10, 1.6, -15, mon_LA); mon_caja([60, -100, 300], [160, 0, 500]); }
    intersection() { multmatrix(mon_MB) mon_u(30, 12, 1.6, -15, mon_LBu); mon_caja([60, 0, 200], [160, 100, 500]); }
    mon_arranque();                                               // puntales y pared -x hasta ellos
  }
  mon_embudo_hueco();
  mon_en_y(0, 0, -60, 60) mon_lazo(mon_r_corte);                 // por donde da la vuelta la banda (con separadores)
  mon_en_x(87, mon_x_pared[1] + 0.01) mon_v_2d(440);             // borde de arriba de la pared -x en V
  mon_caja([80, -30, 421.6], [96, 30, 450]);                      // lado -x del embudo: lo tapa el tensor (sin voladizo)
  mon_caja([93, -4.5, 413], [119.9, 4.5, 422.5]);                 // pasa el barril de la aleta bajo la salida
  mon_cil_x([0, 418], 8 + 2 * tol, 119, 124, $fn = 32);           // bisagra: el cubo Ø8 de la aleta gira en la pared +x
  mon_caja([133, -(mon_sg[1] / 2 + tol), 405], [138, mon_sg[1] / 2 + tol, 418 + mon_sg[2] / 2 + tol]);  // ventana abierta abajo
  for (s = [-1, 1]) mon_cil_x([s * 13.9, 418], 2, 132, 138);      // MEDIR: tornillos M2 de las alas del SG90
}
// Aleta (auditoria 2026-10-25): la que colgaba del pivote dejaba caer el 41-43 % de la salida al canal contrario y no
// tenia union con el SG90. Ahora sube del pivote DENTRO del embudo: en cada extremo (+-mon_reposo) su placa de 2 llega a
// la pared del cono del lado al que se inclina (0,8 de luz) y la moneda resbala por ella al canal del otro lado.
// Del lado -x la recorta la vuelta de la banda: como pasa por la vertical al girar, todo punto queda bajo la envolvente
// de los separadores (r 17) con 1 de luz (lazo r 18). Se imprime con el eje 20 grados de la vertical (mon_u_aleta, hacia
// la punta): la estria ciega abre en la cara de arriba y ese borde, que sigue al lazo, queda a <= 50 grados (desde
// x 106.9 una recta a 70 en la placa = 50 en la cama). La base es un disco Ø8.4 perpendicular a mon_u_aleta en x 101.
mon_u_aleta = 20;
module mon_libre_aleta(a) translate(mon_piv) rotate([-a, 0, 0]) translate(-mon_piv) {   // donde puede estar girada a:
  translate([mon_x_e4, 0, 419]) cylinder(h = 30, r1 = 14.5 - 0.8, r2 = 10 + 29 * 10 / 26 - 0.8, $fn = 72);   // hueco del embudo
  mon_caja([93.5, -4.2, 413.3], [119.4, 4.2, 422.2]);            // y ranura del barril, menos la luz
}
module mon_base_aleta() translate([101, 0, 418]) rotate([0, 90 - mon_u_aleta, 0]) children();   // marco de la cara de la cama
module mon_aleta_quieta() difference() {   // vertical; en el ensamble se gira mon_reposo
  intersection() {
    union() {
      difference() {
        intersection() {
          mon_caja([99.4, -1, 412], [119.4, 1, 450]);            // placa de 2 (s = z - 418)
          mon_libre_aleta(mon_reposo);
          mon_libre_aleta(-mon_reposo);
          mon_libre_aleta(0);                                    // la cola (s < 0) llega mas abajo en la vertical
        }
        mon_en_y(0, 0, -60, 60) mon_lazo(mon_d_rod / 2 + 2 + mon_sep_alto + 1);   // vuelta de la banda + 1
        mon_en_y(0, 0, -60, 60) polygon([[106.9, 432.8], [140, 432.8 + 2.747 * 33.1], [140, 600], [106.9, 600]]);   // a 70
      }
      mon_base_aleta() cylinder(r = 4.2, h = 1.6, $fn = 48);     // base (cara de la cama), dentro de la ranura
      mon_cil_x([0, 418], 5, 100, 115, $fn = 32);                // barril
      translate([115, 0, 418]) rotate([0, 90, 0]) cylinder(h = 3, r1 = 2.5, r2 = 4, $fn = 32);   // al cubo sin voladizo
      mon_cil_x([0, 418], 8, 118, 126.4, $fn = 32);              // cubo: gira en el Ø8,4 de la pared +x
    }
    mon_base_aleta() translate([-60, -60, 0]) cube(120);         // nada debajo de la base
  }
  // shortcut: estria lisa a presion (como alm_obturador); si patina, pegar el brazo simple del SG90 en la cara +x
  mon_cil_x([0, 418], mon_estria[0], 126.4 - mon_estria[1] - 0.1, 127, $fn = 32);
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
  else if (n == "mon_casq_a_m") mon_casq_a(-1);
  else if (n == "mon_casq_a_p") mon_casq_a(1);
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
  else if (n == "mon_guia_m") rotate([-90, 0, 0]) children();    // la cara exterior de la pared en la cama
  else if (n == "mon_guia_p") rotate([90, 0, 0]) children();
  // acostados sobre la cara de la placa (2,6 de alto): de pie sobre la tira de arriba eran 107 de alto sobre 2,6 de
  // base (2026-10-24). En la cama quedan sus agujeros de costado (b_m 2, b_p ninguno: van por el labio);
  // el labio de b_p queda parado sobre la placa. Los casquillos de A van como estan (acostados sobre una cara).
  else if (len([for (c = mon_colg) if (c[0] == n) 1]) > 0)
    rotate([n == "mon_ret_b_p" ? -90 : 90, 0, 0]) children();
  else if (n == "mon_aleta") rotate([0, mon_u_aleta - 90, 0]) translate(mon_piv) rotate([-mon_reposo, 0, 0]) translate(-mon_piv) children();   // sobre su base: la estria abre arriba
  else if (n == "mon_canal_b") rotate([90, 0, 0]) multmatrix(mon_inv(mon_MB)) children();
  else children();
}

// ----------------------------------------------------------------- lo que se mueve
// la banda: envolvente del lazo (convexo: los 4 rodillos quedan en el casco) de 2 de banda + 4 de separadores, desde la
// cara de los rodillos (la banda corre sobre la cima de los rodillos y la bancada, las dos en z 450)
mon_rodillos = concat([[mon_x_mot, mon_z_rod], [mon_x_ten, mon_z_rod]], mon_ret);
module mon_lazo(r) hull() for (p = mon_rodillos) translate(p) circle(r, $fn = 64);
module mon_barrido(n) {
  if (n == "mon_aleta") difference() {
    for (a = [-mon_reposo:2.5:mon_reposo + 0.1]) mon_aleta_en(a);   // pasa por 0 (la vertical, lo mas cerca de la banda)
    mon_cil_x([0, 418], mon_estria[0] + 0.3, 122, 127);         // la estria del SG90 sobre la que gira
  }
  else if (n == "mon_vuelta_banda") difference() {
    mon_en_y(0, 0, -mon_banda[1] / 2, mon_banda[1] / 2) difference() {
      mon_lazo(mon_d_rod / 2 + 2 + mon_sep_alto);
      mon_lazo(mon_d_rod / 2);
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
    // ejes de retorno (fijos): el de A cuelga de las bajadas de los bloques del motriz (hasta y +-57), el de B llega al
    // colgante exterior
    for (i = [0 : 1]) mon_cil_y(mon_ret[i], mon_d_eje, [-57, -32.3][i], [57, 52][i]);
    // M3 x 16 de empuje del tensor, a tope con el 608 en 90 (la punta a 0.3 del aro)
    for (s = [-1, 1]) mon_ten_tornillo(s) { translate([0, 0, -3]) cylinder(d = 2.5, h = 16, $fn = 16); translate([0, 0, -6]) cylinder(d = 5.5, h = 3, $fn = 16); }
    mon_cil_y([mon_x_mot, mon_z_rod], mon_d_eje, -57.5, mon_acople[2]);            // eje motriz hasta el acople
    mon_cil_y([mon_x_ten, mon_z_rod], mon_d_eje, -57.5, 57.5);
    for (x = [mon_x_mot, mon_x_ten]) for (s = [-1, 1])
      mon_cil_y([x, mon_z_rod], mon_608[0], s > 0 ? 48.7 : -55.7, s > 0 ? 55.7 : -48.7);   // 608
    mon_cil_y([mon_x_mot, mon_z_rod], mon_acople[0], mon_acople[2] - mon_acople[1] / 2, mon_acople[2] + mon_acople[1] / 2);
    mon_cil_y([mon_x_mot, mon_z_rod], 5, mon_acople[2] + mon_sep_nema, mon_y_nema + mon_sep_nema);   // eje del motor (24): 9.5 dentro del acople
  }
  color("#333") mon_caja([mon_x_mot - mon_nema / 2, mon_y_nema + mon_sep_nema, mon_z_rod - mon_nema / 2],
                         [mon_x_mot + mon_nema / 2, mon_y_nema + mon_sep_nema + mon_nema_l, mon_z_rod + mon_nema / 2]);
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

// Paso de los ejes Ø8 de los rodillos motriz (x -110) y tensor (x 90) por los rieles de la estructura (eje z 439,
// dentro del tubo de z 432 a 448): Ø9 de lado a lado (coordinador, 2026-10-24; lo pidio el agente de monedas).
// El del tensor es una ranura de 9 x 13 (x 83.5-96.5; 2026-10-25): el 608 corre de 86 a 90 (mon_rod_ten). Va como 5 Ø9
// cada 1 mm (la lista tiene que ser literal); entre uno y otro la pared queda 0.03 adentro.
AGUJEROS_MON = [[[-110, -60, 439], [-110, 60, 439], 9],
  [[86, -60, 439], [86, 60, 439], 9], [[87, -60, 439], [87, 60, 439], 9], [[88, -60, 439], [88, 60, 439], 9],
  [[89, -60, 439], [89, 60, 439], 9], [[90, -60, 439], [90, 60, 439], 9]];
