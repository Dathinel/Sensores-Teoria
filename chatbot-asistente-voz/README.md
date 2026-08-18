# Chatbot: asistente de voz

## La idea general

Este proyecto enciende y apaga dos LEDs conectados a un ESP32 a partir de comandos hablados. Una persona habla frente al micrófono de la computadora, lo que dice se transcribe a texto, ese texto se le manda a un modelo de lenguaje a través de la API de DeepSeek, el modelo interpreta qué se le está pidiendo, y la computadora traduce esa interpretación en una orden concreta que le manda al ESP32 por cable USB.

```mermaid
flowchart LR
    Microfono[Microfono] --> Transcripcion[Reconocimiento de voz]
    Transcripcion -->|texto| DeepSeek[API de DeepSeek]
    DeepSeek -->|intencion en JSON| PC[Script en Python]
    PC -->|Cable USB, puerto serial| ESP32[ESP32 con MicroPython]
    ESP32 --> LedRojo[LED rojo]
    ESP32 --> LedAzul[LED azul]
```

La API de DeepSeek vive en un servidor en la nube, así que llamarla siempre necesita internet en ese momento puntual. El ESP32 en cambio no necesita ninguna conexión inalámbrica propia, se queda escuchando el cable USB todo el tiempo sin saber ni necesitar saber de dónde viene la orden que recibe.

## El armado físico

Se necesitan dos LEDs, dos resistencias de 220 ohmios, una protoboard y algunos cables. El LED rojo se conecta a GPIO25 y el LED azul a GPIO26, ambos pines de propósito general del ESP32 sin restricciones especiales de arranque ni de memoria flash. En cada LED, la pata larga, el ánodo, va conectada a través de su resistencia hacia el pin del ESP32 correspondiente, y la pata corta, el cátodo, va directamente a GND.

El valor de 220 ohmios sale de calcular cuánta corriente puede pasar sin forzar ni al LED ni al pin del ESP32. El chip trabaja a 3.3 voltios, un LED típico cae alrededor de 2 voltios cuando está encendido, y con esa resistencia la corriente resultante queda cerca de los 6 miliamperios, un valor bajo y seguro tanto para el LED como para el pin.

## Por qué usar un modelo de lenguaje en vez de simplemente buscar palabras clave

Se podría resolver esto revisando si el texto transcrito contiene la palabra encender o apagar junto con el color mencionado, pero ese enfoque se rompe apenas alguien cambia ligeramente la forma de pedirlo. Prende el rojo, activa la luz roja, dale al led rojo, enciéndeme el de color rojo, todas esas frases significan exactamente lo mismo pero ninguna coincide con las otras palabra por palabra, y escribir reglas para cubrir cada variación posible del lenguaje hablado es una tarea que crece sin fin. Delegarle esa interpretación a un modelo de lenguaje como el de DeepSeek resuelve ese problema de raíz, porque el modelo entiende la intención sin importar cómo esté formulada la frase, y además distingue cuándo la persona está pidiendo algo sobre los LEDs de cuando está diciendo algo completamente distinto que no debería activar nada.

El detalle técnico que hace que esto funcione de forma confiable es no dejar que el modelo responda con una frase libre en lenguaje natural, porque un programa no puede interpretar de forma segura una respuesta como listo, ya prendí el rojo para ti. En vez de eso, la petición a la API se hace pidiéndole explícitamente que devuelva un objeto en formato JSON, usando el parámetro response_format que ofrece la API para forzar ese comportamiento, con instrucciones precisas sobre qué claves puede incluir y qué significa cada una. El script en la computadora nunca necesita entender lenguaje natural por su cuenta, solo lee ese JSON estructurado y actúa según lo que diga.

Otro detalle importante del diseño es que el modelo solo incluye en su respuesta las claves que el comando menciona explícitamente. Si alguien dice enciende el rojo, la respuesta trae únicamente la clave del LED rojo, sin mencionar el azul para nada, y el script en la computadora mantiene por su cuenta un estado guardado de cómo está cada LED, actualizando solo la parte que cambió. Esto evita que el modelo asuma por error que hay que apagar algo que la persona nunca mencionó, simplemente porque no lo nombró en esa frase.

## El show de luces

Si el comando de voz incluye algo como haz un show de luces o pon un espectáculo, el modelo devuelve la clave show en vez de las claves de los LEDs individuales, y el script en la computadora le manda al ESP32 la palabra SHOW en vez de las dos cifras que normalmente indican el estado de cada LED.

Del lado del ESP32, antes de arrancar la secuencia de parpadeo, el programa guarda en qué estado estaba cada LED en ese momento. Después hace alternar el LED rojo y el azul varias veces seguidas, con una pequeña pausa entre cada cambio, y al terminar la secuencia devuelve ambos LEDs exactamente al estado en el que estaban antes del show, en vez de dejarlos apagados. Esto importa porque si el rojo ya estaba encendido antes de pedir el show, se espera que siga encendido después de que termine el espectáculo, no que se apague solo porque el show terminó.

## Preparar el entorno

Todo esto va en su propia carpeta, con su propio entorno virtual de Python, para mantener sus librerías separadas de cualquier otra cosa instalada en el sistema. Un detalle importante antes de crear ese entorno, tiene que ser con Python 3.12 y no con una versión más nueva como 3.13 o 3.14, por una razón concreta que se explica más abajo en la sección de problemas, así que el comando para crear el entorno queda apuntando a esa versión específica:

```
py -3.12 -m venv entorno
.\entorno\Scripts\Activate
pip install openai pyserial SpeechRecognition pyaudio python-dotenv
```

Cada una de estas librerías cubre una parte distinta del proceso. La librería openai es la que habla con la API de DeepSeek, y funciona porque DeepSeek diseñó su API para ser compatible con el mismo formato que usa OpenAI, así que el mismo cliente sirve para ambas, solo cambiando la dirección del servidor al que apunta y la clave que usa para autenticarse. SpeechRecognition maneja la parte de convertir audio en texto, y cuando se usa su función recognize_google, manda el audio grabado a los servidores de reconocimiento de voz de Google de forma gratuita, sin necesitar una clave de API propia para eso, lo cual significa que esa parte también depende de tener conexión a internet en el momento de hablar. pyaudio es la librería que le da a Python acceso directo al micrófono del sistema operativo, y python-dotenv es la que permite cargar la clave de la API de DeepSeek desde un archivo aparte en vez de dejarla escrita directamente dentro del código fuente.

La clave de la API nunca debe quedar escrita dentro de un archivo que se vaya a subir a GitHub, porque el repositorio es público y cualquiera podría copiarla y empezar a hacer llamadas a la API a nombre tuyo, consumiendo el saldo de tu cuenta sin que lo sepas. Para evitar eso, la clave se guarda en un archivo llamado .env, dentro de esta misma carpeta, con una sola línea así:

```
DEEPSEEK_API_KEY=tu_clave_aqui
```

Ese archivo .env no se sube nunca al repositorio, y para eso hay que agregar la línea .env al archivo .gitignore de la raíz del repositorio, así git lo ignora automáticamente sin importar en qué carpeta aparezca. El archivo .env.example que sí viene incluido en esta carpeta sirve como plantilla, mostrando qué formato debe tener el archivo real sin exponer ninguna clave verdadera.

En Windows, instalar pyaudio a veces falla directamente con pip porque el paquete necesita compilar código nativo en el sistema, algo para lo que normalmente hace falta tener herramientas de compilación instaladas que la mayoría de computadoras no traen por defecto. Si eso pasa, la alternativa más simple es instalar una versión ya compilada del paquete con:

```
pip install pipwin
pipwin install pyaudio
```

## Cómo correrlo

Con el ESP32 conectado por USB, se abre el archivo esp32_voz.py de esta carpeta en Thonny y se guarda directamente en el dispositivo con el nombre main.py, para que se ejecute automáticamente cada vez que el ESP32 se reinicie o se conecte a la energía. Guardado ese archivo, hay que cerrar la conexión de Thonny con el dispositivo, porque el puerto serial solo puede estar abierto por un programa a la vez, y el siguiente paso necesita ese mismo puerto libre para la computadora.

Del lado de la computadora, con el entorno virtual activado y el archivo .env ya con la clave puesta, se revisa que el número de puerto serial dentro de comando_voz.py corresponda al que muestra el Administrador de dispositivos, y se corre con:

```
python comando_voz.py
```

El script queda esperando a que se presione Enter para empezar a escuchar por el micrófono. Al decir el comando en voz alta, en cuanto se detecta que la persona dejó de hablar la grabación se corta sola y arranca el proceso completo, primero la transcripción, después la consulta a la API de DeepSeek, y finalmente el envío de la orden resultante al ESP32. Todo ese recorrido toma normalmente uno o dos segundos, la mayor parte del tiempo consumida por la respuesta de la API, así que el encendido del LED no es instantáneo pero sí bastante rápido para tratarse de una cadena que pasa por dos servicios en internet antes de llegar al chip.

## Problemas encontrados

Poner esto a funcionar en Windows tomó varias vueltas, y vale la pena dejarlas anotadas porque cualquiera que repita el proyecto probablemente se va a topar con las mismas.

La primera fue correr el script con el Python global del sistema en vez del que vive dentro del entorno virtual del proyecto. Aunque las librerías ya estaban instaladas dentro de entorno, al lanzar el script apuntando directamente a un intérprete distinto, como el de una instalación global de Python en otra carpeta, ese intérprete no tiene ni idea de que esas librerías existen, y el script revienta apenas intenta importar la primera de ellas.

La segunda fue una instalación parcial de las cinco librerías necesarias. Al instalarlas todas en una sola línea con pip, si una de ellas falla a mitad de camino, como pyaudio compilando desde código fuente, pip puede cortar el resto de la lista antes de llegar a instalar las que faltaban, dejando el entorno con solo una parte de lo necesario sin que sea evidente a simple vista.

La tercera fue confundir el archivo .env.example con el archivo .env real. python-dotenv por defecto solo lee un archivo que se llame exactamente .env, así que tener nada más la plantilla de ejemplo en la carpeta hace que la clave nunca se cargue, y el script truena con un KeyError al intentar leer la variable de entorno que nunca quedó definida.

La cuarta fue un error de edición donde terminó pegado el valor real de la clave de la API en el lugar del código donde debía ir el nombre de la variable de entorno, dentro de os.environ. Python entonces intenta buscar una variable de entorno que se llame literalmente igual a la clave, no la encuentra porque eso no es un nombre de variable sino un valor, y truena con el mismo tipo de KeyError. Esto además dejó la clave real expuesta por fuera del archivo .env, así que tocó revocarla y generar una nueva.

La quinta, y la más profunda, fue que pyaudio no lograba instalarse en el entorno creado con Python 3.14. En PyPI, PyAudio 0.2.14 todavía no tiene wheels precompilados para Python 3.14 por ser una versión demasiado nueva, así que pip intenta compilarlo desde el código fuente, y esa compilación necesita el header portaudio.h de la librería PortAudio instalada en el sistema, que no está presente, así que la instalación termina en un error de compilador sin encontrar ese archivo. La solución fue crear el entorno virtual del proyecto apuntando explícitamente a una versión de Python donde sí existen esos wheels ya compilados, en este caso Python 3.12, dejando la instalación global de Python 3.14 intacta para todo lo demás.

La sexta fue un ModuleNotFoundError sobre pydantic_core, la parte binaria compilada de la que depende pydantic y, a través de ella, la librería openai. La carpeta del proyecto vivía dentro de OneDrive, y la sincronización en tiempo real de OneDrive puede interferir justo cuando pip está escribiendo muchos archivos pequeños de golpe durante una instalación, dejando algún archivo binario a medias o movido en mal momento. Reinstalar el paquete forzando una descarga limpia, y sacar la carpeta del proyecto de OneDrive hacia una ruta local normal, resolvió el problema de fondo.

## Demostración en funcionamiento

Con todo lo anterior resuelto, esta es una corrida real dando los comandos por voz uno detrás de otro, prender el rojo, prender también el azul, pedir el show de luces, y apagar los dos al final.

![Protoboard con el LED rojo encendido tras pedirlo por voz](demo-led-rojo.gif)

![Protoboard con los dos LEDs encendidos tras pedir que se prenda también el azul](demo-dos-leds.gif)

![Protoboard durante el show de luces, con el LED azul encendido en ese instante de la secuencia](demo-show-luces-azul.gif)

![Protoboard durante el show de luces, con el LED rojo encendido en ese instante de la secuencia](demo-show-luces-rojo.gif)
