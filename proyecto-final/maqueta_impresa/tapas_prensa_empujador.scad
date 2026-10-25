// =====================================================================================
// Subsistema "tapas_prensa_empujador" (prefijo tap_): ESCAPE DE TAPAS, PRENSA, EMPUJADOR y SENSOR
// INTERIOR, todo en PLA y colgado del portico impreso (viga 16 x 16 con eje en y -40.5, z 400; columna
// +x en (315, -40.5)). Cada pieza en su lugar del mundo (mm, z = 0 el piso); maqueta.scad resta los
// agujeros de los remaches de REM_TAP. Geometria funcional tomada del visor (app/visor3d/piezas/
// linea_vasos.js) SIN mover: ejes del tubo (200,-100) y de la prensa (280,-100), cabezal en z 225,
// piston arriba en z 229 con carrera 14 (2026-10-25: con 13 el plato llegaba a 216 y la tapa asentada tiene el ala
// arriba en 215.5: no la apretaba), paleta en x 360 (reposo y -55, fin y -122.5, borde abajo z 138),
// cara del VL53L0X interior en (40, -100, 227).
//
// Lo que cambia respecto al visor (solo soportes):
//  - tubo de acrilico + cabezal  -> una sola pieza impresa (tap_tubo). El anillo de la abrazadera del servo queda ENCIMA
//    del hombro del cabezal: solo frena la subida, por gravedad no sostiene nada (2026-10-25). Al armar se sube el tubo
//    hasta que el hombro toque el anillo y se pegan con cianoacrilato (corona de ~500 mm2): de ese pegado cuelga el tubo
//    con la pila. La de arriba solo lo centra.
//  - colgante de aluminio 12x12  -> tap_colgante (poste 10 x 12 + escuadra remachada abajo y en la
//    cara -y de la viga). Las abrazaderas lo abrazan con dos orejas y un remache de lado a lado.
//  - placa de aluminio de la prensa -> tap_pre_placa (6 mm) con los separadores del MG996R
//    integrados (tetones de 23.5: la placa ahora apoya en la viga en y -48.7 en vez de -55), que siguen como
//    costillas hasta la viga, y remachada tambien a la columna t_F5-P2_2 (2026-10-25).
//  - limitador de fuerza y collar de la prensa: no van. El resorte de retorno apoya entre el buje y
//    la horquilla del rodillo; plato y horquilla van a presion (y pegados) en el vastago. La fuerza sobre la
//    tapa la da el apriete de 0.5 al final de la carrera (plato a 215, ala asentada a 215.5) contra la
//    rigidez de la estructura: no hay resorte que la limite. Si la tapa real pide mas (MEDIR), se pegan bajo el plato
//    los suplementos de 0,5 y 1 (tap_pre_suplemento_05/_10): mas apriete con la misma carrera.
//  - empujador: bloque de varillas remachado a la cara +x de la columna; placa del servo colgada del
//    bloque (no puede ir a la columna: ahi esta el empalme e_F5-P2_1, z 181..229).
//  - puntal del portico (2026-10-25, no esta en el visor): tubo 16 x 16 vertical en (226, -40.5) del tubo del piso
//    t_F6-F5_2 a la viga t_P1-P2_2, que sola flectaba 1,30 mm y con la holgura de las cajeras se asentaba hasta 3,3.
//    Dos tramos (tap_puntal_inf / _sup) con media union y remaches; ver tap_pieza.
// Uniones que NO son remaches: servos con sus tornillos (agujeros guia MEDIR), leva y manivela a los
// cuernos de disco con los tornillos del cuerno, pernos de acero (Ø2 dedos, Ø3 rodillo, M4 biela).
// =====================================================================================

// ----------------------------------------------------------------- medidas a confirmar (MEDIR)
tap_guia_servo = 3.0;      // MEDIR: agujero guia de los tornillos de los servos en el plastico
tap_guia_cuerno = 2.0;     // MEDIR: agujeros de los tornillos del cuerno de disco del MG996R (a r 8.4)
tap_r_cuerno = 8.4;        // MEDIR: radio de esos agujeros (visor: 0.42 x brazo de 20)
tap_l_cuerno = 3;          // MEDIR: lo que entra en el plastico el M2 autorroscante del cuerno (agujero ciego = esto + 1)
tap_l_sg90 = 3;            // MEDIR: lo que entra en el plastico el tornillo del SG90 (agujero ciego = esto + 1)
tap_vl53 = [13, 25, 1.6];  // MEDIR: placa GY-530 (x, y, espesor); agujeros M2 a +-10 en y
tap_largo_vastago = 79;    // MEDIR/cortar: vastago Ø8 de z 232 a 311
tap_largo_varillas = 102.5;// MEDIR/cortar: varillas Ø8 de y -135.5 a -33
// MEDIR: resorte de retorno [diametro exterior, largo libre, largo a bloque]. Instalado mide 30 con el piston arriba
// (horquilla 305 - buje 275) y 16 abajo: libre >= 38 (8 de precarga arriba) y a bloque <= 15; k de 0.15 a 0.3 N/mm
// (1.2 a 2.4 N arriba, 2 a 4 veces el peso del piston, 0.58 N; 3.3 a 6.6 N abajo, sobrado para el MG996R)
tap_resorte = [15, 38, 15];

// ----------------------------------------------------------------- posiciones funcionales (no mover)
tap_tubo_c = [200, -100];     // eje del tubo de tapas
tap_z_cab = 225;              // cara de abajo del cabezal (13 sobre la boca del vaso, 212)
tap_pre_c = [280, -100];      // eje de la prensa
tap_z_plato = 229;            // cara de abajo del plato con el piston arriba
tap_z_leva = 339.5;           // eje del MG996R de la prensa
tap_exc = 7;                  // excentricidad (carrera 14: el plato baja de 229 a 215)
tap_r_leva = tap_z_leva + tap_exc - 324;   // 22.5: con el piston arriba la leva toca el rodillo (arriba en z 324)
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
module tap_cil_y(x, z, y0, y1, r, fn = 40) translate([x, y0, z]) rotate([-90, 0, 0]) cylinder(r = r, h = y1 - y0, $fn = fn);
module tap_cil_z(x, y, z0, z1, r, fn = 40) translate([x, y, z0]) cylinder(r = r, h = z1 - z0, $fn = fn);
module tap_anillo(z0, z1, ri, re) translate([tap_tubo_c[0], tap_tubo_c[1], z0])
  difference() { cylinder(r = re, h = z1 - z0, $fn = 96); translate([0, 0, -1]) cylinder(r = ri, h = z1 - z0 + 2, $fn = 96); }

PIEZAS_TAP = [
  "tap_tubo", "tap_abr_servo", "tap_abr_sup", "tap_colgante", "tap_dedo_a", "tap_dedo_b",
  "tap_pre_placa", "tap_pre_leva", "tap_pre_buje", "tap_pre_plato", "tap_pre_horquilla", "tap_pre_rodillo",
  "tap_pre_suplemento_05", "tap_pre_suplemento_10",
  "tap_emp_soporte", "tap_emp_placa_servo", "tap_emp_carro", "tap_emp_paleta", "tap_emp_manivela", "tap_emp_biela",
  "tap_sens_porta", "tap_puntal_inf", "tap_puntal_sup"];

// [nombre, agarre, cabeza, eje]  (agarre = suma de lo que atraviesa; 0,2 por cada holgura)
REM_TAP = [
  // abrazaderas -> poste del colgante: oreja 4 + 0,2 + poste 10 + 0,2 + oreja 4. Desde -x (2026-10-25): por +x el pasillo de
  // 38 mm para meterlos (hasta x 247) lo cruza el puntal (x 218..234); la una sale en x 209.2 con 8,8 libres hasta el puntal
  ["r_tap_abr_servo_1", 18.4, [190.8, -44.7, 245.5], [1, 0, 0]],
  ["r_tap_abr_servo_2", 18.4, [190.8, -44.7, 253.0], [1, 0, 0]],
  ["r_tap_abr_sup_1", 18.4, [190.8, -44.7, 289.5], [1, 0, 0]],
  ["r_tap_abr_sup_2", 18.4, [190.8, -44.7, 296.5], [1, 0, 0]],
  // colgante -> cara de abajo de la viga: ala 4 + 0,2 + pared 1,6. En z (quedan de lado al imprimir sobre la cara -y).
  // Las patas se abren en y, a lo ancho de la cara: el hueco del tubo tiene chaflanes de 3 y su cara plana llega a
  // +-3,4 del eje, asi que el remache va a no mas de 3,4 - 2,45 (una) - 0,2 = 0,75 del eje (y -40.5). 2026-10-25: en
  // y -37.5 y -42.5 una pata caia sobre el chaflan (cara de salida 7,75 y 6,75 contra 5,8: no entraba o no trababa).
  // Solo 2: a x 193.3 / 206.7 la cabeza quedaba a 0,1 del poste (x 195..205) y no se puede empujar con el dedo
  ["r_tap_colg_1", 5.8, [187.5, -40.5, 387.8], [0, 0, 1]],
  ["r_tap_colg_2", 5.8, [212.5, -40.5, 387.8], [0, 0, 1]],
  // placa de la prensa -> cara -y de la viga: placa 6 + 0,2 + 1,6
  ["r_tap_pre_placa_1", 7.8, [242, -54.7, 400], [0, 1, 0]],
  ["r_tap_pre_placa_2", 7.8, [258, -54.7, 400], [0, 1, 0]],
  ["r_tap_pre_placa_3", 7.8, [274, -54.7, 400], [0, 1, 0]],
  // placa de la prensa -> cara -y de la columna t_F5-P2_2 (2026-10-25): sin ellos el momento de la prensa (la reaccion en
  // y -100, 51 delante de la placa) lo tomaban a traccion los 3 de z 400 con 6 de brazo (171 N cada uno con 60 N).
  // Sobre el eje de la columna (x 315: las patas se abren en x) y a 10 de los r_tap_emp_sop (z 278/298/318)
  ["r_tap_pre_col_1", 7.8, [315, -54.7, 265], [0, 1, 0]],
  ["r_tap_pre_col_2", 7.8, [315, -54.7, 288], [0, 1, 0]],
  ["r_tap_pre_col_3", 7.8, [315, -54.7, 308], [0, 1, 0]],
  ["r_tap_pre_col_4", 7.8, [315, -54.7, 345], [0, 1, 0]],
  // buje -> placa: ala 4 + 0,2 + placa 6 (la una sale al aire detras de la placa, bajo la viga)
  ["r_tap_pre_buje_1", 10.2, [263, -58.9, 267], [0, 1, 0]],
  ["r_tap_pre_buje_2", 10.2, [297, -58.9, 267], [0, 1, 0]],
  // soporte del empujador -> cara +x de la columna: 4 + 0,2 + 1,6
  ["r_tap_emp_sop_1", 5.8, [327.2, -40.5, 278], [-1, 0, 0]],
  ["r_tap_emp_sop_2", 5.8, [327.2, -40.5, 298], [-1, 0, 0]],
  ["r_tap_emp_sop_3", 5.8, [327.2, -40.5, 318], [-1, 0, 0]],
  // placa del servo -> bloque de varillas: ala 3 + 0,2 + bloque 16 (bloque alargado a y -28 para que quepan con 2 mm de pared)
  ["r_tap_emp_srv_1", 19.2, [332.2, -41.5, 248.8], [0, 0, 1]],   // a 9 entre centros: a 7 las cabezas se pisaban   // x 332.2: el alero del empalme e_F5-P2_1 llega a x 328.8
  ["r_tap_emp_srv_2", 19.2, [332.2, -32.5, 248.8], [0, 0, 1]],
  // carro -> paleta: una lengueta por FUERA de cada brazo, remache en x: 3 + 0,4 + brazo 6 (2026-10-25: la paleta queda
  // en la U de las dos lenguetas con 0,4 de juego; el remache la empuja contra la otra y con 9,2 el hombro quedaba a ras).
  // La una sale al hueco de 5 mm entre el brazo y la manivela (x 350..355 y 365..370); con una lengueta tambien por
  // dentro quedaba a 1,8 de la manivela. z 242.5 (no 244): la muesca del brazo +x para la biela empieza en z 247.5
  ["r_tap_emp_pal_1", 9.4, [340.8, -52.5, 242.5], [1, 0, 0]],
  ["r_tap_emp_pal_2", 9.4, [379.2, -52.5, 242.5], [-1, 0, 0]],
  // segundo remache por brazo (2026-10-25), 11,5 debajo: con uno solo la paleta giraba sobre el eje de los dos y el
  // giro lo frenaba el tope de los brazos a 4,5 del eje (550 N con el servo trabado). Lenguetas y brazos bajan a z 226
  ["r_tap_emp_pal_3", 9.4, [340.8, -53.2, 231], [1, 0, 0]],
  ["r_tap_emp_pal_4", 9.4, [379.2, -53.2, 231], [-1, 0, 0]],
  // porta del sensor -> cara de abajo de la viga: brazo 6 + 0,2 + 1,6
  // sobre el eje del tubo (chaflanes del hueco: ver el colgante), a 10 entre ejes; quedan 1,3 de pared a cada punta del taco (x 33..50)
  ["r_tap_sens_1", 7.8, [36.5, -40.5, 385.8], [0, 0, 1]],
  ["r_tap_sens_2", 7.8, [46.5, -40.5, 385.8], [0, 0, 1]],
  // puntal: silla de arriba -> costados de la viga (pared 4 + 0,2 + 1,6), uno por lado sobre el eje del tubo (z 400; las patas
  // se abren en x, a lo largo del tubo); silla de abajo -> cara +y del tubo del piso (z 10.6), solo por +y: el tramo de abajo
  // entra deslizando desde +y (ver tap_pieza)
  ["r_tap_punt_sup_1", 5.8, [226, -52.7, 400], [0, 1, 0]],
  ["r_tap_punt_sup_2", 5.8, [226, -28.3, 400], [0, -1, 0]],
  ["r_tap_punt_inf_1", 5.8, [226, -28.3, 10.6], [0, -1, 0]],
  // union del medio, desde +y: media maciza del tramo de abajo 7,8 + 0,2 + pared de 1,6 de la media caja del de arriba (la una
  // abre en su hueco: nada asoma por -y, donde a 0,2 esta el panel de luz de vasos, z 125..222)
  ["r_tap_punt_med_1", 9.6, [226, -32.5, 200], [0, -1, 0]],
  ["r_tap_punt_med_2", 9.6, [226, -32.5, 210], [0, -1, 0]],
];

// ================================================================= piezas
module tap_pieza(n) {
  // ---------------- escape de tapas
  if (n == "tap_tubo") difference() {   // cabezal Ø90 x 16 + tubo Ø85.2/Ø82 (pared 1.6: solo guia) hasta z 300 (alto total 75)
    union() {
      tap_anillo(tap_z_cab, tap_z_cab + 16, 41, 45); tap_anillo(tap_z_cab + 16, tap_z_cab + 75, 41, 42.6);
      // guias de los dedos por fuera del cabezal (2026-10-25): con solo la pared (4 mm) y 0.5 de juego el dedo A
      // cabeceaba 8.8 grados y la pila bajaba 1.3 en la punta. Hasta y -151.5: la cola (10 de ancho, no entra en la
      // ranura de 7) llega como mucho a -151.96 y hace de tope. De pie desde z 225, techo de la ranura = puente de 7.
      for (g = [[12, 233.7], [-12, 239.3]]) difference() {
        tap_caja([200 + g[0] - 5.5, -151.5, tap_z_cab], [200 + g[0] + 5.5, -138, g[1]]);
        tap_cil_z(tap_tubo_c[0], tap_tubo_c[1], tap_z_cab - 1, g[1] + 1, 41, 96);
      }
    }
    // sin ventanas en el tubo (2026-10-24): una tapa ladeada podia trabarse en el borde; no valen 11 g
    // ranuras con 0.2 de juego en z (2026-10-25): el dedo, por su peso, apoya en el piso de la ranura
    tap_caja([208.5, -152, 228.3], [215.5, -130, 231.7]);  // ranura del dedo A (x +12, z +3.3..+6.7)
    tap_caja([184.5, -152, 235.3], [191.5, -130, 237.3]);  // ranura del dedo B (x -12, z +10.3..+12.3)
  }
  else if (n == "tap_abr_servo") difference() {
    union() {
      // toca el hombro del cabezal (z 241, re 45; antes a 0,2): ahi se pegan con cianoacrilato al armar y de eso cuelga el
      // tubo. Encima del hombro el anillo solo frenaria la subida
      tap_anillo(241, 259.5, 43.2, 46.2);
      tap_caja([190.8, -57, 241], [194.8, -40.7, 259.5]);  // orejas a los lados del poste
      tap_caja([205.2, -57, 241], [209.2, -40.7, 259.5]);
      tap_caja([176, -168, 254.5], [213, -147, 259.5]);    // placa del SG90 (5 de espesor, encima de sus orejas)
      tap_caja([190, -148, 254.5], [210, -144, 259.5]);
    }
    tap_caja([183, -170, 250], [206.3, -151.7, 261]);      // ventana del cuerpo, abierta hacia -y: la cara que apoya (z 259.5) queda maciza
    // tornillos del SG90 (MEDIR): ciegos desde el lado del servo (abajo), tornillo + 1 de hondo; se imprime boca abajo
    for (x = [180.9, 208.4]) tap_cil_z(x, tap_sg_eje[1], 250, 254.5 + tap_l_sg90 + 1, 1.0);
  }
  else if (n == "tap_abr_sup") union() {
    tap_anillo(292, 300, 43.2, 46.2);                    // solo centra el tubo: 8 de alto bastan
    tap_caja([190.8, -57, 286], [194.8, -40.7, 300]);
    tap_caja([205.2, -57, 286], [209.2, -40.7, 300]);
  }
  else if (n == "tap_colgante") union() {
    tap_caja([195, -52.7, 241.5], [205, -40.7, 387.8]);    // poste entre las orejas
    tap_caja([183.3, -52.7, 387.8], [216.7, -32.7, 391.8]);  // ala bajo la viga (2 remaches en z sobre el eje del tubo; sin oreja en la cara -y)
  }
  else if (n == "tap_dedo_a") tap_dedo(12, 228.5, 231.5, tap_pinA, 0);
  // B de 1.6 (4 perimetros): entre el ala de la tapa 1 (arriba en 235) y la de la tapa 2 (abajo en 237.7) quedan 0.5 y 0.6
  else if (n == "tap_dedo_b") tap_dedo(-12, 235.5, 237.1, tap_pinB, -2 * 12.4 * sin(tap_a0));
  // ---------------- prensa
  else if (n == "tap_pre_placa") difference() {
    union() {
      tap_caja([235, -54.7, 257], [304, -48.7, 406]);
      // amarre a la columna (2026-10-25): hasta x 323 frente a la cara -y de t_F5-P2_2, por debajo del brazo del nodo P2
      // (z 367.4), con los 4 r_tap_pre_col. La placa gira contra la viga (arriba) y estos toman la traccion con 61 a 141 de brazo
      tap_caja([304, -54.7, 257], [323, -48.7, 367]);
      // pie de 8 hacia -y en la cara que apoya (de pie, 149 de alto): con las costillas el centro de masa caia 2,1 fuera de
      // la base de 6. Queda 0,2 bajo el buje (z 259)
      tap_caja([235, -62.7, 257], [323, -54.7, 258.8]);
      for (x0 = [240, 290.05]) {
        tap_caja([x0, -78.2, 330], [x0 + 8.95, -54.7, 349]);   // separadores del MG996R (integrados)
        // y siguen como costillas hasta la viga (2026-10-25): de pie, la placa sola entre el servo y la viga daba I 288 mm4 y
        // se abria entre capas al prensar. La de +x para en 385, bajo el brazo del nodo P2 (desde 385.6); la de -x sigue
        // hasta 393, ya frente a la viga (desde 392): parando en 391 quedaba la placa sola de 391 a 392 (I 850). Queda
        // debajo de las cabezas de r_tap_pre_placa (z 398.4) y de su pasillo
        tap_caja([x0, -78.2, 349], [x0 + 8.95, -54.7, x0 < 270 ? 393 : 385]);
        // cartela a 45 bajo cada separador: la placa se imprime DE PIE (z arriba) para que todos sus agujeros queden de lado
        translate([x0, 0, 0]) rotate([90, 0, 90]) linear_extrude(8.95) polygon([[-54.7, 306.5], [-54.7, 330], [-78.2, 330]]);
      }
    }
    tap_caja([282.2, -60, 385.6], [310, -40, 420]);         // brazo del nodo P2 (con su alero hasta z 386.2)
    // ventanas (ahorro de PLA): quedan 14 a los lados (ahi van separadores y costillas) y 6 al centro, la banda del servo (z 322..357),
    // la del buje (257..277, con sus remaches) y la de arriba (392..406, con los remaches a la viga) enteras
    // (de pie, cada ventana lleva techo a 45 grados: ningun puente)
    tap_ventana_xz([[249, 277], [266, 277], [266, 309.5], [257.5, 318], [249, 309.5]]);
    tap_ventana_xz([[272, 277], [290, 277], [290, 309], [281, 318], [272, 309]]);
    // las dos de arriba, entre las costillas (antes iban de x 243 a 296: les habrian cortado la raiz). Del lado de la columna
    // del medio el borde de abajo va a 45, paralelo al techo de la ventana del servo y 4.25 mas arriba (franja de 3 de espesor):
    // bajando hasta z 357 cortaban ese techo y la columna (x 266..272) nacia en el aire en z 366.6 (2026-10-25)
    tap_ventana_xz([[249, 357], [252.15, 357], [266, 370.85], [266, 380], [257.5, 388.5], [249, 380]]);
    tap_ventana_xz([[286.85, 357], [290, 357], [290, 371.5], [281, 380.5], [272.175, 371.675]]);
    // ventana del cuerpo del servo (llega a y -51.2) con techo a 45 encima
    tap_ventana_xz([[248.95, 329.45], [290.05, 329.45], [290.05, 349.55], [269.5, 370.1], [248.95, 349.55]]);
    for (x = [244.75, 294.25], dz = [-5, 5]) tap_cil_y(x, tap_z_leva + dz, -80, -60, tap_guia_servo / 2);
  }
  else if (n == "tap_pre_leva") difference() {   // disco Ø45 x 8 con el centro 7 sobre el eje (leva a 0 grados)
    tap_cil_y(tap_pre_c[0], tap_z_leva + tap_exc, -104, -96, tap_r_leva);
    // tornillos M2 del cuerno: ciegos desde la cara del cuerno (y -96), tornillo + 1 de hondo; se imprime con esa cara arriba
    for (a = [45:90:315]) tap_cil_y(tap_pre_c[0] + tap_r_cuerno * cos(a), tap_z_leva + tap_r_cuerno * sin(a), -96 - tap_l_cuerno - 1, -95, tap_guia_cuerno / 2);
  }
  else if (n == "tap_pre_buje") difference() {
    union() { tap_caja([272, -110, 259], [288, -58.9, 275]); tap_caja([258, -58.9, 259], [302, -54.9, 275]); }
    tap_cil_z(tap_pre_c[0], tap_pre_c[1], 258, 276, 4 + tol);   // guia del vastago (desliza)
  }
  else if (n == "tap_pre_plato") difference() {
    union() { tap_cil_z(tap_pre_c[0], tap_pre_c[1], tap_z_plato, tap_z_plato + 6, 31, 96); tap_cil_z(tap_pre_c[0], tap_pre_c[1], tap_z_plato + 6, 241, 9); }
    tap_cil_z(tap_pre_c[0], tap_pre_c[1], 232, 242, 4.1);
  }
  // suplementos del plato (2026-10-25): anillos de 0,5 y 1 (Ø62 como el plato) que se pegan bajo el plato (cinta doble faz
  // fina o una gota de cianoacrilato) para apretar mas la tapa SIN cambiar la carrera, despues de MEDIR la tapa real (cada
  // uno baja la cara del plato su espesor; se pueden apilar). NO van montados: aqui estan guardados, apilados en el piso
  // bajo la prensa, fuera de todo. Se imprimen planos; el agujero Ø8,2 (el del vastago) no es chico para la primera capa
  else if (n == "tap_pre_suplemento_05") tap_suplemento(0, 0.5);
  else if (n == "tap_pre_suplemento_10") tap_suplemento(0.5, 1.0);
  else if (n == "tap_pre_horquilla") difference() {
    union() {
      tap_caja([273, -107.2, 305], [287, -92.8, 311]);
      // brazos hasta z 328 (antigiro, 2026-10-25): abrazan el disco de la leva con 0.2 por lado en toda la carrera
      // (al ras del rodillo, en los puntos muertos el disco no entraba) y quedan 0.5 bajo el cuerno de disco
      tap_caja([274, -107.2, 311], [286, -104.2, 328]);
      tap_caja([274, -95.8, 311], [286, -92.8, 328]);
    }
    tap_cil_z(tap_pre_c[0], tap_pre_c[1], 304, 312, 4.1);
    tap_cil_y(tap_pre_c[0], 318, -108, -92, 1.6);
  }
  else if (n == "tap_pre_rodillo") difference() {  // Ø12 x 8: toca la leva (abajo en z 324) con el piston arriba
    // redondo y DE PIE (2026-10-25): el plano para la cama rodaba (1.83 vueltas por carrera) y quitaba 0.54 de carrera;
    // queda un agujero Ø3.4 en la cara de apoyo
    tap_cil_y(tap_pre_c[0], 318, -104, -96, 6, 60);
    tap_cil_y(tap_pre_c[0], 318, -105, -95, 1.5 + tol);
  }
  // ---------------- empujador
  else if (n == "tap_emp_soporte") difference() {
    union() { tap_caja([323.2, -48.5, 252], [327.2, -28, 330]); tap_caja([327.2, -45, 252], [382, -28, 268]); }   // hasta y -28: sitio para los 2 remaches de la placa del servo
    // varillas A PRESION (radio 4 - 0.05, 2026-10-25: con 8.4 cabeceaban 1.35 grados y la punta caia 2 mm), ciegas hasta
    // 0.2 detras de la punta (y -33): hacen de tope al meterlas y la cara que apoya (+y) queda maciza
    for (x = [345, 375]) tap_cil_y(x, 260, -46, -33 + 0.2, 4 - 0.05);
  }
  else if (n == "tap_emp_placa_servo") difference() {
    union() {
      tap_caja([337, -50, 221.7], [400, -26.25, 224.7]);       // placa: desde y -50 (las orejas del servo llegan a -48.6); libra los brazos de la paleta
      tap_caja([335.5, -47.5, 224.7], [340.5, -26.25, 248.8]); // alma: libra la lengueta del carro (x 340.8) y las cabezas de sus remaches (x 332.2)
      tap_caja([327.5, -47.5, 248.8], [340.5, -26.25, 251.8]); // ala bajo el bloque
    }
    // ventana del cuerpo abierta hacia -y (el marco de 2,2 de ese lado no sujetaba nada): impresa sobre la cara +y no hay puente
    tap_caja([349.7, -60, 220], [391.3, -28.45, 226]);
    for (x = [345.75, 395.25], dy = [-5, 5]) tap_cil_z(x, tap_emp_ys + dy, 220, 226, tap_guia_servo / 2);
  }
  else if (n == "tap_emp_carro") difference() {
    union() {
      tap_caja([337, -64, 252], [383, -46, 268]);
      for (x0 = [340.8, 376.2]) {
        tap_caja([x0, -57, 236], [x0 + 3, -48, 252]);     // lenguetas (9 en y) por fuera de cada brazo
        // bajan a z 226 para el 2.o remache (z 231): 7,6 en y (1,6 de pared al agujero); hasta y -49.4 libran el MG996R
        // (cuerpo desde y -48.6, hasta z 234.6) y estan sobre su placa (arriba en z 224.7)
        tap_caja([x0, -57, 226], [x0 + 3, -49.4, 236]);
      }
    }
    for (x = [345, 375]) tap_cil_y(x, 260, -65, -45, 4 + tol);   // bujes (deslizan en las varillas)
    tap_cil_z(tap_emp_x, -55, 247, 266, 2.1);                     // perno de la biela: ciego desde abajo (arriba al imprimir boca abajo), para 2 mm antes de la cara que apoya
    // bolsillos de 2 donde entran los brazos de la paleta: sin ellos la paleta giraba libre sobre sus 2 remaches coaxiales
    // (solo la frenaba una luz de 0,2). Boca abajo en la cama, abren hacia arriba: sin puente.
    for (x0 = [344, 370]) tap_caja([x0 - 0.2, -57.2, 251.9], [x0 + 6.2, -47.8, 254]);
  }
  else if (n == "tap_emp_paleta") difference() { union() {
    tap_caja([332, -57, 138], [388, -54, 193]);   // chapa de 3; 56 de ancho (no 60): libra los tacos de la banda que suben a z 141 en x 390..400
    for (x0 = [344, 370]) {   // brazos: 6 x 9 arriba (el remache en x deja 2,3 por lado); 6 x 6,5 abajo (libran el MG996R y su placa)
      tap_caja([x0, -57, 236], [x0 + 6, -48, 253.8]);   // 1,8 dentro del bolsillo del carro
      tap_caja([x0, -57, 193], [x0 + 6, -50.5, 236]);
      tap_caja([x0, -57, 226], [x0 + 6, -49.4, 236]);   // 7,6 en y donde va el 2.o remache (z 231): 1,6 de pared al agujero
    }
    tap_caja([344, -57, 219], [376, -53, 225]);   // travesano: bajo de z 228..234 a 219..225 (ahi abre la una del 2.o remache)
  }
    // muesca del brazo +x: con la manivela entre 60 y 120 grados la biela (z 248.5..251.5) pasa por esa esquina
    // (2026-10-24, revision por fases de tap_fase). El resto del brazo sigue a 0.2 del carro: no deja que la
    // paleta gire alrededor del eje de los remaches.
    tap_caja([369.9, -51.8, 247.5], [373.5, -47.9, 254]);
    tap_caja([382, -58, 137], [389, -52, 143.5]);   // esquina: ahi pasan los tacos de la banda al dar la vuelta (z ~141, x 390..400)
  }
  else if (n == "tap_emp_manivela") difference() {   // barra de 10 x 5 (cubo cuadrado): se imprime DE CANTO y todos sus agujeros quedan de lado
    union() {
      tap_caja([tap_emp_x - 5, tap_emp_ys - tap_r_cuerno - 3, 242.5], [tap_emp_x + 5, tap_emp_ys + tap_emp_r, 247.5]);
      tap_cil_z(tap_emp_x, tap_emp_ys + tap_emp_r, 242.5, 247.5, 5);
    }
    // 2 tornillos M2 del cuerno (a 90 y 270 grados, r 8.4): ciegos desde la cara del cuerno, tornillo + 1 de hondo
    for (sg = [-1, 1]) tap_cil_z(tap_emp_x, tap_emp_ys + sg * tap_r_cuerno, 242, 242.5 + tap_l_cuerno + 1, tap_guia_cuerno / 2);
    tap_cil_z(tap_emp_x, tap_emp_ys + tap_emp_r, 243.5, 248, 2.1);   // perno de la biela: ciego desde arriba, 1 mm de fondo
  }
  else if (n == "tap_emp_biela") difference() {
    hull() for (y = [-55, -55 + tap_emp_L]) tap_cil_z(tap_emp_x, y, 248.5, 251.5, 4.5);
    for (y = [-55, -55 + tap_emp_L]) tap_cil_z(tap_emp_x, y, 248, 252, 2 + tol);   // giran en los pernos M4
  }
  // ---------------- sensor interior
  else if (n == "tap_sens_porta") difference() {
    union() {
      tap_caja([33, -104, 385.8], [43, -32.7, 391.8]);     // brazo bajo la viga (entre los tacos de x 20 y 58), 6 de alto
      tap_caja([33, -48.5, 385.8], [50, -32.7, 391.8]);     // taco bajo la viga para los 2 remaches sobre el eje del tubo (desde x 33: la cara que apoya)
      tap_caja([33, -104, 232.8], [39, -98, 385.8]);       // poste 6 x 6 (x < 45: fuera del almacen)
      tap_caja([33, -112.5, 229.8], [44.8, -87.5, 232.8]); // porta: la placa GY-530 va debajo con 2 M2
    }
    for (y = [-110, -90]) tap_cil_z(tap_sens[0], y, 229, 234, 1.1);
  }
  // ---------------- puntal del portico (2026-10-25)
  // Tubo 16 x 16 en (226, -40.5), de la cara de arriba del tubo del piso (z 18.6) a la de abajo de la viga (z 392): ventana
  // medida libre entre el ala del colgante (x <= 216.7) y la placa de la prensa (x >= 235). Delante (y <= -48.7) estan el panel
  // de luz y la lateral de vasos (z 72..222) y el tubo de tapas: no se le puede poner nada por -y salvo arriba (silla).
  // Dos tramos que caben en la cama (216 cada uno) con media union en z 190..220 y 2 remaches desde +y.
  // Armado, con la viga levantada a mano en x 226 hasta que quede recta (si no, el puntal la deja con la flecha y el asiento
  // que ya tenia): (1) el de arriba sube desde abajo y abraza la viga (U hacia arriba, 2 remaches de costado); (2) el de abajo entra
  // DESLIZANDO desde +y: su silla solo tiene la pared +y y pasa por encima del tubo del piso, y su media maciza pasa por el
  // costado +y de la media caja del de arriba; (3) remaches de la union y el de abajo. Con dos U (una por tramo) no se arma:
  // cada U solo entra en z y el apoyo a compresion entre los tramos no se puede alcanzar moviendo en z.
  // A compresion todo es contacto: viga / silla (z 392), media caja del de arriba / tapa del tubo de abajo (z 190), silla de
  // abajo / tubo del piso (z 18.6). Los remaches solo trabajan si el puntal tira (la prensa empuja la viga hacia arriba).
  else if (n == "tap_puntal_inf") difference() {
    union() {
      tap_caja([218, -48.5, 18.6], [234, -28.3, 24.6]);   // silla: apoya en el tubo del piso y llega a la pared +y
      tap_caja([218, -32.3, 4], [234, -28.3, 18.6]);      // pared +y (0,2 del tubo), con el remache sobre su eje
      tap_caja([218, -48.5, 24.6], [234, -32.5, 190]);    // tubo
      tap_caja([218, -40.3, 190], [234, -32.5, 219.8]);   // media union maciza (+y), 0,2 de la media caja y bajo el tubo de arriba
    }
    translate([226, -40.5, 24.6]) linear_extrude(188 - 24.6) hueco_tubo_2d();   // tapa de 2 arriba: ahi apoya la media caja
  }
  else if (n == "tap_puntal_sup") difference() {
    union() {
      tap_caja([218, -48.5, 190], [234, -40.5, 220]);     // media union en caja (-y): apoya en la tapa del tramo de abajo
      tap_caja([218, -48.5, 220], [234, -32.5, 386]);     // tubo
      tap_caja([218, -52.7, 386], [234, -28.3, 392]);     // silla bajo la viga
      for (y0 = [-52.7, -32.3]) tap_caja([218, y0, 392], [234, y0 + 4, 406]);   // paredes a los costados de la viga (0,2)
    }
    // hueco de la media caja (12,8 x 4,8 detras de la pared de 1,6 que agarran los remaches de la union: ahi abren las unas)
    tap_caja([219.6, -46.9, 192], [232.4, -42.1, 221]);
    translate([226, -40.5, 220]) linear_extrude(386 - 220) hueco_tubo_2d();
  }
}

// Dedo del escape: 6 de ancho, cola de 10 con ranura en x para el perno del cuerno (Ø2 + 2 tol).
// dy: corrimiento en reposo (el B esta retirado 6.08 mm: no toca la pila).
module tap_dedo(xd, z0, z1, pin, dy) difference() {
  union() {
    tap_caja([200 + xd - 3, -154.96 + dy, z0], [200 + xd + 3, -133.5 + dy, z1]);
    tap_caja([200 + xd - 5, pin[1] - 3, z0], [200 + xd + 5, pin[1] + 3, z1]);
  }
  // ranura abierta hacia afuera (+x en A, -x en B): la cola queda en horquilla y la cara de apoyo sin agujeros
  tap_caja([pin[0] - (xd > 0 ? 3.8 : 6), pin[1] - 1 - tol, z0 - 1], [pin[0] + (xd > 0 ? 6 : 3.8), pin[1] + 1 + tol, z1 + 1]);
}
// suplemento del plato guardado en el piso bajo la prensa (entre los tubos del piso y los nodos F5, V4 y K0): desde z0, espesor e
module tap_suplemento(z0, e) difference() {
  tap_cil_z(240, -85.5, z0, z0 + e, 31, 96);
  tap_cil_z(240, -85.5, z0 - 1, z0 + e + 1, 4.1);
}
// ventana pasante en y por la placa de la prensa (poligono en el plano xz)
module tap_ventana_xz(pts) rotate([90, 0, 0]) translate([0, 0, 40]) linear_extrude(20) polygon(pts);

// giro para imprimir (lo que queda abajo apoya en la cama)
module tap_a_cama(n) {
  // Regla de primera capa (2026-10-24): la cara que apoya, maciza; los agujeros, de lado o ciegos desde la cara de arriba (nada que perforar).
  if (n == "tap_abr_servo" || n == "tap_abr_sup" || n == "tap_emp_carro") rotate([180, 0, 0]) children();   // boca abajo
  else if (n == "tap_colgante" || n == "tap_emp_paleta") rotate([90, 0, 0]) children();   // sobre la cara -y
  else if (n == "tap_emp_soporte" || n == "tap_emp_placa_servo") rotate([-90, 0, 0]) children();   // sobre la cara +y
  else if (n == "tap_pre_leva") rotate([90, 0, 0]) children();                              // sobre la cara -y: la cara del cuerno (+y) arriba
  else if (n == "tap_pre_rodillo") rotate([90, 0, 0]) children();                           // de pie sobre la cara -y
  else if (n == "tap_emp_biela" || n == "tap_emp_manivela") rotate([0, 90, 0]) children();  // de canto: ojos y agujeros quedan de lado
  else if (n == "tap_sens_porta") rotate([0, -90, 0]) children();                           // sobre la cara -x
  // puntal: acostado sobre la cara -x, como los tubos (todos sus agujeros son en y: quedan de lado; huecos con techo de 45)
  else if (n == "tap_puntal_inf" || n == "tap_puntal_sup") rotate([0, -90, 0]) children();
  else children();   // tubo, dedos, placa de la prensa (DE PIE), buje, plato, horquilla
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

// cuerno doble del SG90 del escape girado a grados (abajo en z 239.5; los pernos Ø2 van a 12.4 del eje)
module tap_cuerno(a) translate([tap_sg_eje[0], tap_sg_eje[1], tap_sg_z - 15]) rotate([0, 0, a]) {
  hull() { cylinder(r = 2.75, h = 1.8); translate([16, 0, 0]) cylinder(r = 1.57, h = 1.8); }
  hull() { cylinder(r = 2.75, h = 1.8); translate([-13.6, 0, 0]) cylinder(r = 1.57, h = 1.8); }
}
// pila de tapas (ala Ø78 x 3.5 + tapon Ø59.6 de 6, paso 6.2) desde la tapa 'desde' (0 = la de abajo, en el dedo A,
// ala abajo en z 231.5), bajada dz
module tap_pila(desde, dz) for (k = [desde:9]) let(z = 231.5 + 6.2 * k - dz) {
  tap_cil_z(tap_tubo_c[0], tap_tubo_c[1], z, z + 3.5, 39, 96);
  tap_cil_z(tap_tubo_c[0], tap_tubo_c[1], z - 6, z, 29.8, 96);
}

module tap_comprados() {
  // SG90 del escape, invertido; cuerno doble a 14.2 grados y pernos Ø2 hasta los dedos
  translate([tap_sg_eje[0], tap_sg_eje[1], tap_sg_z]) rotate([180, 0, 0]) tap_servo(22.5, 11.8, 22.7, 15.9, 32.2, 2.5, 5.9, 5.9, 4, 3.6, 15);
  tap_cuerno(tap_a0);
  tap_cil_z(tap_pinA[0], tap_pinA[1], 229.5, 240.4, 1.0, 16);
  tap_cil_z(tap_pinB[0], tap_pinB[1], 235.3, 240.4, 1.0, 16);   // atraviesa el dedo B (1.6) entero
  tap_pila(0, 0);
  // MG996R de la prensa: eje hacia -y, orejas en y -78.2; cuerno de disco hasta y -96
  translate([tap_pre_c[0], -78.2, tap_z_leva]) rotate([90, 0, 0]) tap_mg996r();
  tap_cil_z(tap_pre_c[0], tap_pre_c[1], 232, 232 + tap_largo_vastago, 4);        // vastago Ø8
  // resorte comprimido en su lugar con el piston arriba: de 38 libre a 30 (buje arriba en 275, horquilla abajo en 305)
  translate([tap_pre_c[0], tap_pre_c[1], 275]) difference() { cylinder(r = tap_resorte[0] / 2, h = 305 - 275); translate([0, 0, -1]) cylinder(r = tap_resorte[0] / 2 - 2, h = 32); }
  tap_cil_y(tap_pre_c[0], 318, -107.5, -92.5, 1.5, 16);                           // eje del rodillo Ø3
  // MG996R del empujador: eje vertical, cuerpo hacia +x, orejas en z 224.7
  translate([tap_emp_x, tap_emp_ys, 224.7]) rotate([0, 0, 180]) tap_mg996r();
  // varillas Ø8; dentro del soporte van a presion: ese tramo se dibuja con el radio del agujero (4 - 0.05), la
  // interferencia es a proposito y no es un choque
  for (x = [345, 375]) { tap_cil_y(x, 260, -33 - tap_largo_varillas, -45, 4); tap_cil_y(x, 260, -45, -33, 4 - 0.05); }
  tap_cil_z(tap_emp_x, -55, 248, 265.5, 2);                                       // perno M4 carro-biela (ciego en el carro)
  tap_cil_z(tap_emp_x, tap_emp_ys + tap_emp_r, 243.5, 253, 2);                    // perno M4 manivela-biela (ciego en la manivela)
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
  ["tap_pre_leva", ["tap_pre_rodillo", "tap_pre_plato", "tap_pre_horquilla"]],   // vuelta completa (el piston la sigue: la leva lo mueve; leva contra piston: fase tap_prensa)
  ["tap_pre_plato", ["tap_pre_horquilla", "tap_pre_rodillo", "tap_pre_leva"]], // piston: baja 14
  ["tap_emp_paleta", ["tap_emp_carro"]],                       // paleta + carro: y -55 -> -122.5
  ["tap_emp_manivela", ["tap_emp_biela", "tap_emp_paleta", "tap_emp_carro"]],   // manivela 0..180 + biela
];
tap_carrera_dedo = 2 * 12.4 * sin(tap_a0);   // 6.08

// Lo comprado que se mueve CON la pieza (pernos, vastago, eje, resorte, goma) esta dibujado quieto, en reposo, en
// tap_comprados: se resta del barrido SOLO en reposo (2026-10-25: restado a lo largo de todo el recorrido se comia el
// frente de la paleta, la horquilla y el rodillo, y un choque ahi no se veia). revisar.py (RECORRIDOS) resta lo mismo.
module tap_quietos(n) {
  if (n == "tap_dedo_a") tap_cil_z(tap_pinA[0], tap_pinA[1], 229.4, 240.5, 1.1);
  else if (n == "tap_dedo_b") tap_cil_z(tap_pinB[0], tap_pinB[1], 235.2, 240.5, 1.1);
  else if (n == "tap_pre_plato") {
    tap_cil_z(tap_pre_c[0], tap_pre_c[1], 231.9, 232 + tap_largo_vastago + 0.1, 4.1);           // vastago
    tap_cil_y(tap_pre_c[0], 318, -108, -92, 1.6);                                             // eje del rodillo
    translate([tap_pre_c[0], tap_pre_c[1], 274]) cylinder(r = tap_resorte[0] / 2 + 0.1, h = 32);  // resorte
  }
  else if (n == "tap_emp_paleta") {
    tap_cil_z(tap_emp_x, -55, 247.9, 265.6, 2.1);                                             // perno carro-biela
    tap_caja([333.9, -58.6, 143.9], [386.1, -56.9, 190.1]);                                   // goma
  }
  else if (n == "tap_emp_manivela") {
    tap_cil_z(tap_emp_x, -55, 247.9, 265.6, 2.1);
    tap_cil_z(tap_emp_x, tap_emp_ys + tap_emp_r, 243.4, 253.1, 2.1);
  }
}
module tap_barrido(n) {
  if (n == "tap_dedo_a" || n == "tap_dedo_b") let(a = n == "tap_dedo_a")
    difference() {
      for (k = [0:12]) translate([0, (a ? -1 : 1) * tap_carrera_dedo * k / 12, 0]) tap_pieza(n);
      tap_quietos(n);
    }
  else if (n == "tap_pre_leva") difference() {
    tap_cil_y(tap_pre_c[0], tap_z_leva, -104, -96, tap_r_leva + tap_exc);   // revolucion exacta del disco excentrico
    tap_cil_y(tap_pre_c[0], 318, -108, -92, 1.6);                     // eje del rodillo (lo sigue)
    // vastago (lo sigue): con exc 7 el envolvente baja a z 310 y la punta del vastago (311) queda adentro; solo llega
    // ahi a 180 grados, cuando el piston bajo 14
    tap_cil_z(tap_pre_c[0], tap_pre_c[1], 231.9, 232 + tap_largo_vastago + 0.1, 4.1);
  }
  else if (n == "tap_pre_plato") difference() {
    for (k = [0:2 * tap_exc]) translate([0, 0, -k]) { tap_pieza("tap_pre_plato"); tap_pieza("tap_pre_horquilla"); tap_pieza("tap_pre_rodillo"); }
    tap_quietos(n);
  }
  else if (n == "tap_emp_paleta") difference() {
    for (k = [0:27]) translate([0, -2.5 * k, 0]) { tap_pieza("tap_emp_paleta"); tap_pieza("tap_emp_carro"); }
    tap_quietos(n);
  }
  else if (n == "tap_emp_manivela") difference() {
    for (t = [0:7.5:180]) let(px = tap_emp_r * sin(t), py = tap_emp_ys + tap_emp_r * cos(t),
                              yc = py - sqrt(tap_emp_L * tap_emp_L - px * px)) {
      translate([tap_emp_x, tap_emp_ys, 0]) rotate([0, 0, -t]) translate([-tap_emp_x, -tap_emp_ys, 0]) tap_pieza("tap_emp_manivela");
      hull() { tap_cil_z(tap_emp_x, yc, 248.5, 251.5, 4.5); tap_cil_z(tap_emp_x + px, py, 248.5, 251.5, 4.5); }
    }
    tap_quietos(n);                                                   // pernos en reposo (se mueven con ella)
  }
}

// ================================================================= mecanismos, fase por fase (revisar.py)
// Lo que se mueve CON otra cosa pero distinto (la leva y el piston que la sigue, la manivela y el carro que arrastra)
// no se puede revisar con los barridos: se excluyen entre si. Aqui cada lado en el paso k de su recorrido; revisar.py
// intersecta lado 0 con lado 1 en cada paso (2026-10-24: asi aparecio la biela pegando en el brazo +x de la paleta).
SINCRONOS_TAP = [["tap_empujador", 36], ["tap_prensa", 36], ["tap_escape", 24], ["tap_descarga", 24]];
module tap_fase(n, k, lado) {
  if (n == "tap_empujador") let(t = 180 * k / 36, px = tap_emp_r * sin(t), py = tap_emp_ys + tap_emp_r * cos(t),
                                yc = py - sqrt(tap_emp_L * tap_emp_L - px * px)) {
    if (lado == 0) {   // manivela girada t y la biela entre sus dos pernos
      translate([tap_emp_x, tap_emp_ys, 0]) rotate([0, 0, -t]) translate([-tap_emp_x, -tap_emp_ys, 0]) pieza("tap_emp_manivela");
      difference() {
        hull() { tap_cil_z(tap_emp_x, yc, 248.5, 251.5, 4.5); tap_cil_z(tap_emp_x + px, py, 248.5, 251.5, 4.5); }
        for (p = [[tap_emp_x, yc], [tap_emp_x + px, py]]) tap_cil_z(p[0], p[1], 248, 252, 2 + tol);
      }
    } else translate([0, yc + 55, 0]) {   // carro + paleta + sus remaches, corridos lo que los empuja la biela
      pieza("tap_emp_carro"); pieza("tap_emp_paleta");
      for (r = REM_TAP) if (r[0] == "r_tap_emp_pal_1" || r[0] == "r_tap_emp_pal_2" || r[0] == "r_tap_emp_pal_3" || r[0] == "r_tap_emp_pal_4") remache_en(r);
    }
  }
  else if (n == "tap_prensa") let(a = 360 * k / 36, xe = tap_exc * sin(a), ze = tap_z_leva + tap_exc * cos(a),
                                  rc = tap_r_leva + 6, baja = 318 - (ze - sqrt(rc * rc - xe * xe))) {   // rodillo (r 6) contra el disco
    if (lado == 0) {   // leva girada y el cuerno de disco del MG996R (redondo: girado es igual)
      translate([tap_pre_c[0], 0, tap_z_leva]) rotate([0, a, 0]) translate([-tap_pre_c[0], 0, -tap_z_leva]) pieza("tap_pre_leva");
      translate([tap_pre_c[0], -78.2, tap_z_leva]) rotate([90, 0, 0]) translate([0, 0, 16]) cylinder(r = 11, h = 1.8);
    }
    else translate([0, 0, -baja - 0.05]) { pieza("tap_pre_rodillo"); pieza("tap_pre_horquilla"); pieza("tap_pre_plato"); }
  }
  // escape de tapas (2026-10-25): cuerno de +14.2 a -14.2 (ida, k 0..12) y de vuelta (k 12..24). Dedos y cuerno contra
  // pernos, pila, cabezal con sus guias y la abrazadera. En la ida la pila esta entera sobre el dedo A (el ala de la tapa 1
  // apoya en su cara: contacto a proposito); en la vuelta la tapa 1 ya cayo y el resto bajo 0.6 sobre el dedo B.
  else if (n == "tap_escape") let(ida = k <= 12, th = ida ? tap_a0 * (1 - 2 * k / 12) : tap_a0 * (2 * (k - 12) / 12 - 1),
                                  dy = 12.4 * (sin(th) - sin(tap_a0))) {
    if (lado == 0) { translate([0, dy, 0]) pieza("tap_dedo_a"); translate([0, -dy, 0]) pieza("tap_dedo_b"); tap_cuerno(th); }
    else {   // pernos girados hasta la cara de abajo del cuerno (van clavados en el)
      tap_cil_z(200 + 12.4 * cos(th), -158 + 12.4 * sin(th), 229.5, tap_sg_z - 15, 1.0, 16);
      tap_cil_z(200 - 12.4 * cos(th), -158 - 12.4 * sin(th), 235.3, tap_sg_z - 15, 1.0, 16);
      if (ida) tap_pila(0, 0); else tap_pila(1, 231.5 + 6.2 - 237.1);
      pieza("tap_tubo"); pieza("tap_abr_servo");
    }
  }
  // descarga del vaso (2026-10-25): la paleta (con carro y goma) corrida s de 0 a 67.5 y el vaso (cono r 26.66 a 31 de
  // z 122 a 211, superficie de la banda) empujado desde que la goma lo toca arriba (z 190, r 29.98: 11.52 de luz), con
  // 0.05 de luz, contra los tacos de su casilla
  else if (n == "tap_descarga") let(s = 67.5 * k / 24, d = max(0, s - 11.52 + 0.05)) {
    if (lado == 0) translate([tap_emp_x, -100 - d, 122]) cylinder(r1 = 26.66, r2 = 31, h = 89, $fn = 120);
    else {
      pieza("vas_taco_5_b"); pieza("vas_taco_6_a");
      translate([0, -s, 0]) { pieza("tap_emp_paleta"); pieza("tap_emp_carro"); tap_caja([334, -58.5, 144], [386, -57, 190]); }
    }
  }
}
