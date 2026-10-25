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
- Si la pieza de adentro queda en una **cajera o en una U** (puede correrse dentro), el agarre lleva **+0,2 más**:
  al entrar, el remache la corre hasta el otro lado (los nodos: pared 2,4 + tubo 1,6 + 0,2 = 4,2 en el ensamble y
  agarre 4,4). `revisar.py` mide **cada pata** (±x local, donde engancha la uña) y acepta la cara de salida entre
  **agarre − 0,3 y agarre + 0,15**: el hombro de la uña está en agarre + 0,2, y si la cara sale más allá queda adentro.
- Agarre máximo 20 mm (el de 37 del carro se doblaba). Si hay más que juntar: cajera para la cabeza.
- Remachar a un **tubo** de la estructura con las patas (el largo de la cabeza) cruzando su cara: el remache va a
  **≤ 0,75 mm del eje de esa cara**. El hueco del tubo es octogonal, con chaflanes de 45°: más afuera una pata cae
  sobre el chaflán, sale 1-2 mm más allá y la uña no traba (pasó con los colgantes de tapas y el sensor).
- **≥ 10 mm entre ejes** de dos remaches de la misma pieza, y que las cabezas (8 × 3,2 × 1,6) no se pisen:
  `revisar.py` marca dos remaches que se cruzan.
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
  ni con el barrido de otra parte móvil. Si toca a propósito su eje o lo que se mueve con ella, se le resta eso,
  **en su posición de reposo** (como está en `<sub>_comprados`), no a lo largo de todo el recorrido.
- Lo que se mueve no puede ni rozar: **> 0,05 mm³ ya es choque** (entre piezas fijas, > 1 mm³).
- El barrido tiene que **contener** lo que lleva en todo el recorrido, **extremos incluidos** y entre copia y copia
  (si se hace con copias sueltas queda aire entre ellas: mejor `hull()` de copias seguidas, parte por parte).
  revisar.py lo pone en los extremos y en 7 posiciones intermedias con `RECORRIDOS` (en revisar.py: una parte móvil
  nueva se pide en el informe) y no acepta más de 0,05 mm³ afuera de más de 0,6 mm de espesor.
- `SINCRONOS_<SUB> = [[nombre, pasos], ...]` y `module <sub>_fase(n, k, lado)`: lo que se mueve junto pero distinto
  (leva y seguidor, manivela y carro, escape y vasos), paso por paso. Cada lado se mide aparte: **un lado vacío es
  MAL** (nombre mal escrito o un `<sub>_fase` que no lo dibuja), igual que un OpenSCAD que falla. Lo que tiene que
  **tocarse** (la leva con el rodillo, el vaso retenido con el dedo del escape) se declara en `CONTACTOS` de
  revisar.py: corrido 0,6 mm hacia el otro lado se tiene que meter. Dibujarlo donde está de verdad (a lo sumo 0,3 de
  luz): el visor y la simulación tienen que ser lo físico.
- `AGUJEROS_<SUB> = [[p0, p1, diámetro], ...]`: agujeros que hacen falta en piezas de otro (un eje que pasa
  por un riel). maqueta.scad los resta en todas las piezas.
- `MOVILES_*`, `SINCRONOS_*` y `AGUJEROS_*`, LITERALES (solo números y strings): `moviles_por_defecto.scad` las
  define vacías antes y OpenSCAD evalúa la reasignación en el lugar de la primera; si usan variables definidas más
  abajo salen undef (revisar.py marca un `REM`, un `MOVIL` o un `SINCRONO` mal formado; un `AGUJERO` no).

## Imprimible sin soportes

- Cada pieza en su orientación de impresión: nada a más de 50° de la vertical en el aire (salvo zonas de
  menos de 5 mm), puentes ≤ 12 mm. Agujeros horizontales: ≤ Ø12 o con techo en gota/alero.
- **Ninguna parte nace en el aire ni cuelga de una sola punta** (agregado el 2026-10-25, segunda opinión: mon_e4,
  tap_pre_placa y vas_lat_s_b tenían pedazos que empezaban sobre nada, y vas_lat_s_a postes en V de 33 mm colgados de la
  pared; todas sus caras estaban a 40-45°, así que el ángulo no los marcaba, pero el laminador imprimía filamento al aire).
  En la orientación de impresión cada capa se apoya en la de abajo: nada empieza sin material debajo (la arista de abajo
  de una V, el canto de una placa inclinada, una columna entre dos ventanas), y lo nuevo de una capa no queda a más de
  5 mm de la capa de abajo, salvo un puente de ≤ 12 mm apoyado en las dos puntas (una cumbrera en V tendida entre dos
  paredes también es un puente). Si la arista de abajo flota: un nervio vertical de ≥ 1,6 mm hasta lo de abajo, una cara a
  ≤ 45° que suba desde la pieza, o llevar el corte hasta que el pedazo desaparezca. `voladizos.py` corta cada pieza cada
  0,2 mm y lo marca MAL (en revisar.py y en auditar.py); para mirarlo a mano, cortar el STL de `_cache/cama`.
  Única excepción, aceptada por el usuario el 2026-10-25 (`voladizos.PUENTES_ACEPTADOS`): en mon_e4, boca abajo, la
  cumbrera entre los pisos de los canales A y B arranca como un puente de 30 mm apoyado en las dos paredes; acortarlo
  metía material en el canal de 30 de la moneda de 26,7 o bajo la aleta. Sale como aviso: esa primera línea puede
  quedar algo caída.
- Cabe en la cama: 240 × 240 × 290 mm. Si no cabe, partirla con cola de milano o remaches.
- Paredes ≥ 1,6 mm (4 perímetros de 0,4). Excepción aceptada (2026-10-24, para ahorrar PLA): 1,2 mm (3 perímetros)
  en lo que solo contiene y no carga ni une (los tubos del tambor de monedas). Lo que gira o roza (ejes, pivotes):
  agujero = eje + 2·tol.

## Comprobar (obligatorio antes de entregar)

```
cd maqueta_impresa
REVISAR_HILOS=3 python revisar.py --sub alm        # tiene que terminar en "TODO OK"
```

Revisa los remaches del subsistema (agarre medido por pata, hueco para la uña, cabeza, que se pueda meter, remache
contra remache), los choques de sus piezas contra TODO (estructura, otros subsistemas, lo comprado), lo que se mueve
(barridos, recorrido completo, fases y contactos), sin soportes, que quepan y la primera capa. Al final, una corrida
completa (`python revisar.py`, sin `--sub`) con TODO OK: sin eso `exportar.py` no exporta.
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

## Primera capa (agregado el 2026-10-24: se levantaba y se despegaba en los círculos chicos)

Con PLA húmedo, cada agujero chico en la cara que apoya en la cama es un bucle corto que al cerrarse (retracción y
limpieza) arranca el material, y cada isla suelta es un viaje más; de ahí para arriba todo se daña. La membrana de
primera capa NO es opción (obliga a recortar). Regla:
- La cara que apoya en la cama queda **maciza**: sin vaciados, rejillas, cerchas, canales ni ventanas que abran
  hacia la cama (se hacen desde arriba o por los costados, cerrados por abajo con 1,2-1,6 mm de piel).
- Los agujeros de remache, perno o eje van, siempre que se pueda, en una cara **lateral** (reorientando la pieza);
  si son inevitables en la cara de apoyo, que sean pocos. Los tubos de la estructura se giran solos sobre su eje
  para dejar su cara con agujeros a un costado (hueco octogonal).
- Una **ranura de aire o una tira de material de menos de 1,2 mm** en la cara de apoyo es tan mala como un agujero
  chico (sus puntas son igual de cerradas), y una ranura cerrada se mide por 4 A / P (una de 4,4 × 16 es un agujero
  de 7,2).
- Se mide con `python primera_capa.py stl/<pieza>.stl` (o un STL en orientación de cama): "islas" tiene que ser 1, y
  "chicos" (agujeros < 8 mm) más "angostas" (ranuras y tiras < 1,2 mm), 0 o casi: revisar.py acepta hasta 2 entre
  los dos.
- **La base**: una pieza de pie se tambalea con la boquilla y se despega. Esbeltez = alto / (base mínima de la
  primera capa + 2 × brim) **≤ 6**, el centro de masa sobre la base, y **despegue ≤ 0,1 MPa** (0,2 N de la boquilla en
  la punta + la inercia de la cama, sobre el módulo resistente de la primera capa); si pasa, **brim propio**
  (`primera_capa.BRIM_OBJETO`, pegado a la pieza) o acostarla.
- **Nada que perforar ni recortar después de imprimir**: ni membrana, ni **capa inicial de sacrificio** (ni balsa),
  ni "tapas" de 0,4 mm sobre agujeros, ni puentes de sacrificio. Un agujero de tornillo que no necesita atravesar se
  hace **ciego desde la cara que queda arriba** al imprimir (y se orienta la pieza para eso).
