# Maqueta impresa: convenciones para cada subsistema

Pedido del usuario (2026-10-24): toda la maqueta en PLA, sin aluminio ni acrílico; la forma de los
soportes puede cambiar, pero **lo funcional no se mueve** (posiciones de estaciones, alturas de bandas,
carrusel, tolva, canaleta, sensores y cámaras: de eso dependen la simulación, el firmware y el visor).
"Revise todo múltiples veces para no cometer el mismo error": en el carro, los remaches del porta baterías
no pasaban y 2 de los rodillos no agarraban nada porque su agarre se sacó de fórmulas. Aquí cada unión se
**mide** en el ensamble con `revisar.py` antes de darla por buena.

## Archivos

- `comun.scad`: marco, tolerancias, `remache(agarre)`, `en_marco(p0, p1, arriba)`, tubo y cajeras. **No se edita.**
- `estructura.py` → `estructura_gen.scad` + `estructura_resumen.md`: tubos 16×16, nodos, empalmes y tacos.
  **No se edita** (si un subsistema necesita un tubo o un nodo nuevo, se pide en el informe).
- `maqueta.scad`: junta todo. **No se edita.**
- Un `.scad` por subsistema; cada agente edita **solo el suyo**:
  `almacen.scad` (prefijo `alm_`), `cinta_monedas.scad` (`mon_`), `cinta_vasos.scad` (`vas_`),
  `tapas_prensa_empujador.scad` (`tap_`), `canaleta_muelle.scad` (`can_`).
- `inventario_maqueta.md`: TODAS las medidas actuales de la maqueta (de `sim/mundo.py`, `sim/geometria.py`,
  `config/parametros.yaml` y el visor), con archivo:línea, más las relaciones que no se pueden romper (§18)
  y las discrepancias entre fuentes (§19). Ahí están las posiciones funcionales que hay que respetar.

## Marco y unidades

El mismo de `sim/mundo.py` pero en **milímetros**: x a lo largo de las cintas, y a lo ancho (−y = lado del
operador: canaleta y carro; +y = pórtico y caja de control), z arriba, **z = 0 el piso**. Cada pieza se
modela EN SU LUGAR del ensamble.

## Lo que define cada subsistema (en su .scad, que NO hace `include` de nada: maqueta.scad ya trae todo)

```
PIEZAS_ALM = ["alm_placa_fija", "alm_tubo_1", ...];     // nombres únicos con el prefijo
REM_ALM = [ ["r_alm_placa_1", agarre, [x,y,z cabeza], [eje]], ... ];   // nombre con r_<prefijo>_
module alm_pieza(n) { ... }       // UNA pieza en su lugar (sin agujeros de remache: maqueta.scad los resta)
module alm_a_cama(n) children();  // giro para imprimirla: lo que quede abajo apoya en la cama
module alm_comprados() { ... }    // lo comprado (motor, servo, eje, rodamiento, banda...) en su lugar,
                                  // con su forma aproximada: entra en la revisión de choques
```

Pueden usar las listas y módulos de `estructura_gen.scad` (NODOS, TUBOS, TACOS, `lado_tubo`…) para
ubicarse, y `remache(agarre)`, `en_marco`, `tol`, `rem_agujero`, `rem_cabeza`, `rem_plano` de `comun.scad`.

## Remaches (la regla que falló en el carro)

- Remache: `[nombre, agarre, cabeza, eje]`. `cabeza` = punto donde apoya la cabeza (sobre la cara de la
  pieza de afuera), `eje` = unitario hacia donde entra. `agarre` = **suma exacta** de lo que atraviesa
  (espesores + 0,2 por cada holgura de encaje). Tiene que salir a **aire o al hueco de un tubo** con ≥ 3 mm
  libres (si no, la uña no abre: agujero ciego), y detrás de la cabeza tiene que haber espacio libre del largo
  del remache + 15 mm (para meterlo con el dedo; ni contra el piso ni desde adentro de un tubo).
- Agarre máximo 20 mm (el de 37 del carro se doblaba). Si hay más que juntar: cajera para la cabeza.
- Los agujeros de los remaches los resta `maqueta.scad` en TODAS las piezas por donde pasan: no hace falta
  hacer agujeros a mano (y no hay que hacerlos, para que no queden corridos).
- Remachar a un tubo de la estructura: atraviesa la pieza y una pared del tubo (1,6): agarre = e + 1,6.
  Lejos (≥ 5 mm) de las bocas de los nodos, de los empalmes y de los remaches de la estructura
  (`estructura_resumen.md`, `REM_ESTRUCTURA`). Mínimo 2 remaches por pieza que carga algo.
- Remache vs. encaje: también valen pernos a presión, colas de milano y clips impresos, siempre que
  `revisar.py` los pueda comprobar (si son encajes, que no choquen y que la holgura sea `tol`).

## Lo que se mueve y los agujeros en piezas ajenas (agregado el 2026-10-24)

- `MOVILES_<SUB> = [[nombre, [piezas que se mueven con ella]], ...]` y `module <sub>_barrido(n)`: cada parte
  móvil dibujada en TODO su recorrido. revisar.py comprueba que no choque con nada fijo, ni con lo comprado,
  ni con el barrido de otra parte móvil. Si toca a propósito su eje o lo que se mueve con ella, se le resta eso.
- `AGUJEROS_<SUB> = [[p0, p1, diámetro], ...]`: agujeros que hacen falta en piezas de otro (un eje que pasa
  por un riel). maqueta.scad los resta en todas las piezas.
- Las dos listas, LITERALES (solo números y strings): `moviles_por_defecto.scad` las define vacías antes y
  OpenSCAD evalúa la reasignación en el lugar de la primera; si usan variables definidas más abajo salen undef.

## Imprimible sin soportes

- Cada pieza en su orientación de impresión: nada a más de 50° de la vertical en el aire (salvo zonas de
  menos de 5 mm), puentes ≤ 12 mm. Agujeros horizontales: ≤ Ø12 o con techo en gota/alero.
- Cabe en la cama: 240 × 240 × 290 mm. Si no cabe, partirla con cola de milano o remaches.
- Paredes ≥ 1,6 mm (4 perímetros de 0,4). Excepción aceptada (2026-10-24, para ahorrar PLA): 1,2 mm (3 perímetros)
  en lo que solo contiene y no carga ni une (los tubos del tambor de monedas). Lo que gira o roza (ejes, pivotes):
  agujero = eje + 2·tol.

## Comprobar (obligatorio antes de entregar)

```
cd maqueta_impresa
python revisar.py --sub alm        # tiene que terminar en "TODO OK"
```

Revisa los remaches del subsistema (agarre medido, hueco para la uña, cabeza, que se pueda meter), los
choques de sus piezas contra TODO (estructura, otros subsistemas, lo comprado), sin soportes y que quepan.
Renderizar también una vista para mirar (`openscad.com -D 'modo="ensamble"' -o vista.png --camera=...`).

OpenSCAD: `D:\cosas uni\Micros\instalados\openscad\openscad.com` (2026, backend Manifold).
Python: el del sistema (`python`), con numpy.

## Qué NO hacer

- No editar archivos de otros subsistemas, ni `comun.scad`, `estructura*`, `maqueta.scad`, `revisar.py`.
- No tocar nada fuera de `maqueta_impresa/` (ni `sim/`, ni el visor, ni `config/`): el visor y la simulación
  se ajustan al final, con lo que entreguen.
- No git, no commits.
- No inventar medidas de lo comprado: si un dato no está en `inventario_maqueta.md` ni en `config/`, poner
  una variable `// MEDIR:` con un valor razonable y decirlo en el informe.
