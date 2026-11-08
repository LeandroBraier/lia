# -*- coding: utf-8 -*-
"""Aislamiento común de las pruebas: nunca usan el llavero real del equipo ni escriben en el registro real."""

import sys

import pytest

import auditoria
import llaves

CLAVE_PRUEBAS = bytes(range(32))


@pytest.fixture(autouse=True)
def aislar_llavero_y_registro(tmp_path, monkeypatch):
    llaves._cache_clave.clear()
    monkeypatch.setattr(llaves, "_clave_desde_llavero", lambda: CLAVE_PRUEBAS)
    if "app_offline" in sys.modules:
        registro = auditoria.RegistroAuditoria(str(tmp_path / "Registros" / "lia_vault.log"), lambda: CLAVE_PRUEBAS)
        monkeypatch.setattr(sys.modules["app_offline"], "registro", registro)
    yield
    llaves._cache_clave.clear()
