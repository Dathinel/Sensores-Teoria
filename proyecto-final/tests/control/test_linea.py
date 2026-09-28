from control.linea import Destino, LineaMonedas


def test_casilla_vacia_no_se_procesa():
    linea = LineaMonedas()
    destino = linea.procesar_elemento(0, ocupada=False)
    assert destino == Destino.VACIA
    casilla = linea.registro.obtener(0)
    assert casilla.metal is None
    assert casilla.clase is None


def test_boton_plastico_va_a_rechazo_sin_pasar_por_vision():
    linea = LineaMonedas()
    destino = linea.procesar_elemento(
        1, ocupada=True, capacitivo=True, inductivo=False,
        diametro_mm=20.0, circularidad=0.99, contornos_internos=0,
        clase="otro", confianza=0.99,
    )
    assert destino == Destino.RECHAZO
    casilla = linea.registro.obtener(1)
    # la vision nunca corrio: no gasto un ciclo de camara
    assert casilla.diametro_mm is None
    assert casilla.clase is None


def test_boton_metalico_pasa_material_pero_lo_rechaza_geometria():
    linea = LineaMonedas()
    destino = linea.procesar_elemento(
        2, ocupada=True, capacitivo=True, inductivo=True,
        diametro_mm=20.0, circularidad=0.99, contornos_internos=1,
        clase="otro", confianza=0.99,
    )
    assert destino == Destino.RECHAZO
    assert linea.registro.obtener(2).causa == "perforado"


def test_moneda_extranjera_va_a_rechazo():
    linea = LineaMonedas()
    destino = linea.procesar_elemento(
        3, ocupada=True, capacitivo=True, inductivo=True,
        diametro_mm=23.25, circularidad=0.98, contornos_internos=0,
        clase="otro", confianza=0.99,
    )
    assert destino == Destino.RECHAZO
    assert linea.registro.obtener(3).causa == "no_reconocida"


def test_moneda_colombiana_valida_llega_al_vaso():
    linea = LineaMonedas()
    destino = linea.procesar_elemento(
        4, ocupada=True, capacitivo=True, inductivo=True,
        diametro_mm=23.7, circularidad=0.98, contornos_internos=0,
        clase="500_nueva", confianza=0.95,
    )
    assert destino == Destino.VASO
    casilla = linea.registro.obtener(4)
    assert casilla.aceptada is True
    assert casilla.denominacion == 500
    assert casilla.valor == 500
    assert casilla.masa_estimada_g == 7.1


def test_pedir_destino_antes_de_tener_veredicto_lanza_error():
    linea = LineaMonedas()
    linea.estacion_1_presencia(0, ocupada=True)
    linea.estacion_2_material(0, capacitivo=True, inductivo=True)
    try:
        linea.destino(0)
    except ValueError:
        pass
    else:
        raise AssertionError("se esperaba ValueError por veredicto incompleto")


def test_escenario_mixto_veinte_elementos_termina_en_el_destino_correcto():
    linea = LineaMonedas()

    elementos = [
        # (ocupada, capacitivo, inductivo, diametro, circularidad, contornos, clase, confianza, destino_esperado)
        (True, True, False, None, None, None, None, None, Destino.RECHAZO),  # boton plastico
        (True, True, True, 20.0, 0.5, 0, "otro", 0.1, Destino.RECHAZO),  # bloque irregular
        (True, True, True, 20.0, 0.99, 1, "otro", 0.1, Destino.RECHAZO),  # arandela
        (True, True, True, 23.7, 0.98, 0, "500_nueva", 0.95, Destino.VASO),
        (False, False, False, None, None, None, None, None, Destino.VACIA),
        (True, True, True, 17.0, 0.97, 0, "50_nueva", 0.90, Destino.VASO),
        (True, True, True, 23.25, 0.98, 0, "otro", 0.99, Destino.RECHAZO),  # un euro
        (True, True, True, 26.7, 0.96, 0, "1000_nueva", 0.6, Destino.RECHAZO),  # confianza baja
        (True, True, True, 20.3, 0.97, 0, "100_nueva", 0.88, Destino.VASO),
        (True, True, True, 21.5, 0.96, 0, "50_antigua", 0.90, Destino.VASO),
    ]

    for indice, (ocupada, cap, ind, d, c, ci, clase, conf, esperado) in enumerate(elementos):
        destino = linea.procesar_elemento(
            indice, ocupada=ocupada, capacitivo=cap, inductivo=ind,
            diametro_mm=d, circularidad=c, contornos_internos=ci,
            clase=clase, confianza=conf,
        )
        assert destino == esperado, f"casilla {indice}: se esperaba {esperado}, se obtuvo {destino}"


def test_inductivo_manda_aunque_falle_el_capacitivo():
    """Si el capacitivo tiene un falso negativo pero el inductivo ve metal,
    la moneda no se debe rechazar como no metalica."""
    linea = LineaMonedas()
    linea.estacion_1_presencia(9, ocupada=True)
    casilla = linea.estacion_2_material(9, capacitivo=False, inductivo=True)
    assert casilla.metal is True and not casilla.rechazada
