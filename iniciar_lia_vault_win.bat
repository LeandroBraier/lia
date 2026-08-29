@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Lia Vault On-Premise Suite
echo ========================================================
echo  Lia Vault On-Premise Suite (Windows)
echo ========================================================
echo.
echo [+] Iniciando motor de IA y servidor local...
echo [+] La aplicacion se abrira en tu navegador (http://localhost:8502)
echo.

if exist "LiaVault.exe" (
    start "" "LiaVault.exe"
    timeout /t 3 /nobreak >nul
    start http://localhost:8502
    exit /b 0
)

if exist "dist\LiaVault\LiaVault.exe" (
    start "" "dist\LiaVault\LiaVault.exe"
    timeout /t 3 /nobreak >nul
    start http://localhost:8502
    exit /b 0
)

python app_grafica.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Error al iniciar la aplicacion. Asegurese de tener Python o el ejecutable LiaVault.exe.
    pause
)
