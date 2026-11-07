# -*- coding: utf-8 -*-
"""
Test unitario para verificar que el procesamiento individual procesa únicamente el archivo seleccionado.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch


class TestSingleFileProcessing(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.entrada = os.path.join(self.test_dir, "Entrada")
        self.salida = os.path.join(self.test_dir, "Seudonimizados")
        self.procesados = os.path.join(self.test_dir, "procesados")
        os.makedirs(self.entrada, exist_ok=True)
        os.makedirs(self.salida, exist_ok=True)
        os.makedirs(self.procesados, exist_ok=True)

        # Crear 2 archivos en la cola
        with open(os.path.join(self.entrada, "archivo1.txt"), "w") as f:
            f.write("Hola Jessica Perez")
        with open(os.path.join(self.entrada, "archivo2.txt"), "w") as f:
            f.write("Hola Carlos Lopez")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_process_only_selected_file(self):
        """Verifica que al pasar archivo_especifico solo se procesa ese archivo y el otro permanece en entrada."""
        import app_offline
        with patch.object(app_offline, "CARPETA_ENTRADA", self.entrada), \
             patch.object(app_offline, "CARPETA_PROCESADOS", self.procesados):

            # Procesar solo archivo1.txt
            app_offline.ejecutar_procesamiento_lotes(carpeta_salida=self.salida, archivo_especifico="archivo1.txt")

            # archivo1.txt debe haberse movido a procesados
            self.assertFalse(os.path.exists(os.path.join(self.entrada, "archivo1.txt")))
            self.assertTrue(os.path.exists(os.path.join(self.procesados, "archivo1.txt")))

            # archivo2.txt debe permanecer en Entrada
            self.assertTrue(os.path.exists(os.path.join(self.entrada, "archivo2.txt")))


if __name__ == "__main__":
    unittest.main()
