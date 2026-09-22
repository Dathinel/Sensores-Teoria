# Reconoce digitos escritos a mano usando la webcam y el modelo CNN de
# entrenar_modelo.py, y le manda cada digito estable al ESP-A (maestro)
# por el puerto serial para que lo reenvie por UART2 al ESP-B (esclavo),
# que lo muestra en la pantalla OLED. Todo el flujo completo (camara,
# reconocimiento, envio Y recepcion de la confirmacion del ESP-A) vive
# en este unico script y se ve en una sola ventana — no hace falta
# nada mas para probarlo de punta a punta.
#
# Basado en el ejemplo de vision computacional con OpenCV compartido en
# el repositorio U_Militar (carpeta "10) Open_Cv"); se le agrego el
# envio/recibo por puerto serial hacia el ESP-A (secciones 4 y 5 de
# aqui abajo) y se reforzo preprocesar_digito() (seccion 1) para que
# reconozca mejor digitos gruesos/con reflejos (por ejemplo, mostrados
# en la pantalla de un celular en vez de en papel) -- ver los
# comentarios 1.2 a 1.10 de esa funcion para el detalle de cada ajuste.
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

import math
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
      - Trazo limpio (sin huecos de ruido) y con un grosor parecido al de MNIST
      - Centrado por centro de masa
      - Escalado a 20x20 con padding y un suavizado final tipo MNIST
    Devuelve (imagen_normalizada, caja) o (None, None) si no hay digito.
    """
    if roi is None or roi.size == 0:
        return None, None

    # 1.1 Escala de grises: el color no aporta nada para reconocer un
    # trazo de lapiz/marcador, y trabajar en 1 solo canal es mas rapido
    # y mas facil de umbralizar.
    gris = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # 1.2 Desenfoque de mediana + Gaussiano (no solo Gaussiano): al
    # fotografiar la pantalla de un celular, la resolucion de esa
    # pantalla "compite" con la del sensor de la camara y aparece un
    # patron de moire (ruido tipo sal y pimienta) que el Gaussiano solo
    # no limpia bien pero el de mediana si; el Gaussiano despues
    # suaviza lo que quede para que el umbral adaptativo no vea bordes
    # falsos.
    blur = cv2.medianBlur(gris, 5)
    blur = cv2.GaussianBlur(blur, (5, 5), 0)

    # 1.3 Umbral: adaptativo + Otsu combinados (con OR), no solo
    # adaptativo. El adaptativo solo tiene un bug conocido con trazos
    # GRUESOS (como una fuente de celular en negrita): calcula el corte
    # segun el promedio de una vecindad chica (11px), y en el CENTRO de
    # un trazo mas ancho que esa vecindad, esa media local es casi
    # igual al propio pixel — el resultado es que el centro del trazo
    # se queda AFUERA (hueco), como si fuera fondo, y solo quedan sus
    # bordes. Eso es justo lo que hacia ver un "1" grueso como un "8":
    # el trazo salia hueco, con dos lineas en vez de una solida. Otsu
    # (un solo corte global, sin ese problema de vecindad) rellena bien
    # las zonas grandes y solidas; el OR se queda con lo mejor de los
    # dos: el detalle del adaptativo en los bordes/luz pareja, y el
    # relleno solido de Otsu donde el trazo es grueso.
    adaptativo = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11, 2,
    )
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    umbral = cv2.bitwise_or(adaptativo, otsu)

    # 1.4 Limpieza morfologica del binario, con kernel CHICO (3x3, una
    # sola pasada): un kernel mas grande (se probo 5x5 x2) alcanza a
    # cerrar el hueco de la curva abierta de digitos como el "2" o el
    # "5" y los deja pareciendo un "8" con un lazo de mas — un problema
    # tan real como el que esto viene a arreglar. CLOSE (dilatar y
    # despues erosionar) cierra huecos/cortes CHIQUITOS dentro del
    # trazo (el bug del paso 1.3, o ruido de moire en el aro de un
    # "0"); OPEN (erosionar y despues dilatar) quita motitas sueltas
    # que quedaron fuera del trazo real. Se midio con un lote de mas de
    # 200 digitos de prueba (fuentes reales + fotos de pantalla
    # simuladas con angulo/reflejo/ruido) que este kernel chico da
    # mejor precision que el grande en ambos casos.
    kernel_cierre = np.ones((3, 3), np.uint8)
    umbral = cv2.morphologyEx(umbral, cv2.MORPH_CLOSE, kernel_cierre, iterations=1)
    umbral = cv2.morphologyEx(umbral, cv2.MORPH_OPEN, kernel_cierre)

    # 1.5 Encontrar el contorno mas grande (el digito): findContours
    # devuelve TODOS los contornos que ve (puede haber manchas, sombras,
    # el borde de la hoja/pantalla); nos quedamos solo con el mas
    # grande, que en la practica casi siempre es el trazo del digito.
    contornos, _ = cv2.findContours(umbral, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return None, None

    c = max(contornos, key=cv2.contourArea)
    if cv2.contourArea(c) < 500:  # Ignorar ruido (manchas chiquitas, no un digito real)
        return None, None

    # 1.6 Recortar el digito a su propio rectangulo, sin todo el fondo
    # alrededor.
    x, y, w, h = cv2.boundingRect(c)
    digito = umbral[y:y + h, x:x + w]

    # 1.7 Adelgazar el trazo SOLO si esta MUY grueso (una fuente de
    # celular en negrita, un marcador grueso, etc.): MNIST tiene trazos
    # delgados (unos 2-3px sobre un digito de 20px), y un trazo mucho
    # mas grueso que eso confunde a la CNN — un "1" grueso se lee como
    # un bloque parecido a un "7", y un "0" grueso deja tan poco hueco
    # en el medio que cualquier ruido ahi adentro alcanza para que se
    # lea como un "8". Se mide que proporcion del rectangulo del digito
    # esta "pintada" (relleno) y, si es MUCHA (mas del 45% — un digito
    # normal, incluso uno "gordo" como el "8", no suele pasar de ahi),
    # se erosiona un poco (hasta 3 veces). El umbral de 45% (antes 35%)
    # tambien se ajusto con el mismo lote de prueba: en 35% se
    # adelgazaban de mas digitos que ya estaban bien (sobre todo el "8"
    # y el "9", que naturalmente tienen mas trazo relleno que el resto).
    kernel_erosion = np.ones((5, 5), np.uint8)
    for _ in range(3):
        relleno = cv2.countNonZero(digito) / (w * h)
        if relleno <= 0.45:
            break
        digito = cv2.erode(digito, kernel_erosion, iterations=1)

    # 1.8 Reescalar manteniendo proporcion a 20x20 (MNIST: 20x20 + margen):
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

    # 1.9 Suavizar un poco el trazo ya reescalado: a diferencia de
    # MNIST (que tiene un degradado suave en el borde de cada trazo,
    # antialiasing), nuestro trazo sale binario puro (0 o 255) del
    # umbral adaptativo. Un desenfoque chiquito aca reintroduce ese
    # degradado y acerca la entrada en vivo a lo que la CNN realmente
    # vio durante el entrenamiento.
    digito = cv2.GaussianBlur(digito, (3, 3), 0)

    # 1.10 Lienzo 28x28 negro y pegar centrado por centro de masa: MNIST
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

    # 1.11 Normalizar a [0,1]: la CNN se entreno con pixeles en ese
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

# Pedir mas resolucion a la camara: mientras mas nitida la imagen que
# entrega el sensor, menos ruido/moire aparece al fotografiar un digito
# chico (por ejemplo, mostrado en la pantalla de un celular en vez de
# en papel). Si la camara no soporta 1280x720 , el pedido se ignora
# solo y sigue con la resolucion que tenia por defecto — no hace falta
# revisar el resultado.
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# Region de interes (ROI): el rectangulo verde fijo que se ve en la
# ventana. Solo se procesa lo que hay ADENTRO de ese rectangulo — todo
# lo demas del frame se ignora. Se calcula como un cuadrado centrado
# que ocupa un 60% del lado mas chico del frame, leyendo la resolucion
# REAL que acepto la camara (cap.get, no los numeros que se pidieron
# arriba) — asi el recuadro sigue bien ubicado sin importar si la
# camara acepto los 1280x720 pedidos o se quedo en su resolucion nativa.
ancho_frame = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
alto_frame = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
lado = int(min(ancho_frame, alto_frame) * 0.6)
cx_frame, cy_frame = ancho_frame // 2, alto_frame // 2
x1, y1 = cx_frame - lado // 2, cy_frame - lado // 2
x2, y2 = x1 + lado, y1 + lado

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


# ------------------------------------------------------------------
# Paleta y helpers de dibujo (cosmetico, cambio "de prueba" pedido
# para que la ventana se vea mas de "app/scanner" y menos de texto
# suelto sobre el video): paneles semi-transparentes en vez de cajas
# opacas, esquinas en L en vez de un rectangulo cerrado tapando la
# ROI, y barras de progreso para la ventana de votacion y la
# confianza. No toca nada de la logica de clasificacion/envio de
# arriba, solo COMO se dibuja lo que ya se calculaba antes.
# ------------------------------------------------------------------
COLOR_FONDO_HUD = (42, 23, 15)     # BGR: navy oscuro (panel)
COLOR_ACENTO = (238, 211, 34)      # BGR: cyan (confianza)
COLOR_OK = (94, 197, 34)           # BGR: verde (confirmado/trabado)
COLOR_ALERTA = (11, 158, 245)      # BGR: ambar (analizando)
COLOR_ERROR = (68, 68, 239)        # BGR: rojo (sin ESP-A)
COLOR_GRIS = (128, 114, 107)       # BGR: gris (sin digito)
COLOR_TEXTO = (240, 240, 240)      # BGR: casi blanco


def panel_transparente(frame, x, y, w, h, color, alpha=0.6):
    """Rectangulo relleno semi-transparente (alpha-blend con el video
    de abajo) en vez de uno solido -- deja ver el video detras del
    HUD en vez de taparlo con una caja opaca."""
    x2, y2 = min(x + w, frame.shape[1]), min(y + h, frame.shape[0])
    sub = frame[y:y2, x:x2]
    overlay = np.full_like(sub, color, dtype=np.uint8)
    frame[y:y2, x:x2] = cv2.addWeighted(overlay, alpha, sub, 1 - alpha, 0)


def barra_progreso(frame, x, y, w, h, proporcion, color):
    """Barra horizontal: fondo gris oscuro + relleno proporcional
    (0.0 a 1.0) del color que se le pase. Se usa para la ventana de
    votacion y para la confianza, en vez de solo mostrar el numero."""
    cv2.rectangle(frame, (x, y), (x + w, y + h), (55, 55, 55), -1)
    relleno = int(w * max(0.0, min(1.0, proporcion)))
    if relleno > 0:
        cv2.rectangle(frame, (x, y), (x + relleno, y + h), color, -1)
    cv2.rectangle(frame, (x, y), (x + w, y + h), COLOR_TEXTO, 1)


def esquinas_roi(frame, x1, y1, x2, y2, color, grosor, largo):
    """Marco de 4 esquinas en L (como el visor de una app de camara o
    un lector de QR) en vez de un rectangulo cerrado: deja ver mejor
    lo que hay adentro de la ROI."""
    for (px, py, dx, dy) in [
        (x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1),
    ]:
        cv2.line(frame, (px, py), (px + dx * largo, py), color, grosor)
        cv2.line(frame, (px, py), (px, py + dy * largo), color, grosor)


LARGO_ESQUINA = min(lado, 40)


while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 4.1 Recortar la ROI de un frame SIN nada dibujado todavia encima
    # (antes se dibujaba el recuadro guia primero y recien despues se
    # recortaba, lo que colaba 1-2px del propio borde verde adentro de
    # la ROI) y clasificar/votar.
    roi = frame[y1:y2, x1:x2]
    clase_frame, confianza_frame, digito_procesado = clasificar_frame(roi)
    confirmado, proporcion, confianza_promedio = actualizar_ventana(clase_frame, confianza_frame)

    # 4.2 Elegir el color/grosor de esquinas de la ROI segun el estado:
    # gris = nada reconocible en este frame; ambar = hay algo pero la
    # ventana todavia no junta el 80% para confirmar; verde con un
    # "pulso" de brillo (seno sobre el reloj, no sobre el frame, para
    # que la velocidad no dependa de los FPS de la camara) = ya
    # confirmado y trabado.
    if confirmado is not None:
        pulso = 0.6 + 0.4 * math.sin(time.time() * 4)
        color_estado_digito = tuple(int(c * pulso) for c in COLOR_OK)
        grosor_roi = 4
    elif digito_procesado is not None:
        color_estado_digito = COLOR_ALERTA
        grosor_roi = 2
    else:
        color_estado_digito = COLOR_GRIS
        grosor_roi = 2
    esquinas_roi(frame, x1, y1, x2, y2, color_estado_digito, grosor_roi, LARGO_ESQUINA)

    # 4.3 Panel HUD superior-izquierdo: si hay un digito confirmado, se
    # muestra grande junto con dos barras de progreso (ventana de
    # votacion y confianza promedio); si no, un panel chico dice en que
    # va ("buscando" o "leyendo, todavia sin confirmar").
    panel_x, panel_y, panel_w = 10, 10, 300
    if confirmado is not None:
        panel_h = 108
        panel_transparente(frame, panel_x, panel_y, panel_w, panel_h, COLOR_FONDO_HUD, alpha=0.68)
        cv2.putText(frame, str(confirmado), (panel_x + 14, panel_y + 78),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.2, COLOR_OK, 4)
        cv2.putText(frame, "DIGITO CONFIRMADO", (panel_x + 90, panel_y + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_TEXTO, 1)
        barra_progreso(frame, panel_x + 90, panel_y + 34, 200, 14, proporcion, COLOR_OK)
        cv2.putText(frame, f"ventana {proporcion*100:.0f}%", (panel_x + 90, panel_y + 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_TEXTO, 1)
        barra_progreso(frame, panel_x + 90, panel_y + 66, 200, 14, confianza_promedio / 100, COLOR_ACENTO)
        cv2.putText(frame, f"confianza {confianza_promedio:.0f}%", (panel_x + 90, panel_y + 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLOR_TEXTO, 1)
    else:
        panel_h = 38
        panel_transparente(frame, panel_x, panel_y, panel_w, panel_h, COLOR_FONDO_HUD, alpha=0.55)
        if digito_procesado is not None:
            subtexto = f"Leyendo... {proporcion*100:.0f}% ventana"
        else:
            subtexto = "Buscando digito..."
        cv2.putText(frame, subtexto, (panel_x + 12, panel_y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, color_estado_digito, 2)

    # 4.4 Mandar al ESP-A solo cuando el digito confirmado cambia,
    # igual que en el tema 3 (deteccion-objetos): no se satura el
    # puerto mandando el mismo valor en cada frame (~30 veces por
    # segundo), solo cuando de verdad cambia.
    if confirmado is not None:
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

    # 4.5 Mostrar el digito preprocesado ampliado, con un marco del
    # mismo color/pulso que las esquinas de la ROI y una barra de
    # titulo arriba -- esto es "la parte que lockea": ahora se nota a
    # simple vista, con el marco en verde y el titulo diciendo
    # "CONFIRMADO: n", cuando la ventana ya trabo un digito en vez de
    # seguir acumulando votos (ambar) o no ver nada (gris).
    if digito_procesado is not None:
        LADO_VISTA, MARGEN, BARRA = 220, 10, 34
        vista = (digito_procesado * 255).astype(np.uint8)
        vista = cv2.resize(vista, (LADO_VISTA, LADO_VISTA), interpolation=cv2.INTER_NEAREST)
        vista_color = cv2.cvtColor(vista, cv2.COLOR_GRAY2BGR)

        lienzo_vista = np.full(
            (LADO_VISTA + 2 * MARGEN + BARRA, LADO_VISTA + 2 * MARGEN, 3),
            COLOR_FONDO_HUD, dtype=np.uint8,
        )
        lienzo_vista[BARRA + MARGEN:BARRA + MARGEN + LADO_VISTA, MARGEN:MARGEN + LADO_VISTA] = vista_color
        cv2.rectangle(lienzo_vista, (0, 0), (lienzo_vista.shape[1] - 1, lienzo_vista.shape[0] - 1),
                      color_estado_digito, 3)
        cv2.line(lienzo_vista, (0, BARRA), (lienzo_vista.shape[1], BARRA), color_estado_digito, 2)

        if confirmado is not None:
            titulo = f"CONFIRMADO: {confirmado}"
        elif clase_frame is not None:
            titulo = f"leyendo... ({clase_frame})"
        else:
            titulo = "sin digito claro"
        cv2.putText(lienzo_vista, titulo, (10, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color_estado_digito, 1)

        cv2.imshow('Digito procesado', lienzo_vista)

    # 4.6 Revisar si llego algo del ESP-A y mostrarlo en la misma
    # ventana (envio y recepcion en un solo lugar, sin necesidad de
    # otra herramienta aparte), con un punto de color a modo de "led"
    # en vez de solo texto. Se muestran DOS lineas de estado:
    #   - la confirmacion "REENVIADO:n" ya interpretada, si llego
    #   - la ULTIMA linea cruda que mando el ESP-A, sea la que sea —
    #     sirve para diagnosticar: si esta linea nunca cambia de
    #     "(nada todavia)", el ESP-A no esta mandando nada por USB en
    #     absoluto (revisar que main.py este de verdad corriendo ahi,
    #     no solo guardado); si cambia pero nunca dice "REENVIADO:",
    #     esta mandando otra cosa (revisar el codigo de esp_a_maestro.py).
    leer_confirmaciones_esp_a()
    if ser is None:
        estado1, color_led = "ESP-A: no conectado", COLOR_ERROR
    elif ultima_confirmacion is not None:
        estado1, color_led = f"ESP-A confirmo el reenvio de: {ultima_confirmacion}", COLOR_OK
    else:
        estado1, color_led = "ESP-A: esperando confirmacion...", COLOR_ALERTA
    estado2 = f"Ultimo dato crudo del ESP-A: {ultima_linea_cruda or '(nada todavia)'}"

    alto_f, ancho_f = frame.shape[:2]
    panel_transparente(frame, 0, alto_f - 54, ancho_f, 54, COLOR_FONDO_HUD, alpha=0.62)
    cv2.circle(frame, (22, alto_f - 34), 6, color_led, -1)
    cv2.putText(frame, estado1, (38, alto_f - 29), cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_TEXTO, 1)
    cv2.putText(frame, estado2, (38, alto_f - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, COLOR_GRIS, 1)

    # 4.8 Mostrar frame principal
    cv2.imshow('Reconocimiento de digitos', frame)

    # 4.9 Salir con 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
if ser is not None:
    ser.close()
