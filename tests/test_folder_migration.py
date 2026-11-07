# -*- coding: utf-8 -*-
"""
Test unitario para la migración y estructura dinámica de carpetas por idioma.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch


class TestFolderMigration(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_legacy_folder_migration(self):
        """Verifica que las carpetas legacy se migran a la nueva estructura."""
        import app_offline
        with patch.object(app_offline, "_base_dir", self.test_dir):
            legacy_seud = os.path.join(self.test_dir, "Archivos seguros de Checkpoint Ley IA")
            os.makedirs(legacy_seud, exist_ok=True)
            test_file = os.path.join(legacy_seud, "documento.key")
            with open(test_file, "w") as f:
                f.write('{"test": "key"}')

            rutas = app_offline.actualizar_rutas_idioma("es")
            
            target_seud = os.path.join(self.test_dir, "Seudonimizados")
            self.assertTrue(os.path.exists(os.path.join(target_seud, "documento.key")))
            self.assertEqual(rutas["seudonimizados"], target_seud)

    def test_language_switch_folder_migration(self):
        """Verifica que al cambiar de idioma (ES -> EN), el contenido se migra a las carpetas en inglés."""
        import app_offline
        with patch.object(app_offline, "_base_dir", self.test_dir):
            # Inicializar en español
            app_offline.actualizar_rutas_idioma("es")
            es_entrada = os.path.join(self.test_dir, "Entrada")
            with open(os.path.join(es_entrada, "archivo.txt"), "w") as f:
                f.write("contenido original")

            # Cambiar a inglés
            rutas_en = app_offline.actualizar_rutas_idioma("en")
            en_input = os.path.join(self.test_dir, "Input")
            self.assertTrue(os.path.exists(os.path.join(en_input, "archivo.txt")))
            self.assertEqual(rutas_en["entrada"], en_input)


if __name__ == "__main__":
    unittest.main()
