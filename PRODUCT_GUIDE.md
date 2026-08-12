# 🛡️ Guía Completa de Producto - Lia Vault

**Lia Vault: On-Premise Privacy & Anonymization Suite**  
*Escudo de Privacidad Local, Anonimización Inteligente y Cumplimiento Normativo (RGPD / Reglamento de Inteligencia Artificial de la UE).*

---

## 📋 Índice
1. [Visión General y Propuesta de Valor](#-visión-general-y-propuesta-de-valor)
2. [Arquitectura y Tecnologías Clave](#-arquitectura-y-tecnologías-clave)
3. [Características Funcionales Destacadas](#-características-funcionales-destacadas)
4. [Cumplimiento Normativo (RGPD & Ley de IA EU)](#-cumplimiento-normativo-rgpd--ley-de-ia-eu)
5. [Opciones de Despliegue](#-opciones-de-despliegue)
6. [❓ Preguntas Frecuentes del Cliente (FAQ Comercial & Técnico)](#-preguntas-frecuentes-del-cliente-faq-comercial--técnico)
   - [🔒 Seguridad y Privacidad](#-seguridad-y-privacidad)
   - [📄 Formatos y Procesamiento](#-formatos-y-procesamiento)
   - [🔐 Reversibilidad Criptográfica](#-reversibilidad-criptográfica)
   - [🔑 Licenciamiento Offline](#-licenciamiento-offline)
   - [⚙️ Personalización y Diccionarios](#-personalización-y-diccionarios)
   - [⚡ Rendimiento y Escalabilidad](#-rendimiento-y-escalabilidad)
   - [🤖 Integración con IA y LLMs](#-integración-con-ia-y-llms)

---

## 💡 Visión General y Propuesta de Valor

**Lia Vault** es una solución de grado empresarial diseñada para la **anonimización, redacción visual y protección de datos sensibles en documentos corporativos**. Funciona de manera **100% offline y local**, garantizando que ningún dato confidencial o PII (Información Personal Identificable) salga de la red corporativa.

### ¿Por qué Lia Vault?
- **Riesgo Cero de Fuga de Datos:** Procesa archivos en el hardware local sin enviar datos a APIs externas o la nube.
- **Preparación para IA Segura:** Permite compartir documentos de forma segura con modelos de lenguaje (LLMs como OpenAI, Anthropic, Mistral) tras haber eliminado o tokenizado la información confidencial.
- **Cumplimiento Automático:** Diseñado según los requisitos del RGPD (Reglamento General de Protección de Datos) y la Ley de Inteligencia Artificial de la UE (EU AI Act).

---

## 🛠️ Arquitectura y Tecnologías Clave

- **Motor NLP/NLU:** Basado en Microsoft Presidio + spaCy (modelo optimizado `es_core_news_sm`).
- **Motor OCR Integrado:** EasyOCR para redacción y extracción gráfica en imágenes (`.png`, `.jpg`) y PDFs escaneados.
- **Interfaces Disponibles:**
  - **Desktop GUI:** Interfaz nativa Flet (Python + Material Design con soporte de modo oscuro).
  - **Web Suite:** Aplicación React 19 + Vite + Express para entornos web/intranet.
- **Criptografía:** Generación de llaves de reversión `.reverse.key` mediante cifrado AES-256 / HMAC RSA para recuperar datos cuando sea autorizado.

---

## ✨ Características Funcionales Destacadas

1. **Detección Multientidad Automatizada:**
   - DNI / NIE / NIF (España y Latinoamérica).
   - IBANs y Números de Cuenta Bancaria.
   - Tarjetas de Crédito y Débito.
   - Nombres de Personas, Direcciones y Ubicaciones.
   - Correos Electrónicos y Números Telefónicos.
   - Fechas, Edades y Datos Médicos u Homólogos.

2. **Soporte Multiformato:**
   - Documentos de texto: `.pdf` (digitales y escaneados), `.docx`, `.txt`.
   - Hojas de cálculo: `.xlsx`, `.csv`.
   - Imágenes gráficas: `.png`, `.jpg`, `.jpeg`, `.tiff`.

3. **Redacción Irreversible en Imágenes / PDFs Escaneados:**
   - Aplicación de máscaras negras / blur visual directamente sobre los mapas de bits donde se ubican las entidades detectadas por OCR.

4. **Diccionario Corporativo Personalizable:**
   - Carga de listas de exclusión o términos específicos de la organización (`diccionario_corporativo.txt`) para ignorar nombres comerciales autorizados o forzar reemplazos a medida.

---

## ⚖️ Cumplimiento Normativo (RGPD & Ley de IA EU)

| Requisito Normativo | Cobertura en Lia Vault |
| :--- | :--- |
| **Privacidad desde el Diseño (Art. 25 RGPD)** | Arquitectura 100% On-Premise sin llamadas de red externas. |
| **Derecho al Olvido / Mapeo de PII** | Sustitución completa de identificadores personales por tokens sintéticos. |
| **Ley de IA EU (Gobernanza de Datos)** | Garantiza que los datasets enviados a prompts o fine-tuning de IA no contengan PII no autorizada. |
| **Trazabilidad y Auditoría** | Registro local criptográfico de archivos procesados y firmas de validación. |

---

## 🚀 Opciones de Despliegue

1. **Empaquetado Nativo (1-Clic):**
   - Ejecutables directos para Windows (`.bat`), macOS (`.command`) y Linux (`.sh`) sin requerir configuración previa por parte del usuario final.
2. **Web Suite Intranet:**
   - Servidor Node.js/Express + React para despliegue centralizado en la red local de la empresa.
3. **Contenedores Docker:**
   - Despliegue mediante `docker-compose` o imágenes Docker aisladas en infraestructura en la nube privada o servidores dedicados.

---

## ❓ Preguntas Frecuentes del Cliente (FAQ Comercial & Técnico)

### 🔒 Seguridad y Privacidad

#### ¿Lia Vault envía algún dato o estadística fuera de nuestra red?
**No.** Lia Vault es 100% offline. No realiza llamadas de telemetría, no envía archivos a servidores externos ni requiere conexión a Internet para procesar documentos ni para validar su licencia.

#### ¿Los modelos de IA/NLP utilizados descargan datos sobre la marcha?
**No.** Todos los modelos de Lenguaje Natural (spaCy) y bibliotecas de OCR (EasyOCR/PyTorch) están preempaquetados localmente.

---

### 📄 Formatos y Procesamiento

#### ¿Qué ocurre con los PDFs escaneados o imágenes de baja calidad?
Lia Vault integra un motor de OCR (Reconocimiento Óptico de Caracteres). Analiza la estructura visual del archivo, extrae el texto, detecta las entidades sensibles y aplica un enmascaramiento visual (recuadros negros) sobre el documento final.

#### ¿Se conserva el formato original de los documentos Word o Excel?
**Sí.** El motor reemplaza el texto confidencial respetando la estructura, estilos y celdas de los archivos `.docx`, `.xlsx` y `.csv`.

---

### 🔐 Reversibilidad Criptográfica

#### ¿Qué es el archivo `.reverse.key` y cómo funciona la des-anonimización?
Durante el proceso de anonimización, Lia Vault crea un mapa de equivalencias cifrado (por ejemplo: `Juan Pérez` $\rightarrow$ `[PERSONA_1]`). Este mapa se guarda en un archivo `.reverse.key`. Solo quienes posean este archivo y los permisos correspondientes pueden revertir el proceso y recuperar los datos originales.

#### ¿Es obligatorio guardar la llave de reversión?
No. Si el usuario desea una anonimización destructiva e irreversible (por ejemplo, para publicar datos abiertos), puede deshabilitar la generación de la llave de reversión.

---

### 🔑 Licenciamiento Offline

#### ¿Cómo valida Lia Vault su licencia si no tiene conexión a Internet?
Lia Vault incluye un sistema de validación criptográfica offline (`validador.py`). Utiliza una firma RSA/HMAC contenida en `licencia.key`. El sistema verifica localmente la vigencia y evita la manipulación del reloj del sistema.

#### ¿Qué sucede cuando una licencia caduca?
La aplicación mostrará una advertencia al usuario impidiendo nuevos procesamientos hasta que se reemplace el archivo `licencia.key` por uno renovado.

---

### ⚙️ Personalización y Diccionarios

#### ¿Es posible evitar que anonimice el nombre de nuestra empresa o marcas registradas?
**Sí.** A través del **Diccionario Corporativo** (`diccionario_corporativo.txt`), puede definir una lista blanca (*whitelist*) de términos que el motor NLP debe omitir.

#### ¿Podemos agregar patrones de regex personalizados (ejemplo: códigos de cliente internos)?
**Sí.** Se pueden añadir reglas personalizadas para detectar formatos específicos de la organización como matrículas, IDs de empleados o códigos de expedientes.

---

### ⚡ Rendimiento y Escalabilidad

#### ¿Cuáles son los requisitos mínimos de hardware?
- **CPU:** Procesador Quad-Core (Intel i5/AMD Ryzen 5 o superior).
- **RAM:** 8 GB mínimo (16 GB recomendado para PDFs voluminosos u OCR intensivo).
- **Almacenamiento:** 2 GB libres en disco.

#### ¿Puede procesar lotes masivos de documentos?
**Sí.** La suite soporta procesamiento por lotes (*batch processing*), procesando automáticamente todos los archivos depositados en el directorio de entrada.

---

### 🤖 Integración con IA y LLMs

#### ¿Cómo me ayuda Lia Vault al usar herramientas como ChatGPT o Copilot?
Antes de copiar y pegar un texto o subir un documento a un LLM comercial, el usuario lo procesa en Lia Vault. Este sustituye los datos confidenciales por etiquetas sintéticas (`[DNI_1]`, `[CLIENTE_A]`). Al recibir la respuesta del LLM, el usuario puede des-anonimizar el resultado usando su `.reverse.key` local.
