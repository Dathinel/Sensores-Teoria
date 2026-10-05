#!/usr/bin/env sh
# Lanzador de las prácticas de Sensores-Teoria en Linux/Mac: `sh probar.sh`.
# Busca un Python >= 3.9 y corre probar.py (solo biblioteca estándar), que abre el hub en
# el navegador. Los paquetes de cada práctica los instala el propio lanzador la primera vez.
cd "$(dirname "$0")" || exit 1
for py in python3 python; do
    if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
        exec "$py" probar.py "$@"
    fi
done
echo "No encontré Python 3.9 o más nuevo."
echo "Instálalo (python.org, 'sudo apt install python3 python3-venv' o 'brew install python@3.13') y vuelve a correr: sh probar.sh"
exit 1
