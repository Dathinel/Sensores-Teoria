# Sensores - Teoría 2026-2

Repositorio con las investigaciones y proyectos de la materia de Sensores, semestre 2026-2. Cada tema tratado en clase vive en su propia carpeta, con su propio README explicando de qué se trata.

## Temas

### [esp32-investigacion](./esp32-investigacion)
Investigación a fondo sobre el ESP32: de dónde viene la idea del microcontrolador, la historia de Espressif y el ESP8266 detrás, y cómo está armado el chip por dentro (pinout, ADC/DAC, periféricos). Cierra con cómo se programa, su costo ambiental y para qué se usa en la práctica.

### [thonny-y-lenguajes](./thonny-y-lenguajes)
Qué es Thonny, cómo se conecta con MicroPython, y por qué programar el ESP32 con MicroPython es un camino distinto a hacerlo con C/C++ vía Arduino. Incluye una comparación directa entre ambos enfoques y cuándo conviene cada uno.

### [yolo-deteccion-fisica](./yolo-deteccion-fisica)
Un modelo YOLO detecta objetos (silla, celular) desde la cámara de la computadora y le avisa al ESP32 por puerto serial para encender LEDs físicos en una protoboard. Incluye el armado del circuito, el protocolo de comunicación y gifs de la demo funcionando.

### [asistente-voz-leds](./asistente-voz-leds)
Comandos de voz que encienden y apagan LEDs en el ESP32: la voz se transcribe a texto, un modelo de lenguaje vía la API de DeepSeek interpreta la intención y la computadora le manda la orden al ESP32 por puerto serial. Incluye el armado del circuito, el manejo seguro de la API key y gifs de la demo funcionando.

### [peces-osciloscopio](./peces-osciloscopio)
El ESP32 usa sus dos salidas DAC para dibujar peces en un osciloscopio puesto en modo XY, combinando elipses, líneas y curvas Bezier para armar la figura. Incluye dos versiones del script (un pez o tres) y gifs mostrando la figura trazándose en pantalla.

---

Más carpetas se irán agregando a medida que se asignen nuevos temas en clase.
