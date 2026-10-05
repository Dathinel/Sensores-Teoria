// App del proyecto final: el recorrido interactivo de una pieza y los paneles "Pruébalo".
// Usa la API común (window.App, /comun/app.js). Los datos del recorrido salen del README
// ("El recorrido de una moneda") y de control/reglas.py (las causas de rechazo).

// ---------------------------------------------------------------------------
// Recorrido de una pieza por las 4 estaciones
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

function recorrido() {
  const cinta = document.getElementById('cinta');
  const ficha = document.getElementById('ficha');
  const explica = document.getElementById('explica');
  const casillas = [...cinta.querySelectorAll('.m-casilla')];
  const destino = document.getElementById('destino');
  const destinoSub = document.getElementById('destinoSub');
  let pieza = PIEZAS.moneda;
  let pos = 0;
  let auto = null;

  const centro = (i) => casillas[i].offsetLeft + casillas[i].offsetWidth / 2;
  const mover = () => { ficha.style.left = centro(pos) + 'px'; };

  function poner(nombre) {
    clearInterval(auto); auto = null;
    pieza = PIEZAS[nombre] || PIEZAS.moneda;
    pos = 0;
    ficha.className = 'm-ficha ' + pieza.clase;
    ficha.textContent = pieza.etiqueta;
    casillas.forEach((c) => c.classList.remove('mirando', 'paso-ok', 'paso-no', 'almacen', 'rechazo'));
    destino.textContent = 'Destino'; destinoSub.textContent = 'almacén o rechazo';
    casillas[0].classList.add('mirando');
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
        html += `<p>Pieza marcada como rechazo: la compuerta se queda apuntando a la <b>bandeja de rechazo</b>.</p>`;
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
      html = `<h3>Bandeja de rechazo</h3><p>Una sola bandeja para todo lo rechazado. El dashboard cuenta esta pieza en la causa `
        + `<span class="causa">${pieza.causa}</span> (decidida en ${ESTACIONES[pieza.en].titulo.split(' ·')[0]}).</p>`;
    }
    explica.innerHTML = html;
  }

  function avanzar() {
    if (pos >= 5) { clearInterval(auto); auto = null; return false; }
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
    }
    pintar();
    return pos < 5;
  }

  document.querySelectorAll('.m-pieza').forEach((b) => b.addEventListener('click', () => {
    document.querySelectorAll('.m-pieza').forEach((x) => x.classList.toggle('activa', x === b));
    poner(b.dataset.pieza);
  }));
  document.getElementById('avanzar').addEventListener('click', avanzar);
  document.getElementById('reiniciar').addEventListener('click', () => poner(Object.keys(PIEZAS).find((k) => PIEZAS[k] === pieza)));
  document.getElementById('todo').addEventListener('click', () => {
    if (pos >= 5) poner(Object.keys(PIEZAS).find((k) => PIEZAS[k] === pieza));
    clearInterval(auto);
    auto = setInterval(() => { if (!avanzar()) { clearInterval(auto); auto = null; } }, 1600);   // el ciclo real: 1,6 s
  });
  window.addEventListener('resize', mover);
  // La sección puede estar oculta (paso del asistente): se recoloca la ficha al mostrarla.
  App.on('paso', () => requestAnimationFrame(mover));
  poner('moneda');
}

// ---------------------------------------------------------------------------
// Paneles "Pruébalo"
// ---------------------------------------------------------------------------

function enlacesEnVivo() {
  // app.lanzar dice los puertos REALES (si el 8765 u 8501 estaban ocupados, usa otros: app/puertos.py).
  const caja = document.getElementById('enlacesVivo');
  const visor = document.getElementById('linkVisor');
  const dash = document.getElementById('linkDash');
  const texto = document.getElementById('puertosReales');
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
    else if (/visor/i.test(linea)) reales.visor = url;
    else return;
    mostrar();
  };
}

async function main() {
  await App.iniciar();
  App.checklist('#pide');
  const pasos = App.pasos('#pasos');
  document.querySelectorAll('[data-ir]').forEach((b) => b.addEventListener('click', () => pasos.ir(Number(b.dataset.ir))));
  document.querySelectorAll('[data-abrir]').forEach((a) => a.addEventListener('click', (ev) => { ev.preventDefault(); App.abrir(a.dataset.abrir); }));

  App.markdown('#arquitectura', 'README.md', { desde: '## La idea general', hasta: '### El recorrido de una moneda' });
  App.markdown('#recorridoMd', 'README.md', { desde: '### El recorrido de una moneda', sinTitulo: true });
  App.markdown('#estado', 'README.md', { desde: '## Estado del proyecto', sinTitulo: true });
  recorrido();

  App.panelEjecucion('#chequeo', 'chequeo', {
    queDeberiasVer: 'Una lista con ✓ (listo), ! (aviso) y ✗ (falta), cada una con cómo arreglarla. Con la instalación mínima es normal ver ✗ en Ollama, la voz o el firmware: no hacen falta para verlo. Si dice "Puerto 8765 … lo ocupa OTRO programa", no pasa nada: se usará el siguiente libre.',
  });

  const alLineaVivo = enlacesEnVivo();
  App.panelEjecucion('#vivo', 'vivo', {
    queVaAPasar: 'Arranca la simulación completa (escenario prueba_completa) y, apenas responden, abre en el navegador el visor 3D y el dashboard. Mientras corra, aquí abajo aparecen los enlaces con los puertos reales.',
    queHacer: [
      'Visor 3D: arrastra para girar, rueda para acercar. Pestaña Sensores → "Ver la prueba de este sensor"; botones de sabotaje (retirar un vaso, mano en la cortina…).',
      'Dashboard: barra lateral → "Probar un filtro" (cada filtro por separado, como pide la sustentación); pestañas Monedas y vasos, Carro y ruta, Asistente.',
      'Detener cierra la simulación y el dashboard.',
    ],
    queDeberiasVer: 'En el visor, el chip de arriba pasa de "conectando…" a "corriendo" y las piezas avanzan por la cinta; en el dashboard, "La línea está trabajando" y el valor aceptado subiendo.',
    alLinea: (texto) => alLineaVivo(texto),
  });

  const teclas = ['En la ventana de PyBullet: espacio pausa, r reinicia, q sale (o ciérrala).', 'Arrastra con el ratón para girar la cámara; rueda para acercar.'];
  App.panelEjecucion('#simFiltro', 'sim-filtro', { queHacer: teclas,
    queDeberiasVer: '18 piezas mezcladas, cada una con un rótulo de su material o su causa de rechazo; al final 7 en el almacén y 11 en rechazo, sin falsas aceptaciones.' });
  App.panelEjecucion('#simVasos', 'sim-vasos', { queHacer: teclas,
    queDeberiasVer: 'El vaso se verifica, se llena por lotes, se tapa y se prensa; con los sabotajes, la línea se detiene a tiempo.' });
  App.panelEjecucion('#simCarro', 'sim-carro', { queHacer: teclas,
    queDeberiasVer: 'El carro sigue la línea, rodea los tres muros, llega a la meta y vuelve de reversa al muelle.' });
  App.panelEjecucion('#simTodo', 'sim-todo', { queHacer: [...teclas, 'Se abren DOS ventanas: la planta y el carro (PyBullet permite una por proceso).'],
    queDeberiasVer: 'La planta y el carro en la misma corrida.' });

  App.panelEjecucion('#asistente', 'asistente', {
    queHacer: 'Escribe en la caja de abajo y pulsa Enter, o usa una de las sugerencias.',
    queDeberiasVer: 'Cada respuesta con las cifras de la última corrida guardada y, al final, [respondió: local] (las reglas).',
    sugerencias: ['¿cuántas monedas se aceptaron?', '¿cuántas piezas se rechazaron y por qué?', '¿qué sensor detecta el metal?',
      'cuanto hay de 500', '¿cuánto cuesta construir el proyecto?', 'avanza 20 cm'],
  });

  App.panelEjecucion('#pruebas', 'pruebas', {
    queDeberiasVer: 'Una fila de puntos que avanza hasta 100 % y al final "936 passed" (con la instalación mínima se omiten 2, "skipped": las que compilan el firmware con mpy-cross). Tarda unos 4 minutos.',
  });

  document.getElementById('abrirPortable').addEventListener('click', () => App.abrir('visor-portable.html'));
  document.getElementById('cargarPortable').addEventListener('click', (ev) => {
    const marco = document.getElementById('marcoPortable');
    if (!marco.firstChild) {
      const f = document.createElement('iframe');
      f.src = App.url('visor-portable.html');
      f.title = 'Visor 3D portable (demo grabada)';
      f.setAttribute('allow', 'fullscreen');
      marco.appendChild(f);
    }
    marco.hidden = false;
    ev.currentTarget.textContent = 'Visor cargado (demo grabada)';
  });

  App.imagen(document.querySelector('.m-capturas'));
}

main().catch((e) => { console.error(e); App.aviso && App.aviso('No se pudo iniciar la app: ' + e.message, 'error'); });
