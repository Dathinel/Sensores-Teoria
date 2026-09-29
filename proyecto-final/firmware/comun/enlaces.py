# Enlaces de comunicacion del firmware (solo MicroPython, en la placa).
#
# - SerialUSB: lee lineas del USB SIN bloquear. El bucle principal no puede
#   quedarse esperando una linea (mismo problema que el `readline()` con
#   timeout que trababa la simulacion del tema 9): se usa select.poll con
#   tiempo 0 y se DRENA todo lo que haya en cada vuelta, no una sola linea.
# - Radio: ESP-NOW entre el ESP32 fijo y el del carro, sin router (el Wi-Fi
#   del PC queda libre para la API del asistente). Se usa la direccion de
#   difusion (ff:ff:ff:ff:ff:ff): no hay que copiar la MAC de cada placa, y
#   como cada mensaje dice su `src`/`dst`, el que no es para uno se ignora.

import sys
import select


class SerialUSB:
    def __init__(self):
        self._sondeo = select.poll()
        self._sondeo.register(sys.stdin, select.POLLIN)
        self._buffer = ""

    def lineas(self):
        """Todas las lineas completas que llegaron desde la vuelta anterior."""
        out = []
        while self._sondeo.poll(0):
            c = sys.stdin.read(1)
            if not c:
                break
            if c == "\n":
                out.append(self._buffer)
                self._buffer = ""
            elif len(self._buffer) < 512:          # una linea con basura no llena la RAM
                self._buffer += c
        return out

    def enviar(self, texto):
        sys.stdout.write(texto)


class Radio:
    DIFUSION = b"\xff" * 6

    def __init__(self):
        import network
        import espnow
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        sta.disconnect()                           # ESP-NOW no necesita router
        self._e = espnow.ESPNow()
        self._e.active(True)
        self._e.add_peer(self.DIFUSION)
        self.demasiado_grandes = 0

    def enviar(self, texto):
        datos = texto.encode()
        if len(datos) > 250:                       # limite de un paquete ESP-NOW
            # No deberia pasar: el carro recorta sus mensajes antes de
            # encolarlos (protocolo.recortar). Se cuenta para verlo.
            self.demasiado_grandes += 1
            return False
        try:
            self._e.send(self.DIFUSION, datos, False)
            return True
        except OSError:
            return False

    def recibir(self):
        out = []
        while True:
            _, msg = self._e.irecv(0)
            if not msg:
                break
            # Se devuelven los BYTES, sin decodificar: otros grupos del salon
            # usan ESP-NOW en difusion y un paquete suyo puede no ser UTF-8;
            # `.decode()` aqui lanzaba UnicodeError y mataba main.py (con las
            # ruedas en el ultimo PWM). protocolo.parsear_linea lo descarta.
            out.append(bytes(msg))
        return out
