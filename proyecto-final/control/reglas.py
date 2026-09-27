"""Reglas de decision del filtrado de monedas (CLAUDE.md, seccion 7).

Cada funcion corresponde a una etapa independiente y devuelve la causa de
rechazo o None si la etapa deja pasar el elemento. `evaluar_moneda` las
encadena en el orden de la seccion 7: en cuanto una etapa rechaza, las
siguientes ya no se evaluan, porque ninguna etapa puede revertir un rechazo
anterior.
"""

from dataclasses import dataclass

from . import monedas

CAUSA_NO_METALICO = "no_metalico"
CAUSA_FUERA_DE_RANGO = "fuera_de_rango"
CAUSA_NO_CIRCULAR = "no_circular"
CAUSA_PERFORADO = "perforado"
CAUSA_NO_RECONOCIDA = "no_reconocida"
CAUSA_INCOHERENTE = "incoherente"

# Exactamente las causas de la seccion 7. No se inventan causas nuevas sin
# actualizar CLAUDE.md (seccion 10.2).
CAUSAS_VALIDAS = (
    CAUSA_NO_METALICO,
    CAUSA_FUERA_DE_RANGO,
    CAUSA_NO_CIRCULAR,
    CAUSA_PERFORADO,
    CAUSA_NO_RECONOCIDA,
    CAUSA_INCOHERENTE,
)


@dataclass(frozen=True)
class ParametrosFiltrado:
    """Umbrales configurables. Los valores por defecto son los de
    config/parametros.yaml al momento de escribir este modulo; quien cargue
    el YAML en tiempo de ejecucion construye su propia instancia en vez de
    depender de que estos defaults nunca cambien."""

    diametro_min_mm: float = 16.5
    diametro_max_mm: float = 27.5
    circularidad_minima: float = 0.90
    confianza_minima: float = 0.85
    tolerancia_coherencia_mm: float = 1.2


_PARAMETROS_POR_DEFECTO = ParametrosFiltrado()


@dataclass(frozen=True)
class VeredictoMoneda:
    aceptada: bool
    causa: str | None
    denominacion: int | None = None
    valor: int | None = None
    masa_estimada_g: float | None = None


def evaluar_material(metal: bool) -> str | None:
    """Estacion 2. Capacitivo activo e inductivo inactivo (no metalico) se
    rechaza de inmediato; metal continua."""
    return None if metal else CAUSA_NO_METALICO


def evaluar_geometria(
    diametro_mm: float,
    circularidad: float,
    contornos_internos: int,
    params: ParametrosFiltrado = _PARAMETROS_POR_DEFECTO,
) -> str | None:
    """Estacion 5, antes de clasificar. Diametro fuera de rango, poca
    circularidad (bloques y fichas irregulares) o contornos internos
    cerrados (arandelas, botones con ojales)."""
    if not (params.diametro_min_mm <= diametro_mm <= params.diametro_max_mm):
        return CAUSA_FUERA_DE_RANGO
    if circularidad < params.circularidad_minima:
        return CAUSA_NO_CIRCULAR
    if contornos_internos > 0:
        return CAUSA_PERFORADO
    return None


def evaluar_clasificacion(
    clase: str, confianza: float, params: ParametrosFiltrado = _PARAMETROS_POR_DEFECTO
) -> str | None:
    """Estacion 5. Clase 'otro' o confianza insuficiente se rechaza."""
    if clase == monedas.CLASE_OTRO or confianza < params.confianza_minima:
        return CAUSA_NO_RECONOCIDA
    return None


def evaluar_coherencia(
    clase: str, diametro_medido_mm: float, params: ParametrosFiltrado = _PARAMETROS_POR_DEFECTO
) -> str | None:
    """Estacion 5. Cruza la clase predicha contra el diametro medido: si el
    diametro nominal de la clase difiere demasiado del medido, la vision y
    la geometria no coinciden y se rechaza aunque la clasificacion sola
    hubiera aceptado."""
    nominal = monedas.diametro_nominal_mm(clase)
    if nominal is None:
        return CAUSA_NO_RECONOCIDA
    if abs(nominal - diametro_medido_mm) > params.tolerancia_coherencia_mm:
        return CAUSA_INCOHERENTE
    return None


def evaluar_moneda(
    *,
    metal: bool,
    diametro_mm: float,
    circularidad: float,
    contornos_internos: int,
    clase: str,
    confianza: float,
    params: ParametrosFiltrado = _PARAMETROS_POR_DEFECTO,
) -> VeredictoMoneda:
    """Encadena las cuatro etapas de la seccion 7 sobre un elemento que ya
    llego a la estacion de vision (es decir, que ya paso la estacion de
    material). Devuelve el veredicto final."""
    causa = evaluar_geometria(diametro_mm, circularidad, contornos_internos, params)
    if causa is None:
        causa = evaluar_clasificacion(clase, confianza, params)
    if causa is None:
        causa = evaluar_coherencia(clase, diametro_mm, params)

    if causa is not None:
        return VeredictoMoneda(aceptada=False, causa=causa)

    moneda = monedas.buscar_por_clase(clase)
    assert moneda is not None  # evaluar_clasificacion ya descarto 'otro'
    return VeredictoMoneda(
        aceptada=True,
        causa=None,
        denominacion=moneda.denominacion,
        valor=moneda.denominacion,
        masa_estimada_g=moneda.masa_g,
    )


def combinar_fotos(
    vistas: list[tuple[str, float]], params: ParametrosFiltrado = _PARAMETROS_POR_DEFECTO
) -> tuple[str, float, str]:
    """Estacion 5 con varias fotos de la misma moneda (el grupo aprobo 2).
    `vistas` = [(clase, confianza), ...], una por foto. Devuelve (clase,
    confianza, motivo):

    - todas las que reconocen (clase colombiana con confianza suficiente)
      dicen la MISMA clase -> esa clase (aunque otra foto no haya reconocido
      por un reflejo o una sombra: por eso dos fotos bajan los rechazos
      falsos, en vez de subirlos);
    - reconocen clases DISTINTAS -> conflicto: 'otro' (sale como
      no_reconocida; la regla de coherencia no alcanza a desempatar);
    - ninguna reconoce -> la de mayor confianza (sera no_reconocida).

    Una clase mal reconocida en UNA sola foto la sigue atajando la regla de
    coherencia con el diametro medido.
    """
    reconocidas = [(c, p) for c, p in vistas if c != monedas.CLASE_OTRO and p >= params.confianza_minima]
    clases = {c for c, _ in reconocidas}
    if len(clases) == 1:
        clase = clases.pop()
        acuerdo = "todas" if len(reconocidas) == len(vistas) else f"{len(reconocidas)} de {len(vistas)}"
        return clase, max(p for c, p in reconocidas), f"reconocida en {acuerdo} las fotos"
    if len(clases) > 1:
        return monedas.CLASE_OTRO, 0.0, "las fotos reconocen clases distintas"
    clase, confianza = max(vistas, key=lambda v: v[1])
    return clase, confianza, "ninguna foto reconoce la moneda"
