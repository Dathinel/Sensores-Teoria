# Carro impreso: reglas para Claude

Qué es, piezas, tandas, uniones y armado: [README.md](README.md). Reglas del proyecto: [../CLAUDE.md](../CLAUDE.md).

## El carro ya existe

- El carro **ya está impreso y armado** (2026-10-24) con lo que hay en `salida/`. Sin un pedido explícito del usuario
  no se regenera nada (STL, 3MF, `piezas.json`, lista de materiales, manual ni GLB) y no se cambia la geometría
  (`chasis.scad`, `manual.scad`, `primera_capa.scad`): un cambio aquí deja de describir el carro que existe.
- Casi todos los scripts escriben algo. `exportar.py` vuelve a escribir todo `salida/stl_*` y `salida/3mf_*`, además
  de `piezas.json`, y `modelo_3d.py` vuelve a escribir `app/visor3d/carro_armado.glb`. Solo `revisar_voladizos.py` y
  `revisar_remaches.py` revisan sin escribir nada: `revisar_remaches.py` corre OpenSCAD en una carpeta temporal.
- Qué script genera qué, en qué orden y qué usa de fuera de la carpeta: README,
  ["Archivos y qué genera qué"](README.md#archivos-y-qué-genera-qué). No se repite aquí.

## Lo que hay en `salida/` (generado, no se edita a mano)

- `stl_con_membrana/` y `stl_sin_membrana/`: 28 STL cada una. `stl_sin_membrana/_ensamble/` tiene las piezas en su
  lugar para los choques y `diagramas.py`, y está en el `.gitignore`.
- `3mf_con_membrana/` y `3mf_sin_membrana/`: 6 tandas cada una, de `tanda0_prueba` a `tanda5_remaches_pasadores`.
- `piezas.json`, `lista_materiales.md`, `manual_armado.pdf` y `visor_carro.html`.

## Contratos con el resto del proyecto

- `exportar.py` también es una biblioteca. `maqueta_impresa/revisar.py` lo importa como `ex_carro`, y por él lo usan
  `exportar`, `auditar`, `laminar`, `modelo_3d`, `manual_maqueta` y `probar_revisor` de la maqueta. Estos nombres no
  se cambian: `OPENSCAD`, `CAMA`, `MARGEN`, `SEPARACION` (la maqueta lo reasigna), `PLA_G_CM3`, `CAUDAL_MM3_S`,
  `S_POR_CAPA`, `leer_stl`, `escribir_stl`, `volumen_area`, `acomodar` y `escribir_3mf`. Al importarlo no tiene que
  hacer nada: todo lo que escribe va bajo `if __name__ == "__main__"`.
- `carro_armado.glb` vive solo en `app/visor3d/`. La copia que había aquí se borró en la tanda C: no crear otra.
- `python` es el del sistema (3.14, con numpy, yaml, matplotlib y reportlab). El `entorno/` no tiene reportlab, así
  que `manual.py` no corre con él. OpenSCAD está en `exportar.OPENSCAD`.
- **CPU**: el máximo es 2 OpenSCAD a la vez por agente, y los scripts de aquí usan más hilos fijos (`exportar.py`
  hasta 8; `revisar_remaches.py` y `modelo_3d.py` 6; `manual.py` 4). Si el usuario pide correrlos, que no haya otro
  OpenSCAD corriendo al mismo tiempo.

## Quién nos nombra desde afuera

Si se mueve o se renombra algo de aquí, se corrige allá. Para encontrar todas las menciones:
`git grep -n chasis_impreso -- ':!proyecto-final/chasis_impreso'`.

| Quién | Qué usa |
|---|---|
| `maqueta_impresa/revisar.py` y todo lo que lo importa | `exportar.py` como biblioteca (`ex_carro`) |
| `maqueta_impresa/exportar.py` | los parámetros de masa y tiempo de `exportar.py` |
| `app/visor3d/visor.js` (`cargarGLB('carro_armado.glb')`) y `app/portable.py` (lo mete en el portable como `__CARRO`) | `app/visor3d/carro_armado.glb`, que escribe `modelo_3d.py` |
| `tests/sim/test_carro_impreso.py` | el GLB y `manual.scad` (`REM_LISTA`): compara las cotas funcionales con el visor y la simulación |
| `.gitattributes` de la raíz del repo | `salida/piezas.json` como generado; STL, 3MF, PDF y GLB como binarios |
| `README.md` del proyecto, `app/visor3d/README.md` y el `README.md` de la raíz del repo | enlaces y rutas de esta carpeta |
