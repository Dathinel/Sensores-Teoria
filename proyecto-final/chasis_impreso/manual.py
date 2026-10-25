"""Manual de armado ilustrado, ordenado por TANDAS DE IMPRESION (usuario, 2026-10-21): por cada tanda,
que piezas trae y donde va cada una (resaltada sobre el carro) y los pasos de armado que esa tanda permite.
Cada paso tiene la misma forma (usuario, 2026-10-24): que hacer, sus remaches, que componentes se montan y
como, y que cables deja. El paso del piso 2 trae TODAS las conexiones, hilo por hilo, sacadas de
sim/conexiones.py (de ahi sale tambien firmware/pines.py: el manual y el firmware no pueden diferir).
comprobar() revisa que cada componente, cable, remache y compra del carro salga en algun paso.
Los renders salen de manual.scad.

Uso: python manual.py   -> manual_armado.pdf (renders en img/manual/)
Se regenera solo desde el modelo: si cambia una pieza, se corre otra vez (despues de guia_corte.py).
Los datos de PIEZAS_INFO tambien los usa modelo_3d.py (visor 3D).
"""
import subprocess
from concurrent.futures import ThreadPoolExecutor

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import sys

import yaml

import exportar as ex
import diagramas
import materiales

sys.path.insert(0, str(ex.AQUI.parent))
from sim import conexiones as cx   # noqa: E402  (mismo conexionado que el firmware y el visor)

AQUI = ex.AQUI
D_IMG = AQUI / "img" / "manual"
ABAJO, ATRAS, ADELANTE = "0,0,30,125,0,215,520", "0,0,60,58,0,215,560", "10,0,60,58,0,125,520"
DERECHA, ARRIBA = "10,0,60,58,0,320,520", "0,0,60,25,0,215,560"

# pieza: (donde va, camara, lo que se oculta para verla). Mismo orden que las tandas.
PIEZAS_INFO = {
    "chasis": ("La base de todo: la placa con nervios. Lo demás se engancha a ella.", ATRAS, []),
    "barra_tcrt5000": ("Debajo del chasis, adelante: sostiene los 5 TCRT5000 a 7 mm del piso.", ABAJO, ["ruedas"]),
    "porta_baterias": ("Encima del chasis, en el centro, bajo el piso 2: lleva el pack 2S.", ARRIBA,
                       ["piso2_esp32", "soporte_tb6612", "esp32", "tb", "vaso"]),
    "pared_cuna_izq": ("Cuna del vaso, lado izquierdo: lleva el TCRT5000 de la cuna.", ATRAS, []),
    "pared_cuna_der": ("Cuna del vaso, lado derecho: lleva la lengüeta.", DERECHA, []),
    "mampara": ("Frente de la cuna: amarra las dos paredes y lleva las espumas.", ARRIBA, ["vaso"]),
    "zapata_guia": ("Por dentro de las paredes de la cuna, a media altura (4): guían el vaso.", ARRIBA, ["vaso", "espumas"]),
    "lengueta": ("Atrás de la pared derecha de la cuna: traba el vaso para que no se salga.", DERECHA, ["vaso"]),
    "soporte_motor_izq": ("Debajo del chasis, rueda izquierda: abraza la caja del motor TT.", ABAJO, ["ruedas"]),
    "soporte_motor_der": ("Debajo del chasis, rueda derecha: abraza la caja del motor TT.", ABAJO, ["ruedas"]),
    "soporte_encoder_izq": ("Contra la mejilla interior del soporte del motor izquierdo: sostiene el H206.", ABAJO, ["ruedas"]),
    "soporte_encoder_der": ("Contra la mejilla interior del soporte del motor derecho: sostiene el H206.", ABAJO, ["ruedas"]),
    "torre_rueda_loca": ("Debajo del chasis, delante del centro: lleva la rueda loca.", ABAJO, ["ruedas"]),
    "soporte_rodillo_izq": ("Debajo de la cola, lado izquierdo: rodillo guía del muelle.", ABAJO, ["ruedas"]),
    "soporte_rodillo_der": ("Debajo de la cola, lado derecho: rodillo guía del muelle.", ABAJO, ["ruedas"]),
    "caja_interruptor": ("Costado izquierdo, en el medio: el interruptor de encendido.", ADELANTE, []),
    "caja_fusible": ("Costado derecho, en el medio: el portafusible de 3 A.", DERECHA, []),
    "escuadra_frontal": ("Al frente: HC-SR04 (invertido) y VL53L0X.", ADELANTE, []),
    "piso2_esp32": ("Piso de arriba, sobre las 4 columnas: ESP32 en su GVS y puente H.", ADELANTE, []),
    "soporte_tb6612": ("Sobre el piso 2, lado izquierdo: la placa TB6612.", ADELANTE, []),
}

# Orden en que conviene imprimir y armar: la tanda 5 (remaches) se necesita desde la tanda 1.
ORDEN_TANDAS = [1, 5, 2, 3, 4]

# Pasos: (tanda, titulo, camara, que hacer, que lleva). El numero del paso es el de manual.scad.
PASOS = [
    (1, "Barra de los sensores de línea", ABAJO, [
        "Clava la placa de los 5 TCRT5000 en los dos pernos partidos de la barra (hacen clic), con los sensores "
        "hacia el piso.",
        "Clava la barra en el chasis por los pernos de sus columnas, desde abajo (golpe suave).",
        "La cara de los sensores tiene que quedar a 7 mm del piso. Si queda baja, calza con una arandela entre "
        "la columna y el chasis.",
    ], "Placa de 5 TCRT5000. No lleva remaches."),
    (1, "Porta baterías", ATRAS, [
        "Encaja el porta baterías en el centro del chasis con 2 remaches de 10,5 por el divisor del medio "
        "(cabeza adentro, la uña sale por debajo del chasis).",
        "El pack va después (paso de energía), con la correa de velcro por las ranuras de los costados.",
    ], "2 remaches de 10,5 (tanda 5)."),
    (2, "Cuna del vaso", ATRAS, [
        "Forra con cinta PTFE el borde de arriba de las paredes (el riel) y la cara de las 4 zapatas.",
        "Clava las zapatas en las paredes (2 pernos cada una), del lado de adentro.",
        "Pared derecha: pon la lengüeta sobre su repisa con el remache de 6 y el elástico entre el gancho de "
        "la lengüeta y la pared. Tiene que volver sola hacia adentro.",
        "Pared izquierda: TCRT5000 de la cuna en su pin, mirando por la ventana, y amarrado con una brida.",
        "Encaja cada pared en el chasis con 2 remaches de 11 desde arriba.",
        "Mampara: 4 remaches de 9,5 desde adelante a los postes de las paredes y 2 remaches de 11 al chasis. "
        "Pega las dos espumas en su cara de atrás.",
    ], "Cinta PTFE, elástico, 1 brida, 2 espumas, TCRT5000 de la cuna, 1 remache de 6, 4 de 9,5, 6 de 11."),
    (3, "Motores (debajo del chasis)", ABAJO, [
        "Para trabajar abajo, apoya el carro boca abajo sobre una caja, sin cargar el peso en la cuna.",
        "Suelda los cables a los motores TT. Mete cada caja TT entre las mejillas de su soporte (el eje hacia "
        "el hueco de la rueda).",
        "Pon el soporte del encoder contra la cara de adentro de la mejilla interior (la repisa abajo, debajo "
        "del eje) y empuja los 2 pasadores a través de la pestaña, la mejilla y la caja, hasta que asomen al ras "
        "de la mejilla exterior: el último tramo entra apretado. Si quedan flojos, M3 x 30 con tuerca.",
        "Encaja cada soporte bajo el chasis con 2 remaches desde abajo: el de 14 en la oreja de atrás (su uña "
        "asoma en el hueco del pie de la pared de la cuna) y uno de 10,5 en la oreja de adelante.",
    ], "2 motores TT, 2 soportes de encoder, 4 pasadores, 2 remaches de 14, 2 de 10,5."),
    (3, "Encoders H206", "0,0,30,125,0,215,430", [
        "Pon el disco de 20 ranuras en la punta interior de cada eje.",
        "Apoya el H206 sobre la repisa del soporte del encoder, con el disco dentro de la horquilla.",
        "Amárralo con dos bridas por las ranuras de la repisa, que quedan a los costados de la placa.",
    ], "2 discos de 20 ranuras, 2 módulos H206, 4 bridas."),
    (3, "Rueda loca y rodillos guía", ABAJO, [
        "Atornilla la rueda loca de bola a la brida de su torre (2 tornillos M3 x 10, tuerca en la torre) y "
        "clava la torre en el chasis por sus dos pernos.",
        "Rodillos: dos rodamientos 623 con arandelas en un M3 x 20, tuerca arriba del brazo. Cada bloque va "
        "bajo la cola con 2 remaches de 37 desde abajo.",
    ], "Rueda loca, 2 M3 x 10 y 2 M3 x 20 con tuerca, 4 rodamientos 623, 6 arandelas, 4 remaches de 37."),
    (3, "Ruedas", ABAJO, [
        "Presiona cada rueda en el eje en D del motor, dejando al menos 2 mm con la mejilla exterior.",
        "Gíralas con la mano: tienen que dar vueltas sin rozar nada. Ya puedes poner el carro sobre sus ruedas.",
    ], "2 ruedas TT de 65 mm."),
    (4, "Energía", ATRAS, [
        "Caja del interruptor (lado izquierdo) y caja del fusible (lado derecho), con 2 remaches de 10,5 cada "
        "una. Monta el interruptor de balancín y el portafusible con el fusible de 3 A.",
        "Pon el pack 2S en el porta baterías con la correa de velcro.",
        "Cableado: B+ al fusible, al interruptor y de ahí a VM del TB6612 y a VIN de la GVS. Los cables van "
        "por los canales de los nervios y suben por los pasacables.",
    ], "Pack 2S con BMS, velcro, interruptor, portafusible y fusible de 3 A, 4 remaches de 10,5."),
    (4, "Sensores del frente", ADELANTE, [
        "Encaja la escuadra con 2 remaches de 11 desde arriba.",
        "Clava el HC-SR04 INVERTIDO (conector arriba) en sus 4 pines y el VL53L0X encima en sus 2. Si quedan "
        "flojos, una gota de pegante en un pin.",
        "Los cables salen hacia atrás por la ventana de la escuadra.",
    ], "HC-SR04, VL53L0X, 2 remaches de 11."),
    (4, "Piso 2: ESP32 y puente H", ADELANTE, [
        "Pasa los cables de abajo por los pasacables de 8 mm antes de cerrar.",
        "Clava el piso 2 en los pernos de las 4 columnas del chasis.",
        "Encaja la GVS con el ESP32 en sus 4 pernos partidos (hacen clic).",
        "Clava el soporte del TB6612 en sus 2 pernos y amarra la placa con una brida, con los pines hacia abajo.",
    ], "ESP32 DevKit en su GVS, TB6612FNG, 1 brida."),
    (4, "Revisión final", "5,0,55,58,0,40,520", [
        "Las ruedas giran libres y nada roza al girar el carro sobre su eje.",
        "El vaso entra desde atrás deslizando por los rieles hasta la espuma, y la lengüeta cae detrás de él.",
        "Los TCRT5000 leen la línea a 7 mm del piso.",
        "Ningún cable cuelga cerca de las ruedas ni del piso.",
    ], "Un vaso para probar la cuna."),
]
REMACHES_DONDE = [("6", 1, "pivote de la lengüeta"), ("9,5", 4, "mampara a los postes de las paredes"),
                  ("10,5", 8, "porta baterías (2), oreja delantera de los motores (2), cajas del interruptor y del fusible (4)"),
                  ("11", 8, "pies de las paredes (4), pie de la mampara (2), escuadra (2)"),
                  ("14", 2, "oreja trasera de los motores"), ("37", 4, "bloques de los rodillos guía")]

# Remaches: color por medida (los mismos de COLOR_REM en manual.scad) y, por paso de PASOS (numero de
# manual.scad), que remaches lleva: (medida, cuantos, donde, por donde entra). Camara de la vista de remaches.
COLOR_REM = {"6": "#ff2fa0", "9,5": "#8a2be2", "10,5": "#e0001b", "11": "#0077ff", "14": "#00a651", "37": "#00c8d7"}
FRENTE_ALTO = "0,0,70,50,0,35,520"
REM_PASO = {
    2: (ARRIBA, [("10,5", 2, "porta baterías al chasis, por el divisor del medio", "desde arriba")]),
    3: (FRENTE_ALTO, [("11", 4, "pies de las dos paredes de la cuna al chasis", "desde arriba"),
                      ("11", 2, "pie de la mampara al chasis (debajo de la mampara)", "desde arriba"),
                      ("9,5", 4, "mampara a los postes delanteros de las paredes", "desde adelante"),
                      ("6", 1, "pivote de la lengüeta, sobre la repisa de la pared derecha", "desde arriba")]),
    4: (ABAJO, [("14", 2, "oreja trasera de cada soporte de motor", "desde abajo"),
                ("10,5", 2, "oreja delantera de cada soporte de motor", "desde abajo")]),
    6: (ABAJO, [("37", 4, "bloques de los rodillos guía (2 por bloque)", "desde abajo")]),
    8: (ARRIBA, [("10,5", 4, "cajas del interruptor y del fusible (2 por caja)", "desde arriba")]),
    9: (ADELANTE, [("11", 2, "pie de la escuadra frontal", "desde arriba")]),
}


# Componentes que se montan en cada paso (numero de PASOS): (id en sim/conexiones.py, como se monta, que cables deja).
COMPONENTES_PASO = {
    1: [("ir_linea", "Clava la placa en los 2 pernos partidos de la barra (hacen clic), con los 5 sensores mirando al piso.",
         "Conecta 7 cables Dupont hembra-hembra de 20 cm a su conector (OUT1 a OUT5, VCC y GND) y súbelos por uno de "
         "los 2 pasacables delanteros (los de 8 mm junto a las columnas del piso 2). Marca el cable de OUT1 con cinta: "
         "OUT3 es el sensor del centro.")],
    3: [("ir_cuna", "En el pin de la pared izquierda de la cuna, con los LED mirando por la ventana hacia el vaso, y "
                    "amarrado con una brida por las 2 ranuras.",
         "3 Dupont hembra-hembra (DO, VCC y GND), por encima del chasis, por el canal de cables de los nervios del lado "
         "izquierdo hasta el piso 2. El pin AO no se usa.")],
    4: [("motor_izq", "Caja TT entre las mejillas del soporte izquierdo, eje hacia la rueda (ver los pasos de arriba).",
         "Antes de montarlo: suelda 2 cables de 22 AWG de 25 cm a sus bornes, rojo a M+ y negro a M−, y un "
         "condensador de 100 nF entre los dos bornes. Trenza el par y llévalo por debajo del chasis hasta el pasacables lateral izquierdo (el de 8 mm justo detrás "
         "de la caja del interruptor), y súbelo por ahí."),
        ("motor_der", "Igual, en el soporte derecho.",
         "Igual que el izquierdo, por el pasacables lateral derecho (detrás de la caja del fusible).")],
    5: [("enc_izq", "Sobre la repisa del soporte del encoder izquierdo, con el disco dentro de la horquilla y 2 bridas.",
         "3 Dupont hembra-hembra (D0, VCC y GND) junto al par del motor, por el mismo pasacables lateral. Si tu "
         "módulo trae un cuarto pin (A0), no se usa."),
        ("enc_der", "Igual, en el lado derecho.", "Igual, por el pasacables lateral derecho.")],
    8: [("bateria", "Pack 2S (con su BMS) en el porta baterías, sujeto con la correa de velcro por las ranuras.",
         "B+ en rojo y B− en negro, de 22 AWG. Del B− salen 2 cables negros: uno al TB6612 (GND_P) y otro al plug del "
         "jack de la GVS. Deja los dos para el paso del piso 2."),
        ("interruptor", "Interruptor de balancín a presión en la ventana de la caja izquierda; portafusible en el "
                        "agujero de la caja derecha con su tuerca, fusible de 3 A adentro.",
         "En el modelo son un solo bloque, «Interruptor + fusible 3 A»: su pin 1 es la ENTRADA del portafusible y su "
         "pin 2 la SALIDA del interruptor. Por dentro van en serie: B+ → portafusible → cable rojo de 22 AWG por "
         "encima del porta → interruptor. Del pin 2 (salida del interruptor) salen 2 cables rojos: uno a VM del "
         "TB6612 y otro al plug del jack. Deja el interruptor APAGADO.")],
    9: [("hcsr04", "Invertido (conector arriba) en sus 4 pines de la escuadra; si queda flojo, una gota de pegante.",
         "4 Dupont hembra-hembra (VCC, TRIG, ECHO, GND) hacia atrás por la ventana de la escuadra. En el ECHO va el "
         "divisor: resistencia de 1 kΩ en serie hacia el ESP32 y una de 2 kΩ desde el lado del ESP32 a GND, todo "
         "cubierto con termoencogible (el ECHO sale a 5 V y el ESP32 aguanta 3,3 V)."),
        ("vl53_frontal", "Encima del HC-SR04, en sus 2 pines de la escuadra.",
         "4 Dupont hembra-hembra (VIN, GND, SCL, SDA) hacia atrás por la misma ventana. XSHUT y GPIO1 no se usan.")],
    10: [("esp32_carro", "ESP32 DevKit de 30 pines puesto en la placa GVS, y la GVS clavada en sus 4 pernos partidos "
                         "del piso 2 (hacen clic). Jumper de la GVS en 3,3 V.",
          "En cada GPIO la GVS tiene 3 pines: G = GND (junto al ESP32), V = 3,3 V (al medio) y S = señal (afuera). "
          "En la página siguiente, todas las conexiones."),
         ("tb6612", "En su soporte sobre el piso 2, pines hacia abajo, amarrado con una brida.",
          "Recibe la batería (VM, GND_P), los motores (AO1/AO2, BO1/BO2) y 9 cables del ESP32.")],
}
# Compras del carro (config/precios.yaml) -> paso donde se montan. pista: va en la mesa, no en el carro.
COMPRA_PASO = {"esp32_carro": 10, "motores_carro": 4, "encoders": 5, "linea_ir": 1, "ultrasonico": 9,
               "laser_frontal": 9, "cuna": 3, "puente_h_carro": 10, "bateria_carro": 8, "interruptor_carro": 8,
               "rodillos_guia": 6, "cuna_carro": 3, "pista": None}
PASO_CONEXIONES = 10
GRUESOS = {"c_bat", "c_mot"}   # 22 AWG (corriente de la batería y los motores); el resto, Dupont de 26 AWG


def cables_carro():
    return [c for c in cx.CABLES if c["tipo"] == "carro"]


def comprobar():
    """Que nada del carro quede fuera del manual (usuario, 2026-10-24: "no haga como lo de los remaches")."""
    montados = {d: i for i, lista in COMPONENTES_PASO.items() for d, _, _ in lista}
    del_carro = {d for d, v in cx.DISPOSITIVOS.items() if v["zona"] == "carro"}
    assert del_carro == set(montados), f"componentes sin paso: {del_carro - set(montados)}; de mas: {set(montados) - del_carro}"
    for c in cables_carro():
        for h_ in c["hilos"]:
            for punta in (h_["de"], h_["a"]):
                dev = punta.split(".")[0]
                assert montados[dev] <= PASO_CONEXIONES, f"{punta}: se monta despues de las conexiones"
                cx.pin(punta)   # el pin existe en su placa
    precios = yaml.safe_load((ex.AQUI.parent / "config" / "precios.yaml").read_text(encoding="utf-8"))
    compras = {k for k, v in precios["items"].items() if v.get("subsistema") == "Carro"}
    assert compras == set(COMPRA_PASO), f"compras del carro sin paso: {compras ^ set(COMPRA_PASO)}"
    assert all(p is None or 1 <= p <= len(PASOS) for p in COMPRA_PASO.values())
    assert set(REM_PASO) <= set(range(1, len(PASOS) + 1))
    assert sum(c for _, lista in REM_PASO.values() for _, c, _, _ in lista) == sum(c for _, c, _ in REMACHES_DONDE)
    hilos = sum(len(c["hilos"]) for c in cables_carro())
    print(f"comprobado: {len(montados)} componentes, {hilos} hilos en {len(cables_carro())} grupos, "
          f"{len(compras)} compras, {sum(c for _, c, _ in REMACHES_DONDE)} remaches")


def nombre_pin(ref):
    dev, p = ref.split(".", 1)
    return f"{cx.DISPOSITIVOS[dev]['nombre']} · <b>{p}</b>"


def cuadro(medida):
    return f"<font color='{COLOR_REM[medida]}' size='14'>■</font>"


def openscad_png(salida, camara, defs):
    args = [str(ex.OPENSCAD)]
    for k, v in defs.items():
        args += ["-D", f"{k}={v}"]
    subprocess.run(args + ["-o", str(salida), "--render", "--imgsize=1500,1000", f"--camera={camara}",
                           "--colorscheme=Tomorrow", str(AQUI / "manual.scad")], capture_output=True)
    if not salida.exists():
        raise SystemExit(f"no se pudo renderizar {salida.name}")
    return salida


def renders():
    D_IMG.mkdir(parents=True, exist_ok=True)
    trabajos = [(D_IMG / f"paso_{i}.png", p[2], {"modo": '"paso"', "paso": i}) for i, p in enumerate(PASOS, start=1)]
    trabajos += [(D_IMG / f"pieza_{n}.png", cam, {"modo": '"pieza"', "cual": f'"{n}"',
                  "ocultar": "[" + ",".join(f'"{o}"' for o in oc) + "]"}) for n, (_, cam, oc) in PIEZAS_INFO.items()]
    trabajos += [(D_IMG / f"remaches_paso_{i}.png", cam, {"modo": '"paso_rem"', "paso": i}) for i, (cam, _) in REM_PASO.items()]
    trabajos += [(D_IMG / f"remaches_{n}.png", cam, {"modo": '"remaches"'})
                 for n, cam in (("arriba", "0,0,60,40,0,215,520"), ("abajo", ABAJO))]
    with ThreadPoolExecutor(4) as ej:
        list(ej.map(lambda t: openscad_png(*t), trabajos))


def main():
    comprobar()
    renders()
    diagramas.dibujar()
    est = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=est["Title"], fontSize=24, spaceAfter=6)
    h1 = ParagraphStyle("h", parent=est["Heading1"], fontSize=18, spaceAfter=4, textColor=colors.HexColor("#c25400"))
    h0 = ParagraphStyle("h0", parent=h1, fontSize=26, textColor=colors.HexColor("#1f3a5f"))
    h2 = ParagraphStyle("h2", parent=h1, fontSize=13, spaceBefore=4, spaceAfter=2, textColor=colors.HexColor("#1f3a5f"))
    cuerpo = ParagraphStyle("c", parent=est["BodyText"], fontSize=11, leading=15, spaceAfter=5)
    chico = ParagraphStyle("ch", parent=cuerpo, fontSize=10, leading=12, spaceAfter=2)
    nota = ParagraphStyle("n", parent=cuerpo, fontSize=10, textColor=colors.HexColor("#555555"))
    lleva = ParagraphStyle("l", parent=cuerpo, backColor=colors.HexColor("#fff1e6"), borderPadding=6, spaceBefore=8)
    ancho = landscape(A4)[0] - 30 * mm
    doc = SimpleDocTemplate(str(AQUI / "manual_armado.pdf"), pagesize=landscape(A4), leftMargin=15 * mm,
                            rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title="Manual de armado del carro", author="Proyecto final, grupo 7")
    nombre_tanda = {t: ex.NOMBRE_TANDA[t].split("_", 1)[1].replace("_", " ") for t in ex.NOMBRE_TANDA}
    h = []
    # Portada
    h += [Paragraph("Manual de armado del carro", titulo),
          Paragraph("Chasis impreso en PLA, uniones a presión. Planta de monedas, proyecto final grupo 7. "
                    "Ordenado por tandas de impresión: cada tanda trae sus piezas, dónde va cada una "
                    "y lo que ya se puede armar.", nota),
          Image(str(AQUI / "img" / "ensamble_iso.png"), width=185 * mm, height=185 * mm * 900 / 1400),
          Paragraph("<b>Orden recomendado:</b> tanda 0 (pieza de prueba), tanda 1, <b>tanda 5 (remaches y pasadores: "
                    "se necesitan desde el primer armado)</b>, tanda 2, tanda 3 y tanda 4. En los renders, "
                    "<font color='#c25400'><b>naranja</b></font> = lo que se agrega; gris = lo que ya está; lo "
                    "comprado va con su color.", cuerpo),
          Paragraph("<b>Cada paso tiene la misma forma:</b> qué hacer y qué lleva; dónde van sus remaches; qué "
                    "componentes se montan, cómo, y qué cables dejan. En el paso del piso 2 están todas las "
                    "conexiones, hilo por hilo (las mismas del firmware).", cuerpo),
          PageBreak()]
    # Lista de materiales (materiales.py): todo lo que lleva el carro
    h.append(Paragraph("Lista de materiales", h0))
    for k, (tit, enc, filas, nota_tabla) in enumerate(materiales.tablas()):
        anchos = {0: [62, 14, 14, 18, 18, 20, 30], 1: [120, 14, 26, 26, 40], 2: [44, 18, 24, 26, 120], 3: [90, 24, 120]}[k]
        anchos = [a * ancho / sum(anchos) for a in anchos]
        t = Table([[Paragraph(f"<b>{c}</b>", chico) for c in enc]] + [[Paragraph(str(c), chico) for c in f] for f in filas],
                  colWidths=anchos, repeatRows=1)
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff1e6")),
                               ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f2f2f2") if k < 2 else colors.white),
                               ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
        h += [Paragraph(tit, h1), t, Paragraph(nota_tabla, nota), Spacer(1, 4 * mm)]
    h.append(PageBreak())
    n_paso = 0
    for tanda in ORDEN_TANDAS:
        piezas = [n for n in ex.PIEZAS if ex.PIEZAS[n][1] == tanda and n in PIEZAS_INFO]
        h.append(Paragraph(f"Tanda {tanda}: {nombre_tanda[tanda]}", h0))
        h.append(Paragraph(f"Archivo: 3mf_sin_membrana/{ex.NOMBRE_TANDA[tanda]}.3mf. "
                           "Abajo, dónde va cada pieza de esta tanda en el carro.", nota))
        if tanda == 5:
            vistas = Table([[Image(str(D_IMG / f"remaches_{v}.png"), width=ancho / 2, height=ancho / 2 * 1000 / 1500)
                             for v in ("arriba", "abajo")], [Paragraph("Desde arriba", nota), Paragraph("Desde abajo", nota)]],
                           colWidths=[ancho / 2] * 2)
            h += [Paragraph("Todos los remaches en el carro. La flecha entra por la cabeza: es el lado por donde se "
                            "mete el remache; la uña sale del otro lado.", cuerpo), vistas, PageBreak(),
                  Paragraph("Tanda 5: medidas y dónde va cada una", h1)]
            filas = [[Paragraph("<b>Remache</b>", cuerpo), Paragraph("<b>Cuántos</b>", cuerpo), Paragraph("<b>Dónde va</b>", cuerpo)]]
            filas += [[Paragraph(f"{cuadro(a)} remache_{a.replace(',', '_')} (agarre {a} mm)", cuerpo), Paragraph(str(c), cuerpo),
                       Paragraph(d, cuerpo)] for a, c, d in REMACHES_DONDE]
            filas += [[Paragraph("pasador_tt", cuerpo), Paragraph("4", cuerpo),
                       Paragraph("cajas de los motores TT (2 por motor), a través del soporte del encoder", cuerpo)]]
            t = Table(filas, colWidths=[70 * mm, 25 * mm, ancho - 95 * mm])
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
                                   ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff1e6"))]))
            h += [Spacer(1, 4 * mm), t, Spacer(1, 4 * mm),
                  Paragraph("El número del remache es su agarre (lo que junta): no se cambian entre sí. Imprime dos "
                            "o tres de más de cada medida. Se ponen empujando hasta el clic; se sacan apretando las "
                            "patas con un alicate del lado de la uña.", cuerpo), PageBreak()]
            continue
        # donde va cada pieza: 2 por fila, 2 filas por pagina
        celdas = []
        for n in piezas:
            cant = ex.PIEZAS[n][0]
            celdas.append([Image(str(D_IMG / f"pieza_{n}.png"), width=92 * mm, height=92 * mm * 1000 / 1500),
                           Paragraph(f"<b>{n}</b>{f' (x{cant})' if cant > 1 else ''}: {PIEZAS_INFO[n][0]}", chico)])
        filas = [celdas[i:i + 2] for i in range(0, len(celdas), 2)]
        for k in range(0, len(filas), 2):
            bloque = [f + [""] * (2 - len(f)) for f in filas[k:k + 2]]
            t = Table(bloque, colWidths=[ancho / 2] * 2)
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
            if k:
                h.append(Paragraph(f"Tanda {tanda}: dónde va cada pieza (sigue)", h1))
            h += [t, PageBreak()]
        # pasos de armado de esta tanda
        for i, (t_, tit, _, que, lleva_txt) in enumerate(PASOS, start=1):
            if t_ != tanda:
                continue
            n_paso += 1
            texto = [Paragraph(f"{k}. {t}", cuerpo) for k, t in enumerate(que, start=1)]
            texto.append(Paragraph(f"<b>Lleva:</b> {lleva_txt}", lleva))
            tabla = Table([[Image(str(D_IMG / f"paso_{i}.png"), width=160 * mm, height=160 * mm * 1000 / 1500), texto]],
                          colWidths=[165 * mm, ancho - 165 * mm])
            tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
            h += [Paragraph(f"Tanda {tanda}, paso {n_paso}. {tit}", h1), Spacer(1, 2 * mm), tabla, PageBreak()]
            if i in REM_PASO:
                filas = [[Paragraph(f"{cuadro(m)} <b>{c} de {m}</b>", cuerpo), Paragraph(f"{d}, <b>{lado}</b>.", chico)]
                         for m, c, d, lado in REM_PASO[i][1]]
                ley = Table(filas, colWidths=[38 * mm, ancho - 205 * mm])
                ley.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                         ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#dddddd"))]))
                texto = [Paragraph("Cada color es una medida de remache. La flecha muestra por dónde se mete: "
                                   "empuja hasta el clic.", cuerpo), Spacer(1, 3 * mm), ley]
                tabla = Table([[Image(str(D_IMG / f"remaches_paso_{i}.png"), width=160 * mm, height=160 * mm * 1000 / 1500),
                                texto]], colWidths=[165 * mm, ancho - 165 * mm])
                tabla.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
                h += [Paragraph(f"Tanda {tanda}, paso {n_paso}. {tit}: dónde van los remaches", h1), Spacer(1, 2 * mm),
                      tabla, PageBreak()]
            if i in COMPONENTES_PASO:
                filas = [[Paragraph("<b>Componente</b>", chico), Paragraph("<b>Cómo se monta</b>", chico),
                          Paragraph("<b>Cables</b>", chico)]]
                filas += [[Paragraph(f"<b>{cx.DISPOSITIVOS[d]['nombre']}</b>", chico), Paragraph(como, chico),
                           Paragraph(cab, chico)] for d, como, cab in COMPONENTES_PASO[i]]
                tc = Table(filas, colWidths=[55 * mm, (ancho - 55 * mm) * 0.42, (ancho - 55 * mm) * 0.58], repeatRows=1)
                tc.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
                                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fa"))]))
                h += [Paragraph(f"Tanda {tanda}, paso {n_paso}. {tit}: componentes y cables", h1), tc, PageBreak()]
            if i == PASO_CONEXIONES:
                h += [Paragraph(f"Tanda {tanda}, paso {n_paso}. Conexiones del carro, hilo por hilo", h1),
                      Paragraph("Con el interruptor APAGADO. Cada fila es un hilo: color, de dónde sale, a dónde llega y "
                                "para qué. En la GVS: <b>S</b> = señal del GPIO, <b>V</b> = 3,3 V, <b>G</b> = GND. "
                                "Calibre: 22 AWG en batería y motores; el resto, Dupont hembra-hembra (26 AWG).", cuerpo),
                      Image(str(D_IMG / "conex_general.png"), width=150 * mm, height=150 * mm * 8 / 11.3),
                      Paragraph("En cada página que sigue: a la izquierda, dónde está cada componente y por dónde pasa "
                                "su mazo de cables (los de debajo del chasis suben por el pasacables marcado); a la "
                                "derecha, el esquema pin a pin, cada hilo con su color. Abajo, la misma información en "
                                "tabla.", nota), PageBreak()]
                for c in cables_carro():
                    filas = [[Paragraph(f"<b>{e}</b>", chico) for e in ("", "De", "A", "Función")]]
                    filas += [[Paragraph(f"<font color='{h_['color']}' size='14'>■</font>" if h_["color"] != cx.BLANCO else "<font size='14'>□</font>", chico),
                               Paragraph(nombre_pin(h_["de"]), chico), Paragraph(nombre_pin(h_["a"]), chico),
                               Paragraph(h_["funcion"], chico)] for h_ in c["hilos"]]
                    resto = ancho - 8 * mm
                    tk = Table(filas, colWidths=[8 * mm, resto * 0.38, resto * 0.38, resto * 0.24])
                    tk.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
                                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fa")),
                                            ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
                    calibre = "22 AWG" if c["id"] in GRUESOS else "Dupont 26 AWG"
                    from PIL import Image as Pil
                    img = D_IMG / f"conex_{c['id']}.png"
                    w, hh = Pil.open(img).size
                    alto = min(115 * mm, ancho * hh / w)
                    h += [Paragraph(f"Conexión: {c['nombre']} ({calibre})", h2), Image(str(img), width=alto * w / hh, height=alto),
                          tk, PageBreak()]
                h += [Paragraph("Antes de encender", h2)] + [Paragraph(f"• {x}", cuerpo) for x in (
                    "Con el multímetro en continuidad: B+ y B− NO deben sonar entre sí, ni +7,4 V con GND.",
                    "En el plug del jack: el centro es + (rojo) y el exterior GND (negro); revísalo antes de enchufar.",
                    "El ECHO del HC-SR04 llega al G23 por el divisor (nunca directo).",
                    "Ningún cable roza las ruedas ni cuelga hacia el piso; los sobrantes, amarrados con bridas.",
                    "Enciende con el interruptor: el LED de la GVS prende y los motores no deben moverse solos.")]
                h.append(PageBreak())
    doc.build(h[:-1])
    print("manual:", AQUI / "manual_armado.pdf")


if __name__ == "__main__":
    main()
