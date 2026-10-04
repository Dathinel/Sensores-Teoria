# Imagen del gemelo digital del enjambre ACO (PyBullet sin pantalla).
#
# Construir y correr (desde esta carpeta):
#   docker compose up --build                 -> gemelo en modo hardware (escucha UDP 4211)
#   docker compose run --rm simulacion        -> demo sin hardware (telemetria simulada)
# Los videos, imagenes y json quedan en ./resultados del computador.

# Python 3.11 "slim" (Debian sin extras). Se fija 3.11 porque pybullet 3.2.7 publica una rueda
# (wheel) ya compilada para cp311 manylinux x86_64: pip la instala en segundos, sin compilador.
# --platform=linux/amd64: pybullet NO trae rueda para ARM (aarch64). En un Mac con Apple Silicon
# (M1/M2/M3) la imagen saldria linux/arm64 y pip intentaria compilar pybullet (y fallaria por falta
# de compilador); asi Docker usa la imagen x86_64 y la corre emulada (mas lento, pero funciona).
FROM --platform=linux/amd64 python:3.11-slim

# fonts-dejavu-core trae DejaVuSans, la fuente con que el gemelo escribe el panel del video.
# --no-install-recommends evita paquetes de sobra y el rm borra el indice de apt (imagen mas chica).
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Librerias de Python con versiones fijas, para que la imagen salga igual hoy y dentro de un ano:
#   pybullet       -> la escena 3D y el renderizador por software (ER_TINY_RENDERER, sin GPU)
#   numpy          -> matrices de la camara y manejo de las imagenes
#   pillow         -> compone cada cuadro (vista 3D + panel de texto)
#   imageio        -> escribe el video cuadro por cuadro
#   imageio-ffmpeg -> trae su propio binario de ffmpeg (H.264), no hace falta instalarlo por apt
# --no-cache-dir: no guarda la cache de pip dentro de la imagen.
RUN pip install --no-cache-dir \
    pybullet==3.2.7 \
    numpy==2.2.6 \
    pillow==11.3.0 \
    imageio==2.37.0 \
    imageio-ffmpeg==0.6.0

# Carpeta de trabajo dentro del contenedor: aqui van el codigo y (montada) la de resultados.
WORKDIR /app

# Solo lo que necesita el gemelo: la logica ACO, el protocolo UDP, el propio gemelo y los
# laberintos. El firmware, el entorno virtual de Windows y los resultados quedan fuera
# (ver .dockerignore). Se copian al final para que cambiar el codigo no reinstale las librerias
# (Docker reutiliza las capas anteriores que no cambiaron).
COPY aco.py protocolo.py gemelo_digital.py maze.json ./
COPY laberintos/ ./laberintos/

# PYTHONUNBUFFERED=1: los print salen enseguida en "docker compose logs" (sin esperar a llenar
# un buffer), importante para ver el diagnostico de "no llega nada por UDP".
# RESULTADOS: carpeta donde el gemelo escribe sus salidas (la monta docker-compose.yml).
ENV PYTHONUNBUFFERED=1 \
    RESULTADOS=/app/resultados

# Documenta que el contenedor escucha la telemetria de los ESP32 en UDP 4211. EXPOSE no abre
# nada por si solo: el puerto se publica con "ports" en docker-compose.yml (o -p 4211:4211/udp).
EXPOSE 4211/udp

# El contenedor ES el gemelo: lo que se ponga despues de la imagen en "docker run" (o en
# "command" del compose) son argumentos de gemelo_digital.py.
ENTRYPOINT ["python", "gemelo_digital.py"]

# Argumentos por defecto: modo hardware (se reemplazan, p. ej., con --modo sin-hardware).
CMD ["--modo", "hardware"]
