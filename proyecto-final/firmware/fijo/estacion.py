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
#     (cintas quietas, prensa arriba, desvio al rechazo, escapes cerrados).
#   - Cortina de seguridad: la reaccion es LOCAL (no espera al PC, que puede
#     estar colgado): prensa arriba y cinta de vasos quieta en el mismo ciclo.
#   - Puente con el carro: lo que llega del PC con dst "carro" sale por
#     ESP-NOW; lo que manda el carro se reenvia al PC tal cual.
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
        self.parada_segura = False
        self.cortina_activa = False
        self.lecturas = {}
        self._ultimas = {}                # ultima lectura publicada de cada sensor discreto
        self._ciclos = []                 # [nombre_servo, t_vuelta] de servos en su ciclo
        self._prox_tel = 0
        self.errores = 0                  # lineas rotas o comandos desconocidos
        self.aplicar_parada_segura(inicial=True)

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
            return
        if m["t"] != "cmd" or "id" not in m:
            self.errores += 1
            return
        nuevo, ack = self.receptor.recibir(m)
        if not nuevo:
            self.enviar_pc(protocolo.linea(ack))   # repetido: solo el ack
            return
        if m.get("dst") == "carro":
            # Puente: la orden sigue al carro por ESP-NOW (el carro confirma
            # por su cuenta con sus eventos). Aca se confirma que salio.
            self.enviar_carro(protocolo.linea(m))
            self.enviar_pc(protocolo.linea(ack))
            return
        error = self._ejecutar(m, t_ms)
        if error:
            ack["ok"] = False
            ack["error"] = error
        self.enviar_pc(protocolo.linea(ack))

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

    def _ejecutar(self, m, t_ms):
        acciones = COMANDOS.get(m.get("dst"), {})
        metodo = acciones.get(m.get("act"))
        if metodo is None:
            self.errores += 1
            return "comando desconocido"
        if self.parada_segura and m.get("dst") != "estado":
            return "parada segura: falta el latido del PC"
        return getattr(self, metodo)(m, t_ms)

    # ------------------------------------------------------------------
    # comandos
    # ------------------------------------------------------------------

    def _avanzar_monedas(self, m, t_ms):
        if self.hw.cinta_moviendose("monedas"):
            return "la cinta de monedas todavia se mueve"
        self.hw.avanzar_cinta("monedas", self.cfg["cinta_monedas_mm"], self.cfg["tiempos"]["avance_casilla_monedas"])
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
        if self.cortina_activa and servo in ("prensa", "tapas", "empujador"):
            return "cortina activa: tapa, prensa y empujador congelados"
        if any(c[0] == servo for c in self._ciclos):
            return servo + " todavia esta en su ciclo"
        self.hw.servo(servo, self.cfg["servos"][servo]["activo"])
        mitad = self.cfg["tiempos"][CICLOS_SERVO[servo]] // 2
        self._ciclos.append([servo, t_ms + mitad])

    def _tapar(self, m, t_ms):
        return self._ciclo("tapas", t_ms)

    def _prensar(self, m, t_ms):
        return self._ciclo("prensa", t_ms)

    def _empujar(self, m, t_ms):
        return self._ciclo("empujador", t_ms)

    def _obturador(self, m, t_ms):
        return self._ciclo("obturador", t_ms)

    def _soltar_vaso(self, m, t_ms):
        return self._ciclo("canaleta", t_ms)

    def _desvio_almacen(self, m, t_ms):
        self.hw.servo("desvio", self.cfg["servos"]["desvio"]["activo"])

    def _desvio_rechazo(self, m, t_ms):
        self.hw.servo("desvio", self.cfg["servos"]["desvio"]["reposo"])

    def _carrusel_ir(self, m, t_ms):
        tubo = m.get("tubo")
        if not isinstance(tubo, int) or not 0 <= tubo < 6:
            return "tubo invalido (0 a 5)"
        self.hw.carrusel_a(tubo)

    def _carrusel_referencia(self, m, t_ms):
        # Gira hasta que el Hall ve el iman: ahi es el tubo 0.
        self.hw.carrusel_buscar_referencia()

    def _leer_estado(self, m, t_ms):
        self._telemetria(t_ms)

    def _parar(self, m, t_ms):
        # Paro de emergencia del dashboard: lo mismo que la parada segura.
        self.aplicar_parada_segura()
        self.evento("esp32", "parada_segura", t_ms, {"motivo": "paro"})

    def _reanudar(self, m, t_ms):
        if not self.latido_pc.vivo(t_ms):
            return "sin latido del PC"
        self.parada_segura = False
        self.evento("esp32", "reanudado", t_ms)

    # ------------------------------------------------------------------
    # seguridad
    # ------------------------------------------------------------------

    def aplicar_parada_segura(self, inicial=False):
        """protocolo.accion_sin_pc(): todo a su posicion segura."""
        self.hw.detener_cintas()
        for nombre, s in self.cfg["servos"].items():
            self.hw.servo(nombre, s["reposo"])
        self._ciclos = []
        self.parada_segura = True
        self.inicial = inicial

    def _revisar_cortina(self, t_ms):
        d = self.lecturas.get("cortina_mm")
        activa = d is not None and d < self.cfg["cortina_umbral_mm"]
        if activa == self.cortina_activa:
            return
        self.cortina_activa = activa
        if activa:
            # En el mismo ciclo: prensa ARRIBA, cinta de vasos quieta, tapa y
            # empujador a reposo. La cinta de monedas sigue.
            self.hw.detener_cinta("vasos")
            for s in ("prensa", "tapas", "empujador"):
                self.hw.servo(s, self.cfg["servos"][s]["reposo"])
            self._ciclos = [c for c in self._ciclos if c[0] not in ("prensa", "tapas", "empujador")]
        self.evento("cortina", "cortina", t_ms, {"activa": activa, "distancia_mm": d})

    # ------------------------------------------------------------------
    # un ciclo del bucle principal
    # ------------------------------------------------------------------

    def tick(self, t_ms):
        # Latido hacia el PC y revision del enlace.
        if self.latido_pc.debe_enviar(t_ms):
            self.enviar_pc(protocolo.linea({"t": "hb", "n": self.n}))
        cambio = self.latido_pc.cambio(t_ms)
        if cambio == "perdido":
            self.aplicar_parada_segura()
            self.evento("esp32", "parada_segura", t_ms, protocolo.accion_sin_pc())
        elif cambio == "recuperado" and self.parada_segura:
            self.parada_segura = False
            self.evento("esp32", "enlace_pc", t_ms, {"vivo": True})

        # Latido hacia el carro (le dice que la estacion esta viva).
        if self.latido_carro.debe_enviar(t_ms):
            self.enviar_carro(protocolo.linea({"t": "hb", "src": "estacion"}))
        cambio = self.latido_carro.cambio(t_ms)
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

        if t_ms >= self._prox_tel:
            self._telemetria(t_ms)

    def _telemetria(self, t_ms):
        self._prox_tel = t_ms + self.cfg["telemetria_ms"]
        m = {"t": "tel", "ms": t_ms, "seguridad": "cortina" if self.cortina_activa else "ok",
             "parada_segura": self.parada_segura, "errores": self.errores,
             "carro_enlace": self.latido_carro.vivo(t_ms),
             "monedas": "mov" if self.hw.cinta_moviendose("monedas") else "quieta",
             "vasos": "mov" if self.hw.cinta_moviendose("vasos") else "quieta"}
        m.update(self.lecturas)
        self._mandar(m)
