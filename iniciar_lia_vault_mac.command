#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Determinar el directorio raíz de la aplicación (soporta ejecución desde raíz o subcarpeta MAC_INSTALLER)
if [ -f "$SCRIPT_DIR/app_grafica.py" ]; then
    APP_DIR="$SCRIPT_DIR"
elif [ -f "$SCRIPT_DIR/../app_grafica.py" ]; then
    APP_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
else
    APP_DIR="$SCRIPT_DIR"
fi

cd "$APP_DIR"

echo "=================================================="
echo "🚀 Iniciando Lia Vault On-Premise (macOS)..."
echo "=================================================="

xattr -cr "$APP_DIR" 2>/dev/null || true

# Liberar el puerto 8502 si quedó una instancia previa colgada
lsof -ti:8502 | xargs kill -9 2>/dev/null || true

# 1. Si existe la aplicación compilada standalone (.app o binario), abrirla directamente
if [ -d "$APP_DIR/dist/LiaVault.app" ]; then
    echo "🚀 Lanzando aplicación LiaVault.app..."
    open "$APP_DIR/dist/LiaVault.app"
    (
        COUNT=0
        while [ $COUNT -lt 20 ]; do
            HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8502/ 2>/dev/null)
            if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 302 ]; then
                open http://localhost:8502
                break
            fi
            sleep 1
            COUNT=$((COUNT+1))
        done
    ) &
    exit 0
fi

if [ -d "$APP_DIR/LiaVault.app" ]; then
    echo "🚀 Lanzando aplicación LiaVault.app..."
    open "$APP_DIR/LiaVault.app"
    (
        COUNT=0
        while [ $COUNT -lt 20 ]; do
            HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8502/ 2>/dev/null)
            if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 302 ]; then
                open http://localhost:8502
                break
            fi
            sleep 1
            COUNT=$((COUNT+1))
        done
    ) &
    exit 0
fi

if [ -f "$APP_DIR/dist/LiaVault/LiaVault" ]; then
    chmod +x "$APP_DIR/dist/LiaVault/LiaVault"
    "$APP_DIR/dist/LiaVault/LiaVault"
    exit 0
fi

if [ -f "$APP_DIR/LiaVault" ]; then
    chmod +x "$APP_DIR/LiaVault"
    "$APP_DIR/LiaVault"
    exit 0
fi

# 2. Manejo de entorno virtual Python (venv)
PYTHON_CMD=""

if [ -f "$APP_DIR/venv/bin/python" ]; then
    PYTHON_CMD="$APP_DIR/venv/bin/python"
elif command -v python3 &>/dev/null; then
    echo "📦 Preparando entorno virtual Python..."
    python3 -m venv "$APP_DIR/venv" 2>/dev/null
    if [ -f "$APP_DIR/venv/bin/python" ]; then
        PYTHON_CMD="$APP_DIR/venv/bin/python"
        echo "📥 Instalando dependencias necesarias (flet, etc.)..."
        "$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt" 2>/dev/null
    else
        PYTHON_CMD="python3"
    fi
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Error: Python 3 no está instalado en este sistema."
    echo "Por favor instala Python 3 desde https://www.python.org/"
    read -p "Presiona Enter para salir..."
    exit 1
fi

# Verificar si flet está disponible en el entorno seleccionado
if ! "$PYTHON_CMD" -c "import flet" 2>/dev/null; then
    echo "📥 Instalando paquetes requeridos en el entorno..."
    if [ -f "$APP_DIR/venv/bin/pip" ]; then
        "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
    else
        "$PYTHON_CMD" -m pip install -r "$APP_DIR/requirements.txt" 2>/dev/null
    fi
fi

# Esperar a que el servidor web responda en el puerto 8502 y abrir el navegador
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

"$PYTHON_CMD" "$APP_DIR/app_grafica.py"

