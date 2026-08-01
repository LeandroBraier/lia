@echo off
echo 🚀 Iniciando Lia Vault On-Premise Suite (Contenedor Docker)...
docker-compose up -d --build
echo ⏳ Esperando a que el servidor web este completamente listo...
:check_loop
timeout /t 1 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://localhost:8502/ | findstr /R "200 302" >nul
if errorlevel 1 (
    goto check_loop
)
echo ✅ Servidor listo. Abriendo navegador en http://localhost:8502
start http://localhost:8502
