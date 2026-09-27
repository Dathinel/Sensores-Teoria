@echo off
rem Doble clic: abre el visor 3D de la linea simulada. Si la simulacion ya
rem esta corriendo, solo abre el visor; si no, la arranca en una ventana
rem minimizada (cerrarla detiene la simulacion). El dashboard de Streamlit
rem queda en http://localhost:8501
cd /d "%~dp0"
start "Planta de monedas (simulacion)" /min cmd /c "entorno\Scripts\python -m app.lanzar --auto prueba_completa --abrir"
