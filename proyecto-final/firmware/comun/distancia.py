# VL53L0X (laser de distancia) sin bloquear el bucle, y varios en el mismo bus.
#
# El driver (vl53l0x.py, lo descarga firmware/preparar.py; su repositorio no
# tiene licencia y por eso no se guarda en este repo) espera la medicion
# dentro de read(). Aqui solo se llama a read() cuando el sensor YA termino
# (registro de interrupcion 0x13), asi el bucle nunca se queda esperando.
#
# Todos los VL53L0X salen de fabrica con la direccion 0x29. Para tener dos en
# el mismo bus se usan sus pines XSHUT: se apagan todos, se prende uno, se le
# cambia la direccion (registro 0x8A), y asi con el siguiente.

import time

_DIRECCION_FABRICA = 0x29
_REG_DIRECCION = 0x8A
_REG_INTERRUPCION = 0x13


class Laser:
    def __init__(self, i2c, direccion, xshut=None, periodo_ms=33, alcance_mm=1200):
        import vl53l0x
        if xshut is not None:
            xshut.value(1)                         # despertarlo
            time.sleep_ms(5)
            if direccion != _DIRECCION_FABRICA:
                i2c.writeto_mem(_DIRECCION_FABRICA, _REG_DIRECCION, bytes([direccion & 0x7F]))
        self.i2c = i2c
        self.direccion = direccion
        self.alcance = alcance_mm
        self.sensor = vl53l0x.VL53L0X(i2c, direccion)
        self.sensor.start(periodo_ms)              # modo continuo
        self.ultima = None                         # mm, o None si no ve nada
        # Cuantas mediciones lleva. OJO: `ultima` NO se borra cuando el sensor
        # deja de medir (OSError, cable flojo): queda congelada en su ultimo
        # valor, que casi siempre es None = "no ve nada". Quien la use para
        # seguridad tiene que mirar si `medidas` sigue creciendo (la cortina lo
        # hace en firmware/fijo/estacion.py, _revisar_cortina) y tratar una
        # lectura vieja como peligrosa, no como "libre".
        self.medidas = 0
        self.errores = 0                           # lecturas I2C fallidas (diagnostico)

    def actualizar(self):
        """Lee solo si hay una medicion nueva. Devuelve True si la hubo."""
        try:
            if not self.i2c.readfrom_mem(self.direccion, _REG_INTERRUPCION, 1)[0] & 0x07:
                return False
            mm = self.sensor.read()
        except OSError:                            # cable flojo, ruido: no se cae, pero `medidas` no crece
            self.errores += 1
            return False
        self.ultima = None if (mm <= 0 or mm >= self.alcance) else mm
        self.medidas += 1
        return True


def apagar_todos(pines_xshut):
    for p in pines_xshut:
        p.value(0)
    time.sleep_ms(10)
