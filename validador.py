# -*- coding: utf-8 -*-
"""
Lia Vault - Validación de licencias offline.

Las licencias se firman con Ed25519 fuera de la app (herramientas/licencias.py, que no se incluye en los
ejecutables). La app solo tiene la clave pública: puede verificar una licencia, pero no crearla.
Se aceptan dos archivos, en este orden:
  1. licencia.key: licencia que KOR emite para un cliente y que el cliente copia en su carpeta de trabajo.
  2. licencia_prueba.key: período de prueba firmado que se incluye en cada versión, con vencimiento fijo.
"""

import base64
import datetime
import json
import os
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# Clave pública de KOR para verificar licencias. La escribe `python3 herramientas/licencias.py generar-claves`.
CLAVE_PUBLICA_LICENCIAS = "g9XDQIaDpRQY1e5rXhHANuPxPzg6hXQ8fy1hCoCaNc0="

ENCABEZADO = "LIAVAULT-LICENCIA-v2"
NOMBRE_LICENCIA = "licencia.key"
NOMBRE_LICENCIA_PRUEBA = "licencia_prueba.key"
TIPOS = ("prueba", "comercial")


class LicenciaInvalidaError(ValueError):
    pass


def serializar_datos(datos):
    """Forma canónica de los datos firmados: JSON en una línea, claves ordenadas."""
    return json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def armar_licencia(datos, firma):
    return f"{ENCABEZADO}\n{serializar_datos(datos).decode('utf-8')}\n{base64.b64encode(firma).decode('ascii')}\n"


def leer_licencia(contenido, clave_publica_b64=None):
    """Verifica la firma y devuelve los datos de la licencia. Lanza LicenciaInvalidaError si no es válida."""
    clave = CLAVE_PUBLICA_LICENCIAS if clave_publica_b64 is None else clave_publica_b64
    if not clave:
        raise LicenciaInvalidaError("Esta versión no tiene configurada la clave pública de licencias.")
    lineas = contenido.strip().splitlines()
    if len(lineas) != 3 or lineas[0] != ENCABEZADO:
        raise LicenciaInvalidaError("Formato de licencia no reconocido. Las licencias anteriores deben renovarse.")
    datos_firmados = lineas[1].encode("utf-8")
    try:
        publica = Ed25519PublicKey.from_public_bytes(base64.b64decode(clave))
        publica.verify(base64.b64decode(lineas[2], validate=True), datos_firmados)
    except (InvalidSignature, ValueError):
        raise LicenciaInvalidaError("La firma de la licencia no es válida.") from None
    try:
        datos = json.loads(datos_firmados)
        datetime.date.fromisoformat(datos["vence"])
        if datos["tipo"] not in TIPOS or not datos["cliente"]:
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise LicenciaInvalidaError("La licencia tiene datos incompletos.") from None
    return datos


def _dir_recursos():
    """Carpeta de los archivos incluidos en la app (PyInstaller los deja en sys._MEIPASS)."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


class ValidadorLicencia:
    def __init__(self, ruta_licencia=None, ruta_db_oculta=None, ruta_prueba=None):
        dir_actual = os.getcwd()
        archivo_prueba = os.path.join(dir_actual, ".test_write_perm")
        es_escribible = True
        try:
            with open(archivo_prueba, "w") as f:
                f.write("test")
            os.remove(archivo_prueba)
        except (OSError, IOError):
            es_escribible = False

        if es_escribible:
            self.ruta_licencia = ruta_licencia or f"./{NOMBRE_LICENCIA}"
            self.ruta_db_oculta = ruta_db_oculta or "./.vault_log.db"
        else:
            base_w = os.path.expanduser("~/LiaVault_Workspace")
            os.makedirs(base_w, exist_ok=True)
            self.ruta_licencia = ruta_licencia or os.path.join(base_w, NOMBRE_LICENCIA)
            self.ruta_db_oculta = ruta_db_oculta or os.path.join(base_w, ".vault_log.db")
        self.ruta_prueba = ruta_prueba or os.path.join(_dir_recursos(), NOMBRE_LICENCIA_PRUEBA)

    def registrar_ejecucion_local(self):
        """
        Guarda la última fecha de ejecución exitosa de forma oculta.
        Sirve para detectar si el usuario atrasó el reloj de su servidor (fraude temporal).
        """
        hoy_str = datetime.date.today().isoformat()
        try:
            with open(self.ruta_db_oculta, "w") as f:
                f.write(hoy_str)
        except Exception:
            pass

    def comprobar_reloj_alterado(self):
        """
        Retorna True si el reloj del sistema es anterior a la última fecha de ejecución guardada.
        """
        if not os.path.exists(self.ruta_db_oculta):
            return False

        try:
            with open(self.ruta_db_oculta, "r") as f:
                ultima_fecha_str = f.read().strip()

            ultima_fecha = datetime.date.fromisoformat(ultima_fecha_str)
            hoy = datetime.date.today()

            # Si el día de hoy es anterior a la última fecha de registro, hay alteración de reloj
            if hoy < ultima_fecha:
                return True
        except Exception:
            pass
        return False

    def _evaluar(self, ruta):
        """(es_valida, mensaje, cliente_id, dias_restantes) para un archivo de licencia."""
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = leer_licencia(f.read())
        except LicenciaInvalidaError as e:
            return False, f"❌ {e}", "Desconocido", 0
        except (OSError, UnicodeDecodeError):
            return False, f"❌ No se pudo leer el archivo '{os.path.basename(ruta)}'.", "Desconocido", 0

        cliente_id = datos["cliente"]
        vencimiento = datetime.date.fromisoformat(datos["vence"])
        hoy = datetime.date.today()
        es_prueba = datos["tipo"] == "prueba"
        if hoy > vencimiento:
            que = "El periodo de prueba" if es_prueba else "La licencia"
            return False, f"❌ {que} venció el {datos['vence']}.", cliente_id, 0
        dias_restantes = (vencimiento - hoy).days
        detalle = "de prueba" if es_prueba else "de licencia"
        return True, f"✅ Licencia válida para {cliente_id}. Quedan {dias_restantes} días {detalle}.", cliente_id, dias_restantes

    def verificar_licencia_offline(self):
        """
        Verifica la licencia del cliente y, si no hay una válida, la de prueba incluida en la versión.
        Nunca crea ni repara licencias. Retorna: (es_valida, mensaje, cliente_id, dias_restantes)
        """
        if self.comprobar_reloj_alterado():
            return False, "⚠️ Alerta de Seguridad: Se detectó manipulación del reloj del sistema.", "N/A", 0

        resultados = [self._evaluar(r) for r in (self.ruta_licencia, self.ruta_prueba) if os.path.isfile(r)]
        if not resultados:
            return False, "❌ No hay una licencia instalada. Solicite una a hello@korautomate.com.", "Desconocido", 0
        for resultado in resultados:
            if resultado[0]:
                # Registrar ejecución válida para evitar fraude de reloj en el futuro
                self.registrar_ejecucion_local()
                return resultado
        return resultados[0]


if __name__ == "__main__":
    valido, msg, cliente, dias = ValidadorLicencia().verificar_licencia_offline()
    print(f"Resultado de verificación local: {valido}")
    print(f"Mensaje oficial: {msg}")
    print(f"Días restantes de acceso: {dias}")
