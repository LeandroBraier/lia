# 🚀 Quickstart - Lia Vault Local Execution

Este proyecto cuenta con dos componentes principales para su ejecución y prueba local:

1. **Frontend Interactivo (React + Vite + TypeScript)**: Una simulación web rápida y responsiva.
2. **Motor de IA Offline (Python + Flet)**: El núcleo del sistema que implementa NLU (Microsoft Presidio/spaCy) y OCR de forma 100% offline.

Sigue las guías a continuación para levantar cualquiera de los dos entornos.

---

## 💻 Opción A: Frontend Web (React + Vite)
Ideal para explorar y probar la interfaz de usuario interactiva y las reglas de redacción locales.

### 📋 Requisitos Previos
* [Node.js](https://nodejs.org/) (versión 18 o superior)
* Administrador de paquetes `npm` (incluido con Node.js)

### 🛠️ Pasos de Instalación
1. **Instalar las dependencias de Node:**
   ```bash
   npm install
   ```

2. **Configurar las Variables de Entorno (Opcional):**
   Copia el archivo `.env.example` como `.env.local` y configura tu clave de API si deseas conectar con servicios en la nube:
   ```bash
   cp .env.example .env.local
   ```
   *Nota: Edita `.env.local` y reemplaza `"MY_GEMINI_API_KEY"` con tu clave real si tu flujo lo requiere.*

3. **Iniciar el servidor de desarrollo:**
   ```bash
   npm run dev
   ```

4. **Acceder a la aplicación:**
   Abre tu navegador y navega a:
   👉 **`http://localhost:3000`**

---

## 🐍 Opción B: Motor de IA & App de Escritorio (Python + Flet)
Esta es la versión real de producción offline que utiliza procesamiento local para textos, imágenes y PDFs.

### 📋 Requisitos Previos
* [Python 3.10+](https://www.python.org/downloads/)
* `pip` (Administrador de paquetes de Python)

### 🛠️ Pasos de Instalación
1. **Instalar las dependencias de Python:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Descargar el modelo de procesamiento de lenguaje natural en Español (NLU):**
   Microsoft Presidio requiere un modelo entrenado en español para detectar entidades como nombres de personas y ubicaciones:
   ```bash
   python -m spacy download es_core_news_sm
   ```

3. **Ejecutar la aplicación gráfica:**
   ```bash
   python app_grafica.py
   ```

4. **Acceder a la interfaz:**
   La aplicación se abrirá automáticamente en tu navegador predeterminado en:
   👉 **`http://localhost:8502`**

---

## 🐳 Opción C: Despliegue con Docker
Si prefieres no instalar dependencias de forma local, puedes encapsular el motor de Python usando Docker.

1. **Construir la imagen de Docker:**
   ```bash
   docker build -t lia-vault .
   ```

2. **Levantar el contenedor con persistencia de carpetas:**
   ```bash
   docker run -d \
     -p 8502:8502 \
     -v ./entrada:/app/entrada \
     -v ./salida:/app/salida \
     -v ./config:/app/config \
     --name lia_vault_server \
     lia-vault
   ```
3. Accede desde tu navegador a **`http://localhost:8502`**.
