// Lector de la investigación del ESP32 (tema 1).
// Arma el índice por capítulos a partir de los "## " del README.md de la práctica y muestra
// un capítulo a la vez con App.markdown (de /comun/app.js), más un capítulo propio de la app:
// "Correr ficha_placa.py en tu ESP32". No ejecuta nada en el PC: el tema es de lectura.
(function () {
  "use strict";

  const CARPETA = "1-esp32-investigacion";
  const REPO = "/repo/" + CARPETA + "/";
  const GITHUB = "https://github.com/Dathinel/Sensores-Teoria";
  const CLAVE = "tema1-lector";               // localStorage: capítulos leídos y el último abierto
  const A = () => window.App || null;

  // Grupos del índice: el orden de lectura que proponemos (no el del README, que mezcla la
  // investigación con el script). Cada capítulo se busca por el comienzo de su título.
  const GRUPOS = [
    { nombre: "La investigación", caps: [
      "Qué pedía la actividad", "Cómo se hizo", "Qué es un microcontrolador", "Ficha técnica", "De dónde viene",
      "La familia y quién la fabrica", "Arquitectura", "Pines", "Qué es un ADC", "Cómo se programa",
      "El costo ambiental", "Para qué se usa"] },
    { nombre: "El script de la placa", caps: [
      "La idea general", "Conexiones", "Qué hace cada archivo", "Cómo funciona", "@placa",
      "Qué se usó de todo esto"] },
  ];
  // Secciones del README que la app reemplaza por su propio capítulo (o que son internas, como el
  // índice de entrada del README, que aquí es el lateral).
  const OCULTAR = ["Cómo probarlo", "Pendiente", "¿Quiere"];   // "¿Quiere probarlo?" / "¿Quiere saber…?": la entrada del README
  // Cada punto de "pide" del manifiesto, con el capítulo que lo responde.
  const PIDE_A_CAP = [
    ["Origen", "De dónde viene"], ["Quién fabrica", "La familia y quién la fabrica"],
    ["Arquitectura", "Arquitectura"], ["Pinout", "Pines"], ["Cómo se programa", "Cómo se programa"],
    ["Costo ambiental", "El costo ambiental"], ["Para qué se usa", "Para qué se usa"],
  ];
  const TITULOS_CORTOS = {            // el índice lateral se lee mejor con títulos breves
    "Qué pedía la actividad y qué hicimos": "La actividad y qué hicimos",
    "Cómo se hizo, paso a paso": "Cómo se hizo",
    "Ficha técnica (DevKit V1 con ESP32-WROOM-32, la placa de los labs)": "Ficha técnica",
    "Pines: lo que no se puede hacer con cada uno": "Pines y sus restricciones",
    "Qué es un ADC, un DAC y el PWM": "ADC, DAC y PWM",
    "Cómo funciona `ficha_placa.py` paso a paso": "Cómo funciona ficha_placa.py",
    "Qué se usó de todo esto en este repositorio": "Qué se usó en el curso",
    "El costo ambiental de un chip barato": "El costo ambiental",
  };

  const $ = (s) => document.querySelector(s);
  let caps = [];          // [{id, titulo, corto, grupo, desde, hasta, especial}]
  let actual = -1;
  let estado = leerEstado();

  function leerEstado() {
    try { return JSON.parse(localStorage.getItem(CLAVE)) || { leidos: {}, marcados: {} }; }
    catch (e) { return { leidos: {}, marcados: {} }; }
  }
  function guardarEstado() { try { localStorage.setItem(CLAVE, JSON.stringify(estado)); } catch (e) { /* sin almacenamiento */ } }

  // Mismo "slug" que usa GitHub para los anclajes (#cómo-funciona-ficha_placapy-paso-a-paso).
  function slugGithub(t) {
    return t.trim().toLowerCase().replace(/[^\p{L}\p{N}\s_-]/gu, "").replace(/\s/g, "-");
  }

  // Títulos "## " del README, sin contar los que están dentro de bloques de código.
  function titulosDelReadme(texto) {
    const salida = [];
    let enCodigo = false;
    for (const linea of texto.split(/\r?\n/)) {
      if (/^```/.test(linea)) { enCodigo = !enCodigo; continue; }
      if (!enCodigo && /^## /.test(linea)) salida.push(linea.slice(3).trim());
    }
    return salida;
  }

  function armarCapitulos(titulos) {
    const usados = new Set();
    const lista = [{ id: "portada", corto: "Portada", grupo: null, especial: true }];
    for (const g of GRUPOS) {
      for (const pref of g.caps) {
        if (pref === "@placa") {
          lista.push({ id: "placa", corto: "Córrelo en tu ESP32", grupo: g.nombre, especial: true });
          continue;
        }
        const i = titulos.findIndex((t) => t.startsWith(pref));
        if (i < 0 || usados.has(i)) continue;
        usados.add(i);
        lista.push(capDeReadme(titulos, i, g.nombre));
      }
    }
    // Si el README gana secciones nuevas, no se pierden: van al final en "Más".
    titulos.forEach((t, i) => {
      if (usados.has(i) || OCULTAR.some((o) => t.startsWith(o))) return;
      lista.push(capDeReadme(titulos, i, "Más"));
    });
    return lista;
  }
  function capDeReadme(titulos, i, grupo) {
    const t = titulos[i];
    return { id: slugGithub(t), titulo: t, corto: TITULOS_CORTOS[t] || t.replace(/`/g, ""), grupo,
             desde: "## " + t, hasta: titulos[i + 1] ? "## " + titulos[i + 1] : null };
  }

  // ---------- índice lateral ----------
  function pintarIndice() {
    const ol = $("#listaCap");
    ol.innerHTML = "";
    let grupo = undefined;
    caps.forEach((c, i) => {
      if (c.grupo !== grupo && c.grupo) {
        const g = document.createElement("li");
        g.className = "grupo"; g.textContent = c.grupo; ol.appendChild(g);
      }
      grupo = c.grupo;
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.className = "cap" + (c.especial && c.id !== "portada" ? " especial" : "");
      a.href = "#" + c.id; a.dataset.i = i;
      a.innerHTML = '<span class="marca">●</span><span></span>';
      a.lastChild.textContent = c.corto;
      li.appendChild(a); ol.appendChild(li);
    });
    // Mapa de la portada: los grupos con su primer capítulo.
    const mapa = $("#mapaGrupos");
    mapa.innerHTML = "";
    for (const g of GRUPOS.concat([{ nombre: "Más" }])) {
      const delGrupo = caps.filter((c) => c.grupo === g.nombre);
      if (!delGrupo.length) continue;
      const li = document.createElement("li");
      li.innerHTML = "<b></b> · <span></span> capítulos. ";
      li.querySelector("b").textContent = g.nombre;
      li.querySelector("span").textContent = delGrupo.length;
      const a = document.createElement("a");
      a.textContent = "Empezar por «" + delGrupo[0].corto + "»";
      a.href = "#" + delGrupo[0].id;
      li.appendChild(a); mapa.appendChild(li);
    }
    refrescarMarcas();
  }

  function refrescarMarcas() {
    document.querySelectorAll(".indice a.cap").forEach((a) => {
      const c = caps[+a.dataset.i];
      a.classList.toggle("leido", !!estado.leidos[c.id]);
      a.classList.toggle("actual", +a.dataset.i === actual);
    });
    const contables = caps.filter((c) => c.id !== "portada");
    const n = contables.filter((c) => estado.leidos[c.id]).length;
    $("#progresoLectura").style.width = (100 * n / contables.length) + "%";
    $("#txtLeidos").textContent = n + " / " + contables.length + " leídos";
    // Checklist: un punto se marca si se leyó su capítulo o si el usuario lo marcó a mano.
    document.querySelectorAll("#listaPide li").forEach((li) => {
      const cb = li.querySelector("input");
      cb.checked = !!(estado.marcados[li.dataset.pide] || (li.dataset.cap && estado.leidos[li.dataset.cap]));
    });
  }

  // ---------- checklist de la portada ----------
  function pintarPide(pide) {
    const ul = $("#listaPide");
    ul.innerHTML = "";
    for (const texto of pide) {
      const par = PIDE_A_CAP.find(([clave]) => texto.startsWith(clave));
      const cap = par && caps.find((c) => c.titulo && c.titulo.startsWith(par[1]));
      const li = document.createElement("li");
      li.dataset.pide = texto;
      if (cap) li.dataset.cap = cap.id;
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.addEventListener("change", () => { estado.marcados[texto] = cb.checked; guardarEstado(); refrescarMarcas(); });
      li.appendChild(cb);
      if (cap) {
        const a = document.createElement("a"); a.href = "#" + cap.id; a.textContent = texto; li.appendChild(a);
      } else {
        li.appendChild(document.createTextNode(texto));
      }
      ul.appendChild(li);
    }
  }

  // ---------- mostrar un capítulo ----------
  function seccionDe(c) {
    if (c.id === "portada") return $("#cap-portada");
    if (c.id === "placa") return $("#cap-placa");
    let s = document.getElementById("cap-" + c.id);
    if (!s) {
      s = document.createElement("section");
      s.className = "capitulo"; s.id = "cap-" + c.id; s.hidden = true;
      s.innerHTML = '<p class="antetitulo"></p><div class="md"><p class="cargando">Cargando el capítulo…</p></div>';
      s.querySelector(".antetitulo").textContent = c.grupo || "";
      $("#capsReadme").appendChild(s);
      renderizar(c, s.querySelector(".md"));
    }
    return s;
  }

  async function renderizar(c, el) {
    const opciones = { desde: c.desde };
    if (c.hasta) opciones.hasta = c.hasta;
    try {
      if (A() && A().markdown) {
        await A().markdown(el, "README.md", opciones);
      } else {
        // Sin el framework (no debería pasar): texto plano legible.
        const t = await (await fetch(REPO + "README.md")).text();
        const ini = t.indexOf(c.desde);
        const fin = c.hasta ? t.indexOf(c.hasta, ini + 1) : -1;
        el.innerHTML = "<pre></pre>";
        el.firstChild.textContent = t.slice(ini, fin > 0 ? fin : undefined);
      }
    } catch (e) {
      el.innerHTML = '<p class="cargando">No se pudo cargar este capítulo. Ábrelo en GitHub con el botón de arriba.</p>';
      return;
    }
    retocar(el);
    // Si el capítulo terminó de cargar mientras está abierto, ya tiene sus subtítulos.
    if (caps[actual] === c) pintarSub(el.closest(".capitulo"));
  }

  // Ajustes al HTML del README para que funcione dentro de la app: enlaces relativos del repo
  // (a otros temas → su app; a archivos → GitHub; anclas → el capítulo), tablas con scroll e
  // imágenes ampliables.
  function retocar(el) {
    el.querySelectorAll("a[href]").forEach((a) => {
      const href = a.getAttribute("href");
      if (/^(https?:|mailto:)/.test(href) && !href.includes(location.host)) {
        a.target = "_blank"; a.rel = "noopener"; return;
      }
      if (href.startsWith("#")) {
        const destino = decodeURIComponent(href.slice(1));
        const cap = caps.find((c) => c.id === destino);
        if (cap) { a.setAttribute("href", "#" + cap.id); a.removeAttribute("target"); return; }
        // Una sección que la app no muestra como capítulo (Pendiente, Cómo probarlo...): se abre
        // en el README de GitHub, en vez de caer a la portada.
        a.setAttribute("href", GITHUB + "/tree/main/" + CARPETA + "#" + destino);
        a.target = "_blank"; a.rel = "noopener";
        return;
      }
      const u = new URL(href, location.origin + REPO + "README.md");
      if (!u.pathname.startsWith("/repo/")) return;
      const rel = decodeURIComponent(u.pathname.slice(6)).replace(/\/$/, "");
      if (rel === CARPETA + "/ficha_placa.py") { a.setAttribute("href", "#placa"); a.removeAttribute("target"); return; }
      a.target = "_blank"; a.rel = "noopener";
      if (/^[^/]+$/.test(rel) && rel !== CARPETA && !rel.includes(".")) {
        // Otro tema del repo: se abre su app. El ancla de instalar del tema 2 tiene la suya.
        const ancla = rel === "2-lenguajes-thonny" && /instalar/.test(u.hash) ? "#instalar" : "";
        a.setAttribute("href", "/app/" + rel + "/" + ancla);
      } else {
        a.setAttribute("href", GITHUB + (rel.includes(".") ? "/blob/main/" : "/tree/main/") + rel + u.hash);
      }
    });
    el.querySelectorAll("table").forEach((t) => {
      if (t.parentElement.classList.contains("tabla-scroll")) return;
      const envoltura = document.createElement("div");
      envoltura.className = "tabla-scroll";
      t.parentNode.insertBefore(envoltura, t); envoltura.appendChild(t);
    });
    el.querySelectorAll("img").forEach((img) => { if (A() && A().imagen) A().imagen(img); });
  }

  // ---------- columna "En este capítulo" (solo en pantallas anchas, ver lector.css) ----------
  // Lista lo que trae el capítulo abierto para saltar directo: subtítulos (### o párrafos que
  // empiezan en negrita, que es como el README parte sus capítulos), diagramas y tablas. En los capítulos propios de la app, sus h2. Marca por dónde va la lectura.
  let subtitulos = [];
  const recortar = (s, n) => (s.length > n ? s.slice(0, n - 1).trimEnd() + "…" : s);
  // Un párrafo que empieza en negrita ("**1. Chip y firmware.** ...") cuenta como subtítulo.
  function esObjeto(el) {
    if (el.parentElement.closest("pre, .mermaid, table")) return false;
    if (el.tagName !== "STRONG") return true;
    const p = el.parentElement, txt = el.textContent.trim();
    return p.firstChild === el && txt.length > 2 && txt.length < 60;
  }
  function etiqueta(el) {
    if (/^(H[23]|STRONG)$/.test(el.tagName)) return el.textContent.trim().replace(/[.:]$/, "");
    if (el.tagName === "TABLE") {
      const ths = Array.from(el.querySelectorAll("th")).map((x) => x.textContent.trim()).filter(Boolean);
      return "▦ Tabla: " + recortar(ths.slice(0, 3).join(" · ") || "datos", 46);
    }
    return "◇ Diagrama";
  }
  function pintarSub(seccion) {
    const aside = $("#enCap"), ol = $("#listaSub");
    if (!aside || !seccion) return;
    const md = seccion.querySelector(".md");
    const hs = md
      ? Array.from(md.querySelectorAll("h3, p > strong:first-child, table, .mermaid")).filter(esObjeto)
      : Array.from(seccion.querySelectorAll("h2"));
    ol.innerHTML = "";
    subtitulos = [];
    hs.forEach((h, n) => {
      if (!h.id) h.id = (seccion.id || "cap") + "-sub-" + n;
      const li = document.createElement("li"), a = document.createElement("a");
      a.href = "#" + h.id; a.textContent = etiqueta(h);
      if (!/^(H[23]|STRONG)$/.test(h.tagName)) a.className = "objeto";
      a.addEventListener("click", (e) => { e.preventDefault(); h.scrollIntoView({ behavior: "smooth", block: "start" }); });
      li.appendChild(a); ol.appendChild(li);
      subtitulos.push([h, a]);
    });
    aside.hidden = hs.length < 2;
    marcarSub();
  }
  function marcarSub() {
    let ultimo = null;
    for (const [h, a] of subtitulos) { a.classList.remove("visto"); if (h.getBoundingClientRect().top < 140) ultimo = a; }
    if (ultimo) ultimo.classList.add("visto");
  }
  window.addEventListener("scroll", () => { if (subtitulos.length) requestAnimationFrame(marcarSub); }, { passive: true });

  function ir(i, desdeHash) {
    if (i < 0 || i >= caps.length) return;
    const c = caps[i];
    document.querySelectorAll(".capitulo").forEach((s) => { s.hidden = true; });
    const s = seccionDe(c);
    s.hidden = false;
    actual = i;
    pintarSub(s);
    if (c.id !== "portada") { estado.leidos[c.id] = true; }
    estado.ultimo = c.id;
    guardarEstado();
    refrescarMarcas();
    $("#bAnterior").disabled = i === 0;
    $("#bSiguiente").disabled = i === caps.length - 1;
    $("#bSiguiente").textContent = i === caps.length - 1 ? "Fin" : "Siguiente: " + caps[i + 1].corto + " →";
    $("#posCap").textContent = i === 0 ? "" : "Capítulo " + i + " de " + (caps.length - 1);
    if (!desdeHash) history.replaceState(null, "", "#" + c.id);
    window.scrollTo({ top: 0 });
    $("#indice").classList.remove("abierto");
    const enlace = document.querySelector('.indice a.cap[data-i="' + i + '"]');
    if (enlace) enlace.scrollIntoView({ block: "nearest" });
  }
  function irPorId(id, desdeHash) {
    const i = caps.findIndex((c) => c.id === id);
    ir(i < 0 ? 0 : i, desdeHash);
  }

  // ---------- código del script, con un resaltado mínimo ----------
  function resaltarPython(texto) {
    const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return texto.split("\n").map((linea) => {
      const m = linea.match(/^(.*?)(#.*)?$/);
      let codigo = esc(m[1] || "");
      codigo = codigo.replace(/("[^"]*")/g, '<span class="s">$1</span>');
      codigo = codigo.replace(/(<span class="s">.*?<\/span>)|\b(\d+)\b/g, (t, s, n) => s || '<span class="n">' + n + "</span>");
      codigo = codigo.replace(/(<span class="[sn]">.*?<\/span>)|\b(import|from|print|try|except|for|in|range|def|return|if|else|while|True|False|None|as)\b/g,
        (t, s, k) => s || '<span class="k">' + k + "</span>");
      return codigo + (m[2] ? '<span class="c">' + esc(m[2]) + "</span>" : "");
    }).join("\n");
  }
  let textoFicha = "";
  async function cargarCodigo() {
    try {
      textoFicha = await (await fetch(REPO + "ficha_placa.py")).text();
      $("#codigoFicha").innerHTML = resaltarPython(textoFicha);
    } catch (e) {
      $("#codigoFicha").textContent = "No se pudo leer ficha_placa.py. Está en GitHub (botón de arriba).";
    }
  }
  async function copiar() {
    try {
      await navigator.clipboard.writeText(textoFicha);
      aviso("Código copiado. Pégalo en un archivo nuevo de Thonny y presiona F5 con la placa conectada.", "ok");
    } catch (e) {
      // Sin permiso de portapapeles: se selecciona el texto para copiarlo con Ctrl+C.
      const r = document.createRange(); r.selectNodeContents($("#codigoFicha"));
      const sel = getSelection(); sel.removeAllRanges(); sel.addRange(r);
      aviso("Texto seleccionado: cópialo con Ctrl+C.", "info");
    }
  }
  function aviso(texto, tipo) {
    if (A() && A().aviso) A().aviso(texto, tipo); else console.log(texto);
  }
  function abrirExterno(url) {
    if (A() && A().abrir) A().abrir(url); else window.open(url, "_blank", "noopener");
  }

  // ---------- arranque ----------
  function dibujarPines() {
    // Las dos hileras de 15 pines del DevKit en el dibujo de la portada.
    const g = document.getElementById("filaPines");
    if (!g) return;
    let html = "";
    for (let i = 0; i < 15; i++) {
      const x = 50 + i * 19;
      html += '<rect x="' + x + '" y="34" width="9" height="9" rx="1.5"/><rect x="' + x + '" y="187" width="9" height="9" rx="1.5"/>';
    }
    g.innerHTML = html;
  }

  async function iniciar() {
    dibujarPines();
    let manifiesto = null;
    try { if (A() && A().iniciar) manifiesto = await A().iniciar(); } catch (e) { /* se sigue con el README */ }
    if (!manifiesto || !manifiesto.pide) {
      try { manifiesto = Object.assign({}, manifiesto, await (await fetch(REPO + "probar.json")).json()); } catch (e) { manifiesto = { pide: [] }; }
    }
    let readme = "";
    try { readme = await (await fetch(REPO + "README.md")).text(); } catch (e) { /* sin README: solo portada */ }
    caps = armarCapitulos(titulosDelReadme(readme));
    pintarIndice();
    pintarPide([].concat(manifiesto.pide || []));
    refrescarMarcas();

    $("#listaCap").addEventListener("click", (e) => {
      const a = e.target.closest("a.cap"); if (!a) return;
      e.preventDefault(); ir(+a.dataset.i);
    });
    $("#bAnterior").onclick = () => ir(actual - 1);
    $("#bSiguiente").onclick = () => ir(actual + 1);
    $("#bEmpezar").onclick = () => ir(1);
    $("#bIrPlaca").onclick = () => irPorId("placa");
    $("#bCopiar").onclick = copiar;
    $("#bWokwi").onclick = () => {
      // La acción "wokwi" del probar.json (App.accion abre la pestaña en el mismo clic).
      if (A() && A().practica) { try { A().accion("wokwi"); return; } catch (e) { /* abajo */ } }
      abrirExterno("https://wokwi.com/projects/new/micropython-esp32");
    };
    $("#bMenu").onclick = () => $("#indice").classList.toggle("abierto");
    window.addEventListener("hashchange", () => irPorId(decodeURIComponent(location.hash.slice(1)) || "portada", true));
    document.addEventListener("keydown", (e) => {
      if (e.target.closest("input, textarea")) return;
      if (e.key === "ArrowRight") ir(actual + 1);
      if (e.key === "ArrowLeft") ir(actual - 1);
    });
    cargarCodigo();
    irPorId(decodeURIComponent(location.hash.slice(1)) || "portada", true);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
