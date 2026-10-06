// App del tema 6: explica los gestos, simula los LEDs con la misma lógica de esp32_gestos.py
// (con la cadena cámara → MediaPipe → filtro → orden → USB → ESP32 animada en cada gesto) y abre
// el reconocedor real (gesture_control.html) dentro de la app con una barra de carga de MediaPipe.
(function () {
  "use strict";
  const CARPETA = "6-control-de-led-mediante-gestos";
  const BASE = "/repo/" + CARPETA + "/";
  const A = window.App || null;
  const $ = (id) => document.getElementById(id);
  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

  // ── Simulación del firmware (copia de manejar_comando() de esp32_gestos.py) ───────────
  const INT = { amarillo: 0.30, azul: 0.70, rojo: 1.0 };
  const brillo = { amarillo: 0, azul: 0, rojo: 0 };
  const nodos = {
    amarillo: [$("ledAmarillo"), $("pctAmarillo")],
    azul: [$("ledAzul"), $("pctAzul")],
    rojo: [$("ledRojo"), $("pctRojo")],
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
  // Igual que parar_secuencia_si_activa() del firmware: si un modo estaba corriendo, se detiene
  // el timer Y se apaga todo; si no, el LED que el modo dejó prendido quedaría encendido y el
  // "alternar" del gesto siguiente partiría de ese brillo (puño tras Modo 1 apagaba el amarillo).
  function pararModo() { if (timerModo) { clearInterval(timerModo); timerModo = null; apagarTodo(); } }
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
  function marcarTarjetas(ultimo) {
    // La tarjeta queda marcada mientras su efecto siga vivo (LED prendido o modo corriendo).
    const modo = ultimo.startsWith("THUMB") ? ultimo : "";
    document.querySelectorAll(".g-gesto").forEach((x) => {
      const c = x.dataset.cmd, led = { FIST: "amarillo", VICTORY: "azul", OPEN2: "rojo" }[c];
      x.classList.toggle("activo", led ? (!timerModo && brillo[led] > 0) : (c === modo));
    });
  }

  // ── Monitor serie simulado: lo que pasaría por el cable ─────────────────────────────────
  function monitor(texto, tipo) {
    const ol = $("monitor"); if (!ol) return;
    const vacio = ol.querySelector(".g-muted"); if (vacio) vacio.remove();
    const li = document.createElement("li"); li.className = tipo; li.textContent = texto;
    ol.appendChild(li);
    while (ol.children.length > 6) ol.firstChild.remove();
  }

  // ── La cadena de la mano al LED, animada etapa por etapa ───────────────────────────────
  const ETAPAS = ["camara", "mediapipe", "filtro", "orden", "usb", "esp32"];
  const cuadros = $("cuadros");
  for (let i = 0; i < 15; i++) cuadros.appendChild(document.createElement("i"));
  let corrida = 0;   // si se pulsa otro gesto a mitad de camino, la animación vieja se corta
  function etapa(nombre, estado) {
    const li = document.querySelector('#cadena [data-etapa="' + nombre + '"]');
    if (li) { li.classList.remove("activa", "hecha"); if (estado) li.classList.add(estado); }
  }
  async function recorrerCadena(boton) {
    const id = ++corrida, vigente = () => id === corrida;
    const cmd = boton.dataset.cmd, mano = boton.querySelector(".g-mano").textContent, nombre = boton.dataset.nombre;
    ETAPAS.forEach((e) => etapa(e, ""));
    cuadros.querySelectorAll("i").forEach((c) => { c.className = ""; });
    $("etOrden").textContent = "—"; $("etUsb").textContent = "—"; $("etEsp").textContent = "—";
    // 1. cámara
    etapa("camara", "activa"); $("etCamara").textContent = cmd === "NONE" ? "sin mano a la vista" : "ve la mano " + mano;
    await dormir(260); if (!vigente()) return; etapa("camara", "hecha");
    // 2. MediaPipe: nombre del gesto y confianza (inventada pero típica: 0,82-0,97)
    etapa("mediapipe", "activa");
    const conf = (0.82 + Math.random() * 0.15).toFixed(2).replace(".", ",");
    $("etMediapipe").textContent = cmd === "NONE" ? "None (ninguna mano)" : nombre + " · " + conf;
    await dormir(320); if (!vigente()) return; etapa("mediapipe", "hecha");
    // 3. filtro: 15 cuadros; 1 o 2 salen "dudosos" (ruido), igual alcanza el 80 %
    etapa("filtro", "activa");
    const malos = new Set([3 + Math.floor(Math.random() * 5), 9 + Math.floor(Math.random() * 4)].slice(0, 1 + Math.round(Math.random())));
    const celdas = cuadros.querySelectorAll("i");
    for (let i = 0; i < 15; i++) {
      celdas[i].className = malos.has(i) ? "malo" : "bueno";
      $("etFiltro").textContent = (i + 1 - [...malos].filter((m) => m <= i).length) + " de " + (i + 1) + " cuadros";
      await dormir(45); if (!vigente()) return;
    }
    $("etFiltro").textContent = (15 - malos.size) + " de 15 ≥ 80 % ✓ confirmado";
    await dormir(200); if (!vigente()) return; etapa("filtro", "hecha");
    // 4. orden, 5. USB
    etapa("orden", "activa"); $("etOrden").textContent = cmd;
    await dormir(260); if (!vigente()) return; etapa("orden", "hecha");
    etapa("usb", "activa"); $("etUsb").textContent = cmd + "\\n"; monitor("→ " + cmd, "sale");
    await dormir(300); if (!vigente()) return; etapa("usb", "hecha");
    // 6. ESP32: aplica el PWM y contesta
    etapa("esp32", "activa"); comando(cmd); marcarTarjetas(cmd);
    $("etEsp").textContent = "OK " + cmd; monitor("← OK " + cmd, "entra");
    await dormir(400); if (!vigente()) return; etapa("esp32", "hecha");
  }

  document.querySelectorAll(".g-gesto").forEach((b) => {
    b.addEventListener("click", () => { recorrerCadena(b); });
  });
  pintar();

  // ── Navegación desde los botones del inicio ────────────────────────────────────────────
  let guia = null;   // el asistente de App.pasos (si está)
  document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => {
    const sec = $("paso-" + b.dataset.ir);
    if (!sec) return;
    if (guia) guia.ir(guia.secciones.indexOf(sec)); else sec.scrollIntoView({ behavior: "smooth" });
  }));

  // ── Reconocedor embebido con barra de carga de MediaPipe ───────────────────────────────
  // gesture_control.html se sirve desde el mismo lanzador (mismo origen), así que se puede leer
  // su panel "Conexión con MediaPipe" (#estadoWasmSpan, #estadoModeloSpan, #estadoMediaPipeSpan).
  let vigilancia = null;
  function mmss(s) { return Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0"); }
  function pasoCarga(id, estado) { const li = $(id); li.classList.remove("hecho", "actual"); if (estado) li.classList.add(estado); }
  function vigilarCarga(iframe) {
    const caja = $("cargaMp"), barra = $("cargaMpBarra"), txt = $("cargaMpTxt");
    caja.hidden = false; $("cargaMpAviso").hidden = true; caja.classList.remove("ok", "mal");
    ["cmPagina", "cmWasm", "cmModelo", "cmListo"].forEach((x) => pasoCarga(x, ""));
    pasoCarga("cmPagina", "actual");
    const t0 = Date.now();
    let frac = 0.03;
    clearInterval(vigilancia);
    vigilancia = setInterval(() => {
      const seg = (Date.now() - t0) / 1000;
      $("cargaMpSeg").textContent = mmss(seg);
      let doc = null;
      try { doc = iframe.contentDocument; } catch (e) { /* otro origen: no debería pasar */ }
      const leer = (id) => { const el = doc && doc.getElementById(id); return el ? el.textContent.trim().toLowerCase() : ""; };
      const pagina = doc && doc.readyState === "complete" && /gesture_control/.test(doc.URL || "");
      const wasm = leer("estadoWasmSpan") === "cargado", modelo = leer("estadoModeloSpan") === "cargado";
      const general = leer("estadoMediaPipeSpan");
      let objetivo;
      if (general === "error") {
        clearInterval(vigilancia); caja.classList.add("mal");
        txt.textContent = "MediaPipe no cargó (¿sin internet?). Los botones de Control manual siguen funcionando.";
        $("cargaMpAviso").hidden = false; return;
      }
      if (modelo) {
        objetivo = 1; pasoCarga("cmPagina", "hecho"); pasoCarga("cmWasm", "hecho"); pasoCarga("cmModelo", "hecho"); pasoCarga("cmListo", "hecho");
        txt.textContent = "MediaPipe listo en " + mmss(seg) + ": haz un gesto frente a la cámara (o usa los botones).";
        caja.classList.add("ok"); clearInterval(vigilancia);
        setTimeout(() => { caja.hidden = true; }, 4000);
      } else if (wasm) {
        objetivo = 0.9; pasoCarga("cmPagina", "hecho"); pasoCarga("cmWasm", "hecho"); pasoCarga("cmModelo", "actual");
        txt.textContent = "Descargando el modelo de gestos (gesture_recognizer.task, ~8 MB)…";
      } else if (pagina) {
        objetivo = 0.5; pasoCarga("cmPagina", "hecho"); pasoCarga("cmWasm", "actual");
        txt.textContent = "Descargando el motor de MediaPipe (runtime WebAssembly)…";
      } else {
        objetivo = 0.15; txt.textContent = "Abriendo la página del reconocedor…";
      }
      // avanza suave hacia el objetivo de la etapa sin llegar nunca solo (la etapa real manda)
      frac = Math.min(objetivo, frac + (objetivo - frac) * 0.08 + 0.002);
      if (objetivo === 1) frac = 1;
      barra.style.width = Math.round(frac * 100) + "%";
      if (seg > 45 && !modelo) $("cargaMpAviso").hidden = false;
    }, 250);
  }
  $("btnEmbeber").addEventListener("click", (ev) => {
    const marco = $("marcoGestos");
    if (marco.hidden) {
      marco.innerHTML = "";
      const f = document.createElement("iframe");
      f.src = BASE + "gesture_control.html";
      f.title = "Reconocedor de gestos";
      f.allow = "camera; serial; microphone 'none'";
      marco.appendChild(f);
      marco.hidden = false;
      ev.target.textContent = "Cerrar el reconocedor (libera la cámara)";
      vigilarCarga(f);
    } else {
      clearInterval(vigilancia); $("cargaMp").hidden = true;
      marco.innerHTML = ""; marco.hidden = true;    // libera la cámara
      ev.target.textContent = "Abrir el reconocedor aquí";
    }
  });

  // ── Código del firmware (solo lectura, con botón copiar) ───────────────────────────────
  let textoFw = "";
  fetch(BASE + "esp32_gestos.py").then((r) => r.ok ? r.text() : Promise.reject())
    .then((t) => { textoFw = t; $("codigoFw").textContent = t; })
    .catch(() => { $("codigoFw").textContent = "No se pudo cargar el archivo esp32_gestos.py."; });
  $("btnCopiarFw").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(textoFw); if (A) A.aviso("Código copiado: pégalo en Thonny y guárdalo en la placa como main.py.", "ok"); }
    catch (e) {
      const r = document.createRange(); r.selectNodeContents($("codigoFw"));
      const s = getSelection(); s.removeAllRanges(); s.addRange(r);
      if (A) A.aviso("Texto seleccionado: cópialo con Ctrl+C.", "info");
    }
  });

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
      $("checklist").innerHTML = '<p class="g-muted g-chico">Abre esta app con ABRIR.bat para ver la lista de la actividad.</p>';
      return;
    }
    try { await A.iniciar(); } catch (e) { console.warn("App.iniciar:", e); }
    try { if (typeof A.pasos === "function") guia = A.pasos($("pasos")); } catch (e) { console.warn(e); }
    try { A.checklist($("checklist")); } catch (e) { console.warn(e); }
    try {
      A.panelEjecucion($("panelWeb"), "web", {
        titulo: "El reconocedor en otra pestaña",
        botonTexto: "Abrir el reconocedor en otra pestaña",
        queVaAPasar: "Se abre en una pestaña nueva del navegador, servida por esta app, para que funcionen la cámara y la conexión USB. La primera vez descarga MediaPipe (unos segundos con internet).",
        queHacer: ["Acepta el permiso de la cámara y haz los gestos frente a ella.", "Sin cámara: usa los botones de 'Control manual'.", "'Conectar ESP32' solo hace falta si tienes la placa."],
        queDeberiasVer: "En 'Lectura en vivo', el gesto y su confianza; al confirmarse, el panel 'LEDs (espejo del firmware)' se prende como los LEDs reales.",
      });
    } catch (e) { console.warn(e); }
    try {
      if (typeof A.markdown === "function")
        await A.markdown($("mdFiltro"), "README.md", { desde: "## Cómo se evita que el LED", hasta: "## La idea general" });
    } catch (e) { console.warn(e); }
  }
  arrancar();
})();
