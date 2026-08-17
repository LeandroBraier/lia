@echo off
cd /d "%~dp0"
title Lia Vault On-Premise Suite
echo ========================================================
echo 🚀 Iniciando Lia Vault On-Premise Suite (Windows)...
echo ========================================================

if exist "dist\LiaVault\LiaVault.exe" (
    start "" "dist\LiaVault\LiaVault.exe"
    exit /b 0
)

if exist "LiaVault.exe" (
    start "" "LiaVault.exe"
    exit /b 0
)

python app_grafica.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Error al iniciar la aplicación. Asegúrese de tener Python o el ejecutable LiaVault.exe.
    pause
)
