# Dígitos: brazo que dibuja + visión que reconoce

Actividad de dos puntos independientes, ambos alrededor de dígitos del 0 al 9 y ambos usando como base el `brazo.urdf` y el ejemplo de OpenCV compartidos en el repositorio [U_Militar](https://github.com/dialejobv/U_Militar/blob/main/README.md).

### [Punto 1: Teclado I2C + brazo robótico dibujando](./punto-1-teclado-brazo-dibujando)
Un teclado matricial 4x4 y una LCD, los dos por I2C, dejan elegir un dígito; el ESP32 lo muestra en la LCD y el brazo simulado en PyBullet lo dibuja moviendo sus articulaciones.

### [Punto 2: Reconocimiento de dígitos con OpenCV + CNN + OLED](./punto-2-reconocimiento-oled-spi)
Un dígito escrito a mano se reconoce con una CNN entrenada sobre MNIST, se manda por serial a un ESP32 maestro, este lo reenvía a un segundo ESP32 esclavo, y ese lo muestra en una pantalla OLED.
