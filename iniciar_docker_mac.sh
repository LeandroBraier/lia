#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."
echo "🚀 Iniciando Lia Vault On-Premise Suite (Contenedor Docker macOS)..."

# Verificar si Docker Daemon está en ejecución
if ! docker info &>/dev/null; then
    echo "❌ Error: Docker Desktop no está iniciado o no se encuentra en ejecución."
    echo "Por favor abra la aplicación Docker Desktop en su Mac y vuelva a intentarlo."
    read -p "Presiona Enter para salir..."
    exit 1
fi

if docker-compose up -d --build || docker compose up -d --build; then
    echo "⏳ Esperando a que la aplicación Flet/Web termine de inicializarse..."
    
    # Bucle de Sondeo de Salud (Healthcheck Probe)
    # Revisa cada 1 segundo si el servidor web responde en el puerto 8502 (HTTP 200/302)
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

    if [ "$SERVER_READY" = true ]; then
        echo "✅ Servidor listo. Abriendo navegador en http://localhost:8502"
        open http://localhost:8502
    else
        echo "⚠️ El servidor tardó más de lo esperado en iniciar. Abriendo http://localhost:8502..."
        open http://localhost:8502
    fi
else
    echo "❌ Ocurrió un error al levantar el contenedor de Docker."
    read -p "Presiona Enter para salir..."
fi
