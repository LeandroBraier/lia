# -*- coding: utf-8 -*-
"""
Pruebas de las llaves de reversión cifradas (H4): una sola llave por documento, cifrada con AES-256-GCM,
en una carpeta aparte con permisos 0600, y sin clave maestra no se guarda nada en claro.
"""

import json
import os
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch

import llaves

CLAVE = bytes(range(32))
MAPA = {"[PERSONA_1]": "Juan Pérez", "[CORREO_1]": "juan@empresa.com"}


class BaseLlaves(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.carpeta = os.path.join(self.dir, "Llaves")
        llaves._cache_clave.clear()
        self.llavero = patch.object(llaves, "_clave_desde_llavero", return_value=CLAVE)
        self.llavero.start()

    def tearDown(self):
        self.llavero.stop()
        llaves._cache_clave.clear()
        shutil.rmtree(self.dir, ignore_errors=True)


class TestLlaves(BaseLlaves):
    def test_ida_y_vuelta_sin_pii_en_claro(self):
        ruta = llaves.guardar_llave(self.carpeta, "informe.docx", MAPA)
        contenido = open(ruta, encoding="utf-8").read()
        self.assertNotIn("Juan", contenido)
        self.assertNotIn("juan@empresa.com", contenido)
        self.assertEqual(llaves.leer_llave_archivo(ruta, self.carpeta), MAPA)

    @unittest.skipIf(os.name == "nt", "permisos POSIX")
    def test_permisos_privados(self):
        ruta = llaves.guardar_llave(self.carpeta, "informe.docx", MAPA)
        self.assertEqual(stat.S_IMODE(os.stat(ruta).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.carpeta).st_mode), 0o700)

    def test_alteraciones_se_detectan(self):
        contenido = llaves.cifrar_mapa(MAPA, "informe.docx", CLAVE)
        encabezado, meta, cifrado = contenido.strip().splitlines()
        otro_doc = meta.replace("informe.docx", "otro.docx")
        bits = cifrado[:-4] + ("AAAA" if cifrado[-4:] != "AAAA" else "BBBB")
        for alterada in (f"{encabezado}\n{otro_doc}\n{cifrado}", f"{encabezado}\n{meta}\n{bits}"):
            with self.subTest(alterada=alterada[-10:]):
                with self.assertRaises(llaves.LlaveError):
                    llaves.descifrar_mapa(alterada, CLAVE)

    def test_llave_de_otra_instalacion(self):
        contenido = llaves.cifrar_mapa(MAPA, "informe.docx", bytes(32))
        with self.assertRaisesRegex(llaves.LlaveError, "otra instalación"):
            llaves.descifrar_mapa(contenido, CLAVE)

    def test_llave_antigua_en_claro_se_puede_leer(self):
        self.assertEqual(llaves.leer_llave(json.dumps(MAPA), self.carpeta), MAPA)
        with self.assertRaises(llaves.LlaveError):
            llaves.leer_llave("LIAVAULT-LICENCIA-v2\n{}\nAAAA", self.carpeta)


class TestClaveMaestra(BaseLlaves):
    def setUp(self):
        super().setUp()
        self.llavero.stop()
        self.llavero = patch.object(llaves, "_clave_desde_llavero", return_value=None)
        self.llavero.start()

    def test_sin_llavero_ni_frase_no_se_guarda_nada(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(llaves.VARIABLE_FRASE, None)
            with self.assertRaises(llaves.LlaveError):
                llaves.guardar_llave(self.carpeta, "informe.docx", MAPA)
        self.assertFalse(os.path.exists(llaves.ruta_llave(self.carpeta, "informe.docx")))

    def test_frase_de_respaldo(self):
        with patch.dict(os.environ, {llaves.VARIABLE_FRASE: "una frase bastante larga"}):
            ruta = llaves.guardar_llave(self.carpeta, "informe.docx", MAPA)
            llaves._cache_clave.clear()
            self.assertEqual(llaves.leer_llave_archivo(ruta, self.carpeta), MAPA)

    def test_frase_corta_se_rechaza(self):
        with patch.dict(os.environ, {llaves.VARIABLE_FRASE: "corta"}):
            with self.assertRaises(llaves.LlaveError):
                llaves.obtener_clave_maestra(self.carpeta)


class TestMigracion(BaseLlaves):
    def test_migra_y_borra_las_llaves_en_claro(self):
        salida = os.path.join(self.dir, "Seudonimizados")
        os.makedirs(salida)
        for sufijo in (".key", ".reverse.key"):
            with open(os.path.join(salida, f"informe.docx{sufijo}"), "w", encoding="utf-8") as f:
                json.dump(MAPA, f)
        with open(os.path.join(salida, "roto.pdf.key"), "w", encoding="utf-8") as f:
            f.write("no es json")

        self.assertEqual(llaves.migrar_llaves_antiguas([salida], self.carpeta), (1, 1))
        self.assertEqual(sorted(os.listdir(salida)), ["roto.pdf.key"])
        ruta = llaves.ruta_llave(self.carpeta, "informe.docx")
        self.assertEqual(llaves.leer_llave_archivo(ruta, self.carpeta), MAPA)


class TestMotorConLlaves(BaseLlaves):
    def setUp(self):
        super().setUp()
        import app_offline
        self.app = app_offline
        self.rutas = [
            patch.object(app_offline, "CARPETA_LLAVES", self.carpeta),
            patch.object(app_offline, "CARPETA_ENTRADA", os.path.join(self.dir, "Entrada")),
            patch.object(app_offline, "CARPETA_PROCESADOS", os.path.join(self.dir, "procesados")),
        ]
        for p in self.rutas:
            p.start()
        os.makedirs(app_offline.CARPETA_ENTRADA)
        self.salida = os.path.join(self.dir, "Seudonimizados")
        with open(os.path.join(app_offline.CARPETA_ENTRADA, "nota.txt"), "w", encoding="utf-8") as f:
            f.write("El informe confidencial de María López fue enviado ayer por la tarde. "
                    "Para cualquier consulta, su correo es maria@test.com y su teléfono es 600123456.")

    def tearDown(self):
        for p in self.rutas:
            p.stop()
        super().tearDown()

    def test_seudonimizar_guarda_una_llave_cifrada_aparte(self):
        if self.app.analyzer is None:
            self.skipTest("motor de IA no disponible")
        self.assertEqual(self.app.ejecutar_procesamiento_lotes(carpeta_salida=self.salida), 1)
        self.assertFalse([f for f in os.listdir(self.salida) if f.endswith(".key")])
        (salida,) = os.listdir(self.salida)
        ruta = self.app.buscar_llave(salida, self.salida)
        self.assertEqual(os.path.dirname(ruta), self.carpeta)
        mapa = llaves.leer_llave_archivo(ruta, self.carpeta)
        self.assertIn("maria@test.com", mapa.values())

        with open(self.app.registro.ruta, encoding="utf-8") as f:
            registro = f.read()
        self.assertNotIn("María", registro)
        self.assertNotIn("maria@test.com", registro)
        evento = json.loads(registro.splitlines()[-1])
        self.assertEqual((evento["evento"], evento["estado"], evento["ext"]), ("seudonimizacion", "ok", ".txt"))
        self.assertTrue(evento["entidades"])

    def test_sin_clave_maestra_no_procesa(self):
        with patch.object(llaves, "_clave_desde_llavero", return_value=None), patch.dict(os.environ, {}, clear=False):
            os.environ.pop(llaves.VARIABLE_FRASE, None)
            with self.assertRaises(llaves.LlaveError):
                self.app.ejecutar_procesamiento_lotes(carpeta_salida=self.salida)
        self.assertTrue(os.path.exists(os.path.join(self.app.CARPETA_ENTRADA, "nota.txt")))
        self.assertFalse(os.path.exists(self.salida) and os.listdir(self.salida))


if __name__ == "__main__":
    unittest.main()
