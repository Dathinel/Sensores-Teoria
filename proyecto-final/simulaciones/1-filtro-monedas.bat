@echo off
rem Filtro de monedas (grupo 7): cinta de monedas + almacen, escenario mixto_20
rem Abre la ventana de PyBullet. En la ventana: espacio pausa, r reinicia, q sale.
rem Parametros opcionales: --velocidad 2 (el doble de rapido), --sin-ventana --segundos 30 (verificar).
cd /d "%~dp0.."
entorno\Scripts\python -m sim.ver.filtro_monedas %*
if errorlevel 1 pause
