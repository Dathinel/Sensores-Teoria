// App del tema 2: Thonny/MicroPython frente a C/C++ (Arduino).
// Lo común (pasos, checklist, imágenes ampliables, abrir Wokwi marcando la checklist) viene de
// /comun/app.js. Lo propio: el visor lado a lado con las ideas resaltadas en los dos códigos, el
// selector de lenguaje de cada ejemplo, copiar el código y la lista de instalación con memoria.
(function () {
  "use strict";

  const CARPETA = "2-lenguajes-thonny";
  const REPO = "/repo/" + CARPETA + "/";
  const A = () => window.App || null;
  const $ = (s) => document.querySelector(s);

  const ARCHIVOS = {
    "7seg": { mp: "siete_segmentos.py", cc: "siete_segmentos/siete_segmentos.ino" },
    semaforo: { mp: "semaforo_velocidad.py", cc: "semaforo_velocidad/semaforo_velocidad.ino" },
  };
  const WOKWI = { mp: "wokwi-mp", cc: "wokwi-c" };                       // acciones del probar.json
  const WOKWI_URL = { mp: "https://wokwi.com/projects/new/micropython-esp32", cc: "https://wokwi.com/projects/new/esp32" };
  const textos = {};

  // Cada idea del lado a lado: qué líneas la representan en cada lenguaje y una frase que la explica.
  const IDEAS = {
    traer: { cc: null, mp: /^from machine|^import /,
      txt: "C/C++: nada, el framework de Arduino ya trae pinMode y digitalWrite. MicroPython: hay que importar Pin del módulo machine." },
    declarar: { cc: /^const int s/, mp: /= Pin\(/,
      txt: "C/C++ guarda solo el número del pin en una constante; MicroPython crea un objeto Pin por segmento." },
    salida: { cc: /pinMode\(/, mp: /Pin\.OUT/,
      txt: "C/C++ lo hace aparte, dentro de setup(); en MicroPython ya va incluido al crear el Pin con Pin.OUT." },
    prender: { cc: /digitalWrite\(/, mp: /\.value\(/,
      txt: "digitalWrite(pin, HIGH) frente a pin.value(1): una función suelta contra un método del objeto." },
    repetir: { cc: /^void loop\(\)/, mp: /^while True:/,
      txt: "En Arduino, loop() lo repite el framework solo. En MicroPython el bucle se escribe a mano con while True." },
  };

  // ---------- resaltado mínimo, línea por línea (para poder marcar líneas) ----------
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  function colorear(linea, lenguaje) {
    const marca = lenguaje === "mp" ? "#" : "//";
    const i = linea.indexOf(marca);
    const codigo = i >= 0 ? linea.slice(0, i) : linea, com = i >= 0 ? linea.slice(i) : "";
    const PAL = lenguaje === "mp"
      ? /\b(from|import|while|True|False|for|in|range|print|def|return|if|else)\b/
      : /\b(const|int|long|unsigned|float|void|for|return|if|else|HIGH|LOW|OUTPUT)\b/;
    let c = esc(codigo).replace(/("[^"]*")/g, "\u0001$1\u0002");
    c = c.split(/(\u0001[^\u0002]*\u0002)/).map((trozo) => {
      if (trozo.startsWith("\u0001")) return '<span class="s">' + trozo.slice(1, -1) + "</span>";
      return trozo.replace(new RegExp(PAL.source, "g"), '<span class="k">$1</span>')
                  .replace(/\b(\d+)\b/g, '<span class="n">$1</span>');
    }).join("");
    return c + (com ? '<span class="c">' + esc(com) + "</span>" : "");
  }
  function pintarCodigo(pre, texto, lenguaje) {
    pre.innerHTML = texto.replace(/\s+$/, "").split("\n").map((l) =>
      '<span class="l" data-crudo="' + esc(l.trim()).replace(/"/g, "&quot;") + '">' + (colorear(l, lenguaje) || " ") + "</span>").join("");
  }

  async function leer(ruta) {
    if (!textos[ruta]) textos[ruta] = await (await fetch(REPO + ruta)).text();
    return textos[ruta];
  }

  // ---------- lado a lado ----------
  async function iniciarLadoALado() {
    try {
      pintarCodigo($("#cod7c"), await leer(ARCHIVOS["7seg"].cc), "cc");
      pintarCodigo($("#cod7p"), await leer(ARCHIVOS["7seg"].mp), "mp");
    } catch (e) {
      $("#cod7c").textContent = $("#cod7p").textContent = "No se pudo leer el código (está en GitHub).";
    }
    const elegir = (clave) => {
      document.querySelectorAll(".idea").forEach((b) => b.classList.toggle("activa", b.dataset.idea === clave));
      const idea = IDEAS[clave];
      $("#explicaIdea").textContent = idea.txt;
      for (const [pre, re] of [[$("#cod7c"), idea.cc], [$("#cod7p"), idea.mp]]) {
        let primera = null;
        pre.querySelectorAll(".l").forEach((l) => {
          const crudo = l.dataset.crudo, esCom = /^(#|\/\/)/.test(crudo);
          const si = !!re && !esCom && re.test(crudo);
          l.classList.toggle("marcada", si);
          if (si && !primera) primera = l;
        });
        if (primera) pre.scrollTo({ top: Math.max(0, primera.offsetTop - pre.clientHeight / 3), behavior: "smooth" });
      }
    };
    document.querySelectorAll(".idea").forEach((b) => {
      b.addEventListener("mouseenter", () => elegir(b.dataset.idea));
      b.addEventListener("click", () => elegir(b.dataset.idea));
    });
  }

  // ---------- ejemplos: lenguaje elegido, abrir Wokwi y copiar ----------
  const lenguajeDe = (ejemplo) => (document.querySelector('.selector-leng[data-ejemplo="' + ejemplo + '"]').closest(".paso").dataset.leng || "mp");
  function iniciarEjemplos() {
    document.querySelectorAll(".selector-leng").forEach((sel) => {
      const paso = sel.closest(".paso");
      let guardado = null;
      try { guardado = localStorage.getItem("tema2-leng-" + sel.dataset.ejemplo); } catch (e) { /* nada */ }
      const poner = (l) => {
        paso.dataset.leng = l;
        sel.querySelectorAll(".sl").forEach((b) => b.classList.toggle("activo", b.dataset.leng === l));
        try { localStorage.setItem("tema2-leng-" + sel.dataset.ejemplo, l); } catch (e) { /* nada */ }
      };
      sel.querySelectorAll(".sl").forEach((b) => b.addEventListener("click", () => poner(b.dataset.leng)));
      poner(guardado === "cc" ? "cc" : "mp");
    });
    document.querySelectorAll("[data-wokwi]").forEach((b) => b.addEventListener("click", () => {
      const l = lenguajeDe(b.dataset.wokwi);
      const app = A();
      // App.accion abre la pestaña en el mismo clic y marca en la checklist lo que "cubre" la acción.
      if (app && app.practica) { try { app.accion(WOKWI[l]); return; } catch (e) { /* abajo */ } }
      window.open(WOKWI_URL[l], "_blank", "noopener");
    }));
    document.querySelectorAll("[data-copiar]").forEach((b) => b.addEventListener("click", async () => {
      const ej = b.dataset.copiar, l = lenguajeDe(ej), ruta = ARCHIVOS[ej][l];
      try {
        await navigator.clipboard.writeText(await leer(ruta));
        aviso("Copiado " + ruta.split("/").pop() + ": pégalo en " + (l === "mp" ? "main.py" : "sketch.ino") + " de Wokwi.", "ok");
      } catch (e) {
        aviso("No se pudo copiar automáticamente. El archivo se abre en una pestaña: cópialo con Ctrl+A y Ctrl+C.", "info");
        window.open(REPO + ruta, "_blank", "noopener");
      }
    }));
  }

  // ---------- portada: el duelo animado ----------
  // Una carrera ilustrativa (no a escala) de lo que pasa en cada camino: C/C++ tarda en arrancar
  // (compilar y grabar) pero después cambia el pin muy rápido; MicroPython arranca al instante y
  // cada línea pasa por el intérprete, así que el LED cambia más despacio.
  const dormir = (ms) => new Promise((r) => setTimeout(r, ms));
  let carrera = 0;                                  // id de la reproducción en curso (para cortarla)
  function iniciarDuelo() {
    const duelo = $("#duelo"), boton = $("#bCorrer");
    if (!duelo || !boton) return;
    const lado = (cl) => {
      const el = duelo.querySelector(cl);
      return { pasos: Array.from(el.querySelectorAll(".tubo li")), barra: el.querySelector(".carril-barra div"),
               led: el.querySelector(".led-mini"), txt: el.querySelector(".carril-txt"),
               lineas: Array.from(el.querySelectorAll(".carril-cod span")), textoInicial: el.querySelector(".carril-txt").textContent };
    };
    const cc = lado(".lado-cc"), mp = lado(".lado-mp");
    const marcar = (l, i) => l.pasos.forEach((li, k) => { li.classList.toggle("activo", k === i); li.classList.toggle("hecho", k < i); });
    const llenar = async (l, ms, id) => {        // barra de 0 a 100 % en ms milisegundos
      const t0 = performance.now();
      while (carrera === id) {
        const f = Math.min(1, (performance.now() - t0) / ms);
        l.barra.style.width = (f * 100) + "%";
        if (f >= 1) return;
        await dormir(40);
      }
    };
    const parpadear = async (l, ms, total, id) => {
      const fin = performance.now() + total;
      while (carrera === id && performance.now() < fin) { l.led.classList.toggle("on"); await dormir(ms); }
    };
    const reiniciar = () => {
      duelo.classList.remove("jugando");
      for (const l of [cc, mp]) {
        l.pasos.forEach((li) => li.classList.remove("activo", "hecho"));
        l.led.classList.remove("on"); l.txt.textContent = l.textoInicial;
        if (l.barra) l.barra.style.width = "0";
        l.lineas.forEach((s) => s.classList.remove("leyendo"));
      }
      boton.textContent = "▶ Ver cómo corre cada uno";
    };
    async function correrCC(id) {
      marcar(cc, 0); cc.txt.textContent = "Escribes el programa completo…"; await dormir(700);
      if (carrera !== id) return;
      marcar(cc, 1); cc.txt.textContent = "Compilando TODO el programa…"; await llenar(cc, 2200, id);
      if (carrera !== id) return;
      marcar(cc, 2); cc.barra.style.width = "0"; cc.txt.textContent = "Grabando el binario en la flash…"; await llenar(cc, 1300, id);
      if (carrera !== id) return;
      marcar(cc, 3); cc.txt.textContent = "Corriendo: el LED cambia muy rápido";
      await parpadear(cc, 90, 5200, id);
      if (carrera === id) cc.txt.textContent = "Arrancó tarde (compilar y grabar), pero corre rápido.";
    }
    async function correrMP(id) {
      marcar(mp, 0); mp.txt.textContent = "El intérprete ya espera en la flash"; await dormir(500);
      if (carrera !== id) return;
      marcar(mp, 1); mp.txt.textContent = "F5: Thonny manda el .py por USB"; await dormir(600);
      if (carrera !== id) return;
      marcar(mp, 2);
      for (let vuelta = 0; vuelta < 4 && carrera === id; vuelta++) {
        for (let k = 0; k < mp.lineas.length && carrera === id; k++) {
          if (vuelta > 0 && k === 0) continue;               // el Pin se crea una sola vez
          mp.lineas.forEach((s, j) => s.classList.toggle("leyendo", j === k));
          mp.txt.textContent = "Leyendo e interpretando: " + mp.lineas[k].textContent;
          if (k === 1) mp.led.classList.add("on");
          if (k === 2) mp.led.classList.remove("on");
          await dormir(650);
        }
      }
      if (carrera !== id) return;
      mp.lineas.forEach((s) => s.classList.remove("leyendo"));
      marcar(mp, 3); mp.txt.textContent = "Arrancó al instante; cada línea pasa por el intérprete.";
    }
    let corriendo = false;
    boton.addEventListener("click", async () => {
      // Mientras corre, el botón detiene; al terminar, queda el estado final a la vista y el
      // siguiente clic vuelve a empezar.
      if (corriendo) { carrera++; corriendo = false; reiniciar(); return; }
      const id = ++carrera;
      reiniciar(); duelo.classList.add("jugando"); corriendo = true;
      boton.textContent = "■ Detener";
      await Promise.all([correrCC(id), correrMP(id)]);
      if (carrera === id) { corriendo = false; boton.textContent = "↺ Otra vez"; }
    });
  }

  // ---------- ejemplo 1: qué segmentos lleva cada número ----------
  // Display de cátodo común: un segmento se prende con el pin en 1 (HIGH).
  const SEGMENTOS = ["a", "b", "c", "d", "e", "f", "g"];
  const GPIO7 = { a: 17, b: 16, c: 32, d: 33, e: 25, f: 14, g: 12 };
  const DIGITOS = { 0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg", 5: "acdfg", 6: "acdefg", 7: "abc", 8: "abcdefg", 9: "abcdfg" };
  let digito = 2;
  function pintarDigito() {
    const on = DIGITOS[digito];
    document.querySelectorAll(".display7 .seg").forEach((g, i) => g.classList.toggle("on", on.includes(SEGMENTOS[i])));
    document.querySelectorAll("#tabla7 tbody tr").forEach((tr, i) => {
      if (i >= SEGMENTOS.length) return;
      const td = tr.cells[2], si = on.includes(SEGMENTOS[i]);
      td.textContent = si ? "encendido" : "apagado"; td.classList.toggle("on", si);
    });
    $("#thDig").textContent = 'Para el "' + digito + '"';
    $("#digTxt").textContent = digito;
    document.querySelectorAll(".dig").forEach((b) => b.classList.toggle("activo", +b.dataset.d === digito));
    const l = $("#ejemplo-7seg").dataset.leng || "mp";
    $("#codDigito").innerHTML = SEGMENTOS.map((s) => {
      const si = on.includes(s), S = s.toUpperCase();
      const linea = l === "mp" ? "s" + S + ".value(" + (si ? 1 : 0) + ")" : "digitalWrite(s" + S + ", " + (si ? "HIGH" : "LOW") + ");";
      return '<span class="' + (si ? "on" : "off") + '">' + linea + "</span>";
    }).join("\n") + '\n<span class="off">' + (l === "mp" ? "# segmento a = GPIO" + GPIO7.a + ", g = GPIO" + GPIO7.g : "// segmento a = GPIO" + GPIO7.a + ", g = GPIO" + GPIO7.g) + "</span>";
  }
  function iniciarDigitos() {
    const caja = $("#digitos");
    if (!caja) return;
    for (let d = 0; d <= 9; d++) {
      const b = document.createElement("button");
      b.className = "dig"; b.dataset.d = d; b.textContent = d; b.type = "button";
      b.title = "Mostrar el " + d + " (segmentos " + DIGITOS[d].split("").join(", ") + ")";
      b.addEventListener("click", () => { digito = d; pintarDigito(); });
      caja.appendChild(b);
    }
    // El código de ejemplo sigue al selector de lenguaje del paso.
    document.querySelectorAll('.selector-leng[data-ejemplo="7seg"] .sl').forEach((b) => b.addEventListener("click", () => setTimeout(pintarDigito, 0)));
    pintarDigito();
  }

  // ---------- instalación: lista con memoria ----------
  function iniciarInstalacion() {
    const casillas = Array.from(document.querySelectorAll("#instalacion input"));
    let hechos = [];
    try { hechos = JSON.parse(localStorage.getItem("tema2-instalar") || "[]"); } catch (e) { /* nada */ }
    const pintar = () => {
      casillas.forEach((c) => c.closest("li").classList.toggle("hecho", c.checked));
      $("#instListo").hidden = !casillas.every((c) => c.checked);
      if (casillas.every((c) => c.checked)) marcarPunto(/^Instalar MicroPython/);
    };
    casillas.forEach((c, i) => {
      c.checked = !!hechos[i];
      c.addEventListener("change", () => {
        try { localStorage.setItem("tema2-instalar", JSON.stringify(casillas.map((x) => x.checked))); } catch (e) { /* nada */ }
        pintar();
      });
    });
    pintar();
  }

  let lista = null, pide = [];
  function marcarPunto(re) {
    const p = pide.find((x) => re.test(x));
    if (lista && p) lista.marcar(p);
  }

  function aviso(t, tipo) { if (A() && A().aviso) A().aviso(t, tipo); }

  // ---------- arranque ----------
  async function iniciar() {
    iniciarEjemplos();
    iniciarDigitos();
    iniciarDuelo();
    iniciarInstalacion();
    iniciarLadoALado();
    const app = A();
    try { if (app && app.iniciar) pide = [].concat((await app.iniciar()).pide || []); } catch (e) { /* el aviso lo muestra App */ }

    if (app && app.checklist) lista = app.checklist($("#checklist"));
    if (app && app.imagen) document.querySelectorAll(".capturas img, .cap-circuito img").forEach((i) => app.imagen(i));
    if (app && app.markdown) {
      app.markdown($("#mdQueEs"), "README.md", { desde: "## Qué es Thonny", hasta: "## Cómo se relaciona esto" })
        .then((el) => { if (el) el.querySelectorAll("img").forEach((i) => app.imagen(i)); })
        .catch(() => {});
    }

    // Un tema de lectura: leer "Qué es" responde los puntos 1 y 3 del enunciado; terminar la
    // lista de instalación, el 2. El 4 se marca solo al abrir Wokwi (acciones que lo "cubren").
    const alCambiar = (i, seccion) => {
      if (lista && seccion && seccion.id === "que-es") { marcarPunto(/^Qué es Thonny/); marcarPunto(/^Por qué MicroPython/); }
    };
    let pasos = null;
    if (app && app.pasos) pasos = app.pasos($("#guia"), { alCambiar });
    else $("#guia").classList.add("sin-pasos");
    // La checklist termina de cargar un instante después: se repasa lo ya hecho.
    setTimeout(() => {
      if (pasos) alCambiar(pasos.actual, pasos.secciones[pasos.actual]);
      if (Array.from(document.querySelectorAll("#instalacion input")).every((c) => c.checked)) marcarPunto(/^Instalar MicroPython/);
    }, 400);

    const irA = (id) => {
      const s = document.getElementById(id); if (!s) return;
      if (pasos) pasos.ir(pasos.secciones.indexOf(s)); else s.scrollIntoView({ behavior: "smooth" });
    };
    document.querySelectorAll("[data-ir]").forEach((b) => b.addEventListener("click", () => irA(b.dataset.ir)));
    // Enlaces de otras apps: /app/2-lenguajes-thonny/#instalar abre directo en ese paso.
    const ir = () => { const h = decodeURIComponent(location.hash.slice(1)); if (h && document.getElementById(h) && document.getElementById(h).classList.contains("paso")) irA(h); };
    window.addEventListener("hashchange", ir);
    ir();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
