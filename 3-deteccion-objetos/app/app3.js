// App del tema 3: YOLO en el PC -> mensaje por serial -> LEDs del ESP32.
// Usa la API común window.App (/comun/app.js) para correr las acciones de
// probar.json dentro de la página. Lo propio de este tema: el menú lateral
// (una sección a la vez, tipo Docker Desktop), el diagrama interactivo (misma
// lógica que deteccion_pc.py + esp32_leds.py, en chico) y el "monitor" que
// muestra lo que ve YOLO mientras deteccion_pc.py corre (--vista salida-app).
"use strict";

const CARPETA = "3-deteccion-objetos";
const REPO = "/repo/" + CARPETA + "/";

// ---------------------------------------------------------------------------
// Diagrama interactivo: cámara -> YOLO -> mensaje -> cable -> ESP32 -> LEDs
// ---------------------------------------------------------------------------
const PARES = {
  silla: { nombres: ["silla", "celular"], coco: ["chair", "cell phone"] },
  carro: { nombres: ["carro", "moto"], coco: ["car", "motorcycle"] },
};
const INFO = {
  camara: "La cámara web entrega unos 30 fotogramas por segundo de 640×480. Sin cámara, el programa puede leer fotos de ejemplo en su lugar (paso «Pruébalo con fotos»).",
  yolo: "YOLOv8 nano mira cada fotograma de una sola pasada y devuelve cajas con lo que reconoce (80 tipos de objetos). El programa se queda solo con los dos que le importan, y solo si la confianza es 0,4 o más.",
  mensaje: "Dos cifras, una por objeto: 1 = se ve, 0 = no se ve. Se manda apenas cambia y se repite cada 500 ms aunque nada cambie, para que el ESP32 sepa que la computadora sigue ahí.",
  esp32: "El ESP32 corre esp32_leds.py (guardado como main.py). Lee cada línea, pone los pines y contesta «LEDS xy». La barrita es su reloj: si llega a 2 s sin mensajes, apaga todo (apagado de seguridad).",
  leds: "Cada LED cuelga de un pin con su resistencia de 220 Ω: GPIO25 para el primer objeto (silla o carro, LED rojo) y GPIO26 para el segundo (celular o moto, LED verde).",
};

function iniciarDiagrama() {
  const $ = (id) => document.getElementById(id);
  const est = { par: "silla", obj: [false, false], cortado: false, ultimoMsg: performance.now(), ultimoEnvio: 0, enviado: null, avisado: false };

  function mensaje() { return est.obj.map((v) => (v ? "1" : "0")).join(""); }

  function pintarEtiquetas() {
    const n = PARES[est.par].nombres;
    $("dObj1").textContent = (est.obj[0] ? "− " : "+ ") + n[0];
    $("dObj2").textContent = (est.obj[1] ? "− " : "+ ") + n[1];
    $("dObj1").classList.toggle("activo", est.obj[0]);
    $("dObj2").classList.toggle("activo", est.obj[1]);
    $("dNom1").textContent = n[0];
    $("dNom2").textContent = n[1];
    const vistos = n.filter((_, i) => est.obj[i]);
    $("dCam").textContent = vistos.length ? vistos.join(" y ") + " en cuadro" : "nada en cuadro";
    const coco = PARES[est.par].coco.filter((_, i) => est.obj[i]);
    $("dYolo").textContent = "ve: " + (coco.length ? coco.map((c) => `"${c}"`).join(", ") : "—");
    $("dMsg").textContent = mensaje();
  }

  // El "PC" manda igual que deteccion_pc.py: al cambiar y cada 500 ms.
  function enviar() {
    const m = mensaje();
    est.enviado = m;
    est.ultimoEnvio = performance.now();
    if (est.cortado) return;
    const p = $("dPulso");
    p.classList.remove("va"); void p.offsetWidth; p.classList.add("va");
    // El "ESP32" lo recibe al llegar el pulso (misma validación que el firmware).
    setTimeout(() => {
      if (est.cortado) return;
      est.ultimoMsg = performance.now();
      est.avisado = false;
      $("dLed1").classList.toggle("on", m[0] === "1");
      $("dLed2").classList.toggle("on", m[1] === "1");
      $("dEsp").textContent = "LEDS " + m;
    }, 340);
  }

  function bucle() {
    const ahora = performance.now();
    if (mensaje() !== est.enviado || ahora - est.ultimoEnvio >= 500) enviar();
    const sin = ahora - est.ultimoMsg;
    $("dReloj").style.width = Math.min(100, (sin / 2000) * 100) + "%";
    if (sin > 2000 && !est.avisado) {
      est.avisado = true;
      $("dLed1").classList.remove("on");
      $("dLed2").classList.remove("on");
      $("dEsp").textContent = "APAGADO_SEGURIDAD";
    }
    requestAnimationFrame(bucle);
  }

  document.querySelectorAll(".diagrama .chip-sel").forEach((b) => b.addEventListener("click", () => {
    est.par = b.dataset.par;
    document.querySelectorAll(".diagrama .chip-sel").forEach((x) => x.classList.toggle("activo", x === b));
    pintarEtiquetas();
  }));
  $("dObj1").addEventListener("click", () => { est.obj[0] = !est.obj[0]; pintarEtiquetas(); });
  $("dObj2").addEventListener("click", () => { est.obj[1] = !est.obj[1]; pintarEtiquetas(); });
  $("dCable").addEventListener("click", () => {
    est.cortado = !est.cortado;
    $("dCable").classList.toggle("cortado", est.cortado);
    $("dLinea").classList.toggle("cortado", est.cortado);
    $("dCable").textContent = est.cortado ? "⟳ Volver a conectar" : "✂ Desconectar el cable";
    $("dInfo").textContent = est.cortado
      ? "Cable cortado: la computadora sigue «mandando», pero no llega nada. Mira la barrita del ESP32: a los 2 s apaga los LEDs y avisa APAGADO_SEGURIDAD."
      : "Cable conectado otra vez: el siguiente mensaje (máx. medio segundo) vuelve a prender lo que corresponda.";
  });
  document.querySelectorAll(".diagrama [data-info]").forEach((n) => {
    const mostrar = () => {
      document.querySelectorAll(".diagrama [data-info]").forEach((x) => x.classList.toggle("sel", x === n));
      $("dInfo").textContent = INFO[n.dataset.info];
    };
    n.addEventListener("click", mostrar);
    n.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); mostrar(); } });
  });
  pintarEtiquetas();
  requestAnimationFrame(bucle);
}

// ---------------------------------------------------------------------------
// Menú lateral (tipo Docker Desktop): una sección visible a la vez
// ---------------------------------------------------------------------------
const SECCIONES = ["inicio", "funciona", "yolo", "camara", "simulador", "montaje", "resultados"];
function leerLS(k) { try { return localStorage.getItem(k); } catch (_) { return null; } }
function guardarLS(k, v) { try { localStorage.setItem(k, v); } catch (_) { /* sin almacenamiento */ } }

function irA(sec, { sinHash } = {}) {
  if (!SECCIONES.includes(sec)) sec = "inicio";
  document.querySelectorAll(".seccion").forEach((s) => { s.hidden = s.dataset.sec !== sec; });
  document.querySelectorAll(".menu-item").forEach((b) => b.classList.toggle("activo", b.dataset.sec === sec));
  document.getElementById("contenido").scrollTop = 0;
  guardarLS("t3-seccion", sec);
  if (!sinHash && location.hash !== "#" + sec) history.replaceState(null, "", "#" + sec);
}

function iniciarMenu() {
  document.querySelectorAll(".menu-item").forEach((b) => b.addEventListener("click", () => irA(b.dataset.sec)));
  document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", (e) => { e.preventDefault(); irA(b.dataset.ir); }));
  addEventListener("hashchange", () => irA(location.hash.slice(1), { sinHash: true }));
  const pedida = location.hash.slice(1);
  irA(SECCIONES.includes(pedida) ? pedida : (leerLS("t3-seccion") || "inicio"), { sinHash: !pedida });
}

// ---------------------------------------------------------------------------
// Monitor: lo que ve YOLO mientras deteccion_pc.py corre
// ---------------------------------------------------------------------------
// deteccion_pc.py --vista salida-app deja ahí ultimo.jpg (el cuadro con las
// cajas) y estado.json (fase de arranque, detecciones con su confianza,
// mensaje, ESP32). La app los vuelve a leer cada 0,4 s mientras corre.
const VISTA = REPO + "salida-app/";
const ES = {
  person: "persona", chair: "silla", "cell phone": "celular", car: "carro", motorcycle: "moto",
  "dining table": "mesa", clock: "reloj", laptop: "portátil", tv: "televisor", bus: "bus", truck: "camión",
  bicycle: "bicicleta", "traffic light": "semáforo", bench: "banca", cup: "taza", bottle: "botella",
  book: "libro", couch: "sofá", "potted plant": "planta", keyboard: "teclado", mouse: "mouse",
  backpack: "morral", handbag: "bolso", tie: "corbata", "stop sign": "pare", umbrella: "sombrilla",
};
const EJEMPLOS = {
  "fotos": [["ejemplo-silla.jpg", "silla"], ["ejemplo-celular.jpg", "celular"], ["ejemplo-silla-y-celular.jpg", "las dos"]],
  "fotos-carro-moto": [["ejemplo-carro.jpg", "carro"], ["ejemplo-moto.jpg", "moto"], ["ejemplo-carro-y-moto.jpg", "los dos"]],
};
const NOMBRES = { "fotos": ["silla", "celular"], "fotos-carro-moto": ["carro", "moto"], "camara": ["silla", "celular"], "camara-carro-moto": ["carro", "moto"] };
const ACTIVOS = ["preparando", "instalando", "lanzada"];
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

function crearMonitor(elMon, elRes, opciones) {
  const conFotos = !!opciones.conFotos;
  elMon.innerHTML = `
    <div class="mon-cab"><span class="mon-rec"></span><span class="mono mon-titulo">lo que ve YOLO</span><span class="mono mon-fuente"></span></div>
    <div class="mon-pantalla">
      <img class="mon-img" alt="Último cuadro procesado por YOLO, con sus cajas" hidden>
      <div class="mon-capa"></div>
    </div>
    <div class="mon-pie"></div>`;
  elRes.innerHTML = `
    <div class="res-bloque">
      <span class="etiqueta">Qué detectó YOLO <span class="res-umbral">· cuenta si confianza ≥ 0,4</span></span>
      <ul class="dets"><li class="dets-vacio">Todavía nada: pulsa Iniciar.</li></ul>
    </div>
    <div class="res-fila">
      <div class="res-bloque res-msg">
        <span class="etiqueta">Mensaje al ESP32</span>
        <span class="msg-grande mono"><span class="c1">–</span><span class="c2">–</span></span>
      </div>
      <div class="res-bloque res-leds">
        <span class="etiqueta">LEDs</span>
        <div class="leds-fila">
          <span class="led-d l1"></span><span class="mono pin">GPIO25<br><b class="n1"></b></span>
          <span class="led-d verde l2"></span><span class="mono pin">GPIO26<br><b class="n2"></b></span>
        </div>
      </div>
    </div>
    <p class="res-esp mono">ESP32: —</p>`;
  const $m = (s) => elMon.querySelector(s), $r = (s) => elRes.querySelector(s);
  const img = $m(".mon-img"), capa = $m(".mon-capa"), pie = $m(".mon-pie");
  const st = { accion: opciones.accion, estado: "listo", t0: 0, desde: 0, timer: null, reloj: null, imgT: -1, ultimo: null, vistas: new Set(), apagando: null };

  function nombres() { return NOMBRES[st.accion] || ["objeto 1", "objeto 2"]; }
  function pintarNombres() { const n = nombres(); $r(".n1").textContent = n[0]; $r(".n2").textContent = n[1]; }

  function tiras(activa) {
    if (!conFotos) return "";
    return '<div class="tira">' + (EJEMPLOS[st.accion] || []).map(([f, txt], i) =>
      `<div class="tira-foto${activa === i + 1 ? " activa" : ""}"><img src="${REPO}img/ejemplos/${f}" alt="foto de ejemplo: ${esc(txt)}"><span class="mono">${i + 1}. ${esc(txt)}</span></div>`).join("") + "</div>";
  }

  function capaReposo() {
    img.hidden = true;
    capa.hidden = false;
    capa.className = "mon-capa reposo";
    capa.innerHTML = conFotos
      ? `<p><b>Pulsa «Iniciar»</b> y YOLO mirará estas tres fotos, una cada 3 s.</p>${tiras(0)}<p class="nota">Arrancar tarda 10-30 s (carga PyTorch). La primera vez descarga además el modelo (6 MB).</p>`
      : `<p><b>Pulsa «Iniciar»</b>: se abre la ventana de la cámara y aquí verás lo mismo, con lo que detecta.</p><p class="nota">Arrancar tarda 10-30 s (carga PyTorch).</p>`;
    pie.innerHTML = "";
  }

  // Pantalla de arranque: tres fases reales (las imprime deteccion_pc.py) y reloj.
  const FASES = ["Preparar el entorno de Python", "Cargar PyTorch, OpenCV y YOLO", "Cargar (o descargar) el modelo yolov8n.pt", "Mirar la primera imagen"];
  function capaArranque(paso, texto) {
    img.hidden = true;
    capa.hidden = false;
    capa.className = "mon-capa arranque";
    const lleva = st.desde ? (Date.now() - st.desde) / 1000 : 0;
    // paso: 0 = el lanzador aún prepara el entorno; 1-3 = fases del script.
    const frac = Math.min(0.97, paso <= 0 ? Math.min(0.15, lleva / 200) : (paso - 1) / 3 + Math.min(1, lleva / 20) / 3 * 0.9);
    capa.innerHTML = `
      <p class="arr-tit">Arrancando YOLO… <span class="mono arr-reloj">lleva ${mmss(lleva)} · suele tardar 10-30 s</span></p>
      <div class="app-barra arr-barra"><div style="width:${Math.round(frac * 100)}%"></div></div>
      <ol class="arr-fases">${FASES.map((f, i) => {
        const cls = i < paso ? "hecha" : i === paso ? "ahora" : "";
        return `<li class="${cls}"><span class="arr-marca">${i < paso ? "✓" : i === paso ? "●" : "○"}</span>${esc(i === paso && texto ? texto : f)}</li>`;
      }).join("")}</ol>
      <p class="nota">No está colgado: importar PyTorch es lo que más tarda. ${paso === 0 ? "Si es la primera vez, a la derecha se ve la instalación." : ""}</p>`;
  }

  function pintarDetecciones(d) {
    const ul = $r(".dets");
    const lista = (d && d.detecciones) || [];
    if (!lista.length) { ul.innerHTML = '<li class="dets-vacio">YOLO no ve nada que reconozca en esta imagen.</li>'; return; }
    const umbral = (d.confianza_minima || 0.4) * 100;
    ul.innerHTML = lista.slice(0, 7).map((c) => {
      const p = Math.round(c.conf * 100);
      const etiqueta = c.cuenta ? "cuenta ✓" : c.objetivo ? "muy baja" : "no interesa";
      const cls = c.cuenta ? "cuenta" : c.objetivo ? "baja" : "otra";
      return `<li class="${cls}"><span class="det-nom">${esc(ES[c.clase] || c.clase)} <span class="mono det-en">${esc(c.clase)}</span></span>
        <span class="det-barra"><span style="width:${p}%"></span><i style="left:${umbral}%"></i></span>
        <span class="mono det-pct">${(c.conf).toFixed(2)}</span><span class="det-etq">${etiqueta}</span></li>`;
    }).join("") + (lista.length > 7 ? `<li class="dets-vacio">y ${lista.length - 7} más…</li>` : "");
  }

  function pintarMensaje(m, conEsp, espDice) {
    const ms = m || "--";
    $r(".c1").textContent = ms[0]; $r(".c2").textContent = ms[1];
    $r(".c1").classList.toggle("on", ms[0] === "1"); $r(".c2").classList.toggle("on", ms[1] === "1");
    $r(".l1").classList.toggle("on", ms[0] === "1"); $r(".l2").classList.toggle("on", ms[1] === "1");
    $r(".res-esp").innerHTML = conEsp
      ? `ESP32 en <b>${esc(conEsp)}</b> · dice: <b>${esc(espDice || "(nada todavía)")}</b>`
      : "Sin ESP32 conectado: los LEDs de arriba muestran <b>cómo quedarían</b> con este mensaje.";
  }

  function pintarDetectando(d) {
    capa.hidden = true;
    img.hidden = false;
    if (d.img_t && d.img_t !== st.imgT) {
      st.imgT = d.img_t;
      const nueva = new Image();
      nueva.onload = () => { img.src = nueva.src; };
      nueva.src = VISTA + "ultimo.jpg?t=" + d.img_t;
    }
    $m(".mon-fuente").textContent = d.fuente || "";
    if (conFotos && d.foto) {
      st.vistas.add(d.foto);
      const quedan = d.segundos_por_foto ? `cambia cada ${d.segundos_por_foto} s` : "";
      pie.innerHTML = tiras(d.foto) + `<span class="nota mono">foto ${d.foto} de ${d.fotos} · ${esc(d.nombre_foto || "")} · ${quedan}</span>`;
      // Las tres fotos vistas = probado el protocolo (10, 01, 11) con YOLO de verdad.
      if (st.vistas.size >= (d.fotos || 3) && opciones.alVerTodo) opciones.alVerTodo(st.accion);
    } else {
      pie.innerHTML = `<span class="nota mono">cuadro de ${new Date(d.t * 1000).toLocaleTimeString()}</span>`;
    }
    pintarDetecciones(d);
    pintarMensaje(d.mensaje, d.esp32, d.esp32_dice);
  }

  // Programa cerrado: el ESP32 real apagaría los LEDs a los 2 s (apagado de seguridad).
  function pintarFin(texto) {
    if (st.ultimo && st.ultimo.fase === "detectando") {
      capa.hidden = false;
      capa.className = "mon-capa fin";
      let s = 2.0;
      capa.innerHTML = `<p><b>${esc(texto)}</b></p><p class="fin-cuenta">Sin mensajes nuevos: el ESP32 apaga los LEDs en <span class="mono">2,0</span> s (apagado de seguridad).</p>`;
      clearInterval(st.apagando);
      st.apagando = setInterval(() => {
        s = Math.max(0, s - 0.1);
        const sp = capa.querySelector(".fin-cuenta .mono"); if (sp) sp.textContent = s.toFixed(1).replace(".", ",");
        if (s <= 0) {
          clearInterval(st.apagando);
          pintarMensaje(null, null, null);
          $r(".c1").textContent = "–"; $r(".c2").textContent = "–";
          const p = capa.querySelector(".fin-cuenta"); if (p) p.innerHTML = "LEDs apagados (<span class=\"mono\">APAGADO_SEGURIDAD</span>). Pulsa Iniciar para volver a probar.";
        }
      }, 100);
    } else if (st.estado !== "listo") {
      capaReposo();
    }
  }

  async function leer() {
    let d = null;
    try {
      const r = await fetch(VISTA + "estado.json?t=" + Date.now(), { cache: "no-store" });
      if (r.ok) d = await r.json();
    } catch (_) { d = null; }
    // Un estado.json de una corrida anterior (antes de pulsar Iniciar) no vale.
    if (d && st.t0 && d.inicio < st.t0 - 3) d = null;
    if (!ACTIVOS.includes(st.estado)) return;
    if (!d) { capaArranque(0, st.estado === "instalando" ? "Preparando el entorno (solo la primera vez: PyTorch, unos minutos)" : ""); return; }
    st.ultimo = d;
    if (d.fase === "arranque") capaArranque(d.paso, d.texto);
    else if (d.fase === "detectando") pintarDetectando(d);
  }

  function alEstado(t) {
    const antes = st.estado;
    st.estado = (t && t.estado) || "listo";
    if (ACTIVOS.includes(st.estado)) {
      if (!ACTIVOS.includes(antes)) {
        clearInterval(st.apagando);
        // Si la página se abrió con el programa ya en marcha, vale cualquier estado.json.
        st.t0 = antes === "listo" && st.estado === "lanzada" ? 0 : Date.now() / 1000;
        st.desde = Date.now(); st.imgT = -1; st.ultimo = null; st.vistas.clear();
        $m(".mon-rec").classList.add("on");
        capaArranque(0, "");
        leer();
        clearInterval(st.timer); st.timer = setInterval(leer, 400);
      }
    } else if (ACTIVOS.includes(antes)) {
      clearInterval(st.timer); st.timer = null;
      $m(".mon-rec").classList.remove("on");
      pintarFin(st.estado === "error" ? "El programa se cerró con un error (mira «Lo que dice el programa»)." : "Programa detenido.");
    }
  }

  function cambiarAccion(id) {
    if (ACTIVOS.includes(st.estado)) return false;
    st.accion = id; pintarNombres();
    if (!st.ultimo) capaReposo();
    return true;
  }

  pintarNombres(); capaReposo(); pintarMensaje(null, null, null);
  $r(".res-esp").textContent = "ESP32: opcional (sin él, los LEDs de arriba muestran cómo quedarían).";
  return { alEstado, cambiarAccion, get estado() { return st.estado; }, get accion() { return st.accion; } };
}

// ---------------------------------------------------------------------------
// Aviso de la instalación (PyTorch pesa cientos de MB) y chip del modelo
// ---------------------------------------------------------------------------
function pintarAvisoInstalacion(info) {
  const e = info && info.entorno;
  const listo = e && e.estado ? e.estado === "listo" : null;
  const textoFalta = "<b>La primera vez tarda:</b> al pulsar Iniciar se instala PyTorch y YOLO "
    + "(unos 700 MB a 1 GB de descarga). Con internet normal son <b>5 a 15 minutos</b>; el avance se ve en la app. "
    + "Solo pasa una vez; después cada prueba arranca en 10 a 30 s.";
  const textoListo = "Todo instalado: cada prueba arranca en <b>10 a 30 s</b> (carga PyTorch). No está colgado.";
  const textoDuda = "Si es la primera vez, al pulsar Iniciar se instala PyTorch y YOLO (cientos de MB, <b>5 a 15 minutos</b> "
    + "según el internet). Después, cada prueba arranca en 10 a 30 s.";
  const el = document.getElementById("avisoInstalacion");
  el.innerHTML = listo === true ? textoListo : listo === false ? textoFalta : textoDuda;
  el.hidden = false;
  el.classList.toggle("ok", listo === true);
}

async function pintarChipModelo() {
  const chip = document.getElementById("chipModelo");
  let hay = null;
  try { const r = await fetch(REPO + "yolov8n.pt", { headers: { Range: "bytes=0-0" }, cache: "no-store" }); hay = r.ok; } catch (_) { hay = null; }
  chip.classList.toggle("ok", hay === true);
  chip.textContent = hay ? "modelo YOLO listo" : "modelo: se descarga solo (6 MB)";
  chip.title = hay ? "yolov8n.pt ya está en la carpeta del tema"
    : "yolov8n.pt no viene en el repositorio: la primera prueba lo descarga solo (6 MB, necesita internet)";
}

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------
const OPCIONES = {
  "fotos": { titulo: "Silla y celular", queVaAPasar: "", botonTexto: "▶ Iniciar YOLO con las fotos" },
  "fotos-carro-moto": { titulo: "Carro y moto", queVaAPasar: "", botonTexto: "▶ Iniciar YOLO con las fotos" },
  "camara": { titulo: "Silla y celular con tu cámara", queVaAPasar: "", botonTexto: "▶ Abrir la cámara con YOLO",
    queHacer: ["La ventana «Deteccion en tiempo real» puede quedar detrás: búscala en la barra de tareas.", "Para cerrarla: clic sobre ella y tecla q (manda '00'), o Detener aquí."] },
  "camara-carro-moto": { titulo: "Carro y moto con tu cámara", queVaAPasar: "", botonTexto: "▶ Abrir la cámara con YOLO",
    queHacer: ["Acerca el juguete con buena luz; si no aparece su caja, prueba con la foto de un carro real en el celular.", "Para cerrarla: clic sobre ella y tecla q, o Detener aquí."] },
};

// El simulador está en el mismo servidor, así que se puede saber cuándo el
// usuario lo usa y marcar los puntos que prueba (protocolo y apagado).
function vigilarSimulador(marcar) {
  const ifr = document.getElementById("simIframe");
  const enganchar = () => {
    let doc;
    try { doc = ifr.contentDocument; } catch (_) { return; }
    if (!doc) return;
    ["btnObj1", "btnObj2"].forEach((id) => { const b = doc.getElementById(id); if (b) b.addEventListener("click", () => marcar(/serial/i)); });
    const corte = doc.getElementById("btnCortar");
    if (corte) corte.addEventListener("click", () => setTimeout(() => marcar(/apagado de seguridad/i), 2200));
  };
  ifr.addEventListener("load", enganchar);
  if (ifr.contentDocument && ifr.contentDocument.readyState === "complete") enganchar();
}

// Un "laboratorio": selector de directiva + paneles de acción + monitor.
function montarLaboratorio(selId, monId, resId, conFotos, marcarCubre) {
  const sel = document.getElementById(selId);
  const botones = [...sel.querySelectorAll("button")];
  const seccion = sel.closest(".seccion");
  const monitor = crearMonitor(document.getElementById(monId), document.getElementById(resId), {
    accion: botones[0].dataset.accion, conFotos, alVerTodo: (id) => marcarCubre(id),
  });
  botones.forEach((b) => b.addEventListener("click", () => {
    if (!monitor.cambiarAccion(b.dataset.accion)) { App.aviso("Primero detén la prueba que está corriendo.", "aviso"); return; }
    botones.forEach((x) => x.classList.toggle("activo", x === b));
    seccion.querySelectorAll(".panel-ej").forEach((p) => { p.hidden = p.dataset.accion !== b.dataset.accion; });
  }));
  seccion.querySelectorAll(".panel-ej[data-accion]").forEach((el) => {
    const id = el.dataset.accion;
    App.panelEjecucion(el, id, Object.assign({}, OPCIONES[id] || {}, {
      alEstado: (t) => {
        // El monitor sigue a la acción que esté corriendo (aunque se haya
        // recargado la página con la otra directiva elegida).
        // Los avisos de la otra directiva (la que no sigue el monitor) se
        // ignoran, salvo que esa sea la que arranca.
        if (id !== monitor.accion) {
          if (!ACTIVOS.includes(t.estado) || ACTIVOS.includes(monitor.estado)) return;
          botones.forEach((x) => x.classList.toggle("activo", x.dataset.accion === id));
          seccion.querySelectorAll(".panel-ej").forEach((p) => { p.hidden = p.dataset.accion !== id; });
          monitor.cambiarAccion(id);
        }
        monitor.alEstado(t);
      },
    }));
  });
}

async function iniciar() {
  iniciarMenu();
  iniciarDiagrama();
  pintarChipModelo();

  if (!window.App) {
    const d = document.createElement("div");
    d.className = "sin-framework";
    d.textContent = "Esta página necesita abrirse desde ABRIR.bat para poder lanzar las pruebas.";
    document.getElementById("contenido").prepend(d);
    pintarAvisoInstalacion(null);
    return;
  }

  let info = null;
  try { info = await App.iniciar(); } catch (err) { App.aviso && App.aviso("No se pudo leer la práctica: " + err.message, "error"); }
  pintarAvisoInstalacion(info);

  // Checklist en Inicio + su resumen en el pie del menú lateral.
  const ctlChecklist = App.checklist(document.getElementById("checklist"));
  const pide = (App.practica && App.practica.pide) || [];
  const resumenPide = () => {
    const cajas = document.querySelectorAll("#checklist input[type=checkbox]");
    const n = [...cajas].filter((c) => c.checked).length, total = cajas.length || pide.length;
    document.getElementById("pideTxt").textContent = `${n} de ${total} probados`;
    document.getElementById("pideBarra").style.width = (total ? (n / total) * 100 : 0) + "%";
  };
  document.getElementById("checklist").addEventListener("change", resumenPide);
  new MutationObserver(resumenPide).observe(document.getElementById("checklist"), { subtree: true, childList: true, attributes: true });
  setTimeout(resumenPide, 300);
  const marcar = (re) => { const p = pide.find((x) => re.test(x)); if (p && ctlChecklist) { ctlChecklist.marcar(p); setTimeout(resumenPide, 50); } };
  // Con --sin-ventana la prueba de fotos termina con Detener (no "terminó bien"):
  // se marca lo que cubre cuando el monitor ya mostró las tres fotos.
  const marcarCubre = (id) => {
    const a = ((App.practica && App.practica.acciones) || []).find((x) => x.id === id);
    ((a && a.cubre) || []).forEach((txt) => { if (ctlChecklist) ctlChecklist.marcar(txt); });
    setTimeout(resumenPide, 50);
  };

  montarLaboratorio("selDirectiva", "monitorFotos", "resFotos", true, marcarCubre);
  montarLaboratorio("selDirCam", "monitorCamara", "resCamara", false, marcarCubre);
  vigilarSimulador(marcar);
  document.querySelectorAll(".figura img, .galeria img, .visor img").forEach((img) => App.imagen(img));
  App.on && App.on("ok", () => setTimeout(resumenPide, 50));

  try { await App.markdown(document.getElementById("mdIdea"), "README.md", { desde: "## Qué es la detección de objetos", hasta: "## Conexiones" }); } catch (_) { /* opcional */ }

  document.getElementById("btnSimPestana").addEventListener("click", () => App.abrir(REPO + "preview.html"));
  document.getElementById("btnReadme").addEventListener("click", () => App.abrir("https://github.com/Dathinel/Sensores-Teoria/tree/main/" + CARPETA));
  let firmware = null;
  const leerFirmware = async () => {
    if (firmware === null) {
      const r = await fetch(REPO + "esp32_leds.py");
      if (!r.ok) throw new Error("No se pudo leer esp32_leds.py");
      firmware = await r.text();
    }
    return firmware;
  };
  document.getElementById("btnVerFw").addEventListener("click", async () => {
    const caja = document.getElementById("fwCodigo");
    try { document.getElementById("fwTexto").textContent = await leerFirmware(); } catch (e) { App.aviso(e.message, "error"); return; }
    caja.hidden = !caja.hidden;
  });
  document.getElementById("btnCopiarFw").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(await leerFirmware());
      App.aviso("Código del ESP32 copiado: pégalo en Thonny y guárdalo en el ESP32 como main.py.", "ok");
    } catch (e) { App.aviso("No se pudo copiar: usa «ver el código» y cópialo a mano.", "error"); }
  });
}

document.addEventListener("DOMContentLoaded", iniciar);
