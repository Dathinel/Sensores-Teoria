# Escucha un comando de voz, lo transcribe a texto, le pregunta a la API
# de DeepSeek que intencion tiene ese comando sobre los LEDs, y le manda
# la orden resultante al ESP32 por el puerto serial.
#
# Flujo de una vuelta del bucle principal:
#   voz (o texto escrito) -> texto -> DeepSeek -> JSON de intencion
#   -> validar el JSON -> actualizar el estado -> "10"/"01"/"11"/"00"/"SHOW" -> ESP32
#
# El script esta pensado para poder probarse aunque falte alguna pieza:
#   - Sin ESP32 conectado: no truena, solo muestra en pantalla lo que habria mandado.
#   - Sin microfono (o sin pyaudio instalado): se escribe el comando con el teclado.
#   - Sin clave de DeepSeek o sin internet: usa un interprete sencillo por palabras
#     clave, avisando en pantalla que no es el modelo de lenguaje.
#   - Esos dos modos tambien se pueden forzar: --texto (no abre el microfono)
#     y --sin-clave (no consulta DeepSeek). --puerto COMx cambia el puerto.

import argparse
import os
import json
import re
import time
import unicodedata

import serial

from dotenv import load_dotenv

# load_dotenv() lee el archivo .env de esta carpeta y copia sus lineas
# (DEEPSEEK_API_KEY=...) a las variables de entorno del proceso. Asi la clave
# nunca queda escrita dentro del codigo que se sube a GitHub.
load_dotenv()

# Opciones de linea de comandos, todas opcionales (sin ninguna, el script se
# comporta como siempre). Sirven para forzar un modo de prueba aunque el PC si
# tenga microfono o el .env si tenga clave; las usa la app de la práctica (ABRIR.bat, motor en _lanzador/lanzador.py).
opciones = argparse.ArgumentParser(description="Asistente de voz para dos LEDs")
opciones.add_argument("--texto", action="store_true",
                      help="no abrir el microfono: solo comandos escritos")
opciones.add_argument("--sin-clave", action="store_true",
                      help="no usar DeepSeek aunque haya clave: interprete por palabras clave")
opciones.add_argument("--puerto", default="COM7",
                      help="puerto serial del ESP32 (por defecto COM7)")
args = opciones.parse_args()

# El numero del puerto cambia en cada computadora: revisarlo en el
# Administrador de dispositivos (Puertos COM y LPT) con el ESP32 conectado.
PUERTO_SERIAL = args.puerto
# Tiene que ser la misma velocidad que usa MicroPython en el USB del ESP32 (115200).
BAUDIOS = 115200


# ------------------------------------------------------------------
# Conexion con el ESP32 (opcional)
# ------------------------------------------------------------------
# Si el puerto no existe o lo tiene abierto otro programa (Thonny, por
# ejemplo), serial.Serial lanza SerialException. En vez de terminar el
# script ahi, se sigue sin ESP32: cada orden se imprime en pantalla para
# poder verificar toda la cadena voz -> DeepSeek -> orden sin el hardware.
try:
    # timeout=1 solo afecta a lecturas bloqueantes; aqui solo se lee lo que ya
    # este en el buffer (ver leer_respuestas_esp32), asi que nunca se espera.
    ser = serial.Serial(PUERTO_SERIAL, BAUDIOS, timeout=1)
    # Abrir el puerto reinicia el ESP32 (la linea DTR del USB va a su pin EN):
    # se esperan 2 s a que arranque main.py, si no la primera orden se perderia
    # (igual que en deteccion_pc.py del tema 3). Sin ESP32 no se espera nada.
    time.sleep(2)
    print("ESP32 conectado en", PUERTO_SERIAL)
except serial.SerialException as error:
    ser = None
    print("No se pudo abrir", PUERTO_SERIAL, "->", error)
    print("Se sigue SIN ESP32: las ordenes solo se muestran en pantalla.")

# Ultima linea cruda que mando el ESP32. Es la mejor pista cuando "no pasa
# nada": si nunca cambia, el ESP32 no esta recibiendo/contestando; si cambia
# pero dice IGNORADO, el problema es de formato, no de cable.
ultima_linea_esp32 = None


# ------------------------------------------------------------------
# Cliente de DeepSeek (opcional)
# ------------------------------------------------------------------
# DeepSeek expone una API con el mismo formato que la de OpenAI, por eso se
# usa la libreria oficial `openai` cambiando solo base_url y la clave.
# Se usa os.environ.get (y no os.environ[...]) para que, si falta el .env,
# el script no truene con KeyError sino que pase al interprete por reglas.
CLAVE_DEEPSEEK = os.environ.get("DEEPSEEK_API_KEY")
cliente = None
if args.sin_clave:
    print("--sin-clave: se usara el interprete por palabras clave (no se consulta DeepSeek).")
elif CLAVE_DEEPSEEK and CLAVE_DEEPSEEK != "tu_api_key_aqui":
    from openai import OpenAI

    cliente = OpenAI(api_key=CLAVE_DEEPSEEK, base_url="https://api.deepseek.com")
else:
    print("No hay DEEPSEEK_API_KEY en el .env: se usara el interprete por palabras clave.")


# ------------------------------------------------------------------
# Microfono (opcional)
# ------------------------------------------------------------------
# sr.Microphone() necesita pyaudio. Si no esta instalado o no hay microfono,
# se sigue funcionando escribiendo el comando con el teclado.
sr = None
microfono = None
if args.texto:
    print("--texto: no se abre el microfono, escribe los comandos con el teclado.")
else:
    try:
        import speech_recognition as sr

        reconocedor = sr.Recognizer()
        microfono = sr.Microphone()
    except (ImportError, AttributeError, OSError) as error:
        sr = None
        microfono = None
        print("Sin microfono disponible (" + str(error) + "): escribe los comandos con el teclado.")


# El prompt de sistema es la "regla del juego" para el modelo: le dice que
# SOLO responda un JSON con tres claves posibles. Asi el programa nunca tiene
# que entender una frase libre como "listo, ya prendi el rojo".
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

# Estado recordado de cada LED. El modelo solo devuelve lo que la frase
# menciona ("enciende el rojo" no dice nada del azul), asi que el script
# guarda el estado completo y solo cambia la parte mencionada.
estado = {"led_rojo": False, "led_azul": False}

# Lista blanca: las unicas claves que el script acepta del JSON. Cualquier
# otra cosa que invente el modelo se descarta antes de tocar el hardware.
CLAVES_VALIDAS = ("led_rojo", "led_azul", "show")


def escuchar_comando():
    """Graba una frase del microfono y la devuelve transcrita, o None."""
    try:
        with microfono as fuente:
            # Mide ~1 s de ruido de fondo para fijar el umbral de energia a partir
            # del cual se considera que alguien empezo a hablar.
            reconocedor.adjust_for_ambient_noise(fuente)
            print("Habla ahora...")
            # listen() corta sola cuando detecta silencio despues de la frase.
            audio = reconocedor.listen(fuente)
    except OSError as error:
        # El microfono existia al arrancar pero ya no se puede abrir (se
        # desconecto, o lo tiene otro programa): se avisa y se sigue con texto.
        print("No se pudo abrir el microfono (" + str(error) + "): escribe el comando.")
        return None

    try:
        # Servicio gratuito de Google (necesita internet); es-CO = espanol de Colombia.
        texto = reconocedor.recognize_google(audio, language="es-CO")
        print("Se entendio:", texto)
        return texto
    except sr.UnknownValueError:
        print("No se logro entender el audio")
        return None
    except sr.RequestError as error:
        print("Error consultando el servicio de reconocimiento de voz:", error)
        return None


def interpretar_por_reglas(texto):
    """Plan B sin DeepSeek: busca palabras clave. Mucho mas rigido que el
    modelo (no entiende frases raras), pero permite probar sin clave/internet."""
    # Minusculas y SIN tildes: Google transcribe con tildes ("enciéndeme",
    # "apágalo", "préndelo") y la raiz "enciend" no coincide con "enciénd".
    # NFD separa cada letra de su tilde (categoria "Mn") y aqui se descartan.
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    datos = {}
    if any(p in t for p in ("show", "espectaculo", "espectáculo", "parpade", "fiesta")):
        datos["show"] = True
        return datos

    # La frase se lee POR PARTES, separadas por "y", comas, "pero", "luego"...
    # Cada verbo manda sobre los colores que vienen despues de el, hasta el
    # siguiente verbo. Antes se buscaba un solo verbo en toda la frase y
    # "enciende el rojo y apaga el azul" apagaba LOS DOS (bastaba con que
    # apareciera "apaga" en cualquier lado).
    # Si una parte no trae verbo ("prende el rojo y el azul"), hereda el de la
    # parte anterior.
    partes = re.split(r",|\by\b|\be\b|\bpero\b|\bluego\b|\bdespues\b|\bdespués\b", t)
    valor = None
    for parte in partes:
        # "deja el azul" / "manten el rojo": ese LED NO se toca (sin esto,
        # "apaga el rojo pero deja el azul" heredaba el "apaga" y apagaba los dos).
        if any(p in parte for p in ("deja", "manten", "mantén")):
            valor = None
            continue
        # "apaga" se revisa ANTES que "activa", porque "desactiva" contiene "activa".
        if any(p in parte for p in ("apaga", "desactiva", "quita")):
            valor = False
        elif any(p in parte for p in ("enciend", "prend", "activa", "pon", "dale")):
            valor = True
        if valor is None:
            continue  # todavia no aparece ningun verbo
        ambos = any(p in parte for p in ("los dos", "ambos", "todo", "todas"))
        if ambos or "roj" in parte:
            datos["led_rojo"] = valor
        if ambos or "azul" in parte:
            datos["led_azul"] = valor
    return datos


def interpretar_comando(texto):
    """Devuelve el JSON de intencion como diccionario de Python."""
    if cliente is None:
        print("(interprete por palabras clave, sin DeepSeek)")
        return interpretar_por_reglas(texto)

    try:
        respuesta = cliente.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": texto},
            ],
            # Obliga a la API a devolver JSON valido en vez de texto libre.
            response_format={"type": "json_object"},
        )
        contenido = respuesta.choices[0].message.content
        print("DeepSeek respondio:", contenido)
        return json.loads(contenido)
    except Exception as error:  # sin internet, clave revocada, JSON roto...
        print("Fallo la consulta a DeepSeek (" + str(error) + "), se usan palabras clave.")
        return interpretar_por_reglas(texto)


def validar(datos):
    """Deja solo las claves de la lista blanca y con valor booleano de verdad.
    Un modelo de lenguaje puede equivocarse de formato ("si", "on", 1...), y
    nada de eso debe llegar a mover un pin sin revisarse antes."""
    if not isinstance(datos, dict):
        return {}
    return {c: datos[c] for c in CLAVES_VALIDAS if isinstance(datos.get(c), bool)}


def enviar(linea):
    """Manda una linea al ESP32, o solo la muestra si no hay ESP32."""
    global ser
    if ser is None:
        print("[sin ESP32] se habria enviado:", linea)
        return
    try:
        # El "\n" es obligatorio: el ESP32 lee con readline(), que espera el fin de linea.
        ser.write((linea + "\n").encode())
    except serial.SerialException:
        # Se desconecto el cable a mitad de la sesion: en vez de cerrar el
        # programa con un traceback, se sigue sin ESP32 (como al arrancar sin el).
        print("Se perdio el ESP32 (cable desconectado). Se sigue SIN ESP32.")
        ser = None
        print("[sin ESP32] se habria enviado:", linea)


def leer_respuestas_esp32():
    """Drena TODO lo que el ESP32 haya mandado (no una sola linea), sin
    bloquear: solo lee si in_waiting dice que ya hay bytes en el buffer."""
    global ultima_linea_esp32, ser
    if ser is None:
        return
    try:
        while ser.in_waiting > 0:
            linea = ser.readline().decode(errors="replace").strip()
            if linea:
                ultima_linea_esp32 = linea
                print("  ESP32 dice:", linea)
    except serial.SerialException:
        print("Se perdio el ESP32 (cable desconectado). Se sigue SIN ESP32.")
        ser = None


def aplicar_comando(datos):
    # El show tiene prioridad y no cambia el estado guardado: el ESP32
    # restaura solo los LEDs como estaban al terminar la secuencia.
    if datos.get("show"):
        enviar("SHOW")
        print("Enviando show de luces")
        return

    if "led_rojo" in datos:
        estado["led_rojo"] = datos["led_rojo"]
    if "led_azul" in datos:
        estado["led_azul"] = datos["led_azul"]

    # Protocolo de dos caracteres: primero el rojo, despues el azul ("10" = rojo on, azul off).
    linea = ("1" if estado["led_rojo"] else "0") + ("1" if estado["led_azul"] else "0")
    enviar(linea)
    print("Estado enviado al ESP32:", linea)


if __name__ == "__main__":
    if microfono is not None:
        print("Enter = hablar | escribir una frase = usarla como comando | salir = terminar")
    else:
        print("Escribe el comando (por ejemplo: enciende el rojo) | salir = terminar")

    while True:
        leer_respuestas_esp32()
        try:
            entrada = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            # EOF: la entrada venia de un archivo o un pipe y se acabo sin "salir";
            # Ctrl+C: el usuario corto. En los dos casos se cierra ordenado
            # (y se libera el puerto serial abajo) en vez de mostrar un traceback.
            print()
            break
        if entrada.lower() == "salir":
            break

        # Entrada manual: si se escribio algo, se usa tal cual como si fuera la
        # transcripcion de la voz (sirve sin microfono o en un salon ruidoso).
        if entrada:
            texto = entrada
        elif microfono is not None:
            texto = escuchar_comando()
        else:
            continue
        if texto is None:
            continue

        datos = validar(interpretar_comando(texto))
        if not datos:
            print("El comando no tenia relacion con los LEDs, no se hizo nada.")
            continue

        aplicar_comando(datos)
        # Pausa corta para dar tiempo a que el ESP32 conteste "OK ..."; aqui no
        # hay ninguna simulacion corriendo, asi que esperar 0.3 s no traba nada.
        time.sleep(0.3)
        leer_respuestas_esp32()
        if ser is not None and ultima_linea_esp32 is None:
            print("  (el ESP32 todavia no ha contestado nada: revisar que main.py este corriendo)")

    if ser is not None:
        ser.close()
