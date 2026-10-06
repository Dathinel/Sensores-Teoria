// App del tema 5: peces en el osciloscopio (modo XY).
// Usa /comun/app.js (window.App) para la checklist, los pasos, el botón del simulador y las
// imágenes ampliables. Lo propio de esta app: el laboratorio de Lissajous (dos senoidales en
// un canvas), el pez del dibujo de conexiones y el visor de los dos scripts.
(function () {
  "use strict";

  const CARPETA = "5-parcial-figuras-lissauer";
  const REPO = "/repo/" + CARPETA + "/";
  const A = () => window.App || null;
  const $ = (s) => document.querySelector(s);
  let pasos = null;   // lo que devuelva App.pasos (si devuelve algo para navegar)

  // ---------- laboratorio de Lissajous ----------
  const lab = { fx: 2, fy: 3, fase: 90, t0: performance.now() };
  function dibujarLissajous(ahora) {
    const cv = $("#cvXY"); if (!cv) return;
    const g = cv.getContext("2d");
    const W = cv.width, H = cv.height, m = 22;
    const fase = lab.fase * Math.PI / 180;
    g.fillStyle = "#06130c"; g.fillRect(0, 0, W, H);
    // retícula del osciloscopio: 8 x 8 divisiones
    g.strokeStyle = "rgba(125,255,155,.09)"; g.lineWidth = 1;
    for (let i = 0; i <= 8; i++) {
      const p = m + i * (W - 2 * m) / 8;
      g.beginPath(); g.moveTo(p, m); g.lineTo(p, H - m); g.stroke();
      g.beginPath(); g.moveTo(m, p); g.lineTo(W - m, p); g.stroke();
    }
    const R = (W - 2 * m) / 2 - 6, cx = W / 2, cy = H / 2;
    const N = 900;
    // figura completa (el "fósforo" que ya quedó)
    g.strokeStyle = "rgba(125,255,155,.55)"; g.lineWidth = 1.6;
    g.shadowColor = "rgba(125,255,155,.7)"; g.shadowBlur = 6;
    g.beginPath();
    for (let i = 0; i <= N; i++) {
      const t = i / N * 2 * Math.PI;
      const x = cx + R * Math.sin(lab.fx * t), y = cy - R * Math.sin(lab.fy * t + fase);
      if (i) g.lineTo(x, y); else g.moveTo(x, y);
    }
    g.stroke();
    // el punto del haz recorriendo la figura
    const t = ((ahora - lab.t0) / 4000 % 1) * 2 * Math.PI;
    const px = cx + R * Math.sin(lab.fx * t), py = cy - R * Math.sin(lab.fy * t + fase);
    g.shadowBlur = 16; g.fillStyle = "#e9ffee";
    g.beginPath(); g.arc(px, py, 4, 0, 2 * Math.PI); g.fill();
    g.shadowBlur = 0;
    trazar($("#cvX"), (u) => Math.sin(lab.fx * u), "#f2c94c", t);
    trazar($("#cvY"), (u) => Math.sin(lab.fy * u + fase), "#56ccf2", t);
    requestAnimationFrame(dibujarLissajous);
  }
  // Cada canal "en el tiempo" (como se vería en modo YT), con una marca en el instante actual.
  function trazar(cv, f, color, tAhora) {
    if (!cv) return;
    const g = cv.getContext("2d"), W = cv.width, H = cv.height;
    g.clearRect(0, 0, W, H);
    g.strokeStyle = color; g.lineWidth = 1.5; g.beginPath();
    for (let i = 0; i <= W; i++) {
      const u = i / W * 2 * Math.PI, y = H / 2 - f(u) * (H / 2 - 5);
      if (i) g.lineTo(i, y); else g.moveTo(i, y);
    }
    g.stroke();
    const xi = tAhora / (2 * Math.PI) * W;
    g.fillStyle = "#fff"; g.beginPath(); g.arc(xi, H / 2 - f(tAhora) * (H / 2 - 5), 3, 0, 2 * Math.PI); g.fill();
  }
  function actualizarTextosLab() {
    $("#txtFx").textContent = lab.fx; $("#txtFy").textContent = lab.fy;
    $("#txtFase").textContent = lab.fase; $("#txtFase2").textContent = lab.fase;
  }
  function iniciarLab() {
    $("#selRel").addEventListener("change", (e) => {
      const [a, b] = e.target.value.split(":").map(Number); lab.fx = a; lab.fy = b; actualizarTextosLab();
    });
    $("#rgFase").addEventListener("input", (e) => { lab.fase = +e.target.value; actualizarTextosLab(); });
    $("#bElipse").addEventListener("click", () => {
      lab.fx = 1; lab.fy = 1; lab.fase = 90; $("#selRel").value = "1:1"; $("#rgFase").value = 90; actualizarTextosLab();
    });
    actualizarTextosLab();
    requestAnimationFrame(dibujarLissajous);
  }

  // ---------- pez chiquito en la pantalla del dibujo de conexiones ----------
  // Misma geometría de pez3_esp32.py (cuerpo, cola, ojo y boca), escalada a la pantalla del SVG.
  function dibujarPezMini() {
    const camino = $("#pezMini"); if (!camino) return;
    const X = (x) => (500 + (x - 0.08) * 125).toFixed(1), Y = (y) => (178 - 8 - y * 105).toFixed(1);
    const elipse = (cx, cy, rx, ry, a0 = 0, a1 = 360, n = 48) => {
      let d = "";
      for (let i = 0; i <= n; i++) {
        const t = (a0 + (a1 - a0) * i / n) * Math.PI / 180;
        d += (i ? "L" : "M") + X(cx + rx * Math.cos(t)) + " " + Y(cy + ry * Math.sin(t)) + " ";
      }
      return d;
    };
    let d = elipse(0.42, 0.52, 0.29, 0.25);
    d += "M" + X(0.71) + " " + Y(0.52) + " L" + X(0.93) + " " + Y(0.78) + " L" + X(0.93) + " " + Y(0.26) + " Z ";
    d += elipse(0.33, 0.64, 0.04, 0.045, 0, 360, 20) + elipse(0.31, 0.44, 0.07, 0.045, 200, 340, 16);
    camino.setAttribute("d", d);
  }

  // ---------- código de los dos scripts ----------
  const textos = {};
  function resaltar(texto) {
    const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const KW = /(<span class="[sn]">.*?<\/span>)|\b(import|from|def|return|for|in|range|if|else|elif|while|True|False|None|and|or|not)\b/g;
    return texto.split("\n").map((linea) => {
      const m = linea.match(/^([^#]*?)(#.*)?$/) || [null, linea, ""];
      let c = esc(m[1] || "");
      c = c.replace(/("[^"]*")/g, '<span class="s">$1</span>');
      c = c.replace(/(<span class="s">.*?<\/span>)|\b(\d+(?:\.\d+)?)\b/g, (t, s, n) => s || '<span class="n">' + n + "</span>");
      c = c.replace(KW, (t, s, k) => s || '<span class="k">' + k + "</span>");
      return c + (m[2] ? '<span class="c">' + esc(m[2]) + "</span>" : "");
    }).join("\n");
  }
  let archivoActual = "pez3_esp32.py";
  async function mostrarCodigo(nombre) {
    archivoActual = nombre;
    document.querySelectorAll(".pestana").forEach((b) => b.classList.toggle("activa", b.dataset.archivo === nombre));
    const pre = $("#codigo");
    if (!textos[nombre]) {
      pre.textContent = "Cargando…";
      try { textos[nombre] = await (await fetch(REPO + nombre)).text(); }
      catch (e) { pre.textContent = "No se pudo leer " + nombre + "."; return; }
    }
    pre.innerHTML = resaltar(textos[nombre]);
    pre.scrollTop = 0;
  }
  async function copiar() {
    try {
      await navigator.clipboard.writeText(textos[archivoActual] || "");
      aviso("Código copiado: pégalo en Thonny y guárdalo en la placa como main.py.", "ok");
    } catch (e) {
      const r = document.createRange(); r.selectNodeContents($("#codigo"));
      const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
      aviso("Texto seleccionado: cópialo con Ctrl+C.", "info");
    }
  }
  function aviso(t, tipo) { if (A() && A().aviso) A().aviso(t, tipo); }

  // ---------- el pez por partes (armador) ----------
  // Copia exacta de la geometría de pez3_esp32.py: mismas funciones (crear_elipse, crear_linea,
  // crear_bezier), mismos números y el mismo DESPLAZAMIENTO_X = -0.08 y rango DAC 10-245.
  const DAC_MIN = 10, DAC_MAX = 245, DESP_X = -0.08, DESP_Y = 0;
  const lim = (v) => Math.max(0, Math.min(1, v));
  const aDacX = (x) => Math.trunc(DAC_MIN + lim(x + DESP_X) * (DAC_MAX - DAC_MIN));
  const aDacY = (y) => Math.trunc(DAC_MIN + lim(y + DESP_Y) * (DAC_MAX - DAC_MIN));
  function elipseP(cx, cy, rx, ry, n, a0 = 0, a1 = 360) {
    const r = [], i0 = a0 * Math.PI / 180, i1 = a1 * Math.PI / 180;
    for (let i = 0; i <= n; i++) { const t = i0 + (i1 - i0) * i / n; r.push([aDacX(cx + rx * Math.cos(t)), aDacY(cy + ry * Math.sin(t))]); }
    return r;
  }
  function lineaP(x1, y1, x2, y2, n) {
    const r = []; for (let i = 0; i <= n; i++) { const t = i / n; r.push([aDacX(x1 + (x2 - x1) * t), aDacY(y1 + (y2 - y1) * t)]); } return r;
  }
  function bezierP(x0, y0, x1, y1, x2, y2, n) {
    const r = [];
    for (let i = 0; i <= n; i++) { const t = i / n, u = 1 - t; r.push([aDacX(u * u * x0 + 2 * u * t * x1 + t * t * x2), aDacY(u * u * y0 + 2 * u * t * y1 + t * t * y2)]); }
    return r;
  }
  const PIEZAS = [
    { nombre: "Cuerpo", forma: "elipse completa", color: "#7dff9b", pts: elipseP(0.42, 0.52, 0.29, 0.25, 110),
      codigo: "cuerpo = crear_elipse(0.42, 0.52, 0.29, 0.25, 110)",
      nota: "La misma elipse del laboratorio de Lissajous (1:1 con 90°): x = cx + rx·cos(t), y = cy + ry·sen(t). 110 tramos = 111 puntos." },
    { nombre: "Cola", forma: "3 líneas", color: "#9df5ff",
      pts: [].concat(lineaP(0.71, 0.52, 0.93, 0.78, 25), lineaP(0.93, 0.78, 0.93, 0.26, 35), lineaP(0.93, 0.26, 0.71, 0.52, 25)),
      codigo: "cola  = crear_linea(P1_X, P1_Y, 0.93, 0.78, 25)  # sube\ncola += crear_linea(0.93, 0.78, 0.93, 0.26, 35)  # baja recto\ncola += crear_linea(0.93, 0.26, P1_X, P1_Y, 25)  # vuelve",
      nota: "Tres rectas que salen y vuelven al borde derecho del cuerpo (P1), así el haz no salta: 26 + 36 + 26 = 88 puntos." },
    { nombre: "Ojo", forma: "elipse chica", color: "#ffe58a", pts: elipseP(0.33, 0.64, 0.040, 0.045, 30),
      codigo: "ojo = crear_elipse(0.33, 0.64, 0.040, 0.045, 30)", nota: "Otra elipse, mucho más pequeña: 31 puntos." },
    { nombre: "Pupila", forma: "elipse mínima", color: "#ffb36b", pts: elipseP(0.33, 0.65, 0.012, 0.014, 14),
      codigo: "pupila = crear_elipse(0.33, 0.65, 0.012, 0.014, 14)\ndibujar(pupila, 180)   # 180 µs en cada punto",
      nota: "Tan chica que casi es un punto: el script se queda 180 µs en cada uno (en vez de DRAW_US = 1) para que, con tan pocos puntos, brille parecido al resto y no más débil. 15 puntos." },
    { nombre: "Boca", forma: "arco 200°-340°", color: "#ff8fb1", pts: elipseP(0.31, 0.44, 0.070, 0.045, 30, 200, 340),
      codigo: "boca = crear_elipse(0.31, 0.44, 0.070, 0.045, 30, 200, 340)",
      nota: "Un trozo de elipse: solo los ángulos de 200° a 340° (la parte de abajo), y queda la sonrisa. 31 puntos." },
    { nombre: "Aleta", forma: "2 curvas Bézier", color: "#c6a6ff",
      pts: [].concat(bezierP(0.575, 0.515, 0.52, 0.515, 0.485, 0.475, 18), bezierP(0.485, 0.475, 0.52, 0.43, 0.58, 0.44, 18)),
      codigo: "aleta  = crear_bezier(0.575,0.515, 0.520,0.515, 0.485,0.475, 18)\naleta += crear_bezier(0.485,0.475, 0.520,0.430, 0.580,0.440, 18)",
      nota: "Bézier cuadrática: B(t) = (1−t)²·P0 + 2(1−t)t·P1 + t²·P2; el punto del medio jala la curva. 19 + 19 = 38 puntos." },
  ];
  const TODOS = []; PIEZAS.forEach((p, k) => p.pts.forEach((q) => TODOS.push([q[0], q[1], k])));
  const arm = { n: 0, hasta: 0, corriendo: false, vel: 3 };   // n = puntos ya dibujados; hasta = dónde parar
  function inicioPieza(k) { let s = 0; for (let i = 0; i < k; i++) s += PIEZAS[i].pts.length; return s; }
  function piezaDe(n) { return n <= 0 ? 0 : TODOS[Math.min(n, TODOS.length) - 1][2]; }

  function pintarArmador() {
    const cv = $("#cvPez"); if (!cv) return;
    const g = cv.getContext("2d"), W = cv.width, H = cv.height, m = 20;
    const X = (v) => m + (v / 255) * (W - 2 * m), Y = (v) => H - m - (v / 255) * (H - 2 * m);
    g.fillStyle = "#06130c"; g.fillRect(0, 0, W, H);
    g.strokeStyle = "rgba(125,255,155,.09)"; g.lineWidth = 1;
    for (let i = 0; i <= 8; i++) {
      const px = m + i * (W - 2 * m) / 8, py = m + i * (H - 2 * m) / 8;
      g.beginPath(); g.moveTo(px, m); g.lineTo(px, H - m); g.stroke();
      g.beginPath(); g.moveTo(m, py); g.lineTo(W - m, py); g.stroke();
    }
    // la figura completa, apenas insinuada (para ver lo que falta)
    g.strokeStyle = "rgba(125,255,155,.12)"; g.lineWidth = 1;
    PIEZAS.forEach((p) => { g.beginPath(); p.pts.forEach((q, i) => (i ? g.lineTo(X(q[0]), Y(q[1])) : g.moveTo(X(q[0]), Y(q[1])))); g.stroke(); });
    // lo ya recorrido, con el color de su pieza
    g.lineWidth = 2.2; g.shadowBlur = 6;
    PIEZAS.forEach((p, k) => {
      const ini = inicioPieza(k), cuantos = Math.max(0, Math.min(p.pts.length, arm.n - ini));
      if (cuantos < 2) return;
      g.strokeStyle = p.color; g.shadowColor = p.color;
      g.beginPath();
      for (let i = 0; i < cuantos; i++) { const q = p.pts[i]; i ? g.lineTo(X(q[0]), Y(q[1])) : g.moveTo(X(q[0]), Y(q[1])); }
      g.stroke();
    });
    g.shadowBlur = 0;
    // el punto del haz y lo que recibe cada DAC en ese instante
    if (arm.n > 0) {
      const q = TODOS[Math.min(arm.n, TODOS.length) - 1];
      g.shadowColor = "#e9ffee"; g.shadowBlur = 16; g.fillStyle = "#ffffff";
      g.beginPath(); g.arc(X(q[0]), Y(q[1]), 4.5, 0, 2 * Math.PI); g.fill(); g.shadowBlur = 0;
      $("#leX").textContent = q[0]; $("#leY").textContent = q[1];
      $("#leVx").textContent = "≈ " + (q[0] / 255 * 3.3).toFixed(2).replace(".", ",") + " V";
      $("#leVy").textContent = "≈ " + (q[1] / 255 * 3.3).toFixed(2).replace(".", ",") + " V";
    } else { $("#leX").textContent = "—"; $("#leY").textContent = "—"; $("#leVx").textContent = ""; $("#leVy").textContent = ""; }
    $("#lePunto").textContent = arm.n + " / " + TODOS.length;
    $("#barraPez").style.width = (arm.n / TODOS.length * 100) + "%";
    trazaPez($("#cvPezX"), 0, "#f2c94c"); trazaPez($("#cvPezY"), 1, "#56ccf2");
    // lista de piezas y el código de la pieza actual
    const k = piezaDe(arm.n);
    document.querySelectorAll("#listaPiezas li:not(.total)").forEach((li, i) => {
      const ini = inicioPieza(i), fin = ini + PIEZAS[i].pts.length;
      li.classList.toggle("hecha", arm.n >= fin);
      li.classList.toggle("actual", (arm.n > ini && arm.n < fin) || (arm.n === 0 && i === 0));
    });
    if (arm.n >= TODOS.length) {
      $("#codigoPieza").textContent = "while True:\n    dibujar_pez()   # cuerpo, cola, ojo, pupila, boca, aleta… y otra vez";
      $("#notaPieza").textContent = "¡Pez completo: 314 puntos! En el ESP32 este recorrido se repite cientos de veces por segundo, por eso el ojo ve una figura quieta (persistencia de la visión).";
    } else {
      const p = PIEZAS[arm.n === 0 ? 0 : k];
      $("#codigoPieza").textContent = p.codigo; $("#notaPieza").textContent = p.nota;
    }
  }
  // X y Y "en el tiempo": la lista de valores que recibe cada DAC, como se vería en modo YT.
  function trazaPez(cv, eje, color) {
    if (!cv) return;
    const g = cv.getContext("2d"), W = cv.width, H = cv.height;
    g.clearRect(0, 0, W, H);
    g.strokeStyle = "rgba(255,255,255,.08)"; g.beginPath(); g.moveTo(0, H / 2); g.lineTo(W, H / 2); g.stroke();
    g.strokeStyle = color; g.lineWidth = 1.4; g.beginPath();
    const n = Math.min(arm.n, TODOS.length);
    for (let i = 0; i < n; i++) { const x = i / (TODOS.length - 1) * W, y = H - 3 - (TODOS[i][eje] / 255) * (H - 6); i ? g.lineTo(x, y) : g.moveTo(x, y); }
    g.stroke();
  }
  function bucleArmador() {
    if (arm.corriendo) {
      arm.n = Math.min(arm.hasta, arm.n + arm.vel);
      if (arm.n >= arm.hasta) {
        arm.corriendo = false; actualizarBotonArmar();
        if (arm.n >= TODOS.length) document.dispatchEvent(new CustomEvent("pez-completo"));
      }
      pintarArmador();
    }
    requestAnimationFrame(bucleArmador);
  }
  function actualizarBotonArmar() {
    const b = $("#bArmar"); if (!b) return;
    b.textContent = arm.corriendo ? "⏸ Pausa" : (arm.n >= TODOS.length ? "↺ Armar otra vez" : (arm.n ? "▶ Seguir" : "▶ Armar el pez"));
  }
  function iniciarArmador() {
    const ol = $("#listaPiezas"); if (!ol) return;
    PIEZAS.forEach((p, i) => {
      const li = document.createElement("li");
      li.innerHTML = '<button type="button" title="Dibujar esta pieza (las anteriores quedan como ya recorridas)"><i style="background:' + p.color + '"></i><b>' + p.nombre +
        "</b><span>" + p.forma + " · " + p.pts.length + "</span></button>";
      li.querySelector("button").addEventListener("click", () => {
        arm.n = inicioPieza(i); arm.hasta = inicioPieza(i) + p.pts.length; arm.corriendo = true; actualizarBotonArmar();
      });
      ol.appendChild(li);
    });
    const tot = document.createElement("li"); tot.className = "total";
    tot.innerHTML = '<div><i></i><b>Total</b><span>' + TODOS.length + " puntos por pez</span></div>"; ol.appendChild(tot);
    $("#bArmar").addEventListener("click", () => {
      if (arm.corriendo) arm.corriendo = false;
      else { if (arm.n >= TODOS.length) arm.n = 0; arm.hasta = TODOS.length; arm.corriendo = true; }
      actualizarBotonArmar();
    });
    // "Siguiente pieza": termina la pieza actual, o dibuja la siguiente si la actual ya está completa.
    $("#bPieza").addEventListener("click", () => {
      if (arm.n >= TODOS.length) arm.n = 0;
      let k = 0;
      while (k < PIEZAS.length - 1 && arm.n >= inicioPieza(k) + PIEZAS[k].pts.length) k++;
      arm.hasta = inicioPieza(k) + PIEZAS[k].pts.length; arm.corriendo = true; actualizarBotonArmar();
    });
    $("#bReiniciar").addEventListener("click", () => { arm.n = 0; arm.corriendo = false; actualizarBotonArmar(); pintarArmador(); });
    $("#rgVelPez").addEventListener("input", (e) => { arm.vel = +e.target.value; });
    pintarArmador();
    requestAnimationFrame(bucleArmador);
  }

  // ---------- carga del simulador (iframe) con barra ----------
  function vigilarCargaSim() {
    const f = $("#iframeSim"), caja = $("#cargaSim"); if (!f || !caja) return;
    const t0 = Date.now();
    const reloj = setInterval(() => { $("#cargaSimSeg").textContent = Math.round((Date.now() - t0) / 1000) + " s"; }, 500);
    let hecho = false;
    const listo = () => { if (hecho) return; hecho = true; clearInterval(reloj); caja.classList.add("lista"); setTimeout(() => { caja.hidden = true; }, 450); };
    f.addEventListener("load", listo);
    try { if (f.contentDocument && f.contentDocument.readyState === "complete" && f.contentDocument.URL.indexOf("preview.html") >= 0) listo(); } catch (e) { /* nada */ }
  }

  // ---------- navegación a un paso desde los botones ----------
  function irA(id) {
    const s = document.getElementById("paso-" + id);
    if (!s) return;
    if (pasos && typeof pasos.ir === "function") {
      const lista = pasos.secciones || Array.from(document.querySelectorAll("#guia .paso"));
      pasos.ir(lista.indexOf(s));
    } else s.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ---------- arranque ----------
  async function iniciar() {
    iniciarLab();
    iniciarArmador();
    dibujarPezMini();
    vigilarCargaSim();
    document.querySelectorAll(".pestana").forEach((b) => b.addEventListener("click", () => mostrarCodigo(b.dataset.archivo)));
    $("#bCopiar").addEventListener("click", copiar);
    document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => irA(b.dataset.ir)));
    mostrarCodigo("pez3_esp32.py");

    const app = A();
    let manifiesto = null;
    try { if (app && app.iniciar) manifiesto = await app.iniciar(); } catch (e) { /* sigue sin el servidor */ }

    // "Qué pide": la checklist del framework (se marca sola al abrir el simulador) o una lista simple.
    let lista = null;
    if (app && app.checklist) {
      try { lista = app.checklist($("#checklist")); } catch (e) { console.warn(e); }
    } else {
      let pide = (manifiesto && manifiesto.pide) || [];
      if (!pide.length) { try { pide = (await (await fetch(REPO + "probar.json")).json()).pide || []; } catch (e) { /* nada */ } }
      $("#checklist").innerHTML = '<ul class="pide-simple"></ul>';
      for (const p of [].concat(pide)) { const li = document.createElement("li"); li.textContent = p; $("#checklist ul").appendChild(li); }
    }

    // Ver el pez armado completo cubre "dibujar una figura propia" (se puede marcar a mano también).
    document.addEventListener("pez-completo", () => {
      if (lista && manifiesto && manifiesto.pide) lista.marcar([].concat(manifiesto.pide)[2]);
    });

    // Botón "abrir el simulador en grande" (acción html "preview" del probar.json).
    if (app && app.panelEjecucion) {
      try { app.panelEjecucion($("#panelPreview"), "preview", {
        titulo: "El simulador en una ventana aparte",
        queVaAPasar: "Se abre el mismo osciloscopio simulado en una pestaña nueva, a pantalla completa.",
        botonTexto: "Abrir el simulador en grande" }); } catch (e) { console.warn(e); }
    } else {
      $("#panelPreview").innerHTML = '<a class="boton-pri" target="_blank" rel="noopener" href="' + REPO + 'preview.html">Abrir el simulador en grande ↗</a>';
    }

    // Imágenes ampliables al clic.
    document.querySelectorAll(".galeria img, #gifPortada").forEach((img) => { if (app && app.imagen) app.imagen(img); });

    // Asistente paso a paso (o todo seguido si el framework no está).
    // Ver los videos del laboratorio es la prueba de "usar el ESP32 como generador hacia el
    // osciloscopio" (no se puede repetir sin el equipo): se marca al abrir ese paso.
    const alCambiar = (i, seccion) => {
      if (lista && seccion && seccion.id === "paso-resultados" && manifiesto && manifiesto.pide) lista.marcar([].concat(manifiesto.pide)[0]);
    };
    if (app && app.pasos) {
      try { pasos = app.pasos($("#guia"), { alCambiar }); setTimeout(() => pasos && alCambiar(pasos.actual, pasos.secciones[pasos.actual]), 400); } catch (e) { console.warn(e); $("#guia").classList.add("sin-pasos"); }
    } else {
      $("#guia").classList.add("sin-pasos");
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
