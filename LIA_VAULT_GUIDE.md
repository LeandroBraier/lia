# 🛡️ Guía de Despliegue y Ejecución - Lia Vault (Offline)

Esta es la documentación técnica oficial de **Lia Vault**, diseñada para administradores de sistemas y desarrolladores que implementan el escudo de privacidad local en redes corporativas de PYMEs.

---

## 🗺️ Estructura del Proyecto

El código completo y refactorizado se encuentra en los siguientes archivos de su espacio de trabajo:

1. **`app_offline.py`**: El cerebro del anonimizador de datos (IA local de Microsoft Presidio, spaCy, EasyOCR para imágenes y PyMuPDF para redacción de PDFs).
2. **`app_grafica.py`**: Interfaz gráfica moderna (estilo Google Material Design con tema oscuro) programada con Flet.
3. **`validador.py`**: Sistema criptográfico offline de autenticación y verificación de licencias (Trial de 1 año con control de alteración de reloj).
4. **`requirements.txt`**: Librerías de Python requeridas.
5. **`Dockerfile`**: Configuración de contenedor de Docker para despliegue centralizado en LAN.

---

## 🛠️ Requisitos e Instalación Local

Para correr Lia Vault directamente en su computadora con Python:

### 1. Clonar o descargar los archivos
Asegúrese de tener los archivos listados arriba en una misma carpeta llamada `lia_vault_pyme/`.

### 2. Instalar dependencias de Python
Abra una terminal en esa carpeta y ejecute:
```bash
pip install -r requirements.txt
```

### 3. Descargar el modelo de lenguaje en Español (NLU)
Para que el analizador de Microsoft Presidio pueda detectar nombres y locaciones en contexto en español de forma offline:
```bash
python -m spacy download es_core_news_sm
```

### 4. Lanzar la Aplicación Gráfica
```bash
python app_grafica.py
```
Se levantará un servidor local rápido y abrirá de forma automática su navegador web en `http://localhost:8502`. Cualquier computadora en la misma red local (LAN) podrá acceder a la interfaz web escribiendo la dirección IP de su equipo en su navegador (ej. `http://192.168.1.50:8502`).

---

## ⚙️ Cómo Generar el Ejecutable Local (`.exe` o `.app`)

Para empaquetar todo el ecosistema (Python + Flet + Modelos de IA) en un único ejecutable distribuible sin necesidad de que el usuario final tenga Python instalado, se utiliza **PyInstaller**.

### 1. Instalar PyInstaller
```bash
pip install pyinstaller
```

### 2. Comando de Compilación Unificada
Ejecute el siguiente comando en su terminal para compilar `app_grafica.py` como una aplicación de escritorio consolidada:
```bash
pyinstaller --name="LiaVault" --noconsole --onefile \
  --add-data "validador.py:." \
  --add-data "app_offline.py:." \
  app_grafica.py
```

*Nota:* PyInstaller creará un archivo ejecutable autónomo en la carpeta `dist/`. La primera vez que el usuario final ejecute la aplicación, esta creará automáticamente las carpetas `entrada/`, `salida/` y `config/` en el mismo directorio del ejecutable.

---

## 🐳 Despliegue Corporativo con Docker (Recomendado para PYMEs)

Para evitar alertas de SmartScreen o Gatekeeper en los equipos clientes, levante Lia Vault en un servidor Docker central de la empresa y permita que los empleados accedan mediante red local.

### 1. Construir la Imagen
```bash
docker build -t lia-vault .
```

### 2. Levantar el Contenedor con Persistencia Local
```bash
docker run -d \
  -p 8502:8502 \
  -v ./entrada:/app/entrada \
  -v ./salida:/app/salida \
  -v ./config:/app/config \
  --name lia_vault_server \
  lia-vault
```

Los empleados podrán procesar carpetas compartidas directamente y acceder a la interfaz hermosa escribiendo la IP del servidor en el puerto `8502`.

---

## 🔑 Gestión de Licencia Offline (`licencia.key`)

El archivo `licencia.key` se compone de una firma de integridad SHA-256 de seguridad y los parámetros de expiración. 

### Crear Licencias a Medida
Para emitir licencias corporativas o de pruebas con fechas de expiración específicas, use la función incorporada de generación en `validador.py`. Abra una consola de Python en el directorio y ejecute:

```python
from validador import ValidadorLicencia
import datetime

# Instanciar validador
validador = ValidadorLicencia()

# Generar licencia de 365 días para un cliente específico (ej. Vence el 2027-07-19)
vencimiento = (datetime.date.today() + datetime.timedelta(days=365)).isoformat()
validador.generar_licencia_oficial("CLIENTE_VITALICIO_PYME", vencimiento)
```

Esto generará un archivo `licencia.key` firmado en la raíz de su proyecto. Distribuya este archivo con el instalador para activar el periodo de uso del cliente.
