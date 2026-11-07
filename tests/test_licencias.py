# -*- coding: utf-8 -*-
"""
Pruebas de licencias firmadas con Ed25519 (H9): solo se aceptan licencias firmadas con la clave privada de KOR,
la app nunca crea ni repara licencias y la de prueba incluida en la versión se usa si no hay otra válida.
"""

import base64
import datetime
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "herramientas"))
import validador  # noqa: E402
from licencias import emitir_licencia  # noqa: E402

HOY = datetime.date.today()


def _par_de_claves():
    privada = Ed25519PrivateKey.generate()
    publica = privada.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return privada, base64.b64encode(publica).decode("ascii")


class TestLicencias(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.privada, publica = _par_de_claves()
        self.clave = patch.object(validador, "CLAVE_PUBLICA_LICENCIAS", publica)
        self.clave.start()
        self.v = validador.ValidadorLicencia(
            ruta_licencia=os.path.join(self.dir, "licencia.key"),
            ruta_db_oculta=os.path.join(self.dir, ".vault_log.db"),
            ruta_prueba=os.path.join(self.dir, "licencia_prueba.key"),
        )

    def tearDown(self):
        self.clave.stop()
        shutil.rmtree(self.dir, ignore_errors=True)

    def _guardar(self, ruta, contenido):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)

    def _licencia(self, cliente="Empresa SL", tipo="comercial", dias=30):
        return emitir_licencia(self.privada, cliente, tipo, HOY + datetime.timedelta(days=dias))

    def test_licencia_comercial_valida(self):
        self._guardar(self.v.ruta_licencia, self._licencia())
        valida, _, cliente, dias = self.v.verificar_licencia_offline()
        self.assertTrue(valida)
        self.assertEqual((cliente, dias), ("Empresa SL", 30))

    def test_sin_licencia_no_crea_ninguna(self):
        valida, _, _, _ = self.v.verificar_licencia_offline()
        self.assertFalse(valida)
        self.assertFalse(os.path.exists(self.v.ruta_licencia))

    def test_datos_modificados_invalidan_la_firma(self):
        alterada = self._licencia().replace(f'"vence":"{(HOY + datetime.timedelta(days=30)).isoformat()}"', '"vence":"2099-12-31"')
        self._guardar(self.v.ruta_licencia, alterada)
        valida, mensaje, _, _ = self.v.verificar_licencia_offline()
        self.assertFalse(valida)
        self.assertIn("firma", mensaje)

    def test_firmada_con_otra_clave_se_rechaza(self):
        otra, _ = _par_de_claves()
        datos = {"cliente": "Empresa SL", "tipo": "comercial", "emitida": HOY.isoformat(), "vence": "2099-12-31"}
        self._guardar(self.v.ruta_licencia, validador.armar_licencia(datos, otra.sign(validador.serializar_datos(datos))))
        self.assertFalse(self.v.verificar_licencia_offline()[0])

    def test_formato_anterior_se_rechaza_sin_autorreparar(self):
        self._guardar(self.v.ruta_licencia, "0" * 64 + "\n2099-12-31|Usuario On-Premise")
        valida, mensaje, _, _ = self.v.verificar_licencia_offline()
        self.assertFalse(valida)
        self.assertIn("renovarse", mensaje)
        with open(self.v.ruta_licencia, encoding="utf-8") as f:
            self.assertTrue(f.read().startswith("0" * 64), "la app no debe reescribir la licencia")

    def test_licencia_vencida(self):
        self._guardar(self.v.ruta_licencia, self._licencia(dias=-1))
        valida, mensaje, _, dias = self.v.verificar_licencia_offline()
        self.assertFalse(valida)
        self.assertEqual(dias, 0)
        self.assertIn("venció", mensaje)

    def test_usa_la_prueba_incluida_si_no_hay_licencia_valida(self):
        self._guardar(self.v.ruta_licencia, "licencia antigua")
        self._guardar(self.v.ruta_prueba, self._licencia(cliente="Prueba Lia Vault", tipo="prueba", dias=365))
        valida, mensaje, cliente, _ = self.v.verificar_licencia_offline()
        self.assertTrue(valida)
        self.assertEqual(cliente, "Prueba Lia Vault")
        self.assertIn("de prueba", mensaje)

    def test_la_licencia_comercial_tiene_prioridad(self):
        self._guardar(self.v.ruta_licencia, self._licencia(dias=10))
        self._guardar(self.v.ruta_prueba, self._licencia(cliente="Prueba Lia Vault", tipo="prueba", dias=365))
        self.assertEqual(self.v.verificar_licencia_offline()[2], "Empresa SL")

    def test_reloj_atrasado(self):
        self._guardar(self.v.ruta_licencia, self._licencia())
        self._guardar(self.v.ruta_db_oculta, (HOY + datetime.timedelta(days=5)).isoformat())
        self.assertFalse(self.v.verificar_licencia_offline()[0])

    def test_sin_clave_publica_ninguna_licencia_es_valida(self):
        self._guardar(self.v.ruta_licencia, self._licencia())
        with patch.object(validador, "CLAVE_PUBLICA_LICENCIAS", ""):
            self.assertFalse(self.v.verificar_licencia_offline()[0])

    def test_la_app_no_contiene_firma_ni_salt(self):
        codigo = open(validador.__file__, encoding="utf-8").read()
        self.assertNotIn("SALT", codigo)
        self.assertNotIn("Ed25519PrivateKey", codigo)


if __name__ == "__main__":
    unittest.main()
