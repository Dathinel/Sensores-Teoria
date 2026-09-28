// Piezas electronicas del visor 3D: placas y modulos con sus pines como anclas.
// Convencion: ver README.md de esta carpeta. Marco de la simulacion (x largo, y ancho,
// z arriba), metros; las medidas de ficha tecnica van en mm y se pasan con MM.
//
// Contenido (agregar funciones nuevas AL FINAL, cada una con su bloque de comentarios):
//   crearESP32DevKit(opciones)      ESP32 DevKit V1 de 30 o 38 pines (pieza piloto)
//   crearESP32DevKit30P(opciones)   atajo, 30 pines (DOIT, el de los labs y el del carro)
//   crearESP32DevKit38P(opciones)   atajo, 38 pines (DevKitC, el de la caja de control)
//   --- A4 (resto de la electronica; convencion comun al inicio de su bloque) ---
//   crearPlacaGVS / crearPlacaGVS30P / crearPlacaGVS38P   placa de expansion G-V-S con su ESP32
//   crearTB6612FNG                  puente H del carro
//   crearDriverPasoAPaso / crearA4988 / crearTMC2208      driver StepStick suelto
//   crearPlacaDriversPasoAPaso      placa perforada con los 2 drivers de las cintas
//   crearPCA9685, crearULN2003, crearPlacaOptoPC817, crearRepartoI2C
//   crearBuckXL4016 (6 V servos), crearBuckLM2596 (5 V), crearFuenteLRS150 (12 V)
//   crearPortafusibles4, crearBorneraDIN16, crearEntradaIEC, crearHubUSB4
//   crearInterruptorFusible, crearPortaBaterias18650x2    (carro)
//   crearNEMA17, crear28BYJ48, crearServo / crearServoSG90 / crearServoMG996R

import * as THREE from 'three';
import { MM, COLOR, METAL, PLASTICO, P, mat, caja, cilindro, ancla, instancias, planoDibujado, terminar } from './base.js';

export const PASO_PIN = 2.54;   // mm, paso de los headers

// ---------------------------------------------------------------------------
// ESP32 DevKit V1
// ---------------------------------------------------------------------------
//
// Pinout REAL (no espejado; ver "Lecciones aprendidas" de GUIA_BLENDER_MCP.md): con la antena
// ARRIBA y los componentes hacia quien mira, el header de EN queda a la IZQUIERDA. En esta
// pieza la antena apunta a -x y el USB a +x, asi que ese header queda en -y. Cada lista va de
// la antena al USB, con los mismos nombres que sim/conexiones.py (G34, TX, 3V3...).
export const PINOUT_ESP32 = {
  30: {
    ladoEN: ['EN', 'G36', 'G39', 'G34', 'G35', 'G32', 'G33', 'G25', 'G26', 'G27', 'G14', 'G12', 'G13', 'GND', 'VIN'],
    lado23: ['G23', 'G22', 'TX', 'RX', 'G21', 'G19', 'G18', 'G5', 'G17', 'G16', 'G4', 'G2', 'G15', 'GND', '3V3'],
    // PCB 28,3 × 51,5 × 1,6 mm (catalogo ESP32_30P, DOIT DevKit V1). El ultimo pin queda a
    // 2,8 mm del borde del USB; la antena del WROOM llega al otro borde.
    largo: 51.5, ancho: 28.3, ultimoPinAlBorde: 2.8,
  },
  38: {
    ladoEN: ['3V3', 'EN', 'G36', 'G39', 'G34', 'G35', 'G32', 'G33', 'G25', 'G26', 'G27', 'G14', 'G12',
      'GND', 'G13', 'SD2', 'SD3', 'CMD', '5V'],
    lado23: ['GND', 'G23', 'G22', 'TX', 'RX', 'G21', 'GND', 'G19', 'G18', 'G5', 'G17', 'G16', 'G4', 'G0',
      'G2', 'G15', 'SD1', 'SD0', 'CLK'],
    // ESP32-DevKitC de 38 pines: 55 × 28 mm (ficha de Espressif: 54,4 × 27,9).
    largo: 55.0, ancho: 28.0, ultimoPinAlBorde: 2.6,
  },
};
const SEP_FILAS = 25.4;          // mm entre los dos headers (1 pulgada)
const T_PCB = 1.6;               // mm
const PIN_ABAJO = 8.5;           // mm que baja la punta del pin macho bajo la placa
const SEPARADOR = 2.5;           // mm del plastico negro del header macho

// Nombre del pin como lo imprime la serigrafia real del DOIT (D34, VP, TX0...).
function rotulo(n, pines) {
  const m = n.match(/^G(\d+)$/);
  if (!m) return { TX: 'TX0', RX: 'RX0' }[n] || n;
  const g = +m[1];
  if (g === 36) return 'VP';
  if (g === 39) return 'VN';
  if (pines === 30 && g === 17) return 'TX2';
  if (pines === 30 && g === 16) return 'RX2';
  return 'D' + g;
}

// ESP32 DevKit V1 (30 o 38 pines) armado con sus piezas reales.
//
// Origen (punto de montaje): el CENTRO del campo de pines, en la cara de ABAJO del PCB. Asi
// la pieza se apoya sobre dos headers hembra (placa GVS, protoboard) poniendo el origen a la
// altura del tope de los headers + el separador del macho (2,5 mm), centrado entre sus filas.
// Antena hacia -x, USB hacia +x, componentes hacia +z.
//
// opciones:
//   pines: 30 | 38 (30)       usb: 'micro' | 'c' ('micro'; el DOIT de los labs es micro-USB)
//   modulo: prefijo de las anclas de pines ('ESP32' -> pin_ESP32_G34)
//   serigrafia: true          conPines: true (los pines macho de abajo)
//   idComponente, sensorId: van en userData de todas las mallas
//
// Nodos con nombre: pcb, modulo_wroom, blindaje, boton_EN, boton_BOOT, usb, led_power,
// led_gpio2 (el azul del GPIO2: `grupo.getObjectByName('led_gpio2').material.color` para
// encenderlo), cp2102, ams1117.
// Anclas: pin_<modulo>_<PIN> en la PUNTA de cada pin macho (los GND repetidos: GND, GND_2,
// GND_3), con userData {pin, rotulo, lado: 'EN'|'23', indice}; ancla_usb (boca del conector),
// ancla_antena (punta de la antena) y ancla_centro_pcb (centro de la cara de arriba).
export function crearESP32DevKit(opciones = {}) {
  const { pines = 30, usb = 'micro', modulo = 'ESP32', serigrafia = true, conPines = true } = opciones;
  const def = PINOUT_ESP32[pines];
  if (!def) throw new Error(`ESP32 DevKit de ${pines} pines: no existe (30 o 38)`);
  const n = def.ladoEN.length;
  const { largo: L, ancho: W } = def;
  // Centro del PCB en el marco de la pieza (el origen es el centro del campo de pines).
  const xPcb = -((L / 2 - def.ultimoPinAlBorde) - (n - 1) * PASO_PIN / 2);
  const X = (xDesdeCentroPcb) => xPcb + xDesdeCentroPcb;     // mm
  const xAntena = X(-L / 2), xUsb = X(L / 2);
  const Q = (x, y, z) => P(x * MM, y * MM, z * MM);           // mm de la pieza -> Three
  const zTop = T_PCB;

  const g = new THREE.Group();
  g.name = `esp32_devkit_${pines}p`;

  // PCB negro mate (el DOIT es negro; el DevKitC de Espressif, tambien).
  const pcb = caja(L * MM, W * MM, T_PCB * MM, COLOR.pcb_negro, Q(xPcb, 0, T_PCB / 2), { roughness: 0.75 });
  pcb.name = 'pcb';
  g.add(pcb);

  // Modulo ESP-WROOM-32: 18 × 25,5 × 3,1 mm; su antena (6,2 mm de PCB sin blindaje) llega
  // al borde de la placa. Encima, el blindaje metalico de 17,6 × 15,8 × 2,3 mm.
  const wroom = new THREE.Group();
  wroom.name = 'modulo_wroom';
  const xMod = xAntena + 25.5 / 2;
  wroom.add(caja(25.5 * MM, 18 * MM, 0.8 * MM, 0x1b1f24, Q(xMod, 0, zTop + 0.4)));
  const blindaje = caja(17.6 * MM, 15.8 * MM, 2.3 * MM, COLOR.plata, Q(xAntena + 6.9 + 17.6 / 2, 0, zTop + 0.8 + 1.15), METAL);
  blindaje.name = 'blindaje';
  wroom.add(blindaje);
  // Antena en zigzag (dorada) y rotulo grabado en el blindaje.
  const antena = planoDibujado(6.2 * MM, 18 * MM, (ctx, x, y, k) => {
    ctx.strokeStyle = '#c9a23a'; ctx.lineWidth = 0.55 * k; ctx.beginPath();
    ctx.moveTo(x(2.6), y(-7.5));
    for (let i = 0; i < 7; i++) { const yy = -7.5 + i * 2.2; ctx.lineTo(x(-2.3), y(yy)); ctx.lineTo(x(-2.3), y(yy + 1.1)); ctx.lineTo(x(2.3), y(yy + 1.1)); ctx.lineTo(x(2.3), y(yy + 2.2)); }
    ctx.stroke();
  }, { ppm: 24 });
  antena.position.copy(Q(xAntena + 3.1, 0, zTop + 0.81));
  wroom.add(antena);
  const grabado = planoDibujado(17.6 * MM, 15.8 * MM, (ctx, x, y, k) => {
    ctx.fillStyle = 'rgba(60,64,70,0.85)'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = `700 ${1.9 * k}px "IBM Plex Mono", monospace`;
    ctx.fillText('ESP-WROOM-32', x(0), y(3));
    ctx.font = `500 ${1.2 * k}px "IBM Plex Mono", monospace`;
    ctx.fillText('ESPRESSIF', x(0), y(0.3));
    ctx.fillText('FCC ID: 2AC7Z-ESPWROOM32', x(0), y(-2.2));
  }, { ppm: 24 });
  grabado.position.copy(Q(xAntena + 6.9 + 17.6 / 2, 0, zTop + 0.8 + 2.3 + 0.02));
  wroom.add(grabado);
  g.add(wroom);

  // Conversor USB-serie CP2102 (QFN 5 × 5 mm) y regulador AMS1117-3.3 (SOT-223).
  const cp = caja(5 * MM, 5 * MM, 0.9 * MM, COLOR.chip, Q(X(L / 2 - 14), 4.5, zTop + 0.45), { roughness: 0.5 });
  cp.name = 'cp2102';
  g.add(cp);
  const ams = new THREE.Group();
  ams.name = 'ams1117';
  ams.add(caja(6.5 * MM, 3.5 * MM, 1.6 * MM, COLOR.chip, Q(X(L / 2 - 21), -6.5, zTop + 0.8), { roughness: 0.5 }));
  ams.add(caja(3.0 * MM, 1.2 * MM, 0.25 * MM, COLOR.estano, Q(X(L / 2 - 21), -4.2, zTop + 0.13), METAL));   // aleta
  for (const dx of [-2.3, 0, 2.3]) ams.add(caja(0.7 * MM, 1.6 * MM, 0.25 * MM, COLOR.estano, Q(X(L / 2 - 21) + dx, -9.0, zTop + 0.13), METAL));
  g.add(ams);

  // Botones EN (reset, del lado del header de EN) y BOOT, a los lados del USB.
  for (const [nombre, s] of [['EN', -1], ['BOOT', 1]]) {
    const b = new THREE.Group();
    b.name = `boton_${nombre}`;
    b.add(caja(4.2 * MM, 3.2 * MM, 1.4 * MM, COLOR.plata, Q(X(L / 2 - 4.5), s * 8.6, zTop + 0.7), METAL));
    b.add(cilindro(0.9 * MM, 0.8 * MM, COLOR.plastico_negro, Q(X(L / 2 - 4.5), s * 8.6, zTop + 1.8), {}, 16));
    g.add(b);
  }

  // Conector USB (boca hacia +x), sobresale 0,8 mm del borde como en la placa real.
  const [uL, uW, uH] = usb === 'c' ? [7.3, 8.9, 3.2] : [5.6, 7.5, 2.7];
  const conector = caja(uL * MM, uW * MM, uH * MM, COLOR.plata, Q(xUsb - uL / 2 + 0.8, 0, zTop + uH / 2), METAL);
  conector.name = 'usb';
  g.add(conector);
  g.add(caja(0.2 * MM, (uW - 1.4) * MM, (uH - 1.2) * MM, 0x0a0a0a, Q(xUsb + 0.81, 0, zTop + uH / 2)));   // boca

  // LEDs 0603: rojo de encendido y azul del GPIO2. Material basico (no les afecta la luz ni el
  // resaltado del visor, que solo toca materiales con `emissive`).
  const led = (nombre, color, y) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(1.6 * MM, 0.55 * MM, 0.8 * MM), new THREE.MeshBasicMaterial({ color }));
    m.position.copy(Q(X(L / 2 - 9.5), y, zTop + 0.28));
    m.name = nombre;
    g.add(m);
  };
  led('led_power', 0xff3b30, -3.2);
  led('led_gpio2', 0x0a2a5a, 3.2);   // apagado; encendido: 0x3d8bff

  // Pasivos 0805/0603 alrededor del regulador y del CP2102 (solo aspecto).
  const pasivos = [[L / 2 - 17, -2.5], [L / 2 - 17, -0.5], [L / 2 - 25, -2], [L / 2 - 11, 8.8], [L / 2 - 13, -8.8], [L / 2 - 26.5, 5.5]];
  for (const [x, y] of pasivos) g.add(caja(2.0 * MM, 1.25 * MM, 0.6 * MM, 0xb59a6a, Q(X(x), y, zTop + 0.3)));

  // Headers macho: un plastico negro por fila bajo la placa y los pines dorados (instanciados).
  const xs = Array.from({ length: n }, (_, i) => (i - (n - 1) / 2) * PASO_PIN);
  if (conPines) {
    for (const s of [-1, 1]) g.add(caja(n * PASO_PIN * MM, 2.5 * MM, SEPARADOR * MM, COLOR.plastico_negro, Q(0, s * SEP_FILAS / 2, -SEPARADOR / 2)));
    const largoPin = T_PCB + 0.6 + PIN_ABAJO;
    const posiciones = [], soldaduras = [];
    for (const s of [-1, 1]) for (const x of xs) {
      posiciones.push(Q(x, s * SEP_FILAS / 2, T_PCB + 0.6 - largoPin / 2));
      soldaduras.push(Q(x, s * SEP_FILAS / 2, T_PCB + 0.2));
    }
    g.add(instancias(new THREE.BoxGeometry(0.64 * MM, largoPin * MM, 0.64 * MM), mat(COLOR.dorado, METAL), posiciones, 'pines'));
    g.add(instancias(new THREE.CylinderGeometry(0.85 * MM, 1.0 * MM, 0.4 * MM, 10), mat(COLOR.estano, METAL), soldaduras, 'soldaduras'));
  }

  // Anclas de los pines: en la punta de cada pin macho.
  const vistos = {};
  for (const [lado, lista, s] of [['EN', def.ladoEN, -1], ['23', def.lado23, 1]]) {
    lista.forEach((nom, i) => {
      vistos[nom] = (vistos[nom] || 0) + 1;
      const sufijo = vistos[nom] > 1 ? `_${vistos[nom]}` : '';
      g.add(ancla(`pin_${modulo}_${nom}${sufijo}`, Q(xs[i], s * SEP_FILAS / 2, -PIN_ABAJO),
        { pin: nom, rotulo: rotulo(nom, pines), lado, indice: i }));
    });
  }
  g.add(ancla('ancla_usb', Q(xUsb + 0.8, 0, zTop + uH / 2)));
  g.add(ancla('ancla_antena', Q(xAntena, 0, zTop + 0.8)));
  g.add(ancla('ancla_centro_pcb', Q(xPcb, 0, zTop)));

  // Serigrafia: anillos de los pines, su rotulo hacia adentro (leido a lo ancho, como en la
  // placa real con el USB abajo), EN/BOOT junto a los botones y el nombre de la placa.
  if (serigrafia) {
    const s = planoDibujado(L * MM, W * MM, (ctx, x, y, k) => {
      const xp = (xm) => x(xm - xPcb);   // mm de la pieza -> pixeles (el plano va centrado en el PCB)
      ctx.textBaseline = 'middle';
      ctx.font = `600 ${1.25 * k}px "IBM Plex Mono", monospace`;
      for (const [lista, sgn] of [[def.ladoEN, -1], [def.lado23, 1]]) lista.forEach((nom, i) => {
        ctx.strokeStyle = '#c9a23a'; ctx.lineWidth = 0.35 * k;
        ctx.beginPath(); ctx.arc(xp(xs[i]), y(sgn * SEP_FILAS / 2), 0.85 * k, 0, 2 * Math.PI); ctx.stroke();
        ctx.save();
        ctx.translate(xp(xs[i]), y(sgn * (SEP_FILAS / 2 - 1.6)));
        ctx.rotate(-Math.PI / 2);
        ctx.fillStyle = '#f4f4f4';
        ctx.textAlign = sgn > 0 ? 'right' : 'left';
        ctx.fillText(rotulo(nom, pines), 0, 0);
        ctx.restore();
      });
      ctx.fillStyle = '#f4f4f4'; ctx.textAlign = 'center';
      ctx.font = `600 ${1.1 * k}px "IBM Plex Mono", monospace`;
      ctx.fillText('EN', xp(X(L / 2 - 4.5)), y(-5.9));
      ctx.fillText('BOOT', xp(X(L / 2 - 4.5)), y(5.9));
      ctx.font = `700 ${1.5 * k}px "Space Grotesk", sans-serif`;
      ctx.save(); ctx.translate(xp(X(L / 2 - 30)), y(0)); ctx.rotate(-Math.PI / 2);
      ctx.fillText(pines === 30 ? 'ESP32 DEVKIT V1' : 'ESP32-DevKitC', 0, 0); ctx.restore();
    }, { ppm: 22 });
    s.position.copy(Q(xPcb, 0, zTop + 0.1));
    g.add(s);
  }

  terminar(g, { datos: { ...(opciones.idComponente ? { idComponente: opciones.idComponente } : {}), ...(opciones.sensorId ? { sensorId: opciones.sensorId } : {}) } });
  g.userData.pieza = `ESP32 DevKit ${pines}P`;
  return g;
}

export const crearESP32DevKit30P = (opciones = {}) => crearESP32DevKit({ ...opciones, pines: 30 });
export const crearESP32DevKit38P = (opciones = {}) => crearESP32DevKit({ ...opciones, pines: 38 });

// ---------------------------------------------------------------------------
// (A4 "electronica": agregar aqui abajo el resto de modulos — TB6612, A4988/TMC2208,
// PCA9685, fuente, buck, hub USB... — con la misma forma: comentario de medidas y de donde
// salen, `export function crearX(opciones) -> THREE.Group`, anclas pin_<MODULO>_<PIN>.)
// ---------------------------------------------------------------------------

// ===========================================================================
// A4 · Resto de la electronica del proyecto (placas, drivers, fuentes, motores, servos)
// ===========================================================================
//
// Convencion comun de las piezas de aqui abajo (si una funcion dice otra cosa, manda ella):
// - Origen (punto de montaje) = CENTRO de la cara de ABAJO de la placa o del cuerpo, igual que
//   `construirModulo` de visor.js: se reemplaza `construirModulo(dev, padre, pos, quat)` por
//   `crearX({ id: dev })` con la misma pos/quat. x a lo largo, y a lo ancho, z arriba (mm*MM).
// - Las (x, y) de cada pin son las de sim/conexiones.py (PLANTILLAS), para que el cableado de la
//   simulacion caiga en el mismo lugar (excepcion documentada: la placa GVS, ver su nota).
// - Anclas `pin_<id>_<PIN>` (PIN = nombre de conexiones.py; `id` = el dispositivo, p. ej.
//   `pin_pca9685_PWM3`, `pin_buck6_OUT+`) en la PUNTA del pin o en la BOCA del borne, con
//   userData { pin, dir } (dir = THREE.Vector3 local hacia donde sale el cable, como sensores.js).
// - opciones comunes: id (prefijo de las anclas), idComponente, sensorId, serigrafia (true).

const Pm = (x, y, z) => P(x * MM, y * MM, z * MM);                 // mm de la pieza -> Three
const Dm = (dx, dy, dz) => P(dx, dy, dz).normalize();              // direccion (sim) -> Three

function _datos(o) {
  return { ...(o.idComponente ? { idComponente: o.idComponente } : {}), ...(o.sensorId ? { sensorId: o.sensorId } : {}) };
}
function _fin(g, o, pieza) { terminar(g, { datos: _datos(o) }); g.userData.pieza = pieza; return g; }
function _pin(g, id, n, pos, dir, extra = {}) { g.add(ancla(`pin_${id}_${n}`, pos, { pin: n, dir, ...extra })); }

// Caja / cilindros en mm, centrados en (x, y, z) mm.
function _cj(g, sx, sy, sz, color, x, y, z, extra, nombre) {
  const m = caja(sx * MM, sy * MM, sz * MM, color, Pm(x, y, z), extra);
  if (nombre) m.name = nombre;
  g.add(m);
  return m;
}
function _ci(g, r, h, color, x, y, z, extra, seg = 24, nombre) {           // eje z (vertical)
  const m = cilindro(r * MM, h * MM, color, Pm(x, y, z), extra, seg);
  if (nombre) m.name = nombre;
  g.add(m);
  return m;
}
function _ciX(g, r, h, color, x, y, z, extra, seg = 24) { const m = _ci(g, r, h, color, x, y, z, extra, seg); m.rotation.z = Math.PI / 2; return m; }
function _ciY(g, r, h, color, x, y, z, extra, seg = 24) { const m = _ci(g, r, h, color, x, y, z, extra, seg); m.rotation.x = Math.PI / 2; return m; }

// Prisma de un contorno (x, y en mm) extruido en z desde zBase `alto` mm.
function _prisma(g, puntos, alto, color, zBase, extra, nombre) {
  const s = new THREE.Shape(puntos.map(([x, y]) => new THREE.Vector2(x * MM, y * MM)));
  const geo = new THREE.ExtrudeGeometry(s, { depth: alto * MM, bevelEnabled: false });
  geo.rotateX(-Math.PI / 2);                                        // (x, y, z) local -> (x, z, -y) Three
  const m = new THREE.Mesh(geo, color && color.isMaterial ? color : mat(color, extra));
  m.position.copy(Pm(0, 0, zBase));
  if (nombre) m.name = nombre;
  g.add(m);
  return m;
}
// Chamfer: cuadrado de lado `a` con esquinas cortadas `c` (NEMA17).
const _cuadradoChaflan = (a, c) => {
  const h = a / 2;
  return [[-h + c, -h], [h - c, -h], [h, -h + c], [h, h - c], [h - c, h], [-h + c, h], [-h, h - c], [-h, -h + c]];
};

// Serigrafia sobre la cara de arriba (zTop) de una placa L × W mm centrada en (cx, cy).
function _serigrafia(g, L, W, zTop, dibujar, { cx = 0, cy = 0, ppm = 18, fondo = null } = {}) {
  const s = planoDibujado(L * MM, W * MM, dibujar, { ppm, fondo });
  s.position.copy(Pm(cx, cy, zTop + 0.03));
  s.name = 'serigrafia';
  g.add(s);
  return s;
}
function _texto(ctx, t, x, y, k, { tam = 1.2, color = '#f2f2f2', peso = 600, alinear = 'center', giro = 0, fuente = 'IBM Plex Mono' } = {}) {
  ctx.save();
  ctx.translate(x, y); ctx.rotate(giro);
  ctx.fillStyle = color; ctx.textAlign = alinear; ctx.textBaseline = 'middle';
  ctx.font = `${peso} ${tam * k}px "${fuente}", monospace`;
  ctx.fillText(t, 0, 0);
  ctx.restore();
}
// Agujeros de montaje dibujados (anillo de estano + hueco oscuro).
function _agujeros(ctx, x, y, k, lista, r = 1.6) {
  for (const [ax, ay] of lista) {
    ctx.fillStyle = '#c8c8c8'; ctx.beginPath(); ctx.arc(x(ax), y(ay), (r + 0.9) * k, 0, 2 * Math.PI); ctx.fill();
    ctx.fillStyle = '#050505'; ctx.beginPath(); ctx.arc(x(ax), y(ay), r * k, 0, 2 * Math.PI); ctx.fill();
  }
}

// PCB rectangular (L × W × T mm) con la cara de abajo en z = 0.
function _pcb(g, L, W, color, T = T_PCB) {
  return _cj(g, L, W, T, color, 0, 0, T / 2, { roughness: 0.75 }, 'pcb');
}

// Header macho recto: plastico de 2,5 mm sobre la cara (zBase) y pin de 0,64 mm que sobresale
// `largo` mm por encima del plastico (o por debajo si `abajo`). Ancla en la punta.
// pines: [{ n, x, y, color?, datos? }]
function _headerMacho(g, pines, id, zBase, { abajo = false, largo = 6, anclas = true } = {}) {
  const s = abajo ? -1 : 1, sep = SEPARADOR;
  const porColor = new Map(), pos = [], sold = [];
  for (const p of pines) {
    const c = p.color ?? COLOR.plastico_negro;
    if (!porColor.has(c)) porColor.set(c, []);
    porColor.get(c).push(Pm(p.x, p.y, zBase + s * sep / 2));
    pos.push(Pm(p.x, p.y, zBase + s * (sep + largo - 3) / 2));      // 3 mm cruzan la placa
    sold.push(Pm(p.x, p.y, zBase - s * (T_PCB + 0.2)));
    if (anclas) _pin(g, id, p.n, Pm(p.x, p.y, zBase + s * (sep + largo)), Dm(0, 0, s), p.datos || {});
  }
  for (const [c, lista] of porColor) g.add(instancias(new THREE.BoxGeometry(2.5 * MM, sep * MM, 2.5 * MM), mat(c, PLASTICO), lista, 'header'));
  g.add(instancias(new THREE.BoxGeometry(0.64 * MM, (sep + largo + 3) * MM, 0.64 * MM), mat(COLOR.dorado, METAL), pos, 'pines'));
  g.add(instancias(new THREE.CylinderGeometry(0.8 * MM, 1.0 * MM, 0.4 * MM, 10), mat(COLOR.estano, METAL), sold, 'soldaduras'));
}
// Header hembra (tira de 2,54 mm, 8,5 mm de alto) con el hueco oscuro arriba.
function _headerHembra(g, pos, zBase, alto = 8.5) {
  g.add(instancias(new THREE.BoxGeometry(2.54 * MM, alto * MM, 2.54 * MM), mat(0x1c1c1e, PLASTICO), pos.map(([x, y]) => Pm(x, y, zBase + alto / 2)), 'header_hembra'));
  g.add(instancias(new THREE.BoxGeometry(1.0 * MM, 0.1 * MM, 1.0 * MM), new THREE.MeshBasicMaterial({ color: 0x000000 }), pos.map(([x, y]) => Pm(x, y, zBase + alto + 0.03)), 'huecos'));
}

// Borne de tornillo de 5,08 mm (KF301 / DG301): 5 × 7,5 × 10 mm. `dir` = [dx, dy] hacia donde
// entra el cable (afuera de la placa). Ancla en la boca del cable.
function _bornes(g, pines, id, zBase, dir, { color = 0x1f7a45, ancho = 5.0, fondo = 7.5, alto = 10 } = {}) {
  const [dx, dy] = dir;
  const aLoLargoX = dy !== 0;                                        // la fila corre en x si el cable entra en y
  const sx = aLoLargoX ? ancho : fondo, sy = aLoLargoX ? fondo : ancho;
  const cuerpos = [], tornillos = [], ranuras = [], bocas = [];
  for (const p of pines) {
    cuerpos.push(Pm(p.x, p.y, zBase + alto / 2));
    tornillos.push(Pm(p.x - dx * 1.2, p.y - dy * 1.2, zBase + alto + 0.1));
    ranuras.push(Pm(p.x - dx * 1.2, p.y - dy * 1.2, zBase + alto + 0.45));
    bocas.push(Pm(p.x + dx * (fondo / 2 + 0.02), p.y + dy * (fondo / 2 + 0.02), zBase + 3.4));
    _pin(g, id, p.n, Pm(p.x + dx * fondo / 2, p.y + dy * fondo / 2, zBase + 3.4), Dm(dx, dy, 0));
  }
  g.add(instancias(new THREE.BoxGeometry((sx - 0.15) * MM, alto * MM, (sy) * MM), mat(color, PLASTICO), cuerpos, 'bornes'));
  g.add(instancias(new THREE.CylinderGeometry(1.5 * MM, 1.5 * MM, 0.5 * MM, 14), mat(COLOR.plata, METAL), tornillos, 'tornillos'));
  g.add(instancias(aLoLargoX ? new THREE.BoxGeometry(2.6 * MM, 0.25 * MM, 0.4 * MM) : new THREE.BoxGeometry(0.4 * MM, 0.25 * MM, 2.6 * MM),
    new THREE.MeshBasicMaterial({ color: 0x222222 }), ranuras, 'ranuras'));
  const bocaGeo = aLoLargoX ? new THREE.BoxGeometry(3.2 * MM, 3.0 * MM, 0.1 * MM) : new THREE.BoxGeometry(0.1 * MM, 3.0 * MM, 3.2 * MM);
  g.add(instancias(bocaGeo, new THREE.MeshBasicMaterial({ color: 0x0a0a0a }), bocas, 'bocas'));
}

// Condensador electrolitico vertical (d × h mm) con su tapa de aluminio y la franja del negativo.
function _electrolitico(g, x, y, zBase, d, h, color = 0x1a3a8a) {
  const r = d / 2;
  _ci(g, r, h - 0.4, color, x, y, zBase + (h - 0.4) / 2, { roughness: 0.4 }, 28);
  _ci(g, r * 0.86, 0.4, COLOR.plata, x, y, zBase + h - 0.2, METAL, 28);
  const franja = new THREE.Mesh(new THREE.CylinderGeometry((r + 0.03) * MM, (r + 0.03) * MM, (h - 1.2) * MM, 8, 1, true, 1.5 * Math.PI - 0.45, 0.9),
    mat(0xd8dde6, { side: THREE.DoubleSide }));
  franja.position.copy(Pm(x, y, zBase + (h - 0.4) / 2));
  g.add(franja);                                                               // franja del negativo
}
// Circuito integrado: cuerpo, patas a los dos lados largos (a lo largo de x) y texto.
function _chip(g, x, y, zBase, L, W, H, texto, { patas = 0, paso = 1.27, dip = false, color = COLOR.chip } = {}) {
  _cj(g, L, W, H, color, x, y, zBase + (dip ? 0.8 : 0) + H / 2, { roughness: 0.55 });
  if (patas) {
    const pos = [];
    for (const s of [-1, 1]) for (let i = 0; i < patas; i++) pos.push(Pm(x + (i - (patas - 1) / 2) * paso, y + s * (W / 2 + 0.35), zBase + (dip ? 1.4 : 0.15)));
    g.add(instancias(new THREE.BoxGeometry((dip ? 0.5 : 0.3) * MM, (dip ? 2.8 : 0.3) * MM, 0.8 * MM), mat(COLOR.estano, METAL), pos, 'patas'));
  }
  if (texto) {
    const t = planoDibujado(L * MM, W * MM, (ctx, X, Y, k) => {
      ctx.fillStyle = 'rgba(210,210,210,0.85)'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.font = `600 ${Math.min(W * 0.32, L * 1.5 / texto.length) * k}px "IBM Plex Mono", monospace`;
      ctx.fillText(texto, X(0), Y(0));
      ctx.beginPath(); ctx.arc(X(-L / 2 + 1.0), Y(-W / 2 + 1.0), 0.35 * k, 0, 2 * Math.PI); ctx.fill();
    }, { ppm: 30 });
    t.position.copy(Pm(x, y, zBase + (dip ? 0.8 : 0) + H + 0.02));
    g.add(t);
  }
}
// Pasivos SMD (0805) en las posiciones dadas.
function _smd(g, lista, zBase, color = 0xb59a6a, [L, W, H] = [2.0, 1.25, 0.6]) {
  g.add(instancias(new THREE.BoxGeometry(L * MM, H * MM, W * MM), mat(color), lista.map(([x, y]) => Pm(x, y, zBase + H / 2)), 'pasivos'));
}
// LED SMD con material basico (no lo toca el resaltado del visor).
function _led(g, nombre, color, x, y, z) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(1.6 * MM, 0.55 * MM, 0.8 * MM), new THREE.MeshBasicMaterial({ color }));
  m.position.copy(Pm(x, y, z + 0.28));
  m.name = nombre;
  g.add(m);
  return m;
}
// Potenciometro de ajuste 3296W (azul, tornillo de laton).
function _trimmer(g, x, y, zBase, nombre = 'ajuste') {
  const t = new THREE.Group(); t.name = nombre;
  t.add(caja(9.5 * MM, 4.8 * MM, 10 * MM, 0x2d6fd0, Pm(x, y, zBase + 5), PLASTICO));
  t.add(cilindro(1.1 * MM, 1.0 * MM, 0xc9a23a, Pm(x - 3.2, y, zBase + 10.5), METAL, 12));
  g.add(t);
}
// Disipador de aluminio con aletas a lo largo de y.
function _disipador(g, x, y, zBase, sx, sy, sz, aletas = 5, color = COLOR.aluminio) {
  const base = 2;
  _cj(g, sx, sy, base, color, x, y, zBase + base / 2, METAL);
  const e = 1.0, paso = (sx - e) / (aletas - 1);
  for (let i = 0; i < aletas; i++) _cj(g, e, sy, sz - base, color, x - sx / 2 + e / 2 + i * paso, y, zBase + base + (sz - base) / 2, METAL);
}
// Placa perforada (paso 2,54): agujeros con su anillo de cobre.
function _dibujarPerforada(ctx, x, y, k, L, W) {
  for (let px = -L / 2 + 1.5; px <= L / 2 - 1.2; px += PASO_PIN) for (let py = -W / 2 + 1.5; py <= W / 2 - 1.2; py += PASO_PIN) {
    ctx.fillStyle = '#c98a4a'; ctx.beginPath(); ctx.arc(x(px), y(py), 0.75 * k, 0, 2 * Math.PI); ctx.fill();
    ctx.fillStyle = '#1a120a'; ctx.beginPath(); ctx.arc(x(px), y(py), 0.4 * k, 0, 2 * Math.PI); ctx.fill();
  }
}
// Receptaculo USB-A en una cara: `dir` [dx, dy] hacia afuera; (x, y, z) = centro de la boca.
function _usbA(g, x, y, z, dir, lengua = 0x111111) {
  const [dx, dy] = dir;
  const ax = dx !== 0;                                                // boca en una cara x
  const [sx, sy] = ax ? [1.0, 13.1] : [13.1, 1.0];
  _cj(g, sx, sy, 5.7, COLOR.plata, x - dx * 0.45, y - dy * 0.45, z, METAL);
  _cj(g, ax ? 0.2 : 11.5, ax ? 11.5 : 0.2, 4.4, 0x050505, x + dx * 0.02, y + dy * 0.02, z);
  _cj(g, ax ? 0.3 : 9.5, ax ? 9.5 : 0.3, 1.6, lengua, x + dx * 0.1, y + dy * 0.1, z + 0.9);
}
// Jack DC de 5,5 mm (cuerpo negro, boca hacia `dir`).
function _jackDC(g, x, y, zBase, dir, [fondo, ancho, alto] = [14, 9, 11]) {
  const [dx, dy] = dir;
  const ax = dx !== 0;
  _cj(g, ax ? fondo : ancho, ax ? ancho : fondo, alto, COLOR.plastico_negro, x, y, zBase + alto / 2, PLASTICO, 'jack');
  const bx = x + dx * (fondo / 2 + 0.02), by = y + dy * (fondo / 2 + 0.02);
  const boca = ax ? _ciX(g, 3.1, 0.1, 0x050505, bx, by, zBase + alto / 2 + 0.6, {}, 20) : _ciY(g, 3.1, 0.1, 0x050505, bx, by, zBase + alto / 2 + 0.6, {}, 20);
  boca.material = new THREE.MeshBasicMaterial({ color: 0x050505 });
  if (ax) _ciX(g, 1.0, 0.3, COLOR.plata, bx, by, zBase + alto / 2 + 0.6, METAL, 12);
  else _ciY(g, 1.0, 0.3, COLOR.plata, bx, by, zBase + alto / 2 + 0.6, METAL, 12);
  return Pm(bx, by, zBase + alto / 2 + 0.6);
}

// ---------------------------------------------------------------------------
// Placa de expansion GVS con su ESP32 (30P del carro, 38P de la caja de control)
// ---------------------------------------------------------------------------
//
// Medidas: 30P = 68 × 53 mm (catalogo `Shield_30P`, 53 × 68 × 12,6 mm), 38P = 80 × 62 mm
// (conexiones.py). Headers hembra del ESP32 a ±12,7 mm; por cada GPIO una fila G-V-S a 17,78 /
// 20,32 / 22,86 mm del centro (G interior, V al medio, S afuera, como `H['gvs']` del catalogo),
// header I2C y bloques GND / 5V / 3V3 al lado del USB (mismas x, y que `_shield` de conexiones.py),
// y en el otro extremo jack DC, micro-USB de alimentacion, AMS1117, jumper de V (5 V / 3,3 V) y LED.
// Encima va la pieza piloto `crearESP32DevKit` (separador de 2,5 mm sobre las hembras de 8,5 mm).
//
// NOTA (orientacion): el ESP32 va con el pinout REAL (antena -x, USB +x, header de EN en -y,
// ver PINOUT_ESP32). `_shield` de conexiones.py usa el mismo pinout (corregido el 2026-09-27):
// las filas GVS siguen al ESP32 real, asi que `G34.S` queda en -y, igual que en la plantilla. El nombre de cada ancla es el
// mismo de conexiones.py (`pin_<id>_G34.S`, `pin_<id>_I2C.SDA`, `pin_<id>_USB`, `pin_<id>_JACK`).
//
// Origen: centro de la cara de abajo de la placa. Nodos: pcb, esp32 (la pieza piloto; sus
// anclas `pin_<idESP32>_<PIN>` quedan en la punta de sus pines, dentro de las hembras), jack,
// puente_v (el jumper). opciones: pines 30|38, id ('esp32_carro' / 'esp32_fijo'),
// conESP32 (true), idESP32 ('ESP32'), usb ('micro').
export function crearPlacaGVS(opciones = {}) {
  const { pines = 30, conESP32 = true, idESP32 = 'ESP32', serigrafia = true } = opciones;
  const id = opciones.id || (pines === 30 ? 'esp32_carro' : 'esp32_fijo');
  const def = PINOUT_ESP32[pines];
  if (!def) throw new Error(`Placa GVS de ${pines} pines: no existe (30 o 38)`);
  const [L, W] = pines === 30 ? [68, 53] : [80, 62];
  const n = def.ladoEN.length, x0 = -(n - 1) * PASO_PIN / 2, zT = T_PCB;
  const g = new THREE.Group();
  g.name = `placa_gvs_${pines}p`;
  _pcb(g, L, W, COLOR.pcb_negro);

  // Hembras del ESP32.
  const hem = [];
  for (const s of [-1, 1]) for (let i = 0; i < n; i++) hem.push([x0 + i * PASO_PIN, s * SEP_FILAS / 2]);
  _headerHembra(g, hem, zT);

  // Filas G-V-S de cada GPIO (negro, rojo, amarillo).
  const filas = [];
  for (const [lista, s] of [[def.ladoEN, -1], [def.lado23, 1]]) lista.forEach((nom, i) => {
    if (!/^G\d+$/.test(nom)) return;
    for (const [col, dy, c] of [['G', 17.78, COLOR.plastico_negro], ['V', 20.32, 0xb3261e], ['S', 22.86, 0xe0b220]])
      filas.push({ n: `${nom}.${col}`, x: x0 + i * PASO_PIN, y: s * dy, color: c, datos: { gpio: nom, columna: col } });
  });
  _headerMacho(g, filas, id, zT);

  // I2C y bloques de alimentacion (junto al USB del ESP32).
  const xe = x0 + n * PASO_PIN + 3;
  const col = (nombres, x, y0, color) => nombres.map((nm, k) => ({ n: nm, x, y: y0 + k * PASO_PIN, color }));
  _headerMacho(g, [
    ...col(['I2C.GND', 'I2C.VCC', 'I2C.SCL', 'I2C.SDA'], xe, -9.5, 0x2a5fb0),
    ...col(['GND.1', 'GND.2', 'GND.3'], xe, 4.0),
    ...col(['5V.1', '5V.2'], xe + PASO_PIN, 4.0, 0xb3261e),
    ...col(['3V3.1', '3V3.2'], xe + 2 * PASO_PIN, 4.0, 0xd9771f),
  ], id, zT);

  // Extremo de la antena: jack DC, micro-USB de alimentacion, regulador, jumper de V, LED, condensador.
  const xc = (-L / 2 + x0 - 2.5) / 2;
  const bocaJack = _jackDC(g, -L / 2 + 7, W / 2 - 8, zT, [-1, 0], [14, 9, 10.5]);
  _pin(g, id, 'JACK', bocaJack, Dm(-1, 0, 0));
  _cj(g, 5.6, 7.5, 2.7, COLOR.plata, -L / 2 + 2.0, -(W / 2 - 8), zT + 1.35, METAL, 'usb_alimentacion');
  _pin(g, id, 'USB_ALIM', Pm(-L / 2 - 0.8, -(W / 2 - 8), zT + 1.35), Dm(-1, 0, 0));
  _chip(g, xc, -8, zT, 6.5, 3.5, 1.6, 'AMS1117', { patas: 3, paso: 2.3 });
  const jp = [0, 1, 2].map((k) => ({ n: `JP${k + 1}`, x: xc, y: -1.27 + k * PASO_PIN }));
  _headerMacho(g, jp, id, zT, { anclas: false });
  const puente = _cj(g, 2.5, 5.0, 6.0, 0x2a5fb0, xc, 0.0, zT + SEPARADOR + 3.2, PLASTICO, 'puente_v');   // jumper en 5V
  puente.userData.posicion = '5V';
  _electrolitico(g, xc, 10, zT, 6.3, 7);
  _led(g, 'led_power', 0xff3b30, xc + 4, -13, zT);

  if (serigrafia) _serigrafia(g, L, W, zT, (ctx, x, y, k) => {
    _agujeros(ctx, x, y, k, [[-L / 2 + 3.5, -W / 2 + 3.5], [L / 2 - 3.5, -W / 2 + 3.5], [-L / 2 + 3.5, W / 2 - 3.5], [L / 2 - 3.5, W / 2 - 3.5]]);
    for (const [lista, s] of [[def.ladoEN, -1], [def.lado23, 1]]) lista.forEach((nom, i) => {
      if (/^G\d+$/.test(nom)) _texto(ctx, nom.slice(1), x(x0 + i * PASO_PIN), y(s * 25.1), k, { tam: 1.05 });
    });
    for (const s of [-1, 1]) [['G', 17.78], ['V', 20.32], ['S', 22.86]].forEach(([c, dy]) => _texto(ctx, c, x(x0 - 2.3), y(s * dy), k, { tam: 1.1, color: '#f2b134' }));
    ['GND', 'VCC', 'SCL', 'SDA'].forEach((t, j) => _texto(ctx, t, x(xe + 1.7), y(-9.5 + j * PASO_PIN), k, { tam: 0.9, alinear: 'left' }));
    [['GND', 0], ['5V', 1], ['3V3', 2]].forEach(([t, j]) => _texto(ctx, t, x(xe + j * PASO_PIN), y(11.9), k, { tam: 0.85, alinear: 'left', giro: -Math.PI / 2 }));
    _texto(ctx, '5V', x(xc + 2.2), y(-1.3), k, { tam: 0.8, alinear: 'left' });
    _texto(ctx, '3V3', x(xc + 2.2), y(3.8), k, { tam: 0.8, alinear: 'left' });
    _texto(ctx, 'DC 6.5-16V', x(-L / 2 + 7), y(W / 2 - 1.8), k, { tam: 0.9 });
  });

  if (conESP32) {
    const esp = crearESP32DevKit({ pines, id: idESP32, modulo: idESP32, usb: opciones.usb || 'micro' });
    esp.name = 'esp32';
    esp.position.copy(Pm(0, 0, zT + 8.5 + SEPARADOR));
    g.add(esp);
    const u = esp.getObjectByName('ancla_usb').position.clone().add(esp.position);
    _pin(g, id, 'USB', u, Dm(1, 0, 0));
  } else _pin(g, id, 'USB', Pm(x0 + (n - 1) * PASO_PIN + def.ultimoPinAlBorde + 0.8, 0, zT + 8.5 + SEPARADOR + T_PCB + 1.4), Dm(1, 0, 0));
  return _fin(g, opciones, `Placa GVS ${pines}P${conESP32 ? ' con ESP32' : ''}`);
}
export const crearPlacaGVS30P = (o = {}) => crearPlacaGVS({ ...o, pines: 30 });
export const crearPlacaGVS38P = (o = {}) => crearPlacaGVS({ ...o, pines: 38 });

// ---------------------------------------------------------------------------
// Puente H TB6612FNG (modulo tipo Pololu/SparkFun, 20,3 × 20,3 mm)
// ---------------------------------------------------------------------------
// Ficha Pololu #713: 0,8" × 0,8" (20,3 mm), dos filas de 8 pines a 0,7" (17,8 mm). Chip SSOP24
// (7,8 × 5,6 mm) al centro y sus condensadores. Pines como conexiones.py (`tb6612`): izquierda
// PWMA..GND_L en x = -8,9, derecha VM..GND_P2 en x = +8,9, de -y a +y.
// Origen: centro de la cara de abajo. opciones: id ('tb6612'), pinesAbajo (false: como la
// plantilla, pines hacia arriba; true para protoboard).
export function crearTB6612FNG(opciones = {}) {
  const { id = 'tb6612', pinesAbajo = false, serigrafia = true } = opciones;
  const izq = ['PWMA', 'AIN2', 'AIN1', 'STBY', 'BIN1', 'BIN2', 'PWMB', 'GND_L'];
  const der = ['VM', 'VCC', 'GND_P', 'AO1', 'AO2', 'BO2', 'BO1', 'GND_P2'];
  const L = 20.3, W = 20.3, T = T_PCB, y0 = -(izq.length - 1) * PASO_PIN / 2;
  const g = new THREE.Group();
  g.name = 'tb6612fng';
  _pcb(g, L, W, 0x7a2a8c);
  const pines = [...izq.map((n, k) => ({ n, x: -8.9, y: y0 + k * PASO_PIN })), ...der.map((n, k) => ({ n, x: 8.9, y: y0 + k * PASO_PIN }))];
  _headerMacho(g, pines, id, pinesAbajo ? 0 : T, { abajo: pinesAbajo });
  const chip = new THREE.Group(); chip.name = 'chip';
  _chip(chip, 0, 0.5, T, 5.6, 7.8, 1.5, '', {});
  const patas = [];
  for (const s of [-1, 1]) for (let i = 0; i < 12; i++) patas.push(Pm(s * 3.2, 0.5 + (i - 5.5) * 0.65, T + 0.15));
  chip.add(instancias(new THREE.BoxGeometry(0.8 * MM, 0.3 * MM, 0.3 * MM), mat(COLOR.estano, METAL), patas, 'patas'));
  g.add(chip);
  _smd(g, [[-3.2, -7.2], [0, -7.2], [3.2, -7.2]], T, 0xc9a86a, [3.2, 1.6, 1.4]);   // 10 µF de VM y VCC
  if (serigrafia) _serigrafia(g, L, W, T, (ctx, x, y, k) => {
    const r = (n) => n.replace(/_(L|P2?|)$/, '').replace('GND_', 'GND');
    izq.forEach((n, j) => _texto(ctx, r(n), x(-7.2), y(y0 + j * PASO_PIN), k, { tam: 0.85, alinear: 'left' }));
    der.forEach((n, j) => _texto(ctx, r(n), x(7.2), y(y0 + j * PASO_PIN), k, { tam: 0.85, alinear: 'right' }));
    _texto(ctx, 'TB6612FNG', x(0), y(-9.5 + 0.2), k, { tam: 0.8, color: '#e6d6f0' });
  }, { ppm: 30 });
  return _fin(g, opciones, 'Puente H TB6612FNG');
}

// ---------------------------------------------------------------------------
// Drivers de paso StepStick: A4988 (Pololu y clones) y TMC2208 (misma huella)
// ---------------------------------------------------------------------------
// Ficha Pololu #1182: 0,6" × 0,8" (15,24 × 20,32 mm), 2 filas de 8 pines a 0,5" (12,7 mm),
// pines hacia ABAJO (se enchufa en hembras). Disipador de 9 × 9 × 6 mm sobre el chip y el
// trimmer de corriente del lado de DIR. Con el trimmer hacia -y: izquierda (x = -6,35) EN, MS1,
// MS2, MS3, RST, SLP, STEP, DIR de +y a -y; derecha (x = +6,35) VMOT, GND, 2B, 2A, 1A, 1B, VDD,
// GND. El TMC2208 (BTT v3) usa la misma huella; sus rotulos cambian (PDN, CLK, VM, VIO) pero las
// anclas conservan los nombres funcionales del A4988 (STEP, DIR, EN, VMOT, VDD, 1A..2B).
// Origen: centro de la cara de abajo del PCB; anclas en la punta de los pines (8,5 mm abajo).
// opciones: tipo 'A4988' | 'TMC2208', id (el tipo), disipador (true).
export function crearDriverPasoAPaso(opciones = {}) {
  const { tipo = 'A4988', disipador = true, serigrafia = true } = opciones;
  const id = opciones.id || tipo;
  const tmc = tipo === 'TMC2208';
  const izq = tmc ? ['EN', 'MS1', 'MS2', 'PDN', 'PDN_UART', 'CLK', 'STEP', 'DIR'] : ['EN', 'MS1', 'MS2', 'MS3', 'RST', 'SLP', 'STEP', 'DIR'];
  const der = ['VMOT', 'GND', '2B', '2A', '1A', '1B', 'VDD', 'GND_2'];
  const rotIzq = tmc ? ['EN', 'MS1', 'MS2', 'PDN', 'PDN', 'CLK', 'STP', 'DIR'] : ['EN', 'MS1', 'MS2', 'MS3', 'RST', 'SLP', 'STP', 'DIR'];
  const rotDer = tmc ? ['VM', 'GND', 'B2', 'B1', 'A1', 'A2', 'VIO', 'GND'] : ['VMT', 'GND', '2B', '2A', '1A', '1B', 'VDD', 'GND'];
  const L = 15.24, W = 20.32, T = T_PCB, yTop = (izq.length - 1) * PASO_PIN / 2;
  const g = new THREE.Group();
  g.name = `driver_${tipo.toLowerCase()}`;
  _pcb(g, L, W, tmc ? 0x4a2a6a : 0xb3243a);
  const pines = [...izq.map((n, k) => ({ n, x: -6.35, y: yTop - k * PASO_PIN })), ...der.map((n, k) => ({ n, x: 6.35, y: yTop - k * PASO_PIN }))];
  _headerMacho(g, pines, id, 0, { abajo: true });
  _chip(g, 0, 2.0, T, 5, 5, 0.9, '', {});
  if (disipador) { const d = new THREE.Group(); d.name = 'disipador'; _disipador(d, 0, 2.0, T + 0.9, 9, 9, 6, 5, tmc ? 0x4a78c8 : COLOR.aluminio); g.add(d); }
  // Trimmer de corriente (cuadrado, con la ranura en cruz) y resistencias de sensado.
  _cj(g, 3.6, 3.6, 1.4, 0xd9d4c8, 0, -7.0, T + 0.7, PLASTICO, 'trimmer');
  _ci(g, 1.3, 0.3, COLOR.plata, 0, -7.0, T + 1.55, METAL, 14);
  _smd(g, [[-3.8, -3.6], [3.8, -3.6]], T, 0x151515, [2.0, 1.25, 0.5]);
  _smd(g, [[-3.8, 6.3], [3.8, 6.3], [0, 8.4]], T, 0xb59a6a);
  if (serigrafia) _serigrafia(g, L, W, T, (ctx, x, y, k) => {
    rotIzq.forEach((t, j) => _texto(ctx, t, x(-4.9), y(yTop - j * PASO_PIN), k, { tam: 0.75, alinear: 'left' }));
    rotDer.forEach((t, j) => _texto(ctx, t, x(4.9), y(yTop - j * PASO_PIN), k, { tam: 0.75, alinear: 'right' }));
  }, { ppm: 34 });
  return _fin(g, opciones, `Driver ${tipo}`);
}
export const crearA4988 = (o = {}) => crearDriverPasoAPaso({ ...o, tipo: 'A4988' });
export const crearTMC2208 = (o = {}) => crearDriverPasoAPaso({ ...o, tipo: 'TMC2208' });

// Placa perforada de 70 × 45 mm con los DOS drivers de las cintas (M = monedas en x = -16,
// V = vasos en x = +9) enchufados en hembras, bornes de las bobinas (M.1A..V.2B) hacia +y,
// VMOT/GNDP hacia +x, header de logica (M.STEP..GND) y un electrolitico de 100 µF por driver.
// Todo en las posiciones de `placa_drivers` de conexiones.py. Nodos: driver_M, driver_V (con sus
// anclas `pin_<id>_M_<PIN>` / `pin_<id>_V_<PIN>` en la punta de sus pines, dentro de las hembras).
// opciones: id ('drivers'), tipo ('A4988' | 'TMC2208').
export function crearPlacaDriversPasoAPaso(opciones = {}) {
  const { id = 'drivers', tipo = 'A4988', serigrafia = true } = opciones;
  const L = 70, W = 45, T = T_PCB;
  const g = new THREE.Group();
  g.name = 'placa_drivers';
  _pcb(g, L, W, 0xb88a4a);
  for (const [cx, letra] of [[-16, 'M'], [9, 'V']]) {
    const hem = [];
    for (const s of [-1, 1]) for (let k = 0; k < 8; k++) hem.push([cx + s * 6.35, 2 + (k - 3.5) * PASO_PIN]);
    _headerHembra(g, hem, T);
    const d = crearDriverPasoAPaso({ tipo, id: `${id}_${letra}` });
    d.name = `driver_${letra}`;
    d.position.copy(Pm(cx, 2, T + 8.5 + SEPARADOR));
    g.add(d);
  }
  _bornes(g, [['M.1A', -30], ['M.1B', -25], ['M.2A', -20], ['M.2B', -15], ['V.1A', 7.5], ['V.1B', 12.5], ['V.2A', 17.5], ['V.2B', 22.5]]
    .map(([n, x]) => ({ n, x, y: 17.5 })), id, T, [0, 1]);
  _bornes(g, [{ n: 'VMOT', x: 25, y: -2.5 }, { n: 'GNDP', x: 25, y: 2.5 }], id, T, [1, 0]);
  _headerMacho(g, ['M.STEP', 'M.DIR', 'V.STEP', 'V.DIR', 'EN', 'VDD', 'GND'].map((n, k) => ({ n, x: -27 + k * PASO_PIN, y: -18 })), id, T);
  _electrolitico(g, -3.5, 12, T, 6.3, 9);
  _electrolitico(g, 29, 13.5, T, 6.3, 9);
  if (serigrafia) _serigrafia(g, L, W, T, (ctx, x, y, k) => {
    _dibujarPerforada(ctx, x, y, k, L, W);
    _texto(ctx, 'M · monedas', x(-16), y(-12.6), k, { tam: 1.4, color: '#1a1a1a', peso: 700 });
    _texto(ctx, 'V · vasos', x(9), y(-12.6), k, { tam: 1.4, color: '#1a1a1a', peso: 700 });
    ['STP', 'DIR', 'STP', 'DIR', 'EN', 'VDD', 'GND'].forEach((t, j) => _texto(ctx, t, x(-27 + j * PASO_PIN), y(-20.8), k, { tam: 0.8, color: '#1a1a1a' }));
    _texto(ctx, '+', x(29.5), y(-2.5), k, { tam: 1.6, color: '#b3261e', peso: 700 });
    _texto(ctx, '−', x(29.5), y(2.5), k, { tam: 1.6, color: '#1a1a1a', peso: 700 });
  }, { ppm: 14 });
  return _fin(g, opciones, `Placa de drivers ${tipo} ×2`);
}

// ---------------------------------------------------------------------------
// PCA9685: 16 canales PWM por I2C (tipo Adafruit #815, 62,2 × 25,4 mm)
// ---------------------------------------------------------------------------
// Ficha Adafruit: 2,45" × 1,0" (62,2 × 25,4 mm). 16 headers de servo 3 × 4 en grupos de 4
// (PWM amarillo, V+ rojo, GND negro), header de 6 pines en cada extremo (IN.* en -x, OUT.* en
// +x: GND, OE, SCL, SDA, VCC, V+), borne de V+ / GND al medio y el electrolitico. Posiciones de
// `_pca9685` de conexiones.py. Anclas: pin_<id>_PWM0..15, V+0..15, GND0..15, IN.*, OUT.*, T.V+, T.GND.
export function crearPCA9685(opciones = {}) {
  const { id = 'pca9685', serigrafia = true } = opciones;
  const L = 62, W = 25.4, T = T_PCB;
  const g = new THREE.Group();
  g.name = 'pca9685';
  _pcb(g, L, W, 0x4b2780);
  const fin = ['GND', 'OE', 'SCL', 'SDA', 'VCC', 'V+'];
  _headerMacho(g, [...fin.map((n, k) => ({ n: `IN.${n}`, x: -28.5, y: -6.35 + k * PASO_PIN })), ...fin.map((n, k) => ({ n: `OUT.${n}`, x: 28.5, y: -6.35 + k * PASO_PIN }))], id, T);
  const servos = [];
  const xs = Array.from({ length: 16 }, (_, k) => -21.6 + k * PASO_PIN + Math.floor(k / 4) * 1.4);
  xs.forEach((x, k) => servos.push({ n: `PWM${k}`, x, y: -4.4, color: 0xe0b220 }, { n: `V+${k}`, x, y: -6.94, color: 0xb3261e }, { n: `GND${k}`, x, y: -9.48 }));
  _headerMacho(g, servos, id, T);
  _bornes(g, [{ n: 'T.V+', x: -2.5, y: 8 }, { n: 'T.GND', x: 2.5, y: 8 }], id, T, [0, 1], { color: 0x2a5fb0 });
  _electrolitico(g, 14, 7, T, 10, 13);
  _chip(g, -14, 5, T, 9.7, 4.4, 1.1, 'PCA9685', { patas: 14, paso: 0.65 });
  _smd(g, [-18, -7.6, 2.8, 13.2].map((x) => [x, -1.2]), T, 0x151515, [3.2, 1.6, 0.5]);   // redes de 220 Ω
  _led(g, 'led_power', 0xff3b30, 22, 9.5, T);
  if (serigrafia) _serigrafia(g, L, W, T, (ctx, x, y, k) => {
    _agujeros(ctx, x, y, k, [[-L / 2 + 2.5, W / 2 - 2.5], [L / 2 - 2.5, W / 2 - 2.5], [-L / 2 + 2.5, -W / 2 + 2.5], [L / 2 - 2.5, -W / 2 + 2.5]], 1.25);
    xs.forEach((xx, j) => _texto(ctx, String(j), x(xx), y(-11.6), k, { tam: 0.85 }));
    _texto(ctx, '16-CH 12-BIT PWM · PCA9685', x(-14), y(9.8), k, { tam: 1.05 });
    [['PWM', -4.4], ['V+', -6.94], ['GND', -9.48]].forEach(([t, yy]) => _texto(ctx, t, x(-23.2), y(yy), k, { tam: 0.7, alinear: 'right' }));
    _texto(ctx, 'V+  GND', x(0), y(2.9), k, { tam: 0.9 });
  });
  return _fin(g, opciones, 'PCA9685 16 canales');
}

// ---------------------------------------------------------------------------
// Placa ULN2003 del 28BYJ-48 (35 × 32 mm)
// ---------------------------------------------------------------------------
// Placa verde tipica: ULN2003 DIP16 en zocalo, 4 LED de fase, JST-XH de 5 vias del motor,
// entradas IN1..IN7 en una columna y "−"/"+" con su jumper. Posiciones de `uln2003`.
export function crearULN2003(opciones = {}) {
  const { id = 'uln2003', serigrafia = true } = opciones;
  const L = 35, W = 32, T = T_PCB;
  const g = new THREE.Group();
  g.name = 'uln2003';
  _pcb(g, L, W, 0x1f6b3a);
  _headerMacho(g, ['IN1', 'IN2', 'IN3', 'IN4', 'IN5', 'IN6', 'IN7'].map((n, k) => ({ n, x: -14.5, y: -7.6 + k * PASO_PIN })), id, T);
  _headerMacho(g, [{ n: '−', x: 11, y: -13 }, { n: '+', x: 13.54, y: -13 }], id, T);
  _cj(g, 20.3, 7.6, 1.2, 0x111111, 0, -2, T + 0.6, PLASTICO);                          // zocalo
  _chip(g, 0, -2, T + 1.2, 19, 6.5, 3.3, 'ULN2003APG', { patas: 8, paso: 2.54, dip: true });
  const jst = new THREE.Group(); jst.name = 'jst_motor';
  jst.add(caja(14.9 * MM, 5.75 * MM, 7 * MM, 0xf2f0e6, Pm(4, 12, T + 3.5), PLASTICO));
  jst.add(caja(12.5 * MM, 0.2 * MM, 4.8 * MM, 0x151515, Pm(4, 12 - 2.9, T + 3.8)));
  g.add(jst);
  _pin(g, id, 'MOTOR', Pm(4, 12, T + 7), Dm(0, 0, 1));
  ['A', 'B', 'C', 'D'].forEach((f, j) => {
    const m = _ci(g, 1.5, 4.5, 0xff4a3d, -9 + j * 4, 5.5, T + 2.25, { roughness: 0.3, transparent: true, opacity: 0.9 }, 16);
    m.name = `led_${f}`;
  });
  _cj(g, 2.5, 5.0, 6, 0x111111, 12.27, -13, T + SEPARADOR + 3.2, PLASTICO, 'jumper');
  if (serigrafia) _serigrafia(g, L, W, T, (ctx, x, y, k) => {
    _agujeros(ctx, x, y, k, [[-L / 2 + 2.8, W / 2 - 2.8], [L / 2 - 2.8, W / 2 - 2.8], [-L / 2 + 2.8, -W / 2 + 2.8], [L / 2 - 2.8, -W / 2 + 2.8]], 1.5);
    ['IN1', 'IN2', 'IN3', 'IN4'].forEach((t, j) => _texto(ctx, t, x(-12.3), y(-7.6 + j * PASO_PIN), k, { tam: 0.9, alinear: 'left' }));
    ['A', 'B', 'C', 'D'].forEach((t, j) => _texto(ctx, t, x(-9 + j * 4), y(8.2), k, { tam: 1.0 }));
    _texto(ctx, '5-12V', x(12.3), y(-10.3), k, { tam: 0.9 });
  });
  return _fin(g, opciones, 'Driver ULN2003');
}

// Placa de 2 optoacopladores PC817 (40 × 30 mm): bornes +12 / IN1 / IN2 (lado de los sensores
// NPN de 12 V) y header GND / 3V3 / OUT1 / OUT2 (lado del ESP32). Posiciones de `opto2`.
export function crearPlacaOptoPC817(opciones = {}) {
  const { id = 'opto', serigrafia = true } = opciones;
  const L = 40, W = 30, T = T_PCB;
  const g = new THREE.Group();
  g.name = 'opto_pc817';
  _pcb(g, L, W, 0x1d4f9c);
  _bornes(g, [['+12', -14], ['IN1', -9], ['IN2', -4]].map(([n, x]) => ({ n, x, y: 9 })), id, T, [0, 1], { color: 0x2a5fb0 });
  _headerMacho(g, ['GND', '3V3', 'OUT1', 'OUT2'].map((n, k) => ({ n, x: -3.8 + k * PASO_PIN, y: -10 })), id, T);
  _chip(g, -6, 0, T, 4.6, 6.5, 3.5, 'PC817', { patas: 2, paso: 2.54, dip: true });
  _chip(g, 6, 0, T, 4.6, 6.5, 3.5, 'PC817', { patas: 2, paso: 2.54, dip: true });
  _smd(g, [[-12, -3], [-12, 1], [12, -3], [12, 1]], T);                              // 2,2 kΩ y 10 kΩ
  _led(g, 'led_1', 0x3a0d0d, 15, 9, T); _led(g, 'led_2', 0x3a0d0d, 15, 11, T);
  if (serigrafia) _serigrafia(g, L, W, T, (ctx, x, y, k) => {
    _agujeros(ctx, x, y, k, [[-L / 2 + 2.8, -W / 2 + 2.8], [L / 2 - 2.8, -W / 2 + 2.8], [L / 2 - 2.8, W / 2 - 2.8]], 1.5);
    ['GND', '3V3', 'O1', 'O2'].forEach((t, j) => _texto(ctx, t, x(-3.8 + j * PASO_PIN), y(-12.6), k, { tam: 0.8 }));
    ['+12', 'IN1', 'IN2'].forEach((t, j) => _texto(ctx, t, x(-14 + j * 5), y(4.2), k, { tam: 0.9 }));
    _texto(ctx, '2 × PC817', x(10), y(-6.5), k, { tam: 1.1 });
  });
  return _fin(g, opciones, 'Optoacopladores PC817 ×2');
}

// Reparto del bus I2C 1 (placa perforada 30 × 22 mm): 3 headers de 4 (SDA, SCL, 3V3, GND) y
// dos pull-ups de 2,2 kΩ (rojo-rojo-rojo) de pie. Posiciones de `hub_i2c`.
export function crearRepartoI2C(opciones = {}) {
  const { id = 'hub_i2c', serigrafia = true } = opciones;
  const L = 30, W = 22, T = T_PCB;
  const g = new THREE.Group();
  g.name = 'reparto_i2c';
  _pcb(g, L, W, 0x1f3d2b);
  const cols = ['SDA', 'SCL', '3V3', 'GND'];
  const pines = [];
  for (const [pref, y] of [['', -7.6], ['A.', 0], ['B.', 7.6]]) cols.forEach((c, k) => pines.push({ n: pref + c, x: -3.8 + k * PASO_PIN, y }));
  _headerMacho(g, pines, id, T);
  // Resistencias axiales de 1/4 W (6,3 × 2,3 mm) acostadas a lo largo de y, con sus bandas.
  for (const x of [9.5, 12.5]) {
    _ciY(g, 1.15, 6.3, 0xd8c7a0, x, 0, T + 1.3, {}, 14);
    [-1.8, -0.8, 0.2].forEach((dy) => _ciY(g, 1.2, 0.5, 0xb3261e, x, dy, T + 1.3, {}, 14));
    _ciY(g, 1.2, 0.5, 0xc9a23a, x, 2.0, T + 1.3, METAL, 14);
    for (const s of [-1, 1]) _cj(g, 0.5, 0.5, 1.3, COLOR.estano, x, s * 3.9, T + 0.65, METAL);
  }
  if (serigrafia) _serigrafia(g, L, W, T, (ctx, x, y, k) => {
    _dibujarPerforada(ctx, x, y, k, L, W);
    ctx.strokeStyle = '#d0d0d0'; ctx.lineWidth = 0.6 * k;
    cols.forEach((_, j) => { ctx.beginPath(); ctx.moveTo(x(-3.8 + j * PASO_PIN), y(-7.6)); ctx.lineTo(x(-3.8 + j * PASO_PIN), y(7.6)); ctx.stroke(); });
    _texto(ctx, 'I2C 1', x(-11), y(0), k, { tam: 1.3, color: '#e8e8e8', peso: 700 });
  }, { ppm: 22 });
  return _fin(g, opciones, 'Reparto I2C');
}

// ---------------------------------------------------------------------------
// Reguladores buck: XL4016 (6 V 8 A, servos) y LM2596 (5 V 3 A)
// ---------------------------------------------------------------------------
// XL4016: modulo azul de 60 × 51 mm con dos disipadores de 18 × 20 × 16 mm, bobina toroidal,
// dos electroliticos de 10 × 13 mm, trimmer 3296 y bornes IN (-x) / OUT (+x). Posiciones de `xl4016`.
export function crearBuckXL4016(opciones = {}) {
  const { id = 'buck6', serigrafia = true, voltaje = '6.0V' } = opciones;
  const L = 60, W = 51, T = T_PCB;
  const g = new THREE.Group();
  g.name = 'buck_xl4016';
  _pcb(g, L, W, 0x1d4f9c);
  _bornes(g, [{ n: 'IN+', x: -26, y: -3.0 }, { n: 'IN-', x: -26, y: 2.0 }], id, T, [-1, 0], { color: 0x2a5fb0 });
  _bornes(g, [{ n: 'OUT+', x: 26, y: -3.0 }, { n: 'OUT-', x: 26, y: 2.0 }], id, T, [1, 0], { color: 0x2a5fb0 });
  _disipador(g, -12, 5, T, 18, 20, 16);
  _disipador(g, 12, 5, T, 18, 20, 16);
  _electrolitico(g, -12, -17, T, 10, 13);
  _electrolitico(g, 12, -17, T, 10, 13);
  const bob = _ci(g, 5, 9, 0x2c2c2c, 0, 20.2, T + 4.5, { roughness: 0.5 }, 28, 'bobina');
  bob.userData.nota = 'bobina de 47 µH';
  _trimmer(g, 0, -18, T);
  _led(g, 'led_power', 0xff3b30, -22, -20, T);
  if (serigrafia) _serigrafia(g, L, W, T, (ctx, x, y, k) => {
    _agujeros(ctx, x, y, k, [[-L / 2 + 3, W / 2 - 3], [L / 2 - 3, W / 2 - 3], [-L / 2 + 3, -W / 2 + 3], [L / 2 - 3, -W / 2 + 3]]);
    _texto(ctx, 'IN', x(-26), y(-8.5), k, { tam: 1.4 }); _texto(ctx, 'OUT', x(26), y(-8.5), k, { tam: 1.4 });
    _texto(ctx, `XL4016 · ${voltaje} 8A`, x(0), y(-23.7), k, { tam: 1.2 });
  }, { ppm: 14 });
  return _fin(g, opciones, 'Buck XL4016');
}
// LM2596: modulo azul de 43 × 21 mm (ficha tipica "DC-DC LM2596"): LM2596S (TO-263), bobina
// CD54 de 12 × 12 mm, dos electroliticos de 8 × 10 mm, trimmer 3296 y 4 pads. Pads de `lm2596`.
export function crearBuckLM2596(opciones = {}) {
  const { id = 'buck5', serigrafia = true } = opciones;
  const L = 43, W = 21, T = T_PCB;
  const g = new THREE.Group();
  g.name = 'buck_lm2596';
  _pcb(g, L, W, 0x1d4f9c);
  _electrolitico(g, -14.5, -1, T, 8, 10);
  _cj(g, 12, 12, 7, 0x2b2b2b, -2, 3, T + 3.5, { roughness: 0.5 }, 'bobina');
  _chip(g, -2, -6.8, T, 9.5, 6.0, 2.3, 'LM2596S');
  _electrolitico(g, 12, 3, T, 8, 10);
  _trimmer(g, 12, -6.5, T);
  for (const [n, x, y] of [['IN+', -19, 8], ['IN-', -19, -8], ['OUT+', 19, 8], ['OUT-', 19, -8]]) {
    _ci(g, 1.4, 0.4, COLOR.estano, x, y, T + 0.2, METAL, 16);
    _pin(g, id, n, Pm(x, y, T + 0.4), Dm(0, 0, 1));
  }
  if (serigrafia) _serigrafia(g, L, W, T, (ctx, x, y, k) => {
    [['IN+', -19, 5.2], ['IN-', -19, -5.2], ['OUT+', 19, 5.2], ['OUT-', 19, -5.2]].forEach(([t, xx, yy]) => _texto(ctx, t, x(xx), y(yy), k, { tam: 0.95 }));
  }, { ppm: 22 });
  return _fin(g, opciones, 'Buck LM2596');
}

// ---------------------------------------------------------------------------
// Fuente conmutada 12 V tipo LRS-150-12 (159 × 97 × 30 mm)
// ---------------------------------------------------------------------------
// Ficha LRS-150: 159 × 97 × 30 mm. Chasis de aluminio con tapa perforada, bornera de barrera de
// 7 tornillos M3,5 en el extremo +x (L, N, PE, -V, -V, +V, +V; paso 9,5 mm, conexiones.py), LED
// verde y trimmer V.ADJ junto a la bornera. Anclas en la cabeza de cada tornillo, cable hacia +x.
export function crearFuenteLRS150(opciones = {}) {
  const { id = 'fuente', serigrafia = true } = opciones;
  const L = 159, W = 97, H = 30, xB = 73;
  const g = new THREE.Group();
  g.name = 'fuente_lrs150';
  _cj(g, L, W, 1.2, 0xa7adb5, 0, 0, 0.6, { metalness: 0.7, roughness: 0.45 }, 'base');
  // Tapa en U (arriba + dos costados) que llega hasta la bornera.
  const xTapa = xB - 9;
  const lt = xTapa + L / 2;
  const tapa = new THREE.Group(); tapa.name = 'tapa';
  tapa.add(caja(lt * MM, W * MM, 1.0 * MM, 0xb9bec6, Pm(-L / 2 + lt / 2, 0, H - 0.5), { metalness: 0.7, roughness: 0.4 }));
  for (const s of [-1, 1]) tapa.add(caja(lt * MM, 1.0 * MM, (H - 1.2) * MM, 0xb9bec6, Pm(-L / 2 + lt / 2, s * (W / 2 - 0.5), 1.2 + (H - 1.2) / 2), { metalness: 0.7, roughness: 0.4 }));
  tapa.add(caja(1.0 * MM, W * MM, (H - 1.2) * MM, 0xb9bec6, Pm(-L / 2 + 0.5, 0, 1.2 + (H - 1.2) / 2), { metalness: 0.7, roughness: 0.4 }));
  g.add(tapa);
  _cj(g, 1.0, W - 2, H - 1.2, 0x2a2e33, xTapa, 0, 1.2 + (H - 1.2) / 2, {});                      // frente interior (oscuro)
  // Bornera de barrera.
  const nombres = ['L', 'N', 'PE', '-V1', '-V2', '+V1', '+V2'];
  _cj(g, 13, 70, 12, 0x151515, xB, 0, 1.2 + 6, PLASTICO, 'bornera');
  nombres.forEach((n, i) => {
    const y = -28.5 + i * 9.5;
    if (i < nombres.length - 1) _cj(g, 13, 1.2, 5, 0x151515, xB, y + 4.75, 1.2 + 12 + 2.5, PLASTICO);   // barreras
    _cj(g, 7, 6.5, 0.5, COLOR.estano, xB + 1.5, y, 1.2 + 12 + 0.25, METAL);                        // placa del borne
    _ci(g, 2.9, 2.2, COLOR.plata, xB + 1.5, y, 1.2 + 12 + 0.5 + 1.1, METAL, 16);
    _cj(g, 4.2, 0.6, 0.3, 0x333333, xB + 1.5, y, 1.2 + 12 + 0.5 + 2.2 + 0.1);
    _pin(g, id, n, Pm(xB + 1.5, y, 1.2 + 12 + 2.9), Dm(1, 0, 0));
  });
  _cj(g, 15, W - 4, 0.8, 0xf2f0e8, xB - 0.5, 0, 1.2 + 12 + 5.4, { transparent: true, opacity: 0.25, roughness: 0.2 }, 'tapa_bornera');
  _led(g, 'led_power', 0x39d353, xB - 2, 40, 1.2 + 12);
  _cj(g, 4, 4, 3, 0x2d6fd0, xB + 2, 43.5, 1.2 + 12 + 1.5, PLASTICO, 'v_adj');
  if (serigrafia) {
    // Perforaciones de la tapa y etiqueta.
    _serigrafia(g, lt, W, H, (ctx, x, y, k) => {
      ctx.fillStyle = '#23272d';
      for (let px = -lt / 2 + 8; px < lt / 2 - 4; px += 5) for (let py = -W / 2 + 6; py < W / 2 - 5; py += 5)
        if (Math.abs(px + 10) > 32 || Math.abs(py) > 22) { ctx.beginPath(); ctx.arc(x(px), y(py), 1.3 * k, 0, 2 * Math.PI); ctx.fill(); }
      ctx.fillStyle = '#f4f4f0'; ctx.fillRect(x(-42), y(22), 64 * k, 44 * k);
      _texto(ctx, 'LRS-150-12', x(-10), y(12), k, { tam: 6, color: '#1a1a1a', peso: 700, fuente: 'Space Grotesk' });
      _texto(ctx, 'SWITCHING POWER SUPPLY', x(-10), y(4), k, { tam: 2.6, color: '#333' });
      _texto(ctx, 'INPUT 100-240VAC  OUTPUT 12VDC', x(-10), y(-4), k, { tam: 2.4, color: '#333' });
      _texto(ctx, 'L  N  PE  -V  -V  +V  +V', x(-10), y(-14), k, { tam: 2.4, color: '#1a1a1a' });
    }, { cx: -L / 2 + lt / 2, ppm: 6 });
  }
  g.add(ancla('ancla_tornillo_1', Pm(-L / 2 + 20, -W / 2 + 15, 0)));
  g.add(ancla('ancla_tornillo_2', Pm(-L / 2 + 20, W / 2 - 15, 0)));
  return _fin(g, opciones, 'Fuente LRS-150-12');
}

// ---------------------------------------------------------------------------
// Portafusibles de 4 vias (cuchilla ATO) 56 × 36 × 11 mm
// ---------------------------------------------------------------------------
// Base negra con 4 fusibles de cuchilla ATO (19,1 × 5,1 mm; parte visible ~11 mm) con su color
// segun la norma: 1 A negro, 2 A gris, 3 A violeta, 5 A canela, 7,5 A cafe, 10 A rojo, 15 A azul.
// Borne comun IN (-x) y uno de salida por fusible (F1..F4, cable hacia +y). Posiciones de `fusibles4`.
const COLOR_FUSIBLE = { 1: 0x222222, 2: 0x8a8f96, 3: 0x8a2be2, 5: 0xc8a165, 7.5: 0x7a4a24, 10: 0xd23a2a, 15: 0x2d6fd0, 20: 0xe3c22b };
function _fusibleATO(g, x, y, zBase, amperios, nombre) {
  const f = new THREE.Group(); f.name = nombre;
  f.add(caja(5.1 * MM, 19.1 * MM, 11 * MM, COLOR_FUSIBLE[amperios] ?? 0xd23a2a, Pm(x, y, zBase + 5.5), { roughness: 0.25, transparent: true, opacity: 0.92 }));
  f.add(caja(5.3 * MM, 12 * MM, 3.2 * MM, COLOR_FUSIBLE[amperios] ?? 0xd23a2a, Pm(x, y, zBase + 11 - 1.6), { roughness: 0.4 }));
  const t = planoDibujado(5.1 * MM, 12 * MM, (ctx, X, Y, k) => _texto(ctx, String(amperios), X(0), Y(0), k, { tam: 3.2, color: '#ffffff', peso: 700, giro: -Math.PI / 2 }), { ppm: 30 });
  t.position.copy(Pm(x, y, zBase + 11.05));
  f.add(t);
  f.userData.amperios = amperios;
  g.add(f);
}
export function crearPortafusibles4(opciones = {}) {
  const { id = 'fusibles', amperios = [5, 2, 3, 1], serigrafia = true } = opciones;
  const L = 56, W = 36, H = 11;
  const g = new THREE.Group();
  g.name = 'portafusibles_4';
  _cj(g, L, W, H, 0x151515, 0, 0, H / 2, { roughness: 0.6 }, 'base');
  _cj(g, L - 4, W - 4, 0.6, 0x222428, 0, 0, H + 0.3, {});
  _bornes(g, [{ n: 'IN', x: -22, y: 0 }], id, H + 0.6, [-1, 0], { color: 0x2a2a2a });
  _bornes(g, amperios.map((_, i) => ({ n: `F${i + 1}`, x: -8 + i * 10.5, y: 11 })), id, H + 0.6, [0, 1], { color: 0x2a2a2a });
  amperios.forEach((a, i) => _fusibleATO(g, -8 + i * 10.5, -4, H + 0.6, a, `fusible_F${i + 1}`));
  if (serigrafia) _serigrafia(g, L - 4, W - 4, H + 0.6, (ctx, x, y, k) => {
    amperios.forEach((a, i) => _texto(ctx, `F${i + 1}`, x(-8 + i * 10.5), y(-15.3), k, { tam: 1.4, color: '#c9ccd1' }));
  });
  return _fin(g, opciones, 'Portafusibles 4 vias');
}

// ---------------------------------------------------------------------------
// Bornera X2 en riel DIN: 16 bornes de 2,5 mm² (6,2 mm) con puentes
// ---------------------------------------------------------------------------
// Riel TS35 × 7,5 (EN 60715: 35 mm de ala, 27 mm de copa, 7,5 mm de alto) de 100 mm y 16 bornes
// grises de 6,2 × 42 × 35 mm (tipo UK 2,5 / PT 2,5) con su tornillo de cada lado (y = ±8), la
// franja de marcado con el numero y los puentes rojos de `bornera16` ([2,3], [5,6], [7..13]).
// Anclas: pin_<id>_<n> en la boca del lado -y (cable hacia -y) y pin_<id>_<n>_b del lado +y.
export function crearBorneraDIN16(opciones = {}) {
  const { id = 'x2', n = 16, puentes = [['2', '3'], ['5', '6'], ['7', '8', '9', '10', '11', '12', '13']], serigrafia = true } = opciones;
  const paso = 6.2, x0 = -(n - 1) * paso / 2, largoRiel = Math.max(100, n * paso + 4);
  const g = new THREE.Group();
  g.name = 'bornera_din';
  // Riel TS35 (copa hacia abajo, alas arriba).
  const riel = new THREE.Group(); riel.name = 'riel_din';
  riel.add(caja(largoRiel * MM, 27 * MM, 1 * MM, 0xc2c6cc, Pm(0, 0, 0.5), METAL));
  for (const s of [-1, 1]) {
    riel.add(caja(largoRiel * MM, 1 * MM, 7.5 * MM, 0xc2c6cc, Pm(0, s * 13, 3.75), METAL));
    riel.add(caja(largoRiel * MM, 4.5 * MM, 1 * MM, 0xc2c6cc, Pm(0, s * 15.25, 7.0), METAL));
  }
  g.add(riel);
  // Perfil de un borne (y, z en mm): pie con la ranura del riel, cuerpo, rampas y franja superior.
  const perfil = [[-21, 1], [-18, 1], [-18, 8.2], [18, 8.2], [18, 1], [21, 1], [21, 20], [15, 22], [15, 29], [10, 35], [-10, 35], [-15, 29], [-15, 22], [-21, 20]];
  const forma = new THREE.Shape(perfil.map(([y, z]) => new THREE.Vector2(y * MM, z * MM)));
  const geo = new THREE.ExtrudeGeometry(forma, { depth: (paso - 0.3) * MM, bevelEnabled: false });
  // Forma en (u, v) = (y, z) de la simulacion; se lleva a Three: u -> -z, v -> y, extrusion -> x.
  geo.applyMatrix4(new THREE.Matrix4().set(0, 0, 1, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 0, 1));
  geo.translate(-(paso - 0.3) / 2 * MM, 0, 0);
  const matBorne = mat(0x8a9099, PLASTICO);
  const tornillos = [], huecos = [], bocas = [];
  for (let i = 0; i < n; i++) {
    const x = x0 + i * paso, nom = String(i + 1);
    const b = new THREE.Mesh(geo, matBorne);
    b.position.copy(Pm(x, 0, 0));
    b.name = `borne_${nom}`;
    g.add(b);
    for (const s of [-1, 1]) {
      huecos.push(Pm(x, s * 8, 35.03));
      tornillos.push(Pm(x, s * 8, 35.2));
      bocas.push(Pm(x, s * 21.02, 14));
    }
    _pin(g, id, nom, Pm(x, -21, 14), Dm(0, -1, 0));
    _pin(g, id, `${nom}_b`, Pm(x, 21, 14), Dm(0, 1, 0));
  }
  // Tornillos hundidos (en su pozo oscuro) y bocas de los cables.
  g.add(instancias(new THREE.BoxGeometry(4 * MM, 0.06 * MM, 4 * MM), new THREE.MeshBasicMaterial({ color: 0x1a1c1f }), huecos, 'pozos'));
  g.add(instancias(new THREE.CylinderGeometry(1.7 * MM, 1.7 * MM, 0.6 * MM, 14), mat(COLOR.plata, METAL), tornillos, 'tornillos'));
  g.add(instancias(new THREE.BoxGeometry(3.5 * MM, 3.5 * MM, 0.1 * MM), new THREE.MeshBasicMaterial({ color: 0x0a0a0a }), bocas, 'bocas'));
  // Puentes enchufables (peines rojos) en el canal del lado +y.
  for (const grupo of puentes) {
    const xs = grupo.map((t) => x0 + (Number(t) - 1) * paso);
    const xa = Math.min(...xs), xb = Math.max(...xs);
    const p = _cj(g, xb - xa + 4, 2.4, 2.2, 0xd23a2a, (xa + xb) / 2, 4.2, 35 + 1.1, PLASTICO, `puente_${grupo[0]}_${grupo[grupo.length - 1]}`);
    p.userData.bornes = grupo;
  }
  if (serigrafia) _serigrafia(g, n * paso, 4.4, 35, (ctx, x, y, k) => {
    for (let i = 0; i < n; i++) {
      const xx = x0 + i * paso;
      ctx.fillStyle = '#f4f4f0'; ctx.fillRect(x(xx - 2.6), y(2.2), 5.2 * k, 4.4 * k);
      _texto(ctx, String(i + 1), x(xx), y(0), k, { tam: 2.2, color: '#111', peso: 700 });
    }
  }, { cy: -1.0, ppm: 24 });
  return _fin(g, opciones, 'Bornera DIN 16 bornes');
}

// Entrada de red IEC C14 con interruptor y portafusible (modulo 3 en 1, tipo AC-01/KCD).
// Medidas tipicas: frente de 48 × 28 mm y 3 mm, cuerpo de 44 × 25 mm que entra 30 mm en el
// panel, faston de 6,3 mm atras (L, N, PE en x = -8, 0, 8, como `iec` de conexiones.py).
// Origen: centro del hueco del panel, EN el plano del panel; el frente mira a -y, el cuerpo va
// hacia +y (dentro de la caja). Nodos: interruptor (el balancin rojo), cajon_fusible.
export function crearEntradaIEC(opciones = {}) {
  const { id = 'iec' } = opciones;
  const g = new THREE.Group();
  g.name = 'entrada_iec';
  _cj(g, 48, 3, 28, 0x151515, 0, -1.5, 0, PLASTICO, 'frente');
  _cj(g, 44, 30, 25, 0x1c1c1c, 0, 15, 0, PLASTICO, 'cuerpo');
  // Toma C14 (hueco trapezoidal aproximado) con sus 3 espigas.
  _cj(g, 20, 0.2, 13, 0x050505, -9, -3.02, 2.5, {});
  for (const [x, z] of [[-13, 3], [-5, 3], [-9, 6.5]]) _cj(g, 1.5, 5, 3.6, COLOR.plata, x, -1.0, z, METAL);
  const fus = _cj(g, 20, 1.2, 6, 0x222222, -9, -3.6, -8.5, PLASTICO, 'cajon_fusible');
  fus.userData.nota = 'fusible 5 × 20 mm';
  const inter = new THREE.Group(); inter.name = 'interruptor';
  inter.add(caja(13 * MM, 2 * MM, 20 * MM, 0x111111, Pm(12, -4, 0), PLASTICO));
  const bal = caja(11 * MM, 3 * MM, 18 * MM, 0xd23a2a, Pm(12, -5.5, 0), { roughness: 0.3, transparent: true, opacity: 0.9 });
  bal.rotation.x = 0.12;
  inter.add(bal);
  g.add(inter);
  for (const [n, x] of [['L', -8], ['N', 0], ['PE', 8]]) {
    _cj(g, 6.3, 7, 0.8, COLOR.estano, x, 30 + 3.5, 0, METAL);
    _pin(g, id, n, Pm(x, 37, 0), Dm(0, 1, 0));
  }
  return _fin(g, opciones, 'Entrada IEC C14 con interruptor');
}

// Hub USB 2.0 de 4 puertos con fuente propia (100 × 35 × 20 mm, conexiones.py `hub_usb4`):
// puertos P1..P4 en la cara -y (x = -30, -10, 10, 30), USB-B de subida en -x, jack DC en +x y
// un interruptor con LED azul por puerto arriba. Nodos: led_P1..led_P4 (MeshBasic; color para
// encenderlos). Origen: centro de la cara de abajo.
export function crearHubUSB4(opciones = {}) {
  const { id = 'hub_usb' } = opciones;
  const L = 100, W = 35, H = 20;
  const g = new THREE.Group();
  g.name = 'hub_usb4';
  _cj(g, L, W, H - 2, 0x1d2129, 0, 0, (H - 2) / 2, { roughness: 0.45 }, 'cuerpo');
  _cj(g, L - 2, W - 2, 2, 0x2a2f38, 0, 0, H - 1, { roughness: 0.3 }, 'tapa');
  for (let i = 0; i < 4; i++) {
    const x = -30 + i * 20;
    _usbA(g, x, -W / 2, 9, [0, -1], 0x2d6fd0);
    _pin(g, id, `P${i + 1}`, Pm(x, -W / 2, 9), Dm(0, -1, 0));
    _cj(g, 6, 4, 1.2, 0x111111, x, 4, H + 0.6, PLASTICO, `boton_P${i + 1}`);
    const led = new THREE.Mesh(new THREE.CylinderGeometry(1.0 * MM, 1.0 * MM, 0.6 * MM, 12), new THREE.MeshBasicMaterial({ color: 0x3d8bff }));
    led.position.copy(Pm(x, -5, H + 0.3));
    led.name = `led_P${i + 1}`;
    g.add(led);
  }
  // USB-B de subida (12 × 11 mm) y jack DC.
  _cj(g, 1.0, 12, 11, COLOR.plata, -L / 2 - 0.5, 0, 9, METAL);
  _cj(g, 0.2, 8.5, 7.5, 0x050505, -L / 2 - 1.02, 0, 9, {});
  _pin(g, id, 'UP', Pm(-L / 2 - 1, 0, 9), Dm(-1, 0, 0));
  _ciX(g, 4.2, 1.0, 0x0a0a0a, L / 2 + 0.5, 0, 9, {}, 20);
  _ciX(g, 1.0, 1.2, COLOR.plata, L / 2 + 0.6, 0, 9, METAL, 12);
  _pin(g, id, 'DC', Pm(L / 2 + 1, 0, 9), Dm(1, 0, 0));
  _serigrafia(g, L - 2, W - 2, H, (ctx, x, y, k) => {
    _texto(ctx, 'USB 2.0 HUB · 4 PORT', x(-30), y(12), k, { tam: 2.2, color: '#8b949e', alinear: 'left', fuente: 'Space Grotesk' });
    for (let i = 0; i < 4; i++) _texto(ctx, String(i + 1), x(-30 + i * 20 + 5), y(4), k, { tam: 2, color: '#8b949e' });
  }, { ppm: 10 });
  return _fin(g, opciones, 'Hub USB 4 puertos');
}

// ---------------------------------------------------------------------------
// Carro: interruptor + fusible, porta-baterias 2 × 18650
// ---------------------------------------------------------------------------
// Caja impresa de 36 × 16 × 12 mm con un balancin KCD11 (15 × 10 mm) y un fusible de cuchilla
// mini (ATM, 10,9 × 3,6 mm) de 3 A en su ranura. Pines de `interruptor`: 1 (entra B+, cara -x) y
// 2 (sale al carro, cara +x), a 4 mm de alto. Nodo: balancin (rotation.x = ±0,25 = I/O).
export function crearInterruptorFusible(opciones = {}) {
  const { id = 'interruptor', encendido = true, amperios = 3 } = opciones;
  const L = 36, W = 16, H = 12;
  const g = new THREE.Group();
  g.name = 'interruptor_fusible';
  _cj(g, L, W, H, COLOR.impreso, 0, 0, H / 2, { roughness: 0.8 }, 'caja');
  _cj(g, 15, 10, 1.2, 0x111111, -8, 0, H + 0.6, PLASTICO);
  const bal = caja(12 * MM, 7.5 * MM, 3 * MM, 0x151515, Pm(0, 0, 0), PLASTICO);
  const piv = new THREE.Group(); piv.name = 'balancin';
  piv.position.copy(Pm(-8, 0, H + 1.2));
  bal.position.copy(Pm(0, 0, 1.2));
  piv.add(bal);
  piv.rotation.z = encendido ? 0.22 : -0.22;           // giro alrededor de y de la simulacion (Three z)
  g.add(piv);
  const t = planoDibujado(10 * MM, 7 * MM, (ctx, X, Y, k) => { _texto(ctx, 'I', X(-2.5), Y(0), k, { tam: 3 }); _texto(ctx, 'O', X(2.5), Y(0), k, { tam: 3 }); }, { ppm: 30 });
  t.position.copy(Pm(0, 0, 2.75)); piv.add(t);
  // Fusible ATM (mini) asomando 7 mm.
  const f = new THREE.Group(); f.name = 'fusible';
  f.add(caja(3.6 * MM, 10.9 * MM, 7 * MM, COLOR_FUSIBLE[amperios] ?? 0x8a2be2, Pm(9, 0, H + 3.5), { roughness: 0.25, transparent: true, opacity: 0.92 }));
  f.userData.amperios = amperios;
  g.add(f);
  _cj(g, 6, 13, 0.6, 0x111111, 9, 0, H + 0.3, PLASTICO);
  for (const [n, s] of [['1', -1], ['2', 1]]) {
    _cj(g, 1.2, 4.5, 4.5, COLOR.estano, s * (L / 2 + 0.6), 0, 4, METAL);
    _pin(g, id, n, Pm(s * (L / 2 + 1.2), 0, 4), Dm(s, 0, 0));
  }
  return _fin(g, opciones, `Interruptor + fusible ${amperios} A`);
}

// Porta-baterias 2S de dos 18650 lado a lado (ficha tipica 76,6 × 41 × 20,7 mm; la plantilla
// `pack2s` usa 12 mm de alto, aqui va el real). Largo a lo largo de y, como `pack2s`. Celdas de
// 18,4 × 65 mm, en serie (una con el + hacia +y y otra hacia -y), resortes y placas de contacto,
// y las lengüetas B+ / B- en la cara +x (x = 20,5, y = ±30). Nodos: celda_1, celda_2, bms.
export function crearPortaBaterias18650x2(opciones = {}) {
  const { id = 'bateria', celdas = true } = opciones;
  const L = 41, W = 76.6, H = 20.7, e = 1.5;
  const g = new THREE.Group();
  g.name = 'porta_18650_2s';
  const negro = 0x151515;
  _cj(g, L, W, e, negro, 0, 0, e / 2, PLASTICO, 'base');
  for (const s of [-1, 1]) {
    _cj(g, e, W, H - 6, negro, s * (L / 2 - e / 2), 0, e + (H - 6 - e) / 2 + e / 2, PLASTICO);
    _cj(g, L, 3, H - 2, negro, 0, s * (W / 2 - 1.5), (H - 2) / 2, PLASTICO);
  }
  _cj(g, 1.2, W - 6, 5, negro, 0, 0, e + 2.5, PLASTICO);                                           // separador central
  [-1, 1].forEach((sx, i) => {
    const x = sx * 9.6, zc = e + 9.2 + 0.3, sgn = i === 0 ? 1 : -1;               // + hacia +y en la 1
    if (celdas) {
      const c = new THREE.Group(); c.name = `celda_${i + 1}`;
      const cuerpo = cilindro(9.2 * MM, 64 * MM, i ? 0x6a3fb5 : 0x2b59c3, Pm(0, 0, 0), { roughness: 0.35 }, 32);
      cuerpo.rotation.x = Math.PI / 2; c.add(cuerpo);
      const polo = cilindro(3.5 * MM, 1.2 * MM, COLOR.plata, Pm(0, sgn * 32.6, 0), METAL, 20);
      polo.rotation.x = Math.PI / 2; c.add(polo);
      const anillo = cilindro(9.25 * MM, 1.5 * MM, 0xe8e8e8, Pm(0, sgn * 30.5, 0), { roughness: 0.5 }, 32);
      anillo.rotation.x = Math.PI / 2; c.add(anillo);
      c.position.copy(Pm(x, 0, zc));
      g.add(c);
    }
    // Resorte (lado -) y placa (lado +).
    _ciY(g, 3.6, 3.3, COLOR.plata, x, -sgn * 33.65, zc, METAL, 16);
    _cj(g, 9, 0.6, 9, COLOR.plata, x, sgn * 33.6, zc, METAL);
  });
  // BMS 2S (placa chica de 22 × 8 mm) pegado en la cara +x y lengüetas B+ / B-.
  const bms = new THREE.Group(); bms.name = 'bms';
  bms.add(caja(1 * MM, 22 * MM, 8 * MM, 0x1d4f9c, Pm(L / 2 + 0.5, 0, 10), {}));
  bms.add(caja(0.6 * MM, 3 * MM, 3 * MM, COLOR.chip, Pm(L / 2 + 1.3, -4, 10), {}));
  bms.add(caja(0.6 * MM, 3 * MM, 3 * MM, COLOR.chip, Pm(L / 2 + 1.3, 4, 10), {}));
  g.add(bms);
  for (const [n, y, c] of [['B+', 30, 0xd23a2a], ['B-', -30, 0x1a1a1a]]) {
    _cj(g, 0.5, 4, 6, COLOR.estano, L / 2 + 0.25, y, 10, METAL);
    _cj(g, 0.3, 2, 2, c, L / 2 + 0.65, y, 14.5, {});
    _pin(g, id, n, Pm(L / 2 + 0.5, y, 10), Dm(1, 0, 0));
  }
  return _fin(g, opciones, 'Porta-baterias 2 × 18650');
}

// ---------------------------------------------------------------------------
// Motores paso a paso: NEMA17 17HS4401 y 28BYJ-48
// ---------------------------------------------------------------------------
// NEMA17 17HS4401: 42,3 × 42,3 × 40 mm, chaflan de las esquinas ~4,5 mm, tapas negras y paquete
// de laminas plateado, resalte de Ø22 × 2 mm, eje de Ø5 × 24 mm con plano (D), 4 agujeros M3 a
// 31 mm, conector JST-PH de 6 vias en una cara lateral cerca de la tapa trasera.
// Origen: centro de la CARA DE MONTAJE (frente); el eje sale hacia +z y el cuerpo baja hasta
// z = -40. Nodos: eje (girar con rotation.y de Three = giro alrededor de z de la simulacion).
// Anclas: ancla_eje (punta), ancla_tornillo_1..4, pin_<id>_JST (boca del conector, hacia -x).
export function crearNEMA17(opciones = {}) {
  const { id = 'nema17', largo = 40 } = opciones;
  const a = 42.3, tapa = 8;
  const g = new THREE.Group();
  g.name = 'nema17';
  const tapaNegra = { roughness: 0.5, metalness: 0.3 };
  _prisma(g, _cuadradoChaflan(a, 4.5), tapa, 0x1c1e22, -tapa, tapaNegra, 'tapa_frontal');
  _prisma(g, _cuadradoChaflan(a - 0.6, 4.8), largo - 2 * tapa, 0xb8bcc2, -largo + tapa, METAL, 'laminas');
  _prisma(g, _cuadradoChaflan(a, 4.5), tapa, 0x1c1e22, -largo, tapaNegra, 'tapa_trasera');
  _ci(g, 11, 2, 0x1c1e22, 0, 0, 1, tapaNegra, 40);
  const eje = new THREE.Group(); eje.name = 'eje';
  eje.add(cilindro(2.5 * MM, 24 * MM, 0xd0d3d8, Pm(0, 0, 12), METAL, 20));
  eje.add(caja(3.0 * MM, 0.5 * MM, 15 * MM, 0x9aa0a8, Pm(0, 2.0, 24 - 7.5), METAL));                 // plano D
  g.add(eje);
  g.add(ancla('ancla_eje', Pm(0, 0, 24)));
  [[1, 1], [-1, 1], [-1, -1], [1, -1]].forEach(([sx, sy], i) => {
    _ci(g, 1.5, 0.2, 0x050505, sx * 15.5, sy * 15.5, 0.05, {}, 14);
    g.add(ancla(`ancla_tornillo_${i + 1}`, Pm(sx * 15.5, sy * 15.5, 0)));
  });
  // Conector JST-PH de 6 vias (blanco) en la cara -x, sobre la tapa trasera.
  _cj(g, 4.5, 14, 6, 0xf2f0e6, -a / 2 - 2.25, 0, -largo + 4, PLASTICO, 'conector');
  _cj(g, 0.1, 12, 3.5, 0x151515, -a / 2 - 4.52, 0, -largo + 4, {});
  _pin(g, id, 'JST', Pm(-a / 2 - 4.5, 0, -largo + 4), Dm(-1, 0, 0));
  return _fin(g, opciones, 'NEMA17 17HS4401');
}

// 28BYJ-48 (5 V): cuerpo Ø28 × 19 mm, pestañas de 42 mm con agujeros Ø4,2 a 35 mm (en y), eje
// de Ø5 con dos planos (3 mm) y 6 mm de largo sobre un resalte de Ø9 × 1,5 mm, DESCENTRADO 8 mm
// hacia +x; caja azul de los cables hacia -x y cable de 5 hilos al JST-XH (en el ULN2003).
// Origen: eje del cuerpo en la cara de las pestañas (montaje); eje hacia +z. Nodo: eje.
export function crear28BYJ48(opciones = {}) {
  const { id = 'motor_carrusel' } = opciones;
  const g = new THREE.Group();
  g.name = 'motor_28byj48';
  _ci(g, 14, 19, 0xc9c9c9, 0, 0, -9.5, METAL, 40, 'cuerpo');
  _prisma(g, [[-3.5, -21], [3.5, -21], [3.5, 21], [-3.5, 21]], 0.8, 0xc9c9c9, -0.8, METAL, 'pestanas');
  for (const s of [-1, 1]) { _ci(g, 3.5, 0.8, 0xc9c9c9, 0, s * 17.5, -0.4, METAL, 20); _ci(g, 2.1, 0.9, 0x050505, 0, s * 17.5, -0.4, {}, 16); }
  _ci(g, 4.5, 1.5, 0xc9c9c9, 8, 0, 0.75, METAL, 24);
  const eje = new THREE.Group(); eje.name = 'eje';
  eje.add(cilindro(2.5 * MM, 6 * MM, 0xd8b04a, Pm(8, 0, 1.5 + 3), METAL, 20));
  for (const s of [-1, 1]) eje.add(caja(5.2 * MM, 1.0 * MM, 5 * MM, 0xb08a30, Pm(8, s * 1.9, 1.5 + 3.5), METAL));   // planos
  g.add(eje);
  g.add(ancla('ancla_eje', Pm(8, 0, 7.5)));
  _cj(g, 5, 15, 16, 0x2a5fb0, -15.5, 0, -9.5, PLASTICO, 'caja_cables');
  for (const s of [-1, 1]) g.add(ancla(`ancla_tornillo_${s > 0 ? 1 : 2}`, Pm(0, s * 17.5, 0)));
  _pin(g, id, 'CABLE', Pm(-18, 0, -14), Dm(-1, 0, 0));
  return _fin(g, opciones, 'Motor 28BYJ-48');
}

// ---------------------------------------------------------------------------
// Servos SG90 y MG996R con su cuerno
// ---------------------------------------------------------------------------
// SG90 (ficha TowerPro): cuerpo 22,5 × 11,8 × 22,7 mm, pestañas de 32,2 mm de 2,5 mm de espesor
// con la cara de abajo a 15,9 mm del fondo, agujeros a 27,5 mm, eje a 5,9 mm de un extremo
// (en el centro del resalte), estriado de Ø4,8 a ~29 mm del fondo. Azul translucido.
// MG996R (ficha TowerPro): 40,7 × 19,7 × 42,9 mm, pestañas de 54 mm (agujeros a 49,5 mm) con la
// cara de abajo a 27 mm del fondo, eje a 9,85 mm del extremo, estriado 25T de Ø5,8. Negro.
// Origen: EJE del servo en el plano de la cara de abajo de las pestañas (donde se atornilla al
// soporte); el cuerpo cuelga hacia -z y el eje sale hacia +z; el cuerpo se extiende hacia -x.
// Nodos: cuerno (girar con rotation.y de Three = alrededor de z; `angulo` en grados lo deja
// puesto), cuerpo. Anclas: ancla_eje (arriba del estriado), ancla_cuerno_punta (hijo del cuerno,
// en el ultimo agujero del brazo), pin_<id>_CABLE (boca del conector JR, hacia -x),
// ancla_tornillo_1/2 (agujeros de las pestañas).
// opciones: modelo 'SG90' | 'MG996R', cuerno 'brazo' | 'doble' | 'cruz' | 'disco', angulo (0).
const SERVOS = {
  SG90: { L: 22.5, W: 11.8, alto: 22.7, zPest: 15.9, lPest: 32.2, ePest: 2.5, agujeros: 27.5, rAg: 1.0, dEje: 5.9,
    rResalte: 5.9, hResalte: 4.0, rEstriado: 2.4, hEstriado: 2.3, color: 0x2458b3, brazo: 16, anchoBrazo: 5.5, rCubo: 3.6, opacidad: 1 },
  MG996R: { L: 40.7, W: 19.7, alto: 36.9, zPest: 27.0, lPest: 54.0, ePest: 2.5, agujeros: 49.5, rAg: 2.2, dEje: 9.85,
    rResalte: 6.5, hResalte: 3.0, rEstriado: 2.9, hEstriado: 3.0, color: 0x151515, brazo: 20, anchoBrazo: 7, rCubo: 5, opacidad: 1 },
};
export function crearServo(opciones = {}) {
  const { modelo = 'SG90', cuerno = 'brazo', angulo = 0 } = opciones;
  const d = SERVOS[modelo];
  if (!d) throw new Error(`Servo ${modelo}: no existe (SG90 o MG996R)`);
  const id = opciones.id || `servo_${modelo.toLowerCase()}`;
  const g = new THREE.Group();
  g.name = `servo_${modelo.toLowerCase()}`;
  const xc = -(d.L / 2 - d.dEje);                    // centro del cuerpo (el eje queda en x = 0)
  const zFondo = -d.zPest, zTope = d.alto - d.zPest;
  const extra = d.opacidad < 1 ? { roughness: 0.3, transparent: true, opacity: d.opacidad } : { roughness: 0.45 };
  const cuerpo = new THREE.Group(); cuerpo.name = 'cuerpo';
  cuerpo.add(caja(d.L * MM, d.W * MM, d.alto * MM, d.color, Pm(xc, 0, (zFondo + zTope) / 2), extra));
  cuerpo.add(caja(d.lPest * MM, d.W * MM, d.ePest * MM, d.color, Pm(xc, 0, d.ePest / 2), extra));
  cuerpo.add(cilindro(d.rResalte * MM, d.hResalte * MM, d.color, Pm(0, 0, zTope + d.hResalte / 2), extra, 28));
  if (modelo === 'SG90') cuerpo.add(cilindro(2.8 * MM, 1.6 * MM, d.color, Pm(-6.2, 0, zTope + 0.8), extra, 20));
  g.add(cuerpo);
  for (const s of [-1, 1]) {
    _ci(g, d.rAg, d.ePest + 0.1, 0x050505, xc + s * d.agujeros / 2, 0, d.ePest / 2, {}, 14);
    g.add(ancla(`ancla_tornillo_${s > 0 ? 1 : 2}`, Pm(xc + s * d.agujeros / 2, 0, 0)));
  }
  // Etiqueta arriba, entre el extremo -x y el resalte del eje.
  const xa = xc - d.L / 2 + 0.6, xb = -d.rResalte - (modelo === 'SG90' ? 4.0 : 0) - 0.4;
  const et = planoDibujado((xb - xa) * MM, (d.W - 2) * MM, (ctx, X, Y, k) => {
    _texto(ctx, modelo, X(0), Y(0), k, { tam: modelo === 'SG90' ? 2.0 : 3.2, color: modelo === 'SG90' ? '#eef2fa' : '#c8cdd4', peso: 700, fuente: 'Space Grotesk' });
  }, { ppm: 24 });
  et.position.copy(Pm((xa + xb) / 2, 0, zTope + 0.03));
  g.add(et);
  // Cable plano de 3 hilos (cafe, rojo, naranja) que sale del extremo -x y conector JR.
  const xCable = xc - d.L / 2, zCable = zFondo + 4, largoCable = 22;
  [0x6b3a1f, 0xd23a2a, 0xe8901c].forEach((c, j) => _ciX(g, 0.5, largoCable, c, xCable - largoCable / 2, (j - 1) * 1.0, zCable, {}, 8));
  _cj(g, 14, 7.6, 2.6, 0x151515, xCable - largoCable - 7, 0, zCable, PLASTICO, 'conector');
  _pin(g, id, 'CABLE', Pm(xCable - largoCable - 14, 0, zCable), Dm(-1, 0, 0));
  // Estriado + cuerno (el cuerno gira; el estriado va con el).
  const zE = zTope + d.hResalte;
  const c = new THREE.Group(); c.name = 'cuerno';
  c.add(cilindro(d.rEstriado * MM, d.hEstriado * MM, 0xe8e8e8, Pm(0, 0, zE + d.hEstriado / 2), {}, 16));
  const zC = zE + 0.3, hC = 1.8, blanco = 0xf2f2f2;
  c.add(cilindro(d.rCubo * MM, (d.hEstriado + 1.6) * MM, blanco, Pm(0, 0, zC + (d.hEstriado + 1.6) / 2), PLASTICO, 24));
  const zBrazo = zC + d.hEstriado + 1.6 - hC / 2;
  const brazo = (ang, largo) => {
    const b = new THREE.Group(); b.rotation.y = ang;
    const forma = new THREE.Shape();
    const r0 = d.anchoBrazo / 2, r1 = d.anchoBrazo / 3.5;
    forma.moveTo(0, -r0 * MM); forma.lineTo(largo * MM, -r1 * MM); forma.absarc(largo * MM, 0, r1 * MM, -Math.PI / 2, Math.PI / 2, false);
    forma.lineTo(0, r0 * MM); forma.lineTo(0, -r0 * MM);
    const geo = new THREE.ExtrudeGeometry(forma, { depth: hC * MM, bevelEnabled: false });
    geo.rotateX(-Math.PI / 2);
    const m = new THREE.Mesh(geo, mat(blanco, PLASTICO)); m.position.copy(Pm(0, 0, zBrazo - hC / 2)); b.add(m);
    const nAg = Math.max(3, Math.round(largo / 3.2));
    for (let i = 1; i < nAg; i++) b.add(cilindro(0.45 * MM, (hC + 0.1) * MM, 0x2a2a2a, Pm(largo * i / nAg + 1.5, 0, zBrazo), {}, 8));
    c.add(b);
  };
  if (cuerno === 'disco') {
    c.add(cilindro((d.brazo * 0.55) * MM, hC * MM, blanco, Pm(0, 0, zBrazo), PLASTICO, 40));
    for (let i = 0; i < 8; i++) c.add(cilindro(0.5 * MM, (hC + 0.1) * MM, 0x2a2a2a, Pm(Math.cos(i * Math.PI / 4) * d.brazo * 0.42, Math.sin(i * Math.PI / 4) * d.brazo * 0.42, zBrazo), {}, 8));
  } else {
    brazo(0, d.brazo);
    if (cuerno === 'doble' || cuerno === 'cruz') brazo(Math.PI, d.brazo * 0.85);
    if (cuerno === 'cruz') { brazo(Math.PI / 2, d.brazo * 0.7); brazo(-Math.PI / 2, d.brazo * 0.7); }
  }
  c.add(cilindro(1.2 * MM, 0.6 * MM, COLOR.plata, Pm(0, 0, zBrazo + hC / 2 + 0.3), METAL, 12));   // tornillo
  const puntaR = cuerno === 'disco' ? d.brazo * 0.42 : d.brazo * (1 - 1 / Math.max(3, Math.round(d.brazo / 3.2))) + 1.5;
  c.add(ancla('ancla_cuerno_punta', Pm(puntaR, 0, zBrazo + hC / 2)));
  c.rotation.y = angulo * Math.PI / 180;
  g.add(c);
  g.add(ancla('ancla_eje', Pm(0, 0, zE)));
  g.userData.modelo = modelo;
  return _fin(g, opciones, `Servo ${modelo}`);
}
export const crearServoSG90 = (o = {}) => crearServo({ ...o, modelo: 'SG90' });
export const crearServoMG996R = (o = {}) => crearServo({ ...o, modelo: 'MG996R' });
