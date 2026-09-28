// Piezas del CARRO de entrega y del MUELLE de carga (visor 3D, Three.js).
// Convencion: ver README.md de esta carpeta. Marco de la simulacion (x a lo largo, hacia el
// frente del carro; y a lo ancho, hacia su izquierda; z arriba), metros; las medidas de ficha
// van en mm y se pasan con MM.
//
// De donde salen las medidas:
// - config/parametros.yaml (vehiculo, canaleta, vaso) via sim/geometria.py: largo 180, ancho
//   120, rueda de 65 mm, eje a -0,18 x largo, rueda loca a +0,30 x largo, rodillos guia 623 en
//   (-L/2 + 8, +-86) mm a 12 mm del piso, 5 infrarrojos a 15 mm, rieles de la cuna.
// - sim/vehiculo_sim.py (_crear_muelle): guias en V (6 mm de espesor, 20 de alto, 3 mm de
//   holgura sobre los rodillos, boca 45 mm mas abierta en 200 mm) y topes de la cola.
// - Fichas tipicas: motorreductor TT 1:48 (70 x 22,5 x 18,8 mm, eje doble en D de 5,4 x 3,7 a
//   11 mm del extremo, motor 130 de O20 con planos a 15 mm), rueda TT de 65 x 26 mm, rodamiento
//   623 (3 x 10 x 4 mm), rueda loca de bola de acero de 16 mm, separadores hexagonales M3.
//
// Contenido:
//   disposicionCarro(o)       donde va cada cosa del carro (la usa construirCarro de visor.js)
//   crearChasisCarro(o)       placa de acrilico de 3 mm con hueco del vaso, ranuras y agujeros
//   crearPerfboard(o)         segundo piso (placa perforada de fibra de vidrio)
//   crearSeparadorM3(o)       separador hexagonal de laton
//   crearMotorTT(o)           motorreductor TT con sus soportes en T, pernos y terminales
//   crearRuedaTT(o)           rueda de 65 mm: rin amarillo con rayos, llanta con dibujo, eje
//   crearRuedaLocaBola(o)     rueda loca de bola de acero con su brida y separadores
//   crearRodilloGuia623(o)    dos rodamientos 623 en un tornillo M3, con su brazo impreso
//   crearSoporteEncoder(o)    columna impresa con repisa que sostiene el H206
//   crearEscuadraFrontal(o)   escuadra impresa del HC-SR04 y del VL53L0X
//   crearCunaCarro(o)         rieles con PTFE, postes, mampara con espumas, guias, lengueta
//   crearMuelleCarga(o)       guias en V con PTFE y topes con espuma (en el piso)

import * as THREE from 'three';
import { MM, COLOR, METAL, PLASTICO, P, mat, caja, cilindro, ancla, planoDibujado, terminar } from './base.js';

const ACRILICO = 0x2b3947;          // acrilico ahumado
const PLA = COLOR.impreso;          // piezas impresas (PLA gris oscuro)
const PTFE = 0xf1f1ee;              // cinta de PTFE (teflon)
const ESPUMA = 0xe3c565;            // espuma EVA amarilla
const LATON = 0xc8a24a;
const ACERO = 0xb8bcc2;

// ------------------------------------------------------------------ ayudantes (mm)
// Caja de sx × sy × sz mm centrada en (x, y, z) mm.
function cj(g, sx, sy, sz, x, y, z, color, extra) {
  const m = caja(sx * MM, sy * MM, sz * MM, color, P(x * MM, y * MM, z * MM), extra);
  g.add(m);
  return m;
}
// Cilindro de radio r y alto h mm con el eje a lo largo de 'x' | 'y' | 'z' (de la simulacion).
function ci(g, r, h, x, y, z, color, eje = 'z', extra, seg = 24) {
  const m = cilindro(r * MM, h * MM, color, P(x * MM, y * MM, z * MM), extra, seg);
  if (eje === 'x') m.rotation.z = Math.PI / 2;
  else if (eje === 'y') m.rotation.x = Math.PI / 2;
  g.add(m);
  return m;
}
// Tuerca / separador hexagonal (6 lados) de "entre caras" e mm y alto h mm.
function hexa(g, e, h, x, y, z, color, eje = 'z', extra = METAL) {
  return ci(g, e / Math.sqrt(3), h, x, y, z, color, eje, extra, 6);
}
// Varilla entre dos puntos (vectores de Three, en metros).
function varilla(g, a, b, radio, color, extra, seg = 14) {
  const d = new THREE.Vector3().subVectors(b, a);
  const m = new THREE.Mesh(new THREE.CylinderGeometry(radio, radio, d.length(), seg),
    color && color.isMaterial ? color : mat(color, extra));
  m.position.copy(a).addScaledVector(d, 0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize());
  m.castShadow = true;
  g.add(m);
  return m;
}
// Extrusion de una forma 2D (mm) de `prof` mm:
//  'xy': la forma en el plano x-y de la simulacion, extruida hacia +z desde z = desde;
//  'xz': forma en x-z (perfil lateral), extruida hacia +y desde y = desde;
//  'yz': forma en y-z (perfil frontal), extruida hacia +x desde x = desde.
function extruir(forma, prof, plano = 'xy', desde = 0, { bisel = 0, curvas = 16 } = {}) {
  const geo = new THREE.ExtrudeGeometry(forma, {
    depth: prof - 2 * bisel, bevelEnabled: bisel > 0, bevelThickness: bisel, bevelSize: bisel,
    bevelSegments: 2, curveSegments: curvas,
  });
  geo.translate(0, 0, bisel);
  if (plano === 'xy') { geo.translate(0, 0, desde); geo.rotateX(-Math.PI / 2); }
  else if (plano === 'xz') geo.translate(0, 0, -desde - prof);
  else { geo.translate(0, 0, desde); geo.rotateY(Math.PI / 2); }
  geo.scale(MM, MM, MM);
  return geo;
}
function malla(g, geo, color, extra) {
  const m = new THREE.Mesh(geo, color && color.isMaterial ? color : mat(color, extra));
  m.castShadow = true;
  g.add(m);
  return m;
}
// Rectangulo de esquinas redondeadas (x0, y0)-(x1, y1) como Shape o Path (hueco).
function rect(x0, y0, x1, y1, r = 0, hueco = false) {
  const s = hueco ? new THREE.Path() : new THREE.Shape();
  r = Math.min(r, (x1 - x0) / 2, (y1 - y0) / 2);
  s.moveTo(x0 + r, y0);
  s.lineTo(x1 - r, y0); if (r) s.quadraticCurveTo(x1, y0, x1, y0 + r);
  s.lineTo(x1, y1 - r); if (r) s.quadraticCurveTo(x1, y1, x1 - r, y1);
  s.lineTo(x0 + r, y1); if (r) s.quadraticCurveTo(x0, y1, x0, y1 - r);
  s.lineTo(x0, y0 + r); if (r) s.quadraticCurveTo(x0, y0, x0 + r, y0);
  return s;
}
function circulo(x, y, r) {
  const p = new THREE.Path();
  p.absarc(x, y, r, 0, Math.PI * 2, true);
  return p;
}
// Ranura (agujero chino) de largo l y ancho w centrada en (x, y), a lo largo de x o de y.
function ranura(x, y, l, w, ejeX = true) {
  return ejeX ? rect(x - l / 2, y - w / 2, x + l / 2, y + w / 2, w / 2, true)
    : rect(x - w / 2, y - l / 2, x + w / 2, y + l / 2, w / 2, true);
}
// Cabeza de tornillo Allen/Phillips vista desde +z (o -z con abajo = true).
function cabeza(g, x, y, z, { r = 2.75, h = 1.8, abajo = false, color = ACERO } = {}) {
  ci(g, r, h, x, y, z + (abajo ? -h / 2 : h / 2), color, 'z', METAL, 16);
  cj(g, r * 1.1, 0.5, 0.3, x, y, z + (abajo ? -h - 0.1 : h + 0.1), 0x2a2a2a);
}

// ==================================================================
// Disposicion: donde va cada cosa del carro, en metros y en el marco del carro (origen en el
// piso bajo el centro del chasis). Todo lo que la simulacion fija (eje de las ruedas, rodillos,
// rueda loca, alturas de los sensores, rieles) sale de sus parametros; lo demas es el boceto.
// La placa va 11,5 mm POR ENCIMA del eje (como en los kits de 2 ruedas: el reductor TT de 22,5
// mm de alto cuelga debajo sin tocarla) y el fondo del vaso colgado pasa por un hueco de ella.
// ==================================================================
export function disposicionCarro({ largo = 0.18, ancho = 0.12, diametroRueda = 0.065, zRiel = 0.129,
  vasoDiametro = 0.062, vasoAltura = 0.09 } = {}) {
  const L = largo, W = ancho, r = diametroRueda / 2;
  const d = { L, W, r };
  d.xRueda = -0.18 * L;                          // eje de las ruedas (sim)
  d.yRueda = W / 2 + 0.013;                      // centro de cada rueda (sim)
  d.eBase = 0.003;                               // acrilico de 3 mm
  d.zBaseAbajo = r + 0.0115;                     // cara de abajo de la placa (el reductor llega a r + 11,25)
  d.zPlaca = d.zBaseAbajo + d.eBase / 2;         // centro de la placa (como antes, para P.carroDims)
  d.zBaseArriba = d.zBaseAbajo + d.eBase;
  d.zPiso2 = d.zPlaca + 0.03;                    // segundo piso (placa perforada)
  d.yMotor = W / 2 - 0.0149;                     // centro del reductor: soporte externo a 2,5 mm del borde
  d.yDisco = W / 2 - 0.0285;                     // disco del encoder, en la punta interior del eje
  d.yEncoder = W / 2 - 0.030;                    // centro de la horquilla del H206
  d.zEncoder = r - 0.0186;                       // cara de abajo del H206: el haz pasa 11,5 mm bajo el eje
  d.xVaso = -0.025;
  d.rHuecoVaso = vasoDiametro / 2 * 0.86 + 0.0035;   // el fondo del vaso (conico) pasa por aqui
  d.xLoca = 0.30 * L;
  d.xIr = L / 2 - 0.012;
  d.xFrente = L / 2 + 0.002;
  d.zUs = r + 0.004 + 0.02;                      // sim/vehiculo_sim.py (z_us)
  d.zTof = 0.074;
  d.xMampara = 0.016;                            // mampara delantera de la cuna (detras, el reborde del vaso)
  d.zRiel = zRiel;
  d.zMedio = zRiel - vasoAltura / 2;
  // Electronica sobre la placa (bajo el segundo piso).
  d.bateria = [0.0405, 0];                       // porta 2 x 18650 (41 x 76,6 mm), de x = 20 a 61 mm
  d.interruptor = [0.048, 0.052];                // al costado izquierdo: se alcanza desde afuera
  d.tb6612 = [0.0725, -0.03];
  d.separadoresPiso2 = [[0.025, 0.042], [0.025, -0.042], [0.0775, 0.044], [0.0775, -0.044]];
  d.agujerosCables = [[0.082, 0.046], [0.082, -0.046]];   // por aqui suben los hilos de abajo
  return d;
}

// ==================================================================
// Chasis: placa de acrilico ahumado de 180 × 120 × 3 mm con esquinas de 8 mm. Hueco del vaso
// (O del fondo + 7 mm) unido a las ranuras de los discos de encoder (que asoman 1 mm por
// encima de la cara de abajo), ranuras de 3 × 10 mm para las lenguetas de los soportes en T de
// los motores, agujeros de 3,2 mm (separadores, rueda loca, infrarrojos, rodillos) y pasacables
// de 6 mm con arandela de goma. Origen: centro de la placa, en su CARA DE ABAJO.
// opciones (mm, marco de la placa): huecos [[x, y, d]], ranuras [[x, y, l, w, ejeX]],
// pasacables [[x, y]], vaso {x, r}, discos [[x0, x1, y0, y1]].
// ==================================================================
export function crearChasisCarro({ largo = 180, ancho = 120, espesor = 3, huecos = [], ranuras = [],
  pasacables = [], vaso = null, discos = [], idComponente = 'chasis_carro' } = {}) {
  const g = new THREE.Group();
  g.name = 'chasis';
  const forma = rect(-largo / 2, -ancho / 2, largo / 2, ancho / 2, 8);
  if (vaso) {
    // Hueco del vaso unido a las ranuras de los discos: la union es "estrellada" desde el
    // centro del vaso, asi que se recorre por angulos tomando el punto mas lejano.
    const n = 240, pts = [];
    for (let k = 0; k < n; k++) {
      const a = (k / n) * Math.PI * 2, dx = Math.cos(a), dy = Math.sin(a);
      let t = vaso.r;
      for (const [x0, x1, y0, y1] of discos) {
        // salida del rayo por el rectangulo, si entra antes de salir del circulo
        const tx = [(x0 - vaso.x) / dx, (x1 - vaso.x) / dx].sort((p, q) => p - q);
        const ty = [y0 / dy, y1 / dy].sort((p, q) => p - q);
        const tin = Math.max(tx[0], ty[0]), tout = Math.min(tx[1], ty[1]);
        if (tout > tin && tin <= vaso.r + 1 && tout > 0) t = Math.max(t, tout);
      }
      pts.push(new THREE.Vector2(vaso.x + dx * t, dy * t));
    }
    forma.holes.push(new THREE.Path(pts.reverse()));
  }
  for (const [x, y, d] of huecos) forma.holes.push(circulo(x, y, d / 2));
  for (const [x, y, l, w, ejeX] of ranuras) forma.holes.push(ranura(x, y, l, w, ejeX));
  for (const [x, y] of pasacables) forma.holes.push(circulo(x, y, 3));
  const placa = malla(g, extruir(forma, espesor, 'xy', 0, { bisel: 0.4, curvas: 20 }), ACRILICO,
    { roughness: 0.18, metalness: 0.05, transparent: true, opacity: 0.88 });
  placa.name = 'placa';
  placa.receiveShadow = true;
  // Arandelas de goma de los pasacables.
  for (const [x, y] of pasacables) {
    const a = new THREE.Mesh(new THREE.TorusGeometry(3.1 * MM, 0.9 * MM, 8, 20), mat(0x111111, { roughness: 0.9 }));
    a.rotation.x = Math.PI / 2;
    a.position.copy(P(x * MM, y * MM, espesor * MM));
    g.add(a);
  }
  return terminar(g, { datos: { idComponente } });
}

// Segundo piso: placa perforada de fibra de vidrio (FR4 verde) con agujeros a 2,54 mm y pads
// de cobre estanado, y 4 agujeros de 3,2 mm para los separadores. Origen: centro, cara de abajo.
export function crearPerfboard({ largo = 60, ancho = 96, espesor = 1.6, huecos = [] } = {}) {
  const g = new THREE.Group();
  g.name = 'perfboard';
  const forma = rect(-largo / 2, -ancho / 2, largo / 2, ancho / 2, 1.5);
  for (const [x, y] of huecos) forma.holes.push(circulo(x, y, 1.6));
  malla(g, extruir(forma, espesor, 'xy'), 0x2f6b3a, { roughness: 0.75 });
  const tex = planoDibujado(largo * MM, ancho * MM, (ctx, X, Y, k) => {
    for (let x = -largo / 2 + 2; x <= largo / 2 - 2; x += 2.54) {
      for (let y = -ancho / 2 + 2; y <= ancho / 2 - 2; y += 2.54) {
        if (huecos.some(([hx, hy]) => Math.hypot(hx - x, hy - y) < 3)) continue;
        ctx.fillStyle = '#b9a67a'; ctx.beginPath(); ctx.arc(X(x), Y(y), 0.8 * k, 0, 7); ctx.fill();
        ctx.fillStyle = '#10130f'; ctx.beginPath(); ctx.arc(X(x), Y(y), 0.4 * k, 0, 7); ctx.fill();
      }
    }
  }, { ppm: 14 });
  tex.position.copy(P(0, 0, espesor * MM + 0.00005));
  g.add(tex);
  return g;
}

// Separador hexagonal M3 de laton (5,5 mm entre caras) de `alto` mm, parado en z = 0.
export function crearSeparadorM3({ alto = 30, color = LATON } = {}) {
  const g = new THREE.Group();
  hexa(g, 5.5, alto, 0, 0, alto / 2, color, 'z', { metalness: 0.8, roughness: 0.3 });
  return g;
}

// ==================================================================
// Motorreductor TT 1:48 (amarillo), eje doble en D a lo largo de y.
// Origen: centro del eje de salida. El motor 130 queda hacia +x; `lado` = +1 si la cara
// EXTERIOR (la de la rueda) es +y. Reductor 44 × 18,8 × 22,5 mm (extremo trasero redondo
// alrededor del eje, dos mitades con su junta), dos agujeros pasantes de 3,2 mm a (24, +-8,75),
// motor de O20 con planos a 15 mm (x = 33 a 58,5), tapa negra con los terminales +/-.
// Soportes en T de acrilico negro de 3 mm a los dos lados (como los kits): su lengueta de
// 10 × 3 mm entra en la ranura de la placa (`hastaPlaca` mm sobre el eje), y dos pernos M3 × 25
// con tuerca atraviesan soportes y reductor.
// Anclas: pin_<id>_M+ / pin_<id>_M- (punta de los terminales, hacia +x), ancla_ranura_int/ext.
// ==================================================================
export function crearMotorTT({ id = 'motor_izq', lado = 1, soportes = true, hastaPlaca = 11.5, espesorPlaca = 3,
  idComponente = 'motores_carro' } = {}) {
  const g = new THREE.Group();
  g.name = id;
  const R = 11.25, X1 = 33, T = 18.8;
  const perfil = () => {
    const f = new THREE.Shape();
    f.moveTo(0, -R);
    f.lineTo(X1 - 2, -R); f.quadraticCurveTo(X1, -R, X1, -R + 2);
    f.lineTo(X1, R - 2); f.quadraticCurveTo(X1, R, X1 - 2, R);
    f.lineTo(0, R);
    f.absarc(0, 0, R, Math.PI / 2, Math.PI * 1.5, false);
    for (const z of [-8.75, 8.75]) f.holes.push(circulo(24, z, 1.6));
    f.holes.push(circulo(0, 0, 2.9));
    return f;
  };
  // Dos mitades con bisel: la junta queda como un surco, como el reductor real.
  const amarillo = mat(0xf2c230, { roughness: 0.55 });
  malla(g, extruir(perfil(), T / 2, 'xz', -T / 2, { bisel: 0.5, curvas: 20 }), amarillo);
  malla(g, extruir(perfil(), T / 2, 'xz', 0, { bisel: 0.5, curvas: 20 }), amarillo);
  // Resaltes alrededor del eje en las dos caras, y dos tornillos de la carcasa (cara interior).
  for (const s of [-1, 1]) {
    ci(g, 4.6, 1.2, 0, s * (T / 2 + 0.6), 0, 0xe0b028, 'y', { roughness: 0.5 });
    ci(g, 2.9, 1.3, 0, s * (T / 2 + 0.65), 0, 0x6b5410, 'y');
  }
  for (const [x, z] of [[8, 8.3], [8, -8.3]]) {
    ci(g, 1.7, 0.8, x, -lado * (T / 2 + 0.4), z, ACERO, 'y', METAL, 12);
  }
  // Motor 130: lata con planos, franja y tapa negra.
  const lata = (rr, plano) => {
    const c = Math.sqrt(rr * rr - plano * plano), a = Math.atan2(c, plano);
    const f = new THREE.Shape();
    f.moveTo(plano, -c); f.lineTo(plano, c);
    f.absarc(0, 0, rr, a, Math.PI - a, false);
    f.lineTo(-plano, -c);
    f.absarc(0, 0, rr, Math.PI + a, Math.PI * 2 - a, false);
    return f;
  };
  malla(g, extruir(lata(10, 7.5), 25.5, 'yz', X1), COLOR.plata, { metalness: 0.85, roughness: 0.32 });
  malla(g, extruir(lata(10.05, 7.55), 1.2, 'yz', X1 + 8), 0x8d939b, { metalness: 0.7, roughness: 0.4 });
  malla(g, extruir(lata(9.6, 7.3), 2.5, 'yz', X1 + 25.5), 0x151515, { roughness: 0.6 });
  ci(g, 3, 1.2, X1 + 28.6, 0, 0, COLOR.plata, 'x', METAL, 16);
  // Terminales de laton y punto rojo del +.
  for (const [n, s] of [['M+', 1], ['M-', -1]]) {
    cj(g, 3.4, 0.4, 2.4, X1 + 29.2, s * 4.5, 5.2, 0xd4af37, METAL);
    g.add(ancla(`pin_${id}_${n}`, P((X1 + 30.9) * MM, s * 4.5 * MM, 5.2 * MM), { pin: n, dir: new THREE.Vector3(1, 0, 0) }));
  }
  ci(g, 0.9, 0.3, X1 + 28.1, 4.5, 1.2, 0xd23a2a, 'x');
  if (soportes) {
    // Soporte en T: perfil lateral con agujeros para los pernos y la lengueta de arriba.
    const t = new THREE.Shape();
    const x0 = 14, x1 = 34, zb = -15.5, zt = hastaPlaca;
    t.moveTo(x0 + 3, zb); t.lineTo(x1 - 3, zb); t.quadraticCurveTo(x1, zb, x1, zb + 3);
    t.lineTo(x1, zt); t.lineTo(29, zt); t.lineTo(29, zt + espesorPlaca); t.lineTo(19, zt + espesorPlaca);
    t.lineTo(19, zt); t.lineTo(x0, zt); t.lineTo(x0, zb + 3); t.quadraticCurveTo(x0, zb, x0 + 3, zb);
    for (const z of [-8.75, 8.75]) t.holes.push(circulo(24, z, 1.6));
    for (const s of [-1, 1]) {
      const y0 = s > 0 ? T / 2 : -T / 2 - 3;
      malla(g, extruir(t, 3, 'xz', y0, { bisel: 0.3 }), 0x121417, { roughness: 0.25 });
    }
    // Pernos M3 x 25: cabeza del lado interior, tuerca del lado de la rueda.
    for (const z of [-8.75, 8.75]) {
      const yi = -lado * (T / 2 + 3), ye = lado * (T / 2 + 3);
      ci(g, 1.5, Math.abs(ye - yi) + 0.4, 24, 0, z, ACERO, 'y', METAL, 12);
      ci(g, 2.75, 2.5, 24, yi - lado * 1.25, z, 0x2a2d31, 'y', METAL, 16);
      hexa(g, 5.5, 2.4, 24, ye + lado * 1.2, z, ACERO, 'y');
    }
    g.add(ancla('ancla_ranura_int', P(24 * MM, -lado * (T / 2 + 1.5) * MM, (hastaPlaca + espesorPlaca) * MM)));
    g.add(ancla('ancla_ranura_ext', P(24 * MM, lado * (T / 2 + 1.5) * MM, (hastaPlaca + espesorPlaca) * MM)));
  }
  return terminar(g, { datos: { idComponente } });
}

// ==================================================================
// Rueda TT de 65 × 26 mm: rin amarillo (aro, 6 rayos, cubo con agujero en D y tornillo) y
// llanta de goma con dibujo en V (dos filas de tacos desfasados). Opcional: el tramo de eje en D
// blanco que sale de la rueda hacia adentro (`ejeAdentro` mm desde la cara interior).
// Origen: centro de la rueda. EJE DE GIRO = +Y de Three (el visor la acuesta con
// rotation.x = PI/2 y la hace girar con rotation.y); `lado` = +1 si el interior es +Y local
// (la rueda izquierda del carro, acostada, tiene el interior hacia +Y).
// ==================================================================
export function crearRuedaTT({ diametro = 65, ancho = 26, lado = 1, ejeAdentro = 0, idComponente = 'motores_carro' } = {}) {
  const g = new THREE.Group();
  g.name = 'rueda';
  const Ro = diametro / 2, a2 = ancho / 2;
  const torno = (pts, color, extra, seg = 72) => {
    const m = new THREE.Mesh(new THREE.LatheGeometry(pts.map(([rr, y]) => new THREE.Vector2(rr * MM, y * MM)), seg),
      mat(color, extra));
    m.castShadow = true;
    g.add(m);
    return m;
  };
  // Llanta: casco con hombros redondeados; los tacos ponen el ultimo milimetro.
  const Rc = Ro - 1.0;
  torno([[Ro - 6, -a2 + 0.5], [Rc - 1.4, -a2 + 0.5], [Rc - 0.4, -a2 + 1.1], [Rc, -a2 + 2.4], [Rc, a2 - 2.4],
    [Rc - 0.4, a2 - 1.1], [Rc - 1.4, a2 - 0.5], [Ro - 6, a2 - 0.5], [Ro - 6, -a2 + 0.5]], 0x161616, { roughness: 0.95 });
  // Tacos: dos filas en V desfasadas medio paso (InstancedMesh).
  const n = 30, geo = new THREE.BoxGeometry(1.1 * MM, 9.2 * MM, 3.4 * MM);
  const im = new THREE.InstancedMesh(geo, mat(0x1b1b1b, { roughness: 0.9 }), 2 * n);
  const M = new THREE.Matrix4(), Q = new THREE.Matrix4();
  for (let k = 0; k < 2 * n; k++) {
    const fila = k < n ? 1 : -1;
    const a = ((k % n) + (fila > 0 ? 0 : 0.5)) / n * Math.PI * 2;
    M.makeRotationY(a).multiply(Q.makeRotationX(fila * 0.32));
    M.setPosition((Rc + 0.45) * MM * Math.cos(a), fila * 5.6 * MM, -(Rc + 0.45) * MM * Math.sin(a));
    im.setMatrixAt(k, M);
  }
  im.instanceMatrix.needsUpdate = true;
  im.castShadow = true;
  g.add(im);
  // Rin: aro con pestanas, alma del lado interior, 6 rayos y cubo.
  const amarillo = 0xf2c230;
  torno([[Ro - 9.5, -a2 + 1], [Ro - 5.2, -a2 + 1], [Ro - 5.2, -a2 + 2.2], [Ro - 6, -a2 + 2.6], [Ro - 6, a2 - 2.6],
    [Ro - 5.2, a2 - 2.2], [Ro - 5.2, a2 - 1], [Ro - 9.5, a2 - 1], [Ro - 9.5, -a2 + 1]], amarillo, { roughness: 0.45 });
  torno([[7, lado * 5 - 0.9], [Ro - 9.4, lado * 5 - 0.9], [Ro - 9.4, lado * 5 + 0.9], [7, lado * 5 + 0.9], [7, lado * 5 - 0.9]],
    0xe3b21f, { roughness: 0.5 });
  for (let k = 0; k < 6; k++) {
    const rayo = new THREE.Mesh(new THREE.BoxGeometry((Ro - 9.5 - 6) * MM, 3.2 * MM, 3.6 * MM), mat(amarillo, { roughness: 0.45 }));
    const a = k / 6 * Math.PI * 2;
    rayo.position.set(Math.cos(a) * (6 + (Ro - 15.5) / 2) * MM, -lado * 2 * MM, -Math.sin(a) * (6 + (Ro - 15.5) / 2) * MM);
    rayo.rotation.y = a;
    rayo.castShadow = true;
    g.add(rayo);
  }
  const cubo = new THREE.Mesh(new THREE.CylinderGeometry(7 * MM, 7 * MM, 20 * MM, 28), mat(amarillo, { roughness: 0.45 }));
  cubo.position.y = lado * 1 * MM;
  g.add(cubo);
  // Cara de afuera del cubo: agujero en D y tornillo autorroscante.
  const tapa = new THREE.Mesh(new THREE.CylinderGeometry(2.3 * MM, 2.3 * MM, 0.4 * MM, 16), mat(0x1a1a1a));
  tapa.position.y = -lado * 9.1 * MM;
  g.add(tapa);
  const tornillo = new THREE.Mesh(new THREE.CylinderGeometry(2.1 * MM, 2.1 * MM, 1.2 * MM, 16), mat(ACERO, METAL));
  tornillo.position.y = -lado * 9.6 * MM;
  g.add(tornillo);
  const cruz = new THREE.Mesh(new THREE.BoxGeometry(2.4 * MM, 0.3 * MM, 0.5 * MM), mat(0x2a2a2a));
  cruz.position.y = -lado * 10.25 * MM;
  g.add(cruz);
  if (ejeAdentro > 0) {
    // Eje en D blanco (nylon), del cubo hacia el reductor y el disco del encoder.
    const eje = new THREE.Mesh(new THREE.CylinderGeometry(2.7 * MM, 2.7 * MM, (a2 + ejeAdentro) * MM, 16), mat(0xf2f2f0, { roughness: 0.4 }));
    eje.position.y = lado * (a2 + ejeAdentro) / 2 * MM;
    eje.name = 'eje';
    g.add(eje);
  }
  return terminar(g, { datos: { idComponente } });
}

// ==================================================================
// Rueda loca de bola: bola de acero de 16 mm en su copa (O21 × 9 mm) con brida de 30 × 12 × 2
// mm y dos separadores M3 de laton hasta la placa. Origen: centro de la brida en la CARA DE
// ABAJO de la placa (la bola toca el piso en z = -alto).
// ==================================================================
export function crearRuedaLocaBola({ alto = 44, idComponente = 'rueda_loca' } = {}) {
  const g = new THREE.Group();
  g.name = 'rueda_loca';
  const zb = -alto + 8;
  const bola = new THREE.Mesh(new THREE.SphereGeometry(8 * MM, 28, 20), mat(0xdfe3e8, { metalness: 0.95, roughness: 0.12 }));
  bola.position.copy(P(0, 0, zb * MM));
  bola.name = 'bola';
  g.add(bola);
  const copa = new THREE.Mesh(new THREE.LatheGeometry([[8.3, -1.5], [10.5, 0.5], [10.5, 8], [9, 9], [0, 9]]
    .map(([rr, y]) => new THREE.Vector2(rr * MM, y * MM)), 40), mat(0xaeb3ba, { metalness: 0.85, roughness: 0.3, side: THREE.DoubleSide }));
  copa.position.copy(P(0, 0, (zb) * MM));
  g.add(copa);
  const brida = rect(-6, -15, 6, 15, 6);
  for (const y of [-11, 11]) brida.holes.push(circulo(0, y, 1.6));
  malla(g, extruir(brida, 2, 'xy', zb + 9), 0xaeb3ba, { metalness: 0.85, roughness: 0.3 });
  // Separadores de laton desde la brida hasta la placa, tornillos por debajo de la brida.
  for (const y of [-11, 11]) {
    const h = -(zb + 11);
    hexa(g, 5.5, h, 0, y, (zb + 11) + h / 2, LATON, 'z', { metalness: 0.8, roughness: 0.3 });
    cabeza(g, 0, y, zb + 9, { abajo: true, r: 2.6, h: 1.6 });
  }
  return terminar(g, { datos: { idComponente } });
}

// ==================================================================
// Rodillo guia: dos rodamientos 623 (O10 × 4 mm, O3) apilados con arandela, en un tornillo M3
// vertical, bajo un brazo impreso (4 mm) que sale del bloque atornillado bajo la placa. Lo que
// empujan las guias del muelle (y la cara trasera del bloque es lo que toca el tope con espuma).
// Origen: centro de los rodamientos (12 mm sobre el piso). `lado` = +1 si esta en +y.
// `subir` = mm hasta la cara de abajo de la placa; `adentro` = [y0, y1] mm del bloque hacia el
// centro; `atras` / `adelante` = mm del bloque desde el eje del rodillo.
// ==================================================================
export function crearRodilloGuia623({ lado = 1, subir = 32, adentro = [28, 40], atras = 8, adelante = 4,
  idComponente = 'rodillos_guia' } = {}) {
  const g = new THREE.Group();
  g.name = 'rodillo_guia';
  for (const z of [-2.5, 2.5]) {
    ci(g, 5, 4, 0, 0, z, 0xc9ccd1, 'z', METAL, 32);                       // aro exterior
    ci(g, 4.1, 4.08, 0, 0, z, 0x3a3f46, 'z', { metalness: 0.6, roughness: 0.35 }, 28);   // tapa (ZZ)
    ci(g, 2.1, 4.12, 0, 0, z, 0xd0d3d8, 'z', METAL, 20);                   // aro interior
  }
  ci(g, 3.2, 1, 0, 0, 0, ACERO, 'z', METAL, 20);                          // arandela entre los dos
  ci(g, 3.2, 1, 0, 0, 5, ACERO, 'z', METAL, 20);                          // arandela bajo el brazo
  ci(g, 1.5, 19, 0, 0, 3.5, ACERO, 'z', METAL, 12);                       // tornillo M3
  cabeza(g, 0, 0, -4.5, { abajo: true, r: 2.75, h: 2 });
  hexa(g, 5.5, 2.4, 0, 0, 9.5 + 1.2, ACERO);                               // tuerca sobre el brazo
  // Brazo: barra con punta redonda sobre el rodillo, hasta el bloque.
  const y1 = -lado * adentro[1];
  const brazo = new THREE.Shape();
  const ya = Math.min(0, y1), yb = Math.max(0, y1);
  brazo.moveTo(-6, ya); brazo.lineTo(6, ya); brazo.lineTo(6, yb); brazo.lineTo(-6, yb); brazo.lineTo(-6, ya);
  malla(g, extruir(brazo, 4, 'xy', 5.5), PLA, PLASTICO);
  ci(g, 6, 4, 0, 0, 7.5, PLA, 'z', PLASTICO, 28);
  // Bloque vertical hasta la placa, con la cara de atras al ras de la cola del chasis.
  const yc = -lado * (adentro[0] + adentro[1]) / 2;
  cj(g, atras + adelante, adentro[1] - adentro[0], subir - 5.5, (adelante - atras) / 2, yc, 5.5 + (subir - 5.5) / 2, PLA, PLASTICO);
  // Refuerzo triangular entre brazo y bloque.
  const tri = new THREE.Shape();
  tri.moveTo(0, 0); tri.lineTo(12, 0); tri.lineTo(0, 12); tri.lineTo(0, 0);
  const ref = malla(g, extruir(tri, 3, 'yz', -1.5), PLA, PLASTICO);
  // el triangulo esta en el plano y-z: y desde la cara del bloque hacia afuera
  ref.scale.z = lado;   // espejo en y (Three z = -y)
  ref.position.copy(P(0, -lado * adentro[0] * MM, 9.5 * MM));
  return terminar(g, { datos: { idComponente } });
}

// ==================================================================
// Soporte del encoder H206: columna impresa de 5 × 5 mm que baja de la placa y una repisa de
// 2 mm donde apoya y se atornilla el extremo del modulo (la horquilla queda bajo el disco).
// Origen: centro de la columna a la altura de la cara de abajo de la repisa. `alto` = mm hasta
// la placa; `lado` = hacia donde (en y) sale la repisa, bajo el modulo.
// ==================================================================
export function crearSoporteEncoder({ alto = 32, lado = 1, idComponente = 'encoders' } = {}) {
  const g = new THREE.Group();
  g.name = 'soporte_encoder';
  cj(g, 5, 5, alto, 0, 0, alto / 2, PLA, PLASTICO);
  cj(g, 9, 11, 2, 2, lado * 3, 1, PLA, PLASTICO);
  return terminar(g, { datos: { idComponente } });
}

// ==================================================================
// Escuadra frontal impresa (PETG negro, 3 mm): pie atornillado sobre la placa y cara vertical
// al ras del frente, con ventana para el header del VL53L0X, separadores de 2,5 mm (M2) para el
// HC-SR04 (agujeros de arriba) y el VL53L0X, y dos refuerzos. Origen: centro de la cara
// vertical en su borde de abajo (sobre la placa), la cara de adelante en x = 0.
// opciones (mm): alto, ancho, pie (largo del pie hacia atras), ventana [y0, y1, z0, z1],
// separadores [[y, z, largo]] (salen de la cara hacia +x).
// ==================================================================
export function crearEscuadraFrontal({ alto = 33, ancho = 50, pie = 16, ventana = null, separadores = [],
  idComponente = 'escuadra_frontal' } = {}) {
  const g = new THREE.Group();
  g.name = 'escuadra_frontal';
  const cara = rect(-ancho / 2, 0, ancho / 2, alto, 2);
  if (ventana) cara.holes.push(rect(ventana[0], ventana[2], ventana[1], ventana[3], 1, true));
  malla(g, extruir(cara, 3, 'yz', -3, { bisel: 0.3 }), 0x1c1f24, { roughness: 0.55 });
  malla(g, extruir(rect(-pie - 3, -12, -3, 12, 2), 2.5, 'xy', 0, { bisel: 0.3 }), 0x1c1f24, { roughness: 0.55 });
  for (const y of [-10, 10]) {
    const tri = new THREE.Shape();
    tri.moveTo(-3, 0); tri.lineTo(-pie + 1, 0); tri.lineTo(-3, alto * 0.45); tri.lineTo(-3, 0);
    malla(g, extruir(tri, 2, 'xz', y - 1), 0x1c1f24, { roughness: 0.55 });
  }
  for (const x of [-pie + 2, -8]) cabeza(g, x, 0, 2.5, { r: 2.6, h: 1.5 });
  for (const [y, z, l] of separadores) {
    hexa(g, 4, l, l / 2, y, z, LATON, 'x', { metalness: 0.8, roughness: 0.3 });
    ci(g, 1.9, 1.2, -3.6, y, z, ACERO, 'x', METAL, 14);   // cabeza del tornillo M2, por detras
  }
  return terminar(g, { datos: { idComponente } });
}

// ==================================================================
// Cuna del carro (punto 13): los mismos rieles de la canaleta forrados con cinta de PTFE, 3 mm
// mas bajos que su final y con entrada en embudo; postes traseros impresos (5 × 5 mm) con
// brazo y asiento bajo cada riel; mampara delantera impresa (3,5 mm) que recibe las puntas de
// los rieles y lleva las dos espumas (arriba y a media altura); dos guias laterales con PTFE a
// media altura del vaso (abiertas en embudo atras) sobre dos postes; lengueta trasera de
// trinquete con resorte de torsion y pasador de tope; y la columna del infrarrojo de la cuna.
// Origen: el del carro (piso bajo el centro del chasis), en metros; todas las cotas llegan en
// metros desde disposicionCarro / la geometria de la simulacion.
// Nodo: `lengueta` (Group en el pivote; el visor la anima con rotation.y).
// ==================================================================
export function crearCunaCarro(o) {
  const { xCola, zBase, zRiel, sepR, sepE, dRiel, xEmb, xMampara, zMedio, rCuerpo, irCol } = o;
  const g = new THREE.Group();
  g.name = 'cuna';
  const V = (x, y, z) => P(x, y, z);
  const ptfe = () => mat(PTFE, { roughness: 0.35 });
  const pla = () => mat(PLA, PLASTICO);
  const mampara = xMampara + 0.0035;
  const rR = dRiel / 2;
  for (const lado of [-1, 1]) {
    // Rieles: boca del embudo -> recta -> dentro de la mampara.
    const e = V(xCola, lado * sepE, zRiel), m = V(xEmb, lado * sepR, zRiel), b = V(xMampara + 0.002, lado * sepR, zRiel);
    varilla(g, e, m, rR, ptfe());
    varilla(g, m, b, rR, ptfe());
    const punta = new THREE.Mesh(new THREE.SphereGeometry(rR, 14, 10), ptfe());
    punta.position.copy(e);
    g.add(punta);
    // Poste trasero con brazo y asiento bajo el riel.
    const xp = xCola + 0.012, yp = lado * (sepE + 0.01);
    const yRielP = lado * (sepE - (sepE - sepR) * ((xp - xCola) / (xEmb - xCola)));
    g.add(caja(0.005, 0.005, zRiel - zBase - 0.004, pla(), V(xp, yp, (zRiel - 0.004 + zBase) / 2)));
    g.add(caja(0.012, 0.012, 0.002, pla(), V(xp, yp, zBase + 0.001)));
    g.add(caja(0.005, Math.abs(yp - yRielP) + 0.003, 0.004, pla(), V(xp, (yp + yRielP) / 2, zRiel - rR - 0.002 - 0.002)));
    const asiento = caja(0.006, 0.006, 0.003, pla(), V(xp, yRielP, zRiel - rR - 0.0015 + 0.0005));
    g.add(asiento);
    // Guias laterales a media altura: cara con PTFE, boca en embudo, dos postes.
    const yG = lado * (rCuerpo + 0.0025);
    const xIni = xCola + 0.03, xFin = 0.004;
    g.add(caja(xFin - xIni, 0.003, 0.014, pla(), V((xIni + xFin) / 2, yG + lado * 0.0015, zMedio)));
    g.add(caja(xFin - xIni, 0.0005, 0.012, ptfe(), V((xIni + xFin) / 2, yG - lado * 0.00025, zMedio)));
    varilla(g, V(xIni, yG + lado * 0.0015, zMedio), V(xCola + 0.008, lado * (rCuerpo + 0.012), zMedio), 0.0016, ptfe());
    for (const xx of [xIni + 0.01, xFin - 0.01]) {
      g.add(caja(0.004, 0.004, zMedio - 0.007 - zBase, pla(), V(xx, lado * (rCuerpo + 0.004), (zMedio - 0.007 + zBase) / 2)));
      g.add(caja(0.009, 0.009, 0.0015, pla(), V(xx, lado * (rCuerpo + 0.004), zBase + 0.00075)));
    }
  }
  // Mampara delantera (con ventana para pasar cables) y su pie con dos tornillos.
  const alto = zRiel + 0.006 - zBase;
  // Marco (no una placa llena): dos largueros y tres travesanos, abajo, a media altura (la
  // espuma de abajo) y arriba (las puntas de los rieles y la espuma de arriba).
  const cara = rect(-40, 0, 40, alto / MM, 3);
  const zm = (zMedio - zBase) / MM, zt = (zRiel - 0.024 - zBase) / MM;
  cara.holes.push(rect(-31, 7, 31, zm - 12, 3, true));
  cara.holes.push(rect(-31, zm + 12, 31, zt, 3, true));
  for (const s of [-1, 1]) cara.holes.push(circulo(s * sepR / MM, (zRiel - zBase) / MM, rR / MM + 0.2));
  const mm = malla(g, extruir(cara, 3.5, 'yz', xMampara / MM, { bisel: 0.3 }), pla());
  mm.position.y = zBase;   // Three y = z de la simulacion
  g.add(caja(xMampara - 0.007, 0.08, 0.0025, pla(), V((xMampara + 0.007) / 2, 0, zBase + 0.00125)));
  for (const s of [-1, 1]) cabeza(g, (xMampara + 0.007) / 2 / MM, s * 30, (zBase + 0.0025) / MM, { r: 2.4, h: 1.4 });
  // Espumas: arriba (bajo el reborde del vaso) y a media altura.
  const esp = (x0, sy, z0, z1) => {
    const m = caja(xMampara - x0, sy, z1 - z0, ESPUMA, V((x0 + xMampara) / 2, 0, (z0 + z1) / 2), { roughness: 1 });
    g.add(m);
  };
  esp(0.007, sepR * 2 - 0.008, zRiel - 0.022, zRiel - 0.004);
  esp(0.0048, 0.04, zMedio - 0.01, zMedio + 0.01);
  // Lengueta trasera (trinquete pasivo, lado -y): brazo rojo, resorte de torsion, eje, soporte
  // al poste trasero y pasador de tope.
  const zL = zRiel - 0.035;
  const pivL = V(xCola + 0.016, -(sepE + 0.009), zL);
  const lengueta = new THREE.Group();
  lengueta.name = 'lengueta';
  lengueta.position.copy(pivL);
  varilla(lengueta, new THREE.Vector3(0, 0, 0), V(0.016, 0.026, 0), 0.0025, 0xd9261a);
  const puntaL = new THREE.Mesh(new THREE.SphereGeometry(0.0025, 12, 8), mat(0xd9261a));
  puntaL.position.copy(V(0.016, 0.026, 0));
  lengueta.add(puntaL);
  g.add(lengueta);
  const resorte = new THREE.Mesh(new THREE.TorusGeometry(0.0045, 0.0009, 6, 20), mat(0xb8bcc2, METAL));
  resorte.rotation.x = Math.PI / 2;
  resorte.position.copy(pivL).add(new THREE.Vector3(0, -0.003, 0));
  g.add(resorte);
  varilla(g, pivL.clone().add(new THREE.Vector3(0, -0.012, 0)), pivL.clone().add(new THREE.Vector3(0, 0.006, 0)), 0.0015, ACERO, METAL);
  g.add(caja(0.006, 0.006, 0.003, pla(), pivL.clone().add(new THREE.Vector3(0, -0.0135, 0))));
  varilla(g, V(xCola + 0.016, -(sepE + 0.009), zL - 0.0135), V(xCola + 0.012, -(sepE + 0.01), zL - 0.0135), 0.0022, pla());
  varilla(g, V(xCola + 0.035, -(sepE + 0.009) + 0.022, zL - 0.006), V(xCola + 0.035, -(sepE + 0.009) + 0.022, zL + 0.006), 0.0015, ACERO, METAL);
  varilla(g, V(xCola + 0.035, -(sepE + 0.009) + 0.022, zL - 0.006), V(xCola + 0.012, -(sepE + 0.01), zL - 0.006), 0.0015, pla());
  // Columna del infrarrojo de la cuna, con su separador hasta el modulo.
  if (irCol) {
    const { x, y, z, yModulo } = irCol;
    g.add(caja(0.006, 0.006, z + 0.006 - zBase, pla(), V(x, y, (z + 0.006 + zBase) / 2)));
    g.add(caja(0.012, 0.012, 0.002, pla(), V(x, y, zBase + 0.001)));
    const largo = Math.abs(y - yModulo) - 0.003;
    const s = new THREE.Mesh(new THREE.CylinderGeometry(2.6 * MM, 2.6 * MM, largo, 6), mat(LATON, { metalness: 0.8, roughness: 0.3 }));
    s.rotation.x = Math.PI / 2;
    s.position.copy(V(x, (yModulo + (y - Math.sign(y - yModulo) * 0.003)) / 2, z));
    g.add(s);
  }
  return terminar(g, { datos: { idComponente: 'cuna_carro' } });
}

// ==================================================================
// Muelle de carga (punto 13): dos guias impresas en V atornilladas al piso (perfil de 6 mm de
// pared × 20 mm de alto con chaflan arriba y pie de 10 mm hacia afuera), cara interna con cinta
// de PTFE, tramo recto desde la cola y boca abierta `abre` m en `x2 - x1`; puntas redondeadas;
// y dos topes impresos con refuerzo y espuma de 6 mm que paran el carro por los bloques de sus
// rodillos. Mismas medidas que sim/vehiculo_sim.py (_crear_muelle) y sim/geometria.py
// (zonas_carro). Origen: el del carro estacionado (piso, +x hacia adelante del carro), metros.
// ==================================================================
export function crearMuelleCarga({ x0, x1, x2, guiaY, abre = 0.045, alto = 0.02, esp = 0.006,
  topes = [], idComponente = 'muelle_carga' } = {}) {
  const g = new THREE.Group();
  g.name = 'muelle';
  const A = alto / MM, E = esp / MM;
  // Perfil (y hacia afuera, z): pared con chaflan interior arriba + pie hacia afuera.
  const perfil = new THREE.Shape();
  perfil.moveTo(0, 0); perfil.lineTo(E + 10, 0); perfil.lineTo(E + 10, 3); perfil.lineTo(E, 3);
  perfil.lineTo(E, A - 1); perfil.lineTo(E - 1, A); perfil.lineTo(1.5, A); perfil.lineTo(0, A - 1.5); perfil.lineTo(0, 0);
  const tramo = (lado, a, b) => {
    // Tramo de guia de a a b (puntos x, y de la cara interior, metros).
    const t = new THREE.Group();
    const largo = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const cuerpo = new THREE.Group();
    const m = malla(cuerpo, extruir(perfil, largo / MM, 'yz', 0), PLA, PLASTICO);
    if (lado < 0) { m.scale.z = -1; }   // espejo: el pie hacia -y
    // Cinta de PTFE en la cara interior.
    cuerpo.add(caja(largo, 0.0005, alto - 0.006, mat(PTFE, { roughness: 0.35 }), P(largo / 2, -lado * 0.00025, 0.004 + (alto - 0.006) / 2)));
    // Tornillos del pie cada ~40 mm.
    const n = Math.max(1, Math.round(largo / 0.04));
    for (let k = 0; k < n; k++) {
      const xx = (k + 0.5) / n * largo / MM;
      cabeza(cuerpo, xx, lado * (E + 5), 3, { r: 2.6, h: 0.8 });
    }
    t.add(cuerpo);
    t.position.copy(P(a[0], a[1], 0));
    t.rotation.y = Math.atan2(b[1] - a[1], b[0] - a[0]);
    g.add(t);
    return t;
  };
  for (const lado of [-1, 1]) {
    const yi = lado * guiaY;
    tramo(lado, [x0, yi], [x1, yi]);
    tramo(lado, [x1, yi], [x2, lado * (guiaY + abre)]);
    // Punta redondeada de la boca y de la cola.
    for (const [x, y] of [[x2, lado * (guiaY + abre)], [x0, yi]]) {
      const c = cilindro(esp / 2, alto - 0.0015, PLA, P(x, y + lado * esp / 2, (alto - 0.0015) / 2), PLASTICO, 20);
      g.add(c);
    }
  }
  // Topes: bloque impreso, refuerzo triangular detras y espuma al frente.
  for (const t of topes) {
    const { x0: tx0, x1: tx1, y, ancho, altoTope, espuma } = t;
    g.add(caja(tx1 - tx0, ancho, altoTope, PLA, P((tx0 + tx1) / 2, y, altoTope / 2), PLASTICO));
    g.add(caja(0.028, ancho + 0.012, 0.003, PLA, P(tx0 - 0.004, y, 0.0015), PLASTICO));
    const tri = new THREE.Shape();
    tri.moveTo(0, 0); tri.lineTo(-16, 0); tri.lineTo(0, altoTope / MM * 0.7); tri.lineTo(0, 0);
    malla(g, extruir(tri, 3, 'xz', y / MM - 1.5), PLA, PLASTICO).position.x = tx0;
    for (const s of [-1, 1]) cabeza(g, (tx0 - 0.012) / MM, y / MM + s * (ancho / MM / 2 + 2), 3, { r: 2.6, h: 0.8 });
    g.add(caja(espuma, ancho, altoTope - 0.012, ESPUMA, P(tx1 + espuma / 2, y, 0.006 + (altoTope - 0.012) / 2), { roughness: 1 }));
  }
  return terminar(g, { datos: { idComponente } });
}
