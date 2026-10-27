"""Internet y voz (usuario, 2026-09-27: la voz tiene que funcionar SIN internet).

Con internet se usa lo del tema 4: reconocimiento de Google en es-CO y respuesta con gTTS.
Sin internet (o si Google falla), todo en el mismo portatil:
- Oir: Whisper (faster-whisper, modelo "small", ~480 MB). Se descarga UNA vez en la carpeta del
  usuario (~/.cache/huggingface), fuera del proyecto, con `python -m app.asistente --preparar-voz`.
  Probado con frases del proyecto: "base" oia "abanza" y "muye"; "small" las escribe bien, con
  tildes, y tarda ~0,1 s por frase ya cargado (la primera vez, ~10 s en cargarse).
- Hablar: las voces de Windows (SAPI, p. ej. "Microsoft Helena", es-ES) con pyttsx3. Corre en un
  proceso aparte: pyttsx3 se cuelga si se llama dos veces en el mismo proceso, y Streamlit atiende
  cada interaccion en otro hilo (la voz de Windows es COM y quiere su propio hilo inicializado).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from app.rutas import RAIZ

MODELO_VOZ = os.environ.get("ASISTENTE_MODELO_VOZ", "small")
_internet = {"t": 0.0, "hay": False}
_whisper = {}


def hay_internet(cada_s: float = 15.0) -> bool:
    """True si se alcanza internet (se revisa como mucho cada `cada_s` segundos).
    Abre una conexion TCP (sin mandar nada) a DeepSeek o, si no, a Google: sin red
    falla en milisegundos (no hay DNS) y con una red sin salida, al 1,5 s."""
    import socket
    import time

    ahora = time.monotonic()
    if _internet["t"] and ahora - _internet["t"] < cada_s:
        return _internet["hay"]
    hay = False
    for host in ("api.deepseek.com", "www.google.com"):
        try:
            socket.create_connection((host, 443), timeout=1.5).close()
            hay = True
            break
        except OSError:
            continue
    _internet.update(t=ahora, hay=hay)
    return hay


def _whisper_modelo():
    if "modelo" not in _whisper:
        from faster_whisper import WhisperModel

        # CPU e int8: no compite con el modelo de lenguaje por los 4 GB de la GPU.
        _whisper["modelo"] = WhisperModel(MODELO_VOZ, device="cpu", compute_type="int8")
    return _whisper["modelo"]


def transcribir_local(audio_wav: bytes) -> str:
    """Audio -> texto con Whisper en el portatil (sin internet)."""
    import io

    segmentos, _ = _whisper_modelo().transcribe(
        io.BytesIO(audio_wav), language="es", beam_size=1, vad_filter=True,
        # Palabras del proyecto que una frase suelta no le deja adivinar.
        initial_prompt="Carro, muelle, meta, línea, monedas, vasos, canaleta, centímetros, grados.")
    return " ".join(s.text.strip() for s in segmentos).strip()


def transcribir(audio_wav: bytes) -> tuple[str | None, str]:
    """Audio del microfono (WAV, lo que da st.audio_input) -> texto.
    Devuelve (texto, quien lo reconocio) o (None, motivo si fallo).
    Con internet, Google (como el tema 4); sin internet o si falla, Whisper local."""
    import io

    motivos = []
    if hay_internet():
        try:
            import speech_recognition as sr

            reconocedor = sr.Recognizer()
            reconocedor.operation_timeout = 8
            with sr.AudioFile(io.BytesIO(audio_wav)) as fuente:
                audio = reconocedor.record(fuente)
            return reconocedor.recognize_google(audio, language="es-CO"), "Google"
        except ImportError:
            motivos.append("falta SpeechRecognition")
        except Exception as error:  # sin respuesta de Google, audio que no entendio...
            motivos.append(f"Google: {type(error).__name__}")
    try:
        texto = transcribir_local(audio_wav)
    except ImportError:
        return None, "Sin internet y sin el reconocimiento local (pip install faster-whisper)."
    except Exception as error:
        return None, f"No se pudo transcribir ({'; '.join(motivos + [str(error)[:80]])})."
    if not texto:
        return None, "No se entendió el audio."
    return texto, "Whisper local (sin internet)"


def _limpiar_para_voz(texto: str) -> str:
    return re.sub(r"<[^>]+>|[*_`#]", "", texto)[:600]


def voz_local(texto: str) -> bytes | None:
    """Texto -> WAV con una voz de Windows en espanol, en un proceso aparte."""
    import subprocess
    import sys
    import tempfile

    ruta = Path(tempfile.gettempdir()) / f"asistente_voz_{os.getpid()}.wav"
    try:
        ruta.unlink(missing_ok=True)
        subprocess.run([sys.executable, "-m", "app.asistente", "--decir", str(ruta)], cwd=RAIZ,
                       input=_limpiar_para_voz(texto), text=True, encoding="utf-8", timeout=60,
                       capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return ruta.read_bytes() if ruta.exists() and ruta.stat().st_size > 1000 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _decir_a_archivo(ruta: str, texto: str) -> None:
    """Lo que corre el proceso aparte de voz_local."""
    import pyttsx3

    motor = pyttsx3.init()
    voces = motor.getProperty("voices")
    espanol = [v for v in voces if "spanish" in v.name.lower() or "es-" in v.id.lower() or "es_" in v.id.lower()
               or any(n in v.name.lower() for n in ("helena", "sabina", "laura", "pablo", "raul"))]
    if espanol:
        motor.setProperty("voice", espanol[0].id)
    motor.setProperty("rate", 175)
    motor.save_to_file(texto, ruta)
    motor.runAndWait()


def voz(texto: str) -> tuple[bytes, str] | None:
    """Texto -> (audio, formato "mp3"|"wav"). Con internet gTTS (acento colombiano);
    sin internet, la voz de Windows. None si no se pudo."""
    import io

    if hay_internet():
        try:
            from gtts import gTTS

            buf = io.BytesIO()
            gTTS(_limpiar_para_voz(texto), lang="es", tld="com.co", timeout=8).write_to_fp(buf)
            return buf.getvalue(), "mp3"
        except Exception:  # Google no respondio: se sigue con la voz local
            pass
    wav = voz_local(texto)
    return (wav, "wav") if wav else None


def preparar_voz() -> str:
    """Descarga el modelo de Whisper (una vez, necesita internet) y prueba la voz de Windows."""
    _whisper_modelo()
    wav = voz_local("Listo. El asistente ya puede oír y hablar sin internet.")
    return (f"Whisper '{MODELO_VOZ}' listo. Voz de Windows: "
            + ("lista." if wav else "no se pudo generar (¿pyttsx3 instalado?)."))
