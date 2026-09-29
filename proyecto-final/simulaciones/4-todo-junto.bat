@echo off
rem Todo junto: prueba_completa (ventana de la planta + ventana del carro)
rem Abre la ventana de PyBullet. En la ventana: espacio pausa, r reinicia, q sale.
rem Parametros opcionales: --velocidad 2 (el doble de rapido), --sin-ventana --segundos 30 (verificar).
cd /d "%~dp0.."
entorno\Scripts\python -m sim.ver.todo_junto %*
if errorlevel 1 pause
