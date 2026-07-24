<div align="center">
  <img src="assets/logo.svg" width="160" alt="Lia Vault Logo" />
  <h1>🛡️ Lia Vault - On-Premise Privacy & Anonymization Suite</h1>
  <p><b>Escudo de Privacidad Local y Anonimización Inteligente Cumplimiento Ley IA / RGPD</b></p>

  [![License: Commercial / Trial](https://img.shields.io/badge/License-Proprietary%20Trial-blue.svg)](licencia.key)
  [![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
  [![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](Dockerfile)
  [![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-orange.svg)](#-descarga-e-instalación-rápida-1-clic)
</div>

---

## 📖 Descripción General

**Lia Vault** es una suite de software de grado empresarial diseñada para procesar, anonimizar y redactar de forma **100% offline y local** todo tipo de documentos confidenciales (PDFs, imágenes OCR, hojas de cálculo Excel/CSV, documentos Word y archivos de texto plano). 

Garantiza el cumplimiento normativo estricto del **RGPD / Reglamento de Inteligencia Artificial (Ley IA EU)** antes de compartir datos con LLMs o proveedores externos, asegurando que ninguna información sensible (DNI, tarjetas, nombres, direcciones, correos, IBANs, teléfonos) abandone su infraestructura corporativa.

---

## ✨ Características Principales

- **🤖 Motor NLU / NLP Offline Integrado:** Basado en Microsoft Presidio y spaCy (modelo `es_core_news_sm`).
- **🔍 OCR Local Incorporado:** Redacción visual irreversible en imágenes (PNG, JPG) y documentos escaneados PDF con EasyOCR.
- **📄 Soporte Multiformato:** PDF, DOCX, XLSX, CSV, TXT, PNG, JPG.
- **🔄 Reversibilidad Criptográfica Controlada:** Generación automática de llaves de reversión de anonimización `.reverse.key`.
- **💻 Interfaz de Usuario Intuitiva:** Aplicación de escritorio moderna desarrollada con Flet (estilo Material Design con modo oscuro).
- **🔑 Licenciamiento Fuera de Línea:** Sistema de validación criptográfica offline con control de tiempo de expiración y alteración de reloj.

---

## 🚀 Descarga e Instalación Rápida (1-Clic)

Para la mayor comodidad de los usuarios finales, Lia Vault ofrece lanzadores listos para ejecutar con **un solo doble clic** inmediatamente tras descomprimir el archivo `.zip`:

### 📦 1. Pack Nativo (Sin Docker)
> Ideal para puestos de trabajo locales con Python instalado.

1. Descargue `LiaVault_Pack_Nativo.zip` y descomprímalo.
2. Ejecute el lanzador correspondiente a su sistema operativo con **un solo doble clic**:
   - **🪟 Windows:** Doble clic en `iniciar_lia_vault_win.bat`
   - **🍏 macOS:** Doble clic en `iniciar_lia_vault_mac.command`
   - **🐧 Linux:** Ejecute `iniciar_lia_vault_linux.sh` (con permisos de ejecución `chmod +x`).

---

### 🐳 2. Pack Containerizado (Con Docker)
> Ideal para servidores corporativos, infraestructura aislada o equipos con Docker Desktop.

1. Descargue `LiaVault_Pack_Docker.zip` y descomprímalo.
2. Inicie el servicio con **un solo doble clic**:
   - **🪟 Windows:** Doble clic en `iniciar_docker_win.bat`
   - **🍏 macOS:** Doble clic en `iniciar_docker_mac.sh`
   - **🐧 Linux:** Ejecute `iniciar_docker_linux.sh`
3. Se abrirá automáticamente la aplicación en su navegador en `http://localhost:8502`.

---

## 🛠️ Compilación a Ejecutable Standalone (.exe / .app / Binario Linux)

Si prefiere empaquetar toda la aplicación en un ejecutable único sin dependencias utilizando PyInstaller:

```bash
python build_executable.py
```
El instalador autónomo se compilará automáticamente dentro del directorio `./dist/LiaVault`.

---

## 📁 Estructura del Proyecto

```text
.
├── app_grafica.py                # Interfaz de Usuario (Flet GUI Material Design)
├── app_offline.py                # Motor de Anonimización, NLU, OCR y Redacción
├── validador.py                  # Sistema Criptográfico Offline de Licencia
├── build_executable.py           # Script automatizado de compilación PyInstaller
├── iniciar_lia_vault_win.bat     # Lanzador 1-Clic para Windows
├── iniciar_lia_vault_mac.command # Lanzador 1-Clic para macOS
├── iniciar_lia_vault_linux.sh    # Lanzador 1-Clic para Linux
├── iniciar_docker_win.bat        # Lanzador Docker Windows
├── iniciar_docker_mac.sh         # Lanzador Docker macOS
├── iniciar_docker_linux.sh       # Lanzador Docker Linux
├── Dockerfile & docker-compose.yml# Configuración de contenedores
├── requirements.txt              # Dependencias de Python
├── licencia.key                  # Firma y estado de la licencia offline
├── entrada/                      # Carpeta de depósitos de archivos origen
├── salida/                       # Carpeta de salida de documentos anonimizados
└── config/                       # Diccionarios de exclusión y configuraciones
```

---

## 📄 Licencia

Este proyecto cuenta con un sistema de licencias offline administrado mediante `validador.py` y `licencia.key`. Consulte [LIA_VAULT_GUIDE.md](LIA_VAULT_GUIDE.md) para más detalles sobre cómo generar licencias personalizadas.