# -*- coding: utf-8 -*-
"""
Herramienta de KOR para firmar licencias de Lia Vault. No se incluye en los ejecutables.

  python3 herramientas/licencias.py generar-claves
  python3 herramientas/licencias.py emitir --cliente "Empresa SL" --dias 365
  python3 herramientas/licencias.py emitir --cliente "Empresa SL" --vence 2027-12-31 --salida licencia.key
  python3 herramientas/licencias.py emitir --tipo prueba --cliente "Prueba Lia Vault" --dias 365 --salida licencia_prueba.key

La clave privada nunca se guarda en disco: se muestra una sola vez al generarla y, al emitir, se pide sin
mostrarla en pantalla o se toma de la variable de entorno LIA_VAULT_CLAVE_PRIVADA.
"""

import argparse
import base64
import datetime
import getpass
import os
import re
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import validador  # noqa: E402

PREFIJO_PRIVADA = "LIAVAULT-PRIV-v1:"
RUTA_VALIDADOR = os.path.join(RAIZ, "validador.py")
RX_CLAVE_PUBLICA = re.compile(r'^CLAVE_PUBLICA_LICENCIAS = ".*"$', re.MULTILINE)


def _b64(datos):
    return base64.b64encode(datos).decode("ascii")


def _publica_b64(privada):
    return _b64(privada.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def obtener_clave_privada():
    """Lee la clave privada de LIA_VAULT_CLAVE_PRIVADA o la pide sin mostrarla, y comprueba que corresponda
    a la clave pública configurada en validador.py."""
    if not validador.CLAVE_PUBLICA_LICENCIAS:
        sys.exit("validador.py no tiene clave pública. Ejecute primero: generar-claves")
    texto = os.environ.get("LIA_VAULT_CLAVE_PRIVADA") or getpass.getpass("Clave privada de licencias (no se muestra): ")
    texto = texto.strip()
    if not texto.startswith(PREFIJO_PRIVADA):
        sys.exit(f"La clave privada debe empezar con {PREFIJO_PRIVADA}")
    try:
        privada = Ed25519PrivateKey.from_private_bytes(base64.b64decode(texto[len(PREFIJO_PRIVADA):], validate=True))
    except ValueError:
        sys.exit("La clave privada no es válida (¿se copió completa?).")
    if _publica_b64(privada) != validador.CLAVE_PUBLICA_LICENCIAS:
        sys.exit("La clave privada no corresponde a la clave pública de validador.py.")
    return privada


def emitir_licencia(privada, cliente, tipo, vence):
    """Devuelve el contenido de un archivo de licencia firmado."""
    datos = {
        "cliente": cliente,
        "tipo": tipo,
        "emitida": datetime.date.today().isoformat(),
        "vence": vence.isoformat(),
    }
    contenido = validador.armar_licencia(datos, privada.sign(validador.serializar_datos(datos)))
    validador.leer_licencia(contenido)  # comprobación: la app la acepta
    return contenido


def cmd_generar_claves(args):
    if validador.CLAVE_PUBLICA_LICENCIAS and not args.reemplazar:
        sys.exit("Ya hay una clave pública en validador.py. Reemplazarla invalida TODAS las licencias emitidas.\n"
                 "Si es lo que quiere, repita con --reemplazar.")
    privada = Ed25519PrivateKey.generate()
    codigo = open(RUTA_VALIDADOR, encoding="utf-8").read()
    codigo, n = RX_CLAVE_PUBLICA.subn(f'CLAVE_PUBLICA_LICENCIAS = "{_publica_b64(privada)}"', codigo)
    if n != 1:
        sys.exit("No se encontró la línea CLAVE_PUBLICA_LICENCIAS en validador.py.")
    with open(RUTA_VALIDADOR, "w", encoding="utf-8") as f:
        f.write(codigo)
    privada_txt = PREFIJO_PRIVADA + _b64(privada.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
    print("Clave pública guardada en validador.py.\n")
    print("CLAVE PRIVADA. Guárdela ahora en su gestor de contraseñas: no se vuelve a mostrar ni se guarda en disco.\n")
    print(privada_txt)
    print("\nDespués de guardarla, limpie la pantalla de la terminal (Cmd+K en macOS).")


def cmd_emitir(args):
    if args.vence:
        vence = datetime.date.fromisoformat(args.vence)
    else:
        vence = datetime.date.today() + datetime.timedelta(days=args.dias)
    privada = obtener_clave_privada()
    contenido = emitir_licencia(privada, args.cliente, args.tipo, vence)
    with open(args.salida, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"Licencia {args.tipo} para '{args.cliente}' hasta el {vence.isoformat()} guardada en {args.salida}")


def main():
    parser = argparse.ArgumentParser(description="Firma de licencias de Lia Vault (uso interno de KOR).")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("generar-claves", help="Crea el par de claves y guarda la pública en validador.py.")
    p.add_argument("--reemplazar", action="store_true", help="Reemplaza la clave existente (invalida las licencias).")
    p.set_defaults(func=cmd_generar_claves)

    p = sub.add_parser("emitir", help="Emite una licencia firmada.")
    p.add_argument("--cliente", required=True, help="Nombre o correo del cliente.")
    p.add_argument("--tipo", choices=validador.TIPOS, default="comercial")
    plazo = p.add_mutually_exclusive_group(required=True)
    plazo.add_argument("--dias", type=int, help="Días de validez desde hoy.")
    plazo.add_argument("--vence", help="Fecha de vencimiento (AAAA-MM-DD).")
    p.add_argument("--salida", default=validador.NOMBRE_LICENCIA, help="Archivo de salida (por defecto licencia.key).")
    p.set_defaults(func=cmd_emitir)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
