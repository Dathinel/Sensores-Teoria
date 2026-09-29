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

El carrusel es el caso conocido que NO cabe (2026-09-28): `carrusel_giro` es
el tiempo real del firmware para media vuelta (28BYJ-48 a 2 ms por medio
paso = 4,1 s) y no entra en un ciclo de 1,6 s. No se esconde cambiando la
cuenta: los dos chequeos quedan en NO CABE y su explicacion dice que se
ajusta (la cinta de monedas espera al carrusel en esos ciclos).

El reintento de la tapa es el otro (2026-09-28): dos tapas completas no caben
en la pausa de la cinta de vasos; el chequeo lo dice y explica que pasa (la
cinta de vasos espera una pausa mas en ese vaso).
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
    # Un intento de tapa: cae por gravedad y la camara la confirma con cuadros votados.
    intento_tapa = t["tapa_caida"] + lecturas_por_decision * t["camara_vasos_cuadro"]

    chequeos = [
        Chequeo("Las lecturas repetidas caben en la pausa",
                lecturas_por_decision * (lectura_mas_lenta + intervalo) + t["serial_ida_vuelta"], pausa,
                "Cada estación lee su sensor varias veces (separadas para que sean independientes) y vota, "
                "y el evento viaja al PC, con la cinta quieta."),
        Chequeo("La visión decide con la cinta quieta",
                fotos_por_moneda * t["vision_captura_inferencia"] + t["serial_ida_vuelta"], pausa,
                f"{fotos_por_moneda} foto(s) + segmentación + clasificador + ida y vuelta por serial, "
                "dentro de la pausa en E3."),
        Chequeo("La compuerta de desvío se pone antes de que caiga la pieza",
                t["desvio"] + t["serial_ida_vuelta"], t["avance_casilla_monedas"],
                "El veredicto ya se sabe desde la visión; el desvío se mueve mientras la cinta trae la pieza "
                "a la descarga."),
        Chequeo("El carrusel pone el tubo bajo la carga antes de que caiga la moneda",
                t["carrusel_giro"] + t["serial_ida_vuelta"], ciclo_monedas,
                "El carrusel gira al tubo de la denominación durante el ciclo en que la moneda va de la "
                "visión a la descarga. Peor caso: media vuelta (tubo opuesto). Si no cabe, la cinta de "
                "monedas ESPERA al carrusel antes de soltar la moneda (pausa más larga en ese ciclo: baja "
                "la producción, no se pierde ninguna moneda; un tubo vecino, 60 grados, tarda 1/3)."),
        # Revision visual 2026-09-29: la moneda guardada OCUPA el carrusel hasta llegar al fondo
        # de su tubo (control/carrusel.py, `ocupar`). En regimen cae al final del avance y la
        # siguiente se acepta despues de la vision: la caida entra en ese hueco. Cuando la moneda
        # ESPERO al carrusel y cae al empezar el ciclo, el giro a la siguiente sale `caida`
        # despues (esa espera ya la cuenta la simulacion).
        Chequeo("La moneda termina de caer a su tubo antes del giro a la siguiente",
                t["caida_moneda_tubo"], fotos_por_moneda * t["vision_captura_inferencia"] + t["serial_ida_vuelta"],
                "Del borde de la cinta al fondo del tubo (embudo, compuerta, canal corto) con el disco "
                "quieto; en régimen el giro a la siguiente moneda sale recién cuando la visión la acepta, "
                "después de esta caída."),
        Chequeo("El carrusel suelta un lote y vuelve entre dos monedas",
                2 * t["carrusel_giro"] + t["compuerta_tubo"], ciclo_monedas,
                "Girar el tubo al agujero, abrir y cerrar el obturador y volver a la posición de carga, "
                "sin frenar la cinta de monedas. Si no cabe, la cinta de monedas ESPERA a que el carrusel "
                "vuelva (una vez por lote, cada `monedas_por_vaso` monedas de una denominación)."),
        Chequeo("Llega un lote más lento de lo que la cinta de vasos lo despacha",
                ciclo_vasos, lote * ciclo_monedas,
                "Peor caso: todas las monedas de la misma denominación (un lote cada `lote` ciclos)."),
        Chequeo("La cámara de vasos decide con la cinta de vasos quieta",
                lecturas_por_decision * t["camara_vasos_cuadro"] + t["serial_ida_vuelta"], t["pausa_casilla_vasos"],
                "Varios cuadros votados (silueta en las franjas de medida + marcador ArUco) en cada estación, "
                "antes de que la cinta de vasos arranque."),
        Chequeo("La tapa cae y la cámara la confirma en la misma pausa",
                intento_tapa, t["pausa_casilla_vasos"],
                "El escape suelta la tapa, cae por gravedad y la cámara ve que quedó sobre el vaso (un intento)."),
        # Peor caso honesto (2026-09-28): si la camara no ve la primera tapa se
        # suelta OTRA (paso 11) y se vuelve a mirar: dos intentos completos. Antes
        # solo se medía uno y el reintento parecía caber sin que nadie lo contara.
        Chequeo("Reintento de la tapa (peor caso: dos tapas)",
                2 * intento_tapa, t["pausa_casilla_vasos"],
                "Si la cámara no ve la primera tapa, el escape suelta otra y se vuelve a mirar. La pausa "
                "de la cinta de vasos se alargó a propósito para que los dos intentos quepan (grupo, "
                "2026-09-29: los lotes llegan mucho más lento que un ciclo de vasos, así que no frena "
                "nada). Si un día no cupieran, la cinta de vasos esperaría una pausa más y la de monedas "
                "seguiría. La simulación hace los dos intentos dentro del mismo ciclo (sim/planta.py, "
                "_estacion_tapa), lo que ahora coincide con el montaje real."),
        Chequeo("La cortina reacciona a tiempo",
                reaccion_cortina, reaccion_cortina_max_ms,
                "Lecturas votadas del VL53L0X (el firmware exige `lecturas_por_decision` mediciones seguidas) "
                "+ aviso por serial, antes de que baje la prensa o se mueva el empujador."),
    ]
    # Cuanto baja la produccion por esperar al carrusel (usuario, 2026-09-28: se ACEPTA la
    # espera). El giro arranca cuando la vision acepta la moneda (dentro de la pausa en E3:
    # avance + fotos + serial) y la moneda cae en E4 al final del avance siguiente. Ese
    # hueco es lo que el carrusel tiene "gratis"; lo que tarde de mas, la cinta de monedas
    # lo espera. Es lo mismo que hace la simulacion (sim/planta.py + control/carrusel.py),
    # que ademas redondea cada espera a ciclos enteros de la cinta.
    hueco = ciclo_monedas - fotos_por_moneda * t["vision_captura_inferencia"] - t["serial_ida_vuelta"]
    espera_vecino = max(0.0, t["carrusel_giro"] / 3 - hueco)      # otro tubo al lado (60 grados)
    espera_peor = max(0.0, t["carrusel_giro"] - hueco)            # el tubo opuesto (180 grados)
    carrusel = {
        "hueco_ms": hueco,
        "espera_tubo_vecino_ms": espera_vecino,
        "espera_peor_ms": espera_peor,
        # Cada moneda de otra denominacion que la anterior paga su espera; una de la misma, nada.
        "elementos_por_minuto_tubo_vecino": 60000 / (ciclo_monedas + espera_vecino),
        "elementos_por_minuto_peor": 60000 / (ciclo_monedas + espera_peor),
        # Un lote: ir al agujero, abrir y cerrar el obturador, volver (peor caso: media vuelta
        # cada tramo). Se paga una vez cada `lote` monedas de una denominacion.
        "lote_peor_ms": 2 * t["carrusel_giro"] + t["compuerta_tubo"],
    }
    return {
        "carrusel": carrusel,
        "ciclo_monedas_ms": ciclo_monedas,
        "elementos_por_minuto": 60000 / ciclo_monedas,
        "ciclo_vasos_ms": ciclo_vasos,
        "vasos_por_minuto_max": 60000 / ciclo_vasos,
        "reaccion_cortina_ms": reaccion_cortina,
        "chequeos": chequeos,
        "todo_ok": all(c.ok for c in chequeos),
    }


def tiempo_real_estimado_s(ticks: int, t: dict) -> float:
    """Cuanto duraria en el montaje real una corrida de `ticks` ciclos de la
    cinta de monedas. Desde 2026-09-28 los ticks de la simulacion ya incluyen
    las esperas al carrusel (redondeadas a ciclos enteros, asi que en el
    montaje real puede ser algo menos)."""
    return ticks * (t["avance_casilla_monedas"] + t["pausa_casilla_monedas"]) / 1000


def elementos_por_minuto_medidos(elementos: int, ticks: int, t: dict) -> float:
    """Ritmo de una corrida simulada: elementos que entraron / su duracion."""
    segundos = tiempo_real_estimado_s(ticks, t)
    return 60 * elementos / segundos if segundos > 0 else 0.0
