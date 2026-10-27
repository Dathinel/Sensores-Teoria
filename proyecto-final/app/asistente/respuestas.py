"""Respuestas por reglas: las cifras de la corrida y los documentos calculados (costos, peso,
consumo). Es lo que contesta el asistente sin DeepSeek y lo que va al modelo local como dato verificado."""

from __future__ import annotations

import re

from app.rutas import RAIZ

from .conocimiento import MAX_SECCION, buscar, normalizar
from .estado import ESTADO_CARRO
from .llm import _umbrales_filtrado
from .reglas import SIN_SENSOR


def _pesos(v) -> str:
    return f"${int(v or 0):,}".replace(",", ".")


# En minúscula, para ir dentro de una frase; el tablero (app/dashboard/textos.py) los escribe con
# mayúscula, como etiquetas. Por eso no se comparten.
NOMBRE_CAUSA = {"no_metalico": "no metálico", "fuera_de_rango": "fuera de rango", "no_circular": "no circular",
                "perforado": "perforado", "no_reconocida": "no reconocida", "incoherente": "incoherente"}
# Qué estación detecta cada causa de rechazo y con qué regla (docs/especificacion.md sec. 7). Los umbrales
# se rellenan con los de config/parametros.yaml (_umbrales_filtrado).
EXPLICA_CAUSA = {
    "no_metalico": "E2 (material): el capacitivo la ve y el inductivo no, así que no es metal",
    "fuera_de_rango": "E3 (cámara): su diámetro está fuera de {dmin}-{dmax} mm",
    "no_circular": "E3 (cámara): circularidad menor a {circ} (bloques, fichas irregulares)",
    "perforado": "E3 (cámara): tiene agujeros o contornos internos (botones, arandelas)",
    "no_reconocida": "E3 (cámara): no reconoce la cara con confianza de al menos {conf} "
                     "(monedas extranjeras o muy antiguas)",
    "incoherente": "E3 (cámara): el diámetro medido difiere más de {coh} mm del de la denominación reconocida",
}


# Preguntas técnicas del FILTRADO que se repiten (foco del grupo). Sin modelo, las reglas las
# contestan con esto en vez de un pedazo de documentación; con el modelo local, van como DATO
# VERIFICADO (en la batería, "cómo sabe si es de metal" hizo que el modelo chico dijera que no
# había sensor de metal, porque la búsqueda no le trajo la sección del inductivo).
SABER_FILTRADO = [
    (re.compile(r"\b(metal|metalic\w*|capacitiv\w*|inductiv\w*)\b"),
     "El material lo decide la estación 2 con dos sensores DEBAJO de la cinta, mirando a través de la banda: "
     "un capacitivo (ve cualquier objeto) y un inductivo M18 (solo ve metal). Si el capacitivo ve la pieza y "
     "el inductivo no, no es metal y se rechaza como «no metálico», sin gastar la cámara; si los dos la ven, "
     "es metálica y sigue a la cámara."),
    (re.compile(r"(huec|ueco|agujer|perfor|ojal|arandela)"),
     "Los botones y arandelas con agujeros los saca la cámara (estación 3): busca contornos internos cerrados "
     "dentro de la pieza y, si encuentra alguno, la rechaza como «perforado»."),
    (re.compile(r"\b(euro|euros|extranjer\w*|otro pais|otros paises|dolar\w*|centimo\w*)\b"),
     "Una moneda extranjera no se rechaza por tamaño (un euro mide 23,25 mm, casi como una de $500), sino por "
     "la CARA: la cámara la clasifica y, si no la reconoce como moneda colombiana con confianza de al menos "
     "{conf}, la rechaza como «no reconocida»; y si la confunde con una colombiana, la regla de coherencia "
     "compara su diámetro con el de esa denominación (tolerancia {coh} mm) y la rechaza como «incoherente»."),
    (re.compile(r"\b(celdas? de carga|balanza|bascula|hx711)\b"),
     "El proyecto no usa celdas de carga: el grupo las prohibió (difíciles de acondicionar y dan problemas). "
     "El peso que se muestra es ESTIMADO por conteo: la suma de la masa nominal de cada moneda reconocida."),
]


MONTAJE = re.compile(r"\b(montaje|estructura|maquina|planta|sistema|proyecto|todo|completo|equipo|carro)\b")
CONSUMO = re.compile(r"\b(consum\w*|potencia|vatios|watts?|energia|autonomia|dura la bateria|cuanto dura)\b")


def _kg(gramos: float) -> str:
    return f"{gramos / 1000:.2f}".replace(".", ",") + " kg"


def peso_montaje() -> str:
    """Peso de TODO el montaje (config/masas.yaml, app/masas.py), no el de las monedas. "" si falla."""
    try:
        from app import masas

        zonas = sorted(masas.por_zona().items(), key=lambda x: -x[1])
        return (f"El montaje completo pesa unos {_kg(masas.total())} sin el portátil (suma de masas de "
                f"hoja de datos y estimadas, en docs/peso.md; no se pesa en la línea). Lo más pesado: "
                + ", ".join(f"{z} {_kg(g)}" for z, g in zonas[:3]) + ".")
    except Exception:  # config a medio editar: se sigue sin esta frase
        return ""


def consumo_electrico() -> str:
    """Consumo CALCULADO (sim/electrica.py -> docs/electrica.md), no medido. "" si no está el documento."""
    ruta = RAIZ / "docs" / "electrica.md"
    if not ruta.exists():
        return ""
    texto = ruta.read_text(encoding="utf-8")
    partes = []
    m = re.search(r"\*\*Consumo desde la red\*\*:\s*([^\n]+?)\s*\(", texto)
    if m:
        partes.append(f"La planta consume, según la simulación eléctrica, {m.group(1).strip()} desde la red")
    m = re.search(r"\*\*Autonom[ií]a\*\*[^:]*:\s*\*\*([^*]+)\*\*", texto)
    if m:
        partes.append(f"el carro, con su batería 2S, tiene unas {m.group(1).strip()}")
    if not partes:
        return ""
    return ("; ".join(partes) + ". Son valores CALCULADOS con corrientes de hoja de datos (docs/electrica.md), "
            "no medidos: ningún sensor mide el consumo en vivo.")


def _denominacion_nombrada(t: str) -> int | None:
    """La denominación que nombra una frase ya normalizada ("de 500", "de mil", "1.000"), o None."""
    m = re.search(r"\b(1[.,]?000|mil|500|200|100|50|quinientos|doscientos|cien)\b", t)
    if not m:
        return None
    palabra = m.group(1).replace(".", "").replace(",", "")
    return {"mil": 1000, "quinientos": 500, "doscientos": 200, "cien": 100}.get(palabra) or int(palabra)


def responder_local(frase: str, estado: dict) -> str:
    """Preguntas basicas con las cifras del estado (sin DeepSeek)."""
    t = normalizar(frase)
    if re.search(r"\b(costo|costos|cuesta|cuestan|precio|precios|presupuesto|barato|abaratar|ahorrar|ahorro)", t):
        try:
            from app import costos

            subs = sorted(costos.por_subsistema().items(), key=lambda x: -x[1])
            mejores = costos.ahorros()[:3]
            return (f"El proyecto cuesta {costos.pesos(costos.total())} en Colombia (precios del "
                    f"{costos.cargar()['consultado']}, sin el portátil). Lo más caro: "
                    + ", ".join(f"{n} {costos.pesos(v)}" for n, v in subs[:3]) + ". Dónde ahorrar: "
                    + "; ".join(f"{a['titulo']} ({costos.pesos(a['ahorro'])}, riesgo {a['riesgo']})"
                                for a in mejores)
                    + ". Detalle en docs/costos.md.")
        except Exception:  # precios.yaml a medio editar o con otro formato: sigue con lo demás
            pass           # (el asistente nunca se cae por una tabla; se busca en docs/costos.md)
    # Lo técnico del filtrado no depende de la corrida: se contesta aunque no haya datos.
    saber = [texto.format(**_umbrales_filtrado()) for patron, texto in SABER_FILTRADO if patron.search(t)]
    # Peso de TODO el montaje (no el de las monedas) y consumo eléctrico: salen de los documentos
    # calculados (docs/peso.md, docs/electrica.md), no de la corrida.
    pide_peso = re.search(r"\b(peso|pesa|pesan|kilos?|kg|masa)\b", t)
    peso_de_montaje = bool(pide_peso and MONTAJE.search(t) and not re.search(r"\bmonedas?\b", t))
    if peso_de_montaje:
        saber.append(peso_montaje())
    if SIN_SENSOR.search(t):
        saber.append("No hay un sensor que mida eso en vivo, así que no tengo ese dato; lo que sí hay son "
                     "valores nominales o calculados de la documentación.")
    if CONSUMO.search(t) or re.search(r"\b(voltaje|tension|corriente)\b", t):
        saber.append(consumo_electrico())
    saber = [x for x in saber if x]
    if not estado.get("hay_datos"):
        return " ".join(saber) or "Todavía no hay datos de ninguna corrida: empiece una desde la barra de la izquierda."
    tot = estado["totales"]
    partes = list(saber)
    if re.search(r"\b(dinero|plata|valor|pesos|cuanto se ha|money)\b", t):
        partes.append(f"Valor aceptado: {_pesos(tot['valor_aceptado_pesos'])} en {tot['monedas_aceptadas']} monedas; "
                      f"en el almacén hay {_pesos(estado.get('almacen_valor_pesos'))} guardados.")
    tubos = estado.get("almacen_tubos") or {}
    denominacion = _denominacion_nombrada(t)
    if denominacion and re.search(r"\b(cuant|hay|tiene|llevan?|van|guardad|aceptad)", t) and \
            re.search(r"\b(monedas?|pesos|almac|almasen|tubo|hay de)", t):
        # "cuánto hay de 500", "cuántas monedas de mil hay en el almacén": la de esa denominación.
        d = estado["aceptadas_por_denominacion"].get(str(denominacion), {"monedas": 0, "valor_pesos": 0,
                                                                         "peso_estimado_g": 0})
        texto = (f"De {_pesos(denominacion)}: {d['monedas']} monedas aceptadas en esta corrida "
                 f"({_pesos(d['valor_pesos'])}, {d['peso_estimado_g']} g estimados)")
        if str(denominacion) in tubos:
            if re.search(r"\b(almac|almasen|tubo)", t):
                # Preguntan por el ALMACEN: esa cifra va primero. El modelo local chico repite la
                # primera cifra del dato verificado y contestaba las aceptadas (3) en vez de las
                # que quedan en el tubo (0 tras soltar un lote).
                n = tubos[str(denominacion)]
                texto = ((f"El tubo de {_pesos(denominacion)} del almacén está VACÍO ahora: 0 monedas guardadas "
                          f"(el último lote ya cayó a un vaso). ") if not n else
                         f"En el tubo de {_pesos(denominacion)} del almacén hay {n} monedas guardadas ahora. ") +                     "Aparte, " + texto[0].lower() + texto[1:]
            else:
                texto += f"; en su tubo del almacén hay {tubos[str(denominacion)]} guardadas"
        partes.append(texto + ".")
    elif re.search(r"\b(moneda|monedas|denominacion|denominaciones|coins)\b", t) and \
            re.search(r"\b(cuant|total|how many)", t) and not re.search(r"rechaz", t):
        por = estado["aceptadas_por_denominacion"]
        detalle = ", ".join(f"{d['monedas']} de {_pesos(int(k))}" for k, d in sorted(por.items(), key=lambda x: int(x[0])))
        partes.append(f"Monedas aceptadas: {tot['monedas_aceptadas']}" + (f" ({detalle})." if detalle else "."))
    if re.search(r"\b(almacen|almasen|almazen|revolver|tubos?)\b", t) and not denominacion and tubos:
        detalle = ", ".join(f"{n} de {_pesos(int(k)) if k.isdigit() else k}" for k, n in tubos.items() if n)
        partes.append(f"En el almacén revólver hay {_pesos(estado.get('almacen_valor_pesos'))} guardados"
                      + (f" ({detalle})" if detalle else " (todos los tubos vacíos)")
                      + f"; un vaso se llena cuando un tubo junta {estado.get('monedas_por_vaso')} monedas "
                        f"de la misma denominación.")
    if re.search(r"\b(peso|pesa|pesan|gramos|masa)\b", t) and not peso_de_montaje:
        partes.append(f"Peso estimado de las monedas aceptadas: {tot['peso_estimado_g']} g ({tot['nota_peso']}).")
    # "filtro" solo pide cifras de rechazos si no es una pregunta técnica ya contestada arriba: en la
    # batería, "qué filtro saca los botones con huecos" recibió también "el último rechazo fue en la
    # casilla 52 (no reconocida)" y el modelo local los mezcló ("el último perforado fue la 52").
    if re.search(r"\b(rechaz|rechazo|rechazos|rechazadas|causa|causas)", t) or \
            (re.search(r"\bfiltros?\b", t) and not saber):
        causas = estado["rechazos_por_causa"]
        detalle = ", ".join(f"{NOMBRE_CAUSA.get(c, c)}: {n}" for c, n in causas.items())
        partes.append(f"Piezas rechazadas: {tot['piezas_rechazadas']}" + (f" ({detalle})." if detalle else "."))
        if causas and re.search(r"\b(por ?que|causa|causas|motivo|explica|razon)", t):
            # "cuántas rechazó y POR QUÉ": qué estación detecta cada causa y con qué umbral.
            u = _umbrales_filtrado()
            partes.append("Por qué: " + "; ".join(f"{NOMBRE_CAUSA.get(c, c)} = {EXPLICA_CAUSA[c].format(**u)}"
                                                  for c in causas if c in EXPLICA_CAUSA) + ".")
        ultimos = estado.get("ultimos_rechazos") or []
        if ultimos:
            partes.append(f"El último rechazo fue en la casilla {ultimos[0]['casilla']} "
                          f"({NOMBRE_CAUSA.get(ultimos[0]['causa'], ultimos[0]['causa'])}).")
    v = estado.get("ultima_inspeccion_camara")
    if v and (re.search(r"\bultim", t) and re.search(r"\b(moneda|pieza|camara|vision|revis|inspecc|vio)", t)
              or re.search(r"\b(camara|vision)\b", t) and re.search(r"\b(vio|reviso|midio|detecto)\b", t)):
        agujeros = v.get("contornos_internos")
        partes.append(
            f"La última pieza que revisó la cámara (casilla {v['casilla']}, {v.get('hora', '')}) midió "
            f"{v['diametro_mm']} mm de diámetro y circularidad {v['circularidad']}, "
            + ("sin agujeros" if not agujeros else f"con {agujeros} agujeros")
            # "otro" no es una denominación: dicho así, el modelo local ya no la llama "una de 500".
            + (f"; NO la reconoció como ninguna moneda colombiana (clase «otro», confianza {v['confianza']})"
               if v.get("clase") in (None, "otro") else
               f"; la reconoció como «{v['clase']}» con confianza {v['confianza']}")
            + " → " + (v["veredicto"] or "")
            + (f" ({NOMBRE_CAUSA.get(v['causa'], v['causa'])})" if v.get("causa") else "") + ".")
    if re.search(r"\b(vaso|vasos)\b", t):
        partes.append(f"Vasos entregados en la meta: {tot['vasos_entregados_en_meta']}; "
                      f"esperando en la canaleta: {estado['canaleta_vasos_esperando']}.")
    if re.search(r"\b(confianza|umbral)\b", t):
        from app import configuracion

        c = configuracion.cargar_parametros()["filtrado"]["confianza_minima"]
        partes.append(f"La cámara acepta una moneda solo si la reconoce con confianza de al menos {c:.2f} "
                      f"({c * 100:.0f} %); por debajo se rechaza como «no reconocida».")
    if re.search(r"\b(carro|vehiculo|carrito|donde esta|ruta|obstaculo|obstaculos|evasion|evasiones)\b", t) and \
            re.search(r"\b(donde|estado|posicion|ubicacion|cuant|recorr|hac|asiendo|haciendo|que esta|como va|"
                      r"evasion|metros)", t):
        c = estado.get("carro")
        if c:
            radio = c.get("radio") or {}
            ultimos = c.get("ultimos_eventos") or []
            partes.append(
                f"El carro está {ESTADO_CARRO.get(c['estado'], c['estado'])} en ({c['x']:.2f}, {c['y']:.2f}) m"
                + (f" (tramo: {c['fase']})" if c.get("fase") else "")
                + (f", con el vaso {c['vaso_id']}" if c.get("vaso_id") else ", sin vaso")
                + f"; lleva {estado['ruta']['distancia_recorrida_m']} m recorridos y {estado['ruta']['evasiones']} "
                  f"evasiones de obstáculos."
                + (" La radio (ESP-NOW) está " + ("conectada." if radio.get("enlace") else "SIN enlace.")
                   if radio else "")
                + (f" Lo último que hizo: {', '.join(e.split(' ', 1)[1].replace('_', ' ') for e in ultimos[:3])}."
                   if ultimos else ""))
        else:
            partes.append("En esta corrida no hay carro con física.")
    if re.search(r"\b(carro|vehiculo|carrito|viaje|viajes)\b", t) and \
            re.search(r"\b(demora\w*|tarda\w*|dura|duracion|cuanto tiempo|que tan rapido|segundos|minutos)\b", t):
        v = estado.get("ruta", {}).get("tiempos_de_viaje") or {}
        if v.get("viajes_completos"):
            partes.append(
                f"El carro se demora en promedio {v['promedio_viaje_completo_s']} s por viaje completo (sale del "
                f"muelle con el vaso, llega a la meta y vuelve); el último tardó {v['ultimo_viaje_completo_s']} s. "
                f"Solo la ida a la meta: {v['promedio_ida_a_la_meta_s']} s en promedio. "
                f"Lleva {v['viajes_completos']} viajes completos (del registro de eventos del carro).")
        elif v.get("ultima_ida_a_la_meta_s") is not None:
            partes.append(f"El carro tardó {v['ultima_ida_a_la_meta_s']} s en llegar a la meta; todavía no "
                          "completó un viaje de vuelta al muelle.")
        else:
            partes.append("Todavía no hay un viaje del carro registrado en esta corrida: no tengo ese dato.")
    if re.search(r"\b(alarma|alarmas|problema|falla)\b", t):
        al = estado.get("alarmas") or []
        partes.append("Alarmas: " + (", ".join(a.replace("_", " ") for a in al) if al else "ninguna") + ".")
    if re.search(r"\b(estado|como va|linea)\b", t) and not partes:
        partes.append(f"La línea está {estado.get('estado_linea')}, ciclo {estado.get('ciclo')}; "
                      f"faltan {estado.get('piezas_por_cargar')} piezas por cargar.")
    if partes:
        return " ".join(partes)
    # La seccion que resume la bateria de pruebas (docs/modelo-local.md) CITA las preguntas de la
    # bateria palabra por palabra, asi que siempre gana la busqueda para esas preguntas, pero no
    # trae la respuesta (se vio con "¿qué pin manda los pasos (STEP)?": salia ella en vez de la
    # tabla de conexiones). Como extracto de respuesta se prefiere otra seccion.
    docs = [d for d in buscar(frase, 4000 + MAX_SECCION) if not d.titulo.startswith("Resultados de la batería")]
    if docs:
        s = docs[0]
        extracto = re.sub(r"\s+", " ", s.texto)[:700]
        return (f"Sin DeepSeek solo entiendo órdenes y preguntas básicas de la corrida. Lo más relacionado "
                f"que encontré en la documentación ({s.archivo}, «{s.titulo}»): {extracto}…")
    return "No tengo ese dato. Sin DeepSeek entiendo órdenes (p. ej. «avanza 30 cm») y preguntas básicas."
