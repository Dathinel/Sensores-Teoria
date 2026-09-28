@echo off
rem Deja el proyecto listo en un PC nuevo (una sola vez, CON internet):
rem   1) crea el entorno virtual `entorno` y le instala las versiones EXACTAS con las que se probo
rem      (requirements-lock.txt);
rem   2) arma el firmware una vez (descarga el driver del VL53L0X: despues se arma sin internet);
rem   3) si esta Ollama, crea el modelo local con mas contexto; descarga Whisper (voz sin internet);
rem   4) corre el chequeo previo a la sustentacion.
rem Despues: doble clic en visor.bat.
cd /d "%~dp0"
setlocal
where py >nul 2>nul && (set PY=py -3.14) || (set PY=python)
if not exist entorno\Scripts\python.exe (
  echo Creando el entorno virtual...
  %PY% -m venv entorno || (echo No se pudo crear el entorno: instalar Python 3.14 desde python.org & pause & exit /b 1)
  echo *> entorno\.gitignore
)
echo Instalando librerias (varios minutos la primera vez)...
entorno\Scripts\python -m pip install --upgrade pip >nul
entorno\Scripts\python -m pip install -r requirements-lock.txt || (echo Fallo la instalacion & pause & exit /b 1)
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
