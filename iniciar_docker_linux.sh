#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Iniciando Lia Vault On-Premise Suite (Contenedor Docker)..."
if command -v docker &>/dev/null; then
    docker-compose up -d --build || docker compose up -d --build
    echo "⏳ Esperando a que el servidor web este completamente listo..."
    
    MAX_RETRIES=30
    COUNT=0
    SERVER_READY=false

    while [ $COUNT -lt $MAX_RETRIES ]; do
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8502/ 2>/dev/null)
        if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 302 ]; then
            SERVER_READY=true
            break
        fi
        sleep 1
        COUNT=$((COUNT+1))
    done

    echo "✅ Servidor listo. Abriendo navegador en http://localhost:8502"
    if command -v xdg-open &>/dev/null; then
        xdg-open http://localhost:8502
    elif command -v gnome-open &>/dev/null; then
        gnome-open http://localhost:8502
    fi
else
    echo "❌ Error: Docker no está instalado o en ejecución."
    read -p "Presiona Enter para salir..."
fi
