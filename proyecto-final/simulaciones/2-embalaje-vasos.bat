@echo off
rem Embalaje de vasos: llenado, tapa, prensa, empujador, canaleta y sabotajes
rem Abre la ventana de PyBullet. En la ventana: espacio pausa, r reinicia, q sale.
rem Parametros opcionales: --velocidad 2 (el doble de rapido), --sin-ventana --segundos 30 (verificar).
cd /d "%~dp0.."
entorno\Scripts\python -m sim.ver.embalaje_vasos %*
if errorlevel 1 pause
