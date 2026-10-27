"""El punto de entrada: `atender` pasa una frase por los proveedores (DeepSeek -> modelo local ->
reglas), valida las ordenes y guarda la conversacion."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

# llm y audio se usan por el modulo (llm.cliente_local()): MODELO_LOCAL cambia en marcha y las
# pruebas reemplazan esas funciones en su modulo.
from . import audio, llm
from .conocimiento import normalizar
from .estado import estado_en_vivo
from .llm import MAX_CARACTERES_DOCS_LOCAL, MAX_CARACTERES_DOCS_LOCAL_BASE, MODELO_LOCAL_BASE, TURNOS_DE_MEMORIA
from .mensajes import conversacion, guardar_mensaje, marcar_pensando
from .ordenes import describir_ordenes, validar_accion
from .reglas import (PIDE_MOVIMIENTO, RESPUESTA_ATRAVESAR, SIN_SENSOR, corregir_giros, destino_imposible, es_consulta,
                     interpretar_orden_local, limpiar_markdown, pide_atravesar, pide_mover_carro, pide_paro,
                     quitar_promesas)
from .respuestas import _denominacion_nombrada, responder_local


@dataclass
class Respuesta:
    texto: str
    modo: str                                  # "deepseek", "ollama" o "local" (reglas)
    ordenes: list[dict] = field(default_factory=list)   # validas: van a la tabla `ordenes`
    descartadas: list[str] = field(default_factory=list)
    documentos: list[str] = field(default_factory=list)
    aviso: str = ""


def atender(frase: str, conexion: sqlite3.Connection, *, usar: str = "auto", usar_deepseek: bool = True,
            cliente=None, cliente_ia_local=None) -> Respuesta:
    """Atiende una frase y guarda la conversacion. Proveedores, en orden:
    DeepSeek (si hay clave y responde) -> modelo LOCAL de Ollama (si esta
    corriendo) -> interprete de reglas (siempre). `usar`: "auto", "deepseek",
    "ollama" o "reglas" (para probar uno solo). NO deja las ordenes en la
    tabla: eso lo hace quien llama (el dashboard), para que la persona vea
    que se va a hacer."""
    if not usar_deepseek:
        usar = "reglas"
    estado = estado_en_vivo(conexion)
    historial = conversacion(conexion, 2 * TURNOS_DE_MEMORIA)
    avisos = []
    crudo = None
    if pide_atravesar(frase):
        crudo = {"respuesta": RESPUESTA_ATRAVESAR, "acciones": [], "documentos": []}
        modo = "local"
    if crudo is None and usar in ("auto", "deepseek"):
        if cliente is None and usar == "auto" and llm.cliente_deepseek() is not None and not audio.hay_internet():
            avisos.append("Sin internet: no se consulta DeepSeek.")
            cliente = False
        cliente = cliente if cliente is not None else llm.cliente_deepseek()
        if cliente is False:
            pass
        elif cliente is None:
            avisos.append("Sin clave de DeepSeek (DEEPSEEK_API_KEY).")
        else:
            try:
                marcar_pensando(conexion, "deepseek", frase)
                crudo = llm.preguntar_deepseek(cliente, frase, estado, historial)
                modo = "deepseek"
            except Exception as error:  # red caida, clave rechazada, JSON roto...
                avisos.append(f"DeepSeek no respondió ({type(error).__name__}: {str(error)[:90]}).")
    if crudo is None and usar in ("auto", "ollama") and SIN_SENSOR.search(normalizar(frase)):
        # Medidas que ningun sensor toma: las reglas lo dicen sin inventar (el modelo local
        # contestaba "7,4 V en este momento", que es el valor nominal, no una medicion).
        crudo = {"respuesta": responder_local(frase, estado), "acciones": [], "documentos": []}
        modo = "local"
    if crudo is None and usar in ("auto", "ollama") and estado.get("hay_datos") \
            and _denominacion_nombrada(normalizar(frase)) and re.search(r"\b(almac|almasen|tubo)", normalizar(frase)):
        # "cuántas monedas de mil hay en el almacén" es una LECTURA de un número, que las reglas
        # tienen exacto. El modelo local chico, aun con el número como dato verificado, repetía las
        # monedas aceptadas (3) en vez de las del tubo (0, recién soltado un lote): 3 de 4 veces mal.
        crudo = {"respuesta": responder_local(frase, estado), "acciones": [], "documentos": []}
        modo = "local"
    if crudo is None and usar in ("auto", "ollama") and interpretar_orden_local(frase):
        # Una orden clara la decide el interprete de reglas (siempre igual), no el modelo
        # chico: en las pruebas, "gira 45 grados a la derecha" le hizo inventar 4 ordenes
        # seguidas. El modelo local se usa para lo que hace bien: responder preguntas.
        ordenes = interpretar_orden_local(frase)
        crudo = {"respuesta": describir_ordenes(ordenes), "acciones": ordenes, "documentos": []}
        modo = "local"
    if crudo is None and usar in ("auto", "ollama"):
        local = cliente_ia_local or llm.cliente_local()
        if local is None:
            avisos.append(f"El modelo local ({llm.MODELO_LOCAL}) no está corriendo (Ollama).")
        else:
            try:
                marcar_pensando(conexion, "ollama", frase)
                # Menos contexto: pocos eventos, menos historial y menos documentacion.
                compacto = {k: v for k, v in estado.items() if k not in ("ultimos_eventos", "errores_del_filtro")}
                limite = (MAX_CARACTERES_DOCS_LOCAL if llm.MODELO_LOCAL != MODELO_LOCAL_BASE
                          else MAX_CARACTERES_DOCS_LOCAL_BASE)
                # Si las reglas ya tienen la cifra exacta, va como dato verificado: el modelo chico
                # confundia "cuanto pesan" (gramos) con pesos colombianos.
                regla = responder_local(frase, estado) if estado.get("hay_datos") else ""
                verificado = "" if regla.startswith(("Sin DeepSeek", "No tengo")) else regla
                crudo = llm.preguntar_llm(local, llm.MODELO_LOCAL, frase, compacto, historial[-2:], limite,
                                          con_readme=False, dato_verificado=verificado)
                modo = "ollama"
            except Exception as error:
                avisos.append(f"El modelo local no respondió ({type(error).__name__}: {str(error)[:90]}).")
    marcar_pensando(conexion, None)
    aviso = " ".join(avisos + (["Respondo con el intérprete de reglas."] if crudo is None and avisos else []))
    if crudo is None:
        ordenes = interpretar_orden_local(frase)
        texto = (describir_ordenes(ordenes) if ordenes else responder_local(frase, estado))
        crudo = {"respuesta": texto, "acciones": ordenes, "documentos": []}
        modo = "local"
    validas, descartadas = [], []
    carro_ya = False
    if not isinstance(crudo.get("acciones"), list):
        crudo["acciones"] = []
    if es_consulta(frase) and crudo["acciones"]:
        # Una pregunta (o un "explícame", "dime", "cuéntame"...) nunca mueve nada, con ningún
        # proveedor (en las pruebas, "¿cuántos vasos llegaron a la meta?" hizo que el modelo local
        # mandara el carro a un punto).
        descartadas.append("una pregunta o un pedido de información no da órdenes")
        crudo["acciones"] = []
    if not PIDE_MOVIMIENTO.search(normalizar(frase)) or not pide_mover_carro(frase):
        # Candado para TODOS los proveedores (antes solo el modelo local): sin un verbo de
        # movimiento en la frase, ninguna orden al carro; y tampoco si el verbo es de otra cosa
        # ("la moneda avanza por la cinta", "sigue la línea de producción": 2026-09-29).
        quitadas = [a for a in crudo["acciones"] if isinstance(a, dict) and a.get("cmd") == "carro"]
        if quitadas:
            descartadas.append("se propuso mover el carro sin que la frase lo pidiera")
            crudo["acciones"] = [a for a in crudo["acciones"] if a not in quitadas]
    if not pide_paro(frase):
        # El paro detiene TODO y solo sale con una corrida nueva: solo con un imperativo explícito.
        quitadas = [a for a in crudo["acciones"] if isinstance(a, dict) and a.get("cmd") == "paro"]
        if quitadas:
            descartadas.append('paro: solo con una orden explícita ("haz paro", "paro de emergencia", "para todo ya")')
            crudo["acciones"] = [a for a in crudo["acciones"] if a not in quitadas]
    for a in corregir_giros(frase, crudo["acciones"]):
        orden, motivo = validar_accion(a)
        if orden and orden["cmd"] == "carro" and orden["accion"] == "ir_a":
            # Un destino dentro de la planta, la canaleta o el muelle, o fuera del piso: ni se
            # manda (el carro tambien lo rechazaria), y la respuesta dice por que en vez de
            # prometer el movimiento.
            imposible = destino_imposible(orden["x"], orden["y"])
            if imposible:
                descartadas.append(imposible)
                crudo["respuesta"] = f"No lo muevo: {imposible}."
                continue
        if orden and orden["cmd"] == "carro" and carro_ya:
            # Una orden nueva al carro reemplaza a la anterior: mandar varias en el mismo
            # mensaje solo dejaria la ultima. Se cumple la primera; las demas se piden despues.
            descartadas.append(f"{orden['accion']}: una sola orden al carro por mensaje")
            continue
        if orden:
            carro_ya = carro_ya or orden["cmd"] == "carro"
            validas.append(orden)
        else:
            descartadas.append(motivo)
    crudo["respuesta"] = limpiar_markdown(str(crudo.get("respuesta") or ""))
    if not any(o["cmd"] == "carro" for o in validas):
        # No se promete lo que no se mandó: sin orden al carro, fuera las oraciones "se moverá...".
        texto, quito = quitar_promesas(crudo["respuesta"])
        if quito:
            crudo["respuesta"] = (texto + " " if texto else "") + "No mandé ninguna orden al carro: no se mueve."
    guardar_mensaje(conexion, "usuario", frase)
    guardar_mensaje(conexion, "asistente", crudo["respuesta"], modo=modo, acciones=validas)
    return Respuesta(crudo["respuesta"], modo, validas, descartadas, crudo.get("documentos", []), aviso)
