# Escucha un comando de voz, lo transcribe a texto, le pregunta a la API
# de DeepSeek que intencion tiene ese comando sobre los LEDs, y le manda
# la orden resultante al ESP32 por el puerto serial.

import os
import json
import serial
import speech_recognition as sr

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PUERTO_SERIAL = "COM7"
BAUDIOS = 115200

cliente = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=1)

reconocedor = sr.Recognizer()
microfono = sr.Microphone()

PROMPT_SISTEMA = """
Eres un interprete de comandos de voz para controlar dos LEDs conectados
a un ESP32, uno rojo y uno azul. Vas a recibir una frase en espanol dicha
por una persona. Responde unicamente con un objeto JSON, sin texto
adicional antes ni despues, con hasta tres claves opcionales:

led_rojo: true si el comando pide encenderlo, false si pide apagarlo.
led_azul: true si el comando pide encenderlo, false si pide apagarlo.
show: true si el comando pide un show de luces o un patron de parpadeo.

Solo incluye una clave si el comando la menciona claramente. Si el
comando no tiene relacion con encender, apagar LEDs o hacer un show,
responde con un objeto JSON vacio.
"""

estado = {"led_rojo": False, "led_azul": False}


def escuchar_comando():
    with microfono as fuente:
        reconocedor.adjust_for_ambient_noise(fuente)
        print("Habla ahora...")
        audio = reconocedor.listen(fuente)

    try:
        texto = reconocedor.recognize_google(audio, language="es-CO")
        print("Se entendio:", texto)
        return texto
    except sr.UnknownValueError:
        print("No se logro entender el audio")
        return None
    except sr.RequestError as error:
        print("Error consultando el servicio de reconocimiento de voz:", error)
        return None


def interpretar_comando(texto):
    respuesta = cliente.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": texto},
        ],
        response_format={"type": "json_object"},
    )
    contenido = respuesta.choices[0].message.content
    return json.loads(contenido)


def aplicar_comando(datos):
    if datos.get("show"):
        ser.write(b"SHOW\n")
        print("Enviando show de luces")
        return

    if "led_rojo" in datos:
        estado["led_rojo"] = bool(datos["led_rojo"])
    if "led_azul" in datos:
        estado["led_azul"] = bool(datos["led_azul"])

    linea = ("1" if estado["led_rojo"] else "0") + ("1" if estado["led_azul"] else "0")
    ser.write((linea + "\n").encode())
    print("Estado enviado al ESP32:", linea)


if __name__ == "__main__":
    print("Presiona Enter para hablar, o escribe salir para terminar.")
    while True:
        entrada = input()
        if entrada.strip().lower() == "salir":
            break

        texto = escuchar_comando()
        if texto is None:
            continue

        datos = interpretar_comando(texto)
        if not datos:
            print("El comando no tenia relacion con los LEDs, no se hizo nada.")
            continue

        aplicar_comando(datos)

    ser.close()
