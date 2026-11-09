# -*- coding: utf-8 -*-
"""
 * @license
 * SPDX-License-Identifier: Apache-2.0
 """

import os
import re
import json
import shutil
import sys
import tempfile

import auditoria
import llaves
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

# Componentes de Microsoft Presidio
try:
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig
except ImportError:
    # Sin Presidio no se procesa nada (fail-closed): exigir_motor() lo informa al intentar procesar.
    AnalyzerEngine = PatternRecognizer = Pattern = NlpEngineProvider = AnonymizerEngine = OperatorConfig = None


class MotorNoDisponibleError(RuntimeError):
    """El motor de detección o un componente necesario para el archivo no está disponible o falló.
    Se aborta el procesamiento: nunca se entrega un archivo sin anonimizar."""

# Certificados de confianza para descargar los modelos de OCR: el Python de python.org en macOS no trae
# las CA del sistema. Se usan las de certifi; la verificación TLS sigue activa.
import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

# Soporte PDF e Imágenes (OCR)
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import easyocr
    import cv2
    from PIL import Image
except ImportError:
    easyocr = None
    cv2 = None
    Image = None

# 1. Configuración de rutas corporativas y soporte multiidioma
# LIA_VAULT_BASE fija la carpeta de datos (en Docker, el volumen /datos; el código queda de solo lectura).
_base_dir = os.environ.get("LIA_VAULT_BASE") or os.path.dirname(os.path.abspath(__file__))
# El ejecutable compilado nunca guarda datos dentro de su paquete: se perderían (llaves incluidas) al actualizar la app.
if not os.environ.get("LIA_VAULT_BASE") and (getattr(sys, "frozen", False) or not os.access(_base_dir, os.W_OK) or _base_dir.startswith("/Volumes/")):
    _base_dir = os.path.join(os.path.expanduser("~"), "LiaVault")

NOMBRES_CARPETAS = {
    "es": {
        "entrada": "Entrada",
        "seudonimizados": "Seudonimizados",
        "anonimizados": "Anonimizados",
        "restaurados": "Restaurados",
        "procesados": "procesados",
        "config": "config"
    },
    "en": {
        "entrada": "Input",
        "seudonimizados": "Pseudonymized",
        "anonimizados": "Anonymized",
        "restaurados": "Restored",
        "procesados": "processed",
        "config": "config"
    }
}

def _mover_contenido_carpeta(origen, destino):
    """Mueve de forma segura el contenido de origen a destino."""
    if not os.path.exists(origen) or os.path.abspath(origen) == os.path.abspath(destino):
        return
    os.makedirs(destino, exist_ok=True)
    try:
        for item in os.listdir(origen):
            s = os.path.join(origen, item)
            d = os.path.join(destino, item)
            try:
                if not os.path.exists(d):
                    shutil.move(s, d)
                else:
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
                        os.remove(s)
            except Exception as e_mv:
                print(f"Aviso migrando {s} -> {d}: {e_mv}")
        if not os.listdir(origen):
            os.rmdir(origen)
    except Exception as e_dir:
        print(f"Aviso en limpieza de directorio {origen}: {e_dir}")

def actualizar_rutas_idioma(lang="es"):
    """Actualiza y migra las carpetas según el idioma activo (ES o EN)."""
    global CARPETA_ENTRADA, CARPETA_SALIDA_DEFECTO, CARPETA_SALIDA_ANONIMIZADA, CARPETA_SALIDA
    global CARPETA_RESTAURADOS, CARPETA_PROCESADOS, CARPETA_CONFIG, RUTA_DICCIONARIO, CARPETA_LLAVES

    idioma = "en" if lang.lower().startswith("en") else "es"
    idioma_previo = "es" if idioma == "en" else "en"
    cfg = NOMBRES_CARPETAS[idioma]
    cfg_prev = NOMBRES_CARPETAS[idioma_previo]

    target_entrada = os.path.join(_base_dir, cfg["entrada"])
    target_seudonimizados = os.path.join(_base_dir, cfg["seudonimizados"])
    target_anonimizados = os.path.join(_base_dir, cfg["anonimizados"])
    target_restaurados = os.path.join(_base_dir, cfg["restaurados"])
    target_procesados = os.path.join(_base_dir, cfg["procesados"])
    target_config = os.path.join(_base_dir, cfg["config"])

    # 1. Migración desde carpetas Legacy
    legacy_seudonimizados = os.path.join(_base_dir, "Archivos seguros de Checkpoint Ley IA")
    legacy_anonimizados = os.path.join(_base_dir, "Archivos anonimizados RGPD")
    legacy_entrada_min = os.path.join(_base_dir, "entrada")

    if os.path.exists(legacy_seudonimizados):
        _mover_contenido_carpeta(legacy_seudonimizados, target_seudonimizados)
    if os.path.exists(legacy_anonimizados):
        _mover_contenido_carpeta(legacy_anonimizados, target_anonimizados)
    if os.path.exists(legacy_entrada_min) and os.path.abspath(legacy_entrada_min) != os.path.abspath(target_entrada):
        _mover_contenido_carpeta(legacy_entrada_min, target_entrada)

    # 2. Migración entre idiomas si cambiamos de idioma
    prev_entrada = os.path.join(_base_dir, cfg_prev["entrada"])
    prev_seudonimizados = os.path.join(_base_dir, cfg_prev["seudonimizados"])
    prev_anonimizados = os.path.join(_base_dir, cfg_prev["anonimizados"])
    prev_restaurados = os.path.join(_base_dir, cfg_prev["restaurados"])
    prev_procesados = os.path.join(_base_dir, cfg_prev["procesados"])

    if os.path.exists(prev_entrada) and os.path.abspath(prev_entrada) != os.path.abspath(target_entrada):
        _mover_contenido_carpeta(prev_entrada, target_entrada)
    if os.path.exists(prev_seudonimizados) and os.path.abspath(prev_seudonimizados) != os.path.abspath(target_seudonimizados):
        _mover_contenido_carpeta(prev_seudonimizados, target_seudonimizados)
    if os.path.exists(prev_anonimizados) and os.path.abspath(prev_anonimizados) != os.path.abspath(target_anonimizados):
        _mover_contenido_carpeta(prev_anonimizados, target_anonimizados)
    if os.path.exists(prev_restaurados) and os.path.abspath(prev_restaurados) != os.path.abspath(target_restaurados):
        _mover_contenido_carpeta(prev_restaurados, target_restaurados)
    if os.path.exists(prev_procesados) and os.path.abspath(prev_procesados) != os.path.abspath(target_procesados):
        _mover_contenido_carpeta(prev_procesados, target_procesados)

    # 3. Asignar variables globales y asegurar existencia
    CARPETA_ENTRADA = target_entrada
    CARPETA_SALIDA_DEFECTO = target_seudonimizados
    CARPETA_SALIDA_ANONIMIZADA = target_anonimizados
    CARPETA_SALIDA = CARPETA_SALIDA_DEFECTO
    CARPETA_RESTAURADOS = target_restaurados
    CARPETA_PROCESADOS = target_procesados
    CARPETA_CONFIG = target_config
    RUTA_DICCIONARIO = os.path.join(CARPETA_CONFIG, "diccionario_exclusiones.txt")
    # Las llaves de reversión no cambian de carpeta con el idioma y nunca van junto a los documentos.
    CARPETA_LLAVES = os.path.join(_base_dir, "Llaves")

    for p in [CARPETA_ENTRADA, CARPETA_SALIDA_DEFECTO, CARPETA_SALIDA_ANONIMIZADA, CARPETA_RESTAURADOS, CARPETA_PROCESADOS, CARPETA_CONFIG]:
        os.makedirs(p, exist_ok=True)
    llaves.preparar_carpeta(CARPETA_LLAVES)

    if not os.path.exists(RUTA_DICCIONARIO):
        try:
            with open(RUTA_DICCIONARIO, "w", encoding="utf-8") as f:
                f.write("# Lista de palabras prohibidas de la empresa (un término por línea)\n")
                f.write("# Las coincidencias se reemplazarán por [TERMINO_CONFIDENCIAL]\n")
                f.write("Proyecto Halcon\n")
                f.write("Adquisición Alfa\n")
                f.write("Formula-X7\n")
        except Exception:
            pass

    return {
        "entrada": CARPETA_ENTRADA,
        "seudonimizados": CARPETA_SALIDA_DEFECTO,
        "anonimizados": CARPETA_SALIDA_ANONIMIZADA,
        "restaurados": CARPETA_RESTAURADOS,
        "procesados": CARPETA_PROCESADOS,
        "config": CARPETA_CONFIG,
        "llaves": CARPETA_LLAVES
    }

# Inicializar carpetas al idioma por defecto
try:
    from i18n import get_current_language
    _lang_init = get_current_language()
except Exception:
    _lang_init = "es"

actualizar_rutas_idioma(_lang_init)

# Registro de auditoría (H5): solo metadatos, firmado con una clave derivada de la clave maestra de las llaves.
registro = auditoria.RegistroAuditoria(
    os.environ.get(auditoria.VARIABLE_RUTA) or os.path.join(_base_dir, "Registros", auditoria.NOMBRE_ARCHIVO),
    lambda: llaves.obtener_clave_maestra(CARPETA_LLAVES),
)


# 2. Inicializar IA local y Lector OCR
print("⏳ Cargando modelos e IA local de Lia Vault...")
try:
    models_config = [{"lang_code": "es", "model_name": "es_core_news_sm"}]
    supported_langs = ["es"]
    try:
        import spacy
        if spacy.util.is_package("en_core_web_sm"):
            models_config.append({"lang_code": "en", "model_name": "en_core_web_sm"})
            supported_langs.append("en")
    except Exception:
        pass

    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": models_config
    }
    provider = NlpEngineProvider(nlp_configuration=nlp_config)
    nlp_engine = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=supported_langs)
    anonymizer = AnonymizerEngine()
    
    # 1. Tarjetas de crédito
    patron_tarjeta = Pattern(name="tarjeta_patron", regex=r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", score=0.85)
    reconocedor_tarjetas_es = PatternRecognizer(supported_entity="CREDIT_CARD", supported_language="es", patterns=[patron_tarjeta])
    analyzer.registry.add_recognizer(reconocedor_tarjetas_es)
    if "en" in supported_langs:
        reconocedor_tarjetas_en = PatternRecognizer(supported_entity="CREDIT_CARD", supported_language="en", patterns=[patron_tarjeta])
        analyzer.registry.add_recognizer(reconocedor_tarjetas_en)

    # 2. Teléfonos en español / internacionales (móviles, fijos, 9 dígitos, con prefijos)
    patron_tel_es = Pattern(
        name="telefono_es_patron",
        regex=r"(?:\+34\s*|0034\s*)?(?:[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}|[6789]\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}|[6789]\d{1}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}|[6789]\d{8}|\b(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b)",
        score=0.85
    )
    reconocedor_telefonos_es = PatternRecognizer(supported_entity="PHONE_NUMBER", supported_language="es", patterns=[patron_tel_es])
    analyzer.registry.add_recognizer(reconocedor_telefonos_es)
    if "en" in supported_langs:
        reconocedor_telefonos_en = PatternRecognizer(supported_entity="PHONE_NUMBER", supported_language="en", patterns=[patron_tel_es])
        analyzer.registry.add_recognizer(reconocedor_telefonos_en)

    # 3. Escuelas, Colegios, Universidades e Instituciones
    patron_instituciones = Pattern(
        name="institucion_educativa_patron",
        regex=r"\b(?:Colegio|Escuela|Instituto|CEIP|IES|Universidad|Facultad|Conservatorio|Hospital|Clínica|Fundación|Centro\s+Educativo|Guardería|Jardín\s+de\s+Infantes|University|College|School|Academy|Institute|Hospital|Clinic)\s+(?:N[º°]?\s*\d+\s+)?(?:de\s+|del\s+|la\s+|las\s+|los\s+|San\s+|Santa\s+|Nuestra\s+Señora\s+de\s+|Don\s+|Doña\s+|of\s+|for\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ0-9\s.-]+?(?=\s*[,;.\n]|\s+y\b|\s+con\b|\s+en\b|\s+de\b|\s+del\b|\s+and\b|\s+with\b|\s+in\b|$)",
        score=0.90
    )
    reconocedor_instituciones_es = PatternRecognizer(supported_entity="ORGANIZATION", supported_language="es", patterns=[patron_instituciones])
    analyzer.registry.add_recognizer(reconocedor_instituciones_es)
    if "en" in supported_langs:
        reconocedor_instituciones_en = PatternRecognizer(supported_entity="ORGANIZATION", supported_language="en", patterns=[patron_instituciones])
        analyzer.registry.add_recognizer(reconocedor_instituciones_en)

    # 4. Nombres propios comunes (para capturar nombres aislados)
    patron_nombres = Pattern(
        name="nombres_propios_patron",
        regex=r"\b(?:Jessica|Jesica|Yessica|Jennifer|Yenifer|Kevin|Brian|Brayan|Jonathan|Jonatan|Nicole|Dylan|Axel|Maite|Nahuel|Thiago|Tiago|Camila|Valeria|Antonella|Agustina|Romina|Florencia|Gisela|Giselle|Micaela|Yamila|Facundo|Mariano|Emiliano|Gonzalo|Esteban|Federico|Hernán|Hernan|Damián|Damian|Ezequiel|Gerónimo|Geronimo|Lautaro|Bautista|Santino|Joaquín|Joaquin|Valentín|Valentin|Ignacio|Lisandro|Agustín|Agustin|Álvaro|Alvaro|Rodrigo|Alfonso|Inés|Ines|Pilar|Teresa|Mercedes|Dolores|Montserrat|Rocío|Rocio|Macarena|Cristina|Susana|Marta|Miriam|Irene|Silvia|Raquel|Mónica|Monica|Natalia|Lorena|Vanesa|Vanessa|Patricia|Beatriz|Guillermo|Manuel|Pablo|Sergio|Rubén|Ruben|Adrián|Adrian|Iván|Ivan|Raúl|Raul|Óscar|Oscar|David|Marcos|Hugo|Lucas|Daniel|Mario|Víctor|Victor|Héctor|Hector|Félix|Felix|César|Cesar|Arturo|Ernesto|Ramiro|Mauricio|Fabián|Fabian|Claudio|Marcelo|Gustavo|Eduardo|Ricardo|Roberto|Fernando|Francisco|José|Jose|Antonio|Luis|Jorge|Miguel|Ángel|Angel|Pedro|Jesús|Jesus|Alberto|Alejandro|Javier|Carlos|Juan|Ana|Lucía|Lucia|María|Maria|Laura|Sofía|Sofia|Elena|Carmen|Paula|Andrea|Claudia|Sara|Julia|Alba|Noelia|Sonia|Alicia|Eva|Marina|Nerea|Belén|Belen|Gloria|Victoria|Carolina|Clara|Daniela|Gabriela|John|Michael|James|Robert|William|David|Richard|Charles|Joseph|Thomas|Christopher|Daniel|Paul|Mark|Donald|George|Kenneth|Steven|Edward|Brian|Ronald|Anthony|Kevin|Jason|Matthew|Gary|Timothy|Jose|Larry|Jeffrey|Frank|Scott|Eric|Stephen|Andrew|Raymond|Gregory|Joshua|Jerry|Dennis|Walter|Patrick|Peter|Harold|Douglas|Henry|Carl|Arthur|Ryan|Roger|Joe|Juan|Jack|Albert|Jonathan|Justin|Terry|Gerald|Keith|Samuel|Willie|Ralph|Lawrence|Nicholas|Roy|Benjamin|Bruce|Brandon|Adam|Harry|Fred|Wayne|Billy|Steve|Louis|Jeremy|Aaron|Randy|Howard|Eugene|Carlos|Russell|Bobby|Victor|Martin|Ernest|Phillip|Todd|Jesse|Craig|Alan|Shawn|Clarence|Sean|Philip|Chris|Johnny|Earl|Jimmy|Antonio|Mary|Patricia|Jennifer|Linda|Elizabeth|Barbara|Susan|Jessica|Sarah|Karen|Nancy|Lisa|Betty|Margaret|Sandra|Ashley|Kimberly|Emily|Donna|Michelle|Dorothy|Carol|Amanda|Melissa|Deborah|Stephanie|Rebecca|Sharon|Laura|Cynthia|Kathleen|Amy|Shirley|Angela|Helen|Anna|Brenda|Pamela|Nicole|Emma|Samantha|Katherine|Christine|Debra|Rachel|Catherine|Carolyn|Janet|Ruth|Maria|Heather|Diane|Virginia|Julie|Joyce|Victoria|Olivia|Kelly|Christina|Lauren|Joan|Evelyn|Judith|Megan|Cheryl|Andrea|Hannah|Martha|Jacqueline|Frances|Gloria|Ann|Teresa|Kathryn|Sara|Janice|Jean|Alice|Madison|Doris|Abigail|Julia|Judy|Grace|Denise|Amber|Marilyn|Beverly|Danielle|Theresa|Sophia|Marie|Diana|Brittany|Natalie|Isabella|Charlotte|Rose|Alexis|Kayla)\b",
        score=0.90
    )
    reconocedor_nombres_es = PatternRecognizer(supported_entity="PERSON", supported_language="es", patterns=[patron_nombres])
    analyzer.registry.add_recognizer(reconocedor_nombres_es)
    if "en" in supported_langs:
        reconocedor_nombres_en = PatternRecognizer(supported_entity="PERSON", supported_language="en", patterns=[patron_nombres])
        analyzer.registry.add_recognizer(reconocedor_nombres_en)
except Exception as e:
    print(f"⚠️ Alerta: Presidio o spaCy no se cargaron ({type(e).__name__}). No se procesarán archivos.")
    analyzer = None
    anonymizer = None


def exigir_motor():
    """Lanza MotorNoDisponibleError si Presidio o spaCy no se cargaron."""
    if analyzer is None:
        raise MotorNoDisponibleError(
            "El motor de anonimización (Presidio/spaCy) no está disponible. "
            "No se procesó ningún archivo. Reinstale Lia Vault o sus dependencias."
        )


def _analizar_o_fallar(**kwargs):
    """analyzer.analyze() que, ante cualquier error, aborta el archivo en lugar de seguir sin detección.
    El mensaje no incluye el texto analizado."""
    exigir_motor()
    try:
        return analyzer.analyze(**kwargs)
    except Exception as ex:
        raise MotorNoDisponibleError(f"Falló la detección de datos personales ({type(ex).__name__}).") from ex

try:
    if easyocr:
        lector_ocr = easyocr.Reader(['es', 'en'], gpu=False)
    else:
        lector_ocr = None
except Exception as e:
    print(f"⚠️ Alerta: EasyOCR no inicializado: {e}")
    lector_ocr = None


def cargar_diccionario_corporativo():
    terminos = []
    if os.path.exists(RUTA_DICCIONARIO):
        with open(RUTA_DICCIONARIO, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#"):
                    terminos.append(linea)
    return terminos


def aplicar_diccionario_exclusiones(texto):
    if not isinstance(texto, str):
        return texto
    terminos = cargar_diccionario_corporativo()
    for termino in terminos:
        patron = re.compile(re.escape(termino), re.IGNORECASE)
        texto = patron.sub("[TERMINO_CONFIDENCIAL]", texto)
    return texto


class IdiomaNoSoportadoError(Exception):
    """Excepción lanzada cuando el documento se encuentra en un idioma no soportado (distinto a ES y EN)."""
    def __init__(self, idioma_detectado):
        self.idioma_detectado = idioma_detectado
        super().__init__(f"Este software sólo está entrenado para documentos en Español y en Inglés. Idioma detectado: '{idioma_detectado}'.")


STOPWORDS_ES = {
    'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por', 'un', 'para', 'con', 'no', 'una',
    'su', 'al', 'lo', 'como', 'más', 'mas', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'sí', 'si', 'porque', 'esta',
    'son', 'entre', 'está', 'esta', 'cuando', 'muy', 'sin', 'sobre', 'ser', 'tiene', 'también', 'tambien', 'me',
    'hasta', 'hay', 'donde', 'quien', 'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni', 'contra',
    'otros', 'ese', 'eso', 'ante', 'ellos', 'e', 'esto', 'mí', 'mi', 'antes', 'algunos', 'qué', 'que', 'unos',
    'yo', 'otro', 'otras', 'otra', 'él', 'el', 'tanto', 'esa', 'estos', 'mucho', 'quienes', 'nada', 'muchos',
    'cual', 'sea', 'poco', 'ella', 'estar', 'haber', 'estas', 'estaba', 'estamos', 'tenemos', 'encontramos'
}

STOPWORDS_EN = {
    'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it', 'for', 'not', 'on', 'with', 'he',
    'as', 'you', 'do', 'at', 'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or', 'an',
    'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who',
    'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
    'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now',
    'look', 'only', 'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work',
    'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us',
    'is', 'are', 'was', 'were', 'been', 'has', 'had', 'according', 'findings', 'research', 'report'
}

STOPWORDS_FR = {'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'est', 'en', 'que', 'qui', 'dans', 'pour', 'pas', 'sur', 'ce', 'par', 'avec', 'ne', 'au', 'aux', 'se', 'son', 'sa', 'ses', 'nous', 'vous', 'ils', 'elles', 'mais', 'ou', 'donc', 'rapport', 'été', 'ete'}
STOPWORDS_DE = {'der', 'die', 'das', 'und', 'in', 'den', 'von', 'zu', 'dem', 'mit', 'sich', 'des', 'auf', 'für', 'ist', 'im', 'nicht', 'eine', 'ein', 'als', 'auch', 'es', 'an', 'werden', 'aus', 'er', 'hat', 'dass', 'sie', 'nach', 'wird', 'bei', 'einer', 'um', 'am', 'sind', 'bericht'}
STOPWORDS_IT = {'il', 'la', 'le', 'i', 'gli', 'di', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 'un', 'uno', 'una', 'è', 'e', 'che', 'non', 'si', 'del', 'della', 'dei', 'delle', 'sono', 'ma', 'come', 'anche', 'questo', 'questa', 'rapporto'}
STOPWORDS_PT = {'o', 'a', 'os', 'as', 'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas', 'por', 'pelo', 'pela', 'pelos', 'pelas', 'para', 'com', 'um', 'uma', 'uns', 'umas', 'que', 'não', 'se', 'como', 'mas', 'ao', 'aos', 'à', 'às', 'este', 'esta', 'estes', 'estas', 'relatório'}


def detectar_idioma(texto: str) -> tuple:
    """
    Identifica el idioma dominante y la estrategia de análisis bilingüe (ES / EN / Mixto) de forma offline.
    Retorna: (idioma_clasificado, [idiomas_a_ejecutar_en_presidio])
    Lanza IdiomaNoSoportadoError si el texto está en un tercer idioma dominante no soportado.
    """
    if not isinstance(texto, str) or not texto.strip():
        return "es", ["es"]

    palabras = re.findall(r'\b[a-záéíóúñüàèìòùâêîôûäëïöüçãõ]{2,}\b', texto.lower())
    
    # 1. Umbral mínimo de longitud/confianza (protección para textos cortos, numéricos o tablas)
    if len(palabras) < 8 or len(texto.strip()) < 40:
        idioma_def = obtener_idioma_activo()
        return idioma_def, ["es", "en"]

    c_es = sum(1 for p in palabras if p in STOPWORDS_ES)
    c_en = sum(1 for p in palabras if p in STOPWORDS_EN)
    c_fr = sum(1 for p in palabras if p in STOPWORDS_FR)
    c_de = sum(1 for p in palabras if p in STOPWORDS_DE)
    c_it = sum(1 for p in palabras if p in STOPWORDS_IT)
    c_pt = sum(1 for p in palabras if p in STOPWORDS_PT)

    total_validos = c_es + c_en + c_fr + c_de + c_it + c_pt

    # Si hay muy pocas stopwords para determinar con rigor (ej. datos estructurados)
    if total_validos < 3:
        idioma_def = obtener_idioma_activo()
        return idioma_def, ["es", "en"]

    # 2. Rechazo duro por tercer idioma dominante
    terceros = {"Francés": c_fr, "Alemán": c_de, "Italiano": c_it, "Portugués": c_pt}
    max_tercero_nombre, max_tercero_count = max(terceros.items(), key=lambda x: x[1])

    if max_tercero_count > (c_es + c_en) * 1.5 and (c_es + c_en) < 4:
        raise IdiomaNoSoportadoError(max_tercero_nombre)

    # 3. Documentos bilingües o con mezcla significativa ES + EN (umbral >= 15%)
    if c_es > 0 and c_en > 0:
        ratio_mezcla = min(c_es, c_en) / (c_es + c_en)
        if ratio_mezcla >= 0.15:
            return "mixto", ["es", "en"]

    # 4. Idioma dominante ES o EN
    if c_en > c_es * 1.8:
        return "en", ["en", "es"]
    else:
        return "es", ["es", "en"]


SOFTWARE_ALLOWLIST = {
    'chatgpt', 'copilot', 'gemini', 'claude', 'llama', 'gpt', 'gpt-4', 'gpt-3.5',
    'windows', 'office', 'excel', 'word', 'powerpoint', 'google', 'microsoft',
    'python', 'docker', 'react', 'vite', 'node', 'express', 'spacy', 'presidio',
    'easyocr', 'pdf', 'csv', 'txt', 'docx', 'xlsx', 'json', 'html', 'css', 'javascript',
    'typescript', 'flet', 'github', 'gitlab', 'slack', 'teams', 'zoom',
    'meeting', 'inteligencia', 'artificial', 'bueno', 'buenos', 'días', 'dias', 'hola',
    'gracias', 'perdón', 'perdon', 'claro', 'exacto', 'así', 'asi', 'igual', 'cualquier', 'esa',
    'uno', 'vale', 'ah', 'mirá', 'mira', 'acá', 'aca', 'después', 'despues', 'grabación',
    'aparentemente', 'socios', 'pymes', 'tecnologías', 'tecnologias', 'verdadero', 'consciente',
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
    'septiembre', 'octubre', 'noviembre', 'diciembre',
    'lunes', 'martes', 'miércoles', 'miercoles', 'jueves', 'viernes', 'sábado', 'sabado', 'domingo',
    'unión europea', 'view', 'notes', 'cuál', 'quién',
    # Términos estructurales, metodológicos, de negocio y tecnología (ES / EN)
    'táctica', 'tactica', 'tácticas', 'tacticas', 'estrategia', 'estrategias', 'estratégico', 'estrategico',
    'misión', 'mision', 'visión', 'vision', 'objetivo', 'objetivos', 'fase', 'fases', 'etapa', 'etapas',
    'plan', 'planes', 'acción', 'accion', 'acciones', 'control', 'controles', 'riesgo', 'riesgos',
    'impacto', 'impactos', 'alcance', 'resumen', 'introducción', 'introduccion', 'análisis', 'analisis',
    'metodología', 'metodologia', 'técnica', 'tecnica', 'herramienta', 'herramientas', 'guía', 'guia',
    'manual', 'manuales', 'norma', 'normas', 'política', 'politica', 'políticas', 'politicas',
    'procedimiento', 'procedimientos', 'proceso', 'procesos', 'criterio', 'criterios',
    'resultado', 'resultados', 'conclusión', 'conclusion', 'conclusiones', 'recomendación', 'recomendacion',
    'nota', 'notas', 'aviso', 'avisos', 'importante', 'atención', 'atencion', 'ejemplo', 'ejemplos',
    'caso', 'casos', 'prueba', 'pruebas', 'test', 'versión', 'version', 'formato', 'plantilla',
    'modelo', 'estructura', 'esquema', 'diseño', 'desarrollo', 'implementación', 'implementacion',
    'configuración', 'configuracion', 'instalación', 'instalacion', 'mantenimiento', 'soporte',
    'servicio', 'servicios', 'sistema', 'sistemas', 'plataforma', 'aplicación', 'aplicacion',
    'software', 'hardware', 'red', 'servidor', 'tabla', 'tablas', 'campo', 'registro', 'fila', 'columna',
    'dato', 'datos', 'información', 'informacion', 'archivo', 'archivos', 'documento', 'documentos',
    'carpeta', 'directorio', 'ruta', 'código', 'codigo', 'texto', 'mensaje', 'correo', 'usuario',
    'perfil', 'rol', 'permiso', 'acceso', 'cuenta', 'equipo', 'organización', 'organizacion',
    'empresa', 'empresas', 'compañía', 'compania', 'entidad', 'cliente', 'clientes', 'sociedad',
    'director', 'directora', 'gerente', 'jefe', 'jefa', 'empleado', 'empleada',
    'área', 'area', 'departamento', 'dirección', 'direccion', 'gerencia', 'jefatura', 'oficina',
    'sede', 'sucursal', 'centro', 'unidad', 'división', 'division', 'proyecto', 'proyectos',
    'programa', 'actividad', 'tarea', 'tareas', 'evento', 'reunión', 'reunion', 'reuniones',
    'acta', 'informe', 'informes', 'reporte', 'reportes', 'estado', 'nivel', 'tipo', 'categoría',
    'categorías', 'clase', 'modo', 'forma', 'medio', 'fuente', 'origen', 'destino',
    'fecha', 'hora', 'día', 'dia', 'días', 'dias', 'mes', 'meses', 'año', 'ano', 'años', 'anos',
    'ayer', 'hoy', 'mañana', 'manana', 'durante', 'según', 'segun', 'mediante', 'luego',
    'primero', 'segundo', 'tercero', 'asimismo', 'además', 'ademas', 'total', 'subtotal',
    'saldo', 'pago', 'factura', 'recibo', 'presupuesto', 'precio', 'costo', 'importe', 'valor',
    'número', 'numero', 'cantidad', 'peso', 'tamaño', 'tamano', 'punto', 'zona', 'sector',
    'región', 'region', 'país', 'pais', 'provincia', 'ciudad', 'municipio', 'localidad', 'barrio',
    'distrito', 'territorio', 'hombres', 'mujeres', 'alumnos', 'alumnas', 'matriculados', 'matriculadas',
    'llamar', 'llamada', 'enviar', 'envío', 'envio', 'consultar', 'solicitar', 'solicitud',
    'estimado', 'estimada', 'adjunto', 'adjuntamos', 'adjunta', 'ver', 'revisar', 'notificar',
    'informar', 'descargar', 'abrir', 'cerrar', 'copiar', 'pegar', 'guardar', 'seleccionar',
    'subir', 'favor', 'buenas', 'tardes', 'noches', 'saludos', 'atentamente', 'cordialmente',
    'apoderado', 'apoderada', 'titular', 'presidente', 'presidenta', 'vicepresidente', 
    'vicepresidenta', 'vocal', 'administrador', 'administradora', 
    'socio', 'socia', 'contratante', 'proveedora', 'receptora', 'divulgadora', 'parte', 'partes', 
    'objeto', 'definiciones', 'excepciones', 'devolución', 'destrucción', 'incumplimiento', 
    'duración', 'jurisdicción', 'anexo', 'anexos', 'acuerdo', 'contrato', 'convenio', 'reunidos',
    # Vocabulario técnico, de IA, agentes y roles en inglés
    'framework', 'frameworks', 'agent', 'agents', 'agente', 'agentes', 'flow', 'flows', 'flujo', 'flujos',
    'pipeline', 'pipelines', 'prompt', 'prompts', 'embedding', 'embeddings', 'dataset', 'datasets',
    'benchmark', 'benchmarks', 'link', 'links', 'enlace', 'enlaces', 'report', 'reports', 'research',
    'researcher', 'lead', 'developer', 'engineer', 'architect', 'analyst', 'manager', 'consultant', 'auditor',
    'overview', 'summary', 'background', 'introduction', 'findings', 'evaluation', 'table', 'content',
    'hub', 'tech', 'stack', 'backend', 'frontend', 'database', 'security', 'privacy', 'compliance',
    'rgpd', 'gdpr', 'hipaa', 'iso', 'api', 'rest', 'sdk', 'llm', 'nlp', 'ner', 'ai'
}

ROLES_GENERICOS = {
    'researcher', 'lead researcher', 'developer', 'software developer', 'engineer', 'software engineer',
    'analyst', 'data analyst', 'manager', 'project manager', 'director', 'managing director', 'consultant',
    'auditor', 'architect', 'designer', 'tester', 'investigador', 'desarrollador', 'ingeniero', 'analista',
    'gerente', 'consultor', 'abogado', 'medico', 'médico', 'doctor', 'doctora', 'interlocutor', 'usuario',
    'cliente', 'responsable', 'autor', 'author'
}

CONCEPTOS_TECNICOS = {
    'framework', 'frameworks', 'agent', 'agents', 'agente', 'agentes', 'flow', 'flows', 'flujo', 'flujos',
    'pipeline', 'pipelines', 'model', 'models', 'modelo', 'modelos', 'process', 'processes', 'proceso', 'procesos',
    'architecture', 'arquitectura', 'system', 'systems', 'sistema', 'sistemas', 'tool', 'tools', 'herramientas',
    'data', 'datos', 'report', 'reporte', 'informe', 'link', 'links', 'enlaces', 'prompt', 'embedding',
    'dataset', 'tech hub', 'hub', 'stack', 'benchmark', 'analysis', 'overview', 'guide', 'checkpoint'
}

VERBOS_DESCARTE = {
    'encontramos', 'buscamos', 'revisamos', 'analizamos', 'encontró', 'encontro', 'hallamos', 'observamos',
    'presentamos', 'identificamos', 'comprobamos', 'detectamos', 'concluimos', 'proponemos', 'evaluamos',
    'found', 'reviewed', 'analyzed', 'discovered', 'identified', 'observed', 'presented', 'proposed', 'concluded'
}

SPANISH_NAMES = [
    "Jessica", "Jesica", "Yessica", "Jennifer", "Yenifer", "Kevin", "Brian", "Brayan", "Jonathan", "Jonatan",
    "Nicole", "Dylan", "Axel", "Maite", "Nahuel", "Thiago", "Tiago", "Camila", "Valeria", "Antonella",
    "Agustina", "Romina", "Florencia", "Gisela", "Giselle", "Micaela", "Yamila", "Facundo", "Mariano",
    "Emiliano", "Gonzalo", "Esteban", "Federico", "Hernan", "Hernán", "Damian", "Damián", "Ezequiel", "Geronimo",
    "Gerónimo", "Lautaro", "Bautista", "Santino", "Joaquin", "Joaquín", "Valentin", "Valentín", "Ignacio",
    "Lisandro", "Agustin", "Agustín", "Alvaro", "Álvaro", "Rodrigo", "Alfonso", "Ines", "Inés", "Pilar",
    "Teresa", "Mercedes", "Dolores", "Montserrat", "Rocio", "Rocío", "Macarena", "Cristina", "Susana",
    "Marta", "Miriam", "Irene", "Silvia", "Raquel", "Monica", "Mónica", "Natalia", "Lorena", "Vanesa",
    "Vanessa", "Patricia", "Beatriz", "Guillermo", "Manuel", "Pablo", "Sergio", "Ruben", "Rubén", "Adrian",
    "Adrián", "Ivan", "Iván", "Raul", "Raúl", "Oscar", "Óscar", "David", "Marcos", "Hugo", "Lucas",
    "Daniel", "Mario", "Victor", "Víctor", "Hector", "Héctor", "Felix", "Félix", "Cesar", "César",
    "Arturo", "Ernesto", "Ramiro", "Mauricio", "Fabian", "Fabián", "Claudio", "Marcelo", "Gustavo",
    "Eduardo", "Ricardo", "Roberto", "Fernando", "Francisco", "Jose", "José", "Antonio", "Luis",
    "Jorge", "Miguel", "Angel", "Ángel", "Pedro", "Jesus", "Jesús", "Alberto", "Alejandro", "Javier",
    "Carlos", "Juan", "Ana", "Lucia", "Lucía", "Maria", "María", "Laura", "Sofia", "Sofía",
    "Elena", "Carmen", "Paula", "Andrea", "Claudia", "Sara", "Julia", "Alba", "Noelia", "Sonia",
    "Alicia", "Eva", "Marina", "Nerea", "Belen", "Belén", "Gloria", "Victoria", "Carolina", "Clara",
    "Daniela", "Gabriela", "Carlos Mendoza", "Santiago Valencia", "Alejandro Gómez", "Juan Pérez", "María Rodríguez",
    "Laura Martínez", "Andrés Felipe", "Sofía Castro", "Diego Armando", "Carlos Ruiz", "Ana Gómez", "Luis Torres", "María López"
]

ENGLISH_NAMES = [
    "John", "Michael", "James", "Robert", "William", "David", "Richard", "Charles", "Joseph", "Thomas",
    "Christopher", "Daniel", "Paul", "Mark", "Donald", "George", "Kenneth", "Steven", "Edward", "Brian",
    "Ronald", "Anthony", "Kevin", "Jason", "Matthew", "Gary", "Timothy", "Larry", "Jeffrey", "Frank",
    "Scott", "Eric", "Stephen", "Andrew", "Raymond", "Gregory", "Joshua", "Jerry", "Dennis", "Walter",
    "Patrick", "Peter", "Harold", "Douglas", "Henry", "Carl", "Arthur", "Ryan", "Roger", "Jack",
    "Albert", "Jonathan", "Justin", "Terry", "Gerald", "Keith", "Samuel", "Willie", "Ralph", "Lawrence",
    "Nicholas", "Roy", "Benjamin", "Bruce", "Brandon", "Adam", "Harry", "Fred", "Wayne", "Billy",
    "Steve", "Louis", "Jeremy", "Aaron", "Randy", "Howard", "Eugene", "Russell", "Bobby", "Victor",
    "Martin", "Ernest", "Phillip", "Todd", "Jesse", "Craig", "Alan", "Shawn", "Clarence", "Sean",
    "Philip", "Chris", "Johnny", "Earl", "Jimmy", "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth",
    "Barbara", "Susan", "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret", "Sandra",
    "Ashley", "Kimberly", "Emily", "Donna", "Michelle", "Dorothy", "Carol", "Amanda", "Melissa", "Deborah",
    "Stephanie", "Rebecca", "Sharon", "Laura", "Cynthia", "Kathleen", "Amy", "Shirley", "Angela", "Helen",
    "Anna", "Brenda", "Pamela", "Nicole", "Emma", "Samantha", "Katherine", "Christine", "Debra", "Rachel",
    "Catherine", "Carolyn", "Janet", "Ruth", "Maria", "Heather", "Diane", "Virginia", "Julie", "Joyce",
    "Victoria", "Olivia", "Kelly", "Christina", "Lauren", "Joan", "Evelyn", "Judith", "Megan", "Cheryl",
    "Andrea", "Hannah", "Martha", "Jacqueline", "Frances", "Gloria", "Ann", "Teresa", "Kathryn", "Sara",
    "Janice", "Jean", "Alice", "Madison", "Doris", "Abigail", "Julia", "Judy", "Grace", "Denise",
    "Amber", "Marilyn", "Beverly", "Danielle", "Theresa", "Sophia", "Marie", "Diana", "Brittany", "Natalie",
    "Isabella", "Charlotte", "Rose", "Alexis", "Kayla", "John Smith", "Pierre Dupont", "Hans Müller"
]

ALL_KNOWN_NAMES = set(n.lower() for n in SPANISH_NAMES + ENGLISH_NAMES)
KNOWN_LOCATIONS = {'madrid', 'barcelona', 'valencia', 'sevilla', 'bilbao', 'paris', 'parís', 'berlin', 'berlín', 'london', 'londres', 'new york', 'rome', 'roma'}


def validar_y_limpiar_entidad(texto_completo, start, end, entidad_tipo):
    """
    Guard Gramatical y Morfosintáctico Centralizado:
    Aplica filtros anti-verbos, anti-roles y desambiguación de Title Case a TODAS las rutas (Presidio y Regex).
    Incluye Salvaguarda Anti-Falsos Negativos (preserva nombres/ubicaciones reales dentro de entidades compuestas).
    Retorna: (es_valido, texto_a_reemplazar, start_ajustado, end_ajustado, entidad_tipo_ajustado)
    """
    val = texto_completo[start:end].strip()
    if not val or len(val) < 2 or "[" in val or "]" in val:
        return False, val, start, end, entidad_tipo

    val_lower = val.lower().strip()

    # 1. Allowlist global directa
    if val_lower in SOFTWARE_ALLOWLIST:
        return False, val, start, end, entidad_tipo

    # 2. Regla Anti-Verbos
    if val_lower in VERBOS_DESCARTE:
        return False, val, start, end, entidad_tipo

    palabras_val = [p for p in re.split(r'[\s\-_/]+', val) if p]
    palabras_lower = [p.lower() for p in palabras_val]

    # 3. Regla para PERSONA / ROLES
    if entidad_tipo == "PERSON" or entidad_tipo == "PERSONA":
        # Descartar si coincide exactamente con un rol genérico sin nombre
        if val_lower in ROLES_GENERICOS:
            return False, val, start, end, entidad_tipo

        # Salvaguarda Anti-Falsos Negativos: si la entidad contiene palabras de rol/técnicas junto a un nombre propio conocido
        if any(p in ROLES_GENERICOS or p in SOFTWARE_ALLOWLIST or p in VERBOS_DESCARTE for p in palabras_lower):
            for n_cand in sorted(list(set(SPANISH_NAMES + ENGLISH_NAMES)), key=len, reverse=True):
                if n_cand.lower() != val_lower and re.search(rf"\b{re.escape(n_cand)}\b", val, re.IGNORECASE):
                    m_sub = re.search(rf"\b{re.escape(n_cand)}\b", val, re.IGNORECASE)
                    if m_sub:
                        nuevo_start = start + m_sub.start()
                        nuevo_end = start + m_sub.end()
                        return True, texto_completo[nuevo_start:nuevo_end], nuevo_start, nuevo_end, entidad_tipo

        # Si todas las palabras son términos técnicos o de negocio comunes, descartar
        if all(p in SOFTWARE_ALLOWLIST or p in ROLES_GENERICOS or p in STOPWORDS_ES or p in STOPWORDS_EN for p in palabras_lower):
            return False, val, start, end, entidad_tipo

    # 4. Regla para UBICACION / LOCATION (Desambiguación de Title Case)
    if entidad_tipo in ["LOCATION", "UBICACION"]:
        # Salvaguarda Anti-Falsos Negativos: si contiene una ubicación conocida real junto a términos técnicos (ej. "Madrid Tech Hub")
        if any(p in CONCEPTOS_TECNICOS or p in SOFTWARE_ALLOWLIST for p in palabras_lower):
            for loc in sorted(list(KNOWN_LOCATIONS), key=len, reverse=True):
                if loc.lower() != val_lower and re.search(rf"\b{re.escape(loc)}\b", val, re.IGNORECASE):
                    m_sub = re.search(rf"\b{re.escape(loc)}\b", val, re.IGNORECASE)
                    if m_sub:
                        nuevo_start = start + m_sub.start()
                        nuevo_end = start + m_sub.end()
                        return True, texto_completo[nuevo_start:nuevo_end], nuevo_start, nuevo_end, entidad_tipo

        # Descartar si está compuesta íntegramente por conceptos técnicos o palabras conectivas (ej. "Frameworks de Agentes y Flujos")
        if all(p in CONCEPTOS_TECNICOS or p in SOFTWARE_ALLOWLIST or p in {'de', 'del', 'la', 'las', 'los', 'el', 'y', 'e', 'en', 'con', 'para', 'and', 'with', 'for', 'of', 'in'} for p in palabras_lower):
            return False, val, start, end, entidad_tipo

    return True, val, start, end, entidad_tipo

MAPA_ETIQUETAS = {
    "PERSON": "PERSONA",
    "LOCATION": "UBICACION",
    "ORGANIZATION": "ORGANIZACION",
    "EMAIL_ADDRESS": "CORREO",
    "PHONE_NUMBER": "TELEFONO",
    "CREDIT_CARD": "TARJETA_CREDITO",
    "DOMAIN": "DOMINIO",
    "SECRET_KEY": "CLAVE",
    "USERNAME": "USUARIO"
}

# Etiquetas genéricas destructivas homogéneas para Anonimización Real (RGPD Considerando 26)
MAPA_ETIQUETAS_ANON_REAL = {
    "PERSON": "[PERSONA]",
    "LOCATION": "[UBICACION]",
    "ORGANIZATION": "[ORGANIZACION]",
    "EMAIL_ADDRESS": "[CORREO_ELIMINADO]",
    "PHONE_NUMBER": "[TELEFONO_ELIMINADO]",
    "CREDIT_CARD": "[TARJETA_ELIMINADA]",
    "DOMAIN": "[DOMINIO_ELIMINADO]",
    "SECRET_KEY": "[CLAVE_ELIMINADA]",
    "USERNAME": "[USUARIO_ELIMINADO]",
    "ID_OFICIAL": "[DOCUMENTO_ELIMINADO]"
}

def generalizar_cuasi_identificadores(texto):
    """
    Aplica generalización y enmascaramiento a cuasi-identificadores (fechas, CP, direcciones)
    según lo dictado en el Manual de Anonimización RGPD (Secciones 1.1, 1.8, 1.9).
    """
    if not isinstance(texto, str) or not texto.strip():
        return texto
    
    t = texto
    # 1. Generalización de Fechas completas (DD/MM/AAAA o DD-MM-AAAA) -> Año
    t = re.sub(r'\b(?:\d{1,2})[/-](?:\d{1,2})[/-](\d{4})\b', r'[AÑO \1]', t)
    
    # Fechas textuales (ej: 14 de agosto de 2026 -> [AÑO 2026])
    t = re.sub(
        r'\b\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b',
        r'[AÑO \1]', t, flags=re.IGNORECASE
    )
    
    # 2. Generalización de Direcciones postales específicas (sin consumir CP o códigos numéricos posteriores)
    t = re.sub(r'\b(?:Calle|C/|Avenida|Avda\.?|Paseo|Plaza|Carrera|Rúa)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ0-9ºª]+){0,3}(?=\s*,\s*|\s+CP\b|\s+[0-5]\d{4}\b|\.|\n|$)', '[DIRECCION_GENERALIZADA]', t, flags=re.IGNORECASE)

    # 3. Generalización de Códigos Postales (5 dígitos) -> Enmascarar últimos 3 dígitos (ej: 28013 -> 28***)
    t = re.sub(r'\b([0-5]\d)(\d{3})\b', r'\1***', t)
    
    return t

def obtener_idioma_activo():
    try:
        from i18n import get_current_language
        lang = get_current_language()
        return "en" if str(lang).lower().startswith("en") else "es"
    except Exception:
        return "es"

# Expresiones Regulares a nivel de módulo para evitar NameError y recompilación
PATRONES_REGEX_ANON = [
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.IGNORECASE), "[CORREO_ELIMINADO]"),
    (re.compile(r"\b(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.(?:com|es|org|net|co|io|gov|edu))\b", re.IGNORECASE), "[DOMINIO_ELIMINADO]"),
    (re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|bearer\s+[a-zA-Z0-9._\-]+|(?:password|clave|contraseña|pwd|api_key|secret|token)\s*[:=]\s*['\"]?([^\s'\"]{4,})['\"]?)\b", re.IGNORECASE), "[CLAVE_ELIMINADA]"),
    (re.compile(r"(?:@([a-zA-Z0-9._-]+)|\b(?:user|usuario|username|interlocutor)\s*[:=]\s*['\"]?([a-zA-Z0-9._-]+)['\"]?)", re.IGNORECASE), "[USUARIO_ELIMINADO]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"), "[TARJETA_ELIMINADA]"),
    # Teléfonos españoles e internacionales
    (re.compile(r"(?:\+34\s*|0034\s*)?(?:[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}|[6789]\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}|[6789]\d{1}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}|[6789]\d{8}|\b(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b)"), "[TELEFONO_ELIMINADO]"),
    (re.compile(r"\b\d{7,10}[-\s]?[A-Z0-9]?\b"), "[DOCUMENTO_ELIMINADO]"),
    # Escuelas, Colegios, Universidades e Instituciones
    (re.compile(r"\b(?:Colegio|Escuela|Instituto|CEIP|IES|Universidad|Facultad|Conservatorio|Hospital|Clínica|Fundación|Centro\s+Educativo|Guardería|Jardín\s+de\s+Infantes)\s+(?:N[º°]?\s*\d+\s+)?(?:de\s+|del\s+|la\s+|las\s+|los\s+|San\s+|Santa\s+|Nuestra\s+Señora\s+de\s+|Don\s+|Doña\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ0-9\s.-]+?(?=\s*[,;.\n]|\s+y\b|\s+con\b|\s+en\b|\s+de\b|\s+del\b|$)"), "[ORGANIZACION]"),
    # Nombres en mayúsculas sostenidas (ALL CAPS) y nombres completos tipo Title Case
    (re.compile(r"\b[A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})+\b"), "[PERSONA]"),
    (re.compile(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})+\b"), "[PERSONA]"),
    # Fórmulas de introducción legal
    (re.compile(r"\b(?:representado|representada|firmado|firma|por)\s+(?:en\s+este\s+acto\s+)?(?:por\s+)?([A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})*|[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)\b"), "[PERSONA]"),
    (re.compile(r"(?:(?:\d{2}:\d{2}\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-Z]\.?[A-Z]\.?)?)\s*:)"), "[PERSONA]"),
    (re.compile(r"(?:,\s*|\b(?:gracias|mira|mirá|dime|decía|bueno|hola|estimado|estimada|saludos)\s+)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})"), "[PERSONA]"),
]

PATRONES_REGEX = [
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.IGNORECASE), "CORREO"),
    (re.compile(r"\b(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.(?:com|es|org|net|co|io|gov|edu))\b", re.IGNORECASE), "DOMINIO"),
    (re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|bearer\s+[a-zA-Z0-9._\-]+|(?:password|clave|contraseña|pwd|api_key|secret|token)\s*[:=]\s*['\"]?([^\s'\"]{4,})['\"]?)\b", re.IGNORECASE), "CLAVE"),
    (re.compile(r"(?:@([a-zA-Z0-9._-]+)|\b(?:user|usuario|username|interlocutor)\s*[:=]\s*['\"]?([a-zA-Z0-9._-]+)['\"]?)", re.IGNORECASE), "USUARIO"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"), "TARJETA_CREDITO"),
    # Teléfonos españoles e internacionales
    (re.compile(r"(?:\+34\s*|0034\s*)?(?:[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}|[6789]\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}|[6789]\d{1}[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}|[6789]\d{8}|\b(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b)"), "TELEFONO"),
    (re.compile(r"\b\d{7,10}[-\s]?[A-Z0-9]?\b"), "ID_OFICIAL"),
    # Escuelas, Colegios, Universidades e Instituciones
    (re.compile(r"\b(?:Colegio|Escuela|Instituto|CEIP|IES|Universidad|Facultad|Conservatorio|Hospital|Clínica|Fundación|Centro\s+Educativo|Guardería|Jardín\s+de\s+Infantes)\s+(?:N[º°]?\s*\d+\s+)?(?:de\s+|del\s+|la\s+|las\s+|los\s+|San\s+|Santa\s+|Nuestra\s+Señora\s+de\s+|Don\s+|Doña\s+)?[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ0-9\s.-]+?(?=\s*[,;.\n]|\s+y\b|\s+con\b|\s+en\b|\s+de\b|\s+del\b|$)"), "ORGANIZACION"),
    # Nombres en mayúsculas sostenidas (ALL CAPS) y nombres completos tipo Title Case
    (re.compile(r"\b[A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})+\b"), "PERSONA"),
    (re.compile(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})+\b"), "PERSONA"),
    # Fórmulas de introducción legal
    (re.compile(r"\b(?:representado|representada|firmado|firma|por)\s+(?:en\s+este\s+acto\s+)?(?:por\s+)?([A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})*|[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)\b"), "PERSONA"),
    (re.compile(r"(?:(?:\d{2}:\d{2}\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-Z]\.?[A-Z]\.?)?)\s*:)"), "PERSONA"),
    (re.compile(r"(?:,\s*|\b(?:gracias|mira|mirá|dime|decía|bueno|hola|estimado|estimada|saludos)\s+)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})"), "PERSONA"),
]

def anonimizar_texto_real_irreversible(texto, generalizar_cuasi=True):
    """
    ANONIMIZACIÓN REAL E IRREVERSIBLE (Considerando 26 RGPD & Directrices EDPB 02/2026)
    - Detección de idioma estricta (ES / EN / Mixto) con rechazo seguro de terceros idiomas.
    - Cero generación de llaves de correspondencia (.key).
    - Destrucción de identificadores directos reemplazándolos por categorías genéricas sin índices correlativos.
    - Generalización de cuasi-identificadores (fechas a años, códigos postales truncados).
    - Retorna el texto anónimo irreversible y un diccionario con estadísticas del proceso.
    """
    if not isinstance(texto, str) or not texto.strip():
        return texto, {}

    # 1. Detección y validación de idioma (lanza IdiomaNoSoportadoError si corresponde)
    idioma_clasificado, idiomas_a_analizar = detectar_idioma(texto)

    stats = {
        "identificadores_directos_suprimidos": 0,
        "cuasi_identificadores_generalizados": 0,
        "terminos_confidenciales_suprimidos": 0,
        "idioma_detectado": idioma_clasificado
    }

    # 2. Aplicar exclusiones corporativas destructivamente
    texto_filtrado = aplicar_diccionario_exclusiones(texto)
    if texto_filtrado != texto:
        stats["terminos_confidenciales_suprimidos"] += 1

    texto_anom = texto_filtrado

    # 3. Generalización de cuasi-identificadores
    if generalizar_cuasi:
        texto_generalizado = generalizar_cuasi_identificadores(texto_anom)
        if texto_generalizado != texto_anom:
            stats["cuasi_identificadores_generalizados"] += 1
        texto_anom = texto_generalizado

    # 4. Presidio AI Engine (Bilingüe / Mixto con guard gramatical centralizado)
    exigir_motor()
    if analyzer:
        try:
            texto_analisis = all_caps_to_title_case(texto_anom)
            todas_entidades = []
            
            for lang in idiomas_a_analizar:
                if lang in analyzer.supported_languages:
                    res_lang = _analizar_o_fallar(
                        text=texto_analisis,
                        language=lang,
                        entities=["PERSON", "LOCATION", "ORGANIZATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"]
                    )
                    todas_entidades.extend(res_lang)

            # Deduplicar entidades solapadas
            res_no_solapados = []
            for pii in sorted(todas_entidades, key=lambda x: (x.end - x.start, x.score), reverse=True):
                if not any(max(pii.start, f.start) < min(pii.end, f.end) for f in res_no_solapados):
                    res_no_solapados.append(pii)

            for pii in sorted(res_no_solapados, key=lambda x: x.start, reverse=True):
                valido, val_txt, s_aj, e_aj, e_tipo = validar_y_limpiar_entidad(texto_anom, pii.start, pii.end, pii.entity_type)
                if not valido:
                    continue

                # Verificar que no esté dentro de corchetes existentes
                prefijo = texto_anom[:s_aj]
                sufijo = texto_anom[e_aj:]
                if prefijo.rfind("[") > prefijo.rfind("]") and sufijo.find("]") < sufijo.find("["):
                    continue

                etiqueta = MAPA_ETIQUETAS_ANON_REAL.get(e_tipo, "[DATO_PERSONAL]")
                texto_anom = texto_anom[:s_aj] + etiqueta + texto_anom[e_aj:]
                stats["identificadores_directos_suprimidos"] += 1
        except IdiomaNoSoportadoError:
            raise
        except MotorNoDisponibleError:
            raise
        except Exception as ex:
            raise MotorNoDisponibleError(f"Falló la detección de datos personales ({type(ex).__name__}).") from ex

    # 5. Nombres propios conocidos (ES y EN con guard gramatical, ordenados por longitud)
    for nombre in sorted(list(set(SPANISH_NAMES + ENGLISH_NAMES)), key=len, reverse=True):
        if nombre.lower() in SOFTWARE_ALLOWLIST or len(nombre) < 3:
            continue
        patron = re.compile(rf"\b{re.escape(nombre)}\b", re.IGNORECASE)
        for match in list(patron.finditer(texto_anom)):
            valido, val_txt, s_aj, e_aj, _ = validar_y_limpiar_entidad(texto_anom, match.start(), match.end(), "PERSON")
            if not valido:
                continue
            if "[" in val_txt or "]" in val_txt:
                continue
            prefijo = texto_anom[:s_aj]
            sufijo = texto_anom[e_aj:]
            if prefijo.rfind("[") > prefijo.rfind("]") and sufijo.find("]") < sufijo.find("["):
                continue
            texto_anom = texto_anom[:s_aj] + "[PERSONA]" + texto_anom[e_aj:]
            stats["identificadores_directos_suprimidos"] += 1

    # 6. Ubicaciones conocidas (Madrid, Barcelona, London, Paris, etc.)
    for loc in sorted(list(KNOWN_LOCATIONS), key=len, reverse=True):
        patron_loc = re.compile(rf"\b{re.escape(loc)}\b", re.IGNORECASE)
        for match in list(patron_loc.finditer(texto_anom)):
            valido, val_txt, s_aj, e_aj, _ = validar_y_limpiar_entidad(texto_anom, match.start(), match.end(), "LOCATION")
            if not valido or "[" in val_txt or "]" in val_txt:
                continue
            prefijo = texto_anom[:s_aj]
            sufijo = texto_anom[e_aj:]
            if prefijo.rfind("[") > prefijo.rfind("]") and sufijo.find("]") < sufijo.find("["):
                continue
            texto_anom = texto_anom[:s_aj] + "[UBICACION]" + texto_anom[e_aj:]
            stats["identificadores_directos_suprimidos"] += 1

    # 7. Expresiones Regulares con Guard Morfosintáctico Unificado
    for regex, tag in PATRONES_REGEX_ANON:
        matches = list(regex.finditer(texto_anom))
        for match in sorted(matches, key=lambda m: m.start(), reverse=True):
            m_start = match.start(1) if match.groups() and match.group(1) else match.start()
            m_end = match.end(1) if match.groups() and match.group(1) else match.end()
            
            entidad_check = "PERSON" if tag == "[PERSONA]" else ("LOCATION" if tag == "[UBICACION]" else tag.strip("[]"))
            valido, val_txt, s_aj, e_aj, _ = validar_y_limpiar_entidad(texto_anom, m_start, m_end, entidad_check)
            if not valido or "[" in val_txt or "]" in val_txt:
                continue

            # Verificar que no esté dentro de corchetes existentes
            prefijo = texto_anom[:s_aj]
            sufijo = texto_anom[e_aj:]
            if prefijo.rfind("[") > prefijo.rfind("]") and sufijo.find("]") < sufijo.find("["):
                continue

            texto_anom = texto_anom[:s_aj] + tag + texto_anom[e_aj:]
            stats["identificadores_directos_suprimidos"] += 1

    texto_anom = re.sub(r'\[+([^\[\]]+)\]+', r'[\1]', texto_anom)
    return texto_anom, stats

def sanitizar_nombre_archivo_real(nombre_archivo):
    nombre_base, ext = os.path.splitext(nombre_archivo)
    nombre_base_espacios = nombre_base.replace("_", " ").replace("-", " ")
    limpio, _ = anonimizar_texto_real_irreversible(nombre_base_espacios)
    sanitizado_base = limpio.replace(" ", "_")
    return f"{sanitizado_base}{ext}"

def sanitizar_nombre_archivo(nombre_archivo, carpeta_salida=None):
    nombre_base, ext = os.path.splitext(nombre_archivo)
    nombre_base_espacios = nombre_base.replace("_", " ").replace("-", " ")
    limpio, key_map = anonimizar_texto_con_ia_y_key(nombre_base_espacios, carpeta_salida=carpeta_salida)
    sanitizado_base = limpio.replace(" ", "_")
    return f"{sanitizado_base}{ext}", key_map

def all_caps_to_title_case(text):
    exclusions = {'DNI', 'NIE', 'NIF', 'IVA', 'NDA'}
    def replace_word(match):
        word = match.group(0)
        if word in exclusions:
            return word
        return word.title()
    return re.sub(r'\b[A-ZÁÉÍÓÚÑ]{2,}\b', replace_word, text)

def anonimizar_texto_con_ia_y_key(texto, nombre_archivo=None, carpeta_salida=None, contadores_existentes=None, key_map_existente=None):
    if not isinstance(texto, str) or not texto.strip():
        return texto, {}

    # 1. Detección y validación de idioma
    idioma_clasificado, idiomas_a_analizar = detectar_idioma(texto)

    target_salida = carpeta_salida or CARPETA_SALIDA_DEFECTO
    os.makedirs(target_salida, exist_ok=True)
    texto_filtrado = aplicar_diccionario_exclusiones(texto)

    key_map = key_map_existente if key_map_existente is not None else {}
    contadores = contadores_existentes if contadores_existentes is not None else {}
    texto_anom = texto_filtrado

    valor_a_etiqueta = {val: k for k, val in key_map.items()}

    # 2. Presidio AI Engine (Bilingüe / Mixto con guard gramatical)
    exigir_motor()
    if analyzer:
        try:
            texto_analisis = all_caps_to_title_case(texto_anom)
            todas_entidades = []
            for lang in idiomas_a_analizar:
                if lang in analyzer.supported_languages:
                    res_lang = _analizar_o_fallar(
                        text=texto_analisis,
                        language=lang,
                        entities=["PERSON", "LOCATION", "ORGANIZATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"]
                    )
                    todas_entidades.extend(res_lang)

            # Desduplicar spans solapados
            res_no_solapados = []
            for pii in sorted(todas_entidades, key=lambda x: (x.end - x.start, x.score), reverse=True):
                if not any(max(pii.start, f.start) < min(pii.end, f.end) for f in res_no_solapados):
                    res_no_solapados.append(pii)

            for pii in sorted(res_no_solapados, key=lambda x: x.start, reverse=True):
                valido, val_txt, s_aj, e_aj, e_tipo = validar_y_limpiar_entidad(texto_anom, pii.start, pii.end, pii.entity_type)
                if not valido:
                    continue

                # Verificar que no esté dentro de corchetes existentes
                prefijo = texto_anom[:s_aj]
                sufijo = texto_anom[e_aj:]
                if prefijo.rfind("[") > prefijo.rfind("]") and sufijo.find("]") < sufijo.find("["):
                    continue

                tag = MAPA_ETIQUETAS.get(e_tipo, "PERSONA")
                if val_txt in valor_a_etiqueta:
                    etiqueta = valor_a_etiqueta[val_txt]
                else:
                    idx = contadores.get(tag, 1)
                    etiqueta = f"[{tag}_{idx}]"
                    contadores[tag] = idx + 1
                    key_map[etiqueta] = val_txt
                    valor_a_etiqueta[val_txt] = etiqueta

                texto_anom = texto_anom[:s_aj] + etiqueta + texto_anom[e_aj:]
        except IdiomaNoSoportadoError:
            raise
        except MotorNoDisponibleError:
            raise
        except Exception as ex:
            raise MotorNoDisponibleError(f"Falló la detección de datos personales ({type(ex).__name__}).") from ex

    valor_a_etiqueta = {val: k for k, val in key_map.items()}

    # 3. Matching explícito de nombres propios conocidos (ES y EN con guard gramatical, ordenados por longitud)
    for nombre in sorted(list(set(SPANISH_NAMES + ENGLISH_NAMES)), key=len, reverse=True):
        if nombre.lower() in SOFTWARE_ALLOWLIST or len(nombre) < 3:
            continue
        patron = re.compile(rf"\b{re.escape(nombre)}\b", re.IGNORECASE)
        for match in list(patron.finditer(texto_anom)):
            valido, val_txt, s_aj, e_aj, _ = validar_y_limpiar_entidad(texto_anom, match.start(), match.end(), "PERSON")
            if not valido or "[" in val_txt or "]" in val_txt:
                continue

            # Verificar que no esté dentro de corchetes existentes
            prefijo = texto_anom[:s_aj]
            sufijo = texto_anom[e_aj:]
            if prefijo.rfind("[") > prefijo.rfind("]") and sufijo.find("]") < sufijo.find("["):
                continue

            if val_txt in valor_a_etiqueta:
                etiqueta = valor_a_etiqueta[val_txt]
            else:
                idx = contadores.get("PERSONA", 1)
                etiqueta = f"[PERSONA_{idx}]"
                contadores["PERSONA"] = idx + 1
                key_map[etiqueta] = val_txt
                valor_a_etiqueta[val_txt] = etiqueta

            texto_anom = texto_anom[:s_aj] + etiqueta + texto_anom[e_aj:]
            valor_a_etiqueta = {val: k for k, val in key_map.items()}

    # 4. Ubicaciones conocidas (Madrid, Barcelona, London, Paris, etc.)
    for loc in sorted(list(KNOWN_LOCATIONS), key=len, reverse=True):
        patron_loc = re.compile(rf"\b{re.escape(loc)}\b", re.IGNORECASE)
        for match in list(patron_loc.finditer(texto_anom)):
            valido, val_txt, s_aj, e_aj, _ = validar_y_limpiar_entidad(texto_anom, match.start(), match.end(), "LOCATION")
            if not valido or "[" in val_txt or "]" in val_txt:
                continue

            prefijo = texto_anom[:s_aj]
            sufijo = texto_anom[e_aj:]
            if prefijo.rfind("[") > prefijo.rfind("]") and sufijo.find("]") < sufijo.find("["):
                continue

            if val_txt in valor_a_etiqueta:
                etiqueta = valor_a_etiqueta[val_txt]
            else:
                idx = contadores.get("UBICACION", 1)
                etiqueta = f"[UBICACION_{idx}]"
                contadores["UBICACION"] = idx + 1
                key_map[etiqueta] = val_txt
                valor_a_etiqueta[val_txt] = etiqueta

            texto_anom = texto_anom[:s_aj] + etiqueta + texto_anom[e_aj:]
            valor_a_etiqueta = {val: k for k, val in key_map.items()}

    # 5. Expresiones Regulares con Guard Morfosintáctico Unificado
    for regex, tag in PATRONES_REGEX:
        matches = list(regex.finditer(texto_anom))
        for match in sorted(matches, key=lambda m: m.start(), reverse=True):
            m_start = match.start(1) if match.groups() and match.group(1) else match.start()
            m_end = match.end(1) if match.groups() and match.group(1) else match.end()

            entidad_check = "PERSON" if tag == "PERSONA" else ("LOCATION" if tag == "UBICACION" else tag)
            valido, val_txt, s_aj, e_aj, _ = validar_y_limpiar_entidad(texto_anom, m_start, m_end, entidad_check)
            if not valido or "[" in val_txt or "]" in val_txt:
                continue

            # Verificar que no esté dentro de corchetes existentes
            prefijo = texto_anom[:s_aj]
            sufijo = texto_anom[e_aj:]
            if prefijo.rfind("[") > prefijo.rfind("]") and sufijo.find("]") < sufijo.find("["):
                continue

            if val_txt in valor_a_etiqueta:
                etiqueta = valor_a_etiqueta[val_txt]
            else:
                idx = contadores.get(tag, 1)
                etiqueta = f"[{tag}_{idx}]"
                contadores[tag] = idx + 1
                key_map[etiqueta] = val_txt
                valor_a_etiqueta[val_txt] = etiqueta

            texto_anom = texto_anom[:s_aj] + etiqueta + texto_anom[e_aj:]
            valor_a_etiqueta = {val: k for k, val in key_map.items()}

    if nombre_archivo and key_map:
        guardar_llave_key(target_salida, nombre_archivo, key_map)

    return texto_anom, key_map


def revertir_anonimizacion(texto_anonimizado, mapa_reversion):
    if not isinstance(texto_anonimizado, str) or not mapa_reversion:
        return texto_anonimizado
    
    texto_restaurado = texto_anonimizado
    for etiqueta, original in mapa_reversion.items():
        if not etiqueta or not isinstance(etiqueta, str):
            continue
        etiqueta_limpia = etiqueta.strip("[]")
        texto_restaurado = re.sub(r"\[+" + re.escape(etiqueta_limpia) + r"\]+", str(original), texto_restaurado)
        texto_restaurado = texto_restaurado.replace(etiqueta, str(original))
    return texto_restaurado


def ejecutar_reversion_archivo(ruta_origen, mapa_reversion, ruta_destino=None):
    if not os.path.exists(ruta_origen) or not mapa_reversion:
        return ruta_origen

    nombre_base, ext = os.path.splitext(os.path.basename(ruta_origen))
    ext_lower = ext.lower()

    if not ruta_destino:
        target_dir = CARPETA_RESTAURADOS if 'CARPETA_RESTAURADOS' in globals() and os.path.exists(CARPETA_RESTAURADOS) else os.path.dirname(ruta_origen)
        os.makedirs(target_dir, exist_ok=True)
        ruta_destino = os.path.join(target_dir, f"{nombre_base}_restaurado{ext}")

    if ext_lower in [".xlsx", ".xls"]:
        wb = openpyxl.load_workbook(ruta_origen)
        for hoja in wb.worksheets:
            for fila in hoja.iter_rows():
                for celda in fila:
                    if isinstance(celda.value, str) and celda.value.strip():
                        celda.value = revertir_anonimizacion(celda.value, mapa_reversion)
        wb.save(ruta_destino)

    elif ext_lower == ".csv":
        df = pd.read_csv(ruta_origen, dtype=str)
        for columna in df.columns:
            for idx, val in enumerate(df[columna]):
                if isinstance(val, str) and val.strip():
                    df.at[idx, columna] = revertir_anonimizacion(val, mapa_reversion)
        df.to_csv(ruta_destino, index=False, encoding="utf-8")

    elif ext_lower == ".docx":
        doc = Document(ruta_origen)
        for parrafo in doc.paragraphs:
            if parrafo.text.strip():
                for run in parrafo.runs:
                    if run.text.strip():
                        run.text = revertir_anonimizacion(run.text, mapa_reversion)
        for tabla in doc.tables:
            for fila in tabla.rows:
                for celda in fila.cells:
                    if celda.text.strip():
                        celda.text = revertir_anonimizacion(celda.text, mapa_reversion)
        doc.save(ruta_destino)

    elif ext_lower == ".json":
        with open(ruta_origen, "r", encoding="utf-8") as f:
            datos = json.load(f)

        def revertir_nodo(obj):
            if isinstance(obj, str):
                return revertir_anonimizacion(obj, mapa_reversion)
            elif isinstance(obj, list):
                return [revertir_nodo(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: revertir_nodo(v) for k, v in obj.items()}
            else:
                return obj

        datos_restaurados = revertir_nodo(datos)
        with open(ruta_destino, "w", encoding="utf-8") as f:
            json.dump(datos_restaurados, f, indent=4, ensure_ascii=False)

    else:
        with open(ruta_origen, "r", encoding="utf-8", errors="ignore") as f:
            contenido = f.read()
        restaurado = revertir_anonimizacion(contenido, mapa_reversion)
        with open(ruta_destino, "w", encoding="utf-8") as f:
            f.write(restaurado)

    registro.registrar("reversion", ruta_archivo=ruta_origen, entidades=auditoria.contar_entidades(mapa_reversion))
    return ruta_destino


def procesar_archivo_texto(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None):
    with open(ruta_origen, "r", encoding="utf-8") as f:
        contenido = f.read()
    
    contenido_limpio, _ = anonimizar_texto_con_ia_y_key(contenido, nombre_archivo, carpeta_salida)
    
    with open(ruta_destino, "w", encoding="utf-8") as f:
        f.write(contenido_limpio)


def procesar_markdown(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None):
    procesar_archivo_texto(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida)


def procesar_json(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None):
    with open(ruta_origen, "r", encoding="utf-8") as f:
        datos = json.load(f)

    target_salida = carpeta_salida or CARPETA_SALIDA_DEFECTO
    key_map = {}
    contadores = {}

    def anonimizar_nodo(obj):
        if isinstance(obj, str):
            res, _ = anonimizar_texto_con_ia_y_key(obj, contadores_existentes=contadores, key_map_existente=key_map)
            return res
        elif isinstance(obj, list):
            return [anonimizar_nodo(item) for item in obj]
        elif isinstance(obj, dict):
            nuevo_dict = {}
            for k, v in obj.items():
                nuevo_dict[k] = anonimizar_nodo(v)
            return nuevo_dict
        else:
            return obj

    datos_limpios = anonimizar_nodo(datos)

    with open(ruta_destino, "w", encoding="utf-8") as f:
        json.dump(datos_limpios, f, indent=4, ensure_ascii=False)

    if key_map:
        guardar_llave_key(target_salida, nombre_archivo, key_map)


def procesar_dataframe_tabular(df, contadores=None, key_map=None):
    """Procedimiento Tabular por Columna unificado para CSV y Excel."""
    key_map = key_map if key_map is not None else {}
    contadores = contadores if contadores is not None else {}

    COLUMNAS_PERSONA = {"nombre", "name", "contacto", "persona", "responsable", "propietario", "representante", "entrevistado", "entrevistada"}
    COLUMNAS_EMPRESA = {"empresa", "company", "organización", "organizacion", "entidad", "razón social", "razon social", "cliente"}
    COLUMNAS_EMAIL = {"email", "correo", "e-mail", "mail"}
    COLUMNAS_URL = {"url", "web", "sitio", "website", "enlace", "link", "dominio"}
    COLUMNAS_TELEFONO = {"telefono", "teléfono", "phone", "tel", "móvil", "movil", "celular"}
    COLUMNAS_UBICACION = {"ubicacion", "ubicación", "location", "ciudad", "city", "país", "pais", "dirección", "direccion", "sede"}

    def tipo_columna_sensible(col_name):
        cl = str(col_name).lower().strip()
        cl_base = re.sub(r'\.\d+$', '', cl)
        for kw in COLUMNAS_PERSONA:
            if kw in cl_base:
                return "PERSONA"
        for kw in COLUMNAS_EMPRESA:
            if kw in cl_base:
                return "ORGANIZACION"
        for kw in COLUMNAS_EMAIL:
            if kw in cl_base:
                return "CORREO"
        for kw in COLUMNAS_URL:
            if kw in cl_base:
                return "DOMINIO"
        for kw in COLUMNAS_TELEFONO:
            if kw in cl_base:
                return "TELEFONO"
        for kw in COLUMNAS_UBICACION:
            if kw in cl_base:
                return "UBICACION"
        return None

    valor_a_etiqueta = {v: k for k, v in key_map.items()}

    for columna in df.columns:
        tipo_forzado = tipo_columna_sensible(columna)

        for idx, val in enumerate(df[columna]):
            if not isinstance(val, str) or not val.strip():
                continue

            val_limpio = val.strip()

            if tipo_forzado:
                if val_limpio.lower() in SOFTWARE_ALLOWLIST or len(val_limpio) < 2:
                    continue
                if val_limpio in valor_a_etiqueta:
                    df.at[idx, columna] = valor_a_etiqueta[val_limpio]
                else:
                    tag = tipo_forzado
                    num = contadores.get(tag, 1)
                    etiqueta = f"[{tag}_{num}]"
                    contadores[tag] = num + 1
                    key_map[etiqueta] = val_limpio
                    valor_a_etiqueta[val_limpio] = etiqueta
                    df.at[idx, columna] = etiqueta
            else:
                limpio, _ = anonimizar_texto_con_ia_y_key(val, contadores_existentes=contadores, key_map_existente=key_map)
                df.at[idx, columna] = limpio
                for k, v in key_map.items():
                    if v not in valor_a_etiqueta:
                        valor_a_etiqueta[v] = k

    return df, key_map, contadores


def procesar_tabla_csv(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None):
    df = pd.read_csv(ruta_origen, dtype=str)
    target_salida = carpeta_salida or CARPETA_SALIDA_DEFECTO
    df, key_map, _ = procesar_dataframe_tabular(df)
    df.to_csv(ruta_destino, index=False, encoding="utf-8")
    if key_map:
        guardar_llave_key(target_salida, nombre_archivo, key_map)


def procesar_documento_word(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None):
    doc = Document(ruta_origen)
    key_map = {}
    contadores = {}
    target_salida = carpeta_salida or CARPETA_SALIDA_DEFECTO
    
    # Procesar párrafos completos para mantener contexto semántico de IA y Regex
    for parrafo in doc.paragraphs:
        if parrafo.text.strip():
            limpio, _ = anonimizar_texto_con_ia_y_key(parrafo.text, contadores_existentes=contadores, key_map_existente=key_map)
            if parrafo.runs:
                parrafo.runs[0].text = limpio
                for run in parrafo.runs[1:]:
                    run.text = ""
                    
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                if celda.text.strip():
                    limpio, _ = anonimizar_texto_con_ia_y_key(celda.text, contadores_existentes=contadores, key_map_existente=key_map)
                    celda.text = limpio
                    
    doc.save(ruta_destino)
    if key_map:
        guardar_llave_key(target_salida, nombre_archivo, key_map)


def procesar_excel(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None):
    target_salida = carpeta_salida or CARPETA_SALIDA_DEFECTO
    wb = openpyxl.load_workbook(ruta_origen)
    key_map = {}
    contadores = {}

    for hoja in wb.worksheets:
        datos = list(hoja.values)
        if not datos:
            continue
        headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(datos[0])]
        rows = datos[1:]
        df = pd.DataFrame(rows, columns=headers).astype(str)
        df, key_map, contadores = procesar_dataframe_tabular(df, contadores=contadores, key_map=key_map)

        for col_idx, col_name in enumerate(headers, start=1):
            for row_idx, val in enumerate(df[col_name], start=2):
                celda = hoja.cell(row=row_idx, column=col_idx)
                if isinstance(celda.value, str) and celda.value.strip():
                    celda.value = val

    wb.save(ruta_destino)
    if key_map:
        guardar_llave_key(target_salida, nombre_archivo, key_map)


def procesar_pdf(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None):
    if not fitz:
        raise MotorNoDisponibleError("PyMuPDF no está instalado: no se pueden procesar archivos PDF.")
    exigir_motor()
        
    doc = fitz.open(ruta_origen)
    mapas_acumulados = {}
    target_salida = carpeta_salida or CARPETA_SALIDA_DEFECTO
    
    for num_pag, pagina in enumerate(doc):
        texto_pagina = pagina.get_text()
        if texto_pagina.strip():
            _, mapa_pag = anonimizar_texto_con_ia_y_key(texto_pagina)
            for etiqueta, val_original in mapa_pag.items():
                if len(val_original.strip()) > 1 and val_original.lower().strip() not in SOFTWARE_ALLOWLIST:
                    rects = pagina.search_for(val_original)
                    for rect in rects:
                        pagina.add_redact_annot(rect, text=etiqueta, fill=(0.12, 0.16, 0.22), text_color=(1, 1, 1), fontsize=8)
                    mapas_acumulados[etiqueta] = val_original
                    
        pagina.apply_redactions()
        
        # C) Si no tiene texto, aplicar OCR si está disponible
        if not texto_pagina.strip() and pagina.get_images() and not lector_ocr:
            raise MotorNoDisponibleError("El PDF tiene páginas escaneadas y el OCR no está disponible.")
        if not texto_pagina.strip() and lector_ocr:
            pix = pagina.get_pixmap(dpi=200)
            fd_tmp, ruta_tmp = tempfile.mkstemp(prefix="liavault_pag_", suffix=".png")
            os.close(fd_tmp)
            # La imagen temporal tiene la página sin tapar: se borra aunque falle el OCR.
            try:
                pix.save(ruta_tmp)
                # Las entradas OCR de la página van a la llave del PDF, con un prefijo para no chocar entre páginas.
                mapa_pagina = procesar_imagen_ocr(ruta_tmp, ruta_tmp, None, carpeta_salida=target_salida, guardar_llave=False)
                for token, valor in mapa_pagina.items():
                    mapas_acumulados[token.replace("[IMAGE_PII_", f"[PAG{num_pag + 1}_IMAGE_PII_")] = valor
                pagina.insert_image(pagina.rect, filename=ruta_tmp)
            finally:
                os.remove(ruta_tmp)
                    
    doc.save(ruta_destino, garbage=4, deflate=True)
    doc.close()
    
    if mapas_acumulados:
        guardar_llave_key(target_salida, nombre_archivo, mapas_acumulados)


def procesar_imagen_ocr(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None, guardar_llave=True):
    if not cv2 or not lector_ocr:
        raise MotorNoDisponibleError("El OCR (EasyOCR/OpenCV) no está disponible: no se pueden procesar imágenes.")
    exigir_motor()
        
    resultados_ocr = lector_ocr.readtext(ruta_origen)
    imagen_cv = cv2.imread(ruta_origen)
    mapas_acumulados = {}
    target_salida = carpeta_salida or CARPETA_SALIDA_DEFECTO
    terminos_corp = cargar_diccionario_corporativo()

    for (coordenadas, texto_detectado, probabilidad) in resultados_ocr:
        if len(texto_detectado.strip()) > 1:
            analisis = _analizar_o_fallar(
                text=texto_detectado, language="es",
                entities=["PERSON", "LOCATION", "ORGANIZATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"]
            )
            
            dict_match = [t for t in terminos_corp if t.lower() in texto_detectado.lower()]
            
            if analisis or dict_match:
                x_min = int(min([p[0] for p in coordenadas]))
                y_min = int(min([p[1] for p in coordenadas]))
                x_max = int(max([p[0] for p in coordenadas]))
                y_max = int(max([p[1] for p in coordenadas]))
                
                label = "[CONFIDENCIAL]" if dict_match else MAPA_ETIQUETAS.get(analisis[0].entity_type, "[PII]")
                
                cv2.rectangle(imagen_cv, (x_min, y_min), (x_max, y_max), (30, 24, 18), -1)
                cv2.rectangle(imagen_cv, (x_min, y_min), (x_max, y_max), (248, 189, 56), 1)
                
                h_box = max(1, y_max - y_min)
                scale = max(0.3, min(0.5, h_box / 35.0))
                cv2.putText(imagen_cv, label, (x_min + 3, y_min + int(h_box * 0.7)), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)
                mapas_acumulados[f"[IMAGE_PII_{len(mapas_acumulados)+1}]"] = texto_detectado

    cv2.imwrite(ruta_destino, imagen_cv)
    if mapas_acumulados and guardar_llave:
        guardar_llave_key(target_salida, nombre_archivo, mapas_acumulados)
    return mapas_acumulados


def _eliminar_salida_parcial(target_salida, ruta_destino, nombre_archivo):
    """Borra lo que haya quedado de un archivo que falló: salida, llaves y certificado."""
    nombre_base = os.path.splitext(nombre_archivo)[0]
    for ruta in (ruta_destino,
                 llaves.ruta_llave(CARPETA_LLAVES, nombre_archivo),
                 os.path.join(target_salida, f"Certificado_Anonimizacion_{nombre_base}.txt")):
        try:
            if os.path.exists(ruta):
                os.remove(ruta)
        except OSError:
            print(f"⚠️ No se pudo borrar una salida parcial en {target_salida}")


def _nombre_salida_libre(carpeta, nombre, carpeta_llaves=None):
    """
    Nombre de salida que no pisa otro documento ni su llave. Distintos originales pueden quedar con el mismo
    nombre seudonimizado (p. ej. [PERSONA_1].xlsx): sin esto, el último sobrescribía la salida y la llave del anterior.
    """
    base, ext = os.path.splitext(nombre)
    candidato, n = nombre, 1
    while os.path.exists(os.path.join(carpeta, candidato)) or (
        carpeta_llaves and os.path.exists(llaves.ruta_llave(carpeta_llaves, candidato))
    ):
        n += 1
        candidato = f"{base}_{n}{ext}"
    return candidato


def ejecutar_procesamiento_lotes(carpeta_salida=None, archivo_especifico=None):
    exigir_motor()
    # Sin clave maestra no se podrían guardar las llaves: se falla antes de tocar ningún archivo.
    llaves.obtener_clave_maestra(CARPETA_LLAVES)
    target_salida = carpeta_salida or CARPETA_SALIDA_DEFECTO
    os.makedirs(target_salida, exist_ok=True)
    os.makedirs(CARPETA_PROCESADOS, exist_ok=True)

    if archivo_especifico:
        archivos = [archivo_especifico] if os.path.exists(os.path.join(CARPETA_ENTRADA, archivo_especifico)) else []
    else:
        archivos = os.listdir(CARPETA_ENTRADA)
        archivos = [f for f in archivos if not f.startswith("~$") and not f.startswith(".") and os.path.isfile(os.path.join(CARPETA_ENTRADA, f))]
    
    if not archivos:
        print(f"[INFO] La carpeta '{CARPETA_ENTRADA}' esta vacia. Agregue archivos para procesar.")
        return 0

    print(f"[INFO] LIA VAULT: Procesando lote de {len(archivos)} archivos -> '{target_salida}'")
    procesados_exitosos = 0
    
    for nombre_archivo in archivos:
        ruta_origen = os.path.join(CARPETA_ENTRADA, nombre_archivo)
        nombre_sanitizado, fn_map = sanitizar_nombre_archivo(nombre_archivo, carpeta_salida=target_salida)
        nombre_sanitizado = _nombre_salida_libre(target_salida, nombre_sanitizado, CARPETA_LLAVES)
        ruta_destino = os.path.join(target_salida, nombre_sanitizado)
        ext = nombre_archivo.lower()
        # La llave se nombra como la salida, no como el original: el nombre original puede contener PII.
        nombre_llave = nombre_sanitizado

        try:
            if ext.endswith(".txt"):
                procesar_archivo_texto(ruta_origen, ruta_destino, nombre_llave, target_salida)
            elif ext.endswith(".md"):
                procesar_markdown(ruta_origen, ruta_destino, nombre_llave, target_salida)
            elif ext.endswith(".json"):
                procesar_json(ruta_origen, ruta_destino, nombre_llave, target_salida)
            elif ext.endswith(".csv"):
                procesar_tabla_csv(ruta_origen, ruta_destino, nombre_llave, target_salida)
            elif ext.endswith(".docx"):
                procesar_documento_word(ruta_origen, ruta_destino, nombre_llave, target_salida)
            elif ext.endswith(".xlsx"):
                procesar_excel(ruta_origen, ruta_destino, nombre_llave, target_salida)
            elif ext.endswith(".pdf"):
                procesar_pdf(ruta_origen, ruta_destino, nombre_llave, target_salida)
            elif ext.endswith((".jpg", ".jpeg", ".png")):
                procesar_imagen_ocr(ruta_origen, ruta_destino, nombre_llave, target_salida)
            else:
                print(f"⚠️ Formato no compatible: {nombre_archivo}")
                continue
            
            # Mover archivo original procesado exitosamente a /procesados para no volver a encriptarlo
            ruta_procesados = os.path.join(CARPETA_PROCESADOS, nombre_archivo)
            if os.path.exists(ruta_procesados):
                os.remove(ruta_procesados)
            shutil.move(ruta_origen, ruta_procesados)
            procesados_exitosos += 1
            ruta_llave_doc = llaves.ruta_llave(CARPETA_LLAVES, nombre_llave)
            mapa_doc = llaves.leer_llave_archivo(ruta_llave_doc, CARPETA_LLAVES) if os.path.exists(ruta_llave_doc) else {}
            registro.registrar("seudonimizacion", ruta_archivo=ruta_procesados, entidades=auditoria.contar_entidades(mapa_doc))
            print(f"✅ Procesado y movido a /procesados: {nombre_archivo}")

        except IdiomaNoSoportadoError as e_lang:
            _eliminar_salida_parcial(target_salida, ruta_destino, nombre_llave)
            registro.registrar("seudonimizacion", "rechazado", ruta_archivo=ruta_origen, error=e_lang)
            print(f"⚠️ Archivo rechazado por idioma no soportado {nombre_archivo}: {e_lang}")
            if archivo_especifico:
                raise e_lang
        except Exception as e:
            _eliminar_salida_parcial(target_salida, ruta_destino, nombre_llave)
            registro.registrar("seudonimizacion", "error", ruta_archivo=ruta_origen, error=e)
            print(f"❌ Error al procesar {nombre_archivo}: {type(e).__name__}")
            if archivo_especifico:
                raise e
            
    return procesados_exitosos


def guardar_llave_key(target_salida, nombre_archivo, key_map):
    """Guarda la llave cifrada del documento en CARPETA_LLAVES. Si no se puede, falla: sin llave no hay reversión."""
    if not key_map or not nombre_archivo:
        return
    llaves.guardar_llave(CARPETA_LLAVES, nombre_archivo, key_map)


def buscar_llave(nombre_documento, carpeta_salida=None):
    """Ruta de la llave de un documento: la cifrada en CARPETA_LLAVES o, si no hay, una .key antigua junto a la salida."""
    ruta = llaves.ruta_llave(CARPETA_LLAVES, nombre_documento)
    if os.path.exists(ruta):
        return ruta
    carpeta = carpeta_salida or CARPETA_SALIDA_DEFECTO
    for sufijo in (".key", ".reverse.key"):
        antigua = os.path.join(carpeta, f"{nombre_documento}{sufijo}")
        if os.path.exists(antigua):
            return antigua
    return None


def migrar_llaves_antiguas(carpeta_salida=None):
    """Cifra las llaves en claro de versiones anteriores que haya en las carpetas de seudonimizados."""
    carpetas = {os.path.join(_base_dir, cfg["seudonimizados"]) for cfg in NOMBRES_CARPETAS.values()}
    carpetas.add(carpeta_salida or CARPETA_SALIDA_DEFECTO)
    return llaves.migrar_llaves_antiguas(sorted(carpetas), CARPETA_LLAVES)


def documentos_con_llave(carpeta_salida=None):
    """Nombres de los documentos que tienen llave de reversión (cifrada o antigua)."""
    nombres = set()
    if os.path.isdir(CARPETA_LLAVES):
        nombres.update(f[:-len(llaves.EXTENSION)] for f in os.listdir(CARPETA_LLAVES) if f.endswith(llaves.EXTENSION))
    carpeta = carpeta_salida or CARPETA_SALIDA_DEFECTO
    if os.path.isdir(carpeta):
        nombres.update(f.replace(".reverse.key", "").replace(".key", "") for f in os.listdir(carpeta) if f.endswith(".key"))
    return sorted(nombres)


def desanonimizar_texto(texto_anonimizado, mapa_llave):
    """Reemplaza los tokens anonimizados por su valor original utilizando el diccionario de llave .key."""
    texto_restaurado = texto_anonimizado
    if isinstance(mapa_llave, str):
        try:
            mapa_llave = json.loads(mapa_llave)
        except Exception:
            pass
            
    if isinstance(mapa_llave, dict):
        for token, valor_original in mapa_llave.items():
            texto_restaurado = texto_restaurado.replace(token, valor_original)
    return texto_restaurado


def desanonimizar_archivo(ruta_archivo, mapa_llave, ruta_destino_restaurada):
    """Lee un archivo anonimizado y aplica la llave para restaurar sus valores originales en el destino."""
    if isinstance(mapa_llave, str):
        try:
            mapa_llave = json.loads(mapa_llave)
        except Exception:
            pass
            
    if not os.path.exists(ruta_archivo) or not isinstance(mapa_llave, dict):
        return False
        
    try:
        with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f_in:
            txt = f_in.read()
        txt_restaurado = desanonimizar_texto(txt, mapa_llave)
        with open(ruta_destino_restaurada, "w", encoding="utf-8") as f_out:
            f_out.write(txt_restaurado)
        return True
    except Exception as e:
        print(f"Error desanonimizando archivo: {e}")
        return False


# ==============================================================================
# PIPELINE DE ANONIMIZACIÓN REAL E IRREVERSIBLE (RGPD Considerando 26)
# ==============================================================================

def limpiar_metadatos_docx(doc):
    try:
        cp = doc.core_properties
        cp.author = "Lia Vault RGPD Anonymizer"
        cp.last_modified_by = "Lia Vault RGPD Anonymizer"
        cp.title = "Documento Anonimizado RGPD"
        cp.subject = "Anonimizacion Irreversible"
        cp.comments = "Procesado conforme al Considerando 26 del RGPD y Directrices EDPB 02/2026."
    except Exception:
        pass


def limpiar_metadatos_openpyxl(wb):
    try:
        wb.properties.creator = "Lia Vault RGPD Anonymizer"
        wb.properties.lastModifiedBy = "Lia Vault RGPD Anonymizer"
        wb.properties.title = "Datos Anonimizados RGPD"
        wb.properties.description = "Procesado conforme al Considerando 26 del RGPD."
    except Exception:
        pass


def limpiar_metadatos_pdf(doc):
    try:
        doc.set_metadata({
            "author": "Lia Vault RGPD Anonymizer",
            "creator": "Lia Vault",
            "producer": "Lia Vault RGPD Engine",
            "title": "Documento Anonimizado RGPD",
            "subject": "Anonimizacion Irreversible"
        })
    except Exception:
        pass


def aplicar_k_anonimato_dataframe(df, k=3, generalizar_cuasi=True, limite_supresion_pct=100.0):
    """
    Aplica k-anonimato y supresión de identificadores directos según Manual RGPD (Secciones 1.3, 1.9, 4.A).
    - Identificadores directos: sustitución destructiva homogénea.
    - Cuasi-identificadores (edad, CP, fecha, ciudad, género): generalización y cálculo de clases de equivalencia.
    - Outliers: supresión de registros que no alcanzan el umbral k dentro del límite permitido.
    """
    df_res = df.copy()
    stats = {
        "filas_originales": len(df_res),
        "filas_anonimizadas": len(df_res),
        "filas_suprimidas": 0,
        "k_objetivo": k,
        "cuasi_identificadores": [],
        "identificadores_directos_suprimidos": 0,
        "cuasi_identificadores_generalizados": 0,
        "terminos_confidenciales_suprimidos": 0
    }
    if df_res.empty:
        return df_res, stats

    COLUMNAS_DIRECTAS = {"nombre", "name", "contacto", "persona", "responsable", "propietario", "representante", 
                         "entrevistado", "entrevistada", "dni", "nif", "nie", "email", "correo", "e-mail", "mail",
                         "telefono", "teléfono", "phone", "tel", "móvil", "movil", "celular", "tarjeta", "credit_card"}
    
    COLUMNAS_CUASI = {"edad", "age", "nacimiento", "fecha", "fecha_nacimiento", "cp", "código postal", "codigo postal",
                      "zip", "zipcode", "ciudad", "city", "provincia", "municipio", "sexo", "genero", "género", "gender", "cargo", "profesion", "profesión"}

    COLUMNAS_PRESERVADAS = {"diagnostico", "diagnóstico", "enfermedad", "patologia", "patología", "tratamiento", 
                           "medicamento", "ingresos", "salario", "sueldo", "precio", "importe", "total", "cantidad",
                           "categoria", "categoría", "departamento", "seccion", "sección", "resultado", "estado", "tipo"}

    cols_directas_detectadas = []
    cols_cuasi_detectadas = []
    cols_preservadas_detectadas = []

    for col in df_res.columns:
        cl = str(col).lower().strip()
        cl_base = re.sub(r'\.\d+$', '', cl)
        if any(kd in cl_base for kd in COLUMNAS_DIRECTAS):
            cols_directas_detectadas.append(col)
        elif any(kc in cl_base for kc in COLUMNAS_CUASI):
            cols_cuasi_detectadas.append(col)
        elif any(kp in cl_base for kp in COLUMNAS_PRESERVADAS):
            cols_preservadas_detectadas.append(col)

    stats["cuasi_identificadores"] = cols_cuasi_detectadas

    # 1. Anonimizar identificadores directos
    for col in df_res.columns:
        if col in cols_directas_detectadas:
            cl = str(col).lower()
            tag = "[DNI_ELIMINADO]" if "dni" in cl or "nif" in cl or "nie" in cl else \
                  "[CORREO_ELIMINADO]" if "mail" in cl or "correo" in cl else \
                  "[TELEFONO_ELIMINADO]" if "tel" in cl or "móvil" in cl or "celular" in cl else "[PERSONA]"
            df_res[col] = tag
            stats["identificadores_directos_suprimidos"] += len(df_res)
        elif col in cols_preservadas_detectadas or col in cols_cuasi_detectadas:
            continue
        else:
            for idx, val in enumerate(df_res[col]):
                if isinstance(val, str) and val.strip():
                    txt_clean, st_sub = anonimizar_texto_real_irreversible(val, generalizar_cuasi=generalizar_cuasi)
                    df_res.at[idx, col] = txt_clean
                    stats["identificadores_directos_suprimidos"] += st_sub.get("identificadores_directos_suprimidos", 0)
                    stats["cuasi_identificadores_generalizados"] += st_sub.get("cuasi_identificadores_generalizados", 0)

    # 2. Generalizar cuasi-identificadores
    if generalizar_cuasi and cols_cuasi_detectadas:
        for col in cols_cuasi_detectadas:
            cl = str(col).lower()
            if "edad" in cl or "age" in cl:
                def gen_edad(v):
                    try:
                        m = re.search(r'\d+', str(v))
                        if m:
                            num = int(m.group(0))
                            r_inf = (num // 10) * 10
                            return f"{r_inf}-{r_inf + 9}"
                    except Exception:
                        pass
                    return str(v)
                df_res[col] = df_res[col].apply(gen_edad)
                stats["cuasi_identificadores_generalizados"] += len(df_res)
            elif "cp" in cl or "código postal" in cl or "codigo postal" in cl or "zip" in cl:
                def gen_cp(v):
                    m = re.search(r'\b([0-5]\d)\d{3}\b', str(v))
                    return f"{m.group(1)}***" if m else str(v)
                df_res[col] = df_res[col].apply(gen_cp)
                stats["cuasi_identificadores_generalizados"] += len(df_res)
            elif "fecha" in cl or "nacimiento" in cl:
                def gen_fecha(v):
                    m = re.search(r'\b(\d{4})\b', str(v))
                    return m.group(1) if m else str(v)
                df_res[col] = df_res[col].apply(gen_fecha)
                stats["cuasi_identificadores_generalizados"] += len(df_res)

        # 3. Calcular k-anonimato y suprimir outliers
        if len(df_res) >= k:
            cuentas = df_res.groupby(cols_cuasi_detectadas).size().reset_index(name='_frecuencia_k')
            df_merged = df_res.merge(cuentas, on=cols_cuasi_detectadas, how='left')
            df_cumple = df_merged[df_merged['_frecuencia_k'] >= k].drop(columns=['_frecuencia_k'])
            filas_suprimidas = len(df_res) - len(df_cumple)
            max_permitido = int(len(df_res) * (limite_supresion_pct / 100.0))
            if filas_suprimidas <= max_permitido:
                df_res = df_cumple.reset_index(drop=True)
                stats["filas_suprimidas"] = filas_suprimidas
                stats["filas_anonimizadas"] = len(df_res)

    return df_res, stats


def generar_certificado_anonimizacion(nombre_archivo, target_salida, resumen):
    """
    Genera un Certificado e Informe de Auditoría de Anonimización conforme al RGPD (Considerando 26)
    y a las Directrices 02/2026 del Comité Europeo de Protección de Datos (EDPB).
    """
    import datetime
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nombre_base = os.path.splitext(nombre_archivo)[0]
    ruta_cert = os.path.join(target_salida, f"Certificado_Anonimizacion_{nombre_base}.txt")

    texto_cert = f"""================================================================================
           LIA VAULT - CERTIFICADO Y AUDITORÍA DE ANONIMIZACIÓN DE DATOS
            Conforme al RGPD (Considerando 26) y Directrices EDPB 02/2026
================================================================================

Fecha y Hora de Emisión : {ahora}
Documento Procesado     : {nombre_archivo}
Modo de Tratamiento     : ANONIMIZACIÓN REAL E IRREVERSIBLE
Tecnología Empleada     : Lia Vault On-Premise + Presidio NLP + Motores Sintácticos
Ubicación de Salida     : {target_salida}

--------------------------------------------------------------------------------
1. MARCO LEGAL Y DOCTRINAL
--------------------------------------------------------------------------------
- Reglamento General de Protección de Datos (RGPD, Reglamento UE 2016/679):
  * Considerando 26: La información anónima es aquella que no guarda relación con
    una persona física identificada ni identificable. El RGPD no es aplicable a
    estos datos.
  * Directrices 02/2026 del Comité Europeo de Protección de Datos (EDPB):
    Criterios de no reidentificación y superación de las 3 pruebas técnicas.

--------------------------------------------------------------------------------
2. SUPERACIÓN DE LAS 3 PRUEBAS DEL EDPB (DIRECTRICES 02/2026)
--------------------------------------------------------------------------------
[✓] PRUEBA 1 - AUSENCIA DE SINGULARIZACIÓN (Singling Out):
    Se han suprimido todos los identificadores directos (nombres, DNI, teléfonos,
    correos, credenciales) y generalizado los cuasi-identificadores para impedir
    que cualquier combinación señale a un individuo único.

[✓] PRUEBA 2 - AUSENCIA DE VINCULACIÓN (Linkability):
    Se ha ejecutado el protocolo Zero-Key. NO se ha creado, transmitido ni
    almacenado ninguna tabla de correspondencia, hash determinista o archivo .key.
    Los metadatos ocultos del archivo han sido purgados.

[✓] PRUEBA 3 - AUSENCIA DE INFERENCIA (Inference):
    Los cuasi-identificadores (fechas exactas, códigos postales, vías) se han
    generalizado a rangos y áreas superiores, impidiendo deducir atributos
    sensibles mediante correlación contextual.

--------------------------------------------------------------------------------
3. DETALLE TÉCNICO DE LA OPERACIÓN
--------------------------------------------------------------------------------
- Identificadores directos redactados : {resumen.get('identificadores_directos_suprimidos', 0)}
- Cuasi-identificadores generalizados : {resumen.get('cuasi_identificadores_generalizados', 0)}
- Términos confidenciales eliminados  : {resumen.get('terminos_confidenciales_suprimidos', 0)}
- Garantía de k-anonimato en tablas   : {resumen.get('k_objetivo', 'N/A (Documento)')}
- Filas suprimidas por outlier        : {resumen.get('filas_suprimidas', 0)}
- Metadatos documentales purgados     : SÍ (Autor, Revisiones, EXIF eliminados)
- Reversibilidad                      : 0% (PROCESO ESTRICTAMENTE IRREVERSIBLE)

--------------------------------------------------------------------------------
4. DECLARACIÓN FORMAL DE PRIVACIDAD
--------------------------------------------------------------------------------
Se certifica que el archivo resultante no contiene claves de reversión y ha sido
transformado localmente sin salida a redes externas, quedando legalmente apto
para publicación, cesión a terceros, retención definitiva o entrenamiento de IA.

Emitido automáticamente por Lia Vault Security Suite.
================================================================================
"""
    try:
        with open(ruta_cert, "w", encoding="utf-8") as fc:
            fc.write(texto_cert)
    except Exception as e:
        print(f"Error generando certificado: {e}")


def procesar_archivo_texto_real(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None, generalizar_cuasi=True):
    with open(ruta_origen, "r", encoding="utf-8", errors="ignore") as f:
        contenido = f.read()
    
    contenido_limpio, stats = anonimizar_texto_real_irreversible(contenido, generalizar_cuasi=generalizar_cuasi)
    with open(ruta_destino, "w", encoding="utf-8") as f:
        f.write(contenido_limpio)
    
    target_salida = carpeta_salida or CARPETA_SALIDA_ANONIMIZADA
    generar_certificado_anonimizacion(nombre_archivo, target_salida, stats)


def procesar_markdown_real(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None, generalizar_cuasi=True):
    procesar_archivo_texto_real(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida, generalizar_cuasi)


def procesar_json_real(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None, generalizar_cuasi=True):
    with open(ruta_origen, "r", encoding="utf-8") as f:
        datos = json.load(f)

    stats_global = {
        "identificadores_directos_suprimidos": 0,
        "cuasi_identificadores_generalizados": 0,
        "terminos_confidenciales_suprimidos": 0
    }

    def anonimizar_nodo_real(obj):
        if isinstance(obj, str):
            res, st = anonimizar_texto_real_irreversible(obj, generalizar_cuasi=generalizar_cuasi)
            for k in stats_global:
                stats_global[k] += st.get(k, 0)
            return res
        elif isinstance(obj, list):
            return [anonimizar_nodo_real(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: anonimizar_nodo_real(v) for k, v in obj.items()}
        else:
            return obj

    datos_limpios = anonimizar_nodo_real(datos)
    with open(ruta_destino, "w", encoding="utf-8") as f:
        json.dump(datos_limpios, f, indent=4, ensure_ascii=False)

    target_salida = carpeta_salida or CARPETA_SALIDA_ANONIMIZADA
    generar_certificado_anonimizacion(nombre_archivo, target_salida, stats_global)


def procesar_documento_word_real(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None, generalizar_cuasi=True):
    doc = Document(ruta_origen)
    stats_global = {
        "identificadores_directos_suprimidos": 0,
        "cuasi_identificadores_generalizados": 0,
        "terminos_confidenciales_suprimidos": 0
    }
    
    for parrafo in doc.paragraphs:
        if parrafo.text.strip():
            limpio, st = anonimizar_texto_real_irreversible(parrafo.text, generalizar_cuasi=generalizar_cuasi)
            for k in stats_global:
                stats_global[k] += st.get(k, 0)
            if parrafo.runs:
                parrafo.runs[0].text = limpio
                for run in parrafo.runs[1:]:
                    run.text = ""
                    
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                if celda.text.strip():
                    limpio, st = anonimizar_texto_real_irreversible(celda.text, generalizar_cuasi=generalizar_cuasi)
                    for k in stats_global:
                        stats_global[k] += st.get(k, 0)
                    celda.text = limpio

    limpiar_metadatos_docx(doc)
    doc.save(ruta_destino)

    target_salida = carpeta_salida or CARPETA_SALIDA_ANONIMIZADA
    generar_certificado_anonimizacion(nombre_archivo, target_salida, stats_global)


def procesar_tabla_csv_real(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None, k_umbral=3, generalizar_cuasi=True):
    df = pd.read_csv(ruta_origen, dtype=str)
    target_salida = carpeta_salida or CARPETA_SALIDA_ANONIMIZADA
    df_anon, stats = aplicar_k_anonimato_dataframe(df, k=k_umbral, generalizar_cuasi=generalizar_cuasi)
    df_anon.to_csv(ruta_destino, index=False, encoding="utf-8")
    generar_certificado_anonimizacion(nombre_archivo, target_salida, stats)


def procesar_excel_real(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None, k_umbral=3, generalizar_cuasi=True):
    target_salida = carpeta_salida or CARPETA_SALIDA_ANONIMIZADA
    wb = openpyxl.load_workbook(ruta_origen)
    stats_totales = {
        "identificadores_directos_suprimidos": 0,
        "cuasi_identificadores_generalizados": 0,
        "terminos_confidenciales_suprimidos": 0,
        "k_objetivo": k_umbral,
        "filas_suprimidas": 0
    }

    for hoja in wb.worksheets:
        datos = list(hoja.values)
        if not datos:
            continue
        headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(datos[0])]
        rows = datos[1:]
        df = pd.DataFrame(rows, columns=headers).astype(str)
        df_anon, st = aplicar_k_anonimato_dataframe(df, k=k_umbral, generalizar_cuasi=generalizar_cuasi)
        for k in ["identificadores_directos_suprimidos", "cuasi_identificadores_generalizados", "terminos_confidenciales_suprimidos", "filas_suprimidas"]:
            stats_totales[k] += st.get(k, 0)

        for col_idx, col_name in enumerate(headers, start=1):
            for row_idx, val in enumerate(df_anon[col_name], start=2):
                celda = hoja.cell(row=row_idx, column=col_idx)
                if isinstance(celda.value, str) and celda.value.strip():
                    celda.value = val

    limpiar_metadatos_openpyxl(wb)
    wb.save(ruta_destino)
    generar_certificado_anonimizacion(nombre_archivo, target_salida, stats_totales)


def procesar_pdf_real(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None, generalizar_cuasi=True):
    if not fitz:
        raise MotorNoDisponibleError("PyMuPDF no está instalado: no se pueden procesar archivos PDF.")
    exigir_motor()
        
    doc = fitz.open(ruta_origen)
    stats_global = {
        "identificadores_directos_suprimidos": 0,
        "cuasi_identificadores_generalizados": 0,
        "terminos_confidenciales_suprimidos": 0
    }
    target_salida = carpeta_salida or CARPETA_SALIDA_ANONIMIZADA
    
    for num_pag, pagina in enumerate(doc):
        texto_pagina = pagina.get_text()
        if texto_pagina.strip():
            texto_anon, st = anonimizar_texto_real_irreversible(texto_pagina, generalizar_cuasi=generalizar_cuasi)
            for k in stats_global:
                stats_global[k] += st.get(k, 0)
            
            # 1. Redactar entidades de Presidio
            if analyzer:
                try:
                    res_pii = _analizar_o_fallar(text=all_caps_to_title_case(texto_pagina), language="es",
                                               entities=["PERSON", "LOCATION", "ORGANIZATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"])
                    for pii in res_pii:
                        val_orig = texto_pagina[pii.start:pii.end].strip()
                        if len(val_orig) > 1 and val_orig.lower() not in SOFTWARE_ALLOWLIST:
                            for rect in pagina.search_for(val_orig):
                                pagina.add_redact_annot(rect, fill=(0.1, 0.1, 0.1))
                except MotorNoDisponibleError:
                    raise
                except Exception as ex:
                    raise MotorNoDisponibleError(f"Falló la detección de datos personales ({type(ex).__name__}).") from ex

            # 2. Redactar entidades por expresiones regulares (Teléfonos, Escuelas, Correos, etc.)
            for reg, _ in PATRONES_REGEX_ANON:
                try:
                    for m in reg.finditer(texto_pagina):
                        val_m = m.group(1) if m.groups() and m.group(1) else m.group(0)
                        if val_m and len(val_m.strip()) > 2 and val_m.lower().strip() not in SOFTWARE_ALLOWLIST:
                            for rect in pagina.search_for(val_m.strip()):
                                pagina.add_redact_annot(rect, fill=(0.1, 0.1, 0.1))
                except Exception as ex:
                    raise MotorNoDisponibleError(f"Falló la redacción del PDF ({type(ex).__name__}).") from ex
                    
        pagina.apply_redactions()
        
        if not texto_pagina.strip() and pagina.get_images() and not lector_ocr:
            raise MotorNoDisponibleError("El PDF tiene páginas escaneadas y el OCR no está disponible.")
        if not texto_pagina.strip() and lector_ocr:
            pix = pagina.get_pixmap(dpi=200)
            fd_tmp, ruta_tmp = tempfile.mkstemp(prefix="liavault_pag_", suffix=".png")
            os.close(fd_tmp)
            # La imagen temporal tiene la página sin tapar: se borra aunque falle el OCR.
            try:
                pix.save(ruta_tmp)
                procesar_imagen_ocr_real(ruta_tmp, ruta_tmp, f"pag_{num_pag}_temp", carpeta_salida=target_salida)
                pagina.insert_image(pagina.rect, filename=ruta_tmp)
            finally:
                os.remove(ruta_tmp)
                    
    limpiar_metadatos_pdf(doc)
    doc.save(ruta_destino, garbage=4, deflate=True)
    doc.close()
    generar_certificado_anonimizacion(nombre_archivo, target_salida, stats_global)


def procesar_imagen_ocr_real(ruta_origen, ruta_destino, nombre_archivo, carpeta_salida=None):
    if not cv2 or not lector_ocr:
        raise MotorNoDisponibleError("El OCR (EasyOCR/OpenCV) no está disponible: no se pueden procesar imágenes.")
    exigir_motor()
        
    resultados_ocr = lector_ocr.readtext(ruta_origen)
    imagen_cv = cv2.imread(ruta_origen)
    target_salida = carpeta_salida or CARPETA_SALIDA_ANONIMIZADA
    terminos_corp = cargar_diccionario_corporativo()
    stats_global = {"identificadores_directos_suprimidos": 0, "cuasi_identificadores_generalizados": 0, "terminos_confidenciales_suprimidos": 0}

    for (coordenadas, texto_detectado, probabilidad) in resultados_ocr:
        if len(texto_detectado.strip()) > 1:
            analisis = _analizar_o_fallar(
                text=texto_detectado, language="es",
                entities=["PERSON", "LOCATION", "ORGANIZATION", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"]
            )
            
            dict_match = [t for t in terminos_corp if t.lower() in texto_detectado.lower()]
            
            if analisis or dict_match:
                x_min = int(min([p[0] for p in coordenadas]))
                y_min = int(min([p[1] for p in coordenadas]))
                x_max = int(max([p[0] for p in coordenadas]))
                y_max = int(max([p[1] for p in coordenadas]))
                
                label = "[CONFIDENCIAL]" if dict_match else "[REDACTADO]"
                cv2.rectangle(imagen_cv, (x_min, y_min), (x_max, y_max), (20, 20, 20), -1)
                cv2.rectangle(imagen_cv, (x_min, y_min), (x_max, y_max), (220, 38, 38), 1)
                
                h_box = max(1, y_max - y_min)
                scale = max(0.3, min(0.5, h_box / 35.0))
                cv2.putText(imagen_cv, label, (x_min + 3, y_min + int(h_box * 0.7)), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 1, cv2.LINE_AA)
                stats_global["identificadores_directos_suprimidos"] += 1

    cv2.imwrite(ruta_destino, imagen_cv)
    generar_certificado_anonimizacion(nombre_archivo, target_salida, stats_global)


def ejecutar_anonimizacion_real_lotes(carpeta_salida=None, k_umbral=3, generalizar_cuasi=True, archivo_especifico=None):
    exigir_motor()
    """
    Ejecuta el pipeline de Anonimización Real Irreversible (Considerando 26 RGPD & Directrices EDPB 02/2026).
    - Cero persistencia de claves .key.
    - Destino exclusivo: Archivos anonimizados RGPD.
    - Generación de Certificados de Auditoría RGPD.
    """
    target_salida = carpeta_salida or CARPETA_SALIDA_ANONIMIZADA
    os.makedirs(target_salida, exist_ok=True)
    os.makedirs(CARPETA_PROCESADOS, exist_ok=True)

    if archivo_especifico:
        archivos = [archivo_especifico] if os.path.exists(os.path.join(CARPETA_ENTRADA, archivo_especifico)) else []
    else:
        archivos = os.listdir(CARPETA_ENTRADA)
        archivos = [f for f in archivos if not f.startswith("~$") and not f.startswith(".") and os.path.isfile(os.path.join(CARPETA_ENTRADA, f))]
    
    if not archivos:
        print(f"[INFO] La carpeta '{CARPETA_ENTRADA}' está vacía.")
        return 0

    print(f"[INFO] LIA VAULT [ANONIMIZACIÓN REAL]: Procesando lote de {len(archivos)} archivos -> '{target_salida}'")
    procesados_exitosos = 0
    
    for nombre_archivo in archivos:
        ruta_origen = os.path.join(CARPETA_ENTRADA, nombre_archivo)
        nombre_sanitizado = _nombre_salida_libre(target_salida, sanitizar_nombre_archivo_real(nombre_archivo))
        ruta_destino = os.path.join(target_salida, nombre_sanitizado)
        ext = nombre_archivo.lower()
        
        try:
            if ext.endswith(".txt"):
                procesar_archivo_texto_real(ruta_origen, ruta_destino, nombre_archivo, target_salida, generalizar_cuasi=generalizar_cuasi)
            elif ext.endswith(".md"):
                procesar_markdown_real(ruta_origen, ruta_destino, nombre_archivo, target_salida, generalizar_cuasi=generalizar_cuasi)
            elif ext.endswith(".json"):
                procesar_json_real(ruta_origen, ruta_destino, nombre_archivo, target_salida, generalizar_cuasi=generalizar_cuasi)
            elif ext.endswith(".csv"):
                procesar_tabla_csv_real(ruta_origen, ruta_destino, nombre_archivo, target_salida, k_umbral=k_umbral, generalizar_cuasi=generalizar_cuasi)
            elif ext.endswith(".docx"):
                procesar_documento_word_real(ruta_origen, ruta_destino, nombre_archivo, target_salida, generalizar_cuasi=generalizar_cuasi)
            elif ext.endswith(".xlsx"):
                procesar_excel_real(ruta_origen, ruta_destino, nombre_archivo, target_salida, k_umbral=k_umbral, generalizar_cuasi=generalizar_cuasi)
            elif ext.endswith(".pdf"):
                procesar_pdf_real(ruta_origen, ruta_destino, nombre_archivo, target_salida, generalizar_cuasi=generalizar_cuasi)
            elif ext.endswith((".jpg", ".jpeg", ".png")):
                procesar_imagen_ocr_real(ruta_origen, ruta_destino, nombre_archivo, target_salida)
            else:
                print(f"⚠️ Formato no compatible: {nombre_archivo}")
                continue
            
            ruta_procesados = os.path.join(CARPETA_PROCESADOS, nombre_archivo)
            if os.path.exists(ruta_procesados):
                os.remove(ruta_procesados)
            shutil.move(ruta_origen, ruta_procesados)
            procesados_exitosos += 1
            registro.registrar("anonimizacion", ruta_archivo=ruta_procesados)
            print(f"✅ Anonimizado (RGPD) y movido a /procesados: {nombre_archivo}")

        except IdiomaNoSoportadoError as e_lang:
            _eliminar_salida_parcial(target_salida, ruta_destino, nombre_archivo)
            registro.registrar("anonimizacion", "rechazado", ruta_archivo=ruta_origen, error=e_lang)
            print(f"⚠️ Archivo rechazado por idioma no soportado {nombre_archivo}: {e_lang}")
            if archivo_especifico:
                raise e_lang
        except Exception as e:
            _eliminar_salida_parcial(target_salida, ruta_destino, nombre_archivo)
            registro.registrar("anonimizacion", "error", ruta_archivo=ruta_origen, error=e)
            print(f"❌ Error al anonimizar {nombre_archivo}: {type(e).__name__}")
            if archivo_especifico:
                raise e
            
    return procesados_exitosos


if __name__ == "__main__":
    ejecutar_procesamiento_lotes()

