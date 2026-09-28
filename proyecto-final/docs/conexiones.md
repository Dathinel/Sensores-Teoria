<!-- Generado por `python -m app.documentos`. No editar a mano. -->


# Conexiones (pin a pin)

Fuente única: `sim/conexiones.py`. De ahí salen los cables del visor 3D (botón **Cables**) y esta tabla; `tests/sim/test_conexiones.py` verifica que cada pin exista, que ningún pin de header reciba dos hilos, que los bornes lleven como mucho dos y que los GPIO sean los de la tabla de pines de [revision-final.md](revision-final.md).

Convenciones: placas GVS con el jumper en 3,3 V (**G** = GND, **V** = 3,3 V, **S** = señal del GPIO). Bornera X2 con puentes 2-3 (+12 V sensores), 5-6 (+5 V) y 7 a 13 (GND en estrella).

## Caja de control

### Entrada IEC → fuente

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#6b3a1f">■</span> | Entrada de red con interruptor · **L** | Fuente 12 V 10 A · **L** | fase |
| <span style="color:#2d6fd0">■</span> | Entrada de red con interruptor · **N** | Fuente 12 V 10 A · **N** | neutro |
| <span style="color:#9bbf2a">■</span> | Entrada de red con interruptor · **PE** | Fuente 12 V 10 A · **PE** | tierra |

### Fuente → fusibles y GND

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Fuente 12 V 10 A · **+V1** | Fusibles F1 5 A · F2 2 A · F3 3 A · F4 1 A · **IN** | +12 V |
| <span style="color:#1a1a1a">■</span> | Fuente 12 V 10 A · **-V1** | Bornera X2 · **7** | GND (estrella) |
| <span style="color:#1a1a1a">■</span> | Fuente 12 V 10 A · **-V2** | Bornera X2 · **8** | GND (estrella) |

### F1 5 A → buck 6 V → bornera

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Fusibles F1 5 A · F2 2 A · F3 3 A · F4 1 A · **F1** | Buck 6 V 8 A (servos) · **IN+** | +12 V |
| <span style="color:#1a1a1a">■</span> | Buck 6 V 8 A (servos) · **IN-** | Bornera X2 · **7** | GND |
| <span style="color:#d23a2a">■</span> | Buck 6 V 8 A (servos) · **OUT+** | Bornera X2 · **4** | +6 V servos |
| <span style="color:#1a1a1a">■</span> | Buck 6 V 8 A (servos) · **OUT-** | Bornera X2 · **9** | GND |

### F2 2 A → buck 5 V → bornera

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Fusibles F1 5 A · F2 2 A · F3 3 A · F4 1 A · **F2** | Buck 5 V 3 A · **IN+** | +12 V |
| <span style="color:#1a1a1a">■</span> | Buck 5 V 3 A · **IN-** | Bornera X2 · **8** | GND |
| <span style="color:#d23a2a">■</span> | Buck 5 V 3 A · **OUT+** | Bornera X2 · **5** | +5 V |
| <span style="color:#1a1a1a">■</span> | Buck 5 V 3 A · **OUT-** | Bornera X2 · **10** | GND |

### F3 3 A (drivers) y F4 1 A (sensores 12 V)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Fusibles F1 5 A · F2 2 A · F3 3 A · F4 1 A · **F3** | Bornera X2 · **1** | +12 V drivers |
| <span style="color:#d23a2a">■</span> | Fusibles F1 5 A · F2 2 A · F3 3 A · F4 1 A · **F4** | Bornera X2 · **2** | +12 V sensores |

### Bornera → PCA9685 (V+ de los servos)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Bornera X2 · **4** | PCA9685 (servos) · **T.V+** | +6 V (18 AWG) |
| <span style="color:#1a1a1a">■</span> | Bornera X2 · **9** | PCA9685 (servos) · **T.GND** | GND (18 AWG) |

### Bornera → drivers (VMOT)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Bornera X2 · **1** | Drivers A4988 (monedas M, vasos V) · **VMOT** | +12 V |
| <span style="color:#1a1a1a">■</span> | Bornera X2 · **11** | Drivers A4988 (monedas M, vasos V) · **GNDP** | GND |

### Bornera → ULN2003

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Bornera X2 · **5** | ULN2003 (carrusel) · **+** | +5 V |
| <span style="color:#1a1a1a">■</span> | Bornera X2 · **10** | ULN2003 (carrusel) · **−** | GND |

### Bornera → optoacopladores (+12)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Bornera X2 · **2** | Optoacopladores PC817 · **+12** | +12 V |

### Buck 5 V → ventilador 4010 (0,1 A)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Buck 5 V 3 A · **OUT+** | Ventilador 4010 5 V (saca el aire de los drivers) · **+5V** | +5 V ventilador |
| <span style="color:#1a1a1a">■</span> | Buck 5 V 3 A · **OUT-** | Ventilador 4010 5 V (saca el aire de los drivers) · **GND** | GND ventilador |

### GND común ESP32 ↔ bornera

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **GND.1** | Bornera X2 · **11** | GND común |

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

### Optoacopladores → ESP32

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | Optoacopladores PC817 · **GND** | ESP32 fijo (DevKit 38P) en placa GVS · **G35.G** | GND |
| <span style="color:#d23a2a">■</span> | Optoacopladores PC817 · **3V3** | ESP32 fijo (DevKit 38P) en placa GVS · **G35.V** | 3,3 V pull-up |
| <span style="color:#2da44e">■</span> | Optoacopladores PC817 · **OUT1** | ESP32 fijo (DevKit 38P) en placa GVS · **G35.S** | capacitivo |
| <span style="color:#e3c22b">■</span> | Optoacopladores PC817 · **OUT2** | ESP32 fijo (DevKit 38P) en placa GVS · **G36.S** | inductivo |

### ESP32 I2C 1 → reparto I2C

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2d6fd0">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G16.S** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **SDA** | SDA (G16) |
| <span style="color:#e3c22b">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G17.S** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **SCL** | SCL (G17) |
| <span style="color:#d23a2a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G16.V** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **3V3** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **G16.G** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **GND** | GND |

### ESP32 fijo → hub USB P3 (datos y alimentación)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | ESP32 fijo (DevKit 38P) en placa GVS · **USB** | Hub USB con fuente · **P3** | USB |

### Hub USB → portátil

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | Hub USB con fuente · **UP** | Portátil · **USB1** | USB |

## Planta (campo)

### FC-51 presencia → ESP32 G34 · conector Dupont 3 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2da44e">■</span> | FC-51 presencia (1) · **OUT** | ESP32 fijo (DevKit 38P) en placa GVS · **G34.S** | señal |
| <span style="color:#1a1a1a">■</span> | FC-51 presencia (1) · **GND** | ESP32 fijo (DevKit 38P) en placa GVS · **G34.G** | GND |
| <span style="color:#d23a2a">■</span> | FC-51 presencia (1) · **VCC** | ESP32 fijo (DevKit 38P) en placa GVS · **G34.V** | 3,3 V |

### Capacitivo → optoacoplador IN1

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | Capacitivo LJC18A3 (2) · **NEGRO** | Optoacopladores PC817 · **IN1** | salida NPN |
| <span style="color:#6b3a1f">■</span> | Capacitivo LJC18A3 (2) · **CAFE** | Bornera X2 · **3** | +12 V |
| <span style="color:#2d6fd0">■</span> | Capacitivo LJC18A3 (2) · **AZUL** | Bornera X2 · **12** | 0 V |

### Inductivo → optoacoplador IN2

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | Inductivo LJ18A3-8 (3) · **NEGRO** | Optoacopladores PC817 · **IN2** | salida NPN |
| <span style="color:#6b3a1f">■</span> | Inductivo LJ18A3-8 (3) · **CAFE** | Bornera X2 · **3** | +12 V |
| <span style="color:#2d6fd0">■</span> | Inductivo LJ18A3-8 (3) · **AZUL** | Bornera X2 · **12** | 0 V |

### Hall KY-003 → ESP32 G39 · conector Dupont 3 vías

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#2da44e">■</span> | Hall KY-003 (6) · **S** | ESP32 fijo (DevKit 38P) en placa GVS · **G39.S** | señal (pull-up del módulo) |
| <span style="color:#d23a2a">■</span> | Hall KY-003 (6) · **+** | ESP32 fijo (DevKit 38P) en placa GVS · **G39.V** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | Hall KY-003 (6) · **−** | ESP32 fijo (DevKit 38P) en placa GVS · **G39.G** | GND |

### VL53L0X interior → reparto I2C (A) y XSHUT G18

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | VL53L0X interior (5) · **VIN** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **A.3V3** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | VL53L0X interior (5) · **GND** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **A.GND** | GND |
| <span style="color:#e3c22b">■</span> | VL53L0X interior (5) · **SCL** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **A.SCL** | SCL |
| <span style="color:#2d6fd0">■</span> | VL53L0X interior (5) · **SDA** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **A.SDA** | SDA |
| <span style="color:#e8e8e8">■</span> | VL53L0X interior (5) · **XSHUT** | ESP32 fijo (DevKit 38P) en placa GVS · **G18.S** | XSHUT (dirección 0x30) |

### VL53L0X cortina → reparto I2C (B) y XSHUT G19

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | VL53L0X cortina (8) · **VIN** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **B.3V3** | 3,3 V |
| <span style="color:#1a1a1a">■</span> | VL53L0X cortina (8) · **GND** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **B.GND** | GND |
| <span style="color:#e3c22b">■</span> | VL53L0X cortina (8) · **SCL** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **B.SCL** | SCL |
| <span style="color:#2d6fd0">■</span> | VL53L0X cortina (8) · **SDA** | Reparto I2C 1 (pull-ups 2,2 kΩ) · **B.SDA** | SDA |
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

### Panel de luz → bornera 5 V

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Panel de luz 5 V · **+5V** | Bornera X2 · **6** | +5 V |
| <span style="color:#1a1a1a">■</span> | Panel de luz 5 V · **GND** | Bornera X2 · **13** | GND |

### Anillo de luz → bornera 5 V

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#d23a2a">■</span> | Anillo de luz 5 V · **+5V** | Bornera X2 · **6** | +5 V |
| <span style="color:#1a1a1a">■</span> | Anillo de luz 5 V · **GND** | Bornera X2 · **13** | GND |

### Webcam cenital → hub USB P2

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | Webcam cenital (4) · **USB** | Hub USB con fuente · **P2** | USB |

### Webcam de vasos → hub USB P1 (con extensión USB de 1 m)

| Hilo | De | A | Función |
|---|---|---|---|
| <span style="color:#1a1a1a">■</span> | Webcam de vasos (7) · **USB** | Hub USB con fuente · **P1** | USB |

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

