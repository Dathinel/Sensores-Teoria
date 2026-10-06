/* Centro de control del laboratorio (tema 11).
 *
 * Usa la API común window.App (apps-comun/app.js): App.iniciar, App.pasos, App.panelEjecucion,
 * App.accion, App.detener, App.checklist, App.markdown, App.imagen, App.url. Lo propio de esta
 * práctica está aquí:
 *   - la animación "Docker paso a paso" (docker-anim.js), a la que se le pasan los datos reales,
 *   - el PROGRESO REAL al levantar: lee línea a línea lo que imprime `docker compose` (imágenes que
 *     se bajan o construyen, redes que se crean, contenedores que arrancan) y lo dibuja con su barra,
 *   - el estado en vivo (mapa, LED, latencias y la lista de contenedores como Docker Desktop), que
 *     llega por la acción "vivo" (app/estado_vivo.py), porque el admin en 127.0.0.1:8180 no
 *     permite CORS y la página no puede leerlo directo,
 *   - la prueba de aislamiento dibujada caso por caso en un mapa (en vivo y repetida del json),
 *   - los resultados de las pruebas, leídos de pruebas/resultados/*.json y dibujados.
 */
(function () {
  "use strict";

  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (v, dec = 2) => (v === null || v === undefined || Number.isNaN(Number(v))) ? "—" : Number(v).toLocaleString("es-CO", { minimumFractionDigits: dec, maximumFractionDigits: dec });
  const R = (ruta) => (window.App && App.url ? App.url(ruta) : ruta);
  const fechaDe = (epoch) => epoch ? new Date(epoch * 1000).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" }) : "—";
  const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  const DASHBOARD = "http://127.0.0.1:8180/";   // el contenedor admin escucha en 8080; en el PC se publica en 8180

  // ---------------------------------------------------------------- datos fijos del laboratorio
  const ZONA = {
    1: { nombre: "Zona Gamer (VLAN 1)", red: "192.168.10.0/24", color: "#3fbf8f", clase: "c11-zona-g" },
    2: { nombre: "Zona Robótica (VLAN 2)", red: "192.168.20.0/24", color: "#f0913a", clase: "c11-zona-r" },
    3: { nombre: "Plano de administración (VLAN 3)", red: "192.168.30.0/24", color: "#a77be8", clase: "c11-zona-a" },
    0: { nombre: "Las tres redes", red: ".254 en cada una", color: "#4f8fce", clase: "" },
  };
  // x, y = centro de la caja en el mapa (viewBox 900 x 560); w = ancho.
  const NODOS = [
    { id: "track-server", vlan: 1, ip: "192.168.10.10", x: 220, y: 78, w: 170, visor: "pista", puerto: 8010,
      que: "El servidor de la carrera: PyBullet sin pantalla con física a 240 Hz, 6 carros (3 de jugadores y 3 autónomos que se adelantan y se esquivan), vueltas y failsafe. Recibe a los jugadores por WebSocket (puerto 8765)." },
    { id: "player-1", vlan: 1, ip: "192.168.10.21", x: 95, y: 152, w: 112, esp: "ctrl-1", led: "GPIO 16",
      que: "Jugador rojo (deportivo). Recibe el joystick de su ESP32 por UDP, cuenta los paquetes perdidos y el jitter, y le pasa el mando al servidor de pista por WebSocket. Si pasa 1 s sin mando, frena el carro (failsafe)." },
    { id: "player-2", vlan: 1, ip: "192.168.10.22", x: 220, y: 152, w: 112, esp: "ctrl-2", led: "GPIO 17",
      que: "Jugador azul (clásico). Igual que player-1, con su propio ESP32 y su carro." },
    { id: "player-3", vlan: 1, ip: "192.168.10.23", x: 345, y: 152, w: 112, esp: "ctrl-3", led: "GPIO 18",
      que: "Jugador verde (rally). Igual que player-1, con su propio ESP32 y su carro." },
    { id: "ctrl-1", vlan: 1, ip: "192.168.10.31", x: 95, y: 228, w: 100, emu: true, manda: "player-1",
      que: "ESP32 maestra emulada con joystick: manda CTRL (dirección, velocidad, botón) a 20 Hz a player-1. Trae un piloto automático que mira la pista." },
    { id: "ctrl-2", vlan: 1, ip: "192.168.10.32", x: 220, y: 228, w: 100, emu: true, manda: "player-2",
      que: "ESP32 maestra emulada de player-2 (joystick con piloto automático)." },
    { id: "ctrl-3", vlan: 1, ip: "192.168.10.33", x: 345, y: 228, w: 100, emu: true, manda: "player-3",
      que: "ESP32 maestra emulada de player-3 (joystick con piloto automático)." },
    { id: "sim-spot", vlan: 2, ip: "192.168.20.21", x: 560, y: 110, w: 112, visor: "spot", puerto: 8011, esp: "ctrl-spot", led: "GPIO 19",
      que: "El Rex, un pequeño Spot (SpotMicro de rex-gym), en PyBullet. Sus 3 ángulos mueven la pose del cuerpo; el botón lo hace trotar. Mide el error real-to-sim." },
    { id: "sim-pepper", vlan: 2, ip: "192.168.20.22", x: 680, y: 110, w: 112, visor: "pepper", puerto: 8012, esp: "ctrl-pepper", led: "GPIO 21",
      que: "Pepper (modelo de qiBullet) copiando hombro, codo y cabeza de su ESP32; el botón saluda. Sin las mallas de SoftBank se dibuja como esqueleto." },
    { id: "sim-nao", vlan: 2, ip: "192.168.20.23", x: 800, y: 110, w: 112, visor: "nao", puerto: 8013, esp: "ctrl-nao", led: "GPIO 22",
      que: "NAO (modelo de qiBullet) copiando hombro, codo y cabeza de su ESP32; el botón saluda." },
    { id: "ctrl-spot", vlan: 2, ip: "192.168.20.31", x: 560, y: 205, w: 104, emu: true, manda: "sim-spot",
      que: "ESP32 maestra emulada con 3 potenciómetros: manda JOINTS (3 ángulos y botón) a sim-spot, moviéndolos con senos lentos y apretando el botón cada 12 s." },
    { id: "ctrl-pepper", vlan: 2, ip: "192.168.20.32", x: 680, y: 205, w: 104, emu: true, manda: "sim-pepper",
      que: "ESP32 maestra emulada de sim-pepper (potenciómetros simulados)." },
    { id: "ctrl-nao", vlan: 2, ip: "192.168.20.33", x: 800, y: 205, w: 104, emu: true, manda: "sim-nao",
      que: "ESP32 maestra emulada de sim-nao (potenciómetros simulados)." },
    { id: "admin", vlan: 3, ip: "192.168.30.10", x: 375, y: 470, w: 170, visor: "dashboard", puerto: 8180,
      que: "La sala de control: broker MQTT (Mosquitto), recibe los latidos UDP de todos, hace ping a cada contenedor a través del router, decide OK / LENTO / CAIDO, lo publica por MQTT y lo muestra en el dashboard (en tu PC, puerto 8180)." },
    { id: "esclava", vlan: 3, ip: "192.168.30.40", x: 580, y: 470, w: 170, emu: true, servicio: "esclava-emulada",
      que: "ESP32 esclava emulada: se suscribe por MQTT a lab/estado/<servicio> y prende sus 6 LED (encendido = OK, parpadeo = LENTO, apagado = CAIDO)." },
    { id: "router", vlan: 0, ip: "192.168.10.254 · 20.254 · 30.254", x: 450, y: 322, w: 120, router: true,
      que: "Alpine con FRR (tabla de rutas) e iptables: tiene una pata en cada red. Reenvía lo permitido (admin ↔ zonas) y descarta (DROP) todo lo que intente cruzar entre la VLAN 1 y la VLAN 2, contando cada paquete descartado." },
  ];
  const GPIO = { "player-1": 16, "player-2": 17, "player-3": 18, "sim-spot": 19, "sim-pepper": 21, "sim-nao": 22 };
  const ORDEN_TABLA = ["track-server", "player-1", "player-2", "player-3", "sim-spot", "sim-pepper", "sim-nao", "router"];
  // Los 16 servicios del compose, en el orden en que conviene mostrarlos, con su red.
  const SERVICIOS = [
    ["router", 0], ["admin", 3], ["esclava-emulada", 3],
    ["track-server", 1], ["player-1", 1], ["player-2", 1], ["player-3", 1], ["ctrl-1", 1], ["ctrl-2", 1], ["ctrl-3", 1],
    ["sim-spot", 2], ["sim-pepper", 2], ["sim-nao", 2], ["ctrl-spot", 2], ["ctrl-pepper", 2], ["ctrl-nao", 2],
  ];
  const RED_DE = Object.fromEntries(SERVICIOS);
  // Las 6 imágenes: MB comprimidos de Docker Hub (docker manifest inspect, 2026-10-05) y tamaño en disco.
  const IMAGENES = [
    { k: "router", mb: 11, disco: "47,6 MB" }, { k: "admin", mb: 19, disco: "79,2 MB" },
    { k: "servidor-pista", mb: 211, disco: "890 MB" }, { k: "jugador", mb: 53, disco: "230 MB" },
    { k: "robot", mb: 214, disco: "898 MB" }, { k: "emulador", mb: 53, disco: "228 MB" },
  ];
  const MB_DESCARGA = 415;   // capas únicas de las 6 imágenes (34 capas): lo que baja la primera vez
  const IMAGEN_DE = (s) => s === "router" ? "router" : s === "admin" ? "admin" : s === "track-server" ? "servidor-pista"
    : /^player/.test(s) ? "jugador" : /^sim-/.test(s) ? "robot" : "emulador";

  let pasosCtl = null;
  let vivo = { datos: null, ultimo: 0, corriendo: false, errorAdmin: null, docker: null, dockerUltimo: 0 };

  // ================================================================ arranque
  async function arrancar() {
    try { await App.iniciar(); } catch (e) { /* App ya muestra el aviso */ }

    // Imágenes y medios
    const gif = $("#gifPortada"); gif.src = R("video/demo-stack.gif"); App.imagen(gif);
    $("#video").src = R("video/demo-stack.mp4");
    document.querySelectorAll("img[data-src]").forEach((im) => { im.src = R(im.dataset.src); App.imagen(im); });

    App.checklist("#checklist");
    App.checklist("#checklistFinal");

    dibujarMapa();
    dibujarVisores();
    dibujarGaleria();
    pintarLedsVacios();
    progreso.pintar();
    aisla.dibujar();
    if (window.DockerAnim) DockerAnim.iniciar({ alIr: irA });

    // Paneles de ejecución (salida en vivo dentro de la página)
    App.panelEjecucion("#panelStack", "stack_hub", Object.assign({
      titulo: "Levantar los 16 contenedores",
      botonTexto: "Levantar el laboratorio",
      queVaAPasar: "Docker enciende el router, la sala de control, la pista, los 3 jugadores, los 3 robots y los 7 ESP32 emulados. Si falta alguna imagen, la baja de Docker Hub (la primera vez, ~415 MB que ocupan ~2,4 GB). El progreso se dibuja arriba; al terminar, la app pasa sola al laboratorio en vivo.",
      queDeberiasVer: "Arriba, cada imagen \"lista\", las 3 redes creadas y los 16 contenedores en verde. Unos segundos después, la sala de control ve a todos en OK (los robots tardan un poco más en cargar).",
    }, progreso.ganchos()));
    App.panelEjecucion("#panelStackBuild", "stack", Object.assign({
      titulo: "Construir y levantar",
      botonTexto: "Construir las imágenes y levantar",
      queDeberiasVer: "Arriba, el paso \"k de n\" de cada Dockerfile (la de la pista y la de los robots son las largas). Al final, lo mismo que con el botón principal.",
    }, progreso.ganchos()));
    App.panelEjecucion("#panelParar", "parar", {
      titulo: "Detener los 16 contenedores",
      botonTexto: "Detener el laboratorio",
      queDeberiasVer: "Una línea \"Stopped\" por cada contenedor. El estado en vivo pasará a \"el admin no responde\".",
      alTerminar: () => { setTimeout(pararVivo, 4000); },
    });

    // Pruebas
    let salidaUnit = [];
    App.panelEjecucion("#panelUnitarias", "unitarias", {
      titulo: "Correr las 40 pruebas del protocolo",
      botonTexto: "Correr las pruebas del protocolo",
      queVaAPasar: "Corre las 40 pruebas unitarias de comun/protocolo.py en tu PC (no necesita Docker ni el laboratorio). Tarda un par de segundos.",
      queDeberiasVer: "Una línea por prueba terminada en \"ok\" y al final \"Ran 40 tests\" y \"OK\".",
      alLinea: (x) => { salidaUnit.push(x); },
      alEstado: (t) => { if (t.estado === "preparando" || t.estado === "instalando") salidaUnit = []; },
      alTerminar: () => { pintarUnitarias(salidaUnit); salidaUnit = []; },
    });
    pintarUnitarias(null);

    App.panelEjecucion("#panelAislamiento", "aislamiento", {
      titulo: "Probar el aislamiento entre VLAN",
      botonTexto: "Correr la prueba de aislamiento",
      queDeberiasVer: "Cada caso dibujado arriba como un paquete (verde llega, rojo bloqueado) y su línea aquí. Al final, 45 de 45 aprobados; el resultado se dibuja debajo.",
      alLinea: (x) => aisla.linea(x),
      alEstado: (t) => { if (t.estado === "preparando") aisla.reiniciar(); },
      alTerminar: () => pintarAislamiento(true),
    });
    pintarAislamiento(false);

    App.panelEjecucion("#panelDisponibilidad", "disponibilidad", {
      titulo: "Probar caídas y recuperación",
      botonTexto: "Correr la prueba de disponibilidad",
      queDeberiasVer: "Cómo se detiene cada contenedor, cuándo el admin lo marca CAIDO y cuándo vuelve a OK. Los LED de arriba se apagan y vuelven en vivo.",
      alEstado: (t) => { if (t.estado === "lanzada" && !vivo.corriendo) empezarVivo(); },
      alTerminar: () => pintarDisponibilidad(true),
    });
    pintarDisponibilidad(false);

    App.panelEjecucion("#panelRed", "red_base", {
      titulo: "Medir latencia y jitter (5 minutos)",
      botonTexto: "Medir 5 minutos",
      queDeberiasVer: "Un avance cada pocos segundos y al final la tabla por servicio. Se espera RTT menor a 1 ms, jitter menor a 0,1 ms, 0 % de pérdida y 100 % de disponibilidad.",
      alTerminar: () => pintarRed("base", true),
    });
    pintarRed("base", false);

    // Botones sueltos
    $("#btnVivo").onclick = empezarVivo;
    $("#btnVivoParar").onclick = pararVivo;
    $("#btnPreviewAbrir").onclick = () => App.accion("preview");
    $("#btnReadme").onclick = () => App.abrir("README.md");
    $("#btnAislaRepetir").onclick = () => aisla.repetir();
    $("#chipEstado").onclick = () => irA("El laboratorio en vivo");
    document.querySelectorAll("[data-ir]").forEach((b) => { b.onclick = () => irA(b.dataset.ir); });

    $("#plegableConceptos").addEventListener("toggle", function () {
      if (this.open && !this.dataset.cargado) {
        this.dataset.cargado = "1";
        App.markdown("#mdConceptos", "README.md", { desde: "## Qué es una VLAN", hasta: "## La idea general" });
      }
    });
    $("#plegableIframe").addEventListener("toggle", function () {
      const f = $("#iframeDashboard");
      if (this.open) f.src = DASHBOARD; else f.removeAttribute("src");
    });

    // Pasos (al final: mueve las secciones y llama a alCambiar con el paso guardado)
    pasosCtl = App.pasos("#pasos", { alCambiar: (i, sec) => alEntrarPaso(sec.dataset.titulo) });

    // Si se cierra la app, se cierra también el lector del estado en vivo.
    window.addEventListener("pagehide", () => {
      if (!vivo.corriendo) return;
      const token = (document.querySelector('meta[name="probar-token"]') || {}).content || "";
      try {
        fetch("/api/detener", { method: "POST", keepalive: true, headers: { "Content-Type": "application/json", "X-Token": token },
          body: JSON.stringify({ carpeta: App.carpeta, accion: "vivo", modo: "app" }) });
      } catch (e) { /* nada */ }
    });
  }

  function irA(titulo) {
    if (!pasosCtl) return;
    const i = pasosCtl.secciones.findIndex((s) => s.dataset.titulo === titulo);
    if (i >= 0) pasosCtl.ir(i);
  }

  function alEntrarPaso(titulo) {
    // La animación y la simulación dibujan sin parar: solo corren en su paso.
    if (window.DockerAnim) DockerAnim.visible(titulo === "Docker paso a paso");
    const f = $("#iframePreview");
    if (titulo === "Sin Docker") { if (!f.getAttribute("src")) f.src = R("preview.html"); }
    else if (f.getAttribute("src")) f.removeAttribute("src");
    // Al entrar al laboratorio en vivo (o a Docker paso a paso, para "la prueba", o a las pruebas, por los LED) se intenta mirar el
    // estado; si el laboratorio no está arriba, el lector se rinde solo a los 20 s.
    if (["El laboratorio en vivo", "Docker paso a paso", "Las pruebas"].includes(titulo) && !vivo.corriendo && !vivo.intentado) {
      vivo.intentado = true; empezarVivo();
    }
  }

  // ================================================================ progreso real al levantar
  // Lee lo que imprime `docker compose` (sin colores, BUILDKIT_PROGRESS=plain, lo pone el lanzador):
  //   " Image dathinel/zonas-esp32-robot:1.0 Pulling" / "Pulled" / "Building" / "Built"
  //   " 4abcf2066143 Downloading 12.58MB"  (una capa; sin el total, así que se suma lo bajado)
  //   "#20 [sim-spot stage-1 3/9] RUN pip install ..."  (paso k de n de un Dockerfile)
  //   " Network vlan1_gamer Creating" / "Created"
  //   " Container zonas-esp32-router-1 Creating" / "Created" / "Starting" / "Started" / "Running"
  const progreso = (() => {
    let P = null;
    let reloj = null;

    function nuevo() {
      return {
        activo: false, t0: 0, tFin: 0, docker: "esperando", hayImagenes: false, error: null, termino: null,
        imgs: Object.fromEntries(IMAGENES.map((i) => [i.k, { estado: "", frac: 0, modo: "" }])),
        capas: {}, redes: { vlan1_gamer: "", vlan2_robotica: "", vlan3_admin: "" },
        conts: Object.fromEntries(SERVICIOS.map(([s]) => [s, ""])),
        hitos: {}, salud: null,
      };
    }
    P = nuevo();

    const bytes = (s) => {
      const m = /([\d.]+)\s*([kKMG]?)B/.exec(s || "");
      if (!m) return 0;
      return parseFloat(m[1]) * ({ "": 1, k: 1e3, K: 1e3, M: 1e6, G: 1e9 }[m[2]] || 1);
    };
    const hito = (k) => { if (!P.hitos[k]) P.hitos[k] = Date.now(); };

    function empezar() {
      P = nuevo(); P.activo = true; P.t0 = Date.now(); P.docker = "comprobando";
      clearInterval(reloj); reloj = setInterval(pintar, 1000);
      pintar();
    }

    function linea(x) {
      if (!P.activo) empezar();
      let m;
      if ((m = /^\s*Image (\S+?)(?::[\w.-]+)?\s+(Pulling|Pulled|Building|Built|Skipped)/.exec(x))) {
        const k = (/zonas-esp32-([\w-]+)/.exec(m[1]) || [])[1];
        if (k && P.imgs[k]) {
          const im = P.imgs[k]; P.hayImagenes = true; hito("imagenes");
          if (m[2] === "Pulling") { im.estado = "bajando"; im.modo = "pull"; }
          else if (m[2] === "Building") { im.estado = "construyendo"; im.modo = "build"; }
          else { im.estado = "lista"; im.frac = 1; }
        }
      } else if ((m = /^\s*([0-9a-f]{12}) (Pulling fs layer|Waiting|Downloading|Verifying Checksum|Download complete|Extracting|Pull complete|Already exists)\s*(.*)$/.exec(x))) {
        P.hayImagenes = true; hito("imagenes");
        const c = P.capas[m[1]] || (P.capas[m[1]] = { b: 0, listo: false });
        if (m[2] === "Downloading") c.b = Math.max(c.b, bytes(m[3]));
        if (m[2] === "Pull complete" || m[2] === "Already exists") c.listo = true;
      } else if ((m = /^#\d+ \[([\w.-]+)(?: ([\w.-]+))? (\d+)\/(\d+)\]/.exec(x))) {
        // Paso k de n del Dockerfile de ese servicio (la etapa "mallas-softbank" del robot es aparte: se ignora)
        const k = IMAGEN_DE(m[1]);
        if ((!m[2] || m[2] === "stage-1") && P.imgs[k] && P.imgs[k].estado !== "lista") {
          P.hayImagenes = true; hito("imagenes");
          const im = P.imgs[k]; im.estado = "construyendo"; im.modo = "build";
          im.frac = Math.max(im.frac, (Number(m[3]) - 1) / Number(m[4]));
          im.paso = `${m[3]}/${m[4]}`;
        }
      } else if ((m = /^\s*Network (\S+)\s+(Creating|Created|Removing|Removed)/.exec(x))) {
        hito("redes");
        if (m[1] in P.redes) P.redes[m[1]] = m[2] === "Created" ? "creada" : m[2] === "Creating" ? "creando" : m[2].toLowerCase();
      } else if ((m = /^\s*Container zonas-esp32-([\w-]+?)-\d+\s+(\w+)/.exec(x))) {
        hito("contenedores");
        const s = m[1];
        if (s in P.conts) {
          const e = m[2];
          P.conts[s] = /^(Started|Running|Healthy)$/.test(e) ? "arriba" : /^(Created|Recreated)$/.test(e) ? "creado"
            : /^(Starting|Waiting)$/.test(e) ? "arrancando" : /^(Creating|Recreate)$/.test(e) ? "creando"
            : /^(Error)$/.test(e) ? "error" : P.conts[s];
        }
      } else if (/port is already allocated|Error response from daemon|error during connect|Pool overlaps/i.test(x)) {
        P.error = x.trim();
      }
      // Si ya empezaron las redes o los contenedores, las imágenes que no se mencionaron ya estaban.
      if (P.hitos.redes || P.hitos.contenedores) {
        for (const im of Object.values(P.imgs)) if (!im.estado) { im.estado = "ya estaba"; im.frac = 1; }
        for (const r of Object.keys(P.redes)) if (!P.redes[r] && P.hitos.contenedores) P.redes[r] = "ya estaba";
      }
      pintarPronto();
    }

    function estado(t) {
      if (t.estado === "preparando" && (!P.activo || P.termino)) empezar();
      if (t.estado === "lanzada" && P.docker === "comprobando") P.docker = "abierto";
      if (t.estado === "lanzada" && !P.activo) empezar();
      pintarPronto();
    }

    function terminar(t) {
      if (!P.activo) return;
      P.termino = t.estado; P.tFin = Date.now();
      if (t.estado === "terminada") {
        for (const im of Object.values(P.imgs)) if (im.estado !== "lista" && im.estado !== "ya estaba") { im.estado = im.estado ? "lista" : "ya estaba"; im.frac = 1; }
        for (const r of Object.keys(P.redes)) if (!P.redes[r] || P.redes[r] === "creando") P.redes[r] = P.redes[r] ? "creada" : "ya estaba";
        for (const s of Object.keys(P.conts)) if (P.conts[s] !== "error") P.conts[s] = "arriba";
        // Tiempos reales de esta subida, para "la prueba" de la escena 6 de la animación
        const seg = (a, b) => (a && b ? `${Math.max(0, Math.round((b - a) / 1000))} s` : "—");
        const h = P.hitos;
        if (window.DockerAnim) DockerAnim.datos({ subida: {
          imagenes: h.imagenes ? seg(h.imagenes, h.redes || h.contenedores || P.tFin) : "ya estaban",
          redes: seg(h.redes, h.contenedores || P.tFin), contenedores: seg(h.contenedores, P.tFin), total: seg(P.t0, P.tFin) } });
        P.salud = { desde: Date.now(), ok: 0, total: 8 };
        setTimeout(() => { if (!vivo.corriendo) empezarVivo(); }, 1500);
      } else {
        clearInterval(reloj);
      }
      pintar();
    }

    /** Lo llama el estado en vivo: cuántos servicios ve el admin en OK (fase final). */
    function salud(d) {
      if (!P.salud || !d) return;
      const sv = Object.values(d.servicios || {});
      P.salud.ok = sv.filter((s) => s.estado === "OK").length;
      P.salud.total = sv.length || 8;
      if (P.salud.ok >= P.salud.total && !P.salud.listo) {
        P.salud.listo = Date.now(); clearInterval(reloj);
        setTimeout(() => irA("El laboratorio en vivo"), 2500);
      }
      pintarPronto();
    }

    function fracciones() {
      const imgs = Object.values(P.imgs);
      const capas = Object.values(P.capas);
      const mbBajados = capas.reduce((a, c) => a + c.b, 0) / 1e6;
      // Imágenes: si se bajan, manda lo descargado (sobre ~415 MB); si se construyen, el paso k/n de cada Dockerfile.
      let fImg = imgs.reduce((a, im, i) => a + im.frac * IMAGENES[i].mb, 0) / MB_DESCARGA;
      if (imgs.some((im) => im.modo === "pull")) fImg = Math.max(fImg, Math.min(0.98, mbBajados / MB_DESCARGA));
      if (imgs.every((im) => im.estado === "lista" || im.estado === "ya estaba")) fImg = 1;
      const fRed = Object.values(P.redes).filter((r) => r === "creada" || r === "ya estaba").length / 3;
      const peso = { creando: 0.25, creado: 0.5, arrancando: 0.7, arriba: 1 };
      const fCont = Object.values(P.conts).reduce((a, e) => a + (peso[e] || 0), 0) / SERVICIOS.length;
      const fSalud = P.salud ? Math.min(1, P.salud.ok / (P.salud.total || 8)) : 0;
      // Pesos: las imágenes solo cuentan si hubo que bajarlas o construirlas.
      const w = P.hayImagenes ? { i: 70, r: 3, c: 17, s: 10 } : { i: 0, r: 10, c: 60, s: 30 };
      const total = (w.i * fImg + w.r * fRed + w.c * fCont + w.s * fSalud) / 100;
      return { fImg, fRed, fCont, fSalud, total, mbBajados };
    }

    let pendiente = false;
    function pintarPronto() { if (!pendiente) { pendiente = true; requestAnimationFrame(() => { pendiente = false; pintar(); }); } }

    function pintar() {
      const f = fracciones();
      const ahora = P.tFin && (!P.salud || P.salud.listo) ? (P.salud && P.salud.listo ? P.salud.listo : P.tFin) : Date.now();
      const seg = P.t0 ? (ahora - P.t0) / 1000 : 0;
      const barra = $("#progBarra");
      barra.style.width = `${Math.round((P.salud && P.salud.listo ? 1 : f.total) * 100)}%`;
      barra.className = P.error || P.termino === "error" ? "mal" : P.salud && P.salud.listo ? "ok" : "";
      // Título: la fase actual en palabras
      let titulo = 'Todavía no has pulsado "Levantar el laboratorio"';
      if (P.activo) {
        if (P.termino === "error") titulo = "No se pudo levantar: mira el resumen del error abajo";
        else if (P.termino === "detenida") titulo = "Detenido";
        else if (P.salud && P.salud.listo) titulo = "Listo: los 16 contenedores arriba y la sala de control ve a todos en OK";
        else if (P.salud) titulo = `Contenedores arriba. Esperando a que la sala de control vea a todos: ${P.salud.ok} de ${P.salud.total} en OK`;
        else if (P.hitos.contenedores) titulo = `Arrancando contenedores: ${Object.values(P.conts).filter((e) => e === "arriba").length} de 16`;
        else if (P.hitos.redes) titulo = "Creando las 3 redes (VLAN)";
        else if (P.hayImagenes) {
          const bajando = Object.entries(P.imgs).filter(([, im]) => im.estado === "bajando" || im.estado === "construyendo").map(([k]) => k);
          titulo = Object.values(P.imgs).some((im) => im.modo === "build")
            ? `Construyendo imágenes: ${bajando.join(", ") || "…"}`
            : `Bajando imágenes de Docker Hub: ${num(f.mbBajados, 0)} de ~${MB_DESCARGA} MB`;
        } else if (P.docker === "comprobando") titulo = "Comprobando que Docker Desktop esté abierto…";
        else titulo = "Docker respondió: revisando qué imágenes faltan…";
      }
      $("#progTitulo").textContent = titulo;
      const tipico = P.hayImagenes ? (Object.values(P.imgs).some((im) => im.modo === "build") ? "10-20 min" : "2-6 min") : "~30 s";
      $("#progReloj").innerHTML = P.activo ? `<b>${mmss(seg)}</b><span>típico: ${tipico}</span>` : `<span>típico: ~30 s · la primera vez 2-6 min</span>`;

      // Fases
      const chip = (nombre, est, extra, color) => {
        const cls = /lista|ya estaba|creada|arriba/.test(est) ? "ok" : /error/.test(est) ? "mal" : est ? "trabaja" : "";
        // title: el texto completo, porque en pantallas de 1366 px la segunda línea se corta con "…"
        const completo = `${nombre}: ${est || "pendiente"}${extra ? " · " + extra : ""}`;
        return `<div class="c11-chipf ${cls}" title="${esc(completo)}" ${color ? `style="--zc:${color}"` : ""}><i></i><b>${esc(nombre)}</b><span>${esc(est || "pendiente")}${extra ? " · " + esc(extra) : ""}</span></div>`;
      };
      const imgs = IMAGENES.map((i) => {
        const im = P.imgs[i.k];
        const extra = im.estado === "construyendo" && im.paso ? `paso ${im.paso}` : im.estado === "bajando" ? `~${i.mb} MB` : im.estado ? i.disco : `${i.mb} MB / ${i.disco}`;
        return chip(i.k, im.estado, extra);
      }).join("");
      const redes = Object.entries(P.redes).map(([n, e], i) => chip(n, e, ["192.168.10.0/24", "192.168.20.0/24", "192.168.30.0/24"][i], ZONA[i + 1].color)).join("");
      const conts = SERVICIOS.map(([s, v]) => chip(s, P.conts[s], "", ZONA[v].color)).join("");
      const fase = (n, titulo, frac, contenido, nota) => `<div class="c11-fase ${frac >= 1 ? "hecha" : frac > 0 ? "en-curso" : ""}">
          <div class="c11-fase-cab"><span class="c11-fase-num">${frac >= 1 ? "✓" : n}</span><b>${titulo}</b><small>${esc(nota || "")}</small>
            <div class="c11-barra"><i style="width:${Math.round(frac * 100)}%"></i></div></div>
          <div class="c11-fase-cuerpo">${contenido}</div></div>`;
      const nOk = P.salud ? `${P.salud.ok} de ${P.salud.total} servicios en OK` : "";
      $("#progFases").innerHTML =
        fase(1, "Imágenes (6)", f.fImg, `<div class="c11-chips seis">${imgs}</div>`,
          P.hayImagenes && Object.values(P.imgs).some((im) => im.modo === "pull") ? `bajados ${num(f.mbBajados, 0)} de ~${MB_DESCARGA} MB` : (P.activo && (P.hitos.redes || P.hitos.contenedores) && !P.hayImagenes ? "ya estaban todas en el PC" : "")) +
        fase(2, "Redes (3)", f.fRed, `<div class="c11-chips tres">${redes}</div>`) +
        fase(3, "Contenedores (16)", f.fCont, `<div class="c11-chips dieciseis">${conts}</div>`, "el router arranca primero: los demás lo esperan") +
        fase(4, "La sala de control ve a todos", P.salud && P.salud.listo ? 1 : f.fSalud, `<p class="c11-nota">${P.salud ? esc(nOk) + (P.salud.listo ? " · ¡listo!" : " · los robots tardan unos segundos en cargar sus modelos") : "Cuando terminen los contenedores, la app lee el estado del admin (los 6 LED)."}</p>`);
      const nota = $("#progNota");
      if (P.activo && !P.error && !(P.salud && P.salud.listo)) {
        nota.textContent = P.termino === "error" ? "Docker no terminó bien: abajo está el resumen del error y sus últimas líneas."
          : "Cada cuadro cambia cuando docker compose lo anuncia (la salida completa está abajo, en \"Lo que dice el programa\").";
        nota.className = "c11-nota";
      }
      if (P.error) { nota.textContent = "Docker avisó: " + P.error; nota.className = "c11-nota c11-mal"; }
      else if (P.salud && P.salud.listo) { nota.innerHTML = 'Todo arriba. <button class="c11-btn primario" id="btnIrVivo">Ver el laboratorio en vivo →</button>'; nota.className = "c11-nota"; const b = $("#btnIrVivo"); if (b) b.onclick = () => irA("El laboratorio en vivo"); }
    }

    function ganchos() {
      return { alLinea: (x, tipo) => { if (tipo !== "in") linea(x); }, alEstado: estado, alTerminar: terminar };
    }

    return { ganchos, pintar, salud, get estado() { return P; } };
  })();

  // ================================================================ mapa
  function dibujarMapa() {
    let s = `<svg viewBox="0 0 900 560" role="img" aria-label="Mapa de las tres VLAN con el router">
      <defs>
        <marker id="m11ok" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 z" fill="#4caf7d"/></marker>
      </defs>`;
    const zona = (x, y, w, h, z, titulo) =>
      `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="12" fill="${ZONA[z].color}10" stroke="${ZONA[z].color}" stroke-opacity=".55" stroke-width="1.4"/>
       <text x="${x + 12}" y="${y + 20}" fill="${ZONA[z].color}" font-family="IBM Plex Mono" font-size="12" font-weight="600">${titulo}</text>
       <text x="${x + w - 12}" y="${y + 20}" fill="#8b929b" font-family="IBM Plex Mono" font-size="11" text-anchor="end">${ZONA[z].red}</text>`;
    s += zona(20, 20, 400, 245, 1, "VLAN 1 · ZONA GAMER");
    s += zona(480, 20, 400, 245, 2, "VLAN 2 · ZONA ROBÓTICA");
    s += zona(250, 405, 420, 135, 3, "VLAN 3 · ADMINISTRACIÓN");
    s += `<g stroke-width="2.2" fill="none">
      <path d="M220 265 C 230 300, 330 322, 390 322" stroke="#4caf7d" marker-end="url(#m11ok)" marker-start="url(#m11ok)"/>
      <path d="M680 265 C 670 300, 570 322, 510 322" stroke="#4caf7d" marker-end="url(#m11ok)" marker-start="url(#m11ok)"/>
      <path d="M450 340 L 450 405" stroke="#4caf7d" marker-end="url(#m11ok)" marker-start="url(#m11ok)"/>
      <path d="M420 150 L 480 150" stroke="#d9534f" stroke-dasharray="6 5"/>
    </g>
    <g font-family="IBM Plex Mono" text-anchor="middle">
      <circle cx="450" cy="150" r="13" fill="#2a1414" stroke="#d9534f"/><text x="450" y="155" fill="#ff8a86" font-size="14" font-weight="700">✕</text>
      <text x="450" y="182" fill="#d9534f" font-size="10">DROP</text>
      <text x="300" y="300" fill="#4caf7d" font-size="10">.254</text><text x="600" y="300" fill="#4caf7d" font-size="10">.254</text><text x="472" y="378" fill="#4caf7d" font-size="10">.254</text>
    </g>`;
    s += `<g stroke="#8b929b" stroke-dasharray="2 4" stroke-width="1.3">`;
    for (const n of NODOS.filter((n) => n.manda)) {
      const d = NODOS.find((m) => m.id === n.manda);
      s += `<line x1="${n.x}" y1="${n.y - 14}" x2="${d.x}" y2="${d.y + 16}"/>`;
    }
    s += `<line x1="545" y1="470" x2="460" y2="470"/></g>`;
    for (const n of NODOS) {
      const c = ZONA[n.vlan].color, h = n.router ? 38 : 32;
      const x = n.x - n.w / 2, y = n.y - h / 2;
      s += `<g class="nodo" data-id="${n.id}" tabindex="0" role="button" aria-label="${esc(n.id)}">
        <rect x="${x}" y="${y}" width="${n.w}" height="${h}" rx="${n.router ? 19 : 6}" fill="${n.emu ? "#0f1316" : c + "22"}" stroke="${c}" stroke-width="1.4" ${n.emu ? 'stroke-dasharray="4 3"' : ""}/>
        <text x="${n.x - 4}" y="${n.y + (n.emu ? 4 : 1)}" fill="#e7e9ec" font-family="${n.emu ? "IBM Plex Mono" : "Space Grotesk"}" font-size="${n.emu ? 11 : 13}" font-weight="${n.emu ? 400 : 600}" text-anchor="middle">${esc(n.router ? "router" : n.id)}</text>
        ${n.emu ? "" : `<text x="${n.x - 4}" y="${n.y + 13}" fill="#8b929b" font-family="IBM Plex Mono" font-size="9" text-anchor="middle">${n.router ? "FRR + iptables" : "." + n.ip.split(".").pop()}</text>`}
        <circle class="luz" cx="${x + n.w - 9}" cy="${y + 9}" r="4.5" fill="#3a4048"/>
      </g>`;
    }
    s += `<text x="20" y="300" fill="#8b929b" font-family="IBM Plex Mono" font-size="10">cajas punteadas = ESP32 emulados</text>`;
    s += "</svg>";
    const mapa = $("#mapa");
    mapa.innerHTML = s;
    mapa.querySelectorAll(".nodo").forEach((g) => {
      const elegir = () => {
        mapa.querySelectorAll(".nodo.sel").forEach((x) => x.classList.remove("sel"));
        g.classList.add("sel");
        mostrarFicha(g.dataset.id);
      };
      g.addEventListener("click", elegir);
      g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); elegir(); } });
    });
  }

  function contenedorDe(id) {
    const servicio = id === "esclava" ? "esclava-emulada" : id;
    return (vivo.docker && Date.now() - vivo.dockerUltimo < 10000 ? vivo.docker.contenedores : []).find((c) => c.servicio === servicio);
  }

  function estadoDeNodo(n) {
    // Si Docker dice que el contenedor está detenido, manda eso (aunque el admin no responda).
    const c = contenedorDe(n.id);
    if (c && c.estado !== "running") return "CAIDO";
    const d = vivo.datos;
    if (!d || Date.now() - vivo.ultimo > 6000) return null;
    if (n.id === "admin") return "OK";
    const s = d.servicios[n.id];
    if (s) return s.estado;
    const origen = n.servicio === "esclava-emulada" ? "esclava" : n.id;
    const l = (d.latidos || []).find((x) => x.origen === origen || x.origen === n.id);
    if (l) return l.edad != null && l.edad < 3 ? "OK" : "CAIDO";
    return null;
  }

  function colorEstado(e) { return e === "OK" ? "#4caf7d" : e === "LENTO" ? "#e8b930" : e === "CAIDO" ? "#d9534f" : "#3a4048"; }

  function pintarMapaVivo() {
    document.querySelectorAll("#mapa .nodo").forEach((g) => {
      const n = NODOS.find((m) => m.id === g.dataset.id);
      g.querySelector(".luz").setAttribute("fill", colorEstado(estadoDeNodo(n)));
    });
    const sel = document.querySelector("#mapa .nodo.sel");
    if (sel) mostrarFicha(sel.dataset.id);
  }

  function mostrarFicha(id) {
    const n = NODOS.find((m) => m.id === id);
    if (!n) return;
    const z = ZONA[n.vlan];
    const e = estadoDeNodo(n);
    const s = vivo.datos && vivo.datos.servicios[n.id];
    const c = contenedorDe(n.id);
    let html = `<p class="c11-etiqueta ${z.clase}">${esc(z.nombre)}</p>
      <h4>${esc(n.router ? "router" : n.id)} ${e ? `<span class="c11-insignia ${e}">${e}</span>` : ""}</h4>
      <p class="c11-nota">${esc(n.que)}</p><dl>
      <dt>IP</dt><dd class="c11-mono">${esc(n.ip)}</dd>
      <dt>Tipo</dt><dd>${n.emu ? "ESP32 emulado (contenedor del emulador)" : n.router ? "Router (contenedor Alpine)" : "Contenedor"}</dd>`;
    if (c) html += `<dt>Docker</dt><dd class="c11-mono">${esc(c.texto)}</dd><dt>Imagen</dt><dd class="c11-mono">${esc((c.imagen || "").replace(/^.*\//, ""))}</dd>`;
    if (n.esp) html += `<dt>Lo maneja</dt><dd class="c11-mono">${esc(n.esp)}</dd>`;
    if (n.manda) html += `<dt>Manda a</dt><dd class="c11-mono">${esc(n.manda)}</dd>`;
    if (n.led) html += `<dt>Su LED</dt><dd class="c11-mono">${esc(n.led)} de la esclava</dd>`;
    if (s && s.prom != null) html += `<dt>RTT ahora</dt><dd class="c11-mono">${num(s.rtt, 3)} ms (prom. ${num(s.prom, 3)})</dd>`;
    if (n.puerto) html += `<dt>Visor</dt><dd class="c11-mono">127.0.0.1:${n.puerto}</dd>`;
    html += "</dl>";
    if (n.visor) html += `<div class="c11-botonera"><button class="c11-btn" data-visor="${n.visor}">Abrir su visor</button></div>`;
    const f = $("#ficha");
    f.innerHTML = html;
    const b = f.querySelector("[data-visor]");
    if (b) b.onclick = () => App.accion(b.dataset.visor);
  }

  // ================================================================ visores y galería
  function dibujarVisores() {
    const v = [
      ["dashboard", "Dashboard del admin", "127.0.0.1:8180", "img/dashboard-stack.png"],
      ["pista", "La carrera", "127.0.0.1:8010", "img/pista-carrera.png"],
      ["spot", "Spot (Rex)", "127.0.0.1:8011", "img/robot-spot.png"],
      ["pepper", "Pepper", "127.0.0.1:8012", "img/robot-pepper.png"],
      ["nao", "NAO", "127.0.0.1:8013", "img/robot-nao.png"],
    ];
    const c = $("#visores");
    c.innerHTML = v.map(([id, n, p, img]) =>
      `<button class="c11-visor" data-accion="${id}" title="Abrir ${esc(n)} en otra pestaña">
        <img src="${R(img)}" alt="" loading="lazy"><div><b>${esc(n)}</b><span>${esc(p)} ↗</span></div></button>`).join("");
    c.querySelectorAll("[data-accion]").forEach((b) => { b.onclick = () => App.accion(b.dataset.accion); });
  }

  function dibujarGaleria() {
    const g = [
      ["img/dashboard-stack.png", "El dashboard del admin con los 16 contenedores arriba: los 6 servicios en OK a través del router."],
      ["img/pista-carrera.png", "La carrera: 3 jugadores manejados por sus ESP32 emulados y 3 autónomos."],
      ["img/pista-failsafe.png", "Failsafe: sin mando durante 1 s, el carro del jugador frena."],
      ["img/robot-spot.png", "El Spot (Rex) siguiendo los 3 ángulos de su ESP32."],
      ["img/robot-pepper-mallas.png", "Pepper con las mallas de SoftBank (solo en local; la imagen publicada lo dibuja como esqueleto)."],
      ["img/robot-nao-mallas.png", "NAO con sus mallas, copiando hombro, codo y cabeza."],
      ["pruebas/resultados/red_base_resumen.png", "RTT y jitter de cada servicio en el escenario base (5 min)."],
      ["pruebas/resultados/red_retardo_rtt_tiempo.png", "Con 30 ± 10 ms de retardo en la VLAN 2: los robots suben a unos 60 ms y la VLAN 1 no se mueve."],
      ["img/preview-ping-bloqueado.png", "En la simulación del navegador: el ping de player-1 a sim-nao muere en el router; el del admin vuelve con ttl=63."],
      ["img/preview-falla-led.png", "Simulación con la zona gamer degradada (LED parpadeando) y sim-pepper detenido (LED apagado)."],
    ];
    const c = $("#galeria");
    c.innerHTML = g.map(([src, t]) => `<figure><img src="${R(src)}" alt="${esc(t)}" loading="lazy"><figcaption>${esc(t)}</figcaption></figure>`).join("");
    App.imagen(c);
  }

  // ================================================================ estado en vivo
  function ledsHtml(d) {
    return (d && d.leds.length ? d.leds : Object.keys(GPIO)).map((n) => {
      const e = d ? ((d.servicios[n] || {}).estado || "") : "";
      return `<div class="c11-led ${e}" title="${esc(n)}: ${esc(e)}"><div class="bombillo"></div><b>${esc(n)}</b><span>GPIO ${GPIO[n] ?? "?"}${d ? " · " + esc(e || "—") : ""}</span></div>`;
    }).join("");
  }
  function pintarLedsVacios() { $("#leds").innerHTML = ledsHtml(null); $("#ledsDisp").innerHTML = ledsHtml(null); }

  async function empezarVivo() {
    if (vivo.corriendo) return;
    vivo.corriendo = true;
    $("#btnVivo").disabled = true; $("#btnVivoParar").disabled = false;
    textoVivo("Conectando con la sala de control y con Docker…", "");
    let lectura = null, lecturaDocker = null;
    const lanzar = () => App.accion("vivo", {
      alLinea: (x) => {
        // Cada lectura llega en varias líneas cortas (el lanzador corta las de más de 2000
        // caracteres): GEN abre una lectura nueva, SVC y LAT la completan y OK la dibuja.
        // Las de Docker igual: CONT (una por contenedor), IMGS, REDES y DOCKER_OK.
        try {
          if (x.startsWith("VIVO_GEN ")) { lectura = Object.assign(JSON.parse(x.slice(9)), { servicios: {}, latidos: [] }); return; }
          if (x.startsWith("VIVO_SVC ") && lectura) { const s = JSON.parse(x.slice(9)); lectura.servicios[s.nombre] = s; return; }
          if (x.startsWith("VIVO_LAT ") && lectura) { lectura.latidos = JSON.parse(x.slice(9)); return; }
          if (x.startsWith("VIVO_CONT ")) { (lecturaDocker = lecturaDocker || { contenedores: [] }).contenedores.push(JSON.parse(x.slice(10))); return; }
          if (x.startsWith("VIVO_IMGS ")) { (lecturaDocker = lecturaDocker || { contenedores: [] }).imagenes = JSON.parse(x.slice(10)); return; }
          if (x.startsWith("VIVO_REDES ")) { (lecturaDocker = lecturaDocker || { contenedores: [] }).redes = JSON.parse(x.slice(11)); return; }
        } catch (e) { lectura = null; lecturaDocker = null; return; /* línea dañada: se espera la lectura siguiente */ }
        if (x === "VIVO_OK" && lectura) { recibirVivo(lectura); lectura = null; }
        else if (x === "VIVO_DOCKER_OK") { recibirDocker(lecturaDocker || { contenedores: [] }); lecturaDocker = null; }
        else if (x.startsWith("SIN_DOCKER")) { recibirDocker(null); }
        else if (x.startsWith("SIN_ADMIN")) { vivo.datos = null; pintarSinAdmin(); }
        else if (x.startsWith("FIN ")) { textoVivo(x.slice(4), vivo.ultimo ? "" : "mal"); }
      },
      alEstado: (t) => {
        if (t.estado === "instalando" || t.estado === "preparando") textoVivo("Preparando el lector del estado…", "");
        if (t.estado === "lanzada" && !vivo.datos) textoVivo("Conectado: esperando la primera lectura de la sala de control…", "");
      },
    });
    try {
      const t = await lanzar().catch(async (e) => {
        // Si quedó uno corriendo de antes (se recargó la página), se cierra y se vuelve a lanzar.
        if (/en marcha/i.test(e.message)) { await App.detener("vivo").catch(() => {}); await new Promise((r) => setTimeout(r, 1200)); return lanzar(); }
        throw e;
      });
      if (t && t.estado === "error") textoVivo("No se pudo leer el estado: " + (t.mensaje || "error"), "mal");
    } catch (e) {
      textoVivo("No se pudo leer el estado: " + e.message, "mal");
    } finally {
      vivo.corriendo = false;
      $("#btnVivo").disabled = false; $("#btnVivoParar").disabled = true;
      $("#btnVivo").textContent = "Volver a mirar";
      if (Date.now() - vivo.ultimo > 3000) { vivo.datos = null; pintarMapaVivo(); chip(null); }
    }
  }

  function pararVivo() {
    if (!vivo.corriendo) return;
    App.detener("vivo").catch(() => {});
    textoVivo("Dejaste de mirar. Pulsa \"Volver a mirar\" para seguir.", "");
  }

  function textoVivo(t, clase) {
    const e = $("#vivoTexto"); e.textContent = t; e.className = "c11-vivo-txt " + (clase || "");
  }

  function chip(d) {
    const c = $("#chipEstado"), t = $("#chipTexto");
    c.classList.remove("ok", "lento", "caido");
    if (!d) {
      const corriendo = vivo.docker ? vivo.docker.contenedores.filter((x) => x.estado === "running").length : null;
      t.textContent = vivo.errorAdmin ? (corriendo ? `Laboratorio: ${corriendo} contenedores, el admin no responde` : "Laboratorio: detenido") : "Laboratorio: sin mirar";
      if (vivo.errorAdmin) c.classList.add("caido");
      return;
    }
    const leds = d.leds.map((n) => (d.servicios[n] || {}).estado);
    const ok = leds.filter((e) => e === "OK").length;
    const caidos = leds.filter((e) => e === "CAIDO").length;
    c.classList.add(caidos ? "caido" : ok === leds.length ? "ok" : "lento");
    t.textContent = `Laboratorio en vivo: ${ok} de ${leds.length} en OK`;
  }

  function pintarSinAdmin() {
    vivo.errorAdmin = true;
    textoVivo("La sala de control no responde en 127.0.0.1:8180. ¿Está levantado el laboratorio? (paso \"Levantar el laboratorio\")", "mal");
    document.querySelectorAll("#leds .c11-led, #ledsDisp .c11-led").forEach((l) => { l.className = "c11-led"; });
    chip(null); pintarMapaVivo();
  }

  function duracion(s) {
    if (s == null) return "—";
    s = Math.round(s);
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
    return h ? `${h} h ${m} min` : m ? `${m} min ${s % 60} s` : `${s} s`;
  }

  function recibirVivo(d) {
    vivo.datos = d; vivo.ultimo = Date.now(); vivo.errorAdmin = false;
    $("#leds").innerHTML = ledsHtml(d);
    $("#ledsDisp").innerHTML = ledsHtml(d);
    // Tabla de lo que mide el admin
    const maxRtt = Math.max(0.5, ...Object.values(d.servicios).map((s) => s.p95 || 0));
    const filas = ORDEN_TABLA.filter((n) => d.servicios[n]).concat(Object.keys(d.servicios).filter((n) => !ORDEN_TABLA.includes(n)));
    $("#tablaVivo tbody").innerHTML = filas.map((n) => {
      const s = d.servicios[n], z = ZONA[s.vlan] || ZONA[0];
      const ancho = Math.min(100, ((s.rtt || 0) / maxRtt) * 100);
      return `<tr>
        <td><b>${esc(n)}</b></td>
        <td><span class="${n === "router" ? "" : z.clase} c11-mono" style="font-size:.72rem">${n === "router" ? "las 3" : s.vlan ? "VLAN " + s.vlan : "—"}</span></td>
        <td><span class="c11-insignia ${esc(s.estado)}">${esc(s.estado || "—")}</span></td>
        <td class="num"><div style="display:flex;align-items:center;gap:.45rem;justify-content:flex-end"><div class="c11-barra" style="width:60px"><i style="width:${ancho}%"></i></div>${num(s.rtt, 3)} ms</div></td>
        <td class="num">${num(s.p95, 3)} ms</td>
        <td class="num">${num(s.jit, 3)} ms</td>
        <td class="num">${num(s.disp, 1)} %</td>
        <td class="c11-nota" style="font-size:.74rem">${esc(s.motivo || "")}</td></tr>`;
    }).join("");
    // Latidos de los ESP32
    const lat = (d.latidos || []);
    $("#latidos").innerHTML = lat.length ? lat.map((l) => {
      const ok = l.edad != null && l.edad < 3;
      return `<span class="c11-latido ${ok ? "vivo" : ""}" title="${esc(l.ip)} · hace ${num(l.edad, 1)} s · ${l.perdidos ?? 0} perdidos">${ok ? "♥" : "·"} ${esc(l.origen)}</span>`;
    }).join("") : '<span class="c11-nota">Ningún ESP32 ha latido todavía.</span>';
    const nOk = lat.filter((l) => l.edad != null && l.edad < 3).length;
    textoVivo(`En vivo · actualizado ${new Date().toLocaleTimeString("es-CO")} · el admin lleva ${duracion(d.en_marcha_s)} en marcha · MQTT ${d.mqtt ? "conectado" : "sin conexión"} · ${nOk} de ${lat.length} ESP32 latiendo`, "ok");
    chip(d);
    pintarMapaVivo();
    progreso.salud(d);
  }

  // ---------------------------------------------------------------- contenedores (como Docker Desktop)
  let filtroRed = "todas";
  function recibirDocker(d) {
    vivo.docker = d; vivo.dockerUltimo = Date.now();
    if (window.DockerAnim && d) DockerAnim.datos({ contenedores: d.contenedores, ...(d.imagenes ? { imagenes: d.imagenes } : {}), ...(d.redes ? { redes: d.redes } : {}) });
    if (d && d.imagenes) vivo.imagenes = d.imagenes;
    pintarContenedores();
    if (!vivo.datos) { chip(null); pintarMapaVivo(); }
  }

  function pintarContenedores() {
    const d = vivo.docker;
    const tb = $("#tablaCont tbody");
    if (!d) {
      $("#contTitulo").textContent = "Docker no responde: ¿está abierto Docker Desktop?";
      tb.innerHTML = '<tr><td colspan="6" class="c11-nota">Abre Docker Desktop y espera a que diga "Engine running".</td></tr>';
      return;
    }
    const cs = d.contenedores;
    const corriendo = cs.filter((c) => c.estado === "running").length;
    $("#contTitulo").textContent = cs.length ? `zonas-esp32 · ${cs.length} contenedores · ${corriendo} en marcha` : "No hay contenedores del laboratorio: levántalo primero";
    const filtros = [["todas", "Todos"], ["1", "VLAN 1"], ["2", "VLAN 2"], ["3", "VLAN 3"], ["0", "router"]];
    $("#contFiltros").innerHTML = filtros.map(([k, n]) => `<button data-f="${k}" class="${filtroRed === k ? "activa" : ""}">${n}</button>`).join("");
    $("#contFiltros").querySelectorAll("button").forEach((b) => { b.onclick = () => { filtroRed = b.dataset.f; pintarContenedores(); }; });
    const orden = SERVICIOS.map(([s]) => s);
    const filas = cs.slice().sort((a, b) => orden.indexOf(a.servicio) - orden.indexOf(b.servicio))
      .filter((c) => filtroRed === "todas" || String(RED_DE[c.servicio]) === filtroRed);
    tb.innerHTML = filas.length ? filas.map((c) => {
      const v = RED_DE[c.servicio] ?? 0, z = ZONA[v];
      const cls = c.estado === "running" ? (c.salud === "unhealthy" ? "lento" : "ok") : c.estado === "restarting" || c.salud === "starting" ? "lento" : "parado";
      const puertos = (c.puertos || []).map((p) => {
        const m = /^(\d+)->(\d+)\/(tcp|udp)$/.exec(p);
        const web = m && m[3] === "tcp" && /^(8180|801[0-3])$/.test(m[1]);
        return web ? `<button class="c11-puerto" data-url="http://127.0.0.1:${m[1]}/" title="Abrir en el navegador">${esc(m[1])}:${esc(m[2])} ↗</button>`
          : `<span class="c11-puerto">${esc(p.replace("->", ":"))}</span>`;
      }).join(" ");
      return `<tr><td><span class="c11-punto-est ${cls}"></span></td>
        <td><b>${esc(c.servicio)}</b><br><span class="c11-nota c11-mono" style="font-size:.66rem">${esc(c.nombre)}</span></td>
        <td><span class="${z.clase} c11-mono" style="font-size:.72rem">${v ? "VLAN " + v : "las 3"}</span></td>
        <td class="c11-mono" style="font-size:.74rem">${esc((c.imagen || "").replace(/^.*\//, ""))}</td>
        <td style="font-size:.78rem">${esc(c.texto)}</td>
        <td>${puertos || '<span class="c11-nota">—</span>'}</td></tr>`;
    }).join("") : '<tr><td colspan="6" class="c11-nota">Ninguno en este filtro.</td></tr>';
    tb.querySelectorAll("[data-url]").forEach((b) => { b.onclick = () => App.abrir(b.dataset.url); });
    const imgs = vivo.imagenes || d.imagenes;
    $("#contImgs").innerHTML = imgs && imgs.length ? `<b>Imágenes en tu PC:</b> ${imgs.map((i) => `<span class="c11-mono">${esc(i.repo.replace(/^.*zonas-esp32-/, ""))}</span> ${esc(i.tamano)}`).join(" · ")}` : "";
  }

  // ================================================================ aislamiento dibujado caso por caso
  const aisla = (() => {
    const POS = {
      "track-server": [80, 70], "player-1": [80, 102], "player-2": [80, 134], "player-3": [80, 166],
      "ctrl-1": [190, 86], "ctrl-2": [190, 118], "ctrl-3": [190, 150],
      "sim-spot": [450, 86], "sim-pepper": [450, 118], "sim-nao": [450, 150],
      "ctrl-spot": [560, 86], "ctrl-pepper": [560, 118], "ctrl-nao": [560, 150],
      admin: [270, 285], esclava: [370, 285],
    };
    const RT = [320, 150], BORDE = { g: [240, 120], r: [400, 120], a: [320, 245] };
    const PUERTA = { g: [135, 214], r: [505, 214] };
    const zonaDe = (n) => /^(player|track|ctrl-\d)/.test(n) ? "g" : /^(sim-|ctrl-(spot|pepper|nao))/.test(n) ? "r" : /^admin|^esclava/.test(n) ? "a" : null;
    let svg = null, cola = [], ocupado = false, cuentas = { bloq: 0, pasan: 0, drop: 0 }, gen = 0;

    function el(tag, attrs, padre) {
      const e = document.createElementNS("http://www.w3.org/2000/svg", tag);
      for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
      (padre || svg).appendChild(e); return e;
    }
    function t(x, y, s, attrs) { const e = el("text", Object.assign({ x, y, fill: "#e7e9ec", "font-family": "IBM Plex Mono", "font-size": 10 }, attrs || {})); e.textContent = s; return e; }

    function dibujar() {
      svg = $("#aislaSvg");
      svg.innerHTML = "";
      el("rect", { x: 20, y: 30, width: 220, height: 160, rx: 10, fill: "#3fbf8f12", stroke: "#3fbf8f" }); t(30, 46, "VLAN 1 · gamer", { fill: "#3fbf8f", "font-weight": 600 });
      el("rect", { x: 400, y: 30, width: 220, height: 160, rx: 10, fill: "#f0913a12", stroke: "#f0913a" }); t(410, 46, "VLAN 2 · robótica", { fill: "#f0913a", "font-weight": 600 });
      el("rect", { x: 210, y: 245, width: 220, height: 70, rx: 10, fill: "#a77be812", stroke: "#a77be8" }); t(220, 261, "VLAN 3 · admin", { fill: "#a77be8", "font-weight": 600 });
      for (const [a, b] of [[BORDE.g, RT], [BORDE.r, RT], [BORDE.a, RT]]) el("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke: "#4f8fce", "stroke-width": 2 });
      for (const k of ["g", "r"]) {
        const [x, y] = PUERTA[k];
        el("rect", { x: x - 42, y: y - 11, width: 84, height: 22, rx: 5, fill: "rgba(36,150,237,.1)", stroke: "#2496ed", "stroke-dasharray": "3 3" });
        t(x, y + 4, "puerta .1 Docker", { "text-anchor": "middle", fill: "#2496ed", "font-size": 9 });
      }
      el("circle", { cx: RT[0], cy: RT[1], r: 20, fill: "#13263a", stroke: "#4f8fce", "stroke-width": 2, id: "aislaRouter" });
      t(RT[0], RT[1] + 4, "router", { "text-anchor": "middle", fill: "#4f8fce", "font-size": 10, "font-weight": 600 });
      for (const [n, [x, y]] of Object.entries(POS)) {
        const z = zonaDe(n), c = z === "g" ? "#3fbf8f" : z === "r" ? "#f0913a" : "#a77be8";
        el("rect", { x: x - 46, y: y - 11, width: 92, height: 22, rx: 5, fill: c + "22", stroke: c, "data-n": n });
        t(x, y + 4, n, { "text-anchor": "middle", "font-size": 9.5 });
      }
      pintarCuentas();
    }

    function pintarCuentas() {
      $("#aislaBloq").textContent = cuentas.bloq; $("#aislaPasan").textContent = cuentas.pasan; $("#aislaDrop").textContent = cuentas.drop;
    }

    function reiniciar() { gen++; cola = []; ocupado = false; cuentas = { bloq: 0, pasan: 0, drop: 0 }; if (svg) dibujar(); $("#aislaCaso").textContent = "esperando el primer caso…"; }

    const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
    function mover(puntos, color, ms, g0) {
      return new Promise((res) => {
        const p = el("circle", { r: 6, fill: color, stroke: "#fff", "stroke-width": 1.2 });
        const largos = []; let total = 0;
        for (let i = 1; i < puntos.length; i++) { const l = Math.hypot(puntos[i][0] - puntos[i - 1][0], puntos[i][1] - puntos[i - 1][1]); largos.push(l); total += l; }
        const t0 = performance.now();
        const paso = (ahora) => {
          if (g0 !== gen) { p.remove(); return res(false); }
          let d = Math.min(1, (ahora - t0) / ms) * total;
          let x = puntos[puntos.length - 1][0], y = puntos[puntos.length - 1][1];
          for (let i = 0; i < largos.length; i++) {
            if (d <= largos[i]) { const f = largos[i] ? d / largos[i] : 1; x = puntos[i][0] + (puntos[i + 1][0] - puntos[i][0]) * f; y = puntos[i][1] + (puntos[i + 1][1] - puntos[i][1]) * f; break; }
            d -= largos[i];
          }
          p.setAttribute("cx", x); p.setAttribute("cy", y);
          if (performance.now() - t0 < ms) requestAnimationFrame(paso); else { p.remove(); res(true); }
        };
        requestAnimationFrame(paso);
      });
    }
    function marca(x, y, ok, texto) {
      const g = el("g", { transform: `translate(${x},${y})` });
      const c = el("circle", { r: 11, fill: ok ? "rgba(76,175,125,.25)" : "rgba(217,83,79,.25)", stroke: ok ? "#4caf7d" : "#d9534f", "stroke-width": 2 }, g);
      void c;
      const s = document.createElementNS("http://www.w3.org/2000/svg", "text");
      s.setAttribute("text-anchor", "middle"); s.setAttribute("y", 4); s.setAttribute("font-size", 12); s.setAttribute("font-weight", 700);
      s.setAttribute("fill", ok ? "#9ff7c6" : "#ff8a86"); s.textContent = ok ? "✓" : "✕"; g.appendChild(s);
      if (texto) { const u = document.createElementNS("http://www.w3.org/2000/svg", "text"); u.setAttribute("text-anchor", "middle"); u.setAttribute("y", 24); u.setAttribute("font-size", 9); u.setAttribute("font-family", "IBM Plex Mono"); u.setAttribute("fill", ok ? "#4caf7d" : "#d9534f"); u.textContent = texto; g.appendChild(u); }
      setTimeout(() => g.remove(), 900);
    }

    /** Dibuja un caso: {caso, esperado, obtenido, resultado}. */
    async function animarCaso(c, rapido, g0) {
      $("#aislaCaso").innerHTML = `<span class="c11-insignia ${esc(c.resultado)}">${esc(c.resultado)}</span> ${esc(c.caso)}`;
      const ms = rapido ? 380 : 650;
      const m = /^(ping|TCP|traceroute) ([\w-]+) -> ([\w-]+)/.exec(c.caso);
      const llego = c.obtenido === "OK";
      if (/contadores DROP/.test(c.caso)) {
        const r = svg.querySelector("#aislaRouter"); r.setAttribute("stroke", "#d9534f"); r.setAttribute("stroke-width", 4);
        await esperar(ms); r.setAttribute("stroke", "#4f8fce"); r.setAttribute("stroke-width", 2);
        return;
      }
      if (/ttl 63/.test(c.caso)) {
        const n = (/de ([\w-]+) cruz/.exec(c.caso) || [])[1];
        if (n && POS[n]) marca(POS[n][0] + ([80, 450].includes(POS[n][0]) ? -56 : 56), POS[n][1], llego, "ttl=63");
        await esperar(rapido ? 80 : 160);
        return;
      }
      if (!m || !POS[m[2]] || !POS[m[3]]) { await esperar(150); return; }
      const [, , o, d] = m;
      const zo = zonaDe(o), zd = zonaDe(d);
      const forzada = /ruta forzada/.test(c.caso);
      let camino, fin = POS[d], textoFin = "";
      if (zo === zd) camino = [POS[o], POS[d]];
      else if (zo === "a" || zd === "a") camino = [POS[o], BORDE[zo], RT, BORDE[zd], POS[d]];
      else if (forzada) { camino = [POS[o], BORDE[zo], RT]; fin = RT; textoFin = "DROP"; }
      else { camino = [POS[o], PUERTA[zo]]; fin = PUERTA[zo]; textoFin = "Docker"; }
      const color = zo === "g" ? "#3fbf8f" : zo === "r" ? "#f0913a" : "#a77be8";
      const ok = await mover(camino, color, ms, g0);
      if (!ok) return;
      if (llego) { cuentas.pasan++; marca(fin[0], fin[1] - 20, true, ""); }
      else { cuentas.bloq++; if (forzada) cuentas.drop++; marca(fin[0], fin[1] - (fin === RT ? 30 : 20), false, textoFin); }
      pintarCuentas();
    }

    async function vaciar() {
      if (ocupado) return;
      ocupado = true;
      const g0 = gen;
      while (cola.length && g0 === gen) {
        const c = cola.shift();
        await animarCaso(c, cola.length > 3, g0);
      }
      ocupado = false;
    }

    /** Una línea de la salida de prueba_aislamiento.py: "  [APROBADA] caso: esperado X, obtenido Y". */
    function linea(x) {
      const m = /^\s*\[(APROBADA|FALLADA)\s*\]\s+(.+?): esperado (\S+?),? obtenido (\S+)/.exec(x);
      if (!m) return;
      cola.push({ resultado: m[1], caso: m[2], esperado: m[3], obtenido: m[4] });
      vaciar();
    }

    async function repetir() {
      reiniciar();
      let d;
      try { d = await leerJson("pruebas/resultados/aislamiento.json", true); } catch (e) { $("#aislaCaso").textContent = e.message; return; }
      cola = (d.casos || []).slice();
      vaciar();
    }

    return { dibujar, linea, reiniciar, repetir };
  })();

  // ================================================================ resultados de las pruebas
  async function leerJson(ruta, fresco) {
    const r = await fetch(R(ruta) + (fresco ? `?t=${Date.now()}` : ""), { cache: "no-store" });
    if (!r.ok) throw new Error(`no existe ${ruta} (todavía no se ha corrido)`);
    return r.json();
  }

  function cabResultado(ok, grande, pequeno, fecha, nota) {
    return `<div class="c11-resultado-cab">
      <div class="c11-veredicto ${ok ? "ok" : "mal"}"><b>${esc(grande)}</b><span class="c11-nota">${esc(pequeno)}</span></div>
      <span class="c11-fecha">${esc(nota || "último resultado guardado")} · ${esc(fecha)}</span></div>`;
  }

  function pintarUnitarias(lineas) {
    const caja = $("#resUnitarias");
    if (!lineas) {
      caja.innerHTML = cabResultado(true, "40 / 40", "pruebas aprobadas", "2026-10-05", "resultado de la entrega") +
        `<p class="c11-nota">Ida y vuelta de cada mensaje, recorte de valores fuera de rango, robots válidos, basura que no lanza excepción,
        el conteo de perdidos por número de secuencia y el jitter del RFC 3550 calculado a mano (el ejemplo de la tabla del README). Pulsa
        el botón para correrlas ahora en tu PC.</p>`;
      return;
    }
    // unittest -v escribe "test_x (modulo.Clase.test_x) ... ok"; si la prueba tiene docstring,
    // el "... ok" sale en la línea siguiente, así que se busca el resultado más adelante.
    const pruebas = [];
    let pendiente = null;
    for (const l of lineas) {
      const m = /^(test_\w+) \(.*?\.(\w+)\.test_\w+\)/.exec(l);
      if (m) pendiente = [l, m[1], m[2]];
      const r = /\.\.\. (ok|FAIL|ERROR)\s*$/.exec(l);
      if (r && pendiente) { pruebas.push([pendiente[0], pendiente[1], pendiente[2], r[1]]); pendiente = null; }
    }
    const ran = lineas.map((l) => /^Ran (\d+) tests?/.exec(l)).find(Boolean);
    const ok = lineas.some((l) => /^OK\b/.test(l.trim()));
    const total = ran ? Number(ran[1]) : pruebas.length;
    const bien = ok ? total : pruebas.filter((p) => p[3] === "ok").length;
    if (!total) { caja.innerHTML = '<p class="c11-nota">No se leyó el resumen de las pruebas: mira la salida de arriba.</p>'; return; }
    // Agrupadas por clase de prueba
    const grupos = {};
    for (const p of pruebas) (grupos[p[2]] = grupos[p[2]] || []).push(p);
    caja.innerHTML = cabResultado(ok, `${bien} / ${total}`, ok ? "pruebas aprobadas" : "con fallas", new Date().toLocaleString("es-CO"), "recién corrido") +
      Object.entries(grupos).map(([g, ps]) => `<div style="margin:.35rem 0"><span class="c11-mono" style="font-size:.7rem;color:var(--c11-suave)">${esc(g.replace(/^Test/, ""))}</span>
        <div class="c11-casos">${ps.map((p) => `<i class="${p[3] === "ok" ? "" : "falla"}" title="${esc(p[1].replace(/^test_/, "").replace(/_/g, " "))}: ${p[3]}"></i>`).join("")}</div></div>`).join("");
  }

  const ZONA_DE = (nombre) => {
    if (/^(player|track|ctrl-\d)/.test(nombre)) return "g";
    if (/^(sim-|ctrl-(spot|pepper|nao))/.test(nombre)) return "r";
    if (/^admin/.test(nombre)) return "a";
    return null;
  };

  async function pintarAislamiento(fresco) {
    const caja = $("#resAislamiento");
    let d;
    try { d = await leerJson("pruebas/resultados/aislamiento.json", fresco); }
    catch (e) { caja.innerHTML = `<p class="c11-nota">Sin resultado guardado: ${esc(e.message)}.</p>`; return; }
    if (window.DockerAnim) DockerAnim.datos({ aislamiento: d });
    const r = d.resumen || {};
    // Matriz origen → destino a partir del texto de cada caso ("ping A -> B", "TCP A -> B")
    const celdas = {};
    for (const c of d.casos || []) {
      const m = /^(ping|TCP|traceroute) ([\w-]+) -> ([\w-]+)/.exec(c.caso);
      if (!m) continue;
      const o = ZONA_DE(m[2]), de = ZONA_DE(m[3]);
      if (!o || !de) continue;
      const k = o + de;
      celdas[k] = celdas[k] || { n: 0, ok: 0, esperado: c.esperado };
      celdas[k].n++; if (c.resultado === "APROBADA") celdas[k].ok++;
    }
    const nombres = { g: "Gamer", r: "Robótica", a: "Admin" };
    let mat = `<div class="cab"></div>` + ["g", "r", "a"].map((z) => `<div class="cab">→ ${nombres[z]}</div>`).join("");
    for (const o of ["g", "r", "a"]) {
      mat += `<div class="fila">${nombres[o]}</div>`;
      for (const de of ["g", "r", "a"]) {
        const c = celdas[o + de];
        if (!c) { mat += `<div class="misma">—</div>`; continue; }
        const bloqueado = c.esperado === "FALLA";
        mat += `<div class="${bloqueado ? "no" : "si"}" title="${c.ok} de ${c.n} casos aprobados">${bloqueado ? "✕ bloqueado" : "✓ llega"}<br><small>${c.ok}/${c.n} casos</small></div>`;
      }
    }
    const ini = (d.router && d.router.drops_inicio && d.router.drops_inicio.por_cadena || {}).AISLAR_V1_V2;
    const fin = (d.router && d.router.drops_fin && d.router.drops_fin.por_cadena || {}).AISLAR_V1_V2;
    const ttl = (d.casos || []).filter((c) => /ttl 63/.test(c.caso) && c.resultado === "APROBADA").length;
    caja.innerHTML = cabResultado(r.veredicto === "APROBADA", `${r.aprobadas ?? "?"} / ${r.casos ?? "?"}`, `casos aprobados · ${r.veredicto || ""}`, fechaDe(d.fecha_epoch), fresco ? "recién corrido" : "") +
      `<div class="c11-rejilla" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">
        <div><p class="c11-etiqueta">Quién llega a quién (origen ↓, destino →)</p><div class="c11-matriz">${mat}</div></div>
        <div>
          <p class="c11-etiqueta">Lo que dice el router</p>
          <p class="c11-nota">Paquetes descartados en su cadena <span class="c11-mono">AISLAR_V1_V2</span>:
            <b class="c11-mono">${ini ?? "?"} → ${fin ?? "?"}</b>. Subieron justo con los intentos entre la VLAN 1 y la VLAN 2 hechos <b>con ruta forzada</b>:
            el paquete llegó al router y el router lo tiró. Ese es el cortafuegos funcionando.</p>
          <p class="c11-nota">${ttl} respuestas al admin llegaron con <b class="c11-mono">ttl=63</b> (64 − 1): cruzaron exactamente un router.</p>
          <p class="c11-etiqueta" style="margin-top:.6rem">Los ${(d.casos || []).length} casos</p>
          <div class="c11-casos">${(d.casos || []).map((c) => `<i class="${c.resultado === "APROBADA" ? "" : "falla"}" title="${esc(c.caso)} · esperado ${esc(c.esperado)}, obtenido ${esc(c.obtenido)}"></i>`).join("")}</div>
        </div>
      </div>
      <details class="c11-plegable"><summary>Ver los casos uno por uno</summary><div class="c11-dentro c11-tabla-envoltura">
        <table class="c11-tabla"><thead><tr><th>Caso</th><th>Esperado</th><th>Obtenido</th><th>Resultado</th></tr></thead><tbody>
        ${(d.casos || []).map((c) => `<tr><td>${esc(c.caso)}</td><td class="c11-mono">${esc(c.esperado)}</td><td class="c11-mono">${esc(c.obtenido)}</td><td><span class="c11-insignia ${esc(c.resultado)}">${esc(c.resultado)}</span></td></tr>`).join("")}
        </tbody></table></div></details>`;
  }

  async function pintarDisponibilidad(fresco) {
    const caja = $("#resDisponibilidad");
    let d;
    try { d = await leerJson("pruebas/resultados/disponibilidad.json", fresco); }
    catch (e) { caja.innerHTML = `<p class="c11-nota">Sin resultado guardado: ${esc(e.message)}.</p>`; return; }
    const ok = d.veredicto === "APROBADA";
    const criterios = (obj) => Object.entries(obj || {}).map(([k, v]) => `<div style="display:flex;gap:.5rem;align-items:center;margin:.2rem 0"><span class="c11-insignia ${esc(v)}">${esc(v)}</span><span class="c11-nota" style="font-size:.78rem">${esc(k)}</span></div>`).join("");
    const linea = (deteccion, vuelta, fuera) => {
      // Barra proporcional: [detección (rojo)] [fuera de servicio a propósito (gris)] [vuelta a OK (verde)]
      const total = Math.max(fuera || 0, (deteccion || 0) + (vuelta || 0) + 0.1);
      const pct = (v) => Math.max(13, (v / total) * 100);
      const medio = Math.max(0, total - deteccion - vuelta);
      return `<div class="c11-linea-tiempo">
        <div class="tramo" style="left:0;width:${pct(deteccion)}%;background:#d9534f">${num(deteccion, 2)} s</div>
        <div class="tramo" style="left:${pct(deteccion)}%;width:${Math.max(0, 100 - pct(deteccion) - pct(vuelta))}%;background:#2a3036;color:#8b929b">apagado a propósito (${num(medio, 0)} s)</div>
        <div class="tramo" style="right:0;width:${pct(vuelta)}%;background:#4caf7d">${num(vuelta, 2)} s</div></div>
        <div class="c11-nota" style="display:flex;justify-content:space-between;font-size:.7rem"><span>se ordena detener → el admin lo marca CAIDO</span><span>se arranca → vuelve a OK</span></div>`;
    };
    let html = cabResultado(ok, ok ? "APROBADA" : "FALLADA", "detección y recuperación de caídas", fechaDe(d.fecha_epoch), fresco ? "recién corrido" : "");
    html += `<div class="c11-rejilla dos">`;
    for (const c of d.caidas || []) {
      html += `<div><p class="c11-etiqueta">Se cae ${esc(c.servicio)}</p>${linea(c.caido_desde_orden_s, c.ok_desde_start_s, c.tiempo_total_fuera_s)}${criterios(c.criterios)}</div>`;
    }
    html += `</div>`;
    const a = d.caida_admin;
    if (a) {
      const zonas = Object.values(a.zonas_despues || {});
      const vivas = zonas.filter((z) => z.corriendo && !z.restart_count).length;
      html += `<p class="c11-etiqueta" style="margin-top:.9rem">Se apaga la propia sala de control (${num(a.duracion_caida_observada_s, 0)} s)</p>
        <div class="c11-cifras" style="margin-top:.2rem">
          <div class="c11-cifra"><b class="c11-zona-g">${vivas}/${zonas.length}</b><span>contenedores de las zonas siguieron corriendo, sin reinicios</span></div>
          <div class="c11-cifra"><b>${num(a.broker_vuelve_desde_start_s, 2)} s</b><span>tarda el broker MQTT en volver</span></div>
          <div class="c11-cifra"><b class="c11-zona-g">${num(a.todos_ok_desde_start_s, 2)} s</b><span>hasta ver los 6 servicios en OK otra vez</span></div>
        </div>${criterios(a.criterios)}`;
    }
    caja.innerHTML = html;
  }

  let redEscenario = "base";
  async function pintarRed(esc_, fresco) {
    redEscenario = esc_ || redEscenario;
    const caja = $("#resRed");
    const ESC = {
      base: "Escenario base: el laboratorio tal cual, 5 minutos.",
      retardo: "Con 30 ± 10 ms de retardo metido en el router a la VLAN 2 (tc netem). La VLAN 1 queda igual, como grupo de control.",
      carga: "Con los 6 mandos emulados mandando a 100 mensajes por segundo en vez de 20.",
    };
    let d;
    try { d = await leerJson(`pruebas/resultados/red_${redEscenario}.json`, fresco); }
    catch (e) { caja.innerHTML = pestanasRed() + `<p class="c11-nota">Sin resultado guardado: ${esc(e.message)}.</p>`; enlazarPestanas(); return; }
    const filas = Object.entries(d.por_servicio || {}).filter(([, s]) => s.ping_desde_admin);
    filas.sort((a, b) => (a[1].vlan - b[1].vlan) || a[0].localeCompare(b[0]));
    const maxP = Math.max(...filas.map(([, s]) => s.ping_desde_admin.p95_ms || 0), 0.1);
    const tabla = filas.map(([n, s]) => {
      const p = s.ping_desde_admin, z = ZONA[s.vlan] || ZONA[0];
      const disp = s.disponibilidad_por_estado ? s.disponibilidad_por_estado.disponibilidad_pct : null;
      const est = (s.segun_admin_mqtt || {}).ultimo_estado;
      return `<tr><td><b>${esc(n)}</b> <span class="${z.clase} c11-mono" style="font-size:.66rem">VLAN ${s.vlan}</span></td>
        <td class="num"><div style="display:flex;align-items:center;gap:.45rem;justify-content:flex-end"><div class="c11-barra" style="width:70px"><i style="width:${Math.min(100, (p.prom_ms / maxP) * 100)}%;background:${z.color}"></i></div>${num(p.prom_ms, 3)}</div></td>
        <td class="num">${num(p.p95_ms, 3)}</td><td class="num">${num(p.max_ms, 3)}</td><td class="num">${num(p.jitter_rfc3550_ms, 3)}</td>
        <td class="num">${p.n}</td><td class="num">${disp == null ? "—" : num(disp, 1) + " %"}</td>
        <td>${est ? `<span class="c11-insignia ${esc(est)}">${esc(est)}</span>` : "—"}</td></tr>`;
    }).join("");
    const proms = filas.map(([, s]) => s.ping_desde_admin.prom_ms);
    const t = Date.now();
    caja.innerHTML = pestanasRed() +
      cabResultado(true, `${num(Math.min(...proms), 2)}–${num(Math.max(...proms), 2)} ms`, "RTT promedio admin → servicios", fechaDe(d.inicio_epoch), `${num(d.duracion_s / 60, 0)} min de medición`) +
      `<p class="c11-nota">${esc(ESC[redEscenario] || "")} Ping cada ${num(d.intervalo_ping_s, 1)} s desde el admin (VLAN 3), cruzando el router. Tiempos en milisegundos.</p>
      <div class="c11-tabla-envoltura"><table class="c11-tabla"><thead><tr><th>Servicio</th><th style="text-align:right">RTT prom.</th><th style="text-align:right">p95</th><th style="text-align:right">máx.</th><th style="text-align:right">jitter</th><th style="text-align:right">pings</th><th style="text-align:right">tiempo en OK</th><th>el admin dijo</th></tr></thead><tbody>${tabla}</tbody></table></div>
      <div class="c11-graficas">
        <img src="${R(`pruebas/resultados/red_${redEscenario}_resumen.png`)}?t=${t}" alt="Resumen de RTT y jitter por servicio, escenario ${redEscenario}" loading="lazy">
        <img src="${R(`pruebas/resultados/red_${redEscenario}_rtt_tiempo.png`)}?t=${t}" alt="RTT en el tiempo, escenario ${redEscenario}" loading="lazy">
      </div>`;
    enlazarPestanas();
    App.imagen(caja);
  }
  function pestanasRed() {
    return `<div class="c11-pestanas">${[["base", "Base (5 min)"], ["retardo", "Con retardo en la VLAN 2"], ["carga", "Con carga (100 Hz)"]].map(([k, n]) =>
      `<button data-esc="${k}" class="${k === redEscenario ? "activa" : ""}">${n}</button>`).join("")}</div>`;
  }
  function enlazarPestanas() {
    $("#resRed").querySelectorAll("[data-esc]").forEach((b) => { b.onclick = () => pintarRed(b.dataset.esc, false); });
  }

  // ================================================================
  if (!window.App) {
    document.body.insertAdjacentHTML("afterbegin", '<div class="c11-aviso peligro" style="margin:1rem">Esta página se abre con el lanzador: doble clic en <b>ABRIR.bat</b> dentro de la carpeta del tema 11.</div>');
    return;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arrancar); else arrancar();
})();
