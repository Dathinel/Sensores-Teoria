/* Consola de mando del tema 9.
   Usa la API común (window.App, de /comun/app.js) para correr las simulaciones y mostrar su
   salida dentro de la página. Lo propio de esta app:
   - el armazón tipo Docker Desktop: barra de estado arriba (entorno, modelos, qué está en marcha),
     menú lateral con las secciones y una sola sección a la vista;
   - el teclado 4x4 interactivo con lo que hace cada tecla en cada simulación;
   - las pruebas visuales: la ruta A → B → C de los drones dibujada con lo que imprime la prueba,
     el tablero "medido contra el límite" de Baxter y la gráfica con/sin asistente de Atlas;
   - la barra de MB de la descarga de modelos. */
(function () {
  "use strict";

  // Carpeta de la práctica: sale de la URL /app/<carpeta>/ (así la app no depende del nombre).
  const partes = location.pathname.split("/").filter(Boolean);
  const CARPETA = partes[0] === "app" && partes[1] ? decodeURIComponent(partes[1]) : "9-taller-segundo-corte";
  const REPO = "/repo/" + encodeURIComponent(CARPETA) + "/";
  const repo = (rel) => REPO + rel.split("/").map(encodeURIComponent).join("/");
  const $ = (s) => document.querySelector(s);
  const NS = "http://www.w3.org/2000/svg";
  const coma = (n, d = 1) => Number(n).toFixed(d).replace(".", ",");

  function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
  function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* sin almacenamiento: no pasa nada */ } }
  function leer(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

  // ==========================================================================================
  // 1. Navegación: una sección a la vista, elegida en el menú lateral (como Docker Desktop).
  // ==========================================================================================
  const CLAVE_VISTA = "c9-vista:" + CARPETA;
  const alMostrar = {};   // vista -> función que se llama la primera vez que se muestra

  function mostrarVista(id, guardarla = true) {
    const vista = document.getElementById("v-" + id);
    if (!vista) return;
    document.querySelectorAll(".c9-vista").forEach((v) => { v.hidden = v !== vista; });
    document.querySelectorAll("#lateral [data-vista]").forEach((b) => b.classList.toggle("activo", b.dataset.vista === id));
    $("#principal").scrollTop = 0;
    if (guardarla) { guardar(CLAVE_VISTA, id); history.replaceState(null, "", "#" + id); }
    if (alMostrar[id]) { const f = alMostrar[id]; delete alMostrar[id]; f(); }
    document.body.classList.remove("menu-abierto");
  }

  function vistaInicial() {
    const h = location.hash.replace("#", "");
    if (h && document.getElementById("v-" + h)) return h;
    const g = leer(CLAVE_VISTA);
    return g && document.getElementById("v-" + g) ? g : "inicio";
  }

  // ==========================================================================================
  // 2. El teclado: qué hace cada tecla (sacado de Mando.tecla, procesar_tecla y los botones).
  //    tipo: jog | golpe | sostener | objetivo | nada ; boton: nombre del botón en la ventana.
  // ==========================================================================================
  const FILAS = [["1", "2", "3", "A"], ["4", "5", "6", "B"], ["7", "8", "9", "C"], ["*", "0", "#", "D"]];
  const NADA = { c: "—", t: "Sin uso en esta simulación.", tipo: "nada" };
  const MAPA = {
    drones: {
      "8": { c: "Adelante", t: "Corre el objetivo del líder 10 cm hacia +Y. Sostenida, unos 2 m/s.", tipo: "jog", boton: "Adelante (Y+)" },
      "2": { c: "Atrás", t: "Objetivo 10 cm hacia −Y.", tipo: "jog", boton: "Atras (Y-)" },
      "4": { c: "Izquierda", t: "Objetivo 10 cm hacia −X.", tipo: "jog", boton: "Izquierda (X-)" },
      "6": { c: "Derecha", t: "Objetivo 10 cm hacia +X.", tipo: "jog", boton: "Derecha (X+)" },
      "9": { c: "Subir", t: "Objetivo 10 cm más alto.", tipo: "jog", boton: "Subir (Z+)" },
      "7": { c: "Bajar", t: "Objetivo 10 cm más bajo; nunca baja del piso.", tipo: "jog", boton: "Bajar (Z-)" },
      "5": { c: "Detener", t: "El objetivo pasa a ser donde está el líder: se queda flotando ahí.", tipo: "objetivo", boton: "Detener" },
      "A": { c: "Ir a A", t: "Vuela directo a la esfera azul A (0; 0,9; 1,2 m).", tipo: "objetivo", boton: "Ir a A" },
      "B": { c: "Ir a B", t: "Vuela directo a la esfera naranja B (1,4; −0,6; 1,6 m).", tipo: "objetivo", boton: "Ir a B" },
      "C": { c: "Ir a C", t: "Vuela directo a la esfera verde C (−1,3; 0,4; 0,9 m).", tipo: "objetivo", boton: "Ir a C" },
      "D": { c: "Origen", t: "Vuelve al origen y aterriza ahí.", tipo: "objetivo", boton: "Home (origen)" },
      "*": { c: "Despegar", t: "Sube a 1 m de altura.", tipo: "objetivo", boton: "Despegar" },
      "#": { c: "Aterrizar", t: "Baja al piso y apaga los motores al tocarlo.", tipo: "objetivo", boton: "Aterrizar" },
      "0": { c: "Misión", t: "Misión automática: va a A, al llegar (a menos de 12 cm y casi quieto) pasa a B y luego a C. Cualquier otra tecla la cancela.", tipo: "objetivo", boton: "Mision A -> B -> C" },
    },
    baxter: {
      "8": { c: "Pinza +Y", t: "La pinza del brazo activo se corre 1,5 cm (30 cm/s sostenida), siempre mirando hacia abajo.", tipo: "jog", boton: "Adelante (Y+) [8]" },
      "2": { c: "Pinza −Y", t: "Pinza 1,5 cm hacia −Y.", tipo: "jog", boton: "Atras (Y-) [2]" },
      "4": { c: "Pinza −X", t: "Pinza 1,5 cm hacia −X.", tipo: "jog", boton: "Izquierda (X-) [4]" },
      "6": { c: "Pinza +X", t: "Pinza 1,5 cm hacia +X.", tipo: "jog", boton: "Derecha (X+) [6]" },
      "9": { c: "Subir", t: "Pinza 1,5 cm más alta.", tipo: "jog", boton: "Subir (Z+) [9]" },
      "7": { c: "Bajar", t: "Pinza 1,5 cm más baja; se detiene a la altura de agarre sin atravesar la mesa.", tipo: "jog", boton: "Bajar (Z-) [7]" },
      "5": { c: "Home", t: "Devuelve el brazo activo a su pose inicial.", tipo: "golpe", boton: "Home [5]" },
      "A": { c: "Abrir", t: "Abre la pinza y suelta el cubo.", tipo: "golpe", boton: "Abrir pinza [A]" },
      "B": { c: "Demo ejes", t: "Demo: recorre los extremos de la caja de trabajo en X, Y y Z.", tipo: "golpe", boton: "Demo: recorrer los 3 ejes [B]" },
      "C": { c: "Cerrar", t: "Cierra la pinza y agarra el cubo si está entre los dedos.", tipo: "golpe", boton: "Cerrar pinza [C]" },
      "D": { c: "Demo cubo", t: "Demo: coge el cubo y lo lleva al destino con el brazo activo (unos 9 s). Mientras corre no se leen teclas.", tipo: "golpe", boton: "Demo: coger y mover [D]" },
      "*": { c: "Brazo", t: "Cambia el brazo activo (izquierdo ↔ derecho). El otro se queda quieto, sostenido por sus motores.", tipo: "golpe", boton: "Cambiar de brazo [*]" },
      "0": { c: "Reponer", t: "Suelta el cubo y lo pone otra vez en el origen.", tipo: "golpe", boton: "Reponer cubo [0]" },
    },
    atlas: {
      "8": { c: "Caminar", t: "Sostenida: camina hacia adelante; al soltar frena (rampa de 0,6 s).", tipo: "sostener", boton: "Caminar adelante on/off (8)" },
      "2": { c: "Atrás", t: "Sostenida: camina hacia atrás.", tipo: "sostener", boton: "Caminar atras on/off (2)" },
      "4": { c: "Girar izq.", t: "Sostenida: gira a la izquierda dando pasos en el lugar.", tipo: "sostener", boton: "Girar izquierda on/off (4)" },
      "6": { c: "Girar der.", t: "Sostenida: gira a la derecha dando pasos en el lugar.", tipo: "sostener", boton: "Girar derecha on/off (6)" },
      "1": { c: "Junta A −", t: "Mueve la primera junta del grupo activo 0,03 rad (0,15 por clic en la ventana), sin pasar del límite.", tipo: "jog", boton: "Junta A - (1)" },
      "3": { c: "Junta A +", t: "Primera junta del grupo, hacia el otro lado.", tipo: "jog", boton: "Junta A + (3)" },
      "7": { c: "Junta B −", t: "Segunda junta del grupo. En piernas mueve cadera, rodilla y tobillo a la vez para agacharlo con los pies planos.", tipo: "jog", boton: "Junta B - (7)" },
      "9": { c: "Junta B +", t: "Segunda junta del grupo, hacia el otro lado.", tipo: "jog", boton: "Junta B + (9)" },
      "5": { c: "De pie", t: "Pose de pie y detiene la caminata.", tipo: "golpe", boton: "De pie / detener (5)" },
      "A": { c: "Asistente", t: "Prende o apaga el asistente de equilibrio (arnés virtual: sostiene la mitad del peso y endereza la cadera).", tipo: "golpe", boton: "Asistente ON/OFF (A)" },
      "B": { c: "Levantar", t: "Lo pone de pie donde está, lo asienta 0,6 s con asistente y deja el asistente como estaba.", tipo: "golpe", boton: "Ponerlo de pie (B)" },
      "C": { c: "Saludar", t: "Pose: saludar (rampa suave de 0,6 s).", tipo: "golpe", boton: "Saludar (C)" },
      "D": { c: "Agacharse", t: "Pose: agacharse.", tipo: "golpe", boton: "Agacharse (D)" },
      "*": { c: "Grupo", t: "Siguiente grupo de juntas: brazo izquierdo → brazo derecho → torso y cabeza → piernas.", tipo: "golpe", boton: "Siguiente grupo (*)" },
      "#": { c: "Brazos ↑", t: "Pose: brazos arriba.", tipo: "golpe", boton: "Brazos arriba (#)" },
      "0": { c: "Reiniciar", t: "Reinicia todo en el origen, con el asistente prendido.", tipo: "golpe", boton: "Reiniciar todo (0)" },
    },
  };
  const NOMBRE_SIM = { drones: "a) Drones", baxter: "b) Baxter", atlas: "c) Atlas" };
  const NOMBRE_TIPO = {
    jog: "jog: sostener = seguir moviéndose", golpe: "un golpe: actúa una vez al apretar",
    sostener: "sostener: dura mientras está apretada", objetivo: "fija un objetivo (repetirlo no cambia nada)", nada: "sin uso",
  };
  const COLOR_TIPO = { jog: "var(--c9-jog)", golpe: "var(--c9-golpe)", sostener: "var(--c9-sostener)", objetivo: "var(--c9-objetivo)", nada: "var(--c9-nada)" };
  const NOTA_SIM = {
    drones: "En los drones todas las teclas actúan en cada línea que manda el ESP32: las de movimiento suman 10 cm al objetivo y las demás fijan un objetivo. Sin ESP32: 14 botones en el panel Params de la ventana.",
    baxter: "Baxter separa jog (8 2 4 6 9 7, en cada línea) de las de un golpe (5 A B C D 0 *, solo al apretar). Sin ESP32: 13 botones en el panel de la ventana.",
    atlas: "Atlas combina las tres: jog de juntas (1 3 7 9), un golpe (A B C D # 5 * 0) y sostener para caminar (8 2 4 6). Sin ESP32: 16 botones; caminar y girar se prenden con un clic y se apagan con el siguiente.",
  };

  let simActual = "drones";
  let teclaActual = "0";
  const dato = (sim, k) => MAPA[sim][k] || NADA;

  function pintarTeclado() {
    const cont = $("#teclado");
    if (!cont) return;
    cont.innerHTML = "";
    cont.style.setProperty("--sim", { drones: "var(--c9-drones)", baxter: "var(--c9-baxter)", atlas: "var(--c9-atlas)" }[simActual]);
    FILAS.flat().forEach((k) => {
      const d = dato(simActual, k);
      const b = document.createElement("button");
      b.type = "button";
      b.className = "c9-tecla" + (d.tipo === "nada" ? " vacia" : "") + (k === teclaActual ? " activa" : "");
      b.style.setProperty("--tipo", COLOR_TIPO[d.tipo]);
      b.dataset.k = k;
      b.setAttribute("aria-label", "Tecla " + k + ": " + d.c);
      b.innerHTML = '<span class="s">' + esc(k) + '</span><span class="q">' + esc(d.c) + "</span>";
      b.addEventListener("click", () => elegirTecla(k));
      cont.appendChild(b);
    });
    $("#nota-sim").textContent = NOTA_SIM[simActual];
    pintarDetalle();
  }

  function pintarDetalle() {
    const det = $("#detalle");
    if (!det) return;
    const d = dato(simActual, teclaActual);
    const otros = Object.keys(MAPA).filter((s) => s !== simActual).map((s) => {
      const o = dato(s, teclaActual);
      return "<div><b>" + esc(NOMBRE_SIM[s]) + "</b><span>" + esc(o.tipo === "nada" ? "sin uso" : o.c + ": " + o.t) + "</span></div>";
    }).join("");
    det.innerHTML =
      '<div class="grande"><span class="c9-k">' + esc(teclaActual) + "</span><div><b>" + esc(d.c) + "</b>" +
      '<div class="tipo" style="color:' + COLOR_TIPO[d.tipo] + '">' + esc(NOMBRE_TIPO[d.tipo]) + "</div></div></div>" +
      "<p>" + esc(d.t) + "</p>" +
      (d.boton ? '<div class="boton-ventana">Botón en la ventana sin ESP32: «' + esc(d.boton) + "»</div>" : "") +
      '<div class="otros"><div style="color:var(--c9-suave)">La misma tecla en las otras simulaciones:</div>' + otros + "</div>";
  }

  function elegirTecla(k) {
    teclaActual = k;
    document.querySelectorAll("#teclado .c9-tecla").forEach((b) => {
      b.classList.toggle("activa", b.dataset.k === k);
      if (b.dataset.k === k) { b.classList.add("pulso"); setTimeout(() => b.classList.remove("pulso"), 120); }
    });
    pintarDetalle();
  }

  function elegirSim(sim) {
    simActual = sim;
    document.querySelectorAll("#pestanas button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.sim === sim)));
    pintarTeclado();
  }

  // Teclas del PC: solo con el teclado dibujado a la vista y sin estar escribiendo en una caja.
  document.addEventListener("keydown", (ev) => {
    const t = ev.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
    const cont = $("#teclado");
    if (!cont || cont.offsetParent === null) return;
    const k = ev.key.length === 1 ? ev.key.toUpperCase() : "";
    if (k && FILAS.flat().includes(k)) elegirTecla(k);
  });

  // ==========================================================================================
  // 3. Medios (imágenes y GIF por /repo/), preview y firmware.
  // ==========================================================================================
  function cargarMedios() {
    document.querySelectorAll("img[data-src]").forEach((img) => {
      img.loading = "lazy";
      img.src = repo(img.dataset.src);
      try { if (window.App && App.imagen) App.imagen(img); } catch (e) { /* sin ampliar: no es grave */ }
    });
  }

  // El preview se dibuja a 1240 px (su diseño de tres columnas) y se escala al ancho del recuadro.
  function cargarPreview() {
    const env = $("#env-preview");
    const marco = $("#marco-preview");
    if (!env || !marco) return;
    marco.src = repo("preview.html");
    const ajustar = () => {
      const w = env.clientWidth;
      if (!w) return;
      const s = w >= 640 ? Math.min(1, w / 1240) : 1;
      marco.style.width = (s < 1 ? 1240 : w) + "px";
      marco.style.height = (env.clientHeight / s) + "px";
      marco.style.transform = s < 1 ? "scale(" + s + ")" : "none";
    };
    ajustar();
    if (window.ResizeObserver) new ResizeObserver(ajustar).observe(env);
  }

  function abrir(rel) {
    if (window.App && App.abrir) { try { return App.abrir(rel); } catch (e) { /* plan B */ } }
    window.open(repo(rel), "_blank", "noopener");
  }

  async function cargarFirmware() {
    const pre = $("#codigo-firmware");
    try {
      const r = await fetch(repo("esp32_teclado.py"));
      pre.textContent = r.ok ? await r.text() : "No se pudo leer el archivo (está en la carpeta del tema 9 como esp32_teclado.py).";
    } catch (e) {
      pre.textContent = "No se pudo leer el archivo (está en la carpeta del tema 9 como esp32_teclado.py).";
    }
  }

  // ==========================================================================================
  // 4. Barra de estado: entorno, modelos y qué está en marcha.
  // ==========================================================================================
  function chip(id, texto, tipo, titulo) {
    const c = document.getElementById(id);
    if (!c) return;
    c.className = "c9-chip " + (tipo || "");
    c.querySelector("span").textContent = texto;
    if (titulo) c.title = titulo;
  }

  function pintarEntorno() {
    const e = (window.App && App.entorno) || {};
    const estado = e.estado || "";
    let txt, tipo, largo;
    if (estado === "listo") {
      txt = "Entorno listo"; tipo = "ok";
      largo = "El entorno de Python ya tiene PyBullet y pyserial: las simulaciones abren en segundos.";
    } else if (estado === "sin-python") {
      txt = "Falta Python"; tipo = "mal";
      largo = "No se encontró la versión de Python que pide la práctica (3.12 a 3.14). " + (e.detalle || "");
    } else if (estado === "roto") {
      txt = "Entorno dañado"; tipo = "mal";
      largo = "El entorno existe pero no funciona; al pulsar Iniciar se intenta reparar. " + (e.detalle || "");
    } else if (estado) {
      txt = "1ª vez: compila PyBullet (~10 min)"; tipo = "aviso";
      largo = "El primer Iniciar crea el entorno e instala PyBullet. Si no está en la caché de pip, se compila: unos 10 minutos con barra de progreso. Después abre en segundos.";
    } else {
      txt = "Entorno: sin lanzador"; tipo = "";
      largo = "Abre la app con ABRIR.bat para poder correr las simulaciones.";
    }
    chip("chip-entorno", txt, tipo, largo);
    const g = $("#estado-entorno");
    if (g) { g.className = "c9-estado-grande " + tipo; g.textContent = largo; }
  }

  async function existe(rel) {
    // GET con Range (el servidor del lanzador no acepta HEAD): basta el primer byte.
    try { const r = await fetch(repo(rel), { headers: { Range: "bytes=0-0" }, cache: "no-store" }); return r.ok; } catch (e) { return false; }
  }
  let modelosListos = null;
  async function revisarModelos() {
    const [b, a] = await Promise.all([
      existe("modelos/baxter_common/baxter_description/urdf/toms_baxter.urdf"),
      existe("modelos/atlas/atlas_v4_with_multisense.urdf"),
    ]);
    modelosListos = a && b;
    const falta = [!b && "Baxter", !a && "Atlas"].filter(Boolean).join(" y ");
    chip("chip-modelos", modelosListos ? "Modelos descargados" : "Modelos: faltan (37 MB)",
      modelosListos ? "ok" : "aviso",
      modelosListos ? "Las mallas de Baxter y Atlas ya están en modelos/." : "Faltan las mallas de " + falta + ": se bajan solas (37 MB) en 'Antes de probar' o al abrir Baxter/Atlas.");
    const g = $("#estado-modelos");
    if (g) {
      g.className = "c9-estado-grande " + (modelosListos ? "ok" : "aviso");
      g.textContent = modelosListos ? "Ya están descargados en modelos/: no hace falta hacer nada."
        : "Faltan las mallas de " + falta + ". Pulsa Iniciar abajo (o se bajan solas al abrir Baxter o Atlas).";
    }
    marcar("modelos", modelosListos);
  }

  const enMarcha = new Set();
  const NOMBRES_ACCION = {
    "modelos": "descarga de modelos", "drones-prueba": "prueba de drones", "drones-mision": "misión de drones",
    "drones": "drones a mano", "baxter": "Baxter", "baxter-prueba": "prueba de Baxter", "atlas": "Atlas", "atlas-prueba": "prueba de Atlas",
  };
  function pintarMarcha() {
    const n = enMarcha.size;
    chip("chip-marcha", n ? "En marcha: " + [...enMarcha].map((i) => NOMBRES_ACCION[i] || i).join(", ") : "Nada en marcha",
      n ? "corre" : "", "Programas corriendo desde esta app");
  }

  // Marca verde en el menú lateral cuando una prueba de esa sección terminó bien.
  const VISTA_DE = { "modelos": "modelos", "drones-prueba": "drones", "drones-mision": "drones", "drones": "drones",
    "baxter": "baxter", "baxter-prueba": "baxter", "atlas": "atlas", "atlas-prueba": "atlas" };
  function marcar(m, ok) {
    const el = document.querySelector('[data-marca="' + m + '"]');
    if (el) el.classList.toggle("ok", !!ok);
  }

  // ==========================================================================================
  // 5. Prueba visual de los drones: la ruta del líder dibujada con las líneas "RUTA t x y z".
  //    La prueba vuela en menos de un segundo de reloj (sin ventana PyBullet va más rápido que el
  //    tiempo real), así que la ruta se REPRODUCE a la velocidad real de la simulación: 1 s de
  //    simulación = 1 s en pantalla, para que se vea cómo despega, se inclina, se pasa y corrige.
  // ==========================================================================================
  const PUNTOS_DEF = { A: [0, 0.9, 1.2], B: [1.4, -0.6, 1.6], C: [-1.3, 0.4, 0.9] };
  const COLOR_PUNTO = { A: "#5b9bd5", B: "#e8963a", C: "#4caf7d" };
  const T_MISION = 1.0;   // la misión arranca 1 s después del despegue (paso 240 en drones_pybullet.py)
  const ruta = { puntos: { ...PUNTOS_DEF }, pts: [], llegadas: {}, ok: null, inclinacion: null, t0: 0, anim: 0 };
  const sx = (x) => 200 + x * 100;   // 100 px por metro; X de −2 a 2 m
  const sy = (y) => 150 - y * 100;   // Y de −1,5 a 1,5 m (hacia arriba)
  const ax = (t) => 34 + t * 52;     // altura: 0 a ~7 s
  const ay = (z) => 62 - z * 28;     // 0 a 2 m

  function svgEl(tag, attrs, padre) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (padre) padre.appendChild(e);
    return e;
  }

  function dibujarFondoRuta() {
    const svg = $("#ruta-svg"), alto = $("#ruta-alto");
    if (!svg || !alto) return;
    svg.innerHTML = ""; alto.innerHTML = "";
    // cuadrícula de 50 cm
    for (let x = -2; x <= 2.001; x += 0.5) svgEl("line", { x1: sx(x), y1: 0, x2: sx(x), y2: 300, class: Math.abs(x) < 0.01 ? "eje" : "rejilla" }, svg);
    for (let y = -1.5; y <= 1.501; y += 0.5) svgEl("line", { x1: 0, y1: sy(y), x2: 400, y2: sy(y), class: Math.abs(y) < 0.01 ? "eje" : "rejilla" }, svg);
    svgEl("text", { x: 394, y: 146, class: "eje-txt", "text-anchor": "end" }, svg).textContent = "X";
    svgEl("text", { x: 205, y: 12, class: "eje-txt" }, svg).textContent = "Y";
    svgEl("text", { x: 6, y: 294, class: "eje-txt" }, svg).textContent = "cuadros de 50 cm";
    // origen (despegue)
    svgEl("rect", { x: sx(0) - 5, y: sy(0) - 5, width: 10, height: 10, class: "origen" }, svg);
    svgEl("text", { x: sx(0) + 8, y: sy(0) + 16, class: "eje-txt" }, svg).textContent = "despega";
    for (const [n, [x, y, z]] of Object.entries(ruta.puntos)) {
      svgEl("circle", { cx: sx(x), cy: sy(y), r: 12, fill: COLOR_PUNTO[n], "fill-opacity": 0.18, stroke: COLOR_PUNTO[n], "stroke-width": 1.5, id: "punto-" + n }, svg);
      svgEl("text", { x: sx(x), y: sy(y) + 5, "text-anchor": "middle", class: "punto-letra", fill: COLOR_PUNTO[n] }, svg).textContent = n;
      svgEl("text", { x: sx(x), y: sy(y) + 27, "text-anchor": "middle", class: "eje-txt" }, svg).textContent = "z " + coma(z) + " m";
    }
    svgEl("polyline", { id: "ruta-linea", class: "ruta-linea", points: "" }, svg);
    svgEl("circle", { id: "ruta-dron", r: 5, cx: -20, cy: -20, class: "ruta-dron" }, svg);
    // altura en el tiempo
    for (const z of [0, 1, 2]) {
      svgEl("line", { x1: 34, y1: ay(z), x2: 396, y2: ay(z), class: z ? "rejilla" : "eje" }, alto);
      svgEl("text", { x: 4, y: ay(z) + 4, class: "eje-txt" }, alto).textContent = z + " m";
    }
    svgEl("line", { x1: ax(T_MISION), y1: 4, x2: ax(T_MISION), y2: 62, class: "marca-mision" }, alto);
    svgEl("text", { x: ax(T_MISION) + 3, y: 11, class: "eje-txt" }, alto).textContent = "empieza la misión";
    svgEl("polyline", { id: "alto-linea", class: "ruta-linea", points: "" }, alto);
  }

  function reiniciarRuta() {
    cancelAnimationFrame(ruta.anim);
    Object.assign(ruta, { puntos: { ...PUNTOS_DEF }, pts: [], llegadas: {}, ok: null, inclinacion: null, t0: 0, anim: 0 });
    dibujarFondoRuta();
    document.querySelectorAll("#ruta-drones > div").forEach((d) => {
      d.classList.remove("llego", "falla");
      d.querySelector("span").textContent = d.dataset.p === "OK" ? "corriendo…" : "esperando";
      if (d.dataset.p === "OK") d.querySelector("b").textContent = "Resultado";
    });
    $("#ruta-estado").textContent = "volando…";
  }

  function lineaDrones(linea) {
    if (typeof linea !== "string") return;
    let m;
    if ((m = linea.match(/^PUNTO ([ABC]) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)/))) {
      ruta.puntos[m[1]] = [+m[2], +m[3], +m[4]];
      if (m[1] === "C") dibujarFondoRuta();
    } else if ((m = linea.match(/^RUTA (-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)/))) {
      if (!ruta.pts.length) { ruta.t0 = performance.now(); animarRuta(); }
      ruta.pts.push([+m[1], +m[2], +m[3], +m[4]]);
    } else if ((m = linea.match(/Llego a ([ABC]) a los ([\d.]+) s/))) {
      ruta.llegadas[m[1]] = +m[2];
    } else if ((m = linea.match(/inclinacion_max_grados['"]?\s*:\s*([\d.]+)/))) {
      ruta.inclinacion = +m[1];
    } else if (/PRUEBA (OK|FALLIDA)/.test(linea)) {
      ruta.ok = /PRUEBA OK/.test(linea);
      if (!ruta.pts.length) pintarResultadoRuta();   // salida vieja sin RUTA: igual se muestra el resultado
    }
  }

  function animarRuta() {
    const paso = () => {
      const tReloj = (performance.now() - ruta.t0) / 1000;
      const visibles = ruta.pts.filter((p) => p[0] <= tReloj);
      $("#ruta-linea").setAttribute("points", visibles.map((p) => sx(p[1]) + "," + sy(p[2])).join(" "));
      $("#alto-linea").setAttribute("points", visibles.map((p) => ax(p[0]) + "," + ay(p[3])).join(" "));
      const u = visibles[visibles.length - 1];
      if (u) { const d = $("#ruta-dron"); d.setAttribute("cx", sx(u[1])); d.setAttribute("cy", sy(u[2])); }
      for (const [n, t] of Object.entries(ruta.llegadas)) {
        const caja = document.querySelector('#ruta-drones [data-p="' + n + '"]');
        if (caja && !caja.classList.contains("llego") && tReloj >= T_MISION + t) {
          caja.classList.add("llego");
          caja.querySelector("span").textContent = "llegó a los " + coma(t) + " s";
          const c = $("#punto-" + n); if (c) c.setAttribute("fill-opacity", 0.55);
        }
      }
      if (u) $("#ruta-estado").textContent = "t = " + coma(u[0]) + " s · z = " + coma(u[3], 2) + " m";
      const ultimo = ruta.pts[ruta.pts.length - 1];
      if (ruta.ok !== null && ultimo && tReloj > ultimo[0] + 0.2) { pintarResultadoRuta(); return; }
      ruta.anim = requestAnimationFrame(paso);
    };
    ruta.anim = requestAnimationFrame(paso);
  }

  function pintarResultadoRuta() {
    const c = document.querySelector('#ruta-drones [data-p="OK"]');
    c.classList.toggle("llego", ruta.ok === true);
    c.classList.toggle("falla", ruta.ok === false);
    c.querySelector("b").textContent = ruta.ok ? "PRUEBA OK" : "FALLÓ";
    c.querySelector("span").textContent = ruta.inclinacion != null ? "inclinación máx. " + coma(ruta.inclinacion) + "°" : "";
    for (const [n, t] of Object.entries(ruta.llegadas)) {
      const caja = document.querySelector('#ruta-drones [data-p="' + n + '"]');
      caja.classList.add("llego"); caja.querySelector("span").textContent = "llegó a los " + coma(t) + " s";
    }
    $("#ruta-estado").textContent = ruta.ok ? "misión completa: A → B → C" : "no completó la misión: mira lo que dice el programa";
  }

  // ==========================================================================================
  // 6. Prueba de Baxter: tablero "medido contra el límite" con las líneas OK / FALLA.
  // ==========================================================================================
  const BAXTER_TOTAL = 18;   // comprobaciones que imprime probar_baxter.py (6 IK + 6 demo + 1 choques + 5 serial)
  const bax = { n: 0, mal: 0, seccion: null };
  function reiniciarBaxter() {
    Object.assign(bax, { n: 0, mal: 0, seccion: null });
    $("#baxter-tablero").innerHTML = "";
    $("#baxter-barra").style.width = "0%";
    $("#baxter-cuenta").textContent = "cargando Baxter…";
  }
  function lineaBaxter(linea) {
    if (typeof linea !== "string") return;
    const tab = $("#baxter-tablero");
    let m;
    if ((m = linea.match(/^(\d)\) (.*)$/))) {
      bax.seccion = document.createElement("div");
      bax.seccion.className = "c9-tab-sec";
      bax.seccion.innerHTML = "<h4>" + esc(m[1] + ") " + m[2]) + "</h4>";
      tab.appendChild(bax.seccion);
    } else if ((m = linea.match(/^\s+(OK|FALLA)\s+(.*)$/))) {
      if (!bax.seccion) { bax.seccion = document.createElement("div"); bax.seccion.className = "c9-tab-sec"; tab.appendChild(bax.seccion); }
      const ok = m[1] === "OK";
      bax.n += 1; bax.mal += ok ? 0 : 1;
      const fila = document.createElement("div");
      fila.className = "c9-tab-fila " + (ok ? "ok" : "mal");
      let barra = "";
      // "error 0.12 cm (< 2 cm)", "cubo a 0.19 cm del destino (< 3 cm)", "subio 19.0 cm (> 5 cm)":
      // lo medido es el ultimo numero en cm antes del parentesis con el limite.
      const lim = m[2].match(/([\d.]+) cm[^()]*\(([<>]) ([\d.]+) cm\)/);
      if (lim) {
        const v = +lim[1], l = +lim[3];
        const pct = Math.min(100, (v / Math.max(v, l)) * 100);
        barra = '<span class="c9-mini"><i style="width:' + pct.toFixed(1) + '%"></i><em style="left:' + (lim[2] === "<" ? 100 : (l / Math.max(v, l)) * 100).toFixed(1) + '%"></em></span>' +
          '<span class="c9-mini-txt">' + coma(v, 2) + " de " + (lim[2] === "<" ? "máx. " : "mín. ") + coma(l, 0) + " cm</span>";
      }
      fila.innerHTML = '<span class="c9-tab-ok">' + (ok ? "✓" : "✗") + "</span><span class=\"c9-tab-txt\">" + esc(m[2].replace(/\s*\([<>] [\d.]+ cm\)/, "")) + "</span>" + barra;
      bax.seccion.appendChild(fila);
      $("#baxter-barra").style.width = Math.min(100, (bax.n / BAXTER_TOTAL) * 100) + "%";
      $("#baxter-cuenta").textContent = bax.n + " de " + BAXTER_TOTAL + " comprobaciones" + (bax.mal ? " · " + bax.mal + " fallaron" : "");
    } else if (/Todas las pruebas pasaron/.test(linea)) {
      $("#baxter-barra").style.width = "100%";
      $("#baxter-cuenta").textContent = "Todas las pruebas pasaron (" + bax.n + " de " + BAXTER_TOTAL + ")";
    }
  }

  // ==========================================================================================
  // 7. Prueba de estrés de Atlas: gráfica de barras con y sin asistente.
  //    Antes de correrla se ve lo que medimos (tabla del README); al correrla se borra y cada
  //    barra aparece cuando probar_atlas.py imprime su línea.
  // ==========================================================================================
  const ATLAS_PRUEBAS = [
    { clave: "De pie quieto", nombre: "De pie quieto", dura: 20 },
    { clave: "Caminar adelante", nombre: "Caminar adelante (8)", dura: 15 },
    { clave: "Arrancar/frenar", nombre: "Arrancar y frenar ×5", dura: 20 },
    { clave: "Girar a la izquierda", nombre: "Girar a la izquierda (4)", dura: 8 },
    { clave: "Caminar atras", nombre: "Caminar atrás (2)", dura: 8 },
    { clave: "Poses seguidas", nombre: "Poses C, D, #, 5", dura: 16 },
  ];
  const ATLAS_TOTAL = 16;   // 6 + 6 pruebas, 3 intentos de levantarlo y la prueba de flanco
  // Lo medido antes (tabla "Lo que medimos" del README del punto c).
  const ATLAS_ANTES = {
    con: [[20, ""], [15, "avanzó 188 cm"], [20, "avanzó 129 cm"], [8, "giró 151°"], [8, "retrocedió 94 cm"], [16, "todas bien"]],
    sin: [[20, ""], [15, "al borde: a veces se cae a los 5,4 s"], [9.8, "se cae"], [2.5, "se cae"], [2.4, "se cae"], [16, "todas bien"]],
  };
  const atl = { modo: null, n: 0, valores: { con: [], sin: [] }, previo: true, extra: "" };

  function pintarGraficaAtlas() {
    const g = $("#atlas-grafica");
    if (!g) return;
    g.classList.toggle("previo", atl.previo);
    g.innerHTML = ATLAS_PRUEBAS.map((p, i) => {
      const fila = (modo) => {
        const v = atl.valores[modo][i];
        if (!v) return '<div class="c9-g-barra ' + modo + ' vacia"><span class="c9-g-pista"></span><span class="c9-g-val">…</span></div>';
        const [s, txt] = v;
        const lleno = s >= p.dura - 0.05;
        return '<div class="c9-g-barra ' + modo + (lleno ? "" : " cae") + '"><span class="c9-g-pista"><i style="width:' +
          (Math.min(1, s / p.dura) * 100).toFixed(1) + '%"></i></span><span class="c9-g-val">' +
          (lleno ? (txt ? "✓ " + esc(txt) : "de pie los " + coma(p.dura, 0) + " s") : "cae a " + coma(s) + " s" + (txt ? " · " + esc(txt) : "")) + "</span></div>";
      };
      return '<div class="c9-g-fila"><div class="c9-g-nombre">' + esc(p.nombre) + "<small>" + p.dura + " s</small></div>" +
        '<div class="c9-g-barras">' + fila("con") + fila("sin") + "</div></div>";
    }).join("") + (atl.extra ? '<div class="c9-g-extra">' + esc(atl.extra) + "</div>" : "");
  }

  function reiniciarAtlas() {
    Object.assign(atl, { modo: null, n: 0, valores: { con: [], sin: [] }, previo: false, extra: "" });
    $("#atlas-barra").style.width = "0%";
    $("#atlas-cuenta").textContent = "cargando Atlas…";
    pintarGraficaAtlas();
  }

  function avanceAtlas() {
    $("#atlas-barra").style.width = Math.min(100, (atl.n / ATLAS_TOTAL) * 100) + "%";
    $("#atlas-cuenta").textContent = atl.n + " de " + ATLAS_TOTAL + " pruebas" + (atl.n >= ATLAS_TOTAL ? " · terminó" : "");
  }

  function lineaAtlas(linea) {
    if (typeof linea !== "string") return;
    let m;
    if (/^Atlas cargado/.test(linea)) { $("#atlas-cuenta").textContent = "0 de " + ATLAS_TOTAL + " pruebas · " + linea.replace("Atlas cargado: ", ""); return; }
    if ((m = linea.match(/=== (CON|SIN) asistente ===/))) { atl.modo = m[1] === "CON" ? "con" : "sin"; return; }
    if (/intento \d+:/.test(linea) || /conmutaciones=/.test(linea)) { atl.n += 1; avanceAtlas(); }
    if ((m = linea.match(/-> (\d)\/3 quedaron de pie/))) {
      atl.extra = "Tirarlo con un empujón y levantarlo con B: " + m[1] + " de 3 veces quedó de pie 5 s sin asistente.";
      pintarGraficaAtlas();
    }
    if ((m = linea.match(/conmutaciones=(\d+)/))) {
      atl.extra += (atl.extra ? " " : "") + "Tecla A sostenida (10 líneas): el asistente cambió " + m[1] + (m[1] === "1" ? " vez (flanco correcto)." : " veces.");
      pintarGraficaAtlas();
    }
    if (!atl.modo) return;
    const i = ATLAS_PRUEBAS.findIndex((p) => linea.trim().startsWith(p.clave));
    if (i < 0) return;
    const p = ATLAS_PRUEBAS[i];
    const resto = linea.trim().slice(linea.trim().search(/\s{2,}/)).trim();
    let s = p.dura, txt = "";
    if (i === 5) {   // poses: "saludar: ok; agacharse: cae a los 2.1 s"
      const partes = resto.split(";").map((x) => x.trim());
      const k = partes.findIndex((x) => /cae a los/.test(x));
      if (k >= 0) { s = 4 * k + parseFloat(partes[k].match(/cae a los ([\d.]+)/)[1]); txt = partes[k].split(":")[0]; }
      else txt = "todas bien";
    } else {
      const cae = resto.match(/se cae a los ([\d.]+) s/);
      if (cae) s = parseFloat(cae[1]);
      const e = resto.match(/(avanzo|giro|retrocedio) (-?\d+) (cm|grados)/);
      if (e) txt = { avanzo: "avanzó ", giro: "giró ", retrocedio: "retrocedió " }[e[1]] + e[2] + (e[3] === "grados" ? "°" : " cm");
    }
    atl.valores[atl.modo][i] = [s, txt];
    atl.n += 1;
    avanceAtlas();
    pintarGraficaAtlas();
  }

  // ==========================================================================================
  // 8. Descarga de modelos: barra con los MB reales ("bajando 12.34/36.70 MB").
  // ==========================================================================================
  function lineaModelos(linea) {
    if (typeof linea !== "string") return;
    const caja = $("#descarga"), barra = $("#descarga-barra"), txt = $("#descarga-txt");
    let m;
    if ((m = linea.match(/Hay que bajar ([\d.]+) MB/))) { caja.hidden = false; barra.style.width = "0%"; txt.textContent = "0 de " + coma(+m[1]) + " MB"; }
    else if ((m = linea.match(/bajando ([\d.]+)\/([\d.]+) MB\s+(.*)/))) {
      caja.hidden = false;
      const total = +m[2] || 1;
      barra.style.width = Math.min(100, (+m[1] / total) * 100) + "%";
      txt.textContent = coma(+m[1]) + " de " + coma(total) + " MB · " + m[3];
    } else if (/ya estaban completos/.test(linea)) { caja.hidden = false; barra.style.width = "100%"; txt.textContent = "Ya estaban: no se bajó nada."; }
    else if ((m = linea.match(/^Listo: ([\d.]+) MB/))) { caja.hidden = false; barra.style.width = "100%"; txt.textContent = "Listo: " + coma(+m[1]) + " MB en modelos/"; }
  }

  // ==========================================================================================
  // 9. Paneles de ejecución (componente común) con los textos de cada bloque.
  // ==========================================================================================
  // Los textos "Qué va a pasar / Qué hacer / Qué deberías ver" están en el HTML (se leen aunque la
  // página se abra sin el lanzador); con el lanzador se le pasan al panel común y se quita la copia.
  function textosDelBloque(el) {
    const bloque = el.closest(".c9-prueba");
    const que = bloque && bloque.querySelector(".c9-que");
    if (!que) return {};
    const partes = [...que.children].map((d) => {
      const c = d.cloneNode(true);
      const b = c.querySelector(":scope > b"); if (b) b.remove();
      const div = document.createElement("div");
      div.className = "c9-texto-panel";
      div.innerHTML = c.innerHTML;
      return div;
    });
    que.remove();
    return { queVaAPasar: partes[0], queHacer: partes[1], queDeberiasVer: partes[2] };
  }

  // Qué hace cada acción con su salida y al empezar (para las pruebas visuales).
  const VISUAL = {
    "drones-prueba": { linea: lineaDrones, reiniciar: reiniciarRuta },
    "baxter-prueba": { linea: lineaBaxter, reiniciar: reiniciarBaxter },
    "atlas-prueba": { linea: lineaAtlas, reiniciar: reiniciarAtlas },
    "modelos": { linea: lineaModelos, reiniciar: () => { $("#descarga").hidden = false; $("#descarga-barra").style.width = "0%"; $("#descarga-txt").textContent = "leyendo la lista de archivos de GitHub…"; } },
  };
  const ACTIVOS = ["preparando", "instalando", "lanzada"];

  const paneles = {};
  function montarPaneles() {
    document.querySelectorAll("[data-panel]").forEach((el) => {
      const id = el.dataset.panel;
      const op = textosDelBloque(el);
      const v = VISUAL[id];
      let activo = false;
      if (v) op.alLinea = (texto) => v.linea(texto);
      op.alEstado = (t) => {
        const e = (t && t.estado) || "";
        const ahora = ACTIVOS.includes(e);
        if (ahora && !activo && v) v.reiniciar();
        activo = ahora;
        if (ahora) enMarcha.add(id); else enMarcha.delete(id);
        pintarMarcha();
      };
      op.alTerminar = (t) => {
        enMarcha.delete(id); pintarMarcha();
        if (id === "modelos" || id === "baxter" || id === "atlas" || id === "baxter-prueba" || id === "atlas-prueba") revisarModelos();
        if (t && t.estado === "terminada" && VISTA_DE[id]) marcar(VISTA_DE[id], true);
      };
      try {
        paneles[id] = App.panelEjecucion(el, id, op);
      } catch (e) {
        el.innerHTML = '<p class="c9-nota">No se pudo armar este botón: ' + esc(e && e.message ? e.message : e) + "</p>";
      }
    });
  }

  // ==========================================================================================
  // 10. Arranque
  // ==========================================================================================
  async function iniciar() {
    // navegación
    document.querySelectorAll("#lateral [data-vista]").forEach((b) => b.addEventListener("click", () => mostrarVista(b.dataset.vista)));
    document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => mostrarVista(b.dataset.ir)));
    document.querySelectorAll("[data-readme]").forEach((b) => b.addEventListener("click", () => abrir(b.dataset.readme)));
    $("#btn-menu").addEventListener("click", () => document.body.classList.toggle("menu-abierto"));
    $("#btn-readme").addEventListener("click", () => abrir("README.md"));
    $("#btn-completa").addEventListener("click", () => {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => {});
    });
    document.addEventListener("fullscreenchange", () => {
      $("#btn-completa").textContent = document.fullscreenElement ? "⛶ Salir de pantalla completa" : "⛶ Pantalla completa";
    });
    $("#abrir-preview").addEventListener("click", () => abrir("preview.html"));
    document.querySelectorAll("#pestanas button").forEach((b) => b.addEventListener("click", () => elegirSim(b.dataset.sim)));
    pintarTeclado();
    dibujarFondoRuta();
    ATLAS_PRUEBAS.forEach((_, i) => { atl.valores.con[i] = ATLAS_ANTES.con[i]; atl.valores.sin[i] = ATLAS_ANTES.sin[i]; });
    pintarGraficaAtlas();
    alMostrar.preview = cargarPreview;
    alMostrar.esp32 = cargarFirmware;
    mostrarVista(vistaInicial(), false);

    if (!window.App) {
      $("#sinapp").style.display = "block";
      cargarMedios(); pintarEntorno();
      $("#checklist").innerHTML = '<p class="c9-intro">Ábrela desde ABRIR.bat para ver y marcar la lista.</p>';
      return;
    }
    try { await App.iniciar(); } catch (e) { $("#sinapp").style.display = "block"; }
    cargarMedios();
    pintarEntorno();
    revisarModelos();
    // La misma lista sale en el resumen y en el checklist: si se marca a mano en una, se redibuja la otra.
    const listas = ["checklist", "checklist-final"];
    listas.forEach((id, i) => {
      const el = document.getElementById(id);
      if (!el) return;
      try { App.checklist(el); } catch (e) { /* la lista es opcional */ }
      el.addEventListener("change", () => {
        const otra = document.getElementById(listas[1 - i]);
        if (otra) setTimeout(() => { try { App.checklist(otra); } catch (e) { /* nada */ } }, 50);
      });
    });
    montarPaneles();
    try {
      App.markdown($("#md-protocolo"), "README.md", { desde: "## El protocolo `TECLA:x` y cómo lo lee el PC", hasta: "## Conexiones" });
    } catch (e) { /* solo es un extra plegado */ }
    // Para las pruebas automáticas (captura con Chrome): paneles e ir a una sección.
    window.Consola9 = { paneles, mostrarVista, lineaDrones, lineaAtlas, lineaBaxter, reiniciarRuta, reiniciarAtlas, reiniciarBaxter };
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
