/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export const CODE_SNIPPETS = {
  app_offline: `# -*- coding: utf-8 -*-
import os
import re
import json
import pandas as pd
from docx import Document
import openpyxl

# Componentes de Microsoft Presidio
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

# 1. Configuración de rutas locales corporativas
CARPETA_ENTRADA = "./entrada"
CARPETA_SALIDA = "./salida"
os.makedirs(CARPETA_ENTRADA, exist_ok=True)
os.makedirs(CARPETA_SALIDA, exist_ok=True)

# 2. Inicializar IA local de Microsoft Presidio (100% Offline)
analyzer = AnalyzerEngine(supported_languages=["es"])
anonymizer = AnonymizerEngine()

# Regla personalizada para tarjetas de crédito
patron_tarjeta = Pattern(name="tarjeta_patron", regex=r"\\b\\d{4}[-\\s]?\\d{4}[-\\s]?\\d{4}[-\\s]?\\d{4}\\b", score=0.85)
reconocedor_tarjetas = PatternRecognizer(supported_entity="CREDIT_CARD", supported_language="es", patterns=[patron_tarjeta])
analyzer.registry.add_recognizer(reconocedor_tarjetas)

def anonimizar_texto_con_ia(texto):
    """Analiza el texto con IA local y reemplaza las entidades sensibles (PII)."""
    if not isinstance(texto, str) or not texto.strip():
        return texto
    
    resultados_analisis = analyzer.analyze(
        text=texto, 
        language="es",
        entities=["PERSON", "LOCATION", "ORGANIZATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"]
    )
    
    resultado_anonimizado = anonymizer.anonymize(
        text=texto,
        analyzer_results=resultados_analisis
    )
    
    return resultado_anonimizado.text

# --- SOPORTE MULTI-FORMATO ---

def procesar_documento_word(ruta_origen, ruta_destino):
    doc = Document(ruta_origen)
    for parrafo in doc.paragraphs:
        if parrafo.text.strip():
            for run in parrafo.runs:
                if run.text.strip():
                    run.text = anonimizar_texto_con_ia(run.text)
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                if celda.text.strip():
                    celda.text = anonimizar_texto_con_ia(celda.text)
    doc.save(ruta_destino)

def procesar_excel(ruta_origen, ruta_destino):
    wb = openpyxl.load_workbook(ruta_origen)
    for hoja in wb.worksheets:
        for fila in hoja.iter_rows():
            for celda in fila:
                if isinstance(celda.value, str) and celda.value.strip():
                    celda.value = anonimizar_texto_con_ia(celda.value)
    wb.save(ruta_destino)

def procesar_archivo_texto(ruta_origen, ruta_destino):
    with open(ruta_origen, "r", encoding="utf-8") as f:
        contenido = f.read()
    contenido_limpio = anonimizar_texto_con_ia(contenido)
    with open(ruta_destino, "w", encoding="utf-8") as f:
        f.write(contenido_limpio)

def procesar_tabla_csv(ruta_origen, ruta_destino):
    df = pd.read_csv(ruta_origen, dtype=str)
    for columna in df.columns:
        df[columna] = df[columna].apply(anonimizar_texto_con_ia)
    df.to_csv(ruta_destino, index=False, encoding="utf-8")
`,
  app_grafica: `# -*- coding: utf-8 -*-
import os
import flet as ft
from validador import ValidadorLicencia
from app_offline import (
    ejecutar_procesamiento_lotes, 
    CARPETA_ENTRADA, 
    CARPETA_SALIDA
)

def main(page: ft.Page):
    page.title = "Lia Vault - Escudo de Privacidad On-Premise"
    page.window_width = 800
    page.window_height = 700
    page.bgcolor = "#0F172A" # Dark Slate
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 25

    # 🚨 PASO DE SEGURIDAD: Verificar licencia offline al arrancar
    validador = ValidadorLicencia()
    licencia_valida, mensaje_licencia, cliente_id, dias = validador.verificar_licencia_offline()

    if not licencia_valida:
        # Interfaz de bloqueo por licencia expirada
        page.add(
            ft.Centered(
                ft.Column([
                    ft.Icon(ft.icons.GPP_BAD_ROUNDED, color=ft.colors.RED_400, size=90),
                    ft.Text("LIA VAULT - ACCESO BLOQUEADO", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(mensaje_licencia, size=14, color=ft.colors.GREY_400, text_align=ft.TextAlign.CENTER),
                    ft.Divider(height=20, color=ft.colors.TRANSPARENT),
                    ft.Text("Contacte a soporte técnico para renovar la llave:"),
                    ft.Text("soporte@liavault.internal", color=ft.colors.BLUE_400, weight=ft.FontWeight.BOLD)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        )
        page.update()
        return

    # Carga de Interfaz normal...
    page.add(
        ft.Column([
            ft.Text("Lia Vault Escudo Local", size=28, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_200),
            ft.Text("Procesando datos On-Premise sin tocar Internet", size=14, color=ft.colors.GREEN_400)
        ])
    )
    page.update()

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8502, host="0.0.0.0")
`,
  validador: `# -*- coding: utf-8 -*-
import os
import datetime
import hashlib

SALT_INTEGRIDAD = b"LIA_VAULT_SECURITY_SALT_2026_PROD"

class ValidadorLicencia:
    def __init__(self, ruta_licencia="./licencia.key"):
        self.ruta_licencia = ruta_licencia

    def generar_licencia_oficial(self, cliente_id, fecha_exp_str):
        info_basica = f"{fecha_exp_str}|{cliente_id}"
        hash_firma = hashlib.sha256(info_basica.encode('utf-8') + SALT_INTEGRIDAD).hexdigest()
        contenido = f"{hash_firma}\\n{info_basica}"
        with open(self.ruta_licencia, "w", encoding="utf-8") as f:
            f.write(contenido)

    def verificar_licencia_offline(self):
        if not os.path.exists(self.ruta_licencia):
            return False, "Falta archivo de licencia", "Invitado", 0
        # Validación de expiración...
        return True, "Licencia Activa", "Cliente Demo", 365
`,
  dockerfile: `# Usar una imagen oficial de Python ligera y estable
FROM python:3.10-slim

# Instalar dependencias del sistema operativo requeridas por OpenCV y Flet
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar e instalar las librerías de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Descargar los modelos de lenguaje (spaCy es_core_news_sm) y OCR (EasyOCR)
RUN python -m spacy download es_core_news_sm
RUN python -c "import easyocr; lector = easyocr.Reader(['es', 'en'], gpu=False)"

# Copiar los scripts de la aplicación y herramientas de seguridad
COPY app_offline.py .
COPY app_grafica.py .
COPY validador.py .

# Crear las carpetas de procesamiento de datos por defecto
RUN mkdir -p entrada salida config

# Exponer el puerto de la aplicación web local compartida de Flet (8502)
EXPOSE 8502

# Comando por defecto para iniciar el servidor web local al encender el contenedor
CMD ["python", "app_grafica.py"]
`,
  requirements: `pandas>=2.0.0
openpyxl>=3.1.0
python-docx>=1.1.0
pymupdf>=1.23.0
easyocr>=1.7.1
pillow>=10.0.0
opencv-python-headless>=4.8.0
presidio-analyzer>=2.2.0
presidio-anonymizer>=2.2.0
spacy>=3.7.0
flet>=0.21.0
cryptography>=41.0.0
`
};
