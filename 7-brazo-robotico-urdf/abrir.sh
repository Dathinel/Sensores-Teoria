#!/usr/bin/env sh
# Abre la app de esta práctica en Linux/Mac: `sh abrir.sh` (en Windows: doble clic en ABRIR.bat).
# Usa el lanzador probar.py de la raíz del repo (solo biblioteca estándar, Python >= 3.9).
cd "$(dirname "$0")" || exit 1
PRACTICA="$(basename "$(pwd)")"
for py in python3 python; do
    if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
        exec "$py" ../probar.py --practica "$PRACTICA" "$@"
    fi
done
echo "No encontré Python 3.9 o más nuevo."
echo "Instálalo (python.org, 'sudo apt install python3 python3-venv' o 'brew install python@3.13') y vuelve a correr: sh abrir.sh"
exit 1
