# -*- coding: utf-8 -*-
"""
Pruebas del registro de auditoría (H5): solo metadatos, nunca PII; firmas encadenadas que detectan
ediciones y borrados; permisos 0600; y un fallo del registro no detiene el procesamiento.
"""

import json
import os
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch

import auditoria

CLAVE = bytes(range(32))


class TestAuditoria(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.ruta = os.path.join(self.dir, "Registros", "lia_vault.log")
        self.reg = auditoria.RegistroAuditoria(self.ruta, lambda: CLAVE)
        self.doc = os.path.join(self.dir, "Contrato Juan Pérez.docx")
        with open(self.doc, "w", encoding="utf-8") as f:
            f.write("Juan Pérez, DNI 12345678Z")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _lineas(self):
        with open(self.ruta, encoding="utf-8") as f:
            return f.read().splitlines()

    def test_solo_metadatos(self):
        self.reg.registrar("seudonimizacion", ruta_archivo=self.doc, entidades={"PERSONA": 1, "DOCUMENTO": 1})
        self.reg.registrar("seudonimizacion", "error", ruta_archivo=self.doc, error=ValueError("Juan Pérez no encaja"))
        contenido = open(self.ruta, encoding="utf-8").read()
        for pii in ("Juan", "Pérez", "12345678Z", "Contrato"):
            self.assertNotIn(pii, contenido)
        primera, segunda = (json.loads(l) for l in self._lineas())
        self.assertEqual(primera["ext"], ".docx")
        self.assertEqual(primera["sha256"], auditoria.sha256_archivo(self.doc))
        self.assertEqual(primera["entidades"], {"PERSONA": 1, "DOCUMENTO": 1})
        self.assertEqual(segunda["error"], "ValueError")

    @unittest.skipIf(os.name == "nt", "permisos POSIX")
    def test_permisos_privados(self):
        self.reg.registrar("anonimizacion")
        self.assertEqual(stat.S_IMODE(os.stat(self.ruta).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(self.ruta)).st_mode), 0o700)

    def test_cadena_integra_y_continua_tras_reiniciar(self):
        self.reg.registrar("seudonimizacion")
        auditoria.RegistroAuditoria(self.ruta, lambda: CLAVE).registrar("reversion")
        ok, detalle = auditoria.verificar(self.ruta, auditoria.derivar_clave(CLAVE))
        self.assertTrue(ok, detalle)
        self.assertIn("2 eventos", detalle)

    def test_detecta_edicion_y_borrado(self):
        for _ in range(3):
            self.reg.registrar("seudonimizacion")
        original = self._lineas()
        editada = original[:]
        editada[1] = editada[1].replace('"ok"', '"error"')
        for lineas in (editada, [original[0], original[2]]):
            with self.subTest(lineas=len(lineas)):
                with open(self.ruta, "w", encoding="utf-8") as f:
                    f.write("\n".join(lineas) + "\n")
                self.assertFalse(auditoria.verificar(self.ruta, auditoria.derivar_clave(CLAVE))[0])

    def test_otra_clave_no_verifica(self):
        self.reg.registrar("seudonimizacion")
        self.assertFalse(auditoria.verificar(self.ruta, auditoria.derivar_clave(bytes(32)))[0])

    def test_rotacion_mantiene_la_cadena(self):
        with patch.object(auditoria, "TAMANO_MAXIMO", 400):
            reg = auditoria.RegistroAuditoria(self.ruta, lambda: CLAVE)
            for _ in range(6):
                reg.registrar("seudonimizacion")
        self.assertTrue(os.path.exists(self.ruta + ".1"))
        self.assertTrue(auditoria.verificar(self.ruta, auditoria.derivar_clave(CLAVE))[0])

    def test_fallo_del_registro_no_detiene(self):
        def sin_clave():
            raise RuntimeError("sin llavero")
        auditoria.RegistroAuditoria(self.ruta, sin_clave).registrar("seudonimizacion")
        self.assertFalse(os.path.exists(self.ruta))

    def test_eventos_desconocidos_se_rechazan(self):
        with self.assertRaises(ValueError):
            self.reg.registrar("Juan Pérez")

    def test_contar_entidades(self):
        mapa = {"[PERSONA_1]": "a", "[PERSONA_2]": "b", "[CORREO_ELECTRONICO_1]": "c", "[PAG2_IMAGE_PII_1]": "d"}
        self.assertEqual(auditoria.contar_entidades(mapa), {"PERSONA": 2, "CORREO_ELECTRONICO": 1, "IMAGE_PII": 1})


if __name__ == "__main__":
    unittest.main()
