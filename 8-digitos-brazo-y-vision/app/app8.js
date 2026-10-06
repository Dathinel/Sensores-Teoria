// App del tema 8: Punto 1 (teclado -> brazo que dibuja) y Punto 2 (dibujo -> CNN -> ESP-A -> SPI/UART -> ESP-B -> OLED).
// Usa la API común window.App (/comun/app.js): App.marco arma la ventana tipo Docker Desktop (cabecera,
// barra lateral, una sección a la vez). Si alguna función de la API no está, la página sigue funcionando
// (las secciones quedan una debajo de otra).
"use strict";

const CARPETA = "8-digitos-brazo-y-vision";
const P2 = "punto-2-reconocimiento-oled-spi";
const tieneApp = (nombre) => typeof window.App === "object" && window.App && typeof window.App[nombre] === "function";
const $ = (id) => document.getElementById(id);

// Los previews (iframes) se cargan recién cuando se ve su sección (no gastar páginas al abrir).
function cargarIframes(raiz) {
  if (!raiz) return;
  raiz.querySelectorAll("iframe[data-src]").forEach((f) => { if (!f.getAttribute("src")) f.setAttribute("src", f.dataset.src); });
}

// Ampliar imágenes si App.imagen no está
function lightboxPropio(img) {
  img.addEventListener("click", () => {
    const capa = document.createElement("div"); capa.className = "t8-lightbox";
    const grande = document.createElement("img"); grande.src = img.src; grande.alt = img.alt;
    capa.appendChild(grande); capa.addEventListener("click", () => capa.remove());
    document.body.appendChild(capa);
  });
}

// ================================================================ Punto 1: trayectoria interactiva
// Copiado de TRAZOS_DIGITOS en punto-1-teclado-brazo-dibujando/brazo_dibuja.py (u horizontal, v vertical, v=1 arriba).
const TRAZOS = {
  0: [[0.2, 0], [0, 0.2], [0, 0.8], [0.2, 1], [0.8, 1], [1, 0.8], [1, 0.2], [0.2, 0]],
  1: [[0.3, 0.8], [0.5, 1], [0.5, 0]],
  2: [[0, 0.8], [0.3, 1], [0.7, 1], [1, 0.8], [1, 0.55], [0, 0.2], [0, 0], [1, 0]],
  3: [[0, 1], [1, 1], [0.5, 0.55], [1, 0.15], [0.6, 0], [0.1, 0.1]],
  4: [[0.7, 0], [0.7, 1], [0, 0.35], [1, 0.35]],
  5: [[1, 1], [0, 1], [0, 0.55], [0.8, 0.55], [1, 0.35], [0.8, 0], [0, 0.1]],
  6: [[0.9, 0.9], [0.3, 1], [0, 0.6], [0, 0.2], [0.3, 0], [0.7, 0], [1, 0.25], [0.7, 0.5], [0.2, 0.5]],
  7: [[0, 1], [1, 1], [0.4, 0]],
  8: [[0.5, 0.5], [0.2, 0.65], [0.2, 0.9], [0.5, 1], [0.8, 0.9], [0.8, 0.65], [0.5, 0.5],
      [0.2, 0.35], [0.2, 0.1], [0.5, 0], [0.8, 0.1], [0.8, 0.35], [0.5, 0.5]],
  9: [[0.3, 0.1], [0.7, 0], [1, 0.35], [1, 0.75], [0.7, 1], [0.3, 0.9], [0.3, 0.5], [0.8, 0.5]],
};
const CENTRO_J1 = 0.0, CENTRO_J2 = 1.0, RANGO_J1 = 0.35, RANGO_J2 = 0.35, PUNTOS_POR_TRAMO = 8;

function densificar(trazo) {
  const out = [];
  for (let i = 0; i < trazo.length - 1; i++) {
    const [u0, v0] = trazo[i], [u1, v1] = trazo[i + 1];
    for (let k = 0; k < PUNTOS_POR_TRAMO; k++) { const t = k / PUNTOS_POR_TRAMO; out.push([u0 + (u1 - u0) * t, v0 + (v1 - v0) * t]); }
  }
  out.push(trazo[trazo.length - 1]);
  return out;
}

function iniciarTrazo() {
  const svg = $("trazo-svg"), botones = $("trazo-botones"), lectura = $("trazo-lectura");
  if (!svg) return;
  const NS = "http://www.w3.org/2000/svg";
  const nuevo = (tag, attrs) => { const e = document.createElementNS(NS, tag); Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v)); svg.appendChild(e); return e; };
  nuevo("rect", { x: 0, y: 0, width: 1, height: 1, fill: "none", stroke: "#262b31", "stroke-width": 0.008, "stroke-dasharray": "0.03 0.02" });
  const linea = nuevo("polyline", { fill: "none", stroke: "#e8b931", "stroke-width": 0.045, "stroke-linecap": "round", "stroke-linejoin": "round" });
  const puntos = nuevo("g", {});
  const punta = nuevo("circle", { r: 0.035, fill: "#fff", stroke: "#e8b931", "stroke-width": 0.012 });
  let animacion = null;
  function dibujar(d) {
    [...botones.children].forEach((b) => b.classList.toggle("activo", b.dataset.d === String(d)));
    const base = TRAZOS[d], pts = densificar(base);
    puntos.innerHTML = "";
    base.forEach(([u, v]) => {
      const c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", u); c.setAttribute("cy", 1 - v); c.setAttribute("r", 0.018); c.setAttribute("fill", "#4f8fce");
      puntos.appendChild(c);
    });
    if (animacion) cancelAnimationFrame(animacion);
    const inicio = performance.now();   // ~25 ms por posición, como los 6 pasos de física por punto del script
    const paso = (ahora) => {
      const n = Math.max(1, Math.min(pts.length, 1 + Math.floor((ahora - inicio) / 25)));
      linea.setAttribute("points", pts.slice(0, n).map(([u, v]) => u + "," + (1 - v)).join(" "));
      const [u, v] = pts[n - 1];
      punta.setAttribute("cx", u); punta.setAttribute("cy", 1 - v);
      const j1 = CENTRO_J1 + (u - 0.5) * 2 * RANGO_J1, j2 = CENTRO_J2 - (v - 0.5) * 2 * RANGO_J2;
      const grados = (r) => (r * 180 / Math.PI).toFixed(1) + "°";
      lectura.textContent = `Dígito ${d} · posición ${n} de ${pts.length} · base ${grados(j1)} · codo ${grados(j2)}` + (n < pts.length ? "" : " · listo");
      if (n < pts.length) animacion = requestAnimationFrame(paso);
    };
    animacion = requestAnimationFrame(paso);
  }
  for (let d = 0; d <= 9; d++) {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = d; b.dataset.d = d;
    b.addEventListener("click", () => dibujar(d));
    botones.appendChild(b);
  }
  dibujar(7);
}

// ================================================================ Punto 2: la red en vivo
// Mismas reglas que reconocer_digito.py: un cuadro con confianza < 60 % cuenta como "nada"; se
// confirma si el ganador tiene >= 80 % de la ventana de 15 (12 de 15); DIGIT:n se manda una sola vez.
const TAM_VENTANA = 15, UMBRAL_CONFIANZA = 60, UMBRAL_CONFIRMACION = 0.8;
const Red = {
  capas: null, fuente: "web", seccion: null,
  ventana: [], enviado: null, cache: null, sucio: true,
};

function iniciarRed() {
  Red.seccion = $("s-p2-red");
  const lienzo = $("lienzo"); if (!lienzo) return;
  const ctx = lienzo.getContext("2d", { willReadFrequently: true });
  const limpiar = () => { ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, 360, 360); Red.sucio = true; };
  limpiar();
  // Lápiz: como GROSOR_LAPIZ = lado // 16 = 22 px en el recuadro de 360 px de reconocer_digito.py
  ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.lineWidth = 22; ctx.strokeStyle = "#000";
  let ant = null;
  const pos = (e) => { const r = lienzo.getBoundingClientRect(); return [(e.clientX - r.left) * 360 / r.width, (e.clientY - r.top) * 360 / r.height]; };
  lienzo.addEventListener("pointerdown", (e) => {
    if (e.button === 2) { limpiar(); return; }
    try { lienzo.setPointerCapture(e.pointerId); } catch (err) { /* nada */ }
    ant = pos(e);
    ctx.beginPath(); ctx.arc(ant[0], ant[1], 11, 0, 7); ctx.fillStyle = "#000"; ctx.fill(); Red.sucio = true;
  });
  lienzo.addEventListener("pointermove", (e) => {
    if (!ant) return; const p = pos(e);
    ctx.beginPath(); ctx.moveTo(ant[0], ant[1]); ctx.lineTo(p[0], p[1]); ctx.stroke(); ant = p; Red.sucio = true;
  });
  const soltar = () => { ant = null; };
  lienzo.addEventListener("pointerup", soltar); lienzo.addEventListener("pointercancel", soltar);
  lienzo.addEventListener("contextmenu", (e) => e.preventDefault());
  $("borrar").addEventListener("click", limpiar);
  Red.ctx = ctx;

  // Estructura de las etapas 3, 4 y 5
  const mapas = $("mapas");
  Red.mapas = Array.from({ length: 32 }, (_, i) => {
    const c = document.createElement("canvas"); c.width = 26; c.height = 26; c.className = "pixelada"; c.title = "Filtro " + (i + 1);
    mapas.appendChild(c); return c;
  });
  const barras = $("barras");
  Red.barras = Array.from({ length: 10 }, (_, d) => {
    const f = document.createElement("div"); f.className = "barra-fila";
    f.innerHTML = `<span class="barra-d">${d}</span><span class="barra-fondo"><span class="barra-relleno"></span><span class="barra-umbral"></span></span><span class="barra-pct">0 %</span>`;
    barras.appendChild(f); return f;
  });
  const votos = $("votos");
  Red.celdas = Array.from({ length: TAM_VENTANA }, () => { const c = document.createElement("div"); c.className = "voto ve vacio"; votos.appendChild(c); return c; });

  // Pesos de la red (los mismos de modelo_mnist_cnn.h5, en int8)
  fetch("cnn-pesos.bin").then((r) => { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); })
    .then((b) => { Red.capas = window.CNN.leerPesos(b); Red.sucio = true; })
    .catch(() => { $("et5-estado").textContent = "No se pudieron cargar los pesos de la red (cnn-pesos.bin)."; });

  // Fuente de los datos: el navegador o el programa de Python
  document.querySelectorAll(".red-fuente button").forEach((b) => b.addEventListener("click", () => cambiarFuente(b.dataset.fuente)));
  pintarOled(null);
  setInterval(tic, 100);   // ~10 cuadros por segundo, como una cámara lenta
}

function cambiarFuente(f) {
  Red.fuente = f;
  document.querySelectorAll(".red-fuente button").forEach((b) => b.classList.toggle("activa", b.dataset.fuente === f));
  $("red-py").hidden = f !== "py";
  $("lienzo").hidden = f === "py"; $("py-recuadro").hidden = f !== "py";
  $("et1-pie").hidden = f === "py";
  $("et1-tit").textContent = f === "py" ? "El recuadro del programa" : "Dibuja aquí";
  $("red-nota").hidden = f === "py";
  Red.ventana = []; Red.enviado = null; Red.sucio = true;
  try { localStorage.setItem("t8-fuente", f); } catch (e) { /* nada */ }
}

const visible = () => Red.seccion && !Red.seccion.hidden && Red.seccion.offsetParent !== null;

function tic() {
  if (!visible()) return;
  if (Red.fuente === "py") { leerEstadoPython(); return; }
  if (!Red.capas) return;
  // 1-4: preprocesar y clasificar el lienzo (solo si cambió; si no, el mismo resultado de antes,
  // igual que la cámara mirando una hoja quieta)
  if (Red.sucio) {
    Red.sucio = false;
    const datos = Red.ctx.getImageData(0, 0, 360, 360).data, gris = new Uint8Array(360 * 360);
    for (let i = 0; i < gris.length; i++) gris[i] = datos[i * 4];
    const pre = window.CNN.preprocesar(gris, 360);
    if (!pre) Red.cache = null;
    else {
      const r = window.CNN.predecir(Red.capas, pre.entrada);
      const p = r.probabilidades, clase = p.indexOf(Math.max(...p)), conf = p[clase] * 100;
      Red.cache = { entrada: pre.entrada, conv1: r.conv1, probs: p, clase: conf >= UMBRAL_CONFIANZA ? clase : null, conf };
    }
  }
  const c = Red.cache;
  // 5: ventana de votos
  Red.ventana.push(c ? c.clase : null); if (Red.ventana.length > TAM_VENTANA) Red.ventana.shift();
  const v = votar(Red.ventana);
  // 6: mandar solo cuando el confirmado cambia
  let recienEnviado = false;
  if (v.confirmado !== null) { if (v.confirmado !== Red.enviado) { Red.enviado = v.confirmado; recienEnviado = true; } }
  else Red.enviado = null;
  pintar({ entrada: c && c.entrada, conv1: c && c.conv1, probs: c && c.probs, claseFrame: c ? c.clase : null, conf: c ? c.conf : 0,
           ventana: Red.ventana, ...v, enviado: Red.enviado, recienEnviado, esp: null });
}

function votar(ventana) {
  const conteo = new Map();
  ventana.forEach((x) => conteo.set(x, (conteo.get(x) || 0) + 1));
  let ganador = null, max = 0;
  conteo.forEach((n, x) => { if (n > max) { max = n; ganador = x; } });
  const proporcion = ventana.length ? max / ventana.length : 0;
  return { ganador, proporcion, confirmado: ganador !== null && proporcion >= UMBRAL_CONFIRMACION ? ganador : null };
}

// ---- programa de Python: lee el estado que escribe reconocer_digito.py --estado estado_en_vivo.json
let pidiendo = false, ultimoT = 0, enviadoPy = null;
async function leerEstadoPython() {
  if (pidiendo) return; pidiendo = true;
  try {
    const r = await fetch(`/repo/${CARPETA}/${P2}/estado_en_vivo.json?t=${Date.now()}`, { cache: "no-store" });
    if (!r.ok) throw new Error("sin archivo");
    const d = await r.json();
    const edad = Date.now() / 1000 - d.t;
    if (d.terminado) { esperaPy("El programa terminó. Vuelve a pulsar Abrir el lienzo (o la cámara) para seguir."); return; }
    if (edad > 4) { esperaPy("Esperando datos del programa… Pulsa Abrir el lienzo (o la cámara) y dibuja en su ventana."); return; }
    $("red-espera").hidden = true;
    if (d.t === ultimoT) return; ultimoT = d.t;
    pintarRecuadro(d.recuadro56);
    const entrada = d.entrada28 ? Float32Array.from({ length: 784 }, (_, i) => parseInt(d.entrada28.substr(i * 2, 2), 16) / 255) : null;
    const conv1 = entrada && Red.capas ? window.CNN.predecir(Red.capas, entrada).conv1 : null;
    const recienEnviado = d.confirmado !== null && d.confirmado !== enviadoPy;
    enviadoPy = d.confirmado;
    pintar({ entrada, conv1, probs: d.probabilidades, claseFrame: d.clase_frame, conf: d.confianza_frame, ventana: d.ventana,
             ganador: null, proporcion: d.proporcion, confirmado: d.confirmado, enviado: d.confirmado, recienEnviado,
             esp: { estado: d.esp_a, confirmacion: d.confirmacion_esp_a } });
  } catch (e) {
    esperaPy("Esperando datos del programa… Pulsa Abrir el lienzo (o la cámara) y dibuja en su ventana.");
  } finally { pidiendo = false; }
}
function esperaPy(texto) { const e = $("red-espera"); e.hidden = false; e.textContent = texto; }
function pintarRecuadro(hex) {
  const c = $("py-recuadro"), ctx = c.getContext("2d"), img = ctx.createImageData(56, 56);
  for (let i = 0; i < 56 * 56; i++) { const v = parseInt(hex[i] || "f", 16) * 17; img.data.set([v, v, v, 255], i * 4); }
  ctx.putImageData(img, 0, 0);
}

// ---- dibujar las etapas 2 a 6
function pintar(s) {
  // 2: entrada 28x28
  const c28 = $("c28").getContext("2d"), img = c28.createImageData(28, 28);
  for (let i = 0; i < 784; i++) { const v = s.entrada ? Math.round(s.entrada[i] * 255) : 0; img.data.set([v, v, v, 255], i * 4); }
  c28.putImageData(img, 0, 0);
  // 3: los 32 mapas de la capa 1 (26x26, cada uno normalizado a su máximo para que se vea)
  Red.mapas.forEach((cv, k) => {
    const x = cv.getContext("2d"), im = x.createImageData(26, 26);
    let max = 1e-6; if (s.conv1) for (let i = 0; i < 676; i++) max = Math.max(max, s.conv1[i * 32 + k]);
    for (let i = 0; i < 676; i++) {
      const v = s.conv1 ? s.conv1[i * 32 + k] / max : 0;
      im.data.set([Math.round(12 + 67 * v), Math.round(16 + 193 * v), Math.round(20 + 177 * v), 255], i * 4);   // de oscuro a cian
    }
    x.putImageData(im, 0, 0);
  });
  // 4: barras de probabilidad
  const ganadorFrame = s.probs ? s.probs.indexOf(Math.max(...s.probs)) : -1;
  Red.barras.forEach((f, d) => {
    const p = s.probs ? s.probs[d] : 0;
    f.querySelector(".barra-relleno").style.width = (p * 100).toFixed(1) + "%";
    f.querySelector(".barra-pct").textContent = s.probs ? (p * 100 >= 99.95 ? "100" : (p * 100).toFixed(p * 100 < 10 ? 1 : 0)) + " %" : "–";
    f.classList.toggle("gana", d === ganadorFrame);
    f.classList.toggle("vota", d === ganadorFrame && p * 100 >= UMBRAL_CONFIANZA);
  });
  // 5: votos
  const ventana = s.ventana || [];
  const desde = TAM_VENTANA - ventana.length;
  Red.celdas.forEach((c, i) => {
    const x = i < desde ? undefined : ventana[i - desde];
    c.className = "voto ve" + (x === undefined ? " vacio" : x === null ? " nada" : "") + (x !== undefined && x !== null && x === s.confirmado ? " gana" : "");
    c.textContent = x === undefined ? "" : x === null ? "·" : x;
    c.title = x === undefined ? "todavía sin cuadro" : x === null ? "sin dígito o confianza < 60 %: cuenta como nada" : "este cuadro votó " + x;
  });
  // La barra muestra cuánto lleva el dígito más votado (no "nada"): con el lienzo vacío, "nada"
  // gana 15 de 15 y la proporción del ganador sería 100 %, lo que se leía como "casi confirmado".
  // Con un dígito ganando es el mismo número que la proporción de reconocer_digito.py.
  const cuenta = {};
  ventana.forEach((x) => { if (x !== null && x !== undefined) cuenta[x] = (cuenta[x] || 0) + 1; });
  const mejor = Math.max(0, ...Object.values(cuenta));
  const pct = ventana.length ? Math.round(mejor / ventana.length * 100) : 0;
  $("prop-relleno").style.width = pct + "%";
  $("prop-relleno").className = s.confirmado !== null && s.confirmado !== undefined ? "ok" : "";
  $("prop-txt").textContent = pct + " %";
  const est = $("et5-estado");
  if (s.confirmado !== null && s.confirmado !== undefined) { est.className = "et-estado ok"; est.textContent = `CONFIRMADO: ${s.confirmado}`; }
  else if (s.entrada) { est.className = "et-estado leyendo"; est.textContent = `Leyendo… (este cuadro: ${s.claseFrame === null || s.claseFrame === undefined ? "nada" : s.claseFrame})`; }
  else { est.className = "et-estado"; est.textContent = Red.fuente === "py" ? "Buscando dígito en el recuadro…" : "Dibuja un dígito."; }
  // 6: mensaje y OLED
  const hay = s.confirmado !== null && s.confirmado !== undefined;
  $("msg-digit").textContent = hay ? `DIGIT:${s.confirmado}` : "DIGIT:–";
  $("msg-digit").classList.toggle("ok", hay);
  const cadena = $("cadena");
  cadena.classList.toggle("activa", hay);
  if (s.recienEnviado) { cadena.classList.remove("viaja"); void cadena.offsetWidth; cadena.classList.add("viaja"); pintarOled(s.confirmado); }
  if (!hay && Red.fuente === "web") { /* la OLED se queda con el último dígito, como la real */ }
  const pie = $("et6-pie");
  if (s.esp) {
    pie.innerHTML = s.esp.estado === "conectado"
      ? `ESP-A conectado. ${s.esp.confirmacion !== null && s.esp.confirmacion !== undefined ? "Confirmó el reenvío de: <b>" + s.esp.confirmacion + "</b>" : "Esperando su REENVIADO:n…"}`
      : "ESP-A <b>no conectado</b> (normal sin la placa): el programa reconoce igual y no manda nada. La OLED de aquí muestra lo que mostraría.";
  }
}

function pintarOled(d) {
  const c = $("oled"), x = c.getContext("2d");
  x.fillStyle = "#000"; x.fillRect(0, 0, 128, 64);
  x.fillStyle = "#bfe9ff"; x.textBaseline = "top";
  x.font = "8px monospace"; x.fillText("Digito reconocido:", 2, 2);
  if (d !== null && d !== undefined) { x.font = "bold 40px monospace"; x.fillText(String(d), 52, 18); }
}

// ================================================================ barra "se está abriendo"
// Los programas con ventana propia (PyBullet, OpenCV) tardan en aparecer: el panel común dice
// "en marcha", y esta barra cuenta cuánto suele tardar hasta que el programa avisa que ya abrió
// (una línea de su salida que cumpla `listo`).
function barraArranque(el, { texto, seg, listo, alAbrir }) {
  const caja = document.createElement("div"); caja.className = "t8-arranque"; caja.hidden = true;
  caja.innerHTML = '<div class="t8-arr-txt"></div><div class="t8-arr-barra"><div></div></div>';
  let t0 = 0, reloj = null, abierto = false;
  const pintar = () => {
    const s = (Date.now() - t0) / 1000, f = s <= seg ? 0.92 * s / seg : 0.92 + 0.07 * (1 - Math.exp(-(s - seg) / seg));
    caja.querySelector(".t8-arr-barra div").style.width = Math.round(f * 100) + "%";
    caja.querySelector(".t8-arr-txt").innerHTML = `<b>${texto}</b> lleva ${Math.round(s)} s ` + (s <= seg * 1.2 ? `de ~${seg} s` : "(está tardando más de lo normal; si la salida sigue avanzando, va bien)");
  };
  const parar = () => { clearInterval(reloj); reloj = null; caja.hidden = true; };
  return {
    montar() { const ref = el.querySelector(".app-panel-estado"); if (ref) ref.after(caja); else el.prepend(caja); },
    alEstado(t) {
      if (!t) return;
      if (t.estado === "lanzada" && !abierto && !reloj) { t0 = Date.now(); caja.hidden = false; pintar(); reloj = setInterval(pintar, 500); }
      if (["terminada", "error", "detenida"].includes(t.estado)) { parar(); abierto = false; }
    },
    alLinea(x) { if (!abierto && listo.test(x)) { abierto = true; parar(); alAbrir && alAbrir(); } },
  };
}

// ================================================================ arranque
async function arrancar() {
  iniciarTrazo();
  iniciarRed();
  try { const f = localStorage.getItem("t8-fuente"); if (f === "py") cambiarFuente("py"); } catch (e) { /* nada */ }

  // Explicaciones del README: se cargan al abrir cada "Leer…"
  document.querySelectorAll("details.mas").forEach((det) => {
    det.addEventListener("toggle", () => {
      const caja = det.querySelector(".md");
      if (!det.open || caja.dataset.cargado) return;
      caja.dataset.cargado = "1";
      if (tieneApp("markdown")) Promise.resolve(App.markdown(caja, caja.dataset.md, { desde: caja.dataset.desde, hasta: caja.dataset.hasta })).catch(() => { caja.textContent = "No se pudo cargar el README."; });
      else caja.innerHTML = 'La explicación completa está en el <a href="/repo/' + CARPETA + '/' + caja.dataset.md + '" target="_blank" rel="noopener">README del punto</a>.';
    });
  });
  document.querySelectorAll("img.ampliable").forEach((img) => { if (tieneApp("imagen")) App.imagen(img); else lightboxPropio(img); });

  if (tieneApp("iniciar")) { try { await App.iniciar(); } catch (e) { console.warn("App.iniciar:", e); } }

  // Marco tipo Docker Desktop: barra lateral con las secciones, agrupadas por punto
  let marco = null;
  if (tieneApp("marco")) {
    marco = App.marco({ titulo: "Dígitos: brazo que dibuja + visión que reconoce", num: "8",
      alCambiar: (i, sec) => cargarIframes(sec) });
    const lateral = document.querySelector(".app-marco-lateral");
    if (lateral) {
      const grupo = (texto, clase, antesDe) => { const g = document.createElement("div"); g.className = "t8-grupo " + clase; g.textContent = texto; lateral.insertBefore(g, antesDe); };
      const items = [...lateral.querySelectorAll(".app-marco-item")];
      const secs = marco.secciones;
      const i1 = secs.findIndex((s) => s.dataset.punto === "p1"), i2 = secs.findIndex((s) => s.dataset.punto === "p2");
      secs.forEach((s, i) => { if (s.dataset.punto) items[i].classList.add("t8-" + s.dataset.punto); });
      if (i1 >= 0) grupo("Punto 1 · teclado + brazo", "g1", items[i1]);
      if (i2 >= 0) grupo("Punto 2 · visión + OLED", "g2", items[i2]);
    }
    cargarIframes(marco.secciones[marco.actual]);
  } else {
    document.querySelectorAll("iframe[data-src]").forEach((f) => f.setAttribute("src", f.dataset.src));
  }
  document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => {
    if (marco) marco.ir(b.dataset.ir); else { const s = $(b.dataset.ir); if (s) s.scrollIntoView({ behavior: "smooth" }); }
  }));

  if (tieneApp("checklist")) App.checklist($("checklist"));

  const paneles = {
    "run-p1-sim": ["p1-sim", {
      titulo: "Brazo dibujando en PyBullet",
      queVaAPasar: "Se abre el simulador PyBullet con el brazo de brazo.urdf (puede quedar detrás de esta ventana: búscalo en la barra de tareas). Sin ESP32, el programa avisa que no encontró COM7 y sigue con 10 botones en la ventana.",
      queHacer: [
        "Busca a la derecha de la ventana el panel con 10 botones, del 0 al 9 (si no lo ves, agranda la ventana).",
        "Haz clic en uno: el brazo borra el dígito anterior y dibuja el nuevo con una línea amarilla. El 8 tarda unos 2 segundos; el 1, menos de medio.",
        "Para mover la cámara: la rueda del mouse acerca, Ctrl + arrastrar gira.",
        "Para terminar, cierra la ventana (o pulsa Detener aquí).",
      ],
      queDeberiasVer: "Aquí abajo: 'No se pudo abrir COM7' y 'Sigue sin ESP32: usa los botones 0-9 de la ventana', y por cada botón 'Dibujando el digito n...' y 'Listo.'",
      botonTexto: "Iniciar el brazo",
    }],
    "run-p2-mouse": ["p2-mouse", {
      titulo: "Dibujar con el mouse (sin cámara)",
      queVaAPasar: "",
      queHacer: ["Se abre un lienzo blanco aparte (~20-60 s). Dibuja un dígito GRANDE dentro de su recuadro; clic derecho o c borra, q sale."],
      queDeberiasVer: "",
      botonTexto: "Abrir el lienzo",
    }],
    "run-p2-camara": ["p2-camara", {
      titulo: "Con la cámara",
      queVaAPasar: "",
      queHacer: ["Muestra un dígito escrito con marcador en una hoja blanca, dentro del recuadro, quieto y con buena luz. q sale. La imagen no sale de este PC."],
      queDeberiasVer: "",
      botonTexto: "Encender la cámara",
    }],
    "run-p2-entrenar": ["p2-entrenar", {
      titulo: "Volver a entrenar la red (sobrescribe el modelo)",
      queDeberiasVer: "Una línea por cada una de las 10 pasadas (épocas) con su precisión, que debería terminar cerca del 99 %. Al final se guarda el modelo nuevo.",
      botonTexto: "Entrenar de nuevo (varios minutos)",
    }],
    "run-p2-probar-esp-a": ["p2-probar-esp-a", {
      titulo: "Probar el ESP-A solo",
      queVaAPasar: "Abre COM7, muestra lo que el ESP-A imprime al arrancar, le manda DIGIT:5 y muestra lo que conteste durante 5 segundos. Termina solo.",
      queDeberiasVer: "Con la placa: '(arranque) -> ESP-A listo...' y '<- recibido: REENVIADO:5', y un 5 en la OLED. Sin la placa: 'No se pudo abrir COM7' y termina con error; es lo esperado.",
      botonTexto: "Probar el ESP-A",
    }],
  };
  const ARRANQUE = {
    "p1-sim": { texto: "Abriendo PyBullet…", seg: 8, listo: /Ventana de PyBullet abierta/ },
    "p2-mouse": { texto: "Cargando TensorFlow y la red…", seg: 30, listo: /Modelo cargado/ },
    "p2-camara": { texto: "Cargando TensorFlow y la red…", seg: 30, listo: /Modelo cargado/ },
  };
  Object.entries(paneles).forEach(([elId, [accion, opciones]]) => {
    const el = $(elId); if (!el) return;
    if (tieneApp("panelEjecucion")) {
      try {
        const arr = ARRANQUE[accion] ? barraArranque(el, ARRANQUE[accion]) : null;
        if (arr) {
          opciones.alEstado = (t) => { arr.alEstado(t); if (t && t.estado === "lanzada" && /^p2-(mouse|camara)$/.test(accion) && Red.fuente !== "py") cambiarFuente("py"); };
          opciones.alLinea = (x) => arr.alLinea(x);
        }
        App.panelEjecucion(el, accion, opciones);
        if (arr) arr.montar();
      }
      catch (e) { el.innerHTML = '<div class="t8-sin-api">No se pudo preparar este botón: ' + String(e.message || e) + "</div>"; }
    } else {
      el.innerHTML = '<div class="t8-sin-api">Este botón funciona cuando la app se abre con doble clic en <b>ABRIR.bat</b> (dentro de la carpeta del tema 8).</div>';
    }
  });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arrancar);
else arrancar();
