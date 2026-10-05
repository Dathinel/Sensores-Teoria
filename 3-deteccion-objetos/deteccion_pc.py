# Corre YOLOv8 sobre la camara en vivo y le avisa al ESP32, por el puerto
# serial, si esta viendo una silla y/o un celular (o, con --carro-moto, un
# carro y una moto de juguete, la directiva alternativa de la actividad).
#
# Ajustar PUERTO_SERIAL segun el puerto que use el ESP32 en el
# Administrador de dispositivos, por ejemplo "COM5" en Windows
# o "/dev/ttyUSB0" en Linux.
#
# Uso:
#   python deteccion_pc.py               -> silla (GPIO25) y celular (GPIO26)
#   python deteccion_pc.py --carro-moto  -> carro (GPIO25, LED rojo) y moto (GPIO26, LED verde)
#
# Sin camara web (las dos opciones se combinan con --carro-moto):
#   python deteccion_pc.py --imagen                  -> fotos de ejemplo de img/ejemplos/
#   python deteccion_pc.py --imagen foto1.jpg ...    -> fotos propias
#   python deteccion_pc.py --video archivo.mp4       -> un video (o un .gif), en bucle
#
# Si el ESP32 no esta conectado (o el puerto esta ocupado por Thonny), el
# script NO se cae: sigue mostrando la camara con las detecciones y escribe
# en pantalla el mensaje que le habria mandado, para poder probar la parte
# de vision sin el hardware a la mano.

import argparse
import sys
import time
from pathlib import Path

import cv2
import serial
from ultralytics import YOLO

PUERTO_SERIAL = "COM7"
BAUDIOS = 115200  # tiene que ser el mismo del lado del ESP32 (por USB, MicroPython usa 115200)

# Carpeta de este archivo: el modelo y las fotos de ejemplo se buscan aqui y
# no en la carpeta desde donde se lanzo el comando, asi funciona igual si se
# corre desde otro lado (por ejemplo desde el lanzador de la raiz del repo).
CARPETA = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(description="YOLOv8 -> LEDs del ESP32 por serial")
parser.add_argument("--carro-moto", action="store_true",
                    help="detectar carro y moto en vez de silla y celular")
# nargs="*": "--imagen" solo (sin archivos) usa las fotos de ejemplo del repo.
parser.add_argument("--imagen", nargs="*", metavar="ARCHIVO",
                    help="usar fotos en vez de la camara (sin archivos: las de ejemplo)")
parser.add_argument("--video", metavar="ARCHIVO",
                    help="usar un video (o gif) en vez de la camara; se repite en bucle")
args = parser.parse_args()

# Nombres exactos de las clases dentro del dataset COCO con el que se entreno
# YOLOv8. El ORDEN importa: el primer objetivo es el primer caracter del
# mensaje (LED en GPIO25) y el segundo es el segundo caracter (LED en GPIO26).
# COCO ya trae "car" y "motorcycle", asi que la directiva del carro y la moto
# no necesita entrenar nada nuevo: solo cambiar esta lista.
if args.carro_moto:
    OBJETIVOS = ["car", "motorcycle"]
    EJEMPLOS = ["ejemplo-carro.jpg", "ejemplo-moto.jpg", "ejemplo-carro-y-moto.jpg"]
else:
    OBJETIVOS = ["chair", "cell phone"]
    EJEMPLOS = ["ejemplo-silla.jpg", "ejemplo-celular.jpg", "ejemplo-silla-y-celular.jpg"]

# Con --imagen se pasa de una foto a la siguiente cada tantos segundos. Las de
# ejemplo estan en ese orden a proposito (solo el primero, solo el segundo,
# los dos) para que se vea el mensaje pasar por "10", "01" y "11".
SEGUNDOS_POR_IMAGEN = 3.0

# Confianza minima para aceptar una deteccion. YOLO devuelve para cada caja un
# numero entre 0 y 1 de que tan seguro esta; por debajo de 0.4 aparecen muchos
# falsos positivos (sombras, reflejos) que harian parpadear el LED.
CONFIANZA_MINIMA = 0.4

# Cada cuanto se repite el mensaje aunque no haya cambiado nada. El ESP32
# apaga los LEDs si pasan 2000 ms sin recibir NADA (apagado de seguridad), asi
# que si solo se mandara el mensaje cuando cambia el estado, una silla que se
# queda quieta frente a la camara apagaria su LED a los 2 s. Repetirlo cada
# 500 ms (4 veces dentro de esa ventana) mantiene el LED encendido mientras el
# objeto sigue ahi y, aun asi, es muy poco trafico (2 lineas por segundo).
REENVIO_S = 0.5

# "n" = nano: la version mas liviana de YOLOv8, la unica que corre fluida sin
# GPU. Si el archivo no esta en la carpeta, ultralytics lo descarga solo.
model = YOLO(str(CARPETA / "yolov8n.pt"))

# --- Puerto serial, con respaldo si no hay ESP32 ---------------------------
try:
    # timeout=0: las lecturas nunca bloquean (ver la parte de lectura abajo).
    ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0)
    # Abrir el puerto reinicia el ESP32 (la linea DTR del USB esta cableada a
    # su pin EN); se esperan 2 s a que arranque y deje main.py escuchando.
    time.sleep(2)
    print(f"ESP32 conectado en {PUERTO_SERIAL}.")
except serial.SerialException as error:
    ser = None
    print(f"Sin ESP32 ({error}). Se sigue solo con la vision: el mensaje "
          "que se mandaria aparece escrito en la ventana.")

# --- De donde salen las imagenes: camara, video o fotos ------------------------
# El resto del programa (YOLO, mensaje, serial) es exactamente el mismo en los
# tres casos: solo cambia de donde sale cada fotograma.
cap = None
imagenes = []
if args.imagen is not None:
    rutas = args.imagen or [str(CARPETA / "img" / "ejemplos" / n) for n in EJEMPLOS]
    for ruta in rutas:
        img = cv2.imread(ruta)  # devuelve None (no una excepcion) si no puede leerla
        if img is None:
            print(f"No se pudo leer la imagen {ruta}")
            sys.exit(1)
        imagenes.append(img)
    fuente = f"FOTOS ({len(imagenes)}, cambia cada {SEGUNDOS_POR_IMAGEN:.0f} s)"
elif args.video:
    cap = cv2.VideoCapture(args.video)
    fuente = f"VIDEO {Path(args.video).name}"
else:
    cap = cv2.VideoCapture(0)
    # 640x480 (la misma del ejemplo del profesor): YOLO reescala todo a 640 por
    # dentro, asi que pedirle a la camara mas resolucion solo gasta tiempo en
    # capturar y dibujar sin mejorar la deteccion de objetos de este tamano.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    fuente = "CAMARA"

if cap is not None and not cap.isOpened():
    print("Error al abrir la camara" if not args.video else f"No se pudo abrir el video {args.video}")
    if not args.video:
        print("Sin camara web se puede probar igual con fotos: "
              "python deteccion_pc.py --imagen")
    sys.exit(1)

print(f"Objetivos: {OBJETIVOS}. Fuente: {fuente}. Presiona 'q' en la ventana para salir.")
estado_anterior = None
ultimo_envio = 0.0
ultima_linea_esp = "(nada todavia)"
inicio = time.time()
cache_fotos = {}  # indice de foto -> resultado de YOLO (una foto quieta no cambia)

while True:
    if imagenes:
        # Que foto toca segun el tiempo transcurrido; vuelve a la primera al final.
        indice = int((time.time() - inicio) / SEGUNDOS_POR_IMAGEN) % len(imagenes)
        if indice not in cache_fotos:
            # Una foto no cambia entre vueltas del bucle: YOLO se corre una sola
            # vez por foto y se reutiliza, en vez de gastar CPU en lo mismo.
            cache_fotos[indice] = model(imagenes[indice], verbose=False)
        results = cache_fotos[indice]
    else:
        ret, frame = cap.read()
        if not ret:
            if args.video:
                # Se acabo el video: vuelve al primer fotograma (bucle infinito).
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
            if not ret:
                break
        # Una sola pasada de la red por fotograma (de ahi "You Only Look Once").
        results = model(frame, verbose=False)

    annotated_frame = results[0].plot()

    # De todas las clases que YOLO reconoce (80 en COCO) solo interesan las de
    # OBJETIVOS; un set evita contar dos veces el mismo tipo de objeto.
    detectados = set()
    for box in results[0].boxes:
        clase = model.names[int(box.cls[0])]
        if clase in OBJETIVOS and float(box.conf[0]) >= CONFIANZA_MINIMA:
            detectados.add(clase)

    # Mensaje de dos caracteres, uno por objetivo y en el orden de la lista:
    # "10" = solo el primero, "01" = solo el segundo, "11" ambos, "00" ninguno.
    estado = "".join("1" if objetivo in detectados else "0" for objetivo in OBJETIVOS)

    # Se manda en cuanto cambia (respuesta inmediata del LED) y, ademas, cada
    # REENVIO_S aunque no cambie (para que no actue el apagado de seguridad).
    ahora = time.time()
    if estado != estado_anterior or ahora - ultimo_envio >= REENVIO_S:
        if ser is not None:
            try:
                ser.write((estado + "\n").encode())
            except serial.SerialException:
                print("Se perdio el ESP32 (cable desconectado). Sigue solo la vision.")
                ser = None
        estado_anterior = estado
        ultimo_envio = ahora

    # Lectura de lo que contesta el ESP32 ("LEDS 10", "APAGADO_SEGURIDAD"...):
    # se vacia TODO lo que haya en el buffer, pero solo si hay algo
    # (in_waiting > 0). Un readline() a secas esperaria datos y frenaria la
    # camara. La ultima linea cruda se muestra en pantalla: si nunca cambia, el
    # ESP32 no esta contestando; si cambia pero no es lo esperado, es formato.
    if ser is not None:
        try:
            while ser.in_waiting > 0:
                linea = ser.readline().decode(errors="replace").strip()
                if linea:
                    ultima_linea_esp = linea
        except serial.SerialException:
            ser = None

    # Texto de estado sobre la imagen (fondo negro para que se lea siempre).
    modo = f"ESP32 en {PUERTO_SERIAL}" if ser is not None else "SIN ESP32 (solo vision)"
    textos = [
        f"{OBJETIVOS[0]}: {estado[0]}   {OBJETIVOS[1]}: {estado[1]}   -> '{estado}'",
        f"{modo}  |  {fuente}",
        f"ESP32 dice: {ultima_linea_esp}" if ser is not None else "",
    ]
    for i, texto in enumerate(t for t in textos if t):
        y = 24 + i * 24
        cv2.rectangle(annotated_frame, (0, y - 18), (annotated_frame.shape[1], y + 6), (0, 0, 0), -1)
        cv2.putText(annotated_frame, texto, (8, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.imshow("Deteccion en tiempo real", annotated_frame)

    # Con fotos quietas no hace falta ir a toda velocidad: 30 ms entre vueltas
    # bastan para que la ventana responda y el reenvio de 500 ms se cumpla.
    if cv2.waitKey(30 if imagenes else 1) & 0xFF == ord("q"):
        break

# Al salir se mandan los LEDs a cero en vez de esperar los 2 s del apagado de
# seguridad, y se liberan camara, ventana y puerto.
if ser is not None:
    try:
        ser.write(b"00\n")
    except serial.SerialException:
        pass
    ser.close()
if cap is not None:
    cap.release()
cv2.destroyAllWindows()
