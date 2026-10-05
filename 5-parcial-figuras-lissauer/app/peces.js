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

  // ---------- navegación a un paso desde los botones de la portada ----------
  function irA(id) {
    const s = document.getElementById("paso-" + id);
    if (!s) return;
    if (pasos && typeof pasos.ir === "function") {
      const lista = Array.from(document.querySelectorAll("#guia .paso"));
      pasos.ir(lista.indexOf(s));
    }
    s.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // ---------- arranque ----------
  async function iniciar() {
    iniciarLab();
    dibujarPezMini();
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
