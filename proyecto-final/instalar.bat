@echo off
rem Deja el proyecto listo en un PC nuevo (una sola vez, CON internet). Dos opciones:
rem   1) MINIMA (requirements-minimo.txt): visor 3D en vivo, dashboard, las 4 escenas de PyBullet,
rem      el asistente por escrito y las pruebas. Unos 0,7 GB.
rem   2) COMPLETA (requirements-lock.txt, las versiones EXACTAS con las que se probo): lo anterior
rem      mas la voz sin internet (Whisper), entrenar la vision (torch, keras) y subir el firmware;
rem      ademas arma el firmware (descarga el driver del VL53L0X), prepara el modelo local si esta
rem      Ollama y corre el chequeo previo a la sustentacion. Unos 1,8 GB.
rem Sin preguntar: `instalar.bat minima` o `instalar.bat completa`.
rem PyBullet 3.2.7 no trae instalador listo para Windows: pip lo COMPILA (unos 10 minutos) y para
rem eso hacen falta las Microsoft C++ Build Tools ("Desarrollo para el escritorio con C++").
rem Despues: doble clic en visor.bat.
cd /d "%~dp0"
setlocal
set OPCION=%~1
if /i "%OPCION%"=="minima" set OPCION=1
if /i "%OPCION%"=="minimo" set OPCION=1
if /i "%OPCION%"=="completa" set OPCION=2
if /i "%OPCION%"=="completo" set OPCION=2
if not "%OPCION%"=="1" if not "%OPCION%"=="2" (
  echo Instalar el proyecto final ^(una sola vez, con internet^):
  echo.
  echo   1^) MINIMA   - para VERLO: visor 3D en vivo, dashboard, escenas de PyBullet, asistente
  echo                escrito y pruebas. ~0,7 GB; 5-15 min ^(+ ~10 min si compila PyBullet^).
  echo   2^) COMPLETA - lo anterior + voz sin internet ^(Whisper^), vision ^(torch^), firmware de los
  echo                ESP32 y modelo local de Ollama. ~1,8 GB; 20-40 min.
  echo.
  choice /c 12 /n /m "Elija 1 o 2: "
  if errorlevel 2 (set OPCION=2) else (set OPCION=1)
)
where py >nul 2>nul && (set PY=py -3.14) || (set PY=python)
if not exist entorno\Scripts\python.exe (
  echo Creando el entorno virtual...
  %PY% -m venv entorno || (echo No se pudo crear el entorno: instalar Python 3.14 desde python.org & pause & exit /b 1)
  echo *> entorno\.gitignore
)
entorno\Scripts\python -m pip install --upgrade pip >nul
if "%OPCION%"=="1" (
  echo Instalando lo minimo ^(varios minutos la primera vez; PyBullet se compila^)...
  entorno\Scripts\python -m pip install -r requirements-minimo.txt || (echo Fallo la instalacion: si el error habla de Visual Studio o de un compilador, faltan las Microsoft C++ Build Tools. Ver README, "Instalar en otro PC". & pause & exit /b 1)
  echo.
  echo Listo ^(instalacion minima^). Doble clic en visor.bat para verlo en vivo.
  echo Para la voz, la vision o el firmware: instalar.bat completa.
  pause
  exit /b 0
)
echo Instalando librerias (varios minutos la primera vez)...
entorno\Scripts\python -m pip install -r requirements-lock.txt || (echo Fallo la instalacion: si el error habla de Visual Studio o de un compilador, faltan las Microsoft C++ Build Tools. Ver README, "Instalar en otro PC". & pause & exit /b 1)
echo Armando el firmware una vez (descarga el driver del VL53L0X)...
entorno\Scripts\python -m firmware.preparar
where ollama >nul 2>nul && (
  echo Preparando el modelo local del asistente...
  ollama pull qwen2.5:3b
  entorno\Scripts\python -m app.asistente --preparar-local
) || echo Ollama no esta instalado: el asistente usara las reglas sin internet. Ver README, "Asistente sin internet".
echo Descargando Whisper para la voz sin internet...
entorno\Scripts\python -m app.asistente --preparar-voz
echo.
entorno\Scripts\python -m app.chequeo
pause
