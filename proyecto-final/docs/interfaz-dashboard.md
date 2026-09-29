# Interfaz del dashboard de Streamlit: inventario de funciones

Lista de TODO lo que hacía el dashboard antes de rehacerlo (`app/dashboard.py`, 1.496 líneas,
2026-09-28), escrita antes de tocar el código. Es la lista de verificación: cada punto tiene que
seguir existiendo en la versión nueva (`app/dashboard/`). La columna "Dónde queda" dice en qué
módulo y en qué lugar de la pantalla quedó; "Prueba" dice qué prueba automática lo cubre
(`tests/app/test_dashboard.py`), si la hay.

Reglas que no cambian (CLAUDE.md §8 y §13): el dashboard SOLO lee SQLite y escribe órdenes en la
tabla `ordenes`; no importa PyBullet ni abre el puerto serial; se refresca con
`st.fragment(run_every=dashboard.refresco_s)`, sin bucles infinitos; gráficas con Plotly.

## Cómo se abre

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| G1 | `python -m app.lanzar` arranca el dashboard (puerto 8501) junto al supervisor; `--reemplazar` cierra la instancia anterior buscando el comando del dashboard | `app/lanzar.py` (comando `streamlit run app/dashboard/inicio.py`; reconoce el comando viejo y el nuevo) | `test_lanzar_arranca_el_paquete_nuevo` |
| G2 | `visor.bat` → `app.lanzar --abrir-dashboard` | sin cambios | `tests/visor/test_portable.py` |
| G3 | `?pestana=<clave>` abre directo una pestaña (resumen, produccion/monedas, calidad/rechazos/inspeccion, linea, ruta/carro, replicacion, asistente, ayuda) | `inicio.py` (+ clave nueva `pruebas`) | `test_query_pestana` |
| G4 | Título de la página "Monedas inteligentes", ícono 🪙, ancho completo | `inicio.py` | — |
| G5 | Tema oscuro (fondo #0e1116, paneles #161b22, ámbar como color principal); las 9 pestañas siempre a la vista: si no caben en una fila (~900 px) pasan a una segunda, sin flecha de desplazamiento | `.streamlit/config.toml` + `estilo.py` | — |
| G6 | `PLANTA_BD` apunta a otra base (pruebas) | `datos.py` (vía `configuracion.ruta_bd`) | todas |

## Cabecera (se refresca sola)

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| C1 | Título "Logística de monedas inteligentes" + frase de qué hace el sistema (elemento 7, UMNG) | `cabecera.py` | — |
| C2 | Chip del estado de la línea en palabras ("La línea está trabajando", "en pausa", "PARO de emergencia", "La corrida terminó", "detenida", "sin supervisor"), con color solo si la simulación está viva | `cabecera.py` | — |
| C3 | Chip del ciclo (tick) | `cabecera.py` | — |
| C4 | Chip del origen de los datos: 🖥 SIMULACIÓN (PyBullet) / 🔌 ESP32 REAL / 🧪 ESP32 EMULADO (sin placa) | `cabecera.py` | `test_sin_internet_y_sin_simulacion_se_ve_de_lejos` |
| C5 | Chip de internet: "🌐 con internet" o "📴 SIN INTERNET" (rojo) | `cabecera.py` | `test_con_internet_no_hay_aviso_de_internet` |
| C6 | Aviso "No hay datos todavía. Abra visor.bat … o `python -m app.lanzar`" cuando la base está vacía | `cabecera.py` | `test_sin_datos_explica_como_arrancar` |
| C7 | Aviso "🧪 Prueba de un filtro: <nombre> (<estación>)": qué se espera, cuántas piezas van decididas y cuántas rechazadas por la causa esperada; "ojo: otras causas" si no coinciden | `cabecera.py` | `test_una_prueba_de_un_filtro_se_anuncia_con_su_resultado` |
| C8 | Aviso GRANDE "⏸ NO ES EN VIVO" con la fecha/hora de la última corrida (el supervisor no responde en `/api/estado`) | `cabecera.py` | `test_sin_internet_y_sin_simulacion_se_ve_de_lejos` |
| C9 | Aviso GRANDE "🧪 ESP32 EMULADO" (modo hardware real sin placa) | `cabecera.py` | `test_aviso_esp32_emulado` |
| C10 | Aviso GRANDE "📴 SIN INTERNET" con lo que sigue funcionando (planta, carro, SQLite, modelo local, Whisper, voz de Windows) | `cabecera.py` | `test_sin_internet_y_sin_simulacion_se_ve_de_lejos` |

## Barra lateral: control de la línea

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| B1 | "▶ Empezar una corrida nueva" (`iniciar`, escenario `prueba_completa`, con confianza, errores forzados y conservar almacén de los ajustes avanzados) | `controles.py` | `test_botones_de_control_mandan_sus_ordenes` |
| B2 | "⏸ Pausa" (solo si corre) y "⏵ Seguir" (solo si está en pausa) | `controles.py` | ídem |
| B3 | "⛔ PARO DE EMERGENCIA" (solo si corre o está en pausa) | `controles.py` | ídem |
| B4 | Respuesta de la última orden (verde ✔ / ámbar ✖, con el detalle del supervisor), se refresca sola | `controles.py` (`respuesta_orden`, también en Pruebas y Carro) | — |
| B5 | Velocidad de la simulación ×0,25 … ×4 ("×1 (tiempo real)"), manda `velocidad` una sola vez por cambio | `controles.py` | `test_barra_lateral_tiene_sus_controles` |
| B6 | Monedas por vaso (1 … capacidad del tubo), manda `lote` una vez por cambio | `controles.py` | ídem |
| B7 | Ajustes avanzados (se aplican al empezar): confianza mínima 0,50-0,99; errores forzados del reconocimiento 0-0,5; "Empezar con lo que quedó guardado en los tubos"; nota del hardware real (fase 8) | `controles.py` | ídem |
| B8 | Nota: los botones dejan una orden que la línea toma en menos de medio segundo | `controles.py` | — |
| B9 | "Probar un filtro": selector de los 6 filtros (estación · nombre), qué se espera, botón "🧪 Probar solo este filtro" (`iniciar` con el escenario del filtro) | **movido** a la pestaña 🧪 Pruebas (sección 1) | `test_una_prueba_de_un_filtro_se_anuncia_con_su_resultado`, `test_pestana_pruebas_tiene_todo` |
| B10 | "Colocar una pieza": selector de las piezas del catálogo y "⬇ Ponerla en la próxima carga" (`colocar`; activo si la línea corre o terminó) | **movido** a 🧪 Pruebas (sección 2) | `test_pestana_pruebas_tiene_todo` |

## Pestaña Resumen

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| R1 | Mensaje "Cuando la línea arranque, aquí se ve todo…" sin telemetría | `pestanas/resumen.py` | `test_sin_datos_todas_las_pestanas_cargan` |
| R2 | 5 indicadores: valor aceptado, monedas aceptadas, piezas rechazadas, vasos entregados, peso estimado (con explicación: por conteo, no hay balanza) | `pestanas/resumen.py` | `test_con_una_corrida_completa_todas_las_pestanas_funcionan` |
| R3 | Tarjetas de estado: cinta de monedas (piezas por cargar, moneda en espera), almacén (valor guardado, lote), cinta de vasos (cortina, tapas, vasos en la canaleta), carro (estado, radio, vaso que lleva / "reemplazo simulado") | `pestanas/resumen.py` | ídem |
| R4 | Aviso con las alarmas activas | `pestanas/resumen.py` | — |
| R5 | "Recorrido de las piezas": diagrama Sankey cargadas → aceptadas (esta corrida) / rechazo por material / por visión → tubos / vasos → entregadas, con una segunda fuente "Del turno anterior" (monedas que ya estaban en los tubos); debajo, una frase que explica la diferencia entre valor aceptado, guardado y lo del turno anterior (`datos.cuentas_de_monedas`, las mismas cifras que Monedas y vasos) | `pestanas/resumen.py` + `datos.py` | ídem, `test_las_monedas_del_turno_anterior_se_cuentan_aparte` |
| R6 | "Qué está pasando": últimos 11 eventos en frases simples con hora e ícono | `pestanas/resumen.py` + `textos.py` | ídem |

## Pestaña Monedas y vasos

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| M1 | Barras de monedas aceptadas por denominación (cantidad · valor) | `pestanas/monedas.py` | ídem |
| M2 | Valor acumulado en el tiempo (escalones, relleno) o "todavía no hay monedas aceptadas" | `pestanas/monedas.py` | ídem |
| M3 | Almacén: barras por tubo (50…1000 y "otras") con la línea punteada del lote; verde si el lote está listo | `pestanas/monedas.py` | ídem |
| M4 | Tabla de los vasos de la corrida (estado en palabras, denominación, monedas, valor, hora de llenado y de entrega); el subtítulo dice cuántas monedas de los vasos son de esta corrida y cuántas del turno anterior, y debajo la misma frase del Resumen | `pestanas/monedas.py` | ídem |

## Pestaña Calidad del filtro

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| Q1 | Mensaje sin piezas | `pestanas/calidad.py` | `test_sin_datos_todas_las_pestanas_cargan` |
| Q2 | Indicadores: decisiones correctas (%), monedas buenas rechazadas, piezas malas aceptadas, piezas procesadas | `pestanas/calidad.py` | `test_con_una_corrida_completa…` ("Decisiones correctas") |
| Q3 | Matriz "qué era cada pieza y qué decidió la línea" (verde aciertos, rojo errores), agrupada por el tipo REAL de la pieza (moneda extranjera y cara con otro diámetro → "moneda que debe rechazarse"; disco → botón metálico); ninguna pieza se descarta y el total, escrito debajo, es el de "Piezas procesadas" | `pestanas/calidad.py` + `datos.matriz_aciertos` | `test_la_matriz_de_calidad_no_pierde_ninguna_pieza`, `test_la_matriz_cuadra_con_las_piezas_procesadas_de_una_corrida` |
| Q4 | "Por qué se rechaza cada cosa": conteo por causa, qué filtra y qué etapa (sensores de material / cámara); filtros que no actuaron | `pestanas/calidad.py` | ídem |
| Q5 | Detalle de la cámara: últimas 15 piezas medidas (diámetro, redondez, agujeros, clase, seguridad, decisión) + nota de cámara simulada | `pestanas/calidad.py` | — |

## Pestaña Línea en vivo

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| L1 | Mensaje "La línea todavía no arrancó…" | `pestanas/linea.py` | `test_sin_datos_todas_las_pestanas_cargan` |
| L2 | Aviso rojo de la cortina (mano en tapa y prensa) | `pestanas/linea.py` | — |
| L3 | Cinta de monedas: 4 casillas (E1-E4) con ficha dibujada (moneda, extranjera, botón con/sin ojales, bloque, casilla con mano), veredicto y número; piezas por cargar | `pestanas/linea.py` + `dibujos.py` | ídem |
| L4 | LEDs: infrarrojo (1), capacitivo (2), inductivo (3) | `pestanas/linea.py` | — |
| L5 | Almacén tipo revólver: 5 tubos dibujados con nivel y marca del lote + compartimiento "otras" | `pestanas/linea.py` + `dibujos.py` | — |
| L6 | Cinta de vasos: 5 casillas (verificación … descarga) con vaso dibujado (nivel, tapa, retirado, figura), estado, monedas y valor, denominación; tapas en el tubo y prensadas | `pestanas/linea.py` + `dibujos.py` | — |
| L7 | LEDs: cortina (8, alarma), sensor del interior del vaso (5), Hall del carrusel (6) | `pestanas/linea.py` | — |
| L8 | Bitácora detallada: 16 eventos, frase simple o el evento técnico con sus valores en palabras (un conteo por tubo sale "$50: 4 · $100: 1", no un diccionario de Python) | `pestanas/linea.py` + `textos.valor_legible` | `test_la_bitacora_no_muestra_diccionarios_de_python` |
| L9 | Sabotajes: retirar un vaso, cambiar por un vaso igual, cambiar por una figura, vaso con algo adentro, mano en la carga, mano que saca un vaso, mano en tapa/prensa ↔ quitar la mano, cortar ↔ reconectar la radio del carro (cada uno activo solo cuando tiene sentido) | **movido** a 🧪 Pruebas (sección 3) | `test_pestana_pruebas_tiene_todo` |
| L10 | "📦 Empacar lo guardado en los tubos (fin de turno)" (`embalar_parciales`, activo si hay algo guardado) | **movido** a 🧪 Pruebas (sección 4) | ídem |

## Pestaña Carro y ruta

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| K1 | Tarjetas del carro: qué hace (tramo), carga (vaso, inclinación), radio ESP-NOW (mensajes guardados), cuna (infrarrojo 12), odometría (error en mm); o "no hay carro con física" | `pestanas/carro.py` | — |
| K2 | Indicadores: vasos entregados, obstáculos esquivados, distancia recorrida | `pestanas/carro.py` | — |
| K3 | Mapa de la pista (rango y alto ajustados a todo lo dibujado: muros, recorrido real con sus esquivas y el carro, más un margen): línea, muros, meta, marca de giro, muelle, recorrido real, hitos (obstáculo, esquiva, vuelve a la línea, detenido, orden, camino bloqueado, bloqueado, atascado), odometría y el carro con su rumbo; leyenda en palabras | `pestanas/carro.py` | — |
| K4 | Pista desde `/api/geometria` del supervisor o, si no corre, desde la demo grabada; "No hay geometría" si ninguna | `datos.py` | — |
| K5 | Tabla de eventos del recorrido | `pestanas/carro.py` | — |
| K6 | Tabla de viajes del carro (sale, ida, ¿entregado?, viaje completo) | `pestanas/carro.py` | — |
| K7 | Órdenes al carro: detener, retomar la línea, ir a la meta, volver al muelle, avanzar N cm, retroceder (máx. 30), girar ± grados, ir al punto (x, y), con la nota de seguridad y la respuesta | `pestanas/carro.py` (panel "Mover el carro", al lado del mapa) | `test_ordenes_al_carro` |

## Pestaña Montaje real

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| T1 | Nota: valores PROVISIONALES, detalle en `docs/replicacion.md` | `pestanas/montaje.py` | — |
| T2 | Indicadores: ciclo de la cinta, ritmo (elem/min), esta corrida en el montaje real (s), reacción de la cortina | `pestanas/montaje.py` | — |
| T3 | Tabla del presupuesto de tiempos (necesita, disponible, margen, OK / NO CABE / "espera aceptada" en ámbar para las esperas del carrusel que el grupo aceptó, con su nota; por qué), con tildes y la estación de la cámara actual (`textos.con_tildes`, sin tocar `control/tiempos.py`) + aviso de margen justo (<15 %) | `pestanas/montaje.py` | `test_la_tabla_de_tiempos_tiene_tildes_y_esperas_aceptadas` |
| T4 | Errores de los sensores en esta corrida (falsos rechazos, falsas aceptaciones, clase equivocada) o "sensores perfectos"; nota de lecturas por decisión | `pestanas/montaje.py` | — |
| T5 | Costo del proyecto en Colombia por subsistema (barras) + tabla de dónde abaratar | `pestanas/montaje.py` | — |
| T6 | Monedas por medir (clases con medidas provisionales) | `pestanas/montaje.py` | — |

## Pestaña Asistente

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| A1 | Chips de proveedores: DeepSeek ✓/sin clave, local <modelo> ✓/apagado, reglas ✓ | `pestanas/asistente.py` | — |
| A2 | Explicación de qué se le puede pedir; aviso si no hay DeepSeek ni modelo local (cómo configurarlos) | `pestanas/asistente.py` | — |
| A3 | Precarga del modelo local (una vez por sesión) y de Whisper (hilo, una vez) | `pestanas/asistente.py` | — |
| A4 | Entrada de texto (`st.chat_input`) | `pestanas/asistente.py` | `test_el_asistente_responde_en_el_dashboard_sin_deepseek` |
| A5 | Micrófono (`st.audio_input`): Google con internet, Whisper sin internet; "Última frase oída con: …"; aviso si no entendió | `pestanas/asistente.py` | — |
| A6 | "🔊 Responder en voz alta" (gTTS o voz de Windows, reproducción automática) | `pestanas/asistente.py` | — |
| A7 | "Quién responde": Automático / Solo DeepSeek / Solo el modelo local / Solo reglas | `pestanas/asistente.py` | — |
| A8 | 8 ejemplos clicables | `pestanas/asistente.py` | `test_pestana_asistente_tiene_sus_controles` |
| A9 | Las órdenes que salen válidas van a la tabla `ordenes` | `pestanas/asistente.py` | `test_el_asistente_responde…` |
| A10 | Aviso de la respuesta, órdenes descartadas, "Documentos que consultó" | `pestanas/asistente.py` | — |
| A11 | Historial: lo más nuevo arriba, cada pregunta con su respuesta debajo; órdenes enviadas; quién respondió; "$" escapado (no LaTeX); "Todavía no le ha preguntado nada" | `pestanas/asistente.py` | `test_el_asistente_responde…` |
| A12 | "Qué pasó con las órdenes" (se refresca solo) | `pestanas/asistente.py` | — |
| A13 | "🗑 Borrar la conversación" | `pestanas/asistente.py` | — |

## Pestaña Ayuda

| # | Función | Dónde queda | Prueba |
|---|---|---|---|
| H1 | Qué hace el sistema en tres pasos (clasificar, empacar, entregar) | `pestanas/ayuda.py` | — |
| H2 | Qué muestra cada pestaña | `pestanas/ayuda.py` (+ la pestaña Pruebas nueva) | — |
| H3 | Palabras que aparecen (lote, cortina, rechazo por material/visión, radio, peso estimado, del turno anterior, espera aceptada, odometría); el asistente se describe en su orden real: DeepSeek → modelo local qwen2.5 (Ollama) → reglas | `pestanas/ayuda.py` | — |
| H4 | "Para ver la planta en 3D … abra visor.bat" | `pestanas/ayuda.py` | — |

## Frases simples de los eventos (para quien no conoce el sistema)

Se conservan todas, palabra por palabra (`textos.py`): moneda aceptada, pieza rechazada con su
causa y qué filtra, lote a un vaso, descarga del vaso (entrega / vacío / rechazo), sabotaje
detectado, cortina, alarma, los 25 eventos del carro (carga, salida, obstáculo, evasión, meta,
radio, órdenes, bloqueos…), pruebas del operador y órdenes del asistente.

## Lo que cambia de lugar (y por qué)

Antes los controles de prueba estaban repartidos en tres sitios: "Probar un filtro" y "Colocar una
pieza" en la barra lateral, los sabotajes y el fin de turno debajo de las cintas en Línea en vivo, y
las órdenes al carro en un desplegable cerrado arriba del mapa. Ahora:

- **Barra lateral** = solo manejar la línea (empezar, pausa, seguir, paro, velocidad, lote, ajustes).
- **Pestaña 🧪 Pruebas** = todo lo que se le hace a la planta para ver si se da cuenta sola, en el
  mismo orden que el visor 3D: 1 Probar un filtro · 2 Colocar una pieza · 3 Sabotajes (vasos,
  manos, radio del carro) · 4 Fin de turno; a la derecha, qué respondió la línea y qué pasó.
- **Carro y ruta** = el mapa con el panel "Mover el carro" al lado (siempre visible, no escondido).

## Verificación (2026-09-28)

- **Pruebas** (`tests/app/test_dashboard.py`, 38 casos con AppTest): cada una de las 9 pestañas carga
  sin excepción con la base vacía y con una corrida completa, y muestra su contenido; los alias
  viejos de `?pestana=` abren la correcta; solo se dibuja la pestaña abierta; avisos SIN INTERNET,
  NO ES EN VIVO, ESP32 EMULADO y prueba de un filtro; barra lateral completa (botones, velocidad,
  lote, ajustes avanzados) y sus órdenes; los 11 botones de la pestaña Pruebas y sus órdenes
  (filtro, colocar, sabotaje); apagados sin línea; los 9 botones del carro y sus órdenes; el
  asistente (controles, respuesta sin DeepSeek con la orden en `ordenes`, un ejemplo con un clic,
  "$" sin LaTeX); `app/lanzar.py` arranca el paquete nuevo.
- **Capturas** con Chrome sin ventana, de cada pestaña, contra la base real (corrida terminada) y
  contra una corrida a mitad (piezas en las casillas, mano en la cortina, botones activos),
  comparadas con las del dashboard anterior.
- Aviso conocido: en la PRIMERA carga en frío de la pestaña Asistente la consola del navegador
  puede mostrar `Recording error: Container not found` (del componente de micrófono de Streamlit,
  mientras el script todavía corre); el micrófono aparece y funciona, y no se repite al recargar.
