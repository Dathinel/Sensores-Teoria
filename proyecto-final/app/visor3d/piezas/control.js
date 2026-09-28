// Piezas de la mesa de control: el gabinete de la caja de control (acrilico con tapa
// transparente, prensaestopas y ventilacion) y el portatil del grupo (ASUS TUF Gaming A15).
// Convencion: ver README.md de esta carpeta. Marco de la simulacion (x largo, y ancho, z arriba),
// metros; las medidas de ficha tecnica van en mm y se pasan con MM.
//
// Contenido:
//   crearGabineteControl(opciones)   caja de acrilico 360 × 240 × 80 mm con placa de montaje,
//                                    esquineros de aluminio, tapa de policarbonato atornillada,
//                                    prensaestopas, ventilador 40 mm y rejilla de entrada de aire
//   crearPrensaestopas(opciones)     prensaestopas de nylon PG7 / PG9 / PG11 / PG16
//   crearVentilador4010(opciones)    ventilador 40 × 40 × 10 mm de 5 V con su rejilla
//   crearLaptopTUFA15(opciones)      ASUS TUF Gaming A15 a su medida real, con la pantalla del
//                                    asistente (lienzo 1920 × 1080) y el teclado RGB

import * as THREE from 'three';
import { MM, COLOR, METAL, PLASTICO, P, mat, caja, cilindro, ancla, instancias, planoDibujado, terminar } from './base.js';

const Pm = (x, y, z) => P(x * MM, y * MM, z * MM);                 // mm -> Three

function _datos(o) {
  return { ...(o.idComponente ? { idComponente: o.idComponente } : {}), ...(o.sensorId ? { sensorId: o.sensorId } : {}) };
}

// Cilindro con el eje a lo ANCHO (y de la simulacion), centrado en (x, y, z) mm. `lados` = 6 para
// una tuerca hexagonal; `giro` gira la pieza sobre su eje (para poner caras planas o vertices arriba).
function _cilY(r, largo, color, x, y, z, extra, lados = 28, giro = 0) {
  const m = cilindro(r * MM, largo * MM, color, Pm(x, y, z), extra, lados);
  m.rotation.set(Math.PI / 2, 0, 0);
  m.rotateY(giro);
  return m;
}

// Caja con esquinas redondeadas (en planta), extruida hacia arriba (z de la simulacion). Medidas en
// metros; `pos` = centro de la cara de abajo.
export function cajaRedonda(sx, sy, sz, r, color, pos, extra = {}) {
  const f = new THREE.Shape();
  const x = -sx / 2, y = -sy / 2;
  f.moveTo(x + r, y); f.lineTo(x + sx - r, y); f.quadraticCurveTo(x + sx, y, x + sx, y + r);
  f.lineTo(x + sx, y + sy - r); f.quadraticCurveTo(x + sx, y + sy, x + sx - r, y + sy);
  f.lineTo(x + r, y + sy); f.quadraticCurveTo(x, y + sy, x, y + sy - r);
  f.lineTo(x, y + r); f.quadraticCurveTo(x, y, x + r, y);
  const bisel = Math.min(sz * 0.25, r * 0.5, 0.0012);
  const g = new THREE.ExtrudeGeometry(f, { depth: Math.max(sz - 2 * bisel, 1e-4), bevelEnabled: bisel > 0,
    bevelThickness: bisel, bevelSize: bisel, bevelSegments: 2, curveSegments: 6 });
  g.rotateX(-Math.PI / 2);
  g.translate(0, bisel, 0);
  const m = new THREE.Mesh(g, color && color.isMaterial ? color : mat(color, extra));
  if (pos) m.position.copy(pos);
  m.castShadow = true;
  return m;
}

// ---------------------------------------------------------------------------
// Prensaestopas de nylon (norma PG, DIN 40430)
// ---------------------------------------------------------------------------
// Medidas de catalogo (tipo LAPP SKINTOP / genericos negros): rosca, llave (entre caras), tuerca
// de cupula y largo por fuera de la pared, y el rango de cable que sella.
//   PG7:  rosca 12,5 · llave 15 · cupula 15 · 19 mm afuera · cable 3-6,5 mm
//   PG9:  rosca 15,2 · llave 19 · cupula 19 · 21 mm afuera · cable 4-8 mm
//   PG11: rosca 18,6 · llave 22 · cupula 22 · 22 mm afuera · cable 5-10 mm
//   PG16: rosca 22,5 · llave 24 · cupula 24 · 24 mm afuera · cable 10-14 mm
// Origen: centro del agujero, EN la cara de AFUERA de la pared. La pieza sale hacia -y (afuera) y la
// contratuerca queda hacia +y (adentro, contra la cara interior de una pared de `pared` mm).
// Contratuerca de nylon real: 5 mm de alto (ficha Lapp SKINTOP GMP-GL, PG7 a PG16); la canaleta de
// adelante de la caja queda a 7,2 mm de la pared para no chocar con ellas.
// Anclas: ancla_afuera (boca de la cupula, por donde entra el cable) y ancla_adentro.
export const PG = {
  PG7: { rosca: 12.5, llave: 15, cupula: 15, fuera: 19, cable: [3, 6.5], contratuerca: 5 },
  PG9: { rosca: 15.2, llave: 19, cupula: 19, fuera: 21, cable: [4, 8], contratuerca: 5 },
  PG11: { rosca: 18.6, llave: 22, cupula: 22, fuera: 22, cable: [5, 10], contratuerca: 5 },
  PG16: { rosca: 22.5, llave: 24, cupula: 24, fuera: 24, cable: [10, 14], contratuerca: 5 },
};

export function crearPrensaestopas(opciones = {}) {
  const { tipo = 'PG7', pared = 3, color = 0x1b1c1f, verticesArriba = true } = opciones;
  const d = PG[tipo] || PG.PG7;
  const g = new THREE.Group();
  g.name = `prensaestopas_${tipo}`;
  const nylon = { roughness: 0.55, metalness: 0.0 };
  const rHex = d.llave / 2 / Math.cos(Math.PI / 6);          // radio a los vertices
  const giro = verticesArriba ? 0 : Math.PI / 6;
  // Afuera: brida hexagonal contra la pared, tuerca de cupula (hexagono + cupula redonda) y el
  // sello de goma que abraza el cable.
  g.add(_cilY(rHex, 3, color, 0, -1.5, 0, nylon, 6, giro));
  g.add(_cilY(d.rosca / 2, 2, color, 0, -4, 0, nylon));
  g.add(_cilY(rHex * 0.97, 5, color, 0, -7.5, 0, nylon, 6, giro));
  const largoCup = d.fuera - 10 - d.cupula * 0.18;
  g.add(_cilY(d.cupula / 2, largoCup, color, 0, -10 - largoCup / 2, 0, nylon));
  const domo = new THREE.Mesh(new THREE.SphereGeometry(d.cupula / 2 * MM, 24, 10, 0, Math.PI * 2, 0, Math.PI / 2), mat(color, nylon));
  domo.scale.set(1, 0.36, 1);
  domo.rotation.x = Math.PI / 2;              // la cupula mira hacia -y (afuera)
  domo.position.copy(Pm(0, -10 - largoCup, 0));
  domo.castShadow = true;
  g.add(domo);
  // Boca y sello (goma gris) donde entra el cable.
  const yBoca = -d.fuera;
  g.add(_cilY(d.cable[1] / 2 + 0.8, 0.6, 0x4a4f57, 0, yBoca + 0.5, 0, { roughness: 0.9 }));
  g.add(_cilY(d.cable[1] / 2 - 0.2, 0.4, 0x050506, 0, yBoca + 0.3, 0, { roughness: 1 }));
  // Adentro: contratuerca (5 mm) y la punta de la rosca que asoma 1 mm.
  const ct = d.contratuerca || 5;
  g.add(_cilY(rHex, ct, color, 0, pared + ct / 2, 0, nylon, 6, giro));
  g.add(_cilY(d.rosca / 2 - 0.4, 1, color, 0, pared + ct + 0.5, 0, nylon));
  g.add(ancla('ancla_afuera', Pm(0, yBoca, 0)));
  g.add(ancla('ancla_adentro', Pm(0, pared + ct + 1, 0)));
  terminar(g, { datos: _datos(opciones) });
  g.userData.pieza = `Prensaestopas ${tipo}`;
  return g;
}

// ---------------------------------------------------------------------------
// Ventilador 40 × 40 × 10 mm de 5 V (tipo 4010, 2 hilos) con rejilla de alambre
// ---------------------------------------------------------------------------
// Ficha tipica 4010: marco de 40 × 40 × 10 mm, agujeros de 3,4 mm a 32 mm entre centros, rotor
// de 37 mm con 7 aspas y cubo de 20 mm. Rejilla de alambre de 40 mm (4 anillos + cruz).
// Origen: centro, EN la cara de afuera de la pared donde se atornilla; el ventilador queda hacia
// -y (afuera) y SACA el aire de la caja. Nodo: aspas (gira sola al dibujarse, ~6 vueltas por
// segundo, solo para que se vea que funciona). Anclas: pin_<id>_+5V y pin_<id>_GND del lado de
// adentro de la pared (los dos hilos pasan por un agujero de 4 mm junto al marco).
export function crearVentilador4010(opciones = {}) {
  const { id = 'ventilador', pared = 3, girar = true } = opciones;
  const g = new THREE.Group();
  g.name = 'ventilador_4010';
  const negro = 0x141517;
  // Marco: 4 lados + las 4 orejas de las esquinas (con el agujero del tornillo).
  for (const [sx, sz, x, z] of [[40, 4, 0, 18], [40, 4, 0, -18], [4, 32, 18, 0], [4, 32, -18, 0]])
    g.add(caja(sx * MM, 10 * MM, sz * MM, negro, Pm(x, -5, z), PLASTICO));
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    g.add(caja(8 * MM, 2 * MM, 8 * MM, negro, Pm(sx * 16, -1, sz * 16), PLASTICO));
    g.add(caja(8 * MM, 2 * MM, 8 * MM, negro, Pm(sx * 16, -9, sz * 16), PLASTICO));
    // Tornillo M3 de cabeza redonda por afuera y su tuerca adentro.
    g.add(_cilY(2.8, 1.6, COLOR.acero, sx * 16, -10.8, sz * 16, METAL, 16));
    g.add(_cilY(3.2, 2.4, COLOR.acero, sx * 16, pared + 1.2, sz * 16, METAL, 6));
  }
  // Tubo del rotor (el hueco redondo del marco) y los 3 brazos del motor, del lado de la pared.
  const tubo = new THREE.Mesh(new THREE.CylinderGeometry(19 * MM, 19 * MM, 10 * MM, 32, 1, true),
    mat(negro, { ...PLASTICO, side: THREE.DoubleSide }));
  tubo.rotation.x = Math.PI / 2;
  tubo.position.copy(Pm(0, -5, 0));
  g.add(tubo);
  for (let i = 0; i < 3; i++) {
    // Brazo radial de 19 mm en el plano del rotor (plano x-z de la simulacion).
    const a = Math.PI / 2 + (i * 2 * Math.PI) / 3;
    const b = caja(19 * MM, 1.5 * MM, 1.6 * MM, negro, Pm(9.5 * Math.cos(a), -0.75, 9.5 * Math.sin(a)), PLASTICO);
    b.rotation.z = a;
    g.add(b);
  }
  // Rotor: cubo con la etiqueta y 7 aspas inclinadas.
  const aspas = new THREE.Group();
  aspas.name = 'aspas';
  aspas.position.copy(Pm(0, -5.5, 0));
  aspas.add(_cilY(10, 7, 0x1d1f22, 0, 0, 0, PLASTICO, 28));
  const et = planoDibujado(14 * MM, 14 * MM, (ctx, X, Y, k) => {
    ctx.fillStyle = '#d9d9d9'; ctx.beginPath(); ctx.arc(X(0), Y(0), 7 * k, 0, 7); ctx.fill();
    ctx.fillStyle = '#16181c'; ctx.font = `700 ${2.2 * k}px "IBM Plex Mono", monospace`; ctx.textAlign = 'center';
    ctx.fillText('DC 5V', X(0), Y(1)); ctx.fillText('0.10A', X(0), Y(-2.4));
  }, { ppm: 24 });
  et.rotation.set(0, 0, 0);                   // plano vertical mirando hacia -y (afuera)
  et.position.copy(Pm(0, -3.56, 0));
  aspas.add(et);
  const matAspa = mat(0x202225, { roughness: 0.45, side: THREE.DoubleSide });
  for (let i = 0; i < 7; i++) {
    const a = new THREE.Mesh(new THREE.BoxGeometry(8.5 * MM, 7 * MM, 0.8 * MM), matAspa);
    const piv = new THREE.Group();
    a.position.set(14 * MM, 0, 0);
    a.rotation.x = 0.55;                      // paso del aspa
    piv.add(a);
    // El rotor gira sobre el eje y de la simulacion (= -z de Three): las aspas se reparten ahi.
    piv.rotateOnAxis(new THREE.Vector3(0, 0, 1), (i * 2 * Math.PI) / 7);
    aspas.add(piv);
  }
  g.add(aspas);
  if (girar) {
    // Gira sola sin depender del bucle del visor (una malla avisa antes de dibujarse).
    let t0 = null;
    aspas.children[0].onBeforeRender = () => {
      const t = performance.now() / 1000;
      if (t0 === null) t0 = t;
      aspas.rotation.z = -(t - t0) * 2 * Math.PI * 6;
    };
  }
  // Rejilla de alambre (4 anillos + cruz), por afuera.
  const matAlambre = mat(0xb9bec6, METAL);
  for (const r of [5, 9.5, 14, 18.5]) {
    const an = new THREE.Mesh(new THREE.TorusGeometry(r * MM, 0.45 * MM, 6, 40), matAlambre);
    an.position.copy(Pm(0, -11.2, 0));
    g.add(an);
  }
  for (const giro of [Math.PI / 4, -Math.PI / 4]) {
    const c = caja(38 * MM, 0.9 * MM, 0.9 * MM, matAlambre, Pm(0, -11.2, 0));
    c.rotateOnAxis(new THREE.Vector3(0, 0, 1), giro);
    g.add(c);
  }
  // Los dos hilos (rojo y negro) entran por un agujero de 4 mm junto a la oreja de abajo.
  g.add(_cilY(2.6, pared + 0.6, 0x050506, 22, pared / 2, -16, { roughness: 1 }, 16));
  g.add(ancla(`pin_${id}_+5V`, Pm(21.2, pared + 2, -16), { pin: '+5V' }));
  g.add(ancla(`pin_${id}_GND`, Pm(22.8, pared + 2, -16), { pin: 'GND' }));
  terminar(g, { datos: _datos(opciones) });
  g.userData.pieza = 'Ventilador 4010 5 V';
  return g;
}

// ---------------------------------------------------------------------------
// Gabinete de la caja de control: acrilico de 3 mm, 360 × 240 × 80 mm
// ---------------------------------------------------------------------------
// Medidas: las del visor (antes de esta pieza, visor.js dibujaba piso + 4 paredes translucidas de
// 360 × 240 × 80 mm): la fuente LRS-150 sola mide 159 × 97 mm y hacen falta las canaletas.
// Como se construye: placa de montaje de aluminio de 3 mm (todo se atornilla a ella), 4 paredes de
// acrilico transparente de 3 mm cortadas a laser (con los agujeros de los prensaestopas, de la
// entrada IEC, del ventilador y la rejilla de ranuras), unidas en las esquinas por angulo de
// aluminio de 15 × 15 × 1,5 mm con tornillos M3, y tapa de policarbonato de 3 mm atornillada con
// 4 tornillos M4 a tacos impresos en las esquinas de arriba. Los tacos dejan 65 mm libres: nada de
// la caja (bornera DIN de 50 mm incluida) llega a la tapa.
// Origen: centro de la cara de ABAJO. x a lo largo (izquierda -x, derecha +x), y a lo ancho
// (adelante -y, donde entran los cables de campo), z arriba. Las paredes estan CENTRADAS en
// ±largo/2 y ±ancho/2 (igual que el modelo anterior del visor).
// opciones:
//   largo, ancho, alto, grueso (mm)
//   prensaestopas: [{ pared: 'frente'|'atras'|'izq'|'der', u, z, tipo, verticesArriba }] con u = mm
//     a lo largo de la pared desde el centro de la caja (x en frente/atras, y en izq/der).
//   ventilador: { pared, u, z } (o null); rejilla: { pared, u0, u1, z0, z1 } (o null)
//   rotulo: texto de la placa grabada de la tapa.
// Nodos: piso, pared_frente / pared_atras / pared_izq / pared_der, tapa, ventilador,
// prensaestopas_<i>. Anclas: ancla_prensa_<i> (boca de afuera de cada prensaestopas, en el orden
// dado), ancla_prensa_<i>_adentro, pin_ventilador_+5V / GND.
export function crearGabineteControl(opciones = {}) {
  const { largo = 360, ancho = 240, alto = 80, grueso = 3, prensaestopas = [], ventilador = null, rejilla = null,
    rotulo = 'CAJA DE CONTROL · GRUPO 7' } = opciones;
  const g = new THREE.Group();
  g.name = 'gabinete_control';
  const L = largo, W = ancho, H = alto, e = grueso;
  // Placa de montaje (aluminio anodizado gris oscuro, 3 mm). 0,2 mm mas chica por lado que el
  // borde de las paredes: sus cantos quedaban en el mismo plano que los de las paredes de acrilico
  // y se veian parpadear a traves de ellas (2026-09-28).
  const piso = caja((L - 0.4) * MM, (W - 0.4) * MM, e * MM, 0x2a2f36, Pm(0, 0, e / 2), { metalness: 0.35, roughness: 0.55 });
  piso.name = 'piso';
  g.add(piso);
  // Paredes de acrilico: casi invisibles, con los cantos marcados (el canto del acrilico se ve
  // mas que la cara, como en la realidad).
  const matAcr = mat(0xcfe6f5, { transparent: true, opacity: 0.1, roughness: 0.05, metalness: 0.0,
    depthWrite: false, side: THREE.DoubleSide });
  const matCanto = new THREE.LineBasicMaterial({ color: 0xbcd9ec, transparent: true, opacity: 0.55 });
  const paredes = {
    frente: [L, e, 0, -W / 2], atras: [L, e, 0, W / 2], izq: [e, W - 2 * e, -L / 2, 0], der: [e, W - 2 * e, L / 2, 0],
  };
  for (const [n, [sx, sy, x, y]] of Object.entries(paredes)) {
    const p = caja(sx * MM, sy * MM, H * MM, matAcr, Pm(x, y, H / 2));
    p.name = `pared_${n}`;
    p.castShadow = false;
    const cantos = new THREE.LineSegments(new THREE.EdgesGeometry(p.geometry), matCanto);
    cantos.raycast = () => {};
    p.add(cantos);
    g.add(p);
  }
  // Esquineros de aluminio 15 × 15 × 1,5 mm por afuera, con 3 tornillos M3 por ala.
  const matAl = mat(COLOR.aluminio, { metalness: 0.75, roughness: 0.35 });
  const tornillos = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    const x0 = sx * (L / 2 + e / 2), y0 = sy * (W / 2 + e / 2);
    g.add(caja(15 * MM, 1.5 * MM, H * MM, matAl, Pm(x0 - sx * 7.5, y0 + sy * 0.75, H / 2)));
    g.add(caja(1.5 * MM, 15 * MM, H * MM, matAl, Pm(x0 + sx * 0.75, y0 - sy * 7.5, H / 2)));
    for (const z of [12, H / 2, H - 12]) {
      tornillos.push(Pm(x0 - sx * 8, y0 + sy * 1.5, z), Pm(x0 + sx * 1.5, y0 - sy * 8, z));
    }
  }
  const cabeza = new THREE.SphereGeometry(2.8 * MM, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2);
  cabeza.scale(1, 0.55, 1);
  // Cabezas de boton: se orientan despues (una InstancedMesh por cara, apuntando hacia afuera).
  const porCara = { x: [], y: [] };
  tornillos.forEach((p, i) => (i % 2 === 0 ? porCara.y : porCara.x).push(p));
  for (const [eje, lista] of Object.entries(porCara)) {
    const im = new THREE.InstancedMesh(cabeza, mat(COLOR.acero, METAL), lista.length);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion();
    lista.forEach((p, i) => {
      // Hacia afuera: segun el signo de la posicion en ese eje.
      const s = eje === 'x' ? Math.sign(p.x) : Math.sign(-p.z);
      const dir = eje === 'x' ? new THREE.Vector3(s, 0, 0) : new THREE.Vector3(0, 0, -s);
      q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
      im.setMatrixAt(i, m.compose(p, q, new THREE.Vector3(1, 1, 1)));
    });
    im.castShadow = false;
    g.add(im);
  }
  // Tacos impresos en las esquinas de arriba (donde entran los tornillos de la tapa).
  const xi = L / 2 - e / 2 - 7, yi = W / 2 - e / 2 - 7;
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) g.add(caja(14 * MM, 14 * MM, 15 * MM, COLOR.impreso, Pm(sx * xi, sy * yi, H - 7.5)));
  // Tapa de policarbonato (3 mm) atornillada: no se puede clicar (deja clicar lo de adentro).
  const tapa = new THREE.Group();
  tapa.name = 'tapa';
  const matTapa = mat(0xdcecf7, { transparent: true, opacity: 0.07, roughness: 0.02, depthWrite: false, side: THREE.DoubleSide });
  const lamina = caja((L + e) * MM, (W + e) * MM, 3 * MM, matTapa, Pm(0, 0, H + 1.5));
  lamina.castShadow = false;
  const cantosTapa = new THREE.LineSegments(new THREE.EdgesGeometry(lamina.geometry), matCanto);
  lamina.add(cantosTapa);
  tapa.add(lamina);
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    tapa.add(cilindro(3.6 * MM, 1.2 * MM, COLOR.acero, Pm(sx * xi, sy * yi, H + 3.6), METAL, 16));
    tapa.add(cilindro(4.6 * MM, 0.6 * MM, 0x111111, Pm(sx * xi, sy * yi, H + 3.1), {}, 16));   // arandela de goma
  }
  // Placa grabada (rotulo) y el aviso de 110 V junto a la entrada de red.
  const placa = planoDibujado(90 * MM, 22 * MM, (ctx, X, Y, k) => {
    ctx.fillStyle = '#1b1f24'; ctx.fillRect(0, 0, 90 * k, 22 * k);
    ctx.strokeStyle = '#c9ccd1'; ctx.lineWidth = 0.4 * k; ctx.strokeRect(1.2 * k, 1.2 * k, 87.6 * k, 19.6 * k);
    ctx.fillStyle = '#e6e8eb'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = `700 ${4.6 * k}px "Space Grotesk", sans-serif`; ctx.fillText(rotulo, X(0), Y(3.5));
    ctx.fillStyle = '#9aa4b1'; ctx.font = `500 ${3 * k}px "IBM Plex Mono", monospace`;
    ctx.fillText('12 V 12,5 A · 110 V~ entrada IEC', X(0), Y(-4.5));
  }, { ppm: 14, fondo: '#1b1f24' });
  placa.position.copy(Pm(-L / 2 + 60, -W / 2 + 20, H + 3.05));
  tapa.add(placa);
  const aviso = planoDibujado(24 * MM, 21 * MM, (ctx, X, Y, k) => {
    ctx.fillStyle = '#f2c21b'; ctx.strokeStyle = '#111'; ctx.lineWidth = 1.4 * k; ctx.lineJoin = 'round';
    ctx.beginPath(); ctx.moveTo(X(0), Y(9.5)); ctx.lineTo(X(11), Y(-9.5)); ctx.lineTo(X(-11), Y(-9.5)); ctx.closePath();
    ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#111'; ctx.font = `800 ${10 * k}px "Space Grotesk", sans-serif`; ctx.textAlign = 'center';
    ctx.textBaseline = 'middle'; ctx.fillText('⚡', X(0), Y(-2.5));
  }, { ppm: 20 });
  aviso.position.copy(Pm(L / 2 - 30, W / 2 - 60, H + 3.05));
  tapa.add(aviso);
  tapa.traverse((o) => { if (o.isMesh || o.isLineSegments) { o.raycast = () => {}; o.castShadow = false; } });
  g.add(tapa);

  // Donde va cada cosa en la pared: (u, z) de la pared -> posicion y giro (la pieza mira a -y).
  const enPared = (pared, u, z) => {
    switch (pared) {
      case 'frente': return { pos: Pm(u, -(W / 2 + e / 2), z), giro: 0 };
      case 'atras': return { pos: Pm(u, W / 2 + e / 2, z), giro: Math.PI };
      case 'izq': return { pos: Pm(-(L / 2 + e / 2), u, z), giro: -Math.PI / 2 };
      default: return { pos: Pm(L / 2 + e / 2, u, z), giro: Math.PI / 2 };
    }
  };
  prensaestopas.forEach((pe, i) => {
    const p = crearPrensaestopas({ tipo: pe.tipo, pared: e, verticesArriba: pe.verticesArriba !== false });
    const { pos, giro } = enPared(pe.pared, pe.u, pe.z);
    p.position.copy(pos);
    p.rotation.y = giro;
    p.name = `prensaestopas_${i}`;
    g.add(p);
    p.updateMatrix();
    for (const [a, sufijo] of [['ancla_afuera', ''], ['ancla_adentro', '_adentro']]) {
      const o = p.getObjectByName(a);
      g.add(ancla(`ancla_prensa_${i}${sufijo}`, o.position.clone().applyMatrix4(p.matrix), { tipo: pe.tipo }));
    }
  });
  if (ventilador) {
    const v = crearVentilador4010({ id: 'ventilador', pared: e });
    const { pos, giro } = enPared(ventilador.pared, ventilador.u, ventilador.z);
    v.position.copy(pos);
    v.rotation.y = giro;
    v.name = 'ventilador';
    g.add(v);
  }
  if (rejilla) {
    // Ranuras cortadas a laser de 3 × (z1 - z0) mm cada 8 mm: se ven por su canto oscuro.
    const { pared, u0, u1, z0, z1 } = rejilla;
    const matRan = mat(0x0d1014, { transparent: true, opacity: 0.55, depthWrite: false });
    const pos = [];
    const lateral = pared === 'izq' || pared === 'der';
    // En el medio del espesor de la pared (enPared da la cara de afuera).
    const hacia = { frente: [0, e / 2], atras: [0, -e / 2], izq: [e / 2, 0], der: [-e / 2, 0] }[pared];
    for (let u = u0; u <= u1 + 1e-6; u += 8) pos.push(enPared(pared, u, (z0 + z1) / 2).pos.add(Pm(hacia[0], hacia[1], 0)));
    const geo = lateral ? new THREE.BoxGeometry((e + 0.4) * MM, (z1 - z0) * MM, 3 * MM) : new THREE.BoxGeometry(3 * MM, (z1 - z0) * MM, (e + 0.4) * MM);
    const im = instancias(geo, matRan, pos, 'rejilla');
    im.raycast = () => {};
    g.add(im);
  }
  terminar(g, { datos: _datos(opciones) });
  g.userData.pieza = 'Gabinete de acrilico 360 × 240 × 80 mm';
  return g;
}

// ---------------------------------------------------------------------------
// Portatil ASUS TUF Gaming A15 (FA507), a su medida real
// ---------------------------------------------------------------------------
// Ficha oficial de ASUS: 359 × 256 × 22,4-24,7 mm, 2,2-2,3 kg, pantalla de 15,6" 16:9 (area activa
// 344,2 × 193,6 mm), teclado con retroiluminacion RGB y numerico, WASD transparentes. Puertos:
// izquierda DC, RJ45, HDMI 2.1, USB-C, USB-A y audio; derecha 2 USB-A. Rejillas de salida de aire
// en las dos esquinas de atras y en el costado izquierdo.
// Aqui se modela a la medida real; el visor lo dibuja ampliado (escala del grupo).
// Origen: centro de la cara de abajo de la base (sin las patas, que bajan 1,5 mm); x a lo ancho del
// portatil (derecha +x), y hacia atras (+y, donde estan las bisagras), z arriba. La tapa gira sobre
// la bisagra: opciones.apertura = radianes que se inclina hacia atras desde la vertical.
// Nodos: tapa, pantalla (MeshBasic con el lienzo del asistente), camara, letras (teclado RGB,
// material con emissiveMap), led_0..led_2 (estado; led_2 = actividad). Anclas: pin_pc_USB1/USB2
// (bocas de los USB de la derecha), ancla_camara.
// userData.laptop = { pantalla, lienzo, textura, matLetras, leds, camara, usbDerecha } para el visor.
const TUF = { ancho: 0.359, fondo: 0.256, base: 0.0167, tapa: 0.007, altoTapa: 0.236, pantalla: [0.3442, 0.1936] };
const COLOR_TUF = { cuerpo: 0x3a3e44, tapa: 0x33373c, oscuro: 0x15171a, tecla: 0x1b1e22, detalle: 0x8b949e };

// Teclado de la TUF A15 (en mm desde el centro del teclado; x a la derecha, y hacia atras): fila de
// funciones baja, bloque principal de 15 unidades, flechas y numerico de 4 columnas.
function teclasTuf() {
  const u = 17.2, t = [];
  const fila = (y, alto, etiquetas, x0 = -168) => {
    let x = x0;
    for (const e of etiquetas) {
      const [txt, ancho = 1] = Array.isArray(e) ? e : [e, 1];
      t.push({ txt, x: x + (ancho * u) / 2, y, w: ancho * u - 2.2, h: alto });
      x += ancho * u;
    }
  };
  fila(47, 9, ['Esc', 'F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12', 'Ins', 'Del',
    'Prt', 'Home', 'End', '⏻'].map((x) => [x, 0.97]));
  fila(33, 15, ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', ['⌫', 2]]);
  fila(16, 15, [['Tab', 1.5], 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', ['\\', 1.5]]);
  fila(-1, 15, [['Caps', 1.75], 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'Ñ', "'", ['Enter', 2.25]]);
  fila(-18, 15, [['Shift', 2.25], 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '-', ['Shift', 1.75], '↑']);
  fila(-35, 15, ['Ctrl', 'Fn', '⊞', 'Alt', ['', 5.5], 'Alt', 'Ctrl', '←', '↓', '→']);
  const np = [['Num', '/', '*', '-'], ['7', '8', '9', '+'], ['4', '5', '6', ''], ['1', '2', '3', 'Ent'], [['0', 2], '.', '']];
  np.forEach((etq, i) => {
    let x = 97;
    for (const e of etq) {
      const [txt, ancho = 1] = Array.isArray(e) ? e : [e, 1];
      if (txt !== '' || i === 4) t.push({ txt, x: x + (ancho * 15) / 2, y: 33 - i * 17, w: ancho * 15 - 2, h: 15 });
      x += ancho * 15;
    }
  });
  return t;
}
const WASD = new Set(['W', 'A', 'S', 'D']);

function _lienzo(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

export function crearLaptopTUFA15(opciones = {}) {
  const { apertura = 0.35 } = opciones;
  const L = TUF, C = COLOR_TUF, mm = 0.001;
  const pc = new THREE.Group();
  pc.name = 'laptop_tuf_a15';
  const metal = { metalness: 0.45, roughness: 0.45 };
  // Base: casco inferior oscuro + cubierta superior gris con esquinas redondeadas; patas de goma.
  pc.add(cajaRedonda(L.ancho, L.fondo, 0.005, 0.012, C.oscuro, P(0, 0, 0)));
  pc.add(cajaRedonda(L.ancho - 0.001, L.fondo - 0.001, L.base - 0.004, 0.011, C.cuerpo, P(0, 0, 0.004), metal));
  // Canto de la cubierta (linea clara de mecanizado alrededor del teclado, como el A15).
  pc.add(cajaRedonda(L.ancho - 0.0045, L.fondo - 0.0045, 0.0003, 0.009, 0x4a4f57, P(0, 0, L.base - 0.0002), metal));
  for (const [x, y] of [[-0.15, -0.1], [0.15, -0.1], [-0.15, 0.1], [0.15, 0.1]])
    pc.add(cajaRedonda(0.05, 0.008, 0.002, 0.003, C.oscuro, P(x, y, -0.0015)));
  // Rejillas de salida de aire: las dos esquinas de atras (panel en angulo del A15) y el costado izquierdo.
  const matRej = mat(0x0a0b0d, { roughness: 0.9 });
  for (const s of [-1, 1]) {
    for (let i = 0; i < 11; i++) pc.add(caja(0.0032, 0.0012, 0.0085, matRej, P(s * (0.105 + i * 0.0062), L.fondo / 2 + 0.0002, 0.0085)));
  }
  pc.add(caja(0.12, 0.0008, 0.011, C.oscuro, P(0, L.fondo / 2 + 0.0001, 0.0085)));   // panel del medio (bisagra)
  for (let i = 0; i < 12; i++) pc.add(caja(0.0012, 0.0035, 0.006, matRej, P(-L.ancho / 2 - 0.0002, 0.03 + i * 0.007, 0.009)));
  // Placa del teclado + teclas en relieve. La placa asoma 0,2 mm sobre el canto de la cubierta
  // (antes su cara de arriba quedaba EXACTAMENTE a la altura del canto, L.base + 0,1 mm, y las dos
  // se turnaban al mover la camara: el "parpadeo del interior del teclado", 2026-09-28). Las
  // teclas arrancan dentro de la placa.
  const zTec = L.base + 0.0002;
  pc.add(caja(0.33, 0.112, 0.0006, C.oscuro, P(0, 0.052, L.base)));
  const teclas = teclasTuf();
  const kc = new THREE.Vector2(0, 0.052);
  const matTecla = mat(C.tecla, { roughness: 0.7 });
  const matWasd = mat(0x9fb3c8, { transparent: true, opacity: 0.8, roughness: 0.2 });
  for (const k of teclas) {
    const esWasd = WASD.has(k.txt);
    pc.add(cajaRedonda(k.w * mm, k.h * mm, 0.0014, 0.0012, esWasd ? matWasd : matTecla, P(kc.x + k.x * mm, kc.y + k.y * mm, zTec)));
  }
  // Letras: un lienzo encima de las teclas. Es tambien el mapa de luz del teclado RGB (emissiveMap).
  const lz = _lienzo(2048, 704);
  const cx = lz.getContext('2d');
  const Wl = 0.36, Hl = 0.124;
  const px = (x) => (x * mm + Wl / 2) / Wl * lz.width, py = (y) => (Hl / 2 - y * mm) / Hl * lz.height;
  cx.fillStyle = '#000'; cx.fillRect(0, 0, lz.width, lz.height);
  cx.textAlign = 'center'; cx.textBaseline = 'middle'; cx.fillStyle = '#fff';
  for (const k of teclas) {
    if (!k.txt) continue;
    const s = k.txt.length > 3 ? 26 : k.txt.length > 1 ? 30 : 40;
    cx.font = `600 ${s}px "Space Grotesk", sans-serif`;
    cx.fillText(k.txt, px(k.x), py(k.y));
  }
  const texLetras = new THREE.CanvasTexture(lz);
  texLetras.colorSpace = THREE.SRGBColorSpace;
  const matLetras = new THREE.MeshStandardMaterial({ color: 0x000000, transparent: true, alphaMap: texLetras,
    emissive: 0xffffff, emissiveMap: texLetras, emissiveIntensity: 0.55, depthWrite: false });
  const letras = new THREE.Mesh(new THREE.PlaneGeometry(Wl, Hl), matLetras);
  letras.name = 'letras';
  letras.rotation.x = -Math.PI / 2;
  letras.position.copy(P(0, 0.052, zTec + 0.0016));
  pc.add(letras);
  // Touchpad (con la linea de los botones), reposamanos con franja y luces de estado.
  pc.add(cajaRedonda(0.11, 0.07, 0.0006, 0.006, 0x2d3137, P(-0.042, -0.078, L.base), { roughness: 0.3 }));
  pc.add(caja(0.108, 0.0004, 0.0002, 0x1b1e22, P(-0.042, -0.1, L.base + 0.0007)));
  pc.add(caja(0.3, 0.0008, 0.0003, 0x6e7681, P(0, -0.115, L.base + 0.0002)));
  // Rebaje para abrir la tapa (muesca del frente).
  pc.add(caja(0.06, 0.0015, 0.0025, C.oscuro, P(0, -L.fondo / 2 - 0.0001, L.base - 0.0014)));
  const leds = [0x3fb68b, 0x3fb68b, 0xf2b134].map((c, i) => {
    const l = new THREE.Mesh(new THREE.CylinderGeometry(0.0012, 0.0012, 0.0005, 10),
      new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: i < 2 ? 0.8 : 0.1 }));
    l.name = `led_${i}`;
    l.position.copy(P(-0.155 + i * 0.006, -L.fondo / 2 + 0.006, L.base + 0.0002));
    pc.add(l);
    return l;
  });
  // Puertos: boca negra hundida y, adentro, la lengueta (azul en los USB 3.2).
  const puerto = (x, y, z, sx, sy, sz, c) => {
    pc.add(caja(sx + 0.0012, sy + 0.0012, sz + 0.0012, 0x050506, P(x, y, z)));
    if (c !== 0x1d2129) pc.add(caja(sx + 0.0014, sy * 0.72, sz * 0.32, c, P(x, y, z + sz * 0.12)));
  };
  const xi = -L.ancho / 2 - 0.0003, xd = L.ancho / 2 + 0.0003;
  [[0.075, 0.006, 0.006, 'cil'], [0.05, 0.016, 0.012, 0x1d2129], [0.028, 0.015, 0.006, 0x1d2129],
    [0.012, 0.009, 0.0035, 0x1d2129], [-0.006, 0.013, 0.005, 0x2d6fd0], [-0.03, 0.006, 0.006, 'cil']].forEach(([y, a, h, c]) => {
    if (c === 'cil') {
      const d = new THREE.Mesh(new THREE.CylinderGeometry(a / 2, a / 2, 0.003, 16), mat(0x0b0c0e));
      d.rotation.z = Math.PI / 2;
      d.position.copy(P(xi, y, 0.009));
      pc.add(d);
    } else puerto(xi, y, 0.009, 0.0012, a, h, c);
  });
  const usbDerecha = [[-0.02, 0.013], [0.0, 0.013]];
  for (const [y, a] of usbDerecha) puerto(xd, y, 0.009, 0.0012, a, 0.005, 0x2d6fd0);
  usbDerecha.forEach(([y], i) => pc.add(ancla(`pin_pc_USB${i + 1}`, P(xd + 0.0006, y, 0.009), { pin: `USB${i + 1}` })));
  // Bisagras: dos ejes y la cubierta de la bisagra de lado a lado (la del A15 es una barra).
  const yBis = L.fondo / 2 - 0.006, zBis = L.base + 0.003;
  for (const x of [-0.13, 0.13]) {
    const b = new THREE.Mesh(new THREE.CylinderGeometry(0.0045, 0.0045, 0.05, 16), mat(C.oscuro, metal));
    b.rotation.z = Math.PI / 2;
    b.position.copy(P(x, yBis, zBis));
    pc.add(b);
  }
  const barra = new THREE.Mesh(new THREE.CylinderGeometry(0.0042, 0.0042, 0.205, 16), mat(0x202328, metal));
  barra.rotation.z = Math.PI / 2;
  barra.position.copy(P(0, yBis, zBis));
  pc.add(barra);
  // Tapa: gira sobre la bisagra. Por fuera, aluminio con el logo y las lineas diagonales del A15;
  // por dentro, el marco negro delgado, la camara y la pantalla.
  const tapa = new THREE.Group();
  tapa.name = 'tapa';
  tapa.position.copy(P(0, yBis, zBis));
  tapa.rotation.x = -apertura;
  const cara = cajaRedonda(L.ancho, L.altoTapa, L.tapa, 0.01, C.tapa, null, metal);
  cara.rotation.x = Math.PI / 2;
  cara.position.copy(P(0, L.tapa, L.altoTapa / 2));
  tapa.add(cara);
  const marco = new THREE.Mesh(new THREE.PlaneGeometry(L.ancho - 0.004, L.altoTapa - 0.004), mat(0x07080a, { roughness: 0.2 }));
  marco.position.copy(P(0, -0.0004, L.altoTapa / 2));
  tapa.add(marco);
  const cam = new THREE.Mesh(new THREE.CircleGeometry(0.0015, 16), mat(0x1f3a5f, { metalness: 0.8, roughness: 0.1 }));
  cam.name = 'camara';
  cam.position.copy(P(0, -0.0006, L.altoTapa - 0.006));
  tapa.add(cam);
  tapa.add(ancla('ancla_camara', P(0, -0.0006, L.altoTapa - 0.006)));
  // Logo TUF por fuera y lineas diagonales en la esquina (lienzo).
  const lg = _lienzo(512, 256);
  const g2 = lg.getContext('2d');
  g2.strokeStyle = '#aab3bd'; g2.lineWidth = 10;
  g2.beginPath();
  for (let i = 0; i < 6; i++) { const a = Math.PI / 6 + i * Math.PI / 3; g2.lineTo(128 + 90 * Math.cos(a), 128 + 90 * Math.sin(a)); }
  g2.closePath(); g2.stroke();
  g2.fillStyle = '#aab3bd'; g2.font = '800 96px "Space Grotesk", sans-serif'; g2.textAlign = 'center'; g2.textBaseline = 'middle';
  g2.fillText('TUF', 128, 132);
  g2.font = '700 54px "Space Grotesk", sans-serif'; g2.textAlign = 'left'; g2.fillText('GAMING', 250, 132);
  const texLogo = new THREE.CanvasTexture(lg);
  texLogo.colorSpace = THREE.SRGBColorSpace;
  const logo = new THREE.Mesh(new THREE.PlaneGeometry(0.1, 0.05), new THREE.MeshStandardMaterial({ map: texLogo,
    transparent: true, metalness: 0.6, roughness: 0.3 }));
  logo.position.copy(P(0, L.tapa + 0.0015, L.altoTapa * 0.55));
  logo.rotation.y = Math.PI;
  tapa.add(logo);
  const ld = _lienzo(512, 512);
  const g4 = ld.getContext('2d');
  g4.strokeStyle = 'rgba(160,170,182,0.55)'; g4.lineWidth = 5;
  for (let i = 0; i < 9; i++) { g4.beginPath(); g4.moveTo(40 + i * 52, 0); g4.lineTo(0, 40 + i * 52); g4.stroke(); }
  const texDiag = new THREE.CanvasTexture(ld);
  texDiag.colorSpace = THREE.SRGBColorSpace;
  const diag = new THREE.Mesh(new THREE.PlaneGeometry(0.08, 0.08), new THREE.MeshStandardMaterial({ map: texDiag,
    transparent: true, metalness: 0.6, roughness: 0.35, depthWrite: false }));
  diag.position.copy(P(L.ancho / 2 - 0.045, L.tapa + 0.0015, L.altoTapa - 0.045));
  diag.rotation.y = Math.PI;
  tapa.add(diag);
  // Pantalla: el asistente (lienzo 1920 x 1080, la misma proporcion que el panel real).
  const lienzo = _lienzo(1920, 1080);
  const textura = new THREE.CanvasTexture(lienzo);
  textura.colorSpace = THREE.SRGBColorSpace;
  textura.anisotropy = 8;
  const pantalla = new THREE.Mesh(new THREE.PlaneGeometry(...L.pantalla), new THREE.MeshBasicMaterial({ map: textura }));
  pantalla.name = 'pantalla';
  pantalla.position.copy(P(0, -0.0008, 0.018 + L.pantalla[1] / 2));
  pantalla.userData.asistente = true;
  tapa.add(pantalla);
  // "TUF GAMING" en el marco de abajo.
  const eb = _lienzo(512, 64);
  const g3 = eb.getContext('2d');
  g3.fillStyle = '#6e7681'; g3.font = '700 40px "Space Grotesk", sans-serif'; g3.textAlign = 'center'; g3.textBaseline = 'middle';
  g3.fillText('TUF GAMING', 256, 34);
  const texEb = new THREE.CanvasTexture(eb);
  const rot = new THREE.Mesh(new THREE.PlaneGeometry(0.05, 0.00625), new THREE.MeshBasicMaterial({ map: texEb, transparent: true }));
  rot.position.copy(P(0, -0.0008, 0.0085));
  tapa.add(rot);
  pc.add(tapa);
  terminar(pc, { datos: _datos(opciones) });
  pc.userData.pieza = 'ASUS TUF Gaming A15';
  pc.userData.laptop = { pantalla, lienzo, textura, matLetras, leds, camara: cam, usbDerecha };
  return pc;
}
