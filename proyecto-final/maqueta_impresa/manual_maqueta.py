"""Manual de armado de la maqueta impresa (usuario, 2026-10-24: "un manual inspirado en el que ya existe"), con la
misma forma que el del carro (chasis_impreso/manual.py): por cada paso, lo que se agrega en naranja sobre lo que ya
esta en gris, que piezas lleva y en que tanda se imprimen, sus remaches por medida, lo comprado que se monta y como,
y los cables hilo por hilo de lo que se monta en ese paso (sim/conexiones.py: el mismo conexionado del firmware).

comprobar() revisa que cada pieza impresa, cada remache y cada dispositivo de la planta salga en un paso, y se niega
a seguir si piezas.json no es de la geometria de hoy (2026-10-25: el PDF pedia remaches de agarres que ya no existian,
el mismo error del carro). En cada paso, "Antes de imprimir, mide:" sale de las lineas // MEDIR de su .scad.
Uso: python manual_maqueta.py   (despues de revisar.py y exportar.py) -> manual_maqueta.pdf, renders en img/manual/
"""
import json
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import revisar as R

AQUI = R.AQUI
D_IMG = AQUI / "img" / "manual"
sys.path.insert(0, str(AQUI.parent))
from sim import conexiones as cx   # noqa: E402
from sim import electrica as el    # noqa: E402  (la resistencia en serie del panel de luz y lo que deja pasar)

POSTES = ("t_F6-L", "t_V2-L", "t_V4-L", "t_C1-L", "t_C2-L", "t_C3-L", "t_C4-L", "t_K1-L")
SCAD = {"alm_": "almacen.scad", "mon_": "cinta_monedas.scad", "vas_": "cinta_vasos.scad",
        "tap_": "tapas_prensa_empujador.scad", "can_": "canaleta_muelle.scad"}

# (titulo, prefijo de sus piezas o None para la estructura, camara "x,y,z,rx,ry,rz,dist", que hacer, que lleva comprado,
#  dispositivos de la planta que se montan)
PASOS = [
    ("Piso: la base que amarra todo", None, "130,-150,0,55,0,320,1500", [
        "Seca cada rollo antes de usarlo (PLA: 45-50 °C, 4-6 h), sobre todo antes de rem_1 y rem_2 (las uñas de los "
        "remaches son lo más frágil que se imprime); entre tandas, guárdalo cerrado con desecante.",
        "Antes de imprimir las tandas de remaches: abre 3mf/rem_1.3mf como proyecto (con su configuración), borra todo "
        "menos ~10 rem_4_4 y lamina: así salen con su perfil (un STL suelto entra con el perfil que tengas activo). "
        "Pruébalos en un nodo y un tubo ya impresos. Los de agarre menor de 8 tienen la ranura desde dentro de la cabeza "
        "(queda un puente de 1 mm): tienen que entrar con el punzón y hacer clic. Si el puente se raja o no entran, no "
        "imprimas el resto todavía. Lo mismo con 3mf/can_1.3mf, dejando solo can_cabezal_c1 y can_prisionero_c1, para "
        "probar la rosca impresa del prisionero antes de la tanda entera.",
        "Arma el piso sobre una mesa plana: nodos del piso (los de abajo plano) y tubos entre ellos. Cada tubo entra 22 mm "
        "en su cajera y se traba con 2 remaches de 4,4 por los costados del nodo (el agarre ya cuenta que el tubo se corre "
        "0,4 dentro de la cajera: no hace falta sostenerlo de lado).",
        "Los tramos largos van en dos partes unidas con un empalme (manguito con tope al medio) y 4 remaches.",
        "Antes de remachar, cuadra el piso: los nodos tienen que quedar planos y las líneas a escuadra.",
        "La canaleta tiene su propio marco de piso (C1-C4, M1, M2): se arma igual, aparte; en el paso de la canaleta el "
        "amarre (can_amarre) lo une al poste de la cinta de vasos de (315, -152,5).",
    ], "Nada comprado; no hace falta tablero (el piso de tubos amarra todo). La mesa: el piso ocupa 617 × 484 mm y, con la "
       "canaleta, el muelle y las bandejas (apoyan directo en la mesa), unos 700 × 900 mm.", []),
    ("Patas, pórtico y mesa de monedas", None, "-20,0,260,60,0,320,1300", [
        "Patas de la mesa de monedas (x -170 y x 30) y columnas del pórtico, cada una en su nodo del piso.",
        "Nodos de arriba (se imprimen dados vuelta): rieles de la mesa de monedas a z 440 y viga del pórtico a z 400.",
        "La pata de x 30, lado +y, sigue de largo como poste de la cámara cenital hasta el nodo de arriba y su brazo.",
        "Los dos tacos unen el riel -y con la viga (placa por la cara -y, 2 remaches en cada tubo).",
    ], "Nada comprado.", []),
    ("Postes de la cinta de vasos, de la cámara de vasos y de la canaleta", "POSTES", "200,-250,80,60,0,320,1100", [
        "Postes con la punta libre: lado -y de la cinta de vasos en x 40 y x 315, lado +y en x 30 (la columna del "
        "pórtico de x 315 hace de cuarto apoyo); poste de la cámara de vasos en (160, -422); cuatro postes de la "
        "canaleta (los de adelante más altos).",
        "Cada poste entra en la cajera de arriba de su nodo del piso, con 2 remaches.",
    ], "Nada comprado.", []),
    ("Cinta de vasos", "vas_", "200,-100,120,60,0,330,900", [
        "Bastidor: laterales partidas en x 200 (se unen con la bancada), remachadas desde adentro a los postes del "
        "lado -y; del lado +y, el taco de cada lateral llena el hueco hasta el poste de x 30 y la columna de x 315. "
        "Remacha las laterales a los postes ANTES de poner rodillos y banda (después tapan esos remaches).",
        "Corta 3 mm del extremo -y de los separadores de la banda (dejan pasar el vaso que baja a la canaleta).",
        "Remacha la placa del motor a los 4 postes huecos de la lateral -y ANTES de atornillar el NEMA 17 (con el motor "
        "puesto no entra el punzón). El motor NO apoya directo en la placa: lleva 4 separadores de nailon de 3 mm en sus "
        "M3 × 12 (aire entre la brida y el PLA: el motor se calienta; prueba con termómetro en «Antes de encender»). Con "
        "los separadores su resalte Ø22 ya no entra en la placa y no lo centra: pon el acople en los dos ejes y aprieta los "
        "M3 recién con el motor centrado por el acople.",
        "Rodillos con sus ejes Ø8 (corta el del rodillo de x 0 a 109 mm y el de x 400 a 97,5): 608 en las laterales y KFL08 "
        "del lado del motor, con el acople al rodillo de x 0. En el acople de 20 el eje del motor entra 10 mm y el Ø8 9 mm "
        "(queda 1 mm entre los dos); cada prisionero del acople aprieta sobre su eje (el del motor, sobre su cara plana).",
        "El rodillo de x 400 va con sus dos 608 al fondo -x de su corredera (x 396): así la banda entra floja.",
        "Tacos de casilla: dos mitades pegadas a cada lado de cada separador, con la cara RECTA hacia -y (la canaleta) y "
        "la curva hacia el panel de luz: al revés, el vaso no sale cuando lo empuja la paleta.",
        "Tensa la banda con los 2 prisioneros M3 × 10 de los topes (llave Allen de 1,5 por fuera de cada lateral, a lo "
        "largo de x): la misma vuelta a los dos, para que el rodillo quede paralelo, hasta que los 608 toquen el fin de la "
        "corredera (x 400); más allá no se puede tensar. Mide la tensión con una balanza de gancho: levanta 10 mm el medio "
        "del ramal de arriba; T ≈ 10 × la lectura en N (para T = 20 N, ~2 N, unos 200 g). Si a tope queda floja, la banda "
        "está larga: se corrige su empalme.",
        "Panel de luz (dos mitades remachadas) a las columnas: la tira LED va sobre cinta de aluminio pegada al marco "
        "(reparte el calor) y con una resistencia de 3,3 Ω 1 W en serie, soldada en línea en su +5 V del lado de la caja "
        "(lejos del PLA): deja las tiras en ~1,4 W. Sin ella son 4 W y el marco de 1,6 llega a ~65 °C, más que la Tg del "
        "PLA. Cortina: la GY-530 (VL53L0X) se pega con cinta doble faz a la cara -x de la escuadra de vas_cortina, con el "
        "chip hacia -x, centrada en (y -185, z 187); vas_cortina va remachada al poste de (315, -152,5). La webcam de "
        "vasos en su placa sobre el poste de (160, -422), con su tornillo de 1/4\"; la bandeja de rechazo suelta en el piso.",
    ], "Banda CERRADA de ~875 × 75 × 2 (mide el largo con una cuerda alrededor de los rodillos montados) con 11 separadores "
       "repartidos en partes iguales: con la banda ya empalmada, mide su largo L y marca uno cada L/11 (≈ 79,6 mm) desde el "
       "empalme (uno cada 80 deja una casilla corta); 2 rodillos Ø22 × 79 con ejes Ø8 (109 y 97,5 mm), 3 rodamientos 608 "
       "y 1 KFL08 con 2 tornillos M4 y sus tuercas, acople Ø19 × 20, NEMA 17 con 4 separadores de nailon de 3 mm y 4 M3 × "
       "12, 2 prisioneros M3 × 10 (tensor), webcam 720p y 1 tornillo de 1/4\", VL53L0X con cinta doble faz, tira LED de "
       "5 V (2 tramos) con cinta de aluminio y una resistencia de 3,3 Ω 1 W; una balanza de gancho.",
     ["motor_vasos", "vl53_cortina", "panel_luz", "cam_vasos"]),
    ("Almacén de monedas (carrusel)", "alm_", "100,-70,300,55,0,330,620", [
        "Puente del motor colgado de la viga con sus dos horquillas (6 remaches), SIN el 28BYJ-48 todavía: con el motor "
        "puesto el eje ya no entra (el cuerpo tapa el agujero Ø16 del puente y entre el cubo del 608 y el puente hay 74 mm "
        "para un eje de 76,5). El motor va al final de este paso.",
        "Columnas del puente a la placa fija (la 2 lleva el módulo Hall en su ranura; abajo cada columna entra en la U de "
        "su pestaña); la placa fija con el 608 de abajo; la tolva remachada bajo la placa fija, con el SG90 del obturador "
        "en su bolsillo y la palanca en su estría (a presión; se calza con el servo en reposo, ver «Antes de encender»).",
        "Obturador: desde arriba, la corredera en el rebaje de la placa fija con su perno dentro de la horquilla de la "
        "palanca. En reposo (cerrado) la corredera queda enrasada con el piso; abre corriéndose 30 mm hacia afuera cuando "
        "la palanca gira 90°.",
        "Cinta de PTFE de 0,13 mm en la cara de arriba de la placa fija, en el anillo de R 17 a 49 del eje (por donde se "
        "arrastran las monedas) sin tapar el rebaje de la corredera, y otra tira sobre la corredera sin tapar la luz de "
        "0,2 de alrededor: baja el roce y el par que pide el 28BYJ-48; los tubos siguen pasando 0,37 mm sobre el piso.",
        "Rotor: el disco PEGADO al alma del tambor (los 6 agujeros Ø29 lo centran; sin remaches) y el imán en su "
        "alojamiento a 0°. Antes de pegar el imán, acércalo al KY-003 (alimentado) y mira el LED: el A3144 responde a un "
        "solo polo; marca la cara que lo enciende y pégala hacia arriba (el sensor queda encima, cara hacia abajo). Al "
        "revés, el homing nunca encuentra la referencia y el imán pegado ya no sale.",
        "El rotor (tambor y disco, SIN eje) entra de costado desde +y, unos 8 mm por encima del cubo del 608, y se baja "
        "sobre la placa fija. Después el eje de acero Ø8 entra desde arriba por el agujero Ø16 del puente, pasa a presión "
        "por el cubo del disco hasta el 608 y se pega en el cubo. Luego el acople rígido sobre el eje y, AL FINAL, el "
        "28BYJ-48: baja su eje dentro del acople y se atornilla al puente con 2 tornillos M4 autorroscantes en sus "
        "agujeros ciegos (no van remaches).",
        "Embudo de carga a las columnas (el remache del lado del disco, con el punzón).",
        "Gira el carrusel a mano: una vuelta entera sin rozar nada. Después, prueba de par: con los 6 tubos con 9 "
        "monedas cada uno, 5 vueltas desde la app sin perder pasos (el imán tiene que volver al Hall). Cada giro ya "
        "arranca y para con rampa (firmware.carrusel_rampa_ms y carrusel_rampa_pasos en config/parametros.yaml). Si "
        "pierde pasos: primero más rampa (sube cualquiera de los dos); después carrusel_ms_por_paso 3; con cada cambio, "
        "tiempos_ms.carrusel_giro con él. Si aun así no alcanza, reducción GT2 2:1 o 3:1, o un NEMA 17.",
    ], "Eje de acero Ø8, rodamiento 608, acople rígido Ø12 × 16, 28BYJ-48 con ULN2003 y 2 tornillos M4 autorroscantes "
       "cortos (lo que entra en el PLA no puede pasar de 3,6 mm: M4 × 4, o más largo con arandelas), SG90, módulo KY-003, "
       "imán de 6 × 3, cianoacrilato (eje y disco), cinta de PTFE de 0,13 mm.",
     ["motor_carrusel", "hall", "servo_obturador"]),
    ("Tapas, prensa y empujador", "tap_", "260,-90,260,55,0,330,800", [
        "Antes de imprimir la prensa, mide la tapa real: un vaso con su tapa apoyada sin asentar sobre una balanza de "
        "cocina; empuja la tapa con una tabla plana hasta que asiente (clic) y anota el pico: F = 9,81 × kg. La prensa no "
        "tiene resorte que dé fuerza: aprieta 0,5 mm al final de la carrera contra lo que cede la estructura (~0,05 mm/N "
        "estimado, sin contar la holgura de las cajeras), unos 10 N; cada 0,5 mm de suplemento bajo el plato suma unos "
        "10 N (0,5 → ~21 N, 1,0 → ~32 N, los dos → ~42 N). Si 1,2 × F pasa de ~42 N, con suplementos no alcanza: hace "
        "falta más carrera de la leva, y eso es un cambio de diseño, no de armado. La prueba con tapas reales («Antes de "
        "encender») es la que manda.",
        "Colgante del tubo de tapas a la viga (2 remaches de 5,8 desde abajo); abrazaderas al colgante ANTES de poner la "
        "placa de la prensa (después la placa tapa sus remaches); tubo de tapas (cabezal hacia abajo) metido desde abajo: "
        "súbelo hasta que el hombro del cabezal toque el anillo de la abrazadera de abajo (tap_abr_servo) y pégalos con "
        "cianoacrilato en toda la corona (~500 mm²). Ese pegado es lo que lo sostiene: el anillo solo frena la subida y "
        "los dedos no aguantan peso. SG90 invertido en su placa y dedos A y B en las ranuras del cabezal y sus guías, "
        "con los 2 pernos Ø2 del cuerno. Cuerno del escape en reposo: +14,2° (el dedo A sostiene la pila); recorrido 28°.",
        "Prensa: placa a la cara -y de la viga (3 remaches de 7,8) Y a la cara -y de la columna de x 315 (4 de 7,8; mejor "
        "antes de montar el empujador), MG996R entre sus separadores, leva al cuerno de disco, buje guía; vástago Ø8 con el "
        "resorte, la horquilla con su rodillo arriba (eje Ø3 con una gota de cianoacrilato en cada punta, para que no "
        "se salga) y el plato abajo (a presión y pegados), SIN suplementos. Leva en reposo: la parte gruesa arriba "
        "(pistón arriba); recorrido 180° (el pistón baja 14 mm).",
        "Empujador: soporte en la cara +x de la columna de x 315 con el bloque de las varillas Ø8; las varillas van a "
        "presión en sus agujeros ciegos hasta el tope (con morsa; si quedan flojas, pegadas); carro con la paleta sobre "
        "las varillas: remacha la paleta con el carro corrido a y -122 (4 remaches de 9,4, dos por brazo; en reposo la "
        "columna los tapa); placa del MG996R colgada del bloque; manivela y biela con sus pernos M4: una gota de "
        "cianoacrilato en el agujero del carro para su perno (abre hacia abajo y la biela gira sobre él: sin pegar se "
        "sale). Manivela en reposo hacia +y (paleta atrás, en y -55); recorrido 180°.",
        "Sensor interior VL53L0X en su porta, colgado de la viga en x 40.",
        "Mueve cada mecanismo a mano en todo su recorrido antes de conectar los servos. Los suplementos de la prensa "
        "(0,5 y 1,0 mm) quedan sueltos hasta la prueba con tapas reales («Antes de encender»).",
    ], "SG90, 2 MG996R con cuerno de disco, vástago Ø8 × 79, 2 varillas Ø8 × 102,5, resorte de compresión Ø15 exterior "
       "(largo libre ≥ 38, a bloque ≤ 15, k 0,15-0,3 N/mm), eje Ø3 del rodillo, 2 pernos M4, 2 pernos de acero Ø2 (cuerno "
       "del escape a los dedos), goma de la paleta, VL53L0X, tapas Ø78; cianoacrilato (tubo de tapas, pernos y "
       "suplementos) o cinta doble faz fina (suplementos); balanza de cocina y calibre para medir.",
     ["servo_tapas", "servo_prensa", "servo_empujador", "vl53_interior"]),
    ("Cinta de monedas y compuerta E4", "mon_", "0,0,420,55,0,330,800", [
        "Bancada entre los rieles con 6 remaches de costado a la cara interior de los rieles; guías laterales con 8 "
        "remaches desde arriba; platinas de los M18 bajo la bancada (4 remaches) ANTES de poner los sensores M18 (después "
        "tapan esos remaches).",
        "Bloques del rodillo motriz (el +y es también la jaula del NEMA 17), con sus 608: entran deslizando en y, "
        "abrazando el riel con los labios de arriba y de abajo; después sus 2 remaches desde abajo. El NEMA 17 va con 4 "
        "separadores de nailon de 3 mm en sus M3 × 12: la brida no toca el PLA (el motor se calienta; prueba con termómetro "
        "en «Antes de encender»). Con los separadores su resalte Ø22 ya no lo centra: céntralo con el acople antes de "
        "apretar. El eje del motor entra solo 9,5 mm en el acople: el prisionero, sobre su cara plana.",
        "Bloques del tensor: antes de poner cada 608, pasa una vez el M3 × 16 por el agujero inclinado de arriba (corta la "
        "rosca en el PLA) y sácalo; el 608 va en la punta de adentro de su ranura (x 86), todavía sin el rodillo tensor.",
        "Compuerta E4: placa bajo los labios de los bloques del tensor, con el embudo. La aleta va ANTES del rodillo tensor "
        "y la banda: bájala por la boca del embudo con el barril a lo largo de x y córrela 6,5 mm hacia +x hasta que el cubo "
        "Ø8 pase por el Ø8,4 de la pared. SG90 en su brida; la aleta se calza a presión en su estría con el servo en "
        "reposo: aleta en +45°, punta hacia -y (rechazo); recorrido 90°, hasta -45° (almacén).",
        "Canal A al embudo de carga del almacén y canal B (dos tramos) a la bandeja de rechazo, con su soporte al poste "
        "de la cámara; la bandeja va suelta en el piso.",
        "Rodillos motriz y tensor con sus ejes Ø8 por los agujeros de los rieles (el del tensor, por la ranura, en x 86). "
        "Retorno A, sin placas: sostén el rodillo y sus dos casquillos entre las bajadas de los bloques del motriz y pasa "
        "el eje Ø8 × 114 desde afuera, por la gota de una bajada hasta la otra. Placas colgantes del retorno B; banda "
        "puesta alrededor de los rodillos.",
        "Tensa la banda: enrosca los 2 M3 × 16 desde arriba (entran inclinados 12°), media vuelta por lado y alternando, "
        "hasta que los dos 608 lleguen al fondo de la ranura (x 90, el tope). Mide la tensión con una balanza de gancho: "
        "levanta 5 mm el medio del ramal de arriba; T ≈ 10 × la lectura en N (para T = 20 N, ~2 N, unos 200 g). No pases "
        "de ~24 N: el colgante del retorno B llega a su límite (esfuerzos.md). Si a tope queda floja, la banda está larga, "
        "y si pasa de 24 N antes del tope, está corta: no fuerces el tornillo (rosca en el PLA); se corrige su empalme.",
        "Columna del FC-51 en el riel -y; abrazadera de la cámara en la punta del brazo, con la webcam (su tornillo de "
        "1/4\") y el anillo LED.",
    ], "Banda CERRADA de ~615 × 55 × 2 (mide el largo con una cuerda alrededor de los rodillos montados) con 15 "
       "separadores de 4 mm repartidos en partes iguales: con la banda ya empalmada, mide su largo L y marca uno cada L/15 "
       "(≈ 41 mm) desde el empalme (uno cada 40 deja una casilla de ~18 mm donde no entra una moneda); 4 rodillos Ø22 × 59 "
       "con ejes Ø8 (los de retorno: A 114 y B 84,3 mm), 4 rodamientos 608, NEMA 17 con 4 separadores de nailon de 3 mm y "
       "4 M3 × 12, 2 tornillos M3 × 16 autorroscantes (empuje del tensor), acople Ø19 × 25, sensor capacitivo M18 × 68 y "
       "sensor inductivo M18 × 60 con sus tuercas, FC-51, webcam 1080p con anillo LED y 1 tornillo de 1/4\", SG90; una "
       "balanza de gancho.",
     ["motor_monedas", "presencia", "capacitivo", "inductivo", "servo_desvio", "cam_cenital", "anillo"]),
    ("Canaleta de entrega y muelle del carro", "can_", "360,-350,120,55,0,330,950", [
        "Amarre del marco: can_amarre entre el poste de C1 (297,5; -211,1) y el de la cinta de vasos (315; -152,5), "
        "a z 48-78, con 2 remaches en cada poste. Sin él el marco queda suelto y el carro, al atracar contra los topes, lo "
        "corre: pon el marco en su lugar contra el piso principal antes de remachar.",
        "Cabezales en las puntas de los cuatro postes (2 remaches cada uno); varillas Ø4 con PTFE en las cunas, "
        "apretadas con los prisioneros impresos (si una se suelta, una gota de cianoacrilato en C1/C2). Antes de "
        "remachar los cabezales y apretar los prisioneros, apoya la plantilla de 69 mm (can_plantilla, muescas hacia "
        "abajo) sobre las dos varillas junto a cada par de cabezales: las deja a 69 entre ejes. Después queda suelta.",
        "Soporte del escape al tubo C4-M2; SG90 en su cuna con los tornillos de su kit; balancín de dos dedos al brazo "
        "del servo, calzado con el servo en reposo: retener (el dedo A, el de aguas abajo, adentro); recorrido 21°.",
        "Muelle: guías rectas a los tubos C3-M1 y C4-M2, bocas en V con su cola de milano; viga de los topes sobre el "
        "tubo M1-M2 con la espuma.",
        "Prueba: un vaso tiene que bajar solo por los rieles, quedar retenido en el escape y soltarse de a uno.",
    ], "2 varillas de acero Ø4 con PTFE (con la curva de la entrada), SG90 con su brazo y tornillos, espuma EVA de 6 mm.",
     ["servo_canaleta"]),
]
INTERNOS = ("interno", "dupont", "usb", "red")    # cables de la caja de control y del portátil (paso final)


def paso_de_pieza(n, estructura):
    """Numero de paso (0..) de una pieza."""
    for k, (_, pre, *_r) in enumerate(PASOS):
        if pre and pre != "POSTES" and n.startswith(pre):
            return k
    if n.startswith(POSTES) or any(n.startswith(f"e_{p[2:]}") for p in POSTES):
        return 2
    return 0 if n in estructura["piso"] else 1


def estructura_por_altura(piezas):
    """El piso: los tubos y empalmes que no pasan de 25 mm de alto y los nodos con el centro en el piso."""
    import estructura as E
    piso = {n for n, p in E.NODOS.items() if p[2] < 20}
    for n in piezas:
        if n.startswith(("alm_", "mon_", "vas_", "tap_", "can_")) or n in E.NODOS:
            continue
        tri = R.ex_carro.leer_stl(R.CACHE / "ens" / f"{n}.stl")
        if len(tri) and tri.reshape(-1, 3)[:, 2].max() <= 25:
            piso.add(n)
    return {"piso": piso}


def paso_de_remache(r, mallas, pasos):
    """El remache se pone cuando ya estan TODAS las piezas que junta: se mide cuales atraviesa (rayos por su eje,
    como revisar.py) y va al paso de la ultima que se monta. Asi el remache de un poste no cae en el paso del piso."""
    import numpy as np
    _, agarre, cab, eje = r
    d = eje / np.linalg.norm(eje)
    aux = np.array([0, 0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0, 0])
    x = np.cross(aux, d); x /= np.linalg.norm(x)
    o = cab + 2.7 * x - d * 5
    junta = [n for n, m in mallas.items()
             if any(a - 5 < agarre - 0.3 and b - 5 > 0.3 for a, b in R.intervalos(o, d, [m]))]
    assert junta, f"remache {r[0]}: no atraviesa ninguna pieza"
    return max(pasos[n] for n in junta)


def a_medir(pre):
    """Lo que el .scad del subsistema da por supuesto de lo comprado (sus lineas // MEDIR, leidas del .scad: si cambian
    alla, cambian aqui). Sin titulos de seccion ni menciones sueltas; de una variable, su nombre y su valor."""
    if pre not in SCAD:
        return []
    out = []
    lineas = (AQUI / SCAD[pre]).read_text(encoding="utf-8").splitlines()
    for k, linea in enumerate(lineas, start=1):
        if "MEDIR" not in linea or "//" not in linea:
            continue
        codigo, com = linea.split("//", 1)
        com = com.strip()
        solo = not codigo.strip()
        if solo:      # nota sola: su variable es la primera linea de codigo que sigue (si es una asignacion)
            codigo = next((l for l in lineas[k:] if l.strip() and not l.strip().startswith("//")), "").split("//")[0]
        asig = re.findall(r"(\w+)\s*=\s*([^;]+);", codigo) if re.match(r"\s*\w+\s*=", codigo) else []
        if com.startswith("-") or not (re.search(r"MEDIR(/\w+)?:", com) or (asig and not solo)):
            continue
        texto = re.sub(r"^MEDIR(/\w+)?:\s*", "", com)
        out.append(f"{texto}: {asig[-1][0]} = {asig[-1][1].strip()} ({SCAD[pre]}:{k})" if asig else f"{texto} ({SCAD[pre]}:{k})")
    return out


def comprobar(piezas, rem, pasos, rpasos, datos):
    assert set(pasos) == set(piezas), "hay piezas sin paso"
    assert len(rpasos) == len(rem), "hay remaches sin paso"
    # candado: las tandas, gramos y remaches de las tablas salen de piezas.json; si es de otra geometria, el manual
    # pediria remaches de un agarre que ya no junta nada (el error del carro)
    impresas = {f["pieza"] for f in datos["piezas"] if f["grupo"] != "rem"}
    assert impresas == set(piezas), (f"piezas.json es de otra geometria (faltan {sorted(set(piezas) - impresas)}, sobran "
                                     f"{sorted(impresas - set(piezas))}): correr exportar.py antes")
    usados = {f["agarre"]: f["usados"] for f in datos["piezas"] if f["grupo"] == "rem"}
    medidos = dict(Counter(round(r[1], 1) for r in rem))
    assert usados == medidos, f"piezas.json pide otros remaches ({usados} contra {medidos} medidos): correr exportar.py antes"
    # los remaches de un paso no pueden ser de piezas que se montan despues
    planta = {d for d, v in cx.DISPOSITIVOS.items() if v["zona"] == "planta"}
    en_pasos = {d for p in PASOS for d in p[5]}
    assert planta == en_pasos, f"dispositivos de la planta sin paso: {planta - en_pasos}; de mas: {en_pasos - planta}"
    for c in cx.CABLES:
        for h in c["hilos"]:
            for punta in (h["de"], h["a"]):
                cx.pin(punta)
    print(f"comprobado: {len(piezas)} piezas, {len(rem)} remaches y {len(planta)} dispositivos de la planta, cada uno en un paso")


def render(k, piezas, pasos, rem, rpasos):
    D_IMG.mkdir(parents=True, exist_ok=True)
    gris = [n for n in piezas if pasos[n] < k]
    naranja = [n for n in piezas if pasos[n] == k]
    rems = [r[0] for r, p in zip(rem, rpasos) if p == k]
    subs = [pre[:-1] for _, pre, *_r in PASOS[:k + 1] if pre and pre != "POSTES"]
    lista = lambda l: "[" + ", ".join(f'"{x}"' for x in l) + "]"
    scad = D_IMG / f"paso_{k}.scad"
    scad.write_text(f'include <{(AQUI / "maqueta.scad").as_posix()}>\nmodo = "nada";\n'
                    f'GRIS = {lista(gris)};\nNARANJA = {lista(naranja)};\nRPASO = {lista(rems)};\n'
                    'color("#c9cdd1") for (n = GRIS) pieza(n);\ncolor("#ff7a1a") for (n = NARANJA) pieza(n);\n'
                    + "".join(f"{s}_comprados();\n" for s in subs) +
                    'color("#d1001f") for (r = REM_TODOS) if (search([r[0]], RPASO)[0] != []) remache_en(r);\n',
                    encoding="utf-8")
    png = D_IMG / f"paso_{k}.png"
    subprocess.run([str(R.OPENSCAD), "-o", str(png), "--render", "--imgsize=1600,1100", f"--camera={PASOS[k][2]}",
                    "--colorscheme=Tomorrow", str(scad)], capture_output=True)
    assert png.exists(), f"no salio el render del paso {k}"
    return png


def portada(png=AQUI / "img" / "maqueta_iso.png"):
    """Portada del manual e imagen del README: el ensamble entero (maqueta.scad, modo "ensamble": piezas, remaches y lo
    comprado), dibujado en cada corrida con los .scad de hoy (2026-10-25: era del 24 y nadie la volvia a dibujar)."""
    png.unlink(missing_ok=True)
    subprocess.run([str(R.OPENSCAD), "-o", str(png), "--render", "--imgsize=1800,1300", "--camera=150,-190,300,55,0,320,2200",
                    "--colorscheme=Tomorrow", str(AQUI / "maqueta.scad")], capture_output=True)
    assert png.exists(), "no salio el render de la portada"
    return png


def main():
    piezas, rem, _ = R.listas()
    # los pasos del armado salen de las piezas en su lugar: con STL viejos el manual no es lo fisico (2026-10-25)
    viejas = [r.stem for r in R.viejos([R.CACHE / "ens" / f"{n}.stl" for n in piezas])]
    if viejas:
        raise SystemExit(f"{len(viejas)} STL de _cache/ens faltan o se dibujaron con otros .scad ({viejas[:5]}...): "
                         "correr antes python revisar.py")
    datos = json.loads((AQUI / "piezas.json").read_text(encoding="utf-8"))
    lam = ""      # lo que da Creality Print al laminar (laminar.py), si ya se lamino
    if (AQUI / "laminado.json").exists():
        L = json.loads((AQUI / "laminado.json").read_text(encoding="utf-8"))
        horas = sum(int(v) * {"d": 24, "h": 1, "m": 1 / 60, "s": 1 / 3600}[u] for x in L for v, u in re.findall(r"(\d+)([dhms])", x["tiempo"]))
        lam = f"; Creality Print da {sum(x['gramos'] for x in L) / 1000:.2f} kg y ≈ {horas:.0f} h al laminar"
    tanda = {f["pieza"]: ", ".join(f.get("tandas", [])) for f in datos["piezas"]}
    est = estructura_por_altura(piezas)
    pasos = {n: paso_de_pieza(n, est) for n in piezas}
    import numpy as np
    mallas = {n: R.ex_carro.leer_stl(R.CACHE / "ens" / f"{n}.stl") for n in piezas}
    cajas = {n: R.caja(m) for n, m in mallas.items()}
    cerca = lambda r: {n: m for n, m in mallas.items() if np.all(cajas[n][0] - 25 < r[2]) and np.all(cajas[n][1] + 25 > r[2])}
    rpasos = [paso_de_remache(r, cerca(r), pasos) for r in rem]
    comprobar(piezas, rem, pasos, rpasos, datos)
    with ThreadPoolExecutor(4) as ej:
        tapa = ej.submit(portada)
        imgs = list(ej.map(lambda k: render(k, piezas, pasos, rem, rpasos), range(len(PASOS))))
        tapa.result()

    est_ = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=est_["Title"], fontSize=24, spaceAfter=6)
    h1 = ParagraphStyle("h", parent=est_["Heading1"], fontSize=18, spaceAfter=4, textColor=colors.HexColor("#c25400"))
    h2 = ParagraphStyle("h2", parent=h1, fontSize=13, spaceBefore=4, spaceAfter=2, textColor=colors.HexColor("#1f3a5f"))
    cuerpo = ParagraphStyle("c", parent=est_["BodyText"], fontSize=10.5, leading=14, spaceAfter=4)
    chico = ParagraphStyle("ch", parent=cuerpo, fontSize=8.5, leading=10.5, spaceAfter=1)
    nota = ParagraphStyle("n", parent=cuerpo, fontSize=9.5, textColor=colors.HexColor("#555555"))
    lleva = ParagraphStyle("l", parent=cuerpo, backColor=colors.HexColor("#fff1e6"), borderPadding=6, spaceBefore=8)
    ancho = landscape(A4)[0] - 30 * mm
    doc = SimpleDocTemplate(str(AQUI / "manual_maqueta.pdf"), pagesize=landscape(A4), leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title="Manual de armado de la maqueta impresa",
                            author="Proyecto final, grupo 7")
    estilo_tabla = lambda: TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                       ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fa")),
                                       ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])
    h = [Paragraph("Manual de armado de la maqueta impresa", titulo),
         Paragraph("Planta de monedas y vasos, proyecto final grupo 7. Toda la estructura y los soportes en PLA, unidos con "
                   "remaches impresos (sin perfil de aluminio ni escuadras; solo llevan tornillos los motores, los servos y "
                   "algunos sensores, y cada paso dice cuáles).", nota),
         Image(str(AQUI / "img" / "maqueta_iso.png"), width=170 * mm, height=170 * mm * 1300 / 1800),
         Paragraph(f"<b>Material:</b> {datos['total_gramos'] / 1000:.2f} kg de PLA en {len(datos['tandas'])} tandas "
                   f"(≈ {datos['total_horas']:.0f} h estimadas{lam}). Detalle en material.md; archivos en 3mf/ (una cama cada uno) y "
                   "stl/ (una pieza cada uno, ya girada para imprimir).", cuerpo),
         Paragraph("<b>Cómo leer cada paso:</b> en naranja lo que se agrega, en gris lo que ya está, en rojo los remaches del paso "
                   "y lo comprado con su color. Todo remache es de un agarre medido en el ensamble (revisar.py): no se cambian "
                   "entre medidas. Se meten empujando hasta el clic con un punzón o una varilla de Ø5 de punta plana: en "
                   "varios lugares el dedo no entra detrás de la cabeza.", cuerpo), PageBreak()]
    for k, (tit, pre, cam, que, lleva_txt, dispositivos) in enumerate(PASOS):
        mias = sorted(n for n in piezas if pasos[n] == k)
        texto = [Paragraph(f"{i}. {t}", cuerpo) for i, t in enumerate(que, start=1)]
        texto.append(Paragraph(f"<b>Lleva comprado:</b> {lleva_txt}", lleva))
        # al lado de la imagen va lo que cabe en su alto; el resto sigue debajo a todo el ancho (2026-10-25: con los avisos
        # nuevos el texto de un paso no entraba en una sola fila de tabla y reportlab no la puede partir)
        alto_img = 165 * mm * 1100 / 1600
        al_lado, usado = [], 0.0
        for p in texto:
            ph = p.wrap(ancho - 170 * mm - 12, 10000)[1] + 6
            if al_lado and usado + ph > alto_img:
                break
            al_lado.append(p)
            usado += ph
        t = Table([[Image(str(imgs[k]), width=165 * mm, height=alto_img), al_lado]],
                  colWidths=[170 * mm, ancho - 170 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        h += [Paragraph(f"Paso {k + 1}. {tit}", h1), t] + texto[len(al_lado):] + [PageBreak()]
        # piezas y remaches
        filas = [[Paragraph("<b>Pieza</b>", chico), Paragraph("<b>Se imprime en</b>", chico)]]
        filas += [[Paragraph(n, chico), Paragraph(f"3mf/{tanda.get(n, '?')}.3mf", chico)] for n in mias]
        cuenta = {}
        for r, p in zip(rem, rpasos):
            if p == k:
                cuenta[round(r[1], 1)] = cuenta.get(round(r[1], 1), 0) + 1
        filas_r = [[Paragraph("<b>Remache</b>", chico), Paragraph("<b>Cuántos</b>", chico)]]
        filas_r += [[Paragraph(f"rem_{str(a).replace('.', '_')}.stl (agarre {a} mm)", chico), Paragraph(str(c), chico)]
                    for a, c in sorted(cuenta.items())]
        tp = Table(filas, colWidths=[90 * mm, 70 * mm], repeatRows=1)
        tp.setStyle(estilo_tabla())
        tr = Table(filas_r, colWidths=[70 * mm, 25 * mm], repeatRows=1)
        tr.setStyle(estilo_tabla())
        doble = Table([[tp, tr]], colWidths=[165 * mm, ancho - 165 * mm])
        doble.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        h += [Paragraph(f"Paso {k + 1}. {tit}: piezas y remaches", h1), doble]
        medir = a_medir(pre)
        if medir:
            h.append(Paragraph(f"<b>Antes de imprimir, mide</b> lo comprado que {SCAD[pre]} da por supuesto (si no coincide, "
                               "se cambia allí y se vuelven a correr revisar.py y exportar.py):", cuerpo))
            h += [Paragraph(f"• {escape(m)}", chico) for m in medir]
        h.append(PageBreak())
        # componentes y cables de la planta que se montan en este paso
        if dispositivos:
            h.append(Paragraph(f"Paso {k + 1}. {tit}: componentes y cables", h1))
            h.append(Paragraph("Cada fila es un hilo: color, de dónde sale y a dónde llega (en la caja de control). Es el mismo "
                               "conexionado del firmware (sim/conexiones.py). Deja los cables recogidos con bridas a lo largo de "
                               "la estructura hasta la caja.", nota))
            for c in cx.CABLES:
                if not any(h_["de"].split(".")[0] in dispositivos or h_["a"].split(".")[0] in dispositivos for h_ in c["hilos"]):
                    continue
                filas = [[Paragraph(f"<b>{e}</b>", chico) for e in ("", "De", "A", "Función")]]
                filas += [[Paragraph(f"<font color='{h_['color']}' size='13'>■</font>", chico),
                           Paragraph(f"{cx.DISPOSITIVOS[h_['de'].split('.')[0]]['nombre']} · <b>{h_['de'].split('.', 1)[1]}</b>", chico),
                           Paragraph(f"{cx.DISPOSITIVOS[h_['a'].split('.')[0]]['nombre']} · <b>{h_['a'].split('.', 1)[1]}</b>", chico),
                           Paragraph(h_["funcion"], chico)] for h_ in c["hilos"]]
                tk = Table(filas, colWidths=[8 * mm, (ancho - 8 * mm) * 0.36, (ancho - 8 * mm) * 0.36, (ancho - 8 * mm) * 0.28])
                tk.setStyle(estilo_tabla())
                h.append(KeepTogether([Paragraph(c["nombre"], h2), tk, Spacer(1, 2 * mm)]))
            h.append(PageBreak())
    # caja de control: todo el cableado interno
    h.append(Paragraph(f"Paso {len(PASOS) + 1}. Caja de control y cableado interno", h1))
    h.append(Paragraph("La caja de control (fuente, reguladores, ESP32 fijo, drivers, PCA9685) no entra en este manual de piezas "
                       "impresas: va en su caja de siempre (docs/conexiones.md). Aquí está su cableado interno completo, hilo por hilo.", nota))
    for c in cx.CABLES:
        if c["tipo"] not in INTERNOS or not c["hilos"]:
            continue
        filas = [[Paragraph(f"<b>{e}</b>", chico) for e in ("", "De", "A", "Función")]]
        filas += [[Paragraph(f"<font color='{h_['color']}' size='13'>■</font>", chico),
                   Paragraph(f"{cx.DISPOSITIVOS[h_['de'].split('.')[0]]['nombre']} · <b>{h_['de'].split('.', 1)[1]}</b>", chico),
                   Paragraph(f"{cx.DISPOSITIVOS[h_['a'].split('.')[0]]['nombre']} · <b>{h_['a'].split('.', 1)[1]}</b>", chico),
                   Paragraph(h_["funcion"], chico)] for h_ in c["hilos"]]
        tk = Table(filas, colWidths=[8 * mm, (ancho - 8 * mm) * 0.36, (ancho - 8 * mm) * 0.36, (ancho - 8 * mm) * 0.28])
        tk.setStyle(estilo_tabla())
        h.append(KeepTogether([Paragraph(c["nombre"], h2), tk, Spacer(1, 2 * mm)]))
    h += [Paragraph("Antes de encender", h2)] + [Paragraph(f"• {x}", cuerpo) for x in (
        "Con la red desconectada: continuidad entre el GND en estrella (los empalmes soldados en los bornes −V de la fuente) y el del ESP32 fijo; ningún +12/+6/+5 con GND.",
        "Gira a mano el carrusel, la banda de monedas y la de vasos, y mueve cada mecanismo en todo su recorrido: nada roza.",
        "Primer encendido sin servos conectados; después uno por uno desde la app.",
        "Cuernos de los servos (palanca del obturador, aleta E4, cuerno del escape de tapas, leva, manivela, balancín de "
        "la canaleta): se calzan con el servo en reposo (0°, config/parametros.yaml firmware.servos), puesto desde la app "
        "o con un probador de servos, y el mecanismo en la posición de reposo que dice su paso. Después, a activo: tiene "
        "que moverse su recorrido hacia el lado que dice el paso. Si gira al revés, no lo fuerces: se usa el otro extremo "
        "del servo (reposo 180 y activo 180 menos el recorrido) y se vuelve a calzar.",
        "Prueba de banco de los dos NEMA 17: 200 pasadas seguidas de cada cinta desde la app, con un termómetro en la "
        "carcasa del motor (y otro en la abrazadera de la cámara cenital, por el anillo LED). Si la carcasa pasa de 45 °C, "
        "baja la Vref de su A4988 a la de 0,8 A (esfuerzos.md); si la abrazadera pasa de 45 °C, el anillo también va con "
        "una resistencia en serie, en línea del lado de la caja, como el panel.",
        "Panel de luz, con su resistencia de {} Ω en serie: un amperímetro en su +5 V y un voltímetro en la tira; "
        "I × V_tiras no puede pasar de {} W (se espera ~{} A con ~{} V en las tiras). Si pasa, la resistencia de 4,7 Ω."
        .format(*(f"{v:.{d}f}".replace(".", ",") for v, d in ((el.PANEL_R_SERIE, 1), (el.PANEL_P_MAX_W, 1),
                                                             (el.panel_luz()["i"], 2), (el.panel_luz()["v_tiras"], 1)))),
        "Prensa, con tapas reales: un vaso con su tapa en la estación de la prensa y un ciclo desde la app. Si la tapa no "
        "queda asentada (sin clic), pega bajo el plato el suplemento de 0,5 (cinta doble faz fina o una gota de "
        "cianoacrilato, centrado: los dos son de Ø62) y repite; si no, el de 1,0 en su lugar; si no, los dos. Mide el "
        "espesor real con calibre (el de 1,0 puede salir de 0,9 o 1,1). Usa el más delgado que asienta la tapa: apretar "
        "de más solo deforma el vaso. Si con los dos no asienta, no apiles más: hace falta más carrera de la leva (cambio "
        "de diseño: leva, visor y simulación juntos).")]
    doc.build(h)
    print("manual:", AQUI / "manual_maqueta.pdf")


if __name__ == "__main__":
    main()
