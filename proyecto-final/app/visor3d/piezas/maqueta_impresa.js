// Maqueta impresa (carpeta maqueta_impresa/ del proyecto): la estructura y las piezas de PLA tal como se
// imprimen, leidas de app/visor3d/maqueta_impresa.glb (lo genera `python maqueta_impresa/modelo_3d.py`
// desde los STL de cada pieza EN SU LUGAR del ensamble; medidas de los .scad de esa carpeta).
// El GLB ya viene en metros y en el marco de Three (sim (x, y, z) -> (x, z, -y)): cada pieza es una
// malla con su nombre (`alm_disco`, `t_F1-F4`...) y en `userData` las extras del GLB: grupo, y en las que
// se mueven `movil` (que objeto del visor siguen), `pivote`, `eje` y `recorrido` (marco sim, m y grados).
// Lector propio y minimo (sin GLTFLoader): el GLB lo escribe nuestro script con un formato fijo (una
// primitiva por malla: POSITION float32 + indices uint16/uint32, color por material).
import * as THREE from 'three';

const TIPOS = { 5123: Uint16Array, 5125: Uint32Array, 5126: Float32Array };

// base64 (como lo embebe visor-portable.html) -> ArrayBuffer
export function base64ABuffer(b64) {
  const bin = atob(b64);
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u.buffer;
}

// GLB -> { grupo, piezas: Map(nombre -> malla), extras (de la escena) }.
export function leerMaquetaGLB(buffer) {
  const dv = new DataView(buffer);
  if (dv.getUint32(0, true) !== 0x46546c67) throw new Error('maqueta_impresa.glb: no es un GLB');
  const largoJson = dv.getUint32(12, true);
  const gltf = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 20, largoJson)));
  const bin = 20 + largoJson + 8;                    // inicio del bloque BIN
  const leer = (i) => {
    const a = gltf.accessors[i], v = gltf.bufferViews[a.bufferView];
    const n = a.count * (a.type === 'VEC3' ? 3 : 1);
    return new TIPOS[a.componentType](buffer.slice(bin + v.byteOffset, bin + v.byteOffset + n * TIPOS[a.componentType].BYTES_PER_ELEMENT));
  };
  const grupo = new THREE.Group();
  grupo.name = 'maqueta_impresa';
  const piezas = new Map();
  for (const nodo of gltf.nodes) {
    const prim = gltf.meshes[nodo.mesh].primitives[0];
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(leer(prim.attributes.POSITION), 3));
    geo.setIndex(new THREE.BufferAttribute(leer(prim.indices), 1));
    geo.computeBoundingSphere();
    const pbr = gltf.materials[prim.material].pbrMetallicRoughness;
    const [r, g, b] = pbr.baseColorFactor;
    const blanco = r + g + b > 2.7;                  // caja de luz (difusor blanco): que se vea encendida
    // Un material por pieza (como mat() del visor): el resaltado cambia el emissive de cada una.
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(r, g, b), roughness: pbr.roughnessFactor, metalness: pbr.metallicFactor,
      flatShading: true, ...(blanco ? { emissive: 0xeaf2ff, emissiveIntensity: 0.45 } : {}),
    });
    const m = new THREE.Mesh(geo, material);
    m.name = nodo.name;
    m.castShadow = true;
    m.receiveShadow = true;
    Object.assign(m.userData, nodo.extras || {});
    grupo.add(m);
    piezas.set(nodo.name, m);
  }
  return { grupo, piezas, extras: gltf.scenes[0].extras || {} };
}
