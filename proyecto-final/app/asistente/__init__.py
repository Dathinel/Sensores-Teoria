"""Asistente del proyecto (fase 7, docs/especificacion.md seccion 14).

Misma idea que el tema 4 del repositorio (4-chatbot-asistente-voz/comando_voz.py):
una frase en palabras normales (escrita o dicha) va a la API de DeepSeek, que
responde SOLO con un objeto JSON; el programa valida ese JSON y recien ahi
actua. Aca el JSON trae dos cosas:

    {"respuesta": "texto para la persona",
     "acciones": [{"cmd": "carro", "accion": "avanzar", "distancia_m": 0.3}, ...]}

- `respuesta`: contesta con los datos del proyecto. Para eso, en cada pregunta
  se le manda (1) el estado EN VIVO de la corrida sacado de SQLite (totales,
  monedas por denominacion, rechazos por causa, vasos, carro, alarmas, lo que
  acaba de pasar) y (2) la documentacion del proyecto que tiene que ver con la
  pregunta. "Lee todo el proyecto" por busqueda: todos los documentos (README,
  docs/especificacion.md, docs/*.md, la configuracion) se parten en secciones y se mandan las
  que mas palabras comparten con la pregunta. Mandar los ~300 kB completos en
  cada pregunta seria lento y caro, y no mejora la respuesta.
- `acciones`: ordenes para la linea o el carro, las MISMAS que dejan los botones
  del dashboard en la tabla `ordenes` (el supervisor las valida otra vez; el
  carro, una tercera vez). El modelo nunca mueve nada directamente: si propone
  algo que no esta en la lista blanca de abajo, se descarta.

Sin clave de DeepSeek o sin internet (el dia de la sustentacion la red del
salon puede fallar), un interprete LOCAL entiende las ordenes y las preguntas
basicas con expresiones regulares, y para lo demas muestra la parte de la
documentacion que mas se parece a la pregunta. Asi el asistente nunca queda
mudo.

Foco (usuario, 2026-09-28): la especialidad del asistente es el filtrado de monedas (elemento 7) y
el movimiento del carro; lo demas tambien lo responde. Eso se nota en el prompt de sistema, en el
peso de la busqueda (factor_foco), en el orden del estado en vivo (monedas, carro, lo demas) y en las
reglas (rechazos con su causa, denominaciones, almacen, ultima inspeccion, donde esta el carro).
Como funciona el modelo local por dentro y por que se eligio: docs/modelo-local.md.

Regla de la seccion 14: nunca inventa cifras. Las cifras salen del estado
inyectado; si una no esta, dice que no tiene ese dato.

El paquete, por partes (antes era un solo archivo, app/asistente.py):

- `entrada.py`: `atender`, el punto de entrada (proveedores, candados y lista blanca).
- `conocimiento.py`: los documentos partidos en secciones y la busqueda.
- `estado.py`: el estado en vivo de la corrida (SQLite).
- `mensajes.py`: la conversacion guardada en la base.
- `ordenes.py`: la lista blanca de ordenes.
- `llm.py`: DeepSeek y el modelo local (Ollama): prompt, clientes y pregunta.
- `reglas.py`: el interprete local de frases (sin internet).
- `respuestas.py`: las respuestas por reglas, con las cifras.
- `audio.py`: internet y voz (oir y hablar, con y sin internet).
- `__main__.py`: `python -m app.asistente --preparar-local | --preparar-voz | --decir RUTA`.

Todo se reexporta aqui (`from app import asistente; asistente.atender(...)`). Una prueba que
reemplaza una funcion (monkeypatch) la reemplaza en su modulo (`asistente.llm.cliente_local`,
`asistente.audio.hay_internet`): ahi la buscan `atender`, el dashboard y el servidor.

Este paquete no importa Streamlit: lo usa el dashboard y se puede probar solo.
"""

from __future__ import annotations

from app.rutas import RAIZ  # noqa: F401

from . import llm
from .audio import (  # noqa: F401
    MODELO_VOZ, _internet, _whisper_modelo, hay_internet, preparar_voz, transcribir, transcribir_local, voz, voz_local)
from .conocimiento import (  # noqa: F401
    DOCUMENTOS, FOCO_CARRO, FOCO_MONEDAS, MAX_CARACTERES_DOCS, MAX_SECCION, PESO_FOCO, Seccion, buscar, corpus,
    factor_foco, normalizar)
from .entrada import Respuesta, atender  # noqa: F401
from .estado import ESTADO_CARRO, estado_en_vivo, viajes_del_carro  # noqa: F401
from .llm import (  # noqa: F401
    MAX_CARACTERES_DOCS_LOCAL, MAX_CARACTERES_DOCS_LOCAL_BASE, MODELO, MODELO_LOCAL_BASE, PROMPT_SISTEMA,
    TURNOS_DE_MEMORIA, URL_DEEPSEEK, URL_LOCAL, cliente_deepseek, cliente_local, precargar_local, preguntar_deepseek,
    preguntar_llm, preparar_local)
from .mensajes import borrar_conversacion, conversacion, guardar_mensaje, marcar_pensando, pensando  # noqa: F401
from .ordenes import ACCIONES_CARRO, ORDENES_LINEA, describir_ordenes, validar_accion  # noqa: F401
from .reglas import (  # noqa: F401
    AJENO_AL_CARRO, ATRAVESAR, CARRO, ESTRUCTURA, FUNCIONAMIENTO_AUTOMATICO, PARO_IMPERATIVO, PARO_SOLO,
    PIDE_INFORMACION, PIDE_MOVIMIENTO, PROMESA_IMPERSONAL, PROMESA_MOVIMIENTO, PROMESA_PRIMERA_PERSONA,
    RESPUESTA_ATRAVESAR, SIN_SENSOR, corregir_giros, destino_imposible, es_consulta, es_pedido_con_que, es_pregunta,
    interpretar_orden_local, limpiar_markdown, pide_atravesar, pide_informacion, pide_mover_carro, pide_paro,
    pide_pausa_linea, promete_movimiento, quitar_promesas)
from .respuestas import (  # noqa: F401
    CONSUMO, EXPLICA_CAUSA, MONTAJE, NOMBRE_CAUSA, SABER_FILTRADO, consumo_electrico, peso_montaje, responder_local)


def __getattr__(nombre: str):
    # MODELO_LOCAL cambia en marcha (cliente_local cae al modelo de base si falta el de contexto
    # largo): se lee siempre de llm, para que el dashboard y el chequeo muestren el que se usa.
    if nombre == "MODELO_LOCAL":
        return llm.MODELO_LOCAL
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")
