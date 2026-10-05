/* Consola de mando del tema 9.
   Usa la API común (window.App, de /comun/app.js) para correr las simulaciones y mostrar su
   salida dentro de la página; lo propio de esta app es el teclado 4x4 interactivo con lo que
   hace cada tecla en cada simulación y el resumen de la prueba rápida de los drones. */
(function () {
  "use strict";

  // Carpeta de la práctica: sale de la URL /app/<carpeta>/ (así la app no depende del nombre).
  const partes = location.pathname.split("/").filter(Boolean);
  const CARPETA = partes[0] === "app" && partes[1] ? decodeURIComponent(partes[1]) : "9-taller-segundo-corte";
  const REPO = "/repo/" + encodeURIComponent(CARPETA) + "/";
  const repo = (rel) => REPO + rel.split("/").map(encodeURIComponent).join("/");

  // ------------------------------------------------------------------------------------------
  // Qué hace cada tecla (sacado de Mando.tecla, procesar_tecla y los botones de cada script).
  // tipo: jog | golpe | sostener | objetivo | nada ; boton: nombre del botón en la ventana.
  // ------------------------------------------------------------------------------------------
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

  function dato(sim, k) { return MAPA[sim][k] || NADA; }
  function esc(s) { return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }

  function pintarTeclado() {
    const cont = document.getElementById("teclado");
    if (!cont) return;
    cont.innerHTML = "";
    const colorSim = { drones: "var(--c9-drones)", baxter: "var(--c9-baxter)", atlas: "var(--c9-atlas)" }[simActual];
    cont.style.setProperty("--sim", colorSim);
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
    const nota = document.getElementById("nota-sim");
    if (nota) nota.textContent = NOTA_SIM[simActual];
    pintarDetalle();
  }

  function pintarDetalle() {
    const det = document.getElementById("detalle");
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
      if (b.dataset.k === k) {
        b.classList.add("pulso");
        setTimeout(() => b.classList.remove("pulso"), 120);
      }
    });
    pintarDetalle();
  }

  function elegirSim(sim) {
    simActual = sim;
    document.querySelectorAll("#pestanas button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.sim === sim)));
    pintarTeclado();
  }

  // Teclas del PC: solo cuando el teclado dibujado está a la vista (paso 2) y no se escribe en una caja.
  document.addEventListener("keydown", (ev) => {
    const t = ev.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
    const cont = document.getElementById("teclado");
    if (!cont || cont.offsetParent === null) return;
    const k = ev.key.length === 1 ? ev.key.toUpperCase() : "";
    if (k && FILAS.flat().includes(k)) elegirTecla(k);
  });

  // ------------------------------------------------------------------------------------------
  // Medios: imágenes y videos se piden a /repo/ (el servidor del lanzador sirve el repo).
  // ------------------------------------------------------------------------------------------
  function cargarMedios() {
    document.querySelectorAll("[data-src]").forEach((el) => {
      el.src = repo(el.dataset.src);
      if (el.tagName === "VIDEO" && el.autoplay) el.play && el.play().catch(() => {});
    });
    document.querySelectorAll("img[data-src]").forEach((img) => {
      try { if (window.App && App.imagen) App.imagen(img); } catch (e) { /* sin ampliar: no es grave */ }
    });
    const marco = document.getElementById("marco-preview");
    if (marco) { marco.src = repo("preview.html"); escalarPreview(); }
  }

  // El preview pasa a una sola columna por debajo de 1100 px: se dibuja a 1240 px y se escala
  // al ancho del recuadro para que se vea como en una pantalla grande (en el celular, sin escalar).
  function escalarPreview() {
    const env = document.getElementById("env-preview");
    const marco = document.getElementById("marco-preview");
    if (!env || !marco) return;
    const ajustar = () => {
      const w = env.clientWidth;
      if (!w) return;
      const s = w >= 640 ? Math.min(1, w / 1240) : 1;
      const anchoReal = s < 1 ? 1240 : w;
      marco.style.width = anchoReal + "px";
      marco.style.height = (env.clientHeight / s) + "px";
      marco.style.transform = s < 1 ? "scale(" + s + ")" : "none";
    };
    ajustar();
    if (window.ResizeObserver) new ResizeObserver(ajustar).observe(env);
  }

  function abrir(rel) {
    const url = repo(rel);
    if (window.App && App.abrir) { try { return App.abrir(rel); } catch (e) { /* cae al plan B */ } }
    window.open(url, "_blank", "noopener");
  }

  async function cargarFirmware() {
    const pre = document.getElementById("codigo-firmware");
    if (!pre) return;
    try {
      const r = await fetch(repo("esp32_teclado.py"));
      pre.textContent = r.ok ? await r.text() : "No se pudo leer el archivo (está en la carpeta del tema 9 como esp32_teclado.py).";
    } catch (e) {
      pre.textContent = "No se pudo leer el archivo (está en la carpeta del tema 9 como esp32_teclado.py).";
    }
  }

  // ------------------------------------------------------------------------------------------
  // Navegación entre pasos (los botones de la portada y las tarjetas de cada simulación).
  // ------------------------------------------------------------------------------------------
  let asistente = null;
  function irAPaso(n) {
    const i = Number(n) - 1;
    const secciones = document.querySelectorAll("#pasos > section.paso");
    if (asistente && typeof asistente.ir === "function") { asistente.ir(i); }
    else if (asistente && typeof asistente.irA === "function") { asistente.irA(i); }
    else if (secciones[i]) {
      // Sin el asistente: se muestran todos los pasos y basta con bajar hasta el que toca.
      secciones[i].hidden = false;
    }
    const s = secciones[i];
    if (s) setTimeout(() => s.scrollIntoView({ behavior: "smooth", block: "start" }), 30);
  }

  // ------------------------------------------------------------------------------------------
  // Prueba rápida de drones: además del panel "Lo que dice el programa", se resume en 4 casillas.
  // ------------------------------------------------------------------------------------------
  function resumenDrones(linea) {
    const caja = document.getElementById("ruta-drones");
    if (!caja || typeof linea !== "string") return;
    const m = linea.match(/Llego a ([ABC]) a los ([\d.]+) s/);
    if (m) {
      const c = caja.querySelector('[data-p="' + m[1] + '"]');
      if (c) { c.classList.add("llego"); c.querySelector("span").textContent = "llegó a los " + m[2].replace(".", ",") + " s"; }
    }
    const inc = linea.match(/inclinacion_max_grados['"]?\s*:\s*([\d.]+)/);
    if (inc) caja.dataset.inclinacion = inc[1];
    if (/PRUEBA OK/.test(linea) || /PRUEBA FALLIDA/.test(linea)) {
      const ok = /PRUEBA OK/.test(linea);
      const c = caja.querySelector('[data-p="OK"]');
      c.classList.toggle("llego", ok);
      c.classList.toggle("falla", !ok);
      c.querySelector("b").textContent = ok ? "PRUEBA OK" : "FALLÓ";
      c.querySelector("span").textContent = caja.dataset.inclinacion
        ? "inclinación máxima " + Number(caja.dataset.inclinacion).toFixed(1).replace(".", ",") + "°"
        : (ok ? "las tres llegadas" : "mira lo que dice el programa");
    }
  }
  function reiniciarResumenDrones() {
    const caja = document.getElementById("ruta-drones");
    if (!caja) return;
    caja.querySelectorAll("div").forEach((d) => {
      d.classList.remove("llego", "falla");
      d.querySelector("span").textContent = d.dataset.p === "OK" ? "corriendo…" : "esperando";
      if (d.dataset.p === "OK") d.querySelector("b").textContent = "Resultado";
    });
    delete caja.dataset.inclinacion;
  }

  // Los textos "Qué va a pasar / Qué hacer / Qué deberías ver" están escritos en el HTML (así se
  // leen aunque la página se abra sin el lanzador); con el lanzador se le pasan al panel común,
  // que los muestra junto al botón Iniciar, y se quita la copia del HTML para no repetirlos.
  function textosDelBloque(el) {
    const bloque = el.closest(".c9-prueba");
    const que = bloque && bloque.querySelector(".c9-que");
    if (!que) return {};
    const partes = [...que.children].map((d) => {
      const c = d.cloneNode(true);
      const b = c.querySelector(":scope > b"); if (b) b.remove();
      const span = document.createElement("div");
      span.className = "c9-texto-panel";
      span.innerHTML = c.innerHTML;
      return span;
    });
    que.remove();
    return { queVaAPasar: partes[0], queHacer: partes[1], queDeberiasVer: partes[2] };
  }

  const paneles = {};
  function montarPaneles() {
    document.querySelectorAll("[data-panel]").forEach((el) => {
      const id = el.dataset.panel;
      const opciones = textosDelBloque(el);
      if (id === "drones-prueba") {
        let enMarcha = false;
        opciones.alLinea = resumenDrones;
        opciones.alEstado = (t) => {
          const e = (t && t.estado) || "";
          const activo = ["preparando", "instalando", "lanzada"].includes(e);
          if (activo && !enMarcha) reiniciarResumenDrones();
          enMarcha = activo;
        };
      }
      try {
        paneles[id] = App.panelEjecucion(el, id, opciones);
      } catch (e) {
        el.innerHTML = '<p class="c9-nota">No se pudo armar este botón: ' + esc(e && e.message ? e.message : e) + "</p>";
      }
    });
  }

  // ------------------------------------------------------------------------------------------
  // Arranque
  // ------------------------------------------------------------------------------------------
  async function iniciar() {
    document.querySelectorAll("#pestanas button").forEach((b) => b.addEventListener("click", () => elegirSim(b.dataset.sim)));
    pintarTeclado();
    document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => irAPaso(b.dataset.ir)));
    document.querySelectorAll("[data-abrir]").forEach((b) => b.addEventListener("click", () => abrir(b.dataset.abrir)));
    const bp = document.getElementById("abrir-preview");
    if (bp) bp.addEventListener("click", () => abrir("preview.html"));

    if (!window.App) {
      document.getElementById("sinapp").style.display = "block";
      cargarMedios();
      cargarFirmware();
      document.getElementById("checklist").innerHTML = '<p class="c9-intro">Ábrela desde ABRIR.bat para ver y marcar la lista.</p>';
      return;
    }
    try { await App.iniciar(); } catch (e) {
      document.getElementById("sinapp").style.display = "block";
    }
    cargarMedios();
    cargarFirmware();
    // La misma lista sale en la portada y en el último paso: si se marca a mano en una, se
    // vuelve a dibujar la otra (las dos leen lo guardado en el navegador).
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
      App.markdown(document.getElementById("md-protocolo"), "README.md",
        { desde: "## El protocolo `TECLA:x` y cómo lo lee el PC", hasta: "## Conexiones" });
    } catch (e) { /* solo es un extra plegado */ }
    try { asistente = App.pasos(document.getElementById("pasos")); } catch (e) { asistente = null; }
    // Para las pruebas automáticas (captura con Chrome): paneles e ir a un paso.
    window.Consola9 = { paneles, irAPaso };
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
