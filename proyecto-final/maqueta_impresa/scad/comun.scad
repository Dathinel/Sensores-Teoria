// =====================================================================================
// MAQUETA IMPRESA: convenciones comunes (usuario, 2026-10-24: toda la maqueta en PLA, sin aluminio).
//
// Marco: el MISMO de sim/mundo.py y del visor, pero en MILIMETROS: x a lo largo de las cintas, y a lo
// ancho (-y = lado del operador: canaleta y carro; +y = pórtico y caja de control), z arriba, z = 0 el
// piso. Cada pieza se modela EN SU LUGAR del ensamble; para imprimirla se gira con su orientacion
// (PIEZAS en maqueta.scad) y exportar.py la apoya en la cama.
//
// Uniones: remaches impresos (los del carro) a traves de paredes, y tubos que se empalman sobre munones.
// Regla aprendida con el carro (2026-10-24): el agarre de cada remache NO se calcula, se MIDE en el
// ensamble (revisar.py): cada remache declarado en una lista REM_* se comprueba contra lo que de verdad
// junta, que del otro lado quede hueco para la una y que no choque con nada.
// =====================================================================================
$fn = 40;

cama = [260, 260, 300];      // Creality Hi: volumen util
margen_cama = 10;
largo_max = 240;             // pieza mas larga que se acepta (deja margen en la cama de 260)
tol = 0.2;                   // holgura de encaje por lado (la misma del carro, probada)

// ----------------------------------------------------------------- remache impreso (igual al del carro)
rem_d = 4;
rem_agujero = rem_d + 2 * tol;   // 4.4
rem_cabeza = [8, 1.6];           // largo y alto de la cabeza (la cabeza es una tira de 8 x 3.2)
rem_garra = 0.45;
rem_ranura = 1.2;
rem_plano = rem_d * 0.8;         // ancho de las caras planas (3.2): se imprime acostado
rem_agarre_max = 20;             // con mas agarre el vastago se dobla antes de salir (el de 37 del carro fallo)
rem_hueco_una = 3;               // del otro lado tiene que haber al menos esto libre para que la una abra

// Remache: cabeza en z < 0, vastago de `agarre` en +z y una que traba en la cara de enfrente.
module remache(agarre) {
  intersection() {
    difference() {
      union() {
        translate([0, 0, -rem_cabeza[1]]) hull() for (s = [-1, 1]) translate([s * (rem_cabeza[0] - rem_plano) / 2, 0, 0]) cylinder(d = rem_plano, h = rem_cabeza[1]);
        cylinder(d = rem_d, h = agarre + 0.2);
        translate([0, 0, agarre + 0.2]) cylinder(d1 = rem_d + 2 * rem_garra, d2 = rem_d - 0.8, h = 2.6);
      }
      // en los cortos (agarre < 8) la ranura empieza DENTRO de la cabeza (queda 1 mm de puente): desde 0,3 agarre la pata del
      // de 4,2 media 3,1 y al entrar se deformaba 2-3 veces mas que los del carro (que si funcionaron); asi queda en ~1,4 %
      // (FEM de la auditoria, 2026-10-25). Desde 8 sigue como en el carro.
      translate([-rem_ranura / 2, -10, agarre < 8 ? -0.6 : agarre * 0.3]) cube([rem_ranura, 20, agarre + 10]);
    }
    translate([-10, -rem_plano / 2, -10]) cube([20, rem_plano, agarre + 20]);
  }
}

// ----------------------------------------------------------------- ejes locales
// Marco local de un eje: z a lo largo de (p1 - p0), y hacia `arriba` (proyectado), x = y x z.
function unit(v) = v / norm(v);
function _y(z, arriba) = unit(arriba - (arriba * z) * z);
function marco(p0, p1, arriba) = let(z = unit(p1 - p0), y = _y(z, arriba), x = cross(y, z))
  [[x[0], y[0], z[0], p0[0]], [x[1], y[1], z[1], p0[1]], [x[2], y[2], z[2], p0[2]], [0, 0, 0, 1]];
module en_marco(p0, p1, arriba) multmatrix(marco(p0, p1, arriba)) children();
// un vector cualquiera que no sea paralelo a d (para elegir `arriba` por defecto)
function no_paralelo(d) = abs(unit(d)[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0];

// Remache en el mundo: [nombre_union, agarre_nominal, punto donde apoya la cabeza, eje (cabeza -> una)].
// El agarre nominal es lo que se DISENO; revisar.py mide el real. Se imprime con la medida redondeada.
module remache_en(r) en_marco(r[2], r[2] + r[3], no_paralelo(r[3])) remache(r[1]);
// Agujero de un remache: atraviesa solo lo que junta (desde la cabeza hasta el agarre + 0,5).
module agujero_rem_en(r) en_marco(r[2], r[2] + r[3], no_paralelo(r[3]))
  translate([0, 0, -2]) cylinder(d = rem_agujero, h = r[1] + 2.5, $fn = 24);
// cajera para la cabeza cuando no se quiere que sobresalga (opcional en cada pieza)
module cajera_cabeza_en(r, hondo = 1.8) en_marco(r[2], r[2] + r[3], no_paralelo(r[3]))
  translate([-(rem_cabeza[0] + 0.6) / 2, -(rem_plano + 0.6) / 2, -0.01]) cube([rem_cabeza[0] + 0.6, rem_plano + 0.6, hondo]);

// ----------------------------------------------------------------- tubo impreso 16 x 16
// Reemplaza al perfil 2020 (la carga es poca: la viga mas cargada flecta 0,5 mm con 900 g; ver esfuerzos.md).
// Se imprime ACOSTADO: el hueco es un octogono (las 4 esquinas cortadas a 45 grados), asi el techo es un puente
// de 6,8 mm (sale sin soportes) GIRE COMO GIRE el tubo sobre su eje: estructura_a_cama elige el giro que deja la
// cara con agujeros de remache hacia un costado y la cara de apoyo lisa (2026-10-24: los circulos chicos en la
// primera capa se levantaban).
lado_tubo = 16;
pared_tubo = 1.6;
chaflan_hueco = 3;
module hueco_tubo_2d(o = 0) let(a = lado_tubo / 2 - pared_tubo, c = chaflan_hueco)
  offset(delta = -o) polygon([[-a + c, -a], [a - c, -a], [a, -a + c], [a, a - c], [a - c, a], [-a + c, a], [-a, a - c], [-a, -a + c]]);
module seccion_tubo() difference() { square(lado_tubo, center = true); hueco_tubo_2d(); }
module tubo(p0, p1, arriba = [0, 0, 1]) en_marco(p0, p1, arriba) linear_extrude(norm(p1 - p0)) seccion_tubo();

// Cajera de un nodo (donde entra el tubo entero): cuadrado de lado_tubo + 2 tol con un "alero" encima de
// 45 grados que termina en un puente de 10 mm (asi el techo de la cajera sale sin soportes). Su arriba es el
// arriba DE LA CAMA del nodo, no el del tubo (el tubo es cuadrado: entra en cualquier posicion).
pared_nodo = 2.4;
module cajera_2d() let(h = lado_tubo / 2 + tol, k = h - 5)
  polygon([[-h, -h], [h, -h], [h, h], [h - k, h + k], [-h + k, h + k], [-h, h]]);
module brazo_2d() offset(delta = pared_nodo) cajera_2d();
// Cajera de un tubo vertical que entra desde abajo (nodo dado vuelta): el fondo es una piramide de 45 grados.
