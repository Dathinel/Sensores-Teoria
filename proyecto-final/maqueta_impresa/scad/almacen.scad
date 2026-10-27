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
//       ├ 28BYJ-48 sobre la placa, 2 tornillos M4 autorroscantes en agujeros ciegos (sin remaches)
//       └ alm_columna_1 (x 45) y alm_columna_2 (x 160): barras 8 x 8 que bajan a la placa fija; la 2 trae
//         la ranura del modulo Hall. Se remachan DE LADO (remaches horizontales) a pestanas verticales que
//         suben de la placa del puente y de la placa fija (2 arriba y 2 abajo cada una, a 10 mm o mas entre
//         ejes; abajo la pestana es una U que abraza la barra: no deja que el conjunto se mueva en paralelogramo)
//          ├ alm_embudo: embudo de carga con una barra a las columnas (1 remache horizontal por columna)
//          └ alm_placa_fija (z 266-270): lleva el 608, el agujero sobre el vaso y el rebaje de la corredera
//             └ alm_tolva: 2 postes que suben junto al borde de la placa y se remachan de lado a sus pestanas,
//                tolva al vaso y bolsillo del SG90 del obturador
//                ├ alm_obturador: corredera de 1,9 mm en un rebaje de la placa fija, ENRASADA con el piso
//                │  (2026-10-25: la aleta de abajo dejaba un bolsillo de 4,4 mm donde quedaban 2-3 monedas de
//                │  cada tubo que pasaba). Corre 30 mm hacia afuera (300 grados) y destapa todo el Ø29
//                └ alm_palanca: horquilla en el eje del SG90 que mueve el perno de la corredera (90 grados)
//   Lo que gira: eje de acero (608 abajo, acople rigido arriba) + alm_disco + alm_tambor (6 tubos): el disco va
//   PEGADO al alma del tambor (los 6 agujeros Ø29 lo centran; sin remaches: serian agujeros en la cara de apoyo).
//
// Primera capa (usuario, 2026-10-24: se levantan los circulos chicos): ninguna pieza lleva canales ni vaciados
// hacia la cama y todos los remaches van por caras laterales. El 28BYJ-48 va con 2 tornillos M4 en agujeros
// CIEGOS desde arriba (sus pestanas son horizontales: un remache ahi atravesaria la cara de apoyo). Queda en una
// cara de apoyo solo el Ø8 del eje en el disco, que lo atraviesa de verdad.
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
alm_byj_tornillo = [3.4, 3.6];    // MEDIR: agujero ciego para tornillo M4 autorroscante (diametro, hondo; piel de 1.4 abajo)
alm_sg_caja = [22.5, 11.8, 22.7]; // SG90 (electronica.js:1203)
alm_sg_eje = 5.9;                 // MEDIR: del eje al extremo cercano de la caja
alm_sg_ala = [32.2, 2.5, 15.9];   // MEDIR: largo de las alas, espesor, altura de su cara de abajo desde el fondo
alm_sg_estria = [4.8, 4];         // MEDIR: estria del eje (diametro, largo sobre la caja)
alm_ky = [18.5, 15, 1.6];         // KY-003 (sensores.js:458)

// ----------------------------------------------------------------- impreso
alm_e_placa = 4;
alm_ext = 15.7;                   // radio exterior de cada tubo (pared 1.2: 3 perimetros; aligerado 2026-10-24)
alm_z_tubo0 = 270.5;              // los tubos pasan 0.5 sobre la placa fija (visor.js:1710-1741)
alm_e_alma = 3;                   // alma que une los 6 tubos bajo el disco (z 325-328)
alm_z_pte = [352, 357];           // placa del puente = placa del motor (cara de arriba z 357, visor.js:1752)
alm_y_cara = [-48.5, -32.5];      // caras -y y +y de la viga (tubo 16 en y -40.5)
alm_hz = 0.2;                     // holgura de cada horquilla contra la viga
alm_e_hz = 3;                     // pared de las horquillas
alm_hzA = [73.2, 83.2];           // horquilla A: entre la placa del taco_2 (x 73) y la boca del embudo
alm_hzB = [165, 183];             // horquilla B: tubo t_P1-P2_2, lejos del empalme (156.5) y del colgante de tapas (x 194)
alm_z_rem_viga = 398.5;           // mitad del hueco del tubo de lado (los chaflanes de arriba empiezan en 403.4)
alm_col = [45, 160];              // x de las columnas (R 55-58 del carrusel: fuera del disco y del iman)
alm_col_y = [-62, -54];           // barra de 8 x 8 (la 1 pasa a +x del porta del VL53L0X, x 33.5-46.5)
alm_col_z1 = 377;                 // tope de las columnas (sube de 373: los remaches de arriba van a 10 mm)
alm_e_pest = 3;                   // pestanas verticales donde se remachan las columnas (a -y de la barra)
alm_y_pest = [alm_col_y[0] - tol - alm_e_pest, alm_col_y[0] - tol];   // y -65.2 .. -62.2
alm_ag_col = 8 + tol + alm_e_pest;      // barra + holgura + pestana = 11.2
alm_z_rem_col = [[275, 289], [362, 372]];   // abajo (U de la placa fija z 270-295) y arriba (pestana z 357-377)
alm_mej = 2.4;                    // mejillas de la U de abajo, a +-x de la barra con holgura tol
alm_tapas = [200, -100];          // eje del tubo de tapas (Ø86 ext. de z 225 a 300): la placa se recorta
// Obturador = corredera enrasada. Marco de H: u radial hacia afuera (300 grados desde alm_C), v a 30 grados.
// La corredera (z 268.1-270, cara de arriba = piso) apoya en un rebaje de la placa a los dos lados del Ø29 y corre
// alm_cie_s hacia +u; un perno bajo su cola entra en la horquilla de alm_palanca (eje del SG90 a alm_cie_d de la
// linea del perno: 2 d tan 45 = 30 con 90 grados de giro). Cerrada: el piso no tiene escalon; abierta: todo el
// Ø29 queda libre (la punta de la corredera pasa a 1 mm del borde del tubo).
alm_cie_s = 30;                   // carrera
alm_cie_up = 24;                  // u del perno con la corredera cerrada (fuera del anillo de la tolva, r 20.7)
alm_cie_d = 15;
alm_cie_z = [268.1, 270];         // 1.9 = 0.3 + 8 capas; el rebaje de la placa queda en 268.1 (2.1 desde la cama)
alm_cie_w = [17.9, 18.1, 21.1];   // medio ancho: corredera, rebaje, oreja de la placa
alm_cie_L = alm_cie_up + 5.5;     // la corredera va de u -14.5 a 29.5
alm_cie_f = 1;                    // luz en cada punta del recorrido: en los extremos la corredera anda 0.5 mm por
                                  // grado del SG90; asi aguanta 2 grados de mas sin trabarse contra el rebaje
module alm_en_H() translate([alm_H[0], alm_H[1], 0]) rotate(300) children();
function alm_de_H(u, v) = [alm_H[0] + u * cos(300) - v * sin(300), alm_H[1] + u * sin(300) + v * cos(300)];
alm_P = alm_de_H(alm_cie_up + alm_cie_s / 2, -alm_cie_d);   // eje del SG90 del obturador (bajo la oreja de la placa)
alm_v = 210;                      // hacia donde va la caja del SG90 (-v: lejos de la horquilla y de la tolva)
alm_z_sg = 237.3;                 // fondo de la caja del SG90 (arriba de la caja en 260)
alm_abre = 90;                    // giro del SG90 de cerrado a abierto (firmware obturador: activo - reposo = 90)
// postes de la tolva: 12 x 12 macizos a R 57-69 del carrusel (fuera del tubo de tapas y de la tolva), a 270 y 250
// grados (el de 300 quedaba en el camino de la corredera); cada uno con una pestana de la placa fija a su lado
// (+tangente) y un remache tangencial
alm_tolva_ang = [270, 250];
alm_tolva_R = [57, 69];
alm_ag_tolva = 12 + 0.3 + alm_e_pest;   // 15.3
module alm_en_C(a) translate([alm_C[0], alm_C[1], 0]) rotate(a) children();
function alm_rot(a, v) = [v[0] * cos(a) - v[1] * sin(a), v[0] * sin(a) + v[1] * cos(a)];

// ----------------------------------------------------------------- remaches (agarre = suma de lo que atraviesan)
function alm_r3(p, z) = [p[0], p[1], z];
alm_y_hz = [alm_y_cara[0] - alm_hz - alm_e_hz, alm_y_cara[1] + alm_hz + alm_e_hz];   // caras de afuera de las horquillas
alm_ag_viga = alm_e_hz + 2 * alm_hz + 1.6;   // 5.0: horquilla 3 + 0,2 + viga 1,6 y +0,2 porque la viga se corre en la U de la horquilla
REM_ALM = concat(
  // horquillas -> viga: uno de cada lado en A, dos de cada lado en B
  [for (x = [(alm_hzA[0] + alm_hzA[1]) / 2, alm_hzB[0] + 4, alm_hzB[1] - 4]) for (s = [0, 1])
    [str("r_alm_viga_", x, s == 0 ? "_m" : "_p"), alm_ag_viga, [x, alm_y_hz[s], alm_z_rem_viga], [0, s == 0 ? 1 : -1, 0]]],
  // columnas -> pestanas del puente y de la placa fija: de lado, cabeza en la cara +y de la barra
  [for (i = [0, 1]) for (k = [0, 1]) for (z = alm_z_rem_col[k])
    [str("r_alm_col", i + 1, k == 0 ? "_abajo_" : "_arriba_", z), alm_ag_col, [alm_col[i], alm_col_y[1], z], [0, -1, 0]]],
  // embudo -> columnas, de lado: en la 1 pestana a -y (el VL53L0X esta detras del otro lado); en la 2 a +y
  // (el brazo del Hall esta a -y), la pestana es la barra misma de 6.8
  [["r_alm_embudo_1", alm_ag_col, [alm_col[0], alm_col_y[1], 338], [0, -1, 0]],
   ["r_alm_embudo_2", 8 + tol + 6.8, [alm_col[1], alm_col_y[0], 334.6], [0, 1, 0]]],   // 334,6: en 334 el pasillo rozaba el disco
  // tolva -> placa fija: tangencial, por el poste macizo y la pestana. El 1 entra por la pestana (detras de su
  // poste, a -tangente, esta el poste 2)
  [for (i = [0, 1]) let(a = alm_tolva_ang[i], s = i == 0 ? -1 : 1, c = alm_rot(a, [63, s > 0 ? -6 : 6 + 0.3 + alm_e_pest]))
    [str("r_alm_tolva_", i + 1), alm_ag_tolva, [alm_C[0] + c[0], alm_C[1] + c[1], 277.5], [-s * sin(a), s * cos(a), 0]]]
);

PIEZAS_ALM = ["alm_placa_fija", "alm_tambor", "alm_disco", "alm_embudo", "alm_tolva", "alm_obturador",
              "alm_palanca", "alm_columna_1", "alm_columna_2", "alm_puente"];

// ----------------------------------------------------------------- piezas
// Placa fija: el piso por donde se arrastran las monedas. Se imprime como esta (cara de abajo en la cama):
// el alojamiento del 608 queda ARRIBA, dentro del anillo de tubos (r 14 < 16.9 del borde interior de los tubos).
// Placa fija: disco de R 51 (el piso de las monedas llega a R 47.5), orejas hasta las columnas y hasta las pestanas
// de la tolva, y pestanas verticales (3 mm) para los remaches de lado. Cara de abajo en la cama, MACIZA: solo el
// agujero Ø29 del vaso y la ranura del perno de la corredera (agujeros grandes). El 608 va en un cubo arriba, con
// piso (el eje no pasa de la placa). Oreja a 300 grados con el rebaje donde corre la corredera.
alm_r_placa_lig = 51;
module alm_placa_fija() difference() {
  union() {
    translate([alm_C[0], alm_C[1], alm_z_fondo - alm_e_placa]) cylinder(r = alm_r_placa_lig, h = alm_e_placa, $fn = 120);
    alm_en_H() translate([10, -alm_cie_w[2], alm_z_fondo - alm_e_placa]) cube([alm_cie_L + alm_cie_s + alm_cie_f + 3 - 10, 2 * alm_cie_w[2], alm_e_placa]);
    for (i = [0, 1]) {
      // oreja: del disco (que no llega a x 45 ni a x 160) hasta debajo de la U de la barra
      translate([i == 0 ? alm_col[0] - 4 - tol - alm_mej : 150, alm_y_pest[0] - 2, alm_z_fondo - alm_e_placa]) cube([i == 0 ? 60 - (alm_col[0] - 4 - tol - alm_mej) : alm_col[1] + 4 + tol + alm_mej - 150, alm_col_y[1] + 2 - alm_y_pest[0] + 2, alm_e_placa]);
      // U: pestana a -y de la barra (13.2 de ancho: 4.4 a cada lado del agujero) y dos mejillas a +-x
      // (tol 0.2) que no dejan girar la columna (2026-10-25: columnas, puente y placa formaban un paralelogramo)
      difference() {
        translate([alm_col[i] - 4 - tol - alm_mej, alm_y_pest[0], alm_z_fondo]) cube([8 + 2 * (tol + alm_mej), alm_col_y[1] - alm_y_pest[0], 25]);
        translate([alm_col[i] - 4 - tol, alm_y_pest[1], alm_z_fondo - 1]) cube([8 + 2 * tol, 20, 30]);
      }
    }
    for (a = alm_tolva_ang) alm_en_C(a) {
      // dedo recto desde dentro del disco (un hull con el disco entero pasaba por debajo del poste)
      translate([alm_r_placa_lig - 3, 6.3, alm_z_fondo - alm_e_placa]) cube([alm_tolva_R[1] + 2 - (alm_r_placa_lig - 3), alm_e_pest + 2, alm_e_placa]);
      translate([alm_tolva_R[0], 6.3, alm_z_fondo]) cube([alm_tolva_R[1] - alm_tolva_R[0], alm_e_pest, 15]);
    }
    translate([alm_C[0], alm_C[1], alm_z_fondo]) cylinder(r = 14, h = 8, $fn = 60);
  }
  alm_en_H() {
    translate([0, 0, 250]) cylinder(r = alm_r_int, h = 40, $fn = 80);                                     // paso de las monedas
    translate([alm_cie_up - 4.5 - alm_cie_f, -4.5 - tol, 250]) cube([alm_cie_s + 9 + 2 * alm_cie_f, 9 + 2 * tol, 40]);    // ranura del cubo del perno
    translate([-alm_r_int - alm_cie_f, -alm_cie_w[1], alm_cie_z[0]]) cube([alm_r_int + alm_cie_L + alm_cie_s + 2 * alm_cie_f, 2 * alm_cie_w[1], 10]);   // rebaje
  }
  translate([alm_C[0], alm_C[1], alm_z_fondo + 1]) cylinder(d = 22.2, h = 10, $fn = 60);   // 608 a presion, con piso
  translate([alm_tapas[0], alm_tapas[1], 250]) cylinder(r = 47, h = 40, $fn = 120);    // tubo de tapas (r ext. ~46)
}

// Tambor: 6 tubos de pared 1.2 unidos por un alma maciza (va en la cama, boca abajo: solo los 7 agujeros grandes).
// Entre tubos vecinos (1.6 de luz) un alma de 3 x 4 a todo lo alto: cada capa es UNA isla y no 6 anillos sueltos
// (2026-10-25: 1365 viajes con retraccion en la tanda alm_1). Queda en R 27-30, dentro del barrido de los tubos.
module alm_tambor() difference() {
  union() {
    for (a = alm_angs) let(p = alm_pol(alm_Rt, a)) translate([p[0], p[1], alm_z_tubo0]) cylinder(r = alm_ext, h = alm_z_boca - alm_z_tubo0, $fn = 90);
    translate([alm_C[0], alm_C[1], alm_z_boca - alm_e_alma]) cylinder(r = 50, h = alm_e_alma, $fn = 120);
    for (a = alm_angs) alm_en_C(a + 30) translate([alm_Rt * cos(30) - 1.5, -2, alm_z_tubo0]) cube([3, 4, alm_z_boca - alm_z_tubo0]);
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

// Embudo de carga. El cono es el del visor, pero termina en z 335 y no en 331: el iman (z 331-334, R 43-53 al
// girar) pasaria por debajo del borde del embudo y lo golpearia. En 335 el cono mide r 14.54, lo mismo que el
// tubo. Boca libre por arriba (la canal de monedas entra desde +y). Una barra 4.5 x 8 (z 336-344) por el lado -y
// del cono lo lleva a las columnas: pestana a -y de la columna 1 (con un travesano que rodea la barra) y la
// barra misma, mas gruesa, a +y de la 2. Se imprime boca abajo (rim, barra y pestanas en la cama).
module alm_embudo() difference() {
  union() {
    translate([alm_L[0], alm_L[1], alm_emb_z0]) cylinder(r1 = alm_emb_r(alm_emb_z0) + 1.8, r2 = alm_emb_r(344) + 1.8, h = 344 - alm_emb_z0, $fn = 100);
    translate([alm_col[0] + 7.2, -51.5, 336]) cube([alm_col[1] + 4 - (alm_col[0] + 7.2), 4.5, 8]);   // barra
    translate([alm_col[0] + 4.2, alm_y_pest[0], 336]) cube([3, -47 - alm_y_pest[0], 8]);              // travesano col. 1
    translate([alm_col[0] - 5, alm_y_pest[0], 325]) cube([9.2, alm_e_pest, 19]);                       // pestana col. 1
    translate([alm_col[1] - 4, alm_col_y[1] + tol, 325]) cube([8, -47 - alm_col_y[1] - tol, 19]);     // pestana col. 2
  }
  translate([alm_L[0], alm_L[1], 334]) cylinder(r1 = alm_emb_r(334), r2 = alm_emb_r(345), h = 11, $fn = 100);
}

// Obturador (2026-10-25): corredera enrasada con el piso en vez de la aleta de abajo (esa dejaba un bolsillo de
// 4,4 mm y cada tubo que pasaba por encima dejaba ahi 2-3 monedas que caian despues en el vaso de otra
// denominacion). Placa de 1.9 que apoya en el rebaje de la placa fija a los dos lados del Ø29 (3.4 mm de apoyo),
// con la punta en u -14.5 (tapa el Ø29 entero) y un perno Ø5 en la cola, bajo el piso, fuera del paso de los
// tubos. Abierta (s = 30) la punta queda en u 15.5: 1 mm fuera del tubo. Se imprime boca abajo: el piso de las
// monedas es la cara de la cama (lisa y maciza) y el perno sale hacia arriba.
module alm_obturador(s = 0) alm_en_H() translate([s, 0, 0]) {
  translate([-alm_r_int, -alm_cie_w[0], alm_cie_z[0]]) cube([alm_r_int + alm_cie_L, 2 * alm_cie_w[0], alm_cie_z[1] - alm_cie_z[0]]);
  translate([alm_cie_up, 0, 266.2]) cylinder(r = 4.5, h = alm_cie_z[0] - 266.2 + 0.01, $fn = 40);   // cubo, dentro de la ranura
  translate([alm_cie_up, 0, 262]) cylinder(d = 5, h = 266.2 - 262 + 0.01, $fn = 30);                 // perno (3.6 dentro de la horquilla)
}
// Palanca en el eje del SG90: brazo con horquilla ABIERTA (en la cama no deja un agujero cerrado) por donde corre el
// perno. Dibujada cerrada (a = 0: el brazo apunta al perno en u 24); gira -a hasta -90 (abierta, perno en u 54).
// Se imprime boca abajo (como la aleta de antes): la estria queda como agujero ciego que abre hacia arriba.
alm_pal_r = 24;                   // largo del brazo (el perno va de 15 a 21.2 del eje)
module alm_palanca_2d(d = 0) rotate(135) hull() {
  circle(r = 5.2 + d, $fn = 40);
  translate([alm_pal_r + d - 0.01, -5.2 - d]) square([0.01, 10.4 + 2 * d]);
}
module alm_en_pal(a = 0) alm_en_H() translate([alm_cie_up + alm_cie_s / 2, -alm_cie_d, 0]) rotate(-a) children();
module alm_palanca(a = 0) alm_en_pal(a) difference() {
  union() {
    translate([0, 0, 261.6]) linear_extrude(4) alm_palanca_2d();
    translate([0, 0, alm_z_sg + alm_sg_caja[2] + 0.4]) cylinder(r = 4.5, h = 261.6 - (alm_z_sg + alm_sg_caja[2] + 0.4) + 0.01, $fn = 40);
  }
  rotate(135) translate([12.3, -2.5 - tol, 261]) cube([20, 5 + 2 * tol, 6]);   // horquilla del perno (0.2 por lado)
  // shortcut: agujero liso para la estria (entra a presion); si patina, pegar el brazo simple del SG90 encima
  translate([0, 0, alm_z_sg + alm_sg_caja[2] - 0.1]) cylinder(d = alm_sg_estria[0], h = alm_sg_estria[1] + 0.1);
}
// corrimiento de la corredera con la palanca girada a (perno a 15 / cos(phi) del eje, phi de -45 a 45)
function alm_cie_sa(a) = alm_cie_d * (1 + tan(a - 45));
// todo lo que barre la palanca (+0.4): se le quita a la tolva (el brazo cerrado pasa sobre el anillo de arriba)
module alm_hueco_palanca() for (a = [0:10:alm_abre - 10]) hull() for (b = [a, a + 10])
  alm_en_pal(b) translate([0, 0, 261.2]) linear_extrude(5.5) alm_palanca_2d(0.4);

// Tolva al vaso + bolsillo del SG90 + 2 postes macizos (12 x 12) que suben junto al borde de la placa fija hasta
// z 285, unidos a la tolva por un nervio de 4 mm. Se imprime como esta (todo nace en z 230: una sola isla).
// Arriba sube hasta tocar la placa (z 266) salvo la muesca por donde pasa el brazo de la palanca. El bolsillo del
// SG90 queda bajo la oreja de la placa, unido a la tolva por el alma de abajo.
module alm_en_servo() translate([alm_P[0], alm_P[1], 0]) rotate(alm_v) children();
alm_bolsillo = [-11.5, 22.2, 7.7];   // de s a s (a lo largo de la caja) y medio ancho exterior
module alm_tolva() difference() {
  union() {
    translate([alm_H[0], alm_H[1], 230]) cylinder(r1 = alm_tol_r(230) + 1.7, r2 = alm_tol_r(262) + 1.7, h = 32, $fn = 100);
    translate([alm_H[0], alm_H[1], 262]) cylinder(r = alm_tol_r(262) + 1.7, h = alm_z_fondo - alm_e_placa - 262, $fn = 100);
    for (a = alm_tolva_ang) {
      alm_en_C(a) translate([alm_tolva_R[0], -6, 230]) cube([12, 12, 285 - 230]);
      let(c = alm_rot(a, [63, 0]), d = [alm_C[0] + c[0] - alm_H[0], alm_C[1] + c[1] - alm_H[1]])
        translate([alm_H[0], alm_H[1], 230]) rotate(atan2(d[1], d[0])) translate([0, -2, 0]) cube([norm(d), 4, alm_z_fondo - alm_e_placa - 230]);
    }
    // bolsillo: las alas del SG90 apoyan en sus paredes de punta (z 253.2)
    alm_en_servo() translate([alm_bolsillo[0], -alm_bolsillo[2], 230]) cube([alm_bolsillo[1] - alm_bolsillo[0], 2 * alm_bolsillo[2], alm_z_sg + alm_sg_ala[2] - 230]);
    hull() {   // alma tolva -> bolsillo (abajo, lejos de la aleta)
      translate([alm_H[0], alm_H[1], 230]) cylinder(r = 15, h = 20);
      alm_en_servo() translate([alm_bolsillo[0], -4, 230]) cube([2, 8, 20]);
    }
  }
  translate([alm_H[0], alm_H[1], 229]) cylinder(r1 = alm_tol_r(229), r2 = alm_tol_r(262), h = 33, $fn = 100);
  translate([alm_H[0], alm_H[1], 261.99]) cylinder(r = alm_tol_r(262), h = 10, $fn = 100);
  alm_en_servo() translate([-alm_sg_eje - tol, -alm_sg_caja[1] / 2 - tol, 232]) cube([alm_sg_caja[0] + 2 * tol, alm_sg_caja[1] + 2 * tol, 40]);
  alm_hueco_palanca();
}

// Columnas: barra 8 x 8 de la placa fija (z 270) al tope (373), perfil en el plano yz extruido 8 mm en x (se
// imprime acostada: una sola isla, sin agujeros en la cama). La 2 lleva el brazo con la ranura del KY-003 (la
// placa entra por la punta del brazo, desde -y, hasta el tope; el A3144 asoma por -x, cara abajo). La ranura
// abierta no deja un agujero cerrado en la cara de apoyo.
alm_ranura_ky = [alm_hall[1] - alm_ky[1] / 2 - tol, alm_hall[1] + alm_ky[1] / 2 + tol, 339.5 - tol, 339.5 + alm_ky[2] + tol];
module alm_perfil_col(i) {
  translate([alm_col_y[0], alm_z_fondo]) square([8, alm_col_z1 - alm_z_fondo]);
  if (i == 1) difference() {
    translate([-81, alm_ranura_ky[2] - 1.6]) square([81 + alm_col_y[0], 344 - (alm_ranura_ky[2] - 1.6)]);
    translate([-82, alm_ranura_ky[2]]) square([alm_ranura_ky[1] + 82, alm_ranura_ky[3] - alm_ranura_ky[2]]);   // abierta por la punta: el modulo entra desde -y hasta el tope
  }
}
module alm_columna(i) multmatrix([[0, 0, 1, alm_col[i] - 4], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) linear_extrude(8) alm_perfil_col(i);

// Puente: placa del motor + horquillas que abrazan la viga (reemplaza varillas M5 y pletina). Se imprime como
// esta: placa en la cama, paredes hacia arriba. Las columnas pasan por muescas del borde +y y se remachan de lado
// a pestanas verticales (z 357-377, 12 de ancho: patas de 3.8 a los lados del agujero). En la cama no queda ningun
// agujero chico (los del motor son ciegos; ventanas y agujeros grandes no cuentan). Ventanas entre cada columna y su
// horquilla (largueros de >= 3.8 mm). Cada horquilla lleva un alma de 3 en cada punta, bajo la viga, que amarra sus
// dos paredes (2026-10-25: eran paredes de 3 x 10 y 51 de alto sueltas, esbeltez 17).
module alm_puente() difference() {
  union() {
    translate([alm_col[0] - 6, -88, alm_z_pte[0]]) cube([alm_hzB[1] - alm_col[0] + 6, 88 + alm_y_cara[0] - alm_hz, 5]);
    for (h = [alm_hzA, alm_hzB]) {
      translate([h[0], alm_y_cara[0] - alm_hz, alm_z_pte[0]]) cube([h[1] - h[0], alm_y_hz[1] - alm_y_cara[0] + alm_hz, 5]);
      translate([h[0], alm_y_hz[0], alm_z_pte[0]]) cube([h[1] - h[0], alm_e_hz, 408 - alm_z_pte[0]]);
      translate([h[0], alm_y_hz[1] - alm_e_hz, alm_z_pte[0]]) cube([h[1] - h[0], alm_e_hz, 408 - alm_z_pte[0]]);
      for (x = [h[0], h[1] - 3]) translate([x, alm_y_hz[0], alm_z_pte[1]]) cube([3, alm_y_hz[1] - alm_y_hz[0], 400 - 8 - alm_hz - alm_z_pte[1]]);   // hasta 0.2 bajo la viga
    }
    for (i = [0, 1]) translate([alm_col[i] - 6, alm_y_pest[0], alm_z_pte[1]]) cube([12, alm_e_pest, alm_col_z1 - alm_z_pte[1]]);
  }
  translate([alm_L[0], alm_L[1], 340]) cylinder(r = 20.2, h = 30, $fn = 100);
  translate([alm_C[0], alm_C[1], 340]) cylinder(d = 16, h = 30);
  // 28BYJ-48: 2 tornillos M4 en agujeros ciegos desde arriba (la cara de abajo, la de la cama, queda maciza)
  for (s = [-1, 1]) translate([alm_byj_c[0] + s * alm_byj_entre / 2, alm_byj_c[1], alm_z_pte[1] - alm_byj_tornillo[1]]) cylinder(d = alm_byj_tornillo[0], h = alm_byj_tornillo[1] + 1, $fn = 24);
  for (i = [0, 1]) translate([alm_col[i] - 4 - tol, alm_y_pest[1], alm_z_pte[0] - 1]) cube([8 + 2 * tol, 20, 7]);   // muesca de la columna
  for (x = [[alm_col[0] + 8, alm_hzA[0] - 2], [128, alm_col[1] - 8]]) translate([x[0], -84, alm_z_pte[0] - 1]) cube([x[1] - x[0], -53 + 84, 7]);
}

module alm_pieza(n) {
  if (n == "alm_placa_fija") alm_placa_fija();
  else if (n == "alm_tambor") alm_tambor();
  else if (n == "alm_disco") alm_disco();
  else if (n == "alm_embudo") alm_embudo();
  else if (n == "alm_tolva") alm_tolva();
  else if (n == "alm_obturador") alm_obturador();
  else if (n == "alm_palanca") alm_palanca();
  else if (n == "alm_columna_1") alm_columna(0);
  else if (n == "alm_columna_2") alm_columna(1);
  else if (n == "alm_puente") alm_puente();
}
module alm_a_cama(n) {
  if (n == "alm_tambor" || n == "alm_embudo" || n == "alm_obturador" || n == "alm_palanca") rotate([180, 0, 0]) children();   // boca abajo
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
// [barrido, [piezas que se mueven con el]]: el conjunto que gira (disco + tambor + iman), la corredera y su palanca
// (se mueven juntas pero distinto: perno en la horquilla, se revisan fase por fase en alm_cierre).
MOVILES_ALM = [["alm_rotor", ["alm_disco", "alm_tambor"]], ["alm_obturador", ["alm_palanca"]], ["alm_palanca", ["alm_obturador"]]];
SINCRONOS_ALM = [["alm_cierre", 18]];
// paso k: palanca girada 5k grados (lado 0) y la corredera donde la deja el perno (lado 1)
module alm_fase(n, k, lado) if (n == "alm_cierre") {
  if (lado == 0) alm_palanca(5 * k);
  else alm_obturador(alm_cie_sa(5 * k));
}
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
  // la corredera solo se traslada: el casco de cada parte convexa entre cerrada y abierta es el barrido exacto
  else if (n == "alm_obturador") alm_en_H() {
    hull() for (s = [0, alm_cie_s]) translate([s - alm_r_int, -alm_cie_w[0], alm_cie_z[0]]) cube([alm_r_int + alm_cie_L, 2 * alm_cie_w[0], alm_cie_z[1] - alm_cie_z[0]]);
    hull() for (s = [0, alm_cie_s]) translate([alm_cie_up + s, 0, 266.2]) cylinder(r = 4.5, h = alm_cie_z[0] - 266.2 + 0.01, $fn = 40);
    hull() for (s = [0, alm_cie_s]) translate([alm_cie_up + s, 0, 262]) cylinder(d = 5, h = 266.2 - 262 + 0.01, $fn = 30);
  }
  else if (n == "alm_palanca") difference() {
    for (a = [0:5:alm_abre]) alm_palanca(a);
    // la estria del SG90 sobre la que gira (el agujero de cada copia gira un poco y la pisaria)
    translate([alm_P[0], alm_P[1], alm_z_sg + alm_sg_caja[2] - 0.2]) cylinder(d = alm_sg_estria[0] + 0.3, h = alm_sg_estria[1] + 0.3);
  }
}
