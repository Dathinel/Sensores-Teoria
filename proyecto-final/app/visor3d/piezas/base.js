// Ayudantes comunes de las piezas del visor 3D (ver README.md de esta carpeta).
//
// Todas las piezas trabajan en METROS y en el marco de la SIMULACION, igual que visor.js:
// x a lo largo, y a lo ancho, z hacia arriba. Three.js tiene la Y hacia arriba, asi que
// `P(x, y, z)` convierte (x, y, z) de la simulacion a (x, z, -y) de Three. `caja` y
// `cilindro` reciben sus medidas en ese mismo marco. Si una medida viene en milimetros de
// una ficha tecnica, se multiplica por `MM`.

import * as THREE from 'three';

export const MM = 0.001;

// Los mismos colores que usa visor.js (objeto COLOR), para que las piezas no desentonen.
export const COLOR = {
  ambar: 0xf2b134, verde: 0x3fb68b, rojo: 0xe5534b, azul: 0x539bf5, morado: 0xb083f0,
  cian: 0x2a9fd6, bancada: 0x2b3a52, cinta: 0x0b0b0c, separador: 0xbfc3c8, naranja: 0xe8741c,
  oro: 0xd4a53a, plata: 0xc9ccd1, acero: 0x6f757e, piel: 0xe0ac8a, pista: 0xd8d3c6,
  aluminio: 0xa9b1bb, impreso: 0x39424f, servo: 0x2458b3, tapa: 0xf28c28,
  // Electronica
  pcb_negro: 0x16181c, pcb_azul: 0x1f4f8f, pcb_verde: 0x1d6b3a, estano: 0xd9d9d9,
  dorado: 0xd4af37, plastico_negro: 0x111111, chip: 0x1a1a1a, blanco: 0xf2f2f2,
};

// Presets de material (se pasan como `extra`).
export const METAL = { metalness: 0.85, roughness: 0.3 };
export const PLASTICO = { roughness: 0.7, metalness: 0.0 };

// Material estandar, igual que `mat` de visor.js. Crea uno NUEVO en cada llamada a proposito:
// el resaltado de componentes del visor cambia el `emissive` del material de cada malla, y un
// material compartido encenderia tambien las piezas vecinas. Para muchas copias de la misma
// forma (pines, tornillos) usar `instancias`, que comparte una sola geometria y un material.
export function mat(color, extra = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0.1, ...extra });
}

// Punto de la simulacion (x, y, z con z arriba) -> vector de Three (y arriba).
export const P = (x, y, z) => new THREE.Vector3(x, z, -y);

// Caja de sx (largo, x) × sy (ancho, y) × sz (alto, z), centrada en `pos` (un vector de
// Three, normalmente hecho con P). `color` puede ser un numero o un material ya hecho.
export function caja(sx, sy, sz, color, pos, extra) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(sx, sz, sy), color && color.isMaterial ? color : mat(color, extra));
  if (pos) m.position.copy(pos);
  m.castShadow = true;
  return m;
}

// Cilindro vertical (eje z de la simulacion) de `radio` y `alto`, centrado en `pos`.
// Para acostarlo: `m.rotation.x = Math.PI / 2` (eje a lo ancho, y) o
// `m.rotation.z = Math.PI / 2` (eje a lo largo, x).
export function cilindro(radio, alto, color, pos, extra, segmentos = 32) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(radio, radio, alto, segmentos),
    color && color.isMaterial ? color : mat(color, extra));
  if (pos) m.position.copy(pos);
  m.castShadow = true;
  return m;
}

// Punto de anclaje vacio: `pin_<MODULO>_<PIN>` para cables y `ancla_<nombre>` para soportes.
// El visor los busca por nombre (`grupo.getObjectByName(...)`) y lee su posicion en mundo.
export function ancla(nombre, pos, datos = {}) {
  const o = new THREE.Object3D();
  o.name = nombre;
  if (pos) o.position.copy(pos);
  Object.assign(o.userData, datos);
  return o;
}

// Muchas copias de una forma (pines, tornillos, huecos): UNA InstancedMesh.
// `posiciones` son vectores de Three. Sin sombra (son chicas y cuestan mucho).
export function instancias(geometria, material, posiciones, nombre = null) {
  const im = new THREE.InstancedMesh(geometria, material, posiciones.length);
  const m = new THREE.Matrix4();
  posiciones.forEach((p, i) => im.setMatrixAt(i, m.makeTranslation(p.x, p.y, p.z)));
  im.instanceMatrix.needsUpdate = true;
  im.castShadow = false;
  if (nombre) im.name = nombre;
  return im;
}

// Textura dibujada en un canvas y pegada en un plano horizontal (cara de arriba de una placa):
// serigrafia, etiquetas impresas, pantallas. `ancho` × `largo` en metros (x, y de la
// simulacion); `dibujar(ctx, X, Y, ppm)` recibe funciones que pasan milimetros locales
// (origen en el centro, y hacia arriba) a pixeles del canvas.
export function planoDibujado(largo, ancho, dibujar, { ppm = 16, fondo = null } = {}) {
  const Lmm = largo / MM, Wmm = ancho / MM;
  const k = Math.min(ppm, 2048 / Math.max(Lmm, Wmm));
  const c = document.createElement('canvas');
  c.width = Math.ceil(Lmm * k); c.height = Math.ceil(Wmm * k);
  const ctx = c.getContext('2d');
  if (fondo) { ctx.fillStyle = fondo; ctx.fillRect(0, 0, c.width, c.height); }
  dibujar(ctx, (x) => (x + Lmm / 2) * k, (y) => (Wmm / 2 - y) * k, k);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  // polygonOffset: el plano va pegado a la cara de la pieza (decimas de mm); se "adelanta" en el
  // z-buffer para que la tarjeta de video nunca lo mezcle con esa cara (parpadeo de lejos).
  const m = new THREE.Mesh(new THREE.PlaneGeometry(largo, ancho),
    new THREE.MeshBasicMaterial({ map: tex, transparent: !fondo, depthWrite: false,
      polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -2 }));
  m.rotation.x = -Math.PI / 2;
  return m;
}

// Marca todas las mallas de un grupo: sombras y datos para el visor (sensorId, idComponente).
export function terminar(grupo, { sombras = true, datos = {} } = {}) {
  grupo.traverse((o) => {
    if (!o.isMesh) return;
    if (sombras && !o.isInstancedMesh && !o.material.transparent) o.castShadow = true;
    Object.assign(o.userData, datos);
  });
  Object.assign(grupo.userData, datos);
  return grupo;
}
