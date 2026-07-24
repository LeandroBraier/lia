#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Iniciando Lia Vault On-Premise Suite (Contenedor Docker)..."
if command -v docker &>/dev/null; then
    docker-compose up -d --build || docker compose up -d --build
    echo "✅ Servidor iniciado exitosamente en http://localhost:8502"
    if command -v xdg-open &>/dev/null; then
        xdg-open http://localhost:8502
    elif command -v gnome-open &>/dev/null; then
        gnome-open http://localhost:8502
    fi
else
    echo "❌ Error: Docker no está instalado o en ejecución."
    read -p "Presiona Enter para salir..."
fi
