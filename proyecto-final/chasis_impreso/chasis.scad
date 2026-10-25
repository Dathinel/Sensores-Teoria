// =====================================================================================
// Chasis impreso del carro (proyecto final, grupo 7) — modelo parametrico en OpenSCAD.
//
// Marco de TODAS las cotas (igual que la simulacion y el visor): x hacia adelante, y hacia
// la izquierda, z hacia arriba, en mm; origen en el piso, bajo el centro del chasis.
// Cada pieza se modela en su lugar del ensamble (modulo *_ens) y `imprimir()` la acuesta en
// la cama en la orientacion de impresion. Uso:
//   openscad -D 'pieza="chasis"' -o chasis.stl chasis.scad     (una pieza, lista para imprimir)
//   openscad -D 'pieza="ensamble"' chasis.scad                  (carro completo con componentes)
// Lista de piezas: ver `PIEZAS` mas abajo. `exportar.py` exporta todo (STL por pieza y 3MF
// por tanda) y calcula masa y tiempo aproximados.
//
// UNIONES SIN TORNILLOS (usuario, 2026-10-21): remaches impresos con una (pieza <-> chasis),
// pernos a presion integrados (piezas livianas), pasadores a presion (caja TT) y bridas
// (placas). Solo quedan 4 tornillos M3, donde hay metal comprado: el eje de los rodamientos
// 623 de los rodillos y la brida de la rueda loca. Todos los agujeros de remache (4.4 mm)
// aceptan un tornillo M4 con tuerca si algun remache no aguanta.
//
// Las medidas marcadas MEDIR son de ficha o del visor y no se han medido en las piezas reales:
// estan en README.md con el modo de medirlas con calibrador.
// =====================================================================================

/* [Seleccion] */
pieza = "ensamble";
cual = "chasis";            // con pieza = "ensamble_pieza": cual de las piezas
$fn = 40;

// ----------------------------------------------------------------- impresora y encajes
cama = [260, 260];          // Creality Hi: volumen util 260 x 260 x 300
margen_cama = 10;           // borde libre en la cama (falda / purga)
tol = 0.2;                  // holgura de encaje POR LADO (colas de milano, remaches, cajas). Ajustar con la pieza de prueba

// ----------------------------------------------------------------- uniones a presion
rem_d = 4;                  // remache impreso: diametro del vastago (se imprime acostado, con caras planas)
rem_agujero = rem_d + 2*tol;     // agujero pasante del remache (4.4)
rem_cabeza = [8, 1.6];      // cabeza: largo y alto
rem_garra = 0.45;           // cuanto sobresale la una por lado (traba del otro lado)
rem_ranura = 1.2;           // ranura que deja cerrar las dos patas al entrar
perno_d = 4;                // pernos a presion integrados (columnas, torre, barra, zapatas, TB6612)
presion_holgura = 0.0;      // agujero del perno = perno_d + esto. 0: el agujero impreso sale ~0.15 mas chico y aprieta
pcb_perno_d = 2.9;          // perno partido con una para agujeros de placa (MEDIR: suelen ser de 3.0 a 3.2)
pin_d = 1.9;                // pines de ubicacion del HC-SR04 y VL53L0X (agujeros de M2: MEDIR)
pasador_d = 2.9;            // pasador de la caja TT (los agujeros de la caja: MEDIR, ~3.0)
pasador_aprieto = 0.15;     // el agujero de la mejilla exterior es asi de mas chico: ahi aprieta el pasador
brida = [1.8, 3.6];         // ranura para brida de 2.5 mm

// ----------------------------------------------------------------- tornilleria que queda (4 M3)
m3_paso = 3.4;
m3_tuerca_ec = 5.5;         // MEDIR: tuerca M3, entre caras
m3_tuerca_e = 2.4;          // MEDIR: espesor de la tuerca M3

// ----------------------------------------------------------------- carro (envolvente de la simulacion)
L = 180;                    // largo (config/parametros.yaml: vehiculo.largo_mm)
W = 120;                    // ancho (vehiculo.ancho_mm)
r_esquina = 8;

// ----------------------------------------------------------------- motorreductor TT y rueda
d_rueda = 65;               // MEDIR: diametro de la llanta amarilla con goma (vehiculo.diametro_rueda_mm)
ancho_rueda = 26;           // MEDIR: ancho de la llanta (vehiculo.ancho_rueda_mm)
x_eje = -0.18 * L;          // eje de las ruedas (= visor: -32.4)
y_rueda = W/2 + 13;         // centro de cada rueda (= visor: 73)
tt_semi = 11.25;            // MEDIR: mitad del alto de la caja reductora TT (22.5 / 2)
tt_espesor = 18.8;          // MEDIR: espesor de la caja reductora (a lo largo del eje)
tt_largo_caja = 33;         // MEDIR: del eje al final de la caja amarilla (donde empieza la lata)
tt_lata_d = 20;             // diametro de la lata del motor 130
tt_lata_largo = 28;         // MEDIR: lata + tapa + bornes
tt_agujeros = [[24, -8.75], [24, 8.75]];  // MEDIR: agujeros pasantes de la caja (x desde el eje, z desde el eje)
y_motor = W/2 - 14.9;       // centro de la caja reductora (= visor: 45.1)
e_mejilla = 3.0;            // mejilla interior del soporte del motor
e_mejilla_ext = 3.5;        // mejilla exterior (ahi aprieta el pasador)
e_techo_motor = 2.5;        // techo del soporte, entre la caja y la placa
x_oreja_del = x_eje + tt_largo_caja + tt_lata_largo + 6;   // oreja de adelante, pasada la lata (el remache no toca el motor)

// ----------------------------------------------------------------- placa principal (rejilla con nervios)
e_placa = 2.0;              // piel inferior (10 capas de 0.2)
h_nervio = 6;               // alto de los nervios sobre la piel
e_nervio = 1.6;             // nervios de la rejilla diagonal (4 lineas de 0.4)
e_nervio_pral = 2.4;        // nervios principales (lineas de carga) y perimetro
ala = 3;                    // piel que queda a cada lado de un nervio (el resto se vacia)
paso_iso = 34;              // paso de la rejilla diagonal (triangulos de ~39 mm de lado)
d_torreta = 9;              // torretas de remache
z_abajo = d_rueda/2 + tt_semi + e_techo_motor;   // cara de abajo de la placa (46.25)
z_plano = z_abajo + e_placa + h_nervio;          // plano de montaje (tope de nervios y torretas)
e_chasis = e_placa + h_nervio;                   // espesor en las torretas (lo que agarra cada remache)
y_paso_rueda = y_rueda - ancho_rueda/2 - 3;      // borde de la placa junto a la rueda (57)
largo_paso_rueda = d_rueda + 8;

// ----------------------------------------------------------------- carga: vaso colgado de los rieles (cuna)
x_vaso = -25;               // centro del vaso (visor: disposicionCarro.xVaso)
vaso_d = 62;                // MEDIR: diametro exterior del vaso en la boca (vasos.diametro_mm)
vaso_d_fondo = 53.3;        // MEDIR: diametro del fondo (el vaso es conico; visor: 0.86 x 62)
vaso_h = 90;                // MEDIR: alto del vaso (vasos.altura_mm)
vaso_reborde = 8;           // pestana de la boca (vasos.reborde_mm)
z_riel = 128.97;            // centro de los rieles = fin de la canaleta - 3 mm (sim/mundo.py)
sep_rieles = 69;            // entre ejes de rieles (canaleta.separacion_rieles_mm)
sep_entrada = 73;           // en la boca del embudo (canaleta.separacion_entrada_mm)
largo_embudo = 20;
r_riel = 2;                 // riel impreso equivalente a la varilla de 4 mm (forrar con cinta PTFE)
r_hueco_vaso = vaso_d_fondo/2 + 3.5;
x_cola = -L/2;
x_mampara = 16;             // cara de atras de la mampara (la espuma va de x = 6 a 16)
e_mampara = 3.5;
e_pared = 3;                // pared lateral de la cuna
y_pared = vaso_d/2 + 2.5;   // cara interior de la pared (33.5): el vaso queda a 2.5 mm
z_medio = z_riel - vaso_h/2;
guia_holgura = 1.5;         // holgura entre zapata guia y vaso a media altura
espuma_e = 10;
x_pie_pared = [-82, -60];   // remaches del pie de cada pared (adelante la amarra la mampara)
y_rem_mampara = y_pared + e_pared + 2.5;   // remaches mampara <-> poste de la pared (39)

// ----------------------------------------------------------------- energia y electronica
celda_d = 18.6;             // MEDIR: diametro de la 18650 (con forro)
pack_largo = 70;            // MEDIR: largo del pack 2S con BMS (celdas de 65 + niquel + BMS en la punta)
pack_alto = 19.5;           // MEDIR: alto del pack acostado
x_bateria = 46;
int_corte = [19.2, 13.2];   // MEDIR: ventana del interruptor de balancin (KCD1: 19 x 13)
fus_d = 12.3;               // MEDIR: rosca del portafusible de panel 5x20 (M12)
x_caja_int = [38, 68];
gvs = [53, 68];             // MEDIR: placa GVS del ESP32 de 30 pines, girada (x, y) (sim/conexiones.py: 68 x 53)
gvs_agujeros = [46, 61];    // MEDIR: distancia entre centros de los 4 agujeros de la GVS (x, y)
gvs_centro = [52, -12];
tb = 20.3;                  // MEDIR: lado del modulo TB6612FNG
tb_centro = [52, 37];
z_piso2 = 80;               // cara de abajo del piso 2 (sobre el pack con su correa)
e_piso2 = 2.4;
columnas_piso2 = [[25, 46], [25, -46], [80, 46], [80, -46]];

// ----------------------------------------------------------------- sensores
z_us = d_rueda/2 + 4 + 20;  // centro de los transductores del HC-SR04 (sim/vehiculo_sim.py: z_us = 56.5)
z_tof = 74;                 // VL53L0X (visor: disposicionCarro.zTof)
hc = [45, 20];              // MEDIR: placa del HC-SR04
hc_agujeros = [41, 16.5];   // MEDIR: entre centros de sus 4 agujeros (y, z)
hc_tx_sep = 26;             // entre centros de los dos transductores
vl = [25, 10.7];            // MEDIR: placa GY-530 (VL53L0X)
vl_agujeros_sep = 20;       // MEDIR: entre sus dos agujeros
x_frente = L/2;             // cara de atras de la escuadra frontal (borde del chasis)
ir_n = 5;                   // TCRT5000 (vehiculo.sensores_linea)
ir_paso = 15;               // vehiculo.separacion_sensores_linea_mm
ir_placa = [14, ir_paso * (ir_n - 1) + 14];   // MEDIR: placa del arreglo de 5 (14 x 74)
ir_agujeros_y = 33.5;       // MEDIR: agujeros de la placa a +-33.5 mm del centro
ir_altura_piso = 7;         // cara de los TCRT5000 sobre el piso (ven bien de 3 a 10 mm)
tcrt_alto = 7.8;            // MEDIR: del piso de la placa a la cara del TCRT5000
x_ir = L/2 - 12;            // (visor: disposicionCarro.xIr = 78)
x_loca = 0.30 * L;          // rueda loca (visor: 54)
loca_tipo = "bola";         // "bola" (rueda loca comercial, 2 tornillos M3) o "deslizador" (domo impreso con PTFE, 0 tornillos)
loca_alto = 19;             // MEDIR: del piso a la cara de ARRIBA de la brida de la rueda loca
loca_agujeros = 22;         // MEDIR: entre los dos agujeros de su brida
rodillo_y = 88;             // rodillos guia 623 (vehiculo.rodillo_guia_y_mm)
rodillo_x = x_cola + 8;
con_encoders = true;        // soporte del encoder H206 (pieza aparte, apretada por los pasadores del motor; lo usa el firmware)
e_encoder = 2.5;            // pestana del soporte del encoder, entre la cabeza del pasador y la mejilla interior

// ----------------------------------------------------------------- corte si algo no cabe en la cama
cabe_chasis = L <= cama[0] - 2*margen_cama && W <= cama[1] - 2*margen_cama;
x_corte = x_vaso - r_hueco_vaso - 10;   // donde se parte el chasis si no cabe (detras del hueco del vaso)
cola_y = [-42, 42];         // colas de milano a lo largo del corte
cola = [10, 14, 10];        // cuello, boca, largo

// =====================================================================================
// Puntos de union del chasis: [x, y, tipo]. "r" = agujero pasante de remache (la pieza va
// encima o debajo y el remache atraviesa los dos); "p" = agujero ciego desde abajo para un
// perno a presion de la pieza de abajo.
// =====================================================================================
torretas = concat(
  [for (s = [-1, 1], x = [x_eje - 15, x_oreja_del]) [x, s * y_motor, "r"]],          // soportes de motor
  [for (s = [-1, 1]) [x_loca, s * 20, "p"]],                                          // torre de la rueda loca
  [for (s = [-1, 1]) [x_ir + 2 - perno_d/2, s * 34, "p"]],                                            // barra de infrarrojos
  [for (s = [-1, 1], x = [rodillo_x + 3, rodillo_x + 11]) [x, s * 54, "r"]],          // rodillos guia
  [for (s = [-1, 1], x = x_pie_pared) [x, s * 42, "r"]],                              // paredes de la cuna
  [for (s = [-1, 1]) [12, s * 24, "r"]],                                              // mampara
  [for (s = [-1, 1]) [x_bateria, s * 22, "r"]],                                       // porta baterias
  [for (s = [-1, 1], x = [x_caja_int[0] + 4, x_caja_int[1] - 4]) [x, s * 51, "r"]],      // cajas del interruptor y del fusible
  [for (s = [-1, 1]) [x_frente - 14, s * 16, "r"]]                                    // escuadra frontal
);
pasacables = [[33.5, 55], [33.5, -55], [70, 40], [70, -40]];    // agujeros de 8 mm (motores, encoders, sensores)
pasacables_d = 8;
anclas_brida = [[-10, 52, 0], [-10, -52, 0], [-60, 52, 0], [-60, -52, 0], [62, 0, 90], [84, 30, 90], [84, -30, 90]];
rutas = [   // canales de cables a traves de los nervios
  [[-75, 50], [33.5, 50]], [[-75, -50], [33.5, -50]],
  [[33.5, 50], [70, 40]], [[33.5, -50], [70, -40]], [[70, 40], [70, -40]], [[70, 30], [88, 30]], [[70, -30], [88, -30]]
];
// Remaches por agarre (lo que juntan): [nombre, agarre mm, cantidad, donde]
REMACHES = [
  ["remache_6", 3 + 0.3 + 3, 1, "pivote de la lengueta (palanca + juego + repisa)"],
  ["remache_9_5", e_mampara + 6, 4, "mampara a los postes de las paredes"],
  ["remache_10_5", e_techo_motor + e_chasis, 8, "oreja delantera de motores, porta baterias, cajas del interruptor y del fusible"],
  ["remache_11", 3 + e_chasis, 8, "pies de las paredes, pie de la mampara, escuadra frontal"],
  ["remache_14", 6 + e_chasis, 2, "oreja trasera de motores"],
  ["remache_37", (z_abajo - 17.5) + e_chasis, 4, "bloques de los rodillos guia"],
  ["remache_12", 4 + e_chasis, 4, "plaquita del corte (solo si el chasis se parte)"]
];

// =====================================================================================
// utilidades
// =====================================================================================
module hex(ec, h) cylinder(d = ec / cos(30), h = h, $fn = 6);
module tuerca_m3(h = m3_tuerca_e + 0.4) hex(m3_tuerca_ec + 2*tol, h);
module linea2d(p0, p1, e) hull() { translate(p0) circle(d = e, $fn = 12); translate(p1) circle(d = e, $fn = 12); }
module rrect(sx, sy, r) offset(r = r) offset(delta = -r) square([sx, sy], center = true);
module caja(p0, p1) translate(p0) cube([p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]]);
module agujero_rem(h = 400) cylinder(d = rem_agujero, h = h, center = true);
module agujero_perno(h) cylinder(d = perno_d + presion_holgura, h = h);
module ranura_brida(l = 10) translate([-brida[0]/2, -brida[1]/2, -l/2]) cube([brida[0], brida[1], l]);
// Radio del vaso (conico) a la altura z (sobre el piso), colgado de los rieles.
function r_vaso(z) = let(f = (z - (z_riel - vaso_h)) / vaso_h) vaso_d_fondo/2 + (vaso_d - vaso_d_fondo)/2 * max(0, min(1, f));

// Remache impreso: cabeza en z < 0, vastago de `agarre` y una que traba en la cara de enfrente.
// Las dos patas (separadas por la ranura, normal x) se cierran al entrar. Caras planas en y
// para imprimirlo acostado: las patas flexan dentro del plano de las capas, que es lo fuerte.
module remache(agarre) {
  plano = rem_d * 0.8;
  intersection() {
    difference() {
      union() {
        translate([0, 0, -rem_cabeza[1]]) cylinder(d = rem_cabeza[0], h = rem_cabeza[1]);
        cylinder(d = rem_d, h = agarre + 0.2);
        translate([0, 0, agarre + 0.2]) cylinder(d1 = rem_d + 2*rem_garra, d2 = rem_d - 0.8, h = 2.6);
      }
      translate([-rem_ranura/2, -10, agarre * 0.3]) cube([rem_ranura, 20, agarre + 10]);
    }
    translate([-10, -plano/2, -10]) cube([20, plano, agarre + 20]);
  }
}
// Perno partido con una (integrado en una pieza): eje +z desde z = 0. `perno_una` es lo que se
// suma y `ranura_una` lo que se resta despues de unir (la ranura baja `baja` mm dentro de la pieza
// y abre `ancho` mm en x para que la base tambien flexe). Ranura con normal y.
module perno_una(d, agarre) {
  cylinder(d = d, h = agarre + 0.2);
  translate([0, 0, agarre + 0.2]) cylinder(d1 = d + 0.6, d2 = d - 0.6, h = 1.8);
}
module ranura_una(agarre, baja = 0, ancho = 10) translate([-ancho/2, -0.45, -baja]) cube([ancho, 0.9, baja + agarre + 3]);
// Pasador de la caja TT: cabeza + vastago con punta achaflanada; caras planas para imprimirlo acostado.
module pasador_tt() {
  l = e_mejilla + tt_espesor + e_mejilla_ext + (con_encoders ? e_encoder : 0);
  intersection() {
    union() {
      translate([0, 0, -1.5]) cylinder(d = 6, h = 1.5);
      cylinder(d = pasador_d, h = l - 0.5);
      translate([0, 0, l - 0.5]) cylinder(d1 = pasador_d, d2 = pasador_d - 0.8, h = 0.5);
    }
    translate([-5, -1.2, -5]) cube([10, 2.4, l + 10]);
  }
}

// =====================================================================================
// 1. CHASIS: piel de 2 mm vaciada en triangulos + nervios de 6 mm arriba (isogrid). Los nervios
// principales van por las lineas de carga: y = +-42/45 (paredes de la cuna -> motores -> ruedas),
// x = eje, rueda loca y rodillos. El vaso cuelga casi sobre el eje (x = -25 contra -32.4).
// =====================================================================================
module contorno_chasis() {
  difference() {
    rrect(L, W, r_esquina);
    for (s = [-1, 1]) translate([x_eje - largo_paso_rueda/2, s > 0 ? y_paso_rueda : -W/2 - 1]) square([largo_paso_rueda, W/2 - y_paso_rueda + 1]);
  }
}
module nervios_2d() {
  difference() { contorno_chasis(); offset(delta = -e_nervio_pral) contorno_chasis(); }
  intersection() {
    contorno_chasis();
    union() {
      for (y = [-45, -42, 0, 42, 45]) linea2d([-L/2, y], [L/2, y], e_nervio_pral);
      for (x = [x_eje - 15, x_eje + 36, x_loca, x_ir, x_cola + 11, 46]) linea2d([x, -W/2], [x, W/2], e_nervio_pral);
      for (a = [60, -60]) for (k = [-7:7]) rotate(a) linea2d([k * paso_iso, -250], [k * paso_iso, 250], e_nervio);
    }
  }
  for (t = torretas) translate([t[0], t[1]]) circle(d = d_torreta);
  for (p = pasacables) translate(p) circle(d = pasacables_d + 2*e_nervio_pral);
  translate([x_vaso, 0]) difference() { circle(r = r_hueco_vaso + e_nervio_pral, $fn = 90); circle(r = r_hueco_vaso, $fn = 90); }
  for (c = columnas_piso2) translate(c) square(10, center = true);
}
module bolsillos_2d() {
  difference() {
    offset(delta = -e_nervio_pral - ala) contorno_chasis();
    offset(delta = ala) nervios_2d();
    for (a = anclas_brida) translate([a[0], a[1]]) circle(d = 14);
  }
}
module chasis_ens() {
  difference() {
    union() {
      translate([0, 0, z_abajo]) linear_extrude(e_placa) difference() { contorno_chasis(); bolsillos_2d(); }
      translate([0, 0, z_abajo]) linear_extrude(e_chasis) intersection() { contorno_chasis(); nervios_2d(); }
      // columnas del piso 2 (impresas con el chasis: suben derecho, sin soporte) con su perno a presion arriba
      for (c = columnas_piso2) translate([c[0], c[1], z_abajo]) {
        translate([-5, -5, 0]) cube([10, 10, z_piso2 - z_abajo]);
        translate([0, 0, z_piso2 - z_abajo]) cylinder(d = perno_d, h = e_piso2 - 0.2);
      }
    }
    translate([x_vaso, 0, 0]) cylinder(r = r_hueco_vaso, h = 200, $fn = 90);
    for (t = torretas) translate([t[0], t[1], 0]) {
      if (t[2] == "r") agujero_rem();
      else translate([0, 0, z_abajo - 1]) agujero_perno(1 + e_chasis - 1);
    }
    for (p = pasacables) translate([p[0], p[1], 0]) cylinder(d = pasacables_d, h = 200);
    for (a = anclas_brida) translate([a[0], a[1], z_abajo - 1]) rotate([0, 0, a[2]])
      for (dx = [-3.5, 3.5]) translate([dx - 0.9, -2, 0]) cube([1.8, 4, 10]);
    // canales de cables: 7 mm de ancho, 4 mm de hondo desde el plano de montaje
    for (r = rutas) hull() for (p = r) translate([p[0], p[1], z_plano - 4]) cylinder(d = 7, h = 10, $fn = 16);
    if (!cabe_chasis) for (s = [-1, 1], dx = [-14, 14]) translate([x_corte + dx, s * 24, 0]) agujero_rem();
  }
}

// --- corte del chasis en dos con colas de milano (solo si no cabe en la cama) ---
module cola_2d(extra = 0) for (y = cola_y) translate([x_corte, y]) polygon([
  [-1, -cola[0]/2 - extra], [cola[2] + extra, -cola[1]/2 - extra], [cola[2] + extra, cola[1]/2 + extra], [-1, cola[0]/2 + extra]]);
module chasis_a() intersection() { chasis_ens(); linear_extrude(400) union() { translate([-500, -500]) square([500 + x_corte, 1000]); cola_2d(0); } }
module chasis_b() difference() { chasis_ens(); linear_extrude(400) union() { translate([-500, -500]) square([500 + x_corte, 1000]); cola_2d(tol); } }
// Plaquita bajo el corte con 4 remaches: las colas aguantan el corte, la plaquita la flexion.
module union_corte_ens() translate([x_corte, 0, z_abajo - 4]) difference() {
  translate([-20, -32, 0]) cube([40, 64, 4]);
  for (s = [-1, 1], dx = [-14, 14]) translate([dx, s * 24, 0]) agujero_rem();
  translate([-12, -16, -1]) cube([24, 32, 10]);
}

// =====================================================================================
// 2. SOPORTE DE MOTOR TT (x2, en espejo): techo de 2.5 mm entre la caja y la placa, oreja de atras
// y brazo hasta una oreja de adelante pasada la lata (dos remaches al chasis), dos mejillas que
// abrazan la caja con dos pasadores impresos a presion. La repisa del encoder H206 es pieza aparte
// (soporte_encoder): pegada al soporte no se podia imprimir sin soporte (quedaba en el aire).
// =====================================================================================
module soporte_motor_ens(s = 1) {
  yc = s * y_motor;
  zt = z_abajo - e_techo_motor;               // cara de abajo del techo = tope de la caja
  ye_i = yc - s * (tt_espesor/2 + e_mejilla); // cara de afuera de la mejilla interior
  ye_e = yc + s * (tt_espesor/2 + e_mejilla_ext);
  y0 = min(ye_i, ye_e); y1 = max(ye_i, ye_e);
  xa = x_eje + 14; xb = x_eje + tt_largo_caja; // mejillas (no tapan el eje ni la lata)
  zb = d_rueda/2 - 15.5;
  ze = d_rueda/2 - 18.6;                       // cara de abajo del H206 (visor: zEncoder)
  yr = s * (W/2 - 30);
  difference() {
    union() {
      caja([x_eje - 20, y0, zt], [xb, y1, z_abajo]);                                         // techo
      translate([x_eje - 15, yc, z_abajo - 6]) cylinder(d = 11, h = 6);                      // oreja de atras
      caja([xb - 1, yc - 4.5, zt], [x_oreja_del, yc + 4.5, z_abajo]);                        // brazo sobre la lata
      translate([x_oreja_del, yc, zt]) cylinder(d = 11, h = e_techo_motor);                  // oreja de adelante
      caja([xa, min(yc + s * tt_espesor/2, ye_e), zb], [xb, max(yc + s * tt_espesor/2, ye_e), zt]);  // mejilla exterior
      caja([xa, min(yc - s * tt_espesor/2, ye_i), zb], [xb, max(yc - s * tt_espesor/2, ye_i), zt]);  // mejilla interior
    }
    // caja reductora (holgura 0.3) y su eje
    translate([0, yc, 0]) rotate([90, 0, 0]) linear_extrude(tt_espesor + 0.6, center = true) offset(0.3) hull() {
      translate([x_eje, d_rueda/2]) circle(r = tt_semi);
      translate([x_eje, d_rueda/2 - tt_semi]) square([tt_largo_caja, 2*tt_semi]);
    }
    translate([x_eje, 0, d_rueda/2]) rotate([90, 0, 0]) cylinder(d = 8, h = 300, center = true);
    // pasadores: pasan libres por la mejilla interior y la caja, y aprietan en la mejilla exterior
    for (a = tt_agujeros) translate([x_eje + a[0], 0, d_rueda/2 + a[1]]) {
      translate([0, (ye_i + (yc + s * tt_espesor/2)) / 2, 0]) rotate([90, 0, 0]) cylinder(d = pasador_d + 2*tol, h = abs(ye_i - (yc + s * tt_espesor/2)) + 0.02, center = true);
      rotate([90, 0, 0]) cylinder(d = pasador_d - pasador_aprieto, h = 300, center = true);
    }
    for (x = [x_eje - 15, x_oreja_del]) translate([x, yc, 0]) agujero_rem();
  }
}

// Soporte del encoder H206 (x2, en espejo): repisa bajo la placa del H206 (el disco de 20 ranuras
// queda en su horquilla) y una pestana vertical que se aprieta entre la cabeza de los pasadores del
// motor y la mejilla interior. Se imprime como va montado: repisa contra la cama, pestana hacia arriba.
module soporte_encoder_ens(s = 1) {
  yc = s * y_motor;
  zt = z_abajo - e_techo_motor;
  ye_i = yc - s * (tt_espesor/2 + e_mejilla);      // cara de adentro de la mejilla interior
  ze = d_rueda/2 - 18.6;                           // cara de abajo del H206 (visor: zEncoder)
  yr = s * (W/2 - 30);                             // centro de la placa del H206
  xp = x_eje + 14;                                 // la pestana arranca donde la mejilla (lejos del disco)
  difference() {
    union() {
      caja([x_eje - 25, yr - 10.5, ze - 2.5], [x_eje + 28, yr + 10.5, ze]);                          // repisa
      caja([xp, min(ye_i, ye_i - s * e_encoder), ze - 2.5], [x_eje + 28, max(ye_i, ye_i - s * e_encoder), zt]);   // pestana
    }
    for (a = tt_agujeros) translate([x_eje + a[0], 0, d_rueda/2 + a[1]]) rotate([90, 0, 0]) cylinder(d = pasador_d + 2*tol, h = 300, center = true);
    for (x = [x_eje - 18, x_eje + 2], dy = [-8.5, 8.5]) translate([x, yr + dy, ze - 1.25]) ranura_brida();   // bridas por fuera de la placa
  }
}

// =====================================================================================
// 3. CUNA DEL VASO: dos paredes en celosia (Warren) con el riel impreso en el borde de arriba
// y la boca en embudo atras, mampara adelante con las espumas, zapatas guia a media altura
// (piezas aparte a presion, ajustables con cinta PTFE), lengueta-trinquete atras y el
// infrarrojo de la cuna (con brida).
// =====================================================================================
z_cordon_inf = z_plano + 8;
z_cordon_sup = z_riel - 8;
x_pared0 = x_cola; x_pared1 = x_mampara - 6;     // la celosia; de x_pared1 a x_mampara va el poste delantero
zapatas_x = [-45, -5];
x_ir_cuna = -33; z_ir_cuna = z_riel - 30;        // visor: xCola/2 + 12, zRiel - 30
ir_cuna_dx = 24;                                 // MEDIR: del centro del TCRT5000 al agujero de su modulo
piv_leng = [x_cola + 16, z_riel - 35];           // pivote de la lengueta (x, z)
z_rem_mampara = [z_plano + 16, z_riel - 14];
module pared_2d(s) {
  n = 4; x0 = x_pared0 + 6; x1 = x_pared1; p = (x1 - x0) / n;
  difference() {
    translate([x_pared0, z_plano]) square([x_mampara - x_pared0, z_riel - z_plano]);
    for (i = [0:n-1]) {
      xi = x0 + i * p;
      offset(r = 2) offset(delta = -3.5) polygon([[xi, z_cordon_inf], [xi + p, z_cordon_inf], [xi + p/2, z_cordon_sup]]);
      if (i < n - 1) offset(r = 2) offset(delta = -3.5) polygon([[xi + p/2, z_cordon_sup], [xi + 3*p/2, z_cordon_sup], [xi + p, z_cordon_inf]]);
    }
  }
  // zonas macizas: zapatas, infrarrojo, marco de la ventana de la lengueta
  for (x = zapatas_x, dx = [-7, 7]) translate([x + dx, z_medio]) circle(r = 5);
  if (s > 0) translate([x_ir_cuna - 9, z_ir_cuna - 12]) square([ir_cuna_dx + 15, 24]);
  if (s < 0) translate([x_pared0, piv_leng[1] - 10]) square([45, 20]);
}
module pared_cuna_ens(s = 1) {
  yi = s * y_pared; ye = s * (y_pared + e_pared);
  difference() {
    union() {
      translate([0, (s > 0 ? ye : yi), 0]) rotate([90, 0, 0]) linear_extrude(e_pared) pared_2d(s);
      // pie hacia afuera con 2 remaches y escuadras
      caja([x_cola, min(ye, s * 46), z_plano], [x_mampara, max(ye, s * 46), z_plano + 3]);
      for (x = [x_cola + 2, -52, -2]) translate([x, 0, z_plano]) hull() {
        caja([0, min(ye, ye + s * 7), 0], [2.4, max(ye, ye + s * 7), 1]);
        caja([0, min(ye, ye + s * 0.5), 0], [2.4, max(ye, ye + s * 0.5), 14]);
      }
      // ala de arriba hacia afuera (rigidez lateral)
      caja([x_cola, min(ye, ye + s * 5), z_cordon_sup], [x_mampara, max(ye, ye + s * 5), z_cordon_sup + 2]);
      // poste delantero: recibe los remaches de la mampara a lo largo de x
      caja([x_pared1, min(yi, s * (y_rem_mampara + 4.5)), z_plano], [x_mampara, max(yi, s * (y_rem_mampara + 4.5)), z_riel]);
      // riel: tramo recto y boca en embudo (cresta 2 mm sobre z_riel)
      intersection() {
        union() {
          hull() for (x = [x_cola + largo_embudo, x_mampara]) translate([x, s * sep_rieles/2, z_riel]) sphere(r = r_riel, $fn = 16);
          hull() { translate([x_cola + 1, s * sep_entrada/2, z_riel]) sphere(r = r_riel, $fn = 16);
                   translate([x_cola + largo_embudo, s * sep_rieles/2, z_riel]) sphere(r = r_riel, $fn = 16); }
          hull() { caja([x_cola, min(yi, s * (sep_entrada/2 + r_riel)), z_cordon_sup], [x_cola + 1, max(yi, s * (sep_entrada/2 + r_riel)), z_riel]);
                   caja([x_cola + largo_embudo, min(yi, ye), z_cordon_sup], [x_cola + largo_embudo + 1, max(yi, ye), z_riel]); }
        }
        caja([x_cola, min(yi, s * 60), 0], [x_mampara, max(yi, s * 60), 200]);   // nada sobresale hacia el vaso
      }
      // torreta del infrarrojo de la cuna con su pin de ubicacion
      if (s > 0) translate([x_ir_cuna + ir_cuna_dx, ye, z_ir_cuna]) rotate([-90, 0, 0]) {
        cylinder(d = 8, h = 7.5); translate([0, 0, 7.5]) cylinder(d = pcb_perno_d - 0.2, h = 1.6); }
      // repisa del pivote de la lengueta
      if (s < 0) translate([piv_leng[0], 0, piv_leng[1] - 3]) caja([-6, ye - 12, 0], [6, ye, 3]);
    }
    for (x = zapatas_x, dx = [-7, 7]) translate([x + dx, 0, z_medio]) rotate([90, 0, 0]) cylinder(d = perno_d + presion_holgura, h = 300, center = true);
    if (s > 0) {
      translate([x_ir_cuna - 6, yi - s, z_ir_cuna - 4]) cube([12, 20, 8]);                   // ventana del TCRT5000
      for (dz = [-9, 9]) translate([x_ir_cuna + ir_cuna_dx/2, yi, z_ir_cuna + dz]) rotate([90, 0, 0]) ranura_brida(20);
    }
    if (s < 0) {
      translate([x_cola + 6, yi + 1, piv_leng[1] - 1]) rotate([90, 0, 0]) linear_extrude(6) square([36, 9]);   // ventana de la lengueta
      translate([piv_leng[0], ye - 6, 0]) agujero_rem();                                                         // pivote
    }
    for (x = x_pie_pared) translate([x, s * 42, 0]) agujero_rem();
    translate([x_eje - 15, s * y_motor, z_plano - 1]) cylinder(d = 9, h = 10);   // ahi asoma la una del remache del motor
    for (z = z_rem_mampara) translate([x_mampara, s * y_rem_mampara, z]) rotate([0, 90, 0]) agujero_rem(30);
  }
}
module mampara_ens() {
  ya = y_rem_mampara + 4.5; zt = z_riel + 4;
  difference() {
    union() {
      translate([x_mampara, 0, 0]) rotate([90, 0, 90]) linear_extrude(e_mampara) difference() {
        translate([-ya, z_plano]) offset(r = 3) offset(delta = -3) square([2*ya, zt - z_plano]);
        translate([-ya + 12, z_plano + 7]) offset(r = 3) offset(delta = -3) square([2*ya - 24, z_medio - 12 - z_plano - 7]);
        translate([-ya + 12, z_medio + 12]) offset(r = 3) offset(delta = -3) square([2*ya - 24, z_riel - 24 - z_medio - 12]);
      }
      for (s = [-1, 1]) caja([8, min(s * 15, s * 31), z_plano], [x_mampara + 0.01, max(s * 15, s * 31), z_plano + 3]);   // pie
    }
    for (s = [-1, 1]) translate([12, s * 24, 0]) agujero_rem();
    for (s = [-1, 1], z = z_rem_mampara) translate([x_mampara, s * y_rem_mampara, z]) rotate([0, 90, 0]) agujero_rem(30);
  }
}
// Zapata guia: pastilla de 24 x 14 con dos pernos a presion que entran en la pared. Su espesor
// deja `guia_holgura` hasta el vaso conico; si el vaso real es otro, se reimprime (2 min).
zapata_e = y_pared - r_vaso(z_medio) - guia_holgura;
module zapata_ens(x = -45, s = 1) {
  translate([x - 12, s > 0 ? y_pared - zapata_e : -y_pared, z_medio - 7]) cube([24, zapata_e, 14]);
  for (dx = [-7, 7]) translate([x + dx, s * y_pared, z_medio]) rotate([s > 0 ? -90 : 90, 0, 0]) cylinder(d = perno_d, h = e_pared - 0.2);
}
// Lengueta (trinquete pasivo, lado -y): palanca de 3 mm que gira en un remache sobre la repisa
// de la pared derecha; un elastico la devuelve detras del vaso.
module lengueta_ens() {
  ye = -(y_pared + e_pared);
  p0 = [piv_leng[0], ye - 6]; p1 = [x_vaso - r_vaso(piv_leng[1]) - 6, -18];
  translate([0, 0, piv_leng[1] + 0.3]) linear_extrude(3) difference() {
    union() { translate(p0) circle(r = 5); hull() { translate(p0) circle(r = 3.5); translate(p1) circle(r = 2.5); } }
    translate(p0) circle(d = rem_agujero + 0.2);       // gira libre en el remache
    translate((p0 + p1) / 2 + [-3, -3]) circle(d = 2); // gancho del elastico
  }
}

// =====================================================================================
// 4. RUEDA LOCA: torre de dos columnas con brida abajo (rueda loca de bola: 2 tornillos M3) o
// domo deslizante impreso. Entra al chasis con dos pernos a presion (trabaja a compresion).
// =====================================================================================
module torre_loca_ens() {
  zb = loca_tipo == "bola" ? loca_alto : 10;
  difference() {
    union() {
      for (s = [-1, 1]) translate([x_loca - 5, s * 20 - 5, zb]) cube([10, 10, z_abajo - zb]);
      for (s = [-1, 1]) translate([x_loca, s * 20, z_abajo]) cylinder(d = perno_d, h = e_chasis - 1.2);
      translate([x_loca - 7, -25, zb]) cube([14, 50, 5]);                          // brida
      translate([x_loca - 1.2, -20, zb]) cube([2.4, 40, z_abajo - zb]);           // alma
      if (loca_tipo != "bola") translate([x_loca, 0, 10]) intersection() { sphere(r = 10); translate([-20, -20, -20]) cube([40, 40, 20]); }
    }
    if (loca_tipo == "bola") for (s = [-1, 1]) translate([x_loca, s * loca_agujeros/2, zb - 1]) {
      cylinder(d = m3_paso, h = 20);
      translate([0, 0, 1 + 5 - m3_tuerca_e - 0.4]) rotate([0, 0, 30]) tuerca_m3(5);
    }
  }
}

// =====================================================================================
// 5. BARRA DE LOS 5 TCRT5000: viga bajo el frente con dos columnas que entran a presion al
// chasis; la placa del arreglo se clava en dos pernos partidos con una. Alto: ir_altura_piso
// (reimprimir si se cambia; para ajuste fino, arandelas o calces entre columna y chasis).
// =====================================================================================
module barra_ir_ens() {
  zp = ir_altura_piso + tcrt_alto;           // cara de abajo de la placa
  zv = zp + 1.6 + 5;                         // viga sobre separadores de 5 mm
  difference() {
    union() {
      translate([x_ir - 6, -ir_agujeros_y - 6, zv]) cube([8, 2 * ir_agujeros_y + 12, 5]);
      for (s = [-1, 1]) {
        // todo al ras de x = x_ir + 2 (la cara que queda contra la cama al imprimirla de costado)
        translate([x_ir - 8, s * 34 - 5, zv]) cube([10, 10, z_abajo - zv]);
        translate([x_ir + 2 - perno_d/2, s * 34, z_abajo]) cylinder(d = perno_d, h = e_chasis - 1.2);
        translate([x_ir - 4, s * ir_agujeros_y - 3, zp + 1.6]) cube([6, 6, 5.01]);
        translate([x_ir + 2 - (pcb_perno_d + 0.6)/2, s * ir_agujeros_y, zp + 1.6]) mirror([0, 0, 1]) perno_una(pcb_perno_d, 1.6);
      }
    }
    for (s = [-1, 1]) translate([x_ir + 2 - (pcb_perno_d + 0.6)/2, s * ir_agujeros_y, zp + 1.6]) mirror([0, 0, 1]) ranura_una(1.6, baja = 4.5, ancho = 7);
  }
}

// =====================================================================================
// 6. RODILLO GUIA (x2): bloque bajo la cola (2 remaches largos al chasis) y brazo hasta y = 88
// con dos rodamientos 623 en un tornillo M3 vertical (lo que empujan las guias del muelle).
// =====================================================================================
module soporte_rodillo_ens(s = 1) {
  zb = 17.5;
  difference() {
    union() {
      caja([x_cola, min(s * 48, s * 60), zb], [x_cola + 14, max(s * 48, s * 60), z_abajo]);
      hull() { caja([rodillo_x - 6, min(s * 60, s * 59), zb], [rodillo_x + 6, max(s * 60, s * 59), zb + 4]);
               translate([rodillo_x, s * rodillo_y, zb]) cylinder(r = 6, h = 4); }
      hull() { caja([rodillo_x - 1.2, min(s * 60, s * 59), zb + 4], [rodillo_x + 1.2, max(s * 60, s * 59), zb + 14]);
               translate([rodillo_x - 1.2, s * (rodillo_y - 6) - 0.5, zb + 4]) cube([2.4, 1, 0.5]); }
    }
    for (x = [rodillo_x + 3, rodillo_x + 11]) translate([x, s * 54, 0]) agujero_rem();
    translate([rodillo_x, s * rodillo_y, 0]) { cylinder(d = m3_paso, h = 100); translate([0, 0, zb + 4 - m3_tuerca_e - 0.4 + 0.01]) rotate([0, 0, 30]) tuerca_m3(5); }
  }
}

// =====================================================================================
// 7. PORTA BATERIAS: cuna para el pack 2S (celdas acostadas a lo ancho del carro) con divisor
// central (ahi van los 2 remaches), topes en las puntas, salida de cables y ranuras para una
// correa de velcro de 20 mm.
// =====================================================================================
module porta_bateria_ens() {
  ax = 2 * celda_d + 3 + 1;  ay = pack_largo + 1;  e = 2;
  zc = z_plano + e + celda_d/2;
  difference() {
    union() {
      translate([x_bateria - ax/2 - e, -ay/2 - e, z_plano]) cube([ax + 2*e, ay + 2*e, e + celda_d * 0.45]);
      for (s = [-1, 1]) translate([x_bateria - ax/2 - e, s > 0 ? ay/2 : -ay/2 - e, z_plano]) cube([ax + 2*e, e, e + pack_alto * 0.8]);
    }
    for (s = [-1, 1]) translate([x_bateria + s * (celda_d/2 + 2), 0, zc]) rotate([90, 0, 0]) cylinder(d = celda_d + 1, h = ay, center = true, $fn = 60);
    translate([x_bateria - ax/2, -ay/2, zc]) cube([ax, ay, 40]);
    for (s = [-1, 1]) translate([x_bateria, s * 22, 0]) agujero_rem();
    for (s = [-1, 1]) translate([x_bateria + s * (ax/2 + e/2) - 1.5, -11, z_plano - 1]) cube([3, 22, 10]);     // correa
    for (s = [-1, 1]) translate([x_bateria - 4, s * (ay/2 + e/2) - e, z_plano + e + 4]) cube([8, 2*e, 30]);     // cables
    // aligerado, hacia las puntas: entre las ventanas queda piso macizo para los remaches (y = +-22)
    for (s = [-1, 1]) translate([x_bateria - ax/2 + 3, s > 0 ? 26 : -ay/2 + 1.5, z_plano - 1]) cube([ax - 6, ay/2 - 1.5 - 26, 10]);
  }
}

// =====================================================================================
// 8. CAJAS DEL INTERRUPTOR Y DEL FUSIBLE: el interruptor de balancin en el costado izquierdo y el
// portafusible de panel en el derecho (se alcanzan desde afuera). Iban en una sola caja, pero la
// ventana del interruptor y el agujero del fusible se montaban: la caja mide 30 mm y harian falta
// ~42 (atras esta el pasacables y adelante la columna del piso 2). Misma caja, en espejo.
// =====================================================================================
module caja_int_ens(s = 1) {
  x0 = x_caja_int[0]; x1 = x_caja_int[1]; y0 = 44; y1 = W/2; h = 22; e = 2.2;
  xc = (x0 + x1) / 2; zc = z_plano + 2.5 + h/2 - 1;
  mirror([0, s > 0 ? 0 : 1, 0]) difference() {
    union() {
      caja([x0, y1 - 2.5, z_plano], [x1, y1, z_plano + h]);              // panel
      caja([x0, y0, z_plano], [x1, y1, z_plano + 2.5]);                  // piso
      for (x = [x0, x1 - e]) caja([x, y0, z_plano], [x + e, y1, z_plano + h]);
      caja([x0, y0, z_plano], [x1, y0 + e, z_plano + 8]);                // pared de atras baja (cables por arriba)
    }
    if (s > 0) translate([xc, y1 - 5, zc]) cube([int_corte[0] + 2*tol, 10, int_corte[1] + 2*tol], center = true);
    else translate([xc, y1 - 5, zc]) rotate([-90, 0, 0]) cylinder(d = fus_d + 2*tol, h = 10, $fn = 48);
    for (x = [x0 + 4, x1 - 4]) translate([x, 51, 0]) agujero_rem();
  }
}

// =====================================================================================
// 9. PISO 2: placa nervada que entra a presion en los pernos de las 4 columnas del chasis, con 4
// separadores de perno partido con una para la placa GVS del ESP32 y dos pernos para el TB6612.
// =====================================================================================
module piso2_ens() {
  x0 = 20; x1 = 86; y0 = -51; y1 = 51;
  gv = [for (sx = [-1, 1], sy = [-1, 1]) [gvs_centro[0] + sx * gvs_agujeros[0]/2, gvs_centro[1] + sy * gvs_agujeros[1]/2]];
  difference() {
    union() {
      translate([0, 0, z_piso2]) linear_extrude(e_piso2) difference() {
        translate([x0, y0]) offset(r = 4) offset(delta = -4) square([x1 - x0, y1 - y0]);
        for (i = [0:2], j = [0:3]) translate([x0 + 7 + i * 19, y0 + 7 + j * 22.5]) offset(r = 3) square([13, 16]);
      }
      translate([0, 0, z_piso2]) linear_extrude(e_piso2 + 4) difference() {
        union() {
          difference() { translate([x0, y0]) offset(r = 4) offset(delta = -4) square([x1 - x0, y1 - y0]);
                         translate([x0, y0]) offset(delta = -2) offset(r = 4) offset(delta = -4) square([x1 - x0, y1 - y0]); }
          for (i = [0:3]) translate([x0 + 4 + i * 19, y0]) square([2, y1 - y0]);
          for (j = [0:4]) translate([x0, y0 + 4 + j * 22.5]) square([x1 - x0, 2]);
          for (c = columnas_piso2) translate(c) circle(d = 10);
        }
        translate([x0 - 1, -4]) square([x1 - x0 + 2, 8]);     // paso de cables a lo largo
      }
      for (p = gv) translate([p[0], p[1], z_piso2]) { cylinder(d = 6.5, h = e_piso2 + 8); translate([0, 0, e_piso2 + 8]) perno_una(pcb_perno_d, 1.6); }
      for (sx = [-1, 1]) translate([tb_centro[0] + sx * 15, tb_centro[1], z_piso2]) { cylinder(d = 8, h = e_piso2 + 4); translate([0, 0, e_piso2 + 4]) cylinder(d = perno_d, h = 4); }
    }
    for (c = columnas_piso2) translate([c[0], c[1], z_piso2 - 1]) agujero_perno(e_piso2 + 6);
    for (p = gv) translate([p[0], p[1], z_piso2 + e_piso2 + 8]) ranura_una(1.6, baja = 7, ancho = 8);
    for (y = [-30, 30]) translate([x1 - 6, y - 2, z_piso2 - 1]) cube([1.8, 4, 20]);      // bridas
  }
}
// Soporte del TB6612: marco elevado 16 mm (caben los conectores dupont por debajo), pines hacia
// abajo por dos ranuras; entra a presion en los pernos del piso 2 y la placa va con una brida.
// Se imprime de costado (ver orientar): acostado, el marco era un puente de 20 mm.
module soporte_tb_ens() {
  z0 = z_piso2 + e_piso2 + 4; h = 16; a = tb + 2*tol;
  translate([tb_centro[0], tb_centro[1], z0]) difference() {
    union() {
      translate([-a/2 - 1.6, -a/2 - 1.6, h - 2]) cube([a + 3.2, a + 3.2, 4]);
      for (sx = [-1, 1]) translate([sx * 15 - 5, -a/2 - 1.6, 0]) cube([10, a + 3.2, h + 2]);   // hasta arriba del marco: boca abajo apoyan en la cama
    }
    translate([-a/2, -a/2, h]) cube([a, a, 10]);
    for (sy = [-1, 1]) translate([-a/2 + 1, sy * (a/2 - 1.3) - 1.5, -1]) cube([a - 2, 3, 30]);   // pines
    for (sx = [-1, 1]) translate([sx * 15, 0, -0.01]) agujero_perno(4.5);
    for (sx = [-1, 1]) translate([sx * 7 - 0.9, -a/2 - 5, h - 3]) cube([1.8, a + 10, 1.4]);       // canal de la brida
  }
}

// =====================================================================================
// 10. ESCUADRA FRONTAL: cara vertical en el borde delantero con el HC-SR04 (INVERTIDO: su conector
// queda arriba y sale hacia atras por una ventana, por encima del chasis) y el VL53L0X encima,
// los dos clavados en pines de ubicacion a presion; pie con 2 remaches. Se imprime de costado: por eso
// el pie es del ancho de la cara (llega a la cama) y el refuerzo es un chaflan corrido (sale vertical);
// el chaflan se corta en el centro para que pase el conector del HC-SR04.
// =====================================================================================
module escuadra_frontal_ens() {
  e = 3; za = z_abajo - 2; zt = z_tof + vl[1]/2 + 3; ya = 25;
  difference() {
    union() {
      caja([x_frente, -ya, za], [x_frente + e, ya, zt]);                                   // cara
      caja([x_frente - 20, -ya, z_plano], [x_frente + 0.01, ya, z_plano + 3]);             // pie
      for (s = [-1, 1]) translate([0, s > 0 ? 9 : -ya, 0]) rotate([90, 0, 0]) translate([0, 0, -(ya - 9)])
        linear_extrude(ya - 9) polygon([[x_frente - 9, z_plano + 3], [x_frente + 0.01, z_plano + 3], [x_frente + 0.01, z_plano + 12]]);   // chaflan
      for (sy = [-1, 1], sz = [-1, 1]) translate([x_frente + e, sy * hc_agujeros[0]/2, z_us + sz * hc_agujeros[1]/2]) rotate([0, 90, 0]) {
        cylinder(d = 5, h = 3); translate([0, 0, 3]) cylinder(d = pin_d, h = 2.2); }
      for (sy = [-1, 1]) translate([x_frente + e, sy * vl_agujeros_sep/2, z_tof]) rotate([0, 90, 0]) {
        cylinder(d = 5, h = 3); translate([0, 0, 3]) cylinder(d = pin_d, h = 2.2); }
    }
    translate([x_frente - 1, -7, z_us + hc[1]/2 - 6]) cube([10, 14, 7]);       // conector del HC-SR04 (arriba al invertirlo)
    translate([x_frente - 1, -9, z_tof + vl[1]/2 - 3.5]) cube([10, 18, 4]);   // header del VL53L0X
    for (s = [-1, 1]) translate([x_frente - 14, s * 16, 0]) agujero_rem();
  }
}

// =====================================================================================
// 11. PIEZA DE PRUEBA: tramo de cola de milano (macho y hembra con la misma `tol`), un remache de
// 8 mm de agarre en su agujero, un perno a presion de 4 mm en su agujero ciego y un pasador de la
// caja TT en el agujero que aprieta. Ver README.
// =====================================================================================
module prueba_tolerancias() {
  h = 8;
  difference() {
    translate([0, -12, 0]) cube([34, 24, h]);
    translate([0, 0, -1]) linear_extrude(h + 2) polygon([[-1, -cola[0]/2 - tol], [cola[2] + tol, -cola[1]/2 - tol], [cola[2] + tol, cola[1]/2 + tol], [-1, cola[0]/2 + tol]]);
    translate([20, 6, 0]) agujero_rem();
    translate([29, 6, 2]) agujero_perno(10);
    translate([27, -6, 0]) cylinder(d = pasador_d - pasador_aprieto, h = 30, center = true);
    translate([18, -10.5, h - 0.6]) linear_extrude(1) text(str("t", tol), size = 3.2, halign = "center");
  }
  translate([-28, 0, 0]) {
    translate([-6, -12, 0]) cube([16, 24, h]);
    translate([10, 0, 0]) linear_extrude(h) polygon([[-1, -cola[0]/2], [cola[2], -cola[1]/2], [cola[2], cola[1]/2], [-1, cola[0]/2]]);
    translate([2, 0, h]) cylinder(d = perno_d, h = 6);
  }
  translate([0, 30, rem_d * 0.4]) rotate([90, 0, 0]) remache(h);
  translate([22, 30, 1.2]) rotate([90, 0, 0]) intersection() {
    union() { translate([0, 0, -1.5]) cylinder(d = 6, h = 1.5); cylinder(d = pasador_d, h = 12); }
    translate([-5, -1.2, -5]) cube([10, 2.4, 30]);
  }
}

// =====================================================================================
// Componentes comprados (solo para ver el ensamble; no se imprimen)
// =====================================================================================
// grupo: "todo" o uno de motores, ruedas, rodillos, encoders, baterias, esp32, tb, frente, ir, loca,
// cajas, vaso, espumas (el manual de armado los muestra paso a paso).
module componentes(grupo = "todo") {
  for (s = [-1, 1]) {
    if (grupo == "todo" || grupo == "motores") color("gold") translate([0, s * y_motor, 0]) rotate([90, 0, 0]) linear_extrude(tt_espesor, center = true) hull() {
      translate([x_eje, d_rueda/2]) circle(r = tt_semi); translate([x_eje, d_rueda/2 - tt_semi]) square([tt_largo_caja, 2*tt_semi]); }
    if (grupo == "todo" || grupo == "motores") color("silver") translate([x_eje + tt_largo_caja, s * y_motor, d_rueda/2]) rotate([0, 90, 0]) cylinder(d = tt_lata_d, h = tt_lata_largo - 2);
    if (grupo == "todo" || grupo == "ruedas") color("#222") translate([x_eje, s * y_rueda, d_rueda/2]) rotate([90, 0, 0]) cylinder(d = d_rueda, h = ancho_rueda, center = true, $fn = 60);
    if (grupo == "todo" || grupo == "ruedas") color("#f2c230") translate([x_eje, s * (y_rueda + 0.5), d_rueda/2]) rotate([90, 0, 0]) cylinder(d = d_rueda * 0.72, h = ancho_rueda + 1, center = true, $fn = 60);
    if (grupo == "todo" || grupo == "rodillos") color("#ccc") for (z = [7, 12]) translate([rodillo_x, s * rodillo_y, z + 1]) cylinder(d = 10, h = 4);
    if (grupo == "todo" || grupo == "encoders") if (con_encoders) color("#1e5aa8") translate([x_eje - 8.5 - 16, s * (W/2 - 30) - 7, d_rueda/2 - 18.6]) cube([32, 14, 1.6]);
  }
  if (grupo == "todo" || grupo == "baterias") color("#2a2a2a") for (s = [-1, 1]) translate([x_bateria + s * (celda_d/2 + 2), 0, z_plano + 2 + celda_d/2]) rotate([90, 0, 0]) cylinder(d = celda_d, h = 65, center = true);
  if (grupo == "todo" || grupo == "esp32") color("#1b1d22") translate([gvs_centro[0] - gvs[0]/2, gvs_centro[1] - gvs[1]/2, z_piso2 + e_piso2 + 8]) cube([gvs[0], gvs[1], 1.6]);
  if (grupo == "todo" || grupo == "esp32") color("#333") translate([gvs_centro[0] - 14, gvs_centro[1] - 25, z_piso2 + e_piso2 + 9.6]) cube([28, 50, 12]);
  if (grupo == "todo" || grupo == "tb") color("#7a2a8c") translate([tb_centro[0] - tb/2, tb_centro[1] - tb/2, z_piso2 + e_piso2 + 4 + 16]) cube([tb, tb, 1.6]);
  if (grupo == "todo" || grupo == "frente") color("#1e5aa8") translate([x_frente + 6, -hc[0]/2, z_us - hc[1]/2]) cube([1.6, hc[0], hc[1]]);
  if (grupo == "todo" || grupo == "frente") color("#ccc") for (s = [-1, 1]) translate([x_frente + 7.6, s * hc_tx_sep/2, z_us]) rotate([0, 90, 0]) cylinder(d = 16, h = 12);
  if (grupo == "todo" || grupo == "frente") color("#6b1fa3") translate([x_frente + 6, -vl[0]/2, z_tof - vl[1]/2]) cube([1.6, vl[0], vl[1]]);
  if (grupo == "todo" || grupo == "ir") color("#1e5aa8") translate([x_ir + 2 - (pcb_perno_d + 0.6)/2 - ir_placa[0]/2, -ir_placa[1]/2, ir_altura_piso + tcrt_alto]) cube([ir_placa[0], ir_placa[1], 1.6]);
  if (grupo == "todo" || grupo == "ir") color("#1b2b5a") for (i = [0:ir_n-1]) translate([x_ir + 2 - (pcb_perno_d + 0.6)/2 - 3, (i - (ir_n-1)/2) * ir_paso - 5, ir_altura_piso]) cube([6, 10, tcrt_alto]);
  if (grupo == "todo" || grupo == "loca") if (loca_tipo == "bola") color("silver") { translate([x_loca, 0, 8]) sphere(r = 8); translate([x_loca - 6, -15, loca_alto - 2]) cube([12, 30, 2]);
    translate([x_loca, 0, 8]) cylinder(r = 10.5, h = loca_alto - 10); }
  if (grupo == "todo" || grupo == "cajas") color("#111") translate([(x_caja_int[0] + x_caja_int[1]) / 2 - 6.5, W/2, z_plano + 2.5 + 11 - 1 - 7]) cube([13, 3, 14]);
  if (grupo == "todo" || grupo == "cajas") color("#111") translate([(x_caja_int[0] + x_caja_int[1]) / 2, -W/2, z_plano + 2.5 + 11 - 1]) rotate([90, 0, 0]) cylinder(d = 15, h = 3);
  // vaso colgado de los rieles
  if (grupo == "todo" || grupo == "vaso") color("#e8e2d0", 0.9) translate([x_vaso, 0, z_riel + r_riel]) {
    translate([0, 0, -vaso_h]) cylinder(d1 = vaso_d_fondo, d2 = vaso_d, h = vaso_h - 1, $fn = 60);
    cylinder(d = vaso_d + 2*vaso_reborde, h = 1.5, $fn = 60);
  }
  if (grupo == "todo" || grupo == "espumas") color("#ffd8a8") translate([x_mampara - espuma_e, -25, z_riel - 22]) cube([espuma_e, 50, 18]);
  if (grupo == "todo" || grupo == "espumas") color("#ffd8a8") translate([x_mampara - espuma_e + 1.2, -20, z_medio - 10]) cube([espuma_e - 1.2, 40, 20]);
}

// =====================================================================================
// Piezas: nombre -> modelo en su lugar del ensamble, y como se acuesta en la cama.
// =====================================================================================
PIEZAS = ["chasis", "soporte_motor_izq", "soporte_motor_der", "pared_cuna_izq", "pared_cuna_der", "mampara",
  "zapata_guia", "lengueta", "torre_rueda_loca", "barra_tcrt5000", "soporte_rodillo_izq", "soporte_rodillo_der",
  "porta_baterias", "caja_interruptor", "caja_fusible", "soporte_encoder_izq", "soporte_encoder_der", "piso2_esp32", "soporte_tb6612", "escuadra_frontal", "pasador_tt",
  "prueba_tolerancias"];   // + los remaches de REMACHES

module pieza_ens(n) {
  if (n == "chasis") chasis_ens();
  else if (n == "chasis_a") chasis_a();
  else if (n == "chasis_b") chasis_b();
  else if (n == "union_corte") union_corte_ens();
  else if (n == "soporte_motor_izq") soporte_motor_ens(1);
  else if (n == "soporte_motor_der") soporte_motor_ens(-1);
  else if (n == "soporte_encoder_izq") soporte_encoder_ens(1);
  else if (n == "soporte_encoder_der") soporte_encoder_ens(-1);
  else if (n == "pared_cuna_izq") pared_cuna_ens(1);
  else if (n == "pared_cuna_der") pared_cuna_ens(-1);
  else if (n == "mampara") mampara_ens();
  else if (n == "zapata_guia") zapata_ens(-45, 1);
  else if (n == "lengueta") lengueta_ens();
  else if (n == "torre_rueda_loca") torre_loca_ens();
  else if (n == "barra_tcrt5000") barra_ir_ens();
  else if (n == "soporte_rodillo_izq") soporte_rodillo_ens(1);
  else if (n == "soporte_rodillo_der") soporte_rodillo_ens(-1);
  else if (n == "porta_baterias") porta_bateria_ens();
  else if (n == "caja_interruptor") caja_int_ens(1);
  else if (n == "caja_fusible") caja_int_ens(-1);
  else if (n == "piso2_esp32") piso2_ens();
  else if (n == "soporte_tb6612") soporte_tb_ens();
  else if (n == "escuadra_frontal") escuadra_frontal_ens();
}

// Orientacion de impresion (rotacion que deja la cara indicada contra la cama). exportar.py
// apoya despues el STL en z = 0 y lo centra.
module orientar(n) {
  if (n == "soporte_motor_izq" || n == "soporte_motor_der" || n == "union_corte")
    mirror([0, 0, 1]) children();                                    // techo contra la cama, mejillas arriba
  else if (n == "barra_tcrt5000") rotate([0, 90, 0]) children();    // de costado: la U queda en el plano de la cama, sin puentes
  else if (n == "pared_cuna_izq") rotate([90, 0, 0]) children();   // cara interior (la del vaso) abajo
  else if (n == "pared_cuna_der") rotate([-90, 0, 0]) children();
  else if (n == "zapata_guia") rotate([90, 0, 0]) children();      // cara del vaso abajo (lisa, para la cinta PTFE), pernos arriba
  else if (n == "mampara") rotate([0, 90, 0]) children();           // cara de adelante abajo
  else if (n == "caja_interruptor") rotate([-90, 0, 0]) children(); // panel abajo
  else if (n == "caja_fusible") rotate([90, 0, 0]) children();
  else if (n == "escuadra_frontal") rotate([-90, 0, 0]) children(); // de costado
  else if (n == "soporte_tb6612") rotate([90, 0, 0]) children();    // de costado: la "Pi" de patas y marco sube derecho (acostado era un puente de 20 mm; boca abajo, el hueco de la placa quedaba de techo)
  else children();
}

module imprimir(n) {
  if (n == "prueba_tolerancias") prueba_tolerancias();
  else if (n == "pasador_tt") rotate([90, 0, 0]) pasador_tt();     // acostado sobre una cara plana
  else if (search([n], [for (r = REMACHES) r[0]])[0] != []) rotate([90, 0, 0]) remache(REMACHES[search([n], [for (r = REMACHES) r[0]])[0]][1]);
  else orientar(n) pieza_ens(n);
}

if (pieza == "ensamble") {
  color("#e4572e") chasis_ens();
  color("#f3a712") for (s = [-1, 1]) { soporte_motor_ens(s); soporte_rodillo_ens(s); if (con_encoders) soporte_encoder_ens(s); }
  color("#4c9f70") { pared_cuna_ens(1); pared_cuna_ens(-1); mampara_ens(); zapata_ens(-45, 1); zapata_ens(-5, 1); zapata_ens(-45, -1); zapata_ens(-5, -1); }
  color("#d9261a") lengueta_ens();
  color("#3a6ea5") { torre_loca_ens(); barra_ir_ens(); escuadra_frontal_ens(); }
  color("#9b9b9b") { porta_bateria_ens(); caja_int_ens(1); caja_int_ens(-1); piso2_ens(); soporte_tb_ens(); }
  componentes();
} else if (pieza == "ensamble_impreso") {
  chasis_ens();
  for (s = [-1, 1]) { soporte_motor_ens(s); soporte_rodillo_ens(s); pared_cuna_ens(s); zapata_ens(-45, s); zapata_ens(-5, s); if (con_encoders) soporte_encoder_ens(s); }
  mampara_ens(); lengueta_ens(); torre_loca_ens(); barra_ir_ens(); escuadra_frontal_ens();
  porta_bateria_ens(); caja_int_ens(1); caja_int_ens(-1); piso2_ens(); soporte_tb_ens();
} else if (pieza == "ensamble_pieza") {
  pieza_ens(cual);          // una pieza en su lugar del ensamble (choques y render)
} else if (pieza == "componentes") {
  componentes();
} else {
  imprimir(pieza);
}
