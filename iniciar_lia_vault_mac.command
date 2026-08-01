#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."

echo "=================================================="
echo "🚀 Iniciando Lia Vault On-Premise (macOS)..."
echo "=================================================="

xattr -cr "$DIR/.." 2>/dev/null || true

# 1. Si existe la aplicación compilada standalone en dist/LiaVault/LiaVault, abrirla directamente sin requerir Python
if [ -f "dist/LiaVault/LiaVault" ]; then
    chmod +x "dist/LiaVault/LiaVault"
    ./dist/LiaVault/LiaVault
    exit 0
fi

if [ -f "LiaVault" ]; then
    chmod +x "LiaVault"
    ./LiaVault
    exit 0
fi

# 2. Si no hay ejecutable autónomo, usar Python 3 del sistema
if command -v python3 &>/dev/null; then
    (
        # Esperar a que el servidor web responda en el puerto 8502 y abrir el navegador
        COUNT=0
        while [ $COUNT -lt 30 ]; do
            HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8502/ 2>/dev/null)
            if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 302 ]; then
                open http://localhost:8502
                break
            fi
            sleep 1
            COUNT=$((COUNT+1))
        done
    ) &
    python3 app_grafica.py
elif command -v python &>/dev/null; then
    (
        COUNT=0
        while [ $COUNT -lt 30 ]; do
            HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8502/ 2>/dev/null)
            if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 302 ]; then
                open http://localhost:8502
                break
            fi
            sleep 1
            COUNT=$((COUNT+1))
        done
    ) &
    python app_grafica.py
else
    echo "❌ Error: Python 3 no está instalado en este sistema."
    echo "Por favor instala Python 3 desde https://www.python.org/ o compila el binario autónomo con build_executable.py"
    read -p "Presiona Enter para salir..."
fi
