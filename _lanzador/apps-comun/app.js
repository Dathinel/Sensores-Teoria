/* =====================================================================================
 * _lanzador/apps-comun/app.js — API común de las apps por práctica (window.App), versión 2.
 *
 * Cada práctica tiene su app en <carpeta>/app/index.html (o la ruta del campo "app" de su
 * probar.json). El lanzador _lanzador/lanzador.py la sirve en http://127.0.0.1:<puerto>/app/<carpeta>/
 * y le inyecta dos <meta> (el token y la carpeta). Esta biblioteca habla con el lanzador
 * por esa API; la app nunca ve rutas ni comandos: solo pulsa botones.
 *
 * Uso mínimo (ver _lanzador/LEEME.md):
 *   <link rel="stylesheet" href="/comun/app.css">
 *   <script src="/comun/app.js"></script>
 *   <script>
 *     (async () => {
 *       const practica = await App.iniciar();
 *       App.panelEjecucion("#simulacion", "sim");
 *     })();
 *   </script>
 *
 * Sin dependencias. marked (markdown) y mermaid (diagramas) se cargan de un CDN solo si se
 * usa App.markdown; sin internet se muestra el texto tal cual.
 * ===================================================================================== */
(function () {
  "use strict";

  const VERSION = "2.0";
  const MARKED = "https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js";
  const MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js";

  const meta = (n) => (document.querySelector(`meta[name="${n}"]`) || {}).content || "";
  const TOKEN = meta("probar-token");
  const CARPETA = meta("probar-carpeta")
    || decodeURIComponent((location.pathname.match(/^\/app\/([^/]+)/) || [])[1] || "");

  const S = { practica: null, datos: null, promesa: null, oyentes: {}, caido: false, trabajos: {} };

  // ------------------------------------------------------------------ utilidades
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
  const $ = (x) => (typeof x === "string" ? document.querySelector(x) : x);
  const ACTIVOS = ["preparando", "instalando", "lanzada"];
  const activo = (estado) => ACTIVOS.includes(estado);
  const norm = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim();
  const mmss = (seg) => { seg = Math.max(0, Math.round(seg)); return `${Math.floor(seg / 60)}:${String(seg % 60).padStart(2, "0")}`; };
  const rutaRepo = (ruta) => "/repo/" + [CARPETA, ...String(ruta).replace(/\\/g, "/").split("/")].filter(Boolean).map(encodeURIComponent).join("/");

  function crear(tag, clase, html) {
    const e = document.createElement(tag);
    if (clase) e.className = clase;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  // Un texto de opciones puede ser: texto (se escapa), lista de textos (viñetas) o un nodo DOM.
  function contenido(valor) {
    if (valor == null || valor === "") return null;
    if (valor instanceof Node) return valor;
    if (Array.isArray(valor)) {
      const ul = crear("ul");
      for (const v of valor) { const li = crear("li"); li.textContent = v; ul.appendChild(li); }
      return ul;
    }
    const p = crear("p"); p.textContent = String(valor); return p;
  }

  function emitir(evento, dato) { for (const f of S.oyentes[evento] || []) { try { f(dato); } catch (e) { console.error(e); } } }

  async function api(ruta, cuerpo) {
    const opciones = cuerpo === undefined ? {} : {
      method: "POST", headers: { "Content-Type": "application/json", "X-Token": TOKEN }, body: JSON.stringify(cuerpo) };
    let r;
    try { r = await fetch(ruta, opciones); }
    catch (e) { throw new Error("No hay conexión con el lanzador: ¿se cerró? Vuelve a abrir la práctica con doble clic en su ABRIR.bat."); }
    let d = null;
    try { d = await r.json(); } catch (e) { /* no JSON */ }
    if (!r.ok) throw new Error((d && d.error) || `El lanzador respondió ${r.status}`);
    return d;
  }

  function cargarScript(src) {
    if (cargarScript.c[src]) return cargarScript.c[src];
    cargarScript.c[src] = new Promise((ok, mal) => {
      const s = document.createElement("script");
      s.src = src; s.async = true; s.onload = ok; s.onerror = () => { delete cargarScript.c[src]; mal(new Error("sin internet")); };
      document.head.appendChild(s);
    });
    return cargarScript.c[src];
  }
  cargarScript.c = {};

  function buscarAccion(id) {
    const a = S.practica && S.practica.acciones.find((x) => x.id === id);
    if (!a) throw new Error(`Esta práctica no declara la acción "${id}" en su probar.json.`);
    return a;
  }

  // ------------------------------------------------------------------ iniciar / latido
  async function iniciar() {
    if (S.promesa) return S.promesa;
    S.promesa = (async () => {
      if (!CARPETA) throw new Error("No sé de qué práctica es esta página (ábrela con su ABRIR.bat).");
      carga("Leyendo la práctica y revisando su entorno de Python…", 0.55);
      const d = await api("/api/practica/" + encodeURIComponent(CARPETA));
      S.datos = d; S.practica = d.practica;
      App.carpeta = CARPETA; App.practica = d.practica; App.entorno = d.entorno;
      if (!document.title) document.title = d.practica.titulo;
      for (const t of d.trabajos || []) if (activo(t.estado)) S.trabajos[t.tid] = { accion: t.accion, estado: t.estado };
      carga(textoEntornoCorto(d) || "Práctica lista.", 0.85);
      latido();
      estadoGlobal();
      return Object.assign({}, d.practica, {
        entorno: d.entorno, sistema: d.sistema, build_tools: d.build_tools, pythons: d.pythons, trabajos: d.trabajos });
    })();
    S.promesa.catch((e) => { S.promesa = null; cargaLista(); aviso(e.message, "error", 0); });
    return S.promesa;
  }

  // ------------------------------------------------------------------ pantalla de carga
  // El lanzador pone en la página principal de la app un <div id="app-carga"> ("Abriendo la
  // práctica…") que se ve desde el primer instante. Aquí se avanza su barra y se quita cuando
  // la página terminó de cargar Y la app ya leyó su práctica (o a los 12 s, pase lo que pase).
  const CARGA = { frac: 0.1, cargada: document.readyState === "complete", quitada: false };
  function carga(paso, frac) {
    const c = document.getElementById("app-carga");
    if (!c || CARGA.quitada) return;
    if (typeof frac === "number") CARGA.frac = Math.max(CARGA.frac, Math.min(1, frac));
    const b = document.getElementById("app-carga-barra"); if (b) b.style.width = Math.round(CARGA.frac * 100) + "%";
    const p = document.getElementById("app-carga-paso"); if (p && paso) p.textContent = paso;
  }
  function cargaLista() {
    if (CARGA.quitada) return;
    CARGA.quitada = true;
    const c = document.getElementById("app-carga");
    if (!c) return;
    carga("Listo.", 1);
    setTimeout(() => { c.classList.add("fuera"); setTimeout(() => c.remove(), 400); }, 150);
  }
  function intentarQuitarCarga() {
    if (!CARGA.cargada) return;
    // Si la app usa App.iniciar (casi todas), se espera a que lea su práctica; si en 1,5 s
    // tras cargar la página no lo llamó, se quita igual.
    if (S.promesa) S.promesa.then(() => setTimeout(cargaLista, 120), cargaLista);
    else setTimeout(() => { if (S.promesa) intentarQuitarCarga(); else cargaLista(); }, 1500);
  }
  carga("Cargando la página…", 0.3);
  document.addEventListener("DOMContentLoaded", () => carga("Cargando estilos, imágenes y fuentes…", 0.45));
  if (CARGA.cargada) intentarQuitarCarga();
  else addEventListener("load", () => { CARGA.cargada = true; carga(null, 0.7); intentarQuitarCarga(); });
  setTimeout(cargaLista, 12000);

  function textoEntornoCorto(d) {
    const p = d.practica || {}, e = d.entorno || {};
    if (!p.python || !(p.python.paquetes || []).length) return "No necesita instalar nada.";
    if (e.estado === "listo") return `Entorno de Python listo (${e.detalle}).`;
    if (e.estado === "subcarpetas") return "Entornos de Python listos.";
    if (e.estado === "nuevo") return "El entorno de Python se prepara la primera vez que pulses Iniciar.";
    if (e.estado === "faltan") return "Al entorno le faltan librerías: se instalan al pulsar Iniciar.";
    if (e.estado === "sin-python") return `Falta Python ${e.detalle} en este PC (la app explica cómo instalarlo).`;
    return "";
  }

  // ------------------------------------------------------------------ barra de herramientas
  // Botón "Pantalla completa" y estado (entorno / programas en marcha) en TODAS las apps: dentro
  // del [data-app-herramientas] si la app reservó un sitio (lo recomendado: en su cabecera), o de
  // .app-marco-cab / .app-encabezado si los tiene; si no, en una franja fina arriba de la página
  // (en el flujo, no flotante: así nunca tapa contenido). Si la app ya trae su propio botón
  // "Pantalla completa", no se repite. Una app puede quitarla con <body data-app-sin-herramientas>.
  const HERR = { el: null, chip: null, bFs: null };
  function pantallaCompleta() {
    const d = document;
    if (d.fullscreenElement) return d.exitFullscreen && d.exitFullscreen();
    const r = d.documentElement.requestFullscreen && d.documentElement.requestFullscreen();
    if (r && r.catch) r.catch(() => aviso("El navegador no dejó pasar a pantalla completa: prueba con F11.", "aviso"));
  }
  function herramientas() {
    if (HERR.el || document.body.hasAttribute("data-app-sin-herramientas")) return;
    const sitio = document.querySelector("[data-app-herramientas]") || document.querySelector(".app-marco-cab, .app-encabezado");
    const el = crear("div", "app-herr" + (sitio ? "" : " franja"));
    const chip = crear("span", "app-chip app-herr-estado"); chip.hidden = true;
    const bFs = crear("button", "app-btn app-btn-mini app-herr-fs"); bFs.type = "button";
    bFs.title = "Pantalla completa (F11). Esc para salir.";
    bFs.onclick = pantallaCompleta;
    const propio = [...document.querySelectorAll("button, a")].some((b) => /pantalla completa/i.test(b.textContent || ""));
    el.append(chip); if (!propio) el.append(bFs);
    if (sitio) sitio.appendChild(el); else document.body.prepend(el);
    Object.assign(HERR, { el, chip, bFs });
    const pintarFs = () => { bFs.innerHTML = document.fullscreenElement ? "&#x2715; Salir de pantalla completa" : "&#x26F6; Pantalla completa"; };
    document.addEventListener("fullscreenchange", pintarFs); pintarFs();
    estadoGlobal();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", herramientas); else herramientas();

  // Estado de la práctica en la cabecera: "▶ N en marcha" o el estado del entorno.
  function estadoGlobal() {
    const n = Object.values(S.trabajos).filter((t) => activo(t.estado)).length;
    const textos = [];
    let cls = "";
    if (n) { textos.push(n === 1 ? "▶ 1 programa en marcha" : `▶ ${n} programas en marcha`); cls = "activo"; }
    else if (S.datos) {
      const e = S.datos.entorno || {}, p = S.practica;
      if (!p.python || !(p.python.paquetes || []).length) { textos.push("Listo: no instala nada"); cls = "ok"; }
      else if (e.estado === "listo" || e.estado === "subcarpetas") { textos.push("Entorno listo"); cls = "ok"; }
      else if (e.estado === "sin-python") { textos.push("Falta Python " + (e.detalle || "")); cls = "mal"; }
      else if (e.estado === "roto") { textos.push("Entorno dañado"); cls = "mal"; }
      else if (e.estado) textos.push("Entorno: se prepara al iniciar");
    }
    for (const el of document.querySelectorAll(".app-herr-estado, [data-app-estado]")) {
      el.hidden = !textos.length; el.textContent = textos.join(" · ");
      el.classList.remove("ok", "mal", "activo"); if (cls) el.classList.add(cls);
    }
    document.documentElement.dataset.appEnMarcha = String(n);
    emitir("estado", { enMarcha: n, entorno: S.datos && S.datos.entorno });
  }
  function anotarTrabajo(t) {
    if (!t || t.tid === undefined) return;
    const antes = S.trabajos[t.tid] && S.trabajos[t.tid].estado;
    S.trabajos[t.tid] = { accion: t.accion, estado: t.estado };
    // Una acción python que terminó bien deja el entorno listo: se refleja sin recargar.
    if (t.estado === "terminada" && S.datos && S.datos.entorno && S.datos.entorno.estado !== "listo" && t.fallo_en !== "preparar"
        && S.practica && S.practica.python) S.datos.entorno = { estado: "listo", detalle: (S.datos.entorno.detalle || "") };
    if (antes !== t.estado) estadoGlobal();
  }

  // Cada 20 s se pregunta al lanzador si sigue vivo (y así sabe que la app sigue abierta).
  function latido() {
    if (latido.on) return; latido.on = true;
    let fallos = 0, banda = null;
    const tic = async () => {
      try {
        const r = await fetch("/api/ping?app=" + encodeURIComponent(CARPETA), { cache: "no-store" });
        if (!r.ok) throw new Error();
        fallos = 0; S.caido = false;
        if (banda) { banda.remove(); banda = null; }
      } catch (e) {
        if (++fallos >= 2 && !banda) {
          S.caido = true;
          banda = crear("div", "app-caido", "<b>El lanzador se cerró.</b> Los botones no funcionarán hasta que vuelvas a abrir la práctica con doble clic en su <b>ABRIR.bat</b>.");
          document.body.prepend(banda);
        }
      }
      setTimeout(tic, fallos ? 5000 : 20000);
    };
    setTimeout(tic, 20000);
    // Al cerrar (o recargar) la página se avisa al lanzador: si no vuelve en 10 s, las acciones
    // con "vida": "app" se detienen solas. sendBeacon no admite cabeceras: el token va en el cuerpo.
    addEventListener("pagehide", () => {
      try {
        navigator.sendBeacon("/api/adios", new Blob([JSON.stringify({ token: TOKEN, carpeta: CARPETA })], { type: "text/plain" }));
      } catch (e) { /* nada */ }
    });
  }

  // ------------------------------------------------------------------ bajo nivel
  function navegable(a) { return a.tipo === "html" || a.tipo === "url" || (a.tipo === "info" && a.enlace); }

  // Sigue un trabajo leyendo su salida por partes (desde=N) hasta que termina.
  async function seguir(tid, op = {}) {
    let desde = 0, fallos = 0, firma = "";
    for (;;) {
      let r;
      try { r = await api(`/api/salida?tid=${encodeURIComponent(tid)}&desde=${desde}`); fallos = 0; }
      catch (e) {
        if (++fallos >= 6) {
          const t = { tid, estado: "error", fase: "", mensaje: "Se perdió la conexión con el lanzador (¿se cerró su ventana?).", lineas: [] };
          anotarTrabajo(t); op.alEstado && op.alEstado(t); return t;
        }
        await dormir(1500); continue;
      }
      anotarTrabajo(r);
      for (const l of r.lineas) op.alLinea && op.alLinea(l.x, l.t, l.n);
      desde = r.siguiente;
      const f = [r.estado, r.fase, r.mensaje, r.parcial, r.abrir].join("|");
      if (f !== firma) { firma = f; op.alEstado && op.alEstado(r); }
      if (!activo(r.estado)) return r;
      await dormir(r.estado === "lanzada" ? 350 : 700);
    }
  }

  function terminoBien(t) {
    if (t.estado === "terminada") return true;
    // Un programa con ventana que el usuario cerró con Detener tras verlo funcionar también cuenta.
    return t.estado === "detenida" && t.fallo_en !== "preparar" && t.lanzado && (t.fin - t.lanzado) > 3;
  }

  // App.accion: lanza la acción y devuelve una promesa con el trabajo final.
  function accion(id, op = {}) {
    // html / url se abren en el mismo clic (sin await antes): si no, el navegador bloquea la ventana.
    if (S.practica) {
      const a = buscarAccion(id);
      if (!a.error && navegable(a)) {
        window.open(a.tipo === "url" ? a.url : a.enlace, "_blank", "noopener");
        const t = { estado: "terminada", mensaje: "Abierto en una pestaña nueva.", accion: id };
        op.alEstado && op.alEstado(t); emitir("ok", id);
        return Promise.resolve(t);
      }
    }
    return (async () => {
      await iniciar();
      const a = buscarAccion(id);
      if (a.error) throw new Error(`La acción "${a.nombre}" tiene un error en probar.json: ${a.error}`);
      if (navegable(a)) return accion(id, op);
      if (a.tipo === "info") { const t = { estado: "terminada", mensaje: "" }; op.alEstado && op.alEstado(t); return t; }
      const t0 = await api("/api/accion", { carpeta: CARPETA, accion: id, modo: "app" });
      op.alEstado && op.alEstado(t0);
      const t = await seguir(t0.tid, op);
      if (terminoBien(t)) emitir("ok", id);
      emitir("fin", { accion: id, trabajo: t });
      return t;
    })();
  }

  async function detener(id) {
    await iniciar();
    return api("/api/detener", { carpeta: CARPETA, accion: id, modo: "app" });
  }

  async function entrada(id, texto) {
    await iniciar();
    return api("/api/entrada", { carpeta: CARPETA, accion: id, texto: String(texto) });
  }

  // ------------------------------------------------------------------ errores en lenguaje humano
  const WINGET = 'winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"';
  const PISTAS = [
    [/ModuleNotFoundError: No module named '([^']+)'/, (m) => `Al programa le falta la librería de Python "${m[1]}". Normalmente el lanzador la instala sola: vuelve a pulsar Iniciar; si se repite, borra la carpeta entorno de la práctica y pulsa otra vez.`],
    [/(SerialException|could not open port|COM\d+.*(denegado|denied))/i, (m, a) => "No se pudo abrir el puerto serie: el ESP32 no está conectado, o lo tiene abierto otro programa (Thonny, el Monitor Serie de Arduino)."
      + (a && a.si_falla ? "" : " Para probar sin hardware no hace falta: el programa debería seguir solo con los controles en pantalla.")],
    [/(can't open camera|cannot open camera|VideoCapture|camera index|no se pudo abrir la c[aá]mara)/i, () => "No se pudo abrir la cámara: revisa que esté conectada y que no la esté usando otra app (Teams, Zoom, el navegador)."],
    [/(WinError 10048|Address already in use|address is already in use)/i, () => "Un puerto de red que necesita el programa ya lo está usando otro programa (¿quedó abierta otra copia?). Ciérrala y vuelve a intentar."],
    [/(WinError 10061|ConnectionRefusedError|Connection refused)/i, () => "El programa intentó conectarse a algo que no está encendido (un servidor o laboratorio que hay que levantar antes)."],
    [/(getaddrinfo failed|Max retries exceeded|Temporary failure in name resolution|ConnectTimeout|No route to host)/i, () => "Problema de conexión a internet: el programa necesitaba descargar o consultar algo en línea."],
    [/(Cannot connect to the Docker daemon|error during connect|docker.*not running|pipe\/docker_engine)/i, () => "Docker Desktop no está abierto. Ábrelo, espera a que diga \"Engine running\" y vuelve a pulsar."],
    [/(FileNotFoundError|No such file or directory)[^\n]*?'([^']+)'/, (m) => `No se encontró el archivo "${m[2]}".`],
    [/MemoryError|out of memory/i, () => "El programa se quedó sin memoria. Cierra otras aplicaciones y vuelve a intentar."],
    [/(PermissionError|Acceso denegado|Access is denied)/i, () => "Windows no dejó acceder a un archivo o dispositivo (permiso denegado): puede estar abierto en otro programa."],
    [/Unable to find a compatible Visual Studio|Microsoft Visual C\+\+ 14.0 or greater is required/i, () => "Para compilar PyBullet faltan las Visual Studio Build Tools con C++. Instálalas una vez con: " + WINGET],
    [/No matching distribution found for ([^\s]+)/i, (m) => `pip no encontró "${m[1]}" para esta versión de Python (o no hay internet).`],
  ];

  function resumenError(t, lineas, a) {
    if (t.fallo_en === "preparar" || (!t.lanzado && t.mensaje)) return { titulo: "No se pudo preparar todo para arrancar", texto: t.mensaje };
    const todo = lineas.join("\n");
    for (const [re, f] of PISTAS) { const m = todo.match(re); if (m) return { titulo: "El programa se detuvo con un problema", texto: f(m, a) }; }
    const exc = [...lineas].reverse().find((l) => /^[A-Za-z_][\w.]*(Error|Exception)\b.*:/.test(l.trim()));
    if (exc) return { titulo: "El programa se detuvo con un error", texto: `Python dijo: ${exc.trim()}` };
    if (t.mensaje) return { titulo: "No funcionó", texto: t.mensaje };
    return { titulo: "No funcionó", texto: `El programa terminó con un código de error (${t.codigo}). Mira las últimas líneas de abajo.` };
  }

  // pip y el lanzador escriben en inglés: se traduce lo que está haciendo a una frase corta.
  function pasoPip(l) {
    let m;
    if ((m = l.match(/^Collecting ([^\s<>=!~;\[]+)/))) return `Buscando ${m[1]}…`;
    if ((m = l.match(/Downloading ([^\s]+)/))) return `Descargando ${m[1].split("/").pop().split("-")[0]}…`;
    if ((m = l.match(/Building wheel for ([^\s]+)/i))) return /pybullet/i.test(m[1]) ? "Compilando PyBullet (la primera vez tarda unos 10-15 minutos; no cierres nada)…" : `Compilando ${m[1]}…`;
    if (/Installing collected packages/.test(l)) return "Instalando los paquetes descargados…";
    if (/Successfully installed/.test(l)) return "Paquetes instalados.";
    if (/Requirement already satisfied/.test(l)) return "Revisando lo que ya está instalado…";
    if (/Using cached/.test(l)) return "Usando lo que ya estaba descargado…";
    return null;
  }

  // ------------------------------------------------------------------ panel de ejecución
  const ESTADOS = {
    listo: "Listo para iniciar", preparando: "Preparando…", instalando: "Preparando el entorno (solo la primera vez)…",
    lanzada: "En marcha", terminada: "Terminó bien", error: "No funcionó", detenida: "Detenido",
  };
  const BOTON = { python: "Iniciar", docker: "Levantar", html: "Abrir", url: "Abrir", archivo: "Abrir", info: "Ver" };

  function avisoEntorno(a) {
    const p = S.practica, d = S.datos || {};
    if (a.tipo !== "python" || !p.python || !(p.python.paquetes || []).length) return null;
    const e = d.entorno || {};
    const caja = crear("div", "app-panel-entorno");
    const n = p.python.paquetes.length;
    if (e.estado === "listo" || e.estado === "subcarpetas") { caja.classList.add("ok"); caja.textContent = "Todo instalado: arranca enseguida."; return caja; }
    if (e.estado === "sin-python") {
      caja.classList.add("mal");
      caja.innerHTML = `Esta práctica necesita <b>Python ${esc(e.detalle)}</b> y no está instalado en este PC. Descárgalo de
        <a href="https://www.python.org/downloads/" target="_blank" rel="noopener">python.org/downloads</a> (instalador de Windows de 64 bits,
        con el "py launcher" marcado) y vuelve a abrir esta app.`;
      return caja;
    }
    if (e.estado === "roto") { caja.classList.add("mal"); caja.textContent = `El entorno de Python de esta práctica está dañado (${e.detalle}). Bórralo: al pulsar Iniciar se crea solo de nuevo.`; return caja; }
    let txt = e.estado === "faltan"
      ? `Al pulsar Iniciar se instalan primero unas librerías que faltan (${e.detalle}).`
      : `La primera vez, al pulsar Iniciar, se prepara solo: crea un entorno de Python ${e.detalle ? "(" + e.detalle.replace("Python ", "") + ") " : ""}e instala ${n} librería${n > 1 ? "s" : ""}. Tarda unos minutos y verás el progreso aquí; las siguientes veces arranca enseguida.`;
    caja.textContent = txt;
    if (p.compila && e.estado !== "listo") {
      const b = crear("div", "app-panel-bt");
      if (d.build_tools === false) {
        b.classList.add("mal");
        b.innerHTML = `<b>Ojo:</b> usa PyBullet, que en Windows se compila, y faltan las <b>Visual Studio Build Tools</b> (C++). Instálalas una sola vez (2-3 GB) con este comando en una consola y luego pulsa Iniciar:`;
        const c = crear("div", "app-comando"); const code = crear("code"); code.textContent = WINGET;
        const cp = crear("button", "app-btn app-btn-mini", "Copiar");
        cp.onclick = () => { navigator.clipboard && navigator.clipboard.writeText(WINGET); aviso("Comando copiado.", "ok"); };
        c.append(code, cp); b.appendChild(c);
      } else {
        b.textContent = "Usa PyBullet, que en Windows se compila la primera vez (unos 10-15 minutos; las Build Tools ya están instaladas).";
      }
      caja.appendChild(b);
    }
    return caja;
  }

  function panelEjecucion(el, accionId, op = {}) {
    el = $(el);
    const ctl = { el, estado: "listo", iniciar: () => {}, detener: () => {}, enviar: () => {} };
    if (!el) { console.error("App.panelEjecucion: no existe el elemento", el); return ctl; }
    el.classList.add("app-panel");
    el.innerHTML = '<p class="app-tenue">Cargando…</p>';
    iniciar().then(() => construir(el, accionId, op, ctl)).catch((e) => { el.innerHTML = ""; el.appendChild(crear("div", "app-aviso error", esc(e.message))); });
    return ctl;
  }

  function construir(el, accionId, op, ctl) {
    let a;
    try { a = buscarAccion(accionId); }
    catch (e) { el.innerHTML = ""; el.appendChild(crear("div", "app-aviso error", esc(e.message))); return; }
    const consola = a.tipo === "python" && a.modo === "consola";
    el.innerHTML = "";
    el.dataset.estado = "listo";
    el.dataset.tipo = a.tipo;

    // Cabecera
    const cab = crear("div", "app-panel-cab");
    const h = crear("h3"); h.textContent = op.titulo || a.nombre; cab.appendChild(h);
    el.appendChild(cab);

    // Qué va a pasar / qué hacer / qué deberías ver
    const info = crear("div", "app-panel-info");
    const bloque = (titulo, valor, clase) => {
      const c = contenido(valor); if (!c) return;
      const d = crear("div", "app-panel-bloque " + (clase || ""));
      d.appendChild(crear("div", "app-etiqueta", esc(titulo))); d.appendChild(c); info.appendChild(d);
    };
    bloque("Qué va a pasar", op.queVaAPasar !== undefined ? op.queVaAPasar : a.descripcion);
    if (a.ventana || op.queHacer) {
      bloque(a.ventana ? "Se abrirá una ventana aparte: úsala así" : "Qué hacer", op.queHacer || "Usa la ventana que se abre; para terminar, ciérrala o pulsa Detener aquí.", "ventana");
    }
    bloque("Qué deberías ver", op.queDeberiasVer);
    if (consola) bloque("Ojo", "Este programa se abre en una ventana de consola (negra) aparte: lo que pide y lo que muestra está allí, no en esta página.");
    if (info.children.length) el.appendChild(info);

    const ent = avisoEntorno(a); if (ent) el.appendChild(ent);
    if (a.tipo === "docker") el.appendChild(crear("div", "app-panel-entorno", "Necesita <b>Docker Desktop</b> abierto (que diga \"Engine running\"). Si no lo está, al pulsar te lo dirá."));
    if (a.error) el.appendChild(crear("div", "app-aviso error", "No se puede iniciar: " + esc(a.error)));

    // Botones
    const bots = crear("div", "app-panel-botones");
    const bIni = crear("button", "app-btn app-btn-grande primario");
    bIni.textContent = op.botonTexto || `${BOTON[a.tipo] || "Iniciar"}: ${a.nombre}`;
    bIni.disabled = !!a.error || (a.tipo === "info" && !a.enlace);
    const bDet = crear("button", "app-btn peligro", a.tipo === "docker" ? "Detener el laboratorio" : "Detener");
    bDet.hidden = a.tipo !== "docker";
    const bAbrir = crear("button", "app-btn", "Abrir"); bAbrir.hidden = true;
    bots.append(bIni, bDet, bAbrir);
    if (a.tipo === "info" && !a.enlace) bIni.hidden = true;
    el.appendChild(bots);

    // Cuánto suele tardar (campo "duracion"/"duracion_s" de la acción, u opción duracion_s del panel)
    const durS = Number(op.duracion_s || a.duracion_s) || 0;
    if (durS && a.tipo !== "html" && a.tipo !== "url" && a.tipo !== "archivo" && a.tipo !== "info") {
      const d = a.duracion || ("~" + mmss(durS));
      const chip = crear("span", "app-chip app-duracion", esc(/^[~≈\d]/.test(d) ? "Tarda " + d : d));
      chip.title = "Cuánto suele tardar"; bots.appendChild(chip);
    }
    let reProg = null;
    try { if (op.progreso_regex || a.progreso_regex) reProg = new RegExp(op.progreso_regex || a.progreso_regex); }
    catch (e) { console.warn("progreso_regex inválida:", e); }

    // Estado ("Se está ejecutando…" bien visible, con el reloj)
    const est = crear("div", "app-panel-estado"); est.hidden = true;
    est.innerHTML = '<span class="app-punto"></span><span class="app-estado-txt"></span><span class="app-tiempo"></span>';
    el.appendChild(est);
    // Barra mientras corre el programa: real (progreso_regex) o estimada (duracion)
    const ejec = crear("div", "app-ejecucion"); ejec.hidden = true;
    ejec.innerHTML = '<div class="app-barra fija"><div></div></div><p class="app-ejecucion-txt"></p>';
    el.appendChild(ejec);

    // Progreso de la preparación (entorno, pip): barra real por pasos de pip
    const prog = crear("div", "app-progreso"); prog.hidden = true;
    prog.innerHTML = '<div class="app-barra fija"><div></div></div><p class="app-progreso-txt"></p><p class="app-progreso-paso"></p>'
      + '<details class="app-plegado"><summary>Ver lo que se está instalando (técnico)</summary><pre class="app-pre"></pre></details>';
    el.appendChild(prog);
    const preProg = prog.querySelector("pre");

    // Resumen (error / bien)
    const res = crear("div", "app-resumen"); res.hidden = true; el.appendChild(res);

    // Salida en vivo
    const caja = crear("div", "app-salida-caja"); caja.hidden = true;
    caja.innerHTML = '<div class="app-salida-cab"><span>Lo que dice el programa</span><label><input type="checkbox" checked> seguir al final</label></div>'
      + '<pre class="app-salida" aria-live="polite"></pre>';
    const pre = caja.querySelector("pre"), auto = caja.querySelector("input");
    const parcial = crear("span", "app-parcial"); pre.appendChild(parcial);
    const form = crear("form", "app-entrada"); form.hidden = true;
    form.innerHTML = '<input type="text" autocomplete="off" placeholder="Escríbele aquí al programa y pulsa Enter"><button class="app-btn primario" type="submit">Enviar</button>';
    caja.appendChild(form);
    if (Array.isArray(op.sugerencias) && op.sugerencias.length) {
      const sug = crear("div", "app-sugerencias");
      for (const s of op.sugerencias) {
        const b = crear("button", "app-btn app-btn-mini"); b.type = "button"; b.textContent = s;
        b.onclick = () => enviar(s); sug.appendChild(b);
      }
      form.appendChild(sug);
    }
    const plegar = crear("details", "app-plegado app-salida-plegada"); plegar.hidden = true;
    plegar.innerHTML = "<summary>Ver toda la salida del programa</summary>";
    el.appendChild(caja); el.appendChild(plegar);

    // Detalles técnicos plegados (rutas y comandos solo aquí)
    const tec = crear("details", "app-plegado app-tecnico");
    const filas = [];
    if (a.muestra) filas.push(["Comando", a.muestra]);
    if (a.archivo) filas.push(["Archivo", `${CARPETA}/${a.archivo}`]);
    if (a.url) filas.push(["Dirección", a.url]);
    if (a.cubre && a.cubre.length) filas.push(["Cubre del enunciado", a.cubre.join(" · ")]);
    filas.push(["Práctica / acción", `${CARPETA} · ${a.id} (${a.tipo}${a.tipo === "python" ? ", " + (consola ? "en consola" : "salida en esta página") : ""})`]);
    tec.innerHTML = "<summary>Detalles técnicos</summary>" + filas.map(([k, v]) => `<div class="app-fila"><b>${esc(k)}</b> <code>${esc(v)}</code></div>`).join("");
    el.appendChild(tec);

    // ---------------- comportamiento
    let lineas = [], nLineas = 0, reloj = null, inicio = 0, siguiendo = false;
    // inicioProg: cuándo arrancó el PROGRAMA (tras preparar el entorno): de ahí cuenta la duración.
    let inicioProg = 0, fracReal = null, ultT = {};
    // Preparación del entorno: pasos de pip vistos (para la barra real).
    const PIP = { buscados: 0, instalando: 0, tInstalar: 0, compilando: 0, listo: false };

    function pintarEstado(t) {
      const e = t.estado || "listo";
      ultT = t;
      el.dataset.estado = e; ctl.estado = e;
      est.hidden = false;
      let txt = ESTADOS[e] || e;
      if (e === "lanzada") {
        if (a.tipo === "python" && consola) txt = "En marcha en su ventana de consola";
        else if (a.ventana) txt = "En marcha: mira la ventana que se abrió (puede tardar unos segundos en aparecer)";
        else if (a.tipo === "docker") txt = "Se está ejecutando… (Docker trabajando)";
        else txt = "Se está ejecutando…";
      }
      if (e === "terminada" && a.tipo === "archivo") txt = "Abierto con el programa del sistema";
      if (["preparando", "instalando"].includes(e) && t.mensaje && a.tipo !== "python") txt = t.mensaje;
      est.querySelector(".app-estado-txt").textContent = txt;
      est.classList.toggle("activo", activo(e));
      if (activo(e)) {
        inicio = inicio || (t.inicio ? t.inicio * 1000 : Date.now());
        if (e === "lanzada") inicioProg = inicioProg || (t.lanzado ? t.lanzado * 1000 : Date.now());
        if (!reloj) reloj = setInterval(tiempo, 1000);
      } else { clearInterval(reloj); reloj = null; }
      // Progreso de la preparación
      const preparando = e === "preparando" || e === "instalando";
      prog.hidden = !preparando || (a.tipo !== "python");
      if (preparando) prog.querySelector(".app-progreso-txt").textContent = t.mensaje || "Preparando…";
      if (e === "lanzada" && !PIP.listo && (PIP.buscados || PIP.instalando)) PIP.listo = true;
      tiempo();
      // Botones
      bIni.disabled = activo(e) || !!a.error;
      bIni.classList.toggle("ocupado", activo(e));
      if (activo(e)) bIni.textContent = e === "lanzada" ? "Ejecutándose…" : "Preparando…";
      if (a.tipo !== "docker") bDet.hidden = !(activo(e) && (a.tipo === "python"));
      if (!activo(e)) bIni.textContent = e === "listo" ? (op.botonTexto || `${BOTON[a.tipo] || "Iniciar"}: ${a.nombre}`)
        : (op.botonTexto ? op.botonTexto : `Volver a ${(BOTON[a.tipo] || "iniciar").toLowerCase()}`);
      form.hidden = !(a.entrada && !consola && e === "lanzada");
      if (!form.hidden && document.activeElement === document.body) form.querySelector("input").focus();
      // Parcial (texto sin salto de línea, p. ej. la pregunta de un input())
      parcial.textContent = t.parcial || "";
      form.querySelector("input").placeholder = t.parcial && t.parcial.trim()
        ? "El programa espera tu respuesta: escríbela aquí y pulsa Enter" : "Escríbele aquí al programa y pulsa Enter";
      if (t.abrir) { bAbrir.hidden = false; bAbrir.textContent = "Abrir " + t.abrir; bAbrir.onclick = () => window.open(t.abrir, "_blank", "noopener"); }
      op.alEstado && op.alEstado(t);
    }

    // Fracción (0-1) de la preparación del entorno según lo que va diciendo pip: es una barra
    // REAL por pasos (revisar → crear el entorno → buscar/descargar cada paquete → instalar).
    function fracPip() {
      if (PIP.listo) return 1;
      const fase = ultT.fase || "";
      if (PIP.instalando) {
        const s = (Date.now() - PIP.tInstalar) / 1000;   // pip no dice nada mientras instala: avanza solo, sin llegar
        return 0.75 + 0.22 * (1 - Math.exp(-s / 40));
      }
      if (PIP.compilando) {
        const s = (Date.now() - PIP.compilando) / 1000;  // PyBullet: ~10-15 min
        return 0.55 + 0.2 * Math.min(1, s / 720);
      }
      if (PIP.buscados) {
        const n = Math.max(1, ((S.practica.python || {}).paquetes || []).length);
        return 0.15 + 0.4 * (1 - 1 / (1 + PIP.buscados / (n * 1.5)));
      }
      if (fase === "creando") return 0.1;
      if (fase === "instalando" || fase === "compilando") return 0.14;
      return 0.04;
    }

    function tiempo() {
      const tEl = est.querySelector(".app-tiempo");
      if (!inicio || !activo(ctl.estado)) { tEl.textContent = ""; ejec.hidden = true; return; }
      const preparando = ctl.estado !== "lanzada";
      if (preparando) {
        tEl.textContent = " · lleva " + mmss((Date.now() - inicio) / 1000);
        if (!prog.hidden) {
          const f = fracPip();
          prog.querySelector(".app-barra div").style.width = Math.round(f * 100) + "%";
          prog.querySelector(".app-progreso-txt").dataset.pct = Math.round(f * 100) + " %";
        }
        ejec.hidden = true;
        return;
      }
      // El programa está corriendo: "lleva m:ss de ~m:ss" y la barra (real o estimada).
      const s = (Date.now() - (inicioProg || inicio)) / 1000;
      let txt = " · lleva " + mmss(s);
      if (durS) txt += s <= durS * 1.1 ? " de ~" + mmss(durS) : " (suele tardar ~" + mmss(durS) + "; sigue trabajando)";
      tEl.textContent = txt;
      const hayBarra = (durS || reProg) && !consola;
      ejec.hidden = !hayBarra;
      if (!hayBarra) return;
      const barra = ejec.querySelector(".app-barra div"), nota = ejec.querySelector("p");
      if (fracReal !== null) {
        barra.style.width = Math.round(Math.min(1, fracReal) * 100) + "%";
        let q = `Avance real: ${Math.round(fracReal * 100)} %`;
        if (fracReal > 0.03 && fracReal < 1) q += ` · quedan ~${mmss(s / fracReal - s)}`;
        nota.textContent = q; ejec.classList.add("real");
      } else if (durS) {
        // Estimada: avanza con el tiempo según lo que suele tardar, sin llegar nunca al final
        // (el final lo marca el programa al terminar).
        const f = s <= durS ? 0.95 * s / durS : 0.95 + 0.04 * (1 - Math.exp(-(s - durS) / durS));
        barra.style.width = Math.round(f * 100) + "%";
        nota.textContent = s <= durS ? `Estimado: suele tardar ${a.duracion || "~" + mmss(durS)}. Puedes seguir leyendo la app mientras tanto.`
          : "Está tardando más de lo habitual; mientras la salida siga avanzando, va bien.";
        ejec.classList.remove("real");
      } else {
        barra.style.width = "4%"; nota.textContent = "Esperando la primera línea de avance del programa…";
      }
    }

    function linea(x, tipo) {
      if (tipo === "pip") {
        preProg.textContent += x + "\n";
        if (preProg.textContent.length > 60000) preProg.textContent = preProg.textContent.slice(-40000);
        if (/^Collecting /.test(x)) PIP.buscados++;
        if (/Building wheel for pybullet/i.test(x) && !PIP.compilando) PIP.compilando = Date.now();
        if (/Installing collected packages/.test(x) && !PIP.instalando) { PIP.instalando = 1; PIP.tInstalar = Date.now(); }
        if (/Successfully installed/.test(x)) PIP.listo = true;
        const paso = pasoPip(x);
        if (paso) prog.querySelector(".app-progreso-paso").textContent = paso + (PIP.buscados > 1 && !PIP.instalando ? ` (${PIP.buscados} paquetes revisados)` : "");
        tiempo();
        return;
      }
      if (consola && tipo === "sis") return;
      // Mensajes del lanzador antes de arrancar el programa ("Reviso el entorno", "Lanzo: …"):
      // van al registro técnico de la preparación, no a "Lo que dice el programa".
      if (tipo === "sis" && ["preparando", "instalando", "listo"].includes(ctl.estado)) {
        preProg.textContent += x + "\n";
        if (!/^(Lanzo|\$ )/.test(x)) prog.querySelector(".app-progreso-paso").textContent = x;
        return;
      }
      if (reProg && tipo === "prog") {
        const m = reProg.exec(x);
        if (m) {
          const n1 = parseFloat(String(m[1]).replace(",", ".")), n2 = m[2] !== undefined ? parseFloat(String(m[2]).replace(",", ".")) : NaN;
          const f = !isNaN(n2) && n2 > 0 ? n1 / n2 : n1 / 100;
          if (isFinite(f) && f >= 0) { fracReal = Math.min(1, f); tiempo(); }
        }
      }
      lineas.push(x); if (lineas.length > 4000) lineas = lineas.slice(-3000);
      if (consola) return;
      caja.hidden = false;
      // "pregunta" = lo que el programa escribió sin salto de línea antes de que contestaras
      // (input("Escribe: ")): va en la misma línea que la respuesta, como en una consola.
      const tras = parcial.previousSibling;
      const pegada = tipo === "in" && tras && tras.classList && tras.classList.contains("l-pregunta");
      const s = crear("span", "l-" + tipo);
      s.textContent = tipo === "pregunta" ? x : (tipo === "in" && !pegada ? "> " : "") + x + "\n";
      pre.insertBefore(s, parcial);
      if (++nLineas > 3000) { pre.removeChild(pre.firstChild); nLineas--; }
      if (auto.checked) pre.scrollTop = pre.scrollHeight;
      op.alLinea && op.alLinea(x, tipo);
    }

    function final(t) {
      res.hidden = false; res.className = "app-resumen";
      res.innerHTML = "";
      if (t.estado === "terminada") {
        res.classList.add("ok");
        const tit = crear("b"); tit.textContent = a.tipo === "python" ? "Terminó bien." : (t.mensaje || "Listo.");
        res.appendChild(tit);
        const c = contenido(op.alTerminarBien); if (c) res.appendChild(c);
      } else if (t.estado === "detenida") {
        res.classList.add("info");
        res.textContent = "Detenido. Puedes volver a iniciarlo cuando quieras.";
      } else if (t.estado === "error") {
        res.classList.add("error");
        const prog_ = lineas.filter((l) => l.trim());
        const r = resumenError(t, prog_, a);
        res.appendChild(crear("b", "", esc(r.titulo)));
        const p = crear("p"); p.textContent = r.texto; res.appendChild(p);
        // "si_falla" de la acción (probar.json) u opción siFalla del panel: qué hacer, propio de esta acción.
        const extra = op.siFalla || (t.fallo_en !== "preparar" && a.si_falla);
        if (extra) { const q = crear("p", "app-si-falla"); q.textContent = extra; res.appendChild(q); }
        const w = /winget install[^\n]*?--includeRecommended"/.exec(r.texto || "");
        if (w) {
          const c = crear("div", "app-comando"); const code = crear("code"); code.textContent = w[0];
          const cp = crear("button", "app-btn app-btn-mini", "Copiar comando");
          cp.onclick = () => { navigator.clipboard && navigator.clipboard.writeText(w[0]); aviso("Comando copiado.", "ok"); };
          c.append(code, cp); res.appendChild(c);
        }
        const ult = (t.fallo_en === "preparar" ? preProg.textContent.split("\n").filter((l) => l.trim()) : prog_)
          .filter((l) => l.trim() !== String(r.texto || "").trim()).slice(-8);
        if (ult.length) {
          res.appendChild(crear("div", "app-etiqueta", "Últimas líneas"));
          const u = crear("pre", "app-pre"); u.textContent = ult.join("\n"); res.appendChild(u);
        }
        // La salida completa (con la traza de Python) queda plegada.
        if (!caja.hidden) { plegar.hidden = false; plegar.appendChild(caja); }
      }
      emitir("panel", { accion: accionId, trabajo: t });
      op.alTerminar && op.alTerminar(t);
    }

    async function seguirTrabajo(t0, limpiar) {
      if (limpiar) {
        lineas = []; nLineas = 0; inicio = 0; inicioProg = 0; fracReal = null;
        Object.assign(PIP, { buscados: 0, instalando: 0, tInstalar: 0, compilando: 0, listo: false });
        for (const s of [...pre.querySelectorAll("span:not(.app-parcial)")]) s.remove();
        preProg.textContent = ""; prog.querySelector(".app-progreso-paso").textContent = "";
        res.hidden = true; plegar.hidden = true; if (plegar.contains(caja)) el.insertBefore(caja, plegar);
        caja.hidden = true;
      }
      siguiendo = true;
      pintarEstado(t0);
      const t = await seguir(t0.tid, { alLinea: linea, alEstado: pintarEstado });
      siguiendo = false;
      pintarEstado(t);
      if (terminoBien(t)) emitir("ok", accionId);
      emitir("fin", { accion: accionId, trabajo: t });
      final(t);
      return t;
    }

    async function iniciarAccion() {
      if (S.caido) { aviso("El lanzador está cerrado: vuelve a abrir la práctica con su ABRIR.bat.", "error"); return; }
      if (navegable(a)) {
        window.open(a.tipo === "url" ? a.url : a.enlace, "_blank", "noopener");
        pintarEstado({ estado: "terminada", mensaje: "Abierto en una pestaña nueva." });
        res.hidden = false; res.className = "app-resumen ok"; res.textContent = "Abierto en una pestaña nueva del navegador.";
        emitir("ok", accionId); return;
      }
      bIni.disabled = true;
      try {
        const t0 = await api("/api/accion", { carpeta: CARPETA, accion: accionId, modo: "app" });
        await seguirTrabajo(t0, true);
      } catch (e) {
        bIni.disabled = false;
        pintarEstado({ estado: "error", mensaje: e.message, fallo_en: "preparar" });
        final({ estado: "error", mensaje: e.message, fallo_en: "preparar" });
      }
    }

    async function detenerAccion() {
      bDet.disabled = true;
      try {
        const t = await detener(accionId);
        // En docker, detener es un trabajo nuevo (docker compose stop): se sigue en el mismo panel.
        if (a.tipo === "docker" && t && t.tid && !siguiendo) await seguirTrabajo(t, true);
      } catch (e) { aviso(e.message, "error"); }
      finally { bDet.disabled = false; }
    }

    function enviar(texto) {
      if (form.hidden) { aviso("El programa no está esperando texto ahora.", "info"); return; }
      entrada(accionId, texto).catch((e) => aviso(e.message, "error"));
    }

    bIni.onclick = iniciarAccion;
    bDet.onclick = detenerAccion;
    form.onsubmit = (ev) => {
      ev.preventDefault();
      const i = form.querySelector("input"); const v = i.value;
      i.value = ""; enviar(v); i.focus();
    };
    ctl.iniciar = iniciarAccion; ctl.detener = detenerAccion; ctl.enviar = enviar; ctl.accion = a;

    // Si la acción ya estaba corriendo (recargaste la página), se vuelve a enganchar a su salida.
    const previo = ((S.datos && S.datos.trabajos) || []).find((t) => t.accion === accionId && activo(t.estado) && t.modo === "app");
    if (previo) seguirTrabajo(previo, true);
  }

  // ------------------------------------------------------------------ markdown
  function recortar(texto, desde, hasta) {
    if (!desde) return texto;
    const ls = texto.split(/\r?\n/);
    let enCodigo = false, ini = -1, nivel = 0, fin = ls.length;
    const objetivo = norm(desde);
    for (let i = 0; i < ls.length; i++) {
      const l = ls[i];
      if (/^\s*(```|~~~)/.test(l)) { enCodigo = !enCodigo; continue; }
      if (enCodigo) continue;
      const m = l.match(/^(#{1,6})\s/);
      if (ini < 0) {
        if (m && (norm(l) === objetivo || norm(l).startsWith(objetivo))) { ini = i; nivel = m[1].length; }
        continue;
      }
      if (hasta && norm(l).startsWith(norm(hasta))) { fin = i; break; }
      if (!hasta && m && m[1].length <= nivel) { fin = i; break; }
    }
    if (ini < 0) return null;
    return ls.slice(ini, fin).join("\n");
  }

  async function markdown(el, ruta, op = {}) {
    el = $(el);
    if (!el) return null;
    el.classList.add("app-md");
    el.textContent = "Cargando…";
    let texto;
    try {
      const r = await fetch(rutaRepo(ruta), { cache: "no-store" });
      if (!r.ok) throw new Error();
      texto = await r.text();
    } catch (e) { el.textContent = `No se pudo leer ${ruta}.`; return el; }
    let parte = recortar(texto, op.desde, op.hasta);
    if (parte === null) { console.warn(`App.markdown: no encontré "${op.desde}" en ${ruta}`); parte = texto; }
    if (op.sinTitulo) parte = parte.replace(/^#{1,6}\s.*\n?/, "");
    try { await cargarScript(MARKED); } catch (e) { /* sin internet */ }
    if (!window.marked) { el.innerHTML = ""; const p = crear("pre", "app-md-crudo"); p.textContent = parte; el.appendChild(p); return el; }
    el.innerHTML = window.marked.parse(parte);
    const dir = String(ruta).replace(/\\/g, "/").split("/").slice(0, -1).join("/");
    const base = location.origin + rutaRepo(dir ? dir + "/" : "") + (dir ? "/" : "");
    const relativa = (u) => u && !/^([a-z]+:|\/|#)/i.test(u);
    for (const img of el.querySelectorAll("img")) {
      const s = img.getAttribute("src"); if (relativa(s)) img.src = new URL(s, base).href;
      img.loading = "lazy";
    }
    for (const aEl of el.querySelectorAll("a[href]")) {
      const h = aEl.getAttribute("href");
      if (relativa(h)) aEl.href = new URL(h, base).href;
      if (!h.startsWith("#")) { aEl.target = "_blank"; aEl.rel = "noopener"; }
    }
    for (const t of el.querySelectorAll("table")) { const w = crear("div", "app-tabla-scroll"); t.replaceWith(w); w.appendChild(t); }
    const merm = el.querySelectorAll("code.language-mermaid");
    if (merm.length) {
      for (const c of merm) { const d = crear("div", "mermaid"); d.textContent = c.textContent; c.parentElement.replaceWith(d); }
      const dibujar = async () => {
        try {
          await cargarScript(MERMAID);
          window.mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "strict" });
          await window.mermaid.run({ nodes: el.querySelectorAll(".mermaid:not([data-processed])") });
        } catch (e) { /* sin internet: queda el texto del diagrama */ }
      };
      // Mermaid mide el texto para dibujar: dentro de un paso oculto saldría vacío. Se dibuja
      // cuando el elemento se ve por primera vez.
      if (el.offsetParent !== null || !("IntersectionObserver" in window)) await dibujar();
      else {
        const obs = new IntersectionObserver((ents) => {
          if (ents.some((x) => x.isIntersecting)) { obs.disconnect(); dibujar(); }
        });
        obs.observe(el);
      }
    }
    imagen(el);
    return el;
  }

  // ------------------------------------------------------------------ pasos
  function pasos(contenedor, op = {}) {
    contenedor = $(contenedor);
    if (!contenedor) return null;
    let secciones = [...contenedor.children].filter((x) => x.matches("section.paso"));
    if (!secciones.length) secciones = [...contenedor.querySelectorAll("section.paso")];
    if (!secciones.length) return null;
    const clave = `app-pasos:${CARPETA}:${location.pathname}:${contenedor.id || ""}`;
    let guardado = {};
    try { guardado = JSON.parse(localStorage.getItem(clave) || "{}"); } catch (e) { /* sin almacenamiento */ }
    const vistos = new Set(guardado.vistos || []);

    contenedor.classList.add("app-pasos");
    const indice = crear("nav", "app-pasos-indice");
    const ol = crear("ol"); indice.appendChild(ol);
    const cuerpo = crear("div", "app-pasos-cuerpo");
    const barra = crear("div", "app-pasos-barra", '<div class="app-pasos-txt"></div><div class="app-barra fija"><div></div></div>');
    const nav = crear("div", "app-pasos-nav");
    const bAnt = crear("button", "app-btn", "← Anterior"), bSig = crear("button", "app-btn primario", "Siguiente →");
    nav.append(bAnt, bSig);
    cuerpo.appendChild(barra);
    secciones.forEach((s, i) => {
      const t = s.dataset.titulo || (s.querySelector("h2,h3") || {}).textContent || `Paso ${i + 1}`;
      s.dataset.titulo = t; s.id = s.id || `paso-${i + 1}`;
      cuerpo.appendChild(s);
      const li = crear("li"); const b = crear("button"); b.type = "button";
      b.innerHTML = `<span class="app-pasos-num">${i + 1}</span><span>${esc(t)}</span>`;
      b.onclick = () => ir(i); li.appendChild(b); ol.appendChild(li);
    });
    cuerpo.appendChild(nav);
    contenedor.prepend(indice); contenedor.appendChild(cuerpo);

    let actual = 0;
    function ir(i, desplazar = true) {
      actual = Math.max(0, Math.min(secciones.length - 1, i));
      vistos.add(actual);
      secciones.forEach((s, k) => { s.hidden = k !== actual; });
      [...ol.children].forEach((li, k) => { li.classList.toggle("actual", k === actual); li.classList.toggle("visto", vistos.has(k) && k !== actual); });
      barra.querySelector(".app-pasos-txt").textContent = `Paso ${actual + 1} de ${secciones.length} · ${secciones[actual].dataset.titulo}`;
      barra.querySelector(".app-barra div").style.width = `${((actual + 1) / secciones.length) * 100}%`;
      bAnt.disabled = actual === 0;
      bSig.textContent = actual === secciones.length - 1 ? "Volver al inicio" : `Siguiente: ${secciones[actual + 1].dataset.titulo} →`;
      try { localStorage.setItem(clave, JSON.stringify({ actual, vistos: [...vistos] })); } catch (e) { /* nada */ }
      if (desplazar) contenedor.scrollIntoView({ behavior: "smooth", block: "start" });
      emitir("paso", { indice: actual, titulo: secciones[actual].dataset.titulo, seccion: secciones[actual] });
      op.alCambiar && op.alCambiar(actual, secciones[actual]);
    }
    bAnt.onclick = () => ir(actual - 1);
    bSig.onclick = () => ir(actual === secciones.length - 1 ? 0 : actual + 1);
    const hash = /^#paso-(\d+)$/.exec(location.hash);
    ir(hash ? Number(hash[1]) - 1 : (op.inicio ?? guardado.actual ?? 0), false);
    return { ir: (i) => ir(i), get actual() { return actual; }, siguiente: () => ir(actual + 1), anterior: () => ir(actual - 1), secciones };
  }

  // ------------------------------------------------------------------ checklist
  function checklist(el, op = {}) {
    el = $(el);
    if (!el) return null;
    el.classList.add("app-checklist");
    el.innerHTML = '<p class="app-tenue">Cargando…</p>';
    const ctl = { marcar: () => {} };
    iniciar().then(() => {
      const pide = op.puntos || S.practica.pide || [];
      const clave = `app-checklist:${CARPETA}`;
      let hechos = {};
      try { hechos = JSON.parse(localStorage.getItem(clave) || "{}"); } catch (e) { /* nada */ }
      const guardar = () => { try { localStorage.setItem(clave, JSON.stringify(hechos)); } catch (e) { /* nada */ } };
      el.innerHTML = "";
      const cab = crear("div", "app-checklist-cab"); el.appendChild(cab);
      const ul = crear("ul"); el.appendChild(ul);
      // Qué acciones cubren cada punto (para el botón "probarlo").
      const quien = pide.map((p) => S.practica.acciones.filter((a) => (a.cubre || []).some((c) => norm(c) === norm(p) || norm(p).startsWith(norm(c)) || norm(c).startsWith(norm(p)))));
      const items = pide.map((p, i) => {
        const li = crear("li");
        const lab = crear("label"); const cb = crear("input"); cb.type = "checkbox"; cb.checked = !!hechos[norm(p)];
        const sp = crear("span"); sp.textContent = p;
        lab.append(cb, sp); li.appendChild(lab);
        if (quien[i].length) {
          const q = crear("span", "app-checklist-quien");
          const vis = quien[i].filter((a) => !a.oculta);
          q.textContent = vis.length ? "Se prueba con: " + vis.map((a) => a.nombre).join(" · ") : "";
          li.appendChild(q);
        }
        cb.onchange = () => { if (cb.checked) hechos[norm(p)] = "usuario"; else delete hechos[norm(p)]; guardar(); pintar(); };
        ul.appendChild(li);
        return { li, cb, p };
      });
      function pintar() {
        const n = items.filter((x) => x.cb.checked).length;
        items.forEach((x) => x.li.classList.toggle("hecho", x.cb.checked));
        cab.innerHTML = `<span>Qué pide la actividad</span><span class="app-chip ${n === items.length ? "ok" : ""}">${n} de ${items.length} probados</span>`;
      }
      ctl.marcar = (texto) => { const it = items.find((x) => norm(x.p) === norm(texto)); if (it) { it.cb.checked = true; hechos[norm(it.p)] = "auto"; guardar(); pintar(); } };
      on("ok", (accionId) => {
        let a; try { a = buscarAccion(accionId); } catch (e) { return; }
        items.forEach((x, i) => { if (quien[i].includes(a) && !x.cb.checked) { x.cb.checked = true; hechos[norm(x.p)] = "auto"; } });
        guardar(); pintar();
      });
      pintar();
    }).catch((e) => { el.textContent = e.message; });
    return ctl;
  }

  // ------------------------------------------------------------------ pestañas
  // App.pestanas(contenedor): los hijos <section data-pestana="Título"> (o class="pestana"
  // con data-titulo / su primer h2-h3) pasan a ser pestañas con una barra arriba. Recuerda la
  // elegida (localStorage) y acepta #pestana-N. Devuelve {ir(i | "título"), actual, secciones}.
  function pestanas(contenedor, op = {}) {
    contenedor = $(contenedor);
    if (!contenedor) return null;
    const secciones = [...contenedor.children].filter((x) => x.matches("[data-pestana], .pestana"));
    if (!secciones.length) return null;
    const clave = `app-pestanas:${CARPETA}:${location.pathname}:${contenedor.id || ""}`;
    contenedor.classList.add("app-pestanas");
    const barra = crear("div", "app-pestanas-barra"); barra.setAttribute("role", "tablist");
    const botones = secciones.map((s, i) => {
      const t = s.dataset.pestana || s.dataset.titulo || ((s.querySelector("h2,h3") || {}).textContent || `Parte ${i + 1}`).trim();
      s.dataset.pestana = t; s.classList.add("app-pestanas-panel"); s.setAttribute("role", "tabpanel");
      const b = crear("button", "app-pestanas-btn"); b.type = "button"; b.setAttribute("role", "tab");
      b.innerHTML = (s.dataset.icono ? `<span aria-hidden="true">${esc(s.dataset.icono)}</span> ` : "") + esc(t);
      b.onclick = () => ir(i); barra.appendChild(b);
      return b;
    });
    contenedor.prepend(barra);
    let actual = 0;
    function ir(i) {
      if (typeof i === "string") i = Math.max(0, secciones.findIndex((s) => norm(s.dataset.pestana) === norm(i)));
      actual = Math.max(0, Math.min(secciones.length - 1, i));
      secciones.forEach((s, k) => { s.hidden = k !== actual; });
      botones.forEach((b, k) => { b.classList.toggle("actual", k === actual); b.setAttribute("aria-selected", String(k === actual)); });
      try { localStorage.setItem(clave, String(actual)); } catch (e) { /* nada */ }
      emitir("pestana", { indice: actual, titulo: secciones[actual].dataset.pestana, seccion: secciones[actual] });
      op.alCambiar && op.alCambiar(actual, secciones[actual]);
    }
    let guardada = 0;
    try { guardada = Number(localStorage.getItem(clave) || 0) || 0; } catch (e) { /* nada */ }
    const h = /^#pestana-(\d+)$/.exec(location.hash);
    ir(h ? Number(h[1]) - 1 : (op.inicio ?? guardada));
    return { ir, get actual() { return actual; }, secciones };
  }

  // ------------------------------------------------------------------ tarjetas de estado
  // App.tarjetaEstado(el, {titulo, valor, detalle, estado: "ok"|"mal"|"aviso"|"activo"|""})
  // → {poner({...})}: una tarjeta pequeña tipo Docker Desktop ("Entorno · listo · Python 3.13").
  // Con {accion: "id"} se mantiene sola con el estado de esa acción del probar.json.
  function tarjetaEstado(el, op = {}) {
    el = $(el);
    if (!el) return null;
    el.classList.add("app-estado-tarjeta");
    el.innerHTML = '<span class="app-punto"></span><div><div class="app-etiqueta"></div><div class="app-estado-valor"></div><div class="app-estado-detalle"></div></div>';
    const ctl = {
      poner(o = {}) {
        Object.assign(op, o);
        el.querySelector(".app-etiqueta").textContent = op.titulo || "";
        el.querySelector(".app-estado-valor").textContent = op.valor || "";
        const d = el.querySelector(".app-estado-detalle"); d.textContent = op.detalle || ""; d.hidden = !op.detalle;
        el.dataset.estado = op.estado || "";
      },
    };
    ctl.poner();
    if (op.accion) {
      const NOMBRES = { preparando: ["Preparando…", "activo"], instalando: ["Preparando el entorno…", "activo"], lanzada: ["En marcha", "activo"],
        terminada: ["Terminó bien", "ok"], error: ["Falló", "mal"], detenida: ["Detenido", ""] };
      const pintar = () => {
        const t = Object.values(S.trabajos).filter((x) => x.accion === op.accion).pop();
        const [v, e] = t ? (NOMBRES[t.estado] || [t.estado, ""]) : ["Sin iniciar", ""];
        ctl.poner({ valor: v, estado: e });
      };
      on("estado", pintar); on("fin", pintar); pintar();
    }
    return ctl;
  }

  // ------------------------------------------------------------------ marco tipo Docker Desktop
  // App.marco({titulo, num, secciones}) arma la página entera como un programa: cabecera fija
  // (número, título, estado de la práctica, Pantalla completa), barra lateral con las secciones
  // y el área principal, que muestra UNA sección a la vez (como Containers / Images / Volumes
  // en Docker Desktop). Las secciones son los elementos [data-seccion="Nombre"] (opcional
  // data-icono="▶" y data-sub="texto corto"). Es opcional: las apps que no lo llaman quedan igual.
  // Devuelve {ir(i | "nombre"), actual, secciones}.
  function marco(op = {}) {
    const secciones = [...document.querySelectorAll(op.secciones || "[data-seccion]")];
    if (!secciones.length) return null;
    const p = S.practica || {};
    const raiz = crear("div", "app-marco");
    const cab = crear("header", "app-marco-cab");
    const num = op.num ?? (p.carpeta && !/^\d/.test(p.carpeta) ? "★" : (p.id || ""));
    cab.innerHTML = `${num ? `<span class="app-num">${esc(num)}</span>` : ""}<h1>${esc(op.titulo || p.titulo || document.title)}</h1>`;
    const lateral = crear("nav", "app-marco-lateral"); lateral.setAttribute("aria-label", "Secciones");
    const cuerpo = crear("main", "app-marco-cuerpo");
    const ancla = secciones[0];
    ancla.parentNode.insertBefore(raiz, ancla);
    raiz.append(cab, lateral, cuerpo);
    const botones = secciones.map((s, i) => {
      const t = s.dataset.seccion || `Sección ${i + 1}`;
      s.classList.add("app-marco-seccion"); s.id = s.id || `s-${i + 1}`;
      cuerpo.appendChild(s);
      const b = crear("button", "app-marco-item"); b.type = "button";
      b.innerHTML = `<span class="app-marco-icono" aria-hidden="true">${esc(s.dataset.icono || String(i + 1))}</span>`
        + `<span class="app-marco-txt">${esc(t)}${s.dataset.sub ? `<small>${esc(s.dataset.sub)}</small>` : ""}</span>`;
      b.onclick = () => ir(i); lateral.appendChild(b);
      return b;
    });
    if (op.pie !== false) {
      const pie = crear("div", "app-marco-pie");
      pie.innerHTML = '<button type="button" class="app-btn app-btn-mini" data-readme>README completo</button>';
      pie.querySelector("[data-readme]").onclick = () => abrir("README.md");
      lateral.appendChild(pie);
    }
    document.body.classList.add("app-con-marco");
    // La barra de herramientas (pantalla completa + estado) va a la cabecera del marco.
    if (HERR.el && HERR.el.classList.contains("franja")) { HERR.el.classList.remove("franja"); cab.appendChild(HERR.el); }
    else if (!HERR.el) herramientas();
    const clave = `app-marco:${CARPETA}:${location.pathname}`;
    let actual = 0;
    function ir(i, guardar = true) {
      if (typeof i === "string") i = Math.max(0, secciones.findIndex((s) => norm(s.dataset.seccion) === norm(i) || s.id === i));
      actual = Math.max(0, Math.min(secciones.length - 1, i));
      secciones.forEach((s, k) => { s.hidden = k !== actual; });
      botones.forEach((b, k) => b.classList.toggle("actual", k === actual));
      cuerpo.scrollTop = 0;
      if (guardar) try { localStorage.setItem(clave, String(actual)); } catch (e) { /* nada */ }
      emitir("seccion", { indice: actual, titulo: secciones[actual].dataset.seccion, seccion: secciones[actual] });
      op.alCambiar && op.alCambiar(actual, secciones[actual]);
    }
    let guardada = 0;
    try { guardada = Number(localStorage.getItem(clave) || 0) || 0; } catch (e) { /* nada */ }
    const h = /^#s-(\d+)$/.exec(location.hash);
    ir(h ? Number(h[1]) - 1 : (op.inicio ?? guardada), false);
    return { ir, get actual() { return actual; }, secciones };
  }

  // ------------------------------------------------------------------ abrir / imagen / aviso
  function abrir(rutaOUrl) {
    const s = String(rutaOUrl || "");
    if (/^(https?:|mailto:)/i.test(s) || s.startsWith("/")) { window.open(s, "_blank", "noopener"); return; }
    if (/^readme\.md$/i.test(s)) { window.open("/readme/" + encodeURIComponent(CARPETA), "_blank", "noopener"); return; }
    window.open(rutaRepo(s), "_blank", "noopener");
  }

  let caja_ = null;
  function imagen(el) {
    el = $(el);
    if (!el) return;
    const imgs = el.tagName === "IMG" ? [el] : [...el.querySelectorAll("img")];
    for (const img of imgs) {
      if (img.dataset.appAmpliar) continue;
      img.dataset.appAmpliar = "1"; img.classList.add("app-ampliable");
      img.addEventListener("click", () => {
        if (!caja_) {
          caja_ = crear("div", "app-lightbox");
          caja_.innerHTML = '<figure><img alt=""><figcaption></figcaption></figure><button class="app-btn" aria-label="Cerrar">Cerrar ✕</button>';
          caja_.onclick = () => { caja_.hidden = true; };
          document.addEventListener("keydown", (e) => { if (e.key === "Escape" && caja_) caja_.hidden = true; });
          document.body.appendChild(caja_);
        }
        caja_.querySelector("img").src = img.currentSrc || img.src;
        caja_.querySelector("figcaption").textContent = img.alt || img.title || "";
        caja_.hidden = false;
      });
    }
  }

  let pila = null;
  function aviso(texto, tipo = "info", ms) {
    if (!pila) { pila = crear("div", "app-toasts"); document.body.appendChild(pila); }
    const t = crear("div", "app-toast " + tipo);
    t.textContent = texto;
    t.onclick = () => t.remove();
    pila.appendChild(t);
    const dur = ms === undefined ? (tipo === "error" ? 12000 : 5000) : ms;
    if (dur > 0) setTimeout(() => t.remove(), dur);
    return t;
  }

  function on(evento, f) { (S.oyentes[evento] = S.oyentes[evento] || []).push(f); }

  // ------------------------------------------------------------------ exportar
  const App = {
    version: VERSION, carpeta: CARPETA, practica: null, entorno: null,
    iniciar, panelEjecucion, accion, detener, entrada, markdown, pasos, checklist, abrir, imagen, aviso,
    on, url: rutaRepo,
    // versión 2: pantalla de carga, barra de herramientas, marco, pestañas, tarjetas de estado
    marco, pestanas, tarjetaEstado, pantallaCompleta, carga, cargaLista, mmss,
  };
  window.App = App;
})();
