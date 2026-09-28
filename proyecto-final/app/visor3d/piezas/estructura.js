// Estructura de la planta: perfil de aluminio 2020 (con su seccion ranurada real), escuadras,
// tornillos para ranura en T, pies niveladores, mesas de perfil y las piezas de la canaleta de
// entrega (rieles de varilla con PTFE, cabezales impresos, soportes).
// Convencion: ver README.md de esta carpeta. Marco de la simulacion (x largo, y ancho, z arriba),
// metros; las medidas de ficha tecnica van en mm y se pasan con MM.
//
// Contenido (agregar funciones nuevas AL FINAL, cada una con su bloque de comentarios):
//   geometriaPerfil2020()              BufferGeometry compartida de 1 m (se escala al largo)
//   mallaPerfil2020(largo, orientacion, material)   UNA malla de perfil (reemplazo liviano de una caja)
//   crearPerfil2020(largo, orientacion, opciones)    Group con el perfil, tapas y anclas en las puntas
//   perfil2020Entre(a, b, opciones)    perfil entre dos puntos de Three alineados con un eje
//   crearTornilloT(opciones)           tornillo M5 de cabeza redonda (ISO 7380) para tuerca en T
//   crearEscuadra2020(opciones)        escuadra de fundicion 20×20×20 con sus 2 tornillos
//   crearPieNivelador(opciones)        pie nivelador M6 con base de goma
//   crearMesaPerfil(opciones)          mesa de 4 patas de 2020 con travesanos, escuadras y pies
//   crearPortico2020(opciones)         portico de 2 columnas y una viga, con escuadras y pies
//   crearRielCanaleta(puntos, opciones)            varilla de acero con su cinta de PTFE (curva del embudo)
//   crearCabezalRiel(opciones)         cabezal impreso que toma el riel en la punta de un poste
//   crearSoporteCanaleta(opciones)     poste 2020 + pie + cabezal, listo para poner bajo un riel
//
// De donde salen las medidas:
//   - Perfil 2020 (ranura "tipo B", la del V-Slot/Misumi HFS5-2020 que venden en Colombia):
//     20 × 20 mm, boca de la ranura 6,2 mm, labio 1,8 mm, camara interior 11 mm, fondo de la
//     ranura a 5,7 mm del borde, agujero central Ø4,2 mm (se rosca M5). Precio en
//     config/precios.yaml (`estructura`: 3 m de V-Slot 2020).
//   - Escuadra 2020 de fundicion (la de los kits de impresora 3D): 20 × 20 × 20 mm, pared 3 mm,
//     dos nervios laterales de 2 mm, agujero de 5,5 mm a 10 mm de la esquina en cada ala;
//     tornillo M5 × 8 ISO 7380 (cabeza Ø9,5 × 2,75 mm) + tuerca en T. `tornilleria` en precios.
//   - Pie nivelador: base Ø26 mm de acero con goma de 2 mm, esparrago M6 al agujero central del
//     perfil (rosca pasada a M6) y contratuerca de 10 mm; 12 mm de alto total (regulable ±4 mm).
//   - Canaleta: config/parametros.yaml, bloque `canaleta` (varilla Ø4 mm forrada con cinta de
//     PTFE de 0,13 mm, rieles a 69 mm, entrada en embudo a 73 mm en 40 mm, 15°) y
//     `zonas_carro.medio_ancho_canaleta_mm` (75 mm: el soporte va 28 mm afuera de cada riel).

import * as THREE from 'three';
import { MM, COLOR, METAL, P, mat, caja, cilindro, ancla, terminar } from './base.js';

// Presets de material de la estructura (se pasan a `mat`, que crea uno nuevo cada vez).
const ALU = { metalness: 0.75, roughness: 0.38 };          // aluminio anodizado natural
const IMPRESO = { roughness: 0.75, metalness: 0.0 };        // PLA
const LADO_2020 = 20 * MM;

// ---------------------------------------------------------------------------
// Perfil 2020
// ---------------------------------------------------------------------------
//
// Seccion en mm, centrada, recorrida en sentido antihorario. Se describe UN lado (el de +y de
// la seccion, de la esquina derecha a la izquierda, con su ranura en T) y se gira 90° cuatro
// veces. Esquinas con chaflan de 0,6 mm como el perfil extruido real.
function contornoSeccion2020() {
  const lado = [
    [10, 9.4], [9.4, 10],                    // chaflan de la esquina
    [3.1, 10], [3.1, 8.2],                   // boca de la ranura (6,2 mm) y labio (1,8 mm)
    [5.5, 8.2], [5.5, 6.4],                  // camara interior bajo el labio (11 mm de ancho)
    [2.9, 4.3], [-2.9, 4.3],                 // paredes en V hasta el fondo de la ranura
    [-5.5, 6.4], [-5.5, 8.2], [-3.1, 8.2], [-3.1, 10],
  ];
  const pts = [];
  for (let k = 0; k < 4; k++) {
    for (const [x, y] of lado) {
      let px = x, py = y;
      for (let i = 0; i < k; i++) [px, py] = [-py, px];
      pts.push(new THREE.Vector2(px, py));
    }
  }
  return pts;
}

let _geoPerfil = null;
// Geometria de 1 m de perfil 2020 a lo largo del eje Z local de Three, centrada (z de -0,5 a
// 0,5). UNA sola para todos los perfiles: cada malla la estira con `scale.z = largo` (escalar a
// lo largo de la extrusion no deforma la seccion). No se debe hacer `dispose()` de ella.
export function geometriaPerfil2020() {
  if (_geoPerfil) return _geoPerfil;
  const forma = new THREE.Shape(contornoSeccion2020());
  const agujero = new THREE.Path();
  agujero.absarc(0, 0, 2.1, 0, Math.PI * 2, true);           // Ø4,2 mm central
  forma.holes.push(agujero);
  const g = new THREE.ExtrudeGeometry(forma, { depth: 1, bevelEnabled: false, curveSegments: 12 });
  g.scale(MM, MM, 1);
  g.translate(0, 0, -0.5);
  g.computeBoundingSphere();
  _geoPerfil = g;
  return g;
}

// Giro de la malla para que el eje del perfil quede en `orientacion` ('x', 'y' o 'z' de la
// SIMULACION). La geometria tiene el largo en Z de Three (= -y de la simulacion).
function orientarPerfil(m, orientacion) {
  if (orientacion === 'z') m.rotation.x = -Math.PI / 2;
  else if (orientacion === 'x') m.rotation.y = Math.PI / 2;
  else if (orientacion !== 'y') throw new Error(`perfil 2020: orientacion "${orientacion}" (x, y o z)`);
}

// UNA malla de perfil 2020 de `largo` metros, centrada en su origen, con el eje en
// `orientacion` ('x' | 'y' | 'z' de la simulacion). Es la version liviana (sin tapas ni anclas)
// para reemplazar una caja: `perfil()` de visor.js la usa. `material`: uno ya hecho (el visor
// pasa su MAT_ALU) o nada (crea uno nuevo, para que el resaltado no encienda a los vecinos).
export function mallaPerfil2020(largo, orientacion = 'x', material = null) {
  const m = new THREE.Mesh(geometriaPerfil2020(), material || mat(COLOR.aluminio, ALU));
  orientarPerfil(m, orientacion);
  m.scale.z = Math.max(largo, 0.001);
  m.castShadow = true;
  m.receiveShadow = true;
  m.name = 'perfil_2020';
  return m;
}

// Perfil 2020 de `largo` metros con el eje en `orientacion` ('x' | 'y' | 'z' de la simulacion).
//
// Origen: el CENTRO del perfil (mitad del largo, centro de la seccion). Se pone con
// `position.copy(punto medio)`; el perfil va de -largo/2 a +largo/2 sobre su eje.
// opciones:
//   tapas: false        tapas de plastico negro de 1,5 mm en las dos puntas (suman 3 mm al largo)
//   material            material ya hecho (si no, uno nuevo de aluminio)
//   idComponente, sensorId: van a userData de todas las mallas
// Nodos: `perfil_2020` (la malla). Anclas: `ancla_extremo_a` (punta de -eje),
// `ancla_extremo_b` (punta de +eje), `ancla_centro`.
export function crearPerfil2020(largo, orientacion = 'x', opciones = {}) {
  const { tapas = false, material = null, idComponente, sensorId } = opciones;
  const g = new THREE.Group();
  g.name = 'perfil2020';
  g.add(mallaPerfil2020(largo, orientacion, material));
  const eje = { x: P(1, 0, 0), y: P(0, 1, 0), z: P(0, 0, 1) }[orientacion];
  if (tapas) {
    for (const s of [-1, 1]) {
      const t = new THREE.Mesh(new THREE.BoxGeometry(LADO_2020, LADO_2020, 1.5 * MM), mat(0x151515, { roughness: 0.8 }));
      orientarPerfil(t, orientacion);
      t.position.copy(eje).multiplyScalar(s * (largo / 2 + 0.75 * MM));
      g.add(t);
    }
  }
  g.add(ancla('ancla_extremo_a', eje.clone().multiplyScalar(-largo / 2)),
    ancla('ancla_extremo_b', eje.clone().multiplyScalar(largo / 2)),
    ancla('ancla_centro', new THREE.Vector3()));
  return terminar(g, { datos: datos(idComponente, sensorId) });
}

// Perfil 2020 entre dos puntos de Three (`a`, `b`, hechos con P) alineados con un eje de la
// simulacion. Devuelve el Group de crearPerfil2020 ya puesto en su lugar. Si los puntos no
// estan alineados con un eje, lanza un error (un 2020 inclinado no se usa en esta planta).
export function perfil2020Entre(a, b, opciones = {}) {
  const d = new THREE.Vector3().subVectors(b, a);
  const orientacion = ejeDominante(d);
  const g = crearPerfil2020(d.length(), orientacion, opciones);
  g.position.copy(a).addScaledVector(d, 0.5);
  return g;
}

// 'x' | 'y' | 'z' (de la simulacion) si `d` (vector de Three) va a lo largo de un eje; null si no.
export function ejeDominante(d, tolerancia = 1e-6) {
  const ax = Math.abs(d.x), ay = Math.abs(d.y), az = Math.abs(d.z);
  const n = (ax > tolerancia) + (ay > tolerancia) + (az > tolerancia);
  if (n !== 1) return null;
  return ax > tolerancia ? 'x' : ay > tolerancia ? 'z' : 'y';
}

function datos(idComponente, sensorId) {
  const d = {};
  if (idComponente) d.idComponente = idComponente;
  if (sensorId) d.sensorId = sensorId;
  return d;
}

// ---------------------------------------------------------------------------
// Tornilleria
// ---------------------------------------------------------------------------
//
// Tornillo M5 de cabeza redonda con hexagono interior (ISO 7380): cabeza Ø9,5 × 2,75 mm,
// hexagono de 3 mm. Del otro lado de la pieza va una tuerca en T (o tuerca "martillo") DENTRO de
// la ranura del perfil: no se ve, por eso no se dibuja.
// Origen: centro de la cara de APOYO de la cabeza; la cabeza crece hacia +z de la simulacion.
export function crearTornilloT({ largoVisible = 0 } = {}) {
  const g = new THREE.Group();
  g.name = 'tornillo_M5';
  const cabeza = new THREE.Mesh(new THREE.SphereGeometry(4.75 * MM, 20, 8, 0, Math.PI * 2, 0, Math.PI / 2),
    mat(0x2a2d31, METAL));
  cabeza.scale.y = 2.75 / 4.75;                                   // domo de 2,75 mm de alto
  g.add(cabeza);
  const hexagono = cilindro(1.6 * MM, 0.4 * MM, mat(0x050505), P(0, 0, 2.6 * MM), {}, 6);
  g.add(hexagono);
  if (largoVisible > 0) g.add(cilindro(2.5 * MM, largoVisible, mat(0x2a2d31, METAL), P(0, 0, -largoVisible / 2), {}, 12));
  return g;
}

// ---------------------------------------------------------------------------
// Escuadra 2020
// ---------------------------------------------------------------------------
//
// Escuadra de fundicion de aluminio para perfil 2020: dos alas de 20 × 20 × 3 mm a 90°, dos
// nervios triangulares de 2 mm a los costados y un tornillo M5 (+ tuerca en T) por ala, a 11 mm
// de la esquina interior.
//
// Origen: la ESQUINA INTERIOR, en la mitad del ancho: el punto donde se juntan las dos caras
// de perfil que une. Sin girar, el ala A apoya sobre una cara horizontal y sale hacia +x; el ala
// B apoya contra una cara vertical y sube hacia +z; el ancho (20 mm) va en y.
// opciones:
//   ejeA, ejeB: hacia donde salen las alas, como vectores de Three (P(...)) o [x, y, z] de la
//     simulacion. Deben ser perpendiculares. Por defecto P(1,0,0) y P(0,0,1).
//   tornillos: true     color: aluminio     idComponente, sensorId
// Anclas: ancla_tornillo_a, ancla_tornillo_b (centro de la cabeza de cada tornillo).
export function crearEscuadra2020(opciones = {}) {
  const { tornillos = true, color = COLOR.aluminio, idComponente, sensorId } = opciones;
  const g = new THREE.Group();
  g.name = 'escuadra_2020';
  const m = mat(color, { metalness: 0.55, roughness: 0.5 });
  const L = 20 * MM, T = 3 * MM, A = 20 * MM, N = 2 * MM;
  g.add(caja(L, A, T, m, P(L / 2, 0, T / 2)));                   // ala A (horizontal)
  g.add(caja(T, A, L, m, P(T / 2, 0, L / 2)));                   // ala B (vertical)
  // Nervios: triangulo rectangulo de catetos 20 mm en el plano x-z, extruido 2 mm en y.
  const tri = new THREE.Shape([new THREE.Vector2(0, 0), new THREE.Vector2(L, 0), new THREE.Vector2(0, L)]);
  const geoTri = new THREE.ExtrudeGeometry(tri, { depth: N, bevelEnabled: false });
  for (const s of [-1, 1]) {
    const nervio = new THREE.Mesh(geoTri, m);
    // Shape en X-Y de Three = x-z de la simulacion; la extrusion (Z de Three) es -y.
    nervio.position.copy(P(0, s * (A / 2 - N / 2) + N / 2, 0));
    g.add(nervio);
  }
  if (tornillos) {
    const a = crearTornilloT();
    a.position.copy(P(11 * MM, 0, T));
    const b = crearTornilloT();
    b.position.copy(P(T, 0, 11 * MM));
    b.rotation.z = -Math.PI / 2;                                  // la cabeza mira a +x
    g.add(a, b, ancla('ancla_tornillo_a', a.position.clone()), ancla('ancla_tornillo_b', b.position.clone()));
  }
  orientarDosEjes(g, opciones.ejeA, opciones.ejeB);
  return terminar(g, { datos: datos(idComponente, sensorId) });
}

const aThree = (v) => (Array.isArray(v) ? P(v[0], v[1], v[2]) : v.clone());
// Gira `obj` para que su +x de la simulacion (X de Three) vaya a `ejeA` y su +z de la
// simulacion (Y de Three) vaya a `ejeB`.
function orientarDosEjes(obj, ejeA, ejeB) {
  if (!ejeA && !ejeB) return;
  const a = aThree(ejeA || [1, 0, 0]).normalize();
  const b = aThree(ejeB || [0, 0, 1]).normalize();
  const c = new THREE.Vector3().crossVectors(a, b);
  obj.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(a, b, c));
}

// ---------------------------------------------------------------------------
// Pie nivelador
// ---------------------------------------------------------------------------
//
// Pie nivelador para la punta de una pata de 2020: base de acero Ø26 mm con goma de 2 mm,
// esparrago M6 enroscado al agujero central del perfil (se pasa el macho M6) y contratuerca de
// 10 mm entre caras. `alto` = del piso a la punta del perfil (12 mm; se regula ±4 mm).
// Origen: centro del apoyo en el PISO. Ancla `ancla_perfil`: donde empieza el perfil (arriba).
export function crearPieNivelador({ alto = 12 * MM, idComponente, sensorId } = {}) {
  const g = new THREE.Group();
  g.name = 'pie_nivelador';
  g.add(cilindro(13 * MM, 2 * MM, mat(0x111111, { roughness: 0.95 }), P(0, 0, 1 * MM), {}, 28));        // goma
  g.add(cilindro(12.5 * MM, 2.5 * MM, mat(0x9aa1aa, METAL), P(0, 0, 3.25 * MM), {}, 28));               // base
  const domo = new THREE.Mesh(new THREE.SphereGeometry(6 * MM, 16, 6, 0, Math.PI * 2, 0, Math.PI / 2), mat(0x9aa1aa, METAL));
  domo.scale.y = 0.4;
  domo.position.copy(P(0, 0, 4.5 * MM));
  g.add(domo);
  const zTuerca = alto - 4 * MM;
  g.add(cilindro(3 * MM, alto - 5 * MM, mat(0xb8bec6, METAL), P(0, 0, 5 * MM + (alto - 5 * MM) / 2), {}, 12));   // esparrago
  g.add(cilindro(5.77 * MM, 4 * MM, mat(0xb8bec6, METAL), P(0, 0, zTuerca + 2 * MM - 0.2 * MM), {}, 6));       // tuerca
  g.add(ancla('ancla_perfil', P(0, 0, alto)));
  return terminar(g, { datos: datos(idComponente, sensorId) });
}
export const ALTO_PIE = 12 * MM;

// ---------------------------------------------------------------------------
// Mesa de perfil 2020
// ---------------------------------------------------------------------------
//
// Mesa de 4 patas de perfil 2020 (como la de la cinta de vasos): patas sobre pies niveladores,
// travesanos a `zTravesano` en los dos sentidos (a distinta altura para que no se crucen: los de
// x 20 mm mas arriba), cada union con su escuadra por dentro. La bancada de la cinta se atornilla
// por arriba a la punta de las patas (M5 al agujero central), por eso no hay marco superior.
//
// Origen: centro de la mesa en el PISO. `largo` (x) y `ancho` (y) son entre EJES de patas;
// `alto` es del piso a la punta de las patas (donde apoya la bancada).
// opciones: tablero: false (tablero MDF de 9 mm encima; si se pone, las patas bajan 9 mm),
//   zTravesano: 0.05, idComponente, sensorId.
// Anclas: ancla_pata_<i> (punta de arriba de cada pata, i = 0..3), ancla_superficie (centro de lo
// alto de la mesa).
export function crearMesaPerfil(opciones = {}) {
  const { largo, ancho, alto, zTravesano = 0.05, tablero = false, idComponente, sensorId } = opciones;
  const g = new THREE.Group();
  g.name = 'mesa_2020';
  const alu = mat(COLOR.aluminio, ALU);
  const eTab = tablero ? 9 * MM : 0;
  const zTope = alto - eTab;
  const patas = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) patas.push([sx * largo / 2, sy * ancho / 2]);
  patas.forEach(([x, y], i) => {
    const pie = crearPieNivelador();
    pie.position.copy(P(x, y, 0));
    const pata = mallaPerfil2020(zTope - ALTO_PIE, 'z', alu);
    pata.position.copy(P(x, y, (ALTO_PIE + zTope) / 2));
    g.add(pie, pata, ancla(`ancla_pata_${i}`, P(x, y, zTope)));
  });
  // Travesanos entre caras de patas (no entran en ellas), con escuadra en cada punta.
  const h = LADO_2020 / 2;
  const zX = zTravesano + LADO_2020, zY = zTravesano;
  for (const sy of [-1, 1]) {
    const t = mallaPerfil2020(largo - LADO_2020, 'x', alu);
    t.position.copy(P(0, sy * ancho / 2, zX));
    g.add(t);
    for (const sx of [-1, 1]) {
      // Encima del travesano, contra la cara interior de la pata.
      const e = crearEscuadra2020({ ejeA: [-sx, 0, 0], ejeB: [0, 0, 1] });
      e.position.copy(P(sx * (largo / 2 - h), sy * ancho / 2, zX + h));
      g.add(e);
    }
  }
  for (const sx of [-1, 1]) {
    const t = mallaPerfil2020(ancho - LADO_2020, 'y', alu);
    t.position.copy(P(sx * largo / 2, 0, zY));
    g.add(t);
    for (const sy of [-1, 1]) {
      const e = crearEscuadra2020({ ejeA: [0, -sy, 0], ejeB: [0, 0, 1] });
      e.position.copy(P(sx * largo / 2, sy * (ancho / 2 - h), zY + h));
      g.add(e);
    }
  }
  if (tablero) {
    const t = caja(largo + 0.04, ancho + 0.04, eTab, mat(0xb58a5a, { roughness: 0.85 }), P(0, 0, alto - eTab / 2));
    t.name = 'tablero_mdf';
    g.add(t);
  }
  g.add(ancla('ancla_superficie', P(0, 0, alto)));
  return terminar(g, { datos: datos(idComponente, sensorId) });
}

// ---------------------------------------------------------------------------
// Portico 2020
// ---------------------------------------------------------------------------
//
// Portico de dos columnas de 2020 sobre pies niveladores y una viga ENTRE ellas (no encima):
// la cara de arriba de la viga queda a ras con la punta de las columnas, unida con dos escuadras
// por debajo. Es el portico trasero de la cinta de vasos (viga a 40 cm: por debajo pasa el canal
// de la descarga al carrusel); de el cuelgan almacen, tubo de tapas y prensa.
//
// Origen: el PISO bajo el centro de la viga. `largo`: entre ejes de columnas (en x);
// `zViga`: altura del EJE de la viga. Anclas: ancla_viga (centro de la viga), ancla_columna_a/b
// (punta de arriba de cada columna).
export function crearPortico2020({ largo, zViga = 0.40, idComponente, sensorId } = {}) {
  const g = new THREE.Group();
  g.name = 'portico_2020';
  const alu = mat(COLOR.aluminio, ALU);
  const h = LADO_2020 / 2;
  const zTop = zViga + h;
  for (const s of [-1, 1]) {
    const pie = crearPieNivelador();
    pie.position.copy(P(s * largo / 2, 0, 0));
    const col = mallaPerfil2020(zTop - ALTO_PIE, 'z', alu);
    col.position.copy(P(s * largo / 2, 0, (ALTO_PIE + zTop) / 2));
    const e = crearEscuadra2020({ ejeA: [0, 0, -1], ejeB: [-s, 0, 0] });   // bajo la viga, contra la columna
    e.position.copy(P(s * (largo / 2 - h), 0, zViga - h));
    g.add(pie, col, e, ancla(s < 0 ? 'ancla_columna_a' : 'ancla_columna_b', P(s * largo / 2, 0, zTop)));
  }
  const viga = mallaPerfil2020(largo - LADO_2020, 'x', alu);
  viga.position.copy(P(0, 0, zViga));
  viga.name = 'viga';
  g.add(viga, ancla('ancla_viga', P(0, 0, zViga)));
  return terminar(g, { datos: datos(idComponente, sensorId) });
}

// ---------------------------------------------------------------------------
// Canaleta de entrega
// ---------------------------------------------------------------------------
//
// Riel de la canaleta: varilla lisa de acero Ø4 mm (`diametro`) FORRADA con cinta de PTFE
// (blanca, 0,13 mm) donde apoya la pestana del vaso; en las puntas se ve el acero (la cinta
// arranca a `margenCinta` de cada punta). `puntos`: polilinea de puntos de Three (P), p. ej.
// [boca del embudo, fin del embudo, final]: la varilla se dobla en cada punto intermedio con un
// radio de `radioCurva` (una varilla real no hace quiebres en punta).
// Origen: el marco del visor (los puntos ya son absolutos); el Group queda en (0,0,0).
// Nodos: `varilla`, `ptfe`. Anclas: ancla_inicio, ancla_fin.
export function crearRielCanaleta(puntos, { diametro = 4 * MM, radioCurva = 15 * MM, margenCinta = 6 * MM,
  idComponente, sensorId } = {}) {
  const g = new THREE.Group();
  g.name = 'riel_canaleta';
  const camino = new THREE.CurvePath();
  let desde = puntos[0].clone();
  for (let i = 1; i < puntos.length - 1; i++) {
    const p = puntos[i];
    const r = Math.min(radioCurva, p.distanceTo(desde) / 2, p.distanceTo(puntos[i + 1]) / 2);
    const antes = p.clone().addScaledVector(new THREE.Vector3().subVectors(desde, p).normalize(), r);
    const despues = p.clone().addScaledVector(new THREE.Vector3().subVectors(puntos[i + 1], p).normalize(), r);
    camino.add(new THREE.LineCurve3(desde, antes));
    camino.add(new THREE.QuadraticBezierCurve3(antes, p.clone(), despues));
    desde = despues;
  }
  camino.add(new THREE.LineCurve3(desde, puntos[puntos.length - 1].clone()));
  const largo = camino.getLength();
  const n = Math.max(24, Math.round(largo / 0.004));
  const varilla = new THREE.Mesh(new THREE.TubeGeometry(camino, n, diametro / 2, 12, false), mat(COLOR.acero, METAL));
  varilla.name = 'varilla';
  g.add(varilla);
  // Cinta de PTFE: el mismo camino, 0,13 mm mas gruesa, sin las puntas.
  const u0 = margenCinta / largo, u1 = 1 - margenCinta / largo;
  const pts = [];
  for (let i = 0; i <= n; i++) pts.push(camino.getPointAt(u0 + (u1 - u0) * i / n));
  const cinta = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), n, diametro / 2 + 0.13 * MM, 12, false),
    mat(0xf1f1ee, { roughness: 0.35 }));
  cinta.name = 'ptfe';
  g.add(cinta);
  // Puntas de la varilla (cortadas y con el canto matado): tapitas de acero.
  for (const [u, nombre] of [[0, 'ancla_inicio'], [1, 'ancla_fin']]) {
    const p = camino.getPointAt(u);
    const tapa = new THREE.Mesh(new THREE.SphereGeometry(diametro / 2, 12, 8), mat(COLOR.acero, METAL));
    tapa.scale.setScalar(0.999);
    tapa.position.copy(p);
    g.add(tapa, ancla(nombre, p));
  }
  return terminar(g, { datos: datos(idComponente, sensorId) });
}

// Cabezal impreso (PLA) que toma un riel de la canaleta en la punta de un poste 2020: un bloque
// de 20 mm de fondo con la cara de arriba inclinada a la pendiente de la canaleta; la varilla
// queda metida a media altura en una ranura de esa cara y la sujeta un prisionero M3 desde
// AFUERA (nada sobresale por encima de la varilla: ahi pasa la pestana del vaso). Se atornilla
// con un M5 a la punta del poste (agujero central del perfil).
//
// Origen: centro de la cara de ABAJO (= punta del poste). El riel queda en x = -`dRiel`
// (hacia el eje de la canaleta si `lado` = +1; con `lado` = -1 todo se espeja en x), a
// `alto` sobre el origen en y = 0; la cara de arriba sube hacia +y con `inclinacion` (grados).
// El bloque va de 1,5 mm por dentro del riel (el cuerpo del vaso pasa a 3,5 mm del riel) hasta
// la cara de afuera del poste. Ancla `ancla_riel`: el eje de la varilla sobre el cabezal.
export function crearCabezalRiel({ dRiel = 28 * MM, alto = 12 * MM, fondo = 20 * MM, inclinacion = 15, lado = 1,
  diametroRiel = 4 * MM, color = COLOR.impreso, idComponente, sensorId } = {}) {
  const g = new THREE.Group();
  g.name = 'cabezal_riel';
  const t = Math.tan(THREE.MathUtils.degToRad(inclinacion));
  // Seccion en el plano (y, z) de la simulacion -> Shape (X = y, Y = z), extruida a lo largo de x.
  const f = fondo / 2;
  const forma = new THREE.Shape([new THREE.Vector2(-f, 0), new THREE.Vector2(f, 0),
    new THREE.Vector2(f, alto + f * t), new THREE.Vector2(-f, alto - f * t)]);
  const x0 = -(dRiel + diametroRiel / 2 - 0.5 * MM), x1 = LADO_2020 / 2;
  const geo = new THREE.ExtrudeGeometry(forma, { depth: x1 - x0, bevelEnabled: false });
  geo.translate(0, 0, x0);
  const bloque = new THREE.Mesh(geo, mat(color, IMPRESO));
  // Shape X -> -Z de Three (= +y de la simulacion), extrusion Z -> +X de Three (= x).
  bloque.rotation.y = Math.PI / 2;
  const cuerpo = new THREE.Group();
  cuerpo.add(bloque);
  // Prisionero M3 del lado de afuera (a la altura de la varilla) y cabeza del M5 de abajo.
  const pris = cilindro(2.75 * MM, 1.5 * MM, mat(0x2a2d31, METAL), null, {}, 6);
  pris.rotation.z = Math.PI / 2;
  pris.position.copy(P(x1 + 0.75 * MM, 0, alto - 3 * MM));
  cuerpo.add(pris);
  if (lado < 0) cuerpo.scale.x = -1;          // espejo: el riel queda en +x
  g.add(cuerpo, ancla('ancla_riel', P(-lado * dRiel, 0, alto)));
  return terminar(g, { datos: datos(idComponente, sensorId) });
}

// Soporte de un riel de la canaleta: pie nivelador, poste de 2020 y cabezal impreso.
// Origen: el PISO bajo el eje del poste. El riel queda en (-lado·dRiel, 0, alturaRiel).
// opciones: alturaRiel (del piso al eje de la varilla), dRiel (28 mm), lado (+1: riel hacia -x),
//   inclinacion (15), idComponente, sensorId.
// Anclas: ancla_riel, ancla_poste_arriba (punta del poste), ancla_poste (eje del poste a
// `zUnion` del piso, para travesanos: 3 cm).
export function crearSoporteCanaleta({ alturaRiel, dRiel = 28 * MM, lado = 1, inclinacion = 15, alto = 12 * MM,
  idComponente, sensorId } = {}) {
  const g = new THREE.Group();
  g.name = 'soporte_canaleta';
  const pie = crearPieNivelador();
  const zPoste = alturaRiel - alto;
  const poste = mallaPerfil2020(zPoste - ALTO_PIE, 'z');
  poste.position.copy(P(0, 0, (ALTO_PIE + zPoste) / 2));
  const cab = crearCabezalRiel({ dRiel, alto, lado, inclinacion });
  cab.position.copy(P(0, 0, zPoste));
  g.add(pie, poste, cab, ancla('ancla_riel', P(-lado * dRiel, 0, alturaRiel)),
    ancla('ancla_poste_arriba', P(0, 0, zPoste)));
  return terminar(g, { datos: datos(idComponente, sensorId) });
}
