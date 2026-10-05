// Interfaz del visor 3D: barra, vistas, panel con pestañas, avisos, bitácora y leyenda de cables.
//
// La escena (piezas, cámara, animaciones) vive en visor.js; aquí solo está lo que el usuario ve
// y toca ALREDEDOR de la escena. visor.js crea la interfaz con `crearInterfaz(ctx)` y le pasa en
// `ctx` lo que necesita de la escena (llevar la cámara a una vista, encuadrar un sensor, saber si
// un sensor está activo, mostrar los cables 3D...). Así este archivo no toca Three.js.
//
// Inventario de todo lo que hace (y la lista de verificación): docs/interfaz-visor.md.
// La forma (colores, tamaños, espaciados) está en estilo.css.

// Selección compartida con la escena: el render resalta estos sensores y este componente.
export const SEL = { resaltados: new Set(), componente: null };

export const esc = (t) => String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const pesos = (n) => '$' + Number(n || 0).toLocaleString('es-CO');
const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];

// ¿La simulación de este PC ya responde? (vigía del visor portable, sin internet: servidor local)
// Devuelve la URL donde responde, o null. Si otro programa del PC tiene el puerto configurado
// (8765), app.lanzar usa el siguiente libre (app/puertos.py): por eso se pregunta también en los
// PUERTOS_EXTRA siguientes y gana el más bajo que conteste con un estado JSON de la planta.
const PUERTOS_EXTRA = 20;
async function respondeEn(url) {
  try {
    const r = await fetch(url + 'api/estado', { cache: 'no-store', signal: AbortSignal.timeout(1500) });
    if (!r.ok) return false;
    const e = await r.json();
    return !!e && typeof e === 'object' && !Array.isArray(e);
  } catch (e) { return false; }
}
export async function simulacionCorriendo(urlVivo) {
  let base;
  try { base = new URL(urlVivo); } catch (e) { return null; }
  const p0 = Number(base.port || 80);
  const urls = [];
  for (let i = 0; i <= PUERTOS_EXTRA; i++) urls.push(`${base.protocol}//${base.hostname}:${p0 + i}/`);
  const vivos = await Promise.all(urls.map(respondeEn));
  const i = vivos.indexOf(true);
  return i < 0 ? null : urls[i];
}

// ---------------------------------------------------------------------------
// datos fijos de la interfaz
// ---------------------------------------------------------------------------

// Prueba UNICA de cada sensor (usuario, 2026-09-27): en la sustentacion los filtros se prueban uno
// por uno. Cada boton manda la orden que hace trabajar SOLO a ese sensor (una prueba de un filtro,
// una pieza puesta a mano, un sabotaje o una orden al carro) y la camara se queda mirandolo.
const PRUEBA_SENSOR = {
  presencia: [['Poner una moneda en la carga', { cmd: 'colocar', pieza: '500_nueva' }],
    ['Mano en la carga (la ve y no es moneda)', { cmd: 'sabotaje', tipo: 'mano_carga' }]],
  capacitivo: [['Prueba del filtro de material (botones de plástico)', { cmd: 'iniciar', escenario: 'no_metalico' }]],
  inductivo: [['Prueba del filtro de material (botones de plástico)', { cmd: 'iniciar', escenario: 'no_metalico' }]],
  camara: [['Diámetro fuera de rango', { cmd: 'iniciar', escenario: 'fuera_de_rango' }],
    ['No circular (bloques)', { cmd: 'iniciar', escenario: 'no_circular' }],
    ['Perforado (botones con agujero)', { cmd: 'iniciar', escenario: 'perforado' }],
    ['No reconocida (sin cara colombiana)', { cmd: 'iniciar', escenario: 'no_reconocida' }],
    ['Incoherente (cara y diámetro no cuadran)', { cmd: 'iniciar', escenario: 'incoherente' }]],
  sensor_interior: [['El próximo vaso trae algo adentro', { cmd: 'sabotaje', tipo: 'vaso_con_algo' }]],
  hall_carrusel: [['Moneda al almacén (el carrusel busca su tubo)', { cmd: 'colocar', pieza: '200_nueva' }]],
  camara_vasos: [['Retirar un vaso', { cmd: 'sabotaje', tipo: 'retirar_vaso' }],
    ['Cambiar un vaso por una figura', { cmd: 'sabotaje', tipo: 'cambiar_vaso' }],
    ['Cambiar un vaso por otro igual (otro marcador)', { cmd: 'sabotaje', tipo: 'vaso_igual' }]],
  cortina: [['Meter o quitar la mano en tapa y prensa', { cmd: 'sabotaje', tipo: 'intruso' }]],
  linea_ir: [['Retomar la línea', { cmd: 'carro', accion: 'seguir_linea' }]],
  ultrasonico: [['Ir a la meta esquivando los muros', { cmd: 'carro', accion: 'ir_meta' }]],
  laser_frontal: [['Ir a la meta esquivando los muros', { cmd: 'carro', accion: 'ir_meta' }]],
  encoders: [['Avanzar 30 cm (cuenta los pulsos)', { cmd: 'carro', accion: 'avanzar', distancia_m: 0.3 }]],
  cuna: [['Volver al muelle (la cuna confirma la carga)', { cmd: 'carro', accion: 'volver_muelle' }]],
};

// Cada boton de Pruebas se habilita solo cuando puede hacer algo; si no, dice por que.
const MOTIVO = {
  corriendo: 'La línea no está corriendo',
  vaso_vl: 'Hace falta un vaso en verificación o en llenado',
  vaso_tp: 'Hace falta un vaso en tapa o en prensa (y que no haya otra mano)',
  sin_mano: 'Ya hay una mano en la línea',
  guardado: 'Los tubos están vacíos',
  carro: 'Sin carro simulado (carro de reemplazo)',
  colocar: 'La corrida tiene que estar andando o terminada',
  libre: 'Esta simulación no trae las pruebas de un filtro (reiniciarla)',
};

// Subsistemas de la pestaña Componentes: sensores y componentes de la misma parte de la planta
// juntos. `vista` es el boton de camara de esa parte.
const SUBSISTEMAS = [
  { nombre: 'Línea de monedas', vista: 'monedas', zonas: ['monedas'], sensor: (s) => s.subsistema === 'cinta de monedas' },
  { nombre: 'Almacén', vista: 'almacen', zonas: ['almacen'], sensor: (s) => s.id === 'hall_carrusel' },
  { nombre: 'Línea de vasos', vista: 'vasos', zonas: ['vasos', 'tapa'], sensor: (s) => s.subsistema === 'cinta de vasos' && s.id !== 'hall_carrusel' },
  { nombre: 'Canaleta y muelle', vista: 'canaleta', zonas: ['canaleta'], sensor: () => false },
  { nombre: 'Carro y pista', vista: 'carro', zonas: ['pista'], categoria: 'Carro', sensor: (s) => s.subsistema === 'carro' },
  { nombre: 'Caja de control y portátil', vista: 'caja', zonas: ['control'], sensor: () => false },
];

const TEXTO_ALARMA = {
  tubo_lleno: 'tubo lleno sin vaso', faltan_vasos: 'faltan vasos',
  cuna_ocupada: 'la cuna del carro no está vacía: no se suelta', carga_no_confirmada: 'el infrarrojo de la cuna no ve el vaso soltado',
};

// Texto de cada evento de la simulacion para la bitacora (null = no se muestra).
function describirEvento(e) {
  const mal = (t) => `<b class="alarma">${t}</b>`;
  const ojo = (t) => `<b class="atencion">${t}</b>`;
  const bien = (t) => `<b class="ok">${t}</b>`;
  switch (e.ev) {
    case 'presencia': return e.tipo_real === 'mano' ? `#${e.casilla} ${mal('mano en la carga')} (el IR la ve)` : e.ocupada ? `#${e.casilla} cargado (${esc(e.tipo_real)})` : `#${e.casilla} casilla vacía`;
    case 'material': return `#${e.casilla} material: <b>${e.metal ? 'metal' : 'no metálico'}</b>`;
    case 'vision': return `#${e.casilla} visión (${(e.fotos || []).length || 1} fotos): ${e.diametro_mm.toFixed(1)} mm, ${esc(e.clase)} (${e.confianza.toFixed(2)})`;
    case 'rechazo': return `#${e.casilla} → ${mal('bandeja de rechazo')} (${esc(e.causa || e.motivo)})`;
    case 'elemento_final': return e.veredicto === 'aceptada' ? `#${e.casilla} aceptada <b>${esc(e.clase)}</b>` : `#${e.casilla} rechazada <b>${esc(e.causa)}</b>`;
    case 'llenado': return `vaso ${e.vaso}: ${e.cantidad} monedas`;
    case 'verificacion': return `vaso ${e.vaso} verificado (cámara): <b>${esc(e.estado)}</b>`;
    case 'tapa': return e.tapado ? `vaso ${e.vaso} <b>tapado</b>` : e.vacio && e.estado === 'valida' ? `vaso ${e.vaso} vacío: no se tapa (se desecha)` : `vaso ${e.vaso} sin tapa (${esc(e.estado)})`;
    case 'tapa_no_confirmada': return mal(`vaso ${e.vaso}: la cámara no ve la tapa`);
    case 'prensa': return `vaso ${e.vaso} prensado`;
    case 'descarga': return e.destino === 'vacio' ? `vaso ${e.vaso} vacío → <b>desechado</b>` : `vaso ${e.vaso} → <b>${esc(e.destino)}</b>`;
    case 'cortina': return e.activa ? `${mal(e.fuente === 'camara_llenado' ? 'la cámara ve algo sobre el llenado' : 'cortina ACTIVA')} (prensa arriba, no se suelta el lote)` : bien('cortina despejada');
    case 'desfase_corregido': return `${ojo(`cinta de ${esc(e.cinta)} corrida`)}: la cámara vio los separadores fuera de lugar, re-sincronizada`;
    case 'sabotaje_detectado': return `${mal('sabotaje detectado')} vaso ${e.vaso}: ${esc(e.motivo)}${e.estacion === 'camara' ? ' (la cámara ve la casilla sin vaso)' : ''}`;
    case 'salto_casilla': return 'salto de casilla en la cinta de vasos';
    case 'espera':
      if (e.src !== 'e4') return null;   // la cinta vacia sin carga no es noticia
      if (e.motivo === 'carrusel_girando') {
        const tubo = e.tubo === 'otras' ? 'otras' : `$${e.denominacion}`;
        return `#${e.casilla} ${ojo('espera en la descarga')}: el carrusel ${e.soltando_lote ? 'suelta un lote y después trae' : 'trae'} el tubo <b>${tubo}</b>${typeof e.falta_ms === 'number' ? ` (falta ${(e.falta_ms / 1000).toFixed(1)} s)` : ''}; la cinta de monedas espera`;
      }
      return `#${e.casilla} ${ojo('espera')}: tubo $${e.denominacion} lleno y sin vaso válido`;
    case 'gira': return e.src === 'carrusel'
      ? `carrusel: tubo <b>${e.tubo === 'otras' ? 'otras' : '$' + e.tubo}</b> → ${e.lugar === 'agujero' ? 'agujero (soltar lote)' : 'carga'} (${(e.dur_ms / 1000).toFixed(1)} s)`
      : null;
    case 'fin': return '<b>fin de la corrida</b>';
    case 'almacen': return e.tubo === 'otras' ? `#${e.casilla} ${esc(e.clase)} → <b>otras</b> (va a su propio vaso)` : `#${e.casilla} ${esc(e.clase)} → <b>tubo $${e.denominacion}</b> (${e.en_tubo})`;
    case 'presencia_recuperada': return `#${e.casilla} ${ojo('presencia recuperada')} (E1 falló, E2 la vio)`;
    case 'canaleta_llena': return `${ojo('canaleta llena')}: el vaso ${e.vaso} espera en la descarga`;
    case 'carga': return `carro: se lleva el vaso ${e.vaso}`;
    case 'en_muelle': return 'carro en el muelle (encoders quietos contra el tope)';
    case 'salida': return 'carro: sale del muelle con el vaso';
    case 'obstaculo': return `${ojo('carro: obstáculo')} a ${Math.round(e.distancia_mm)} mm (3 lecturas seguidas)`;
    case 'evasion': return `carro: esquiva por la <b>${esc(e.lado)}</b>${e.izq_mm || e.der_mm ? ` (izq ${e.izq_mm ?? 'libre'} mm, der ${e.der_mm ?? 'libre'} mm)` : ' (los dos lados libres)'}`;
    case 'linea_recuperada': return 'carro: vuelve a la línea';
    case 'linea_perdida': return `${ojo('carro: perdió la línea')}, la busca girando`;
    case 'meta': return `${bien('carro en la META')}: esperan que saquen el vaso`;
    case 'entregado': return `vaso ${e.vaso} ${bien('entregado en la meta')}`;
    case 'sin_enlace': return `${mal('radio del carro sin enlace')}: termina la vuelta solo; no se le carga otro vaso`;
    case 'enlace_recuperado': return `radio del carro ${bien('con enlace')} (${e.en_espera || 0} mensajes guardados llegan en orden)`;
    case 'estado': return `el carro informa: ${esc(e.estado)}, cuna ${e.cuna ? 'ocupada' : 'vacía'}`;
    case 'vaso_retirado': return 'el infrarrojo de la cuna ve que sacaron el vaso: vuelve';
    case 'vuelve_con_vaso': return ojo('sin radio: vuelve con el vaso');
    case 'devuelto': return `vaso ${e.vaso} devuelto al muelle y retirado a mano`;
    case 'vuelta': return 'carro: media vuelta, regresa solo';
    case 'marca_giro': return 'carro: marca de giro, entra de reversa al muelle';
    case 'error': return `${mal('carro detenido')}: ${esc(e.motivo)}`;
    case 'soltar': return `escape: suelta el vaso ${e.vaso} a la cuna`;
    case 'embalado': return `${bien(`lote de ${e.denominacion === 'otras' ? 'otras' : '$' + e.denominacion}`)} → vaso ${e.vaso} (${e.cantidad} monedas)`;
    default: return null;
  }
}

// ---------------------------------------------------------------------------
// la interfaz
// ---------------------------------------------------------------------------

/**
 * ctx (lo pone visor.js):
 *   enArchivo, urlVivo, base               de dónde se abrió y a quién se le pregunta
 *   modoDemo()                             true si se ve la demo grabada (puede cambiar al arrancar)
 *   G(), estado(), pasos()                 geometría, último /api/estado, paso a paso
 *   vista(nombre), saltarVuelo()           cámara
 *   enfocarSensor(id), encuadrarComponente(id)
 *   tiene3D(idComponente), sensorEn3D(id), sensorActivo(id), sensorEnAlarma(id)
 *   mostrarCables3D(si), datosCables()     -> { cables: [{nombre,tipo,largo,zona}], tipos }
 *   alCambiarInternet(hay)                 la nube 3D del asistente (gris sin internet)
 */
export function crearInterfaz(ctx) {
  const contenido = $('#contenido');
  const panel = $('#panel');
  let pestana = 'vivo';
  let seleccion = { tipo: null, valor: null };   // {tipo:'paso'|'sensor', valor}
  let sensorEnComp = null;                        // sensor abierto en la pestaña Componentes
  let pruebaEnviada = null;                       // { sensor, n }: respuesta a "Ver la prueba"
  let ultimaRespuesta = 0;
  let ultimoPintado = 0;
  let fallos = 0;
  let hayInternet = null;
  let fallosInternet = 0;
  const bitacora = [];

  const demo = () => ctx.modoDemo();
  const marcarVista = (nombre) => $$('[data-vista]').forEach((b) => b.classList.toggle('activo', b.dataset.vista === nombre));
  // La camara va a un sensor o a un componente: ya no esta en ninguna vista de los botones.
  const enfocarSensor = (id) => { marcarVista(null); ctx.enfocarSensor(id); };
  const G = () => ctx.G();
  const estado = () => ctx.estado() || {};
  const ledDe = (id) => (ctx.sensorActivo(id) ? (ctx.sensorEnAlarma(id) ? 'led alarma' : 'led on') : 'led');

  // ---------- distribución: la parte libre de la escena ----------

  function panelAbierto() { return !panel.classList.contains('oculto'); }
  // Ancho que tapa el panel a la izquierda (0 si está cerrado o si es la hoja de abajo).
  function anchoTapado() {
    return panelAbierto() && window.innerWidth > 900 ? panel.getBoundingClientRect().right : 0;
  }
  function acomodar() {
    const tapado = anchoTapado();
    const izq = tapado ? tapado + 12 : 12;
    document.documentElement.style.setProperty('--izq', izq + 'px');
    // La ayuda va entre la leyenda/panel y la bitácora; si no cabe, no se muestra.
    document.body.classList.toggle('estrecho', window.innerWidth - izq - 464 < 470);
    pintarModo();
  }
  function mostrarPanel(si) {
    panel.classList.toggle('oculto', !si);
    $('#btnPanel').classList.toggle('activo', si);
    acomodar();
  }

  // ---------- pestañas ----------

  function marcarPestana(nombre) {
    pestana = nombre;
    $$('[data-pestana]').forEach((x) => x.classList.toggle('activo', x.dataset.pestana === nombre));
  }
  function mostrarPestana(nombre) {
    marcarPestana(nombre);
    contenido.innerHTML = '';
    contenido.scrollTop = 0;
    pintarPanel();
  }
  function pintarPanel() {
    if (!G()) return;
    if (pestana === 'componentes') return pintarComponentes();
    if (pestana === 'pasos') return pintarPasos();
    if (pestana === 'sensores') return pintarSensores();
    if (pestana === 'pruebas') return pintarPruebas();
    pintarVivo();
  }
  // Lo que cambia con la simulación, sin rehacer lo que el usuario está tocando (listas
  // desplegables abiertas, botones a medio clic): una vez por segundo como mucho.
  function refrescar() {
    const e = estado();
    if (pestana === 'vivo') actualizarVivo(e);
    if (pestana === 'pruebas') actualizarBotones(e);
    for (const el of $$('[data-led]', contenido)) el.className = ledDe(el.dataset.led);
    for (const el of $$('[data-lectura]', contenido)) el.textContent = ctx.sensorActivo(el.dataset.lectura) ? 'activo' : 'inactivo';
    const rs = $('#respSensor', contenido);
    if (rs) rs.innerHTML = respuestaPrueba(rs.dataset.sensor);
  }

  // ---------- En vivo ----------

  function pintarVivo() {
    if (!$('#vivoDatos', contenido)) {
      contenido.innerHTML = `
        <h3 class="titulo-pestana">Línea en vivo</h3>
        <div id="vivoDatos"></div>
        <section class="seccion"><h4>Sensores de la planta <span class="cuenta">verde: activo · rojo: alarma</span></h4>
          <div id="vivoLeds" class="leds"></div></section>`;
      $('#vivoLeds', contenido).innerHTML = G().sensores.filter((s) => s.geometria).map((s) =>
        `<div><span data-led="${esc(s.id)}" class="${ledDe(s.id)}"></span><span class="n">${s.numero}</span><span>${esc(s.nombre)}</span></div>`).join('');
    }
    actualizarVivo(estado());
  }

  function actualizarVivo(e) {
    const caja = $('#vivoDatos', contenido);
    if (!caja) return;
    const vs = e.vasos_salida || [];
    const enVasos = [...(e.casillas_vasos || []).filter(Boolean), ...vs];
    const monedas = enVasos.reduce((a, v) => a + (v.cantidad || 0), 0);
    const valor = enVasos.reduce((a, v) => a + (v.valor || 0), 0);
    const rech = (e.salidas || {}).rechazo || [];
    const porCausa = {};
    for (const r of rech) porCausa[r.causa || 'sin registro'] = (porCausa[r.causa || 'sin registro'] || 0) + 1;
    const al = e.almacen || {};
    const tubos = [50, 100, 200, 500, 1000].map((d) => `${pesos(d)}: <b>${al[String(d)] || 0}</b>`).join(' · ') + ` · otras: <b>${al.otras || 0}</b>`;
    const ef = e.errores_filtrado || {};
    const c = e.carro;
    const radio = c && c.radio;
    caja.innerHTML = `
      <p class="escenario">Escenario <b>${esc(e.escenario || '—')}</b> · quedan <b class="mono">${e.pendientes ?? '—'}</b> por cargar</p>
      <div class="tiras">
        <div class="tira"><div class="valor">${monedas}</div><div class="que">monedas en vasos · ${pesos(valor)}</div></div>
        <div class="tira"><div class="valor">${pesos(e.almacen_valor)}</div><div class="que">guardado en tubos</div></div>
        <div class="tira"><div class="valor">${rech.length}</div><div class="que">rechazos (una sola bandeja)</div></div>
        <div class="tira"><div class="valor">${vs.filter((v) => v.destino === 'entrega').length}</div><div class="que">vasos entregados</div></div>
      </div>
      <dl class="detalle">
        <dt>Guardado en tubos (lote de ${e.monedas_por_vaso ?? '—'})</dt><dd>${tubos}<br><span class="tenue">ninguna moneda aceptada se descarta</span></dd>
        <dt>Rechazos por causa</dt><dd>${rech.length ? Object.entries(porCausa).map(([k, n]) => `${esc(k)}: ${n}`).join(' · ') : '<span class="tenue">ninguno</span>'}</dd>
        <dt>Errores de sensor (simulados)</dt><dd>${e.errores_sensores_activos ? `colombianas rechazadas por error: ${ef.falsos_rechazos || 0} · no colombianas aceptadas: ${ef.falsas_aceptaciones || 0} · vaso equivocado: ${ef.clase_equivocada || 0}` : 'sensores perfectos en esta corrida'}</dd>
        <dt>Vasos</dt><dd>Entregados: ${vs.filter((v) => v.destino === 'entrega').length} · rechazados: ${vs.filter((v) => v.destino === 'rechazo').length} · vacíos desechados: ${vs.filter((v) => v.destino === 'vacio').length}</dd>
        <dt>Canaleta y carro</dt><dd>En la canaleta: ${(e.canaleta || []).length} de ${G().canaleta.capacidad}${e.vaso_esperando_canaleta ? ` · el vaso ${e.vaso_esperando_canaleta} espera en la descarga` : ''}<br>${c ? `Carro: ${esc(c.fase)} (${esc(c.estado)})${c.vaso_id ? `, lleva el vaso ${c.vaso_id}` : ''}` : '<span class="tenue">Sin carro simulado: uno de reemplazo se los lleva</span>'}</dd>
        ${radio ? `<dt>Radio del carro</dt><dd>${radio.enlace ? '<span class="bien">con enlace</span>' : '<span class="mal">sin enlace</span>'}${radio.en_espera ? ` · ${radio.en_espera} mensajes guardados en el carro` : ''} · cuna según el carro: ${radio.cuna_reportada === null ? 'sin saber (no se le carga)' : radio.cuna_reportada ? 'ocupada' : 'vacía'}${radio.enlace ? '' : '<br><span class="tenue">Último dato: no se le carga hasta que informe de nuevo</span>'}</dd>` : ''}
      </dl>`;
  }

  // ---------- Pruebas (todos los controles en un solo lugar) ----------

  function pintarPruebas() {
    if ($('#controles', contenido)) return actualizarBotones(estado());
    contenido.innerHTML = `
      <h3 class="titulo-pestana">Pruebas</h3>
      <p class="intro">Todo lo que se le puede pedir a la simulación. Un botón gris no puede hacer nada ahora: el motivo sale al pasar el ratón. La respuesta del supervisor aparece al pie del panel.</p>
      ${demo() ? '<div class="demo-aviso">Demo grabada: los controles están desactivados. Para manejar la línea, abrir <code>visor.bat</code> en el PC.</div>' : ''}
      <div id="controles">
        <section class="control"><h4>Línea</h4>
          <div class="rejilla c4">
            <button data-orden="iniciar" class="primario" title="Corrida nueva con la prueba completa">▶ Iniciar</button>
            <button data-orden="pausar" title="Pausa la línea">Pausa</button>
            <button data-orden="reanudar" title="Sigue después de una pausa">Seguir</button>
            <button data-orden="paro" class="peligro" title="Paro de emergencia: todo queda quieto; sale con Iniciar">Paro</button>
          </div></section>
        <section class="control"><h4>Probar un filtro</h4>
          <p>Corrida con solo piezas que ese filtro debe rechazar (uno por uno, como en la sustentación).</p>
          <div class="rejilla c1">
            <select id="selFiltro" aria-label="Filtro a probar"></select>
            <button id="botonFiltro" data-pide="libre">Probar solo este filtro</button>
          </div></section>
        <section class="control"><h4>Colocar una pieza</h4>
          <p>Entra en la próxima carga, antes que lo que falta de la corrida.</p>
          <div class="rejilla c1">
            <select id="selPieza" aria-label="Pieza a colocar"></select>
            <button id="botonPieza" data-pide="colocar">Ponerla en la próxima carga</button>
          </div></section>
        <section class="control"><h4>Sabotajes</h4>
          <div class="subtitulo">A los vasos</div>
          <div class="rejilla c2">
            <button data-sab="retirar_vaso" data-pide="vaso_vl">Retirar un vaso</button>
            <button data-sab="cambiar_vaso" data-pide="vaso_vl">Cambiar por figura</button>
            <button data-sab="vaso_igual" data-pide="vaso_vl">Cambiar por vaso igual</button>
            <button data-sab="vaso_con_algo" data-pide="corriendo">Vaso con algo adentro</button>
          </div>
          <div class="subtitulo">Manos en la línea</div>
          <div class="rejilla c2">
            <button data-sab="mano_carga" data-pide="corriendo">Mano en la carga</button>
            <button data-sab="mano_llenado" data-pide="sin_mano">Mano sobre el llenado</button>
            <button data-sab="intruso" data-pide="corriendo" id="botonIntruso">Mano en tapa/prensa</button>
            <button data-sab="mano_saca_vaso" data-pide="vaso_tp">Mano saca un vaso</button>
          </div></section>
        <section class="control"><h4>Carro y radio</h4>
          <div class="rejilla c1">
            <button data-sab="radio" data-pide="carro" id="botonRadio" title="Corta o reconecta la radio (ESP-NOW) del carro">Cortar la radio del carro</button>
          </div></section>
        <section class="control"><h4>Fin de turno</h4>
          <div class="rejilla c1">
            <button data-orden="embalar_parciales" data-pide="guardado" title="Empaca lo que quedó en los tubos (cada vaso de una sola denominación)">Embalar lo guardado</button>
          </div></section>
      </div>`;
    $$('[data-orden]', contenido).forEach((b) => b.addEventListener('click', () => {
      const orden = { cmd: b.dataset.orden };
      // Una sola prueba (prueba_completa): el supervisor la usa por defecto.
      if (orden.cmd === 'iniciar') orden.escenario = 'prueba_completa';
      enviarOrden(orden);
    }));
    $('#botonFiltro', contenido).addEventListener('click', () => {
      const v = $('#selFiltro', contenido).value;
      if (v) enviarOrden({ cmd: 'iniciar', escenario: v });
    });
    $('#botonPieza', contenido).addEventListener('click', () => {
      const v = $('#selPieza', contenido).value;
      if (v) enviarOrden({ cmd: 'colocar', pieza: v });
    });
    $$('[data-sab]', contenido).forEach((b) => b.addEventListener('click', () => {
      const e = estado();
      let tipo = b.dataset.sab;
      if (tipo === 'intruso') tipo = e.intruso ? 'intruso_off' : 'intruso_on';
      if (tipo === 'radio') tipo = e.carro && e.carro.radio && !e.carro.radio.conectada ? 'radio_on' : 'radio_off';
      enviarOrden({ cmd: 'sabotaje', tipo });
    }));
    actualizarBotones(estado());
  }

  function actualizarBotones(e) {
    const raiz = $('#controles', contenido);
    if (!raiz) return;
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
      colocar: (corre || e.linea === 'terminada') && !!(e.piezas && e.piezas.length),
      libre: !!(e.pruebas_filtro && e.pruebas_filtro.length),
    };
    // Las listas vienen del supervisor (sim/carga_escenarios.py): se llenan una vez.
    const selF = $('#selFiltro', raiz);
    if (!selF.options.length && e.pruebas_filtro) {
      selF.innerHTML = e.pruebas_filtro.map((pr) => `<option value="${esc(pr.escenario)}">${esc(pr.estacion)} · ${esc(pr.nombre)}</option>`).join('');
    }
    const selP = $('#selPieza', raiz);
    if (!selP.options.length && e.piezas) {
      selP.innerHTML = e.piezas.map((pz) => `<option value="${esc(pz.id)}">${esc(pz.nombre)}</option>`).join('');
    }
    // La demo grabada no trae las listas: se dice en vez de dejar la lista vacia.
    if (!selF.options.length && demo()) selF.innerHTML = '<option>solo con la simulación en vivo</option>';
    if (!selP.options.length && demo()) selP.innerHTML = '<option>solo con la simulación en vivo</option>';
    selF.disabled = selP.disabled = demo();
    // El motivo real primero: con la corrida terminada, "Mano sobre el llenado" decia "ya hay una mano"
    // y "Cortar la radio" decia "sin carro simulado", cuando lo que falta es que la linea corra.
    const motivo = (k) => {
      if (k === 'carro' && e.carro && e.carro.radio) return 'La línea no está corriendo ni en pausa';
      if (['vaso_vl', 'vaso_tp', 'sin_mano'].includes(k) && !corre) return MOTIVO.corriendo;
      return MOTIVO[k];
    };
    $$('[data-pide]', raiz).forEach((b) => {
      const ok = demo() ? false : puede[b.dataset.pide];
      b.disabled = !ok;
      b.title = ok ? '' : (demo() ? 'Demo grabada' : motivo(b.dataset.pide));
    });
    const orden = { pausar: corre, reanudar: e.linea === 'pausada', paro: corre || e.linea === 'pausada' };
    $$('[data-orden]', raiz).forEach((b) => {
      if (b.dataset.orden in orden) b.disabled = demo() || !orden[b.dataset.orden];
      if (b.dataset.orden === 'iniciar') b.disabled = demo();
    });
    $('#botonIntruso', raiz).textContent = e.intruso ? 'Quitar la mano (tapa/prensa)' : 'Mano en tapa/prensa';
    $('#botonRadio', raiz).textContent = e.carro && e.carro.radio && !e.carro.radio.conectada ? 'Reconectar la radio del carro' : 'Cortar la radio del carro';
  }

  // Respuesta del supervisor a la última orden, al pie del panel (se ve desde cualquier pestaña).
  function actualizarRespuesta(e) {
    const r = e.ultima_orden;
    const caja = $('#respuestaOrden');
    if (!caja || !r || r.n === ultimaRespuesta) return;
    const primera = ultimaRespuesta === 0 && !enviada;
    ultimaRespuesta = r.n;
    if (primera) return;   // la de antes de abrir el visor no es noticia
    caja.innerHTML = `<div class="respuesta ${r.ok ? 'ok' : 'no'}"><span class="marca-r">${r.ok ? '✔' : '✖'}</span><span>${esc(r.detalle)}</span></div>`;
    caja.classList.add('visible');
    clearTimeout(caja._t);
    caja._t = setTimeout(() => caja.classList.remove('visible'), 7000);
  }

  let enviada = false;
  async function enviarOrden(orden) {
    if (demo()) return;
    enviada = true;
    try {
      await fetch(ctx.base + 'api/orden', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(orden) });
    } catch (e) { /* el aviso de conexion ya lo muestra */ }
  }

  // ---------- Paso a paso ----------

  function pintarPasos() {
    const sel = seleccion.tipo === 'paso' ? seleccion.valor : null;
    const pasos = ctx.pasos();
    const lista = pasos.map((p) => `
      <button class="item ${sel === p.numero ? 'sel' : ''}" data-paso="${p.numero}">
        <span class="n">${p.numero}</span><span class="nombre">${esc(p.titulo)}</span><span class="rev ${esc(p.revision)}">${esc(p.revision)}</span>
      </button>${sel === p.numero ? detallePaso(p, pasos.length) : ''}`).join('');
    contenido.innerHTML = `<h3 class="titulo-pestana">Paso a paso</h3>
      <p class="intro">Cada punto de la secuencia (sección 5). Al elegir uno, la cámara va a esa zona y se resaltan sus sensores.</p>${lista || '<p class="tenue">Sin paso a paso (la simulación no lo mandó).</p>'}`;
    $$('[data-paso]', contenido).forEach((d) => d.addEventListener('click', () => seleccionarPaso(Number(d.dataset.paso))));
    $$('[data-ir]', contenido).forEach((b) => b.addEventListener('click', (ev) => { ev.stopPropagation(); seleccionarPaso(Number(b.dataset.ir)); }));
    const elegido = $('.item.sel', contenido);
    if (elegido) elegido.scrollIntoView({ block: 'start' });   // con su detalle abajo, a la vista
  }

  function detallePaso(p, total) {
    const sens = (p.sensores || []).map((n) => G().sensores.find((s) => s.numero === n)).filter(Boolean)
      .map((s) => `<span class="n">${s.numero}</span>${esc(s.nombre)}`).join('<br>') || '<span class="tenue">ninguno (usa el registro)</span>';
    const preguntas = (p.preguntas || []).map((q) => `<li>${esc(q)}</li>`).join('');
    return `<div class="abierto"><dl class="detalle">
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
      </dl><div class="navegar">
        ${p.numero > 1 ? `<button data-ir="${p.numero - 1}">← Paso ${p.numero - 1}</button>` : ''}
        ${p.numero < total ? `<button data-ir="${p.numero + 1}">Paso ${p.numero + 1} →</button>` : ''}
      </div></div>`;
  }

  function seleccionarPaso(n) {
    const p = ctx.pasos().find((x) => x.numero === n);
    if (!p) return;
    seleccion = { tipo: 'paso', valor: n };
    SEL.resaltados.clear();
    for (const num of p.sensores || []) {
      const s = G().sensores.find((x) => x.numero === num);
      if (s) SEL.resaltados.add(s.id);
    }
    ctx.vista(p.zona);
    pintarPasos();
  }

  // ---------- Sensores ----------

  function respuestaPrueba(id) {
    const r = estado().ultima_orden;
    return pruebaEnviada && pruebaEnviada.sensor === id && r && r.n > pruebaEnviada.n
      ? `<div class="respuesta ${r.ok ? 'ok' : 'no'}"><span class="marca-r">${r.ok ? '✔' : '✖'}</span><span>${esc(r.detalle)}</span></div>` : '';
  }

  function botonesPruebaSensor(id) {
    const pruebas = PRUEBA_SENSOR[id] || [];
    if (!pruebas.length) return '';
    return `<section class="control" style="margin-top:12px"><h4>Ver la prueba de este sensor</h4>`
      + (demo() ? '<p>Demo grabada: para probarlo, abrir visor.bat.</p>' : '<p>Hace trabajar solo a este sensor; la cámara se queda mirándolo.</p>')
      + '<div class="rejilla c1">'
      + pruebas.map((pr, i) => `<button data-prueba="${i}" ${demo() ? 'disabled title="Demo grabada"' : ''}>▶ ${esc(pr[0])}</button>`).join('')
      + `</div><div id="respSensor" data-sensor="${esc(id)}">${respuestaPrueba(id)}</div></section>`;
  }

  function probarSensor(id, i) {
    const e = estado();
    const orden = { ...PRUEBA_SENSOR[id][i][1] };
    if (orden.tipo === 'intruso') orden.tipo = e.intruso ? 'intruso_off' : 'intruso_on';
    pruebaEnviada = { sensor: id, n: (e.ultima_orden && e.ultima_orden.n) || 0 };
    enviarOrden(orden);
    enfocarSensor(id);
  }

  function fichaSensor(s) {
    return `<dl class="detalle">
      <dt>Dónde</dt><dd>${esc(s.estacion)}</dd>
      <dt>Modelo propuesto</dt><dd>${esc(s.modelo)}</dd>
      <dt>Qué lo activa</dt><dd>${esc(s.fenomeno)}</dd>
      <dt>Recibe</dt><dd>${esc(s.entrada)}</dd>
      <dt>Entrega</dt><dd>${esc(s.salida)}</dd>
      <dt>Lectura ahora</dt><dd style="display:flex;align-items:center;gap:6px"><span data-led="${esc(s.id)}" class="${ledDe(s.id)}"></span><span data-lectura="${esc(s.id)}">${ctx.sensorActivo(s.id) ? 'activo' : 'inactivo'}</span></dd>
      <dt>Mensaje al PC</dt><dd><code>${esc(s.mensaje)}</code></dd>
      <dt>Cómo se simula</dt><dd>${esc(s.simulacion)}</dd>
      <dt>Rango</dt><dd>${esc(s.rango)}</dd>
      <dt>Tiempo de respuesta</dt><dd>${esc(s.tiempo_respuesta)}</dd>
      <dt>Error típico</dt><dd>${esc(s.error_tipico)}</dd>
      <dt>Cómo mitigarlo</dt><dd>${esc(s.mitigacion)}</dd>
      <dt>Conexión</dt><dd>${esc(s.conexion)}</dd></dl>`;
  }

  function pintarSensores() {
    const sel = seleccion.tipo === 'sensor' ? seleccion.valor : null;
    const grupos = {};
    for (const s of G().sensores) (grupos[s.subsistema] ||= []).push(s);
    let html = '<h3 class="titulo-pestana">Sensores</h3><p class="intro">Qué recibe cada sensor, qué entrega y qué mensaje termina llegando al PC. Clic para verlo en la escena y probarlo.</p>';
    for (const [nombre, lista] of Object.entries(grupos)) {
      html += `<section class="seccion"><h4>${esc(nombre[0].toUpperCase() + nombre.slice(1))} <span class="cuenta">${lista.length}</span></h4>`;
      for (const s of lista) {
        html += `<button class="item ${sel === s.id ? 'sel' : ''}" data-sensor="${esc(s.id)}"><span data-led="${esc(s.id)}" class="${ledDe(s.id)}"></span><span class="n">${s.numero}</span><span class="nombre">${esc(s.nombre)}</span></button>`;
        if (sel === s.id) html += `<div class="abierto">${fichaSensor(s)}${botonesPruebaSensor(s.id)}</div>`;
      }
      html += '</section>';
    }
    contenido.innerHTML = html;
    $$('[data-sensor]', contenido).forEach((d) => d.addEventListener('click', () => seleccionarSensor(d.dataset.sensor, true)));
    $$('[data-prueba]', contenido).forEach((b) => b.addEventListener('click', () => probarSensor(sel, Number(b.dataset.prueba))));
    const elegido = $('.item.sel', contenido);
    if (elegido) elegido.scrollIntoView({ block: 'start' });   // con su detalle abajo, a la vista
  }

  function seleccionarSensor(id, enfocar) {
    seleccion = { tipo: 'sensor', valor: id };
    SEL.resaltados.clear();
    SEL.resaltados.add(id);
    if (pestana !== 'sensores') marcarPestana('sensores');
    if (!panelAbierto()) mostrarPanel(true);
    if (enfocar) enfocarSensor(id);
    pintarSensores();
  }

  // ---------- Componentes (por subsistema, con sus sensores) ----------

  function subsistemaDe(c) {
    const i = SUBSISTEMAS.findIndex((g) => g.categoria === c.categoria);
    if (i >= 0) return i;
    const j = SUBSISTEMAS.findIndex((g) => g.zonas.includes(c.zona));
    return j >= 0 ? j : SUBSISTEMAS.length;
  }

  function pintarComponentes() {
    const sel = SEL.componente;
    const lista = G().componentes || [];
    const sensores = G().sensores;
    const total = lista.reduce((a, c) => a + c.cantidad, 0);
    const servos = lista.filter((c) => c.id.startsWith('servo')).reduce((a, c) => a + c.cantidad, 0);
    const grupos = SUBSISTEMAS.map((g) => ({ ...g, sensores: [], comps: [] }));
    grupos.push({ nombre: 'Otros', vista: null, sensores: [], comps: [] });
    for (const s of sensores) {
      const i = SUBSISTEMAS.findIndex((g) => g.sensor(s));
      grupos[i >= 0 ? i : grupos.length - 1].sensores.push(s);
    }
    for (const c of lista) grupos[subsistemaDe(c)].comps.push(c);

    let html = `<h3 class="titulo-pestana">Componentes</h3>
      <p class="intro">Lista de materiales por parte de la planta: ${total} piezas + ${sensores.length} sensores; ${servos} servos en el PCA9685 de 16 canales. Clic para verlo en la escena.</p>
      <div class="leyenda-insignias">
        <span class="par"><span class="rev simulado">simulado</span>la simulación hace lo que hace la pieza</span>
        <span class="par"><span class="rev efecto">efecto simulado</span>su efecto lo hace otra pieza</span>
        <span class="par"><span class="rev">solo visual</span>nada depende de ella</span>
        <span class="par"><span class="rev chica">3D</span>modelada</span>
        <span class="par"><span class="rev chica">N hilos</span>conexionado pin a pin</span>
      </div>`;
    for (const g of grupos) {
      if (!g.sensores.length && !g.comps.length) continue;
      const piezas = g.comps.reduce((a, c) => a + c.cantidad, 0);
      const cuenta = [g.sensores.length ? `${g.sensores.length} sensores` : '', `${piezas} piezas`].filter(Boolean).join(' · ');
      html += `<section class="seccion"><h4>${esc(g.nombre)} <span class="cuenta">${cuenta}</span>`
        + (g.vista ? `<button class="ir" data-vistagrupo="${g.vista}" title="Lleva la cámara a esta parte">ver zona</button>` : '') + '</h4>';
      for (const s of g.sensores) {
        const en3d = ctx.sensorEn3D(s.id);
        html += `<button class="item ${sensorEnComp === s.id ? 'sel' : ''}" data-sensorcomp="${esc(s.id)}"><span data-led="${esc(s.id)}" class="${ledDe(s.id)}"></span>`
          + `<span class="n">${s.numero}</span><span class="nombre">${esc(s.nombre)}<span class="insignias">`
          + (s.hilos ? `<span class="rev chica">${s.hilos} ${s.hilos === 1 ? 'hilo' : 'hilos'}</span>` : '') + (en3d ? '<span class="rev chica">3D</span>' : '')
          + '<span class="rev simulado">simulado</span></span></span></button>';
        if (sensorEnComp === s.id) {
          html += `<div class="abierto"><dl class="detalle"><dt>Modelo propuesto</dt><dd>${esc(s.modelo)}</dd><dt>Conexión</dt><dd>${esc(s.conexion)}</dd></dl>`
            + `<div class="navegar"><button data-fichasensor="${esc(s.id)}">Ficha completa y su prueba en Sensores</button></div></div>`;
        }
      }
      for (const c of g.comps) {
        const clase = { propia: 'simulado', efecto: 'efecto', no: '' }[c.simulacion] ?? '';
        const tiene = ctx.tiene3D(c.id);
        html += `<button class="item ${sel === c.id ? 'sel' : ''}" data-comp="${esc(c.id)}"><span class="n">${c.cantidad}×</span><span class="nombre">${esc(c.nombre)}<span class="insignias">`
          + (c.hilos ? `<span class="rev chica">${c.hilos} ${c.hilos === 1 ? 'hilo' : 'hilos'}</span>` : '')
          + (tiene ? '<span class="rev chica">3D</span>' : '<span class="rev pendiente chica">sin 3D</span>')
          + `<span class="rev ${clase}">${esc(c.estado)}</span></span></span></button>`;
        if (sel === c.id) {
          html += `<div class="abierto"><dl class="detalle"><dt>Tipo</dt><dd>${esc(c.categoria)}</dd><dt>Modelo propuesto</dt><dd>${esc(c.modelo)}</dd>
            <dt>Para qué sirve</dt><dd>${esc(c.funcion)}</dd>
            <dt>Estado en la simulación</dt><dd>${esc(c.estado)}${tiene ? '' : ' (todavía no dibujado)'}</dd>
            <dt>Conexión (pin a pin)</dt><dd>${esc(c.conexion)}</dd></dl></div>`;
        }
      }
      html += '</section>';
    }
    contenido.innerHTML = html;
    $$('[data-comp]', contenido).forEach((d) => d.addEventListener('click', () => seleccionarComponente(d.dataset.comp)));
    $$('[data-sensorcomp]', contenido).forEach((d) => d.addEventListener('click', () => {
      const id = d.dataset.sensorcomp;
      sensorEnComp = sensorEnComp === id ? null : id;
      SEL.componente = null;
      SEL.resaltados.clear();
      if (sensorEnComp) { SEL.resaltados.add(id); enfocarSensor(id); }
      pintarComponentes();
    }));
    $$('[data-fichasensor]', contenido).forEach((b) => b.addEventListener('click', () => {
      marcarPestana('sensores');
      seleccionarSensor(b.dataset.fichasensor, false);
    }));
    $$('[data-vistagrupo]', contenido).forEach((b) => b.addEventListener('click', () => ctx.vista(b.dataset.vistagrupo)));
    const elegido = $('.item.sel', contenido);
    if (elegido) elegido.scrollIntoView({ block: 'start' });   // con su detalle abajo, a la vista
  }

  function seleccionarComponente(id) {
    SEL.componente = SEL.componente === id ? null : id;
    sensorEnComp = null;
    SEL.resaltados.clear();
    if (SEL.componente && ctx.tiene3D(id)) { marcarVista(null); ctx.encuadrarComponente(id); }
    pintarComponentes();
  }

  // ---------- avisos grandes: demo grabada, sin conexión, sin internet ----------

  // null = todavia no se sabe. Se revisa cada 20 s y cuando el navegador avisa que cambio la red.
  // Antes (2026-09-27) el visor probaba UNA vez al arrancar, con la escena 3D todavia armandose (el
  // navegador ocupado varios segundos): el intento se pasaba del tiempo y decia "sin internet" con
  // internet. Ahora:
  // - En vivo decide la simulacion (`/api/internet`, el mismo chequeo en Python que usan el asistente
  //   y el dashboard): el visor y el Streamlit nunca se contradicen.
  // - En la demo (sin simulacion) prueba el navegador, con varios sitios y solo tras 2 fallos seguidos.
  async function alcanza(url) {
    try {
      // no-cors: no se lee la respuesta, solo se ve si el servidor se alcanza.
      await fetch(url, { mode: 'no-cors', cache: 'no-store', signal: AbortSignal.timeout(8000) });
      return true;
    } catch (e) { return false; }
  }

  async function revisarInternet() {
    let hay = null;
    if (!demo()) {
      try {
        const r = await fetch(ctx.base + 'api/internet', { cache: 'no-store', signal: AbortSignal.timeout(8000) });
        if (r.ok) hay = !!(await r.json()).internet;
      } catch (e) { /* supervisor viejo o caido: prueba el navegador */ }
    }
    if (hay === null) {
      const ok = navigator.onLine && (await alcanza('https://api.deepseek.com/') || await alcanza('https://www.google.com/generate_204'));
      fallosInternet = ok ? 0 : fallosInternet + 1;
      if (!ok && fallosInternet < 2) { setTimeout(revisarInternet, 4000); return; }   // una sola falla no basta
      hay = ok;
    }
    if (hay !== hayInternet) { hayInternet = hay; pintarModo(); }
  }

  let modoPintado = null;
  let temporizadorModo = null;
  function pintarModo() {
    const caja = $('#modo');
    const partes = [];
    if (demo()) {
      partes.push('<div class="demo"><b>▶ DEMO GRABADA</b><span>' + (ctx.enArchivo
        ? 'No es la simulación en vivo. Cuando la simulación de este PC arranque, esta pestaña pasa sola a en vivo.'
        : 'No es la simulación en vivo: es una corrida grabada que se repite.') + '</span></div>');
    } else if (fallos > 3) {
      partes.push('<div class="desconectado"><b>⚠ SIN CONEXIÓN CON LA SIMULACIÓN</b><span>Lo que se ve está congelado. '
        + 'Vuelva a abrir visor.bat.</span></div>');
    }
    // Sin internet lo dice el chip rojo de la barra (al lado de los ticks, como en el dashboard).
    const html = partes.join('');
    if (html !== modoPintado) {
      modoPintado = html;
      // Aviso nuevo: completo 10 s y despues compacto (no tapa la pantalla de la laptop).
      caja.innerHTML = html;
      caja.classList.remove('compacto');
      clearTimeout(temporizadorModo);
      temporizadorModo = setTimeout(() => { caja.classList.add('compacto'); colocarAvisos(); }, 10000);
    }
    // Centrado sobre la parte libre de la escena, debajo de las vistas.
    const izq = anchoTapado();
    caja.style.left = ((izq + window.innerWidth) / 2) + 'px';
    caja.style.top = ($('#vistas').getBoundingClientRect().bottom + 10) + 'px';
    colocarAvisos();
    const chipRed = $('#chipRed');
    chipRed.textContent = hayInternet === null ? 'revisando internet…' : hayInternet ? 'con internet' : 'SIN INTERNET';
    chipRed.className = 'chip ' + (hayInternet === false ? 'sinred' : hayInternet ? 'conred' : '');
    ctx.alCambiarInternet(hayInternet);
  }

  // Lo que tapan arriba la barra fija + la barra de vistas (todo el ancho) y el aviso de modo
  // ("DEMO GRABADA" / "SIN CONEXIÓN"), en píxeles de pantalla: la escena desvanece las etiquetas
  // 3D que caen debajo (se leían mal, encimadas con los botones). Se mide aquí (al acomodar y al
  // cambiar el aviso), no en cada cuadro: la escena solo lee esta lista.
  let zonasArriba = [];
  function medirZonasArriba() {
    const zonas = [{ izq: 0, der: window.innerWidth, abajo: $('#vistas').getBoundingClientRect().bottom }];
    const modo = $('#modo');
    if (modo.childElementCount) {
      const r = modo.getBoundingClientRect();
      if (r.width > 0) zonas.push({ izq: r.left, der: r.right, abajo: r.bottom });
    }
    zonasArriba = zonas;
  }

  // Los avisos de la línea (arriba a la derecha) van debajo del aviso grande, sin taparlo.
  function colocarAvisos() {
    medirZonasArriba();
    const modo = $('#modo');
    const arriba = $('#vistas').getBoundingClientRect().bottom + 10;
    $('#aviso').style.top = (modo.childElementCount ? modo.getBoundingClientRect().bottom + 8 : arriba) + 'px';
    // Leyenda de cables: a la derecha, debajo del último aviso de la línea (si hay) y sin bajar
    // más allá de la bitácora (o de la hoja del panel en pantalla angosta).
    const ley = $('#leyendaCables');
    const avisos = [...$('#aviso').children];
    const arribaLey = avisos.length ? avisos[avisos.length - 1].getBoundingClientRect().bottom + 8
      : (modo.childElementCount && window.innerWidth <= 900 ? modo.getBoundingClientRect().bottom + 8 : arriba);
    let tope = window.innerHeight - 12;
    const bit = $('#bitacora');
    if (bit && getComputedStyle(bit).display !== 'none') tope = Math.min(tope, bit.getBoundingClientRect().top - 10);
    if (panelAbierto() && window.innerWidth <= 900) tope = Math.min(tope, panel.getBoundingClientRect().top - 10);
    ley.style.top = arribaLey + 'px';
    ley.style.maxHeight = Math.max(44, tope - arribaLey) + 'px';
  }

  // Rectángulos de la pantalla que tapa la interfaz (barra, vistas, panel, avisos, bitácora,
  // leyenda de cables, ayuda): la escena no pone etiquetas 3D debajo de ellos (se leían cortadas
  // o quedaban tapadas, p. ej. el cartel META bajo el aviso de la cortina, 2026-09-28).
  function zonasOcupadas() {
    const sels = ['#barra', '#vistas', '#modo', '#aviso', '#bitacora', '#leyendaCables', '#ayuda'];
    if (panelAbierto()) sels.push('#panel');
    const out = [];
    for (const sel of sels) {
      const el = $(sel);
      if (!el || el.hidden) continue;
      // Los avisos son contenedores: cuenta cada aviso, no la caja vacía que los agrupa.
      const partes = (sel === '#aviso' || sel === '#vistas') ? [...el.children] : [el];
      for (const p of partes) {
        const r = p.getBoundingClientRect();
        if (r.width < 1 || r.height < 1) continue;
        out.push({ x0: r.left - 4, x1: r.right + 4, y0: r.top - 4, y1: r.bottom + 4 });
      }
    }
    return out;
  }
  // La parte de la pantalla donde se ve la escena sin nada encima: debajo de las vistas, a la
  // derecha del panel (pantalla ancha) o encima de la hoja del panel (pantalla angosta). Las
  // tomas de la cámara centran lo enfocado AQUÍ (a 900 px la hoja de abajo tapaba el carro).
  function zonaLibre() {
    const W = window.innerWidth, H = window.innerHeight;
    const z = { izq: 0, der: W, arriba: $('#vistas').getBoundingClientRect().bottom + 6, abajo: H };
    if (panelAbierto()) {
      const r = panel.getBoundingClientRect();
      if (W > 900) z.izq = r.right;
      else z.abajo = Math.max(z.arriba + 80, r.top - 6);
    }
    return z;
  }

  function vigilarInternet() {
    // La primera revision espera a que la escena termine de armarse.
    setTimeout(revisarInternet, 1500);
    setInterval(revisarInternet, 20000);
    window.addEventListener('online', revisarInternet);
    window.addEventListener('offline', revisarInternet);
  }

  // Vigia del visor portable: mientras muestra la demo grabada, pregunta cada 3 s si la simulacion
  // ya esta corriendo en este PC y, cuando responde, la pestaña pasa sola al visor en vivo.
  function vigilarSimulacion() {
    const chip = $('#chipEstado');
    const revisar = async () => {
      const url = await simulacionCorriendo(ctx.urlVivo);
      if (url) {
        chip.textContent = 'simulación encontrada · abriendo en vivo…';
        chip.className = 'chip corriendo';
        location.replace(url + location.search);
        return;
      }
      setTimeout(revisar, 3000);
    };
    revisar();
  }

  // ---------- estado de la simulación ----------

  function estadoNuevo(e) {
    const volvio = fallos > 3;
    fallos = 0;
    if (volvio) pintarModo();
    const chip = $('#chipEstado');
    chip.textContent = demo() ? (ctx.enArchivo ? 'demo grabada · esperando la simulación de este PC'
      : `demo grabada · ${e.linea || ''}`) : (e.linea || '—');
    chip.className = 'chip ' + (demo() ? 'demo' : (e.linea || ''));   // demo: ámbar, nunca verde
    $('#chipTick').textContent = `tick ${e.tick ?? '—'}`;
    // Cada aviso es una línea corta (título) y el detalle sale al pasar el ratón: el globo completo
    // tapaba el cartel META de la pista en la vista Todo (revisión visual, 2026-09-28). El detalle
    // también queda en la bitácora.
    const lista = [];
    if (e.cortina_activa) lista.push(['', 'Cortina activa · prensa detenida', 'la prensa sube y se detiene; tapa y empujador congelados. La cinta de monedas sigue.']);
    // Esperar al carrusel es normal (sale en la bitacora); el aviso grande es solo el tubo lleno.
    if (e.moneda_en_espera && (e.motivo_espera || 'tubo_lleno') === 'tubo_lleno') lista.push(['ambar', 'Tubo lleno · cinta de monedas en espera', 'la moneda espera en la descarga (E4) y la cinta de monedas se detiene hasta que un vaso reciba ese lote (no se descarta nada).']);
    // Montaje real: la placa en parada segura, con el motivo y cómo se sale (revisión 2026-09-29).
    if (e.motivo_parada) lista.push(['', `Estación en parada segura · ${e.motivo_parada.replace('_', ' ')}`,
      ({ sin_pc: 'la placa no oye al PC: sale sola cuando vuelve el latido.', pausa: 'pausa del PC: sale con Reanudar.',
         paro: 'paro de emergencia: sale con Iniciar.', error: 'error del firmware: revisar y salir con Reanudar.' })[e.motivo_parada]
      || 'la placa está detenida.']);
    if ((e.alarmas || []).includes('faltan_vasos')) lista.push(['ambar', 'Faltan vasos en la entrada', 'hay un lote listo y no hay vaso válido en el llenado; poner vasos en la entrada.']);
    const html = lista.map(([clase, titulo, detalle]) =>
      `<div class="${clase}" title="${esc(titulo + ': ' + detalle)}"><b>${titulo}</b><span class="detalle"><br>${detalle}</span></div>`).join('');
    const aviso = $('#aviso');
    if (aviso.innerHTML !== html) { aviso.innerHTML = html; colocarAvisos(); }
    actualizarRespuesta(e);
    const ahora = performance.now();
    if (ahora - ultimoPintado > 1000) {
      ultimoPintado = ahora;
      if (!contenido.firstChild) pintarPanel(); else refrescar();
    }
  }

  function falloConexion() {
    fallos++;
    if (fallos > 3) {
      const chip = $('#chipEstado');
      chip.textContent = 'sin conexión con el supervisor';
      chip.className = 'chip error';
    }
    pintarModo();
  }

  function eventos(lista) {
    for (const e of lista) {
      if (e.ev === 'alarma') bitacora.unshift(`<span class="src">   alarma</span> <b class="alarma">${esc(TEXTO_ALARMA[e.tipo] || e.tipo)}</b>`);
      const txt = describirEvento(e);
      if (txt) bitacora.unshift(`<span class="src">${esc(String(e.src).padStart(9, ' '))}</span> ${txt}`);
    }
    bitacora.length = Math.min(bitacora.length, 12);
    $('#eventos').innerHTML = bitacora.join('<br>') || '<span class="tenue">sin eventos todavía</span>';
  }

  // ---------- cables: botón y leyenda ----------

  let verCables = false;
  // La leyenda arranca plegada (una línea con los totales) y se recuerda si se abrió.
  function plegarLeyenda(si) {
    const ley = $('#leyendaCables');
    ley.classList.toggle('plegada', si);
    const b = ley.querySelector('header button');
    if (b) b.textContent = si ? 'Abrir' : 'Plegar';
    try { localStorage.setItem('leyendaPlegada', si ? '1' : '0'); } catch { /* nada */ }
  }
  function mostrarCables(si) {
    verCables = si;
    ctx.mostrarCables3D(si);
    $('#btnCables').classList.toggle('activo', si);
    document.body.classList.toggle('cables', si);
    const ley = $('#leyendaCables');
    ley.hidden = !si;
    colocarAvisos();
    if (!si || ley.dataset.hecha) return;
    ley.dataset.hecha = '1';
    const cx = G().conexiones;
    const { cables, tipos } = ctx.datosCables();
    const hex = (n) => '#' + n.toString(16).padStart(6, '0');
    const m = (x) => (x * 1.2).toFixed(2).replace('.', ',');
    const campo = cables.filter((c) => c.zona === 'planta' || c.zona === 'mesa');
    const total = campo.reduce((s, c) => s + c.largo, 0);
    const hilos = cx.cables.reduce((s, c) => s + c.hilos.length, 0);
    let html = `<header>Cableado <span class="cuenta">${cx.cables.length} cables · ${hilos} hilos · ${m(total)} m</span><button title="Pliega o abre la leyenda de cables">Abrir</button></header><div class="cuerpo">`
      + `<p class="tenue" style="margin:0 0 6px">${m(total)} m de cable de campo.</p>`
      + '<p class="tenue" style="margin:0 0 6px">Largos con 20 % de holgura para amarras y curvas; tabla completa en docs/conexiones.md.</p>';
    const porTipo = {};
    for (const c of campo) (porTipo[c.tipo] ||= []).push(c);
    for (const [tipo, lista] of Object.entries(porTipo)) {
      const t = tipos[tipo];
      html += `<details><summary><span class="muestra" style="background:${hex(t.color)}"></span>${esc(t.nombre)}<span class="cuenta-ley">&nbsp;·&nbsp;${lista.length}</span></summary>`;
      html += lista.map((c) => `<div class="ley-fila">${esc(c.nombre)}<span>${m(c.largo)} m</span></div>`).join('');
      html += '</details>';
    }
    const nombre = (ref) => `${esc(cx.dispositivos[ref.split('.', 1)[0]].nombre.split(' (')[0])} <b>${esc(ref.split('.', 1)[1])}</b>`;
    html += '<details><summary>Pin a pin</summary>';
    for (const c of cx.cables) {
      if (!c.hilos.length) continue;
      html += `<div class="ley-cable">${esc(c.nombre)}</div>`;
      html += c.hilos.map((h) => `<div class="ley-hilo"><span class="muestra" style="background:${esc(h.color)}"></span>` +
        `${nombre(h.de)} → ${nombre(h.a)} <span class="tenue">${esc(h.funcion)}</span></div>`).join('');
    }
    html += '</details></div>';
    ley.innerHTML = html;
    ley.querySelector('header button').addEventListener('click', () => plegarLeyenda(!ley.classList.contains('plegada')));
    let plegada = true;
    try { plegada = localStorage.getItem('leyendaPlegada') !== '0'; } catch { /* nada */ }
    plegarLeyenda(plegada);
  }

  // Después de armar los cables 3D: se recuerda si estaban a la vista; ?cables los abre.
  function iniciarCables() {
    let si = false;
    try { si = localStorage.getItem('verCables') === '1'; } catch { /* sin almacenamiento */ }
    if (new URLSearchParams(location.search).has('cables')) si = true;
    mostrarCables(si);
    $('#btnCables').addEventListener('click', () => {
      try { localStorage.setItem('verCables', verCables ? '0' : '1'); } catch { /* nada */ }
      mostrarCables(!verCables);
    });
  }

  // ---------- parámetros de la URL ----------

  // ?panel=0, ?paso=3, ?componente=<id> o ?sensor=<id>. Devuelve true si ya ubicó la cámara.
  function aplicarURL(q) {
    if (q.get('panel') === '0') mostrarPanel(false);
    if (q.get('paso')) {
      marcarPestana('pasos');
      seleccionarPaso(Number(q.get('paso')));
    } else if (q.get('componente')) {
      marcarPestana('componentes');
      seleccionarComponente(q.get('componente'));
    } else if (q.get('sensor')) {
      seleccionarSensor(q.get('sensor'), true);
    } else return false;
    ctx.saltarVuelo();
    return true;
  }

  // ---------- eventos de la página ----------

  $$('[data-vista]').forEach((b) => b.addEventListener('click', () => ctx.vista(b.dataset.vista)));
  $('#btnPanel').addEventListener('click', () => mostrarPanel(!panelAbierto()));
  $$('[data-pestana]').forEach((b) => b.addEventListener('click', () => {
    if (b.dataset.pestana === 'vivo') { SEL.resaltados.clear(); seleccion = { tipo: null, valor: null }; }
    if (b.dataset.pestana !== 'componentes') { SEL.componente = null; sensorEnComp = null; }
    mostrarPestana(b.dataset.pestana);
  }));
  const bitacoraCaja = $('#bitacora');
  const btnBitacora = $('#btnBitacora');
  function plegarBitacora(si) {
    bitacoraCaja.classList.toggle('plegada', si);
    btnBitacora.textContent = si ? 'Abrir' : 'Plegar';
    try { localStorage.setItem('bitacoraPlegada', si ? '1' : '0'); } catch { /* nada */ }
  }
  btnBitacora.addEventListener('click', () => plegarBitacora(!bitacoraCaja.classList.contains('plegada')));
  try { if (localStorage.getItem('bitacoraPlegada') === '1') plegarBitacora(true); } catch { /* nada */ }
  $('#eventos').innerHTML = '<span class="tenue">sin eventos todavía</span>';
  window.addEventListener('resize', acomodar);
  acomodar();

  return {
    // la escena pregunta
    anchoTapado, zonaLibre, zonasOcupadas,
    marcarVista,
    zonasArriba: () => zonasArriba,
    // arranque
    pintarPanel, pintarModo, vigilarInternet, vigilarSimulacion, iniciarCables, aplicarURL,
    // simulación
    estadoNuevo, falloConexion, eventos, limpiarBitacora: () => { bitacora.length = 0; },
    // clic en la escena
    seleccionarSensor,
  };
}
