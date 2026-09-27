<!-- Generado por `python -m app.documentos`. No editar a mano. -->


# Sensores del proyecto

Numerados igual que en el visor 3D (pestaña Sensores). Qué lo activa, qué recibe y entrega, qué mensaje manda al PC, cómo se replica y cómo se simula.

| # | Sensor | Subsistema | Modelo propuesto |
|---|---|---|---|
| 1 | [Infrarrojo de presencia](#1-infrarrojo-de-presencia) | cinta de monedas | FC-51 (infrarrojo reflectivo, alcance ajustable) a 5 cm de la cinta |
| 2 | [Sensor capacitivo](#2-sensor-capacitivo) | cinta de monedas | LJC18A3-H-Z/BX (NPN, 5-40 V) |
| 3 | [Sensor inductivo](#3-sensor-inductivo) | cinta de monedas | LJ18A3-8-Z/BX (NPN, M18, 8 mm) |
| 4 | [Cámara cenital](#4-cámara-cenital) | cinta de monedas | Webcam USB 1080p + anillo de luz difusa |
| 5 | [Sensor del interior del vaso](#5-sensor-del-interior-del-vaso) | cinta de vasos | VL53L0X (el mismo de la cortina; otra dirección I2C con su pin XSHUT) |
| 6 | [Sensor Hall del carrusel](#6-sensor-hall-del-carrusel) | cinta de vasos | A3144 (Hall digital, módulo KY-003) + imán de neodimio 6 x 3 mm |
| 7 | [Cámara de vasos (silueta, ArUco y tapa)](#7-cámara-de-vasos-silueta-aruco-y-tapa) | cinta de vasos | Webcam USB 720p + panel LED difuso detrás de la cinta + OpenCV (silueta y cv2.aruco 4x4_50) |
| 8 | [Cortina de seguridad](#8-cortina-de-seguridad) | cinta de vasos | 1 × VL53L0X (tiempo de vuelo láser, I2C; otra dirección que el del interior, con su pin XSHUT) |
| 9 | [Arreglo de 5 infrarrojos de línea](#9-arreglo-de-5-infrarrojos-de-línea) | carro | 5 × TCRT5000 (módulo de 5 canales) |
| 10 | [Ultrasónico frontal (respaldo)](#10-ultrasónico-frontal-respaldo) | carro | HC-SR04 |
| 11 | [Encoders de las ruedas](#11-encoders-de-las-ruedas) | carro | Encoder óptico de ranura (disco de 20 ranuras) |
| 12 | [Infrarrojo de la cuna de carga](#12-infrarrojo-de-la-cuna-de-carga) | carro | TCRT5000 o FC-51 |
| 13 | [Láser de distancia frontal](#13-láser-de-distancia-frontal) | carro | VL53L0X (el mismo de la cortina) |

## 1. Infrarrojo de presencia

**Subsistema:** cinta de monedas · **Dónde:** E1 · Presencia · **Modelo propuesto:** FC-51 (infrarrojo reflectivo, alcance ajustable) a 5 cm de la cinta

- **Qué lo activa:** Luz infrarroja que rebota en el elemento. La cinta es negra mate y casi no refleja, así que solo hay rebote fuerte si hay algo encima.
- **Recibe:** Luz IR reflejada (sin elemento: casi nada; con elemento: mucha).
- **Entrega:** Digital: 1 = casilla ocupada, 0 = vacía (salida del comparador LM393).
- **Rango:** FC-51: 2-30 cm, ajustable; va a 5 cm de la cinta (un TCRT5000 solo ve hasta ~15 mm: tendria que ir tan bajo que los bloques altos lo golpearian) · **Respuesta:** < 1 ms (comparador LM393)
- **Error típico:** Falsos negativos con piezas muy oscuras o con acabado espejo que desvian el haz; falsos positivos con sol directo o flash sobre la cinta.
- **Cómo mitigarlo:** Capuchon que tape la luz ambiente en E1; ajustar el potenciometro del LM393 con la cinta vacia; voto de 3 lecturas; ademas E2 respalda a E1 (presencia recuperada).
- **Conexión:** Salida digital D0 del modulo a una entrada del ESP32 fijo (alimentar el modulo a 3,3 V).
- **Cómo se simula:** rayTest vertical de 5 cm hacia la cinta; bloqueado si golpea algo que no sea la cinta.
- **Pasos:** [1. Carga del elemento y estación 1 (presencia)](paso-a-paso.md#1-carga-del-elemento-y-estación-1-presencia)

```json
{"t":"evt","src":"e1","ev":"presencia","casilla":17,"ocupada":true}
```

## 2. Sensor capacitivo

**Subsistema:** cinta de monedas · **Dónde:** E2 · Material (montado BAJO la cinta, en la casilla E1) · **Modelo propuesto:** LJC18A3-H-Z/BX (NPN, 5-40 V)

- **Qué lo activa:** Cualquier objeto cerca cambia la capacitancia de su placa (plástico, metal, madera...). Va debajo de la cinta, mirando hacia arriba, y lee la pieza a través de la banda (2 mm); la banda y los separadores siempre están iguales en cada pausa, así que se calibra con ellos puestos (quedan como fondo).
- **Recibe:** Presencia de cualquier material a ~2 mm sobre su cara (a través de la banda).
- **Entrega:** Digital: 1 si hay CUALQUIER elemento.
- **Rango:** 1-10 mm, ajustable con el tornillo de sensibilidad · **Respuesta:** ~5 ms (conmuta a ~100 Hz)
- **Error típico:** Humedad o polvo en la cara activa dan falsos positivos; piezas muy pequenas y delgadas pueden no alcanzar el umbral (falso negativo).
- **Cómo mitigarlo:** Montarlo a 3-5 mm de la trayectoria; calibrar con el boton de plastico mas pequeno; limpiar la cara; voto de 3 lecturas.
- **Conexión:** Salida NPN alimentada a 6-36 V: pasar por optoacoplador (PC817) o divisor a 3,3 V. NUNCA directo al ESP32.
- **Cómo se simula:** Consulta si hay un cuerpo activo en la casilla E1 (cualquiera); la lectura viaja en el registro de la casilla y se usa en E2.
- **Pasos:** [2. Estación 2 (material)](paso-a-paso.md#2-estación-2-material)

```json
{"t":"evt","src":"e2","ev":"material","capacitivo":true,"inductivo":false}
```

## 3. Sensor inductivo

**Subsistema:** cinta de monedas · **Dónde:** E2 · Material (BAJO la cinta, en la casilla E2) · **Modelo propuesto:** LJ18A3-8-Z/BX (NPN, M18, 8 mm)

- **Qué lo activa:** Un campo magnético oscilante induce corrientes de Foucault solo en metales. Va debajo de la cinta, centrado bajo la casilla, mirando hacia arriba a través de la banda.
- **Recibe:** Metal a ~2 mm sobre su cara (a través de la banda de 2 mm).
- **Entrega:** Digital: 1 solo si el elemento es metálico. Junto con el capacitivo: cap=1, ind=0 → no metálico; cap=1, ind=1 → metal.
- **Rango:** 8 mm nominal en acero (placa patron de 24 x 24 mm); una moneda de 17-27 mm centrada da ~70-80 % de eso, y en bronce, laton y cuproniquel ~40-60 % mas: ~2,2-4,8 mm, contra 2 mm de banda. Por eso M18 de 8 mm y no el M12 de 4 mm (a traves de la banda no alcanzaba con las no ferrosas) · **Respuesta:** ~2 ms (conmuta a ~500 Hz)
- **Error típico:** Las monedas NO ferrosas (casi todas las antiguas y muy antiguas) se detectan a menos distancia que el acero: si la moneda pasa lejos, falso negativo y se iria como no metalica.
- **Cómo mitigarlo:** Centrado bajo la casilla (descentrado pierde la mitad del alcance); inserto IMPRESO en la bancada alrededor de la cara (es no enrasable: nada de metal a menos de ~2 cm); probar con cada familia, sobre todo las de bronce; voto de 3 lecturas; si el inductivo ve metal, manda sobre el capacitivo.
- **Conexión:** Salida NPN a 6-36 V: optoacoplador o divisor a 3,3 V. NUNCA directo al ESP32.
- **Cómo se simula:** Consulta la bandera `metal` del cuerpo que está en E2.
- **Pasos:** [2. Estación 2 (material)](paso-a-paso.md#2-estación-2-material)

```json
{"t":"evt","src":"e2","ev":"material","capacitivo":true,"inductivo":true}
```

## 4. Cámara cenital

**Subsistema:** cinta de monedas · **Dónde:** E5 · Visión · **Modelo propuesto:** Webcam USB 1080p + anillo de luz difusa

- **Qué lo activa:** Imagen de la moneda sobre la cinta negra (fondo de contraste). En la misma imagen se ven los separadores de la casilla: con eso se mide si la cinta quedó en su lugar (reemplaza al sensor de ranura, grupo 2026-09-25).
- **Recibe:** Imagen de la casilla quieta bajo la cámara.
- **Entrega:** En el PC: diámetro (mm), circularidad, contornos internos, clase y confianza; y cuántos mm quedó corrida la cinta (si pasa del margen, se corrige con micropasos en la misma pausa).
- **Rango:** A 15 cm de la cinta (webcam con AUTOENFOQUE: las de foco fijo no enfocan tan cerca): campo de ~170 x 100 mm, 1 px ~ 0,1 mm · **Respuesta:** ~250 ms (captura + segmentacion + clasificador en la CPU del portatil)
- **Error típico:** Diametro +-0,08 mm (calibracion de escala y borde difuso); circularidad +-0,01; error de clase: sale de la matriz de confusion del modelo entrenado (fase 5); reflejos del anillo de luz en monedas brillantes.
- **Cómo mitigarlo:** Anillo de luz difusa y cinta negra mate; calibrar la escala con una moneda patron medida con calibrador; umbral de confianza 0,85; regla de coherencia diametro-clase.
- **Conexión:** USB directo al PC (no pasa por el ESP32).
- **Cómo se simula:** Modo oráculo: geometría real del cuerpo + ruido de clasificación (fase 5: render real).
- **Pasos:** [1. Carga del elemento y estación 1 (presencia)](paso-a-paso.md#1-carga-del-elemento-y-estación-1-presencia), [3. Estación 3 (visión, dos fotos)](paso-a-paso.md#3-estación-3-visión-dos-fotos)

```json
{"casilla":17,"diametro_mm":23.68,"circularidad":0.981,"clase":"500_nueva","confianza":0.94}
```

## 5. Sensor del interior del vaso

**Subsistema:** cinta de vasos · **Dónde:** Verificación (arriba, mirando hacia adentro del vaso) · **Modelo propuesto:** VL53L0X (el mismo de la cortina; otra dirección I2C con su pin XSHUT)

- **Qué lo activa:** Mide la distancia hacia abajo, al fondo del vaso. Los vasos son opacos (la cámara no ve adentro): si algo está más arriba que el fondo de un vaso vacío, el vaso trae algo adentro.
- **Recibe:** Distancia desde el sensor hasta lo primero que hay dentro del vaso.
- **Entrega:** Digital (en el PC): 1 = el vaso trae algo → no entra (cada vaso arranca de cero).
- **Rango:** 3 cm a ~1,2 m; a 1,5 cm sobre la boca el fondo queda a ~10,5 cm y el cono de 25 grados llega con ~6 mm de margen a la pared (aguanta ~3 grados de torcido: collar de centrado) · **Respuesta:** ~33 ms por medida; se votan 3
- **Error típico:** ±3 % de la distancia (~4 mm a 12 cm): un objeto de pocos milímetros (una sola moneda acostada) puede no verse; reflejos en el fondo liso.
- **Cómo mitigarlo:** Margen de 10 mm sobre el fondo del vaso vacío; fondo del vaso mate; sensor centrado sobre la boca y fijo al pórtico; 3 medidas con voto.
- **Conexión:** I2C (SDA/SCL) al ESP32 fijo, 3,3 V; XSHUT a un pin para cambiarle la dirección.
- **Cómo se simula:** El vaso simulado tiene o no un objeto adentro, con su error (errores_sensores.sensor_interior).
- **Pasos:** [6. Verificación del vaso (antes de llenar)](paso-a-paso.md#6-verificación-del-vaso-antes-de-llenar)

```json
{"t":"evt","src":"vasos","ev":"verificacion","vaso":4,"objeto_adentro":false}
```

## 6. Sensor Hall del carrusel

**Subsistema:** cinta de vasos · **Dónde:** Borde del carrusel del almacén · **Modelo propuesto:** A3144 (Hall digital, módulo KY-003) + imán de neodimio 6 x 3 mm

- **Qué lo activa:** El imán, en una cavidad del disco del carrusel (entre dos tubos), pasa por debajo del sensor una vez por vuelta, con 4 mm de aire entre los dos.
- **Recibe:** Campo magnético del imán.
- **Entrega:** Digital: 1 = el carrusel está en su referencia. El motor paso a paso no sabe dónde está al encender: gira hasta ver el imán (homing) y desde ahí cuenta pasos.
- **Rango:** Con 4 mm de aire un iman N35 de 6 x 3 mm da ~70 mT en la cara; el A3144 conmuta con ~10-35 mT: sobra margen (hasta ~7-8 mm) · **Respuesta:** < 1 ms
- **Error típico:** Casi ninguno: no le afecta la luz ni el polvo. Solo falla si el imán se despega o queda lejos.
- **Cómo mitigarlo:** Imán pegado en una cavidad impresa; homing lento; al terminar cada vuelta completa, comprobar que el imán aparece donde se esperaba.
- **Conexión:** Salida digital (colector abierto con pull-up) a una entrada del ESP32 fijo, 3,3-5 V.
- **Cómo se simula:** Siempre encuentra la referencia (el carrusel simulado no pierde pasos).
- **Pasos:** [5. Almacén tipo revólver (por denominación)](paso-a-paso.md#5-almacén-tipo-revólver-por-denominación)

```json
{"t":"evt","src":"almacen","ev":"referencia","ok":true}
```

## 7. Cámara de vasos (silueta, ArUco y tapa)

**Subsistema:** cinta de vasos · **Dónde:** Verificación, llenado, tapa y prensa (una sola vista) · **Modelo propuesto:** Webcam USB 720p + panel LED difuso detrás de la cinta + OpenCV (silueta y cv2.aruco 4x4_50)

- **Qué lo activa:** A contraluz, lo que hay en cada casilla se ve como una silueta oscura sobre el panel blanco. Cada vaso personalizado (opaco) lleva una CINTA impresa alrededor con el mismo marcador ArUco repetido 6 veces: siempre hay uno de frente, gire como gire el vaso. La tapa naranja se ve como una franja sobre la boca. Con los separadores a contraluz mide también si la cinta quedó en su lugar (reemplaza al sensor de ranura). Reemplaza a las 6 barreras IR y a los 2 sensores de presencia de vasos (grupo, 2026-09-25). Lo que hay ADENTRO de un vaso opaco no lo ve: eso lo mide el sensor del interior del vaso.
- **Recibe:** Imagen de las 4 primeras casillas de la cinta de vasos (verificación, llenado, tapa, prensa).
- **Entrega:** Por casilla: presencia; silueta en la franja de media altura y en la franja justo por encima del borde ("barreras virtuales": media ocupada y borde libre = vaso); número del marcador (si cambia entre verificación y llenado, tapa o prensa, el vaso fue cambiado por otro igual); en tapa y prensa, si la tapa está puesta; y cuánto quedó corrida la cinta.
- **Rango:** Las 3 casillas (~24 cm de ancho) a ~22 cm de la cámara; marcador de 20 x 20 mm legible aunque esté algo inclinado; 1 px ~ 0,2 mm · **Respuesta:** ~60 ms por cuadro (captura + silueta + detectMarkers en la CPU del portátil); se votan 3 cuadros
- **Error típico:** Silueta: sombras o reflejos en el borde del vaso (casi desaparecen a contraluz). Marcador: reflejo o tapado → no lo lee; casi nunca lee un número equivocado (el diccionario ArUco corrige errores de bits). Si se cae el PC, no hay verificación de vasos.
- **Cómo mitigarlo:** Panel LED difuso detrás (contraluz: la silueta no depende del color ni de la luz del salón); franjas con margen de ±5 mm; marcador mate; voto de 3 cuadros; si no lee el marcador decide la silueta (no se bloquea la línea); sin PC la cinta de vasos no avanza (falla segura: nada se llena sin verificar).
- **Conexión:** USB directo al PC (segunda webcam; no pasa por el ESP32).
- **Cómo se simula:** Franjas: rayTest horizontal a 45 mm y a 94,5 mm en cada casilla. Marcador y tapa: lo que tiene el vaso simulado, con camara_vasos.no_lee y no_ve_tapa por cuadro.
- **Pasos:** [6. Verificación del vaso (antes de llenar)](paso-a-paso.md#6-verificación-del-vaso-antes-de-llenar), [7. Llenado por lotes de una sola denominación](paso-a-paso.md#7-llenado-por-lotes-de-una-sola-denominación), [8. Estación de tapa](paso-a-paso.md#8-estación-de-tapa), [9. Prensa](paso-a-paso.md#9-prensa), [10. Descarga de vasos](paso-a-paso.md#10-descarga-de-vasos)

```json
{"t":"evt","src":"vasos","ev":"verificacion","vaso":4,"media":true,"borde":false,"marcador":104}
```

## 8. Cortina de seguridad

**Subsistema:** cinta de vasos · **Dónde:** Tapa → Prensa, lado del operador · **Modelo propuesto:** 1 × VL53L0X (tiempo de vuelo láser, I2C; otra dirección que el del interior, con su pin XSHUT)

- **Qué lo activa:** Un solo sensor a media altura del vaso (65 mm sobre la cinta), en el extremo de la prensa mirando hacia la tapa, del lado del operador. Mide en un cono de ~25°, no en un rayo: con el eje a 85 mm del eje de la cinta el cono no toca vasos, tapa, prensa ni cinta (aguanta ~8° de sensor torcido). Una mano que entra a la zona a media altura cruza el cono. Una que pase por encima puede evadirlo: eso lo cubre la cámara de vasos, que revisa en cada tick que no falte ningún vaso.
- **Recibe:** Distancia al primer objeto dentro del cono.
- **Entrega:** Distancia en mm; si es menor que el largo de la zona (~140 mm) → algo invadió (una mano). Más lejos o fuera de rango: no cuenta.
- **Rango:** 3 cm a ~1,2 m en modo por defecto · **Respuesta:** ~33 ms por medida
- **Error típico:** +-3 % a corta distancia; las superficies negras reducen el alcance; reflejos pueden dar lecturas cortas (falso positivo).
- **Cómo mitigarlo:** Ventana de distancia (solo cuenta lo que esté a menos del largo de la zona); voto de 3 medidas (~100 ms); eje a 85 mm de la cinta para que el cono no toque los vasos.
- **Conexión:** I2C (SDA/SCL) al ESP32 fijo, 3,3 V.
- **Cómo se simula:** Cono real: 19 rayTest repartidos en un cono de 25° de prensa a tapa, a 65 mm de altura; activa si cualquiera ve algo dentro de la ventana de distancia.
- **Pasos:** [11. Cortina de seguridad](paso-a-paso.md#11-cortina-de-seguridad)

```json
{"t":"evt","src":"seguridad","ev":"cortina","activa":true}
```

## 9. Arreglo de 5 infrarrojos de línea

**Subsistema:** carro · **Dónde:** Bajo el frente del carro · **Modelo propuesto:** 5 × TCRT5000 (módulo de 5 canales)

- **Qué lo activa:** La línea negra absorbe el IR; el piso claro lo refleja.
- **Recibe:** Reflectancia bajo cada uno de los 5 sensores.
- **Entrega:** 5 bits (p. ej. 00100 = centrado, 01100 = línea un poco a la izquierda).
- **Rango:** 2-10 mm sobre el piso · **Respuesta:** < 1 ms
- **Error típico:** Cambios de luz y de altura del chasis; brillo de la cinta aislante.
- **Cómo mitigarlo:** Montar a 3-5 mm del piso con falda contra la luz; calibrar blanco y negro al arrancar.
- **Conexión:** 5 entradas (digitales o ADC) del ESP32 del carro.
- **Cómo se simula:** Distancia de cada sensor a la línea central de la pista (y a las franjas negras de meta y de giro), con lecturas cambiadas a veces (errores_sensores.carro.error_linea). El control decide cada bit por mayoría de 3 lecturas y, para volver a la línea, exige 4 seguidas.
- **Pasos:** [14. Ruta del carro con tres obstáculos (ida y vuelta sola)](paso-a-paso.md#14-ruta-del-carro-con-tres-obstáculos-ida-y-vuelta-sola), [16. Asistente (DeepSeek) y órdenes al carro](paso-a-paso.md#16-asistente-deepseek-y-órdenes-al-carro)

```json
{"t":"evt","src":"carro","ev":"linea","bits":"00100"}
```

## 10. Ultrasónico frontal (respaldo)

**Subsistema:** carro · **Dónde:** Frente del carro · **Modelo propuesto:** HC-SR04

- **Qué lo activa:** Pulso de 40 kHz que rebota en el obstáculo; se mide el tiempo de ida y vuelta. Ve lejos (4 m) pero mide lento (~60 ms entre disparos). Respaldo del láser: no le afectan las superficies negras o brillantes ni el sol.
- **Recibe:** Eco del muro (o nada si no hay obstáculo en rango).
- **Entrega:** Distancia en mm; a menos de 500 mm frena, a menos de 200 mm (2 mediciones seguidas) esquiva.
- **Rango:** 2-400 cm, resolucion ~3 mm, apertura ~15 grados · **Respuesta:** ~25 ms por medida + ~60 ms recomendados entre disparos
- **Error típico:** +-3 mm tipico; ecos perdidos en superficies inclinadas; lecturas falsas por ecos de otros objetos.
- **Cómo mitigarlo:** Respaldo del laser: 2 mediciones seguidas; disparos cada 60 ms para que no se mezclen ecos.
- **Conexión:** TRIG a una salida; ECHO (5 V) por divisor a 3,3 V al ESP32 del carro.
- **Cómo se simula:** Abanico de 5 rayTest en ±7,5° a la altura real, una medición cada 60 ms, con ruido.
- **Pasos:** [14. Ruta del carro con tres obstáculos (ida y vuelta sola)](paso-a-paso.md#14-ruta-del-carro-con-tres-obstáculos-ida-y-vuelta-sola), [16. Asistente (DeepSeek) y órdenes al carro](paso-a-paso.md#16-asistente-deepseek-y-órdenes-al-carro)

```json
{"t":"evt","src":"carro","ev":"obstaculo","sensor":"ultrasonico","distancia_mm":182}
```

## 11. Encoders de las ruedas

**Subsistema:** carro · **Dónde:** Ruedas motrices · **Modelo propuesto:** Encoder óptico de ranura (disco de 20 ranuras)

- **Qué lo activa:** Cada ranura que pasa corta el haz: pulsos proporcionales al giro de la rueda.
- **Recibe:** Giro de cada rueda.
- **Entrega:** Pulsos → odometría (distancia y giro).
- **Rango:** 20 ranuras por vuelta: con rueda de 65 mm, ~10 mm de avance por pulso · **Respuesta:** Por interrupcion
- **Error típico:** Deslizamiento de las ruedas; rebotes del sensor de ranura.
- **Cómo mitigarlo:** Interrupciones con antirrebote; corregir la odometria con la linea.
- **Conexión:** 2 entradas con interrupcion del ESP32 del carro.
- **Cómo se simula:** Pulsos enteros del giro REAL de cada rueda en PyBullet (20 por vuelta, ~10 mm): si la rueda patina, cuenta de más. Llegar al muelle = dejan de contar contra el tope (con PWM bajo).
- **Pasos:** [14. Ruta del carro con tres obstáculos (ida y vuelta sola)](paso-a-paso.md#14-ruta-del-carro-con-tres-obstáculos-ida-y-vuelta-sola), [16. Asistente (DeepSeek) y órdenes al carro](paso-a-paso.md#16-asistente-deepseek-y-órdenes-al-carro)

```json
{"t":"tel","src":"carro","x":0.84,"y":-0.52,"rumbo":-1.57}
```

## 12. Infrarrojo de la cuna de carga

**Subsistema:** carro · **Dónde:** Cuna (rieles) del carro · **Modelo propuesto:** TCRT5000 o FC-51

- **Qué lo activa:** Antes de soltar confirma que la cuna está vacía; después, que el vaso soltado por el escape quedó en la cuna.
- **Recibe:** Luz IR reflejada por el vaso.
- **Entrega:** Digital: 1 = vaso cargado.
- **Rango:** TCRT5000: 2-15 mm · **Respuesta:** < 1 ms
- **Error típico:** Igual que el de presencia: vasos transparentes reflejan poco.
- **Cómo mitigarlo:** Apuntarlo al fondo opaco del vaso; voto de 3 lecturas.
- **Conexión:** Entrada digital del ESP32 del carro.
- **Cómo se simula:** La cuna tiene o no un vaso (lo pone el escape al soltar), más su error (errores_sensores.cuna). Se lee antes de soltar (tiene que estar vacía) y después (confirma la carga).
- **Pasos:** [13. Acople con el carro (ESP-NOW)](paso-a-paso.md#13-acople-con-el-carro-esp-now), [15. Telemetría, protocolo y 3D](paso-a-paso.md#15-telemetría-protocolo-y-3d)

```json
{"t":"evt","src":"carro","ev":"carga","vaso":4,"ok":true}
```

## 13. Láser de distancia frontal

**Subsistema:** carro · **Dónde:** Frente del carro, sobre el ultrasónico · **Modelo propuesto:** VL53L0X (el mismo de la cortina)

- **Qué lo activa:** Pulso de luz infrarroja láser: mide el tiempo que tarda en volver. Una medición cada 33 ms (el doble de rápido que el ultrasónico), hasta ~1,2 m, cono de ~25°.
- **Recibe:** Luz reflejada por lo que haya adelante.
- **Entrega:** Distancia en mm: a menos de 500 mm el carro baja a velocidad de maniobra; a menos de 200 mm en 3 mediciones seguidas se detiene, mira a los lados y esquiva.
- **Rango:** 3 cm a ~1,2 m (modo por defecto); cono de ~25 grados · **Respuesta:** ~33 ms por medida
- **Error típico:** +-3 % a corta distancia; superficies negras o muy brillantes y el sol directo acortan el alcance o dan lecturas falsas.
- **Cómo mitigarlo:** 3 mediciones seguidas para decidir; el ultrasonico de respaldo cubre lo que el laser no ve.
- **Conexión:** I2C (SDA/SCL) al ESP32 del carro, 3,3 V.
- **Cómo se simula:** Cono de 5 rayTest en ±12,5° a 7 cm del piso, una medición cada 33 ms, hasta 1,2 m, con ruido proporcional (errores_sensores.carro.ruido_tof).
- **Pasos:** [14. Ruta del carro con tres obstáculos (ida y vuelta sola)](paso-a-paso.md#14-ruta-del-carro-con-tres-obstáculos-ida-y-vuelta-sola), [16. Asistente (DeepSeek) y órdenes al carro](paso-a-paso.md#16-asistente-deepseek-y-órdenes-al-carro)

```json
{"t":"evt","src":"carro","ev":"obstaculo","sensor":"laser","distancia_mm":191}
```

Valores PROVISIONALES (hoja de datos): se miden como dice [replicacion.md](replicacion.md).
