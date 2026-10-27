# `app/asistente/`: el asistente del proyecto

Una frase (escrita o dicha) pasa por DeepSeek → el modelo local (Ollama) → las reglas sin internet,
y lo que vuelve se valida contra una lista blanca antes de llegar a la línea. Qué debe hacer y qué
no: [§14 de la especificación](../../docs/especificacion.md#14-chatbot). Cómo es el modelo local
por dentro y por qué se eligió: [`docs/modelo-local.md`](../../docs/modelo-local.md).

Antes era un solo archivo (`app/asistente.py`); el docstring de [`__init__.py`](__init__.py) explica
la idea completa (el JSON de respuesta, el estado en vivo, la búsqueda en la documentación).

## Módulos

| Módulo | Qué tiene |
|---|---|
| `entrada.py` | `atender`, el punto de entrada: elige proveedor, valida órdenes y guarda la conversación. |
| `conocimiento.py` | Los documentos (`DOCUMENTOS`: README, `docs/*.md`, config) partidos en secciones, y la búsqueda. |
| `estado.py` | El estado en vivo de la corrida, sacado de SQLite. |
| `mensajes.py` | La conversación guardada en la base (la ven el dashboard y el visor). |
| `ordenes.py` | La lista blanca de órdenes a la línea y al carro. |
| `llm.py` | DeepSeek y el modelo local: prompt, clientes, `preparar_local`. |
| `reglas.py` | El intérprete local de frases (expresiones regulares, sin internet). |
| `respuestas.py` | Las respuestas por reglas, con las cifras de la corrida, costos, peso y consumo. |
| `audio.py` | Internet y voz: oír y hablar, con y sin internet (Whisper, voz de Windows). |
| `__main__.py` | Lo que corre aparte (abajo). |

`__init__.py` reexporta toda la API (`from app import asistente; asistente.atender(...)`). Lo usan la
pestaña Asistente del dashboard, `app/servidor.py` (`/api/internet`), `app/charla.py`,
`app/evaluar_asistente.py` y `app/chequeo.py`. No importa Streamlit.

## Comandos

```
python -m app.asistente --preparar-local   # crea qwen2.5-proyecto en Ollama (una vez)
python -m app.asistente --preparar-voz     # descarga Whisper y prueba la voz de Windows
python -m app.asistente --decir RUTA       # escribe en RUTA (.wav) el texto de la entrada estándar
```

`instalar.bat` (opción completa) corre los dos primeros (`--preparar-local` solo si encuentra
Ollama); `--decir` lo lanza `audio.voz_local` en un
proceso aparte. Para probar el asistente sin nada instalado: `python -m app.charla`; con preguntas
reales: `python -m app.evaluar_asistente`.

## Reglas para las pruebas (y para quien llame desde afuera)

- **Un monkeypatch reemplaza la función en SU módulo**, no en el paquete:
  `monkeypatch.setattr(asistente.llm, "cliente_local", ...)`, `asistente.audio.hay_internet`,
  `asistente.llm.preguntar_deepseek`, etc. `atender` las busca ahí; un parche sobre
  `asistente.hay_internet` no alcanza a nadie. Por lo mismo, el código de afuera que una prueba
  necesite parchear llama por el submódulo (`asistente.llm.cliente_local()`,
  `asistente.audio.hay_internet()`), como hacen el dashboard, el servidor y el chequeo.
- **`asistente.MODELO_LOCAL` se lee siempre de `llm`** (por un `__getattr__` del paquete):
  `cliente_local` lo cambia en marcha a `qwen2.5:3b` si falta el modelo de contexto largo. Hay que
  leerlo en el momento de usarlo; un `from app.asistente import MODELO_LOCAL` arriba de un módulo se
  queda con el valor de ese instante.
- Las respuestas por reglas no inventan cifras: salen del estado inyectado o dicen que no tienen el
  dato (§14). Pruebas: `tests/app/test_asistente.py`, `test_asistente_planta.py` y `test_voz.py`.
