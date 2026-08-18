# Lenguajes: por qué Thonny

## Qué es Thonny

Thonny es un entorno de desarrollo pensado originalmente para enseñar Python a gente que nunca había programado antes. Lo creó Aivar Annamaa en la Universidad de Tartu, en Estonia, y salió como versión estable en 2015, después de que su creador pasara varios años dando clases de Python a principiantes y viendo de primera mano en qué se atascaban. Por eso Thonny trae cosas como un depurador visual que muestra paso a paso cómo cambian las variables mientras el programa corre, algo pensado para quien recién está entendiendo cómo funciona el flujo de un programa.

El soporte para MicroPython llegó después, primero como un plugin para la placa BBC micro:bit y luego, ya en la versión 3.0 de Thonny, como soporte general para cualquier placa que corra MicroPython, entre ellas el ESP32, el ESP8266 y la Raspberry Pi Pico. Esto convirtió a Thonny en una puerta de entrada bastante natural para pasar de programar en la computadora a programar microcontroladores, sin cambiar de herramienta ni de lenguaje.

## Cómo se relaciona esto con Arduino y con C++

La diferencia entre usar el Arduino IDE y usar Thonny no es una simple cuestión de gustos, es una diferencia de fondo en cómo el chip termina ejecutando el código.

```mermaid
flowchart LR
    subgraph Arduino[Camino Arduino IDE]
        A1[Código en C o C++] --> A2[Compilador]
        A2 --> A3[Archivo binario]
        A3 --> A4[Se graba en la memoria flash del ESP32]
        A4 --> A5[El chip ejecuta instrucciones de máquina directamente]
    end

    subgraph Thonny[Camino Thonny]
        B1[Firmware de MicroPython ya grabado en el chip] --> B2[Thonny se conecta por el puerto serial]
        B2 --> B3[Se envía código Python]
        B3 --> B4[El interprete de MicroPython lo lee y ejecuta linea por linea]
    end
```

En el camino de Arduino, el código en C o C++ se compila por completo antes de tocar el chip, se convierte en instrucciones de máquina y ese binario queda grabado en la memoria flash. El ESP32 arranca y ejecuta directamente esas instrucciones, sin ningún interprete de por medio, lo que lo hace muy rápido y muy eficiente en el uso de memoria.

En el camino de Thonny, lo primero que tiene que pasar es que el ESP32 tenga instalado el firmware de MicroPython, que en la práctica es un programa en C compilado que actúa como interprete de Python dentro del chip. Una vez ese firmware está instalado, Thonny se conecta al chip por el mismo puerto serial que usaría el Arduino IDE, pero en lugar de mandar un binario compilado manda el código Python tal cual, línea por línea si se quiere, y ese interprete dentro del chip lo va leyendo y ejecutando al vuelo.

Por eso no tiene sentido preguntarse por qué usar Arduino y no Thonny como si fueran dos programas que compiten por lo mismo, porque en el fondo apuntan a dos formas distintas de trabajar con el mismo chip. El ESP32 solo puede tener un firmware corriendo a la vez, así que instalar MicroPython para usar Thonny reemplaza por completo el firmware que el Arduino IDE necesita para funcionar, y viceversa. La elección real está entre programar con un lenguaje compilado que se convierte en instrucciones nativas, o programar con un lenguaje interpretado que corre dentro de un intérprete ya instalado en el chip.

## Por qué MicroPython y no Python normal

Python normal, el que corre en una computadora, necesita un sistema operativo completo detrás, con varios megabytes de memoria disponibles y un procesador bastante más potente que el de un microcontrolador. El ESP32 tiene apenas algunos cientos de kilobytes de RAM, así que instalar el Python de una computadora tal cual no es una opción.

MicroPython es una reimplementación del lenguaje Python, escrita desde cero por Damien George y publicada por primera vez en 2014, pensada específicamente para correr con esas limitaciones de memoria y sin sistema operativo debajo. Mantiene la mayor parte de la sintaxis y de la forma de escribir código de Python, así que quien ya sabe Python puede empezar a escribir para un microcontrolador casi sin curva de aprendizaje adicional, pero por dentro es un intérprete mucho más liviano, que deja por fuera buena parte de las librerías estándar de Python y las reemplaza por módulos propios pensados para hablar directamente con los pines, los buses de comunicación y los periféricos del chip.

## Por qué MicroPython y no C++

Acá la comparación sí es directa, porque ambos corren en el mismo tipo de hardware.

| Aspecto | C o C++ vía Arduino o ESP-IDF | MicroPython vía Thonny |
|---|---|---|
| Cómo se ejecuta | Se compila a instrucciones de máquina nativas | Se interpreta línea por línea dentro del chip |
| Velocidad de ejecución | Mucho más rápido, ideal para tareas con tiempos críticos | Más lento, suficiente para la mayoría de proyectos de aprendizaje |
| Uso de memoria | Muy eficiente | Consume más RAM porque el propio intérprete ocupa espacio |
| Velocidad para probar cambios | Hay que compilar y grabar todo de nuevo cada vez | Se puede escribir y probar código directamente en el chip en segundos |
| Curva de aprendizaje | Más exigente, hay que manejar punteros, tipos de datos, compilación | Más suave, sintaxis simple y errores más fáciles de entender |
| Caso de uso típico | Proyectos donde el tiempo de respuesta importa mucho, o donde se necesita exprimir al máximo el chip | Aprendizaje, prototipado rápido, proyectos donde la velocidad de desarrollo importa más que la eficiencia bruta |

En resumen, C++ le exige más al chip pero saca más rendimiento de él, mientras que MicroPython le pide al chip que cargue con el peso de un intérprete pero a cambio permite escribir, probar y corregir código muchísimo más rápido, algo especialmente útil al momento de aprender cómo funciona un sensor o un periférico nuevo sin perder tiempo compilando cada intento.

Para ver esta diferencia de velocidad en la práctica basta un montaje simple: tres LEDs (rojo, amarillo y verde) conectados al ESP32, cada uno a un pin distinto.

![Circuito con tres LEDs conectados al ESP32](./circuito-comparacion-leds.png)

Corriendo la misma secuencia de encendido y apagado sobre este circuito, primero escrita en MicroPython y luego en C/C++ vía Arduino, se nota la demora extra que mete el intérprete de MicroPython frente al binario nativo que produce C/C++: el mismo proceso, el mismo hardware, pero un tiempo de respuesta distinto según el lenguaje.

## Qué se modificó frente al material original

La guía enlazada desde el [README principal del repositorio](../README.md) es una guía de instalación para el NodeMCU V3, una placa con chip ESP8266, y se limita a los pasos de línea de comandos para borrar la flash y grabar el firmware de MicroPython con `esptool`, sin entrar en comparaciones de lenguajes ni en código de ejemplo. A partir de esa base, este README cambia el enfoque de varias formas:

- Se generalizó el procedimiento del ESP8266 de la guía original al ESP32, que es el chip que se usa en el resto de este repositorio y que tiene más memoria y más periféricos que el ESP8266.
- Se agregó toda la parte conceptual que la guía original no cubre: qué es Thonny, de dónde viene, por qué existe MicroPython como reimplementación de Python y no el Python normal de una computadora.
- Se agregó la comparación directa contra programar en C/C++ vía Arduino, con el diagrama de los dos caminos posibles y la tabla de ventajas y desventajas de cada uno, algo que la guía original no menciona porque solo se ocupa de dejar el firmware instalado.
- Se armó el montaje físico de los tres LEDs y se documentó como ejemplo práctico de la diferencia de velocidad entre ambos lenguajes, algo que tampoco existe en el material original.

En resumen, la guía original resuelve un problema puntual, dejar MicroPython grabado en una placa distinta; este README parte de ahí para explicar el porqué detrás de esa elección y para generalizarla al ESP32.

## Problemas de compatibilidad

- **El chip necesita un driver USB-a-serial para que Windows lo reconozca como puerto COM.** La mayoría de placas ESP32 usan un chip CP2102 o CH340 para el puerto USB, y si Windows no tiene el driver correspondiente instalado, el ESP32 no aparece en el Administrador de dispositivos ni en la lista de puertos de Thonny, aunque el cable y la placa estén perfectamente bien.
- **El soporte de MicroPython en Thonny requiere la versión 3.0 o más nueva del programa.** Versiones más viejas de Thonny, pensadas solo para Python de escritorio, no muestran la opción de intérprete de MicroPython en el menú Ejecutar, así que hay que actualizar Thonny antes de intentar conectarse a la placa.
- **El firmware y la velocidad de baudios tienen que coincidir en los dos lados.** Si el firmware de MicroPython grabado en el chip no corresponde al modelo exacto de ESP32 (por ejemplo un firmware genérico de ESP32 en una variante S2 o S3), Thonny puede conectarse al puerto pero fallar al intentar hablarle al intérprete, o mostrar errores extraños apenas se corre cualquier código.
