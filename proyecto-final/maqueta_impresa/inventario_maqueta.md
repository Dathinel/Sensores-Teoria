# Inventario geométrico de la maqueta (planta) — proyecto final

> **Qué vale de este inventario (nota del 2026-10-25).** Es la foto de la simulación y del visor del 2026-10-24 por
> la mañana, de antes de la maqueta impresa. Valen sus **medidas funcionales** (estaciones, alturas de las bandas,
> carrusel, tolva, canaleta, sensores, cámaras, §18): son las que la maqueta impresa no mueve. Los **soportes** que
> describe (perfil 2020, escuadras, pies niveladores, poste E4, pletina y varillas M5, placas de aluminio y acrílico,
> tablero MDF) son del diseño anterior: en la maqueta impresa todo es PLA, con tubos 16 × 16 y nodos
> (`estructura.py`; la viga del pórtico va en y −40,5, z 400, con las columnas P1 en x −50 y P2 en x 315). Las citas
> `precios.yaml:NNN` son de la versión de ese archivo del 2026-10-24 por la mañana y ya no apuntan a lo que dicen.
> Lo que la maqueta impresa cambió de las medidas de aquí (y el visor y la simulación tienen que seguir) está en §20.

Rutas relativas a `D:\cosas uni\Micros\Micros teoria\github\Sensores-Teoria\proyecto-final`.
Solo lectura. Los números "(calc.)" son derivados por mí de las fórmulas citadas; los demás están
escritos tal cual en la fuente. Las posiciones de `sim/geometria.py` se verificaron ejecutando
`geometria_completa()` con `entorno/Scripts/python.exe` (sin escribir nada en el repo).

---

## 0. Marco de referencia

| Concepto | Valor | Fuente |
|---|---|---|
| Unidades | metros en todo `sim/` y en el visor; mm en `config/*.yaml` | sim/geometria.py:189 (`"unidades": "metros"`), app/visor3d/piezas/base.js:3-7 |
| Plano z = 0 | el PISO (`plane.urdf`) | sim/mundo.py:363 |
| Ejes | x a lo largo de las cintas, y a lo ancho, z arriba | app/visor3d/piezas/base.js:4, sim/urdf/*.urdf |
| Lado operador | −y (canaleta, carro, cámara de vasos, cortina) | sim/geometria.py:110-111, sim/mundo.py:688 |
| Lado trasero | +y (pórtico, caja de control, bandeja de rechazo de monedas) | app/visor3d/visor.js:1236-1240, 3036-3038 |
| Origen | arbitrario: no coincide con ninguna pieza; la cinta de monedas tiene su base en (0,01; 0; 0,43) | sim/mundo.py:86 |
| Gravedad | (0, 0, −9,81) | sim/mundo.py:361 |
| Conversión del visor | `P(x,y,z)` = Three `(x, z, −y)` (Three tiene Y arriba) | base.js:37; visor.js:42-43 (`V`, `Vxyz`) |
| Ángulos del carrusel | grados, desde +x hacia +y | sim/geometria.py:198 |

Altura de superficie de ambas cintas sobre su mesa: bancada 20 mm + banda 2 mm = **22 mm**
(sim/mundo.py:60-62).

---

## 1. Cinta de monedas y su mesa

### 1.1 Estaciones (centro de casilla, a ras de la banda)
Fórmula: x = 0,01 − 0,06 + i·0,04; y = 0; z = 0,43 + 0,022 (sim/mundo.py:175-181, 38, 64, 83, 86).

| Estación | x | y | z | Fuente |
|---|---|---|---|---|
| E1 presencia (i=0) | −0,05 | 0 | 0,452 | mundo.py:48, 181 |
| E2 material (i=1) | −0,01 | 0 | 0,452 | mundo.py:49 |
| E3 visión (i=2) | 0,03 | 0 | 0,452 | mundo.py:50 |
| E4 descarga (i=3) | 0,07 | 0 | 0,452 | mundo.py:51 |

Paso de casilla 40 mm (mundo.py:38; parametros.yaml:25).

### 1.2 Elementos

| Elemento | Def. | Posición (mundo) | Medidas (mm) | Orientación | Material hoy | Se sujeta a |
|---|---|---|---|---|---|---|
| Base URDF de la cinta | mundo.py:86, 365-369 | origen del cuerpo (0,01; 0; 0,43) | — | sin giro | — | base fija |
| Banda (visor) | visor.js:770, 862 | x −0,11 a 0,09 (calc.), y 0, z centro 0,451 | 200 × 55 × 2 | a lo largo de x | caucho negro mate (comprada) | rodillos |
| Banda (URDF) | cinta_monedas.urdf:53-61 | centro (−0,01; 0; 0,451) (calc.) | 200 × 55 × 2 | — | — | — |
| Bancada (visor, 3 tramos por las ventanas) | visor.js:755-761 | x [−0,097;−0,068], [−0,032;−0,028], [0,008;0,077] (calc.); z centro 0,44 | ancho 61 × alto 20 | — | sin material dicho (color "bancada") | rieles 2020 |
| Bancada (URDF, maciza) | cinta_monedas.urdf:33-41 | centro (−0,01; 0; 0,44) (calc.) | 200 × 61 × 20 | — | — | — |
| Ventanas bajo E1 y E2 | visor.js:755, 892 | x −0,05 y −0,01, ±18 mm | 36 mm de largo | — | hueco | — |
| Separadores | visor.js:794-799, 891 | cada 40 mm desde x0 = −0,11 | 3 × 55 × **4** | — | (sin material) | banda |
| Guías laterales de la banda | visor.js:1024-1027 | y ±0,0285, z centro 0,455 (calc.) | 200 × 2 × 6 | a lo largo de x | impreso | rieles (precios.yaml:135) |
| Rodillo motriz (cola) | visor.js:873-878; linea_monedas.js:129-163 | eje en (−0,11; 0; 0,441) | Ø22 × 59 (largo ancho+4), eje Ø8 | eje según y | tubo de aluminio Ø22 con goma; eje acero | 2 cojinetes 608 |
| Rodillo tensor (cabeza) | ídem | eje en (0,09; 0; 0,441) | Ø22 × 59 | eje según y | aluminio | 2 cojinetes tensores |
| Cojinetes 608ZZ (4 bloques) | visor.js:905-916; linea_monedas.js:174-200 | x −0,11 y 0,09; y ±0,0505 (yRiel+0,01); z 0,441 | bloque 30 × 9 × 22; 608 = 8×22×7 | — | impreso + rodamiento comprado | cara del riel 2020 con 2 M4 + tuerca T |
| Rieles laterales 2020 (2) | visor.js:899-902 | de x −0,145 a 0,106, y ±0,0405, eje z 0,440 | 251 × 20 × 20 | a lo largo de x | perfil 2020 | patas |
| Patas 2020 (3) | visor.js:924-937 | (−0,145; −0,0405), (−0,145; +0,0405), (0,03; +0,0405); de z 0,012 a 0,430 | 418 largo | vertical | 2020 | pies niveladores |
| Taco sobre la viga (4.º apoyo) | visor.js:951, 1258-1260 | (0,03; −0,0405), de z 0,41 a 0,43 | 20 × 20 × 20 | — | impreso | viga del pórtico |
| Travesaño de la cola | visor.js:938 | x −0,145, y −0,0305 a 0,0305, z 0,05 | 61 | según y | 2020 | patas de la cola |
| Travesaño lateral | visor.js:939 | y +0,0405, x −0,135 a 0,02, z 0,05 | 155 | según x | 2020 | patas +y |
| Escuadras (4) | visor.js:941-947 | (−0,145; −0,0305), (−0,145; 0,0305), (−0,135; 0,0405), (0,02; 0,0405), z 0,06 | 20×20×20 | — | fundición de aluminio (comprada) | travesaño–pata |
| Retorno de la banda: rodillos A, B, C | visor.js:962-978 | A (−0,113; 0,344), B (0,011; 0,344), C (0,065; 0,4188) (x; z), y 0 | Ø22 × 59, eje Ø8 | eje según y | aluminio + 608 | 2 placas colgantes cada uno |
| Placas colgantes de A, B, C (6) | visor.js:968-971 | y ±0,031 (ancho/2+3,5 mm); de z 0,430 a z_eje−0,009 | 14 × 3 × 95 (A, B) y 14 × 3 × 20,8 (C) (calc.) | vertical | impreso | cara inferior de los rieles |
| NEMA 17 (motor) | visor.js:1168-1195 | cara de montaje en (−0,11; +0,097; 0,441); cuerpo hasta y 0,137 (calc.) | 42,3 × 42,3 × 40 (electronica.js:1145) | eje hacia −y | comprado | jaula impresa |
| Jaula del NEMA 17 | visor.js:1175; linea_monedas.js:235-253 | sobre el motor, distancia a la cara del riel 46,5 mm (calc.: 0,097−0,0505) | placa 50×50×4, paredes 4 mm, alas 14×20×4 | — | impreso (PETG según comentario) | riel +y con 2 M5 + tuercas T |
| Acople flexible | visor.js:1178-1180; linea_monedas.js:203-225 | (−0,11; 0,073; 0,441) | Ø19 × 25 | eje según y | aluminio (comprado) | ejes motor/rodillo |

Largo de la banda: x0 = E1 − 1,5·paso, x1 = E4 + paso/2 (visor.js:862) → la banda arranca
una casilla antes de E1.

Mesa de monedas: **no** usa `crearMesaPerfil`; está armada a mano (visor.js:917-951). Su alto
(z punta de patas) = zs − 0,022 = 0,430 (visor.js:924), que coincide con `ALTURA_MESA_MONEDAS = 0.43`
(mundo.py:83).

---

## 2. Sensores de la cinta de monedas y sus soportes

| Sensor | Def. | Posición (mundo) | Mira | Medidas del módulo | Soporte | Fuente medidas |
|---|---|---|---|---|---|---|
| FC-51 presencia (E1) | sensores_sim.py:313-323; geometria.py:63-64; visor.js:4391-4455 | rayo de (−0,05; 0; 0,502) a (−0,05; 0; 0,452): **50 mm sobre la banda** | −z | placa 32 × 14 × 1,6 (sensores.js:226) | bandera impresa en L 3 mm + columna impresa 10×10 con pie 20×20×3 sobre la cara de arriba del riel −y (z 0,450), columna en x −0,07 (E1 − 20 mm), y −0,0405; 2 M5 + tuercas T | visor.js:4414-4432 |
| Capacitivo LJC18A3 (bajo E1) | geometria.py:80-84 | cara activa (−0,05; 0; 0,4495) = 2,5 mm bajo la superficie, 0,5 mm bajo la banda | +z | M18, 68 mm (cabeza 6 + rosca 50 + cola 12) (sensores.js:328) | platina M18 | — |
| Inductivo LJ18A3-8 (bajo E2) | geometria.py:80-84 | cara activa (−0,01; 0; 0,4495) | +z | M18, 60 mm (cabeza 8 + rosca 42 + cola 10) (sensores.js:334) | platina M18 | — |
| Platinas M18 (2) | visor.js:883-893; linea_monedas.js:263-289 | centro del agujero, cara de arriba en z 0,436 (= 0,452 − 0,0025 − 0,0125 − 0,001), x −0,05 y −0,01 | 36 × 60 (ancho = 2·(yRiel−0,01) = 61 → forma 60) × 3, agujero Ø18,5, 2 escuadras de alu 15×12×2 por lado, contratuerca M18 24 e/c × 4 | horizontal | **aluminio** | cara interior de los rieles 2020 |
| Webcam cenital 1080p + anillo (E3) | geometria.py:103-107; visor.js:4512-4556 | vidrio de la lente en (0,03; 0; 0,602): **150 mm sobre la banda**; centro de la carcasa 27,3 mm más arriba (z 0,6293 calc.) | −z | carcasa 42 × 42 × 20, anillo LED 60/40 mm (sensores.js:342-344) | ver poste cenital | — |
| Poste cenital | visor.js:4531-4548; linea_monedas.js:591-605 | poste vertical en (0,03; 0,0605), de z 0,430 (cara inferior del riel) a 0,6923 (calc.); brazo de y 0 a 0,0605 a z ≈ 0,682 (calc.) | brazo = 60,5 mm (calc.); alto = 236,3 mm (calc.: 0,6663 − 0,430) | — | modelado como **caja** de alu 20×20 (no perfil real); abrazadera impresa 30 × 24 × 6 con tornillo 1/4" | costado del riel +y con escuadra de alu 2 alas 20×18×3 + 2 M5 (visor.js:4540-4546) |

---

## 3. Compuerta de desvío E4 y canales

| Elemento | Def. | Posición | Medidas (mm) | Material | Sujeción |
|---|---|---|---|---|---|
| Embudo de descarga | visor.js:1040-1043 | eje x = 0,105 (x1 + 15 mm), y 0; boca z 0,446 (Ø40), salida z 0,420 (Ø20) | alto 26 | impreso (precios.yaml:142) | brazo de alu Ø4 al riel −y (visor.js:1087) |
| Pivote de la compuerta | visor.js:1044-1046 | (0,105; 0; 0,418) | — | — | — |
| Aleta de desvío | linea_monedas.js:299-317 | cuelga del pivote; reposo 0,5 rad hacia rechazo (visor.js:1046) | 18 × 2 × 16, barril Ø5 | impreso (rojo) | pasador Ø3 + cubo al cuerno del SG90 |
| SG90 desvío | visor.js:1054-1056 | (0,138; 0; 0,418), eje del servo = eje de la bisagra (−x) | 22,5 × 11,8 × 22,7 (electronica.js:1203) | comprado | brida impresa (linea_monedas.js:340-355) sobre taco |
| Poste E4 | visor.js:1097-1103 | (0,1395; 0), de z 0,012 a 0,38855 (calc.) | 2020, 376,55 (calc.) / 377 (precios.yaml:198) | 2020 + pie nivelador | piso |
| Taco del poste | visor.js:1103 | z 0,38655 centro | 20 × 20 × 4 | impreso | punta del poste |
| Oreja de la bisagra | visor.js:1104-1105; linea_monedas.js:321-329 | (0,0925; 0; 0,418) | 3 × 7 × 8 | impreso | embudo |
| Canal A (al carrusel) | visor.js:1066-1079 | de (0,105; −0,0095; 0,40008) a 12 mm antes y 6 mm sobre la boca de carga (0,1035; −0,03842; 0,340) | U 30 × 10, largo ≈ 66,7 (calc.) | impreso (precios.yaml:143) | — |
| Embudo de carga | visor.js:1080-1082 | de z 0,344 (r 18) a z 0,331 (r 13), en el punto de carga | — | (sin material) | — |
| Canal B (a rechazo) | visor.js:1083-1086 | de (0,105; 0,0095; 0,40008) a (0,10; 0,10; 0,05) | U 30 × 12, largo ≈ 361,6 (calc.) | impreso (precios.yaml:145) | — |

Boca de los canales: z = 0,418 − 0,017·cos 0,5 − 0,003 = 0,40008 (visor.js:1071).
Tiempo de caída cinta → tubo: 400 ms; canal "~72 grados" (parametros.yaml:443-455).

---

## 4. Almacén tipo revólver (carrusel), obturador y tolva

### 4.1 Geometría base (sim/mundo.py)

| Dato | Valor | Fuente |
|---|---|---|
| Radio del carrusel (eje → tubo) | 33 mm | mundo.py:114 |
| Radio interior de tubo | 14,5 mm (Ø29) | mundo.py:111 |
| Alto de tubo | 58 mm | mundo.py:112 |
| Fondo de los tubos (`TUBO_BASE_Z`) | z 0,270 | mundo.py:113 |
| Boca de los tubos | z 0,328 | geometria.py:211 |
| Grosor por moneda en la pila | 2,2 mm | mundo.py:115 |
| Ángulo de carga / agujero | 90° / 300° | mundo.py:211-212 |
| Centro del carrusel | (0,1035; −0,07142) | mundo.py:215-222 (ejecutado) |
| Punto de carga | (0,1035; −0,03842) | mundo.py:225-232 |
| Salida de la tolva / agujero | (0,12; −0,10) = vaso de llenado | mundo.py:235-238 |
| Capacidad por tubo | 25 monedas | parametros.yaml:127 |

Tubos en reposo (centro del fondo, z 0,27; ángulo 90° + k·60°, mundo.py:328-338):

| Tubo | Ángulo | x | y |
|---|---|---|---|
| $50 | 90° | 0,1035 | −0,03842 |
| $100 | 150° | 0,07492 | −0,05492 |
| $200 | 210° | 0,07492 | −0,08792 |
| $500 | 270° | 0,1035 | −0,10442 |
| $1000 | 330° | 0,13208 | −0,08792 |
| otras | 30° | 0,13208 | −0,05492 |

### 4.2 Piezas (visor)

| Elemento | Def. | Posición | Medidas (mm) | Material hoy | Sujeción |
|---|---|---|---|---|---|
| Placa fija | visor.js:1531-1541; linea_monedas.js:401-424 | centro (0,1035; −0,07142; 0,268), de z 0,266 a 0,270 | Ø116 × 4, agujero Ø29 en el vaso de llenado, alojamiento 608 Ø28 × 6 | **acrílico oscuro** (visor) | 2 varillas M5 |
| Varillas M5 de la placa (2) | visor.js:1543-1547 | a R 56 mm, 30° y 150° del centro: (0,15200; −0,04342) y (0,05500; −0,04342) (calc.); de z 0,390 a 0,264 | Ø5 | acero | viga del pórtico |
| Disco del carrusel | visor.js:1686-1691; linea_monedas.js:432-466 | z 0,328 a 0,331 | Ø104 × 3, 6 agujeros Ø29, cubo Ø24/Ø14 | **acrílico transparente** | eje Ø8 |
| Tubos (6) | visor.js:1710-1741; linea_monedas.js:472-516 | de z 0,2705 a 0,328 (0,5 mm sobre la placa, pegados a tope bajo el disco) | Ø29 int, pared 1,5 (Ø32 ext), alto 54,5 + 3 | **policarbonato** (visor) | disco |
| Eje del carrusel | visor.js:1692-1693 | de z 0,262 a z_acople 0,3475 (calc.) | Ø8 | acero | 608 de la placa fija + acople |
| Acople rígido | visor.js:1695-1696 | z 0,3475 (calc.: 0,357 − 0,0015 − 0,008) | Ø12 × 16 | aluminio | eje motor–eje carrusel |
| 28BYJ-48 | visor.js:1749-1751 | (0,0955; −0,07142; 0,357) (cuerpo corrido 8 mm en −x, eje coaxial) | Ø28 × 19, pestañas 42 (electronica.js:1177) | comprado | placa impresa |
| Placa del motor | visor.js:1752-1753; linea_monedas.js:565-580 | eje en (0,1035; −0,07142), cara de arriba z 0,357 | 42 × 56 × 5 | impreso | 2 varillas M5 |
| Varillas M5 del motor (2) | visor.js:1755-1757 | (0,1095; −0,07142 ± 0,022), de z 0,347 a 0,387 | Ø5 | acero | pletina |
| Pletina | visor.js:1758-1759 | x 0,1095, y de −0,09942 a −0,035, z 0,3885 | 20 × 64,4 × 3 | aluminio | viga del pórtico |
| Iman N35 | visor.js:1690 | R + 15 = 48 mm a 0°, sobre el disco | 6 × 3 | comprado | disco |
| Hall KY-003 | geometria.py:99-102; visor.js:4656-4688 | cara del A3144 en (0,1515; −0,07142; 0,338), 4 mm sobre el imán | placa 18,5 × 15 × 1,6 (sensores.js:458) | comprado | taco impreso 6×6×5 + varilla Ø4 a la viga (taco en la viga 12×20×6, corrido 8 mm en x) |
| Obturador (aleta) | visor.js:1552-1564; linea_monedas.js:526-557 | bisagra 20 mm afuera del agujero (dirección 300°) y 4 mm bajo él (z ≈ 0,262) | aleta Ø34 × 2 + sello | impreso | pasador Ø3 al SG90 |
| SG90 obturador | visor.js:1561-1568 | 47 mm de la bisagra sobre su eje | 22,5 × 11,8 × 22,7 | comprado | brida + listón impreso 8 × 4 + taco 8×8 al borde de la placa fija |
| Tolva al vaso | visor.js:1557; geometria.py:212 | eje (0,12; −0,10); boca z 0,262 (r 19), salida z 0,230 (r **14** en visor) | alto 32 | impreso (precios.yaml:152) | — |

---

## 5. Cinta de vasos y su mesa

### 5.1 Estaciones
x = 0,20 − 0,16 + i·0,08; y = −0,10; z = 0,10 + 0,022 (mundo.py:184-186, 43, 65, 82, 91).

| Estación | x | y | z (banda) |
|---|---|---|---|
| Verificación (0) | 0,04 | −0,10 | 0,122 |
| Llenado (1) | 0,12 | −0,10 | 0,122 |
| Tapa (2) | 0,20 | −0,10 | 0,122 |
| Prensa (3) | 0,28 | −0,10 | 0,122 |
| Descarga (4) | 0,36 | −0,10 | 0,122 |

Paso 80 mm (mundo.py:43; parametros.yaml:53). Vaso 62 × 90, pestaña 8 (boca Ø78) (parametros.yaml:40-69).

### 5.2 Elementos

| Elemento | Def. | Posición | Medidas (mm) | Material | Sujeción |
|---|---|---|---|---|---|
| Banda | visor.js:1208, 1212 | x 0,0 a 0,40; y −0,10; z 0,121 | 400 × 75 × 2 | caucho (comprada) | rodillos |
| Bancada (visor) | visor.js:755-761 | x 0,013 a 0,387, z centro 0,11 | 374 × 81 × 20 | sin material en visor; peso.md:203 dice MDF | placas laterales |
| Bancada (URDF) | cinta_vasos.urdf:116-124 | centro (0,20; −0,10; 0,11) | 400 × 80 × 20 | — | — |
| Separadores (6 visibles + 1) | visor.js:794-799, 1212 | cada 80 mm desde x 0,0 | 3 × 75 × 15 | — | banda |
| Tacos de casilla (7) | visor.js:1215-1221; linea_vasos.js:189-201 | en cada separador | ~47 × 75 × 10 (alto 10 en visor; precios.yaml:155 dice 15) | impreso | separador |
| Rodillos | visor.js:774-792 | ejes en x 0,0 y 0,40, z 0,111 | Ø22 × 79 | aluminio | rodamientos |
| Placas laterales del bastidor (2) | visor.js:1224-1228 | y −0,1425 y −0,0575, x −0,015 a 0,415, z centro 0,103 | 430 × 4 × 34 | **aluminio** | mesa |
| Mesa 2020 (crearMesaPerfil) | visor.js:1229; estructura.js:282-329 | patas en x 0,02 / 0,38 × y −0,13 / −0,07; de z 0,012 a 0,100 | patas 88; largueros (x) 340 a z 0,07; travesaños (y) 40 a z 0,05 | 2020 | 4 pies niveladores |
| Escuadras de la mesa (8) | estructura.js:298-321 | largueros: (0,03 / 0,37; −0,13 / −0,07; z 0,08); travesaños: (0,02 / 0,38; −0,12 / −0,08; z 0,06) | 20×20×20 | fundición | — |
| NEMA 17 de la cinta + placa | visor.js:1492-1501; linea_vasos.js:488-514 | origen (0,0; −0,1445; 0,111); cara del motor en y −0,1785; cuerpo hasta y ≈ −0,2185 | placa 48 × 5 × 48 + 4 separadores M5 de 29 mm; rodamiento con brida KFL08; acople Ø19 × 20 | motor comprado; placa impresa | placa lateral −y |
| Bandeja de rechazo de vasos | mundo.py:241-246; visor.js:1450-1465 | piso, centro (0,47; −0,10; 0,004) | visor 95,8 × 115,8 piso + paredes de 60 | impresa (precios.yaml:169) | apoyada en el piso |
| Labio inclinado | visor.js:1462-1463 | (0,45; −0,10; 0,078), giro −0,9 rad | 50 × 75 × 3 | — | (sin sujeción dibujada) |

---

## 6. Escape de tapas y su tubo

| Elemento | Def. | Posición | Medidas (mm) | Material | Sujeción |
|---|---|---|---|---|---|
| Tubo de tapas (cabezal + tubo) | visor.js:1299-1325; linea_vasos.js:216-295 | eje (0,20; −0,10); cara de abajo del cabezal z 0,225 (13 mm sobre la boca del vaso, 0,212) | cabezal Ø92 × 16 (r_int 41, r_cab 46); tubo Ø82 int / Ø86 ext, alto total 75, tubo 61 desde z+14 | cabezal impreso, tubo acrílico | colgante 12 mm |
| Abrazaderas | linea_vasos.js:234-235 | sup. a z 0,292–0,300; servo a z 0,251–0,261 | anillo de 4 mm | sup. aluminio, la del servo impresa | colgante (M3) |
| SG90 de tapas (invertido) | linea_vasos.js:253-257 | (0,20; −0,158; 0,2545) (calc.: ys −58, zS 29,5) | SG90 | comprado | placa impresa con ventana |
| Dedos A y B | linea_vasos.js:269-289 | x ±12 mm; A z 3,5–6,5, B z 10,1–12,5 sobre el cabezal | 6 mm de ancho, carrera ±14,2° | impreso | ranuras del cabezal |
| Colgante 12 mm | visor.js:1314-1317 | de la viga (y −0,045, z 0,39) a y −0,0455 y abajo hasta z 0,251 | 12 × 12, ≈ 139 de alto (calc.) | barra cuadrada de aluminio (peso.md:252) | viga del pórtico |
| Pila de tapas | visor.js:1306-1307 | asiento de la 1.ª en z 0,2315 (calc.: 0,225 + 6,5 mm), paso 6,2 | 10 tapas Ø78 | — | — |

---

## 7. Prensa

| Elemento | Def. | Posición | Medidas (mm) | Material | Sujeción |
|---|---|---|---|---|---|
| Pistón (cara de abajo del plato, arriba) | visor.js:1363-1373 | (0,28; −0,10; 0,229) (12 mm sobre la tapa) | plato Ø62 × 6 + neopreno 0,5; carrera 13 (exc 6,5) | plato aluminio; vástago acero Ø8 | buje |
| Eje del servo / leva | visor.js:1366 | z 0,3395 | leva Ø44 × 8 | impresa (precios.yaml:160) | cuerno de disco MG996R |
| MG996R | linea_vasos.js:321-327 | eje según −y en z 0,3395 | 40,7 × 19,7 × 42,9 (electronica.js:1206) | comprado | 2 separadores impresos 17 mm a la placa |
| Placa de montaje | linea_vasos.js:328-337 | x 0,235 a 0,305, y −0,061 a −0,055, z 0,245 a 0,410 | 70 × 6 × 165, ventana del servo | **aluminio 6 mm** | cara −y de la viga |
| Buje guía | linea_vasos.js:353-356 | z 0,259 a 0,275 sobre el eje | 22 × 20 × 16 + brazo a la placa | impreso + casquillo bronce | placa |

---

## 8. Empujador

| Elemento | Def. | Posición | Medidas (mm) | Material | Sujeción |
|---|---|---|---|---|---|
| Paleta (reposo → fin) | visor.js:1415-1429; linea_vasos.js:406-477 | x 0,36; y de −0,055 a −0,1225 (carrera 67,5); borde de abajo z 0,138, arriba 0,193 | 60 × 55, cara de goma | impresa | carro en 2 varillas |
| Varillas guía (2) | linea_vasos.js:428-431 | x 0,345 y 0,375; z 0,26; de y −0,1355 a −0,035 (calc.) | Ø8 | acero | bloque impreso en la columna +x del pórtico |
| MG996R + manivela | linea_vasos.js:409-440 | eje vertical en (0,36; ≈ −0,0436) (calc.: ys = yR − r + 50 mm), cara de orejas z ≈ 0,2145 (calc.) | manivela r 33,75; biela 50 | servo comprado; manivela impresa | placa impresa en la columna x 0,315 |

---

## 9. Cámara de vasos, panel de luz, cortina y sensor interior

| Elemento | Def. | Posición | Medidas (mm) | Material | Sujeción |
|---|---|---|---|---|---|
| Webcam 720p de vasos | geometria.py:116-129; visor.js:4566-4576 | centro de la carcasa (0,16; −0,40; 0,21177) (300 mm del eje de la cinta); objetivo (0,16; −0,10; 0,17397) | 42 × 42 × 20 | comprada | poste |
| Poste de la cámara de vasos | linea_vasos.js:548-561, 597-616 | pie en (0,16; −0,422; 0) (calc.: 22 mm detrás, −y); alto hasta la placa ≈ 187,8 (calc.) | pie 30×30×4, poste 20×20 (caja), placa impresa 24 × 36 × 4 | aluminio (caja) | piso, sin escuadra |
| Panel de luz | visor.js:1269-1295; linea_vasos.js:523-539 | plano frontal en y −0,060; x −0,005 a 0,305; z 0,125 a 0,222 | 310 × 97 (calc.), difusor 3 mm, marco L 5 mm | acrílico opalino + tira LED | marco de barras 10 mm a la columna (visor.js:1281-1283) |
| Franjas de medida (por estación 0–3) | geometria.py:119-122; sensores_sim.py:342-356 | media z 0,167 (45 mm), borde z 0,2165 (94,5 mm), y de −0,14 a −0,06 | — | — | — |
| Cortina VL53L0X | sensores_sim.py:410-436; geometria.py:68-71 | origen (0,30; −0,185; 0,187) → destino (0,16; −0,185; 0,187); radio final 31,04 | ventana 140 mm, cono 25°, 65 mm sobre la banda, 85 mm del eje | GY-530 comprada | escuadra impresa + poste 10 mm de z 0,113 a 0,183 en x 0,308 + brazo 10 mm a z 0,108 desde y −0,1445 (placa lateral) (visor.js:4490-4504) |
| VL53L0X interior (verificación) | geometria.py:89-93 | cara (0,04; −0,10; 0,227) = 15 mm sobre la boca | GY-530 + porta impreso 30 × 7 × 3 | comprado | varilla Ø4 hasta z 0,388 y a la viga (visor.js:4721-4727) |

---

## 10. Bandejas de rechazo

| Bandeja | Def. | Centro en el piso | Medidas (mm) | Material |
|---|---|---|---|---|
| Monedas (única) | mundo.py:189-194; visor.js:1126-1142; linea_monedas.js:363-392 | (0,10; 0,13; 0,004) [visor: base en z 0] | 90 × 90 × 35, pared 2,5, piso 3 | impresa (PETG rojo según comentario; precios: PLA) |
| Vasos | mundo.py:241-246; visor.js:1450-1465 | (0,47; −0,10; 0,004) | 95,8 × 115,8 × 60 | impresa |

---

## 11. Canaleta de entrega y muelle del carro

| Dato | Valor | Fuente |
|---|---|---|
| Inicio (eje del riel, centro) | (0,36; −0,1375; 0,207) | mundo.py:262-290 (ejecutado) |
| Fin | (0,36; −0,4175; 0,13197) | ídem |
| Largo horizontal | 280 | parametros.yaml:166 |
| Pendiente | 15° (caída 75,03 calc.) | parametros.yaml:84 |
| Separación de rieles / entrada | 69 / 73 | parametros.yaml:171, 187 |
| Embudo | 40 de largo, 3 de caída | parametros.yaml:188-189 |
| Riel | varilla Ø4 + PTFE 0,13 | parametros.yaml:179 |
| Capacidad | 4 vasos | parametros.yaml:191 |
| Fin del embudo (m) | y −0,1775, z 0,19628 (calc.) | visor.js:1977-1981 |
| Vaso entregado (centro, inclinado 15°) | (0,36; −0,18705; 0,15045) | mundo.py:293-325 (ejecutado) |

| Elemento | Def. | Posición | Medidas (mm) | Material | Sujeción |
|---|---|---|---|---|---|
| Rieles (2) | visor.js:1995-1998; estructura.js:376-414 | x 0,3255 / 0,3945 (entrada 0,3235 / 0,3965) | Ø4, curva r 15 | acero + PTFE | cabezales |
| Postes altos (2) | visor.js:2001-2007 | x 0,2975 / 0,4225, y −0,2111; punta z 0,17528 | 2020, 163,28 (calc.) | 2020 + pie | piso |
| Postes bajos (2) | ídem | x 0,2975 / 0,4225, y −0,3095; punta z 0,14891 | 2020, 136,91 (calc.) | 2020 + pie | piso |
| Cabezales (4) | estructura.js:427-452 | sobre cada poste, riel 28 mm hacia adentro, 12 mm de alto | 41 × 20 × ~15, prisionero M3 | impreso | M5 a la punta del poste |
| Travesaños (2) | visor.js:2009-2020 | z 0,03, y −0,2111 / −0,3095 | 2020, 105 | 2020 | escuadras |
| Largueros (2) | visor.js:2021-2032 | z 0,05, x 0,2975 / 0,4225 | 2020, 78,4 (calc.) | 2020 | escuadras |
| Escuadras (8) | visor.js:2016, 2028 | 4 a z 0,04 y 4 a z 0,06 | 20×20×20 | fundición | — |
| Escape de dos dedos | visor.js:2040-2091 | pivote (0,41; −0,37597; 0,09810) (calc.) | balancín + 2 dedos Ø5 | impreso + SG90 | poste |
| Poste del escape | visor.js:2077-2089 | (0,444; −0,37597), punta z 0,055 (por el largo de 43 en precios.yaml:211) | 2020, 43 | 2020 + pie | piso |
| Muelle (guías en V + topes) | visor.js:2246-2300; geometria.py:314-338 | carro estacionado centro (0,36; −0,5075), rumbo −90° | guías 20 alto × 6 esp.; boca V 200 largo, abre 45; holgura 3; topes 22 de ancho a y ±52 | impreso | piso (M4, precios.yaml:175-176) |
| Rieles de la cuna del carro | visor.js:2314 | z 0,12897 (= fin − 3 mm) | — | — | carro |

Cola de la cuna: y = −0,5075 + 0,5·0,18 = −0,4175 = fin de la canaleta (geometria.py:36-38, 174).

---

## 12. Pórtico

| Elemento | Def. | Posición | Medidas (mm) | Material |
|---|---|---|---|---|
| Columnas (2) | visor.js:1240-1247; estructura.js:343-363 | (−0,035; −0,045) y (0,315; −0,045), de z 0,012 a 0,410 | 2020, 398 | 2020 + pie nivelador |
| Viga | ídem | eje y −0,045, z 0,40, x −0,025 a 0,305 | 2020, 330 | 2020 |
| Escuadras (2) | estructura.js:354-355 | bajo la viga, x −0,025 y 0,305, z 0,39 | 20×20×20 | fundición |

Cuelgan de la viga: placa fija (2 M5), pletina del 28BYJ-48, Hall, VL53L0X interior, colgante del
tubo de tapas, placa de la prensa, columna +x con el empujador, taco de la mesa de monedas.

---

## 13. Caja de control

| Dato | Valor | Fuente |
|---|---|---|
| Centro de la cara de abajo | (0,355; 0,145; 0) (sobre el piso) | visor.js:3038, 3066 |
| Medidas | 360 × 240 × 80 | visor.js:3039; control.js:7 |
| Huella | x 0,175 a 0,535; y 0,025 a 0,265 (calc.) | — |
| Material | placa de montaje alu 3 mm, paredes acrílico 3 mm, tapa policarbonato | control.js:207-213 |

---

## 14. Base / MDF

| Fuente | Dato |
|---|---|
| precios.yaml:90 | "Tablero MDF de 9 mm para la base y la pista", 40 000 COP |
| docs/peso.md:351 | "Tablero MDF de 9 mm bajo la planta (600 x 450 mm)", 1579,5 g |
| visor / mundo / urdf | **no definido**: ninguna pieza lo dibuja; patas, postes, bandejas y caja apoyan en z = 0. `crearMesaPerfil` tiene `tablero: false` por defecto (estructura.js:283, 322-326) y nadie lo activa |

Posición y orientación del tablero: no definidas.

---

## 15. Pies niveladores (15)

Pieza: base Ø26 + goma 2 mm, espárrago M6, alto 12 mm ±4 (estructura.js:250-265).

| Dónde | Posiciones (x; y) | Fuente |
|---|---|---|
| Mesa de monedas (3) | (−0,145; ±0,0405), (0,03; 0,0405) | visor.js:925-932 |
| Poste E4 (1) | (0,1395; 0) | visor.js:1100-1101 |
| Mesa de vasos (4) | (0,02 / 0,38; −0,13 / −0,07) | estructura.js:290-292 |
| Pórtico (2) | (−0,035 / 0,315; −0,045) | estructura.js:349-351 |
| Canaleta (4) | (0,2975 / 0,4225; −0,2111 / −0,3095) | visor.js:2003-2004 |
| Escape (1) | (0,444; −0,37597) | visor.js:2081-2082 |

---

## 16. Tramos de perfil 2020 y uniones (precios.yaml:189-234)

| Zona | Tramo | Largo | Cant. | Comprobado en visor |
|---|---|---|---|---|
| Monedas | larguero del riel | 251 | 2 | sí (visor.js:900) |
| Monedas | pata | 418 | 3 | sí (visor.js:937) |
| Monedas | travesaño de la cola | 61 | 1 | sí |
| Monedas | travesaño lateral | 155 | 1 | sí |
| Monedas | poste E4 | 377 | 1 | 376,55 (calc.) |
| Monedas | poste cámara cenital | 240 | 1 | en visor es caja de 262,3 (calc.) |
| Monedas | brazo cámara cenital | 70 | 1 | caja de 70,5 |
| Vasos | pata de la mesa | 88 | 4 | sí |
| Vasos | larguero de la mesa | 340 | 2 | sí |
| Vasos | travesaño de la mesa | 40 | 2 | sí |
| Vasos | poste cámara de vasos | 190 | 1 | caja de ≈ 183,8 |
| Pórtico | columna | 398 | 2 | sí |
| Pórtico | viga | 330 | 1 | sí |
| Canaleta | poste alto | 163 | 2 | 163,28 |
| Canaleta | poste bajo | 137 | 2 | 136,91 |
| Canaleta | travesaño | 105 | 2 | sí |
| Canaleta | larguero | 78 | 2 | 78,4 |
| Canaleta | poste del escape | 43 | 1 | — |

Total 6,10 m en 31 tramos (docs/costos.md:45). Escuadras: 5 + 9 + 2 + 8 = 24 (precios.yaml:231-234).

---

## 17. Componentes comprados montados

| Componente | Cant. | Medidas | Dónde | Fuente |
|---|---|---|---|---|
| NEMA 17 17HS4401 | 2 | 42,3 × 42,3 × 40, eje Ø5 × 24, M3 a 31 | rodillo de cola de cada cinta | electronica.js:1145-1151; parametros.yaml:74 |
| 28BYJ-48 + ULN2003 | 1 | Ø28 × 19, pestañas 42, eje descentrado 8 | sobre el carrusel | electronica.js:1177-1180 |
| SG90 | 4 | 22,5 × 11,8 × 22,7 | desvío, obturador, tapas, escape de la canaleta | electronica.js:1203; firmware.servos parametros.yaml:576-582 |
| MG996R | 2 | 40,7 × 19,7 × 42,9 | prensa, empujador | electronica.js:1206 |
| Webcam 1080p + anillo | 1 | 42 × 42 × 20, anillo 60/40 | E3 | sensores.js:342-344 |
| Webcam 720p | 1 | 42 × 42 × 20 | cámara de vasos | linea_vasos.js:590-600 |
| VL53L0X (GY-530) | 2 en planta | ~25 × 13 | cortina, interior | visor.js:4483-4487 |
| LJC18A3 / LJ18A3 | 1 + 1 | M18 × 68 / 60 | bajo E1 / E2 | sensores.js:328-335 |
| FC-51 | 1 | 32 × 14 × 1,6 | sobre E1 | sensores.js:226 |
| Hall KY-003 + imán 6×3 | 1 | 18,5 × 15 × 1,6 | carrusel | sensores.js:458, 482 |
| Rodamiento 608ZZ | ≥ 11 | 8 × 22 × 7 | 4 en rodillos de monedas, 6 en rodillos de retorno A/B/C, 1 en la placa fija | linea_monedas.js:166-174, 415-418; visor.js:958-960 |
| Rodamiento con brida KFL08 | 1 (visor) | brida 48 × 14 | rodillo motriz de vasos | linea_vasos.js:484-495 |
| Bandas | 2 | 55 mm y 75 mm | — | precios.yaml:76-77 |

---

## 18. Relaciones que no se pueden romper

1. Agujero de la placa fija = salida de la tolva = vaso de llenado (0,12; −0,10); el centro del carrusel sale de ahí (mundo.py:215-222, 235-238).
2. Carga a 90° y agujero a 300°: 210° de separación, así que nunca coinciden con tubos a 60° (mundo.py:207-212).
3. Hall a 0° entre los tubos de 330° y 30° (geometria.py:95-102).
4. Tubos de 58 mm entre z 0,270 y 0,328; sensor Hall 10 mm sobre la boca (geometria.py:101).
5. Tolva: boca z 0,262 (8 mm bajo el fondo de los tubos), salida z 0,230, 18 mm sobre la boca del vaso (0,212) (geometria.py:212).
6. Cinta de monedas sobre todo lo demás: superficie 0,452 → boca de carga 0,340 por gravedad (mundo.py:73-79; parametros.yaml:448).
7. Paso de casilla 40 / 80 mm con rodillo Ø22 = 69,1 mm por vuelta: 463 / 926 micropasos (parametros.yaml:546). Si cambia el rodillo, cambia el firmware.
8. Alturas de sensores: FC-51 a 50 mm, M18 a 2,5 mm bajo la superficie, cámara cenital a 150 mm, interior a 15 mm sobre la boca, cortina a 65 mm y 85 mm del eje, cámara de vasos a 300 mm (geometria.py; parametros.yaml:93, 103).
9. Canaleta: arranca en el borde −y de la banda (y −0,1375) a z = boca − r_riel − caída = 0,207; termina en la cola de la cuna (y −0,4175); la cuna está 3 mm por debajo (mundo.py:278-282; visor.js:2314).
10. Empujador a x de descarga (0,36); el cono de la cortina termina 20 mm después de la prensa para no estorbarle (sensores_sim.py:430-433).
11. Bandeja de vasos al final de la cinta (x de descarga + 110 mm) (mundo.py:246).
12. Tubo de tapas 13 mm sobre la boca; pistón 12 mm sobre la tapa con 13 mm de carrera (visor.js:1302, 1364-1365).
13. Panel de luz justo detrás de la banda (y −0,058), entre verificación y prensa, enfrentado a la cámara de vasos (visor.js:1269-1277).

---

## 19. Discrepancias entre fuentes

| # | Tema | Lado A | Lado B |
|---|---|---|---|
| 1 | Patas de la mesa de monedas | URDF: 4 patas en x −0,05 / 0,07, y ±0,02, 430 mm (cinta_monedas.urdf:46-49) | visor: 3 patas en (−0,145; ±0,0405), (0,03; 0,0405) + taco en la viga (visor.js:924-951) |
| 2 | Patas de la mesa de vasos | URDF: 14 × 14 en x 0,01 / 0,39 (cinta_vasos.urdf:139-142) | visor: 2020 en x 0,02 / 0,38 (visor.js:1229) |
| 3 | Bancada de vasos | URDF 400 × 80 (cinta_vasos.urdf:117) | visor 374 × 81 (visor.js:755-759) |
| 4 | Separadores de monedas | URDF 3 mm de alto (cinta_monedas.urdf:65-70) | visor 4 mm (visor.js:891) |
| 5 | Tubo de tapas | URDF r 34, z 0,25–0,35 (cinta_vasos.urdf:178-182) | visor r_int 41 / r_ext 43, desde z 0,225, 75 de alto (visor.js:1302; linea_vasos.js:219) |
| 6 | Prensa | URDF: columna + plato r 28 en z 0,285 (cinta_vasos.urdf:185-199) | visor: plato r 31, abajo en z 0,229, placa de alu en la viga (visor.js:1363-1373) |
| 7 | Empujador | URDF: paleta revoluta de 80 mm en (0,32; −0,14; 0,132) (cinta_vasos.urdf:207-224) | visor: paleta lineal biela-manivela en x 0,36 (visor.js:1415-1429) |
| 8 | Bandeja de vasos | URDF z 0,002, 96 × 116 (cinta_vasos.urdf:232, 244) / mundo z 0,004 (mundo.py:246) | visor 95,8 × 115,8 × 60 (visor.js:1454-1456); precios 104 × 124 × 60 (precios.yaml:169) |
| 9 | Marca de salida | URDF en (0,36; −0,20) (cinta_vasos.urdf:264-267), vieja | canaleta empieza en y −0,1375 (mundo.py:279) |
| 10 | Comentarios viejos de mundo.py | "su extremo queda justo encima del punto de carga" y "−0,08 + 0,20 = 0,12, igual a la estación 7 de monedas" (mundo.py:84-91) | E4 en x 0,07; carga en (0,1035; −0,0384); el visor lo resuelve con el canal A (visor.js:1066-1079) |
| 11 | Inclinación del canal | "canal que baja ~30 grados" y "5 tubos" (mundo.py:73-79, 99-104) | "canal corto a ~72 grados" (parametros.yaml:444); 6 posiciones (mundo.py:106-110) |
| 12 | Salida de la tolva | visor r 14 (Ø28) (visor.js:1557) | precios "Ø38 a Ø30" (precios.yaml:152) |
| 13 | Material de la placa fija y el disco | visor: acrílico (linea_monedas.js:397, 426) | precios: PLA (precios.yaml:78, 148-149) |
| 14 | Medidas de la placa y el disco | visor: placa Ø116 × 4, disco Ø104 × 3 (linea_monedas.js:402, 433) | precios: placa 116 × 116 × 15, disco 146 × 146 × 11 (precios.yaml:148-149) |
| 15 | Tubos del almacén | visor: policarbonato, Ø32 ext (linea_monedas.js:468-477) | precios "acrílico" (precios.yaml:78); peso.md Ø33 ext (peso.md:181) |
| 16 | Interior del tubo de tapas | visor y precios Ø82 (precios.yaml:79) | peso.md Ø78 (peso.md:256) |
| 17 | Panel de luz | visor 310 × 97 (calc., visor.js:1276-1278) | precios 33 × 11 cm (precios.yaml:35); peso 330 × 110 × 3 (peso.md:255) |
| 18 | Placa de la prensa | visor 6 mm (linea_vasos.js:333) | peso 70 × 165 × 8 (peso.md:253) |
| 19 | Bastidor de vasos | visor: placas de aluminio 430 × 34 × 4 en la cinta de vasos (visor.js:1224-1226) | peso.md las pone en la cinta de monedas (peso.md:132) y llama MDF a la "cama y placas laterales" (peso.md:203) |
| 20 | Tablero MDF | precios.yaml:90; peso.md:351 (600 × 450 × 9) | no existe en visor/sim/urdf |
| 21 | Brazos y tacos de las platinas M18 | precios: 4 × [14, 95, 3] y 2 × [14, 20, 3] impresos (precios.yaml:136-137) | en visor esas medidas son las placas colgantes de los rodillos de retorno (visor.js:968-971); las platinas M18 son de aluminio (linea_monedas.js:256-287). Lo infiero por las medidas |
| 22 | Bloque de varillas | precios lo llama "de la prensa" (precios.yaml:163) | en visor es del empujador (linea_vasos.js:430) |
| 23 | Soporte de la bandeja de vasos | precios.yaml:170 (33 × 41 × 75) | no está en el visor |
| 24 | Poste de la cámara de vasos | precios: 1 escuadra, 190 mm (precios.yaml:204, 232) | visor: pie 30 × 30 sin escuadra, ≈ 183,8 (linea_vasos.js:548-558) |
| 25 | Poste de la cámara cenital | tramo 240 (precios.yaml:199) | comentario 262 (precios.yaml:188); caja del visor 262,3 |
| 26 | Qué es "posición" de una cámara | cenital: el vidrio (visor.js:4526-4527) | vasos: centro de la carcasa, lente 27,3 mm adelante (linea_vasos.js:594) |
| 27 | Medio ancho de la canaleta | estructura.js:33 dice 75 mm | parametros.yaml:378 dice 100 mm |
| 28 | Alto de los tacos de casilla | visor 10 mm (linea_vasos.js:191) | precios 15 mm (precios.yaml:155) |
| 29 | Comentario del URDF de monedas | "5 separadores" (cinta_monedas.urdf:63) | dibuja 6 (cinta_monedas.urdf:65-70) |

---

## 20. Lo que la maqueta impresa cambió de este inventario (2026-10-25)

Mandan las piezas físicas: el visor y la simulación se ajustan a esto (rutas en `maqueta_impresa/`).

| § | Elemento | Aquí dice | En la maqueta impresa | Fuente |
|---|---|---|---|---|
| 1.2 | Ejes de los rodillos motriz y tensor de monedas | z 0,441 | z 0,439: la cima del Ø22 en 0,450, la cara de la bancada (la banda apoya en los dos; superficie 0,452 igual) | cinta_monedas.scad:39 |
| 1.2 | NEMA 17 de monedas | cara en y 0,097 | cara en y 0,100 (4 separadores de nailon de 3 mm; la jaula sigue en 0,093-0,097); el eje entra 9,5 mm en el acople | cinta_monedas.scad:55 |
| 1.2 | Banda de monedas (la que se compra) | 200 × 55 × 2 (tramo de arriba), separadores cada 40 | cerrada de ~620 × 55 × 2 alrededor de los rodillos motriz, tensor, B y A (L 611,5 con el tensor en x 86, 618 en 90), con 15 separadores a L/15 (≈ 41 mm) marcados desde el empalme: uno cada 40 deja una casilla de ~18 mm. El visor y la simulación pueden seguir con 40 (menos de 1,2 mm por casilla) | manual_maqueta.py |
| 1.2 | Bloques del rodillo motriz de monedas | — | abrazan el riel: labio bajo el riel y otro SOBRE el riel (z 0,4482-0,4512; x −0,135 a −0,098; \|y\| 0,034-0,0485); se montan deslizando en y | cinta_monedas.scad:249 |
| 1.2 | Retorno A de monedas | placas colgantes | sin placas: su eje Ø8 (de y −0,057 a 0,057) cuelga de las bajadas de los bloques del motriz (\|y\| 0,0485-0,0575, hasta z 0,336), con 2 casquillos impresos de \|y\| 0,0296 a 0,0484 (mon_casq_a_m/_p); el rodillo sigue en (−0,113; 0,344). Ya no existen mon_ret_a_m/_p ni sus 4 remaches | cinta_monedas.scad:250-266, 516 |
| 1.2 | Tensor de monedas | cojinetes tensores (608 fijo en x 0,090) | el 608 corre en una ranura de x 0,086 (montaje) a 0,090 (funcional, a tope), empujado por un M3 × 16 autorroscante que baja desde z 0,456 en \|y\| 0,0522, inclinado 12° hacia +x; ranura de 9 × 13 en los rieles (x 0,0835-0,0965); piso del bloque en z 0,422 | cinta_monedas.scad:296-317, 553 |
| 1.2 | Retorno C de monedas (rodillo, eje y colgantes) | rodillo en (0,065; 0,4188) con 2 placas colgantes | no hay: quedaba 6,3 mm dentro del lazo (la banda es el casco de los rodillos) y no tocaba la banda; se quitaron el rodillo, su eje de 64,6, mon_ret_c_m/_p y sus 4 remaches. El visor tiene que dejar de dibujarlo (y de pasar la banda por encima de él) | cinta_monedas.scad, esfuerzos.md |
| 3 | Salida del embudo E4 | Ø20 | Ø29 | cinta_monedas.scad:10 |
| 3 | Aleta de desvío | cuelga del pivote, reposo 0,5 rad, pasador Ø3 | placa de 2 que SUBE del pivote (0,105; 0; 0,418) dentro del embudo, ±45° (+45 = rechazo, reposo, punta hacia −y); barril Ø5 y cubo Ø8 a presión en la estría del SG90 | cinta_monedas.scad:25, 46 |
| 4.2 | Obturador | aleta Ø34 × 2 bajo la placa, bisagra a 20 mm | corredera de 44 × 35,8 × 1,9 en un rebaje de la placa fija, z 0,2681-0,270 (enrasada con el piso), de u −14,5 a 29,5 desde el agujero en la dirección 300°; abre corriéndose 30 mm a 300° | almacen.scad:93, 226 |
| 4.2 | SG90 del obturador | 47 mm de la bisagra | eje en (0,1265; −0,1413), caja hacia 210°; palanca de 24 mm con horquilla para el perno de la corredera, gira −90° (horario visto desde arriba) | almacen.scad:103, 240 |
| 4.2 | Tolva y columnas | — | poste 1 de la tolva a 270° (antes 300°); columnas hasta z 0,377 | almacen.scad:81, 110 |
| 5.2 | Ejes de los rodillos de vasos | z 0,111 | z 0,109 (la banda envuelve el Ø22: arriba 0,122 igual; vuelta de abajo en z 0,096-0,098) | cinta_vasos.scad:44 |
| 5.2 | NEMA 17 de vasos | origen (0; −0,1445; 0,111), cara en y −0,1785 | origen (0; −0,1445; 0,109), cara en y −0,1855 (separadores de 3 mm), cuerpo hasta y ≈ −0,2255; placa del motor en y −0,1825 a −0,1775 sobre 4 postes de 32,8 mm; la punta del eje del motor en y −0,1615, el medio del acople | cinta_vasos.scad:79, 412-417 |
| 5.2 | Largo de los ejes de los rodillos de vasos | — | el de x 0 de y −0,1605 a −0,0515 (109 mm: entra 9 en el acople y queda a 1 del eje del motor); el de x 0,400, 97,5 mm | cinta_vasos.scad:404 |
| 5.2 | Tensor de vasos (rodillo de x 0,400) | rodillo fijo | el 608 de cada lateral corre de x 0,396 (montaje) a 0,400 (funcional, a tope), empujado hacia +x por un prisionero M3 × 10 en z 0,107 (y −0,146 y −0,054); más allá de 0,400 no se tensa | cinta_vasos.scad:81-89, 164-189 |
| 5.2 | Bancada de vasos | x 0,013 a 0,387 | x 0,013 a 0,383 (a 2 del rodillo de x 0,400 cuando está en 0,396) | cinta_vasos.scad:62 |
| 5.2 | Banda de vasos (la que se compra) | 400 × 75 × 2, 6 separadores + 1 abajo | cerrada de ~875 × 75 × 2 (L = 2 × 400 + 2π × 12 = 875,4 con el tensor a tope), con 11 separadores a L/11 (≈ 79,6 mm) marcados desde el empalme: con 7 quedaban 2 huecos de 238 y la casilla de entrada sin separador al avanzar. El visor y la simulación pueden seguir con 80 (la resincronización por cámara corrige 0,4 mm por casilla) | manual_maqueta.py, cinta_vasos.scad (VAS_TACOS) |
| 5.2 | Tacos de casilla | arco a los dos lados | arco solo del lado +y; del lado −y (canaleta) cara recta, para que el vaso salga | cinta_vasos.scad:230-231 |
| 6 | Colgante del tubo de tapas | colgante de aluminio 12 × 12 (M3) | tap_colgante con 2 remaches verticales en (0,1875 y 0,2125; −0,0405; 0,3878) | tapas_prensa_empujador.scad:90-91 |
| 6 | Tubo de tapas: de qué cuelga | colgado del colgante | entra desde abajo y el hombro del cabezal (z 0,241) se pega con cianoacrilato al anillo de tap_abr_servo (corona de ~500 mm²): de ese pegado cuelga; el anillo solo frena la subida y los dedos no sostienen peso | tapas_prensa_empujador.scad:12-14, 164-167 |
| 9 | Cortina VL53L0X: sujeción | escuadra + poste + brazo (aluminio) | la GY-530 pegada con cinta doble faz a la cara −x (x 0,3018) de la escuadra de vas_cortina, chip hacia −x, centrada en (y −0,185; z 0,187); vas_cortina remachada a la cara −y del tubo (0,315; −0,1525) | cinta_vasos.scad:313-325, 446-448 |
| 7 | Prensa | carrera 13 (exc 6,5), neopreno 0,5 | carrera 14 (exc 7, leva R 22,5): el plato baja de 0,229 a 0,215 y aprieta 0,5 el ala de la tapa asentada (0,2155); sin neopreno ni resorte limitador. Suplementos de 0,5 y 1,0 mm (Ø62) para pegar bajo el plato si la tapa real lo pide: no van montados (en el ensamble, sueltos en el piso en (0,240; −0,0855)) | tapas_prensa_empujador.scad:48-49, 218-224 |
| 7 | Placa de la prensa | placa de aluminio en y −0,055 | tap_pre_placa de 6 mm (y −0,0547 a −0,0487) con costillas (x 0,240-0,249 y 0,290-0,299, hasta y −0,0782, de z 0,349 a 0,393 / 0,385), alargada hasta x 0,323 (z 0,257-0,367) y remachada a la viga (3) y a la cara −y de la columna de x 0,315 (4, en z 0,265 / 0,288 / 0,308 / 0,345); pie en z 0,257-0,2588 | tapas_prensa_empujador.scad:96-101, 178-200 |
| 8 | Paleta del empujador | — | 4 remaches con el carro, dos por brazo (z 0,2425 y 0,231); las lengüetas del carro y los brazos bajan a z 0,226 y el travesaño de la paleta va en z 0,219-0,225 | tapas_prensa_empujador.scad:117-122, 262-282 |
| 9 | Porta del VL53L0X interior | — | remachado bajo la viga en x 0,0365 y 0,0465 (y −0,0405) | tapas_prensa_empujador.scad:125-126 |
| 11 | Marco de la canaleta: amarre | travesaños, largueros y escuadras de 2020 sobre el MDF | el marco de tubos (nodos C1..C4, M1, M2) va unido al resto por can_amarre: puntal en Z de z 0,048 a 0,078 entre la cara +y del poste t_C1-L (0,2975; −0,2111) y la cara −y del poste t_V4-L (0,315; −0,1525), 2 remaches en cada poste. Plantilla de 69 mm (can_plantilla) para dejar las varillas a 69 entre ejes al remachar los cabezales; queda suelta en el piso del marco | canaleta_muelle.scad:185-205 |
| 12 | Pórtico | 2020, viga en y −0,045, columnas en x −0,035 / 0,315 | tubos 16 × 16 impresos: viga en y −0,0405, z 0,400; columnas P1 en x −0,050 y P2 en x 0,315 | estructura.py:69 |
| 14, 15 | MDF y pies niveladores | tablero 600 × 450, 15 pies | no hay: el piso de tubos apoya directo en la mesa (617 × 484 mm; con canaleta, muelle y bandejas, ~700 × 900) | estructura.py, manual_maqueta.py |
| 18.12 | Prensa | 13 mm de carrera | 14 mm | tapas_prensa_empujador.scad:48 |
