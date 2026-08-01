# Dockerfile optimizado ultraligero para Lia Vault On-Premise Suite
FROM python:3.11-slim

# Instalar librerías de sistema mínimas sin compiladores
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Instalar PyTorch CPU directamente
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Instalar modelo SpaCy en español
RUN pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.8.0/es_core_news_sm-3.8.0-py3-none-any.whl

# 4. Copiar código fuente
COPY . .

# 5. Crear carpetas de trabajo
RUN mkdir -p entrada salida procesados

EXPOSE 8502

CMD ["python", "app_grafica.py"]
