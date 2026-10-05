from control import reglas


def test_material_no_metalico_rechaza():
    assert reglas.evaluar_material(metal=False) == reglas.CAUSA_NO_METALICO


def test_material_metalico_continua():
    assert reglas.evaluar_material(metal=True) is None


def test_geometria_diametro_fuera_de_rango():
    causa = reglas.evaluar_geometria(diametro_mm=10.0, circularidad=0.99, contornos_internos=0)
    assert causa == reglas.CAUSA_FUERA_DE_RANGO


def test_geometria_no_circular():
    causa = reglas.evaluar_geometria(diametro_mm=20.0, circularidad=0.5, contornos_internos=0)
    assert causa == reglas.CAUSA_NO_CIRCULAR


def test_geometria_perforado():
    causa = reglas.evaluar_geometria(diametro_mm=20.0, circularidad=0.99, contornos_internos=1)
    assert causa == reglas.CAUSA_PERFORADO


def test_geometria_valida_no_rechaza():
    causa = reglas.evaluar_geometria(diametro_mm=23.7, circularidad=0.98, contornos_internos=0)
    assert causa is None


def test_clasificacion_clase_otro_rechaza():
    causa = reglas.evaluar_clasificacion(clase="otro", confianza=0.99)
    assert causa == reglas.CAUSA_NO_RECONOCIDA


def test_clasificacion_confianza_insuficiente_rechaza():
    causa = reglas.evaluar_clasificacion(clase="500_nueva", confianza=0.5)
    assert causa == reglas.CAUSA_NO_RECONOCIDA


def test_clasificacion_confianza_suficiente_continua():
    assert reglas.evaluar_clasificacion(clase="500_nueva", confianza=0.90) is None


def test_coherencia_diametro_incoherente_rechaza():
    # nominal de 500_nueva es 23.7 mm; 20 mm difiere mas de 1.2 mm
    causa = reglas.evaluar_coherencia(clase="500_nueva", diametro_medido_mm=20.0)
    assert causa == reglas.CAUSA_INCOHERENTE


def test_coherencia_dentro_de_tolerancia_continua():
    causa = reglas.evaluar_coherencia(clase="500_nueva", diametro_medido_mm=23.0)
    assert causa is None


def test_evaluar_moneda_aceptada():
    veredicto = reglas.evaluar_moneda(
        metal=True,
        diametro_mm=23.7,
        circularidad=0.98,
        contornos_internos=0,
        clase="500_nueva",
        confianza=0.95,
    )
    assert veredicto.aceptada is True
    assert veredicto.causa is None
    assert veredicto.denominacion == 500
    assert veredicto.valor == 500
    assert veredicto.masa_estimada_g == 7.1


def test_evaluar_moneda_moneda_extranjera_de_diametro_similar_se_rechaza():
    # Un euro mide 23.25 mm, muy cerca del rango de las de 500, pero el
    # clasificador debe devolver 'otro' porque no es una clase colombiana
    # (docs/especificacion.md, seccion 6): la decision final es por reconocimiento de
    # cara, no por geometria.
    veredicto = reglas.evaluar_moneda(
        metal=True,
        diametro_mm=23.25,
        circularidad=0.98,
        contornos_internos=0,
        clase="otro",
        confianza=0.99,
    )
    assert veredicto.aceptada is False
    assert veredicto.causa == reglas.CAUSA_NO_RECONOCIDA


def test_evaluar_moneda_no_revierte_primer_rechazo_encontrado():
    # circularidad mala Y clase 'otro' a la vez: debe quedarse con la causa
    # de geometria porque esa etapa corre primero.
    veredicto = reglas.evaluar_moneda(
        metal=True,
        diametro_mm=20.0,
        circularidad=0.5,
        contornos_internos=0,
        clase="otro",
        confianza=0.1,
    )
    assert veredicto.causa == reglas.CAUSA_NO_CIRCULAR


def test_parametros_configurables_cambian_el_umbral():
    params = reglas.ParametrosFiltrado(confianza_minima=0.99)
    causa = reglas.evaluar_clasificacion(clase="500_nueva", confianza=0.9, params=params)
    assert causa == reglas.CAUSA_NO_RECONOCIDA



# --- dos fotos por moneda (control.reglas.combinar_fotos) ---

from control.reglas import combinar_fotos  # noqa: E402


def test_dos_fotos_que_coinciden():
    assert combinar_fotos([("500_nueva", 0.95), ("500_nueva", 0.93)])[:2] == ("500_nueva", 0.95)


def test_una_foto_con_reflejo_no_tumba_la_moneda():
    """Una foto no reconoce (reflejo) y la otra si: se acepta la que
    reconocio. Con 'las dos deben coincidir', el rechazo falso se duplicaria."""
    clase, confianza, _ = combinar_fotos([("otro", 0.40), ("200_antigua", 0.95)])
    assert (clase, confianza) == ("200_antigua", 0.95)


def test_dos_fotos_en_conflicto_se_rechazan():
    assert combinar_fotos([("500_nueva", 0.95), ("500_antigua", 0.92)])[0] == "otro"


def test_confianza_baja_no_cuenta_como_reconocida():
    clase, confianza, _ = combinar_fotos([("100_nueva", 0.60), ("otro", 0.40)])
    assert clase == "100_nueva" and confianza == 0.60  # la mejor, pero sera no_reconocida por confianza
