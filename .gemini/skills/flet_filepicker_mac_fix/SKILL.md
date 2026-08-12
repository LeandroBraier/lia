---
name: flet_filepicker_mac_fix
description: Guía y mejores prácticas para la integración de FilePicker en Flet (Python/Web) en macOS y soluciones a errores comunes (Unknown control, SSL, coroutines no awaited, page.services vs page.overlay).
---

# Flet FilePicker & macOS Integration Guide

## Context & Overview
Esta skill documenta la resolución técnica de errores críticos de `FilePicker`, SSL y manejo de eventos al ejecutar aplicaciones Flet en Python 3.14+ sobre macOS en modo Web (`WEB_BROWSER`) y Nativo.

---

## 🚨 Errores Frecuentes y Causas Raíz

### 1. `Unknown control: FilePicker` en Flet Web (0.86+)
- **Síntoma:** Aparece un recuadro o banner rojo en la interfaz Web indicando `Unknown control: FilePicker`.
- **Causa Raíz (Flet ≥ 0.86):** En Flet 0.86+, `page.services` es un proxy a `view.services`, que es una lista Python plana con `metadata={"skip": True}`. Esto significa que agregar controles ahí (`page.services.extend(...)` o `page.services.append(...)`) **NO registra el servicio** en el `ServiceRegistry` interno de la Page, y **NO lo sincroniza** con el cliente Flutter. El FilePicker queda en un limbo: ni se monta, ni se renderiza, ni se comunica con el frontend. Usar `page.overlay.append(picker)` tampoco funciona porque intenta renderizarlo como widget visual.
- **Solución Obligatoria (Flet ≥ 0.86):** Registrar el `FilePicker` directamente en el `ServiceRegistry` interno de la Page:
  ```python
  picker = ft.FilePicker()
  page._services.register_service(picker)
  ```
  Esto invoca `register_service()` en la clase `ServiceRegistry`, que agrega el servicio a `_services`, llama a `__internal_update()`, y sincroniza el control con el cliente Flutter correctamente.
- **NO usar:** `page.services.extend([picker])`, `page.services.append(picker)`, ni `page.overlay.append(picker)`.

### 2. Incompatibilidad de `on_result` con `await pick_files()`
- **Síntoma:** La ventana de selección abre pero al elegir archivos no se cargan ni se refresca la vista (`pick_files` bloqueado).
- **Causa Raíz:** Mezclar el patrón de callback `picker.on_result = callback` con llamadas asíncronas `files = await picker.pick_files(...)`.
- **Solución Obligatoria:** En funciones `async def`, **NUNCA** usar `on_result`. Utilizar el patrón de retorno directo con `await`:
  ```python
  files = await picker.pick_files(allow_multiple=True, with_data=True)
  ```

### 3. Transmisión de Archivos en Navegador Web (`with_data=True`)
- **Síntoma:** En la Web los archivos seleccionados no se guardan o se lanza error de ruta no encontrada.
- **Causa Raíz:** El sandbox de seguridad del navegador no proporciona `f.path` absoluto al servidor Python.
- **Solución Obligatoria:** Pasar siempre `with_data=True` a `pick_files()`. Verificar si existe `f.bytes` (entorno Web) o `f.path` (entorno Desktop/Local):
  ```python
  if hasattr(f, "bytes") and f.bytes:
      with open(dest, "wb") as out_f:
          out_f.write(f.bytes)
  elif hasattr(f, "path") and f.path and os.path.exists(f.path):
      shutil.copy(f.path, dest)
  ```

### 4. Warning `coroutine 'FilePicker.pick_files' was never awaited`
- **Síntoma:** El cuadro de diálogo no se abre y la consola imprime `RuntimeWarning: coroutine ... was never awaited`.
- **Causa Raíz:** Llamar a `picker.pick_files()` sin la palabra clave `await` dentro de un handler asíncrono.
- **Solución Obligatoria:** Definir los manejadores de eventos como `async def` y anteponer `await picker.pick_files(...)`.

### 5. Fallo SSL en EasyOCR / PyTorch en macOS (`SSL: CERTIFICATE_VERIFY_FAILED`)
- **Síntoma:** La aplicación se congela al iniciar descargando modelos con `CERTIFICATE_VERIFY_FAILED`.
- **Causa Raíz:** El entorno por defecto de Python en macOS no instala ni valida los certificados CA del sistema.
- **Solución Obligatoria:** Incluir el parche de contexto SSL al inicio del script antes de importar módulos pesados:
  ```python
  import ssl
  try:
      ssl._create_default_https_context = ssl._create_unverified_context
  except AttributeError:
      pass
  ```

### 6. Cancelación prematura del diálogo en macOS Web (`cancel_upload_on_window_blur=False`)
- **Síntoma:** En navegadores macOS (Safari/Chrome), al presionar el botón de selección de archivos, el cuadro de diálogo se cancela inmediatamente o no retorna archivos seleccionados.
- **Causa Raíz:** En Flet Web, por defecto `cancel_upload_on_window_blur=True`. Al abrir el selector nativo del sistema operativo en Mac, la ventana del navegador pierde el foco (evento `blur`), lo que hace que Flet interprete el desenfoque como una cancelación explícita por parte del usuario.
- **Solución Obligatoria:** Pasar siempre `cancel_upload_on_window_blur=False` al invocar `pick_files()`:
  ```python
  files = await picker.pick_files(allow_multiple=True, with_data=True, cancel_upload_on_window_blur=False)
  ```

### 7. Persistencia del error por scripts de instalación / caché local (`SCRIPT_DIR/..`)
- **Síntoma:** El código en el repositorio ya incluye `page._services.register_service(...)`, pero en la máquina del usuario sigue apareciendo `Unknown control: FilePicker`.
- **Causa Raíz:** Al mover scripts lanzadores (`.command` o `.sh`) dentro de subcarpetas (ej. `🍏 MAC_INSTALLER/`), si el script usa `DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"` sin subir al directorio padre (`$SCRIPT_DIR/..`), el comando de instalación copia solo la subcarpeta en vez de la raíz del proyecto. El sistema del usuario termina ejecutando una instalación vieja en `~/Applications/...` que aún contiene el patrón obsoleto `page.overlay.append()`.
- **Solución Obligatoria:** 
  1. Resolver el directorio raíz del paquete subiendo desde la subcarpeta lanzadora:
     ```bash
     SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
     DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
     ```
  2. Limpiar instalaciones viejas antes de copiar para prevenir residuos de versiones anteriores:
     ```bash
     if [ -d "$TARGET_DIR" ]; then
         rm -rf "$TARGET_DIR"
     fi
     ```

---


## 🛠️ Patrón Canónico Recomendado para Flet Web & Desktop

```python
import flet as ft
import os, shutil, json, ssl

# Parche SSL para macOS
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

async def main(page: ft.Page):
    # Instanciación y registro via ServiceRegistry interno (Flet 0.86+)
    picker_documentos = ft.FilePicker()
    page._services.register_service(picker_documentos)

    async def click_abrir_documentos(e):
        try:
            files = await picker_documentos.pick_files(allow_multiple=True, with_data=True, cancel_upload_on_window_blur=False)
            if files:
                for f in files:
                    dest = os.path.join("./entrada", f.name)
                    if hasattr(f, "bytes") and f.bytes:
                        with open(dest, "wb") as out_f:
                            out_f.write(f.bytes)
                    elif hasattr(f, "path") and f.path and os.path.exists(f.path):
                        shutil.copy(f.path, dest)
                # Refrescar UI e informar a la página
                page.update()
        except Exception as ex:
            print(f"Error cargando archivos: {ex}")

    # UI Element
    page.add(
        ft.ElevatedButton("Seleccionar Archivos", on_click=click_abrir_documentos)
    )

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=8502)
```
