import sys
from machine import Pin, PWM, Timer

PIN_AMARILLO = 25  # 30% de intensidad -> puño cerrado
PIN_AZUL = 26       # 70% de intensidad -> señal de victoria
PIN_ROJO = 27       # 100% de intensidad -> ambas manos abiertas

pwm_amarillo = PWM(Pin(PIN_AMARILLO), freq=5000, duty=0)
pwm_azul = PWM(Pin(PIN_AZUL), freq=5000, duty=0)
pwm_rojo = PWM(Pin(PIN_ROJO), freq=5000, duty=0)

DUTY_MAX = 1023
INT_30 = int(0.30 * DUTY_MAX)
INT_70 = int(0.70 * DUTY_MAX)
INT_100 = DUTY_MAX

modo_activo = 0
paso_secuencia = 0
timer_modo = Timer(0)


def apagar_todos():
    pwm_amarillo.duty(0)
    pwm_azul.duty(0)
    pwm_rojo.duty(0)


def alternar_led(pwm_objetivo, valor):
    # cada LED revisa su propio estado real en el PWM, no una variable
    # aparte, así que no le afecta lo que hagan los otros dos
    if pwm_objetivo.duty() > 0:
        pwm_objetivo.duty(0)
    else:
        pwm_objetivo.duty(valor)


def avanzar_secuencia_modo1(t):
    # barrido secuencial: amarillo, azul, rojo, y repite
    global paso_secuencia
    apagar_todos()
    paso = paso_secuencia % 3
    if paso == 0:
        pwm_amarillo.duty(DUTY_MAX)
    elif paso == 1:
        pwm_azul.duty(DUTY_MAX)
    else:
        pwm_rojo.duty(DUTY_MAX)
    paso_secuencia += 1


def avanzar_secuencia_modo2(t):
    # parpadeo sincronizado de los tres LEDs
    global paso_secuencia
    if paso_secuencia % 2 == 0:
        pwm_amarillo.duty(DUTY_MAX)
        pwm_azul.duty(DUTY_MAX)
        pwm_rojo.duty(DUTY_MAX)
    else:
        apagar_todos()
    paso_secuencia += 1


def parar_secuencia_si_activa():
    global modo_activo
    if modo_activo != 0:
        modo_activo = 0
        timer_modo.deinit()


def iniciar_modo(modo):
    global modo_activo, paso_secuencia
    apagar_todos()
    modo_activo = modo
    paso_secuencia = 0
    callback = avanzar_secuencia_modo1 if modo == 1 else avanzar_secuencia_modo2
    timer_modo.init(period=200, mode=Timer.PERIODIC, callback=callback)


def detener_modo():
    global modo_activo
    modo_activo = 0
    timer_modo.deinit()
    apagar_todos()


def manejar_comando(comando):
    # FIST, VICTORY y OPEN2 alternan su propio LED sin tocar los otros dos
    if comando == "FIST":
        parar_secuencia_si_activa()
        alternar_led(pwm_amarillo, INT_30)
    elif comando == "FIST_ON":
        parar_secuencia_si_activa()
        pwm_amarillo.duty(INT_30)
    elif comando == "FIST_OFF":
        pwm_amarillo.duty(0)

    elif comando == "VICTORY":
        parar_secuencia_si_activa()
        alternar_led(pwm_azul, INT_70)
    elif comando == "VICTORY_ON":
        parar_secuencia_si_activa()
        pwm_azul.duty(INT_70)
    elif comando == "VICTORY_OFF":
        pwm_azul.duty(0)

    elif comando == "OPEN2":
        parar_secuencia_si_activa()
        alternar_led(pwm_rojo, INT_100)
    elif comando == "OPEN2_ON":
        parar_secuencia_si_activa()
        pwm_rojo.duty(INT_100)
    elif comando == "OPEN2_OFF":
        pwm_rojo.duty(0)

    elif comando == "THUMB_DOWN":
        iniciar_modo(1)
    elif comando == "THUMB_UP":
        iniciar_modo(2)
    elif comando == "NONE":
        detener_modo()


apagar_todos()

# Este archivo debe guardarse como main.py en el ESP32 para que arranque
# solo al encender la placa, sin necesidad de tener Thonny conectado.
# Una vez corriendo, el puerto USB queda libre para que el navegador
# le escriba comandos directamente por Web Serial.
while True:
    linea = sys.stdin.readline()
    if linea:
        comando = linea.strip()
        manejar_comando(comando)
