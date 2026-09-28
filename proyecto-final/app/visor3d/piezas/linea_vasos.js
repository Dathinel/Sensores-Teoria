// Piezas de la CINTA DE VASOS (estacion de embalaje) para el visor 3D: vaso y tapa, tacos de
// las casillas, tubo de tapas con su escape de servo, prensa de leva excentrica, empujador de
// descarga, accionamiento de la cinta (NEMA17), panel de luz, poste de la camara de vasos y
// porta-sensor del VL53L0X del interior.
//
// Convencion: ver README.md de esta carpeta. Todo en METROS y en el marco de la simulacion
// (x a lo largo de la cinta, y a lo ancho, z arriba); las cotas de cada pieza se escriben en mm
// y se pasan con `Pm` (mm -> Three). Cada funcion dice su ORIGEN.
//
// De donde salen las medidas:
// - config/parametros.yaml (vasos): vaso de 62 mm x 90 mm (PROVISIONAL), pestana del reborde de
//   8 mm (boca de 78 mm), casillas de 80 mm, separador de 15 mm; prensa con leva de 6,5 mm de
//   excentricidad en un MG996R (carrera 13 mm); tapa que cae ~13 mm desde el tubo.
// - sim/geometria.py y visor.js: posiciones de estaciones, tubo, prensa, empujador y sensores.
// - Servos y NEMA17: piezas/electronica.js (fichas TowerPro SG90/MG996R, 17HS4401).
// - Lo que no esta en ninguna parte (espesores de pared, tapon de la tapa, largo de la biela,
//   guias...) son medidas SUPUESTAS de un montaje impreso razonable; cada una esta anotada.
import * as THREE from 'three';
import { MM, COLOR, METAL, PLASTICO, P, mat, caja, cilindro, ancla, terminar } from './base.js';
import { crearServo, crearNEMA17 } from './electronica.js';
import { crearWebcam } from './sensores.js';

const Pm = (x, y, z) => P(x * MM, y * MM, z * MM);
const IMPRESO = COLOR.impreso;                      // PETG gris oscuro impreso
const ALU = { metalness: 0.75, roughness: 0.35 };
const ACERO = 0xc4c8ce;

function datos(o) {
  return { ...(o.idComponente ? { idComponente: o.idComponente } : {}), ...(o.sensorId ? { sensorId: o.sensorId } : {}) };
}
// Caja sx x sy x sz mm centrada en (x, y, z) mm.
function cj(g, sx, sy, sz, color, x, y, z, extra, nombre) {
  const m = caja(sx * MM, sy * MM, sz * MM, color, Pm(x, y, z), extra);
  if (nombre) m.name = nombre;
  g.add(m);
  return m;
}
// Caja dada por sus limites en mm (x0..x1, y0..y1, z0..z1).
function cjL(g, x0, x1, y0, y1, z0, z1, color, extra, nombre) {
  return cj(g, x1 - x0, y1 - y0, z1 - z0, color, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, extra, nombre);
}
// Cilindro de radio r y alto h mm centrado en (x, y, z) mm; eje 'z' (vertical), 'y' o 'x'.
function ci(g, r, h, color, x, y, z, extra, seg = 24, eje = 'z', nombre) {
  const m = cilindro(r * MM, h * MM, color, Pm(x, y, z), extra, seg);
  if (eje === 'y') m.rotation.x = Math.PI / 2;
  else if (eje === 'x') m.rotation.z = Math.PI / 2;
  if (nombre) m.name = nombre;
  g.add(m);
  return m;
}
// Solido de revolucion alrededor del eje z: perfil [[r, z], ...] en mm.
function torno(g, perfil, material, seg = 48, nombre) {
  const geo = new THREE.LatheGeometry(perfil.map(([r, z]) => new THREE.Vector2(r * MM, z * MM)), seg);
  const m = new THREE.Mesh(geo, material);
  m.castShadow = true;
  if (nombre) m.name = nombre;
  g.add(m);
  return m;
}
// Prisma: contorno (x, y) mm extruido en z desde zBase `alto` mm.
function prisma(g, puntos, alto, color, zBase, extra, nombre) {
  const s = new THREE.Shape(puntos.map(([x, y]) => new THREE.Vector2(x * MM, y * MM)));
  const geo = new THREE.ExtrudeGeometry(s, { depth: alto * MM, bevelEnabled: false });
  geo.rotateX(-Math.PI / 2);
  const m = new THREE.Mesh(geo, color && color.isMaterial ? color : mat(color, extra));
  m.position.copy(Pm(0, 0, zBase));
  m.castShadow = true;
  if (nombre) m.name = nombre;
  g.add(m);
  return m;
}
// Resorte helicoidal: `vueltas` espiras de radio medio rMedio y alambre rAlambre (mm), de z = 0
// a z = largo. Se comprime con scale.y (Three y = z de la simulacion).
function resorte(rMedio, rAlambre, largo, vueltas, color = ACERO) {
  const n = Math.ceil(vueltas * 16);
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const t = i / n, a = t * vueltas * Math.PI * 2;
    pts.push(Pm(rMedio * Math.cos(a), rMedio * Math.sin(a), largo * t));
  }
  const geo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), n, rAlambre * MM, 6, false);
  const m = new THREE.Mesh(geo, mat(color, METAL));
  m.castShadow = true;
  return m;
}
// Placa (espesor en z) con una ventana rectangular: 4 cajas alrededor de la ventana.
function placaConVentana(g, [x0, x1, y0, y1], [vx0, vx1, vy0, vy1], z0, z1, color, extra) {
  return [cjL(g, x0, vx0, y0, y1, z0, z1, color, extra), cjL(g, vx1, x1, y0, y1, z0, z1, color, extra),
    cjL(g, vx0, vx1, y0, vy0, z0, z1, color, extra), cjL(g, vx0, vx1, vy1, y1, z0, z1, color, extra)];
}
function tornilloZ(g, x, y, z, r = 1.9) {                          // cabeza Allen vista desde arriba
  ci(g, r, 1.4, 0xb8bec6, x, y, z + 0.7, METAL, 12);
  ci(g, r * 0.45, 0.3, 0x1a1a1a, x, y, z + 1.45, {}, 6);
}

// ==================================================================
// Vaso personalizado (PROVISIONAL, config vasos: 62 x 90 mm, reborde 8 mm)
// ==================================================================
// Vaso OPACO conico de pared delgada (0,8 mm): boca exterior de Ø62, base de Ø53,3 (86 %,
// como un vaso de polipropileno), fondo levantado 2 mm sobre un anillo de apoyo, y la PESTANA
// del reborde de 8 mm (Ø78, 1,2 mm de espesor) con el labio enrollado: es lo que cuelga en los
// rieles de la canaleta y lo que la tapa usa de asiento. La cinta ArUco (20 mm, a 62 % de la
// altura) sigue la conicidad del vaso.
// Origen: centro de la BASE (donde apoya en la cinta); z arriba. Nodos (los usa visor.js):
// cuerpo, fondo, reborde, aro, aruco, tapa (oculta; su origen en el asiento = z altura),
// pila (grupo de las monedas), figura (el objeto del sabotaje "cambiar vaso"), fantasma.
// opciones: diametro, altura, reborde (m), mapaAruco (textura de la cinta), color.
export function crearVaso(o = {}) {
  const D = (o.diametro ?? 0.062) / MM, H = (o.altura ?? 0.09) / MM, B = (o.reborde ?? 0.008) / MM;
  const R1 = D / 2, R0 = R1 * 0.86, t = 0.8, rB = R1 + B, zF = 2.0;
  const r = (z) => R0 + (R1 - R0) * z / H;
  const g = new THREE.Group();
  g.name = 'vaso';
  const colorVaso = o.color ?? 0xeef1f4;
  const matVaso = () => mat(colorVaso, { roughness: 0.55, side: THREE.DoubleSide });
  torno(g, [[r(zF) - t, zF], [R1 - t, H - 1.2], [R1, H - 1.2], [R0 + 0.1, 0.8], [R0 - 0.6, 0], [R0 - 2.6, 0], [R0 - 3.2, 1.2]],
    matVaso(), 64, 'cuerpo');
  ci(g, r(zF) - t, zF - 1.2, colorVaso, 0, 0, (zF + 1.2) / 2, { roughness: 0.6 }, 48, 'z', 'fondo');
  // Pestana plana (el asiento de la tapa queda a ras, en z = H) y labio enrollado.
  torno(g, [[R1 - t, H - 1.2], [rB - 0.9, H - 1.2], [rB - 0.9, H], [R1 - t, H], [R1 - t, H - 1.2]],
    mat(colorVaso, { roughness: 0.5, side: THREE.DoubleSide }), 64, 'reborde');
  const aro = new THREE.Mesh(new THREE.TorusGeometry((rB - 0.9) * MM, 0.9 * MM, 8, 64), mat(colorVaso, { roughness: 0.45 }));
  aro.rotation.x = Math.PI / 2;
  aro.position.copy(Pm(0, 0, H - 0.9));
  aro.name = 'aro';
  g.add(aro);
  // Cinta ArUco (6 marcadores alrededor): sigue la conicidad, 0,35 mm por fuera de la pared.
  const zB = H * 0.62, hB = 20;
  const aruco = new THREE.Mesh(new THREE.CylinderGeometry((r(zB + hB / 2) + 0.35) * MM, (r(zB - hB / 2) + 0.35) * MM, hB * MM, 64, 1, true),
    o.mapaAruco ? new THREE.MeshBasicMaterial({ map: o.mapaAruco }) : mat(0x222222));
  aruco.position.copy(Pm(0, 0, zB));
  aruco.name = 'aruco';
  g.add(aruco);
  const pila = new THREE.Group();
  pila.name = 'pila';
  g.add(pila);
  // Figura del sabotaje "cambiar vaso": un bloque redondeado de 56 x 35 mm, mas bajo que la
  // franja de media altura (config: planta.figura_altura_mm).
  const figura = torno(g, [[0, 0], [26.5, 0], [28, 1.5], [28, 32], [25.5, 35], [0, 35]], mat(0x8a4fcf, { roughness: 0.5 }), 40, 'figura');
  figura.visible = false;
  const fantasma = new THREE.Mesh(new THREE.CylinderGeometry(R1 * MM, R0 * MM, H * MM, 16, 1, true),
    new THREE.MeshBasicMaterial({ color: COLOR.rojo, wireframe: true, transparent: true, opacity: 0.5 }));
  fantasma.position.copy(Pm(0, 0, H / 2));
  fantasma.name = 'fantasma';
  fantasma.visible = false;
  g.add(fantasma);
  const tapa = crearTapa({ rBoca: rB * MM, rInterior: (R1 - t) * MM });
  tapa.position.copy(Pm(0, 0, H));
  tapa.visible = false;
  g.add(tapa);
  g.add(ancla('ancla_asiento_tapa', Pm(0, 0, H)));
  terminar(g, { datos: datos(o) });
  return g;
}

// ==================================================================
// Tapa del vaso con su cono (SUPUESTA: no hay medida en config)
// ==================================================================
// Ala plana de Ø(boca) = 78 mm y 3,5 mm de alto que asienta en la pestana del vaso, y un TAPON
// conico hueco (Ø59,6 arriba -> Ø52 abajo, 6 mm de profundidad) que entra en la boca (Ø60,4
// interior): al caer, el cono la centra sola. El hueco del tapon deja que las tapas se APILEN
// una dentro de otra en el tubo (paso de 6,2 mm, el mismo de visor.js).
// Origen: el ASIENTO (cara de abajo del ala) en el eje; el tapon baja hasta z = -6 mm.
export function crearTapa(o = {}) {
  const rB = (o.rBoca ?? 0.039) / MM, ri = (o.rInterior ?? 0.0302) / MM;
  const rp = ri - 0.4;
  const g = new THREE.Group();
  g.name = 'tapa';
  torno(g, [[0, -6], [rp - 3.8, -6], [rp, -0.3], [rp, 0], [rB - 1.2, 0], [rB, 1.0], [rB, 2.6], [rB - 0.9, 3.5],
    [rp - 1.2, 3.5], [rp - 4.6, -4.8], [0, -4.8]], mat(o.color ?? COLOR.tapa, { roughness: 0.5, side: THREE.DoubleSide }), 56, 'cuerpo_tapa');
  // Nervio de agarre en el ala (relieve de 0,4 mm).
  const nervio = new THREE.Mesh(new THREE.TorusGeometry((rB - 4) * MM, 0.5 * MM, 4, 56), mat(0xe07a18, { roughness: 0.5 }));
  nervio.rotation.x = Math.PI / 2;
  nervio.position.copy(Pm(0, 0, 3.5));
  g.add(nervio);
  terminar(g, { datos: datos(o) });
  return g;
}

// ==================================================================
// Taco de casilla (SUPUESTO, impreso): encaja la base del vaso
// ==================================================================
// Va pegado a cada separador de la cinta (se mueve con el): dos caras concavas de R = radio de
// la base del vaso + 0,8 mm, centradas a +-(paso/2) = +-40 mm, que abrazan la base del vaso de
// cada casilla por adelante y por atras. Abierto hacia los lados (+-y): el empujador puede
// sacar el vaso de lado y el extremo de la cinta lo deja caer.
// Origen: el pie del separador (centro, sobre la banda); el taco sube `alto` mm (10 < 15 del
// separador). opciones: paso (m), rBase (m, radio de la base del vaso), medioAncho, alto (mm).
export function crearTacoCasilla(o = {}) {
  const paso = (o.paso ?? 0.08) / MM, R = (o.rBase ?? 0.02666) / MM + 0.8;
  const w = Math.min(o.medioAncho ?? 22, R - 2), alto = o.alto ?? 10, c = paso / 2;
  const xr = (y) => c - Math.sqrt(R * R - y * y);
  const N = 14, pts = [];
  for (let i = 0; i <= N; i++) { const y = w - 2 * w * i / N; pts.push([xr(y), y]); }
  for (let i = 0; i <= N; i++) { const y = -w + 2 * w * i / N; pts.push([-xr(y), y]); }
  const g = new THREE.Group();
  g.name = 'taco_casilla';
  prisma(g, pts, alto, o.color ?? 0x8e969f, 0, { roughness: 0.6 }, 'taco');
  terminar(g, { datos: datos(o) });
  return g;
}

// ==================================================================
// Tubo vertical de tapas con escape de dos dedos (servo SG90)
// ==================================================================
// Tubo de acrilico (Ø int = tapa + 4 mm, pared 2 mm) apoyado en un CABEZAL impreso de 16 mm con
// dos ranuras al frente (-y). Por ellas entran dos DEDOS que deslizan en y: el de abajo (A)
// sostiene la tapa de abajo por el ala; el de arriba (B) entra entre la primera y la segunda.
// Los mueve un SG90 invertido (cuerpo arriba, eje hacia abajo) con el cuerno doble: cada punta
// del cuerno lleva un perno que entra en la ranura de un dedo; al girar +-14 grados un dedo
// sale 6 mm y el otro entra (escape de reloj: cae UNA tapa). El servo va en una placa de una
// abrazadera del tubo, por encima del haz de la cortina y fuera del paso de los vasos.
// Origen: eje del tubo en la cara de abajo del cabezal. Nodos: escape (dedo_a, dedo_b),
// tapa_0..n. userData: poner(u) (0 = A sostiene, 1 = suelta la de abajo), pila, dedos,
// zAsiento0 (m, asiento de la tapa de abajo), rExterior (m), crearTapa().
export function crearTuboTapas(o = {}) {
  const rT = (o.rTapa ?? 0.039) / MM, rInV = (o.rInteriorVaso ?? 0.0302) / MM;
  const H = (o.altoTubo ?? 0.075) / MM, n = o.nTapas ?? 10, paso = (o.pasoTapas ?? 0.0062) / MM;
  const rIn = rT + 2, rEx = rIn + 2, rCab = rEx + 3;
  const zA0 = 6.5;                                   // asiento de la tapa de abajo (sobre el dedo A)
  const g = new THREE.Group();
  g.name = 'tubo_tapas';
  const matImp = () => mat(IMPRESO, PLASTICO);
  // Cabezal del escape (impreso) con las ranuras de los dedos, y el tubo de acrilico.
  torno(g, [[rIn, 0], [rCab, 0], [rCab, 16], [rIn, 16], [rIn, 0]], matImp(), 56, 'cabezal_escape');
  const tubo = new THREE.Mesh(new THREE.CylinderGeometry(rEx * MM, rEx * MM, (H - 14) * MM, 48, 1, true),
    mat(0xcfe3ff, { transparent: true, opacity: 0.22, side: THREE.DoubleSide, roughness: 0.1, depthWrite: false }));
  tubo.position.copy(Pm(0, 0, 14 + (H - 14) / 2));
  tubo.name = 'tubo';
  g.add(tubo);
  const xDedo = 12, yRanura = -Math.sqrt(rCab * rCab - xDedo * xDedo);
  for (const [x, z0, z1] of [[xDedo, 3, 7], [-xDedo, 9.6, 13]]) cjL(g, x - 3.5, x + 3.5, yRanura - 0.6, yRanura + 0.4, z0, z1, 0x0b0d10);
  // Abrazaderas: la de arriba (aluminio, al colgante) y la del servo (impresa).
  const abrSup = torno(g, [[rEx, H - 8], [rEx + 4, H - 8], [rEx + 4, H], [rEx, H], [rEx, H - 8]], mat(COLOR.aluminio, ALU), 56, 'abrazadera_sup');
  const abrServo = torno(g, [[rEx, 26], [rEx + 4, 26], [rEx + 4, 36], [rEx, 36], [rEx, 26]], matImp(), 56, 'abrazadera_servo');
  for (const z of [H - 4, 31]) {
    cjL(g, -6, 6, rEx + 3, rEx + 5.5, z - 3, z + 3, z > 40 ? COLOR.aluminio : IMPRESO, z > 40 ? ALU : PLASTICO);   // oreja al colgante
    // Cabeza del M3 DETRAS del colgante de 12 mm (el visor lo pone con su cara contra la oreja,
    // en rEx + 5,5 mm): el tornillo lo atraviesa y rosca en la oreja. Antes la cabeza quedaba
    // entre la oreja y el colgante, metida en el perfil (agente de solapes, 2026-09-27).
    ci(g, 1.6, 1.2, 0xb8bec6, 0, rEx + 5.5 + 12 + 0.6, z, METAL, 10, 'y');
  }
  // Pila de tapas (encajadas una en otra).
  const pila = [];
  for (let k = 0; k < n; k++) {
    const t = crearTapa({ rBoca: rT * MM, rInterior: rInV * MM });
    t.position.copy(Pm(0, 0, zA0 + k * paso));
    t.name = `tapa_${k}`;
    g.add(t);
    pila.push(t);
  }
  // Servo SG90 invertido: eje en (0, ys), origen (cara de apoyo de las orejas) a zS.
  const ys = -58, zS = 29.5, aPin = 12.4, a0 = 14.2 * Math.PI / 180;
  const servo = crearServo({ modelo: 'SG90', cuerno: 'doble', id: o.idServo ?? 'servo_tapas', idComponente: o.idComponente });
  servo.rotation.x = Math.PI;
  servo.position.copy(Pm(0, ys, zS));
  g.add(servo);
  const cuerno = servo.getObjectByName('cuerno');
  // Pernos de las puntas del cuerno (en el marco del servo: z del servo = hacia abajo aqui).
  const zBrazo = 14.1;
  const pinA = zS - 4.5 - zBrazo, pinB = zS - 11 - zBrazo;
  ci(cuerno, 1.0, pinA, ACERO, aPin, 0, zBrazo + pinA / 2, METAL, 10);
  ci(cuerno, 1.0, pinB, ACERO, -aPin, 0, zBrazo + pinB / 2, METAL, 10);
  // Placa del servo (arriba de las orejas) con la ventana del cuerpo, pegada a su abrazadera.
  placaConVentana(g, [-24, 13, -68, -47], [-17, 6.3, -64.3, -51.7], zS, zS + 3, IMPRESO, PLASTICO);
  cjL(g, -10, 10, -48, -rEx - 1, zS, zS + 3, IMPRESO, PLASTICO);
  for (const x of [-19.1, 8.4]) tornilloZ(g, x, ys, zS + 3, 1.3);
  // Dedos (se arman en la posicion de SOSTENER; poner() los corre en y).
  const yPunta = -33.5, yCola = ys + aPin * Math.sin(a0);
  const escape = new THREE.Group();
  escape.name = 'escape';
  const dedo = (nombre, x, z0, z1) => {
    const d = new THREE.Group();
    d.name = nombre;
    cjL(d, x - 3, x + 3, yCola, yPunta, z0, z1, 0xd9261a, { roughness: 0.45 });
    cjL(d, x - 5, x + 5, yCola - 3, yCola + 3, z0, z1, 0xb81f15, { roughness: 0.45 });   // cola con ranura en x
    cjL(d, x - 3.8, x + 3.8, yCola - 1.1, yCola + 1.1, z1, z1 + 0.05, 0x1a1a1a);
    escape.add(d);
    return d;
  };
  const dedoA = dedo('dedo_a', xDedo, 3.5, 6.5), dedoB = dedo('dedo_b', -xDedo, 10.1, 12.5);
  g.add(escape);
  const poner = (u) => {
    const a = a0 * (1 - 2 * u);
    cuerno.rotation.y = -a;
    dedoA.position.z = -(aPin * (Math.sin(a) - Math.sin(a0))) * MM;       // Three z = -y
    dedoB.position.z = -(aPin * (-Math.sin(a) - Math.sin(a0))) * MM;
  };
  poner(0);
  g.add(ancla('ancla_colgante', Pm(0, rEx + 5.5, H - 4)));
  terminar(g, { datos: datos(o) });
  Object.assign(g.userData, { poner, pila, dedos: [dedoA, dedoB], servo, cuerno, zAsiento0: zA0 * MM, rExterior: (rEx + 4) * MM, rOreja: (rEx + 5.5) * MM,
    crearTapa: () => crearTapa({ rBoca: rT * MM, rInterior: rInV * MM }), estructura: [abrSup], motor: [servo, escape] });
  return g;
}

// ==================================================================
// Prensa de tapa: leva excentrica en un MG996R
// ==================================================================
// Placa de montaje de aluminio de 6 mm atornillada a la viga del portico (cara +y de la placa
// contra la cara -y de la viga). El MG996R pasa por una ventana de la placa y se atornilla, con
// dos separadores impresos de 17 mm, con el eje hacia -y: su cuerno de disco lleva la LEVA
// (disco de Ø44 x 8 mm, excentricidad 6,5 mm). Debajo, el piston: rodillo seguidor (Ø12) en una
// horquilla, vastago de acero Ø8 guiado por un buje impreso con casquillo de bronce, collar,
// resorte de retorno (entre el buje y el collar: devuelve el piston contra la leva) y, abajo,
// el plato de aluminio (Ø62) con un resorte LIMITADOR entre el vastago y el plato (un objeto
// extrano no rompe nada) y una almohadilla de neopreno de 0,5 mm. Con la leva a 0 grados el
// rodillo toca la leva; a 180 grados el piston bajo 2 x 6,5 = 13 mm y la almohadilla toca la
// tapa. Todo sale de las mismas cuentas que animan visor.js (piston.position.y).
// Origen: eje del piston en la cara de abajo del plato con el piston ARRIBA (z = zPiston de
// visor.js). opciones (m): exc, zEje (eje del servo sobre el origen), rLeva, rPlato, yPlaca
// (cara -y de la placa, desde el eje), zPlaca0/zPlaca1 (borde de abajo / arriba de la placa).
// Nodos: piston (se mueve en z), leva (gira con rotation.z), servo_prensa.
export function crearPrensaLeva(o = {}) {
  const exc = (o.exc ?? 0.0065) / MM, zE = (o.zEje ?? 0.1105) / MM, R = (o.rLeva ?? 0.022) / MM;
  const rPl = (o.rPlato ?? 0.031) / MM, yPl = (o.yPlaca ?? 0.039) / MM;
  const zP0 = (o.zPlaca0 ?? 0.016) / MM, zP1 = (o.zPlaca1 ?? 0.181) / MM;
  const g = new THREE.Group();
  g.name = 'prensa';
  const fijas = [];
  // Servo MG996R: eje hacia -y a zE; la cara de las orejas a yO (el cuerno de disco termina
  // 17,8 mm mas alla; ahi apoya la leva, de y = -4 a +4).
  const yO = 4 + 17.8;
  const servo = crearServo({ modelo: 'MG996R', cuerno: 'disco', id: o.idServo ?? 'servo_prensa', idComponente: o.idComponente });
  servo.rotation.x = Math.PI / 2;
  servo.position.copy(Pm(0, yO, zE));
  g.add(servo);
  // Placa de montaje con la ventana del cuerpo del servo (x -30,85..9,85; z zE +-9,85).
  const placa = new THREE.Group();
  placa.name = 'placa_prensa';
  const vx0 = -31.8, vx1 = 10.8, vz0 = zE - 10.8, vz1 = zE + 10.8;
  for (const [x0, x1, z0, z1] of [[-45, vx0, zP0, zP1], [vx1, 25, zP0, zP1], [vx0, vx1, zP0, vz0], [vx0, vx1, vz1, zP1]]) {
    cjL(placa, x0, x1, yPl, yPl + 6, z0, z1, COLOR.aluminio, ALU);
  }
  for (const x of [-35, 15]) for (const dz of [-6, 6]) ci(placa, 2.6, 1.8, 0xb8bec6, x, yPl - 0.9, zP1 - 10 + dz, METAL, 12, 'y');
  g.add(placa);
  fijas.push(placa);
  // Separadores impresos bajo las orejas del servo y sus tornillos (M4).
  const xc = -(40.7 / 2 - 9.85);
  for (const x of [xc - 24.75, xc + 24.75]) {
    fijas.push(cjL(g, x - 4.5, x + 4.5, yO, yPl, zE - 9.5, zE + 9.5, IMPRESO, PLASTICO));
    for (const dz of [-5, 5]) ci(g, 2.6, 1.8, 0xb8bec6, x, yO - 2.5 - 0.9, zE + dz, METAL, 12, 'y');
  }
  // Leva: disco excentrico (su centro a exc del eje, "arriba" con la leva a 0 grados) y buje.
  const leva = new THREE.Group();
  leva.name = 'leva';
  leva.position.copy(Pm(0, 0, zE));
  const disco = ci(leva, R, 8, 0xe0c341, 0, 0, exc, { metalness: 0.4, roughness: 0.4 }, 48, 'y', 'disco_leva');
  ci(leva, 7, 1.2, 0xc9a92e, 0, -4.4, 0, { metalness: 0.5 }, 24, 'y');
  for (let k = 0; k < 4; k++) ci(leva, 0.9, 0.3, 0x1a1a1a, 4.2 * Math.cos(k * Math.PI / 2), -5.1, 4.2 * Math.sin(k * Math.PI / 2), {}, 8, 'y');
  g.add(leva);
  // Buje guia del vastago (casquillo de bronce) y su brazo a la placa.
  const zG0 = 30, zG1 = 46;
  fijas.push(cjL(g, -11, 11, -10, 10, zG0, zG1, IMPRESO, PLASTICO, 'buje_prensa'),
    cjL(g, -8, 8, 10, yPl, zG0 + 6, zG1, IMPRESO, PLASTICO));
  ci(g, 5.5, 0.6, 0xb08d57, 0, 0, zG1 + 0.3, METAL, 20);
  // Piston (se mueve entero).
  const piston = new THREE.Group();
  piston.name = 'piston';
  ci(piston, rPl - 1, 0.5, 0x151515, 0, 0, -0.25, { roughness: 0.9 }, 48);                  // neopreno
  torno(piston, [[0, 0], [rPl - 1, 0], [rPl, 1], [rPl, 5], [rPl - 1, 6], [0, 6]], mat(COLOR.aluminio, ALU), 56, 'plato');
  ci(piston, 9, 3, IMPRESO, 0, 0, 7.5, PLASTICO, 24);                                         // copa del limitador
  const lim = resorte(6.5, 0.8, 7, 4);
  lim.position.copy(Pm(0, 0, 9));
  piston.add(lim);
  ci(piston, 8, 1, ACERO, 0, 0, 16.5, METAL, 24);                                             // arandela
  const zCollar = 72, zRod = zE + exc - R - 6;                                                // centro del rodillo
  ci(piston, 4, zRod - 7 - 17, ACERO, 0, 0, (17 + zRod - 7) / 2, METAL, 20, 'z', 'vastago');
  ci(piston, 8, 4, ACERO, 0, 0, zCollar + 2, METAL, 24, 'z', 'collar');
  cjL(piston, -7, 7, -8, 8, zRod - 13, zRod - 7, 0x2b2f36, METAL);                            // base de la horquilla
  for (const s of [-1, 1]) cjL(piston, -6, 6, s * 4.5, s * 6.5, zRod - 7, zRod + 4, 0x2b2f36, METAL);
  ci(piston, 6, 8, 0x222222, 0, 0, zRod, { roughness: 0.4 }, 32, 'y', 'rodillo');
  ci(piston, 1.5, 15, ACERO, 0, 0, zRod, METAL, 12, 'y');
  g.add(piston);
  // Resorte de retorno, fijo al buje: se estira/comprime con la posicion del piston.
  const L0 = zCollar - zG1;
  const retorno = resorte(7.5, 1.0, L0, 6);
  retorno.name = 'resorte_retorno';
  retorno.position.copy(Pm(0, 0, zG1 + 0.6));
  retorno.onBeforeRender = () => {
    const L = Math.max(4, piston.position.y / MM + zCollar - zG1 - 0.6);
    retorno.scale.y = L / L0;
    retorno.updateMatrixWorld(true);
  };
  g.add(retorno);
  g.add(ancla('ancla_viga', Pm(-10, yPl + 6, zP1 - 10)));
  terminar(g, { datos: datos(o) });
  Object.assign(g.userData, { piston, leva, disco, servo, exc: exc * MM, zPiston: 0, fijas, motor: [servo, leva, piston, retorno] });
  return g;
}

// ==================================================================
// Empujador de descarga: MG996R con manivela y biela (biela-manivela)
// ==================================================================
// La paleta CUELGA de un carro que corre sobre dos varillas de acero Ø8 en voladizo (por encima
// de los vasos: nada cruza la cinta a la altura de los vasos), fijas a la columna +x del
// portico con un bloque impreso. El MG996R (eje vertical, en una placa atornillada a la misma
// columna) lleva una manivela impresa de r = carrera/2 y una biela rigida de 50 mm hasta el
// carro: con 180 grados de servo la paleta recorre la carrera completa y vuelve (0 -> 180 -> 0).
// Paleta de 60 x 55 mm con cara de goma, colgada del carro con dos brazos.
// Origen: eje de la cinta en la estacion de descarga, a ras de la banda (xd, y, zs).
// opciones (m, relativas al origen): yReposo, yFin (centro de la paleta), columna = {x, y}
// (eje de la columna del portico), zVarillas, zPaleta0 (borde de abajo de la paleta).
// Nodos: paleta (se mueve en y), manivela (gira), biela. userData.poner(u): u = 0 reposo,
// 1 = fin de carrera (la manivela gira pi*u).
export function crearEmpujador(o = {}) {
  const yR = (o.yReposo ?? 0.045) / MM, yF = (o.yFin ?? -0.0225) / MM;
  const col = { x: (o.columna?.x ?? -0.045) / MM, y: (o.columna?.y ?? 0.055) / MM };
  const r = (yR - yF) / 2, L = 50, ys = yR - r + L;
  const zV = (o.zVarillas ?? 0.138) / MM, zPa0 = (o.zPaleta0 ?? 0.016) / MM;
  const zCar0 = zV - 8, zPa1 = zCar0 - 14.5;                  // carro: bujes Ø16 alrededor de las varillas
  const zMan = zCar0 - 9.5;                                    // manivela: 5 mm de espesor, de zMan a zMan + 5
  const zServo = zMan - 17.8;                                  // cara de las orejas del MG996R
  const zBiela = zMan + 6 + 1.5;                               // biela de 3 mm, encima del perno
  const g = new THREE.Group();
  g.name = 'empujador';
  const fijas = [];
  // Servo (girado 180 grados: el cuerpo hacia +x, lejos de la columna) y su placa a la columna.
  const servo = crearServo({ modelo: 'MG996R', cuerno: 'disco', id: o.idServo ?? 'servo_empujador', idComponente: o.idComponente });
  servo.rotation.y = Math.PI;
  servo.position.copy(Pm(0, ys, zServo));
  g.add(servo);
  const xCol = col.x + 10;                                     // cara +x de la columna
  fijas.push(...placaConVentana(g, [xCol, 40, ys - 12.5, ys + 12.5], [-10.3, 31.3, ys - 10.3, ys + 10.3], zServo - 3, zServo, IMPRESO, PLASTICO));
  fijas.push(cjL(g, xCol, xCol + 6, ys - 12.5, ys + 12.5, zServo - 25, zServo - 3, IMPRESO, PLASTICO));   // escuadra a la columna
  for (const x of [-(-10.5 - 24.75), -(-10.5 + 24.75)]) tornilloZ(g, x, ys, zServo, 2.2);
  // Varillas y su bloque en la columna.
  const yV0 = yF - 13, yV1 = col.y + 10;
  for (const x of [-15, 15]) fijas.push(ci(g, 4, yV1 - yV0, ACERO, x, (yV0 + yV1) / 2, zV, METAL, 16, 'y'));
  fijas.push(cjL(g, xCol, 22, col.y, col.y + 10, zV - 9, zV + 9, IMPRESO, PLASTICO, 'bloque_varillas'));
  for (const x of [-15, 15]) ci(g, 4.5, 0.8, 0x2b2f36, x, yV0 - 0.4, zV, METAL, 16, 'y');     // topes
  // Manivela (gira sobre el eje del servo): brazo de r mm con perno arriba.
  const manivela = new THREE.Group();
  manivela.name = 'manivela';
  manivela.position.copy(Pm(0, ys, zMan));
  ci(manivela, 7.5, 5, IMPRESO, 0, 0, 2.5, PLASTICO, 24);
  cjL(manivela, -5, 5, 0, r, 0, 5, IMPRESO, PLASTICO);
  ci(manivela, 5, 5, IMPRESO, 0, r, 2.5, PLASTICO, 20);
  ci(manivela, 1.9, 8, ACERO, 0, r, 5 + 2, METAL, 12);                                         // perno
  g.add(manivela);
  // Paleta + carro (se mueven juntos en y).
  const paleta = new THREE.Group();
  paleta.name = 'paleta';
  // Paleta de 60 x 55 mm (empuja el vaso entre 16 y 71 mm de altura, por debajo de su centro)
  // colgada de dos brazos de 6 x 4 mm hasta el carro, con un travesano arriba.
  const zPl1 = zPa0 + 55;
  cjL(paleta, -30, 30, -2, 2, zPa0, zPl1, 0x2a8c46, { roughness: 0.5 });
  cjL(paleta, -28, 28, -3.5, -2, zPa0 + 3, zPl1 - 3, 0x151515, { roughness: 0.95 });           // goma
  for (const x of [-22, 22]) cjL(paleta, x - 3, x + 3, -2, 2, zPl1, zCar0 + 1, 0x2a8c46, { roughness: 0.5 });
  cjL(paleta, -25, 25, -2, 2, zPa1 - 6, zPa1, 0x2a8c46, { roughness: 0.5 });
  for (const x of [-15, 15]) ci(paleta, 8, 18, IMPRESO, x, 0, zV, PLASTICO, 20, 'y');          // bujes
  cjL(paleta, -15, 15, -8, 8, zV - 6, zV + 6, IMPRESO, PLASTICO);
  ci(paleta, 1.9, zCar0 - zBiela + 2, ACERO, 0, 0, (zCar0 + zBiela) / 2 - 1, METAL, 12);     // perno de la biela
  g.add(paleta);
  // Biela rigida de L mm (ojos en las puntas).
  const biela = new THREE.Group();
  biela.name = 'biela';
  cj(biela, L, 7, 3, ACERO, 0, 0, 0, METAL);
  for (const s of [-1, 1]) ci(biela, 4.5, 3, ACERO, s * L / 2, 0, 0, METAL, 16);
  g.add(biela);
  const poner = (u) => {
    const th = Math.PI * u;
    const px = r * Math.sin(th), py = ys + r * Math.cos(th);
    const yc = py - Math.sqrt(L * L - px * px);
    paleta.position.z = -yc * MM;
    manivela.rotation.y = -th;
    const cu = servo.getObjectByName('cuerno');
    if (cu) cu.rotation.y = th;
    biela.position.copy(Pm(px / 2, (py + yc) / 2, zBiela));
    biela.rotation.y = Math.atan2(py - yc, px);   // eje x de la biela: del perno del carro al de la manivela
  };
  poner(0);
  g.add(ancla('ancla_columna', Pm(col.x, col.y, zServo - 14)));
  terminar(g, { datos: datos(o) });
  Object.assign(g.userData, { poner, paleta, manivela, biela, servo, fijas, carrera: 2 * r * MM, motor: [servo, paleta, manivela, biela] });
  return g;
}

// ==================================================================
// Accionamiento de la cinta: NEMA17 directo al rodillo (acople flexible)
// ==================================================================
// NEMA17 17HS4401 con el eje a lo ancho de la cinta, en una placa impresa sostenida por 4
// separadores de 20 mm desde la placa lateral del bastidor; acople flexible de aluminio
// 5 -> 8 mm (Ø19 x 25) entre el eje del motor y el del rodillo, que gira en un rodamiento
// con brida (KFL08) atornillado a la placa lateral.
// Origen: eje del rodillo en la cara EXTERIOR de la placa lateral; el motor queda hacia -y.
// Nodos: nema17 (con su `eje`), acople. userData.nema (el grupo del motor).
export function crearAccionamientoCinta(o = {}) {
  const g = new THREE.Group();
  g.name = 'accionamiento_cinta';
  // Rodamiento con brida de 2 agujeros.
  cjL(g, -24, 24, -3, 0, -7, 7, 0x8c939c, METAL);
  ci(g, 10, 5, 0x6d737b, 0, -4.5, 0, METAL, 28, 'y');
  for (const x of [-18, 18]) ci(g, 2.4, 1.6, 0xb8bec6, x, -3.8, 0, METAL, 12, 'y');
  ci(g, 4, 14, ACERO, 0, -9, 0, METAL, 16, 'y');                                              // eje del rodillo
  // Acople flexible (helicoidal): cuerpo con dos ranuras.
  const acople = new THREE.Group();
  acople.name = 'acople';
  ci(acople, 9.5, 20, 0xb9c0c9, 0, -17, 0, METAL, 28, 'y');
  for (const y of [-13, -21]) ci(acople, 9.6, 0.8, 0x2b2f36, 0, y, 0, {}, 28, 'y');
  g.add(acople);
  // Placa del motor (la cara del motor apoya en ella) y separadores a la placa lateral.
  const yM = -34;
  cjL(g, -24, 24, yM, yM + 5, -24, 24, IMPRESO, PLASTICO);
  for (const [x, z] of [[20, 20], [-20, 20], [20, -20], [-20, -20]]) ci(g, 2.5, -yM - 5, 0xb8bec6, x, (yM + 5) / 2, z, METAL, 10, 'y');
  for (const [x, z] of [[15.5, 15.5], [-15.5, 15.5], [15.5, -15.5], [-15.5, -15.5]]) ci(g, 2.6, 1.6, 0xb8bec6, x, yM + 5.8, z, METAL, 12, 'y');
  const nema = crearNEMA17({ id: o.id ?? 'motor_vasos', idComponente: o.idComponente });
  nema.rotation.x = -Math.PI / 2;                   // eje (+z de la pieza) -> +y
  nema.position.copy(Pm(0, yM, 0));
  g.add(nema);
  terminar(g, { datos: datos(o) });
  g.userData.nema = nema;
  return g;
}

// ==================================================================
// Panel de luz (contraluz de la camara de vasos)
// ==================================================================
// Panel LED de borde: difusor de acrilico opalino de 3 mm, marco de aluminio en L de 5 mm
// (0,8 mm de ala al frente) y la tira LED de 5 V con su conector atras, abajo a la derecha.
// Origen: centro de la cara del FRENTE (la que mira a la camara, hacia -y). opciones: largo,
// alto (m). Nodo: difusor (emisivo).
export function crearPanelLuz(o = {}) {
  const Lx = (o.largo ?? 0.33) / MM, Hz = (o.alto ?? 0.1) / MM;
  const g = new THREE.Group();
  g.name = 'panel_luz';
  // El difusor queda 0,3 mm adentro del marco en los cantos y 0,2 mm antes de su cara de atras:
  // con las caras en el mismo plano, la tarjeta de video las mezclaba (parpadeo, 2026-09-28).
  const dif = cjL(g, -Lx / 2 + 0.3, Lx / 2 - 0.3, 0, 2.8, -Hz / 2 + 0.3, Hz / 2 - 0.3, 0xf4f7fb, { emissive: 0xeaf2ff, emissiveIntensity: 0.55, roughness: 0.9 }, 'difusor');
  dif.receiveShadow = false;
  const m = (x0, x1, z0, z1) => cjL(g, x0, x1, -0.8, 3, z0, z1, COLOR.aluminio, ALU);
  m(-Lx / 2, Lx / 2, Hz / 2 - 5, Hz / 2);
  m(-Lx / 2, Lx / 2, -Hz / 2, -Hz / 2 + 5);
  m(-Lx / 2, -Lx / 2 + 5, -Hz / 2, Hz / 2);
  m(Lx / 2 - 5, Lx / 2, -Hz / 2, Hz / 2);
  cjL(g, Lx / 2 - 40, Lx / 2 - 28, 3, 6, -Hz / 2 + 8, -Hz / 2 + 18, 0xf2f0e6, PLASTICO, 'conector_panel');
  terminar(g, { datos: datos(o) });
  return g;
}

// ==================================================================
// Poste de la camara de vasos
// ==================================================================
// Perfil 20x20 de aluminio sobre un pie de 30 x 30 mm, con una placa impresa arriba que llega
// hasta el tornillo de 1/4" de la escuadra de la webcam (sensores.js: ancla_soporte).
// Origen: centro del pie en el piso. opciones (m): alto (hasta la cara de abajo de la placa),
// haciaAncla (desplazamiento en y del ancla respecto del poste).
export function crearPosteCamara(o = {}) {
  const H = (o.alto ?? 0.19) / MM, dy = (o.haciaAncla ?? -0.017) / MM;
  const g = new THREE.Group();
  g.name = 'poste_camara';
  cjL(g, -15, 15, -15, 15, 0, 4, 0x30363d, METAL);
  cjL(g, -10, 10, -10, 10, 4, H, COLOR.aluminio, ALU);
  for (const [x, y] of [[-10, 0], [10, 0], [0, -10], [0, 10]]) cj(g, x ? 0.3 : 6, y ? 0.3 : 6, H - 8, 0x3a4048, x * 1.0, y * 1.0, (H + 4) / 2);   // ranuras
  const y0 = Math.min(-10, dy - 8), y1 = Math.max(10, dy + 8);
  cjL(g, -12, 12, y0, y1, H, H + 4, IMPRESO, PLASTICO);
  tornilloZ(g, 0, dy, H + 4, 3.2);
  g.add(ancla('ancla_camara', Pm(0, dy, H + 4)));
  terminar(g, { datos: datos(o) });
  return g;
}

// ==================================================================
// Porta-sensor del VL53L0X del interior del vaso
// ==================================================================
// Placa impresa de 30 x 7 x 3 mm atornillada a la GY-VL53L0XV2 por sus 2 agujeros (x = +-10,35,
// y = -1,6 mm) con separadores M2 de 5 mm (el header de pines queda libre, hacia +y), y un
// bloque con tornillo prisionero que toma la varilla Ø4 que la cuelga del portico.
// Origen: el de la placa del sensor (centro, cara de abajo del PCB). userData.colgar = punto
// (local, m) donde entra la varilla.
export function crearPortaVL53Interior(o = {}) {
  const g = new THREE.Group();
  g.name = 'porta_vl53';
  const T = 1.6;
  for (const x of [-10.35, 10.35]) {
    ci(g, 1.6, 5, 0xc9a24a, x, -1.6, T + 2.5, METAL, 6);
    tornilloZ(g, x, -1.6, T + 8, 1.6);
  }
  cjL(g, -15, 15, -5.4, 1.6, T + 5, T + 8, IMPRESO, PLASTICO, 'placa_porta');
  cjL(g, -4, 4, -5.4, 1.6, T + 8, T + 14, IMPRESO, PLASTICO);
  ci(g, 1.2, 1.5, 0xb8bec6, 4.6, -1.9, T + 11, METAL, 10, 'x');
  terminar(g, { datos: datos(o) });
  g.userData.colgar = Pm(0, -1.9, T + 14);
  return g;
}

// ==================================================================
// Camara de vasos: webcam 720p (sensores.js) mirando hacia +y, en su poste
// ==================================================================
// Webcam USB de 42 x 42 x 20 mm SIN anillo (la luz la pone el panel de contraluz), girada para
// mirar a lo ancho de la cinta (+y), con su escuadra y rotula; el tornillo de 1/4" de la
// escuadra apoya en la placa del poste (crearPosteCamara), que baja al piso 22 mm detras de la
// camara (config zonas_carro: el poste queda dentro del cuadrado de 40 mm alrededor de ella).
// Origen: centro de la carcasa de la camara (= posicion de la camara en sim/geometria.py).
// opciones: alturaOptica (m, z de la camara sobre el piso), id, sensorId.
// userData: led (LED de actividad), camara (la webcam), poste.
export function crearCamaraVasos(o = {}) {
  const g = new THREE.Group();
  g.name = 'camara_vasos';
  const cam = crearWebcam({ id: o.id ?? 'cam_vasos', sensorId: o.sensorId ?? 'camara_vasos', anillo: false, resolucion: '720p' });
  cam.rotation.x = Math.PI / 2;                     // optica (-Y de la pieza) -> +y de la simulacion
  g.add(cam);
  cam.updateMatrix();
  const a = cam.getObjectByName('ancla_soporte').position.clone().applyMatrix4(cam.matrix);
  const yA = -a.z / MM, zA = a.y / MM;              // ancla en mm (marco de la simulacion)
  const yPoste = yA + 15;
  const zPiso = -(o.alturaOptica ?? 0.2118) / MM;
  const poste = crearPosteCamara({ alto: (zA - 4 - zPiso) * MM, haciaAncla: (yA - yPoste) * MM, sensorId: o.sensorId ?? 'camara_vasos' });
  poste.position.copy(Pm(0, yPoste, zPiso));
  g.add(poste);
  g.userData.led = cam.getObjectByName('led_estado');
  g.userData.camara = cam;
  g.userData.poste = poste;
  g.userData.puntosPoste = [Pm(8, yPoste, zA - 6), Pm(8, yPoste, zPiso + 8)];
  return g;
}
