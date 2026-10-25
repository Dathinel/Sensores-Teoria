// =====================================================================================
// MAQUETA IMPRESA: ensamble de todo (estructura + subsistemas) en el marco del mundo, en mm.
//   modo = "ensamble":  todas las piezas en su lugar (y los remaches)
//   modo = "pieza":     una pieza (cual) en su lugar
//   modo = "cama":      una pieza (cual) girada para imprimir (exportar.py la apoya en la cama)
//   modo = "remaches":  solo los remaches en su lugar
// Cada subsistema (otro .scad) define: <sub>_ens(), <sub>_pieza(n), <sub>_a_cama(n) { children },
// PIEZAS_<SUB> (nombres) y REM_<SUB> (remaches que declara).
// =====================================================================================
include <estructura.scad>
include <moviles_por_defecto.scad>
include <almacen.scad>
include <cinta_monedas.scad>
include <cinta_vasos.scad>
include <tapas_prensa_empujador.scad>
include <canaleta_muelle.scad>

modo = "ensamble";
cual = "";

REM_TODOS = concat(REM_ESTRUCTURA, REM_ALM, REM_MON, REM_VAS, REM_TAP, REM_CAN);
AGUJEROS = concat(AGUJEROS_ALM, AGUJEROS_MON, AGUJEROS_VAS, AGUJEROS_TAP, AGUJEROS_CAN);
MOVILES = concat(MOVILES_ALM, MOVILES_MON, MOVILES_VAS, MOVILES_TAP, MOVILES_CAN);
PIEZAS = concat(PIEZAS_ESTRUCTURA, PIEZAS_ALM, PIEZAS_MON, PIEZAS_VAS, PIEZAS_TAP, PIEZAS_CAN);

function _de(lista, n) = search([n], lista)[0] != [];
// Una pieza en su lugar, con los agujeros de TODOS los remaches que la atraviesan.
module pieza(n) difference() {
  if (_de(PIEZAS_ESTRUCTURA, n)) estructura_pieza(n);
  else if (_de(PIEZAS_ALM, n)) alm_pieza(n);
  else if (_de(PIEZAS_MON, n)) mon_pieza(n);
  else if (_de(PIEZAS_VAS, n)) vas_pieza(n);
  else if (_de(PIEZAS_TAP, n)) tap_pieza(n);
  else if (_de(PIEZAS_CAN, n)) can_pieza(n);
  for (r = REM_TODOS) agujero_rem_en(r);
  for (a = AGUJEROS) en_marco(a[0], a[1], no_paralelo(a[1] - a[0])) translate([0, 0, -0.01]) cylinder(d = a[2], h = norm(a[1] - a[0]) + 0.02, $fn = 32);
}
module a_cama(n) {
  if (_de(PIEZAS_ESTRUCTURA, n)) estructura_a_cama(n) children();
  else if (_de(PIEZAS_ALM, n)) alm_a_cama(n) children();
  else if (_de(PIEZAS_MON, n)) mon_a_cama(n) children();
  else if (_de(PIEZAS_VAS, n)) vas_a_cama(n) children();
  else if (_de(PIEZAS_TAP, n)) tap_a_cama(n) children();
  else if (_de(PIEZAS_CAN, n)) can_a_cama(n) children();
}

// Barrido de una pieza que se mueve (todo su recorrido): lo define su subsistema.
function _de_mov(l, n) = search([n], [for (m = l) m[0]])[0] != [];
module barrido(n) {
  if (_de_mov(MOVILES_ALM, n)) alm_barrido(n);
  else if (_de_mov(MOVILES_MON, n)) mon_barrido(n);
  else if (_de_mov(MOVILES_VAS, n)) vas_barrido(n);
  else if (_de_mov(MOVILES_TAP, n)) tap_barrido(n);
  else if (_de_mov(MOVILES_CAN, n)) can_barrido(n);
}

// lo comprado (motores, servos, bandas, rodillos...), solo para ver y revisar choques: cada subsistema lo agrega
module comprados() { alm_comprados(); mon_comprados(); vas_comprados(); tap_comprados(); can_comprados(); }
HAY_COMPRADOS = true;

if (modo == "lista") {
  for (n = PIEZAS) echo(PIEZA = n);
  for (r = REM_TODOS) echo(REM = r);
  echo(COMPRADOS = HAY_COMPRADOS);
  for (m = MOVILES) echo(MOVIL = m);
}
else if (modo == "comprados") comprados();
else if (modo == "barrido") barrido(cual);
else if (modo == "ensamble") { for (n = PIEZAS) pieza(n); color("#d22") for (r = REM_TODOS) remache_en(r); comprados(); }
else if (modo == "pieza") pieza(cual);
else if (modo == "cama") a_cama(cual) pieza(cual);
else if (modo == "remaches") for (r = REM_TODOS) remache_en(r);
