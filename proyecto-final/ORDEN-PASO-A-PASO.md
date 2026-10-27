# Orden del proyecto — paso a paso (TEMPORAL: se borra al terminar)

Pedido del usuario (2026-10-26), textual en CONTEXTO-SESION.md §0. Este archivo existe para retomar si la sesión se
corta: cada tanda se marca [x] al terminar y verificar. El mapa completo de dependencias (7 agentes, solo lectura) está en
`C:\Users\danie\AppData\Local\Temp\claude\D--cosas-uni\9408d2be-81d2-407f-8fc9-d0e529da2642\scratchpad\mapa\` (mapa.json,
propuestas.md, fragiles.md, faltantes.md); si se perdió, se rehace con el workflow `mapa-rutas-proyecto-final`.

Estado: **APROBADO (2026-10-26)**. Decisiones del usuario: código "Todo, incluso asistente.py"; .md "README + CLAUDE.md con
reglas"; archivos sin uso "Borrarlos"; "Commit local por tanda" (sin push hasta que lo pida). Orden: A (yo) → B y C en
paralelo (un agente cada uno, sin tocar archivos comunes) → D (agentes en cadena) → E → F. Los archivos comunes (README.md,
CLAUDE.md, docs/, .gitattributes del repo) solo los toca la sesión principal o el agente de la tanda E.

## Lo que NO se mueve ni se renombra (lo nombran contratos de afuera)

- `proyecto-final/` y su `README.md` (el Word entregado a la universidad enlaza `.../blob/main/proyecto-final/README.md`).
- `ABRIR.bat`, `abrir.sh`, `probar.json`, `pytest.ini`, `.streamlit/`, `visor-portable.html`, `CLAUDE.md`, `CONTEXTO-SESION.md`
  (lanzador común del repo, .gitattributes, reglas y CLAUDE.md de afuera).
- Paquetes y carpetas: `app/`, `app/visor3d/` (y `piezas/`, `vendor/`, `demo/`), `app/dashboard/`, `app-practica/`, `firmware/`
  (`fijo/`, `carro/`, `comun/`, `preparar.py`, `subir.py`), `wokwi/`, `sim/ver/`, `sim/conexiones.py` (8 scripts de Modelado 3D),
  `docs/` sin subcarpetas nuevas (enlaces con ancla, corpus del asistente, generadores).
- `control/protocolo.py` y `control/vehiculo.py`: van tal cual a la placa con ese nombre.
- `maqueta_impresa/3mf/`: el usuario imprime desde ahí (alm_1, alm_2 y alm_3 guardados por Creality Print el 25 y 26/10,
  sin commit: NO se tocan ni se restauran).
- `chasis_impreso/`: el carro ya está impreso y armado; no se regenera nada ni cambia la geometría.
- `visor.js` no se parte (las pruebas lo leen con regex).

## Tandas (cada una: cambiar → verificar → marcar [x] → commit local si el usuario lo aprueba)

### A. Limpieza sin riesgo — HECHA (commit local 04130e1, 950 pruebas)
- [x] Borrar lo que nadie usa (grep sin resultados): `sim/urdf/.gitkeep`, `maqueta_impresa/img/maqueta_atras.png`,
  `chasis_impreso/img/ensamble_iso_der.png`, `chasis_impreso/img/corte/` (17 PNG que guia_corte.py escribe y nadie lee; quitar ese
  bucle), `maqueta_impresa/primera_capa.json` (viejo, 19 de 183 piezas; a .gitignore), `requirements.txt` (nadie lo instala),
  `app/visor3d/piezas/muestrario.html` (página de desarrollo sin enlaces).
- [x] Constantes muertas: sim/planta.py RECHAZO_FINAL, NOMBRES_/ETIQUETAS_ESTACIONES_*; sim/catalogos.py PENDIENTE_CONEXION;
  control/carrusel.py LUGARES.
- [x] .gitignore sin líneas repetidas (proyecto, chasis, maqueta); `.gitattributes`: `*.bat text eol=crlf` (hoy solo ABRIR.bat:
  visor.bat e instalar.bat llegan con LF en un ZIP de GitHub) y `git add --renormalize`.
- Verificar: `git status --short --ignored` igual antes y después; pytest completo.

### B. maqueta_impresa/ — HECHA (scad/, informes/, salida/; huella igual, revisar TODO OK)
- [x] Primero, sin mover nada: todas las rutas en un solo lugar en revisar.py (D_SCAD, D_SALIDA, D_INFORMES) y que las demás
  herramientas las usen; assert en huella() de que encontró los .scad.
- [x] `scad/`: las 10 fuentes OpenSCAD (incluido estructura_gen.scad). La huella hashea nombre + contenido: _cache y el sello
  siguen vigentes.
- [x] `informes/`: material.md, auditoria.md, esfuerzos.md, estructura_resumen.md (generados).
- [x] `salida/`: stl/, piezas.json, laminado.json, manual_maqueta.pdf (generados). `3mf/` e `img/` se quedan donde están.
- [x] Las 11 herramientas .py, README.md, CONVENCIONES.md, inventario_maqueta.md y perfil_creality.json quedan en la raíz.
- Verificar: `python revisar.py --sin-render` (TODO OK y sello), `python probar_revisor.py`, pytest de la maqueta y de costos,
  `python -m app.documentos` + `git diff --stat docs` (sin cambios), enlaces de los .md.

### C. chasis_impreso/ — HECHA (salida/, GLB único, textos)
- [x] `salida/` con git mv: stl_*/, 3mf_*/, piezas.json, lista_materiales.md, manual_armado.pdf, visor_carro.html; borrar la copia
  chasis_impreso/carro_armado.glb (el visor usa la de app/visor3d/) y su comparación en la prueba.
- [x] Textos viejos: "Nada de esto está impreso todavía", exportar.py:8, manual.py:10, revisar_remaches.py en el README.
- Verificar: pytest tests/sim/test_carro_impreso.py y de la maqueta (usa chasis_impreso/exportar.py como biblioteca).

### D. Código (mismo comportamiento; pytest completo después de cada punto)
- [ ] `app/rutas.py` con RAIZ, DOCS, CONFIG, DATOS, VISOR: reemplaza los 13 `Path(__file__).parent.parent` de app/.
- [ ] Un solo lector de config fuera de app/ (`control/configuracion.py`; app/configuracion.py lo reexporta): corta sim → app.
- [ ] `control/hal/backend_sim.py` → `sim/backend_sim.py` (es la HAL sobre PyBullet: control/ queda sin PyBullet, como pide la regla 17).
- [ ] Duplicados: una sola fábrica de planta simulada (supervisor, grabar_demo, sim/ver/planta_vista), un solo guion de sabotajes,
  `db.copiar_base` (charla y evaluar_asistente), firmware/preparar.py con un solo sys.path, vision/ con AQUI propia,
  exportar.py lee el precio del PLA de config/precios.yaml.
- [ ] `sim/electrica.py`: el informe (§8, 460 líneas) a `sim/electrica_informe.py`.
- [ ] `app/asistente.py` (1638 líneas) a un paquete `app/asistente/` por secciones (aprobado).
- [ ] `tests/visor/test_portable.py` escribe el portable en una carpeta temporal (hoy reescribe el archivo versionado de 9,4 MB).
- Verificar: pytest completo; `python -m app.grabar_demo` solo si cambia la demo; `python -m app.portable`; captura del visor.

### E. Documentos para personas y para Claude
- [ ] Un README.md por carpeta donde falta: app/, app/dashboard/, app/visor3d/ (y corregir piezas/README.md), app-practica/,
  sim/, control/, config/, tests/; chasis_impreso/ con una sección "archivos y qué genera qué".
- [ ] CLAUDE.md solo donde hay reglas para el agente: el general (tabla "Dónde leer" con TODAS las carpetas, lo que no se mueve,
  quién nos nombra desde afuera, checklist de verificación), `maqueta_impresa/CLAUDE.md` (orden de trabajo, sello, Creality solo
  con --cli, 3mf/guardados) y `chasis_impreso/CLAUDE.md` (ya impreso: no regenerar).
- [ ] CONTEXTO-SESION.md corto: los pedidos cerrados pasan a docs/historial-pedidos.md.
- [ ] Árboles de carpetas al día: README.md (tabla "Qué hace cada archivo"), docs/especificacion.md §árbol, docs/README.md.
- [ ] Cifras viejas: 937 pruebas → las de hoy; portable 2,5 MB → 9,4 MB (probar.json, README, app-practica, .gitattributes).
- [ ] Enlace roto de la app de la práctica: "Enunciado (PDF)" da 403 (el lanzador bloquea "umng.pdf").

### F. Verificación final y cierre
- [ ] pytest completo; `revisar.py --sin-render` TODO OK; `python _lanzador/revisar_enlaces.py proyecto-final`;
  `python _lanzador/lanzador.py --comprobar`; `python -m app.documentos` sin cambios; portable regenerado; captura del visor;
  grep de cada nombre viejo (sin contar bitacora.md ni historial-pedidos.md).
- [ ] Marcar el punto en CONTEXTO-SESION.md y BORRAR este archivo.
