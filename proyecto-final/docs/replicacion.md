<!-- Generado por `python -m app.documentos`. No editar a mano. -->


# Replicación en la vida real

Todo lo que la simulación supone y que hay que **medir en el montaje real** antes de dar el diseño por cerrado: medidas físicas, monedas, sensores con su error individual y tiempos. Cada valor tiene su lugar en la configuración: al medirlo, se cambia ahí y se vuelve a generar este documento (`python -m app.documentos`).

Estado de hoy: **todos los valores de esta página son PROVISIONALES** salvo las 9 monedas marcadas como verificadas. Salen de hojas de datos y valores típicos, no de mediciones propias.

## 1. Medidas físicas por confirmar

| Qué | Valor provisional | Dónde se cambia | Cómo medirlo |
|---|---|---|---|
| Altura del vaso | 90 mm | `config/parametros.yaml · vasos.altura_mm` | Calibrador sobre 3 vasos del lote que se va a usar. |
| Diámetro exterior del vaso | 62 mm | `vasos.diametro_mm` | Calibrador en la boca y en la base (se usa el mayor). |
| Separación entre casillas de la cinta de vasos | 80 mm | `vasos.separacion_casilla_mm + sim/urdf/cinta_vasos.urdf` | Diámetro del vaso + 15 mm de margen, en el CAD. |
| Altura del separador de la cinta de vasos | 15 mm | `vasos.separador_altura_mm` | Del CAD: por debajo del reborde para que el vaso pueda colgarse en la canaleta. |
| Motor paso a paso de las cintas | NEMA17 17HS4401 (provisional) | `motor_paso_a_paso.modelo` | Confirmar el torque con la cinta cargada antes de elegir driver. |
| Altura de la mesa de la cinta de monedas | 430 mm | `sim/mundo.py · ALTURA_MESA_MONEDAS` | Del CAD: tiene que quedar sobre el selector y los tubos. |
| Altura de la mesa de la cinta de vasos | 100 mm | `sim/mundo.py · ALTURA_MESA_VASOS` | Del CAD: el vaso colgado al final de la canaleta no puede tocar el piso. |
| Tubos del almacén (diámetro interior y alto) | 29 mm x 58 mm | `sim/mundo.py · TUBO_*` | Interior 2 mm mayor que la moneda más grande (1000 nueva, 26,7 mm). |
| Capacidad de cada tubo | 25 monedas | `planta.capacidad_tubo` | Alto útil del tubo / 2,2 mm por moneda (medir la pila real). |
| Monedas por vaso (lote) | 10 | `planta.monedas_por_vaso` | Decisión del grupo; el enunciado no lo fija. |
| Largo de la canaleta de entrega | 280 mm | `canaleta.largo_mm` | Del CAD; con 15° cada 100 mm baja 27 mm. |
| Separación entre rieles de la canaleta | 69 mm | `canaleta.separacion_rieles_mm` | Mayor que el cuerpo del vaso y menor que su reborde. |
| Trazado de la pista | 7 tramos, muros en [1992, 3834, 5676] mm | `pista.tramos / pista.obstaculos_mm` | Medir la pista real con cinta métrica (radios y largos). |
| Dimensiones del carro | 180 x 120 mm, rueda 65 mm | `vehiculo.*` | Del chasis comprado o del CAD. |
| Tiempo máximo de reacción de la cortina | 200 ms | `cortina_seguridad.reaccion_max_ms` | Con la velocidad real de la leva de la prensa. |

## 2. Monedas

18 clases en 4 generaciones (`config/monedas.yaml`). Las no verificadas hay que medirlas: diámetro con calibrador (+-0,02 mm) en 3 direcciones y masa con báscula de 0,01 g, al menos 5 piezas por clase, incluidas gastadas. Van al tubo de su denominación; las denominaciones sin tubo (todas menos $50, $100, $200, $500, $1000) van al compartimiento "otras": se guardan, no se empacan.

| Clase | Familia | Diámetro (mm) | Masa (g) | Material | Estado |
|---|---|---|---|---|---|
| 50_nueva | nueva | 17.0 | 2.0 | acero niquelado | verificada |
| 100_nueva | nueva | 20.3 | 3.3 | acero recubierto | verificada |
| 200_nueva | nueva | 22.4 | 4.6 | cuproniquel-zinc | verificada |
| 500_nueva | nueva | 23.7 | 7.1 | bimetalica | verificada |
| 1000_nueva | nueva | 26.7 | 10.0 | bimetalica | verificada |
| 50_antigua | antigua | 21.5 | 4.5 | cuproniquel-zinc | verificada |
| 100_antigua | antigua | 23.0 | 5.3 | bronce-aluminio | verificada |
| 200_antigua | antigua | 24.4 | 7.1 | cuproniquel-zinc | verificada |
| 500_antigua | antigua | 23.5 | 7.4 | bimetalica | verificada |
| 10_muy_antigua | muy_antigua | 19.0 | 3.4 | laton | **PROVISIONAL: medir** |
| 20_muy_antigua | muy_antigua | 21.0 | 4.0 | bronce-aluminio | **PROVISIONAL: medir** |
| 50_muy_antigua | muy_antigua | 22.0 | 4.8 | cuproniquel | **PROVISIONAL: medir** |
| 100_muy_antigua | muy_antigua | 26.0 | 8.0 | bronce-aluminio | **PROVISIONAL: medir** |
| 1_historica | historica | 18.0 | 2.5 | cobre-niquel | **PROVISIONAL: medir** |
| 2_historica | historica | 20.0 | 3.0 | bronce | **PROVISIONAL: medir** |
| 5_historica | historica | 21.5 | 4.0 | bronce-aluminio | **PROVISIONAL: medir** |
| 10_historica | historica | 23.0 | 5.0 | cuproniquel | **PROVISIONAL: medir** |
| 20_historica | historica | 24.5 | 6.0 | bronce-aluminio | **PROVISIONAL: medir** |

## 3. Sensores: error individual y cómo medirlo

La simulación reproduce el error de cada sensor con las probabilidades de `errores_sensores` (por lectura). Cada estación lee su sensor 3 veces durante la pausa y decide por mayoría, lo que baja una probabilidad p por lectura a ~3p² por decisión.

**Prueba de banco (200 pasadas):** pasar el mismo elemento 200 veces por el sensor y contar las veces que no lo ve (falsos negativos / 200); pasar 200 veces la casilla vacia y contar las veces que ve algo (falsos positivos / 200). Repetir con cada tipo de pieza (moneda de cada familia, botón de plástico, botón metálico, vaso) y anotar el peor caso.

| # | Sensor | Rango | Respuesta | Error típico | Error simulado | Mitigación | Conexión |
|---|---|---|---|---|---|---|---|
| 1 | [Infrarrojo de presencia](sensores.md#1-infrarrojo-de-presencia) | FC-51: 2-30 cm, ajustable; va a 5 cm de la cinta (un TCRT5000 solo ve hasta ~15 mm: tendria que ir tan bajo que los bloques altos lo golpearian) | < 1 ms (comparador LM393) | Falsos negativos con piezas muy oscuras o con acabado espejo que desvian el haz; falsos positivos con sol directo o flash sobre la cinta. | FN 0.5%, FP 0.1% | Capuchon que tape la luz ambiente en E1; ajustar el potenciometro del LM393 con la cinta vacia; voto de 3 lecturas; ademas E2 respalda a E1 (presencia recuperada). | Salida digital D0 del modulo a una entrada del ESP32 fijo (alimentar el modulo a 3,3 V). |
| 2 | [Sensor capacitivo](sensores.md#2-sensor-capacitivo) | 1-10 mm, ajustable con el tornillo de sensibilidad | ~5 ms (conmuta a ~100 Hz) | Humedad o polvo en la cara activa dan falsos positivos; piezas muy pequenas y delgadas pueden no alcanzar el umbral (falso negativo). | FN 0.2%, FP 0.1% | Montarlo a 3-5 mm de la trayectoria; calibrar con el boton de plastico mas pequeno; limpiar la cara; voto de 3 lecturas. | Salida NPN alimentada a 6-36 V: pasar por optoacoplador (PC817) o divisor a 3,3 V. NUNCA directo al ESP32. |
| 3 | [Sensor inductivo](sensores.md#3-sensor-inductivo) | 8 mm nominal en acero (placa patron de 24 x 24 mm); una moneda de 17-27 mm centrada da ~70-80 % de eso, y en bronce, laton y cuproniquel ~40-60 % mas: ~2,2-4,8 mm, contra 2 mm de banda. Por eso M18 de 8 mm y no el M12 de 4 mm (a traves de la banda no alcanzaba con las no ferrosas) | ~2 ms (conmuta a ~500 Hz) | Las monedas NO ferrosas (casi todas las antiguas y muy antiguas) se detectan a menos distancia que el acero: si la moneda pasa lejos, falso negativo y se iria como no metalica. | FN 1.0%, FP 0.0% | Centrado bajo la casilla (descentrado pierde la mitad del alcance); inserto IMPRESO en la bancada alrededor de la cara (es no enrasable: nada de metal a menos de ~2 cm); probar con cada familia, sobre todo las de bronce; voto de 3 lecturas; si el inductivo ve metal, manda sobre el capacitivo. | Salida NPN a 6-36 V: optoacoplador o divisor a 3,3 V. NUNCA directo al ESP32. |
| 4 | [Cámara cenital](sensores.md#4-cámara-cenital) | A 15 cm de la cinta (webcam con AUTOENFOQUE: las de foco fijo no enfocan tan cerca): campo de ~170 x 100 mm, 1 px ~ 0,1 mm | ~250 ms (captura + segmentacion + clasificador en la CPU del portatil) | Diametro +-0,08 mm (calibracion de escala y borde difuso); circularidad +-0,01; error de clase: sale de la matriz de confusion del modelo entrenado (fase 5); reflejos del anillo de luz en monedas brillantes. | diámetro ±0.08 mm, clase 2% | Anillo de luz difusa y cinta negra mate; calibrar la escala con una moneda patron medida con calibrador; umbral de confianza 0,85; regla de coherencia diametro-clase. | USB directo al PC (no pasa por el ESP32). |
| 5 | [Sensor del interior del vaso](sensores.md#5-sensor-del-interior-del-vaso) | 3 cm a ~1,2 m; a 1,5 cm sobre la boca el fondo queda a ~10,5 cm y el cono de 25 grados llega con ~6 mm de margen a la pared (aguanta ~3 grados de torcido: collar de centrado) | ~33 ms por medida; se votan 3 | ±3 % de la distancia (~4 mm a 12 cm): un objeto de pocos milímetros (una sola moneda acostada) puede no verse; reflejos en el fondo liso. | FN 0.5%, FP 0.2% | Margen de 10 mm sobre el fondo del vaso vacío; fondo del vaso mate; sensor centrado sobre la boca y fijo al pórtico; 3 medidas con voto. | I2C (SDA/SCL) al ESP32 fijo, 3,3 V; XSHUT a un pin para cambiarle la dirección. |
| 6 | [Sensor Hall del carrusel](sensores.md#6-sensor-hall-del-carrusel) | Con 4 mm de aire un iman N35 de 6 x 3 mm da ~70 mT en la cara; el A3144 conmuta con ~10-35 mT: sobra margen (hasta ~7-8 mm) | < 1 ms | Casi ninguno: no le afecta la luz ni el polvo. Solo falla si el imán se despega o queda lejos. | sin error simulado | Imán pegado en una cavidad impresa; homing lento; al terminar cada vuelta completa, comprobar que el imán aparece donde se esperaba. | Salida digital (colector abierto con pull-up) a una entrada del ESP32 fijo, 3,3-5 V. |
| 7 | [Cámara de vasos (silueta, ArUco y tapa)](sensores.md#7-cámara-de-vasos-silueta-aruco-y-tapa) | Las 3 casillas (~24 cm de ancho) a ~22 cm de la cámara; marcador de 20 x 20 mm legible aunque esté algo inclinado; 1 px ~ 0,2 mm | ~60 ms por cuadro (captura + silueta + detectMarkers en la CPU del portátil); se votan 3 cuadros | Silueta: sombras o reflejos en el borde del vaso (casi desaparecen a contraluz). Marcador: reflejo o tapado → no lo lee; casi nunca lee un número equivocado (el diccionario ArUco corrige errores de bits). Si se cae el PC, no hay verificación de vasos. | FN 0.2%, FP 0.1% | Panel LED difuso detrás (contraluz: la silueta no depende del color ni de la luz del salón); franjas con margen de ±5 mm; marcador mate; voto de 3 cuadros; si no lee el marcador decide la silueta (no se bloquea la línea); sin PC la cinta de vasos no avanza (falla segura: nada se llena sin verificar). | USB directo al PC (segunda webcam; no pasa por el ESP32). |
| 8 | [Cortina de seguridad](sensores.md#8-cortina-de-seguridad) | 3 cm a ~1,2 m en modo por defecto | ~33 ms por medida | +-3 % a corta distancia; las superficies negras reducen el alcance; reflejos pueden dar lecturas cortas (falso positivo). | FN 0.1%, FP 0.2% | Ventana de distancia (solo cuenta lo que esté a menos del largo de la zona); voto de 3 medidas (~100 ms); eje a 85 mm de la cinta para que el cono no toque los vasos. | I2C (SDA/SCL) al ESP32 fijo, 3,3 V. |
| 9 | [Arreglo de 5 infrarrojos de línea](sensores.md#9-arreglo-de-5-infrarrojos-de-línea) | 2-10 mm sobre el piso | < 1 ms | Cambios de luz y de altura del chasis; brillo de la cinta aislante. | pendiente (puntos 13-14) | Montar a 3-5 mm del piso con falda contra la luz; calibrar blanco y negro al arrancar. | 5 entradas (digitales o ADC) del ESP32 del carro. |
| 10 | [Ultrasónico frontal (respaldo)](sensores.md#10-ultrasónico-frontal-respaldo) | 2-400 cm, resolucion ~3 mm, apertura ~15 grados | ~25 ms por medida + ~60 ms recomendados entre disparos | +-3 mm tipico; ecos perdidos en superficies inclinadas; lecturas falsas por ecos de otros objetos. | pendiente (puntos 13-14) | Respaldo del laser: 2 mediciones seguidas; disparos cada 60 ms para que no se mezclen ecos. | TRIG a una salida; ECHO (5 V) por divisor a 3,3 V al ESP32 del carro. |
| 11 | [Encoders de las ruedas](sensores.md#11-encoders-de-las-ruedas) | 20 ranuras por vuelta: con rueda de 65 mm, ~10 mm de avance por pulso | Por interrupcion | Deslizamiento de las ruedas; rebotes del sensor de ranura. | pendiente (puntos 13-14) | Interrupciones con antirrebote; corregir la odometria con la linea. | 2 entradas con interrupcion del ESP32 del carro. |
| 12 | [Infrarrojo de la cuna de carga](sensores.md#12-infrarrojo-de-la-cuna-de-carga) | TCRT5000: 2-15 mm | < 1 ms | Igual que el de presencia: vasos transparentes reflejan poco. | pendiente (puntos 13-14) | Apuntarlo al fondo opaco del vaso; voto de 3 lecturas. | Entrada digital del ESP32 del carro. |
| 13 | [Láser de distancia frontal](sensores.md#13-láser-de-distancia-frontal) | 3 cm a ~1,2 m (modo por defecto); cono de ~25 grados | ~33 ms por medida | +-3 % a corta distancia; superficies negras o muy brillantes y el sol directo acortan el alcance o dan lecturas falsas. | pendiente (puntos 13-14) | 3 mediciones seguidas para decidir; el ultrasonico de respaldo cubre lo que el laser no ve. | I2C (SDA/SCL) al ESP32 del carro, 3,3 V. |

## 4. Tiempos

Valores de `tiempos_ms`. **Cómo medirlos:** en el firmware, marcar con `millis()`/`micros()` el inicio y fin de cada acción y mandarlo en el campo `ms` de los eventos (sección 10.1); para la ida y vuelta por serial, un `ping` desde el PC con marca de tiempo.

| Acción | Tiempo (ms) |
|---|---|
| avance casilla monedas | 600 |
| pausa casilla monedas | 1000 |
| presencia lectura | 2 |
| material lectura | 5 |
| intervalo entre lecturas | 30 |
| vision captura inferencia | 400 |
| desvio | 150 |
| carrusel giro | 500 |
| compuerta tubo | 600 |
| avance casilla vasos | 1000 |
| pausa casilla vasos | 800 |
| camara vasos cuadro | 60 |
| tapa caida | 500 |
| prensa ciclo | 1400 |
| empujador | 700 |
| cortina lectura | 33 |
| serial ida vuelta | 20 |
| esp now latencia | 10 |

### Presupuesto: ¿cabe cada acción en su hueco?

Ciclo de la cinta de monedas: **1600 ms** (≈ 38 elementos por minuto). Ciclo mínimo de la cinta de vasos: **2400 ms**. Reacción de la cortina: **119 ms**.

| Chequeo | Necesita (ms) | Disponible (ms) | Margen | Estado | Por qué |
|---|---|---|---|---|---|
| Las lecturas repetidas caben en la pausa | 125 | 1000 | +875 | OK | Cada estacion lee su sensor varias veces (separadas para que sean independientes) y vota, y el evento viaja al PC, con la cinta quieta. |
| La vision decide con la cinta quieta | 820 | 1000 | +180 | OK | 2 foto(s) + segmentacion + clasificador + ida y vuelta por serial, dentro de la pausa en E5. |
| La compuerta de desvio se pone antes de que caiga la pieza | 170 | 600 | +430 | OK | El veredicto ya se sabe desde la vision; el desvio se mueve mientras la cinta trae la pieza a la descarga. |
| El carrusel pone el tubo bajo la carga antes de que caiga la moneda | 520 | 1600 | +1080 | OK | El carrusel gira al tubo de la denominacion durante el ciclo en que la moneda va de la vision a la descarga. |
| El carrusel suelta un lote y vuelve entre dos monedas | 1600 | 1600 | +0 | OK | Girar el tubo al agujero, abrir y cerrar el obturador y volver a la posicion de carga, sin frenar la cinta de monedas. |
| Llega un lote mas lento de lo que la cinta de vasos lo despacha | 2400 | 16000 | +13600 | OK | Peor caso: todas las monedas de la misma denominacion (un lote cada `lote` ciclos). |
| La camara de vasos decide con la cinta de vasos quieta | 200 | 800 | +600 | OK | Varios cuadros votados (silueta en las franjas de medida + marcador ArUco) en cada estacion, antes de que la cinta de vasos arranque. |
| La tapa cae y la camara la confirma en la misma pausa | 680 | 800 | +120 | OK | El escape suelta la tapa, cae por gravedad y la camara ve que quedo sobre el vaso. |
| La cortina reacciona a tiempo | 119 | 200 | +81 | OK | Lecturas votadas del VL53L0X + aviso por serial, antes de que baje la prensa o se mueva el empujador. |

Si al medir un tiempo real algún chequeo queda en **NO CABE**, las salidas son: alargar la pausa (`pausa_casilla_monedas`, baja la producción), un servo más rápido, o bajar `lecturas_por_decision`.
