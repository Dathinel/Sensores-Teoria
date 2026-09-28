// Pista del carro (punto 14): lamina blanca con borde, linea de cinta aislante, franjas de
// meta y de giro, los tres muros-obstaculo, la bandera de meta y el piso del salon alrededor.
//
// Todo en METROS y en el marco de la simulacion (x, y en el piso, z arriba), como base.js.
// La LINEA CENTRAL no se inventa aqui: llega ya muestreada desde sim/geometria.py
// (`G.pista.linea`, un punto cada 2 cm, generada por sim/pista.py con los tramos de
// config/parametros.yaml). El carro de la simulacion sigue EXACTAMENTE esa linea, asi que este
// modulo solo la viste: nunca la mueve ni la suaviza.
//
// Medidas (config/parametros.yaml, bloque `pista` y `vehiculo`):
//   - lamina: 160 mm de ancho (`ancho_mm`), vinilo/carton blanco de ~1 mm, con un borde
//     pintado de 8 mm a cada lado. Se alarga antes de la salida (el visor pasa `antesSalida` =
//     medio carro + 5 mm: no se mete bajo los topes del muelle) y 15 cm despues de la
//     meta para que el carro (180 mm de largo) nunca quede con media rueda fuera.
//   - linea: cinta aislante negra de 19 mm (`ancho_linea_mm`, la medida estandar del rollo).
//     En las curvas (radio 300 mm) la cinta no se deja doblar plana, asi que se pega en
//     pedazos de ~10 cm montados uno sobre otro: se ve la costura de cada union.
//   - franja de meta: 50 mm (`franja_meta_ancho_mm`) = 3 tiras de cinta de 19 mm montadas;
//     franja de giro: 20 mm (`franja_giro_ancho_mm`) = una tira. Las dos de lado a lado de la
//     pista (las ven los 5 infrarrojos a la vez). Negras lisas: una franja a cuadros
//     confundiria a los sensores; los cuadros van solo en la bandera.
//   - muros: 100 mm a lo ancho de la pista x 30 mm a lo largo x 80 mm de alto
//     (`obstaculo_largo_mm`, `obstaculo_grueso_mm`, `obstaculo_alto_mm`): cuatro hiladas de
//     ladrillo de juguete de 48 x 30 x 18 mm con junta de 2 mm (trabados, medio ladrillo en
//     las hiladas impares).
//   - bandera (a 45 mm del canto de la lamina): mastil de aluminio de 6 mm y 250 mm sobre una base redonda de 60 mm, pano a
//     cuadros de 90 x 60 mm (cuadros de 15 mm).
//   - piso: baldosa de 30 cm alrededor de la pista, con el margen de piso libre de
//     `zonas_carro.margen_zona_libre_mm` (300 mm) por donde el carro puede andar por orden.

import * as THREE from 'three';
import { MM, COLOR, P, mat, caja, cilindro, ancla, planoDibujado, terminar } from './base.js';

// Alturas (z) de cada capa, de abajo hacia arriba. Los espesores reales son de decimas de
// milimetro; se separan un poco mas para que la tarjeta de video no las mezcle de lejos.
const Z_PISO = 0.0007;           // encima de la grilla del visor (0,5 mm)
const Z_LAMINA = 0.0016;         // cara de arriba de la lamina (misma altura de antes)
const Z_BORDE = 0.0017;
const Z_CINTA = 0.0019;
const Z_COSTURA = 0.0021;
const Z_FRANJA = 0.0022;

// ---------------------------------------------------------------------------
// ayudantes de geometria a lo largo de la linea
// ---------------------------------------------------------------------------

// Direccion de avance (unitaria) y normal hacia la IZQUIERDA en cada punto [x, y].
function marcos(pts) {
  return pts.map((_, i) => {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)];
    let dx = b[0] - a[0], dy = b[1] - a[1];
    const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
    return { t: [dx, dy], n: [-dy, dx] };
  });
}

// Tira horizontal entre dos distancias laterales (a < b, medidas hacia la izquierda de la
// linea) a la altura z. Con UV: u = metros recorridos, v = 0..1 de lado a lado.
function tira(pts, mrc, a, b, z, material) {
  const pos = [], uv = [], idx = [];
  let s = 0;
  for (let i = 0; i < pts.length; i++) {
    if (i > 0) s += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    const [nx, ny] = mrc[i].n;
    const pa = P(pts[i][0] + nx * a, pts[i][1] + ny * a, z), pb = P(pts[i][0] + nx * b, pts[i][1] + ny * b, z);
    pos.push(pa.x, pa.y, pa.z, pb.x, pb.y, pb.z);
    uv.push(s, 0, s, 1);
    if (i > 0) { const k = 2 * i; idx.push(k - 2, k, k - 1, k - 1, k, k + 1); }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  // La cara de arriba tiene que mirar hacia arriba (y de Three): si el orden salio al reves,
  // se da vuelta (si no, la luz la dejaria negra).
  if (geo.attributes.normal.getY(0) < 0) {
    const inv = [];
    for (let i = 0; i < idx.length; i += 3) inv.push(idx[i], idx[i + 2], idx[i + 1]);
    geo.setIndex(inv);
    geo.computeVertexNormals();
  }
  const m = new THREE.Mesh(geo, material);
  m.receiveShadow = true;
  return m;
}

// Canto vertical de la lamina a una distancia lateral `d`, de z0 a z1.
function canto(pts, mrc, d, z0, z1, material) {
  const pos = [], idx = [];
  for (let i = 0; i < pts.length; i++) {
    const [nx, ny] = mrc[i].n;
    const p0 = P(pts[i][0] + nx * d, pts[i][1] + ny * d, z0), p1 = P(pts[i][0] + nx * d, pts[i][1] + ny * d, z1);
    pos.push(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z);
    if (i > 0) { const k = 2 * i; idx.push(k - 2, k, k - 1, k - 1, k, k + 1); }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  return new THREE.Mesh(geo, material);
}

// Muchas copias giradas en el plano del piso (rumbo = giro alrededor de z de la simulacion,
// que es girar en y de Three con el mismo signo). Una sola InstancedMesh.
function instanciasGiradas(geometria, material, lista, nombre) {
  const im = new THREE.InstancedMesh(geometria, material, lista.length);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), uno = new THREE.Vector3(1, 1, 1), eje = new THREE.Vector3(0, 1, 0);
  lista.forEach((e, i) => im.setMatrixAt(i, m.compose(e.p, q.setFromAxisAngle(eje, e.rumbo), uno)));
  im.instanceMatrix.needsUpdate = true;
  im.receiveShadow = true;
  if (nombre) im.name = nombre;
  return im;
}

// Punto (x, y, rumbo) de la linea a una distancia recorrida `s` (interpolado).
function puntoEn(pts, acum, s) {
  let i = 1;
  while (i < pts.length - 1 && acum[i] < s) i++;
  const a = pts[i - 1], b = pts[i];
  const t = acum[i] > acum[i - 1] ? Math.min(1, Math.max(0, (s - acum[i - 1]) / (acum[i] - acum[i - 1]))) : 0;
  return { x: a[0] + (b[0] - a[0]) * t, y: a[1] + (b[1] - a[1]) * t, rumbo: Math.atan2(b[1] - a[1], b[0] - a[0]) };
}

// ---------------------------------------------------------------------------
// texturas
// ---------------------------------------------------------------------------

// Baldosa de 30 cm (gris oscuro, para no romper el tema oscuro del visor), con junta y un
// moteado suave. La textura cubre 2 x 2 baldosas y se repite.
function texturaBaldosa() {
  const c = document.createElement('canvas'); c.width = 256; c.height = 256;
  const ctx = c.getContext('2d');
  const tonos = ['#232932', '#252b34', '#21272f', '#242a33'];
  for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) {
    ctx.fillStyle = tonos[i * 2 + j];
    ctx.fillRect(i * 128, j * 128, 128, 128);
  }
  let semilla = 7;
  const azar = () => ((semilla = (semilla * 16807) % 2147483647) / 2147483647);
  for (let k = 0; k < 1400; k++) {
    ctx.fillStyle = azar() < 0.5 ? 'rgba(255,255,255,0.035)' : 'rgba(0,0,0,0.06)';
    ctx.fillRect(azar() * 256, azar() * 256, 2, 2);
  }
  ctx.fillStyle = '#171c23';
  for (const k of [0, 128]) { ctx.fillRect(k, 0, 3, 256); ctx.fillRect(0, k, 256, 3); }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 8;
  return t;
}

// Pano de la bandera: 6 x 4 cuadros de 15 mm (90 x 60 mm).
function texturaCuadros() {
  const c = document.createElement('canvas'); c.width = 96; c.height = 64;
  const ctx = c.getContext('2d');
  for (let i = 0; i < 6; i++) for (let j = 0; j < 4; j++) {
    ctx.fillStyle = (i + j) % 2 ? '#111214' : '#f3f3f0';
    ctx.fillRect(i * 16, j * 16, 16, 16);
  }
  const t = new THREE.CanvasTexture(c);
  t.magFilter = THREE.NearestFilter;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// ---------------------------------------------------------------------------
// piezas
// ---------------------------------------------------------------------------

// Muro-obstaculo de ladrillos de juguete. Origen: centro de la base, apoyado en la lamina.
// Marco local: x = a lo largo de la pista (grueso), y = a lo ancho (largo), z arriba.
export function crearMuroLadrillo({ largo = 100 * MM, grueso = 30 * MM, alto = 80 * MM, nombre = 'muro', semilla = 1 } = {}) {
  const g = new THREE.Group();
  g.name = nombre;
  const junta = 2 * MM;
  const hiladas = Math.max(1, Math.round(alto / (20 * MM)));
  const hAlto = alto / hiladas - junta;                 // 18 mm
  const entero = (largo - 3 * junta) / 2;               // 48 mm (dos por hilada + juntas)
  const medio = (largo - 4 * junta - entero) / 2;       // 23 mm (hiladas trabadas)
  // Mortero: el nucleo gris que asoma en las juntas.
  // (un poco mas bajo y mas corto que los ladrillos: asoma solo en las juntas, sin encimarse).
  // Largo: 1 mm menos que la hilada (los ladrillos terminan a largo/2 - junta = 48 mm del centro;
  // con largo - 4 mm el mortero terminaba en el MISMO plano y las puntas del muro parpadeaban
  // entre gris y ladrillo, 2026-09-28).
  g.add(caja(grueso - 3 * MM, largo - 2 * junta - 1 * MM, alto - 3 * MM, mat(0xb9b3a8, { roughness: 1 }), P(0, 0, (alto - 3 * MM) / 2)));
  const enteros = [], medios = [];
  for (let k = 0; k < hiladas; k++) {
    const z = k * (hAlto + junta) + junta / 2 + hAlto / 2;
    if (k % 2 === 0) {
      for (const s of [-1, 1]) enteros.push(P(0, s * (entero / 2 + junta / 2), z));
    } else {
      enteros.push(P(0, 0, z));
      for (const s of [-1, 1]) medios.push(P(0, s * (entero / 2 + junta + medio / 2), z));
    }
  }
  const matLadrillo = mat(0xffffff, { roughness: 0.92 });
  const tonos = [0xa9472f, 0xb65238, 0x9b3f2b, 0xae4a30, 0xa04330];
  let i = semilla;
  for (const [lista, ancho, nom] of [[enteros, entero, 'ladrillos'], [medios, medio, 'medios_ladrillos']]) {
    if (!lista.length) continue;
    const geo = new THREE.BoxGeometry(grueso, hAlto, ancho);
    const im = new THREE.InstancedMesh(geo, matLadrillo, lista.length);
    const m = new THREE.Matrix4(), color = new THREE.Color();
    lista.forEach((p, j) => {
      im.setMatrixAt(j, m.makeTranslation(p.x, p.y, p.z));
      im.setColorAt(j, color.setHex(tonos[(i++ * 7 + j) % tonos.length]));
    });
    im.instanceMatrix.needsUpdate = true;
    im.castShadow = true;        // son pocos y grandes: la sombra del muro si se nota
    im.receiveShadow = true;
    im.name = nom;
    g.add(im);
  }
  return terminar(g);
}

// Bandera de meta: base redonda con peso, mastil de aluminio y pano a cuadros ondulado.
// Origen: centro de la base, en el piso. El pano sale hacia +x local.
export function crearBanderaMeta({ altoMastil = 250 * MM } = {}) {
  const g = new THREE.Group();
  g.name = 'bandera_meta';
  g.add(cilindro(30 * MM, 8 * MM, mat(0x2d3138, { roughness: 0.5, metalness: 0.6 }), P(0, 0, 4 * MM)));
  g.add(cilindro(8 * MM, 10 * MM, mat(0x3a3f47, { roughness: 0.5, metalness: 0.6 }), P(0, 0, 13 * MM)));   // buje
  g.add(cilindro(3 * MM, altoMastil, mat(COLOR.aluminio, { metalness: 0.85, roughness: 0.3 }), P(0, 0, altoMastil / 2 + 8 * MM), undefined, 16));
  const bola = new THREE.Mesh(new THREE.SphereGeometry(5 * MM, 16, 12), mat(COLOR.oro, { metalness: 0.8, roughness: 0.3 }));
  bola.position.copy(P(0, 0, altoMastil + 12 * MM));
  g.add(bola);
  // Pano de 90 x 60 mm, con una onda suave (tela), prendido del mastil por su borde.
  const L = 90 * MM, H = 60 * MM;
  const geo = new THREE.PlaneGeometry(L, H, 18, 1);
  const pos = geo.attributes.position;
  for (let k = 0; k < pos.count; k++) {
    const u = (pos.getX(k) + L / 2) / L;                       // 0 en el mastil, 1 en la punta
    pos.setZ(k, Math.sin(u * Math.PI * 2.2) * 6 * MM * u);
  }
  geo.translate(L / 2 + 3 * MM, 0, 0);
  geo.computeVertexNormals();
  const pano = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: texturaCuadros(), side: THREE.DoubleSide, roughness: 0.85 }));
  pano.name = 'bandera';
  pano.position.copy(P(0, 0, altoMastil + 8 * MM - H / 2 - 4 * MM));
  pano.castShadow = true;
  g.add(pano);
  g.add(ancla('ancla_punta_mastil', P(0, 0, altoMastil + 17 * MM)));
  return terminar(g);
}

// Rotulo impreso en el margen de la lamina (tinta gris sobre blanco).
function rotulo(texto, largo, ancho, color = '#3b4048') {
  return planoDibujado(largo, ancho, (ctx, X, Y, k) => {
    ctx.fillStyle = color;
    ctx.font = `700 ${Math.round(ancho / MM * 0.72 * k)}px "Space Grotesk", "IBM Plex Mono", sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(texto, X(0), Y(0));
  }, { ppm: 12 });
}

// Pista completa. `linea`: [[x, y], ...] de G.pista.linea. `obstaculos`: [{x, y, rumbo, largo,
// alto}]. `franjaMeta` / `franjaGiro`: {x, y, rumbo, ancho}. `meta`: {x, y, rumbo}.
// Hijos con nombre: `piso_pista` (el piso del salon: NO es parte de la pista), `lamina`,
// `borde_lamina`, `cinta_linea`, `costuras_cinta`, `franja_meta`, `franja_giro`,
// `muro_1..3`, `bandera_meta`, `rotulos`; anclas `ancla_mastil_meta` (base del mastil) y
// `ancla_muro_1..3` (centro de la cara de arriba de cada muro, para su etiqueta).
export function crearPista({
  linea, ancho = 160 * MM, anchoLinea = 19 * MM, obstaculos = [], grueso = 30 * MM,
  franjaMeta = null, franjaGiro = null, meta = null,
  antesSalida = 0.12, despuesMeta = 0.15, margenPiso = 0.30, borde = 8 * MM,
} = {}) {
  const g = new THREE.Group();
  g.name = 'pista';

  // Distancia recorrida en cada muestra de la linea.
  const acum = [0];
  for (let i = 1; i < linea.length; i++) acum.push(acum[i - 1] + Math.hypot(linea[i][0] - linea[i - 1][0], linea[i][1] - linea[i - 1][1]));
  const mrcLinea = marcos(linea);

  // Lamina: la misma linea, alargada en recta antes de la salida y despues de la meta.
  const prolongar = (p, t, d, sgn) => {
    const n = Math.max(1, Math.round(d / 0.02)), out = [];
    for (let k = 1; k <= n; k++) out.push([p[0] + sgn * t[0] * d * k / n, p[1] + sgn * t[1] * d * k / n]);
    return out;
  };
  const ext = [
    ...prolongar(linea[0], mrcLinea[0].t, antesSalida, -1).reverse(),
    ...linea,
    ...prolongar(linea[linea.length - 1], mrcLinea[linea.length - 1].t, despuesMeta, 1),
  ];
  const mrcExt = marcos(ext);
  const W = ancho / 2;

  // ---- Piso del salon alrededor (baldosa de 30 cm), rectangulo de la zona libre.
  const xs = ext.map((q) => q[0]), ys = ext.map((q) => q[1]);
  const m = W + margenPiso;
  const x0 = Math.min(...xs) - m, x1 = Math.max(...xs) + m, y0 = Math.min(...ys) - m, y1 = Math.max(...ys) + m;
  const tex = texturaBaldosa();
  tex.repeat.set((x1 - x0) / 0.6, (y1 - y0) / 0.6);
  const piso = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, y1 - y0), new THREE.MeshStandardMaterial({ map: tex, roughness: 0.95 }));
  piso.rotation.x = -Math.PI / 2;
  piso.position.copy(P((x0 + x1) / 2, (y0 + y1) / 2, Z_PISO));
  piso.receiveShadow = true;
  piso.name = 'piso_pista';
  g.add(piso);

  // ---- Lamina blanca (vinilo/carton de ~1 mm) con su canto y el borde pintado.
  const lamina = tira(ext, mrcExt, -W, W, Z_LAMINA, mat(0xeeede8, { roughness: 0.82 }));
  lamina.name = 'lamina';
  g.add(lamina);
  const matCanto = mat(0xcfccc3, { roughness: 0.9, side: THREE.DoubleSide });
  for (const d of [-W, W]) g.add(canto(ext, mrcExt, d, Z_PISO, Z_LAMINA, matCanto));
  // Tapas de los dos extremos de la lamina.
  for (const [q, t] of [[ext[0], mrcExt[0].t], [ext[ext.length - 1], mrcExt[ext.length - 1].t]]) {
    const tapa = caja(0.0006, ancho, Z_LAMINA - Z_PISO, matCanto, P(q[0], q[1], (Z_LAMINA + Z_PISO) / 2));
    tapa.rotation.y = Math.atan2(t[1], t[0]);
    tapa.castShadow = false;
    g.add(tapa);
  }
  // polygonOffset (como la cinta): el borde va 0,1 mm sobre la lamina y de lejos se mezclaban.
  const matBorde = mat(0xb23a2e, { roughness: 0.8, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
  const bordeIzq = tira(ext, mrcExt, W - borde, W, Z_BORDE, matBorde);
  const bordeDer = tira(ext, mrcExt, -W, -W + borde, Z_BORDE, matBorde);
  bordeIzq.name = 'borde_lamina'; bordeDer.name = 'borde_lamina';
  g.add(bordeIzq, bordeDer);

  // ---- Cinta aislante de 19 mm sobre la linea central (vinilo negro con algo de brillo).
  const matCinta = mat(0x0c0c0d, { roughness: 0.38, metalness: 0.0, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
  const cinta = tira(linea, mrcLinea, -anchoLinea / 2, anchoLinea / 2, Z_CINTA, matCinta);
  cinta.name = 'cinta_linea';
  g.add(cinta);

  // Costuras: en cada cambio de tramo (recta <-> curva) y cada ~10 cm dentro de las curvas,
  // donde la cinta se pega en pedazos. Se detecta la curva por el cambio de rumbo entre
  // muestras (0,067 rad cada 2 cm en radio 300 mm; el redondeo de 0,1 mm da < 0,01 en recta).
  const curva = [];
  for (let i = 1; i < linea.length - 1; i++) {
    const r0 = Math.atan2(linea[i][1] - linea[i - 1][1], linea[i][0] - linea[i - 1][0]);
    const r1 = Math.atan2(linea[i + 1][1] - linea[i][1], linea[i + 1][0] - linea[i][0]);
    let d = r1 - r0; d = Math.atan2(Math.sin(d), Math.cos(d));
    curva[i] = Math.abs(d) > 0.03;
  }
  curva[0] = curva[1]; curva[linea.length - 1] = curva[linea.length - 2];
  const costuras = [];
  let ultima = -1;
  for (let i = 1; i < linea.length; i++) {
    const cambio = curva[i] !== curva[i - 1];
    if (cambio || (curva[i] && acum[i] - ultima >= 0.10)) {
      const q = puntoEn(linea, acum, acum[i]);
      costuras.push({ p: P(q.x, q.y, Z_COSTURA), rumbo: q.rumbo });
      ultima = acum[i];
    }
  }
  if (costuras.length) {
    const geoC = new THREE.BoxGeometry(1.2 * MM, 0.25 * MM, anchoLinea + 0.6 * MM);
    g.add(instanciasGiradas(geoC, mat(0x2a2b2e, { roughness: 0.3 }), costuras, 'costuras_cinta'));
  }

  // ---- Franjas de meta y de giro: tiras de la misma cinta, de lado a lado (sin tapar el borde).
  const franja = (f, nombre) => {
    const fg = new THREE.Group();
    fg.name = nombre;
    fg.position.copy(P(f.x, f.y, 0));
    fg.rotation.y = f.rumbo;
    const n = Math.max(1, Math.ceil((f.ancho - 1 * MM) / anchoLinea));
    const paso = n > 1 ? (f.ancho - anchoLinea) / (n - 1) : 0;
    for (let k = 0; k < n; k++) {
      const w = n > 1 ? anchoLinea : f.ancho;
      const x = n > 1 ? -f.ancho / 2 + anchoLinea / 2 + k * paso : 0;
      const t = caja(w, ancho - 2 * borde - 2 * MM, 0.15 * MM, mat(0x0c0c0d, { roughness: 0.38 }), P(x, 0, Z_FRANJA + k * 0.00008));
      t.castShadow = false; t.receiveShadow = true;
      fg.add(t);
    }
    return fg;
  };
  if (franjaMeta) g.add(franja(franjaMeta, 'franja_meta'));
  if (franjaGiro) g.add(franja(franjaGiro, 'franja_giro'));

  // ---- Rotulos impresos en el margen izquierdo (entre 40 y 70 mm del centro): fuera del
  // alcance de los 5 infrarrojos (+-30 mm) para no confundirlos. Se leen desde afuera.
  const rot = new THREE.Group();
  rot.name = 'rotulos';
  const ponerRotulo = (texto, s, color) => {
    const q = puntoEn(linea, acum, s);
    const r = rotulo(texto, 70 * MM, 20 * MM, color);
    const h = new THREE.Group();
    h.position.copy(P(q.x, q.y, Z_BORDE + 0.0001));
    h.rotation.y = q.rumbo + Math.PI;               // de espaldas al avance: se lee desde el lado izquierdo
    r.position.copy(P(0, -(W - borde - 15 * MM), 0)); // (en el marco girado, -y local = izquierda de la pista)
    h.add(r);
    rot.add(h);
  };
  const largoLinea = acum[acum.length - 1];
  if (franjaGiro) ponerRotulo('GIRO', Math.max(0, sDe(linea, acum, franjaGiro) + 0.07), '#3b4048');
  ponerRotulo('SALIDA', 0.42, '#3b4048');
  if (franjaMeta) ponerRotulo('META', Math.max(0, largoLinea - 0.12), '#b23a2e');
  obstaculos.forEach((o, i) => ponerRotulo(`MURO ${i + 1}`, Math.max(0, (o.s ?? sDe(linea, acum, o)) - 0.14), '#3b4048'));
  g.add(rot);

  // ---- Muros: atraviesan la linea (largo a lo ancho de la pista), apoyados en la lamina.
  obstaculos.forEach((o, i) => {
    const muro = crearMuroLadrillo({ largo: o.largo, alto: o.alto, grueso, nombre: `muro_${i + 1}`, semilla: i * 3 + 1 });
    muro.position.copy(P(o.x, o.y, Z_LAMINA));
    muro.rotation.y = o.rumbo;
    g.add(muro);
    g.add(ancla(`ancla_muro_${i + 1}`, P(o.x, o.y, Z_LAMINA + o.alto)));
  });

  // ---- Bandera de meta, afuera de la lamina a la izquierda del final de la linea.
  if (meta) {
    const lado = [-Math.sin(meta.rumbo), Math.cos(meta.rumbo)];
    // Base de 60 mm con 15 mm de aire hasta el canto de la lamina (no se monta en ella).
    const bx = meta.x + lado[0] * (W + 0.045), by = meta.y + lado[1] * (W + 0.045);
    const b = crearBanderaMeta();
    b.position.copy(P(bx, by, 0));
    b.rotation.y = meta.rumbo + Math.PI;            // el pano ondea hacia atras (de donde viene el carro)
    g.add(b);
    g.add(ancla('ancla_mastil_meta', P(bx, by, 0)));
  }
  return g;
}

// Distancia recorrida del punto de la linea mas cercano a {x, y}.
function sDe(linea, acum, q) {
  let mejor = 0, dmin = Infinity;
  for (let i = 0; i < linea.length; i++) {
    const d = (linea[i][0] - q.x) ** 2 + (linea[i][1] - q.y) ** 2;
    if (d < dmin) { dmin = d; mejor = i; }
  }
  return acum[mejor];
}
