# Peso del montaje

> Generado por `python -m app.documentos` desde `config/masas.yaml` y `config/precios.yaml` (piezas
> impresas, maqueta impresa y tornillería): no editar a mano. Masas de hoja de datos o estimadas por material
> x volumen (2026-09-28): PESAR lo marcado *estimado* cuando esté en la mano.

**Peso total del montaje: 8,08 kg** (sin el portátil). De eso, 7,00 kg (87 %) son **estimados**; el resto es de hoja de datos.

No hay celda de carga en el diseño (prohibidas por el grupo): estas masas son para dimensionar motores y estructura, no se miden en la línea.

## Por subsistema

| Subsistema | Masa | % |
|---|---:|---:|
| Cinta de monedas | 1,16 kg | 14 % |
| Almacén | 0,26 kg | 3 % |
| Cinta de vasos | 1,42 kg | 18 % |
| Pórtico | 0,39 kg | 5 % |
| Canaleta y muelle | 0,27 kg | 3 % |
| Estructura impresa | 1,38 kg | 17 % |
| Carro | 0,51 kg | 6 % |
| Caja de control | 1,80 kg | 22 % |
| Pista | 0,89 kg | 11 % |
| **Total** | **8,08 kg** | **100 %** |

## Comprobaciones con estas masas

> ✅ Con estas masas todos los motores alcanzan con margen x2 o más.

Criterio: un motor **alcanza** si da al menos 2 veces lo que se le pide (margen x2: cubre lo que no se sabe todavía, como la tensión real de la banda o el roce de una pieza mal alineada). Vaso lleno en el peor caso: vaso 25 g + tapa 8 g + 10 monedas de 10 g = **133 g**.

### Cinta de monedas: NEMA 17 17HS4401

Peor caso: las 10 casillas de la banda con una moneda de 10 g. Banda 66 g, separadores 15 g, carga 100 g, cada rodillo 88 g. Avance de 40 mm en 0,6 s.

```
a      = 4·d / t²                                  = 4 x 0,040 / 0,6² = 0,44 m/s²
F_roz  = μ·(m_banda/2 + m_sep/2 + m_carga)·g       = 0,60 x 0,140 x 9,81 = 0,83 N
F_in   = (m_banda + m_sep + m_carga)·a              = 0,181 x 0,44 = 0,080 N
T_rod  = 2 rodillos · μ_rod · 2·T0 · r_eje          = 2 x 0,0015 x 2 x 20 x 0,004 = 0,00048 N·m
T_giro = (I_rotor + 2·m_rodillo·r²) · a / r
T      = (F_roz + F_in)·r + T_rod + T_giro
T_disp = T_retención · (I_driver / I_nominal) · 0,50 = 0,40 x (1,0 / 1,7) x 0,50 = 0,118 N·m
```

| Radio del rodillo | r (mm) | Par pedido (N·m) | Disponible (N·m) | Margen | rpm pico |
|---|---:|---:|---:|---:|---:|
| modelo 3D (Ø22) | 11,0 | 0,0115 | 0,118 | x10,2 | 116 |

Resultado: ✅ **ALCANZA** (margen x10,2) con el peor radio (modelo 3D (Ø22)). Lo que más pide es el rozamiento de la banda contra la cama (0,0091 N·m de 0,0115).

### Cinta de vasos: NEMA 17 17HS4401

Peor caso: 5 vasos llenos sobre la banda. Banda 128 g, separadores 48 g, carga 665 g, cada rodillo 45 g. Avance de 80 mm en 1,0 s.

```
a      = 4·d / t²                                  = 4 x 0,080 / 1,0² = 0,32 m/s²
F_roz  = μ·(m_banda/2 + m_sep/2 + m_carga)·g       = 0,60 x 0,753 x 9,81 = 4,43 N
F_in   = (m_banda + m_sep + m_carga)·a              = 0,841 x 0,32 = 0,269 N
T_rod  = 2 rodillos · μ_rod · 2·T0 · r_eje          = 2 x 0,0015 x 2 x 20 x 0,004 = 0,00048 N·m
T_giro = (I_rotor + 2·m_rodillo·r²) · a / r
T      = (F_roz + F_in)·r + T_rod + T_giro
T_disp = T_retención · (I_driver / I_nominal) · 0,50 = 0,40 x (1,0 / 1,7) x 0,50 = 0,118 N·m
```

| Radio del rodillo | r (mm) | Par pedido (N·m) | Disponible (N·m) | Margen | rpm pico |
|---|---:|---:|---:|---:|---:|
| modelo 3D (Ø22) | 11,0 | 0,0527 | 0,118 | x2,2 | 139 |

Resultado: ✅ **ALCANZA** (margen x2,2) con el peor radio (modelo 3D (Ø22)). Lo que más pide es el rozamiento de la banda contra la cama (0,0488 N·m de 0,0527).

Rodillo: Ø22 mm, el mismo en el modelo 3D y en el firmware (`firmware.mm_por_vuelta_cinta` = 69,1 mm por vuelta = π·22).

### MG996R de la prensa (leva excéntrica)

```
T = (F + m_pistón·g) · e · sen(θ)        peor punto: θ = 90° (sen = 1)
e = 7,0 mm;  par de bloqueo MG996R: 0,92 N·m a 4,8 V, 1,08 N·m a 6 V
```

| Fuerza en la tapa | Par pedido a 90° | Margen a 6 V | Margen a 4,8 V | Resultado |
|---|---:|---:|---:|---|
| tapa (máx. provisional): 50 N | 0,350 N·m | x3,09 | x2,63 | ✅ **ALCANZA** |
| objetivo de la prensa (tope de diseño): 60 N | 0,420 N·m | x2,57 | x2,19 | ✅ **ALCANZA** |

La tapa sella a presión (snap-fit: el reborde de la tapa salta sobre el labio del vaso), lo que pide 30-50 N (PROVISIONAL hasta medirla); pasado el salto, apretar más solo deforma el vaso. Por eso la prensa apunta a **60 N** (la tapa más dura x1,2) como tope de diseño para el servo. La maqueta impresa no lleva resorte limitador: la fuerza la da el apriete de 0,5 mm al final de la carrera (leva de 7,0 mm, el pistón baja 14 mm) más los suplementos impresos de 0,5 y 1,0 mm que se pegan bajo el plato, contra la rigidez del lazo de la prensa (estimada ~0,05 mm/N con la placa con costillas y remachada a la columna: ~10 N con 0,5 mm y ~40 N con los dos suplementos): hay que medir la tapa y el lazo con una balanza y elegir el suplemento. A 90° de la leva (el peor punto) eso pide 0,42 N·m, el 39 % del bloqueo a 6 V. (Antes el catálogo decía "≥150 N": el MG996R con esta leva no lo sostiene en toda la carrera y la tapa no lo necesita.)

### MG996R del empujador (manivela)

```
F = μ·m_vaso_lleno·g + roce de la paleta (10 % de su peso);   T = F · r_manivela
F = 0,60 x 0,133 x 9,81 + … = 0,78 N;   T = 0,78 x 0,035 = 0,0274 N·m
```

Resultado: ✅ **ALCANZA** (margen x39,4) (de 1,08 N·m a 6 V).

### Carro con el vaso lleno: motores TT 1:48

Masa del carro (suma de su subsistema): **0,51 kg**; con el vaso lleno: **0,64 kg**. Rueda de 65 mm; el firmware pide hasta 1,0 m/s² (`vehiculo.aceleracion_max_m_s2`) y 0,40 m/s en la línea.

```
F_rr   = Crr·m·g                    = 0,03 x 0,642 x 9,81 = 0,189 N
F      = m·a + F_rr                 = 0,642 x 1,0 + 0,189 = 0,831 N
T/motor = F·r / 2                   = 0,831 x 0,0325 / 2 = 0,0135 N·m
T_disp(v) = T_arranque·(1 - v/v_max)  (motor DC: el par cae con la velocidad), v_max = 0,55 m/s
a sostenida hasta v = v_max·(1 - T/motor ÷ T_arranque) = 0,46 m/s
a_max (motores, parado) = (2·T_arranque/r - F_rr)/m  = 7,4 m/s²
a_patina  = μ·g·fracción en ruedas - Crr·g           = 4,5 m/s²
a_vuelco del carro = g·d_apoyo / h_cg                 = 13,1 m/s²
a_vuelco del vaso (si estuviera suelto) = g·(D/2)/h_cg = 6,8 m/s²
```

| Qué | Pedido | Disponible / límite | Margen | Resultado |
|---|---:|---:|---:|---|
| Par por motor al arrancar | 0,0135 N·m | 0,08 N·m | x5,9 | ✅ **ALCANZA** |
| Llegar a 0,40 m/s acelerando a 1,0 m/s² | 0,40 m/s | 0,46 m/s | x1,14 | ✅ **ALCANZA** |
| Par por motor en crucero (0,40 m/s) | 0,0031 N·m | 0,0218 N·m | x7,1 | ✅ **ALCANZA** |
| Que las llantas no patinen | 1,0 m/s² | 4,5 m/s² | x4,5 | ✅ **ALCANZA** |
| Que el carro no vuelque al frenar | 1,0 m/s² | 13,1 m/s² | x13,1 | ✅ **ALCANZA** |
| Que el vaso no vuelque | 1,0 m/s² | 6,8 m/s² | x6,8 | ✅ **ALCANZA** |

El vaso va colgado del reborde en la cuna (centro de masa bajo el apoyo): a 1,0 m/s² se inclina como mucho 5,8° y lo frenan la espuma y la lengüeta; ni suelto se volcaría.

## Detalle por subsistema

La cinta de monedas va primero y con todo su detalle: su NEMA 17 es el que más pasos da por turno.

### Cinta de monedas: 1,16 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Maqueta impresa: cinta de monedas (PLA) | 1 | 318,7 | 318,7 | *estimado* | 20 piezas, gramos del exportador de la maqueta (maqueta_impresa/piezas.json) |
| Motor de la cinta de monedas | 1 | 280,0 | 280,0 | hoja de datos | 17HS4401: 0,28 kg |
| Cámara cenital | 1 | 110,0 | 110,0 | *estimado* | webcam 1080p con su cable (~80 g) + anillo LED (~30 g) |
| Rodillos de retorno A y B (Ø22 x 59) con sus ejes Ø8 fijos | 1 | 100,0 | 100,0 | *estimado* | 2 tubos de aluminio Ø22 pared 1 mm: π·22·59·1 = 4,1 cm³ x 2,7 = 11 g c/u; ejes de acero Ø8 de 114 (A: cuelga de las bajadas de los bloques del motriz) y 84,3 mm (B) de cinta_monedas.scad: π·4²·198,3 = 10,0 cm³ x 7,85 = 78 g. Sin el retorno C (2026-10-25: quedaba dentro del lazo y no tocaba la banda) |
| Rodillos Ø22 x 59 mm con su eje de 8 mm (x2) | 1 | 76,0 | 76,0 | *estimado* | tubo de aluminio Ø22 pared 1 mm: π·22·59·1 = 4,1 cm³ x 2,7 = 11 g + eje de acero Ø8 x 68: 3,4 cm³ x 7,85 = 27 g; = 38 g por rodillo |
| Banda de caucho de 55 mm (cerrada) | 1 | 65,9 | 65,9 | *estimado* | largo ~615 mm (línea media del casco del motriz, el tensor y los retornos A y B de cinta_monedas.scad: 611,5 con el tensor en x 86 y 618 en x 90; segunda opinión 2026-10-25) x 55 mm x 1,5 mm de espesor. Antes 638 (contaba el retorno C, que queda dentro del lazo) y 930 (la cinta vieja de 2 rodillos) |
| Sensor capacitivo | 1 | 60,0 | 60,0 | *estimado* | cuerpo M18 x 60 mm con 2 tuercas + 1 m de cable |
| Sensor inductivo | 1 | 55,0 | 55,0 | *estimado* | LJ18A3-8: cuerpo M18 con tuercas + 1 m de cable |
| Rodamientos 608ZZ (x4) | 1 | 48,0 | 48,0 | hoja de datos | 608ZZ: 12 g c/u |
| Separadores de casilla de la banda (15, a L/15 ≈ 41 mm) | 1 | 15,0 | 15,0 | *estimado* | una banda cerrada solo tiene casillas iguales si su largo es N x paso: ~615 mm / 15 = 41 mm (quedan 38 mm libres para la moneda de Ø26,7; con 16 cada 40 sobraba una casilla de ~15-18 mm). Listón de caucho de 55 x 3 x 4 mm: 0,7 cm³ x 1,3 ≈ 1 g c/u |
| Servo de la compuerta de desvío (E4) | 1 | 9,0 | 9,0 | hoja de datos | SG90: 9 g |
| Acople flexible 5 a 8 mm | 1 | 9,0 | 9,0 | hoja de datos | acople helicoidal de aluminio Ø19 x 25 |
| Tornillo M3 x 12 (NEMA 17: placa + separador de nailon de 3 mm) | 4 | 1,1 | 4,4 | *estimado* |  |
| Infrarrojo de presencia | 1 | 3,0 | 3,0 | *estimado* | módulo FC-51 (PCB de 31 x 14 mm) |
| Tornillo 1/4"-20 x 12 mm (rosca de trípode de las webcams) | 1 | 3,0 | 3,0 | *estimado* |  |
| Tornillo M3 x 16 autorroscante (empuje del tensor de la cinta de monedas; agujero de 2,6 mm en PLA, MEDIR) | 2 | 1,2 | 2,4 | *estimado* |  |
| Tornillo M3 x 10 | 1 | 1,0 | 1,0 | *estimado* |  |
| Tuerca M3 | 1 | 0,4 | 0,4 | *estimado* |  |
| **Subtotal** | | | **1.160,8** | | |

### Almacén: 0,26 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Maqueta impresa: almacén de monedas (PLA) | 1 | 206,8 | 206,8 | *estimado* | 10 piezas, gramos del exportador de la maqueta (maqueta_impresa/piezas.json) |
| Motor del carrusel del almacén | 1 | 30,0 | 30,0 | hoja de datos | 28BYJ-48: ~30 g |
| Rodamiento 608ZZ del eje del carrusel (en la placa fija) | 1 | 12,0 | 12,0 | hoja de datos | 608ZZ: 12 g (almacen.scad) |
| Servo del obturador del almacén | 1 | 9,0 | 9,0 | hoja de datos | SG90: 9 g |
| Sensor Hall del carrusel | 1 | 3,0 | 3,0 | *estimado* | módulo 3144 + imán de neodimio de 6 mm |
| Tornillo M4 autorroscante corto (28BYJ-48: oreja + agujero ciego de 3,6 mm, MEDIR el largo) | 2 | 1,0 | 2,0 | *estimado* |  |
| **Subtotal** | | | **262,8** | | |

### Cinta de vasos: 1,42 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Maqueta impresa: cinta de vasos (PLA) | 1 | 575,6 | 575,6 | *estimado* | 34 piezas, gramos del exportador de la maqueta (maqueta_impresa/piezas.json) |
| Motor de la cinta de vasos | 1 | 280,0 | 280,0 | hoja de datos | 17HS4401: 0,28 kg |
| Banda de caucho de 75 mm (cerrada) | 1 | 127,9 | 127,9 | *estimado* | largo 2 x 400 + 2π x 12 = 875 mm (línea media de una banda de 2 sobre los Ø22) x 75 mm x 1,5 mm |
| Rodillos Ø22 x 79 mm con su eje (x2) | 1 | 90,0 | 90,0 | *estimado* | igual que los de monedas pero de 79 mm: ~45 g por rodillo |
| Varillas guía Ø8 del empujador (x2) y separadores de nailon de 3 mm del NEMA (x4) | 1 | 82,0 | 82,0 | *estimado* | varillas de acero Ø8 x 102,5 mm: 5,2 cm³ x 7,85 = 40 g c/u; separadores de nailon ~0,5 g. Los postes del motor (32,8 mm) son impresos: van en vas_lat_s_a |
| Cámara de vasos (silueta, ArUco y tapa) | 1 | 70,0 | 70,0 | *estimado* | webcam 720p con su cable |
| Rodamiento con brida KFL08 (x1) y rodamientos 608ZZ (x3) | 1 | 66,0 | 66,0 | hoja de datos | KFL08 de zamak ~30 g (eje motriz, lateral -y) + 3 x 608ZZ de 12 g (cinta_vasos.scad) |
| Servo del empujador de descarga | 1 | 55,0 | 55,0 | hoja de datos | MG996R: 55 g |
| Separadores de casilla de la banda (11, a L/11 ≈ 79,6 mm; cada uno con su taco separador impreso, que va en la maqueta) | 1 | 48,2 | 48,2 | *estimado* | 875,4 mm de banda / 80 = 10,94: 11 separadores a L/11 (segunda opinión 2026-10-25; antes 7, con dos huecos de 238 mm). Separador de 3 x 75 x 15 mm (cinta_vasos.scad, vas_sep; viene con la banda): 3,4 cm³ c/u |
| Acople flexible 5 a 8 mm | 1 | 9,0 | 9,0 | hoja de datos |  |
| Tornillo M4 x 16 (rodamiento KFL08: brida de 37 mm entre agujeros contra Ø5,5 a 36 en la lateral) | 2 | 2,5 | 5,0 | *estimado* |  |
| Tornillo M3 x 12 (NEMA 17: placa + separador de nailon de 3 mm) | 4 | 1,1 | 4,4 | *estimado* |  |
| Tornillo 1/4"-20 x 12 mm (rosca de trípode de las webcams) | 1 | 3,0 | 3,0 | *estimado* |  |
| Sensor del interior del vaso | 1 | 2,0 | 2,0 | *estimado* | módulo GY-VL53L0XV2 |
| Cortina de seguridad | 1 | 2,0 | 2,0 | *estimado* | módulo GY-VL53L0XV2 |
| Tuerca M4 | 2 | 0,8 | 1,6 | *estimado* |  |
| Prisionero M3 x 10 punta de copa (tensor de la cinta de vasos; rosca en un agujero de 2,5 mm en PLA, MEDIR) | 2 | 0,5 | 1,0 | *estimado* |  |
| **Subtotal** | | | **1.422,8** | | |

### Pórtico: 0,39 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Maqueta impresa: tapas, prensa y empujador (PLA) | 1 | 300,6 | 300,6 | *estimado* | 23 piezas, gramos del exportador de la maqueta (maqueta_impresa/piezas.json) |
| Servo de la prensa | 1 | 55,0 | 55,0 | hoja de datos | MG996R: 55 g |
| Panel de luz de la cámara de vasos | 1 | 20,0 | 20,0 | *estimado* | tira LED de 1 m (~20 g); la caja de luz es de PLA blanco (vas_panel_a/b) y va en la maqueta impresa (antes 130 g de acrílico opalino) |
| Servo del escape de tapas | 1 | 9,0 | 9,0 | hoja de datos | SG90: 9 g |
| Tornillo M4 x 20 de perno de la biela del empujador | 2 | 2,5 | 5,0 | *estimado* |  |
| Pasador de acero Ø2 x 17 (pernos del cuerno del escape de tapas) | 2 | 0,4 | 0,8 | *estimado* |  |
| Tornillo M2 x 8 autorroscante (servos, placas) | 2 | 0,3 | 0,6 | *estimado* |  |
| **Subtotal** | | | **391,0** | | |

### Canaleta y muelle: 0,27 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Maqueta impresa: canaleta y muelle (PLA) | 1 | 194,6 | 194,6 | *estimado* | 17 piezas, gramos del exportador de la maqueta (maqueta_impresa/piezas.json) |
| Canaleta de entrega | 1 | 55,0 | 55,0 | *estimado* | 2 varillas de acero Ø4 x 284 mm: π·2²·284 = 3,6 cm³ x 7,85 = 28 g c/u, + cinta de PTFE |
| Servo del escape de la canaleta | 1 | 9,0 | 9,0 | hoja de datos | SG90: 9 g |
| Espuma de los topes y cinta de PTFE | 1 | 8,0 | 8,0 | *estimado* |  |
| **Subtotal** | | | **266,6** | | |

### Estructura impresa: 1,38 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Maqueta impresa: estructura: tubos de 16 x 16 (PLA) | 1 | 813,0 | 813,0 | *estimado* | 46 piezas, gramos del exportador de la maqueta (maqueta_impresa/piezas.json) |
| Maqueta impresa: estructura: nodos (PLA) | 1 | 400,5 | 400,5 | *estimado* | 22 piezas, gramos del exportador de la maqueta (maqueta_impresa/piezas.json) |
| Maqueta impresa: estructura: empalmes y tacos (PLA) | 1 | 119,3 | 119,3 | *estimado* | 11 piezas, gramos del exportador de la maqueta (maqueta_impresa/piezas.json) |
| Maqueta impresa: remaches impresos (PLA) | 1 | 49,8 | 49,8 | *estimado* | 382 piezas, gramos del exportador de la maqueta (maqueta_impresa/piezas.json) |
| **Subtotal** | | | **1.382,6** | | |

### Carro: 0,51 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Batería del carro | 1 | 112,0 | 112,0 | hoja de datos | 2 celdas 18650 de 2500 mAh (46 g c/u) + portapilas 2S (~15 g) + BMS (~5 g) |
| Motorreductores del carro | 2 | 50,0 | 100,0 | *estimado* | motorreductor TT 1:48 (~30 g) + llanta de 65 mm (~20 g), por lado |
| Placa de acrílico de 180 x 120 x 3 mm (con el hueco del vaso) | 1 | 64,9 | 64,9 | *estimado* | 180 x 120 x 3 = 64,8 cm³ menos el hueco Ø66 (10,3 cm³) |
| Cuna del vaso (mampara, postes, brazos, asientos, lengüeta) (impresa) | 1 | 46,5 | 46,5 | *estimado* | 37,5 cm³ x 1,24 g/cm³ x 100% de llenado |
| Rueda loca de bola de acero 3/4" | 1 | 35,0 | 35,0 | *estimado* | bola de acero de 19 mm (28 g) + carcasa |
| Separadores de latón, tornillos de las placas y cables del carro | 1 | 25,0 | 25,0 | *estimado* |  |
| Tornillo M3 x 10 | 16 | 1,0 | 16,0 | *estimado* |  |
| Soportes en T de los motores (acrílico 3 mm, x2) con tornillos | 1 | 16,0 | 16,0 | *estimado* | ~5 g de acrílico + 3 g de tornillos M3 x 25 por lado |
| Arreglo de 5 infrarrojos de línea | 1 | 12,0 | 12,0 | *estimado* | placa de 5 TCRT5000 |
| Rodillos guía traseros | 2 | 6,0 | 12,0 | *estimado* | 2 rodamientos 623 (~1,7 g c/u) + tornillo M3 x 30 y tuerca, por esquina |
| ESP32 del carro | 1 | 10,0 | 10,0 | hoja de datos | ESP32 DevKit de 30 pines: ~9-10 g |
| Ultrasónico frontal (respaldo) | 1 | 8,5 | 8,5 | hoja de datos | HC-SR04: 8,5 g |
| Interruptor y fusible del carro | 1 | 8,0 | 8,0 | *estimado* | interruptor KCD11 + portafusible y fusible (la caja impresa va aparte) |
| Escuadra frontal del HC-SR04 y el VL53L0X (impresa) | 1 | 7,8 | 7,8 | *estimado* | 6,3 cm³ x 1,24 g/cm³ x 100% de llenado |
| Brazo del rodillo guía trasero (impresa) | 2 | 3,7 | 7,4 | *estimado* | 3,0 cm³ x 1,24 g/cm³ x 100% de llenado |
| Tuerca M3 | 12 | 0,4 | 4,8 | *estimado* |  |
| Encoders de las ruedas | 1 | 4,0 | 4,0 | *estimado* | herradura F249 (~3 g) + disco de 20 ranuras (~1 g), por rueda |
| Tornillo M3 x 30 | 2 | 2,0 | 4,0 | *estimado* |  |
| Caja del interruptor y el fusible (impresa) | 1 | 3,7 | 3,7 | *estimado* | 3,0 cm³ x 1,24 g/cm³ x 100% de llenado |
| Infrarrojo de la cuna de carga | 1 | 3,0 | 3,0 | *estimado* | módulo TCRT5000 de 1 canal |
| Puente H del carro | 1 | 3,0 | 3,0 | *estimado* | placa TB6612FNG de 20 x 20 mm |
| Soporte del encoder H206 (impresa) | 2 | 1,2 | 2,5 | *estimado* | 1,0 cm³ x 1,24 g/cm³ x 100% de llenado |
| Láser de distancia frontal | 1 | 2,0 | 2,0 | *estimado* | módulo GY-VL53L0XV2 |
| Tornillo M2 x 8 autorroscante (servos, placas) | 4 | 0,3 | 1,2 | *estimado* |  |
| **Subtotal** | | | **509,3** | | |

### Caja de control: 1,80 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Gabinete de acrílico 360 x 240 x 80 mm, 3 mm (con tapa) | 1 | 955,6 | 955,6 | *estimado* | piso y tapa 2 x 360 x 240 + paredes 2 x 360 x 80 + 2 x 234 x 80 = 0,268 m² x 3 mm |
| Fuente de 12 V | 1 | 300,0 | 300,0 | *estimado* | fuente conmutada 12 V 5 A de caja metálica (genérica de 60 W: ~0,3 kg) |
| Cables de la caja y de campo (18 AWG, dupont, JST) | 1 | 250,0 | 250,0 | *estimado* | ~15 m de cable de 18-24 AWG entre caja, planta y sensores |
| Cable de poder de la fuente | 1 | 120,0 | 120,0 | *estimado* | cable de poder de 3 x 18 AWG de 1,5 m con enchufe |
| ESP32 fijo (estación) | 1 | 35,0 | 35,0 | *estimado* | ESP32 DevKit 38 pines (~10 g) + placa de expansión GVS (~25 g) |
| Regulador de 6 V (servos) | 1 | 25,0 | 25,0 | *estimado* | XL4015 de 5 A con su disipador |
| Bridas y ventilador | 1 | 25,0 | 25,0 | *estimado* | ~40 bridas usadas (~0,3 g c/u) + 10 bases adhesivas (~1 g) + ventilador 4010 (~6 g) |
| Drivers de las dos cintas (M y V) | 2 | 12,0 | 24,0 | *estimado* | A4988 con disipador (~3 g) + su mitad de la placa perforada, por driver |
| Regulador de 5 V | 1 | 12,0 | 12,0 | *estimado* | módulo LM2596 |
| Fusible principal | 1 | 10,0 | 10,0 | *estimado* | un portafusible de 1 vía con su fusible |
| Controlador de servos | 1 | 9,0 | 9,0 | hoja de datos | PCA9685 de 16 canales: ~9 g |
| Tornillo M4 x 12 | 4 | 2,0 | 8,0 | *estimado* |  |
| Taco de esquina de la tapa de la caja (impresa) | 4 | 1,9 | 7,5 | *estimado* | 2,9 cm³ x 1,24 g/cm³ x 52% de llenado |
| Driver del carrusel | 1 | 6,0 | 6,0 | *estimado* | placa ULN2003 del kit del 28BYJ-48 |
| Empalmes soldados | 1 | 5,0 | 5,0 | *estimado* | estaño, termoencogible, 2 diodos y 5 resistencias (la de 3,3 Ω 1 W del panel de luz, ~1 g) |
| Tuerca M4 | 4 | 0,8 | 3,2 | *estimado* |  |
| **Subtotal** | | | **1.795,2** | | |

### Pista: 0,89 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Lámina blanca de la pista (cartón/vinilo de 1 mm, 160 mm de ancho) | 1 | 392,5 | 392,5 | *estimado* | malla del modelo: 0,56 m² x 1 mm |
| 3 muros-obstáculo de bloques de juguete (100 x 30 x 80 mm) | 1 | 360,0 | 360,0 | *estimado* | bloques de ABS huecos: ~120 g por muro |
| Bandera de la meta (mástil de aluminio Ø6 x 250 y base de Ø60) | 1 | 80,0 | 80,0 | *estimado* |  |
| Pista con 3 obstáculos y meta | 1 | 60,0 | 60,0 | hoja de datos | rollo de cinta aislante 3M de 18 m (la lámina y los muros van en `otros`) |
| **Subtotal** | | | **892,5** | | |
