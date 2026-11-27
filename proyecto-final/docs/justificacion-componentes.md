# Justificación de los componentes

Por qué se eligió cada componente de la planta y del carro, qué otras referencias existen en el mercado y por qué no se usaron, y cuánta corriente consume cada uno. Complementa la lista de materiales de [componentes.md](componentes.md) y los [13 sensores](sensores.md).

**De dónde salen las cifras.** Los números del proyecto (corriente de cada riel, picos, pares, márgenes, pines, precios) vienen de [electrica.md](electrica.md), [peso.md](peso.md), [conexiones.md](conexiones.md) y [costos.md](costos.md), y se citan entre comillas latinas («docs/…»). Los valores de las referencias alternativas son los típicos de su hoja de datos y se marcan así; cuando un dato no se conoce con seguridad, dice «medir en el montaje». Si el repositorio y una hoja de datos difieren, se usa el del repositorio y se anota. Cada cifra se revisó dos veces (redacción y verificación contra el repositorio y las hojas de datos).

Escrito a mano (2026-11-11): si cambia la lista de materiales o el modelo eléctrico, hay que revisarlo.

## Contenido

- [Actuadores](#actuadores)
- [Control y potencia](#control-y-potencia)
- [Sensores de la estación](#sensores-de-la-estación)
- [Carro](#carro)

## Actuadores

La planta tiene 9 actuadores de cuatro tipos: 2 motores paso a paso NEMA 17, 1 motor paso a paso 28BYJ-48, 4 servos SG90 y 2 servos MG996R. Cada modelo se eligió por dos cosas: el par que pide su carga y la corriente que puede dar el riel que lo alimenta. También contaron los pines libres del ESP32 fijo, que ya usa 19 de sus ~25 pines útiles («docs/costos.md»). Por eso los 6 servos van por un PCA9685 en I2C, que solo ocupa G21 y G22 («docs/conexiones.md»).

La tabla compara el par pedido con el disponible. El criterio del repo es que un motor alcanza si da al menos el doble de lo que se le pide («docs/peso.md»):

| Actuador | Par pedido (peor caso) | Par disponible | Margen | Fuente |
|---|---:|---:|---:|---|
| NEMA 17, cinta de monedas (10 monedas de 10 g) | 0,0115 N·m | 0,118 N·m | x10,2 | «docs/peso.md» |
| NEMA 17, cinta de vasos (5 vasos llenos de 133 g) | 0,0527 N·m | 0,118 N·m | x2,2 | «docs/peso.md» |
| MG996R, prensa (tapa más dura provisional: 50 N) | 0,350 N·m | 1,08 N·m a 6 V / 0,92 N·m a 4,8 V | x3,09 / x2,63 | «docs/peso.md» |
| MG996R, prensa (tope de diseño: 60 N, leva de 7 mm a 90°) | 0,420 N·m | 1,08 N·m a 6 V / 0,92 N·m a 4,8 V | x2,57 / x2,19 | «docs/peso.md» |
| MG996R, empujador (vaso lleno, manivela de 35 mm) | 0,0274 N·m | 1,08 N·m a 6 V | x39,4 | «docs/peso.md» |
| 28BYJ-48, carrusel | el repo no lo calcula | ~0,034 N·m (hoja de datos, típico) | medir en el montaje | — |
| SG90 (desvío, obturador, tapas, canaleta) | el repo no lo calcula | ~0,18 N·m a 4,8 V (hoja de datos, típico) | medir en el montaje | — |

### Motor de las cintas — NEMA 17 17HS4401 (x2)
**Para qué está:** mueve las dos cintas indexadas. La de monedas avanza una casilla de 40 mm en 0,6 s y la de vasos una de 80 mm en 1,0 s («docs/peso.md», «docs/componentes.md»). Después de cada avance la cinta se detiene para que actúen los sensores y la cámara.

**Por qué este modelo:** la cinta tiene que parar siempre en el mismo sitio. Un motor paso a paso lo consigue contando pasos, sin encoder. Si la banda patina, la cámara re-sincroniza la posición con los separadores («docs/bitacora.md», «docs/electrica.md»).
- **Par:** el caso que decide es la cinta de vasos, que pide 0,0527 N·m. Casi todo ese par (0,0488 N·m) es el roce de la banda contra la cama. El par disponible sale de 0,40 N·m de retención × (1,0 A del driver / 1,7 A nominal) × 0,50 = 0,118 N·m. El margen es x2,2, apenas por encima del criterio x2 («docs/peso.md»).
- **Corriente del driver:** el A4988 trabaja a 1,0 A por fase, no a los 1,7 A nominales del motor. Según el repo, 1,0 A es el límite que da la hoja del A4988 sin disipador ni aire forzado. Aun así la caja lleva un ventilador de 5 V, porque el aire del interior cerrado sube unos 8 °C («docs/electrica.md»).
- **Pines:** cada motor usa 2 pines, STEP y DIR, y los dos comparten ENABLE. La cinta de monedas va en G25/G26, la de vasos en G27/G14 y el ENABLE común en G13 («docs/conexiones.md»).
- **Precio:** 59.000 COP cada uno en Mercado Libre, contra 79.900 COP en Electronilab por el mismo modelo («docs/costos.md»).
- **Estado:** «docs/componentes.md» todavía lo marca como PROVISIONAL.

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| 17HS4401 (elegido) | NEMA 17, cuerpo de ~40 mm, 1,8° por paso, retención 0,40 N·m, 0,28 kg («docs/peso.md») | 1,7 A/fase nominal, 1,5 Ω/fase; en el proyecto, 1,0 A/fase con A4988 a 12 V («docs/electrica.md») | Sí: da x2,2 en el peor caso aun con la corriente bajada a 1,0 A. Es el NEMA 17 más común y barato del mercado local. |
| 17HS3401 | NEMA 17 corto (~34 mm), retención ~0,28-0,32 N·m (hoja de datos, típico) | ~1,3 A/fase | No: con la misma reducción de corriente quedaría por debajo de x2 en la cinta de vasos. |
| 17HS8401 | NEMA 17 largo (~48 mm), retención ~0,5 N·m (hoja de datos, típico) | ~1,7-1,8 A/fase | No hace falta: el 17HS4401 ya alcanza. Pesa más y a 1,0 A/fase tampoco daría todo su par. |
| NEMA 23 | Retención ≥1 N·m (hoja de datos, típico) | 2-3 A/fase | No: está sobredimensionado. Necesita un driver de más corriente que el A4988 y una fuente más grande. |
| Motorreductor DC con encoder | Mucho par a bajo costo | Depende del modelo (6-12 V) | No: para parar en la casilla necesita encoder, lazo cerrado y puente H. El paso a paso indexa en lazo abierto con 2 pines. |

**Consumo:** por motor, en el riel de 12 V: 190 mA en reposo, 300 mA típico y 450 mA de pico («docs/electrica.md»). Por cada hilo de bobina circulan 707 mA rms y hasta 1,00 A. El A4988 es un chopper, así que de los 12 V solo toma la potencia que se gasta, no 1 A por fase («docs/electrica.md»). Quieto consume casi lo mismo que andando, porque el A4988 mantiene la corriente plena mientras ENABLE está activo. El firmware suelta ENABLE (G13 en 1) cuando las dos cintas llevan 3000 ms quietas. El riel de 12 V completo promedia 1,38 A en el ciclo y tiene un pico de 2,93 A, sobre una fuente de 5 A («docs/electrica.md»).

### Motor del carrusel del almacén — 28BYJ-48 5 V + driver ULN2003 (x1)
**Para qué está:** gira el carrusel de 6 tubos. Pone bajo el punto de carga el tubo de cada moneda y, para soltar un lote, lleva ese tubo sobre el agujero de la placa fija. Un sensor Hall le sirve de referencia («docs/componentes.md», «docs/bitacora.md»).

**Por qué este modelo:**
- **Reemplazó 7 actuadores:** el diseño anterior tenía un servo selector y 6 servos de compuerta. El almacén tipo revólver se queda con 2 actuadores: este motor y el servo del obturador («docs/bitacora.md», «docs/componentes.md»).
- **Par y posición:** la reducción interna (~1:64) le da bastante par y resolución para posicionar un disco liviano sin engranajes extra. Solo necesita un acople rígido de 5 a 8 mm («docs/costos.md»).
- **Alimentación y pines:** funciona a 5 V desde el LM2596, que ya existe. El ULN2003 trae diodos de rueda libre y se maneja con 4 pines del ESP32: G32, G33, G23 y G4 («docs/conexiones.md»).
- **Precio:** 19.000 COP con el driver incluido («docs/costos.md»).
- **Desventaja aceptada:** es lento. A 500 Hz de medio paso tarda 4,22 s en media vuelta, y la cinta de monedas tiene que esperar al carrusel. El usuario decidió aceptar esa espera y no cambiar el motor («CONTEXTO-SESION.md», 2026-09-28).
- **Par sin calcular:** «docs/peso.md» no calcula el par que pide el carrusel. Hay que medirlo en el montaje.

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| 28BYJ-48 5 V + ULN2003 (elegido) | Unipolar, reducción ~1:64, ~4096 medios pasos por vuelta, par ~0,034 N·m (hoja de datos, típico), ~30 g | 5 V, 50 Ω por bobina, 0,1 A por bobina («docs/electrica.md») | Sí: es barato, preciso gracias a la reducción, usa el riel de 5 V y el driver viene en el kit. La lentitud (4,22 s por media vuelta) está aceptada. |
| 28BYJ-48 12 V | La misma mecánica | 12 V, bobinas de ~200 Ω, menos corriente (hoja de datos, típico) | No: es el mismo motor en otro riel. No gana velocidad, y el de 5 V ya comparte el LM2596. |
| NEMA 17 + A4988 | Más par y más velocidad | 12 V, 1-1,7 A/fase | No: cuesta 59.000 + 8.000 COP («docs/costos.md») y carga más el riel de 12 V. Además, el usuario decidió no cambiar el motor del carrusel. |
| Servo de giro continuo (SG90 360°) | Barato, 3 hilos | 4,8-6 V | No: no sabe en qué ángulo está. Para alinear un tubo con el agujero haría falta otro sensor. |
| Servo de 180° con selector (diseño anterior) | Posición absoluta | 4,8-6 V | No: el diseño anterior necesitaba 7 servos en total, y el selector no era fiable porque la moneda llega con velocidad («docs/bitacora.md»). |

**Consumo:** en el riel de 5 V de la caja (LM2596): 0 mA en reposo, 150 mA típico y 240 mA de pico («docs/electrica.md»). El pico corresponde a 2 bobinas encendidas a la vez en medio paso, más los LEDs del ULN2003. Cada bobina lleva 50 mA de promedio y 100 mA de pico. Las entradas del ULN2003 toman ~0,7 mA cada una desde los 3,3 V del ESP32. El riel de 5 V completo llega a 964 mA de pico, sobre 3 A («docs/electrica.md»).

### Servos pequeños — SG90 (x4: desvío, obturador, escape de tapas, escape de la canaleta)
**Para qué está:** los cuatro hacen movimientos cortos y livianos («docs/componentes.md»):
- **Desvío (E4):** es la única salida de rechazo de la cinta de monedas. En reposo manda todo a la bandeja de rechazo, a prueba de fallas.
- **Obturador del almacén:** con una palanca a 90° corre 30 mm una corredera.
- **Escape de tapas:** suelta una tapa del tubo vertical sobre el vaso.
- **Escape de la canaleta:** deja pasar un solo vaso hacia la cuna del carro.

**Por qué este modelo:**
- **Carga liviana:** todos mueven poco peso: una aleta, una corredera, una tapa de 8 g y un balancín («docs/peso.md»). Un servo sabe en qué ángulo quedó, así que no hace falta sensor de posición ni puente H.
- **Preferencia del usuario:** el SG90 está en su lista de componentes «baratos y conocidos» («CONTEXTO-SESION.md»).
- **Peso y precio:** pesa 9 g («docs/peso.md») y cuesta 11.000 COP («docs/costos.md»).
- **Conexión:** van por los canales PWM0, PWM1, PWM2 y PWM5 del PCA9685, con 50 Hz y pulsos de 0,5-2,5 ms («docs/electrica.md»). Conectarlos directo al ESP32 no cabe por pines («docs/costos.md»).
- **Par sin calcular:** «docs/peso.md» no calcula el par de estos cuatro mecanismos. Hay que medirlo en el montaje, sobre todo en el obturador, por el roce de la corredera.

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| SG90 (elegido) | Engranajes plásticos, ~0,18 N·m (1,8 kg·cm) a 4,8 V, 9 g | 4,8-6 V; en el repo, ~6 mA quieto, ~250 mA moviéndose y ~700 mA trabado («docs/electrica.md») | Sí: alcanza para cargas de pocos gramos, y es el más barato y el más conocido. |
| MG90S | Mismo tamaño, engranajes metálicos, ~0,2 N·m a 4,8 V, ~13 g (hoja de datos, típico) | 4,8-6 V, consumo parecido al SG90 | Es el reemplazo directo si un SG90 pierde dientes, por ejemplo en el obturador. Está en la lista de preferidos del usuario, pero hoy no hace falta. |
| MG996R | ~1 N·m, 55 g | Hasta 2,5 A trabado a 6 V | No: está sobredimensionado. Cuatro más subirían el pico del riel de 6 V, que ya llega al 69 %. |
| Solenoide push-pull de 5/12 V | Movimiento lineal todo o nada | ~0,3-1 A mientras está activado (hoja de datos, típico; depende del modelo) | No: necesita transistor y diodo, consume mientras sostiene y no tiene posiciones intermedias. |

**Consumo:** en el riel de 6 V de los servos (XL4015 por la bornera V+ del PCA9685, con 1000 µF): 6 mA en reposo, 250 mA típico y 700 mA de pico durante ~30 ms al arrancar («docs/electrica.md»). Para la corriente trabada el repo usa 700 mA y algunas hojas de datos dan ~650 mA; se toma el valor del repo. Promedio de cada canal en el ciclo: desvío 37 mA, obturador 11 mA, escape de tapas 21 mA y canaleta 9 mA. El pico de cada uno es 700 mA («docs/electrica.md»).

### Servos de potencia — MG996R (x2: prensa y empujador)
**Para qué está:** («docs/componentes.md»)
- **Prensa:** gira una leva excéntrica de 7 mm de 0 a 180° y vuelve a 0°. El pistón baja 14 mm y el plato aprieta 0,5 mm el ala de la tapa, que cierra a presión (snap-fit).
- **Empujador:** con una manivela de ~70 mm de carrera pasa el vaso tapado a la canaleta de entrega.

**Por qué este modelo:**
- **Prensa (decide el modelo):** la tapa pide 30-50 N, valor PROVISIONAL, y el tope de diseño es 60 N. A 90° de la leva eso son 0,42 N·m, el 39 % del par de bloqueo a 6 V. El MG996R se bloquea en 1,08 N·m a 6 V y en 0,92 N·m a 4,8 V. Los márgenes son x2,57 y x2,19, así que cumple el x2 aunque el riel baje a 4,8 V («docs/peso.md»).
  - **Objetivo de fuerza rebajado:** el catálogo pedía antes «≥150 N». El MG996R no los sostiene en toda la carrera con esta leva, y la tapa tampoco los necesita, así que el objetivo bajó a 60 N («docs/peso.md», «docs/historial-pedidos.md», «docs/bitacora.md»).
  - **Sin sensor de posición:** como es servo, sabe en qué ángulo quedó. No hace falta sensor de posición ni puente H.
- **Empujador:** pide solo 0,0274 N·m, un margen de x39,4. Por cálculo propio, un SG90 (~0,18 N·m) también superaría el x2. El repo eligió MG996R «porque el vaso lleno pesa más» («docs/componentes.md»). Así los dos servos de potencia son iguales y comparten repuesto.
- **Precio:** 37.000 COP cada uno («docs/costos.md»).
- **Arranques separados:** el firmware nunca arranca la prensa y el empujador a la vez (regla EXCLUYENTES en `firmware/fijo/estacion.py`). Gracias a eso basta un XL4015 de 5 A en vez de un XL4016 de 9 A («docs/costos.md», «docs/electrica.md»).

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| MG996R (elegido) | Engranajes metálicos, bloqueo 0,92 N·m a 4,8 V y 1,08 N·m a 6 V («docs/peso.md»), ~55 g | 4,8-7,2 V; en el repo, ~10 mA quieto, 0,5-0,9 A moviéndose y 2,5 A trabado a 6 V («docs/electrica.md») | Sí: da más de x2 en la prensa a 60 N, incluso a 4,8 V. Es barato y conocido. |
| MG995 | Antecesor del MG996R, mismo tamaño y par parecido | Similar | No: es la versión anterior del mismo servo y tiene fama de vibrar en reposo. No ofrece ninguna ventaja. |
| DS3218 | ~20 kg·cm (~2 N·m), ~60 g (hoja de datos, típico) | Hasta 6,8 V; corriente trabado mayor que la del MG996R (medir en el montaje) | No hace falta: le sobra par, y su arranque cargaría más el XL4015 de 5 A. |
| MG90S | ~0,2 N·m, ~13 g (hoja de datos, típico) | 4,8-6 V | No para la prensa, que pide 0,42 N·m. Para el empujador sí alcanzaría, pero el repo prefirió el MG996R. |
| Actuador lineal / solenoide de 12 V | Empuje lineal directo | 12 V, ~1 A o más según el modelo | No: necesita puente H o relé y un final de carrera. El servo da posición y fuerza con un solo canal del PCA9685. |

**Consumo:** en el riel de 6 V de los servos: 10 mA en reposo, 900 mA típico y 2,50 A de pico trabado («docs/electrica.md»). Promedio en el ciclo: prensa 397 mA y empujador 286 mA. La prensa marca el pico del riel de 6 V mientras aprieta la tapa: 3,47 A sobre 5 A, es decir el 69 %. El condensador de 1000 µF limita a ~0,25 V la caída de tensión cuando arranca con 2,5 A («docs/electrica.md»).

Hay dos peores casos que no ocurren en el ciclo normal («docs/electrica.md»):
- Prensa trabada más los 4 SG90 trabados en los mismos 30 ms: 5,30 A.
- Los 6 servos trabados a la vez: 7,80 A.

En los dos casos el XL4015 limita la corriente a 4,5 A. El riel se hunde y los servos se frenan, pero no se quema nada.

---

Quedan por medir en el montaje: el par real del carrusel y de los cuatro SG90, la corriente trabada de cada servo con su carga real, la fuerza de la tapa y la Vref de los A4988 («docs/electrica.md»). Los valores típicos de las alternativas (17HS3401, 17HS8401, NEMA 23, 28BYJ-48 de 12 V, DS3218, MG90S y solenoides) son valores conocidos de hoja de datos y no se compararon con una hoja concreta.

## Control y potencia

En esta sección se explica por qué se eligió cada pieza de la caja de control y de la alimentación de la estación fija, y qué otras opciones hay en el mercado. Los requisitos y las cifras salen de los documentos del repositorio. La fuente principal es «docs/electrica.md», que simula el ciclo eléctrico con un paso de 10 ms. Todas sus corrientes son provisionales hasta medirlas en el montaje. Los precios son los de «docs/costos.md», en pesos colombianos. Los datos que no están en el repositorio se marcan como «hoja de datos, típico».

### Microcontrolador de la estación — ESP32 DevKit V1 de 38 pines, CH9102F (x1)
**Para qué está:** lee los sensores discretos y mueve los dos paso a paso, los servos (a través del PCA9685) y el carrusel. Se comunica con el PC por USB y con el carro por ESP-NOW. No decide la clasificación: de eso se encarga la visión en el PC («docs/especificacion.md», §15).

**Por qué este modelo:**
- **Radio para ESP-NOW.** Es el requisito que decide la elección. El enlace con el carro funciona sin router y sin ocupar el Wi-Fi del PC.
- **Mismo ecosistema que el carro.** El carro también usa un ESP32 DevKit, y el firmware de las dos placas está en MicroPython, el lenguaje del curso («docs/bitacora.md»).
- **Pines.** Usa 19 de unos 25 pines útiles («docs/revision-final.md», §3):
  - I2C 0: pines 21 y 22, a 400 kHz (PCA9685).
  - I2C 1: pines 16 y 17, a 100 kHz (los dos VL53L0X).
  - XSHUT de los VL53L0X: pines 18 y 19.
  - STEP y DIR de las cintas: 25/26 (monedas) y 27/14 (vasos). ENABLE común: 13.
  - ULN2003: pines 32, 33, 23 y 4.
  - Entradas de solo lectura: 34, 35, 36 y 39.
- **No quedan pines libres.** Quedan fuera los pines de arranque (0, 2, 5, 12 y 15), los de la memoria flash (6 a 11) y los del USB (1 y 3). Así, los 19 pines usados son todos los GPIO libres que no son de arranque; «docs/historial-pedidos.md» lo cuenta como «19 de 24 GPIO». Esta falta de pines es la razón del PCA9685 y la que descarta un MOSFET con PWM para el panel de luz («docs/electrica.md», §7).
- **Por qué 38 pines.** Los ESP32 van montados sobre placas de expansión GVS como las de los laboratorios: la de 38 pines para la estación fija y la de 30 para el carro («docs/bitacora.md»). Los pines extra de la versión de 38 son sobre todo los de la memoria flash (6 a 11), que no se pueden usar. No dan GPIO útiles nuevos.
- **Precio:** $39.500 («docs/costos.md»).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| ESP32 DevKit V1 38 pines CH9102F (elegida) | Doble núcleo a 240 MHz, Wi-Fi y BT, ESP-NOW, MicroPython | 3,3 V (AMS1117 en la placa, alimentado por los 5 V del USB); ~100 mA con la radio escuchando, ~240 mA transmitiendo («docs/electrica.md») | Sí: tiene ESP-NOW, comparte ecosistema con el carro y encaja en la placa GVS de 38 pines. |
| ESP32 DevKit 30 pines CH340 | Mismo chip y casi los mismos GPIO útiles | Igual | Es la placa del carro ($34.900). En la estación serviría eléctricamente, pero se eligió la de 38 pines por su placa GVS. |
| Arduino Mega 2560 | ATmega2560 a 16 MHz, 54 E/S digitales, lógica de 5 V, sin radio | 5 V; ~50-80 mA (hoja de datos, típico) | No: sin ESP-NOW ni Wi-Fi haría falta un segundo módulo de radio para hablar con el carro, y su lógica de 5 V no es compatible con los sensores de 3,3 V. |
| Raspberry Pi Pico W | RP2040, 26 GPIO, Wi-Fi | 3,3 V; ~50-100 mA con Wi-Fi (hoja de datos, típico) | No: no tiene ESP-NOW. Habría que comunicarse por Wi-Fi con router y se perdería la compatibilidad con el carro. |
| ESP32-S3 DevKitC | Más GPIO libres, USB nativo, ESP-NOW | 3,3 V; consumo de radio parecido al ESP32 | Técnicamente válida, pero el grupo trabaja con el DevKit V1 y la tabla de pines ya está validada por `tests/sim/test_conexiones.py`. |

**Consumo** («docs/electrica.md»). El ESP32 se alimenta del riel de 3,3 V que genera el AMS1117 del DevKit, que a su vez toma los 5 V del USB del portátil.
- **Solo el ESP32:** 100 mA en reposo, 110 mA típicos y 240 mA de pico.
- **Riel de 3,3 V completo** (el ESP32 más toda la lógica): 181 mA de promedio y 315 mA de pico. El límite térmico es de unos 0,6 A, así que en el pico va al 53 %.
- **Puerto USB:** 186 mA de promedio y 320 mA de pico, contra los 0,5 A que da un USB 2.0.
- **Calor en el AMS1117:** 0,31 W de promedio y 0,54 W de pico. No conviene colgarle más sensores de 3,3 V.

### Drivers de las cintas — A4988 (TMC2208 como opción) (x2)
**Para qué está:** generan la corriente de las bobinas de los dos NEMA17 17HS4401 (cinta de monedas M y cinta de vasos V) a partir de las señales STEP y DIR. Los dos comparten placa, el VMOT de 12 V y la señal ENABLE (G13).

**Por qué este modelo:**
- **Corriente por fase: 1 A.** El motor admite 1,7 A, pero a 1 A queda tibio y el A4988 trabaja sin disipador forzado («docs/electrica.md», §7).
- **Par.** Con 1 A el motor da 0,118 N·m («docs/peso.md»). La cinta de vasos pide 0,0527 N·m (margen de ×2,2) y la de monedas 0,0115 N·m (margen de ×10,2). No hace falta más corriente.
- **Ajuste de Vref.** Se calcula con Vref = 8·Rs·I, según la resistencia Rs del módulo:

  | Rs del módulo | Vref para 1 A |
  |---|---|
  | R050 | 0,400 V |
  | R068 | 0,544 V |
  | R100 | 0,800 V |

  Se mide entre el potenciómetro y GND, con el driver alimentado y sin dar pasos. Si en la prueba de banco el motor pasa de 45 °C, se baja Vref hasta dar 0,8 A.
- **Micropaso de 1/4, no 1/16.** Los pasos los genera el PWM del ESP32, y a 1/4 la frecuencia queda baja: unos 0,8 kHz en monedas y 0,9 kHz en vasos. Así salen 800 micropasos por vuelta y 0,086 mm por micropaso (`config/parametros.yaml`, `microstepping: 4`).
- **Corriente en reposo y ENABLE.** El A4988 no reduce la corriente por su cuenta cuando el motor está quieto. Por eso el firmware desactiva ENABLE cuando las dos cintas llevan 3000 ms quietas (`firmware.a4988_reposo_ms`). Con la línea en marcha nunca se sueltan, porque las pausas son de 1000 y 1400 ms.
- **Ventilador.** A 1 A por fase el A4988 está justo en el límite para trabajar sin aire forzado. Por eso se deja el ventilador 4010 (ver más abajo).
- **Precio y opción.** $8.000 cada uno. «docs/especificacion.md» (§15) y «docs/componentes.md» admiten un TMC2208, que es «silencioso».

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| A4988 (elegida) | Chopper, hasta 1/16 de paso, Vref = 8·Rs·I, protección térmica | VMOT 8-35 V; ~1 A por fase sin disipador ni aire y hasta ~2 A con buen enfriamiento (hoja de datos, típico) | Sí: barato ($8.000), da la corriente que pide el par y usa el formato StepStick común. |
| DRV8825 | Hasta 1/32 de paso, mismo formato StepStick | VMOT 8,2-45 V; ~1,5 A por fase sin disipador y 2,2 A como máximo con enfriamiento (hoja de datos, típico) | Funcionaría, pero no hace falta más corriente ni más micropaso. Su Vref se calcula distinto (I = 2·Vref con Rs de 0,1 Ω) y su ENABLE tiene otra polaridad de pines. |
| TMC2208 | StealthChop (casi silencioso), interpola a 1/256, reduce la corriente en reposo | 4,75-36 V; ~1,2 A RMS por fase (2 A de pico) (hoja de datos, típico) | Opción válida que el repositorio admite. Su fórmula de Vref y su tabla MS1/MS2 son distintas, así que hay que revisarlas en la hoja del módulo antes de cambiar. No tiene precio en «docs/costos.md». |
| TMC2209 | Como el TMC2208, más UART y StallGuard (detecta bloqueos) | ~2 A RMS (2,8 A de pico) (hoja de datos, típico) | Sobra: no se usan ni la detección de bloqueo ni el UART, y la cámara ya resincroniza la cinta. |

**Consumo** («docs/electrica.md»):
- **12 V, VMOT de los dos drivers** (fila 17): 443 mA de promedio y 835 mA de pico.
  - Cada NEMA17 consume 190 mA en reposo, 300 mA típicos y 450 mA de pico.
  - El chopper solo toma de 12 V la potencia que se gasta: 1,50 W en el cobre más 0,75 W en el driver. No toma 1 A por fase.
- **3,3 V, lógica:** 5 mA cada uno, con un máximo de 8 mA.
- **Calor dentro de la caja:** 1,50 W entre los dos drivers.

### Controlador de servos — PCA9685, 16 canales, I2C (x1)
**Para qué está:** genera el PWM de 50 Hz de los 6 servos usando solo 2 pines del ESP32 (SDA 21 y SCL 22, dirección 0x40). Su bornera V+ es el punto de entrada del riel de 6 V, con el condensador de 1000 µF.

**Por qué este modelo:**
- **Pines.** El ESP32 fijo ya usa 19 de sus ~25 pines útiles, así que seis servos más no caben sin quitar otra cosa. «docs/costos.md» descarta conectar los servos directo al PWM del ESP32 y califica ese riesgo como alto. Además, el usuario pidió expresamente dejar el PCA9685 («CONTEXTO-SESION.md», 2026-10-24).
- **Canales.** Usa 6 de 16: 0 desvío, 1 obturador, 2 escape de tapas, 3 prensa (MG996R), 4 empujador (MG996R) y 5 escape de la canaleta. Quedan 10 libres.
- **Separa la potencia de la lógica.** La corriente de los servos vuelve a la fuente por la bornera y no pasa por el ESP32.
- **Bus.** Va en el bus I2C 0, que es corto y trabaja a 400 kHz, con las pull-ups de 10 kΩ del propio módulo. El tiempo de subida es de 297 ns, dentro de los 300 ns que exige 400 kHz («docs/electrica.md», §7).
- **Precio:** $29.500.

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| PCA9685 (elegida) | 16 canales, 12 bits, I2C, oscilador interno, bornera V+ aparte | Lógica 2,3-5,5 V, ~6 mA; V+ pasa directo a los servos (aquí 6 V) | Sí: usa solo 2 pines, sobran canales y separa la potencia de la lógica. |
| LEDC del ESP32 (sin placa) | 16 canales PWM por hardware | Sin consumo extra | No: no hay 6 GPIO libres. Ahorraría $29.500, pero «docs/costos.md» califica el riesgo como alto. |
| Pololu Maestro (6-24 canales) | Controlador por USB o serial, con secuencias propias | Lógica 5-16 V; los servos con fuente aparte (hoja de datos, típico) | No: ocupa otro USB o una UART, y no está en el repositorio (sin precio). |
| TLC5940 | 16 canales PWM de 12 bits con salidas de corriente constante | Lógica 3-5,5 V | No: está pensado para LED. Para servos necesita pull-ups externas y una interfaz serie con más líneas (XLAT, BLANK y GSCLK). |

**Consumo** («docs/electrica.md»):
- **Lógica (3,3 V):** 6 mA típicos y 10 mA de pico.
- **Riel de 6 V que pasa por su bornera** (los 6 servos): 760 mA de promedio y 3,47 A de pico, cuando la prensa aprieta la tapa. El límite es de 5 A (XL4015).
- **Corriente por servo**, tal como la usa la simulación:

  | Servo | Reposo | Moviéndose | Trabado |
  |---|---|---|---|
  | SG90 | 6 mA | 250 mA | 700 mA |
  | MG996R | 10 mA | 900 mA | 2,50 A |

  El repositorio usa 700 mA para un SG90 trabado. La cifra típica de hoja de datos es ~650 mA, así que la del repositorio es un poco más conservadora. Para el MG996R trabado las dos fuentes dan 2,5 A.

### Driver del carrusel — placa ULN2003 con diodos de rueda libre (x1)
**Para qué está:** maneja las 4 bobinas unipolares del 28BYJ-48 de 5 V que gira el carrusel de 6 tubos. Usa 4 GPIO (32, 33, 23 y 4) y tiene el común de las bobinas a +5 V.

**Por qué este modelo:**
- **Tipo de motor.** El 28BYJ-48 es unipolar: cada bobina solo hay que llevarla a GND. El ULN2003 es un arreglo de 7 transistores Darlington con los diodos de rueda libre integrados (COM a 5 V), así que no necesita diodos externos («docs/revision-final.md», §4).
- **Corriente.** Cada bobina tiene unos 50 Ω, lo que da 0,1 A a 5 V. Es muy poco frente a los ~500 mA por canal que admite el ULN2003.
- **Lógica.** Sus entradas aceptan los 3,3 V del ESP32 y tienen resistencias internas de 2,7 kΩ, así que cada entrada consume ~0,7 mA.
- **Precio.** Viene con el motor: $19.000 el conjunto de motor y driver («docs/costos.md»), así que su costo propio es $0.

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| ULN2003 (elegida) | 7 Darlington de colector abierto, diodos internos | Hasta 50 V, ~500 mA por canal (hoja de datos, típico) | Sí: viene con el motor, lleva la carga unipolar a GND y trae los diodos. |
| ULN2803 | Igual, con 8 canales | Igual | No aporta nada: sobran canales y no viene en módulo con el motor. |
| L293D | Doble puente H (4 medios puentes), diodos internos | 4,5-36 V, 600 mA por canal (hoja de datos, típico) | No: pierde más voltaje (~1,4 V o más) y para usar el motor como bipolar habría que cortar el común del 28BYJ-48. |
| L298N | Doble puente H de potencia | Hasta 46 V, 2 A por canal (hoja de datos, típico) | No: está sobredimensionado, es grande, cae ~2 V al conducir y necesita diodos externos. |

**Consumo** («docs/electrica.md»):
- **5 V de la caja:** 0 en reposo, 150 mA típicos y 240 mA de pico. En medio paso conducen 1 o 2 bobinas, más los LED del módulo. Por el cable del ULN2003 pasan 116 mA de promedio y 150 mA de pico.
- **3,3 V (entradas):** 0 en reposo, 1 mA típico y 3 mA de pico.

### Fuente principal — conmutada 12 V 5 A 60 W, caja metálica genérica, 110 × 78 × 36 mm (x1)
**Para qué está:** convierte los 110 V AC de la red en 12 V DC. Alimenta los dos A4988 (VMOT), los sensores M18 (capacitivo e inductivo) y la entrada de los dos buck, todo detrás del fusible principal. Sus bornes −V son el centro de la tierra en estrella.

**Por qué este modelo:**
- **Por qué 5 A.**
  - En el ciclo simulado, el riel de 12 V pide 1,38 A de promedio y 2,93 A de pico: el 59 % de 5 A.
  - El peor caso es el XL4015 en su límite de 4,5 A más el pico de las demás ramas: 3,91 A. También cabe en 5 A.
- **Por qué no 10 A.** La fuente de 10 A anterior se había elegido para los 6 servos trabados a la vez, que piden 7,8 A en 6 V. Con el buck limitado en corriente, esa demanda ya no llega a la fuente («docs/electrica.md», §8).
- **Decisión.** El cambio de 10 A a 5 A se aprobó el 2026-10-24. Ahorra $31.000 y su riesgo es bajo («docs/costos.md»).
- **Por qué 12 V.**
  - Los paso a paso rinden mejor a 12 V, porque la corriente sube más rápido en la bobina.
  - Los M18 piden entre 6 y 36 V («docs/sensores.md»).
  - Los dos buck bajan desde 12 V sin problema.
- **Precio:** $38.000, estimado; hay que verificarlo antes de comprar («docs/costos.md»).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| Fuente 12 V 5 A 60 W (elegida) | Conmutada, caja metálica, bornes de tornillo, sin PFC | 12 V, 5 A | Sí: el pico es de 2,93 A y el peor caso de 3,91 A. |
| Fuente 12 V 10 A 120 W | La del diseño anterior | 12 V, 10 A | No: sobra desde que el XL4015 limita los servos a 4,5 A. Cuesta $31.000 más. |
| Fuente 12 V 3 A 36 W | Más pequeña | 12 V, 3 A | No: el pico del ciclo (2,93 A) la dejaría al 98 % y el peor caso (3,91 A) la sobrecargaría. |
| Fuente ATX de PC | Muchos amperios en 12, 5 y 3,3 V | 12 V, más de 10 A (típico) | No: es voluminosa, necesita un puente para arrancar y no aporta nada frente a los buck ya elegidos. |
| Adaptador de pared 12 V 5 A | Salida por conector jack | 12 V, 5 A | Posible, pero la de caja metálica tiene bornes de tornillo para la tierra en estrella y se monta dentro de la caja. |

**Consumo** («docs/electrica.md»):
- **Salida de 12 V:** 1,38 A de promedio y 2,93 A de pico. El peor caso calculado es de 3,91 A.
- **Desde la red:** 21,2 W de promedio y 43,8 W de pico, con un rendimiento del 82 % más 1,00 W en vacío. Equivale a 0,35 A de promedio a 110 V, con un factor de potencia de unos 0,55 porque no tiene PFC.
- **Calor dentro de la caja:** 4,63 W.

### Regulador de los servos — buck XL4015 CC/CV, 6 V 5 A, límite de corriente en ~4,5 A (x1)
**Para qué está:** baja los 12 V a 6 V solo para los 6 servos (2 MG996R y 4 SG90). La energía les llega por la bornera V+ del PCA9685.

**Por qué este modelo:**
- **Tensión: 6 V.** Es el máximo seguro de los SG90 (4,8-6 V). Además, a 6 V el MG996R da 1,08 N·m de par de bloqueo, frente a 0,92 N·m a 4,8 V («docs/peso.md»).
- **Corriente.** El pico del riel es de 3,47 A: el 69 % de 5 A.
- **Regla del firmware.** El pico cabe porque la prensa y el empujador nunca arrancan a la vez (`EXCLUYENTES` en `firmware/fijo/estacion.py`, comprobado por `tests/firmware/test_firmware.py`).
- **Modo de corriente constante (CC).** Es lo que hace segura la elección. El trimmer de corriente se ajusta en 4,5 A. En los peores casos (6 servos trabados = 7,8 A; 5,3 A si se respeta la regla), el riel de 6 V se hunde durante unos milisegundos en lugar de pasarle esa corriente a la fuente. Los servos se frenan y nada se quema.
- **Por qué no el XL4016.** Reemplazó al XL4016 de 9 A con un ahorro de $16.900. El riesgo es medio: hay que medir el pico real en el montaje («docs/costos.md»).
- **Por qué no el LM2596.** Ver la tabla: no cubre el pico.
- **Precio:** $13.000, estimado; hay que verificarlo.

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| XL4015 CC/CV 5 A (elegida) | Buck de 180 kHz, con ajuste de voltaje y de límite de corriente | Entrada 8-36 V; 5 A, ~4-4,5 A continuos sin disipador extra (hoja de datos, típico) | Sí: cubre el pico de 3,47 A, y su límite de corriente impide que el peor caso llegue a la fuente. |
| XL4016 (anunciado como 9 A) | Igual, más grande, con disipador | Entrada 8-40 V; ~8 A según el chip (el repositorio lo cita como «9 A») (hoja de datos, típico) | No: solo hacía falta para los 6 servos trabados a la vez, y eso ya lo evitan la regla del firmware y el límite CC. Cuesta $16.900 más. |
| LM2596 3 A | Buck de 150 kHz sin límite de corriente ajustable | Entrada 4,5-40 V; 3 A, ~2 A continuos sin disipador (hoja de datos, típico) | No: el pico del riel (3,47 A) lo supera, y un solo MG996R trabado (2,5 A) ya lo deja al límite. |
| Regulador lineal LM7806 / LM1084 | Lineal, sin ruido de conmutación | 1,5 A (7806) / 5 A (1084) (hoja de datos, típico) | No: disiparía (12 − 6) V × I. Con el promedio de 0,76 A son ~4,6 W de calor, y ~20,8 W en el pico de 3,47 A (cálculo con «docs/electrica.md»). |
| MP1584 mini-buck | Muy pequeño | Entrada hasta 28 V; ~3 A de pico, ~2 A continuos (hoja de datos, típico) | No: le falta corriente para el pico de 3,47 A. |

**Consumo** («docs/electrica.md»):
- **Salida de 6 V:** 760 mA de promedio y 3,47 A de pico. El límite es de 5 A, ajustado a 4,5 A.
- **Entrada de 12 V:** 440 mA de promedio y 1,98 A de pico.
- **Potencia que entrega:** 4,56 W de promedio y 20,83 W de pico, con un rendimiento del 88 %.
- **Calor:** 0,62 W de promedio y 2,84 W de pico.

### Regulador de 5 V — buck LM2596, 5 V 3 A, módulo sin voltímetro (x1)
**Para qué está:** da 5 V al ULN2003 y al 28BYJ-48, al panel de luz, al anillo de la cámara y al ventilador.

**Por qué este modelo:**
- **Corriente.** El riel de 5 V pide 930 mA de promedio y 964 mA de pico. Eso es el 32 % de 3 A y queda por debajo de los ~2 A que da en continuo sin disipador. Las cargas son casi constantes (luces y ventilador).
- **Calor.** Disipa entre 1,02 y 1,06 W y queda tibio o caliente sin disipador. Por eso va en el flujo de aire del ventilador («docs/electrica.md», §8).
- **Precio:** $7.000.

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| LM2596 (elegida) | Buck de 150 kHz con trimmer de voltaje | Entrada 4,5-40 V; 3 A, ~2 A continuos (hoja de datos, típico) | Sí: da unas 3 veces la corriente que pide el riel y es barato. |
| XL4015 5 A | Buck CC/CV | 5 A | Sobra: cuesta casi el doble ($13.000) para una carga de ~1 A. |
| MP1584 mini-buck | Buck muy pequeño, conmuta hasta 1,5 MHz | ~3 A de pico, menos en continuo (hoja de datos, típico) | Posible, pero por su tamaño se calienta más y tiene menos margen con ~1 A continuo. |
| LM7805 lineal | Lineal, sin conmutación | 1,5 A (hoja de datos, típico) | No: disiparía (12 − 5) V × 0,93 A ≈ 6,5 W (cálculo con «docs/electrica.md»), lo que exige un disipador grande dentro de una caja cerrada. |

**Consumo** («docs/electrica.md»):
- **Salida de 5 V:** 930 mA de promedio y 964 mA de pico.
- **Entrada de 12 V:** 481 mA de promedio y 498 mA de pico.
- **Potencia que entrega:** 4,65 W de promedio y 4,82 W de pico, con un rendimiento del 82 %.
- **Calor:** 1,02 W de promedio y 1,06 W de pico.

### Fusible principal — fusible de 5 A lento en portafusible de 1 vía, en el +12 V (x1)
**Para qué está:** protege todo el +12 V a la salida de la fuente: los dos buck, los drivers y los sensores M18. Se abre ante un corto o un motor trabado de forma sostenida.

**Por qué este modelo:**
- **Por qué lento.** Un fusible lento aguanta su corriente nominal sin límite de tiempo y se abre en segundos con unas 2 veces ese valor. Así, los picos de 30 ms de un servo no lo abren.
- **Por qué 5 A.** No se abre con el pico del ciclo (2,93 A) ni con el peor caso (3,91 A). Además, queda por debajo de los 7 A que aguanta el cable de 18 AWG de la caja, así que también protege el cableado.
- **Decisión.** Desde el 2026-10-24 hay un solo fusible en lugar de cuatro (antes había uno por rama). Esto, junto con el cable con enchufe a una multitoma con interruptor, ahorró $6.900 («docs/costos.md»).
- **Precio:** $2.300 (portafusible con fusible).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| Fusible 5 A lento (elegida) | Curva lenta; típicamente de vidrio 5 × 20 mm (verificar el portafusible) | 5 A, 250 V | Sí: no se abre con 2,93 A ni con 3,91 A y protege el cable de 18 AWG (7 A). |
| Fusible 5 A rápido | Curva rápida | 5 A | No: podría abrirse sin falla con la corriente de carga de los condensadores al enchufar (los 100 µF de VMOT y las entradas de los buck). |
| Fusible 3 A lento | Curva lenta | 3 A | No: el pico del ciclo (2,93 A) lo dejaría al 98 % y el peor caso (3,91 A, sostenido) lo abriría en plena operación. |
| Fusible 10 A | Curva lenta | 10 A | No: supera los 7 A del cable de 18 AWG, así que no protege el cableado. |
| PTC rearmable (polyfuse) | Se rearma solo al enfriarse | Varios valores | No: con 3-4 A en 12 V su resistencia al conducir y su disparo, lento y variable, son peores. El fusible de vidrio es más predecible. |

**Consumo:** no consume; solo conduce la corriente del riel de 12 V: 1,38 A de promedio y 2,93 A de pico, con un 41 % de margen en el pico («docs/electrica.md»).

### Diodos de las entradas NPN — Schottky BAT85, en los empalmes (x2)
**Para qué está:** llevan la salida NPN del sensor capacitivo LJC18A3 (a G35) y del inductivo LJ18A3-8 (a G36) al ESP32 sin que el pin vea nunca los 12 V del sensor. Reemplazan a los optoacopladores PC817.

**Por qué este modelo:**
- **Condición para leer un 0.** Cuando el sensor detecta, el pin queda en V_ce + V_f. Ese valor tiene que ser menor que 0,825 V, lo máximo que el ESP32 lee como 0.
  - Con el BAT85 (V_f ≈ 0,27 V a ~0,3 mA), el pin queda en 0,57 V: 255 mV de margen.
  - Con un 1N4148, el pin quedaría en 0,85 V, es decir 25 mV por encima del límite. El 0 quedaría en el borde y se podría leer mal.
- **Sin cambios en el firmware.** La lógica sigue siendo activa en bajo.
- **Lo que se pierde.** El aislamiento galvánico del optoacoplador. Si un cable de 12 V pelado toca la señal, llega al diodo y no al pin («docs/electrica.md», §7).
- **Decisión.** Los empalmes soldados reemplazan a la bornera X2, a los optoacopladores y al reparto I2C. El cambio se aprobó el 2026-10-24 con un ahorro total de $27.000 y riesgo bajo («docs/costos.md»).
- **Precio:** $1.000 en total, por los 2 diodos y las 4 resistencias de los empalmes.

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| BAT85 (elegida) | Schottky de señal | V_f ≤ 0,24 V a 0,1 mA y ≤ 0,32 V a 1 mA; 30 V, 200 mA | Sí: deja 255 mV de margen bajo el umbral del 0 del ESP32. |
| 1N4148 | Diodo de silicio de señal | V_f ~0,55 V a 0,3 mA; 100 V | No: el pin queda en 0,85 V, por encima de 0,825 V. Cuesta lo mismo que el BAT85. |
| Optoacoplador PC817 | Aislamiento galvánico | LED de entrada de ~5-20 mA (hoja de datos, típico) | Era el diseño anterior. Es más seguro, pero cuesta más y lleva más cableado. Se quitó para ahorrar. |
| Divisor resistivo | Dos resistencias | Depende de los valores | No: según el sensor, la salida NPN libre flota o sube a 12 V, y el divisor no garantiza ni el nivel alto ni el bajo. |

**Consumo:** despreciable, en el riel de 3,3 V. Pasan 0,27 mA por la pull-up mientras el sensor detecta («docs/electrica.md»).

### Resistencias pull-up — 10 kΩ (x2, entradas NPN) y 2,2 kΩ (x2, bus I2C 1) (x4)
**Para qué están:**
- **Las de 10 kΩ** fijan G35 y G36 en 3,3 V cuando el sensor M18 no detecta. Esos pines son de solo entrada y no tienen pull-up interna.
- **Las de 2,2 kΩ** van en SDA y SCL del bus I2C 1, el bus largo (unos 1,7 m) de los dos VL53L0X.

**Por qué estos valores:**
- **10 kΩ.** Con el NPN conduciendo pasan solo 0,27 mA y el nivel bajo queda bien definido.
- **2,2 kΩ.**
  - **Tiempo de subida.** Con ~170 pF de cable, t_r = 0,8473·R·C = 317 ns. Cumple los 1000 ns de 100 kHz pero no los 300 ns de 400 kHz; por eso este bus va a 100 kHz.
  - **Resistencia mínima.** R_mín = (3,3 − 0,4 V) / 3 mA = 967 Ω, así que 2,2 kΩ cumple.
  - **Corriente.** Con la línea en bajo circulan 1,5 mA.
- **El Hall de G39** usa la pull-up de 10 kΩ de su propio módulo KY-003 (0,33 mA cuando conduce).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| 10 kΩ en las entradas NPN (elegida) | Pull-up externa | 0,27 mA con el sensor detectando | Sí: G35 y G36 no tienen pull-up interna y el consumo es bajo. |
| Pull-up interna del ESP32 (~45 kΩ) | Se activa por software | ~0,07 mA | No: G34 a G39 no la tienen. |
| 2,2 kΩ en el I2C 1 (elegida) | Pull-up de bus | 1,5 mA en bajo; t_r = 317 ns | Sí: cumple a 100 kHz con margen y está por encima del mínimo de 967 Ω. |
| 4,7 kΩ en el I2C 1 | Valor de bus habitual | 0,6 mA en bajo; t_r ≈ 677 ns (misma fórmula de «docs/electrica.md») | Cumpliría a 100 kHz, pero con menos margen en un cable de 1,7 m. |
| 10 kΩ en el I2C 1 (las que traen los módulos) | Las de las placas GY-530 | 0,29 mA en bajo; t_r ≈ 1,44 µs (misma fórmula) | No: superan los 1000 ns de 100 kHz con 170 pF. |

**Consumo:** en el riel de 3,3 V, todas las pull-ups juntas consumen 2 mA en reposo, 3 mA típicos y 4 mA de pico («docs/electrica.md»).

### Resistencia del panel de luz — 3,3 Ω 1 W en serie con el +5 V (x1)
**Para qué está:** limita la potencia de las dos tiras LED 2835 del panel de contraluz de la cámara de vasos. El panel va dentro de una caja de luz de PLA.

**Por qué este modelo:**
- **Sin resistencia.** Las tiras piden 0,80 A a 5 V, es decir 4,0 W dentro del PLA. La caja llegaría a unos 65 °C, por encima de la temperatura de transición vítrea del PLA (55-60 °C).
- **Con 3,3 Ω.** La corriente es I = (5 − 2,8) / (2,75 + 3,3) = 0,36 A. A las tiras les quedan 3,80 V y 1,38 W, por debajo del máximo de 1,5 W.
- **Por qué de 1 W.** La resistencia disipa 0,44 W, así que se elige de 1 W y se monta fuera del PLA.
- **Por qué no un MOSFET con PWM.** No hay GPIO libres. Además, el PWM de 50 Hz del PCA9685 se vería como parpadeo en la cámara.
- **Comprobación en el montaje.** Si la potencia en las tiras (I · V_tiras) pasa de 1,5 W, se cambia por una de 4,7 Ω («docs/electrica.md», §7).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| 3,3 Ω 1 W (elegida) | Resistencia de potencia | 0,36 A; 0,44 W en la resistencia | Sí: deja 1,38 W en las tiras (≤ 1,5 W) y le sobra capacidad de disipación. |
| 4,7 Ω 1 W | Valor de respaldo del repositorio | Menos corriente | Se usa si la medición da más de 1,5 W en las tiras. |
| 3,3 Ω 0,5 W | Resistencia común | 0,44 W | No: trabajaría al 88 % de su potencia nominal y muy caliente. |
| Sin resistencia | — | 0,80 A; 4 W | No: la caja de PLA llegaría a unos 65 °C. |
| MOSFET con PWM | Atenuación por ciclo de trabajo | Variable | No: no hay GPIO libres, y con el PCA9685 a 50 Hz el contraluz parpadearía. |

**Consumo:** en el riel de 5 V de la caja, el panel pide 364 mA en reposo y en uso típico, y 381 mA de pico. Es el dato más incierto de la tabla: es provisional y hay que medirlo en el montaje. En el pico, la resistencia y el cable bajan 1,21 V («docs/electrica.md»).

### Ventilador de la caja — 4010, 5 V, 0,1 A (x1)
**Para qué está:** saca el aire caliente de la caja de control. Va sobre los A4988 y el LM2596.

**Por qué este modelo:**
- **Calor dentro de la caja.** Suma 8,08 W:
  - fuente: 4,63 W;
  - A4988: 1,50 W;
  - XL4015: 0,62 W;
  - LM2596: 1,02 W;
  - AMS1117: 0,31 W.

  Sin ventilador, el aire de la caja cerrada subiría unos 8 °C.
- **Límite de los A4988.** A 1 A por fase están justo en el límite que da la hoja de datos para trabajar sin aire forzado, y ese límite se mide a temperatura de laboratorio. Sin aire se apagarían por temperatura (165 °C) y la cinta se detendría en plena sustentación. La alternativa sería bajar a ~0,8 A por fase, con menos par («docs/electrica.md», §7).
- **Alimentación y tamaño.** El 4010 se alimenta de los empalmes de 5 V y cabe en la caja de 30 × 20 × 8 cm («docs/revision-final.md»).
- **Precio:** ~$6.000, incluido en el renglón de bridas y ventilador ($19.000).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| 4010 5 V (elegida) | 40 × 40 × 10 mm | 5 V, 0,1 A | Sí: es barato, cabe en la caja y se alimenta del riel de 5 V, que tiene un 68 % de margen. |
| Sin ventilador | — | 0 A | No: con +8 °C, los A4988 a 1 A quedan fuera de su condición de uso sin aire forzado. |
| 4010 12 V | Mismo tamaño | 12 V, ~0,05-0,1 A (hoja de datos, típico) | Válido, pero carga el +12 V. El de 5 V usa el riel que tiene más margen. |
| 6025 / 8025 | Más caudal | 5-12 V, ~0,1-0,2 A (hoja de datos, típico) | El de 80 mm no entra en una caja de 8 cm de alto. El de 60 mm es posible, pero no hace falta para unos 8 W. |

**Consumo:** en el riel de 5 V de la caja, 100 mA en reposo y en uso típico, y 150 mA de pico («docs/electrica.md»).

### Condensador de VMOT — electrolítico de 100 µF, ≥ 25 V, uno por A4988 (x2)
**Para qué está:** es la reserva de carga local del chopper y además absorbe el pico LC al enchufar los 12 V.

**Por qué este modelo:**
- **Rizado.** El chopper toma pulsos de hasta 1 A durante unos 20 µs. Con 100 µF, el rizado es ΔV = 1 A · 20 µs / 100 µF = 0,20 V.
- **Pico al enchufar.** Sin el condensador, el pico LC puede llevar la tensión a unas 2 veces su valor (~24 V o más) y superar los 35 V del A4988 («docs/electrica.md», §7). «docs/revision-final.md» advierte que el A4988 «se quema sin él».
- **Tensión nominal de 25 V o más.** Deja más del doble de margen sobre los 12 V.

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| 100 µF ≥ 25 V electrolítico (elegida) | Valor recomendado para módulos StepStick | Rizado de 0,20 V | Sí: el rizado es bajo y absorbe el transitorio al enchufar. |
| 47 µF | Más pequeño | Rizado de ≈ 0,43 V (misma fórmula) | No: duplica el rizado y absorbe menos el pico al enchufar. |
| 220 µF | Más grande | Rizado de ≈ 0,09 V | Funciona, pero es más voluminoso y sube sin necesidad la corriente de carga al enchufar. |
| Solo cerámico de 100 nF | Filtra alta frecuencia | No almacena carga útil | No: no sirve para los pulsos del chopper ni para el pico LC. |

**Consumo:** no consume en régimen permanente (solo la fuga del electrolítico, que es despreciable). Está en el riel de 12 V.

### Condensador de la bornera V+ del PCA9685 — electrolítico de 1000 µF, ≥ 10 V (16 V recomendado) (x1)
**Para qué está:** entrega la corriente de arranque de los servos mientras el XL4015 reacciona. Así evita que el riel de 6 V se hunda y reinicie un servo.

**Por qué este modelo:**
- **Caída de tensión.** Cuando la prensa arranca, pide 2,5 A de golpe, y el buck tarda unos 100 µs en reaccionar. Con 1000 µF, la caída es ΔV = 2,5 A · 100 µs / 1000 µF = 0,25 V.
- **Sin el condensador**, el pico recorre el cable y el voltaje baja lo suficiente para reiniciar un servo («docs/electrica.md», §7).
- **Tensión nominal.** Al menos 10 V sobre los 6 V del riel; se recomiendan 16 V.

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| 1000 µF 16 V (elegida) | Electrolítico | Caída de 0,25 V con 2,5 A | Sí: los servos quedan muy por encima de su mínimo (4,8 V). |
| 470 µF | Más pequeño | Caída de ≈ 0,53 V (misma fórmula) | Funcionaría con menos margen. Si arrancan dos servos, la caída se duplica. |
| 2200 µF | Más grande | Caída de ≈ 0,11 V | Funciona, pero es más grande y pide más corriente al cargarse en el encendido. |
| Sin condensador | — | El pico va directo por el cable | No: hay riesgo de que se reinicien los servos. |

**Consumo:** no consume en régimen permanente. Está en el riel de 6 V.

### Presupuesto de corriente por riel

Valores del ciclo real simulado («docs/electrica.md», §4). Se calcularon con corrientes de hoja de datos y son provisionales hasta medirlos.

| Riel | Lo genera | Promedio | Pico | Límite | Uso en el pico | Margen |
|---|---|---|---|---|---|---|
| 12 V de la fuente | Fuente 12 V 5 A | 1,38 A | 2,93 A | 5,00 A | 59 % | 41 % |
| 6 V de los servos | XL4015 | 760 mA | 3,47 A | 5,00 A | 69 % | 31 % |
| 5 V de la caja | LM2596 | 930 mA | 964 mA | 3,00 A | 32 % | 68 % |
| 3,3 V del ESP32 fijo | AMS1117 del DevKit | 181 mA | 315 mA | 0,60 A | 53 % | 47 % |
| 5 V del USB del ESP32 fijo | Puerto USB del portátil | 186 mA | 320 mA | 0,50 A | 64 % | 36 % |
| Batería 2S del carro | 2 × 18650 | 336 mA | 702 mA | 3,00 A | 23 % | 77 % |
| 5 V del carro | Regulador de la placa GVS | 238 mA | 372 mA | 1,00 A | 37 % | 63 % |

**Peores casos.** No ocurren en el ciclo normal; son calculados.

| Caso | Riel | Corriente | Límite | Qué pasa |
|---|---|---|---|---|
| Los 6 servos trabados a la vez (sin la regla prensa/empujador) | 6 V | 7,80 A | 5,00 A | El XL4015 se queda en 4,5 A y el riel de 6 V se hunde. El fusible principal ve 3,91 A de sus 5 A y no se abre. |
| La prensa y los 4 SG90 trabados en los mismos 30 ms (respetando la regla) | 6 V | 5,30 A | 5,00 A | Igual: el XL4015 lo limita a 4,5 A durante unos milisegundos. El fusible ve 3,91 A. |
| Motor TT trabado con PWM al 100 % y batería a 8,4 V | TB6612 (por canal) | 1,53 A | 1,20 A | No cumple. Con los dos motores, 3,45 A frente a los 3 A del fusible del carro. |
| Motor TT trabado con PWM limitado al 70 % | TB6612 (por canal) | 1,07 A | 1,20 A | Cumple. Con los dos motores, 1,90 A de 3 A. |

**Rendimiento y calor de los reguladores:**

| Regulador | Potencia entregada (prom. / pico) | Rendimiento | Calor (prom. / pico) |
|---|---|---|---|
| XL4015 (6 V) | 4,56 / 20,83 W | 88 % | 0,62 / 2,84 W |
| LM2596 (5 V) | 4,65 / 4,82 W | 82 % | 1,02 / 1,06 W |
| AMS1117-3.3 (ESP32 fijo) | 0,60 / 1,04 W | 66 % | 0,31 / 0,54 W |
| 5 V lineal del carro (8,4 V, batería llena) | 1,19 / 1,86 W | 60 % | 0,81 / 1,26 W |
| 5 V lineal del carro (7,4 V) | 1,19 / 1,86 W | 68 % | 0,57 / 0,89 W |

**Consumo desde la red:** 21,2 W de promedio y 43,8 W de pico, es decir, 0,35 A de promedio a 110 V. No incluye el portátil.

---

Nota: el repositorio se contradice en un punto. La tabla de pines de «docs/revision-final.md» (§3) todavía dice que G35 y G36 llevan optoacopladores PC817. En cambio, «docs/electrica.md», «docs/sensores.md» y «docs/costos.md» dicen BAT85 con pull-up de 10 kΩ desde el 2026-10-24, que es lo vigente. Esa tabla está desactualizada.

## Sensores de la estación

Esta sección cubre los sensores 1 a 8 de «docs/sensores.md». Seis van al ESP32 fijo y dos, las webcams, van directo al portátil, cada una por su propio puerto USB. Las entradas digitales usan los GPIO 34, 35, 36 y 39. Esos pines solo sirven como entrada, así que no ocupan pines de salida, que en el ESP32 fijo escasean: se usan 19 de unos 25 pines útiles («docs/revision-final.md»; «docs/bitacora.md» cuenta 19 de 24). Como esos pines no tienen pull-up interno, las resistencias pull-up van por fuera: en el módulo o soldadas en línea en los empalmes («docs/conexiones.md»). Los dos VL53L0X comparten el bus I2C 1 (SDA en G16, SCL en G17), que tiene pull-ups de 2,2 kΩ y funciona a 100 kHz («docs/electrica.md»).

Desde el 2026-09-25 la regla del grupo es reemplazar con visión todo lo que se pueda. Solo quedan como sensores físicos los que la cámara no puede sustituir:
- el material, porque la cámara no distingue un plástico pintado de un metal;
- la cortina, porque la seguridad no puede depender del PC;
- el interior del vaso, porque los vasos son opacos;
- la referencia del carrusel.

(«docs/especificacion.md», «docs/bitacora.md».) El usuario además prefiere sensores baratos y conocidos («CONTEXTO-SESION.md»).

### Infrarrojo de presencia (E1) — FC-51 (x1)
**Para qué está:** indica si la casilla de la cinta de monedas que llega a E1 trae una pieza (1 = ocupada). Es la primera decisión de la línea: si no hay pieza, no se mide nada más.

**Por qué este modelo:**
- **Distancia de montaje.** Tiene que ver a 5 cm de la cinta para que los bloques altos no lo golpeen. El FC-51 alcanza de 2 a 30 cm, y el alcance se ajusta con el potenciómetro de su comparador LM393. Un TCRT5000 solo ve hasta unos 15 mm, así que tendría que ir tan bajo que las piezas lo golpearían («docs/sensores.md»).
- **Salida y pines.** La salida es digital y responde en menos de 1 ms. El módulo se alimenta a 3,3 V, así que su salida D0 entra directamente al GPIO 34 sin adaptar niveles («docs/conexiones.md»). Llegan 3,30 V al módulo («docs/electrica.md»).
- **Fondo.** La cinta es negra mate y casi no refleja. Para la luz ambiente lleva un capuchón, y el potenciómetro se ajusta con la cinta vacía («docs/sensores.md»).
- **Precio:** $5.000 («docs/costos.md»).

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| FC-51 (elegido) | IR reflectivo con comparador LM393, salida digital, alcance de 2 a 30 cm ajustable | 3,3-5 V; unos 12 mA a 3,3 V («docs/electrica.md») | Sí: alcanza los 5 cm, entrega 3,3 V directo al GPIO y es barato y conocido. |
| TCRT5000 (módulo) | IR reflectivo de corto alcance (2-15 mm), salida digital o analógica | 3,3-5 V; unos 10-20 mA (hoja de datos, típico) | No: con tan poco alcance quedaría donde lo golpean las piezas. En el carro sí se usa. |
| E18-D80NK | IR modulado en cápsula M18, de 3 a 80 cm, salida NPN | 5 V; hasta unos 25 mA (hoja de datos) | No: le sobra alcance, pide 5 V y su salida hay que adaptarla a 3,3 V. Además es más grande y más caro. |
| VL53L0X | Tiempo de vuelo láser, I2C, de 3 cm a 1,2 m | 3,3 V; 19 mA de promedio y unos 40 mA en pulsos | No: para un sí o no a 5 cm no hace falta medir distancia. Sumaría otro dispositivo al bus I2C con su propio XSHUT. |

**Consumo:** en reposo 12 mA, típico 12 mA y pico 15 mA, en el riel de 3,3 V del ESP32 fijo («docs/electrica.md»: unos 10 mA del LED IR más el LM393 y los LED del módulo).

### Sensor capacitivo (E2, montado bajo la casilla E1) — LJC18A3-H-Z/BX (x1)
**Para qué está:** confirma que hay una pieza de cualquier material (plástico, metal o madera) leyéndola a través de los 2 mm de la banda. Junto con el inductivo clasifica el material:
- capacitivo 1 e inductivo 0: no metálico;
- los dos en 1: metal.

**Por qué este modelo:**
- **Alcance y respuesta.** Detecta de 1 a 10 mm, con un tornillo para ajustar la sensibilidad. Responde en unos 5 ms (conmuta a unos 100 Hz). Se calibra con la banda puesta («docs/sensores.md»).
- **Por qué es un sensor físico.** La cámara no distingue un plástico pintado de un metal («docs/especificacion.md»).
- **Posición.** Va centrado bajo la casilla E1 y no bajo la E2, porque una moneda de 17 mm no tapa al mismo tiempo dos caras de 18 mm («docs/bitacora.md»).
- **Tensión y salida.** Necesita de 6 a 36 V, así que se alimenta del riel de +12 V. La salida es NPN normalmente abierta.
- **Cómo llega al GPIO de 3,3 V.** El cable negro pasa por un diodo Schottky BAT85 (con el cátodo hacia el sensor), y el GPIO 35 tiene una pull-up de 10 kΩ a 3,3 V. Los dos van soldados en línea.
  - Con el sensor libre, el diodo queda polarizado en inverso aunque el sensor traiga su propia resistencia a 12 V, y el pin lee 3,32 V.
  - Al detectar, el pin queda en V_ce + V_f = 0,3 + 0,27 = 0,57 V. El ESP32 lee un 0 hasta 0,825 V, así que el margen es de 255 mV.
  - Con un 1N4148 el 0 quedaría en el borde y no se leería de forma confiable. Por eso va un Schottky, que cuesta lo mismo («docs/electrica.md»).
  - La señal es activa en bajo.
  - Este montaje sin optoacoplador PC817 rige desde el 2026-10-24, como ahorro aprobado por el usuario. Se pierde el aislamiento galvánico, pero el diodo impide que los 12 V lleguen al pin («docs/electrica.md», «docs/historial-pedidos.md»).
  - Nunca se conecta el cable negro solo al pin («docs/sensores.md»).
- **Precio:** $32.606 («docs/costos.md»).
- **Discrepancia en el modelo.** «docs/costos.md» cotiza el LJC18A3-**B**-Z/BX, mientras que «docs/sensores.md» dice LJC18A3-**H**-Z/BX. Los dos son NPN normalmente abiertos de 6-36 V. Manda «docs/sensores.md»; la letra hay que confirmarla al comprar.

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| LJC18A3-H-Z/BX (elegido) | M18 capacitivo, 1-10 mm ajustable, salida NPN normalmente abierta | 6-36 V; consumo sin carga ≤ 10-15 mA («docs/electrica.md») | Sí: ve cualquier material a través de 2 mm de banda, y su salida NPN se lleva a 3,3 V con solo un BAT85 y una pull-up. |
| LJC18A3-H-Z/BY (PNP) | Igual, pero la salida entrega +V al detectar | 6-36 V; ≤ 10-15 mA | No: al detectar saca unos 12 V, así que necesita un divisor o un optoacoplador. La salida NPN, que conmuta a GND, se protege con solo un diodo. |
| Módulo táctil TTP223 | Capacitivo de contacto o a través de plástico delgado | 2-5,5 V; unos µA | No: está pensado para un dedo sobre una placa. No tiene un alcance ajustable confiable para una moneda que pasa en movimiento a través de la banda. |
| Sin capacitivo (FC-51 + inductivo) | La presencia la da E1; no metálico = hay presencia y el inductivo no detecta | — | Propuesta de ahorro de $40.606, no aplicada («docs/costos.md»). Se perdería la segunda confirmación de que la pieza sigue en la casilla. |

**Consumo:** en reposo 8 mA, típico 8 mA y pico 15 mA, en el riel de 12 V de la fuente, detrás del fusible principal de 5 A («docs/electrica.md», fila «sensor_m18»). Del lado de 3,3 V, la pull-up gasta 0,27 mA mientras el sensor detecta (la tabla de hilos da 10 µA en reposo y 273 µA de pico).

### Sensor inductivo (E2) — LJ18A3-8-Z/BX (x1)
**Para qué está:** detecta solo metal, por las corrientes de Foucault, bajo la casilla E2 y a través de la banda. Si el inductivo ve metal, su lectura manda sobre la del capacitivo.

**Por qué este modelo:**
- **Alcance real a través de la banda.** El alcance nominal es de 8 mm en acero, medido con una placa patrón de 24 × 24 mm.
  - Una moneda de 17-27 mm bien centrada da alrededor del 70-80 % de ese valor.
  - En bronce, latón y cuproníquel se pierde además un 40-60 %.
  - El alcance real queda entre 2,2 y 4,8 mm, frente a los 2 mm de la banda («docs/sensores.md»).
- **Por qué M18 y no M12.** El M12 de 4 mm se descartó porque, a través de la banda, no alcanzaba con las monedas no ferrosas («docs/sensores.md», «docs/bitacora.md»).
- **Respuesta:** unos 2 ms (conmuta a unos 500 Hz).
- **Montaje.** No es enrasable: no puede haber metal a menos de unos 2 cm de la cara. Por eso va en un inserto impreso en la bancada. Si queda descentrado, pierde la mitad del alcance («docs/sensores.md»).
- **Alimentación y entrada.** Va a +12 V y entra al GPIO 36 con el mismo circuito que el capacitivo: BAT85 más pull-up de 10 kΩ, 0,57 V al detectar y activo en bajo («docs/electrica.md»).
- **Precio:** $21.740 («docs/costos.md»).

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| LJ18A3-8-Z/BX (elegido) | M18, 8 mm nominal en acero, NPN normalmente abierto, no enrasable | 6-36 V; ≤ 10-15 mA («docs/electrica.md») | Sí: es el de la familia que alcanza con monedas no ferrosas a través de 2 mm de banda. |
| LJ12A3-4-Z/BX | M12, 4 mm nominal, NPN normalmente abierto | 6-36 V; unos 10 mA (hoja de datos, típico) | No: con bronce o latón no alcanzaba a través de la banda («docs/bitacora.md»). |
| LJ30A3-15-Z/BX | M30, 15 mm nominal | 6-36 V; unos 10-15 mA (hoja de datos, típico) | No: el nominal se mide con una placa grande. Con una moneda de 17 mm frente a una cara de 30 mm el alcance real cae mucho, y además ocupa más espacio en la bancada. |
| LJ18A3-8-Z/BY (PNP) | Igual, con salida PNP | 6-36 V; ≤ 10-15 mA | No: entrega unos 12 V al detectar y obliga a usar divisor u optoacoplador. |
| TI LDC1612 (inductancia a digital) | Bobina impresa más convertidor I2C que mide la variación de inductancia | 2,7-3,6 V; unos pocos mA (hoja de datos) | No: hay que diseñar la bobina y calibrarla. Es poco conocido, en contra de la preferencia del usuario («CONTEXTO-SESION.md»). |

**Consumo:** en reposo 8 mA, típico 8 mA y pico 15 mA, en el riel de 12 V (fila «sensor_m18» de «docs/electrica.md»). Del lado de 3,3 V, la pull-up gasta 0,27 mA mientras detecta.

### Cámara cenital (E3) — Webcam USB 1080p con autoenfoque + anillo de luz difusa 5 V (x1)
**Para qué está:** fotografía la moneda sobre la cinta negra. En el portátil mide el diámetro, la circularidad y los contornos, y entrega la clase con su nivel de confianza. Con la misma imagen mide cuánto se corrió la cinta. Eso reemplazó al sensor de ranura en la revisión del 2026-09-25 («docs/bitacora.md»).

**Por qué este modelo:**
- **Distancia y enfoque.** Va a 15 cm de la cinta. A esa distancia una webcam de foco fijo no enfoca, así que tiene que tener autoenfoque.
- **Resolución.** El campo es de unos 170 × 100 mm, con 1 px ≈ 0,1 mm. El error esperado en el diámetro es de ±0,08 mm y la respuesta tarda unos 250 ms («docs/sensores.md»).
- **Por qué no 720p.** Bajar a 720p ahorraría $15.000, pero la resolución pasaría de unos 0,05 a unos 0,08 mm/píxel («docs/costos.md»). El usuario decidió el 2026-10-24 no cambiar la webcam cenital («CONTEXTO-SESION.md»).
  - Las cifras de resolución de «docs/sensores.md» (0,1 mm/px) y de «docs/costos.md» (0,05 mm/px) no coinciden. Se confirman con fotos reales en la fase 5.
- **Iluminación.** El anillo de luz difusa reduce las sombras. Puede dar reflejos en monedas brillantes («docs/sensores.md»).
- **Conexión.** USB directo a un puerto propio del portátil, sin hub desde el 2026-10-24 («docs/electrica.md»).
- **Precio estimado:** $80.000, entre webcam (unos $60.000) y anillo (unos $20.000) («docs/costos.md»).

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| Webcam USB 1080p con autoenfoque + anillo (elegida) | 1920 × 1080, MJPEG, UVC (sin driver), autoenfoque | 5 V USB, 250-350 mA; anillo a 5 V, 350-400 mA («docs/electrica.md») | Sí: enfoca a 15 cm, le sobra resolución y se conecta al portátil, donde corre el clasificador. |
| Webcam USB 720p | 1280 × 720, a menudo de foco fijo | 5 V USB, unos 200-250 mA | No: tiene menos resolución y normalmente no enfoca a 15 cm. El usuario rechazó ese ahorro. |
| ESP32-CAM (OV2640) | 2 MP, Wi-Fi, foco fijo de fábrica | 5 V, unos 160-310 mA según el Wi-Fi y el flash (hoja de datos, típico) | No: la imagen llega comprimida por Wi-Fi, sin autoenfoque y con más ruido. El clasificador corre en el portátil de todos modos. |
| Raspberry Pi Camera Module 3 | 12 MP con autoenfoque, interfaz CSI | Necesita una Raspberry Pi | No: añade otro computador al sistema. |
| Celular como cámara IP | Muy buena óptica | Batería propia | No: no queda fijo ni repetible en el montaje y depende de la red. |

**Consumo:**
- Webcam: en reposo 250 mA, típico 250 mA y pico 350 mA, a 5 V por USB desde su puerto del portátil. Un puerto USB 2.0 da 0,5 A («docs/electrica.md»). Tras 1,78 m de cable le llegan unos 4,73 V.
- Anillo: en reposo 350 mA, típico 350 mA y pico 400 mA, en el riel de 5 V de la caja (buck LM2596). «docs/electrica.md» lo marca como dato PROVISIONAL: medir en el montaje.

### Sensor del interior del vaso — VL53L0X, módulo GY-530 (x1, dirección 0x30)
**Para qué está:** en la verificación mide hacia abajo la distancia al fondo del vaso. Si algo queda más arriba que el fondo de un vaso vacío, el vaso trae algo y no entra.

**Por qué este modelo:**
- **Por qué es un sensor físico.** Los vasos son opacos y la cámara no ve adentro («docs/especificacion.md»).
- **Distancia y cono.** Va a 1,5 cm sobre la boca, así que el fondo queda a unos 10,5 cm, dentro del rango de 3 cm a 1,2 m. El cono de 25° llega a la pared con unos 6 mm de margen y tolera unos 3° de inclinación; por eso lleva un collar de centrado («docs/sensores.md»).
- **Precisión.** El error es de ±3 %, unos 4 mm a 12 cm. Por eso se compara con el fondo vacío dejando un margen y se votan 3 medidas de unos 33 ms cada una («docs/sensores.md»).
- **Interfaz y pines.** Es I2C a 3,3 V y comparte el bus con el sensor de la cortina. Solo suma un pin, el XSHUT en el GPIO 18. Su cable mide 1,20 m («docs/electrica.md»).
- **Un solo modelo.** Es el mismo sensor que el de la cortina y el del carro: un solo tipo de pieza y una sola librería.
- **Precio:** $25.000 («docs/costos.md»).

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| VL53L0X (elegido) | Tiempo de vuelo láser de 940 nm, I2C, 3 cm a 1,2 m (hasta unos 2 m en modo largo), cono de unos 25° | Módulo 2,6-5,5 V (chip 2,6-3,5 V); 19 mA de promedio, unos 40 mA en pulsos | Sí: el cono cabe en la boca del vaso, el rango sirve para unos 10 cm y usa los dos hilos compartidos más un XSHUT. |
| VL53L1X | Tiempo de vuelo hasta unos 4 m, cono de unos 27° con región de interés (ROI) programable | 2,6-3,5 V (el módulo suele aceptar 5 V); unos 16-20 mA | No hace falta: 4 m sobran para 10 cm y cuesta más. Su ROI sí permitiría estrechar el cono si el margen de 6 mm no alcanza. |
| HC-SR04 | Ultrasónico de 40 kHz, 2-400 cm, apertura de unos 15° | 5 V; unos 15 mA | No: dentro de un vaso el eco rebota en las paredes. Además su ECHO de 5 V necesita un divisor y ocupa 2 pines. |
| Sharp GP2Y0A21YK0F | IR por triangulación, 10-80 cm, salida analógica | 4,5-5,5 V; unos 30 mA | No: 10 cm es su mínimo, justo la distancia al fondo. Además pide una entrada analógica y su curva no es lineal. |

**Consumo:** en reposo 19 mA, típico 19 mA y pico 40 mA, en el riel de 3,3 V del ESP32 fijo (AMS1117) («docs/electrica.md»). Tras 1,20 m de cable le llegan 3,29 V.

### Sensor Hall del carrusel — A3144 (módulo KY-003) + imán de neodimio N35 de 6 × 3 mm (x1)
**Para qué está:** da la referencia del carrusel (almacén revólver). El 28BYJ-48 no sabe dónde está al encender. Gira hasta encontrar el imán (homing) y desde ahí cuenta pasos. En cada vuelta comprueba que el imán aparezca donde debe.

**Por qué este modelo:**
- **Margen magnético.** Con 4 mm de aire, el imán da unos 70 mT en la cara, y el A3144 conmuta con unos 10-35 mT. El margen alcanza hasta unos 7-8 mm.
- **Respuesta y robustez.** Responde en menos de 1 ms y no le afectan la luz ni el polvo («docs/sensores.md»).
- **Tipo de salida.** Es unipolar: conmuta con un solo polo y se suelta cuando el imán se aleja. Eso es lo que necesita una marca que pasa una vez por vuelta.
- **Conexión.** La salida es de colector abierto y va al GPIO 39, que no tiene pull-up interno, con una pull-up de 10 kΩ. Cuando conduce pasan 0,33 mA y el pin queda en unos 0,15 V («docs/electrica.md»).
- **Decisión del grupo.** El almacén revólver, con su sensor Hall de referencia, se aprobó el 2026-09-26 («docs/bitacora.md»).
- **Discrepancia de tensión.** La hoja de datos de Allegro del A3144 especifica 4,5-24 V, pero el repo lo alimenta a 3,3 V. Muchos módulos KY-003 funcionan a 3,3 V, pero no está garantizado.
  - En el montaje hay que comprobar que conmuta con el imán a 4 mm.
  - Si no lo hace, se cambia por un Hall especificado a 3,3 V (fila del DRV5023) sin tocar el cableado.

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| A3144 / KY-003 (elegido) | Hall unipolar digital, colector abierto; el módulo trae LED | Hoja de datos 4,5-24 V (el repo lo usa a 3,3 V); unos 4,4 mA, máximo 9 mA | Sí: barato, conocido, sin contacto, inmune a la luz y al polvo, y con margen magnético. |
| US1881 | Hall bipolar de enclavamiento (latch), colector abierto | 3,5-24 V; unos 3-5 mA | No: se activa con un polo y solo se libera con el contrario. Con un solo imán quedaría enclavado después de pasar. |
| DRV5023 (TI) | Hall unipolar digital, colector abierto | 2,5-38 V; unos 2,7 mA | Sí como plan B: equivale al A3144 y está especificado a 3,3 V. Es menos común en módulo. |
| Reed switch | Contacto en ampolla de vidrio que cierra con el imán | Sin alimentación | No: tiene rebotes, el vidrio es frágil y su ventana de cierre es más ancha y menos repetible. |
| Final de carrera (microswitch) | Contacto mecánico con palanca | Sin alimentación | No: roza el disco en cada vuelta, se desgasta y suma un par resistente contra un 28BYJ-48 de poca fuerza. |

**Consumo:** en reposo 5 mA, típico 5 mA y pico 10 mA, en el riel de 3,3 V del ESP32 fijo («docs/electrica.md»: el A3144 más el LED del módulo). La pull-up gasta 0,33 mA mientras el imán está debajo.

### Cámara de vasos (silueta, ArUco y tapa) — Webcam USB 720p + panel LED difuso detrás de la cinta (x1)
**Para qué está:** con una sola vista a contraluz de las casillas de la cinta de vasos, da para cada casilla:
- si hay vaso;
- las dos «barreras virtuales» (media altura y borde de la silueta);
- el número del marcador ArUco 4x4_50, que detecta si cambiaron un vaso por otro igual;
- si la tapa está puesta;
- cuánto se corrió la cinta.

**Por qué este modelo:**
- **Qué reemplaza.** A las 6 barreras IR y a los 2 sensores de presencia de vasos (revisión del 2026-09-25, «docs/bitacora.md»), y también al sensor de ranura.
- **Por qué basta con 720p.** Las casillas ocupan unos 24 cm de ancho a unos 22 cm de la cámara, con 1 px ≈ 0,2 mm. Eso basta para las siluetas y para los marcadores de 20 × 20 mm. Responde en unos 60 ms por cuadro y se votan 3 cuadros («docs/sensores.md»). Aquí no se miden décimas de milímetro como en la cámara cenital.
- **Por qué a contraluz.** La silueta no depende del color del vaso ni de la luz del salón, y las sombras casi desaparecen.
- **Panel de luz.**
  - Son 2 tiras 2835 de 20 LED que a 5 V pedirían 0,80 A, es decir 4 W dentro de la caja de luz de PLA. La caja llegaría a unos 65 °C, por encima de la Tg del PLA (55-60 °C).
  - Por eso lleva en serie una resistencia de 3,3 Ω y 1 W: la corriente baja a 0,36 A y las tiras disipan 1,38 W.
  - No se regula con PWM por dos motivos: no hay GPIO libres, y el PCA9685 trabaja a 50 Hz, lo que la cámara vería como parpadeo («docs/electrica.md»).
- **Límite.** Si se cae el PC, no hay verificación de vasos («docs/sensores.md»).
- **Precios estimados:** webcam $45.000 («docs/costos.md»). La resistencia en serie va dentro del lote «Bridas y ventilador» (unos $5.000 entre separadores, cinta de aluminio y resistencia). En las filas leídas de «docs/costos.md» no aparece un precio aparte para las tiras LED.

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| Webcam USB 720p + panel LED (elegida) | 1280 × 720, MJPEG, UVC; contraluz difuso | 5 V USB, 200-250 mA; panel a 5 V, 0,36 A («docs/electrica.md») | Sí: un solo dispositivo reemplaza a varios sensores físicos, y la resolución basta para siluetas y ArUco. |
| Webcam 1080p | Más resolución | 5 V USB, 250-350 mA | No hace falta: 0,2 mm/px es suficiente, y cuesta y consume más. |
| 6 barreras IR (emisor-receptor) + 2 sensores de presencia | Un haz por franja y por estación | Unos 10-20 mA cada uno (hoja de datos, típico) | Diseño anterior, descartado: ocupa entradas que no hay, no lee ArUco ni la tapa, y no nota que cambiaron un vaso por otro igual («docs/bitacora.md»). |
| ESP32-CAM (OV2640) | 2 MP, Wi-Fi | 5 V, unos 160-310 mA (hoja de datos, típico) | No: transmite comprimido por Wi-Fi, con más latencia que por USB. OpenCV corre en el portátil de todos modos. |

**Consumo:**
- Webcam: en reposo 200 mA, típico 200 mA y pico 250 mA, a 5 V por USB desde su propio puerto del portátil, con una extensión de 1 m. Le llegan unos 4,78 V («docs/electrica.md», «docs/conexiones.md»).
- Panel: en reposo 364 mA, típico 364 mA y pico 381 mA, en el riel de 5 V de la caja. «docs/electrica.md» lo marca como PROVISIONAL. En el montaje hay que medir que I × V_tiras ≤ 1,5 W; si se pasa, la resistencia se cambia por una de 4,7 Ω.

### Cortina de seguridad — VL53L0X, módulo GY-530 (x1, dirección 0x31)
**Para qué está:** detecta una mano que entra en la zona entre la tapa y la prensa, del lado del operador. Si mide menos que el largo de la zona (unos 140 mm), la línea se detiene.

**Por qué este modelo:**
- **Por qué es un sensor físico.** La seguridad no puede depender del PC («docs/especificacion.md»).
- **Cuántos sensores.** Hubo un diseño con 3 VL53L0X a 25, 65 y 105 mm. El 2026-09-26 el usuario pidió uno solo a media altura (65 mm), lo que además elimina la interferencia entre sensores («docs/bitacora.md»).
- **Geometría del cono.** Mide en un cono de unos 25°. Con el eje a 85 mm del eje de la cinta, el cono no toca vasos, tapa, prensa ni cinta, y tolera unos 8° de inclinación («docs/sensores.md»).
- **Ventana y voto.** Solo cuenta lo que está dentro de la ventana de distancia, y se votan 3 medidas (unos 100 ms en total).
- **Dos VL53L0X en el mismo bus.**
  - Los dos arrancan con la dirección 0x29.
  - Al encender, el firmware los mantiene apagados con XSHUT (G18 y G19). Enciende uno y le asigna 0x30; luego enciende el otro y le asigna 0x31.
  - Así comparten SDA y SCL, a cambio de un pin más cada uno.
  - El bus mide unos 1,7 m y carga unos 170 pF. Con pull-ups de 2,2 kΩ, el tiempo de subida es de 317 ns: cumple a 100 kHz (máximo 1000 ns) y no cumpliría a 400 kHz (máximo 300 ns). Por eso el bus va a 100 kHz («docs/electrica.md»).
- **Precio:** $25.000 («docs/costos.md»).
- **Límite aceptado.** Una mano que pase por encima del cono puede esquivarlo. Ese caso lo cubre la cámara de vasos, que revisa en cada avance que no falte ningún vaso («docs/sensores.md»). Lo que se busca no es una certificación de seguridad, sino que la máquina se detenga si ve una mano («docs/bitacora.md»).

**Referencias que existen:**
| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| VL53L0X (elegido) | Tiempo de vuelo, I2C, 3 cm a 1,2 m, unos 33 ms por medida, cono de unos 25° | Módulo 2,6-5,5 V; 19 mA de promedio, unos 40 mA en pulsos | Sí: el cono cubre la zona con un solo sensor, mide distancia (lo que permite la ventana) y comparte el bus con el del interior del vaso. |
| VL53L1X | Tiempo de vuelo hasta unos 4 m, cono de unos 27° con ROI | 2,6-3,5 V (el módulo suele aceptar 5 V); unos 16-20 mA | No hace falta para 140 mm. Sería el reemplazo directo si hubiera que recortar el cono con la ROI. |
| HC-SR04 | Ultrasónico, 2-400 cm, apertura de unos 15° | 5 V; unos 15 mA | No: necesita unos 60 ms entre disparos, más lento que los 33 ms del láser. Usa 2 pines y un divisor, y los ecos en los vasos vecinos darían falsos positivos. |
| Barrera IR emisor-receptor / E18-D80NK | Haz fino de sí o no; el E18 llega de 3 a 80 cm con salida NPN | 5 V; hasta unos 25 mA (E18) | No: un haz es una línea, no un cono; por eso antes hicieron falta 3. El E18 pide 5 V y hay que adaptar su salida. |
| Cortina de luz industrial | Muchos haces, certificada | 24 V; del orden de 100 mA según el modelo (hoja de datos) | No: es cara y desproporcionada para el objetivo («docs/bitacora.md»). |

**Consumo:** en reposo 19 mA, típico 19 mA y pico 40 mA, en el riel de 3,3 V del ESP32 fijo («docs/electrica.md»). Con los dos VL53L0X, ese riel suma 38 mA típicos y 80 mA de pico si coinciden los pulsos de los láseres.

---
Las corrientes de las alternativas que no están en el repo son valores típicos de hoja de datos. Hay que confirmar en el montaje tres cosas:
- que el A3144 funciona a 3,3 V, porque está fuera de su especificación de 4,5-24 V;
- la letra del capacitivo: «docs/costos.md» dice B y «docs/sensores.md» dice H;
- el consumo real del panel y del anillo, que el repo marca como PROVISIONAL.

## Carro

El carro es un vehículo de tracción diferencial, separado de la estación. Lleva su propio ESP32 y su propia batería. Recibe el vaso en la cuna, sigue la línea de la pista, esquiva tres obstáculos, llega a la meta y vuelve solo al muelle. Se comunica con la estación por ESP-NOW.

Todos los consumos de esta sección salen de la simulación de «docs/electrica.md». El propio repositorio la marca como PROVISIONAL hasta medirla con multímetro en el montaje.

El carro pesa 0,51 kg, y 0,64 kg con el vaso lleno («docs/peso.md»). Cuesta $253.036, el 16 % del total («docs/costos.md»).

---

### ESP32 del carro — ESP32 DevKit V1 de 30 pines (CH340) sobre placa de expansión GVS (x1)

**Para qué está:** es el controlador del carro. Lee las 12 señales de sus sensores y maneja el TB6612 con 7 pines (PWM, sentido y STBY). Decide qué hacer en cada caso: seguir la línea, esquivar, llegar a la meta, volver o entrar al muelle. Avisa a la estación por ESP-NOW con mensajes numerados que llevan confirmación (ack) («docs/especificacion.md», §10.1).

**Por qué este modelo:**
- **Radio:** la estación es otro ESP32 y el enlace es ESP-NOW («docs/especificacion.md», §10.1). Por eso hace falta un chip de Espressif. Con un microcontrolador sin radio habría que agregar un transceptor, y el protocolo sería otro.
- **Pines:** el carro usa **19 GPIO** («docs/revision-final.md», «ESP32 del carro: 19 pines»):
  - TB6612: 25, 26, 27 / 33, 32, 13 / 4 (7 pines).
  - Encoders con interrupción: 18 y 19.
  - 5 infrarrojos de línea: 34, 35, 36, 39 y 16.
  - HC-SR04: 17 / 23.
  - I2C del VL53L0X: 21 / 22.
  - Cuna: 14.

  Un ESP8266 o una placa mínima ESP32-C3 no tienen tantos pines libres.
- **ADC2 y ESP-NOW:** con ESP-NOW encendido, el ADC2 (pines 0, 2, 4, 12-15, 25-27) no funciona («docs/revision-final.md»). Por eso todos los sensores entregan señal digital. Los pines 34 a 39 son solo de entrada, y ahí van solo sensores.
- **Montaje:** va en una placa GVS como las de los laboratorios, con el jumper en 3,3 V. Cada sensor de 3 hilos entra en la fila de su GPIO (G, V, S) («docs/conexiones.md»).
- **Precio:** $34.900 («docs/costos.md»).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **ESP32 DevKit V1, 30 pines (elegida)** | Doble núcleo a 240 MHz, Wi-Fi + BT, ESP-NOW, ~25 GPIO útiles, 16 canales PWM (LEDC), 2 ADC | 100 mA con la radio escuchando y 240 mA de pico transmitiendo («docs/electrica.md»); entrada VIN de 5 V que la placa baja a 3,3 V | Sí: tiene la misma radio y el mismo firmware (MicroPython) que el ESP32 fijo, y le sobran pines para los 19 que se usan. |
| ESP8266 (NodeMCU) | Un núcleo, Wi-Fi, ESP-NOW, ~9-11 GPIO útiles, un solo ADC | ~70-80 mA con Wi-Fi y picos de ~170 mA al transmitir; 3,3 V | No: le faltan pines (se necesitan 19). |
| ESP32-C3 SuperMini | RISC-V de un núcleo, Wi-Fi + BLE, ESP-NOW, ~13 GPIO en la placa | Del orden del ESP32 con la radio encendida; medir en el montaje | No: es más pequeño, pero sus ~13 pines no alcanzan para los 19. |
| Arduino Nano (ATmega328P) | 16 MHz, 5 V, 22 E/S, sin radio | ~20 mA; 5 V | No: no tiene radio. Habría que agregar un nRF24L01 y un protocolo distinto del ESP-NOW de la estación. |
| Raspberry Pi Pico W | RP2040, Wi-Fi (CYW43439), 26 GPIO | Decenas de mA con Wi-Fi; medir en el montaje | No: no habla ESP-NOW. La estación y el carro necesitarían una red Wi-Fi o un punto de acceso. |

**Consumo:** 100 mA en reposo, 110 mA típico y 240 mA de pico. Va en el riel de 5 V del carro, que sale del regulador de la placa GVS a partir de la batería («docs/electrica.md», carga `esp32_carro`).
- **Riel de 5 V del carro completo** (ESP32 y todos los sensores): 238 mA de promedio y 372 mA de pico, frente a 1 A del regulador (37 % de uso).
- **Nota (discrepancia del repo):** «docs/conexiones.md» y `sim/conexiones.py` llevan la batería al jack de la placa GVS. Ese regulador es lineal, tipo AMS1117-5.0. «docs/revision-final.md» §4 habla en cambio de un buck de 5 V.
  - Con el regulador lineal y la batería llena (8,4 V) se disipan 0,81 W de promedio y 1,26 W de pico. Eso queda cerca del límite de un encapsulado SOT-223.
  - «docs/electrica.md» recomienda un mini-buck (MP1584 o similar), o medir la temperatura después de 10 minutos de uso.

---

### Motorreductores del carro — Motor TT amarillo 1:48 con llanta de 65 mm y encoder de ranura (x2)

**Para qué está:** dan la tracción diferencial. Son dos ruedas motrices más una rueda loca de bola: los tres apoyos siempre tocan el piso y el carro gira sobre su eje sin patinar («docs/componentes.md»).

**Por qué este modelo:** el cálculo de «docs/peso.md» usa el carro con el vaso lleno (0,64 kg), una rueda de 65 mm, una aceleración de 1,0 m/s² y 0,40 m/s en la línea. Da esto:

| Comprobación | Pedido | Disponible | Margen |
|---|---:|---:|---:|
| Par por motor al arrancar | 0,0135 N·m | 0,08 N·m | x5,9 |
| Par por motor en crucero (0,40 m/s) | 0,0031 N·m | 0,0218 N·m | x7,1 |
| Velocidad alcanzable acelerando | 0,40 m/s | 0,46 m/s (v_max = 0,55 m/s) | x1,14 |
| Llantas sin patinar | 1,0 m/s² | 4,5 m/s² | x4,5 |

- **Velocidad:** la reducción 1:48 es la que permite llegar a 0,40 m/s. Una 1:120 daría más par, pero bajaría la velocidad máxima a unos 0,22 m/s (0,55 × 48/120), menos de lo que pide la pista.
- **Tensión:** el motor es de 3-6 V. Con la batería 2S, el firmware limita el PWM a 0,70 (`firmware.carro_pwm_max`). Eso deja unos 5,9 V medios en el motor con la batería llena («docs/electrica.md», §7).
- **Precio:** $12.000 cada uno, $24.000 el par («docs/costos.md»).
- **Decisión del usuario:** el carro ya está impreso y armado con estos motores («CONTEXTO-SESION.md», 2026-10-24: «el carro ya no lo toque»).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **TT 1:48 (elegida)** | Caja de plástico, eje doble en D, ~30 g más 20 g de llanta («docs/peso.md»), disco de encoder en el eje | 3-6 V; 0,15 A en vacío; R ≈ 5,0 Ω («docs/electrica.md»); trabado a ~5,9 V: 1,07 A (contando la caída del driver) | Sí: cubre el par con x5,9 de margen y la velocidad con x1,14. Es barato y es el que ya está montado. |
| TT 1:120 | Misma carcasa, más reducción | 3-6 V; corriente del motor parecida a la de la 1:48 | No: tiene par de sobra, pero solo llega a ~0,22 m/s, menos que los 0,40 m/s del control. |
| N20 con encoder magnético | Micromotorreductor metálico de 12 mm, encoder Hall de 2 canales | Versiones de 3, 6 o 12 V; la corriente depende de la versión (ver su hoja de datos) | No: es más preciso y compacto, pero necesita llantas y soportes propios, y su par depende mucho de la reducción que se compre. |
| JGA25-370 con encoder Hall | Caja metálica, ~90-100 g por motor | 12 V nominal (a 7,4 V gira a ~60 % de su velocidad); trabado pide más de 1 A, según la versión | No: está pensado para 12 V y suma ~100 g por motor. Para 0,64 kg no hace falta. |

**Consumo:** los motores toman de la batería a través del TB6612 («docs/electrica.md», §5 e hilos 123-126):
- **Sin carga:** 0,15 A.
- **Típico en el recorrido:** ~164 mA de promedio por motor (corriente en el cable del motor).
- **Pico:** 471 mA, en los arranques y contra el tope del muelle.
- **Trabado con el PWM al 70 %:** 1,07 A por motor.
- **Trabado con el PWM al 100 % y la batería llena:** 1,53 A. El tope del 70 % existe para evitar este caso.

---

### Puente H del carro — Módulo TB6612FNG (x1)

**Para qué está:** convierte las señales lógicas de 3,3 V del ESP32 en la potencia de los dos motores. Controla el sentido de giro (AIN/BIN), la velocidad (PWMA/PWMB a 1 kHz) y el paro general (STBY).

**Por qué este modelo:**
- **Tensión:** VM trabaja hasta 13,5 V y la batería 2S va de 6,0 a 8,4 V.
- **Corriente:** entrega 1,2 A continuos por canal. Un motor trabado con el PWM al 70 % pide 1,07 A y queda dentro («docs/electrica.md», §7). Al 100 % pediría 1,53 A y se pasaría; por eso el firmware pone el tope.
- **Eficiencia:** las salidas son MOSFET, con unos 0,5 Ω sumando el transistor alto y el bajo (hoja de datos, típico). En el pico de 471 mA caen ~0,24 V y se disipan ~0,11 W por canal. Un puente bipolar perdería ~1,5-2 V.
- **Interfaz:** la lógica funciona de 2,7 a 5,5 V, así que acepta los 3,3 V del ESP32. Usa 7 pines (25, 26, 27, 33, 32, 13 y 4), con el PWM en un pin aparte del sentido.
- **Tamaño:** la placa mide 20 × 20 mm y pesa ~3 g («docs/peso.md»).
- **Precio:** $15.000 («docs/costos.md»).
- **PWM a 1 kHz:** con los 100 nF en los bornes de cada motor, la pérdida por conmutación es de 7,1 mW a 1 kHz. A 20 kHz sería de 141 mW («docs/electrica.md», §7).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **TB6612FNG (elegida)** | Doble puente H MOSFET, ~0,5 Ω (alto + bajo), entradas PWM/IN1/IN2/STBY | 1,2 A continuos y 3,2 A de pico por canal; VM 2,5-13,5 V; lógica 2,7-5,5 V | Sí: tiene poca caída, aguanta el caso trabado al 70 % y con STBY corta todo desde un pin. |
| L298N (módulo) | Doble puente H bipolar, disipador grande, regulador 78M05 en la placa | 2 A por canal; hasta 46 V; caída total de ~1,8-3 V | No: a 7,4 V perdería ~2 V (25-30 % de la batería) en calor. Con el PWM limitado al 70 %, al motor le quedaría muy poca tensión. Además es más grande y pesado. |
| L9110S (módulo) | Doble puente H barato, 2 entradas por motor, sin pin PWM aparte ni STBY | ~0,8 A continuos por canal; 2,5-12 V | No: sus 0,8 A son menos que los 1,07 A de un motor trabado al 70 %, y no tiene modo de espera. |
| DRV8833 (módulo) | Doble puente H MOSFET, ~0,36 Ω (alto + bajo), nSLEEP, 2 entradas por motor | 1,5 A RMS y 2 A de pico por canal; 2,7-10,8 V | Habría servido: es igual de eficiente y sus 10,8 V cubren los 8,4 V de la batería. El TB6612 da más margen de tensión (13,5 V) y separa el PWM del sentido. El repositorio no compara los dos. |

**Consumo:**
- **Lógica (VCC):** ~2 mA desde el 3,3 V del ESP32 (fila G4 de la placa GVS). Cuelga, a su vez, del riel de 5 V del carro.
- **Potencia (VM, desde la batería):** 98 mA de promedio y 330 mA de pico durante el recorrido («docs/electrica.md», hilo 110). Es menos que la corriente de los motores porque, con PWM, la batería solo entrega D·I.
- **Pérdida propia en el pico de 471 mA por canal:** ~0,11 W (hoja de datos, típico; medir en el montaje).

---

### Batería del carro — 2 celdas 18650 de 2500 mAh en serie (7,4 V) con portapilas 2S y BMS 2S (x1)

**Para qué está:** alimenta todo el carro: los motores a través del TB6612, y el ESP32 con sus sensores a través del regulador de 5 V de la placa.

**Por qué este modelo:**
- **Tensión:** el rango 2S (6,0-8,4 V) queda por debajo de los 13,5 V del TB6612. Los motores, que son de 3-6 V, se protegen con el tope de PWM al 70 %.
- **Batería casi vacía:** con un regulador lineal tipo AMS1117-5.0, que necesita ~1,1-1,3 V de margen (hoja de datos), la salida de 5 V se mantiene solo con la batería por encima de ~6,2 V. Cerca de 6,0 V baja a ~4,8 V. El ESP32 y el HC-SR04 siguen funcionando con eso, pero conviene medirlo.
- **Autonomía** («docs/electrica.md», §5):
  - Un recorrido completo dura 122 s, con 336 mA de promedio y 702 mA de pico.
  - Con el 85 % de 2500 mAh (2125 mAh) alcanza para **6,3 h andando**, unos 186 recorridos.
  - Esperando en el muelle con la radio encendida (232 mA), dura **9,2 h**.
  - Una carga cubre de sobra la sustentación.
- **Caída en el pico:** la batería baja a 7,27 V. La resistencia interna, el BMS, el fusible y el interruptor suman ≈180 mΩ.
- **Protección y peso:** el BMS 2S protege contra sobredescarga y cortocircuito. El conjunto pesa 112 g y es la masa más grande del carro («docs/peso.md»). Va atravesada en el chasis («docs/revision-final.md»).
- **Precio:** $71.500 (par de celdas $60.000 + portapilas $3.500 + BMS $8.000). Comprar las celdas en par ahorra $4.000 frente a dos sueltas («docs/costos.md»).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **2 × 18650 de 2500 mAh + BMS 2S (elegida)** | Recargable, celdas reemplazables, BMS de protección | 6,0-8,4 V; el BMS 2S típico corta en 3-5 A («docs/electrica.md») | Sí: da 6,3 h de marcha, aguanta sin problema los picos de 0,7 A y cabe atravesada en el chasis. |
| LiPo 2S de 1000-2200 mAh | Plana y liviana, alta descarga | 7,4 V nominal; decenas de amperios (C alto) | No: necesita cargador con balanceo y cuidado al usarla (se hincha si se descarga de más). Las 18650 con BMS son más seguras para un proyecto de aula. |
| 4 × AA alcalinas o NiMH | Portapilas común | 6 V (alcalinas) o 4,8 V (NiMH) nominales; la tensión cae mucho con carga | No: las dos quedan por debajo de los ~6,2 V que pide el regulador lineal de 5 V. Las alcalinas además no se recargan. |
| Batería de 9 V (PP3) | Pequeña | 9 V, ~400-600 mAh, alta resistencia interna | No: no sostiene los picos de 0,7 A y duraría muy poco. |
| 1 × 18650 + elevador (boost) a 5-7 V | Una sola celda | 3,0-4,2 V de entrada | No: el boost cargaría con toda la corriente de los motores (picos de ~1 A a la salida) y sumaría su propia pérdida. Son más piezas y más calor que usar 2S directo. |

**Consumo (lo que entrega):** 232 mA en reposo (en el muelle, con la radio encendida), 336 mA típico durante el recorrido y 702 mA de pico, en el riel de batería 2S («docs/electrica.md», §4 y §5). El promedio se reparte en 98 mA al VM del TB6612 y 238 mA al regulador de 5 V.

---

### Interruptor y fusible del carro — Interruptor + portafusible aéreo con fusible de 3 A (x1)

**Para qué está:** el interruptor desconecta la batería para apagar el carro. El fusible protege el cableado (22 AWG) ante un cortocircuito o si los motores quedan trabados de forma sostenida.

**Por qué este modelo:** «docs/electrica.md» (Fusibles y Peores casos) dimensiona el fusible de 3 A así:

| Situación | Corriente | Frente a 3 A |
|---|---:|---|
| Recorrido normal (promedio / pico) | 336 mA / 702 mA | 77 % de margen en el pico |
| Dos motores trabados con PWM al 70 % | 1,90 A | No abre; el firmware detecta el atasco (los encoders dejan de contar) |
| Dos motores trabados con PWM al 100 % y batería llena | 3,45 A | Supera el nominal |

- **Uso normal:** el fusible no salta en el uso normal y solo actúa ante una falla.
- **Caso de 3,45 A:** son solo ~1,15 veces el nominal, y un fusible de vidrio puede tardar mucho en abrir con eso, o no abrir (las normas garantizan la apertura con ~1,35-2,1 veces el nominal, según el tipo). Ese caso lo evita de verdad el tope de PWM del firmware. El fusible protege sobre todo contra cortocircuitos.
- **Montaje y precio:** va en la caja impresa del interruptor (36 × 16 × 12 mm). Precio estimado: $4.000 («docs/costos.md»).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **Fusible de vidrio de 3 A en portafusible aéreo + interruptor (elegida)** | Barato, fácil de cambiar | 3 A nominales | Sí: deja pasar el pico de 0,7 A y los 1,9 A de un atasco pasajero, y abre ante un cortocircuito. |
| Fusible de 2 A | Más sensible | 2 A nominales | No: queda muy justo frente a los 1,90 A de dos motores trabados al 70 %. Podría saltar si el carro empuja el tope del muelle por mucho tiempo. |
| Fusible de 5 A | Más tolerante | 5 A nominales | No: queda muy por encima del peor caso del carro (3,45 A), así que solo actuaría ante un cortocircuito franco. |
| Polifusible PTC de ~2,5 A | Se rearma solo | Corriente de mantenimiento ~2,5 A; corta más lento | Podría servir: evita cambiar fusibles, pero el corte es más lento y menos definido. El repositorio no lo considera. |
| Solo el BMS 2S | Ya viene con la batería | Corta en 3-5 A | No como única protección: cuida las celdas, pero no el cableado que sigue. |

**Consumo:** no consume nada propio. Su caída está incluida en los ≈180 mΩ del camino batería → BMS → fusible → interruptor («docs/electrica.md», §5). Por él pasan 336 mA de promedio y 702 mA de pico, en el riel de batería.
- **Nota (discrepancia del repo):** «docs/componentes.md» y «docs/costos.md» dicen «interruptor de palanca», mientras que «docs/peso.md» dice «interruptor KCD11», que es de balancín. Con la pieza comprada hay que confirmar que su capacidad en corriente continua es al menos la del fusible (3 A). Los KCD11 suelen venir marcados solo en alterna.

---

### Rodillos guía traseros — Rodamiento 623 (3 × 10 × 4 mm) en tornillo M3 × 30 (x2)

**Para qué está:** van en las esquinas traseras del carro. Las guías en V del muelle empujan estos rodillos, no las llantas. Al entrar de reversa, el carro gira hacia el centro «como un carrito de supermercado». Así la cuna queda bajo el final de la canaleta, aunque el carro haya seguido la línea con error («docs/componentes.md»).

**Por qué este modelo:**
- **Tornillería:** el agujero de 3 mm encaja en tornillo M3, que es el que usa todo el carro (2 tornillos M3 × 30, «docs/costos.md»).
- **Peso:** ~1,7 g cada uno («docs/peso.md»).
- **Tamaño:** su diámetro de 10 mm rueda sobre la guía forrada con PTFE sin agrandar el brazo impreso (40 × 14 × 12 mm).
- **Rozamiento:** el rodamiento cambia el roce por rodadura. Así el carro se deja centrar aunque entre con el PWM bajo (35 %, «docs/electrica.md»).
- **Precio:** estimado de $3.000 cada uno, $6.000 el par («docs/costos.md»).
- **Nota (discrepancia del repo):** «docs/costos.md» y «docs/componentes.md» cuentan 2 rodamientos en total. «docs/peso.md» los describe como «2 rodamientos 623 … por esquina», lo que daría 4. Hay que confirmarlo en el carro armado.

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **623 / 623ZZ (elegido)** | 3 × 10 × 4 mm, ~1,7 g | No aplica | Sí: encaja en M3 y es pequeño y liviano. |
| 603 / 693 | 3 × 9 × 5 mm y 3 × 8 × 4 mm | No aplica | Servirían igual: son para M3 y apenas más pequeños. El repositorio no explica por qué eligió el 623. |
| 624 | 4 × 13 × 5 mm | No aplica | No: pide tornillo M4 y un brazo más grande, y el carro usa M3. |
| 608ZZ | 8 × 22 × 7 mm (el que usa la estación) | No aplica | No: es demasiado grande y pesado (~12 g) para la esquina del carro y no va en M3. |
| Rodillo impreso sin rodamiento | PLA girando sobre el tornillo | No aplica | No: el roce del PLA sobre el acero frenaría el centrado cuando el carro entra con PWM bajo. |

**Consumo:** no aplica (es una pieza mecánica).

---

### Sensor 9: arreglo de 5 infrarrojos de línea — Módulo de seguimiento TCRT5000 de 5 canales (x1)

**Para qué está:** detecta la línea negra de cinta aislante bajo el frente del carro. Entrega 5 bits; por ejemplo, 00100 significa centrado («docs/sensores.md», §9).

**Por qué este modelo:**
- **Salidas digitales:** el módulo trae comparadores y sus salidas son digitales. Así no se usa el ADC2 (que no funciona con ESP-NOW) y las 5 señales entran en los pines 34, 35, 36, 39 y 16.
- **Cobertura:** cinco canales cubren el ancho de la cinta y permiten saber hacia qué lado se va el carro.
- **Velocidad:** responde en menos de 1 ms.
- **Altura de montaje:** «docs/sensores.md» recomienda 3-5 mm del piso (alcance de 2-10 mm). «docs/revision-final.md» registra el montaje real a 7 mm, con un alcance de ~15 mm.
- **Filtrado:** el control decide cada bit por mayoría de 3 lecturas.
- **Precio:** $15.900 («docs/costos.md»).
- **Nota (discrepancia del repo):** «docs/componentes.md» dice que la cinta es de 19 mm y «docs/costos.md» compra cinta de 18 mm.

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **Módulo TCRT5000 de 5 canales (elegido)** | 5 pares emisor-receptor IR con comparador, salidas digitales, una sola placa | ~10 mA por LED, 50 mA en total a 3,3 V («docs/electrica.md») | Sí: es una sola placa con una sola alimentación, da salida digital (no necesita ADC) y es económico. |
| 5 módulos TCRT5000 sueltos | Misma óptica en 5 placas | ~10-12 mA cada uno a 3,3 V | No: hace lo mismo con cinco veces más cables y es más difícil alinearlos. |
| Pololu QTR-8RC / QTR-8A | 8 sensores; versión RC (tiempo de descarga) o analógica | ~100 mA con todos los LED a 5 V | No: tiene más resolución de la necesaria. La versión A pide ADC (con ESP-NOW, solo el ADC1) y la RC pide medir tiempos por software en 8 pines. |
| CNY70 (sueltos) | Sensor reflexivo encapsulado, sin comparador | ~10-20 mA de LED por sensor | No: necesita comparador o ADC y montarlos uno por uno. |

**Consumo:** 50 mA en reposo, 50 mA típico y 60 mA de pico. Sale del 3,3 V del ESP32, que cuelga del riel de 5 V del carro («docs/electrica.md», carga `ir5`).

---

### Sensor 10: ultrasónico frontal (respaldo) — HC-SR04 (x1)

**Para qué está:** mide la distancia al obstáculo de adelante. Es el respaldo del láser: no le afectan las superficies negras o brillantes ni el sol. A menos de 500 mm el carro frena; a menos de 200 mm, con 2 mediciones seguidas, esquiva («docs/sensores.md», §10).

**Por qué este modelo:**
- **Alcance:** mide de 2 a 400 cm, con resolución de ~3 mm y una apertura de ~15°.
- **Complementa al láser:** el VL53L0X falla con superficies negras o brillantes, que no afectan al ultrasonido.
- **Interfaz:** usa 2 pines: TRIG en G17 (un pulso de 3,3 V alcanza para dispararlo) y ECHO en G23.
- **Divisor del ECHO:** el sensor saca 5 V por ECHO. Un divisor de 1 kΩ / 2 kΩ lo baja a 3,33 V, que está por debajo de los 3,6 V máximos del pin y por encima de los 2,47 V que el ESP32 lee como 1 («docs/electrica.md», §7).
- **Precio:** $7.500 («docs/costos.md»).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **HC-SR04 (elegido)** | 40 kHz, 2-400 cm, ~15°, TRIG/ECHO | 15 mA a 5 V | Sí: es barato y conocido, y cubre lo que el láser no ve. Solo pide el divisor en ECHO. |
| RCWL-1601 | Clon del HC-SR04 que funciona a 3,3 V | Pocos mA (según el vendedor; medir en el montaje) | Podría servir y ahorraría el divisor, pero el repositorio no lo considera. |
| US-100 | 2-450 cm, compensación de temperatura, modo UART o pulso | ~2 mA; 2,4-5,5 V | Es más preciso, pero el HC-SR04 basta para decidir a 200 y 500 mm. |
| JSN-SR04T | Sonda impermeable separada | ~30 mA; 5 V; zona ciega de ~20-25 cm | No: su zona ciega coincide con el umbral de esquivar (200 mm). |
| Sharp GP2Y0A21YK0F | IR por triangulación, 10-80 cm, salida analógica | ~30 mA; 5 V | No: necesita ADC (con ESP-NOW, solo el ADC1) y las superficies oscuras también lo confunden, igual que al láser. |

**Consumo:** 15 mA en reposo, 15 mA típico y 15 mA de pico, en el riel de 5 V del carro (pin 5V de la placa GVS) («docs/electrica.md», carga `hcsr04`). El divisor gasta además 1,67 mA, solo mientras ECHO está en alto.

---

### Sensor 11: encoders de las ruedas — Horquilla óptica F249 / H206 + disco de 20 ranuras (x2)

**Para qué está:** cuenta el giro de cada rueda para la odometría (distancia y rumbo). También detecta la llegada al muelle: cuando el carro empuja el tope con PWM bajo, los encoders dejan de contar («docs/sensores.md», §11; «docs/componentes.md»).

**Por qué este modelo:**
- **Resolución:** 20 ranuras con una rueda de 65 mm dan ~10 mm de avance por pulso (π·65/20 ≈ 10,2 mm). Es suficiente porque la odometría se corrige con la línea.
- **Interfaz:** salida digital con comparador LM393, a los pines con interrupción 18 y 19. Los pulsos llegan a «hasta ~120 por s» («docs/electrica.md», hilos 127 y 130).
- **Montaje:** el disco va en el eje doble del motor TT, con un soporte impreso de 1,4 g («docs/costos.md»).
- **Precio:** $7.500 cada uno (sensor $6.000 + disco $1.500), $15.000 el par («docs/costos.md»).
- **Nota (nombres distintos en el repo):** «docs/costos.md» lo llama «sensor de herradura F249», «docs/conexiones.md» y «docs/revision-final.md» lo llaman «H206» y «docs/componentes.md» / «docs/sensores.md» lo llaman «encoder óptico de ranura». Los tres nombres describen el mismo tipo de pieza: una horquilla óptica con comparador.

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **Horquilla H206 / F249 + disco de 20 ranuras (elegida)** | Barrera óptica, LM393, salida digital, ~10 mm por pulso | 12 mA (15 mA de pico) a 3,3 V («docs/electrica.md») | Sí: encaja en el eje del TT, es barata y da una señal limpia para interrupciones. |
| Encoder magnético Hall de 2 canales (motor TT o N20 que ya lo trae) | Cuadratura A/B (detecta el sentido) y más pulsos por vuelta | ~5-10 mA; 3,3-5 V | No: obliga a cambiar de motor o a usar un kit específico. Además, el sentido ya lo conoce el firmware, porque es él quien lo manda. |
| AS5600 (magnético absoluto) | 12 bits por vuelta, I2C | ~6,5 mA; 3,3 V | No: tiene mucha más resolución de la necesaria. Habría que pegar un imán en el eje y compartir el bus I2C con el VL53L0X. |
| TCRT5000 sobre un disco pintado | Sensor reflexivo en vez de barrera | ~10-12 mA | No: es más sensible a la luz ambiente y a la distancia al disco que una horquilla. |

**Consumo:** cada encoder gasta 12 mA en reposo, 12 mA típico y 15 mA de pico (24 / 24 / 30 mA los dos). Sale del 3,3 V del ESP32, que cuelga del riel de 5 V del carro («docs/electrica.md», carga `h206`).

---

### Sensor 12: infrarrojo de la cuna de carga — Módulo TCRT5000 de 1 canal (x1)

**Para qué está:** antes de que el escape suelte un vaso, confirma que la cuna está vacía. Después confirma que el vaso quedó en ella. Decide con 3 lecturas iguales, y la estación no suelta un vaso si la cuna no está libre («docs/sensores.md», §12; «docs/especificacion.md»).

**Por qué este modelo:**
- **Alcance:** el TCRT5000 detecta de 2 a 15 mm, apuntado al fondo opaco del vaso. Quedó a 6 mm del vaso; antes estaba a 15,5 mm, justo en el límite, y se corrigió («docs/revision-final.md»).
- **Conexión:** salida digital activa en bajo, en G14. Ese pin es del ADC2, pero aquí se usa solo como entrada digital.
- **Señal limpia:** como su alcance es corto, no ve las paredes ni los rieles de la cuna.
- **Elección del repo:** «docs/sensores.md» admite TCRT5000 o FC-51; «docs/costos.md» y «docs/conexiones.md» eligen el TCRT5000.
- **Precio:** $6.000 («docs/costos.md»).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **TCRT5000, módulo de 1 canal (elegido)** | Reflexivo, 2-15 mm, comparador ajustable | 12 mA (15 mA de pico) a 3,3 V («docs/electrica.md») | Sí: su alcance es corto y definido, justo a la distancia del vaso. |
| FC-51 | Reflexivo, emisor y receptor separados, ~2-30 cm ajustable | ~12 mA a 3,3 V (medir en el montaje); $5.000 en «docs/costos.md» (el de la estación) | El repo lo admite, pero con su alcance largo puede detectar las paredes de la cuna o lo que haya detrás. |
| Final de carrera (microinterruptor) | Contacto mecánico | Prácticamente 0 mA (solo la pull-up) | No: el vaso tendría que empujar la palanca. Uno vacío o liviano puede no accionarla, y el contacto rebota. |
| VL53L0X | Láser de tiempo de vuelo, I2C | 19 mA (40 mA de pico) | No: su alcance mínimo es de ~3 cm, así que no mide a 6 mm. Además cuesta $25.000 («docs/costos.md»). |

**Consumo:** 12 mA en reposo, 12 mA típico y 15 mA de pico. Sale del 3,3 V del ESP32, que cuelga del riel de 5 V del carro («docs/electrica.md», carga `tcrt_cuna`).

---

### Sensor 13: láser de distancia frontal — VL53L0X (módulo GY-530) (x1)

**Para qué está:** es el sensor principal de obstáculos y va al frente, encima del ultrasónico. A menos de 500 mm el carro baja a velocidad de maniobra. A menos de 200 mm, con 3 mediciones seguidas, se detiene, mira a los lados y esquiva («docs/sensores.md», §13).

**Por qué este modelo:**
- **Velocidad:** mide cada ~33 ms, el doble de rápido que el ultrasónico (~60 ms entre disparos). A 0,40 m/s el carro avanza ~13 mm entre dos lecturas.
- **Alcance:** de 3 cm a ~1,2 m en el modo por defecto, con un cono de ~25° y un error de ±3 % a corta distancia.
- **Interfaz:** I2C en G21/G22. Es el único dispositivo del bus del carro, así que no necesita XSHUT. El bus es corto (0,15 m) y funciona a 400 kHz («docs/electrica.md», hilos 144-147).
- **Repuestos:** es el mismo modelo que la cortina y el sensor del interior del vaso de la estación.
- **Precio:** $25.000 («docs/costos.md»).

**Referencias que existen:**

| Referencia | Características clave | Corriente / tensión | ¿Por qué no (o por qué sí)? |
|---|---|---|---|
| **VL53L0X (elegido)** | Tiempo de vuelo a 940 nm, ~1,2 m, ~25°, 33 ms, I2C | 19 mA de promedio y ~40 mA en los pulsos («docs/electrica.md»); el sensor trabaja a 2,6-3,5 V y el módulo acepta 3,3-5 V | Sí: es rápido, pequeño y digital, y es el mismo modelo de la estación. |
| VL53L1X | Tiempo de vuelo hasta ~4 m, zona de medida configurable | ~16-20 mA; 2,6-3,5 V en el sensor | Funcionaría, pero la pista no necesita más de 1,2 m. El repositorio no tiene su precio. |
| VL6180X | Tiempo de vuelo de corto alcance (~10 cm garantizados) | Pocos mA de promedio (según el modo; medir en el montaje) | No: con ese alcance no se puede cumplir el umbral de 500 mm para frenar. |
| Sharp GP2Y0A21YK0F | IR por triangulación, 10-80 cm, salida analógica | ~30 mA; 5 V | No: necesita ADC1, su salida no es lineal y es más lento (~39 ms). |
| TF-Luna (LiDAR) | 0,2-8 m, UART o I2C, ~100 Hz | ~70 mA; 5 V | No: su zona ciega de 20 cm coincide con el umbral de esquivar. Además consume más y es más grande. |

**Consumo:** 19 mA en reposo y típico, y ~40 mA de pico en los pulsos del láser. Sale del 3,3 V del ESP32, que cuelga del riel de 5 V del carro («docs/electrica.md», carga `vl53`, hilos 144-145).

---

### Resumen eléctrico del carro

| Riel | Promedio | Pico | Límite | Fuente |
|---|---:|---:|---:|---|
| Batería 2S (6,0-8,4 V) | 336 mA | 702 mA | 3 A (fusible) | «docs/electrica.md», §4-§5 |
| VM del TB6612 | 98 mA | 330 mA | 1,2 A continuos por canal | «docs/electrica.md», hilo 110 |
| Cada motor TT (corriente del motor) | ~164 mA | 471 mA | 1,07 A trabado con PWM al 70 % | «docs/electrica.md», hilos 123-126 |
| 5 V del carro (ESP32 + sensores) | 238 mA | 372 mA | 1 A (≈0,3 A continuos por calor si el regulador es lineal) | «docs/electrica.md», §1 y §4 |

**Qué medir en el montaje** («docs/electrica.md», §9):
- La corriente real de la batería con el carro andando, con el multímetro en serie en el fusible.
- Qué regulador trae la placa GVS (lineal o conmutado), su temperatura después de 10 minutos y la tensión de 5 V con la batería cerca de 6,0 V.

Las alternativas de las tablas son referencias del mercado: el repositorio no las cita ni tiene sus precios. Sus corrientes son valores típicos de hoja de datos. Donde no hay un dato confiable, dice «medir en el montaje» o «según la versión».
