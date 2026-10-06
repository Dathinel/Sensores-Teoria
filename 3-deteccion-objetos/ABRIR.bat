@echo off
rem ---------------------------------------------------------------------------------
rem  Abre la app de ESTA practica (doble clic aqui).
rem
rem  Usa el lanzador de la raiz del repo (_lanzador\lanzador.py): levanta un servidor solo
rem  en este PC (127.0.0.1) y abre la app en una ventana tipo programa, maximizada. Si el
rem  lanzador ya estaba abierto (por el ABRIR.bat de otra practica), lo reutiliza. Solo hace
rem  falta Python 3.9 o mas nuevo; lo que la practica necesite (PyBullet, OpenCV...) lo
rem  instala la propia app la primera vez, mostrando el progreso.
rem ---------------------------------------------------------------------------------
setlocal
chcp 65001 >nul
rem El nombre de esta carpeta es el nombre de la practica.
for %%I in ("%~dp0.") do set "PRACTICA=%%~nxI"
set "LANZADOR=%~dp0..\_lanzador\lanzador.py"
title Sensores-Teoria - %PRACTICA%

if not exist "%LANZADOR%" goto sin_lanzador

rem 1) "py" es el lanzador que instala el instalador oficial de python.org: el mas fiable.
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul && set "PY=py -3"

rem 2) Si no, "python" del PATH (si Python no esta instalado puede ser un acceso directo a
rem    la Microsoft Store que no hace nada: por eso se comprueba la version).
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY goto sin_python

echo.
echo  Abriendo la app de %PRACTICA%... (la primera vez tarda unos segundos)
echo  Esta ventana mantiene la app funcionando: se minimiza sola; no la cierres mientras la usas.
echo.
%PY% "%LANZADOR%" --practica "%PRACTICA%" %*
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
echo  No encuentro el lanzador en %LANZADOR%
echo  Este ABRIR.bat tiene que estar dentro de la carpeta de la practica, en el repo completo
echo  Sensores-Teoria (descargalo entero desde GitHub: boton "Code" y "Download ZIP").
echo.
pause
exit /b 1
