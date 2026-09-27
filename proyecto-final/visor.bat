@echo off
rem Abre el visor 3D al instante (visor-portable.html: la demo grabada, sin servidor ni
rem internet) y arranca la simulacion por detras. Cuando la simulacion responde, la misma
rem pestana pasa sola al visor en vivo: no hay que recargar ni abrir nada mas.
cd /d "%~dp0"
if exist entorno\Scripts\python.exe entorno\Scripts\python -m app.portable --silencioso
start "" "%~dp0visor-portable.html"
if exist entorno\Scripts\python.exe start "Planta de monedas (simulacion)" /min cmd /c "entorno\Scripts\python -m app.lanzar --auto prueba_completa"
