# Logica del ESP32 del CARRO (fase 8). MicroPython en la placa; CPython en las
# pruebas del PC con un hardware falso.
#
# El control es EL MISMO de la simulacion: control/vehiculo.py (ControlCarro),
# compilado para el ESP32 por firmware/preparar.py. Por eso lo que se probo en
# PyBullet (seguir la linea, esquivar, meta, vuelta, muelle, ordenes) es lo
# que corre aqui; este archivo solo lo conecta con la radio y el hardware.
#
# El carro decide SOLO (no espera al PC para frenar): a 50 Hz lee sensores,
# le pregunta al control y mueve los motores. Por la radio:
#   - manda sus eventos numerados y los guarda hasta el ack (si el enlace se
#     corta, los reenvia en orden al volver);
#   - manda y escucha el latido (sin oir nada en 1 s = enlace perdido: termina
#     la vuelta y queda en el muelle);
#   - recibe ordenes del asistente/botones (dst "carro") y las pasa a
#     ControlCarro.ordenar, que las valida otra vez.

try:
    import protocolo
except ImportError:
    from control import protocolo


class CarroFirmware:
    def __init__(self, hw, control, cfg, enviar_radio):
        p = cfg["protocolo"]
        self.hw = hw
        self.control = control
        self.enviar_radio = enviar_radio
        self.emisor = protocolo.Emisor(p["carro_reintento_ms"], None, p.get("carro_cola_max", 32))
        self.latido = protocolo.Latido(p["carro_latido_ms"], p["carro_enlace_perdido_ms"])
        self.receptor = protocolo.Receptor()     # ordenes (un reenvio no se ejecuta dos veces)
        self.lectura = None

    def _evento(self, datos, t_ms):
        m = {"t": "evt", "src": "carro"}
        m.update(datos)
        if self.lectura is not None:
            m["cuna"] = self.lectura.cuna
        pos = self.control.posicion_estimada()
        if pos is not None:
            m["x"], m["y"] = round(pos[0], 3), round(pos[1], 3)
        self.enviar_radio(protocolo.linea(self.emisor.enviar(m, t_ms)))

    def mensaje(self, texto, t_ms):
        """Un mensaje de la estacion (por ESP-NOW)."""
        m = protocolo.parsear_linea(texto)
        if m is None or m.get("src") == "carro":
            return                               # basura o el eco de lo propio
        self.latido.oido(t_ms)
        if m["t"] == "ack" and m.get("dst") == "carro":
            self.emisor.ack(m["id"])
        elif m["t"] == "cmd" and m.get("dst") == "carro" and "id" in m:
            nuevo, _ = self.receptor.recibir(m)
            if not nuevo:
                return
            orden = {"accion": m.get("act")}
            for k, v in m.items():
                if k not in ("t", "id", "dst", "act", "src", "origen"):
                    orden[k] = v
            ok, detalle = self.control.ordenar(orden)
            self._evento({"ev": "respuesta_orden", "orden": m["id"], "ok": ok, "detalle": detalle}, t_ms)

    def tick(self, t_ms, dt):
        c = self.control
        c.enlace_vivo = self.latido.vivo(t_ms) if self.latido.ultimo_oido is not None else True
        self.lectura = self.hw.leer()
        v_izq, v_der = c.paso(self.lectura, dt)
        self.hw.motores(v_izq, v_der, c.pwm_bajo)
        for e in c.eventos:
            self._evento(e, t_ms)
        c.eventos = []
        # Radio: reenviar lo que no tiene ack, latido y estado al reconectar.
        for m in self.emisor.a_reenviar(t_ms):
            self.enviar_radio(protocolo.linea(m))
        if self.latido.debe_enviar(t_ms):
            self.enviar_radio(protocolo.linea({"t": "hb", "src": "carro"}))
        if self.latido.cambio(t_ms) == "recuperado":
            # Lo primero al volver el enlace: su estado, con la cuna (punto 15).
            self._evento({"ev": "estado", "estado": c.estado, "fase": c.fase}, t_ms)
