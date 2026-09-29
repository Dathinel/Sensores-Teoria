@echo off
rem Carro con fisica real: linea, 3 muros, meta y vuelta al muelle
rem Abre la ventana de PyBullet. En la ventana: espacio pausa, r reinicia, q sale.
rem Parametros opcionales: --velocidad 2 (el doble de rapido), --sin-ventana --segundos 30 (verificar).
cd /d "%~dp0.."
entorno\Scripts\python -m sim.ver.carro_pista %*
if errorlevel 1 pause
