@echo off
rem Abre el visor 3D al instante (visor-portable.html: la demo grabada, sin servidor ni
rem internet) y arranca la simulacion por detras. Cuando la simulacion responde, la misma
rem pestana pasa sola al visor en vivo: no hay que recargar ni abrir nada mas. El dashboard
rem de Streamlit se abre solo en otra pestana apenas responde.
rem Puertos: el visor en vivo usa el 8765 (o PLANTA_PUERTO_VISOR); si lo tiene otro programa,
rem usa el siguiente libre y lo dice aqui (app/puertos.py). Igual el dashboard (8501).
cd /d "%~dp0"
if not exist entorno\Scripts\python.exe goto sin_instalar
entorno\Scripts\python -m app.portable --silencioso
entorno\Scripts\python -m app.puertos
set CAMBIA=%errorlevel%
start "" "%~dp0visor-portable.html"
start "Planta de monedas (simulacion)" /min cmd /c "entorno\Scripts\python -m app.lanzar --auto prueba_completa --abrir-dashboard"
if "%CAMBIA%"=="2" (
  echo.
  echo No hay que hacer nada: el visor portable encuentra solo el puerto nuevo y el dashboard se
  echo abre en el puerto correcto. Esta ventana se cierra en 20 s.
  timeout /t 20 >nul
)
exit /b 0

:sin_instalar
echo.
echo  ================================================================
echo   El proyecto NO esta instalado en este PC (no existe entorno\).
echo.
echo   Se abre la DEMO GRABADA del visor 3D (no es en vivo: no corre
echo   la simulacion, ni el dashboard, ni el asistente).
echo.
echo   Para el modo en vivo: doble clic en instalar.bat (una vez, con
echo   internet; la opcion 1, minima, basta para verlo) y despues
echo   otra vez visor.bat.
echo  ================================================================
echo.
start "" "%~dp0visor-portable.html"
pause
