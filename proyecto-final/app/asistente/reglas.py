"""El interprete local (sin internet): que pide una frase (una pregunta, una orden al carro o a la
linea, el paro...), con expresiones regulares. Tambien decide que ordenes de un modelo se quitan."""

from __future__ import annotations

import re

from .conocimiento import normalizar

_NUM = r"(-?\d+(?:[.,]\d+)?)"


def _num(t: str) -> float:
    return float(t.replace(",", "."))


def _distancia_m(texto: str) -> float | None:
    m = re.search(_NUM + r"\s*(cm|centimetros?|m|metros?|mm|milimetros?)?\b", texto)
    if not m:
        return None
    v, u = _num(m.group(1)), (m.group(2) or "cm")
    return v / 100 if u.startswith("c") else v / 1000 if u.startswith("mm") or u.startswith("mili") else v


# "que + subjuntivo" es un PEDIDO, no una pregunta (revision logica 2026-09-29): el usuario habla
# asi ("que vaya a donde esta el filtro", "que avance el carro 30 cm", "que vuelva al muelle") y
# `es_pregunta` tomaba el "que " inicial como el "que" interrogativo, asi que esas ordenes no daban
# nada. El interrogativo lleva tilde ("¿qué hay?") o va seguido de es/hay/tan/cuanto/hace...: ninguna
# de esas es un subjuntivo de esta lista, asi que siguen siendo preguntas (y una pregunta nunca
# mueve nada). Si la frase trae "qué" CON tilde, gana la pregunta.
_QUE_PEDIDO = re.compile(
    r"que\s+(el carro|el carrito|el vehiculo|el robot|la linea( de produccion)?|la planta|la produccion|"
    r"la cinta|se|lo|le)?\s*"
    r"(avance|avancen|abance|retroceda|retrocedan|gire|giren|voltee|rote|vaya|vayan|vuelva|vuelvan|regrese|"
    r"regresen|siga|sigan|retome|mueva|muevan|detenga|detengan|pare|paren|frene|frenen|ande|camine|lleve|"
    r"pause|reanude|continue|arranque|inicie|empiece|empaque|embale|haga|quede|de (la|media) vuelta)\b")


def es_pedido_con_que(frase: str) -> bool:
    """"que vaya a la meta" (pedido) y no "qué hay en la meta" (pregunta)."""
    t = normalizar(frase).strip().lstrip("¡ ")
    return (not frase.strip().lstrip("¡ ").lower().startswith("qué") and "?" not in frase and "¿" not in frase
            and bool(_QUE_PEDIDO.match(t)))


def es_pregunta(frase: str) -> bool:
    t = normalizar(frase).strip()
    if es_pedido_con_que(frase):
        return False
    return "?" in t or "¿" in frase or bool(re.match(r"(cuant|que |como |donde |cual|por ?que|quien|cuando |how |what |where )", t))


# Pide un movimiento del carro. Si la frase no lo pide, ninguna orden al carro pasa, venga de
# donde venga (reglas, modelo local o DeepSeek; antes el candado era solo para el modelo local).
# Incluye lo que el interprete de reglas entiende como orden (adelante, atras, camina, stop,
# "da la vuelta") para que el candado no le quite una orden legitima.
# Con las formas de "que + subjuntivo" (avance, siga, frene, lleve, camine: 2026-09-29; "avance" se
# escribe con c y el candado le quitaba la orden a "que avance el carro 30 cm").
PIDE_MOVIMIENTO = re.compile(r"\b(muev|avanz|avanc|abanz|abanc|avans|adelante|camin|retroce|reversa|atras|gir|volte|"
                             r"rota|rote|media vuelta|da la vuelta|de la vuelta|ve |ir |vaya|anda|ande|llev|vuelv|"
                             r"regres|deten|det[eé]n|fren|para el|pare|quieto|stop|sigue|siga|retom|continu|meta|"
                             r"muelle|punto)")

# ---- A quien le habla la frase: al carro, a la linea o a nadie (revision logica 2026-09-29) ----
# `PIDE_MOVIMIENTO` solo mira si aparece un verbo de movimiento, sin importar de QUIEN se habla:
# "la moneda avanza por la cinta" mandaba el carro 0,2 m adelante y "sigue la linea de produccion"
# lo ponia a seguir su linea negra (la regla de reanudar nunca se alcanzaba). Ahora una orden al
# carro exige que la frase nombre al carro o que EMPIECE con el verbo (imperativo: "avanza 30 cm",
# "que vuelva al muelle"), y nunca sale si una moneda/pieza/cinta/la planta es el sujeto o lo que
# se mueve.

# Palabras de relleno al inicio de un pedido. "que" es el del pedido ("que vuelva al muelle"): las
# preguntas ya se descartaron antes con `es_consulta`.
_RELLENO = re.compile(r"^\s*((por favor|porfa|oye|ey|bueno|ok|okay|listo|entonces|ahora|y|ya|puedes|podrias|"
                      r"haz que|haga que|hazme el favor de|haz el favor de|necesito que|quiero que|que)\s+)+")
CARRO = re.compile(r"\b(carro|carrito|vehiculo|robot)\b")
# Lo que NO es el carro: si es el sujeto de la frase, el movimiento es de eso (la moneda avanza por la
# cinta, la pieza retrocede, la cinta gira) y el carro no se toca. "linea" sola es la linea negra del
# carro; "linea de produccion", "produccion" y "planta" son la linea de la planta.
AJENO_AL_CARRO = (r"(monedas?|piezas?|cintas?|bandas?|vasos?|elementos?|botones|boton|tapas?|carrusel|tubos?|"
                  r"prensa|empujador|compuerta|linea de produccion|produccion|planta)")
_AJENO = re.compile(r"\b" + AJENO_AL_CARRO + r"\b")
# Verbos (y adverbios) con los que se le da una orden al carro. Si la frase no nombra al carro, tiene
# que EMPEZAR con uno de estos (despues del relleno).
_VERBO_CARRO = (r"(avanz\w*|avance\w*|abanz\w*|abance\w*|avans\w*|adelante|atras|reversa|retroce\w*|muev\w*|"
                r"camin\w*|gir[ae]\w*|volte\w*|rot[ae]\w*|da|de|media vuelta|ve|ir|vaya\w*|vete|anda\w*|"
                r"ande|llev[ae]\w*|vuelv\w*|volver|regres\w*|devuelve\w*|sigue|seguir|siga\w*|retom\w*|"
                r"deten\w*|detien\w*|para|pare\w*|frena\w*|frene\w*|quieto|stop|continu\w*)")
# Verbo que MUEVE a su complemento: "avanza la cinta", "gira el carrusel", "sigue la linea de
# produccion", "deten la planta" hablan de mover eso, no el carro.
_VERBO_CON_OBJETO_AJENO = re.compile(
    r"\b(avanz\w*|avance\w*|retroce\w*|gir[ae]\w*|volte\w*|rot[ae]\w*|muev\w*|deten\w*|detenga\w*|para|pare\w*|"
    r"frena\w*|frene\w*|sigue|seguir|siga\w*|retom\w*|continu\w*)\s+((el|la|los|las|un|una|esa|esta|esas|estas)\s+)?"
    + AJENO_AL_CARRO + r"\b")


def _sin_relleno(t: str) -> str:
    """Frase normalizada, sin signos y sin el relleno del principio."""
    return _RELLENO.sub("", re.sub(r"[¡!¿?.,;:]", " ", t)).strip()


def pide_mover_carro(frase: str) -> bool:
    """La frase le da una orden AL CARRO (no a una moneda, a la cinta ni a la planta)."""
    t = _sin_relleno(normalizar(frase))
    carro, ajeno = CARRO.search(t), _AJENO.search(t)
    verbo = re.search(r"\b" + _VERBO_CARRO + r"\b", t)
    if ajeno and (not carro or ajeno.start() < carro.start()) and (not verbo or ajeno.start() < verbo.start()):
        return False     # "la moneda avanza por la cinta": el sujeto es la moneda
    objeto = _VERBO_CON_OBJETO_AJENO.search(t)
    if objeto and (not carro or objeto.start() < carro.start()):
        return False     # "avanza la cinta", "sigue la linea de produccion"
    if carro:
        return True      # "que el carro vaya a la meta", "gira el carro 90 grados"
    return bool(re.match(_VERBO_CARRO + r"\b", t))   # imperativo al inicio: "avanza 30 cm", "stop"


# Pausar / reanudar LA LINEA (regla acordada con el usuario, 2026-09-29): "deten/para la linea",
# "deten todo", "para la planta", "deten la produccion" = PAUSA (se sale con "reanudar"). El PARO
# queda para "paro", "paro de emergencia" o la urgencia explicita ("para todo ya", `pide_paro`).
# Antes "deten todo/la planta/la produccion" daban `carro detener` (la linea seguia) y "para todo"
# o "para la linea" no daban nada.
_OBJETO_LINEA = r"(todo|toda la planta|la planta|la linea( de produccion)?|la produccion|la maquina|las cintas)"
_PAUSA_DETEN = re.compile(r"\b(deten|detenga|detengan|detener|frena|frene|frenen|frenar|pausa|pausar|pause|"
                          r"paraliza|paralizar)\s+" + _OBJETO_LINEA + r"\b")
# "para" tambien es preposicion ("sirve para todo", "gira el carro para la derecha"): solo cuenta
# como verbo al inicio de la frase o justo antes de todo/la linea/la planta/la produccion, y no
# despues de palabras que la vuelven preposicion.
_PAUSA_PARA = re.compile(r"(?:^|\b(\w+)\s+)(para|pare|paren|parar)\s+" + _OBJETO_LINEA + r"\b")
_ANTES_DE_PREPOSICION = {"sirve", "sirven", "usa", "usan", "util", "listo", "lista", "listos", "hecho", "hecha",
                         "bueno", "buena", "necesario", "necesaria", "importante", "suficiente", "tiempo", "espacio"}


def pide_pausa_linea(frase: str) -> bool:
    t = _sin_relleno(normalizar(frase))
    if _PAUSA_DETEN.search(t):
        return True
    for m in _PAUSA_PARA.finditer(t):
        if m.group(1) not in _ANTES_DE_PREPOSICION:
            return True
    return False


# Reanudar la LINEA: "sigue/continua/retoma la linea de produccion / la produccion / la planta".
_REANUDA_LINEA = re.compile(r"\b(reanuda\w*|reanude\w*|continua\w*|continue\w*|sigue|seguir|siga\w*|retoma\w*|"
                            r"retome\w*|arranca de nuevo)\b.*\b(linea de produccion|produccion|planta)\b")

# Pedir INFORMACION no es dar una orden (revision 2026-09-28): "Dime cuantos vasos llegaron a la
# meta" mandaba el carro a la meta, "Explicame el paro de emergencia" paraba la linea y "Cuentame
# como hace la media vuelta el carro" lo giraba 180 grados. `es_pregunta` solo mira el "?" o la
# primera palabra, y el reconocimiento de voz (Whisper, Google) NO pone signos de pregunta. Con
# estos verbos de explicar/informar la frase nunca da ordenes, con ningun proveedor.
PIDE_INFORMACION = re.compile(
    r"\b(explica\w*|expliq\w*|cuentame|cuentanos|contame|dime|dinos|digame|hablame|hablanos|habla de|"
    r"resume\w*|resumen|muestrame|muestranos|describe\w*|detalla\w*|informame|ensename|"
    r"que es|que son|como funciona\w*|como se hace|como hace|quiero saber|me gustaria saber|necesito saber|"
    r"recuerdame)\b")


def pide_informacion(frase: str) -> bool:
    """La frase pide que se EXPLIQUE o INFORME algo (sin signo de pregunta)."""
    return bool(PIDE_INFORMACION.search(normalizar(frase)))


def es_consulta(frase: str) -> bool:
    """Pregunta o pedido de informacion: ninguna de las dos mueve nada."""
    return es_pregunta(frase) or pide_informacion(frase)


# Paro de emergencia: SOLO con un imperativo explicito. Antes bastaba con que la frase nombrara
# "paro" o "emergencia" ("explicame el paro de emergencia" paraba la linea). Vale: la frase entera
# es el grito ("paro!", "paro de emergencia", "emergencia ya") o un verbo que lo manda ("haz
# paro", "activa el paro", "paro ya") o la urgencia explicita ("para todo ya", "deten la linea ahora
# mismo"). "para todo" o "deten la linea" a secas son PAUSA (`pide_pausa_linea`).
PARO_SOLO = re.compile(r"\s*(paro|emergencia|paro de emergencia)(\s+(ya|ahora|ahora mismo|inmediato|por favor))?\s*$")
PARO_IMPERATIVO = re.compile(
    r"\b(haz|haga|hace|activa|active|activar|pulsa|pulse|presiona|presione|aprieta|oprime|dale|da|dele|"
    r"ejecuta|ejecute|manda|mande)\s+(un |el |al )?(boton de(l)? )?paro\b"
    r"|\bparo( de emergencia)? (ya|ahora|inmediato)\b"
    r"|\b(para|pare|paren|deten|detenga|detengan|frena|frene)\s+(todo|toda la planta|la planta|la linea|"
    r"la maquina|la produccion)\s+(ya|ahora|ahora mismo|inmediatamente|de inmediato)\b")
# "detén la línea" / "para todo" a secas NO son paro: dan PAUSA (se sigue con "reanudar"). Del PARO
# solo se sale con Iniciar, que empieza una corrida nueva: se reserva para "paro" o para la urgencia
# explícita ("para todo ya", "detén la línea ahora mismo").


def pide_paro(frase: str) -> bool:
    t = re.sub(r"[¡!.,;]", " ", normalizar(frase)).strip()
    return bool(PARO_SOLO.match(t) or PARO_IMPERATIVO.search(t))


# Medidas que ningun sensor del proyecto toma en vivo.
SIN_SENSOR = re.compile(r"\b(temperatura|voltaje|tension|corriente|humedad)\b")

# Pedir que el carro ATRAVIESE la planta (usuario, 2026-09-27: "que vaya a donde esta el filtro de
# monedas, lo atraviese y que el propio sistema lo pase por el lado con sus sensores"). El modelo
# local contesto "cruzara por el" y lo mando a (-0,5; 0), dentro de la planta: el carro se trabo
# contra el muelle. El carro anda por el PISO; la planta, la canaleta y el muelle estan prohibidos
# en su mapa. Se contesta con reglas, con cualquier proveedor, y no sale ninguna orden.
ATRAVESAR = re.compile(r"\b(atravies|atraves|cruce|cruza|cruzar|traspas|pase por (encima|dentro|debajo|medio)|"
                       r"por (encima|dentro|debajo|en medio) de)")
ESTRUCTURA = re.compile(r"\b(planta|filtro|cinta|banda|almacen|revolver|canaleta|mesa|estacion|maquina|prensa|"
                        r"camara|sensores|embalaje)")


_zonas = {}


def destino_imposible(x: float, y: float) -> str:
    """"" si el carro puede ir a (x, y); si no, el motivo. Mismo mapa y misma holgura que usa el
    carro (control/vehiculo.py: motivo_destino), armado de la geometria (sim/geometria.py)."""
    from app.configuracion import cargar_parametros
    from control.vehiculo import holguras_carro, motivo_destino
    from sim.geometria import zonas_carro

    if "z" not in _zonas:
        p = cargar_parametros()
        _zonas["z"] = zonas_carro(p)
        _zonas["holgura"] = holguras_carro(p["vehiculo"])[1]
    return motivo_destino(_zonas["z"], float(x), float(y), _zonas["holgura"])


def pide_atravesar(frase: str) -> bool:
    """Una ORDEN (no una pregunta) de que el carro atraviese la planta. Tiene que hablar del
    carro, mandarlo a algun lado o empezar con el verbo: "la moneda pasa por encima de la cinta"
    o "cruce la camara con la mano" no son pedidos al carro."""
    t = normalizar(frase)
    if es_pregunta(frase) or not (ATRAVESAR.search(t) and ESTRUCTURA.search(t)):
        return False
    return bool(re.search(r"\b(carro|vehiculo|vaya|ve a|ir a|lleve|llevalo|haga que|hazlo|muev)", t)
                # Con la frase original (con tildes): "crucé ..." es pasado, no una orden.
                or re.match(r"\s*(atraviesa|atraviese|cruza|cruce|pasa por|pase por)\b", frase.lower()))


RESPUESTA_ATRAVESAR = (
    "Eso no se puede: el carro anda por el piso de la pista y no puede atravesar la planta (las cintas, el "
    "filtro de monedas, el almacén, la canaleta), ni subirse a ella. Además, en su mapa esas zonas están "
    "prohibidas, así que rechaza cualquier destino dentro de ellas. Por los sensores del filtro pasan las "
    "monedas sobre la cinta, no el carro. Lo que sí puede: ir a la meta, volver al muelle, avanzar, girar "
    "o ir a un punto del piso libre alrededor de la pista.")


# Frases que PROMETEN mover el carro (revision visual 2026-09-28: el modelo local decia "se moverá a
# tres posiciones aleatorias" o "se moverá al muelle" sin mandar ninguna orden). Si al final no sale
# ninguna orden al carro, esas oraciones se quitan de la respuesta y se dice que no se movio.
#
# Dos clases (revision logica 2026-09-29): la PRIMERA PERSONA ("lo muevo", "voy a mover", "avanzaré")
# siempre es una promesa de hacerlo ahora por una orden; la IMPERSONAL ("se moverá", "va a moverse")
# a veces describe el FUNCIONAMIENTO AUTOMATICO ("se moverá solo a la meta cuando lo carguen", "cada
# vez que entra al muelle...") y eso es informacion correcta: antes se borraba y se le pegaba "no se
# mueve", que confundia. Solo se quita la impersonal si no trae una marca de automatico/condicion.
# "(?<!no )": "No lo muevo: ese punto está dentro de la planta" es justo lo contrario de una promesa.
PROMESA_PRIMERA_PERSONA = re.compile(
    r"(?<!no )\b(lo movere|movere|voy a mover|lo muevo|muevo el carro|lo llevo|lo llevare|llevare el carro|"
    r"lo mando|lo mandare|enviare el carro|mandare el carro|avanzare|retrocedere|girare|ire a)\b")
PROMESA_IMPERSONAL = re.compile(
    r"(?<!no )\b(se movera|va a moverse|se desplazara|comenzara a moverse|empezara a moverse)\b")
FUNCIONAMIENTO_AUTOMATICO = re.compile(
    r"\b(solo|sola|por si solo|por si mismo|automatic\w*|por su cuenta|cuando|cada vez|siempre|en cuanto|"
    r"apenas|una vez que|despues de|al (terminar|llegar|cargar\w*|recibir|entrar))\b")
# Compatibilidad (evaluador y pruebas viejas): cualquiera de las dos formas.
PROMESA_MOVIMIENTO = re.compile(PROMESA_PRIMERA_PERSONA.pattern + "|" + PROMESA_IMPERSONAL.pattern)


def promete_movimiento(oracion: str) -> str:
    """El trozo de la oracion que promete mover el carro AHORA, o "" (una descripcion del recorrido
    automatico no cuenta)."""
    t = normalizar(oracion)
    m = PROMESA_PRIMERA_PERSONA.search(t)
    if m:
        return m.group(0)
    m = PROMESA_IMPERSONAL.search(t)
    if m and not FUNCIONAMIENTO_AUTOMATICO.search(t):
        return m.group(0)
    return ""


def quitar_promesas(texto: str) -> tuple[str, bool]:
    """Quita las oraciones que prometen un movimiento del carro. Devuelve (texto, quito_algo)."""
    oraciones = re.split(r"(?<=[.!?])\s+", texto.strip())
    quedan = [o for o in oraciones if not promete_movimiento(o)]
    return " ".join(quedan).strip(), len(quedan) != len(oraciones)


def limpiar_markdown(texto: str) -> str:
    """La respuesta se muestra como texto plano (visor 3D, voz): sin `codigo`, **negritas** ni
    titulos "#". El modelo local a veces escribe `qwen2.5-proyecto` y en el visor quedaban las
    comillas invertidas sueltas."""
    t = texto.replace("```", "").replace("`", "")
    t = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), t)
    t = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", t)
    return t.strip()


def _orden_al_carro(t: str) -> dict | None:
    """La orden al carro de una frase ya normalizada que SI le habla al carro, o None."""
    tl = _sin_relleno(t)
    # "para" como verbo solo al inicio o en "para el carro": "gira el carro para el lado derecho"
    # antes lo detenia (la regla buscaba "para el" en cualquier parte).
    if re.search(r"\b(deten|detente|detener|detenga|detengase|frena|frenar|frene|quieto|stop)\b", tl) \
            or re.match(r"(para|pare|parate|parese)\b", tl) or re.search(r"\b(para|pare) (el|al) (carro|carrito|vehiculo|robot)\b", tl):
        return {"cmd": "carro", "accion": "detener"}
    if re.search(r"\b(meta)\b", t) and re.search(r"\b(ve|ir|vaya|vayan|lleva|llevar|lleve|anda|hasta|a la)\b", t):
        return {"cmd": "carro", "accion": "ir_meta"}
    if re.search(r"\b(muelle|base|casa|inicio)\b", t) and re.search(
            r"\b(vuelve|volver|vuelva|regresa|regresar|regrese|ve|ir|vaya|lleva|llevar|lleve|llevalo|manda|mandar|"
            r"mande|devuelve|devuelva)\b", t):
        return {"cmd": "carro", "accion": "volver_muelle"}
    if re.search(r"\b(sigue|seguir|siga|retoma|retomar|retome)\b.*\b(linea|ruta|recorrido)\b", t):
        return {"cmd": "carro", "accion": "seguir_linea"}
    m = re.search(r"\bx\s*=?\s*" + _NUM + r".*?\by\s*=?\s*" + _NUM, t) or \
        re.search(r"\(\s*" + _NUM + r"\s*[,;]\s*" + _NUM + r"\s*\)", t)
    if m and re.search(r"\b(ve|ir|vaya|anda|lleva|lleve|posicion|punto|a)\b", t):
        return {"cmd": "carro", "accion": "ir_a", "x": _num(m.group(1)), "y": _num(m.group(2))}
    if re.search(r"\b(gira|girar|gire|giren|voltea|voltear|voltee|rota|rotar|rote|da la vuelta|de la vuelta|"
                 r"media vuelta)\b", t):
        if "media vuelta" in t or re.search(r"\b(da|de) la vuelta\b", t):
            return {"cmd": "carro", "accion": "girar", "grados": 180}
        g = re.search(_NUM + r"\s*(?:grados?|°)?", t)
        grados = _num(g.group(1)) if g else 90.0
        if "derech" in t:
            grados = -abs(grados)
        return {"cmd": "carro", "accion": "girar", "grados": grados}
    if re.search(r"\b(avanza|avanzar|avance|avancen|avanzando|abanza|abanzar|abance|avansa|avansar|adelante|"
                 r"muevete|mueve|muevelo|mueva|muevase|camina|camine)\b", t):
        return {"cmd": "carro", "accion": "avanzar", "distancia_m": _distancia_m(t) or 0.2}
    if re.search(r"\b(retrocede|retroceder|retroceda|atras|reversa)\b", t):
        return {"cmd": "carro", "accion": "retroceder", "distancia_m": _distancia_m(t) or 0.1}
    return None


def interpretar_orden_local(frase: str) -> list[dict]:
    """Ordenes con expresiones regulares (sin DeepSeek). Devuelve la lista de
    ordenes crudas (despues se validan igual que las de DeepSeek)."""
    t = normalizar(frase).strip()
    # Una pregunta nunca mueve nada ("¿cuantos vasos llegaron a la meta?"), y un pedido de
    # informacion tampoco ("dime cuantos vasos llegaron a la meta", sin signos: asi lo escribe
    # el reconocimiento de voz).
    if es_consulta(frase):
        return []
    if pide_paro(frase):
        return [{"cmd": "paro"}]
    # La LINEA antes que el carro: "deten todo", "para la planta" (pausa) y "sigue la linea de
    # produccion" (reanudar) no son ordenes al carro.
    if pide_pausa_linea(frase):
        return [{"cmd": "pausar"}]
    if _REANUDA_LINEA.search(t):
        return [{"cmd": "reanudar"}]
    # Ordenes al carro: solo si la frase le habla al carro (ver `pide_mover_carro`). Se incluyen las
    # formas de "que + subjuntivo" (avance, vuelva, gire...), que es como pide las cosas el usuario.
    if pide_mover_carro(frase):
        orden = _orden_al_carro(t)
        if orden:
            return [orden]
    if re.search(r"\b(pausa|pausar|pausala|pause)\b", t):
        return [{"cmd": "pausar"}]
    if re.search(r"\b(reanuda|reanudar|reanude|continua|continuar|continue)\b", t):
        return [{"cmd": "reanudar"}]
    if re.search(r"\b(inicia|iniciar|empieza|empezar|arranca|arrancar)\b.*\b(corrida|prueba|linea)\b", t):
        return [{"cmd": "iniciar"}]
    if re.search(r"\b(empaca|empacar|embala|embalar)\b", t):
        return [{"cmd": "embalar_parciales"}]
    m = re.search(r"\blote\b.*?" + _NUM, t) or re.search(_NUM + r"\s*monedas por vaso", t)
    if m:
        return [{"cmd": "lote", "valor": _num(m.group(1))}]
    m = re.search(r"\bvelocidad\b.*?" + _NUM, t)
    if m:
        return [{"cmd": "velocidad", "valor": _num(m.group(1))}]
    return []


def corregir_giros(frase: str, acciones: list) -> list:
    """Un modelo chico a veces se equivoca con el signo del giro (se vio: "a la
    derecha" -> +45). Si la frase dice el lado, manda la frase: derecha =
    negativo, izquierda = positivo (misma convencion que el carro)."""
    t = normalizar(frase)
    lado = -1 if "derech" in t else 1 if "izquierd" in t else 0
    out = []
    for a in acciones:
        if lado and isinstance(a, dict) and a.get("accion") == "girar":
            try:
                a = dict(a, grados=lado * abs(float(a.get("grados", 0))))
            except (TypeError, ValueError):
                pass
        out.append(a)
    return out
