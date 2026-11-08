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
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "herramientas"))
from licencias import emitir_licencia, obtener_clave_privada  # noqa: E402
from validador import NOMBRE_LICENCIA_PRUEBA  # noqa: E402

DIAS_PRUEBA = 365

# Forzar codificacion UTF-8 segura para salida por consola
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def construir_ejecutable_nativo():
    print("[+] Iniciando construccion del ejecutable nativo de Lia Vault...")
    
    system = platform.system()
    print(f"[+] Sistema Operativo Detectado: {system}")

    # Licencia de prueba firmada para esta versión: vence DIAS_PRUEBA días después de compilar.
    # Pide la clave privada (o la toma de LIA_VAULT_CLAVE_PRIVADA).
    vence = datetime.date.today() + datetime.timedelta(days=DIAS_PRUEBA)
    contenido = emitir_licencia(obtener_clave_privada(), "Prueba Lia Vault", "prueba", vence)
    with open(NOMBRE_LICENCIA_PRUEBA, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"[+] Licencia de prueba incluida, válida hasta el {vence.isoformat()}")

    # Instalar PyInstaller si no está presente
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    
    sep = os.pathsep
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name=LiaVault",
        f"--add-data=assets{sep}assets",
        f"--add-data=config{sep}config",
        f"--add-data=metadata.json{sep}.",
        f"--add-data=app_offline.py{sep}.",
        f"--add-data=validador.py{sep}.",
        f"--add-data=llaves.py{sep}.",
        f"--add-data=auditoria.py{sep}.",
        "--hidden-import=spacy",
        "--hidden-import=es_core_news_sm",
        "--hidden-import=presidio_analyzer",
        "--hidden-import=presidio_anonymizer",
        "--hidden-import=easyocr",
        "--hidden-import=fitz",
        "--hidden-import=openpyxl",
        "--hidden-import=docx",
        "--hidden-import=flet",
        "--hidden-import=flet_web",
        "--hidden-import=flet_core",
        "--collect-all=es_core_news_sm",
        "--collect-all=presidio_analyzer",
        "--collect-all=presidio_anonymizer",
        "--collect-all=flet",
        "--collect-all=flet_web",
        "--collect-all=flet_core",
        # keyring descubre los backends del llavero por metadatos: sin esto el ejecutable no encuentra el Llavero.
        "--collect-all=keyring",
        "--copy-metadata=spacy",
        "--copy-metadata=es_core_news_sm",
    ]

    cmd.append(f"--add-data={NOMBRE_LICENCIA_PRUEBA}{sep}.")

    if system == "Darwin":
        if os.path.exists("assets/icon.icns"):
            cmd.append("--icon=assets/icon.icns")
        cmd.extend(["--windowed", "--osx-bundle-identifier=com.liavault.app"])
    else:
        if os.path.exists("assets/icon.ico"):
            cmd.append("--icon=assets/icon.ico")
        elif os.path.exists("assets/icon.png"):
            cmd.append("--icon=assets/icon.png")
        cmd.append("--console")

    cmd.append("app_grafica.py")
    
    print("[+] Ejecutando comando de compilacion PyInstaller...")
    subprocess.run(cmd, check=True)
    
    if system == "Darwin":
        print("[OK] Compilacion exitosa. El paquete ejecutable .app se encuentra en './dist/LiaVault.app'.")
    else:
        print("[OK] Compilacion exitosa. El paquete ejecutable se encuentra en './dist/LiaVault'.")

if __name__ == "__main__":
    construir_ejecutable_nativo()
