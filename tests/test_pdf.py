# -*- coding: utf-8 -*-
"""
Reversión de PDF: las etiquetas vuelven a su valor original dentro del hueco que ocupaban, y el resultado
sigue siendo un PDF válido (antes se trataba como texto y quedaba un archivo vacío/corrupto).
"""

import os
import shutil
import tempfile
import unittest

import fitz

import app_offline


def _seudonimizado(ruta, mapa):
    """PDF como lo deja procesar_pdf: cada valor tapado por un recuadro oscuro con su etiqueta."""
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_text((72, 100), "Factura de " + " y ".join(mapa.values()) + ".", fontsize=11)
    huecos = []
    for etiqueta, valor in sorted(mapa.items(), key=lambda kv: len(kv[1]), reverse=True):
        for rect in pagina.search_for(valor):
            if any(rect.intersects(h) for h, _ in huecos):
                continue  # "Ana" también aparece dentro de "ana@correo.com"
            pagina.add_redact_annot(rect, fill=app_offline.FONDO_ETIQUETA_PDF)
            huecos.append((rect, etiqueta))
    pagina.apply_redactions()
    for rect, etiqueta in huecos:
        app_offline._escribir_en_hueco(pagina, rect, etiqueta, (1, 1, 1), 8)
    doc.save(ruta)


class TestReversionPdf(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.mapa = {"[PERSONA_1]": "Ana", "[PERSONA_10]": "Carlos Gomez", "[CORREO_1]": "ana@correo.com"}
        self.origen = os.path.join(self.dir, "seud.pdf")
        _seudonimizado(self.origen, self.mapa)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_etiquetas_cortas_quedan_escritas(self):
        # "Ana" deja un hueco angosto: con letra fija de 8 puntos, [PERSONA_1] no entraba y no se escribía.
        texto = fitz.open(self.origen)[0].get_text()
        for etiqueta in self.mapa:
            self.assertIn(etiqueta, texto)

    def test_restaura_valores_en_pdf_valido(self):
        destino = os.path.join(self.dir, "rest.pdf")
        app_offline.ejecutar_reversion_archivo(self.origen, self.mapa, ruta_destino=destino)
        texto = fitz.open(destino)[0].get_text()
        for etiqueta, valor in self.mapa.items():
            self.assertIn(valor, texto)
            self.assertNotIn(etiqueta, texto)

    def test_llave_de_otro_documento_da_error_claro(self):
        with self.assertRaises(ValueError):
            app_offline.ejecutar_reversion_archivo(self.origen, {"[OTRA_1]": "x"}, os.path.join(self.dir, "r.pdf"))

    def test_imagenes_no_se_restauran(self):
        ruta = os.path.join(self.dir, "img.png")
        open(ruta, "wb").write(b"\x89PNG")
        with self.assertRaises(ValueError):
            app_offline.ejecutar_reversion_archivo(ruta, self.mapa, os.path.join(self.dir, "r.png"))


if __name__ == "__main__":
    unittest.main()
