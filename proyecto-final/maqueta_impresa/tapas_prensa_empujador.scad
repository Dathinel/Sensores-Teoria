// =====================================================================================
// Subsistema "tapas_prensa_empujador" (prefijo tap_): ESCAPE DE TAPAS, PRENSA, EMPUJADOR y SENSOR
// INTERIOR, todo en PLA y colgado del portico impreso (viga 16 x 16 con eje en y -40.5, z 400; columna
// +x en (315, -40.5)). Cada pieza en su lugar del mundo (mm, z = 0 el piso); maqueta.scad resta los
// agujeros de los remaches de REM_TAP. Geometria funcional tomada del visor (app/visor3d/piezas/
// linea_vasos.js) SIN mover: ejes del tubo (200,-100) y de la prensa (280,-100), cabezal en z 225,
// piston abajo en z 229 con carrera 13, paleta en x 360 (reposo y -55, fin y -122.5, borde abajo z 138),
// cara del VL53L0X interior en (40, -100, 227).
//
// Lo que cambia respecto al visor (solo soportes):
//  - tubo de acrilico + cabezal  -> una sola pieza impresa (tap_tubo); cuelga del anillo de la
//    abrazadera del servo apoyado en el hombro del cabezal (gravedad) y la de arriba lo centra.
//  - colgante de aluminio 12x12  -> tap_colgante (poste 10 x 12 + escuadra remachada abajo y en la
//    cara -y de la viga). Las abrazaderas lo abrazan con dos orejas y un remache de lado a lado.
//  - placa de aluminio de la prensa -> tap_pre_placa (6 mm) con los separadores del MG996R
//    integrados (tetones de 23.5: la placa ahora apoya en la viga en y -48.7 en vez de -55).
//  - limitador de fuerza y collar de la prensa: no van. El resorte de retorno apoya entre el buje y
//    la horquilla del rodillo; plato y horquilla van a presion (y pegados) en el vastago.
//  - empujador: bloque de varillas remachado a la cara +x de la columna; placa del servo colgada del
//    bloque (no puede ir a la columna: ahi esta el empalme e_F5-P2_1, z 181..229).
// Uniones que NO son remaches: servos con sus tornillos (agujeros guia MEDIR), leva y manivela a los
// cuernos de disco con los tornillos del cuerno, pernos de acero (Ø2 dedos, Ø3 rodillo, M4 biela).
// =====================================================================================

// ----------------------------------------------------------------- medidas a confirmar (MEDIR)
tap_guia_servo = 3.0;      // MEDIR: agujero guia de los tornillos de los servos en el plastico
tap_guia_cuerno = 2.0;     // MEDIR: agujeros de los tornillos del cuerno de disco del MG996R (a r 8.4)
tap_r_cuerno = 8.4;        // MEDIR: radio de esos agujeros (visor: 0.42 x brazo de 20)
tap_vl53 = [13, 25, 1.6];  // MEDIR: placa GY-530 (x, y, espesor); agujeros M2 a +-10 en y
tap_largo_vastago = 79;    // MEDIR/cortar: vastago Ø8 de z 232 a 311
tap_largo_varillas = 102.5;// MEDIR/cortar: varillas Ø8 de y -135.5 a -33
tap_resorte = [15, 30];    // MEDIR: resorte de retorno (diametro exterior, largo libre >= 30 para que empuje)

// ----------------------------------------------------------------- posiciones funcionales (no mover)
tap_tubo_c = [200, -100];     // eje del tubo de tapas
tap_z_cab = 225;              // cara de abajo del cabezal (13 sobre la boca del vaso, 212)
tap_pre_c = [280, -100];      // eje de la prensa
tap_z_plato = 229;            // cara de abajo del plato con el piston arriba
tap_z_leva = 339.5;           // eje del MG996R de la prensa
tap_exc = 6.5;                // excentricidad (carrera 13)
tap_emp_x = 360;              // paleta del empujador
tap_emp_r = 33.75;            // manivela
tap_emp_L = 50;               // biela
tap_emp_ys = -55 - tap_emp_r + tap_emp_L;   // eje del servo del empujador: -38.75
tap_sens = [40, -100, 227];   // cara del VL53L0X interior (mira -z)

// SG90 del escape (visor: eje en (0,-58) del tubo, cara de las orejas 29.5 sobre el cabezal, invertido)
tap_sg_eje = [200, -158];
tap_sg_z = 254.5;
tap_a0 = 14.2;                                   // grados del cuerno en reposo (A sostiene)
tap_pinA = [200 + 12.4 * cos(tap_a0), -158 + 12.4 * sin(tap_a0)];
tap_pinB = [200 - 12.4 * cos(tap_a0), -158 - 12.4 * sin(tap_a0)];

module tap_caja(a, b) translate(a) cube(b - a);
module tap_cil_y(x, z, y0, y1, r) translate([x, y0, z]) rotate([-90, 0, 0]) cylinder(r = r, h = y1 - y0);
module tap_cil_z(x, y, z0, z1, r, fn = 40) translate([x, y, z0]) cylinder(r = r, h = z1 - z0, $fn = fn);
module tap_anillo(z0, z1, ri, re) translate([tap_tubo_c[0], tap_tubo_c[1], z0])
  difference() { cylinder(r = re, h = z1 - z0, $fn = 96); translate([0, 0, -1]) cylinder(r = ri, h = z1 - z0 + 2, $fn = 96); }

PIEZAS_TAP = [
  "tap_tubo", "tap_abr_servo", "tap_abr_sup", "tap_colgante", "tap_dedo_a", "tap_dedo_b",
  "tap_pre_placa", "tap_pre_leva", "tap_pre_buje", "tap_pre_plato", "tap_pre_horquilla", "tap_pre_rodillo",
  "tap_emp_soporte", "tap_emp_placa_servo", "tap_emp_carro", "tap_emp_paleta", "tap_emp_manivela", "tap_emp_biela",
  "tap_sens_porta"];

// [nombre, agarre, cabeza, eje]  (agarre = suma de lo que atraviesa; 0,2 por cada holgura)
REM_TAP = [
  // abrazaderas -> poste del colgante: oreja 4 + 0,2 + poste 10 + 0,2 + oreja 4
  ["r_tap_abr_servo_1", 18.4, [209.2, -44.7, 245.5], [-1, 0, 0]],
  ["r_tap_abr_servo_2", 18.4, [209.2, -44.7, 253.0], [-1, 0, 0]],
  ["r_tap_abr_sup_1", 18.4, [209.2, -44.7, 289.5], [-1, 0, 0]],
  ["r_tap_abr_sup_2", 18.4, [209.2, -44.7, 296.5], [-1, 0, 0]],
  // colgante -> viga: cara -y (oreja 4 + 0,2 + pared 1,6) y cara de abajo (ala 4 + 0,2 + 1,6)
  ["r_tap_colg_1", 5.8, [188, -52.7, 400], [0, 1, 0]],
  ["r_tap_colg_2", 5.8, [212, -52.7, 400], [0, 1, 0]],
  ["r_tap_colg_3", 5.8, [188, -40.5, 387.8], [0, 0, 1]],
  ["r_tap_colg_4", 5.8, [212, -40.5, 387.8], [0, 0, 1]],
  // placa de la prensa -> cara -y de la viga: placa 6 + 0,2 + 1,6
  ["r_tap_pre_placa_1", 7.8, [242, -54.7, 400], [0, 1, 0]],
  ["r_tap_pre_placa_2", 7.8, [258, -54.7, 400], [0, 1, 0]],
  ["r_tap_pre_placa_3", 7.8, [274, -54.7, 400], [0, 1, 0]],
  // buje -> placa: ala 4 + 0,2 + placa 6 (la una sale al aire detras de la placa, bajo la viga)
  ["r_tap_pre_buje_1", 10.2, [263, -58.9, 267], [0, 1, 0]],
  ["r_tap_pre_buje_2", 10.2, [297, -58.9, 267], [0, 1, 0]],
  // soporte del empujador -> cara +x de la columna: 4 + 0,2 + 1,6
  ["r_tap_emp_sop_1", 5.8, [327.2, -40.5, 278], [-1, 0, 0]],
  ["r_tap_emp_sop_2", 5.8, [327.2, -40.5, 298], [-1, 0, 0]],
  ["r_tap_emp_sop_3", 5.8, [327.2, -40.5, 318], [-1, 0, 0]],
  // placa del servo -> bloque de varillas: ala 3 + 0,2 + bloque 16
  ["r_tap_emp_srv_1", 19.2, [333.2, -42, 248.8], [0, 0, 1]],
  ["r_tap_emp_srv_2", 19.2, [333.2, -36, 248.8], [0, 0, 1]],
  // carro -> paleta: lengueta 4 + 0,2 + brazo 4
  ["r_tap_emp_pal_1", 8.2, [347, -61.2, 244], [0, 1, 0]],
  ["r_tap_emp_pal_2", 8.2, [373, -61.2, 244], [0, 1, 0]],
  // porta del sensor -> cara de abajo de la viga: brazo 6 + 0,2 + 1,6
  ["r_tap_sens_1", 7.8, [38, -43.5, 385.8], [0, 0, 1]],
  ["r_tap_sens_2", 7.8, [38, -37.5, 385.8], [0, 0, 1]],
];

// ================================================================= piezas
module tap_pieza(n) {
  // ---------------- escape de tapas
  if (n == "tap_tubo") difference() {   // cabezal Ø90 x 16 + tubo Ø85.2/Ø82 (pared 1.6: solo guia) hasta z 300 (alto total 75)
    union() { tap_anillo(tap_z_cab, tap_z_cab + 16, 41, 45); tap_anillo(tap_z_cab + 16, tap_z_cab + 75, 41, 42.6); }
    // sin ventanas en el tubo (2026-10-24): una tapa ladeada podia trabarse en el borde; no valen 11 g
    tap_caja([208.5, -150, 228], [215.5, -130, 232]);      // ranura del dedo A (x +12, z +3..+7)
    tap_caja([184.5, -150, 234.6], [191.5, -130, 238]);    // ranura del dedo B (x -12, z +9.6..+13)
  }
  else if (n == "tap_abr_servo") difference() {
    union() {
      tap_anillo(241.2, 257.5, 43.2, 46.2);                // apoya en el hombro del cabezal (z 241, re 45): de ahi cuelga el tubo
      tap_caja([190.8, -57, 241.2], [194.8, -40.7, 257.5]);// orejas a los lados del poste
      tap_caja([205.2, -57, 241.2], [209.2, -40.7, 257.5]);
      tap_caja([176, -168, 254.5], [213, -147, 257.5]);    // placa del SG90 (encima de sus orejas)
      tap_caja([190, -148, 254.5], [210, -144, 257.5]);
    }
    tap_caja([183, -164.3, 250], [206.3, -151.7, 260]);    // ventana del cuerpo
    for (x = [180.9, 208.4]) tap_cil_z(x, tap_sg_eje[1], 250, 260, 1.0);   // tornillos del SG90 (MEDIR)
  }
  else if (n == "tap_abr_sup") union() {
    tap_anillo(292, 300, 43.2, 46.2);                    // solo centra el tubo: 8 de alto bastan
    tap_caja([190.8, -57, 286], [194.8, -40.7, 300]);
    tap_caja([205.2, -57, 286], [209.2, -40.7, 300]);
  }
  else if (n == "tap_colgante") union() {
    tap_caja([195, -52.7, 241.5], [205, -40.7, 387.8]);    // poste entre las orejas
    tap_caja([184, -52.7, 387.8], [216, -32.7, 391.8]);    // ala bajo la viga
    tap_caja([184, -52.7, 391.8], [216, -48.7, 406]);      // oreja en la cara -y de la viga
  }
  else if (n == "tap_dedo_a") tap_dedo(12, 228.5, 231.5, tap_pinA, 0);
  else if (n == "tap_dedo_b") tap_dedo(-12, 235.1, 237.5, tap_pinB, -2 * 12.4 * sin(tap_a0));
  // ---------------- prensa
  else if (n == "tap_pre_placa") difference() {
    union() {
      tap_caja([235, -54.7, 257], [304, -48.7, 406]);
      tap_caja([240, -78.2, 330], [248.95, -54.7, 349]);   // separadores del MG996R (integrados)
      tap_caja([290.05, -78.2, 330], [299, -54.7, 349]);
    }
    tap_caja([282.2, -60, 385.6], [310, -40, 420]);         // brazo del nodo P2 (con su alero hasta z 386.2)
    // ventanas (ahorro de PLA): quedan costillas de 8 a los lados y 6 al centro, la banda del servo (z 322..357),
    // la del buje (257..277, con sus remaches) y la de arriba (392..406, con los remaches a la viga) enteras
    for (x0 = [243, 272]) { tap_caja([x0, -60, 277], [x0 + 24, -40, 322]); tap_caja([x0, -60, 357], [x0 + 24, -40, x0 < 250 ? 392 : 380]); }
    tap_caja([248.95, -60, 329.45], [290.05, -40, 349.55]); // ventana: el cuerpo llega a y -51.2
    for (x = [244.75, 294.25], dz = [-5, 5]) tap_cil_y(x, tap_z_leva + dz, -80, -60, tap_guia_servo / 2);
  }
  else if (n == "tap_pre_leva") difference() {   // disco Ø44 x 8 con el centro 6.5 sobre el eje (leva a 0 grados)
    tap_cil_y(tap_pre_c[0], tap_z_leva + tap_exc, -104, -96, 22);
    tap_cil_y(tap_pre_c[0], tap_z_leva, -105, -95, 1.5);
    for (a = [45:90:315]) tap_cil_y(tap_pre_c[0] + tap_r_cuerno * cos(a), tap_z_leva + tap_r_cuerno * sin(a), -105, -95, tap_guia_cuerno / 2);
  }
  else if (n == "tap_pre_buje") difference() {
    union() { tap_caja([272, -110, 259], [288, -58.9, 275]); tap_caja([258, -58.9, 259], [302, -54.9, 275]); }
    tap_cil_z(tap_pre_c[0], tap_pre_c[1], 258, 276, 4 + tol);   // guia del vastago (desliza)
  }
  else if (n == "tap_pre_plato") difference() {
    union() { tap_cil_z(tap_pre_c[0], tap_pre_c[1], tap_z_plato, tap_z_plato + 6, 31, 96); tap_cil_z(tap_pre_c[0], tap_pre_c[1], tap_z_plato + 6, 241, 9); }
    tap_cil_z(tap_pre_c[0], tap_pre_c[1], 232, 242, 4.1);
  }
  else if (n == "tap_pre_horquilla") difference() {
    union() {
      tap_caja([273, -107.2, 305], [287, -92.8, 311]);
      tap_caja([274, -107.2, 311], [286, -104.2, 324]);
      tap_caja([274, -95.8, 311], [286, -92.8, 324]);
    }
    tap_cil_z(tap_pre_c[0], tap_pre_c[1], 304, 312, 4.1);
    tap_cil_y(tap_pre_c[0], 318, -108, -92, 1.6);
  }
  else if (n == "tap_pre_rodillo") difference() {  // Ø12 x 8: toca la leva (abajo en z 324) con el piston arriba
    tap_cil_y(tap_pre_c[0], 318, -104, -96, 6);
    tap_cil_y(tap_pre_c[0], 318, -105, -95, 1.5 + tol);
  }
  // ---------------- empujador
  else if (n == "tap_emp_soporte") difference() {
    union() { tap_caja([323.2, -48.5, 252], [327.2, -32.5, 330]); tap_caja([327.2, -45, 252], [382, -33, 268]); }
    for (x = [345, 375]) tap_cil_y(x, 260, -46, -32, 4.1);
  }
  else if (n == "tap_emp_placa_servo") difference() {
    union() {
      tap_caja([337, -51.25, 221.7], [400, -26.25, 224.7]);
      tap_caja([337, -51.25, 224.7], [343, -26.25, 248.8]);
      tap_caja([329.4, -51.25, 248.8], [343, -26.25, 251.8]);
    }
    tap_caja([349.7, -49.05, 220], [391.3, -28.45, 226]);
    for (x = [345.75, 395.25], dy = [-5, 5]) tap_cil_z(x, tap_emp_ys + dy, 220, 226, tap_guia_servo / 2);
  }
  else if (n == "tap_emp_carro") difference() {
    union() {
      tap_caja([337, -64, 252], [383, -46, 268]);
      tap_caja([344, -61.2, 236], [350, -57.2, 252]);
      tap_caja([370, -61.2, 236], [376, -57.2, 252]);
    }
    for (x = [345, 375]) tap_cil_y(x, 260, -65, -45, 4 + tol);   // bujes (deslizan en las varillas)
    tap_cil_z(tap_emp_x, -55, 247, 269, 2.1);
  }
  else if (n == "tap_emp_paleta") difference() { union() {
    tap_caja([332, -57, 138], [388, -54, 193]);   // chapa de 3; 56 de ancho (no 60): libra los tacos de la banda que suben a z 141 en x 390..400
    tap_caja([344, -57, 193], [350, -53, 251.8]);
    tap_caja([370, -57, 193], [376, -53, 251.8]);
    tap_caja([344, -57, 228], [376, -53, 234]);
  }
    tap_caja([382, -58, 137], [389, -52, 143.5]);   // esquina: ahi pasan los tacos de la banda al dar la vuelta (z ~141, x 390..400)
  }
  else if (n == "tap_emp_manivela") difference() {
    union() {
      tap_cil_z(tap_emp_x, tap_emp_ys, 242.5, 247.5, 11);
      tap_caja([tap_emp_x - 5, tap_emp_ys, 242.5], [tap_emp_x + 5, tap_emp_ys + tap_emp_r, 247.5]);
      tap_cil_z(tap_emp_x, tap_emp_ys + tap_emp_r, 242.5, 247.5, 5);
    }
    tap_cil_z(tap_emp_x, tap_emp_ys, 242, 248, 1.5);
    for (a = [45:90:315]) tap_cil_z(tap_emp_x + tap_r_cuerno * cos(a), tap_emp_ys + tap_r_cuerno * sin(a), 242, 248, tap_guia_cuerno / 2);
    tap_cil_z(tap_emp_x, tap_emp_ys + tap_emp_r, 242, 248, 2.1);
  }
  else if (n == "tap_emp_biela") difference() {
    hull() for (y = [-55, -55 + tap_emp_L]) tap_cil_z(tap_emp_x, y, 248.5, 251.5, 4.5);
    for (y = [-55, -55 + tap_emp_L]) tap_cil_z(tap_emp_x, y, 248, 252, 2 + tol);   // giran en los pernos M4
  }
  // ---------------- sensor interior
  else if (n == "tap_sens_porta") difference() {
    union() {
      tap_caja([33, -104, 385.8], [43, -32.7, 391.8]);     // brazo bajo la viga (entre los tacos de x 20 y 58), 6 de alto
      tap_caja([33, -104, 232.8], [39, -98, 385.8]);       // poste 6 x 6 (x < 45: fuera del almacen)
      tap_caja([33, -112.5, 229.8], [44.8, -87.5, 232.8]); // porta: la placa GY-530 va debajo con 2 M2
    }
    for (y = [-110, -90]) tap_cil_z(tap_sens[0], y, 229, 234, 1.1);
  }
}

// Dedo del escape: 6 de ancho, cola de 10 con ranura en x para el perno del cuerno (Ø2 + 2 tol).
// dy: corrimiento en reposo (el B esta retirado 6.08 mm: no toca la pila).
module tap_dedo(xd, z0, z1, pin, dy) difference() {
  union() {
    tap_caja([200 + xd - 3, -154.96 + dy, z0], [200 + xd + 3, -133.5 + dy, z1]);
    tap_caja([200 + xd - 5, pin[1] - 3, z0], [200 + xd + 5, pin[1] + 3, z1]);
  }
  tap_caja([pin[0] - 3.8, pin[1] - 1 - tol, z0 - 1], [pin[0] + 3.8, pin[1] + 1 + tol, z1 + 1]);
}

// giro para imprimir (lo que queda abajo apoya en la cama)
module tap_a_cama(n) {
  if (n == "tap_abr_servo" || n == "tap_abr_sup" || n == "tap_emp_carro") rotate([180, 0, 0]) children();   // abr_sup boca abajo: anillo y orejas apoyan en z 300
  else if (n == "tap_colgante" || n == "tap_emp_placa_servo" || n == "tap_emp_paleta") rotate([90, 0, 0]) children();
  else if (n == "tap_pre_placa" || n == "tap_pre_leva" || n == "tap_pre_buje") rotate([-90, 0, 0]) children();
  else if (n == "tap_pre_rodillo") rotate([90, 0, 0]) children();
  else if (n == "tap_emp_soporte" || n == "tap_sens_porta") rotate([0, -90, 0]) children();
  else children();
}

// ================================================================= comprado (forma aproximada)
// Servo en su marco: eje en el origen, cara de abajo de las orejas en z 0, eje hacia +z (electronica.js).
module tap_servo(L, W, alto, zP, lP, eP, dE, rR, hR, rC, tope) {
  xc = -(L / 2 - dE);
  translate([xc - L / 2, -W / 2, -zP]) cube([L, W, alto]);
  translate([xc - lP / 2, -W / 2, 0]) cube([lP, W, eP]);
  translate([0, 0, alto - zP]) cylinder(r = rR, h = hR);
  translate([0, 0, alto - zP + hR]) cylinder(r = rC, h = tope - (alto - zP + hR));
}
module tap_mg996r() { tap_servo(40.7, 19.7, 36.9, 27, 54, 2.5, 9.85, 6.5, 3, 5, 17.8); translate([0, 0, 16]) cylinder(r = 11, h = 1.8); }

module tap_comprados() {
  // SG90 del escape, invertido; cuerno doble a 14.2 grados y pernos Ø2 hasta los dedos
  translate([tap_sg_eje[0], tap_sg_eje[1], tap_sg_z]) rotate([180, 0, 0]) tap_servo(22.5, 11.8, 22.7, 15.9, 32.2, 2.5, 5.9, 5.9, 4, 3.6, 15);
  translate([tap_sg_eje[0], tap_sg_eje[1], tap_sg_z - 15]) rotate([0, 0, tap_a0]) {
    hull() { cylinder(r = 2.75, h = 1.8); translate([16, 0, 0]) cylinder(r = 1.57, h = 1.8); }
    hull() { cylinder(r = 2.75, h = 1.8); translate([-13.6, 0, 0]) cylinder(r = 1.57, h = 1.8); }
  }
  tap_cil_z(tap_pinA[0], tap_pinA[1], 229.5, 240.4, 1.0, 16);
  tap_cil_z(tap_pinB[0], tap_pinB[1], 236, 240.4, 1.0, 16);
  // pila de 10 tapas (ala Ø78 x 3.5 + tapon Ø59.6 de 6), la de abajo en el dedo A (z 231.5), paso 6.2
  for (k = [0:9]) let(z = 231.5 + 6.2 * k) {
    tap_cil_z(tap_tubo_c[0], tap_tubo_c[1], z, z + 3.5, 39, 96);
    tap_cil_z(tap_tubo_c[0], tap_tubo_c[1], z - 6, z, 29.8, 96);
  }
  // MG996R de la prensa: eje hacia -y, orejas en y -78.2; cuerno de disco hasta y -96
  translate([tap_pre_c[0], -78.2, tap_z_leva]) rotate([90, 0, 0]) tap_mg996r();
  tap_cil_z(tap_pre_c[0], tap_pre_c[1], 232, 232 + tap_largo_vastago, 4);        // vastago Ø8
  translate([tap_pre_c[0], tap_pre_c[1], 275]) difference() { cylinder(r = tap_resorte[0] / 2, h = 30); translate([0, 0, -1]) cylinder(r = tap_resorte[0] / 2 - 2, h = 32); }
  tap_cil_y(tap_pre_c[0], 318, -107.5, -92.5, 1.5, 16);                           // eje del rodillo Ø3
  // MG996R del empujador: eje vertical, cuerpo hacia +x, orejas en z 224.7
  translate([tap_emp_x, tap_emp_ys, 224.7]) rotate([0, 0, 180]) tap_mg996r();
  for (x = [345, 375]) tap_cil_y(x, 260, -33 - tap_largo_varillas, -33, 4);      // varillas Ø8
  tap_cil_z(tap_emp_x, -55, 248, 268, 2);                                         // perno M4 carro-biela
  tap_cil_z(tap_emp_x, tap_emp_ys + tap_emp_r, 242.5, 253, 2);                    // perno M4 manivela-biela
  tap_caja([334, -58.5, 144], [386, -57, 190]);                                   // goma de la paleta
  // VL53L0X interior (GY-530): chip con la cara en z 227
  tap_caja([tap_sens[0] - tap_vl53[0] / 2, tap_sens[1] - tap_vl53[1] / 2, 228], [tap_sens[0] + tap_vl53[0] / 2, tap_sens[1] + tap_vl53[1] / 2, 228 + tap_vl53[2]]);
  tap_caja([tap_sens[0] - 2.2, tap_sens[1] - 1.2, tap_sens[2]], [tap_sens[0] + 2.2, tap_sens[1] + 1.2, 228]);
}

// ================================================================= lo que se mueve (revisar.py barre cada uno)
// [pieza, [piezas que se mueven con ella]]. Lo comprado que se mueve con la parte (pernos, vastago, resorte,
// goma) se RESTA del barrido (esta quieto en su posicion de reposo en _comprados).
MOVILES_TAP = [
  ["tap_dedo_a", []],                                          // cuerno +-14.2 grados: el A sale 6.08 hacia -y
  ["tap_dedo_b", []],                                          // el B entra 6.08 hacia +y
  ["tap_pre_leva", ["tap_pre_rodillo", "tap_pre_plato"]],      // vuelta completa (el piston la sigue: la leva lo mueve)
  ["tap_pre_plato", ["tap_pre_horquilla", "tap_pre_rodillo", "tap_pre_leva"]], // piston: baja 13
  ["tap_emp_paleta", ["tap_emp_carro"]],                       // paleta + carro: y -55 -> -122.5
  ["tap_emp_manivela", ["tap_emp_biela", "tap_emp_paleta", "tap_emp_carro"]],   // manivela 0..180 + biela
];
tap_carrera_dedo = 2 * 12.4 * sin(tap_a0);   // 6.08

module tap_barrido(n) {
  if (n == "tap_dedo_a" || n == "tap_dedo_b") let(a = n == "tap_dedo_a", pin = a ? tap_pinA : tap_pinB)
    difference() {
      for (k = [0:12]) translate([0, (a ? -1 : 1) * tap_carrera_dedo * k / 12, 0]) tap_pieza(n);
      tap_cil_z(pin[0], pin[1], 225, 242, 1.1);              // su perno (va en la ranura)
    }
  else if (n == "tap_pre_leva") difference() {
    tap_cil_y(tap_pre_c[0], tap_z_leva, -104, -96, 22 + tap_exc);   // revolucion exacta del disco excentrico
    tap_cil_y(tap_pre_c[0], 318, -108, -92, 1.6);                     // eje del rodillo (lo sigue)
  }
  else if (n == "tap_pre_plato") difference() {
    for (k = [0:13]) translate([0, 0, -k]) { tap_pieza("tap_pre_plato"); tap_pieza("tap_pre_horquilla"); tap_pieza("tap_pre_rodillo"); }
    hull() for (z = [305, 318]) tap_cil_y(tap_pre_c[0], z, -108, -92, 1.6);           // eje del rodillo
    translate([tap_pre_c[0], tap_pre_c[1], 274]) cylinder(r = tap_resorte[0] / 2 + 0.1, h = 32);   // resorte
    tap_cil_z(tap_pre_c[0], tap_pre_c[1], 231.9, 232 + tap_largo_vastago + 0.1, 4.1);           // vastago (baja con el)
  }
  else if (n == "tap_emp_paleta") difference() {
    for (k = [0:27]) translate([0, -2.5 * k, 0]) { tap_pieza("tap_emp_paleta"); tap_pieza("tap_emp_carro"); }
    hull() for (y = [-55, -122.5]) tap_cil_z(tap_emp_x, y, 247, 269, 2.1);            // perno carro-biela
    hull() for (dy = [0, -67.5]) tap_caja([333.9, -58.6 + dy, 143.9], [386.1, -56.9 + dy, 190.1]);   // goma
  }
  else if (n == "tap_emp_manivela") difference() {
    for (t = [0:7.5:180]) let(px = tap_emp_r * sin(t), py = tap_emp_ys + tap_emp_r * cos(t),
                              yc = py - sqrt(tap_emp_L * tap_emp_L - px * px)) {
      translate([tap_emp_x, tap_emp_ys, 0]) rotate([0, 0, -t]) translate([-tap_emp_x, -tap_emp_ys, 0]) tap_pieza("tap_emp_manivela");
      hull() { tap_cil_z(tap_emp_x, yc, 248.5, 251.5, 4.5); tap_cil_z(tap_emp_x + px, py, 248.5, 251.5, 4.5); }
    }
    tap_cil_z(tap_emp_x, -55, 242, 269, 2.1);                         // pernos en reposo (se mueven con ella)
    tap_cil_z(tap_emp_x, tap_emp_ys + tap_emp_r, 242, 254, 2.1);
  }
}
