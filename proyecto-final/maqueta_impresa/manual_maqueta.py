"""Manual de armado de la maqueta impresa (usuario, 2026-10-24: "un manual inspirado en el que ya existe"), con la
misma forma que el del carro (chasis_impreso/manual.py): por cada paso, lo que se agrega en naranja sobre lo que ya
esta en gris, que piezas lleva y en que tanda se imprimen, sus remaches por medida, lo comprado que se monta y como,
y los cables hilo por hilo de lo que se monta en ese paso (sim/conexiones.py: el mismo conexionado del firmware).

comprobar() revisa que cada pieza impresa, cada remache y cada dispositivo de la planta salga en un paso.
Uso: python manual_maqueta.py   (despues de revisar.py y exportar.py) -> manual_maqueta.pdf, renders en img/manual/
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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

POSTES = ("t_F6-L", "t_V2-L", "t_V4-L", "t_C1-L", "t_C2-L", "t_C3-L", "t_C4-L", "t_K1-L")

# (titulo, prefijo de sus piezas o None para la estructura, camara "x,y,z,rx,ry,rz,dist", que hacer, que lleva comprado,
#  dispositivos de la planta que se montan)
PASOS = [
    ("Piso: la base que amarra todo", None, "130,-150,0,55,0,320,1500", [
        "Arma el piso sobre el MDF: nodos del piso (los de abajo plano) y tubos entre ellos. Cada tubo entra 22 mm en "
        "su cajera y se traba con 2 remaches de 4,2 por los costados del nodo (empuja hasta el clic).",
        "Los tramos largos van en dos o tres partes unidas con un empalme (manguito con tope al medio) y 4 remaches.",
        "Antes de remachar, cuadra el piso: los nodos tienen que quedar planos y las líneas a escuadra.",
        "La canaleta tiene su propio marco de piso (C1-C4, M1, M2): se arma igual y queda aparte.",
    ], "Nada comprado. Tablero de MDF de 600 × 450 como piso (opcional).", []),
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
        "lado -y; del lado +y, el taco de cada lateral llena el hueco hasta el poste de x 30 y la columna de x 315.",
        "Corta 3 mm del extremo -y de los separadores de la banda (dejan pasar el vaso que baja a la canaleta).",
        "Rodillos con sus ejes Ø8: 608 en las laterales y KFL08 del lado del motor; NEMA 17 en su placa, sobre los 4 "
        "postes huecos de la lateral -y, con el acople al rodillo de x 0. El motor NO apoya directo en la placa: lleva 4 "
        "separadores de nailon de 3 mm en sus M3 (aire entre la brida y el PLA: el motor se calienta; ver esfuerzos.md).",
        "Tacos de casilla: dos mitades pegadas a cada lado de cada separador.",
        "Panel de luz (dos mitades remachadas) a las columnas: la tira LED va sobre cinta de aluminio pegada al marco "
        "(reparte el calor) y alimentada a MEDIA potencia (resistencia en serie o dimmer): pegada directo al PLA y a "
        "plena potencia lo calienta hasta 45-65 °C. Cortina VL53L0X en el poste de (315, -152,5); la webcam de vasos "
        "en su placa sobre el poste de (160, -422); la bandeja de rechazo suelta en el piso.",
    ], "Banda 400 × 75 × 2 con 7 separadores, 2 rodillos Ø22 × 79 con ejes Ø8, 3 rodamientos 608 y 1 KFL08, acople Ø19 × 20, "
       "NEMA 17 con 4 separadores de nailon de 3 mm, webcam 720p (tornillo de 1/4\"), VL53L0X, tira LED de 5 V (2 tramos) "
       "con cinta de aluminio y resistencia o dimmer.",
     ["motor_vasos", "vl53_cortina", "panel_luz", "cam_vasos"]),
    ("Almacén de monedas (carrusel)", "alm_", "100,-70,300,55,0,330,620", [
        "Puente del motor colgado de la viga con sus dos horquillas (6 remaches); 28BYJ-48 sobre el puente (2 remaches "
        "por las pestañas).",
        "Columnas del puente a la placa fija (la 2 lleva el módulo Hall en su ranura); la placa fija con el 608 de "
        "abajo; la tolva remachada bajo la placa fija, con el SG90 del obturador en su bolsillo.",
        "Eje de acero Ø8 a presión en el cubo del disco (y pegado); los 6 tubos (tambor) bajo el disco con 3 remaches; "
        "imán en su alojamiento a 0°; acople rígido al 28BYJ-48.",
        "Embudo de carga a las columnas; el obturador a presión en la estría del SG90.",
        "Gira el carrusel a mano: una vuelta entera sin rozar nada.",
    ], "Eje de acero Ø8, rodamiento 608, acople rígido Ø12 × 16, 28BYJ-48 con ULN2003, SG90, módulo KY-003 e imán de 6 × 3.",
     ["motor_carrusel", "hall", "servo_obturador"]),
    ("Tapas, prensa y empujador", "tap_", "260,-90,260,55,0,330,800", [
        "Colgante del tubo de tapas a la viga; abrazaderas al colgante; tubo de tapas (cabezal hacia abajo) colgado del "
        "hombro de la abrazadera de abajo; SG90 invertido en su placa y dedos A y B en las ranuras del cabezal.",
        "Prensa: placa a la cara -y de la viga, MG996R entre sus separadores, leva al cuerno de disco, buje guía; "
        "vástago Ø8 con el resorte, la horquilla con su rodillo arriba y el plato abajo (a presión y pegados).",
        "Empujador: soporte en la cara +x de la columna de x 315 con el bloque de las varillas Ø8; carro con la paleta "
        "sobre las varillas; placa del MG996R colgada del bloque; manivela y biela con sus pernos M4.",
        "Sensor interior VL53L0X en su porta, colgado de la viga en x 40.",
        "Mueve cada mecanismo a mano en todo su recorrido antes de conectar los servos.",
    ], "SG90, 2 MG996R con cuerno de disco, vástago Ø8 × 79, 2 varillas Ø8 × 102,5, resorte Ø15 × 30, eje Ø3 del rodillo, "
       "2 pernos M4, goma de la paleta, VL53L0X, tapas Ø78.",
     ["servo_tapas", "servo_prensa", "servo_empujador", "vl53_interior"]),
    ("Cinta de monedas y compuerta E4", "mon_", "0,0,420,55,0,330,800", [
        "Bancada entre los rieles con las guías laterales (8 remaches desde arriba); platinas de los M18 bajo la bancada.",
        "Bloques del rodillo motriz (el +y es también la jaula del NEMA 17) y del tensor, con los rodamientos 608; los "
        "ejes Ø8 pasan por los agujeros de los rieles. El NEMA 17 va con 4 separadores de nailon de 3 mm en sus M3: la "
        "brida no toca el PLA (el motor se calienta; ver esfuerzos.md).",
        "Placas colgantes de los rodillos de retorno A, B y C; banda puesta en los cinco rodillos.",
        "Compuerta E4: placa bajo los labios de los bloques del tensor, embudo, SG90 y aleta; canal A al embudo de carga "
        "del almacén y canal B (dos tramos) a la bandeja de rechazo, con su soporte al poste de la cámara.",
        "Columna del FC-51 en el riel -y; abrazadera de la cámara en la punta del brazo, con la webcam y el anillo LED.",
    ], "Banda 200 × 55 × 2, 5 rodillos Ø22 × 59 con ejes Ø8, 4 rodamientos 608, NEMA 17 con acople Ø19 × 25, sensor "
       "capacitivo M18 × 68 y sensor inductivo M18 × 60 con sus tuercas, FC-51, webcam 1080p con anillo LED, SG90.",
     ["motor_monedas", "presencia", "capacitivo", "inductivo", "servo_desvio", "cam_cenital", "anillo"]),
    ("Canaleta de entrega y muelle del carro", "can_", "360,-350,120,55,0,330,950", [
        "Cabezales en las puntas de los cuatro postes (2 remaches cada uno); varillas Ø4 con PTFE en las cunas, "
        "apretadas con los prisioneros impresos (si una se suelta, una gota de cianoacrilato en C1/C2).",
        "Soporte del escape al tubo C4-M2; SG90 en su cuna con los tornillos de su kit; balancín de dos dedos al brazo "
        "del servo.",
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


def comprobar(piezas, rem, pasos, rpasos):
    assert set(pasos) == set(piezas), "hay piezas sin paso"
    assert len(rpasos) == len(rem), "hay remaches sin paso"
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


def main():
    piezas, rem, _ = R.listas()
    datos = json.loads((AQUI / "piezas.json").read_text(encoding="utf-8"))
    tanda = {f["pieza"]: ", ".join(f.get("tandas", [])) for f in datos["piezas"]}
    est = estructura_por_altura(piezas)
    pasos = {n: paso_de_pieza(n, est) for n in piezas}
    import numpy as np
    mallas = {n: R.ex_carro.leer_stl(R.CACHE / "ens" / f"{n}.stl") for n in piezas}
    cajas = {n: R.caja(m) for n, m in mallas.items()}
    cerca = lambda r: {n: m for n, m in mallas.items() if np.all(cajas[n][0] - 25 < r[2]) and np.all(cajas[n][1] + 25 > r[2])}
    rpasos = [paso_de_remache(r, cerca(r), pasos) for r in rem]
    comprobar(piezas, rem, pasos, rpasos)
    with ThreadPoolExecutor(4) as ej:
        imgs = list(ej.map(lambda k: render(k, piezas, pasos, rem, rpasos), range(len(PASOS))))

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
                   "remaches impresos (sin perfil de aluminio, sin escuadras, sin tornillos salvo los de los kits de los servos).", nota),
         Image(str(AQUI / "img" / "maqueta_iso.png"), width=170 * mm, height=170 * mm * 1300 / 1800),
         Paragraph(f"<b>Material:</b> {datos['total_gramos'] / 1000:.2f} kg de PLA en {len(datos['tandas'])} tandas "
                   f"(≈ {datos['total_horas']:.0f} h de impresora). Detalle en material.md; archivos en 3mf/ (una cama cada uno) y "
                   "stl/ (una pieza cada uno, ya girada para imprimir).", cuerpo),
         Paragraph("<b>Cómo leer cada paso:</b> en naranja lo que se agrega, en gris lo que ya está, en rojo los remaches del paso "
                   "y lo comprado con su color. Todo remache es de un agarre medido en el ensamble (revisar.py): no se cambian "
                   "entre medidas. Se meten empujando hasta el clic.", cuerpo), PageBreak()]
    for k, (tit, pre, cam, que, lleva_txt, dispositivos) in enumerate(PASOS):
        mias = sorted(n for n in piezas if pasos[n] == k)
        texto = [Paragraph(f"{i}. {t}", cuerpo) for i, t in enumerate(que, start=1)]
        texto.append(Paragraph(f"<b>Lleva comprado:</b> {lleva_txt}", lleva))
        t = Table([[Image(str(imgs[k]), width=165 * mm, height=165 * mm * 1100 / 1600), texto]],
                  colWidths=[170 * mm, ancho - 170 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        h += [Paragraph(f"Paso {k + 1}. {tit}", h1), t, PageBreak()]
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
        h += [Paragraph(f"Paso {k + 1}. {tit}: piezas y remaches", h1), doble, PageBreak()]
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
        "Con la red desconectada: continuidad entre los GND de la bornera y el del ESP32 fijo; ningún +12/+6/+5 con GND.",
        "Gira a mano el carrusel, la banda de monedas y la de vasos, y mueve cada mecanismo en todo su recorrido: nada roza.",
        "Primer encendido sin servos conectados; después uno por uno desde la app.")]
    doc.build(h)
    print("manual:", AQUI / "manual_maqueta.pdf")


if __name__ == "__main__":
    main()
