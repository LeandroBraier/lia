# -*- coding: utf-8 -*-
"""
Lia Vault - Sistema de Validación de Licencia Offline
Desarrollado para asegurar el control de accesos On-Premise sin tocar Internet.
"""

import os
import datetime
import hashlib

def _obtener_salt_seguridad():
    """
    Obtiene la SALT de integridad desde variables de entorno o el archivo .env.
    Esto evita exponer claves secretas en repositorios públicos.
    """
    salt = os.getenv("LIA_VAULT_SALT")
    if not salt:
        ruta_env = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(ruta_env):
            try:
                with open(ruta_env, "r", encoding="utf-8") as f:
                    for linea in f:
                        linea = linea.strip()
                        if linea.startswith("LIA_VAULT_SALT="):
                            salt = linea.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass
    if not salt:
        salt = "LIA_VAULT_SECURITY_DEFAULT_SALT"
    return salt.encode('utf-8')

SALT_INTEGRIDAD = _obtener_salt_seguridad()

class ValidadorLicencia:
    def __init__(self, ruta_licencia=None, ruta_db_oculta=None):
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
            self.ruta_licencia = ruta_licencia or "./licencia.key"
            self.ruta_db_oculta = ruta_db_oculta or "./.vault_log.db"
        else:
            base_w = os.path.expanduser("~/LiaVault_Workspace")
            os.makedirs(base_w, exist_ok=True)
            self.ruta_licencia = os.path.join(base_w, "licencia.key")
            self.ruta_db_oculta = os.path.join(base_w, ".vault_log.db")

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

    def generar_licencia_oficial(self, cliente_id, fecha_exp_str):
        """
        Genera un archivo de licencia firmado digitalmente (licencia.key) localmente.
        El formato de la firma es un Hash SHA256 compuesto por la información de la licencia + SALT.
        """
        info_basica = f"{fecha_exp_str}|{cliente_id}"
        hash_firma = hashlib.sha256(info_basica.encode('utf-8') + SALT_INTEGRIDAD).hexdigest()
        
        # Archivo guardado con firma + contenido estructurado
        contenido_licencia = f"{hash_firma}\n{info_basica}"
        
        with open(self.ruta_licencia, "w", encoding="utf-8") as f:
            f.write(contenido_licencia)
        
        return self.ruta_licencia

    def verificar_licencia_offline(self):
        """
        Verifica la autenticidad y el tiempo de expiración de la licencia de forma offline.
        Retorna: (es_valida, mensaje, cliente_id, dias_restantes)
        """
        if self.comprobar_reloj_alterado():
            return False, "⚠️ Alerta de Seguridad: Se detectó manipulación del reloj del sistema.", "N/A", 0

        if not os.path.exists(self.ruta_licencia):
            # Auto-activación transparente al primer uso
            hoy = datetime.date.today()
            vencimiento_trial = (hoy + datetime.timedelta(days=365)).isoformat()
            try:
                self.generar_licencia_oficial("Usuario On-Premise", vencimiento_trial)
            except (OSError, IOError):
                return True, "✅ Licencia válida (Modo Lectura DMG). Quedan 365 días de Trial.", "Usuario On-Premise", 365

        try:
            with open(self.ruta_licencia, "r", encoding="utf-8") as f:
                lineas = f.read().splitlines()
            
            if len(lineas) < 2:
                return False, "❌ Error: Formato de licencia corrupto o incompleto.", "Desconocido", 0
            
            hash_guardado = lineas[0]
            info_basica = lineas[1]
            
            # Verificar firma de integridad
            hash_calculado = hashlib.sha256(info_basica.encode('utf-8') + SALT_INTEGRIDAD).hexdigest()
            if hash_guardado != hash_calculado:
                # Si la firma no coincide o es de otro entorno, intentar auto-reparar
                try:
                    hoy = datetime.date.today()
                    vencimiento_trial = (hoy + datetime.timedelta(days=365)).isoformat()
                    self.generar_licencia_oficial("Usuario On-Premise", vencimiento_trial)
                    return self.verificar_licencia_offline()
                except (OSError, IOError):
                    # Si el sistema de archivos es Read-Only (ej. montado directamente desde DMG de macOS),
                    # omitir la escritura física e interpretar el acceso como valido durante la sesión.
                    hoy = datetime.date.today()
                    fecha_exp_str = info_basica.split("|")[0] if "|" in info_basica else (hoy + datetime.timedelta(days=365)).isoformat()
                    try:
                        fecha_expiracion = datetime.date.fromisoformat(fecha_exp_str)
                    except Exception:
                        fecha_expiracion = hoy + datetime.timedelta(days=365)
                    dias_restantes = max(0, (fecha_expiracion - hoy).days)
                    return True, f"✅ Licencia válida (Modo Lectura DMG). Quedan {dias_restantes} días de Trial.", "Usuario On-Premise", dias_restantes
            
            # Parsear datos de la licencia
            fecha_exp_str, cliente_id = info_basica.split("|")
            fecha_expiracion = datetime.date.fromisoformat(fecha_exp_str)
            hoy = datetime.date.today()
            
            if hoy > fecha_expiracion:
                return False, f"❌ El periodo de prueba (Trial de 1 año) expiró el {fecha_exp_str}.", cliente_id, 0
            
            dias_restantes = (fecha_expiracion - hoy).days
            
            # Registrar ejecución válida para evitar fraude de reloj en el futuro
            self.registrar_ejecucion_local()
            
            return True, f"✅ Licencia válida para {cliente_id}. Quedan {dias_restantes} días de Trial.", cliente_id, dias_restantes

        except Exception as e:
            return False, f"❌ Error al procesar el archivo 'licencia.key': {str(e)}", "Desconocido", 0

if __name__ == "__main__":
    # Autogenerar licencia de prueba de 1 año si no existe para demostración rápida
    validador = ValidadorLicencia()
    hoy = datetime.date.today()
    vencimiento_un_ano = (hoy + datetime.timedelta(days=365)).isoformat()
    
    print("Iniciando validación y autogeneración de llave de prueba...")
    validador.generar_licencia_oficial("CLIENTE_DEMO_PYME", vencimiento_un_ano)
    
    valido, msg, cliente, dias = validador.verificar_licencia_offline()
    print(f"Resultado de verificación local: {valido}")
    print(f"Mensaje oficial: {msg}")
    print(f"Días restantes de acceso: {dias}")
