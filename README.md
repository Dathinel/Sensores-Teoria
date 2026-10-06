# Sensores · Teoría 2026-2

Repositorio con las investigaciones y proyectos de la materia de Sensores, semestre 2026-2. Cada tema tratado en clase vive en su propia carpeta, con su propio README explicando de qué se trata, y al final está el proyecto final del corte. Varios temas están basados en el repositorio [U_Militar](https://github.com/dialejobv/U_Militar/blob/main/README.md).

Todos los README siguen el mismo orden, para que se entiendan sin haber estado en clase: qué pedía la actividad y qué se hizo, qué es cada concepto nuevo, la idea general en diagramas, las conexiones pin a pin (con el voltaje y el porqué de cada pin), qué hace cada archivo, la lógica del código paso a paso y cómo probarlo, con y sin el ESP32 conectado. Además, cada práctica se puede probar sin hardware desde su propia app, con doble clic en el `ABRIR.bat` de su carpeta.

![La app de una práctica, abierta desde su ABRIR.bat](_lanzador/captura-app.png)

## Paso a paso para probar cualquier práctica

1. **Descargar el repo completo.** En GitHub: botón verde **Code** → **Download ZIP**, y descomprimirlo entero (o
   `git clone https://github.com/Dathinel/Sensores-Teoria.git`). Tiene que ser el repo completo, no una carpeta suelta:
   el `ABRIR.bat` de cada práctica usa el motor de la carpeta [`_lanzador/`](./_lanzador/LEEME.md) de la raíz. Puede
   quedar en cualquier carpeta, aunque su ruta tenga espacios o tildes.
2. **Instalar Python** (una sola vez), si no está: [python.org/downloads](https://www.python.org/downloads/), el
   instalador de Windows de 64 bits, con **"Add python.exe to PATH"** marcado y el **"py launcher"** también. Para
   abrir las apps basta **Python 3.9 o más nuevo**; las prácticas que corren Python piden 3.12, 3.13 o 3.14 (cada una
   dice cuál, y si no está, la app explica cuál instalar). Si no hay ningún Python, el propio `ABRIR.bat` lo avisa y
   dice qué hacer.
3. **Doble clic en el `ABRIR.bat` de la práctica** (por ejemplo `7-brazo-robotico-urdf\ABRIR.bat`; en Linux/Mac,
   `sh abrir.sh` dentro de la carpeta). Si Windows pregunta si ejecutar un archivo descargado de internet, elegir
   **Ejecutar**. Se abre una ventana negra que se minimiza sola: es la que mantiene la app funcionando.
4. **Se abre la app**, como un programa, en una ventana maximizada (Edge o Chrome sin barra de direcciones; si no hay
   ninguno, en el navegador por defecto), con un botón **Pantalla completa**. Primero sale "Abriendo la práctica…"
   con una barra; después, a la izquierda, sus secciones: qué hace la práctica, qué pide la actividad (cada punto se
   marca solo al probarlo), cómo funciona, cómo se conecta, **Pruébalo** y los resultados.
5. **Pulsar el botón de una prueba** (Iniciar, Abrir o Levantar). Se ve ahí mismo que se está ejecutando, cuánto
   lleva y cuánto suele tardar, y lo que va diciendo el programa; **Detener** lo para. Si el programa abre su propia
   ventana (PyBullet, OpenCV), la app lo avisa y dice cómo usarla. Si algo falla, un recuadro explica el problema en
   palabras simples (falta Docker, el ESP32 no está conectado, la cámara la usa otra app…) y qué hacer.
6. **La primera vez**, en las prácticas con Python, el botón prepara solo el `entorno/` de Python de esa práctica
   (crea el entorno e instala sus librerías), con una barra de progreso y lo que va haciendo; puede tardar unos
   minutos (con PyBullet, 10-15). Las siguientes veces arranca enseguida.
7. **Para terminar**, cerrar la ventana de la app y la ventana negra (al cerrarla se detiene también lo que siga
   corriendo dentro de la app). Si nadie usa la app en 10 minutos y no hay nada en marcha, se cierra sola. Abrir el
   `ABRIR.bat` de otra práctica mientras una está abierta reutiliza el mismo motor y solo abre otra ventana.

**Requisitos especiales** (lo que no los necesita, como los simuladores en el navegador, los videos y las capturas,
funciona igual sin ellos):

- **Temas 1, 2, 5 y 6**: no instalan nada. El tema 6 (gestos) necesita **Chrome o Edge** (Web Serial) e internet la
  primera vez para el modelo de MediaPipe; la webcam es opcional.
- **Tema 3**: instala YOLO con PyTorch (una descarga grande) y la primera vez baja el modelo `yolov8n.pt` (6 MB). La
  webcam es opcional: también se prueba con fotos de ejemplo.
- **Tema 4**: el micrófono y la clave de DeepSeek son opcionales (sin clave, un intérprete por palabras clave; con
  clave, copiar `.env.example` como `.env`, que nunca se sube).
- **Temas 7, 8, 9, 10 y el proyecto final**: usan **PyBullet**, que en Windows se compila la primera vez; para eso
  hacen falta las **Build Tools de Visual Studio con C++** (2-3 GB, una sola vez). La app lo avisa antes y muestra el
  comando para instalarlas:
  `winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"`.
  El tema 8 usa además TensorFlow, que necesita **Python 3.13 o 3.12** (todavía no 3.14). El tema 9 baja la primera
  vez las mallas de Baxter y Atlas (`descargar_modelos.py`).
- **Temas 10 y 11**: los laboratorios necesitan **Docker Desktop** abierto (que diga "Engine running"); la app lo
  comprueba antes. El dashboard del tema 11 queda en `http://127.0.0.1:8180`.
- **Internet la primera vez**: para instalar las librerías de Python y, en las apps, para las fuentes y para
  mostrar los README con sus diagramas (sin internet se ven como texto).

**Sin la app**: cada README trae, en "Cómo probarlo", los comandos para correr todo desde una consola, y cómo
probarlo con el hardware real (o, si se entregó en simulación, lo dice). `python _lanzador/lanzador.py`, sin nada más,
abre una página con la lista de todas las apps, para saltar de una a otra.

## Temas

### 1. [Investigación del ESP32](./1-esp32-investigacion)
Investigación a fondo sobre el ESP32: de dónde viene la idea del microcontrolador, la historia de Espressif y el ESP8266 detrás, y cómo está armado el chip por dentro (pinout, ADC/DAC, periféricos). Cierra con cómo se programa, su costo ambiental y para qué se usa en la práctica, más un script corto que comprueba la ficha técnica en la placa real. La app lo presenta como un lector por capítulos.

Abrir: doble clic en [`1-esp32-investigacion/ABRIR.bat`](./1-esp32-investigacion/ABRIR.bat).

### 2. [Lenguajes: por qué Thonny](./2-lenguajes-thonny)
Qué es Thonny, cómo se conecta con MicroPython, y por qué programar el ESP32 con MicroPython es un camino distinto a hacerlo con C/C++ vía Arduino. Incluye cómo instalar MicroPython en el ESP32, una comparación directa entre ambos enfoques y el mismo código en los dos lenguajes (un semáforo que mide en microsegundos cuánto tarda cada uno y un display de siete segmentos en Wokwi). Basado en [Instalación de Thonny — NODEMCU V3 ESP8266](https://github.com/dialejobv/U_Militar/blob/main/1%29%20Instalaci%C3%B3n%20Thonny/NODEMCU%20V3%20ESP8266.md).

Abrir: doble clic en [`2-lenguajes-thonny/ABRIR.bat`](./2-lenguajes-thonny/ABRIR.bat).

### 3. [Detección de objetos](./3-deteccion-objetos)
Un modelo YOLO detecta objetos (silla, celular) desde la cámara de la computadora y le avisa al ESP32 por puerto serial para encender LEDs físicos en una protoboard. Con `--carro-moto` detecta en su lugar un carro y una moto de juguete (la directiva alternativa). Incluye el armado del circuito, el protocolo de comunicación con apagado de seguridad, un modo que funciona sin el ESP32 y gifs de la demo funcionando. Sin webcam se prueba con fotos de ejemplo (`deteccion_pc.py --imagen`), y sin instalar nada con `preview.html`. Basado en [Explicación de la arquitectura YOLO](https://github.com/dialejobv/U_Militar/blob/main/2%29%20Yolo/Explicaci%C3%B3n_Arq_YOLO.md).

Abrir: doble clic en [`3-deteccion-objetos/ABRIR.bat`](./3-deteccion-objetos/ABRIR.bat).

### 4. [Chatbot: asistente de voz](./4-chatbot-asistente-voz)
Comandos de voz que encienden y apagan LEDs en el ESP32: la voz se transcribe a texto, un modelo de lenguaje vía la API de DeepSeek interpreta la intención y la computadora le manda la orden al ESP32 por puerto serial, que confirma cada orden con un `OK`. Funciona también sin ESP32, sin micrófono (escribiendo la frase, `comando_voz.py --texto`) o sin clave de la API (intérprete por palabras clave, `--sin-clave`), y sin instalar nada con `preview.html`. Incluye el armado del circuito, el manejo seguro de la API key y gifs de la demo funcionando. Basado en [chatbot.py](https://github.com/dialejobv/U_Militar/blob/main/3%29%20chatbot/chatbot.py).

Abrir: doble clic en [`4-chatbot-asistente-voz/ABRIR.bat`](./4-chatbot-asistente-voz/ABRIR.bat).

### 5. [Parcial: peces en el osciloscopio (modo XY)](./5-parcial-figuras-lissauer)
Parcial del primer corte, a partir de las figuras de Lissajous. El ESP32 usa sus dos salidas DAC para dibujar peces en un osciloscopio puesto en modo XY, combinando elipses, líneas y curvas Bezier para armar la figura. Incluye dos versiones del script (un pez o tres) y gifs mostrando la figura trazándose en pantalla. Sin placa ni osciloscopio, `preview.html` simula la pantalla XY con la misma geometría (un pez, tres peces o una Lissajous).

Abrir: doble clic en [`5-parcial-figuras-lissauer/ABRIR.bat`](./5-parcial-figuras-lissauer/ABRIR.bat).

### 6. [Control de iluminación por gestos](./6-control-de-led-mediante-gestos)
Una página web reconoce gestos de la mano en vivo con MediaPipe Gesture Recognizer y le manda el comando al ESP32 por Web Serial para controlar tres LEDs por PWM (intensidad según el gesto) y dos modos de secuencia. Sin ESP32 ni cámara se puede probar igual con los botones manuales, que encienden un espejo de los LEDs en la propia página; basta con Chrome o Edge. Basado en la Actividad 4 asignada en clase, usando [MediaPipe Gesture Recognizer](https://google-ai-edge.github.io/mediapipe-samples-web/#/vision/gesture_recognizer).

Abrir: doble clic en [`6-control-de-led-mediante-gestos/ABRIR.bat`](./6-control-de-led-mediante-gestos/ABRIR.bat).

### 7. [Brazo robótico: control por teclado (jog) + simulación URDF](./7-brazo-robotico-urdf)
Un teclado matricial 4x4, conectado directo a 8 GPIO del ESP32, mueve, en tiempo real, un brazo de 2 grados de libertad con pinza simulado en PyBullet a partir del `brazo.urdf` compartido en clase — tipo "teach pendant": mantener una tecla presionada mueve una articulación mientras se sostiene. Si no hay ESP32 conectado, la misma ventana de PyBullet trae los mismos botones de jog para probar sin hardware, y `preview.html` tiene el teclado clicable en el navegador. Basado en [brazo.urdf](https://github.com/dialejobv/U_Militar/blob/main/8%29%20Brazo_URDF/brazo.urdf).

Abrir: doble clic en [`7-brazo-robotico-urdf/ABRIR.bat`](./7-brazo-robotico-urdf/ABRIR.bat).

### 8. [Dígitos: brazo que dibuja + visión que reconoce](./8-digitos-brazo-y-vision)
Dos puntos: un teclado matricial (directo a 8 GPIO) y una LCD por I2C eligen un dígito que el brazo del tema 7 dibuja moviendo sus articulaciones; y por otro lado, una CNN entrenada sobre MNIST reconoce un dígito escrito a mano y lo muestra en una OLED, reenviado entre dos ESP32 (maestro/esclavo). El modelo entrenado ya viene incluido, y sin cámara el dígito se dibuja con el mouse (`reconocer_digito.py --mouse`). Basado en [brazo.urdf](https://github.com/dialejobv/U_Militar/blob/main/8%29%20Brazo_URDF/brazo.urdf) y en el ejemplo de [OpenCV](https://github.com/dialejobv/U_Militar/blob/main/10%29%20Open_Cv).

Abrir: doble clic en [`8-digitos-brazo-y-vision/ABRIR.bat`](./8-digitos-brazo-y-vision/ABRIR.bat).

### 9. [Taller segundo corte: consolas de mando con ESP32 para simulaciones en PyBullet](./9-taller-segundo-corte)
Un solo teclado matricial 4x4, conectado directo a GPIO y con el mismo firmware de ESP32 sin cambios, controla tres simulaciones distintas: cinco drones en formación en V que vuelan con física real (gravedad y la fuerza de sus 4 motores, con un control en cascada como el de gym-pybullet-drones) entre tres puntos A, B y C, a mano o con una misión automática A→B→C; el robot **Baxter** real, que mueve sus dos brazos por cinemática inversa y agarra y lleva un cubo; y el humanoide **Atlas** real, que mueve sus juntas, hace poses y camina con física real, con un asistente de equilibrio que se prende y se apaga para comparar cómo se comporta con y sin ayuda. Las mallas de los dos robots se bajan con `descargar_modelos.py`. Basado en [gym-pybullet-drones](https://github.com/utiasDSL/gym-pybullet-drones) y en [pybullet_robots](https://github.com/erwincoumans/pybullet_robots) (`baxter_ik_demo.py` y `atlas.py`).

Abrir: doble clic en [`9-taller-segundo-corte/ABRIR.bat`](./9-taller-segundo-corte/ABRIR.bat).

### 10. [Enjambre de carritos con algoritmo de hormigas (ACO) y gemelo digital](./10-enjambre-algoritmo-hormigas)
Tres carritos con ESP32 buscan la ruta más corta en un laberinto tipo almacén con optimización por colonia de hormigas: el algoritmo corre dentro de cada ESP32, los tres comparten la feromona por UDP en una red propia (el nodo 1 hace de punto de acceso) sin servidor central, y un gemelo digital en PyBullet, dentro de Docker, replica lo que hacen con tres robots virtuales y graba un video. El mismo laberinto (`maze.json`) alimenta el firmware y la simulación, y el ACO en C++ y en Python dan las mismas rutas bit a bit. Incluye un modo sin hardware, un emulador de los tres nodos y quince pruebas de red, algoritmo y gemelo. Sin los carritos se prueba con el emulador y el gemelo, o con `docker compose run --rm simulacion`.

Abrir: doble clic en [`10-enjambre-algoritmo-hormigas/ABRIR.bat`](./10-enjambre-algoritmo-hormigas/ABRIR.bat).

### 11. [Zonas virtualizadas (VLAN) con ESP32, PyBullet, Docker y plano de administración](./11-zonas-virtualizadas-esp32-vlan)
Un laboratorio de 16 contenedores Docker repartidos en tres redes aisladas que hacen de VLAN. En la zona gamer, un servidor de pista en PyBullet corre una carrera con tres carros autónomos y tres carros de jugador, cada uno manejado por una ESP32 maestra con joystick. En la zona robótica, Spot, Pepper y NAO siguen en simulación (real-to-sim) los potenciómetros de su propia ESP32. Un router Alpine con FRR e iptables deja que el plano de administración (broker MQTT, monitor de latencia, jitter y disponibilidad, y un dashboard) observe las dos zonas sin que ellas se vean entre sí. Una ESP32 esclava refleja con seis LEDs el estado de cada contenedor. Se entrega completo en simulación: siete ESP32 emulados hacen lo mismo que el firmware, y el montaje de las placas está en 3D. Se prueba con `preview.html`, con `docker compose --profile emulado up -d --build` y el dashboard en `127.0.0.1:8180` (que enlaza los visores de la pista y los robots), o desde su app (`ABRIR.bat`), que levanta el laboratorio, lo muestra en vivo y lo detiene. Incluye pruebas de aislamiento, disponibilidad y red con retardo y carga, un `preview.html` que simula el laboratorio en el navegador y las imágenes publicadas en Docker Hub. Basado en la Actividad 8 asignada en clase, con [rl-baselines3-zoo](https://github.com/DLR-RM/rl-baselines3-zoo), [rex-gym](https://github.com/nicrusso7/rex-gym) y [humanoid-gym](https://github.com/0aqz0/humanoid-gym) como referencias.

Abrir: doble clic en [`11-zonas-virtualizadas-esp32-vlan/ABRIR.bat`](./11-zonas-virtualizadas-esp32-vlan/ABRIR.bat).

### ★ [Proyecto final: Sistema de Logística de Monedas Inteligentes](./proyecto-final)
Segundo parcial (grupo 7: **detector de elementos de monedas y vasos**). Una cinta de cuatro estaciones filtra monedas colombianas —rechaza botones, arandelas, bloques y monedas de otros países con sensores capacitivo/inductivo, geometría y visión, y cruza el diámetro medido con la clase reconocida— y manda todo rechazo, con su causa, a una sola bandeja. Las aceptadas se guardan en un almacén tipo revólver y se empacan en vasos tapados de una sola denominación, vigilados por una cámara que descubre si alguien retira, cambia o llena un vaso, y por una cortina que frena la prensa si entra una mano. Un carro con ESP-NOW va de reversa al muelle, sigue la línea, esquiva tres muros, llega a la meta y vuelve solo. Todo corre con física real en PyBullet (con el error de cada sensor simulado), se ve en un visor 3D portable que `visor.bat` abre junto con el dashboard de Streamlit, y un asistente responde por voz o texto (DeepSeek, o un modelo local sin internet). El firmware de los dos ESP32 está en MicroPython y comparte la lógica de control con la simulación; falta el montaje físico.

Abrir: doble clic en [`proyecto-final/ABRIR.bat`](./proyecto-final/ABRIR.bat).

![Arquitectura del enunciado](./proyecto-final/docs/enunciado/1-arquitectura-general.png)

## Cómo está organizado el repo

```
Sensores-Teoria/
├─ README.md                 este archivo: cómo usar el repo y un párrafo por tema
├─ _lanzador/                el motor de las apps (no es una práctica): ver _lanzador/LEEME.md
│  ├─ lanzador.py            servidor local (solo 127.0.0.1) que abre cada app y lanza sus pruebas
│  ├─ apps-comun/            app.js y app.css: lo que comparten todas las apps
│  └─ revisar_enlaces.py     revisa que los enlaces, imágenes y anclas de todos los .md funcionen en GitHub
├─ N-nombre-del-tema/        una carpeta por tema (1 a 11) y proyecto-final/
│  ├─ README.md              la explicación completa (lo que lee el profesor)
│  ├─ ABRIR.bat / abrir.sh   doble clic: abre la app de la práctica
│  ├─ probar.json            qué pruebas ofrece la app (las únicas que el lanzador ejecuta)
│  ├─ app/                   la app de la práctica (en el proyecto final, app-practica/)
│  ├─ img/, video/           capturas, fotos del montaje, gifs y videos de la demo
│  ├─ preview.html           simulador en el navegador, sin instalar nada (en los temas que lo tienen)
│  ├─ *.py                   el código del PC (y el de MicroPython que va al ESP32)
│  └─ firmware/              el firmware del ESP32 (.ino o MicroPython), en los temas que lo separan
└─ LICENSE
```

Lo que no se sube (lo excluye el `.gitignore`): los `entorno/` de Python (los crea la app la primera vez), los `.env`
con claves, las bases de datos locales, las salidas que se regeneran al correr las pruebas y los documentos de entrega
de la universidad.

---

Más carpetas se irán agregando a medida que se asignen nuevos temas en clase.
