# Esfuerzos, deformación y calor en la maqueta impresa (GENERADO por esfuerzos.py)

PLA impreso: E = 3500 MPa, admisible 10 MPa en cargas cortas y 5 MPa en cargas que están siempre (por fluencia); la uña de un remache, 0,6 de eso (trabaja entre capas); ningún PLA que cargue algo por encima de 45 °C (Tg 55-60 °C). Modelos de resistencia de materiales, no elementos finitos; las secciones de piezas se miden cortando su malla del ensamble (_cache/ens). Tubo 16 × 16 pared 1,6 con hueco octogonal: A = 110,2 mm², I = 3758 mm⁴. Tensión de la banda T = 20 N por ramal (config/masas.yaml, PROVISIONAL: se mide al montar).

**Resultado: todo cumple.**

## Mecánica

| Qué | Carga | Largo | Esfuerzo (MPa) | Admisible | Flecha (mm) | ¿Cumple? | De dónde sale |
|---|---|---|---:|---:|---:|---|---|
| tubo P1-P2, tramo P1-puntal (continua sobre P1, puntal y P2) | 20.9 N | 276 mm | 1.43 | 5 | 0.29 | sí | cargas en su x (1001 g en x 78, 359 g en x 174, 184 g en x 200, 177 g en x 258, 12 g en x 42, 175 g en x 20, 175 g en x 58) + peso propio; P1 y P2 apoyos simples (giro 0.0035 y 0.0007 rad, menos que el libre de la cajera, 0.0182); flecha mayor en x 74, admisible L/500 = 0.55 mm |
| tubo P1-P2, tramo puntal-P2 (continua sobre P1, puntal y P2) | 20.9 N | 89 mm | 1.34 | 5 | 0.02 | sí | cargas en su x (1001 g en x 78, 359 g en x 174, 184 g en x 200, 177 g en x 258, 12 g en x 42, 175 g en x 20, 175 g en x 58) + peso propio; P1 y P2 apoyos simples (giro 0.0035 y 0.0007 rad, menos que el libre de la cajera, 0.0182); flecha mayor en x 263, admisible L/500 = 0.18 mm |
| tubo P1-P2 con la prensa (continua sobre P1, puntal y P2) | 60.0 N | 276 mm | 3.01 | 10 | 0.08 | sí | la prensa asentando una tapa: 60 N hacia arriba en x 280, toda a la viga, sumada a las cargas de siempre; flecha de la prensa sola 0.08 mm en x 109 (tramo P1-puntal), admisible L/200 = 1.38 mm (vuelve al soltar) |
| columna puntal tap_puntal_inf/_sup (x 226) | 20.9 N | 373 mm | 0.11 | 5 | 0.00 | sí | reaccion de la viga continua (las cargas de siempre); I 1197 mm4 de la union del medio (z 205, 191 mm2: las dos medias sin trabajar juntas) en todo el largo, en vez de 3758 del tubo. Comprimido hasta 47 N de prensa; con 60 tira 5.9 N; pandeo critico 297 N (SF 14) |
| remaches: puntal (el de la silla de abajo, solo) | 5.9 N | - | 0.80 | 10 | 0.00 | sí | a compresion el puntal apoya a contacto (sillas y union); tira solo con mas de 47 N de prensa: con 60 N, 5.9 N a cortante en r_tap_punt_inf_1 (los otros 4 van de a 2) (corte) |
| tubo F6-F5 bajo el puntal | 20.9 N | 108 mm | 1.13 | 5 | 0.04 | sí | el puntal apoya en x 226: viga apoyada entre los pasadores del empalme e_F6-F5_1 (x 185,5, sobre la mesa) y de F5 (x 293,4); flecha admisible L/500 = 0.22 mm |
| remaches: cajera P2 sujetando la viga hacia abajo | 22.4 N c/u (2) | - | 3.02 | 10 | 0.00 | sí | con el puntal P2 tira de la viga hacia abajo: 6.4 N siempre, hasta 44.8 N con la prensa (la peor de: puntal firme, o puntal flojo y la viga apoyada en P1 y P2) (corte) |
| tubo T2-T3 | 5.2 N | 200 mm | 0.28 | 5 | 0.04 | sí | riel +y de monedas: mitad de la cinta + NEMA 17 (280 g) + jaula; flecha admisible 0.4 mm |
| tubo T1-L | 5.2 N | 276 mm | 0.38 | 5 | 0.11 | sí | riel -y de monedas: mitad de la cinta + compuerta E4 + FC-51; flecha admisible 0.6 mm |
| tubo M1-M2 | 1.5 N | 125 mm | 0.10 | 10 | 0.00 | sí | tope del muelle: carro de 0,64 kg a 0,12 m/s frenado en 3 mm de espuma (F = m v^2 / 2 d = 1,5 N); flecha admisible 0.6 mm |
| tubo Q2-L | 1.1 N | 55 mm | 0.13 | 5 | 0.00 | sí | brazo de la camara cenital: webcam + anillo (110 g) en la punta (voladizo de 55 mm); flecha admisible 0.6 mm |
| columna F2-T2 | 4.4 N | 430 mm | 0.04 | 5 | 0.00 | sí | pata de la mesa de monedas: un tercio de la cinta y el NEMA; pandeo critico 702 N (SF 160) |
| columna F4-P1 | 6.4 N | 400 mm | 0.06 | 5 | 0.00 | sí | columna del portico: su reaccion de la viga continua sobre el puntal; pandeo critico 811 N (SF 127) |
| columna F5-P2 | 4.4 N (tracción) | 400 mm | 0.04 | 5 | 0.00 | sí | columna del portico, lado +x: su reaccion de la viga (que ahora tira de ella hacia arriba) y el empujador (MG996R y paleta); a traccion: no pandea |
| columna V2-L | 3.4 N | 110 mm | 0.03 | 5 | 0.00 | sí | poste de la cinta de vasos (un cuarto del bastidor con 5 vasos llenos), punta libre; pandeo critico 2682 N (SF 781) |
| columna C1-L | 0.6 N | 170 mm | 0.01 | 5 | 0.00 | sí | poste de la canaleta, punta libre; pandeo critico 1123 N (SF 1832) |
| remaches: colgante del tubo de tapas a la viga | 7.8 N c/u (2) | - | 2.30 | 3 | 0.00 | sí | tubo + abrazaderas + colgante + dedos + SG90 + 10 tapas (184 g) en y -100, pivote en el borde +y del ala (traccion) |
| remaches: placa de la prensa a la viga y a la columna | 9.2 N (el mas cargado de 7) | - | 2.71 | 6 | 0.00 | sí | 60 N de prensa: M = F x 51,3 repartido como F x 51,3 x d / suma d2, d = 406 - z; cortante F/7 = 8.6 N (traccion) |
| placa de la prensa, entre capas (z 385.8) | 60 N | - | 2.17 | 10 | 0.00 | sí | seccion mas debil medida en _cache/ens/tap_pre_placa.stl: 461 mm2, I 35290 mm4 fuera del plano (centroide en y -58.4) e 77122 en el plano; flexion de los dos lados + axial |
| remaches: puente del almacen a la viga | 2.2 N c/u (6) | - | 0.30 | 5 | 0.00 | sí | almacen impreso + comprado + monedas (1360 g): cuelga de 6 remaches en cortante (corte) |
| remaches: laterales de vasos a los postes | 1.7 N c/u (8) | - | 0.23 | 5 | 0.00 | sí | bastidor con banda, motor y 5 vasos llenos (133 g c/u) (corte) |
| remaches: bancada de monedas a los rieles | 0.7 N c/u (6) | - | 0.09 | 5 | 0.00 | sí | 6 remaches de costado a la cara interior de los rieles (corte) |
| remaches: cabezales de la canaleta a los postes | 0.7 N c/u (8) | - | 0.10 | 5 | 0.00 | sí | varillas con 4 vasos llenos (corte) |
| remaches: tubo en su cajera (cualquier nodo) | 1.7 N c/u (2) | - | 0.23 | 5 | 0.00 | sí | el poste mas cargado: un cuarto del bastidor de vasos (corte) |
| remaches: topes del muelle a M1-M2 | 0.8 N c/u (2) | - | 0.10 | 10 | 0.00 | sí | choque del carro (1,5 N) (corte) |
| remaches: bloques del motriz al riel (banda) | 10.0 N c/u (2 por bloque) | - | 1.35 | 5 | 0.00 | sí | por bloque [20.0, 0.0] N (motriz + retorno A, T = 20 N); el momento lo toman los labios sobre y bajo el riel (corte) |
| bajada del retorno A (raiz en z 426) | [10.3, 10.0] N | - | 2.07 | 5 | 0.00 | sí | seccion medida en mon_rod_mot_m: 162 mm2, I 4374 mm4; momento 976 N mm. Se imprime sobre la cara -x: la flexion estira en el plano de las capas |
| remaches: bloques del tensor al riel (banda) | 8.2 N c/u (2 por bloque) | - | 1.10 | 5 | 0.00 | sí | la x del rodillo tensor; su z (hacia abajo) apoya el labio en el riel (corte) |
| rosca del M3 de empuje del tensor de monedas | 9.7 N axial, 14.7 N lateral | - | 0.57 | 5 | 0.00 | sí | autorroscante en 8.6 mm de PLA: corte en la rosca y apoyo del costado; empuja el 608 con 17.6 N |
| remaches: colgante b_m del retorno B al taco_1 (banda) | 30.0 N | - | 4.04 | 5 | 0.00 | sí | [-4.5, 9.5] N en el eje de B, 2 remaches de costado a 17 mm; b_p apoya su labio en el riel (sin traccion) (corte) |
| rosca del prisionero M3 del tensor de vasos | 20.0 N por lateral | - | 0.73 | 5 | 0.00 | sí | el prisionero empuja el 608 de x 400 hasta el fin de la corredera; rosca de 5,8 mm en el PLA (O2,5, MEDIR) |
| columna lateral de la cinta de vasos (4 x 48) | 20.0 N | 120 mm | 0.10 | 5 | 0.00 | sí | la banda junta los dos rodillos con 2 T: T por lateral; tramo libre mas largo, del ultimo remache a la bancada (x 280) al rodillo de x 400; pandeo critico 614 N (SF 31) |
| remaches: placa del motor de vasos a sus postes | 1.3 N c/u (2 de arriba) | - | 0.39 | 3 | 0.00 | sí | momento del NEMA (centro 28 detras de la placa) (traccion) |
| postes del NEMA de vasos (raiz en la lateral) | 2.8 N | - | 0.04 | 5 | 0.00 | sí | momento 174 N mm (centro del NEMA a 61 de la lateral); los 4 postes de 32,8: 540 mm2, I 152055 mm4 en z |
| cajera del nodo (aplastamiento) | 63.4 N | 16 x 22 mm | 0.18 | 5 | 0.00 | sí | tubo apoyado en el piso de la cajera, 2,4 mm de pared alrededor |

El esfuerzo más exigido es **remaches: colgante b_m del retorno B al taco_1 (banda)**: 4,04 MPa de 5,0 admisibles (factor 1,2 sobre el admisible, que ya lleva factor 3 sobre la rotura entre capas).

**Viga del pórtico P1-P2.** Lleva 20,9 N en total y desde el 2026-10-25 un puntal en x 226 (tap_puntal_inf / _sup: tubo 16 × 16 del tubo del piso F6-F5 a la cara de abajo de la viga). Sin él, apoyada en P1 y P2, flectaba **1,30 mm** en x 127 contra 0,73 admisibles. Continua sobre P1, el puntal y P2 la flecha mayor es **0,29 mm** en el tramo P1-puntal (276 mm, admite 0,55) y 0,022 mm en el tramo puntal-P2 (89 mm, admite 0,18); el esfuerzo mayor, 1,43 MPa. El puntal toma 20,9 N, P1 6,4 N y P2 -6,4 N: la viga gira sobre el puntal y P2 la **sujeta hacia abajo** (sus 2 remaches a cortante). P1 y P2 siguen como apoyos simples: el giro de la viga ahí no llega al libre de la cajera.

**Prensa.** Sus 60 N hacia arriba en x 280 los toman el puntal (26,8 N, tirando), P2 (34,0 N) y P1 (0,8 N). El puntal sigue comprimido (a contacto, sin holgura) mientras la prensa no pase de 47 N; con 60 N tira 5,9 N y la holgura de sus remaches (agujero 4,4 para 4) puede abrirse: la prensa pierde parte del apriete de 0,5 solo por encima de 47 N. Sin el puntal, P2 cargaba 9,4 N y la prensa levantaba la punta de la viga en su cajera desde 10 N.

**Asiento por holgura (al armarla; no es elástico ni crece con el tiempo).** Antes, P1, el empalme e_P1-P2_1 y P2 eran pasadores en línea y el empalme podía bajar 3,3 mm. Ahora el tubo t_P1-P2_2 queda entre el puntal (a contacto) y el pasador de P2, y el manguito gira sobre su pasador del lado del puntal (x 145,5) lo que deja su cajera: 0,0182 × 26 = **0,47 mm** en el pasador de x 119,5 (con la holgura nominal; con lo que encogen las cajeras al imprimir, menos). Como P2 sujeta hacia abajo, si su punta sube lo que dejan la cajera y los agujeros de r_P2_1 (2 × 0,2) la viga gira sobre el puntal y el empalme baja 0,48 mm más: en el peor caso **1,10 mm** en x 119,5, que en el tramo P1-empalme queda en 0,80 mm en la horquilla del almacén (x 78,2) y 0,65 / 0,36 mm en los tacos del riel (x 58 / 20). El tubo t_P1-P2_2 solo gira con la punta de P2: en el peor caso baja 0,15 mm en x 200 (tapas) y sube 0,32 en x 280 (prensa; desde el ensamble, con el tubo centrado en la cajera, la mitad: 0,16 de los 0,5 de apriete). El puntal se monta con la viga levantada a mano en x 226 hasta que quede recta: así la deja en su lugar y no se suma la flecha que ya tenía.

**Deformación permanente (fluencia):** la carga sostenida más exigida es remaches: colgante b_m del retorno B al taco_1 (banda), 4,04 MPa de 5,0: todas quedan por debajo del umbral en que el PLA impreso fluye de forma medible a temperatura ambiente.

**Banda de monedas** (rodillos de cinta_monedas.scad, T = 20 N): cada rodillo recibe T por ramal, en la bisectriz de los dos tramos.

| Rodillo | Resultante (× T) | Con T (N) | La toma |
|---|---:|---:|---|
| motriz | 1.39 | 27.8 | bloques del motriz (con A: se anulan en z) |
| tensor | 1.81 | 36.2 | bloques del tensor (tornillo de empuje) |
| A | 1.44 | 28.7 | bajadas de los bloques del motriz |
| B | 0.85 | 17.0 | colgantes b_m (taco_1) y b_p (labio) |

La de vasos (rodillos en x 0 y 400) junta los dos rodillos con 2 T: T en cada prisionero del tensor y T de compresión en cada lateral. Con el tensor a tope, la T real sale del largo del empalme de la banda: se mide con una balanza de gancho en un ramal (manual).

## Calor

| Fuente | Potencia | Temperatura estimada | ¿Cumple? | Qué PLA toca | Qué hacer |
|---|---|---|---|---|---|
| NEMA 17 de cada cinta (17HS4401 a 1 A/fase) | 1.50 W | 36 °C | sí | mon_jaula_nema / vas_placa_motor | la brida NO toca la placa: 4 separadores de nailon de 3 mm en los M3 (aire entre medio). Prueba de banco con un termometro en la carcasa (manual, «Antes de encender»): si pasa de 45 C, bajar Vref a 0,8 A (o esas dos piezas en PETG) |
| 28BYJ-48 (5 V, medio paso: 0,1-0,2 A) | 0.22 W | 31 °C | sí | alm_puente (pestanas del motor) | ninguna: la carcasa queda tibia (~35 C) |
| SG90 (desvio, obturador, tapas, escape) | 0.20 W | 31 °C | sí | bridas y cunas impresas | ninguna |
| MG996R de la prensa (0,2 s trabado cada ciclo) | 0.40 W | 31 °C | sí | tap_pre_placa (costillas) | ninguna mientras la prensa no quede trabada: el firmware la suelta a los 200 ms (tiempos_ms); trabado 15 W lo quemaria a el antes que al PLA |
| MG996R del empujador | 0.30 W | 30 °C | sí | tap_emp_placa_servo | ninguna |
| tira LED del panel de luz (5 V, 2 tramos) con resistencia en serie, sobre cinta de aluminio | 1.38 W | 39 °C | sí | vas_panel_a/_b (marco de 1,6 mm) | OBLIGATORIO: la resistencia de 3,3 Ω 1 W en línea en el +5 V (del lado de la caja, lejos del PLA) y la tira sobre cinta de aluminio pegada al marco (reparte el calor). Sin la resistencia (4 W) y pegada al PLA llega a ~65 C. Prueba (manual, «Antes de encender»): I × V_tiras ≤ 1,5 W; se esperan ~0,36 A con ~3,8 V en las tiras; si pasa, 4,7 Ω |
| anillo LED de la camara cenital (en la webcam) | 1.75 W | 51 °C (no toca PLA) | sí | ninguno directo: rodea el lente (z ~602) y la abrazadera mon_camara agarra la carcasa por arriba (z 639 a 689) | medir la abrazadera con el termometro en la prueba de banco; si pasa de 45 C, el anillo tambien con una resistencia en serie, en linea del lado de la caja |
| fuente, bucks, A4988, ESP32, ventilador | 9.00 W | 25 °C (no toca PLA) | sí | nada: van en la caja de control (acrilico y aluminio) | ninguna |

**Puntos calientes.** El NEMA 17 disipa 1,5 W (I²R con micropaso) todo el tiempo que la línea anda, porque el firmware no suelta los A4988 en las pausas: la carcasa queda en ~36 °C, debajo del límite, pero igual no apoya en el PLA (separadores de nailon de 3 mm) y se mide en la prueba de banco: si pasa de 45 °C, Vref a 0,8 A (la cinta sobra par: margen ×10 y ×2,2 en peso.md). El panel de luz pide 4 W sin nada en serie (0,8 A a 5 V): pegado al marco de 1,6 llegaría a ~65 °C, más que la Tg. Por eso va con una resistencia de 3,3 Ω 1 W en línea en su +5 V, del lado de la caja (sim/electrica.py, docs/electrica.md): las tiras quedan en 1,38 W (~39 °C) sobre cinta de aluminio, y la resistencia disipa 0,44 W fuera del PLA. No va un MOSFET con PWM.

## Lo que NO cubre

- No es un análisis por elementos finitos: cada pieza se redujo a su modelo de viga, columna, sección o unión más simple.
- La torsión de la viga del pórtico por lo que cuelga delante (almacén, tapas y prensa a 31-60 mm del eje): con nodos rígidos la viga gira ~0,4-0,5° (pórtico 3D de la auditoría del 2026-10-25) y la holgura de las cajeras suma giro (las paredes de la silla de arriba del puntal la frenan en x 226).
- El asiento por holgura sale de la holgura nominal (0,2 por lado en las cajeras y en los agujeros de los remaches); el real depende de cómo quede armada. El puntal se toma como apoyo rígido (se acorta 0,02 mm y el tubo del piso baja 0,04 bajo él) y sin cargas de costado.
- Las cargas son las de config/masas.yaml, config/monedas.yaml y piezas.json (estimadas: pesar al armar); T de la banda es la de montaje (medirla), sin la diferencia de tensión que suma el par del motor.
- Los valores del PLA son los publicados para piezas impresas con 4 perímetros a 20-25 °C; el filamento húmedo o las capas mal pegadas bajan la resistencia entre capas (por eso el factor 3). El arranque real de la uña no está medido.
- Las temperaturas son estimadas con resistencias térmicas típicas; hay que MEDIR la carcasa del NEMA 17 y el panel.
