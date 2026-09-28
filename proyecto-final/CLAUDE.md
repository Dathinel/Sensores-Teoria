# Sistema de Logística de Monedas Inteligentes

> **LEER PRIMERO `CONTEXTO-SESION.md`** (mismo directorio): reglas estrictas del usuario, lo
> PROHIBIDO (celdas de carga, sensores difíciles o sensibles, cambios grandes no pedidos) y
> en qué quedó el trabajo. Revisar cada punto del mensaje del usuario uno por uno.

Documento maestro de contexto. Este archivo vive en la raíz del repositorio y se lee al
inicio de cada sesión de trabajo. Todo lo que está aquí es la fuente de verdad del
proyecto. Si una instrucción puntual del usuario contradice este archivo, gana la
instrucción puntual y se actualiza este archivo al terminar.

---

## 0. Cómo usar este archivo

Lea primero las secciones 1 a 3 para entender qué se entrega y por qué. La sección 5 es la
descripción funcional completa del sistema y es la referencia contra la cual se valida
cualquier implementación. Las secciones 8 a 15 definen la arquitectura de software y los
contratos que no se deben romper. La sección 16 es el plan de trabajo por fases: antes de
escribir código, identifique en qué fase está el repositorio y trabaje solo sobre la fase
actual. La sección 17 son reglas de comportamiento del agente.

---

## 1. Qué es el proyecto

Proyecto del segundo corte de Micros y Laboratorio, quinto semestre de Ingeniería
Mecatrónica, Universidad Militar Nueva Granada.

Objetivo general del enunciado: diseñar e implementar un sistema logístico de monedas
inteligentes desarrollado con la ESP32, con estructuras mecánicas y electrónicas propias,
que permita una conexión inalámbrica por medio de un aplicativo web en Streamlit, donde se
visualice la integración de un contador de monedas, un módulo de transporte y embalaje
conectado al final con un sistema de recolección de los vasos que contienen las monedas, y
un vehículo que siga una trayectoria dada con tres obstáculos hasta llegar a la meta,
mientras se tiene en un dashboard el seguimiento de la ruta y el valor de las monedas
procesadas con variables de peso, cantidad y valor, y finalmente un chatbot asistente que
exponga los datos del proyecto.

Entrega: enlace a repositorio de GitHub con el paso a paso documentado. El profesor
comparte una base en URDF en https://github.com/dialejobv/U_Militar que sirve de punto de
partida opcional.

## 2. Qué le toca a este grupo

El curso repartió elementos diferenciales por grupo. A este grupo le corresponde el
elemento 7: detector de elementos de monedas y vasos. Es decir, además de todo el sistema
general, la especialidad y el peso técnico de la sustentación está en la detección y el
filtrado confiable de qué entra al sistema y qué se rechaza.

Consecuencias prácticas de tener el elemento 7:

El sistema debe aceptar monedas colombianas de la familia antigua y de la familia nueva,
incluyendo piezas desgastadas, manchadas o descoloridas por el uso. Debe rechazar botones
de plástico, botones metálicos de medida similar a una moneda, bloques de colores y monedas
de otros países. Los filtros se van a probar uno por uno durante la sustentación, por lo
que cada etapa debe poder demostrarse de forma aislada y debe aportar información que las
otras etapas no aportan. Ninguna etapa puede ser un cuello de botella donde lo rechazado se
atasca: todo rechazo sale de la línea. **Grupo (2026-09-25): "filtro total"** — en vez de un
expulsor lateral por etapa, TODO sigue hasta la descarga y una sola compuerta de desvío manda lo
que no pasó a UNA bandeja de rechazo (menos sensores, menos servos, cinta más corta). Cada etapa
se sigue demostrando por separado porque cada rechazo queda registrado con su causa.

El filtrado también aplica al subsistema de vasos. Durante la operación pueden retirar un
vaso de la línea, reemplazarlo por una figura distinta o introducir un objeto extraño como
una mano. El sistema debe detectarlo y reaccionar sin hacer un paro total de la línea de
producción.

Condición que simplifica el diseño: los elementos a filtrar se colocan de a uno, de forma
manual y ordenada, por el mismo grupo. No hace falta tolva, embudo de singulación ni disco
de alveolos. El sistema no tiene que crear la fila, solo tiene que no perderla.

## 3. Entregables de este corte

1. Arquitectura del sistema con requerimientos funcionales y no funcionales, diagramas de
   bloques por módulo, y selección y justificación de materiales.
2. Diseño mecánico y electrónico con modelos CAD, planos y esquemas eléctricos. Se acepta
   desarrollo en PyBullet con archivos URDF.
3. Construcción de los primeros módulos con avances funcionales. En esta etapa se aceptan
   diseños simulados en PyBullet del funcionamiento del sistema.
4. Aplicación web en Streamlit comunicada de forma inalámbrica con el ESP32 por Bluetooth,
   ESP-NOW o Wi-Fi, con las primeras visualizaciones de las métricas.

El foco de trabajo actual es todo el software y la simulación completa del comportamiento.
El hardware real se integra después reemplazando el backend de la capa de abstracción,
nunca reescribiendo la lógica.

---

## 4. Arquitectura física del sistema

Cuatro subsistemas.

**Estación de filtrado y conteo.** Una cinta transportadora indexada, de superficie negra
mate, con separadores cada 40 mm que definen casillas. La mueve un motor paso a paso en
modo avanzar y detener: avanza exactamente una casilla, se detiene 1000 ms (`tiempos_ms`), vuelve
a avanzar. La cámara de cada cinta ve sus separadores y mide, después de cada avance, si la
cinta quedó en su casilla; si se corrió, se corrige con micropasos en la misma pausa (grupo,
2026-09-25: reemplaza al sensor de ranura que proponía esta sección). Sobre esa cinta se montan las estaciones fijas
descritas en la sección 5: presencia, material, visión y descarga (4 casillas desde el
2026-09-25). Al final, el almacén tipo revólver (6 tubos en un carrusel que gira sobre una placa
fija con un solo agujero sobre el vaso de llenado).

**Estación de embalaje.** Una segunda cinta indexada, perpendicular o en línea con la
primera, con casillas que encajan la base del vaso. Contiene la verificación de vaso, el
llenado, el dispensador de tapas por gravedad, la prensa de tapa y el empujador de
descarga.

**Canaleta de entrega.** Dos rieles a 15 grados, forrados con cinta de PTFE, que sostienen
el vaso colgado por la pestaña del reborde (8 mm). El centro de masa queda por debajo del
punto de apoyo, así que el vaso no puede volcarse. Entrada en embudo; los vasos se acumulan en
fila contra un escape de dos dedos movido por un servo, que suelta uno a la vez.

**Vehículo autónomo.** Dos ruedas motrices + rueda loca de bola (usuario, 2026-09-26: tres
apoyos siempre tocan el piso y gira sobre su eje sin patinar), puente H, arreglo de cinco
sensores infrarrojos de línea, sensor ultrasónico frontal, encoders de 20 ranuras y dos
rodillos guía en las esquinas traseras. Sigue una línea negra con tres obstáculos sobre la
pista, los esquiva hacia el lado con más espacio, llega a la meta, espera que saquen el vaso
y vuelve SOLO al muelle, entrando de reversa. La cuna de carga son los mismos rieles de la
canaleta (3 mm más bajos, en embudo, con PTFE, espuma adelante y lengüeta atrás), de modo que
el vaso pasa deslizando sin necesidad de brazo robótico.

---

## 5. Secuencia de operación, ciclo completo

Esta es la descripción funcional de referencia. La simulación y el firmware deben
reproducirla paso a paso.

1. El operador coloca un elemento en la casilla de carga de la cinta de monedas durante una
   de las pausas.
2. Estación 1, presencia. Un sensor infrarrojo confirma que la casilla está ocupada y crea
   un registro para esa casilla. Si está vacía, la casilla se marca vacía y las demás
   estaciones la ignoran durante todo su recorrido.
3. Estación 2, material. Un sensor capacitivo y uno inductivo leen el elemento. Van DEBAJO de
   la cinta, mirando hacia arriba, a través de la banda (grupo, 2026-09-26): el capacitivo
   centrado bajo E1 (su lectura viaja en el registro) y el inductivo (M18, 8 mm) bajo E2.
   Capacitivo activo e inductivo inactivo significa material no metálico. Ambos activos
   significa metal. El resultado se guarda en el registro de la casilla.
4. **Grupo (2026-09-25), filtro total:** ya no hay expulsores a mitad de la cinta ni estación
   libre. Lo no metálico queda rechazado en E2 (sin gastar la cámara) y sigue hasta la descarga.
5. (Estación libre eliminada.)
6. Estación 3, visión. La casilla queda quieta bajo una cámara cenital con anillo de luz
   difusa. Como la cinta es negra mate, la cinta misma es el fondo de contraste. El PC
   captura, segmenta el elemento, mide diámetro real en milímetros con la calibración de
   escala, evalúa circularidad, busca contornos internos y clasifica la cara de la moneda
   con el modelo entrenado. Devuelve denominación y confianza, o la clase otro. La misma
   imagen mide si la cinta de monedas quedó en su casilla.
7. (Segundo expulsor eliminado: todo rechazo sale por la descarga.)
8. Estación 4, descarga. La pieza cae por el extremo de la cinta a un embudo; una compuerta de
   desvío a prueba de fallas (en reposo apunta al rechazo) la manda por un canal corto y
   empinado a la boca del tubo del carrusel que está en la carga, o a la ÚNICA bandeja de
   rechazo. Solo abre hacia el almacén para una moneda registrada y aceptada; todo lo demás,
   sea cual sea su causa (o si ningún sensor lo registró), va a la bandeja. El almacén es un
   revólver: 6 tubos (50, 100, 200, 500, 1000 y "otras"; la familia no importa) en un
   carrusel movido por un motor paso a paso con referencia por sensor Hall; la moneda cae casi
   vertical al tubo de su denominación. **Reglas del grupo (2026-09-22): ninguna moneda
   colombiana aceptada se descarta —si no tiene vaso, se guarda— y cada vaso lleva una sola
   denominación.** Si el tubo está lleno, la moneda espera en la descarga y la cinta de
   monedas se detiene; nunca se bota.
9. Verificación de vaso, en la cinta de embalaje, antes del llenado. **Grupo (2026-09-25):
   las barreras IR se reemplazaron por visión.** Una cámara de vasos al costado de la cinta,
   con un panel de luz detrás (silueta a contraluz), mira en cada estación dos franjas de la
   imagen ("barreras virtuales"): una a media altura del vaso que debe estar ocupada, y otra
   justo por encima del borde que debe estar libre. Ambas condiciones correctas significa
   vaso válido. Cualquier otra combinación marca la casilla como inválida. La misma cámara
   (el profesor también puede cambiar los vasos, 2026-09-22) lee el marcador ArUco de cada
   vaso personalizado; en el llenado y en la tapa se vuelve a leer y, si el número cambió, el
   vaso fue cambiado por otro igual y se invalida. Si no se puede leer el marcador, decide la
   silueta. El marcador va en una CINTA alrededor de todo el vaso (el mismo ArUco 6 veces:
   siempre hay uno de frente). Los vasos son OPACOS (grupo, 2026-09-25): que lleguen vacíos lo
   mide un VL53L0X que mira desde arriba al interior del vaso en la verificación (un vaso con algo
   adentro no entra). NO hay celdas de carga: el grupo las prohíbe. Cada avance de cada cinta
   lo confirma su cámara midiendo dónde quedaron los separadores; si la cinta se corrió, se
   re-sincroniza (`desfase_corregido`).
10. Llenado por lotes. Cuando un tubo junta un lote completo (`planta.monedas_por_vaso`),
    el carrusel pone ese tubo sobre el agujero de la placa, se abre el obturador y el lote
    entero cae por un embudo corto al vaso, que queda con una sola denominación. Justo antes, la cámara de vasos
    re-verifica en el llenado (las mismas dos franjas) que ahí haya un vaso: una figura o un
    vaso retirado no reciben nada. Después, la cámara confirma que las monedas llegaron al
    fondo (si no, `lote_no_confirmado`: el vaso sale por rechazo). Si no hay vaso válido, la cinta de vasos avanza buscando la siguiente
    casilla válida y las monedas siguen guardadas. No hay paro de línea, solo un salto de
    casilla. Lote de 10 por defecto, ajustable en caliente desde el dashboard (orden `lote`;
    grupo, 2026-09-22: depende de cuántas monedas traiga el profesor). Al final del turno lo
    que quedó en los tubos se empaca en vasos incompletos, cada uno de una sola denominación
    ("Embalar lo guardado"), o se deja guardado y el turno siguiente arranca con eso
    (`planta.conservar_almacen_entre_turnos`, tabla `almacen_turno`). Los vasos son genéricos:
    la denominación de un vaso la decide el tubo que se abre sobre él. Un tubo lleno sin vaso
    donde soltarlo no bota nada: la moneda espera en la descarga, la cinta de monedas se detiene y se
    avisa al operador (alarmas `tubo_lleno` / `faltan_vasos`).
11. Estación de tapa. Se repite la verificación de presencia y altura en ese instante, con
    la cámara de vasos. No se confía en el estado registrado antes. Si el vaso está lleno y
    sigue válido, el escape de servo del tubo vertical de tapas suelta una tapa que cae ~13 mm
    por gravedad y se centra sola por el cono de la tapa. Un vaso vacío no se tapa ni se
    prensa: se desecha (grupo, 2026-09-25: la cinta queda libre y cada corrida arranca de 0).
    La misma cámara confirma que la tapa quedó puesta (sin sensor aparte); si no, se suelta
    otra una vez y si tampoco, el vaso queda inválido. Si el vaso fue retirado o cambiado, no
    se suelta tapa.
12. Prensa. Una leva excéntrica movida por un servo MG996R (0 → 180 → 0 grados; con 6,5 mm
    de excentricidad empuja con ≥150 N, y una tapa pide ~30-50 N, PROVISIONAL) asienta la tapa
    a presión con la cinta detenida. El servo sabe su ángulo: no hay sensor de posición ni
    puente H. Un resorte limita la fuerza máxima, de modo que un objeto extraño no rompe nada.
    Antes de prensar, la cámara de vasos (que también ve esta casilla) revisa vaso, marcador,
    tapa y fondo.
13. Descarga. En la última casilla, si el registro dice vaso válido con tapa, un empujador
    (servo con manivela) pasa el vaso de lado a la canaleta de entrega. Si no, no se empuja:
    en el siguiente avance la cinta lo deja caer por su extremo a la bandeja de rechazo de
    vasos (un empujador solo empuja hacia un lado). Ahí caen también los vasos vacíos
    (desechados): que llegó vacío lo confirmó el sensor del interior, no solo el registro. Si la canaleta
    está llena, el vaso tapado espera en la descarga y la cinta de vasos se detiene (la de
    monedas sigue). Al terminar una corrida la cinta de vasos se vacía.
14. Cortina de seguridad. UN sensor de distancia (VL53L0X) a media altura (65 mm sobre la
    cinta), mirando a lo largo de la zona de tapa y prensa, del lado del operador, con el eje a
    85 mm del eje de la cinta: su cono real (~25°) no toca vasos, tapa, prensa ni cinta. No es un
    equipo de seguridad certificado; lo que se busca es que el sistema se detenga si ve una mano:
    la prensa SUBE y se detiene arriba, tapa y empujador se congelan y la cinta de vasos se
    detiene. La cinta de monedas continúa. Al despejarse, la cámara revisa los vasos antes de
    seguir (`retirado_con_mano`) y la línea retoma donde iba. Como una mano puede sacar un vaso
    por encima sin cruzar el haz, la cámara de vasos revisa además en CADA tick que ninguna de
    sus 4 casillas haya quedado sin su vaso (`retirado`, estación `camara`).
15. Acople. El vehículo entra de reversa al muelle de carga (guías en V que empujan sus
    rodillos traseros, topes con espuma) y sabe que llegó porque los encoders dejan de contar
    contra el tope; avisa por ESP-NOW. Secuencia segura: la cuna tiene que estar vacía, el
    escape de dos dedos suelta UN vaso y el infrarrojo de la cuna confirma la carga.
16. Ruta. El vehículo sigue la línea, detecta cada muro con 3 lecturas seguidas del
    ultrasónico, mira a ±30° y esquiva hacia el lado con más espacio (45° afuera, derecho,
    60° de vuelta hasta VER la línea), llega a la meta (franja negra), espera que saquen el
    vaso y vuelve solo; en la marca de giro da media vuelta, se endereza y entra de reversa al
    muelle. Publica eventos durante todo el trayecto (tabla `ruta`).
17. Telemetría. El ESP32 fijo envía todos los eventos por USB serial al PC. El PC persiste
    en base de datos y alimenta el dashboard y el chatbot.

---

## 6. Datos de referencia de las monedas

Valores nominales aproximados. El desgaste mueve décimas de milímetro en diámetro y algo
más en masa. Estas cifras se usan para el cálculo de peso estimado y como compuertas
previas de la visión, nunca como criterio único de aceptación.

**La tabla completa vive en `config/monedas.yaml`** (fuente única, la lee
`control/monedas.py`). A pedido del grupo (2026-09-22) tiene cuatro generaciones: `nueva`
(la última), `antigua` (la penúltima) y, "por si acaso", `muy_antigua` e `historica`, con
medidas PROVISIONALES sin verificar (`verificado: false`) que hay que medir con calibrador y
báscula. Solo 50, 100, 200, 500 y 1000 tienen tubo en el almacén; las demás denominaciones
aceptadas van al compartimiento "otras" (se guardan, no se empacan). Las 9 filas de abajo
son las verificadas:

| Denominación | Familia | Diámetro mm | Masa g | Ferromagnética | Bimetálica |
|---|---|---|---|---|---|
| 50 | nueva | 17.0 | 2.0 | sí | no |
| 100 | nueva | 20.3 | 3.3 | sí | no |
| 50 | antigua | 21.5 | 4.5 | no | no |
| 200 | nueva | 22.4 | 4.6 | no | no |
| 100 | antigua | 23.0 | 5.3 | no | no |
| 500 | antigua | 23.5 | 7.4 | no | sí |
| 500 | nueva | 23.7 | 7.1 | no | sí |
| 200 | antigua | 24.4 | 7.1 | no | no |
| 1000 | nueva | 26.7 | 10.0 | no | sí |

Nota importante para el informe: con monedas extranjeras en juego, el diámetro deja de ser
discriminante. Una moneda de un euro mide 23.25 mm y cae dentro del grupo de las de 500.
Una de veinte céntimos mide 22.25 mm y cae junto a la de 200 nueva. Por eso la decisión
final es por reconocimiento de la cara y no por geometría. El sistema garantiza rechazar lo
que no reconoce con confianza suficiente, no garantiza reconocer cualquier moneda del
mundo.

El peso reportado en el dashboard es peso estimado por conteo, calculado como la suma de
masas nominales de las monedas identificadas. No hay celda de carga en el diseño (el grupo
las prohíbe, 2026-09-25). Esto debe quedar explícito en la interfaz y en el informe.

---

### Replicación en la vida real

Regla del grupo (2026-09-22): todo tiene que poder replicarse en el montaje real con sus
tiempos, medidas y el error individual de cada sensor, y todo eso queda anotado. Fuentes:
`tiempos_ms` y `errores_sensores` en `config/parametros.yaml` (PROVISIONALES, de hoja de
datos), los datos de cada sensor en `sim/catalogos.py` y el presupuesto de tiempos en
`control/tiempos.py`. `docs/replicacion.md` se genera de ahí (`python -m app.documentos`) y
lista qué medir y cómo. La simulación usa esos errores (supervisor y demo; las pruebas los
apagan) y cada estación decide por mayoría de `planta.lecturas_por_decision` lecturas.

Sensores optimizados (grupo, 2026-09-25): se reemplaza por visión lo que se pueda. Las 6
barreras IR y los 2 sensores de presencia de vasos pasaron a ser franjas de la cámara de
vasos, y los 2 sensores de ranura, la medición de los separadores con la cámara de cada cinta
(toda la línea depende del PC de todos modos). Con el filtro total se quitaron también las 2
confirmaciones de expulsión; se agregaron el sensor del interior del vaso (VL53L0X, vasos
opacos), el Hall de referencia del carrusel y el láser frontal del carro (2026-09-26): 13 sensores. La cámara de vasos
ve 4 casillas (verificación a prensa). Se quedan como sensores
físicos, a propósito: el capacitivo/inductivo (la cámara no distingue plástico pintado de
metal), la cortina (la seguridad no puede depender del PC), el sensor del interior (la cámara no
ve adentro de un vaso opaco), el Hall (el motor del carrusel necesita una referencia) y los del
carro (no lleva cámara).

Modelo físico (2026-09-25): todo lo que se mueve lo hace dentro de sus límites y con su
mecanismo (carrusel del almacén con motor y obturador, empujador con manivela, leva de la
prensa, desvío de la descarga), y nada queda en el aire: la mesa de monedas (43 cm, para que
la moneda baje por gravedad al carrusel y de ahí al vaso) y un pórtico trasero de perfil 2020
(viga a 40 cm) sostienen almacén, tubo de tapas, prensa y panel de luz. Rieles de la canaleta a
69 mm (el cuerpo del vaso, 62 mm, pasa entre ellos; la pestaña del reborde, 72 mm, se
apoya). El visor 3D (`app/visor3d/visor.js`) es además el boceto de presentación: tiene que
verse pulido.

Tiempos LENTOS a propósito (grupo, 2026-09-22: el montaje real verifica con calma): pausa de
1000 ms, ciclo de 1,6 s. La simulación corre con esos mismos tiempos (supervisor a velocidad 1 y
ventana de PyBullet).
El conexionado y los voltajes de cada componente están en `sim/conexiones.py` (fuente única) →
`docs/conexiones.md`, y la revisión de cada sensor en `docs/revision-final.md`.

## 7. Reglas de decisión del filtrado

La decisión final por elemento se construye acumulando evidencia de etapas independientes.
Cada etapa escribe en el registro de la casilla y ninguna etapa puede revertir un rechazo
anterior.

Etapa de material. No metálico implica rechazo inmediato con causa `no_metalico`. Metálico
continúa.

Etapa de geometría, calculada por visión antes de clasificar. Diámetro fuera del rango de
16.5 a 27.5 mm implica rechazo con causa `fuera_de_rango`. Circularidad por debajo de 0.90
implica rechazo con causa `no_circular`, lo que se lleva bloques y fichas irregulares.
Presencia de contornos internos cerrados implica rechazo con causa `perforado`, lo que se
lleva arandelas y botones con ojales.

Etapa de clasificación. El recorte normalizado pasa al modelo. Si la clase ganadora es
`otro` o la confianza es menor a 0.85, rechazo con causa `no_reconocida`. Si la clase es
una denominación colombiana con confianza suficiente, aceptación.

Etapa de coherencia. Si la denominación predicha tiene un diámetro nominal que difiere en
más de 1.2 mm del diámetro medido, rechazo con causa `incoherente`. Esta regla cruza dos
mediciones independientes y es la que hay que resaltar en la sustentación como ejemplo de
filtros que se complementan.

Para los vasos, el estado de casilla es una máquina de estados con los valores `vacia`,
`valida`, `invalida`, `llenando`, `llena`, `tapada`, `rechazada`, `entregada`. Cada
estación relee sus sensores antes de actuar y puede degradar el estado a `invalida` en
cualquier momento.

---

## 8. Arquitectura de software

Regla central: la lógica de control se escribe una sola vez y corre contra dos backends
intercambiables, simulación y hardware real. Nada de la lógica puede importar PyBullet ni
pyserial directamente.

Capas, de abajo hacia arriba:

**Capa de abstracción de hardware.** Define interfaces abstractas para actuadores y
sensores: banda indexada, servo, motor de prensa, dispensador de tapas, sensor discreto,
sensor de distancia, cámara. Dos implementaciones concretas. El backend `sim` traduce cada
llamada a comandos de PyBullet y cada lectura a consultas del mundo simulado. El backend
`real` traduce cada llamada a un mensaje serial hacia el ESP32 y cada lectura a un campo de
la telemetría recibida.

**Capa de control.** La máquina de estados de la línea, el registro de casillas, las reglas
de decisión de la sección 7 y la secuencia de la sección 5. Es código puro de Python sin
dependencias de entorno, y por eso es la capa que se puede probar con pruebas unitarias sin
abrir ninguna ventana.

**Capa de percepción.** El pipeline de visión. Recibe una imagen y devuelve un veredicto.
En backend real la imagen viene de la webcam. En backend sim la imagen viene del render de
PyBullet o de un banco de fotos reales, y el clasificador puede operar en modo oráculo con
ruido configurable para poder probar la línea antes de tener el modelo entrenado.

**Capa de persistencia y servicios.** Base de datos SQLite con los eventos, el proceso
supervisor que corre la línea y escribe eventos, el dashboard de Streamlit que solo lee, y
el chatbot que consulta el estado.

Separación de procesos. Un proceso llamado supervisor corre la línea, la visión y la
comunicación, y escribe en SQLite. Otro proceso corre Streamlit y solo lee de SQLite y
escribe comandos en una tabla de órdenes. Mezclar la cámara y el puerto serial dentro de
Streamlit lo vuelve inestable porque Streamlit reejecuta el script en cada interacción.
Esta separación no es negociable.

---

## 9. Estructura del repositorio

Reorganizada el 2026-09-26 a pedido del usuario: solo lo que se usa. Lo que se visualiza
es el visor 3D (`visor.bat`); el dashboard de Streamlit se mantiene porque lo pide el
enunciado. Las carpetas de fases futuras (firmware/, vision/, cad/, docs de planos y
esquemas) se crean cuando empiece esa fase, no antes.

```
/
  CLAUDE.md                     este archivo
  CONTEXTO-SESION.md            reglas del usuario y en qué quedó el trabajo (leer primero)
  README.md                     resumen público y cómo verlo
  visor.bat                     doble clic: abre visor-portable.html y arranca la simulación por detrás
  visor-portable.html           visor en UN archivo (demo embebida); pasa solo al vivo (generado)
  .env.example                  cómo poner DEEPSEEK_API_KEY (el .env real queda fuera de git)
  requirements.txt
  config/parametros.yaml        umbrales, valores físicos, tiempos y errores de sensores
  config/monedas.yaml           tabla de monedas: 4 generaciones (sección 6)
  config/precios.yaml           precio en Colombia de cada componente + ahorros propuestos (→ docs/costos.md)
  .streamlit/config.toml        tema del dashboard
  docs/
    paso-a-paso.yaml            los 17 puntos con su estado de revisión (fuente única)
    paso-a-paso.md, sensores.md, componentes.md, replicacion.md, conexiones.md   generados (python -m app.documentos)
    bitacora.md                 avance y decisiones por sesión
    enunciado/                  la guia del parcial (segundo-parcial-umng.pdf) y sus figuras, numeradas; README.md
  control/                      lógica pura (sin PyBullet ni pyserial)
    hal/interfaces.py           clases abstractas de sensores y actuadores
    hal/backend_sim.py          la HAL sobre la simulación
    hal/backend_real.py         la HAL sobre el ESP32 (telemetría y comandos del puente serial)
    linea.py                    máquina de estados de la cinta de monedas
    embalaje.py                 máquina de estados de la cinta de vasos
    registro.py                 registro de casillas y transiciones
    reglas.py                   reglas de decisión de la sección 7
    almacen.py                  tubos por denominación (ninguna moneda se descarta)
    vehiculo.py                 control del carro: línea, evasión, meta, vuelta y muelle; órdenes (fase 7) y odometría
    protocolo.py                mensajes numerados, ack, latido y reglas del enlace (punto 15)
    monedas.py                  tabla de referencia y utilidades
    tiempos.py                  presupuesto de tiempos del montaje real
  sim/
    planta.py                   LA simulación de la línea: cintas, almacén, canaleta, carro
    mundo.py                    escena de PyBullet de las dos cintas (urdf/)
    sensores_sim.py             sensores emulados, incluida la cámara en modo oráculo
    vehiculo_sim.py             el carro con física real, en su propio mundo
    pista.py                    línea central de la pista a partir de sus tramos
    geometria.py                geometría de todo el sistema para el visor 3D
    catalogos.py                sensores numerados y lista de materiales (sin dependencias)
    conexiones.py               conexionado pin a pin: módulos, pines, cada hilo (fuente única)
    carga_escenarios.py         lectura de escenarios YAML
    escenarios/                 prueba_completa.yaml (la única prueba de la interfaz)
  app/
    lanzar.py                   supervisor + dashboard (lo usa visor.bat)
    supervisor.py               corre la simulación, escribe SQLite, sirve el visor
    servidor.py                 HTTP del supervisor: visor 3D + /api/estado (127.0.0.1)
    visor3d/                    visor 3D en Three.js (vendor/ local, sin CDN; demo/ grabada)
    dashboard.py                aplicación Streamlit (incluye la pestaña Asistente y los botones de órdenes al carro)
    asistente.py                fase 7: DeepSeek (JSON), búsqueda en la documentación, estado en vivo, intérprete local, voz
    db.py                       esquema y acceso a SQLite
    configuracion.py            carga de config/parametros.yaml
    grabar_demo.py              graba una corrida para el modo demo del visor (y rehace el portable)
    portable.py                 arma visor-portable.html (three.js en data: URLs + visor + demo)
    documentos.py               genera los .md de docs/ (incluido costos.md)
    costos.py                   lee config/precios.yaml: totales por subsistema, ahorros
    evaluar_asistente.py        batería REAL del asistente (24 casos) -> docs/pruebas-asistente.md
    puente_serial.py            fase 8: PC <-> ESP32 fijo (y estación EMULADA si no hay placa)
  firmware/                     fase 8, MicroPython (ver firmware/README.md)
    fijo/  carro/  comun/       lógica pura (se prueba en el PC) + hw.py (pines) + main.py
    preparar.py, subir.py       arma salida/<placa>/ (pines y config generados, .mpy) y la sube con mpremote
  tests/                        pruebas (+ escenarios/ de un solo filtro y el mixto de 20)
```

---

## 10. Contratos de datos

Son la frontera entre módulos. Cambiarlos obliga a actualizar esta sección en el mismo
commit.

### 10.1 Protocolo: PC ↔ ESP32 fijo ↔ carro

Punto 15 (usuario, 2026-09-26). Lógica en `control/protocolo.py` (Python puro, con pruebas);
tiempos en `config/parametros.yaml`, clave `protocolo`.

Líneas de JSON terminadas en salto de línea, a 115200 baudios por USB entre el ESP32 fijo y
el PC. El parser tolera líneas cortadas o con basura: las descarta y las cuenta, nunca se cae.

**PC → ESP32 fijo: comandos numerados con confirmación.**

```json
{"t":"cmd","id":42,"dst":"linea","act":"avanzar"}
{"t":"cmd","id":43,"dst":"vasos","act":"tapar"}
{"t":"cmd","id":44,"dst":"canaleta","act":"soltar"}
```

El ESP32 contesta `{"t":"ack","id":42,"ok":true}` (o `"ok":false,"error":"..."`). Sin ack en
300 ms, el PC reenvía UNA vez; si tampoco llega, marca `fallo_comunicacion`. Si llega
repetido, el ESP32 vuelve a mandar el ack pero no ejecuta el comando dos veces.

**ESP32 fijo → PC: eventos y telemetría con número de secuencia `n`.** Un hueco en la
numeración es un mensaje perdido y se registra.

```json
{"t":"evt","n":1201,"ms":124503,"src":"linea","ev":"paso","casilla":17}
{"t":"evt","n":1202,"ms":124604,"src":"e2","ev":"material","capacitivo":true,"inductivo":false}
{"t":"tel","n":1203,"ms":130500,"linea":"run","vasos":"run","seguridad":"ok","casilla":17,"vaso":4}
```

**Latido en los dos sentidos: `{"t":"hb","n":...}` cada 500 ms.**
- Si el ESP32 no oye al PC en 2 s, hace una parada segura: cintas quietas, prensa arriba,
  desvío al rechazo y escapes cerrados.
- Si el PC no oye al ESP32, pausa la línea y da la alarma `sin_esp32`.

**Carro ↔ ESP32 fijo (ESP-NOW).** El fijo reenvía al PC con `src:"carro"`.
- **Eventos numerados.** El carro numera sus eventos (`id`) y le agrega la lectura del
  infrarrojo de la cuna. Los guarda (hasta 32) y los reenvía cada 500 ms hasta recibir el
  `ack`. El receptor descarta los repetidos.
- **Latido.** Cada 250 ms en los dos sentidos. Sin oír nada en 1 s, el enlace se da por
  perdido.

```json
{"t":"evt","src":"carro","id":88,"ev":"en_muelle","cuna":false,"x":0.36,"y":-0.51}
{"t":"evt","src":"carro","id":89,"ev":"estado","estado":"esperando_carga","fase":"vuelta","cuna":false}
{"t":"ack","dst":"carro","id":89,"ok":true}
```

**Órdenes al carro (fase 7, usuario 2026-09-27).** Las da el asistente o un botón del dashboard;
van por la radio (sin enlace no llegan) y el carro las valida otra vez (`ControlCarro.ordenar`):

```json
{"t":"cmd","id":57,"dst":"carro","act":"avanzar","distancia_m":0.3}
{"t":"cmd","id":58,"dst":"carro","act":"ir_a","x":1.2,"y":-0.3}
```

`act`: `detener`, `avanzar` (≤ 1,5 m), `retroceder` (≤ 0,3 m: atrás no hay sensor), `girar`
(±180°, positivo = izquierda), `ir_a` (x, y en metros, ≤ 2,5 m), `ir_meta`, `volver_muelle`,
`seguir_linea`. Una orden nueva reemplaza a la anterior. El carro sabe dónde está por odometría
(encoders), que se pone en la posición conocida cada vez que entra al muelle. Antes de moverse mira
el camino (láser al frente y a ±15°) y responde `camino_bloqueado` si algo cae dentro de su ancho;
en marcha se detiene con `bloqueado` (algo adelante) o `atascado` (una rueda cuenta mucho más que la
otra en una recta). Cumplida la orden queda en `esperando_orden`; `ir_meta`, `volver_muelle` y
`seguir_linea` terminan en el recorrido automático (buscan la línea con los infrarrojos,
`ruta_retomada`). La estación no le suelta un vaso a un carro que se movió por orden hasta que
vuelva a decir `en_muelle`.

**Reglas del carro:**
- El carro decide solo, con su infrarrojo de la cuna (3 lecturas iguales), que ya lo
  cargaron: sale del muelle.
- También decide solo que en la meta le sacaron el vaso: vuelve.
- Si pierde el enlace, termina la vuelta y queda en el muelle. En la meta espera como mucho
  `espera_meta_sin_enlace_s`; si nadie saca el vaso, vuelve con él.
- Al volver el enlace, lo primero que manda es su `estado`, con la cuna.

**Regla de la estación (`protocolo.puede_soltar_vaso`).** Suelta UN vaso solo si se cumplen
las cuatro condiciones:
- el enlace está vivo;
- tiene un estado del carro recibido después de la última reconexión;
- el carro está en el muelle;
- la cuna está vacía.

Si no, no carga. Si la cuna está ocupada, da la alarma `cuna_ocupada`.

### 10.2 Veredicto de visión

```json
{
  "casilla": 17,
  "diametro_mm": 23.68,
  "circularidad": 0.981,
  "contornos_internos": 0,
  "bimetalica": true,
  "clase": "500_nueva",
  "confianza": 0.94,
  "veredicto": "aceptada",
  "causa": null
}
```

Las causas posibles son exactamente las de la sección 7. No se inventan causas nuevas sin
actualizar este archivo.

### 10.3 Esquema de SQLite

Tablas mínimas. `eventos` con marca de tiempo, origen, tipo y carga útil en JSON.
`elementos` con casilla, veredicto, causa, denominación, valor, masa estimada, ruta de la
imagen capturada y marca de tiempo. `vasos` con identificador, estado, denominación (única por
vaso; columna agregada con migración en `app/db.py`), cantidad de monedas,
valor total, masa estimada y marcas de tiempo de llenado, tapado y entrega. `ruta` con
marca de tiempo, posición estimada, evento de obstáculo y estado del vehículo. `ordenes`
con comandos pendientes escritos por el dashboard y consumidos por el supervisor (cada respuesta
queda además como evento `respuesta`, con `origen` = `boton` o `asistente`). `asistente` (fase 7)
con la conversación: ts, rol (`usuario`/`asistente`), texto, modo (`deepseek`/`local`) y las órdenes
que salieron; la escribe el dashboard, la leen el dashboard y el visor (`/api/asistente`); no es tabla
de corrida. `almacen_turno`
(una sola fila) con lo que hay en los tubos; no es tabla de corrida, sobrevive a
`reiniciar_corrida` para que el turno siguiente arranque con esas monedas.

### 10.4 Telemetría en SQLite

El supervisor publica el estado completo de la planta (casillas de ambas cintas, todos
los sensores, cortina, estado de la línea) como una fila de `eventos` con `tipo = 'tel'`
y el estado en el payload JSON; el dashboard lee siempre la última. Es el equivalente en
base de datos del mensaje `t: tel` de la sección 10.1, así que no hay tabla propia. Los
eventos de la planta usan el mismo estilo `src`/`ev` del protocolo serial.

Identidad de los elementos: en `sim/planta.py` el id de registro de cada elemento es un
contador secuencial (`Elemento.id_registro`), no el `body_id` de PyBullet, porque
PyBullet reutiliza los `body_id` de cuerpos borrados (retirar o cambiar un vaso).

---

## 11. Simulación en PyBullet

Sirve para tres cosas: demostrar el funcionamiento antes de tener hardware, validar la
lógica de control contra escenarios que en físico son difíciles de repetir, y generar el
material visual de la sustentación.

**Escena.** Bancada, cinta de monedas con separadores, cuatro estaciones marcadas (filtro
total, 2026-09-25), una sola bandeja de rechazo, cinta de vasos, tubo de tapas, prensa, canaleta de entrega, pista con línea y
tres obstáculos, y el vehículo.

**Cómo se mueve la cinta indexada.** No hay que simular una banda flexible. Modele la cinta
como una plataforma con juntas prismáticas o, más simple y estable, mueva los cuerpos de
las casillas por control de posición en pasos discretos. La cinta indexada se presta
perfectamente a esto porque el movimiento real también es discreto. Un paso de casilla es
una interpolación de posición durante un número fijo de pasos de física, seguida de una
pausa.

**Elementos.** Las monedas son cilindros con radio y masa de la tabla de la sección 6, más
una textura por cara para el render de la cámara. Los botones plásticos son cilindros con
densidad baja y una bandera de material no metálico. Los botones metálicos son cilindros
con bandera de metal y agujeros modelados como textura y como propiedad. Los bloques son
cajas. Cada cuerpo lleva un diccionario de verdad de terreno con su clase real, que sirve
tanto para el modo oráculo como para calcular la matriz de confusión en las pruebas.

**Cómo se emula cada sensor.**

El infrarrojo de presencia se emula con `rayTest` entre dos puntos. Si el rayo golpea un
cuerpo que no es la cinta, el sensor está bloqueado. Las franjas de la cámara de vasos
(media altura y borde, en verificación, llenado y tapa) se emulan igual: lo que corta el
rayo es lo que taparía esa franja de la imagen a contraluz. Cada sensor lleva su
probabilidad de error configurable (`errores_sensores`) para probar la robustez.

El par capacitivo e inductivo se emula consultando la bandera de material del cuerpo que
esté dentro del volumen de la estación. El capacitivo responde a cualquier cuerpo presente,
el inductivo solo a los marcados como metálicos.

La cámara (cenital sobre E3, con la cinta negra como fondo) HOY es un oráculo: no hay render ni
pipeline de OpenCV todavía (`sim/sensores_sim.py`); lo previsto es emularla con `getCameraImage`
y pasar esa imagen por el mismo pipeline que usaría la webcam (fase 5, pendiente). El
clasificador corre en modo oráculo: lee
la clase real del cuerpo y le aplica un ruido configurable de confusión, de modo que la
línea completa se puede probar antes de tener el modelo entrenado.

El sensor de cortina se emula con su cono real: varios rayos repartidos dentro de un cono de
~25° (`cortina_seguridad`), a media altura y del lado del operador. La posición de las cintas que mide
la cámara y el sensor del interior del vaso se emulan con el estado del cuerpo simulado más su
error.
Para las pruebas de sabotaje, un script inyecta un cuerpo intruso en la escena a mitad de
línea, retira un vaso o lo sustituye por un cilindro de otra altura.

El vehículo tiene su propio mundo de PyBullet (`sim/vehiculo_sim.py`) con física real: ruedas
con motor de torque limitado, rueda loca sin roce, muros y muelle sólidos, vaso que cabecea.
El ultrasónico es un abanico de 5 `rayTest` (±7,5°) con ruido; cada infrarrojo de línea, la
distancia de su punto a la línea central (y a las franjas de meta y de giro) con lecturas
cambiadas a veces; los encoders, pulsos enteros del giro real de cada rueda. El control
(`control/vehiculo.py`) es Python puro. `simulacion.carro: fisico` lo usa el supervisor;
`reemplazo` (más rápido) lo usan las pruebas de la planta.

**Modos de ejecución.** El simulador debe correr en modo GUI para demostración y en modo
DIRECT sin ventana para las pruebas automáticas. Las pruebas de la línea deben poder correr
en DIRECT a velocidad acelerada, sin sincronizar con tiempo real.

**Escenarios reproducibles.** Defina archivos YAML de escenario que listen la secuencia de
elementos a inyectar y los eventos de sabotaje con su instante. Así la sustentación es
repetible y las pruebas automáticas comparan resultados contra lo esperado. Un escenario
por cada filtro que el profesor va a probar por separado, más un escenario mixto largo.

---

## 12. Visión computacional

Pipeline fijo: adquisición, corrección de perspectiva si la cámara no está perfectamente
cenital, conversión a escala de grises, umbralizado adaptativo o separación por saturación,
apertura morfológica, búsqueda de contornos, selección del contorno mayor dentro de la
región de interés de la casilla, cálculo de diámetro equivalente y circularidad, detección
de contornos internos, recorte cuadrado centrado y normalizado a 96 por 96 píxeles, y
finalmente inferencia.

La calibración de escala se hace una sola vez con un patrón de dimensión conocida y se
guarda en un archivo de configuración. Todo diámetro se reporta en milímetros, nunca en
píxeles.

La bandera bimetálica se calcula comparando el tono promedio del disco central contra el
del anillo exterior de la misma moneda. Es un contraste relativo dentro de la propia pieza,
no una comparación contra una tabla de colores absolutos, y por eso sobrevive al desgaste y
a la variación de iluminación.

El clasificador es una red pequeña de transferencia de aprendizaje sobre MobileNet, o un
modelo exportado de Teachable Machine si el tiempo aprieta. **Decidido (grupo, 2026-09-22):
Keras + MobileNetV2**, con **dos fotos por moneda** combinadas por
`control.reglas.combinar_fotos` (si las fotos que reconocen coinciden → esa clase; si
reconocen clases distintas → no_reconocida). Solo se entrenan las familias de
`familias_entrenadas` en `config/monedas.yaml` (hoy nueva y antigua; las muy antiguas e
históricas salen como no_reconocida hasta conseguir las piezas). Clases: las nueve
combinaciones de denominación y familia de la tabla, más la clase `otro` que incluye
monedas extranjeras y botones metálicos. Se entrena con fotos del propio montaje, entre 80
y 150 por clase, incluyendo anverso y reverso y piezas gastadas. Como la cámara, la
distancia y la luz son siempre las mismas, el modelo no necesita ser grande.

El script de entrenamiento debe generar y versionar la matriz de confusión y la curva de
confianza, porque son material directo para el informe.

---

## 13. Dashboard en Streamlit

Debe cumplir el objetivo específico cuatro y servir de panel de depuración durante el
desarrollo. Organización sugerida en pestañas.

**Producción.** Indicadores grandes con cantidad total de monedas, valor acumulado en
pesos, masa estimada acumulada, vasos completados y tasa de rechazo. Gráfico de barras de
cantidad por denominación y gráfico de línea de valor acumulado en el tiempo.

**Línea en vivo.** Representación de la cinta como una fila de casillas con su estado y su
contenido, de modo que se ve el elemento avanzar estación por estación. Estado de cada
sensor como indicador encendido o apagado. Estado de la cinta de vasos con el estado de
cada casilla. Bandera de la cortina de seguridad.

**Inspección.** La última imagen capturada con el contorno detectado superpuesto, el
diámetro medido, la circularidad, la clase predicha y la confianza. Historial de los
últimos veinte elementos con miniatura y veredicto. Esta pestaña es la que demuestra el
elemento 7 durante la sustentación.

**Rechazos.** Conteo por causa, que es la evidencia de que los filtros se complementan y no
se solapan. Si una causa nunca dispara, ese filtro no está aportando y hay que decirlo en
el informe.

**Ruta.** Mapa de la pista con la posición estimada del vehículo, marcas de los tres
obstáculos y de los eventos de evasión, y línea de tiempo del trayecto.

**Control.** Botones de iniciar, pausar, reanudar y paro de emergencia, selector de backend
entre simulación y hardware real, selector de escenario, umbral de confianza ajustable y
velocidad de la línea. Los botones escriben en la tabla de órdenes y el supervisor las
consume.

**Asistente.** El chatbot.

Use `st.fragment` o refresco periódico para la actualización en vivo sin recargar toda la
página. Gráficos con Plotly. Nada de bucles infinitos dentro del script de Streamlit.

---

## 14. Chatbot

Cliente de la API de DeepSeek, compatible con el formato de OpenAI, apuntando a
`https://api.deepseek.com`. La clave va en variable de entorno, nunca en el repositorio.

En cada pregunta se arma un mensaje de sistema que incluye una descripción corta del
proyecto y el estado actual serializado en JSON: totales, conteo por denominación, últimos
eventos, estado de la línea, estado del vehículo y conteo de rechazos por causa. El modelo
responde sobre esos datos.

Entrada de voz con el micrófono de Streamlit y transcripción local o por servicio. Salida
de voz con edge-tts o gTTS. Prevea un respaldo sin internet con Ollama y un modelo pequeño,
porque el día de la sustentación la red del salón puede fallar.

**Hecho (fase 7, 2026-09-27)** en `app/asistente.py`, con la lógica del tema 4 del repositorio
(`4-chatbot-asistente-voz/comando_voz.py`): la frase va a DeepSeek (`deepseek-chat`,
`response_format: json_object`) y vuelve un JSON `{"respuesta", "acciones"}`; las acciones pasan
por una lista blanca con rangos y van a la tabla `ordenes`. "Lee todo el proyecto" por búsqueda:
README, CLAUDE.md, docs/*.md y la configuración se parten en secciones y en cada pregunta se mandan
el README, el estado en vivo y las secciones más parecidas a la pregunta (~24 000 caracteres; los
~300 kB completos serían lentos y caros). Voz: `st.audio_input` → reconocimiento de Google en es-CO
(SpeechRecognition, como el tema 4) y respuesta con gTTS. Respaldo sin internet: en vez de Ollama
(descargar un modelo pesado), un intérprete LOCAL con expresiones regulares entiende las órdenes y
las preguntas básicas y, para lo demás, muestra la sección de la documentación más parecida. Una
pregunta nunca mueve nada. La clave del tema 4 fue rechazada por DeepSeek (401, 2026-09-27): hay
que poner una válida en `.env` (ver `.env.example`).

**Modelo local (2026-09-27):** Ollama + `qwen2.5:3b` en el mismo portátil (fuera del repo), con
el mismo cliente de OpenAI, el mismo prompt, JSON y lista blanca. Orden: DeepSeek → local →
reglas. Al modelo local va un contexto corto (sin README, ~3000 caracteres de docs, sin eventos):
con el contexto por defecto de Ollama (~4000 tokens) un prompt largo se corta por el principio y
pierde las instrucciones. Las órdenes claras las decide el intérprete de reglas (el modelo chico
inventó una secuencia de 4 órdenes para "gira a la derecha"), el signo del giro lo manda la frase
y se acepta UNA sola orden al carro por mensaje, con cualquier proveedor.

**Modelo local, segunda ronda (2026-09-27):** `qwen2.5-proyecto` = qwen2.5:3b con 8192 tokens de
contexto (`python -m app.asistente --preparar-local`; 3,5 de 4 GB en la RTX 3050), ~9000 caracteres
de documentación, el estado en vivo PEGADO a la pregunta (al principio de un texto largo el modelo
chico lo ignoraba) y, si las reglas ya tienen la cifra exacta, va como "DATO VERIFICADO" (confundía
"cuánto pesan" con pesos). Candados para TODOS los proveedores: una pregunta nunca da órdenes; el
modelo local no puede mover el carro si la frase no pide un movimiento; las medidas que ningún
sensor toma (temperatura, voltaje, corriente) las responden las reglas sin inventar. Estado
"pensando" (tabla `asistente_pensando`, en `/api/asistente`): el visor anima la nube si piensa
DeepSeek o la laptop (teclado RGB, luz de actividad, pantalla) si piensa el modelo local.
`python -m app.evaluar_asistente`: 24 casos reales (cifras, técnico, costos, sin dato, órdenes con
errores de ortografía, seguridad, inglés) → 24/24 local (mediana 7,5 s) y 24/24 reglas.

**Sin internet (2026-09-27):** `hay_internet()` (conexión TCP a DeepSeek o Google, recordada 15 s).
Sin red no se intenta DeepSeek (no se espera su timeout). Voz: con internet Google + gTTS; sin
internet **Whisper `small`** (faster-whisper, CPU int8, ~2,5 s por frase; `base` oía "abanza" y
"muye") y la **voz de Windows** (pyttsx3, en un proceso aparte: se cuelga si se llama dos veces en
el mismo proceso). Modelo descargado una vez con `python -m app.asistente --preparar-voz`, fuera del
repo. Avisos: el dashboard pregunta al servidor del supervisor si está vivo (la telemetría se
detiene al terminar la corrida, así que su edad no sirve) y muestra "NO ES EN VIVO", "ESP32
EMULADO" y "SIN INTERNET" en grande; el visor, "DEMO GRABADA" y "SIN CONEXIÓN" (completos 10 s,
luego en una línea), un chip de internet al lado de los ticks y la nube gris. En vivo el visor NO
decide solo si hay internet: pregunta a `/api/internet` del supervisor (el mismo `hay_internet()`);
probar desde el navegador al arrancar (con la escena 3D armándose) daba "sin internet" falso. En
la demo prueba el navegador: DeepSeek o Google, y solo tras 2 fallos seguidos.

El chatbot nunca inventa cifras: si una métrica no está en el estado inyectado, debe decir
que no tiene ese dato.

---

## 15. Firmware y comunicaciones

**ESP32 fijo.** Conectado por USB al PC. Controla los dos motores paso a paso con drivers
A4988 o TMC2208, los servos (incluida la prensa) a través de un PCA9685 por I2C para ahorrar
pines, y lee los sensores discretos. No toma decisiones de clasificación:
ejecuta comandos y reporta eventos. Toda la inteligencia está en el PC. Esto es
deliberado y hay que justificarlo en el informe por la carga de la visión.

**ESP32 del vehículo.** Se comunica con el ESP32 fijo por ESP-NOW. Controla motores,
encoders, arreglo de línea y ultrasónico. Publica odometría y eventos de obstáculo. El
ESP32 fijo actúa de puente hacia el PC por el mismo puerto serial. Con esto se cumple el
requisito de comunicación inalámbrica sin depender del router del salón y sin ocupar el
Wi-Fi del PC, que se necesita para la API del chatbot.

**Estructura del firmware.** Bucle no bloqueante basado en máquina de estados y temporizadores
por milisegundos. Prohibido usar delay en el bucle principal. Los pasos del motor se
generan por temporizador o por librería de aceleración. El parser de comandos es tolerante
a líneas incompletas.

---

## 16. Plan de trabajo por fases

Trabaje una fase a la vez. No empiece una fase sin que la anterior pase sus criterios de
aceptación. Al cerrar cada fase, actualice `docs/bitacora.md` con lo hecho y lo pendiente.

**Fase 0. Andamiaje.** Estructura de carpetas, requirements, configuración, esquema de
SQLite, módulo de monedas con la tabla, y pruebas vacías que corren. Criterio: el
repositorio clona, instala e importa sin errores.

**Fase 1. Control puro.** Registro de casillas, máquinas de estado de línea y embalaje,
reglas de decisión, todo contra un backend falso en memoria. Criterio: pruebas unitarias
que alimentan secuencias de elementos ficticios y verifican que cada uno termina en el
destino correcto, incluyendo los casos de sabotaje de vaso. Sin PyBullet todavía.

**Fase 2. Mundo simulado.** URDF de la estación, escena en PyBullet, movimiento indexado de
las dos cintas, inyección de elementos, servos de expulsión (con el filtro total del 2026-09-25
quedó una sola compuerta de desvío en E4). Criterio: en modo GUI se ve un
elemento recorrer la cinta y ser expulsado por el servo correcto según un veredicto
inyectado a mano.

**Fase 3. Sensores simulados y backend sim.** Emulación de todos los sensores, backend sim
de la HAL, y conexión de la capa de control. Criterio: la línea corre sola en simulación
con un escenario de veinte elementos mixtos y el resultado coincide con lo esperado por el
escenario.

**Fase 4. Persistencia y dashboard.** Supervisor escribiendo eventos, SQLite, dashboard con
las pestañas de producción, línea en vivo y rechazos. Criterio: se abre Streamlit mientras
la simulación corre y las métricas se mueven en vivo.

**Fase 5. Visión.** Render cenital, pipeline de segmentación y métricas geométricas,
clasificador en modo oráculo primero y luego modelo real, pestaña de inspección. Criterio:
el veredicto de visión reemplaza al oráculo sin cambiar nada de la capa de control.

**Fase 6. Vehículo y ruta.** Pista con línea y tres obstáculos, dinámica del carro,
seguimiento de línea, maniobra de evasión, acople con la canaleta, pestaña de ruta.
Criterio: un vaso se entrega, el carro recorre la pista esquivando los tres obstáculos y
llega a la meta, y todo queda registrado.

**Fase 7. Chatbot.** Cliente de DeepSeek, inyección de estado, voz. Criterio: responde
correctamente preguntas sobre cifras reales del proceso en curso. **Hecha el 2026-09-27** (con
órdenes al carro y a la línea, a pedido del usuario; punto 16 del paso a paso, EN PAUSA hasta el
montaje real). Modelo local (Ollama) y voz sin internet hechos; falta probar una clave de DeepSeek válida.

**Fase 8. Backend real.** Firmware de los dos ESP32, protocolo serial, backend real de la
HAL. Criterio: el mismo código de control que corría en simulación mueve el hardware
cambiando una sola línea de configuración. **Hecha en software el 2026-09-27**
(`hardware.backend: real`; ver `firmware/README.md`): firmware MicroPython, puente serial,
`control/hal/backend_real.py`, supervisor en modo real y 17 pruebas con una estación emulada.
Falta: probar en las placas, medir los valores PROVISIONALES de `firmware:`, y la línea
automática con hardware espera la visión real (fase 5).

**Fase 9. Documentación.** README con el paso a paso, diagramas de bloques, requerimientos,
materiales justificados, esquemas, planos y resultados del clasificador.

---

## 17. Reglas para el agente

Trabaje siempre sobre la fase actual. Si encuentra trabajo pendiente de una fase anterior,
termínelo antes de avanzar.

No importe PyBullet, pyserial ni OpenCV desde `control/`. Si necesita hardware o percepción
desde ahí, es señal de que falta un método en la HAL.

No invente valores de hardware. Si falta un dato físico, como la altura del vaso o el
diámetro del rodillo, escríbalo en `config/parametros.yaml` con un valor provisional
claramente marcado y menciónelo al usuario en vez de enterrarlo en el código.

Todo número mágico va a configuración: umbrales de confianza, rangos de diámetro,
tolerancia de coherencia, duración de pausas, velocidades.

Escriba pruebas para la capa de control y para las reglas de decisión. La simulación no
sustituye a las pruebas: es lenta y visual, las pruebas son rápidas y verificables.

Comentarios y documentación en español. Nombres de variables y funciones en español
también, para que el código sea legible en la sustentación.

Commits pequeños y descriptivos, uno por unidad de trabajo, con el número de fase al
inicio del mensaje.

No agregue dependencias pesadas sin justificarlas. El proyecto debe correr en un portátil
de estudiante sin GPU.

Cuando una decisión de diseño tenga alternativas reales, expóngalas con sus ventajas y
desventajas antes de implementar, en lugar de elegir en silencio.

---

## 18. Herramientas recomendadas

**CAD.** Onshape es la mejor opción para este caso: corre en el navegador, es gratuito para
uso educativo, guarda versiones automáticamente y varios integrantes pueden trabajar sobre
el mismo documento. Alternativas: Fusion 360 con licencia educativa si ya la tienen, o
FreeCAD si prefieren algo local y libre. Exporte cada pieza a STL para las mallas visuales.

**Del CAD al URDF.** No exporte la malla de alta resolución como geometría de colisión. Use
mallas detalladas solo para lo visual y primitivas simples, cajas y cilindros, para
colisión. Las monedas deben ser cilindros de colisión puros. Para simplificar mallas
pesadas, el modificador de decimación de Blender resuelve en un minuto. Si quiere
automatizar la exportación, el exportador de URDF de Onshape, onshape-to-robot, genera el
árbol de eslabones y juntas directamente desde el ensamblaje.

**Motor de física y visualizador.** PyBullet es lo exigido y es suficiente. Su GUI integrada
sirve para demostración y permite grabar video. Para las pruebas automáticas use modo
DIRECT. Si en algún momento quiere una vista más presentable para el video de sustentación,
MeshCat renderiza en navegador y se conecta bien con Python, pero no invierta tiempo ahí
hasta tener las fases 1 a 5 cerradas.

**Interfaz.** Streamlit para el dashboard oficial, que es lo que pide el enunciado. Plotly
para las gráficas. Para depuración rápida durante el desarrollo, imprimir el estado de la
línea en consola con `rich` es más ágil que abrir el navegador.

**Entrenamiento del clasificador.** Teachable Machine si necesita resultados en un día,
Keras con MobileNetV2 si quiere control y material más serio para el informe. Roboflow
sirve para etiquetar y aumentar el dataset si consiguen suficientes fotos.

**Firmware.** Decidido (2026-09-27): **MicroPython** (el del curso, con Thonny) y no
PlatformIO: así `control/protocolo.py` y `control/vehiculo.py` corren tal cual en las placas
(compilados con `mpy-cross`), sin reescribir el control en C++. Se sube con `mpremote`
(`python -m firmware.subir`).

---

## 19. Dependencias base

```
pybullet
numpy
opencv-python
streamlit
plotly
pandas
pyserial
pyyaml
requests
openai
```

Añada `tensorflow` o `onnxruntime` solo en la fase 5, según cómo se entrene el modelo.
