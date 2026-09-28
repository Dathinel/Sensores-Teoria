// Optimizacion de la escena del visor 3D: MENOS llamadas de dibujo, el MISMO detalle.
//
// No es una pieza: es el paso que visor.js corre una vez, al terminar de construir la escena y
// antes del primer cuadro en vivo. Vive en esta carpeta porque app/portable.py ya mete todos los
// `piezas/*.js` en el HTML de un solo archivo (y solo importa `three`, como las piezas).
//
// Por que hace falta (medido el 2026-09-28 con ?demo&auditar): la escena tenia 3.257 mallas y
// 2.629 materiales para solo 0,62 M triangulos. La tarjeta de video dibuja 0,6 M triangulos sin
// esfuerzo; lo que cuesta es que cada malla es una "llamada de dibujo" (draw call) aparte, con su
// cambio de material, y la pasada de sombras las vuelve a dibujar: ~3.000 llamadas por cuadro en
// la vista general. Unir en UNA malla todas las piezas quietas que se ven igual (mismo material)
// deja los mismos triangulos en muchas menos llamadas.
//
// Que se une y que no:
// - Se unen las mallas QUIETAS, dentro de su "ancla" (el grupo mas cercano que se mueve o se
//   oculta; si no hay ninguno, la escena). La malla unida queda como hija de esa ancla, en su
//   mismo marco: si el ancla se mueve (el carro, el carrusel, la paleta del empujador), la malla
//   unida se mueve con ella.
// - Un grupo por (ancla, componentes, aspecto del material, datos del visor): el resaltado de un
//   componente (visor.js cambia el `emissive` del material de sus mallas) sigue encendiendo solo
//   ese componente, porque cada combinacion de componentes tiene su propio material. Y el clic en
//   un sensor sigue funcionando: `userData.sensorId` va en la malla unida.
// - NO se tocan: lo que el visor anima o cambia en vivo (todo lo que se alcanza desde las
//   referencias que se le pasan -P, SENS, CINTAS...- y desde el `userData` de cada nodo, mas los
//   nombres que se buscan en vivo con getObjectByName), las mallas ocultas, las transparentes
//   (necesitan ordenarse una por una), los sprites (etiquetas), las lineas y cables, las
//   InstancedMesh (ya son una sola llamada) y las mallas con hijos.

import * as THREE from 'three';

// Propiedades que definen el aspecto de un material: dos materiales con los mismos valores se ven
// igual y pueden compartirse.
const PROPS_MATERIAL = ['type', 'color', 'emissive', 'emissiveIntensity', 'roughness', 'metalness', 'map', 'emissiveMap',
  'alphaMap', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'envMap', 'side', 'transparent', 'opacity', 'depthWrite',
  'depthTest', 'flatShading', 'vertexColors', 'wireframe', 'polygonOffset', 'polygonOffsetFactor', 'polygonOffsetUnits',
  'toneMapped', 'fog', 'alphaTest', 'visible', 'blending', 'shininess', 'specular', 'clearcoat', 'clearcoatRoughness',
  'sheen', 'transmission', 'ior', 'reflectivity', 'envMapIntensity', 'normalScale', 'colorWrite'];

function firmaMaterial(m, sinColor = false, sinRugMet = false) {
  if (m.onBeforeCompile && m.onBeforeCompile.toString() !== THREE.Material.prototype.onBeforeCompile.toString()) return null;
  const partes = [];
  for (const k of PROPS_MATERIAL) {
    if (sinColor && k === 'color') continue;
    if (sinRugMet && (k === 'roughness' || k === 'metalness')) continue;
    const v = m[k];
    if (v === undefined) continue;
    if (v && v.isColor) partes.push(k + ':' + v.getHexString());
    else if (v && v.isTexture) partes.push(k + ':' + v.uuid);
    else if (v && v.isVector2) partes.push(k + ':' + v.x + ',' + v.y);
    else if (v === null || typeof v !== 'object') partes.push(k + ':' + v);
  }
  return partes.join('|');
}

// Atributos de la geometria (nombre:tamaño). Solo geometrias simples: sin morph ni instancias.
function firmaGeometria(g) {
  if (!g || !g.isBufferGeometry || !g.attributes.position) return null;
  if (Object.keys(g.morphAttributes).length) return null;
  const nombres = Object.keys(g.attributes).sort();
  for (const n of nombres) if (g.attributes[n].isInstancedBufferAttribute) return null;
  return nombres.map((n) => n + ':' + g.attributes[n].itemSize).join(',');
}

// userData de una malla: solo valores simples (sensorId, idComponente, parte...). Una malla con
// funciones u objetos en su userData guarda algo que el visor usa en vivo: no se une.
function firmaDatos(ud) {
  const partes = [];
  for (const k of Object.keys(ud).sort()) {
    const v = ud[k];
    if (v !== null && (typeof v === 'object' || typeof v === 'function')) return null;
    partes.push(k + '=' + v);
  }
  return partes.join('&');
}

// Recorre referencias (objetos, listas, Map, Set) y junta los Object3D y materiales alcanzables.
function juntarReferencias(valor, objetos, materiales, visto, ignorar, prof = 0) {
  if (!valor || typeof valor !== 'object' || prof > 8 || visto.has(valor)) return;
  visto.add(valor);
  if (valor.isObject3D) {
    // (Su material no se marca: la malla misma no se une, y las unidas usan copias del material,
    // asi que lo que el visor le cambie a esta no se "contagia".)
    objetos.add(valor);
    for (const [k, v] of Object.entries(valor.userData || {})) if (!ignorar.has(k)) juntarReferencias(v, objetos, materiales, visto, ignorar, prof + 1);
    return;
  }
  if (valor.isMaterial) { materiales.add(valor); return; }
  if (valor.isTexture || valor.isBufferGeometry || ArrayBuffer.isView(valor)) return;
  if (valor.isVector3 || valor.isVector2 || valor.isQuaternion || valor.isEuler || valor.isColor || valor.isMatrix4) return;
  const hijos = valor instanceof Map ? [...valor.values()] : valor instanceof Set ? [...valor] : Array.isArray(valor) ? valor
    : Object.entries(valor).filter(([k]) => !ignorar.has(k)).map(([, v]) => v);
  for (const v of hijos) juntarReferencias(v, objetos, materiales, visto, ignorar, prof + 1);
}

// Une las partes (geometria + matriz al marco del ancla) en una BufferGeometry indexada.
// Con `conColor`, cada parte lleva su color (el de su material) como atributo `color` por
// vertice: piezas del mismo material que solo cambian de color quedan en UNA malla.
function unirGeometrias(partes, firma, conColor, conRugMet) {
  const nombres = firma.split(',').map((s) => s.split(':')[0]);
  let totalV = 0, totalI = 0;
  for (const { geo } of partes) {
    totalV += geo.attributes.position.count;
    totalI += geo.index ? geo.index.count : geo.attributes.position.count;
  }
  const salida = {};
  for (const n of nombres) salida[n] = new Float32Array(totalV * partes[0].geo.attributes[n].itemSize);
  const colores = conColor ? new Float32Array(totalV * 3) : null;
  const rugMet = conRugMet ? new Float32Array(totalV * 2) : null;
  const indices = totalV > 65535 ? new Uint32Array(totalI) : new Uint16Array(totalI);
  const v = new THREE.Vector3(), normal = new THREE.Matrix3();
  let baseV = 0, baseI = 0;
  for (const { geo, matriz, color, rugosidad, metal } of partes) {
    const n = geo.attributes.position.count;
    if (rugMet) for (let i = 0; i < n; i++) { rugMet[(baseV + i) * 2] = rugosidad; rugMet[(baseV + i) * 2 + 1] = metal; }
    if (colores) for (let i = 0; i < n; i++) { colores[(baseV + i) * 3] = color.r; colores[(baseV + i) * 3 + 1] = color.g; colores[(baseV + i) * 3 + 2] = color.b; }
    normal.getNormalMatrix(matriz);
    const espejo = matriz.determinant() < 0;   // escala negativa: se invierte el orden de los triangulos
    for (const nombre of nombres) {
      const a = geo.attributes[nombre], t = a.itemSize, dst = salida[nombre];
      for (let i = 0; i < n; i++) {
        if (nombre === 'position') {
          v.fromBufferAttribute(a, i).applyMatrix4(matriz);
          dst[(baseV + i) * 3] = v.x; dst[(baseV + i) * 3 + 1] = v.y; dst[(baseV + i) * 3 + 2] = v.z;
        } else if (nombre === 'normal') {
          v.fromBufferAttribute(a, i).applyMatrix3(normal).normalize();
          dst[(baseV + i) * 3] = v.x; dst[(baseV + i) * 3 + 1] = v.y; dst[(baseV + i) * 3 + 2] = v.z;
        } else {
          const o = (baseV + i) * t;
          dst[o] = a.getX(i);
          if (t > 1) dst[o + 1] = a.getY(i);
          if (t > 2) dst[o + 2] = a.getZ(i);
          if (t > 3) dst[o + 3] = a.getW(i);
        }
      }
    }
    const idx = geo.index;
    const ni = idx ? idx.count : n;
    for (let i = 0; i < ni; i += 3) {
      const a = idx ? idx.getX(i) : i, b = idx ? idx.getX(i + 1) : i + 1, c = idx ? idx.getX(i + 2) : i + 2;
      indices[baseI + i] = baseV + a;
      indices[baseI + i + 1] = baseV + (espejo ? c : b);
      indices[baseI + i + 2] = baseV + (espejo ? b : c);
    }
    baseV += n; baseI += ni;
  }
  const g = new THREE.BufferGeometry();
  for (const n of nombres) g.setAttribute(n, new THREE.BufferAttribute(salida[n], partes[0].geo.attributes[n].itemSize));
  if (colores) g.setAttribute('color', new THREE.BufferAttribute(colores, 3));
  if (rugMet) g.setAttribute('rugosidadMetal', new THREE.BufferAttribute(rugMet, 2));
  g.setIndex(new THREE.BufferAttribute(indices, 1));
  g.computeBoundingBox();
  g.computeBoundingSphere();
  return g;
}

// Rugosidad y metal POR VERTICE (atributo `rugosidadMetal`) en un MeshStandardMaterial: el
// sombreado es el mismo de three (solo cambia de donde sale el numero), y piezas que solo se
// diferencian en lo brillantes o metalicas que son quedan en una sola malla.
function usarRugMetPorVertice(m) {
  m.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec2 rugosidadMetal;\nvarying vec2 vRugMet;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvRugMet = rugosidadMetal;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vRugMet;')
      .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = vRugMet.x;')
      .replace('#include <metalnessmap_fragment>', 'float metalnessFactor = vRugMet.y;');
  };
  m.customProgramCacheKey = () => 'rugosidadMetal';
}

/**
 * Une las mallas quietas de `escena` (ver el comentario de arriba).
 * @param escena        la THREE.Scene ya construida
 * @param renderer      el WebGLRenderer (para encender las mallas "solo sombra" en su pasada)
 * @param comp          COMP de visor.js: id de componente -> lista de objetos (se actualiza aqui)
 * @param referencias   lo que el visor mueve o cambia en vivo (P, SENS, CINTAS, CABLES...)
 * @param nombresVivos  nombres que se buscan con getObjectByName mientras corre
 * @param ignorarDatos  claves (de userData o de las referencias) con listas que solo se usan al construir
 * @param auditar       guarda como estaba cada malla unida (resumen.revisarOriginales())
 * @returns resumen con cuantas mallas habia, cuantas quedaron y cuantas se unieron
 */
export function optimizarEscena(escena, { renderer = null, comp = {}, referencias = [], nombresVivos = [], ignorarDatos = [], auditar = false } = {}) {
  const t0 = performance.now();
  escena.updateMatrixWorld(true);
  const ignorar = new Set(ignorarDatos);
  const vivos = new Set(), matVivos = new Set(), visto = new Set();
  for (const r of referencias) juntarReferencias(r, vivos, matVivos, visto, ignorar);
  const nombres = new Set(nombresVivos);
  escena.traverse((o) => {
    if (o === escena) return;
    if (nombres.has(o.name) || !o.visible) vivos.add(o);
    for (const [k, v] of Object.entries(o.userData)) if (!ignorar.has(k)) juntarReferencias(v, vivos, matVivos, visto, ignorar);
  });

  // Componentes de cada malla (una malla puede estar en varios: se respeta tal cual).
  const compDe = new Map();
  for (const [id, lista] of Object.entries(comp)) for (const o of lista) o.traverse((m) => {
    if (!m.isMesh) return;
    if (!compDe.has(m)) compDe.set(m, new Set());
    compDe.get(m).add(id);
  });

  const grupos = new Map();
  let mallas = 0;
  escena.traverse((m) => {
    if (!m.isMesh) return;
    mallas++;
    if (m.isSkinnedMesh || vivos.has(m) || m.children.length || Array.isArray(m.material)) return;
    const mt = m.material;
    if (!mt || matVivos.has(mt)) return;
    const fg = firmaGeometria(m.geometry), fd = firmaDatos(m.userData);
    // Color por vertice: si el material no usa ya colores por vertice, su color pasa a la
    // geometria y el material compartido queda blanco (mismo resultado en pantalla).
    // (Las transparentes solo se unen con otras de material IDENTICO: mismo color y opacidad.)
    const conColor = !mt.transparent && !mt.vertexColors && !m.geometry.attributes.color && mt.color && mt.color.isColor;
    const conRugMet = conColor && mt.type === 'MeshStandardMaterial' && !mt.roughnessMap && !mt.metalnessMap;
    const fm = firmaMaterial(mt, conColor, conRugMet);
    if (fm === null || fg === null || fd === null) return;
    if (m.isInstancedMesh && (!conColor || m.count < 1)) return;
    // Ancla: el antecesor mas cercano que se mueve, se oculta o se busca por nombre en vivo.
    let ancla = m.parent;
    while (ancla && ancla !== escena && !vivos.has(ancla)) ancla = ancla.parent;
    if (!ancla) return;
    const comps = [...(compDe.get(m) || [])].sort().join(',');
    const clave = [ancla.uuid, comps, fm, fg, fd, conColor, conRugMet, m.renderOrder, m.frustumCulled, m.layers.mask].join('#');
    if (!grupos.has(clave)) grupos.set(clave, { ancla, comps, fm, fg, conColor, conRugMet, lista: [] });
    grupos.get(clave).lista.push(m);
  });

  // Un material por (aspecto, componentes): el resaltado enciende solo ese componente.
  const materiales = new Map();
  const unidas = new Set();
  const inversa = new THREE.Matrix4(), mi = new THREE.Matrix4(), ci = new THREE.Color();
  let nuevas = 0;
  const sombras = new Map();
  for (const g of grupos.values()) {
    // Una sola malla comun (sin instancias ni cambio de color): se queda como esta.
    if (g.lista.length < 2 && !g.lista[0].isInstancedMesh && !g.conColor) continue;
    const claveMat = g.fm + '#' + g.comps + '#' + g.conColor + '#' + g.conRugMet;
    if (!materiales.has(claveMat)) {
      const m = g.lista[0].material.clone();
      if (g.conColor) { m.vertexColors = true; m.color.setRGB(1, 1, 1); }
      if (g.conRugMet) usarRugMetPorVertice(m);
      materiales.set(claveMat, m);
    }
    const material = materiales.get(claveMat);
    inversa.copy(g.ancla.matrixWorld).invert();
    const partes = [];
    for (const m of g.lista) {
      const base = new THREE.Matrix4().multiplyMatrices(inversa, m.matrixWorld);
      const color = m.material.color ? m.material.color.clone() : null;
      const rugosidad = m.material.roughness, metal = m.material.metalness;
      if (m.isInstancedMesh) {
        // Cada copia de la InstancedMesh pasa a ser una parte mas (con su matriz y su color).
        for (let i = 0; i < m.count; i++) {
          m.getMatrixAt(i, mi);
          const c = color.clone();
          if (m.instanceColor) { m.getColorAt(i, ci); c.multiply(ci); }
          partes.push({ geo: m.geometry, matriz: base.clone().multiply(mi), color: c, rugosidad, metal, sombra: m.castShadow });
        }
      } else partes.push({ geo: m.geometry, matriz: base, color, rugosidad, metal, sombra: m.castShadow });
    }
    const malla = new THREE.Mesh(unirGeometrias(partes, g.fg, g.conColor, g.conRugMet), material);
    malla.name = 'unida';
    // Opacas: la sombra la proyecta la malla "solo sombra" de su ancla (abajo), con SOLO las
    // partes que proyectaban sombra antes. Transparentes: como estaban.
    const transparente = material.transparent;
    malla.castShadow = transparente && g.lista.some((m) => m.castShadow);
    if (!transparente) {
      const lado = material.shadowSide ?? material.side;
      const clave = g.ancla.uuid + '#' + lado;
      if (!sombras.has(clave)) sombras.set(clave, { ancla: g.ancla, lado, partes: [] });
      sombras.get(clave).partes.push(...partes.filter((q) => q.sombra));
    }
    malla.receiveShadow = g.lista.some((m) => m.receiveShadow);
    malla.renderOrder = g.lista[0].renderOrder;
    malla.frustumCulled = g.lista[0].frustumCulled;
    malla.layers.mask = g.lista[0].layers.mask;
    Object.assign(malla.userData, g.lista[0].userData, { unidas: partes.length });
    malla.matrixAutoUpdate = false;
    // Al principio de los hijos: el visor quita "el ultimo hijo" de algunas pilas.
    g.ancla.add(malla);
    g.ancla.children.unshift(g.ancla.children.pop());
    malla.updateMatrixWorld(true);
    for (const m of g.lista) {
      if (auditar) { const r = []; for (let p = m; p; p = p.parent) if (p.name) r.push(p.name); m.userData.rutaOriginal = r.join('<'); }
      m.parent.remove(m);
      unidas.add(m);
    }
    nuevas++;
    if (g.comps) for (const id of g.comps.split(',')) comp[id].push(malla);
  }
  // Sombras: la pasada de sombras vuelve a dibujar cada malla que proyecta sombra. Para ella no
  // importa el material (solo la forma y de que lado se ve la cara), asi que por cada ancla va
  // UNA malla "solo sombra" con la forma de todas las partes (de las mallas unidas) que
  // proyectaban sombra. Su material esta apagado (`visible = false`: la pasada normal ni la mira y
  // el clic tampoco) y se enciende SOLO mientras three dibuja el mapa de sombras (se envuelve
  // `renderer.shadowMap.render`, que corre despues de armar la lista de la pasada normal). Las
  // mallas unidas reciben sombra igual que antes.
  const matSombra = {};
  let mallasSombra = 0;
  for (const s of sombras.values()) {
    if (!s.partes.length) continue;
    const geo = unirGeometrias(s.partes, 'position:3', false, false);
    matSombra[s.lado] ||= new THREE.MeshBasicMaterial({ side: s.lado, visible: false });
    const sombra = new THREE.Mesh(geo, matSombra[s.lado]);
    sombra.name = 'solo_sombra';
    sombra.userData.soloSombra = true;
    sombra.castShadow = true;
    sombra.matrixAutoUpdate = false;
    s.ancla.add(sombra);
    s.ancla.children.unshift(s.ancla.children.pop());
    sombra.updateMatrixWorld(true);
    mallasSombra++;
  }

  if (renderer && Object.keys(matSombra).length) {
    const mats = Object.values(matSombra);
    const mapa = renderer.shadowMap, dibujar = mapa.render;
    mapa.render = function (...args) {
      for (const m of mats) m.visible = true;
      try { return dibujar.apply(this, args); } finally { for (const m of mats) m.visible = false; }
    };
  }

  // Los componentes ya no apuntan a las mallas que se unieron (estan fuera de la escena).
  for (const id of Object.keys(comp)) comp[id] = comp[id].filter((o) => !unidas.has(o));

  let despues = 0;
  escena.traverse((m) => { if (m.isMesh) despues++; });
  const resumen = { antes: mallas, despues, unidas: unidas.size, mallasNuevas: nuevas, mallasSombra, materiales: materiales.size, ms: Math.round(performance.now() - t0) };
  // Revision (?auditar): si despues algo del visor mueve, oculta o recolorea una malla que se
  // unio (ya fuera de la escena), `revisarOriginales()` lo encuentra: esa malla no debio unirse.
  if (auditar) {
    const foto = (m) => [m.position.toArray(), m.quaternion.toArray(), m.scale.toArray(), m.visible,
      m.material.color ? m.material.color.getHex() : null, m.material.emissive ? m.material.emissive.getHex() : null,
      m.material.opacity, m.material.visible].map((x) => JSON.stringify(x)).join('|');
    const fotos = new Map([...unidas].map((m) => [m, foto(m)]));
    resumen.revisarOriginales = () => [...fotos].filter(([m, f]) => foto(m) !== f)
      .map(([m]) => (m.userData.rutaOriginal || m.geometry.type) + ' ' + (m.userData.sensorId || ''));
  }
  return resumen;
}
