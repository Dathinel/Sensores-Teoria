"""Presupuesto de tiempos de la linea real (codigo puro, sin simulacion).

La simulacion avanza por "ticks" y no le importa cuanto tarda cada cosa;
el montaje real si. Este modulo toma los tiempos de config/parametros.yaml
(`tiempos_ms`, PROVISIONALES hasta medirlos) y responde dos preguntas:

1. ¿Cabe cada accion en el hueco que le da la cinta? Por ejemplo, la vision
   tiene que decidir mientras la cinta esta quieta (la pausa), y el carrusel
   del almacen tiene que llegar al tubo correcto antes de que caiga la
   moneda.
2. ¿Cuanto produce la linea? Elementos por minuto, vasos por minuto.

Si al medir el montaje un tiempo real no cabe, el chequeo correspondiente
dice exactamente que ajustar (pausa mas larga, servo mas rapido...).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chequeo:
    nombre: str
    necesita_ms: float
    disponible_ms: float
    explicacion: str

    @property
    def ok(self) -> bool:
        return self.necesita_ms <= self.disponible_ms

    @property
    def margen_ms(self) -> float:
        return self.disponible_ms - self.necesita_ms


def presupuesto(t: dict, *, lote: int, lecturas_por_decision: int, reaccion_cortina_max_ms: float,
                fotos_por_moneda: int = 1) -> dict:
    """`t` es el bloque `tiempos_ms` de la configuracion."""
    ciclo_monedas = t["avance_casilla_monedas"] + t["pausa_casilla_monedas"]
    pausa = t["pausa_casilla_monedas"]
    lectura_mas_lenta = max(t["presencia_lectura"], t["material_lectura"])
    intervalo = t.get("intervalo_entre_lecturas", 0)
    ciclo_vasos = t["avance_casilla_vasos"] + max(
        t["pausa_casilla_vasos"], t["prensa_ciclo"], t["compuerta_tubo"], t["tapa_caida"], t["empujador"]
    )
    reaccion_cortina = lecturas_por_decision * t["cortina_lectura"] + t["serial_ida_vuelta"]

    chequeos = [
        Chequeo("Las lecturas repetidas caben en la pausa",
                lecturas_por_decision * (lectura_mas_lenta + intervalo) + t["serial_ida_vuelta"], pausa,
                "Cada estacion lee su sensor varias veces (separadas para que sean independientes) y vota, "
                "y el evento viaja al PC, con la cinta quieta."),
        Chequeo("La vision decide con la cinta quieta",
                fotos_por_moneda * t["vision_captura_inferencia"] + t["serial_ida_vuelta"], pausa,
                f"{fotos_por_moneda} foto(s) + segmentacion + clasificador + ida y vuelta por serial, "
                "dentro de la pausa en E5."),
        Chequeo("La compuerta de desvio se pone antes de que caiga la pieza",
                t["desvio"] + t["serial_ida_vuelta"], t["avance_casilla_monedas"],
                "El veredicto ya se sabe desde la vision; el desvio se mueve mientras la cinta trae la pieza "
                "a la descarga."),
        Chequeo("El carrusel pone el tubo bajo la carga antes de que caiga la moneda",
                t["carrusel_giro"] + t["serial_ida_vuelta"], ciclo_monedas,
                "El carrusel gira al tubo de la denominacion durante el ciclo en que la moneda va de la "
                "vision a la descarga."),
        Chequeo("El carrusel suelta un lote y vuelve entre dos monedas",
                2 * t["carrusel_giro"] + t["compuerta_tubo"], ciclo_monedas,
                "Girar el tubo al agujero, abrir y cerrar el obturador y volver a la posicion de carga, "
                "sin frenar la cinta de monedas."),
        Chequeo("Llega un lote mas lento de lo que la cinta de vasos lo despacha",
                ciclo_vasos, lote * ciclo_monedas,
                "Peor caso: todas las monedas de la misma denominacion (un lote cada `lote` ciclos)."),
        Chequeo("La camara de vasos decide con la cinta de vasos quieta",
                lecturas_por_decision * t["camara_vasos_cuadro"] + t["serial_ida_vuelta"], t["pausa_casilla_vasos"],
                "Varios cuadros votados (silueta en las franjas de medida + marcador ArUco) en cada estacion, "
                "antes de que la cinta de vasos arranque."),
        Chequeo("La tapa cae y la camara la confirma en la misma pausa",
                t["tapa_caida"] + lecturas_por_decision * t["camara_vasos_cuadro"], t["pausa_casilla_vasos"],
                "El escape suelta la tapa, cae por gravedad y la camara ve que quedo sobre el vaso."),
        Chequeo("La cortina reacciona a tiempo",
                reaccion_cortina, reaccion_cortina_max_ms,
                "Lecturas votadas del VL53L0X + aviso por serial, antes de que baje la prensa o se mueva el empujador."),
    ]
    return {
        "ciclo_monedas_ms": ciclo_monedas,
        "elementos_por_minuto": 60000 / ciclo_monedas,
        "ciclo_vasos_ms": ciclo_vasos,
        "vasos_por_minuto_max": 60000 / ciclo_vasos,
        "reaccion_cortina_ms": reaccion_cortina,
        "chequeos": chequeos,
        "todo_ok": all(c.ok for c in chequeos),
    }


def tiempo_real_estimado_s(ticks: int, t: dict) -> float:
    """Cuanto duraria en el montaje real una corrida de `ticks` avances de la
    cinta de monedas (cota inferior: ignora esperas por tubos llenos)."""
    return ticks * (t["avance_casilla_monedas"] + t["pausa_casilla_monedas"]) / 1000
