# -*- coding: utf-8 -*-
"""
Script de Automatización PyInstaller para construir los ejecutables nativos 
de Lia Vault (Sin Docker) para macOS (.app) y Windows (.exe).
"""

import os
import sys
import platform
import subprocess
import tempfile

# Solución defensiva para fallos de TMPDIR en macOS/Linux
try:
    tempfile.gettempdir()
except Exception:
    os.environ['TMPDIR'] = '/tmp'

def construir_ejecutable_nativo():
    print("🔨 Iniciando construcción del ejecutable nativo de Lia Vault...")
    
    system = platform.system()
    print(f"🖥️ Sistema Operativo Detectado: {system}")
    
    # Instalar PyInstaller si no está presente
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name=LiaVault",
        "--add-data=assets:assets",
        "--add-data=config:config",
        "--add-data=licencia.key:.",
        "--add-data=metadata.json:.",
        "--add-data=app_offline.py:.",
        "--add-data=validador.py:.",
        "--hidden-import=spacy",
        "--hidden-import=es_core_news_sm",
        "--hidden-import=presidio_analyzer",
        "--hidden-import=presidio_anonymizer",
        "--hidden-import=easyocr",
        "--hidden-import=fitz",
        "--hidden-import=openpyxl",
        "--hidden-import=docx",
        "--collect-all=es_core_news_sm",
        "--collect-all=presidio_analyzer",
        "--collect-all=presidio_anonymizer",
        "--collect-all=flet",
        "--collect-all=flet_web",
        "--collect-all=flet_core",
        "--copy-metadata=spacy",
        "--copy-metadata=es_core_news_sm",
    ]

    if os.path.exists("assets/icon.icns"):
        cmd.append("--icon=assets/icon.icns")

    if system == "Darwin":
        cmd.extend(["--windowed", "--osx-bundle-identifier=com.liavault.app"])
    else:
        cmd.append("--console")

    cmd.append("app_grafica.py")
    
    print("📦 Ejecutando comando de compilación PyInstaller...")
    subprocess.run(cmd, check=True)
    
    if system == "Darwin":
        print("✅ Compilación exitosa. El paquete ejecutable .app se encuentra en './dist/LiaVault.app'.")
    else:
        print("✅ Compilación exitosa. El paquete ejecutable se encuentra en './dist/LiaVault'.")

if __name__ == "__main__":
    construir_ejecutable_nativo()
