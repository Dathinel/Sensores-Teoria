"""Conexionado exacto de la planta y del carro: fuente unica.

Tres partes:

- `PLANTILLAS`: cada tipo de modulo (placa) con su medida real y sus pines,
  cada uno con su nombre, su posicion en la placa (mm, desde el centro; x a lo
  largo, y a lo ancho) y su tipo (pin macho de header, borne de tornillo,
  conector JST, pad de soldadura, salida de un cable integrado, USB). No se
  modela el chip: lo que importa son las entradas y salidas.
- `DISPOSITIVOS`: cada modulo real del montaje (id -> plantilla).
- `CABLES`: cada cable, con cada uno de sus hilos de un pin a otro
  ("dispositivo.pin"), su color y su funcion.

El visor 3D arma los modulos y dibuja los hilos desde aca, `app.documentos`
genera `docs/conexiones.md` y `tests/sim/test_conexiones.py` verifica que no haya
pines repetidos, que cada pin exista y que los GPIO coincidan con la tabla de
pines de `docs/revision-final.md`. Sin dependencias (no importa PyBullet).
"""

from __future__ import annotations

PASO = 2.54  # paso de los headers (mm)


def _fila(nombres, x0, y, paso=PASO, tipo="macho", eje="x"):
    """Pines en fila: `nombres` desde (x0, y) avanzando a lo largo de `eje`."""
    pines = []
    for i, n in enumerate(nombres):
        if n is None:
            continue
        x, yy = (x0 + i * paso, y) if eje == "x" else (x0, y + i * paso)
        pines.append({"n": n, "x": round(x, 3), "y": round(yy, 3), "tipo": tipo})
    return pines


# ---------------------------------------------------------------------------
# Placas de expansion GVS con su ESP32 (como las de los labs)
# ---------------------------------------------------------------------------

# ESP32 DevKit V1 de 38 pines (antena a la izquierda, -x; USB a la derecha).
# Header de arriba (+y) y de abajo (-y), leidos de la antena al USB.
# Pinout REAL (corregido el 2026-09-27, estaba espejado): con la antena ARRIBA y los
# componentes hacia quien mira, el header de EN queda a la IZQUIERDA; con la antena a -x y
# vista desde arriba, ese lado es -y ("abajo"). Igual en app/visor3d/piezas/electronica.js.
ESP38_ABAJO = ["3V3", "EN", "G36", "G39", "G34", "G35", "G32", "G33", "G25", "G26", "G27", "G14", "G12",
               "GND", "G13", "SD2", "SD3", "CMD", "5V"]
ESP38_ARRIBA = ["GND", "G23", "G22", "TX", "RX", "G21", "GND", "G19", "G18", "G5", "G17", "G16", "G4", "G0",
                "G2", "G15", "SD1", "SD0", "CLK"]
# ESP32 DevKit V1 de 30 pines (el de los labs; para el carro).
ESP30_ABAJO = ["EN", "G36", "G39", "G34", "G35", "G32", "G33", "G25", "G26", "G27", "G14", "G12", "G13", "GND", "VIN"]
ESP30_ARRIBA = ["G23", "G22", "TX", "RX", "G21", "G19", "G18", "G5", "G17", "G16", "G4", "G2", "G15", "GND", "3V3"]


def _es_gpio(n: str) -> bool:
    return n.startswith("G") and n[1:].isdigit()


def _shield(arriba, abajo, largo, ancho, x_extremo_usb):
    """Placa de expansion GVS: en cada fila de un GPIO, tres pines G (junto
    al ESP32), V (al medio) y S (afuera), como en el shield del lab 4 (el
    jumper deja V en 3,3 V). Mas un header I2C (21/22), bloques de GND,
    5 V y 3V3, el USB del ESP32 y el jack DC."""
    n = len(arriba)
    x0 = -(n - 1) * PASO / 2
    pines = []
    for lado, filas, s in (("arriba", arriba, 1), ("abajo", abajo, -1)):
        for i, nom in enumerate(filas):
            if not _es_gpio(nom):
                continue
            x = x0 + i * PASO
            for col, dy in (("G", 17.78), ("V", 20.32), ("S", 22.86)):
                pines.append({"n": f"{nom}.{col}", "x": round(x, 3), "y": round(s * dy, 3), "tipo": "macho"})
    # Headers del ESP32 (solo para verlos; los cables van al GVS).
    esp = [{"n": f"esp.{nom}.{i}", "x": round(x0 + i * PASO, 3), "y": round(s * 12.7, 3), "tipo": "hembra"}
           for filas, s in ((arriba, 1), (abajo, -1)) for i, nom in enumerate(filas)]
    xe = x0 + n * PASO + 3
    bloques = (_fila(["I2C.GND", "I2C.VCC", "I2C.SCL", "I2C.SDA"], xe, -9.5, eje="y")
               + _fila(["GND.1", "GND.2", "GND.3"], xe, 4.0, eje="y")
               + _fila(["5V.1", "5V.2"], xe + PASO, 4.0, eje="y")
               + _fila(["3V3.1", "3V3.2"], xe + 2 * PASO, 4.0, eje="y"))
    otros = [{"n": "USB", "x": x_extremo_usb, "y": 0.0, "tipo": "usb"},
             {"n": "JACK", "x": -largo / 2 + 5, "y": ancho / 2 - 8, "tipo": "jack"}]
    return {"tamano": [largo, ancho, 1.6], "color": "#1b1d22", "pines": pines + esp + bloques + otros,
            "partes": [{"caja": [n * PASO + 2, 28.3, 1.6], "p": [0, 0, 11.0], "color": "#16181c", "nombre": "ESP32 DevKit"},
                       {"caja": [18, 25.5, 3.2], "p": [-(n * PASO) / 2 + 12, 0, 13.4], "color": "#b8bcc2", "metal": True},
                       {"caja": [7, 8, 3], "p": [n * PASO / 2 - 1, 0, 13.6], "color": "#c9ccd1", "metal": True},
                       {"caja": [n * PASO, 2.5, 9], "p": [0, 12.7, 6.1], "color": "#111111"},
                       {"caja": [n * PASO, 2.5, 9], "p": [0, -12.7, 6.1], "color": "#111111"},
                       {"caja": [9, 11, 11], "p": [-largo / 2 + 5, ancho / 2 - 8, 6.4], "color": "#111111"}]}


def _dos_filas(izq, der, sep, x_centro=0.0, y_centro=0.0, tipo="macho"):
    """Dos filas de pines enfrentadas (a lo largo de y), separadas `sep` mm."""
    a = _fila(izq, x_centro - sep / 2, y_centro - (len(izq) - 1) * PASO / 2, tipo=tipo, eje="y")
    b = _fila(der, x_centro + sep / 2, y_centro - (len(der) - 1) * PASO / 2, tipo=tipo, eje="y")
    return a + b


def _bornes(nombres, x0, y, paso=5.0, eje="x"):
    return _fila(nombres, x0, y, paso=paso, tipo="borne", eje=eje)


# ---------------------------------------------------------------------------
# Plantillas
# ---------------------------------------------------------------------------

def _pca9685():
    pines = _fila(["IN.GND", "IN.OE", "IN.SCL", "IN.SDA", "IN.VCC", "IN.V+"], -28.5, -6.35, eje="y")
    pines += _fila(["OUT.GND", "OUT.OE", "OUT.SCL", "OUT.SDA", "OUT.VCC", "OUT.V+"], 28.5, -6.35, eje="y")
    for k in range(16):
        x = -21.6 + k * PASO + (k // 4) * 1.4
        pines += [{"n": f"PWM{k}", "x": round(x, 3), "y": -4.4, "tipo": "macho"},
                  {"n": f"V+{k}", "x": round(x, 3), "y": -6.94, "tipo": "macho"},
                  {"n": f"GND{k}", "x": round(x, 3), "y": -9.48, "tipo": "macho"}]
    pines += _bornes(["T.V+", "T.GND"], -2.5, 8.0)
    return {"tamano": [62, 25.4, 1.6], "color": "#4b2780", "pines": pines,
            "partes": [{"cilindro": [5, 13], "p": [14, 7, 7.3], "color": "#1a3a8a", "nombre": "1000 µF"}]}


PLANTILLAS: dict[str, dict] = {
    "shield38": _shield(ESP38_ARRIBA, ESP38_ABAJO, 80, 62, 29.0),
    "shield30": _shield(ESP30_ARRIBA, ESP30_ABAJO, 68, 53, 23.0),
    "pca9685": _pca9685(),
    # Placa perforada con dos A4988 (cada uno con su 100 µF en VMOT): bornes
    # de los motores y de VMOT, header de logica.
    "placa_drivers": {
        "tamano": [70, 45, 1.6], "color": "#b88a4a",
        "pines": (_bornes(["M.1A", "M.1B", "M.2A", "M.2B"], -30, 17.5) + _bornes(["V.1A", "V.1B", "V.2A", "V.2B"], 7.5, 17.5)
                  + _bornes(["VMOT", "GNDP"], 25, -2.5, eje="y")
                  + _fila(["M.STEP", "M.DIR", "V.STEP", "V.DIR", "EN", "VDD", "GND"], -27, -18)),
        "partes": [{"caja": [15.2, 20.3, 1.6], "p": [-16, 2, 11], "color": "#b3243a", "nombre": "A4988"},
                   {"caja": [9, 9, 8], "p": [-16, 2, 16.5], "color": "#a9b1bb", "metal": True},
                   {"caja": [15.2, 20.3, 1.6], "p": [9, 2, 11], "color": "#b3243a", "nombre": "A4988"},
                   {"caja": [9, 9, 8], "p": [9, 2, 16.5], "color": "#a9b1bb", "metal": True},
                   {"cilindro": [3.2, 9], "p": [22, 12, 5.3], "color": "#1a1a1a"},
                   {"cilindro": [3.2, 9], "p": [-2, 12, 5.3], "color": "#1a1a1a"}]},
    "uln2003": {
        "tamano": [35, 32, 1.6], "color": "#1f6b3a",
        "pines": (_fila(["IN1", "IN2", "IN3", "IN4", "IN5", "IN6", "IN7"], -14.5, -7.6, eje="y")
                  + _fila(["−", "+"], 11.0, -13.0) + [{"n": "MOTOR", "x": 4.0, "y": 12.0, "tipo": "jst"}]),
        "partes": [{"caja": [19, 6.5, 3.5], "p": [0, -2, 3.4], "color": "#111111", "nombre": "ULN2003"}]},
    # Empalme soldado con termoencogible (ahorro 2026-10-24: reemplaza la bornera X2, la placa de
    # los optoacopladores y la del reparto I2C). Un solo "pin" J que junta todos sus hilos (hasta 5:
    # mas no se sueldan bien en un termoencogible de 6 mm). Acostado sobre la placa de montaje.
    "empalme": {"tamano": [22, 7, 7], "color": "#151515",
                "pines": [{"n": "J", "x": 0, "y": 0, "tipo": "empalme"}], "partes": []},
    # Buck XL4015 5 A de los servos (modulo CC/CV tipico de 54 x 23 mm, un disipador, trimmer de
    # voltaje y de corriente): bornes IN a -x y OUT a +x. El de corriente se deja en ~4,5 A.
    "xl4015": {
        "tamano": [54, 23, 1.6], "color": "#1d4f9c",
        "pines": _bornes(["IN+", "IN-"], -23, -2.5, eje="y") + _bornes(["OUT+", "OUT-"], 23, -2.5, eje="y"),
        "partes": [{"caja": [12, 13, 10], "p": [-8, 3.5, 5.8], "color": "#a9b1bb", "metal": True},
                   {"cilindro": [6, 7], "p": [8, 4, 4.3], "color": "#2c2c2c"},
                   {"caja": [9.5, 4.8, 10], "p": [12.5, -7, 5.8], "color": "#2d6fd0", "nombre": "ajuste"}]},
    "lm2596": {  # buck 5 V 3 A
        "tamano": [43, 21, 1.6], "color": "#1d4f9c",
        "pines": [{"n": "IN+", "x": -19, "y": 8, "tipo": "pad"}, {"n": "IN-", "x": -19, "y": -8, "tipo": "pad"},
                  {"n": "OUT+", "x": 19, "y": 8, "tipo": "pad"}, {"n": "OUT-", "x": 19, "y": -8, "tipo": "pad"}],
        "partes": [{"caja": [12, 12, 7], "p": [-6, 0, 4.3], "color": "#2b2b2b"},
                   {"cilindro": [4, 10], "p": [8, 4, 5.8], "color": "#1a1a1a"},
                   {"caja": [7, 4, 8], "p": [8, -6, 4.8], "color": "#2d6fd0"}]},
    "fuente60": {  # fuente 12 V 5 A 60 W de caja metalica (generica: 110 x 78 x 36 mm)
        "tamano": [110, 78, 36], "color": "#b9bec6",
        "pines": _bornes(["L", "N", "PE", "-V1", "-V2", "+V1", "+V2"], 48.5, -28.5, paso=9.5, eje="y"),
        "partes": []},
    # Fusible principal (uno solo, en el +12 V a la salida de la fuente): portafusible de cuchilla
    # de 1 via con su fusible ATO; borne de entrada (-x) y de salida (+x).
    "portafusible1": {"tamano": [30, 20, 11], "color": "#151515",
                      "pines": [{"n": "IN", "x": -10, "y": 0, "tipo": "borne"}, {"n": "OUT", "x": 10, "y": 0, "tipo": "borne"}],
                      "partes": [{"caja": [4, 12, 9], "p": [0, 0, 15.5], "color": "#c8a165"}]},
    # Cable de poder de la fuente (con su enchufe, a una multitoma con interruptor): entra a la caja
    # por un agujero de la pared derecha con una brida de alivio por dentro (sin conector IEC).
    "salida_red": {"tamano": [12, 12, 6], "color": "#111111",
                   "pines": [{"n": "L", "x": 0, "y": -3, "tipo": "pad"}, {"n": "N", "x": 0, "y": 0, "tipo": "pad"},
                             {"n": "PE", "x": 0, "y": 3, "tipo": "pad"}], "partes": []},
    "portatil": {"tamano": [300, 200, 12], "color": "#3a3f47",
                 "pines": [{"n": "USB1", "x": 150, "y": 30, "tipo": "usb"}, {"n": "USB2", "x": 150, "y": 50, "tipo": "usb"},
                           {"n": "USB3", "x": -150, "y": 0, "tipo": "usb"}],
                 "partes": []},

    # --- Sensores y actuadores de la planta ---
    # Headers "acodado": [sx, sy] = pines a 90 grados, acostados sobre la placa y saliendo hacia
    # ese lado (como las piezas reales de app/visor3d/piezas/sensores.js).
    "fc51": {"tamano": [32, 14, 1.6], "color": "#1d4f9c",
             "pines": [dict(p, acodado=[1, 0]) for p in _fila(["OUT", "GND", "VCC"], 14.0, -PASO, eje="y")],
             "partes": [{"cilindro": [2.5, 5], "p": [-13, 3, -2.5], "color": "#e8e8e8", "nombre": "emisor"},
                        {"cilindro": [2.5, 5], "p": [-13, -3, -2.5], "color": "#111111"},
                        {"caja": [5, 5, 4], "p": [2, 0, 2.8], "color": "#2d6fd0"}]},
    "ky003": {"tamano": [18.5, 15, 1.6], "color": "#1f5f2e",
              "pines": _fila(["S", "+", "−"], 7.0, -PASO, eje="y"),
              "partes": [{"caja": [4.5, 3.0, 3.5], "p": [-6.0, 0, -1.75], "color": "#111111", "nombre": "A3144"}]},
    "gy530": {"tamano": [25, 10.7, 1.6], "color": "#6b1fa3",
              "pines": _fila(["VIN", "GND", "SCL", "SDA", "GPIO1", "XSHUT"], -6.35, 3.5),
              "partes": [{"caja": [4.4, 2.4, 1.0], "p": [0, -1.8, -0.5], "color": "#111111", "nombre": "VL53L0X"}]},
    # Sensor de proximidad M18 con su cable de 3 hilos (sale del cuerpo).
    "npn_m18": {"tamano": [18, 18, 0], "color": "#b8bec6",
                "pines": [{"n": c, "x": 0, "y": 0, "tipo": "cable"} for c in ("CAFE", "AZUL", "NEGRO")], "partes": []},
    "nema17": {"tamano": [42, 42, 40], "color": "#2b2f36",   # 17HS4401: 42,3 x 42,3 x 40 mm
               "pines": [{"n": "JST", "x": 0, "y": 0, "tipo": "jst"}], "partes": []},
    "byj48": {"tamano": [28, 28, 19], "color": "#c9c9c9",
              "pines": [{"n": "CABLE", "x": 0, "y": 0, "tipo": "cable"}], "partes": []},
    "servo": {"tamano": [23, 12, 22], "color": "#2458b3",
              "pines": [{"n": "CABLE", "x": 0, "y": 0, "tipo": "cable"}], "partes": []},
    "tira_led": {"tamano": [20, 8, 1], "color": "#f4f7fb",
                 "pines": [{"n": "+5V", "x": -3, "y": 0, "tipo": "pad"}, {"n": "GND", "x": 3, "y": 0, "tipo": "pad"}],
                 "partes": []},
    # Ventilador 4010 de 5 V (0,1 A) de la caja: sus dos hilos salen del marco y entran por un
    # agujero de 4 mm de la pared derecha (anclas pin_ventilador_+5V / GND de piezas/control.js).
    "ventilador4010": {"tamano": [40, 10, 40], "color": "#141517",
                       "pines": [{"n": "+5V", "x": 21.2, "y": 0, "tipo": "cable"}, {"n": "GND", "x": 22.8, "y": 0, "tipo": "cable"}],
                       "partes": []},
    "webcam": {"tamano": [30, 22, 22], "color": "#20242b",
               "pines": [{"n": "USB", "x": 0, "y": 0, "tipo": "cable"}], "partes": []},

    # --- Carro ---
    "tb6612": {"tamano": [20.3, 20.3, 1.6], "color": "#7a2a8c",
               "pines": _dos_filas(["PWMA", "AIN2", "AIN1", "STBY", "BIN1", "BIN2", "PWMB", "GND_L"],
                                   ["VM", "VCC", "GND_P", "AO1", "AO2", "BO2", "BO1", "GND_P2"], 17.8),
               "partes": [{"caja": [7, 5, 1.2], "p": [0, 0, 1.4], "color": "#111111", "nombre": "TB6612"}]},
    # Modulo H206 real: placa 32 x 14 mm, horquilla en la punta -x y header acodado por +x.
    "h206": {"tamano": [32, 14, 1.6], "color": "#1e5aa8",
             "pines": [dict(p, acodado=[1, 0]) for p in _fila(["VCC", "GND", "D0"], 14.0, -PASO, eje="y")],
             "partes": [{"caja": [12, 11, 11], "p": [-9.5, 0, 7.1], "color": "#111111", "nombre": "horquilla"}]},
    # 5 canales a 15 mm: 4 x 15 + 14 = 74 mm de largo (el quinto sensor queda sobre la placa).
    "ir5": {"tamano": [14, 74, 1.6], "color": "#1e5aa8",
            "pines": _fila(["VCC", "GND", "OUT1", "OUT2", "OUT3", "OUT4", "OUT5"], 4.5, -7.6, eje="y"),
            "partes": [{"caja": [6, 10, 5.5], "p": [-3, -30 + 7.5 + i * 15, -2.75], "color": "#1b2b5a"} for i in range(5)]},
    "hcsr04": {"tamano": [45, 20, 1.6], "color": "#1e5aa8",
               "pines": [dict(p, abajo=True) for p in _fila(["VCC", "TRIG", "ECHO", "GND"], -3.8, -8.5)],
               "partes": [{"cilindro": [8, 12], "p": [-13, 1, 6.8], "color": "#c9ccd1", "metal": True},
                          {"cilindro": [8, 12], "p": [13, 1, 6.8], "color": "#c9ccd1", "metal": True},
                          {"caja": [5, 3, 2], "p": [0, 5, 1.8], "color": "#c9ccd1", "metal": True}]},
    "tcrt_mod": {"tamano": [32, 14, 1.6], "color": "#1e5aa8",
                 "pines": [dict(p, acodado=[1, 0]) for p in _fila(["VCC", "GND", "DO", "AO"], 14.0, -3.81, eje="y")],
                 "partes": [{"caja": [6, 10, 5.5], "p": [-13, 0, -2.75], "color": "#1b2b5a", "nombre": "TCRT5000"}]},
    "motor_tt": {"tamano": [28, 21, 21], "color": "#c9ccd1",
                 "pines": [{"n": "M+", "x": 0, "y": 4, "tipo": "pad"}, {"n": "M-", "x": 0, "y": -4, "tipo": "pad"}],
                 "partes": []},
    "pack2s": {"tamano": [41, 76.6, 20.7], "color": "#151515",   # porta 2 x 18650: 76,6 x 41 x 20,7 mm
               "pines": [{"n": "B+", "x": 20.5, "y": 30, "tipo": "pad"}, {"n": "B-", "x": 20.5, "y": -30, "tipo": "pad"}],
               "partes": []},
    "interruptor": {"tamano": [8, 12, 6], "color": "#111111",
                    "pines": [{"n": "1", "x": 0, "y": -3, "tipo": "pad"}, {"n": "2", "x": 0, "y": 3, "tipo": "pad"}],
                    "partes": []},
}

# ---------------------------------------------------------------------------
# Dispositivos (instancias) y su nombre para mostrar
# ---------------------------------------------------------------------------

DISPOSITIVOS: dict[str, dict] = {
    # Caja de control
    "esp32_fijo": {"plantilla": "shield38", "nombre": "ESP32 fijo (DevKit 38P) en placa GVS", "zona": "caja"},
    "pca9685": {"plantilla": "pca9685", "nombre": "PCA9685 (servos)", "zona": "caja"},
    "drivers": {"plantilla": "placa_drivers", "nombre": "Drivers A4988 (monedas M, vasos V)", "zona": "caja"},
    "uln2003": {"plantilla": "uln2003", "nombre": "ULN2003 (carrusel)", "zona": "caja"},
    "buck6": {"plantilla": "xl4015", "nombre": "Buck 6 V 5 A XL4015 (servos)", "zona": "caja"},
    "buck5": {"plantilla": "lm2596", "nombre": "Buck 5 V 3 A", "zona": "caja"},
    "fuente": {"plantilla": "fuente60", "nombre": "Fuente 12 V 5 A", "zona": "caja"},
    "fusible": {"plantilla": "portafusible1", "nombre": "Fusible principal 5 A (lento) en el +12 V", "zona": "caja"},
    "cable_red": {"plantilla": "salida_red", "nombre": "Cable de poder (a la multitoma con interruptor)", "zona": "caja"},
    "ventilador": {"plantilla": "ventilador4010", "nombre": "Ventilador 4010 5 V (saca el aire de los drivers)", "zona": "caja"},
    # Empalmes soldados con termoencogible (en lugar de la bornera X2, los optos y el reparto I2C).
    # El GND sigue en estrella: todos los retornos llegan a los dos bornes -V de la fuente.
    "e12": {"plantilla": "empalme", "nombre": "Empalme +12 V (después del fusible)", "zona": "caja"},
    "e12s": {"plantilla": "empalme", "nombre": "Empalme +12 V de los sensores M18", "zona": "caja"},
    "e5": {"plantilla": "empalme", "nombre": "Empalme +5 V", "zona": "caja"},
    "e5_gnd": {"plantilla": "empalme", "nombre": "Empalme GND de 5 V", "zona": "caja"},
    "egnd": {"plantilla": "empalme", "nombre": "Empalme GND de potencia (a −V1)", "zona": "caja"},
    "egnd_s": {"plantilla": "empalme", "nombre": "Empalme GND de los sensores M18 (a −V2)", "zona": "caja"},
    "capacitivo_s": {"plantilla": "empalme", "nombre": "Señal del capacitivo (diodo + pull-up 10 kΩ)", "zona": "caja"},
    "inductivo_s": {"plantilla": "empalme", "nombre": "Señal del inductivo (diodo + pull-up 10 kΩ)", "zona": "caja"},
    "i2c1_sda": {"plantilla": "empalme", "nombre": "SDA del bus I2C 1 (pull-up 2,2 kΩ)", "zona": "caja"},
    "i2c1_scl": {"plantilla": "empalme", "nombre": "SCL del bus I2C 1 (pull-up 2,2 kΩ)", "zona": "caja"},
    "i2c1_3v3": {"plantilla": "empalme", "nombre": "3,3 V del bus I2C 1", "zona": "caja"},
    "i2c1_gnd": {"plantilla": "empalme", "nombre": "GND del bus I2C 1", "zona": "caja"},
    "pc": {"plantilla": "portatil", "nombre": "Portátil", "zona": "mesa"},
    # Planta
    "presencia": {"plantilla": "fc51", "nombre": "FC-51 presencia (1)", "zona": "planta"},
    "capacitivo": {"plantilla": "npn_m18", "nombre": "Capacitivo LJC18A3 (2)", "zona": "planta"},
    "inductivo": {"plantilla": "npn_m18", "nombre": "Inductivo LJ18A3-8 (3)", "zona": "planta"},
    "hall": {"plantilla": "ky003", "nombre": "Hall KY-003 (6)", "zona": "planta"},
    "vl53_interior": {"plantilla": "gy530", "nombre": "VL53L0X interior (5)", "zona": "planta"},
    "vl53_cortina": {"plantilla": "gy530", "nombre": "VL53L0X cortina (8)", "zona": "planta"},
    "motor_monedas": {"plantilla": "nema17", "nombre": "NEMA17 cinta de monedas", "zona": "planta"},
    "motor_vasos": {"plantilla": "nema17", "nombre": "NEMA17 cinta de vasos", "zona": "planta"},
    "motor_carrusel": {"plantilla": "byj48", "nombre": "28BYJ-48 carrusel", "zona": "planta"},
    "servo_desvio": {"plantilla": "servo", "nombre": "Servo desvío (SG90)", "zona": "planta"},
    "servo_obturador": {"plantilla": "servo", "nombre": "Servo obturador (SG90)", "zona": "planta"},
    "servo_tapas": {"plantilla": "servo", "nombre": "Servo escape de tapas (SG90)", "zona": "planta"},
    "servo_prensa": {"plantilla": "servo", "nombre": "Servo prensa (MG996R)", "zona": "planta"},
    "servo_empujador": {"plantilla": "servo", "nombre": "Servo empujador (MG996R)", "zona": "planta"},
    "servo_canaleta": {"plantilla": "servo", "nombre": "Servo escape canaleta (SG90)", "zona": "planta"},
    "panel_luz": {"plantilla": "tira_led", "nombre": "Panel de luz 5 V", "zona": "planta"},
    "anillo": {"plantilla": "tira_led", "nombre": "Anillo de luz 5 V", "zona": "planta"},
    "cam_cenital": {"plantilla": "webcam", "nombre": "Webcam cenital (4)", "zona": "planta"},
    "cam_vasos": {"plantilla": "webcam", "nombre": "Webcam de vasos (7)", "zona": "planta"},
    # Carro
    "esp32_carro": {"plantilla": "shield30", "nombre": "ESP32 carro (DevKit 30P) en placa GVS", "zona": "carro"},
    "tb6612": {"plantilla": "tb6612", "nombre": "Puente H TB6612FNG", "zona": "carro"},
    "enc_izq": {"plantilla": "h206", "nombre": "Encoder izquierdo H206 (11)", "zona": "carro"},
    "enc_der": {"plantilla": "h206", "nombre": "Encoder derecho H206 (11)", "zona": "carro"},
    "ir_linea": {"plantilla": "ir5", "nombre": "5 infrarrojos de línea TCRT5000 (9)", "zona": "carro"},
    "hcsr04": {"plantilla": "hcsr04", "nombre": "Ultrasónico HC-SR04 (10)", "zona": "carro"},
    "vl53_frontal": {"plantilla": "gy530", "nombre": "Láser VL53L0X (13)", "zona": "carro"},
    "ir_cuna": {"plantilla": "tcrt_mod", "nombre": "Infrarrojo de la cuna TCRT5000 (12)", "zona": "carro"},
    "motor_izq": {"plantilla": "motor_tt", "nombre": "Motor TT izquierdo", "zona": "carro"},
    "motor_der": {"plantilla": "motor_tt", "nombre": "Motor TT derecho", "zona": "carro"},
    "bateria": {"plantilla": "pack2s", "nombre": "2 × 18650 (7,4 V) con BMS", "zona": "carro"},
    "interruptor": {"plantilla": "interruptor", "nombre": "Interruptor + fusible 3 A", "zona": "carro"},
}

# Colores de hilo
ROJO, NEGRO, CAFE, AZUL, NARANJA, AMARILLO, VERDE, BLANCO, MORADO, GRIS = (
    "#d23a2a", "#1a1a1a", "#6b3a1f", "#2d6fd0", "#e8901c", "#e3c22b", "#2da44e", "#e8e8e8", "#8957e5", "#8a939e")
VERDE_AMARILLO = "#9bbf2a"


def _h(a, b, color, funcion):
    return {"de": a, "a": b, "color": color, "funcion": funcion}


def _servo(dev, canal, nombre):
    """Servo: su conector de 3 vias (cafe GND, rojo V+, naranja senal) va
    directo al canal del PCA9685, con extension de 22 AWG."""
    return {"id": f"servo_{canal}", "nombre": f"{nombre} → PCA9685 canal {canal}", "tipo": "servo",
            "conector": "JR 3 vías",
            "hilos": [_h(f"{dev}.CABLE", f"pca9685.PWM{canal}", NARANJA, "señal PWM"),
                      _h(f"{dev}.CABLE", f"pca9685.V+{canal}", ROJO, "6 V"),
                      _h(f"{dev}.CABLE", f"pca9685.GND{canal}", CAFE, "GND")]}


CABLES: list[dict] = [
    # ---------------- Potencia (caja) ----------------
    # Ahorro 2026-10-24: sin entrada IEC, sin bornera X2 y con UN fusible. La fuente trae su cable de
    # poder con enchufe (a una multitoma con interruptor, que es el interruptor general); el +12 V
    # pasa por el fusible principal y se reparte con empalmes soldados. Cada empalme junta como mucho
    # 5 hilos. El GND sigue en estrella: todo vuelve a los bornes -V1 / -V2 de la fuente.
    {"id": "red", "nombre": "Cable de poder de la fuente → multitoma con interruptor", "tipo": "red",
     "externo": "multitoma con interruptor", "hilos": []},
    {"id": "p_red", "nombre": "Cable de poder → fuente (entra con una brida de alivio)", "tipo": "interno", "hilos": [
        _h("cable_red.L", "fuente.L", CAFE, "fase"), _h("cable_red.N", "fuente.N", AZUL, "neutro"),
        _h("cable_red.PE", "fuente.PE", VERDE_AMARILLO, "tierra")]},
    {"id": "p_12", "nombre": "Fuente → fusible principal y GND en estrella", "tipo": "interno", "hilos": [
        _h("fuente.+V1", "fusible.IN", ROJO, "+12 V"), _h("fuente.-V1", "egnd.J", NEGRO, "GND (estrella)"),
        _h("fuente.-V2", "egnd_s.J", NEGRO, "GND (estrella)")]},
    {"id": "p_e12", "nombre": "Fusible principal → empalmes de +12 V", "tipo": "interno", "hilos": [
        _h("fusible.OUT", "e12.J", ROJO, "+12 V"), _h("e12.J", "e12s.J", ROJO, "+12 V sensores")]},
    {"id": "p_buck6", "nombre": "+12 V → buck 6 V (XL4015)", "tipo": "interno", "hilos": [
        _h("e12.J", "buck6.IN+", ROJO, "+12 V"), _h("buck6.IN-", "egnd.J", NEGRO, "GND")]},
    {"id": "p_pca", "nombre": "Buck 6 V → PCA9685 (V+ de los servos)", "tipo": "interno", "hilos": [
        _h("buck6.OUT+", "pca9685.T.V+", ROJO, "+6 V (18 AWG)"), _h("buck6.OUT-", "pca9685.T.GND", NEGRO, "GND (18 AWG)")]},
    {"id": "p_buck5", "nombre": "+12 V → buck 5 V → empalmes de 5 V", "tipo": "interno", "hilos": [
        _h("e12.J", "buck5.IN+", ROJO, "+12 V"), _h("buck5.IN-", "egnd.J", NEGRO, "GND"),
        _h("buck5.OUT+", "e5.J", ROJO, "+5 V"), _h("buck5.OUT-", "e5_gnd.J", NEGRO, "GND")]},
    {"id": "p_drv", "nombre": "+12 V → drivers (VMOT)", "tipo": "interno", "hilos": [
        _h("e12.J", "drivers.VMOT", ROJO, "+12 V"), _h("drivers.GNDP", "egnd.J", NEGRO, "GND")]},
    {"id": "p_uln", "nombre": "Empalmes de 5 V → ULN2003", "tipo": "interno", "hilos": [
        _h("e5.J", "uln2003.+", ROJO, "+5 V"), _h("e5_gnd.J", "uln2003.−", NEGRO, "GND")]},
    {"id": "p_vent", "nombre": "Empalmes de 5 V → ventilador 4010 (0,1 A)", "tipo": "interno", "hilos": [
        _h("e5.J", "ventilador.+5V", ROJO, "+5 V ventilador"), _h("e5_gnd.J", "ventilador.GND", NEGRO, "GND ventilador")]},
    {"id": "p_gnd", "nombre": "GND común ESP32 ↔ estrella", "tipo": "interno", "hilos": [
        _h("esp32_fijo.GND.1", "egnd.J", NEGRO, "GND común")]},

    # ---------------- Logica dentro de la caja ----------------
    {"id": "l_i2c0", "nombre": "ESP32 I2C 0 → PCA9685", "tipo": "dupont", "hilos": [
        _h("esp32_fijo.I2C.SDA", "pca9685.IN.SDA", AZUL, "SDA (G21)"),
        _h("esp32_fijo.I2C.SCL", "pca9685.IN.SCL", AMARILLO, "SCL (G22)"),
        _h("esp32_fijo.I2C.VCC", "pca9685.IN.VCC", ROJO, "3,3 V lógica"),
        _h("esp32_fijo.I2C.GND", "pca9685.IN.GND", NEGRO, "GND")]},
    {"id": "l_drv", "nombre": "ESP32 → drivers (STEP, DIR, EN)", "tipo": "dupont", "hilos": [
        _h("esp32_fijo.G25.S", "drivers.M.STEP", AMARILLO, "STEP monedas"),
        _h("esp32_fijo.G26.S", "drivers.M.DIR", VERDE, "DIR monedas"),
        _h("esp32_fijo.G27.S", "drivers.V.STEP", AMARILLO, "STEP vasos"),
        _h("esp32_fijo.G14.S", "drivers.V.DIR", VERDE, "DIR vasos"),
        _h("esp32_fijo.G13.S", "drivers.EN", BLANCO, "ENABLE común"),
        _h("esp32_fijo.G13.V", "drivers.VDD", ROJO, "3,3 V lógica"),
        _h("esp32_fijo.G13.G", "drivers.GND", NEGRO, "GND lógica")]},
    {"id": "l_uln", "nombre": "ESP32 → ULN2003 (IN1-IN4)", "tipo": "dupont", "hilos": [
        _h("esp32_fijo.G32.S", "uln2003.IN1", AZUL, "bobina 1"), _h("esp32_fijo.G33.S", "uln2003.IN2", MORADO, "bobina 2"),
        _h("esp32_fijo.G23.S", "uln2003.IN3", GRIS, "bobina 3"), _h("esp32_fijo.G4.S", "uln2003.IN4", BLANCO, "bobina 4")]},
    # Sin optoacopladores (2026-10-24): la salida NPN del sensor llega al GPIO por un diodo Schottky
    # BAT85 (catodo hacia el sensor) y el GPIO tiene una pull-up de 10 kΩ a 3,3 V (G35 y G36 no
    # tienen pull-up interno). Con el sensor libre el diodo queda en inverso (aunque el sensor traiga
    # su propia resistencia a 12 V) y el pin lee 3,3 V; al detectar, el NPN lo baja a ~0,5 V:
    # sigue activo en bajo. Diodo y resistencia van soldados en linea, con termoencogible.
    {"id": "l_npn", "nombre": "Capacitivo e inductivo → ESP32 (diodo + pull-up 10 kΩ en línea)", "tipo": "dupont", "hilos": [
        _h("capacitivo_s.J", "esp32_fijo.G35.S", VERDE, "capacitivo (activo en bajo)"),
        _h("esp32_fijo.G35.V", "capacitivo_s.J", ROJO, "pull-up 10 kΩ a 3,3 V (en línea)"),
        _h("inductivo_s.J", "esp32_fijo.G36.S", AMARILLO, "inductivo (activo en bajo)"),
        _h("esp32_fijo.G36.V", "inductivo_s.J", ROJO, "pull-up 10 kΩ a 3,3 V (en línea)")]},
    # Bus I2C 1 sin placa de reparto: los hilos de los dos VL53L0X se sueldan en 4 empalmes y las
    # dos pull-ups de 2,2 kΩ van soldadas en linea entre el empalme de 3,3 V y el de SDA / SCL.
    {"id": "l_i2c1", "nombre": "ESP32 I2C 1 → empalmes del bus (pull-ups 2,2 kΩ en línea)", "tipo": "dupont", "hilos": [
        _h("esp32_fijo.G16.S", "i2c1_sda.J", AZUL, "SDA (G16)"), _h("esp32_fijo.G17.S", "i2c1_scl.J", AMARILLO, "SCL (G17)"),
        _h("esp32_fijo.G16.V", "i2c1_3v3.J", ROJO, "3,3 V"), _h("esp32_fijo.G16.G", "i2c1_gnd.J", NEGRO, "GND"),
        _h("i2c1_3v3.J", "i2c1_sda.J", ROJO, "pull-up 2,2 kΩ de SDA (en línea)"),
        _h("i2c1_3v3.J", "i2c1_scl.J", ROJO, "pull-up 2,2 kΩ de SCL (en línea)")]},

    # ---------------- Campo: planta ----------------
    {"id": "presencia", "nombre": "FC-51 presencia → ESP32 G34", "tipo": "senal", "conector": "Dupont 3 vías", "hilos": [
        _h("presencia.OUT", "esp32_fijo.G34.S", VERDE, "señal"), _h("presencia.GND", "esp32_fijo.G34.G", NEGRO, "GND"),
        _h("presencia.VCC", "esp32_fijo.G34.V", ROJO, "3,3 V")]},
    {"id": "capacitivo", "nombre": "Capacitivo → su diodo (G35) y empalmes de 12 V", "tipo": "sensor12", "hilos": [
        _h("capacitivo.NEGRO", "capacitivo_s.J", NEGRO, "salida NPN (por el diodo BAT85)"),
        _h("capacitivo.CAFE", "e12s.J", CAFE, "+12 V"), _h("capacitivo.AZUL", "egnd_s.J", AZUL, "0 V")]},
    {"id": "inductivo", "nombre": "Inductivo → su diodo (G36) y empalmes de 12 V", "tipo": "sensor12", "hilos": [
        _h("inductivo.NEGRO", "inductivo_s.J", NEGRO, "salida NPN (por el diodo BAT85)"),
        _h("inductivo.CAFE", "e12s.J", CAFE, "+12 V"), _h("inductivo.AZUL", "egnd_s.J", AZUL, "0 V")]},
    {"id": "hall", "nombre": "Hall KY-003 → ESP32 G39", "tipo": "senal", "conector": "Dupont 3 vías", "hilos": [
        _h("hall.S", "esp32_fijo.G39.S", VERDE, "señal (pull-up del módulo)"), _h("hall.+", "esp32_fijo.G39.V", ROJO, "3,3 V"),
        _h("hall.−", "esp32_fijo.G39.G", NEGRO, "GND")]},
    {"id": "vl53_interior", "nombre": "VL53L0X interior → empalmes del bus I2C 1 y XSHUT G18", "tipo": "i2c", "hilos": [
        _h("vl53_interior.VIN", "i2c1_3v3.J", ROJO, "3,3 V"), _h("vl53_interior.GND", "i2c1_gnd.J", NEGRO, "GND"),
        _h("vl53_interior.SCL", "i2c1_scl.J", AMARILLO, "SCL"), _h("vl53_interior.SDA", "i2c1_sda.J", AZUL, "SDA"),
        _h("vl53_interior.XSHUT", "esp32_fijo.G18.S", BLANCO, "XSHUT (dirección 0x30)")]},
    {"id": "vl53_cortina", "nombre": "VL53L0X cortina → empalmes del bus I2C 1 y XSHUT G19", "tipo": "i2c", "hilos": [
        _h("vl53_cortina.VIN", "i2c1_3v3.J", ROJO, "3,3 V"), _h("vl53_cortina.GND", "i2c1_gnd.J", NEGRO, "GND"),
        _h("vl53_cortina.SCL", "i2c1_scl.J", AMARILLO, "SCL"), _h("vl53_cortina.SDA", "i2c1_sda.J", AZUL, "SDA"),
        _h("vl53_cortina.XSHUT", "esp32_fijo.G19.S", BLANCO, "XSHUT (dirección 0x31)")]},
    {"id": "motor_monedas", "nombre": "NEMA17 cinta de monedas → driver M", "tipo": "paso", "conector": "JST-PH 6 → bornes",
     "hilos": [_h("motor_monedas.JST", "drivers.M.1A", NEGRO, "A+"), _h("motor_monedas.JST", "drivers.M.1B", VERDE, "A−"),
               _h("motor_monedas.JST", "drivers.M.2A", ROJO, "B+"), _h("motor_monedas.JST", "drivers.M.2B", AZUL, "B−")]},
    {"id": "motor_vasos", "nombre": "NEMA17 cinta de vasos → driver V", "tipo": "paso", "conector": "JST-PH 6 → bornes",
     "hilos": [_h("motor_vasos.JST", "drivers.V.1A", NEGRO, "A+"), _h("motor_vasos.JST", "drivers.V.1B", VERDE, "A−"),
               _h("motor_vasos.JST", "drivers.V.2A", ROJO, "B+"), _h("motor_vasos.JST", "drivers.V.2B", AZUL, "B−")]},
    {"id": "motor_carrusel", "nombre": "28BYJ-48 → ULN2003 (JST-XH 5)", "tipo": "paso", "conector": "JST-XH 5 vías",
     "hilos": [_h("motor_carrusel.CABLE", "uln2003.MOTOR", c, f) for c, f in
               ((AZUL, "bobina 1"), ("#e07aa8", "bobina 2"), (AMARILLO, "bobina 3"), (NARANJA, "bobina 4"), (ROJO, "+5 V común"))]},
    _servo("servo_desvio", 0, "Servo desvío"),
    _servo("servo_obturador", 1, "Servo obturador"),
    _servo("servo_tapas", 2, "Servo escape de tapas"),
    _servo("servo_prensa", 3, "Servo prensa (MG996R)"),
    _servo("servo_empujador", 4, "Servo empujador (MG996R)"),
    _servo("servo_canaleta", 5, "Servo escape canaleta"),
    # La tira del panel va detras de una resistencia de 3,3 Ω 1 W soldada en linea en su +5 V, del lado de la caja
    # (con termoencogible): deja las dos tiras en <= 1,5 W para no ablandar la caja de luz de PLA (sim/electrica.py).
    {"id": "panel_luz", "nombre": "Panel de luz → empalmes de 5 V (resistencia de 3,3 Ω en línea)", "tipo": "cinco", "hilos": [
        _h("panel_luz.+5V", "e5.J", ROJO, "+5 V por la resistencia de 3,3 Ω 1 W (en línea)"),
        _h("panel_luz.GND", "e5_gnd.J", NEGRO, "GND")]},
    {"id": "anillo", "nombre": "Anillo de luz → empalmes de 5 V", "tipo": "cinco", "hilos": [
        _h("anillo.+5V", "e5.J", ROJO, "+5 V"), _h("anillo.GND", "e5_gnd.J", NEGRO, "GND")]},
    # Sin hub USB (2026-10-24): cada uno a su puerto del portatil (ninguno pasa de 0,35 A; un
    # USB 2.0 da 0,5 A). Los dos del costado derecho para la cenital (el de adelante) y el ESP32
    # (el de atras: asi sus cables no se cruzan), el izquierdo para la webcam de vasos (su cable
    # viene por la izquierda de las mesas).
    {"id": "usb_cenital", "nombre": "Webcam cenital → portátil (USB derecho de adelante)", "tipo": "usb", "hilos": [
        _h("cam_cenital.USB", "pc.USB1", NEGRO, "USB")]},
    {"id": "usb_vasos", "nombre": "Webcam de vasos → portátil (USB izquierdo, con la extensión USB de 1 m)", "tipo": "usb", "hilos": [
        _h("cam_vasos.USB", "pc.USB3", NEGRO, "USB")]},
    {"id": "usb_esp", "nombre": "ESP32 fijo → portátil (USB derecho de atrás, datos y alimentación)", "tipo": "usb", "hilos": [
        _h("esp32_fijo.USB", "pc.USB2", NEGRO, "USB")]},

    # ---------------- Carro ----------------
    {"id": "c_bat", "nombre": "Batería → interruptor → TB6612 y ESP32", "tipo": "carro", "hilos": [
        _h("bateria.B+", "interruptor.1", ROJO, "+7,4 V"),
        _h("interruptor.2", "tb6612.VM", ROJO, "+7,4 V motores"),
        _h("interruptor.2", "esp32_carro.JACK", ROJO, "+7,4 V al jack (regulador de la placa)"),
        _h("bateria.B-", "tb6612.GND_P", NEGRO, "GND potencia"),
        _h("bateria.B-", "esp32_carro.JACK", NEGRO, "GND al jack")]},
    {"id": "c_tb", "nombre": "ESP32 carro → TB6612", "tipo": "carro", "hilos": [
        _h("esp32_carro.G25.S", "tb6612.PWMA", AMARILLO, "PWM A"), _h("esp32_carro.G26.S", "tb6612.AIN1", VERDE, "AIN1"),
        _h("esp32_carro.G27.S", "tb6612.AIN2", AZUL, "AIN2"), _h("esp32_carro.G33.S", "tb6612.PWMB", AMARILLO, "PWM B"),
        _h("esp32_carro.G32.S", "tb6612.BIN1", VERDE, "BIN1"), _h("esp32_carro.G13.S", "tb6612.BIN2", AZUL, "BIN2"),
        _h("esp32_carro.G4.S", "tb6612.STBY", BLANCO, "STBY"), _h("esp32_carro.G4.V", "tb6612.VCC", ROJO, "3,3 V lógica"),
        _h("esp32_carro.G4.G", "tb6612.GND_L", NEGRO, "GND")]},
    {"id": "c_mot", "nombre": "TB6612 → motores (pares trenzados, 100 nF en bornes)", "tipo": "carro", "hilos": [
        _h("tb6612.AO1", "motor_izq.M+", ROJO, "motor A +"), _h("tb6612.AO2", "motor_izq.M-", NEGRO, "motor A −"),
        _h("tb6612.BO1", "motor_der.M+", ROJO, "motor B +"), _h("tb6612.BO2", "motor_der.M-", NEGRO, "motor B −")]},
    {"id": "c_enc", "nombre": "Encoders → ESP32 G18 / G19", "tipo": "carro", "hilos": [
        _h("enc_izq.D0", "esp32_carro.G18.S", VERDE, "pulsos izq."), _h("enc_izq.VCC", "esp32_carro.G18.V", ROJO, "3,3 V"),
        _h("enc_izq.GND", "esp32_carro.G18.G", NEGRO, "GND"),
        _h("enc_der.D0", "esp32_carro.G19.S", VERDE, "pulsos der."), _h("enc_der.VCC", "esp32_carro.G19.V", ROJO, "3,3 V"),
        _h("enc_der.GND", "esp32_carro.G19.G", NEGRO, "GND")]},
    {"id": "c_ir", "nombre": "5 infrarrojos de línea → ESP32", "tipo": "carro", "hilos": [
        _h("ir_linea.OUT1", "esp32_carro.G34.S", VERDE, "IR 1"), _h("ir_linea.OUT2", "esp32_carro.G35.S", VERDE, "IR 2"),
        _h("ir_linea.OUT3", "esp32_carro.G36.S", VERDE, "IR 3 (centro)"), _h("ir_linea.OUT4", "esp32_carro.G39.S", VERDE, "IR 4"),
        _h("ir_linea.OUT5", "esp32_carro.G16.S", VERDE, "IR 5"), _h("ir_linea.VCC", "esp32_carro.G34.V", ROJO, "3,3 V"),
        _h("ir_linea.GND", "esp32_carro.G34.G", NEGRO, "GND")]},
    {"id": "c_us", "nombre": "HC-SR04 → ESP32 (ECHO por divisor 1 kΩ / 2 kΩ)", "tipo": "carro", "hilos": [
        _h("hcsr04.VCC", "esp32_carro.5V.1", ROJO, "5 V"), _h("hcsr04.GND", "esp32_carro.GND.1", NEGRO, "GND"),
        _h("hcsr04.TRIG", "esp32_carro.G17.S", AMARILLO, "TRIG"),
        _h("hcsr04.ECHO", "esp32_carro.G23.S", AZUL, "ECHO (divisor en termorretráctil)")]},
    {"id": "c_tof", "nombre": "Láser VL53L0X → I2C del ESP32 carro", "tipo": "carro", "hilos": [
        _h("vl53_frontal.VIN", "esp32_carro.I2C.VCC", ROJO, "3,3 V"), _h("vl53_frontal.GND", "esp32_carro.I2C.GND", NEGRO, "GND"),
        _h("vl53_frontal.SCL", "esp32_carro.I2C.SCL", AMARILLO, "SCL (G22)"),
        _h("vl53_frontal.SDA", "esp32_carro.I2C.SDA", AZUL, "SDA (G21)")]},
    {"id": "c_cuna", "nombre": "Infrarrojo de la cuna → ESP32 G14", "tipo": "carro", "hilos": [
        _h("ir_cuna.DO", "esp32_carro.G14.S", VERDE, "vaso en la cuna"), _h("ir_cuna.VCC", "esp32_carro.G14.V", ROJO, "3,3 V"),
        _h("ir_cuna.GND", "esp32_carro.G14.G", NEGRO, "GND")]},
]

# Pines que pueden recibir mas de un hilo: bornes (hasta 2 hilos), empalmes (hasta 5), salidas
# de cables integrados y conectores (todos sus hilos van juntos).
TIPOS_MULTIPLES = {"borne", "borne_din", "cable", "jst", "pad", "jack", "empalme"}
MAX_HILOS_EMPALME = 5   # mas hilos no se sueldan bien dentro de un termoencogible de 6 mm


def pin(ref: str) -> dict:
    """`"dispositivo.pin"` -> definicion del pin (con su tipo)."""
    dev, nombre = ref.split(".", 1)
    tpl = PLANTILLAS[DISPOSITIVOS[dev]["plantilla"]]
    for p in tpl["pines"]:
        if p["n"] == nombre:
            return p
    raise KeyError(ref)


def gpio_usados(dispositivo: str) -> dict[str, str]:
    """GPIO del ESP32 `dispositivo` usados como senal (columna S o I2C) ->
    funcion."""
    uso = {}
    for c in CABLES:
        for h in c["hilos"]:
            for extremo in (h["de"], h["a"]):
                if not extremo.startswith(dispositivo + "."):
                    continue
                nombre = extremo.split(".", 1)[1]
                if nombre.endswith(".S"):
                    uso[nombre[:-2]] = h["funcion"]
                elif nombre == "I2C.SDA":
                    uso["G21"] = h["funcion"]
                elif nombre == "I2C.SCL":
                    uso["G22"] = h["funcion"]
    return uso


def datos_visor() -> dict:
    """Lo que necesita el visor 3D: plantillas, dispositivos y cables."""
    return {"plantillas": PLANTILLAS, "dispositivos": DISPOSITIVOS, "cables": CABLES}
