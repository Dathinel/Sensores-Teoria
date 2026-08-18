# Corre YOLOv8 sobre la camara en vivo y le avisa al ESP32, por el puerto
# serial, cada vez que aparece o desaparece una silla o un celular.
#
# Ajustar PUERTO_SERIAL segun el puerto que use el ESP32 en el
# Administrador de dispositivos, por ejemplo "COM5" en Windows
# o "/dev/ttyUSB0" en Linux.

import cv2
import serial
import time
from ultralytics import YOLO

PUERTO_SERIAL = "COM5"
BAUDIOS = 115200

# Nombres exactos de las clases dentro del dataset COCO que usa YOLOv8
OBJETIVOS = ["chair", "cell phone"]

model = YOLO('yolov8n.pt')

ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=1)
time.sleep(2)  # da tiempo a que el ESP32 termine de reiniciar tras abrir el puerto

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("Error al abrir la camara")
    exit()

print("Presiona 'q' para salir.")
estado_anterior = None

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, verbose=False)
    annotated_frame = results[0].plot()

    detectados = set()
    for box in results[0].boxes:
        clase = model.names[int(box.cls[0])]
        if clase in OBJETIVOS:
            detectados.add(clase)

    estado = "".join("1" if objetivo in detectados else "0" for objetivo in OBJETIVOS)

    if estado != estado_anterior:
        ser.write((estado + "\n").encode())
        estado_anterior = estado

    cv2.imshow('Deteccion en tiempo real', annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
ser.close()
