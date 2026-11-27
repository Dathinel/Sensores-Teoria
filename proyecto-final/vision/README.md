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

## Detector YOLO con el celular (`yolo_monedas/`, aparte de la línea)

Pedido del 2026-11-24: detectar monedas colombianas (familias nueva y antigua) con YOLO, tomando la
foto con el celular desde una página de Streamlit, midiendo el diámetro, la figura y los detalles, y
descargando los recortes. No lee sensores, no manda órdenes y no toca `control/` (solo lee
`config/monedas.yaml`). Plástico o metal da igual: se mira la apariencia.

1. **Dataset** (no se toman fotos propias): export "YOLOv8" de Roboflow
   [monedas-colombianas-ins-seg v1](https://universe.roboflow.com/lladinog-unal-edu-co/monedas-colombianas-ins-seg/dataset/1)
   (CC BY 4.0, 9 clases: 50/100/200/500 nueva y antigua, y 1000), descomprimido en `vision/dataset/yolo_monedas/`.
2. **Prueba y error**: `entorno\Scripts\python -m vision.yolo_monedas.entrenar` entrena varias variantes
   (yolov8n y yolo11n, de segmentación si las etiquetas traen polígonos), se queda con la de mejor mAP50-95
   en `vision/modelos/yolo_monedas.pt` y deja la tabla `vision/resultados/yolo_monedas/comparativa.md` y las
   gráficas de cada intento.
3. **Celular**: `entorno\Scripts\python -m vision.yolo_monedas` y, en el S24 Ultra conectado a la misma
   Wi-Fi, abrir la dirección que imprime (puerto `yolo_monedas.puerto`, 8510). «Tomar foto» abre la cámara.
   Lo mismo está en la pestaña **Detector de monedas** del tablero, que además muestra la última foto
   tomada desde el celular (`vision/capturas/ultima/`, fuera de git).

Medidas (`medir.py`): diámetro equivalente de la máscara; la escala sale de un cuadrado ArUco 4x4 de
5 cm impreso junto a las monedas o, sin él, de las mismas monedas (mediana de px / diámetro nominal: con
una sola moneda el diámetro es el nominal). Circularidad y elongación (disco o inclinada/ocluida), color
(plateado, dorado, cobrizo) y bandera bimetálica por contraste centro/anillo en Lab (§12), comparada con
la tabla. Umbrales en `config/parametros.yaml`, bloque `yolo_monedas`. Pruebas: `tests/vision/`.

**Cómo decide (medido en las 33 monedas de test, 2026-11-24):** los dos detectores (yolo11n-seg ganador y
yolov8n-seg segundo, `yolo_monedas_2.pt`) se fusionan y encuentran 31 de 33 monedas con 2 falsas. La clase
la da la opinión más segura entre YOLO y el clasificador de recortes (`clasificador.py`: yolo11n-cls sobre
cada moneda recortada y girada 8 veces): 24 de 33 bien (YOLO solo, 21). El color bimetálico solo avisa
("revisar"): usarlo para corregir la clase bajaba a 16. **Qué no es moneda:** el dataset no trae botones ni
arandelas, así que lo deciden `medir.agujeros` (manchas redondas con el color del fondo dentro del disco: 0
falsos en 54 monedas reales) y la confianza mínima `clase_conf_min`. Progreso del entrenamiento:
`python -m vision.yolo_monedas.progreso --grafica`.
