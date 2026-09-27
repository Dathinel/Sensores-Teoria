# Contexto de sesión — LEER ANTES DE TOCAR NADA

Este archivo existe para que una sesión nueva sepa en qué va el proyecto sin gastar miles de
tokens buscando, y sobre todo **qué NO hacer**. Se actualiza al final de cada sesión.

## 1. Reglas estrictas del usuario (no negociables)

1. **Si el usuario dice que NO se haga algo, no se hace.** Nunca "mejorarlo" por cuenta propia.
2. **Leer el mensaje del usuario punto por punto**, listar cada pedido y verificar que TODOS
   quedaron atendidos antes de responder. Cada punto está escrito a propósito.
3. **Hacer solo lo que se pidió.** Nada de refactors grandes, mecanismos nuevos o sensores
   nuevos sin pedirlo. Si algo pedido implica un cambio grande o ambiguo: proponerlo en 2-3
   líneas y preguntar ANTES de implementar.
4. **Mundo real, no mundo perfecto:** el montaje se hace en Colombia, con sensores mal
   alineados, alturas distintas, ruido eléctrico, errores de tiempo y de movimiento, brisa,
   aceleraciones que tumban monedas y vasos. Diseñar para el error.
5. Si el usuario pregunta "¿puede asegurarme que X funciona?", responder con honestidad (los
   riesgos reales), no implementar primero.
6. Todo lo que exista en el diseño se modela en el 3D con su soporte (patas de servos,
   escuadras, tornillería visible si hace falta) para juzgar si es realista.
7. No hacer commit ni push sin que el usuario lo pida.

## 2. Prohibido (el usuario lo dijo explícitamente)

- **Celdas de carga** (y HX711): prohibidas. Son difíciles de acondicionar y dan problemas.
- Sensores difíciles de instalar, muy sensibles, caros o poco conocidos.
- Vasos transparentes (el usuario no los quiere).
- Agregar sensores "por si acaso" (el usuario quiere MENOS sensores y MENOS servos).

Preferidos (baratos y conocidos): TCRT5000/FC-51, VL53L0X, HC-SR04, webcam, SG90/MG90S/MG996R.

## 0. Pedido EN CURSO (se escribe AL EMPEZAR cada sesión, antes de tocar código)

Por qué existe: dos veces se cerró una sesión a la fuerza a mitad de trabajo y se perdió el
último mensaje del usuario. Regla: al empezar, copiar aquí el pedido textual y la lista de
puntos; al terminar cada punto, marcarlo. Si se pierde un mensaje, está completo en el
transcript de Claude Code: `~/.claude/projects/C--Users-danie-OneDrive-Escritorio-Micors-teoria/<sesion>.jsonl`
(líneas con `"type":"user"`; el más reciente por fecha de modificación).

**Reglas permanentes del usuario (2026-09-27):** responder SIEMPRE en español; dejar SIEMPRE la
app corriendo escondida (`python -m app.lanzar --auto prueba_completa --reemplazar` en segundo plano)
para que él vea visor y Streamlit cuando quiera; ahorrar tokens: antes de escribir lógica desde
cero, revisar el repo `Sensores-Teoria` (temas 1-9) que ya tiene patrones resueltos.

**Pedido del 2026-09-27 (tarde), textual resumido:**
> no se guardó que siempre responda en español, y que ejecute la consola escondida [...] revise la
> carpeta de sensores teoría que tiene lógica que ayuda a hacer más rápido las cosas; esta es la clave
> de deepseek [...] colóquela y pruebe; no me gusta el orden de las respuestas en el streamlit, salen
> hacia abajo [...] se escribe arriba y se ve abajo; en el visor 3D no quiero pestaña de asistente,
> solo la nubecita, solo lectura, un bloque de texto de lo que responde deepseek arriba de la nube o
> en la pantalla del PC, y un botón igual a los de arriba a la derecha que ponga la cámara para
> leerlo; vaya creando la fase 8 (no tengo las imágenes de las monedas), instalando cosas, metiendo
> lógica a cada parte, todo guardado en el contexto; organice carpetas y mejore lo de GitHub, haga
> commits; pase la carpeta entera de proyecto final a Sensores-Teoria (sin los respaldos) y súbala;
> mejore las demás actividades: lógica, presentación en GitHub, quitar texto irrelevante, poner
> datos y diagramas.

Puntos (marcar al terminar):
- [x] a. Memoria: responder en español (memory + aquí).
- [x] b. (DeepSeek la rechaza: 401, con y sin sk-; queda en .env) Clave de DeepSeek en `.env` (fuera de git) y probarla de verdad.
- [x] c. Streamlit: chat con lo más nuevo ARRIBA, pegado a la caja de escribir.
- [x] d. Visor: quitar pestaña Asistente; texto de la última respuesta sobre la nube / pantalla del
      PC (solo lectura); botón de vista "Asistente" en la barra de vistas.
- [ ] e. Mover `proyecto final/` dentro del repo `Sensores-Teoria/` (sin respaldos ni entorno), commits y push.
- [ ] f. Fase 8: firmware de los dos ESP32 + backend real de la HAL + puente serial, con pruebas.
- [ ] g. Mejorar los otros temas del repo (README con datos y diagramas, sin texto de relleno).
- [ ] h. Actualizar contexto, bitácora, CLAUDE.md.

## 3. Estado actual (2026-09-27, fin de sesión)

- Pruebas: `entorno/Scripts/python -m pytest -q` → todas deben pasar (528, ~4 min).
- Forma de trabajar (usuario, 2026-09-26): dejar SIEMPRE una corrida escondida con el código
  actual (`python -m app.lanzar --auto prueba_completa --reemplazar` en segundo plano; cierra la
  anterior y su consola). El usuario la mira cuando quiere con `visor.bat` (un clic). NO
  abrir consolas visibles ni el navegador del usuario, y NO mandarle links.
- Correr y mostrar: `entorno/Scripts/python -m app.lanzar --auto prueba_completa` y abrir
  `http://localhost:8765` (visor 3D) y `http://localhost:8501` (dashboard). **NO publicarlo como
  artefacto de Claude**: se abre en el navegador del PC. Si los puertos ya están ocupados es que
  el usuario lo tiene abierto: no cerrarlo; para verificar, levantar una copia en otro puerto.
- Paso a paso (`docs/paso-a-paso.yaml`, 16 puntos): 1-14 aprobados; **15 (protocolo) preaprobado**
  (2026-09-27), falta la aprobación del usuario; **16 (asistente y órdenes al carro) pendiente** de
  revisión.
- Decisiones vigentes: filtro total (cinta de monedas de 4 estaciones: presencia, material,
  visión, descarga; UNA bandeja de rechazo por la compuerta de desvío); cámara de vasos
  reemplaza barreras IR y sensores de ranura, y además vigila en cada avance que no falte ningún
  vaso en sus 4 casillas; marcador ArUco en CINTA alrededor del vaso; vasos OPACOS; qué hay
  dentro del vaso lo dice un **sensor que apunta hacia el interior del vaso** en la verificación
  (VL53L0X); vasos vacíos se desechan; canaleta llena → el vaso espera y la cinta de vasos se
  detiene; almacén revólver con Hall (aprobado); **cortina de UN solo VL53L0X a media altura,
  con su cono real; al activarse la prensa SUBE y se detiene**; prensa con servo MG996R;
  carro 2 ruedas + rueda loca con rodillos guía, va y vuelve solo (física real en PyBullet).
- Fase 7 (2026-09-27): asistente en `app/asistente.py` (DeepSeek con JSON como el tema 4 del repo;
  busca en toda la documentación; estado en vivo; lista blanca de órdenes; voz; intérprete local sin
  internet). Órdenes al carro por la radio: detener, avanzar, retroceder, girar, ir_a, ir_meta,
  volver_muelle, seguir_linea; odometría (a cero en el muelle), revisa el camino a 0/±15° y no choca;
  desde el muelle sale derecho antes de girar. Evasión automática: `margen_pasar_muro_mm: 70`
  (rozaba el muro con 1 de 11 semillas). Visor: nube de la API + pestaña Asistente (solo lectura).
- **Clave de DeepSeek:** la del tema 4 (`Sensores-Teoria/4-chatbot-asistente-voz/.env`) fue RECHAZADA
  (401). No hay `.env` en el proyecto final: el usuario tiene que poner una válida (`.env.example`).

## 4. Pendiente de decisión del usuario (no implementar sin respuesta)

- Revisión final hecha (`docs/revision-final.md`). Sensores de material bajo la cinta APROBADOS.
  Conexionado pin a pin en `sim/conexiones.py` (fuente única → visor, `docs/conexiones.md`,
  `tests/test_conexiones.py`). Punto 15 hecho y PREAPROBADO (protocolo en
  `control/protocolo.py`, contrato en CLAUDE.md 10.1): falta que el usuario lo apruebe.
  Mejora de interfaz hecha el 2026-09-27 (dashboard para cualquier persona, visor con
  encuadre automático, componentes completos). Fase 7 hecha el 2026-09-27. Siguiente: que el
  usuario apruebe el 15 y el 16, ponga la clave de DeepSeek, y elija la próxima fase (5 visión real,
  8 firmware o 9 documentación para la entrega del 29-09).
- UNA sola prueba en la interfaz: `prueba_completa` (las aisladas quedan en
  `sim/escenarios/pruebas_aisladas/`, solo para pytest).
- Soportes de servos (cuna con torres y tornillos), Hall a 4 mm del imán y poste de la cortina corregidos el 2026-09-26; revisar con el usuario.

## 5. Dónde está cada cosa (para no buscar)

- Reglas del proyecto y arquitectura: `CLAUDE.md` (este mismo directorio).
- Historial de decisiones: `docs/bitacora.md`. Paso a paso: `docs/paso-a-paso.yaml` (el `.md`
  se genera con `python -m app.documentos`).
- Lógica pura: `control/` (linea.py, embalaje.py, reglas.py, almacen.py, tiempos.py, vehiculo.py).
- Asistente: `app/asistente.py` (+ pestaña en `app/dashboard.py`, `/api/asistente` en `app/servidor.py`,
  pestaña y nube en `app/visor3d/visor.js`). Guía del parcial: `docs/enunciado/`.
- Simulación: `sim/planta.py` (todo el flujo tick a tick), `sim/mundo.py` (PyBullet y medidas),
  `sim/sensores_sim.py`, `control/hal/backend_sim.py`, `sim/geometria.py` (lo que ve el visor).
- Catálogos: `sim/catalogos.py` (13 sensores + lista de materiales).
- Configuración y valores provisionales: `config/parametros.yaml`.
- Visor 3D: `app/visor3d/visor.js`. Demo grabada: `python -m app.grabar_demo`.
- Capturas en tiempo real para revisar el 3D (no usar `--virtual-time-budget`, engaña):
  script `captura.mjs` con Chrome headless por CDP (ver bitácora 2026-09-25).
