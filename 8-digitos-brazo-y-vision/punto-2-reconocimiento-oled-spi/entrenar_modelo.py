# Entrena una CNN sobre MNIST y guarda el modelo en disco.
# Ejecutar UNA SOLA VEZ antes de usar reconocer_digito.py.
#
# Basado en el ejemplo de vision computacional con OpenCV compartido en
# el repositorio U_Militar (carpeta "10) Open_Cv").

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import random

import cv2
import numpy as np
import tensorflow as tf

# 1. Cargar MNIST: 70,000 imagenes de digitos (0-9) escritos a mano,
# 28x28 pixeles en blanco y negro, ya separadas en 60,000 para
# entrenar (x_train/y_train) y 10,000 para validar (x_test/y_test) que
# el modelo aprendio de verdad y no solo memorizo. tf.keras.datasets
# la descarga sola la primera vez que se corre esto.
mnist = tf.keras.datasets.mnist
(x_train, y_train), (x_test, y_test) = mnist.load_data()

# 2. Normalizar: los pixeles llegan de 0 a 255 (blanco y negro de 8
# bits); dividir entre 255 los deja entre 0 y 1. Las redes neuronales
# entrenan mejor con numeros chicos que con numeros grandes — por eso
# reconocer_digito.py tiene que hacer exactamente esta misma division
# antes de pasarle una imagen de la camara al modelo.
x_train = x_train / 255.0
x_test = x_test / 255.0

# 3. Reshape para CNN (canal de entrada = 1): una CNN espera imagenes
# con la forma (alto, ancho, canales) — para blanco y negro el numero
# de canales es 1 (en vez de 3 como seria RGB a color). MNIST viene
# como (alto, ancho) sin esa tercera dimension, asi que hay que
# agregarla.
x_train = x_train.reshape(-1, 28, 28, 1)
x_test = x_test.reshape(-1, 28, 28, 1)

# 4. Construir CNN (mucho mas robusta que la red densa): cada Conv2D
# desliza filtros pequenos sobre la imagen para aprender a detectar
# bordes y curvas, y cada MaxPooling2D reduce el tamano a la mitad
# quedandose con lo mas fuerte de cada zona (asi la red se vuelve
# tolerante a que el trazo este un poco corrido o mas grueso/delgado).
# Flatten aplana todo lo aprendido en un vector, Dense(128) lo combina,
# Dropout(0.5) apaga la mitad de esas neuronas al azar en cada paso de
# entrenamiento (evita que la red "memorice" en vez de generalizar), y
# la ultima capa Dense(10, softmax) da una probabilidad para cada
# digito del 0 al 9 (las 10 probabilidades suman 1).
modelo = tf.keras.Sequential([
    tf.keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
    tf.keras.layers.MaxPooling2D((2, 2)),
    tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
    tf.keras.layers.MaxPooling2D((2, 2)),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.Dense(10, activation='softmax'),
])

# optimizer='adam' es el algoritmo que ajusta los pesos de la red en
# cada paso; loss='sparse_categorical_crossentropy' mide que tan
# equivocada esta la prediccion cuando la respuesta correcta es un
# numero entero (0-9) en vez de un vector; metrics=['accuracy'] es
# solo para que se vea el porcentaje de aciertos mientras entrena.
modelo.compile(optimizer='adam',
               loss='sparse_categorical_crossentropy',
               metrics=['accuracy'])

# 5. Entrenar con data augmentation (rotaciones, traslaciones y ahora
# tambien grosor de trazo): en vez de entrenar siempre con las mismas
# 60,000 imagenes tal cual, ImageDataGenerator le aplica variaciones
# aleatorias chiquitas (rotar hasta 10°, correr hasta 10% en x/y, hacer
# zoom hasta 10%, y de yapa variar_grosor_trazo de aqui abajo) a cada
# imagen en cada epoca. Esto simula que el digito escrito a mano frente
# a la camara nunca va a estar perfectamente centrado, derecho, ni con
# el mismo grosor de lapiz que en MNIST original, asi que la red se
# curte para reconocerlo igual.
def variar_grosor_trazo(img):
    """Engrosa o adelgaza el trazo al azar (dilatar/erosionar en OpenCV).
    MNIST tiene trazos siempre finos y parejos (lapiz digital), pero un
    digito real frente a la camara puede venir escrito con marcador
    grueso o mostrado en una fuente de celular en negrita — mucho mas
    grueso que cualquier cosa que la red haya visto entrenando. En vez
    de perseguir esto solo con el preprocesamiento del lado de la
    camara (fragil: cada ajuste ahi arregla un caso y rompe otro), se
    le enseña a la propia red a reconocer un rango de grosores desde el
    entrenamiento, igual que ya se le enseñan rotaciones/corrimientos.
    ImageDataGenerator llama a esta funcion con cada imagen ya rotada/
    corrida/con zoom (por eso va como preprocessing_function, que
    corre DESPUES de esas transformaciones)."""
    img_u8 = (img[:, :, 0] * 255).astype(np.uint8)
    r = random.random()
    if r < 0.35:
        # Engrosar (35% de las veces): simula marcador/fuente en negrita.
        kernel = np.ones((random.choice([2, 3]), random.choice([2, 3])), np.uint8)
        img_u8 = cv2.dilate(img_u8, kernel, iterations=1)
    elif r < 0.50:
        # Adelgazar (15% de las veces): simula un lapiz muy fino o un
        # trazo que el umbral de la camara dejo mas delgado de lo normal.
        kernel = np.ones((2, 2), np.uint8)
        img_u8 = cv2.erode(img_u8, kernel, iterations=1)
    # El 50% restante queda igual: la mayoria de los trazos reales SI
    # se parecen al grosor de MNIST, no hay que exagerar la variacion.
    return (img_u8.astype(np.float32) / 255.0).reshape(28, 28, 1)


datagen = tf.keras.preprocessing.image.ImageDataGenerator(
    rotation_range=10,
    width_shift_range=0.1,
    height_shift_range=0.1,
    zoom_range=0.1,
    preprocessing_function=variar_grosor_trazo,
)

# epochs=10: 10 pasadas completas por las 60,000 imagenes de
# entrenamiento. validation_data=(x_test, y_test): despues de cada
# epoca, se mide que tan bien predice sobre las 10,000 imagenes que
# NUNCA vio entrenando — si el accuracy de entrenamiento sube pero el
# de validacion no, es senal de que esta memorizando en vez de
# aprender (overfitting).
modelo.fit(datagen.flow(x_train, y_train, batch_size=32),
           epochs=10,
           validation_data=(x_test, y_test))

# 6. Guardar: el archivo .h5 guarda tanto la arquitectura de la red
# como los pesos ya entrenados, listo para que
# tf.keras.models.load_model() lo cargue en reconocer_digito.py sin
# tener que entrenar de nuevo cada vez.
modelo.save('modelo_mnist_cnn.h5')
print("Modelo guardado como modelo_mnist_cnn.h5")
