# Logica del ESP32 FIJO (fase 8). MicroPython en la placa; CPython en las
# pruebas del PC (tests/firmware/test_firmware.py) con un hardware falso.
#
# Este archivo NO toca pines: recibe un objeto `hw` (firmware/fijo/hw.py en la
# placa) que sabe mover motores y leer sensores. Aqui solo vive la decision:
#
#   - Comandos del PC por USB serial, una linea JSON por comando, numerados:
#     cada uno se confirma con su ack; si llega repetido (el ack se perdio y el
#     PC lo reenvio) se vuelve a confirmar pero NO se ejecuta dos veces.
#   - Eventos y telemetria hacia el PC con numero de secuencia `n` (el PC ve
#     si se perdio alguno).
#   - Latido: si el PC deja de hablar `pc_sin_latido_ms`, PARADA SEGURA
#     (cintas quietas, prensa arriba, desvio al rechazo, escapes cerrados,
#     carrusel frenado). La parada guarda su MOTIVO (ver MOTIVOS_PARADA):
#     solo la de "sin_pc" se levanta sola al volver el latido; el paro del
#     dashboard queda ENCLAVADO hasta `estado.reanudar` (Iniciar/Reanudar).
#   - Cortina de seguridad: la reaccion es LOCAL (no espera al PC, que puede
#     estar colgado): prensa arriba y cinta de vasos quieta. Vota como las
#     demas estaciones (N lecturas NUEVAS seguidas para activarla y N para
#     despejarla) y falla del lado SEGURO: sin mediciones nuevas del VL53L0X
#     (cable I2C flojo, sensor muerto) la cortina queda ACTIVA.
#   - Canaleta: el escape suelta un vaso solo si el carro esta en el muelle
#     con la cuna vacia (`protocolo.puede_soltar_vaso`, CLAUDE.md 10.1).
#   - Prensa y empujador NUNCA se mueven a la vez, y eso lo asegura la PLACA,
#     no solo el orden de comandos del PC (ver EXCLUYENTES).
#   - Carrusel y obturador tampoco se estorban (2026-09-29): el obturador no
#     abre con el disco girando (el lote caeria entre dos tubos) y el disco no
#     gira con el obturador abierto. Mismo patron que EXCLUYENTES: el segundo
#     ESPERA su turno (ver BLOQUEOS).
#   - Puente con el carro: lo que llega del PC con dst "carro" sale por
#     ESP-NOW y se REINTENTA hasta que el carro contesta `respuesta_orden` (o
#     se avisa `carro_sin_respuesta`); lo que manda el carro se reenvia al PC.
#
# Contrato completo de los mensajes: CLAUDE.md, seccion 10.1.

try:
    import protocolo                      # en el ESP32: protocolo.mpy en la raiz
except ImportError:                       # en el PC (pruebas)
    from control import protocolo

# Que hace cada comando: destino -> accion -> metodo de esta clase.
COMANDOS = {
    "linea": {"avanzar": "_avanzar_monedas"},
    "vasos": {"avanzar": "_avanzar_vasos", "tapar": "_tapar", "prensar": "_prensar", "empujar": "_empujar"},
    "desvio": {"almacen": "_desvio_almacen", "rechazo": "_desvio_rechazo"},
    "carrusel": {"ir": "_carrusel_ir", "referencia": "_carrusel_referencia", "abrir": "_obturador"},
    "canaleta": {"soltar": "_soltar_vaso"},
    "estado": {"leer": "_leer_estado", "parar": "_parar", "reanudar": "_reanudar"},
}

# Duracion de los movimientos de servos que son un ciclo (ida y vuelta), ms.
CICLOS_SERVO = {"prensa": "prensa_ciclo", "empujador": "empujador", "tapas": "tapa_caida",
                "obturador": "compuerta_tubo", "canaleta": "empujador"}

# Servos que no se pueden mover a la vez: los dos MG996R del riel de 6 V.
# Por que: la prensa apretando la tapa ya lleva el riel a ~3,9 A; con el
# empujador arrancando (o trabado) al mismo tiempo el peor caso queda JUSTO
# bajo los 8 A del XL4016 y el fusible F1 (docs/electrica.md). Ademas son la
# misma casilla de la cinta de vasos: el plato de la prensa abajo y la paleta
# empujando el vaso de lado se estorbarian. El PC ya los manda en orden, pero
# un reintento, un boton de prueba del dashboard o un PC colgado pueden
# romper ese orden: por eso la regla vive aqui.
# Que hace la placa si llega uno mientras el otro se mueve: lo ENCOLA (ack
# ok:true + evento "en_espera") y lo arranca apenas el otro vuelve a reposo.
# Se eligio esperar y no rechazar porque el PC ya dio la orden por buena con
# su ack y no la reintenta: rechazarla dejaria una tapa sin prensar o un vaso
# sin descargar. Si mientras espera salta la cortina o la parada segura, la
# orden se cancela (evento "cancelado"): con una mano adentro no se mueve nada.
EXCLUYENTES = {"prensa": "empujador", "empujador": "prensa"}

# Lo que espera su turno por algo que NO es un servo del riel de 6 V
# (2026-09-29, revision logica): el obturador del almacen no abre mientras el
# carrusel gira (el lote de monedas caeria entre dos tubos o fuera del
# agujero) y el carrusel no gira con el obturador abierto (el borde de la
# placa cizallaria las monedas que estan cayendo). El PC ya espera `llego`
# antes de abrir, pero un boton de prueba o un reintento pueden romper ese
# orden: igual que EXCLUYENTES, la regla vive en la placa y el segundo ESPERA
# (ack ok:true + evento `en_espera`), no se rechaza.
#   "obturador" espera a "carrusel" (el disco girando)
#   "carrusel"  espera a "obturador" (en su ciclo: abierto o cerrando)
#   "carrusel"  espera a "moneda" (revision visual 2026-09-29): una moneda
#               aceptada cae cuando la cinta de monedas termina su avance con
#               el desvio hacia el almacen, y tarda `tiempos.caida_moneda_tubo`
#               en llegar al fondo de su tubo. Mientras cae el disco no gira
#               (si giraba, la moneda caia fuera de la boca). La placa lo sabe
#               sola: desvio en "almacen" + avance de la cinta.
BLOQUEOS = {"obturador": "carrusel", "carrusel": "obturador"}

# Servos que la cortina congela (y cuya espera cancela): los de la zona de
# tapa y prensa. El obturador y el carrusel estan en el almacen, lejos de la
# mano: una espera suya no se cancela por la cortina.
ZONA_CORTINA = ("prensa", "tapas", "empujador")

# Por que se para la estacion. El motivo decide COMO se sale de la parada:
#   "sin_pc": no se oye el latido del PC (o recien encendida). Se levanta SOLA
#             cuando el latido vuelve: el PC no pidio parar, solo se callo.
#   "paro":   el PC mando `estado.parar` (paro de emergencia o pausa del
#             dashboard). Queda ENCLAVADO: un latido que vuelve NO la levanta
#             (antes si: un paro con el cable USB flojo se borraba solo al
#             reconectar). Sale solo con `estado.reanudar`, que el PC manda
#             con Iniciar o con Reanudar (app/supervisor.py).
#   "pausa":  el PC pauso la linea (boton Pausar, o porque dejo de oir a la
#             placa: `sin_esp32`). Enclavada como el paro (2026-09-29): antes la
#             pausa por `sin_esp32` no le decia nada a la placa, y al volver el
#             cable la placa se levantaba sola mientras el PC decia PAUSADA.
#             Sale con `estado.reanudar` (Reanudar).
#   "error":  una excepcion en el bucle de main.py. Tambien enclavada: si el
#             firmware fallo, alguien tiene que mirarlo antes de seguir.
# Un motivo enclavado no se rebaja: si hay paro y ademas se pierde el PC, al
# volver el PC sigue el paro. Entre enclavados gana el mas grave (PRIORIDAD):
# un paro sobre una pausa queda como paro; un error, como error.
MOTIVOS_ENCLAVADOS = ("pausa", "paro", "error")
PRIORIDAD_MOTIVO = {"sin_pc": 0, "pausa": 1, "paro": 2, "error": 3}


class Estacion:
    def __init__(self, hw, cfg, enviar_pc, enviar_carro):
        """cfg: diccionario de config_placa.py (sale de config/parametros.yaml).
        enviar_pc / enviar_carro: funciones que reciben una linea de texto."""
        self.hw = hw
        self.cfg = cfg
        self.enviar_pc = enviar_pc
        self.enviar_carro = enviar_carro
        p = cfg["protocolo"]
        self.receptor = protocolo.Receptor()
        self.latido_pc = protocolo.Latido(p["pc_latido_ms"], p["pc_sin_latido_ms"])
        self.latido_carro = protocolo.Latido(p["carro_latido_ms"], p["carro_enlace_perdido_ms"])
        self.receptor_carro = protocolo.Receptor()   # eventos del carro: ack + sin repetidos
        self.n = 0                        # numero de secuencia de lo que se manda al PC
        # Latidos del PC recibidos desde que arranco la placa. main.py arma el
        # perro guardian recien con el primero (ver main.py: mpremote nunca
        # manda un latido, asi que subir el firmware no reinicia la placa).
        self.pc_latidos = 0
        # Ordenes al carro que todavia no contestaron (revision 2026-09-29):
        # id -> [linea, act, t_envio, intentos, en_muelle_antes, version_carro].
        # Se reenvian cada `carro_reintento_ms` hasta la `respuesta_orden` del
        # carro, como mucho `carro_orden_intentos` veces.
        self._ordenes_carro = {}
        self._orden_reintento_ms = p["carro_reintento_ms"]
        self._orden_intentos = p.get("carro_orden_intentos", 4)
        # Cuantas veces cambio lo que se sabe del muelle por un evento del carro
        # (para no pisar un estado mas nuevo al deshacer una orden rechazada).
        self._version_carro = 0
        # Sesion de esta placa (va en su latido): si se reinicia, el PC sabe
        # que `n` vuelve a empezar y no cuenta mensajes perdidos falsos.
        self.sesion = protocolo.nueva_sesion()
        self.parada_segura = False
        self.motivo_parada = None         # "sin_pc", "paro" o "error" (ver MOTIVOS_ENCLAVADOS)
        self.cortina_activa = False
        self.cortina_motivo = None        # "mano" o "sin_lectura" mientras esta activa
        # Votacion de la cortina: cuantas lecturas NUEVAS seguidas contradicen
        # el estado actual. Hacen falta `lecturas_por_decision` para cambiarlo.
        self._cortina_racha = 0
        self._cortina_medidas = None      # contador de mediciones del VL53L0X visto la ultima vez
        self._t_cortina = None            # t_ms de la ultima medicion NUEVA de la cortina
        # Lo ultimo que dijo el carro (para `protocolo.puede_soltar_vaso`).
        # "fresco" = recibido despues de la ultima reconexion de la radio.
        self.estado_carro = {"fresco": False, "en_muelle": False, "cuna": None}
        self.lecturas = {}
        self._ultimas = {}                # ultima lectura publicada de cada sensor discreto
        self._ciclos = []                 # [nombre_servo, t_vuelta] de servos en su ciclo
        self._ocupado = {}                # servo -> t_ms en que termina de VOLVER a reposo
        self._en_espera = []              # [servo, t_pedido]: esperan a que su excluyente vuelva
        self._carrusel_pedido = None      # [tubo, lugar, t_pedido] hasta que el motor para
        self._desvio_al_almacen = False   # el desvio apunta al almacen (una moneda aceptada)
        self._moneda_cae_hasta = -1       # t_ms en que la ultima moneda llega al fondo de su tubo
        self._prox_tel = 0
        self.errores = 0                  # lineas rotas o comandos desconocidos
        # Arranca parada, como si no oyera al PC: sale sola con su primer latido.
        self.aplicar_parada_segura("sin_pc", inicial=True)

    # ------------------------------------------------------------------
    # salida hacia el PC
    # ------------------------------------------------------------------

    def _mandar(self, mensaje):
        self.n += 1
        mensaje["n"] = self.n
        self.enviar_pc(protocolo.linea(mensaje))

    def evento(self, src, ev, t_ms, datos=None):
        m = {"t": "evt", "ms": t_ms, "src": src, "ev": ev}
        if datos:
            m.update(datos)
        self._mandar(m)

    # ------------------------------------------------------------------
    # entrada: una linea del PC o un mensaje del carro
    # ------------------------------------------------------------------

    def linea_del_pc(self, texto, t_ms):
        m = protocolo.parsear_linea(texto)
        if m is None:
            self.errores += 1             # linea cortada o con basura: se cuenta y se sigue
            return
        self.latido_pc.oido(t_ms)
        if m["t"] == "hb":
            self.pc_latidos += 1
            self.receptor.ver_sesion(m.get("s"))   # PC reiniciado: sus ids vuelven a 1
            return
        if m["t"] != "cmd" or "id" not in m:
            self.errores += 1
            return
        nuevo, ack = self.receptor.recibir(m)
        if not nuevo:
            self.enviar_pc(protocolo.linea(ack))   # repetido: solo el ack
            return
        # Si el comando lanza una excepcion a mitad (OSError del PCA9685 por un
        # cable I2C flojo), antes NO salia ack y el id ya quedaba marcado como
        # visto: el PC lo reenviaba y recibia "ok:true" sin que se hubiera
        # ejecutado. Ahora: ack ok:false con el error, el id se des-marca (un
        # reenvio se vuelve a intentar) y la excepcion SIGUE hacia main.py, que
        # hace la parada segura con motivo "error".
        try:
            if m.get("dst") == "carro":
                self._orden_al_carro(m, t_ms)
                self.enviar_pc(protocolo.linea(ack))
                return
            error = self._ejecutar(m, t_ms)
        except Exception as e:
            self.receptor.olvidar(m["id"])
            ack["ok"] = False
            ack["error"] = "excepcion: " + str(e)[:60]
            self.enviar_pc(protocolo.linea(ack))
            raise
        if error:
            # Rechazado = NO ejecutado: tambien se des-marca. Si este ack ok:false
            # se pierde, el reenvio del PC se vuelve a evaluar (y da el mismo
            # rechazo o, si la causa ya paso, se ejecuta) en vez de recibir el
            # "ok:true" de un repetido sin que nada se haya hecho.
            self.receptor.olvidar(m["id"])
            ack["ok"] = False
            ack["error"] = error
        self.enviar_pc(protocolo.linea(ack))

    def _orden_al_carro(self, m, t_ms):
        """Puente: la orden sigue al carro por ESP-NOW. El ack al PC dice que
        SALIO; si el carro la acepta o no lo dice su `respuesta_orden`.

        - Se reintenta (en tick) hasta esa respuesta: antes salia UNA vez y, si
          se perdia el paquete, la orden desaparecia sin aviso (el reenvio del
          PC se descartaba como repetido, porque aca ya estaba confirmada). El
          carro descarta los repetidos por id: reintentar no la ejecuta dos veces.
        - Muelle: la estacion deja de soltarle vasos apenas manda la orden (del
          lado seguro: entre la orden y la respuesta el carro puede estar
          arrancando). Si el carro la RECHAZA, sigue quieto en el muelle y nunca
          vuelve a decir `en_muelle`: por eso al llegar el rechazo se deshace
          (ver _respuesta_del_carro). Antes no se deshacia y todos los
          `canaleta.soltar` siguientes daban `vaso retenido: no_esta_en_muelle`.
          Queda igual que sim/planta.py (orden_carro): el muelle solo se da por
          dejado si la orden se ACEPTO."""
        linea = protocolo.linea(m)
        self.enviar_carro(linea)
        ec = self.estado_carro
        self._ordenes_carro[m["id"]] = [linea, m.get("act"), t_ms, 1, ec["en_muelle"], self._version_carro]
        if m.get("act") != "detener":
            ec["en_muelle"] = False

    def mensaje_del_carro(self, texto, t_ms=0):
        """Lo que llega por ESP-NOW. Cada evento del carro se confirma aqui
        mismo (ack con dst carro: el carro lo borra de su cola) y se reenvia
        al PC UNA vez (los repetidos, por un ack perdido, se descartan)."""
        m = protocolo.parsear_linea(texto)
        if m is None or m.get("src") != "carro":
            return
        self.latido_carro.oido(t_ms)
        if m["t"] == "evt" and "id" in m:
            nuevo, ack = self.receptor_carro.recibir(m)
            ack["dst"] = "carro"
            self.enviar_carro(protocolo.linea(ack))
            if nuevo:
                self.enviar_pc(protocolo.linea(m))
                self._estado_del_carro(m)

    def _estado_del_carro(self, m):
        """Guarda lo que el carro dice de si mismo (las mismas reglas que
        sim/planta.py, _mensaje_del_carro). Cada evento del carro trae la
        lectura del infrarrojo de su cuna (`cuna`)."""
        ev = m.get("ev")
        ec = self.estado_carro
        if ev in ("en_muelle", "estado"):
            ec["fresco"] = True
            ec["cuna"] = m.get("cuna")
            ec["en_muelle"] = ev == "en_muelle" or m.get("estado") == "esperando_carga"
            self._version_carro += 1
        elif ev == "salida":
            ec["en_muelle"] = False
            ec["cuna"] = m.get("cuna")
            self._version_carro += 1
        elif ev == "vaso_retirado":
            ec["cuna"] = False
        elif ev == "respuesta_orden":
            self._respuesta_del_carro(m)

    def _respuesta_del_carro(self, m):
        """El carro contesto una orden: se deja de reintentar. Si la rechazo
        (`ok: false`: camino bloqueado, fuera de rango, etc.) no se movio, asi que
        el muelle vuelve a lo que era antes de la orden, salvo que el carro haya
        dicho algo mas nuevo de si mismo entre medio (entonces vale eso)."""
        o = self._ordenes_carro.pop(m.get("orden"), None)
        if o is None:
            return                        # respuesta a una orden ya abandonada (o repetida)
        if not m.get("ok") and o[5] == self._version_carro:
            self.estado_carro["en_muelle"] = o[4]

    def _ejecutar(self, m, t_ms):
        acciones = COMANDOS.get(m.get("dst"), {})
        metodo = acciones.get(m.get("act"))
        if metodo is None:
            self.errores += 1
            return "comando desconocido"
        if self.parada_segura and m.get("dst") != "estado":
            if self.motivo_parada == "paro":
                return "parada segura por paro: sale con reanudar (Iniciar)"
            if self.motivo_parada == "pausa":
                return "parada segura por pausa del PC: sale con reanudar"
            if self.motivo_parada == "error":
                return "parada segura por un error del firmware: sale con reanudar"
            return "parada segura: falta el latido del PC"
        return getattr(self, metodo)(m, t_ms)

    # ------------------------------------------------------------------
    # comandos
    # ------------------------------------------------------------------

    def _avanzar_monedas(self, m, t_ms):
        if self.hw.cinta_moviendose("monedas"):
            return "la cinta de monedas todavia se mueve"
        t = self.cfg["tiempos"]
        self.hw.avanzar_cinta("monedas", self.cfg["cinta_monedas_mm"], t["avance_casilla_monedas"])
        if self._desvio_al_almacen:
            # La moneda de la descarga cae al terminar este avance y baja por
            # el canal hasta el fondo de su tubo: el carrusel queda ocupado.
            self._moneda_cae_hasta = t_ms + t["avance_casilla_monedas"] + t.get("caida_moneda_tubo", 0)
        self.evento("linea", "paso", t_ms)

    def _avanzar_vasos(self, m, t_ms):
        if self.cortina_activa:
            return "cortina activa: la cinta de vasos no avanza"
        if self.hw.cinta_moviendose("vasos"):
            return "la cinta de vasos todavia se mueve"
        self.hw.avanzar_cinta("vasos", self.cfg["cinta_vasos_mm"], self.cfg["tiempos"]["avance_casilla_vasos"])
        self.evento("vasos", "paso", t_ms)

    def _ciclo(self, servo, t_ms):
        """Servo a su posicion activa y, pasado su tiempo, de vuelta al reposo."""
        if self.cortina_activa and servo in ZONA_CORTINA:
            return "cortina activa: tapa, prensa y empujador congelados"
        if any(c[0] == servo for c in self._ciclos):
            return servo + " todavia esta en su ciclo"
        if any(e[0] == servo for e in self._en_espera):
            return servo + " ya esta esperando su turno"
        otro = self._bloqueado_por(servo, t_ms)
        if otro is not None:
            # El otro MG996R esta en su ciclo (ida O vuelta), o el carrusel
            # gira bajo el obturador: este espera.
            self._en_espera.append([servo, t_ms])
            self.evento("servo", servo, t_ms, {"ciclo": "en_espera", "espera_a": otro})
            return None
        self._arrancar(servo, t_ms)

    def _bloqueado_por(self, nombre, t_ms):
        """Que impide mover `nombre` ahora (EXCLUYENTES o BLOQUEOS), o None."""
        otro = EXCLUYENTES.get(nombre)
        if otro is not None and self._moviendose(otro, t_ms):
            return otro
        otro = BLOQUEOS.get(nombre)
        if otro == "carrusel" and self.hw.carrusel_moviendose():
            return otro
        if otro == "obturador" and self._moviendose("obturador", t_ms):
            return otro
        if nombre == "carrusel" and t_ms < self._moneda_cae_hasta:
            return "moneda"               # una moneda todavia cae a su tubo
        return None

    def _moviendose(self, servo, t_ms):
        """True mientras el servo no termino de volver a reposo (el ciclo
        completo, no solo la ida: de vuelta tambien consume y tambien ocupa
        la casilla)."""
        return t_ms < self._ocupado.get(servo, -1)

    def _arrancar(self, servo, t_ms):
        self.hw.servo(servo, self.cfg["servos"][servo]["activo"])
        ciclo = self.cfg["tiempos"][CICLOS_SERVO[servo]]
        self._ciclos.append([servo, t_ms + ciclo // 2])
        self._ocupado[servo] = t_ms + ciclo

    def _cancelar_espera(self, t_ms, motivo, solo=None):
        """Cancela lo que esperaba turno (todo, o solo los de `solo`)."""
        quedan = []
        for e in self._en_espera:
            if solo is not None and e[0] not in solo:
                quedan.append(e)
            else:
                self.evento("servo", e[0], t_ms, {"ciclo": "cancelado", "motivo": motivo})
        self._en_espera = quedan

    def _tapar(self, m, t_ms):
        return self._ciclo("tapas", t_ms)

    def _prensar(self, m, t_ms):
        return self._ciclo("prensa", t_ms)

    def _empujar(self, m, t_ms):
        return self._ciclo("empujador", t_ms)

    def _obturador(self, m, t_ms):
        return self._ciclo("obturador", t_ms)

    def _soltar_vaso(self, m, t_ms):
        # Regla de la estacion (CLAUDE.md 10.1, protocolo.puede_soltar_vaso):
        # la decide la PLACA con lo ultimo que oyo del carro, no el PC (que en
        # modo real no lo revisaba: soltaba el vaso al piso si el carro no
        # estaba). Enlace vivo + estado fresco + carro en el muelle + cuna vacia.
        ok, motivo = protocolo.puede_soltar_vaso(self.estado_carro, self.latido_carro.vivo(t_ms))
        if not ok:
            if motivo == "cuna_ocupada":
                self.evento("operador", "alarma", t_ms, {"tipo": "cuna_ocupada"})
            return "vaso retenido: " + motivo
        error = self._ciclo("canaleta", t_ms)
        if error is None:
            # Hasta que el carro diga que lo tiene (o que sigue vacia) la cuna
            # es desconocida: no se suelta un segundo vaso encima del primero.
            self.estado_carro["cuna"] = None
        return error

    def _desvio_almacen(self, m, t_ms):
        self.hw.servo("desvio", self.cfg["servos"]["desvio"]["activo"])
        self._desvio_al_almacen = True

    def _desvio_rechazo(self, m, t_ms):
        self.hw.servo("desvio", self.cfg["servos"]["desvio"]["reposo"])
        self._desvio_al_almacen = False

    def _carrusel_ir(self, m, t_ms):
        # {"dst":"carrusel","act":"ir","tubo":k,"lugar":"carga"|"agujero"}: deja el
        # tubo k bajo la carga (donde cae la moneda de la cinta) o sobre el agujero
        # (donde se abre el obturador). El giro tarda lo que tarda (media vuelta
        # 4,1 s): cuando el motor para se avisa `carrusel/llego` (ver tick). El PC
        # NO suelta la moneda ni abre el obturador antes de ese aviso (2026-09-28).
        tubo = m.get("tubo")
        lugar = m.get("lugar", "carga")
        if not isinstance(tubo, int) or not 0 <= tubo < 6:
            return "tubo invalido (0 a 5)"
        if lugar not in ("carga", "agujero"):
            return "lugar invalido (carga o agujero)"
        # `llego` lleva el id de ESTE comando (`pedido`): el backend del PC lo
        # compara y no confunde el aviso de un giro viejo con el suyo.
        pedido = m.get("id")
        otro = self._bloqueado_por("carrusel", t_ms)
        if otro is not None:
            # Obturador abierto (o cerrando) o una moneda cayendo a su tubo: el
            # disco espera. Un pedido nuevo reemplaza al que esperaba (manda el
            # ultimo, como con el motor).
            self._en_espera = [e for e in self._en_espera if e[0] != "carrusel"]
            self._en_espera.append(["carrusel", t_ms, tubo, lugar, pedido])
            self.evento("carrusel", "en_espera", t_ms, {"tubo": tubo, "lugar": lugar, "espera_a": otro,
                                                        "pedido": pedido})
            return None
        self._girar_carrusel(tubo, lugar, t_ms, pedido)

    def _girar_carrusel(self, tubo, lugar, t_ms, pedido):
        self.hw.carrusel_a(tubo, lugar)
        self._carrusel_pedido = [tubo, lugar, t_ms, pedido]

    def _carrusel_referencia(self, m, t_ms):
        # Gira hasta que el Hall ve el iman: ahi es el tubo 0. Con el obturador
        # abierto no (mismo motivo que BLOQUEOS); se pide de nuevo despues.
        if self._bloqueado_por("carrusel", t_ms) is not None:
            return "obturador abierto: el carrusel no gira"
        self.hw.carrusel_buscar_referencia()

    def _leer_estado(self, m, t_ms):
        self._telemetria(t_ms)

    def _parar(self, m, t_ms):
        # Paro de emergencia o pausa del PC: parada segura ENCLAVADA. El PC dice
        # cual con `motivo` ("pausa"); sin el campo es un paro.
        motivo = "pausa" if m.get("motivo") == "pausa" else "paro"
        self.aplicar_parada_segura(motivo, t_ms)
        self.evento("esp32", "parada_segura", t_ms, {"motivo": self.motivo_parada})

    def _reanudar(self, m, t_ms):
        # Unica salida de un paro o de un error (Iniciar/Reanudar del PC). Con
        # el PC mudo no: la parada por "sin_pc" seguiria de todos modos.
        if not self.latido_pc.vivo(t_ms):
            return "sin latido del PC"
        motivo = self.motivo_parada
        self.parada_segura = False
        self.motivo_parada = None
        self.evento("esp32", "reanudado", t_ms, {"motivo_parada": motivo})

    # ------------------------------------------------------------------
    # seguridad
    # ------------------------------------------------------------------

    def aplicar_parada_segura(self, motivo="sin_pc", t_ms=None, inicial=False):
        """protocolo.accion_sin_pc(): todo a su posicion segura. `motivo`:
        ver MOTIVOS_ENCLAVADOS (un motivo enclavado no se rebaja a sin_pc)."""
        self.hw.detener_cintas()
        for nombre, s in self.cfg["servos"].items():
            self.hw.servo(nombre, s["reposo"])
        self._ciclos = []
        self._en_espera = []              # lo que esperaba turno no se ejecuta despues de una parada
        self._frenar_carrusel(t_ms, motivo)
        if (not self.parada_segura or self.motivo_parada not in MOTIVOS_ENCLAVADOS
                or PRIORIDAD_MOTIVO.get(motivo, 0) >= PRIORIDAD_MOTIVO.get(self.motivo_parada, 0)):
            self.motivo_parada = motivo
        self.parada_segura = True
        self.inicial = inicial

    def _frenar_carrusel(self, t_ms, motivo):
        """El carrusel lo gira un Timer (fijo/hw.py) que sigue solo aunque el
        bucle se detenga: hay que decirle que su objetivo es donde esta ahora.
        Sin esto, en una parada segura el revolver seguia girando hasta 4 s
        con una mano cerca del obturador. El pedido en curso se da por
        perdido (no habra `llego`): el PC lo pide otra vez al reanudar."""
        frenar = getattr(self.hw, "carrusel_detener", None)
        if frenar is None:                # hardware emulado viejo, sin carrusel real
            return
        girando = self.hw.carrusel_moviendose()
        frenar()
        c = self._carrusel_pedido
        self._carrusel_pedido = None
        if girando and t_ms is not None:
            datos = {"motivo": motivo}
            if c is not None:
                datos["tubo"] = c[0]
                datos["lugar"] = c[1]
            self.evento("carrusel", "detenido", t_ms, datos)

    def _revisar_cortina(self, t_ms):
        """Cortina de seguridad (paso 14), decidida en la placa.

        1. Frescura: el VL53L0X da una medicion cada ~33 ms y `hw.leer()` trae
           su contador (`cortina_medidas`). Si pasan mas de
           `cortina_sin_lectura_ms` sin una medicion nueva (OSError por un
           cable I2C flojo, sensor colgado), la ultima distancia es VIEJA: casi
           siempre None = "libre", o sea que la cortina fallaba del lado
           inseguro. Ahora eso cuenta como cortina ACTIVA (+ evento
           `cortina_sin_lectura`). El hardware emulado del PC no trae el
           contador: ahi cada vuelta es una lectura nueva.
        2. Votacion: hace falta `lecturas_por_decision` lecturas NUEVAS
           seguidas que digan lo contrario del estado actual para cambiarlo
           (activar Y despejar: si no, parpadea). Una sola lectura con ruido
           (falso positivo 0,2 %, ~1 cada 17 s a 30 Hz) ya no para la cinta.
           Es lo que presupuesta control/tiempos.py: N x cortina_lectura."""
        d = self.lecturas.get("cortina_mm")
        medidas = self.lecturas.get("cortina_medidas")
        if medidas is None:
            nueva = True
        elif self._cortina_medidas is None:
            nueva = False                 # primera vuelta: solo se toma la referencia
            self._cortina_medidas = medidas
        else:
            nueva = medidas != self._cortina_medidas
            self._cortina_medidas = medidas
        if nueva or self._t_cortina is None:
            self._t_cortina = t_ms
        elif t_ms - self._t_cortina > self.cfg["cortina_sin_lectura_ms"]:
            self._cortina_racha = 0
            if self.cortina_motivo != "sin_lectura":
                self.evento("cortina", "cortina_sin_lectura", t_ms, {"sin_medir_ms": t_ms - self._t_cortina})
                self._cambiar_cortina(True, t_ms, d, "sin_lectura")
            return
        if not nueva:
            return
        mano = d is not None and d < self.cfg["cortina_umbral_mm"]
        if mano == self.cortina_activa:
            self._cortina_racha = 0
            if mano:
                self.cortina_motivo = "mano"  # volvio a medir y hay mano: ya no es por falta de lectura
            return
        self._cortina_racha += 1
        if self._cortina_racha >= self.cfg["lecturas_por_decision"]:
            self._cortina_racha = 0
            self._cambiar_cortina(mano, t_ms, d, "mano" if mano else "libre")

    def _cambiar_cortina(self, activa, t_ms, d, motivo):
        cambia = activa != self.cortina_activa
        self.cortina_activa = activa
        self.cortina_motivo = motivo if activa else None
        if activa:
            # En el mismo ciclo: prensa ARRIBA, cinta de vasos quieta, tapa y
            # empujador a reposo. La cinta de monedas sigue.
            self.hw.detener_cinta("vasos")
            for s in ("prensa", "tapas", "empujador"):
                self.hw.servo(s, self.cfg["servos"][s]["reposo"])
            self._ciclos = [c for c in self._ciclos if c[0] not in ZONA_CORTINA]
            self._cancelar_espera(t_ms, "cortina", ZONA_CORTINA)
        if cambia or activa:
            self.evento("cortina", "cortina", t_ms, {"activa": activa, "distancia_mm": d, "motivo": motivo})

    # ------------------------------------------------------------------
    # un ciclo del bucle principal
    # ------------------------------------------------------------------

    def tick(self, t_ms):
        # Latido hacia el PC y revision del enlace.
        if self.latido_pc.debe_enviar(t_ms):
            self.enviar_pc(protocolo.linea({"t": "hb", "n": self.n, "s": self.sesion}))
        cambio = self.latido_pc.cambio(t_ms)
        if cambio == "perdido":
            self.aplicar_parada_segura("sin_pc", t_ms)
            datos = protocolo.accion_sin_pc()
            datos["motivo"] = self.motivo_parada
            self.evento("esp32", "parada_segura", t_ms, datos)
        elif cambio == "recuperado":
            if self.parada_segura and self.motivo_parada == "sin_pc":
                # Solo la parada por falta de latido se levanta sola.
                self.parada_segura = False
                self.motivo_parada = None
            datos = {"vivo": True}
            if self.parada_segura:
                datos["sigue_parada"] = self.motivo_parada   # paro/error: espera reanudar
            self.evento("esp32", "enlace_pc", t_ms, datos)

        # Latido hacia el carro (le dice que la estacion esta viva).
        if self.latido_carro.debe_enviar(t_ms):
            self.enviar_carro(protocolo.linea({"t": "hb", "src": "estacion"}))
        cambio = self.latido_carro.cambio(t_ms)
        if cambio == "perdido":
            # Lo que se sabia del carro ya no vale: hasta que mande su estado
            # despues de reconectar, no se le suelta ningun vaso.
            self.estado_carro["fresco"] = False
        if cambio:
            self.evento("carro", "sin_enlace" if cambio == "perdido" else "enlace_recuperado", t_ms)

        # Sensores: la cortina primero (seguridad), despues los discretos.
        self.lecturas = self.hw.leer()
        self._revisar_cortina(t_ms)
        for nombre in ("presencia", "capacitivo", "inductivo", "hall"):
            v = self.lecturas.get(nombre)
            if v is not None and v != self._ultimas.get(nombre):
                self._ultimas[nombre] = v
                self.evento("sensor", nombre, t_ms, {"valor": v})

        # Servos que terminan su ciclo: vuelven a reposo.
        for c in list(self._ciclos):
            if t_ms >= c[1]:
                self.hw.servo(c[0], self.cfg["servos"][c[0]]["reposo"])
                self._ciclos.remove(c)
                self.evento("servo", c[0], t_ms, {"ciclo": "hecho"})

        # Carrusel: el giro lo da un Timer (hw.py); aqui solo se avisa cuando
        # termino, una vez por pedido, con cuanto tardo de verdad y el id del
        # comando que lo pidio (`pedido`). Va ANTES de las esperas: si el
        # obturador esperaba al disco, en el PC se lee "llego" y despues "arranca".
        c = self._carrusel_pedido
        if c is not None and not self.hw.carrusel_moviendose():
            self._carrusel_pedido = None
            self.evento("carrusel", "llego", t_ms, {"tubo": c[0], "lugar": c[1], "giro_ms": t_ms - c[2],
                                                    "pedido": c[3]})

        # Lo que esperaba turno (EXCLUYENTES / BLOQUEOS) arranca cuando lo que
        # lo bloqueaba ya volvio a reposo (o el disco ya paro).
        for e in list(self._en_espera):
            if self.parada_segura:
                break
            if self._bloqueado_por(e[0], t_ms) is None:
                self._en_espera.remove(e)
                if e[0] == "carrusel":
                    self._girar_carrusel(e[2], e[3], t_ms, e[4])
                    self.evento("carrusel", "arranca", t_ms, {"tubo": e[2], "esperado_ms": t_ms - e[1]})
                else:
                    self._arrancar(e[0], t_ms)
                    self.evento("servo", e[0], t_ms, {"ciclo": "arranca", "esperado_ms": t_ms - e[1]})

        # Ordenes al carro sin respuesta: se reenvian; agotados los intentos,
        # se avisa al PC (el muelle queda como "no esta": no se sabe si el carro
        # la recibio; su `estado` al reconectar lo vuelve a decir).
        for id_ in list(self._ordenes_carro):
            o = self._ordenes_carro[id_]
            if t_ms - o[2] < self._orden_reintento_ms:
                continue
            if o[3] >= self._orden_intentos:
                del self._ordenes_carro[id_]
                self.evento("carro", "carro_sin_respuesta", t_ms, {"orden": id_, "act": o[1], "intentos": o[3]})
                continue
            o[2] = t_ms
            o[3] += 1
            self.enviar_carro(o[0])

        if t_ms >= self._prox_tel:
            self._telemetria(t_ms)

    def _telemetria(self, t_ms):
        self._prox_tel = t_ms + self.cfg["telemetria_ms"]
        m = {"t": "tel", "ms": t_ms, "seguridad": "cortina" if self.cortina_activa else "ok",
             "parada_segura": self.parada_segura, "motivo_parada": self.motivo_parada,
             "cortina_motivo": self.cortina_motivo, "errores": self.errores,
             "carro_enlace": self.latido_carro.vivo(t_ms),
             "monedas": "mov" if self.hw.cinta_moviendose("monedas") else "quieta",
             "vasos": "mov" if self.hw.cinta_moviendose("vasos") else "quieta",
             "carrusel_mov": self.hw.carrusel_moviendose()}
        m.update(self.lecturas)
        self._mandar(m)
