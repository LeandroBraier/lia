# Lia Vault On-Premise Suite: imagen endurecida (H3).
# El código queda de solo lectura; los datos van al volumen /datos y el registro a /var/log/lia_vault.
FROM python:3.11-slim

# Librerías de sistema mínimas, sin compiladores
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    LIA_VAULT_BASE=/datos \
    LIA_VAULT_LOG=/var/log/lia_vault/lia_vault.log \
    EASYOCR_MODULE_PATH=/opt/easyocr

WORKDIR /app

# 1. PyTorch CPU
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Dependencias Python y modelo SpaCy en español
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.8.0/es_core_news_sm-3.8.0-py3-none-any.whl

# 3. Modelos de OCR dentro de la imagen: el contenedor no descarga nada ni escribe fuera de sus volúmenes
RUN python -c "import easyocr; easyocr.Reader(['es', 'en'], gpu=False)"

# 4. Solo el código de la aplicación (nada de datos, llaves ni documentos del repositorio)
COPY app_grafica.py app_offline.py validador.py llaves.py auditoria.py i18n.py metadata.json ./
COPY assets ./assets
COPY config ./config

# 5. Usuario sin privilegios
RUN useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin lia \
    && mkdir -p /datos /var/log/lia_vault \
    && chown lia:lia /datos /var/log/lia_vault
USER 10001:10001

EXPOSE 8502

CMD ["python", "app_grafica.py"]
