---
name: flet-bugs
description: Diagnóstico y arreglo de errores de la interfaz Flet de Lia Vault (app_grafica.py, Flet 0.86 en modo web). Úsalo cuando un botón, diálogo, selector de archivos u otro control "no hace nada", la app se cuelga o crashea en la interfaz, aparece "Timeout waiting for invoke method listener", errores minificados del navegador (RangeError, IndexError), o algo funciona en el Mac y no en Docker o al revés.
---

# Errores de Flet en Lia Vault

La interfaz corre con `ft.app(view=WEB_BROWSER, port=8502)`: el servidor es Python y la pantalla es un cliente
Flutter (wasm) en el navegador. Muchos fallos son **silenciosos**: Python no da error y el cliente falla en la
consola del navegador, o una API vieja se ignora sin avisar.

## Método (en este orden)

1. **Mirar los dos lados.**
   - Servidor: la terminal de la app, o `docker compose logs --since 15m lia-vault`.
   - Cliente: la consola del navegador. Los errores salen minificados (`RangeError (details omitted due to --minify)`), pero que aparezcan ya es la pista. `scripts/navegador.py` los captura sin abrir DevTools.
2. **Fijar versiones antes de suponer.** `flet==0.86.1`, `flet-web==0.86.1`, Python 3.14 en el Mac y 3.11 en Docker (`docker compose exec -T lia-vault python3 -c "import sys,flet;print(sys.version,flet.__version__)"`). Leer el código de Flet instalado (`python3 -c "import flet,os;print(os.path.dirname(flet.__file__))"`) en vez de confiar en documentación de otra versión.
3. **Reproducir con una app mínima** (`scripts/repro_minima.py`): solo el control sospechoso, con un `MODO` para comparar variantes. Correrla en el Mac y en la imagen de Docker:
   ```bash
   docker run -d --name repro -p 127.0.0.1:8610:8610 -e MODO=a -v "$PWD/.claude/skills/flet-bugs/scripts":/repro:ro --entrypoint python3 lia-vault:local /repro/repro_minima.py
   ```
4. **Probar en un navegador automático** con `scripts/navegador.py` (Chrome del sistema, invisible, perfil temporal: no toca el navegador del usuario). Sirve para la app mínima y para la app real en `http://127.0.0.1:8502`. Primero sacar una foto para ubicar coordenadas: Flutter dibuja en un canvas y no hay selectores CSS.
5. **Verificar cada hipótesis antes de dejarla en el código.** Si un parche no cambia el resultado, quitarlo junto con su comentario. Ejemplo real: se culpó a que Flet descartaba el FilePicker por conteo de referencias; la prueba con varios clics mostró que no, y el parche se revirtió (4c2cacc).
6. **Pedir prueba al usuario solo al final**, con recarga forzada (Cmd+Shift+R) y preguntando el navegador. Pedir permiso antes de cualquier prueba en su navegador.

## Trampas conocidas de Flet 0.86

| Síntoma | Causa | Arreglo |
|---|---|---|
| Un botón que abre un diálogo no hace nada y no hay error | `page.dialog = dlg; dlg.open = True` se ignora en 0.86 | `page.show_dialog(dlg)` y `page.pop_dialog()` para cerrar (a55e8fa) |
| "Seleccionar archivos" no responde; servidor: `Timeout waiting for invoke method listener for FilePicker(N).pick_files`; navegador: `RangeError`/`IndexError` | El `FilePicker` se registraba dos veces: `ft.FilePicker()` ya se registra solo (`Service.init`) y además se llamaba `page._services.register_service` | Crear el servicio una sola vez, sin registro manual ni re-registro al reconstruir la interfaz (bf96894). Vale para todos los servicios (`Clipboard`, `UrlLauncher`, `SharedPreferences`…) |
| `module 'flet' has no attribute 'app'` en Docker | Otra versión de Flet instalada | Fijar `flet==0.86.1` y `flet-web==0.86.1` |
| `TypeError` con `openapi_prefix` al arrancar el servidor web | `fastapi`/`starlette`/`uvicorn` incompatibles | Fijar `fastapi==0.139.2`, `starlette==1.3.1`, `uvicorn==0.51.0` |
| Un icono aparece distinto del pedido | `SafeIconsProxy` en `app_grafica.py` reemplaza en silencio los nombres que no existen | Buscar el nombre real en `ft.Icons`; no confiar en que el proxy avise |

## Trampas relacionadas (Python, pero aparecen en la interfaz)

- **Rutas viejas tras cambiar de idioma** (`No such file or directory: '/datos/Input'`): `from app_offline import CARPETA_ENTRADA` copia el valor al importar. Leer siempre `app_offline.CARPETA_...` (bffad43).
- **Idioma inglés en Docker**: `LANG=C.UTF-8` se interpreta como `en_US`; `i18n.detect_system_language` lo trata como "sin idioma" → español.
- **El Mac y Docker difieren**: distinto Python (3.14 vs 3.11), sistema de archivos sin mayúsculas en macOS (`entrada` = `Entrada`), usuario sin privilegios y disco de solo lectura en Docker. Ante un fallo en un solo entorno, empezar por estas diferencias.

## Sin resolver

- Una vez, el primer clic en "Llave .key" dio `Error -3 while decompressing data: incorrect header check` y no se reprodujo. Si vuelve, capturar el traceback desde el código (`python3 app_grafica.py`).

## Herramientas (una vez por sesión)

```bash
S=<carpeta temporal>
python3 -m venv $S/pw && $S/pw/bin/pip install -q playwright
$S/pw/bin/python .claude/skills/flet-bugs/scripts/navegador.py http://127.0.0.1:8502 $S/foto.png
```
`navegador.py` usa `channel="chrome"` (el Chrome instalado), así no hace falta descargar navegadores de Playwright.
