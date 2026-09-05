# -*- coding: utf-8 -*-
"""
 * @license
 * SPDX-License-Identifier: Apache-2.0
 """

import os
import sys
import shutil
import base64
import json
import platform
import subprocess
import flet as ft
import warnings
import ssl

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Parchear resolución de iconos y alineaciones de forma 100% segura
class SafeIconsProxy:
    def __init__(self, target):
        self._target = target
    def __getattr__(self, name):
        if hasattr(self._target, name):
            return getattr(self._target, name)
        # Fallbacks seguros por similitud semántica
        upper_name = name.upper()
        if "SHIELD" in upper_name or "SECURITY" in upper_name or "LOCK" in upper_name:
            return getattr(self._target, "SHIELD_OUTLINED", getattr(self._target, "SHIELD", 72371))
        if "CHECK" in upper_name or "VERIF" in upper_name:
            return getattr(self._target, "CHECK", getattr(self._target, "VERIFIED_USER", 66861))
        if "DOC" in upper_name or "FILE" in upper_name or "TEXT" in upper_name:
            return getattr(self._target, "DESCRIPTION_OUTLINED", 67448)
        if "KEY" in upper_name or "VPN" in upper_name:
            return getattr(self._target, "VPN_KEY", 74031)
        return getattr(self._target, "HELP_OUTLINE", getattr(self._target, "CIRCLE", 66917))

_target_icons = getattr(ft, "Icons", getattr(ft.icons, "Icons", ft.icons))
ft.icons = SafeIconsProxy(_target_icons)
ft.Icons = ft.icons

ft.border.all = getattr(ft.border, "all", getattr(ft.border, "Border", None).all)
ft.MainAxisAlignment.BETWEEN = getattr(ft.MainAxisAlignment, "BETWEEN", ft.MainAxisAlignment.SPACE_BETWEEN)
ft.colors = getattr(ft, "colors", getattr(ft, "Colors", None))
ft.alignment.center = getattr(ft.alignment, "center", getattr(ft.alignment, "Alignment", None)(0, 0))
ft.alignment.center_right = getattr(ft.alignment, "center_right", getattr(ft.alignment, "Alignment", None)(1, 0))
ft.alignment.center_left = getattr(ft.alignment, "center_left", getattr(ft.alignment, "Alignment", None)(-1, 0))
if not hasattr(ft, "FileDropEvent"):
    class FileDropEvent:
        pass
    ft.FileDropEvent = FileDropEvent

from validador import ValidadorLicencia
from app_offline import (
    ejecutar_procesamiento_lotes, 
    ejecutar_anonimizacion_real_lotes,
    revertir_anonimizacion,
    ejecutar_reversion_archivo,
    CARPETA_ENTRADA, 
    CARPETA_SALIDA_DEFECTO,
    CARPETA_SALIDA_ANONIMIZADA,
    CARPETA_PROCESADOS,
    cargar_diccionario_corporativo,
    RUTA_DICCIONARIO
)
from i18n import t, get_current_language, set_current_language

# Paleta de colores "Lia Vault Premium Suite"
DARK_BACKGROUND = "#0F172A" # Slate 900
SURFACE_CARD = "#1E293B"     # Slate 800
ACCENT_ORANGE = "#F59E0B"    # Amber / Orange 500
NEON_BLUE = "#38BDF8"        # Sky 400
EMERALD_GREEN = "#10B981"    # Emerald 500
CRIMSON_ERROR = "#EF4444"    # Red 500
TEXT_MUTED = "#94A3B8"       # Slate 400

# SVG Logo base64 (Dos formas curvas solapadas carmesí y cian)
LOGO_SVG_RAW = """<svg width="200" height="200" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M 45 115 C 65 40 145 15 145 15 C 115 80 115 125 145 185 C 70 175 45 115 45 115 Z" fill="#E11D5A"/>
  <path d="M 100 110 C 120 70 170 50 170 50 C 148 90 148 125 170 160 C 120 150 100 110 100 110 Z" fill="#38BDF8" fill-opacity="0.85"/>
</svg>"""
LOGO_BASE64 = base64.b64encode(LOGO_SVG_RAW.encode("utf-8")).decode("utf-8")


ES_DOCKER = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") == "true"

def abrir_local(ruta):
    """Abre un archivo o carpeta en el explorador del sistema operativo local."""
    if ES_DOCKER:
        return  # En Docker no hay explorador de escritorio gráfico
    try:
        abs_path = os.path.abspath(ruta)
        if not os.path.exists(abs_path):
            return
        if platform.system() == "Darwin":      # macOS
            subprocess.run(["open", abs_path])
        elif platform.system() == "Windows":   # Windows
            subprocess.run(["explorer", abs_path])
        else:                                  # Linux
            subprocess.run(["xdg-open", abs_path])
    except Exception as e:
        print(f"Error abriendo ruta {ruta}: {e}")


async def main(page: ft.Page):
    page.title = "Lia Vault - Escudo de privacidad on-premise"
    page.bgcolor = DARK_BACKGROUND
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 24
    page.scroll = ft.ScrollMode.AUTO

    def abrir_url(url="https://checkpoint-ia.com"):
        try:
            page.launch_url(url, web_window_name="_blank")
        except Exception:
            pass
        # Fallback nativo de escritorio para asegurar apertura de navegador local
        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", url])
            elif platform.system() == "Windows":
                subprocess.run(["explorer", url])
            else:
                subprocess.run(["xdg-open", url])
        except Exception as ex:
            print(f"Error abriendo URL {url}: {ex}")

    validador = ValidadorLicencia()
    licencia_valida, mensaje_licencia, cliente_id, dias_restantes = validador.verificar_licencia_offline()

    # --- VARIABLES DE ESTADO DEL WORKSPACE ---
    lista_archivos_entrada = []
    carpeta_salida_configurada = os.path.abspath(CARPETA_SALIDA_DEFECTO)
    carpeta_salida_anonimizada_configurada = os.path.abspath(CARPETA_SALIDA_ANONIMIZADA)
    menu_activo = "sanitizador"
    archivo_seleccionado_preview = None
    archivo_seleccionado_preview_anon = None
    mapa_key_cargado_traduccion = {}
    archivo_anonimizado_traduccion_path = None
    nombre_archivo_traduccion_original = None

    # --- CONTROLES DE SEUDONIMIZACIÓN (REVERSIBLE) ---
    texto_estado_sanitizador = ft.Text(t("sanitizer_status_ready"), size=12, color=TEXT_MUTED)
    barra_progreso_sanitizador = ft.ProgressBar(visible=False, color=ACCENT_ORANGE)
    btn_procesar_lote = ft.ElevatedButton(t("sanitizer_btn_process"), icon=ft.icons.SHIELD, color="#FFFFFF", bgcolor=ACCENT_ORANGE, width=320, disabled=True)

    vista_cola_archivos = ft.ListView(expand=1, spacing=6, height=140)
    panel_inspector_preview = ft.Container(
        content=ft.Column([
            ft.Icon(ft.icons.REMOVE_RED_EYE_OUTLINED, size=28, color=TEXT_MUTED),
            ft.Text(t("sanitizer_preview_empty_title"), size=11, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Text(t("sanitizer_preview_empty_desc"), size=10, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=4),
        bgcolor="#1E293B44", padding=10, border_radius=8, border=ft.border.all(1, "#334155"), height=110, expand=True
    )

    vista_procesados_unificada = ft.ListView(expand=1, spacing=8, height=240)
    card_visibilidad_procesados_y_salida = ft.Container()

    # --- CONTROLES DE ANONIMIZACIÓN (IRREVERSIBLE - RGPD) ---
    texto_estado_anon = ft.Text(t("anon_status_ready"), size=12, color=TEXT_MUTED)
    barra_progreso_anon = ft.ProgressBar(visible=False, color=EMERALD_GREEN)
    btn_procesar_lote_anon = ft.ElevatedButton(t("anon_btn_process"), icon=ft.icons.VERIFIED_USER, color="#FFFFFF", bgcolor=EMERALD_GREEN, height=40, expand=True, disabled=True)

    dd_k_anonimato = ft.Dropdown(
        label="Nivel k-anonimato (Tablas)",
        options=[
            ft.dropdown.Option("3", "k = 3 (Uso interno / Retención)"),
            ft.dropdown.Option("5", "k = 5 (Cesión a terceros / Modelos IA)"),
            ft.dropdown.Option("10", "k = 10 (Máxima protección)")
        ],
        value="3",
        text_size=12,
        expand=True
    )
    chk_generalizar_cuasi = ft.Checkbox(
        label="Generalizar cuasi-identificadores (Fechas a años, CPs truncados)",
        value=True,
        check_color="#FFFFFF",
        active_color=EMERALD_GREEN,
        label_style=ft.TextStyle(size=12, color="#FFFFFF")
    )

    vista_cola_archivos_anon = ft.ListView(expand=1, spacing=6, height=180)
    panel_inspector_preview_anon = ft.Container(
        content=ft.Column([
            ft.Icon(ft.icons.REMOVE_RED_EYE_OUTLINED, size=28, color=TEXT_MUTED),
            ft.Text("Ningún archivo seleccionado", size=11, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Text("Seleccione un archivo para previsualizar.", size=10, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=4),
        bgcolor="#1E293B44", padding=10, border_radius=8, border=ft.border.all(1, "#334155"), height=110, expand=True
    )

    vista_anonimizados_unificada = ft.ListView(expand=1, spacing=8, height=240)
    card_visibilidad_anonimizados = ft.Container()

    dd_archivo_origen_key = ft.Dropdown(
        label="Documento procesado de origen",
        hint_text="Seleccione el documento de origen...",
        text_size=12,
        width=360
    )
    tf_texto_anonimizado = ft.TextField(hint_text="Pegue el texto o respuesta generada por la IA aquí...", multiline=True, min_lines=5, max_lines=8, text_size=12)
    txt_info_doc_traduccion = ft.Text("Sin archivo cargado", size=11, color=TEXT_MUTED)
    txt_info_key = ft.Text("Seleccione el documento de origen arriba para usar su llave automáticamente", size=11, color=TEXT_MUTED)
    tf_texto_restaurado = ft.TextField(hint_text="Resultado de la respuesta con datos reales restaurados...", multiline=True, min_lines=5, max_lines=8, read_only=True, text_size=12, color=EMERALD_GREEN)

    wrap_chips_dic = ft.Row(wrap=True, spacing=8)
    tf_nueva_palabra_dic = ft.TextField(hint_text="Término prohibido...", width=260, height=38, text_size=12, content_padding=8)

    # --- DRAG AND DROP NATIVO DE FLET ---
    def on_file_drop(e: ft.FileDropEvent):
        if e.files:
            count = 0
            for f_item in e.files:
                f_path = getattr(f_item, "path", str(f_item))
                if f_path and os.path.exists(f_path):
                    dest = os.path.join(CARPETA_ENTRADA, os.path.basename(f_path))
                    shutil.copy(f_path, dest)
                    count += 1
            refrescar_vistas_archivos()
            texto_estado_sanitizador.value = f"¡{count} archivo(s) agregados por arrastre!"
            texto_estado_sanitizador.color = EMERALD_GREEN
            page.update()

    page.on_file_drop = on_file_drop

    EXT_PERMITIDAS = {".txt", ".csv", ".docx", ".xlsx", ".pdf", ".png", ".jpg", ".jpeg", ".json", ".md"}
    ultimo_archivo_procesado = None

    def mostrar_dialogo_ver_documento(nombre_doc, ruta_doc):
        contenido = ""
        try:
            if os.path.exists(ruta_doc):
                if nombre_doc.endswith((".txt", ".csv", ".json", ".md")):
                    with open(ruta_doc, "r", encoding="utf-8", errors="ignore") as f:
                        contenido = f.read(3000)
                else:
                    contenido = f"📄 Archivo resguardado: {nombre_doc}\n\nLos archivos binarios (.pdf, .docx, .xlsx, .png) están procesados y disponibles en la carpeta /salida de tu sistema."
            else:
                contenido = "Archivo no encontrado."
        except Exception as ex:
            contenido = f"Error al leer contenido: {ex}"

        def cerrar_dlg(e):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.ARTICLE, color=EMERALD_GREEN, size=20),
                ft.Text(f"Documento Sanitizado: {nombre_doc}", size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF")
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.TextField(value=contenido, multiline=True, min_lines=8, max_lines=14, read_only=True, text_size=11, color="#E2E8F0")
                ], spacing=6),
                width=520, padding=4
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=cerrar_dlg)
            ]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def abrir_documento_o_dialogo(nombre_doc, ruta_doc):
        if ES_DOCKER:
            mostrar_dialogo_ver_documento(nombre_doc, ruta_doc)
        else:
            abrir_local(ruta_doc)

    def mostrar_dialogo_key(nombre_doc, ruta_k):
        def cerrar_dlg(e):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.VPN_KEY, color=ACCENT_ORANGE, size=20),
                ft.Text("Llave Criptográfica (.key)", size=13, weight=ft.FontWeight.BOLD, color="#FFFFFF")
            ]),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Documento: {nombre_doc}", size=11, weight=ft.FontWeight.BOLD, color=NEON_BLUE),
                    ft.Text(
                        "Este archivo contiene la matriz de tokens y datos sensibles generada por Lia Vault para la Traducción Inversa.\n\n"
                        "Está estructurado para lectura interna de la plataforma y no debe ser modificado ni abierto con programas externos (como Apple Keynote).",
                        size=11, color="#E2E8F0"
                    )
                ], spacing=8),
                width=380, padding=6
            ),
            actions=[
                ft.TextButton("Entendido", on_click=cerrar_dlg)
            ]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    # --- LÓGICA DE PROCESAMIENTO EN 1 CLIC ---
    def click_procesar_individual(fname):
        nonlocal ultimo_archivo_procesado
        _, ext = os.path.splitext(fname.lower())
        if ext not in EXT_PERMITIDAS:
            texto_estado_sanitizador.value = f"⚠️ {fname} no es un formato compatible."
            texto_estado_sanitizador.color = CRIMSON_ERROR
            page.update()
            return

        barra_progreso_sanitizador.visible = True
        texto_estado_sanitizador.value = f"Sanitizando {fname} con IA local..."
        texto_estado_sanitizador.color = ACCENT_ORANGE
        page.update()

        try:
            ejecutar_procesamiento_lotes(carpeta_salida=carpeta_salida_configurada)
            ultimo_archivo_procesado = fname
            texto_estado_sanitizador.value = f"¡Éxito! Archivo {fname} sanitizado y resguardado."
            texto_estado_sanitizador.color = EMERALD_GREEN
        except Exception as ex:
            texto_estado_sanitizador.value = f"Error: {str(ex)}"
            texto_estado_sanitizador.color = CRIMSON_ERROR

        barra_progreso_sanitizador.visible = False
        refrescar_vistas_archivos()

        try:
            card_visibilidad_procesados_y_salida.scroll_into_view()
        except Exception:
            pass

    def seleccionar_para_preview(nombre_archivo):
        nonlocal archivo_seleccionado_preview
        archivo_seleccionado_preview = nombre_archivo
        ruta_f = os.path.join(CARPETA_ENTRADA, nombre_archivo)
        _, ext_f = os.path.splitext(nombre_archivo.lower())
        es_comp = ext_f in EXT_PERMITIDAS
        
        contenido_preliminar = ""
        if os.path.exists(ruta_f):
            try:
                if nombre_archivo.endswith((".txt", ".csv", ".json", ".md")):
                    with open(ruta_f, "r", encoding="utf-8", errors="ignore") as f_in:
                        contenido_preliminar = f_in.read(300)
                else:
                    contenido_preliminar = f"Documento preparado para análisis: {nombre_archivo}"
            except Exception as ex:
                contenido_preliminar = f"Error de lectura: {ex}"

        panel_inspector_preview.content = ft.Column([
            ft.Row([
                ft.Icon(ft.icons.DESCRIPTION_OUTLINED if es_comp else ft.icons.WARNING_AMBER_ROUNDED, color=NEON_BLUE if es_comp else CRIMSON_ERROR, size=16),
                ft.Text(nombre_archivo, size=11, weight=ft.FontWeight.BOLD, color="#FFFFFF", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=220)
            ]),
            ft.Container(
                content=ft.Text(contenido_preliminar if es_comp else "⚠️ Formato no compatible. Formatos permitidos: .txt, .csv, .docx, .xlsx, .pdf, .json, .md, .png, .jpg", size=10, color="#E2E8F0" if es_comp else CRIMSON_ERROR),
                bgcolor="#0F172A", padding=6, border_radius=4, height=45
            ),
            ft.Row([
                ft.ElevatedButton("Abrir", icon=ft.icons.OPEN_IN_NEW, color="#FFFFFF", bgcolor="#334155", height=28, on_click=lambda _, fn=nombre_archivo, r=ruta_f: abrir_documento_o_dialogo(fn, r)),
                ft.ElevatedButton("Anonimizar ahora", icon=ft.icons.SHIELD, color="#FFFFFF", bgcolor=ACCENT_ORANGE if es_comp else "#475569", height=28, disabled=not es_comp, on_click=lambda _: click_procesar_individual(nombre_archivo))
            ], spacing=6)
        ], spacing=4)
        page.update()

    # --- FUNCIONES DE REFRESCO DEFINIDAS EN ÁMBITO MAIN ---
    def refrescar_vistas_archivos():
        nonlocal lista_archivos_entrada
        # 1. Cola de entrada
        try:
            todos = os.listdir(CARPETA_ENTRADA)
            lista_archivos_entrada = [f for f in todos if not f.startswith(".") and not f.startswith("~$") and os.path.isfile(os.path.join(CARPETA_ENTRADA, f))]
            texto_estado_sanitizador.value = t("sanitizer_queue_status", count=len(lista_archivos_entrada))
            texto_estado_sanitizador.color = NEON_BLUE
            btn_procesar_lote.disabled = len(lista_archivos_entrada) == 0
        except Exception as ex:
            texto_estado_sanitizador.value = t("sanitizer_status_error", error=str(ex))
            texto_estado_sanitizador.color = CRIMSON_ERROR

        vista_cola_archivos.controls.clear()
        if not lista_archivos_entrada:
            vista_cola_archivos.controls.append(
                ft.Container(
                    content=ft.Text(t("queue_empty_folder"), size=11, color=TEXT_MUTED, italic=True, text_align=ft.TextAlign.CENTER),
                    padding=10, alignment=ft.alignment.center
                )
            )
        else:
            for f in lista_archivos_entrada:
                ruta_f = os.path.join(CARPETA_ENTRADA, f)
                _, ext_f = os.path.splitext(f.lower())
                es_compatible = ext_f in EXT_PERMITIDAS

                def del_file(e, fname=f):
                    try:
                        os.remove(os.path.join(CARPETA_ENTRADA, fname))
                        refrescar_vistas_archivos()
                    except Exception as ex:
                        print(f"Error borrando: {ex}")

                vista_cola_archivos.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.icons.INSERT_DRIVE_FILE_OUTLINED if es_compatible else ft.icons.WARNING_AMBER_ROUNDED, color=NEON_BLUE if es_compatible else CRIMSON_ERROR, size=15),
                                    ft.Text(f, size=11, weight=ft.FontWeight.W_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=170),
                                    ft.Container(
                                        content=ft.Text(t("badge_incompatible"), size=9, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                                        bgcolor=CRIMSON_ERROR, padding=3, border_radius=3
                                    ) if not es_compatible else ft.Container()
                                ]),
                                expand=True,
                                on_click=lambda _, fn=f: seleccionar_para_preview(fn)
                            ),
                            ft.ElevatedButton(t("btn_anonymize_row"), icon=ft.icons.SHIELD, color="#FFFFFF", bgcolor=ACCENT_ORANGE if es_compatible else "#475569", height=26, disabled=not es_compatible, on_click=lambda _, fn=f: click_procesar_individual(fn)),
                            ft.IconButton(ft.icons.DELETE_OUTLINED, icon_size=14, icon_color=CRIMSON_ERROR, on_click=del_file)
                        ], alignment=ft.MainAxisAlignment.BETWEEN),
                        bgcolor="#1E293B66", padding=4, border_radius=4
                    )
                )

        # 2. Caja Unificada: Archivos seguros ya procesados
        vista_procesados_unificada.controls.clear()
        try:
            archivos_sal = [f for f in os.listdir(carpeta_salida_configurada) if not f.startswith(".") and not f.startswith("~$") and not f.endswith(".key")] if os.path.exists(carpeta_salida_configurada) else []
            archivos_sal.sort(key=lambda x: os.path.getmtime(os.path.join(carpeta_salida_configurada, x)), reverse=True)
        except Exception:
            archivos_sal = []

        if not archivos_sal:
            vista_procesados_unificada.controls.append(
                ft.Container(content=ft.Text(t("sanitizer_no_processed"), size=11, color=TEXT_MUTED, italic=True), padding=10)
            )
        else:
            for f in archivos_sal:
                ruta_doc = os.path.join(carpeta_salida_configurada, f)
                ruta_key1 = os.path.join(carpeta_salida_configurada, f"{f}.key")
                ruta_key2 = os.path.join(carpeta_salida_configurada, f"{f}.reverse.key")
                ruta_key = ruta_key1 if os.path.exists(ruta_key1) else (ruta_key2 if os.path.exists(ruta_key2) else None)

                es_reciente = False
                if ultimo_archivo_procesado:
                    base_orig = os.path.splitext(ultimo_archivo_procesado)[0].lower()
                    base_sal = os.path.splitext(f)[0].lower()
                    if base_orig == base_sal or base_orig in base_sal or base_sal in base_orig:
                        es_reciente = True

                vista_procesados_unificada.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Row([
                                ft.Icon(ft.icons.CHECK_CIRCLE_OUTLINED, color=EMERALD_GREEN, size=16),
                                ft.Text(f, size=12, weight=ft.FontWeight.W_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=200),
                                ft.Container(
                                    content=ft.Text(t("badge_new"), size=9, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                                    bgcolor=EMERALD_GREEN, padding=3, border_radius=3
                                ) if es_reciente else ft.Container()
                            ], expand=True),
                            ft.Row([
                                ft.ElevatedButton(t("btn_open_doc"), icon=ft.icons.OPEN_IN_NEW, color="#FFFFFF", bgcolor=ACCENT_ORANGE, height=30, on_click=lambda _, fn=f, r=ruta_doc: abrir_documento_o_dialogo(fn, r)),
                                ft.ElevatedButton(t("btn_key_doc"), icon=ft.icons.VPN_KEY, color="#FFFFFF", bgcolor="#334155", height=30, disabled=not ruta_key, on_click=lambda _, fn=f, r=ruta_key: mostrar_dialogo_key(fn, r))
                            ], spacing=6)
                        ], alignment=ft.MainAxisAlignment.BETWEEN),
                        bgcolor="#05966933" if es_reciente else "#1E293B66",
                        border=ft.border.all(1, EMERALD_GREEN) if es_reciente else None,
                        padding=6, border_radius=6
                    )
                )

        refrescar_dropdown_archivos_traduccion()
        page.update()

    # --- FUNCIONES DEL MÓDULO DE ANONIMIZACIÓN (IRREVERSIBLE - RGPD) ---
    def click_procesar_individual_anon(fname):
        _, ext = os.path.splitext(fname.lower())
        if ext not in EXT_PERMITIDAS:
            texto_estado_anon.value = f"⚠️ {fname} no es un formato compatible."
            texto_estado_anon.color = CRIMSON_ERROR
            page.update()
            return

        barra_progreso_anon.visible = True
        texto_estado_anon.value = f"Anonimizando {fname} de forma irreversible (RGPD)..."
        texto_estado_anon.color = EMERALD_GREEN
        page.update()

        try:
            k_val = int(dd_k_anonimato.value or 3)
            cuasi_val = chk_generalizar_cuasi.value
            ejecutar_anonimizacion_real_lotes(
                carpeta_salida=carpeta_salida_anonimizada_configurada,
                k_umbral=k_val,
                generalizar_cuasi=cuasi_val
            )
            texto_estado_anon.value = f"¡Éxito! Archivo {fname} anonimizado con Certificado RGPD."
            texto_estado_anon.color = EMERALD_GREEN
        except Exception as ex:
            texto_estado_anon.value = f"Error: {str(ex)}"
            texto_estado_anon.color = CRIMSON_ERROR

        barra_progreso_anon.visible = False
        refrescar_vistas_archivos_anon()
        try:
            card_visibilidad_anonimizados.scroll_into_view()
        except Exception:
            pass

    def seleccionar_para_preview_anon(nombre_archivo):
        nonlocal archivo_seleccionado_preview_anon
        archivo_seleccionado_preview_anon = nombre_archivo
        ruta_f = os.path.join(CARPETA_ENTRADA, nombre_archivo)
        _, ext_f = os.path.splitext(nombre_archivo.lower())
        es_comp = ext_f in EXT_PERMITIDAS
        
        contenido_preliminar = ""
        if os.path.exists(ruta_f):
            try:
                if nombre_archivo.endswith((".txt", ".csv", ".json", ".md")):
                    with open(ruta_f, "r", encoding="utf-8", errors="ignore") as f_in:
                        contenido_preliminar = f_in.read(300)
                else:
                    contenido_preliminar = f"Documento preparado para anonimización: {nombre_archivo}"
            except Exception as ex:
                contenido_preliminar = f"Error de lectura: {ex}"

        panel_inspector_preview_anon.content = ft.Column([
            ft.Row([
                ft.Icon(ft.icons.DESCRIPTION_OUTLINED if es_comp else ft.icons.WARNING_AMBER_ROUNDED, color=EMERALD_GREEN if es_comp else CRIMSON_ERROR, size=16),
                ft.Text(nombre_archivo, size=11, weight=ft.FontWeight.BOLD, color="#FFFFFF", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=220)
            ]),
            ft.Container(
                content=ft.Text(contenido_preliminar if es_comp else "⚠️ Formato no compatible. Formatos permitidos: .txt, .csv, .docx, .xlsx, .pdf, .json, .md, .png, .jpg", size=10, color="#E2E8F0" if es_comp else CRIMSON_ERROR),
                bgcolor="#0F172A", padding=6, border_radius=4, height=45
            ),
            ft.Row([
                ft.ElevatedButton(t("btn_open"), icon=ft.icons.OPEN_IN_NEW, color="#FFFFFF", bgcolor="#334155", height=28, on_click=lambda _, fn=nombre_archivo, r=ruta_f: abrir_documento_o_dialogo(fn, r)),
                ft.ElevatedButton(t("btn_anon_now"), icon=ft.icons.VERIFIED_USER, color="#FFFFFF", bgcolor=EMERALD_GREEN if es_comp else "#475569", height=28, disabled=not es_comp, on_click=lambda _: click_procesar_individual_anon(nombre_archivo))
            ], spacing=6)
        ], spacing=4)
        page.update()

    def refrescar_vistas_archivos_anon():
        # 1. Cola de entrada para anonimizar
        try:
            todos = os.listdir(CARPETA_ENTRADA)
            archivos_entrada = [f for f in todos if not f.startswith(".") and not f.startswith("~$") and os.path.isfile(os.path.join(CARPETA_ENTRADA, f))]
            texto_estado_anon.value = t("anon_queue_status", count=len(archivos_entrada))
            texto_estado_anon.color = EMERALD_GREEN
            btn_procesar_lote_anon.disabled = len(archivos_entrada) == 0
        except Exception as ex:
            texto_estado_anon.value = t("anon_status_error", error=str(ex))
            texto_estado_anon.color = CRIMSON_ERROR
            archivos_entrada = []

        vista_cola_archivos_anon.controls.clear()
        if not archivos_entrada:
            vista_cola_archivos_anon.controls.append(
                ft.Container(
                    content=ft.Text(t("queue_empty_folder"), size=11, color=TEXT_MUTED, italic=True, text_align=ft.TextAlign.CENTER),
                    padding=10, alignment=ft.alignment.center
                )
            )
        else:
            for f in archivos_entrada:
                ruta_f = os.path.join(CARPETA_ENTRADA, f)
                _, ext_f = os.path.splitext(f.lower())
                es_compatible = ext_f in EXT_PERMITIDAS

                def del_file_anon(e, fname=f):
                    try:
                        os.remove(os.path.join(CARPETA_ENTRADA, fname))
                        refrescar_vistas_archivos_anon()
                    except Exception as ex:
                        print(f"Error borrando: {ex}")

                vista_cola_archivos_anon.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.icons.INSERT_DRIVE_FILE_OUTLINED if es_compatible else ft.icons.WARNING_AMBER_ROUNDED, color=EMERALD_GREEN if es_compatible else CRIMSON_ERROR, size=15),
                                    ft.Text(f, size=11, weight=ft.FontWeight.W_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=170),
                                    ft.Container(
                                        content=ft.Text(t("badge_incompatible"), size=9, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                                        bgcolor=CRIMSON_ERROR, padding=3, border_radius=3
                                    ) if not es_compatible else ft.Container()
                                ]),
                                expand=True,
                                on_click=lambda _, fn=f: seleccionar_para_preview_anon(fn)
                            ),
                            ft.ElevatedButton(t("btn_anonymize_row"), icon=ft.icons.VERIFIED_USER, color="#FFFFFF", bgcolor=EMERALD_GREEN if es_compatible else "#475569", height=26, disabled=not es_compatible, on_click=lambda _, fn=f: click_procesar_individual_anon(fn)),
                            ft.IconButton(ft.icons.DELETE_OUTLINED, icon_size=14, icon_color=CRIMSON_ERROR, on_click=del_file_anon)
                        ], alignment=ft.MainAxisAlignment.BETWEEN),
                        bgcolor="#1E293B66", padding=4, border_radius=4
                    )
                )

        # 2. Caja de Archivos Anonimizados RGPD
        vista_anonimizados_unificada.controls.clear()
        try:
            archivos_anon = [f for f in os.listdir(carpeta_salida_anonimizada_configurada) if not f.startswith(".") and not f.startswith("~$")] if os.path.exists(carpeta_salida_anonimizada_configurada) else []
            archivos_anon.sort(key=lambda x: os.path.getmtime(os.path.join(carpeta_salida_anonimizada_configurada, x)), reverse=True)
        except Exception:
            archivos_anon = []

        if not archivos_anon:
            vista_anonimizados_unificada.controls.append(
                ft.Container(content=ft.Text(t("anon_no_processed"), size=11, color=TEXT_MUTED, italic=True), padding=10)
            )
        else:
            for f in archivos_anon:
                ruta_doc = os.path.join(carpeta_salida_anonimizada_configurada, f)
                base_sin_ext = os.path.splitext(f)[0]
                ruta_cert = os.path.join(carpeta_salida_anonimizada_configurada, f"Certificado_Anonimizacion_{base_sin_ext}.txt")
                tiene_cert = os.path.exists(ruta_cert)
                es_cert = f.startswith("Certificado_Anonimizacion_")

                if es_cert:
                    vista_anonimizados_unificada.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Row([
                                    ft.Icon(ft.icons.VERIFIED_USER, color=EMERALD_GREEN, size=16),
                                    ft.Text(f, size=11, weight=ft.FontWeight.BOLD, color=EMERALD_GREEN, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=220),
                                    ft.Container(
                                        content=ft.Text(t("btn_rgpd_cert").upper(), size=8, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                                        bgcolor="#059669", padding=3, border_radius=3
                                    )
                                ], expand=True),
                                ft.ElevatedButton(t("btn_rgpd_cert"), icon=ft.icons.ARTICLE, color="#FFFFFF", bgcolor="#059669", height=28, on_click=lambda _, fn=f, r=ruta_doc: mostrar_dialogo_ver_documento(fn, r))
                            ], alignment=ft.MainAxisAlignment.BETWEEN),
                            bgcolor="#05966922",
                            border=ft.border.all(1, "#05966944"),
                            padding=6, border_radius=6
                        )
                    )
                else:
                    vista_anonimizados_unificada.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Row([
                                    ft.Icon(ft.icons.SHIELD, color=EMERALD_GREEN, size=16),
                                    ft.Text(f, size=12, weight=ft.FontWeight.W_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=200),
                                    ft.Container(
                                        content=ft.Text(t("badge_new"), size=8, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                                        bgcolor="#059669", padding=3, border_radius=3
                                    )
                                ], expand=True),
                                ft.Row([
                                    ft.ElevatedButton(t("btn_open_doc"), icon=ft.icons.OPEN_IN_NEW, color="#FFFFFF", bgcolor=EMERALD_GREEN, height=30, on_click=lambda _, fn=f, r=ruta_doc: abrir_documento_o_dialogo(fn, r)),
                                    ft.ElevatedButton(
                                        t("btn_rgpd_cert"),
                                        icon=ft.icons.ARTICLE,
                                        color="#FFFFFF",
                                        bgcolor="#334155",
                                        height=30,
                                        disabled=not tiene_cert,
                                        on_click=lambda _, fn=base_sin_ext, r=ruta_cert: mostrar_dialogo_ver_documento(f"Certificado {fn}", r)
                                    )
                                ], spacing=6)
                            ], alignment=ft.MainAxisAlignment.BETWEEN),
                            bgcolor="#05966922",
                            border=ft.border.all(1, "#05966944"),
                            padding=6, border_radius=6
                        )
                    )

        page.update()

    def refrescar_diccionario_view():
        wrap_chips_dic.controls.clear()
        terminos = cargar_diccionario_corporativo()
        if not terminos:
            wrap_chips_dic.controls.append(ft.Text("No hay términos prohibidos definidos.", size=12, color=TEXT_MUTED, italic=True))
        else:
            for t in terminos:
                wrap_chips_dic.controls.append(
                    ft.Chip(
                        label=ft.Text(t, size=11, color="#FFFFFF"),
                        bgcolor="#334155",
                        on_delete=lambda _, term=t: eliminar_termino_dic(term)
                    )
                )
        page.update()

    def refrescar_dropdown_archivos_traduccion():
        dd_archivo_origen_key.options.clear()
        opciones = []
        if os.path.exists(carpeta_salida_configurada):
            for f in os.listdir(carpeta_salida_configurada):
                if f.endswith(".key"):
                    nombre_orig = f.replace(".reverse.key", "").replace(".key", "")
                    if nombre_orig not in opciones:
                        opciones.append(nombre_orig)
        if os.path.exists(CARPETA_PROCESADOS):
            for f in os.listdir(CARPETA_PROCESADOS):
                if not f.startswith(".") and f not in opciones:
                    opciones.append(f)

        for opt in opciones:
            dd_archivo_origen_key.options.append(ft.dropdown.Option(opt))
        if opciones and not dd_archivo_origen_key.value:
            dd_archivo_origen_key.value = opciones[0]

    # --- FILE PICKER (registrado via ServiceRegistry interno de Flet 0.86) ---
    global_file_picker = ft.FilePicker()
    page._services.register_service(global_file_picker)

    async def click_abrir_picker_documentos(e):
        try:
            files = await global_file_picker.pick_files(allow_multiple=True, with_data=True, cancel_upload_on_window_blur=False)
            if files:
                for f in files:
                    dest = os.path.join(CARPETA_ENTRADA, f.name)
                    if hasattr(f, "bytes") and f.bytes:
                        with open(dest, "wb") as out_f:
                            out_f.write(f.bytes)
                    elif hasattr(f, "path") and f.path and os.path.exists(f.path):
                        shutil.copy(f.path, dest)
                refrescar_vistas_archivos()
                page.update()
        except Exception as ex:
            print(f"Error pick_files documentos: {ex}")

    async def click_abrir_picker_diccionario(e):
        try:
            files = await global_file_picker.pick_files(with_data=True, cancel_upload_on_window_blur=False)
            if files:
                for f in files:
                    contenido = None
                    if hasattr(f, "bytes") and f.bytes:
                        contenido = f.bytes.decode("utf-8", errors="ignore").splitlines()
                    elif hasattr(f, "path") and f.path and os.path.exists(f.path):
                        with open(f.path, "r", encoding="utf-8", errors="ignore") as f_in:
                            contenido = f_in.readlines()
                    if contenido:
                        with open(RUTA_DICCIONARIO, "a", encoding="utf-8") as f_out:
                            f_out.write("\n")
                            for l in contenido:
                                if l.strip():
                                    f_out.write(l.strip() + "\n")
                refrescar_diccionario_view()
                page.update()
        except Exception as ex:
            print(f"Error pick_files diccionario: {ex}")

    async def click_abrir_picker_key_traduccion(e):
        try:
            files = await global_file_picker.pick_files(with_data=True, cancel_upload_on_window_blur=False)
            if files and files[0]:
                f = files[0]
                content_str = None
                if hasattr(f, "bytes") and f.bytes:
                    content_str = f.bytes.decode("utf-8", errors="ignore")
                elif hasattr(f, "path") and f.path and os.path.exists(f.path):
                    with open(f.path, "r", encoding="utf-8", errors="ignore") as k_in:
                        content_str = k_in.read()
                if content_str:
                    nonlocal mapa_key_cargado_traduccion
                    try:
                        mapa_key_cargado_traduccion = json.loads(content_str)
                        txt_info_key.value = f"✅ Llave cargada manualmente: {f.name}"
                        txt_info_key.color = EMERALD_GREEN
                    except Exception:
                        txt_info_key.value = "❌ Archivo de llave no válido"
                        txt_info_key.color = CRIMSON_ERROR
                    page.update()
        except Exception as ex:
            print(f"Error pick_files key: {ex}")

    async def click_abrir_picker_doc_traduccion(e):
        try:
            files = await global_file_picker.pick_files(with_data=True, cancel_upload_on_window_blur=False)

            if files and files[0]:
                f = files[0]
                nonlocal archivo_anonimizado_traduccion_path, nombre_archivo_traduccion_original
                nombre_archivo_traduccion_original = f.name
                dest_path = os.path.join(CARPETA_ENTRADA, f.name)
                
                if hasattr(f, "bytes") and f.bytes:
                    with open(dest_path, "wb") as out_f:
                        out_f.write(f.bytes)
                    archivo_anonimizado_traduccion_path = dest_path
                elif hasattr(f, "path") and f.path and os.path.exists(f.path):
                    shutil.copy(f.path, dest_path)
                    archivo_anonimizado_traduccion_path = dest_path

                _, ext = os.path.splitext(f.name.lower())
                txt_cargado = ""
                if ext in [".txt", ".csv", ".json", ".md"]:
                    try:
                        with open(dest_path, "r", encoding="utf-8", errors="ignore") as f_in:
                            txt_cargado = f_in.read(3000)
                    except Exception:
                        txt_cargado = f"Documento cargado: {f.name}"
                else:
                    txt_cargado = f"📄 Archivo estructurado {ext.upper()} listo para desanonimizar: {f.name}"

                tf_texto_anonimizado.value = txt_cargado
                txt_info_doc_traduccion.value = f"📄 Archivo cargado: {f.name}"
                txt_info_doc_traduccion.color = NEON_BLUE
                page.update()
        except Exception as ex:
            print(f"Error pick_files doc traduccion: {ex}")

    # --- PANTALLA DE ACCESO BLOQUEADO ---
    if not licencia_valida:
        def intentar_revalidar(e):
            nonlocal licencia_valida, mensaje_licencia, cliente_id, dias_restantes
            lic_valida, msg_lic, cli_id, dias = validador.verificar_licencia_offline()
            if lic_valida:
                page.controls.clear()
                cargar_interfaz_principal()
            else:
                texto_error_licencia.value = f"⚠️ Estado de licencia: {msg_lic}"
                page.update()

        texto_error_licencia = ft.Text(mensaje_licencia, size=13, color="#FCA5A5", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.W_500)

        page.add(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.TIMER_OFF_ROUNDED, color=ACCENT_ORANGE, size=72),
                    ft.Text("Período de Prueba Expirado", size=24, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    ft.Text("Tu licencia de uso On-Premise ha llegado a su término.", size=13, color=TEXT_MUTED),
                    ft.Container(
                        content=ft.Column([
                            texto_error_licencia,
                            ft.Text("Para continuar anonimizando documentos con Lia Vault sin límites, solicita la renovación de tu licencia corporativa.", size=11, color="#94A3B8", text_align=ft.TextAlign.CENTER)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                        bgcolor="#1E293B88", padding=16, border_radius=8, border=ft.border.all(1, "#334155"), width=440
                    ),
                    ft.Row([
                        ft.ElevatedButton(
                            "Solicitar Renovación por Email", 
                            icon=ft.icons.EMAIL_OUTLINED, 
                            color="#FFFFFF", 
                            bgcolor=ACCENT_ORANGE, 
                            height=42,
                            on_click=lambda _: abrir_url("mailto:hello@korautomate.com?subject=Quiero%20renovar%20mi%20licencia%20de%20Lia%20Vault")
                        ),
                        ft.OutlinedButton(
                            "Ir a la Web de Renovación",
                            icon=ft.icons.OPEN_IN_NEW,
                            height=42,
                            on_click=lambda _: abrir_url("https://lia.korautomate.com/#renovacion")
                        )
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
                    ft.Text("O escribe a: hello@korautomate.com (Asunto: Quiero renovar mi licencia de Lia Vault)", size=11, color=NEON_BLUE, weight=ft.FontWeight.W_500),
                    ft.Divider(height=20, color="#334155"),
                    ft.Row([
                        ft.Text("Lia Vault es un desarrollo de", size=11, color=TEXT_MUTED),
                        ft.TextButton(
                            "KorAutomate", 
                            on_click=lambda _: abrir_url("https://korautomate.com"),
                            style=ft.ButtonStyle(color=NEON_BLUE, padding=0)
                        ),
                        ft.Text("para la iniciativa", size=11, color=TEXT_MUTED),
                        ft.TextButton(
                            "Checkpoint-IA", 
                            on_click=lambda _: abrir_url("https://checkpoint-ia.com"),
                            style=ft.ButtonStyle(color=NEON_BLUE, padding=0)
                        )
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=4)
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16),
                alignment=ft.alignment.center,
                padding=40
            )
        )
        page.update()
        return

    # --- INTERFAZ PRINCIPAL SUITE LIA VAULT ---
    def cargar_interfaz_principal():
        lang_curr = get_current_language()
        logo_img = ft.Image(src=f"data:image/svg+xml;base64,{LOGO_BASE64}", width=44, height=44, fit="contain")
        
        # Sincronizar textos de controles dinámicos con el idioma activo
        btn_procesar_lote.text = t("sanitizer_btn_process")
        btn_procesar_lote_anon.text = t("anon_btn_process")
        texto_estado_sanitizador.value = t("sanitizer_status_ready")
        texto_estado_anon.value = t("anon_status_ready")
        dd_k_anonimato.label = t("anon_k_label")
        dd_k_anonimato.options = [
            ft.dropdown.Option("3", t("anon_k_3")),
            ft.dropdown.Option("5", t("anon_k_5")),
            ft.dropdown.Option("10", t("anon_k_10"))
        ]
        chk_generalizar_cuasi.label = t("anon_quasi_label")
        dd_archivo_origen_key.label = t("reversion_dd_label")
        dd_archivo_origen_key.hint_text = t("reversion_select_hint")
        tf_texto_anonimizado.hint_text = t("reversion_hint_input")
        txt_info_doc_traduccion.value = t("reversion_txt_no_doc")
        txt_info_key.value = t("reversion_txt_key_auto")
        tf_texto_restaurado.hint_text = t("reversion_output_hint")
        tf_nueva_palabra_dic.hint_text = t("dict_tf_hint")
        
        panel_inspector_preview.content = ft.Column([
            ft.Icon(ft.icons.REMOVE_RED_EYE_OUTLINED, size=28, color=TEXT_MUTED),
            ft.Text(t("sanitizer_preview_empty_title"), size=11, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Text(t("sanitizer_preview_empty_desc"), size=10, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=4)

        panel_inspector_preview_anon.content = ft.Column([
            ft.Icon(ft.icons.REMOVE_RED_EYE_OUTLINED, size=28, color=TEXT_MUTED),
            ft.Text(t("sanitizer_preview_empty_title"), size=11, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Text(t("sanitizer_preview_empty_desc"), size=10, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=4)
        
        def toggle_language(e):
            nuevo_lang = "en" if get_current_language() == "es" else "es"
            set_current_language(nuevo_lang)
            page.clean()
            cargar_interfaz_principal()
            page.update()

        header_brand = ft.Column([
            ft.Row([
                logo_img,
                ft.Text("LIA VAULT", size=26, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ft.Container(content=ft.Text("ON-PREMISE", size=11, weight=ft.FontWeight.BOLD, color=ACCENT_ORANGE), bgcolor="#3B2506", padding=ft.Padding(left=8, right=8, top=3, bottom=3), border_radius=4)
            ], spacing=10),
            ft.Text(t("header_subtitle"), size=13, weight=ft.FontWeight.W_500, color=TEXT_MUTED)
        ], spacing=4)

        status_pills = ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.LANGUAGE, color=ACCENT_ORANGE, size=16),
                    ft.Text("ES" if lang_curr == "es" else "EN", size=12, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                ], spacing=6),
                bgcolor=SURFACE_CARD, padding=ft.Padding(left=12, right=12, top=8, bottom=8), border_radius=16, border=ft.border.all(1, ACCENT_ORANGE),
                tooltip=t("lang_switch_tooltip"),
                on_click=toggle_language,
                ink=True
            ),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.CIRCLE, color=EMERALD_GREEN, size=11),
                    ft.Text(t("server_lan"), size=12, color=NEON_BLUE, weight=ft.FontWeight.W_600)
                ], spacing=8),
                bgcolor=SURFACE_CARD, padding=ft.Padding(left=12, right=12, top=8, bottom=8), border_radius=16, border=ft.border.all(1, "#334155")
            ),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.VERIFIED_USER, color=EMERALD_GREEN, size=16),
                    ft.Text(t("license_active_badge", days=dias_restantes) if licencia_valida else t("license_invalid_badge"), size=12, color=EMERALD_GREEN, weight=ft.FontWeight.W_600)
                ], spacing=8),
                bgcolor=SURFACE_CARD, padding=ft.Padding(left=12, right=12, top=8, bottom=8), border_radius=16, border=ft.border.all(1, "#334155")
            )
        ], spacing=14, alignment=ft.MainAxisAlignment.END, wrap=False)

        header_responsive = ft.ResponsiveRow([
            ft.Container(content=header_brand, col={"sm": 12, "md": 6}),
            ft.Container(content=status_pills, alignment=ft.alignment.center_right if platform.system() != "Mobile" else ft.alignment.center_left, col={"sm": 12, "md": 6})
        ], alignment=ft.MainAxisAlignment.BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # Menú Lateral Sidebar
        btn_nav_sanitizador = ft.ElevatedButton(t("tab_sanitizer"), icon=ft.icons.SHIELD_OUTLINED, color="#FFFFFF", bgcolor=ACCENT_ORANGE if menu_activo == "sanitizador" else SURFACE_CARD, height=42)
        btn_nav_anonimizador = ft.ElevatedButton(t("tab_anonymizer"), icon=ft.icons.VERIFIED_USER, color="#FFFFFF", bgcolor=ACCENT_ORANGE if menu_activo == "anonimizador" else SURFACE_CARD, height=42)
        btn_nav_traduccion = ft.ElevatedButton(t("tab_reversion"), icon=ft.icons.SWAP_HORIZ, color="#FFFFFF", bgcolor=ACCENT_ORANGE if menu_activo == "traduccion" else SURFACE_CARD, height=42)
        btn_nav_diccionario = ft.ElevatedButton(t("tab_dictionary"), icon=ft.icons.MENU_BOOK_OUTLINED, color="#FFFFFF", bgcolor=ACCENT_ORANGE if menu_activo == "diccionario" else SURFACE_CARD, height=42)
        btn_nav_licencias = ft.ElevatedButton(t("tab_license"), icon=ft.icons.VPN_KEY_OUTLINED, color="#FFFFFF", bgcolor=ACCENT_ORANGE if menu_activo == "licencias" else SURFACE_CARD, height=42)
        btn_nav_codigo = ft.ElevatedButton(t("tab_code"), icon=ft.icons.CODE, color="#FFFFFF", bgcolor=ACCENT_ORANGE if menu_activo == "codigo" else SURFACE_CARD, height=42)

        def cambiar_seccion(nombre):
            nonlocal menu_activo
            menu_activo = nombre
            btn_nav_sanitizador.bgcolor = ACCENT_ORANGE if nombre == "sanitizador" else SURFACE_CARD
            btn_nav_anonimizador.bgcolor = ACCENT_ORANGE if nombre == "anonimizador" else SURFACE_CARD
            btn_nav_traduccion.bgcolor = ACCENT_ORANGE if nombre == "traduccion" else SURFACE_CARD
            btn_nav_diccionario.bgcolor = ACCENT_ORANGE if nombre == "diccionario" else SURFACE_CARD
            btn_nav_licencias.bgcolor = ACCENT_ORANGE if nombre == "licencias" else SURFACE_CARD
            btn_nav_codigo.bgcolor = ACCENT_ORANGE if nombre == "codigo" else SURFACE_CARD

            panel_sanitizador.visible = (nombre == "sanitizador")
            panel_anonimizador.visible = (nombre == "anonimizador")
            panel_traduccion.visible = (nombre == "traduccion")
            panel_diccionario.visible = (nombre == "diccionario")
            panel_licencias.visible = (nombre == "licencias")
            panel_codigo.visible = (nombre == "codigo")

            if nombre == "anonimizador":
                refrescar_vistas_archivos_anon()
            elif nombre == "traduccion":
                refrescar_dropdown_archivos_traduccion()

            page.update()

        btn_nav_sanitizador.on_click = lambda _: cambiar_seccion("sanitizador")
        btn_nav_anonimizador.on_click = lambda _: cambiar_seccion("anonimizador")
        btn_nav_traduccion.on_click = lambda _: cambiar_seccion("traduccion")
        btn_nav_diccionario.on_click = lambda _: cambiar_seccion("diccionario")
        btn_nav_licencias.on_click = lambda _: cambiar_seccion("licencias")
        btn_nav_codigo.on_click = lambda _: cambiar_seccion("codigo")

        # --- SISTEMA DE TOUR GUIADO INTERACTIVO CON ENFOQUE ---
        pasos_tour = [
            {
                "seccion": "sanitizador",
                "titulo": t("tour_1_title"),
                "icono": ft.icons.SHIELD_OUTLINED,
                "color": ACCENT_ORANGE,
                "descripcion": t("tour_1_desc")
            },
            {
                "seccion": "anonimizador",
                "titulo": t("tour_2_title"),
                "icono": ft.icons.VERIFIED_USER,
                "color": EMERALD_GREEN,
                "descripcion": t("tour_2_desc")
            },
            {
                "seccion": "traduccion",
                "titulo": t("tour_3_title"),
                "icono": ft.icons.SWAP_HORIZ,
                "color": ACCENT_ORANGE,
                "descripcion": t("tour_3_desc")
            },
            {
                "seccion": "diccionario",
                "titulo": t("tour_4_title"),
                "icono": ft.icons.MENU_BOOK_OUTLINED,
                "color": NEON_BLUE,
                "descripcion": t("tour_4_desc")
            },
            {
                "seccion": "codigo",
                "titulo": t("tour_5_title"),
                "icono": ft.icons.CODE,
                "color": EMERALD_GREEN,
                "descripcion": t("tour_5_desc")
            }
        ]

        paso_tour_actual = 0
        txt_tour_progreso = ft.Text(t("tour_step_prefix", step=1, total=len(pasos_tour)), size=11, weight=ft.FontWeight.BOLD, color=ACCENT_ORANGE)
        txt_tour_titulo = ft.Text("", size=15, weight=ft.FontWeight.BOLD, color="#FFFFFF")
        txt_tour_desc = ft.Text("", size=12, color="#E2E8F0")
        icon_tour_paso = ft.Icon(ft.icons.HELP_OUTLINE, size=24, color=ACCENT_ORANGE)

        btn_tour_anterior = ft.OutlinedButton(t("tour_btn_prev"), height=32, disabled=True)
        btn_tour_siguiente = ft.ElevatedButton(t("tour_btn_next"), height=32, bgcolor=ACCENT_ORANGE, color="#FFFFFF")
        btn_tour_cerrar = ft.TextButton(t("tour_btn_skip"), style=ft.ButtonStyle(color=TEXT_MUTED))

        def cerrar_tour(_=None):
            overlay_tour_modal.visible = False
            page.update()

        def mostrar_paso_tour(indice):
            nonlocal paso_tour_actual
            paso_tour_actual = max(0, min(indice, len(pasos_tour) - 1))
            paso = pasos_tour[paso_tour_actual]

            cambiar_seccion(paso["seccion"])

            txt_tour_progreso.value = t("tour_step_prefix", step=paso_tour_actual + 1, total=len(pasos_tour))
            txt_tour_titulo.value = paso["titulo"]
            txt_tour_desc.value = paso["descripcion"]
            icon_tour_paso.name = paso["icono"]
            icon_tour_paso.color = paso["color"]

            btn_tour_anterior.disabled = (paso_tour_actual == 0)
            if paso_tour_actual == len(pasos_tour) - 1:
                btn_tour_siguiente.text = t("tour_btn_finish")
                btn_tour_siguiente.bgcolor = EMERALD_GREEN
            else:
                btn_tour_siguiente.text = t("tour_btn_next")
                btn_tour_siguiente.bgcolor = ACCENT_ORANGE

            overlay_tour_modal.visible = True
            page.update()

        def click_tour_sig(_=None):
            if paso_tour_actual < len(pasos_tour) - 1:
                mostrar_paso_tour(paso_tour_actual + 1)
            else:
                cerrar_tour()

        def click_tour_ant(_=None):
            if paso_tour_actual > 0:
                mostrar_paso_tour(paso_tour_actual - 1)

        btn_tour_anterior.on_click = click_tour_ant
        btn_tour_siguiente.on_click = click_tour_sig
        btn_tour_cerrar.on_click = cerrar_tour

        card_tour_flotante = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        icon_tour_paso,
                        ft.Column([
                            txt_tour_progreso,
                            txt_tour_titulo
                        ], spacing=2)
                    ], spacing=10),
                    ft.IconButton(ft.icons.CLOSE, icon_size=18, icon_color=TEXT_MUTED, on_click=cerrar_tour)
                ], alignment=ft.MainAxisAlignment.BETWEEN),
                ft.Divider(height=12, color="#334155"),
                txt_tour_desc,
                ft.Divider(height=12, color="#334155"),
                ft.Row([
                    btn_tour_cerrar,
                    ft.Row([
                        btn_tour_anterior,
                        btn_tour_siguiente
                    ], spacing=8)
                ], alignment=ft.MainAxisAlignment.BETWEEN)
            ], spacing=10),
            bgcolor="#0F172A",
            padding=20,
            border_radius=12,
            border=ft.border.all(2, ACCENT_ORANGE),
            shadow=ft.BoxShadow(blur_radius=25, color="#000000CC"),
            width=540
        )

        overlay_tour_modal = ft.Container(
            content=card_tour_flotante,
            alignment=ft.alignment.center,
            bgcolor="#000000B3",
            visible=False,
            expand=True
        )

        def iniciar_tour_guiado(paso=0):
            mostrar_paso_tour(paso)

        card_compromiso_offline = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.SHIELD_OUTLINED, color=EMERALD_GREEN, size=18),
                    ft.Text(t("sidebar_privacy_badge"), size=12, weight=ft.FontWeight.BOLD, color=EMERALD_GREEN)
                ], spacing=6),
                ft.Text(
                    t("sidebar_privacy_desc"),
                    size=11, color=TEXT_MUTED
                ),
            ], spacing=8),
            bgcolor=SURFACE_CARD, padding=16, border_radius=10, border=ft.border.all(1, "#334155")
        )

        btn_tour_sidebar = ft.ElevatedButton(
            t("sidebar_tour_btn"),
            icon=ft.icons.EXPLORE,
            color="#FFFFFF",
            bgcolor="#334155",
            height=40,
            on_click=lambda _: iniciar_tour_guiado(paso=0),
            tooltip=t("sidebar_tour_btn")
        )

        columna_sidebar = ft.Container(
            content=ft.Column([
                ft.Text(t("sidebar_local_features"), size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                btn_nav_sanitizador,
                btn_nav_anonimizador,
                btn_nav_traduccion,
                btn_nav_diccionario,
                ft.Divider(height=16, color="#334155"),
                ft.Text(t("sidebar_deploy_admin"), size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                btn_nav_licencias,
                btn_nav_codigo,
                ft.Divider(height=16, color="#334155"),
                card_compromiso_offline,
                btn_tour_sidebar
            ], spacing=10),
            col={"sm": 12, "md": 4, "lg": 3}
        )

        # ==========================================
        # SECCIÓN 1: SANITIZADOR DE ARCHIVOS
        # ==========================================
        card_dropzone = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.UNARCHIVE_OUTLINED, size=32, color=TEXT_MUTED),
                ft.Text(t("btn_add_files"), size=13, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ft.Text(t("dropzone_formats"), size=10, color=TEXT_MUTED)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
            bgcolor="#1E293B88",
            padding=16,
            border_radius=8,
            border=ft.border.all(1, "#334155"),
            alignment=ft.alignment.center,
            on_click=click_abrir_picker_documentos
        )

        # Caja de Sanitizador (Izquierda - Altura fija igual a la derecha)
        card_header_sanitizador = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.LAYERS_OUTLINED, color=ACCENT_ORANGE, size=20),
                    ft.Text(t("sanitizer_card_title"), size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF")
                ], spacing=8),
                ft.Text(
                    t("sanitizer_card_desc"),
                    size=11, color=TEXT_MUTED
                ),
                ft.Divider(height=8, color="#334155"),
                card_dropzone,
                ft.Row([btn_procesar_lote], alignment=ft.MainAxisAlignment.CENTER)
            ], spacing=10),
            bgcolor=SURFACE_CARD, padding=18, border_radius=10, border=ft.border.all(1, "#334155"), height=330
        )

        # Cola de Entrada + Inspector (Derecha - Altura fija idéntica de 330px)
        card_cola_archivos = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(t("sanitizer_queue_title"), size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    ft.TextButton(t("btn_clear_all"), icon=ft.icons.DELETE_SWEEP, style=ft.ButtonStyle(color=CRIMSON_ERROR), on_click=lambda _: limpiar_todo_cola())
                ], alignment=ft.MainAxisAlignment.BETWEEN),
                ft.Column([
                    vista_cola_archivos,
                    panel_inspector_preview
                ], spacing=8)
            ], spacing=8),
            bgcolor=SURFACE_CARD, padding=18, border_radius=10, border=ft.border.all(1, "#334155"), height=330
        )

        # Disposición en 2 COLUMNAS PERFECTAMENTE ALINEADAS DE 330PX
        grid_sanitizador_superior = ft.ResponsiveRow([
            ft.Container(content=card_header_sanitizador, col={"sm": 12, "md": 6}),
            ft.Container(content=card_cola_archivos, col={"sm": 12, "md": 6})
        ], spacing=16)

        # CAJA ÚNICA UNIFICADA INFERIOR: Archivos seguros ya procesados
        nonlocal_card_visibilidad = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.icons.FOLDER_SPECIAL, color=EMERALD_GREEN, size=20),
                        ft.Column([
                            ft.Text(t("sanitizer_output_title"), size=15, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                            ft.Text(t("sanitizer_output_path_hint"), size=11, color=NEON_BLUE, weight=ft.FontWeight.W_500)
                        ], spacing=2)
                    ], spacing=8),
                    ft.IconButton(
                        ft.icons.FOLDER_OPEN, 
                        icon_size=18, 
                        disabled=ES_DOCKER,
                        icon_color=TEXT_MUTED if ES_DOCKER else "#FFFFFF",
                        tooltip=t("sanitizer_tooltip_folder_docker") if ES_DOCKER else t("sanitizer_tooltip_folder"), 
                        on_click=lambda _: abrir_local(carpeta_salida_configurada)
                    )
                ], alignment=ft.MainAxisAlignment.BETWEEN),
                ft.Divider(height=10, color="#334155"),
                vista_procesados_unificada
            ], spacing=10),
            bgcolor=SURFACE_CARD, padding=20, border_radius=10, border=ft.border.all(1, "#334155")
        )
        card_visibilidad_procesados_y_salida.content = nonlocal_card_visibilidad.content
        card_visibilidad_procesados_y_salida.bgcolor = SURFACE_CARD
        card_visibilidad_procesados_y_salida.padding = 20
        card_visibilidad_procesados_y_salida.border_radius = 10
        card_visibilidad_procesados_y_salida.border = ft.border.all(1, "#334155")

        def click_procesar_lote():
            btn_procesar_lote.disabled = True
            barra_progreso_sanitizador.visible = True
            texto_estado_sanitizador.value = t("sanitizer_status_processing")
            texto_estado_sanitizador.color = ACCENT_ORANGE
            page.update()

            try:
                cant = ejecutar_procesamiento_lotes(carpeta_salida=carpeta_salida_configurada)
                texto_estado_sanitizador.value = t("sanitizer_status_completed", count=cant)
                texto_estado_sanitizador.color = EMERALD_GREEN
            except Exception as ex:
                texto_estado_sanitizador.value = t("sanitizer_status_error", error=str(ex))
                texto_estado_sanitizador.color = CRIMSON_ERROR

            barra_progreso_sanitizador.visible = False
            refrescar_vistas_archivos()

            try:
                card_visibilidad_procesados_y_salida.scroll_into_view()
            except Exception:
                pass

        btn_procesar_lote.on_click = lambda _: click_procesar_lote()

        def limpiar_todo_cola():
            for f in os.listdir(CARPETA_ENTRADA):
                r = os.path.join(CARPETA_ENTRADA, f)
                if os.path.isfile(r):
                    os.remove(r)
            refrescar_vistas_archivos()

        panel_sanitizador = ft.Column([
            grid_sanitizador_superior,
            barra_progreso_sanitizador,
            texto_estado_sanitizador,
            card_visibilidad_procesados_y_salida
        ], spacing=16)

        # ==========================================
        # SECCIÓN 1.5: ANONIMIZACIÓN IRREVERSIBLE (RGPD)
        # ==========================================
        card_dropzone_anon = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.UNARCHIVE_OUTLINED, size=34, color=TEXT_MUTED),
                ft.Text(t("btn_add_files"), size=13, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ft.Text(t("dropzone_formats"), size=11, color=TEXT_MUTED)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=6),
            bgcolor="#1E293B88",
            padding=16,
            border_radius=8,
            border=ft.border.all(1, "#334155"),
            alignment=ft.alignment.center,
            on_click=click_abrir_picker_documentos
        )

        card_header_anonimizador = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.VERIFIED_USER, color=EMERALD_GREEN, size=22),
                    ft.Text(t("anon_card_title"), size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF")
                ], spacing=8),
                ft.Text(
                    t("anon_card_desc"),
                    size=12, color=TEXT_MUTED
                ),
                ft.Divider(height=12, color="#334155"),
                dd_k_anonimato,
                chk_generalizar_cuasi,
                card_dropzone_anon,
                ft.Row([btn_procesar_lote_anon])
            ], spacing=10),
            bgcolor=SURFACE_CARD, padding=20, border_radius=10, border=ft.border.all(1, "#334155"), height=420
        )

        card_cola_anonimizador = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(t("anon_queue_title"), size=12, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    ft.TextButton(t("btn_clear_all"), icon=ft.icons.DELETE_SWEEP, style=ft.ButtonStyle(color=CRIMSON_ERROR), on_click=lambda _: limpiar_todo_cola())
                ], alignment=ft.MainAxisAlignment.BETWEEN),
                ft.Divider(height=8, color="#334155"),
                ft.Column([
                    vista_cola_archivos_anon,
                    panel_inspector_preview_anon
                ], spacing=10)
            ], spacing=10),
            bgcolor=SURFACE_CARD, padding=20, border_radius=10, border=ft.border.all(1, "#334155"), height=420
        )

        grid_anonimizador_superior = ft.ResponsiveRow([
            ft.Container(content=card_header_anonimizador, col={"sm": 12, "md": 6}),
            ft.Container(content=card_cola_anonimizador, col={"sm": 12, "md": 6})
        ], spacing=16)

        nonlocal_card_visibilidad_anon = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.icons.FOLDER_SPECIAL, color=EMERALD_GREEN, size=20),
                        ft.Column([
                            ft.Text(t("anon_output_title"), size=13, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                            ft.Text(t("anon_output_path", path=CARPETA_SALIDA_ANONIMIZADA), size=10, color=TEXT_MUTED)
                        ], spacing=2)
                    ], spacing=8),
                    ft.IconButton(
                        ft.icons.FOLDER_OPEN, 
                        icon_size=18, 
                        disabled=ES_DOCKER,
                        icon_color=TEXT_MUTED if ES_DOCKER else "#FFFFFF",
                        tooltip=t("anon_tooltip_folder"), 
                        on_click=lambda _: abrir_local(CARPETA_SALIDA_ANONIMIZADA)
                    )
                ], alignment=ft.MainAxisAlignment.BETWEEN),
                ft.Divider(height=10, color="#334155"),
                vista_anonimizados_unificada
            ], spacing=10),
            bgcolor=SURFACE_CARD, padding=20, border_radius=10, border=ft.border.all(1, "#334155")
        )
        card_visibilidad_anonimizados.content = nonlocal_card_visibilidad_anon.content
        card_visibilidad_anonimizados.bgcolor = SURFACE_CARD
        card_visibilidad_anonimizados.padding = 20
        card_visibilidad_anonimizados.border_radius = 10
        card_visibilidad_anonimizados.border = ft.border.all(1, "#334155")

        def click_procesar_lote_anon():
            btn_procesar_lote_anon.disabled = True
            barra_progreso_anon.visible = True
            texto_estado_anon.value = t("anon_status_processing")
            texto_estado_anon.color = ACCENT_ORANGE
            page.update()

            k_val = int(dd_k_anonimato.value or "3")
            cuasi_val = chk_generalizar_cuasi.value

            try:
                cant = ejecutar_anonimizacion_real_lotes(
                    carpeta_salida=CARPETA_SALIDA_ANONIMIZADA,
                    k_umbral=k_val,
                    generalizar_cuasi=cuasi_val
                )
                texto_estado_anon.value = t("anon_status_completed", count=cant)
                texto_estado_anon.color = EMERALD_GREEN
            except Exception as ex:
                texto_estado_anon.value = t("anon_status_error", error=str(ex))
                texto_estado_anon.color = CRIMSON_ERROR

            barra_progreso_anon.visible = False
            refrescar_vistas_archivos_anon()

            try:
                card_visibilidad_anonimizados.scroll_into_view()
            except Exception:
                pass

        btn_procesar_lote_anon.on_click = lambda _: click_procesar_lote_anon()

        panel_anonimizador = ft.Column([
            grid_anonimizador_superior,
            barra_progreso_anon,
            texto_estado_anon,
            card_visibilidad_anonimizados
        ], spacing=16)

        # ==========================================
        # SECCIÓN 2: TRADUCCIÓN INVERSA INTELIGENTE
        # ==========================================
        def ejecutar_reversion_inteligente(e):
            txt_anon = tf_texto_anonimizado.value or ""
            doc_sel = dd_archivo_origen_key.value

            if not txt_anon:
                tf_texto_restaurado.value = "⚠️ Por favor pegue la respuesta o texto generado por la IA."
                page.update()
                return

            if not doc_sel:
                tf_texto_restaurado.value = "⚠️ Por favor seleccione el documento de origen en el desplegable superior."
                page.update()
                return

            k1 = os.path.join(carpeta_salida_configurada, f"{doc_sel}.key")
            k2 = os.path.join(carpeta_salida_configurada, f"{doc_sel}.reverse.key")
            ruta_k = k1 if os.path.exists(k1) else (k2 if os.path.exists(k2) else None)

            if not ruta_k:
                for f in os.listdir(carpeta_salida_configurada):
                    if f.startswith(doc_sel) and f.endswith(".key"):
                        ruta_k = os.path.join(carpeta_salida_configurada, f)
                        break

        def ejecutar_reversion_inteligente(e):
            nonlocal mapa_key_cargado_traduccion, archivo_anonimizado_traduccion_path
            doc_sel = dd_archivo_origen_key.value

            mapa_k = mapa_key_cargado_traduccion
            if not mapa_k and doc_sel:
                k1 = os.path.join(carpeta_salida_configurada, f"{doc_sel}.key")
                k2 = os.path.join(carpeta_salida_configurada, f"{doc_sel}.reverse.key")
                ruta_k = k1 if os.path.exists(k1) else (k2 if os.path.exists(k2) else None)

                if not ruta_k:
                    for f in os.listdir(carpeta_salida_configurada):
                        if f.startswith(doc_sel) and f.endswith(".key"):
                            ruta_k = os.path.join(carpeta_salida_configurada, f)
                            break

                if ruta_k:
                    try:
                        with open(ruta_k, "r", encoding="utf-8") as fk:
                            mapa_k = json.load(fk)
                    except Exception:
                        pass

            if not mapa_k:
                tf_texto_restaurado.value = f"⚠️ No se encontró la llave .key para la desanonimización."
                txt_info_key.value = "Seleccione el documento de origen o cargue manualmente la llave .key arriba."
                txt_info_key.color = CRIMSON_ERROR
                page.update()
                return

            try:
                if archivo_anonimizado_traduccion_path and os.path.exists(archivo_anonimizado_traduccion_path):
                    ruta_restaurada = ejecutar_reversion_archivo(archivo_anonimizado_traduccion_path, mapa_k)
                    nombre_res = os.path.basename(ruta_restaurada)
                    _, ext_res = os.path.splitext(nombre_res.lower())
                    
                    if ext_res in [".txt", ".csv", ".json", ".md"]:
                        try:
                            with open(ruta_restaurada, "r", encoding="utf-8", errors="ignore") as f_in:
                                tf_texto_restaurado.value = f_in.read(3000)
                        except Exception:
                            tf_texto_restaurado.value = f"✅ Archivo desanonimizado guardado en: {ruta_restaurada}"
                    else:
                        tf_texto_restaurado.value = f"✅ Documento {ext_res.upper()} desanonimizado exitosamente conservando formato nativo:\n{ruta_restaurada}"

                    txt_info_key.value = f"✅ Llave aplicada exitosamente ({len(mapa_k)} términos desanonimizados). Guardado como {nombre_res}."
                    txt_info_key.color = EMERALD_GREEN
                    
                    abrir_documento_o_dialogo(nombre_res, ruta_restaurada)
                else:
                    txt_anon = tf_texto_anonimizado.value or ""
                    res = revertir_anonimizacion(txt_anon, mapa_k)
                    tf_texto_restaurado.value = res
                    txt_info_key.value = f"✅ Llave aplicada exitosamente ({len(mapa_k)} términos desanonimizados)."
                    txt_info_key.color = EMERALD_GREEN
                page.update()
            except Exception as ex:
                tf_texto_restaurado.value = f"Error al procesar la desanonimización: {ex}"
                page.update()

        def guardar_resultado_restaurado(e):
            nonlocal archivo_anonimizado_traduccion_path, nombre_archivo_traduccion_original
            
            ext_final = None
            if archivo_anonimizado_traduccion_path:
                ext_final = os.path.splitext(archivo_anonimizado_traduccion_path)[1]
            elif nombre_archivo_traduccion_original:
                ext_final = os.path.splitext(nombre_archivo_traduccion_original)[1]
            elif dd_archivo_origen_key.value:
                ext_final = os.path.splitext(dd_archivo_origen_key.value)[1]
            
            if not ext_final:
                ext_final = ".txt"

            if archivo_anonimizado_traduccion_path and os.path.exists(archivo_anonimizado_traduccion_path):
                nombre_b, ext = os.path.splitext(os.path.basename(archivo_anonimizado_traduccion_path))
                target = os.path.join(os.path.dirname(archivo_anonimizado_traduccion_path), f"{nombre_b}_restaurado{ext}")
                if os.path.exists(target):
                    abrir_documento_o_dialogo(os.path.basename(target), target)
                    return
                else:
                    abrir_documento_o_dialogo(os.path.basename(archivo_anonimizado_traduccion_path), archivo_anonimizado_traduccion_path)
                    return

            if tf_texto_restaurado.value and not tf_texto_restaurado.value.startswith("⚠️"):
                nombre_base_out = "respuesta_restaurada"
                if nombre_archivo_traduccion_original:
                    nombre_base_out = f"{os.path.splitext(nombre_archivo_traduccion_original)[0]}_restaurado"
                elif dd_archivo_origen_key.value:
                    nombre_base_out = f"{os.path.splitext(dd_archivo_origen_key.value)[0]}_restaurado"

                dest = os.path.join(CARPETA_ENTRADA, f"{nombre_base_out}{ext_final}")
                with open(dest, "w", encoding="utf-8") as f_out:
                    f_out.write(tf_texto_restaurado.value)
                abrir_documento_o_dialogo(os.path.basename(dest), dest)

        def click_limpiar_traduccion(e=None):
            nonlocal mapa_key_cargado_traduccion, archivo_anonimizado_traduccion_path, nombre_archivo_traduccion_original
            mapa_key_cargado_traduccion = {}
            archivo_anonimizado_traduccion_path = None
            nombre_archivo_traduccion_original = None
            tf_texto_anonimizado.value = ""
            tf_texto_restaurado.value = ""
            txt_info_doc_traduccion.value = t("reversion_txt_no_doc")
            txt_info_doc_traduccion.color = TEXT_MUTED
            txt_info_key.value = t("reversion_txt_key_auto")
            txt_info_key.color = TEXT_MUTED
            page.update()

        barra_progreso_traduccion = ft.ProgressBar(color=ACCENT_ORANGE, bgcolor="#1E293B", visible=False)
        texto_estado_traduccion = ft.Text("", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_500)

        card_header_traduccion_carpeta = ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Icon(ft.icons.SWAP_HORIZ, color=ACCENT_ORANGE, size=22),
                    ft.Column([
                        ft.Text(t("reversion_card_title"), size=17, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                        ft.Text(f"Carpeta / Keys: {carpeta_salida_configurada}", size=11, color=TEXT_MUTED)
                    ], spacing=2)
                ], spacing=8),
                ft.IconButton(
                    ft.icons.FOLDER_OPEN,
                    icon_size=20,
                    disabled=ES_DOCKER,
                    icon_color=TEXT_MUTED if ES_DOCKER else "#FFFFFF",
                    tooltip=t("sanitizer_tooltip_folder"),
                    on_click=lambda _: abrir_local(carpeta_salida_configurada)
                )
            ], alignment=ft.MainAxisAlignment.BETWEEN),
            padding=ft.Padding(bottom=4)
        )

        def ejecutar_reversion_inteligente_con_preloader(e):
            barra_progreso_traduccion.visible = True
            texto_estado_traduccion.value = t("reversion_status_processing")
            texto_estado_traduccion.color = ACCENT_ORANGE
            page.update()
            try:
                ejecutar_reversion_inteligente(e)
                texto_estado_traduccion.value = t("reversion_status_completed")
                texto_estado_traduccion.color = EMERALD_GREEN
            except Exception as ex:
                texto_estado_traduccion.value = f"Error: {ex}"
                texto_estado_traduccion.color = CRIMSON_ERROR
            finally:
                barra_progreso_traduccion.visible = False
                page.update()

        panel_traduccion = ft.Container(
            content=ft.Column([
                card_header_traduccion_carpeta,
                ft.Text(
                    t("reversion_card_desc"),
                    size=12, color=TEXT_MUTED
                ),
                ft.Divider(height=16, color="#334155"),
                ft.Row([
                    dd_archivo_origen_key,
                    ft.ElevatedButton(t("reversion_btn_load_key"), icon=ft.icons.VPN_KEY, color="#FFFFFF", bgcolor="#334155", on_click=click_abrir_picker_key_traduccion)
                ], spacing=10, wrap=True),
                txt_info_key,
                ft.Divider(height=10, color="#334155"),
                ft.Row([
                    ft.ElevatedButton(t("reversion_btn_load_ai_doc"), icon=ft.icons.FILE_UPLOAD, color="#FFFFFF", bgcolor="#334155", on_click=click_abrir_picker_doc_traduccion),
                    txt_info_doc_traduccion
                ], spacing=10),
                tf_texto_anonimizado,
                ft.Row([
                    ft.ElevatedButton(t("reversion_btn_restore"), icon=ft.icons.LOCK_OPEN, color="#FFFFFF", bgcolor=ACCENT_ORANGE, on_click=ejecutar_reversion_inteligente_con_preloader),
                    ft.ElevatedButton(t("reversion_btn_clear"), icon=ft.icons.CLEAR_ALL, color="#FFFFFF", bgcolor="#334155", on_click=click_limpiar_traduccion)
                ], spacing=10),
                barra_progreso_traduccion,
                texto_estado_traduccion,
                ft.Divider(height=16, color="#334155"),
                ft.Text(t("reversion_output_label"), size=12, weight=ft.FontWeight.BOLD, color=EMERALD_GREEN),
                tf_texto_restaurado,
                ft.ElevatedButton(t("reversion_btn_save_file"), icon=ft.icons.SAVE_ALT, color="#FFFFFF", bgcolor=EMERALD_GREEN, on_click=guardar_resultado_restaurado)
            ], spacing=12),
            bgcolor=SURFACE_CARD, padding=20, border_radius=10, border=ft.border.all(1, "#334155")
        )

        # SECCIÓN 3: DICCIONARIO EMPRESA
        def eliminar_termino_dic(termino_eliminar):
            terminos = cargar_diccionario_corporativo()
            nuevos = [t for t in terminos if t.lower() != termino_eliminar.lower()]
            with open(RUTA_DICCIONARIO, "w", encoding="utf-8") as f:
                f.write("# Lista de palabras prohibidas corporativas\n")
                for t in nuevos:
                    f.write(t + "\n")
            refrescar_diccionario_view()

        def agregar_termino_dic(e):
            val = tf_nueva_palabra_dic.value.strip() if tf_nueva_palabra_dic.value else ""
            if val:
                with open(RUTA_DICCIONARIO, "a", encoding="utf-8") as f:
                    f.write("\n" + val + "\n")
                tf_nueva_palabra_dic.value = ""
                refrescar_diccionario_view()

        panel_diccionario = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.MENU_BOOK_OUTLINED, color=ACCENT_ORANGE, size=22),
                    ft.Text(t("dict_card_title"), size=17, weight=ft.FontWeight.BOLD, color="#FFFFFF")
                ], spacing=8),
                ft.Text(t("dict_card_desc"), size=12, color=TEXT_MUTED),
                ft.Divider(height=16, color="#334155"),
                ft.Row([
                    tf_nueva_palabra_dic,
                    ft.ElevatedButton(t("dict_btn_add"), icon=ft.icons.ADD, color="#FFFFFF", bgcolor=EMERALD_GREEN, on_click=agregar_termino_dic),
                    ft.ElevatedButton(t("dict_btn_import"), icon=ft.icons.FILE_UPLOAD, color="#FFFFFF", bgcolor="#334155", on_click=click_abrir_picker_diccionario)
                ], spacing=10, wrap=True),
                ft.Divider(height=16, color="#334155"),
                ft.Text(t("dict_current_terms"), size=12, weight=ft.FontWeight.BOLD, color=NEON_BLUE),
                wrap_chips_dic
            ], spacing=12),
            bgcolor=SURFACE_CARD, padding=20, border_radius=10, border=ft.border.all(1, "#334155")
        )

        # SECCIÓN 4: LICENCIAS
        panel_licencias = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.VPN_KEY_OUTLINED, color=ACCENT_ORANGE, size=22),
                    ft.Text(t("license_card_title"), size=17, weight=ft.FontWeight.BOLD, color="#FFFFFF")
                ], spacing=8),
                ft.Text(t("license_card_desc"), size=12, color=TEXT_MUTED),
                ft.Divider(height=16, color="#334155"),
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"{t('license_client_label')} {cliente_id}", size=13, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                        ft.Text(t("license_trial_days", days=dias_restantes), size=12, color=EMERALD_GREEN),
                        ft.Text(t("license_valid_msg", client=cliente_id, days=dias_restantes) if licencia_valida else t("license_invalid_msg"), size=12, color=NEON_BLUE)
                    ], spacing=8),
                    bgcolor="#0F172A", padding=16, border_radius=6
                )
            ], spacing=12),
            bgcolor=SURFACE_CARD, padding=20, border_radius=10, border=ft.border.all(1, "#334155")
        )

        # SECCIÓN 5: CÓDIGO ON-PREMISE
        snippet_python = """# Integración On-Premise en Python con app_offline.py
from app_offline import ejecutar_procesamiento_lotes, desanonimizar_texto, desanonimizar_archivo

# 1. Ejecutar sanitización de la carpeta /entrada
archivos_procesados = ejecutar_procesamiento_lotes(carpeta_salida="./salida_segura")

# 2. Desanonimizar resultado usando la llave .key
texto_restaurado = desanonimizar_texto("[PERSONA_1]", {"[PERSONA_1]": "Juan Pérez"})
"""

        panel_codigo = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.CODE, color=ACCENT_ORANGE, size=22),
                    ft.Text(t("code_card_title"), size=17, weight=ft.FontWeight.BOLD, color="#FFFFFF")
                ], spacing=8),
                ft.Text(t("code_card_desc"), size=12, color=TEXT_MUTED),
                ft.Divider(height=16, color="#334155"),
                ft.Container(
                    content=ft.Text(snippet_python, size=11, color="#38BDF8", font_family="monospace"),
                    bgcolor="#0F172A", padding=16, border_radius=6
                )
            ], spacing=12),
            bgcolor=SURFACE_CARD, padding=20, border_radius=10, border=ft.border.all(1, "#334155")
        )

        # FOOTER CON ENLACE CHECKPOINT-IA.COM
        footer_container = ft.Container(
            content=ft.Row([
                ft.Text(t("footer_suite_text"), size=12, color=TEXT_MUTED),
                ft.TextButton(
                    content=ft.Text("Checkpoint-ia.com", size=12, color=NEON_BLUE, weight=ft.FontWeight.W_600),
                    url="https://checkpoint-ia.com",
                    style=ft.ButtonStyle(padding=0)
                )
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
            padding=12
        )

        refrescar_vistas_archivos()
        refrescar_vistas_archivos_anon()
        refrescar_diccionario_view()
        refrescar_dropdown_archivos_traduccion()

        panel_anonimizador.visible = False
        panel_traduccion.visible = False
        panel_diccionario.visible = False
        panel_licencias.visible = False
        panel_codigo.visible = False

        columna_workspace = ft.Container(
            content=ft.Column([
                panel_sanitizador,
                panel_anonimizador,
                panel_traduccion,
                panel_diccionario,
                panel_licencias,
                panel_codigo
            ], spacing=16),
            col={"sm": 12, "md": 8, "lg": 9}
        )

        layout_principal = ft.ResponsiveRow([
            columna_sidebar,
            columna_workspace
        ], spacing=20)

        contenido_base = ft.Column([
            header_responsive,
            ft.Divider(height=1, color="#334155"),
            layout_principal,
            ft.Divider(height=1, color="#334155"),
            footer_container
        ], spacing=16)

        page.add(
            ft.Stack([
                contenido_base,
                overlay_tour_modal
            ], expand=True)
        )

    cargar_interfaz_principal()


def liberar_puerto(puerto=8502):
    import subprocess, platform
    sistema = platform.system()
    if sistema in ("Darwin", "Linux"):
        try:
            subprocess.run(f"lsof -ti:{puerto} | xargs kill -9", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except Exception:
            pass
    elif sistema == "Windows":
        try:
            cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {puerto} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"'
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except Exception:
            pass

def _lanzar_navegador_seguro(url="http://localhost:8502"):
    import time, webbrowser, platform
    time.sleep(2)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    if platform.system() == "Windows":
        try:
            import os
            os.system(f"start {url}")
        except Exception:
            pass

if __name__ == "__main__":
    liberar_puerto(8502)
    print("\n==================================================")
    print(" [OK] SERVIDOR LIA VAULT EN EJECUCION")
    print(" [+] URL Local: http://localhost:8502")
    print(" [+] URL Red:   http://127.0.0.1:8502")
    print("==================================================\n")
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8502, host="0.0.0.0")
