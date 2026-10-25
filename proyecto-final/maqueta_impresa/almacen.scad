// =====================================================================================
// Subsistema "almacen" (prefijo alm_): ALMACEN DE MONEDAS tipo revolver, todo en PLA (usuario, 2026-10-24:
// tambien lo que antes era acrilico, policarbonato, varillas M5 y pletina de aluminio). Ver CONVENCIONES.md.
// Medidas funcionales: inventario_maqueta.md §4 (sim/mundo.py:111-238, geometria.py:99-102, 211-212).
// Lo incluye maqueta.scad (este archivo no incluye nada). Todas las variables llevan alm_ porque al incluir
// los archivos OpenSCAD las comparte entre todos los subsistemas.
//
// Como se arma (de arriba abajo):
//   viga del portico (tubo 16x16, eje y -40.5, z 400)
//    └ alm_puente: placa horizontal z 352-357 (es la placa del 28BYJ-48) con dos horquillas que abrazan la
//      viga (A en x 73-83, B en x 165-183, fuera del empalme e_P1-P2_1 de x 108.5-156.5), 6 remaches
//       ├ 28BYJ-48 sobre la placa, 2 remaches por sus orejas
//       └ alm_columna_1 (x 47) y alm_columna_2 (x 160): bajan a la placa fija (2 remaches arriba y 2 abajo);
//         la 2 trae la ranura del modulo Hall, las dos una oreja para el embudo
//          ├ alm_embudo: embudo de carga con dos brazos a las columnas (2 remaches)
//          └ alm_placa_fija (z 266-270): lleva el 608 y el agujero sobre el vaso
//             └ alm_tolva (2 remaches): tolva al vaso + bolsillo del SG90 del obturador
//                └ alm_obturador: aleta que gira en horizontal bajo el agujero (calza en el eje del SG90)
//   Lo que gira: eje de acero (608 abajo, acople rigido arriba) + alm_disco + alm_tambor (6 tubos), 3 remaches.
// =====================================================================================

// ----------------------------------------------------------------- funcional (NO se mueve)
alm_C = [103.5, -71.42];          // centro del carrusel (mundo.py:215-222)
alm_Rt = 33;                      // eje -> eje de tubo (mundo.py:114)
alm_angs = [for (k = [0:5]) 90 + 60 * k];   // tubos en reposo (mundo.py:328-338)
function alm_pol(r, a) = [alm_C[0] + r * cos(a), alm_C[1] + r * sin(a)];
alm_H = alm_pol(alm_Rt, 300);     // agujero = vaso de llenado (120, -100)
alm_L = alm_pol(alm_Rt, 90);      // punto de carga (103.5, -38.42)
alm_r_int = 14.5;                 // tubo Ø29 (mundo.py:111)
alm_z_fondo = 270;                // fondo de los tubos = cara de arriba de la placa fija (mundo.py:113)
alm_z_boca = 328;                 // boca de los tubos = cara de abajo del disco (geometria.py:211)
alm_r_disco = 52;                 // disco Ø104 x 3, z 328-331
alm_r_placa = 58;                 // placa Ø116 x 4, z 266-270
alm_iman = [6, 3];                // N35, a R 48 y 0 grados, sobre el disco (z 331-334)
alm_hall = [151.5, -71.42, 338];  // cara del A3144 (geometria.py:99-102): 4 mm sobre el iman
// embudo de carga: cono de z 344 r 18 a z 331 r 13 (visor.js:1080-1082)
function alm_emb_r(z) = 13 + (z - 331) * 5 / 13;
alm_emb_z0 = 335;                 // se corta a 335 (ahi su radio es 14.54 = el del tubo): ver nota en alm_embudo
// tolva al vaso: boca z 262 r 19, salida z 230 r 14 (visor.js:1557, geometria.py:212)
function alm_tol_r(z) = 14 + (z - 230) * 5 / 32;

// ----------------------------------------------------------------- comprado (MEDIR: de ficha, sin calibrador)
alm_byj_c = [alm_C[0], alm_C[1] - 8];  // cuerpo del 28BYJ-48: eje descentrado 8 mm. Corrido hacia -y y no hacia
                                       // -x como en el visor: girado sobre su propio eje (no cambia nada funcional)
                                       // para que la oreja no quede encima de la boca del embudo
alm_byj_oreja = 1.0;              // MEDIR: espesor de la pestana del 28BYJ-48 (chapa)
alm_byj_entre = 35;               // agujeros de las pestanas (pestanas de 42 en total)
alm_sg_caja = [22.5, 11.8, 22.7]; // SG90 (electronica.js:1203)
alm_sg_eje = 5.9;                 // MEDIR: del eje al extremo cercano de la caja
alm_sg_ala = [32.2, 2.5, 15.9];   // MEDIR: largo de las alas, espesor, altura de su cara de abajo desde el fondo
alm_sg_estria = [4.8, 4];         // MEDIR: estria del eje (diametro, largo sobre la caja)
alm_ky = [18.5, 15, 1.6];         // KY-003 (sensores.js:458)

// ----------------------------------------------------------------- impreso
alm_e_placa = 4;
alm_ext = 15.7;                   // radio exterior de cada tubo (pared 1.2: 3 perimetros; aligerado 2026-10-24)
alm_ang_rem_disco = [60, 240, 300];   // remaches disco -> tambor (entre tubos, fuera de la sombra del puente)
alm_z_tubo0 = 270.5;              // los tubos pasan 0.5 sobre la placa fija (visor.js:1710-1741)
alm_e_alma = 3;                   // alma que une los 6 tubos bajo el disco (z 325-328)
alm_z_pte = [352, 357];           // placa del puente = placa del motor (cara de arriba z 357, visor.js:1752)
alm_y_cara = [-48.5, -32.5];      // caras -y y +y de la viga (tubo 16 en y -40.5)
alm_hz = 0.2;                     // holgura de cada horquilla contra la viga
alm_e_hz = 3;                     // pared de las horquillas
alm_hzA = [73.2, 83.2];           // horquilla A: entre la placa del taco_2 (x 73) y la boca del embudo
alm_hzB = [165, 183];             // horquilla B: tubo t_P1-P2_2, lejos del empalme (156.5) y del colgante de tapas (x 194)
alm_z_rem_viga = 398.5;           // mitad del hueco del tubo de lado (los chaflanes de arriba empiezan en 403.4)
alm_col = [47, 160];              // x de las columnas (angulos 160 y 20 grados, R 60: fuera del disco)
alm_col_y = [-55, -47];           // barra de 8 x 8
alm_tapas = [200, -100];          // eje del tubo de tapas (Ø86 ext. de z 225 a 300): la placa se recorta
alm_P = [alm_H[0] + 34 * cos(150), alm_H[1] + 34 * sin(150)];   // eje del SG90 del obturador (bajo la placa)
alm_v = 150;                      // hacia donde va la caja del SG90 (lejos de la tolva)
alm_z_sg = 237.3;                 // fondo de la caja del SG90 (arriba de la caja en 260)
alm_z_aleta = [263.6, 265.6];     // aleta del obturador: 0.4 bajo la placa fija
alm_abre = 70;                    // giro del obturador para destapar (la aleta se corre 39 mm: el agujero mide 29)
alm_postes = [[alm_H[0], alm_H[1] - 26], [alm_H[0] + 26 * cos(330), alm_H[1] + 26 * sin(330)]];  // tolva -> placa

// ----------------------------------------------------------------- remaches (agarre = suma de lo que atraviesan)
function alm_r3(p, z) = [p[0], p[1], z];
alm_y_hz = [alm_y_cara[0] - alm_hz - alm_e_hz, alm_y_cara[1] + alm_hz + alm_e_hz];   // caras de afuera de las horquillas
alm_ag_viga = alm_e_hz + alm_hz + 1.6;                                                // 4.8
REM_ALM = concat(
  // horquillas -> viga: uno de cada lado en A, dos de cada lado en B
  [for (x = [(alm_hzA[0] + alm_hzA[1]) / 2, alm_hzB[0] + 4, alm_hzB[1] - 4]) for (s = [0, 1])
    [str("r_alm_viga_", x, s == 0 ? "_m" : "_p"), alm_ag_viga, [x, alm_y_hz[s], alm_z_rem_viga], [0, s == 0 ? 1 : -1, 0]]],
  // 28BYJ-48 -> puente: pestana + placa
  [for (s = [-1, 1]) [str("r_alm_motor_", s), alm_byj_oreja + 5, [alm_byj_c[0] + s * alm_byj_entre / 2, alm_byj_c[1], alm_z_pte[1] + alm_byj_oreja], [0, 0, -1]]],
  // columnas -> puente (placa 5 + pie 3) y -> placa fija (pie 3 + placa 4)
  [for (i = [0, 1]) for (y = [-61, -81]) [str("r_alm_col", i + 1, "_arriba_", -y), 8, [alm_col[i], y, alm_z_pte[1]], [0, 0, -1]]],
  [for (i = [0, 1]) for (y = (i == 0 ? [-61, -81] : [-61, -68])) [str("r_alm_col", i + 1, "_abajo_", -y), 7, [alm_col[i], y, alm_z_fondo + 3], [0, 0, -1]]],
  // embudo -> orejas de las columnas (brazo 4 + oreja 4)
  [for (i = [0, 1]) [str("r_alm_embudo_", i + 1), 8, [alm_col[i], -41, 344], [0, 0, -1]]],
  // placa fija -> postes huecos de la tolva (placa 4 + tapa 3): la una abre dentro del poste
  [for (i = [0, 1]) [str("r_alm_tolva_", i + 1), 7, alm_r3(alm_postes[i], alm_z_fondo), [0, 0, -1]]],
  // disco -> alma del tambor (3 + 3), entre tubos y fuera de la sombra del puente
  [for (a = alm_ang_rem_disco) [str("r_alm_disco_", a), 6, alm_r3(alm_pol(45, a), alm_z_boca + 3), [0, 0, -1]]]
);
// puntos donde la placa fija recibe remaches (orejas)
alm_orejas = concat([for (r = REM_ALM) if (r[2][2] == alm_z_fondo + 3 || r[2][2] == alm_z_fondo) [r[2][0], r[2][1]]]);

PIEZAS_ALM = ["alm_placa_fija", "alm_tambor", "alm_disco", "alm_embudo", "alm_tolva", "alm_obturador",
              "alm_columna_1", "alm_columna_2", "alm_puente"];

// ----------------------------------------------------------------- piezas
// Placa fija: el piso por donde se arrastran las monedas. Se imprime como esta (cara de abajo en la cama):
// el alojamiento del 608 queda ARRIBA, dentro del anillo de tubos (r 14 < 16.9 del borde interior de los tubos).
// Aligerada (2026-10-24): disco de R 51 (el piso de las monedas llega a R 47.5) con orejas solo donde hay
// remaches, y canales por debajo (1.6 de piso arriba, puentes de 9 mm al imprimir) en la zona de las monedas.
// Quedan macizos: el aro del 608 (r 17), el agujero del vaso y donde apoya la tolva (r 23), las orejas.
alm_r_placa_lig = 51;
module alm_placa_fija() difference() {
  union() {
    translate([alm_C[0], alm_C[1], alm_z_fondo - alm_e_placa]) cylinder(r = alm_r_placa_lig, h = alm_e_placa, $fn = 120);
    for (p = alm_orejas) let(a = atan2(p[1] - alm_C[1], p[0] - alm_C[0])) hull() {
      translate([p[0], p[1], alm_z_fondo - alm_e_placa]) cylinder(r = 5.5, h = alm_e_placa);
      let(q = alm_pol(alm_r_placa_lig - 4, a)) translate([q[0], q[1], alm_z_fondo - alm_e_placa]) cylinder(r = 5.5, h = alm_e_placa);
    }
    translate([alm_C[0], alm_C[1], alm_z_fondo]) cylinder(r = 14, h = 8, $fn = 60);
  }
  translate([alm_H[0], alm_H[1], 250]) cylinder(r = alm_r_int, h = 40, $fn = 80);
  translate([alm_C[0], alm_C[1], alm_z_fondo + 1]) cylinder(d = 22.2, h = 10, $fn = 60);   // 608 a presion
  translate([alm_C[0], alm_C[1], 250]) cylinder(d = 12, h = 40);                          // aro interior libre
  translate([alm_tapas[0], alm_tapas[1], 250]) cylinder(r = 47, h = 40, $fn = 120);    // tubo de tapas (r ext. ~46)
  // canales por debajo (a lo largo de x: el revisor de voladizos los ve como puentes de 9 mm)
  difference() {
    intersection() {
      translate([alm_C[0], alm_C[1], alm_z_fondo - alm_e_placa - 1]) cylinder(r = 47, h = 1 + alm_e_placa - 1.6, $fn = 120);
      for (k = [-5:5]) translate([alm_C[0] - 60, alm_C[1] + 11 * k - 4.5, alm_z_fondo - alm_e_placa - 1]) cube([120, 9, 1 + alm_e_placa - 1.6]);
    }
    translate([alm_C[0], alm_C[1], 250]) cylinder(r = 17, h = 40);
    translate([alm_H[0], alm_H[1], 250]) cylinder(r = 23, h = 40);
  }
}

// Tambor: los 6 tubos unidos por un alma bajo el disco. Se imprime boca abajo (el alma en la cama).
// Aligerado (2026-10-24): pared 1.2 y el alma solo como aros alrededor de cada tubo (se tocan entre si) mas
// un resalte de r 5 en cada remache (2.8 mm de material alrededor del agujero).
module alm_tambor() difference() {
  union() {
    for (a = alm_angs) let(p = alm_pol(alm_Rt, a)) translate([p[0], p[1], alm_z_tubo0]) cylinder(r = alm_ext, h = alm_z_boca - alm_z_tubo0, $fn = 90);
    intersection() {
      translate([alm_C[0], alm_C[1], alm_z_boca - alm_e_alma]) cylinder(r = 50, h = alm_e_alma, $fn = 120);
      union() {
        for (a = alm_angs) let(p = alm_pol(alm_Rt, a)) translate([p[0], p[1], alm_z_boca - alm_e_alma]) cylinder(r = 19.5, h = alm_e_alma, $fn = 90);
        for (a = alm_ang_rem_disco) let(p = alm_pol(45, a)) translate([p[0], p[1], alm_z_boca - alm_e_alma]) cylinder(r = 5, h = alm_e_alma);
      }
    }
  }
  for (a = alm_angs) let(p = alm_pol(alm_Rt, a)) translate([p[0], p[1], 260]) cylinder(r = alm_r_int, h = 80, $fn = 90);
  translate([alm_C[0], alm_C[1], 260]) cylinder(r = 10, h = 80);
}

// Disco Ø104 x 3 con 6 agujeros Ø29, cubo Ø24 (el eje entra a presion y se pega) y el alojamiento del iman.
// Se imprime como esta: cara de abajo en la cama.
module alm_disco() let(pi = alm_pol(48, 0)) difference() {
  union() {
    translate([alm_C[0], alm_C[1], alm_z_boca]) cylinder(r = alm_r_disco, h = 3, $fn = 120);
    translate([alm_C[0], alm_C[1], alm_z_boca + 3]) cylinder(d = 24, h = 7, $fn = 60);
    translate([pi[0], pi[1], alm_z_boca + 3]) cylinder(d = 10, h = alm_iman[1]);
  }
  for (a = alm_angs) let(p = alm_pol(alm_Rt, a)) translate([p[0], p[1], 320]) cylinder(r = alm_r_int, h = 20, $fn = 90);
  translate([alm_C[0], alm_C[1], 320]) cylinder(d = 8, h = 30);
  translate([pi[0], pi[1], alm_z_boca + 3]) cylinder(d = alm_iman[0] + 0.2, h = 5);   // iman pegado, cara de arriba en 334
}

// Embudo de carga con dos brazos a las orejas de las columnas. El cono es el del visor, pero termina en z 335
// y no en 331: el iman (z 331-334, R 43-53 al girar) pasaria por debajo del borde del embudo y lo golpearia.
// En 335 el cono mide r 14.54, lo mismo que el tubo. Boca libre por arriba (la canal de monedas entra desde +y).
// Se imprime boca abajo (boca y brazos en la cama).
module alm_embudo() difference() {
  union() {
    translate([alm_L[0], alm_L[1], alm_emb_z0]) cylinder(r1 = alm_emb_r(alm_emb_z0) + 1.8, r2 = alm_emb_r(344) + 1.8, h = 344 - alm_emb_z0, $fn = 100);
    translate([alm_col[0] - 4, -45, 340]) cube([alm_col[1] - alm_col[0] + 8, 8, 4]);
  }
  translate([alm_L[0], alm_L[1], 334]) cylinder(r1 = alm_emb_r(334), r2 = alm_emb_r(345), h = 11, $fn = 100);
}

// Obturador: aleta Ø34 que tapa el agujero desde abajo y gira 70 grados en horizontal (en el hueco de 4 mm
// entre la placa y la tolva) con el SG90. La del visor bajaba girando y chocaba con la pared de la tolva.
module alm_en_P(a = 0) translate([alm_P[0], alm_P[1], 0]) rotate(a) translate([-alm_P[0], -alm_P[1], 0]) children();
module alm_aleta_2d(d = 0) {
  hull() { translate(alm_P) circle(r = 4 + d); translate(alm_H) circle(r = 4 + d); }
  translate(alm_H) circle(r = 17 + d, $fn = 80);
  translate(alm_P) circle(r = 4.5 + d);
}
module alm_obturador() difference() {
  union() {
    translate([0, 0, alm_z_aleta[0]]) linear_extrude(alm_z_aleta[1] - alm_z_aleta[0]) alm_aleta_2d();
    translate([alm_P[0], alm_P[1], alm_z_sg + alm_sg_caja[2] + 0.4]) cylinder(r = 4.5, h = alm_z_aleta[1] - (alm_z_sg + alm_sg_caja[2] + 0.4));
  }
  // shortcut: agujero liso para la estria (entra a presion); si patina, pegar el brazo simple del SG90 encima
  translate([alm_P[0], alm_P[1], alm_z_sg + alm_sg_caja[2] - 0.1]) cylinder(d = alm_sg_estria[0], h = alm_sg_estria[1] + 0.1);
}
// todo lo que barre la aleta al abrir (+0.4): se le quita a la tolva
module alm_hueco_aleta() for (a = [0:10:alm_abre - 10]) hull() for (b = [a, a + 10])
  alm_en_P(b) translate([0, 0, alm_z_aleta[0] - 0.4]) linear_extrude(4) alm_aleta_2d(0.4);

// Tolva al vaso + bolsillo del SG90 + 2 postes huecos que se remachan a la placa fija. Se imprime como esta.
// Arriba sube hasta tocar la placa (z 266) salvo la ranura por donde sale la aleta.
module alm_en_servo() translate([alm_P[0], alm_P[1], 0]) rotate(alm_v) children();
alm_bolsillo = [-11.5, 22.2, 7.7];   // de s a s (a lo largo de la caja) y medio ancho exterior
module alm_tolva() difference() {
  union() {
    translate([alm_H[0], alm_H[1], 230]) cylinder(r1 = alm_tol_r(230) + 1.7, r2 = alm_tol_r(262) + 1.7, h = 32, $fn = 100);
    translate([alm_H[0], alm_H[1], 262]) cylinder(r = alm_tol_r(262) + 1.7, h = alm_z_fondo - alm_e_placa - 262, $fn = 100);
    for (p = alm_postes) translate([p[0] - 6, p[1] - 6, 230]) cube([12, 12, alm_z_fondo - alm_e_placa - 230]);
    // bolsillo: las alas del SG90 apoyan en sus paredes de punta (z 253.2)
    alm_en_servo() translate([alm_bolsillo[0], -alm_bolsillo[2], 230]) cube([alm_bolsillo[1] - alm_bolsillo[0], 2 * alm_bolsillo[2], alm_z_sg + alm_sg_ala[2] - 230]);
    hull() {   // alma tolva -> bolsillo (abajo, lejos de la aleta)
      translate([alm_H[0], alm_H[1], 230]) cylinder(r = 15, h = 20);
      alm_en_servo() translate([alm_bolsillo[0], -4, 230]) cube([2, 8, 20]);
    }
  }
  translate([alm_H[0], alm_H[1], 229]) cylinder(r1 = alm_tol_r(229), r2 = alm_tol_r(262), h = 33, $fn = 100);
  translate([alm_H[0], alm_H[1], 261.99]) cylinder(r = alm_tol_r(262), h = 10, $fn = 100);
  for (p = alm_postes) translate([p[0] - 3.2, p[1] - 3.2, 229]) cube([6.4, 6.4, alm_z_fondo - alm_e_placa - 3 - 229]);
  alm_en_servo() translate([-alm_sg_eje - tol, -alm_sg_caja[1] / 2 - tol, 232]) cube([alm_sg_caja[0] + 2 * tol, alm_sg_caja[1] + 2 * tol, 40]);
  alm_hueco_aleta();
}

// Columnas: un perfil en el plano yz extruido 8 mm en x (se imprime acostada: el perfil en la cama).
// Barra 8 x 8 de la placa fija al puente, pie abajo y arriba (remaches), oreja para el embudo; la 2 lleva
// ademas el brazo con la ranura del KY-003 (la placa entra deslizando en x; el A3144 asoma por -x, cara abajo).
alm_ranura_ky = [alm_hall[1] - alm_ky[1] / 2 - tol, alm_hall[1] + alm_ky[1] / 2 + tol, 339.5 - tol, 339.5 + alm_ky[2] + tol];
module alm_perfil_col(i) {
  translate([alm_col_y[0], alm_z_fondo]) square([8, alm_z_pte[0] - alm_z_fondo]);
  translate([i == 0 ? -86 : -72, alm_z_fondo]) square([(i == 0 ? 86 : 72) + alm_col_y[1], 3]);
  translate([-86, alm_z_pte[0] - 3]) square([86 + alm_col_y[1], 3]);
  translate([alm_col_y[1], 336]) square([10, 4]);
  if (i == 1) difference() {
    translate([-81, alm_ranura_ky[2] - 1.6]) square([81 + alm_col_y[0], 344 - (alm_ranura_ky[2] - 1.6)]);
    translate([alm_ranura_ky[0], alm_ranura_ky[2]]) square([alm_ranura_ky[1] - alm_ranura_ky[0], alm_ranura_ky[3] - alm_ranura_ky[2]]);
  }
}
module alm_columna(i) multmatrix([[0, 0, 1, alm_col[i] - 4], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) linear_extrude(8) alm_perfil_col(i);

// Puente: placa del motor + horquillas que abrazan la viga (reemplaza varillas M5 y pletina). Se imprime como
// esta: placa en la cama, paredes hacia arriba. Agujero para el acople y recorte sobre la boca del embudo.
module alm_puente() difference() {
  union() {
    translate([alm_col[0] - 4, -88, alm_z_pte[0]]) cube([alm_hzB[1] - alm_col[0] + 4, -88 * -1 + alm_y_cara[0] - alm_hz, 5]);
    for (h = [alm_hzA, alm_hzB]) {
      translate([h[0], alm_y_cara[0] - alm_hz, alm_z_pte[0]]) cube([h[1] - h[0], alm_y_hz[1] - alm_y_cara[0] + alm_hz, 5]);
      translate([h[0], alm_y_hz[0], alm_z_pte[0]]) cube([h[1] - h[0], alm_e_hz, 408 - alm_z_pte[0]]);
      translate([h[0], alm_y_hz[1] - alm_e_hz, alm_z_pte[0]]) cube([h[1] - h[0], alm_e_hz, 408 - alm_z_pte[0]]);
    }
  }
  translate([alm_L[0], alm_L[1], 340]) cylinder(r = 20.2, h = 30, $fn = 100);
  translate([alm_C[0], alm_C[1], 340]) cylinder(d = 16, h = 30);
  // aligerado (2026-10-24): ventanas en la placa entre cada columna y su horquilla (quedan dos largueros de 4 x 5
  // y >= 3.8 mm alrededor de cada remache) y en las paredes de la horquilla B, bajo la viga (techo = puente de 11)
  for (x = [[alm_col[0] + 6, alm_hzA[0] - 2], [128, alm_col[1] - 8]]) translate([x[0], -84, alm_z_pte[0] - 1]) cube([x[1] - x[0], -53 + 84, 7]);
  for (y = alm_y_hz) translate([alm_hzB[0] + 3.5, y - 5, 362]) cube([alm_hzB[1] - alm_hzB[0] - 7, 10, 24]);
}

module alm_pieza(n) {
  if (n == "alm_placa_fija") alm_placa_fija();
  else if (n == "alm_tambor") alm_tambor();
  else if (n == "alm_disco") alm_disco();
  else if (n == "alm_embudo") alm_embudo();
  else if (n == "alm_tolva") alm_tolva();
  else if (n == "alm_obturador") alm_obturador();
  else if (n == "alm_columna_1") alm_columna(0);
  else if (n == "alm_columna_2") alm_columna(1);
  else if (n == "alm_puente") alm_puente();
}
module alm_a_cama(n) {
  if (n == "alm_tambor" || n == "alm_embudo" || n == "alm_obturador") rotate([180, 0, 0]) children();   // boca abajo
  else if (n == "alm_columna_1" || n == "alm_columna_2") rotate([0, 90, 0]) children();                 // acostada
  else children();
}

// ----------------------------------------------------------------- lo comprado (forma aproximada)
module alm_comprados() {
  translate([alm_C[0], alm_C[1], alm_z_fondo + 1]) cylinder(d = 8, h = 347.5 - (alm_z_fondo + 1));   // eje de acero Ø8
  translate([alm_C[0], alm_C[1], alm_z_fondo + 1]) cylinder(d = 22, h = 7);                          // 608ZZ
  translate([alm_C[0], alm_C[1], 339.5]) cylinder(d = 12, h = 16);                                   // acople rigido
  // 28BYJ-48: cuerpo Ø28 x 19 sobre la placa, pestanas con agujeros, resalte y eje Ø5 hacia abajo
  translate([alm_byj_c[0], alm_byj_c[1], alm_z_pte[1]]) cylinder(r = 14, h = 19, $fn = 60);
  difference() {
    hull() for (s = [-1, 1]) translate([alm_byj_c[0] + s * alm_byj_entre / 2, alm_byj_c[1], alm_z_pte[1]]) cylinder(r = 3.5, h = alm_byj_oreja);
    for (s = [-1, 1]) translate([alm_byj_c[0] + s * alm_byj_entre / 2, alm_byj_c[1], alm_z_pte[1] - 1]) cylinder(d = rem_agujero, h = 3);
  }
  translate([alm_C[0], alm_C[1], alm_z_pte[1] - 1.5]) cylinder(d = 9, h = 1.5);
  translate([alm_C[0], alm_C[1], 347]) cylinder(d = 5, h = alm_z_pte[1] - 1.5 - 347);
  // SG90 del obturador: caja, alas y estria
  alm_en_servo() {
    translate([-alm_sg_eje, -alm_sg_caja[1] / 2, alm_z_sg]) cube(alm_sg_caja);
    translate([-alm_sg_eje - (alm_sg_ala[0] - alm_sg_caja[0]) / 2, -alm_sg_caja[1] / 2, alm_z_sg + alm_sg_ala[2]]) cube([alm_sg_ala[0], alm_sg_caja[1], alm_sg_ala[1]]);
    translate([0, 0, alm_z_sg + alm_sg_caja[2]]) cylinder(d = alm_sg_estria[0], h = alm_sg_estria[1]);
  }
  // KY-003: placa en la ranura de la columna 2 y el A3144 con la cara hacia abajo en z 338
  translate([alm_hall[0] - 1.5, alm_hall[1] - alm_ky[1] / 2, 339.5]) cube(alm_ky);
  translate([alm_hall[0] - 2, alm_hall[1] - 2, alm_hall[2]]) cube([4, 4, 1.5]);
  // iman 6 x 3
  let(pi = alm_pol(48, 0)) translate([pi[0], pi[1], alm_z_boca + 3]) cylinder(d = alm_iman[0], h = alm_iman[1]);
}

// ----------------------------------------------------------------- lo que se mueve (revisar.py lo barre)
// [barrido, [piezas que se mueven con el]]: el conjunto que gira (disco + tambor + iman) y el obturador.
MOVILES_ALM = [["alm_rotor", ["alm_disco", "alm_tambor"]], ["alm_obturador", []]];
// Rotor: una vuelta completa = el perfil (R, z) girado 360 grados (el limite exacto de "copias cada 5 grados";
// todo lo que gira es de revolucion salvo el iman y los agujeros, que solo achican la pieza).
module alm_perfil_rotor() {
  translate([4, alm_z_boca]) square([alm_r_disco - 4, 3]);                                      // disco (sin el eje)
  translate([4, alm_z_boca + 3]) square([12 - 4, 7]);                                           // cubo
  translate([48 - 5, alm_z_boca + 3]) square([10, alm_iman[1]]);                              // resalte + iman
  translate([10, alm_z_boca - alm_e_alma]) square([50 - 10, alm_e_alma]);                      // alma del tambor
  translate([alm_Rt - alm_ext, alm_z_tubo0]) square([2 * alm_ext, alm_z_boca - alm_z_tubo0]);   // tubos
}
module alm_barrido(n) {
  if (n == "alm_rotor") difference() {
    translate([alm_C[0], alm_C[1], 0]) rotate_extrude($fn = 180) alm_perfil_rotor();
    // el iman quieto de alm_comprados es el mismo que gira: no es choque
    let(pi = alm_pol(48, 0)) translate([pi[0], pi[1], alm_z_boca + 2.9]) cylinder(d = alm_iman[0] + 0.1, h = alm_iman[1] + 0.2);
  }
  else if (n == "alm_obturador") difference() {
    for (a = [0:5:alm_abre]) alm_en_P(a) alm_obturador();
    // la estria del SG90 sobre la que gira (el agujero de cada copia gira un poco y la pisaria)
    translate([alm_P[0], alm_P[1], alm_z_sg + alm_sg_caja[2] - 0.2]) cylinder(d = alm_sg_estria[0] + 0.3, h = alm_sg_estria[1] + 0.3);
  }
}
