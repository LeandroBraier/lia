#!/bin/bash
# Script instalador/desbloqueador automático para Mac
# DIR apunta al directorio raíz del DMG (padre de 🍏 MAC_INSTALLER)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
TARGET_DIR="$HOME/Applications/LiaVault"

if [ -d "$TARGET_DIR" ]; then
    echo "🧹 Eliminando instalación previa y residuos viejos de Lia Vault..."
    rm -rf "$TARGET_DIR"
fi

echo "📦 Instalando Lia Vault desde cero en su carpeta de Aplicaciones..."
mkdir -p "$TARGET_DIR"
cp -R "$DIR/"* "$TARGET_DIR/" 2>/dev/null

echo "🔓 Removiendo bloqueo de seguridad de macOS Gatekeeper..."
xattr -cr "$TARGET_DIR" 2>/dev/null || true
chmod +x "$TARGET_DIR/iniciar_lia_vault_mac.command" 2>/dev/null || true

echo "✅ Instalación y desbloqueo completados."
echo "🚀 Iniciando Lia Vault..."

cd "$TARGET_DIR"
if [ -f "$TARGET_DIR/iniciar_lia_vault_mac.command" ]; then
    exec "$TARGET_DIR/iniciar_lia_vault_mac.command"
else
    echo "❌ Error: No se encontró el script de inicio en $TARGET_DIR."
    read -p "Presiona Enter para salir..."
fi

