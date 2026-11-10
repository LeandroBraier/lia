# -*- coding: utf-8 -*-
"""
Lia Vault - Llaves de reversión cifradas (H4).

Cada documento seudonimizado tiene una sola llave (<documento>.lvkey) con la tabla token → valor original,
cifrada con AES-256-GCM. La clave maestra no se guarda en disco:
  1. Se guarda en el llavero del sistema (Llavero de macOS, Administrador de credenciales de Windows,
     Secret Service en Linux). Se genera la primera vez.
  2. Si no hay llavero (Docker, servidores sin escritorio), se deriva con scrypt de la frase de la variable
     de entorno LIA_VAULT_FRASE_MAESTRA.
Sin ninguna de las dos, no se guardan ni se leen llaves: la seudonimización falla en lugar de dejar el PII en claro.

Formato del archivo:
  LIAVAULT-LLAVE-v1
  {"creada": "...", "doc": "...", "kid": "..."}   ← autenticado (AAD), no cifrado
  base64(nonce || texto cifrado)
"""

import base64
import datetime
import hashlib
import json
import os
import secrets
import sys

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

ENCABEZADO = "LIAVAULT-LLAVE-v1"
EXTENSION = ".lvkey"
SERVICIO_LLAVERO = "Lia Vault"
CUENTA_LLAVERO = "clave-maestra"
VARIABLE_FRASE = "LIA_VAULT_FRASE_MAESTRA"
ARCHIVO_SAL = ".sal_frase"

_cache_clave = {}


class LlaveError(RuntimeError):
    pass


def carpeta_base():
    """
    Carpeta de datos de Lia Vault. LIA_VAULT_BASE la fija (en Docker, el volumen /datos; el código queda de solo
    lectura). El ejecutable compilado nunca guarda datos dentro de su paquete: se perderían (llaves incluidas)
    al actualizar la app.
    """
    if os.environ.get("LIA_VAULT_BASE"):
        return os.environ["LIA_VAULT_BASE"]
    base = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, "frozen", False) or not os.access(base, os.W_OK) or base.startswith("/Volumes/"):
        return os.path.join(os.path.expanduser("~"), "LiaVault")
    return base


def _clave_desde_llavero():
    """Clave maestra del llavero del sistema; la crea si no existe. None si no hay llavero utilizable."""
    try:
        import keyring
        from keyring.errors import KeyringError
    except ImportError:
        return None
    try:
        guardada = keyring.get_password(SERVICIO_LLAVERO, CUENTA_LLAVERO)
        if guardada:
            return base64.b64decode(guardada)
        nueva = AESGCM.generate_key(bit_length=256)
        keyring.set_password(SERVICIO_LLAVERO, CUENTA_LLAVERO, base64.b64encode(nueva).decode("ascii"))
        if keyring.get_password(SERVICIO_LLAVERO, CUENTA_LLAVERO) is None:
            return None
        return nueva
    except (KeyringError, RuntimeError, ValueError):
        return None


def _clave_desde_frase(carpeta_llaves):
    frase = os.environ.get(VARIABLE_FRASE)
    if not frase:
        return None
    if len(frase) < 12:
        raise LlaveError(f"La frase de {VARIABLE_FRASE} debe tener al menos 12 caracteres.")
    ruta_sal = os.path.join(carpeta_llaves, ARCHIVO_SAL)
    if os.path.exists(ruta_sal):
        with open(ruta_sal, "rb") as f:
            sal = f.read()
    else:
        sal = secrets.token_bytes(16)
        _escribir_privado(ruta_sal, sal)
    return Scrypt(salt=sal, length=32, n=2**15, r=8, p=1).derive(frase.encode("utf-8"))


def obtener_clave_maestra(carpeta_llaves):
    """Clave AES-256 de esta instalación. Lanza LlaveError si no hay llavero ni frase."""
    if carpeta_llaves in _cache_clave:
        return _cache_clave[carpeta_llaves]
    clave = _clave_desde_llavero() or _clave_desde_frase(carpeta_llaves)
    if clave is None or len(clave) != 32:
        raise LlaveError(
            "No hay dónde guardar la clave maestra de las llaves: el llavero del sistema no está disponible "
            f"y no se definió {VARIABLE_FRASE}."
        )
    _cache_clave[carpeta_llaves] = clave
    return clave


def huella(clave):
    """Identificador corto de la clave maestra, para saber con cuál se cifró una llave sin revelarla."""
    return hashlib.sha256(b"liavault-kid" + clave).hexdigest()[:16]


def preparar_carpeta(carpeta_llaves):
    os.makedirs(carpeta_llaves, exist_ok=True)
    try:
        os.chmod(carpeta_llaves, 0o700)
    except OSError:
        pass


def _escribir_privado(ruta, datos):
    """Escritura atómica con permisos 0600 desde el primer byte."""
    temporal = ruta + ".tmp"
    fd = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(datos)
        os.replace(temporal, ruta)
    except BaseException:
        if os.path.exists(temporal):
            os.remove(temporal)
        raise


def ruta_llave(carpeta_llaves, nombre_documento):
    return os.path.join(carpeta_llaves, f"{nombre_documento}{EXTENSION}")


def cifrar_mapa(mapa, nombre_documento, clave):
    meta = {"creada": datetime.datetime.now().isoformat(timespec="seconds"), "doc": nombre_documento, "kid": huella(clave)}
    linea_meta = json.dumps(meta, ensure_ascii=False, sort_keys=True)
    aad = f"{ENCABEZADO}\n{linea_meta}".encode("utf-8")
    nonce = secrets.token_bytes(12)
    cifrado = AESGCM(clave).encrypt(nonce, json.dumps(mapa, ensure_ascii=False).encode("utf-8"), aad)
    return f"{ENCABEZADO}\n{linea_meta}\n{base64.b64encode(nonce + cifrado).decode('ascii')}\n"


def descifrar_mapa(contenido, clave):
    lineas = contenido.strip().splitlines()
    if len(lineas) != 3 or lineas[0] != ENCABEZADO:
        raise LlaveError("El archivo no es una llave de Lia Vault.")
    try:
        meta = json.loads(lineas[1])
        bruto = base64.b64decode(lineas[2], validate=True)
    except ValueError:
        raise LlaveError("La llave está dañada.") from None
    if meta.get("kid") != huella(clave):
        raise LlaveError("Esta llave se creó en otra instalación de Lia Vault y no se puede abrir aquí.")
    aad = f"{lineas[0]}\n{lineas[1]}".encode("utf-8")
    try:
        mapa = AESGCM(clave).decrypt(bruto[:12], bruto[12:], aad)
    except InvalidTag:
        raise LlaveError("La llave fue modificada o está dañada.") from None
    return json.loads(mapa)


def guardar_llave(carpeta_llaves, nombre_documento, mapa):
    """Cifra y guarda la llave del documento. Lanza LlaveError u OSError si no se puede: nunca la deja en claro."""
    preparar_carpeta(carpeta_llaves)
    clave = obtener_clave_maestra(carpeta_llaves)
    ruta = ruta_llave(carpeta_llaves, nombre_documento)
    _escribir_privado(ruta, cifrar_mapa(mapa, nombre_documento, clave).encode("utf-8"))
    return ruta


def leer_llave(contenido, carpeta_llaves):
    """
    Devuelve el mapa de una llave. Acepta el formato cifrado y, para poder restaurar documentos antiguos,
    las llaves .key en JSON plano anteriores a la versión cifrada (migrables con herramientas/migrar_llaves.py).
    """
    if contenido.lstrip().startswith(ENCABEZADO):
        return descifrar_mapa(contenido, obtener_clave_maestra(carpeta_llaves))
    try:
        mapa = json.loads(contenido)
    except ValueError:
        raise LlaveError("El archivo no es una llave de Lia Vault.") from None
    if not isinstance(mapa, dict):
        raise LlaveError("El archivo no es una llave de Lia Vault.")
    return mapa


def leer_llave_archivo(ruta, carpeta_llaves):
    with open(ruta, "r", encoding="utf-8") as f:
        return leer_llave(f.read(), carpeta_llaves)


def migrar_llaves_antiguas(carpetas_origen, carpeta_llaves):
    """
    Cifra las llaves .key / .reverse.key en JSON plano de versiones anteriores y borra los originales,
    solo después de comprobar que la llave cifrada se lee igual. Retorna (migradas, omitidas).
    """
    agrupadas = {}
    for carpeta in carpetas_origen:
        if not os.path.isdir(carpeta):
            continue
        for f in os.listdir(carpeta):
            if f.endswith(".reverse.key"):
                nombre = f[:-len(".reverse.key")]
            elif f.endswith(".key"):
                nombre = f[:-len(".key")]
            else:
                continue
            agrupadas.setdefault(nombre, []).append(os.path.join(carpeta, f))

    migradas = omitidas = 0
    for nombre, rutas in agrupadas.items():
        mapa = {}
        try:
            for ruta in rutas:
                with open(ruta, "r", encoding="utf-8") as f:
                    contenido = json.load(f)
                if not isinstance(contenido, dict):
                    raise ValueError
                mapa.update(contenido)
        except (OSError, ValueError):
            omitidas += 1
            continue
        destino = ruta_llave(carpeta_llaves, nombre)
        if os.path.exists(destino) or not mapa:
            omitidas += 1
            continue
        guardar_llave(carpeta_llaves, nombre, mapa)
        if leer_llave_archivo(destino, carpeta_llaves) != mapa:
            os.remove(destino)
            omitidas += 1
            continue
        for ruta in rutas:
            os.remove(ruta)
        migradas += 1
    return migradas, omitidas
