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
    // Sin tildes, igual que el programa ("enciéndeme" tiene que coincidir con "enciend").
    const t = texto.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
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

  // ---------------------------- Recorrido animado (paso Pruébalo) ----------------------------
  // Cada frase recorre las cinco etapas voz -> texto -> intención -> orden -> LED. Las etapas se
  // encienden una tras otra (con un "paquete" que viaja por la flecha) para que se vea el camino.
  // Todo va en una cola: si llegan dos frases seguidas, la segunda espera a que termine la primera.
  // Al recargar la página con el programa ya en marcha, el lanzador vuelve a mandar toda la salida
  // vieja de golpe: esas vueltas se dibujan sin pausas (rapido) para no repetir la animación de cada una.
  const t0Pagina = Date.now();
  const pausa = (ms) => dormir(Date.now() - t0Pagina < 2500 ? 0 : ms);
  const recorrido = {
    cola: Promise.resolve(),
    encolar(f) { this.cola = this.cola.then(f).catch((e) => console.warn(e)); return this.cola; },
    etapa(n) { return document.querySelector(`#recorrido .etapa[data-e="${n}"]`); },
    flechaTras(n) { const e = this.etapa(n); return e && e.nextElementSibling && e.nextElementSibling.classList.contains("flecha") ? e.nextElementSibling : null; },
    poner(n, estado, valorHtml, exp) {
      const e = this.etapa(n); if (!e) return;
      e.classList.remove("activa", "hecha", "nula");
      if (estado) e.classList.add(estado);
      if (valorHtml != null) $("eVal-" + n).innerHTML = valorHtml;
      if (exp != null && $("eExp-" + n)) $("eExp-" + n).textContent = exp;
    },
    async pasar(n) {
      // La etapa n queda hecha y el paquete viaja por la flecha hacia la siguiente.
      this.poner(n, "hecha");
      const f = this.flechaTras(n);
      if (f) { f.classList.remove("viaja"); void f.offsetWidth; f.classList.add("viaja", "paso"); }
      await pausa(380);
    },
    limpiar() {
      for (const n of ["voz", "texto", "intencion", "orden"]) this.poner(n, null, "—");
      this.poner("led", null);
      document.querySelectorAll("#recorrido .flecha").forEach((f) => f.classList.remove("viaja", "paso"));
    },
    // Llega una frase (escrita, o ya transcrita si fue por voz).
    inicio(frase, porVoz) {
      return this.encolar(async () => {
        if (!porVoz) {
          this.limpiar();
          this.poner("voz", "activa", "⌨ Escrita", "Modo texto: no se usa el micrófono.");
          await pausa(260);
        }
        await this.pasar("voz");
        this.poner("texto", "activa", `"${esc(frase)}"`, porVoz ? "Google la transcribió (es-CO)." : "Ya viene escrita: no hay que transcribir.");
        await pausa(260);
        await this.pasar("texto");
        this.poner("intencion", "activa", '<span class="pensando">el programa la interpreta</span>', "Esperando la respuesta de comando_voz.py");
      });
    },
    escuchando() {
      return this.encolar(async () => {
        this.limpiar();
        this.poner("voz", "activa", "🎙 Escuchando", "Habla ahora: graba hasta que haya silencio.");
      });
    },
    // El programa terminó la vuelta: JSON, orden (o nada) y LEDs.
    fin({ json, origen, orden, sinEsp, alAplicar }) {
      return this.encolar(async () => {
        this.poner("intencion", "activa", esc(json || "{}"), "Según " + origen + (orden ? "." : ": nada sobre los LEDs."));
        await pausa(420);
        if (!orden) {
          this.poner("intencion", "hecha");
          this.poner("orden", "nula", "—", "No se manda nada: la frase no habla de los LEDs.");
          // Se dibuja el estado que tienen ahora (no lo que quedó de la frase anterior,
          // que tras un SHOW seguiría parpadeando aquí).
          this.poner("led", "nula", bulbos((leds.rojo ? "1" : "0") + (leds.azul ? "1" : "0")), "Siguen como estaban.");
          return;
        }
        await this.pasar("intencion");
        this.poner("orden", "activa", orden, orden === "SHOW" ? "Show de luces: alterna 2,4 s y vuelve."
          : `Primer carácter = rojo, segundo = azul (1 = prendido).`);
        await pausa(420);
        await this.pasar("orden");
        this.poner("led", "activa", bulbos(orden), sinEsp ? "Sin ESP32: se dibuja aquí (no hay cable)." : "Esperando la respuesta del ESP32…");
        if (alAplicar) alAplicar();
        await pausa(orden === "SHOW" ? 2500 : 450);
        this.poner("led", "hecha", bulbos(orden));
      });
    },
    respuestaEsp(texto) { this.encolar(async () => { this.poner("led", "hecha", null, "El ESP32 contestó: " + texto); }); },
  };

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
        recorrido.fin({ json, origen, orden, sinEsp: st.sinEsp, alAplicar: () => aplicarOrden(orden) });
        // El modo texto nunca "termina bien" (sigue esperando frases): el checklist se marca
        // aquí, cuando el programa real ya armó una orden (y el show, si fue SHOW).
        marcarPide(/^Orden al ESP32/);
        if (orden === "SHOW") marcarPide(/^Extra: show/);
      } else {
        html += "<div>Eso no tiene que ver con los LEDs, así que no hice nada.</div>";
        st.ultimaBot = burbuja("bot nada", html);
        recorrido.fin({ json, origen, orden: null });
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
      recorrido.inicio(texto, false);
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
      } else if (/^(Escribe el comando|Enter = hablar)/.test(l)) {
        // El programa terminó de arrancar y espera la primera frase.
        marcarListo(accionId);
      } else if ((m = l.match(/^Se entendio:\s*(.*)$/))) { st.vozTexto = m[1]; st.vozDeVoz = true; recorrido.inicio(m[1], true); }
      else if (l.startsWith("Habla ahora")) { burbuja("sistema", "🎙 Escuchando… habla ahora."); recorrido.escuchando(); }
      else if (l.startsWith("No se logro entender")) burbuja("sistema", "No se entendió el audio. Inténtalo de nuevo.");
      else if ((m = l.match(/^DeepSeek respondio:\s*(.*)$/))) { st.json = m[1]; st.deepseek = true; }
      else if (l.startsWith("Fallo la consulta a DeepSeek")) st.fallo = "DeepSeek no respondió; se usaron las palabras clave.";
      else if (l.startsWith("[sin ESP32]")) st.sinEsp = true;
      else if ((m = l.match(/^Estado enviado al ESP32:\s*([01]{2})/))) cerrarVuelta(m[1]);
      else if (l.startsWith("Enviando show de luces")) cerrarVuelta("SHOW");
      else if (l.startsWith("El comando no tenia relacion")) cerrarVuelta(null);
      else if ((m = l.match(/^ESP32 dice:\s*(.*)$/)) && st.ultimaBot) {
        st.ultimaBot.insertAdjacentHTML("beforeend", `<div class="nota">ESP32 contestó: <code>${esc(m[1])}</code></div>`);
        recorrido.respuestaEsp(m[1]);
      }
    }
    return { st, linea, anotar };
  }

  // Checklist de "Qué pide la actividad" (en Qué hace y en Resultados).
  const checklists = [];
  function marcarPide(re) {
    const p = ((window.App && App.practica && App.practica.pide) || []).find((x) => re.test(x));
    if (p) checklists.forEach((c) => c && c.marcar(p));
  }

  // ---------------------------- Integración con la API común ----------------------------
  const lectores = { texto: crearLector("texto"), voz: crearLector("voz") };
  const corriendo = { texto: false, voz: false };
  const listo = { texto: false, voz: false };
  const esperasListo = { texto: [], voz: [] };
  const ctls = {};

  // ---------------------------- Arranque: barra de carga y chip de estado ----------------------------
  // El programa suele tardar ~3 s en arrancar (el lanzador revisa el entorno y Python importa openai,
  // pyserial y SpeechRecognition). La primera vez, además, se crea el entorno e instala paquetes (1-3 min).
  const ARRANQUE_S = 3;
  let relojArranque = null;
  function chip(estado, texto) {
    const c = $("chipAsist"); if (!c) return;
    c.dataset.estado = estado; $("chipTxt").textContent = texto;
  }
  function mostrarArranque(modo) {
    const caja = $("arranque"); if (!caja) return;
    clearInterval(relojArranque);
    caja.hidden = false; caja.classList.remove("listo", "indeterminada");
    const t0 = Date.now();
    if (modo === "entorno") {
      caja.classList.add("indeterminada");
      $("arrTxt").textContent = "Preparando el entorno de Python (solo la primera vez: 1-3 min; el progreso de pip sale en el panel)…";
      chip("arrancando", "Preparando el entorno…");
    } else {
      $("arrTxt").textContent = "Arrancando el asistente… suele tardar ~" + ARRANQUE_S + " s";
      chip("arrancando", "Arrancando el asistente…");
    }
    const pintar = () => {
      const s = (Date.now() - t0) / 1000;
      $("arrTiempo").textContent = modo === "entorno" ? `lleva ${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`
        : `lleva ${s.toFixed(1)} s de ~${ARRANQUE_S} s`;
      if (modo !== "entorno") $("arrBarra").style.width = Math.min(92, (s / ARRANQUE_S) * 92) + "%";
    };
    pintar(); relojArranque = setInterval(pintar, 200);
  }
  function ocultarArranque(ok) {
    clearInterval(relojArranque);
    const caja = $("arranque"); if (!caja || caja.hidden) return;
    if (ok) {
      caja.classList.remove("indeterminada"); caja.classList.add("listo");
      $("arrBarra").style.width = "100%"; $("arrTxt").textContent = "¡Listo! El asistente espera tu frase.";
      setTimeout(() => { caja.hidden = true; }, 1600);
    } else caja.hidden = true;
  }
  function marcarListo(id) {
    listo[id] = true;
    ocultarArranque(true);
    chip("listo", id === "voz" ? "Asistente con micrófono en marcha" : "Asistente en marcha (modo texto)");
    esperasListo[id].splice(0).forEach((r) => r(true));
  }

  function marcarEstado(id, estado) {
    const e = String(estado && (estado.estado || estado) || "");
    corriendo[id] = e === "lanzada";
    if (e === "preparando" || e === "instalando") { listo[id] = false; mostrarArranque(e === "instalando" ? "entorno" : "normal"); }
    else if (e === "lanzada") { if (!listo[id] && $("arranque").hidden) mostrarArranque("normal"); }
    else if (["terminada", "detenida", "error"].includes(e)) {
      listo[id] = false; ocultarArranque(false);
      esperasListo[id].splice(0).forEach((r) => r(false));
      const otro = id === "texto" ? "voz" : "texto";
      if (!corriendo[otro]) chip(e === "error" ? "error" : "parado", e === "error" ? "El asistente no arrancó (mira el panel)" : "Asistente detenido");
    }
  }
  function esperarListo(id, ms) {
    if (listo[id]) return Promise.resolve(true);
    return new Promise((r) => { esperasListo[id].push(r); setTimeout(() => r(false), ms); });
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

  // Botones de frases: si el asistente no está en marcha, se arranca solo; luego la frase se
  // "teclea" sola en la caja y se le manda al programa.
  let escribiendo = false;
  async function decir(frase) {
    if (escribiendo) return;
    escribiendo = true;
    document.querySelectorAll(".frase-btn").forEach((b) => { b.disabled = true; });
    const panel = $("panelTexto");
    try {
      if (!listo.texto) {
        if (!corriendo.texto && ctls.texto) ctls.texto.iniciar();
        if (!(await esperarListo("texto", 240000))) {
          aviso("El asistente no llegó a arrancar: mira el panel de abajo (Lo que dice el programa).", "error");
          return;
        }
        await dormir(150);
      }
      const caja = cajaDe(panel);
      if (caja) {
        caja.value = "";
        for (const c of frase) { caja.value += c; caja.dispatchEvent(new Event("input", { bubbles: true })); await dormir(24); }
        await dormir(150);
      }
      lectores.texto.anotar(frase, false);
      // Que se vea el recorrido de la frase (el foco de la caja puede haber movido la página).
      const rec = $("recorrido"), r = rec.getBoundingClientRect();
      if (r.top < 60 || r.bottom > innerHeight) rec.scrollIntoView({ behavior: "smooth", block: "start" });
      await App.entrada("texto", frase);
      if (caja) { caja.value = ""; caja.dispatchEvent(new Event("input", { bubbles: true })); }
      // Deja terminar la animación del recorrido antes de aceptar otra frase.
      await recorrido.cola;
    } catch (err) {
      aviso("No se pudo mandar la frase: " + (err && err.message || err), "error");
    } finally {
      escribiendo = false;
      document.querySelectorAll(".frase-btn").forEach((b) => { b.disabled = false; });
    }
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
    ctls[accionId] = r;
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
    $("btnReadme").onclick = () => (window.App ? App.abrir("README.md") : null);
    // Al volver a una página con el asistente ya en marcha, el panel común enfoca su caja de texto y el
    // navegador baja hasta la consola: en los primeros segundos se vuelve arriba (al recorrido).
    document.addEventListener("focusin", (ev) => {
      if (Date.now() - t0Pagina < 4000 && ev.target.closest && ev.target.closest("#panelTexto")) {
        requestAnimationFrame(() => window.scrollTo({ top: 0 }));
      }
    });

    if (!window.App) {
      document.body.insertAdjacentHTML("afterbegin", '<p class="aviso-suave" style="margin:1rem">Esta página se abre con el '
        + "acceso directo <b>ABRIR.bat</b> de la carpeta de la práctica (así puede arrancar el programa).</p>");
      return;
    }
    try { await App.iniciar(); } catch (e) { aviso("No se pudo hablar con el lanzador: " + (e.message || e), "error"); }
    let pasos = null;
    try { pasos = App.pasos($("pasos")); } catch (e) { console.warn(e); }
    // "Probar" lleva al paso Pruébalo (el 4.º) desde cualquier parte.
    const irProbar = () => { if (pasos) pasos.ir(3); };
    $("btnIrProbar").onclick = irProbar;
    $("btnPortadaProbar").onclick = irProbar;
    try { checklists.push(App.checklist($("checklist")), App.checklist($("checklist2"))); } catch (e) { console.warn(e); }
    panel("panelTexto", "texto", {
      titulo: "El asistente, en modo texto",
      botonTexto: "Iniciar el asistente",
      queVaAPasar: "Arranca comando_voz.py sin micrófono, sin clave de DeepSeek y sin ESP32 (~3 s). "
        + "Entiende las frases con sus reglas por palabras clave y dice qué orden le habría mandado al ESP32.",
      queHacer: "Toca una frase de ejemplo (arriba) o escribe la tuya en la caja y pulsa Enter. "
        + "Para terminar: escribe salir o pulsa Detener.",
      queDeberiasVer: "",
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
