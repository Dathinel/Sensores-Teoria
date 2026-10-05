// App del tema 8: Punto 1 (teclado -> brazo que dibuja) y Punto 2 (visión -> CNN -> ESP-A -> SPI/UART -> ESP-B -> OLED).
// Usa la API común window.App (/comun/app.js). Si alguna función de la API no está, la página sigue
// funcionando con un reemplazo sencillo (pestañas, pasos, ampliar imágenes).
"use strict";

const CARPETA = "8-digitos-brazo-y-vision";

// ---------------------------------------------------------------- utilidades
function guardar(clave, valor) { try { localStorage.setItem("t8-" + clave, valor); } catch (e) { /* sin storage */ } }
function leer(clave) { try { return localStorage.getItem("t8-" + clave); } catch (e) { return null; } }
const tieneApp = (nombre) => typeof window.App === "object" && window.App && typeof window.App[nombre] === "function";

// ---------------------------------------------------------------- pestañas Punto 1 / Punto 2
function mostrarPunto(id, desplazar) {
  document.querySelectorAll(".punto").forEach((el) => el.classList.toggle("visible", el.id === id));
  document.querySelectorAll(".pest").forEach((b) => {
    const activa = b.dataset.punto === id;
    b.classList.toggle("activa", activa);
    b.setAttribute("aria-selected", activa ? "true" : "false");
  });
  guardar("punto", id);
  // El hash es "#punto-1"/"#punto-2" (no "#p1": el navegador saltaría al elemento con ese id).
  const hash = "#punto-" + id.slice(1);
  if (location.hash !== hash) history.replaceState(null, "", hash);
  cargarIframes(document.getElementById(id));
  if (desplazar) document.querySelector(".pestanas").scrollIntoView({ behavior: "smooth" });
}

// Los previews se cargan recién cuando se ve su punto (no gastar dos páginas al abrir).
function cargarIframes(raiz) {
  if (!raiz) return;
  raiz.querySelectorAll("iframe[data-src]").forEach((f) => {
    if (!f.getAttribute("src")) f.setAttribute("src", f.dataset.src);
  });
}

// ---------------------------------------------------------------- pasos (fallback si no hay App.pasos)
function pasosPropios(contenedor) {
  const pasos = [...contenedor.querySelectorAll(":scope > section.paso")];
  const clave = "paso-" + contenedor.id;
  let actual = Math.min(Number(leer(clave)) || 0, pasos.length - 1);
  const nav = document.createElement("div");
  nav.className = "t8-pasos-nav";
  pasos.forEach((s, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = (i + 1) + ". " + s.dataset.titulo;
    b.addEventListener("click", () => ir(i, true));
    nav.appendChild(b);
  });
  contenedor.prepend(nav);
  const pie = document.createElement("div");
  pie.className = "t8-pasos-pie";
  pie.innerHTML = '<button type="button" data-d="-1">← Anterior</button><button type="button" data-d="1">Siguiente →</button>';
  pie.addEventListener("click", (e) => { const d = Number(e.target.dataset.d); if (d) ir(actual + d, true); });
  contenedor.appendChild(pie);
  function ir(i, desplazar) {
    actual = Math.max(0, Math.min(pasos.length - 1, i));
    pasos.forEach((s, k) => { s.hidden = k !== actual; });
    [...nav.children].forEach((b, k) => b.classList.toggle("activo", k === actual));
    pie.children[0].disabled = actual === 0;
    pie.children[1].disabled = actual === pasos.length - 1;
    guardar(clave, String(actual));
    if (desplazar) document.querySelector(".pestanas").scrollIntoView({ behavior: "smooth" });
  }
  ir(actual, false);
}

// ---------------------------------------------------------------- ampliar imágenes (fallback)
function lightboxPropio(img) {
  img.addEventListener("click", () => {
    const capa = document.createElement("div");
    capa.className = "t8-lightbox";
    const grande = document.createElement("img");
    grande.src = img.src; grande.alt = img.alt;
    capa.appendChild(grande);
    capa.addEventListener("click", () => capa.remove());
    document.addEventListener("keydown", function esc(e) { if (e.key === "Escape") { capa.remove(); document.removeEventListener("keydown", esc); } });
    document.body.appendChild(capa);
  });
}

// ---------------------------------------------------------------- Punto 1: trayectoria interactiva
// Copiado de TRAZOS_DIGITOS en punto-1-teclado-brazo-dibujando/brazo_dibuja.py (u horizontal, v vertical, v=1 arriba).
const TRAZOS = {
  0: [[0.2, 0], [0, 0.2], [0, 0.8], [0.2, 1], [0.8, 1], [1, 0.8], [1, 0.2], [0.2, 0]],
  1: [[0.3, 0.8], [0.5, 1], [0.5, 0]],
  2: [[0, 0.8], [0.3, 1], [0.7, 1], [1, 0.8], [1, 0.55], [0, 0.2], [0, 0], [1, 0]],
  3: [[0, 1], [1, 1], [0.5, 0.55], [1, 0.15], [0.6, 0], [0.1, 0.1]],
  4: [[0.7, 0], [0.7, 1], [0, 0.35], [1, 0.35]],
  5: [[1, 1], [0, 1], [0, 0.55], [0.8, 0.55], [1, 0.35], [0.8, 0], [0, 0.1]],
  6: [[0.9, 0.9], [0.3, 1], [0, 0.6], [0, 0.2], [0.3, 0], [0.7, 0], [1, 0.25], [0.7, 0.5], [0.2, 0.5]],
  7: [[0, 1], [1, 1], [0.4, 0]],
  8: [[0.5, 0.5], [0.2, 0.65], [0.2, 0.9], [0.5, 1], [0.8, 0.9], [0.8, 0.65], [0.5, 0.5],
      [0.2, 0.35], [0.2, 0.1], [0.5, 0], [0.8, 0.1], [0.8, 0.35], [0.5, 0.5]],
  9: [[0.3, 0.1], [0.7, 0], [1, 0.35], [1, 0.75], [0.7, 1], [0.3, 0.9], [0.3, 0.5], [0.8, 0.5]],
};
const CENTRO_J1 = 0.0, CENTRO_J2 = 1.0, RANGO_J1 = 0.35, RANGO_J2 = 0.35, PUNTOS_POR_TRAMO = 8;

function densificar(trazo) {
  const out = [];
  for (let i = 0; i < trazo.length - 1; i++) {
    const [u0, v0] = trazo[i], [u1, v1] = trazo[i + 1];
    for (let k = 0; k < PUNTOS_POR_TRAMO; k++) {
      const t = k / PUNTOS_POR_TRAMO;
      out.push([u0 + (u1 - u0) * t, v0 + (v1 - v0) * t]);
    }
  }
  out.push(trazo[trazo.length - 1]);
  return out;
}

function iniciarTrazo() {
  const svg = document.getElementById("trazo-svg");
  const botones = document.getElementById("trazo-botones");
  const lectura = document.getElementById("trazo-lectura");
  if (!svg) return;
  const NS = "http://www.w3.org/2000/svg";
  // marco del "cuadrado" del dígito
  const marco = document.createElementNS(NS, "rect");
  Object.entries({ x: 0, y: 0, width: 1, height: 1, fill: "none", stroke: "#262b31", "stroke-width": 0.008, "stroke-dasharray": "0.03 0.02" })
    .forEach(([k, v]) => marco.setAttribute(k, v));
  svg.appendChild(marco);
  const linea = document.createElementNS(NS, "polyline");
  Object.entries({ fill: "none", stroke: "#e8b931", "stroke-width": 0.045, "stroke-linecap": "round", "stroke-linejoin": "round" })
    .forEach(([k, v]) => linea.setAttribute(k, v));
  svg.appendChild(linea);
  const puntos = document.createElementNS(NS, "g");
  svg.appendChild(puntos);
  const punta = document.createElementNS(NS, "circle");
  Object.entries({ r: 0.035, fill: "#fff", stroke: "#e8b931", "stroke-width": 0.012 }).forEach(([k, v]) => punta.setAttribute(k, v));
  svg.appendChild(punta);

  let animacion = null;
  function dibujar(d) {
    [...botones.children].forEach((b) => b.classList.toggle("activo", b.dataset.d === String(d)));
    const base = TRAZOS[d];
    const pts = densificar(base);
    puntos.innerHTML = "";
    base.forEach(([u, v]) => {
      const c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", u); c.setAttribute("cy", 1 - v); c.setAttribute("r", 0.018); c.setAttribute("fill", "#4f8fce");
      puntos.appendChild(c);
    });
    if (animacion) cancelAnimationFrame(animacion);
    // ~25 ms por posición, como los 6 pasos de física por punto del script
    const inicio = performance.now();
    const paso = (ahora) => {
      const n = Math.max(1, Math.min(pts.length, 1 + Math.floor((ahora - inicio) / 25)));
      linea.setAttribute("points", pts.slice(0, n).map(([u, v]) => u + "," + (1 - v)).join(" "));
      const [u, v] = pts[n - 1];
      punta.setAttribute("cx", u); punta.setAttribute("cy", 1 - v);
      const j1 = CENTRO_J1 + (u - 0.5) * 2 * RANGO_J1;
      const j2 = CENTRO_J2 - (v - 0.5) * 2 * RANGO_J2;
      const grados = (r) => (r * 180 / Math.PI).toFixed(1).padStart(5, " ") + "°";
      lectura.textContent = `Dígito ${d} · posición ${n} de ${pts.length} · u=${u.toFixed(2)} v=${v.toFixed(2)} → base ${grados(j1)} · codo ${grados(j2)}`;
      if (n < pts.length) animacion = requestAnimationFrame(paso);
      else lectura.textContent += " · listo";
    };
    animacion = requestAnimationFrame(paso);
  }
  for (let d = 0; d <= 9; d++) {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = d; b.dataset.d = d;
    b.addEventListener("click", () => dibujar(d));
    botones.appendChild(b);
  }
  dibujar(7);
}

// ---------------------------------------------------------------- Punto 2: simulador de la votación
// Misma regla que reconocer_digito.py: un frame con confianza < 60 % cuenta como "nada"; se confirma si el
// ganador tiene >= 80 % de la ventana de 15 (12 de 15).
function iniciarVotos() {
  const sel = document.getElementById("votos-digito");
  const ruido = document.getElementById("votos-ruido");
  const ruidoV = document.getElementById("votos-ruido-v");
  const fila = document.getElementById("votos-fila");
  const res = document.getElementById("votos-res");
  if (!sel) return;
  for (let d = 0; d <= 9; d++) sel.add(new Option(String(d), String(d)));
  sel.value = "3";
  ruido.addEventListener("input", () => { ruidoV.textContent = ruido.value + " %"; });
  // confusiones típicas de dígitos escritos a mano
  const PARECIDOS = { 0: [6, 8], 1: [7, 4], 2: [7, 3], 3: [8, 5], 4: [9, 1], 5: [6, 3], 6: [5, 0], 7: [1, 2], 8: [3, 0], 9: [4, 7] };
  let temporizadores = [];
  document.getElementById("votos-correr").addEventListener("click", () => {
    temporizadores.forEach(clearTimeout); temporizadores = [];
    const real = Number(sel.value), p = Number(ruido.value) / 100;
    const votos = [];
    for (let i = 0; i < 15; i++) {
      const r = Math.random();
      if (r >= p) votos.push(real);
      else if (r < p / 2) votos.push(null); // confianza < 60 %: "nada"
      else { const op = PARECIDOS[real]; votos.push(op[Math.floor(Math.random() * op.length)]); }
    }
    fila.innerHTML = "";
    res.className = "lectura"; res.textContent = "Leyendo...";
    votos.forEach((v, i) => {
      const c = document.createElement("div");
      c.className = "voto" + (v === null ? " nada" : "");
      c.textContent = v === null ? "·" : v;
      c.title = v === null ? "confianza < 60 %: cuenta como nada" : "la red dijo " + v;
      fila.appendChild(c);
      temporizadores.push(setTimeout(() => c.classList.add("ve"), 60 * i));
    });
    temporizadores.push(setTimeout(() => {
      const conteo = new Map();
      votos.forEach((v) => conteo.set(v, (conteo.get(v) || 0) + 1));
      let ganador = null, max = -1;
      conteo.forEach((n, v) => { if (n > max) { max = n; ganador = v; } });
      const prop = max / votos.length;
      fila.querySelectorAll(".voto").forEach((c, i) => c.classList.toggle("gana", votos[i] === ganador && ganador !== null));
      if (ganador !== null && prop >= 0.8) {
        res.className = "lectura ok";
        res.textContent = `CONFIRMADO: ${ganador} (ganó ${max} de 15 = ${Math.round(prop * 100)} %) → se manda DIGIT:${ganador} una sola vez`;
      } else {
        res.className = "lectura no";
        res.textContent = `Sin confirmar: el más votado (${ganador === null ? "nada" : ganador}) tiene ${max} de 15 = ${Math.round(prop * 100)} %, le falta llegar a 12. No se manda nada todavía.`;
      }
    }, 60 * 15 + 150));
  });
}

// ---------------------------------------------------------------- arranque
async function arrancar() {
  // pestañas
  document.querySelectorAll(".pest").forEach((b) => b.addEventListener("click", () => mostrarPunto(b.dataset.punto, false)));
  document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => mostrarPunto(b.dataset.ir, true)));
  const enHash = /^#punto-([12])$/.exec(location.hash || "");
  const guardado = leer("punto");
  mostrarPunto(enHash ? "p" + enHash[1] : (guardado === "p2" ? "p2" : "p1"), false);

  iniciarTrazo();
  iniciarVotos();

  // markdown del README al abrir cada "Leer la explicación completa"
  document.querySelectorAll("details.mas").forEach((det) => {
    det.addEventListener("toggle", () => {
      const caja = det.querySelector(".md");
      if (!det.open || caja.dataset.cargado) return;
      caja.dataset.cargado = "1";
      if (tieneApp("markdown")) {
        Promise.resolve(App.markdown(caja, caja.dataset.md, { desde: caja.dataset.desde, hasta: caja.dataset.hasta }))
          .catch(() => { caja.textContent = "No se pudo cargar el README."; });
      } else {
        caja.innerHTML = 'La explicación completa está en el <a href="/repo/' + CARPETA + '/' + caja.dataset.md + '" target="_blank" rel="noopener">README del punto</a>.';
      }
    });
  });

  // imágenes ampliables
  document.querySelectorAll("img.ampliable").forEach((img) => { if (tieneApp("imagen")) App.imagen(img); else lightboxPropio(img); });

  // API común: manifiesto, checklist, pasos y paneles de ejecución
  if (tieneApp("iniciar")) {
    try { await App.iniciar(); } catch (e) { console.warn("App.iniciar:", e); }
  }
  if (tieneApp("checklist")) App.checklist(document.getElementById("checklist"));
  else document.getElementById("checklist").innerHTML = '<p class="nota">(La lista se carga cuando la app se abre con ABRIR.bat.)</p>';

  ["pasos-p1", "pasos-p2"].forEach((id) => {
    const c = document.getElementById(id);
    if (tieneApp("pasos")) App.pasos(c); else pasosPropios(c);
  });

  const paneles = {
    "run-p1-sim": ["p1-sim", {
      titulo: "Brazo dibujando en PyBullet",
      queVaAPasar: "Se abre el simulador PyBullet con el brazo robótico de brazo.urdf. Sin ESP32 conectado, el programa avisa que no encontró COM7 y sigue con 10 botones en la ventana.",
      queHacer: [
        "Busca a la derecha de la ventana el panel con 10 botones, del 0 al 9 (si no lo ves, agranda la ventana).",
        "Haz clic en uno: el brazo borra el dígito anterior y dibuja el nuevo con una línea amarilla. El 8 tarda unos 2 segundos; el 1, menos de medio.",
        "Para mover la cámara: la rueda del mouse acerca, Ctrl + arrastrar gira.",
        "Para terminar, cierra la ventana (o pulsa Detener aquí).",
      ],
      queDeberiasVer: "Aquí abajo: 'No se pudo abrir COM7' y 'Sigue sin ESP32: usa los botones 0-9 de la ventana', y por cada botón 'Dibujando el digito n...' y 'Listo.'",
      botonTexto: "Iniciar el brazo",
    }],
    "run-p2-mouse": ["p2-mouse", {
      titulo: "Dibuja un número con el mouse",
      queVaAPasar: "Se abre el programa de reconocimiento con un lienzo blanco en vez de la cámara. Tarda unos segundos en aparecer porque carga TensorFlow y la red ya entrenada.",
      queHacer: [
        "En la ventana grande, dibuja un dígito GRANDE con el clic izquierdo dentro del recuadro y suelta el mouse.",
        "Espera un momento: las esquinas pasan a ámbar mientras vota y a verde cuando aparece 'DIGITO CONFIRMADO' arriba a la izquierda, con el número grande.",
        "La ventana chica 'Digito procesado' muestra la imagen de 28x28 que de verdad ve la red.",
        "Clic derecho o la tecla c borra para dibujar otro. La tecla q (o cerrar la ventana) termina.",
      ],
      queDeberiasVer: "Aquí abajo: 'No se encontro el ESP-A en COM7: el reconocimiento sigue...' y 'Modelo cargado'. En la ventana, abajo, 'ESP-A: no conectado' en rojo: es lo normal sin la placa.",
      botonTexto: "Abrir el lienzo",
    }],
    "run-p2-camara": ["p2-camara", {
      titulo: "Reconocer con la cámara",
      queVaAPasar: "Se enciende la cámara del PC y se abre la ventana del reconocimiento con un recuadro en el centro. Si la cámara no abre, el programa pasa solo al lienzo del mouse.",
      queHacer: [
        "Muestra la hoja con el dígito dentro del recuadro, quieta y con buena luz.",
        "Cuando el dígito gana 12 de 15 cuadros aparece confirmado arriba a la izquierda, igual que con el mouse.",
        "La tecla q termina (o cierra la ventana).",
      ],
      queDeberiasVer: "El dígito confirmado con sus dos barras (votos y confianza) y la ventana 'Digito procesado' con lo que ve la red.",
      botonTexto: "Encender la cámara",
    }],
    "run-p2-entrenar": ["p2-entrenar", {
      titulo: "Volver a entrenar la red (sobrescribe el modelo)",
      queDeberiasVer: "Una línea por cada una de las 10 pasadas (épocas) con su precisión, que debería terminar cerca del 99 %. Al final se guarda el modelo nuevo.",
      botonTexto: "Entrenar de nuevo (varios minutos)",
    }],
    "run-p2-probar-esp-a": ["p2-probar-esp-a", {
      titulo: "Probar el ESP-A solo",
      queVaAPasar: "Abre COM7, muestra lo que el ESP-A imprime al arrancar, le manda DIGIT:5 y muestra todo lo que conteste durante 5 segundos. Termina solo.",
      queDeberiasVer: "Con la placa: '(arranque) -> ESP-A listo...' y '<- recibido: REENVIADO:5', y un 5 en la OLED. Sin la placa: 'No se pudo abrir COM7' y termina con error; es lo esperado.",
      botonTexto: "Probar el ESP-A",
    }],
  };
  Object.entries(paneles).forEach(([elId, [accion, opciones]]) => {
    const el = document.getElementById(elId);
    if (!el) return;
    if (tieneApp("panelEjecucion")) {
      try { App.panelEjecucion(el, accion, opciones); }
      catch (e) { el.innerHTML = '<div class="t8-sin-api">No se pudo preparar este botón: ' + String(e.message || e) + "</div>"; }
    } else {
      el.innerHTML = '<div class="t8-sin-api">Este botón funciona cuando la app se abre con doble clic en <b>ABRIR.bat</b> (dentro de la carpeta del tema 8).</div>';
    }
  });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", arrancar);
else arrancar();
