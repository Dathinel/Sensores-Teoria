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

2. **Entrenar** (Keras + MobileNetV2, transferencia de aprendizaje) en el **mismo entorno** del
   proyecto. TensorFlow no tiene versión para Python 3.14, pero Keras 3 ya no depende de él: corre
   sobre PyTorch (`KERAS_BACKEND=torch`, lo pone el script solo), que sí la tiene. `torch`, `keras` y
   `matplotlib` ya vienen en `requirements-lock.txt` (torch en su versión CPU):

   ```
   entorno\Scripts\python -m vision.entrenar
   ```

   La primera vez descarga los pesos de MobileNetV2 (necesita internet). Deja en
   `vision/resultados/` la **matriz de confusión**, la **curva de confianza** y `metricas.json`
   (con la confianza mínima sugerida para `config/parametros.yaml`); esos sí se suben, son material
   del informe. El modelo (`vision/modelos/monedas.keras`) no se sube: pesa.

   Para probar que el script funciona sin fotos reales ni internet:
   `entorno\Scripts\python -m vision.entrenar --dataset <carpeta> --epocas 1 --sin-imagenet --salida <otra carpeta>`
   (probado el 2026-09-27 con 36 imágenes sintéticas de 3 clases: entrena, guarda el modelo y deja
   las dos gráficas y las métricas).

Pendiente, antes de usar el modelo en la línea: el pipeline geométrico con OpenCV (segmentar la
pieza sobre la cinta negra, diámetro en mm con la calibración, circularidad, agujeros y bandera
bimetálica) y conectar `vision/modelos/monedas.keras` en lugar del oráculo, sin tocar `control/`.
