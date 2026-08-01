# -*- coding: utf-8 -*-
"""
Script auxiliar para emitir licencias corporativas de prueba o de clientes en Lia Vault.
Sintaxis: python3 generar_key_prueba.py <email_o_cliente> <dias_validez>
"""

import sys
import os
import datetime
import hashlib

def generar_key(cliente_id="leandro@korautomate.com", dias=365):
    salt = "LIA_VAULT_SECURITY_DEFAULT_SALT" # Salt por defecto sin .env
    hoy = datetime.date.today()
    vencimiento = (hoy + datetime.timedelta(days=dias)).isoformat()
    
    info_basica = f"{vencimiento}|{cliente_id}"
    hash_firma = hashlib.sha256(info_basica.encode('utf-8') + salt.encode('utf-8')).hexdigest()
    
    contenido = f"{hash_firma}\n{info_basica}"
    
    ruta_licencia = "licencia.key"
    with open(ruta_licencia, "w", encoding="utf-8") as f:
        f.write(contenido)
    
    print(f"✅ Archivo '{ruta_licencia}' generado exitosamente.")
    print(f"👤 Cliente: {cliente_id}")
    print(f"📅 Vencimiento: {vencimiento} ({dias} días)")
    print(f"🔑 Firma SHA256: {hash_firma}")

if __name__ == "__main__":
    cliente = sys.argv[1] if len(sys.argv) > 1 else "leandro@korautomate.com"
    dias_val = int(sys.argv[2]) if len(sys.argv) > 2 else 365
    generar_key(cliente, dias_val)
