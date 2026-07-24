@echo off
cd /d "%~dp0"
title Lia Vault On-Premise Suite
echo ========================================================
echo 🚀 Iniciando Lia Vault On-Premise Suite...
echo ========================================================
python app_grafica.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Error al iniciar la aplicación. Asegúrese de tener Python instalado.
    pause
)
