"""Graba una corrida completa para el modo demo del visor 3D.

El visor (app/visor3d/) normalmente le pregunta el estado al supervisor en
vivo. Para poder mostrarlo SIN el PC -- por ejemplo publicado en una
pagina, o en la sustentacion si algo falla -- este script corre la planta
sin ventana y guarda, tick por tick, exactamente lo mismo que el supervisor
publicaria en /api/estado. El visor lo reproduce en bucle si se abre con
?demo o si no encuentra servidor detras.

Guion de la demo (escenario prueba_completa, lotes de 5):
- dos veces una mano en la casilla de carga (ya vienen en el escenario);
- tick 6: cambian el vaso de llenado por una figura (no debe recibir nada);
- tick 12: el proximo vaso trae algo adentro (lo detecta el sensor del interior del vaso);
- ticks 22-27: una mano en la zona de tapa/prensa (cortina de seguridad);
- tick 36: una mano entra a media altura y se lleva un vaso (cortina + camara);
- al terminar: "embalar lo guardado" para empacar los tubos incompletos.

Uso, desde proyecto-final/:
    python -m app.grabar_demo
Escribe app/visor3d/demo/{geometria,pasos,grabacion}.json.
"""

from __future__ import annotations

import json

import yaml

from app import configuracion
from app.rutas import DOCS, RAIZ, VISOR
from sim.carga_escenarios import listar_escenarios
from sim.geometria import geometria_completa
from sim.mundo import EscenaEstacion
from sim.planta import GUION_SABOTAJES, LOTE_DEMO, crear_planta_simulada

DESTINO = VISOR / "demo"
ESCENARIO = "prueba_completa"
CUADROS_FINALES = 8  # el ultimo estado se sostiene un rato antes de repetir


def grabar() -> list[dict]:
    parametros = configuracion.cargar_parametros()
    escena = EscenaEstacion()
    try:
        # Igual que el supervisor (cada sensor con su error individual), pero el carro sin
        # los errores de config y con el lote de la demo.
        planta = crear_planta_simulada(escena, parametros, ESCENARIO, errores_carro=False,
                                       monedas_por_vaso=LOTE_DEMO)
        t = parametros["tiempos_ms"]
        comun = {"escenario": ESCENARIO, "escenarios_disponibles": listar_escenarios(), "backend": "sim",
                 "monedas_por_vaso": LOTE_DEMO, "velocidad": 1.0,
                 # la demo se reproduce al ritmo real de la cinta
                 "ciclo_ms": t["avance_casilla_monedas"] + t["pausa_casilla_monedas"],
                 "avance_ms": t["avance_casilla_monedas"]}
        cuadros = [dict(planta.estado(), linea="corriendo", eventos_tick=planta.eventos_arranque, **comun)]
        embalo_parciales = False
        ya_entrego = False
        while planta.ticks < 1200:
            if planta.ticks in GUION_SABOTAJES:
                getattr(planta, GUION_SABOTAJES[planta.ticks])()
            eventos = planta.paso()
            # Con el carro fisico: la demo termina cuando el carro vuelve al
            # muelle despues de entregar su primer vaso (toda la produccion +
            # un viaje completo de ida y vuelta, unos 7 minutos).
            ya_entrego = ya_entrego or any(e["ev"] == "entregado" for e in eventos)
            if ya_entrego and any(e["ev"] == "en_muelle" for e in eventos):
                cuadros.append(json.loads(json.dumps(dict(planta.estado(), linea="terminada", eventos_tick=eventos,
                                                          **comun))))
                break
            linea = "terminada" if planta.terminado else "corriendo"
            # Copia profunda (ida y vuelta por JSON): cada cuadro es una foto
            # independiente, sin listas compartidas con la planta.
            cuadros.append(json.loads(json.dumps(dict(planta.estado(), linea=linea, eventos_tick=eventos, **comun))))
            if planta.terminado:
                if embalo_parciales:
                    break
                # Fin de turno: se empaca lo que quedo guardado en los tubos.
                cuadros += [dict(cuadros[-1], eventos_tick=[]) for _ in range(3)]
                planta.pedir_embalar_parciales()
                embalo_parciales = True
        cuadros += [dict(cuadros[-1], eventos_tick=[]) for _ in range(CUADROS_FINALES)]
        # tick monotono dentro de la grabacion (el visor limpia la escena
        # cuando el tick baja, es decir, cuando la demo vuelve a empezar)
        for i, c in enumerate(cuadros):
            c["tick"] = i
        return cuadros
    finally:
        if "planta" in locals():
            planta.cerrar()   # el mundo propio del carro
        escena.cerrar()


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    cuadros = grabar()
    (DESTINO / "grabacion.json").write_text(json.dumps(cuadros, ensure_ascii=False), encoding="utf-8")
    (DESTINO / "geometria.json").write_text(
        json.dumps(geometria_completa(configuracion.cargar_parametros()), ensure_ascii=False), encoding="utf-8")
    with open(DOCS / "paso-a-paso.yaml", encoding="utf-8") as archivo:
        pasos = yaml.safe_load(archivo)["pasos"]
    (DESTINO / "pasos.json").write_text(json.dumps(pasos, ensure_ascii=False), encoding="utf-8")
    print(f"{len(cuadros)} cuadros grabados en {DESTINO.relative_to(RAIZ)}")
    # visor-portable.html lleva esta demo adentro: se rehace para que no quede con la vieja.
    from app import portable
    portable.generar()


if __name__ == "__main__":
    main()
