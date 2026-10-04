// comparar_preview.mjs - Corre el nucleo ACO de preview.html con node y lo compara contra aco.py.
//
// Saca de preview.html el bloque entre "// === NUCLEO ACO INICIO ===" y "// === NUCLEO ACO FIN ==="
// (mas los laberintos embebidos), lo ejecuta, y compara con la referencia que genero Python
// (comparar_preview.py): mejor ruta, longitud, hormigas exitosas y descartadas de cada nodo en
// cada iteracion, la feromona completa de cada iteracion y el resumen final. Igualdad exacta.
//
// Uso: node comparar_preview.mjs <ref.json>   (lo llama comparar_preview.py)
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const aqui = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(aqui, '..', '..', 'preview.html'), 'utf8');
const ini = html.indexOf('// === NUCLEO ACO INICIO ===');
const fin = html.indexOf('// === NUCLEO ACO FIN ===');
const laberintos = html.slice(html.indexOf('const LABERINTOS'), ini);
const api = new Function(laberintos + html.slice(ini, fin) +
  '; return {LABERINTOS, cargarLaberinto, simularEnjambre, parametrosPorDefecto, crcLaberinto};')();

const ref = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const archivoAClave = { 'maze.json': 'almacen', 'laberintos/abierto.json': 'abierto' };
let fallos = 0;
for (const [clave, r] of Object.entries(ref)) {
  const [maze, semilla, caidasTxt, deposito] = clave.split('|');
  const caidas = JSON.parse(caidasTxt) || {};
  const lab = api.cargarLaberinto(api.LABERINTOS[archivoAClave[maze]]);
  const p = api.parametrosPorDefecto();
  p.semilla = Number(semilla);
  p.deposito = deposito;
  const js = api.simularEnjambre(lab, p, [1, 2, 3], caidas);
  const err = [];
  if (api.crcLaberinto(lab) !== r.crc) err.push('crc');
  r.historial.forEach((h, i) => {
    const hj = js.historial[i];
    for (const n of ['1', '2', '3']) {
      const [cam, L, ex, de] = h.por_nodo[n];
      const dj = hj.porNodo[n];
      const Lj = isFinite(dj.mejorLongitud) ? dj.mejorLongitud : null;
      if (JSON.stringify(cam) !== JSON.stringify(dj.mejorCamino) || L !== Lj ||
          ex !== dj.exitosas || de !== dj.descartadas) err.push(`it${h.it} nodo${n}`);
    }
    if (h.tau.length !== hj.tau.length || h.tau.some((t, e) => t !== hj.tau[e])) err.push(`tau it${h.it}`);
  });
  for (const n of ['1', '2', '3']) {
    if (r.tau_final[n].some((t, e) => t !== js.tauFinal[n][e])) err.push('tau_final nodo' + n);
  }
  if (JSON.stringify(r.codicioso) !== JSON.stringify(js.caminoCodicioso) || r.convergio !== js.convergio ||
      r.primera !== js.iteracionPrimerOptimo) err.push('resumen');
  console.log(`${err.length ? 'FALLA' : 'OK   '} ${maze.padEnd(24)} semilla ${semilla.padEnd(6)} caidas ${caidasTxt.padEnd(9)} deposito ${deposito.padEnd(5)} ${err.slice(0, 5).join(', ')}`);
  if (err.length) fallos++;
}
console.log(fallos ? `${fallos} casos con diferencias` : 'TODO IGUAL (bit a bit)');
process.exit(fallos ? 1 : 0);
