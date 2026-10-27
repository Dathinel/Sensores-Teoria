"""Los modelos de lenguaje: DeepSeek (en la nube) y el modelo LOCAL de Ollama, con el mismo
prompt, el mismo JSON y la misma lista blanca. Aqui estan el prompt, los clientes y la pregunta."""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.rutas import RAIZ

from .conocimiento import MAX_CARACTERES_DOCS, buscar

URL_DEEPSEEK = "https://api.deepseek.com"
MODELO = os.environ.get("DEEPSEEK_MODELO", "deepseek-chat")
# Proveedor LOCAL (usuario, 2026-09-27): Ollama con un modelo chico en el mismo portatil, para
# probar el asistente sin internet ni clave. El modelo (~1,9 GB, Q4_K_M) vive FUERA del proyecto,
# en la carpeta que diga OLLAMA_MODELS (en este portatil, D:\cosas uni\Micros\instalados): no pesa
# en GitHub. Explicacion completa del modelo y de como se usa: docs/modelo-local.md. Ollama habla el mismo formato de OpenAI, asi que se usa
# el mismo cliente, el mismo prompt, el mismo JSON y la misma lista blanca que con DeepSeek.
URL_LOCAL = os.environ.get("ASISTENTE_URL_LOCAL", "http://localhost:11434")
# `qwen2.5-proyecto` = qwen2.5:3b con 8192 tokens de contexto (Ollama trae ~4000 por defecto),
# creado con `python -m app.asistente --preparar-local`. Si no existe, se usa el de base.
MODELO_LOCAL = os.environ.get("ASISTENTE_MODELO_LOCAL", "qwen2.5-proyecto")
MODELO_LOCAL_BASE = "qwen2.5:3b"
# Ollama usa por defecto un contexto de ~4000 tokens: si el prompt lo pasa, se corta POR EL
# PRINCIPIO y el modelo pierde las instrucciones (se vio: respondia sin la clave "respuesta").
# Por eso al modelo local va menos: sin el README; con el contexto subido a 8192 tokens
# (qwen2.5-proyecto) caben ~9000 caracteres de documentacion (3000 con el modelo base).
MAX_CARACTERES_DOCS_LOCAL = 9000   # con 8192 tokens de contexto (medido: 3,5 de 4 GB en la RTX 3050)
MAX_CARACTERES_DOCS_LOCAL_BASE = 3000
TURNOS_DE_MEMORIA = 6            # preguntas y respuestas anteriores que se le recuerdan

_PLANTILLA_PROMPT = """
Eres el asistente del "Sistema de Logística de Monedas Inteligentes" (proyecto del segundo corte de
Micros y Laboratorio, Ingeniería Mecatrónica, UMNG; grupo con el elemento 7: detector de elementos de
monedas y vasos). Hablas español de Colombia, claro y breve, para alguien que puede no conocer el sistema.

TU ESPECIALIDAD (responde esto con más detalle que lo demás):
1. El FILTRADO DE MONEDAS, que es la parte del grupo (elemento 7). La cinta de monedas tiene 4 estaciones:
   E1 presencia (infrarrojo: ¿hay algo en la casilla?); E2 material (capacitivo + inductivo debajo de la
   cinta: capacitivo solo = no metálico, rechazo "no_metalico"); E3 visión (cámara cenital, dos fotos:
   diámetro en mm fuera de {dmin}-{dmax} = "fuera_de_rango", circularidad < {circ} = "no_circular", agujeros o
   contornos internos = "perforado", clase "otro" o confianza < {conf} = "no_reconocida", diámetro que
   no coincide con la denominación reconocida (> {coh} mm) = "incoherente"); E4 descarga (una compuerta
   manda lo aceptado al tubo de su denominación en el almacén revólver y TODO rechazo a una sola bandeja).
   Denominaciones 50, 100, 200, 500 y 1000 de la familia nueva y la antigua; cada vaso lleva UNA sola
   denominación, en lotes (monedas por vaso); lo que no completa lote queda guardado en su tubo. El peso
   es ESTIMADO por conteo (no hay balanza ni celda de carga). Al hablar de rechazos, di la causa en
   palabras y qué estación la detecta.
2. El MOVIMIENTO DEL CARRO: sus órdenes (abajo), la odometría con encoders (se pone en cero en el muelle),
   la evasión de los 3 obstáculos con el ultrasónico, la meta y la vuelta al muelle de reversa. Para
   "dónde está / qué hace el carro" usa lo que dice el carro en ESTADO_EN_VIVO (que_hace, x, y,
   ultimos_eventos, ruta).
Lo demás (vasos, tapa y prensa, cortina, canaleta, costos, parte eléctrica, pines, simulación) también
lo respondes, con los datos de DOCUMENTACION; no lo desvíes hacia las monedas si no lo preguntan.

Recibes: (1) ESTADO_EN_VIVO, un JSON con las cifras reales de la corrida actual; (2) DOCUMENTACION, las
secciones del proyecto relacionadas con la pregunta; (3) la frase de la persona.

Responde ÚNICAMENTE con un objeto JSON, sin texto antes ni después:
{{"respuesta": "<texto para la persona>", "acciones": [ ...órdenes... ]}}

Reglas:
- Nunca inventes cifras. Toda cifra de la corrida sale de ESTADO_EN_VIVO; si no está, di que no tienes ese
  dato. Lo técnico (sensores, pines, medidas, decisiones) sale de DOCUMENTACION; si no está, dilo.
- "acciones" va vacío si la persona solo pregunta. Solo agrega órdenes si la persona pide hacer algo.
  Órdenes posibles (exactamente estas):
  {{"cmd":"carro","accion":"detener"}}
  {{"cmd":"carro","accion":"avanzar","distancia_m":0.3}}      (0.01 a 1.5 m, hacia adelante, despacio)
  {{"cmd":"carro","accion":"retroceder","distancia_m":0.1}}   (0.01 a 0.3 m: atrás no tiene sensor)
  {{"cmd":"carro","accion":"girar","grados":90}}              (-180 a 180; positivo = izquierda)
  {{"cmd":"carro","accion":"ir_a","x":1.2,"y":-0.5}}           (metros, coordenadas de la pista)
  {{"cmd":"carro","accion":"ir_meta"}}      {{"cmd":"carro","accion":"volver_muelle"}}
  {{"cmd":"carro","accion":"seguir_linea"}} (retomar el recorrido automático)
  {{"cmd":"pausar"}} {{"cmd":"reanudar"}} {{"cmd":"paro"}} {{"cmd":"iniciar"}} {{"cmd":"embalar_parciales"}}
  {{"cmd":"lote","valor":10}} (monedas por vaso)   {{"cmd":"velocidad","valor":2}} (0.25 a 8)
- Varias órdenes seguidas se ejecutan en orden, pero una orden nueva al carro reemplaza la anterior: para
  una secuencia de movimientos del carro, manda solo la primera y explica que la siguiente se pide después.
- Si preguntan por una medida que ningún sensor del proyecto mide EN VIVO (temperatura, voltaje o
  corriente de algo, humedad...), di claramente que no hay un sensor que la mida y que no tienes ese
  dato; puedes dar el valor NOMINAL de la documentación, aclarando que no es una medición.
- Una pregunta (¿...?) nunca da órdenes: "acciones" va vacío. Tampoco un pedido de información
  ("dime", "explícame", "cuéntame", "muéstrame").
- Nunca digas que el carro "se moverá", "irá" o "volverá" si "acciones" no lleva esa orden: sin orden,
  el carro NO se mueve. Escribe texto plano, sin markdown (sin `comillas invertidas` ni **negritas**).
- En las tablas de conexiones, "G25.S" es el GPIO 25 del ESP32 (fila S = señal de la placa GVS) y
  "M.STEP" es la entrada STEP del driver; el pin del ESP32 es el número que va después de la G.
- El carro no choca: antes de moverse mira el camino, y si ve algo adelante se detiene; si la persona pide
  algo que lo haría chocar o salir de la pista, explícalo. Las cm se pasan a metros. El carro anda SOLO
  por el piso: nunca puede atravesar ni entrar a la planta (cintas, filtro, almacén, canaleta) ni al
  muelle por un costado; no prometas eso ni mandes ir_a a un punto de la planta.
- En "respuesta": si es una orden, una o dos frases diciendo qué vas a hacer. Si es una pregunta,
  de 2 a 6 frases completas: la respuesta directa primero, con las cifras exactas de ESTADO_EN_VIVO
  (con sus unidades) o los datos de DOCUMENTACION, y después el porqué o el detalle útil. Nunca
  contestes una pregunta con una sola frase: agrega qué significa la cifra, de dónde sale (qué
  sensor, estación o archivo) y un dato relacionado del estado o de la documentación. No nombres
  campos internos (ESTADO_EN_VIVO, claves del JSON como valor_aceptado_pesos): habla como persona.
"""


def _umbrales_filtrado() -> dict:
    """Los umbrales del filtrado para el prompt, leidos de config/parametros.yaml (fuente unica;
    ningun numero magico en el codigo). Si la configuracion no se puede leer, los de docs/especificacion.md sec. 7."""
    try:
        from app.configuracion import cargar_parametros

        f = cargar_parametros()["filtrado"]
        valores = (f["diametro_min_mm"], f["diametro_max_mm"], f["circularidad_minima"], f["confianza_minima"],
                   f["tolerancia_coherencia_mm"])
    except Exception:  # sin configuracion: los valores de la seccion 7
        valores = (16.5, 27.5, 0.90, 0.85, 1.2)
    return {k: f"{v:g}".replace(".", ",") for k, v in zip(("dmin", "dmax", "circ", "conf", "coh"), valores)}


PROMPT_SISTEMA = _PLANTILLA_PROMPT.format(**_umbrales_filtrado())


def cliente_deepseek():
    """Cliente de la API (formato de OpenAI) o None si no hay clave. La clave
    va en la variable de entorno DEEPSEEK_API_KEY o en un archivo .env en la
    raiz del proyecto (ignorado por git), como en el tema 4."""
    try:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
    except ImportError:
        pass
    clave = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not clave:
        return None
    from openai import OpenAI

    return OpenAI(api_key=clave, base_url=URL_DEEPSEEK, timeout=40, max_retries=1)


def cliente_local():
    """Cliente de Ollama (si esta corriendo y tiene el modelo), o None."""
    import urllib.request

    try:
        with urllib.request.urlopen(URL_LOCAL + "/api/tags", timeout=0.8) as r:
            modelos = [m["name"] for m in json.loads(r.read()).get("models", [])]
    except (OSError, ValueError):
        return None
    global MODELO_LOCAL
    nombres = {m.split(":")[0] if m.endswith(":latest") else m for m in modelos}
    if MODELO_LOCAL not in nombres:
        if MODELO_LOCAL_BASE not in nombres:
            return None
        MODELO_LOCAL = MODELO_LOCAL_BASE           # sin el de contexto largo: el de base
    from openai import OpenAI

    return OpenAI(api_key="ollama", base_url=URL_LOCAL + "/v1", timeout=90, max_retries=0)


def preguntar_deepseek(cliente, pregunta: str, estado: dict, historial: list[dict]) -> dict:
    """Una pregunta a DeepSeek. Devuelve {"respuesta", "acciones", "documentos"}."""
    return preguntar_llm(cliente, MODELO, pregunta, estado, historial)


def preguntar_llm(cliente, modelo: str, pregunta: str, estado: dict, historial: list[dict],
                  limite_docs: int = MAX_CARACTERES_DOCS, con_readme: bool = True, dato_verificado: str = "") -> dict:
    """Una pregunta a un modelo con API de OpenAI (DeepSeek u Ollama). `dato_verificado`: la
    respuesta exacta que ya calcularon las reglas (el modelo la amplia, no la recalcula)."""
    docs = buscar(pregunta, limite_docs)
    readme = ((RAIZ / "README.md").read_text(encoding="utf-8")
              if con_readme and (RAIZ / "README.md").exists() else "")
    documentacion = readme + "\n\n" + "\n\n".join(f"[{s.archivo} · {s.titulo}]\n{s.texto}" for s in docs
                                                  if s.archivo != "README.md")
    mensajes = [{"role": "system", "content": PROMPT_SISTEMA}]
    for m in historial[-2 * TURNOS_DE_MEMORIA:]:
        mensajes.append({"role": "user" if m["rol"] == "usuario" else "assistant", "content": m["texto"]})
    # Documentacion primero y el estado en vivo pegado a la pregunta: un modelo chico se
    # "pierde" si las cifras quedan al principio de un texto largo (se vio en las pruebas).
    mensajes.append({"role": "user", "content": (
        "DOCUMENTACION:\n" + documentacion
        + "\n\nESTADO_EN_VIVO (cifras reales de la corrida):\n" + json.dumps(estado, ensure_ascii=False)
        + ("\n\nDATO VERIFICADO (cifras exactas, úsalas tal cual y amplía la explicación):\n" + dato_verificado
           if dato_verificado else "")
        + "\n\nFRASE DE LA PERSONA:\n" + pregunta)})
    r = cliente.chat.completions.create(model=modelo, messages=mensajes, response_format={"type": "json_object"},
                                        temperature=0.2, max_tokens=900)
    datos = json.loads(r.choices[0].message.content or "{}")
    if not isinstance(datos, dict):
        datos = {}
    texto = datos.get("respuesta")
    if not isinstance(texto, str) or not texto.strip():
        # Un modelo chico a veces cambia el nombre de la clave: el primer texto que traiga.
        texto = next((v for v in datos.values() if isinstance(v, str) and v.strip()), "")
    return {"respuesta": texto.strip() or "(sin respuesta)",
            "acciones": datos.get("acciones") or [], "documentos": [f"{s.archivo} · {s.titulo}" for s in docs[:6]]}


def precargar_local() -> None:
    """Carga el modelo local en la GPU en segundo plano (la primera respuesta
    tarda ~1 min si el modelo no esta cargado). No hace nada si Ollama no esta."""
    import threading
    import urllib.request

    def _cargar():
        try:
            datos = json.dumps({"model": MODELO_LOCAL, "prompt": "", "keep_alive": "30m"}).encode()
            urllib.request.urlopen(urllib.request.Request(URL_LOCAL + "/api/generate", data=datos), timeout=120).read()
        except OSError:
            pass

    threading.Thread(target=_cargar, daemon=True).start()


def preparar_local() -> str:
    """Crea en Ollama `qwen2.5-proyecto` (qwen2.5:3b con 8192 tokens de contexto). Una vez."""
    import subprocess
    import tempfile

    import shutil

    # Ollama se instalo en D: (el disco del sistema no se llena; usuario, 2026-09-28); antes vivia
    # en la carpeta del usuario. Se prueba el PATH, D: y la ruta de instalacion por defecto.
    candidatos = [shutil.which("ollama") or "", r"D:\Program Files\Ollama\ollama.exe",
                  os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")]
    ollama = next((c for c in candidatos if c and Path(c).exists()), "ollama")
    with tempfile.NamedTemporaryFile("w", suffix=".Modelfile", delete=False, encoding="utf-8") as f:
        f.write(f"FROM {MODELO_LOCAL_BASE}\nPARAMETER num_ctx 8192\nPARAMETER temperature 0.2\n")
    r = subprocess.run([ollama, "create", "qwen2.5-proyecto", "-f", f.name], capture_output=True, text=True)
    return r.stdout + r.stderr
