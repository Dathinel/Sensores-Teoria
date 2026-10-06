// La CNN del punto 2 en el navegador: los MISMOS pesos de modelo_mnist_cnn.h5 (exportados a
// cnn-pesos.bin por exportar_pesos_web.py, en int8) y el MISMO preprocesamiento que
// preprocesar_digito() de reconocer_digito.py, para el caso del lienzo (trazo negro sobre blanco).
// No usa ninguna librería: son unas pocas sumas y multiplicaciones (~2,6 millones por imagen).
// Funciona en el navegador (window.CNN) y en Node (module.exports) para poder probarla.
(function (raiz) {
  "use strict";

  // ── Pesos ──────────────────────────────────────────────────────────────────────────────
  // Capas en el orden del archivo: [salidas, entradas por salida]
  const FORMA = [["conv1", 32, 9], ["conv2", 64, 288], ["densa", 128, 1600], ["salida", 10, 128]];
  function leerPesos(buffer) {
    const capas = {}; let pos = 0;
    for (const [nombre, nSal, nEnt] of FORMA) {
      const q = new Int8Array(buffer, pos, nSal * nEnt); pos += nSal * nEnt;
      const esc = new Float32Array(buffer.slice(pos, pos + 4 * nSal)); pos += 4 * nSal;
      const sesgo = new Float32Array(buffer.slice(pos, pos + 4 * nSal)); pos += 4 * nSal;
      const w = new Float32Array(nSal * nEnt);
      for (let s = 0; s < nSal; s++) for (let e = 0; e < nEnt; e++) w[s * nEnt + e] = q[s * nEnt + e] * esc[s];
      capas[nombre] = { w, sesgo, nSal, nEnt };
    }
    return capas;
  }

  // ── Capas (canales al final, como Keras: índice = (fila * ancho + col) * canales + c) ─────
  function conv3x3Relu(x, H, W, C, capa) {           // padding "valid": sale (H-2) x (W-2)
    const H2 = H - 2, W2 = W - 2, S = capa.nSal, y = new Float32Array(H2 * W2 * S);
    for (let i = 0; i < H2; i++) for (let j = 0; j < W2; j++) for (let s = 0; s < S; s++) {
      let suma = capa.sesgo[s]; const base = s * capa.nEnt; let k = 0;
      for (let di = 0; di < 3; di++) for (let dj = 0; dj < 3; dj++) {
        const px = ((i + di) * W + (j + dj)) * C;
        for (let c = 0; c < C; c++) suma += x[px + c] * capa.w[base + k++];
      }
      y[(i * W2 + j) * S + s] = suma > 0 ? suma : 0;   // ReLU
    }
    return y;
  }
  function maxPool2(x, H, W, C) {                      // 2x2, paso 2 (descarta la fila/columna impar)
    const H2 = Math.floor(H / 2), W2 = Math.floor(W / 2), y = new Float32Array(H2 * W2 * C);
    for (let i = 0; i < H2; i++) for (let j = 0; j < W2; j++) for (let c = 0; c < C; c++) {
      const a = x[((2 * i) * W + 2 * j) * C + c], b = x[((2 * i) * W + 2 * j + 1) * C + c];
      const d = x[((2 * i + 1) * W + 2 * j) * C + c], e = x[((2 * i + 1) * W + 2 * j + 1) * C + c];
      y[(i * W2 + j) * C + c] = Math.max(a, b, d, e);
    }
    return y;
  }
  function densa(x, capa, relu) {
    const y = new Float32Array(capa.nSal);
    for (let s = 0; s < capa.nSal; s++) {
      let suma = capa.sesgo[s]; const base = s * capa.nEnt;
      for (let e = 0; e < capa.nEnt; e++) suma += x[e] * capa.w[base + e];
      y[s] = relu && suma < 0 ? 0 : suma;
    }
    return y;
  }
  function softmax(z) {
    const m = Math.max(...z), ex = Array.from(z, (v) => Math.exp(v - m)), t = ex.reduce((a, b) => a + b, 0);
    return ex.map((v) => v / t);
  }

  // entrada: Float32Array(784) con valores 0..1 (28x28, fondo negro, trazo blanco).
  // Devuelve las probabilidades y lo que pasa por dentro (para dibujarlo).
  function predecir(capas, entrada) {
    const c1 = conv3x3Relu(entrada, 28, 28, 1, capas.conv1);      // 26x26x32: bordes y trazos
    const p1 = maxPool2(c1, 26, 26, 32);                            // 13x13x32
    const c2 = conv3x3Relu(p1, 13, 13, 32, capas.conv2);           // 11x11x64: piezas (lazos, esquinas)
    const p2 = maxPool2(c2, 11, 11, 64);                            // 5x5x64 = 1600
    const d1 = densa(p2, capas.densa, true);                        // 128
    const z = densa(d1, capas.salida, false);                       // 10
    return { probabilidades: softmax(z), conv1: c1, conv2: c2, densa: d1 };
  }

  // ── Preprocesamiento (igual que preprocesar_digito() para un lienzo limpio) ───────────────
  // gris: Uint8Array (lado x lado), 255 = papel blanco, 0 = tinta negra.
  // Devuelve {entrada: Float32Array(784), caja: [x, y, w, h]} o null si no hay dígito.
  function preprocesar(gris, lado) {
    // 1.1-1.3 El lienzo ya es gris y limpio: el umbral (Otsu) separa tinta (255) de papel (0).
    const bin = new Uint8Array(lado * lado);
    for (let i = 0; i < bin.length; i++) bin[i] = gris[i] < 128 ? 255 : 0;
    // 1.5 Componentes conectadas: nos quedamos con la más grande (como el contorno mayor)
    const etiqueta = new Int32Array(lado * lado); let mejor = null; let n = 0;
    for (let p = 0; p < bin.length; p++) {
      if (!bin[p] || etiqueta[p]) continue;
      n++; const pila = [p]; etiqueta[p] = n;
      let x0 = lado, y0 = lado, x1 = -1, y1 = -1;
      while (pila.length) {
        const q = pila.pop(), qx = q % lado, qy = (q - qx) / lado;
        if (qx < x0) x0 = qx; if (qx > x1) x1 = qx; if (qy < y0) y0 = qy; if (qy > y1) y1 = qy;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          const nx = qx + dx, ny = qy + dy;
          if (nx < 0 || ny < 0 || nx >= lado || ny >= lado) continue;
          const r = ny * lado + nx;
          if (bin[r] && !etiqueta[r]) { etiqueta[r] = n; pila.push(r); }
        }
      }
      const area = (x1 - x0 + 1) * (y1 - y0 + 1);
      if (!mejor || area > mejor.area) mejor = { n, x0, y0, w: x1 - x0 + 1, h: y1 - y0 + 1, area };
    }
    if (!mejor || mejor.area < 500) return null;            // "ignorar ruido"
    // 1.6 Recortar a su caja (como umbral[y:y+h, x:x+w]: entra todo lo que haya dentro)
    const { x0, y0, w, h } = mejor;
    let dig = new Uint8Array(w * h);
    for (let i = 0; i < h; i++) for (let j = 0; j < w; j++) dig[i * w + j] = bin[(y0 + i) * lado + (x0 + j)];
    // 1.7 Adelgazar si más del 45 % de la caja es trazo (erosión 5x5, hasta 3 veces)
    for (let vuelta = 0; vuelta < 3; vuelta++) {
      let pint = 0; for (const v of dig) if (v) pint++;
      if (pint / (w * h) <= 0.45) break;
      const e = new Uint8Array(w * h);
      for (let i = 0; i < h; i++) for (let j = 0; j < w; j++) {
        let todo = 255;
        for (let di = -2; di <= 2 && todo; di++) for (let dj = -2; dj <= 2; dj++) {
          const a = i + di, b = j + dj;
          if (a < 0 || b < 0 || a >= h || b >= w) continue;   // borde: no erosiona (como OpenCV)
          if (!dig[a * w + b]) { todo = 0; break; }
        }
        e[i * w + j] = todo;
      }
      dig = e;
    }
    // 1.8 Escalar el lado mayor a 20 px conservando la proporción (INTER_AREA = promedio por área)
    const nw = w > h ? 20 : Math.max(1, Math.round(20 * w / h));
    const nh = w > h ? Math.max(1, Math.round(20 * h / w)) : 20;
    let chico = new Float32Array(nw * nh);
    const fx = w / nw, fy = h / nh;
    for (let i = 0; i < nh; i++) for (let j = 0; j < nw; j++) {
      const ya = i * fy, yb = ya + fy, xa = j * fx, xb = xa + fx; let s = 0;
      for (let yy = Math.floor(ya); yy < Math.ceil(yb); yy++) {
        const wy = Math.min(yb, yy + 1) - Math.max(ya, yy);
        for (let xx = Math.floor(xa); xx < Math.ceil(xb); xx++) {
          const wx = Math.min(xb, xx + 1) - Math.max(xa, xx);
          s += dig[Math.min(h - 1, yy) * w + Math.min(w - 1, xx)] * wx * wy;
        }
      }
      chico[i * nw + j] = Math.round(s / (fx * fy));
    }
    // 1.9 Desenfoque gaussiano 3x3 ([1 2 1]/4 en cada eje, borde reflejado como OpenCV)
    const refl = (k, n) => (n === 1 ? 0 : k < 0 ? -k : k >= n ? 2 * n - 2 - k : k);
    const tmp = new Float32Array(nw * nh), suave = new Float32Array(nw * nh);
    for (let i = 0; i < nh; i++) for (let j = 0; j < nw; j++)
      tmp[i * nw + j] = (chico[i * nw + refl(j - 1, nw)] + 2 * chico[i * nw + j] + chico[i * nw + refl(j + 1, nw)]) / 4;
    for (let i = 0; i < nh; i++) for (let j = 0; j < nw; j++)
      suave[i * nw + j] = Math.round((tmp[refl(i - 1, nh) * nw + j] + 2 * tmp[i * nw + j] + tmp[refl(i + 1, nh) * nw + j]) / 4);
    // 1.10 Pegar en 28x28 negro, centrado por el CENTRO DE MASA (no por la caja)
    let m00 = 0, m10 = 0, m01 = 0;
    for (let i = 0; i < nh; i++) for (let j = 0; j < nw; j++) { const v = suave[i * nw + j]; m00 += v; m10 += j * v; m01 += i * v; }
    const cx = m00 ? Math.trunc(m10 / m00) : Math.floor(nw / 2), cy = m00 ? Math.trunc(m01 / m00) : Math.floor(nh / 2);
    const entrada = new Float32Array(784);
    for (let i = 0; i < nh; i++) for (let j = 0; j < nw; j++) {
      const yi = i + 14 - cy, xj = j + 14 - cx;
      if (yi >= 0 && yi < 28 && xj >= 0 && xj < 28) entrada[yi * 28 + xj] = suave[i * nw + j] / 255;   // 1.11 /255
    }
    return { entrada, caja: [x0, y0, w, h] };
  }

  const CNN = { leerPesos, predecir, preprocesar };
  if (typeof module === "object" && module.exports) module.exports = CNN; else raiz.CNN = CNN;
})(typeof window !== "undefined" ? window : globalThis);
