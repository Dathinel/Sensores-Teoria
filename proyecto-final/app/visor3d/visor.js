// Visor 3D de la planta de monedas (Three.js).
//
// No simula nada por su cuenta: dibuja la geometria que le da el supervisor
// (GET /api/geometria, construida por sim/geometria.py con las MISMAS
// posiciones que usa PyBullet) y anima lo que la simulacion va reportando
// (GET /api/estado, cinco veces por segundo). Si algo se ve raro aqui, el
// problema esta en la simulacion o en la geometria, no en una copia aparte.
//
// Tambien es el boceto de como se construye de verdad: cada pieza que se
// mueve lo hace dentro de sus limites y con el mecanismo que la mueve en el
// montaje (manivelas, leva, compuertas con bisagra), y nada queda colgando en
// el aire: la estructura de perfil 2020 sostiene cintas, almacen, tubo de
// tapas, prensa y panel de luz. Las duraciones salen de config (tiempos_ms).
//
// Convencion de ejes: la simulacion usa z hacia arriba (x, y, z) y Three.js
// usa y hacia arriba. `V()` hace la conversion: (x, y, z) -> (x, z, -y).

import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';

// Abierto como ARCHIVO (visor-portable.html, lo que abre visor.bat): no hay servidor en la
// misma direccion, asi que se le pregunta al de la simulacion en este PC. El puerto es el de
// config/parametros.yaml (supervisor.puerto_http); app/portable.py lo deja escrito aqui.
const EN_ARCHIVO = location.protocol === 'file:';
const URL_VIVO = window.__URL_VIVO || 'http://127.0.0.1:8765/';
const BASE = EN_ARCHIVO ? URL_VIVO : './';

const V = (p) => new THREE.Vector3(p[0], p[2], -p[1]);
const Vxyz = (x, y, z) => new THREE.Vector3(x, z, -y);

const COLOR = {
  ambar: 0xf2b134, verde: 0x3fb68b, rojo: 0xe5534b, azul: 0x539bf5, morado: 0xb083f0,
  cian: 0x2a9fd6, bancada: 0x2b3a52, cinta: 0x0b0b0c, separador: 0xbfc3c8, naranja: 0xe8741c,
  oro: 0xd4a53a, plata: 0xc9ccd1, acero: 0x6f757e, piel: 0xe0ac8a, pista: 0xd8d3c6,
  aluminio: 0xa9b1bb, impreso: 0x39424f, servo: 0x2458b3, tapa: 0xf28c28,
};
const NOMBRES_E_MONEDAS = ['E1 Presencia', 'E2 Material', 'E3 Visión', 'E4 Descarga'];
const NOMBRES_E_VASOS = ['Verificación', 'Llenado', 'Tapa', 'Prensa', 'Descarga'];
const BIMETALICAS = new Set(['500_antigua', '500_nueva', '1000_nueva']);
const SENSORES_ALARMA = new Set(['cortina']);
const DENOMINACIONES = [50, 100, 200, 500, 1000];

// Modo demo: reproduce una corrida grabada (app/grabar_demo.py) sin
// supervisor. Se activa con ?demo o solo, si no hay servidor detras (por
// ejemplo cuando el visor esta publicado fuera del PC).
let MODO_DEMO = new URLSearchParams(location.search).has('demo') || EN_ARCHIVO;
let cuadrosDemo = [];
let cuadroDemo = 0;

let G = null;          // geometria
let PASOS = [];        // docs/paso-a-paso.yaml
let estado = null;     // ultimo /api/estado
let ultimoTick = -1;
let pestana = 'vivo';
let seleccion = { tipo: null, valor: null };   // {tipo:'paso'|'sensor', valor}
const resaltados = new Set();                   // ids de sensores resaltados

// ---------------------------------------------------------------------------
// escena basica
// ---------------------------------------------------------------------------

const contenedor = document.getElementById('lienzo');
const renderer = new THREE.WebGLRenderer({ antialias: true });
// Rendimiento (usuario, 2026-09-26: el visor iba lento): 1,5x como maximo.
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
contenedor.appendChild(renderer.domElement);

const escena = new THREE.Scene();
escena.background = new THREE.Color(0x0e1116);
escena.fog = new THREE.Fog(0x0e1116, 5, 11);

const camara = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.005, 30);
camara.position.set(0.9, 0.9, 1.3);
const controles = new OrbitControls(camara, renderer.domElement);
controles.enableDamping = true;
controles.dampingFactor = 0.08;
controles.maxPolarAngle = Math.PI * 0.495;   // no se mete debajo del piso
controles.minDistance = 0.08;
controles.maxDistance = 6;
controles.target.set(0.6, 0.05, 0.4);

escena.add(new THREE.HemisphereLight(0xdfe8ff, 0x1a1f27, 1.0));
const sol = new THREE.DirectionalLight(0xffffff, 2.1);
sol.position.set(1.2, 2.6, 1.6);
sol.castShadow = true;
sol.shadow.mapSize.set(2048, 2048);
sol.shadow.bias = -0.0004;
sol.shadow.normalBias = 0.002;
Object.assign(sol.shadow.camera, { left: -1.4, right: 1.4, top: 1.4, bottom: -1.4, near: 0.5, far: 7 });
escena.add(sol, sol.target);
sol.target.position.set(0.3, 0, 0.3);
const relleno = new THREE.DirectionalLight(0xb9c7ff, 0.5);
relleno.position.set(-1.5, 1.2, -1.0);
escena.add(relleno);

const piso = new THREE.Mesh(new THREE.PlaneGeometry(14, 14), new THREE.MeshStandardMaterial({ color: 0x161b22, roughness: 1 }));
piso.rotation.x = -Math.PI / 2;
piso.receiveShadow = true;
escena.add(piso);
const grilla = new THREE.GridHelper(14, 140, 0x2a313c, 0x1d232c);
grilla.position.y = 0.0005;
escena.add(grilla);

window.addEventListener('resize', () => {
  camara.aspect = window.innerWidth / window.innerHeight;
  camara.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// ---------------------------------------------------------------------------
// utilidades de construccion
// ---------------------------------------------------------------------------

function mat(color, extra = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0.1, ...extra });
}
const MAT_ALU = mat(COLOR.aluminio, { metalness: 0.75, roughness: 0.38 });

function caja(sx, sy, sz, color, pos, extra) {
  // sx, sy, sz en ejes de la SIMULACION (largo x, ancho y, alto z)
  const m = new THREE.Mesh(new THREE.BoxGeometry(sx, sz, sy), color && color.isMaterial ? color : mat(color, extra));
  if (pos) m.position.copy(pos);
  m.castShadow = true;
  return m;
}

function cilindro(radio, alto, color, pos, extra, segmentos = 32) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(radio, radio, alto, segmentos),
    color && color.isMaterial ? color : mat(color, extra));
  if (pos) m.position.copy(pos);
  m.castShadow = true;
  return m;
}

// Barra redonda entre dos puntos (rieles, varillas, rayos de sensores).
function barra(a, b, radio, color, extra) {
  const dir = new THREE.Vector3().subVectors(b, a);
  const m = new THREE.Mesh(new THREE.CylinderGeometry(radio, radio, dir.length(), 12),
    color && color.isMaterial ? color : mat(color, extra));
  m.position.copy(a).addScaledVector(dir, 0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
  m.castShadow = true;
  return m;
}

// Perfil de aluminio 2020 entre dos puntos alineados con un eje.
function perfil(a, b, lado = 0.02) {
  const d = new THREE.Vector3().subVectors(b, a);
  const g = new THREE.BoxGeometry(Math.abs(d.x) || lado, Math.abs(d.y) || lado, Math.abs(d.z) || lado);
  const m = new THREE.Mesh(g, MAT_ALU);
  m.position.copy(a).addScaledVector(d, 0.5);
  m.castShadow = true;
  return m;
}

// Canal en U entre dos puntos (canaletas de rechazo, canal de E7): piso y
// dos paredes, orientado a lo largo del segmento.
function canalU(a, b, ancho, alto, color, extra = {}) {
  const g = new THREE.Group();
  const largo = a.distanceTo(b);
  const m = mat(color, { side: THREE.DoubleSide, ...extra });
  const piso = new THREE.Mesh(new THREE.BoxGeometry(ancho, 0.002, largo), m);
  g.add(piso);
  for (const lado of [-1, 1]) {
    const pared = new THREE.Mesh(new THREE.BoxGeometry(0.002, alto, largo), m);
    pared.position.set(lado * ancho / 2, alto / 2, 0);
    g.add(pared);
  }
  g.position.copy(a).lerp(b, 0.5);
  g.lookAt(b);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

// Embudo (tambien oblicuo): boca circular arriba, salida circular abajo,
// cada una con su propio centro.
function embudo(centroArriba, radioArriba, centroAbajo, radioAbajo, color, extra = {}) {
  const seg = 40;
  const pos = [];
  const idx = [];
  for (let i = 0; i <= seg; i++) {
    const a = (i / seg) * Math.PI * 2;
    const c = Math.cos(a), s = Math.sin(a);
    pos.push(centroArriba.x + radioArriba * c, centroArriba.y, centroArriba.z + radioArriba * s);
    pos.push(centroAbajo.x + radioAbajo * c, centroAbajo.y, centroAbajo.z + radioAbajo * s);
    if (i < seg) { const k = 2 * i; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, mat(color, { side: THREE.DoubleSide, ...extra }));
  m.castShadow = true;
  return m;
}

// Etiquetas: se muestran solo cuando la camara esta lo bastante cerca para
// leerlas (con todo el sistema en pantalla serian manchas encimadas).
const ETIQUETAS = [];
function etiqueta(texto, { alto = 0.012, color = '#e6e8eb', fondo = 'rgba(14,17,22,0.78)', borde = null, alcance = null } = {}) {
  const lienzo = document.createElement('canvas');
  const ctx = lienzo.getContext('2d');
  const fuente = 44;
  ctx.font = `600 ${fuente}px "Space Grotesk", sans-serif`;
  const ancho = Math.ceil(ctx.measureText(texto).width) + 36;
  lienzo.width = ancho; lienzo.height = fuente + 26;
  ctx.font = `600 ${fuente}px "Space Grotesk", sans-serif`;
  ctx.fillStyle = fondo;
  ctx.beginPath(); ctx.roundRect(0, 0, lienzo.width, lienzo.height, 16); ctx.fill();
  if (borde) { ctx.strokeStyle = borde; ctx.lineWidth = 5; ctx.stroke(); }
  ctx.fillStyle = color; ctx.textBaseline = 'middle';
  ctx.fillText(texto, 18, lienzo.height / 2 + 2);
  const tex = new THREE.CanvasTexture(lienzo);
  tex.colorSpace = THREE.SRGBColorSpace;
  // Tamaño FIJO en pantalla (no se agranda al acercarse ni se achica al
  // alejarse): se lee igual desde lejos y de cerca no tapa todo. Solo se
  // desvanece cuando esta muy lejos (`alcance`).
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true, sizeAttenuation: false }));
  const h = THREE.MathUtils.clamp(0.017 + (alto - 0.004) * 0.9, 0.017, 0.03);
  sprite.scale.set(h * lienzo.width / lienzo.height, h, 1);
  sprite.renderOrder = 10;
  sprite.userData.etiqueta = { alcance: (alcance ?? alto * 60) * 1.8 };
  ETIQUETAS.push(sprite);
  return sprite;
}

const _p = new THREE.Vector3();
function actualizarEtiquetas() {
  for (const e of ETIQUETAS) {
    if (!e.parent) continue;
    e.getWorldPosition(_p);
    const a = e.userData.etiqueta.alcance;
    let op = Math.max(0, Math.min(1, (a - _p.distanceTo(camara.position)) / (a * 0.3)));
    if (e.userData.sensorId && resaltados.has(e.userData.sensorId)) op = 1;
    e.material.opacity = op * (e.userData.opacidadBase ?? 1);
    e.visible = op > 0.02;
  }
}

function texturaLadrillo() {
  const c = document.createElement('canvas'); c.width = 128; c.height = 64;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#d8d0c4'; ctx.fillRect(0, 0, 128, 64);
  for (let fila = 0; fila < 4; fila++) {
    for (let col = -1; col < 4; col++) {
      const x = col * 32 + (fila % 2) * 16;
      ctx.fillStyle = ['#a8432f', '#b24c35', '#9c3d2a'][(fila + col + 3) % 3];
      ctx.fillRect(x + 1, fila * 16 + 1, 30, 14);
    }
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

function texturaAjedrez() {
  const c = document.createElement('canvas'); c.width = 64; c.height = 64;
  const ctx = c.getContext('2d');
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) {
    ctx.fillStyle = (i + j) % 2 ? '#111' : '#f4f4f4'; ctx.fillRect(i * 8, j * 8, 8, 8);
  }
  const t = new THREE.CanvasTexture(c); t.magFilter = THREE.NearestFilter; return t;
}

// Cinta del vaso: el mismo marcador 6 veces a lo largo de todo el contorno.
function texturaCintaAruco(numero) {
  const c = document.createElement('canvas'); c.width = 360; c.height = 60;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#f6f6f2'; ctx.fillRect(0, 0, 360, 60);
  const unico = texturaAruco(numero).image;
  for (let k = 0; k < 6; k++) ctx.drawImage(unico, k * 60 + 3, 3, 54, 54);
  const t = new THREE.CanvasTexture(c); t.magFilter = THREE.NearestFilter; t.colorSpace = THREE.SRGBColorSpace; return t;
}

// Marcador ArUco de mentira (patron 4x4 fijo) para los vasos.
function texturaAruco(numero) {
  const c = document.createElement('canvas'); c.width = 60; c.height = 60;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, 60, 60);
  ctx.fillStyle = '#000'; ctx.fillRect(6, 6, 48, 48);
  ctx.fillStyle = '#fff';
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
    if (((numero * 2654435761) >>> (i * 4 + j)) & 1) ctx.fillRect(14 + i * 8, 14 + j * 8, 8, 8);
  }
  const t = new THREE.CanvasTexture(c); t.magFilter = THREE.NearestFilter; return t;
}

// ---------------------------------------------------------------------------
// animaciones con tiempo real (config: tiempos_ms, divididos por la
// velocidad de la linea que se eligio en el dashboard)
// ---------------------------------------------------------------------------

const ANIMS = [];
let VEL = 1;
const suave = (u) => u * u * (3 - 2 * u);
const caida = (u) => u * u;                    // arranca quieto y acelera (gravedad)
const frenado = (u) => 1 - (1 - u) * (1 - u);  // arranca rapido y frena
const seg = (clave, defecto) => (((G && G.tiempos_ms && G.tiempos_ms[clave]) || defecto) / 1000);

function animar(segundos, fn, { retraso = 0, fin = null, dueno = null } = {}) {
  const a = { t0: performance.now() + (retraso / VEL) * 1000, dur: Math.max(1, (segundos / VEL) * 1000), fn, fin, dueno };
  ANIMS.push(a);
  return a;
}
function cancelar(dueno) {
  for (let i = ANIMS.length - 1; i >= 0; i--) if (ANIMS[i].dueno === dueno) ANIMS.splice(i, 1);
}
function correrAnimaciones() {
  const ahora = performance.now();
  for (let i = ANIMS.length - 1; i >= 0; i--) {
    const a = ANIMS[i];
    if (ahora < a.t0) continue;
    const u = Math.min(1, (ahora - a.t0) / a.dur);
    a.fn(u);
    if (u >= 1) { ANIMS.splice(i, 1); if (a.fin) a.fin(); }
  }
}

// Lleva un objeto por un camino suave que pasa por los puntos; `tramos`
// encadena varios caminos con su propio ritmo (empuje, caida, deslizamiento).
function recorrer(obj, puntos, segundos, { ease = suave, retraso = 0, fin = null, giro = null } = {}) {
  const curva = puntos.length > 2 ? new THREE.CatmullRomCurve3(puntos, false, 'centripetal') : new THREE.LineCurve3(puntos[0], puntos[1]);
  const q0 = obj.quaternion.clone();
  return animar(segundos, (u) => {
    obj.position.copy(curva.getPoint(ease(u)));
    if (giro) obj.quaternion.slerpQuaternions(q0, giro, ease(u));
  }, { retraso, fin, dueno: obj });
}
function tramos(obj, lista, fin, retraso = 0) {
  const [primero, ...resto] = lista;
  if (!primero) { if (fin) fin(); return; }
  recorrer(obj, primero.puntos, primero.seg, { ease: primero.ease || suave, giro: primero.giro, retraso,
    fin: () => tramos(obj, resto, fin) });
}

// ---------------------------------------------------------------------------
// planta
// ---------------------------------------------------------------------------

const P = {};   // referencias a piezas que se animan
const CINTAS = {};

// Componentes fisicos (sim/catalogos.py): id -> objetos 3D que
// lo representan, para resaltarlo cuando se elige en la pestana Componentes.
const COMP = {};
let compResaltado = null;
function registrar(id, ...objetos) {
  for (const o of objetos) if (o) { o.userData.parte = true; (COMP[id] ||= []).push(o); }
}

// Caja de un motor paso a paso NEMA17 (42 mm), con el eje hacia +y.
function nema17(pos) {
  const g = new THREE.Group();
  g.add(caja(0.042, 0.034, 0.042, 0x2b2f36, Vxyz(0, 0, 0), { metalness: 0.6 }));
  for (const dy of [-0.019, 0.019]) g.add(caja(0.043, 0.005, 0.043, 0x9aa1ab, Vxyz(0, dy, 0), { metalness: 0.7 }));
  g.add(barra(Vxyz(0, 0.02, 0), Vxyz(0, 0.042, 0), 0.0025, COLOR.plata, { metalness: 0.9 }));
  // Conector JST-PH de 6 pines (4 hilos) en la cara de abajo, atras.
  g.add(caja(0.016, 0.006, 0.005, 0xf2f2f2, Vxyz(0, -0.012, -0.0235)));
  g.position.copy(pos);
  g.userData.conector = Vxyz(0, -0.012, -0.026);
  return g;
}

// Servo: micro (SG90/MG90S, 23 x 12 x 22 mm) o estandar (MG996R, 40 x 20 x
// 38 mm). Cuerpo, orejas de montaje con sus agujeros, torre del eje con el
// disco (horn) arriba, etiqueta y la salida del cable de 3 hilos (cafe =
// GND, rojo = V+, naranja = senal) por el costado de abajo.
function servo(pos, { color = COLOR.servo, grande = false } = {}) {
  const g = new THREE.Group();
  const [sx, sy, sz] = grande ? [0.040, 0.020, 0.038] : [0.023, 0.012, 0.022];
  const cuerpo = grande ? 0x1d1d1d : color;
  const oreja = grande ? 0.007 : 0.0045;
  const zOreja = sz * 0.2;
  g.add(caja(sx, sy, sz, cuerpo, Vxyz(0, 0, 0)));
  g.add(caja(sx + 2 * oreja, sy, 0.0025, cuerpo, Vxyz(0, 0, zOreja)));
  for (const l of [-1, 1]) {
    const hueco = cilindro(grande ? 0.0022 : 0.0012, 0.0027, 0x0a0a0a, Vxyz(l * (sx / 2 + oreja / 2), 0, zOreja), {}, 12);
    g.add(hueco);
  }
  g.add(cilindro(grande ? 0.0065 : 0.004, 0.004, cuerpo, Vxyz(sx * 0.25, 0, sz / 2 + 0.002), {}, 24));
  const horn = cilindro(grande ? 0.012 : 0.007, 0.002, 0xeeeeee, Vxyz(sx * 0.25, 0, sz / 2 + 0.005));
  g.add(horn);
  g.add(caja(sx * 0.6, 0.0004, sz * 0.35, grande ? 0x3a3a3a : 0x9fb6e0, Vxyz(-sx * 0.1, -sy / 2 - 0.0002, -sz * 0.1)));
  // Cable: sale por el costado (-x), abajo, con los 3 hilos pegados.
  const salida = Vxyz(-sx / 2, 0, -sz / 2 + 0.004);
  [0x6b3a1f, 0xc8241c, 0xe8901c].forEach((c, i) => {
    const dy = (i - 1) * 0.0011;
    g.add(barra(salida.clone().add(Vxyz(0, dy, 0)), salida.clone().add(Vxyz(-0.012, dy, 0)), 0.00055, c));
  });
  g.position.copy(pos);
  g.userData = { horn, tam: [sx, sy, sz], oreja, zOreja, cable: salida.clone().add(Vxyz(-0.012, 0, 0)) };
  return g;
}

// Montaje de un servo: una escuadra impresa que lo abraza por debajo (el
// cuerpo APOYA en ella) con dos torres bajo las orejas, atornillado por las
// orejas (4 tornillos), y una barra en "L" hasta el punto de la estructura del
// que se sostiene: primero horizontal por debajo del servo y despues vertical
// (una barra recta subia a veces por dentro del servo; revision de espacio
// 2026-09-26). Ningun servo queda flotando ni "posado" sin fijar.
function soporteServo(grupo, servoObj, puntoEstructura, idComponente, grande = false) {
  servoObj.updateWorldMatrix(true, false);
  const p0 = servoObj.getWorldPosition(new THREE.Vector3());
  const q = servoObj.getWorldQuaternion(new THREE.Quaternion());
  const { tam: [sx, sy, sz], oreja, zOreja } = servoObj.userData;
  const montaje = new THREE.Group();
  montaje.position.copy(p0);
  montaje.quaternion.copy(q);
  const piezas = [];
  const zBase = -sz / 2 - 0.0015;
  piezas.push(caja(sx + 2 * oreja + 0.004, sy + 0.006, 0.003, COLOR.impreso, Vxyz(0, 0, zBase)));
  for (const l of [-1, 1]) {
    const xo = l * (sx / 2 + oreja / 2);
    const alto = zOreja - 0.00125 - (zBase + 0.0015);
    piezas.push(caja(oreja + 0.002, sy + 0.006, alto, COLOR.impreso, Vxyz(xo, 0, zBase + 0.0015 + alto / 2)));
    for (const dy of [-sy / 4, sy / 4]) {
      piezas.push(cilindro(grande ? 0.0022 : 0.0015, 0.0012, 0xb8bec6, Vxyz(xo, dy, zOreja + 0.0019), { metalness: 0.8 }, 10));
    }
  }
  montaje.add(...piezas);
  grupo.add(montaje);
  montaje.updateMatrixWorld(true);
  const bajo = new THREE.Vector3(0, zBase - 0.0015, 0).applyMatrix4(montaje.matrixWorld);
  const codo = new THREE.Vector3(puntoEstructura.x, bajo.y, puntoEstructura.z);
  const tramos = [];
  if (codo.distanceTo(bajo) > 0.002) tramos.push(barra(bajo, codo, 0.0025, MAT_ALU));
  if (codo.distanceTo(puntoEstructura) > 0.002) tramos.push(barra(codo, puntoEstructura, 0.0025, MAT_ALU));
  const pie = cilindro(0.005, 0.004, 0x30363d, puntoEstructura.clone());
  grupo.add(...tramos, pie);
  if (idComponente) registrar(idComponente, montaje);
  registrar('estructura', ...tramos, pie);
  // Camino del cable: sale del servo, baja a la escuadra y sigue la barra
  // (3 mm al lado) hasta el punto de la estructura.
  const salida = servoObj.localToWorld(servoObj.userData.cable.clone());
  const d = new THREE.Vector3(0.0125, 0, 0.004);
  const abajo = new THREE.Vector3(0, -0.005, 0);
  const bajoSalida = salida.clone().setY(bajo.y).add(abajo);
  P.rutasServo[idComponente] = [salida, bajoSalida, codo.clone().add(d).add(abajo), puntoEstructura.clone().add(d)];
}

// Sensor de proximidad cilindrico (capacitivo LJC18A3 / inductivo LJ18A3):
// cuerpo M18 roscado de laton niquelado, tapa de la cara, tuerca de
// fijacion, LED de estado atras y cable. `cara` = centro de la cara activa;
// `mira` = hacia donde mira (en coordenadas de Three).
function sensorCilindrico(cara, mira, { largo, colorCara, tuercaA = 0.0105 }) {
  const g = new THREE.Group();
  const r = 0.009;
  g.add(cilindro(r * 0.96, 0.004, colorCara, new THREE.Vector3(0, -0.002, 0), { roughness: 0.5 }));
  g.add(cilindro(r, largo - 0.012, 0xb8bec6, new THREE.Vector3(0, -0.004 - (largo - 0.012) / 2, 0), { metalness: 0.85, roughness: 0.35 }));
  // Rosca: anillos cada 1,5 mm.
  const matRosca = mat(0xd0d5db, { metalness: 0.9, roughness: 0.3 });
  for (let d = 0.006; d < largo - 0.012; d += 0.0015) {
    const anillo = new THREE.Mesh(new THREE.TorusGeometry(r, 0.00035, 4, 24), matRosca);
    anillo.rotation.x = Math.PI / 2;
    anillo.position.y = -d;
    g.add(anillo);
  }
  // Tuerca de fijacion (M18, 24 mm entre caras) bajo el inserto.
  const tuerca = new THREE.Mesh(new THREE.CylinderGeometry(0.0139, 0.0139, 0.004, 6), mat(0xc9ccd1, { metalness: 0.85, roughness: 0.3 }));
  tuerca.position.y = -tuercaA;
  g.add(tuerca);
  // Cola de plastico con el LED de estado y el prensacable.
  g.add(cilindro(r * 0.9, 0.008, 0x2b2f36, new THREE.Vector3(0, -largo + 0.004, 0)));
  const led = new THREE.Mesh(new THREE.SphereGeometry(0.0022, 12, 12), new THREE.MeshBasicMaterial({ color: 0x30363d }));
  led.position.set(r * 0.9, -largo + 0.005, 0);
  g.add(led);
  g.add(cilindro(0.0028, 0.012, 0x1c1c1c, new THREE.Vector3(0, -largo - 0.006, 0)));
  g.position.copy(cara);
  g.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), mira.clone().normalize());
  g.userData.led = led;
  g.userData.salidaCable = new THREE.Vector3(0, -largo - 0.012, 0);
  return g;
}

// Campo de un sensor: el cono NOMINAL (hoja de datos) y, mas tenue, el cono
// de ERROR PROBABLE (el nominal mas la desalineacion de montaje, ~5 grados):
// lo que el sensor podria llegar a ver si queda torcido. `origen` y `dir` en
// coordenadas de Three; angulos en grados (semiangulo).
function conosSensor(origen, dir, alcance, semiNominal, semiError, color = COLOR.cian) {
  const d = dir.clone().normalize();
  const hacer = (semi, opacidad) => {
    const cono = new THREE.Mesh(new THREE.ConeGeometry(Math.tan(THREE.MathUtils.degToRad(semi)) * alcance, alcance, 24, 1, true),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: opacidad, side: THREE.DoubleSide, depthWrite: false }));
    cono.position.copy(origen).addScaledVector(d, alcance / 2);
    cono.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().negate());   // punta en el sensor
    cono.castShadow = false;
    cono.userData.campo = true;
    return cono;
  };
  return [hacer(semiNominal, 0.13), hacer(semiError, 0.05)];
}

// Cinta indexada: bancada, banda, rodillos y separadores que SI avanzan
// una casilla en cada paso (y reaparecen por la cola, como una banda real).
function construirBanda(grupo, nombre, { x0, x1, y, zs, ancho, paso, altoSep, ventanas = [] }) {
  const zb = zs - G.altura_superficie;
  const largo = x1 - x0, xc = (x0 + x1) / 2;
  // Bancada (la cama sobre la que desliza la banda). Donde va un sensor
  // DEBAJO de la cinta, la bancada tiene una ventana de 36 mm tapada por un
  // inserto IMPRESO de 6 mm, roscado M18: el sensor se enrosca ahi con la
  // cara a ras (un inductivo no enrasable no puede tener metal alrededor).
  const cortes = [x0, ...ventanas.flatMap((v) => [v - 0.018, v + 0.018]), x1];
  for (let i = 0; i < cortes.length; i += 2) {
    const a = cortes[i], b = cortes[i + 1];
    if (b - a < 0.001) continue;
    const tramo = caja(b - a, ancho + 0.006, 0.02, COLOR.bancada, Vxyz((a + b) / 2, y, zb + 0.01));
    tramo.receiveShadow = true;
    grupo.add(tramo);
  }
  for (const v of ventanas) {
    const inserto = caja(0.036, ancho + 0.006, 0.006, 0x56606e, Vxyz(v, y, zs - 0.005));
    grupo.add(inserto);
    registrar('estructura', inserto);
  }
  const banda = caja(largo, ancho, 0.002, COLOR.cinta, Vxyz(xc, y, zs - 0.001), { roughness: 0.95 });
  banda.receiveShadow = true;
  grupo.add(banda);
  const rodillos = [];
  for (const x of [x0, x1]) {
    const r = cilindro(0.011, ancho + 0.004, 0x5d646e, Vxyz(x, y, zs - 0.011), { metalness: 0.7 });
    r.rotation.x = Math.PI / 2;
    const banda = cilindro(0.0112, ancho, COLOR.cinta, Vxyz(x, y, zs - 0.011), { roughness: 0.95 });
    banda.rotation.x = Math.PI / 2;
    grupo.add(r, banda);
    rodillos.push(r);
  }
  const seps = [], base = [];
  for (let k = -1; x0 + k * paso <= x1 + 1e-6; k++) {
    const x = x0 + k * paso;
    const s = caja(0.003, ancho, altoSep, COLOR.separador, Vxyz(x, y, zs + altoSep / 2));
    s.visible = k >= 0;
    grupo.add(s);
    seps.push(s); base.push(x);
  }
  CINTAS[nombre] = { seps, base, paso, xmin: x0, xmax: x1, rodillos, moviendo: false };
}

function moverCinta(nombre, segundos) {
  const c = CINTAS[nombre];
  if (!c || c.moviendo) return;
  c.moviendo = true;
  const poner = (off) => c.seps.forEach((m, i) => {
    const x = c.base[i] + off;
    m.position.x = x;
    m.visible = x >= c.xmin - 1e-4 && x <= c.xmax + 1e-4;
  });
  animar(segundos, (u) => {
    const off = suave(u) * c.paso;
    poner(off);
    for (const r of c.rodillos) r.rotation.y = -off / 0.011;
  }, { fin: () => { c.moviendo = false; poner(0); } });
}

// Mesa de 4 patas de perfil 2020 bajo una cinta, con travesanos.
function mesa(grupo, xs, ys, alto, id) {
  const piezas = [];
  for (const x of xs) for (const y of ys) piezas.push(perfil(Vxyz(x, y, 0), Vxyz(x, y, alto)));
  for (const y of ys) piezas.push(perfil(Vxyz(xs[0], y, 0.05), Vxyz(xs[1], y, 0.05)));
  for (const x of xs) piezas.push(perfil(Vxyz(x, ys[0], 0.05), Vxyz(x, ys[1], 0.05)));
  for (const x of xs) for (const y of ys) piezas.push(caja(0.03, 0.03, 0.004, 0x30363d, Vxyz(x, y, 0.002)));
  grupo.add(...piezas);
  registrar(id, ...piezas);
}

function cubeta(pos, colorPiso, colorPared) {
  const g = new THREE.Group();
  g.add(caja(0.07, 0.07, 0.003, colorPiso, Vxyz(0, 0, 0.0015)));
  for (const [dx, dy, sx, sy] of [[0.035, 0, 0.003, 0.07], [-0.035, 0, 0.003, 0.07], [0, 0.035, 0.07, 0.003], [0, -0.035, 0.07, 0.003]]) {
    g.add(caja(sx, sy, 0.03, colorPared, Vxyz(dx, dy, 0.015), { transparent: true, opacity: 0.8 }));
  }
  g.position.copy(pos);
  return g;
}

function construirCintaMonedas() {
  const est = G.cinta_monedas.estaciones.map((e) => e.posicion);
  const n = est.length;
  const paso = G.cinta_monedas.separacion;
  const zs = est[0][2];
  const zb = zs - G.altura_superficie;
  const y = est[0][1];
  const ancho = G.ancho_cinta_monedas;
  // La banda arranca UNA casilla antes de E1: con el rodillo de cola a 2 cm
  // de E1 no cabia el capacitivo debajo (revision 2026-09-26).
  const x0 = est[0][0] - 1.5 * paso, x1 = est[n - 1][0] + paso / 2;
  const grupo = new THREE.Group();

  construirBanda(grupo, 'monedas', { x0, x1, y, zs, ancho, paso, altoSep: 0.004,
    ventanas: [est[0][0], est[1][0]] });
  // Rieles laterales (perfil 2020) a los dos lados de la bancada: la
  // sostienen y llevan los cojinetes de los rodillos. Las patas van debajo
  // de los rieles, POR FUERA de la banda, para que el retorno pase libre.
  const yRiel = ancho / 2 + 0.003 + 0.01;
  P.rielMonedas = { y: y - yRiel, zArriba: zs - 0.002 };
  const rieles = [-1, 1].map((l) => perfil(Vxyz(x0 - 0.035, y + l * yRiel, zs - 0.012), Vxyz(x1, y + l * yRiel, zs - 0.012)));
  grupo.add(...rieles);
  registrar('estructura', ...rieles);
  // Patas: dos en la cola (fuera de la viga del portico) y una en el
  // extremo de descarga del lado +y; del lado -y ese extremo APOYA sobre la
  // viga del portico con un taco de 2 cm (una pata ahi atravesaba la viga).
  // Las del extremo de descarga van 6 cm antes del final: mas cerca pasaban
  // por el carrusel del almacen (revision de espacio 2026-09-26).
  const zPata = zs - 0.022, xPD = x1 - 0.06;
  const patas = [[x0 - 0.035, y - yRiel], [x0 - 0.035, y + yRiel], [xPD, y + yRiel]]
    .map(([px, py]) => perfil(Vxyz(px, py, 0), Vxyz(px, py, zPata)));
  const piesMesa = [[x0 - 0.035, y - yRiel], [x0 - 0.035, y + yRiel], [xPD, y + yRiel]]
    .map(([px, py]) => caja(0.03, 0.03, 0.004, 0x30363d, Vxyz(px, py, 0.002)));
  const travesanos = [perfil(Vxyz(x0 - 0.035, y - yRiel, 0.05), Vxyz(x0 - 0.035, y + yRiel, 0.05)),
    perfil(Vxyz(x0 - 0.035, y + yRiel, 0.05), Vxyz(xPD, y + yRiel, 0.05))];
  grupo.add(...patas, ...piesMesa, ...travesanos);
  registrar('estructura', ...patas, ...piesMesa, ...travesanos);
  P.apoyoMesaMonedas = { x: xPD, y: y - yRiel, zArriba: zs - 0.022 };   // el taco se pone con el portico
  // Retorno de la banda: sale por debajo del rodillo de cabeza, pasa sobre
  // un rodillo tensor y BAJA por dos rodillos hasta 11 cm bajo la cinta en
  // la zona de E1-E2, para dejar lugar a los dos sensores (6-7 cm de largo)
  // y a la curva de sus cables; despues sube por detras del rodillo de cola.
  const zr = zs - 0.0232;
  const rodIdler = (x, z) => {
    const r = cilindro(0.008, ancho + 0.004, 0x5d646e, Vxyz(x, y, z), { metalness: 0.7 });
    r.rotation.x = Math.PI / 2;
    // Eje sostenido por dos placas que cuelgan de los rieles.
    const placas = [-1, 1].map((l) => caja(0.014, 0.003, zs - 0.022 - z + 0.008, COLOR.impreso,
      Vxyz(x, y + l * (ancho / 2 + 0.0035), (zs - 0.022 + z - 0.008) / 2)));
    grupo.add(r, ...placas);
    registrar('cinta_monedas', r);
    registrar('estructura', ...placas);
  };
  const xA = x0 - 0.003, xB = est[1][0] + 0.04, xC = est[1][0] + 0.08, zAB = zs - 0.10;
  rodIdler(xA, zAB); rodIdler(xB, zAB); rodIdler(xC, zs - 0.0332);
  const retorno = [[x1, zr], [xC, zr - 0.001], [xB + 0.0085, zAB - 0.003], [xB, zAB - 0.009],
    [xA, zAB - 0.009], [xA - 0.009, zAB], [x0 - 0.0112, zs - 0.011]];
  for (let i = 0; i + 1 < retorno.length; i++) {
    const [ax, az] = retorno[i], [bx, bz] = retorno[i + 1];
    const tira = new THREE.Mesh(new THREE.BoxGeometry(Math.hypot(bx - ax, bz - az), 0.002, ancho), mat(COLOR.cinta, { roughness: 0.95 }));
    tira.position.copy(Vxyz((ax + bx) / 2, y, (az + bz) / 2));
    tira.rotation.z = Math.atan2(bz - az, bx - ax);
    grupo.add(tira);
  }
  // Guias laterales: la moneda no se sale de su casilla (no hay expulsores
  // que tengan que sacarla de lado: filtro total).
  for (const lado of [-1, 1]) {
    const guia = caja(x1 - x0, 0.002, 0.006, COLOR.impreso, Vxyz((x0 + x1) / 2, y + lado * (ancho / 2 + 0.001), zs + 0.003));
    grupo.add(guia);
  }
  est.forEach((p, i) => {
    const e = etiqueta(NOMBRES_E_MONEDAS[i], { alto: 0.0085 });
    e.position.copy(Vxyz(p[0], y + 0.05, zs + 0.012));
    grupo.add(e);
  });

  // Descarga (E4), filtro total: la pieza cae por el extremo de la cinta a
  // un embudo; abajo, la compuerta de desvio (a prueba de fallas: en reposo
  // apunta al rechazo) la manda por uno de dos canales cortos y empinados:
  // a la boca del tubo del carrusel que esta en la carga, o a la UNICA
  // bandeja de rechazo.
  const al = G.almacen;
  const fx = x1 + 0.015;
  const zEmbArriba = zs - 0.006, zEmbAbajo = zs - 0.032;
  const emb = embudo(Vxyz(fx, y, zEmbArriba), 0.02, Vxyz(fx, y, zEmbAbajo), 0.01, 0x8d96a3,
    { metalness: 0.5, transparent: true, opacity: 0.55, depthWrite: false });
  const desvio = new THREE.Group();
  desvio.position.copy(Vxyz(fx, y, zEmbAbajo - 0.002));
  desvio.add(caja(0.018, 0.002, 0.016, 0xd9261a, Vxyz(0, 0, -0.008)));
  desvio.rotation.x = 0.5;   // reposo: hacia el rechazo
  // 35 mm detras del embudo: con su escuadra, a 22 mm tocaba los dos canales.
  const servoDesvio = servo(Vxyz(fx + 0.035, y, zEmbAbajo));
  const carga = al.punto_carga;
  const bocaCarga = Vxyz(carga[0], carga[1], al.tubo_z_arriba + 0.012);
  const inicioA = Vxyz(fx, y - 0.006, zEmbAbajo - 0.006);
  const canalA = canalU(inicioA, bocaCarga, 0.03, 0.01, COLOR.plata, { metalness: 0.5 });
  const embCarga = embudo(bocaCarga.clone().add(new THREE.Vector3(0, 0.004, 0)), 0.018,
    Vxyz(carga[0], carga[1], al.tubo_z_arriba + 0.003), 0.013, 0x8d96a3,
    { metalness: 0.5, transparent: true, opacity: 0.6, depthWrite: false });
  const rf = al.rechazo_final;
  const inicioB = Vxyz(fx, y + 0.006, zEmbAbajo - 0.006);
  const finB = Vxyz(rf[0], rf[1] - 0.03, 0.05);
  const canalB = canalU(inicioB, finB, 0.03, 0.012, 0x8a3a3a, { transparent: true, opacity: 0.85 });
  const brazoEmb = barra(Vxyz(fx - 0.018, y - 0.012, zEmbAbajo), Vxyz(x1 - 0.012, y - ancho / 2 - 0.013, zs - 0.0235), 0.002, MAT_ALU);
  grupo.add(emb, desvio, servoDesvio, canalA, embCarga, canalB, brazoEmb);
  // Poste propio hasta el piso, justo debajo: a los lados bajan los dos
  // canales (al carrusel y al rechazo) y adelante esta el rodillo.
  soporteServo(grupo, servoDesvio, Vxyz(fx + 0.035, y, 0.002), 'servo_desvio_e7');
  const etDesvio = etiqueta('Compuerta de rechazo (desvío)', { alto: 0.009, color: '#e5534b' });
  etDesvio.position.copy(Vxyz(fx + 0.03, y, zEmbAbajo + 0.03));
  grupo.add(etDesvio);
  registrar('canal_e7', emb, canalA, embCarga, brazoEmb);
  registrar('servo_desvio_e7', desvio, servoDesvio);
  registrar('canaletas_rechazo', canalB);
  const cubFinal = cubeta(Vxyz(rf[0], rf[1], 0), 0x4a2a2a, 0x6b3a3a);
  cubFinal.scale.set(1.3, 1, 1.3);
  grupo.add(cubFinal);
  registrar('canaletas_rechazo', cubFinal);
  const etRf = etiqueta('Bandeja de rechazo', { alto: 0.01, color: '#e5534b' });
  etRf.position.copy(Vxyz(rf[0], rf[1], 0.06));
  grupo.add(etRf);
  P.cubetas = { rechazo: Vxyz(rf[0], rf[1], rf[2]) };
  P.desvio = desvio;
  P.e7 = {
    cabeza: Vxyz(x1 + 0.006, y, zs + 0.004),
    embudo: Vxyz(fx, y, zEmbArriba - 0.01),
    aSelector: [inicioA, bocaCarga],
    aRechazo: [inicioB, finB],
  };

  // Mano que alguien apoya un instante en la casilla de carga (punto 1).
  const manoCarga = new THREE.Group();
  manoCarga.add(caja(0.03, 0.036, 0.016, COLOR.piel, Vxyz(0, 0, 0.008)));
  manoCarga.add(barra(Vxyz(0, 0.01, 0.012), Vxyz(0, 0.16, 0.09), 0.017, COLOR.piel));
  manoCarga.position.copy(Vxyz(est[0][0], y, zs));
  manoCarga.visible = false;
  manoCarga.userData.parte = true;
  grupo.add(manoCarga);
  P.manoCarga = { grupo: manoCarga, hasta: 0 };

  // Motor paso a paso en el rodillo de la cola (entrada), del lado +y, por
  // fuera del riel (el eje del rodillo atraviesa el riel por su cojinete).
  const motor = nema17(Vxyz(x0, y + yRiel + 0.01 + 0.019, zs - 0.011));
  P.nemaMonedas = motor;
  motor.rotation.y = Math.PI;   // eje hacia -y, al rodillo
  grupo.add(motor);
  registrar('motor_cinta_monedas', motor);
  registrar('cinta_monedas', ...grupo.children.filter((o) => !o.userData.parte && !o.isSprite));

  escena.add(grupo);
}

function construirCintaVasos() {
  const est = G.cinta_vasos.estaciones.map((e) => e.posicion);
  const paso = G.cinta_vasos.separacion;
  const zs = est[0][2];
  const zb = zs - G.altura_superficie;
  const y = est[0][1];
  const ancho = G.ancho_cinta_vasos;
  const x0 = est[0][0] - paso / 2, x1 = est[4][0] + paso / 2;
  const hV = G.vaso.altura, rBoca = G.vaso.diametro / 2 + G.vaso.reborde;
  const grupo = new THREE.Group();

  construirBanda(grupo, 'vasos', { x0, x1, y, zs, ancho, paso, altoSep: 0.015 });
  mesa(grupo, [x0 + 0.02, x1 - 0.02], [y - 0.03, y + 0.03], zb, 'estructura');
  est.forEach((p, i) => {
    const e = etiqueta(NOMBRES_E_VASOS[i], { alto: 0.011 });
    e.position.copy(Vxyz(p[0], y - 0.075, zs + 0.004));
    grupo.add(e);
  });

  // Portico trasero de perfil 2020 (del lado +y, entre la cinta de vasos y
  // la mesa de monedas): de el cuelgan el almacen, el tubo de tapas y la
  // prensa. Ninguna pieza queda en el aire.
  // Viga a 40 cm: por debajo pasa el canal corto de la descarga al carrusel.
  const yP = y + 0.055, zViga = 0.40;
  const xa = x0 - 0.035, xb = est[3][0] + 0.035;
  const portico = [perfil(Vxyz(xa, yP, 0), Vxyz(xa, yP, zViga + 0.01)), perfil(Vxyz(xb, yP, 0), Vxyz(xb, yP, zViga + 0.01)),
    perfil(Vxyz(xa, yP, zViga), Vxyz(xb, yP, zViga)), caja(0.03, 0.03, 0.004, 0x30363d, Vxyz(xa, yP, 0.002)),
    caja(0.03, 0.03, 0.004, 0x30363d, Vxyz(xb, yP, 0.002))];
  grupo.add(...portico);
  registrar('estructura', ...portico);
  P.portico = { y: yP, z: zViga };
  // Taco impreso: el extremo -y de la mesa de monedas apoya en la viga.
  const am = P.apoyoMesaMonedas;
  const taco = caja(0.02, 0.02, am.zArriba - (zViga + 0.01), COLOR.impreso, Vxyz(am.x, am.y, (am.zArriba + zViga + 0.01) / 2));
  grupo.add(taco);
  registrar('estructura', taco);

  // Panel de luz detras de verificacion, llenado, tapa y prensa: la camara
  // de vasos ve cada casilla a contraluz (silueta nitida, sin depender de la
  // luz del salon ni del color del vaso; las monedas se ven en el fondo del
  // vaso translucido). Tambien cierra por detras la zona de tapa y prensa:
  // una mano solo entra por el lado de la cortina. Queda por debajo de los
  // servos de las compuertas del almacen.
  const yPanel = y + ancho / 2 + 0.0045;
  const xp0 = x0 - 0.005, xp1 = est[3][0] + 0.045;
  const zp0 = zs + 0.003, zp1 = zs + hV + 0.025;
  const panel = caja(xp1 - xp0, 0.004, zp1 - zp0, 0xf4f7fb, Vxyz((xp0 + xp1) / 2, yPanel, (zp0 + zp1) / 2),
    { emissive: 0xeaf2ff, emissiveIntensity: 0.55, roughness: 0.9 });
  const marco = [perfil(Vxyz(xp0, yPanel + 0.006, zp1), Vxyz(xp1, yPanel + 0.006, zp1), 0.01),
    perfil(Vxyz(xp0, yPanel + 0.006, zp0), Vxyz(xp1, yPanel + 0.006, zp0), 0.01),
    perfil(Vxyz(xa, yPanel + 0.006, zp1), Vxyz(xp0, yPanel + 0.006, zp1), 0.01)];
  grupo.add(panel, ...marco);
  registrar('panel_luz', panel, ...marco);

  construirAlmacen(grupo);

  // Tubo vertical de tapas (punto 8): termina 13 mm sobre la boca del vaso
  // (la tapa cae poco y no se voltea) y cuelga del portico.
  const xt = est[2][0];
  const zTubo0 = zs + hV + 0.013, altoTubo = 0.075;
  const rTubo = rBoca + 0.005;
  const tubo = new THREE.Mesh(new THREE.CylinderGeometry(rTubo, rTubo, altoTubo, 40, 1, true),
    mat(0xcfe3ff, { transparent: true, opacity: 0.22, side: THREE.DoubleSide, roughness: 0.1, depthWrite: false }));
  tubo.position.copy(Vxyz(xt, y, zTubo0 + altoTubo / 2));
  const aros = [0.004, altoTubo - 0.004].map((dz) => {
    const a = new THREE.Mesh(new THREE.TorusGeometry(rTubo, 0.0022, 8, 40), MAT_ALU);
    a.rotation.x = Math.PI / 2; a.position.copy(Vxyz(xt, y, zTubo0 + dz));
    return a;
  });
  const colgante = [perfil(Vxyz(xt, yP, zViga - 0.01), Vxyz(xt, y + rTubo + 0.004, zViga - 0.01), 0.012),
    perfil(Vxyz(xt, y + rTubo + 0.004, zViga - 0.01), Vxyz(xt, y + rTubo + 0.004, zTubo0 + altoTubo - 0.004), 0.012)];
  grupo.add(tubo, ...aros, ...colgante);
  registrar('tubo_tapas', tubo, ...aros);
  registrar('estructura', ...colgante);
  P.pilaTapas = [];
  for (let k = 0; k < 10; k++) {
    const t = cilindro(rBoca, 0.005, COLOR.tapa, Vxyz(xt, y, zTubo0 + 0.003 + k * 0.0062));
    grupo.add(t);
    P.pilaTapas.push(t);
    registrar('tubo_tapas', t);
  }
  // Escape de dos dedos (servo al frente, por encima del haz de la cortina).
  const servoTapas = servo(Vxyz(xt, y - rTubo - 0.015, zTubo0 + 0.03));
  const dedos = [caja(0.012, 0.018, 0.003, 0xd9261a, Vxyz(xt, y - rTubo + 0.004, zTubo0 - 0.001)),
    caja(0.012, 0.018, 0.003, 0xd9261a, Vxyz(xt, y - rTubo + 0.004, zTubo0 + 0.0075))];
  grupo.add(servoTapas, ...dedos);
  soporteServo(grupo, servoTapas, Vxyz(xt, y - rTubo, zTubo0 + 0.02), 'servo_tapas');
  registrar('servo_tapas', servoTapas, ...dedos);
  P.tapas = { x: xt, y, zBase: zTubo0 + 0.003, dedos, rTapa: rBoca };

  // Prensa (punto 9): servo MG996R con una leva excentrica en su eje; al
  // girar 0 -> 180 grados la leva empuja un piston guiado que baja 13 mm
  // (2 x excentricidad) sobre la tapa, y vuelve. Un resorte limita la
  // fuerza. El servo sabe en que angulo quedo: no hace falta sensor.
  const xpz = est[3][0];
  const zPiston = zs + hV + 0.005 + 0.012;   // 12 mm sobre la tapa: el vaso pasa por debajo
  const exc = 0.0065;
  const zEje = zPiston + 0.012 + 0.07 + 0.022 + exc;
  const piston = new THREE.Group();
  piston.add(cilindro(rBoca, 0.012, COLOR.acero, Vxyz(0, 0, 0.006), { metalness: 0.7 }));
  piston.add(barra(Vxyz(0, 0, 0.012), Vxyz(0, 0, 0.082), 0.005, COLOR.plata, { metalness: 0.8 }));
  const resorte = new THREE.Mesh(new THREE.TorusGeometry(0.008, 0.0012, 6, 20), mat(0xb8bcc2, { metalness: 0.8 }));
  for (let k = 0; k < 6; k++) { const r = resorte.clone(); r.rotation.x = Math.PI / 2; r.position.copy(Vxyz(0, 0, 0.04 + k * 0.006)); piston.add(r); }
  piston.add(cilindro(0.006, 0.01, 0x333333, Vxyz(0, 0, 0.087)));   // rodillo seguidor
  piston.position.copy(Vxyz(xpz, y, zPiston));
  const guia = caja(0.03, 0.02, 0.012, COLOR.impreso, Vxyz(xpz, y, zPiston + 0.05));
  const leva = new THREE.Group();
  leva.position.copy(Vxyz(xpz, y, zEje));
  const disco = cilindro(0.022, 0.008, 0xe0c341, Vxyz(0, 0, 0), { metalness: 0.4 });
  disco.rotation.x = Math.PI / 2;
  const discoExc = new THREE.Group();
  discoExc.add(disco);
  disco.position.set(exc, 0, 0);
  leva.add(discoExc);
  const motorLeva = servo(Vxyz(xpz, y + 0.036, zEje), { grande: true });
  motorLeva.rotation.x = Math.PI / 2;   // eje horizontal, hacia la leva
  const reductor = barra(Vxyz(xpz, y + 0.008, zEje), Vxyz(xpz, y + 0.02, zEje), 0.003, COLOR.plata);
  const placaPrensa = [perfil(Vxyz(xpz, yP, zViga - 0.01), Vxyz(xpz, y + 0.075, zViga - 0.01), 0.012),
    perfil(Vxyz(xpz, y + 0.075, zViga - 0.01), Vxyz(xpz, y + 0.075, zPiston + 0.04), 0.012),
    perfil(Vxyz(xpz, y + 0.075, zPiston + 0.05), Vxyz(xpz, y + 0.012, zPiston + 0.05), 0.01)];
  grupo.add(piston, guia, leva, motorLeva, reductor, ...placaPrensa);
  soporteServo(grupo, motorLeva, Vxyz(xpz, y + 0.075, zEje), 'motor_prensa', true);
  registrar('motor_prensa', piston, leva, motorLeva, reductor);
  registrar('estructura', guia, ...placaPrensa);
  P.prensa = { piston, leva: discoExc, zPiston, exc };

  // Empujador de descarga (punto 10): servo grande con manivela; la paleta
  // pasa de lado el vaso tapado a la canaleta (-y). Los rechazados no se
  // empujan: siguen en la cinta y caen por su extremo a la bandeja.
  const xd = est[4][0];
  const yEmpReposo = y + rBoca + 0.006;
  const paletaEmp = caja(0.06, 0.004, 0.05, 0x2a8c46, Vxyz(xd, yEmpReposo, zs + 0.035));
  const servoEmp = servo(Vxyz(xd, y + 0.085, zs + 0.03), { grande: true });
  const bielaEmp = barra(Vxyz(xd, yEmpReposo + 0.002, zs + 0.035), Vxyz(xd, y + 0.075, zs + 0.05), 0.0018, COLOR.plata);
  // Buje guia del vastago, detras de la cinta (nada cruza por encima del
  // paso de los vasos).
  const buje = caja(0.02, 0.016, 0.016, COLOR.impreso, Vxyz(xd, y + 0.06, zs + 0.042));
  const soporteEmp = perfil(Vxyz(xd, y + 0.085, 0), Vxyz(xd, y + 0.085, zs + 0.01));
  const brazoBuje = perfil(Vxyz(xd, y + 0.06, zs + 0.034), Vxyz(xd, y + 0.085, zs + 0.034), 0.01);
  grupo.add(paletaEmp, servoEmp, bielaEmp, buje, soporteEmp, brazoBuje);
  soporteServo(grupo, servoEmp, Vxyz(xd, y + 0.085, zs + 0.01), 'servo_empujador', true);
  registrar('servo_empujador', paletaEmp, servoEmp, bielaEmp);
  registrar('estructura', soporteEmp, buje, brazoBuje);
  const yEmpFin = G.canaleta.inicio[1] - 0.03 + rBoca + 0.006;
  P.empujador = { paleta: paletaEmp, biela: bielaEmp, horn: servoEmp.userData.horn, xd, y, zs, yReposo: yEmpReposo, yFin: yEmpFin };

  // Bandeja de rechazo de vasos al final de la cinta, con un labio inclinado.
  const bj = G.bandeja_rechazo_vasos;
  const bandeja = new THREE.Group();
  bandeja.add(caja(0.10, 0.12, 0.004, 0x5a616c, Vxyz(0, 0, 0.002)));
  for (const [dx, dy, sx, sy] of [[0.05, 0, 0.004, 0.12], [-0.05, 0, 0.004, 0.12], [0, 0.06, 0.10, 0.004], [0, -0.06, 0.10, 0.004]]) {
    bandeja.add(caja(sx, sy, 0.06, 0x8b939f, Vxyz(dx, dy, 0.03), { transparent: true, opacity: 0.55 }));
  }
  bandeja.position.copy(Vxyz(bj[0], bj[1], 0));
  const labio = caja(0.05, ancho, 0.003, 0x8b939f, Vxyz(x1 + 0.032, y, zs - 0.036));
  labio.rotation.z = -0.9;
  grupo.add(bandeja, labio);
  registrar('bandeja_rechazo_vasos', bandeja, labio);
  const et = etiqueta('Rechazo de vasos', { alto: 0.01, color: '#e5534b' });
  et.position.copy(Vxyz(bj[0], bj[1], 0.09));
  grupo.add(et);
  P.bandeja = Vxyz(bj[0], bj[1], 0.004);
  P.finCintaVasos = Vxyz(x1 + 0.012, y, zs);

  // La mano del sabotaje de la cortina: entra desde el lado del operador (-y)
  // a media altura del vaso (donde esta el haz), entre tapa y prensa (igual
  // que en PyBullet).
  const xm = (est[2][0] + est[3][0]) / 2;
  const mano = new THREE.Group();
  mano.add(caja(0.04, 0.05, 0.02, COLOR.piel, Vxyz(0, 0.005, 0)));
  mano.add(barra(Vxyz(0, -0.02, 0), Vxyz(0, -0.2, 0.06), 0.02, COLOR.piel));
  mano.position.copy(Vxyz(xm, y - 0.06, zs + 0.065));
  mano.visible = false;
  mano.userData.parte = true;
  grupo.add(mano);
  P.mano = mano;
  // Sabotaje "mano que saca un vaso": a media altura, agarrando el vaso.
  const manoSaca = mano.clone();
  manoSaca.visible = false;
  grupo.add(manoSaca);
  P.manoSaca = manoSaca;

  // Motor de la cinta de vasos en el rodillo de la ENTRADA, del lado del
  // operador (el extremo de salida queda libre para la bandeja).
  const motor = nema17(Vxyz(x0, y - ancho / 2 - 0.024, zs - 0.011));
  P.nemaVasos = motor;
  grupo.add(motor);
  registrar('motor_cinta_vasos', motor);
  registrar('cinta_vasos', ...grupo.children.filter((o) => !o.userData.parte && !o.isSprite));

  escena.add(grupo);
}

// Almacen por denominacion: 6 tubos en hexagono sobre una placa, con una
// compuerta con bisagra bajo cada uno; en el centro el servo del selector
// con su pico giratorio; debajo la tolva oblicua que lleva el lote al vaso.
function construirAlmacen(grupo) {
  const al = G.almacen;
  const [cx, cy] = al.centro;
  const zBase = al.tubos[0].base[2];
  const zArriba = al.tubo_z_arriba;
  const R = al.radio_carrusel;
  const ang = (g) => (g * Math.PI) / 180;
  // Placa FIJA con un solo agujero (sobre el vaso de llenado). Cuelga del
  // portico con dos varillas por FUERA del giro de los tubos.
  const placa = cilindro(0.058, 0.004, 0x3a4250, Vxyz(cx, cy, zBase - 0.002), { transparent: true, opacity: 0.75 });
  grupo.add(placa);
  registrar('almacen', placa);
  for (const g of [30, 150]) {
    const px = cx + 0.056 * Math.cos(ang(g)), py = cy + 0.056 * Math.sin(ang(g));
    const v = barra(Vxyz(px, py, P.portico.z - 0.01), Vxyz(px, py, zBase - 0.004), 0.003, MAT_ALU);
    grupo.add(v);
    registrar('estructura', v);
  }
  // Obturador del agujero (servo SG90 bajo la placa) y embudo corto al vaso.
  const tv = al.tolva;
  const hueco = Vxyz(tv.salida[0], tv.salida[1], zBase - 0.004);
  const fuera = new THREE.Vector3(tv.salida[0] - cx, 0, -(tv.salida[1] - cy)).normalize();
  const obturador = new THREE.Group();
  obturador.position.copy(hueco).addScaledVector(fuera, 0.02).add(new THREE.Vector3(0, -0.004, 0));
  obturador.lookAt(obturador.position.clone().add(fuera));
  obturador.add(Object.assign(cilindro(0.017, 0.002, 0x9c2a22, new THREE.Vector3(0, 0, -0.02), {}, 24)));
  const servoObt = servo(hueco.clone().addScaledVector(fuera, 0.034).add(new THREE.Vector3(0, -0.012, 0)));
  const tolva = embudo(Vxyz(tv.salida[0], tv.salida[1], tv.z_arriba), tv.radio, Vxyz(tv.salida[0], tv.salida[1], tv.z_abajo), 0.014, 0xcfd3da,
    { transparent: true, opacity: 0.45, metalness: 0.6, depthWrite: false });
  grupo.add(obturador, servoObt, tolva);
  const ladoObt = new THREE.Vector3(-fuera.z, 0, fuera.x);
  soporteServo(grupo, servoObt, hueco.clone().addScaledVector(fuera, 0.034).addScaledVector(ladoObt, 0.02).add(new THREE.Vector3(0, 0.002, 0)), 'servo_obturador');
  registrar('servo_obturador', obturador, servoObt);
  registrar('almacen', tolva);
  P.obturador = obturador;
  P.hueco = hueco;
  P.tolva = Vxyz(tv.salida[0], tv.salida[1], tv.z_abajo);

  // Carrusel que GIRA: disco de arriba con los 6 tubos colgados (sus fondos
  // pasan a 0,5 mm de la placa fija: las pilas resbalan sobre ella). Lo
  // mueve un 28BYJ-48 por el eje central; un Hall ve el iman de referencia.
  const carrusel = new THREE.Group();
  carrusel.position.copy(Vxyz(cx, cy, 0));
  const disco = cilindro(0.052, 0.003, 0x566070, new THREE.Vector3(0, zArriba + 0.0015, 0), { transparent: true, opacity: 0.55, metalness: 0.4 });
  const eje = cilindro(0.004, zArriba - zBase + 0.03, COLOR.acero, new THREE.Vector3(0, (zArriba + zBase) / 2 + 0.01, 0), { metalness: 0.8 });
  // Iman de referencia (neodimio 6 x 3 mm) sobre el disco, a R+15 mm y
  // entre los tubos de 330 y 30 grados; el Hall queda 4 mm encima.
  const iman = cilindro(0.003, 0.003, 0x8f96a0, new THREE.Vector3(R + 0.015, zArriba + 0.0045, 0), { metalness: 0.9 });
  carrusel.add(disco, eje, iman);
  registrar('almacen', disco, eje);
  P.tubos = {};
  for (const t of al.tubos) {
    const rel = new THREE.Vector3(t.base[0] - cx, 0, -(t.base[1] - cy));
    const tubo = new THREE.Mesh(new THREE.CylinderGeometry(t.radio + 0.001, t.radio + 0.001, t.alto, 28, 1, true),
      mat(0xcfe3ff, { transparent: true, opacity: 0.22, side: THREE.DoubleSide, roughness: 0.1, depthWrite: false }));
    tubo.position.copy(rel).add(new THREE.Vector3(0, zBase + t.alto / 2, 0));
    const aro = new THREE.Mesh(new THREE.TorusGeometry(t.radio + 0.001, 0.0012, 8, 28), mat(COLOR.plata, { metalness: 0.7 }));
    aro.rotation.x = Math.PI / 2;
    aro.position.copy(rel).add(new THREE.Vector3(0, zArriba, 0));
    const texto = t.denominacion === 'otras' ? 'otras' : `$${t.denominacion.toLocaleString('es-CO')}`;
    const et = etiqueta(texto, { alto: 0.009, color: t.denominacion === 'otras' ? '#8b949e' : '#f2b134' });
    et.position.copy(rel).add(new THREE.Vector3(0, zArriba + 0.008, 0)).addScaledVector(rel.clone().normalize(), 0.02);
    const pila = new THREE.Group();
    pila.position.copy(rel).add(new THREE.Vector3(0, zBase, 0));
    pila.userData.parte = true;
    carrusel.add(tubo, aro, et, pila);
    registrar('almacen', tubo, aro);
    P.tubos[t.denominacion] = { pila, n: 0, radio: t.radio, alto: t.alto, anguloCasa: Math.atan2(t.base[1] - cy, t.base[0] - cx), vaciarEn: 0 };
  }
  grupo.add(carrusel);
  const motor = cilindro(0.014, 0.019, 0xc9c9c9, Vxyz(cx, cy, zArriba + 0.02), { metalness: 0.5 });
  const soporte = [barra(Vxyz(cx, cy, zArriba + 0.03), Vxyz(cx, cy, P.portico.z - 0.012), 0.004, MAT_ALU),
    barra(Vxyz(cx, cy, P.portico.z - 0.012), Vxyz(cx, P.portico.y, P.portico.z - 0.012), 0.004, MAT_ALU)];
  grupo.add(motor, ...soporte);
  registrar('motor_carrusel', motor, carrusel);
  registrar('estructura', ...soporte);
  P.carrusel = { grupo: carrusel, angulo: 0, libre: 0, cx, cy, R, zBase,
    carga: ang(al.angulo_carga), agujero: ang(al.angulo_agujero) };
  const et = etiqueta('Almacén tipo revólver', { alto: 0.011, color: '#3fb68b' });
  et.position.copy(Vxyz(cx - 0.08, cy - 0.02, zArriba + 0.03));
  grupo.add(et);
}

// Gira el carrusel (en cola: un movimiento empieza cuando termina el
// anterior) hasta que el tubo `denominacion` quede en `anguloDestino`.
// Devuelve cuantos segundos faltan para que termine el giro.
function girarCarrusel(denominacion, anguloDestino, retraso = 0) {
  const c = P.carrusel;
  const t = P.tubos[denominacion] || P.tubos.otras;
  if (!c || !t) return 0;
  let objetivo = anguloDestino - t.anguloCasa;
  const actual = c.objetivo ?? c.angulo;
  let dif = Math.atan2(Math.sin(objetivo - actual), Math.cos(objetivo - actual));
  objetivo = actual + dif;
  c.objetivo = objetivo;
  const dur = Math.max(0.05, seg('carrusel_giro', 500) * Math.abs(dif) / Math.PI);
  const ahora = performance.now() / 1000;
  const inicio = Math.max(ahora + retraso / VEL, c.libre);
  c.libre = inicio + dur / VEL;
  const desde = actual;
  animar(dur, (u) => { c.angulo = desde + dif * suave(u); c.grupo.rotation.y = c.angulo; },
    { retraso: (inicio - ahora) * VEL });
  return (c.libre - ahora) * VEL;
}

function colorMoneda(denominacion, i) {
  if (denominacion === 500 || denominacion === 1000) return i % 2 ? COLOR.plata : COLOR.oro;
  return denominacion === 50 || denominacion === 100 ? (i % 2 ? COLOR.plata : 0xb8b9bd) : COLOR.oro;
}

function sincronizarAlmacen() {
  const al = estado.almacen || {};
  for (const d of [...DENOMINACIONES, 'otras']) {
    const tubo = P.tubos && P.tubos[d];
    if (!tubo) continue;
    const n = Number(al[String(d)] || 0);
    while (tubo.n < n) {
      const moneda = cilindro(tubo.radio - 0.0025, 0.0018, colorMoneda(d, tubo.n),
        new THREE.Vector3(0, 0.002 + tubo.n * G.almacen.grosor_moneda, 0), { metalness: 0.85, roughness: 0.3 });
      tubo.pila.add(moneda);
      tubo.n++;
    }
    // Si su lote esta cayendo (animarEmbalado), la pila baja cuando cae.
    while (tubo.n > n && performance.now() >= tubo.vaciarEn) {
      tubo.pila.remove(tubo.pila.children[tubo.pila.children.length - 1]);
      tubo.n--;
    }
  }
}

function animarEmbalado(e) {
  // El carrusel pone ese tubo sobre el agujero, se abre el obturador y la
  // pila entera cae por el embudo al vaso de llenado.
  const tubo = P.tubos[e.denominacion];
  if (!tubo) return;
  const v = vasos.get(e.vaso);
  const listo = girarCarrusel(e.denominacion, P.carrusel.agujero);
  const abrir = seg('compuerta_tubo', 600) * 0.25;
  const o = P.obturador;
  animar(abrir, (u) => { o.rotation.x = -1.3 * suave(u); }, { retraso: listo, dueno: o });
  animar(abrir, (u) => { o.rotation.x = -1.3 * (1 - suave(u)); }, { retraso: listo + seg('compuerta_tubo', 600) * 0.75, dueno: o });
  P.carrusel.libre = Math.max(P.carrusel.libre, performance.now() / 1000 + (listo + seg('compuerta_tubo', 600)) / VEL);
  const n = Math.min(e.cantidad, 10);
  tubo.vaciarEn = performance.now() + ((listo + abrir) / VEL) * 1000;
  if (v) {
    v.llenando = true;
    animar(0.01, () => {}, { retraso: listo + abrir + n * 0.05 + 0.45, fin: () => { v.llenando = false; ajustarPila(v, e.cantidad); } });
  }
  const destino = v ? posEstacionVasos(1).add(new THREE.Vector3(0, 0.006, 0)) : P.tolva.clone();
  for (let i = 0; i < n; i++) {
    const desde = P.hueco.clone().add(new THREE.Vector3(0, 0.004 + 0.002 * i, 0));
    const m = cilindro(0.011, 0.0018, colorMoneda(e.denominacion, i), desde.clone(), { metalness: 0.85, roughness: 0.3 });
    m.visible = false;
    escena.add(m);
    const r = listo + abrir + i * 0.05;
    animar(0.01, () => { m.visible = true; }, { retraso: r });
    recorrer(m, [desde, P.tolva.clone(), destino], 0.4, { ease: caida, retraso: r, fin: () => escena.remove(m) });
  }
}

// Canaleta de entrega (puntos 10 y 12): dos rieles lisos a 15 grados que
// sostienen el vaso de la pestana del reborde. Los postes van por fuera del
// paso del vaso. Entrada en embudo (usuario, 2026-09-26): los rieles
// arrancan mas separados y unos mm por debajo de la pestana y se cierran en
// los primeros centimetros, asi un vaso que llega algo corrido o bajo cae
// sobre ellos en vez de chocar con la punta. Al final, un escape de dos
// dedos con UN servo suelta los vasos de a uno.
function construirCanaleta() {
  const c = G.canaleta;
  const grupo = new THREE.Group();
  const ini = V(c.inicio), fin = V(c.fin);
  const dir = new THREE.Vector3().subVectors(fin, ini).normalize();
  const s = c.separacion_rieles / 2, sE = c.separacion_entrada / 2;
  const largoH = Math.hypot(c.fin[0] - c.inicio[0], c.fin[1] - c.inicio[1]);
  const fEmbudo = c.largo_embudo / largoH;
  // Rieles forrados con cinta de PTFE (blanca) donde apoya la pestana.
  const PTFE = 0xf1f1ee;
  for (const lado of [-1, 1]) {
    const e = V([c.inicio[0] + lado * sE, c.inicio[1], c.inicio[2]]);
    const b = V([c.fin[0] + lado * s, c.fin[1], c.fin[2]]);
    const m = V([c.inicio[0] + lado * s, c.inicio[1] + (c.fin[1] - c.inicio[1]) * fEmbudo,
      c.inicio[2] + (c.fin[2] - c.inicio[2]) * fEmbudo]);
    grupo.add(barra(e, m, c.diametro_riel / 2, PTFE, { roughness: 0.35 }));
    grupo.add(barra(m, b, c.diametro_riel / 2, PTFE, { roughness: 0.35 }));
    grupo.add(new THREE.Mesh(new THREE.SphereGeometry(c.diametro_riel / 2, 10, 10), mat(PTFE, { roughness: 0.35 })).translateX(m.x).translateY(m.y).translateZ(m.z));
    for (const t of [0.12, 0.55]) {
      const r = m.clone().lerp(b, t);
      const afuera = r.clone().add(new THREE.Vector3(lado * 0.028, 0, 0));
      grupo.add(barra(r.clone().add(new THREE.Vector3(0, -0.003, 0)), afuera.clone().add(new THREE.Vector3(0, -0.003, 0)), 0.003, MAT_ALU));
      grupo.add(perfil(new THREE.Vector3(afuera.x, 0, afuera.z), new THREE.Vector3(afuera.x, afuera.y - 0.003, afuera.z), 0.012));
    }
  }

  // Escape de dos dedos (puntos 12 y 13), del lado +x, a media altura del
  // cuerpo del vaso: un balancin paralelo a los rieles, con un dedo en cada
  // punta, que gira sobre el eje de UN servo SG90. Dedo A (adelante) retiene
  // al primer vaso; dedo B entra en el hueco entre el primero y el segundo
  // (los cuerpos de 62 mm dejan 16 mm entre ellos aunque las bocas se
  // toquen). Soltar: A sale y B entra -- se va solo el primero y B sostiene
  // la fila --; despues B sale, A entra y la fila baja un lugar.
  const paso = G.vaso.diametro + 2 * G.vaso.reborde + 0.004;
  const primero = fin.clone().addScaledVector(dir, -0.04);           // centro del vaso contra A
  const pA = primero.clone().addScaledVector(dir, G.vaso.diametro / 2 + 0.004);
  const pB = primero.clone().addScaledVector(dir, -(G.vaso.diametro / 2 + (paso - G.vaso.diametro) / 2));
  const mitad = pA.distanceTo(pB) / 2;
  const adentro = new THREE.Vector3(-1, 0, 0);                        // hacia el eje de la canaleta
  const n = new THREE.Vector3().crossVectors(dir, adentro).normalize();
  if (n.y < 0) n.negate();
  const zAdentro = new THREE.Vector3().crossVectors(dir, n).normalize();   // eje local Z
  const base = new THREE.Matrix4().makeBasis(dir, n, zAdentro);
  const marco = new THREE.Quaternion().setFromRotationMatrix(base);
  const xBal = fin.x + 0.05;                                            // afuera del riel y de la pestana
  const pivote = pA.clone().lerp(pB, 0.5).add(new THREE.Vector3(0, -0.045, 0));
  pivote.x = xBal;
  const balancin = new THREE.Group();
  balancin.position.copy(pivote);
  balancin.quaternion.copy(marco);
  const giro = new THREE.Group();   // lo que gira (sobre el eje local Y = eje del servo)
  balancin.add(giro);
  const largoDedo = xBal - (fin.x + 0.027);
  giro.add(caja(2 * mitad + 0.01, 0.008, 0.004, 0xd9261a, new THREE.Vector3(0, 0, 0)));
  for (const sx of [mitad, -mitad]) {
    const dedo = barra(new THREE.Vector3(sx, 0, 0), new THREE.Vector3(sx, 0, largoDedo * (zAdentro.x < 0 ? 1 : -1)), 0.0025, 0xd9261a);
    giro.add(dedo);
  }
  const servoC = servo(new THREE.Vector3(0, -0.014, 0));
  balancin.add(servoC);
  grupo.add(balancin);
  balancin.updateMatrixWorld(true);
  const posteX = xBal + 0.03;
  const zPoste = pivote.z;
  grupo.add(perfil(new THREE.Vector3(posteX, 0, zPoste), new THREE.Vector3(posteX, pivote.y - 0.03, zPoste), 0.012));
  soporteServo(grupo, servoC, new THREE.Vector3(posteX, pivote.y - 0.03, zPoste), 'servo_compuerta_canaleta');
  P.posteCanaleta = new THREE.Vector3(posteX, 0, zPoste);
  // Retener = dedo A adentro: con el signo del eje, el angulo que mete la punta A.
  // Girar theta sobre Y lleva la punta A (+X local) hacia -Z local; si +Z
  // local apunta hacia adentro, retener es theta negativo, y al reves.
  const signo = zAdentro.x < 0 ? 1 : -1;
  const theta0 = Math.asin(Math.min(0.99, 0.007 / mitad));
  P.escape = { giro, retener: -signo * theta0, soltar: signo * theta0 };
  giro.rotation.y = P.escape.retener;
  registrar('servo_compuerta_canaleta', giro, servoC);
  registrar('canaleta_entrega', ...grupo.children.filter((o) => !o.userData.parte && !o.isSprite && o !== balancin));
  const et = etiqueta('Canaleta de entrega · 15°', { alto: 0.012, color: '#3fb68b' });
  et.position.copy(ini.clone().lerp(fin, 0.5).add(new THREE.Vector3(0.08, 0.06, 0)));
  grupo.add(et);
  P.canaleta = { ini, fin, dir };
  escena.add(grupo);
}

// ---------------------------------------------------------------------------
// pista, obstaculos, meta y carro
// ---------------------------------------------------------------------------

function cinta2D(puntos, ancho, alturaZ, color, extra) {
  // Tira de triangulos a lo largo de una polilinea (x, y de la simulacion).
  const pos = [];
  const idx = [];
  for (let i = 0; i < puntos.length; i++) {
    const a = puntos[Math.max(0, i - 1)], b = puntos[Math.min(puntos.length - 1, i + 1)];
    let dx = b[0] - a[0], dy = b[1] - a[1];
    const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
    const nx = -dy * ancho / 2, ny = dx * ancho / 2;
    const p1 = Vxyz(puntos[i][0] + nx, puntos[i][1] + ny, alturaZ);
    const p2 = Vxyz(puntos[i][0] - nx, puntos[i][1] - ny, alturaZ);
    pos.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);
    if (i > 0) { const k = 2 * i; idx.push(k - 2, k - 1, k, k - 1, k + 1, k); }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  const m = new THREE.Mesh(geo, mat(color, { side: THREE.DoubleSide, ...extra }));
  m.receiveShadow = true;
  return m;
}

function construirPista() {
  const p = G.pista;
  const grupo = new THREE.Group();
  grupo.add(cinta2D(p.linea, p.ancho + 0.02, 0.0012, 0x9a3b30, { roughness: 1 }));   // borde
  grupo.add(cinta2D(p.linea, p.ancho, 0.0016, COLOR.pista, { roughness: 1 }));
  grupo.add(cinta2D(p.linea, p.ancho_linea, 0.002, 0x0a0a0a, { roughness: 0.9 }));

  const ladrillo = texturaLadrillo();
  P.obstaculos = [];
  p.obstaculos.forEach((o, i) => {
    // El muro atraviesa la linea: largo "a lo ancho" de la pista, delgado a lo largo.
    const muro = new THREE.Mesh(new THREE.BoxGeometry(0.03, o.alto, o.largo), new THREE.MeshStandardMaterial({ map: ladrillo, roughness: 0.9 }));
    muro.position.copy(Vxyz(o.x, o.y, o.alto / 2));
    muro.rotation.y = o.rumbo;
    muro.castShadow = true;
    grupo.add(muro);
    const et = etiqueta(`Obstáculo ${i + 1}`, { alto: 0.02, color: '#e5534b' });
    et.position.copy(Vxyz(o.x, o.y, o.alto + 0.03));
    grupo.add(et);
    P.obstaculos.push(muro);
  });

  // Meta: franja NEGRA de lado a lado (la ven los 5 infrarrojos a la vez:
  // una a cuadros los confundiria) + banderin a cuadros. Y la marca de giro
  // antes del muelle (a la vuelta el carro da media vuelta ahi).
  const m = p.meta;
  for (const f of [p.franja_meta, p.franja_giro]) {
    const franja = new THREE.Mesh(new THREE.PlaneGeometry(f.ancho, p.ancho), mat(0x0a0a0a, { roughness: 0.9 }));
    franja.rotation.x = -Math.PI / 2;
    franja.rotation.z = f.rumbo;
    franja.position.copy(Vxyz(f.x, f.y, 0.0025));
    grupo.add(franja);
  }
  const lado = [-Math.sin(m.rumbo), Math.cos(m.rumbo)];
  const baseMastil = Vxyz(m.x + lado[0] * (p.ancho / 2 + 0.03), m.y + lado[1] * (p.ancho / 2 + 0.03), 0);
  grupo.add(barra(baseMastil, baseMastil.clone().add(new THREE.Vector3(0, 0.25, 0)), 0.004, COLOR.plata));
  const bandera = new THREE.Mesh(new THREE.PlaneGeometry(0.09, 0.06), new THREE.MeshStandardMaterial({ map: texturaAjedrez(), side: THREE.DoubleSide }));
  bandera.position.copy(baseMastil).add(new THREE.Vector3(0.045, 0.22, 0));
  grupo.add(bandera);
  const et = etiqueta('META', { alto: 0.03, color: '#f2b134', alcance: 4 });
  et.position.copy(baseMastil).add(new THREE.Vector3(0, 0.3, 0));
  grupo.add(et);

  // Marca de parada bajo el final de la canaleta (punto 13): la cruza el
  // extremo trasero del carro.
  const s = p.salida;
  const parada = new THREE.Mesh(new THREE.PlaneGeometry(0.02, p.ancho), mat(0xffffff));
  parada.rotation.x = -Math.PI / 2; parada.rotation.z = s.rumbo;
  parada.position.copy(Vxyz(s.x, G.canaleta.fin[1] - 0.01, 0.0026));
  grupo.add(parada);
  registrar('pista', ...grupo.children.filter((o) => !o.isSprite));
  escena.add(grupo);
}

// Muelle de carga (punto 13, usuario 2026-09-26): el carro no depende de
// que tan bien siga la linea para quedar alineado con la canaleta. Entra de
// REVERSA, como un camion a un muelle: dos guias en V en el piso lo centran
// por los RODILLOS guia de las esquinas traseras (boca 4,5 cm mas ancha por
// lado en 20 cm, ~13 grados; cierra a 3 mm de holgura; cara interna con cinta
// de PTFE) y dos topes con espuma frenan la cola del chasis justo
// bajo el final de la canaleta. El carro sabe que llego porque sus encoders
// dejan de contar contra el tope: no hace falta sensor. Los topes van a los
// lados (no en el centro): por el centro pasa el fondo del vaso que baja.
function construirMuelle() {
  const v = G.vehiculo;
  const s = G.pista.salida;
  const muelle = new THREE.Group();   // mismo marco local que el carro: +x adelante (sim)
  const L = v.largo, W = v.ancho, r = v.diametro_rueda / 2;
  // Las guias tocan los RODILLOS de las esquinas traseras (nunca las llantas),
  // con 3 mm de holgura por lado (sim/vehiculo_sim.py).
  const guiaY = v.rodillo_guia_y + v.rodillo_guia_radio + 0.003;
  const alto = 0.02, esp = 0.006;
  const xRueda = -L * 0.18;
  // Tramo recto desde la cola (donde quedan los rodillos) y boca de ~13 grados.
  const x0 = -L / 2 - 0.004, x1 = xRueda + r + 0.015, x2 = x1 + 0.20;   // mismas medidas que sim/vehiculo_sim.py
  for (const lado of [-1, 1]) {
    // Cara interna forrada con cinta de PTFE (blanca): la llanta resbala y el carro se centra.
    const recto = caja(x1 - x0, esp, alto, COLOR.impreso, Vxyz((x0 + x1) / 2, lado * (guiaY + esp / 2), alto / 2));
    const ptfe = caja(x1 - x0, 0.0008, alto, 0xf1f1ee, Vxyz((x0 + x1) / 2, lado * (guiaY + 0.0004), alto / 2));
    muelle.add(ptfe);
    const a = Vxyz(x1, lado * (guiaY + esp / 2), alto / 2), b = Vxyz(x2, lado * (guiaY + 0.045 + esp / 2), alto / 2);
    const largo = a.distanceTo(b);
    const boca = caja(largo, esp, alto, COLOR.impreso, a.clone().lerp(b, 0.5));
    boca.rotation.y = Math.atan2(-(b.z - a.z), b.x - a.x);   // girar en Y (Three) = girar en z (sim)
    muelle.add(recto, boca);
    registrar('muelle_carga', recto, boca);
    // Tope de la cola del chasis, a un costado del paso del vaso, con espuma.
    const xT = -L / 2 - 0.006;
    const tope = caja(0.01, 0.022, r + 0.012, 0x30363d, Vxyz(xT - 0.008, lado * 0.052, (r + 0.012) / 2));
    const espuma = caja(0.006, 0.022, 0.014, 0xe3c565, Vxyz(xT, lado * 0.052, r + 0.004), { roughness: 1 });
    muelle.add(tope, espuma);
    registrar('muelle_carga', tope, espuma);
  }
  const et = etiqueta('Muelle de carga', { alto: 0.01, color: '#e3c565' });
  et.position.copy(Vxyz(x2 - 0.02, -(guiaY + 0.07), 0.03));   // al costado: no tapa la del ESP32
  muelle.add(et);
  muelle.position.copy(Vxyz(s.x, s.y, 0));
  muelle.rotation.y = s.rumbo;
  escena.add(muelle);
}

function construirCarro() {
  const v = G.vehiculo;
  const s = G.pista.salida;
  const carro = new THREE.Group();   // marco local: +x adelante, +y izquierda, z arriba (sim)
  P.carroGrupo = carro;
  const L = v.largo, W = v.ancho, r = v.diametro_rueda / 2;
  const zPlaca = r + 0.004;
  const xCola = -L / 2;               // extremo trasero: ahi empieza la cuna

  // ---- Chasis: placa de acrilico ahumado de 3 mm y segundo piso (perfboard)
  // sobre separadores de bronce, solo en la mitad delantera: la de atras es la
  // bahia de carga donde cuelga el vaso.
  const xRueda = -L * 0.18;
  const chasis = caja(L, W, 0.003, 0x33414f, Vxyz(0, 0, zPlaca), { roughness: 0.35, metalness: 0.1 });
  chasis.receiveShadow = true;
  carro.add(chasis);
  const zPiso2 = zPlaca + 0.03;
  // Termina 1 cm antes de la escuadra del frente (no la atraviesa).
  // Segundo piso de x = 2 a 8 cm: atras queda el espacio del vaso colgado y
  // adelante la escuadra de los sensores (revision de espacio 2026-09-26).
  const piso2 = caja(0.06, W * 0.8, 0.0016, 0x2f6b3a, Vxyz(0.05, 0, zPiso2), { roughness: 0.8 });
  carro.add(piso2);
  for (const [dx, dy] of [[0.025, 0.042], [0.025, -0.042], [0.075, 0.042], [0.075, -0.042]]) {
    carro.add(barra(Vxyz(dx, dy, zPlaca + 0.0015), Vxyz(dx, dy, zPiso2 - 0.0008), 0.0024, 0xc8a24a, { metalness: 0.8 }));
  }

  // ---- Motorreductores TT (caja amarilla + motor plateado) bajo la placa,
  // con su rueda de 65 mm (llanta de goma y rin amarillo con rayos, que se
  // ven girar) y el encoder: disco de 20 ranuras + sensor de horquilla.
  P.ruedas = [];
  for (const lado of [-1, 1]) {
    const yMotor = lado * (W / 2 - 0.012);
    // Bajo la placa (su tope a 0,5 mm de ella), no metidos en el acrilico.
    const caja_tt = caja(0.062, 0.022, 0.019, 0xf2c230, Vxyz(xRueda + 0.02, yMotor, zPlaca - 0.0015 - 0.0005 - 0.0095), { roughness: 0.6 });
    const motor = cilindro(0.0105, 0.028, 0xc9ccd1, Vxyz(xRueda + 0.064, yMotor, zPlaca - 0.002 - 0.0105), { metalness: 0.8, roughness: 0.3 });
    motor.rotation.z = Math.PI / 2;
    const brida = caja(0.008, 0.004, 0.012, 0x20242b, Vxyz(xRueda + 0.02, lado * (W / 2 - 0.024), zPlaca - 0.007));
    carro.add(caja_tt, motor, brida);
    registrar('motores_carro', caja_tt, motor);

    const rueda = new THREE.Group();
    rueda.add(cilindro(r, 0.026, 0x111111, new THREE.Vector3(0, 0, 0), { roughness: 0.95 }));
    rueda.add(cilindro(r * 0.72, 0.027, 0xf2c230, new THREE.Vector3(0, 0, 0), { roughness: 0.5 }));
    rueda.add(cilindro(0.006, 0.026, 0xeeeeee, new THREE.Vector3(0, 0, 0)));
    for (const ang of [0, Math.PI / 3, 2 * Math.PI / 3]) {
      const rayo = new THREE.Mesh(new THREE.BoxGeometry(r * 1.35, 0.0285, 0.004), mat(0xd9a820));
      rayo.rotation.y = ang;
      rueda.add(rayo);
    }
    rueda.position.copy(Vxyz(xRueda, lado * (W / 2 + 0.013), r));
    rueda.rotation.x = Math.PI / 2;
    carro.add(rueda);
    P.ruedas.push(rueda);
    registrar('motores_carro', ...rueda.children);

    const disco = cilindro(0.013, 0.0015, 0x1a1a1a, Vxyz(xRueda, lado * (W / 2 - 0.026), r));
    disco.rotation.x = Math.PI / 2;
    // Encoder H206: placa vertical junto a la rueda, con la horquilla
    // abrazando el disco ranurado y sus pines (VCC, GND, D0).
    disco.userData.sensorId = 'encoders';
    carro.add(disco);
    const qEnc = orientar(Vxyz(0, lado, 0));
    construirModulo(lado > 0 ? 'enc_izq' : 'enc_der', carro, Vxyz(xRueda, lado * (W / 2 - 0.0333), r - 0.012), qEnc,
      { sensorId: 'encoders', etiquetaSobre: 0.012 });
    pinSuelto(`${lado > 0 ? 'motor_izq' : 'motor_der'}.M+`, carro, Vxyz(xRueda + 0.081, yMotor + 0.004, zPlaca - 0.0125), new THREE.Vector3(1, 0, 0), 'pad', new THREE.Vector3(0, 1, 0));
    pinSuelto(`${lado > 0 ? 'motor_izq' : 'motor_der'}.M-`, carro, Vxyz(xRueda + 0.081, yMotor - 0.004, zPlaca - 0.0125), new THREE.Vector3(1, 0, 0), 'pad', new THREE.Vector3(0, 1, 0));
    const etMotor = etiqueta(`Motor TT ${lado > 0 ? 'izq.' : 'der.'}`, { alto: 0.0042, alcance: 0.3 });
    etMotor.position.copy(Vxyz(xRueda + 0.064, yMotor, zPlaca - 0.03));
    carro.add(etMotor);
  }

  // Rodillos guia (rodamiento 623) en las esquinas traseras, un poco mas
  // afuera que las llantas: son lo que empujan las guias del muelle.
  for (const lado of [-1, 1]) {
    const rod = cilindro(v.rodillo_guia_radio, 0.01, 0xc9ccd1, Vxyz(-L / 2 + 0.008, lado * v.rodillo_guia_y, 0.012), { metalness: 0.8 });
    const soporteRod = caja(0.012, v.rodillo_guia_y - W / 2 + 0.004, 0.003, COLOR.impreso, Vxyz(-L / 2 + 0.008, lado * (W / 2 + (v.rodillo_guia_y - W / 2) / 2), 0.019));
    carro.add(rod, soporteRod);
    registrar('rodillos_guia', rod, soporteRod);
  }

  // ---- Rueda loca de bola (acero) con su carcasa, bajo el frente.
  const xLoca = L * 0.30;   // detras de la placa de infrarrojos (antes chocaban)
  carro.add(barra(Vxyz(xLoca, 0, 0.022), Vxyz(xLoca, 0, zPlaca - 0.0015), 0.004, 0x30363d));
  carro.add(cilindro(0.011, 0.01, 0x20242b, Vxyz(xLoca, 0, 0.017)));
  const loca = new THREE.Mesh(new THREE.SphereGeometry(0.008, 16, 16), mat(COLOR.plata, { metalness: 0.9, roughness: 0.2 }));
  loca.position.copy(Vxyz(xLoca, 0, 0.008));
  carro.add(loca);

  // ---- Energia: porta-baterias 2 x 18650 (7,4 V) sobre la placa, bajo el
  // segundo piso, e interruptor.
  // Atravesado (celdas a lo ancho): de x = 1,2 a 5,3 cm, delante del vaso.
  const xBat = 0.0325, zBat = zPlaca + 0.0015 + 0.006;
  const portaBat = caja(0.041, 0.077, 0.012, 0x151515, Vxyz(xBat, 0, zBat));
  carro.add(portaBat);
  const celdas = [-1, 1].map((k) => {
    const c18650 = cilindro(0.009, 0.065, 0x2a6fdb, Vxyz(xBat + k * 0.0095, 0, zBat + 0.006), { roughness: 0.4 });
    c18650.rotation.x = Math.PI / 2;
    return c18650;
  });
  carro.add(...celdas);
  registrar('bateria_carro', portaBat, ...celdas);
  pinSuelto('bateria.B+', carro, Vxyz(xBat + 0.014, 0.036, zBat + 0.0075), new THREE.Vector3(0, 1, 0), 'pad');
  pinSuelto('bateria.B-', carro, Vxyz(xBat + 0.014, -0.036, zBat + 0.0075), new THREE.Vector3(0, 1, 0), 'pad');
  const etBat = etiqueta('2 × 18650 (7,4 V) con BMS', { alto: 0.0042, alcance: 0.3 });
  etBat.position.copy(Vxyz(xBat, 0, zBat + 0.016));
  carro.add(etBat);
  // Interruptor con fusible de 3 A, en el piso de abajo (el de arriba lo
  // ocupa la placa GVS del ESP32).
  construirModulo('interruptor', carro, Vxyz(0.068, 0.03, zPlaca + 0.0015), yaw(0), { etiquetaSobre: 0.012, idComponente: 'interruptor_carro' });

  // ---- Electronica: el ESP32 DevKit de 30 pines en su placa GVS (la de los
  // labs), en el segundo piso; el puente H TB6612, en el de abajo.
  const xEsp = 0.05;
  construirModulo('esp32_carro', carro, Vxyz(xEsp, 0, zPiso2 + 0.0008), yaw(90), { idComponente: 'esp32_carro', etiquetaSobre: 0.03 });
  construirModulo('tb6612', carro, Vxyz(0.068, -0.03, zPlaca + 0.0035), yaw(0), { idComponente: 'puente_h_carro', etiquetaSobre: 0.022 });
  // Separadores del puente H.
  for (const [dx, dy] of [[-0.008, -0.008], [0.008, 0.008]]) carro.add(cilindro(0.0015, 0.002, 0xc8a24a, Vxyz(0.068 + dx, -0.03 + dy, zPlaca + 0.0025)));

  // ---- Arreglo de 5 infrarrojos TCRT5000 bajo el frente, en su soporte.
  P.irLinea = [];
  const n = v.sensores_linea, sep = v.separacion_sensores_linea;
  const xIr = L / 2 - 0.012;
  carro.add(caja(0.004, sep * n, 0.022, 0x20242b, Vxyz(xIr + 0.009, 0, 0.024)));   // soporte
  construirModulo('ir_linea', carro, Vxyz(xIr, 0, 0.009), yaw(0), { sensorId: 'linea_ir', etiquetaSobre: 0 });
  for (let i = 0; i < n; i++) {
    const yy = (i - (n - 1) / 2) * sep;
    const led = new THREE.Mesh(new THREE.SphereGeometry(0.0012, 10, 10), new THREE.MeshBasicMaterial({ color: 0x30363d }));
    led.position.copy(Vxyz(xIr - 0.005, yy, 0.0142));
    led.userData.sensorId = 'linea_ir';
    carro.add(led);
    P.irLinea.push(led);
  }
  const etIr = etiqueta('5 × TCRT5000 (línea)', { alto: 0.0042, alcance: 0.3 });
  etIr.position.copy(Vxyz(xIr + 0.02, 0, 0.005));
  carro.add(etIr);

  // ---- Adelante, en una escuadra: ultrasonico HC-SR04 (respaldo) y encima
  // el laser VL53L0X (principal: mide cada 33 ms, hasta ~1,2 m).
  const xFrente = L / 2 + 0.002, zUs = zPlaca + 0.02;
  carro.add(caja(0.0016, 0.03, 0.045, 0x20242b, Vxyz(xFrente - 0.004, 0, zPlaca + 0.024)));   // escuadra
  carro.add(caja(0.012, 0.03, 0.0016, 0x20242b, Vxyz(xFrente - 0.01, 0, zPlaca + 0.0023)));
  // HC-SR04 y VL53L0X mirando hacia adelante; sus pines salen por detras
  // (por la ranura de la escuadra).
  const qFrente = (cara) => orientar(cara);
  construirModulo('hcsr04', carro, Vxyz(xFrente + 0.001, 0, zUs), qFrente(new THREE.Vector3(1, 0, 0)), { sensorId: 'ultrasonico', etiquetaSobre: 0 });
  construirModulo('vl53_frontal', carro, Vxyz(xFrente + 0.003, 0, 0.074), qFrente(new THREE.Vector3(-1, 0, 0)), { sensorId: 'laser_frontal', etiquetaSobre: 0 });
  const etUs = etiqueta('HC-SR04 · VL53L0X', { alto: 0.0042, alcance: 0.3 });
  etUs.position.copy(Vxyz(xFrente + 0.012, 0, 0.088));
  carro.add(etUs);
  // Conos: el del ultrasonico hasta la distancia de obstaculo; el del laser
  // hasta la zona de frenado.
  const cono = new THREE.Mesh(new THREE.ConeGeometry(Math.tan(0.13) * v.distancia_obstaculo, v.distancia_obstaculo, 24, 1, true),
    new THREE.MeshBasicMaterial({ color: COLOR.cian, transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false }));
  cono.rotation.z = Math.PI / 2;
  cono.position.copy(Vxyz(xFrente + 0.01 + v.distancia_obstaculo / 2, 0, zUs));
  cono.userData.sensorId = 'ultrasonico';
  carro.add(cono);
  P.conoUS = cono;
  const conoTof = new THREE.Mesh(new THREE.ConeGeometry(Math.tan(0.218) * v.distancia_frenado, v.distancia_frenado, 24, 1, true),
    new THREE.MeshBasicMaterial({ color: COLOR.ambar, transparent: true, opacity: 0.07, side: THREE.DoubleSide, depthWrite: false }));
  conoTof.rotation.z = Math.PI / 2;
  conoTof.position.copy(Vxyz(xFrente + 0.004 + v.distancia_frenado / 2, 0, 0.074));
  conoTof.userData.sensorId = 'laser_frontal';
  carro.add(conoTof);
  P.conoTof = conoTof;
  // Conos de error probable (nominal + ~7 grados: el HC-SR04 tiene lobulos
  // laterales; el laser, desalineacion de montaje).
  const adelante = new THREE.Vector3(1, 0, 0);
  const [, errUS] = conosSensor(Vxyz(xFrente + 0.012, 0, zUs), adelante, v.distancia_obstaculo, 7.5, 15);
  const [, errTof] = conosSensor(Vxyz(xFrente + 0.003, 0, 0.074), adelante, v.distancia_frenado, 12.5, 17.5, COLOR.ambar);
  errUS.userData.sensorId = 'ultrasonico'; errTof.userData.sensorId = 'laser_frontal';
  carro.add(errUS, errTof);
  // Infrarrojos de linea: a 7 mm del piso (el TCRT5000 ve hasta ~15 mm).
  for (let i = 0; i < n; i++) {
    const yy = (i - (n - 1) / 2) * sep;
    for (const c of conosSensor(Vxyz(xIr, yy, 0.007), new THREE.Vector3(0, -1, 0), 0.007, 15, 20)) {
      c.userData.sensorId = 'linea_ir';
      carro.add(c);
    }
  }

  // Cuna (punto 13, usuario 2026-09-26): los mismos rieles de la canaleta,
  // forrados con cinta de PTFE, pero 3 mm MAS BAJOS que el final de la
  // canaleta y con la entrada en embudo (arrancan 4 mm mas separados y se
  // cierran en 20 mm): si el carro queda algo corrido o desnivelado, la
  // pestana cae sobre ellos en vez de chocar con su punta.
  const c = G.canaleta;
  const zRiel = c.fin[2] - c.caida_entrada;
  const sepR = c.separacion_rieles / 2, sepE = c.separacion_entrada / 2;
  const xEmb = xCola + 0.02;
  const PTFE = 0xf1f1ee;
  for (const lado of [-1, 1]) {
    const e = Vxyz(xCola, lado * sepE, zRiel), m = Vxyz(xEmb, lado * sepR, zRiel), b = Vxyz(0.01, lado * sepR, zRiel);
    const tramos = [barra(e, m, c.diametro_riel / 2, PTFE, { roughness: 0.35 }), barra(m, b, c.diametro_riel / 2, PTFE, { roughness: 0.35 })];
    carro.add(...tramos);
    registrar('cuna_carro', ...tramos);
    for (const xx of [xCola + 0.012, 0.0]) {
      const poste = barra(Vxyz(xx, lado * (sepE + 0.01), zPlaca), Vxyz(xx, lado * (sepE + 0.01), zRiel), 0.003, MAT_ALU);
      const brazo = barra(Vxyz(xx, lado * (sepE + 0.01), zRiel - 0.003), Vxyz(xx, lado * (xx < xEmb ? sepE : sepR), zRiel - 0.003), 0.002, MAT_ALU);
      carro.add(poste, brazo);
      registrar('cuna_carro', poste);
    }
  }
  // Tope delantero de la cuna con espuma del lado del vaso: el vaso llega
  // deslizando (con teflon desliza bien) y no rebota.
  carro.add(caja(0.004, sepR * 2 + 0.02, 0.03, 0x444b55, Vxyz(0.014, 0, zRiel - 0.012)));
  const espumaCuna = caja(0.006, sepR * 2, 0.026, 0xe3c565, Vxyz(0.009, 0, zRiel - 0.012), { roughness: 1 });
  carro.add(espumaCuna);
  registrar('cuna_carro', espumaCuna);
  // Soporte de 4 puntos a media altura del vaso (usuario, 2026-09-26): ademas
  // de colgar de los rieles, el cuerpo queda tomado adelante (espuma), atras
  // (lengueta) y a los dos costados (guias con cinta de PTFE, abiertas en
  // embudo atras para que el vaso entre deslizando). Sin cabeceo: el carro
  // puede ir mas rapido.
  const zMedio = zRiel - G.vaso.altura / 2;
  const rCuerpo = G.vaso.diametro / 2;
  const espumaBaja = caja(0.006, 0.04, 0.02, 0xe3c565, Vxyz(0.009, 0, zMedio), { roughness: 1 });
  // Colgada del tope delantero (no baja al chasis: ahi van las baterias).
  const soporteEspuma = barra(Vxyz(0.014, 0, zRiel - 0.027), Vxyz(0.014, 0, zMedio + 0.01), 0.003, MAT_ALU);
  carro.add(espumaBaja, soporteEspuma);
  registrar('cuna_carro', espumaBaja, soporteEspuma);
  for (const lado of [-1, 1]) {
    const yG = lado * (rCuerpo + 0.0025);
    const xIni = xCola + 0.03, xFin = 0.004;
    const recta = caja(xFin - xIni, 0.003, 0.014, 0xf1f1ee, Vxyz((xIni + xFin) / 2, yG, zMedio), { roughness: 0.4 });
    const boca = barra(Vxyz(xIni, yG, zMedio), Vxyz(xCola + 0.008, lado * (rCuerpo + 0.012), zMedio), 0.0018, 0xf1f1ee);
    const postes = [xIni + 0.01, xFin - 0.01].map((xx) => barra(Vxyz(xx, lado * (rCuerpo + 0.004), zPlaca),
      Vxyz(xx, lado * (rCuerpo + 0.004), zMedio - 0.007), 0.0022, MAT_ALU));
    carro.add(recta, boca, ...postes);
    registrar('cuna_carro', recta, boca, ...postes);
  }
  // Lengueta trasera (usuario, 2026-09-26): la cuna queda abierta por
  // atras (por ahi entra el vaso) y sobre teflon el vaso se saldria al
  // arrancar el carro. Trinquete pasivo del lado -y: al entrar, el cuerpo del
  // vaso la empuja hacia adelante (gira sobre su eje y se acuesta contra el
  // costado); cuando el vaso pasa, el resorte la devuelve DETRAS del cuerpo y
  // un pasador de tope no la deja abrirse hacia atras. Sin sensor ni servo.
  // Para sacar el vaso en la meta se levanta (cuelga de los rieles).
  const zL = zRiel - 0.035;
  const pivL = Vxyz(xCola + 0.016, -(sepE + 0.009), zL);
  const lengueta = new THREE.Group();
  lengueta.position.copy(pivL);
  const puntaL = Vxyz(0.016, 0.026, 0);
  const brazoL = barra(new THREE.Vector3(0, 0, 0), puntaL, 0.0025, 0xd9261a);
  lengueta.add(brazoL);
  const resorteL = new THREE.Mesh(new THREE.TorusGeometry(0.005, 0.0012, 6, 16), mat(0xb8bcc2, { metalness: 0.8 }));
  resorteL.rotation.x = Math.PI / 2;
  const ejeL = barra(pivL.clone().add(new THREE.Vector3(0, -0.012, 0)), pivL.clone().add(new THREE.Vector3(0, 0.006, 0)), 0.0015, MAT_ALU);
  const soporteL = barra(pivL.clone().add(new THREE.Vector3(0, -0.012, 0)), Vxyz(xCola + 0.012, -(sepE + 0.01), zL - 0.012), 0.002, MAT_ALU);
  // Pasador de tope, del lado de adentro de la punta: no deja que gire hacia atras.
  const topeL = barra(Vxyz(xCola + 0.016 + 0.019, -(sepE + 0.009) + 0.022, zL - 0.006), Vxyz(xCola + 0.016 + 0.019, -(sepE + 0.009) + 0.022, zL + 0.006), 0.0015, MAT_ALU);
  carro.add(lengueta, resorteL.translateX(pivL.x).translateY(pivL.y).translateZ(pivL.z), ejeL, soporteL, topeL);
  registrar('cuna_carro', brazoL, resorteL, topeL);
  P.lengueta = lengueta;

  // Infrarrojo de la cuna (TCRT5000): apunta al costado del vaso cargado, a
  // 6 mm de su cuerpo (ve hasta ~15 mm; antes quedaba a 15,5 mm: al limite).
  const yIrCuna = G.vaso.diametro / 2 + 0.006 + 0.003;
  // Cara del TCRT5000 hacia el vaso (-y); con esta orientacion el eje x
  // de la placa apunta hacia atras, asi que el centro va 13 mm adelante.
  const ir = construirModulo('ir_cuna', carro, Vxyz(xCola / 2 - 0.013, yIrCuna + 0.0025, zRiel - 0.03), orientar(Vxyz(0, 1, 0)), { sensorId: 'cuna', etiquetaSobre: 0 });
  carro.add(barra(Vxyz(xCola / 2, yIrCuna + 0.003, zRiel - 0.03), Vxyz(xCola / 2, sepE + 0.01, zRiel - 0.03), 0.0015, MAT_ALU));
  for (const c of conosSensor(Vxyz(xCola / 2, yIrCuna - 0.003, zRiel - 0.03), new THREE.Vector3(0, 0, 1), 0.012, 15, 20)) {   // hacia -y (el vaso)
    c.userData.sensorId = 'cuna';
    carro.add(c);
  }
  P.irCuna = ir;

  // Colocar el carro en la salida: la conversion de ejes hace que girar
  // `rumbo` alrededor de z (sim) sea girar `rumbo` alrededor de y (Three).
  // Vaso que lleva el carro (visible mientras va cargado).
  const vasoCarro = crearVaso('carro');
  vasoCarro.tapa.visible = true;
  vasoCarro.et.visible = false;
  vasoCarro.grupo.position.copy(Vxyz(-0.025, 0, zRiel - G.vaso.altura));
  vasoCarro.grupo.visible = false;
  carro.add(vasoCarro.grupo);
  P.vasoCarro = vasoCarro;
  carro.position.copy(Vxyz(s.x, s.y, 0));
  carro.rotation.y = s.rumbo;
  P.carroPose = { x: s.x, y: s.y, r: s.rumbo, ox: s.x, oy: s.y, or: s.rumbo };
  carro.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  escena.add(carro);
  P.carroDims = { zPlaca, zPiso2, piso2: { x0: 0.02, x1: 0.08, y: W * 0.4 }, W, L };
  P.carro = carro;
}

// ---------------------------------------------------------------------------
// modulos electronicos con sus pines reales y el conexionado pin a pin
// (fuente unica: sim/conexiones.py, que llega en G.conexiones)
// ---------------------------------------------------------------------------

const MM = 0.001;
const PIN = {};                 // "dispositivo.pin" -> {padre, tip, dir, eje, tipo, usados}
const MODULOS = {};             // dispositivo -> grupo
const LOTES = new Map();        // piezas repetidas (pines, bornes...) como InstancedMesh
const CAPAS_CABLES = [];        // lo que el boton "Cables" muestra u oculta
const CABLES = [];              // {nombre, tipo, largo (m), malla, zona}

function plantilla(dev) {
  const cx = G.conexiones;
  return cx.plantillas[cx.dispositivos[dev].plantilla];
}

// Piezas repetidas: una geometria y un material por tipo, y una
// InstancedMesh por padre (la escena o el carro, que se mueve).
const PIEZA = {
  base: () => [new THREE.BoxGeometry(2.5 * MM, 2.5 * MM, 2.5 * MM), mat(0x151515)],
  pin: () => [new THREE.BoxGeometry(0.64 * MM, 8.5 * MM, 0.64 * MM), mat(0xd4af37, { metalness: 0.9, roughness: 0.3 })],
  hembra: () => [new THREE.BoxGeometry(2.54 * MM, 8.5 * MM, 2.54 * MM), mat(0x111111)],
  borne: () => [new THREE.BoxGeometry(5 * MM, 10 * MM, 7.5 * MM), mat(0x1f7a45)],
  tornillo: () => [new THREE.CylinderGeometry(1.4 * MM, 1.4 * MM, 0.8 * MM, 10), mat(0xc9ccd1, { metalness: 0.9, roughness: 0.3 })],
  din: () => [new THREE.BoxGeometry(6.0 * MM, 35 * MM, 42 * MM), mat(0x8a939e)],
  jst: () => [new THREE.BoxGeometry(12.5 * MM, 6 * MM, 6 * MM), mat(0xf2f2f2)],
  pad: () => [new THREE.CylinderGeometry(1.3 * MM, 1.3 * MM, 0.3 * MM, 12), mat(0xd9d9d9, { metalness: 0.9, roughness: 0.3 })],
  usb: () => [new THREE.BoxGeometry(12 * MM, 4.5 * MM, 5 * MM), mat(0xc9ccd1, { metalness: 0.9, roughness: 0.3 })],
  carcasa: () => [new THREE.BoxGeometry(2.5 * MM, 14 * MM, 2.5 * MM), mat(0x141414)],
  ferrula: () => [new THREE.CylinderGeometry(0.9 * MM, 0.9 * MM, 8 * MM, 8), mat(0xc9ccd1, { metalness: 0.9, roughness: 0.3 })],
  enchufe: () => [new THREE.BoxGeometry(12.5 * MM, 12 * MM, 4.5 * MM), mat(0xefefef)],
};
const _geoPieza = {};
function lote(padre, tipo, matriz) {
  const clave = padre.uuid + '|' + tipo;
  if (!LOTES.has(clave)) LOTES.set(clave, { padre, tipo, matrices: [] });
  LOTES.get(clave).matrices.push(matriz);
}
function cerrarLotes() {
  for (const { padre, tipo, matrices } of LOTES.values()) {
    const [geo, mt] = (_geoPieza[tipo] ||= PIEZA[tipo]());
    const im = new THREE.InstancedMesh(geo, mt, matrices.length);
    matrices.forEach((m, i) => im.setMatrixAt(i, m));
    im.castShadow = false;
    im.userData.piezaRepetida = tipo;
    padre.add(im);
  }
  LOTES.clear();
}

// Texto impreso en la cara de arriba de la placa: el nombre de cada pin junto
// a el y el del modulo donde haya lugar (como la serigrafia real).
function serigrafia(tpl, nombre) {
  const [L, W] = tpl.tamano;
  const ppm = Math.min(16, 2048 / Math.max(L, W));
  const c = document.createElement('canvas');
  c.width = Math.ceil(L * ppm); c.height = Math.ceil(W * ppm);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#f4f4f4'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  const X = (x) => (x + L / 2) * ppm, Y = (y) => (W / 2 - y) * ppm;
  ctx.font = `600 ${1.45 * ppm}px "IBM Plex Mono", monospace`;
  const lados = new Set();
  const ocupado = [];
  for (const p of tpl.pines) {
    if (p.n.startsWith('esp.') || ['cable', 'usb', 'jack'].includes(p.tipo)) continue;
    ocupado.push([p.x, p.y]);
    const m = p.n.match(/^(G\d+)\.(G|V|S)$/);
    if (m) {
      // Placa GVS: el nombre del GPIO una vez por fila, afuera de la S.
      if (m[2] !== 'S') continue;
      ctx.save(); ctx.translate(X(p.x), Y(p.y + Math.sign(p.y) * 3.4)); ctx.rotate(-Math.PI / 2);
      ctx.fillText(m[1], 0, 0); ctx.restore();
      lados.add(Math.sign(p.y) * 1 + ':' + p.x);
      continue;
    }
    const cercaDeY = Math.abs(p.y) / (W / 2) >= Math.abs(p.x) / (L / 2);
    const texto = p.n.replace(/^(IN|OUT|T)\./, '');
    const vecinoEnX = tpl.pines.some((q) => q !== p && Math.abs(q.y - p.y) < 0.1 && Math.abs(q.x - p.x) < 3.5);
    if (cercaDeY && vecinoEnX && p.tipo === 'macho') {
      // Fila a lo largo de x con paso de 2,54 mm: el nombre girado, hacia el
      // centro de la placa (si no, los nombres se enciman).
      const sy = Math.sign(p.y || 1);
      ctx.save(); ctx.translate(X(p.x), Y(p.y - sy * 2.0)); ctx.rotate(-Math.PI / 2);
      ctx.textAlign = sy > 0 ? 'right' : 'left'; ctx.fillText(texto, 0, 0); ctx.restore();
      continue;
    }
    const d = p.tipo.startsWith('borne') ? 5.6 : 2.7;
    const [dx, dy] = cercaDeY ? [0, -Math.sign(p.y || 1) * d] : [-Math.sign(p.x || 1) * d, 0];
    ctx.fillText(texto, X(p.x + dx), Y(p.y + dy));
  }
  if (lados.size) {
    // Encabezado G V S de las columnas.
    const g = tpl.pines.filter((p) => /\.(G|V|S)$/.test(p.n));
    const xMin = Math.min(...g.map((p) => p.x));
    for (const s of [1, -1]) for (const [col, dy] of [['G', 17.78], ['V', 20.32], ['S', 22.86]]) ctx.fillText(col, X(xMin - 3), Y(s * dy));
  }
  if (nombre) {
    // El nombre donde no tape pines ni piezas.
    const piezas = (tpl.partes || []).map((pt) => [pt.p[0], pt.p[1], ((pt.caja || [pt.cilindro?.[0] * 2 || 0])[0]) / 2 + 2]);
    const libre = (x, y) => ocupado.every(([a, b]) => Math.hypot(a - x, b - y) > 4) && piezas.every(([a, b, r]) => Math.hypot(a - x, b - y) > r);
    const candidatos = [[0, 0], [0, W / 2 - 3], [0, -W / 2 + 3], [-L / 4, 0], [L / 4, 0], [-L / 4, W / 2 - 3], [L / 4, -W / 2 + 3]];
    const sitio = candidatos.find(([x, y]) => libre(x, y));
    if (sitio) {
      ctx.font = `700 ${Math.min(2.4, L / nombre.length * 1.4) * ppm}px "Space Grotesk", sans-serif`;
      ctx.fillText(nombre, X(sitio[0]), Y(sitio[1]));
    }
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(L * MM, W * MM),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2;
  return m;
}

// Arma un modulo con su placa, sus piezas y sus pines, y registra donde
// queda la punta de cada pin (en el marco del padre). `pos`/`quat` en el
// marco del padre (Three). Marco local del modulo: x a lo largo, y a lo
// ancho, z hacia la cara con componentes (como la simulacion).
function construirModulo(dev, padre, pos, quat, { etiquetaSobre = 0.02, idComponente = null, sensorId = null } = {}) {
  const enCarro = padre === P.carroGrupo;
  const tpl = plantilla(dev);
  const info = G.conexiones.dispositivos[dev];
  const [L, W, T] = tpl.tamano;
  const g = new THREE.Group();
  g.position.copy(pos);
  g.quaternion.copy(quat);
  const placa = caja(L * MM, W * MM, T * MM, tpl.color, Vxyz(0, 0, T * MM / 2),
    T > 5 ? { metalness: 0.6, roughness: 0.45 } : { roughness: 0.7 });
  g.add(placa);
  if (T <= 5 || dev === 'fusibles') {
    const s = serigrafia(tpl, info.nombre.split(' (')[0]);
    s.position.copy(Vxyz(0, 0, T * MM + 0.00012));
    g.add(s);
  }
  for (const pt of tpl.partes || []) {
    const extra = pt.metal ? { metalness: 0.85, roughness: 0.3 } : {};
    const m = pt.caja ? caja(pt.caja[0] * MM, pt.caja[1] * MM, pt.caja[2] * MM, pt.color, Vxyz(pt.p[0] * MM, pt.p[1] * MM, pt.p[2] * MM), extra)
      : cilindro(pt.cilindro[0] * MM, pt.cilindro[1] * MM, pt.color, Vxyz(pt.p[0] * MM, pt.p[1] * MM, pt.p[2] * MM), extra, 20);
    g.add(m);
  }
  g.traverse((o) => { if (o.isMesh) { o.castShadow = false; if (sensorId) o.userData.sensorId = sensorId; } });
  padre.add(g);
  g.updateMatrix();
  const M = g.matrix;
  const aPadre = (x, y, z) => Vxyz(x * MM, y * MM, z * MM).applyMatrix4(M);
  const dirPadre = (x, y, z) => Vxyz(x, y, z).applyQuaternion(g.quaternion).normalize();
  const matriz = (x, y, z, q = null) => new THREE.Matrix4().compose(aPadre(x, y, z),
    q ? g.quaternion.clone().multiply(q) : g.quaternion.clone(), new THREE.Vector3(1, 1, 1));
  const eje = dirPadre(1, 0, 0);
  const qV = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI / 2);   // girar 90 grados en planta
  for (const p of tpl.pines) {
    const s = p.abajo ? -1 : 1;
    const z0 = p.abajo ? 0 : T;
    let tip, dir;
    const haciaFuera = Math.abs(p.y) / (W / 2) >= Math.abs(p.x) / (L / 2) ? [0, Math.sign(p.y) || 1, 0] : [Math.sign(p.x) || 1, 0, 0];
    switch (p.tipo) {
      case 'macho':
        lote(padre, 'base', matriz(p.x, p.y, z0 + s * 1.25));
        lote(padre, 'pin', matriz(p.x, p.y, z0 + s * 4.25));
        tip = aPadre(p.x, p.y, z0 + s * 16.5); dir = dirPadre(0, 0, s);
        break;
      case 'hembra':
        lote(padre, 'hembra', matriz(p.x, p.y, z0 + 4.25));
        break;
      case 'borne': {
        const [fx, fy] = haciaFuera;
        lote(padre, 'borne', matriz(p.x, p.y, z0 + 5, fx ? qV : null));
        lote(padre, 'tornillo', matriz(p.x, p.y, z0 + 10.4));
        tip = aPadre(p.x + fx * 11.75, p.y + fy * 11.75, z0 + 4); dir = dirPadre(fx, fy, 0);
        break;
      }
      case 'borne_din':
        lote(padre, 'din', matriz(p.x, p.y, z0 + 17.5));
        lote(padre, 'tornillo', matriz(p.x, p.y - 8, z0 + 35.4));
        lote(padre, 'tornillo', matriz(p.x, p.y + 8, z0 + 35.4));
        tip = aPadre(p.x, p.y - 15, z0 + 43); dir = dirPadre(0, 0, 1);
        break;
      case 'jst':
        lote(padre, 'jst', matriz(p.x, p.y, z0 + 3));
        tip = aPadre(p.x, p.y, z0 + 18); dir = dirPadre(0, 0, 1);
        break;
      case 'pad':
        lote(padre, 'pad', matriz(p.x, p.y, z0 + 0.15));
        tip = aPadre(p.x, p.y, z0 + 1.5); dir = dirPadre(0, 0, 1);
        break;
      case 'usb': {
        const [fx, fy] = haciaFuera;
        lote(padre, 'usb', matriz(p.x, p.y, T / 2, fx ? qV : null));
        tip = aPadre(p.x + fx * 20, p.y + fy * 20, T / 2); dir = dirPadre(fx, fy, 0);
        break;
      }
      case 'jack': {
        const [fx, fy] = haciaFuera;
        tip = aPadre(p.x + fx * 14, p.y + fy * 14, 6.4); dir = dirPadre(fx, fy, 0);
        break;
      }
      default:
        tip = aPadre(p.x, p.y, T); dir = dirPadre(0, 0, 1);
    }
    if (tip) PIN[`${dev}.${p.n}`] = { padre, tip, dir, eje, tipo: p.tipo, usados: 0 };
  }
  if (etiquetaSobre) {
    const et = etiqueta(info.nombre, enCarro ? { alto: 0.0042, alcance: 0.3 } : { alto: 0.0058, alcance: 0.4 });
    et.position.copy(aPadre(0, 0, T + etiquetaSobre / MM));
    padre.add(et);
  }
  if (idComponente) registrar(idComponente, placa);
  MODULOS[dev] = g;
  return g;
}

// Pin de algo que no es una placa (el cable que sale de un sensor M18, de un
// servo, de una webcam...): solo se registra donde sale el hilo.
function pinSuelto(ref, padre, tip, dir = new THREE.Vector3(0, 1, 0), tipo = 'cable', eje = new THREE.Vector3(1, 0, 0)) {
  PIN[ref] = { padre, tip: tip.clone(), dir: dir.clone().normalize(), eje, tipo, usados: 0 };
}

// ---------------------------------------------------------------------------
// hilos y cables
// ---------------------------------------------------------------------------

const TIPOS_CABLE = {
  paso: { nombre: 'Paso a paso: 4 hilos, 2 pares trenzados', color: 0x2b2b2b, r: 0.0019 },
  servo: { nombre: 'Servo: 3 hilos (extensión de 22 AWG)', color: 0x6b3a1f, r: 0.0013 },
  sensor12: { nombre: 'Sensor NPN 12 V: 3 hilos, PVC', color: 0x8a939e, r: 0.0019 },
  senal: { nombre: 'Sensor digital 3,3 V: 3 hilos', color: 0x3a3f47, r: 0.0012 },
  i2c: { nombre: 'I2C + XSHUT: 5 hilos (SDA y SCL trenzados con GND)', color: 0x5b3e96, r: 0.0015 },
  cinco: { nombre: 'Luz 5 V: par', color: 0xd9d9d9, r: 0.0012 },
  usb: { nombre: 'USB (con ferrita)', color: 0x111111, r: 0.0022 },
  red: { nombre: 'Red 110 V', color: 0x1a1a1a, r: 0.0034 },
  interno: { nombre: 'Potencia dentro de la caja (18 AWG)', color: 0xd23a2a, r: 0.0009 },
  dupont: { nombre: 'Lógica dentro de la caja (Dupont)', color: 0x2d6fd0, r: 0.0006 },
  carro: { nombre: 'Carro (Dupont y pares)', color: 0x2d6fd0, r: 0.0006 },
};
const aThree = (p) => (p.isVector3 ? p.clone() : Vxyz(p[0], p[1], p[2]));

// Camino redondeado (curvas en cada esquina, como un cable real).
function redondear(pts, radio = 0.01) {
  const limpio = pts.filter((p, i) => i === 0 || p.distanceTo(pts[i - 1]) > 1e-4);
  const out = [limpio[0]];
  for (let i = 1; i < limpio.length - 1; i++) {
    const a = limpio[i - 1], p = limpio[i], b = limpio[i + 1];
    const d = Math.min(radio, a.distanceTo(p) * 0.45, p.distanceTo(b) * 0.45);
    const p1 = p.clone().addScaledVector(a.clone().sub(p).normalize(), d);
    const p2 = p.clone().addScaledVector(b.clone().sub(p).normalize(), d);
    for (let k = 0; k <= 4; k++) {
      const t = k / 4;
      out.push(p1.clone().multiplyScalar((1 - t) ** 2).addScaledVector(p, 2 * (1 - t) * t).addScaledVector(p2, t * t));
    }
  }
  out.push(limpio[limpio.length - 1]);
  return out.filter((p, i, arr) => i === 0 || p.distanceTo(arr[i - 1]) > 1e-5);
}

function tubo(puntos, r, color, radio) {
  const pts = redondear(puntos, radio);
  const camino = new THREE.CurvePath();
  let largo = 0;
  for (let i = 0; i + 1 < pts.length; i++) {
    camino.add(new THREE.LineCurve3(pts[i], pts[i + 1]));
    largo += pts[i].distanceTo(pts[i + 1]);
  }
  const malla = new THREE.Mesh(new THREE.TubeGeometry(camino, Math.max(8, pts.length * 3), r, 6, false),
    color && color.isMaterial ? color : mat(color, { roughness: 0.55 }));
  malla.castShadow = false;
  malla.userData.cable = true;
  malla.userData.camino = pts;      // para revisar que no atraviese nada
  malla.userData.radio = r;
  return { malla, largo };
}

// Funda de un cable de campo (lo que se ve por la estructura).
function funda(nombre, tipo, puntos, padre, zona = 'planta') {
  const t = TIPOS_CABLE[tipo];
  const { malla, largo } = tubo(puntos.map(aThree), t.r, t.color, t.r > 0.003 ? 0.02 : 0.01);
  padre.add(malla);
  CABLES.push({ nombre, tipo, largo, malla, zona });
  return malla;
}

const _matHilo = {};
// Un hilo de un pin a otro. `a` y `b` son pines registrados (o puntos);
// `ruta`, los puntos intermedios. Pone la carcasa Dupont o la ferrula en
// cada punta, segun el tipo de pin.
function hilo(a, b, color, ruta, padre, { r = 0.00055, nombre = null, tipo = 'dupont', zona = 'caja' } = {}) {
  const punta = (P, k) => {
    if (!P || P.isVector3 || Array.isArray(P)) return [aThree(P)];
    // Varios hilos al mismo pin (conector, cable integrado, borne): se abren.
    const n = P.total || 1;
    const sep = { jst: 2.5, cable: 1.2, jack: 1.4, pad: 1.0, borne: 0.7, borne_din: 0, usb: 1.0 }[P.tipo] ?? 0;
    const off = P.eje.clone().multiplyScalar(((k - (n - 1) / 2) * sep) * MM);
    let t = P.tip.clone().add(off);
    if (P.tipo === 'borne_din' && k % 2 === 1) t = t.add(P.eje.clone().cross(P.dir).multiplyScalar(-30 * MM));
    if (P.tipo === 'macho') {
      lote(padre, 'carcasa', new THREE.Matrix4().compose(t.clone().addScaledVector(P.dir, -7 * MM),
        new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), P.dir), new THREE.Vector3(1, 1, 1)));
    } else if (P.tipo === 'borne' || P.tipo === 'borne_din') {
      lote(padre, 'ferrula', new THREE.Matrix4().compose(t.clone().addScaledVector(P.dir, -4 * MM),
        new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), P.dir), new THREE.Vector3(1, 1, 1)));
    } else if ((P.tipo === 'jst') && !P.enchufe) {
      P.enchufe = true;
      lote(padre, 'enchufe', new THREE.Matrix4().compose(P.tip.clone().addScaledVector(P.dir, -8 * MM),
        new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), P.dir).multiply(
          new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), new THREE.Vector3(1, 0, 0))), new THREE.Vector3(1, 1, 1)));
    }
    return [t, t.clone().addScaledVector(P.dir, 6 * MM)];
  };
  const A = typeof a === 'string' ? PIN[a] : a, B = typeof b === 'string' ? PIN[b] : b;
  const ka = A && A.usados !== undefined ? A.usados++ : 0;
  const kb = B && B.usados !== undefined ? B.usados++ : 0;
  const pa = punta(A, ka), pb = punta(B, kb).reverse();
  const clave = color;
  _matHilo[clave] ||= mat(new THREE.Color(color).getHex(), { roughness: 0.5 });
  const { malla, largo } = tubo([...pa, ...(ruta || []).map(aThree), ...pb], r, _matHilo[clave], 0.006);
  padre.add(malla);
  if (nombre) CABLES.push({ nombre, tipo, largo, malla, zona });
  return malla;
}

// ---------------------------------------------------------------------------
// caja de control
// ---------------------------------------------------------------------------

// Placa con la cara de componentes hacia `normal` (Three): x = arriba x
// normal, para que la serigrafia se lea derecha mirando esa cara.
function orientar(normal) {
  const n = normal.clone().normalize();
  let x = new THREE.Vector3(0, 1, 0).cross(n);
  if (x.lengthSq() < 1e-6) x = new THREE.Vector3(1, 0, 0);
  x.normalize();
  return new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, n, x.clone().cross(n)));
}
const yaw = (grados) => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad(grados));

// Caja de control (tapa quitada para verla por dentro), ordenada como un
// tablero real: adelante la fila de logica (ESP32, reparto I2C,
// optoacopladores, PCA9685, ULN2003, drivers), atras la de potencia (fuente,
// fusibles, reguladores, bornera X2 en carril DIN), y entre y alrededor de
// las dos filas canaletas ranuradas: todos los hilos van por ellas, ninguno
// cruza por encima de otra placa. Los cables de campo entran por
// prensaestopas en la pared de adelante, el USB por la izquierda y la red por
// la derecha.
function construirCajaControl() {
  const grupo = new THREE.Group();
  // 36 x 24 x 8 cm: la fuente sola mide 159 x 97 mm y hacen falta las
  // canaletas. Al costado de la cinta de vasos, detras.
  const [bx, by] = [0.355, 0.145];
  const [ax, ay, az] = [0.36, 0.24, 0.08];
  const piso = caja(ax, ay, 0.003, 0x2a2f36, Vxyz(bx, by, 0.0015));
  const matPared = mat(0x9aa4b1, { transparent: true, opacity: 0.14, depthWrite: false, side: THREE.DoubleSide });
  const paredes = [[0, -ay / 2, ax, 0.003], [0, ay / 2, ax, 0.003], [-ax / 2, 0, 0.003, ay], [ax / 2, 0, 0.003, ay]]
    .map(([dx, dy, sx, sy]) => caja(sx, sy, az, matPared, Vxyz(bx + dx, by + dy, az / 2)));
  grupo.add(piso, ...paredes);
  registrar('esp32_fijo', piso, ...paredes);
  const z0 = 0.003;
  const en = (dx, dy, z = z0) => Vxyz(bx + dx, by + dy, z);

  // Canaletas ranuradas (25 x 30 mm, grises, con la tapa translucida).
  const DUCTOS = { yF: -0.105, yM: 0.005, xI: -0.1695, xD: 0.1695 };
  const matDucto = mat(0x9ca3ad, { roughness: 0.8 });
  const matTapa = mat(0xc9ced6, { transparent: true, opacity: 0.25, depthWrite: false });
  const ducto = (dx, dy, largo, alongX, ancho) => {
    const g = new THREE.Group();
    const [sx, sy] = alongX ? [largo, ancho] : [ancho, largo];
    g.add(caja(sx, sy, 0.0015, matDucto, en(dx, dy, z0 + 0.00075)));
    for (const s of [-1, 1]) {
      const pared = alongX ? caja(largo, 0.0015, 0.028, matDucto, en(dx, dy + s * ancho / 2, z0 + 0.014))
        : caja(0.0015, largo, 0.028, matDucto, en(dx + s * ancho / 2, dy, z0 + 0.014));
      g.add(pared);
      // Ranuras (los "dedos" de la canaleta).
      const n = Math.floor(largo / 0.008);
      for (let i = 0; i < n; i++) {
        const t = -largo / 2 + (i + 0.5) * (largo / n);
        const r = alongX ? caja(0.0035, 0.0017, 0.02, 0x7d848e, en(dx + t, dy + s * ancho / 2, z0 + 0.018))
          : caja(0.0017, 0.0035, 0.02, 0x7d848e, en(dx + s * ancho / 2, dy + t, z0 + 0.018));
        g.add(r);
      }
    }
    g.add(caja(sx, sy, 0.001, matTapa, en(dx, dy, z0 + 0.0285)));
    g.traverse((o) => { o.castShadow = false; });
    grupo.add(g);
    registrar('canaletas_caja', g);
  };
  ducto(0, DUCTOS.yF, 0.339 + 0.02, true, 0.02);
  ducto(0, DUCTOS.yM, 0.339 + 0.02, true, 0.02);
  ducto(DUCTOS.xI, (DUCTOS.yF + DUCTOS.yM) / 2, DUCTOS.yM - DUCTOS.yF - 0.02, false, 0.015);
  ducto(DUCTOS.xD, (DUCTOS.yF + DUCTOS.yM) / 2, DUCTOS.yM - DUCTOS.yF - 0.02, false, 0.015);
  // Canaleta de la fila de potencia, pegada a la bornera de la fuente.
  ducto(0, (DUCTOS.yM + 0.117) / 2 + 0.005, 0.117 - DUCTOS.yM - 0.01, false, 0.015);
  DUCTOS.segmentos = [[[DUCTOS.xI, DUCTOS.yF], [DUCTOS.xD, DUCTOS.yF]], [[DUCTOS.xD, DUCTOS.yF], [DUCTOS.xD, DUCTOS.yM]],
    [[DUCTOS.xD, DUCTOS.yM], [DUCTOS.xI, DUCTOS.yM]], [[DUCTOS.xI, DUCTOS.yM], [DUCTOS.xI, DUCTOS.yF]],
    [[0, DUCTOS.yM], [0, 0.108]]];

  // Fila de logica (adelante) y de potencia (atras). La placa GVS gira 180
  // grados: el USB del ESP32 queda hacia la pared izquierda.
  construirModulo('esp32_fijo', grupo, en(-0.117, -0.05), yaw(180), { idComponente: 'esp32_fijo' });
  construirModulo('hub_i2c', grupo, en(-0.045, -0.078), yaw(0), { idComponente: 'reparto_i2c' });
  construirModulo('opto', grupo, en(-0.045, -0.035), yaw(0), { idComponente: 'optoacopladores' });
  construirModulo('pca9685', grupo, en(0.02, -0.075), yaw(0), { idComponente: 'pca9685' });
  construirModulo('uln2003', grupo, en(0.005, -0.03), yaw(0), { idComponente: 'uln2003' });
  construirModulo('drivers', grupo, en(0.1, -0.05), yaw(0), { idComponente: 'drivers_cintas' });
  construirModulo('fuente', grupo, en(-0.093, 0.068), yaw(0), { idComponente: 'fuente', etiquetaSobre: 0.045 });
  construirModulo('buck6', grupo, en(0.045, 0.045), yaw(0), { idComponente: 'buck_servos' });
  construirModulo('fusibles', grupo, en(0.045, 0.093), yaw(0), { idComponente: 'fusibles' });
  construirModulo('buck5', grupo, en(0.115, 0.035), yaw(0), { idComponente: 'buck_5v' });
  // Bornera X2 sobre su carril DIN, con los puentes (2-3, 5-6, 7 a 13).
  grupo.add(caja(0.105, 0.035, 0.0075, 0xc9ccd1, en(0.125, 0.092, z0 + 0.00375), { metalness: 0.8 }));
  construirModulo('x2', grupo, en(0.125, 0.092, z0 + 0.0075), yaw(0), { idComponente: 'bornera_x2', etiquetaSobre: 0.05 });
  const tplX2 = plantilla('x2');
  for (const grupoP of tplX2.puentes) {
    const xs = grupoP.map((n) => tplX2.pines.find((p) => p.n === n).x);
    const a = Math.min(...xs), b = Math.max(...xs);
    grupo.add(caja((b - a) * MM + 0.004, 0.003, 0.004, 0xd23a2a, en(0.125 + (a + b) / 2 * MM, 0.092, z0 + 0.0075 + 0.03)));
  }
  // Entrada de red IEC con interruptor, en la pared derecha.
  const iec = caja(0.012, 0.03, 0.026, 0x111111, en(ax / 2 - 0.003, 0.06, 0.03));
  const tecla = caja(0.006, 0.01, 0.012, 0xc8241c, en(ax / 2 + 0.005, 0.06, 0.036));
  grupo.add(iec, tecla);
  registrar('entrada_red', iec, tecla);
  ['L', 'N', 'PE'].forEach((n, i) => pinSuelto(`iec.${n}`, grupo, en(ax / 2 - 0.012, 0.052 + i * 0.008, 0.03),
    new THREE.Vector3(-1, 0, 0), 'pad', new THREE.Vector3(0, 0, -1)));
  // Prensaestopas: adelante (senales G1, motores y servos G2, cortos G3-G5),
  // USB a la izquierda.
  const glandes = [];
  // Uno grande (G1) para el mazo del portico; los demas, de a un cable.
  for (const [gx, rg] of [[0.2, 0.0055], [0.28, 0.0055], [0.297, 0.0055], [0.3338, 0.011], [0.3725, 0.0055], [0.405, 0.0055]]) {
    const pe = cilindro(rg, 0.012, 0x2b2b2b, Vxyz(gx, by - ay / 2, 0.014));
    pe.rotation.x = Math.PI / 2;
    glandes.push(pe);
  }
  const peUsb = cilindro(0.005, 0.012, 0x2b2b2b, Vxyz(bx - ax / 2, by - 0.047, 0.02));
  peUsb.rotation.z = Math.PI / 2;
  const peRed = cilindro(0.006, 0.012, 0x2b2b2b, Vxyz(bx + ax / 2, by + 0.02, 0.02));
  peRed.rotation.z = Math.PI / 2;
  const peLuz = cilindro(0.005, 0.012, 0x2b2b2b, Vxyz(bx - ax / 2, by - 0.079, 0.02));
  peLuz.rotation.z = Math.PI / 2;
  grupo.add(...glandes, peUsb, peRed, peLuz);
  const et = etiqueta('Caja de control', { alto: 0.014, color: '#f2b134' });
  et.position.copy(Vxyz(bx, by + ay / 2 + 0.01, 0.1));
  grupo.add(et);

  P.caja = { bx, by, ax, ay, yPared: by - ay / 2, xParedIzq: bx - ax / 2, xParedDer: bx + ax / 2, DUCTOS };
  escena.add(grupo);

  // Hub USB con fuente propia (el portatil necesita 3 USB) y el portatil.
  construirModulo('hub_usb', escena, Vxyz(0.26, 0.30, 0), yaw(0), { idComponente: 'hub_usb', etiquetaSobre: 0.02 });
  construirLaptop();
  construirEnlaceAsistente();
}

// Portatil del grupo: ASUS TUF Gaming A15 (ficha oficial de ASUS: 359 x 256 x 24,7 mm,
// 2,3 kg, pantalla de 15,6" 16:9 = 344 x 194 mm de area activa). Se modela a su medida real y
// se dibuja AMPLIADO x1,5 (usuario, 2026-09-28: para leer en el visor lo que responde el
// asistente); la etiqueta lo dice. Esta detras de la caja de control, en espacio libre (medido
// con la auditoria de solapes), y sus USB del costado derecho quedan del lado del hub.
const LAPTOP = { escala: 1.5, cx: 0.0, cy: 0.535, ancho: 0.359, fondo: 0.256, base: 0.0167, tapa: 0.007,
  alto_tapa: 0.236, apertura: 0.35, pantalla: [0.3442, 0.1936] };
const COLOR_TUF = { cuerpo: 0x3a3e44, tapa: 0x33373c, oscuro: 0x15171a, tecla: 0x1b1e22, detalle: 0x8b949e };

// Caja con esquinas redondeadas (vista en planta), extruida hacia arriba: la base, la tapa,
// el touchpad y las teclas dejan de verse como bloques.
function cajaRedonda(sx, sy, sz, r, color, pos, extra = {}) {
  const f = new THREE.Shape();
  const x = -sx / 2, y = -sy / 2;
  f.moveTo(x + r, y); f.lineTo(x + sx - r, y); f.quadraticCurveTo(x + sx, y, x + sx, y + r);
  f.lineTo(x + sx, y + sy - r); f.quadraticCurveTo(x + sx, y + sy, x + sx - r, y + sy);
  f.lineTo(x + r, y + sy); f.quadraticCurveTo(x, y + sy, x, y + sy - r);
  f.lineTo(x, y + r); f.quadraticCurveTo(x, y, x + r, y);
  const bisel = Math.min(sz * 0.25, r * 0.5, 0.0012);
  const g = new THREE.ExtrudeGeometry(f, { depth: Math.max(sz - 2 * bisel, 1e-4), bevelEnabled: bisel > 0,
    bevelThickness: bisel, bevelSize: bisel, bevelSegments: 2, curveSegments: 6 });
  g.rotateX(-Math.PI / 2);            // la extrusion queda hacia arriba (z de la simulacion)
  g.translate(0, bisel, 0);
  const m = new THREE.Mesh(g, color && color.isMaterial ? color : mat(color, extra));
  if (pos) m.position.copy(pos);
  m.castShadow = true;
  return m;
}

// Teclado de la TUF A15 (en mm desde el centro del teclado; x a la derecha, y hacia atras):
// fila de funciones baja, bloque principal de 15 unidades, flechas y numerico de 4 columnas.
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
  // Numerico (mas angosto, como en la A15).
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

function construirLaptop() {
  const L = LAPTOP, C = COLOR_TUF, mm = 0.001;
  const pc = new THREE.Group();
  const metal = { metalness: 0.45, roughness: 0.45 };
  // Base: casco inferior oscuro + cubierta superior gris con esquinas redondeadas; patas de goma.
  pc.add(cajaRedonda(L.ancho, L.fondo, 0.005, 0.012, C.oscuro, Vxyz(0, 0, 0)));
  pc.add(cajaRedonda(L.ancho - 0.001, L.fondo - 0.001, L.base - 0.004, 0.011, C.cuerpo, Vxyz(0, 0, 0.004), metal));
  for (const [x, y] of [[-0.15, -0.1], [0.15, -0.1], [-0.15, 0.1], [0.15, 0.1]])
    pc.add(cajaRedonda(0.05, 0.008, 0.002, 0.003, C.oscuro, Vxyz(x, y, -0.0015)));
  // Rejilla trasera (salida del aire caliente) y lateral.
  for (let i = 0; i < 26; i++) pc.add(caja(0.0035, 0.0012, 0.008, C.oscuro, Vxyz(-0.14 + i * 0.0112, L.fondo / 2 + 0.0002, 0.009)));
  for (let i = 0; i < 12; i++) pc.add(caja(0.0012, 0.0035, 0.006, C.oscuro, Vxyz(-L.ancho / 2 - 0.0002, 0.03 + i * 0.007, 0.009)));
  // Placa del teclado hundida + teclas en relieve (una malla por fila de teclas repetidas).
  const zTec = L.base + 0.0002;
  pc.add(caja(0.33, 0.112, 0.0006, C.oscuro, Vxyz(0, 0.052, zTec - 0.0004)));
  const teclas = teclasTuf();
  const kc = new THREE.Vector2(0, 0.052);   // centro del teclado en la base
  for (const k of teclas) {
    const esWasd = WASD.has(k.txt);
    const tec = cajaRedonda(k.w * mm, k.h * mm, 0.0014, 0.0012, esWasd ? 0x9fb3c8 : C.tecla,
      Vxyz(kc.x + k.x * mm, kc.y + k.y * mm, zTec), esWasd ? { transparent: true, opacity: 0.8, roughness: 0.2 } : { roughness: 0.7 });
    pc.add(tec);
  }
  // Letras de las teclas: un lienzo encima de las teclas. Es tambien el mapa de luz del
  // teclado RGB (emissiveMap): cuando el modelo local piensa, la luz cambia de color.
  const lz = document.createElement('canvas');
  lz.width = 2048; lz.height = 704;
  const cx = lz.getContext('2d');
  const W = 0.36, H = 0.124;                  // metros que cubre el lienzo
  const px = (x) => (x * mm + W / 2) / W * lz.width, py = (y) => (H / 2 - y * mm) / H * lz.height;
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
  const letras = new THREE.Mesh(new THREE.PlaneGeometry(W, H), matLetras);
  letras.rotation.x = -Math.PI / 2;
  letras.position.copy(Vxyz(0, 0.052, zTec + 0.0016));
  pc.add(letras);
  // Touchpad, reposamanos con franja y luces de estado (la de "actividad" parpadea al pensar).
  pc.add(cajaRedonda(0.11, 0.07, 0.0006, 0.006, 0x2d3137, Vxyz(-0.042, -0.078, L.base), { roughness: 0.3 }));
  pc.add(caja(0.3, 0.0008, 0.0003, 0x6e7681, Vxyz(0, -0.115, L.base + 0.0002)));
  const leds = [0x3fb68b, 0x3fb68b, 0xf2b134].map((c, i) => {
    const l = new THREE.Mesh(new THREE.CylinderGeometry(0.0012, 0.0012, 0.0005, 10),
      new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: i < 2 ? 0.8 : 0.1 }));
    l.position.copy(Vxyz(-0.155 + i * 0.006, -L.fondo / 2 + 0.006, L.base + 0.0002));
    pc.add(l);
    return l;
  });
  // Puertos. Izquierda: DC, RJ45, HDMI, USB-C, USB-A, audio. Derecha: 2 USB-A (a estos llegan
  // los cables de las webcams y del ESP32 por el hub).
  // Un puerto: boca negra hundida en el costado y, adentro, la lengueta (azul en los USB 3.0).
  const puerto = (x, y, z, sx, sy, sz, c) => {
    pc.add(caja(sx + 0.0012, sy + 0.0012, sz + 0.0012, 0x050506, Vxyz(x, y, z)));
    if (c !== 0x1d2129) pc.add(caja(sx + 0.0014, sy * 0.72, sz * 0.32, c, Vxyz(x, y, z + sz * 0.12)));
  };
  const xi = -L.ancho / 2 - 0.0003, xd = L.ancho / 2 + 0.0003;
  [[0.075, 0.006, 0.006, 'cil'], [0.05, 0.016, 0.012, 0x1d2129], [0.028, 0.015, 0.006, 0x1d2129],
    [0.012, 0.009, 0.0035, 0x1d2129], [-0.006, 0.013, 0.005, 0x2d6fd0], [-0.03, 0.006, 0.006, 'cil']].forEach(([y, a, h, c]) => {
    if (c === 'cil') {
      const d = new THREE.Mesh(new THREE.CylinderGeometry(a / 2, a / 2, 0.003, 16), mat(0x0b0c0e));
      d.rotation.z = Math.PI / 2;
      d.position.copy(Vxyz(xi, y, 0.009));
      pc.add(d);
    } else puerto(xi, y, 0.009, 0.0012, a, h, c);
  });
  const usbDerecha = [[-0.02, 0.013], [0.0, 0.013]];
  for (const [y, a] of usbDerecha) puerto(xd, y, 0.009, 0.0012, a, 0.005, 0x2d6fd0);
  // Bisagras.
  const yBis = L.fondo / 2 - 0.006, zBis = L.base + 0.003;
  for (const x of [-0.13, 0.13]) {
    const b = new THREE.Mesh(new THREE.CylinderGeometry(0.0045, 0.0045, 0.05, 16), mat(C.oscuro, metal));
    b.rotation.z = Math.PI / 2;
    b.position.copy(Vxyz(x, yBis, zBis));
    pc.add(b);
  }
  // Tapa: gira sobre la bisagra. Por fuera, aluminio con el logo; por dentro, el marco negro
  // delgado, la camara y la pantalla.
  const tapa = new THREE.Group();
  tapa.position.copy(Vxyz(0, yBis, zBis));
  tapa.rotation.x = -L.apertura;
  const cara = cajaRedonda(L.ancho, L.alto_tapa, L.tapa, 0.01, C.tapa, null, metal);
  cara.rotation.x = Math.PI / 2;                       // de horizontal a vertical
  cara.position.copy(Vxyz(0, L.tapa, L.alto_tapa / 2));
  tapa.add(cara);
  const marco = new THREE.Mesh(new THREE.PlaneGeometry(L.ancho - 0.004, L.alto_tapa - 0.004), mat(0x07080a, { roughness: 0.2 }));
  marco.position.copy(Vxyz(0, -0.0004, L.alto_tapa / 2));
  tapa.add(marco);
  const cam = new THREE.Mesh(new THREE.CircleGeometry(0.0015, 16), mat(0x1f3a5f, { metalness: 0.8, roughness: 0.1 }));
  cam.position.copy(Vxyz(0, -0.0006, L.alto_tapa - 0.006));
  tapa.add(cam);
  // Logo TUF por fuera (lienzo).
  const lg = document.createElement('canvas');
  lg.width = 512; lg.height = 256;
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
  logo.position.copy(Vxyz(0, L.tapa + 0.0015, L.alto_tapa * 0.55));
  logo.rotation.y = Math.PI;
  tapa.add(logo);
  // Pantalla: el asistente (lienzo 1920 x 1080, la misma proporcion que el panel real).
  const lienzo = document.createElement('canvas');
  lienzo.width = 1920; lienzo.height = 1080;
  const textura = new THREE.CanvasTexture(lienzo);
  textura.colorSpace = THREE.SRGBColorSpace;
  textura.anisotropy = 8;
  const pantalla = new THREE.Mesh(new THREE.PlaneGeometry(...L.pantalla), new THREE.MeshBasicMaterial({ map: textura }));
  pantalla.position.copy(Vxyz(0, -0.0008, 0.018 + L.pantalla[1] / 2));
  pantalla.userData.asistente = true;
  tapa.add(pantalla);
  // "TUF GAMING" en el marco de abajo.
  const eb = document.createElement('canvas');
  eb.width = 512; eb.height = 64;
  const g3 = eb.getContext('2d');
  g3.fillStyle = '#6e7681'; g3.font = '700 40px "Space Grotesk", sans-serif'; g3.textAlign = 'center'; g3.textBaseline = 'middle';
  g3.fillText('TUF GAMING', 256, 34);
  const texEb = new THREE.CanvasTexture(eb);
  const rot = new THREE.Mesh(new THREE.PlaneGeometry(0.05, 0.00625), new THREE.MeshBasicMaterial({ map: texEb, transparent: true }));
  rot.position.copy(Vxyz(0, -0.0008, 0.0085));
  tapa.add(rot);
  pc.add(tapa);

  pc.scale.setScalar(L.escala);
  pc.position.copy(Vxyz(L.cx, L.cy, 0.0015 * L.escala));   // apoyada en sus patas
  escena.add(pc);
  pc.updateMatrixWorld(true);
  const meshes = [];
  pc.traverse((m) => { if (m.isMesh) meshes.push(m); });
  registrar('pc', ...meshes);
  // Pines de los USB de la derecha, en coordenadas del mundo (el portatil esta ampliado).
  usbDerecha.forEach(([y], i) => {
    const w = pc.localToWorld(Vxyz(xd + 0.0006, y, 0.009));
    pinSuelto(`pc.USB${i + 1}`, escena, w, new THREE.Vector3(1, 0, 0), 'usb');
  });
  const etPc = etiqueta('Portátil ASUS TUF Gaming A15 · dibujado ×1,5 para leer la pantalla', { alto: 0.012, alcance: 1.2 });
  escena.add(etPc);
  const puntaTapa = new THREE.Vector3();
  cam.getWorldPosition(puntaTapa);
  // Sobre el borde de arriba de la tapa, a la izquierda (adelante o al costado quedaba
  // encima de la planta en las vistas "Planta" y "Todo").
  etPc.position.copy(puntaTapa).add(new THREE.Vector3(-0.22, 0.05, 0));
  P.laptop = { grupo: pc, pantalla, lienzo, textura, matLetras, leds, puntaTapa };
}

// Fase 7: el asistente vive en el portatil. Con DeepSeek la pregunta viaja por el Wi-Fi a la
// API (la nube); con el modelo local piensa el mismo portatil (teclado RGB y luz de actividad).
function construirEnlaceAsistente() {
  const grupo = new THREE.Group();
  const L = P.laptop;
  // Nube CENTRADA sobre el portatil (misma x), por encima del borde de la tapa.
  const a = L.puntaTapa.clone().add(new THREE.Vector3(0, 0.02, 0));
  const centro = new THREE.Vector3(a.x, a.y + 0.2, a.z);
  const matNube = new THREE.MeshStandardMaterial({ color: 0xdfe7f5, roughness: 0.9, emissive: 0x539bf5, emissiveIntensity: 0.12 });
  for (const [dx, dy, dz, r] of [[0, 0, 0, 0.055], [-0.062, -0.012, 0.006, 0.042], [0.062, -0.012, -0.006, 0.042],
    [-0.03, 0.03, -0.01, 0.04], [0.03, 0.03, 0.01, 0.04], [0, -0.02, 0.03, 0.035], [0, -0.02, -0.03, 0.035]]) {
    const b = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 14), matNube);
    b.position.copy(centro).add(new THREE.Vector3(dx, dy, dz));
    b.userData.asistente = true;
    grupo.add(b);
  }
  const b = centro.clone().add(new THREE.Vector3(0, -0.05, 0));
  const geo = new THREE.BufferGeometry().setFromPoints([a, b]);
  const linea = new THREE.Line(geo, new THREE.LineDashedMaterial({ color: 0x539bf5, dashSize: 0.012, gapSize: 0.008 }));
  linea.computeLineDistances();
  grupo.add(linea);
  const paquete = new THREE.Mesh(new THREE.SphereGeometry(0.009, 12, 10), new THREE.MeshBasicMaterial({ color: COLOR.ambar }));
  paquete.visible = false;
  grupo.add(paquete);
  const et = etiqueta('☁ API de DeepSeek (internet)', { alto: 0.014, alcance: 1.8, borde: '#539bf5' });
  et.position.copy(centro).add(new THREE.Vector3(0, 0.085, 0));
  grupo.add(et);
  const etW = etiqueta('Wi-Fi del portátil (el carro usa ESP-NOW)', { alto: 0.009, alcance: 1.0, color: '#8b949e' });
  etW.position.copy(a.clone().lerp(b, 0.5)).add(new THREE.Vector3(0.1, 0, 0));
  grupo.add(etW);
  escena.add(grupo);
  P.asistente = { grupo, paquete, a, b, matNube, mensajes: -1, panel: L.pantalla, lienzo: L.lienzo,
    textura: L.textura, pensando: null, fase: 0 };
  dibujarPanelAsistente(null);
}

function envolver(ctx, texto, ancho) {
  const lineas = [];
  for (const parrafo of String(texto).split('\n')) {
    let linea = '';
    for (const palabra of parrafo.split(' ')) {
      const prueba = linea ? `${linea} ${palabra}` : palabra;
      if (ctx.measureText(prueba).width > ancho && linea) { lineas.push(linea); linea = palabra; } else linea = prueba;
    }
    lineas.push(linea);
  }
  return lineas;
}

const QUIEN = { deepseek: 'DeepSeek (internet)', ollama: 'modelo local qwen2.5 (este portátil)' };

// La pantalla de la laptop: barra de ventana, la pregunta, la respuesta con la letra MAS GRANDE
// que quepa entera, y abajo quien respondio. Mientras piensa: la pregunta y un indicador animado.
function dibujarPanelAsistente(d) {
  const A = P.asistente;
  if (!A) return;
  const ctx = A.lienzo.getContext('2d');
  const W = A.lienzo.width, H = A.lienzo.height, m = 70;
  ctx.fillStyle = '#0d1117'; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = '#161b22'; ctx.fillRect(0, 0, W, 96);
  ctx.fillStyle = '#e6e8eb'; ctx.font = '700 46px "Space Grotesk", sans-serif'; ctx.textBaseline = 'middle';
  ctx.fillText('💬 Asistente del proyecto', m, 50);
  ctx.fillStyle = '#8b949e'; ctx.font = '500 30px "IBM Plex Mono", monospace'; ctx.textAlign = 'right';
  ctx.fillText('solo lectura · se le escribe o habla desde el dashboard', W - m, 50);
  ctx.textAlign = 'left';
  const msgs = (d && d.mensajes) || [];
  const pens = d && d.pensando;
  let pregunta = null, respuesta = null;
  for (let k = msgs.length - 1; k >= 0; k--) {
    if (!respuesta && msgs[k].rol === 'asistente') respuesta = msgs[k];
    else if (respuesta && msgs[k].rol === 'usuario') { pregunta = msgs[k]; break; }
  }
  let y = 150;
  const bloquePregunta = (texto) => {
    ctx.font = '600 44px "Space Grotesk", sans-serif'; ctx.fillStyle = '#f2b134'; ctx.textBaseline = 'top';
    for (const l of envolver(ctx, `🧑 ${texto}`, W - 2 * m).slice(0, 2)) { ctx.fillText(l, m, y); y += 56; }
    y += 24;
  };
  if (pens) {
    bloquePregunta(pens.pregunta || '');
    const local = pens.proveedor === 'ollama';
    ctx.font = '600 56px "Space Grotesk", sans-serif'; ctx.fillStyle = local ? '#b083f0' : '#539bf5';
    const puntos = '.'.repeat(1 + (A.fase % 3));
    ctx.fillText((local ? 'Pensando en este portátil (qwen2.5, sin internet)' : 'Consultando a DeepSeek por internet') + puntos, m, y + 60);
    // Barra que va y viene.
    const u = (Math.sin(A.fase * 0.5) + 1) / 2;
    ctx.fillStyle = '#21262d'; ctx.fillRect(m, y + 170, W - 2 * m, 16);
    ctx.fillStyle = local ? '#b083f0' : '#539bf5'; ctx.fillRect(m + u * (W - 2 * m - 300), y + 170, 300, 16);
  } else if (!respuesta) {
    ctx.font = '500 52px "Space Grotesk", sans-serif'; ctx.fillStyle = '#8b949e'; ctx.textBaseline = 'top';
    ctx.fillText(MODO_DEMO ? 'Demo grabada: sin conversación.' : 'Todavía nadie le ha preguntado nada.', m, y);
  } else {
    if (pregunta) bloquePregunta(pregunta.texto);
    // Respuesta: la letra mas grande (de 64 a 30 px) con la que cabe entera.
    const alto = H - y - 120;
    let tam = 64, lineas;
    for (; tam >= 30; tam -= 2) {
      ctx.font = `500 ${tam}px "Space Grotesk", sans-serif`;
      lineas = envolver(ctx, respuesta.texto, W - 2 * m);
      if (lineas.length * tam * 1.3 <= alto) break;
    }
    ctx.fillStyle = '#e6e8eb'; ctx.textBaseline = 'top';
    const caben = Math.floor(alto / (tam * 1.3));
    for (const l of lineas.slice(0, caben)) { ctx.fillText(l, m, y); y += tam * 1.3; }
    if (lineas.length > caben) { ctx.fillStyle = '#8b949e'; ctx.fillText('… (completa en el dashboard)', m, y); }
    ctx.fillStyle = '#161b22'; ctx.fillRect(0, H - 86, W, 86);
    ctx.font = '500 32px "IBM Plex Mono", monospace'; ctx.textBaseline = 'middle';
    ctx.fillStyle = QUIEN[respuesta.modo] ? '#3fb68b' : '#f2b134';
    const ordenes = (respuesta.acciones || []).map((o) => o.accion || o.cmd).join(', ');
    ctx.fillText(`${respuesta.ts.slice(11, 19)} · respondió: ${QUIEN[respuesta.modo] || 'intérprete de reglas'}`
      + (ordenes ? ` · órdenes: ${ordenes}` : ''), m, H - 43);
  }
  A.textura.needsUpdate = true;
}

// Mientras alguien piensa (lo dice /api/asistente): con DeepSeek el paquete va y viene por la
// linea a la nube; con el modelo local la nube se queda quieta y el que "piensa" es el
// portatil: teclado RGB que cambia de color, luz de actividad parpadeando y la pantalla animada.
function animarAsistente(dt) {
  const A = P.asistente, L = P.laptop;
  if (!A || !L) return;
  const pens = asistenteDatos && asistenteDatos.pensando;
  A.t = (A.t || 0) + dt;
  if (pens && A.t > 0.25) { A.t = 0; A.fase++; dibujarPanelAsistente(asistenteDatos); }
  const local = pens && pens.proveedor === 'ollama';
  const nube = pens && pens.proveedor === 'deepseek';
  const s = performance.now() / 1000;
  if (local) {
    L.matLetras.emissive.setHSL((s * 0.25) % 1, 0.9, 0.55);
    L.matLetras.emissiveIntensity = 0.9;
    L.leds[2].material.emissiveIntensity = (Math.sin(s * 12) > 0) ? 1.2 : 0.05;
  } else {
    L.matLetras.emissive.setHex(0xffffff);
    L.matLetras.emissiveIntensity = 0.55;
    L.leds[2].material.emissiveIntensity = 0.1;
  }
  if (nube) {
    const u = (s * 0.8) % 1;
    A.paquete.visible = true;
    A.paquete.position.copy(A.a).lerp(A.b, suave(u));
    A.matNube.emissiveIntensity = 0.25 + 0.25 * Math.sin(s * 6);
  } else if (!A.animandoRespuesta) {
    A.paquete.visible = false;
    A.matNube.emissiveIntensity = 0.12;
  }
}

// Llego la respuesta de DeepSeek: el paquete baja de la nube a la laptop.
function pulsoAsistente() {
  const A = P.asistente;
  if (!A) return;
  cancelar(A);
  A.animandoRespuesta = true;
  A.paquete.visible = true;
  animar(0.5, (u) => { A.matNube.emissiveIntensity = 0.12 + 0.6 * Math.sin(Math.PI * u); }, { dueno: A });
  animar(0.7, (u) => A.paquete.position.copy(A.b).lerp(A.a, suave(u)), { dueno: A, retraso: 0.3,
    fin: () => { A.paquete.visible = false; A.animandoRespuesta = false; } });
}

// Donde cree el carro que esta (odometria) y a donde se le pidio ir.
function marcasOrdenCarro(c) {
  if (!P.odoAnillo) {
    P.odoAnillo = new THREE.Mesh(new THREE.RingGeometry(0.05, 0.062, 40),
      new THREE.MeshBasicMaterial({ color: COLOR.azul, transparent: true, opacity: 0.85, side: THREE.DoubleSide }));
    P.odoAnillo.rotation.x = -Math.PI / 2;
    const et = etiqueta('donde cree que está (odometría)', { alto: 0.008, alcance: 1.0, color: '#539bf5' });
    et.position.set(0, 0, 0.04);
    P.odoAnillo.add(et);
    escena.add(P.odoAnillo);
    P.objetivo = new THREE.Group();
    P.objetivo.add(cilindro(0.004, 0.09, COLOR.ambar, new THREE.Vector3(0, 0.045, 0)));
    const disco = new THREE.Mesh(new THREE.RingGeometry(0.018, 0.03, 32),
      new THREE.MeshBasicMaterial({ color: COLOR.ambar, side: THREE.DoubleSide }));
    disco.rotation.x = -Math.PI / 2;
    disco.position.y = 0.002;
    P.objetivo.add(disco);
    const etO = etiqueta('punto pedido', { alto: 0.008, alcance: 1.0, color: '#f2b134' });
    etO.position.set(0, 0.11, 0);
    P.objetivo.add(etO);
    escena.add(P.objetivo);
  }
  const o = c && c.odometria;
  P.odoAnillo.visible = !!o;
  if (o) P.odoAnillo.position.copy(Vxyz(o[0], o[1], 0.004));
  const u = c && c.ultima_orden;
  P.objetivo.visible = !!(u && u.accion === 'ir_a' && c.estado === 'manual');
  if (P.objetivo.visible) P.objetivo.position.copy(Vxyz(u.x, u.y, 0));
}

// Camino de un hilo dentro de la caja: sale de su pin, entra a la canaleta
// mas cercana, va por la red de canaletas (el camino mas corto) y sale junto
// al otro pin. Cada hilo tiene su lugar dentro de la canaleta (`k`: al lado
// y en capas), asi que no se enciman. `a`, `b` en coordenadas de Three.
function rutaCaja(a, b, k = 0) {
  const { bx, by, DUCTOS: D } = P.caja;
  const S = (v) => [v.x - bx, -v.z - by, v.y];
  const segs = D.segmentos;
  const proyectar = ([x, y]) => {
    let mejor = null;
    segs.forEach(([p, q], i) => {
      const [dx, dy] = [q[0] - p[0], q[1] - p[1]];
      const L2 = dx * dx + dy * dy;
      const t = Math.max(0, Math.min(1, ((x - p[0]) * dx + (y - p[1]) * dy) / L2));
      const pt = [p[0] + t * dx, p[1] + t * dy];
      const d = Math.hypot(pt[0] - x, pt[1] - y);
      if (!mejor || d < mejor.d) mejor = { d, pt, i, t };
    });
    return mejor;
  };
  const pa = S(a), pb = S(b);
  const ea = proyectar(pa), eb = proyectar(pb);
  // Grafo: extremos de los segmentos + los dos puntos de entrada.
  const nodos = [];
  const id = (pt) => {
    let i = nodos.findIndex((n) => Math.hypot(n[0] - pt[0], n[1] - pt[1]) < 1e-6);
    if (i < 0) { nodos.push(pt); i = nodos.length - 1; }
    return i;
  };
  const ia = id(ea.pt), ib = id(eb.pt);
  const aristas = new Map();
  const unir = (i, j) => {
    const d = Math.hypot(nodos[i][0] - nodos[j][0], nodos[i][1] - nodos[j][1]);
    (aristas.get(i) || aristas.set(i, []).get(i)).push([j, d]);
    (aristas.get(j) || aristas.set(j, []).get(j)).push([i, d]);
  };
  segs.forEach(([p, q]) => { id(p); id(q); });
  segs.forEach(([p, q], s) => {
    // Nodos que caen sobre este segmento, en orden.
    const [dx, dy] = [q[0] - p[0], q[1] - p[1]];
    const L2 = dx * dx + dy * dy;
    const sobre = [id(p), id(q)];
    nodos.forEach((n, i) => {
      const t = ((n[0] - p[0]) * dx + (n[1] - p[1]) * dy) / L2;
      const pt = [p[0] + t * dx, p[1] + t * dy];
      if (t > 1e-6 && t < 1 - 1e-6 && Math.hypot(pt[0] - n[0], pt[1] - n[1]) < 1e-6) sobre.push(i);
    });
    const tt = (i) => ((nodos[i][0] - p[0]) * dx + (nodos[i][1] - p[1]) * dy) / L2;
    const orden = [...new Set(sobre)].sort((i, j) => tt(i) - tt(j));
    for (let n = 0; n + 1 < orden.length; n++) unir(orden[n], orden[n + 1]);
  });
  // Dijkstra.
  const dist = nodos.map(() => Infinity), prev = nodos.map(() => -1), hecho = nodos.map(() => false);
  dist[ia] = 0;
  for (;;) {
    let u = -1;
    dist.forEach((d, i) => { if (!hecho[i] && d < Infinity && (u < 0 || d < dist[u])) u = i; });
    if (u < 0 || u === ib) break;
    hecho[u] = true;
    for (const [v, w] of aristas.get(u) || []) if (dist[u] + w < dist[v]) { dist[v] = dist[u] + w; prev[v] = u; }
  }
  const camino = [];
  for (let v = ib; v >= 0; v = prev[v]) camino.unshift(nodos[v]);
  if (camino[0] !== nodos[ia]) camino.unshift(nodos[ia]);
  // Lugar del hilo en la canaleta: 9 posiciones de lado y 12 capas (108
  // lugares distintos).
  const lat = ((k % 8) - 3.5) * 0.0018;
  const zD = 0.003 + 0.0035 + (Math.floor(k / 8) % 13) * 0.0018;
  const normal = (p, q) => { const L = Math.hypot(q[0] - p[0], q[1] - p[1]) || 1; return [-(q[1] - p[1]) / L, (q[0] - p[0]) / L]; };
  const corrido = camino.map((p, i) => {
    const n1 = i > 0 ? normal(camino[i - 1], p) : null, n2 = i + 1 < camino.length ? normal(p, camino[i + 1]) : null;
    let n = n1 && n2 ? [n1[0] + n2[0], n1[1] + n2[1]] : n1 || n2 || [0, 0];
    const L = Math.hypot(n[0], n[1]) || 1;
    n = [n[0] / L, n[1] / L];
    // En las esquinas, el corrimiento a inglete (si no, los hilos se juntan).
    const coseno = n1 ? Math.max(0.5, n[0] * n1[0] + n[1] * n1[1]) : 1;
    return [p[0] + n[0] * lat / coseno, p[1] + n[1] * lat / coseno];
  });
  const W = ([x, y], z) => Vxyz(bx + x, by + y, z);
  const alto = (z) => Math.max(z, 0.036) + (k % 5) * 0.0012;
  return [W(pa, alto(pa[2])), W(corrido[0], alto(pa[2])), ...corrido.map((p) => W(p, zD)),
    W(corrido[corrido.length - 1], alto(pb[2])), W(pb, alto(pb[2]))];
}

// ---------------------------------------------------------------------------
// cableado: cada hilo de sim/conexiones.py, de su pin al otro
// ---------------------------------------------------------------------------

function construirCables() {
  const grupo = new THREE.Group();
  CAPAS_CABLES.push(grupo);
  escena.updateMatrixWorld(true);   // para los localToWorld de abajo
  const cx = G.conexiones;
  const C = P.caja;
  const S = (v) => [v.x, -v.z, v.y];                       // Three -> simulacion

  // Pines que no son placas: donde sale el cable de cada cosa.
  const servos = { servo_desvio: 'servo_desvio_e7', servo_obturador: 'servo_obturador', servo_tapas: 'servo_tapas',
    servo_prensa: 'motor_prensa', servo_empujador: 'servo_empujador', servo_canaleta: 'servo_compuerta_canaleta' };
  for (const [dev, comp] of Object.entries(servos)) pinSuelto(`${dev}.CABLE`, escena, P.rutasServo[comp][0]);
  for (const id of ['capacitivo', 'inductivo']) {
    for (const c of ['CAFE', 'AZUL', 'NEGRO']) pinSuelto(`${id}.${c}`, escena, SENS[id].rutaCable[0], new THREE.Vector3(0, -1, 0));
  }
  pinSuelto('cam_cenital.USB', escena, SENS.camara.rutaCable[0]);
  pinSuelto('cam_vasos.USB', escena, SENS.camara_vasos.rutaCable[0]);
  const nm = P.nemaMonedas.localToWorld(P.nemaMonedas.userData.conector.clone());
  const nv = P.nemaVasos.localToWorld(P.nemaVasos.userData.conector.clone());
  pinSuelto('motor_monedas.JST', escena, nm, new THREE.Vector3(0, -1, 0), 'jst');
  pinSuelto('motor_vasos.JST', escena, nv, new THREE.Vector3(0, -1, 0), 'jst');
  const [cxa, cya] = G.almacen.centro;
  pinSuelto('motor_carrusel.CABLE', escena, Vxyz(cxa + 0.007, cya, G.almacen.tubo_z_arriba + 0.03));
  const zp = G.cinta_vasos.estaciones[0].posicion[2] + 0.02;
  pinSuelto('panel_luz.+5V', escena, Vxyz(0.295, -0.051, zp + 0.004), new THREE.Vector3(0, 0, -1), 'pad');
  pinSuelto('panel_luz.GND', escena, Vxyz(0.295, -0.051, zp - 0.004), new THREE.Vector3(0, 0, -1), 'pad');
  const anillo = SENS.camara.rutaCable[0].clone().add(new THREE.Vector3(-0.012, -0.026, 0));
  pinSuelto('anillo.+5V', escena, anillo.clone().add(new THREE.Vector3(0, 0, 0.002)), new THREE.Vector3(-1, 0, 0), 'pad');
  pinSuelto('anillo.GND', escena, anillo.clone().add(new THREE.Vector3(0, 0, -0.002)), new THREE.Vector3(-1, 0, 0), 'pad');

  // Cuantos hilos llegan a cada pin (para abrirlos en los conectores).
  for (const c of cx.cables) for (const h of c.hilos) for (const e of [h.de, h.a]) if (PIN[e]) PIN[e].total = (PIN[e].total || 0) + 1;

  // --- Recorridos de los cables de campo: del dispositivo al prensaestopas.
  // Mazo del portico: por el costado -y de la viga, cada cable en su lugar
  // (c = capa hacia afuera, r = fila hacia arriba). Los que llegan desde
  // abajo toman las filas de abajo, y un cable solo pasa por lugares que
  // todavia estan libres en ese punto: los cables del mazo no se cruzan.
  // Al final de la viga baja por la cara +x de la columna derecha y va por
  // el piso a UN prensaestopas grande (G1).
  const xCol = 0.315;
  const yV = (c) => P.portico.y - 0.01 - 0.0025 - c * 0.0042;        // costado -y de la viga
  const zV = (r) => P.portico.z - 0.0005 + r * 0.0042;
  const xC = (r) => xCol + 0.0125 + r * 0.0042;                       // cara +x de la columna
  const yC = (c) => P.portico.y + 0.008 - c * 0.0042;
  const zP = (c) => 0.0066 + (2 - c) * 0.0042;                        // en el piso, apilados
  const G1 = xC(1.5), yG = C.yPared;
  const SLOT = { motor_monedas: [0, 3], vl53_interior: [0, 2], hall: [0, 1], servo_2: [0, 0],
    capacitivo: [1, 2], inductivo: [1, 1], motor_carrusel: [1, 0], presencia: [2, 0],
    // Los que se suman en la columna (desde +y, del lado de afuera del mazo):
    panel_luz: [-1, 0], servo_3: [-1, 1], servo_1: [-1, 2] };
  const bajarColumna = (id, zDesde) => {
    const [c, r] = SLOT[id];
    return [[xC(r), yC(c), zDesde], [xC(r), yC(c), zP(c) + 0.01], [xC(r), yC(c) + 0.012, zP(c)],
      [xC(r), yG - 0.008, zP(c)], [G1 + (r - 1.5) * 0.003, yG + 0.012, 0.014 + (2 - c) * 0.0032]];
  };
  // Por la viga desde x hasta la columna (y el codo hacia la cara +x).
  const porViga = (id, x) => {
    const [c, r] = SLOT[id];
    return [[x, yV(c), zV(r)], [xCol + 0.005, yV(c), zV(r)], [xC(r), yV(c), zV(r) - 0.008],
      [xC(r), yC(c), zV(r) - 0.03], ...bajarColumna(id, zV(r) - 0.03).slice(1)];
  };
  // Subir desde debajo de la viga hasta su lugar en el mazo.
  const subir = (id, x, zDesde) => [[x, yV(SLOT[id][0]), zDesde], ...porViga(id, x)];
  const entrar = (gx, z = 0.0066) => [[gx, yG - 0.008, z], [gx, yG + 0.012, 0.014]];
  const RUTAS = {
    motor_monedas: () => {
      const [x, y, z] = S(nm);
      return [[x, y, z - 0.014], [-0.09, y, z - 0.014], [-0.09, y, 0.37], [-0.09, 0.0, 0.365], ...subir('motor_monedas', -0.09, 0.365)];
    },
    capacitivo: () => { const p0 = S(SENS.capacitivo.rutaCable[0]); return [p0, [p0[0], 0, 0.362], ...subir('capacitivo', p0[0], 0.362)]; },
    inductivo: () => { const p0 = S(SENS.inductivo.rutaCable[0]); return [p0, [p0[0], 0, 0.362], ...subir('inductivo', p0[0], 0.362)]; },
    presencia: () => {
      const r = SENS.presencia.rutaCable.map(S);
      const u = r[r.length - 1];
      return [...r, [u[0], yV(2), u[2]], ...porViga('presencia', u[0])];
    },
    hall: () => { const r = SENS.hall_carrusel.rutaCable.map(S); const u = r[r.length - 1]; return [...r, ...subir('hall', u[0], u[2])]; },
    vl53_interior: () => { const r = SENS.sensor_interior.rutaCable.map(S); const u = r[r.length - 1]; return [...r, ...subir('vl53_interior', u[0], u[2])]; },
    motor_carrusel: () => {
      const x = cxa + 0.007, zTope = G.almacen.tubo_z_arriba + 0.03;
      return [[x, cya, zTope], [x, cya, P.portico.z - 0.014], ...subir('motor_carrusel', x, P.portico.z - 0.014)];
    },
    // Tapas: sube por afuera del tubo, pasa por encima de su boca y sube
    // junto al colgante del tubo hasta la viga.
    servo_2: () => {
      const s0 = S(P.rutasServo.servo_tapas[0]);
      const zTop = G.cinta_vasos.estaciones[0].posicion[2] + G.vaso.altura + 0.013 + 0.075 + 0.008;
      return [s0, [s0[0], s0[1] - 0.013, s0[2]], [0.225, s0[1] - 0.013, s0[2]], [0.225, -0.153, zTop], [0.209, -0.063, zTop],
        [0.209, -0.063, P.portico.z - 0.019], ...subir('servo_2', 0.209, P.portico.z - 0.019).slice(0)];
    },
    // Obturador: hacia +y por encima del marco del panel de luz y, por
    // detras de la columna, se suma al mazo.
    servo_1: () => {
      const r = P.rutasServo.servo_obturador.map(S);
      const z = G.cinta_vasos.estaciones[0].posicion[2] + G.vaso.altura + 0.025 + 0.0085;
      const [c, rr] = SLOT.servo_1;
      return [r[0], r[1], [0.1455, r[1][1], r[1][2]], [0.1455, -0.07, r[1][2]], [0.1455, -0.07, z], [0.1455, -0.049, z],
        [0.30, -0.049, z], [0.30, -0.029, z], [xC(rr), -0.029, z], ...bajarColumna('servo_1', z)];
    },
    servo_3: () => {
      const s0 = S(P.rutasServo.motor_prensa[0]);
      const [, rr] = SLOT.servo_3;
      return [s0, [s0[0] - 0.003, s0[1], s0[2]], [s0[0] - 0.003, -0.013, s0[2]], [xC(rr), -0.013, s0[2]], ...bajarColumna('servo_3', s0[2])];
    },
    panel_luz: () => {
      const [, rr] = SLOT.panel_luz;
      return [[0.29, -0.051, zp], [0.29, -0.029, zp], [xC(rr), -0.029, zp], ...bajarColumna('panel_luz', zp)];
    },
    servo_0: () => {
      const r = P.rutasServo.servo_desvio_e7.map(S);
      const u = r[r.length - 1];
      return [...r, [u[0], u[1], 0.0066], [0.2, u[1], 0.0066], ...entrar(0.2)];
    },
    servo_4: () => {
      const r = P.rutasServo.servo_empujador.map(S);
      const u = r[r.length - 1];
      // Por el lado +y del poste (antes lo atravesaba).
      return [r[0], r[1], [r[1][0], -0.001, r[1][2]], [u[0], -0.001, r[1][2]], [u[0], -0.001, 0.0066], ...entrar(u[0])];
    },
    servo_5: () => {
      const r = P.rutasServo.servo_compuerta_canaleta.map(S);
      const pc = S(P.posteCanaleta);
      const x = pc[0] + 0.0125;
      return [...r, [x, pc[1], r[r.length - 1][2]], [x, pc[1], 0.0066], [x, pc[1] + 0.014, 0.0066], [0.405, pc[1] + 0.014, 0.0066],
        [0.405, -0.03, 0.0066], ...entrar(0.405)];
    },
    motor_vasos: () => {
      const v = S(nv);
      return [[v[0], v[1], v[2] - 0.014], [v[0] - 0.012, v[1], 0.0066], [v[0] - 0.012, -0.024, 0.0066], [0.28, -0.024, 0.0066], ...entrar(0.28)];
    },
    vl53_cortina: () => {
      const r = SENS.cortina.rutaCable.map(S);
      const u = r[r.length - 1];
      // Por la izquierda de la columna derecha (antes la atravesaba).
      return [...r, [u[0], u[1] - 0.004, 0.0066], [0.297, u[1] - 0.004, 0.0066], ...entrar(0.297)];
    },
    anillo: () => {
      const r = SENS.camara.rutaCable.map(S);
      const u = r[r.length - 1];
      const yl = 0.066;
      return [...r.map((p, i) => [p[0] - 0.012, p[1], p[2] - (i === 0 ? 0.026 : 0)]), [u[0] - 0.012, yl, 0.0066],
        [C.xParedIzq - 0.008, yl, 0.0066], [C.xParedIzq - 0.008, yl, 0.02], [C.xParedIzq + 0.012, yl, 0.02]];
    },
    // USB: cada webcam por su carril, sin cruzarse con nada. La de vasos da
    // la vuelta por la izquierda de las mesas (lleva extension USB de 1 m).
    usb_vasos: () => {
      const r = SENS.camara_vasos.rutaCable.map(S);
      const u = r[r.length - 1];
      const p = S(PIN['hub_usb.P1'].tip);
      return [...r, [u[0], u[1] - 0.008, 0.0066], [-0.168, u[1] - 0.008, 0.0066], [-0.168, 0.2775, 0.0066], [p[0], 0.2775, 0.0066], p];
    },
    usb_cenital: () => {
      const r = SENS.camara.rutaCable.map(S);
      const u = r[r.length - 1];
      const p = S(PIN['hub_usb.P2'].tip);
      return [...r, [u[0], 0.2728, 0.0066], [p[0], 0.2728, 0.0066], p];
    },
    usb_esp: () => {
      const pe = S(PIN['esp32_fijo.USB'].tip), y = pe[1];
      const p = S(PIN['hub_usb.P3'].tip);
      const x = C.xParedIzq - 0.0045;
      return [pe, [x, y, pe[2]], [x, y, 0.0066], [x, 0.2685, 0.0066], [p[0], 0.2685, 0.0066], p];
    },
    usb_pc: () => {
      // Por el piso, paralelo al costado derecho de la laptop, y entra derecho al puerto.
      const h = S(PIN['hub_usb.UP'].tip), p = S(PIN['pc.USB1'].tip);
      const xc = Math.max(h[0], p[0]) + 0.03;
      return [h, [h[0], h[1], 0.006], [xc, h[1], 0.006], [xc, p[1], 0.006], [p[0] + 0.012, p[1], p[2]], p];
    },
    red: () => [[0.75, C.by + 0.02, 0.0066], [C.xParedDer + 0.02, C.by + 0.02, 0.0066], [C.xParedDer + 0.02, C.by + 0.02, 0.02],
      [C.xParedDer - 0.004, C.by + 0.02, 0.02]],
  };

  const zonaDe = (ref) => cx.dispositivos[ref.split('.', 1)[0]].zona;
  const lead = (ref) => PIN[ref].tip.clone().addScaledVector(PIN[ref].dir, 0.006);
  let k = 0;
  for (const c of cx.cables) {
    if (c.tipo === 'carro') continue;
    const nombreTipo = c.tipo;
    if (c.tipo === 'interno' || c.tipo === 'dupont') {
      // Dentro de la caja: cada hilo de su pin al otro por las canaletas.
      for (const h of c.hilos) {
        hilo(h.de, h.a, h.color, rutaCaja(lead(h.de), lead(h.a), k++), grupo,
          { r: c.tipo === 'interno' ? 0.0008 : 0.00055, nombre: `${c.nombre}: ${h.funcion}`, tipo: nombreTipo });
      }
      continue;
    }
    const pts = RUTAS[c.id] ? RUTAS[c.id]() : null;
    if (!pts) { console.warn('cable sin recorrido', c.id); continue; }
    if (c.tipo === 'usb' || c.tipo === 'red') {
      funda(c.nombre, c.tipo, pts, grupo, 'mesa');
      continue;
    }
    // Funda por la estructura; en cada punta, los hilos a sus pines.
    funda(c.nombre, c.tipo, pts, grupo);
    const inicio = aThree(pts[0]), fin = aThree(pts[pts.length - 1]);
    for (const h of c.hilos) {
      const [dev, caja_] = zonaDe(h.de) === 'planta' ? [h.de, h.a] : [h.a, h.de];
      const Pd = PIN[dev];
      if (Pd && !['cable', 'jst'].includes(Pd.tipo)) {
        // Del pin del sensor al comienzo de la funda (con su carcasa).
        hilo(dev, inicio, h.color, [], grupo);
      }
      hilo(fin, caja_, h.color, rutaCaja(fin, lead(caja_), k++), grupo);
    }
  }
  construirCablesCarro();
  cerrarLotes();
  grupo.visible = false;
  escena.add(grupo);
}

// Boton "Cables": los muestra u oculta por completo, con su leyenda (tipo,
// cantidad y largo de cada cable, con 20 % de holgura para amarras y curvas).
function mostrarCables(si) {
  for (const g of CAPAS_CABLES) g.visible = si;
  const b = document.getElementById('btnCables');
  if (b) b.classList.toggle('activo', si);
  const ley = document.getElementById('leyendaCables');
  if (!ley) return;
  ley.style.display = si ? 'block' : 'none';
  if (!si || ley.dataset.hecha) return;
  ley.dataset.hecha = '1';
  const cx = G.conexiones;
  const hex = (n) => '#' + n.toString(16).padStart(6, '0');
  const m = (x) => (x * 1.2).toFixed(2).replace('.', ',');
  const campo = CABLES.filter((c) => c.zona === 'planta' || c.zona === 'mesa');
  const total = campo.reduce((s, c) => s + c.largo, 0);
  const hilos = cx.cables.reduce((s, c) => s + c.hilos.length, 0);
  let html = `<div class="ley-titulo">Conexiones · ${cx.cables.length} cables · ${hilos} hilos · campo ${m(total)} m ` +
    '<span class="tenue">(+20 %; tabla completa en docs/conexiones.md)</span></div>';
  const porTipo = {};
  for (const c of campo) (porTipo[c.tipo] ||= []).push(c);
  for (const [tipo, lista] of Object.entries(porTipo)) {
    const t = TIPOS_CABLE[tipo];
    html += `<details><summary><span class="muestra" style="background:${hex(t.color)}"></span>${esc(t.nombre)} · ${lista.length}</summary>`;
    html += lista.map((c) => `<div class="ley-fila">${esc(c.nombre)}<span>${m(c.largo)} m</span></div>`).join('');
    html += '</details>';
  }
  const nombre = (ref) => `${esc(cx.dispositivos[ref.split('.', 1)[0]].nombre.split(' (')[0])} <b>${esc(ref.split('.', 1)[1])}</b>`;
  html += '<details><summary>Pin a pin</summary>';
  for (const c of cx.cables) {
    if (!c.hilos.length) continue;
    html += `<div class="ley-cable">${esc(c.nombre)}</div>`;
    html += c.hilos.map((h) => `<div class="ley-hilo"><span class="muestra" style="background:${h.color}"></span>` +
      `${nombre(h.de)} → ${nombre(h.a)} <span class="tenue">${esc(h.funcion)}</span></div>`).join('');
  }
  html += '</details>';
  ley.innerHTML = html;
}

// Cableado del carro: cada hilo de su pin al otro. Lo de abajo de la placa
// sube por un agujero junto a su modulo; lo que esta entre los dos pisos sale
// por el borde del segundo piso y sube. Van dentro del grupo del carro (se
// mueven con el).
function construirCablesCarro() {
  const D = P.carroDims;
  const cc = new THREE.Group();
  CAPAS_CABLES.push(cc);
  P.carro.add(cc);
  const nivel = (p) => (p.y > D.zPiso2 + 0.002 ? 2 : p.y > D.zPlaca ? 1 : 0);   // en Three, y es la altura
  const zAgujero = D.zPlaca + 0.006;
  // Punto (x, y de la simulacion) justo afuera del borde del segundo piso.
  const borde = (p) => {
    const [x0, x1, yb] = [D.piso2.x0, D.piso2.x1, D.piso2.y];
    const ys = -p.z;
    const lim = (v, a, b) => Math.max(a, Math.min(b, v));
    const opciones = [[x1 + 0.004, lim(ys, -yb, yb)], [x0 - 0.004, lim(ys, -yb, yb)],
      [lim(p.x, x0, x1), yb + 0.004], [lim(p.x, x0, x1), -yb - 0.004]];
    return opciones.sort((a, b) => Math.hypot(a[0] - p.x, a[1] - ys) - Math.hypot(b[0] - p.x, b[1] - ys))[0];
  };
  // Por debajo de la placa hasta un agujero en el frente (x = 82 mm, a
  // 46 mm del centro) y arriba por el.
  const zBajo = D.zPlaca - 0.0045;
  const porAbajo = (p, k) => {
    const lado = -p.z >= 0 ? 1 : -1;
    const [ox, oy] = [((k % 4) - 1.5) * 0.002, (Math.floor(k / 4) % 4 - 1.5) * 0.002];
    const z = zBajo - (k % 2) * 0.0012;
    const pts = [new THREE.Vector3(p.x, z, p.z)];
    if (p.x < 0.02) pts.push(Vxyz(0.03 + ox, lado * 0.029 + oy, z));
    pts.push(Vxyz(0.082 + ox, lado * 0.046 + oy, z), Vxyz(0.082 + ox, lado * 0.046 + oy, zAgujero));
    return pts;
  };
  // Entre dos puntos a la misma altura que difieren en x y en y, un codo:
  // primero a lo largo del carro (x) y despues a lo ancho.
  const rectos = (pts) => {
    const out = [pts[0]];
    for (let i = 1; i < pts.length; i++) {
      const p = out[out.length - 1], q = pts[i];
      if (Math.abs(q.x - p.x) > 0.0015 && Math.abs(q.z - p.z) > 0.0015) {
        if (Math.abs(q.y - p.y) < 0.002) out.push(new THREE.Vector3(q.x, p.y, p.z));
        else out.push(new THREE.Vector3(p.x, q.y, p.z), new THREE.Vector3(q.x, q.y, p.z));
      }
      out.push(q);
    }
    return out;
  };
  const ruta = (a, b, k) => {
    const a0 = a.clone(), b0 = b.clone();
    let ini = [], fin = [];
    if (nivel(a) === 0) { ini = porAbajo(a, k); a = ini[ini.length - 1].clone(); }
    if (nivel(b) === 0) { fin = porAbajo(b, k); b = fin[fin.length - 1].clone(); }
    const na = nivel(a), nb = nivel(b);
    const medio = [];
    if (na === 2 && nb === 2) {
      const z = Math.max(a.y, b.y) + 0.004 + (k % 3) * 0.001;
      medio.push(new THREE.Vector3(a.x, z, a.z), new THREE.Vector3(b.x, z, b.z));
    } else if (na === 1 && nb === 1) {
      const z = Math.min(Math.max(a.y, b.y) + 0.004, D.zPiso2 - 0.004);
      medio.push(new THREE.Vector3(a.x, z, a.z), new THREE.Vector3(b.x, z, b.z));
    } else {
      const [bajo, alto] = na === 1 ? [a, b] : [b, a];
      const [ex, ey] = borde(bajo);
      const zb = Math.min(bajo.y, D.zPiso2 - 0.004);
      const zs = Math.max(alto.y + 0.004, D.zPiso2 + 0.012) + (k % 3) * 0.001;
      const tramo = [Vxyz(ex, ey, zb), Vxyz(ex, ey, zs), new THREE.Vector3(alto.x, zs, alto.z)];
      medio.push(...(na === 1 ? tramo : tramo.reverse()));
    }
    // Hilos del mismo mazo lado a lado (no encimados).
    const o = new THREE.Vector3(((k % 3) - 1) * 0.0012, 0, ((Math.floor(k / 3) % 3) - 1) * 0.0012);
    return rectos([a0, ...ini, ...medio.map((p) => p.add(o)), ...fin.reverse(), b0]).slice(1, -1);
  };
  const lead = (ref) => PIN[ref].tip.clone().addScaledVector(PIN[ref].dir, 0.006);
  let k = 0;
  for (const c of G.conexiones.cables) {
    if (c.tipo !== 'carro') continue;
    for (const h of c.hilos) {
      const par = /motor [AB]/.test(h.funcion);
      hilo(h.de, h.a, h.color, ruta(lead(h.de), lead(h.a), k++), cc,
        { r: par ? 0.0007 : 0.0005, nombre: `${c.nombre}: ${h.funcion}`, tipo: 'carro', zona: 'carro' });
    }
  }
  cc.visible = false;
}

// ---------------------------------------------------------------------------
// sensores de la planta (rayos, cabezas de proximidad, camaras)
// ---------------------------------------------------------------------------

const SENS = {};   // id -> {objetos, marcador, activo}
P.rutasServo = {};

// Webcam con su soporte: poste al piso (o a la mesa) y brazo hasta la camara.
function camaraConSoporte(pos, mira, { anillo = false, basePoste }) {
  const objs = [];
  const cuerpo = new THREE.Group();
  cuerpo.add(caja(0.03, 0.022, 0.022, 0x20242b, Vxyz(0, 0, 0)));
  const lente = cilindro(0.008, 0.008, 0x0c0e12, new THREE.Vector3(0, 0, 0), { metalness: 0.8, roughness: 0.2 });
  lente.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), mira);
  lente.position.copy(mira.clone().multiplyScalar(0.013));
  cuerpo.add(lente);
  cuerpo.position.copy(pos);
  objs.push(cuerpo);
  if (anillo) {
    const a = new THREE.Mesh(new THREE.TorusGeometry(0.022, 0.003, 12, 40), mat(0xffffff, { emissive: 0xffffff, emissiveIntensity: 0.5 }));
    a.rotation.x = Math.PI / 2;
    a.position.copy(pos).add(new THREE.Vector3(0, -0.014, 0));
    objs.push(a);
  }
  const codo = new THREE.Vector3(basePoste.x, pos.y, basePoste.z);
  objs.push(barra(pos, codo, 0.003, MAT_ALU), barra(codo, basePoste, 0.004, MAT_ALU));
  const d = new THREE.Vector3(0.006, 0, 0);
  objs.rutaCable = [pos.clone().add(new THREE.Vector3(0, 0.012, 0)), codo.clone().add(d).add(new THREE.Vector3(0, 0.006, 0)),
    basePoste.clone().add(d).add(new THREE.Vector3(0, 0.004, 0))];
  objs.push(caja(0.03, 0.03, 0.004, 0x30363d, basePoste.clone().add(new THREE.Vector3(0, 0.002, 0))));
  return objs;
}

function construirSensores() {
  for (const s of G.sensores) {
    const obj = { objetos: [], numero: s.numero, meta: s };
    const g = s.geometria;
    if (g && g.tipo === 'rayo') {
      const a = V(g.origen), b = V(g.destino);
      obj.rayos = (g.haces || [g]).map((h) => {
        const r = barra(V(h.origen), V(h.destino), 0.0009, COLOR.cian, { emissive: COLOR.cian, emissiveIntensity: 0.6, transparent: true, opacity: 0.55 });
        r.castShadow = false;
        obj.objetos.push(r);
        return r;
      });
      if (s.id === 'presencia') {
        // TCRT5000 mirando hacia abajo, en una escuadra desde la orilla -y
        // (en la orilla +y esta el motor de la cinta).
        // FC-51 acostado, con los LED en la punta sobre la casilla y los pines
        // hacia la escuadra (-y).
        construirModulo('presencia', escena, a.clone().add(Vxyz(0, -0.013, 0.005)), yaw(-90), { sensorId: 'presencia', etiquetaSobre: 0.03 });
        // Escuadra: sale hacia el riel -y y baja hasta apoyarse encima de el.
        const rm = P.rielMonedas;
        // La escuadra lo toma por debajo de la placa (los pines quedan libres).
        const bajo = a.clone().add(Vxyz(0, -0.013, 0.003));
        const lado = new THREE.Vector3(a.x, bajo.y, -rm.y);
        const pie = new THREE.Vector3(a.x, rm.zArriba + 0.0015, -rm.y);
        obj.objetos.push(barra(bajo, lado, 0.002, MAT_ALU), barra(lado, pie, 0.002, MAT_ALU),
          caja(0.012, 0.012, 0.003, COLOR.impreso, pie.clone()));
        // El cable: de los pines (arriba de la punta -y de la placa) hacia el
        // riel, por afuera de el.
        const xs = a.x + 0.006;
        obj.rutaCable = [new THREE.Vector3(xs, a.y + 0.03, -(a.z * -1) + 0.035), new THREE.Vector3(xs, a.y + 0.03, -rm.y + 0.012),
          new THREE.Vector3(xs, rm.zArriba + 0.012, -rm.y + 0.012)];
        obj.campos = conosSensor(a, b.clone().sub(a), a.distanceTo(b), 10, 15);
        obj.objetos.push(...obj.campos);
      } else {
        // Barreras de confirmacion: emisor y receptor en las paredes de la canaleta.
        obj.objetos.push(caja(0.006, 0.006, 0.01, 0x1c2733, a), caja(0.006, 0.006, 0.01, 0x1c2733, b));
      }
      obj.ancla = a.clone().add(new THREE.Vector3(0, 0.014, 0));
    } else if (g && g.tipo === 'cono') {
      // Cortina (punto 11): UN VL53L0X en el extremo de la prensa, del lado
      // del operador, mirando hacia la tapa. Se dibuja su cono real (~25
      // grados) hasta el final de la ventana de distancia: lo que entre ahi
      // es una mano; lo que queda mas lejos no cuenta. Placa del sensor en
      // una escuadra sobre un poste de perfil desde la mesa (nada flota).
      const a = V(g.origen), b = V(g.destino);
      const eje = b.clone().sub(a);
      const largo = eje.length();
      const dir = eje.clone().normalize();
      const conoCortina = new THREE.Mesh(new THREE.ConeGeometry(g.radio_final, largo, 32, 1, true),
        new THREE.MeshBasicMaterial({ color: COLOR.cian, transparent: true, opacity: 0.06, side: THREE.DoubleSide, depthWrite: false }));
      conoCortina.position.copy(a).add(eje.clone().multiplyScalar(0.5));
      conoCortina.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().negate());   // punta en el sensor
      obj.cono = conoCortina;
      obj.objetos.push(conoCortina);
      obj.campos = [conosSensor(a, dir, largo, 12.5, 17.5)[1]];
      obj.objetos.push(...obj.campos);
      const ejeLinea = barra(a, b, 0.0006, COLOR.cian, { emissive: COLOR.cian, emissiveIntensity: 0.6, transparent: true, opacity: 0.45 });
      ejeLinea.castShadow = false;
      obj.rayos = [ejeLinea];
      obj.objetos.push(ejeLinea);
      // Placa del VL53L0X (la de los modulos comunes: ~25 x 13 mm) de
      // canto, con la cara del chip hacia la zona, y su escuadra.
      // GY-530 de canto, con el VL53L0X hacia la zona y los pines atras.
      const qCortina = orientar(dir.clone().negate());
      construirModulo('vl53_cortina', escena, a.clone().addScaledVector(dir, -0.001), qCortina, { sensorId: 'cortina', etiquetaSobre: 0 });
      // Todo el soporte queda detras de la placa (hasta `fondo_soporte`),
      // fuera del cono y del paso del vaso que va a la canaleta.
      const fondo = g.fondo_soporte;
      const escuadra = caja(0.006, 0.02, 0.004, COLOR.impreso, a.clone().add(dir.clone().multiplyScalar(-0.005)).add(new THREE.Vector3(0, -0.0085, 0)));
      const zMesa = G.cinta_vasos.estaciones[0].posicion[2] - G.altura_superficie;
      const xPoste = a.clone().add(dir.clone().multiplyScalar(-(fondo - 0.005)));
      // El poste arranca de un brazo de perfil 10 mm atornillado al costado
      // de la bancada de vasos (antes arrancaba a la altura de la mesa pero
      // fuera de ella: flotaba). El brazo va por debajo de la banda: no
      // estorba al vaso que el empujador pasa a la canaleta.
      const yBorde = -(G.cinta_vasos.estaciones[0].posicion[1] - G.ancho_cinta_vasos / 2 - 0.003);
      const zBrazo = zMesa + 0.008;
      const poste = perfil(new THREE.Vector3(xPoste.x, zBrazo + 0.005, xPoste.z), new THREE.Vector3(xPoste.x, a.y - 0.004, xPoste.z), 0.01);
      const brazo = perfil(new THREE.Vector3(xPoste.x, zBrazo, yBorde), new THREE.Vector3(xPoste.x, zBrazo, xPoste.z + 0.005), 0.01);
      const pie = caja(0.016, 0.004, 0.016, 0x30363d, new THREE.Vector3(xPoste.x, zBrazo, yBorde + 0.002));
      obj.objetos.push(escuadra, poste, brazo, pie);
      obj.rutaCable = [PIN['vl53_cortina.SDA'].tip.clone().addScaledVector(dir, -0.012), new THREE.Vector3(xPoste.x + 0.007, a.y - 0.004, xPoste.z),
        new THREE.Vector3(xPoste.x + 0.007, zBrazo - 0.007, xPoste.z), new THREE.Vector3(xPoste.x + 0.007, zBrazo - 0.007, yBorde)];
      obj.ancla = a.clone().add(new THREE.Vector3(0, 0.022, 0));
    } else if (g && g.tipo === 'camara') {
      const p = V(g.posicion);
      const mira = new THREE.Vector3(g.mira[0], g.mira[2], -g.mira[1]).normalize();
      const objetivo = V(g.objetivo);
      if (s.id === 'camara') {
        // Cenital sobre E5, con anillo de luz; poste desde el piso del lado +y.
        const partes = camaraConSoporte(p, mira, { anillo: true, basePoste: Vxyz(g.posicion[0], g.posicion[1] + 0.075, 0) });
        obj.objetos.push(...partes);
        obj.rutaCable = partes.rutaCable;
      } else {
        // Camara de vasos: al costado, a la altura de la boca, sobre su poste.
        const partes = camaraConSoporte(p, mira, { basePoste: Vxyz(g.posicion[0], g.posicion[1] - 0.02, 0) });
        obj.objetos.push(...partes);
        obj.rutaCable = partes.rutaCable;
        // Franjas de medida de cada estacion (las "barreras virtuales").
        obj.franjas = (g.franjas || []).map((f) => {
          const m = barra(V(f.origen), V(f.destino), 0.0007, COLOR.cian, { emissive: COLOR.cian, emissiveIntensity: 0.6, transparent: true, opacity: 0.4 });
          m.castShadow = false;
          m.userData.nivel = f.nivel;
          obj.objetos.push(m);
          return m;
        });
      }
      // Campo de vision de la camara (piramide abierta hasta lo que mira).
      const eje = p.clone().sub(objetivo);
      const ancho = s.id === 'camara' ? 0.035 : 0.21;
      const cono = new THREE.Mesh(new THREE.ConeGeometry(ancho, eje.length(), 4, 1, true),
        new THREE.MeshBasicMaterial({ color: COLOR.cian, transparent: true, opacity: 0.07, side: THREE.DoubleSide, depthWrite: false }));
      cono.position.copy(objetivo).add(eje.clone().multiplyScalar(0.5));
      cono.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), eje.clone().normalize());
      cono.rotateY(Math.PI / 4);
      obj.cono = cono;
      obj.objetos.push(cono);
      const led = new THREE.Mesh(new THREE.SphereGeometry(0.003, 12, 12), new THREE.MeshBasicMaterial({ color: 0x30363d }));
      led.position.copy(p).add(new THREE.Vector3(0, 0.014, 0));
      obj.led = led;
      obj.objetos.push(led);
      obj.ancla = p.clone().add(new THREE.Vector3(0, 0.03, 0));
    } else if (g && g.tipo === 'proximidad') {
      // `posicion` es la CARA activa del sensor; el cuerpo queda detras.
      const p = V(g.posicion);
      const mira = new THREE.Vector3(g.mira[0], g.mira[2], -g.mira[1]).normalize();
      const CAMPO = { sensor_interior: [0.105, 12.5, 17.5], capacitivo: [0.006, 35, 40], inductivo: [0.004, 30, 35],
                      hall_carrusel: [0.004, 30, 35] }[s.id];
      let modulo, colgar = null;
      if (g.bajo_cinta) {
        // Capacitivo (tapa azul) e inductivo (tapa naranja) debajo de la
        // cinta, enroscados en el inserto de la bancada.
        modulo = sensorCilindrico(p, mira, s.id === 'capacitivo'
          ? { largo: 0.068, colorCara: 0x2f6fd0 } : { largo: 0.060, colorCara: COLOR.naranja });
        // Etiqueta abajo y hacia afuera de la cinta, una a cada lado (si no
        // se enciman: estan a 4 cm).
        const dx = s.id === 'capacitivo' ? -0.03 : 0.03;
        const lado = Vxyz(g.posicion[0] + dx, g.posicion[1] - 0.06, g.posicion[2] - 0.05);
        const et = etiqueta(s.id === 'capacitivo' ? 'Capacitivo (bajo E1)' : 'Inductivo (bajo E2)',
          { alto: 0.0085, color: s.id === 'capacitivo' ? '#6aa3ff' : '#f0a060' });
        et.position.copy(lado).add(new THREE.Vector3(0, -0.012, 0));
        // Linea guia de la etiqueta (una anotacion, no una pieza).
        obj.objetos.push(et, barra(lado, p.clone().add(new THREE.Vector3(0, -0.03, 0)), 0.0004,
          new THREE.MeshBasicMaterial({ color: 0x8b949e, transparent: true, opacity: 0.5 })));
        obj.ancla = lado;
      } else if (s.id === 'hall_carrusel') {
        // KY-003 acostado sobre el iman: el A3144 abajo, en la punta interior
        // de la placa; los pines en la exterior, hacia arriba.
        const [cx, cy] = G.almacen.centro;
        const fuera = new THREE.Vector3(g.posicion[0] - cx, 0, -(g.posicion[1] - cy)).normalize();
        const q = yaw(THREE.MathUtils.radToDeg(Math.atan2(-fuera.z, fuera.x)));
        const centro = p.clone().addScaledVector(fuera, 0.006).add(new THREE.Vector3(0, 0.0035, 0));
        modulo = construirModulo('hall', escena, centro, q, { sensorId: s.id, etiquetaSobre: 0.03 });
        // Varilla desde el medio de la placa: por fuera del disco.
        colgar = centro.clone().addScaledVector(fuera, 0.002).add(new THREE.Vector3(0, 0.0016, 0));
        obj.ancla = p.clone().add(new THREE.Vector3(0, 0.03, 0));
      } else {
        // GY-530 con el VL53L0X mirando hacia abajo y los pines arriba.
        modulo = construirModulo('vl53_interior', escena, p.clone().add(new THREE.Vector3(0, 0.001, 0)), yaw(0), { sensorId: s.id, etiquetaSobre: 0.03 });
        colgar = p.clone().add(Vxyz(0, -0.003, 0.0026));
        // Abrazadera impresa: la varilla no se clava en la placa, la toma un bloque pegado
        // con cinta doble faz (se veia como si la atravesara, auditoria 2026-09-28).
        obj.objetos.push(caja(0.009, 0.007, 0.003, 0x1b1e22, colgar.clone().add(new THREE.Vector3(0, 0.0015, 0))));
        colgar.add(new THREE.Vector3(0, 0.003, 0));
        obj.ancla = p.clone().add(new THREE.Vector3(0, 0.03, 0));
      }
      if (modulo.userData.led) obj.led = modulo.userData.led;
      else if (!g.bajo_cinta) {
        const led = new THREE.Mesh(new THREE.SphereGeometry(0.0011, 10, 10), new THREE.MeshBasicMaterial({ color: 0x30363d }));
        led.position.copy(colgar).add(new THREE.Vector3(0.005, 0.0005, 0));
        obj.objetos.push(led);
        obj.led = led;
      }
      if (g.bajo_cinta) obj.objetos.push(modulo);
      if (CAMPO) {
        obj.campos = conosSensor(p, mira, ...CAMPO);
        obj.objetos.push(...obj.campos);
      }
      if (colgar) {
        // Colgado del portico con una varilla (nada flota).
        const zVarilla = P.portico.z - 0.012;
        const arriba = new THREE.Vector3(colgar.x, zVarilla, colgar.z);
        const alPortico = new THREE.Vector3(colgar.x, zVarilla, -P.portico.y);
        obj.objetos.push(barra(colgar, arriba, 0.002, MAT_ALU), barra(arriba, alPortico, 0.002, MAT_ALU));
        // El cable sale de los pines y sube pegado a la varilla (4 mm al lado).
        const lado = new THREE.Vector3(0.006, 0, 0);
        const pines = s.id === 'hall_carrusel' ? PIN['hall.S'] : PIN['vl53_interior.SCL'];
        obj.rutaCable = [pines.tip.clone().add(new THREE.Vector3(0, 0.012, 0)), arriba.clone().add(lado).add(new THREE.Vector3(0, -0.02, 0)),
          arriba.clone().add(lado), alPortico.clone().add(lado)];
      }
      modulo.updateMatrixWorld(true);
      if (g.bajo_cinta) obj.rutaCable = [modulo.localToWorld(modulo.userData.salidaCable.clone())];
    } else {
      // Sensores del carro: los objetos ya estan en el carro; aqui solo el marcador.
      obj.ancla = null;
    }
    obj.objetos.forEach((o) => { o.traverse((m) => { m.userData.sensorId = s.id; }); escena.add(o); });
    const marca = etiqueta(String(s.numero), { alto: 0.011, color: '#0e1116', fondo: '#f2b134', alcance: 1.1 });
    marca.userData.sensorId = s.id;
    if (obj.ancla) { marca.position.copy(obj.ancla); escena.add(marca); }
    obj.marcador = marca;
    SENS[s.id] = obj;
  }
  // Marcadores de los sensores del carro, pegados al carro.
  const v = G.vehiculo;
  const pos = {
    linea_ir: Vxyz(v.largo / 2 - 0.012, 0.05, 0.03), ultrasonico: Vxyz(v.largo / 2 + 0.02, 0.03, 0.08),
    laser_frontal: Vxyz(v.largo / 2 + 0.045, -0.045, 0.1),
    encoders: Vxyz(-v.largo * 0.18, v.ancho / 2 + 0.03, 0.07), cuna: Vxyz(-v.largo * 0.25, 0.05, 0.17),
  };
  for (const [id, p] of Object.entries(pos)) {
    if (!SENS[id]) continue;
    SENS[id].marcador.position.copy(p);
    P.carro.add(SENS[id].marcador);
  }
}

function sensorActivo(id) {
  if (!estado || !estado.sensores) return false;
  if (id === 'camara') return !!(estado.casillas_monedas && estado.casillas_monedas[4]);
  if (id === 'linea_ir' || id === 'encoders') return true;   // carro quieto sobre la linea (punto 14 pendiente)
  if (id === 'ultrasonico' || id === 'laser_frontal') return false;
  if (id === 'cuna') return false;
  if (estado.lecturas_tick && id in estado.lecturas_tick) return !!estado.lecturas_tick[id];
  return !!estado.sensores[id];
}

function sensorEnAlarma(id) {
  if (id === 'camara_vasos') return !!(estado && estado.camara_vasos_alarma);
  return SENSORES_ALARMA.has(id) && sensorActivo(id);
}

const ZONAS_FRANJAS = ['verificacion', 'verificacion', 'llenado', 'llenado', 'tapa', 'tapa', 'prensa', 'prensa'];

function actualizarSensores(t) {
  for (const [id, s] of Object.entries(SENS)) {
    const activo = sensorActivo(id);
    const alarma = sensorEnAlarma(id);
    const color = alarma ? COLOR.rojo : activo ? COLOR.verde : COLOR.cian;
    const resaltado = resaltados.has(id);
    const pulso = resaltado ? 0.6 + 0.4 * Math.sin(t * 6) : 0;
    for (const r of s.rayos || []) {
      r.material.color.setHex(color);
      r.material.emissive.setHex(color);
      r.material.emissiveIntensity = (activo ? 1.6 : 0.5) + pulso * 2;
      r.material.opacity = activo || resaltado ? 0.95 : 0.45;
      const grosor = resaltado ? 2.2 : activo ? 1.6 : 1;
      r.scale.set(grosor, 1, grosor);
    }
    if (s.franjas) {
      const zonas = (estado && estado.camara_vasos_zonas) || {};
      s.franjas.forEach((f, i) => {
        const z = zonas[ZONAS_FRANJAS[i]] || {};
        const ocupada = f.userData.nivel === 'media' ? !!z.media : !!z.borde;
        const c = ocupada ? (f.userData.nivel === 'borde' ? COLOR.rojo : COLOR.verde) : COLOR.cian;
        f.material.color.setHex(c); f.material.emissive.setHex(c);
        f.material.opacity = ocupada || resaltado ? 0.85 : 0.3;
        f.material.emissiveIntensity = 0.6 + pulso * 2;
      });
    }
    if (s.led) s.led.material.color.setHex(activo ? (alarma ? COLOR.rojo : COLOR.verde) : 0x30363d);
    if (s.cono) s.cono.material.opacity = (activo ? 0.14 : 0.06) + (resaltado ? 0.08 * pulso : 0);
    if (s.cono && id === 'cortina') s.cono.material.color.setHex(color);
    s.marcador.userData.opacidadBase = resaltados.size === 0 ? 0.9 : resaltado ? 1 : 0.25;
    if (!s.marcador.userData.baseX) continue;
    const escala = resaltado ? 1.35 + 0.15 * Math.sin(t * 6) : 1;
    s.marcador.scale.set(escala * s.marcador.userData.baseX, escala * s.marcador.userData.baseY, 1);
  }
  // Infrarrojos de linea: el del centro ve la linea con el carro en la salida.
  if (P.irLinea) P.irLinea.forEach((led, i) => led.material.color.setHex(i === 2 ? COLOR.verde : 0x30363d));
  if (P.conoUS) P.conoUS.material.opacity = resaltados.has('ultrasonico') ? 0.25 + 0.1 * Math.sin(t * 6) : 0.12;
  if (P.conoTof) P.conoTof.material.opacity = resaltados.has('laser_frontal') ? 0.2 + 0.1 * Math.sin(t * 6) : 0.07;
}

// ---------------------------------------------------------------------------
// elementos dinamicos: fichas de la cinta, vasos, salidas
// ---------------------------------------------------------------------------

const fichas = new Map();     // id -> {grupo, halo, indice}
const vasos = new Map();      // id vaso -> {...}
const enCubeta = { rechazo: new Set() };

function crearFicha(c) {
  const grupo = new THREE.Group();
  const d = Math.max(0.008, (c.diametro_mm || 20) / 1000);
  if (c.tipo === 'vacia_registrada') {
    const anillo = new THREE.Mesh(new THREE.RingGeometry(0.008, 0.011, 30),
      new THREE.MeshBasicMaterial({ color: COLOR.rojo, side: THREE.DoubleSide, transparent: true, opacity: 0.8 }));
    anillo.rotation.x = -Math.PI / 2;
    anillo.position.y = 0.001;
    grupo.add(anillo);
  } else if (c.tipo === 'moneda') {
    const alto = 0.0018;
    const bimetalica = BIMETALICAS.has(c.clase_real);
    grupo.add(cilindro(d / 2, alto, bimetalica ? COLOR.plata : COLOR.oro, new THREE.Vector3(0, alto / 2, 0), { metalness: 0.85, roughness: 0.3 }));
    if (bimetalica) grupo.add(cilindro(d * 0.32, alto + 0.0003, COLOR.oro, new THREE.Vector3(0, alto / 2, 0), { metalness: 0.85, roughness: 0.3 }));
    const et = etiqueta(c.clase_real ? c.clase_real.split('_')[0] : '?', { alto: 0.007, color: '#f2b134' });
    et.position.set(0, 0.012, 0);
    grupo.add(et);
  } else if (c.tipo === 'bloque') {
    grupo.add(caja(0.02, 0.02, 0.02, 0x3372c4, new THREE.Vector3(0, 0.01, 0)));
  } else {
    const alto = 0.003;
    const plastico = c.tipo === 'boton_plastico';
    grupo.add(cilindro(d / 2, alto, plastico ? 0xd9259f : 0x8d939b, new THREE.Vector3(0, alto / 2, 0), plastico ? {} : { metalness: 0.8, roughness: 0.35 }));
    for (const dx of [-0.0025, 0.0025]) grupo.add(cilindro(0.0012, alto + 0.0006, 0x07090c, new THREE.Vector3(dx, alto / 2, 0)));
  }
  const halo = new THREE.Mesh(new THREE.RingGeometry(0.0135, 0.0165, 40), new THREE.MeshBasicMaterial({ color: 0x30363d, transparent: true, opacity: 0, side: THREE.DoubleSide }));
  halo.rotation.x = -Math.PI / 2;
  halo.position.y = 0.0004;
  grupo.add(halo);
  grupo.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  escena.add(grupo);
  return { grupo, halo, tipo: c.tipo, clase: c.clase_real, indice: -1 };
}

function posEstacionMonedas(i) { return V(G.cinta_monedas.estaciones[i].posicion); }
function posEstacionVasos(i) { return V(G.cinta_vasos.estaciones[i].posicion); }

function sincronizarFichas() {
  const vivos = new Set();
  const avance = seg('avance_casilla_monedas', 600);
  const nEst = G.cinta_monedas.estaciones.length;
  (estado.casillas_monedas || []).forEach((c, i) => {
    if (!c) return;
    vivos.add(c.id);
    let f = fichas.get(c.id);
    if (!f) {
      f = crearFicha(c);
      // Una ficha nueva aparece en la carga (la puso el operador en la pausa);
      // si el visor se abrio a mitad de corrida, directo en su casilla.
      f.grupo.position.copy(posEstacionMonedas(i));
      f.indice = i;
      fichas.set(c.id, f);
    } else if (f.indice !== i) {
      // Viaja con la banda: mismo tiempo y misma curva que los separadores.
      cancelar(f.grupo);
      recorrer(f.grupo, [f.grupo.position.clone(), posEstacionMonedas(i)], avance);
      f.indice = i;
    }
    const color = c.causa ? COLOR.rojo : c.aceptada ? COLOR.verde : null;
    f.halo.material.opacity = color ? 0.95 : 0;
    if (color) f.halo.material.color.setHex(color);
  });
  // Las que ya no estan en la cinta salieron por la descarga (filtro total):
  // al almacen si fueron aceptadas, a la unica bandeja si no.
  const rechazos = (estado.salidas || {}).rechazo || [];
  for (const [id, f] of fichas) {
    if (vivos.has(id)) continue;
    fichas.delete(id);
    cancelar(f.grupo);
    f.halo.visible = false;
    const inicio = posEstacionMonedas(nEst - 1);
    const llegar = f.indice >= 0 && f.indice < nEst - 1
      ? [{ puntos: [f.grupo.position.clone(), inicio], seg: avance }] : [];
    const rechazada = rechazos.some((s) => s.id === id);
    const [a, b] = rechazada ? P.e7.aRechazo : P.e7.aSelector;
    const caidaEmbudo = [inicio, P.e7.cabeza, P.e7.embudo, a];
    const retrasoDesvio = llegar.length ? avance : 0;
    if (rechazada) {
      enCubeta.rechazo.add(id);
      f.grupo.userData.deCubeta = true;
      const k = enCubeta.rechazo.size - 1;
      const cub = P.cubetas.rechazo.clone().add(new THREE.Vector3(((k % 4) - 1.5) * 0.018, 0.002 + Math.floor(k / 12) * 0.004, ((Math.floor(k / 4) % 3) - 1) * 0.02));
      moverDesvio(false, retrasoDesvio);
      tramos(f.grupo, [...llegar, { puntos: caidaEmbudo, seg: 0.45, ease: caida }, { puntos: [a, b, cub], seg: 0.5, ease: caida }]);
    } else {
      const d = parseInt(f.clase, 10);
      const den = P.tubos[d] ? d : 'otras';
      // El carrusel pone el tubo de esa denominacion bajo la carga mientras
      // la moneda viene; la moneda cae casi vertical a la boca del tubo.
      girarCarrusel(den, P.carrusel.carga);
      moverDesvio(true, retrasoDesvio);
      const boca = b.clone();
      tramos(f.grupo, [...llegar,
        { puntos: caidaEmbudo, seg: 0.4, ease: caida },
        { puntos: [a, boca], seg: 0.25, ease: caida },
        { puntos: [boca, boca.clone().add(new THREE.Vector3(0, -0.035, 0))], seg: 0.2, ease: caida },
      ], () => escena.remove(f.grupo));
    }
  }
}

function moverDesvio(haciaAlmacen, retraso = 0) {
  if (!P.desvio) return;
  cancelar(P.desvio);
  const ang = 0.5;
  const hasta = haciaAlmacen ? -ang : ang;
  let desde = P.desvio.rotation.x;
  animar(0.15, (u) => { if (u === 0) desde = P.desvio.rotation.x; P.desvio.rotation.x = desde + (hasta - desde) * suave(u); },
    { retraso, dueno: P.desvio });
  if (haciaAlmacen) {
    // A prueba de fallas: vuelve sola al reposo (hacia el rechazo).
    animar(0.2, (u) => { P.desvio.rotation.x = hasta + (ang - hasta) * suave(u); }, { retraso: retraso + 1.0, dueno: P.desvio });
  }
}

function crearVaso(id, marcador) {
  const g = G.vaso;
  const rBoca = g.diametro / 2 + g.reborde;
  const grupo = new THREE.Group();
  // Vaso OPACO (grupo, 2026-09-25): lo que tiene adentro lo ve el sensor
  // del interior en la verificacion.
  const cuerpo = new THREE.Mesh(new THREE.CylinderGeometry(g.diametro / 2, g.diametro / 2 * 0.86, g.altura, 40, 1, true),
    mat(0xeef1f4, { side: THREE.DoubleSide, roughness: 0.55 }));
  cuerpo.position.y = g.altura / 2;
  const fondo = cilindro(g.diametro / 2 * 0.86, 0.002, 0xdfe1e4, new THREE.Vector3(0, 0.001, 0));
  // Pestana del reborde (8 mm): es lo que se apoya en los rieles.
  const reborde = new THREE.Mesh(new THREE.RingGeometry(g.diametro / 2, rBoca, 40), mat(0xeef3f8, { transparent: true, opacity: 0.75, side: THREE.DoubleSide }));
  reborde.rotation.x = -Math.PI / 2;
  reborde.position.y = g.altura - 0.001;
  const aro = new THREE.Mesh(new THREE.TorusGeometry(rBoca, 0.0012, 6, 40), mat(0xeef3f8, { transparent: true, opacity: 0.8 }));
  aro.rotation.x = Math.PI / 2;
  aro.position.y = g.altura - 0.001;
  const tapa = cilindro(rBoca, 0.005, COLOR.tapa, new THREE.Vector3(0, g.altura + 0.0015, 0));
  tapa.visible = false;
  // Identificador: una CINTA que rodea todo el vaso con el mismo ArUco
  // repetido 6 veces (siempre hay uno de frente, gire como gire).
  const hBanda = 0.02, yBanda = g.altura * 0.62;
  const rBanda = (g.diametro / 2 * 0.86) + (g.diametro / 2 * 0.14) * (yBanda / g.altura) + 0.0006;
  const aruco = new THREE.Mesh(new THREE.CylinderGeometry(rBanda + 0.00035, rBanda - 0.00035, hBanda, 48, 1, true),
    new THREE.MeshBasicMaterial({ map: texturaCintaAruco(marcador || id) }));
  aruco.position.set(0, yBanda, 0);
  const pila = new THREE.Group();
  const figura = cilindro(0.028, 0.035, 0x8a4fcf, new THREE.Vector3(0, 0.0175, 0));
  figura.visible = false;
  const fantasma = new THREE.Mesh(new THREE.CylinderGeometry(g.diametro / 2, g.diametro / 2, g.altura, 16, 1, true),
    new THREE.MeshBasicMaterial({ color: COLOR.rojo, wireframe: true, transparent: true, opacity: 0.5 }));
  fantasma.position.y = g.altura / 2;
  fantasma.visible = false;
  const anillo = new THREE.Mesh(new THREE.RingGeometry(g.diametro / 2 + 0.004, g.diametro / 2 + 0.008, 40), new THREE.MeshBasicMaterial({ color: 0x8b949e, side: THREE.DoubleSide }));
  anillo.rotation.x = -Math.PI / 2;
  anillo.position.y = 0.0006;
  const et = etiqueta(`vaso ${id}`, { alto: 0.011 });
  et.position.y = g.altura + 0.03;
  grupo.add(cuerpo, fondo, reborde, aro, tapa, aruco, pila, figura, fantasma, anillo, et);
  cuerpo.castShadow = false;
  escena.add(grupo);
  return { grupo, cuerpo, fondo, reborde, aro, tapa, aruco, pila, figura, fantasma, anillo, et, monedas: 0, fuera: false, indice: -1, marcador };
}

const COLOR_ESTADO_VASO = { valida: 0x8b949e, llenando: COLOR.ambar, llena: COLOR.ambar, tapada: COLOR.verde, invalida: COLOR.rojo, rechazada: COLOR.rojo, entregada: COLOR.azul, vacia: 0x30363d };

function ajustarPila(v, cantidad) {
  while (v.monedas < cantidad) {
    const n = v.monedas;
    const moneda = cilindro(0.011, 0.0018, n % 3 === 0 ? COLOR.plata : COLOR.oro, new THREE.Vector3(((n * 37) % 5 - 2) * 0.004, 0.003 + n * 0.0022, ((n * 53) % 5 - 2) * 0.004), { metalness: 0.85, roughness: 0.3 });
    v.pila.add(moneda);
    v.monedas++;
  }
}

function sincronizarVasos() {
  const enCinta = new Set();
  let avanzo = false;
  const avance = seg('avance_casilla_vasos', 1000);
  (estado.casillas_vasos || []).forEach((c, i) => {
    if (!c) return;
    enCinta.add(c.id);
    let v = vasos.get(c.id);
    if (!v) {
      v = crearVaso(c.id, c.marcador);
      v.grupo.position.copy(posEstacionVasos(i));
      v.indice = i;
      vasos.set(c.id, v);
    }
    let movido = false;
    if (v.indice !== i && !v.fuera) {
      cancelar(v.grupo);
      recorrer(v.grupo, [v.grupo.position.clone(), posEstacionVasos(i)], avance);
      if (i > v.indice) avanzo = true;
      v.indice = i;
      movido = true;
    }
    const ausente = c.fisico === 'ausente', figura = c.fisico === 'figura';
    for (const o of [v.cuerpo, v.fondo, v.reborde, v.aro, v.pila, v.aruco]) o.visible = !ausente && !figura;
    if (c.marcador && c.marcador !== v.marcador) {
      // Cambiado por otro vaso igual: el marcador nuevo es otro patron.
      v.marcador = c.marcador;
      v.aruco.material.map = texturaCintaAruco(c.marcador);
    }
    v.figura.visible = figura;
    v.fantasma.visible = ausente;
    const tapadoAhora = !ausente && !figura && (c.estado === 'tapada' || c.estado === 'entregada');
    if (tapadoAhora && !v.tapa.visible && !v.tapaCayendo) caerTapa(v, movido ? avance : 0);
    if (!tapadoAhora && !v.tapaCayendo) v.tapa.visible = false;
    v.anillo.material.color.setHex(COLOR_ESTADO_VASO[c.estado] || 0x8b949e);
    if (c.denominacion && !v.conDenominacion) {
      v.grupo.remove(v.et);
      const nombre = c.denominacion === 'otras' ? 'otras' : `$${c.denominacion.toLocaleString('es-CO')}`;
      v.et = etiqueta(`vaso ${c.id} · ${nombre}`, { alto: 0.011, color: '#3fb68b' });
      v.et.position.y = G.vaso.altura + 0.03;
      v.grupo.add(v.et);
      v.conDenominacion = true;
    }
    // Las monedas aparecen cuando termina de caer el lote (animarEmbalado).
    if (!ausente && !figura && !v.llenando) ajustarPila(v, c.cantidad);
  });
  // Vasos que ya salieron de la cinta: a la canaleta o a la bandeja. La
  // simulacion los descarga en el mismo avance en que llegan a la ultima
  // casilla, asi que aqui primero llegan con la banda y despues salen.
  const entregados = [], rechazados = [];
  for (const s of estado.vasos_salida || []) (s.destino === 'entrega' ? entregados : rechazados).push(s);
  // La fila de la canaleta la lleva la simulacion (estado.canaleta: el
  // primero esta contra la compuerta). Los entregados que ya no estan en la
  // fila se los llevo el carro (de reemplazo, hasta los puntos 13-14).
  const fila = estado.canaleta || [];
  for (const s of entregados) {
    if (fila.includes(s.id) || enCinta.has(s.id)) continue;
    const v = vasos.get(s.id);
    if (v && v.fuera && !v.retirado && !v.enCamino) {
      v.retirado = true;
      cancelar(v.grupo);
      soltarUnVaso();
      abrirLengueta(0.25);
      const cuna = P.canaleta.fin.clone().addScaledVector(P.canaleta.dir, 0.06).add(new THREE.Vector3(0, -G.vaso.altura + 0.004, 0));
      recorrer(v.grupo, [v.grupo.position.clone(), cuna], 0.5, { ease: caida,
        fin: () => animar(0.6, () => {}, { fin: () => escena.remove(v.grupo) }) });
    } else if (!v) {
      // entregado y retirado antes de abrir el visor: no se dibuja
    }
  }
  const enCanaleta = entregados.filter((s) => fila.includes(s.id));
  enCanaleta.forEach((s) => {
    if (enCinta.has(s.id)) return;
    const pos = fila.indexOf(s.id);   // 0 = contra la compuerta
    let v = vasos.get(s.id);
    const objetivo = P.canaleta.fin.clone().addScaledVector(P.canaleta.dir, -(pos * (G.vaso.diametro + 2 * G.vaso.reborde + 0.004) + 0.04))
      .add(new THREE.Vector3(0, -G.vaso.altura + 0.002 + G.canaleta.diametro_riel / 2, 0));
    if (!v) {
      // El visor se abrio despues de que este vaso salio de la cinta: se
      // crea directamente en su lugar, sin animacion.
      v = crearVaso(s.id);
      ajustarPila(v, s.cantidad);
      v.tapa.visible = true;
      v.fuera = true;
      v.grupo.position.copy(objetivo);
      vasos.set(s.id, v);
      v.enCola = pos;
      return;
    }
    v.anillo.visible = false;
    if (!v.fuera) {
      v.fuera = true;
      v.enCola = pos;
      avanzo = true;
      empujarACanaleta(v, objetivo, seg('avance_casilla_vasos', 1000));
    } else if (v.enCola !== pos && !v.enCamino) {
      // La fila avanza cuando se libera un lugar adelante.
      v.enCola = pos;
      recorrer(v.grupo, [v.grupo.position.clone(), objetivo], 0.5, { ease: caida });
    }
  });
  rechazados.forEach((s, k) => {
    if (enCinta.has(s.id)) return;
    let v = vasos.get(s.id);
    const objetivo = P.bandeja.clone().add(new THREE.Vector3(((k % 3) - 1) * 0.028, 0.004, ((Math.floor(k / 3) % 2) - 0.5) * 0.05));
    if (!v) {
      v = crearVaso(s.id);
      v.fuera = true;
      v.grupo.position.copy(objetivo);
      v.grupo.rotation.z = -1.2;
      vasos.set(s.id, v);
      return;
    }
    v.objetivoBandeja = objetivo;
    if (v.fuera) return;
    // No lo empuja nadie: llega a la ultima casilla con la banda y ahi
    // espera; en el siguiente avance la cinta lo deja caer por el extremo.
    v.fuera = true;
    v.esperandoCaer = true;
    v.anillo.visible = false;
    avanzo = true;
    cancelar(v.grupo);
    recorrer(v.grupo, [v.grupo.position.clone(), posEstacionVasos(4)], avance);
    v.esperaDesde = estado.tick;
  });
  if (avanzo) {
    moverCinta('vasos', avance);
    for (const v of vasos.values()) {
      if (!v.esperandoCaer || v.esperaDesde === estado.tick) continue;
      v.esperandoCaer = false;
      const borde = P.finCintaVasos.clone();
      const giro = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, -1.2));
      tramos(v.grupo, [
        { puntos: [v.grupo.position.clone(), borde], seg: avance },
        { puntos: [borde, borde.clone().add(new THREE.Vector3(0.04, -0.04, 0)), v.objetivoBandeja], seg: 0.45, ease: caida, giro },
      ]);
    }
  }
}

// Empujador de descarga: la paleta (manivela) pasa el vaso de lado, la
// pestana se sube a los rieles y el vaso baja deslizando hasta su lugar en la
// fila.
// Escape de dos dedos: A sale y B entra (se va el primer vaso), y despues al
// reves (la fila baja un lugar contra A).
function soltarUnVaso() {
  const e = P.escape;
  if (!e) return;
  cancelar(e);
  const ida = seg('empujador', 700) / 3;
  animar(ida, (u) => { e.giro.rotation.y = e.retener + (e.soltar - e.retener) * suave(u); }, { dueno: e });
  animar(ida, (u) => { e.giro.rotation.y = e.soltar + (e.retener - e.soltar) * suave(u); }, { retraso: ida + 0.45, dueno: e });
}

// El vaso entra a la cuna: empuja la lengueta hacia adelante y el resorte
// la devuelve detras de el.
function abrirLengueta(retraso = 0) {
  const l = P.lengueta;
  if (!l) return;
  cancelar(l);
  animar(0.15, (u) => { l.rotation.y = -1.0 * suave(u); }, { retraso, dueno: l });
  animar(0.2, (u) => { l.rotation.y = -1.0 * (1 - suave(u)); }, { retraso: retraso + 0.3, dueno: l });
}

function empujarACanaleta(v, objetivo, llegada = 0) {
  const e = P.empujador;
  const ida = seg('empujador', 700) / 2;
  const recorrido = e.yFin - e.yReposo;   // en coordenadas sim (negativo: hacia -y)
  const moverPaleta = (u) => {
    const yy = e.yReposo + recorrido * u;
    e.paleta.position.z = -yy;
    const a = Vxyz(e.xd, yy + 0.002, e.zs + 0.035), b = Vxyz(e.xd, e.y + 0.075, e.zs + 0.05);
    const dir = new THREE.Vector3().subVectors(b, a);
    e.biela.position.copy(a).addScaledVector(dir, 0.5);
    e.biela.scale.y = dir.length() / (e.biela.geometry.parameters.height || 1);
    e.biela.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    e.horn.rotation.y = Math.PI * u;
  };
  animar(ida, (u) => moverPaleta(suave(u)), { retraso: llegada, dueno: e });
  animar(ida, (u) => moverPaleta(1 - suave(u)), { retraso: llegada + ida + 0.1, dueno: e });
  cancelar(v.grupo);
  const enDescarga = posEstacionVasos(4);
  const alLado = Vxyz(e.xd, G.canaleta.inicio[1] - 0.03, e.zs);
  tramos(v.grupo, [
    ...(llegada ? [{ puntos: [v.grupo.position.clone(), enDescarga], seg: llegada }] : []),
    { puntos: [enDescarga, alLado], seg: ida },
    { puntos: [alLado, objetivo], seg: 0.9, ease: caida },
  ]);
  v.enCamino = true;
  animar(llegada + ida + 0.9, () => {}, { fin: () => { v.enCamino = false; } });
}

function caerTapa(v, retraso = 0) {
  // El escape de dos dedos: se abre el de abajo (cae la tapa de abajo) y se
  // cierra el de arriba (retiene la pila); luego al reves. La tapa cae
  // ~13 mm y se asienta en la boca del vaso.
  const t = P.tapas;
  if (!t) { v.tapa.visible = true; return; }
  v.tapaCayendo = true;
  const [dedoAbajo, dedoArriba] = t.dedos;
  const xa0 = dedoAbajo.position.x, xb0 = dedoArriba.position.x;
  animar(0.12, (u) => { dedoAbajo.position.x = xa0 + 0.014 * suave(u); dedoArriba.position.x = xb0 - 0.006 * suave(u); }, { retraso, dueno: dedoAbajo });
  animar(0.12, (u) => { dedoAbajo.position.x = xa0 + 0.014 * (1 - suave(u)); dedoArriba.position.x = xb0 - 0.006 * (1 - suave(u)); }, { retraso: retraso + 0.35, dueno: dedoAbajo });
  const tapa = cilindro(t.rTapa, 0.005, COLOR.tapa, Vxyz(t.x, t.y, t.zBase));
  tapa.visible = false;
  escena.add(tapa);
  const destino = posEstacionVasos(2).add(new THREE.Vector3(0, G.vaso.altura + 0.0015, 0));
  animar(0.01, () => { tapa.visible = true; }, { retraso: retraso + 0.1 });
  recorrer(tapa, [tapa.position.clone(), destino], 0.12, { ease: caida, retraso: retraso + 0.12,
    fin: () => { escena.remove(tapa); v.tapa.visible = true; v.tapaCayendo = false; } });
}

// ---------------------------------------------------------------------------
// animaciones de actuadores disparadas por eventos
// ---------------------------------------------------------------------------

const bitacora = [];

function ciclarPrensa(retraso = 0) {
  const pr = P.prensa;
  // El servo lleva la leva de 0 a 180 grados y la devuelve: el piston baja
  // 2 x excentricidad y sube.
  animar(seg('prensa_ciclo', 1400), (u) => {
    const th = Math.PI * (1 - Math.cos(2 * Math.PI * u)) / 2;
    pr.leva.rotation.z = th;
    pr.piston.position.y = pr.zPiston - pr.exc * (1 - Math.cos(th));
  }, { retraso, dueno: pr });
}

// Cortina activa (usuario, 2026-09-26): la prensa no se queda congelada a
// mitad de camino; el servo lleva la leva a 0 grados (piston arriba) desde
// donde este y la deja ahi.
function subirPrensa() {
  const pr = P.prensa;
  cancelar(pr);
  const th0 = pr.leva.rotation.z;
  animar(seg('prensa_ciclo', 1400) / 2 * (th0 / Math.PI), (u) => {
    const th = th0 * (1 - suave(u));
    pr.leva.rotation.z = th;
    pr.piston.position.y = pr.zPiston - pr.exc * (1 - Math.cos(th));
  }, { dueno: pr });
}

const TEXTO_ALARMA = {
  tubo_lleno: 'tubo lleno sin vaso', faltan_vasos: 'faltan vasos',
  cuna_ocupada: 'la cuna del carro no está vacía: no se suelta', carga_no_confirmada: 'el infrarrojo de la cuna no ve el vaso soltado',
};

function procesarEventos() {
  if (!estado.eventos_tick || estado.tick === ultimoTick) return;
  const primero = ultimoTick === -1;
  ultimoTick = estado.tick;
  // La cinta de monedas se anima solo si de verdad avanzo en este ciclo
  // (vacia y sin carga se queda quieta: evento 'espera').
  if (!primero && estado.eventos_tick.some((e) => e.ev === 'paso' && e.src === 'linea')) moverCinta('monedas', seg('avance_casilla_monedas', 600));
  for (const e of estado.eventos_tick) {
    if (e.ev === 'prensa') ciclarPrensa(seg('avance_casilla_vasos', 1000));
    if (e.ev === 'cortina' && e.activa) subirPrensa();
    if (e.ev === 'alarma') bitacora.unshift(`<span class="src">  alarma</span> <b style="color:#e5534b">${TEXTO_ALARMA[e.tipo] || e.tipo}</b>`);
    if (e.ev === 'embalado') animarEmbalado(e);
    if (e.ev === 'presencia' && e.tipo_real === 'mano') P.manoCarga.hasta = performance.now() + 1200;
    const txt = describirEvento(e);
    if (txt) bitacora.unshift(`<span class="src">${e.src.padStart(9, ' ')}</span> ${txt}`);
  }
  bitacora.length = Math.min(bitacora.length, 12);
  document.getElementById('eventos').innerHTML = bitacora.join('<br>') || '<span class="tenue">sin eventos todavía</span>';
}

function describirEvento(e) {
  switch (e.ev) {
    case 'presencia': return e.tipo_real === 'mano' ? `#${e.casilla} <b style="color:#e5534b">mano en la carga</b> (el IR la ve)` : e.ocupada ? `#${e.casilla} cargado (${e.tipo_real})` : `#${e.casilla} casilla vacía`;
    case 'material': return `#${e.casilla} material: <b>${e.metal ? 'metal' : 'no metálico'}</b>`;
    case 'vision': return `#${e.casilla} visión (${(e.fotos || []).length || 1} fotos): ${e.diametro_mm.toFixed(1)} mm, ${e.clase} (${e.confianza.toFixed(2)})`;
    case 'rechazo': return `#${e.casilla} → <b style="color:#e5534b">bandeja de rechazo</b> (${e.causa || e.motivo})`;
    case 'elemento_final': return e.veredicto === 'aceptada' ? `#${e.casilla} aceptada <b>${e.clase}</b>` : `#${e.casilla} rechazada <b>${e.causa}</b>`;
    case 'llenado': return `vaso ${e.vaso}: ${e.cantidad} monedas`;
    case 'verificacion': return `vaso ${e.vaso} verificado (cámara): <b>${e.estado}</b>`;
    case 'tapa': return e.tapado ? `vaso ${e.vaso} <b>tapado</b>` : e.vacio && e.estado === 'valida' ? `vaso ${e.vaso} vacío: no se tapa (se desecha)` : `vaso ${e.vaso} sin tapa (${e.estado})`;
    case 'tapa_no_confirmada': return `<b style="color:#e5534b">vaso ${e.vaso}: la cámara no ve la tapa</b>`;
    case 'prensa': return `vaso ${e.vaso} prensado`;
    case 'descarga': return e.destino === 'vacio' ? `vaso ${e.vaso} vacío → <b>desechado</b>` : `vaso ${e.vaso} → <b>${e.destino}</b>`;
    case 'cortina': return e.activa ? `<b style="color:#e5534b">${e.fuente === 'camara_llenado' ? 'la cámara ve algo sobre el llenado' : 'cortina ACTIVA'}</b> (prensa arriba, no se suelta el lote)` : '<b style="color:#3fb68b">cortina despejada</b>';
    case 'desfase_corregido': return `<b style="color:#f2b134">cinta de ${e.cinta} corrida</b>: la cámara vio los separadores fuera de lugar, re-sincronizada`;
    case 'sabotaje_detectado': return `<b style="color:#e5534b">sabotaje detectado</b> vaso ${e.vaso}: ${e.motivo}${e.estacion === 'camara' ? ' (la cámara ve la casilla sin vaso)' : ''}`;
    case 'salto_casilla': return 'salto de casilla en la cinta de vasos';
    case 'espera': return `#${e.casilla} espera: no hay vaso válido`;
    case 'fin': return '<b>fin de la corrida</b>';
    case 'almacen': return e.tubo === 'otras' ? `#${e.casilla} ${e.clase} → <b>otras</b> (va a su propio vaso)` : `#${e.casilla} ${e.clase} → <b>tubo $${e.denominacion}</b> (${e.en_tubo})`;
    case 'presencia_recuperada': return `#${e.casilla} <b style="color:#f2b134">presencia recuperada</b> (E1 falló, E2 la vio)`;
    case 'canaleta_llena': return `<b style="color:#f2b134">canaleta llena</b>: el vaso ${e.vaso} espera en la descarga`;
    case 'carga': return `carro: se lleva el vaso ${e.vaso}`;
    case 'en_muelle': return 'carro en el muelle (encoders quietos contra el tope)';
    case 'salida': return 'carro: sale del muelle con el vaso';
    case 'obstaculo': return `<b style="color:#f2b134">carro: obstáculo</b> a ${Math.round(e.distancia_mm)} mm (3 lecturas seguidas)`;
    case 'evasion': return `carro: esquiva por la <b>${e.lado}</b>${e.izq_mm || e.der_mm ? ` (izq ${e.izq_mm ?? 'libre'} mm, der ${e.der_mm ?? 'libre'} mm)` : ' (los dos lados libres)'}`;
    case 'linea_recuperada': return 'carro: vuelve a la línea';
    case 'linea_perdida': return '<b style="color:#f2b134">carro: perdió la línea</b>, la busca girando';
    case 'meta': return '<b style="color:#3fb68b">carro en la META</b>: esperan que saquen el vaso';
    case 'entregado': return `vaso ${e.vaso} <b style="color:#3fb68b">entregado en la meta</b>`;
    case 'sin_enlace': return `<b style="color:#e5534b">radio del carro sin enlace</b>: termina la vuelta solo; no se le carga otro vaso`;
    case 'enlace_recuperado': return `radio del carro <b style="color:#3fb68b">con enlace</b> (${e.en_espera || 0} mensajes guardados llegan en orden)`;
    case 'estado': return `el carro informa: ${esc(e.estado)}, cuna ${e.cuna ? 'ocupada' : 'vacía'}`;
    case 'vaso_retirado': return 'el infrarrojo de la cuna ve que sacaron el vaso: vuelve';
    case 'vuelve_con_vaso': return '<b style="color:#f2b134">sin radio: vuelve con el vaso</b>';
    case 'devuelto': return `vaso ${e.vaso} devuelto al muelle y retirado a mano`;
    case 'vuelta': return 'carro: media vuelta, regresa solo';
    case 'marca_giro': return 'carro: marca de giro, entra de reversa al muelle';
    case 'error': return `<b style="color:#e5534b">carro detenido</b>: ${e.motivo}`;
    case 'soltar': return `escape: suelta el vaso ${e.vaso} a la cuna`;
    case 'embalado': return `<b style="color:#3fb68b">lote de ${e.denominacion === 'otras' ? 'otras' : '$' + e.denominacion}</b> → vaso ${e.vaso} (${e.cantidad} monedas)`;
    default: return null;
  }
}

function animarActuadores(dt) {
  if (P.manoCarga) P.manoCarga.grupo.visible = performance.now() < P.manoCarga.hasta;
  animarCarro(dt);
}

// El carro sigue la pose que calcula la simulacion (fisica real, un punto
// por ciclo de la cinta): entre dos poses se interpola suave, las ruedas
// giran lo que avanzo y queda el rastro del recorrido.
function animarCarro(dt) {
  const c = P.carroPose;
  if (!c || !P.carro || !c.camino) return;
  const n = c.camino.length;
  const u = Math.min(1, (performance.now() - c.t0) / c.dur) * (n - 1);
  const i = Math.min(n - 2, Math.floor(u)), f = n > 1 ? u - i : 0;
  const a = c.camino[Math.max(0, i)], b = c.camino[Math.min(n - 1, i + 1)];
  let dr = b[2] - a[2]; dr = Math.atan2(Math.sin(dr), Math.cos(dr));
  const x0 = c.ox, y0 = c.oy;
  c.ox = a[0] + (b[0] - a[0]) * f; c.oy = a[1] + (b[1] - a[1]) * f; c.or = a[2] + dr * f;
  P.carro.position.copy(Vxyz(c.ox, c.oy, 0));
  P.carro.rotation.y = c.or;
  const avance = Math.hypot(c.ox - x0, c.oy - y0);
  for (const r of P.ruedas || []) r.rotation.y += avance / (G.vehiculo.diametro_rueda / 2);
  if (avance > 0.0005) agregarRastro(c.ox, c.oy);
}

function agregarRastro(x, y) {
  if (!P.rastro) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(3 * 6000), 3));
    geo.setDrawRange(0, 0);
    P.rastro = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0xf2b134, transparent: true, opacity: 0.8 }));
    P.rastro.frustumCulled = false;
    P.rastroN = 0;
    escena.add(P.rastro);
  }
  const pos = P.rastro.geometry.attributes.position;
  const n = P.rastroN;
  const p = Vxyz(x, y, 0.004);
  if (n > 0) {
    const dx = pos.getX(n - 1) - p.x, dz = pos.getZ(n - 1) - p.z;
    if (dx * dx + dz * dz < 0.0001) return;   // un punto cada ~1 cm
  }
  if (n >= 6000) return;
  pos.setXYZ(n, p.x, p.y, p.z);
  P.rastroN = n + 1;
  P.rastro.geometry.setDrawRange(0, P.rastroN);
  pos.needsUpdate = true;
}

// ---------------------------------------------------------------------------
// camara: vistas predefinidas y vuelo suave
// ---------------------------------------------------------------------------

let vuelo = null;

function vista(nombre) {
  const em = G.cinta_monedas.estaciones.map((e) => V(e.posicion));
  const ev = G.cinta_vasos.estaciones.map((e) => V(e.posicion));
  const centroM = em[0].clone().lerp(em[em.length - 1], 0.5);
  const centroV = ev[0].clone().lerp(ev[4], 0.5);
  const c = P.canaleta;
  const pista = new THREE.Box3().setFromPoints(G.pista.linea.map((q) => Vxyz(q[0], q[1], 0)));
  const centroP = pista.getCenter(new THREE.Vector3());
  const almacen = Vxyz(G.almacen.centro[0], G.almacen.centro[1], G.almacen.tubo_z_arriba - 0.03);
  const vistas = {
    // Incluye la laptop y la nube del asistente (detras de la planta, a la izquierda de la pista).
    todo: [centroP.clone().add(new THREE.Vector3(-0.55, 0.05, -0.12)), new THREE.Vector3(-1.1, 1.65, 1.85)],
    planta: [centroV.clone().lerp(centroM, 0.5).add(new THREE.Vector3(0.05, 0, 0.05)), new THREE.Vector3(0.45, 0.45, 0.75)],
    carga: [em[0], new THREE.Vector3(-0.1, 0.14, 0.24)],
    monedas: [centroM, new THREE.Vector3(0.02, 0.22, 0.4)],
    vision: [em[4], new THREE.Vector3(0.06, 0.12, 0.22)],
    almacen: [almacen, new THREE.Vector3(0.12, 0.12, 0.26)],
    vasos: [centroV.clone().add(new THREE.Vector3(0, 0.07, 0)), new THREE.Vector3(0.02, 0.2, 0.52)],
    tapa: [ev[2].clone().lerp(ev[3], 0.5).add(new THREE.Vector3(0, 0.09, 0)), new THREE.Vector3(0.05, 0.1, 0.32)],
    canaleta: [c.ini.clone().lerp(c.fin, 0.55), new THREE.Vector3(0.42, 0.2, 0.3)],
    pista: [centroP, new THREE.Vector3(0.0, 1.9, 1.2)],
    // Los dos sensores de material se ven desde abajo de la cinta.
    material: [em[0].clone().lerp(em[1], 0.5).add(new THREE.Vector3(0, -0.04, 0)), new THREE.Vector3(0.06, -0.07, 0.2)],
    caja: [Vxyz(P.caja.bx, P.caja.by, 0.02), new THREE.Vector3(0, 0.3, 0.16)],
    // De frente a la pantalla de la laptop (la pantalla mira hacia +z de three).
    asistente: [P.asistente ? P.asistente.panel.getWorldPosition(new THREE.Vector3()) : centroP,
      new THREE.Vector3(0, 0.72 * Math.sin(LAPTOP.apertura), 0.72 * Math.cos(LAPTOP.apertura))],
    carro: [P.carro ? P.carro.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 0.04, 0)) : centroP,
      new THREE.Vector3(0.16, 0.14, 0.2)],
  };
  document.querySelectorAll('[data-vista]').forEach((b) => b.classList.toggle('activo', b.dataset.vista === nombre));
  const [objetivo, desplazamiento] = vistas[nombre] || vistas.todo;
  // El panel lateral tapa la izquierda de la pantalla: se corre el punto de
  // mira hacia -x (en proporcion a la distancia) para que la zona quede a la
  // derecha, a la vista.
  const panelVisible = !document.getElementById('panel').classList.contains('oculto') && window.innerWidth > 900;
  const corrimiento = panelVisible ? new THREE.Vector3(-desplazamiento.length() * 0.22, 0, 0) : new THREE.Vector3();
  volarA(objetivo.clone().add(corrimiento), objetivo.clone().add(corrimiento).add(desplazamiento), { seguir: nombre === 'carro' });
}

function volarA(objetivo, posicion, { seguir = false } = {}) {
  seguirCarro = seguir && P.carroGrupo ? { ultimo: P.carroGrupo.getWorldPosition(new THREE.Vector3()) } : null;
  vuelo = { t: 0, desdeT: controles.target.clone(), hastaT: objetivo, desdeP: camara.position.clone(), hastaP: posicion };
}

// Si se enfoco algo del carro, la camara lo sigue mientras avanza (hasta que
// el usuario mueva la vista o elija otra).
let seguirCarro = null;
controles.addEventListener('start', () => { seguirCarro = null; });
function animarVuelo(dt) {
  if (seguirCarro && P.carroGrupo) {
    const ahora = P.carroGrupo.getWorldPosition(new THREE.Vector3());
    const d = ahora.clone().sub(seguirCarro.ultimo);
    seguirCarro.ultimo = ahora;
    if (d.lengthSq() > 0) {
      if (vuelo) { vuelo.hastaT.add(d); vuelo.hastaP.add(d); }
      else { controles.target.add(d); camara.position.add(d); }
    }
  }
  if (!vuelo) return;
  vuelo.t = Math.min(1, vuelo.t + dt / 0.9);
  const s = vuelo.t * vuelo.t * (3 - 2 * vuelo.t);
  controles.target.lerpVectors(vuelo.desdeT, vuelo.hastaT, s);
  camara.position.lerpVectors(vuelo.desdeP, vuelo.hastaP, s);
  if (vuelo.t >= 1) vuelo = null;
}

function enfocarSensor(id) {
  const s = SENS[id];
  if (!s) return;
  const mallas = mallasDeSensor(id);
  if (mallas.length) {
    encuadrar(mallas, { desdeAbajo: !!(s.meta.geometria && s.meta.geometria.bajo_cinta) });
    return;
  }
  const p = new THREE.Vector3();
  s.marcador.getWorldPosition(p);
  volarA(p, p.clone().add(new THREE.Vector3(0.08, 0.1, 0.16)));
}

document.querySelectorAll('[data-vista]').forEach((b) => b.addEventListener('click', () => vista(b.dataset.vista)));

// Clic en un sensor -> lo selecciona.
const rayo = new THREE.Raycaster();
renderer.domElement.addEventListener('click', (ev) => {
  const m = new THREE.Vector2((ev.clientX / window.innerWidth) * 2 - 1, -(ev.clientY / window.innerHeight) * 2 + 1);
  rayo.setFromCamera(m, camara);
  const golpes = rayo.intersectObjects(escena.children, true);
  if (golpes.find((g) => g.object.userData.asistente)) return vista('asistente');
  const golpe = golpes.find((g) => g.object.userData.sensorId && g.object.visible);
  if (golpe) seleccionarSensor(golpe.object.userData.sensorId, true);
});

// ---------------------------------------------------------------------------
// panel lateral
// ---------------------------------------------------------------------------

const contenido = document.getElementById('contenido');
document.getElementById('btnPanel').addEventListener('click', () => {
  const oculto = document.getElementById('panel').classList.toggle('oculto');
  document.getElementById('btnPanel').classList.toggle('activo', !oculto);
});
document.querySelectorAll('[data-pestana]').forEach((b) => b.addEventListener('click', () => {
  pestana = b.dataset.pestana;
  document.querySelectorAll('[data-pestana]').forEach((x) => x.classList.toggle('activo', x === b));
  if (pestana === 'vivo') { resaltados.clear(); seleccion = { tipo: null, valor: null }; }
  if (pestana !== 'componentes') compResaltado = null;
  contenido.innerHTML = '';
  pintarPanel();
}));

const esc = (t) => String(t ?? '').replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

// Pestana "Asistente": espejo de solo lectura de la conversacion del
// dashboard (fase 7) y de lo que paso con cada orden que dio.
let asistenteDatos = null;
let ultimaConsultaAsistente = 0;
async function consultarAsistente() {
  if (MODO_DEMO) return;
  const ahora = performance.now();
  const pensando = asistenteDatos && asistenteDatos.pensando;
  if (ahora - ultimaConsultaAsistente < (pensando ? 500 : 1500)) return;
  ultimaConsultaAsistente = ahora;
  try {
    asistenteDatos = await cargarJSON(BASE + 'api/asistente');
    const n = asistenteDatos.mensajes.length ? asistenteDatos.mensajes[asistenteDatos.mensajes.length - 1].ts : '';
    const ultimo = asistenteDatos.mensajes[asistenteDatos.mensajes.length - 1];
    // Solo la respuesta de DeepSeek baja de la nube (el modelo local y las reglas no salen del portatil).
    if (P.asistente && P.asistente.mensajes !== -1 && n !== P.asistente.mensajes && ultimo && ultimo.modo === 'deepseek') pulsoAsistente();
    const pensaba = P.asistente && P.asistente.pensando;
    P.asistente.pensando = asistenteDatos.pensando ? asistenteDatos.pensando.proveedor : null;
    if (P.asistente && (n !== P.asistente.mensajes || pensaba !== P.asistente.pensando)) dibujarPanelAsistente(asistenteDatos);
    if (P.asistente) P.asistente.mensajes = n;
  } catch (e) { /* sin supervisor: se reintenta */ }
}

function pintarPanel() {
  if (pestana === 'componentes') return pintarComponentes();
  if (pestana === 'pasos') return pintarPasos();
  if (pestana === 'sensores') return pintarSensores();
  pintarVivo();
}

function pintarVivo() {
  // Los controles (botones) se construyen UNA vez; cada
  // segundo solo se actualiza #vivoDatos. Antes se reconstruia todo el
  // panel y el menu desplegable se cerraba solo mientras se usaba.
  if (!contenido.querySelector('#vivoDatos')) {
    contenido.innerHTML = `
      <h3>Línea en vivo</h3>
      <div id="vivoDatos"></div>
      <div class="grupo-botones controles">
        <h4>Línea</h4>
        <div class="fila4">
          <button data-orden="iniciar" title="Corrida nueva con la prueba completa">▶ Iniciar</button>
          <button data-orden="pausar" title="Pausa la línea">⏸ Pausa</button>
          <button data-orden="reanudar" title="Sigue después de una pausa">⏵ Seguir</button>
          <button data-orden="paro" class="peligro" title="Paro de emergencia: todo queda quieto; sale con Iniciar">⛔ Paro</button>
        </div>
      </div>
      <div class="grupo-botones controles">
        <h4>Sabotajes a los vasos</h4>
        <div class="fila2">
          <button data-sab="retirar_vaso" data-pide="vaso_vl">Retirar un vaso</button>
          <button data-sab="cambiar_vaso" data-pide="vaso_vl">Cambiar por figura</button>
          <button data-sab="vaso_igual" data-pide="vaso_vl">Cambiar por vaso igual</button>
          <button data-sab="vaso_con_algo" data-pide="corriendo">Vaso con algo adentro</button>
        </div>
      </div>
      <div class="grupo-botones controles">
        <h4>Manos en la línea</h4>
        <div class="fila2">
          <button data-sab="mano_carga" data-pide="corriendo">✋ En la carga</button>
          <button data-sab="mano_llenado" data-pide="sin_mano">✋ Sobre el llenado</button>
          <button data-sab="intruso" data-pide="corriendo" id="botonIntruso">✋ En tapa/prensa</button>
          <button data-sab="mano_saca_vaso" data-pide="vaso_tp">✋ Saca un vaso</button>
        </div>
      </div>
      <div class="grupo-botones controles">
        <h4>Radio del carro</h4>
        <div class="fila1">
          <button data-sab="radio" data-pide="carro" id="botonRadio" title="Corta o reconecta la radio (ESP-NOW) del carro">📡 Cortar la radio del carro</button>
        </div>
      </div>
      <div class="grupo-botones controles">
        <h4>Fin de turno</h4>
        <div class="fila1">
          <button data-orden="embalar_parciales" data-pide="guardado" title="Empaca lo que quedó en los tubos (cada vaso de una sola denominación)">📦 Embalar lo guardado</button>
        </div>
      </div>
      <div id="respuestaOrden" class="respuesta-orden"></div>
      <div class="tenue demo-aviso" style="display:none;font-size:.8rem;margin-bottom:10px">Demo grabada: los botones están desactivados. Para manejar la línea, abrir <code>visor.bat</code> en el PC.</div>
      <dt class="tenue" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.05em">Sensores de la planta</dt>
      <div id="vivoLeds" style="margin-top:6px;line-height:1.8"></div>`;
    contenido.querySelectorAll('[data-orden]').forEach((b) => b.addEventListener('click', () => {
      const orden = { cmd: b.dataset.orden };
      // Una sola prueba (prueba_completa): el supervisor la usa por defecto.
      if (orden.cmd === 'iniciar') orden.escenario = 'prueba_completa';
      enviarOrden(orden);
    }));
    contenido.querySelectorAll('[data-sab]').forEach((b) => b.addEventListener('click', () => {
      let tipo = b.dataset.sab;
      if (tipo === 'intruso') tipo = estado && estado.intruso ? 'intruso_off' : 'intruso_on';
      if (tipo === 'radio') tipo = estado && estado.carro && estado.carro.radio && !estado.carro.radio.conectada ? 'radio_on' : 'radio_off';
      enviarOrden({ cmd: 'sabotaje', tipo });
    }));
    if (MODO_DEMO) {
      contenido.querySelectorAll('.controles button, .controles select').forEach((b) => { b.disabled = true; b.style.opacity = 0.45; });
      contenido.querySelector('.demo-aviso').style.display = 'block';
    }
  }
  actualizarVivo();
}

// Cada boton se habilita solo cuando puede hacer algo; si no, dice por que
// (al pasar el mouse). Y la respuesta del supervisor a la ultima orden.
const MOTIVO = {
  corriendo: 'La línea no está corriendo',
  vaso_vl: 'Hace falta un vaso en verificación o en llenado',
  vaso_tp: 'Hace falta un vaso en tapa o en prensa (y que no haya otra mano)',
  sin_mano: 'Ya hay una mano en la línea',
  guardado: 'Los tubos están vacíos',
  carro: 'Sin carro simulado (carro de reemplazo)',
};
let ultimaRespuesta = 0;
function actualizarBotones(e) {
  const corre = e.linea === 'corriendo';
  const cv = e.casillas_vasos || [];
  const mano = e.mano_sacando !== null && e.mano_sacando !== undefined;
  const puede = {
    corriendo: corre,
    vaso_vl: corre && !!(cv[0] || cv[1]),
    vaso_tp: corre && !!(cv[2] || cv[3]) && !mano,
    sin_mano: corre && !mano,
    guardado: (e.almacen_valor || 0) > 0,
    carro: !!(e.carro && e.carro.radio) && (corre || e.linea === 'pausada'),
  };
  contenido.querySelectorAll('[data-pide]').forEach((b) => {
    const ok = MODO_DEMO ? false : puede[b.dataset.pide];
    b.disabled = !ok;
    b.title = ok ? '' : (MODO_DEMO ? 'Demo grabada' : MOTIVO[b.dataset.pide]);
  });
  const orden = { pausar: corre, reanudar: e.linea === 'pausada', paro: corre || e.linea === 'pausada' };
  contenido.querySelectorAll('[data-orden]').forEach((b) => {
    if (b.dataset.orden in orden) b.disabled = MODO_DEMO || !orden[b.dataset.orden];
  });
  const bi = contenido.querySelector('#botonIntruso');
  if (bi) bi.textContent = e.intruso ? '✋ Quitar la mano (tapa/prensa)' : '✋ En tapa/prensa';
  const br = contenido.querySelector('#botonRadio');
  if (br) br.textContent = e.carro && e.carro.radio && !e.carro.radio.conectada ? '📡 Reconectar la radio del carro' : '📡 Cortar la radio del carro';
  const r = e.ultima_orden;
  const caja = contenido.querySelector('#respuestaOrden');
  if (caja && r && r.n !== ultimaRespuesta) {
    ultimaRespuesta = r.n;
    caja.textContent = (r.ok ? '✔ ' : '✖ ') + r.detalle;
    caja.className = 'respuesta-orden visible ' + (r.ok ? 'ok' : 'no');
    clearTimeout(caja._t);
    caja._t = setTimeout(() => { caja.className = 'respuesta-orden'; }, 7000);
  }
}

function actualizarVivo() {
  const e = estado || {};
  actualizarBotones(e);
  const vs = e.vasos_salida || [];
  const enVasos = [...(e.casillas_vasos || []).filter(Boolean), ...vs];
  const monedas = enVasos.reduce((a, v) => a + (v.cantidad || 0), 0);
  const valor = enVasos.reduce((a, v) => a + (v.valor || 0), 0);
  const rech = (e.salidas || {}).rechazo || [];
  const porCausa = {};
  for (const r of rech) porCausa[r.causa || 'sin registro'] = (porCausa[r.causa || 'sin registro'] || 0) + 1;
  const al = e.almacen || {};
  const tubos = DENOMINACIONES.map((d) => `$${d.toLocaleString('es-CO')}: <b>${al[String(d)] || 0}</b>`).join(' · ') + ` · otras: <b>${al.otras || 0}</b>`;
  document.getElementById('vivoDatos').innerHTML = `
    <div class="tenue">Escenario <b>${esc(e.escenario || '—')}</b> · quedan ${e.pendientes ?? '—'} por cargar</div>
    <dl class="detalle">
      <dt>En vasos</dt><dd>${monedas} monedas · $${valor.toLocaleString('es-CO')}</dd>
      <dt>Guardado en tubos (lote de ${e.monedas_por_vaso ?? '—'})</dt><dd>${tubos}<br><span class="tenue">$${(e.almacen_valor || 0).toLocaleString('es-CO')} guardados · ninguna moneda aceptada se descarta</span></dd>
      <dt>Rechazos (una sola bandeja)</dt><dd>${rech.length}${rech.length ? ' · ' + Object.entries(porCausa).map(([c, n]) => `${esc(c)}: ${n}`).join(' · ') : ''}</dd>
      <dt>Errores de sensor (simulados)</dt><dd>${e.errores_sensores_activos ? `colombianas rechazadas por error: ${(e.errores_filtrado || {}).falsos_rechazos || 0} · no colombianas aceptadas: ${(e.errores_filtrado || {}).falsas_aceptaciones || 0} · vaso equivocado: ${(e.errores_filtrado || {}).clase_equivocada || 0}` : 'sensores perfectos en esta corrida'}</dd>
      <dt>Vasos</dt><dd>Entregados: ${vs.filter((v) => v.destino === 'entrega').length} · rechazados: ${vs.filter((v) => v.destino === 'rechazo').length} · vacíos desechados: ${vs.filter((v) => v.destino === 'vacio').length}<br><span class="tenue">En la canaleta: ${(e.canaleta || []).length} de ${G.canaleta.capacidad}${e.vaso_esperando_canaleta ? ` · el vaso ${e.vaso_esperando_canaleta} espera en la descarga` : ''} ${e.carro ? ` · carro: ${esc(e.carro.fase)} (${esc(e.carro.estado)})${e.carro.vaso_id ? `, lleva el vaso ${e.carro.vaso_id}` : ''}` : ' (sin carro simulado: uno de reemplazo se los lleva)'}</span>${e.carro && e.carro.radio ? `<br><span class="tenue">Radio del carro: ${e.carro.radio.enlace ? '<b style="color:#3fb68b">con enlace</b>' : '<b style="color:#e5534b">sin enlace</b>'}${e.carro.radio.en_espera ? ` · ${e.carro.radio.en_espera} mensajes guardados en el carro` : ''} · cuna según el carro: ${e.carro.radio.cuna_reportada === null ? 'sin saber (no se le carga)' : e.carro.radio.cuna_reportada ? 'ocupada' : 'vacía'}${e.carro.radio.enlace ? '' : ' (último dato: no se le carga hasta que informe de nuevo)'}</span>` : ''}</dd>
    </dl>`;
  document.getElementById('vivoLeds').innerHTML = G.sensores.filter((s) => s.geometria).map((s) => {
    const on = sensorActivo(s.id);
    const cls = on ? (sensorEnAlarma(s.id) ? 'led alarma' : 'led on') : 'led';
    return `<div><span class="${cls}"></span><span class="n mono">${s.numero}</span>${esc(s.nombre)}</div>`;
  }).join('');
}

function pintarPasos() {
  const sel = seleccion.tipo === 'paso' ? seleccion.valor : null;
  const lista = PASOS.map((p) => `
    <div class="item ${sel === p.numero ? 'sel' : ''}" data-paso="${p.numero}">
      <span class="rev ${p.revision}">${p.revision}</span><span class="n">${p.numero}</span>${esc(p.titulo)}
    </div>${sel === p.numero ? detallePaso(p) : ''}`).join('');
  contenido.innerHTML = `<h3>Paso a paso</h3>
    <p class="tenue" style="margin-top:0">Cada punto de la secuencia (sección 5). Al elegir uno, la cámara va a esa zona y se resaltan sus sensores.</p>${lista}`;
  contenido.querySelectorAll('[data-paso]').forEach((d) => d.addEventListener('click', () => seleccionarPaso(Number(d.dataset.paso))));
  contenido.querySelectorAll('[data-ir]').forEach((b) => b.addEventListener('click', (ev) => { ev.stopPropagation(); seleccionarPaso(Number(b.dataset.ir)); }));
  const elegido = contenido.querySelector('.item.sel');
  if (elegido) elegido.scrollIntoView({ block: 'nearest' });
}

function detallePaso(p) {
  const sens = (p.sensores || []).map((n) => G.sensores.find((s) => s.numero === n)).filter(Boolean)
    .map((s) => `<span class="n mono">${s.numero}</span>${esc(s.nombre)}`).join('<br>') || '<span class="tenue">ninguno (usa el registro)</span>';
  const preguntas = (p.preguntas || []).map((q) => `<li>${esc(q)}</li>`).join('');
  return `<dl class="detalle">
    <dt>Qué pasa</dt><dd>${esc(p.que_pasa)}</dd>
    <dt>Sensores</dt><dd>${sens}</dd>
    <dt>Entra</dt><dd>${esc(p.entra)}</dd>
    <dt>Decide</dt><dd>${esc(p.decide)}</dd>
    <dt>Sale</dt><dd>${esc(p.sale)}</dd>
    ${p.mensaje ? `<dt>Mensaje</dt><dd><code>${esc(p.mensaje)}</code></dd>` : ''}
    ${p.como_esta_hoy ? `<dt>Cómo está hoy</dt><dd>${esc(p.como_esta_hoy)}</dd>` : ''}
    ${p.replicacion ? `<dt>Para replicarlo en la vida real</dt><dd>${esc(p.replicacion)}</dd>` : ''}
    ${preguntas ? `<dt>Por revisar con el grupo</dt><dd><ul class="preg">${preguntas}</ul></dd>` : ''}
    ${p.nota_revision ? `<dt>Nota de revisión</dt><dd>${esc(p.nota_revision)}</dd>` : ''}
    <dd style="margin-top:10px;display:flex;gap:6px">
      ${p.numero > 1 ? `<button data-ir="${p.numero - 1}">← ${p.numero - 1}</button>` : ''}
      ${p.numero < PASOS.length ? `<button data-ir="${p.numero + 1}">${p.numero + 1} →</button>` : ''}
    </dd></dl>`;
}

function seleccionarPaso(n) {
  const p = PASOS.find((x) => x.numero === n);
  if (!p) return;
  seleccion = { tipo: 'paso', valor: n };
  resaltados.clear();
  for (const num of p.sensores || []) {
    const s = G.sensores.find((x) => x.numero === num);
    if (s) resaltados.add(s.id);
  }
  vista(p.zona);
  pintarPasos();
}

function pintarSensores() {
  const sel = seleccion.tipo === 'sensor' ? seleccion.valor : null;
  const grupos = {};
  for (const s of G.sensores) (grupos[s.subsistema] ||= []).push(s);
  let html = '<h3>Sensores</h3><p class="tenue" style="margin-top:0">Qué recibe cada sensor, qué entrega y qué mensaje termina llegando al PC. Clic para verlo en la escena.</p>';
  for (const [nombre, lista] of Object.entries(grupos)) {
    html += `<div class="tenue" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;margin:10px 0 6px">${esc(nombre)}</div>`;
    for (const s of lista) {
      const on = sensorActivo(s.id);
      const cls = on ? (sensorEnAlarma(s.id) ? 'led alarma' : 'led on') : 'led';
      html += `<div class="item ${sel === s.id ? 'sel' : ''}" data-sensor="${s.id}"><span class="${cls}"></span><span class="n">${s.numero}</span>${esc(s.nombre)}</div>`;
      if (sel === s.id) {
        html += `<dl class="detalle">
          <dt>Dónde</dt><dd>${esc(s.estacion)}</dd>
          <dt>Modelo propuesto</dt><dd>${esc(s.modelo)}</dd>
          <dt>Qué lo activa</dt><dd>${esc(s.fenomeno)}</dd>
          <dt>Recibe</dt><dd>${esc(s.entrada)}</dd>
          <dt>Entrega</dt><dd>${esc(s.salida)}</dd>
          <dt>Lectura ahora</dt><dd><span class="${cls}"></span>${on ? 'activo' : 'inactivo'}</dd>
          <dt>Mensaje al PC</dt><dd><code>${esc(s.mensaje)}</code></dd>
          <dt>Cómo se simula</dt><dd>${esc(s.simulacion)}</dd>
          <dt>Rango</dt><dd>${esc(s.rango)}</dd>
          <dt>Tiempo de respuesta</dt><dd>${esc(s.tiempo_respuesta)}</dd>
          <dt>Error típico</dt><dd>${esc(s.error_tipico)}</dd>
          <dt>Cómo mitigarlo</dt><dd>${esc(s.mitigacion)}</dd>
          <dt>Conexión</dt><dd>${esc(s.conexion)}</dd></dl>`;
      }
    }
  }
  contenido.innerHTML = html;
  contenido.querySelectorAll('[data-sensor]').forEach((d) => d.addEventListener('click', () => seleccionarSensor(d.dataset.sensor, true)));
}

function pintarComponentes() {
  const sel = compResaltado;
  const lista = G.componentes || [];
  const total = lista.reduce((a, c) => a + c.cantidad, 0);
  const servos = lista.filter((c) => c.id.startsWith('servo')).reduce((a, c) => a + c.cantidad, 0);
  let html = `<h3>Componentes</h3><p class="tenue" style="margin-top:0">Lista de materiales del proyecto: ${total} piezas
    (+ ${G.sensores.length} sensores). ${servos} servos en el PCA9685 de 16 canales. Clic para verlo en la escena.</p>
    <p class="tenue" style="margin-top:0;font-size:.74rem"><span class="rev simulado">simulado</span> la simulación hace lo que hace
    la pieza · <span class="rev efecto">efecto simulado</span> su efecto lo hace otra pieza en la simulación ·
    <span class="rev">solo visual</span> nada en la simulación depende de ella. Además: <span class="rev chica">3D</span> está
    modelada y <span class="rev chica">N hilos</span> tiene su conexionado pin a pin.</p>`;
  for (const cat of G.categorias_componentes || []) {
    const deCat = lista.filter((c) => c.categoria === cat);
    if (cat === 'Sensores') {
      html += `<div class="tenue" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;margin:10px 0 6px">Sensores (${G.sensores.length})</div>`;
      for (const s of G.sensores) {
        const en3d = mallasDeSensor(s.id).length > 0;
        html += `<div class="item" data-sensorcomp="${s.id}"><span class="rev simulado">simulado</span>`
          + (s.hilos ? `<span class="rev chica">${s.hilos} hilos</span>` : '')
          + (en3d ? '<span class="rev chica">3D</span>' : '')
          + `<span class="n">${s.numero}</span>${esc(s.nombre)}</div>`;
      }
      html += `<div class="item" data-irsensores="1"><span class="n">→</span>Ver cada sensor con su error y mitigación</div>`;
      continue;
    }
    html += `<div class="tenue" style="font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;margin:10px 0 6px">${esc(cat)}</div>`;
    for (const c of deCat) {
      const clase = { propia: 'simulado', efecto: 'efecto', no: '' }[c.simulacion] ?? '';
      const insignias = `<span class="rev ${clase}">${esc(c.estado)}</span>`
        + (c.hilos ? `<span class="rev chica">${c.hilos} hilos</span>` : '')
        + (COMP[c.id] ? '<span class="rev chica">3D</span>' : '<span class="rev pendiente chica">sin 3D</span>');
      html += `<div class="item ${sel === c.id ? 'sel' : ''}" data-comp="${c.id}">${insignias}`
        + `<span class="n">${c.cantidad}×</span>${esc(c.nombre)}</div>`;
      if (sel === c.id) {
        html += `<dl class="detalle"><dt>Modelo propuesto</dt><dd>${esc(c.modelo)}</dd>
          <dt>Para qué sirve</dt><dd>${esc(c.funcion)}</dd>
          <dt>Estado en la simulación</dt><dd>${esc(c.estado)}${COMP[c.id] ? '' : ' (todavía no dibujado)'}</dd>
          <dt>Conexión (pin a pin)</dt><dd>${esc(c.conexion)}</dd></dl>`;
      }
    }
  }
  contenido.innerHTML = html;
  contenido.querySelectorAll('[data-comp]').forEach((d) => d.addEventListener('click', () => seleccionarComponente(d.dataset.comp)));
  contenido.querySelectorAll('[data-sensorcomp]').forEach((d) => d.addEventListener('click', () => {
    resaltados.clear();
    resaltados.add(d.dataset.sensorcomp);
    enfocarSensor(d.dataset.sensorcomp);
  }));
  const ir = contenido.querySelector('[data-irsensores]');
  if (ir) ir.addEventListener('click', () => {
    pestana = 'sensores';
    document.querySelectorAll('[data-pestana]').forEach((x) => x.classList.toggle('activo', x.dataset.pestana === 'sensores'));
    pintarPanel();
  });
}

// Lleva la camara a ver `mallas` enteras: la distancia sale del tamaño
// real de la pieza (y del campo de vision de la camara), y la mira es desde
// afuera de la planta hacia adentro, un poco desde arriba (o desde abajo si
// `desdeAbajo`), para que nada de la planta la tape.
function encuadrar(mallas, { desdeAbajo = false } = {}) {
  const caja = new THREE.Box3();
  escena.updateMatrixWorld(true);
  let enCarro = false;
  for (const o of mallas) o.traverse((m) => {
    if (!m.isMesh || m.userData.campo || m.isInstancedMesh) return;
    // Lineas guia, conos y LED (materiales basicos) no cuentan para el tamaño.
    if (m.material && (m.material.isMeshBasicMaterial || (m.material.transparent && m.material.opacity < 0.3))) return;
    caja.expandByObject(m);
    for (let p = m; p; p = p.parent) if (p === P.carroGrupo) enCarro = true;
  });
  if (caja.isEmpty()) return;
  const centro = caja.getCenter(new THREE.Vector3());
  const radio = Math.max(0.015, caja.getSize(new THREE.Vector3()).length() / 2);
  const fov = THREE.MathUtils.degToRad(camara.fov);
  const dist = THREE.MathUtils.clamp(radio / Math.sin(fov / 2) * 1.25, 0.09, 2.6);
  let dir;
  if (desdeAbajo) {
    // Debajo de la cinta: desde abajo, del lado del operador (-y).
    dir = new THREE.Vector3(0.3, -0.4, 0.87).normalize();
  } else {
    if (enCarro) {
      // En el carro: de costado (el izquierdo), algo desde arriba y un poco
      // hacia el lado de la pieza: el vaso colgado no tapa.
      const q = P.carroGrupo.getWorldQuaternion(new THREE.Quaternion());
      const local = P.carroGrupo.worldToLocal(centro.clone());
      const izquierda = new THREE.Vector3(0, 0, -1).applyQuaternion(q);
      const adelante = new THREE.Vector3(1, 0, 0).applyQuaternion(q);
      dir = izquierda.multiplyScalar(0.85).addScaledVector(adelante, Math.sign(local.x || 1) * 0.35)
        .add(new THREE.Vector3(0, 0.42, 0)).normalize();
      volarA(centro, centro.clone().addScaledVector(dir, Math.max(dist, 0.24)), { seguir: true });
      return;
    }
    // Centro de la planta: se mira desde afuera, desde arriba.
    const ref = enCarro ? P.carroGrupo.getWorldPosition(new THREE.Vector3())
      : V(G.cinta_vasos.estaciones[2].posicion).lerp(V(G.cinta_monedas.estaciones[1].posicion), 0.5);
    let afuera = centro.clone().sub(ref).setY(0);
    if (afuera.lengthSq() < 1e-5) afuera = new THREE.Vector3(1, 0, 0).applyQuaternion(enCarro ? P.carroGrupo.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion());
    afuera.normalize();
    dir = afuera.multiplyScalar(enCarro ? 0.6 : 0.72).add(new THREE.Vector3(0, enCarro ? 0.8 : 0.62, 0)).normalize();
  }
  volarA(centro, centro.clone().addScaledVector(dir, Math.max(dist, enCarro ? 0.16 : 0.09)), { seguir: enCarro });
}

function mallasDeSensor(id) {
  const out = [];
  escena.traverse((m) => { if (m.isMesh && m.userData.sensorId === id && !m.userData.campo) out.push(m); });
  return out;
}

function seleccionarComponente(id) {
  compResaltado = compResaltado === id ? null : id;
  resaltados.clear();
  if (compResaltado && COMP[id]) encuadrar(COMP[id]);
  pintarComponentes();
}

// Resalta (pulso ambar) las mallas del componente elegido.
let compPintado = null;
function resaltarComponente(t) {
  if (compPintado && compPintado !== compResaltado) {
    for (const o of COMP[compPintado] || []) o.traverse((m) => { if (m.isMesh && m.material.emissive) m.material.emissive.setHex(0x000000); });
    compPintado = null;
  }
  if (!compResaltado) return;
  const k = 0.35 + 0.3 * Math.sin(t * 5);
  for (const o of COMP[compResaltado] || []) o.traverse((m) => {
    if (m.isMesh && m.material.emissive) { m.material.emissive.setHex(COLOR.ambar); m.material.emissiveIntensity = k; }
  });
  compPintado = compResaltado;
}

function seleccionarSensor(id, enfocar) {
  seleccion = { tipo: 'sensor', valor: id };
  resaltados.clear();
  resaltados.add(id);
  if (pestana !== 'sensores') {
    pestana = 'sensores';
    document.querySelectorAll('[data-pestana]').forEach((x) => x.classList.toggle('activo', x.dataset.pestana === 'sensores'));
    document.getElementById('panel').classList.remove('oculto');
  }
  if (enfocar) enfocarSensor(id);
  pintarSensores();
}

async function enviarOrden(orden) {
  if (MODO_DEMO) return;
  try {
    await fetch(BASE + 'api/orden', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(orden) });
  } catch (e) { /* el aviso de conexion ya lo muestra */ }
}

// ---------------------------------------------------------------------------
// estado en vivo
// ---------------------------------------------------------------------------

let fallos = 0;
let ultimoPintado = 0;
let tickAnterior = -1;

// Corrida nueva (el tick vuelve a empezar): se borra todo lo dinamico.
function limpiarCorrida() {
  ANIMS.length = 0;
  if (P.rastro) { P.rastroN = 0; P.rastro.geometry.setDrawRange(0, 0); }
  for (const f of fichas.values()) escena.remove(f.grupo);
  for (const v of vasos.values()) escena.remove(v.grupo);
  fichas.clear(); vasos.clear();
  for (const c of Object.values(CINTAS)) { c.moviendo = false; c.seps.forEach((m, i) => { m.position.x = c.base[i]; m.visible = i > 0; }); }
  if (P.carrusel) { P.carrusel.angulo = 0; P.carrusel.objetivo = 0; P.carrusel.libre = 0; P.carrusel.grupo.rotation.y = 0; }
  for (const t of Object.values(P.tubos || {})) t.vaciarEn = 0;
  for (const c of Object.values(enCubeta)) c.clear();
  // Las fichas que quedaron en las cubetas tambien son de la corrida vieja.
  for (const o of [...escena.children]) if (o.userData.deCubeta) escena.remove(o);
  bitacora.length = 0;
  ultimoTick = -1;
}

async function consultar() {
  try {
    if (MODO_DEMO) {
      estado = cuadrosDemo[cuadroDemo];
      cuadroDemo = (cuadroDemo + 1) % cuadrosDemo.length;
    } else {
      const r = await fetch(BASE + 'api/estado', { cache: 'no-store' });
      estado = await r.json();
    }
    fallos = 0;
    VEL = MODO_DEMO ? 1 : Math.max(0.25, Number(estado.velocidad) || 1);
    if (estado.tick !== undefined && estado.tick < tickAnterior) limpiarCorrida();
    const cicloNuevo = estado.tick !== tickAnterior || ultimoTick === -1;
    tickAnterior = estado.tick ?? tickAnterior;
    if (estado.casillas_monedas && cicloNuevo) {
      // Primero las fichas (salen de la cinta), despues los eventos (los
      // lotes que caen necesitan el vaso) y al final los vasos.
      sincronizarFichas();
      procesarEventos();
      sincronizarVasos();
    }
    if (P.mano) P.mano.visible = !!estado.intruso;
    if (estado.carro && P.carroPose && estado.tick !== P.carroPose.tick) {
      // Trayectoria del ultimo ciclo (una muestra cada 0,1 s de simulacion):
      // se reproduce en lo que dura un ciclo, a velocidad constante.
      P.carroPose.tick = estado.tick;
      P.carroPose.camino = (estado.carro.camino && estado.carro.camino.length > 1)
        ? estado.carro.camino : [[estado.carro.x, estado.carro.y, estado.carro.rumbo]];
      P.carroPose.t0 = performance.now();
      P.carroPose.dur = (Number(estado.ciclo_ms) || 1600) / VEL;
      if (P.vasoCarro) P.vasoCarro.grupo.visible = !!estado.carro.vaso;
    }
    if (G) marcasOrdenCarro(estado.carro);
    consultarAsistente();
    if (P.manoSaca) {
      const c = estado.mano_sacando;
      P.manoSaca.visible = c !== null && c !== undefined;
      if (P.manoSaca.visible) P.manoSaca.position.copy(posEstacionVasos(c).add(new THREE.Vector3(0, estado.mano_altura || 0.045, 0.06)));
    }
    if (estado.casillas_monedas) sincronizarAlmacen();
    const chip = document.getElementById('chipEstado');
    chip.textContent = MODO_DEMO ? (EN_ARCHIVO ? 'demo grabada · esperando la simulación de este PC'
      : `demo grabada · ${estado.linea || ''}`) : (estado.linea || '—');
    chip.className = 'chip ' + (estado.linea || '');
    document.getElementById('chipTick').textContent = `tick ${estado.tick ?? '—'}`;
    const avisos = [];
    if (estado.cortina_activa) avisos.push('<div>🖐 <b>Cortina activa</b>: la prensa sube y se detiene; tapa y empujador congelados. La cinta de monedas sigue.</div>');
    if (estado.moneda_en_espera) avisos.push('<div class="ambar">Tubo lleno: la moneda espera en E7 y la cinta de monedas se detiene hasta que un vaso reciba ese lote (no se descarta nada).</div>');
    if ((estado.alarmas || []).includes('faltan_vasos')) avisos.push('<div class="ambar">Hay un lote listo y no hay vaso válido en el llenado: poner vasos en la entrada.</div>');
    const aviso = document.getElementById('aviso');
    aviso.innerHTML = avisos.join('');
    aviso.style.display = avisos.length ? 'block' : 'none';
    // El panel se repinta como mucho una vez por segundo (no molesta al hacer clic).
    const ahora = performance.now();
    if (ahora - ultimoPintado > 1000 && pestana !== 'pasos' && pestana !== 'componentes') { pintarPanel(); ultimoPintado = ahora; }
  } catch (e) {
    fallos++;
    if (fallos > 3) {
      const chip = document.getElementById('chipEstado');
      chip.textContent = 'sin conexión con el supervisor';
      chip.className = 'chip error';
    }
  }
}

// ---------------------------------------------------------------------------
// arranque
// ---------------------------------------------------------------------------

const reloj = new THREE.Clock();
function bucle() {
  const dt = Math.min(0.05, reloj.getDelta());
  const t = reloj.elapsedTime;
  animarVuelo(dt);
  correrAnimaciones();
  animarActuadores(dt);
  animarAsistente(dt);
  if (G) { actualizarSensores(t); resaltarComponente(t); }
  controles.update();
  actualizarEtiquetas();
  renderer.render(escena, camara);
  requestAnimationFrame(bucle);
}

async function cargarJSON(url) {
  // La demo puede venir EMBEBIDA en la pagina (visor-portable.html): no hace falta pedirla.
  const embebida = window.__DEMO && url.startsWith('./demo/') ? window.__DEMO[url.slice(7, -5)] : null;
  if (embebida) return embebida;
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

// Vigia del visor portable: mientras muestra la demo grabada, pregunta cada 3 s si la
// simulacion ya esta corriendo en este PC y, cuando responde, la pestaña pasa sola al visor en
// vivo (sin que el usuario haga nada). No necesita internet: es un servidor local.
async function simulacionCorriendo() {
  try {
    const r = await fetch(URL_VIVO + 'api/estado', { cache: 'no-store', signal: AbortSignal.timeout(1500) });
    return r.ok;
  } catch (e) { return false; }
}

function vigilarSimulacion() {
  const aviso = document.getElementById('chipEstado');
  const revisar = async () => {
    if (await simulacionCorriendo()) {
      if (aviso) { aviso.textContent = 'simulación encontrada · abriendo en vivo…'; aviso.className = 'chip corriendo'; }
      location.replace(URL_VIVO + location.search);
      return;
    }
    setTimeout(revisar, 3000);
  };
  revisar();
}

async function iniciar() {
  if (EN_ARCHIVO && await simulacionCorriendo()) {
    // La simulacion ya estaba corriendo: directo al visor en vivo.
    location.replace(URL_VIVO + location.search);
    return;
  }
  if (!MODO_DEMO) {
    try { G = await cargarJSON('./api/geometria'); } catch (e) { MODO_DEMO = true; }
  }
  if (MODO_DEMO) {
    G = await cargarJSON('./demo/geometria.json');
    PASOS = await cargarJSON('./demo/pasos.json');
    cuadrosDemo = await cargarJSON('./demo/grabacion.json');
  } else {
    try { PASOS = await cargarJSON('./api/pasos'); } catch (e) { PASOS = []; }
  }
  if (EN_ARCHIVO) vigilarSimulacion();
  construirCintaMonedas();
  construirCintaVasos();
  construirCanaleta();
  construirPista();
  construirCarro();
  construirMuelle();
  construirCajaControl();
  construirSensores();
  construirCables();
  let verCables = false;
  try { verCables = localStorage.getItem('verCables') === '1'; } catch { /* sin almacenamiento */ }
  if (new URLSearchParams(location.search).has('cables')) verCables = true;
  mostrarCables(verCables);
  document.getElementById('btnCables').addEventListener('click', () => {
    verCables = !verCables;
    try { localStorage.setItem('verCables', verCables ? '1' : '0'); } catch { /* nada */ }
    mostrarCables(verCables);
  });
  for (const s of Object.values(SENS)) s.marcador.userData.baseX = s.marcador.scale.x, s.marcador.userData.baseY = s.marcador.scale.y;

  // ?vista=pista, ?paso=3 o ?sensor=cortina en la URL abren directo ahi.
  const q = new URLSearchParams(location.search);
  // Antes de ubicar la camara: la vista se corre segun si el panel tapa.
  if (q.get('panel') === '0') {
    document.getElementById('panel').classList.add('oculto');
    document.getElementById('btnPanel').classList.remove('activo');
  }
  if (q.get('paso')) {
    pestana = 'pasos';
    document.querySelectorAll('[data-pestana]').forEach((x) => x.classList.toggle('activo', x.dataset.pestana === 'pasos'));
    seleccionarPaso(Number(q.get('paso')));
    if (vuelo) { vuelo.t = 0.999; }
  } else if (q.get('componente')) {
    pestana = 'componentes';
    document.querySelectorAll('[data-pestana]').forEach((x) => x.classList.toggle('activo', x.dataset.pestana === 'componentes'));
    seleccionarComponente(q.get('componente'));
    if (vuelo) { vuelo.t = 0.999; }
  } else if (q.get('sensor')) {
    seleccionarSensor(q.get('sensor'), true);
    if (vuelo) { vuelo.t = 0.999; }
  } else if (q.get('cam') && q.get('mira')) {
    // ?cam=x,y,z&mira=x,y,z en coordenadas de la simulacion (metros): una
    // toma exacta, para capturas del informe o revisar medidas.
    const num = (t) => t.split(',').map(Number);
    controles.target.copy(V(num(q.get('mira'))));
    camara.position.copy(V(num(q.get('cam'))));
    pintarPanel();
  } else {
    vista(q.get('vista') || 'todo');
    vuelo.t = 0.999;
    pintarPanel();
  }
  await consultar();
  // En vivo se pregunta 5 veces por segundo; la demo avanza un tick por
  // cada ciclo real de la cinta (avance + pausa, config tiempos_ms), igual
  // que el supervisor a velocidad 1.
  setInterval(consultar, MODO_DEMO ? (cuadrosDemo[0] && cuadrosDemo[0].ciclo_ms) || 1600 : 200);
}

// Revision de espacio (?auditar): expone la escena para que un script mida
// si alguna pieza atraviesa a otra. No cambia nada del visor.
if (new URLSearchParams(location.search).has('auditar')) window.__visor = { THREE, escena, COMP, SENS, P, CABLES, G: () => G, camara, controles };

bucle();
iniciar();
