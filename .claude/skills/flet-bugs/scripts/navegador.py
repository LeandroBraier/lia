"""
Maneja una app Flet web con el Chrome instalado, invisible y con perfil temporal (no toca el navegador del usuario).

Uso: navegador.py URL FOTO [PASO ...]
  PASO = x,y[:espera]     clic y espera en segundos (4 por defecto)
         selector:x,y     clic que debe abrir el selector de archivos (se cancela sin elegir nada)
Imprime los errores de la consola del navegador y guarda una foto al final (y FOTO_inicio.png al cargar).
Ejemplo: navegador.py http://127.0.0.1:8502 /tmp/f.png 145,222 selector:632,290
"""
import sys
import time

from playwright.sync_api import sync_playwright

url, foto, pasos = sys.argv[1], sys.argv[2], sys.argv[3:]
with sync_playwright() as p:
    navegador = p.chromium.launch(channel="chrome", headless=True)
    pagina = navegador.new_page(viewport={"width": 1440, "height": 900})
    pagina.on("console", lambda m: print("CONSOLA:", m.text[:160]) if "at http" not in m.text else None)
    pagina.goto(url)
    time.sleep(25)  # Flutter tarda en cargar; con menos, los clics caen en una pantalla vacía
    pagina.screenshot(path=foto.replace(".png", "_inicio.png"))
    for paso in pasos:
        if paso.startswith("selector:"):
            x, y = map(int, paso.split(":", 1)[1].split(","))
            try:
                with pagina.expect_file_chooser(timeout=15000) as fc:
                    pagina.mouse.click(x, y)
                fc.value.set_files([])
                print(f"selector {x},{y}: ABIERTO")
            except Exception as e:
                print(f"selector {x},{y}: NO SE ABRIÓ ({type(e).__name__})")
            time.sleep(3)
        else:
            xy, _, espera = paso.partition(":")
            pagina.mouse.click(*map(int, xy.split(",")))
            time.sleep(float(espera or 4))
            print("clic", xy)
    pagina.screenshot(path=foto)
    navegador.close()
