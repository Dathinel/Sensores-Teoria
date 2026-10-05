// App del tema 6: explica los gestos, simula los LEDs con la misma lógica de esp32_gestos.py
// y abre el reconocedor (gesture_control.html) servido por probar.py.
(function () {
  "use strict";
  const CARPETA = "6-control-de-led-mediante-gestos";
  const BASE = "/repo/" + CARPETA + "/";
  const A = window.App || null;

  // ── Simulación del firmware (copia de manejar_comando() de esp32_gestos.py) ───────────
  const INT = { amarillo: 0.30, azul: 0.70, rojo: 1.0 };
  const brillo = { amarillo: 0, azul: 0, rojo: 0 };
  const nodos = {
    amarillo: [document.getElementById("ledAmarillo"), document.getElementById("pctAmarillo")],
    azul: [document.getElementById("ledAzul"), document.getElementById("pctAzul")],
    rojo: [document.getElementById("ledRojo"), document.getElementById("pctRojo")],
  };
  let timerModo = null, pasoModo = 0;

  function pintar() {
    for (const k of Object.keys(brillo)) {
      const [led, pct] = nodos[k];
      led.style.setProperty("--b", brillo[k]);
      pct.textContent = Math.round(brillo[k] * 100) + " %";
    }
  }
  function apagarTodo() { brillo.amarillo = brillo.azul = brillo.rojo = 0; }
  function pararModo() { if (timerModo) { clearInterval(timerModo); timerModo = null; } }
  function alternar(k) { brillo[k] = brillo[k] > 0 ? 0 : INT[k]; }
  function iniciarModo(fn) {
    pararModo(); apagarTodo(); pasoModo = 0; fn(); pintar();
    timerModo = setInterval(() => { fn(); pintar(); }, 200);   // PERIODO_MODO_MS = 200
  }
  const modo1 = () => {        // barrido: uno solo al 100 %, amarillo → azul → rojo
    apagarTodo(); brillo[["amarillo", "azul", "rojo"][pasoModo % 3]] = 1; pasoModo++;
  };
  const modo2 = () => {        // parpadeo: pares prenden los tres, impares apagan
    const v = pasoModo % 2 === 0 ? 1 : 0; brillo.amarillo = brillo.azul = brillo.rojo = v; pasoModo++;
  };

  function comando(cmd) {
    document.getElementById("ultimoCmd").textContent = cmd + "   →   OK " + cmd;
    switch (cmd) {
      case "FIST": pararModo(); alternar("amarillo"); break;
      case "VICTORY": pararModo(); alternar("azul"); break;
      case "OPEN2": pararModo(); alternar("rojo"); break;
      case "THUMB_DOWN": iniciarModo(modo1); break;
      case "THUMB_UP": iniciarModo(modo2); break;
      case "NONE": pararModo(); apagarTodo(); break;
    }
    pintar();
  }

  document.querySelectorAll(".g-gesto").forEach((b) => {
    b.addEventListener("click", () => {
      comando(b.dataset.cmd);
      // La tarjeta queda marcada mientras su efecto siga vivo (LED prendido o modo corriendo).
      const modo = b.dataset.cmd.startsWith("THUMB") ? b.dataset.cmd : (timerModo ? null : "");
      document.querySelectorAll(".g-gesto").forEach((x) => {
        const c = x.dataset.cmd, led = { FIST: "amarillo", VICTORY: "azul", OPEN2: "rojo" }[c];
        x.classList.toggle("activo", led ? (!timerModo && brillo[led] > 0) : (c === modo));
      });
    });
  });
  pintar();

  // ── Navegación de la portada ───────────────────────────────────────────────────────────
  let guia = null;   // el asistente de App.pasos (si está)
  document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => {
    const sec = document.getElementById("paso-" + b.dataset.ir);
    if (!sec) return;
    if (guia) guia.ir(guia.secciones.indexOf(sec)); else sec.scrollIntoView({ behavior: "smooth" });
  }));

  // ── Reconocedor embebido (cámara y Web Serial necesitan allow en el iframe) ──────────
  document.getElementById("btnEmbeber").addEventListener("click", (ev) => {
    const marco = document.getElementById("marcoGestos");
    if (marco.hidden) {
      marco.innerHTML = "";
      const f = document.createElement("iframe");
      f.src = BASE + "gesture_control.html";
      f.title = "Reconocedor de gestos";
      f.allow = "camera; serial; microphone 'none'";
      marco.appendChild(f);
      marco.hidden = false;
      ev.target.textContent = "Quitar el reconocedor de esta página";
    } else {
      marco.innerHTML = ""; marco.hidden = true;    // libera la cámara
      ev.target.textContent = "Mostrar el reconocedor dentro de esta página";
    }
  });

  // ── Código del firmware (solo lectura) ─────────────────────────────────────────────────
  fetch(BASE + "esp32_gestos.py").then((r) => r.ok ? r.text() : Promise.reject())
    .then((t) => { document.getElementById("codigoFw").textContent = t; })
    .catch(() => { document.getElementById("codigoFw").textContent = "No se pudo cargar el archivo esp32_gestos.py."; });

  // ── Imágenes ampliables ────────────────────────────────────────────────────────────────
  function visorPropio(img) {
    const v = document.createElement("div"); v.className = "g-visor";
    const i = document.createElement("img"); i.src = img.src; i.alt = img.alt; v.appendChild(i);
    v.addEventListener("click", () => v.remove()); document.body.appendChild(v);
  }
  document.querySelectorAll(".g-ampliable").forEach((img) => {
    if (A && typeof A.imagen === "function") { try { A.imagen(img); return; } catch (e) { /* abajo */ } }
    img.addEventListener("click", () => visorPropio(img));
  });

  // ── Integración con /comun/app.js ──────────────────────────────────────────────────────
  async function arrancar() {
    if (!A) {
      document.getElementById("checklist").innerHTML =
        '<p class="g-muted g-chico">Abre esta app con ABRIR.bat para ver la lista de la actividad.</p>';
      return;
    }
    try { await A.iniciar(); } catch (e) { console.warn("App.iniciar:", e); }
    try { if (typeof A.pasos === "function") guia = A.pasos(document.getElementById("pasos")); } catch (e) { console.warn(e); }
    try { A.checklist(document.getElementById("checklist")); } catch (e) { console.warn(e); }
    try {
      A.panelEjecucion(document.getElementById("panelWeb"), "web", {
        titulo: "Abrir el reconocedor de gestos",
        botonTexto: "Abrir el reconocedor de gestos",
        queVaAPasar: "Se abre en una pestaña nueva del navegador, servida por esta app, para que funcionen la cámara y la conexión USB. La primera vez descarga MediaPipe (unos segundos con internet).",
        queHacer: ["Acepta el permiso de la cámara y haz los gestos frente a ella.", "Sin cámara: usa los botones de 'Control manual' (Puño, Victoria, Manos abiertas, Modo 1, Modo 2, Detener todo).", "'Conectar ESP32' solo hace falta si tienes la placa."],
        queDeberiasVer: "En 'Lectura en vivo', el gesto y su confianza; al confirmarse, el panel 'LEDs (espejo del firmware)' se prende como los LEDs reales.",
      });
    } catch (e) { console.warn(e); }
    try {
      if (typeof A.markdown === "function")
        await A.markdown(document.getElementById("mdFiltro"), "README.md",
          { desde: "## Cómo se evita que el LED", hasta: "## La idea general" });
    } catch (e) { console.warn(e); }
  }
  arrancar();
})();
