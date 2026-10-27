"""`python -m app.asistente ...`: lo que corre aparte (lo llaman instalar.bat y audio.voz_local).

    python -m app.asistente --preparar-local   # crea qwen2.5-proyecto en Ollama (una vez)
    python -m app.asistente --preparar-voz     # descarga Whisper y prueba la voz de Windows
    python -m app.asistente --decir RUTA       # dice en RUTA (.wav) el texto de la entrada estandar
"""

from .audio import _decir_a_archivo, preparar_voz
from .llm import preparar_local

if __name__ == "__main__":
    import sys

    if "--preparar-local" in sys.argv:
        print(preparar_local())
    if "--preparar-voz" in sys.argv:
        print(preparar_voz())
    if "--decir" in sys.argv:
        _decir_a_archivo(sys.argv[sys.argv.index("--decir") + 1], sys.stdin.read())
