# Maqueta impresa

Toda la maqueta de la planta (mesas, pórtico, soportes, almacén de monedas, mecanismos y canaleta) en PLA, para la
Creality Hi. Reemplaza los 6,1 m de perfil de aluminio 2020, las 24 escuadras, los 15 pies niveladores, las placas
de aluminio y las piezas de acrílico (los tubos y discos del almacén y el tubo de tapas también son impresos).
Lo comprado sigue siendo comprado: motores, servos, sensores, cámaras, bandas, rodillos, ejes y rodamientos.

![Maqueta impresa armada](img/maqueta_iso.png)

## Números

| | |
|---|---|
| Piezas impresas | 183 (más 382 remaches de 24 medidas: 316 que van y 10 % de repuesto) |
| PLA | **2,98 kg** estimados (Creality Print da **2,95 kg** al laminar las 26 tandas): 4 rollos de 1 kg con el 10 % de desperdicio (≈ $308.000 de filamento). Aligerada donde no carga; los refuerzos de la auditoría del 2026-10-25 (puntal de la viga, bajadas del rodillo A, labios, costillas de la prensa, tambor de una isla) suman lo que hacía falta para que todo cumpla |
| Tiempo de impresora | **≈ 101 h** según Creality Print (laminado.json), en 26 tandas de una cama cada una |
| Uniones | 316 remaches impresos, cada uno con su agarre **medido en el ensamble, pata por pata** |

El detalle por pieza y por tanda está en [material.md](material.md); el armado, paso a paso, en
[manual_maqueta.pdf](manual_maqueta.pdf).

## Cómo está hecha

- **Estructura** (`estructura.py` → `estructura_gen.scad`): tubos de 16 × 16 impresos acostados (hueco con
  chaflanes de 45°: sale sin soportes), nodos con cajeras donde entra el tubo entero 22 mm, empalmes para los tramos
  de más de 240 mm y tacos entre la mesa de monedas y la viga. Un piso de tubos amarra todo en una sola pieza. Nada
  pasa bajo la banda de vasos (la vuelta de abajo con sus separadores baja a z 81).
- **Subsistemas**, un archivo cada uno: `almacen.scad`, `cinta_monedas.scad`, `cinta_vasos.scad`,
  `tapas_prensa_empujador.scad`, `canaleta_muelle.scad`. Las reglas comunes están en [CONVENCIONES.md](CONVENCIONES.md).
- `maqueta.scad` junta todo, en el mismo marco de `sim/mundo.py` pero en mm.

## Cómo se revisó (la lección del carro)

En el carro, el remache del porta baterías no pasaba y dos de los rodillos no agarraban nada: su agarre se había
sacado de fórmulas. Aquí `revisar.py` **mide** todo en el ensamble, sobre STL dibujados con los `.scad` de ahora (cada
STL de `_cache/` lleva la huella de los `.scad` con que se dibujó; lo que falta o está viejo se vuelve a dibujar):

- **cada remache**, con rayos por su eje y **por cada pata** (donde engancha la uña): la cara de salida tiene que
  quedar entre el agarre − 0,3 y el agarre + 0,15 mm (el hombro de la uña está en agarre + 0,2: si la cara sale más
  allá, el hombro queda adentro y no traba); material alrededor del agujero en los 8 rayos (no al canto); detrás de
  cada pata ≥ 3 mm libres para que abra la uña; agujero libre; la cabeza (el estadio de 8 × 3,2 entero) apoyada y sin
  nada encima, con espacio detrás para meterla con el dedo; agarre ≤ 20 mm;
- **remache contra remache**: dos remaches no se pueden cruzar ni pisarse las cabezas;
- **choques** entre todas las piezas (> 1 mm³) y con lo comprado, un STL por subsistema cruzados entre sí (lo
  comprado de un mismo subsistema no se cruza consigo mismo: un eje dentro de su rodillo es a propósito);
- **lo que se mueve** (carrusel, obturador y su palanca, aleta E4, bandas con sus separadores y tacos, dedos, leva y
  pistón de la prensa, empujador, escape y vaso de la canaleta) barrido en todo su recorrido contra todo lo fijo,
  contra los otros barridos y contra los remaches; aquí 0,05 mm³ ya es un roce. Y lo que lleva cada barrido tiene que
  quedar **dentro** de él en todo el recorrido, extremos incluidos (si no, lo que choca ahí no se ve);
- los **mecanismos fase por fase** (cierre del almacén, empujador, prensa, escape de tapas, descarga del vaso, escape
  de la canaleta): que no se metan, con cada lado medido aparte (un lado vacío o un nombre mal escrito es MAL, no
  "0 mm³"), y que **se toquen** los que tienen que tocarse (la leva con el rodillo, los dedos del escape con el vaso);
- **sin soportes** (`voladizos.py`): nada a más de 50° en el aire, puentes ≤ 12 mm, agujeros horizontales ≤ Ø12 o con
  gota, y **capa por capa** (un corte cada 0,2 mm) que nada nazca en el aire ni empiece a más de 5 mm de la capa de
  abajo salvo un puente ≤ 12 mm apoyado en las dos puntas (única excepción aceptada: el puente de 30 mm de la cumbrera
  de mon_e4, que sale como aviso); y que quepa en la cama (240 × 240 × 290);
- la **primera capa** (`primera_capa.py`): una sola isla y como mucho 2 entre agujeros chicos (< 8 mm, por área o por
  4 A / P) y ranuras o tiras de material de menos de 1,2 mm; y la **base**: esbeltez (alto / (base mínima + 2 × brim))
  ≤ 6, el centro de masa sobre la base y despegue (0,2 N de la boquilla en la punta + la inercia de la cama, sobre el
  módulo resistente de la primera capa) ≤ 0,1 MPa, o brim propio.

Un OpenSCAD que falla es MAL, nunca "sin choque". Solo una corrida completa (sin `--sub`) que da TODO OK deja el sello
`_cache/revision_ok.huella`: `exportar.py` no exporta sin él (ni si un `.scad` cambió después), y `auditar.py`,
`modelo_3d.py` y `manual_maqueta.py` no corren con STL viejos. `probar_revisor.py` le mete errores a propósito (y
casos buenos) a cada una de estas revisiones para comprobar que los atrapa y que no grita por todo.

## Cómo imprimir (Creality Print)

Cada `3mf/<tanda>.3mf` es un proyecto de Creality Print 7.3 con **la configuración adentro**: proceso
**"0.20mm Standard @dathi 0.4 maqueta"** y filamento **"Hyper PLA @dathi 0.4 humedo maqueta"** en los 3 huecos, con la
capa, las paredes y el relleno de su grupo. Abrirlo **como proyecto, con su configuración** (no "solo geometría"),
revisar que todas las piezas estén en el filamento 1 y no aceptar "sincronizar filamentos del CFS" si cambia el perfil.
Lo que tienen esos perfiles contra la primera capa que se levantaba: sin limpieza en los bucles ni antes del perímetro
exterior, el filamento sin limpieza al retraer ni "retraer antes de limpiar" (era lo que recogía el hilo antes de
cerrar cada círculo), z hop normal, costura al punto más cercano y la primera capa de 0,3 mm a 30 mm/s.

- **Secar el PLA**: seca cada rollo antes de usarlo (45-50 °C, 4-6 h), sobre todo antes de `rem_1` y `rem_2` (las
  uñas de los remaches son lo más frágil que se imprime); entre tandas, guárdalo cerrado con desecante. El PLA húmedo
  fue parte de lo que levantaba la primera capa.
- **Prueba antes de las tandas grandes**: abrir `3mf/rem_1.3mf` como proyecto, borrar todo menos ~10 `rem_4_4` y
  laminar (así salen con su perfil; un STL suelto entra con el perfil activo); lo mismo con `3mf/can_1.3mf` dejando
  un prisionero y su cabezal para probar la rosca impresa.
- **Brim**: 5 mm a todas las piezas; las paredes altas que van de pie llevan **brim propio**, más ancho y pegado a la
  pieza, escrito por pieza en el 3MF (`primera_capa.BRIM_OBJETO`). Los **remaches van sin brim** y sin compensación de
  pata de elefante (con ella sus patas de 0,77 se pierden).
- **Nada de membrana, capa inicial de sacrificio ni balsa**, ni nada que perforar o recortar después de imprimir: la
  cara que apoya queda maciza por diseño y los agujeros van a los costados
  ([CONVENCIONES.md](CONVENCIONES.md), "Primera capa"); `revisar.py` lo comprueba.
- `laminar.py` lamina cada tanda con el CLI de Creality Print (con una carpeta de datos propia: nunca abrir
  `CrealityPrint.exe` sin `--cli`, que se sincroniza con la nube y borra los perfiles hechos a mano) y revisa el
  G-code: perfiles "maqueta", un solo filamento, cama a 65, sin repaso en seco en la primera capa y la capa de su
  grupo. De ahí salen el tiempo y los gramos reales (`laminado.json`).

## Cómo regenerar

```
python estructura.py      # estructura_gen.scad y estructura_resumen.md (con sus propias comprobaciones)
python revisar.py         # todo; con TODO OK deja el sello para exportar.py (con --sub alm solo un subsistema, sin sello)
python probar_revisor.py  # el revisor contra errores puestos a propósito
python exportar.py        # stl/, 3mf/ (con la configuración adentro), piezas.json y material.md; pide el sello
python laminar.py         # lamina las tandas con el CLI de Creality Print y revisa el G-code -> laminado.json
python modelo_3d.py       # app/visor3d/maqueta_impresa.glb (el visor)
python esfuerzos.py       # esfuerzos.md: flexión, pandeo, remaches, cajeras y calor
python auditar.py         # auditoria.md: TODOS los criterios por pieza (primera capa, soportes, paredes, cama)
python manual_maqueta.py  # manual_maqueta.pdf (usa piezas.json de exportar.py) y la imagen de arriba (img/maqueta_iso.png)
```

Con varios agentes o procesos a la vez, `REVISAR_HILOS=3` limita los OpenSCAD en paralelo.

## Lo que cambió respecto del diseño anterior (manda lo físico)

Lo funcional no se movió (estaciones, alturas de bandas, carrusel, tolva, canaleta, sensores, cámaras). Sí cambió:

- La viga del pórtico pasó de y −45 a y −40,5 (alineada con el riel de la mesa de monedas); patas, columnas y
  postes en otras posiciones; ya no hay poste E4 (la compuerta cuelga de los bloques del tensor).
- Salida del embudo E4 de Ø20 a **Ø29**: por Ø20 no pasaba acostada la moneda de 26,7 mm. Aleta nueva de 20 mm.
- Obturador del almacén de corredera (1,9 mm, enrasada con el piso en un rebaje de la placa fija; la mueve
  alm_palanca, una horquilla en el eje del SG90 que gira 90° y la corre 30 mm: la aleta de antes dejaba un bolsillo
  de 4,4 mm donde quedaban monedas); 28BYJ-48 girado 90° (una pestaña
  quedaba sobre la boca del embudo); embudo de carga que termina en z 335 (el imán lo golpeaba).
- Paleta del empujador de 56 mm con la esquina de abajo cortada (rozaba los tacos de la banda al dar la vuelta).
- Separadores de la banda de vasos recortados 3 mm y una muesca en el bastidor: el vaso recién entregado a la
  canaleta tocaba el borde.
- El vaso retenido por el escape queda ~17 mm más abajo que lo que dibujaba el visor.
- Sin rodillo de retorno C en la cinta de monedas: quedaba 6 mm dentro del lazo y no tocaba la banda.
- Separadores repartidos en partes iguales sobre la banda cerrada: 11 en la de vasos (≈ 79,6 mm) y 15 en la de
  monedas (≈ 41 mm); con un paso fijo de 80 o 40 quedaba una casilla corta.
- El marco de la canaleta va amarrado al poste de la cinta de vasos (`can_amarre`): antes quedaba suelto y el carro
  lo corría al atracar.

## Esfuerzo, deformación y calor

`esfuerzos.py` → [esfuerzos.md](esfuerzos.md): cada tubo cargado (flexión y flecha), cada columna (pandeo), cada
unión de remaches (cortante y arranque de la uña), el aplastamiento en las cajeras y cada fuente de calor que toca
PLA, contra el PLA impreso (admisible 10 MPa en cargas cortas, 5 MPa sostenidas por fluencia, nada que cargue por
encima de 45 °C). Todo cumple; lo más exigido son los remaches del colgante del retorno B con la banda tensa (4,0 MPa
de 5); la viga del pórtico, con el puntal, queda en 3,0 MPa de 10 cuando la prensa asienta una tapa. Dos condiciones salen de ahí y están en el manual: el NEMA 17 **no apoya directo**
en su placa (separadores de nailon: a 1 A/fase se estima en ~36 °C, y se mide en la prueba de banco: si pasa de 45 °C, Vref a 0,8 A) y la tira LED del panel va
sobre cinta de aluminio y con una resistencia de 3,3 Ω 1 W en serie (la del circuito, `sim/electrica.py`: ~1,4 W en
las tiras en vez de 4). Son modelos simples del lado seguro, no elementos finitos.

## Lo que no está verificado

- Los remaches y los encajes se prueban al imprimir; los esfuerzos son calculados, no ensayados. Hay que medir la
  carcasa del NEMA 17 en la prueba de banco.
- La rosca impresa de los prisioneros de la canaleta (se prueba antes de la tanda: ver "Cómo imprimir") y la cola de
  milano de las bocas del muelle.
- Las medidas marcadas `MEDIR` en cada `.scad` (servos, sensores, webcam): medirlas antes de imprimir esas piezas.
- La caja de control no es parte de esta carpeta (su cableado sí está en el manual).
