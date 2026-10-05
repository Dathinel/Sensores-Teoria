@echo off
rem ---------------------------------------------------------------------------------
rem  Lanzador de las practicas de Sensores-Teoria (doble clic aqui).
rem
rem  Busca un Python instalado y corre probar.py, que abre en el navegador una pagina con
rem  una tarjeta por practica y botones para probar cada una sin hardware. probar.py solo
rem  usa la biblioteca estandar: no hace falta instalar nada antes. Los paquetes de cada
rem  practica (PyBullet, OpenCV, ...) los instala el propio lanzador la primera vez, en el
rem  entorno\ de esa practica.
rem ---------------------------------------------------------------------------------
setlocal
rem UTF-8 en la consola, para que las tildes de los mensajes se vean bien.
chcp 65001 >nul
cd /d "%~dp0"
title Lanzador de Sensores-Teoria

rem 1) "py" es el lanzador que instala el instalador oficial de python.org: el mas fiable.
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul && set "PY=py -3"

rem 2) Si no, "python" del PATH. En Windows, si Python no esta instalado, "python" puede ser
rem    un acceso directo a la Microsoft Store que no hace nada: por eso se comprueba la version.
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul && set "PY=python"
)

if not defined PY goto sin_python

%PY% probar.py %*
rem Si probar.py termino con error, se deja la ventana abierta para leer el mensaje.
if errorlevel 1 pause
exit /b

:sin_python
echo.
echo  No encontre Python 3.9 o mas nuevo en este equipo.
echo.
echo  Para instalarlo:
echo    1. Entra a https://www.python.org/downloads/ y baja Python 3.13
echo       (con esa basta para abrir el lanzador; si una practica pide otra version,
echo       su boton en la pagina dice cual y desde donde instalarla).
echo    2. En el instalador marca "Add python.exe to PATH" y deja marcado el "py launcher".
echo    3. Cuando termine, vuelve a hacer doble clic en PROBAR.bat.
echo.
pause
exit /b 1
