@echo off
rem Menu de las simulaciones de PyBullet con fisica (sim/ver/). Doble clic y elegir.
cd /d "%~dp0"
:menu
cls
echo.
echo   SIMULACIONES DE PYBULLET (fisica real)
echo   --------------------------------------
echo   1  Filtro de monedas (grupo 7): cinta de monedas + almacen
echo   2  Embalaje de vasos: llenado, tapa, prensa, empujador, canaleta
echo   3  Carro en la pista: linea, 3 muros, meta y vuelta al muelle
echo   4  Todo junto: prueba_completa (planta + carro)
echo   5  Abrir la carpeta de videos (docs\videos)
echo   0  Salir
echo.
echo   En la ventana: espacio = pausa, r = reiniciar, q = salir.
echo.
choice /c 123450 /n /m "  Elija una opcion: "
if errorlevel 6 exit /b
if errorlevel 5 (start "" explorer "%~dp0docs\videos" & goto menu)
if errorlevel 4 (call "%~dp0simulaciones\4-todo-junto.bat" & goto menu)
if errorlevel 3 (call "%~dp0simulaciones\3-carro-pista.bat" & goto menu)
if errorlevel 2 (call "%~dp0simulaciones\2-embalaje-vasos.bat" & goto menu)
if errorlevel 1 (call "%~dp0simulaciones\1-filtro-monedas.bat" & goto menu)
goto menu
