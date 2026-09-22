# Reconoce digitos escritos a mano usando la webcam y el modelo CNN de
# entrenar_modelo.py, y le manda cada digito estable al ESP-A (maestro)
# por el puerto serial para que lo reenvie por UART2 al ESP-B (esclavo),
# que lo muestra en la pantalla OLED. Todo el flujo completo (camara,
# reconocimiento, envio Y recepcion de la confirmacion del ESP-A) vive
# en este unico script y se ve en una sola ventana — no hace falta
# nada mas para probarlo de punta a punta.
#
# Basado en el ejemplo de vision computacional con OpenCV compartido en
# el repositorio U_Militar (carpeta "10) Open_Cv"); la parte de
# preprocesamiento y reconocimiento (preprocesar_digito) es la misma
# tal cual la comparte el profesor, solo se le agrego el envio/recibo
# por puerto serial hacia el ESP-A (secciones 4 y 5 de aqui abajo).
#
# Ajustar PUERTO_SERIAL segun el puerto que use el ESP-A en el
# Administrador de dispositivos. Si no se encuentra el ESP-A, el
# reconocimiento sigue funcionando igual en pantalla, simplemente no le
# manda nada a nadie.

# ------------------------------------------------------------------
# 0. Silenciar mensajes de TensorFlow (deben ir ANTES de importar TF)
# ------------------------------------------------------------------
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'    # Solo errores
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'   # Desactiva oneDNN

import time

import cv2
import numpy as np
import serial
import tensorflow as tf

PUERTO_SERIAL = "COM7"
BAUDIOS = 115200

# Abrir el puerto serial reinicia el ESP32 (Windows togglea la linea
# DTR al conectar), y durante ese reinicio el ESP32 no procesa nada ni
# esta listo para recibir — por eso el time.sleep(2) antes de seguir,
# igual que en brazo_pybullet.py y brazo_dibuja.py. Sin esa espera, los
# primeros DIGIT:n que se manden se pierden porque el ESP32 todavia
# esta arrancando.
try:
    ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.05)
    time.sleep(2)
    print(f"ESP-A conectado en {PUERTO_SERIAL}: cada digito estable se le manda.")
except serial.SerialException:
    ser = None
    print(f"No se encontro el ESP-A en {PUERTO_SERIAL}: el reconocimiento sigue, pero no se manda nada.")


# ------------------------------------------------------------------
# 1. Funcion de preprocesamiento estilo MNIST
# ------------------------------------------------------------------
def preprocesar_digito(roi):
    """
    Convierte un recorte BGR de la webcam en una imagen 28x28 tipo MNIST:
      - Fondo negro, digito blanco
      - Centrado por centro de masa
      - Escalado a 20x20 con padding
    Devuelve (imagen_normalizada, caja) o (None, None) si no hay digito.
    """
    if roi is None or roi.size == 0:
        return None, None

    # 1.1 Escala de grises: el color no aporta nada para reconocer un
    # trazo de lapiz sobre papel, y trabajar en 1 solo canal es mas
    # rapido y mas facil de umbralizar.
    gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # 1.2 Desenfoque suave (kernel pequeno para no cerrar el hueco del 0):
    # sin esto, el ruido de la camara puede crear bordes falsos que el
    # umbral adaptativo interpretaria como parte del trazo.
    blur = cv2.GaussianBlur(gris, (5, 5), 0)

    # 1.3 Umbral adaptativo (mas robusto que uno fijo): en vez de un
    # solo valor de corte para toda la imagen, calcula el umbral en
    # cada zona segun la iluminacion local — asi funciona aunque la
    # luz no sea pareja sobre el papel.
    umbral = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2,
    )

    # 1.4 Encontrar el contorno mas grande (el digito): findContours
    # devuelve TODOS los contornos que ve (puede haber manchas, sombras,
    # el borde de la hoja); nos quedamos solo con el mas grande, que en
    # la practica casi siempre es el trazo del digito.
    contornos, _ = cv2.findContours(umbral, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return None, None

    c = max(contornos, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:  # Ignorar ruido (manchas chiquitas, no un digito real)
        return None, None

    # 1.5 Recortar el digito a su propio rectangulo, sin todo el fondo
    # alrededor.
    x, y, w, h = cv2.boundingRect(c)
    digito = umbral[y:y + h, x:x + w]

    # 1.6 Reescalar manteniendo proporcion a 20x20 (MNIST: 20x20 + margen):
    # el dataset MNIST original centra cada digito en un cuadro de 28x28
    # pero el trazo en si mide unos 20x20 — reproducir exactamente esa
    # proporcion es lo que hace que la CNN (entrenada sobre MNIST)
    # reconozca bien los digitos de la camara.
    if w > h:
        nuevo_w = 20
        nuevo_h = max(1, int(round(20 * h / w)))
    else:
        nuevo_h = 20
        nuevo_w = max(1, int(round(20 * w / h)))

    digito = cv2.resize(digito, (nuevo_w, nuevo_h), interpolation=cv2.INTER_AREA)

    # 1.7 Lienzo 28x28 negro y pegar centrado por centro de masa: MNIST
    # no centra los digitos por su caja (bounding box) sino por su
    # centro de masa (donde "pesa" mas el trazo), asi que se calcula
    # ese centro con cv2.moments y se pega ahi, no a la mitad geometrica.
    lienzo = np.zeros((28, 28), dtype=np.uint8)

    M = cv2.moments(digito)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
    else:
        cx, cy = nuevo_w // 2, nuevo_h // 2

    desplaz_x = 14 - cx
    desplaz_y = 14 - cy

    for i in range(nuevo_h):
        for j in range(nuevo_w):
            yi = i + desplaz_y
            xj = j + desplaz_x
            if 0 <= yi < 28 and 0 <= xj < 28:
                lienzo[yi, xj] = digito[i, j]

    # 1.8 Normalizar a [0,1]: la CNN se entreno con pixeles en ese
    # rango (entrenar_modelo.py hace x_train/255.0), asi que la entrada
    # en vivo tiene que seguir la misma escala o la red predice mal.
    lienzo = lienzo / 255.0

    return lienzo, (x, y, w, h)


# ------------------------------------------------------------------
# 2. Cargar el modelo entrenado (avisa con un paso claro si falta)
# ------------------------------------------------------------------
if not os.path.exists('modelo_mnist_cnn.h5'):
    print("No existe 'modelo_mnist_cnn.h5' todavia.")
    print("Corre primero, una sola vez: python entrenar_modelo.py")
    print("(tarda varios minutos; despues de eso ya puedes correr este script normal)")
    exit()

modelo = tf.keras.models.load_model('modelo_mnist_cnn.h5')
print("Modelo cargado. Presiona 'q' para salir.")


# ------------------------------------------------------------------
# 3. Abrir la camara
# ------------------------------------------------------------------
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("No se pudo abrir la camara.")
    exit()

# Region de interes (ROI): el rectangulo verde fijo que se ve en la
# ventana. Solo se procesa lo que hay ADENTRO de ese rectangulo — todo
# lo demas del frame se ignora. Ajustar estos 4 numeros segun la
# resolucion de la camara si el recuadro no queda bien ubicado.
x1, y1, x2, y2 = 300, 100, 600, 400

# ------------------------------------------------------------------
# Suavizado por ventana de votacion, con umbral de proporcion y de
# confianza — el mismo esquema de 3 filtros que ya se probo y funciona
# bien en el tema 6 (gesture_control.html: clasificarFrame +
# actualizarVentana), adaptado de "gestos de mano" a "digitos". Antes
# esto era una ventana mas chica (5 frames) que solo pedia "el mas
# repetido" sin exigir que ganara por mucho — eso dejaba pasar
# confirmaciones con apenas 2 de 5 votos (40%), y por eso se sentia que
# fallaba "por pequenos errores".
# ------------------------------------------------------------------
TAM_VENTANA = 15        # ventana mas grande (antes 5): mas frames = menos ruido
UMBRAL_CONFIANZA = 60   # % minimo de confianza de la CNN en UN frame para que cuente algo (si no, cuenta como "nada")
UMBRAL_CONFIRMACION = 0.8  # el digito ganador tiene que ser al menos el 80% de la ventana para "confirmarse", no solo el mas comun

ventana = []             # ultimas TAM_VENTANA clases (None = "nada reconocido con confianza" en ese frame)
ventana_confianzas = []  # su confianza correspondiente, para poder promediar
digito_enviado = None       # ultimo digito que se le mando al ESP-A (para no repetir envios)
ultima_confirmacion = None  # ultima confirmacion "REENVIADO:n" que llego del ESP-A
ultima_linea_cruda = None   # ultima linea que llego del ESP-A, sea o no una confirmacion


def clasificar_frame(roi):
    """Igual que clasificarFrame() del tema 6: procesa UN frame y
    devuelve (clase, confianza, digito_procesado). clase es None si no
    hay contorno reconocible O si la confianza de la CNN no alcanza
    UMBRAL_CONFIANZA — asi un frame ruidoso entra a la ventana como
    "nada" en vez de como un digito equivocado."""
    digito_procesado, bbox = preprocesar_digito(roi)
    if digito_procesado is None:
        return None, 0.0, None

    entrada = digito_procesado.reshape(1, 28, 28, 1)
    prediccion = modelo.predict(entrada, verbose=0)
    clase = int(np.argmax(prediccion))
    confianza = float(np.max(prediccion)) * 100

    if confianza < UMBRAL_CONFIANZA:
        return None, confianza, digito_procesado
    return clase, confianza, digito_procesado


def actualizar_ventana(clase, confianza):
    """Igual que actualizarVentana() del tema 6: mete (clase, confianza)
    a la ventana deslizante y vota por mayoria, pero solo "confirma" un
    digito si gano con al menos UMBRAL_CONFIRMACION de los votos — no
    solo por ser el mas frecuente. Devuelve (confirmado, proporcion,
    confianza_promedio); confirmado es None si nadie llego al umbral
    (incluido el caso en que "nada" es lo que mas se repite, por
    ejemplo cuando se quita el papel)."""
    ventana.append(clase)
    ventana_confianzas.append(confianza)
    if len(ventana) > TAM_VENTANA:
        ventana.pop(0)
        ventana_confianzas.pop(0)

    conteo = {}
    suma_confianza = {}
    for c, conf in zip(ventana, ventana_confianzas):
        conteo[c] = conteo.get(c, 0) + 1
        suma_confianza[c] = suma_confianza.get(c, 0) + conf

    ganador = max(conteo, key=conteo.get)
    proporcion = conteo[ganador] / len(ventana)
    confianza_promedio = suma_confianza[ganador] / conteo[ganador]

    confirmado = ganador if (ganador is not None and proporcion >= UMBRAL_CONFIRMACION) else None
    return confirmado, proporcion, confianza_promedio


# ------------------------------------------------------------------
# 4. Recibir del ESP-A (no solo mandarle) — esto es lo que cierra el
# circuito: sin esto, el script "manda y reza" sin saber si el ESP-A
# de verdad recibio algo.
# ------------------------------------------------------------------
def leer_confirmaciones_esp_a():
    """Lee TODAS las lineas que hayan llegado del ESP-A desde la
    ultima vez que se llamo esta funcion (no solo una), para no
    quedarse atras si llegaron varias entre un frame de camara y el
    siguiente. Actualiza ultima_linea_cruda con lo ultimo que llego
    (aunque no sea una confirmacion valida) para poder diagnosticar
    en pantalla si el ESP-A esta mandando ALGO o nada en absoluto."""
    global ultima_confirmacion, ultima_linea_cruda
    if ser is None:
        return
    while ser.in_waiting > 0:
        linea = ser.readline().decode(errors="ignore").strip()
        if not linea:
            continue
        ultima_linea_cruda = linea
        print(f"[SERIAL] recibido: {linea!r}")  # log en consola, no solo en pantalla
        if linea.startswith("REENVIADO:"):
            ultima_confirmacion = linea.split(":", 1)[1]


while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 4.1 Dibujar el recuadro guia
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # 4.2 Recortar la ROI, clasificar el frame y votar en la ventana
    roi = frame[y1:y2, x1:x2]
    clase_frame, confianza_frame, digito_procesado = clasificar_frame(roi)
    confirmado, proporcion, confianza_promedio = actualizar_ventana(clase_frame, confianza_frame)

    if confirmado is not None:
        # 4.3 Solo se muestra/manda cuando la ventana ya esta segura
        # (>= UMBRAL_CONFIRMACION de los votos), no con cualquier
        # mayoria por poquito.
        texto = f"Numero: {confirmado} ({proporcion*100:.0f}% ventana, {confianza_promedio:.1f}% confianza)"
        cv2.putText(frame, texto, (x1, y1 - 15), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # 4.4 Mandar al ESP-A solo cuando el digito confirmado cambia,
        # igual que en el tema 3 (deteccion-objetos): no se satura el
        # puerto mandando el mismo valor en cada frame (~30 veces por
        # segundo), solo cuando de verdad cambia.
        if ser is not None and confirmado != digito_enviado:
            ser.write(f"DIGIT:{confirmado}\n".encode())
            digito_enviado = confirmado
            ultima_confirmacion = None  # todavia no ha llegado confirmacion de ESTE envio
            print(f"[SERIAL] mandado: DIGIT:{confirmado}")  # log en consola, no solo en pantalla
    else:
        # nada confirmado todavia (ventana insegura, o "nada" gano
        # porque se quito el papel): el proximo digito que se confirme
        # se manda de una, no se espera a que cambie de otro digito
        digito_enviado = None

    # 4.5 Mostrar el digito preprocesado ampliado, si hay uno
    if digito_procesado is not None:
        vista = (digito_procesado * 255).astype(np.uint8)
        vista = cv2.resize(vista, (200, 200), interpolation=cv2.INTER_NEAREST)
        cv2.imshow('Digito procesado (28x28 ampliado)', vista)

    # 4.6 Revisar si llego algo del ESP-A y mostrarlo en la misma
    # ventana (envio y recepcion en un solo lugar, sin necesidad de
    # otra herramienta aparte). Se muestran DOS lineas de estado:
    #   - la confirmacion "REENVIADO:n" ya interpretada, si llego
    #   - la ULTIMA linea cruda que mando el ESP-A, sea la que sea —
    #     sirve para diagnosticar: si esta linea nunca cambia de
    #     "(nada todavia)", el ESP-A no esta mandando nada por USB en
    #     absoluto (revisar que main.py este de verdad corriendo ahi,
    #     no solo guardado); si cambia pero nunca dice "REENVIADO:",
    #     esta mandando otra cosa (revisar el codigo de esp_a_maestro.py).
    leer_confirmaciones_esp_a()
    if ser is None:
        estado1, color1 = "ESP-A: no conectado", (0, 0, 255)
    elif ultima_confirmacion is not None:
        estado1, color1 = f"ESP-A confirmo el reenvio de: {ultima_confirmacion}", (0, 255, 0)
    else:
        estado1, color1 = "ESP-A: esperando confirmacion...", (0, 165, 255)
    estado2 = f"Ultimo dato crudo del ESP-A: {ultima_linea_cruda or '(nada todavia)'}"

    cv2.putText(frame, estado1, (10, frame.shape[0] - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color1, 2)
    cv2.putText(frame, estado2, (10, frame.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # 4.8 Mostrar frame principal
    cv2.imshow('Reconocimiento de digitos', frame)

    # 4.9 Salir con 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
if ser is not None:
    ser.close()
