@echo off
echo 🚀 Iniciando Lia Vault On-Premise Suite (Contenedor Docker)...
docker-compose up -d --build
echo ✅ Servidor iniciado en http://localhost:8502
start http://localhost:8502
