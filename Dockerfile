# Dockerfile para Lia Vault On-Premise Suite
FROM python:3.11-slim

# Instalar dependencias del sistema requeridas por OpenCV, PyMuPDF y EasyOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requerimientos e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Descargar e instalar el modelo de SpaCy en español
RUN pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.8.0/es_core_news_sm-3.8.0-py3-none-any.whl

# Copiar el código fuente completo del proyecto
COPY . .

# Crear las carpetas requeridas para los documentos
RUN mkdir -p entrada salida procesados

EXPOSE 8502

CMD ["python", "app_grafica.py"]
