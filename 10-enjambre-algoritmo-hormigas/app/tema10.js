/* App del tema 10: enjambre de 3 carritos ESP32 con el algoritmo de hormigas (ACO).
 *
 * Usa la API común window.App (/comun/app.js) para lanzar las acciones declaradas en ../probar.json
 * y agrega las piezas propias de este tema:
 *   - una animación del "puente doble" para explicar el ACO;
 *   - el laberinto dibujado desde maze.json (con las rutas reales de los tres nodos);
 *   - el diagrama de la red (AP, estaciones, PC);
 *   - la "salida bonita": lee lo que imprime cada programa y lo convierte en tarjetas, tablas y el
 *     video final, sin perder la salida cruda del panel común;
 *   - el GEMELO EN VIVO: mientras corre gemelo_digital.py (nativo o en Docker), lee la foto que el
 *     gemelo deja cada 0,4 s en resultados/vivo_<modo>.json y dibuja el laberinto con la feromona
 *     de cada tramo, los 3 carritos donde están y en qué paso del algoritmo va, con barra de avance;
 *   - la barra superior tipo Docker Desktop: lo que está en marcha, con su avance y su reloj.
 */
(function () {
  "use strict";

  const CARPETA = "10-enjambre-algoritmo-hormigas";
  const RAIZ = "/repo/" + CARPETA + "/";
  const COLORES = { 1: "#e5534b", 2: "#4f8fce", 3: "#e8b930" };
  const GRIS = "#8d939b";
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const coma = (x, d) => (+x).toFixed(d == null ? 2 : d).replace(".", ",");
  const reloj = (s) => { s = Math.max(0, Math.round(s)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };

  /* Cuánto tarda cada acción (segundos, medido en este PC). Lo mismo está en probar.json
     ("duracion_s"); aquí sirve para la barra mientras no hay un dato mejor (el avance real). */
  const DURACION = { aco: 2, pruebas: 4, gemelo: 300, "gemelo-apagado": 240, "gemelo-hw": 70, emulador: 45, docker: 180, "docker-hw": 70 };
  const NOMBRE_CORTO = { aco: "Algoritmo", pruebas: "Pruebas 6-11", gemelo: "Gemelo", "gemelo-apagado": "Gemelo (nodo 3 apagado)",
    "gemelo-hw": "Gemelo escuchando", emulador: "Emulador 3 ESP32", docker: "Gemelo en Docker", "docker-hw": "Docker escuchando", fw: "Firmware" };
  /* Qué archivo vivo_<modo>.json escribe cada acción del gemelo. */
  const MODO_VIVO = { gemelo: "sin-hardware", "gemelo-apagado": "sin-hardware_apagado3", "gemelo-hw": "hardware", docker: "sin-hardware", "docker-hw": "hardware" };

  /* El laberinto de respaldo (copia de maze.json) por si la página se abre sin el servidor. */
  let MAZE = {
    nombre: "almacen-5x5", columnas: 5, filas: 5, tam_celda_m: 0.2, inicio: [0, 0], meta: [4, 4],
    paredes: [[[0, 0], [0, 1]], [[1, 0], [1, 1]], [[1, 1], [1, 2]], [[1, 4], [2, 4]], [[2, 1], [2, 2]], [[2, 2], [2, 3]],
      [[3, 0], [3, 1]], [[3, 2], [3, 3]], [[3, 2], [4, 2]], [[3, 3], [3, 4]], [[4, 3], [4, 4]]],
  };
  /* Rutas de la corrida de referencia (semilla 12345), las mismas que imprime aco.py. */
  const RUTAS_REF = {
    optima: [0, 1, 2, 3, 4, 9, 14, 19, 18, 17, 22, 23, 24],
    nodos: { 1: [0, 1, 2, 7, 6, 5, 10, 11, 16, 17, 22, 23, 24], 2: [0, 1, 2, 3, 4, 9, 14, 19, 18, 17, 22, 23, 24], 3: [0, 1, 2, 3, 4, 9, 14, 19, 18, 17, 22, 23, 24] },
  };

  /* ------------------------------------------------------------------ util de estados */
  // Estados del lanzador (apps-comun/app.js): listo, preparando, instalando, lanzada, terminada,
  // error, detenida. Los reducimos a cuatro casos.
  function tipoEstado(t) {
    const s = (t && t.estado) || "";
    if (s === "terminada") return "bien";
    if (s === "error" || s === "detenida") return "mal";
    if (s === "lanzada") return "corriendo";
    if (s === "preparando" || s === "instalando") return "preparando";
    return s;
  }
  const activo = (t) => t === "corriendo" || t === "preparando";
  function textoLinea(l) { return typeof l === "string" ? l : (l && (l.x || l.texto)) || ""; }

  /* ------------------------------------------------------------------ animación del puente doble */
  function iniciarPuente() {
    const cv = $("#puente");
    if (!cv) return;
    const cx = cv.getContext("2d");
    const W = cv.width, H = cv.height;
    const NIDO = { x: 75, y: 125 }, COMIDA = { x: W - 75, y: 125 };
    // Dos caminos como curvas cuadráticas: arriba el corto, abajo el largo (más curvado).
    const caminos = [
      { ctrl: { x: W / 2, y: 20 }, nombre: "corto" },
      { ctrl: { x: W / 2, y: 470 }, nombre: "largo" },
    ];
    const punto = (c, t) => ({
      x: (1 - t) * (1 - t) * NIDO.x + 2 * (1 - t) * t * c.ctrl.x + t * t * COMIDA.x,
      y: (1 - t) * (1 - t) * NIDO.y + 2 * (1 - t) * t * c.ctrl.y + t * t * COMIDA.y,
    });
    caminos.forEach((c) => { let L = 0, p = punto(c, 0); for (let i = 1; i <= 200; i++) { const q = punto(c, i / 200); L += Math.hypot(q.x - p.x, q.y - p.y); p = q; } c.L = L; });
    const VEL = 150, N = 24, Q = 1;
    let tau, hormigas, pausa = false, rho = 0.15, ult = performance.now(), visibles = true;

    function elegir() {
      const a = tau[0], b = tau[1];
      return Math.random() * (a + b) < a ? 0 : 1;
    }
    function reiniciar() {
      tau = [1, 1];
      hormigas = [];
      for (let i = 0; i < N; i++) hormigas.push({ c: elegir(), s: -i * 18, ida: true }); // salen escalonadas
    }
    function paso(dt) {
      // evaporación continua: tau *= (1 - rho)^dt
      const f = Math.pow(1 - rho, dt);
      tau[0] = Math.max(0.02, tau[0] * f); tau[1] = Math.max(0.02, tau[1] * f);
      for (const h of hormigas) {
        h.s += VEL * dt;
        const L = caminos[h.c].L;
        if (h.s >= L) {
          if (h.ida) { h.ida = false; h.s -= L; }
          else { // volvió al hormiguero: deja feromona según lo corto del camino y elige de nuevo
            tau[h.c] += Q * 400 / L;
            h.ida = true; h.s -= L; h.c = elegir();
          }
        }
      }
    }
    function dibujar() {
      cx.clearRect(0, 0, W, H);
      const tot = tau[0] + tau[1];
      caminos.forEach((c, i) => {
        const w = 3 + 22 * (tau[i] / tot);
        cx.lineCap = "round";
        cx.strokeStyle = "#20252b"; cx.lineWidth = 26;
        cx.beginPath(); cx.moveTo(NIDO.x, NIDO.y); cx.quadraticCurveTo(c.ctrl.x, c.ctrl.y, COMIDA.x, COMIDA.y); cx.stroke();
        cx.strokeStyle = `rgba(157,108,255,${0.25 + 0.75 * tau[i] / tot})`; cx.lineWidth = w;
        cx.beginPath(); cx.moveTo(NIDO.x, NIDO.y); cx.quadraticCurveTo(c.ctrl.x, c.ctrl.y, COMIDA.x, COMIDA.y); cx.stroke();
        const m = punto(c, 0.5);
        cx.fillStyle = "#8b929b"; cx.font = "13px 'IBM Plex Mono', monospace"; cx.textAlign = "center";
        cx.fillText(`camino ${c.nombre} · feromona ${Math.round(100 * tau[i] / tot)} %`, m.x, i === 0 ? m.y - 20 : m.y - 36);
      });
      for (const h of hormigas) {
        if (h.s < 0) continue;
        const c = caminos[h.c], t = h.ida ? h.s / c.L : 1 - h.s / c.L;
        const p = punto(c, Math.min(1, Math.max(0, t)));
        cx.fillStyle = h.ida ? "#e7e9ec" : "#4caf7d";
        cx.beginPath(); cx.arc(p.x, p.y, 4, 0, 7); cx.fill();
      }
      cx.font = "600 13px 'Space Grotesk', sans-serif"; cx.textAlign = "center";
      cx.fillStyle = "#4caf7d"; cx.beginPath(); cx.arc(NIDO.x, NIDO.y, 30, 0, 7); cx.fill();
      cx.fillStyle = "#0d1013"; cx.fillText("nido", NIDO.x, NIDO.y + 5);
      cx.fillStyle = "#e8b930"; cx.beginPath(); cx.arc(COMIDA.x, COMIDA.y, 30, 0, 7); cx.fill();
      cx.fillStyle = "#0d1013"; cx.fillText("comida", COMIDA.x, COMIDA.y + 5);
      cx.fillStyle = "#8b929b"; cx.font = "12px 'IBM Plex Mono', monospace"; cx.textAlign = "left";
      cx.fillText("● blanca = va a la comida   ● verde = vuelve y deja feromona", 12, 18);
      const enCorto = hormigas.filter((h) => h.s >= 0 && h.c === 0).length;
      const vivas = hormigas.filter((h) => h.s >= 0).length || 1;
      const pct = Math.round(100 * enCorto / vivas);
      $("#puente-medidor").style.width = pct + "%";
      $("#puente-pct").textContent = pct + " %";
    }
    function bucle(ahora) {
      const dt = Math.min(0.05, (ahora - ult) / 1000); ult = ahora;
      if (!pausa && visibles) paso(dt);
      if (visibles) dibujar();
      requestAnimationFrame(bucle);
    }
    // No gastar CPU si la animación no está a la vista (otro paso de la app).
    if ("IntersectionObserver" in window) new IntersectionObserver((e) => { visibles = e[0].isIntersecting; }).observe(cv);
    $("#puente-reiniciar").onclick = reiniciar;
    $("#puente-pausa").onclick = (ev) => { pausa = !pausa; ev.target.textContent = pausa ? "Seguir" : "Pausa"; };
    $("#puente-rho").oninput = (ev) => { rho = +ev.target.value; $("#puente-rho-v").textContent = rho.toFixed(2).replace(".", ","); };
    reiniciar();
    requestAnimationFrame(bucle);
  }

  /* ------------------------------------------------------------------ laberinto en SVG */
  const S = 60, M = 20; // tamaño de celda y margen en el SVG (viewBox 340)
  const centro = (id) => { const x = id % MAZE.columnas, y = Math.floor(id / MAZE.columnas); return { x: M + x * S + S / 2, y: M + (MAZE.filas - 1 - y) * S + S / 2 }; };

  function svgLaberinto(rutas, opciones) {
    const o = opciones || {};
    const C = MAZE.columnas, F = MAZE.filas, ancho = M * 2 + C * S;
    let h = `<rect x="0" y="0" width="${ancho}" height="${ancho}" rx="10" fill="#0a0d10"/>`;
    for (let y = 0; y < F; y++) for (let x = 0; x < C; x++) {
      const px = M + x * S, py = M + (F - 1 - y) * S;
      h += `<rect x="${px + 1}" y="${py + 1}" width="${S - 2}" height="${S - 2}" fill="${(x + y) % 2 ? "#14181c" : "#171c21"}"/>`;
      if (o.numeros !== false) h += `<text x="${px + 5}" y="${py + 13}" font-size="9" fill="#4a5058" font-family="IBM Plex Mono">${5 * y + x}</text>`;
    }
    // Rutas (cada nodo desplazado un poco para que no se tapen si coinciden).
    (rutas || []).forEach((r, i) => {
      const d = (i - (rutas.length - 1) / 2) * 6;
      const pts = r.celdas.map((id) => { const c = centro(id); return `${c.x + d},${c.y + d}`; }).join(" ");
      h += `<polyline points="${pts}" fill="none" stroke="${r.color}" stroke-width="${r.grosor || 4}" stroke-linejoin="round" stroke-linecap="round" opacity="0.92"${r.punteada ? ' stroke-dasharray="6 5"' : ""}/>`;
    });
    // Paredes interiores
    h += `<g stroke="#e7e9ec" stroke-width="5" stroke-linecap="round">`;
    for (const [[x1, y1], [x2, y2]] of MAZE.paredes) {
      if (y1 === y2) { // pared vertical entre (x,y) y (x+1,y)
        const xx = M + Math.max(x1, x2) * S, yy = M + (F - 1 - y1) * S;
        h += `<line x1="${xx}" y1="${yy}" x2="${xx}" y2="${yy + S}"/>`;
      } else { // pared horizontal entre (x,y) y (x,y+1)
        const yy = M + (F - 1 - Math.max(y1, y2)) * S + S, xx = M + x1 * S;
        h += `<line x1="${xx}" y1="${yy}" x2="${xx + S}" y2="${yy}"/>`;
      }
    }
    h += `</g><rect x="${M}" y="${M}" width="${C * S}" height="${F * S}" fill="none" stroke="#e7e9ec" stroke-width="5" rx="2"/>`;
    // En la vista en vivo las marcas A y M van después de la feromona (opción sinMarcas).
    if (!o.sinMarcas) h += marcasAyM();
    return h;
  }

  function marcasAyM(chicas) {
    const C = MAZE.columnas;
    const a = centro(MAZE.inicio[1] * C + MAZE.inicio[0]), m = centro(MAZE.meta[1] * C + MAZE.meta[0]);
    // En la vista en vivo van chicas y en la esquina, para no tapar a los carritos.
    const r = 15, dx = chicas ? -18 : 0, dy = chicas ? -18 : 0, rr = chicas ? 9 : r, fs = chicas ? 10 : 16;
    return `<circle cx="${a.x + dx}" cy="${a.y - dy}" r="${rr}" fill="#4caf7d"/><text x="${a.x + dx}" y="${a.y - dy + fs * 0.37}" text-anchor="middle" font-size="${fs}" font-weight="700" fill="#0d1013" font-family="Space Grotesk">A</text>` +
      `<circle cx="${m.x - dx}" cy="${m.y + dy}" r="${rr}" fill="#9d6cff"/><text x="${m.x - dx}" y="${m.y + dy + fs * 0.37}" text-anchor="middle" font-size="${fs}" font-weight="700" fill="#0d1013" font-family="Space Grotesk">M</text>`;
  }

  function leyendaRutas(rutas) {
    return rutas.map((r) => `<span><i class="t10-muestra" style="background:${r.color}"></i>${esc(r.nombre)}</span>`).join("");
  }

  function iniciarLaberinto() {
    const svg = $("#laberinto");
    if (!svg) return;
    let modo = "ninguna";
    const dibujar = () => {
      let rutas = [];
      if (modo === "optima") rutas = [{ celdas: RUTAS_REF.optima, color: "#9d6cff", nombre: "una ruta óptima: 12 pasos, 2,40 m", grosor: 6 }];
      if (modo === "nodos") rutas = [1, 2, 3].map((n) => ({ celdas: RUTAS_REF.nodos[n], color: COLORES[n], nombre: `carrito ${n}` }));
      svg.innerHTML = svgLaberinto(rutas);
      $("#leyenda-laberinto").innerHTML = rutas.length ? leyendaRutas(rutas) + (modo === "nodos" ? "<span>(las de la semilla 12345; los carritos 2 y 3 eligieron la misma)</span>" : "") :
        "<span>A = inicio · M = meta · línea blanca = pared</span>";
    };
    $$("#selector-rutas button").forEach((b) => b.addEventListener("click", () => {
      modo = b.dataset.ruta;
      $$("#selector-rutas button").forEach((x) => x.classList.toggle("activo", x === b));
      dibujar();
    }));
    dibujar();
  }

  /* ------------------------------------------------------------------ diagrama de la red */
  function iniciarRed() {
    const svg = $("#red");
    if (!svg) return;
    const caja = (x, y, w, h, color, t1, t2, t3) =>
      `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="9" fill="#15191d" stroke="${color}" stroke-width="2"/>` +
      `<text x="${x + w / 2}" y="${y + 22}" text-anchor="middle" fill="${color}" font-size="14" font-weight="600" font-family="Space Grotesk">${t1}</text>` +
      `<text x="${x + w / 2}" y="${y + 40}" text-anchor="middle" fill="#c9cdd2" font-size="11" font-family="IBM Plex Mono">${t2}</text>` +
      (t3 ? `<text x="${x + w / 2}" y="${y + 56}" text-anchor="middle" fill="#8b929b" font-size="10.5" font-family="IBM Plex Mono">${t3}</text>` : "");
    const flecha = (x1, y1, x2, y2, color, dash) =>
      `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${color}" stroke-width="2" ${dash ? 'stroke-dasharray="5 4"' : ""} marker-end="url(#pf)" marker-start="url(#pi)"/>`;
    svg.innerHTML =
      `<defs><marker id="pf" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#8b929b"/></marker>` +
      `<marker id="pi" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M10,0 L0,5 L10,10 z" fill="#8b929b"/></marker></defs>` +
      `<ellipse cx="260" cy="150" rx="250" ry="140" fill="#17132a" stroke="#3a2d63" stroke-dasharray="6 5"/>` +
      `<text x="260" y="28" text-anchor="middle" fill="#9d6cff" font-size="12" font-family="IBM Plex Mono">WiFi ENJAMBRE_ACO (sin internet)</text>` +
      caja(185, 50, 150, 66, COLORES[1], "Carrito 1 · AP", "192.168.4.1", "crea la red + hormigas") +
      caja(30, 175, 150, 66, COLORES[2], "Carrito 2", "192.168.4.2", "hormigas") +
      caja(340, 175, 150, 66, COLORES[3], "Carrito 3", "192.168.4.3", "hormigas") +
      flecha(200, 118, 130, 172, "#8b929b") + flecha(320, 118, 390, 172, "#8b929b") + flecha(182, 208, 338, 208, "#8b929b", true) +
      `<rect x="184" y="214" width="128" height="15" rx="3" fill="#17132a"/><text x="248" y="225" text-anchor="middle" fill="#8b929b" font-size="10" font-family="IBM Plex Mono">UDP 4210 (pasa por el AP)</text>` +
      `<text x="128" y="140" fill="#8b929b" font-size="10" font-family="IBM Plex Mono">UDP 4210</text>` +
      `<text x="345" y="140" fill="#8b929b" font-size="10" font-family="IBM Plex Mono">UDP 4210</text>` +
      caja(160, 280, 200, 70, "#4caf7d", "PC · gemelo digital", "192.168.4.100", "PyBullet en Docker, UDP 4211") +
      `<path d="M105,243 C105,300 150,312 158,312" fill="none" stroke="#4caf7d" stroke-width="1.6" stroke-dasharray="4 4" marker-end="url(#pf)"/>` +
      `<path d="M415,243 C415,300 370,312 362,312" fill="none" stroke="#4caf7d" stroke-width="1.6" stroke-dasharray="4 4" marker-end="url(#pf)"/>` +
      `<path d="M322,118 L322,277" fill="none" stroke="#4caf7d" stroke-width="1.6" stroke-dasharray="4 4" marker-end="url(#pf)"/>` +
      `<text x="328" y="262" fill="#4caf7d" font-size="10" font-family="IBM Plex Mono">telemetría</text>`;
  }

  /* ------------------------------------------------------------------ salidas "bonitas" */

  // aco.py: tarjetas por nodo + laberinto con las rutas que imprimió.
  function bonitoAco(lineas, caja) {
    const txt = lineas.join("\n");
    const nodos = {};
    for (const m of txt.matchAll(/nodo (\d): L = ([\d.]+) m\s+([\d-]+)/g)) nodos[m[1]] = { L: m[2], ruta: m[3].split("-").map(Number) };
    if (!Object.keys(nodos).length) { caja.innerHTML = ""; return; }
    const opt = txt.match(/Optimo \(BFS\): ([\d-]+)\s+L = ([\d.]+)/);
    const primera = txt.match(/Primera vez con el optimo: iteracion (\d+)/);
    const conv = txt.match(/Camino por maxima feromona: ([\d-]+)\s+convergio=(\w+)/);
    const Lopt = opt ? opt[2] : "2.40";
    const rutas = Object.keys(nodos).sort().map((n) => ({ celdas: nodos[n].ruta, color: COLORES[n] || "#ccc", nombre: `carrito ${n}` }));
    if (conv) rutas.push({ celdas: conv[1].split("-").map(Number), color: "#9d6cff", nombre: "máxima feromona", grosor: 2, punteada: true });
    caja.innerHTML = `<div class="t10-tarjeta">
      <div class="t10-rejilla2" style="gap:0.8rem">
        <div><svg class="t10-laberinto" viewBox="0 0 340 340">${svgLaberinto(rutas, { numeros: false })}</svg>
          <div class="t10-leyenda">${leyendaRutas(rutas)}</div></div>
        <div class="t10-nodos">
          ${Object.keys(nodos).sort().map((n) => `<div class="t10-nodo" style="--c:${COLORES[n]}">
            <div class="f1"><b>Carrito ${n}</b><span>${(+nodos[n].L).toFixed(2).replace(".", ",")} m ${nodos[n].L === Lopt ? "· óptima" : ""}</span></div>
            <div class="ruta">${nodos[n].ruta.join(" → ")}</div></div>`).join("")}
          <div>${primera ? `<span class="t10-insignia si">ruta óptima desde la vuelta ${primera[1]}</span> ` : ""}
            ${conv ? `<span class="t10-insignia ${conv[2] === "True" ? "si" : "no"}">${conv[2] === "True" ? "la colonia convergió" : "no convergió"}</span>` : ""}</div>
          <p class="t10-nota">Las tres son rutas óptimas de ${Lopt.replace(".", ",")} m (hay cinco con esa longitud). La línea punteada violeta es el camino que sale de seguir siempre el tramo con más feromona: la respuesta del enjambre.</p>
        </div></div></div>`;
  }

  // pruebas_algoritmo.py imprime Markdown: lo pasamos a HTML (títulos, tablas y el "Cumple: si/no").
  function mdSimple(texto) {
    const L = texto.split(/\r?\n/);
    let h = "", i = 0;
    const enLinea = (t) => esc(t).replace(/\*\*Cumple: si\*\*/i, '<span class="t10-insignia si">cumple</span>')
      .replace(/\*\*Cumple: no\*\*/i, '<span class="t10-insignia no">no cumple</span>')
      .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>");
    while (i < L.length) {
      const l = L[i];
      if (/^#{1,6} /.test(l)) { h += `<h4>${enLinea(l.replace(/^#+ /, ""))}</h4>`; i++; continue; }
      if (/^\|/.test(l)) {
        const filas = [];
        while (i < L.length && /^\|/.test(L[i])) { filas.push(L[i]); i++; }
        const celdas = (f) => f.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
        const cab = celdas(filas[0]);
        const cuerpo = filas.slice(1).filter((f) => !/^\|[\s|:-]+\|$/.test(f));
        h += `<div class="t10-tabla-caja"><table class="t10-tabla"><tr>${cab.map((c) => `<th>${enLinea(c)}</th>`).join("")}</tr>` +
          cuerpo.map((f) => `<tr>${celdas(f).map((c) => `<td>${enLinea(c)}</td>`).join("")}</tr>`).join("") + "</table></div>";
        continue;
      }
      if (l.trim()) h += `<p>${enLinea(l)}</p>`;
      i++;
    }
    return h;
  }

  // gemelo_digital.py: tarjetas finales y el video (el avance en vivo lo muestra la vista "en vivo").
  function bonitoGemelo(lineas, caja, video, imagen, terminado) {
    const txt = lineas.join("\n");
    let h = "";
    const nodos = [...txt.matchAll(/^\s+nodo (\d): ([\d.]+ m|[^\s]+)\s+fase (\w+)(.*)$/gm)];
    if (nodos.length) {
      const conv = txt.match(/Convergio[^:]*: (si|no)/);
      h += `<div class="t10-nodos">` + nodos.map((m) => `<div class="t10-nodo" style="--c:${COLORES[m[1]]}">
          <div class="f1"><b>Carrito ${m[1]}</b><span>${esc(m[2])} · ${esc(m[3])}${/apagado/.test(m[4]) ? " · apagado" : ""}</span></div></div>`).join("") + `</div>`;
      if (conv) h += `<p><span class="t10-insignia ${conv[1] === "si" ? "si" : "no"}">${conv[1] === "si" ? "la colonia convergió a la ruta óptima" : "no convergió"}</span></p>`;
    }
    if (terminado && video) {
      const v = RAIZ + video + "?v=" + Date.now();
      h += `<div class="t10-aviso ok">Listo: el video quedó en la carpeta de resultados del tema.
          <div class="t10-fila" style="margin-top:0.5rem">
          <button class="t10-boton primario" data-ver-video="${esc(v)}">Ver el video aquí</button>
          ${imagen ? `<button class="t10-boton" data-abrir="${esc(imagen)}">Ver la imagen final</button>` : ""}
          <button class="t10-boton" data-carpeta="1">Abrir la carpeta de resultados</button></div>
          <div class="t10-hueco-video"></div></div>`;
    }
    caja.innerHTML = h;
    const bv = $("[data-ver-video]", caja);
    if (bv) bv.onclick = () => { $(".t10-hueco-video", caja).innerHTML = `<video class="t10-video" style="margin-top:0.6rem" controls autoplay src="${bv.dataset.verVideo}"></video>`; };
    $$("[data-abrir]", caja).forEach((b) => (b.onclick = () => abrirRel(b.dataset.abrir)));
    $$("[data-carpeta]", caja).forEach((b) => (b.onclick = () => abrirCarpeta("carpeta-resultados")));
  }

  // emulador_nodos.py: tarjetas por nodo y el "Identico a la simulacion".
  function bonitoEmulador(lineas, caja) {
    const txt = lineas.join("\n");
    let h = "";
    const vistos = new Set([...txt.matchAll(/nodo[ =]?(\d)/gi)].map((m) => m[1]));
    const fin = [...txt.matchAll(/^\s+nodo (\d): (\w+)\s+iter\s+(\d+)\s+(.*)$/gm)];
    if (fin.length) h += `<div class="t10-nodos">` + fin.map((m) => {
      const lr = m[4].match(/L =\s*([\d.]+) m\s+ruta ([\d-]+)/);
      const extra = /APAGADO/.test(m[4]) ? " · apagado" : "";
      return `<div class="t10-nodo" style="--c:${COLORES[m[1]]}">
        <div class="f1"><b>Nodo ${m[1]}</b><span>${esc(m[2])} · ${m[3]} vueltas${lr ? " · " + (+lr[1]).toFixed(2).replace(".", ",") + " m" : ""}${extra}</span></div>
        <div class="ruta">${lr ? lr[2].split("-").join(" → ") : esc(m[4])}</div></div>`;
    }).join("") + `</div>`;
    else if (vistos.size) h += `<div class="t10-nota">Nodos activos: ${[...vistos].sort().join(", ")}</div>`;
    const ident = txt.match(/Identico a la simulacion: (\w+)/i);
    if (ident) h += `<p><span class="t10-insignia ${/^s/i.test(ident[1]) ? "si" : "no"}">Idéntico a la simulación: ${esc(ident[1])}</span></p>`;
    caja.innerHTML = h;
  }

  /* ------------------------------------------------------------------ el gemelo EN VIVO */
  /* Qué se explica en cada fase del enjambre (la misma máquina de estados del firmware). */
  const FASES = [
    { id: "ESPERA", titulo: "Se saludan", txt: "Cada carrito anuncia que existe con <code>HELLO</code> y el CRC del mapa. Cuando los tres se ven durante 2 s, arrancan juntos." },
    { id: "BUSQUEDA", titulo: "Buscan (30 vueltas)", txt: "En cada vuelta cada carrito suelta 4 hormigas, <b>evapora</b> la feromona (×0,5), su mejor hormiga <b>deposita</b> 100/L en su ruta y lo <b>comparte</b> por UDP (<code>PHER</code> + <code>FIN</code>). Mira cómo la franja violeta se va concentrando en un solo camino." },
    { id: "RECORRIDO", titulo: "Recorren su ruta", txt: "Terminada la búsqueda, cada carrito recorre de verdad su mejor ruta (<code>PATH</code>), uno cada 8 s para no chocar. El gemelo los mueve con los mismos tiempos del firmware." },
    { id: "TERMINADO", titulo: "Llegaron", txt: "Los carritos están en la meta. El gemelo cierra el video y guarda la imagen final y los json en <code>resultados/</code>." },
  ];

  function faseGlobal(d) {
    const ns = Object.values(d.nodos || {}).filter((n) => !n.apagado);
    if (!ns.length) return "ESPERA";
    if (d.terminado || ns.every((n) => n.fase === "TERMINADO")) return "TERMINADO";
    if (ns.some((n) => n.fase === "RECORRIDO" || n.fase === "TERMINADO")) return "RECORRIDO";
    if (ns.some((n) => n.fase === "BUSQUEDA") || d.iter > 0) return "BUSQUEDA";
    return "ESPERA";
  }

  /* Avance real (0..1) a partir de la foto del gemelo. Sin hardware el tiempo virtual total se
     conoce desde el principio; con hardware se estima por fases: búsqueda 40 % y recorrido 60 %. */
  function avanceDe(d) {
    if (!d) return null;
    if (d.terminado) return 1;
    if (d.t_total) return Math.min(0.99, d.t / d.t_total);
    const ns = Object.values(d.nodos || {});
    // Con hardware y sin ningún carrito todavía no hay avance real que medir: null deja la barra
    // "estimada" (indeterminada) en vez de bajarla a 0 % de golpe al llegar la primera foto.
    if (!ns.length) return null;
    const busq = Math.min(1, (d.iter || 0) / (d.iteraciones || 30));
    const rec = ns.map((n) => {
      if (n.apagado) return 1;
      if (n.fase === "TERMINADO") return 1;
      if (n.fase === "RECORRIDO" && n.ruta) return Math.max(0, n.ruta.indexOf(n.celda)) / (n.ruta.length - 1);
      return 0;
    });
    return Math.min(0.99, 0.4 * busq + 0.6 * rec.reduce((a, b) => a + b, 0) / rec.length);
  }

  /* El laberinto con la feromona y los carritos, dibujado con la foto del gemelo. */
  function svgVivo(d) {
    const C = d.columnas || MAZE.columnas, F = d.filas || MAZE.filas, cel = d.tam_celda || 0.2;
    let h = svgLaberinto([], { numeros: true, sinMarcas: true });
    // Feromona: un tramo violeta por arista, más grueso y opaco cuanto más feromona tiene.
    const tau = d.tau || [], max = Math.max(1e-9, ...tau);
    const conv = new Set();
    const cod = d.camino_feromona || [];
    for (let i = 0; i + 1 < cod.length; i++) conv.add(Math.min(cod[i], cod[i + 1]) + "-" + Math.max(cod[i], cod[i + 1]));
    let fer = "";
    (d.aristas || []).forEach(([u, v], i) => {
      const a = (tau[i] || 0) / max;
      if (a < 0.03) return;
      const p = centro(u), q = centro(v);
      fer += `<line x1="${p.x}" y1="${p.y}" x2="${q.x}" y2="${q.y}" stroke="#9d6cff" stroke-linecap="round" stroke-width="${(3 + 15 * a).toFixed(1)}" opacity="${(0.18 + 0.8 * a).toFixed(2)}"/>`;
    });
    h += `<g>${fer}</g>`;
    // Mejores rutas de cada nodo (finas, de su color), corridas un poco para que no se tapen.
    Object.entries(d.nodos || {}).forEach(([n, nd]) => {
      if (!nd.ruta) return;
      const off = (n - 2) * 5;
      const pts = nd.ruta.map((id) => { const c = centro(id); return `${c.x + off},${c.y + off}`; }).join(" ");
      h += `<polyline points="${pts}" fill="none" stroke="${nd.apagado ? GRIS : COLORES[n]}" stroke-width="1.6" stroke-dasharray="4 4" opacity="0.75"/>`;
    });
    h += marcasAyM(true);
    // Carritos: un círculo de su color con el número y una flecha hacia donde miran.
    Object.entries(d.nodos || {}).forEach(([n, nd]) => {
      if (!nd.pose) return;
      const [x, y, rumbo] = nd.pose;
      const px = M + (x / cel) * S, py = M + (F - y / cel) * S;
      const col = nd.apagado ? GRIS : COLORES[n];
      const gx = Math.cos(rumbo), gy = -Math.sin(rumbo);
      h += `<g class="t10-carro"><circle cx="${px}" cy="${py}" r="12" fill="${col}" stroke="#0d1013" stroke-width="2"/>` +
        `<path d="M${px + gx * 19},${py + gy * 19} L${px + gx * 11 - gy * 6},${py + gy * 11 + gx * 6} L${px + gx * 11 + gy * 6},${py + gy * 11 - gx * 6} z" fill="${col}"/>` +
        `<text x="${px}" y="${py + 4.5}" text-anchor="middle" font-size="13" font-weight="700" fill="#0d1013" font-family="Space Grotesk">${n}</text></g>`;
    });
    return h;
  }

  /* Un componente "gemelo en vivo": el laberinto a la izquierda, la explicación de la fase y los
     carritos a la derecha, y arriba la barra de avance con el reloj. Sigue a UNA acción a la vez. */
  function crearVivo(el, opciones) {
    if (!el) return null;
    const o = Object.assign({ titulo: "Gemelo en vivo", modoInicial: "sin-hardware", acciones: [] }, opciones);
    el.classList.add("t10-vivo");
    el.innerHTML = `
      <div class="t10-vivo-cab"><span class="t10-pildora" data-v="pildora">en espera</span><b>${esc(o.titulo)}</b><span class="t10-vivo-reloj" data-v="reloj"></span></div>
      <div class="t10-progreso" data-v="barra"><div></div></div>
      <div class="t10-vivo-sub" data-v="sub">Pulsa Iniciar y aquí verás el enjambre mientras el gemelo trabaja.</div>
      <div class="t10-vivo-cuerpo">
        <div><svg class="t10-laberinto" viewBox="0 0 340 340" data-v="svg"></svg>
          <div class="t10-leyenda"><span><i class="t10-muestra" style="background:#9d6cff;height:8px"></i>feromona (más gruesa = más)</span>
            <span><i class="t10-muestra" style="background:repeating-linear-gradient(90deg,#c9cdd2 0 4px,transparent 4px 8px)"></i>mejor ruta de cada carrito</span></div></div>
        <div class="t10-vivo-lado">
          <ol class="t10-fases" data-v="fases">${FASES.map((f, i) => `<li data-fase="${f.id}"><span>${i + 1}</span><div><b>${f.titulo}</b><p>${f.txt}</p></div></li>`).join("")}</ol>
          <div class="t10-concentra" data-v="conc"></div>
          <div class="t10-nodos t10-nodos-mini" data-v="nodos"></div>
        </div>
      </div>
      <div class="t10-nota t10-ultima" data-v="ultima"></div>
      <div data-v="video"></div>`;
    const V = (k) => $(`[data-v="${k}"]`, el);
    const st = { accion: null, modo: o.modoInicial, t0: 0, estado: "", datos: null, temporizador: null, guardada: false };

    function pintar() {
      const d = st.datos;
      const corriendo = activo(st.estado);
      const pild = V("pildora");
      const etiqueta = { corriendo: "en marcha", preparando: "preparando", bien: "terminó", mal: "se detuvo" }[st.estado] || (st.guardada ? "última corrida" : "en espera");
      pild.textContent = etiqueta;
      pild.className = "t10-pildora " + (st.estado || (st.guardada ? "guardada" : ""));
      // Barra y reloj.
      const p = d && !st.guardada ? avanceDe(d) : (st.guardada ? 1 : null);
      const barra = V("barra");
      const lleva = st.t0 ? (Date.now() - st.t0) / 1000 : 0;
      const dur = DURACION[st.accion] || 120;
      if (corriendo && (p == null || p < 0.01)) {
        barra.classList.add("indeterminado");
        V("reloj").textContent = st.t0 ? `lleva ${reloj(lleva)} de ~${reloj(dur)}` : "";
      } else {
        barra.classList.remove("indeterminado");
        $("div", barra).style.width = `${Math.round(100 * (p || 0))}%`;
        if (corriendo && p > 0.08) {
          // Con poco avance la extrapolación exagera (el arranque de PyBullet pesa mucho): se
          // espera a un 8 % antes de calcular cuánto falta a partir del avance real.
          const total = Math.max(lleva / p, lleva + 1);
          V("reloj").textContent = `${Math.round(100 * p)} % · lleva ${reloj(lleva)} · faltan ~${reloj(total - lleva)}`;
        } else if (corriendo) V("reloj").textContent = `lleva ${reloj(lleva)} de ~${reloj(dur)}`;
        else if (st.estado === "bien" && st.t0) V("reloj").textContent = `100 % · tardó ${reloj(lleva)}`;
        else V("reloj").textContent = p === 1 ? "100 %" : "";
      }
      if (st.accion) avancePorAccion[st.accion] = p;
      // Subtítulo: qué está pasando en una línea.
      let sub;
      if (!d) {
        if (st.estado === "preparando") sub = "Preparando el entorno de Python (la primera vez puede tardar)…";
        else if (st.estado === "corriendo") sub = st.modo === "hardware" ? "Arrancando el gemelo; después espera la telemetría de los carritos…" : "Arrancando PyBullet y armando el laberinto en 3D…";
        else sub = "Pulsa Iniciar y aquí verás el enjambre mientras el gemelo trabaja: la feromona de cada tramo y dónde va cada carrito.";
      } else {
        const tv = d.t_total ? `tiempo del enjambre ${coma(d.t, 1)} de ${coma(d.t_total, 1)} s` : `${coma(d.t, 1)} s escuchando`;
        sub = `${st.guardada ? "Última corrida guardada en resultados/ (nativa o en Docker) · " : ""}${tv} · vuelta ${d.iter} de ${d.iteraciones} · ${d.cuadros} cuadros de video`;
        // t = 0 es la foto que el gemelo deja antes de armar la escena (unos segundos de PyBullet).
        if (d.modo === "hardware" && !Object.keys(d.nodos || {}).length) sub = d.t > 0 ?
          `${coma(d.t, 1)} s escuchando el puerto UDP 4211 · todavía no llega ningún carrito (lanza el emulador o enciende los carritos)` :
          "Armando el laberinto en PyBullet; el puerto UDP 4211 ya está abierto (lo que llegue mientras tanto no se pierde)…";
      }
      V("sub").textContent = sub;
      // Laberinto.
      V("svg").innerHTML = d ? svgVivo(d) : svgLaberinto([], { numeros: true });
      // Fase actual.
      const fase = d ? faseGlobal(d) : null;
      const idx = FASES.findIndex((f) => f.id === fase);
      $$("li", V("fases")).forEach((li, i) => { li.classList.toggle("actual", i === idx); li.classList.toggle("hecha", idx >= 0 && i < idx); });
      // Concentración de la feromona en el camino de máxima feromona (cuánto "se decidió" la colonia).
      if (d && d.tau && d.tau.length && d.camino_feromona) {
        const cod = d.camino_feromona, set = new Set();
        for (let i = 0; i + 1 < cod.length; i++) set.add(Math.min(cod[i], cod[i + 1]) + "-" + Math.max(cod[i], cod[i + 1]));
        let en = 0, tot = 0;
        d.aristas.forEach(([u, v], i) => { tot += d.tau[i]; if (set.has(u + "-" + v)) en += d.tau[i]; });
        // En la vuelta 0 la feromona es uniforme y el "camino ganador" sale solo del desempate por
        // orden de vecinos: su porcentaje (12 de 29 tramos, 41 %) no dice nada, así que no se muestra.
        const pc = d.iter === 0 ? 0 : Math.round(100 * en / (tot || 1));
        V("conc").innerHTML = `<div class="t10-fila t10-entre"><span>feromona sobre el camino ganador</span><b>${d.iter === 0 ? "—" : pc + " %"}</b></div>
          <div class="t10-medidor"><div style="width:${pc}%"></div></div>
          <div class="t10-nota">${d.iter === 0 ? "Al empezar todos los tramos tienen lo mismo." : d.convergio ? "Seguir siempre el tramo con más feromona ya da una ruta óptima (2,40 m): la colonia convergió." : "Todavía hay feromona repartida en varios caminos."}</div>`;
      } else V("conc").innerHTML = "";
      // Tarjetas de los carritos.
      const ns = d ? Object.entries(d.nodos || {}) : [];
      V("nodos").innerHTML = ns.map(([n, nd]) => `<div class="t10-nodo" style="--c:${nd.apagado ? GRIS : COLORES[n]}">
          <div class="f1"><b>Carrito ${n}</b><span>${nd.apagado ? "apagado" : esc((nd.fase || "").toLowerCase())}${nd.longitud ? " · " + coma(nd.longitud) + " m" : ""} · celda ${nd.celda}</span></div></div>`).join("");
      V("ultima").textContent = d && d.ultima_linea ? "última línea UDP: " + d.ultima_linea : "";
      // Terminada (o guardada de antes): el video de esa corrida, aquí mismo.
      const caja = V("video");
      const quiere = d && d.terminado && !corriendo ? d.modo : "";
      if (caja.dataset.modo !== quiere) {
        caja.dataset.modo = quiere;
        caja.innerHTML = quiere ? `<div class="t10-fila" style="margin-top:0.6rem"><button class="t10-boton primario">▶ Ver el video de esta corrida</button>
          <button class="t10-boton" data-abrir-img>Ver la imagen final</button></div><div data-hueco></div>` : "";
        if (quiere) {
          $("button", caja).onclick = () => { $("[data-hueco]", caja).innerHTML = `<video class="t10-video" style="margin-top:0.6rem" controls autoplay src="${RAIZ}resultados/gemelo_${quiere}.mp4?v=${Date.now()}"></video>`; };
          $("[data-abrir-img]", caja).onclick = () => abrirRel(`resultados/ruta_final_${quiere}.png`);
        }
      }
    }

    async function leer() {
      try {
        const r = await fetch(`${RAIZ}resultados/vivo_${st.modo}.json?t=${Date.now()}`, { cache: "no-store" });
        if (!r.ok) return null;
        return await r.json();
      } catch (e) { return null; }
    }

    async function tic() {
      const d = await leer();
      // Si se sigue una corrida, solo valen fotos escritas después de que empezó (con margen
      // por si el reloj del contenedor de Docker anda unos segundos corrido).
      if (d && (!st.t0 || d.inicio * 1000 >= st.t0 - 30000)) { st.datos = d; st.guardada = false; }
      pintar();
      if (!activo(st.estado)) { clearInterval(st.temporizador); st.temporizador = null; }
    }

    async function mostrarGuardada(modo) {
      if (activo(st.estado)) return;
      st.modo = modo; st.accion = null; st.t0 = 0; st.estado = "";
      const d = await leer();
      st.datos = d && d.terminado ? d : null; st.guardada = !!st.datos;
      pintar();
    }

    function alEstado(accion, t, trabajo) {
      if (activo(t) && st.accion !== accion) {
        st.accion = accion; st.modo = MODO_VIVO[accion] || st.modo; st.datos = null; st.guardada = false;
        st.t0 = trabajo && trabajo.lanzado ? trabajo.lanzado * 1000 : Date.now();
      }
      if (st.accion !== accion) return;
      if (activo(t) && !activo(st.estado) && st.estado) st.t0 = trabajo && trabajo.lanzado ? trabajo.lanzado * 1000 : Date.now(); // otra corrida
      st.estado = t;
      if (activo(t) && !st.temporizador) st.temporizador = setInterval(tic, 600);
      tic();
    }

    // Reloj de la barra aunque no llegue una foto nueva.
    setInterval(() => { if (activo(st.estado)) pintar(); }, 1000);
    mostrarGuardada(o.modoInicial);
    return { alEstado, mostrarGuardada, get accion() { return st.accion; } };
  }

  /* ------------------------------------------------------------------ barra superior: lo que está en marcha */
  const tareas = {};                 // id -> {t0, estado, fin}
  const avancePorAccion = {};        // id -> 0..1 (lo llena la vista en vivo)
  function tareaEstado(id, t, trabajo) {
    const x = tareas[id] = tareas[id] || {};
    if (activo(t) && !activo(x.estado)) x.t0 = trabajo && trabajo.lanzado ? trabajo.lanzado * 1000 : Date.now();
    if (!activo(t) && activo(x.estado)) x.fin = Date.now();
    x.estado = t;
    pintarTareas();
  }
  function pintarTareas() {
    const caja = $("#t10-tareas");
    if (!caja) return;
    const ahora = Date.now();
    const lista = Object.entries(tareas).filter(([, x]) => activo(x.estado) || (x.fin && ahora - x.fin < 10000 && (x.estado === "bien" || x.estado === "mal")));
    if (!lista.length) { caja.innerHTML = `<span class="t10-tareas-vacio">Nada en marcha</span>`; return; }
    caja.innerHTML = lista.map(([id, x]) => {
      const lleva = (ahora - (x.t0 || ahora)) / 1000, dur = DURACION[id] || 60;
      let p = avancePorAccion[id];
      if (p == null) p = Math.min(0.95, lleva / dur);
      if (x.estado === "bien") p = 1;
      const total = p > 0.08 && avancePorAccion[id] != null ? lleva / p : Math.max(dur, lleva + 5);
      const txt = x.estado === "bien" ? "terminó" : x.estado === "mal" ? "se detuvo" : x.estado === "preparando" ? `preparando · ${reloj(lleva)}` : `${Math.round(100 * p)} % · ${reloj(lleva)}`;
      const titulo = x.estado === "corriendo" ? `${NOMBRE_CORTO[id] || id}: ${Math.round(100 * p)} %, lleva ${reloj(lleva)} de ~${reloj(total)}. Clic para ir a su panel.` : "Ir a su panel";
      return `<button class="t10-tarea ${x.estado}" data-tarea="${id}" title="${esc(titulo)}"><span class="t10-punto"></span><b>${esc(NOMBRE_CORTO[id] || id)}</b><span class="t10-mini"><i style="width:${Math.round(100 * p)}%"></i></span><small>${txt}</small></button>`;
    }).join("");
    $$("[data-tarea]", caja).forEach((b) => (b.onclick = () => irAPanel(b.dataset.tarea)));
  }
  setInterval(pintarTareas, 1000);

  /* ------------------------------------------------------------------ paneles de ejecución */
  const lineasDe = {};   // id de acción -> líneas recibidas
  const estadoDe = {};   // id de acción -> último estado normalizado
  const oyentes = {};    // id de acción -> [fn(estado, trabajo)]
  const paneles = {};    // id de acción -> control del panel (iniciar, detener, estado)
  const elPanel = {};    // id de acción -> elemento del panel (para "ir a su panel")

  function alEstado(id, fn) { (oyentes[id] = oyentes[id] || []).push(fn); }

  function montarPanel(idElemento, accion, bonito, extra) {
    const el = document.getElementById(idElemento);
    if (!el || !window.App || !App.panelEjecucion) return;
    elPanel[accion] = el;
    lineasDe[accion] = [];
    let pendiente = false;
    // Repintar a lo sumo unas 4 veces por segundo (el gemelo imprime mucho).
    const repintar = (yaMismo) => {
      if (!bonito) return;
      if (yaMismo) { bonito(lineasDe[accion], estadoDe[accion] === "bien"); return; }
      if (pendiente) return;
      pendiente = true;
      setTimeout(() => { pendiente = false; bonito(lineasDe[accion], estadoDe[accion] === "bien"); }, 250);
    };
    paneles[accion] = App.panelEjecucion(el, accion, Object.assign({
      alLinea: (x, tipo) => {
        if (tipo === "sis") return; // mensajes del lanzador, no del programa
        lineasDe[accion].push(textoLinea(x));
        repintar(false);
      },
      alEstado: (e) => {
        const t = tipoEstado(e);
        const antes = estadoDe[accion];
        // Una corrida nueva empieza limpia.
        if (activo(t) && !activo(antes)) lineasDe[accion] = [];
        estadoDe[accion] = t;
        repintar(true);
        tareaEstado(accion, t, e);
        (oyentes[accion] || []).forEach((fn) => fn(t, e));
      },
    }, extra || {}));
  }

  // Las carpetas se abren en el explorador con una acción "archivo" declarada en probar.json.
  function abrirCarpeta(id) {
    if (window.App && App.accion) App.accion(id).catch((e) => App.aviso(e.message, "error"));
  }

  function abrirRel(ruta) {
    if (window.App && App.abrir) App.abrir(ruta);
    else window.open(RAIZ + ruta, "_blank");
  }

  /* Pestañas simples: [data-pestanas] > button[data-pestana=id] muestra ese id y esconde los otros. */
  const alCambiarPestana = {};
  function iniciarPestanas() {
    $$("[data-pestanas]").forEach((grupo) => {
      const bs = $$("button[data-pestana]", grupo);
      bs.forEach((b) => b.addEventListener("click", () => {
        bs.forEach((x) => { x.classList.toggle("activo", x === b); const p = document.getElementById(x.dataset.pestana); if (p) p.hidden = x !== b; });
        (alCambiarPestana[b.dataset.pestana] || (() => {}))();
      }));
    });
  }
  function mostrarPestana(id) {
    const b = $(`button[data-pestana="${id}"]`);
    if (b && !b.classList.contains("activo")) b.click();
  }

  let PASOS = null;
  function irASeccion(titulo) {
    const secs = $$("section.paso");
    const i = secs.findIndex((s) => s.dataset.titulo === titulo);
    if (i < 0) return;
    if (PASOS && typeof PASOS.ir === "function") PASOS.ir(i);
    else secs[i].scrollIntoView({ behavior: "smooth" });
  }
  function irAPanel(accion) {
    const el = elPanel[accion];
    if (!el) return;
    const sec = el.closest("section.paso");
    const pest = el.closest(".t10-pestana");
    if (sec) irASeccion(sec.dataset.titulo);
    if (pest) mostrarPestana(pest.id);
    setTimeout(() => el.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
  }

  function iniciarPaneles() {
    montarPanel("panel-aco", "aco", (l) => bonitoAco(l, $("#bonito-aco")), {
      botonTexto: "Iniciar: correr el enjambre",
      queVaAPasar: "Corre el enjambre completo (3 carritos × 4 hormigas × 30 vueltas, semilla 12345) con la misma lógica, bit a bit, que el programa de los ESP32. Tarda menos de un segundo.",
      queDeberiasVer: "En menos de un segundo: la ruta de cada carrito dibujada en el laberinto (las tres de 2,40 m) y si la colonia convergió.",
    });
    montarPanel("panel-pruebas", "pruebas", (l) => { $("#bonito-pruebas").innerHTML = mdSimple(l.join("\n")); }, {
      botonTexto: "Iniciar: correr las pruebas 6 a 11",
      queVaAPasar: "Unos 3 segundos: prueba el algoritmo en un laberinto abierto, en uno de un solo camino y en uno de dos caminos, con 20 semillas distintas, y cambiando ρ, α y β. Guarda las tablas en la carpeta de pruebas (mismos números de siempre).",
      queDeberiasVer: "Una tabla por prueba con el porcentaje de semillas que hallan y convergen, y si cumple el criterio (la 6 no cumple por una semilla: está explicado en Resultados).",
    });
    const gem = "A la derecha, en vivo: la feromona concentrándose en la ruta corta y los tres carritos recorriéndola, con la barra de avance. Al final, la ruta de cada carrito y un botón para ver el video aquí mismo.";
    montarPanel("panel-gemelo", "gemelo", (l, fin) => bonitoGemelo(l, $("#bonito-gemelo"), "resultados/gemelo_sin-hardware.mp4", "resultados/ruta_final_sin-hardware.png", fin),
      { botonTexto: "Iniciar el gemelo (4-5 min)", queDeberiasVer: gem,
        queVaAPasar: "Corre el mismo algoritmo, arma el laberinto en PyBullet sin abrir ventanas y graba un video desde arriba: primero la búsqueda (feromona violeta) y después los tres carritos recorriendo su ruta. Tarda unos 4 a 5 minutos." });
    montarPanel("panel-gemelo-apagado", "gemelo-apagado", (l, fin) => bonitoGemelo(l, $("#bonito-gemelo-apagado"), "resultados/gemelo_sin-hardware_apagado3.mp4", "resultados/ruta_final_sin-hardware_apagado3.png", fin),
      { botonTexto: "Iniciar con el nodo 3 apagado (4-5 min)", queVaAPasar: "La prueba 14 en simulación: después de la vuelta 10 el nodo 3 se apaga, su robot queda gris y los nodos 1 y 2 terminan solos. Tarda lo mismo (4 a 5 minutos).", queDeberiasVer: "En vivo a la derecha: el carrito 3 se pone gris tras la vuelta 10 y los otros dos llegan con su ruta." });
    montarPanel("panel-gemelo-hw", "gemelo-hw", (l, fin) => {
      bonitoGemelo(l, $("#bonito-gemelo-hw"), "resultados/gemelo_hardware.mp4", "resultados/ruta_final_hardware.png", fin);
      const ult = [...l.join("\n").matchAll(/vivos \[([\d, ]*)\]/g)].pop();
      const vivos = ult ? ult[1].split(",").map((s) => s.trim()) : [];
      $$("#vivos-hw span").forEach((s, i) => s.classList.toggle("on", vivos.includes(String(i + 1))));
      if (/Escuchando telemetria/.test(l.join("\n")) && !fin) $("#candado-emulador").classList.add("t10-oculto");
    }, {
      botonTexto: "1) Iniciar el gemelo que escucha",
      queVaAPasar: "El gemelo se queda escuchando la red (puerto UDP 4211) hasta 240 s, como lo haría con los carritos. Termina solo unos 50 s después de que arranque el emulador y deja su video. Si Windows pregunta por el firewall, permítelo.",
      queDeberiasVer: "\"Escuchando telemetria UDP en 0.0.0.0:4211\". Entonces se habilita el paso 2. Cuando llegan los nodos se encienden sus etiquetas de colores y aparecen en la vista en vivo.",
    });
    montarPanel("panel-emulador", "emulador", (l) => bonitoEmulador(l, $("#bonito-emulador")), {
      botonTexto: "2) Iniciar los 3 ESP32 emulados",
      queVaAPasar: "Tres ESP32 virtuales dentro del PC, con el mismo protocolo del firmware, mandan sus mensajes por UDP de verdad al gemelo. Tarda unos 50 s y al final compara su feromona con la del algoritmo.",
      queDeberiasVer: "Los tres nodos buscando y recorriendo; al final una tarjeta por nodo y \"Idéntico a la simulación: SI\".",
    });
    montarPanel("panel-docker", "docker", (l, fin) => bonitoGemelo(l, $("#bonito-docker"), "resultados/gemelo_sin-hardware.mp4", "resultados/ruta_final_sin-hardware.png", fin),
      { queDeberiasVer: "Primero la construcción de la imagen (solo la primera vez); después, a la derecha, el gemelo del contenedor en vivo, igual que el nativo." });
    montarPanel("panel-docker-hw", "docker-hw");
    montarPanel("panel-fw", "fw", null, { botonTexto: "Ver el código del firmware" });

    alEstado("gemelo-hw", (t) => {
      if (t === "corriendo") $("#candado-emulador").classList.add("t10-oculto");
      // Se vuelve a bloquear solo si el emulador no llegó a correr (así su resultado sigue a la vista).
      const em = estadoDe["emulador"];
      if ((t === "bien" || t === "mal") && em !== "bien" && em !== "mal" && em !== "corriendo") $("#candado-emulador").classList.remove("t10-oculto");
    });

    // Las vistas en vivo: cada una sigue a las acciones de su paso.
    const vivoGemelo = crearVivo($("#vivo-gemelo"), { titulo: "Gemelo en vivo", modoInicial: "sin-hardware" });
    const vivoHw = crearVivo($("#vivo-hw"), { titulo: "Gemelo en vivo (tiempo real, UDP 4211)", modoInicial: "hardware" });
    const vivoDocker = crearVivo($("#vivo-docker"), { titulo: "Gemelo del contenedor, en vivo", modoInicial: "sin-hardware" });
    ["gemelo", "gemelo-apagado"].forEach((a) => alEstado(a, (t, e) => vivoGemelo && vivoGemelo.alEstado(a, t, e)));
    alEstado("gemelo-hw", (t, e) => vivoHw && vivoHw.alEstado("gemelo-hw", t, e));
    ["docker", "docker-hw"].forEach((a) => alEstado(a, (t, e) => vivoDocker && vivoDocker.alEstado(a, t, e)));
    alCambiarPestana["p-gemelo"] = () => vivoGemelo && vivoGemelo.mostrarGuardada("sin-hardware");
    alCambiarPestana["p-gemelo-apagado"] = () => vivoGemelo && vivoGemelo.mostrarGuardada("sin-hardware_apagado3");
    alCambiarPestana["p-docker"] = () => vivoDocker && vivoDocker.mostrarGuardada("sin-hardware");
    alCambiarPestana["p-docker-hw"] = () => vivoDocker && vivoDocker.mostrarGuardada("hardware");
  }

  /* "Lanzar los dos en orden": pulsa el Iniciar del panel 1, espera a que el gemelo diga que
     escucha y pulsa el del panel 2. Así la salida de cada uno queda en su propio panel. */
  function iniciarLanzarAmbos() {
    const b = $("#lanzar-ambos"), info = $("#estado-ambos");
    if (!b) return;
    b.onclick = async () => {
      const p1 = paneles["gemelo-hw"], p2 = paneles["emulador"];
      if (!p1 || !p2) { info.textContent = "La app todavía no está conectada al lanzador."; return; }
      if (activo(estadoDe["gemelo-hw"]) || activo(estadoDe["emulador"])) { info.textContent = "Ya hay uno de los dos en marcha: espera a que termine o detenlo."; return; }
      b.disabled = true;
      info.textContent = "1/2 · arrancando el gemelo (la primera vez puede tardar mientras prepara el entorno)...";
      const escucha = () => /Escuchando telemetria/.test((lineasDe["gemelo-hw"] || []).join("\n"));
      p1.iniciar();
      const t0 = Date.now();
      // Esperar hasta 20 min (la primera vez puede compilar PyBullet).
      while (!escucha() && Date.now() - t0 < 20 * 60 * 1000) {
        await new Promise((r) => setTimeout(r, 500));
        if ((estadoDe["gemelo-hw"] === "bien" || estadoDe["gemelo-hw"] === "mal") && Date.now() - t0 > 3000) break;
      }
      if (!escucha() || estadoDe["gemelo-hw"] !== "corriendo") {
        info.textContent = "El gemelo no llegó a escuchar: mira su panel (paso 1) para ver qué dijo.";
        b.disabled = false; return;
      }
      info.textContent = "2/2 · el gemelo escucha; arrancando los tres ESP32 emulados... (mira la vista en vivo a la derecha)";
      await new Promise((r) => setTimeout(r, 1000));
      p2.iniciar();
      const fin = (t) => {
        if (t === "bien") info.textContent = "El emulador terminó. El gemelo cierra solo en unos segundos y deja el video en el paso 1.";
        if (t === "mal") info.textContent = "El emulador no terminó bien: mira su panel (paso 2).";
        if (t === "bien" || t === "mal") b.disabled = false;
      };
      alEstado("emulador", fin);
    };
  }

  /* ------------------------------------------------------------------ arranque */
  async function cargarMaze() {
    try { const r = await fetch(RAIZ + "maze.json"); if (r.ok) MAZE = await r.json(); } catch (e) { /* se queda con la copia */ }
  }

  async function iniciar() {
    await cargarMaze();
    iniciarPuente();
    iniciarLaberinto();
    iniciarRed();
    iniciarPestanas();

    if (window.App) {
      try { await App.iniciar(); } catch (e) { console.warn("App.iniciar:", e); }
      if (App.checklist) { App.checklist($("#checklist-portada")); App.checklist($("#checklist-final")); }
      if (App.pasos) PASOS = App.pasos($("#pasos"));
      iniciarPaneles();
      if (App.markdown) {
        App.markdown($("#md-conexiones"), "README.md", { desde: "### Alimentación", hasta: "### Distancias entre los ESP32 en el montaje" });
        App.markdown($("#md-docker"), "README.md", { desde: "### Problemas típicos", hasta: "## El montaje y la demo" });
      }
      if (App.imagen) $$("[data-ampliar]").forEach((im) => App.imagen(im));
    }
    iniciarLanzarAmbos();

    // Botones que llevan a un paso.
    $$("[data-ir]").forEach((b) => b.addEventListener("click", () => irASeccion(b.dataset.ir)));
    $("#abrir-preview").onclick = () => (window.App && App.abrir ? App.abrir("preview.html") : window.open(RAIZ + "preview.html", "_blank"));
    $("#abrir-firmware").onclick = () => abrirCarpeta("carpeta-firmware");
    $("#abrir-resultados").onclick = () => abrirCarpeta("carpeta-resultados");
    $("#abrir-repo").onclick = () => window.open("https://github.com/Dathinel/Sensores-Teoria/tree/main/" + CARPETA, "_blank");
    $("#abrir-readme").onclick = () => window.open("/readme/" + CARPETA, "_blank");
    const bpc = $("#pantalla-completa");
    bpc.onclick = () => {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => App.aviso && App.aviso("El navegador no dejó pasar a pantalla completa (prueba con F11).", "aviso"));
    };
    document.addEventListener("fullscreenchange", () => { bpc.textContent = document.fullscreenElement ? "⛶ Salir de pantalla completa" : "⛶ Pantalla completa"; });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
