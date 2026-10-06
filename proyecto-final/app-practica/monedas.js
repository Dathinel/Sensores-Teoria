// App del proyecto final, organizada como Docker Desktop: barra lateral con las vistas, la lista de
// programas con su estado (y el detalle al lado) y la prueba visual: el recorrido animado de una pieza
// JUNTO al estado real de la simulación (GET /api/estado del visor, el mismo que usa el visor 3D).
// Usa la API común (window.App, /comun/app.js). Los datos del recorrido salen del README
// ("El recorrido de una moneda") y de control/reglas.py (las causas de rechazo).

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const guardar = (k, v) => { try { localStorage.setItem('pf-' + k, v); } catch (e) { /* sin almacenamiento */ } };
const leer = (k) => { try { return localStorage.getItem('pf-' + k); } catch (e) { return null; } };
const escapar = (t) => String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// ---------------------------------------------------------------------------
// Vistas (barra lateral)
// ---------------------------------------------------------------------------

const vistas = { actual: 'inicio', alCambiar: [] };
function irA(nombre) {
  if (!document.querySelector(`.pf-vista[data-vista="${nombre}"]`)) nombre = 'inicio';
  vistas.actual = nombre;
  $$('.pf-vista').forEach((v) => v.classList.toggle('activa', v.dataset.vista === nombre));
  $$('.pf-nav').forEach((b) => b.classList.toggle('activa', b.dataset.vista === nombre));
  $('#principal').scrollTop = 0;
  guardar('vista', nombre);
  if (location.hash !== '#' + nombre) history.replaceState(null, '', '#' + nombre);
  vistas.alCambiar.forEach((f) => f(nombre));
}

// ---------------------------------------------------------------------------
// Recorrido de una pieza por las 4 estaciones (animación)
// ---------------------------------------------------------------------------

const ESTACIONES = [
  { titulo: 'Carga', texto: 'La pieza se pone a mano en la casilla de carga, durante una pausa de la cinta. La cinta solo avanza si lleva algo registrado o si el infrarrojo de la carga vio algo: vacía, espera quieta.' },
  { titulo: 'E1 · presencia (infrarrojo FC-51)', texto: 'Mira hacia abajo. La cinta negra mate casi no refleja, así que solo "ve" algo si hay una pieza. Ocupada: crea el registro de la casilla, con un número propio que la acompaña todo el camino.' },
  { titulo: 'E2 · material (capacitivo + inductivo)', texto: 'Dos sensores DEBAJO de la cinta, mirando a través de la banda: el capacitivo ve cualquier objeto y el inductivo M18 solo ve metal. Capacitivo sí e inductivo no: no es metal.' },
  { titulo: 'E3 · cámara cenital', texto: 'La casilla queda quieta bajo la cámara, con anillo de luz difusa y la cinta negra de fondo. Dos fotos: diámetro en milímetros, circularidad, agujeros y qué moneda es. Si las dos fotos no están de acuerdo, rechaza.' },
  { titulo: 'E4 · descarga (compuerta de desvío)', texto: 'La pieza cae a un embudo. La compuerta en reposo apunta al RECHAZO: solo se mueve hacia el almacén para una moneda registrada y aceptada.' },
];

// en: índice de la estación que la rechaza (null = aceptada). causa: la de control/reglas.py.
const PIEZAS = {
  moneda: { clase: 'moneda', etiqueta: '$500', nombre: 'moneda de $500', en: null,
    vistas: ['', 'La ve: casilla ocupada, registro creado.', 'Capacitivo sí, inductivo sí: es metal. Sigue a la cámara.',
      'Diámetro 23,7 mm, redonda, sin agujeros, cara de $500 en las dos fotos: ACEPTADA.', 'Moneda aceptada: la compuerta gira hacia el almacén.'] },
  boton: { clase: 'boton', etiqueta: '', nombre: 'botón de plástico', en: 2, causa: 'no_metalico',
    vistas: ['', 'La ve: casilla ocupada, registro creado.', 'Capacitivo sí, inductivo NO: no es metal. Rechazo sin gastar la cámara.'] },
  arandela: { clase: 'arandela', etiqueta: '', nombre: 'arandela', en: 3, causa: 'perforado',
    vistas: ['', 'La ve: casilla ocupada, registro creado.', 'Capacitivo sí, inductivo sí: es metal. Sigue a la cámara.',
      'Encuentra un contorno interno cerrado: tiene un agujero. Ninguna moneda colombiana lo tiene.'] },
  bloque: { clase: 'bloque', etiqueta: '', nombre: 'bloque metálico', en: 3, causa: 'no_circular',
    vistas: ['', 'La ve: casilla ocupada, registro creado.', 'Capacitivo sí, inductivo sí: es metal. Sigue a la cámara.',
      'La circularidad del contorno es baja: no es redondo.'] },
  euro: { clase: 'euro', etiqueta: '1€', nombre: 'moneda de 1 euro', en: 3, causa: 'no_reconocida',
    vistas: ['', 'La ve: casilla ocupada, registro creado.', 'Capacitivo sí, inductivo sí: es metal. Sigue a la cámara.',
      'Redonda, del tamaño de una moneda, pero la cara no es de ninguna moneda colombiana con confianza suficiente (85 %).'] },
};
const CICLO_MS = 1600;   // el ciclo real de la cinta: 600 ms avanzando + 1000 ms de pausa

function recorrido() {
  const cinta = $('#cinta');
  const ficha = $('#ficha');
  const explica = $('#explica');
  const casillas = [...cinta.querySelectorAll('.m-casilla')];
  const destino = $('#destino');
  const destinoSub = $('#destinoSub');
  const barra = $('#cicloBarra');
  const relojTxt = $('#cicloTxt');
  const bTodo = $('#todo');
  let pieza = PIEZAS.moneda;
  let pos = 0;
  let auto = null;
  let anim = null;

  const centro = (i) => casillas[i].offsetLeft + casillas[i].offsetWidth / 2;
  const mover = () => { ficha.style.left = centro(pos) + 'px'; };
  const parar = () => { clearInterval(auto); auto = null; cancelAnimationFrame(anim); barra.style.width = '0%'; bTodo.textContent = '▶ Reproducir el recorrido'; };

  // Barra del ciclo real: 600 ms "avanzando" y 1000 ms "pausa: la estación mira y decide".
  function relojCiclo() {
    const t0 = performance.now();
    const paso = (t) => {
      const dt = Math.min(CICLO_MS, t - t0);
      barra.style.width = (dt / CICLO_MS * 100) + '%';
      relojTxt.textContent = dt < 600 ? 'La cinta avanza una casilla (40 mm en 600 ms)…' : 'Pausa de 1 s: la estación mira y decide';
      if (dt < CICLO_MS && auto) anim = requestAnimationFrame(paso);
    };
    anim = requestAnimationFrame(paso);
  }

  function poner(nombre) {
    parar();
    pieza = PIEZAS[nombre] || PIEZAS.moneda;
    pos = 0;
    ficha.className = 'm-ficha ' + pieza.clase;
    ficha.textContent = pieza.etiqueta;
    casillas.forEach((c) => c.classList.remove('mirando', 'paso-ok', 'paso-no', 'almacen', 'rechazo'));
    destino.textContent = 'Destino'; destinoSub.textContent = 'almacén o rechazo';
    casillas[0].classList.add('mirando');
    relojTxt.textContent = 'Ciclo real: 600 ms avanzando + 1000 ms de pausa';
    mover();
    pintar();
  }

  function pintar() {
    const e = ESTACIONES[pos];
    let html = '';
    if (pos <= 4) {
      html = `<h3>${e.titulo}</h3><p>${e.texto}</p>`;
      const rechazada = pieza.en !== null && pos > pieza.en;
      if (pos > 0 && pos < 4 && rechazada) {
        html += `<p>Esta casilla ya va marcada como rechazo (<span class="causa">${pieza.causa}</span>): la estación ni siquiera la mira.</p>`;
      } else if (pos === 4 && pieza.en !== null) {
        html += '<p>Pieza marcada como rechazo: la compuerta se queda apuntando a la <b>bandeja de rechazo</b>.</p>';
      } else if (pieza.vistas[pos]) {
        const esRechazo = pieza.en === pos;
        html += `<p class="${esRechazo ? '' : 'bien'}"><b>Con la ${pieza.nombre}:</b> ${pieza.vistas[pos]}`
          + (esRechazo ? ` Causa: <span class="causa">${pieza.causa}</span>.` : '') + '</p>';
      }
    } else if (pieza.en === null) {
      html = '<h3>Almacén · tubo de $500</h3><p class="bien">El carrusel ya tiene el tubo de su denominación bajo el punto de carga: '
        + 'la moneda cae casi vertical. Si el tubo estuviera lleno, la moneda esperaría en la descarga y la cinta se detendría: '
        + '<b>ninguna moneda colombiana aceptada se bota</b>. Con 10 del mismo valor se llena un vaso.</p>';
    } else {
      html = '<h3>Bandeja de rechazo</h3><p>Una sola bandeja para todo lo rechazado. El dashboard cuenta esta pieza en la causa '
        + `<span class="causa">${pieza.causa}</span> (decidida en ${ESTACIONES[pieza.en].titulo.split(' ·')[0]}).</p>`;
    }
    explica.innerHTML = html;
  }

  function avanzar() {
    if (pos >= 5) { parar(); return false; }
    casillas[pos].classList.remove('mirando');
    if (pos > 0 && pos < 5) casillas[pos].classList.add(pieza.en === pos ? 'paso-no' : 'paso-ok');
    pos += 1;
    mover();
    if (pos === 5) {
      const ok = pieza.en === null;
      casillas[5].classList.add(ok ? 'almacen' : 'rechazo');
      destino.textContent = ok ? 'Almacén' : 'Rechazo';
      destinoSub.textContent = ok ? 'tubo de $500' : pieza.causa;
    } else {
      casillas[pos].classList.add('mirando');
      // la estación "mira" al terminar el avance (600 ms)
      setTimeout(() => { ficha.classList.remove('mira'); void ficha.offsetWidth; ficha.classList.add('mira'); }, 600);
    }
    pintar();
    return pos < 5;
  }

  const nombreActual = () => Object.keys(PIEZAS).find((k) => PIEZAS[k] === pieza);
  $$('.m-pieza').forEach((b) => b.addEventListener('click', () => {
    $$('.m-pieza').forEach((x) => x.classList.toggle('activa', x === b));
    poner(b.dataset.pieza);
  }));
  $('#avanzar').addEventListener('click', () => { parar(); avanzar(); });
  $('#reiniciar').addEventListener('click', () => poner(nombreActual()));
  bTodo.addEventListener('click', () => {
    if (auto) { parar(); return; }
    if (pos >= 5) poner(nombreActual());
    bTodo.textContent = '❚❚ Pausar';
    const tic = () => { if (!avanzar()) { parar(); return; } relojCiclo(); };
    auto = setInterval(tic, CICLO_MS);
    tic();
  });
  window.addEventListener('resize', mover);
  vistas.alCambiar.push((v) => { if (v === 'prueba') requestAnimationFrame(mover); else parar(); });
  poner('moneda');
}

// ---------------------------------------------------------------------------
// Estado REAL de la simulación (lo mismo que lee el visor 3D)
// ---------------------------------------------------------------------------

const CAUSAS = {
  no_metalico: 'no metálico', fuera_de_rango: 'diámetro fuera', no_circular: 'no circular', perforado: 'perforado',
  no_reconocida: 'no reconocida', incoherente: 'incoherente', vacia: 'vacía',
};
const vivo = { puerto: null, candidatos: new Set([8765, 8766, 8767, 8768]), ultimo: null, fallos: 0 };

function fichaDe(c) {
  if (!c) return { clase: 'vacia', txt: '' };
  const t = String(c.tipo || ''), real = String(c.clase_real || '');
  if (t === 'vacia_registrada') return { clase: 'vacia', txt: '' };
  if (t.startsWith('boton_metal')) return { clase: 'boton-metal', txt: '' };
  if (t.startsWith('boton')) return { clase: 'boton', txt: '' };
  if (t.includes('bloque')) return { clase: 'bloque', txt: '' };
  if (t.includes('arandela') || c.contornos_internos > 0) return { clase: 'arandela', txt: '' };
  const m = real.match(/^(\d+)_/);
  if (t === 'moneda' && m) return { clase: 'moneda', txt: '$' + m[1] };
  return { clase: 'euro', txt: real.slice(0, 4) };
}

function barras(el, datos, max) {
  const filas = Object.entries(datos);
  if (!filas.length) { el.innerHTML = '<p class="app-tenue pf-chico">nada todavía</p>'; return; }
  const tope = max || Math.max(1, ...filas.map(([, v]) => v));
  el.innerHTML = filas.map(([k, v]) => `<div class="pf-fila"><span title="${escapar(k)}">${escapar(k)}</span>`
    + `<i style="width:${Math.max(1, v / tope * 100)}%"></i><span>${v}</span></div>`).join('');
}

function pintarReal(e) {
  const NOMBRES = ['E1 presencia', 'E2 material', 'E3 cámara', 'E4 descarga'];
  const cas = (e.casillas_monedas || []).slice(0, 4);
  while (cas.length < 4) cas.push(null);
  $('#realCinta').innerHTML = cas.map((c, i) => {
    const f = fichaDe(c);
    let est = 'vacía', cls = '';
    if (c && c.tipo !== 'vacia_registrada') {
      if (c.causa) { est = 'rechazo: ' + (CAUSAS[c.causa] || c.causa); cls = 'no'; }
      else if (c.aceptada) { est = 'aceptada'; cls = 'si'; }
      else est = c.metal === false ? 'no es metal' : 'en revisión';
    }
    const nombre = c && c.clase_real ? c.clase_real.replace(/_/g, ' ') : (c ? c.tipo || '' : '');
    return `<div class="pf-real-casilla ${cls}"><b>${NOMBRES[i]}</b><div class="m-ficha ${f.clase}">${escapar(f.txt)}</div>`
      + `<small>${escapar(nombre)}</small><small>${escapar(est)}</small></div>`;
  }).join('');

  const linea = e.terminado ? 'terminó la corrida' : (e.linea || '?');
  $('#realLinea').innerHTML = `Línea: <b>${escapar(linea)}</b> · tick ${e.tick ?? '?'} · escenario <code>${escapar(e.escenario || '?')}</code>`
    + (e.pendientes ? ` · faltan ${e.pendientes} piezas` : '')
    + ((e.alarmas || []).length ? ` · <span class="causa">${e.alarmas.length} alarma(s)</span>` : '');

  const alm = {};
  for (const [k, v] of Object.entries(e.almacen || {})) if (v || k !== 'otras') alm[k === 'otras' ? 'otras' : '$' + k] = v;
  barras($('#realAlmacen'), alm, e.capacidad_tubo);
  const rech = {};
  for (const r of ((e.salidas || {}).rechazo || [])) { const k = CAUSAS[r.causa] || r.causa; rech[k] = (rech[k] || 0) + 1; }
  barras($('#realRechazos'), rech);

  const carro = e.carro || {};
  $('#realCarro').innerHTML = `Carro: <b>${escapar((carro.estado || '?').replace(/_/g, ' '))}</b> (fase ${escapar(carro.fase || '?')}`
    + `${carro.vaso ? ', lleva un vaso' : ''})`;
  const vasos = e.vasos_salida || [];
  const valor = vasos.reduce((s, v) => s + (v.valor || 0), 0);
  $('#realVasos').innerHTML = `Vasos despachados: <b>${vasos.length}</b> ($${valor.toLocaleString('es-CO')}) · `
    + `en el almacén: $${(e.almacen_valor || 0).toLocaleString('es-CO')}`;
}

function pintarChip(estado) {
  const chip = $('#chipSim'), txt = $('#chipSimTxt'), real = $('#realChip');
  chip.classList.remove('vivo', 'fin');
  if (!estado) {
    txt.textContent = 'Simulación: apagada';
    real.textContent = 'sin simulación';
  } else if (estado.terminado) {
    chip.classList.add('fin');
    txt.textContent = `Simulación: corrida terminada · :${vivo.puerto}`;
    real.textContent = 'corrida terminada';
  } else {
    chip.classList.add('vivo');
    txt.textContent = `Simulación: en marcha · :${vivo.puerto}`;
    real.textContent = 'en vivo · cada 1 s';
  }
  $('#realApagado').hidden = !!estado;
  $('#realVivo').hidden = !estado;
  if (estado) {
    const url = `http://127.0.0.1:${vivo.puerto}/`;
    $('#realAbrirVisor').href = url;
  }
}

async function pedirEstado(puerto) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), 1500);
  try {
    const r = await fetch(`http://127.0.0.1:${puerto}/api/estado`, { signal: ctl.signal, cache: 'no-store' });
    if (!r.ok) return null;
    const d = await r.json();
    return d && typeof d === 'object' && 'casillas_monedas' in d ? d : null;
  } catch (e) { return null; } finally { clearTimeout(t); }
}

async function buscarPuerto() {
  // app/puertos.py deja el puerto REAL de la corrida en marcha en datos/puertos.json.
  try {
    const r = await fetch(App.url('datos/puertos.json'), { cache: 'no-store' });
    if (r.ok) { const p = await r.json(); if (p.visor) vivo.candidatos.add(Number(p.visor)); if (p.visor) return [Number(p.visor), ...vivo.candidatos]; }
  } catch (e) { /* no existe todavía */ }
  return [...vivo.candidatos];
}

async function sondear() {
  let estado = null;
  if (vivo.puerto) estado = await pedirEstado(vivo.puerto);
  if (!estado) {
    vivo.fallos += 1;
    if (!vivo.puerto || vivo.fallos >= 2) {
      vivo.puerto = null;
      for (const p of new Set(await buscarPuerto())) {
        estado = await pedirEstado(p);
        if (estado) { vivo.puerto = p; break; }
      }
    }
  }
  if (estado) { vivo.fallos = 0; vivo.ultimo = estado; pintarReal(estado); }
  else if (!vivo.puerto) vivo.ultimo = null;
  pintarChip(vivo.ultimo);
}

function estadoReal() {
  let ocupado = false;
  const ciclo = async () => {
    if (!ocupado && !document.hidden) { ocupado = true; try { await sondear(); } finally { ocupado = false; } }
    // cada 1 s mirando la prueba visual; cada 5 s en las demás vistas
    setTimeout(ciclo, vistas.actual === 'prueba' ? 1000 : 5000);
  };
  ciclo();
  $('#chipSim').addEventListener('click', () => irA('prueba'));
  $('#realVerAqui').addEventListener('click', (ev) => {
    const marco = $('#realMarco');
    if (!vivo.puerto) return;
    marco.innerHTML = '';
    const f = document.createElement('iframe');
    f.src = `http://127.0.0.1:${vivo.puerto}/`;
    f.title = 'Visor 3D en vivo';
    marco.appendChild(f);
    marco.hidden = false;
    ev.currentTarget.textContent = 'Recargar el visor aquí';
  });
}

// ---------------------------------------------------------------------------
// Programas (lista tipo Docker Desktop + detalle)
// ---------------------------------------------------------------------------

const PROGRAMAS = [
  { grupo: 'Ver el proyecto' },
  { id: 'vivo', el: '#vivo', nombre: 'Línea en vivo: visor 3D + dashboard', sub: '~8-10 s en responder' },
  { id: 'asistente', el: '#asistente', nombre: 'Asistente (preguntas y órdenes)', sub: '~5 s en arrancar' },
  { grupo: 'Física en PyBullet (ventana aparte)' },
  { id: 'sim-filtro', el: '#simFiltro', nombre: 'Escena 1 · filtro de monedas', sub: '~5 s · dura ~1 min' },
  { id: 'sim-vasos', el: '#simVasos', nombre: 'Escena 2 · embalaje de vasos', sub: '~5 s · dura ~1,5 min' },
  { id: 'sim-carro', el: '#simCarro', nombre: 'Escena 3 · carro en la pista', sub: '~5 s · dura ~3 min' },
  { id: 'sim-todo', el: '#simTodo', nombre: 'Escena 4 · todo junto', sub: '~5 s · dos ventanas' },
  { grupo: 'Comprobar' },
  { id: 'pruebas', el: '#pruebas', nombre: 'Pruebas automáticas (936)', sub: '~4-5 min' },
  { id: 'chequeo', el: '#chequeo', nombre: 'Chequeo del PC', sub: '~10-20 s' },
];
const ESTADOS = {
  preparando: ['prepara', 'preparando…'], instalando: ['prepara', 'instalando…'], lanzada: ['marcha', 'en marcha'],
  terminada: ['bien', 'terminó bien'], error: ['mal', 'falló'], detenida: ['', 'detenido'],
};
const ctls = {};
const enMarcha = new Set();
const estadoDe = {};
let elegido = 'vivo';

// Cabecera del detalle (como la de un contenedor en Docker Desktop): nombre, estado e Iniciar/Detener.
function pintarCabecera() {
  const p = PROGRAMAS.find((x) => x.id === elegido) || {};
  const est = estadoDe[elegido];
  const [cls, txt] = ESTADOS[est] || ['', 'listo para iniciar'];
  const cab = $('.pf-detalle-cab');
  cab.classList.remove('prepara', 'marcha', 'bien', 'mal');
  if (cls) cab.classList.add(cls);
  $('#detNombre').textContent = p.nombre || '';
  $('#detSub').textContent = 'Tarda ' + (p.sub || '');
  $('#detEstado').textContent = txt;
  const activo = enMarcha.has(elegido);
  $('#detIniciar').hidden = activo;
  $('#detDetener').hidden = !activo;
  $('#detIniciar').textContent = est && !activo ? '↻ Iniciar otra vez' : '▶ Iniciar';
}

function elegirPrograma(id) {
  if (!PROGRAMAS.some((p) => p.id === id)) id = 'vivo';
  $$('.pf-item').forEach((b) => { b.classList.toggle('activo', b.dataset.programa === id); b.setAttribute('aria-selected', b.dataset.programa === id); });
  $$('.pf-panel').forEach((p) => { p.hidden = p.dataset.programa !== id; });
  guardar('programa', id);
  elegido = id;
  pintarCabecera();
}

function marcarFila(id, estado) {
  const fila = document.querySelector(`.pf-item[data-programa="${id}"]`);
  if (!fila) return;
  const [cls, txt] = ESTADOS[estado] || ['', ''];
  fila.classList.remove('prepara', 'marcha', 'bien', 'mal');
  if (cls) fila.classList.add(cls);
  fila.querySelector('.pf-item-estado').textContent = txt;
  if (['preparando', 'instalando', 'lanzada'].includes(estado)) enMarcha.add(id); else enMarcha.delete(id);
  estadoDe[id] = estado;
  const cuenta = $('#cuentaMarcha');
  cuenta.hidden = !enMarcha.size;
  cuenta.textContent = enMarcha.size;
  pintarCabecera();
}

function listaProgramas() {
  const lista = $('#listaProgramas');
  for (const p of PROGRAMAS) {
    if (p.grupo) { const g = document.createElement('div'); g.className = 'pf-grupo'; g.textContent = p.grupo; lista.appendChild(g); continue; }
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'pf-item'; b.dataset.programa = p.id; b.setAttribute('role', 'option');
    b.innerHTML = `<span class="pf-punto"></span><span><b>${escapar(p.nombre)}</b><small>${escapar(p.sub)}</small></span><span class="pf-item-estado"></span>`;
    b.addEventListener('click', () => elegirPrograma(p.id));
    lista.appendChild(b);
  }
}

function enlacesEnVivo() {
  // app.lanzar dice los puertos REALES (si el 8765 u 8501 estaban ocupados, usa otros: app/puertos.py).
  const caja = $('#enlacesVivo');
  const visor = $('#linkVisor');
  const dash = $('#linkDash');
  const texto = $('#puertosReales');
  const reales = {};
  const mostrar = () => {
    caja.hidden = false;
    if (reales.visor) visor.href = reales.visor; visor.hidden = !reales.visor;
    if (reales.dash) dash.href = reales.dash; dash.hidden = !reales.dash;
    texto.textContent = [reales.visor && 'visor ' + reales.visor, reales.dash && 'dashboard ' + reales.dash].filter(Boolean).join(' · ');
  };
  return (linea) => {
    const url = (linea.match(/https?:\/\/(?:127\.0\.0\.1|localhost):\d+\/?/) || [])[0];
    if (!url) return;
    if (/dashboard/i.test(linea)) reales.dash = url;
    else if (/visor/i.test(linea)) {
      reales.visor = url;
      const p = Number((url.match(/:(\d+)/) || [])[1]);
      if (p) { vivo.candidatos.add(p); vivo.puerto = vivo.puerto || p; }
    } else return;
    mostrar();
  };
}

function panel(id, el, opciones) {
  const prog = PROGRAMAS.find((p) => p.id === id);
  ctls[id] = App.panelEjecucion(el, id, {
    ...opciones,
    alEstado: (t) => { marcarFila(id, t.estado); opciones.alEstado && opciones.alEstado(t); },
  });
  return ctls[id] && prog;
}

function programas() {
  listaProgramas();

  const alLineaVivo = enlacesEnVivo();
  panel('vivo', '#vivo', {
    queVaAPasar: 'Arranca la simulación completa (escenario prueba_completa) y, apenas responde, abre en el navegador el visor 3D y el dashboard. El visor tarda unos 8-10 s en responder; el dashboard un poco más. Mientras corra, aquí abajo salen los enlaces con los puertos reales, y en "Prueba visual" se ven las piezas reales pasando.',
    queHacer: [
      'Visor 3D: arrastra para girar, rueda para acercar. Pestaña Sensores → "Ver la prueba de este sensor"; botones de sabotaje (retirar un vaso, mano en la cortina…).',
      'Dashboard: barra lateral → "Probar un filtro" (cada filtro por separado, como pide la sustentación); pestañas Monedas y vasos, Carro y ruta, Asistente.',
      'Detener cierra la simulación y el dashboard.',
    ],
    queDeberiasVer: 'En el visor, el chip de arriba pasa de "conectando…" a "corriendo" y las piezas avanzan por la cinta; en el dashboard, "La línea está trabajando" y el valor aceptado subiendo. Arriba en esta app, "Simulación: en marcha".',
    alLinea: (texto) => alLineaVivo(texto),
  });

  const teclas = ['En la ventana de PyBullet: espacio pausa, r reinicia, q sale (o ciérrala).', 'Arrastra con el ratón para girar la cámara; rueda para acercar.'];
  panel('sim-filtro', '#simFiltro', { queHacer: teclas,
    queDeberiasVer: '18 piezas mezcladas, cada una con un rótulo de su material o su causa de rechazo; al final 7 en el almacén y 11 en rechazo, sin falsas aceptaciones.' });
  panel('sim-vasos', '#simVasos', { queHacer: teclas,
    queDeberiasVer: 'El vaso se verifica, se llena por lotes, se tapa y se prensa; con los sabotajes, la línea se detiene a tiempo.' });
  panel('sim-carro', '#simCarro', { queHacer: teclas,
    queDeberiasVer: 'El carro sigue la línea, rodea los tres muros, llega a la meta y vuelve de reversa al muelle.' });
  panel('sim-todo', '#simTodo', { queHacer: [...teclas, 'Se abren DOS ventanas: la planta y el carro (PyBullet permite una por proceso).'],
    queDeberiasVer: 'La planta y el carro en la misma corrida.' });

  panel('asistente', '#asistente', {
    queHacer: 'Escribe en la caja de abajo y pulsa Enter, o usa una de las sugerencias.',
    queDeberiasVer: 'Cada respuesta con las cifras de la última corrida guardada y, al final, [respondió: local] (las reglas). Las órdenes ("avanza 20 cm") las entiende, pero desde aquí no mueven nada: para eso, la pestaña Asistente del dashboard con la línea en vivo.',
    sugerencias: ['¿cuántas monedas se aceptaron?', '¿cuántas piezas se rechazaron y por qué?', '¿qué sensor detecta el metal?',
      'cuanto hay de 500', '¿cuánto cuesta construir el proyecto?', 'avanza 20 cm'],
  });

  panel('pruebas', '#pruebas', {
    queDeberiasVer: 'Una fila de puntos que avanza hasta 100 % y al final "936 passed" (con la instalación mínima se omiten 2, "skipped": las que compilan el firmware con mpy-cross). Tarda unos 4-5 minutos.',
  });
  panel('chequeo', '#chequeo', {
    queDeberiasVer: 'Una lista con ✓ (listo), ! (aviso) y ✗ (falta), cada una con cómo arreglarla. Con la instalación mínima es normal ver ✗ en Ollama, la voz o el firmware: no hacen falta para verlo. Si dice "Puerto 8765 … lo ocupa OTRO programa", no pasa nada: se usará el siguiente libre.',
  });

  $('#detIniciar').addEventListener('click', () => { const c = ctls[elegido]; if (c && c.iniciar) c.iniciar(); });
  $('#detDetener').addEventListener('click', () => { const c = ctls[elegido]; if (c && c.detener) c.detener(); });
  elegirPrograma(leer('programa') || 'vivo');
}

function arrancar(id) {
  irA('programas');
  elegirPrograma(id);
  const c = ctls[id];
  if (c && c.iniciar && !enMarcha.has(id)) c.iniciar();
}

// ---------------------------------------------------------------------------
// Inicio
// ---------------------------------------------------------------------------

async function main() {
  // Navegación primero: la app responde aunque el lanzador tarde.
  $$('.pf-nav').forEach((b) => b.addEventListener('click', () => irA(b.dataset.vista)));
  $$('[data-ir]').forEach((b) => b.addEventListener('click', () => {
    irA(b.dataset.ir);
    if (b.dataset.programa) elegirPrograma(b.dataset.programa);
  }));
  $$('[data-ir-programa]').forEach((a) => a.addEventListener('click', (ev) => { ev.preventDefault(); irA('programas'); elegirPrograma(a.dataset.irPrograma); }));
  recorrido();
  irA((location.hash || '').slice(1) || leer('vista') || 'inicio');

  await App.iniciar();
  App.checklist('#pide');
  $$('[data-abrir]').forEach((a) => a.addEventListener('click', (ev) => { ev.preventDefault(); App.abrir(a.dataset.abrir); }));

  App.markdown('#arquitectura', 'README.md', { desde: '## La idea general', hasta: '### El recorrido de una moneda' });
  App.markdown('#recorridoMd', 'README.md', { desde: '### El recorrido de una moneda', sinTitulo: true });
  App.markdown('#estado', 'README.md', { desde: '## Estado del proyecto', sinTitulo: true });

  programas();
  estadoReal();
  $('#arrancarDesdePrueba').addEventListener('click', () => arrancar('vivo'));

  $('#abrirPortable').addEventListener('click', () => App.abrir('visor-portable.html'));
  $('#cargarPortable').addEventListener('click', (ev) => {
    const marco = $('#marcoPortable');
    if (!marco.firstChild) {
      const nota = $('#portableCarga');
      nota.textContent = 'Cargando 2,6 MB (Three.js + la demo)… unos segundos.';
      const f = document.createElement('iframe');
      f.src = App.url('visor-portable.html');
      f.title = 'Visor 3D portable (demo grabada)';
      f.setAttribute('allow', 'fullscreen');
      f.addEventListener('load', () => { nota.textContent = 'Listo: demo grabada.'; });
      marco.appendChild(f);
    }
    marco.hidden = false;
    ev.currentTarget.textContent = 'Visor cargado (demo grabada)';
  });

  App.imagen(document.querySelector('.m-capturas'));
}

main().catch((e) => { console.error(e); App.aviso && App.aviso('No se pudo iniciar la app: ' + e.message, 'error'); });
