# Maqueta impresa: reglas para Claude

Qué es, números, cómo se revisa y cómo se imprime: [README.md](README.md). Cómo se diseña cada `.scad` (marco,
remaches, sin soportes, primera capa, qué no hacer): [CONVENCIONES.md](CONVENCIONES.md). Reglas del proyecto:
[../CLAUDE.md](../CLAUDE.md).

## Carpetas y rutas

- `scad/`: fuentes, a mano, salvo `estructura_gen.scad`, que escribe `estructura.py` (se cambia `estructura.py` y se
  corre; el `.scad` no se edita).
- `informes/`: `material.md`, `auditoria.md`, `esfuerzos.md` y `estructura_resumen.md`, todos generados.
- `salida/`: `stl/`, `piezas.json`, `laminado.json` y `manual_maqueta.pdf`, generados. `primera_capa.json` sale ahí
  solo al correr `primera_capa.py` suelto y está en el `.gitignore`.
- `3mf/`: las tandas desde las que imprime el usuario (ver abajo). `img/`: `maqueta_iso.png`, y `img/manual/` sin
  versionar. `_cache/`: STL de `revisar.py` con su huella, el sello y `cp_datadir/` de Creality Print (sin versionar).
- Las rutas salen de `revisar.py` (`D_SCAD`, `D_SALIDA`, `D_INFORMES`, `CACHE`, `SCAD`): una herramienta nueva
  hace `import revisar as R` y usa esas, sin escribirlas a mano. Las excepciones que ya existen son estas:
  `estructura.py` repite `D_SCAD` y `D_INFORMES`, y `esfuerzos.py` repite `D_INFORMES` (no importan `revisar` al cargar), `exportar.py`
  define `D_3MF`, `manual_maqueta.py` usa `img/manual/` y `modelo_3d.py` escribe el GLB. Si se mueve una carpeta, se
  cambian todas.

## Orden de trabajo al cambiar una pieza

1. Editar en `scad/` solo el `.scad` del subsistema (CONVENCIONES, "Archivos"). Si cambia la estructura, correr
   `python estructura.py`.
2. `python revisar.py` hasta `TODO OK`. Con `--sin-render` usa los STL de `_cache/` y marca MAL los viejos. Con
   `--sub alm` revisa un solo subsistema y no sella. Solo una corrida completa con TODO OK escribe
   `_cache/revision_ok.huella`: el sha1 del nombre y el contenido de todos los `scad/*.scad`. Si después cambia un
   `.scad`, el sello deja de valer.
3. `python probar_revisor.py`, si se tocó `revisar.py`, `voladizos.py`, `primera_capa.py`, `auditar.py` o
   `estructura.py`. La última corrida (2026-10-24) dio 128 de 128. Usa OpenSCAD.
4. `python exportar.py` es el único que pide el sello (`R.revision_ok()`): sin él, sale con "NO SE EXPORTA". Antes de
   correrlo, leer la regla de `3mf/`.
5. `python laminar.py` lee `3mf/*.3mf` y escribe `salida/laminado.json`.
6. `python auditar.py`, `python esfuerzos.py` y `python modelo_3d.py` no piden el sello. Piden que los STL de
   `_cache/` estén vigentes (`R.viejos()`): si no lo están, salen sin escribir nada.
7. `python manual_maqueta.py` va al final. Además de `_cache/ens/` vigente, lee `salida/piezas.json` de `exportar.py` y,
   si está, `salida/laminado.json`.
8. Lo de afuera: si cambió `salida/piezas.json`, correr `entorno/Scripts/python.exe -m app.documentos`
   (`docs/costos.md` y `docs/peso.md`). Si cambió el GLB, correr `entorno/Scripts/python.exe -m app.portable`. Después,
   `entorno/Scripts/python.exe -m pytest tests/sim/test_maqueta_impresa.py tests/app/test_costos.py tests/app/test_masas.py`
   (desde `proyecto-final/`).

## Python y el carro

- `python` es el del sistema (3.14, con numpy, scipy, yaml, matplotlib y reportlab). El `entorno/` no tiene reportlab,
  así que `manual_maqueta.py` corre solo con el del sistema. No hace falta `PYTHONPATH`: `manual_maqueta.py` y
  `esfuerzos.py` ya ponen `proyecto-final/` en `sys.path` para `sim.conexiones` y `sim.electrica`.
- `revisar.py` importa `../chasis_impreso/exportar.py` como `ex_carro`. De ahí salen OpenSCAD, `leer_stl`,
  `escribir_stl`, `volumen_area`, `escribir_3mf`, `acomodar`, `CAMA`, `MARGEN` y los parámetros de masa y tiempo.
  `exportar.py` de aquí cambia `ex_carro.SEPARACION`. Esa API no se rompe allá. Aquí, `revisar` se importa antes que
  `exportar`, porque los dos módulos se llaman igual (`revisar.py:46-50`).

## Lo que no se hace sin que el usuario lo pida

- **Excepciones de soportes**: `voladizos.PUENTES_ACEPTADOS` tiene una sola, el puente de ~30 mm de `mon_e4` en z
  46,5-47,7, que aceptó el usuario y sale como aviso. No se agregan otras: se arregla la pieza.
- **Creality Print, solo por línea de comandos**, como hace `laminar.py`: `CrealityPrint.exe --cli --datadir
  _cache/cp_datadir ...`. Nunca abrir la interfaz ni correr `--help`: el 2026-10-25 la interfaz se sincronizó con la
  nube y borró los perfiles hechos a mano. `perfil_creality.json` es el perfil que `exportar.py` mete en cada 3MF, sin
  la MAC de la impresora.
- **`3mf/` es del usuario.** `alm_1.3mf`, `alm_2.3mf` y `alm_3.3mf` los guardó él con Creality Print (traen
  `Metadata/slice_info.config`) y están modificados sin commit. No se tocan, no se restauran (`git restore` ni
  `checkout`) y no entran en un commit: cuidado con `git add -A`.
- **`exportar.py` toca esos 3MF**: mueve todo 3MF guardado desde Creality Print a
  `3mf/guardados/<nombre>_<fecha>.3mf` y vuelve a escribir las tandas. Hoy sacaría los `alm_*` del usuario de `3mf/`.
- **`3mf/guardados/` nunca se sube**: trae la configuración y la MAC de la impresora, y está en el `.gitignore` de
  esta carpeta.
- **Nada se manda a imprimir.**
- **CPU**: máximo 2 OpenSCAD a la vez por agente. `REVISAR_HILOS` (6 por defecto) limita `revisar.py`,
  `exportar.py`, `auditar.py`, `modelo_3d.py` y `primera_capa.py`: con agentes, usar `REVISAR_HILOS=2`.
  `manual_maqueta.py` usa 4 hilos fijos y `laminar.py` lamina 2 tandas a la vez.

## Quién nos nombra desde afuera

Si se mueve o se renombra algo de aquí, se corrige allá. Para encontrar todas las menciones:
`git grep -n maqueta_impresa -- ':!proyecto-final/maqueta_impresa'`.

| Quién | Qué usa |
|---|---|
| `config/precios.yaml` (`estructura_3d.maqueta`) | `archivo: maqueta_impresa/salida/piezas.json` y los grupos por prefijo de tanda |
| `app/costos.py` y `app/masas.py` | `salida/piezas.json`, a través de precios.yaml (de ahí salen `docs/costos.md` y `docs/peso.md`) |
| `app/visor3d/maqueta_impresa.glb` | lo escribe `modelo_3d.py`; lo leen `visor.js` y `maqueta_impresa.js`, y `app/portable.py` lo mete en el portable |
| `tests/sim/test_maqueta_impresa.py` | carga `modelo_3d.py` por ruta (`leer_glb`, `vertices_mm`, `R.SCAD`), lista `scad/maqueta.scad` con OpenSCAD y compara el GLB con `_cache/ens/` |
| `tests/app/test_costos.py` y `tests/app/test_masas.py` | `salida/piezas.json` |
| `.gitattributes` de la raíz del repo | `scad/estructura_gen.scad` y `salida/piezas.json` como generados; STL, 3MF, PDF y GLB como binarios |
| comentarios en `sim/urdf/`, `sim/electrica.py`, `config/parametros.yaml`, `docs/paso-a-paso.yaml` y `app/visor3d/piezas/linea_vasos.js` | rutas de `scad/*.scad` e `informes/*.md` |
