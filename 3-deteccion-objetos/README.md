# Detección de objetos

## Qué es YOLO

YOLO, cuyas siglas vienen de You Only Look Once, es una familia de modelos de red neuronal pensada para detectar objetos dentro de una imagen o un video en tiempo real. La idea que lo hizo diferente cuando apareció en 2015, de la mano de Joseph Redmon y Ali Farhadi, fue tratar la detección como un solo problema de regresión, es decir el modelo mira la imagen completa una única vez y en esa misma pasada calcula al mismo tiempo dónde están los objetos y qué son, en lugar de primero buscar posibles regiones con objetos y después clasificarlas por separado, que era como funcionaban los detectores anteriores basados en dos etapas, como R-CNN. Esa diferencia es la que le da a YOLO su velocidad, siendo capaz de procesar decenas de fotogramas por segundo incluso en hardware modesto.

Internamente el proceso funciona dividiendo la imagen de entrada en una cuadrícula, donde cada celda de esa cuadrícula queda a cargo de predecir posibles objetos cuyo centro caiga dentro de ella. Para cada objeto candidato el modelo predice las coordenadas del cuadro que lo delimita, una puntuación de qué tan seguro está de que ahí realmente hay algo, y las probabilidades de a qué clase pertenece ese objeto, por ejemplo una silla o un celular. Como este proceso genera muchas predicciones superpuestas para el mismo objeto, al final se aplica una técnica llamada supresión no máxima, que se encarga de quedarse solo con la predicción más confiable de cada objeto y descartar las repetidas.

Desde esa primera versión la familia fue evolucionando mucho. Las versiones intermedias mejoraron la precisión y la capacidad de detectar objetos pequeños, y en 2020 Ultralytics lanzó YOLOv5, implementado en PyTorch, lo que lo hizo mucho más fácil de instalar y usar y terminó convirtiéndolo en el estándar de facto para la mayoría de proyectos aplicados. Las versiones más recientes, incluida la usada en este proyecto, siguen esa misma línea de facilidad de uso, empaquetadas dentro de la librería ultralytics de Python.

## Cómo está armado este proyecto

La idea central es cerrar el círculo entre visión artificial y electrónica física. La computadora corre el modelo de YOLO leyendo la cámara en vivo, y cuando reconoce alguno de los objetos que nos interesan, en este caso una silla o un celular, le avisa al ESP32 a través de un cable USB, y el ESP32 enciende el LED correspondiente. Cuando el objeto deja de estar en cuadro, el LED se apaga.

```mermaid
flowchart TD
    Camara["Cámara web"] --> PC["deteccion_pc.py<br/>YOLO + pyserial<br/>corre en la PC"]
    PC -->|"puerto serial USB<br/>115200 baudios"| ESP32["main.py<br/>MicroPython<br/>corre en el ESP32"]
    ESP32 -->|"GPIO25"| LED1["LED silla"]
    ESP32 -->|"GPIO26"| LED2["LED celular"]
```

El cable USB que normalmente se usa para programar el ESP32 desde Thonny es el mismo que se aprovecha aquí, porque por dentro no es más que un puerto serial. La computadora le manda al ESP32 un texto corto cada vez que cambia lo que está viendo, y el ESP32 se queda escuchando ese puerto todo el tiempo, sin necesidad de estar conectado a internet ni de usar WiFi para nada de esto.

El protocolo de comunicación se mantuvo lo más simple posible a propósito. Cada vez que el estado de lo que ve la cámara cambia, la computadora envía dos caracteres seguidos de un salto de línea, el primero indica si la silla está presente con un uno o un cero, y el segundo hace lo mismo con el celular. Por ejemplo diez significa que se ve la silla pero no el celular, y cero uno sería lo contrario. El ESP32 lee esa línea y prende o apaga cada LED según corresponda. Además, si la computadora deja de mandar mensajes por más de dos segundos, por ejemplo porque el script se cerró o el cable se desconectó, el ESP32 apaga los dos LEDs por su cuenta, para que no se queden encendidos de forma indefinida por accidente.

Vista de forma dinámica, así se comportan la cámara, el script y el ESP32 a lo largo del tiempo, incluyendo el caso en el que el cable se desconecta y actúa el apagado de seguridad:

```mermaid
sequenceDiagram
    participant Cam as Cámara web
    participant PC as deteccion_pc.py
    participant ESP as ESP32 (main.py)
    participant LEDs as LEDs

    loop cada fotograma
        Cam->>PC: fotograma
        PC->>PC: YOLO detecta objetos<br/>del fotograma
        alt el estado cambió desde el último envío
            PC->>ESP: "10\n" / "01\n" / "11\n" / "00\n"
            ESP->>LEDs: enciende o apaga<br/>segun cada caracter
            ESP->>ESP: reinicia el contador<br/>de 2 segundos
        end
    end

    Note over PC,ESP: si el cable se desconecta<br/>o el script se cierra...
    ESP->>ESP: pasan 2s sin mensajes nuevos
    ESP->>LEDs: apaga los dos LEDs<br/>por seguridad
```

## El armado físico

Se necesitan dos LEDs, dos resistencias de 220 ohmios, una protoboard y algunos cables macho a macho o macho a hembra según el tipo de protoboard que se use.

El LED que representa la detección de la silla se conecta a GPIO25, y el que representa la detección del celular se conecta a GPIO26. Ambos son pines de propósito general del ESP32 sin restricciones especiales de arranque ni de memoria flash, así que son una elección segura para esta clase de proyecto. La pata larga del LED, el ánodo, va conectada a través de la resistencia hacia el pin del ESP32, y la pata corta, el cátodo, va directamente a GND. La resistencia puede ir antes o después del LED dentro de esa misma línea, el orden no afecta el resultado porque están en serie.

El valor de 220 ohmios sale de calcular cuánta corriente puede pasar sin forzar ni al LED ni al pin del ESP32. El chip trabaja a 3.3 voltios, y un LED típico cae alrededor de 2 voltios cuando está encendido, así que quedan aproximadamente 1.3 voltios por repartir en la resistencia. Con una resistencia de 220 ohmios la corriente resultante queda cerca de los 6 miliamperios, un valor bajo y seguro tanto para el LED como para el pin, que en el ESP32 no debería superar los 20 miliamperios de forma sostenida.

### Alimentación

Todo el circuito se alimenta desde el mismo cable USB que lleva los datos: la computadora le manda 5 voltios al ESP32 por ese cable, y el regulador que trae la placa integrado los convierte a los 3.3 voltios con los que en realidad trabaja el chip por dentro. No hace falta ninguna fuente externa ni batería para este proyecto, porque tanto el ESP32 como los dos LEDs, que consumen apenas unos miliamperios cada uno, quedan cómodamente dentro de lo que el puerto USB de cualquier computadora puede entregar. Los LEDs en sí no se alimentan desde una fuente aparte, sino directamente desde los pines GPIO25 y GPIO26 del ESP32 puestos en alto, que a 3.3 voltios y con la resistencia de por medio les dan corriente suficiente para encender sin necesitar nada más.

```mermaid
flowchart TD
    USB["Puerto USB de la PC<br/>5V"] --> REG["Regulador de la placa ESP32<br/>5V a 3.3V"]
    REG --> ESP["Chip ESP32<br/>3.3V"]
    ESP -->|"GPIO25 en alto"| R1["Resistencia 220Ω"]
    R1 --> L1["LED silla"]
    L1 --> GND1["GND"]
    ESP -->|"GPIO26 en alto"| R2["Resistencia 220Ω"]
    R2 --> L2["LED celular"]
    L2 --> GND2["GND"]
```

## El código, pin por pin

### `deteccion_pc.py`, en la computadora

Este script no está dividido en funciones porque es corto y todo pasa dentro de un mismo bucle, pero se puede leer por bloques:

- **Configuración inicial** (`PUERTO_SERIAL`, `BAUDIOS`, `OBJETIVOS`): son las tres cosas que alguien tendría que tocar para adaptar el proyecto a otro puerto, otra velocidad o a otros objetos. `OBJETIVOS` es una lista con los nombres exactos que usa el dataset COCO, `"chair"` y `"cell phone"`, y el orden de esa lista es el mismo orden en el que después se arman los dos caracteres que se le mandan al ESP32.
- **Carga del modelo** (`model = YOLO('yolov8n.pt')`): carga la versión "nano" de YOLOv8, la más liviana de la familia. Se eligió esta y no una versión más grande porque el proyecto corre en tiempo real sobre una laptop común, sin GPU dedicada, y la ganancia de precisión de una versión más pesada no compensa la pérdida de velocidad para detectar solo dos clases de objetos.
- **Apertura del puerto serial** (`serial.Serial(...)` y `time.sleep(2)`): abre la conexión con el ESP32 y espera dos segundos antes de mandar nada, porque abrir el puerto serial reinicia al ESP32 y el chip necesita ese tiempo para terminar de arrancar y dejar main.py corriendo y escuchando.
- **Captura de video** (`cv2.VideoCapture(0)` y los `cap.set(...)`): abre la cámara por defecto de la computadora y fija la resolución a 640x480, un tamaño que YOLO procesa rápido sin perder demasiado detalle para objetos del tamaño de una silla o un celular.
- **El bucle principal**: por cada fotograma corre el modelo (`model(frame, verbose=False)`), recorre las cajas detectadas y se queda solo con las que coinciden con `OBJETIVOS`, arma el estado como una cadena de "1" y "0" con esa misma lógica de posición, y solo escribe al puerto serial (`ser.write(...)`) cuando ese estado es distinto al del fotograma anterior.
- **Por qué solo se envía en los cambios de estado**: YOLO corre muchas veces por segundo, y mandar un mensaje serial en cada fotograma saturaría el puerto sin necesidad, porque al ESP32 solo le importa enterarse cuando algo prende o apaga, no que la silla "sigue ahí" fotograma tras fotograma. Guardar `estado_anterior` y comparar es lo que evita ese tráfico de más.

### `esp32_leds.py`, guardado como `main.py` en el ESP32

Tampoco usa funciones propias, corre de arriba a abajo como firmware:

- **Configuración de pines** (`Pin(25, Pin.OUT)` y `Pin(26, Pin.OUT)`): declara GPIO25 y GPIO26 como salidas digitales y los apaga de entrada, para que los LEDs no queden en un estado indefinido justo después de que el chip arranca.
- **`select.poll()` sobre `sys.stdin`**: en MicroPython, el mismo puerto serial que usa Thonny para la consola también se puede leer como `sys.stdin`. Se usa `select.poll()` en vez de simplemente llamar a `sys.stdin.readline()` a secas porque esa segunda opción bloquearía el programa esperando datos, y mientras espera no podría revisar el reloj para el apagado de seguridad. Con `poll(100)` el ESP32 pregunta cada 100 milisegundos si hay algo para leer, y si no hay nada sigue de largo.
- **Validación de la línea** (`len(linea) == 2 and linea[0] in "01" and linea[1] in "01"`): antes de tocar los pines se comprueba que lo que llegó tenga exactamente el formato esperado, dos caracteres que sean "0" o "1". Cualquier mensaje corrupto o incompleto, por ejemplo si el cable se pone ruidoso a mitad de una línea, simplemente se ignora en vez de hacer que el programa truene.
- **`time.ticks_ms()` y `time.ticks_diff(...)`**: MicroPython recomienda estas dos funciones en vez de restar directamente dos `time.time()`, porque el contador interno de milisegundos del chip eventualmente da la vuelta y vuelve a cero, y `ticks_diff` calcula la diferencia correctamente incluso cuando eso pasa, cosa que una resta común no haría.
- **El apagado de seguridad**: cada vez que llega un mensaje válido se guarda el momento en `ultimo_mensaje`. Si pasan más de `TIEMPO_LIMITE_MS` (2000 milisegundos) sin que llegue ninguno, el ESP32 asume que la computadora dejó de hablarle, ya sea porque el script se cerró, se desconectó el cable o la cámara se cayó, y apaga los dos LEDs por su cuenta para que no se queden encendidos "pegados" indefinidamente.

## Qué se modificó frente al código original de YOLO

El script base con el que arrancó este proyecto es el que aparece en la explicación de la arquitectura de YOLO enlazada desde el [README principal del repositorio](../README.md), que solo abre la cámara, corre YOLOv8 sobre cada fotograma y muestra la ventana con las cajas dibujadas encima. A partir de esa base se agregó todo lo que conecta la detección con el mundo físico:

- Se agregó el `import serial` y la apertura del puerto (`PUERTO_SERIAL`, `BAUDIOS`) para hablar con el ESP32, algo que el código original no hacía porque solo mostraba resultados en pantalla.
- Se agregó la lista `OBJETIVOS` para filtrar, de todas las clases que YOLO puede reconocer, solo las dos que le importan a este proyecto, en vez de reaccionar a cualquier objeto detectado.
- Se agregó el seguimiento de `estado_anterior` y el envío condicional por serial, para no saturar el puerto mandando el mismo estado en cada fotograma.
- Se escribió desde cero el firmware `esp32_leds.py`, que no existe en el material original, encargado de recibir esos mensajes, mover los pines físicos y aplicar el apagado de seguridad si la comunicación se corta.
- Se diseñó el circuito físico (elección de pines, resistencias y su valor) que tampoco forma parte del material original, centrado únicamente en la parte de visión artificial.

En resumen, el original se queda en "ver y mostrar en pantalla"; este proyecto le agrega la mitad de "avisar y actuar" sobre hardware real.

## Instalación del entorno en la computadora

Todo el proyecto vive en una sola carpeta, que puede llamarse por ejemplo 3-deteccion-objetos, la misma que contiene este README junto con los dos scripts.

Dentro de esa carpeta se crea un entorno virtual de Python, para mantener las librerías de este proyecto separadas de cualquier otra cosa instalada en el sistema. En Windows, desde PowerShell y parado dentro de la carpeta del proyecto, esto se hace con:

```
python -m venv entorno
.\entorno\Scripts\Activate
```

Con el entorno ya activado, que se nota porque el nombre del entorno aparece entre corchetes al principio de la línea de comandos, se instalan las librerías necesarias:

```
pip install ultralytics opencv-python pyserial
```

Ultralytics trae el modelo de YOLO listo para usarse, opencv-python maneja la cámara y el video, y pyserial es la que permite que el script de Python hable con el ESP32 a través del puerto serial.

## Cómo correrlo

Primero hay que dejar el ESP32 listo. En Thonny, con el ESP32 conectado, se abre el archivo esp32_leds.py de este proyecto y se guarda directamente en el ESP32 con el nombre main.py, usando la opción de guardar en el dispositivo MicroPython en vez de guardar en la computadora. Al guardarlo como main.py el ESP32 lo va a ejecutar automáticamente cada vez que se reinicie o se conecte a la energía, sin depender de que Thonny esté abierto.

Una vez guardado, hay que cerrar la conexión de Thonny con el dispositivo, para que el puerto serial quede libre y la computadora pueda usarlo desde el script de Python. En Thonny esto se hace deteniendo la conexión con el intérprete o simplemente cerrando el programa.

Después, en el script deteccion_pc.py hay que revisar el nombre del puerto serial, que en Windows suele verse como COM3, COM5 o similar, y se puede confirmar abriendo el Administrador de dispositivos y buscando en la sección de puertos. Con el puerto correcto puesto en el script, se corre con el entorno virtual activado:

```
python deteccion_pc.py
```

Se va a abrir una ventana mostrando la cámara con los cuadros de detección dibujados encima, y en cuanto aparezca una silla o un celular frente a la cámara el LED correspondiente en la protoboard debería encenderse casi al instante.

## Demostración en funcionamiento

Así se ve el montaje corriendo de principio a fin, desde la computadora reconociendo la silla haciendo que los LEDs enciednan reaccionando en la protoboard.

![Vista general del montaje con la detección corriendo en pantalla](demo-montaje-1.gif)

Así se ve el montaje corriendo de principio a fin, desde la computadora reconociendo la telefono haciendo que los LEDs enciednan reaccionando en la protoboard.

![Vista general del montaje desde otro ángulo](demo-montaje-2.gif)

La ventana de detección marcando los objetos que YOLO reconoce frente a la cámara, junto con la puntuación de confianza de cada uno, reconociendo la silla y el "telefono":

![Ventana de detección reconociendo persona, silla y mesa](demo-deteccion.gif)

La protoboard en reposo, reconociendo la silla con una sensibilidad muy alta:

![Protoboard con los LEDs apagados en reposo](demo-protoboard-reposo.gif)

Y la protoboard con los LEDs encendidos en el momento en que la cámara reconoce alguno de los objetos configurados:

![Protoboard con los LEDs encendidos al detectar un objeto](demo-protoboard-encendida.gif)
