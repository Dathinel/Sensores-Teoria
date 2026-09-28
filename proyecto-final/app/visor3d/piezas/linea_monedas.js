// Piezas de la LINEA DE MONEDAS: cinta indexada (rodillos, cojinetes, soporte del motor, platina
// de los sensores M18), descarga (compuerta de desvio, bandeja de rechazo) y almacen tipo
// revolver (placa fija, disco del carrusel, tubos de policarbonato, obturador, soporte del
// 28BYJ-48). Convencion: ver README.md de esta carpeta. Marco de la simulacion (x a lo largo,
// y a lo ancho, z arriba), metros; las medidas de ficha van en mm y se pasan con MM.
//
// Contenido (agregar funciones nuevas AL FINAL):
//   crearRodilloCinta(opciones)       rodillo motriz (con recubrimiento de goma) o tensor, con eje
//   crearCojinete608(opciones)        bloque impreso con rodamiento 608ZZ (fijo o tensor)
//   crearAcople(opciones)             acople de eje: flexible (helicoidal) o rigido
//   crearSoporteNEMA17(opciones)      jaula impresa que separa el NEMA17 del riel (deja el acople)
//   crearPlatinaM18(opciones)         platina de aluminio con agujero M18, escuadras y contratuerca
//   crearCompuertaDesvio(opciones)    aleta de desvio con su bisagra y el cubo que va al cuerno
//   crearOrejaBisagra(opciones)       oreja impresa que sostiene el pasador del otro lado
//   crearBridaServo(opciones)         brida impresa que toma un servo por sus pestañas
//   crearBandejaRechazo(opciones)     bandeja impresa de rechazo con rotulo
//   crearPlacaFijaAlmacen(opciones)   placa fija con UN agujero, alojamiento del rodamiento
//   crearDiscoCarrusel(opciones)      disco de acrilico con los 6 agujeros, cubo e iman
//   crearTuboMonedas(opciones)        tubo de policarbonato con etiqueta curva de denominacion
//   crearObturadorAlmacen(opciones)   aleta del obturador con nudillo, pasador y cubo al cuerno
//   crearSoporteMotorCarrusel(opc.)   placa impresa del 28BYJ-48 (eje del motor = eje del carrusel)
//   crearListon(a, b, ancho, alto)    barra rectangular entre dos puntos (brazos de soporte)
//   crearPosteCamaraCenital(opc.)     poste 2020 + brazo + abrazadera de la camara cenital
//
// De donde salen las medidas:
//   - config/parametros.yaml: casillas de 40 mm (cinta_monedas.separacion_casilla_mm).
//   - sim/geometria.py (GET /api/geometria): ancho de la cinta 55 mm, superficie a 452 mm,
//     rodillos de Ø22 (radio 11 mm, el mismo que usa moverCinta), almacen (centro, radio 33 mm,
//     tubos Ø29 interior × 58 mm, placa a 270 mm, disco a 328 mm, tolva, agujero a 300°).
//   - sim/catalogos.py: NEMA17 17HS4401 en la cinta, 28BYJ-48 + ULN2003 en el carrusel (NO un
//     NEMA17), SG90 en desvio y obturador, drivers de las cintas EN la caja de control.
//   - Fichas: rodamiento 608ZZ (8 × 22 × 7 mm); acople flexible 5-8 mm (Ø19 × 25 mm); acople
//     rigido 5-8 (Ø12 × 16 mm); tuerca M18 × 1 (24 mm entre caras, 4 mm); iman N35 6 × 3 mm.
import * as THREE from 'three';
import { MM, COLOR, METAL, PLASTICO, P, mat, caja, cilindro, ancla, planoDibujado, terminar } from './base.js';

const ALU = { metalness: 0.75, roughness: 0.38 };
const ACERO = { metalness: 0.85, roughness: 0.3 };
const IMPRESO = COLOR.impreso;

function datos(o = {}) {
  const d = {};
  if (o.idComponente) d.idComponente = o.idComponente;
  if (o.sensorId) d.sensorId = o.sensorId;
  return d;
}

// Cilindro con el eje a lo largo de un eje de la simulacion ('x', 'y' o 'z').
function cil(r, largo, color, centro, eje = 'z', extra = {}, seg = 28) {
  const m = cilindro(r, largo, color, centro, extra, seg);
  if (eje === 'x') m.rotation.z = Math.PI / 2;
  if (eje === 'y') m.rotation.x = Math.PI / 2;
  return m;
}

// Losa: una forma 2D (en el plano x-y de la simulacion, metros) extruida `espesor` hacia +z,
// con la cara de abajo en z = 0. Las formas con agujeros (THREE.Path en `holes`) quedan huecas.
function losa(forma, espesor, color, extra = {}) {
  const geo = new THREE.ExtrudeGeometry(forma, { depth: espesor, bevelEnabled: false, curveSegments: 40 });
  geo.rotateX(-Math.PI / 2);
  const m = new THREE.Mesh(geo, color && color.isMaterial ? color : mat(color, extra));
  m.castShadow = true;
  m.receiveShadow = true;
  return m;
}
const agujero = (r, x = 0, y = 0) => { const p = new THREE.Path(); p.absarc(x, y, r, 0, Math.PI * 2, true); return p; };
function circuloForma(r, x = 0, y = 0) { const s = new THREE.Shape(); s.absarc(x, y, r, 0, Math.PI * 2, false); return s; }
function rectRedondeado(l, a, r, cx = 0, cy = 0) {
  const s = new THREE.Shape();
  const x0 = cx - l / 2, y0 = cy - a / 2;
  s.moveTo(x0 + r, y0);
  s.lineTo(x0 + l - r, y0); s.absarc(x0 + l - r, y0 + r, r, -Math.PI / 2, 0, false);
  s.lineTo(x0 + l, y0 + a - r); s.absarc(x0 + l - r, y0 + a - r, r, 0, Math.PI / 2, false);
  s.lineTo(x0 + r, y0 + a); s.absarc(x0 + r, y0 + a - r, r, Math.PI / 2, Math.PI, false);
  s.lineTo(x0, y0 + r); s.absarc(x0 + r, y0 + r, r, Math.PI, 1.5 * Math.PI, false);
  return s;
}
function rectAgujero(l, a, cx = 0, cy = 0) {
  const p = new THREE.Path();
  p.moveTo(cx - l / 2, cy - a / 2); p.lineTo(cx - l / 2, cy + a / 2); p.lineTo(cx + l / 2, cy + a / 2); p.lineTo(cx + l / 2, cy - a / 2);
  p.closePath();
  return p;
}
// Cabeza de tornillo Allen (ISO 4762) vista desde afuera, eje en `eje`, apoyada en `pos`.
function tornillo(g, pos, eje = 'z', d = 3, signo = 1) {
  const r = d * 0.8 * MM, h = d * 0.6 * MM;
  const off = { x: P(1, 0, 0), y: P(0, 1, 0), z: P(0, 0, 1) }[eje].multiplyScalar(signo * h / 2);
  g.add(cil(r, h, 0x2a2d31, pos.clone().add(off), eje, ACERO, 14));
  const off2 = off.clone().multiplyScalar(2.02);
  g.add(cil(r * 0.45, 0.0002, 0x050505, pos.clone().add(off2), eje, {}, 6));
}
// Tuerca hexagonal con eje vertical (sim z).
function tuerca(entreCaras, alto, pos, color = 0xc9ccd1) {
  const r = entreCaras / Math.sqrt(3);
  return cilindro(r, alto, color, pos, METAL, 6);
}

// Arandela plana (anillo con espesor), eje vertical, cara de abajo en `pos`.
function arandela(rIn, rOut, h, pos, color = 0xd6d9dd) {
  const m = new THREE.Mesh(new THREE.LatheGeometry([new THREE.Vector2(rIn, 0), new THREE.Vector2(rOut, 0),
    new THREE.Vector2(rOut, h), new THREE.Vector2(rIn, h), new THREE.Vector2(rIn, 0)], 32), mat(color, METAL));
  m.position.copy(pos);
  return m;
}

// Barra rectangular (liston) entre dos puntos de Three: brazos de soporte impresos o de
// aluminio. `ancho` es horizontal (perpendicular al tramo), `alto` el otro lado.
export function crearListon(a, b, ancho, alto, color = IMPRESO, extra = {}) {
  const d = new THREE.Vector3().subVectors(b, a);
  const m = new THREE.Mesh(new THREE.BoxGeometry(ancho, alto, d.length()), color && color.isMaterial ? color : mat(color, extra));
  m.position.copy(a).addScaledVector(d, 0.5);
  const arriba = Math.abs(d.clone().normalize().y) > 0.99 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
  m.up.copy(arriba);
  m.lookAt(b);
  m.castShadow = true;
  return m;
}

// ==================================================================================
// Rodillo de la cinta: tubo de aluminio Ø22 (radio 11 mm, el de moverCinta) de `largo`,
// tapas, una raya para que se VEA girar y el eje de acero Ø8.
//   motriz: true -> recubrimiento de goma con ranuras (agarra la banda sin patinar).
// Origen: centro del rodillo. Eje del rodillo = Y de Three (vertical sin rotar). Se pone con
// `rotation.x = Math.PI / 2` (el eje queda a lo ancho de la cinta: +Y local -> -y de la
// simulacion) y se gira con `rotation.y`, igual que los rodillos que ya animaba moverCinta.
// ejeMas / ejeMenos: cuanto sale el eje hacia +y / -y de la SIMULACION (ya montado).
// Nodos: tubo, eje. Anclas: ancla_eje_mas, ancla_eje_menos (puntas del eje, en local).
// ==================================================================================
export function crearRodilloCinta(opciones = {}) {
  const { largo = 0.059, radio = 11 * MM, motriz = false, ejeMas = 0.062, ejeMenos = 0.062 } = opciones;
  const g = new THREE.Group();
  g.name = motriz ? 'rodillo_motriz' : 'rodillo_tensor';
  const Y = (y) => new THREE.Vector3(0, y, 0);
  const tubo = new THREE.Mesh(new THREE.CylinderGeometry(radio, radio, largo - 2 * MM, 40),
    motriz ? mat(0x26292e, { roughness: 0.92 }) : mat(0xb8bec6, ALU));
  tubo.name = 'tubo';
  tubo.castShadow = true;
  g.add(tubo);
  // Tapas de aluminio (con el eje pasante) y, si es motriz, las ranuras de la goma.
  for (const s of [-1, 1]) {
    g.add(cilindro(radio * 0.93, 1 * MM, 0x9aa1ab, Y(s * (largo / 2 - 0.5 * MM)), ALU, 32));
  }
  if (motriz) {
    const n = 7;
    for (let i = 0; i < n; i++) {
      const anillo = new THREE.Mesh(new THREE.TorusGeometry(radio + 0.05 * MM, 0.35 * MM, 4, 40), mat(0x111214, { roughness: 1 }));
      anillo.rotation.x = Math.PI / 2;
      anillo.position.y = -largo / 2 + (i + 1) * (largo / (n + 1));
      g.add(anillo);
    }
  }
  // Raya a lo largo: con ella se ve el giro (la banda tapa solo media vuelta).
  const raya = new THREE.Mesh(new THREE.BoxGeometry(0.6 * MM, largo * 0.92, 2 * MM), mat(motriz ? 0xf2b134 : 0x3a3f46));
  raya.position.set(0, 0, radio);
  g.add(raya);
  // Eje de acero Ø8: +Y local = -y de la simulacion una vez montado.
  const eje = cilindro(4 * MM, ejeMas + ejeMenos, 0xd0d3d8, Y((ejeMenos - ejeMas) / 2), ACERO, 20);
  eje.name = 'eje';
  g.add(eje);
  // Collarines (anillos de fijacion) contra los cojinetes no: el cojinete ya tiene prisionero.
  g.add(ancla('ancla_eje_mas', Y(-ejeMas)), ancla('ancla_eje_menos', Y(ejeMenos)));
  return terminar(g, { datos: datos(opciones) });
}

// ==================================================================================
// Bloque impreso con rodamiento 608ZZ (8 × 22 × 7 mm) para la punta de un rodillo.
// Bloque de 30 (x) × 9 (y) × 22 (z) mm, atornillado al costado del riel 2020 con 2 M4 y
// tuercas en T. `tensor: true` -> los agujeros son colisos (6 mm de carrera) y un tornillo
// tensor M4 empuja el bloque hacia afuera de la cinta desde una oreja fija.
// Origen: centro del rodamiento en la cara que APOYA en el riel. `lado` (+1/-1): hacia que
// lado de la simulacion (+y/-y) crece el bloque. `haciaFuera` (+1/-1): hacia que x queda el
// extremo de la cinta (el tensor tira hacia ahi).
// ==================================================================================
export function crearCojinete608(opciones = {}) {
  const { lado = 1, tensor = false, haciaFuera = 1 } = opciones;
  const g = new THREE.Group();
  g.name = tensor ? 'cojinete_tensor' : 'cojinete_608';
  const t = 9 * MM, yc = lado * t / 2, yf = lado * t;
  g.add(caja(30 * MM, t, 22 * MM, IMPRESO, P(0, yc, 0), PLASTICO));
  // Rodamiento: pista exterior, sello negro y pista interior (se ven desde afuera).
  g.add(cil(11 * MM, 0.6 * MM, 0xc9ccd1, P(0, yf + lado * 0.3 * MM, 0), 'y', METAL, 32));
  g.add(cil(9.6 * MM, 0.7 * MM, 0x151618, P(0, yf + lado * 0.35 * MM, 0), 'y', { roughness: 0.6 }, 32));
  g.add(cil(6 * MM, 0.8 * MM, 0xd0d3d8, P(0, yf + lado * 0.4 * MM, 0), 'y', METAL, 24));
  // Tornillos M4 a ±11 mm (los del tensor, en colisos).
  for (const s of [-1, 1]) {
    const pos = P(s * 11 * MM, yf, 0);
    if (tensor) g.add(caja(7 * MM, 0.2 * MM, 4.4 * MM, 0x0a0a0a, P(s * 11 * MM, yf + lado * 0.1 * MM, 0)));
    tornillo(g, pos, 'y', 4, lado);
  }
  if (tensor) {
    // Oreja fija (atornillada al riel) y tornillo tensor M4 que empuja la cara interior.
    const xo = -haciaFuera * (15 + 9) * MM;
    g.add(caja(6 * MM, t, 14 * MM, IMPRESO, P(xo, yc, 0), PLASTICO));
    tornillo(g, P(xo, yf, 0), 'y', 4, lado);
    g.add(cil(2 * MM, 16 * MM, 0xd0d3d8, P(-haciaFuera * (15 + 8) * MM + haciaFuera * 5 * MM, yc, 5 * MM), 'x', ACERO, 12));
    g.add(cil(3.5 * MM, 3 * MM, 0x2a2d31, P(-haciaFuera * (15 + 12.5) * MM, yc, 5 * MM), 'x', ACERO, 6));
    g.add(caja(4 * MM, t, 6 * MM, IMPRESO, P(-haciaFuera * 17 * MM, yc, 5 * MM), PLASTICO));   // tope del tornillo
  }
  return terminar(g, { datos: datos(opciones) });
}

// ==================================================================================
// Acople de eje. flexible: aluminio Ø19 × 25 mm con corte helicoidal (5 a 8 mm), el que une el
// NEMA17 al rodillo motriz; rigido: Ø12 × 16 mm (5 a 8 mm), 28BYJ-48 al eje del carrusel.
// Origen: centro del acople; eje a lo largo de z de la simulacion (Y de Three).
// ==================================================================================
export function crearAcople(opciones = {}) {
  const { tipo = 'flexible' } = opciones;
  const d = opciones.diametro || (tipo === 'flexible' ? 19 * MM : 12 * MM);
  const L = opciones.largo || (tipo === 'flexible' ? 25 * MM : 16 * MM);
  const g = new THREE.Group();
  g.name = `acople_${tipo}`;
  g.add(cilindro(d / 2, L, tipo === 'flexible' ? 0xc4cad2 : 0xb0b6be, P(0, 0, 0), ALU, 32));
  if (tipo === 'flexible') {
    for (let i = -2; i <= 2; i++) {
      const r = new THREE.Mesh(new THREE.TorusGeometry(d / 2 + 0.05 * MM, 0.35 * MM, 4, 32), mat(0x2a2d31));
      r.rotation.x = Math.PI / 2 + 0.12;
      r.position.y = i * 2.2 * MM;
      g.add(r);
    }
  }
  // Prisioneros en cada punta.
  for (const s of [-1, 1]) g.add(cil(1.2 * MM, 0.4 * MM, 0x151515, P(d / 2, 0, s * L * 0.33), 'x', {}, 8));
  return terminar(g, { datos: datos(opciones) });
}

// ==================================================================================
// Jaula impresa del NEMA17 (PETG, 4 mm): placa frontal de 50 × 50 mm con el agujero Ø23 del
// resalte y los 4 M3 a 31 mm, dos paredes laterales hasta el riel y dos alas con 2 M5 a la
// ranura del perfil. Deja lugar adentro para el cojinete y el acople.
// Marco local = el del NEMA17 de electronica.js: origen en la CARA DE MONTAJE del motor, eje +z
// (hacia el riel). La placa va de z = 0 a 4 mm; las paredes hasta z = `distancia` (cara del
// riel). Con `rotation.x = Math.PI / 2` (Three) el +z local apunta a -y de la simulacion.
// ==================================================================================
export function crearSoporteNEMA17(opciones = {}) {
  const { distancia = 0.0465 } = opciones;
  const g = new THREE.Group();
  g.name = 'soporte_nema17';
  const m = mat(IMPRESO, PLASTICO);
  const placa = rectRedondeado(50 * MM, 50 * MM, 4 * MM);
  placa.holes.push(agujero(11.5 * MM));
  for (const [sx, sy] of [[1, 1], [-1, 1], [-1, -1], [1, -1]]) placa.holes.push(agujero(1.7 * MM, sx * 15.5 * MM, sy * 15.5 * MM));
  g.add(losa(placa, 4 * MM, m));
  for (const [sx, sy] of [[1, 1], [-1, 1], [-1, -1], [1, -1]]) tornillo(g, P(sx * 15.5 * MM, sy * 15.5 * MM, 4 * MM), 'z', 3, 1);
  const largoPared = distancia - 4 * MM;
  for (const s of [-1, 1]) {
    g.add(caja(4 * MM, 50 * MM, largoPared, m, P(s * 23 * MM, 0, 4 * MM + largoPared / 2)));
    // Ala contra el riel, con sus dos M5 (tuerca en T en la ranura).
    g.add(caja(14 * MM, 20 * MM, 4 * MM, m, P(s * 32 * MM, 0, distancia - 2 * MM)));
    tornillo(g, P(s * 32 * MM, 0, distancia - 4 * MM), 'z', 5, -1);
  }
  return terminar(g, { datos: datos(opciones) });
}

// ==================================================================================
// Platina de aluminio (3 mm) que sostiene un sensor M18 BAJO la cinta, en la ventana de la
// bancada: agujero Ø18,5, dos escuadras de aluminio (15 × 12 × 2 mm) atornilladas a la cara
// interior de cada riel y, debajo, la contratuerca M18 (24 mm entre caras, 4 mm) con su arandela.
// La tuerca de ARRIBA es la del propio sensor (sensores.js / sensorCilindrico) y apoya en la
// arandela de arriba: la cara del sensor queda a ras, 0,5 mm bajo la banda.
// Origen: centro del agujero en la cara de ARRIBA de la platina.
// ==================================================================================
export function crearPlatinaM18(opciones = {}) {
  const { largo = 36 * MM, ancho = 61 * MM, espesor = 3 * MM, contratuerca = true } = opciones;
  const g = new THREE.Group();
  g.name = 'platina_m18';
  const forma = rectRedondeado(largo, ancho - 1 * MM, 2 * MM);
  forma.holes.push(agujero(9.25 * MM));
  const pl = losa(forma, espesor, 0xb9c0c9, ALU);
  pl.position.y = -espesor;
  g.add(pl);
  // Arandela de arriba (apoyo de la tuerca del sensor) y contratuerca abajo.
  g.add(arandela(9.3 * MM, 15 * MM, 1 * MM, P(0, 0, 0)));
  if (contratuerca) {
    g.add(arandela(9.3 * MM, 15 * MM, 1 * MM, P(0, 0, -espesor - 1 * MM)));
    g.add(tuerca(24 * MM, 4 * MM, P(0, 0, -espesor - 1 * MM - 2 * MM)));
  }
  // Escuadras contra la cara interior de cada riel (ala vertical) y sobre la platina.
  for (const s of [-1, 1]) {
    const yv = s * (ancho / 2 - 1 * MM);
    g.add(caja(largo - 8 * MM, 2 * MM, 12 * MM, 0xa9b1bb, P(0, yv, 6 * MM), ALU));
    g.add(caja(largo - 8 * MM, 10 * MM, 2 * MM, 0xa9b1bb, P(0, s * (ancho / 2 - 6 * MM), 1 * MM), ALU));
    for (const sx of [-1, 1]) {
      tornillo(g, P(sx * 9 * MM, s * (ancho / 2 - 6 * MM), 2 * MM), 'z', 3, 1);
      tornillo(g, P(sx * 9 * MM, yv - s * 1 * MM, 8 * MM), 'y', 4, -s);
    }
  }
  return terminar(g, { datos: datos(opciones) });
}

// ==================================================================================
// Compuerta de desvio (E4): aleta impresa de 18 × 16 × 2 mm que cuelga de una bisagra en el
// centro de la salida del embudo (desviador en "Y": la moneda cae a un lado o al otro), un
// pasador Ø3 hacia -x hasta la oreja del embudo y, hacia +x, un brazo con el cubo que se
// atornilla al cuerno de disco del SG90 (el eje del servo ES el eje de la bisagra).
// Origen: sobre el eje de la bisagra. La aleta cuelga hacia -z; gira con rotation.x (Three),
// que es lo que ya anima moverDesvio. `alCuerno`: distancia en x hasta la cara del cuerno.
// ==================================================================================
export function crearCompuertaDesvio(opciones = {}) {
  const { ancho = 18 * MM, alto = 16 * MM, espesor = 2 * MM, alCuerno = 17 * MM } = opciones;
  const g = new THREE.Group();
  g.name = 'compuerta_desvio';
  const rojo = mat(0xd9261a, PLASTICO);
  g.add(caja(ancho, espesor, alto, rojo, P(0, 0, -alto / 2 - 1 * MM)));
  // Canto redondeado abajo (la moneda no se engancha).
  g.add(cil(espesor / 2, ancho, rojo, P(0, 0, -alto - 1 * MM), 'x', {}, 12));
  // Barril de la bisagra, pasador y brazo al cuerno.
  g.add(cil(2.5 * MM, ancho, rojo, P(0, 0, 0), 'x', {}, 20));
  g.add(cil(1.5 * MM, ancho / 2 + 6 * MM, 0xd0d3d8, P(-ancho / 2 - 3 * MM + 3 * MM, 0, 0), 'x', ACERO, 12));
  const largoBrazo = alCuerno - ancho / 2 - 2 * MM;
  g.add(cil(2.5 * MM, largoBrazo, rojo, P(ancho / 2 + largoBrazo / 2, 0, 0), 'x', {}, 16));
  g.add(cil(7 * MM, 2 * MM, rojo, P(alCuerno - 1 * MM, 0, 0), 'x', {}, 28));
  for (const [dy, dz] of [[4.5, 0], [-4.5, 0], [0, 4.5], [0, -4.5]]) {
    g.add(cil(0.9 * MM, 0.4 * MM, 0x2a2d31, P(alCuerno - 2.2 * MM, dy * MM, dz * MM), 'x', {}, 8));
  }
  return terminar(g, { datos: datos(opciones) });
}

// Oreja impresa que cuelga del embudo y toma el pasador de la bisagra. Origen: el eje del
// pasador; la oreja sube `alto` hasta el embudo. Plano de la oreja: y-z (pasador en x).
export function crearOrejaBisagra(opciones = {}) {
  const { alto = 8 * MM, espesor = 3 * MM, ancho = 7 * MM } = opciones;
  const g = new THREE.Group();
  g.name = 'oreja_bisagra';
  const m = mat(IMPRESO, PLASTICO);
  g.add(caja(espesor, ancho, alto, m, P(0, 0, alto / 2)));
  g.add(cil(ancho / 2, espesor, m, P(0, 0, 0), 'x', {}, 20));
  return terminar(g, { datos: datos(opciones) });
}

// ==================================================================================
// Brida impresa para un servo (SG90 por defecto): placa de 3 mm con la ventana del cuerpo y los
// 2 tornillos M2 de las pestañas. Mismo marco que crearServo de electronica.js: origen en el
// eje del servo, en el plano de la cara de abajo de las pestañas; la placa va de z = -3 a 0 mm,
// el cuerpo cuelga hacia -z y se extiende hacia -x.
// Anclas: ancla_brida_menos_x / ancla_brida_mas_x (centro de cada punta, cara de abajo).
// ==================================================================================
const SERVO_MEDIDAS = { SG90: { L: 22.5, W: 11.8, lPest: 32.2, agujeros: 27.5, dEje: 5.9 },
  MG996R: { L: 40.7, W: 19.7, lPest: 54.0, agujeros: 49.5, dEje: 9.85 } };
export function crearBridaServo(opciones = {}) {
  const { modelo = 'SG90' } = opciones;
  const d = SERVO_MEDIDAS[modelo];
  const g = new THREE.Group();
  g.name = 'brida_servo';
  const xc = -(d.L / 2 - d.dEje) * MM;
  const L = (d.lPest + 8) * MM, W = (d.W + 8) * MM;
  const forma = rectRedondeado(L, W, 2 * MM, xc, 0);
  forma.holes.push(rectAgujero((d.L + 0.6) * MM, (d.W + 0.6) * MM, xc, 0));
  const pl = losa(forma, 3 * MM, IMPRESO, PLASTICO);
  pl.position.y = -3 * MM;
  g.add(pl);
  for (const s of [-1, 1]) tornillo(g, P(xc + s * d.agujeros / 2 * MM, 0, 2.5 * MM), 'z', 2, 1);
  g.add(ancla('ancla_brida_menos_x', P(xc - L / 2, 0, -3 * MM)), ancla('ancla_brida_mas_x', P(xc + L / 2, 0, -3 * MM)));
  return terminar(g, { datos: datos(opciones) });
}

// ==================================================================================
// Bandeja de rechazo (impresa, PETG rojo oscuro): `largo` × `ancho` × `alto`, pared de 2,5 mm,
// piso de 3 mm, labio redondeado arriba y rotulo "RECHAZO" en la cara +x. Todo lo que no es una
// moneda aceptada cae aqui (filtro total, grupo 2026-09-25).
// Origen: centro del apoyo en el PISO.
// ==================================================================================
export function crearBandejaRechazo(opciones = {}) {
  const { largo = 90 * MM, ancho = 90 * MM, alto = 35 * MM, pared = 2.5 * MM } = opciones;
  const g = new THREE.Group();
  g.name = 'bandeja_rechazo';
  const m = mat(0x6b2f2f, PLASTICO);
  const exterior = rectRedondeado(largo, ancho, 6 * MM);
  g.add(losa(exterior, 3 * MM, m));
  const aro = rectRedondeado(largo, ancho, 6 * MM);
  const interior = new THREE.Path();
  const r = 6 * MM - pared, l = largo - 2 * pared, a = ancho - 2 * pared;
  interior.moveTo(-l / 2 + r, -a / 2);
  interior.absarc(-l / 2 + r, -a / 2 + r, r, -Math.PI / 2, -Math.PI, true);
  interior.lineTo(-l / 2, a / 2 - r); interior.absarc(-l / 2 + r, a / 2 - r, r, Math.PI, Math.PI / 2, true);
  interior.lineTo(l / 2 - r, a / 2); interior.absarc(l / 2 - r, a / 2 - r, r, Math.PI / 2, 0, true);
  interior.lineTo(l / 2, -a / 2 + r); interior.absarc(l / 2 - r, -a / 2 + r, r, 0, -Math.PI / 2, true);
  aro.holes.push(interior);
  const paredes = losa(aro, alto - 3 * MM, m);
  paredes.position.y = 3 * MM;
  g.add(paredes);
  // Rotulo en la cara +x (vertical).
  const rot = planoDibujado(ancho * 0.8, 14 * MM, (ctx, X, Y, k) => {
    ctx.fillStyle = '#e8e2d8'; ctx.fillRect(X(-ancho * 0.4 / MM), Y(7), ancho * 0.8 / MM * k, 14 * k);
    ctx.fillStyle = '#b3261e'; ctx.font = `700 ${9 * k}px "Space Grotesk", sans-serif`;
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('RECHAZO', X(0), Y(0));
  }, { ppm: 20 });
  rot.rotation.set(0, Math.PI / 2, 0);
  rot.position.copy(P(largo / 2 + 0.3 * MM, 0, alto * 0.55));
  g.add(rot);
  return terminar(g, { datos: datos(opciones) });
}

// ==================================================================================
// ALMACEN TIPO REVOLVER
// ==================================================================================
// Placa FIJA (acrilico oscuro de 4 mm, Ø116): UN agujero (sobre el vaso de llenado) en
// `agujeroEn` = [x, y] relativo al centro, y el alojamiento impreso del rodamiento 608 del eje
// en el centro (arriba). `tuercas`: [[x, y], ...] de las varillas M5 que la cuelgan del portico.
// Origen: centro de la placa, a media altura (como el cilindro que reemplaza).
export function crearPlacaFijaAlmacen(opciones = {}) {
  const { radio = 58 * MM, espesor = 4 * MM, agujeroEn = [0.0165, -0.0286], rAgujero = 14.5 * MM, tuercas = [] } = opciones;
  const g = new THREE.Group();
  g.name = 'placa_fija';
  const forma = circuloForma(radio);
  forma.holes.push(agujero(rAgujero, agujeroEn[0], agujeroEn[1]), agujero(4.2 * MM));
  const pl = losa(forma, espesor, mat(0x3a4250, { transparent: true, opacity: 0.8, roughness: 0.25 }));
  pl.position.y = -espesor / 2;
  g.add(pl);
  // Chaflan claro alrededor del agujero (se ve donde esta).
  const bisel = new THREE.Mesh(new THREE.RingGeometry(rAgujero, rAgujero + 1.5 * MM, 40), mat(0xf2b134, { side: THREE.DoubleSide }));
  bisel.rotation.x = -Math.PI / 2;
  bisel.position.copy(P(agujeroEn[0], agujeroEn[1], espesor / 2 + 0.15 * MM));
  g.add(bisel);
  // Alojamiento del 608 (arriba, Ø28 × 6) con el rodamiento a la vista.
  g.add(cilindro(14 * MM, 6 * MM, IMPRESO, P(0, 0, espesor / 2 + 3 * MM), PLASTICO, 36));
  g.add(cilindro(11 * MM, 0.4 * MM, 0xc9ccd1, P(0, 0, espesor / 2 + 6.2 * MM), METAL, 32));
  g.add(cilindro(9.6 * MM, 0.5 * MM, 0x151618, P(0, 0, espesor / 2 + 6.25 * MM), {}, 32));
  for (const [x, y] of tuercas) {
    g.add(tuerca(8 * MM, 4 * MM, P(x, y, espesor / 2 + 2 * MM)));
    g.add(tuerca(8 * MM, 4 * MM, P(x, y, -espesor / 2 - 2 * MM)));
  }
  return terminar(g, { datos: datos(opciones) });
}

// Disco del carrusel (acrilico transparente de 3 mm, Ø104): 6 agujeros de radio `rHueco` (el
// visor usa el interior del tubo, Ø29: los tubos van pegados a tope por DEBAJO, no atraviesan el
// disco; a 33 mm entre ejes, agujeros Ø32 dejaban 1 mm de acrilico entre dos) en
// `tubos` = [[x, y], ...] relativos al centro, cubo impreso con prisionero sobre el eje
// Ø8 y, en `iman` = [x, y], el iman N35 de 6 × 3 mm pegado en un anillo (el Hall lo ve pasar).
// Origen: centro del disco, a media altura.
export function crearDiscoCarrusel(opciones = {}) {
  const { radio = 52 * MM, espesor = 3 * MM, tubos = [], rHueco = 16 * MM, iman = null } = opciones;
  const g = new THREE.Group();
  g.name = 'disco_carrusel';
  const forma = circuloForma(radio);
  for (const [x, y] of tubos) forma.holes.push(agujero(rHueco, x, y));
  forma.holes.push(agujero(4 * MM));
  const d = losa(forma, espesor, mat(0x9fb3c8, { transparent: true, opacity: 0.45, roughness: 0.15, metalness: 0.1, depthWrite: false }));
  d.position.y = -espesor / 2;
  d.castShadow = false;
  g.add(d);
  // Canto pulido (se ve el borde del acrilico).
  const canto = new THREE.Mesh(new THREE.TorusGeometry(radio, espesor / 2, 6, 64), mat(0xc8d8ea, { transparent: true, opacity: 0.6 }));
  canto.rotation.x = Math.PI / 2;
  g.add(canto);
  // Cubo con brida (4 M3) y prisionero.
  g.add(cilindro(12 * MM, 2.5 * MM, IMPRESO, P(0, 0, espesor / 2 + 1.25 * MM), PLASTICO, 32));
  g.add(cilindro(7 * MM, 8 * MM, IMPRESO, P(0, 0, espesor / 2 + 4 * MM), PLASTICO, 28));
  for (let i = 0; i < 4; i++) {
    const a = i * Math.PI / 2 + Math.PI / 4;
    tornillo(g, P(Math.cos(a) * 9.5 * MM, Math.sin(a) * 9.5 * MM, espesor / 2 + 2.5 * MM), 'z', 3, 1);
  }
  g.add(cil(1.3 * MM, 1 * MM, 0x151515, P(7 * MM, 0, espesor / 2 + 6 * MM), 'x', {}, 8));
  if (iman) {
    const [x, y] = iman;
    const anillo = cilindro(4.5 * MM, 2 * MM, IMPRESO, P(x, y, espesor / 2 + 1 * MM), PLASTICO, 24);
    const im = cilindro(3 * MM, 3 * MM, 0xd9dde2, P(x, y, espesor / 2 + 1.5 * MM), { metalness: 0.95, roughness: 0.18 }, 24);
    im.name = 'iman';
    const punto = new THREE.Mesh(new THREE.CircleGeometry(0.8 * MM, 16), mat(0xc62828));
    punto.rotation.x = -Math.PI / 2;
    punto.position.copy(P(x, y, espesor / 2 + 3.02 * MM));
    g.add(anillo, im, punto);
  }
  return terminar(g, { datos: datos(opciones) });
}

// Tubo de policarbonato (pared de 1,5 mm), pegado a tope bajo su agujero del disco, con una etiqueta
// curva con la denominacion mirando hacia `angulo` (radianes, en el plano x-y de la simulacion:
// hacia afuera del carrusel). Origen: centro de la boca de ABAJO (la que resbala sobre la placa
// fija). El tubo sube `alto` + 3 mm. `collar` (mm de ala, 0 = sin collar) en `zCollar`.
export function crearTuboMonedas(opciones = {}) {
  const { rInterior = 14.5 * MM, pared = 1.5 * MM, alto = 58 * MM, zCollar = 58 * MM, texto = '', angulo = 0,
    fondoEtiqueta = '#f2b134', tintaEtiqueta = '#1a1a1a', collar = 0 } = opciones;
  const g = new THREE.Group();
  g.name = 'tubo_monedas';
  const rExt = rInterior + pared;
  const perfilTubo = [new THREE.Vector2(rInterior, 0), new THREE.Vector2(rExt, 0), new THREE.Vector2(rExt, alto + 3 * MM),
    new THREE.Vector2(rInterior, alto + 3 * MM), new THREE.Vector2(rInterior, 0)];
  const tubo = new THREE.Mesh(new THREE.LatheGeometry(perfilTubo, 40),
    mat(0xdcecff, { transparent: true, opacity: 0.25, roughness: 0.08, metalness: 0.05, side: THREE.DoubleSide, depthWrite: false }));
  tubo.name = 'policarbonato';
  g.add(tubo);
  // Cantos del tubo (anillos finos): lo hacen legible aunque sea transparente.
  for (const z of [0.3 * MM, alto + 2.7 * MM]) {
    const a = new THREE.Mesh(new THREE.TorusGeometry(rExt - pared / 2, pared / 2, 6, 40), mat(0xe8f2ff, { transparent: true, opacity: 0.45 }));
    a.rotation.x = Math.PI / 2;
    a.position.y = z;
    g.add(a);
  }
  // Collar opcional (de fabrica no: con los tubos a 33 mm entre ejes y 32 mm de diametro
  // exterior, entre dos tubos queda 1 mm y no cabe; el tubo va pegado en el agujero del disco).
  if (collar) {
    const cl = new THREE.Mesh(new THREE.LatheGeometry([new THREE.Vector2(rExt, 0), new THREE.Vector2(rExt + collar, 0),
      new THREE.Vector2(rExt + collar, 2 * MM), new THREE.Vector2(rExt, 2 * MM), new THREE.Vector2(rExt, 0)], 40), mat(IMPRESO, PLASTICO));
    cl.position.y = zCollar;
    g.add(cl);
  }
  if (texto) {
    const c = document.createElement('canvas');
    c.width = 256; c.height = 96;
    const ctx = c.getContext('2d');
    ctx.fillStyle = fondoEtiqueta; ctx.fillRect(0, 0, 256, 96);
    ctx.fillStyle = tintaEtiqueta; ctx.font = '700 58px "Space Grotesk", sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(texto, 128, 52);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    const arco = 1.5;
    const et = new THREE.Mesh(new THREE.CylinderGeometry(rExt + 0.15 * MM, rExt + 0.15 * MM, 12 * MM, 20, 1, true,
      angulo + Math.PI / 2 - arco / 2, arco), mat(0xffffff, { map: tex, roughness: 0.6 }));
    et.position.y = alto * 0.62;
    et.name = 'etiqueta';
    g.add(et);
  }
  return terminar(g, { datos: datos(opciones), sombras: false });
}

// Obturador del agujero de la placa fija: aleta impresa Ø34 × 2 (con un anillo de goma que sella
// contra la placa) y brazo hasta el nudillo de la bisagra; un pasador de acero Ø3 sale por el
// eje de la bisagra hasta el cubo del cuerno del SG90 (coaxial: el servo gira la bisagra).
// Marco local EN COORDENADAS DE THREE (el grupo del visor ya esta orientado con lookAt): origen
// en el eje de la bisagra, +X de Three = eje de la bisagra, +Z = hacia afuera del carrusel; la
// aleta queda centrada en z = -distancia. Gira con rotation.x. `lado` (+1/-1): hacia que punta
// del eje (+X o -X) sale el pasador al servo; `alCuerno`: distancia a la cara del cuerno.
// Nodo: aleta (la malla del disco).
export function crearObturadorAlmacen(opciones = {}) {
  const { radio = 17 * MM, distancia = 20 * MM, alCuerno = 22 * MM, lado = 1 } = opciones;
  const g = new THREE.Group();
  g.name = 'obturador';
  const m = mat(0x9c2a22, PLASTICO);
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  const aleta = cilindro(radio, 2 * MM, m, V(0, 0, -distancia), {}, 36);
  aleta.name = 'aleta';
  g.add(aleta);
  // Anillo de goma arriba: sella contra la placa.
  const sello = new THREE.Mesh(new THREE.TorusGeometry(radio - 2.5 * MM, 0.6 * MM, 6, 36), mat(0x111111, { roughness: 1 }));
  sello.rotation.x = Math.PI / 2;
  sello.position.set(0, 1 * MM, -distancia);
  g.add(sello);
  const largoBrazo = distancia - radio + 2 * MM;
  const brazo = new THREE.Mesh(new THREE.BoxGeometry(10 * MM, 2 * MM, largoBrazo), m);
  brazo.position.set(0, 0, -largoBrazo / 2);
  g.add(brazo);
  const nudillo = cilindro(3 * MM, 10 * MM, m, V(0, 0, 0), {}, 20);
  nudillo.rotation.z = Math.PI / 2;
  g.add(nudillo);
  // Pasador: desde 4 mm del otro lado del nudillo hasta el cubo del cuerno (entra 3 mm).
  const desde = -lado * 4 * MM, hasta = lado * (alCuerno + 3 * MM);
  const pasador = cilindro(1.5 * MM, Math.abs(hasta - desde), 0xd0d3d8, V((desde + hasta) / 2, 0, 0), ACERO, 12);
  pasador.rotation.z = Math.PI / 2;
  g.add(pasador);
  // Collarin con prisionero junto al cuerno (el pasador no se sale).
  const collarin = cilindro(3 * MM, 3 * MM, 0xb8bec6, V(lado * (alCuerno - 2.5 * MM), 0, 0), METAL, 20);
  collarin.rotation.z = Math.PI / 2;
  g.add(collarin);
  return terminar(g, { datos: datos(opciones) });
}

// Placa impresa del 28BYJ-48 (5 mm): el motor va ENCIMA con el eje hacia abajo; como el eje del
// 28BYJ-48 esta descentrado 8 mm, el cuerpo queda corrido 8 mm hacia -x y el EJE del motor
// coincide con el del carrusel. Agujero Ø14 por donde baja el acople rigido, 2 M4 de las
// pestañas (a ±17,5 mm en y) y 2 varillas roscadas M5 que la cuelgan del portico
// (`varillas` = [[x, y], ...] relativos al eje).
// Origen: eje del carrusel en la cara de ARRIBA de la placa.
export function crearSoporteMotorCarrusel(opciones = {}) {
  const { varillas = [[6 * MM, 22 * MM], [6 * MM, -22 * MM]], espesor = 5 * MM } = opciones;
  const g = new THREE.Group();
  g.name = 'soporte_motor_carrusel';
  const forma = rectRedondeado(42 * MM, 56 * MM, 5 * MM, -6 * MM, 0);
  forma.holes.push(agujero(7 * MM));
  const pl = losa(forma, espesor, IMPRESO, PLASTICO);
  pl.position.y = -espesor;
  g.add(pl);
  for (const s of [-1, 1]) tornillo(g, P(-8 * MM, s * 17.5 * MM, 0.8 * MM), 'z', 4, 1);
  for (const [x, y] of varillas) {
    g.add(tuerca(8 * MM, 4 * MM, P(x, y, 2 * MM)));
    g.add(tuerca(8 * MM, 4 * MM, P(x, y, -espesor - 2 * MM)));
  }
  return terminar(g, { datos: datos(opciones) });
}

// ==================================================================================
// Poste de la camara cenital (E3): perfil 2020 vertical atornillado al costado del riel +y
// con una escuadra, brazo 2020 horizontal hasta encima de la casilla y abrazadera impresa
// donde se atornilla la webcam (rosca de 1/4" en su base). Pensado para que lo integre quien
// dibuja la camara (construirSensores): la camara queda con su cara de arriba en la abrazadera.
// Origen: punto de la cara de ARRIBA de la camara (centro), en el eje del brazo.
// `alto`: del fondo del riel (donde empieza el poste) a la cara de arriba de la camara.
// `brazo`: del centro de la camara al eje del poste, hacia +y.
// ==================================================================================
export function crearPosteCamaraCenital(opciones = {}) {
  const { alto = 0.183, brazo = 0.0605 } = opciones;
  const g = new THREE.Group();
  g.name = 'poste_camara';
  const alu = mat(COLOR.aluminio, ALU);
  // Abrazadera: bloque impreso 30 × 24 × 6 con el tornillo de 1/4".
  g.add(caja(30 * MM, 24 * MM, 6 * MM, IMPRESO, P(0, 0, 3 * MM), PLASTICO));
  g.add(cil(3.2 * MM, 3 * MM, 0x2a2d31, P(0, 0, 7.5 * MM), 'z', ACERO, 16));
  // Brazo 2020 (a lo ancho, y) encima de la abrazadera, hasta el poste.
  g.add(caja(20 * MM, brazo + 10 * MM, 20 * MM, alu, P(0, (brazo + 10 * MM) / 2 - 10 * MM, 16 * MM)));
  // Poste 2020 vertical.
  g.add(caja(20 * MM, 20 * MM, alto + 26 * MM, alu, P(0, brazo, 26 * MM - (alto + 26 * MM) / 2)));
  g.add(ancla('ancla_pie_poste', P(0, brazo, -alto)));
  return terminar(g, { datos: datos(opciones) });
}
