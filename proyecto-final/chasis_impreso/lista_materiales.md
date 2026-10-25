# Lista de materiales del carro

> Generado por `python materiales.py` (no editar a mano): sale de piezas.json, config/precios.yaml, docs/electrica.md y la tabla de compras del README.

## Piezas impresas (PLA)

| Pieza | Tanda | Cant. | g c/u | min c/u | g total | Tiempo total |
|---|---|---|---|---|---|---|
| chasis | 1 | 1 | 83.4 | 120 | 83.4 | 2 h 00 min |
| barra_tcrt5000 | 1 | 1 | 5.3 | 9 | 5.3 | 0 h 09 min |
| porta_baterias | 1 | 1 | 14.2 | 23 | 14.2 | 0 h 23 min |
| pared_cuna_izq | 2 | 1 | 26.0 | 38 | 26.0 | 0 h 38 min |
| pared_cuna_der | 2 | 1 | 25.8 | 38 | 25.8 | 0 h 38 min |
| mampara | 2 | 1 | 18.7 | 28 | 18.7 | 0 h 28 min |
| zapata_guia | 2 | 4 | 0.9 | 2 | 3.6 | 0 h 08 min |
| lengueta | 2 | 1 | 0.8 | 2 | 0.8 | 0 h 02 min |
| soporte_motor_izq | 3 | 1 | 9.0 | 18 | 9.0 | 0 h 18 min |
| soporte_motor_der | 3 | 1 | 9.0 | 18 | 9.0 | 0 h 18 min |
| soporte_encoder_izq | 3 | 1 | 4.6 | 13 | 4.6 | 0 h 13 min |
| soporte_encoder_der | 3 | 1 | 4.6 | 13 | 4.6 | 0 h 13 min |
| torre_rueda_loca | 3 | 1 | 10.0 | 20 | 10.0 | 0 h 20 min |
| soporte_rodillo_izq | 3 | 1 | 6.6 | 15 | 6.6 | 0 h 15 min |
| soporte_rodillo_der | 3 | 1 | 6.6 | 15 | 6.6 | 0 h 15 min |
| piso2_esp32 | 4 | 1 | 21.7 | 32 | 21.7 | 0 h 32 min |
| soporte_tb6612 | 4 | 1 | 4.7 | 11 | 4.7 | 0 h 11 min |
| caja_interruptor | 4 | 1 | 3.2 | 8 | 3.2 | 0 h 08 min |
| caja_fusible | 4 | 1 | 3.2 | 8 | 3.2 | 0 h 08 min |
| escuadra_frontal | 4 | 1 | 7.7 | 21 | 7.7 | 0 h 21 min |
| pasador_tt | 5 | 4 | 0.2 | 1 | 0.8 | 0 h 04 min |
| remache_6 | 5 | 1 | 0.1 | 1 | 0.1 | 0 h 01 min |
| remache_9_5 | 5 | 4 | 0.2 | 1 | 0.8 | 0 h 04 min |
| remache_10_5 | 5 | 8 | 0.2 | 1 | 1.6 | 0 h 08 min |
| remache_11 | 5 | 8 | 0.2 | 1 | 1.6 | 0 h 08 min |
| remache_14 | 5 | 2 | 0.2 | 1 | 0.4 | 0 h 02 min |
| remache_37 | 5 | 4 | 0.5 | 2 | 2.0 | 0 h 08 min |
| Total |  | 54 |  |  | 276 | 8 h 13 min |

Estimado de exportar.py (±30 % en el tiempo; Creality Print da el real al laminar). PLA: 276 g ≈ $25.916 a $93.900/kg. Sin la pieza de prueba (tanda 0) ni los remaches de repuesto.

## Electrónica

| Componente | Cant. | Precio c/u | Subtotal | Tienda |
|---|---|---|---|---|
| ESP32 DevKit 30 pines CH340 | 1 | $34.900 | $34.900 | Electronilab |
| Motorreductor TT amarillo 1:48 con llanta | 2 | $12.000 | $24.000 | Ferretrónica |
| Sensor de herradura F249 (6 000) + disco de 20 ranuras (1 500) | 2 | $7.500 | $15.000 | Ferretrónica |
| Módulo de seguimiento TCRT5000 de 5 canales | 1 | $15.900 | $15.900 | Electronilab |
| HC-SR04 | 1 | $7.500 | $7.500 | Ferretrónica |
| Sensor de distancia VL53L0X | 1 | $25.000 | $25.000 | Ferretrónica |
| Módulo TCRT5000 | 1 | $6.000 | $6.000 | Ferretrónica |
| Módulo puente H TB6612FNG | 1 | $15.000 | $15.000 | Ferretrónica |
| Par de 18650 2500 mAh (60 000) + portapilas 2S (3 500) + BMS 2S (8 000) | 1 | $71.500 | $71.500 | Ferretrónica |
| Interruptor de palanca + portafusible aéreo con fusible 3 A | 1 | $4.000 | $4.000 | estimado |
| Placa de expansión GVS para ESP32 DevKit 30 pines | 1 | sin precio | — | verificar |
| Total electrónica |  |  | $218.800 |  |

Precios de config/precios.yaml (consultados el 2026-09-27, COP, sin envío): verificarlos antes de comprar.

## Cables y componentes sueltos

| Calibre / ítem | Hilos | m (modelo) | m a comprar | Para qué |
|---|---|---|---|---|
| 22 AWG | 9 | 1.35 | 1.8 | batería, interruptor, TB6612 y motores (rojo/negro) |
| 26 AWG | 33 | 4.95 | 6.4 | señales y alimentación de sensores: Dupont hembra-hembra de 20 cm |
| Condensador cerámico 100 nF | 2 |  |  | en los bornes de cada motor TT |
| Plug DC 5,5 × 2,1 mm con cable | 1 |  |  | jack de la GVS: +7,4 V del interruptor y GND de la batería |
| Resistencias 1 kΩ y 2 kΩ | 1 + 1 |  |  | divisor del ECHO del HC-SR04 (en termoencogible) |
| Termoencogible 2-4 mm | ~50 cm |  |  | empalmes y el divisor |

Hilos y largos de docs/electrica.md (cada hilo del carro mide 0,15 m en el modelo); se compra un 30 % de más.

## Ferretería y consumibles

| Ítem | Cant. | Dónde |
|---|---|---|
| Tornillo M3 × 20 + tuerca M3 | 2 | ejes de los rodillos guía |
| Tornillo M3 × 10 + tuerca M3 | 2 | rueda loca de bola (0 si loca_tipo = "deslizador") |
| Arandela M3 | 6 | entre los rodamientos y el brazo de los rodillos |
| Rodamiento 623ZZ (3 × 10 × 4) | 4 | rodillos guía (2 por lado) |
| Rueda loca de bola con brida de 2 agujeros | 1 | o el deslizador impreso |
| Bridas de 2,5 mm | ~15 | cables, TB6612, H206 y TCRT5000 de la cuna |
| Cinta PTFE de 10 a 12 mm | ~40 cm | rieles y zapatas (también sirve para el deslizador) |
| Espuma de 10 mm | 2 trozos | en la mampara (arriba y a media altura) |
| Correa de velcro de 20 mm | 1 | pack 2S |
| Elástico pequeño | 1 | lengüeta |
| Pegante instantáneo | 1 | por si un perno a presión queda flojo |
| Pasacables de goma de 8 mm (opcional) | 4 | agujeros de cables |

De la tabla de compras del README del chasis. Los remaches y pasadores son impresos (tanda 5).
