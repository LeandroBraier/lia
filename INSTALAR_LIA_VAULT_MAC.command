#!/bin/bash
# Script instalador/desbloqueador automático para Mac
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_DIR="$HOME/Applications/LiaVault"

echo "📦 Instalando Lia Vault en su carpeta de Aplicaciones..."
mkdir -p "$TARGET_DIR"
cp -R "$DIR/"* "$TARGET_DIR/" 2>/dev/null

echo "🔓 Removiendo bloqueo de seguridad de macOS Gatekeeper..."
xattr -cr "$TARGET_DIR" 2>/dev/null || true
chmod +x "$TARGET_DIR/iniciar_lia_vault_mac.command" 2>/dev/null || true

echo "✅ Instalación y desbloqueo completados."
echo "🚀 Iniciando Lia Vault..."

cd "$TARGET_DIR"
if command -v python3 &>/dev/null; then
    python3 app_grafica.py
elif command -v python &>/dev/null; then
    python app_grafica.py
else
    echo "❌ Error: Python 3 no está instalado en este sistema."
    read -p "Presiona Enter para salir..."
fi
