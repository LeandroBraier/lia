---
name: flet_filepicker_mac_fix
description: Guía y mejores prácticas para la integración de FilePicker en Flet (Python/Web) en macOS y soluciones a errores comunes (Unknown control, SSL, coroutines no awaited, page.services vs page.overlay).
---

# Flet FilePicker & macOS Integration Guide

## Context & Overview
Esta skill documenta la resolución técnica de errores críticos de `FilePicker`, SSL y manejo de eventos al ejecutar aplicaciones Flet en Python 3.14+ sobre macOS en modo Web (`WEB_BROWSER`) y Nativo.

---

## 🚨 Errores Frecuentes y Causas Raíz

### 1. `Unknown control: FilePicker` en Flet Web
- **Síntoma:** Aparece un recuadro o banner rojo en la interfaz Web indicando `Unknown control: FilePicker`.
- **Causa Raíz:** Usar `page.overlay.append(picker)` en Flet Web. El motor gráfico de Flutter/Web intenta renderizar el `FilePicker` como un widget visual cuando en realidad es un servicio en segundo plano.
- **Solución Obligatoria:** Registrar los `FilePicker` en `page.services.extend([picker])`.

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
    # Instanciación y registro en page.services
    picker_documentos = ft.FilePicker()
    page.services.extend([picker_documentos])

    async def click_abrir_documentos(e):
        try:
            files = await picker_documentos.pick_files(allow_multiple=True, with_data=True)
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
