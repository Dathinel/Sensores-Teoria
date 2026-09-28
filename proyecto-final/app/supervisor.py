"""Proceso supervisor (CLAUDE.md, seccion 8): corre la linea y escribe en
SQLite. Es el UNICO proceso que toca la simulacion (y, en la fase 8, el
puerto serial); el dashboard de Streamlit corre en otro proceso, solo lee
de SQLite y deja ordenes en la tabla `ordenes`, que este proceso consume.

Por que dos procesos y no uno: Streamlit reejecuta el script completo en
cada interaccion (cada click, cada refresco). Si la simulacion o el puerto
serial vivieran dentro del dashboard, se reiniciarian o duplicarian cada
vez. Con la base de datos en medio, el dashboard puede refrescarse todo lo
que quiera sin que la linea se entere.

Bucle principal, una vuelta:
  1. Leer ordenes pendientes (iniciar, pausar, reanudar, paro, velocidad,
     sabotajes) y aplicarlas.
  2. Si la linea esta corriendo, un tick de `sim.planta.PlantaSimulada`.
  3. Guardar los eventos de ese tick y una fotografia del estado completo
     (telemetria) para la pestana "Linea en vivo".
  4. Dormir lo necesario para que la linea avance a ritmo humano.

Uso, desde la raiz del repo:
    python -m app.supervisor                      # espera la orden "iniciar" del dashboard
    python -m app.supervisor --auto prueba_completa      # arranca solo con ese escenario
(normalmente lo arranca `visor.bat`, via app/lanzar.py). La simulacion corre
sin ventana de PyBullet: lo que se mira es el visor 3D.
"""

from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

from app import configuracion, db, servidor
from control.embalaje import EmbalajeVasos
from control.hal.backend_sim import EstacionBackendSim
from control.linea import LineaMonedas
from sim.sensores_sim import CamaraOraculo
from sim.carga_escenarios import (ESCENARIO_UNICO, PIEZAS, PRUEBAS_DE_UN_FILTRO, cargar_escenario,
                                  escenarios_validos, especificacion_pieza, listar_escenarios,
                                  prueba_de_un_filtro)
from sim.geometria import geometria_completa
from sim.mundo import EscenaEstacion
from sim.planta import PlantaSimulada, opciones_desde_config

# Estados de la linea que ve el dashboard.
DETENIDA = "detenida"
CORRIENDO = "corriendo"
PAUSADA = "pausada"
PARO = "paro"
TERMINADA = "terminada"


class Supervisor:
    def __init__(self, ruta_bd: str | Path, *, parametros: dict | None = None,
                 puerto_http: int | None = None):
        self.parametros = parametros if parametros is not None else configuracion.cargar_parametros()
        Path(ruta_bd).parent.mkdir(parents=True, exist_ok=True)
        self.conexion = db.conectar(ruta_bd)
        db.activar_wal(self.conexion)

        self.estado_linea = DETENIDA
        # Respuesta a la ultima orden (el visor la muestra: cada boton dice si
        # hizo algo o por que no pudo).
        self.ultima_orden: dict | None = None
        self._n_orden = 0
        self.escenario_nombre: str | None = None
        self.velocidad = 1.0
        self.confianza_minima = self.parametros["filtrado"]["confianza_minima"]
        self.probabilidad_error = 0.0
        self.planta: PlantaSimulada | None = None
        self._escena: EscenaEstacion | None = None
        self._ts_vasos: dict[int, dict] = {}
        self._eventos_tick: list[dict] = []

        # Estado en memoria para el visor 3D (app/servidor.py). El servidor
        # solo arranca si se pide un puerto; las pruebas no lo necesitan.
        self.compartido = servidor.EstadoCompartido(geometria_completa(self.parametros), Path(ruta_bd))
        self.servidor_http = servidor.arrancar(self.compartido, puerto_http) if puerto_http else None

        # Fase 8: `hardware.backend: real` (UNA linea de config/parametros.yaml)
        # cambia la simulacion por los ESP32 de verdad. Sin placa conectada, el
        # puente usa la estacion emulada (el mismo firmware con hardware falso).
        hw = self.parametros.get("hardware", {})
        self.backend = hw.get("backend", "sim")
        self.puente = None
        if self.backend == "real":
            from app.puente_serial import PuenteESP32
            from control.hal.backend_real import BackendReal

            self._t0 = time.monotonic()
            puerto = hw.get("puerto")
            self.puente = PuenteESP32(self.parametros, None if puerto in (None, "auto") else puerto)
            self.hardware = BackendReal(self.puente, self._ms, self.parametros["vasos"])
            self._eventos_leidos = 0
            self._tick_real = 0

        self._publicar_telemetria()

    # ------------------------------------------------------------------
    # ordenes del dashboard
    # ------------------------------------------------------------------

    def iniciar(self, escenario: str, *, confianza_minima: float | None = None,
                probabilidad_error: float | None = None, conservar_almacen: bool | None = None) -> None:
        """Nueva corrida: escena limpia, registros vacios y tablas de la
        corrida anterior borradas."""
        if self.backend == "real":
            # Con hardware no hay escena que armar: se limpia la corrida y la
            # estacion sale de su parada (si oye al PC).
            db.reiniciar_corrida(self.conexion)
            self.escenario_nombre = "hardware real"
            self.estado_linea = CORRIENDO
            self.puente.comando("estado", "reanudar", self._ms())
            self.conexion.commit()
            return
        if confianza_minima is not None:
            self.confianza_minima = float(confianza_minima)
        if probabilidad_error is not None:
            self.probabilidad_error = float(probabilidad_error)

        cliente_anterior = self._escena.cliente if self._escena is not None else None
        # Sin ventana: el ritmo real (tiempos_ms) lo da la espera de `correr`.
        self._escena = EscenaEstacion(reusar_cliente=cliente_anterior)
        backend = EstacionBackendSim(
            self._escena, camara=CamaraOraculo(probabilidad_error=self.probabilidad_error)
        )
        sim = self.parametros.get("simulacion", {})
        if sim.get("errores_sensores"):
            # Cada sensor con su error individual (config: errores_sensores),
            # como en el montaje real. Semilla fija: corrida repetible.
            backend.aplicar_errores(self.parametros["errores_sensores"], sim.get("semilla"),
                                    errores_actuadores=self.parametros.get("errores_actuadores"))
        linea = LineaMonedas(
            configuracion.parametros_filtrado(self.parametros, confianza_minima=self.confianza_minima)
        )
        p_planta = self.parametros["planta"]
        if self.planta is not None:
            self.planta.cerrar()   # el mundo propio del carro de la corrida anterior

        db.reiniciar_corrida(self.conexion)
        self._ts_vasos = {}
        self.escenario_nombre = escenario
        self.planta = PlantaSimulada(
            self._escena, backend, linea, EmbalajeVasos(), cargar_escenario(escenario),
            **opciones_desde_config(self.parametros),
            errores_carro=bool(sim.get("errores_sensores")), semilla_carro=sim.get("semilla"),
        )
        # Turno nuevo: los tubos arrancan con lo que dejo el anterior (si el
        # grupo no lo empaco con "Embalar lo guardado").
        if conservar_almacen is None:
            conservar_almacen = p_planta.get("conservar_almacen_entre_turnos", False)
        if conservar_almacen:
            self.planta.precargar_almacen(db.leer_almacen_turno(self.conexion))
        self.estado_linea = CORRIENDO
        # Los eventos del arranque (primer vaso a llenado) tambien cuentan.
        self._guardar_eventos(self.planta.eventos_arranque)
        self._sincronizar_vasos()
        self.conexion.commit()

    def _responder(self, orden: dict, ok: bool, detalle: str) -> None:
        self._n_orden += 1
        self.ultima_orden = {"n": self._n_orden, "cmd": orden.get("cmd"), "tipo": orden.get("tipo"),
                             "accion": orden.get("accion"), "origen": orden.get("origen", "boton"),
                             "ok": ok, "detalle": detalle}
        # Tambien queda como evento: el asistente muestra que paso con cada
        # orden que dio (no solo la ultima).
        db.registrar_evento(self.conexion, "supervisor", "respuesta", self.ultima_orden)

    def aplicar_orden(self, orden: dict) -> None:
        cmd = orden.get("cmd")
        db.registrar_evento(self.conexion, "supervisor", "orden", orden)
        if self.backend == "real" and cmd not in ("iniciar", "lote", "velocidad"):
            self._orden_real(orden)
            self.conexion.commit()
            return
        corriendo = self.estado_linea == CORRIENDO and self.planta is not None

        if cmd == "iniciar" and (orden.get("escenario") or ESCENARIO_UNICO) not in escenarios_validos():
            # Llega tambien por HTTP (visor): solo los escenarios de la interfaz, nunca una ruta.
            self._responder(orden, False, f"Escenario desconocido: {orden.get('escenario')}")
        elif cmd == "iniciar":
            self.iniciar(
                orden.get("escenario") or ESCENARIO_UNICO,
                confianza_minima=orden.get("confianza_minima"),
                probabilidad_error=orden.get("probabilidad_error"),
                conservar_almacen=orden.get("conservar_almacen"),
            )
            prueba = prueba_de_un_filtro(self.escenario_nombre or "")
            self._responder(orden, True, f"Prueba de un filtro: {prueba['nombre']}" if prueba
                            else "Corrida nueva: prueba completa")
        elif cmd == "pausar":
            if corriendo:
                self.estado_linea = PAUSADA
                self._responder(orden, True, "Línea en pausa")
            else:
                self._responder(orden, False, "La línea no está corriendo")
        elif cmd == "reanudar":
            if self.estado_linea == PAUSADA:
                self.estado_linea = CORRIENDO
                self._responder(orden, True, "La línea sigue")
            else:
                self._responder(orden, False, "La línea no está en pausa")
        elif cmd == "paro":
            # Paro de emergencia: la linea queda congelada donde esta y
            # solo sale de ahi con una corrida nueva ("iniciar").
            if self.estado_linea in (CORRIENDO, PAUSADA):
                self.estado_linea = PARO
                self._responder(orden, True, "PARO: todo detenido. Sale con Iniciar")
            else:
                self._responder(orden, False, "No hay una corrida en marcha")
        elif cmd == "embalar_parciales":
            if self.planta is None:
                self._responder(orden, False, "No hay corrida")
            elif self.planta.almacen.valor_total() <= 0:
                self._responder(orden, False, "Los tubos están vacíos: no hay nada guardado")
            else:
                # Fin de turno: empacar lo que quedo guardado en los tubos (cada
                # vaso sigue siendo de una sola denominacion). Si la corrida ya
                # habia terminado, se reanuda solo para eso.
                self.planta.pedir_embalar_parciales()
                if self.estado_linea == TERMINADA:
                    self.estado_linea = CORRIENDO
                self._responder(orden, True, "Se empaca lo guardado en los tubos")
        elif cmd == "lote":
            # Monedas por vaso: vale para esta corrida y las siguientes.
            valor = int(orden.get("valor", self.parametros["planta"]["monedas_por_vaso"]))
            if self.planta is not None:
                valor = self.planta.cambiar_lote(valor)
            self.parametros["planta"]["monedas_por_vaso"] = max(1, valor)
            self._responder(orden, True, f"Lote de {max(1, valor)} monedas por vaso")
        elif cmd == "velocidad":
            self.velocidad = max(0.25, min(8.0, float(orden.get("valor", 1.0))))
            self._responder(orden, True, f"Velocidad x{self.velocidad:g}")
        elif cmd == "carro":
            # Fase 7: orden para el carro (asistente o botones del dashboard).
            if self.planta is None:
                self._responder(orden, False, "No hay corrida: empiece una para tener el carro")
            elif self.estado_linea in (PAUSADA, PARO):
                self._responder(orden, False, "La línea está en pausa o en paro: el carro no se mueve")
            else:
                ok, detalle = self.planta.orden_carro({k: v for k, v in orden.items() if k not in ("cmd", "origen")})
                if ok and self.estado_linea == TERMINADA:
                    self.estado_linea = CORRIENDO
                self._responder(orden, ok, detalle)
        elif cmd == "colocar":
            # "Colocar pieza X": esa pieza entra en la proxima carga.
            pieza = orden.get("pieza")
            if self.planta is None:
                self._responder(orden, False, "No hay corrida: empiece una primero")
            elif self.estado_linea in (PAUSADA, PARO):
                self._responder(orden, False, "La línea está en pausa o en paro")
            elif pieza not in PIEZAS:
                self._responder(orden, False, f"Pieza desconocida: {pieza}")
            else:
                self.planta.colocar_pieza(especificacion_pieza(pieza))
                if self.estado_linea == TERMINADA:
                    self.estado_linea = CORRIENDO
                self._responder(orden, True, f"{PIEZAS[pieza]['nombre']}: va en la próxima carga")
        elif cmd == "sabotaje":
            if not corriendo:
                self._responder(orden, False, "La línea no está corriendo")
            else:
                self._aplicar_sabotaje(orden)
        self.conexion.commit()

    def _orden_real(self, orden: dict) -> None:
        """Ordenes del dashboard/asistente con el hardware real: se traducen a
        comandos del firmware (firmware/fijo/estacion.py, COMANDOS)."""
        from firmware.fijo.estacion import COMANDOS

        cmd, t = orden.get("cmd"), self._ms()
        if cmd == "carro":
            datos = {k: v for k, v in orden.items() if k not in ("cmd", "accion", "origen")}
            self.puente.comando("carro", orden.get("accion"), t, **datos)
            self._responder(orden, True, "Orden enviada al carro por la radio (él la valida y responde)")
        elif cmd in ("pausar", "paro"):
            self.puente.comando("estado", "parar", t)
            self.estado_linea = PAUSADA if cmd == "pausar" else PARO
            self._responder(orden, True, "Estación en parada segura: cintas quietas, prensa arriba")
        elif cmd == "reanudar":
            self.puente.comando("estado", "reanudar", t)
            self.estado_linea = CORRIENDO
            self._responder(orden, True, "La estación sigue")
        elif cmd == "hardware" and orden.get("act") in COMANDOS.get(orden.get("dst"), {}):
            # Probar un actuador suelto (puesta en marcha del montaje).
            datos = {k: v for k, v in orden.items() if k not in ("cmd", "dst", "act", "origen")}
            self.puente.comando(orden["dst"], orden["act"], t, **datos)
            self._responder(orden, True, f"Comando {orden['dst']}.{orden['act']} enviado")
        else:
            self._responder(orden, False, f"Con hardware real todavía no se puede: {cmd}")

    def _vuelta_real(self) -> None:
        """Hardware real: el puente drena el serial; cada evento del ESP32 (y
        del carro, reenviado por el) va a SQLite con el mismo estilo src/ev, y
        la telemetria se publica para el dashboard y el visor."""
        t = self._ms()
        self.puente.atender(t)
        nuevos = self.puente.eventos[self._eventos_leidos:]
        self._eventos_leidos = len(self.puente.eventos)
        for e in nuevos:
            datos = {k: v for k, v in e.items() if k not in ("t", "src", "ev")}
            db.registrar_evento(self.conexion, e.get("src", "esp32"), e.get("ev", "evento"), datos)
            if e.get("src") == "carro" and "x" in e:
                db.registrar_ruta(self.conexion, e["x"], e["y"], e["ev"], e.get("fase", ""))
        self._tick_real += 1
        if self._tick_real % 10 == 0 or nuevos:
            self._publicar_telemetria()

    def _ms(self) -> int:
        return int((time.monotonic() - self._t0) * 1000)

    # Que hace cada sabotaje y que se responde si no puede hacerlo ahora.
    SABOTAJES = {
        "retirar_vaso": ("sabotaje_retirar_vaso", "Vaso {r} retirado", "No hay vaso en verificación ni en llenado ahora"),
        "cambiar_vaso": ("sabotaje_cambiar_vaso", "Vaso {r} cambiado por una figura",
                         "No hay vaso en verificación ni en llenado ahora"),
        "vaso_igual": ("sabotaje_cambiar_por_vaso_igual", "Vaso {r} cambiado por otro igual (otro marcador)",
                       "No hay vaso en verificación ni en llenado ahora"),
        "mano_carga": ("sabotaje_mano_en_carga", "Mano en la casilla de carga (en la próxima carga)", ""),
        "mano_saca_vaso": ("sabotaje_mano_saca_vaso", "Una mano se llevó el vaso {r}",
                           "No hay vaso en tapa ni en prensa ahora (o ya hay una mano)"),
        "mano_llenado": ("sabotaje_mano_en_llenado", "Mano sobre el vaso de llenado", "Ya hay una mano en la línea"),
        "vaso_con_algo": ("sabotaje_vaso_con_contenido", "El próximo vaso trae algo adentro", ""),
        "intruso_on": ("sabotaje_poner_intruso", "Mano en tapa/prensa (queda hasta quitarla)", "La mano ya está puesta"),
        "intruso_off": ("sabotaje_quitar_intruso", "Mano quitada de tapa/prensa", "No hay mano puesta"),
        "radio_off": ("sabotaje_cortar_radio", "Radio del carro cortada: termina la vuelta y guarda sus mensajes",
                      "La radio ya está cortada (o no hay carro simulado)"),
        "radio_on": ("sabotaje_reconectar_radio", "Radio reconectada: llegan los mensajes guardados",
                     "La radio ya está conectada"),
    }

    def _aplicar_sabotaje(self, orden: dict) -> None:
        tipo = orden.get("tipo")
        if tipo not in self.SABOTAJES:
            self._responder(orden, False, f"Sabotaje desconocido: {tipo}")
            return
        metodo, bien, mal = self.SABOTAJES[tipo]
        resultado = getattr(self.planta, metodo)()
        if resultado is None or resultado is False:
            self._responder(orden, False, mal)
        else:
            self._responder(orden, True, bien.format(r=resultado))
        # Se registra lo que HIZO el operador; si la planta se da cuenta o
        # no, eso aparece despues como evento propio de la planta
        # (`sabotaje_detectado`, `cortina`).
        db.registrar_evento(self.conexion, "operador", "sabotaje", {"tipo": tipo, "resultado": resultado})

    # ------------------------------------------------------------------
    # persistencia
    # ------------------------------------------------------------------

    def _guardar_eventos(self, eventos: list[dict]) -> None:
        ahora = db.ahora()
        for evento in eventos:
            db.registrar_evento(self.conexion, evento["src"], evento["ev"], evento)
            ev = evento["ev"]
            if ev == "elemento_final":
                db.registrar_elemento(self.conexion, evento)
            elif ev == "llenado_cerrado" and evento.get("cantidad"):
                self._ts_vasos.setdefault(evento["vaso"], {})["ts_llenado"] = ahora
            elif ev == "tapa" and evento.get("tapado"):
                self._ts_vasos.setdefault(evento["vaso"], {})["ts_tapado"] = ahora
            elif ev == "descarga" and evento.get("destino") == "entrega":
                self._ts_vasos.setdefault(evento["vaso"], {})["ts_entrega"] = ahora
            if evento["src"] == "carro" and "x" in evento:
                # Eventos del recorrido (obstaculo, evasion, meta...) en la tabla ruta.
                db.registrar_ruta(self.conexion, evento["x"], evento["y"], ev, evento.get("fase", ""))

    def _sincronizar_vasos(self) -> None:
        """La tabla `vasos` es una foto del registro de la cinta de vasos:
        se reescribe entera en cada tick (son pocos vasos)."""
        for id_vaso, casilla in self.planta.embalaje.registro.items():
            db.guardar_vaso(
                self.conexion,
                id_vaso,
                estado=casilla.estado.value,
                denominacion=casilla.denominacion,
                cantidad_monedas=casilla.cantidad_monedas,
                valor_total=casilla.valor_total,
                masa_estimada_g=round(casilla.masa_estimada_g, 2),
                **self._ts_vasos.get(id_vaso, {}),
            )

    def _publicar_telemetria(self) -> None:
        estado = self.planta.estado() if self.planta is not None else {}
        if self.backend == "real":
            tel = self.puente.tel
            estado = {"tick": self._tick_real, "hardware": self.puente.estado(),
                      "sensores": {k: tel.get(k) for k in ("presencia", "capacitivo", "inductivo", "hall")},
                      "cortina_activa": tel.get("seguridad") == "cortina",
                      "alarmas": (["sin_esp32"] if not self.puente.latido.vivo(self._ms()) else [])
                      + (["parada_segura"] if tel.get("parada_segura") else [])}
        estado.update(
            linea=self.estado_linea,
            backend=self.backend,
            escenario=self.escenario_nombre,
            escenarios_disponibles=listar_escenarios(),
            pruebas_filtro=PRUEBAS_DE_UN_FILTRO,
            piezas=[{"id": k, "nombre": v["nombre"]} for k, v in PIEZAS.items()],
            velocidad=self.velocidad,
            confianza_minima=self.confianza_minima,
            probabilidad_error=self.probabilidad_error,
            monedas_por_vaso=(self.planta.monedas_por_vaso if self.planta is not None
                              else self.parametros["planta"]["monedas_por_vaso"]),
            avance_ms=self.parametros["tiempos_ms"]["avance_casilla_monedas"],
            ciclo_ms=self._ciclo_ms(),
            ultima_orden=self.ultima_orden,
        )
        db.registrar_evento(self.conexion, "supervisor", "tel", estado)
        self.conexion.commit()
        # El visor 3D recibe ademas los eventos del ultimo tick (no van a la
        # fila 'tel' de SQLite porque ya estan guardados uno por uno).
        self.compartido.publicar(dict(estado, eventos_tick=self._eventos_tick))

    # ------------------------------------------------------------------
    # bucle
    # ------------------------------------------------------------------

    def tick(self) -> None:
        eventos = self.planta.paso()
        self._eventos_tick = eventos
        self._guardar_eventos(eventos)
        carro = self.planta.carro
        if carro is not None:
            # El recorrido de este tick, una muestra cada 0,1 s (con un solo
            # punto por tick las esquivas se veian como triangulos).
            for x, y, _ in (getattr(carro, "camino", None) or [carro.pose()])[1:] or [carro.pose()]:
                db.registrar_ruta(self.conexion, round(x, 4), round(y, 4), None,
                                  f"{carro.control.fase}:{carro.control.estado}")
        self._sincronizar_vasos()
        # Lo que hay en los tubos queda guardado en cada tick: si el turno
        # termina (o se cierra el programa) el siguiente arranca con eso.
        db.guardar_almacen_turno(self.conexion, self.planta.almacen.exportar())
        if self.planta.terminado:
            self.estado_linea = TERMINADA
        self.conexion.commit()

    def vuelta(self) -> None:
        """Una vuelta del bucle principal (separada de `correr` para poder
        probarla sin un bucle infinito)."""
        ordenes = db.tomar_ordenes_pendientes(self.conexion)
        for orden in ordenes:
            self.aplicar_orden(orden)
        if self.backend == "real":
            self._vuelta_real()
            self.conexion.commit()
            return

        if self.estado_linea == CORRIENDO and self.planta is not None:
            self.tick()
            self._publicar_telemetria()
        elif ordenes:
            self._publicar_telemetria()

    def _ciclo_ms(self) -> int:
        """Un ciclo real de la cinta de monedas: avance + pausa."""
        t = self.parametros["tiempos_ms"]
        return t["avance_casilla_monedas"] + t["pausa_casilla_monedas"]

    def correr(self) -> None:
        p_sup = self.parametros["supervisor"]
        print("Supervisor corriendo (simulacion sin ventana; mirar el visor 3D). Ctrl+C para salir.")
        try:
            while True:
                inicio = time.monotonic()
                self.vuelta()
                if self.backend == "real":
                    time.sleep(0.02)       # el serial se atiende seguido (latido cada 500 ms)
                elif self.estado_linea == CORRIENDO:
                    # Cada tick dura lo mismo que un ciclo real de la cinta
                    # (tiempos_ms, dividido por la velocidad elegida): la
                    # fisica es instantanea y se completa el resto durmiendo.
                    restante = self._ciclo_ms() / 1000 / self.velocidad - (time.monotonic() - inicio)
                    time.sleep(max(0.0, restante))
                else:
                    time.sleep(p_sup["intervalo_ordenes_s"])
        except KeyboardInterrupt:
            print("Supervisor detenido.")
        except sqlite3.OperationalError as error:
            print(f"Error de base de datos: {error}")
        finally:
            if self.servidor_http is not None:
                self.servidor_http.shutdown()
            if self.puente is not None:
                self.puente.cerrar()
            self.conexion.close()


def main() -> None:
    analizador = argparse.ArgumentParser(description="Supervisor de la linea (backend sim).")
    analizador.add_argument("--auto", metavar="ESCENARIO", help="arrancar sin esperar la orden del dashboard")
    analizador.add_argument("--bd", help="ruta de la base SQLite (por defecto la de config/parametros.yaml)")
    args = analizador.parse_args()

    parametros = configuracion.cargar_parametros()
    ruta = Path(args.bd) if args.bd else configuracion.ruta_bd(parametros)
    puerto = parametros["supervisor"]["puerto_http"]
    supervisor = Supervisor(ruta, parametros=parametros, puerto_http=puerto)
    print(f"Visor 3D en http://localhost:{puerto}")
    if args.auto:
        supervisor.iniciar(args.auto)
        supervisor._publicar_telemetria()
    supervisor.correr()


if __name__ == "__main__":
    main()
