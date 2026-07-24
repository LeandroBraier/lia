#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Iniciando Lia Vault On-Premise Suite..."
if command -v python3 &>/dev/null; then
    python3 app_grafica.py
elif command -v python &>/dev/null; then
    python app_grafica.py
else
    echo "❌ Error: Python 3 no está instalado en este sistema."
    echo "Por favor instala Python 3.10+ y reintenta."
    read -p "Presiona Enter para salir..."
fi
