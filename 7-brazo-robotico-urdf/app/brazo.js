// App del tema 7: explica el jog, simula el teclado 4x4 con la misma lógica de esp32_brazo.py,
// lanza la simulación de PyBullet (vía /comun/app.js) y embebe preview.html.
(function () {
  "use strict";
  const CARPETA = "7-brazo-robotico-urdf";
  const BASE = "/repo/" + CARPETA + "/";
  const A = window.App || null;

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
    if (FUNC[e.key]) presionar(e.key);
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
  }
  setInterval(tick, 100);                       // time.sleep(0.1) del firmware

  // ── La cinta de 8 pines ────────────────────────────────────────────────────────────────
  const CINTA = [["R1", "GPIO14"], ["R2", "GPIO27"], ["R3", "GPIO26"], ["R4", "GPIO25"],
                 ["C1", "GPIO33"], ["C2", "GPIO32"], ["C3", "GPIO18"], ["C4", "GPIO19"]];
  document.getElementById("cinta").innerHTML = CINTA.map(([c, g]) =>
    `<div class="b-pin" style="--c:${c[0] === "R" ? "var(--b-azul)" : "var(--b-verde)"}"><b>${c}</b><span>${g}</span></div>`).join("");

  // ── preview.html embebido (Web Serial necesita allow="serial") ─────────────────────────
  document.getElementById("marcoPreview").src = BASE + "preview.html";

  // ── Navegación de la portada ───────────────────────────────────────────────────────────
  let guia = null;   // el asistente de App.pasos (si está)
  document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => {
    const sec = document.getElementById("paso-" + b.dataset.ir);
    if (!sec) return;
    if (guia) guia.ir(guia.secciones.indexOf(sec)); else sec.scrollIntoView({ behavior: "smooth" });
  }));

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
    if (A && typeof A.imagen === "function") { try { A.imagen(img); return; } catch (e) { /* abajo */ } }
    img.addEventListener("click", () => visorPropio(img));
  });

  // ── Integración con /comun/app.js ──────────────────────────────────────────────────────
  async function arrancar() {
    if (!A) {
      document.getElementById("checklist").innerHTML =
        '<p class="b-muted b-chico">Abre esta app con ABRIR.bat para ver la lista de la actividad.</p>';
      document.getElementById("panelSim").innerHTML =
        '<p class="b-muted b-chico">El botón para iniciar la simulación aparece al abrir la app con ABRIR.bat.</p>';
      return;
    }
    try { await A.iniciar(); } catch (e) { console.warn("App.iniciar:", e); }
    try { if (typeof A.pasos === "function") guia = A.pasos(document.getElementById("pasos")); } catch (e) { console.warn(e); }
    try { A.checklist(document.getElementById("checklist")); } catch (e) { console.warn(e); }
    try {
      A.panelEjecucion(document.getElementById("panelSim"), "sim", {
        titulo: "Simulación del brazo en PyBullet",
        botonTexto: "Iniciar la simulación",
        queVaAPasar: "Se abre una ventana aparte de PyBullet con el brazo en 3D (puede quedar detrás de esta: búscala en la barra de tareas). Sin ESP32, aquí abajo aparece 'No se encontro el ESP32 en COM7: se usan los botones de jog'. Es normal. La primera vez se prepara PyBullet (lo compila, unos 10 minutos): la barra te va contando.",
        queHacer: ["En el panel derecho de la ventana, haz clic en joint_1 (base) + / − para girar la base.", "joint_2 (codo) + / − dobla el codo; pinza + / − abre y cierra la pinza.", "Home (0, 0, 0) devuelve todo a cero. Cada clic mueve ~2,9° o 5 mm.", "Para terminar, cierra la ventana de PyBullet o pulsa Detener aquí."],
        queDeberiasVer: "El brazo moviéndose en la ventana y, arriba de ella en verde, 'Serial: sin ESP32 (modo botones)'.",
      });
    } catch (e) { console.warn(e); }
    try {
      A.panelEjecucion(document.getElementById("panelPreview"), "preview", {
        titulo: "La versión del navegador, a pantalla completa",
        botonTexto: "Abrir en su propia pestaña",
        queVaAPasar: "La misma página de arriba, en una pestaña nueva.",
      });
    } catch (e) { console.warn(e); }
    try {
      if (typeof A.markdown === "function")
        await A.markdown(document.getElementById("mdUrdf"), "README.md",
          { desde: "## Qué es un URDF", hasta: "## Qué es PyBullet" });
    } catch (e) { console.warn(e); }
  }
  arrancar();
})();
