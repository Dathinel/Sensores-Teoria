// App del tema 7: explica el jog, simula el teclado 4x4 con la misma lógica de esp32_brazo.py (y dibuja
// el brazo de lado y desde arriba con la cinemática de brazo.urdf), lanza la simulación de PyBullet
// (vía /comun/app.js) y embebe preview.html. App.marco arma la ventana tipo Docker Desktop.
(function () {
  "use strict";
  const CARPETA = "7-brazo-robotico-urdf";
  const BASE = "/repo/" + CARPETA + "/";
  const A = window.App || null;
  const tiene = (f) => A && typeof A[f] === "function";

  // ── Teclado 4x4 (mismo MAPA_TECLAS y pasos que esp32_brazo.py) ─────────────────────────
  const MAPA = [["1", "2", "3", "A"], ["4", "5", "6", "B"], ["7", "8", "9", "C"], ["*", "0", "#", "D"]];
  const FUNC = {
    "8": ["Base +", "var(--b-azul)"], "2": ["Base −", "var(--b-azul)"],
    "6": ["Codo +", "var(--b-verde)"], "4": ["Codo −", "var(--b-verde)"],
    "9": ["Abre", "var(--b-naranja)"], "7": ["Cierra", "var(--b-naranja)"],
    "5": ["Home", "var(--b-rosa)"],
  };
  const PASO = { j1: 0.05, j2: 0.05, g: 0.005 };
  const LIM = { j1: [-2.5, 2.5], j2: [-2.0, 2.0], g: [0.0, 0.15] };
  const pos = { j1: 0, j2: 0, g: 0 };
  let teclaAbajo = null;
  const botones = {};

  const keypad = document.getElementById("keypad");
  MAPA.flat().forEach((t) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "b-tecla"; b.dataset.t = t;
    b.innerHTML = t + (FUNC[t] ? "<small>" + FUNC[t][0] + "</small>" : "");
    if (FUNC[t]) { b.classList.add("viva"); b.style.setProperty("--c", FUNC[t][1]); }
    else b.title = "Esta tecla no hace nada";
    b.addEventListener("pointerdown", (e) => { e.preventDefault(); presionar(t); });
    keypad.appendChild(b); botones[t] = b;
  });
  const soltar = () => { if (teclaAbajo) botones[teclaAbajo].classList.remove("abajo"); teclaAbajo = null; };
  function presionar(t) {
    if (!FUNC[t]) return;
    soltar(); teclaAbajo = t; botones[t].classList.add("abajo");
    tick();                                     // el primer paso se nota al instante
  }
  window.addEventListener("pointerup", soltar);
  window.addEventListener("blur", soltar);
  document.addEventListener("keydown", (e) => {
    if (e.repeat || e.target.closest("input, textarea")) return;
    if (FUNC[e.key] && !document.getElementById("s-teclado").hidden) presionar(e.key);
  });
  document.addEventListener("keyup", (e) => { if (e.key === teclaAbajo) soltar(); });

  const limitar = (v, [lo, hi]) => Math.max(lo, Math.min(hi, v));
  function tick() {
    const t = teclaAbajo;
    if (t === "8") pos.j1 = limitar(pos.j1 + PASO.j1, LIM.j1);
    else if (t === "2") pos.j1 = limitar(pos.j1 - PASO.j1, LIM.j1);
    else if (t === "6") pos.j2 = limitar(pos.j2 + PASO.j2, LIM.j2);
    else if (t === "4") pos.j2 = limitar(pos.j2 - PASO.j2, LIM.j2);
    else if (t === "9") pos.g = limitar(pos.g + PASO.g, LIM.g);
    else if (t === "7") pos.g = limitar(pos.g - PASO.g, LIM.g);
    else if (t === "5") { pos.j1 = pos.j2 = pos.g = 0; }
    document.getElementById("lecTecla").textContent = t || "—";
    document.getElementById("lecJ1").textContent = pos.j1.toFixed(3);
    document.getElementById("lecJ2").textContent = pos.j2.toFixed(3);
    document.getElementById("lecG").textContent = pos.g.toFixed(3);
    document.getElementById("lineaSerial").textContent =
      `J1:${pos.j1.toFixed(3)},J2:${pos.j2.toFixed(3)},G:${pos.g.toFixed(3)}`;
    const cam = document.querySelector(".b-camino"); if (cam) cam.classList.toggle("activo", !!t);
    dibujarBrazo();
  }
  setInterval(tick, 100);                       // time.sleep(0.1) del firmware

  // ── El brazo de lado y desde arriba (cinemática directa de brazo.urdf) ──────────────────
  // base 0,15 m de alto; brazo1 de 0,35 m (gira con J1 alrededor de Z); en su punta, joint_2
  // (eje Y) dobla el brazo2 de 0,30 m; la pinza sube g por el brazo2 y cada dedo se abre g/3.
  const NS = "http://www.w3.org/2000/svg";
  function svg(el, tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); el.appendChild(e); return e; }
  const lado = document.getElementById("vistaLado"), arriba = document.getElementById("vistaArriba");
  const L = {}, U = {};
  if (lado) {
    svg(lado, "line", { x1: -0.7, y1: 0, x2: 0.7, y2: 0, stroke: "#3a4048", "stroke-width": 0.008 });
    svg(lado, "rect", { x: -0.25, y: -0.15, width: 0.5, height: 0.15, rx: 0.02, fill: "#3b4148" });
    svg(lado, "path", { d: "M 0 -0.5 m -0.42 0 a 0.42 0.42 0 0 1 0.84 0", fill: "none", stroke: "#2a3037", "stroke-width": 0.006, "stroke-dasharray": "0.02 0.02" });
    L.b1 = svg(lado, "line", { x1: 0, y1: -0.15, x2: 0, y2: -0.5, stroke: "#4f8fce", "stroke-width": 0.1, "stroke-linecap": "round" });
    L.b2 = svg(lado, "line", { stroke: "#e0913a", "stroke-width": 0.08, "stroke-linecap": "round" });
    L.pinza = svg(lado, "g", {});
    L.base = svg(L.pinza, "rect", { x: -0.04, y: -0.02, width: 0.08, height: 0.04, fill: "#d64545" });
    L.dI = svg(L.pinza, "rect", { y: -0.12, width: 0.03, height: 0.12, fill: "#e6e6e6" });
    L.dD = svg(L.pinza, "rect", { y: -0.12, width: 0.03, height: 0.12, fill: "#e6e6e6" });
    L.codo = svg(lado, "circle", { cx: 0, cy: -0.5, r: 0.035, fill: "#4caf7d" });
    L.txt = svg(lado, "text", { x: -0.72, y: -1.04, fill: "#8b929b", "font-size": 0.06, "font-family": "IBM Plex Mono, monospace" });
  }
  if (arriba) {
    svg(arriba, "circle", { cx: 0, cy: 0, r: 0.25, fill: "#3b4148" });
    svg(arriba, "circle", { cx: 0, cy: 0, r: 0.62, fill: "none", stroke: "#2a3037", "stroke-width": 0.006, "stroke-dasharray": "0.02 0.02" });
    svg(arriba, "path", { d: "M 0 0 L 0.62 0", stroke: "#2a3037", "stroke-width": 0.006 });
    U.arco = svg(arriba, "path", { fill: "none", stroke: "#4f8fce", "stroke-width": 0.012 });
    U.brazo = svg(arriba, "line", { x1: 0, y1: 0, stroke: "#e0913a", "stroke-width": 0.08, "stroke-linecap": "round" });
    U.eje = svg(arriba, "circle", { cx: 0, cy: 0, r: 0.06, fill: "#4f8fce" });
    U.txt = svg(arriba, "text", { x: -0.72, y: -0.66, fill: "#8b929b", "font-size": 0.06, "font-family": "IBM Plex Mono, monospace" });
  }
  function dibujarBrazo() {
    if (!lado || !arriba) return;
    const { j1, j2, g } = pos;
    // De lado (plano que contiene al brazo): el codo está a 0,50 m; el brazo2 apunta (sin j2, cos j2)
    const cx = 0, cz = 0.5, dx = Math.sin(j2), dz = Math.cos(j2);
    const px = cx + dx * 0.30, pz = cz + dz * 0.30;           // punta del brazo2
    L.b2.setAttribute("x1", cx); L.b2.setAttribute("y1", -cz); L.b2.setAttribute("x2", px); L.b2.setAttribute("y2", -pz);
    const gx = cx + dx * (0.30 + g), gz = cz + dz * (0.30 + g); // la pinza sube g por el brazo2
    const abre = g / 3;
    L.dI.setAttribute("x", -0.055 - abre - 0.015); L.dD.setAttribute("x", 0.055 + abre - 0.015);
    L.pinza.setAttribute("transform", `translate(${gx} ${-gz}) rotate(${(j2 * 180 / Math.PI).toFixed(2)})`);
    L.txt.textContent = `J2 ${(j2 * 180 / Math.PI).toFixed(0)}°  G ${(g * 100).toFixed(1)} cm`;
    // Desde arriba: el alcance horizontal es sin(j2)·(0,30+g), girado j1 alrededor de Z
    const alcance = Math.max(0.06, Math.abs(dx) * (0.30 + g) + 0.06) * Math.sign(dx || 1);
    const ux = Math.cos(j1) * alcance, uy = -Math.sin(j1) * alcance;
    U.brazo.setAttribute("x2", ux); U.brazo.setAttribute("y2", uy);
    const r = 0.36, a = -j1;
    U.arco.setAttribute("d", `M ${r} 0 A ${r} ${r} 0 ${Math.abs(j1) > Math.PI ? 1 : 0} ${j1 > 0 ? 0 : 1} ${r * Math.cos(a)} ${r * Math.sin(a)}`);
    U.txt.textContent = `J1 ${(j1 * 180 / Math.PI).toFixed(0)}°`;
  }
  dibujarBrazo();

  // ── La cinta de 8 pines ────────────────────────────────────────────────────────────────
  const CINTA = [["R1", "GPIO14"], ["R2", "GPIO27"], ["R3", "GPIO26"], ["R4", "GPIO25"],
                 ["C1", "GPIO33"], ["C2", "GPIO32"], ["C3", "GPIO18"], ["C4", "GPIO19"]];
  document.getElementById("cinta").innerHTML = CINTA.map(([c, g]) =>
    `<div class="b-pin" style="--c:${c[0] === "R" ? "var(--b-azul)" : "var(--b-verde)"}"><b>${c}</b><span>${g}</span></div>`).join("");

  // ── preview.html embebido (Web Serial necesita allow="serial"): se carga al ver su sección ──
  const cargarPreview = () => { const f = document.getElementById("marcoPreview"); if (!f.getAttribute("src")) f.src = BASE + "preview.html"; };

  // ── Código del firmware ────────────────────────────────────────────────────────────────
  fetch(BASE + "esp32_brazo.py").then((r) => r.ok ? r.text() : Promise.reject())
    .then((t) => { document.getElementById("codigoFw").textContent = t; })
    .catch(() => { document.getElementById("codigoFw").textContent = "No se pudo cargar el archivo esp32_brazo.py."; });

  // ── Imágenes ampliables ────────────────────────────────────────────────────────────────
  function visorPropio(img) {
    const v = document.createElement("div"); v.className = "b-visor";
    const i = document.createElement("img"); i.src = img.src; i.alt = img.alt; v.appendChild(i);
    v.addEventListener("click", () => v.remove()); document.body.appendChild(v);
  }
  document.querySelectorAll(".b-ampliable").forEach((img) => {
    if (tiene("imagen")) { try { A.imagen(img); return; } catch (e) { /* abajo */ } }
    img.addEventListener("click", () => visorPropio(img));
  });

  // ── Barra "se está abriendo" mientras PyBullet arranca ─────────────────────────────────
  function barraArranque(el, texto, seg, listo) {
    const caja = document.createElement("div"); caja.className = "b-arranque"; caja.hidden = true;
    caja.innerHTML = '<div class="b-arr-txt"></div><div class="b-arr-barra"><div></div></div>';
    let t0 = 0, reloj = null, abierto = false;
    const pintar = () => {
      const s = (Date.now() - t0) / 1000, f = s <= seg ? 0.92 * s / seg : 0.92 + 0.07 * (1 - Math.exp(-(s - seg) / seg));
      caja.querySelector(".b-arr-barra div").style.width = Math.round(f * 100) + "%";
      caja.querySelector(".b-arr-txt").innerHTML = `<b>${texto}</b> lleva ${Math.round(s)} s ` + (s <= seg * 1.2 ? `de ~${seg} s` : "(tarda más de lo normal; si la salida avanza, va bien)");
    };
    const parar = () => { clearInterval(reloj); reloj = null; caja.hidden = true; };
    return {
      montar() { const ref = el.querySelector(".app-panel-estado"); if (ref) ref.after(caja); else el.prepend(caja); },
      alEstado(t) {
        if (!t) return;
        if (t.estado === "lanzada" && !abierto && !reloj) { t0 = Date.now(); caja.hidden = false; pintar(); reloj = setInterval(pintar, 500); }
        if (["terminada", "error", "detenida"].includes(t.estado)) { parar(); abierto = false; }
      },
      alLinea(x) { if (!abierto && listo.test(x)) { abierto = true; parar(); } },
    };
  }

  // ── Integración con /comun/app.js ──────────────────────────────────────────────────────
  async function arrancar() {
    let marco = null;
    const irA = (id) => { if (marco) marco.ir(id); else { const s = document.getElementById(id); if (s) s.scrollIntoView({ behavior: "smooth" }); } };
    document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => irA(b.dataset.ir)));
    // Trozos del README que se cargan al abrir su "details"
    document.querySelectorAll("details .b-md[data-md]").forEach((caja) => {
      const det = caja.closest("details");
      det.addEventListener("toggle", () => {
        if (!det.open || caja.dataset.cargado) return;
        caja.dataset.cargado = "1";
        if (tiene("markdown")) A.markdown(caja, caja.dataset.md, { desde: caja.dataset.desde, hasta: caja.dataset.hasta });
        else caja.innerHTML = '<a href="' + BASE + 'README.md" target="_blank" rel="noopener">Abrir el README</a>';
      });
    });
    if (!A) {
      document.getElementById("checklist").innerHTML =
        '<p class="b-muted b-chico">Abre esta app con ABRIR.bat para ver la lista de la actividad.</p>';
      document.getElementById("panelSim").innerHTML =
        '<p class="b-muted b-chico">El botón para iniciar la simulación aparece al abrir la app con ABRIR.bat.</p>';
      cargarPreview();
      return;
    }
    try { await A.iniciar(); } catch (e) { console.warn("App.iniciar:", e); }
    if (tiene("marco")) {
      try {
        marco = A.marco({ titulo: "Brazo robótico: control por teclado (jog) + simulación URDF", num: "7",
          alCambiar: (i, sec) => { if (sec.id === "s-preview") cargarPreview(); } });
        if (marco.secciones[marco.actual].id === "s-preview") cargarPreview();
      } catch (e) { console.warn(e); cargarPreview(); }
    } else cargarPreview();
    try { A.checklist(document.getElementById("checklist")); } catch (e) { console.warn(e); }
    try {
      const el = document.getElementById("panelSim");
      const arr = barraArranque(el, "Abriendo PyBullet…", 8, /Ventana de PyBullet abierta/);
      A.panelEjecucion(el, "sim", {
        titulo: "Simulación del brazo en PyBullet",
        botonTexto: "Iniciar la simulación",
        queVaAPasar: "Se abre una ventana aparte de PyBullet con el brazo en 3D (puede quedar detrás de esta: búscala en la barra de tareas). Sin ESP32, aquí abajo aparece 'No se encontro el ESP32 en COM7: se usan los botones de jog'. Es normal.",
        queHacer: ["En el panel derecho de la ventana, haz clic en joint_1 (base) + / − para girar la base.", "joint_2 (codo) + / − dobla el codo; pinza + / − abre y cierra la pinza.", "Home (0, 0, 0) devuelve todo a cero. Para terminar, cierra la ventana o pulsa Detener aquí."],
        queDeberiasVer: "El brazo moviéndose en la ventana y, arriba de ella en verde, 'Serial: sin ESP32 (modo botones)'.",
        alEstado: (t) => arr.alEstado(t), alLinea: (x) => arr.alLinea(x),
      });
      arr.montar();
    } catch (e) { console.warn(e); }
    try {
      A.panelEjecucion(document.getElementById("panelPreview"), "preview", {
        titulo: "La versión del navegador, a pantalla completa",
        botonTexto: "Abrir en su propia pestaña",
        queVaAPasar: "La misma página de arriba, en una pestaña nueva.",
      });
    } catch (e) { console.warn(e); }
    try {
      if (tiene("markdown"))
        await A.markdown(document.getElementById("mdUrdf"), "README.md", { desde: "## Qué es un URDF", hasta: "## Qué es PyBullet" });
    } catch (e) { console.warn(e); }
  }
  arrancar();
})();
