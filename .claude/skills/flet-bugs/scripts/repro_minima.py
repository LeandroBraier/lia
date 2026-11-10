"""
App Flet mínima para aislar un fallo. Editar solo el bloque marcado y comparar variantes con MODO.
Ejemplo: MODO=a PUERTO=8610 python3 repro_minima.py
El botón ocupa la franja izquierda: con navegador.py, "selector:30,300".
"""
import os

import flet as ft

MODO = os.environ.get("MODO", "a")


def main(page: ft.Page):
    # --- Control sospechoso: adaptar a cada caso ---
    picker = ft.FilePicker()
    if MODO == "b":
        page._services.register_service(picker)  # variante que reproducía el registro doble
    print("servicios registrados:", len(page._services._services), flush=True)

    async def click(e):
        print("CLICK", flush=True)
        try:
            files = await picker.pick_files(allow_multiple=True, with_data=True)
            print("RESULTADO", files, flush=True)
        except Exception as ex:
            print("ERROR", type(ex).__name__, ex, flush=True)
    # --- fin del bloque ---

    page.add(ft.Container(ft.Text("PROBAR"), on_click=click, expand=True, bgcolor="#336699"))


ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PUERTO", "8610")), host="0.0.0.0")
