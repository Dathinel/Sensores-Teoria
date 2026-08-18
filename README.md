# Sensores - Teoría 2026-2

Repositorio con las investigaciones y proyectos de la materia de Sensores, semestre 2026-2. Cada tema tratado en clase vive en su propia carpeta, con su propio README explicando de qué se trata. Varios temas están basados en el repositorio [U_Militar](https://github.com/dialejobv/U_Militar/blob/main/README.md).

## Temas

### 1. [esp32-investigacion](./esp32-investigacion)
Investigación a fondo sobre el ESP32: de dónde viene la idea del microcontrolador, la historia de Espressif y el ESP8266 detrás, y cómo está armado el chip por dentro (pinout, ADC/DAC, periféricos). Cierra con cómo se programa, su costo ambiental y para qué se usa en la práctica.

### 2. [Lenguajes: por qué Thonny](./lenguajes-thonny)
Qué es Thonny, cómo se conecta con MicroPython, y por qué programar el ESP32 con MicroPython es un camino distinto a hacerlo con C/C++ vía Arduino. Incluye una comparación directa entre ambos enfoques y cuándo conviene cada uno. Basado en [Instalación de Thonny — NODEMCU V3 ESP8266](https://github.com/dialejobv/U_Militar/blob/main/1%29%20Instalaci%C3%B3n%20Thonny/NODEMCU%20V3%20ESP8266.md).

### 3. [Detección de objetos](./deteccion-objetos)
Un modelo YOLO detecta objetos (silla, celular) desde la cámara de la computadora y le avisa al ESP32 por puerto serial para encender LEDs físicos en una protoboard. Incluye el armado del circuito, el protocolo de comunicación y gifs de la demo funcionando. Basado en [Explicación de la arquitectura YOLO](https://github.com/dialejobv/U_Militar/blob/main/2%29%20Yolo/Explicaci%C3%B3n_Arq_YOLO.md).

### 4. [Chatbot: asistente de voz](./chatbot-asistente-voz)
Comandos de voz que encienden y apagan LEDs en el ESP32: la voz se transcribe a texto, un modelo de lenguaje vía la API de DeepSeek interpreta la intención y la computadora le manda la orden al ESP32 por puerto serial. Incluye el armado del circuito, el manejo seguro de la API key y gifs de la demo funcionando.

### [parcial-figuras-lissauer](./parcial-figuras-lissauer)
El ESP32 usa sus dos salidas DAC para dibujar peces en un osciloscopio puesto en modo XY, combinando elipses, líneas y curvas Bezier para armar la figura. Incluye dos versiones del script (un pez o tres) y gifs mostrando la figura trazándose en pantalla.

---

Más carpetas se irán agregando a medida que se asignen nuevos temas en clase.
