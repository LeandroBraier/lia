# -*- coding: utf-8 -*-
"""
Módulo de Internacionalización (i18n) para Lia-Vault.
Permite alternar entre Español (ES) e Inglés (EN) de forma ligera sin impacto en el peso del instalador.
Detecta automáticamente el idioma del sistema operativo en el primer inicio con fallback a Español.
"""

import os
import json
import locale

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")

TRANSLATIONS = {
    "es": {
        # General & App Header
        "app_title": "Lia Vault - Escudo de privacidad on-premise",
        "header_subtitle": "Suite de Privacidad y Anonimización 100% On-Premise",
        "privacy_tagline": "100% Local • Cero Fugas de Datos • Motor NLP On-Premise",
        "lang_switch_tooltip": "Cambiar idioma / Switch language",
        "server_lan": "127.0.0.1:8502 (LAN)",
        "license_active_badge": "Trial activo ({days}d)",
        "license_invalid_badge": "Licencia No Válida",

        # Sidebar
        "sidebar_local_features": "FUNCIONES LOCALES",
        "sidebar_deploy_admin": "DESPLIEGUE & ADMIN",
        "sidebar_tour_btn": "Iniciar tour interactivo",
        "sidebar_privacy_badge": "PRIVACIDAD 100% GARANTIZADA",
        "sidebar_privacy_desc": "Procesamiento totalmente local en tu CPU/GPU. Cero conexiones externas.",

        # Tabs & Navigation Buttons
        "tab_sanitizer": "Seudonimización (reversible)",
        "tab_anonymizer": "Anonimización (irreversible)",
        "tab_reversion": "Traducción inversa",
        "tab_dictionary": "Diccionario empresa",
        "tab_license": "Licencias y simulación",
        "tab_code": "Código on-premise",

        # Common Actions & Buttons
        "btn_add_files": "Seleccionar archivos",
        "btn_clear_all": "Limpiar todo",
        "btn_open_folder": "Abrir carpeta",
        "btn_browse": "Explorar...",
        "btn_copy": "Copiar al portapapeles",
        "btn_copied": "¡Copiado!",
        "btn_refresh": "Refrescar",
        "btn_close": "Cerrar",
        "btn_save": "Guardar",
        "btn_cancel": "Cancelar",
        "btn_download": "Descargar",
        "btn_anonymize_row": "Anonimizar",
        "btn_open_doc": "Abrir documento",
        "btn_key_doc": "Llave .key",
        "btn_open": "Abrir",
        "btn_anon_now": "Anonimizar ahora",
        "btn_rgpd_cert": "Certificado RGPD",
        "badge_incompatible": "No compatible",
        "badge_new": "NUEVO",
        "dropzone_formats": "TXT, CSV, DOCX, XLSX, PDF, PNG/JPG",
        "dropzone_prompt": "Arrastre archivos aquí o haga clic para seleccionar",
        "queue_empty_folder": "Carpeta /entrada vacía.",

        # Sanitizer Tab (Reversible)
        "sanitizer_card_title": "Sanitizador de archivos",
        "sanitizer_card_desc": "Arrastre sus documentos para buscar datos sensibles y generar un clon protegido listo para ChatGPT.",
        "sanitizer_btn_process": "Procesar todo el lote",
        "sanitizer_queue_title": "COLA DE ARCHIVOS LISTOS",
        "sanitizer_queue_status": "Cola actualizada: {count} archivo(s) pendientes.",
        "sanitizer_preview_empty_title": "Ningún archivo seleccionado",
        "sanitizer_preview_empty_desc": "Seleccione un archivo para previsualizar.",
        "sanitizer_output_title": "Archivos seguros ya procesados",
        "sanitizer_output_path_hint": "📍 Ubicación física de descarga en tu equipo: ./salida (dentro de la carpeta del proyecto)",
        "sanitizer_tooltip_folder": "Abrir carpeta de salida en explorador",
        "sanitizer_tooltip_folder_docker": "Acceso directo desactivado en Docker (archivos almacenados en ./salida)",
        "sanitizer_no_processed": "No hay archivos procesados en la carpeta de salida aún.",
        "sanitizer_status_ready": "Listo para escanear y seudonimizar.",
        "sanitizer_status_processing": "Procesando lote completo con IA y OCR offline...",
        "sanitizer_status_completed": "Lote completado exitosamente ({count} archivos procesados con su .key).",
        "sanitizer_status_error": "Error en ejecución: {error}",

        # Anonymizer Tab (Irreversible - RGPD)
        "anon_card_title": "Anonimización irreversible RGPD",
        "anon_card_desc": "Anonimiza irreversiblemente datos personales aplicando k-anonimato y generalización conforme a RGPD.",
        "anon_btn_process": "Anonimizar todo el lote (Irreversible - RGPD)",
        "anon_queue_title": "COLA DE ARCHIVOS (ANONIMIZACIÓN)",
        "anon_queue_status": "Cola lista: {count} archivo(s) pendientes para anonimizar.",
        "anon_k_label": "Nivel k-anonimato (Tablas)",
        "anon_k_3": "k = 3 (Uso interno / Retención)",
        "anon_k_5": "k = 5 (Cesión a terceros / Modelos IA)",
        "anon_k_10": "k = 10 (Máxima protección)",
        "anon_quasi_label": "Generalizar cuasi-identificadores (Fechas a años, CPs truncados)",
        "anon_output_title": "CARPETA DE SALIDA: ARCHIVOS ANONIMIZADOS RGPD",
        "anon_output_path": "Ruta: {path}",
        "anon_tooltip_folder": "Abrir carpeta de anonimizados",
        "anon_no_processed": "No hay documentos anonimizados en la carpeta de salida aún.",
        "anon_status_ready": "Listo para anonimizar de forma irreversible (RGPD).",
        "anon_status_processing": "Ejecutando anonimización irreversible RGPD...",
        "anon_status_completed": "Anonimización completada ({count} archivos procesados con certificado RGPD).",
        "anon_status_error": "Error en anonimización: {error}",

        # Reversion Tab (Reverse Translation)
        "reversion_card_title": "Traducción inversa inteligente",
        "reversion_card_desc": "Pegue la respuesta o suba el archivo generado por la IA. Seleccione el documento de origen y Lia Vault aplicará su llave (.key) automáticamente.",
        "reversion_dd_label": "Documento procesado de origen",
        "reversion_btn_load_key": "Cargar .key manual",
        "reversion_btn_load_ai_doc": "Cargar archivo de respuesta IA",
        "reversion_txt_no_doc": "Sin archivo cargado",
        "reversion_txt_key_auto": "Seleccione el documento de origen arriba para usar su llave automáticamente",
        "reversion_hint_input": "Pegue el texto o respuesta generada por la IA aquí...",
        "reversion_btn_restore": "Desanonimizar y revertir",
        "reversion_btn_clear": "Limpiar campos",
        "reversion_output_label": "Respuesta original restaurada:",
        "reversion_output_hint": "Resultado de la respuesta con datos reales restaurados...",
        "reversion_btn_save_file": "Guardar respuesta en archivo",
        "reversion_status_processing": "Procesando desanonimización con clave .key...",
        "reversion_status_completed": "Desanonimización finalizada con éxito.",

        # Corporate Dictionary Tab
        "dict_card_title": "Diccionario confidencial empresa",
        "dict_card_desc": "Los términos añadidos aquí se censuran automáticamente con [CONFIDENCIAL] en documentos e imágenes.",
        "dict_tf_hint": "Término prohibido...",
        "dict_btn_add": "Añadir",
        "dict_btn_import": "Importar .txt",
        "dict_current_terms": "Términos actuales (presione 'X' para eliminar):",

        # License Tab
        "license_card_title": "Gestión de licencia on-premise",
        "license_card_desc": "Detalles de validación offline de la licencia actual de Lia Vault.",
        "license_client_label": "ID cliente:",
        "license_trial_days": "Días de prueba restantes: {days} días",
        "license_status_text": "Estado oficial: {status}",
        "license_valid_msg": "✅ Licencia válida para {client}. Quedan {days} días de Trial.",
        "license_invalid_msg": "❌ Licencia no válida o expirada.",

        # Code Tab
        "code_card_title": "Código on-premise",
        "code_card_desc": "Código de integración para automatización o servidor local backend en su infraestructura.",

        # Footer
        "footer_suite_text": "Lia Vault On-Premise Suite • Una solución de",

        # Tour
        "tour_step_prefix": "Paso {step} de {total}",
        "tour_btn_prev": "Anterior",
        "tour_btn_next": "Siguiente",
        "tour_btn_skip": "Omitir tour",
        "tour_btn_finish": "¡Comenzar a usar Lia!",
        "tour_1_title": "1. Seudonimización Reversible (Para interactuar con LLMs)",
        "tour_1_desc": "Arrastra documentos (PDF, DOCX, XLSX, TXT, OCR) para detectar datos sensibles. Reemplaza PII por etiquetas como [PERSONA_1] y genera un archivo .key para revertir la respuesta de ChatGPT o Claude conservando la privacidad total.",
        "tour_2_title": "2. Anonimización Irreversible (Conforme a RGPD)",
        "tour_2_desc": "Destruye y generaliza datos personales de forma 100% irreversible según el Recital 26 y guías EDPB. Permite configurar k-anonimato (k=3, 5, 10), generalización de fechas/CPs y emite Certificados de Auditoría RGPD.",
        "tour_3_title": "3. Traducción Inversa (De-seudonimización inteligente)",
        "tour_3_desc": "Pega aquí la respuesta generada por la IA o sube el documento protegido. Lia Vault aplicará la llave (.key) correspondiente para devolverle los nombres y datos reales originales en tu equipo.",
        "tour_4_title": "4. Diccionario Confidencial Corporativo",
        "tour_4_desc": "Define nombres de proyectos secretos, códigos de clientes o patentes internas. Cualquier término que añadas aquí será censurado automáticamente en todos los documentos e imágenes.",
        "tour_5_title": "5. Privacidad & Despliegue On-Premise",
        "tour_5_desc": "Todos los modelos de IA y OCR corren de forma 100% local en tu procesador/GPU. Cero fugas hacia servidores externos o la nube. ¡Disfruta de Lia Vault!",
    },
    "en": {
        # General & App Header
        "app_title": "Lia Vault - On-Premise Privacy Shield",
        "header_subtitle": "100% On-Premise Privacy & Anonymization Suite",
        "privacy_tagline": "100% Local • Zero Data Leakage • On-Premise NLP Engine",
        "lang_switch_tooltip": "Switch language / Cambiar idioma",
        "server_lan": "127.0.0.1:8502 (LAN)",
        "license_active_badge": "Active Trial ({days}d)",
        "license_invalid_badge": "Invalid License",

        # Sidebar
        "sidebar_local_features": "LOCAL FEATURES",
        "sidebar_deploy_admin": "DEPLOYMENT & ADMIN",
        "sidebar_tour_btn": "Start interactive tour",
        "sidebar_privacy_badge": "100% GUARANTEED PRIVACY",
        "sidebar_privacy_desc": "Fully local processing on your CPU/GPU. Zero external connections.",

        # Tabs & Navigation Buttons
        "tab_sanitizer": "Pseudonymization (reversible)",
        "tab_anonymizer": "Anonymization (irreversible)",
        "tab_reversion": "Reverse translation",
        "tab_dictionary": "Company dictionary",
        "tab_license": "Licenses & simulation",
        "tab_code": "On-premise code",

        # Common Actions & Buttons
        "btn_add_files": "Select files",
        "btn_clear_all": "Clear all",
        "btn_open_folder": "Open folder",
        "btn_browse": "Browse...",
        "btn_copy": "Copy to clipboard",
        "btn_copied": "Copied!",
        "btn_refresh": "Refresh",
        "btn_close": "Close",
        "btn_save": "Save",
        "btn_cancel": "Cancel",
        "btn_download": "Download",
        "btn_anonymize_row": "Anonymize",
        "btn_open_doc": "Open document",
        "btn_key_doc": ".key File",
        "btn_open": "Open",
        "btn_anon_now": "Anonymize now",
        "btn_rgpd_cert": "GDPR Certificate",
        "badge_incompatible": "Unsupported",
        "badge_new": "NEW",
        "dropzone_formats": "TXT, CSV, DOCX, XLSX, PDF, PNG/JPG",
        "dropzone_prompt": "Drag files here or click to select",
        "queue_empty_folder": "/entrada folder is empty.",

        # Sanitizer Tab (Reversible)
        "sanitizer_card_title": "File Sanitizer",
        "sanitizer_card_desc": "Drag your documents to detect sensitive data and create a protected clone ready for ChatGPT.",
        "sanitizer_btn_process": "Process entire batch",
        "sanitizer_queue_title": "READY FILES QUEUE",
        "sanitizer_queue_status": "Queue updated: {count} pending file(s).",
        "sanitizer_preview_empty_title": "No file selected",
        "sanitizer_preview_empty_desc": "Select a file to preview.",
        "sanitizer_output_title": "Safe processed files",
        "sanitizer_output_path_hint": "📍 Physical download folder on your computer: ./salida (inside project folder)",
        "sanitizer_tooltip_folder": "Open output folder in file explorer",
        "sanitizer_tooltip_folder_docker": "Direct folder access disabled in Docker (files stored in ./salida)",
        "sanitizer_no_processed": "No processed files in the output folder yet.",
        "sanitizer_status_ready": "Ready to scan and pseudonymize.",
        "sanitizer_status_processing": "Processing full batch with offline AI and OCR...",
        "sanitizer_status_completed": "Batch completed successfully ({count} files processed with their .key).",
        "sanitizer_status_error": "Execution error: {error}",

        # Anonymizer Tab (Irreversible - RGPD / GDPR)
        "anon_card_title": "GDPR Irreversible Anonymization",
        "anon_card_desc": "Irreversibly anonymizes personal data using k-anonymity and generalization compliant with GDPR.",
        "anon_btn_process": "Anonymize entire batch (Irreversible - GDPR)",
        "anon_queue_title": "FILES QUEUE (ANONYMIZATION)",
        "anon_queue_status": "Queue ready: {count} pending file(s) for anonymization.",
        "anon_k_label": "k-Anonymity Level (Tables)",
        "anon_k_3": "k = 3 (Internal use / Retention)",
        "anon_k_5": "k = 5 (Third-party sharing / AI Models)",
        "anon_k_10": "k = 10 (Maximum protection)",
        "anon_quasi_label": "Generalize quasi-identifiers (Dates to years, truncated Postal Codes)",
        "anon_output_title": "OUTPUT FOLDER: GDPR ANONYMIZED FILES",
        "anon_output_path": "Path: {path}",
        "anon_tooltip_folder": "Open anonymized files folder",
        "anon_no_processed": "No anonymized documents in the output folder yet.",
        "anon_status_ready": "Ready to anonymize irreversibly (GDPR).",
        "anon_status_processing": "Running GDPR irreversible anonymization...",
        "anon_status_completed": "Anonymization completed ({count} files processed with GDPR certificate).",
        "anon_status_error": "Anonymization error: {error}",

        # Reversion Tab (Reverse Translation)
        "reversion_card_title": "Smart Reverse Translation",
        "reversion_card_desc": "Paste the response or upload the AI generated file. Select the source document and Lia Vault will apply its (.key) automatically.",
        "reversion_dd_label": "Source processed document",
        "reversion_btn_load_key": "Load manual .key",
        "reversion_btn_load_ai_doc": "Load AI response file",
        "reversion_txt_no_doc": "No file loaded",
        "reversion_txt_key_auto": "Select the source document above to automatically use its key",
        "reversion_hint_input": "Paste the text or response generated by AI here...",
        "reversion_btn_restore": "De-anonymize and revert",
        "reversion_btn_clear": "Clear fields",
        "reversion_output_label": "Original restored response:",
        "reversion_output_hint": "Response result with restored real data...",
        "reversion_btn_save_file": "Save response to file",
        "reversion_status_processing": "Processing de-anonymization with .key cryptographic key...",
        "reversion_status_completed": "De-anonymization completed successfully.",

        # Corporate Dictionary Tab
        "dict_card_title": "Corporate Confidential Dictionary",
        "dict_card_desc": "Terms added here are automatically censored with [CONFIDENCIAL] across all documents and images.",
        "dict_tf_hint": "Prohibited term...",
        "dict_btn_add": "Add",
        "dict_btn_import": "Import .txt",
        "dict_current_terms": "Current terms (click 'X' to delete):",

        # License Tab
        "license_card_title": "On-Premise License Management",
        "license_card_desc": "Offline validation details for current Lia Vault license.",
        "license_client_label": "Client ID:",
        "license_trial_days": "Trial days remaining: {days} days",
        "license_status_text": "Official status: {status}",
        "license_valid_msg": "✅ Valid license for {client}. {days} trial days remaining.",
        "license_invalid_msg": "❌ Invalid or expired license.",

        # Code Tab
        "code_card_title": "On-Premise Code",
        "code_card_desc": "Integration code for automation or local backend server on your infrastructure.",

        # Footer
        "footer_suite_text": "Lia Vault On-Premise Suite • A solution by",

        # Tour
        "tour_step_prefix": "Step {step} of {total}",
        "tour_btn_prev": "Previous",
        "tour_btn_next": "Next",
        "tour_btn_skip": "Skip tour",
        "tour_btn_finish": "Start using Lia!",
        "tour_1_title": "1. Reversible Pseudonymization (For LLM Interactions)",
        "tour_1_desc": "Drag documents (PDF, DOCX, XLSX, TXT, OCR) to detect sensitive data. Replaces PII with tokens like [PERSONA_1] and generates a .key file to reverse ChatGPT or Claude responses with total privacy.",
        "tour_2_title": "2. Irreversible Anonymization (GDPR Compliant)",
        "tour_2_desc": "Permanently destroys and generalizes personal data following Recital 26 and EDPB guidelines. Supports k-anonymity (k=3, 5, 10), date/postal code generalization, and issues GDPR Audit Certificates.",
        "tour_3_title": "3. Reverse Translation (Smart De-pseudonymization)",
        "tour_3_desc": "Paste the AI generated response or upload the protected file. Lia Vault will apply the corresponding (.key) to restore original real names and data locally on your computer.",
        "tour_4_title": "4. Corporate Confidential Dictionary",
        "tour_4_desc": "Define secret project names, client codes, or internal patents. Any term added here will be automatically censored across all documents and images.",
        "tour_5_title": "5. On-Premise Privacy & Deployment",
        "tour_5_desc": "All AI and OCR models run 100% locally on your processor/GPU. Zero data leakage to external cloud servers. Enjoy Lia Vault!",
    }
}


def detect_system_language() -> str:
    """Detecta el idioma del sistema operativo (en o es)."""
    try:
        lang, _ = locale.getdefaultlocale()
        if lang and lang.lower().startswith("en"):
            return "en"
    except Exception:
        pass
    try:
        env_lang = os.getenv("LANG", "") or os.getenv("LC_ALL", "")
        if env_lang.lower().startswith("en"):
            return "en"
    except Exception:
        pass
    return "es"


def load_saved_language() -> str:
    """Carga el idioma guardado en config/settings.json o detecta el del SO."""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "language" in data and data["language"] in TRANSLATIONS:
                    return data["language"]
    except Exception:
        pass
    return detect_system_language()


def save_language(lang: str):
    """Guarda el idioma en config/settings.json."""
    global CURRENT_LANG
    CURRENT_LANG = lang if lang in TRANSLATIONS else "es"
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        data = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data["language"] = CURRENT_LANG
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardando idioma: {e}")


def get_current_language() -> str:
    """Obtiene el idioma actual configurado."""
    return CURRENT_LANG


def set_current_language(lang: str):
    """Establece el idioma actual y lo persiste."""
    save_language(lang)


def t(key: str, lang: str = None, **kwargs) -> str:
    """
    Obtiene la traducción para una clave dada en el idioma actual o especificado.
    Admite interpolación de variables via kwargs (ej. t('tour_step_prefix', step=1, total=5)).
    """
    target_lang = lang or CURRENT_LANG
    lang_dict = TRANSLATIONS.get(target_lang, TRANSLATIONS.get("es", {}))
    text = lang_dict.get(key, TRANSLATIONS.get("es", {}).get(key, key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

# Inicializar idioma detectado / guardado
CURRENT_LANG = load_saved_language()
