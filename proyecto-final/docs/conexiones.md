<!-- Generado por `python -m app.documentos`. No editar a mano. -->


# Conexiones (pin a pin)

Fuente única: `sim/conexiones.py`. De ahí salen los cables del visor 3D (botón **Cables**) y esta tabla; `tests/sim/test_conexiones.py` verifica que cada pin exista, que ningún pin de header reciba dos hilos, que los bornes lleven como mucho dos y que los GPIO sean los de la tabla de pines de [revision-final.md](revision-final.md).

Convenciones: placas GVS con el jumper en 3,3 V (**G** = GND, **V** = 3,3 V, **S** = señal del GPIO). Sin bornera (ahorro 2026-10-24): el +12 V (después del fusible principal), el +5 V y la tierra se reparten con **empalmes soldados con termoencogible** (pin `J`, hasta 5 hilos cada uno); la tierra sigue en estrella en los bornes −V de la fuente. Las pull-ups y los diodos de las entradas NPN y las pull-ups del bus I2C 1 van soldados en línea en sus empalmes.

## Caja de control

### Cable de poder → fuente (entra con una brida de alivio)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#6b3a1f">■</span> | Cable de poder (a la multitoma con interruptor) · **L** | Fuente 12 V 5 A · **L** | fase |
| <span style="color:#2d6fd0">■</span> | Cable de poder (a la multitoma con interruptor) · **N** | Fuente 12 V 5 A · **N** | neutro |
| <span style="color:#9bbf2a">■</span> | Cable de poder (a la multitoma con interruptor) · **PE** | Fuente 12 V 5 A · **PE** | tierra |

### Fuente → fusible principal y GND en estrella

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Fuente 12 V 5 A · **+V1** | Fusible principal 5 A (lento) en el +12 V · **IN** | +12 V |
| <span style="color:#1a1a1a">■</span> | Fuente 12 V 5 A · **-V1** | Empalme GND de potencia (a −V1) · **J** | GND (estrella) |
| <span style="color:#1a1a1a">■</span> | Fuente 12 V 5 A · **-V2** | Empalme GND de los sensores M18 (a −V2) · **J** | GND (estrella) |

### Fusible principal → empalmes de +12 V

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Fusible principal 5 A (lento) en el +12 V · **OUT** | Empalme +12 V (después del fusible) · **J** | +12 V |
| <span style="color:#d23a2a">■</span> | Empalme +12 V (después del fusible) · **J** | Empalme +12 V de los sensores M18 · **J** | +12 V sensores |

### +12 V → buck 6 V (XL4015)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Empalme +12 V (después del fusible) · **J** | Buck 6 V 5 A XL4015 (servos) · **IN+** | +12 V |
| <span style="color:#1a1a1a">■</span> | Buck 6 V 5 A XL4015 (servos) · **IN-** | Empalme GND de potencia (a −V1) · **J** | GND |

### Buck 6 V → PCA9685 (V+ de los servos)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Buck 6 V 5 A XL4015 (servos) · **OUT+** | PCA9685 (servos) · **T.V+** | +6 V (18 AWG) |
| <span style="color:#1a1a1a">■</span> | Buck 6 V 5 A XL4015 (servos) · **OUT-** | PCA9685 (servos) · **T.GND** | GND (18 AWG) |

### +12 V → buck 5 V → empalmes de 5 V

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Empalme +12 V (después del fusible) · **J** | Buck 5 V 3 A · **IN+** | +12 V |
| <span style="color:#1a1a1a">■</span> | Buck 5 V 3 A · **IN-** | Empalme GND de potencia (a −V1) · **J** | GND |
| <span style="color:#d23a2a">■</span> | Buck 5 V 3 A · **OUT+** | Empalme +5 V · **J** | +5 V |
| <span style="color:#1a1a1a">■</span> | Buck 5 V 3 A · **OUT-** | Empalme GND de 5 V · **J** | GND |

### +12 V → drivers (VMOT)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Empalme +12 V (después del fusible) · **J** | Drivers A4988 (monedas M, vasos V) · **VMOT** | +12 V |
| <span style="color:#1a1a1a">■</span> | Drivers A4988 (monedas M, vasos V) · **GNDP** | Empalme GND de potencia (a −V1) · **J** | GND |

### Empalmes de 5 V → ULN2003

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Empalme +5 V · **J** | ULN2003 (carrusel) · **+** | +5 V |
| <span style="color:#1a1a1a">■</span> | Empalme GND de 5 V · **J** | ULN2003 (carrusel) · **−** | GND |

### Empalmes de 5 V → ventilador 4010 (0,1 A)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Empalme +5 V · **J** | Ventilador 4010 5 V (saca el aire de los drivers) · **+5V** | +5 V ventilador |
| <span style="color:#1a1a1a">■</span> | Empalme GND de 5 V · **J** | Ventilador 4010 5 V (saca el aire de los drivers) · **GND** | GND ventilador |

### GND común ESP32 ↔ estrella

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **GND.1** | Empalme GND de potencia (a −V1) · **J** | GND común |

### ESP32 I2C 0 → PCA9685

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2d6fd0">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **I2C.SDA** | PCA9685 (servos) · **IN.SDA** | SDA (G21) |
| <span style="color:#e3c22b">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **I2C.SCL** | PCA9685 (servos) · **IN.SCL** | SCL (G22) |
| <span style="color:#d23a2a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **I2C.VCC** | PCA9685 (servos) · **IN.VCC** | 3,3 V lógica |
| <span style="color:#1a1a1a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **I2C.GND** | PCA9685 (servos) · **IN.GND** | GND |

### ESP32 → drivers (STEP, DIR, EN)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#e3c22b">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G25.S** | Drivers A4988 (monedas M, vasos V) · **M.STEP** | STEP monedas |
| <span style="color:#2da44e">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G26.S** | Drivers A4988 (monedas M, vasos V) · **M.DIR** | DIR monedas |
| <span style="color:#e3c22b">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G27.S** | Drivers A4988 (monedas M, vasos V) · **V.STEP** | STEP vasos |
| <span style="color:#2da44e">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G14.S** | Drivers A4988 (monedas M, vasos V) · **V.DIR** | DIR vasos |
| <span style="color:#e8e8e8">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G13.S** | Drivers A4988 (monedas M, vasos V) · **EN** | ENABLE común |
| <span style="color:#d23a2a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G13.V** | Drivers A4988 (monedas M, vasos V) · **VDD** | 3,3 V lógica |
| <span style="color:#1a1a1a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G13.G** | Drivers A4988 (monedas M, vasos V) · **GND** | GND lógica |

### ESP32 → ULN2003 (IN1-IN4)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2d6fd0">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G32.S** | ULN2003 (carrusel) · **IN1** | bobina 1 |
| <span style="color:#8957e5">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G33.S** | ULN2003 (carrusel) · **IN2** | bobina 2 |
| <span style="color:#8a939e">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G23.S** | ULN2003 (carrusel) · **IN3** | bobina 3 |
| <span style="color:#e8e8e8">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G4.S** | ULN2003 (carrusel) · **IN4** | bobina 4 |

### Capacitivo e inductivo → ESP32 (diodo + pull-up 10 kΩ en línea)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2da44e">■</span> | Señal del capacitivo (diodo + pull-up 10 kΩ) · **J** | ESP32 fijo (DevKit 38P) en placa GVS · **G35.S** | capacitivo (activo en bajo) |
| <span style="color:#d23a2a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G35.V** | Señal del capacitivo (diodo + pull-up 10 kΩ) · **J** | pull-up 10 kΩ a 3,3 V (en línea) |
| <span style="color:#e3c22b">■</span> | Señal del inductivo (diodo + pull-up 10 kΩ) · **J** | ESP32 fijo (DevKit 38P) en placa GVS · **G36.S** | inductivo (activo en bajo) |
| <span style="color:#d23a2a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G36.V** | Señal del inductivo (diodo + pull-up 10 kΩ) · **J** | pull-up 10 kΩ a 3,3 V (en línea) |

### ESP32 I2C 1 → empalmes del bus (pull-ups 2,2 kΩ en línea)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2d6fd0">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G16.S** | SDA del bus I2C 1 (pull-up 2,2 kΩ) · **J** | SDA (G16) |
| <span style="color:#e3c22b">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G17.S** | SCL del bus I2C 1 (pull-up 2,2 kΩ) · **J** | SCL (G17) |
| <span style="color:#d23a2a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G16.V** | 3,3 V del bus I2C 1 · **J** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G16.G** | GND del bus I2C 1 · **J** | GND |
| <span style="color:#d23a2a">■</span> | 3,3 V del bus I2C 1 · **J** | SDA del bus I2C 1 (pull-up 2,2 kΩ) · **J** | pull-up 2,2 kΩ de SDA (en línea) |
| <span style="color:#d23a2a">■</span> | 3,3 V del bus I2C 1 · **J** | SCL del bus I2C 1 (pull-up 2,2 kΩ) · **J** | pull-up 2,2 kΩ de SCL (en línea) |

### ESP32 fijo → portátil (USB derecho de atrás, datos y alimentación)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **USB** | Portátil · **USB2** | USB |

## Planta (campo)

### FC-51 presencia → ESP32 G34 · conector Dupont 3 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2da44e">■</span> | FC-51 presencia (1) · **OUT** | ESP32 fijo (DevKit 38P) en placa GVS · **G34.S** | señal |
| <span style="color:#1a1a1a">■</span> | FC-51 presencia (1) · **GND** | ESP32 fijo (DevKit 38P) en placa GVS · **G34.G** | GND |
| <span style="color:#d23a2a">■</span> | FC-51 presencia (1) · **VCC** | ESP32 fijo (DevKit 38P) en placa GVS · **G34.V** | 3,3 V |

### Capacitivo → su diodo (G35) y empalmes de 12 V

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | Capacitivo LJC18A3 (2) · **NEGRO** | Señal del capacitivo (diodo + pull-up 10 kΩ) · **J** | salida NPN (por el diodo BAT85) |
| <span style="color:#6b3a1f">■</span> | Capacitivo LJC18A3 (2) · **CAFE** | Empalme +12 V de los sensores M18 · **J** | +12 V |
| <span style="color:#2d6fd0">■</span> | Capacitivo LJC18A3 (2) · **AZUL** | Empalme GND de los sensores M18 (a −V2) · **J** | 0 V |

### Inductivo → su diodo (G36) y empalmes de 12 V

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | Inductivo LJ18A3-8 (3) · **NEGRO** | Señal del inductivo (diodo + pull-up 10 kΩ) · **J** | salida NPN (por el diodo BAT85) |
| <span style="color:#6b3a1f">■</span> | Inductivo LJ18A3-8 (3) · **CAFE** | Empalme +12 V de los sensores M18 · **J** | +12 V |
| <span style="color:#2d6fd0">■</span> | Inductivo LJ18A3-8 (3) · **AZUL** | Empalme GND de los sensores M18 (a −V2) · **J** | 0 V |

### Hall KY-003 → ESP32 G39 · conector Dupont 3 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2da44e">■</span> | Hall KY-003 (6) · **S** | ESP32 fijo (DevKit 38P) en placa GVS · **G39.S** | señal (pull-up del módulo) |
| <span style="color:#d23a2a">■</span> | Hall KY-003 (6) · **+** | ESP32 fijo (DevKit 38P) en placa GVS · **G39.V** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | Hall KY-003 (6) · **−** | ESP32 fijo (DevKit 38P) en placa GVS · **G39.G** | GND |

### VL53L0X interior → empalmes del bus I2C 1 y XSHUT G18

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | VL53L0X interior (5) · **VIN** | 3,3 V del bus I2C 1 · **J** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | VL53L0X interior (5) · **GND** | GND del bus I2C 1 · **J** | GND |
| <span style="color:#e3c22b">■</span> | VL53L0X interior (5) · **SCL** | SCL del bus I2C 1 (pull-up 2,2 kΩ) · **J** | SCL |
| <span style="color:#2d6fd0">■</span> | VL53L0X interior (5) · **SDA** | SDA del bus I2C 1 (pull-up 2,2 kΩ) · **J** | SDA |
| <span style="color:#e8e8e8">■</span> | VL53L0X interior (5) · **XSHUT** | ESP32 fijo (DevKit 38P) en placa GVS · **G18.S** | XSHUT (dirección 0x30) |

### VL53L0X cortina → empalmes del bus I2C 1 y XSHUT G19

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | VL53L0X cortina (8) · **VIN** | 3,3 V del bus I2C 1 · **J** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | VL53L0X cortina (8) · **GND** | GND del bus I2C 1 · **J** | GND |
| <span style="color:#e3c22b">■</span> | VL53L0X cortina (8) · **SCL** | SCL del bus I2C 1 (pull-up 2,2 kΩ) · **J** | SCL |
| <span style="color:#2d6fd0">■</span> | VL53L0X cortina (8) · **SDA** | SDA del bus I2C 1 (pull-up 2,2 kΩ) · **J** | SDA |
| <span style="color:#e8e8e8">■</span> | VL53L0X cortina (8) · **XSHUT** | ESP32 fijo (DevKit 38P) en placa GVS · **G19.S** | XSHUT (dirección 0x31) |

### NEMA17 cinta de monedas → driver M · conector JST-PH 6 → bornes

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | NEMA17 cinta de monedas · **JST** | Drivers A4988 (monedas M, vasos V) · **M.1A** | A+ |
| <span style="color:#2da44e">■</span> | NEMA17 cinta de monedas · **JST** | Drivers A4988 (monedas M, vasos V) · **M.1B** | A− |
| <span style="color:#d23a2a">■</span> | NEMA17 cinta de monedas · **JST** | Drivers A4988 (monedas M, vasos V) · **M.2A** | B+ |
| <span style="color:#2d6fd0">■</span> | NEMA17 cinta de monedas · **JST** | Drivers A4988 (monedas M, vasos V) · **M.2B** | B− |

### NEMA17 cinta de vasos → driver V · conector JST-PH 6 → bornes

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | NEMA17 cinta de vasos · **JST** | Drivers A4988 (monedas M, vasos V) · **V.1A** | A+ |
| <span style="color:#2da44e">■</span> | NEMA17 cinta de vasos · **JST** | Drivers A4988 (monedas M, vasos V) · **V.1B** | A− |
| <span style="color:#d23a2a">■</span> | NEMA17 cinta de vasos · **JST** | Drivers A4988 (monedas M, vasos V) · **V.2A** | B+ |
| <span style="color:#2d6fd0">■</span> | NEMA17 cinta de vasos · **JST** | Drivers A4988 (monedas M, vasos V) · **V.2B** | B− |

### 28BYJ-48 → ULN2003 (JST-XH 5) · conector JST-XH 5 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2d6fd0">■</span> | 28BYJ-48 carrusel · **CABLE** | ULN2003 (carrusel) · **MOTOR** | bobina 1 |
| <span style="color:#e07aa8">■</span> | 28BYJ-48 carrusel · **CABLE** | ULN2003 (carrusel) · **MOTOR** | bobina 2 |
| <span style="color:#e3c22b">■</span> | 28BYJ-48 carrusel · **CABLE** | ULN2003 (carrusel) · **MOTOR** | bobina 3 |
| <span style="color:#e8901c">■</span> | 28BYJ-48 carrusel · **CABLE** | ULN2003 (carrusel) · **MOTOR** | bobina 4 |
| <span style="color:#d23a2a">■</span> | 28BYJ-48 carrusel · **CABLE** | ULN2003 (carrusel) · **MOTOR** | +5 V común |

### Servo desvío → PCA9685 canal 0 · conector JR 3 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#e8901c">■</span> | Servo desvío (SG90) · **CABLE** | PCA9685 (servos) · **PWM0** | señal PWM |
| <span style="color:#d23a2a">■</span> | Servo desvío (SG90) · **CABLE** | PCA9685 (servos) · **V+0** | 6 V |
| <span style="color:#6b3a1f">■</span> | Servo desvío (SG90) · **CABLE** | PCA9685 (servos) · **GND0** | GND |

### Servo obturador → PCA9685 canal 1 · conector JR 3 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#e8901c">■</span> | Servo obturador (SG90) · **CABLE** | PCA9685 (servos) · **PWM1** | señal PWM |
| <span style="color:#d23a2a">■</span> | Servo obturador (SG90) · **CABLE** | PCA9685 (servos) · **V+1** | 6 V |
| <span style="color:#6b3a1f">■</span> | Servo obturador (SG90) · **CABLE** | PCA9685 (servos) · **GND1** | GND |

### Servo escape de tapas → PCA9685 canal 2 · conector JR 3 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#e8901c">■</span> | Servo escape de tapas (SG90) · **CABLE** | PCA9685 (servos) · **PWM2** | señal PWM |
| <span style="color:#d23a2a">■</span> | Servo escape de tapas (SG90) · **CABLE** | PCA9685 (servos) · **V+2** | 6 V |
| <span style="color:#6b3a1f">■</span> | Servo escape de tapas (SG90) · **CABLE** | PCA9685 (servos) · **GND2** | GND |

### Servo prensa (MG996R) → PCA9685 canal 3 · conector JR 3 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#e8901c">■</span> | Servo prensa (MG996R) · **CABLE** | PCA9685 (servos) · **PWM3** | señal PWM |
| <span style="color:#d23a2a">■</span> | Servo prensa (MG996R) · **CABLE** | PCA9685 (servos) · **V+3** | 6 V |
| <span style="color:#6b3a1f">■</span> | Servo prensa (MG996R) · **CABLE** | PCA9685 (servos) · **GND3** | GND |

### Servo empujador (MG996R) → PCA9685 canal 4 · conector JR 3 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#e8901c">■</span> | Servo empujador (MG996R) · **CABLE** | PCA9685 (servos) · **PWM4** | señal PWM |
| <span style="color:#d23a2a">■</span> | Servo empujador (MG996R) · **CABLE** | PCA9685 (servos) · **V+4** | 6 V |
| <span style="color:#6b3a1f">■</span> | Servo empujador (MG996R) · **CABLE** | PCA9685 (servos) · **GND4** | GND |

### Servo escape canaleta → PCA9685 canal 5 · conector JR 3 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#e8901c">■</span> | Servo escape canaleta (SG90) · **CABLE** | PCA9685 (servos) · **PWM5** | señal PWM |
| <span style="color:#d23a2a">■</span> | Servo escape canaleta (SG90) · **CABLE** | PCA9685 (servos) · **V+5** | 6 V |
| <span style="color:#6b3a1f">■</span> | Servo escape canaleta (SG90) · **CABLE** | PCA9685 (servos) · **GND5** | GND |

### Panel de luz → empalmes de 5 V

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Panel de luz 5 V · **+5V** | Empalme +5 V · **J** | +5 V |
| <span style="color:#1a1a1a">■</span> | Panel de luz 5 V · **GND** | Empalme GND de 5 V · **J** | GND |

### Anillo de luz → empalmes de 5 V

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Anillo de luz 5 V · **+5V** | Empalme +5 V · **J** | +5 V |
| <span style="color:#1a1a1a">■</span> | Anillo de luz 5 V · **GND** | Empalme GND de 5 V · **J** | GND |

### Webcam cenital → portátil (USB derecho de adelante)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | Webcam cenital (4) · **USB** | Portátil · **USB1** | USB |

### Webcam de vasos → portátil (USB izquierdo, con la extensión USB de 1 m)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | Webcam de vasos (7) · **USB** | Portátil · **USB3** | USB |

## Carro

### Batería → interruptor → TB6612 y ESP32

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | 2 × 18650 (7,4 V) con BMS · **B+** | Interruptor + fusible 3 A · **1** | +7,4 V |
| <span style="color:#d23a2a">■</span> | Interruptor + fusible 3 A · **2** | Puente H TB6612FNG · **VM** | +7,4 V motores |
| <span style="color:#d23a2a">■</span> | Interruptor + fusible 3 A · **2** | ESP32 carro (DevKit 30P) en placa GVS · **JACK** | +7,4 V al jack (regulador de la placa) |
| <span style="color:#1a1a1a">■</span> | 2 × 18650 (7,4 V) con BMS · **B-** | Puente H TB6612FNG · **GND_P** | GND potencia |
| <span style="color:#1a1a1a">■</span> | 2 × 18650 (7,4 V) con BMS · **B-** | ESP32 carro (DevKit 30P) en placa GVS · **JACK** | GND al jack |

### ESP32 carro → TB6612

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#e3c22b">■</span> | ESP32 carro (DevKit 30P) en placa GVS · **G25.S** | Puente H TB6612FNG · **PWMA** | PWM A |
| <span style="color:#2da44e">■</span> | ESP32 carro (DevKit 30P) en placa GVS · **G26.S** | Puente H TB6612FNG · **AIN1** | AIN1 |
| <span style="color:#2d6fd0">■</span> | ESP32 carro (DevKit 30P) en placa GVS · **G27.S** | Puente H TB6612FNG · **AIN2** | AIN2 |
| <span style="color:#e3c22b">■</span> | ESP32 carro (DevKit 30P) en placa GVS · **G33.S** | Puente H TB6612FNG · **PWMB** | PWM B |
| <span style="color:#2da44e">■</span> | ESP32 carro (DevKit 30P) en placa GVS · **G32.S** | Puente H TB6612FNG · **BIN1** | BIN1 |
| <span style="color:#2d6fd0">■</span> | ESP32 carro (DevKit 30P) en placa GVS · **G13.S** | Puente H TB6612FNG · **BIN2** | BIN2 |
| <span style="color:#e8e8e8">■</span> | ESP32 carro (DevKit 30P) en placa GVS · **G4.S** | Puente H TB6612FNG · **STBY** | STBY |
| <span style="color:#d23a2a">■</span> | ESP32 carro (DevKit 30P) en placa GVS · **G4.V** | Puente H TB6612FNG · **VCC** | 3,3 V lógica |
| <span style="color:#1a1a1a">■</span> | ESP32 carro (DevKit 30P) en placa GVS · **G4.G** | Puente H TB6612FNG · **GND_L** | GND |

### TB6612 → motores (pares trenzados, 100 nF en bornes)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Puente H TB6612FNG · **AO1** | Motor TT izquierdo · **M+** | motor A + |
| <span style="color:#1a1a1a">■</span> | Puente H TB6612FNG · **AO2** | Motor TT izquierdo · **M-** | motor A − |
| <span style="color:#d23a2a">■</span> | Puente H TB6612FNG · **BO1** | Motor TT derecho · **M+** | motor B + |
| <span style="color:#1a1a1a">■</span> | Puente H TB6612FNG · **BO2** | Motor TT derecho · **M-** | motor B − |

### Encoders → ESP32 G18 / G19

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2da44e">■</span> | Encoder izquierdo H206 (11) · **D0** | ESP32 carro (DevKit 30P) en placa GVS · **G18.S** | pulsos izq. |
| <span style="color:#d23a2a">■</span> | Encoder izquierdo H206 (11) · **VCC** | ESP32 carro (DevKit 30P) en placa GVS · **G18.V** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | Encoder izquierdo H206 (11) · **GND** | ESP32 carro (DevKit 30P) en placa GVS · **G18.G** | GND |
| <span style="color:#2da44e">■</span> | Encoder derecho H206 (11) · **D0** | ESP32 carro (DevKit 30P) en placa GVS · **G19.S** | pulsos der. |
| <span style="color:#d23a2a">■</span> | Encoder derecho H206 (11) · **VCC** | ESP32 carro (DevKit 30P) en placa GVS · **G19.V** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | Encoder derecho H206 (11) · **GND** | ESP32 carro (DevKit 30P) en placa GVS · **G19.G** | GND |

### 5 infrarrojos de línea → ESP32

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2da44e">■</span> | 5 infrarrojos de línea TCRT5000 (9) · **OUT1** | ESP32 carro (DevKit 30P) en placa GVS · **G34.S** | IR 1 |
| <span style="color:#2da44e">■</span> | 5 infrarrojos de línea TCRT5000 (9) · **OUT2** | ESP32 carro (DevKit 30P) en placa GVS · **G35.S** | IR 2 |
| <span style="color:#2da44e">■</span> | 5 infrarrojos de línea TCRT5000 (9) · **OUT3** | ESP32 carro (DevKit 30P) en placa GVS · **G36.S** | IR 3 (centro) |
| <span style="color:#2da44e">■</span> | 5 infrarrojos de línea TCRT5000 (9) · **OUT4** | ESP32 carro (DevKit 30P) en placa GVS · **G39.S** | IR 4 |
| <span style="color:#2da44e">■</span> | 5 infrarrojos de línea TCRT5000 (9) · **OUT5** | ESP32 carro (DevKit 30P) en placa GVS · **G16.S** | IR 5 |
| <span style="color:#d23a2a">■</span> | 5 infrarrojos de línea TCRT5000 (9) · **VCC** | ESP32 carro (DevKit 30P) en placa GVS · **G34.V** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | 5 infrarrojos de línea TCRT5000 (9) · **GND** | ESP32 carro (DevKit 30P) en placa GVS · **G34.G** | GND |

### HC-SR04 → ESP32 (ECHO por divisor 1 kΩ / 2 kΩ)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Ultrasónico HC-SR04 (10) · **VCC** | ESP32 carro (DevKit 30P) en placa GVS · **5V.1** | 5 V |
| <span style="color:#1a1a1a">■</span> | Ultrasónico HC-SR04 (10) · **GND** | ESP32 carro (DevKit 30P) en placa GVS · **GND.1** | GND |
| <span style="color:#e3c22b">■</span> | Ultrasónico HC-SR04 (10) · **TRIG** | ESP32 carro (DevKit 30P) en placa GVS · **G17.S** | TRIG |
| <span style="color:#2d6fd0">■</span> | Ultrasónico HC-SR04 (10) · **ECHO** | ESP32 carro (DevKit 30P) en placa GVS · **G23.S** | ECHO (divisor en termorretráctil) |

### Láser VL53L0X → I2C del ESP32 carro

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Láser VL53L0X (13) · **VIN** | ESP32 carro (DevKit 30P) en placa GVS · **I2C.VCC** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | Láser VL53L0X (13) · **GND** | ESP32 carro (DevKit 30P) en placa GVS · **I2C.GND** | GND |
| <span style="color:#e3c22b">■</span> | Láser VL53L0X (13) · **SCL** | ESP32 carro (DevKit 30P) en placa GVS · **I2C.SCL** | SCL (G22) |
| <span style="color:#2d6fd0">■</span> | Láser VL53L0X (13) · **SDA** | ESP32 carro (DevKit 30P) en placa GVS · **I2C.SDA** | SDA (G21) |

### Infrarrojo de la cuna → ESP32 G14

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2da44e">■</span> | Infrarrojo de la cuna TCRT5000 (12) · **DO** | ESP32 carro (DevKit 30P) en placa GVS · **G14.S** | vaso en la cuna |
| <span style="color:#d23a2a">■</span> | Infrarrojo de la cuna TCRT5000 (12) · **VCC** | ESP32 carro (DevKit 30P) en placa GVS · **G14.V** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | Infrarrojo de la cuna TCRT5000 (12) · **GND** | ESP32 carro (DevKit 30P) en placa GVS · **G14.G** | GND |

