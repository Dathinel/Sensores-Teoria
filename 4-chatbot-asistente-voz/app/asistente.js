// App del tema 4: el asistente de voz que prende dos LEDs.
// Usa la API común de /comun/app.js (window.App). Lo propio de esta práctica:
//  - lee lo que imprime comando_voz.py ("[sin ESP32] se habria enviado: 10", "Enviando show de luces",
//    "El comando no tenia relacion...") y lo convierte en una conversación y en dos LEDs dibujados;
//  - botones de frases de ejemplo que se escriben solas en la caja y se le mandan al programa;
//  - la tabla de ejemplos de "Cómo funciona", calculada con las mismas reglas del programa.
(function () {
  "use strict";
  const CARPETA = "4-chatbot-asistente-voz";
  const $ = (id) => document.getElementById(id);
  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

  // ---------------------------------------------------------------------------------------------
  // Copia exacta del plan B de comando_voz.py (interpretar_por_reglas). En modo texto el programa
  // corre con --sin-clave, así que esta copia da el mismo JSON que el programa usó por dentro
  // (el programa no lo imprime en ese modo; con DeepSeek sí, y entonces se muestra el suyo).
  // ---------------------------------------------------------------------------------------------
  function interpretarPorReglas(texto) {
    const t = texto.toLowerCase();
    const datos = {};
    if (["show", "espectaculo", "espectáculo", "parpade", "fiesta"].some((p) => t.includes(p))) {
      datos.show = true; return datos;
    }
    const partes = t.split(/,|\by\b|\be\b|\bpero\b|\bluego\b|\bdespues\b|después/);
    let valor = null;
    for (const parte of partes) {
      if (["deja", "manten", "mantén"].some((p) => parte.includes(p))) { valor = null; continue; }
      if (["apaga", "desactiva", "quita"].some((p) => parte.includes(p))) valor = false;
      else if (["enciend", "prend", "activa", "pon", "dale"].some((p) => parte.includes(p))) valor = true;
      if (valor === null) continue;
      const ambos = ["los dos", "ambos", "todo", "todas"].some((p) => parte.includes(p));
      if (ambos || parte.includes("roj")) datos.led_rojo = valor;
      if (ambos || parte.includes("azul")) datos.led_azul = valor;
    }
    return datos;
  }

  const bulbos = (orden) => {
    if (orden === "SHOW") return '<span class="par show-demo"><i class="bulbo rojo"></i><i class="bulbo azul"></i></span>';
    return `<span class="par"><i class="bulbo rojo${orden[0] === "1" ? " on" : ""}"></i><i class="bulbo azul${orden[1] === "1" ? " on" : ""}"></i></span>`;
  };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  // ---------------------------- Tabla de ejemplos (paso 2) ----------------------------
  function llenarTablaEjemplos() {
    const frases = ["enciende el rojo", "prende también el azul", "apaga el rojo pero deja el azul", "haz un show de luces",
      "enciende el rojo y apaga el azul", "apaga todo", "¿qué hora es?"];
    const est = { r: false, a: false };
    $("tablaEjemplos").innerHTML = frases.map((f) => {
      const d = interpretarPorReglas(f);
      let orden;
      if (!Object.keys(d).length) orden = null;
      else if (d.show) orden = "SHOW";
      else {
        if ("led_rojo" in d) est.r = d.led_rojo;
        if ("led_azul" in d) est.a = d.led_azul;
        orden = (est.r ? "1" : "0") + (est.a ? "1" : "0");
      }
      return `<tr><td>"${esc(f)}"</td><td><code>${esc(JSON.stringify(d))}</code></td>`
        + `<td>${orden ? `<code>${orden}</code>` : "<span class='nota'>no manda nada</span>"}</td>`
        + `<td>${orden ? bulbos(orden) + (orden === "SHOW" ? " <span class='nota'>y vuelven como estaban</span>" : "") : "—"}</td></tr>`;
    }).join("");
  }

  // ---------------------------- LEDs dibujados ----------------------------
  const leds = { rojo: false, azul: false, enShow: false, colaShow: Promise.resolve() };
  function pintar(r, a) {
    $("gRojo").classList.toggle("on", !!r);
    $("gAzul").classList.toggle("on", !!a);
  }
  function aplicarOrden(orden) {
    $("gOrden").textContent = orden;
    // Igual que el ESP32: atiende una orden a la vez; lo que llegue durante el show espera.
    leds.colaShow = leds.colaShow.then(async () => {
      if (orden === "SHOW") {
        leds.enShow = true;
        for (let i = 0; i < 6; i++) { pintar(1, 0); await dormir(200); pintar(0, 1); await dormir(200); }
        leds.enShow = false;
      } else if (/^[01][01]$/.test(orden)) {
        leds.rojo = orden[0] === "1"; leds.azul = orden[1] === "1";
      }
      pintar(leds.rojo, leds.azul);
    });
  }
  function reiniciarLeds() {
    leds.rojo = false; leds.azul = false; pintar(0, 0); $("gOrden").textContent = "—";
  }

  // ---------------------------- Conversación ----------------------------
  function burbuja(clase, html) {
    const chat = $("chat");
    const b = document.createElement("div");
    b.className = "burbuja " + clase;
    b.innerHTML = html;
    chat.appendChild(b);
    chat.scrollTop = chat.scrollHeight;
    return b;
  }

  // Un "lector" por acción (texto o voz): junta las líneas de una vuelta del bucle de
  // comando_voz.py y, al llegar la línea que la cierra, dibuja la respuesta.
  function crearLector(accionId) {
    const st = { cola: [], vozTexto: null, json: null, deepseek: false, ultimaBot: null, fallo: null };
    function cerrarVuelta(orden) {
      const frase = st.vozTexto != null ? st.vozTexto : (st.cola.length ? st.cola.shift().texto : null);
      st.vozTexto = null;
      if (frase != null) burbuja("yo", `<span class="quien">Tú${accionId === "voz" && st.vozDeVoz ? " (por voz)" : ""}</span>${esc(frase)}`);
      st.vozDeVoz = false;
      let json = st.json;
      let origen = st.deepseek ? "DeepSeek" : "reglas por palabras clave";
      if (!json && frase != null) json = JSON.stringify(interpretarPorReglas(frase));
      st.json = null; st.deepseek = false;
      let html = `<span class="quien">Asistente · ${origen}</span>`;
      if (st.fallo) { html += `<div class="nota">${esc(st.fallo)}</div>`; st.fallo = null; }
      if (json) html += `<div class="fila-json">${esc(json)}</div>`;
      if (orden) {
        const texto = orden === "SHOW" ? "¡Show de luces! Alterno los LEDs 2,4 s y los dejo como estaban."
          : `Listo: rojo ${orden[0] === "1" ? "encendido" : "apagado"}, azul ${orden[1] === "1" ? "encendido" : "apagado"}.`;
        html += `<div>${texto}</div><div class="fila-orden">Orden <code>${orden}</code> ${bulbos(orden)}`
          + `<span class="nota">${st.sinEsp ? "(sin ESP32: solo se muestra)" : ""}</span></div>`;
        st.ultimaBot = burbuja("bot", html);
        aplicarOrden(orden);
      } else {
        html += "<div>Eso no tiene que ver con los LEDs, así que no hice nada.</div>";
        st.ultimaBot = burbuja("bot nada", html);
      }
      st.sinEsp = false;
    }
    // Anota una frase enviada. Puede llegar dos veces (al mandarla desde aquí y como eco "in"
    // del lanzador): se cuenta una sola.
    function anotar(texto, eco) {
      texto = String(texto || "").trim();
      if (!texto || texto.toLowerCase() === "salir") return;
      if (eco) {
        const p = st.cola.find((c) => !c.eco && c.texto === texto);
        if (p) { p.eco = true; return; }
      } else {
        const p = st.cola.find((c) => c.eco && !c.propio && c.texto === texto);
        if (p) { p.propio = true; return; }
      }
      st.cola.push({ texto, eco: !!eco, propio: !eco });
    }
    function linea(cruda, tipo) {
      if (tipo === "in") { anotar(cruda, true); return; }
      if (tipo === "pip" || tipo === "sis") return;
      let l = String(cruda).replace(/\r/g, "");
      while (l.startsWith("> ")) l = l.slice(2);
      l = l.replace(/^>\s*$/, "").trim();
      if (!l) return;
      let m;
      if (/^(--texto:|No se pudo abrir|ESP32 conectado en)/.test(l)) {
        // El programa acaba de arrancar: su estado empieza con los dos LEDs apagados.
        if (/^(No se pudo abrir|ESP32 conectado en)/.test(l)) {
          reiniciarLeds(); st.cola.length = 0; st.vozTexto = null;
          burbuja("sistema", l.startsWith("ESP32 conectado") ? "El programa arrancó y encontró el ESP32: las órdenes salen por el cable."
            : "El programa arrancó sin ESP32: las órdenes solo se muestran (y se dibujan aquí).");
        }
      } else if ((m = l.match(/^Se entendio:\s*(.*)$/))) { st.vozTexto = m[1]; st.vozDeVoz = true; }
      else if (l.startsWith("Habla ahora")) burbuja("sistema", "🎙 Escuchando… habla ahora.");
      else if (l.startsWith("No se logro entender")) burbuja("sistema", "No se entendió el audio. Inténtalo de nuevo.");
      else if ((m = l.match(/^DeepSeek respondio:\s*(.*)$/))) { st.json = m[1]; st.deepseek = true; }
      else if (l.startsWith("Fallo la consulta a DeepSeek")) st.fallo = "DeepSeek no respondió; se usaron las palabras clave.";
      else if (l.startsWith("[sin ESP32]")) st.sinEsp = true;
      else if ((m = l.match(/^Estado enviado al ESP32:\s*([01]{2})/))) cerrarVuelta(m[1]);
      else if (l.startsWith("Enviando show de luces")) cerrarVuelta("SHOW");
      else if (l.startsWith("El comando no tenia relacion")) cerrarVuelta(null);
      else if ((m = l.match(/^ESP32 dice:\s*(.*)$/)) && st.ultimaBot) {
        st.ultimaBot.insertAdjacentHTML("beforeend", `<div class="nota">ESP32 contestó: <code>${esc(m[1])}</code></div>`);
      }
    }
    return { st, linea, anotar };
  }

  // ---------------------------- Integración con la API común ----------------------------
  const lectores = { texto: crearLector("texto"), voz: crearLector("voz") };
  const corriendo = { texto: false, voz: false };

  function marcarEstado(id, estado) {
    const e = String(estado && (estado.estado || estado) || "");
    corriendo[id] = e === "lanzada";
  }

  // La caja de texto que pone panelEjecucion para las acciones con "entrada": true.
  const cajaDe = (panel) => panel.querySelector(".app-entrada input[type=text]");

  // Registra lo que el usuario escribe en la caja del panel (para saber a qué frase responde
  // cada vuelta del programa). Se escucha en fase de captura para verlo antes de que se borre.
  function vigilarCaja(panel, id) {
    panel.addEventListener("submit", () => {
      const caja = cajaDe(panel);
      if (caja) lectores[id].anotar(caja.value, false);
    }, true);
  }

  // Botones de frases: la frase se "teclea" sola en la caja y se le manda al programa.
  let escribiendo = false;
  async function decir(frase) {
    if (escribiendo) return;
    const panel = $("panelTexto");
    if (!corriendo.texto) {
      aviso("Primero pulsa «Iniciar» para arrancar el asistente; luego toca la frase.", "info");
      panel.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    escribiendo = true;
    const caja = cajaDe(panel);
    try {
      if (caja) {
        caja.value = "";
        for (const c of frase) { caja.value += c; caja.dispatchEvent(new Event("input", { bubbles: true })); await dormir(28); }
        await dormir(180);
      }
      lectores.texto.anotar(frase, false);
      await App.entrada("texto", frase);
      if (caja) { caja.value = ""; caja.dispatchEvent(new Event("input", { bubbles: true })); }
    } catch (err) {
      aviso("No se pudo mandar la frase: " + (err && err.message || err), "error");
    } finally { escribiendo = false; }
  }

  function aviso(texto, tipo) {
    if (window.App && App.aviso) App.aviso(texto, tipo); else alert(texto);
  }

  function crearBotonesFrases() {
    const frases = ["enciende el rojo", "prende los dos", "apaga el azul", "haz un show de luces",
      "enciende el rojo y apaga el azul", "apaga el rojo pero deja el azul", "apaga todo", "¿qué hora es?"];
    const cont = $("botonesFrases");
    cont.innerHTML = "";
    for (const f of frases) {
      const b = document.createElement("button");
      b.type = "button"; b.className = "frase-btn"; b.textContent = f;
      b.onclick = () => decir(f);
      cont.appendChild(b);
    }
    cont.insertAdjacentHTML("afterend", '<p class="nota">La última ("¿qué hora es?") no tiene que ver con los LEDs: '
      + "el asistente debe ignorarla. Para terminar el programa escribe <code>salir</code> o pulsa Detener.</p>");
  }

  function panel(elId, accionId, extra) {
    const el = $(elId);
    const opciones = Object.assign({
      alLinea: (x, tipo) => lectores[accionId] && lectores[accionId].linea(x, tipo),
      alEstado: (e) => marcarEstado(accionId, e),
    }, extra || {});
    const r = App.panelEjecucion(el, accionId, opciones);
    if (lectores[accionId]) vigilarCaja(el, accionId);
    return r;
  }

  async function iniciar() {
    llenarTablaEjemplos();
    crearBotonesFrases();
    const rutaRepo = (r) => `/repo/${CARPETA}/${r}`;
    $("simulador").src = rutaRepo("preview.html");
    $("abrirSim").onclick = () => App.abrir("preview.html");
    $("abrirReadme").onclick = () => App.abrir("README.md");

    if (!window.App) {
      document.body.insertAdjacentHTML("afterbegin", '<p class="aviso-suave" style="margin:1rem">Esta página se abre con el '
        + "acceso directo <b>ABRIR.bat</b> de la carpeta de la práctica (así puede arrancar el programa).</p>");
      return;
    }
    try { await App.iniciar(); } catch (e) { aviso("No se pudo hablar con el lanzador: " + (e.message || e), "error"); }
    try { App.pasos($("pasos")); } catch (e) { console.warn(e); }
    try { App.checklist($("checklist")); App.checklist($("checklist2")); } catch (e) { console.warn(e); }
    panel("panelTexto", "texto", {
      titulo: "El asistente, en modo texto",
      botonTexto: "Iniciar el asistente",
      queVaAPasar: "Arranca el programa real de la práctica sin micrófono, sin clave de DeepSeek y sin ESP32. "
        + "Entiende las frases con sus reglas por palabras clave y dice qué orden le habría mandado al ESP32.",
      queHacer: "Toca una frase de ejemplo (abajo) o escribe la tuya en la caja que aparece y pulsa Enter. "
        + "Para terminar: escribe salir o pulsa Detener.",
      queDeberiasVer: "En la conversación de la derecha, tu frase, el JSON que entendió y la orden (10, 01, 11, 00 o SHOW); "
        + "los LEDs dibujados se prenden igual que lo harían los de la protoboard.",
    });
    panel("panelVoz", "voz", {
      titulo: "El asistente con micrófono (y DeepSeek si pusiste la clave)",
      botonTexto: "Iniciar con micrófono",
      queVaAPasar: "Arranca el mismo programa, ahora con el micrófono. Si hay clave en el .env consulta a DeepSeek; "
        + "si no, usa las palabras clave. Si el ESP32 está conectado en COM7, la orden sale por el cable.",
      queHacer: "Envía la caja vacía (Enter) y habla cuando diga «Habla ahora...». También puedes escribir la frase.",
      queDeberiasVer: "«Se entendio: …» con tu frase, «DeepSeek respondio: {…}» si hay clave, y la orden. "
        + "Las respuestas también aparecen en la conversación y en los LEDs del paso Pruébalo.",
    });
    try { App.panelEjecucion($("panelFw"), "fw"); } catch (e) { console.warn(e); }
    document.querySelectorAll("img[data-ampliar]").forEach((img) => { try { App.imagen(img); } catch (e) { /* opcional */ } });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar); else iniciar();
})();
