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
