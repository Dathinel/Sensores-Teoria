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
// Piezas detalladas, un modulo por grupo (ver piezas/README.md). app/portable.py las mete
// en el importmap del HTML de un solo archivo: estos imports tienen que quedar asi, uno por
// linea y con la ruta './piezas/<archivo>.js'.
import * as PIEZAS_ELECTRONICA from './piezas/electronica.js';
import * as PIEZAS_CONTROL from './piezas/control.js';
import * as PIEZAS_PISTA from './piezas/pista.js';
import * as PIEZAS_ESTRUCTURA from './piezas/estructura.js';
import * as PIEZAS_LINEA_MONEDAS from './piezas/linea_monedas.js';
import * as PIEZAS_CARRO from './piezas/carro.js';
import * as PIEZAS_SENSORES_CARRO from './piezas/sensores.js';
import * as PIEZAS_VASOS from './piezas/linea_vasos.js';
import * as PIEZAS_OPTIMIZAR from './piezas/optimizar.js';
// La interfaz (barra, vistas, panel, avisos, bitacora): ver interfaz.js y docs/interfaz-visor.md.
import { crearInterfaz, SEL, simulacionCorriendo } from './interfaz.js';

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
const resaltados = SEL.resaltados;              // ids de sensores resaltados (los elige la interfaz)

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
controles.maxPolarAngle = Math.PI * 0.495;   // no se mete debajo del piso (ver limitarPolar)
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
// Con lado = 20 mm y alineado con un eje es un 2020 de verdad (seccion ranurada en T,
// piezas/estructura.js, una geometria compartida); los perfiles mas delgados (10-12 mm: brazos y
// postes impresos) y los que no van a lo largo de un eje siguen siendo cajas.
function perfil(a, b, lado = 0.02) {
  const d = new THREE.Vector3().subVectors(b, a);
  if (Math.abs(lado - 0.02) < 1e-9) {
    try {
      const eje = PIEZAS_ESTRUCTURA.ejeDominante(d);
      if (eje) {
        const m = PIEZAS_ESTRUCTURA.mallaPerfil2020(d.length(), eje, MAT_ALU);
        m.position.copy(a).addScaledVector(d, 0.5);
        return m;
      }
    } catch (e) { console.warn('perfil 2020: se usa la caja', e); }
  }
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
function etiqueta(texto, { alto = 0.012, color = '#e6e8eb', fondo = 'rgba(14,17,22,0.78)', borde = null, alcance = null, prioridad = 0 } = {}) {
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
  sprite.userData.etiqueta = { alcance: (alcance ?? alto * 60) * 1.8, texto };
  // Metros de ventaja al repartir el lugar en pantalla (las estaciones ganan a sus vecinas).
  sprite.userData.prioridad = prioridad;
  ETIQUETAS.push(sprite);
  return sprite;
}

const _p = new THREE.Vector3();
const _q = new THREE.Vector3();
const _dir = new THREE.Vector3();

// --- Etiquetas sin encimarse (revision visual, 2026-09-28) ---
// Antes cada etiqueta solo miraba su distancia a la camara: en las vistas cercanas se apilaban
// (E1..E4, las placas del carro, las de la caja de control) y se leian a traves de las piezas
// (depthTest apagado). Ahora, en cada cuadro:
//  1. se proyecta cada etiqueta a la pantalla (su rectangulo en pixeles);
//  2. se ordenan por PRIORIDAD: la del sensor resaltado primero, despues la mas cercana al punto
//     que mira la camara (el foco de la vista actual gana);
//  3. se colocan en ese orden: si choca con una ya puesta (o con la interfaz: barras, panel,
//     avisos, bitacora, leyenda), se prueba correrla media etiqueta arriba o abajo; si tampoco
//     cabe, se oculta;
//  4. se ocultan las que quedan DETRAS de una pieza solida (profundidad de la escena medida en la
//     GPU cada ~250 ms) y las muy lejos del foco de la vista;
//  5. aparecen y desaparecen con un fundido corto (no parpadean al girar).
// Tamaño en pantalla del sprite (sizeAttenuation false): escala x (1/tan(fov/2)) x media altura.
let zonasUI = [];
let zonasUIHechas = -1e9;
// Cuanto corrio volarA la mira para centrar lo enfocado en la parte libre: el foco REAL de la
// vista es controles.target - desfaseFoco (vale tambien si el usuario gira o acerca la camara).
const desfaseFoco = new THREE.Vector3();
const _foco = new THREE.Vector3();

// Oclusion por PROFUNDIDAD en la GPU: cada ~250 ms se dibuja la escena a 256 px de ancho con un
// material que solo guarda la profundidad de cada pixel (solo las piezas solidas: sin conos ni
// campos, vidrios, lineas, LED, etiquetas ni tornilleria instanciada) y se lee a la CPU. Una
// etiqueta esta "tapada" si en su pixel hay una pieza mas cerca que ella. Se probo antes con rayos
// (Raycaster), pero las mallas unidas por optimizar.js son enormes: 7-10 ms por rayo.
const OCLU_ANCHO = 256;
const ocluRT = new THREE.WebGLRenderTarget(OCLU_ANCHO, 128, { depthBuffer: true });
const ocluMat = new THREE.ShaderMaterial({
  side: THREE.DoubleSide,
  vertexShader: 'void main() { gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  // gl_FragCoord.z (0..1) repartido en 3 bytes (r + g/255 + b/255^2).
  fragmentShader: 'void main() { float z = gl_FragCoord.z; vec3 e = fract(z * vec3(1.0, 255.0, 65025.0));'
    + ' e -= e.yzz * vec3(1.0 / 255.0, 1.0 / 255.0, 0.0); gl_FragColor = vec4(e, 1.0); }',
});
const ocluCam = new THREE.PerspectiveCamera();
let ocluPix = null;
let ocluAlto = 128;
let ocluHecha = -1e9;
const _blancoOclu = new THREE.Color(0xffffff);
function esSolidoParaOclusion(o) {
  if (o.isSprite || o.isLine || o.isPoints || o.isInstancedMesh) return false;
  if (!o.isMesh) return true;
  if (o.userData.campo) return false;
  const mt = Array.isArray(o.material) ? o.material[0] : o.material;
  if (!mt || mt.isMeshBasicMaterial || mt.isShaderMaterial) return false;
  return !(mt.transparent && mt.opacity < 0.6);
}
function medirProfundidad(ahora) {
  if (ahora - ocluHecha < 250) return;
  ocluHecha = ahora;
  const W = window.innerWidth, H = window.innerHeight;
  ocluAlto = Math.max(16, Math.round(OCLU_ANCHO * H / W));
  if (ocluRT.height !== ocluAlto) ocluRT.setSize(OCLU_ANCHO, ocluAlto);
  const ocultos = [];
  escena.traverseVisible((o) => { if (o !== escena && !esSolidoParaOclusion(o)) ocultos.push(o); });
  for (const o of ocultos) o.visible = false;
  const fondo = escena.background, niebla = escena.fog, sobre = escena.overrideMaterial;
  const auto = renderer.shadowMap.autoUpdate, previo = renderer.getRenderTarget();
  const colorPrevio = renderer.getClearColor(new THREE.Color()), alfaPrevio = renderer.getClearAlpha();
  try {
    escena.background = null; escena.fog = null; escena.overrideMaterial = ocluMat;
    renderer.shadowMap.autoUpdate = false;
    renderer.setRenderTarget(ocluRT);
    renderer.setClearColor(_blancoOclu, 1);   // blanco = lo mas lejos
    renderer.clear();
    renderer.render(escena, camara);
    if (!ocluPix || ocluPix.length !== OCLU_ANCHO * ocluAlto * 4) ocluPix = new Uint8Array(OCLU_ANCHO * ocluAlto * 4);
    renderer.readRenderTargetPixels(ocluRT, 0, 0, OCLU_ANCHO, ocluAlto, ocluPix);
    ocluCam.copy(camara);
  } finally {
    renderer.setRenderTarget(previo);
    renderer.setClearColor(colorPrevio, alfaPrevio);
    renderer.shadowMap.autoUpdate = auto;
    escena.background = fondo; escena.fog = niebla; escena.overrideMaterial = sobre;
    for (const o of ocultos) o.visible = true;
  }
}
// Distancia (a lo largo de la vista) de la profundidad guardada: z de 0..1 a metros.
function linealDesdeZ(z) {
  const n = ocluCam.near, f = ocluCam.far;
  const ndc = z * 2 - 1;
  return (2 * n * f) / (f + n - ndc * (f - n));
}
// La etiqueta en `_p` queda detras de una pieza? Mira un cuadrito de 3 x 3 pixeles y se queda con
// lo MAS LEJANO: una viga fina delante no la tapa, una pieza que la cubre entera si.
function tapadaPorPieza() {
  if (!ocluPix) return false;
  _q.copy(_p).project(ocluCam);
  if (_q.z > 1 || Math.abs(_q.x) > 1 || Math.abs(_q.y) > 1) return false;
  const u = Math.round((_q.x + 1) / 2 * (OCLU_ANCHO - 1)), v = Math.round((_q.y + 1) / 2 * (ocluAlto - 1));
  let lejos = 0;
  for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
    const x = THREE.MathUtils.clamp(u + dx, 0, OCLU_ANCHO - 1), y = THREE.MathUtils.clamp(v + dy, 0, ocluAlto - 1);
    const k = (y * OCLU_ANCHO + x) * 4;
    const z = ocluPix[k] / 255 + ocluPix[k + 1] / 65025 + ocluPix[k + 2] / 16581375;
    lejos = Math.max(lejos, z);
  }
  if (lejos >= 0.999) return false;   // nada solido en ese pixel
  const pieza = linealDesdeZ(lejos);
  const etiqueta = linealDesdeZ(_q.z * 0.5 + 0.5);
  // Tolerancia: la etiqueta flota justo encima de su pieza; esa pieza no cuenta como "delante".
  return pieza < etiqueta - Math.max(0.025, etiqueta * 0.06);
}
function chocan(a, b) {
  return a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;
}
function actualizarEtiquetas() {
  const ahora = performance.now();
  const W = window.innerWidth, H = window.innerHeight;
  const k = camara.projectionMatrix.elements[5] * H / 2;
  if (ahora - zonasUIHechas > 300) {
    zonasUIHechas = ahora;
    try { zonasUI = ui.zonasOcupadas ? ui.zonasOcupadas() : []; } catch (err) { zonasUI = []; }
  }
  const foco = _foco.subVectors(controles.target, desfaseFoco);
  const distFoco = camara.position.distanceTo(foco);
  const cand = [];
  for (const e of ETIQUETAS) {
    const d = e.userData;
    d.meta ??= 0;
    d.vis ??= 0;
    d.meta = 0;
    if (!e.parent) continue;
    e.getWorldPosition(_p);
    const distCam = _p.distanceTo(camara.position);
    const a = d.etiqueta.alcance;
    const resaltada = !!(d.sensorId && resaltados.has(d.sensorId));
    const distF = _p.distanceTo(foco);
    let op = Math.max(0, Math.min(1, (a - distCam) / (a * 0.3)));
    // Cerca del foco de la vista se leen enteras aunque su `alcance` ya las estuviera desvaneciendo
    // (en la vista Caja de control los rotulos de las placas quedaban grises, ilegibles).
    if (resaltada || (distF < distFoco * 0.4 && distCam < a * 1.4)) op = 1;
    d.op = op;
    if (d.oculta || op <= 0.02) continue;
    // Muy lejos del foco de la vista: no es de esta vista. De lado (mas de 1,15 veces la distancia
    // de la camara al foco) o DETRAS de lo enfocado (p. ej. "Caja de control" sobre el rollo de tapas
    // en la vista Vasos, o los sensores de material asomando detras de la cinta de vasos). Los hitos
    // de largo alcance (META, la nube) se quedan.
    if (!resaltada && distF > Math.max(0.3, distFoco * 1.15)) continue;
    const detras = _dir.subVectors(_p, foco).dot(_q.subVectors(foco, camara.position).normalize());
    if (!resaltada && a < 3 && detras > Math.max(0.1, distFoco * 0.17)) continue;
    _q.copy(_p).project(camara);
    if (_q.z > 1 || _q.z < -1) continue;
    const x = (_q.x + 1) / 2 * W, y = (1 - _q.y) / 2 * H;
    const alto = e.scale.y * k, ancho = e.scale.x * k;
    if (x + ancho / 2 < 0 || x - ancho / 2 > W || y + alto / 2 < 0 || y - alto / 2 > H) continue;
    // Las del centro de la vista son el TEMA de la toma: se muestran aunque una pieza las tape
    // (p. ej. en la vista Material la del inductivo queda detras de su propio sensor).
    const tema = resaltada || distF < Math.max(0.06, distFoco * 0.22);
    cand.push({ e, x, y, alto, ancho, distCam, tema, prio: (resaltada ? -1e3 : 0) + distF - (d.prioridad || 0) });
  }
  cand.sort((u, v) => u.prio - v.prio);
  // Oclusion: la profundidad de la escena se mide cada ~250 ms (medirProfundidad).
  if (cand.length) { try { medirProfundidad(ahora); } catch (err) { ocluPix = null; } }
  const puestas = [];
  for (const c of cand) {
    const d = c.e.userData;
    c.e.getWorldPosition(_p);
    try { d.tapada = tapadaPorPieza(); } catch (err) { d.tapada = false; }
    if (d.tapada && !c.tema) continue;
    // Donde cabe: en su lugar, media etiqueta arriba, media abajo, una entera arriba.
    let puesto = null;
    for (const s of [0, 0.62, -0.62, 1.15]) {
      const r = { x0: c.x - c.ancho / 2 - 2, x1: c.x + c.ancho / 2 + 2, y0: c.y - c.alto / 2 - s * c.alto - 1, y1: c.y + c.alto / 2 - s * c.alto + 1 };
      if (puestas.some((o) => chocan(r, o)) || zonasUI.some((z) => chocan(r, z))) continue;
      puesto = { r, s };
      break;
    }
    if (!puesto) continue;
    puestas.push(puesto.r);
    d.meta = 1;
    // Correrla hacia arriba/abajo en pantalla: el ancla del sprite (center) se mueve en alturas.
    const cy = 0.5 - puesto.s;
    if (d.vis < 0.05 || Math.abs(c.e.center.y - cy) < 1e-3) c.e.center.y = cy;
    else c.e.center.y += (cy - c.e.center.y) * 0.35;
  }
  // Fundido por tiempo real (no por cuadro): igual de rapido a 60 fps que en una captura lenta.
  const dtReal = Math.min(0.5, Math.max(0, (ahora - (actualizarEtiquetas.antes || ahora)) / 1000));
  actualizarEtiquetas.antes = ahora;
  const paso = 1 - Math.exp(-dtReal * 12);
  for (const e of ETIQUETAS) {
    const d = e.userData;
    if (d.vis === undefined) continue;
    d.vis += ((d.meta || 0) - d.vis) * paso;
    if (d.vis < 0.01) d.vis = 0;
    const op = (d.op || 0) * d.vis;
    e.material.opacity = op * (d.opacidadBase ?? 1);
    // `oculta`: apagada a proposito (p. ej. la de "sin internet" con internet). Sin esto, este bucle
    // la volvia a encender en cada cuadro y quedaba encimada sobre la otra (2026-09-27).
    e.visible = !d.oculta && op > 0.02;
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

// `espera` (opcional, lo usa el carrusel): funcion que mientras devuelva true
// no deja EMPEZAR la animacion (se corre su arranque cuadro a cuadro). Sirve
// para ordenar por ESTADO y no por reloj: con pocos cuadros por segundo los
// tramos encadenados se estiran y un horario fijo se adelantaba.
function animar(segundos, fn, { retraso = 0, fin = null, dueno = null, espera = null } = {}) {
  const a = { t0: performance.now() + (retraso / VEL) * 1000, dur: Math.max(1, (segundos / VEL) * 1000), fn, fin, dueno, espera };
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
    if (a.espera) {
      if (a.espera()) { a.bloqueada = true; continue; }   // todavia no: arranca cuando se cumpla
      a.espera = null;
      // Si estuvo esperando, empieza AHORA desde 0 (no salta lo que espero).
      if (a.bloqueada) a.t0 = ahora;
    }
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
// Altura (y de Three) del eje de la barra de un soporteServo: bajo el centro de la base o, si el
// servo esta inclinado (base casi horizontal pero no del todo), 2,5 mm bajo su esquina mas baja.
function alturaBarraSoporte(servoObj) {
  servoObj.updateWorldMatrix(true, false);
  const q = servoObj.getWorldQuaternion(new THREE.Quaternion());
  const { tam: [sx, sy, sz], oreja } = servoObj.userData;
  const m = new THREE.Matrix4().compose(servoObj.getWorldPosition(new THREE.Vector3()), q, new THREE.Vector3(1, 1, 1));
  const zB = -sz / 2 - 0.003;                          // cara de abajo de la base (3 mm)
  const centro = Vxyz(0, 0, zB).applyMatrix4(m).y;
  if (new THREE.Vector3(0, 1, 0).applyQuaternion(q).y <= 0.7) return centro;
  const hx = (sx + 2 * oreja + 0.004) / 2, hy = (sy + 0.006) / 2;
  let yMin = Infinity;
  for (const ex of [-hx, hx]) for (const ey of [-hy, hy]) yMin = Math.min(yMin, Vxyz(ex, ey, zB).applyMatrix4(m).y);
  return yMin < centro - 0.0005 ? yMin - 0.0025 : centro;
}

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
  const tramos = [];
  // Servo inclinado (el del escape de la canaleta va a 15 grados): la barra horizontal que sale
  // del centro de la base atravesaba la esquina de la base que queda mas abajo. Se baja la barra
  // por debajo de esa esquina y un tramo corto vertical la une a la base (agente de solapes,
  // 2026-09-27). Con el servo nivelado no cambia nada. El que llama pone la punta de su poste
  // por debajo de `alturaBarraSoporte` (construirCanaleta).
  const yBarra = alturaBarraSoporte(servoObj);
  if (yBarra < bajo.y - 0.0001) {
    const baja = bajo.clone().setY(yBarra);
    tramos.push(barra(bajo, baja, 0.0025, MAT_ALU));
    bajo.copy(baja);
  }
  const codo = new THREE.Vector3(puntoEstructura.x, bajo.y, puntoEstructura.z);
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
function construirBanda(grupo, nombre, { x0, x1, y, zs, ancho, paso, altoSep, ventanas = [], insertos = true, fabricaRodillo = null }) {
  const zb = zs - G.altura_superficie;
  const largo = x1 - x0, xc = (x0 + x1) / 2;
  // Bancada (la cama sobre la que desliza la banda): termina 2 mm antes de
  // cada rodillo (antes llegaba hasta su eje y se metia en medio rodillo).
  // Donde va un sensor DEBAJO de la cinta, la bancada tiene una ventana de
  // 36 mm. Si la cinta no trae su propio soporte (`insertos: false`, la de
  // monedas usa platinas M18), la tapa un inserto IMPRESO de 6 mm roscado
  // M18: el sensor se enrosca ahi con la cara a ras.
  const cortes = [x0 + 0.013, ...ventanas.flatMap((v) => [v - 0.018, v + 0.018]), x1 - 0.013];
  for (let i = 0; i < cortes.length; i += 2) {
    const a = cortes[i], b = cortes[i + 1];
    if (b - a < 0.001) continue;
    const tramo = caja(b - a, ancho + 0.006, 0.02, COLOR.bancada, Vxyz((a + b) / 2, y, zb + 0.01));
    tramo.receiveShadow = true;
    grupo.add(tramo);
  }
  if (insertos) {
    for (const v of ventanas) {
      const inserto = caja(0.036, ancho + 0.006, 0.006, 0x56606e, Vxyz(v, y, zs - 0.005));
      grupo.add(inserto);
      registrar('estructura', inserto);
    }
  }
  const banda = caja(largo, ancho, 0.002, COLOR.cinta, Vxyz(xc, y, zs - 0.001), { roughness: 0.95 });
  banda.receiveShadow = true;
  grupo.add(banda);
  const rodillos = [];
  [x0, x1].forEach((x, i) => {
    // `fabricaRodillo(x, i)` (opcional) devuelve un rodillo detallado ya
    // puesto y con rotation.x = PI/2, que se gira con rotation.y como este.
    let r = null;
    if (fabricaRodillo) {
      try { r = fabricaRodillo(x, i); } catch (e) { console.warn('rodillo detallado: se usa el simple', e); }
    }
    if (!r) {
      r = cilindro(0.011, ancho + 0.004, 0x5d646e, Vxyz(x, y, zs - 0.011), { metalness: 0.7 });
      r.rotation.x = Math.PI / 2;
    }
    // La banda abraza media vuelta del rodillo (el lado de afuera de la cinta).
    const banda = new THREE.Mesh(new THREE.CylinderGeometry(0.0115, 0.0115, ancho, 40, 1, true, i === 0 ? Math.PI : 0, Math.PI),
      mat(COLOR.cinta, { roughness: 0.95, side: THREE.DoubleSide }));
    banda.position.copy(Vxyz(x, y, zs - 0.011));
    banda.rotation.x = Math.PI / 2;
    grupo.add(r, banda);
    rodillos.push(r);
  });
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
// Con la pieza de piezas/estructura.js: patas sobre pies niveladores, travesanos entre caras de
// patas (x a 7 cm, y a 5 cm: no se cruzan) y una escuadra 2020 en cada union.
function mesa(grupo, xs, ys, alto, id) {
  try {
    const m = PIEZAS_ESTRUCTURA.crearMesaPerfil({ largo: xs[1] - xs[0], ancho: ys[1] - ys[0], alto, idComponente: id });
    m.position.copy(Vxyz((xs[0] + xs[1]) / 2, (ys[0] + ys[1]) / 2, 0));
    grupo.add(m);
    registrar(id, m);
    return;
  } catch (e) { console.warn('mesa 2020: se usa el modelo simple', e); }
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
  // Piso y paredes sin caras en el mismo plano (se ven a traves de las paredes transparentes y
  // parpadeaban, 2026-09-28): el piso y las paredes cortas quedan entre las largas.
  g.add(caja(0.067, 0.067, 0.003, colorPiso, Vxyz(0, 0, 0.0015)));
  for (const [dx, dy, sx, sy] of [[0.035, 0, 0.003, 0.07], [-0.035, 0, 0.003, 0.07], [0, 0.035, 0.0668, 0.003], [0, -0.035, 0.0668, 0.003]]) {
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

  const yRiel = ancho / 2 + 0.003 + 0.01;
  const LM = PIEZAS_LINEA_MONEDAS;
  // Rodillos detallados (piezas/linea_monedas.js): el de la cola (x0) es el
  // MOTRIZ (goma ranurada, eje largo hacia +y hasta el acople del NEMA17); el
  // de la cabeza (x1) es el tensor. Ejes de Ø8 en rodamientos 608ZZ montados
  // en bloques impresos a los costados de los rieles.
  const ejeLado = yRiel + 0.01 + 0.012;               // cara de afuera del riel + bloque + 3 mm
  const yAcople = yRiel + 0.01 + 0.009 + 0.001 + 0.0125;   // centro del acople flexible (Ø19 × 25)
  const fabricaRodillo = (x, i) => {
    const r = LM.crearRodilloCinta({ largo: ancho + 0.004, motriz: i === 0, ejeMas: i === 0 ? yAcople : ejeLado,
      ejeMenos: ejeLado, idComponente: 'cinta_monedas' });
    r.position.copy(Vxyz(x, y, zs - 0.011));
    r.rotation.x = Math.PI / 2;
    return r;
  };
  // Platinas M18 bajo E1 (capacitivo) y E2 (inductivo): la cara del sensor
  // queda a 2,5 mm bajo la superficie (sim/geometria.py); su tuerca (10,5 mm
  // bajo la cara, 4 mm) apoya en la arandela de la platina.
  let platinas = [];
  try {
    platinas = [est[0][0], est[1][0]].map((xv) => {
      const pl = LM.crearPlatinaM18({ ancho: 2 * (yRiel - 0.01), idComponente: 'estructura' });
      pl.position.copy(Vxyz(xv, y, zs - 0.0025 - 0.0125 - 0.001));
      return pl;
    });
  } catch (e) { console.warn('platinas M18: se usa el inserto impreso', e); platinas = []; }
  construirBanda(grupo, 'monedas', { x0, x1, y, zs, ancho, paso, altoSep: 0.004,
    ventanas: [est[0][0], est[1][0]], insertos: platinas.length === 0, fabricaRodillo });
  if (platinas.length) { grupo.add(...platinas); registrar('estructura', ...platinas); }
  // Rieles laterales (perfil 2020) a los dos lados de la bancada: la
  // sostienen y llevan los cojinetes de los rodillos. Las patas van debajo
  // de los rieles, POR FUERA de la banda, para que el retorno pase libre.
  // Pasan 16 mm el eje del rodillo de cabeza: el bloque del tensor (30 mm)
  // queda entero sobre el perfil.
  P.rielMonedas = { y: y - yRiel, zArriba: zs - 0.002 };
  const rieles = [-1, 1].map((l) => perfil(Vxyz(x0 - 0.035, y + l * yRiel, zs - 0.012), Vxyz(x1 + 0.016, y + l * yRiel, zs - 0.012)));
  grupo.add(...rieles);
  registrar('estructura', ...rieles);
  // Cojinetes 608ZZ de los dos rodillos, a los dos lados (el de la cabeza
  // es tensor: colisos y tornillo que lo empuja hacia afuera).
  try {
    const cojs = [];
    for (const [x, tensor, fuera] of [[x0, false, -1], [x1, true, 1]]) {
      for (const l of [-1, 1]) {
        const c = LM.crearCojinete608({ lado: l, tensor, haciaFuera: fuera, idComponente: 'cinta_monedas' });
        c.position.copy(Vxyz(x, y + l * (yRiel + 0.01), zs - 0.011));
        cojs.push(c);
      }
    }
    grupo.add(...cojs);
    registrar('cinta_monedas', ...cojs);
  } catch (e) { console.warn('cojinetes de la cinta de monedas', e); }
  // Patas: dos en la cola (fuera de la viga del portico) y una en el
  // extremo de descarga del lado +y; del lado -y ese extremo APOYA sobre la
  // viga del portico con un taco de 2 cm (una pata ahi atravesaba la viga).
  // Las del extremo de descarga van 6 cm antes del final: mas cerca pasaban
  // por el carrusel del almacen (revision de espacio 2026-09-26).
  // Cada pata apoya en un pie nivelador M6 (12 mm) y los travesanos van de
  // cara a cara de las patas, con una escuadra de fundicion en cada union.
  const zPata = zs - 0.022, xPD = x1 - 0.06, xPC = x0 - 0.035;
  const puntosPata = [[xPC, y - yRiel], [xPC, y + yRiel], [xPD, y + yRiel]];
  let altoPie = 0, piesMesa = [];
  try {
    piesMesa = puntosPata.map(([px, py]) => {
      const pie = PIEZAS_ESTRUCTURA.crearPieNivelador({ idComponente: 'estructura' });
      pie.position.copy(Vxyz(px, py, 0));
      return pie;
    });
    altoPie = PIEZAS_ESTRUCTURA.ALTO_PIE;
  } catch (e) {
    piesMesa = puntosPata.map(([px, py]) => caja(0.03, 0.03, 0.004, 0x30363d, Vxyz(px, py, 0.002)));
  }
  const patas = puntosPata.map(([px, py]) => perfil(Vxyz(px, py, altoPie), Vxyz(px, py, zPata)));
  const travesanos = [perfil(Vxyz(xPC, y - yRiel + 0.01, 0.05), Vxyz(xPC, y + yRiel - 0.01, 0.05)),
    perfil(Vxyz(xPC + 0.01, y + yRiel, 0.05), Vxyz(xPD - 0.01, y + yRiel, 0.05))];
  const escuadras = [];
  try {
    for (const [px, py, ex, ey] of [[xPC, y - yRiel + 0.01, 0, 1], [xPC, y + yRiel - 0.01, 0, -1],
      [xPC + 0.01, y + yRiel, 1, 0], [xPD - 0.01, y + yRiel, -1, 0]]) {
      const e = PIEZAS_ESTRUCTURA.crearEscuadra2020({ ejeA: [ex, ey, 0], ejeB: [0, 0, 1], idComponente: 'estructura' });
      e.position.copy(Vxyz(px, py, 0.06));
      escuadras.push(e);
    }
  } catch (e) { console.warn('escuadras de la mesa de monedas', e); }
  grupo.add(...patas, ...piesMesa, ...travesanos, ...escuadras);
  registrar('estructura', ...patas, ...piesMesa, ...travesanos, ...escuadras);
  P.apoyoMesaMonedas = { x: xPD, y: y - yRiel, zArriba: zs - 0.022 };   // el taco se pone con el portico
  // Retorno de la banda (revision de solapes, 2026-09-27). Con rodillos de Ø22 el retorno iria
  // derecho a ~429 mm y atravesaria el capacitivo y el inductivo M18, que cuelgan 50-60 mm bajo
  // E1/E2 (sus cables salen de lado a ~345-354 mm). Como en una cinta real, el retorno BAJA por
  // debajo de ellos con rodillos de desvio: sale por abajo del rodillo de cabeza, pasa SOBRE un
  // rodillo que la tensa (C), baja envolviendo por debajo el rodillo B (a la derecha del
  // inductivo, antes de la pata de ese extremo), corre 11 cm bajo la cara de la cinta y sube por
  // el rodillo A, junto al de cola. Los tres son como los de la cinta: tubo de Ø22 sobre dos
  // 608ZZ y eje de Ø8, colgados de los rieles 2020 con dos placas impresas de 3 mm. La cara de
  // arriba de la cinta y las estaciones no cambian (la simulacion mueve casillas, no la banda).
  // El camino se calcula con las tangentes reales entre rodillos (no a ojo).
  const R_ROD = 0.011, R_BANDA = R_ROD + 0.001;        // radio del rodillo y de la linea media de la banda
  const rodIdler = (x, z) => {
    const r = cilindro(R_ROD, ancho + 0.004, 0x5d646e, Vxyz(x, y, z), { metalness: 0.7 });
    r.rotation.x = Math.PI / 2;
    const eje = cilindro(0.004, ancho + 0.013, COLOR.acero, Vxyz(x, y, z), { metalness: 0.8 });
    eje.rotation.x = Math.PI / 2;
    // Placas impresas (14 x 3 mm) desde la cara de abajo de los rieles hasta 9 mm bajo el eje.
    const zTop = zs - 0.022, zBot = z - 0.009;
    const placas = [-1, 1].map((l) => caja(0.014, 0.003, zTop - zBot, COLOR.impreso,
      Vxyz(x, y + l * (ancho / 2 + 0.0035), (zTop + zBot) / 2)));
    grupo.add(r, eje, ...placas);
    registrar('cinta_monedas', r, eje);
    registrar('estructura', ...placas);
  };
  const zAB = zs - 0.108;                              // eje de A y B: la banda pasa ~10-12 mm bajo los cables
  const xA = x0 - 0.003, xB = est[1][0] + 0.021, xC = est[1][0] + 0.075, zC = zs - 0.0332;   // C: 2 mm antes del brazo del embudo de E4
  rodIdler(xA, zAB); rodIdler(xB, zAB); rodIdler(xC, zC);
  // Recorrido (sentido de avance del retorno: de cabeza a cola). s = +1: el rodillo queda a la
  // izquierda de la banda (la banda lo rodea antihorario en el plano x-z); s = -1: a la derecha.
  const ruedas = [
    { c: [x1, zs - R_ROD], r: R_BANDA, s: -1 },         // cabeza: la banda sale por abajo
    { c: [xC, zC], r: R_BANDA, s: 1 },                   // C: pasa por encima
    { c: [xB, zAB], r: R_BANDA, s: -1 },                 // B: por debajo
    { c: [xA, zAB], r: R_BANDA, s: -1 },                 // A: por debajo
    { c: [x0, zs - R_ROD], r: R_BANDA, s: -1 },          // cola: sube por su lado de afuera
  ];
  const tangente = (A, B) => {
    const Dx = B.c[0] - A.c[0], Dz = B.c[1] - A.c[1], L = Math.hypot(Dx, Dz);
    const f = Math.atan2(Dz, Dx) - Math.asin((B.s * B.r - A.s * A.r) / L);
    const n = [-Math.sin(f), Math.cos(f)];
    return [[A.c[0] - A.s * A.r * n[0], A.c[1] - A.s * A.r * n[1]], [B.c[0] - B.s * B.r * n[0], B.c[1] - B.s * B.r * n[1]]];
  };
  const tramosT = ruedas.slice(0, -1).map((a, k) => tangente(a, ruedas[k + 1]));
  const retorno = [tramosT[0][0]];
  for (let k = 1; k < ruedas.length - 1; k++) {
    // Arco sobre el rodillo k, de donde llega la banda a donde sale.
    const { c, r, s: sen } = ruedas[k];
    const a0 = Math.atan2(tramosT[k - 1][1][1] - c[1], tramosT[k - 1][1][0] - c[0]);
    let a1 = Math.atan2(tramosT[k][0][1] - c[1], tramosT[k][0][0] - c[0]);
    if (sen > 0) { while (a1 < a0) a1 += 2 * Math.PI; } else { while (a1 > a0) a1 -= 2 * Math.PI; }
    const nArc = Math.max(1, Math.ceil(Math.abs(a1 - a0) / 0.2));
    for (let q = 0; q <= nArc; q++) {
      const a = a0 + (a1 - a0) * q / nArc;
      retorno.push([c[0] + r * Math.cos(a), c[1] + r * Math.sin(a)]);
    }
  }
  retorno.push(tramosT[tramosT.length - 1][1]);
  const matBanda = mat(COLOR.cinta, { roughness: 0.95 });
  const tirasRetorno = [];
  for (let i = 0; i + 1 < retorno.length; i++) {
    const [ax, az] = retorno[i], [bx, bz] = retorno[i + 1];
    const l = Math.hypot(bx - ax, bz - az);
    if (l < 1e-4) continue;
    const tira = new THREE.Mesh(new THREE.BoxGeometry(l + 0.0004, 0.002, ancho), matBanda);
    tira.position.copy(Vxyz((ax + bx) / 2, y, (az + bz) / 2));
    tira.rotation.z = Math.atan2(bz - az, bx - ax);
    tirasRetorno.push(tira);
  }
  grupo.add(...tirasRetorno);
  registrar('cinta_monedas', ...tirasRetorno);
  // Guias laterales: la moneda no se sale de su casilla (no hay expulsores
  // que tengan que sacarla de lado: filtro total).
  for (const lado of [-1, 1]) {
    const guia = caja(x1 - x0, 0.002, 0.006, COLOR.impreso, Vxyz((x0 + x1) / 2, y + lado * (ancho / 2 + 0.001), zs + 0.003));
    grupo.add(guia);
  }
  est.forEach((p, i) => {
    const e = etiqueta(NOMBRES_E_MONEDAS[i], { alto: 0.0085, prioridad: 0.08 });
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
  desvio.rotation.x = 0.5;   // reposo: hacia el rechazo
  // Compuerta detallada: la bisagra (eje x) ES el eje del SG90, que va
  // acostado detras del embudo con el cuerno de disco hacia la aleta; asi el
  // giro que anima moverDesvio es exactamente el del servo (antes el servo
  // estaba parado, con el eje vertical, y no podia mover la aleta).
  let servoDesvio = null, desvioDetallado = false;
  try {
    desvio.add(LM.crearCompuertaDesvio({ alCuerno: 0.018, idComponente: 'servo_desvio_e7' }));
    servoDesvio = PIEZAS_ELECTRONICA.crearServoSG90({ id: 'servo_desvio', cuerno: 'disco', idComponente: 'servo_desvio_e7' });
    servoDesvio.position.copy(Vxyz(fx + 0.033, y, zEmbAbajo - 0.002));
    servoDesvio.rotation.z = Math.PI / 2;               // eje del servo (+z local) hacia -x; cuerpo hacia abajo
    desvioDetallado = true;
  } catch (e) {
    console.warn('compuerta de desvio: se usa el modelo simple', e);
    desvio.clear();
    desvio.add(caja(0.018, 0.002, 0.016, 0xd9261a, Vxyz(0, 0, -0.008)));
    // 35 mm detras del embudo: con su escuadra, a 22 mm tocaba los dos canales.
    servoDesvio = servo(Vxyz(fx + 0.035, y, zEmbAbajo));
  }
  const carga = al.punto_carga;
  const bocaCarga = Vxyz(carga[0], carga[1], al.tubo_z_arriba + 0.012);
  // Boca de cada canal JUSTO despues de la punta de la compuerta (17 mm bajo el pivote, a 0,5 rad:
  // y = ±8 mm, z = pivote - 15 mm) y 1 mm por debajo de ella (agente de solapes, 2026-09-27):
  // antes la boca quedaba en y = ±6 mm, 11 mm mas arriba, y la punta de la compuerta en reposo
  // atravesaba el piso del canal de rechazo. Asi la moneda resbala de la compuerta al canal.
  const zBocaCanal = zEmbAbajo - 0.002 - 0.017 * Math.cos(0.5) - 0.003;   // eje del piso (cara de arriba 1 mm mas alta)
  const inicioA = Vxyz(fx, y - 0.0095, zBocaCanal);
  // El canal termina SOBRE la boca del embudo de carga, 12 mm antes de su centro y 6 mm mas
  // arriba (agente de solapes, 2026-09-27): terminaba en el centro, 4 mm por debajo del borde, y
  // su piso atravesaba la pared del embudo; tampoco puede bajar mas cerca del centro porque sus
  // paredes (perpendiculares al piso empinado) tocarian la placa del motor del carrusel.
  const haciaInicioA = new THREE.Vector3(inicioA.x - bocaCarga.x, 0, inicioA.z - bocaCarga.z).normalize();
  const finCanalA = bocaCarga.clone().addScaledVector(haciaInicioA, 0.012).add(new THREE.Vector3(0, 0.006, 0));
  const canalA = canalU(inicioA, finCanalA, 0.03, 0.01, COLOR.plata, { metalness: 0.5 });
  const embCarga = embudo(bocaCarga.clone().add(new THREE.Vector3(0, 0.004, 0)), 0.018,
    Vxyz(carga[0], carga[1], al.tubo_z_arriba + 0.003), 0.013, 0x8d96a3,
    { metalness: 0.5, transparent: true, opacity: 0.6, depthWrite: false });
  const rf = al.rechazo_final;
  const inicioB = Vxyz(fx, y + 0.0095, zBocaCanal);
  const finB = Vxyz(rf[0], rf[1] - 0.03, 0.05);
  const canalB = canalU(inicioB, finB, 0.03, 0.012, 0x8a3a3a, { transparent: true, opacity: 0.85 });
  const brazoEmb = barra(Vxyz(fx - 0.018, y - 0.012, zEmbAbajo), Vxyz(x1 - 0.012, y - ancho / 2 - 0.013, zs - 0.0235), 0.002, MAT_ALU);
  grupo.add(emb, desvio, servoDesvio, canalA, embCarga, canalB, brazoEmb);
  // Poste propio hasta el piso, justo debajo: a los lados bajan los dos
  // canales (al carrusel y al rechazo) y adelante esta el rodillo.
  if (desvioDetallado) try {
    // Brida impresa en las pestañas del SG90, sobre un taco en la punta de un
    // poste 2020 con pie nivelador; oreja del pasador colgada del embudo.
    const brida = LM.crearBridaServo({ idComponente: 'servo_desvio_e7' });
    brida.position.copy(servoDesvio.position);
    brida.rotation.copy(servoDesvio.rotation);
    const zPivote = zEmbAbajo - 0.002;
    const zBajoBrida = zPivote - 0.02545;               // punta de abajo de la brida
    const xPoste = fx + 0.0345;
    const pieD = PIEZAS_ESTRUCTURA.crearPieNivelador({ idComponente: 'estructura' });
    pieD.position.copy(Vxyz(xPoste, y, 0));
    const posteD = perfil(Vxyz(xPoste, y, PIEZAS_ESTRUCTURA.ALTO_PIE), Vxyz(xPoste, y, zBajoBrida - 0.004));
    const tacoD = caja(0.02, 0.02, 0.004, COLOR.impreso, Vxyz(xPoste, y, zBajoBrida - 0.002));
    const oreja = LM.crearOrejaBisagra({ idComponente: 'canal_e7' });
    oreja.position.copy(Vxyz(fx - 0.0125, y, zPivote));
    grupo.add(brida, pieD, posteD, tacoD, oreja);
    registrar('servo_desvio_e7', brida);
    registrar('estructura', pieD, posteD, tacoD);
    registrar('canal_e7', oreja);
    // Cable: del conector del servo (cuelga junto a la cara +x del poste)
    // baja pegado al poste hasta el piso.
    servoDesvio.updateMatrixWorld(true);
    const pinD = servoDesvio.getObjectByName('pin_servo_desvio_CABLE').getWorldPosition(new THREE.Vector3());
    const xc = xPoste + 0.0135;
    P.rutasServo.servo_desvio_e7 = [pinD, Vxyz(xc, y, pinD.y - 0.004), Vxyz(xc, y, 0.03), Vxyz(xc, y, 0.006)];
  } catch (e) { console.warn('soporte del servo de desvio', e); }
  else {
    soporteServo(grupo, servoDesvio, Vxyz(fx + 0.035, y, 0.002), 'servo_desvio_e7');
  }
  const etDesvio = etiqueta('Compuerta de rechazo (desvío)', { alto: 0.009, color: '#e5534b' });
  etDesvio.position.copy(Vxyz(fx + 0.03, y, zEmbAbajo + 0.03));
  grupo.add(etDesvio);
  registrar('canal_e7', emb, canalA, embCarga, brazoEmb);
  registrar('servo_desvio_e7', desvio, servoDesvio);
  registrar('canaletas_rechazo', canalB);
  let cubFinal;
  try {
    // Bandeja impresa de 90 × 90 × 35 mm con su rotulo (la misma huella que
    // la cubeta de 70 mm escalada × 1,3 que habia).
    cubFinal = LM.crearBandejaRechazo({ idComponente: 'canaletas_rechazo' });
    cubFinal.position.copy(Vxyz(rf[0], rf[1], 0));
  } catch (e) {
    console.warn('bandeja de rechazo: se usa la cubeta simple', e);
    cubFinal = cubeta(Vxyz(rf[0], rf[1], 0), 0x4a2a2a, 0x6b3a3a);
    cubFinal.scale.set(1.3, 1, 1.3);
  }
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
  // NEMA17 17HS4401 real (40 mm) en una jaula impresa atornillada al riel:
  // adentro quedan el cojinete y el acople flexible 5-8 mm (Ø19 × 25) que une
  // su eje (24 mm) con el del rodillo. Antes el motor iba pegado al riel y lo
  // atravesaba. Los drivers de las cintas van en la caja de control
  // (sim/catalogos.py, drivers_cintas), no al lado del motor.
  let motor;
  try {
    const yCara = yAcople + 0.024;                     // cara de montaje del motor
    motor = PIEZAS_ELECTRONICA.crearNEMA17({ id: 'motor_monedas', idComponente: 'motor_cinta_monedas' });
    motor.position.copy(Vxyz(x0, y + yCara, zs - 0.011));
    motor.rotation.x = Math.PI / 2;                    // eje (+z local) hacia -y, al rodillo
    motor.userData.conector = motor.getObjectByName('pin_motor_monedas_JST').position.clone();
    const jaula = LM.crearSoporteNEMA17({ distancia: yCara - (yRiel + 0.01), idComponente: 'estructura' });
    jaula.position.copy(motor.position);
    jaula.rotation.x = Math.PI / 2;
    const acople = LM.crearAcople({ tipo: 'flexible', idComponente: 'cinta_monedas' });
    acople.position.copy(Vxyz(x0, y + yAcople, zs - 0.011));
    acople.rotation.x = Math.PI / 2;
    grupo.add(jaula, acople);
    registrar('estructura', jaula);
    registrar('cinta_monedas', acople);
    // El acople y el eje del motor giran con los rodillos (moverCinta).
    CINTAS.monedas.rodillos.push(acople);
    const ejeMotor = motor.getObjectByName('eje');
    if (ejeMotor) CINTAS.monedas.rodillos.push(ejeMotor);
  } catch (e) {
    console.warn('NEMA17 de la cinta de monedas: se usa el modelo simple', e);
    motor = nema17(Vxyz(x0, y + yRiel + 0.01 + 0.019, zs - 0.011));
    motor.rotation.y = Math.PI;   // eje hacia -y, al rodillo
  }
  P.nemaMonedas = motor;
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
  // Casillas que encajan la base del vaso: un taco impreso con dos caras concavas pegado a cada
  // separador (avanza con el); abierto hacia los lados para el empujador y la caida al final.
  try {
    for (const s of CINTAS.vasos.seps) {
      const t = PIEZAS_VASOS.crearTacoCasilla({ paso, rBase: G.vaso.diametro / 2 * 0.86, idComponente: 'cinta_vasos' });
      t.position.y = -0.015 / 2;   // pie del separador (la caja del separador esta centrada en su alto)
      s.add(t);
    }
  } catch (e) { console.warn('tacos de casilla: sin tacos', e); }
  // Bastidor: placas laterales de aluminio de 4 mm a los dos lados de la bancada, con los
  // rodamientos de los rodillos; la del lado del operador lleva el motor.
  const yLadoMenos = y - ancho / 2 - 0.005;
  const ladosBastidor = [yLadoMenos, y + ancho / 2 + 0.005].map((yl) =>
    caja(x1 - x0 + 0.03, 0.004, 0.034, COLOR.aluminio, Vxyz((x0 + x1) / 2, yl, zb + 0.003), { metalness: 0.75, roughness: 0.38 }));
  grupo.add(...ladosBastidor);
  registrar('estructura', ...ladosBastidor);
  mesa(grupo, [x0 + 0.02, x1 - 0.02], [y - 0.03, y + 0.03], zb, 'estructura');
  est.forEach((p, i) => {
    const e = etiqueta(NOMBRES_E_VASOS[i], { alto: 0.011, prioridad: 0.08 });
    e.position.copy(Vxyz(p[0], y - 0.075, zs + 0.004));
    grupo.add(e);
  });

  // Portico trasero de perfil 2020 (del lado +y, entre la cinta de vasos y
  // la mesa de monedas): de el cuelgan el almacen, el tubo de tapas y la
  // prensa. Ninguna pieza queda en el aire.
  // Viga a 40 cm: por debajo pasa el canal corto de la descarga al carrusel.
  const yP = y + 0.055, zViga = 0.40;
  const xa = x0 - 0.035, xb = est[3][0] + 0.035;
  let portico;
  try {
    // Columnas sobre pies niveladores y la viga ENTRE ellas, con escuadras (piezas/estructura.js).
    const pz = PIEZAS_ESTRUCTURA.crearPortico2020({ largo: xb - xa, zViga, idComponente: 'estructura' });
    pz.position.copy(Vxyz((xa + xb) / 2, yP, 0));
    portico = [pz];
  } catch (e) {
    console.warn('portico 2020: se usa el modelo simple', e);
    portico = [perfil(Vxyz(xa, yP, 0), Vxyz(xa, yP, zViga + 0.01)), perfil(Vxyz(xb, yP, 0), Vxyz(xb, yP, zViga + 0.01)),
      perfil(Vxyz(xa, yP, zViga), Vxyz(xb, yP, zViga)), caja(0.03, 0.03, 0.004, 0x30363d, Vxyz(xa, yP, 0.002)),
      caja(0.03, 0.03, 0.004, 0x30363d, Vxyz(xb, yP, 0.002))];
  }
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
  let panel, marco;
  try {
    // Panel LED de borde con marco de aluminio (piezas/linea_vasos.js). Termina en la cara de la
    // columna +x (antes se metia 2 cm en ella) y su borde de arriba queda 10 mm sobre la boca del
    // vaso, por debajo del cabezal del tubo de tapas (el tubo, de Ø int. 82 mm, pasa por delante
    // del plano del panel: su eje esta a 40 mm de el). Los perfiles del marco van DETRAS del panel.
    const xp0 = x0 - 0.005, xp1 = xb - 0.01;
    const zp0 = zs + 0.003, zp1 = zs + hV + 0.010;
    panel = PIEZAS_VASOS.crearPanelLuz({ largo: xp1 - xp0, alto: zp1 - zp0, idComponente: 'panel_luz' });
    panel.position.copy(Vxyz((xp0 + xp1) / 2, yPanel - 0.002, (zp0 + zp1) / 2));
    const yM = yPanel + 0.0065;
    marco = [perfil(Vxyz(xp0, yM, zp1 - 0.006), Vxyz(xp1, yM, zp1 - 0.006), 0.01),
      perfil(Vxyz(xp0, yM, zp0 + 0.006), Vxyz(xp1, yM, zp0 + 0.006), 0.01),
      perfil(Vxyz(xa + 0.01, yM, zp1 - 0.006), Vxyz(xp0, yM, zp1 - 0.006), 0.01)];
  } catch (e) {
    console.warn('panel de luz: se usa el modelo simple', e);
    const xp0 = x0 - 0.005, xp1 = est[3][0] + 0.045;
    const zp0 = zs + 0.003, zp1 = zs + hV + 0.025;
    panel = caja(xp1 - xp0, 0.004, zp1 - zp0, 0xf4f7fb, Vxyz((xp0 + xp1) / 2, yPanel, (zp0 + zp1) / 2),
      { emissive: 0xeaf2ff, emissiveIntensity: 0.55, roughness: 0.9 });
    marco = [perfil(Vxyz(xp0, yPanel + 0.006, zp1), Vxyz(xp1, yPanel + 0.006, zp1), 0.01),
      perfil(Vxyz(xp0, yPanel + 0.006, zp0), Vxyz(xp1, yPanel + 0.006, zp0), 0.01),
      perfil(Vxyz(xa, yPanel + 0.006, zp1), Vxyz(xp0, yPanel + 0.006, zp1), 0.01)];
  }
  grupo.add(panel, ...marco);
  registrar('panel_luz', panel, ...marco);

  construirAlmacen(grupo);

  // Tubo vertical de tapas (punto 8): termina 13 mm sobre la boca del vaso
  // (la tapa cae poco y no se voltea) y cuelga del portico.
  const xt = est[2][0];
  const zTubo0 = zs + hV + 0.013, altoTubo = 0.075;
  try {
    // Tubo de acrilico sobre un cabezal impreso con el escape de dos dedos que mueve un SG90
    // invertido (piezas/linea_vasos.js); cuelga del portico por un perfil de 12 mm detras.
    const tt = PIEZAS_VASOS.crearTuboTapas({ rTapa: rBoca, rInteriorVaso: G.vaso.diametro / 2 - 0.0008, altoTubo,
      nTapas: 10, pasoTapas: 0.0062, idServo: 'servo_tapas', idComponente: 'tubo_tapas' });
    tt.position.copy(Vxyz(xt, y, zTubo0));
    grupo.add(tt);
    const ud = tt.userData;
    ud.servo.traverse((m) => { if (m.isMesh) m.userData.idComponente = 'servo_tapas'; });
    // Colgante (12 mm) con su cara contra las orejas de las abrazaderas (rOreja); con rExterior
    // (la cara de la abrazadera) las orejas quedaban 1,5 mm metidas en el perfil.
    const yCol = y + (ud.rOreja ?? ud.rExterior) + 0.006;
    const colgante = [perfil(Vxyz(xt, yP, zViga - 0.01), Vxyz(xt, yCol, zViga - 0.01), 0.012),
      perfil(Vxyz(xt, yCol, zViga - 0.01), Vxyz(xt, yCol, zTubo0 + 0.026), 0.012)];
    grupo.add(...colgante);
    registrar('tubo_tapas', ...tt.children.filter((o) => o !== ud.servo && o.name !== 'escape'));
    registrar('servo_tapas', ...ud.motor);
    registrar('estructura', ...colgante);
    P.pilaTapas = ud.pila;
    P.tapas = { x: xt, y, zBase: zTubo0 + ud.zAsiento0, dedos: ud.dedos, rTapa: rBoca, poner: ud.poner, crear: ud.crearTapa };
    tt.updateMatrixWorld(true);
    const pinTapas = tt.getObjectByName('pin_servo_tapas_CABLE').getWorldPosition(new THREE.Vector3());
    P.rutasServo.servo_tapas = [pinTapas, Vxyz(xt, yCol, pinTapas.y)];
  } catch (e) {
  console.warn('tubo de tapas: se usa el modelo simple', e);
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
  }

  // Prensa (punto 9): servo MG996R con una leva excentrica en su eje; al
  // girar 0 -> 180 grados la leva empuja un piston guiado que baja 13 mm
  // (2 x excentricidad) sobre la tapa, y vuelve. Un resorte limita la
  // fuerza. El servo sabe en que angulo quedo: no hace falta sensor.
  const xpz = est[3][0];
  const zPiston = zs + hV + 0.005 + 0.012;   // 12 mm sobre la tapa: el vaso pasa por debajo
  const exc = 0.0065;
  const zEje = zPiston + 0.012 + 0.07 + 0.022 + exc;
  try {
    // Placa de aluminio atornillada a la viga, MG996R con la leva, piston guiado con rodillo,
    // resorte de retorno y limitador, plato Ø62 con neopreno (piezas/linea_vasos.js). El plato
    // es de Ø62 (no Ø78): asienta el tapon y no choca con el cabezal del tubo de tapas vecino.
    const pr = PIEZAS_VASOS.crearPrensaLeva({ exc, zEje: zEje - zPiston, rLeva: 0.022, rPlato: 0.031,
      yPlaca: yP - 0.01 - 0.006 - y, zPlaca0: 0.016, zPlaca1: zViga + 0.01 - zPiston, idServo: 'servo_prensa', idComponente: 'motor_prensa' });
    pr.position.copy(Vxyz(xpz, y, zPiston));
    grupo.add(pr);
    const ud = pr.userData;
    registrar('motor_prensa', ...ud.motor);
    registrar('estructura', ...ud.fijas);
    P.prensa = { piston: ud.piston, leva: ud.leva, zPiston: ud.zPiston, exc: ud.exc };
    pr.updateMatrixWorld(true);
    P.rutasServo.motor_prensa = [pr.getObjectByName('pin_servo_prensa_CABLE').getWorldPosition(new THREE.Vector3())];
  } catch (e) {
  console.warn('prensa: se usa el modelo simple', e);
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
  }

  // Empujador de descarga (punto 10): servo grande con manivela; la paleta
  // pasa de lado el vaso tapado a la canaleta (-y). Los rechazados no se
  // empujan: siguen en la cinta y caen por su extremo a la bandeja.
  const xd = est[4][0];
  const yEmpReposo = y + rBoca + 0.006;
  const yEmpFin = G.canaleta.inicio[1] - 0.03 + rBoca + 0.006;
  try {
    // Paleta colgada de un carro sobre dos varillas en voladizo desde la columna +x del portico,
    // movida por biela-manivela desde un MG996R (piezas/linea_vasos.js): nada cruza la cinta a la
    // altura de los vasos y todo queda delante de la caja de control (y < 0,025).
    const em = PIEZAS_VASOS.crearEmpujador({ yReposo: yEmpReposo - y, yFin: yEmpFin - y, columna: { x: xb - xd, y: yP - y },
      zVarillas: 0.138, zPaleta0: 0.016, idServo: 'servo_empujador', idComponente: 'servo_empujador' });
    em.position.copy(Vxyz(xd, y, zs));
    grupo.add(em);
    const ud = em.userData;
    registrar('servo_empujador', ...ud.motor);
    registrar('estructura', ...ud.fijas);
    P.empujador = { paleta: ud.paleta, biela: ud.biela, horn: ud.manivela, xd, y, zs, yReposo: yEmpReposo, yFin: yEmpFin, poner: ud.poner };
    em.updateMatrixWorld(true);
    const pinEmp = em.getObjectByName('pin_servo_empujador_CABLE').getWorldPosition(new THREE.Vector3());
    P.rutasServo.servo_empujador = [pinEmp, Vxyz(xb + 0.012, yP, (pinEmp.y)), Vxyz(xb + 0.012, yP, 0.01)];
  } catch (e) {
  console.warn('empujador: se usa el modelo simple', e);
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
  P.empujador = { paleta: paletaEmp, biela: bielaEmp, horn: servoEmp.userData.horn, xd, y, zs, yReposo: yEmpReposo, yFin: yEmpFin };
  }

  // Bandeja de rechazo de vasos al final de la cinta, con un labio inclinado.
  const bj = G.bandeja_rechazo_vasos;
  const bandeja = new THREE.Group();
  // (Piso y paredes cortas entre las largas: sin caras en el mismo plano, que parpadeaban.)
  bandeja.add(caja(0.0958, 0.1158, 0.004, 0x5a616c, Vxyz(0, 0, 0.002)));
  for (const [dx, dy, sx, sy] of [[0.05, 0, 0.004, 0.12], [-0.05, 0, 0.004, 0.12], [0, 0.06, 0.0957, 0.004], [0, -0.06, 0.0957, 0.004]]) {
    bandeja.add(caja(sx, sy, 0.06, 0x8b939f, Vxyz(dx, dy, 0.03), { transparent: true, opacity: 0.55 }));
  }
  bandeja.position.copy(Vxyz(bj[0], bj[1], 0));
  // Labio 18 mm mas afuera y 8 mm mas abajo (agente de solapes, 2026-09-27): su canto de arriba
  // quedaba a 16 mm del eje del rodillo de cabeza y los separadores (15 mm) con su taco barren
  // hasta ~32 mm al dar la vuelta; ahora queda a 36 mm.
  const labio = caja(0.05, ancho, 0.003, 0x8b939f, Vxyz(x1 + 0.05, y, zs - 0.044));
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
  try {
    // NEMA17 con acople flexible al eje del rodillo, en una placa con separadores desde la placa
    // lateral del bastidor (piezas/linea_vasos.js).
    const ac = PIEZAS_VASOS.crearAccionamientoCinta({ id: 'motor_vasos', idComponente: 'motor_cinta_vasos' });
    ac.position.copy(Vxyz(x0, yLadoMenos - 0.002, zs - 0.011));
    grupo.add(ac);
    const nema = ac.userData.nema;
    nema.userData.conector = nema.getObjectByName('pin_motor_vasos_JST').position.clone();
    P.nemaVasos = nema;
    registrar('motor_cinta_vasos', ac);
  } catch (e) {
    console.warn('motor de la cinta de vasos: se usa el modelo simple', e);
    const motor = nema17(Vxyz(x0, y - ancho / 2 - 0.024, zs - 0.011));
    P.nemaVasos = motor;
    grupo.add(motor);
    registrar('motor_cinta_vasos', motor);
  }
  registrar('cinta_vasos', ...grupo.children.filter((o) => !o.userData.parte && !o.isSprite));

  escena.add(grupo);
}

// Almacen por denominacion (revolver): placa FIJA con un solo agujero, un
// carrusel con 6 tubos de policarbonato que gira encima, el obturador del
// agujero con su SG90 y, debajo, la tolva que lleva el lote al vaso.
// Piezas detalladas en piezas/linea_monedas.js; si alguna falla queda el
// modelo simple de antes.
function construirAlmacen(grupo) {
  const al = G.almacen;
  const [cx, cy] = al.centro;
  const zBase = al.tubos[0].base[2];
  const zArriba = al.tubo_z_arriba;
  const R = al.radio_carrusel;
  const ang = (g) => (g * Math.PI) / 180;
  const LM = PIEZAS_LINEA_MONEDAS;
  const tv = al.tolva;
  // Placa FIJA con un solo agujero (sobre el vaso de llenado). Cuelga del
  // portico con dos varillas M5 por FUERA del giro de los tubos, con tuerca
  // arriba y abajo de la placa.
  const colgadores = [30, 150].map((g) => [0.056 * Math.cos(ang(g)), 0.056 * Math.sin(ang(g))]);
  let placa;
  try {
    placa = LM.crearPlacaFijaAlmacen({ agujeroEn: [tv.salida[0] - cx, tv.salida[1] - cy], rAgujero: al.tubos[0].radio,
      tuercas: colgadores, idComponente: 'almacen' });
    placa.position.copy(Vxyz(cx, cy, zBase - 0.002));
  } catch (e) {
    console.warn('placa fija del almacen: se usa el disco simple', e);
    placa = cilindro(0.058, 0.004, 0x3a4250, Vxyz(cx, cy, zBase - 0.002), { transparent: true, opacity: 0.75 });
  }
  grupo.add(placa);
  registrar('almacen', placa);
  for (const [dx, dy] of colgadores) {
    const v = barra(Vxyz(cx + dx, cy + dy, P.portico.z - 0.01), Vxyz(cx + dx, cy + dy, zBase - 0.006), 0.0025, MAT_ALU);
    grupo.add(v);
    registrar('estructura', v);
  }
  // Obturador del agujero y embudo corto al vaso. La bisagra del obturador
  // (eje horizontal) es el eje de un SG90 acostado al lado, por FUERA del
  // borde de la placa (su cuerno no cabe en los 4 mm bajo ella) y del lado de
  // 210 grados: del otro lado quedaba dentro del tubo de tapas.
  const hueco = Vxyz(tv.salida[0], tv.salida[1], zBase - 0.004);
  const fuera = new THREE.Vector3(tv.salida[0] - cx, 0, -(tv.salida[1] - cy)).normalize();
  const obturador = new THREE.Group();
  obturador.position.copy(hueco).addScaledVector(fuera, 0.02).add(new THREE.Vector3(0, -0.004, 0));
  obturador.lookAt(obturador.position.clone().add(fuera));
  const tolva = embudo(Vxyz(tv.salida[0], tv.salida[1], tv.z_arriba), tv.radio, Vxyz(tv.salida[0], tv.salida[1], tv.z_abajo), 0.014, 0xcfd3da,
    { transparent: true, opacity: 0.45, metalness: 0.6, depthWrite: false });
  let servoObt = null;
  try {
    const t0 = 0.047;                                   // de la bisagra al plano de las pestanas del servo
    const aleta = LM.crearObturadorAlmacen({ lado: -1, alCuerno: t0 - 0.015, idComponente: 'servo_obturador' });
    obturador.add(aleta);
    const h = new THREE.Vector3(1, 0, 0).applyQuaternion(obturador.quaternion);   // eje de la bisagra
    const arriba = new THREE.Vector3(0, 1, 0);
    servoObt = PIEZAS_ELECTRONICA.crearServoSG90({ id: 'servo_obturador', cuerno: 'brazo', angulo: 180, idComponente: 'servo_obturador' });
    servoObt.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(arriba, h, arriba.clone().cross(h)));
    servoObt.position.copy(obturador.position).addScaledVector(h, -t0);
    // El cuerno gira con la aleta (animarEmbalado solo mueve el obturador).
    const cuerno = servoObt.getObjectByName('cuerno');
    const base = cuerno.rotation.y;
    aleta.getObjectByName('aleta').onBeforeRender = () => { cuerno.rotation.y = base + obturador.rotation.x; };
    // Brida en las pestanas y un liston impreso desde su punta de arriba
    // hasta un taco atornillado al borde de la placa (fuera del giro de los tubos).
    const brida = LM.crearBridaServo({ idComponente: 'servo_obturador' });
    brida.position.copy(servoObt.position);
    brida.quaternion.copy(servoObt.quaternion);
    grupo.add(brida);
    brida.updateMatrixWorld(true);
    const A = brida.getObjectByName('ancla_brida_mas_x').getWorldPosition(new THREE.Vector3())
      .addScaledVector(h, 0.0015).add(new THREE.Vector3(0, 0.002, 0));
    const dir = new THREE.Vector3(A.x - cx, 0, A.z + cy).normalize();
    const B = new THREE.Vector3(cx + dir.x * 0.054, A.y, -cy + dir.z * 0.054);
    const liston = LM.crearListon(A, B, 0.008, 0.004);
    const zPlaca = zBase;                               // cara de arriba de la placa fija
    const taco = caja(0.008, 0.008, A.y - 0.002 - zPlaca, COLOR.impreso, new THREE.Vector3(B.x, (A.y - 0.002 + zPlaca) / 2, B.z));
    grupo.add(liston, taco);
    registrar('servo_obturador', brida);
    registrar('estructura', liston, taco);
    // Coleta del SG90: el servo va parado (su -x mira abajo) y la coleta recta colgaba 36 mm hacia
    // el paso de los vasos (~8 mm de holgura). Se dobla: baja 3 mm al salir del cuerpo, pasa a su
    // espalda (lado contrario al eje, 3,6 mm afuera) y SUBE pegada a ella; el conector JR queda
    // parado junto al servo, a la altura de la placa, y la funda sigue por el liston hasta el taco.
    // (Coordenadas de la pieza en mm: x a lo largo del cuerpo, z el eje del servo; ver crearServo.)
    try {
      const Q = (x, y, z) => new THREE.Vector3(x * MM, z * MM, -y * MM);
      const xS = -16.6, zS = -11.9, zE = -19.5, xArr = -1;   // salida del cuerpo, espalda, fin de la subida
      for (const c of [...servoObt.children]) {
        const coleta = c.isMesh && Math.abs(c.rotation.z - Math.PI / 2) < 1e-6 && c.position.x < xS * MM && Math.abs(c.position.y - zS * MM) < 1e-5;
        if (coleta) servoObt.remove(c);
      }
      [0x6b3a1f, 0xd23a2a, 0xe8901c].forEach((color, j) => {
        const yj = (j - 1) * 1.0, m = mat(color);
        const q = [Q(xS, yj, zS), Q(xS - 3, yj, zS), Q(xS - 3, yj, zE), Q(xArr, yj, zE)];
        for (let k = 0; k + 1 < q.length; k++) servoObt.add(barra(q[k], q[k + 1], 0.5 * MM, m));
      });
      // Amarra plastica (2,5 mm) alrededor del cuerpo que sujeta la coleta contra su espalda.
      const mA = mat(0x111214, { roughness: 0.6 }), xa = -12, ya = 6.5, z0 = -20.2, z1 = 7.4, e = 0.6;
      for (const [yc, zc, ly, lz] of [[ya, (z0 + z1) / 2, e, z1 - z0], [-ya, (z0 + z1) / 2, e, z1 - z0], [0, z0, 2 * ya + e, e], [0, z1, 2 * ya + e, e]]) {
        const b = new THREE.Mesh(new THREE.BoxGeometry(2.5 * MM, lz * MM, ly * MM), mA);
        b.position.copy(Q(xa, yc, zc));
        servoObt.add(b);
      }
      const con = servoObt.getObjectByName('conector');
      con.position.copy(Q(xArr + 7, 0, zE));
      const pinObt = servoObt.getObjectByName('pin_servo_obturador_CABLE');
      pinObt.position.copy(Q(xArr + 14, 0, zE));
      if (pinObt.userData.dir) pinObt.userData.dir = new THREE.Vector3(1, 0, 0);
    } catch (e) { console.warn('coleta del servo del obturador: queda recta', e); }
    servoObt.updateMatrixWorld(true);
    const pin = servoObt.getObjectByName('pin_servo_obturador_CABLE').getWorldPosition(new THREE.Vector3());
    P.rutasServo.servo_obturador = [pin, pin.clone().add(new THREE.Vector3(0, 0.006, 0)),
      A.clone().add(new THREE.Vector3(0, 0.006, 0)), B.clone().add(new THREE.Vector3(0, 0.006, 0))];
    // Brazo portacables (2026-09-28): el tramo horizontal del cable (de encima del servo hasta
    // donde baja, x = 0,1445) pasaba ~72 mm suelto, unos 2 cm por fuera del borde de la placa fija.
    // Un brazo impreso de 8 x 3 mm atornillado al canto de la placa lo toma por la mitad con una
    // abrazadera. (El tramo va a lo largo de x, a la altura del pin + 6 mm.)
    try {
      const yC = pin.y + 0.006;
      const M = new THREE.Vector3((pin.x + 0.1445) / 2, yC, pin.z);
      const cen = placa.getWorldPosition(new THREE.Vector3());
      const radial = new THREE.Vector3(M.x - cen.x, 0, M.z - cen.z);
      const dist = radial.length();
      radial.normalize();
      const rPlaca = 0.058;
      if (dist > rPlaca + 0.004) {
        const brazo = new THREE.Group();
        const matImp = new THREE.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.8 });
        const largo = dist - rPlaca + 0.012;                        // se mete 12 mm bajo el canto
        const bar = new THREE.Mesh(new THREE.BoxGeometry(largo, 0.003, 0.008), matImp);
        bar.position.set(rPlaca - 0.012 + largo / 2, -0.0045, 0);  // pegado por debajo del cable
        const aro = new THREE.Mesh(new THREE.TorusGeometry(0.0035, 0.0009, 8, 20), matImp);
        aro.position.set(dist, 0, 0);
        aro.rotation.y = Math.PI / 2;                               // abraza el cable, que va a lo largo de x
        const tornillo = new THREE.Mesh(new THREE.CylinderGeometry(0.0028, 0.0028, 0.0016, 12),
          new THREE.MeshStandardMaterial({ color: 0x9aa0a8, metalness: 0.8, roughness: 0.35 }));
        tornillo.position.set(rPlaca - 0.006, -0.0022, 0);
        brazo.add(bar, aro, tornillo);
        brazo.position.set(cen.x, yC, cen.z);
        brazo.rotation.y = -Math.atan2(radial.z, radial.x);
        brazo.traverse((o) => { if (o.isMesh) o.castShadow = true; });
        brazo.name = 'portacables_obturador';
        escena.add(brazo);
      }
    } catch (e) { console.warn('portacables del obturador', e); }
  } catch (e) {
    console.warn('obturador del almacen: se usa el modelo simple', e);
    obturador.clear();
    obturador.add(cilindro(0.017, 0.002, 0x9c2a22, new THREE.Vector3(0, 0, -0.02), {}, 24));
    servoObt = servo(hueco.clone().addScaledVector(fuera, 0.034).add(new THREE.Vector3(0, -0.012, 0)));
    grupo.add(servoObt);
    const ladoObt = new THREE.Vector3(-fuera.z, 0, fuera.x);
    soporteServo(grupo, servoObt, hueco.clone().addScaledVector(fuera, 0.034).addScaledVector(ladoObt, 0.02).add(new THREE.Vector3(0, 0.002, 0)), 'servo_obturador');
  }
  grupo.add(obturador, servoObt, tolva);
  registrar('servo_obturador', obturador, servoObt);
  registrar('almacen', tolva);
  P.obturador = obturador;
  P.hueco = hueco;
  P.tolva = Vxyz(tv.salida[0], tv.salida[1], tv.z_abajo);

  // Carrusel que GIRA: disco de arriba con los 6 tubos colgados (sus fondos
  // pasan a 0,5 mm de la placa fija: las pilas resbalan sobre ella). Lo
  // mueve un 28BYJ-48 (sim/catalogos.py) por el eje central; un Hall ve el
  // iman de referencia.
  const carrusel = new THREE.Group();
  carrusel.position.copy(Vxyz(cx, cy, 0));
  // Cara de arriba de la placa del motor: el acople rigido (12 x 16 mm) queda
  // entre el cubo del disco y el eje del motor (6 mm dentro del acople).
  const zMotor = zArriba + 0.029;
  const zAcople = zMotor - 0.0015 - 0.008;
  let piezasDetalle = false;
  try {
    // Iman de referencia (neodimio 6 x 3 mm) sobre el disco, a R+15 mm y
    // entre los tubos de 330 y 30 grados; el Hall queda 4 mm encima.
    const disco = LM.crearDiscoCarrusel({ tubos: al.tubos.map((t) => [t.base[0] - cx, t.base[1] - cy]),
      // Agujeros del MISMO diametro que el interior del tubo (Ø29): el tubo no atraviesa el disco,
      // va pegado A TOPE por debajo (agente de solapes, 2026-09-27). Con agujeros Ø32 para meter
      // el tubo, a 33 mm entre ejes quedaba 1 mm de acrilico entre dos agujeros; asi quedan 4 mm.
      rHueco: al.tubos[0].radio, iman: [R + 0.015, 0], idComponente: 'almacen' });
    disco.position.set(0, zArriba + 0.0015, 0);
    const zEje0 = zBase - 0.008, zEje1 = zAcople;
    const eje = cilindro(0.004, zEje1 - zEje0, COLOR.acero, new THREE.Vector3(0, (zEje0 + zEje1) / 2, 0), { metalness: 0.8 });
    const collarin = cilindro(0.007, 0.004, 0xb8bec6, new THREE.Vector3(0, zBase - 0.0082, 0), { metalness: 0.85, roughness: 0.3 });
    const acople = LM.crearAcople({ tipo: 'rigido', idComponente: 'motor_carrusel' });
    acople.position.set(0, zAcople, 0);
    carrusel.add(disco, eje, collarin, acople);
    registrar('almacen', disco, eje, collarin);
    piezasDetalle = true;
  } catch (e) {
    console.warn('disco del carrusel: se usa el modelo simple', e);
    carrusel.clear();
    const disco = cilindro(0.052, 0.003, 0x566070, new THREE.Vector3(0, zArriba + 0.0015, 0), { transparent: true, opacity: 0.55, metalness: 0.4 });
    const eje = cilindro(0.004, zArriba - zBase + 0.03, COLOR.acero, new THREE.Vector3(0, (zArriba + zBase) / 2 + 0.01, 0), { metalness: 0.8 });
    const iman = cilindro(0.003, 0.003, 0x8f96a0, new THREE.Vector3(R + 0.015, zArriba + 0.0045, 0), { metalness: 0.9 });
    carrusel.add(disco, eje, iman);
    registrar('almacen', disco, eje);
  }
  P.tubos = {};
  for (const t of al.tubos) {
    const rel = new THREE.Vector3(t.base[0] - cx, 0, -(t.base[1] - cy));
    const texto = t.denominacion === 'otras' ? 'otras' : `$${t.denominacion.toLocaleString('es-CO')}`;
    const anguloCasa = Math.atan2(t.base[1] - cy, t.base[0] - cx);
    let partes;
    try {
      if (!piezasDetalle) throw new Error('sin disco detallado');
      // Tubo de policarbonato: de 0,5 mm sobre la placa hasta la cara de ABAJO del disco (pegado
      // a tope con cemento de policarbonato/acrilico; el agujero del disco sigue el mismo Ø29, asi
      // que la boca de carga queda donde estaba), con la etiqueta hacia afuera. Sin collar.
      const tubo = LM.crearTuboMonedas({ rInterior: t.radio, alto: zArriba - zBase - 0.0005 - 0.003, zCollar: zArriba - zBase - 0.0005,
        texto, angulo: anguloCasa, fondoEtiqueta: t.denominacion === 'otras' ? '#9aa3ad' : '#f2b134', idComponente: 'almacen' });
      tubo.position.copy(rel).add(new THREE.Vector3(0, zBase + 0.0005, 0));
      partes = [tubo];
    } catch (e) {
      const tubo = new THREE.Mesh(new THREE.CylinderGeometry(t.radio + 0.001, t.radio + 0.001, t.alto, 28, 1, true),
        mat(0xcfe3ff, { transparent: true, opacity: 0.22, side: THREE.DoubleSide, roughness: 0.1, depthWrite: false }));
      tubo.position.copy(rel).add(new THREE.Vector3(0, zBase + t.alto / 2, 0));
      const aro = new THREE.Mesh(new THREE.TorusGeometry(t.radio + 0.001, 0.0012, 8, 28), mat(COLOR.plata, { metalness: 0.7 }));
      aro.rotation.x = Math.PI / 2;
      aro.position.copy(rel).add(new THREE.Vector3(0, zArriba, 0));
      partes = [tubo, aro];
    }
    const et = etiqueta(texto, { alto: 0.009, color: t.denominacion === 'otras' ? '#8b949e' : '#f2b134' });
    et.position.copy(rel).add(new THREE.Vector3(0, zArriba + 0.008, 0)).addScaledVector(rel.clone().normalize(), 0.02);
    const pila = new THREE.Group();
    pila.position.copy(rel).add(new THREE.Vector3(0, zBase, 0));
    pila.userData.parte = true;
    carrusel.add(...partes, et, pila);
    registrar('almacen', ...partes);
    P.tubos[t.denominacion] = { pila, n: 0, radio: t.radio, alto: t.alto, anguloCasa, vaciarEn: 0 };
  }
  grupo.add(carrusel);
  // Motor del carrusel: 28BYJ-48 parado sobre su placa impresa, eje hacia
  // abajo y corrido 8 mm (su eje esta descentrado) para quedar en el eje del
  // carrusel. La placa cuelga del portico con dos varillas M5 y una pletina.
  let motor;
  const soporte = [];
  try {
    motor = PIEZAS_ELECTRONICA.crear28BYJ48({ id: 'motor_carrusel', idComponente: 'motor_carrusel' });
    motor.position.copy(Vxyz(cx - 0.008, cy, zMotor));
    motor.rotation.x = Math.PI;                        // eje (+z local) hacia abajo
    const placaM = LM.crearSoporteMotorCarrusel({ idComponente: 'estructura' });
    placaM.position.copy(Vxyz(cx, cy, zMotor));
    const zPletina = P.portico.z - 0.01 - 0.003;
    for (const s of [-1, 1]) {
      soporte.push(barra(Vxyz(cx + 0.006, cy + s * 0.022, zMotor - 0.005 - 0.005), Vxyz(cx + 0.006, cy + s * 0.022, zPletina), 0.0025, MAT_ALU));
    }
    const y0 = cy - 0.028, y1 = P.portico.y + 0.01;
    soporte.push(caja(0.02, y1 - y0, 0.003, MAT_ALU, Vxyz(cx + 0.006, (y0 + y1) / 2, zPletina + 0.0015)));
    soporte.push(placaM);
  } catch (e) {
    console.warn('motor del carrusel: se usa el modelo simple', e);
    motor = cilindro(0.014, 0.019, 0xc9c9c9, Vxyz(cx, cy, zArriba + 0.02), { metalness: 0.5 });
    soporte.length = 0;
    soporte.push(barra(Vxyz(cx, cy, zArriba + 0.03), Vxyz(cx, cy, P.portico.z - 0.012), 0.004, MAT_ALU),
      barra(Vxyz(cx, cy, P.portico.z - 0.012), Vxyz(cx, P.portico.y, P.portico.z - 0.012), 0.004, MAT_ALU));
  }
  grupo.add(motor, ...soporte);
  registrar('motor_carrusel', motor, carrusel);
  registrar('estructura', ...soporte);
  P.carrusel = { grupo: carrusel, angulo: 0, finGiro: 0, giros: 0, activo: 0, cx, cy, R, zBase,
    carga: ang(al.angulo_carga), agujero: ang(al.angulo_agujero) };
  const et = etiqueta('Almacén tipo revólver', { alto: 0.011, color: '#3fb68b' });
  et.position.copy(Vxyz(cx - 0.08, cy - 0.02, zArriba + 0.03));
  grupo.add(et);
}

// El carrusel SIGUE a la simulacion (usuario, 2026-09-28: "la moneda pasa sin
// que se espere a que de la vuelta"). Antes el visor giraba por su cuenta, en
// una cola propia que se iba atrasando (hasta 6,5 s) mientras la moneda caia
// igual: caia a un tubo que todavia no llegaba. Ahora cada giro es un evento
// `carrusel/gira` de la simulacion (sim/planta.py + control/carrusel.py) con
// su angulo final, su duracion real (28BYJ-48: media vuelta = 4,1 s) y cuando
// arranca dentro del ciclo (`en_ms`); aqui solo se anima eso, a la velocidad
// del visor. Un giro nuevo arranca desde donde este el disco en ese momento
// (como el firmware, que solo cambia su objetivo), asi que nunca se acumula
// atraso. `c.finGiro` (ms de performance.now) es cuando termina el ultimo
// giro pedido: la moneda y el lote no caen antes.
// La CAIDA ocupa el disco (revision visual 2026-09-29: de 15 llegadas, 8 caian
// 15-37 mm fuera de la boca con el disco girando 22-40 grados). La simulacion ya
// retrasa el giro a la siguiente moneda hasta que la anterior llega al fondo de
// su tubo (`en_ms`, tiempos_ms.caida_moneda_tubo). Como red de seguridad el visor
// ordena por ESTADO, no por reloj (con pocos cuadros por segundo un horario fijo
// se adelantaba a la animacion de la caida):
//  - cada moneda que va al almacen y cada lote se anotan en `c.enAire` con el
//    giro que los deja en su lugar (`necesita`: el ultimo giro pedido cuando
//    llegaron; la simulacion solo suelta con el tubo ya puesto);
//  - la moneda no deja la cinta (y el obturador no abre) hasta que ESE giro
//    termino (`c.terminado`);
//  - un giro pedido DESPUES no arranca mientras quede en el aire algo anotado
//    antes que el (hasta que la moneda aterriza o el obturador cierra).
// Los giros arrancan en orden (`inicioUltimo`): un giro viejo retrasado no
// puede tomar el disco despues del nuevo.
function girarCarrusel(e) {
  const c = P.carrusel;
  if (!c) return;
  const id = ++c.giros;
  const hasta = (e.hasta_grados * Math.PI) / 180;
  const difSim = ((e.hasta_grados - e.desde_grados) * Math.PI) / 180;
  const dur = Math.max(0.05, (e.dur_ms || 0) / 1000);
  const ahora = performance.now();
  const retraso = Math.max(0, (e.en_ms || 0) / 1000, (((c.inicioUltimo || 0) - ahora) / 1000) * VEL);
  c.inicioUltimo = ahora + (retraso / VEL) * 1000;
  // Espera si el giro anterior todavia no arranco (si no, al arrancar despues le
  // quitaria el disco) o si algo anotado antes que este sigue cayendo.
  const espera = () => (c.empezado || 0) < id - 1 || (c.enAire || []).some((m) => m.necesita < id);
  let desde = null, dif = 0;
  animar(dur, (u) => {
    if (desde === null) {
      // Toma el disco donde este (el giro anterior deja de mandar).
      c.activo = id;
      c.empezado = Math.max(c.empezado || 0, id);
      desde = c.angulo;
      dif = Math.atan2(Math.sin(hasta - desde), Math.cos(hasta - desde));
      if (Math.abs(Math.abs(dif) - Math.PI) < 1e-3) dif = Math.sign(difSim || 1) * Math.PI;   // media vuelta: mismo sentido
    }
    if (c.activo !== id) return;
    // Velocidad constante: el firmware da un medio paso cada 2 ms, sin rampas.
    c.angulo = desde + dif * u;
    c.grupo.rotation.y = c.angulo;
    c.girando = u < 1;
  }, { retraso, dueno: c, espera, fin: () => {
    // Termino con el disco en su lugar (si otro giro no se lo quito antes).
    if (c.activo === id) { c.girando = false; c.terminado = Math.max(c.terminado || 0, id); }
  } });
  c.finGiro = ahora + ((retraso + dur) / VEL) * 1000;
}

// Una moneda que va a su tubo, o un lote que va a caer por el obturador: queda
// anotado con el giro que lo deja en su lugar (el ultimo pedido hasta ahora).
function anotarEnAire() {
  const c = P.carrusel;
  if (!c) return null;
  const marca = { necesita: c.giros };
  (c.enAire = c.enAire || []).push(marca);
  return marca;
}
function quitarDelAire(marca) {
  const c = P.carrusel;
  if (c && marca) c.enAire = (c.enAire || []).filter((m) => m !== marca);
}
// True mientras el giro que necesita `marca` no haya terminado (el tubo todavia
// no esta quieto en la carga o sobre el agujero).
function faltaSuGiro(marca) {
  const c = P.carrusel;
  return !!(c && marca && (c.terminado || 0) < marca.necesita);
}

// Segundos (de simulacion) que faltan para que el carrusel quede quieto (para
// revisar desde la consola; la moneda y el lote esperan por estado, faltaSuGiro).
function faltaCarrusel() {
  const c = P.carrusel;
  return c ? Math.max(0, ((c.finGiro - performance.now()) / 1000) * VEL) : 0;
}

// Visor abierto a mitad de corrida (o corrida nueva): el disco donde dice la simulacion.
function ubicarCarrusel() {
  const c = P.carrusel, e = estado.carrusel;
  if (!c || !e || typeof e.angulo_grados !== 'number') return;
  cancelar(c);
  c.activo = ++c.giros;
  c.angulo = (e.angulo_grados * Math.PI) / 180;
  c.grupo.rotation.y = c.angulo;
  c.finGiro = 0;
  c.girando = false;
  // Lo que se esperaba ya no cuenta: el disco esta donde dice la simulacion.
  c.empezado = c.terminado = c.giros;
  c.enAire = [];
}

function colorMoneda(denominacion, i) {
  if (denominacion === 500 || denominacion === 1000) return i % 2 ? COLOR.plata : COLOR.oro;
  return denominacion === 50 || denominacion === 100 ? (i % 2 ? COLOR.plata : 0xb8b9bd) : COLOR.oro;
}

function sincronizarAlmacen() {
  const al = estado.almacen || {};
  // La pila crece cuando la moneda termina de caer en la boca del tubo (no
  // cuando cambia la cuenta: esa cambia al empezar la caida). Revision visual
  // 2026-09-29: la pila de $500 crecia con el disco quieto en el tubo $200 (la
  // cuenta subia sin animacion de caida). Ahora crece SOLO cuando termina de
  // caer una moneda de ESE tubo (`tubo.aterrizadas`); si la cuenta sube sin
  // caida (almacen precargado, visor abierto a mitad de corrida) se pone de una
  // vez al arrancar, o con el disco quieto, nunca en medio de un giro.
  const libre = !P.almacenVisto || !(P.carrusel && P.carrusel.girando);
  for (const d of [...DENOMINACIONES, 'otras']) {
    const tubo = P.tubos && P.tubos[d];
    if (!tubo) continue;
    const n = Math.max(0, Number(al[String(d)] || 0) - (tubo.cayendo || 0));
    while (tubo.n < n && (libre || (tubo.aterrizadas || 0) > 0)) {
      if (tubo.aterrizadas > 0) tubo.aterrizadas--;
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
  if (estado.almacen) P.almacenVisto = true;
}

function animarEmbalado(e) {
  // El tubo ya llego al agujero (el giro vino antes, en su propio evento
  // `carrusel/gira`): se abre el obturador en el instante que dice la
  // simulacion (`en_ms`) y la pila entera cae por el embudo al vaso de
  // llenado. Revision visual 2026-09-29 (el lote de $500 caia a 9 mm del agujero
  // con 15 grados de giro en el segundo previo): el obturador abre recien cuando
  // ESE giro termino (el tubo quieto sobre el agujero, por estado y no por
  // reloj) y hasta que cierra el disco no gira (el giro de vuelta espera).
  const tubo = P.tubos[e.denominacion];
  if (!tubo) return;
  const v = vasos.get(e.vaso);
  const compuerta = (e.obturador_ms || seg('compuerta_tubo', 600) * 1000) / 1000;
  const abrir = compuerta * 0.25;
  const o = P.obturador;
  const n = Math.min(e.cantidad, 10);
  const marca = anotarEnAire();
  tubo.vaciarEn = Infinity;             // la pila no baja antes de abrir
  if (v) v.llenando = true;
  const soltar = () => {
    animar(abrir, (u) => { o.rotation.x = -1.3 * suave(u); }, { dueno: o });
    animar(abrir, (u) => { o.rotation.x = -1.3 * (1 - suave(u)); }, { retraso: compuerta * 0.75, dueno: o,
      fin: () => quitarDelAire(marca) });   // obturador cerrado: el disco ya puede girar
    tubo.vaciarEn = performance.now() + (abrir / VEL) * 1000;
    // La pila baja JUSTO cuando se abre el obturador (con el tubo quieto sobre
    // el agujero), no en la siguiente consulta (en la demo, una cada 1,6 s).
    animar(0.01, () => {}, { retraso: abrir, fin: sincronizarAlmacen });
    if (v) animar(0.01, () => {}, { retraso: abrir + n * 0.05 + 0.45, fin: () => { v.llenando = false; ajustarPila(v, e.cantidad); } });
    const destino = v ? posEstacionVasos(1).add(new THREE.Vector3(0, 0.006, 0)) : P.tolva.clone();
    for (let i = 0; i < n; i++) {
      const desde = P.hueco.clone().add(new THREE.Vector3(0, 0.004 + 0.002 * i, 0));
      const m = cilindro(0.011, 0.0018, colorMoneda(e.denominacion, i), desde.clone(), { metalness: 0.85, roughness: 0.3 });
      m.visible = false;
      escena.add(m);
      const r = abrir + i * 0.05;
      animar(0.01, () => { m.visible = true; }, { retraso: r });
      recorrer(m, [desde, P.tolva.clone(), destino], 0.4, { ease: caida, retraso: r, fin: () => escena.remove(m) });
    }
  };
  // Espera el instante de la simulacion y, por si el visor viene atrasado, que
  // el giro al agujero haya terminado.
  animar(0.001, () => {}, { retraso: Math.max(0, (e.en_ms || 0) / 1000), espera: () => faltaSuGiro(marca), fin: soltar });
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
  // Boca del embudo (e), fin del embudo (m) y final (b) de cada riel.
  const puntosRiel = (lado) => ({
    e: V([c.inicio[0] + lado * sE, c.inicio[1], c.inicio[2]]),
    b: V([c.fin[0] + lado * s, c.fin[1], c.fin[2]]),
    m: V([c.inicio[0] + lado * s, c.inicio[1] + (c.fin[1] - c.inicio[1]) * fEmbudo,
      c.inicio[2] + (c.fin[2] - c.inicio[2]) * fEmbudo]),
  });
  // Piezas reales (piezas/estructura.js): varilla de acero de 4 mm doblada en el embudo y
  // forrada con PTFE; cada riel apoya en dos postes 2020 (28 mm afuera, sobre pies
  // niveladores) con un cabezal impreso inclinado a la pendiente que lo toma por DEBAJO (nada
  // sobresale por encima de la varilla, por donde pasa la pestana). Los cuatro postes se atan
  // con un marco bajo de 2020 (travesanos a 3 cm, por debajo del vaso colgado; largueros a
  // 5 cm) y escuadras: sin el marco, cada poste solo se sostendria de su pie.
  let rielesHechos = false;
  try {
    const E = PIEZAS_ESTRUCTURA;
    const nuevo = new THREE.Group();
    const incl = THREE.MathUtils.radToDeg(Math.atan2(c.inicio[2] - c.fin[2], largoH));
    const dRiel = 0.028, h = 0.01;
    const postes = {};
    for (const lado of [-1, 1]) {
      const { e, m, b } = puntosRiel(lado);
      nuevo.add(E.crearRielCanaleta([e, m, b], { diametro: c.diametro_riel }));
      // Primer par a t = 0,14 (agente de solapes, 2026-09-27): en 0,12 el cabezal del lado +x
      // se metia 2 mm en la placa GY-530 de la cortina, que baja de canto justo encima.
      postes[lado] = [0.14, 0.55].map((t) => {
        const r = m.clone().lerp(b, t);
        const sop = E.crearSoporteCanaleta({ alturaRiel: r.y, dRiel, lado, inclinacion: incl });
        sop.position.set(r.x + lado * dRiel, 0, r.z);
        nuevo.add(sop);
        return sop.position.clone();
      });
    }
    const zT = 0.03, zL = 0.05;
    for (const k of [0, 1]) {
      const a = postes[-1][k], d = postes[1][k];
      const t = E.mallaPerfil2020(d.x - a.x - 2 * h, 'x');
      t.position.set((a.x + d.x) / 2, zT, a.z);
      nuevo.add(t);
      for (const lado of [-1, 1]) {
        const esc = E.crearEscuadra2020({ ejeA: [-lado, 0, 0], ejeB: [0, 0, 1] });
        esc.position.set(postes[lado][k].x - lado * h, zT + h, a.z);
        nuevo.add(esc);
      }
    }
    for (const lado of [-1, 1]) {
      const [a, d] = postes[lado];
      const l = E.mallaPerfil2020(Math.abs(d.z - a.z) - 2 * h, 'y');
      l.position.set(a.x, zL, (a.z + d.z) / 2);
      nuevo.add(l);
      for (const [p, q] of [[a, d], [d, a]]) {
        const sg = Math.sign(q.z - p.z);                 // hacia el otro poste (z de Three = -y)
        const esc = E.crearEscuadra2020({ ejeA: [0, -sg, 0], ejeB: [0, 0, 1] });
        esc.position.set(p.x, zL + h, p.z + sg * h);
        nuevo.add(esc);
      }
    }
    grupo.add(...nuevo.children.slice());
    rielesHechos = true;
  } catch (err) { console.warn('canaleta: rieles y soportes simples', err); }
  if (!rielesHechos) for (const lado of [-1, 1]) {
    const { e, m, b } = puntosRiel(lado);
    grupo.add(barra(e, m, c.diametro_riel / 2, PTFE, { roughness: 0.35 }));
    grupo.add(barra(m, b, c.diametro_riel / 2, PTFE, { roughness: 0.35 }));
    grupo.add(new THREE.Mesh(new THREE.SphereGeometry(c.diametro_riel / 2, 10, 10), mat(PTFE, { roughness: 0.35 })).translateX(m.x).translateY(m.y).translateZ(m.z));
    for (const t of [0.14, 0.55]) {
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
  // 34 mm afuera del balancin (agente de solapes, 2026-09-27): a 30 mm el pie nivelador del poste
  // se metia 2 mm en la base del tope derecho del muelle.
  const posteX = xBal + 0.034;
  const zPoste = pivote.z;
  // Punta del poste: 30 mm bajo el pivote, o mas abajo si hace falta para que la barra del soporte
  // (que pasa bajo la esquina mas baja del servo inclinado) llegue POR ENCIMA del taco del poste.
  const zTopPoste = Math.min(pivote.y - 0.03, alturaBarraSoporte(servoC) - 0.0025 - 0.006);
  // Poste del escape: 2020 sobre pie nivelador (antes un poste de 12 mm hasta el piso).
  try {
    const pie = PIEZAS_ESTRUCTURA.crearPieNivelador();
    pie.position.set(posteX, 0, zPoste);
    const alto = zTopPoste - PIEZAS_ESTRUCTURA.ALTO_PIE;
    const poste = PIEZAS_ESTRUCTURA.mallaPerfil2020(alto, 'z');
    poste.position.set(posteX, PIEZAS_ESTRUCTURA.ALTO_PIE + alto / 2, zPoste);
    grupo.add(pie, poste);
  } catch (err) {
    console.warn('canaleta: poste del escape simple', err);
    grupo.add(perfil(new THREE.Vector3(posteX, 0, zPoste), new THREE.Vector3(posteX, zTopPoste, zPoste), 0.012));
  }
  // El taco (Ø10 x 4 mm) va ENCIMA de la punta del poste (su centro 2 mm arriba); antes quedaba
  // medio metido en el perfil.
  soporteServo(grupo, servoC, new THREE.Vector3(posteX, zTopPoste + 0.002, zPoste), 'servo_compuerta_canaleta');
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
  const m = p.meta;
  const lado = [-Math.sin(m.rumbo), Math.cos(m.rumbo)];
  let baseMastil = Vxyz(m.x + lado[0] * (p.ancho / 2 + 0.03), m.y + lado[1] * (p.ancho / 2 + 0.03), 0);
  P.obstaculos = [];
  try {
    // Pieza detallada (piezas/pista.js): lamina con borde, cinta de 19 mm con sus costuras,
    // franjas de cinta, muros de ladrillo, bandera con base y el piso del salon alrededor.
    // Usa la MISMA linea central de la simulacion (G.pista.linea): no cambia el trazado.
    const pz = PIEZAS_PISTA.crearPista({
      linea: p.linea, ancho: p.ancho, anchoLinea: p.ancho_linea, obstaculos: p.obstaculos,
      franjaMeta: p.franja_meta, franjaGiro: p.franja_giro, meta: m,
      // De la configuracion (sim/geometria.py), no escritos a mano en la pieza.
      ...(p.obstaculos[0] && p.obstaculos[0].grueso ? { grueso: p.obstaculos[0].grueso } : {}),
      ...(p.margen_zona_libre ? { margenPiso: p.margen_zona_libre } : {}),
      // Detras de la salida la lamina llega solo hasta 5 mm mas alla de la cola del carro
      // estacionado (agente de solapes, 2026-09-27): con los 12 cm de antes pasaba por debajo
      // de las bases de los topes del muelle y de un pie de la canaleta, que van al piso.
      ...(G.vehiculo && G.vehiculo.largo ? { antesSalida: G.vehiculo.largo / 2 + 0.005 } : {}),
    });
    for (const h of [...pz.children]) grupo.add(h);
    P.obstaculos = p.obstaculos.map((_, i) => grupo.getObjectByName(`muro_${i + 1}`));
    const am = grupo.getObjectByName('ancla_mastil_meta');
    if (am) baseMastil = am.position.clone();
  } catch (e) {
    console.warn('pieza pista: se usa el modelo simple', e);
    grupo.clear();
    P.obstaculos = [];
    grupo.add(cinta2D(p.linea, p.ancho + 0.02, 0.0012, 0x9a3b30, { roughness: 1 }));   // borde
    grupo.add(cinta2D(p.linea, p.ancho, 0.0016, COLOR.pista, { roughness: 1 }));
    grupo.add(cinta2D(p.linea, p.ancho_linea, 0.002, 0x0a0a0a, { roughness: 0.9 }));

    const ladrillo = texturaLadrillo();
    p.obstaculos.forEach((o, i) => {
      // El muro atraviesa la linea: largo "a lo ancho" de la pista, delgado a lo largo.
      const muro = new THREE.Mesh(new THREE.BoxGeometry(0.03, o.alto, o.largo), new THREE.MeshStandardMaterial({ map: ladrillo, roughness: 0.9 }));
      muro.position.copy(Vxyz(o.x, o.y, o.alto / 2));
      muro.rotation.y = o.rumbo;
      muro.castShadow = true;
      grupo.add(muro);
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
  }
  p.obstaculos.forEach((o, i) => {
    const et = etiqueta(`Obstáculo ${i + 1}`, { alto: 0.02, color: '#e5534b' });
    et.position.copy(Vxyz(o.x, o.y, o.alto + 0.03));
    grupo.add(et);
  });
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
  // El piso del salon no es parte de la pista (no se enciende al resaltarla).
  registrar('pista', ...grupo.children.filter((o) => !o.isSprite && o.name !== 'piso_pista'));
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
// Pieza detallada: piezas/carro.js (crearMuelleCarga), mismas medidas que
// sim/vehiculo_sim.py (_crear_muelle).
function construirMuelle() {
  const v = G.vehiculo;
  const s = G.pista.salida;
  let muelle = new THREE.Group();   // mismo marco local que el carro: +x adelante (sim)
  const L = v.largo, r = v.diametro_rueda / 2;
  // Las guias tocan los RODILLOS de las esquinas traseras (nunca las llantas),
  // con la holgura por lado de la configuracion (vehiculo.muelle_*, la misma que usa
  // sim/vehiculo_sim.py; los numeros de respaldo son los de antes, por si la geometria es vieja).
  const largoBoca = v.muelle_largo_boca ?? 0.20, abreBoca = v.muelle_abre_boca ?? 0.045;
  const guiaY = v.rodillo_guia_y + v.rodillo_guia_radio + (v.muelle_holgura ?? 0.003);
  const alto = 0.02, esp = 0.006;
  const xRueda = -L * 0.18;
  // Tramo recto desde la cola (donde quedan los rodillos) y boca de ~13 grados.
  const x0 = -L / 2 - 0.004, x1 = xRueda + r + 0.015, x2 = x1 + largoBoca;   // mismas medidas que sim/vehiculo_sim.py
  const xT = -L / 2 - 0.006;
  try {
    // Topes: bloque de -L/2-11 a -L/2-3 mm y espuma de 6 mm (la caja de la simulacion va de
    // -L/2-17 a -L/2-3); paran el carro por los bloques de sus rodillos guia.
    muelle = PIEZAS_CARRO.crearMuelleCarga({
      x0, x1, x2, guiaY, abre: abreBoca, alto, esp,
      topes: [-1, 1].map((lado) => ({ x0: xT - 0.011, x1: xT - 0.003, y: lado * 0.052, ancho: 0.022, altoTope: r + 0.012, espuma: 0.006 })),
    });
    const partes = [];
    muelle.traverse((o) => { if (o.isMesh) partes.push(o); });
    registrar('muelle_carga', ...partes);
  } catch (e) {
    console.warn('pieza muelle: se usa el modelo simple', e);
    muelle = new THREE.Group();
    for (const lado of [-1, 1]) {
      const recto = caja(x1 - x0, esp, alto, COLOR.impreso, Vxyz((x0 + x1) / 2, lado * (guiaY + esp / 2), alto / 2));
      const ptfe = caja(x1 - x0, 0.0008, alto, 0xf1f1ee, Vxyz((x0 + x1) / 2, lado * (guiaY + 0.0004), alto / 2));
      muelle.add(ptfe);
      const a = Vxyz(x1, lado * (guiaY + esp / 2), alto / 2), b = Vxyz(x2, lado * (guiaY + abreBoca + esp / 2), alto / 2);
      const boca = caja(a.distanceTo(b), esp, alto, COLOR.impreso, a.clone().lerp(b, 0.5));
      boca.rotation.y = Math.atan2(-(b.z - a.z), b.x - a.x);   // girar en Y (Three) = girar en z (sim)
      muelle.add(recto, boca);
      registrar('muelle_carga', recto, boca);
      const tope = caja(0.01, 0.022, r + 0.012, 0x30363d, Vxyz(xT - 0.008, lado * 0.052, (r + 0.012) / 2));
      const espuma = caja(0.006, 0.022, 0.014, 0xe3c565, Vxyz(xT, lado * 0.052, r + 0.004), { roughness: 1 });
      muelle.add(tope, espuma);
      registrar('muelle_carga', tope, espuma);
    }
  }
  muelle.name = 'muelle';
  const et = etiqueta('Muelle de carga', { alto: 0.01, color: '#e3c565' });
  et.position.copy(Vxyz(x2 - 0.02, -(guiaY + 0.07), 0.03));   // al costado: no tapa la del ESP32
  muelle.add(et);
  muelle.position.copy(Vxyz(s.x, s.y, 0));
  muelle.rotation.y = s.rumbo;
  escena.add(muelle);
}

// Carro de entrega (boceto de lo que se va a construir; piezas en piezas/carro.js,
// piezas/sensores.js y piezas/electronica.js; cotas en PIEZAS_CARRO.disposicionCarro).
// Placa de acrilico de 3 mm a 11,5 mm POR ENCIMA del eje (como los kits de 2 ruedas: los
// motorreductores TT cuelgan debajo en sus soportes en T), con un hueco por donde baja el
// fondo del vaso colgado; segundo piso de placa perforada sobre separadores de laton con el
// ESP32 en su placa GVS; debajo, encoders H206 bajo el disco de 20 ranuras de cada eje,
// rueda loca de bola, los 5 TCRT5000 y los rodillos guia; adelante, HC-SR04 y VL53L0X en
// una escuadra; atras, la cuna.
function construirCarro() {
  const v = G.vehiculo;
  const s = G.pista.salida;
  const carro = new THREE.Group();   // marco local: +x adelante, +y izquierda, z arriba (sim)
  carro.name = 'carro';
  P.carroGrupo = carro;
  const L = v.largo, W = v.ancho, r = v.diametro_rueda / 2;
  const c = G.canaleta;
  const zRiel = c.fin[2] - c.caida_entrada;
  const D = PIEZAS_CARRO.disposicionCarro({ largo: L, ancho: W, diametroRueda: v.diametro_rueda, zRiel,
    vasoDiametro: G.vaso.diametro, vasoAltura: G.vaso.altura });
  const { zPlaca, zPiso2, xRueda } = D;
  const zArriba = D.zBaseArriba;
  const xCola = -L / 2;               // extremo trasero: ahi empieza la cuna
  const mallas = (g) => { const ms = []; g.traverse((o) => { if (o.isMesh) ms.push(o); }); return ms; };
  // Orientacion de una pieza "de ficha": hacia donde van sus ejes x, y, z (en la simulacion).
  const base = (fx, fy, fz) => new THREE.Quaternion().setFromRotationMatrix(
    new THREE.Matrix4().makeBasis(Vxyz(...fx), Vxyz(...fz), Vxyz(...fy).negate()));
  const pieza = (crear, opciones) => (typeof crear === 'function' ? () => crear(opciones) : null);
  // Monta una pieza detallada con sus anclas pin_<dev>_<PIN> (mismos pines que la plantilla de
  // sim/conexiones.py) y registra cada pin para los cables; si la pieza falla o le falta un
  // pin, queda el modulo simple de siempre (construirModulo) o el `respaldo`.
  const montar = (dev, crear, pos, quat, { sensorId = null, idComponente = null, etiquetaSobre = 0, espejo = false, respaldo = null } = {}) => {
    let g = null;
    try {
      if (!crear) throw new Error('pieza no disponible');
      g = crear();
      g.position.copy(pos);
      g.quaternion.copy(quat);
      if (espejo) g.scale.z = -1;       // espejo en y de la simulacion (Three z = -y)
      carro.add(g);
      carro.updateMatrixWorld(true);
      const inv = carro.matrixWorld.clone().invert();
      const aCarro = (o) => inv.clone().multiply(o.matrixWorld);
      const eje = new THREE.Vector3(1, 0, 0).transformDirection(aCarro(g));
      const pines = plantilla(dev).pines.map((p) => {
        const a = g.getObjectByName(`pin_${dev}_${p.n}`);
        if (!a) throw new Error(`falta pin_${dev}_${p.n}`);
        return [p, a];
      });
      for (const [p, a] of pines) {
        const dir = (a.userData.dir || new THREE.Vector3(0, 1, 0)).clone().transformDirection(aCarro(a.parent));
        pinSuelto(`${dev}.${p.n}`, carro, new THREE.Vector3().setFromMatrixPosition(aCarro(a)), dir, p.tipo, eje);
      }
      if (sensorId) g.traverse((o) => { if (o.isMesh) o.userData.sensorId = sensorId; });
      if (idComponente) registrar(idComponente, ...mallas(g));
      MODULOS[dev] = g;
      if (etiquetaSobre) {
        const et = etiqueta(G.conexiones.dispositivos[dev].nombre, { alto: 0.0042, alcance: 0.55 });
        et.position.copy(pos).add(new THREE.Vector3(0, etiquetaSobre, 0));
        carro.add(et);
      }
      return g;
    } catch (e) {
      if (g) carro.remove(g);
      console.warn(`pieza ${dev}: se usa el modelo simple`, e);
      return respaldo ? respaldo() : construirModulo(dev, carro, pos, quat, { sensorId, idComponente, etiquetaSobre });
    }
  };

  // ---- Chasis de acrilico con sus agujeros, y segundo piso (placa perforada)
  // sobre 4 separadores de laton, solo en la mitad delantera: la de atras es la
  // bahia de carga donde cuelga el vaso.
  const wIr = (v.sensores_linea - 1) * v.separacion_sensores_linea / MM + 14;   // largo del modulo de 5 TCRT5000
  try {
    const mm = (x) => x / MM;
    const huecos = [
      ...D.separadoresPiso2.map(([x, y]) => [mm(x), mm(y), 3.2]),
      ...[-11, 11].map((y) => [mm(D.xLoca), y, 3.2]),                          // rueda loca
      ...[-1, 1].map((k) => [mm(D.xIr + 0.003), k * (wIr / 2 - 3), 3.2]),      // infrarrojos de linea
      ...[-1, 1].map((k) => [mm(xCola + 0.006), k * 52, 3.2]),                 // bloques de los rodillos
    ];
    const ranuras = [], discos = [];
    for (const k of [-1, 1]) {
      for (const dy of [-10.9, 10.9]) ranuras.push([mm(xRueda) + 24, k * (mm(D.yMotor) + dy), 10, 3.2, true]);
      const yd = [k * (mm(D.yDisco) - 2), k * (mm(D.yDisco) + 2)].sort((a, b) => a - b);
      discos.push([mm(xRueda) - 14, mm(xRueda) + 14, yd[0], yd[1]]);
    }
    const chasis = PIEZAS_CARRO.crearChasisCarro({ largo: mm(L), ancho: mm(W), espesor: mm(D.eBase), huecos, ranuras,
      pasacables: D.agujerosCables.map(([x, y]) => [mm(x), mm(y)]), vaso: { x: mm(D.xVaso), r: mm(D.rHuecoVaso) }, discos });
    chasis.position.copy(Vxyz(0, 0, D.zBaseAbajo));
    carro.add(chasis);
    const piso2 = PIEZAS_CARRO.crearPerfboard({ largo: 60, ancho: mm(W * 0.8), huecos: D.separadoresPiso2.map(([x, y]) => [mm(x - 0.05), mm(y)]) });
    piso2.position.copy(Vxyz(0.05, 0, zPiso2 - 0.0008));
    carro.add(piso2);
    for (const [x, y] of D.separadoresPiso2) {
      const sep = PIEZAS_CARRO.crearSeparadorM3({ alto: mm(zPiso2 - 0.0008 - zArriba) });
      sep.position.copy(Vxyz(x, y, zArriba));
      carro.add(sep);
    }
  } catch (e) {
    console.warn('pieza chasis del carro: se usa el modelo simple', e);
    const chasis = caja(L, W, 0.003, 0x33414f, Vxyz(0, 0, zPlaca), { roughness: 0.35, metalness: 0.1 });
    chasis.receiveShadow = true;
    carro.add(chasis, caja(0.06, W * 0.8, 0.0016, 0x2f6b3a, Vxyz(0.05, 0, zPiso2), { roughness: 0.8 }));
    for (const [dx, dy] of D.separadoresPiso2) {
      carro.add(barra(Vxyz(dx, dy, zArriba), Vxyz(dx, dy, zPiso2 - 0.0008), 0.0024, 0xc8a24a, { metalness: 0.8 }));
    }
  }

  // ---- Motorreductores TT (en sus soportes en T, bajo la placa) con su rueda
  // de 65 mm (se ven girar), el disco de 20 ranuras en la punta interior del
  // eje (gira con la rueda) y el encoder H206 debajo del disco, en su soporte.
  P.ruedas = [];
  for (const lado of [-1, 1]) {
    const motor = lado > 0 ? 'motor_izq' : 'motor_der';
    montar(motor, pieza(PIEZAS_CARRO.crearMotorTT, { id: motor, lado, hastaPlaca: (D.zBaseAbajo - r) / MM, espesorPlaca: D.eBase / MM }),
      Vxyz(xRueda, lado * D.yMotor, r), new THREE.Quaternion(), { idComponente: 'motores_carro' });
    const etMotor = etiqueta(`Motor TT ${lado > 0 ? 'izq.' : 'der.'}`, { alto: 0.0042, alcance: 0.3 });
    etMotor.position.copy(Vxyz(xRueda + 0.045, lado * D.yMotor, 0.012));
    carro.add(etMotor);

    let rueda;
    try {
      // Ancho de la llanta: config vehiculo.ancho_rueda_mm (el mismo cilindro que choca en PyBullet).
      rueda = PIEZAS_CARRO.crearRuedaTT({ diametro: v.diametro_rueda / MM, ancho: (v.ancho_rueda ?? 0.026) / MM, lado,
        ejeAdentro: (D.yRueda - 0.013 - (D.yMotor - 0.018)) / MM });
      registrar('motores_carro', ...mallas(rueda));
      // Disco del encoder en la punta interior del eje, con el cubo hacia el reductor.
      const disco = PIEZAS_SENSORES_CARRO.crearDiscoEncoder20({ sensorId: 'encoders' });
      disco.position.y = lado * (D.yRueda - D.yDisco);
      disco.rotation.x = lado > 0 ? Math.PI : 0;
      rueda.add(disco);
    } catch (e) {
      console.warn('pieza rueda TT: se usa el modelo simple', e);
      rueda = new THREE.Group();
      rueda.add(cilindro(r, v.ancho_rueda ?? 0.026, 0x111111, new THREE.Vector3(0, 0, 0), { roughness: 0.95 }));
      rueda.add(cilindro(r * 0.72, 0.027, 0xf2c230, new THREE.Vector3(0, 0, 0), { roughness: 0.5 }));
      registrar('motores_carro', ...rueda.children);
    }
    rueda.position.copy(Vxyz(xRueda, lado * D.yRueda, r));
    rueda.rotation.x = Math.PI / 2;
    carro.add(rueda);
    P.ruedas.push(rueda);

    // H206 boca arriba bajo el disco: la horquilla abraza el borde de abajo del
    // disco (el haz pasa por la corona de ventanas, 11,5 mm bajo el eje) y la
    // placa sale hacia atras, apoyada en una columna impresa que baja de la placa.
    const enc = lado > 0 ? 'enc_izq' : 'enc_der';
    montar(enc, pieza(PIEZAS_SENSORES_CARRO.crearEncoderH206, { id: enc, sensorId: 'encoders' }),
      Vxyz(xRueda - 0.0085, lado * D.yEncoder, D.zEncoder), yaw(180), { sensorId: 'encoders', espejo: lado < 0, etiquetaSobre: 0.012 });
    try {
      const sop = PIEZAS_CARRO.crearSoporteEncoder({ alto: (D.zBaseAbajo - D.zEncoder + 0.002) / MM, lado });
      sop.position.copy(Vxyz(xRueda - 0.0231, lado * (D.yEncoder - 0.011), D.zEncoder - 0.002));
      carro.add(sop);
    } catch (e) { console.warn('pieza soporte del encoder', e); }
  }

  // Rodillos guia (rodamiento 623) en las esquinas traseras, un poco mas
  // afuera que las llantas: son lo que empujan las guias del muelle. Su bloque
  // impreso queda al ras de la cola: es lo que toca el tope con espuma.
  for (const lado of [-1, 1]) {
    try {
      const rod = PIEZAS_CARRO.crearRodilloGuia623({ lado, subir: (D.zBaseAbajo - 0.012) / MM,
        adentro: [(v.rodillo_guia_y - 0.058) / MM, (v.rodillo_guia_y - 0.046) / MM], atras: 8, adelante: 4 });
      rod.position.copy(Vxyz(-L / 2 + 0.008, lado * v.rodillo_guia_y, 0.012));
      carro.add(rod);
      registrar('rodillos_guia', ...mallas(rod));
    } catch (e) {
      console.warn('pieza rodillo guia: se usa el modelo simple', e);
      const rod = cilindro(v.rodillo_guia_radio, 0.01, 0xc9ccd1, Vxyz(-L / 2 + 0.008, lado * v.rodillo_guia_y, 0.012), { metalness: 0.8 });
      carro.add(rod);
      registrar('rodillos_guia', rod);
    }
  }

  // ---- Rueda loca de bola (acero) con su brida, bajo el frente.
  try {
    const loca = PIEZAS_CARRO.crearRuedaLocaBola({ alto: D.zBaseAbajo / MM });
    loca.position.copy(Vxyz(D.xLoca, 0, D.zBaseAbajo));
    carro.add(loca);
  } catch (e) {
    console.warn('pieza rueda loca: se usa el modelo simple', e);
    const loca = new THREE.Mesh(new THREE.SphereGeometry(0.008, 16, 16), mat(COLOR.plata, { metalness: 0.9, roughness: 0.2 }));
    loca.position.copy(Vxyz(D.xLoca, 0, 0.008));
    carro.add(loca, barra(Vxyz(D.xLoca, 0, 0.016), Vxyz(D.xLoca, 0, D.zBaseAbajo), 0.004, 0x30363d));
  }

  // ---- Energia: porta-baterias 2 x 18650 (7,4 V) sobre la placa, bajo el
  // segundo piso (celdas a lo ancho, delante de la mampara de la cuna), e
  // interruptor con fusible de 3 A al costado izquierdo (se alcanza desde afuera).
  const [xBat, yBat] = D.bateria;
  montar('bateria', pieza(PIEZAS_ELECTRONICA.crearPortaBaterias18650x2, { id: 'bateria' }), Vxyz(xBat, yBat, zArriba), yaw(0), {
    idComponente: 'bateria_carro',
    respaldo: () => {
      const zBat = zArriba + 0.006;
      const portaBat = caja(0.041, 0.077, 0.012, 0x151515, Vxyz(xBat, yBat, zBat));
      carro.add(portaBat);
      registrar('bateria_carro', portaBat);
      pinSuelto('bateria.B+', carro, Vxyz(xBat + 0.0205, 0.03, zBat), new THREE.Vector3(1, 0, 0), 'pad');
      pinSuelto('bateria.B-', carro, Vxyz(xBat + 0.0205, -0.03, zBat), new THREE.Vector3(1, 0, 0), 'pad');
      return portaBat;
    },
  });
  const etBat = etiqueta('2 × 18650 (7,4 V) con BMS', { alto: 0.0042, alcance: 0.3 });
  etBat.position.copy(Vxyz(xBat, 0, zArriba + 0.024));
  carro.add(etBat);
  montar('interruptor', pieza(PIEZAS_ELECTRONICA.crearInterruptorFusible, { id: 'interruptor' }),
    Vxyz(D.interruptor[0], D.interruptor[1], zArriba), yaw(0), { idComponente: 'interruptor_carro', etiquetaSobre: 0.02 });

  // ---- Electronica: el ESP32 DevKit de 30 pines en su placa GVS (la de los
  // labs), en el segundo piso; el puente H TB6612, en el de abajo, sobre dos separadores.
  const xEsp = 0.05;
  construirModulo('esp32_carro', carro, Vxyz(xEsp, 0, zPiso2 + 0.0008), yaw(90), { idComponente: 'esp32_carro', etiquetaSobre: 0.03 });
  const [xTb, yTb] = D.tb6612;
  montar('tb6612', pieza(PIEZAS_ELECTRONICA.crearTB6612FNG, { id: 'tb6612' }), Vxyz(xTb, yTb, zArriba + 0.002), yaw(0),
    { idComponente: 'puente_h_carro', etiquetaSobre: 0.022 });
  for (const [dx, dy] of [[-0.008, -0.008], [0.008, 0.008]]) carro.add(cilindro(0.0015, 0.002, 0xc8a24a, Vxyz(xTb + dx, yTb + dy, zArriba + 0.001)));

  // ---- Arreglo de 5 infrarrojos TCRT5000 bajo el frente, colgado de dos
  // separadores de laton: la cara de los sensores queda a 7 mm del piso.
  P.irLinea = [];
  const n = v.sensores_linea, sep = v.separacion_sensores_linea;
  const xIr = D.xIr;
  const zIr = 0.007 + 0.0078;          // cara de abajo de la placa (el TCRT5000 baja 7,8 mm)
  const ir5 = montar('ir_linea', pieza(PIEZAS_SENSORES_CARRO.crearArregloTCRT5000, { id: 'ir_linea', sensorId: 'linea_ir', n, paso: sep / MM }),
    Vxyz(xIr + 0.003, 0, zIr), new THREE.Quaternion(), { sensorId: 'linea_ir' });
  if (ir5.userData.leds) {
    P.irLinea = ir5.userData.leds;
    for (const k of [-1, 1]) {
      const sepIr = PIEZAS_CARRO.crearSeparadorM3({ alto: (D.zBaseAbajo - zIr - 0.0016) / MM });
      sepIr.position.copy(Vxyz(xIr + 0.003, k * (wIr / 2 - 3) * MM, zIr + 0.0016));
      carro.add(sepIr);
    }
  } else {
    for (let i = 0; i < n; i++) {
      const led = new THREE.Mesh(new THREE.SphereGeometry(0.0012, 10, 10), new THREE.MeshBasicMaterial({ color: 0x30363d }));
      led.position.copy(Vxyz(xIr - 0.005, (i - (n - 1) / 2) * sep, 0.0142));
      led.userData.sensorId = 'linea_ir';
      carro.add(led);
      P.irLinea.push(led);
    }
  }
  const etIr = etiqueta('5 × TCRT5000 (línea)', { alto: 0.0042, alcance: 0.3 });
  etIr.position.copy(Vxyz(xIr + 0.02, 0, 0.005));
  carro.add(etIr);

  // ---- Adelante, en una escuadra impresa: ultrasonico HC-SR04 (respaldo) y
  // encima el laser VL53L0X (principal: mide cada 33 ms, hasta ~1,2 m). Los
  // dos miran hacia adelante; el header del laser sale por la ventana de la escuadra.
  const xFrente = D.xFrente, zUs = D.zUs;
  try {
    const z = (zz) => (zz - zArriba) / MM;
    const esc = PIEZAS_CARRO.crearEscuadraFrontal({ alto: 33, ancho: 50, pie: 14, ventana: [-9, 9, z(0.066), z(0.0715)],
      separadores: [[-21, z(zUs - 0.001 + 0.0085), 2.5], [21, z(zUs - 0.001 + 0.0085), 2.5],
        [-10.35, z(D.zTof - 0.0018 + 0.0016), 2.9], [10.35, z(D.zTof - 0.0018 + 0.0016), 2.9]] });
    esc.position.copy(Vxyz(xFrente - 0.0025, 0, zArriba));
    carro.add(esc);
  } catch (e) {
    console.warn('pieza escuadra frontal: se usa el modelo simple', e);
    carro.add(caja(0.0016, 0.03, 0.045, 0x20242b, Vxyz(xFrente - 0.004, 0, zArriba + 0.02)));
  }
  montar('hcsr04', pieza(PIEZAS_SENSORES_CARRO.crearHCSR04, { id: 'hcsr04', sensorId: 'ultrasonico' }),
    Vxyz(xFrente, 0, zUs - 0.001), base([0, 1, 0], [0, 0, 1], [1, 0, 0]), { sensorId: 'ultrasonico' });
  montar('vl53_frontal', pieza(PIEZAS_SENSORES_CARRO.crearVL53L0X, { id: 'vl53_frontal', sensorId: 'laser_frontal' }),
    Vxyz(xFrente + 0.002, 0, D.zTof - 0.0018), base([0, 1, 0], [0, 0, -1], [-1, 0, 0]), { sensorId: 'laser_frontal' });
  const etUs = etiqueta('HC-SR04 · VL53L0X', { alto: 0.0042, alcance: 0.3 });
  // 3 cm por delante del frente y a 7 cm del piso (agente de solapes, 2026-09-27): a 8,8 cm, justo
  // encima del frente, se montaba sobre la etiqueta del puente H TB6612FNG.
  etUs.position.copy(Vxyz(xFrente + 0.03, 0, 0.07));
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
  conoTof.position.copy(Vxyz(xFrente + 0.004 + v.distancia_frenado / 2, 0, D.zTof));
  conoTof.userData.sensorId = 'laser_frontal';
  carro.add(conoTof);
  P.conoTof = conoTof;
  // Conos de error probable (nominal + ~7 grados: el HC-SR04 tiene lobulos
  // laterales; el laser, desalineacion de montaje).
  const adelante = new THREE.Vector3(1, 0, 0);
  const [, errUS] = conosSensor(Vxyz(xFrente + 0.012, 0, zUs), adelante, v.distancia_obstaculo, 7.5, 15);
  const [, errTof] = conosSensor(Vxyz(xFrente + 0.003, 0, D.zTof), adelante, v.distancia_frenado, 12.5, 17.5, COLOR.ambar);
  errUS.userData.sensorId = 'ultrasonico'; errTof.userData.sensorId = 'laser_frontal';
  carro.add(errUS, errTof);
  // Infrarrojos de linea: a 7 mm del piso (el TCRT5000 ve hasta ~15 mm).
  for (let i = 0; i < n; i++) {
    const yy = (i - (n - 1) / 2) * sep;
    for (const cn of conosSensor(Vxyz(xIr, yy, 0.007), new THREE.Vector3(0, -1, 0), 0.007, 15, 20)) {
      cn.userData.sensorId = 'linea_ir';
      carro.add(cn);
    }
  }

  // Cuna (punto 13, usuario 2026-09-26): los mismos rieles de la canaleta,
  // forrados con cinta de PTFE, pero 3 mm MAS BAJOS que el final de la
  // canaleta y con la entrada en embudo (arrancan 4 mm mas separados y se
  // cierran en 20 mm): si el carro queda algo corrido o desnivelado, la
  // pestana cae sobre ellos en vez de chocar con su punta. Soporte de 4
  // puntos a media altura del vaso (usuario, 2026-09-26): espuma adelante (en
  // la mampara), lengueta atras y dos guias con PTFE a los costados. Lengueta
  // (trinquete pasivo del lado -y): al entrar, el cuerpo del vaso la empuja
  // hacia adelante; el resorte la devuelve DETRAS del cuerpo y un pasador de
  // tope no la deja abrirse hacia atras. Sin sensor ni servo.
  const sepR = c.separacion_rieles / 2, sepE = c.separacion_entrada / 2;
  const xEmb = xCola + 0.02;
  // Infrarrojo de la cuna (TCRT5000): mira al costado del vaso cargado desde
  // 6 mm (ve hasta ~15 mm), atornillado a una columna de la cuna.
  const yOptIr = G.vaso.diametro / 2 + 0.006;
  const zIrCuna = zRiel - 0.03;
  const xIrCuna = xCola / 2 + 0.012;
  try {
    const cuna = PIEZAS_CARRO.crearCunaCarro({ xCola, zBase: zArriba, zRiel, sepR, sepE, dRiel: c.diametro_riel, xEmb,
      xMampara: D.xMampara, zMedio: D.zMedio, rCuerpo: G.vaso.diametro / 2,
      irCol: { x: xIrCuna - 0.001, y: yOptIr + 0.0078 + 0.0082, z: zIrCuna, yModulo: yOptIr + 0.0078 + 0.0016 } });
    carro.add(cuna);
    registrar('cuna_carro', ...mallas(cuna));
    P.lengueta = cuna.getObjectByName('lengueta');
  } catch (e) {
    console.warn('pieza cuna del carro: se usa el modelo simple', e);
    for (const lado of [-1, 1]) {
      const e0 = Vxyz(xCola, lado * sepE, zRiel), m = Vxyz(xEmb, lado * sepR, zRiel), b = Vxyz(0.016, lado * sepR, zRiel);
      const tramos = [barra(e0, m, c.diametro_riel / 2, 0xf1f1ee, { roughness: 0.35 }), barra(m, b, c.diametro_riel / 2, 0xf1f1ee, { roughness: 0.35 })];
      carro.add(...tramos);
      registrar('cuna_carro', ...tramos);
    }
    const lengueta = new THREE.Group();
    lengueta.position.copy(Vxyz(xCola + 0.016, -(sepE + 0.009), zRiel - 0.035));
    lengueta.add(barra(new THREE.Vector3(0, 0, 0), Vxyz(0.016, 0.026, 0), 0.0025, 0xd9261a));
    carro.add(lengueta);
    P.lengueta = lengueta;
  }
  const ir = montar('ir_cuna', pieza(PIEZAS_SENSORES_CARRO.crearIRCuna, { id: 'ir_cuna', sensorId: 'cuna' }),
    Vxyz(xIrCuna, yOptIr + 0.0078, zIrCuna), base([1, 0, 0], [0, 0, -1], [0, 1, 0]), { sensorId: 'cuna' });
  for (const cn of conosSensor(Vxyz(xCola / 2, yOptIr, zIrCuna), new THREE.Vector3(0, 0, 1), 0.012, 15, 20)) {   // hacia -y (el vaso)
    cn.userData.sensorId = 'cuna';
    carro.add(cn);
  }
  P.irCuna = ir;

  // Vaso que lleva el carro (visible mientras va cargado).
  const vasoCarro = crearVaso('carro');
  vasoCarro.tapa.visible = true;
  vasoCarro.et.userData.oculta = true;   // el vaso del carro no lleva su rotulo (ver actualizarEtiquetas)
  vasoCarro.grupo.position.copy(Vxyz(D.xVaso, 0, zRiel - G.vaso.altura));
  vasoCarro.grupo.visible = false;
  carro.add(vasoCarro.grupo);
  P.vasoCarro = vasoCarro;
  // Colocar el carro en la salida: la conversion de ejes hace que girar
  // `rumbo` alrededor de z (sim) sea girar `rumbo` alrededor de y (Three).
  carro.position.copy(Vxyz(s.x, s.y, 0));
  carro.rotation.y = s.rumbo;
  P.carroPose = { x: s.x, y: s.y, r: s.rumbo, ox: s.x, oy: s.y, or: s.rumbo };
  carro.traverse((o) => { if (o.isMesh && !o.material.transparent) o.castShadow = true; });
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
  let partes = tpl.partes || [];
  let pieza = null;                 // pieza detallada montada en la placa (se resalta con ella)
  if (partes[0]?.nombre === 'ESP32 DevKit') {
    // Placa GVS con su ESP32: el ESP32 es la pieza detallada (piezas/electronica.js) sobre los
    // headers hembra (9 mm) + el separador de su header macho (2,5 mm). Las 5 primeras
    // "partes" de la plantilla eran el ESP32 simple; si la pieza falla, se dibujan esas.
    try {
      const nPines = tpl.pines.filter((p) => p.n.startsWith('esp.')).length;   // las dos filas
      const esp = PIEZAS_ELECTRONICA.crearESP32DevKit({ pines: nPines, idComponente, sensorId });
      esp.position.copy(Vxyz(0, 0, (T + 9 + 2.5) * MM));
      g.add(esp);
      pieza = esp;
      partes = partes.slice(5);
    } catch (e) {
      console.warn('pieza ESP32 DevKit: se usa el modelo simple', e);
    }
  }
  for (const pt of partes) {
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
        if (p.acodado) {
          // Header acodado (90 grados): acostado sobre la placa, la punta sale hacia `acodado`.
          const [ax, ay] = p.acodado;
          lote(padre, 'base', matriz(p.x + ax * 1.9, p.y + ay * 1.9, T + 1.27));
          tip = aPadre(p.x + ax * 9.2, p.y + ay * 9.2, T + 1.27); dir = dirPadre(ax, ay, 0);
          break;
        }
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
    // En el carro alcance 0.55 (se ven hasta ~1 m): la vista del carro quedo a ~0,6 m.
    const et = etiqueta(info.nombre, enCarro ? { alto: 0.0042, alcance: 0.55 } : { alto: 0.0058, alcance: 0.4 });
    et.position.copy(aPadre(0, 0, T + etiquetaSobre / MM));
    padre.add(et);
  }
  if (idComponente) registrar(idComponente, placa, pieza);
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
  // Gabinete real (piezas/control.js): placa de montaje de aluminio, paredes de acrilico de 3 mm
  // con esquineros de aluminio, tapa de policarbonato atornillada (transparente: se ve todo y no
  // se puede clicar), prensaestopas PG en los mismos puntos por donde entran los cables,
  // ventilador de 40 mm que saca el aire junto a los drivers y rejilla de entrada a la izquierda.
  // Si la pieza falla, quedan el piso y las 4 paredes translucidas de antes.
  let gabinete = null, piso, paredes;
  try {
    gabinete = PIEZAS_CONTROL.crearGabineteControl({
      largo: ax / MM, ancho: ay / MM, alto: az / MM,
      prensaestopas: [
        // Adelante: senales G1 (el mazo del portico, PG16), motores, servos y cortos (PG7).
        ...[[0.2, 'PG7'], [0.28, 'PG7'], [0.297, 'PG7'], [0.3338, 'PG16'], [0.3725, 'PG7'], [0.405, 'PG7']]
          // PG16 a 16 mm: su rosca (22,5 mm) queda entera sobre la placa de montaje (a 14 mm se metia
          // 0,25 mm en ella). Los PG7 a 14 mm dejan 5,3 mm libres bajo la contratuerca.
          .map(([x, tipo]) => ({ pared: 'frente', u: (x - bx) / MM, z: tipo === 'PG16' ? 16 : 14, tipo, verticesArriba: tipo !== 'PG16' })),
        // A la izquierda, a 52 mm: la contratuerca (8,7 mm a los vertices) queda por ENCIMA de la
        // canaleta lateral (32,5 mm con su tapa) y de los hilos que entran en ella desde las placas.
        { pared: 'izq', u: -47, z: 52, tipo: 'PG7' },     // USB del ESP32
        { pared: 'izq', u: -79, z: 52, tipo: 'PG7' },     // luz 5 V (anillo)
        // La red NO usa prensaestopas: el cable de poder trae su conector C13 y se enchufa a la
        // entrada IEC C14 de la pared derecha (antes habia un PG9 vacio al lado).
      ],
      // Ventilador a 54 mm: las tuercas de abajo (z = 38 mm) quedan sobre la canaleta lateral derecha.
      ventilador: { pared: 'der', u: -50, z: 54 },
      rejilla: { pared: 'izq', u0: 20, u1: 92, z0: 38, z1: 64 },
    });
    gabinete.position.copy(Vxyz(bx, by, 0));
    grupo.add(gabinete);
    piso = gabinete.getObjectByName('piso');
    paredes = ['frente', 'atras', 'izq', 'der'].map((n) => gabinete.getObjectByName(`pared_${n}`));
  } catch (e) {
    console.warn('pieza gabinete de control: se usa el modelo simple', e);
    gabinete = null;
    piso = caja(ax, ay, 0.003, 0x2a2f36, Vxyz(bx, by, 0.0015));
    const matPared = mat(0x9aa4b1, { transparent: true, opacity: 0.14, depthWrite: false, side: THREE.DoubleSide });
    paredes = [[0, -ay / 2, ax, 0.003], [0, ay / 2, ax, 0.003], [-ax / 2, 0, 0.003, ay], [ax / 2, 0, 0.003, ay]]
      .map(([dx, dy, sx, sy]) => caja(sx, sy, az, matPared, Vxyz(bx + dx, by + dy, az / 2)));
    grupo.add(piso, ...paredes);
  }
  registrar('esp32_fijo', piso, ...paredes);
  const z0 = 0.003;
  const en = (dx, dy, z = z0) => Vxyz(bx + dx, by + dy, z);

  // Canaletas ranuradas (25 x 30 mm, grises, con la tapa translucida).
  // yF a 100,5 mm del centro: la canaleta de adelante deja 7,2 mm libres a la pared, donde van las
  // contratuercas de los prensaestopas (5 mm reales; antes quedaba pegada a ellas).
  const DUCTOS = { yF: -0.1005, yM: 0.005, xI: -0.1695, xD: 0.1695 };
  const matDucto = mat(0x9ca3ad, { roughness: 0.8 });
  const matTapa = mat(0xc9ced6, { transparent: true, opacity: 0.25, depthWrite: false });
  // `huecos`: [lado, t, ancho] = tramos de pared cortados donde llega otra canaleta (union en T,
  // como se corta en el tablero real): por ahi pasan los hilos de una a la otra.
  const ducto = (dx, dy, largo, alongX, ancho, huecos = []) => {
    const g = new THREE.Group();
    const [sx, sy] = alongX ? [largo, ancho] : [ancho, largo];
    g.add(caja(sx, sy, 0.0015, matDucto, en(dx, dy, z0 + 0.00075)));
    for (const s of [-1, 1]) {
      const cortes = huecos.filter(([l]) => l === s).map(([, t, w]) => [t - w / 2, t + w / 2]).sort((u, v) => u[0] - v[0]);
      let t0 = -largo / 2;
      for (const [c0, c1] of [...cortes, [largo / 2, largo / 2]]) {
        const L = c0 - t0, tc = (t0 + c0) / 2;
        if (L > 1e-4) {
          g.add(alongX ? caja(L, 0.0015, 0.028, matDucto, en(dx + tc, dy + s * ancho / 2, z0 + 0.014))
            : caja(0.0015, L, 0.028, matDucto, en(dx + s * ancho / 2, dy + tc, z0 + 0.014)));
        }
        t0 = c1;
      }
      // Ranuras (los "dedos" de la canaleta).
      const n = Math.floor(largo / 0.008);
      for (let i = 0; i < n; i++) {
        const t = -largo / 2 + (i + 0.5) * (largo / n);
        if (cortes.some(([c0, c1]) => t > c0 - 0.002 && t < c1 + 0.002)) continue;
        // Terminan 0,4 mm antes del borde de la pared: con la cara de arriba en el mismo plano que
        // la de la pared, las dos parpadeaban (2026-09-28).
        const r = alongX ? caja(0.0035, 0.0017, 0.0196, 0x7d848e, en(dx + t, dy + s * ancho / 2, z0 + 0.0178))
          : caja(0.0017, 0.0035, 0.0196, 0x7d848e, en(dx + s * ancho / 2, dy + t, z0 + 0.0178));
        g.add(r);
      }
    }
    g.add(caja(sx, sy, 0.001, matTapa, en(dx, dy, z0 + 0.0285)));
    g.traverse((o) => { o.castShadow = false; });
    grupo.add(g);
    registrar('canaletas_caja', g);
  };
  ducto(0, DUCTOS.yF, 0.339 + 0.02, true, 0.02, [[1, DUCTOS.xI, 0.015], [1, DUCTOS.xD, 0.015]]);
  ducto(0, DUCTOS.yM, 0.339 + 0.02, true, 0.02, [[-1, DUCTOS.xI, 0.015], [-1, DUCTOS.xD, 0.015], [1, 0, 0.015]]);
  ducto(DUCTOS.xI, (DUCTOS.yF + DUCTOS.yM) / 2, DUCTOS.yM - DUCTOS.yF - 0.02, false, 0.015);
  ducto(DUCTOS.xD, (DUCTOS.yF + DUCTOS.yM) / 2, DUCTOS.yM - DUCTOS.yF - 0.02, false, 0.015);
  // Canaleta de la fila de potencia, pegada a la bornera de la fuente.
  ducto(0, (DUCTOS.yM + 0.117) / 2 + 0.005, 0.117 - DUCTOS.yM - 0.01, false, 0.015);
  DUCTOS.segmentos = [[[DUCTOS.xI, DUCTOS.yF], [DUCTOS.xD, DUCTOS.yF]], [[DUCTOS.xD, DUCTOS.yF], [DUCTOS.xD, DUCTOS.yM]],
    [[DUCTOS.xD, DUCTOS.yM], [DUCTOS.xI, DUCTOS.yM]], [[DUCTOS.xI, DUCTOS.yM], [DUCTOS.xI, DUCTOS.yF]],
    [[0, DUCTOS.yM], [0, 0.108]]];

  // Fila de logica (adelante) y de potencia (atras). La placa GVS gira 180
  // grados: el USB del ESP32 queda hacia la pared izquierda.
  // Cada placa es la pieza detallada de piezas/electronica.js (mismo origen y mismos pines que la
  // plantilla de conexiones.py). construirModulo sigue registrando los pines para los cables; los
  // pines, bornes y headers simples que dibujaba la plantilla se quitan (la pieza trae los suyos)
  // y la placa simple queda oculta. Si la pieza falla, queda el modelo simple completo.
  const conPieza = (dev, fabrica, padre, pos, q, opts, zPieza = 0) => {
    const antes = new Map([...LOTES].map(([k, v]) => [k, v.matrices.length]));
    const g = construirModulo(dev, padre, pos, q, opts);
    try {
      const pz = PIEZAS_ELECTRONICA[fabrica]({ id: dev, idComponente: opts.idComponente, sensorId: opts.sensorId });
      pz.position.copy(Vxyz(0, 0, zPieza));
      for (const c of g.children) c.visible = false;
      g.add(pz);
      for (const [k, v] of LOTES) if (v.padre === padre) v.matrices.length = antes.get(k) ?? 0;
      if (opts.idComponente) registrar(opts.idComponente, pz);
      return true;
    } catch (e) {
      console.warn(`pieza ${fabrica} (${dev}): se usa el modelo simple`, e);
      return false;
    }
  };
  // Placa GVS de 38 pines con su ESP32 (crearPlacaGVS38P). Orientacion revisada contra el ESP32
  // real: antena a -x, header de EN en -y; conexiones.py (`_shield`, ESP38_ABAJO en -y) ya usa ese
  // mismo pinout, asi que cada ancla `pin_esp32_fijo_G34.S` cae donde la plantilla (+8 mm de
  // punta) y los cables salen de los pines que se ven.
  // 14 mm mas a la derecha que antes (y el reparto I2C y los optoacopladores 6 mm): la clavija
  // micro-USB (23 mm con su alivio) deja 9 mm a la canaleta lateral para que el cable suba por
  // encima de ella hacia su prensaestopas.
  conPieza('esp32_fijo', 'crearPlacaGVS38P', grupo, en(-0.103, -0.05), yaw(180), { idComponente: 'esp32_fijo' });
  conPieza('hub_i2c', 'crearRepartoI2C', grupo, en(-0.039, -0.078), yaw(0), { idComponente: 'reparto_i2c' });
  conPieza('opto', 'crearPlacaOptoPC817', grupo, en(-0.039, -0.035), yaw(0), { idComponente: 'optoacopladores' });
  conPieza('pca9685', 'crearPCA9685', grupo, en(0.02, -0.075), yaw(0), { idComponente: 'pca9685' });
  conPieza('uln2003', 'crearULN2003', grupo, en(0.005, -0.03), yaw(0), { idComponente: 'uln2003' });
  conPieza('drivers', 'crearPlacaDriversPasoAPaso', grupo, en(0.1, -0.05), yaw(0), { idComponente: 'drivers_cintas' });
  conPieza('fuente', 'crearFuenteLRS150', grupo, en(-0.093, 0.068), yaw(0), { idComponente: 'fuente', etiquetaSobre: 0.045 });
  conPieza('buck6', 'crearBuckXL4016', grupo, en(0.045, 0.045), yaw(0), { idComponente: 'buck_servos' });
  conPieza('fusibles', 'crearPortafusibles4', grupo, en(0.045, 0.093), yaw(0), { idComponente: 'fusibles' });
  conPieza('buck5', 'crearBuckLM2596', grupo, en(0.115, 0.035), yaw(0), { idComponente: 'buck_5v' });
  // Bornera X2 sobre su riel DIN TS35, con los puentes (2-3, 5-6, 7 a 13). La pieza trae el riel:
  // va 7,5 mm mas abajo que la plantilla (que se apoyaba ENCIMA de un riel dibujado aparte).
  const x2Pieza = conPieza('x2', 'crearBorneraDIN16', grupo, en(0.125, 0.092, z0 + 0.0075), yaw(0),
    { idComponente: 'bornera_x2', etiquetaSobre: 0.05 }, -0.0075);
  if (!x2Pieza) {
    grupo.add(caja(0.105, 0.035, 0.0075, 0xc9ccd1, en(0.125, 0.092, z0 + 0.00375), { metalness: 0.8 }));
    const tplX2 = plantilla('x2');
    for (const grupoP of tplX2.puentes) {
      const xs = grupoP.map((n) => tplX2.pines.find((p) => p.n === n).x);
      const a = Math.min(...xs), b = Math.max(...xs);
      grupo.add(caja((b - a) * MM + 0.004, 0.003, 0.004, 0xd23a2a, en(0.125 + (a + b) / 2 * MM, 0.092, z0 + 0.0075 + 0.03)));
    }
  }
  // Entrada de red IEC C14 con interruptor y fusible, en la pared derecha (el frente hacia afuera).
  // Centrada en y = 44 mm (agente de solapes, 2026-09-27): su cuerpo ocupa 48 mm de ancho y 36 mm
  // hacia adentro; en y = 56 mm se metia 9 mm en los bornes 13-16 de la bornera X2. Ahora le
  // deja 3 mm (cuerpo hasta y = 68 mm, bornera desde y = 71 mm).
  try {
    const iec = PIEZAS_ELECTRONICA.crearEntradaIEC({ id: 'iec', idComponente: 'entrada_red' });
    iec.position.copy(en(ax / 2 + 0.0015, 0.044, 0.03));
    iec.quaternion.copy(yaw(90));
    grupo.add(iec);
    registrar('entrada_red', iec);
    iec.updateMatrix();
    ['L', 'N', 'PE'].forEach((n) => pinSuelto(`iec.${n}`, grupo,
      iec.getObjectByName(`pin_iec_${n}`).position.clone().applyMatrix4(iec.matrix),
      new THREE.Vector3(-1, 0, 0), 'pad', new THREE.Vector3(0, 0, -1)));
  } catch (e) {
    console.warn('pieza entrada IEC: se usa el modelo simple', e);
    const iec = caja(0.012, 0.03, 0.026, 0x111111, en(ax / 2 - 0.003, 0.06, 0.03));
    const tecla = caja(0.006, 0.01, 0.012, 0xc8241c, en(ax / 2 + 0.005, 0.06, 0.036));
    grupo.add(iec, tecla);
    registrar('entrada_red', iec, tecla);
    ['L', 'N', 'PE'].forEach((n, i) => pinSuelto(`iec.${n}`, grupo, en(ax / 2 - 0.012, 0.052 + i * 0.008, 0.03),
      new THREE.Vector3(-1, 0, 0), 'pad', new THREE.Vector3(0, 0, -1)));
  }
  // Prensaestopas: los pone el gabinete (adelante G1 PG16 + 5 PG7, USB y luz a la izquierda, red a
  // la derecha). Sin gabinete, los cilindros simples de antes.
  if (!gabinete) {
    const glandes = [];
    for (const [gx, rg] of [[0.2, 0.0055], [0.28, 0.0055], [0.297, 0.0055], [0.3338, 0.011], [0.3725, 0.0055], [0.405, 0.0055]]) {
      const pe = cilindro(rg, 0.012, 0x2b2b2b, Vxyz(gx, by - ay / 2, rg > 0.01 ? 0.016 : 0.014));
      pe.rotation.x = Math.PI / 2;
      glandes.push(pe);
    }
    const peUsb = cilindro(0.005, 0.012, 0x2b2b2b, Vxyz(bx - ax / 2, by - 0.047, 0.052));
    peUsb.rotation.z = Math.PI / 2;
    const peLuz = cilindro(0.005, 0.012, 0x2b2b2b, Vxyz(bx - ax / 2, by - 0.079, 0.052));
    peLuz.rotation.z = Math.PI / 2;
    grupo.add(...glandes, peUsb, peLuz);
  }
  const et = etiqueta('Caja de control', { alto: 0.014, color: '#f2b134' });
  et.position.copy(Vxyz(bx, by + ay / 2 + 0.01, 0.1));
  grupo.add(et);

  P.caja = { bx, by, ax, ay, yPared: by - ay / 2, xParedIzq: bx - ax / 2, xParedDer: bx + ax / 2, DUCTOS };
  escena.add(grupo);

  // Hub USB con fuente propia (el portatil necesita 3 USB) y el portatil. Detras de la caja, a
  // la derecha del portatil: sus puertos miran a la caja con 8 mm libres detras de los enchufes
  // (antes, en (0,26; 0,30), los USB chocaban con la pared de atras), y el USB-B de subida queda
  // delante del costado derecho del portatil sin tocarlo.
  // Posicion del hub desde config/parametros.yaml (puesto_pc): la misma que usa el mapa del carro.
  const hubC = (G.puesto_pc && G.puesto_pc.hub_centro_mm) || [360, 330];
  conPieza('hub_usb', 'crearHubUSB4', escena, Vxyz(hubC[0] / 1000, hubC[1] / 1000, 0), yaw(0), { idComponente: 'hub_usb', etiquetaSobre: 0.02 });
  construirLaptop();
  construirEnlaceAsistente();
}

// Portatil del grupo: ASUS TUF Gaming A15 (ficha oficial de ASUS: 359 x 256 x 24,7 mm,
// 2,3 kg, pantalla de 15,6" 16:9 = 344 x 194 mm de area activa). Se modela a su medida real y
// se dibuja AMPLIADO x1,5 (usuario, 2026-09-27: para leer en el visor lo que responde el
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
  // Centro del portatil desde config/parametros.yaml (puesto_pc): la misma huella que el mapa del
  // carro marca como prohibida (2026-09-28).
  if (G.puesto_pc && G.puesto_pc.laptop_centro_mm) {
    LAPTOP.cx = G.puesto_pc.laptop_centro_mm[0] / 1000;
    LAPTOP.cy = G.puesto_pc.laptop_centro_mm[1] / 1000;
  }
  // Pieza detallada (piezas/control.js: crearLaptopTUFA15, la misma laptop con rejillas traseras,
  // barra de bisagra, lineas del A15 en la tapa y muesca del frente). Si falla, el modelo de abajo.
  let pcPieza = null;
  try {
    const pc = pcPieza = PIEZAS_CONTROL.crearLaptopTUFA15({ apertura: LAPTOP.apertura });
    const d = pc.userData.laptop;
    pc.scale.setScalar(LAPTOP.escala);
    pc.position.copy(Vxyz(LAPTOP.cx, LAPTOP.cy, 0.0015 * LAPTOP.escala));   // apoyada en sus patas
    escena.add(pc);
    pc.updateMatrixWorld(true);
    const meshes = [];
    pc.traverse((m) => { if (m.isMesh) meshes.push(m); });
    registrar('pc', ...meshes);
    // Pines de los USB de la derecha, en coordenadas del mundo (el portatil esta ampliado).
    [1, 2].forEach((i) => pinSuelto(`pc.USB${i}`, escena, pc.getObjectByName(`pin_pc_USB${i}`).getWorldPosition(new THREE.Vector3()),
      new THREE.Vector3(1, 0, 0), 'usb'));
    const etPc = etiqueta('Portátil ASUS TUF Gaming A15 · dibujado ×1,5 para leer la pantalla', { alto: 0.012, alcance: 1.2 });
    // Detras de la planta: con depthTest la planta la tapa; sin el, el rotulo se veia encima de
    // las tomas de la cinta y del material (2026-09-28).
    etPc.material.depthTest = true;
    escena.add(etPc);
    const puntaTapa = d.camara.getWorldPosition(new THREE.Vector3());
    etPc.position.copy(puntaTapa).add(new THREE.Vector3(-0.22, 0.05, 0));
    P.laptop = { grupo: pc, pantalla: d.pantalla, lienzo: d.lienzo, textura: d.textura, matLetras: d.matLetras, leds: d.leds, puntaTapa };
    return;
  } catch (e) {
    console.warn('pieza laptop TUF A15: se usa el modelo simple', e);
    if (pcPieza) escena.remove(pcPieza);
  }
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
  // Detras de la planta: con depthTest la planta la tapa; sin el, el rotulo se veia encima de
  // las tomas de la cinta y del material (2026-09-28).
  etPc.material.depthTest = true;
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
  // Nube de dibujo: lobulos redondos arriba y una base ancha y plana (un elipsoide aplastado),
  // como el icono de "la nube"; la base tapa las uniones de los lobulos por debajo.
  for (const [dx, dy, dz, r, sy = 1] of [[0, 0.004, 0, 0.055], [-0.062, -0.012, 0.006, 0.042], [0.062, -0.012, -0.006, 0.042],
    [-0.03, 0.03, -0.01, 0.04], [0.03, 0.03, 0.01, 0.04], [0, -0.02, 0.03, 0.035], [0, -0.02, -0.03, 0.035],
    [-0.095, -0.03, 0, 0.03], [0.095, -0.03, 0, 0.03], [0, -0.036, 0, 0.06, 0.38]]) {
    const b = new THREE.Mesh(new THREE.SphereGeometry(r, 24, 16), matNube);
    b.scale.set(sy === 1 ? 1 : 2.1, sy, sy === 1 ? 1 : 0.95);
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
  // Detras de la planta: con depthTest la planta la tapa; sin el, el rotulo se veia encima de
  // las tomas de la cinta y del material (2026-09-28).
  et.material.depthTest = true;
  et.position.copy(centro).add(new THREE.Vector3(0, 0.085, 0));
  grupo.add(et);
  // La misma etiqueta sin internet, en el mismo lugar: se muestra una u otra, nunca las dos.
  const etSinRed = etiqueta('☁ API de DeepSeek · sin internet', { alto: 0.014, alcance: 1.8, borde: '#e5534b', color: '#ffb4ae' });
  // Detras de la planta: con depthTest la planta la tapa; sin el, el rotulo se veia encima de
  // las tomas de la cinta y del material (2026-09-28).
  etSinRed.material.depthTest = true;
  etSinRed.position.copy(et.position);
  etSinRed.userData.oculta = true;
  grupo.add(etSinRed);
  const etW = etiqueta('Wi-Fi del portátil (el carro usa ESP-NOW)', { alto: 0.009, alcance: 1.0, color: '#8b949e' });
  // Detras de la planta: con depthTest la planta la tapa; sin el, el rotulo se veia encima de
  // las tomas de la cinta y del material (2026-09-28).
  etW.material.depthTest = true;
  etW.position.copy(a.clone().lerp(b, 0.5)).add(new THREE.Vector3(0.1, 0, 0));
  grupo.add(etW);
  escena.add(grupo);
  P.asistente = { grupo, paquete, a, b, matNube, linea, et, etSinRed, mensajes: -1, panel: L.pantalla, lienzo: L.lienzo,
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

// La respuesta del asistente viene en markdown (el dashboard lo dibuja); en el canvas de la laptop
// se veian los simbolos sueltos (`qwen2.5-proyecto`, **negrita**): se quitan y queda el texto.
function sinMarkdown(t) {
  return String(t ?? '')
    .replace(/```[a-z]*\n?/gi, '')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,;:!?]|$)/g, '$1$2')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^\s{0,3}#{1,6}\s+/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '• ')
    .replace(/`/g, '');
}

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
    if (pregunta) bloquePregunta(sinMarkdown(pregunta.texto));
    // Respuesta: la letra mas grande (de 64 a 30 px) con la que cabe entera.
    const alto = H - y - 120;
    const textoResp = sinMarkdown(respuesta.texto);
    let tam = 64, lineas;
    for (; tam >= 30; tam -= 2) {
      ctx.font = `500 ${tam}px "Space Grotesk", sans-serif`;
      lineas = envolver(ctx, textoResp, W - 2 * m);
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
// `aDentro`: el punto `a` ya esta dentro de una canaleta (un cable que entra por un prensaestopas
// y sigue derecho por una ranura): no sube por encima de la pared de la canaleta.
function rutaCaja(a, b, k = 0, { aDentro = false } = {}) {
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
  const inicio = aDentro ? [W(pa, pa[2])] : [W(pa, alto(pa[2])), W(corrido[0], alto(pa[2]))];
  return [...inicio, ...corrido.map((p) => W(p, zD)),
    W(corrido[corrido.length - 1], alto(pb[2])), W(pb, alto(pb[2]))];
}

// ---------------------------------------------------------------------------
// cableado: cada hilo de sim/conexiones.py, de su pin al otro
// ---------------------------------------------------------------------------

// Pines REALES de las piezas detalladas (piezas/*.js): cada pieza trae un ancla
// `pin_<dispositivo>_<PIN>` en la punta de su pin (o la boca de su borne), con
// `userData.dir` = hacia donde sale el cable. Donde exista, esa ancla manda sobre
// la posicion de plantilla que registro construirModulo / pinSuelto: el hilo sale
// del pin que se ve, no de donde decia la plantilla. Se busca en toda la escena
// (tambien dentro del carro, que se mueve: la punta queda en el marco de su padre).
// Devuelve cuantos pines se movieron y cuanto (para revisar con ?auditar).
const PINES_REALES = {};
function pinesDePiezas() {
  escena.updateMatrixWorld(true);
  const devs = Object.keys(G.conexiones.dispositivos).sort((a, b) => b.length - a.length);
  const anclas = {};
  escena.traverse((o) => {
    if (!o.name || !o.name.startsWith('pin_') || o.isMesh) return;
    // Solo las de piezas visibles (la plantilla oculta no cuenta).
    for (let p = o.parent; p; p = p.parent) if (p.visible === false) return;
    const dev = devs.find((d) => o.name.startsWith(`pin_${d}_`));
    if (dev) anclas[`${dev}.${o.name.slice(dev.length + 5)}`] ||= o;
  });
  const inv = new THREE.Matrix4(), q = new THREE.Quaternion();
  for (const [ref, o] of Object.entries(anclas)) {
    const Pn = PIN[ref];
    if (!Pn) continue;
    const padre = Pn.padre;
    padre.updateMatrixWorld(true);
    inv.copy(padre.matrixWorld).invert();
    const tip = o.getWorldPosition(new THREE.Vector3()).applyMatrix4(inv);
    let dir = Pn.dir;
    const d = o.userData.dir;
    if (d && d.isVector3) {
      o.getWorldQuaternion(q);
      dir = d.clone().applyQuaternion(q).applyQuaternion(padre.getWorldQuaternion(new THREE.Quaternion()).invert()).normalize();
    }
    PINES_REALES[ref] = +(tip.distanceTo(Pn.tip) / MM).toFixed(1);   // mm que se movio
    Pn.tip = tip;
    Pn.dir = dir;
  }
  return PINES_REALES;
}

function construirCables() {
  const grupo = new THREE.Group();
  CAPAS_CABLES.push(grupo);
  escena.updateMatrixWorld(true);   // para los localToWorld de abajo
  const cx = G.conexiones;
  const C = P.caja;
  const S = (v) => [v.x, -v.z, v.y];                       // Three -> simulacion

  // Pines que no son placas: donde sale el cable de cada cosa. Los registran sus zonas (servos,
  // sensores de la planta y motores con sus anclas); aqui solo se ponen los que falten, con una
  // posicion de respaldo.
  const siFalta = (ref, ...args) => { if (!PIN[ref]) pinSuelto(ref, escena, ...args); };
  const servos = { servo_desvio: 'servo_desvio_e7', servo_obturador: 'servo_obturador', servo_tapas: 'servo_tapas',
    servo_prensa: 'motor_prensa', servo_empujador: 'servo_empujador', servo_canaleta: 'servo_compuerta_canaleta' };
  for (const [dev, comp] of Object.entries(servos)) siFalta(`${dev}.CABLE`, P.rutasServo[comp][0]);
  for (const id of ['capacitivo', 'inductivo']) {
    for (const c of ['CAFE', 'AZUL', 'NEGRO']) siFalta(`${id}.${c}`, SENS[id].rutaCable[0], new THREE.Vector3(0, -1, 0));
  }
  siFalta('cam_cenital.USB', SENS.camara.rutaCable[0]);
  siFalta('cam_vasos.USB', SENS.camara_vasos.rutaCable[0]);
  const conectorNema = (m) => (m && m.userData.conector ? m.localToWorld(m.userData.conector.clone()) : null);
  siFalta('motor_monedas.JST', conectorNema(P.nemaMonedas) || Vxyz(-0.1356, 0.133, 0.441), new THREE.Vector3(-1, 0, 0), 'jst');
  siFalta('motor_vasos.JST', conectorNema(P.nemaVasos) || Vxyz(-0.0256, -0.2145, 0.111), new THREE.Vector3(-1, 0, 0), 'jst');
  const [cxa, cya] = G.almacen.centro;
  siFalta('motor_carrusel.CABLE', Vxyz(cxa + 0.007, cya, G.almacen.tubo_z_arriba + 0.03), new THREE.Vector3(-1, 0, 0));
  const zp = G.cinta_vasos.estaciones[0].posicion[2] + 0.02;
  siFalta('panel_luz.+5V', Vxyz(0.295, -0.051, zp + 0.004), new THREE.Vector3(0, 0, -1), 'pad');
  siFalta('panel_luz.GND', Vxyz(0.295, -0.051, zp - 0.004), new THREE.Vector3(0, 0, -1), 'pad');
  const anillo = SENS.camara.rutaCable[0].clone().add(new THREE.Vector3(-0.012, -0.026, 0));
  siFalta('anillo.+5V', anillo.clone().add(new THREE.Vector3(0, 0, 0.002)), new THREE.Vector3(-1, 0, 0), 'pad');
  siFalta('anillo.GND', anillo.clone().add(new THREE.Vector3(0, 0, -0.002)), new THREE.Vector3(-1, 0, 0), 'pad');

  // Ventilador de la caja: sus dos hilos salen por el agujero de 4 mm junto al marco (anclas de
  // piezas/control.js), hacia adentro de la caja (+y local del ventilador).
  for (const n of ['+5V', 'GND']) {
    const o = escena.getObjectByName(`pin_ventilador_${n}`);
    const q = new THREE.Quaternion();
    const pos = o ? o.getWorldPosition(new THREE.Vector3())
      : Vxyz(C.xParedDer - 0.0035, C.by - 0.05 + (n === 'GND' ? 0.0016 : 0), 0.038);
    const dir = o ? new THREE.Vector3(0, 0, -1).applyQuaternion(o.parent.getWorldQuaternion(q)) : new THREE.Vector3(-1, 0, 0);
    pinSuelto(`ventilador.${n}`, escena, pos, dir, 'cable', new THREE.Vector3(0, 0, -1));
  }
  // Donde la pieza detallada trae el pin real, el hilo sale de ahi.
  pinesDePiezas();
  // Cuantos hilos llegan a cada pin (para abrirlos en los conectores).
  for (const c of cx.cables) for (const h of c.hilos) for (const e of [h.de, h.a]) if (PIN[e]) PIN[e].total = (PIN[e].total || 0) + 1;

  // --- Recorridos de los cables de campo (coordenadas de la simulacion, m) ---
  // Reglas: cada cable sale de su pin, va por perfiles y por el piso (apoyado, no flotando),
  // entra a la caja DERECHO por el eje de su prensaestopas (boca, rosca, contratuerca) y sigue por
  // una ranura hasta dentro de la canaleta; los cables del mismo tramo van lado a lado sin
  // cruzarse; los USB y la red terminan en su clavija.
  const enMundo = (nombre) => { const o = escena.getObjectByName(nombre); return o ? o.getWorldPosition(new THREE.Vector3()) : null; };
  const zPiso = (tipo) => TIPOS_CABLE[tipo].r + 0.0004;          // apoyado en el piso
  // Prensaestopas del gabinete (piezas/control.js): 0-5 adelante, 6 USB y 7 luz a la izquierda.
  const FRENTE_X = [0.2, 0.28, 0.297, 0.3338, 0.3725, 0.405];   // desvio, cinta de vasos, cortina, G1, canaleta, empujador
  const glandula = (i) => {
    const a = enMundo(`ancla_prensa_${i}`), d = enMundo(`ancla_prensa_${i}_adentro`);
    if (a && d) return { afuera: S(a), adentro: S(d) };
    if (i < 6) {
      const z = i === 3 ? 0.016 : 0.014;
      return { afuera: [FRENTE_X[i], C.yPared - 0.02, z], adentro: [FRENTE_X[i], C.yPared + 0.0075, z] };
    }
    const y = C.by + (i === 6 ? -0.047 : -0.079);
    return { afuera: [C.xParedIzq - 0.02, y, 0.052], adentro: [C.xParedIzq + 0.0075, y, 0.052] };
  };
  // Adentro de la canaleta de adelante, 4 mm despues de su pared (el cable pasa por una ranura).
  const yDentroF = C.by + C.DUCTOS.yF - 0.004;
  // Tramo final por un prensaestopas de adelante: 12 mm derecho frente a la boca, la boca, la
  // rosca y la contratuerca, y la ranura de la canaleta. El punto anterior del recorrido tiene que
  // quedar frente a la boca (x del prensaestopas, 25 mm o mas afuera).
  const entrarFrente = (i, ox = 0, oz = 0) => {
    const { afuera: a, adentro: d } = glandula(i);
    const x = a[0] + ox, z = a[2] + oz;
    return [[x, a[1] - 0.01, z], [x, a[1], z], [x, d[1], z], [x, yDentroF, z]];
  };
  const antesDe = (i, zp, ox = 0) => [glandula(i).afuera[0] + ox, glandula(i).afuera[1] - 0.022, zp];

  // Mazo del portico (atado con amarras a la viga y a la columna derecha) hasta el PG16 (G1).
  // - Lado -y de la viga (x < 0,19): alli llegan los sensores y motores de la cinta de monedas y
  //   del almacen. `c` = capa desde la cara del perfil, `r` = fila a lo alto.
  // - Entre x = 0,170 y 0,188 cada cable pasa POR ENCIMA de la viga al lado +y (en el -y, mas a la
  //   derecha, estan el colgador del tubo de tapas y la placa de la prensa).
  // - Lado +y de la viga hasta la columna derecha y abajo por su cara +y (en la +x esta el
  //   empujador), hasta ~6 cm del piso, y derecho al PG16.
  // Sin cruces: el que sube desde abajo a una fila tiene libres las de abajo de su capa (los de
  // filas mas bajas se suman mas a la derecha); al pasar por arriba cruza primero la fila de arriba
  // y del otro lado queda abajo; en la columna cada fila baja por su propia bajada `i` (x). Los que
  // se suman en la columna (servos de la prensa y del obturador, panel de luz) y el de las tapas
  // van en la capa de afuera (c = 4).
  const V0 = P.portico.y;                                           // centro de la viga (y)
  const yM = (c) => V0 - 0.01 - 0.0025 - c * 0.0042;                // capas del lado -y
  const yL = (c) => V0 + 0.01 + 0.0025 + c * 0.0042;                // capas del lado +y
  const zR = (r) => P.portico.z - 0.0065 + r * 0.0038;             // filas sobre la cara de la viga
  const zArriba = (c) => P.portico.z + 0.01 + 0.0025 + c * 0.0042; // capas por encima de la viga
  const xCol = 0.315;                                               // columna derecha (centro)
  const xB = (i) => xCol - 0.0075 + i * 0.0038;                     // bajadas por la cara +y
  const zBajo = G.cinta_vasos.estaciones[0].posicion[2] - 0.062;    // fin de la bajada (~6 cm)
  // [c, fila del lado -y, x donde pasa por arriba]; del lado +y la fila se invierte.
  const MAZO = {
    motor_monedas: [0, 1, 0.170], capacitivo: [1, 1, 0.173], presencia: [2, 1, 0.176],
    inductivo: [0, 0, 0.179], vl53_interior: [1, 0, 0.182], motor_carrusel: [2, 0, 0.185], hall: [3, 0, 0.188],
  };
  // Capa 4 (afuera), cada uno con su bajada: [c, i].
  const AFUERA = { panel_luz: [4, 0], servo_1: [4, 1], servo_3: [4, 2], servo_2: [4, 3] };
  // Bajada por la columna (capa c, bajada i) hasta G1: la bajada i entra a la izquierda o a la
  // derecha del prensaestopas y la capa, abajo o arriba (el haz entra ordenado).
  const bajarColumna = (c, i, zDesde) => [[xB(i), yL(c), zDesde], [xB(i), yL(c), zBajo],
    ...entrarFrente(3, (i - 1.5) * 0.0034, (c - 2) * 0.003)];
  // De su lugar en el lado -y (x donde ya esta en su fila) hasta G1.
  const porViga = (id, x) => {
    const [c, r, xw] = MAZO[id];
    const r2 = 1 - r;                                               // fila del lado +y
    return [[x, yM(c), zR(r)], [xw, yM(c), zR(r)], [xw, yM(c), zArriba(c)], [xw, yL(c), zArriba(c)], [xw, yL(c), zR(r2)],
      ...bajarColumna(c, r2, zR(r2))];
  };
  // Subir a su lugar desde abajo de la viga: primero a lo ancho (a su altura, por debajo de la viga
  // y de los sensores de la cinta de monedas) hasta su capa, y despues derecho arriba.
  const subir = (id, x, yDesde, zDesde) => [[x, yDesde, zDesde], [x, yM(MAZO[id][0]), zDesde], ...porViga(id, x)];
  // Sumarse en la columna, viniendo desde el lado -y a su altura z: por el costado -x de la columna.
  const sumarse = (id, z, y0 = -0.047) => {
    const [c, i] = AFUERA[id];
    return [[xCol - 0.015, y0, z], [xCol - 0.015, yL(c), z], [xB(i), yL(c), z], ...bajarColumna(c, i, z).slice(1)];
  };
  const nm = S(PIN['motor_monedas.JST'].tip);
  const mc = S(PIN['motor_carrusel.CABLE'].tip);
  const RUTAS = {
    // Motor de la cinta de monedas: del conector (cara -x) baja junto al motor, pasa por debajo
    // de la cinta y sube a la viga junto a la columna izquierda.
    motor_monedas: () => [nm, [nm[0] - 0.008, nm[1], nm[2]], [nm[0] - 0.008, nm[1], 0.412], [-0.09, nm[1], 0.412],
      [-0.09, nm[1], 0.37], [-0.09, 0.02, 0.365], [-0.06, 0.02, 0.365], ...subir('motor_monedas', -0.06, 0.02, 0.365).slice(1)],
    // M18: su cable integrado termina abajo (anclas pin_<id>_AZUL, a ~350 mm); de ahi sale DE LADO
    // 5 mm mas abajo, ~10 mm por encima del retorno de la banda (cara de arriba a ~333 mm), y sube.
    capacitivo: () => { const p0 = S(PIN['capacitivo.AZUL'].tip); return [p0, ...subir('capacitivo', p0[0], p0[1], p0[2] - 0.005)]; },
    inductivo: () => { const p0 = S(PIN['inductivo.AZUL'].tip); return [p0, ...subir('inductivo', p0[0], p0[1], p0[2] - 0.005)]; },
    // Presencia: llega por encima de la columna izquierda (su brazo) y baja a la fila de arriba de su capa.
    presencia: () => {
      const r = SENS.presencia.rutaCable.map(S);
      const u = r[r.length - 1];
      return [...r, [u[0], yM(MAZO.presencia[0]), u[2]], ...porViga('presencia', u[0])];
    },
    hall: () => { const r = SENS.hall_carrusel.rutaCable.map(S); return [r[0], r[1], ...subir('hall', r[1][0], r[1][1], r[1][2])]; },
    vl53_interior: () => { const r = SENS.sensor_interior.rutaCable.map(S); return [r[0], r[1], ...subir('vl53_interior', r[1][0], r[1][1], r[1][2])]; },
    motor_carrusel: () => [mc, ...subir('motor_carrusel', mc[0] - 0.006, mc[1], mc[2])],
    // Tapas: sale del servo hacia -x, sube por encima de la boca del tubo de tapas hasta el colgador
    // del tubo (P.rutasServo), sube pegado a su costado +x hasta 6 mm bajo la viga, pasa a la cara
    // +y y sube a la capa de afuera.
    servo_2: () => {
      const r = P.rutasServo.servo_tapas.map(S);
      const [s0, u] = [r[0], r[r.length - 1]];
      const x = u[0] + 0.0085, zv = P.portico.z - 0.016, zt = s0[2] + 0.046;
      const [c, i] = AFUERA.servo_2;
      return [s0, [s0[0] - 0.006, s0[1], s0[2]], [s0[0] - 0.006, s0[1], zt], [x, u[1] - 0.003, zt], [x, u[1] - 0.003, zv],
        [x, yL(c), zv], [x, yL(c), zR(0)], ...bajarColumna(c, i, zR(0))];
    },
    // Obturador: el conector de su coleta queda parado junto al servo, a la altura de la placa; la
    // funda sube 6 mm, va hacia +x por FUERA del borde de la placa (a 79 mm o mas de su centro:
    // ni placa ni tubos), baja fuera del paso de los vasos (14 mm mas alla del reborde) y sigue
    // bajo el almacen, por delante del tubo de tapas y de la prensa.
    servo_1: () => {
      const r = P.rutasServo.servo_obturador.map(S);
      const z = G.cinta_vasos.estaciones[0].posicion[2] + G.vaso.altura + 0.0335;
      return [r[0], r[1], [0.1445, r[1][1], r[1][2]], [0.1445, r[1][1], z], [0.1445, -0.07, z], [0.1445, -0.048, z],
        ...sumarse('servo_1', z)];
    },
    // Prensa: del servo hacia -x 6 mm, a +y (fuera de la placa de la prensa) y a la columna.
    servo_3: () => {
      const s0 = S(PIN['servo_prensa.CABLE'].tip);
      return [s0, [s0[0] - 0.006, s0[1], s0[2]], [s0[0] - 0.006, -0.043, s0[2]], ...sumarse('servo_3', s0[2], -0.043)];
    },
    panel_luz: () => {
      const zp = PIN['panel_luz.+5V'].tip.y - 0.004;
      return [[0.295, -0.047, zp], [xCol - 0.015, -0.047, zp], ...sumarse('panel_luz', zp).slice(1)];
    },
    // Desvio: baja junto a la descarga hasta el piso y entra por el prensaestopas 0.
    servo_0: () => {
      const r = P.rutasServo.servo_desvio_e7.map(S);
      const zp = zPiso('servo');
      return [r[0], r[1], [r[1][0], r[1][1], 0.03], [r[1][0], -0.024, zp], [antesDe(0, zp)[0], -0.024, zp], antesDe(0, zp), ...entrarFrente(0)];
    },
    // Empujador: el conector del servo mira a +x; baja por fuera del empujador hasta el piso y va
    // por el piso al prensaestopas 5 (a la derecha del de la canaleta, sin cruzarlo).
    servo_4: () => {
      const r = P.rutasServo.servo_empujador.map(S);
      const zp = zPiso('servo');
      const x = r[0][0] + 0.008;
      return [r[0], [x, r[0][1], r[0][2]], [x, r[0][1], 0.02], [x, r[0][1], zp], [antesDe(5, zp)[0], r[0][1], zp], antesDe(5, zp),
        ...entrarFrente(5)];
    },
    // Escape de la canaleta: de la coleta baja bajo el servo, sigue la barra del soporte hasta el
    // poste 2020 del escape (P.rutasServo: 12,5 mm al lado de su eje, pegado a su cara) y BAJA
    // por el poste; a 2 cm del piso se aparta 12 mm (el pie nivelador mide Ø26), va por el piso
    // por fuera de la mesa de vasos y entra por el prensaestopas 4.
    servo_5: () => {
      const r = P.rutasServo.servo_compuerta_canaleta.map(S);
      const zp = zPiso('servo');
      const [xp, yp] = r[3];
      const yS = yp + Math.sign(-0.05 - yp || 1) * 0.012;
      return [r[0], r[1], r[2], r[3], [xp, yp, 0.02], [xp, yS, zp], [xp, -0.05, zp], [antesDe(4, zp)[0], -0.05, zp],
        antesDe(4, zp), ...entrarFrente(4)];
    },
    // Motor de la cinta de vasos: baja junto al motor, esquiva el pie izquierdo del portico por
    // +x y va por el piso (a 2,8 cm del frente de la caja, sin cruzar ningun otro) hasta G2.
    motor_vasos: () => {
      const v = S(PIN['motor_vasos.JST'].tip);
      const zp = zPiso('paso');
      return [v, [v[0] - 0.008, v[1], v[2]], [v[0] - 0.008, v[1], 0.03], [0.009 - 0.027, v[1], zp], [-0.018, -0.028, zp],
        [antesDe(1, zp)[0], -0.028, zp], antesDe(1, zp), ...entrarFrente(1)];
    },
    vl53_cortina: () => {
      const r = SENS.cortina.rutaCable.map(S);
      const u = r[r.length - 1];
      const zp = zPiso('i2c');
      return [...r, [u[0], u[1] - 0.004, zp], [antesDe(2, zp)[0], u[1] - 0.004, zp], antesDe(2, zp), ...entrarFrente(2)];
    },
    // Anillo de luz: de sus pads sube 5 mm, va al poste de la camara y baja pegado a el (junto al
    // USB de la camara), pasa a la cara +y de la pata de la mesa, baja por ella y va por el piso al
    // prensaestopas de la izquierda (7), a 52 mm de alto (por encima de la canaleta lateral).
    anillo: () => {
      const p1 = S(PIN['anillo.+5V'].tip), p2 = S(PIN['anillo.GND'].tip);
      const m = [(p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, Math.max(p1[2], p2[2]) + 0.005];
      const pie = SENS.camara.rutaCable.map(S).slice(-1)[0];          // pie del poste, sobre el riel
      const { afuera: a, adentro: d } = glandula(7);
      const zp = zPiso('cinco');
      const x = PATA.x1 - 0.004, y = PATA.y1 + 0.0016;
      return [m, [m[0], PATA.y1 - 0.006, m[2]], [pie[0] - 0.0002, PATA.y1 - 0.006, m[2]], [pie[0] - 0.0002, pie[1] - 0.006, m[2] - 0.006], [pie[0] - 0.0002, pie[1] - 0.006, pie[2] - 0.015],
        [x, y, pie[2] - 0.03], [x, y, 0.025], [x, a[1], zp], [a[0] - 0.03, a[1], zp], [a[0] - 0.012, a[1], a[2]], a, d, [d[0] + 0.004, d[1], d[2]]];
    },
  };

  // --- USB y red: por la mesa, cada uno en su carril; terminan en su clavija (USB-A, micro-USB,
  // USB-B, C13), que se dibuja en la boca del conector.
  const CLAVIJAS = { A: [16, 8, 22], micro: [11, 6.5, 17], B: [16, 12, 21], C13: [26, 20, 36] };
  const clavija = (boca, dir, tipo) => {
    const [an, al, lg] = CLAVIJAS[tipo];
    const d = dir.clone().normalize();
    const m = mat(0x15171a, { roughness: 0.6 });
    const cuerpo = new THREE.Mesh(new THREE.BoxGeometry(an * MM, al * MM, lg * MM), m);
    cuerpo.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), d);
    cuerpo.position.copy(boca).addScaledVector(d, lg * MM / 2);
    const alivio = new THREE.Mesh(new THREE.CylinderGeometry(al * 0.24 * MM, al * 0.3 * MM, 7 * MM, 12), m);
    alivio.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d);
    alivio.position.copy(boca).addScaledVector(d, (lg + 3.5) * MM);
    cuerpo.userData.clavija = alivio.userData.clavija = tipo;
    grupo.add(cuerpo, alivio);
    return S(boca.clone().addScaledVector(d, (lg + 6) * MM));
  };
  const enchufe = (ref, tipo) => clavija(PIN[ref].tip, PIN[ref].dir, tipo);
  // Carriles detras de la caja, entre su pared de atras y los enchufes del hub (el cable del puerto
  // mas lejano va en el carril mas cercano a la caja: ninguno cruza a otro al doblar hacia su puerto).
  const zU = zPiso('usb');
  // Pata de la mesa de monedas bajo el pie del poste de la camara cenital (perfil 2020): los cables
  // de la camara y del anillo bajan pegados a su cara +y.
  const PATA = (() => {
    const pie = SENS.camara.rutaCable.map(S).slice(-1)[0];
    let mejor = null;
    const b = new THREE.Box3();
    escena.traverse((o) => {
      if (o.name !== 'perfil_2020' || !o.isMesh) return;
      b.setFromObject(o);
      const [x0, x1, y0, y1, z1] = [b.min.x, b.max.x, -b.max.z, -b.min.z, b.max.y];
      if (x1 - x0 > 0.025 || y1 - y0 > 0.025 || z1 < 0.3) return;               // solo perfiles verticales
      const d = Math.hypot((x0 + x1) / 2 - pie[0], (y0 + y1) / 2 - pie[1]);
      if (d < 0.05 && (!mejor || d < mejor.d)) mejor = { d, x0, x1, y0, y1 };
    });
    return mejor || { x0: 0.02, x1: 0.04, y0: 0.03, y1: 0.051 };
  })();
  const yAtras = C.by + C.ay / 2 + 0.0015;                          // cara de afuera de la pared de atras
  const carril = { P3: yAtras + 0.0075, P2: yAtras + 0.0125, P1: yAtras + 0.0175 };
  const alPuerto = (puerto, desdeX) => {
    const e = enchufe(`hub_usb.${puerto}`, 'A');
    return [[desdeX, carril[puerto], zU], [e[0], carril[puerto], zU], [e[0], e[1] - 0.006, e[2]], e];
  };
  Object.assign(RUTAS, {
    // Webcam de vasos: por el piso por la izquierda de las mesas (extension USB de 1 m).
    usb_vasos: () => {
      // Sale de la webcam hacia +x, baja por la cara +x de su poste (antes iba por dentro de el),
      // rodea su base por -y y va por el piso por la izquierda de las mesas.
      const c0 = S(PIN['cam_vasos.USB'].tip);
      const poste = escena.getObjectByName('camara_vasos')?.getObjectByName('poste_camara');
      const b = poste ? new THREE.Box3().setFromObject(poste) : null;
      const [px, py0, py1] = b ? [b.max.x, -b.max.z, -b.min.z] : [0.175, -0.445, -0.407];
      const xp = px + 0.0026, yp = (py0 + py1) / 2, yS = py0 - 0.006;
      return [c0, [c0[0] + 0.008, c0[1], c0[2]], [c0[0] + 0.008, c0[1], c0[2] - 0.02], [xp, yp, c0[2] - 0.04], [xp, yp, 0.02],
        [xp, yS, zU], [-0.168, yS, zU], ...alPuerto('P1', -0.168)];
    },
    // Webcam cenital: baja por el poste hasta su pie (rutaCable), pasa a la cara +y de la pata de la
    // mesa de monedas, baja por ella y va por el piso a su carril.
    usb_cenital: () => {
      const r = SENS.camara.rutaCable.map(S);
      const u = r[r.length - 1];
      const x = PATA.x0 + 0.006, y = PATA.y1 + 0.0026;
      return [...r, [u[0], u[1], u[2] - 0.015], [x, y, u[2] - 0.03], [x, y, 0.025], [x, y + 0.009, zU], ...alPuerto('P2', x)];
    },
    // ESP32: micro-USB, sube por encima de la canaleta lateral, sale por el prensaestopas 6 y va
    // por el piso junto a la pared izquierda hasta su carril.
    usb_esp: () => {
      const e = enchufe('esp32_fijo.USB', 'micro');
      const { afuera: a, adentro: d } = glandula(6);
      // Afuera baja entre la bandeja de rechazo de monedas (en el piso) y la pared de la caja.
      const xFuera = C.xParedIzq - 0.016;
      return [e, [e[0] - 0.004, e[1], e[2]], [e[0] - 0.004, e[1], 0.04], [d[0] + 0.012, d[1], a[2]], [d[0] + 0.004, d[1], a[2]], d, a,
        [a[0] - 0.006, a[1], a[2]], [a[0] - 0.006, a[1] + 0.012, 0.04], [xFuera, a[1] + 0.02, zU], ...alPuerto('P3', xFuera)];
    },
    // Hub -> portatil: sale del USB-B de subida hacia -x, va por el piso junto al portatil (sin
    // tocar su clavija) y entra al USB1 desde afuera.
    usb_pc: () => {
      const h = enchufe('hub_usb.UP', 'B');
      const p = enchufe('pc.USB1', 'A');
      const xl = h[0] - 0.0045;
      const xa = p[0] + 0.016;
      return [h, [xl, h[1], h[2]], [xl, h[1] + 0.012, zU], [xl, p[1] - 0.035, zU], [xa, p[1] - 0.02, zU], [xa, p[1], p[2]], p];
    },
    // Red: el cable de poder con su conector C13 enchufado en la entrada IEC (pared derecha).
    red: () => {
      const iec = escena.getObjectByName('entrada_iec');
      const zr = zPiso('red');
      let e;
      if (iec) {
        const q = iec.getWorldQuaternion(new THREE.Quaternion());
        e = clavija(iec.localToWorld(new THREE.Vector3(-9 * MM, 2.5 * MM, 3.2 * MM)), new THREE.Vector3(0, 0, 1).applyQuaternion(q), 'C13');
      } else e = [C.xParedDer + 0.04, C.by + 0.056, 0.03];
      return [e, [e[0] + 0.012, e[1], e[2]], [e[0] + 0.03, e[1], zr], [0.75, e[1], zr]];
    },
  });

  const zonaDe = (ref) => cx.dispositivos[ref.split('.', 1)[0]].zona;
  // Punta de un pin + 6 mm hacia donde sale el cable. Si el pin no esta registrado (una pieza que
  // cambio de nombre, un dispositivo nuevo de conexiones.py todavia sin modelo) se avisa y ese hilo
  // no se dibuja: el visor sigue arrancando.
  const lead = (ref) => {
    if (!PIN[ref]) { console.warn('cable: pin sin registrar', ref); return null; }
    return PIN[ref].tip.clone().addScaledVector(PIN[ref].dir, 0.006);
  };
  let k = 0;
  for (const c of cx.cables) {
    if (c.tipo === 'carro') continue;
    const nombreTipo = c.tipo;
    if (c.tipo === 'interno' || c.tipo === 'dupont') {
      // Dentro de la caja: cada hilo de su pin al otro por las canaletas.
      for (const h of c.hilos) {
        if (!lead(h.de) || !lead(h.a)) continue;
        hilo(h.de, h.a, h.color, rutaCaja(lead(h.de), lead(h.a), k++), grupo,
          { r: c.tipo === 'interno' ? 0.0008 : 0.00055, nombre: `${c.nombre}: ${h.funcion}`, tipo: nombreTipo });
      }
      continue;
    }
    let pts = null;
    try { pts = RUTAS[c.id] ? RUTAS[c.id]() : null; } catch (e) { console.warn('cable sin recorrido', c.id, e); }
    if (!pts) { console.warn('cable sin recorrido', c.id); continue; }
    if (c.tipo === 'usb' || c.tipo === 'red') {
      funda(c.nombre, c.tipo, pts, grupo, 'mesa');
      continue;
    }
    // Funda por la estructura; en cada punta, los hilos a sus pines. Los que entran por un
    // prensaestopas de adelante terminan ya dentro de la canaleta: sus hilos siguen por ella.
    funda(c.nombre, c.tipo, pts, grupo);
    const inicio = aThree(pts[0]), fin = aThree(pts[pts.length - 1]);
    const enDucto = Math.abs(pts[pts.length - 1][1] - yDentroF) < 1e-6;
    for (const h of c.hilos) {
      const [dev, caja_] = zonaDe(h.de) === 'planta' ? [h.de, h.a] : [h.a, h.de];
      const Pd = PIN[dev];
      if (Pd && !['cable', 'jst'].includes(Pd.tipo)) {
        // Del pin del sensor al comienzo de la funda (con su carcasa).
        hilo(dev, inicio, h.color, [], grupo);
      }
      if (lead(caja_)) hilo(fin, caja_, h.color, rutaCaja(fin, lead(caja_), k++, { aDentro: enDucto }), grupo);
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
  // La leyenda y el boton los maneja la interfaz (interfaz.js).
  for (const g of CAPAS_CABLES) g.visible = si;
}

// Cableado del carro: cada hilo de su pin al otro, en tres niveles (marco del carro, simulacion):
// - ABAJO de la placa (motores, encoders, infrarrojos de linea, ultrasonico): cada hilo va pegado
//   a la cara de abajo, por el centro (entre los discos de los encoders y la rueda loca, por
//   encima de los infrarrojos) hasta el PASACABLES con arandela de su lado (82, ±46 mm) y sube.
// - ENTRE los dos pisos (bateria, interruptor, TB6612, laser): a 1 mm sobre el porta-baterias.
// - ARRIBA del segundo piso (ESP32, jack, infrarrojo de la cuna): a 1 cm sobre los pines.
// Entre el nivel del medio y el de arriba, los hilos suben por las dos ESQUINAS de adelante del
// segundo piso (84, ±50 mm), fuera de la escuadra del ultrasonico y de los separadores. Van dentro
// del grupo del carro (se mueven con el).
function construirCablesCarro() {
  const D = P.carroDims;
  const cc = new THREE.Group();
  CAPAS_CABLES.push(cc);
  P.carro.add(cc);
  const V = (x, y, z) => Vxyz(x, y, z);                    // marco del carro (sim) -> Three
  const S = (v) => [v.x, -v.z, v.y];
  const zAbajo = D.zPlaca - 0.0015;                       // cara de abajo de la placa
  const zArribaPlaca = D.zPlaca + 0.0015;
  const zPiso2 = D.zPiso2 - 0.0008;                        // cara de abajo del segundo piso
  const nivel = (z) => (z < zAbajo ? 0 : z < zPiso2 ? 1 : 2);
  const zMedio = (k) => zPiso2 - 0.0062 + (k % 3) * 0.001;             // sobre la bateria (67,3 mm)
  const zAlto = (k) => D.zPiso2 + 0.03 + (k % 3) * 0.0012;              // sobre los pines del ESP32
  const PASO = [0.082, 0.046];                                           // pasacables (x, |y|)
  const ESQ = [0.084, 0.05];                                              // esquina de subida
  const lado = (y, otro) => (Math.abs(y) > 0.008 ? Math.sign(y) : Math.sign(otro) || -1);
  // Encoders: su ancla mira hacia la placa; el cable sale por el extremo del header, hacia -x.
  for (const ref of Object.keys(PIN)) {
    if (/^enc_(izq|der)\./.test(ref) && PIN[ref].padre === P.carro) PIN[ref].dir = V(-1, 0, 0).normalize();
  }
  // De un punto de abajo al pasacables de su lado, y arriba hasta el nivel del medio.
  const deAbajo = ([x, y, z], s, k) => {
    const o = ((k % 3) - 1) * 0.0012;
    const [px, py] = [PASO[0] + o, s * PASO[1] + ((k >> 2) % 2 ? 0.0012 : -0.0012)];
    const zb = zAbajo - 0.004 - (k % 2) * 0.0012;
    let pts;
    if (x > 0.088) pts = [[x, y, 0.032], [x, py, 0.032], [px, py, 0.034]];               // ultrasonico (adelante)
    else if (x < -0.03) {                                                                    // encoders (atras)
      // Por dentro de los soportes de los encoders (|y| < 16,5 mm) y, pasada la rueda loca, por su costado.
      const yc = s * (0.012 + (k % 3) * 0.001), yl = s * (0.018 + (k % 3) * 0.001);
      pts = [[-0.07, y, z], [-0.07, yc, 0.03], [0.03, yc, 0.03], [0.038, yl, 0.03], [0.066, yl, 0.03], [0.078, s * 0.042, zb], [px, py, zb]];
    } else if (x > 0.07) pts = [[x, y, Math.max(z, 0.031)], [px, py, zb]];                  // infrarrojos de linea
    else pts = [[x, y, z], [0.075, y, z], [px, py, zb]];                                    // motores (bornes hacia +x)
    return [...pts, [px, py, zArribaPlaca + 0.003], [px, py, zMedio(k)]];
  };
  // De un punto del nivel de arriba a la esquina de su lado y abajo hasta el nivel del medio.
  const deArriba = ([x, y, z], s, k) => {
    const o = ((k % 3) - 1) * 0.0015;
    const [ex, ey] = [ESQ[0] + o, s * (ESQ[1] + ((k >> 2) % 2) * 0.0015)];
    return [[x, y, zAlto(k)], [x, ey, zAlto(k)], [ex, ey, zAlto(k)], [ex, ey, zMedio(k)]];
  };
  // Dos puntos del nivel del medio: primero a lo ancho, despues a lo largo.
  const enMedio = (a, b, k) => [[a[0], a[1], zMedio(k)], [a[0], b[1], zMedio(k)], [b[0], b[1], zMedio(k)]];
  const ruta = (a3, b3, k) => {
    const a = S(a3), b = S(b3);
    const na = nivel(a[2]), nb = nivel(b[2]);
    const s = lado(na === 0 ? a[1] : nb === 0 ? b[1] : na === 1 ? a[1] : b[1], na === 0 ? b[1] : a[1]);
    let pts;
    if (na === 2 && nb === 2) {
      pts = [[a[0], a[1], zAlto(k)], [b[0], a[1], zAlto(k)], [b[0], b[1], zAlto(k)]];
    } else {
      const ida = na === 0 ? deAbajo(a, s, k) : na === 2 ? deArriba(a, s, k) : [[a[0], a[1], zMedio(k)]];
      const vuelta = (nb === 0 ? deAbajo(b, s, k) : nb === 2 ? deArriba(b, s, k) : [[b[0], b[1], zMedio(k)]]).reverse();
      pts = [...ida, ...enMedio(ida[ida.length - 1], vuelta[0], k).slice(1, -1), ...vuelta];
    }
    return pts.map(([x, y, z]) => V(x, y, z));
  };
  const lead = (ref) => {
    if (!PIN[ref]) { console.warn('cable del carro: pin sin registrar', ref); return null; }
    return PIN[ref].tip.clone().addScaledVector(PIN[ref].dir, 0.006);
  };
  let k = 0;
  for (const c of G.conexiones.cables) {
    if (c.tipo !== 'carro') continue;
    for (const h of c.hilos) {
      if (!lead(h.de) || !lead(h.a)) continue;
      const par = /motor [AB]/.test(h.funcion);
      hilo(h.de, h.a, h.color, ruta(lead(h.de), lead(h.a), k++), cc,
        { r: par ? 0.0007 : 0.0005, nombre: `${c.nombre}: ${h.funcion}`, tipo: 'carro', zona: 'carro' });
    }
  }
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

// Ubica una pieza detallada de piezas/sensores.js en la planta (en `pos`, `quat`, coordenadas de
// la escena) y registra sus anclas pin_<dev>_<PIN> como pines para los cables (mismos nombres
// que la plantilla de sim/conexiones.py). Si le falta un pin lanza un error: quien la llama
// deja el modelo simple de siempre. NO la agrega a la escena (va en obj.objetos del sensor).
function montarSensorPlanta(dev, g, pos, quat, { etiquetaSobre = 0 } = {}) {
  g.position.copy(pos);
  g.quaternion.copy(quat);
  g.updateMatrixWorld(true);
  const pines = plantilla(dev).pines.map((p) => {
    const a = g.getObjectByName(`pin_${dev}_${p.n}`);
    if (!a) throw new Error(`falta pin_${dev}_${p.n}`);
    return [p, a];
  });
  const eje = new THREE.Vector3(1, 0, 0).transformDirection(g.matrixWorld);
  for (const [p, a] of pines) {
    const dir = (a.userData.dir || new THREE.Vector3(0, 1, 0)).clone().transformDirection(a.parent.matrixWorld);
    pinSuelto(`${dev}.${p.n}`, escena, a.getWorldPosition(new THREE.Vector3()), dir, p.tipo, eje);
  }
  MODULOS[dev] = g;
  if (etiquetaSobre) {
    const et = etiqueta(G.conexiones.dispositivos[dev].nombre, { alto: 0.0058, alcance: 0.4 });
    et.position.copy(pos).add(new THREE.Vector3(0, etiquetaSobre, 0));
    escena.add(et);
  }
  return g;
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
        // FC-51 (piezas/sensores.js) BOCA ABAJO sobre E1: la punta de sus dos
        // LED (ancla `optica`) justo en el origen del rayo, 5 cm sobre la
        // cinta. El largo de la placa va a lo ancho de la cinta, con el
        // header acodado hacia el riel -y (en la orilla +y esta el motor).
        // Soporte: una "bandera" impresa en L de 3 mm atornillada (M3 +
        // tuerca) por el agujero del modulo, con la cara de las soldaduras
        // contra ella, sobre una columna impresa 10 x 10 con pie de 20 x 20
        // que va con 2 M5 y tuercas en T a la ranura de arriba del riel -y.
        // La columna queda 20 mm aguas arriba de E1: el conector Dupont
        // (que sale bajo la bandera hacia -y) pasa libre.
        const rm = P.rielMonedas;
        const xS = a.x, simY = (v) => -v.z;
        let hecho = false;
        try {
          const fc = PIEZAS_SENSORES_CARRO.crearFC51({ id: 'presencia', sensorId: 'presencia' });
          // ficha x -> Three +z (sim -y); ficha z (cara de los componentes) -> Three -Y (boca abajo).
          const q = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(
            new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, -1, 0), new THREE.Vector3(1, 0, 0)));
          const pos = a.clone().sub(fc.getObjectByName('optica').position.clone().applyQuaternion(q));
          montarSensorPlanta('presencia', fc, pos, q, { etiquetaSobre: 0.03 });
          obj.objetos.push(fc);
          obj.led = fc.userData.led;
          const zB = pos.y;                                   // cara de las soldaduras (arriba)
          const yAg = simY(pos) - 0.0015;                     // agujero M3 (ficha x = 1,5 mm)
          const xCol = xS - 0.02, yCol = rm.y;   // columna sobre el eje del riel -y
          const e = 0.003;
          // Bandera en L: tramo a lo largo de x por el agujero + tramo a lo ancho hasta la columna.
          const tramoX = [xCol - 0.005, xS + 0.006], tramoY = [yCol - 0.005, yAg + 0.005];
          obj.objetos.push(
            caja(tramoX[1] - tramoX[0], 0.01, e, COLOR.impreso, Vxyz((tramoX[0] + tramoX[1]) / 2, yAg, zB + e / 2)),
            caja(0.01, tramoY[1] - tramoY[0] - 0.01, e, COLOR.impreso, Vxyz(xCol, (tramoY[0] + tramoY[1] - 0.01) / 2, zB + e / 2)));
          // Tornillo M3 (cabeza arriba) y su tuerca bajo la placa.
          const cab = cilindro(0.0027, 0.0018, 0x2a2d31, Vxyz(xS, yAg, zB + e + 0.0009), { metalness: 0.85, roughness: 0.3 }, 16);
          const tu = cilindro(0.0032, 0.0024, 0xc9ccd1, Vxyz(xS, yAg, zB - 0.0016 - 0.0012), { metalness: 0.85, roughness: 0.3 }, 6);
          // Columna y pie sobre el riel (su cara de arriba es rm.zArriba).
          const zPie = rm.zArriba + 0.003;
          const col = caja(0.01, 0.01, zB - zPie, COLOR.impreso, Vxyz(xCol, yCol, (zB + zPie) / 2));
          const pie = caja(0.02, 0.02, 0.003, COLOR.impreso, Vxyz(xCol, yCol, rm.zArriba + 0.0015));
          const m5 = [-1, 1].map((sx) => cilindro(0.004, 0.003, 0x2a2d31, Vxyz(xCol + sx * 0.0075, yCol, zPie + 0.0015),
            { metalness: 0.85, roughness: 0.3 }, 16));
          obj.objetos.push(cab, tu, col, pie, ...m5);
          // Cable: sale del Dupont hacia -y bajo la bandera, pasa por afuera del
          // riel y baja pegado a su cara de afuera.
          const t = PIN['presencia.GND'];
          const p1 = t.tip.clone().addScaledVector(t.dir, 0.016);
          const yFuera = yCol - 0.012;
          obj.rutaCable = [p1, Vxyz(xS, yFuera, p1.y), Vxyz(xS, yFuera, rm.zArriba + 0.012)];
          hecho = true;
        } catch (e) {
          console.warn('FC-51 detallado: se usa el modulo simple', e);
        }
        if (!hecho) {
          construirModulo('presencia', escena, a.clone().add(Vxyz(0, -0.013, 0.005)), yaw(-90), { sensorId: 'presencia', etiquetaSobre: 0.03 });
          const bajo = a.clone().add(Vxyz(0, -0.013, 0.003));
          const lado = new THREE.Vector3(a.x, bajo.y, -rm.y);
          const pie = new THREE.Vector3(a.x, rm.zArriba + 0.0015, -rm.y);
          obj.objetos.push(barra(bajo, lado, 0.002, MAT_ALU), barra(lado, pie, 0.002, MAT_ALU),
            caja(0.012, 0.012, 0.003, COLOR.impreso, pie.clone()));
          const xs = a.x + 0.006;
          obj.rutaCable = [new THREE.Vector3(xs, a.y + 0.03, -(a.z * -1) + 0.035), new THREE.Vector3(xs, a.y + 0.03, -rm.y + 0.012),
            new THREE.Vector3(xs, rm.zArriba + 0.012, -rm.y + 0.012)];
        }
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
      // (cara de afuera de la placa lateral del bastidor de la cinta de vasos, 4 mm)
      const yBorde = -(G.cinta_vasos.estaciones[0].posicion[1] - G.ancho_cinta_vasos / 2 - 0.007);
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
        // Webcam 1080p de piezas/sensores.js, cenital sobre E3, con el anillo
        // LED 60/40 mm. El vidrio de la lente (y el difusor del anillo, 0,2 mm
        // mas abajo) queda en `posicion` de sim/geometria.py: 15 cm sobre la
        // cinta. Girada 180 grados para que la escuadra de su rotula apunte
        // al poste (+y) y quede debajo del brazo. La sostiene el poste 2020 de
        // piezas/linea_monedas.js: abrazadera sobre la escuadra, brazo 2020
        // hasta un poste vertical pegado al costado del riel +y (con una
        // escuadra de aluminio sobre el riel). El poste es estructura, no
        // sensor: al elegir la camara se encuadra solo la camara.
        let hecho = false;
        try {
          const cam = PIEZAS_SENSORES_CARRO.crearWebcam({ id: 'cam_cenital', sensorId: 'camara', anillo: true, idAnillo: 'anillo', resolucion: '1080p' });
          cam.quaternion.copy(yaw(180));
          const vidrio = cam.getObjectByName('optica').position.clone().applyQuaternion(cam.quaternion);
          cam.position.copy(p).sub(vidrio);
          cam.updateMatrixWorld(true);
          obj.objetos.push(cam);
          obj.led = cam.userData.led;
          const rm = P.rielMonedas;
          const yMas = 2 * G.cinta_monedas.estaciones[0].posicion[1] - rm.y;   // eje del riel +y (sim)
          const zRielAbajo = rm.zArriba - 0.02;
          const tope = cam.position.clone().add(new THREE.Vector3(0, 0.037, 0));   // cara de arriba de la escuadra
          const brazo = yMas + 0.02 - g.posicion[1];                              // poste pegado al riel
          const poste = PIEZAS_LINEA_MONEDAS.crearPosteCamaraCenital({ alto: tope.y - zRielAbajo, brazo, idComponente: 'estructura' });
          poste.position.copy(tope);
          // Escuadra de aluminio (2 alas de 20 x 18 x 3 mm) entre la cara de
          // arriba del riel y la cara -y del poste, con sus 2 tornillos M5.
          const yCara = yMas + 0.01, xE = g.posicion[0];
          const esc = [caja(0.02, 0.018, 0.003, COLOR.aluminio, Vxyz(xE, yCara - 0.009, rm.zArriba + 0.0015), { metalness: 0.75, roughness: 0.38 }),
            caja(0.02, 0.003, 0.018, COLOR.aluminio, Vxyz(xE, yCara - 0.0015, rm.zArriba + 0.009), { metalness: 0.75, roughness: 0.38 }),
            cilindro(0.004, 0.003, 0x2a2d31, Vxyz(xE, yCara - 0.01, rm.zArriba + 0.0045), { metalness: 0.85 }, 16)];
          const m5 = cilindro(0.004, 0.003, 0x2a2d31, Vxyz(xE, yCara - 0.0045, rm.zArriba + 0.011), { metalness: 0.85 }, 16);
          m5.rotation.x = Math.PI / 2;
          esc.push(m5);
          escena.add(poste, ...esc);
          registrar('estructura', poste, ...esc);
          // Cable USB: sale de la carcasa hacia -x, va a lo ancho hasta el
          // poste y baja por su cara -x hasta el riel.
          const usb = cam.getObjectByName('pin_cam_cenital_USB').getWorldPosition(new THREE.Vector3());
          const xUsb = usb.x, yPoste = g.posicion[1] + brazo, xBaja = g.posicion[0] - 0.012;
          obj.rutaCable = [usb.clone().add(new THREE.Vector3(-0.004, 0, 0)), Vxyz(xUsb - 0.004, yPoste, usb.y),
            Vxyz(xBaja, yPoste, usb.y), Vxyz(xBaja, yPoste, zRielAbajo)];
          obj.anclaCamara = tope.clone().add(new THREE.Vector3(0, 0.045, 0));
          hecho = true;
        } catch (e) {
          console.warn('webcam cenital detallada: se usa el modelo simple', e);
        }
        if (!hecho) {
          const partes = camaraConSoporte(p, mira, { anillo: true, basePoste: Vxyz(g.posicion[0], g.posicion[1] + 0.075, 0) });
          obj.objetos.push(...partes);
          obj.rutaCable = partes.rutaCable;
        }
      } else {
        // Camara de vasos: al costado, a la altura de la boca, sobre su poste.
        try {
          // Webcam 720p de sensores.js (sin anillo: la luz es el panel de contraluz) con escuadra
          // y rotula sobre un poste de perfil 20x20 al piso (piezas/linea_vasos.js).
          const cv = PIEZAS_VASOS.crearCamaraVasos({ alturaOptica: g.posicion[2], sensorId: 'camara_vasos' });
          cv.position.copy(p);
          obj.objetos.push(cv);
          cv.updateMatrixWorld(true);
          obj.led = cv.userData.led;
          obj.rutaCable = [cv.getObjectByName('pin_cam_vasos_USB').getWorldPosition(new THREE.Vector3()),
            ...cv.userData.puntosPoste.map((q) => cv.localToWorld(q.clone()))];
        } catch (e) {
          console.warn('camara de vasos: se usa el modelo simple', e);
          const partes = camaraConSoporte(p, mira, { basePoste: Vxyz(g.posicion[0], g.posicion[1] - 0.02, 0) });
          obj.objetos.push(...partes);
          obj.rutaCable = partes.rutaCable;
        }
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
      if (!obj.led) {   // la webcam de la camara de vasos trae su propio LED de actividad
        const led = new THREE.Mesh(new THREE.SphereGeometry(0.003, 12, 12), new THREE.MeshBasicMaterial({ color: 0x30363d }));
        led.position.copy(p).add(new THREE.Vector3(0, 0.014, 0));
        obj.led = led;
        obj.objetos.push(led);
      }
      obj.ancla = obj.anclaCamara || p.clone().add(new THREE.Vector3(0, 0.03, 0));   // la webcam cenital es mas alta que 3 cm
    } else if (g && g.tipo === 'proximidad') {
      // `posicion` es la CARA activa del sensor; el cuerpo queda detras.
      const p = V(g.posicion);
      const mira = new THREE.Vector3(g.mira[0], g.mira[2], -g.mira[1]).normalize();
      const CAMPO = { sensor_interior: [0.105, 12.5, 17.5], capacitivo: [0.006, 35, 40], inductivo: [0.004, 30, 35],
                      hall_carrusel: [0.004, 30, 35] }[s.id];
      let modulo, colgar = null;
      if (g.bajo_cinta) {
        // Capacitivo LJC18A3 (tapa azul) e inductivo LJ18A3 (tapa naranja)
        // de piezas/sensores.js, debajo de la cinta, mirando hacia arriba, en
        // el agujero de la platina M18 de la bancada (piezas/linea_monedas.js,
        // centrada en la misma x, y que el sensor). La platina ya trae su
        // arandela de arriba y la CONTRATUERCA de abajo: al sensor le queda
        // UNA sola tuerca, la de arriba, apoyada en esa arandela, con el
        // centro 10,5 mm bajo la cara (cara a 2,5 mm bajo la superficie, como
        // en sim/geometria.py). En crearM18 la distancia de la tuerca se mide
        // desde el final de la cabeza (6 mm la del capacitivo, 8 la del
        // inductivo), no desde la cara.
        const cap = s.id === 'capacitivo';
        try {
          const cabeza = cap ? 6 : 8;
          const crear = cap ? PIEZAS_SENSORES_CARRO.crearCapacitivoLJC18A3 : PIEZAS_SENSORES_CARRO.crearInductivoLJ18A3;
          // Cola de cable corta (8 mm): los hilos terminan ~12 mm mas arriba y la funda sale de lado
          // por encima del retorno de la banda (su cara de arriba, a ~333 mm), sin tocarlo.
          modulo = crear({ id: s.id, sensorId: s.id, tuercas: [10.5 - cabeza], cable: 8 });
          // La arandela dentada de la pieza queda del lado de la cara (sobre
          // la tuerca, en el aire): aqui la arandela es la de la platina.
          const t0 = modulo.getObjectByName('tuerca_0');
          const ar = modulo.children[modulo.children.indexOf(t0) + 1];
          if (ar && !ar.name) modulo.remove(ar);
          modulo.position.copy(p);
          modulo.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), mira);
        } catch (e) {
          console.warn(`${s.id} M18 detallado: se usa el modelo simple`, e);
          modulo = sensorCilindrico(p, mira, cap ? { largo: 0.068, colorCara: 0x2f6fd0 } : { largo: 0.060, colorCara: COLOR.naranja });
        }
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
        try {
          // KY-003 de piezas/sensores.js: la cara marcada del A3144 (ancla
          // `optica`, debajo de la placa) justo en `posicion`, que esta 4 mm
          // sobre la cara de arriba del iman 6 x 3 del disco del carrusel
          // (piezas/linea_monedas.js, a R + 15 mm del eje). Lo toma un taco
          // impreso de 6 x 6 x 5 mm atornillado (M3) por el agujero del modulo;
          // del taco sube la varilla de aluminio hasta la viga del portico.
          const ky = PIEZAS_SENSORES_CARRO.crearHallKY003({ id: 'hall', sensorId: s.id });
          const pos = p.clone().sub(ky.getObjectByName('optica').position.clone().applyQuaternion(q));
          montarSensorPlanta('hall', ky, pos, q, { etiquetaSobre: 0.03 });
          modulo = ky;
          obj.objetos.push(ky);
          const agujero = ky.localToWorld(new THREE.Vector3(-2.5 * MM, 1.6 * MM, -4.5 * MM));   // ficha (-2,5; 4,5), cara de arriba
          obj.objetos.push(caja(0.006, 0.006, 0.005, COLOR.impreso, agujero.clone().add(new THREE.Vector3(0, 0.0025, 0))));
          colgar = agujero.clone().add(new THREE.Vector3(0, 0.005, 0));
          // Taco que toma la varilla bajo la viga del portico (antes quedaba
          // tocandola, sin nada que la sujete).
          // 8 mm corrido en x (agente de solapes, 2026-09-27): justo encima baja la varilla M5 que
          // cuelga la placa fija del almacen (a 30 grados, R 56 mm) y atravesaba este taco.
          obj.objetos.push(caja(0.012, 0.02, 0.006, COLOR.impreso, new THREE.Vector3(colgar.x + 0.008, P.portico.z - 0.01 - 0.003, -P.portico.y)));
        } catch (e) {
          console.warn('KY-003 detallado: se usa el modulo simple', e);
          const centro = p.clone().addScaledVector(fuera, 0.006).add(new THREE.Vector3(0, 0.0035, 0));
          modulo = construirModulo('hall', escena, centro, q, { sensorId: s.id, etiquetaSobre: 0.03 });
          colgar = centro.clone().addScaledVector(fuera, 0.002).add(new THREE.Vector3(0, 0.0016, 0));
        }
        obj.ancla = p.clone().add(new THREE.Vector3(0, 0.03, 0));
      } else {
        // GY-530 con el VL53L0X mirando hacia abajo y los pines arriba.
        modulo = construirModulo('vl53_interior', escena, p.clone().add(new THREE.Vector3(0, 0.001, 0)), yaw(0), { sensorId: s.id, etiquetaSobre: 0.03 });
        try {
          // Porta-sensor impreso atornillado por los 2 agujeros del GY-530 con separadores M2 y
          // un bloque con prisionero que toma la varilla (piezas/linea_vasos.js).
          const porta = PIEZAS_VASOS.crearPortaVL53Interior({ sensorId: s.id });
          porta.position.copy(p).add(new THREE.Vector3(0, 0.001, 0));
          obj.objetos.push(porta);
          colgar = porta.position.clone().add(porta.userData.colgar);
        } catch (e) {
          console.warn('porta VL53 interior: se usa el modelo simple', e);
          colgar = p.clone().add(Vxyz(0, -0.003, 0.0026));
          // Abrazadera impresa: la varilla no se clava en la placa, la toma un bloque pegado
          // con cinta doble faz (se veia como si la atravesara, auditoria 2026-09-27).
          obj.objetos.push(caja(0.009, 0.007, 0.003, 0x1b1e22, colgar.clone().add(new THREE.Vector3(0, 0.0015, 0))));
          colgar.add(new THREE.Vector3(0, 0.003, 0));
        }
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
        // El Hall llega a su taco 8 mm corrido en x (esquiva la varilla de la placa fija).
        const alPortico = new THREE.Vector3(colgar.x + (s.id === 'hall_carrusel' ? 0.008 : 0), zVarilla, -P.portico.y);
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
  } else if (c.apariencia === 'moneda_extranjera') {
    // Moneda de otro pais (1 euro): se ve como moneda bimetalica, pero sin cara colombiana.
    const alto = 0.0022;
    grupo.add(cilindro(d / 2, alto, COLOR.oro, new THREE.Vector3(0, alto / 2, 0), { metalness: 0.85, roughness: 0.3 }));
    grupo.add(cilindro(d * 0.36, alto + 0.0003, COLOR.plata, new THREE.Vector3(0, alto / 2, 0), { metalness: 0.85, roughness: 0.3 }));
    const et = etiqueta('1 €', { alto: 0.007, color: '#9fb8ff' });
    et.position.set(0, 0.012, 0);
    grupo.add(et);
  } else if (c.tipo === 'bloque') {
    const metal = c.apariencia === 'bloque_metalico';
    grupo.add(caja(0.02, 0.02, 0.02, metal ? 0x8d939b : 0x3372c4, new THREE.Vector3(0, 0.01, 0)));
  } else {
    // Botones y discos: los agujeros se dibujan SOLO si la pieza los tiene (contornos_internos),
    // que es lo que la camara busca. Antes todo lo metalico salia con 2 ojales, y un disco liso o
    // una moneda extranjera parecian "perforados" aunque la camara (bien) no les encontraba agujeros.
    const alto = 0.003;
    const plastico = c.tipo === 'boton_plastico';
    grupo.add(cilindro(d / 2, alto, plastico ? 0xd9259f : 0x8d939b, new THREE.Vector3(0, alto / 2, 0), plastico ? {} : { metalness: 0.8, roughness: 0.35 }));
    const agujeros = c.contornos_internos ?? (c.apariencia === 'disco' ? 0 : 1);
    if (agujeros > 0) for (const dx of [-0.0025, 0.0025]) grupo.add(cilindro(0.0012, alto + 0.0006, 0x07090c, new THREE.Vector3(dx, alto / 2, 0)));
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
      // Sale de la cinta en el ciclo en que la simulacion la GUARDA (evento
      // `e4/almacen`): para entonces su tubo ya esta quieto bajo la carga.
      // Mientras esperaba al carrusel se quedo quieta en la descarga (seguia en
      // la cinta). Cae casi vertical a la boca del tubo.
      const guardada = (estado.eventos_tick || []).find((e) => e.src === 'e4' && e.ev === 'almacen' && e.casilla === id);
      const d = guardada ? guardada.tubo : parseInt(f.clase, 10);
      const den = P.tubos[d] ? d : 'otras';
      const tubo = P.tubos[den];
      moverDesvio(true, retrasoDesvio);
      const boca = b.clone();
      // Toda la caida (embudo, compuerta, canal corto, boca y fondo del tubo)
      // dura lo mismo que en el montaje y en la simulacion: caida_moneda_tubo.
      // El ultimo 0,1 s es el asentamiento en la pila (el rebote que el tiempo
      // del config ya incluye): la moneda ya se ve en la pila y el disco sigue
      // quieto; recien despues puede arrancar el giro siguiente.
      const tCaida = seg('caida_moneda_tubo', 400);
      const tAsienta = Math.min(0.1, tCaida / 4);
      const tBaja = tCaida - tAsienta;
      const caer = [
        { puntos: caidaEmbudo, seg: tBaja * 0.35, ease: caida },
        { puntos: [a, boca], seg: tBaja * 0.35, ease: caida },
        { puntos: [boca, boca.clone().add(new THREE.Vector3(0, -0.035, 0))], seg: tBaja * 0.3, ease: caida },
      ];
      if (tubo) tubo.cayendo = (tubo.cayendo || 0) + 1;
      // Anotada en el aire desde ya: el giro hacia el tubo de la SIGUIENTE
      // moneda (que llega despues) no arranca hasta que esta aterrice.
      const marca = anotarEnAire();
      const alFinal = () => {
        escena.remove(f.grupo);
        animar(tAsienta, () => {}, { fin: () => quitarDelAire(marca) });
        if (tubo) {
          // ESTA moneda llego: la pila de SU tubo crece una (sincronizarAlmacen).
          tubo.cayendo = Math.max(0, tubo.cayendo - 1);
          tubo.aterrizadas = (tubo.aterrizadas || 0) + 1;
          sincronizarAlmacen();
        }
      };
      // Por si el visor viene atrasado respecto a la simulacion: no deja la
      // cinta hasta que el giro que trae su tubo a la carga haya terminado.
      tramos(f.grupo, llegar, () => animar(0.001, () => {}, { espera: () => faltaSuGiro(marca),
        fin: () => tramos(f.grupo, caer, alFinal) }));
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
  try {
    // Vaso de pared delgada con fondo levantado, pestana con labio enrollado, cinta ArUco que
    // sigue la conicidad y tapa con su cono (piezas/linea_vasos.js). Mismos nodos que antes.
    const grupo = PIEZAS_VASOS.crearVaso({ diametro: g.diametro, altura: g.altura, reborde: g.reborde,
      mapaAruco: texturaCintaAruco(marcador || id) });
    const n = (k) => grupo.getObjectByName(k);
    const partes = { cuerpo: n('cuerpo'), fondo: n('fondo'), reborde: n('reborde'), aro: n('aro'), tapa: n('tapa'),
      aruco: n('aruco'), pila: n('pila'), figura: n('figura'), fantasma: n('fantasma') };
    const anillo = new THREE.Mesh(new THREE.RingGeometry(g.diametro / 2 + 0.004, g.diametro / 2 + 0.008, 40), new THREE.MeshBasicMaterial({ color: 0x8b949e, side: THREE.DoubleSide }));
    anillo.rotation.x = -Math.PI / 2;
    anillo.position.y = 0.0006;
    const et = etiqueta(`vaso ${id}`, { alto: 0.011 });
    et.position.y = g.altura + 0.03;
    grupo.add(anillo, et);
    partes.cuerpo.castShadow = false;
    escena.add(grupo);
    return { grupo, ...partes, anillo, et, monedas: 0, fuera: false, indice: -1, marcador };
  } catch (e) {
    console.warn('vaso: se usa el modelo simple', e);
  }
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
    if (e.poner) { e.poner(u); return; }   // biela-manivela de piezas/linea_vasos.js
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
  if (t.poner) {
    // Escape de piezas/linea_vasos.js: el SG90 gira y los dedos se cruzan (u = 0 -> 1 -> 0).
    animar(0.12, (u) => t.poner(suave(u)), { retraso, dueno: dedoAbajo });
    animar(0.12, (u) => t.poner(1 - suave(u)), { retraso: retraso + 0.35, dueno: dedoAbajo });
  } else {
    const xa0 = dedoAbajo.position.x, xb0 = dedoArriba.position.x;
    animar(0.12, (u) => { dedoAbajo.position.x = xa0 + 0.014 * suave(u); dedoArriba.position.x = xb0 - 0.006 * suave(u); }, { retraso, dueno: dedoAbajo });
    animar(0.12, (u) => { dedoAbajo.position.x = xa0 + 0.014 * (1 - suave(u)); dedoArriba.position.x = xb0 - 0.006 * (1 - suave(u)); }, { retraso: retraso + 0.35, dueno: dedoAbajo });
  }
  // La tapa nueva (con su cono) tiene el origen en su asiento; la vieja era un disco centrado.
  const tapa = t.crear ? t.crear() : cilindro(t.rTapa, 0.005, COLOR.tapa, new THREE.Vector3());
  tapa.position.copy(Vxyz(t.x, t.y, t.zBase));
  tapa.visible = false;
  escena.add(tapa);
  const destino = posEstacionVasos(2).add(new THREE.Vector3(0, G.vaso.altura + (t.crear ? 0 : 0.0015), 0));
  animar(0.01, () => { tapa.visible = true; }, { retraso: retraso + 0.1 });
  recorrer(tapa, [tapa.position.clone(), destino], 0.12, { ease: caida, retraso: retraso + 0.12,
    fin: () => { escena.remove(tapa); v.tapa.visible = true; v.tapaCayendo = false; } });
}

// ---------------------------------------------------------------------------
// animaciones de actuadores disparadas por eventos
// ---------------------------------------------------------------------------

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

function procesarEventos() {
  if (!estado.eventos_tick || estado.tick === ultimoTick) return;
  const primero = ultimoTick === -1;
  ultimoTick = estado.tick;
  // La cinta de monedas se anima solo si de verdad avanzo en este ciclo
  // (vacia y sin carga se queda quieta: evento 'espera').
  if (!primero && estado.eventos_tick.some((e) => e.ev === 'paso' && e.src === 'linea')) moverCinta('monedas', seg('avance_casilla_monedas', 600));
  if (primero) ubicarCarrusel();
  for (const e of estado.eventos_tick) {
    if (e.src === 'carrusel' && e.ev === 'gira') girarCarrusel(e);
    if (e.ev === 'prensa') ciclarPrensa(seg('avance_casilla_vasos', 1000));
    if (e.ev === 'cortina' && e.activa) subirPrensa();
    if (e.ev === 'embalado') animarEmbalado(e);
    if (e.ev === 'presencia' && e.tipo_real === 'mano') P.manoCarga.hasta = performance.now() + 1200;
  }
  ui.eventos(estado.eventos_tick);   // la bitacora (interfaz.js)
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

// Direccion (desde el sensor hacia la camara) para ver los sensores de material bajo la cinta:
// desde atras (-z de three = +y de la simulacion) y 50° por debajo de la horizontal. Es la que
// dejo ver mas de los dos M18 en un barrido por raycast (elevacion x azimut x distancia): ~92 %
// de sus puntos a la vista, contra ~60-75 % de la toma anterior (casi desde abajo, del lado
// del operador), que tapaban la viga del portico y las de la mesa.
const DIR_BAJO_CINTA = new THREE.Vector3(0, -Math.sin(THREE.MathUtils.degToRad(50)), -Math.cos(THREE.MathUtils.degToRad(50)));
// Centro de los dos sensores de material (sus mallas reales; si no estan, bajo E1-E2).
function centroMaterial() {
  const caja = new THREE.Box3();
  for (const id of ['capacitivo', 'inductivo']) for (const m of mallasDeSensor(id)) {
    const mat = m.material;
    if (m.isInstancedMesh || (mat && (mat.isMeshBasicMaterial || (mat.transparent && mat.opacity < 0.3)))) continue;
    caja.expandByObject(m);
  }
  if (!caja.isEmpty()) return caja.getCenter(new THREE.Vector3());
  const em = G.cinta_monedas.estaciones.map((e) => V(e.posicion));
  return em[0].clone().lerp(em[1], 0.5).add(new THREE.Vector3(0, -0.05, 0));
}

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
    // De la esquina de la carga (-x), 40° desde arriba: de frente (desde el operador) la pantalla del
    // portatil quedaba justo detras de la cinta y competia con las estaciones (revision visual,
    // 2026-09-28). Asi E1..E4 quedan en diagonal, sin encimarse, y el portatil queda al costado.
    monedas: [centroM, new THREE.Vector3(-0.32, 0.29, 0.13)],
    vision: [em[2], new THREE.Vector3(0.06, 0.12, 0.22)],
    almacen: [almacen, new THREE.Vector3(0.12, 0.12, 0.26)],
    vasos: [centroV.clone().add(new THREE.Vector3(0, 0.07, 0)), new THREE.Vector3(0.02, 0.2, 0.52)],
    tapa: [ev[2].clone().lerp(ev[3], 0.5).add(new THREE.Vector3(0, 0.09, 0)), new THREE.Vector3(0.05, 0.1, 0.32)],
    canaleta: [c.ini.clone().lerp(c.fin, 0.55), new THREE.Vector3(0.42, 0.2, 0.3)],
    pista: [centroP, new THREE.Vector3(0.0, 1.9, 1.2)],
    // Los dos sensores de material (M18) se ven desde abajo de la cinta, del lado de ATRAS (+y de
    // la simulacion, -z aqui) y a ~50° bajo la horizontal: buscado por raycast (2026-09-28). Del
    // lado del operador la viga del portico (y = -45 mm, z = 400 mm) tapa la mitad de abajo, y
    // casi desde abajo se miraba entre las vigas de la mesa, con los sensores chicos. La mira es
    // el centro de los dos sensores (no la cinta): quedan grandes y enteros, con rosca, tuerca y
    // platina. A 0,22 m la caja de control queda detras de la camara, tambien con el panel
    // abierto (x1,4).
    material: [centroMaterial(), new THREE.Vector3(-0.094, -0.122, -0.258)],
    // Desde arriba: en diagonal desde el operador, la cinta de vasos remodelada (tubo de tapas,
    // prensa, portico) quedaba en medio y tapaba la caja (2026-09-28).
    caja: [Vxyz(P.caja.bx, P.caja.by, 0.02), new THREE.Vector3(0, 0.45, 0.02)],
    // De frente a la pantalla de la laptop (la pantalla mira hacia +z de three), ~9° mas desde
    // arriba que su normal: justo de frente, al correr la toma de lado por el panel, la camara
    // caia DENTRO del NEMA17 de la cinta y la pantalla se veia negra (2026-09-28).
    asistente: [P.asistente ? P.asistente.panel.getWorldPosition(new THREE.Vector3()) : centroP,
      new THREE.Vector3(0, 0.72 * Math.sin(LAPTOP.apertura + 0.16), 0.72 * Math.cos(LAPTOP.apertura + 0.16))],
    carro: [P.carro ? P.carro.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 0.04, 0)) : centroP,
      // ~0,6 m: el carro entero con su vaso y un poco de pista (a 0,3 m quedaba demasiado cerca).
      new THREE.Vector3(0.33, 0.29, 0.42)],
  };
  ui.marcarVista(nombre);
  const [objetivo, desplazamiento] = vistas[nombre] || vistas.todo;
  // La laptop esta detras de la cinta: alejarse por el panel la taparia con la cinta.
  volarA(objetivo.clone(), objetivo.clone().add(desplazamiento), { seguir: nombre === 'carro', alejar: nombre !== 'asistente' ? true : 'poco' });
}

function volarA(objetivo, posicion, { seguir = false, alejar = true } = {}) {
  // El panel lateral tapa la izquierda de la pantalla: TODA toma (vistas, sensor, componente) se
  // corre de lado (en el plano de la pantalla) para que lo enfocado quede en el centro de la
  // parte libre. A la distancia d, media pantalla de ancho son d*tan(fov/2)*aspecto metros.
  // Y se aleja en proporcion (W / ancho libre, hasta x1,4): lo encuadrado para la pantalla
  // entera cabe en la parte libre (la pantalla de la laptop quedaba cortada por el panel).
  // A cualquier ancho (revision visual, 2026-09-28): a 900 px o menos el panel es una hoja ABAJO
  // (45 % de la altura) y la toma no la tenia en cuenta: el carro y las estaciones quedaban debajo
  // de la hoja. Ahora la toma se centra en la parte libre que mide la interfaz (`zonaLibre`: a la
  // derecha del panel, o entre las vistas de arriba y la hoja de abajo), de lado Y de alto, y se
  // aleja segun la dimension mas recortada (de lado hasta x1,4 como antes; con la hoja, hasta x1,9).
  let libre = null;
  try { libre = ui.zonaLibre ? ui.zonaLibre() : null; } catch (e) { libre = null; }
  if (!libre) {
    const t = ui.anchoTapado();
    libre = { izq: t, der: window.innerWidth, arriba: 0, abajo: window.innerHeight };
  }
  const W = window.innerWidth, H = window.innerHeight;
  const anchoLibre = Math.max(1, libre.der - libre.izq), altoLibre = Math.max(1, libre.abajo - libre.arriba);
  const cx = (libre.izq + libre.der) / 2, cy = (libre.arriba + libre.abajo) / 2;
  const ndx = cx / W * 2 - 1, ndy = 1 - cy / H * 2;
  if (Math.abs(ndx) > 1e-3 || Math.abs(ndy) > 1e-3) {
    const hojaAbajo = libre.abajo < H - 20;
    // Lo encuadrado para la pantalla entera (menos las barras de arriba, que siempre estuvieron).
    const porAncho = W / anchoLibre, porAlto = (H - libre.arriba) / altoLibre;
    // 'poco' (vista Asistente): de lado no se aleja (la cinta taparia la laptop), pero con la hoja
    // de abajo la pantalla no cabia en la franja libre: se aleja lo justo, hasta x1,45.
    const tope = alejar === 'poco' ? (hojaAbajo ? 1.45 : 1) : (hojaAbajo ? 1.9 : 1.4);
    const lejos = alejar ? Math.max(1, Math.min(tope, Math.max(porAncho, porAlto))) : 1;
    posicion = objetivo.clone().addScaledVector(posicion.clone().sub(objetivo), lejos);
    const d = posicion.distanceTo(objetivo);
    const adelante = new THREE.Vector3().subVectors(objetivo, posicion).normalize();
    const derecha = adelante.clone().cross(camara.up).normalize();
    const arribaPantalla = derecha.clone().cross(adelante).normalize();
    const mitadAlto = d * Math.tan(THREE.MathUtils.degToRad(camara.fov) / 2);
    const mitadAncho = mitadAlto * camara.aspect;
    // Correr la camara (y su mira) al lado contrario de donde debe verse lo enfocado.
    const corr = derecha.multiplyScalar(-mitadAncho * ndx).addScaledVector(arribaPantalla, -mitadAlto * ndy);
    objetivo = objetivo.clone().add(corr);
    posicion = posicion.clone().add(corr);
    desfaseFoco.copy(corr);
  } else desfaseFoco.set(0, 0, 0);
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

// Clic en un sensor -> lo selecciona.
const rayo = new THREE.Raycaster();
renderer.domElement.addEventListener('click', (ev) => {
  const m = new THREE.Vector2((ev.clientX / window.innerWidth) * 2 - 1, -(ev.clientY / window.innerHeight) * 2 + 1);
  rayo.setFromCamera(m, camara);
  const golpes = rayo.intersectObjects(escena.children, true);
  // Lo MAS CERCANO de los dos (antes ganaba la laptop aunque estuviera detras: en la vista
  // Monedas, clic en un sensor de la cinta llevaba al asistente).
  // Los campos de vision (conos y volumenes casi transparentes) solo cuentan si no hay una pieza
  // solida: el campo de la camara de vasos tapaba al VL53L0X del interior (2026-09-28).
  const util = (g) => g.object.visible && (g.object.userData.asistente || g.object.userData.sensorId);
  const fantasma = (g) => g.object.userData.campo || (g.object.material && g.object.material.transparent && g.object.material.opacity < 0.5);
  const golpe = golpes.find((g) => util(g) && !fantasma(g)) || golpes.find(util);
  if (!golpe) return;
  if (golpe.object.userData.asistente) return vista('asistente');
  ui.seleccionarSensor(golpe.object.userData.sensorId, true);
});

// ---------------------------------------------------------------------------
// pantalla del asistente en la laptop 3D
// ---------------------------------------------------------------------------

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

// Lleva la camara a ver `mallas` enteras: la distancia sale del tamaño
// real de la pieza (y del campo de vision de la camara), y la mira es desde
// afuera de la planta hacia adentro, un poco desde arriba (o desde abajo si
// `desdeAbajo`), para que nada de la planta la tape.
function encuadrar(mallas, { desdeAbajo = false } = {}) {
  const caja = new THREE.Box3();
  escena.updateMatrixWorld(true);
  let enCarro = false;
  for (const o of mallas) o.traverse((m) => {
    if (!m.isMesh || m.userData.campo || m.userData.soloSombra || m.isInstancedMesh) return;
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
    // Debajo de la cinta: la misma direccion que la vista Material (ver DIR_BAJO_CINTA).
    dir = DIR_BAJO_CINTA.clone();
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
      // Mas lejos que en la planta (usuario, 2026-09-27): la pieza con el carro alrededor, para
      // ver donde queda montada.
      volarA(centro, centro.clone().addScaledVector(dir, Math.max(dist * 1.6, 0.42)), { seguir: true });
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

// Resalta (pulso ambar) las mallas del componente elegido.
let compPintado = null;
function resaltarComponente(t) {
  if (compPintado && compPintado !== SEL.componente) {
    for (const o of COMP[compPintado] || []) o.traverse((m) => { if (m.isMesh && m.material.emissive) m.material.emissive.setHex(0x000000); });
    compPintado = null;
  }
  if (!SEL.componente) return;
  const k = 0.35 + 0.3 * Math.sin(t * 5);
  for (const o of COMP[SEL.componente] || []) o.traverse((m) => {
    if (m.isMesh && m.material.emissive) { m.material.emissive.setHex(COLOR.ambar); m.material.emissiveIntensity = k; }
  });
  compPintado = SEL.componente;
}

// Sin internet (lo decide la interfaz): la nube del asistente queda gris, con la linea roja y la
// etiqueta "sin internet".
function nubeSinInternet(hay) {
  if (!P.asistente) return;
  const sinRed = hay === false;
  P.asistente.et.userData.oculta = sinRed;
  P.asistente.etSinRed.userData.oculta = !sinRed;
  P.asistente.matNube.color.set(sinRed ? 0x5b6270 : 0xdfe7f5);
  P.asistente.matNube.emissive.set(sinRed ? 0x000000 : 0x539bf5);
  P.asistente.linea.material.color.set(sinRed ? 0xe5534b : 0x539bf5);
}

// ---------------------------------------------------------------------------
// estado en vivo
// ---------------------------------------------------------------------------

let tickAnterior = -1;

// Corrida nueva (el tick vuelve a empezar): se borra todo lo dinamico.
function limpiarCorrida() {
  ANIMS.length = 0;
  if (P.rastro) { P.rastroN = 0; P.rastro.geometry.setDrawRange(0, 0); }
  for (const f of fichas.values()) escena.remove(f.grupo);
  for (const v of vasos.values()) escena.remove(v.grupo);
  fichas.clear(); vasos.clear();
  for (const c of Object.values(CINTAS)) { c.moviendo = false; c.seps.forEach((m, i) => { m.position.x = c.base[i]; m.visible = i > 0; }); }
  if (P.carrusel) {
    Object.assign(P.carrusel, { angulo: 0, finGiro: 0, inicioUltimo: 0, girando: false, enAire: [] });
    P.carrusel.activo = ++P.carrusel.giros;
    P.carrusel.empezado = P.carrusel.terminado = P.carrusel.giros;
    P.carrusel.grupo.rotation.y = 0;
  }
  for (const t of Object.values(P.tubos || {})) { t.vaciarEn = 0; t.cayendo = 0; t.aterrizadas = 0; }
  // Corrida nueva: lo que ya hay en los tubos (turno anterior) se pone de una vez.
  P.almacenVisto = false;
  for (const c of Object.values(enCubeta)) c.clear();
  // Las fichas que quedaron en las cubetas tambien son de la corrida vieja.
  for (const o of [...escena.children]) if (o.userData.deCubeta) escena.remove(o);
  ui.limpiarBitacora();
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
    // Chips, avisos, respuesta a la ultima orden y el panel: interfaz.js.
    ui.estadoNuevo(estado);
  } catch (e) {
    ui.falloConexion();
  }
}

// ---------------------------------------------------------------------------
// arranque
// ---------------------------------------------------------------------------

// Menos llamadas de dibujo con el MISMO detalle (usuario, 2026-09-28: "quedo algo pesado").
// Al terminar de construir, las mallas quietas que se ven igual se unen en una sola
// (piezas/optimizar.js explica que se une y que no). ?sinoptimizar deja la escena como se
// construyo (para comparar); ?auditar muestra el resumen en window.__visor.optimizacion.
let resumenOptimizacion = null;
function optimizar() {
  if (new URLSearchParams(location.search).has('sinoptimizar')) return;
  try {
    resumenOptimizacion = PIEZAS_OPTIMIZAR.optimizarEscena(escena, {
      renderer,
      auditar: new URLSearchParams(location.search).has('auditar'),
      comp: COMP,
      // Todo lo que las animaciones, los sensores y los botones mueven, ocultan o recolorean.
      referencias: [P, SENS, CINTAS, CAPAS_CABLES, fichas, vasos],
      // Se buscan por nombre mientras corre (el cuerno del servo del empujador).
      nombresVivos: ['cuerno'],
      // Listas que solo se usan al construir (componentes de cada pieza, partes de cada sensor):
      // lo que se anima de un sensor va aparte (rayos, franjas, led, cono, campos).
      ignorarDatos: ['fijas', 'estructura', 'motor', 'objetos'],
    });
  } catch (e) { console.warn('optimizar escena: se deja sin unir', e); }
}

// Camara de la sombra del sol ajustada a lo que hay (2026-09-28): antes era un cuadrado fijo de
// 2,8 m que dejaba sin sombra el final de la pista. Se mide la caja de toda la escena vista desde
// el sol y el mapa crece para que cada pixel de sombra siga midiendo ~1,4 mm (lo mismo de antes).
function ajustarSombra() {
  escena.updateMatrixWorld(true);
  sol.shadow.updateMatrices(sol);
  const vista = sol.shadow.camera.matrixWorldInverse;
  const caja = new THREE.Box3(), p = new THREE.Vector3(), tam = new THREE.Vector3();
  escena.traverse((m) => {
    if (!m.isMesh || !(m.castShadow || m.receiveShadow)) return;
    for (let q = m; q; q = q.parent) if (!q.visible) return;
    if (!m.geometry.boundingBox) m.geometry.computeBoundingBox();
    const b = m.geometry.boundingBox;
    if (b.getSize(tam).length() > 4) return;   // el piso del salon (14 m) no cuenta
    for (let i = 0; i < 8; i++) {
      p.set(i & 1 ? b.max.x : b.min.x, i & 2 ? b.max.y : b.min.y, i & 4 ? b.max.z : b.min.z);
      caja.expandByPoint(p.applyMatrix4(m.matrixWorld).applyMatrix4(vista));
    }
  });
  if (caja.isEmpty()) return;
  const margen = 0.06;
  // La camara de la luz mira hacia -z: lo mas cerca tiene z mas alta.
  Object.assign(sol.shadow.camera, { left: caja.min.x - margen, right: caja.max.x + margen, bottom: caja.min.y - margen,
    top: caja.max.y + margen, near: Math.max(0.05, -caja.max.z - 0.5), far: -caja.min.z + 0.5 });
  sol.shadow.camera.updateProjectionMatrix();
  const lado = Math.max(caja.max.x - caja.min.x, caja.max.y - caja.min.y) + 2 * margen;
  const px = THREE.MathUtils.clamp(Math.ceil(lado / 0.00137 / 256) * 256, 1024, 4096);
  if (px !== sol.shadow.mapSize.x) {
    sol.shadow.mapSize.set(px, px);
    if (sol.shadow.map) { sol.shadow.map.dispose(); sol.shadow.map = null; }
  }
}

// Planos de recorte de la camara segun lo lejos que mira (anti-parpadeo, 2026-09-28). La
// precision del z-buffer depende casi solo del plano cercano: con near fijo en 5 mm, de lejos
// dos caras a 0,1 mm (las capas de la pista, la placa del teclado) caian en el mismo valor de
// profundidad y "parpadeaban" al mover la camara. Cerca de la pieza near baja hasta 2 mm (se
// puede acercar sin que se corte); de lejos sube (hasta 8 cm) y la precision alcanza.
// ?planosfijos deja los de antes (5 mm y 30 m), para comparar.
const PLANOS_FIJOS = new URLSearchParams(location.search).has('planosfijos');
function ajustarPlanos() {
  if (PLANOS_FIJOS) return;
  const d = camara.position.distanceTo(controles.target);
  const near = THREE.MathUtils.clamp(d / 40, 0.002, 0.08);
  const far = THREE.MathUtils.clamp(d * 6 + 6, 12, 40);
  if (Math.abs(near - camara.near) > camara.near * 0.02 || far !== camara.far) {
    camara.near = near;
    camara.far = far;
    camara.updateProjectionMatrix();
  }
}

// Limite de la orbita: la camara no baja del piso (3 cm), pero SI puede mirar desde abajo algo que
// esta en alto. Con el tope fijo de ~89° (horizontal) las tomas "desde abajo" de los sensores de
// material quedaban aplastadas a la horizontal, entre las vigas de la mesa (2026-09-28). El angulo
// maximo sale de la altura de la mira y la distancia: cos(polar) >= -(altura - 3 cm) / distancia.
function limitarPolar() {
  const d = camara.position.distanceTo(controles.target);
  const h = controles.target.y - 0.03;
  const libre = h > 0 && d > 1e-4 ? Math.acos(THREE.MathUtils.clamp(-h / d, -1, 1)) : 0;
  controles.maxPolarAngle = THREE.MathUtils.clamp(libre, Math.PI * 0.495, Math.PI * 0.95);
}

const reloj = new THREE.Clock();
function bucle() {
  const dt = Math.min(0.05, reloj.getDelta());
  const t = reloj.elapsedTime;
  animarVuelo(dt);
  correrAnimaciones();
  animarActuadores(dt);
  animarAsistente(dt);
  if (G) { actualizarSensores(t); resaltarComponente(t); }
  limitarPolar();
  controles.update();
  ajustarPlanos();
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

async function iniciar() {
  if (EN_ARCHIVO && await simulacionCorriendo(URL_VIVO)) {
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
  // Vigia del portable: pasa solo a en vivo cuando la simulacion de este PC responde.
  if (EN_ARCHIVO) ui.vigilarSimulacion();
  ui.vigilarInternet();
  ui.pintarModo();
  construirCintaMonedas();
  construirCintaVasos();
  construirCanaleta();
  construirPista();
  construirCarro();
  construirMuelle();
  construirCajaControl();
  construirSensores();
  construirCables();
  ui.iniciarCables();
  for (const s of Object.values(SENS)) s.marcador.userData.baseX = s.marcador.scale.x, s.marcador.userData.baseY = s.marcador.scale.y;
  ajustarSombra();
  optimizar();

  // ?vista=pista, ?paso=3, ?sensor=cortina o ?componente=<id> en la URL abren directo ahi
  // (?panel=0 lo aplica la interfaz antes de ubicar la camara: la toma se corre si el panel tapa).
  const q = new URLSearchParams(location.search);
  if (ui.aplicarURL(q)) {
    // ya ubico la camara
  } else if (q.get('cam') && q.get('mira')) {
    // ?cam=x,y,z&mira=x,y,z en coordenadas de la simulacion (metros): una
    // toma exacta, para capturas del informe o revisar medidas.
    const num = (t) => t.split(',').map(Number);
    controles.target.copy(V(num(q.get('mira'))));
    camara.position.copy(V(num(q.get('cam'))));
    ui.pintarPanel();
  } else {
    vista(q.get('vista') || 'todo');
    vuelo.t = 0.999;
    ui.pintarPanel();
  }
  await consultar();
  // En vivo se pregunta 5 veces por segundo; la demo avanza un tick por
  // cada ciclo real de la cinta (avance + pausa, config tiempos_ms), igual
  // que el supervisor a velocidad 1.
  setInterval(consultar, MODO_DEMO ? (cuadrosDemo[0] && cuadrosDemo[0].ciclo_ms) || 1600 : 200);
}

// Revision de espacio (?auditar): expone la escena para que un script mida
// si alguna pieza atraviesa a otra. No cambia nada del visor.
if (new URLSearchParams(location.search).has('auditar')) window.__visor = { THREE, escena, COMP, SENS, P, CABLES, G: () => G, camara, controles, PIN, PINES_REALES, renderer, vista, vuelo: () => vuelo,
  // Rendimiento: renderer.info (llamadas de dibujo, triangulos, geometrias, texturas) y lo que unio optimizar().
  info: () => ({ calls: renderer.info.render.calls, triangulos: renderer.info.render.triangles, ...renderer.info.memory, programas: renderer.info.programs.length }),
  optimizacion: () => resumenOptimizacion, ETIQUETAS };

// La interfaz: le pasa lo que necesita de la escena (interfaz.js no toca Three.js).
const ui = crearInterfaz({
  enArchivo: EN_ARCHIVO, urlVivo: URL_VIVO, base: BASE,
  modoDemo: () => MODO_DEMO, G: () => G, estado: () => estado, pasos: () => PASOS,
  vista, saltarVuelo: () => { if (vuelo) vuelo.t = 0.999; },
  enfocarSensor, encuadrarComponente: (id) => encuadrar(COMP[id]),
  tiene3D: (id) => !!COMP[id], sensorEn3D: (id) => mallasDeSensor(id).length > 0,
  sensorActivo, sensorEnAlarma,
  mostrarCables3D: mostrarCables, datosCables: () => ({ cables: CABLES, tipos: TIPOS_CABLE }),
  alCambiarInternet: nubeSinInternet,
});

bucle();
iniciar();
