# -*- coding: utf-8 -*-
"""
Pruebas de fail-closed (auditoría H1): si falta el motor, un componente o la detección falla,
no se entrega ningún archivo, no queda salida parcial y el original sigue en Entrada.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import app_offline
from app_offline import MotorNoDisponibleError

TEXTO = "Hola, me llamo Jessica Pérez y mi correo es jessica.perez@empresa.com. Vivo en Madrid con mi familia."


class TestFailClosed(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.entrada = os.path.join(self.test_dir, "Entrada")
        self.salida = os.path.join(self.test_dir, "Salida")
        self.procesados = os.path.join(self.test_dir, "procesados")
        for d in (self.entrada, self.salida, self.procesados):
            os.makedirs(d, exist_ok=True)
        self.carpetas = [
            patch.object(app_offline, "CARPETA_ENTRADA", self.entrada),
            patch.object(app_offline, "CARPETA_PROCESADOS", self.procesados),
        ]
        for p in self.carpetas:
            p.start()

    def tearDown(self):
        for p in self.carpetas:
            p.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _crear(self, nombre, contenido=TEXTO):
        modo = "wb" if isinstance(contenido, bytes) else "w"
        with open(os.path.join(self.entrada, nombre), modo, **({} if modo == "wb" else {"encoding": "utf-8"})) as f:
            f.write(contenido)

    def _comprobar_sin_salida(self, nombre):
        self.assertEqual(os.listdir(self.salida), [], "no debe quedar ninguna salida")
        self.assertTrue(os.path.exists(os.path.join(self.entrada, nombre)), "el original debe seguir en Entrada")

    def test_sin_motor_no_procesa_ningun_modo(self):
        self._crear("informe.txt")
        with patch.object(app_offline, "analyzer", None):
            with self.assertRaises(MotorNoDisponibleError):
                app_offline.ejecutar_procesamiento_lotes(carpeta_salida=self.salida)
            with self.assertRaises(MotorNoDisponibleError):
                app_offline.ejecutar_anonimizacion_real_lotes(carpeta_salida=self.salida)
            with self.assertRaises(MotorNoDisponibleError):
                app_offline.anonimizar_texto_con_ia_y_key(TEXTO)
            with self.assertRaises(MotorNoDisponibleError):
                app_offline.anonimizar_texto_real_irreversible(TEXTO)
        self._comprobar_sin_salida("informe.txt")

    def test_error_de_deteccion_aborta_y_no_deja_salida(self):
        self._crear("informe.txt")
        roto = MagicMock(supported_languages=["es", "en"])
        roto.analyze.side_effect = RuntimeError("fallo interno")
        for funcion in (app_offline.ejecutar_procesamiento_lotes, app_offline.ejecutar_anonimizacion_real_lotes):
            with self.subTest(funcion=funcion.__name__), patch.object(app_offline, "analyzer", roto):
                with self.assertRaises(MotorNoDisponibleError):
                    funcion(carpeta_salida=self.salida, archivo_especifico="informe.txt")
                self._comprobar_sin_salida("informe.txt")

    def test_el_mensaje_de_error_no_incluye_el_texto(self):
        roto = MagicMock(supported_languages=["es", "en"])
        roto.analyze.side_effect = ValueError(TEXTO)
        with patch.object(app_offline, "analyzer", roto):
            with self.assertRaises(MotorNoDisponibleError) as ctx:
                app_offline.anonimizar_texto_con_ia_y_key(TEXTO)
        self.assertNotIn("Jessica", str(ctx.exception))

    def test_pdf_sin_pymupdf_no_copia_el_original(self):
        self._crear("contrato.pdf", b"%PDF-1.4 contenido de prueba")
        for funcion in (app_offline.ejecutar_procesamiento_lotes, app_offline.ejecutar_anonimizacion_real_lotes):
            with self.subTest(funcion=funcion.__name__), patch.object(app_offline, "fitz", None):
                with self.assertRaises(MotorNoDisponibleError):
                    funcion(carpeta_salida=self.salida, archivo_especifico="contrato.pdf")
                self._comprobar_sin_salida("contrato.pdf")

    def test_imagen_sin_ocr_no_copia_el_original(self):
        self._crear("dni.png", b"\x89PNG\r\n\x1a\n")
        for funcion in (app_offline.ejecutar_procesamiento_lotes, app_offline.ejecutar_anonimizacion_real_lotes):
            with self.subTest(funcion=funcion.__name__), patch.object(app_offline, "lector_ocr", None):
                with self.assertRaises(MotorNoDisponibleError):
                    funcion(carpeta_salida=self.salida, archivo_especifico="dni.png")
                self._comprobar_sin_salida("dni.png")

    @unittest.skipUnless(app_offline.fitz, "PyMuPDF no instalado")
    def test_pdf_escaneado_sin_ocr_no_se_entrega(self):
        fitz = app_offline.fitz
        doc = fitz.open()
        pagina = doc.new_page()
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), False)
        pix.clear_with(200)
        pagina.insert_image(fitz.Rect(50, 50, 250, 250), pixmap=pix)
        doc.save(os.path.join(self.entrada, "escaneado.pdf"))
        doc.close()
        for funcion in (app_offline.ejecutar_procesamiento_lotes, app_offline.ejecutar_anonimizacion_real_lotes):
            with self.subTest(funcion=funcion.__name__), patch.object(app_offline, "lector_ocr", None):
                with self.assertRaises(MotorNoDisponibleError):
                    funcion(carpeta_salida=self.salida, archivo_especifico="escaneado.pdf")
                self._comprobar_sin_salida("escaneado.pdf")

    def test_el_codigo_no_copia_originales_a_la_salida(self):
        ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app_offline.py")
        with open(ruta, encoding="utf-8") as f:
            codigo = f.read()
        self.assertNotIn("shutil.copy(ruta_origen", codigo)
        self.assertNotIn("_create_unverified_context", codigo)


if __name__ == "__main__":
    unittest.main()
