# Peso del montaje

> Generado por `python -m app.documentos` desde `config/masas.yaml` y `config/precios.yaml` (piezas
> impresas, perfil y tornillería): no editar a mano. Masas de hoja de datos o estimadas por material
> x volumen (2026-09-28): PESAR lo marcado *estimado* cuando esté en la mano.

**Peso total del montaje: 13,38 kg** (sin el portátil). De eso, 9,21 kg (69 %) son **estimados**; el resto es de hoja de datos.

No hay celda de carga en el diseño (prohibidas por el grupo): estas masas son para dimensionar motores y estructura, no se miden en la línea.

## Por subsistema

| Subsistema | Masa | % |
|---|---:|---:|
| Cinta de monedas | 2,96 kg | 22 % |
| Almacén | 0,23 kg | 2 % |
| Cinta de vasos | 2,59 kg | 19 % |
| Pórtico | 1,35 kg | 10 % |
| Canaleta y muelle | 1,08 kg | 8 % |
| Carro | 0,51 kg | 4 % |
| Caja de control | 2,18 kg | 16 % |
| Pista y base | 2,47 kg | 18 % |
| **Total** | **13,38 kg** | **100 %** |

## Comprobaciones con estas masas

> ✅ Con estas masas todos los motores alcanzan con margen x2 o más.

Criterio: un motor **alcanza** si da al menos 2 veces lo que se le pide (margen x2: cubre lo que no se sabe todavía, como la tensión real de la banda o el roce de una pieza mal alineada). Vaso lleno en el peor caso: vaso 25 g + tapa 8 g + 10 monedas de 10 g = **133 g**.

### Cinta de monedas: NEMA 17 17HS4401

Peor caso: las 10 casillas de la banda con una moneda de 10 g. Banda 100 g, separadores 23 g, carga 100 g, cada rodillo 38 g. Avance de 40 mm en 0,6 s.

```
a      = 4·d / t²                                  = 4 x 0,040 / 0,6² = 0,44 m/s²
F_roz  = μ·(m_banda/2 + m_sep/2 + m_carga)·g       = 0,60 x 0,161 x 9,81 = 0,95 N
F_in   = (m_banda + m_sep + m_carga)·a              = 0,223 x 0,44 = 0,099 N
T_rod  = 2 rodillos · μ_rod · 2·T0 · r_eje          = 2 x 0,0015 x 2 x 20 x 0,004 = 0,00048 N·m
T_giro = (I_rotor + 2·m_rodillo·r²) · a / r
T      = (F_roz + F_in)·r + T_rod + T_giro
T_disp = T_retención · (I_driver / I_nominal) · 0,50 = 0,40 x (1,0 / 1,7) x 0,50 = 0,118 N·m
```

| Radio del rodillo | r (mm) | Par pedido (N·m) | Disponible (N·m) | Margen | rpm pico |
|---|---:|---:|---:|---:|---:|
| modelo 3D (Ø22) | 11,0 | 0,0126 | 0,118 | x9,3 | 116 |

Resultado: ✅ **ALCANZA** (margen x9,3) con el peor radio (modelo 3D (Ø22)). Lo que más pide es el rozamiento de la banda contra la cama (0,0104 N·m de 0,0126).

### Cinta de vasos: NEMA 17 17HS4401

Peor caso: 5 vasos llenos sobre la banda. Banda 122 g, separadores 79 g, carga 665 g, cada rodillo 45 g. Avance de 80 mm en 1,0 s.

```
a      = 4·d / t²                                  = 4 x 0,080 / 1,0² = 0,32 m/s²
F_roz  = μ·(m_banda/2 + m_sep/2 + m_carga)·g       = 0,60 x 0,765 x 9,81 = 4,50 N
F_in   = (m_banda + m_sep + m_carga)·a              = 0,866 x 0,32 = 0,277 N
T_rod  = 2 rodillos · μ_rod · 2·T0 · r_eje          = 2 x 0,0015 x 2 x 20 x 0,004 = 0,00048 N·m
T_giro = (I_rotor + 2·m_rodillo·r²) · a / r
T      = (F_roz + F_in)·r + T_rod + T_giro
T_disp = T_retención · (I_driver / I_nominal) · 0,50 = 0,40 x (1,0 / 1,7) x 0,50 = 0,118 N·m
```

| Radio del rodillo | r (mm) | Par pedido (N·m) | Disponible (N·m) | Margen | rpm pico |
|---|---:|---:|---:|---:|---:|
| modelo 3D (Ø22) | 11,0 | 0,0536 | 0,118 | x2,2 | 139 |

Resultado: ✅ **ALCANZA** (margen x2,2) con el peor radio (modelo 3D (Ø22)). Lo que más pide es el rozamiento de la banda contra la cama (0,0496 N·m de 0,0536).

Rodillo: Ø22 mm, el mismo en el modelo 3D y en el firmware (`firmware.mm_por_vuelta_cinta` = 69,1 mm por vuelta = π·22).

### MG996R de la prensa (leva excéntrica)

```
T = (F + m_pistón·g) · e · sen(θ)        peor punto: θ = 90° (sen = 1)
e = 6,5 mm;  par de bloqueo MG996R: 0,92 N·m a 4,8 V, 1,08 N·m a 6 V
```

| Fuerza en la tapa | Par pedido a 90° | Margen a 6 V | Margen a 4,8 V | Resultado |
|---|---:|---:|---:|---|
| tapa (máx. provisional): 50 N | 0,326 N·m | x3,31 | x2,82 | ✅ **ALCANZA** |
| objetivo de la prensa (lo limita el resorte): 60 N | 0,391 N·m | x2,76 | x2,35 | ✅ **ALCANZA** |

La tapa sella a presión (snap-fit: el reborde de la tapa salta sobre el labio del vaso), lo que pide 30-50 N (PROVISIONAL hasta medirla); pasado el salto, apretar más solo deforma el vaso. Por eso la prensa apunta a **60 N** (la tapa más dura x1,2) y el resorte limitador del plato se elige para no pasar de ahí al final de la carrera. A 90° de la leva (el peor punto) eso pide 0,39 N·m, el 36 % del bloqueo a 6 V. (Antes el catálogo decía "≥150 N": el MG996R con esta leva no lo sostiene en toda la carrera y la tapa no lo necesita.)

### MG996R del empujador (manivela)

```
F = μ·m_vaso_lleno·g + roce de la paleta (10 % de su peso);   T = F · r_manivela
F = 0,60 x 0,133 x 9,81 + … = 0,80 N;   T = 0,80 x 0,035 = 0,0282 N·m
```

Resultado: ✅ **ALCANZA** (margen x38,4) (de 1,08 N·m a 6 V).

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

### Cinta de monedas: 2,96 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Perfil 2020: pata de la mesa de monedas (418 mm) | 3 | 209,0 | 627,0 | hoja de datos | 418 mm x 0,50 kg/m |
| Platinas laterales de aluminio 430 x 34 x 4 mm (x2) | 1 | 315,9 | 315,9 | *estimado* | malla del modelo: 58,5 cm³ cada una |
| Motor de la cinta de monedas | 1 | 280,0 | 280,0 | hoja de datos | 17HS4401: 0,28 kg |
| Perfil 2020: larguero del riel de la cinta de monedas (251 mm) | 2 | 125,5 | 251,0 | hoja de datos | 251 mm x 0,50 kg/m |
| Perfil 2020: poste de la compuerta de desvío E4 (377 mm) | 1 | 188,5 | 188,5 | hoja de datos | 377 mm x 0,50 kg/m |
| Perfil 2020: poste de la cámara cenital (240 mm) | 1 | 120,0 | 120,0 | hoja de datos | 240 mm x 0,50 kg/m |
| Cámara cenital | 1 | 110,0 | 110,0 | *estimado* | webcam 1080p con su cable (~80 g) + anillo LED (~30 g) |
| Banda de caucho de 55 mm (cerrada) | 1 | 99,7 | 99,7 | *estimado* | largo 2 x 430 + π x 22 = 930 mm x 55 mm x 1,5 mm de espesor |
| Pie nivelador M6 Ø26 con contratuerca | 4 | 20,0 | 80,0 | *estimado* |  |
| Perfil 2020: travesaño lateral (a lo largo) (155 mm) | 1 | 77,5 | 77,5 | hoja de datos | 155 mm x 0,50 kg/m |
| Rodillos Ø22 x 57 mm con su eje de 8 mm (x2) | 1 | 76,0 | 76,0 | *estimado* | tubo de aluminio Ø22 pared 1 mm: π·22·57·1 = 3,9 cm³ x 2,7 = 11 g + eje de acero Ø8 x 68: 3,4 cm³ x 7,85 = 27 g; = 38 g por rodillo |
| Escuadra 2020 de fundición | 5 | 14,0 | 70,0 | *estimado* |  |
| Bandeja de rechazo de monedas (impresa) | 1 | 63,2 | 63,2 | *estimado* | 51,0 cm³ x 1,24 g/cm³ x 100% de llenado |
| Sensor capacitivo | 1 | 60,0 | 60,0 | *estimado* | cuerpo M18 x 60 mm con 2 tuercas + 1 m de cable |
| Sensor inductivo | 1 | 55,0 | 55,0 | *estimado* | LJ18A3-8: cuerpo M18 con tuercas + 1 m de cable |
| Canal largo a la bandeja de rechazo (impresa) | 1 | 48,5 | 48,5 | *estimado* | 39,1 cm³ x 1,24 g/cm³ x 100% de llenado |
| Tuerca en T M5 (martillo) para 2020 | 24 | 2,0 | 48,0 | *estimado* |  |
| Rodamientos 608ZZ (x4) | 1 | 48,0 | 48,0 | hoja de datos | 608ZZ: 12 g c/u |
| Tornillo M5 x 10 cabeza Allen | 15 | 3,0 | 45,0 | *estimado* |  |
| Perfil 2020: brazo de la cámara cenital (70 mm) | 1 | 35,0 | 35,0 | hoja de datos | 70 mm x 0,50 kg/m |
| Perfil 2020: travesaño de la cola (a lo ancho) (61 mm) | 1 | 30,5 | 30,5 | hoja de datos | 61 mm x 0,50 kg/m |
| Tornillo M3 x 10 | 28 | 1,0 | 28,0 | *estimado* |  |
| Tornillo M5 x 8 ISO 7380 (escuadras) | 10 | 2,5 | 25,0 | *estimado* |  |
| Separadores de casilla de la banda (cada 40 mm, ~23) | 1 | 23,0 | 23,0 | *estimado* | listón de caucho de 55 x 3 x 4 mm: 0,7 cm³ x 1,3 ≈ 1 g c/u |
| Platinas de los sensores M18 (x2) | 1 | 21,6 | 21,6 | *estimado* | platina de 36 x 61 mm de 2 mm con agujero de 18 mm: ~4 cm³ c/u |
| Brazo de las platinas M18 (capacitivo e inductivo) (impresa) | 4 | 5,0 | 19,8 | *estimado* | 4,0 cm³ x 1,24 g/cm³ x 100% de llenado |
| Jaula del NEMA 17 de la cinta de monedas (impresa) | 1 | 17,9 | 17,9 | *estimado* | 27,8 cm³ x 1,24 g/cm³ x 52% de llenado |
| Canal corto al carrusel / al rechazo (impresa) | 2 | 7,4 | 14,9 | *estimado* | 6,0 cm³ x 1,24 g/cm³ x 100% de llenado |
| Tuerca M3 | 26 | 0,4 | 10,4 | *estimado* |  |
| Bloque tensor del rodamiento 608 (impresa) | 2 | 5,2 | 10,3 | *estimado* | 8,0 cm³ x 1,24 g/cm³ x 52% de llenado |
| Servo de la compuerta de desvío (E4) | 1 | 9,0 | 9,0 | hoja de datos | SG90: 9 g |
| Acople flexible 5 a 8 mm | 1 | 9,0 | 9,0 | hoja de datos | acople helicoidal de aluminio Ø19 x 25 |
| Bloque del rodamiento 608 (rodillo motriz) (impresa) | 2 | 4,3 | 8,5 | *estimado* | 6,6 cm³ x 1,24 g/cm³ x 52% de llenado |
| Embudo de la descarga de la cinta (impresa) | 1 | 6,2 | 6,2 | *estimado* | 5,0 cm³ x 1,24 g/cm³ x 100% de llenado |
| Guía lateral de la banda de monedas (impresa) | 2 | 3,0 | 6,0 | *estimado* | 2,4 cm³ x 1,24 g/cm³ x 100% de llenado |
| Abrazadera de la cámara cenital (impresa) | 1 | 5,3 | 5,3 | *estimado* | 4,3 cm³ x 1,24 g/cm³ x 100% de llenado |
| Tornillo M3 x 30 | 2 | 2,0 | 4,0 | *estimado* |  |
| Brida de servo SG90 (desvío y obturador) (impresa) | 2 | 1,9 | 3,7 | *estimado* | 1,5 cm³ x 1,24 g/cm³ x 100% de llenado |
| Infrarrojo de presencia | 1 | 3,0 | 3,0 | *estimado* | módulo FC-51 (PCB de 31 x 14 mm) |
| Taco de las platinas M18 (impresa) | 2 | 1,0 | 2,0 | *estimado* | 0,8 cm³ x 1,24 g/cm³ x 100% de llenado |
| Taco del poste de la compuerta E4 (impresa) | 1 | 2,0 | 2,0 | *estimado* | 1,6 cm³ x 1,24 g/cm³ x 100% de llenado |
| Aleta de la compuerta de desvío (E4) (impresa) | 1 | 1,9 | 1,9 | *estimado* | 1,5 cm³ x 1,24 g/cm³ x 100% de llenado |
| Tornillo M2 x 8 autorroscante (servos, placas) | 6 | 0,3 | 1,8 | *estimado* |  |
| Oreja de la bisagra de la compuerta (impresa) | 1 | 0,3 | 0,3 | *estimado* | 0,2 cm³ x 1,24 g/cm³ x 100% de llenado |
| **Subtotal** | | | **2.962,4** | | |

### Almacén: 0,23 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Almacén tipo revólver | 1 | 80,0 | 80,0 | *estimado* | solo los 6 tubos de acrílico Ø29 int / Ø33 ext x 58 mm: π·(16,5² - 14,5²)·58 = 11,2 cm³ x 1,19 = 13 g c/u (disco y placa: piezas impresas) |
| Placa fija del almacén (con el agujero) (impresa) | 1 | 36,8 | 36,8 | *estimado* | 57,1 cm³ x 1,24 g/cm³ x 52% de llenado |
| Motor del carrusel del almacén | 1 | 30,0 | 30,0 | hoja de datos | 28BYJ-48: ~30 g |
| Tornillo M5 x 10 cabeza Allen | 6 | 3,0 | 18,0 | *estimado* |  |
| Tuerca en T M5 (martillo) para 2020 | 6 | 2,0 | 12,0 | *estimado* |  |
| Disco del carrusel (6 agujeros y cubo) (impresa) | 1 | 11,7 | 11,7 | *estimado* | 18,2 cm³ x 1,24 g/cm³ x 52% de llenado |
| Servo del obturador del almacén | 1 | 9,0 | 9,0 | hoja de datos | SG90: 9 g |
| Placa del motor del carrusel (28BYJ-48) (impresa) | 1 | 7,7 | 7,7 | *estimado* | 11,9 cm³ x 1,24 g/cm³ x 52% de llenado |
| Embudo corto del almacén al vaso (impresa) | 1 | 7,4 | 7,4 | *estimado* | 6,0 cm³ x 1,24 g/cm³ x 100% de llenado |
| Tornillo M4 x 12 (o autorroscante para MDF) | 2 | 2,0 | 4,0 | *estimado* |  |
| Obturador del almacén (impresa) | 1 | 3,2 | 3,2 | *estimado* | 2,6 cm³ x 1,24 g/cm³ x 100% de llenado |
| Sensor Hall del carrusel | 1 | 3,0 | 3,0 | *estimado* | módulo 3144 + imán de neodimio de 6 mm |
| Tornillo M3 x 10 | 2 | 1,0 | 2,0 | *estimado* |  |
| Tuerca M4 | 2 | 0,8 | 1,6 | *estimado* |  |
| Portacables del servo del obturador (impresa) | 1 | 1,1 | 1,1 | *estimado* | 0,9 cm³ x 1,24 g/cm³ x 100% de llenado |
| Tornillo M2 x 8 autorroscante (servos, placas) | 1 | 0,3 | 0,3 | *estimado* |  |
| **Subtotal** | | | **227,9** | | |

### Cinta de vasos: 2,59 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Cama y placas laterales de la cinta de vasos (MDF) | 1 | 393,9 | 393,9 | *estimado* | malla del modelo: 374 x 81 x 20 mm |
| Perfil 2020: larguero de la mesa de vasos (340 mm) | 2 | 170,0 | 340,0 | hoja de datos | 340 mm x 0,50 kg/m |
| Motor de la cinta de vasos | 1 | 280,0 | 280,0 | hoja de datos | 17HS4401: 0,28 kg |
| Perfil 2020: pata de la mesa de vasos (88 mm) | 4 | 44,0 | 176,0 | hoja de datos | 88 mm x 0,50 kg/m |
| Escuadra 2020 de fundición | 9 | 14,0 | 126,0 | *estimado* |  |
| Bandeja de rechazo de vasos (impresa) | 1 | 124,0 | 124,0 | *estimado* | 100,0 cm³ x 1,24 g/cm³ x 100% de llenado |
| Banda de caucho de 75 mm (cerrada) | 1 | 122,2 | 122,2 | *estimado* | largo 2 x 400 + π x 22 = 870 mm x 75 mm x 1,5 mm |
| Rodamientos con brida KFL08 (x4) | 1 | 120,0 | 120,0 | hoja de datos | KFL08 de zamak: ~30 g c/u |
| Perfil 2020: poste de la cámara de vasos (190 mm) | 1 | 95,0 | 95,0 | hoja de datos | 190 mm x 0,50 kg/m |
| Rodillos Ø22 x 79 mm con su eje (x2) | 1 | 90,0 | 90,0 | *estimado* | igual que los de monedas pero de 79 mm: ~45 g por rodillo |
| Separadores M3 x 20 del motor (x4) y varillas guía de la prensa (x2) | 1 | 85,0 | 85,0 | *estimado* | varillas de acero Ø8 x 101 mm: 5,1 cm³ x 7,85 = 40 g c/u; separadores de latón ~1 g |
| Pie nivelador M6 Ø26 con contratuerca | 4 | 20,0 | 80,0 | *estimado* |  |
| Taco separador de la banda de vasos (impresa) | 7 | 11,2 | 78,5 | *estimado* | 17,4 cm³ x 1,24 g/cm³ x 52% de llenado |
| Cámara de vasos (silueta, ArUco y tapa) | 1 | 70,0 | 70,0 | *estimado* | webcam 720p con su cable |
| Servo del empujador de descarga | 1 | 55,0 | 55,0 | hoja de datos | MG996R: 55 g |
| Tornillo M5 x 8 ISO 7380 (escuadras) | 18 | 2,5 | 45,0 | *estimado* |  |
| Tuerca en T M5 (martillo) para 2020 | 21 | 2,0 | 42,0 | *estimado* |  |
| Perfil 2020: travesaño de la mesa de vasos (40 mm) | 2 | 20,0 | 40,0 | hoja de datos | 40 mm x 0,50 kg/m |
| Tornillo M3 x 10 | 30 | 1,0 | 30,0 | *estimado* |  |
| Paleta del empujador (impresa) | 1 | 22,1 | 22,1 | *estimado* | 34,3 cm³ x 1,24 g/cm³ x 52% de llenado |
| Orejas y bridas del MG996R de la prensa (impresa) | 1 | 21,0 | 21,0 | *estimado* | 16,9 cm³ x 1,24 g/cm³ x 100% de llenado |
| Pistón de la prensa (impresa) | 1 | 17,6 | 17,6 | *estimado* | 27,3 cm³ x 1,24 g/cm³ x 52% de llenado |
| Cabezal del escape de tapas (impresa) | 1 | 14,1 | 14,1 | *estimado* | 21,8 cm³ x 1,24 g/cm³ x 52% de llenado |
| Soporte de la bandeja de rechazo de vasos (impresa) | 1 | 14,0 | 14,0 | *estimado* | 11,3 cm³ x 1,24 g/cm³ x 100% de llenado |
| Tuerca M3 | 30 | 0,4 | 12,0 | *estimado* |  |
| Tornillo M4 x 12 (o autorroscante para MDF) | 6 | 2,0 | 12,0 | *estimado* |  |
| Tornillo M5 x 10 cabeza Allen | 3 | 3,0 | 9,0 | *estimado* |  |
| Acople flexible 5 a 8 mm | 1 | 9,0 | 9,0 | hoja de datos |  |
| Tornillo M3 x 30 | 4 | 2,0 | 8,0 | *estimado* |  |
| Leva excéntrica de la prensa (impresa) | 1 | 7,8 | 7,8 | *estimado* | 12,1 cm³ x 1,24 g/cm³ x 52% de llenado |
| Placa del NEMA 17 de la cinta de vasos (impresa) | 1 | 7,7 | 7,7 | *estimado* | 12,0 cm³ x 1,24 g/cm³ x 52% de llenado |
| Abrazadera del tubo con el servo de tapas (impresa) | 1 | 7,3 | 7,3 | *estimado* | 11,3 cm³ x 1,24 g/cm³ x 52% de llenado |
| Bloque de las varillas guía de la prensa (impresa) | 1 | 6,6 | 6,6 | *estimado* | 10,3 cm³ x 1,24 g/cm³ x 52% de llenado |
| Buje guía del pistón (impresa) | 1 | 4,5 | 4,5 | *estimado* | 7,0 cm³ x 1,24 g/cm³ x 52% de llenado |
| Placa de la cámara de vasos (sobre su poste) (impresa) | 1 | 4,1 | 4,1 | *estimado* | 3,3 cm³ x 1,24 g/cm³ x 100% de llenado |
| Manivela del empujador (impresa) | 1 | 3,7 | 3,7 | *estimado* | 3,0 cm³ x 1,24 g/cm³ x 100% de llenado |
| Tornillo M2 x 8 autorroscante (servos, placas) | 11 | 0,3 | 3,3 | *estimado* |  |
| Tuerca M4 | 4 | 0,8 | 3,2 | *estimado* |  |
| Balancín y dedos del escape de tapas (impresa) | 1 | 2,6 | 2,6 | *estimado* | 2,1 cm³ x 1,24 g/cm³ x 100% de llenado |
| Sensor del interior del vaso | 1 | 2,0 | 2,0 | *estimado* | módulo GY-VL53L0XV2 |
| Cortina de seguridad | 1 | 2,0 | 2,0 | *estimado* | módulo GY-VL53L0XV2 |
| Porta-sensor del VL53L0X del interior (impresa) | 1 | 1,4 | 1,4 | *estimado* | 1,1 cm³ x 1,24 g/cm³ x 100% de llenado |
| **Subtotal** | | | **2.587,6** | | |

### Pórtico: 1,35 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Perfil 2020: columna del pórtico (398 mm) | 2 | 199,0 | 398,0 | hoja de datos | 398 mm x 0,50 kg/m |
| Barras cuadradas de aluminio de 10-12 mm (colgantes y marco del panel) | 1 | 243,0 | 243,0 | *estimado* | marco del panel 310 + 310 + 20 mm de 10 x 10 (64 cm³ de malla) + colgantes del tubo de tapas y de la prensa (~26 cm³) |
| Placa de aluminio de la prensa (70 x 165 x 8 mm) | 1 | 172,5 | 172,5 | *estimado* | malla del modelo |
| Perfil 2020: viga del pórtico (a 40 cm) (330 mm) | 1 | 165,0 | 165,0 | hoja de datos | 330 mm x 0,50 kg/m |
| Panel de luz de la cámara de vasos | 1 | 150,0 | 150,0 | *estimado* | acrílico opalino 330 x 110 x 3 mm = 109 cm³ x 1,19 = 130 g + tira LED de 1 m (~20 g) |
| Tubo vertical de tapas | 1 | 75,0 | 75,0 | *estimado* | tubo de acrílico Ø78 int / Ø86 ext x 61 mm: π·(43² - 39²)·61 = 62,8 cm³ x 1,19 |
| Servo de la prensa | 1 | 55,0 | 55,0 | hoja de datos | MG996R: 55 g |
| Pie nivelador M6 Ø26 con contratuerca | 2 | 20,0 | 40,0 | *estimado* |  |
| Escuadra 2020 de fundición | 2 | 14,0 | 28,0 | *estimado* |  |
| Tornillo M5 x 8 ISO 7380 (escuadras) | 4 | 2,5 | 10,0 | *estimado* |  |
| Servo del escape de tapas | 1 | 9,0 | 9,0 | hoja de datos | SG90: 9 g |
| Tuerca en T M5 (martillo) para 2020 | 4 | 2,0 | 8,0 | *estimado* |  |
| **Subtotal** | | | **1.353,5** | | |

### Canaleta y muelle: 1,08 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Perfil 2020: poste alto de la canaleta (163 mm) | 2 | 81,5 | 163,0 | hoja de datos | 163 mm x 0,50 kg/m |
| Perfil 2020: poste bajo de la canaleta (137 mm) | 2 | 68,5 | 137,0 | hoja de datos | 137 mm x 0,50 kg/m |
| Guía en V del muelle (tramo recto + V) (impresa) | 2 | 57,8 | 115,6 | *estimado* | 46,6 cm³ x 1,24 g/cm³ x 100% de llenado |
| Escuadra 2020 de fundición | 8 | 14,0 | 112,0 | *estimado* |  |
| Perfil 2020: travesaño de la canaleta (105 mm) | 2 | 52,5 | 105,0 | hoja de datos | 105 mm x 0,50 kg/m |
| Pie nivelador M6 Ø26 con contratuerca | 5 | 20,0 | 100,0 | *estimado* |  |
| Perfil 2020: larguero de la canaleta (78 mm) | 2 | 39,0 | 78,0 | hoja de datos | 78 mm x 0,50 kg/m |
| Canaleta de entrega | 1 | 55,0 | 55,0 | *estimado* | 2 varillas de acero Ø4 x 284 mm: π·2²·284 = 3,6 cm³ x 7,85 = 28 g c/u, + cinta de PTFE |
| Tornillo M5 x 8 ISO 7380 (escuadras) | 16 | 2,5 | 40,0 | *estimado* |  |
| Tuerca en T M5 (martillo) para 2020 | 16 | 2,0 | 32,0 | *estimado* |  |
| Tope del muelle con refuerzo (impresa) | 2 | 14,1 | 28,3 | *estimado* | 11,4 cm³ x 1,24 g/cm³ x 100% de llenado |
| Cabezal del riel de la canaleta (impresa) | 4 | 6,1 | 24,5 | *estimado* | 9,5 cm³ x 1,24 g/cm³ x 52% de llenado |
| Tornillo M4 x 12 (o autorroscante para MDF) | 12 | 2,0 | 24,0 | *estimado* |  |
| Perfil 2020: poste del escape de la canaleta (43 mm) | 1 | 21,5 | 21,5 | hoja de datos | 43 mm x 0,50 kg/m |
| Tornillo M5 x 10 cabeza Allen | 5 | 3,0 | 15,0 | *estimado* |  |
| Servo del escape de la canaleta | 1 | 9,0 | 9,0 | hoja de datos | SG90: 9 g |
| Espuma de los topes y cinta de PTFE | 1 | 8,0 | 8,0 | *estimado* |  |
| Soporte del SG90 del escape (impresa) | 1 | 6,6 | 6,6 | *estimado* | 5,3 cm³ x 1,24 g/cm³ x 100% de llenado |
| Balancín de dos dedos del escape (impresa) | 1 | 4,5 | 4,5 | *estimado* | 3,6 cm³ x 1,24 g/cm³ x 100% de llenado |
| Tornillo M3 x 10 | 4 | 1,0 | 4,0 | *estimado* |  |
| Tornillo M2 x 8 autorroscante (servos, placas) | 3 | 0,3 | 0,9 | *estimado* |  |
| **Subtotal** | | | **1.083,8** | | |

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

### Caja de control: 2,18 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Gabinete de acrílico 360 x 240 x 80 mm, 3 mm (con tapa) | 1 | 955,6 | 955,6 | *estimado* | piso y tapa 2 x 360 x 240 + paredes 2 x 360 x 80 + 2 x 234 x 80 = 0,268 m² x 3 mm |
| Fuente de 12 V | 1 | 500,0 | 500,0 | *estimado* | fuente conmutada 12 V 10 A de caja metálica (genérica ~0,5 kg; la LRS-150-12 original pesa 0,6 kg) |
| Cables de la caja y de campo (18 AWG, dupont, JST) | 1 | 250,0 | 250,0 | *estimado* | ~15 m de cable de 18-24 AWG entre caja, planta y sensores |
| Bornera X2 (carril DIN) | 1 | 125,0 | 125,0 | *estimado* | 16 bornes de 2,5 mm² (~6 g c/u) + riel DIN de 110 mm (~25 g) |
| Canaletas, prensaestopas y ventilador | 1 | 70,0 | 70,0 | *estimado* | 1 m de canaleta ranurada 25 x 30 (~40 g) + 8 prensaestopas (~3 g c/u) + ventilador 4010 (~6 g) |
| Regulador de 6 V (servos) | 1 | 60,0 | 60,0 | *estimado* | XL4016 con sus dos disipadores |
| Hub USB con fuente | 1 | 45,0 | 45,0 | *estimado* | hub de 4 puertos con su cable (el adaptador de pared no va en la caja) |
| Portafusibles | 1 | 40,0 | 40,0 | *estimado* | portafusibles de 4 vías con fusibles de cuchilla |
| ESP32 fijo (estación) | 1 | 35,0 | 35,0 | *estimado* | ESP32 DevKit 38 pines (~10 g) + placa de expansión GVS (~25 g) |
| Drivers de las dos cintas (M y V) | 2 | 12,0 | 24,0 | *estimado* | A4988 con disipador (~3 g) + su mitad de la placa perforada, por driver |
| Entrada de red con interruptor | 1 | 20,0 | 20,0 | *estimado* | conector IEC C14 con interruptor y portafusible |
| Regulador de 5 V | 1 | 12,0 | 12,0 | *estimado* | módulo LM2596 |
| Controlador de servos | 1 | 9,0 | 9,0 | hoja de datos | PCA9685 de 16 canales: ~9 g |
| Tornillo M4 x 12 (o autorroscante para MDF) | 4 | 2,0 | 8,0 | *estimado* |  |
| Taco de esquina de la tapa de la caja (impresa) | 4 | 1,9 | 7,5 | *estimado* | 2,9 cm³ x 1,24 g/cm³ x 52% de llenado |
| Driver del carrusel | 1 | 6,0 | 6,0 | *estimado* | placa ULN2003 del kit del 28BYJ-48 |
| Optoacopladores | 1 | 5,0 | 5,0 | *estimado* | placa de 2 PC817 |
| Reparto del bus I2C 1 | 1 | 5,0 | 5,0 | *estimado* | placa perforada pequeña con 2 conectores |
| Tuerca M4 | 4 | 0,8 | 3,2 | *estimado* |  |
| **Subtotal** | | | **2.180,2** | | |

### Pista y base: 2,47 kg

| Qué | Cant. | c/u (g) | Total (g) | Fuente | Cómo |
|---|---:|---:|---:|---|---|
| Tablero MDF de 9 mm bajo la planta (600 x 450 mm) | 1 | 1.579,5 | 1.579,5 | *estimado* | huella de las mesas, el pórtico y la canaleta en el modelo: ~0,60 x 0,45 m x 9 mm |
| Lámina blanca de la pista (cartón/vinilo de 1 mm, 160 mm de ancho) | 1 | 392,5 | 392,5 | *estimado* | malla del modelo: 0,56 m² x 1 mm |
| 3 muros-obstáculo de bloques de juguete (100 x 30 x 80 mm) | 1 | 360,0 | 360,0 | *estimado* | bloques de ABS huecos: ~120 g por muro |
| Bandera de la meta (mástil de aluminio Ø6 x 250 y base de Ø60) | 1 | 80,0 | 80,0 | *estimado* |  |
| Pista con 3 obstáculos y meta | 1 | 60,0 | 60,0 | hoja de datos | rollo de cinta aislante 3M de 18 m (la lámina y los muros van en `otros`) |
| **Subtotal** | | | **2.472,0** | | |
