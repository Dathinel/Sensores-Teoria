"""Los dibujos de la línea en vivo, en HTML: la cinta de monedas con sus
piezas, el almacén tipo revólver con sus tubos y la cinta de vasos.

Cada casilla es un rectángulo oscuro (la cinta negra mate); adentro va la
pieza dibujada con CSS (moneda dorada, botón con ojales, bloque, vaso con su
nivel de monedas y su tapa). Los estilos están en `estilo.CSS` (clases
.casilla, .ficha, .vaso, .tubo); aquí solo se arma la estructura.
"""

from __future__ import annotations

import html

from .datos import nombre_denominacion, pesos
from .estilo import AMBAR, AZUL, GRIS, ROJO, VERDE
from .textos import ESTACIONES_MONEDAS, ESTACIONES_VASOS, NOMBRE_CAUSA, TUBOS

COLOR_ESTADO_VASO = {
    "valida": GRIS, "llenando": AMBAR, "llena": AMBAR, "tapada": VERDE,
    "invalida": ROJO, "rechazada": ROJO, "entregada": AZUL, "vacia": "#30363d",
}


def _casilla(titulo: str, cuerpo: str, numero: str, baja: bool = False) -> str:
    return (f'<div class="casilla{" baja" if baja else ""}"><div class="est">{titulo}</div>{cuerpo}'
            f'<div class="num">{numero}</div></div>')


def _cinta(columnas: int, casillas: list[str]) -> str:
    return f'<div class="cinta" style="grid-template-columns:repeat({columnas}, minmax(0,1fr))">{"".join(casillas)}</div>'


def ficha(c: dict) -> str:
    """La pieza que viaja en una casilla, dibujada."""
    tipo = c["tipo"]
    if tipo == "moneda":
        denominacion = (c.get("clase_real") or "?").split("_")[0]
        return f'<div class="ficha moneda" style="width:46px;height:46px">{denominacion}</div>'
    if tipo == "vacia_registrada":
        # Casilla que el infrarrojo vio ocupada (una mano) pero viaja vacía.
        return '<div class="ficha mano" style="width:40px;height:40px">✋</div>'
    apariencia = c.get("apariencia")
    if apariencia == "moneda_extranjera":
        return '<div class="ficha moneda" style="width:44px;height:44px;filter:saturate(.35)">€</div>'
    if tipo in ("boton_plastico", "boton_metalico"):
        # Ojales solo si de verdad tiene agujeros (un disco liso o una moneda extranjera no).
        ojales = '<span class="ojal"></span><span class="ojal"></span>' if (c.get("contornos_internos") or 0) > 0 else ""
        return f'<div class="ficha {tipo}" style="width:40px;height:40px">{ojales}</div>'
    color = "background:#8d939b" if apariencia == "bloque_metalico" else ""
    return f'<div class="ficha bloque" style="width:36px;height:36px;{color}"></div>'


def veredicto(c: dict) -> str:
    if c.get("causa"):
        return f'<div class="veredicto no">✕ {NOMBRE_CAUSA.get(c["causa"], c["causa"])}</div>'
    if c.get("aceptada"):
        conf = f' · {c["confianza"]:.2f}' if c.get("confianza") is not None else ""
        return f'<div class="veredicto ok">✓ {html.escape(str(c.get("clase")))}{conf}</div>'
    if c.get("metal") is True:
        return '<div class="veredicto pend">metal · a visión</div>'
    return '<div class="veredicto pend">en camino</div>'


def cinta_monedas(tel: dict) -> str:
    casillas = []
    for i, nombre in enumerate(ESTACIONES_MONEDAS):
        c = tel["casillas_monedas"][i]
        cuerpo = '<div class="vacia">—</div>' if c is None else ficha(c) + veredicto(c)
        casillas.append(_casilla(f"E{i + 1} · {nombre}", cuerpo, f'#{c["id"]}' if c else "&nbsp;"))
    return _cinta(len(ESTACIONES_MONEDAS), casillas)


def cinta_vasos(tel: dict) -> str:
    por_vaso = max(1, tel.get("monedas_por_vaso") or 5)
    casillas = []
    for i, nombre in enumerate(ESTACIONES_VASOS):
        v = tel["casillas_vasos"][i]
        if v is None:
            casillas.append(_casilla(nombre, '<div class="vacia">sin vaso</div>', "&nbsp;"))
            continue
        nivel = min(1.0, v["cantidad"] / por_vaso) * 100
        clases = "vaso"
        if v["fisico"] == "ausente":
            clases += " ausente"
        elif v["fisico"] == "figura":
            clases += " figura"
        if v["estado"] in ("tapada", "entregada"):
            clases += " tapado"
        relleno = f'<div class="nivel" style="height:{nivel:.0f}%"></div>' if v["fisico"] == "vaso" else ""
        color = COLOR_ESTADO_VASO.get(v["estado"], GRIS)
        # Un vaso recién puesto en la entrada todavía no pasó la verificación: su registro dice
        # "vacia" solo porque es el estado inicial, no porque la cámara lo haya visto vacío.
        estado_txt = "por verificar" if (v["estado"] == "vacia" and i == 0) else v["estado"]
        etiqueta = {"ausente": "retirado", "figura": "figura extraña"}.get(v["fisico"], "")
        cuerpo = (
            f'<div class="{clases}">{relleno}</div>'
            f'<span class="estado-vaso" style="--c:{color}">{estado_txt}</span>'
            f'<div class="veredicto pend">{v["cantidad"]} mon · {pesos(v["valor"])}</div>'
            + (f'<div class="veredicto no">{etiqueta}</div>' if etiqueta else "")
            + (f'<div class="veredicto ok">vaso de {nombre_denominacion(v["denominacion"])}</div>'
               if v.get("denominacion") else "")
        )
        casillas.append(_casilla(nombre, cuerpo, f'vaso {v["id"]}'))
    return _cinta(len(ESTACIONES_VASOS), casillas)


def almacen(tel: dict) -> str:
    """Los 5 tubos del almacén con cuántas monedas tiene cada uno y la marca del lote,
    más el compartimiento de las denominaciones sin tubo."""
    guardado = tel.get("almacen") or {}
    lote = max(1, tel.get("monedas_por_vaso") or 5)
    capacidad = max(lote, tel.get("capacidad_tubo") or 25)
    casillas = []
    for d in TUBOS:
        n = int(guardado.get(d, 0))
        if d == "otras":
            # Denominaciones sin tubo ($1, $2, $5, $10, $20 de series viejas) y lo que no se
            # alcanzó a registrar: se guarda, no forma lotes.
            cuerpo = (f'<div class="caja-otras">{n}</div>'
                      f'<div class="veredicto {"ok" if n >= lote else "pend"}">{n} guardadas · van juntas a su vaso</div>')
            casillas.append(_casilla("otras", cuerpo, "&nbsp;", baja=True))
            continue
        listo = n >= lote
        cuerpo = (f'<div class="tubo" style="--c:{VERDE if listo else AMBAR}">'
                  f'<div class="nivel" style="height:{min(1.0, n / capacidad) * 100:.0f}%"></div>'
                  f'<div class="lote" style="bottom:{min(1.0, lote / capacidad) * 100:.0f}%"></div></div>'
                  f'<div class="veredicto {"ok" if listo else "pend"}">{n} guardadas{" · lote listo" if listo else ""}</div>')
        casillas.append(_casilla(f"tubo {pesos(int(d))}", cuerpo, "&nbsp;", baja=True))
    return _cinta(len(TUBOS), casillas)
