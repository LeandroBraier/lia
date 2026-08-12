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
- **🌐 Interfaz Web Moderna & Desktop GUI:** Elección entre la interfaz de escritorio Flet (Material Design) y la interfaz Web dinámica construida en React 19 + Vite + Express.
- **🔄 Reversibilidad Criptográfica Controlada:** Generación automática de llaves de reversión de anonimización `.reverse.key`.
- **💼 Diccionario Corporativo Personalizado:** Reglas de exclusión y reemplazos específicos para entidades corporativas.
- **🔑 Licenciamiento Fuera de Línea:** Sistema de validación criptográfica offline con control de expiración y protección anti-tamper de reloj.

---

## 🚀 Descarga e Instalación Rápida (1-Clic)

Para la mayor comodidad de los usuarios finales, Lia Vault ofrece lanzadores listos para ejecutar con **un solo doble clic** inmediatamente tras descomprimir el archivo `.zip`:

### 📦 1. Pack Nativo (Sin Docker)
> Ideal para puestos de trabajo locales con Python instalado.

1. Descargue o clone el repositorio.
2. Ejecute el instalador automático / lanzador correspondiente a su sistema operativo:
   - **🍏 macOS (Instalación limpia):** Clic en `INSTALAR_LIA_VAULT_MAC.command`
   - **🍏 macOS (Ejecución):** Doble clic en `iniciar_lia_vault_mac.command`
   - **🪟 Windows:** Doble clic en `iniciar_lia_vault_win.bat`
   - **🐧 Linux:** Ejecute `iniciar_lia_vault_linux.sh` (con permisos `chmod +x`).

---

### 🌐 2. Interfaz Web (React + Vite + Express)
> Para ejecutar la suite web completa:

```bash
# Instalar dependencias de Node.js
npm install

# Iniciar servidor de desarrollo en http://localhost:3000
npm run dev

# Compilar para producción
npm run build
```

---

### 🐳 3. Pack Containerizado (Con Docker)
> Ideal para servidores corporativos, infraestructura aislada o equipos con Docker Desktop.

1. Inicie el servicio con **un solo doble clic**:
   - **🪟 Windows:** Doble clic en `iniciar_docker_win.bat`
   - **🍏 macOS:** Doble clic en `iniciar_docker_mac.sh`
   - **🐧 Linux:** Ejecute `iniciar_docker_linux.sh`
2. Se abrirá automáticamente la aplicación en su navegador en `http://localhost:8502`.

---

## ⚙️ Configuración y Variables de Entorno

Copie el archivo de ejemplo `.env.example` a `.env` para ajustar la configuración:

```bash
cp .env.example .env
```

Parámetros clave:
- `PORT`: Puerto de ejecución del servidor web (por defecto: `3000`).
- `MODE`: Modo de ejecución (`offline` / `production`).
- `LICENSE_PATH`: Ruta al archivo `licencia.key`.

---

## 🔑 Gestión de Licencias Offline

El sistema utiliza validación RSA/HMAC criptográfica local. Para comprobar o generar licencias de prueba:

```bash
# Validar la licencia actual
python validador.py

# Generar clave de prueba o evaluar expiración
python generar_key_prueba.py
```

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
├── app_grafica.py                # Interfaz de Usuario Desktop (Flet GUI Material Design)
├── app_offline.py                # Motor Principal de Anonimización, NLU, OCR y Redacción
├── validador.py                  # Sistema Criptográfico Offline de Licencia
├── generar_key_prueba.py         # Utilidad para generación y verificación de claves de prueba
├── build_executable.py           # Script automatizado de compilación PyInstaller
├── src/                          # Componentes del Frontend Web (React 19 + Vite)
├── index.html                    # Entry point de la App Web
├── package.json                  # Dependencias y scripts de Node.js / Vite
├── INSTALAR_LIA_VAULT_MAC.command# Instalador automático para macOS
├── iniciar_lia_vault_mac.command # Lanzador 1-Clic para macOS
├── iniciar_lia_vault_win.bat     # Lanzador 1-Clic para Windows
├── iniciar_lia_vault_linux.sh    # Lanzador 1-Clic para Linux
├── iniciar_docker_mac.sh         # Lanzador Docker macOS
├── iniciar_docker_win.bat        # Lanzador Docker Windows
├── iniciar_docker_linux.sh       # Lanzador Docker Linux
├── Dockerfile & docker-compose.yml# Configuración de contenedores Docker
├── requirements.txt              # Dependencias de Python
├── licencia.key                  # Firma y estado de la licencia offline
├── .env.example                  # Plantilla de configuración de variables de entorno
├── entrada/                      # Carpeta de depósitos de archivos origen
├── salida/                       # Carpeta de salida de documentos anonimizados
├── diccionario_corporativo.txt/  # Diccionario corporativo de entidades excluidas/reemplazadas
└── config/                       # Archivos de configuración general
```

---

## 📄 Licencia

Este proyecto cuenta con un sistema de licencias offline administrado mediante `validador.py` y `licencia.key`. Consulte [LIA_VAULT_GUIDE.md](LIA_VAULT_GUIDE.md) para más detalles sobre cómo generar e instalar licencias personalizadas.