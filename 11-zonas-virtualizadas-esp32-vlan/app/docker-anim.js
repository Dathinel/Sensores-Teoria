/* Docker, paso a paso (tema 11): seis escenas animadas en SVG, cada una con "su prueba al lado".
 *
 *   1. La imagen      : el Dockerfile se convierte en capas apiladas (y viaja a Docker Hub).
 *   2. El contenedor  : de UNA imagen salen tres contenedores (sim-spot, sim-pepper, sim-nao).
 *   3. La red (VLAN)  : tres redes bridge = tres switches; un broadcast no sale de su red.
 *   4. El router      : el admin llega a una zona pasando por el router (ttl 64 -> 63).
 *   5. El DROP        : de la zona gamer a la robótica no se pasa: sin ruta lo tira Docker,
 *                       con la ruta forzada lo tira el router y sube su contador.
 *   6. docker compose : el orden en que se levanta todo (imágenes, redes, router, el resto, LED).
 *
 * No depende de App: centro.js le pasa los datos reales con DockerAnim.datos({...}) (imágenes,
 * contenedores y redes que lee app/estado_vivo.py de Docker; el json de la prueba de aislamiento;
 * los tiempos de la última vez que se levantó) y la escena muestra "la prueba" con eso.
 */
(function () {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";
  const C = { g: "#3fbf8f", r: "#f0913a", a: "#a77be8", rt: "#4f8fce", ok: "#4caf7d", mal: "#d9534f", lento: "#e8b930",
              txt: "#e7e9ec", suave: "#8b929b", panel: "#15191d", borde: "#2c3238", hondo: "#0a0d10", docker: "#2496ed" };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const CANCELADA = { cancelada: true };

  let svg = null, token = 0, escena = 0, reproduciendo = true, visible = false, alIr = null;
  let D = { imagenes: null, contenedores: null, redes: null, aislamiento: null, subida: null };

  // ------------------------------------------------------------------ utilidades SVG
  function el(tag, attrs, padre) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) if (v !== undefined && v !== null) e.setAttribute(k, v);
    (padre || svg).appendChild(e);
    return e;
  }
  function txt(x, y, s, attrs, padre) {
    const t = el("text", Object.assign({ x, y, fill: C.txt, "font-family": "IBM Plex Mono", "font-size": 12 }, attrs || {}), padre);
    t.textContent = s;
    return t;
  }
  function caja(x, y, w, h, color, padre, extra) {
    return el("rect", Object.assign({ x, y, width: w, height: h, rx: 7, fill: color + "1c", stroke: color, "stroke-width": 1.5 }, extra || {}), padre);
  }
  function grupo(attrs, padre) { return el("g", attrs, padre); }
  function oculto(e) { e.style.opacity = 0; return e; }
  function flecha(color) {
    const id = "fl" + color.slice(1);
    if (!svg.querySelector("#" + id)) {
      const defs = svg.querySelector("defs") || el("defs", {});
      const m = el("marker", { id, viewBox: "0 0 8 8", refX: 7, refY: 4, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" }, defs);
      el("path", { d: "M0 0 L8 4 L0 8 z", fill: color }, m);
    }
    return `url(#${id})`;
  }

  // ------------------------------------------------------------------ tiempo y movimiento
  const suave = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
  function animar(ms, paso, tk) {
    return new Promise((res, rej) => {
      const t0 = performance.now();
      function f(ahora) {
        if (tk !== token) return rej(CANCELADA);
        const t = Math.min(1, (ahora - t0) / ms);
        paso(suave(t), t);
        if (t < 1) requestAnimationFrame(f); else res();
      }
      requestAnimationFrame(f);
    });
  }
  function esperar(ms, tk) {
    return new Promise((res, rej) => setTimeout(() => (tk === token ? res() : rej(CANCELADA)), ms));
  }
  async function aparecer(e, tk, ms = 350) { await animar(ms, (t) => { e.style.opacity = t; }, tk); }
  async function desaparecer(e, tk, ms = 300) { await animar(ms, (t) => { e.style.opacity = 1 - t; }, tk); }

  /** Un "paquete": un círculo con una etiqueta que se mueve por una polilínea. */
  function paquete(color, etiqueta, padre) {
    const g = grupo({}, padre);
    el("circle", { r: 8, fill: color, stroke: "#fff", "stroke-width": 1.5 }, g);
    const t = txt(12, 4, etiqueta || "", { "font-size": 11, fill: color, "font-weight": 600 }, g);
    g.etiqueta = t;
    g.style.opacity = 0;
    return g;
  }
  function ponerEn(g, x, y) { g.setAttribute("transform", `translate(${x},${y})`); g.pos = [x, y]; }
  async function mover(g, puntos, ms, tk) {
    // Reparte el tiempo según la longitud de cada tramo.
    const tramos = [];
    let total = 0;
    for (let i = 1; i < puntos.length; i++) {
      const [x0, y0] = puntos[i - 1], [x1, y1] = puntos[i];
      const l = Math.hypot(x1 - x0, y1 - y0);
      tramos.push([x0, y0, x1, y1, l]); total += l;
    }
    ponerEn(g, ...puntos[0]); g.style.opacity = 1;
    await animar(ms, (t) => {
      let d = t * total;
      for (const [x0, y0, x1, y1, l] of tramos) {
        if (d <= l || l === 0) { const f = l ? d / l : 1; ponerEn(g, x0 + (x1 - x0) * f, y0 + (y1 - y0) * f); return; }
        d -= l;
      }
      ponerEn(g, ...puntos[puntos.length - 1]);
    }, tk);
  }
  /** Una X roja que aparece y se desvanece donde murió un paquete. */
  async function explotar(x, y, texto, tk) {
    const g = grupo({ transform: `translate(${x},${y})` });
    el("circle", { r: 16, fill: "rgba(217,83,79,.18)", stroke: C.mal, "stroke-width": 2 }, g);
    txt(0, 6, "✕", { "text-anchor": "middle", fill: "#ff8a86", "font-size": 18, "font-weight": 700 }, g);
    if (texto) txt(0, 34, texto, { "text-anchor": "middle", fill: C.mal, "font-size": 11, "font-weight": 600 }, g);
    await animar(250, (t) => { g.setAttribute("transform", `translate(${x},${y}) scale(${0.4 + 0.6 * t})`); }, tk);
    await esperar(1100, tk);
    await desaparecer(g, tk, 400);
    g.remove();
  }
  async function bien(x, y, texto, tk) {
    const g = grupo({ transform: `translate(${x},${y})` });
    el("circle", { r: 15, fill: "rgba(76,175,125,.18)", stroke: C.ok, "stroke-width": 2 }, g);
    txt(0, 6, "✓", { "text-anchor": "middle", fill: "#9ff7c6", "font-size": 17, "font-weight": 700 }, g);
    if (texto) txt(0, 32, texto, { "text-anchor": "middle", fill: C.ok, "font-size": 11, "font-weight": 600 }, g);
    await esperar(900, tk);
    await desaparecer(g, tk, 300);
    g.remove();
  }
  /** Rótulo de abajo: qué está pasando ahora mismo en la escena. */
  function rotulo(s, color) {
    const t = svg.querySelector("#rotulo");
    if (t) { t.textContent = s; t.setAttribute("fill", color || C.txt); }
  }

  // ------------------------------------------------------------------ dibujos que se repiten
  /** Las tres zonas con el router al centro (escenas 4 y 5). Devuelve las posiciones. */
  function dibujarZonas() {
    const P = { "player-1": [165, 112], "track-server": [165, 160], "sim-nao": [735, 112], "sim-spot": [735, 160],
                admin: [450, 352], router: [450, 225], puerta: [165, 262] };
    caja(30, 40, 270, 160, C.g); txt(42, 60, "VLAN 1 · ZONA GAMER", { fill: C.g, "font-weight": 600 }); txt(42, 78, "192.168.10.0/24", { fill: C.suave, "font-size": 10 });
    caja(600, 40, 270, 160, C.r); txt(612, 60, "VLAN 2 · ZONA ROBÓTICA", { fill: C.r, "font-weight": 600 }); txt(612, 78, "192.168.20.0/24", { fill: C.suave, "font-size": 10 });
    caja(300, 300, 300, 92, C.a); txt(312, 320, "VLAN 3 · ADMINISTRACIÓN", { fill: C.a, "font-weight": 600 }); txt(588, 320, "192.168.30.0/24", { fill: C.suave, "font-size": 10, "text-anchor": "end" });
    // Patas del router (.254 en cada red)
    const pata = { stroke: C.rt, "stroke-width": 2.5, fill: "none" };
    el("path", Object.assign({ d: "M300 150 C 360 150, 400 200, 428 215" }, pata));
    el("path", Object.assign({ d: "M600 150 C 540 150, 500 200, 472 215" }, pata));
    el("path", Object.assign({ d: "M450 250 L 450 300" }, pata));
    txt(318, 142, ".10.254", { fill: C.rt, "font-size": 10 }); txt(538, 142, ".20.254", { fill: C.rt, "font-size": 10 }); txt(458, 290, ".30.254", { fill: C.rt, "font-size": 10 });
    el("circle", { cx: 450, cy: 225, r: 26, fill: "#13263a", stroke: C.rt, "stroke-width": 2.5 });
    txt(450, 222, "router", { "text-anchor": "middle", fill: C.rt, "font-size": 11, "font-weight": 600 });
    txt(450, 236, "iptables", { "text-anchor": "middle", fill: C.suave, "font-size": 9 });
    const nodo = (id, ip, color) => {
      const [x, y] = P[id];
      el("rect", { x: x - 62, y: y - 15, width: 124, height: 30, rx: 6, fill: color + "26", stroke: color });
      txt(x, y + 1, id, { "text-anchor": "middle", "font-family": "Space Grotesk", "font-size": 13, "font-weight": 600 });
      txt(x, y + 12, ip, { "text-anchor": "middle", fill: C.suave, "font-size": 8.5 });
    };
    nodo("player-1", ".21", C.g); nodo("track-server", ".10", C.g);
    nodo("sim-nao", ".23", C.r); nodo("sim-spot", ".21", C.r);
    nodo("admin", ".10", C.a);
    txt(450, 404, "", { id: "rotulo", "text-anchor": "middle", "font-size": 12.5 });
    return P;
  }

  function pilaCapas(x, yBase, w, capas, padre, alto = 30) {
    // Capas de abajo hacia arriba; devuelve los grupos para animarlos.
    return capas.map(([nombre, tam, color], i) => {
      const g = grupo({}, padre);
      const y = yBase - (i + 1) * (alto + 3);
      el("rect", { x, y, width: w, height: alto, rx: 4, fill: (color || C.docker) + "30", stroke: color || C.docker }, g);
      txt(x + 10, y + alto / 2 + 4, nombre, { "font-size": 11 }, g);
      if (tam) txt(x + w - 8, y + alto / 2 + 4, tam, { "font-size": 10, fill: C.suave, "text-anchor": "end" }, g);
      return g;
    });
  }

  // ------------------------------------------------------------------ las escenas
  const IMG_TAM = { router: "47,6 MB", admin: "79,2 MB", "servidor-pista": "890 MB", jugador: "230 MB", robot: "898 MB", emulador: "228 MB" };

  const ESCENAS = [
    // ---------------------------------------------------------------- 1. imagen
    {
      titulo: "La imagen: una receta convertida en capas",
      explica: `<p>Todo empieza con un <b>Dockerfile</b>: una receta de pasos. <span class="c11-mono">docker build</span> ejecuta cada paso
        y guarda su resultado como una <b>capa</b>. Las capas apiladas son la <b>imagen</b>: una plantilla de solo lectura con un Linux,
        Python, PyBullet, los modelos de los robots y nuestro código.</p>
        <p>La imagen se sube a <b>Docker Hub</b> (<span class="c11-mono">docker push</span>) y otro PC la baja
        (<span class="c11-mono">docker pull</span>). Las capas de abajo (Linux y Python) son iguales en 4 de las 6 imágenes: <b>se bajan una sola vez</b>.</p>`,
      dibujar() {
        // Dockerfile
        el("rect", { x: 24, y: 40, width: 350, height: 262, rx: 9, fill: C.panel, stroke: C.borde });
        txt(38, 62, "zona-robotica/Dockerfile", { fill: C.suave, "font-size": 11 });
        const lineas = [
          ["FROM python:3.11-slim", "Linux + Python 3.11", "~45 MB"],
          ["RUN apt-get install iproute2", "herramientas de red", "~5 MB"],
          ["RUN pip install pybullet numpy…", "PyBullet y librerías", "~700 MB"],
          ["RUN python descargar_modelos.py", "modelos de los robots", "~30 MB"],
          ["COPY robots.py sim_robot.py ./", "nuestro código", "60 kB"],
          ["CMD python sim_robot.py", "qué corre al arrancar", "0 B"],
        ];
        const marcas = lineas.map(([l], i) => {
          const y = 80 + i * 36;
          const m = el("rect", { x: 32, y: y - 4, width: 334, height: 28, rx: 4, fill: "rgba(36,150,237,.18)" });
          m.style.opacity = 0;
          txt(42, y + 14, l, { "font-size": 12, fill: i === 0 ? "#9ecbff" : C.txt });
          return m;
        });
        // build
        el("path", { d: "M384 170 L 476 170", stroke: C.docker, "stroke-width": 2.5, "marker-end": flecha(C.docker) });
        txt(430, 160, "docker build", { "text-anchor": "middle", fill: C.docker, "font-size": 11 });
        // pila
        const capas = pilaCapas(490, 320, 250, lineas.map(([, n, t]) => [n, t]), null, 32);
        capas.forEach(oculto);
        const nombre = txt(615, 70, "imagen dathinel/zonas-esp32-robot:1.0", { "text-anchor": "middle", fill: C.docker, "font-size": 12, "font-weight": 600 });
        const total = txt(615, 88, "898 MB en disco", { "text-anchor": "middle", fill: C.suave, "font-size": 11 });
        oculto(nombre); oculto(total);
        // Docker Hub
        const hub = grupo({});
        el("rect", { x: 770, y: 120, width: 112, height: 70, rx: 30, fill: "rgba(36,150,237,.12)", stroke: C.docker, "stroke-width": 1.6 }, hub);
        txt(826, 152, "Docker Hub", { "text-anchor": "middle", fill: C.docker, "font-size": 12, "font-weight": 600 }, hub);
        txt(826, 170, "dathinel/…", { "text-anchor": "middle", fill: C.suave, "font-size": 10 }, hub);
        oculto(hub);
        txt(450, 404, "", { id: "rotulo", "text-anchor": "middle", "font-size": 12.5 });
        return { marcas, capas, nombre, total, hub };
      },
      async correr(r, tk) {
        rotulo("docker build lee el Dockerfile línea por línea…", C.suave);
        for (let i = 0; i < r.marcas.length; i++) {
          r.marcas.forEach((m, j) => { m.style.opacity = j === i ? 1 : 0; });
          const g = r.capas[i];
          await animar(450, (t) => { g.style.opacity = t; g.setAttribute("transform", `translate(${(1 - t) * -60},0)`); }, tk);
          rotulo(`paso ${i + 1} de 6 → capa "${g.querySelector("text").textContent}"`, C.txt);
          await esperar(450, tk);
        }
        r.marcas.forEach((m) => { m.style.opacity = 0; });
        await aparecer(r.nombre, tk); await aparecer(r.total, tk);
        rotulo("las 6 capas apiladas = la imagen (solo lectura)", C.docker);
        await esperar(900, tk);
        await aparecer(r.hub, tk);
        const p = paquete(C.docker, "push");
        await mover(p, [[745, 180], [770, 160]], 700, tk);
        p.etiqueta.textContent = "pull (otro PC)";
        rotulo("docker push la sube; en otro PC, docker pull la baja (solo las capas que le falten)", C.docker);
        await mover(p, [[826, 195], [826, 300], [826, 330]], 1100, tk);
        p.remove();
        await esperar(2200, tk);
      },
      prueba() {
        const imgs = D.imagenes;
        if (imgs && imgs.length) {
          return `<p class="c11-nota">Las imágenes del laboratorio que <b>tu Docker</b> tiene ahora mismo (<span class="c11-mono">docker images</span>):</p>
            <table class="c11-tabla"><tbody>${imgs.map((i) => `<tr><td class="c11-mono">${esc(i.repo.replace(/^.*\//, ""))}:${esc(i.tag)}</td><td class="num">${esc(i.tamano)}</td></tr>`).join("")}</tbody></table>
            <p class="c11-nota" style="margin-top:.4rem">Bajadas de Docker Hub son <b>~415 MB</b> comprimidos (34 capas, varias compartidas).</p>`;
        }
        return `<p class="c11-nota">Las 6 imágenes del laboratorio (medidas en la entrega; con "Mirar en vivo" se leen de tu Docker):</p>
          <table class="c11-tabla"><tbody>${Object.entries(IMG_TAM).map(([k, v]) => `<tr><td class="c11-mono">zonas-esp32-${esc(k)}:1.0</td><td class="num">${esc(v)}</td></tr>`).join("")}</tbody></table>
          <p class="c11-nota" style="margin-top:.4rem">De Docker Hub se bajan <b>~415 MB</b> comprimidos (34 capas; las de Linux y Python, una sola vez).</p>`;
      },
    },

    // ---------------------------------------------------------------- 2. contenedor
    {
      titulo: "El contenedor: la imagen, encendida",
      explica: `<p>Un <b>contenedor</b> es una imagen en marcha. Docker le pone encima una <b>capa de escritura</b> propia (lo que el
        programa cambie queda ahí, no en la imagen), le da su propio proceso, su propia red y sus variables.</p>
        <p>Por eso <b>de una sola imagen salen tres robots</b>: <span class="c11-mono">sim-spot</span>, <span class="c11-mono">sim-pepper</span>
        y <span class="c11-mono">sim-nao</span> usan <span class="c11-mono">zonas-esp32-robot:1.0</span>; solo cambia la variable
        <span class="c11-mono">ROBOT</span> y la IP. Igual con los 7 ESP32 emulados: una imagen, siete contenedores.</p>`,
      dibujar() {
        const capas = pilaCapas(40, 330, 220, [["Linux + Python"], ["iproute2"], ["PyBullet"], ["modelos"], ["código"]], null, 30);
        txt(150, 150, "imagen robot:1.0", { "text-anchor": "middle", fill: C.docker, "font-weight": 600 });
        txt(150, 166, "(solo lectura)", { "text-anchor": "middle", fill: C.suave, "font-size": 10 });
        void capas;
        const robots = [["sim-spot", "spot", ".21"], ["sim-pepper", "pepper", ".22"], ["sim-nao", "nao", ".23"]];
        const conts = robots.map(([n, rb, ip], i) => {
          const x = 360 + i * 175, y = 120;
          const flechaE = el("path", { d: `M262 200 C 300 60, ${x + 40} 40, ${x + 80} ${y - 6}`, stroke: C.docker, "stroke-width": 2, fill: "none", "stroke-dasharray": 900, "stroke-dashoffset": 900, "marker-end": flecha(C.docker) });
          const g = grupo({});
          el("rect", { x, y, width: 160, height: 220, rx: 9, fill: C.r + "12", stroke: C.r, "stroke-width": 1.6 }, g);
          el("rect", { x: x + 8, y: y + 8, width: 144, height: 26, rx: 4, fill: "rgba(232,185,48,.16)", stroke: C.lento, "stroke-dasharray": "3 3" }, g);
          txt(x + 80, y + 25, "capa de escritura", { "text-anchor": "middle", fill: C.lento, "font-size": 10 }, g);
          txt(x + 80, y + 60, n, { "text-anchor": "middle", "font-family": "Space Grotesk", "font-size": 15, "font-weight": 600 }, g);
          txt(x + 80, y + 82, `ROBOT=${rb}`, { "text-anchor": "middle", fill: C.r, "font-size": 11 }, g);
          txt(x + 80, y + 100, `IP 192.168.20${ip}`, { "text-anchor": "middle", fill: C.suave, "font-size": 10 }, g);
          // imagen debajo (solo lectura), compartida
          el("rect", { x: x + 8, y: y + 150, width: 144, height: 58, rx: 4, fill: C.docker + "18", stroke: C.docker, "stroke-opacity": .6 }, g);
          txt(x + 80, y + 176, "imagen robot", { "text-anchor": "middle", fill: C.docker, "font-size": 10 }, g);
          txt(x + 80, y + 192, "(compartida)", { "text-anchor": "middle", fill: C.suave, "font-size": 9 }, g);
          const estado = txt(x + 80, y + 128, "", { "text-anchor": "middle", "font-size": 11, "font-weight": 600 }, g);
          const proc = el("circle", { cx: x + 146, cy: y + 52, r: 5, fill: "#3a4048" }, g);
          g.style.opacity = 0;
          return { g, flechaE, estado, proc, x, y };
        });
        txt(450, 404, "", { id: "rotulo", "text-anchor": "middle", "font-size": 12.5 });
        return { conts };
      },
      async correr(r, tk) {
        for (const c of r.conts) {
          rotulo(`docker compose crea ${c.g.querySelector("text:nth-of-type(2)").textContent}…`, C.suave);
          await animar(500, (t) => { c.flechaE.setAttribute("stroke-dashoffset", 900 * (1 - t)); }, tk);
          c.estado.textContent = "Created"; c.estado.setAttribute("fill", C.lento);
          await aparecer(c.g, tk, 300);
          await esperar(300, tk);
          c.estado.textContent = "Starting"; await esperar(350, tk);
          c.estado.textContent = "Up · running"; c.estado.setAttribute("fill", C.ok); c.proc.setAttribute("fill", C.ok);
        }
        rotulo("tres contenedores de la MISMA imagen, cada uno con su proceso, su IP y su capa de escritura", C.txt);
        // latidos (HB) hacia el admin
        for (let k = 0; k < 2; k++) {
          const ps = r.conts.map((c) => paquete(C.ok, k ? "" : "HB"));
          await Promise.all(r.conts.map((c, i) => mover(ps[i], [[c.x + 146, c.y + 52], [c.x + 146, 30]], 900, tk)));
          ps.forEach((p) => p.remove());
        }
        rotulo("cada uno manda su latido (HB) al admin una vez por segundo", C.ok);
        await esperar(2500, tk);
      },
      prueba() {
        const cs = (D.contenedores || []).filter((c) => /robot/.test(c.imagen || ""));
        if (cs.length) {
          return `<p class="c11-nota">En <b>tu Docker</b> ahora (<span class="c11-mono">docker ps</span>), los contenedores de la imagen
            <span class="c11-mono">zonas-esp32-robot:1.0</span>:</p>
            <table class="c11-tabla"><tbody>${cs.map((c) => `<tr><td class="c11-mono">${esc(c.servicio)}</td><td><span class="c11-insignia ${c.estado === "running" ? "OK" : "CAIDO"}">${esc(c.estado)}</span></td><td class="c11-nota" style="font-size:.72rem">${esc(c.texto)}</td></tr>`).join("")}</tbody></table>
            <p class="c11-nota" style="margin-top:.4rem">Y la imagen <span class="c11-mono">emulador</span> tiene ${(D.contenedores || []).filter((c) => /emulador/.test(c.imagen || "")).length} contenedores (los ESP32 emulados).</p>`;
        }
        return `<p class="c11-nota">Con el laboratorio levantado y "Mirar en vivo" activo, aquí salen los tres contenedores reales de la
          imagen robot con su estado (<span class="c11-mono">running</span>) y cuánto llevan encendidos.</p>
          <p class="c11-nota">En la entrega: 16 contenedores salen de solo <b>6 imágenes</b> (robot ×3, jugador ×3, emulador ×7, y una de router, admin y pista).</p>`;
      },
    },

    // ---------------------------------------------------------------- 3. red / VLAN
    {
      titulo: "La red: tres switches virtuales, como tres VLAN",
      explica: `<p>Cada red del <span class="c11-mono">docker-compose.yml</span> es una <b>red bridge</b>: un switch virtual dentro del PC.
        Cada contenedor se "enchufa" con su cable virtual (<span class="c11-mono">veth</span>) y una <b>IP fija</b>.</p>
        <p>Un mensaje a todos (un <b>broadcast</b>, como la pregunta ARP "¿quién tiene 192.168.10.10?") llega a todos los de <b>su</b>
        red y a nadie más: son tres dominios de broadcast separados, igual que tres VLAN. Docker además impide el paso directo entre
        bridges (reglas <span class="c11-mono">DOCKER-ISOLATION</span>). El único que está en las tres es el router.</p>`,
      dibujar() {
        const redes = [
          ["vlan1_gamer · 192.168.10.0/24", C.g, 95, ["track-server .10", "player-1 .21", "player-2 .22", "player-3 .23", "ctrl-1 .31", "ctrl-2 .32", "ctrl-3 .33"]],
          ["vlan2_robotica · 192.168.20.0/24", C.r, 225, ["sim-spot .21", "sim-pepper .22", "sim-nao .23", "ctrl-spot .31", "ctrl-pepper .32", "ctrl-nao .33"]],
          ["vlan3_admin · 192.168.30.0/24", C.a, 355, ["admin .10", "esclava .40"]],
        ];
        const R = redes.map(([nombre, color, y, nodos]) => {
          el("rect", { x: 20, y, width: 760, height: 12, rx: 6, fill: color + "55", stroke: color });
          txt(24, y + 30, nombre, { fill: color, "font-size": 11, "font-weight": 600 });
          const cajas = nodos.map((n, i) => {
            const x = 30 + i * 106;
            el("line", { x1: x + 48, y1: y - 18, x2: x + 48, y2: y, stroke: color, "stroke-width": 1.5 });
            const r = el("rect", { x, y: y - 56, width: 96, height: 38, rx: 6, fill: color + "1a", stroke: color });
            const [id, ip] = n.split(" ");
            txt(x + 48, y - 38, id, { "text-anchor": "middle", "font-size": 10.5, "font-weight": 600 });
            txt(x + 48, y - 25, ip, { "text-anchor": "middle", fill: C.suave, "font-size": 9.5 });
            return { r, x: x + 48, y };
          });
          return { color, y, cajas };
        });
        // router: en las tres redes
        el("rect", { x: 800, y: 40, width: 84, height: 330, rx: 10, fill: "#13263a", stroke: C.rt, "stroke-width": 2 });
        txt(842, 66, "router", { "text-anchor": "middle", fill: C.rt, "font-weight": 600 });
        for (const r of R) { el("line", { x1: 780, y1: r.y + 6, x2: 800, y2: r.y + 6, stroke: C.rt, "stroke-width": 2.5 }); txt(842, r.y + 10, ".254", { "text-anchor": "middle", fill: C.rt, "font-size": 11 }); }
        txt(450, 404, "", { id: "rotulo", "text-anchor": "middle", "font-size": 12.5 });
        return { R };
      },
      async correr(r, tk) {
        const difusion = async (red, origen, pregunta, quien) => {
          rotulo(pregunta, red.color);
          const o = red.cajas[origen];
          o.r.setAttribute("stroke-width", 3);
          const ps = red.cajas.filter((_, i) => i !== origen).map(() => paquete(red.color, ""));
          await Promise.all(ps.map((p, i) => {
            const d = red.cajas.filter((_, j) => j !== origen)[i];
            return mover(p, [[o.x, red.y + 6], [d.x, red.y + 6], [d.x, red.y - 30]], 1100, tk);
          }));
          ps.forEach((p) => p.remove());
          red.cajas.forEach((c) => c.r.setAttribute("fill", red.color + "44"));
          // las otras redes no se enteran
          for (const otra of r.R) if (otra !== red) otra.cajas.forEach((c) => { c.r.style.opacity = 0.35; });
          await esperar(700, tk);
          rotulo(quien, red.color);
          await esperar(1600, tk);
          red.cajas.forEach((c) => c.r.setAttribute("fill", red.color + "1a"));
          o.r.setAttribute("stroke-width", 1);
          for (const otra of r.R) otra.cajas.forEach((c) => { c.r.style.opacity = 1; });
        };
        await difusion(r.R[0], 1, "player-1 pregunta a todos (broadcast ARP): ¿quién tiene 192.168.10.10?", "le llega a los 6 de la VLAN 1 y a nadie de las otras dos redes: track-server contesta \"soy yo\"");
        await difusion(r.R[1], 2, "sim-nao hace lo mismo en la VLAN 2…", "…y solo se entera la VLAN 2. Tres redes = tres dominios de broadcast, como tres VLAN");
        rotulo("el router está en las tres (.254), pero no reenvía broadcasts: solo paquetes con destino, y según sus reglas", C.rt);
        await esperar(2600, tk);
      },
      prueba() {
        const redes = D.redes;
        const n = (re) => (D.contenedores || []).filter((c) => re.test(c.servicio || "")).length;
        if (redes && redes.length) {
          return `<p class="c11-nota">Las redes que <b>tu Docker</b> tiene creadas (<span class="c11-mono">docker network inspect</span>):</p>
            <table class="c11-tabla"><tbody>${redes.map((r) => `<tr><td class="c11-mono">${esc(r.nombre)}</td><td class="c11-mono">${r.existe ? esc(r.subred) : '<span class="c11-insignia CAIDO">no existe</span>'}</td></tr>`).join("")}</tbody></table>
            ${D.contenedores && D.contenedores.length ? `<p class="c11-nota" style="margin-top:.4rem">Contenedores conectados: ${n(/^(track|player|ctrl-\d)/)} en la VLAN 1, ${n(/^(sim-|ctrl-(spot|pepper|nao))/)} en la VLAN 2 y ${n(/^(admin|esclava)/)} en la VLAN 3, más el router en las tres.</p>` : ""}`;
        }
        return `<p class="c11-nota">Del <span class="c11-mono">docker-compose.yml</span>:</p>
          <pre class="c11-cmd">networks:
  vlan1_gamer:    subnet 192.168.10.0/24
  vlan2_robotica: subnet 192.168.20.0/24
  vlan3_admin:    subnet 192.168.30.0/24</pre>
          <p class="c11-nota">Con "Mirar en vivo" se leen de tu Docker.</p>`;
      },
    },

    // ---------------------------------------------------------------- 4. router
    {
      titulo: "El router: el único camino entre redes",
      explica: `<p>El router es <b>otro contenedor</b> (Alpine + FRR + iptables) conectado a las tres redes, con la IP
        <span class="c11-mono">.254</span> en cada una y <span class="c11-mono">ip_forward=1</span>: recibe un paquete por una pata y lo
        reenvía por otra.</p>
        <p>Cada contenedor agrega al arrancar una ruta "para la red del admin, ve por mi .254". Así el admin hace ping a la zona gamer
        y a la robótica <b>pasando por el router</b>. La prueba de que cruzó exactamente un router es el <b>TTL</b>: sale con 64, el
        router le resta 1, y la respuesta llega con <span class="c11-mono">ttl=63</span>.</p>`,
      dibujar() {
        const P = dibujarZonas();
        const ruta = txt(450, 272, "", { "text-anchor": "middle", fill: C.suave, "font-size": 10.5 });
        return { P, ruta };
      },
      async correr(r, tk) {
        const P = r.P;
        for (const [dest, color] of [["player-1", C.g], ["sim-nao", C.r]]) {
          r.ruta.textContent = `admin: ip route ${dest === "player-1" ? "192.168.10.0/24" : "192.168.20.0/24"} via 192.168.30.254`;
          rotulo(`ping desde el admin a ${dest}: el paquete sale con TTL 64`, C.a);
          const p = paquete(C.a, "TTL 64");
          await mover(p, [P.admin, [450, 300], P.router], 1000, tk);
          p.etiqueta.textContent = "TTL 63"; p.etiqueta.setAttribute("fill", C.lento);
          rotulo("el router lo deja pasar (admin → zona: permitido) y le resta 1 al TTL", C.rt);
          await esperar(700, tk);
          await mover(p, [P.router, dest === "player-1" ? [300, 150] : [600, 150], P[dest]], 1000, tk);
          p.remove();
          await bien(P[dest][0], P[dest][1] - 34, "", tk).catch((e) => { throw e; });
          rotulo(`${dest} contesta; la respuesta vuelve por el router y llega con ttl=63 (un salto)`, color);
          const q = paquete(color, "respuesta");
          await mover(q, [P[dest], dest === "player-1" ? [300, 150] : [600, 150], P.router, [450, 300], P.admin], 1500, tk);
          q.remove();
          await bien(P.admin[0] + 96, P.admin[1], "ttl=63", tk);
        }
        r.ruta.textContent = "";
        await esperar(1200, tk);
      },
      prueba() {
        const a = D.aislamiento;
        if (a && a.casos) {
          const ttl = a.casos.filter((c) => /ttl 63/.test(c.caso));
          const okTtl = ttl.filter((c) => c.resultado === "APROBADA").length;
          const tr = a.casos.filter((c) => /^traceroute/.test(c.caso));
          return `<p class="c11-nota">De la prueba de aislamiento (${esc(new Date((a.fecha_epoch || 0) * 1000).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" }))}):</p>
            <div class="c11-cifras" style="grid-template-columns:repeat(2,minmax(0,1fr));margin:.3rem 0">
              <div class="c11-cifra"><b class="c11-zona-g">${okTtl}/${ttl.length}</b><span>respuestas al admin con ttl=63</span></div>
              <div class="c11-cifra"><b class="c11-zona-g">${tr.filter((c) => c.resultado === "APROBADA").length}/${tr.length}</b><span>traceroute: salto 1 = el router</span></div>
            </div>
            <pre class="c11-cmd">${tr.map((c) => esc(c.caso.replace(/^traceroute /, ""))).join("\n")}</pre>`;
        }
        return `<p class="c11-nota">Corre la prueba de aislamiento (paso "Las pruebas") para verlo con tu laboratorio.</p>`;
      },
    },

    // ---------------------------------------------------------------- 5. DROP
    {
      titulo: "El DROP: de la zona gamer a la robótica no se pasa",
      explica: `<p>¿Y si player-1 intenta hablarle a sim-nao? <b>Sin ruta</b>, el paquete sale por la puerta por defecto
        (<span class="c11-mono">.1</span>, la de Docker) y Docker lo descarta: no deja pasar entre bridges.</p>
        <p>Si alguien <b>fuerza la ruta</b> por el router (<span class="c11-mono">ip route add 192.168.20.0/24 via 192.168.10.254</span>),
        el paquete llega al router… y el cortafuegos lo tira: la regla VLAN 1 ↔ VLAN 2 lo manda a la cadena
        <span class="c11-mono">AISLAR_V1_V2</span>, que lo <b>descarta (DROP) y lo cuenta</b>. Ese contador es la prueba de que quien
        bloquea es el router. El admin, en cambio, sí pasa.</p>`,
      dibujar() {
        const P = dibujarZonas();
        // puerta .1 de Docker bajo la VLAN 1
        el("rect", { x: 105, y: 245, width: 120, height: 34, rx: 6, fill: "rgba(36,150,237,.12)", stroke: C.docker, "stroke-dasharray": "4 3" });
        txt(165, 260, "puerta .1", { "text-anchor": "middle", fill: C.docker, "font-size": 11, "font-weight": 600 });
        txt(165, 273, "(Docker)", { "text-anchor": "middle", fill: C.suave, "font-size": 9.5 });
        el("line", { x1: 165, y1: 200, x2: 165, y2: 245, stroke: C.docker, "stroke-dasharray": "3 3" });
        // contador
        const cg = grupo({});
        el("rect", { x: 640, y: 228, width: 220, height: 56, rx: 8, fill: "rgba(217,83,79,.1)", stroke: C.mal }, cg);
        txt(750, 248, "router · cadena AISLAR_V1_V2", { "text-anchor": "middle", fill: C.mal, "font-size": 10.5 }, cg);
        const n = txt(750, 274, "0 paquetes descartados", { "text-anchor": "middle", fill: "#ff8a86", "font-size": 13, "font-weight": 700 }, cg);
        const ruta = txt(450, 272, "", { "text-anchor": "middle", fill: C.suave, "font-size": 10.5 });
        return { P, n, ruta, cuenta: 0 };
      },
      async correr(r, tk) {
        const P = r.P;
        const sumar = () => { r.cuenta++; r.n.textContent = `${r.cuenta} paquete${r.cuenta === 1 ? "" : "s"} descartado${r.cuenta === 1 ? "" : "s"}`; };
        // A) sin ruta
        rotulo("player-1 → sim-nao SIN ruta: el paquete sale por la puerta .1 de Docker…", C.g);
        let p = paquete(C.g, "ping");
        await mover(p, [P["player-1"], [165, 200], [165, 245]], 1000, tk);
        p.remove();
        rotulo("…y Docker lo descarta (DOCKER-ISOLATION): no deja cruzar entre bridges", C.mal);
        await explotar(165, 262, "DOCKER-ISOLATION", tk);
        // B) ruta forzada
        r.ruta.textContent = "player-1: ip route add 192.168.20.0/24 via 192.168.10.254  (ruta forzada a mano)";
        rotulo("ahora con la ruta forzada: el paquete SÍ llega al router…", C.g);
        p = paquete(C.g, "ping");
        await mover(p, [P["player-1"], [300, 150], P.router], 1300, tk);
        p.remove();
        sumar();
        rotulo("…y el router lo tira: regla VLAN 1 → VLAN 2 ⇒ AISLAR_V1_V2 (DROP) y el contador sube", C.mal);
        await explotar(P.router[0], P.router[1], "DROP", tk);
        // C) al revés, por TCP
        r.ruta.textContent = "sim-spot: TCP a track-server:8765 con la ruta forzada";
        rotulo("lo mismo al revés, de la zona robótica a la gamer, por TCP (el WebSocket de la pista)", C.r);
        p = paquete(C.r, "TCP");
        await mover(p, [P["sim-spot"], [600, 150], P.router], 1300, tk);
        p.remove(); sumar();
        await explotar(P.router[0], P.router[1], "DROP", tk);
        // D) el admin sí pasa
        r.ruta.textContent = "";
        rotulo("en cambio, del admin a sim-nao: permitido. El paquete cruza y vuelve", C.a);
        p = paquete(C.a, "ping");
        await mover(p, [P.admin, [450, 300], P.router, [600, 150], P["sim-nao"]], 1600, tk);
        p.remove();
        await bien(P["sim-nao"][0], P["sim-nao"][1] - 34, "", tk);
        rotulo("solo se cruza lo que la lista blanca permite: admin ↔ zonas. Gamer ↔ robótica: nunca", C.txt);
        await esperar(2200, tk);
      },
      prueba() {
        const a = D.aislamiento;
        if (a && a.resumen) {
          const ini = ((a.router || {}).drops_inicio || {}).por_cadena || {};
          const fin = ((a.router || {}).drops_fin || {}).por_cadena || {};
          const bloq = (a.casos || []).filter((c) => c.esperado === "FALLA");
          return `<p class="c11-nota">De la prueba real de aislamiento (contra los 16 contenedores):</p>
            <div class="c11-cifras" style="grid-template-columns:repeat(2,minmax(0,1fr));margin:.3rem 0">
              <div class="c11-cifra"><b style="color:#ff8a86">${esc(ini.AISLAR_V1_V2 ?? "?")} → ${esc(fin.AISLAR_V1_V2 ?? "?")}</b><span>paquetes en AISLAR_V1_V2 (el DROP del router)</span></div>
              <div class="c11-cifra"><b class="c11-zona-g">${bloq.filter((c) => c.resultado === "APROBADA").length}/${bloq.length}</b><span>intentos gamer ↔ robótica bloqueados</span></div>
            </div>
            <p class="c11-nota">Veredicto: <span class="c11-insignia ${esc(a.resumen.veredicto)}">${esc(a.resumen.veredicto)}</span> · ${esc(a.resumen.aprobadas)}/${esc(a.resumen.casos)} casos.</p>
            <div class="c11-botonera"><button class="c11-btn primario" data-ir="Las pruebas">Correr la prueba de verdad (~30 s)</button></div>`;
        }
        return `<div class="c11-botonera"><button class="c11-btn primario" data-ir="Las pruebas">Ir a la prueba de aislamiento</button></div>`;
      },
    },

    // ---------------------------------------------------------------- 6. compose
    {
      titulo: "docker compose up: todo, en orden",
      explica: `<p><span class="c11-mono">docker compose --profile emulado up -d</span> lee el <span class="c11-mono">docker-compose.yml</span> y hace
        todo lo anterior solo: <b>1)</b> consigue las 6 imágenes (las baja de Docker Hub o las construye), <b>2)</b> crea las 3 redes,
        <b>3)</b> arranca primero el router (los demás lo esperan: <span class="c11-mono">depends_on</span>), <b>4)</b> el admin y las zonas,
        <b>5)</b> los 7 ESP32 emulados. Al final el admin empieza a recibir latidos y pings y prende los 6 LED.</p>
        <p>Esto mismo es lo que hace el botón "Levantar el laboratorio", con su progreso real.</p>`,
      dibujar() {
        const cols = [
          ["1 · imágenes", C.docker, ["router", "admin", "pista", "jugador", "robot", "emulador"]],
          ["2 · redes", C.txt, ["vlan1_gamer", "vlan2_robotica", "vlan3_admin"]],
          ["3 · router", C.rt, ["router"]],
          ["4 · admin y zonas", C.a, ["admin", "track-server", "player-1..3", "sim-spot", "sim-pepper", "sim-nao"]],
          ["5 · ESP32 emulados", C.r, ["ctrl-1..3", "ctrl-spot", "ctrl-pepper", "ctrl-nao", "esclava"]],
        ];
        const G = cols.map(([t, color, items], i) => {
          const x = 18 + i * 176;
          txt(x + 4, 44, t, { fill: color, "font-size": 12, "font-weight": 600 });
          const filas = items.map((it, j) => {
            const g = grupo({});
            el("rect", { x, y: 58 + j * 34, width: 160, height: 28, rx: 5, fill: C.panel, stroke: C.borde }, g);
            const tt = txt(x + 10, 76 + j * 34, it, { "font-size": 11 }, g);
            const v = txt(x + 150, 76 + j * 34, "", { "font-size": 12, "text-anchor": "end", fill: C.ok, "font-weight": 700 }, g);
            g.style.opacity = 0.35;
            return { g, tt, v, r: g.querySelector("rect") };
          });
          return { filas, color };
        });
        // fila de LED
        const leds = ["player-1", "player-2", "player-3", "sim-spot", "sim-pepper", "sim-nao"].map((n, i) => {
          const x = 120 + i * 120;
          const c = el("circle", { cx: x, cy: 330, r: 14, fill: "#26302b", stroke: "#3a4a42", "stroke-width": 2 });
          txt(x, 360, n, { "text-anchor": "middle", "font-size": 10.5, fill: C.suave });
          return c;
        });
        txt(450, 300, "ESP32 esclava · 6 LED", { "text-anchor": "middle", fill: "#7fb79c", "font-size": 10.5 });
        txt(450, 404, "", { id: "rotulo", "text-anchor": "middle", "font-size": 12.5 });
        return { G, leds };
      },
      async correr(r, tk) {
        const textos = ["consigue las imágenes (pull o build)", "crea las 3 redes bridge", "arranca primero el router (depends_on)", "arranca el admin y las dos zonas", "arranca los 7 ESP32 emulados"];
        for (let i = 0; i < r.G.length; i++) {
          rotulo(`paso ${i + 1}: ${textos[i]}`, r.G[i].color);
          for (const f of r.G[i].filas) {
            f.g.style.opacity = 1; f.r.setAttribute("stroke", r.G[i].color);
            await esperar(i === 0 ? 260 : 200, tk);
            f.v.textContent = "✓";
          }
          await esperar(350, tk);
        }
        rotulo("el admin recibe latidos y pings: prende los LED uno por uno", C.ok);
        for (const c of r.leds) {
          c.setAttribute("fill", "#6bf0a5"); c.setAttribute("stroke", "#9ff7c6");
          c.style.filter = "drop-shadow(0 0 6px #4cf09a)";
          await esperar(260, tk);
        }
        rotulo("laboratorio arriba: 16 contenedores, 3 redes, 6 LED encendidos", C.ok);
        await esperar(3000, tk);
      },
      prueba() {
        const s = D.subida;
        const fila = (n, v) => `<tr><td>${esc(n)}</td><td class="num">${esc(v)}</td></tr>`;
        if (s && s.total) {
          return `<p class="c11-nota">La última vez que lo levantaste desde esta app (tiempos reales leídos de <span class="c11-mono">docker compose</span>):</p>
            <table class="c11-tabla"><tbody>${fila("imágenes", s.imagenes)}${fila("redes", s.redes)}${fila("contenedores", s.contenedores)}${fila("total", s.total)}</tbody></table>
            <div class="c11-botonera"><button class="c11-btn" data-ir="El laboratorio en vivo">Ver el laboratorio en vivo</button></div>`;
        }
        return `<p class="c11-nota">Tiempos típicos: <b>~30 s</b> con las imágenes ya en el PC; <b>2 a 6 min</b> la primera vez (baja ~415 MB);
          <b>10 a 20 min</b> construyendo desde el código.</p>
          <div class="c11-botonera"><button class="c11-btn primario" data-ir="Levantar el laboratorio">Levantarlo ahora</button></div>`;
      },
    },
  ];

  // ------------------------------------------------------------------ control
  function pintarTexto() {
    const e = ESCENAS[escena];
    document.getElementById("animNum").textContent = `Escena ${escena + 1} de ${ESCENAS.length}`;
    document.getElementById("animTitulo").textContent = e.titulo;
    document.getElementById("animExplica").innerHTML = e.explica;
    pintarPrueba();
    document.querySelectorAll("#animPuntos button").forEach((b, i) => b.classList.toggle("activo", i === escena));
  }
  function pintarPrueba() {
    const caja = document.getElementById("animPrueba");
    if (!caja) return;
    caja.innerHTML = ESCENAS[escena].prueba();
    caja.querySelectorAll("[data-ir]").forEach((b) => { b.onclick = () => alIr && alIr(b.dataset.ir); });
  }

  async function correrEscena() {
    const tk = ++token;
    svg.innerHTML = "";
    const e = ESCENAS[escena];
    const refs = e.dibujar();
    if (!reproduciendo || !visible) return;   // quieto: se queda el dibujo inicial
    try {
      await e.correr(refs, tk);
      if (tk === token && reproduciendo && visible) ir(escena + 1);
    } catch (err) {
      if (err !== CANCELADA) console.error(err);
    }
  }

  function ir(i) {
    escena = (i + ESCENAS.length) % ESCENAS.length;
    pintarTexto();
    correrEscena();
  }

  function pintarBotonPlay() {
    const b = document.getElementById("animPlay");
    b.textContent = reproduciendo ? "❚❚ Pausa" : "▶ Reproducir";
  }

  window.DockerAnim = {
    iniciar(opciones = {}) {
      svg = document.getElementById("animSvg");
      if (!svg) return;
      alIr = opciones.alIr || null;
      const puntos = document.getElementById("animPuntos");
      puntos.innerHTML = ESCENAS.map((e, i) => `<button title="${esc(e.titulo)}" aria-label="Escena ${i + 1}">${i + 1}</button>`).join("");
      puntos.querySelectorAll("button").forEach((b, i) => { b.onclick = () => ir(i); });
      document.getElementById("animAnt").onclick = () => ir(escena - 1);
      document.getElementById("animSig").onclick = () => ir(escena + 1);
      document.getElementById("animPlay").onclick = () => { reproduciendo = !reproduciendo; pintarBotonPlay(); correrEscena(); };
      pintarBotonPlay();
      pintarTexto();
      correrEscena();
    },
    /** Se llama al entrar o salir del paso: fuera de la vista no se anima (no gasta CPU). */
    visible(v) {
      if (!svg || v === visible) return;
      visible = v;
      if (v) correrEscena(); else token++;
    },
    datos(nuevos) {
      Object.assign(D, nuevos);
      if (svg) pintarPrueba();
    },
    irA: (i) => ir(i),
    get escena() { return escena; },
  };
})();
