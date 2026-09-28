# Firmware del ESP32 para el control de iluminacion por gestos.
#
# La pagina gesture_control.html reconoce el gesto con MediaPipe y manda
# por el cable USB (Web Serial, 115200 baudios) una palabra por linea:
#
#   FIST / VICTORY / OPEN2        -> alterna (prende o apaga) su LED
#   FIST_ON / VICTORY_ON / ...    -> lo prende (modo "automatico" y botones sostenidos)
#   FIST_OFF / VICTORY_OFF / ...  -> lo apaga
#   THUMB_DOWN                    -> Modo 1: barrido amarillo -> azul -> rojo
#   THUMB_UP                      -> Modo 2: parpadeo de los tres a la vez
#   NONE                          -> detiene cualquier modo y apaga todo
#
# Por cada linea recibida contesta "OK <comando>" (o "? <comando>" si no
# la reconoce). La pagina muestra esa respuesta como "ultima linea
# recibida": si nunca aparece, el problema es la conexion o que main.py
# no esta corriendo; si aparece "?", el problema es el texto enviado.
#
# Este archivo debe guardarse como main.py en el ESP32 para que arranque
# solo al encender la placa, sin necesidad de tener Thonny conectado.
# Una vez corriendo, el puerto USB queda libre para que el navegador le
# escriba comandos directamente por Web Serial (cerrar Thonny antes: dos
# programas no pueden tener abierto el mismo puerto a la vez).

import sys
from machine import Pin, PWM, Timer

PIN_AMARILLO = 25  # 30% de intensidad -> puño cerrado
PIN_AZUL = 26      # 70% de intensidad -> señal de victoria
PIN_ROJO = 27      # 100% de intensidad -> ambas manos abiertas

# PWM: el pin se prende y apaga muy rapido y el LED "promedia" ese
# encendido. El ciclo de trabajo (duty) es la fraccion del tiempo que el
# pin pasa en alto: 30% del tiempo prendido = el ojo lo ve a ~30% de
# brillo. 5000 Hz es muy por encima de lo que el ojo percibe como
# parpadeo (~60 Hz), asi que la luz se ve continua.
pwm_amarillo = PWM(Pin(PIN_AMARILLO), freq=5000, duty=0)
pwm_azul = PWM(Pin(PIN_AZUL), freq=5000, duty=0)
pwm_rojo = PWM(Pin(PIN_ROJO), freq=5000, duty=0)

# En MicroPython para ESP32, duty() va de 0 (siempre apagado) a 1023
# (siempre prendido): 10 bits de resolucion. Los porcentajes del
# enunciado se pasan a esa escala.
DUTY_MAX = 1023
INT_30 = int(0.30 * DUTY_MAX)   # 306
INT_70 = int(0.70 * DUTY_MAX)   # 716
INT_100 = DUTY_MAX

# Los modos 1 y 2 son "interrupciones" (asi las llama el enunciado): un
# Timer por hardware llama a la funcion del modo cada PERIODO_MODO_MS
# por su cuenta, sin depender del bucle principal. Por eso las luces
# siguen animandose aunque el bucle este esperando la siguiente linea en
# sys.stdin.readline().
PERIODO_MODO_MS = 200  # 5 cambios por segundo: se nota la secuencia sin marear

modo_activo = 0        # 0 = ninguno, 1 = barrido, 2 = parpadeo
paso_secuencia = 0
timer_modo = Timer(0)


def apagar_todos():
    pwm_amarillo.duty(0)
    pwm_azul.duty(0)
    pwm_rojo.duty(0)


def alternar_led(pwm_objetivo, valor):
    # Cada LED revisa su propio estado real en el PWM, no una variable
    # aparte, asi que no le afecta lo que hagan los otros dos (y nunca
    # puede quedar "desincronizado" de lo que de verdad muestra el pin).
    if pwm_objetivo.duty() > 0:
        pwm_objetivo.duty(0)
    else:
        pwm_objetivo.duty(valor)


def avanzar_secuencia_modo1(t):
    # Barrido secuencial: amarillo, azul, rojo, y repite. El % 3 hace que
    # el contador de pasos de la vuelta 0,1,2,0,1,2...
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
    # Parpadeo sincronizado de los tres LEDs: pasos pares prendidos,
    # impares apagados (200 ms cada uno -> 2.5 parpadeos por segundo).
    global paso_secuencia
    if paso_secuencia % 2 == 0:
        pwm_amarillo.duty(DUTY_MAX)
        pwm_azul.duty(DUTY_MAX)
        pwm_rojo.duty(DUTY_MAX)
    else:
        apagar_todos()
    paso_secuencia += 1


def parar_secuencia_si_activa():
    # Si un modo esta corriendo y llega un gesto de LED fijo, se detiene
    # el timer y se apaga todo: si no, el timer volveria a pisar el LED
    # recien encendido en su siguiente paso.
    global modo_activo
    if modo_activo != 0:
        modo_activo = 0
        timer_modo.deinit()
        apagar_todos()


def iniciar_modo(modo):
    global modo_activo, paso_secuencia
    apagar_todos()
    modo_activo = modo
    paso_secuencia = 0
    callback = avanzar_secuencia_modo1 if modo == 1 else avanzar_secuencia_modo2
    # init() sobre un timer ya activo lo reconfigura: pasar de modo 1 a
    # modo 2 directamente no deja dos timers corriendo.
    timer_modo.init(period=PERIODO_MODO_MS, mode=Timer.PERIODIC, callback=callback)


def detener_modo():
    global modo_activo
    modo_activo = 0
    timer_modo.deinit()
    apagar_todos()


def manejar_comando(comando):
    """Aplica el comando. Devuelve False si no lo reconoce."""
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
    else:
        return False
    return True


apagar_todos()

while True:
    # readline() se queda esperando hasta que llegue una linea completa
    # (terminada en "\n"). Aqui bloquear no es problema: el ESP32 no
    # tiene nada mas que hacer mientras tanto, y las animaciones de los
    # modos corren aparte, en el Timer.
    linea = sys.stdin.readline()
    if linea:
        comando = linea.strip()
        if not comando:
            continue
        reconocido = manejar_comando(comando)
        print(("OK " if reconocido else "? ") + comando)
