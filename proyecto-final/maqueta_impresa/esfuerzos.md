# Esfuerzos, deformación y calor en la maqueta impresa (GENERADO por esfuerzos.py)

PLA impreso: E = 3500 MPa, admisible 10 MPa en cargas cortas y 5 MPa en cargas que están siempre (por fluencia); ningún PLA que cargue algo por encima de 45 °C (Tg 55-60 °C). Modelos simples del lado seguro (viga apoyada, carga en el peor punto, columna con extremo libre); no es un análisis por elementos finitos. Tubo 16 × 16 pared 1,6: A = 101 mm², I = 3224 mm⁴.

## Mecánica

| Qué | Carga | Largo | Esfuerzo (MPa) | Admisible | Flecha (mm) | ¿Cumple? | De dónde sale |
|---|---|---|---:|---:|---:|---|---|
| tubo P1-P2 | 8.8 N | 365 mm | 1.00 | 5 | 0.50 | sí | viga del portico: almacen con 150 monedas, 28BYJ, tubo de tapas, prensa, sensores (masas.yaml); flecha admisible 0.7 mm |
| tubo P1-P2 | 60.0 N | 365 mm | 4.71 | 10 | 1.57 | sí | la prensa asentando una tapa: 60 N, reaccion en la viga en x 280 (a 330 mm de P1); flecha admisible 1.8 mm |
| tubo T2-T3 | 5.2 N | 200 mm | 0.32 | 5 | 0.05 | sí | riel +y de monedas: mitad de la cinta + NEMA 17 (280 g) + jaula; flecha admisible 0.4 mm |
| tubo T1-L | 5.2 N | 276 mm | 0.45 | 5 | 0.13 | sí | riel -y de monedas: mitad de la cinta + compuerta E4 + FC-51; flecha admisible 0.6 mm |
| tubo M1-M2 | 1.5 N | 125 mm | 0.12 | 10 | 0.01 | sí | tope del muelle: carro de 0,64 kg a 0,12 m/s frenado en 3 mm de espuma (F = m v^2 / 2 d = 1,5 N); flecha admisible 0.6 mm |
| tubo Q2-L | 1.1 N | 55 mm | 0.15 | 5 | 0.01 | sí | brazo de la camara cenital: webcam + anillo (110 g) en la punta (voladizo de 55 mm); flecha admisible 0.6 mm |
| columna F2-T2 | 4.4 N | 430 mm | 0.04 | 5 | 0.00 | sí | pata de la mesa de monedas: un tercio de la cinta y el NEMA; pandeo critico 602 N (SF 137) |
| columna F4-P1 | 4.4 N | 400 mm | 0.04 | 5 | 0.00 | sí | columna del portico: mitad de lo colgado de la viga; pandeo critico 696 N (SF 158) |
| columna F5-P2 | 6.4 N | 400 mm | 0.06 | 5 | 0.00 | sí | columna del portico, lado +x: ademas lleva el empujador (MG996R y paleta); pandeo critico 696 N (SF 109) |
| columna V2-L | 3.4 N | 110 mm | 0.03 | 5 | 0.00 | sí | poste de la cinta de vasos (un cuarto del bastidor con 5 vasos llenos), punta libre; pandeo critico 2301 N (SF 670) |
| columna C1-L | 0.6 N | 170 mm | 0.01 | 5 | 0.00 | sí | poste de la canaleta, punta libre; pandeo critico 964 N (SF 1571) |
| remaches: puente del almacen a la viga | 2.6 N en 6 | - | 0.06 | 5 | 0.00 | sí | almacen impreso + 28BYJ + 150 monedas de hasta 7,1 g: cuelga de 6 remaches en cortante (corte) |
| remaches: colgante del tubo de tapas a la viga | 1.3 N en 4 | - | 0.04 | 5 | 0.00 | sí | tubo + abrazaderas + 10 tapas (corte) |
| remaches: placa de la prensa a la viga | 60.0 N en 3 | - | 2.58 | 10 | 0.00 | sí | reaccion de los 60 N de la prensa (corte) |
| remaches: laterales de vasos a los postes | 13.7 N en 4 | - | 0.44 | 5 | 0.00 | sí | bastidor con banda, motor y 5 vasos llenos (133 g c/u) (corte) |
| remaches: bancada de monedas a los rieles | 3.9 N en 8 | - | 0.14 | 3 | 0.00 | sí | la bancada cuelga de 8 remaches desde arriba (la una abre abajo) (traccion) |
| remaches: placas colgantes de los rodillos de retorno | 1.5 N en 12 | - | 0.04 | 3 | 0.00 | sí | 3 rodillos de aluminio con 608 (traccion) |
| remaches: cabezales de la canaleta a los postes | 5.8 N en 8 | - | 0.09 | 5 | 0.00 | sí | varillas con 4 vasos llenos (corte) |
| remaches: tubo en su cajera (cualquier nodo) | 3.4 N en 2 | - | 0.22 | 5 | 0.00 | sí | el poste mas cargado: un cuarto del bastidor de vasos (corte) |
| remaches: topes del muelle a M1-M2 | 1.5 N en 2 | - | 0.10 | 10 | 0.00 | sí | choque del carro (1,5 N) (corte) |
| cajera del nodo (aplastamiento) | 63.4 N | 16 x 22 mm | 0.18 | 5 | 0.00 | sí | tubo apoyado en el piso de la cajera, 2,4 mm de pared alrededor |

El caso más exigido es **tubo P1-P2**: 4.71 MPa de 10 admisibles (factor 2.1 sobre el admisible, que ya lleva factor 3 sobre la rotura entre capas).

**Deformación permanente (fluencia):** todas las cargas sostenidas quedan por debajo de 5 MPa, donde el PLA impreso no fluye de forma medible a temperatura ambiente. La flecha mayor es elástica (vuelve al descargar).

## Calor

| Fuente | Potencia | Temperatura estimada | ¿Cumple? | Qué PLA toca | Qué hacer |
|---|---|---|---|---|---|
| NEMA 17 de cada cinta (17HS4401 a 1 A/fase) | 1.1 W medio / 3.0 W continuo | 33 °C / 46 °C continuo | sí (continuo al 100 %: NO) | mon_jaula_nema / vas_placa_motor (la brida del motor apoya en la placa) | la brida NO debe tocar la placa: 4 separadores de nailon de 3 mm en los M3 (aire entre medio) y correr la prueba de banco de 200 pasadas con un termometro en la carcasa: si pasa de 45 C, bajar Vref a 0,8 A o imprimir esas dos piezas en PETG (Tg 80 C) |
| 28BYJ-48 (5 V, medio paso: 0,1-0,2 A) | 0.2 W medio | 31 °C | sí | alm_puente (pestanas del motor) | ninguna: la carcasa queda tibia (~35 C) |
| SG90 (desvio, obturador, tapas, escape) | 0.2 W medio | 31 °C | sí | bridas y cunas impresas | ninguna |
| MG996R de la prensa (0,2 s trabado cada ciclo) | 0.4 W medio | 31 °C | sí | tap_pre_placa (separadores) | ninguna mientras la prensa no quede trabada: el firmware la suelta a los 200 ms (tiempos_ms); trabado 15 W lo quemaria a el antes que al PLA |
| MG996R del empujador | 0.3 W medio | 30 °C | sí | tap_emp_placa_servo | ninguna |
| tira LED del panel de luz (5 V, 1 m) A MEDIA POTENCIA sobre cinta de aluminio | 1.0 W medio / 2.0 W continuo | 35 °C / 45 °C continuo | sí | vas_panel_a/_b (marco de 1,6 mm) | OBLIGATORIO: la tira va sobre cinta de aluminio pegada al marco (reparte el calor) y alimentada a media potencia (resistencia en serie o dimmer PWM; la camara solo necesita luz pareja, no maxima). A plena potencia y pegada directo al PLA llegaria a 45-65 C |
| anillo LED de la camara cenital (en la carcasa de la webcam) | 1.0 W medio | 40 °C | sí | mon_camara (abrazadera, por la webcam) | ninguna: ~40 C en el anillo, menos en la abrazadera |
| fuente, bucks, A4988, ESP32, ventilador | 9.0 W medio | 25 °C | sí | nada: van en la caja de control (acrilico y aluminio) | ninguna |

**El único punto caliente es el NEMA 17.** A 1 A por fase disipa 3 W mientras las bobinas están excitadas; con el ciclo normal (37 % del tiempo y los drivers sueltos en reposo) la carcasa queda en ~33 °C, pero en una prueba continua sube a ~46 °C, justo en el límite. Por eso el motor NO debe apoyar directo en la placa impresa: 4 separadores de nailon de 3 mm en sus M3 dejan aire entre la brida y el PLA, y hay que medir la carcasa en la prueba de banco. Si pasa de 45 °C: Vref a 0,8 A (la cinta sobra par: margen ×9 y ×2,3 en peso.md) o esas dos placas en PETG.

## Lo que NO cubre

- No es un análisis por elementos finitos: cada pieza se redujo a su modelo de viga, columna o unión más simple.
- Las cargas son las de config/masas.yaml y config/parametros.yaml (estimadas: pesar al armar).
- Los valores del PLA son los publicados para piezas impresas con 4 perímetros a 20-25 °C; el filamento húmedo o las capas mal pegadas bajan la resistencia entre capas (por eso el factor 3).
- Las temperaturas son estimadas con resistencias térmicas típicas; hay que MEDIR la carcasa del NEMA 17.
