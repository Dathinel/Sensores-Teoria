// App del tema 3: YOLO en el PC -> mensaje por serial -> LEDs del ESP32.
// Usa la API común window.App (/comun/app.js) para correr las acciones de
// probar.json dentro de la página; lo propio de este tema es el diagrama
// interactivo (misma lógica que deteccion_pc.py + esp32_leds.py, en chico).
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
// Aviso de la instalación (PyTorch pesa cientos de MB)
// ---------------------------------------------------------------------------
// El estado del entorno viene de App.iniciar() (entorno.estado: "listo",
// "faltan", "nuevo", "sin-python", "roto"...).
function entornoListo(info) {
  const e = info && info.entorno;
  if (!e || !e.estado) return null;
  if (e.estado === "listo") return true;
  return false;
}

function pintarAvisoInstalacion(listo) {
  const textoFalta = "<b>La primera vez tarda:</b> al pulsar Iniciar se instala PyTorch y YOLO "
    + "(unos 700 MB a 1 GB de descarga). Con internet normal son <b>5 a 15 minutos</b>; el avance se ve aquí mismo. "
    + "Solo pasa una vez; después cada prueba abre en 10 a 30 s.";
  const textoListo = "Todo instalado: cada prueba tarda unos <b>10 a 30 s</b> en abrir su ventana (carga PyTorch). No está colgado.";
  const textoDuda = "Si es la primera vez, al pulsar Iniciar se instala PyTorch y YOLO (cientos de MB, <b>5 a 15 minutos</b> "
    + "según el internet). Después, cada prueba abre en 10 a 30 s.";
  const html = listo === true ? textoListo : listo === false ? textoFalta : textoDuda;
  const portada = document.getElementById("avisoInstalacion");
  portada.innerHTML = html;
  portada.hidden = false;
  portada.classList.toggle("ok", listo === true);
  // En cada paso solo hace falta avisar si todavía no está instalado (si ya
  // lo está, el panel de cada prueba ya dice «Todo instalado»).
  document.querySelectorAll("[data-aviso-instalacion]").forEach((el) => {
    el.innerHTML = listo === true ? "" : html;
  });
}

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------
function irAPaso(clave) {
  const sec = document.querySelector(`.paso[data-clave="${clave}"]`);
  if (!sec) return;
  if (ctlPasos) { const i = ctlPasos.secciones.indexOf(sec); if (i >= 0) { ctlPasos.ir(i); return; } }
  sec.scrollIntoView({ behavior: "smooth" });
}

// Lo que el usuario hace en la ventana de OpenCV y lo que debería ver, por acción.
const VENTANA_FOTOS = [
  "La ventana se llama «Deteccion en tiempo real» y puede quedar detrás de esta página: búscala en la barra de tareas.",
  "No hay que hacer nada: cambia sola de foto cada 3 segundos.",
  "Para cerrarla, haz clic sobre ella y pulsa la tecla q (o pulsa Detener aquí).",
];
const VENTANA_CAMARA = [
  "La ventana «Deteccion en tiempo real» muestra tu cámara con las cajas de todo lo que YOLO reconoce.",
  "Pon el objeto frente a la cámara, de cerca y con buena luz.",
  "Para cerrarla, haz clic sobre ella y pulsa la tecla q: manda '00' y apaga los LEDs.",
];
const OPCIONES = {
  "fotos": {
    titulo: "Silla y celular con fotos",
    queHacer: VENTANA_FOTOS,
    queDeberiasVer: [
      "En la franja negra de arriba: chair: 1 cell phone: 0 -> '10', luego '01' (celular) y luego '11' (las dos).",
      "Debajo: SIN ESP32 (solo vision) | FOTOS (3, cambia cada 3 s), si no tienes el ESP32 conectado.",
      "Aquí abajo, en «Lo que dice el programa»: «Sin ESP32 (…)» y «Objetivos: ['chair', 'cell phone']».",
    ],
  },
  "fotos-carro-moto": {
    titulo: "Carro y moto con fotos",
    queHacer: VENTANA_FOTOS,
    queDeberiasVer: [
      "Arriba: car: 1 motorcycle: 0 -> '10' (LED rojo), luego '01' (LED verde) y '11' (los dos).",
      "Aquí abajo: «Objetivos: ['car', 'motorcycle']».",
    ],
  },
  "camara": {
    titulo: "Silla y celular con tu cámara",
    queHacer: VENTANA_CAMARA,
    queDeberiasVer: [
      "Con una silla en cuadro: chair: 1 cell phone: 0 -> '10'. Con un celular en la mano: '01'. Con los dos: '11'.",
      "Con el ESP32 conectado: ESP32 en COM7 y la línea «ESP32 dice: LEDS 10»; el LED se prende al instante.",
    ],
  },
  "camara-carro-moto": {
    titulo: "Carro y moto con tu cámara",
    queHacer: VENTANA_CAMARA,
    queDeberiasVer: [
      "Con el carro: car: 1 motorcycle: 0 -> '10' (LED rojo, GPIO25). Con la moto: '01' (LED verde, GPIO26).",
      "Si no aparece la caja del juguete, acércalo o prueba con una foto de un carro real en el celular.",
    ],
  },
};

let ctlPasos = null;

// El simulador está en el mismo servidor, así que se puede saber cuándo el
// usuario lo usa y marcar los puntos que prueba (protocolo y apagado).
function vigilarSimulador(ctlChecklist) {
  const ifr = document.getElementById("simulador");
  const pide = (App.practica && App.practica.pide) || [];
  const punto = (re) => pide.find((p) => re.test(p));
  const enganchar = () => {
    let doc;
    try { doc = ifr.contentDocument; } catch (_) { return; }
    if (!doc) return;
    const marcar = (re) => { const p = punto(re); if (p && ctlChecklist) ctlChecklist.marcar(p); };
    ["btnObj1", "btnObj2"].forEach((id) => { const b = doc.getElementById(id); if (b) b.addEventListener("click", () => marcar(/serial/i)); });
    const corte = doc.getElementById("btnCortar");
    if (corte) corte.addEventListener("click", () => setTimeout(() => marcar(/apagado de seguridad/i), 2200));
  };
  ifr.addEventListener("load", enganchar);
  if (ifr.contentDocument && ifr.contentDocument.readyState === "complete") enganchar();
}

async function iniciar() {
  iniciarDiagrama();

  document.querySelectorAll("[data-ir]").forEach((a) => a.addEventListener("click", (e) => {
    e.preventDefault();
    irAPaso(a.dataset.ir);
  }));

  if (!window.App) {
    const d = document.createElement("div");
    d.className = "sin-framework";
    d.textContent = "Esta página necesita abrirse desde ABRIR.bat (o PROBAR.bat) para poder lanzar las pruebas.";
    document.body.prepend(d);
    pintarAvisoInstalacion(null);
    return;
  }

  let info = null;
  try { info = await App.iniciar(); } catch (err) { App.aviso && App.aviso("No se pudo leer la práctica: " + err.message, "error"); }
  pintarAvisoInstalacion(entornoListo(info));

  const ctlChecklist = App.checklist(document.getElementById("checklist"));
  document.querySelectorAll(".panel-ej[data-accion]").forEach((el) => App.panelEjecucion(el, el.dataset.accion, OPCIONES[el.dataset.accion] || {}));
  ctlPasos = App.pasos(document.getElementById("pasos"));
  vigilarSimulador(ctlChecklist);
  document.querySelectorAll(".figura img, .galeria img, .visor img").forEach((img) => App.imagen(img));

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
