"""Graba las 4 escenas en video, SIN abrir ninguna ventana.

    python -m sim.ver.grabar                       las 4
    python -m sim.ver.grabar filtro_monedas        solo esa (o varias, separadas por espacio)

Cada escena corre en p.DIRECT con el MISMO codigo que en la ventana; cada
`acelerar / fps` segundos simulados se toma una foto con `p.getCameraImage`
(ER_TINY_RENDERER, render por software) desde la camara de la escena y se le
dibuja el rotulo encima con PIL, con tildes (los textos de depuracion de la
ventana no salen en getCameraImage). Resultado, en docs/videos/:

- `<escena>.mp4`: el video completo en H.264 (se ve en GitHub y en cualquier
  navegador), a 10 cuadros por segundo;
- `<escena>.gif`: la misma corrida comprimida a ~14 s, 640 px de ancho y pocos
  colores (menos de 5 MB), para embeberla en el README.
"""

from __future__ import annotations

import subprocess
import sys
import time

from sim.ver import carro_pista, embalaje_vasos, filtro_monedas, todo_junto
from sim.ver.comun import CARPETA_VIDEOS, Terminar, Vista, buscar_ffmpeg

# nombre -> (modulo, segundos simulados por segundo de video)
ESCENAS = {
    "filtro_monedas": (filtro_monedas, 1.0),     # ~45 s simulados: a tiempo real
    "embalaje_vasos": (embalaje_vasos, 2.0),     # ~85 s
    "carro_pista": (carro_pista, 4.0),           # ~160 s (ida y vuelta)
    "todo_junto": (todo_junto, 4.0),             # ~225 s
}
FPS = 10
GIF_SEGUNDOS = 14
GIF_MAX_MB = 5.0
# 2026-09-29: 640 px (antes 480: con la letra reducida, los rotulos no se leian).
GIF_ANCHO = 640


def hacer_gif(mp4, gif, duracion_video: float) -> float:
    """GIF liviano de toda la corrida: acelerado para que dure ~14 s, 640 px
    de ancho, paleta propia. Si pasa de 5 MB, se repite con menos cuadros y
    colores. Devuelve el tamano en MB."""
    ffmpeg = buscar_ffmpeg()
    if ffmpeg is None:
        print("  (sin ffmpeg: no se hace el GIF)")
        return 0.0
    factor = max(1.0, duracion_video / GIF_SEGUNDOS)
    for fps, colores in ((8, 96), (6, 64), (5, 48), (4, 32)):
        filtro = (f"setpts=PTS/{factor:.3f},fps={fps},scale={GIF_ANCHO}:-1:flags=lanczos,split[a][b];"
                  f"[a]palettegen=max_colors={colores}:stats_mode=diff[p];"
                  f"[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle")
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(mp4), "-vf", filtro, "-loop", "0", str(gif)],
                       check=True)
        mb = gif.stat().st_size / 1e6
        if mb <= GIF_MAX_MB:
            return mb
    return mb


def grabar(nombre: str) -> dict:
    modulo, acelerar = ESCENAS[nombre]
    mp4 = CARPETA_VIDEOS / f"{nombre}.mp4"
    vista = Vista(nombre, ventana=False, grabar=mp4, fps=FPS, acelerar=acelerar)
    vista.titulo = modulo.TITULO
    t0 = time.perf_counter()
    try:
        modulo.correr(vista)
    except Terminar:
        pass
    info = vista.cerrar_video()
    gif = CARPETA_VIDEOS / f"{nombre}.gif"
    mb_gif = hacer_gif(mp4, gif, info["segundos_video"])
    info.update(gif=gif, mb_mp4=mp4.stat().st_size / 1e6, mb_gif=mb_gif, simulados=vista.t,
                reloj=time.perf_counter() - t0, fin=vista.mensaje_fin)
    print(f"{nombre}: {vista.t:.0f} s simulados -> {mp4.name} {info['segundos_video']:.0f} s "
          f"({info['mb_mp4']:.1f} MB), {gif.name} ({mb_gif:.1f} MB) en {info['reloj']:.0f} s de reloj. {vista.mensaje_fin}")
    return info


def main(argv=None) -> None:
    nombres = (argv if argv is not None else sys.argv[1:]) or list(ESCENAS)
    CARPETA_VIDEOS.mkdir(parents=True, exist_ok=True)
    for n in nombres:
        grabar(n)


if __name__ == "__main__":
    main()
