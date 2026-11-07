# -*- coding: utf-8 -*-
"""
Test Unitario para la Anonimización Irreversible RGPD en Lia Vault.
Ejecución: python3 test_anonimizacion_rgpd.py
"""

import os
import unittest
try:
    import pandas as pd
except ImportError:
    pd = None
import shutil
import tempfile
import app_offline

class TestAnonimizacionRGPD(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.carpeta_salida_test = os.path.join(self.temp_dir, "salida_anon_test")
        os.makedirs(self.carpeta_salida_test, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_anonimizacion_texto_irreversible(self):
        """Verifica la destrucción de PII y la generalización de cuasi-identificadores en texto libre."""
        texto_original = (
            "El paciente Juan Pérez, nacido el 15/05/1984, vive en Calle Mayor 12, CP 28013 Madrid. "
            "Su email es juan.perez@empresa.com, DNI 12345678Z, teléfono 600123456."
        )
        texto_anon, resumen = app_offline.anonimizar_texto_real_irreversible(texto_original, generalizar_cuasi=True)

        # 1. No debe quedar información identificativa directa
        self.assertNotIn("Juan Pérez", texto_anon)
        self.assertNotIn("juan.perez@empresa.com", texto_anon)
        self.assertNotIn("600123456", texto_anon)
        self.assertNotIn("12345678Z", texto_anon)

        # 2. Las etiquetas deben ser genéricas (sin índices numéricos de reversión)
        self.assertIn("[CORREO_ELIMINADO]", texto_anon)
        self.assertIn("[DOCUMENTO_ELIMINADO]", texto_anon)
        self.assertIn("[TELEFONO_ELIMINADO]", texto_anon)

        # 3. Cuasi-identificadores deben estar generalizados
        self.assertIn("[AÑO 1984]", texto_anon)
        self.assertIn("28***", texto_anon)
        self.assertIn("[DIRECCION_GENERALIZADA]", texto_anon)

    def test_k_anonimato_dataframe(self):
        """Verifica que el algoritmo de k-anonimato agrupe o suprima registros inferiores a k."""
        if pd is None:
            self.skipTest("pandas no disponible en este entorno")
        data = {
            "nombre": ["Carlos Ruiz", "Carlos Ruiz", "Carlos Ruiz", "Ana Gómez", "Luis Torres"],
            "edad": [25, 25, 25, 42, 60],
            "codigo_postal": ["28001", "28001", "28001", "08001", "41001"],
            "diagnostico": ["Gripe", "Gripe", "Asma", "Diabetes", "Hipertensión"]
        }
        df = pd.DataFrame(data)
        df_anon, resumen = app_offline.aplicar_k_anonimato_dataframe(df, k=3, generalizar_cuasi=True)

        # Los nombres deben haber sido anonimizados
        for val in df_anon["nombre"]:
            self.assertNotEqual(val, "Carlos Ruiz")
            self.assertNotEqual(val, "Ana Gómez")

        # Filas con frecuencia < k=3 deben haber sido suprimidas
        self.assertEqual(len(df_anon), 3)
        self.assertEqual(resumen["filas_suprimidas"], 2)

    def test_regression_bugs_reportados(self):
        """Verifica que verbos al inicio de frase, roles en inglés y títulos conceptuales no se anonimicen erróneamente."""
        texto_muestra = "Encontramos que el Researcher presentó el informe sobre Frameworks de Agentes y Flujos a Juan Pérez en Madrid."
        texto_anon, _ = app_offline.anonimizar_texto_real_irreversible(texto_muestra)

        # "Encontramos", "Researcher" y "Frameworks de Agentes y Flujos" NO deben anonimizarse
        self.assertIn("Encontramos", texto_anon)
        self.assertIn("Researcher", texto_anon)
        self.assertIn("Frameworks de Agentes y Flujos", texto_anon)

        # "Juan Pérez" y "Madrid" SÍ deben anonimizarse
        self.assertNotIn("Juan Pérez", texto_anon)
        self.assertNotIn("Madrid", texto_anon)
        self.assertIn("[PERSONA]", texto_anon)
        self.assertIn("[UBICACION]", texto_anon)

    def test_no_regresion_entidades_mixtas(self):
        """Verifica que nombres propios y topónimos reales no se pierdan al convivir con términos técnicos o roles."""
        texto_mixto = "El Lead Researcher Carlos Gómez organizó la conferencia de IA en el auditorio de Madrid Tech Hub."
        texto_anon, _ = app_offline.anonimizar_texto_real_irreversible(texto_mixto)

        # El nombre real y la ubicación real deben ser anonimizados
        self.assertNotIn("Carlos Gómez", texto_anon)
        self.assertNotIn("Madrid", texto_anon)
        self.assertIn("[PERSONA]", texto_anon)
        self.assertIn("[UBICACION]", texto_anon)

    def test_documentos_mixtos_es_en(self):
        """Verifica que documentos bilingües con fragmentos en ES y EN se procesen correctamente sin rechazo."""
        texto_bilingue = (
            "El paciente Juan Pérez asistió a consulta médica en Madrid. "
            "According to Dr. John Smith, the patient is recovering well in London."
        )
        texto_anon, resumen = app_offline.anonimizar_texto_real_irreversible(texto_bilingue)
        self.assertNotIn("Juan Pérez", texto_anon)
        self.assertNotIn("John Smith", texto_anon)
        self.assertNotIn("Madrid", texto_anon)
        self.assertNotIn("London", texto_anon)
        self.assertIn("[PERSONA]", texto_anon)

    def test_textos_cortos_y_tablas(self):
        """Verifica que textos breves o tablas numéricas no disparen rechazo por falta de stopwords."""
        texto_corto = "ID: 1045, Total: 150.00 EUR, Ref: INV-2026"
        texto_anon, _ = app_offline.anonimizar_texto_real_irreversible(texto_corto)
        self.assertTrue(len(texto_anon) > 0)

    def test_rechazo_terceros_idiomas(self):
        """Verifica que documentos en idiomas no soportados (ej. Francés o Alemán) lancen IdiomaNoSoportadoError."""
        texto_fr = "Le rapport confidentiel concernant Pierre Dupont a été envoyé à Paris pour une évaluation détaillée de la situation."
        with self.assertRaises(app_offline.IdiomaNoSoportadoError):
            app_offline.anonimizar_texto_real_irreversible(texto_fr)

        texto_de = "Der Bericht über Hans Müller wurde nach Berlin gesendet für die Prüfung der Unterlagen und die Analyse."
        with self.assertRaises(app_offline.IdiomaNoSoportadoError):
            app_offline.anonimizar_texto_real_irreversible(texto_de)

    def test_procesar_archivos_reales_de_entrada(self):
        """Procesa y valida automáticamente todos los archivos presentes en la carpeta /entrada."""
        carpeta_entrada = app_offline.CARPETA_ENTRADA
        archivos_en_entrada = [
            f for f in os.listdir(carpeta_entrada)
            if not f.startswith(".") and not f.startswith("~$") and os.path.isfile(os.path.join(carpeta_entrada, f))
        ]

        if not archivos_en_entrada:
            # Si la carpeta está vacía, creamos archivos de prueba representativos (.txt y .csv)
            ruta_dummy_txt = os.path.join(carpeta_entrada, "test_muestra.txt")
            with open(ruta_dummy_txt, "w", encoding="utf-8") as f:
                f.write("Informe confidencial de María López (DNI 87654321A). Contacto: maria@test.com el 10/12/1990.")
            archivos_en_entrada = ["test_muestra.txt"]

        print(f"\n[+] Ejecutando test de anonimización sobre {len(archivos_en_entrada)} archivo(s) en /entrada...")

        cant_procesados = app_offline.ejecutar_anonimizacion_real_lotes(
            carpeta_salida=self.carpeta_salida_test,
            k_umbral=3,
            generalizar_cuasi=True
        )

        self.assertGreaterEqual(cant_procesados, 1)

        # Verificar que se crearon los archivos anonimizados y sus Certificados de Auditoría RGPD
        archivos_salida = os.listdir(self.carpeta_salida_test)
        certificados = [f for f in archivos_salida if f.startswith("Certificado_Anonimizacion_")]
        self.assertGreaterEqual(len(certificados), 1)

        # Verificar que NO se generaron archivos .key
        keys = [f for f in archivos_salida if f.endswith(".key")]
        self.assertEqual(len(keys), 0, "No deben generarse archivos .key en el flujo de anonimización real.")

        print(f"[OK] {cant_procesados} archivo(s) anonimizados exitosamente con {len(certificados)} certificado(s) RGPD.")

if __name__ == "__main__":
    unittest.main()
