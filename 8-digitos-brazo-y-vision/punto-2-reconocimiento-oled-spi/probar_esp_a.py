# Prueba minima y aislada del ESP-A: manda "DIGIT:5" por el puerto
# serial y muestra TODO lo que responda, sin camara, sin CNN y sin
# Thonny de por medio.
#
# Por que no sirve escribir "DIGIT:5" directo en la consola de Thonny:
# cuando main.py ya esta corriendo y bloqueado en sys.stdin.readline(),
# el REPL de MicroPython no esta "libre" para recibir texto suelto de
# la Shell de Thonny de la forma normal — Thonny intenta mandarlo con
# su protocolo interno de "raw paste" (pensado para pegar/ejecutar
# codigo Python en el REPL, no para escribirle al stdin de un programa
# que ya esta corriendo) y tira "Could not get raw-paste confirmation",
# interrumpiendo main.py con un KeyboardInterrupt. Ese error es de como
# funciona Thonny, no dice nada sobre si esp_a_maestro.py esta bien o
# mal. Este script en cambio abre el puerto con pyserial, exactamente
# como lo hace reconocer_digito.py, asi que prueba lo mismo que
# realmente importa.
#
# Ajustar PUERTO_SERIAL abajo y correrlo con el entorno activado:
#   entorno\Scripts\activate
#   python probar_esp_a.py

import time
import serial

PUERTO_SERIAL = "COM7"
BAUDIOS = 115200

print(f"Abriendo {PUERTO_SERIAL}...")
ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=0.5)
time.sleep(2)  # el ESP32 se reinicia al abrir el puerto; darle tiempo a que arranque

print("Puerto abierto. Leyendo lo que el ESP32 mande solo al arrancar (2 segundos)...")
t0 = time.time()
while time.time() - t0 < 2:
    if ser.in_waiting:
        print("  (arranque) ->", ser.readline().decode(errors="ignore").strip())

print("Mandando DIGIT:5 ...")
ser.write(b"DIGIT:5\n")

print("Esperando respuesta (5 segundos)...")
t0 = time.time()
recibido_algo = False
while time.time() - t0 < 5:
    if ser.in_waiting:
        linea = ser.readline().decode(errors="ignore").strip()
        print("  <- recibido:", repr(linea))
        recibido_algo = True

if not recibido_algo:
    print("No llego NADA de vuelta en 5 segundos.")
    print("Esto confirma que el problema esta en el ESP-A o en el cable/puerto,")
    print("no en como reconocer_digito.py lee la respuesta.")
else:
    print("Si arriba aparece 'REENVIADO:5', el ESP-A esta funcionando perfecto")
    print("y el problema estaria en otro lado (revisar PUERTO_SERIAL en reconocer_digito.py).")

ser.close()
