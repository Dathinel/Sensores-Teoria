"""Prueba automatica del punto b) en modo DIRECT (sin ventana, sin ESP32).

    entorno\\Scripts\\python punto-b-brazo-tipo-baxter\\probar_baxter.py

(desde la carpeta del taller). Tarda menos de un minuto. Comprueba:
  1. con cada brazo, la IK + los motores llevan la pinza a menos de 2 cm
     de 3 objetivos dentro de su caja de trabajo;
  2. la demo D (con cada brazo) deja el cubo a menos de 3 cm del destino,
     despues de haberlo levantado mas de 5 cm;
  3. ningun link de los brazos atraviesa el torso ni el pedestal durante
     las demos (distancia minima con getClosestPoints);
  4. la entrada serial: "TECLA:*" repetida 10 veces (una tecla sostenida
     llega asi) cambia de brazo UNA sola vez (flanco), y "TECLA:8"
     repetida 10 veces mueve la pinza 10 pasos de jog (y "7" sostenida no
     baja el objetivo por debajo de la caja de trabajo).
Ademas mide, solo como dato, si los dedos solos (sin constraint) levantan
el cubo. Imprime todas las cifras y termina con codigo 1 si algo falla.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pybullet as p

import brazo_pybullet as bz

fallas = []


def revisar(condicion, texto):
    print(("  OK    " if condicion else "  FALLA ") + texto)
    if not condicion:
        fallas.append(texto)


estado = bz.crear_mundo(p.DIRECT)
robot = estado.robot

# ----------------------------------------------------------------------
# Registro durante la simulacion: se reemplaza bz.avanzar por una version
# que, ademas de simular, anota la altura maxima del cubo y (cada 10
# pasos) la distancia minima entre los brazos y el torso/pedestal.
# ----------------------------------------------------------------------
nombre_link = {i: p.getJointInfo(robot, i)[12].decode() for i in range(p.getNumJoints(robot))}
cuerpo_fijo = [estado.nombres["torso_t0"], estado.nombres["pedestal_fixed"]]   # links "torso" y "pedestal"
# Links de cada brazo con colision, desde el antebrazo ("lower_elbow")
# hasta los dedos. Los del hombro y el brazo superior (upper/lower
# shoulder, upper_elbow) quedan aparte: estan atornillados junto al torso
# y la forma de colision del torso es una envolvente convexa (un "globo"
# alrededor de la malla) que ya los toca en la pose de home, sin que se
# vea ningun cruce. Esos se miden igual, pero comparados con su valor en
# home (ver "brazo superior" abajo).
SUPERIORES = ("upper_shoulder", "lower_shoulder", "upper_elbow", "upper_elbow_visual")
links_brazo, links_superior = {}, {}
for nombre, brazo in estado.brazos.items():
    prefijo = "left" if nombre == "izquierdo" else "right"
    letra = prefijo[0]
    propios = [i for i, n in nombre_link.items()
               if (n.startswith(prefijo + "_") or n.startswith(letra + "_gripper"))
               and p.getCollisionShapeData(robot, i)]
    links_superior[nombre] = [i for i in propios if nombre_link[i].endswith(SUPERIORES[2:])]
    links_brazo[nombre] = [i for i in propios if not nombre_link[i].endswith(SUPERIORES)]


def distancia_minima(links, otros, alcance=1.0):
    """(distancia, par de links) mas chica entre dos grupos de links del
    robot. getClosestPoints mide la geometria aunque la auto-colision este
    apagada (como en el demo del profesor), y negativo = se meten."""
    mejor = (1e9, None)
    for a in links:
        for b in otros:
            for punto in p.getClosestPoints(robot, robot, alcance, a, b):
                if punto[8] < mejor[0]:
                    mejor = (punto[8], (nombre_link[a], nombre_link[b]))
    return mejor


superior_home = {n: distancia_minima(l, cuerpo_fijo)[0] for n, l in links_superior.items()}
registro = {"z_max": -1e9, "dist_min": 1e9, "par_min": None, "pasos": 0,
            "sup_min": dict(superior_home), "entre_brazos": 1e9}
avanzar_original = bz.avanzar


def avanzar_con_registro(est, pasos):
    for _ in range(pasos):
        p.stepSimulation()
        registro["pasos"] += 1
        registro["z_max"] = max(registro["z_max"], p.getBasePositionAndOrientation(est.cubo)[0][2])
        if registro["pasos"] % 10 == 0:
            for nombre, links in links_brazo.items():
                d, par = distancia_minima(links, cuerpo_fijo, 0.05)
                if d < registro["dist_min"]:
                    registro["dist_min"], registro["par_min"] = d, par
                d, _ = distancia_minima(links_superior[nombre], cuerpo_fijo, 0.2)
                registro["sup_min"][nombre] = min(registro["sup_min"][nombre], d)
            d, _ = distancia_minima(links_brazo["izquierdo"], links_brazo["derecho"], 0.05)
            registro["entre_brazos"] = min(registro["entre_brazos"], d)


bz.avanzar = avanzar_con_registro

# ----------------------------------------------------------------------
print("\n1) IK + motores: error final de la pinza (objetivo -> posicion real)")
objetivos = {
    "izquierdo": [(0.55, 0.35, 0.10), (0.68, 0.10, -0.12), (0.62, -0.15, bz.Z_AGARRE + 0.02)],
    "derecho": [(0.55, -0.35, 0.10), (0.68, -0.10, -0.12), (0.62, 0.15, bz.Z_AGARRE + 0.02)],
}
for nombre, puntos in objetivos.items():
    for punto in puntos:
        error = bz.mover_a(estado, nombre, punto, 480)
        revisar(error < 0.02, f"brazo {nombre:9s} -> {punto[0]:.2f} {punto[1]:+.2f} {punto[2]:+.3f}: "
                              f"error {error * 100:.2f} cm (< 2 cm)")
    bz.mover_a(estado, nombre, bz.HOME[nombre], 480)

# ----------------------------------------------------------------------
print("\n2) Demo D (coger el cubo del origen y dejarlo en el destino)")
for nombre in ("izquierdo", "derecho"):
    bz.reponer_cubo(estado)
    bz.avanzar(estado, 60)
    estado.activo = nombre
    z_inicial = p.getBasePositionAndOrientation(estado.cubo)[0][2]
    registro["z_max"] = z_inicial
    pasos_antes = registro["pasos"]
    bz.ejecutar_demo(estado)
    bz.avanzar(estado, 120)   # que termine de asentarse
    final = p.getBasePositionAndOrientation(estado.cubo)[0]
    distancia = math.dist(final[:2], bz.POS_DESTINO)
    subida = registro["z_max"] - z_inicial
    duracion = (registro["pasos"] - pasos_antes - 120) / bz.PASOS_POR_SEGUNDO
    revisar(distancia < 0.03, f"brazo {nombre}: cubo a {distancia * 100:.2f} cm del destino (< 3 cm)")
    revisar(subida > 0.05, f"brazo {nombre}: el cubo subio {subida * 100:.1f} cm (> 5 cm)")
    revisar(abs(final[2] - bz.Z_CUBO) < 0.005, f"brazo {nombre}: el cubo quedo apoyado en la mesa "
                                                f"(z = {final[2]:.4f}, esperado {bz.Z_CUBO:.4f})")
    print(f"        duracion de la demo: {duracion:.1f} s de simulacion")
    bz.mover_a(estado, nombre, bz.HOME[nombre], 360)
estado.activo = "izquierdo"

print("\n3) Torso y pedestal durante todo lo anterior")
if registro["par_min"] is None:
    revisar(True, "antebrazos, munecas y pinzas: nunca a menos de 5 cm del torso ni del pedestal")
else:
    revisar(registro["dist_min"] > 0, f"distancia minima antebrazo/pinza-(torso/pedestal): "
                                      f"{registro['dist_min'] * 100:.1f} cm entre {registro['par_min']}")
for nombre in links_superior:
    print(f"        brazo superior {nombre}: contra la envolvente del torso {superior_home[nombre] * 100:.1f} cm en "
          f"home, minimo {registro['sup_min'][nombre] * 100:.1f} cm en las demos")
entre = registro["entre_brazos"]
print("        entre los dos brazos: " + ("nunca a menos de 5 cm" if entre > 1e8 else f"minimo {entre * 100:.1f} cm"))
contactos_mesa = [c for c in p.getContactPoints(robot, estado.mesa)]
print(f"        contactos brazo-mesa al final: {len(contactos_mesa)}")

# ----------------------------------------------------------------------
print("\n4) Entrada serial simulada (procesar_linea, como si llegara del ESP32)")
bz.avanzar = avanzar_original


def alimentar(lineas, pasos_entre=12):
    """Una linea cada 50 ms (12 pasos de fisica), como manda el firmware."""
    for linea in lineas:
        bz.procesar_linea(estado, linea)
        bz.avanzar(estado, pasos_entre)


activo_antes = estado.activo
alimentar(["TECLA:-"] + ["TECLA:*"] * 10 + ["TECLA:-"])
revisar(estado.activo != activo_antes,
        f"'*' sostenida 10 lineas: {activo_antes} -> {estado.activo} (cambio UNA vez, por flanco)")
alimentar(["TECLA:*"] * 10 + ["TECLA:-"])
revisar(estado.activo == activo_antes, f"otro toque de '*': vuelve a {estado.activo}")

brazo = estado.activo
bz.mover_a(estado, brazo, (0.60, 0.10, 0.0), 480)
antes = bz.posicion_efector(estado, brazo)
objetivo_antes = estado.objetivo[brazo]
alimentar(["TECLA:8"] * 10 + ["TECLA:-"])
bz.avanzar(estado, 240)
despues = bz.posicion_efector(estado, brazo)
avance_objetivo = estado.objetivo[brazo][1] - objetivo_antes[1]
avance_real = despues[1] - antes[1]
revisar(abs(avance_objetivo - 10 * bz.PASO_JOG) < 1e-9,
        f"'8' sostenida 10 lineas: el objetivo avanzo {avance_objetivo * 100:.1f} cm en Y "
        f"(= 10 pasos de {bz.PASO_JOG * 100:.1f} cm)")
revisar(abs(avance_real - 10 * bz.PASO_JOG) < 0.01,
        f"la pinza real avanzo {avance_real * 100:.1f} cm en Y (en X y Z se movio "
        f"{abs(despues[0] - antes[0]) * 100:.2f} y {abs(despues[2] - antes[2]) * 100:.2f} cm)")
z_antes = estado.objetivo[brazo][2]
alimentar(["TECLA:7"] * 60)
revisar(abs(estado.objetivo[brazo][2] - bz.Z_AGARRE) < 1e-9,
        f"'7' sostenida 60 lineas: el objetivo bajo de z = {z_antes:.3f} y se detuvo en el piso "
        f"de la caja, z = {estado.objetivo[brazo][2]:.4f} (no atraviesa la mesa)")

# ----------------------------------------------------------------------
print("\n5) Solo como dato: los dedos SIN constraint, levantan el cubo?")
bz.reponer_cubo(estado)
bz.mover_a(estado, brazo, bz.HOME[brazo], 360)
x, y = bz.POS_ORIGEN
bz.mover_pinza(estado, brazo, abierta=True)
bz.mover_a(estado, brazo, (x, y, bz.Z_VIAJE), 360)
bz.mover_a(estado, brazo, (x, y, bz.Z_AGARRE), 300)
bz.mover_pinza(estado, brazo, abierta=False)
bz.avanzar(estado, 120)
z0 = p.getBasePositionAndOrientation(estado.cubo)[0][2]
bz.mover_a(estado, brazo, (x, y, bz.Z_VIAJE), 360)
z_sin = p.getBasePositionAndOrientation(estado.cubo)[0][2] - z0
bz.mover_a(estado, brazo, (bz.POS_DESTINO[0], bz.POS_DESTINO[1], bz.Z_VIAJE), 360)
c = p.getBasePositionAndOrientation(estado.cubo)[0]
print(f"        al subir la pinza 19 cm, el cubo subio {z_sin * 100:.1f} cm; tras el viaje quedo en "
      f"({c[0]:.3f}, {c[1]:.3f}, {c[2]:.3f})")

print()
if fallas:
    print(f"{len(fallas)} prueba(s) fallaron.")
    sys.exit(1)
print("Todas las pruebas pasaron.")
