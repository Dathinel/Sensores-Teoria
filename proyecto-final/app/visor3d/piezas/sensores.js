// Piezas de los SENSORES del catalogo (sim/catalogos.py, CATALOGO_SENSORES),
// modeladas con medidas de ficha tecnica, para el visor 3D (Three.js).
//
// Convencion (igual que el resto de app/visor3d/piezas/):
// - Cada funcion `crear<Pieza>(opciones)` devuelve un THREE.Group en METROS.
// - Modulos en placa (FC-51, KY-003, GY-VL53L0XV2, HC-SR04, TCRT5000, H206):
//   el sistema local es el MISMO de `construirModulo` en visor.js: la placa
//   queda en el plano x-y "de la ficha" (x a lo largo, y a lo ancho), con su
//   cara de abajo en z = 0 y el origen en el centro de la placa. En Three eso
//   es (x, z, -y) -> la placa acostada, con su cara de arriba hacia +Y. Asi
//   se reemplaza `construirModulo(dev, padre, pos, quat)` por
//   `crearX({ id: dev })` con la misma pos/quat.
// - Sensores cilindricos M18: origen en la CARA activa, mirando hacia +Y
//   (igual que `sensorCilindrico` de visor.js); el cuerpo queda hacia -Y.
// - Webcam: origen en el centro de la carcasa, mirando hacia -Y (camara
//   cenital sin rotar).
// - Cada pin es un Object3D vacio `pin_<dispositivo>_<PIN>` (los nombres de
//   sim/conexiones.py: `presencia.OUT` -> `pin_presencia_OUT`) en la PUNTA
//   del pin, con `userData.dir` = hacia donde sale el cable (local).
// - Lo que se mueve o se enciende tiene nombre: `disco_encoder`,
//   `led_estado`, `led_ir_0..4`, `anillo_luz`, `optica`.
// - `userData.sensorId` en todas las mallas (resaltado y clic del visor).
// - `userData.mira` (Vector3 local): hacia donde "mira" el sensor.
import * as THREE from 'three';

import { MM, mat as matBase, ancla as anclaBase } from './base.js';

// Coordenadas "de ficha" (mm, z hacia arriba de la placa) -> Three (m, Y arriba).
const P = (x, y, z) => new THREE.Vector3(x * MM, z * MM, -y * MM);
const D = (x, y, z) => new THREE.Vector3(x, z, -y).normalize();

// ---------------------------------------------------------------- materiales
// Uno NUEVO por llamada (como base.js): el resaltado del visor cambia el
// `emissive` de cada malla, y un material compartido encenderia tambien el
// sensor vecino (hay tres VL53L0X iguales).
function mat(color, extra = {}) {
  const { basico, ...resto } = extra;
  return basico ? new THREE.MeshBasicMaterial({ color, ...resto }) : matBase(color, { metalness: 0.05, ...resto });
}
const METAL = { metalness: 0.9, roughness: 0.3 };
const ORO = (c = 0xd4af37) => mat(c, { metalness: 0.95, roughness: 0.25 });
const EST = () => mat(0xc9ccd1, METAL);   // estano / niquel
const PLASTICO_NEGRO = () => mat(0x151515, { roughness: 0.55 });

// Caja de w x d x h mm centrada en (x, y, z) de ficha.
function caja(g, w, d, h, x, y, z, material) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w * MM, h * MM, d * MM), material);
  m.position.copy(P(x, y, z));
  g.add(m);
  return m;
}
// Cilindro de radio r y alto h mm, eje a lo largo de `eje` de ficha ('x'|'y'|'z').
function cil(g, r, h, x, y, z, material, eje = 'z', seg = 24, r2 = null) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry((r2 ?? r) * MM, r * MM, h * MM, seg), material);
  m.position.copy(P(x, y, z));
  if (eje === 'x') m.rotation.z = -Math.PI / 2;
  else if (eje === 'y') m.rotation.x = Math.PI / 2;
  g.add(m);
  return m;
}
function ancla(g, nombre, pos, dir = null) {
  const o = anclaBase(nombre, pos, dir ? { dir } : {});
  g.add(o);
  return o;
}

// Texto serigrafiado (blanco sobre transparente) acostado sobre la placa.
function serigrafia(g, texto, x, y, z, ancho, alto, { color = '#f2f2f2', giro = 0 } = {}) {
  const c = document.createElement('canvas');
  const esc = 12;
  c.width = Math.max(32, Math.round(ancho * esc * 4)); c.height = Math.max(16, Math.round(alto * esc * 4));
  const x2 = c.getContext('2d');
  x2.fillStyle = color;
  x2.font = `600 ${Math.round(c.height * 0.72)}px "IBM Plex Mono", monospace`;
  x2.textAlign = 'center'; x2.textBaseline = 'middle';
  x2.fillText(texto, c.width / 2, c.height / 2, c.width * 0.96);
  const tex = new THREE.CanvasTexture(c);
  tex.anisotropy = 4;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(ancho * MM, alto * MM),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2;
  m.rotation.z = giro;
  m.position.copy(P(x, y, z + 0.03));
  m.renderOrder = 2;
  g.add(m);
  return m;
}

// PCB con agujeros de montaje (anillos de estano) y mascara de color.
function pcb(g, L, W, T, color, agujeros = []) {
  const forma = new THREE.Shape();
  const r = 0.6;
  forma.moveTo(-L / 2 + r, -W / 2);
  forma.lineTo(L / 2 - r, -W / 2); forma.quadraticCurveTo(L / 2, -W / 2, L / 2, -W / 2 + r);
  forma.lineTo(L / 2, W / 2 - r); forma.quadraticCurveTo(L / 2, W / 2, L / 2 - r, W / 2);
  forma.lineTo(-L / 2 + r, W / 2); forma.quadraticCurveTo(-L / 2, W / 2, -L / 2, W / 2 - r);
  forma.lineTo(-L / 2, -W / 2 + r); forma.quadraticCurveTo(-L / 2, -W / 2, -L / 2 + r, -W / 2);
  for (const [x, y, d] of agujeros) {
    const h = new THREE.Path();
    h.absarc(x, y, d / 2, 0, Math.PI * 2, true);
    forma.holes.push(h);
  }
  const geo = new THREE.ExtrudeGeometry(forma, { depth: T, bevelEnabled: false, curveSegments: 16 });
  geo.scale(MM, MM, MM);
  geo.rotateX(-Math.PI / 2);   // (x, y, z) de ficha -> (x, z, -y)
  const m = new THREE.Mesh(geo, mat(color, { roughness: 0.65 }));
  m.name = 'pcb';
  g.add(m);
  for (const [x, y, d] of agujeros) {
    const anillo = new THREE.Mesh(new THREE.RingGeometry(d / 2 * MM, (d / 2 + 0.7) * MM, 20), EST());
    anillo.rotation.x = -Math.PI / 2;
    anillo.position.copy(P(x, y, T + 0.02));
    g.add(anillo);
  }
  return m;
}

// Header de pines 2,54 mm.
// tipo 'recto': vertical, sale por arriba (lado=+1) o por abajo (lado=-1).
// tipo 'acodado': a 90 grados, acostado sobre la cara de arriba, las puntas
//   salen en el plano de la placa hacia `sale` ([1,0] = +x, [0,-1] = -y).
function header(g, id, pines, T, { tipo = 'recto', lado = 1, sale = [1, 0] } = {}) {
  const plast = PLASTICO_NEGRO();
  const oro = ORO();
  for (const p of pines) {
    if (tipo === 'recto') {
      const z0 = lado > 0 ? T : 0;
      caja(g, 2.54, 2.54, 2.5, p.x, p.y, z0 + lado * 1.25, plast);
      caja(g, 0.64, 0.64, 11.6, p.x, p.y, z0 + lado * 2.8, oro);   // de -3 (soldadura) a +8,5
      ancla(g, `pin_${id}_${p.n}`, P(p.x, p.y, z0 + lado * 8.6), D(0, 0, lado));
    } else {
      const [sx, sy] = sale;
      const zc = T + 1.27;
      // cuerpo de plastico acostado junto al agujero, hacia afuera
      caja(g, sx ? 2.5 : 2.54, sy ? 2.5 : 2.54, 2.54, p.x + sx * 1.9, p.y + sy * 1.9, zc, plast);
      caja(g, 0.64, 0.64, zc + 2.2, p.x, p.y, (zc - 2.2) / 2 - 0.3, oro);      // pata vertical a la placa
      const largo = 9.2;
      caja(g, sx ? largo : 0.64, sy ? largo : 0.64, 0.64, p.x + sx * largo / 2, p.y + sy * largo / 2, zc, oro);
      ancla(g, `pin_${id}_${p.n}`, P(p.x + sx * largo, p.y + sy * largo, zc), D(sx, sy, 0));
    }
    // pad de soldadura del otro lado
    const pad = new THREE.Mesh(new THREE.CircleGeometry(0.85 * MM, 12), EST());
    pad.rotation.x = Math.PI / 2;
    pad.position.copy(P(p.x, p.y, -0.02));
    g.add(pad);
  }
}
const fila = (nombres, x0, y0, eje = 'y', paso = 2.54) =>
  nombres.map((n, i) => ({ n, x: eje === 'x' ? x0 + i * paso : x0, y: eje === 'y' ? y0 + i * paso : y0 }));

// Componentes SMD / THT sueltos.
function smd(g, x, y, z, w, d, color = 0x2a2a2a, h = 0.5) {
  caja(g, w, d, h, x, y, z + h / 2, mat(color));
  // terminales de estano en los extremos del largo
  caja(g, 0.35, d * 1.02, h * 1.02, x - w / 2 + 0.17, y, z + h / 2, EST());
  caja(g, 0.35, d * 1.02, h * 1.02, x + w / 2 - 0.17, y, z + h / 2, EST());
}
function soic(g, x, y, z, n, { giro = false, nombre = null } = {}) {
  const largo = n === 14 ? 8.65 : 4.9, ancho = 3.9;
  const [w, d] = giro ? [ancho, largo] : [largo, ancho];
  const cuerpo = caja(g, w, d, 1.5, x, y, z + 0.9, mat(0x1b1b1b, { roughness: 0.4 }));
  if (nombre) cuerpo.name = nombre;
  const porLado = n / 2;
  for (let i = 0; i < porLado; i++) {
    const t = -largo / 2 + largo / porLado * (i + 0.5);
    for (const s of [-1, 1]) {
      if (giro) caja(g, 1.0, 0.4, 0.25, x + s * (ancho / 2 + 0.4), y + t, z + 0.15, EST());
      else caja(g, 0.4, 1.0, 0.25, x + t, y + s * (ancho / 2 + 0.4), z + 0.15, EST());
    }
  }
}
function ledSmd(g, x, y, z, color, nombre) {
  caja(g, 2.0, 1.25, 0.3, x, y, z + 0.15, mat(0xeeeeee));
  const lente = caja(g, 1.4, 1.1, 0.5, x, y, z + 0.55, mat(0x30363d, { roughness: 0.2 }));
  lente.userData.colorEncendido = color;
  if (nombre) lente.name = nombre;
  return lente;
}
// Trimmer azul (3362P / RM065): cuerpo 6,6 x 6,6 x 4,5 mm con rotor ranurado.
function trimmer(g, x, y, z, nombre = 'potenciometro') {
  caja(g, 6.6, 6.6, 4.5, x, y, z + 2.25, mat(0x2358c4, { roughness: 0.45 }));
  const rotor = cil(g, 2.2, 1.0, x, y, z + 5.0, mat(0xf2f2f2, { roughness: 0.4 }), 'z', 20);
  rotor.name = nombre;
  caja(g, 3.6, 0.5, 0.4, x, y, z + 5.35, mat(0x9aa0a6));
  caja(g, 0.5, 3.6, 0.4, x, y, z + 5.35, mat(0x9aa0a6));
}
// LED THT de 3 mm (cuerpo + cupula), de pie sobre (x, y, z) apuntando a +z*lado.
function led3mm(g, x, y, z, color, { lado = 1, opacidad = 0.9, alto = 5.3 } = {}) {
  const m = mat(color, { roughness: 0.15, transparent: opacidad < 1, opacity: opacidad });
  cil(g, 1.75, 1.0, x, y, z + lado * 0.5, m, 'z', 20);            // pestana
  cil(g, 1.5, alto - 1.5, x, y, z + lado * (1 + (alto - 1.5) / 2), m, 'z', 20);
  const cup = new THREE.Mesh(new THREE.SphereGeometry(1.5 * MM, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), m);
  cup.position.copy(P(x, y, z + lado * (alto - 0.5)));
  if (lado < 0) cup.rotation.x = Math.PI;
  g.add(cup);
}

// TCRT5000: 10,2 x 5,8 x 7 mm; emisor (azul translucido) y detector (negro).
// Cara optica hacia -z (debajo de la placa), largo a lo largo de `eje`.
function tcrt5000(g, x, y, zPlaca, eje = 'x') {
  const gx = eje === 'x';
  const [w, d] = gx ? [10.2, 5.8] : [5.8, 10.2];
  caja(g, w, d, 7.0, x, y, zPlaca - 3.5, mat(0x111111, { roughness: 0.5 }));
  for (const [s, color, op] of [[-1, 0x3b6fd8, 0.8], [1, 0x0a0a0a, 1]]) {
    const cx = gx ? x + s * 2.55 : x, cy = gx ? y : y + s * 2.55;
    const m = mat(color, { roughness: 0.1, transparent: op < 1, opacity: op });
    cil(g, 1.5, 0.8, cx, cy, zPlaca - 7.4, m, 'z', 18);
    const cup = new THREE.Mesh(new THREE.SphereGeometry(1.5 * MM, 14, 7, 0, Math.PI * 2, 0, Math.PI / 2), m);
    cup.rotation.x = Math.PI;
    cup.position.copy(P(cx, cy, zPlaca - 7.8));
    g.add(cup);
  }
  // patas a la placa (4)
  for (const s of [-1, 1]) for (const t of [-1, 1])
    caja(g, 0.5, 0.5, 1.2, x + (gx ? s * 3.8 : t * 1.3), y + (gx ? t * 1.3 : s * 3.8), zPlaca - 0.6, EST());
}

function marcar(g, sensorId, id, mira, extra = {}) {
  g.traverse((o) => { if (o.isMesh) { o.castShadow = false; if (sensorId) o.userData.sensorId = sensorId; } });
  Object.assign(g.userData, { sensorId, dispositivo: id, mira, ...extra });
  g.name = id;
  return g;
}

// ==================================================================
// 1 · FC-51 (infrarrojo reflectivo, LM393). Placa 32 x 14 x 1,6 mm (ficha
// del vendedor: 3,1-3,2 x 1,4 cm), agujero M3 al centro. Todo del mismo
// lado: LED IR (transparente) y fototransistor (negro) de 3 mm de pie en la
// punta -x, trimmer azul, LM393 (SOIC-8), LED de alimentacion y de
// obstaculo, header acodado de 3 pines (OUT, GND, VCC) saliendo por +x.
// Mira hacia +Z de ficha (arriba de la placa): el visor lo monta boca abajo.
// ==================================================================
export function crearFC51({ id = 'presencia', sensorId = 'presencia' } = {}) {
  const g = new THREE.Group();
  const T = 1.6;
  pcb(g, 32, 14, T, 0x1d4f9c, [[1.5, 0, 3.0]]);
  led3mm(g, -13, 3, T, 0xd8e6ff, { opacidad: 0.55 });   // emisor IR
  led3mm(g, -13, -3, T, 0x0c0c0c, { opacidad: 1 });     // receptor
  ancla(g, 'optica', P(-13, 0, T + 5.3), D(0, 0, 1));
  trimmer(g, -5.5, 0, T);
  soic(g, 7.5, 3.4, T, 8, { giro: true, nombre: 'LM393' });
  smd(g, 7.5, -3.5, T, 2.0, 1.25, 0x3a2a1a);
  smd(g, 10.3, -3.5, T, 2.0, 1.25, 0x3a2a1a);
  const ledPwr = ledSmd(g, 4.0, -5.2, T, 0xff3030, 'led_alimentacion');
  const ledObs = ledSmd(g, 10.0, 5.5, T, 0x30ff60, 'led_estado');
  header(g, id, fila(['OUT', 'GND', 'VCC'], 14.0, -2.54), T, { tipo: 'acodado', sale: [1, 0] });
  serigrafia(g, 'FC-51', 1.5, -5.2, T, 7, 2.2);
  serigrafia(g, 'OUT GND VCC', 11.2, 0, T, 7.6, 1.4, { giro: Math.PI / 2 });
  marcar(g, sensorId, id, D(0, 0, 1), { led: ledObs, ledAlimentacion: ledPwr, medidas: [32, 14, 1.6] });
  return g;
}

// ==================================================================
// 2-3 · Sensores de proximidad cilindricos M18 x 1 (NPN, 3 hilos).
// Origen = cara activa, mirando a +Y. Rosca M18 x 1 continua (un solo
// torno), dos tuercas de 24 mm entre caras x 4 mm con arandela dentada,
// cola de plastico con LED de estado, prensacable y cable de 4 mm que se
// abre en los tres hilos (CAFE +V, AZUL 0 V, NEGRO salida).
// ==================================================================
function crearM18({ id, sensorId, largoRosca, largoCabeza, colorCara, largoCola, tornilloSens, cable = 45,
                    tuercas = [12, 30], nombre }) {
  const g = new THREE.Group();
  const R = 9.0, Rn = 8.35;   // radio exterior y de fondo de la rosca M18 x 1
  // Cabeza de plastico (no enrasable: sobresale de la rosca).
  cil(g, 8.6, largoCabeza, 0, 0, 0, mat(colorCara, { roughness: 0.45 }), 'z').position.copy(P(0, 0, 0)).setY(-largoCabeza / 2 * MM);
  // Rosca como torno de un diente de sierra (paso 1 mm).
  const perfil = [new THREE.Vector2(0, 0), new THREE.Vector2(Rn * MM, 0)];
  for (let t = 0; t < largoRosca; t += 1) {
    perfil.push(new THREE.Vector2(R * MM, -(t + 0.45) * MM), new THREE.Vector2(Rn * MM, -(t + 1) * MM));
  }
  perfil.push(new THREE.Vector2(0, -largoRosca * MM));
  perfil.reverse();   // de abajo hacia arriba: normales hacia afuera
  const rosca = new THREE.Mesh(new THREE.LatheGeometry(perfil, 40), mat(0xc7ccd3, { metalness: 0.85, roughness: 0.32 }));
  rosca.position.y = -largoCabeza * MM;
  rosca.name = 'rosca';
  g.add(rosca);
  const y0 = largoCabeza;   // la rosca empieza aqui (medido hacia -Y)
  // Tuercas M18: hexagono de 24 mm entre caras (26,6 mm entre vertices), 4 mm.
  tuercas.forEach((d, i) => {
    const tu = new THREE.Mesh(new THREE.CylinderGeometry(13.3 * MM, 13.3 * MM, 4 * MM, 6), mat(0xd3d7dc, { metalness: 0.9, roughness: 0.28 }));
    tu.position.y = -(y0 + d) * MM;
    tu.name = `tuerca_${i}`;
    g.add(tu);
    const ar = new THREE.Mesh(new THREE.CylinderGeometry(12 * MM, 12 * MM, 0.8 * MM, 24), mat(0xb3b8be, METAL));
    ar.position.y = -(y0 + d + (i === 0 ? -2.4 : 2.4)) * MM;
    g.add(ar);
  });
  // Cola de plastico con el anillo de LED.
  const yc = y0 + largoRosca;
  const cola = new THREE.Mesh(new THREE.CylinderGeometry(8.4 * MM, 8.4 * MM, largoCola * MM, 32), mat(0x24272c));
  cola.position.y = -(yc + largoCola / 2) * MM;
  g.add(cola);
  const led = new THREE.Mesh(new THREE.CylinderGeometry(8.55 * MM, 8.55 * MM, 2.2 * MM, 32), mat(0x4a1a1a, { transparent: true, opacity: 0.85, roughness: 0.2 }));
  led.position.y = -(yc + 2.5) * MM;
  led.name = 'led_estado';
  g.add(led);
  if (tornilloSens) {   // potenciometro de sensibilidad en la tapa trasera (solo el capacitivo)
    const t = new THREE.Mesh(new THREE.CylinderGeometry(1.6 * MM, 1.6 * MM, 1 * MM, 16), mat(0xd4af37, METAL));
    t.position.set(4.5 * MM, -(yc + largoCola + 0.3) * MM, 0);
    g.add(t);
  }
  // Prensacable y cable de PVC gris 4 mm.
  const yp = yc + largoCola;
  const pc = new THREE.Mesh(new THREE.CylinderGeometry(3.4 * MM, 4.2 * MM, 6 * MM, 20), mat(0x1c1c1c));
  pc.position.y = -(yp + 3) * MM;
  g.add(pc);
  const cab = new THREE.Mesh(new THREE.CylinderGeometry(2 * MM, 2 * MM, cable * MM, 16), mat(0x6f747a, { roughness: 0.7 }));
  cab.position.y = -(yp + 6 + cable / 2) * MM;
  g.add(cab);
  // Tres hilos que se abren (1 mm de diametro, 14 mm) con la punta pelada.
  const yf = yp + 6 + cable;
  [['CAFE', 0x6b3e1e, -2.4], ['AZUL', 0x1f5fbf, 0], ['NEGRO', 0x101010, 2.4]].forEach(([n, color, dx]) => {
    const a = new THREE.Vector3(0, -yf * MM, 0), b = new THREE.Vector3(dx * MM, -(yf + 14) * MM, 0);
    const h = new THREE.Mesh(new THREE.CylinderGeometry(0.55 * MM, 0.55 * MM, a.distanceTo(b), 10), mat(color));
    h.position.copy(a).add(b).multiplyScalar(0.5);
    h.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
    g.add(h);
    const punta = new THREE.Mesh(new THREE.CylinderGeometry(0.4 * MM, 0.4 * MM, 3 * MM, 8), mat(0xc87533, METAL));
    punta.position.copy(b).add(new THREE.Vector3(0, -1.5 * MM, 0));
    g.add(punta);
    ancla(g, `pin_${id}_${n}`, b.clone().add(new THREE.Vector3(0, -3 * MM, 0)), new THREE.Vector3(0, -1, 0));
  });
  ancla(g, 'ancla_salida_cable', new THREE.Vector3(0, -yp * MM, 0), new THREE.Vector3(0, -1, 0));
  marcar(g, sensorId, id, new THREE.Vector3(0, 1, 0),
    { led, salidaCable: new THREE.Vector3(0, -yp * MM, 0), largo: (largoCabeza + largoRosca + largoCola) * MM, nombre });
  return g;
}
// LJC18A3-H-Z/BX: M18, largo total 68 mm (cabeza azul 6 + rosca 50 + cola 12),
// alcance 1-10 mm ajustable con el tornillo trasero.
export function crearCapacitivoLJC18A3({ id = 'capacitivo', sensorId = 'capacitivo', tuercas = [10.5, 30], cable = 45 } = {}) {
  return crearM18({ id, sensorId, largoCabeza: 6, largoRosca: 50, largoCola: 12, colorCara: 0x2f6fd0,
    tornilloSens: true, tuercas, cable, nombre: 'LJC18A3-H-Z/BX' });
}
// LJ18A3-8-Z/BX: M18, largo total 60 mm (cabeza naranja 8 + rosca 42 + cola 10),
// 8 mm de alcance nominal en acero (no enrasable).
export function crearInductivoLJ18A3({ id = 'inductivo', sensorId = 'inductivo', tuercas = [10.5, 26], cable = 45 } = {}) {
  return crearM18({ id, sensorId, largoCabeza: 8, largoRosca: 42, largoCola: 10, colorCara: 0xe07b24,
    tornilloSens: false, tuercas, cable, nombre: 'LJ18A3-8-Z/BX' });
}

// ==================================================================
// 4 / 7 · Webcam USB (modulo 1080p o 720p de 38 x 38 mm con lente M12, en
// carcasa de aluminio 42 x 42 x 20 mm). Mira hacia -Y. Anillo de luz LED
// difusa opcional (60 mm exterior, 40 mm interior, 5 V) sostenido por 3
// separadores, soporte en L con rotula y cable USB con prensacable.
// Nodos: `optica` (centro del vidrio), `anillo_luz` (difusor emisivo),
// `ancla_soporte` (donde va el poste), `pin_<id>_USB`, `pin_<idAnillo>_+5V/GND`.
// ==================================================================
export function crearWebcam({ id = 'cam_cenital', sensorId = 'camara', anillo = true, idAnillo = 'anillo',
                              resolucion = '1080p', cable = 30 } = {}) {
  const g = new THREE.Group();
  const cuerpo = mat(0x2a2e35, { metalness: 0.5, roughness: 0.45 });
  // Carcasa: Three directo (x, y=eje optico, z). Cara frontal en y = -10 mm.
  const box = (w, h, d, x, y, z, m) => {
    const o = new THREE.Mesh(new THREE.BoxGeometry(w * MM, h * MM, d * MM), m);
    o.position.set(x * MM, y * MM, z * MM); g.add(o); return o;
  };
  const cy = (r, h, x, y, z, m, seg = 32, r2 = null) => {
    const o = new THREE.Mesh(new THREE.CylinderGeometry((r2 ?? r) * MM, r * MM, h * MM, seg), m);
    o.position.set(x * MM, y * MM, z * MM); g.add(o); return o;
  };
  box(42, 18, 42, 0, 0, 0, cuerpo);
  box(40, 1.2, 40, 0, -9.4, 0, mat(0x1a1d22, { roughness: 0.5 }));   // tapa frontal
  // tornillos de la tapa
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) cy(1.1, 0.6, sx * 17, -10.1, sz * 17, mat(0x8a9099, METAL), 12);
  // Portalente M12 (cuadrado 16 mm) + lente (barril 14 mm con estrias) + vidrio.
  box(16, 6, 16, 0, -13, 0, PLASTICO_NEGRO());
  cy(7, 11, 0, -21.5, 0, mat(0x0d0f12, { metalness: 0.4, roughness: 0.35 }));
  for (let k = 0; k < 4; k++) cy(7.3, 0.9, 0, -18.5 - k * 1.8, 0, mat(0x16181c, { roughness: 0.3 }), 32);
  cy(5.2, 0.4, 0, -27.1, 0, mat(0x1a3a5a, { metalness: 0.9, roughness: 0.05 }), 32).name = 'vidrio';
  ancla(g, 'optica', new THREE.Vector3(0, -27.3 * MM, 0), new THREE.Vector3(0, -1, 0));
  // LED de actividad y rotulo.
  const led = cy(0.9, 0.5, 14, -10.2, -15, mat(0x30363d, { roughness: 0.2 }), 12);
  led.name = 'led_estado';
  const rot = serigrafia(g, `USB ${resolucion}`, 0, 0, 0, 18, 3);
  rot.rotation.set(Math.PI / 2, 0, 0); rot.position.set(0, -10.1 * MM, 15 * MM);
  // Cable USB (5 mm) con prensacable por la cara trasera de un costado.
  cy(3.2, 6, 21 + 3, 2, 0, mat(0x1c1c1c), 16).rotation.z = Math.PI / 2;
  const cab = cy(2.5, cable, 27 + cable / 2, 2, 0, mat(0x1b1b1b, { roughness: 0.7 }), 12);
  cab.rotation.z = Math.PI / 2;
  ancla(g, `pin_${id}_USB`, new THREE.Vector3((27 + cable) * MM, 2 * MM, 0), new THREE.Vector3(1, 0, 0));
  // Soporte: rosca 1/4" en la cara trasera, rotula de 12 mm y escuadra de
  // aluminio de 20 mm de ancho.
  cy(4, 3, 0, 10.5, 0, mat(0x9aa0a6, METAL), 20);
  cy(3, 5, 0, 14.5, 0, mat(0x6d737b, METAL), 16);
  const bola = new THREE.Mesh(new THREE.SphereGeometry(6 * MM, 20, 14), mat(0x3a3f46, METAL));
  bola.position.set(0, 22 * MM, 0); g.add(bola);
  cy(4, 8, 0, 31, 0, mat(0x3a3f46, METAL), 20);
  box(20, 2, 30, 0, 36, 7, mat(0xb9bec5, { metalness: 0.8, roughness: 0.35 }));
  ancla(g, 'ancla_soporte', new THREE.Vector3(0, 37 * MM, 20 * MM), new THREE.Vector3(0, 0, 1));
  let difusor = null;
  if (anillo) {
    // Anillo LED 60/40 mm: PCB negra 1,6 mm + 16 LED 5050 + difusor opalino.
    const yA = -24;
    for (const [dy, rx] of [[0, Math.PI / 2], [1.6, -Math.PI / 2]]) {   // caras de abajo y de arriba
      const ring = new THREE.Mesh(new THREE.RingGeometry(20 * MM, 30 * MM, 48), mat(0x111111));
      ring.rotation.x = rx; ring.position.y = (yA + dy) * MM; g.add(ring);
    }
    const aro = new THREE.Mesh(new THREE.CylinderGeometry(30 * MM, 30 * MM, 1.6 * MM, 48, 1, true), mat(0x111111, { side: THREE.DoubleSide }));
    aro.position.y = (yA + 0.8) * MM; g.add(aro);
    for (let k = 0; k < 16; k++) {
      const a = k / 16 * Math.PI * 2;
      box(5, 1.4, 5, Math.cos(a) * 25, yA - 0.8, Math.sin(a) * 25, mat(0xf4f4f4));
    }
    difusor = new THREE.Mesh(new THREE.TorusGeometry(25 * MM, 5.2 * MM, 10, 48),
      mat(0xfffaf0, { emissive: 0xfff4e0, emissiveIntensity: 0.35, transparent: true, opacity: 0.88, roughness: 0.9 }));
    difusor.rotation.x = Math.PI / 2;
    difusor.scale.set(1, 1, 0.55);
    difusor.position.y = (yA - 3.5) * MM;
    difusor.name = 'anillo_luz';
    g.add(difusor);
    // 3 separadores M3 de la carcasa al anillo.
    for (let k = 0; k < 3; k++) {
      const a = Math.PI / 6 + k * 2 * Math.PI / 3;
      const px = Math.cos(a) * 27, pz = Math.sin(a) * 27;
      cy(1.8, 14, px, -10 - 7, pz, mat(0xc8a24a, METAL), 6);
    }
    // Pads de alimentacion atras del anillo (+5V, GND) con sus hilos.
    for (const [n, dx, color] of [['+5V', -3, 0xc62828], ['GND', 3, 0x151515]]) {
      box(2.5, 0.3, 2, dx, yA + 1.8, -28, mat(0xc9ccd1, METAL));
      ancla(g, `pin_${idAnillo}_${n}`, new THREE.Vector3(dx * MM, (yA + 2.2) * MM, -28 * MM), new THREE.Vector3(0, 1, 0));
    }
  }
  marcar(g, sensorId, id, new THREE.Vector3(0, -1, 0), { led, anillo: difusor, resolucion });
  return g;
}

// ==================================================================
// 5 / 8 / 13 · VL53L0X en modulo GY-VL53L0XV2: placa morada 25 x 10,7 x 1,6
// mm, dos agujeros de 2,2 mm en los extremos, regulador 662K (SOT-23) y
// condensadores; el VL53L0X (4,4 x 2,4 x 1,0 mm, ventana del emisor y del
// receptor) va en la cara de ABAJO mirando a -Z; el header de 6 pines
// (VIN GND SCL SDA GPIO1 XSHUT) sale hacia arriba, como en conexiones.py.
// ==================================================================
export function crearVL53L0X({ id = 'vl53_interior', sensorId = 'sensor_interior' } = {}) {
  const g = new THREE.Group();
  const T = 1.6;
  pcb(g, 25, 10.7, T, 0x6b1fa3, [[-10.35, -1.6, 2.2], [10.35, -1.6, 2.2]]);
  // Chip debajo: cuerpo negro con dos ventanas de vidrio.
  caja(g, 4.4, 2.4, 1.0, 0, -1.8, -0.5, mat(0x0c0c0c, { roughness: 0.35 }));
  for (const [dx, color] of [[-0.9, 0x5a3a2a], [0.9, 0x2a2a3a]]) {
    const v = new THREE.Mesh(new THREE.CircleGeometry(0.42 * MM, 14), mat(color, { metalness: 0.6, roughness: 0.05 }));
    v.rotation.x = Math.PI / 2;
    v.position.copy(P(dx, -1.8, -1.02));
    g.add(v);
  }
  ancla(g, 'optica', P(0, -1.8, -1.05), D(0, 0, -1));
  // Componentes de arriba: regulador, capacitores, resistencias de pull-up.
  caja(g, 2.9, 1.6, 1.1, -6, -2.6, T + 0.55, mat(0x1a1a1a));
  for (const [x, y] of [[-2.5, -2.8], [0.5, -2.8], [3.5, -2.8], [6.5, -2.8]]) smd(g, x, y, T, 1.6, 0.8, x < 0 ? 0xb58a4a : 0x2a2a2a, 0.45);
  header(g, id, fila(['VIN', 'GND', 'SCL', 'SDA', 'GPIO1', 'XSHUT'], -6.35, 3.5, 'x'), T, { tipo: 'recto', lado: 1 });
  serigrafia(g, 'GY-VL53L0XV2', 0, -0.6, T, 13, 1.6);
  marcar(g, sensorId, id, D(0, 0, -1), { medidas: [25, 10.7, 1.6] });
  return g;
}

// ==================================================================
// 6 · Hall A3144 en modulo KY-003: placa 18,5 x 15 x 1,6 mm (ficha KY-003),
// agujero M3, LED rojo SMD + resistencia; el A3144 (TO-92S: 4,0 x 3,0 x
// 1,52 mm) doblado y ACOSTADO debajo de la placa con la cara marcada hacia
// -Z (el iman pasa por debajo); header acodado S, +, - saliendo por +x.
// ==================================================================
export function crearHallKY003({ id = 'hall', sensorId = 'hall_carrusel' } = {}) {
  const g = new THREE.Group();
  const T = 1.6;
  pcb(g, 18.5, 15, T, 0x1b1d22, [[-2.5, 4.5, 3.0]]);
  // A3144 acostado bajo la punta -x.
  caja(g, 3.0, 4.0, 1.52, -6.2, 0, -1.3, mat(0x111111, { roughness: 0.4 }));
  caja(g, 2.0, 3.0, 0.02, -6.2, 0, -2.07, mat(0x333333));   // cara marcada (biselada)
  for (const dy of [-1.27, 0, 1.27]) {
    caja(g, 2.4, 0.4, 0.4, -3.5, dy, -1.3, EST());
    caja(g, 0.4, 0.4, 1.5, -2.3, dy, -0.6, EST());
  }
  ancla(g, 'optica', P(-6.2, 0, -2.1), D(0, 0, -1));
  smd(g, 1.0, -4.0, T, 2.0, 1.25, 0x2a2a2a);
  const led = ledSmd(g, 1.0, 4.8, T, 0xff2020, 'led_estado');
  header(g, id, fila(['S', '+', '−'], 7.0, -2.54), T, { tipo: 'acodado', sale: [1, 0] });
  serigrafia(g, 'KY-003', -3, -4.5, T, 7, 2);
  marcar(g, sensorId, id, D(0, 0, -1), { led, medidas: [18.5, 15, 1.6] });
  return g;
}
// Iman de neodimio N35 de 6 x 3 mm, niquelado. Origen al centro, eje +Y
// (cara norte arriba, marcada con un punto rojo).
export function crearIman6x3({ sensorId = 'hall_carrusel' } = {}) {
  const g = new THREE.Group();
  g.add(new THREE.Mesh(new THREE.CylinderGeometry(3 * MM, 3 * MM, 3 * MM, 32), mat(0xd9dde2, { metalness: 0.95, roughness: 0.18 })));
  const n = new THREE.Mesh(new THREE.CircleGeometry(0.8 * MM, 16), mat(0xc62828));
  n.rotation.x = -Math.PI / 2; n.position.y = 1.52 * MM;
  g.add(n);
  return marcar(g, sensorId, 'iman', new THREE.Vector3(0, 1, 0), { medidas: [6, 3] });
}

// ==================================================================
// 10 · HC-SR04: placa 45 x 20 x 1,6 mm, 4 agujeros de 1 mm en las esquinas;
// transductores T y R de 16 mm de diametro x 12 mm de alto con malla,
// centros a 26 mm; cristal HC-49S de 12 MHz entre los dos; header acodado
// de 4 pines (VCC TRIG ECHO GND) en el borde -y, puntas en el plano de la
// placa (asi viene el modulo real). Atras: 3 CI SOIC (MCU, LM324, MAX232).
// Mira hacia +Z de ficha.
// ==================================================================
export function crearHCSR04({ id = 'hcsr04', sensorId = 'ultrasonico' } = {}) {
  const g = new THREE.Group();
  const T = 1.6;
  pcb(g, 45, 20, T, 0x1e5aa8, [[-21, 8.5, 1.1], [21, 8.5, 1.1], [-21, -8.5, 1.1], [21, -8.5, 1.1]]);
  const lata = mat(0xc9ccd1, { metalness: 0.85, roughness: 0.3 });
  for (const [x, letra] of [[-13, 'T'], [13, 'R']]) {
    cil(g, 8, 12, x, 1, T + 6, lata, 'z', 40);
    cil(g, 8.05, 0.8, x, 1, T + 11.6, mat(0xb0b4ba, METAL), 'z', 40);           // reborde
    cil(g, 6.6, 0.3, x, 1, T + 12.05, mat(0x1a1a1a, { roughness: 0.9 }), 'z', 32); // malla
    for (let k = -2; k <= 2; k++) {                                              // tejido de la malla
      caja(g, 12.6, 0.18, 0.1, x, 1 + k * 2.4, T + 12.25, mat(0x3a3a3a));
      caja(g, 0.18, 12.6, 0.1, x + k * 2.4, 1, T + 12.25, mat(0x3a3a3a));
    }
    serigrafia(g, letra, x - 9.3, -7.3, T, 2.4, 2.4);
  }
  // Cristal HC-49S (11 x 4,6 x 3,5 mm).
  const cr = caja(g, 11, 4.6, 3.5, 0, 5.5, T + 1.75, lata);
  cr.name = 'cristal';
  serigrafia(g, 'HC-SR04', 0, 1.2, T, 11, 2.4);
  serigrafia(g, 'Vcc Trig Echo Gnd', 0, -4.2, T, 13, 1.4);
  header(g, id, fila(['VCC', 'TRIG', 'ECHO', 'GND'], -3.81, -8.5, 'x'), T, { tipo: 'acodado', sale: [0, -1] });
  // Cara de atras: tres CI SOIC y pasivos.
  const atras = new THREE.Group();
  soic(atras, -12, -1.5, 0, 8, { nombre: 'MCU' });
  soic(atras, 0, -1.5, 0, 14, { nombre: 'LM324' });
  soic(atras, 12, -1.5, 0, 14, { nombre: 'MAX232' });
  for (let k = 0; k < 6; k++) smd(atras, -12 + k * 4.8, -6.5, 0, 1.6, 0.8, k % 2 ? 0x2a2a2a : 0xb58a4a, 0.45);
  atras.rotation.x = Math.PI;   // espejo a la cara de abajo (z -> -z)
  g.add(atras);
  ancla(g, 'optica', P(0, 1, T + 12.3), D(0, 0, 1));
  marcar(g, sensorId, id, D(0, 0, 1), { medidas: [45, 20, 1.6] });
  return g;
}

// ==================================================================
// 9 · Arreglo de 5 TCRT5000 (modulo de 5 canales, LM339): placa 14 x 74 x
// 1,6 mm (largo en y), sensores a `paso` mm (15, config: separacion_
// sensores_linea_mm) boca abajo, un LED rojo por canal arriba
// (`led_ir_0..4`, 0 = y negativo), header recto de 7 pines (VCC GND
// OUT1-OUT5) arriba, como en conexiones.py.
// ==================================================================
export function crearArregloTCRT5000({ id = 'ir_linea', sensorId = 'linea_ir', n = 5, paso = 15 } = {}) {
  const g = new THREE.Group();
  const T = 1.6;
  const W = (n - 1) * paso + 14;
  pcb(g, 14, W, T, 0x1e5aa8, [[0, -W / 2 + 3, 3.0], [0, W / 2 - 3, 3.0]]);
  const leds = [];
  for (let i = 0; i < n; i++) {
    const y = (i - (n - 1) / 2) * paso;
    tcrt5000(g, -3, y, 0, 'x');
    ancla(g, `optica_${i}`, P(-3, y, -7.8), D(0, 0, -1));
    const l = ledSmd(g, -4.5, y + (y > -8 && y < 8 ? -2.5 : 0), T, 0xff2a2a, `led_ir_${i}`);
    leds.push(l);
    smd(g, -1.2, y + 3.2, T, 1.6, 0.8, 0x2a2a2a, 0.45);
  }
  soic(g, 3.0, 15, T, 14, { giro: true, nombre: 'LM339' });
  header(g, id, fila(['VCC', 'GND', 'OUT1', 'OUT2', 'OUT3', 'OUT4', 'OUT5'], 4.5, -7.6), T, { tipo: 'recto', lado: 1 });
  serigrafia(g, 'TCRT5000 x5', 2.5, -W / 2 + 12, T, 12, 1.8, { giro: Math.PI / 2 });
  marcar(g, sensorId, id, D(0, 0, -1), { leds, medidas: [14, W, 1.6] });
  return g;
}

// ==================================================================
// 12 · Infrarrojo de la cuna: modulo TCRT5000 de un canal (LM393), placa
// 32 x 14 x 1,6 mm con agujero M3, TCRT5000 boca abajo en la punta -x,
// trimmer azul, LED de alimentacion y de senal, header acodado de 4 pines
// (VCC GND DO AO) saliendo por +x.
// ==================================================================
export function crearIRCuna({ id = 'ir_cuna', sensorId = 'cuna' } = {}) {
  const g = new THREE.Group();
  const T = 1.6;
  pcb(g, 32, 14, T, 0x1e5aa8, [[-1, 0, 3.0]]);
  tcrt5000(g, -12, 0, 0, 'y');
  ancla(g, 'optica', P(-12, 0, -7.8), D(0, 0, -1));
  trimmer(g, -8, 0, T);
  soic(g, 4, 3.3, T, 8, { giro: true, nombre: 'LM393' });
  const led = ledSmd(g, 8.5, 5.3, T, 0x30ff60, 'led_estado');
  ledSmd(g, 8.5, -5.3, T, 0xff3030, 'led_alimentacion');
  smd(g, 4, -3.8, T, 2.0, 1.25, 0x2a2a2a);
  header(g, id, fila(['VCC', 'GND', 'DO', 'AO'], 14.0, -3.81), T, { tipo: 'acodado', sale: [1, 0] });
  serigrafia(g, 'TCRT5000', -1, -5.3, T, 9, 1.8);
  marcar(g, sensorId, id, D(0, 0, -1), { led, medidas: [32, 14, 1.6] });
  return g;
}

// ==================================================================
// 11 · Encoder optico de ranura H206 (LM393): placa 32 x 14 x 1,6 mm,
// horquilla H206 en la punta -x (12 x 11 x 11 mm, ranura de 5 mm de ancho x
// 7,5 de hondo, el haz a 5,5 mm del fondo), LM393, LED, header acodado de 3
// pines (VCC GND D0) por +x. La ranura corta la placa a lo largo de x: el
// disco entra por arriba, en el plano x-z de ficha. `ancla_haz` = centro del
// haz (donde tiene que pasar la corona de ventanas del disco).
// ==================================================================
export function crearEncoderH206({ id = 'enc_izq', sensorId = 'encoders' } = {}) {
  const g = new THREE.Group();
  const T = 1.6;
  pcb(g, 32, 14, T, 0x1e5aa8, [[2, 0, 3.0]]);
  const neg = mat(0x121212, { roughness: 0.5 });
  const xF = -9.5;
  caja(g, 12, 11, 3.5, xF, 0, T + 1.75, neg);                     // base
  for (const s of [-1, 1]) {
    caja(g, 12, 3, 7.5, xF, s * 4, T + 3.5 + 3.75, neg);           // dedos
    // ventanitas del emisor / receptor enfrentadas
    caja(g, 1.4, 0.05, 1.4, xF + 1, s * 2.47, T + 3.5 + 5.5 - 3.5, mat(s < 0 ? 0x3b6fd8 : 0x050505));
  }
  serigrafia(g, 'H206', xF, -4, T + 11, 6, 1.8);
  ancla(g, 'ancla_haz', P(xF + 1, 0, T + 5.5), D(0, 1, 0));
  soic(g, 7, 3.2, T, 8, { giro: true, nombre: 'LM393' });
  const led = ledSmd(g, 7, -4.5, T, 0x30ff60, 'led_estado');
  smd(g, 2, -4.6, T, 2.0, 1.25, 0x2a2a2a);
  header(g, id, fila(['VCC', 'GND', 'D0'], 14.0, -2.54), T, { tipo: 'acodado', sale: [1, 0] });
  marcar(g, sensorId, id, D(0, 1, 0), { led, medidas: [32, 14, 1.6] });
  return g;
}
// Disco de encoder de 20 ventanas para motor TT: 25 mm de diametro, 1,5 mm
// de espesor, ventanas de 2 x 4 mm entre r = 8 y r = 12 mm, agujero en D de
// 5,4 x 3,7 mm para el eje. Origen al centro, eje de giro = +Y. El Group
// devuelto se llama `disco_encoder` (girarlo con .rotation.y).
export function crearDiscoEncoder20({ sensorId = 'encoders', ventanas = 20, diametro = 25 } = {}) {
  const R = diametro / 2;
  const forma = new THREE.Shape();
  forma.absarc(0, 0, R, 0, Math.PI * 2, false);
  for (let k = 0; k < ventanas; k++) {
    const a0 = (k / ventanas) * Math.PI * 2, da = (Math.PI * 2 / ventanas) * 0.45;
    const h = new THREE.Path();
    h.absarc(0, 0, R - 0.8, a0, a0 + da, false);
    h.absarc(0, 0, R - 4.8, a0 + da, a0, true);
    h.closePath();
    forma.holes.push(h);
  }
  const eje = new THREE.Path();   // agujero en D
  const r = 2.7;
  const c = Math.acos(1.0 / r);
  eje.absarc(0, 0, r, c, Math.PI * 2 - c, false);
  eje.lineTo(1.0, r * Math.sin(c));
  eje.closePath();
  forma.holes.push(eje);
  const geo = new THREE.ExtrudeGeometry(forma, { depth: 1.5, bevelEnabled: false, curveSegments: 10 });
  geo.translate(0, 0, -0.75);
  geo.scale(MM, MM, MM);
  geo.rotateX(-Math.PI / 2);
  const g = new THREE.Group();
  const m = new THREE.Mesh(geo, mat(0x161616, { roughness: 0.5 }));
  m.name = 'disco';
  g.add(m);
  // cubo del disco
  const cubo = new THREE.Mesh(new THREE.CylinderGeometry(4 * MM, 4 * MM, 3 * MM, 24, 1, true), mat(0x161616, { side: THREE.DoubleSide }));
  cubo.position.y = 1.5 * MM;
  g.add(cubo);
  marcar(g, sensorId, 'disco_encoder', new THREE.Vector3(0, 1, 0), { ventanas, radioVentanas: (R - 2.8) * MM });
  g.name = 'disco_encoder';
  return g;
}

// ==================================================================
// Tabla: sensor del catalogo (sim/catalogos.py) -> como construirlo.
// ==================================================================
export const SENSORES = {
  presencia: () => crearFC51({ id: 'presencia', sensorId: 'presencia' }),
  capacitivo: () => crearCapacitivoLJC18A3({ id: 'capacitivo', sensorId: 'capacitivo' }),
  inductivo: () => crearInductivoLJ18A3({ id: 'inductivo', sensorId: 'inductivo' }),
  camara: () => crearWebcam({ id: 'cam_cenital', sensorId: 'camara', anillo: true, resolucion: '1080p' }),
  sensor_interior: () => crearVL53L0X({ id: 'vl53_interior', sensorId: 'sensor_interior' }),
  hall_carrusel: () => crearHallKY003({ id: 'hall', sensorId: 'hall_carrusel' }),
  camara_vasos: () => crearWebcam({ id: 'cam_vasos', sensorId: 'camara_vasos', anillo: false, resolucion: '720p' }),
  cortina: () => crearVL53L0X({ id: 'vl53_cortina', sensorId: 'cortina' }),
  linea_ir: () => crearArregloTCRT5000({ id: 'ir_linea', sensorId: 'linea_ir' }),
  ultrasonico: () => crearHCSR04({ id: 'hcsr04', sensorId: 'ultrasonico' }),
  encoders: () => crearEncoderH206({ id: 'enc_izq', sensorId: 'encoders' }),
  laser_frontal: () => crearVL53L0X({ id: 'vl53_frontal', sensorId: 'laser_frontal' }),
  cuna: () => crearIRCuna({ id: 'ir_cuna', sensorId: 'cuna' }),
};
