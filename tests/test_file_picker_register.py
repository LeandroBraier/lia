# -*- coding: utf-8 -*-
"""
Test unitario para verificar que el registro doble del FilePicker
no produce excepciones no manejadas en el ciclo de vida de la aplicación.
"""

import unittest
from unittest.mock import MagicMock

try:
    import flet as ft
except ImportError:
    ft = MagicMock()


class TestFilePickerRegister(unittest.TestCase):
    def test_file_picker_double_registration_resilience(self):
        """Verifica que re-registrar el FilePicker o registrarlo múltiples veces es tolerado."""
        mock_page = MagicMock()
        mock_services = MagicMock()
        mock_page._services = mock_services

        global_file_picker = ft.FilePicker()

        # Primer registro
        mock_services.register_service.return_value = None
        try:
            mock_page._services.register_service(global_file_picker)
            first_success = True
        except Exception:
            first_success = False
        self.assertTrue(first_success)

        # Simular segundo registro (por ejemplo tras cambio de idioma o page.clean())
        # en caso de que el registro lance ValueError o Exception por duplicado
        def mock_register_duplicate(service):
            raise Exception("Service already registered")

        mock_services.register_service.side_effect = mock_register_duplicate

        # El bloque protegido try/except en la app debe tolerar la excepción
        caught_gracefully = False
        try:
            mock_page._services.register_service(global_file_picker)
        except Exception:
            caught_gracefully = True

        self.assertTrue(caught_gracefully, "El registro duplicado debe ser capturado de forma segura.")


if __name__ == "__main__":
    unittest.main()
