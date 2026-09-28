# Visión: dataset y entrenamiento del clasificador (fase 5)

Hoy la cámara de la línea es un **oráculo** (la simulación entrega la clase con un ruido
configurable). Estos dos scripts dejan listo el camino para el modelo real, en cuanto tengamos las
monedas y el montaje:

1. **Capturar fotos** con la webcam del montaje (a ~15 cm sobre E3, anillo de luz, cinta negra):

   ```
   entorno\Scripts\python -m vision.capturar_dataset --camara 1
   ```

   Teclas 1-9 eligen la clase (las 9 que se entrenan, de `config/monedas.yaml`), 0 es "otro"
   (extranjeras, botones metálicos, arandelas), espacio guarda la foto, q sale. Meta: 80-150 fotos
   por clase, anverso y reverso, incluidas piezas gastadas. Quedan en `vision/dataset/` (fuera de git).

2. **Entrenar** (Keras + MobileNetV2, transferencia de aprendizaje). TensorFlow no tiene versión para
   Python 3.14 (el del proyecto), así que se usa un entorno aparte con Python 3.12, una sola vez:

   ```
   py -3.12 -m venv vision\entorno
   vision\entorno\Scripts\python -m pip install tensorflow opencv-python matplotlib pyyaml
   vision\entorno\Scripts\python -m vision.entrenar
   ```

   La primera vez descarga los pesos de MobileNetV2 (necesita internet). Deja en
   `vision/resultados/` la **matriz de confusión**, la **curva de confianza** y `metricas.json`
   (con la confianza mínima sugerida para `config/parametros.yaml`); esos sí se suben, son material
   del informe. El modelo (`vision/modelos/monedas.keras`) no se sube: pesa.

Pendiente, antes de usar el modelo en la línea: el pipeline geométrico con OpenCV (segmentar la
pieza sobre la cinta negra, diámetro en mm con la calibración, circularidad, agujeros y bandera
bimetálica) y conectar `vision/modelos/monedas.keras` en lugar del oráculo, sin tocar `control/`.
