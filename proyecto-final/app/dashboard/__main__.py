"""`python -m app.dashboard [--server.port N ...]`: abre solo el dashboard
(sin supervisor; para todo junto, `python -m app.lanzar`)."""

import subprocess
import sys
from pathlib import Path

ENTRADA = Path(__file__).resolve().parent / "inicio.py"

if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(ENTRADA), *sys.argv[1:]]))
