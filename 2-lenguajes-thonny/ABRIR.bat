@echo off
rem ---------------------------------------------------------------------------------
rem  Abre la app de ESTA practica (doble clic aqui).
rem
rem  Usa el lanzador probar.py de la raiz del repo: levanta un servidor solo en este PC
rem  (127.0.0.1) y abre la app en una ventana tipo programa. Si el lanzador ya estaba
rem  abierto (por PROBAR.bat u otro ABRIR.bat), lo reutiliza. Solo hace falta Python 3.9
rem  o mas nuevo; lo que la practica necesite (PyBullet, OpenCV...) lo instala la propia
rem  app la primera vez, mostrando el progreso.
rem ---------------------------------------------------------------------------------
setlocal
chcp 65001 >nul
rem El nombre de esta carpeta es el nombre de la practica.
for %%I in ("%~dp0.") do set "PRACTICA=%%~nxI"
title Sensores-Teoria - %PRACTICA%

if not exist "%~dp0..\probar.py" goto sin_lanzador

rem 1) "py" es el lanzador que instala el instalador oficial de python.org: el mas fiable.
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul && set "PY=py -3"

rem 2) Si no, "python" del PATH (si Python no esta instalado puede ser un acceso directo a
rem    la Microsoft Store que no hace nada: por eso se comprueba la version).
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY goto sin_python

echo Abriendo la app de la practica %PRACTICA%...
%PY% "%~dp0..\probar.py" --practica "%PRACTICA%"
rem Si algo fallo, la ventana queda abierta para leer el mensaje.
if errorlevel 1 pause
exit /b

:sin_python
echo.
echo  No encontre Python 3.9 o mas nuevo en este equipo, y la app lo necesita.
echo.
echo  Para instalarlo (una sola vez):
echo    1. Entra a https://www.python.org/downloads/ y baja Python 3.13
echo       ("Windows installer (64-bit)").
echo    2. En el instalador marca "Add python.exe to PATH" y deja marcado el "py launcher".
echo    3. Cuando termine, vuelve a hacer doble clic en este ABRIR.bat.
echo.
pause
exit /b 1

:sin_lanzador
echo.
echo  No encuentro probar.py en la carpeta de arriba (%~dp0..).
echo  Este ABRIR.bat tiene que estar dentro de la carpeta de la practica, en el repo completo
echo  Sensores-Teoria (descargalo entero desde GitHub: boton "Code" y "Download ZIP").
echo.
pause
exit /b 1
