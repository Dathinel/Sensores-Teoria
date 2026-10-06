"""Prueba de estres de atlas_pybullet.py, sin ventana (PyBullet DIRECT).

Mide lo que se reporta en el README, con y sin asistente de equilibrio:
  1. de pie quieto 20 s,
  2. caminando hacia adelante 15 s (distancia y si se cae),
  3. caminando con arranques y frenadas (5 tandas de 3 s caminando + 1 s quieto),
  4. girando en el lugar 8 s (grados) y caminando hacia atras 8 s,
  5. las poses (saludar, agacharse, brazos arriba, de pie), 4 s cada una,
  6. "ponerlo de pie" despues de tirarlo con un empujon, 3 veces, y que
     quede de pie 5 s SIN asistente,
  7. el flanco: la tecla A repetida 10 veces (sostenida 0,5 s) conmuta el
     asistente UNA sola vez.

Todo pasa por las mismas funciones que usa la ventana (procesar_tecla /
simular), simulando el protocolo del ESP32: una linea "TECLA:x" cada 50 ms.

    entorno\\Scripts\\python punto-c-atlas\\probar_atlas.py

Tarda unos 3 a 4 minutos. No abre ventanas.
"""

import math
import sys
import time

import pybullet as p

sys.dont_write_bytecode = True  # no dejar __pycache__ en la carpeta del punto
import atlas_pybullet as A

VENTANA = 0.1  # s: cada cuanto se revisa si se cayo


def correr(e, segundos, tecla="-"):
    """Simula `segundos` con la tecla sostenida y devuelve (segundo en que
    se cayo o None, distancia horizontal recorrida en cm)."""
    x0, y0, _ = A.leer_estado(e)["pos"]
    caida = None
    for k in range(round(segundos / VENTANA)):
        A.simular(e, VENTANA, tecla)
        if A.leer_estado(e)["caido"]:
            caida = round((k + 1) * VENTANA, 1)
            break
    x, y, _ = A.leer_estado(e)["pos"]
    return caida, 100 * math.hypot(x - x0, y - y0)


def texto(caida, total):
    return f"se cae a los {caida} s" if caida is not None else f"de pie los {total} s"


def bloque(e, con_asistente):
    """Pruebas 1 a 5 con el asistente prendido o apagado."""
    nombre = "CON asistente" if con_asistente else "SIN asistente"
    # Cada resultado se imprime apenas se mide (no todo junto al final del bloque): asi la app del
    # tema 9 va dibujando la grafica con/sin asistente prueba por prueba mientras corre.
    print(f"\n=== {nombre} ===", flush=True)

    class Filas(list):
        def append(self, fila):
            super().append(fila)
            print(f"  {fila[0]:<50} {fila[1]}", flush=True)

    filas = Filas()

    def preparar():
        A.reiniciar_todo(e)
        A.asistente(e, con_asistente)

    preparar()
    caida, _ = correr(e, 20)
    filas.append(("De pie quieto 20 s", texto(caida, 20)))

    preparar()
    caida, cm = correr(e, 15, "8")
    filas.append(("Caminar adelante 15 s (tecla 8)", f"{texto(caida, 15)}, avanzo {cm:.0f} cm"))

    preparar()
    caida_total, cm_total, t = None, 0.0, 0.0
    for _ in range(5):
        caida, cm = correr(e, 3, "8")
        cm_total += cm
        if caida is not None:
            caida_total = round(t + caida, 1)
            break
        t += 3
        caida, _ = correr(e, 1, "-")
        if caida is not None:
            caida_total = round(t + caida, 1)
            break
        t += 1
    filas.append(("Arrancar/frenar 5 veces (3 s con 8, 1 s suelta)",
                  f"{texto(caida_total, 20)}, avanzo {cm_total:.0f} cm"))

    preparar()
    yaw0 = A.leer_estado(e)["yaw"]
    caida, _ = correr(e, 8, "4")
    giro = (A.leer_estado(e)["yaw"] - yaw0 + 180) % 360 - 180
    filas.append(("Girar a la izquierda 8 s (tecla 4)", f"{texto(caida, 8)}, giro {giro:.0f} grados"))

    preparar()
    caida, cm = correr(e, 8, "2")
    filas.append(("Caminar atras 8 s (tecla 2)", f"{texto(caida, 8)}, retrocedio {cm:.0f} cm"))

    preparar()
    resultados = []
    for tecla, pose in (("C", "saludar"), ("D", "agacharse"), ("#", "brazos arriba"), ("5", "de pie")):
        A.procesar_tecla(e, tecla)
        caida, _ = correr(e, 4)
        resultados.append(f"{pose}: {'cae a los ' + str(caida) + ' s' if caida else 'ok'}")
        if caida:
            break
        A.procesar_tecla(e, "-")
    filas.append(("Poses seguidas, 4 s c/u (C, D, #, 5)", "; ".join(resultados)))

    return list(filas)


def prueba_poner_de_pie(e):
    """Lo tira con un empujon lateral (asistente OFF) y lo levanta con B,
    tres veces. Despues de B el asistente vuelve a OFF: se exige que quede
    de pie 5 s solo."""
    print("\n=== Ponerlo de pie (B) despues de tirarlo, 3 veces ===")
    A.reiniciar_todo(e)
    ok = 0
    for intento in range(1, 4):
        A.asistente(e, False)
        # empujon: 1500 N de costado durante 0,2 s a la altura del pecho
        for _ in range(round(0.2 / A.PASO_FISICA)):
            pos = A.leer_estado(e)["pos"]
            p.applyExternalForce(e.atlas, -1, [0, 1500, 0], [pos[0], pos[1], pos[2] + 0.4],
                                 p.WORLD_FRAME)
            A.paso(e)
        correr(e, 3)
        tirado = A.leer_estado(e)["caido"]
        A.procesar_tecla(e, "B")
        A.procesar_tecla(e, "-")
        caida, _ = correr(e, 5)
        quedo = caida is None and not e.asistente
        ok += quedo
        print(f"  intento {intento}: tirado={tirado}, tras B asistente="
              f"{'ON' if e.asistente else 'OFF'}, {texto(caida, 5)}")
    print(f"  -> {ok}/3 quedaron de pie 5 s sin asistente")
    return ok


def prueba_flanco(e):
    print("\n=== Flanco: tecla A sostenida (10 lineas TECLA:A) ===")
    A.reiniciar_todo(e)
    antes = e.asistente
    cambios = 0
    for _ in range(10):
        previo = e.asistente
        A.procesar_tecla(e, "A")
        cambios += e.asistente != previo
        for _ in range(round(A.INTERVALO_TECLA / A.PASO_FISICA)):
            A.paso(e)
    A.procesar_tecla(e, "-")
    print(f"  asistente antes={antes}, despues={e.asistente}, conmutaciones={cambios}")
    return cambios


def main():
    inicio = time.time()
    e = A.crear_mundo(p.DIRECT)
    print(f"Atlas cargado: {len(e.juntas)} juntas, masa total {e.masa:.1f} kg")
    bloque(e, True)
    bloque(e, False)
    prueba_poner_de_pie(e)
    prueba_flanco(e)
    print(f"\nTiempo total: {time.time() - inicio:.0f} s")
    p.disconnect()


if __name__ == "__main__":
    main()
