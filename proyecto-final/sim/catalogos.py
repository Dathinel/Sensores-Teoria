"""Catalogos del proyecto, sin dependencias (ni PyBullet ni Streamlit):

- CATALOGO_SENSORES: los sensores numerados (estacion fija y carro): modelo
  real propuesto, que lo activa, que recibe, que entrega, que mensaje viaja
  al PC (seccion 10.1 de CLAUDE.md), como se replica y como se simula.
- COMPONENTES / CATEGORIAS: la lista de materiales. Cada componente tiene un
  `id` que el visor 3D usa para resaltarlo, cuantos hay, el modelo propuesto,
  para que sirve y su estado en la simulacion ("simulado", "solo visual" o
  "pendiente"). El conexionado va en la fase 8 (firmware).

Los leen sim/geometria.py (visor 3D) y app/documentos.py (docs/sensores.md y
docs/componentes.md).
"""

# ---------------------------------------------------------------------

CATALOGO_SENSORES = [
    {
        "numero": 1, "id": "presencia", "nombre": "Infrarrojo de presencia", "subsistema": "cinta de monedas",
        "estacion": "E1 · Presencia", "modelo": "FC-51 (infrarrojo reflectivo, alcance ajustable) a 5 cm de la cinta",
        "fenomeno": "Luz infrarroja que rebota en el elemento. La cinta es negra mate y casi no refleja, "
                    "así que solo hay rebote fuerte si hay algo encima.",
        "entrada": "Luz IR reflejada (sin elemento: casi nada; con elemento: mucha).",
        "salida": "Digital: 1 = casilla ocupada, 0 = vacía (salida del comparador LM393).",
        "mensaje": '{"t":"evt","src":"e1","ev":"presencia","casilla":17,"ocupada":true}',
        "simulacion": "rayTest vertical de 5 cm hacia la cinta; bloqueado si golpea algo que no sea la cinta.",
    },
    {
        "numero": 2, "id": "capacitivo", "nombre": "Sensor capacitivo", "subsistema": "cinta de monedas",
        "estacion": "E2 · Material (montado BAJO la cinta, en la casilla E1)", "modelo": "LJC18A3-H-Z/BX (NPN, 6-36 V)",
        "fenomeno": "Cualquier objeto cerca cambia la capacitancia de su placa (plástico, metal, madera...). "
                    "Va debajo de la cinta, mirando hacia arriba, y lee la pieza a través de la banda (2 mm); "
                    "la banda y los separadores siempre están iguales en cada pausa, así que se calibra con "
                    "ellos puestos (quedan como fondo).",
        "entrada": "Presencia de cualquier material a ~2 mm sobre su cara (a través de la banda).",
        "salida": "Digital: 1 si hay CUALQUIER elemento.",
        "mensaje": '{"t":"evt","src":"e2","ev":"material","capacitivo":true,"inductivo":false}',
        "simulacion": "Consulta si hay un cuerpo activo en la casilla E1 (cualquiera); la lectura viaja en el "
                      "registro de la casilla y se usa en E2.",
    },
    {
        "numero": 3, "id": "inductivo", "nombre": "Sensor inductivo", "subsistema": "cinta de monedas",
        "estacion": "E2 · Material (BAJO la cinta, en la casilla E2)", "modelo": "LJ18A3-8-Z/BX (NPN, M18, 8 mm)",
        "fenomeno": "Un campo magnético oscilante induce corrientes de Foucault solo en metales. Va debajo de "
                    "la cinta, centrado bajo la casilla, mirando hacia arriba a través de la banda.",
        "entrada": "Metal a ~2 mm sobre su cara (a través de la banda de 2 mm).",
        "salida": "Digital: 1 solo si el elemento es metálico. Junto con el capacitivo: "
                  "cap=1, ind=0 → no metálico; cap=1, ind=1 → metal.",
        "mensaje": '{"t":"evt","src":"e2","ev":"material","capacitivo":true,"inductivo":true}',
        "simulacion": "Consulta la bandera `metal` del cuerpo que está en E2.",
    },
    {
        "numero": 4, "id": "camara", "nombre": "Cámara cenital", "subsistema": "cinta de monedas",
        "estacion": "E3 · Visión", "modelo": "Webcam USB 1080p + anillo de luz difusa",
        "fenomeno": "Imagen de la moneda sobre la cinta negra (fondo de contraste). En la misma imagen "
                    "se ven los separadores de la casilla: con eso se mide si la cinta quedó en su lugar "
                    "(reemplaza al sensor de ranura, grupo 2026-09-25).",
        "entrada": "Imagen de la casilla quieta bajo la cámara.",
        "salida": "En el PC: diámetro (mm), circularidad, contornos internos, clase y confianza; y cuántos "
                  "mm quedó corrida la cinta (si pasa del margen, se corrige con micropasos en la misma pausa).",
        "mensaje": '{"casilla":17,"diametro_mm":23.68,"circularidad":0.981,"clase":"500_nueva","confianza":0.94}',
        "simulacion": "Modo oráculo: geometría real del cuerpo + ruido de clasificación (fase 5: render real).",
    },
    {
        "numero": 5, "id": "sensor_interior", "nombre": "Sensor del interior del vaso", "subsistema": "cinta de vasos",
        "estacion": "Verificación (arriba, mirando hacia adentro del vaso)",
        "modelo": "VL53L0X (el mismo de la cortina; otra dirección I2C con su pin XSHUT)",
        "fenomeno": "Mide la distancia hacia abajo, al fondo del vaso. Los vasos son opacos (la cámara no ve "
                    "adentro): si algo está más arriba que el fondo de un vaso vacío, el vaso trae algo adentro.",
        "entrada": "Distancia desde el sensor hasta lo primero que hay dentro del vaso.",
        "salida": "Digital (en el PC): 1 = el vaso trae algo → no entra (cada vaso arranca de cero).",
        "mensaje": '{"t":"evt","src":"vasos","ev":"verificacion","vaso":4,"objeto_adentro":false}',
        "simulacion": "El vaso simulado tiene o no un objeto adentro, con su error "
                      "(errores_sensores.sensor_interior).",
    },
    {
        "numero": 6, "id": "hall_carrusel", "nombre": "Sensor Hall del carrusel", "subsistema": "cinta de vasos",
        "estacion": "Borde del carrusel del almacén", "modelo": "A3144 (Hall digital, módulo KY-003) + imán de neodimio 6 x 3 mm",
        "fenomeno": "El imán, en una cavidad del disco del carrusel (entre dos tubos), pasa por debajo del sensor "
                    "una vez por vuelta, con 4 mm de aire entre los dos.",
        "entrada": "Campo magnético del imán.",
        "salida": "Digital: 1 = el carrusel está en su referencia. El motor paso a paso no sabe dónde está al "
                  "encender: gira hasta ver el imán (homing) y desde ahí cuenta pasos.",
        "mensaje": '{"t":"evt","src":"almacen","ev":"referencia","ok":true}',
        "simulacion": "Siempre encuentra la referencia (el carrusel simulado no pierde pasos).",
    },
    {
        "numero": 7, "id": "camara_vasos", "nombre": "Cámara de vasos (silueta, ArUco y tapa)",
        "subsistema": "cinta de vasos", "estacion": "Verificación, llenado, tapa y prensa (una sola vista)",
        "modelo": "Webcam USB 720p + panel LED difuso detrás de la cinta + OpenCV (silueta y cv2.aruco 4x4_50)",
        "fenomeno": "A contraluz, lo que hay en cada casilla se ve como una silueta oscura sobre el panel "
                    "blanco. Cada vaso personalizado (opaco) lleva una CINTA impresa alrededor con el mismo "
                    "marcador ArUco repetido 6 veces: siempre hay uno de frente, gire como gire el vaso. La "
                    "tapa naranja se ve como una franja sobre la boca. Con los separadores a contraluz mide "
                    "también si la cinta quedó en su lugar (reemplaza al sensor de ranura). Reemplaza a las 6 "
                    "barreras IR y a los 2 sensores de presencia de vasos (grupo, 2026-09-25). Lo que hay "
                    "ADENTRO de un vaso opaco no lo ve: eso lo mide el sensor del interior del vaso.",
        "entrada": "Imagen de las 4 primeras casillas de la cinta de vasos (verificación, llenado, tapa, prensa).",
        "salida": "Por casilla: presencia; silueta en la franja de media altura y en la franja justo por "
                  "encima del borde (\"barreras virtuales\": media ocupada y borde libre = vaso); número del "
                  "marcador (si cambia entre verificación y llenado, tapa o prensa, el vaso fue cambiado por "
                  "otro igual); en tapa y prensa, si la tapa está puesta; y cuánto quedó corrida la cinta.",
        "mensaje": '{"t":"evt","src":"vasos","ev":"verificacion","vaso":4,"media":true,"borde":false,"marcador":104}',
        "simulacion": "Franjas: rayTest horizontal a 45 mm y a 94,5 mm en cada casilla. Marcador y tapa: "
                      "lo que tiene el vaso simulado, con camara_vasos.no_lee y no_ve_tapa por cuadro.",
    },
    {
        "numero": 8, "id": "cortina", "nombre": "Cortina de seguridad", "subsistema": "cinta de vasos",
        "estacion": "Tapa → Prensa, lado del operador",
        "modelo": "1 × VL53L0X (tiempo de vuelo láser, I2C; otra dirección que el del interior, con su pin XSHUT)",
        "fenomeno": "Un solo sensor a media altura del vaso (65 mm sobre la cinta), en el extremo de la prensa "
                    "mirando hacia la tapa, del lado del operador. Mide en un cono de ~25°, no en un rayo: con "
                    "el eje a 85 mm del eje de la cinta el cono no toca vasos, tapa, prensa ni cinta (aguanta "
                    "~8° de sensor torcido). Una mano que entra a la zona a media altura cruza el cono. Una "
                    "que pase por encima puede evadirlo: eso lo cubre la cámara de vasos, que revisa en cada "
                    "tick que no falte ningún vaso.",
        "entrada": "Distancia al primer objeto dentro del cono.",
        "salida": "Distancia en mm; si es menor que el largo de la zona (~140 mm) → algo invadió (una mano). "
                  "Más lejos o fuera de rango: no cuenta.",
        "mensaje": '{"t":"evt","src":"seguridad","ev":"cortina","activa":true}',
        "simulacion": "Cono real: 19 rayTest repartidos en un cono de 25° de prensa a tapa, a 65 mm de "
                      "altura; activa si cualquiera ve algo dentro de la ventana de distancia.",
    },
    {
        "numero": 9, "id": "linea_ir", "nombre": "Arreglo de 5 infrarrojos de línea", "subsistema": "carro",
        "estacion": "Bajo el frente del carro", "modelo": "5 × TCRT5000 (módulo de 5 canales)",
        "fenomeno": "La línea negra absorbe el IR; el piso claro lo refleja.",
        "entrada": "Reflectancia bajo cada uno de los 5 sensores.",
        "salida": "5 bits (p. ej. 00100 = centrado, 01100 = línea un poco a la izquierda).",
        "mensaje": '{"t":"evt","src":"carro","ev":"linea","bits":"00100"}',
        "simulacion": "Distancia de cada sensor a la línea central de la pista (y a las franjas negras de meta y "
                      "de giro), con lecturas cambiadas a veces (errores_sensores.carro.error_linea). El control "
                      "decide cada bit por mayoría de 3 lecturas y, para volver a la línea, exige 4 seguidas.",
    },
    {
        "numero": 10, "id": "ultrasonico", "nombre": "Ultrasónico frontal (respaldo)", "subsistema": "carro",
        "estacion": "Frente del carro", "modelo": "HC-SR04",
        "fenomeno": "Pulso de 40 kHz que rebota en el obstáculo; se mide el tiempo de ida y vuelta. Ve lejos "
                    "(4 m) pero mide lento (~60 ms entre disparos). Respaldo del láser: no le afectan las "
                    "superficies negras o brillantes ni el sol.",
        "entrada": "Eco del muro (o nada si no hay obstáculo en rango).",
        "salida": "Distancia en mm; a menos de 500 mm frena, a menos de 200 mm (2 mediciones seguidas) esquiva.",
        "mensaje": '{"t":"evt","src":"carro","ev":"obstaculo","sensor":"ultrasonico","distancia_mm":182}',
        "simulacion": "Abanico de 5 rayTest en ±7,5° a la altura real, una medición cada 60 ms, con ruido.",
    },
    {
        "numero": 11, "id": "encoders", "nombre": "Encoders de las ruedas", "subsistema": "carro",
        "estacion": "Ruedas motrices", "modelo": "Encoder óptico de ranura (disco de 20 ranuras)",
        "fenomeno": "Cada ranura que pasa corta el haz: pulsos proporcionales al giro de la rueda.",
        "entrada": "Giro de cada rueda.", "salida": "Pulsos → odometría (distancia y giro).",
        "mensaje": '{"t":"tel","src":"carro","x":0.84,"y":-0.52,"rumbo":-1.57}',
        "simulacion": "Pulsos enteros del giro REAL de cada rueda en PyBullet (20 por vuelta, ~10 mm): si la rueda "
                      "patina, cuenta de más. Llegar al muelle = dejan de contar contra el tope (con PWM bajo).",
    },
    {
        "numero": 13, "id": "laser_frontal", "nombre": "Láser de distancia frontal", "subsistema": "carro",
        "estacion": "Frente del carro, sobre el ultrasónico", "modelo": "VL53L0X (el mismo de la cortina)",
        "fenomeno": "Pulso de luz infrarroja láser: mide el tiempo que tarda en volver. Una medición cada 33 ms "
                    "(el doble de rápido que el ultrasónico), hasta ~1,2 m, cono de ~25°.",
        "entrada": "Luz reflejada por lo que haya adelante.",
        "salida": "Distancia en mm: a menos de 500 mm el carro baja a velocidad de maniobra; a menos de 200 mm "
                  "en 3 mediciones seguidas se detiene, mira a los lados y esquiva.",
        "mensaje": '{"t":"evt","src":"carro","ev":"obstaculo","sensor":"laser","distancia_mm":191}',
        "simulacion": "Cono de 5 rayTest en ±12,5° a 7 cm del piso, una medición cada 33 ms, hasta 1,2 m, "
                      "con ruido proporcional (errores_sensores.carro.ruido_tof).",
    },
    {
        "numero": 12, "id": "cuna", "nombre": "Infrarrojo de la cuna de carga", "subsistema": "carro",
        "estacion": "Cuna (rieles) del carro", "modelo": "TCRT5000 o FC-51",
        "fenomeno": "Antes de soltar confirma que la cuna está vacía; después, que el vaso soltado por el "
                    "escape quedó en la cuna.",
        "entrada": "Luz IR reflejada por el vaso.", "salida": "Digital: 1 = vaso cargado.",
        "mensaje": '{"t":"evt","src":"carro","ev":"carga","vaso":4,"ok":true}',
        "simulacion": "La cuna tiene o no un vaso (lo pone el escape al soltar), más su error "
                      "(errores_sensores.cuna). Se lee antes de soltar (tiene que estar vacía) y después "
                      "(confirma la carga).",
    },
]




# ---------------------------------------------------------------------
# Datos para replicarlo en la vida real: rango, tiempo de respuesta, error
# tipico de cada sensor, como mitigarlo y como se conecta. `error_config`
# es la clave de config/parametros.yaml (errores_sensores) con la que la
# simulacion reproduce ese error. Valores de hoja de datos: PROVISIONALES
# hasta medirlos en banco (docs/replicacion.md).
# ---------------------------------------------------------------------

_REPLICACION = {
    'presencia': {'rango': 'FC-51: 2-30 cm, ajustable; va a 5 cm de la cinta (un TCRT5000 solo ve hasta ~15 mm: tendria que ir tan bajo que los bloques altos lo golpearian)',
     'tiempo_respuesta': '< 1 ms (comparador LM393)',
     'error_tipico': 'Falsos negativos con piezas muy oscuras o con acabado espejo que desvian el haz; '
                     'falsos positivos con sol directo o flash sobre la cinta.',
     'mitigacion': 'Capuchon que tape la luz ambiente en E1; ajustar el potenciometro del LM393 con la '
                   'cinta vacia; voto de 3 lecturas; ademas E2 respalda a E1 (presencia recuperada).',
     'conexion': 'Salida digital D0 del modulo a una entrada del ESP32 fijo (alimentar el modulo a 3,3 V).',
     'error_config': 'presencia'},
    'capacitivo': {'rango': '1-10 mm, ajustable con el tornillo de sensibilidad',
     'tiempo_respuesta': '~5 ms (conmuta a ~100 Hz)',
     'error_tipico': 'Humedad o polvo en la cara activa dan falsos positivos; piezas muy pequenas y '
                     'delgadas pueden no alcanzar el umbral (falso negativo).',
     'mitigacion': 'Montarlo a 3-5 mm de la trayectoria; calibrar con el boton de plastico mas pequeno; '
                   'limpiar la cara; voto de 3 lecturas.',
     'conexion': 'Salida NPN alimentada a 6-36 V: pasar por optoacoplador (PC817) o divisor a 3,3 V. NUNCA '
                 'directo al ESP32.',
     'error_config': 'capacitivo'},
    'inductivo': {'rango': '8 mm nominal en acero (placa patron de 24 x 24 mm); una moneda de 17-27 mm centrada da '
              '~70-80 % de eso, y en bronce, laton y cuproniquel ~40-60 % mas: ~2,2-4,8 mm, contra 2 mm de banda. '
              'Por eso M18 de 8 mm y no el M12 de 4 mm (a traves de la banda no alcanzaba con las no ferrosas)',
     'tiempo_respuesta': '~2 ms (conmuta a ~500 Hz)',
     'error_tipico': 'Las monedas NO ferrosas (casi todas las antiguas y muy antiguas) se detectan a menos '
                     'distancia que el acero: si la moneda pasa lejos, falso negativo y se iria como no '
                     'metalica.',
     'mitigacion': 'Centrado bajo la casilla (descentrado pierde la mitad del alcance); inserto IMPRESO en la '
                   'bancada alrededor de la cara (es no enrasable: nada de metal a menos de ~2 cm); probar con cada '
                   'familia, sobre todo las de bronce; voto de 3 lecturas; si el inductivo ve metal, manda sobre el '
                   'capacitivo.',
     'conexion': 'Salida NPN a 6-36 V: optoacoplador o divisor a 3,3 V. NUNCA directo al ESP32.',
     'error_config': 'inductivo'},
    'camara': {'rango': 'A 15 cm de la cinta (webcam con AUTOENFOQUE: las de foco fijo no enfocan tan cerca): campo de ~170 x 100 mm, 1 px ~ 0,1 mm',
     'tiempo_respuesta': '~250 ms (captura + segmentacion + clasificador en la CPU del portatil)',
     'error_tipico': 'Diametro +-0,08 mm (calibracion de escala y borde difuso); circularidad +-0,01; '
                     'error de clase: sale de la matriz de confusion del modelo entrenado (fase 5); '
                     'reflejos del anillo de luz en monedas brillantes.',
     'mitigacion': 'Anillo de luz difusa y cinta negra mate; calibrar la escala con una moneda patron '
                   'medida con calibrador; umbral de confianza 0,85; regla de coherencia diametro-clase.',
     'conexion': 'USB directo al PC (no pasa por el ESP32).',
     'error_config': 'camara'},
    'cortina': {'rango': '3 cm a ~1,2 m en modo por defecto',
     'tiempo_respuesta': '~33 ms por medida',
     'error_tipico': '+-3 % a corta distancia; las superficies negras reducen el alcance; reflejos pueden '
                     'dar lecturas cortas (falso positivo).',
     'mitigacion': 'Ventana de distancia (solo cuenta lo que esté a menos del largo de la zona); voto de 3 '
                   'medidas (~100 ms); eje a 85 mm de la cinta para que el cono no toque los vasos.',
     'conexion': 'I2C (SDA/SCL) al ESP32 fijo, 3,3 V.',
     'error_config': 'cortina'},
    'sensor_interior': {'rango': '3 cm a ~1,2 m; a 1,5 cm sobre la boca el fondo queda a ~10,5 cm y el cono de 25 grados llega con ~6 mm de margen a la pared (aguanta ~3 grados de torcido: collar de centrado)',
     'tiempo_respuesta': '~33 ms por medida; se votan 3',
     'error_tipico': '±3 % de la distancia (~4 mm a 12 cm): un objeto de pocos milímetros (una sola moneda '
                     'acostada) puede no verse; reflejos en el fondo liso.',
     'mitigacion': 'Margen de 10 mm sobre el fondo del vaso vacío; fondo del vaso mate; sensor centrado sobre '
                   'la boca y fijo al pórtico; 3 medidas con voto.',
     'conexion': 'I2C (SDA/SCL) al ESP32 fijo, 3,3 V; XSHUT a un pin para cambiarle la dirección.',
     'error_config': 'sensor_interior'},
    'hall_carrusel': {'rango': 'Con 4 mm de aire un iman N35 de 6 x 3 mm da ~70 mT en la cara; el A3144 conmuta '
     'con ~10-35 mT: sobra margen (hasta ~7-8 mm)',
     'tiempo_respuesta': '< 1 ms',
     'error_tipico': 'Casi ninguno: no le afecta la luz ni el polvo. Solo falla si el imán se despega o queda '
                     'lejos.',
     'mitigacion': 'Imán pegado en una cavidad impresa; homing lento; al terminar cada vuelta completa, '
                   'comprobar que el imán aparece donde se esperaba.',
     'conexion': 'Salida digital (colector abierto con pull-up) a una entrada del ESP32 fijo, 3,3-5 V.',
     'error_config': None},
    'camara_vasos': {'rango': 'Las 3 casillas (~24 cm de ancho) a ~22 cm de la cámara; marcador de 20 x 20 mm '
                              'legible aunque esté algo inclinado; 1 px ~ 0,2 mm',
     'tiempo_respuesta': '~60 ms por cuadro (captura + silueta + detectMarkers en la CPU del portátil); '
                         'se votan 3 cuadros',
     'error_tipico': 'Silueta: sombras o reflejos en el borde del vaso (casi desaparecen a contraluz). '
                     'Marcador: reflejo o tapado → no lo lee; casi nunca lee un número equivocado (el '
                     'diccionario ArUco corrige errores de bits). Si se cae el PC, no hay verificación de vasos.',
     'mitigacion': 'Panel LED difuso detrás (contraluz: la silueta no depende del color ni de la luz del '
                   'salón); franjas con margen de ±5 mm; marcador mate; voto de 3 cuadros; si no lee el '
                   'marcador decide la silueta (no se bloquea la línea); sin PC la cinta de vasos no avanza '
                   '(falla segura: nada se llena sin verificar).',
     'conexion': 'USB directo al PC (segunda webcam; no pasa por el ESP32).',
     'error_config': 'camara_vasos'},
    'linea_ir': {'rango': '2-10 mm sobre el piso',
     'tiempo_respuesta': '< 1 ms',
     'error_tipico': 'Cambios de luz y de altura del chasis; brillo de la cinta aislante.',
     'mitigacion': 'Montar a 3-5 mm del piso con falda contra la luz; calibrar blanco y negro al arrancar.',
     'conexion': '5 entradas (digitales o ADC) del ESP32 del carro.',
     'error_config': None},
    'ultrasonico': {'rango': '2-400 cm, resolucion ~3 mm, apertura ~15 grados',
     'tiempo_respuesta': '~25 ms por medida + ~60 ms recomendados entre disparos',
     'error_tipico': '+-3 mm tipico; ecos perdidos en superficies inclinadas; lecturas falsas por ecos de '
                     'otros objetos.',
     'mitigacion': 'Respaldo del laser: 2 mediciones seguidas; disparos cada 60 ms para que no se mezclen ecos.',
     'conexion': 'TRIG a una salida; ECHO (5 V) por divisor a 3,3 V al ESP32 del carro.',
     'error_config': None},
    'encoders': {'rango': '20 ranuras por vuelta: con rueda de 65 mm, ~10 mm de avance por pulso',
     'tiempo_respuesta': 'Por interrupcion',
     'error_tipico': 'Deslizamiento de las ruedas; rebotes del sensor de ranura.',
     'mitigacion': 'Interrupciones con antirrebote; corregir la odometria con la linea.',
     'conexion': '2 entradas con interrupcion del ESP32 del carro.',
     'error_config': None},
    'laser_frontal': {'rango': '3 cm a ~1,2 m (modo por defecto); cono de ~25 grados',
     'tiempo_respuesta': '~33 ms por medida',
     'error_tipico': '+-3 % a corta distancia; superficies negras o muy brillantes y el sol directo acortan el '
                     'alcance o dan lecturas falsas.',
     'mitigacion': '3 mediciones seguidas para decidir; el ultrasonico de respaldo cubre lo que el laser no ve.',
     'conexion': 'I2C (SDA/SCL) al ESP32 del carro, 3,3 V.',
     'error_config': None},
    'cuna': {'rango': 'TCRT5000: 2-15 mm',
     'tiempo_respuesta': '< 1 ms',
     'error_tipico': 'Un fondo muy oscuro o brillante refleja poco; luz ambiente fuerte.',
     'mitigacion': 'Apuntarlo al fondo opaco del vaso; voto de 3 lecturas.',
     'conexion': 'Entrada digital del ESP32 del carro.',
     'error_config': None},
}

CATALOGO_SENSORES.sort(key=lambda _s: _s["numero"])
for _s in CATALOGO_SENSORES:
    _s.update(_REPLICACION[_s["id"]])


# =====================================================================
# Lista de materiales
# =====================================================================

PENDIENTE_CONEXION = "Pendiente: sección de conexiones y voltajes (fase 8)."

CATEGORIAS = ("Actuadores", "Control y potencia", "Estructura", "Carro", "Sensores")

COMPONENTES = [
    # ---------------------------------------------------------------- actuadores
    {"id": "motor_cinta_monedas", "categoria": "Actuadores", "nombre": "Motor de la cinta de monedas",
     "cantidad": 1, "modelo": "NEMA17 17HS4401 (PROVISIONAL)",
     "funcion": "Avanza la cinta de monedas una casilla (40 mm) y se detiene (sección 4).",
     "estado": "simulado", "zona": "monedas"},
    # Los dos drivers son el mismo modelo, en la MISMA placa perforada de la caja
    # de control (usuario, 2026-09-27: una sola explicacion para los dos).
    {"id": "drivers_cintas", "categoria": "Control y potencia", "nombre": "Drivers de las dos cintas (M y V)",
     "cantidad": 2, "modelo": "A4988 o TMC2208 (silencioso), en una sola placa",
     "funcion": "Generan los pasos de los dos NEMA17 (micropaso 1/4, por el PWM del ESP32): el driver M mueve la cinta de monedas y "
                "el V la de vasos. Son iguales y comparten placa, 12 V (VMOT, con su condensador de 100 µF cada "
                "uno) y la señal ENABLE; cada uno tiene su STEP y su DIR propios en el ESP32 fijo.",
     "estado": "solo visual", "zona": "control"},
    {"id": "motor_cinta_vasos", "categoria": "Actuadores", "nombre": "Motor de la cinta de vasos",
     "cantidad": 1, "modelo": "NEMA17 17HS4401 (PROVISIONAL)",
     "funcion": "Avanza la cinta de vasos una casilla (80 mm).", "estado": "simulado", "zona": "vasos"},
    {"id": "servo_desvio_e7", "categoria": "Actuadores", "nombre": "Servo de la compuerta de desvío (E4)",
     "cantidad": 1, "modelo": "SG90",
     "funcion": "Filtro total: es la ÚNICA salida de rechazo de la cinta de monedas. En reposo manda todo a la "
                "bandeja de rechazo (a prueba de fallas); solo abre hacia el almacén para una moneda "
                "registrada y aceptada. Reemplaza a los dos expulsores laterales (grupo, 2026-09-25).",
     "estado": "simulado", "zona": "monedas"},
    {"id": "motor_carrusel", "categoria": "Actuadores", "nombre": "Motor del carrusel del almacén",
     "cantidad": 1, "modelo": "28BYJ-48 (5 V, con reducción) + driver ULN2003",
     "funcion": "Gira el carrusel de 6 tubos: pone el tubo de cada moneda bajo el punto de carga y, para "
                "soltar un lote, ese tubo sobre el agujero de la placa. Reemplaza al servo del selector y a "
                "los 6 servos de compuerta.",
     "estado": "simulado", "zona": "almacen"},
    {"id": "servo_obturador", "categoria": "Actuadores", "nombre": "Servo del obturador del almacén",
     "cantidad": 1, "modelo": "SG90",
     "funcion": "Abre el único agujero de la placa fija (sobre el vaso de llenado) para soltar el lote del "
                "tubo que el carrusel puso encima; cerrado, el carrusel puede girar sin que se caiga nada.",
     "estado": "simulado", "zona": "almacen"},
    {"id": "servo_tapas", "categoria": "Actuadores", "nombre": "Servo del escape de tapas",
     "cantidad": 1, "modelo": "SG90", "funcion": "Suelta una tapa del tubo vertical sobre el vaso.",
     "estado": "simulado", "zona": "tapa"},
    {"id": "motor_prensa", "categoria": "Actuadores", "nombre": "Servo de la prensa",
     "cantidad": 1, "modelo": "MG996R (~10 kg·cm) con leva excéntrica de 6,5 mm y resorte",
     "funcion": "Gira la leva 0 → 180 → 0 grados: el pistón baja 13 mm y asienta la tapa. Con 6,5 mm de "
                "excentricidad apunta a 60 N: la tapa sella a presión (snap-fit) y pide ~30-50 N, PROVISIONAL "
                "hasta medirla; 60 N es la más dura con margen x1,2 y el resorte limitador no deja pasar de ahí "
                "(el MG996R la sostiene con margen >x2 a 6 V; ver docs/peso.md). Al ser servo, sabe en qué ángulo quedó: no hace falta sensor de "
                "posición ni puente H.",
     "estado": "simulado", "zona": "tapa"},
    {"id": "servo_empujador", "categoria": "Actuadores", "nombre": "Servo del empujador de descarga",
     "cantidad": 1, "modelo": "MG996R (el vaso lleno pesa más)",
     "funcion": "Con una manivela (carrera ~70 mm) pasa de lado el vaso tapado a la canaleta de entrega. "
                "Los rechazados no se empujan: la cinta los deja caer por su extremo a la bandeja.",
     "estado": "simulado",
     "zona": "vasos"},
    {"id": "servo_compuerta_canaleta", "categoria": "Actuadores", "nombre": "Servo del escape de la canaleta",
     "cantidad": 1, "modelo": "SG90",
     "funcion": "Balancín con dos dedos: el de adelante retiene la fila y el de atrás entra entre el "
                "primer y el segundo vaso al soltar, así sale UN vaso a la cuna del carro (punto 13).",
     "estado": "solo visual", "zona": "canaleta"},
    # ------------------------------------------------------- control y potencia
    {"id": "esp32_fijo", "categoria": "Control y potencia", "nombre": "ESP32 fijo (estación)",
     "cantidad": 1, "modelo": "ESP32 DevKit V1 (38 pines)",
     "funcion": "Lee los sensores, mueve motores y servos, habla con el PC por USB y con el carro por ESP-NOW. "
                "No decide la clasificación: la visión corre en el PC.",
     "estado": "simulado", "zona": "control"},
    {"id": "pca9685", "categoria": "Control y potencia", "nombre": "Controlador de servos",
     "cantidad": 1, "modelo": "PCA9685 (16 canales, I2C)",
     "funcion": "Maneja los 6 servos con solo 2 pines del ESP32 (I2C; sobran 10 de sus 16 canales).",
     "estado": "solo visual", "zona": "control"},
    {"id": "fuente", "categoria": "Control y potencia", "nombre": "Fuente de 12 V",
     "cantidad": 1, "modelo": "Fuente conmutada 12 V 10 A (tipo LRS-150-12, 159 x 97 x 30 mm)",
     "funcion": "12 V para los drivers de los pasos a paso, los sensores capacitivo e inductivo y los dos "
                "reguladores. Tierra comun en estrella en la bornera X2. El ESP32 fijo va por el USB del portatil.",
     "estado": "solo visual", "zona": "control"},
    {"id": "buck_servos", "categoria": "Control y potencia", "nombre": "Regulador de 6 V (servos)",
     "cantidad": 1, "modelo": "Buck XL4016, 6 V 8 A, con disipadores",
     "funcion": "Alimenta solo los servos (dos MG996R piden hasta 2,5 A cada uno trabados), a traves de la "
                "bornera V+ del PCA9685 con su 1000 uF.", "estado": "solo visual", "zona": "control"},
    {"id": "buck_5v", "categoria": "Control y potencia", "nombre": "Regulador de 5 V",
     "cantidad": 1, "modelo": "Buck LM2596, 5 V 3 A",
     "funcion": "5 V para el ULN2003 y el 28BYJ-48 del carrusel, el panel de luz y el anillo de la camara.",
     "estado": "solo visual", "zona": "control"},
    {"id": "fusibles", "categoria": "Control y potencia", "nombre": "Portafusibles",
     "cantidad": 1, "modelo": "Portafusibles de 4 vias (cuchilla): F1 5 A, F2 2 A, F3 3 A, F4 1 A",
     "funcion": "Un fusible por rama de 12 V: regulador de servos, regulador de 5 V, drivers y sensores de 12 V.",
     "estado": "solo visual", "zona": "control"},
    {"id": "bornera_x2", "categoria": "Control y potencia", "nombre": "Bornera X2 (carril DIN)",
     "cantidad": 1, "modelo": "16 bornes de 2,5 mm² con puentes (2-3 +12 V sensores, 5-6 +5 V, 7 a 13 GND)",
     "funcion": "Reparte +12 V, +6 V, +5 V y la tierra comun en estrella: ahi llega cada cable de alimentacion.",
     "estado": "solo visual", "zona": "control"},
    {"id": "entrada_red", "categoria": "Control y potencia", "nombre": "Entrada de red con interruptor",
     "cantidad": 1, "modelo": "Conector IEC C14 con interruptor y portafusible",
     "funcion": "Entrada de 110 V a la fuente, con su interruptor general.", "estado": "solo visual", "zona": "control"},
    {"id": "optoacopladores", "categoria": "Control y potencia", "nombre": "Optoacopladores",
     "cantidad": 1, "modelo": "Placa con 2 PC817 (2,2 kΩ de entrada, 10 kΩ de pull-up a 3,3 V)",
     "funcion": "Pasan las salidas NPN de 12 V del capacitivo y del inductivo a 3,3 V para el ESP32 (nunca directo).",
     "estado": "efecto simulado", "zona": "control"},
    {"id": "reparto_i2c", "categoria": "Control y potencia", "nombre": "Reparto del bus I2C 1",
     "cantidad": 1, "modelo": "Placa perforada con pull-ups de 2,2 kΩ y 2 conectores",
     "funcion": "Reparte el bus I2C largo (100 kHz) a los dos VL53L0X (interior del vaso y cortina).",
     "estado": "efecto simulado", "zona": "control"},
    {"id": "uln2003", "categoria": "Control y potencia", "nombre": "Driver del carrusel",
     "cantidad": 1, "modelo": "Placa ULN2003 (con diodos de rueda libre)",
     "funcion": "Maneja las 4 bobinas del 28BYJ-48 del carrusel desde 4 pines del ESP32.",
     "estado": "efecto simulado", "zona": "control"},
    {"id": "hub_usb", "categoria": "Control y potencia", "nombre": "Hub USB con fuente",
     "cantidad": 1, "modelo": "Hub USB 2.0 de 4 puertos con alimentacion propia",
     "funcion": "El portatil necesita 3 USB: las dos webcams y el ESP32 fijo.", "estado": "efecto simulado",
     "zona": "control"},
    {"id": "canaletas_caja", "categoria": "Control y potencia", "nombre": "Canaletas, prensaestopas y ventilador",
     "cantidad": 1, "modelo": "Canaleta ranurada 25 x 30 mm, prensaestopas PG y ventilador 4010 de 5 V (0,1 A, del buck de 5 V)",
     "funcion": "Todo el cableado de la caja va por las canaletas (ningun hilo cruza por encima de una placa); "
                "los cables de campo entran por prensaestopas separados.", "estado": "solo visual", "zona": "control"},
    {"id": "pc", "categoria": "Control y potencia", "nombre": "Portátil",
     "cantidad": 1, "modelo": "El del grupo (sin GPU)",
     "funcion": "Visión, supervisor, base de datos, dashboard y visor 3D.", "estado": "simulado",
     "zona": "control"},
    # ---------------------------------------------------------------- estructura
    {"id": "cinta_monedas", "categoria": "Estructura", "nombre": "Cinta de monedas y su mesa",
     "cantidad": 1, "modelo": "Banda negra mate de 55 mm, separadores cada 40 mm, mesa de 43 cm (PROVISIONAL)",
     "funcion": "Lleva cada elemento por las 7 estaciones.", "estado": "simulado", "zona": "monedas"},
    {"id": "cinta_vasos", "categoria": "Estructura", "nombre": "Cinta de vasos y su mesa",
     "cantidad": 1, "modelo": "Banda de 75 mm, casillas de 80 mm, mesa de 10 cm (PROVISIONAL)",
     "funcion": "Lleva los vasos por verificación, llenado, tapa, prensa y descarga.", "estado": "simulado",
     "zona": "vasos"},
    {"id": "canaletas_rechazo", "categoria": "Estructura", "nombre": "Bandeja de rechazo de monedas",
     "cantidad": 1, "modelo": "Impresión 3D / acrílico",
     "funcion": "La única salida de rechazo (grupo, 2026-09-25: filtro total): recibe desde la compuerta de "
                "desvío todo lo que no es una moneda aceptada. La causa de cada rechazo queda registrada.",
     "estado": "simulado", "zona": "monedas"},
    {"id": "almacen", "categoria": "Estructura", "nombre": "Almacén tipo revólver",
     "cantidad": 1, "modelo": "6 tubos de 29 mm interior x 58 mm (PROVISIONAL) en un disco giratorio sobre una "
                              "placa fija con un agujero; embudo corto al vaso. Impresión 3D",
     "funcion": "Guarda las monedas por denominación hasta completar un lote. La moneda cae casi vertical a "
                "la boca del tubo que está bajo el punto de carga; la pila resbala sobre la placa fija al girar.",
     "estado": "simulado", "zona": "almacen"},
    {"id": "tubo_tapas", "categoria": "Estructura", "nombre": "Tubo vertical de tapas",
     "cantidad": 1, "modelo": "Tubo de 78 mm interior, termina ~1 cm sobre la boca del vaso",
     "funcion": "Guarda las tapas; el escape suelta una que cae poco y se centra sola.",
     "estado": "simulado", "zona": "tapa"},
    {"id": "bandeja_rechazo_vasos", "categoria": "Estructura", "nombre": "Bandeja de rechazo de vasos",
     "cantidad": 1, "modelo": "Impresión 3D, al final de la cinta de vasos",
     "funcion": "Recibe los vasos inválidos, que caen por el extremo de la cinta.",
     "estado": "simulado", "zona": "vasos"},
    {"id": "estructura", "categoria": "Estructura", "nombre": "Estructura de perfil de aluminio",
     "cantidad": 1, "modelo": "Perfil 2020 (patas de la mesa de monedas y pórtico trasero de la cinta de vasos)",
     "funcion": "Sostiene la cinta de monedas, el almacén, el tubo de tapas, la prensa y el panel de luz: "
                "nada queda colgando en el aire.",
     "estado": "solo visual", "zona": "vasos"},
    {"id": "panel_luz", "categoria": "Estructura", "nombre": "Panel de luz de la cámara de vasos",
     "cantidad": 1, "modelo": "Panel LED difuso 5 V (o tira LED detrás de acrílico opalino), ~33 x 11 cm",
     "funcion": "Contraluz detrás de verificación, llenado, tapa y prensa: la cámara de vasos ve siluetas "
                "nítidas y las monedas en el fondo del vaso translúcido. También cierra por detrás la zona de "
                "tapa y prensa (una mano solo entra por el lado del operador).",
     "estado": "solo visual", "zona": "vasos"},
    {"id": "canal_e7", "categoria": "Estructura", "nombre": "Embudo y canales de la descarga",
     "cantidad": 1, "modelo": "Embudo y dos canales cortos impresos (~60° de inclinación)",
     "funcion": "Recibe la moneda que cae por el extremo de la cinta; la compuerta de desvío la manda por un "
                "canal corto a la boca del tubo del carrusel o por el otro a la bandeja de rechazo.",
     "estado": "simulado", "zona": "monedas"},
    {"id": "canaleta_entrega", "categoria": "Estructura", "nombre": "Canaleta de entrega",
     "cantidad": 1, "modelo": "2 rieles de 4 mm a 15°, forrados con cinta adhesiva de PTFE (PROVISIONAL: 280 mm)",
     "funcion": "Sostiene los vasos colgados del reborde, en fila contra el escape. Entrada en embudo: "
                "los rieles arrancan 4 mm más separados y 3 mm más abajo y se cierran en 40 mm.",
     "estado": "solo visual", "zona": "canaleta"},
    {"id": "pista", "categoria": "Estructura", "nombre": "Pista con 3 obstáculos y meta",
     "cantidad": 1, "modelo": "Línea de cinta aislante de 19 mm (trazado PROVISIONAL)",
     "funcion": "Recorrido del carro (punto 14).", "estado": "solo visual", "zona": "pista"},
    # --------------------------------------------------------------------- carro
    {"id": "esp32_carro", "categoria": "Carro", "nombre": "ESP32 del carro", "cantidad": 1,
     "modelo": "ESP32 DevKit V1", "funcion": "Sigue la línea, esquiva, llega a la meta y vuelve solo; avisa "
     "por ESP-NOW.", "estado": "simulado", "zona": "pista"},
    {"id": "motores_carro", "categoria": "Carro", "nombre": "Motorreductores del carro", "cantidad": 2,
     "modelo": "Motor TT 1:48 con encoder", "funcion": "Tracción diferencial (2 ruedas + rueda loca de bola: "
     "los 3 apoyos siempre tocan el piso y gira sobre su eje sin patinar).", "estado": "simulado",
     "zona": "pista"},
    {"id": "rodillos_guia", "categoria": "Carro", "nombre": "Rodillos guía traseros", "cantidad": 2,
     "modelo": "Rodamiento 623 (10 mm) en un tornillo M3, en cada esquina trasera",
     "funcion": "Lo que empujan las guías del muelle (no las llantas): el carro gira hacia el centro al entrar de "
                "reversa, como un carrito de supermercado.", "estado": "simulado", "zona": "canaleta"},
    {"id": "puente_h_carro", "categoria": "Carro", "nombre": "Puente H del carro", "cantidad": 1,
     "modelo": "TB6612FNG", "funcion": "Controla los dos motores del carro.", "estado": "pendiente",
     "zona": "pista"},
    {"id": "interruptor_carro", "categoria": "Carro", "nombre": "Interruptor y fusible del carro", "cantidad": 1,
     "modelo": "Interruptor de palanca + fusible de 3 A", "funcion": "Corta la bateria; el fusible protege el cableado.",
     "estado": "solo visual", "zona": "pista"},
    {"id": "bateria_carro", "categoria": "Carro", "nombre": "Batería del carro", "cantidad": 1,
     "modelo": "2 celdas 18650 (7,4 V)", "funcion": "Alimenta motores y ESP32 del carro.",
     "estado": "pendiente", "zona": "pista"},
    {"id": "cuna_carro", "categoria": "Carro", "nombre": "Cuna de carga (rieles)", "cantidad": 1,
     "modelo": "Mismos rieles de la canaleta (forrados con cinta de PTFE), 3 mm más bajos, entrada en embudo",
     "funcion": "Recibe el vaso desde la canaleta sin brazo robótico. Soporte de 4 puntos a media altura: "
                "espuma adelante, lengüeta con resorte atrás (el vaso la empuja al entrar y no puede "
                "salirse) y dos guías con PTFE a los costados: el vaso no cabecea y el carro puede ir "
                "más rápido.", "estado": "solo visual", "zona": "pista"},
    {"id": "muelle_carga", "categoria": "Estructura", "nombre": "Muelle de carga del carro", "cantidad": 1,
     "modelo": "2 guías en V impresas con cinta de PTFE (boca 4,5 cm más ancha por lado en 20 cm, 3 mm de "
               "holgura) + 2 topes con espuma",
     "funcion": "El carro entra de reversa: las guías empujan sus rodillos traseros y lo centran, y los topes lo "
                "paran con la cuna justo bajo el final de la canaleta, aunque haya seguido la línea con error. "
                "Sabe que llegó porque los encoders dejan de contar contra el tope (entra con PWM bajo).",
     "estado": "simulado", "zona": "canaleta"},
]

# Estado de cada componente, con su propia logica (no escrito a mano):
# - "simulado": la simulacion hace lo que hace esta pieza (se mueve, cuenta,
#   decide);
# - "efecto simulado": la pieza no se simula sola, pero su efecto si esta en
#   la simulacion porque lo hace otra (los drivers: la cinta avanza igual;
#   el ESP32 fijo: el supervisor hace su parte);
# - "solo visual": esta en el 3D y en el conexionado, pero nada en la
#   simulacion depende de ella (la fuente, la bateria, la estructura).
# Ademas, el modelo 3D y el conexionado se comprueban aparte (el visor mira
# si esta dibujado; `conexiones.py` dice cuantos hilos tiene).
SIMULACION = {
    "motor_cinta_monedas": ("propia", ["motor_monedas"]), "drivers_cintas": ("efecto", ["drivers"]),
    "motor_cinta_vasos": ("propia", ["motor_vasos"]),
    "servo_desvio_e7": ("propia", ["servo_desvio"]), "motor_carrusel": ("propia", ["motor_carrusel"]),
    "servo_obturador": ("propia", ["servo_obturador"]), "servo_tapas": ("propia", ["servo_tapas"]),
    "motor_prensa": ("propia", ["servo_prensa"]), "servo_empujador": ("propia", ["servo_empujador"]),
    "servo_compuerta_canaleta": ("propia", ["servo_canaleta"]),
    "esp32_fijo": ("efecto", ["esp32_fijo"]), "pca9685": ("efecto", ["pca9685"]),
    "fuente": ("no", ["fuente"]), "pc": ("propia", ["pc"]),
    "buck_servos": ("no", ["buck6"]), "buck_5v": ("no", ["buck5"]), "fusibles": ("no", ["fusibles"]),
    "bornera_x2": ("no", ["x2"]), "entrada_red": ("no", ["iec"]), "optoacopladores": ("efecto", ["opto"]),
    "reparto_i2c": ("efecto", ["hub_i2c"]), "uln2003": ("efecto", ["uln2003"]), "hub_usb": ("efecto", ["hub_usb"]),
    "canaletas_caja": ("no", ["ventilador"]), "interruptor_carro": ("no", ["interruptor"]),
    "cinta_monedas": ("propia", []), "cinta_vasos": ("propia", []), "canaletas_rechazo": ("propia", []),
    "almacen": ("propia", []), "tubo_tapas": ("propia", []), "bandeja_rechazo_vasos": ("propia", []),
    "estructura": ("no", []), "panel_luz": ("efecto", ["panel_luz"]), "canal_e7": ("propia", []),
    "canaleta_entrega": ("propia", []), "pista": ("propia", []), "esp32_carro": ("propia", ["esp32_carro"]),
    "motores_carro": ("propia", ["motor_izq", "motor_der"]), "rodillos_guia": ("propia", []),
    "puente_h_carro": ("efecto", ["tb6612"]), "bateria_carro": ("no", ["bateria"]),
    "cuna_carro": ("propia", []), "muelle_carga": ("propia", []),
}
TEXTO_SIMULACION = {"propia": "simulado", "efecto": "efecto simulado", "no": "solo visual"}
# Dispositivos del conexionado que son sensores (van en el catalogo de sensores).
DISPOSITIVOS_DE_SENSOR = {
    "presencia": "presencia", "capacitivo": "capacitivo", "inductivo": "inductivo", "hall": "hall_carrusel",
    "vl53_interior": "sensor_interior", "vl53_cortina": "cortina", "cam_cenital": "camara", "anillo": "camara",
    "cam_vasos": "camara_vasos", "enc_izq": "encoders", "enc_der": "encoders", "ir_linea": "linea_ir",
    "hcsr04": "ultrasonico", "vl53_frontal": "laser_frontal", "ir_cuna": "cuna",
}


def _hilos_de(dispositivos: list[str]) -> list[str]:
    from sim.conexiones import CABLES

    out = []
    for cab in CABLES:
        for h in cab["hilos"]:
            if {h["de"].split(".", 1)[0], h["a"].split(".", 1)[0]} & set(dispositivos):
                out.append(f"{h['de']} → {h['a']} ({h['funcion']})")
    return out


# Los 13 sensores: todos simulados; sus dispositivos del conexionado y
# cuantos hilos tienen.
for _s in CATALOGO_SENSORES:
    _devs = [d for d, sid in DISPOSITIVOS_DE_SENSOR.items() if sid == _s["id"]]
    _s["dispositivos"] = _devs
    _s["hilos"] = len(_hilos_de(_devs))

for _c in COMPONENTES:
    _nivel, _devs = SIMULACION[_c["id"]]
    _c["simulacion"] = _nivel
    _c["estado"] = TEXTO_SIMULACION[_nivel]
    _c["dispositivos"] = _devs
    _hilos = _hilos_de(_devs)
    _c["hilos"] = len(_hilos)
    _c["conexion"] = (f"{len(_hilos)} hilos (detalle en docs/conexiones.md): " + "; ".join(_hilos[:6])
                      + (" …" if len(_hilos) > 6 else "")) if _hilos else "Sin hilos: pieza mecánica."

