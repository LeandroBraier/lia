# -*- coding: utf-8 -*-
"""
Lia Vault - Registro de auditoría (H5).

Una línea JSON por evento, solo con metadatos: fecha, tipo de evento, SHA-256 y extensión del archivo,
conteo de entidades por tipo, estado y, si falló, el tipo de excepción. Nunca nombres de archivo, textos
ni mensajes de error, que pueden contener PII.

Cada línea lleva un HMAC-SHA256 encadenado con la anterior (clave derivada de la clave maestra de las llaves),
así que editar o borrar una línea rompe la cadena. Verificación: python3 auditoria.py verificar [ruta]

Ruta: <base>/Registros/lia_vault.log, o la de la variable LIA_VAULT_LOG (en Docker, /var/log/lia_vault.log).
Rota a los 5 MB y conserva 10 archivos, con permisos 0600.
"""

import datetime
import hashlib
import hmac
import json
import logging
import os
import re
import sys
import threading
from logging.handlers import RotatingFileHandler

VARIABLE_RUTA = "LIA_VAULT_LOG"
NOMBRE_ARCHIVO = "lia_vault.log"
TAMANO_MAXIMO = 5 * 1024 * 1024
ARCHIVOS_ROTADOS = 10
INICIO_CADENA = "0" * 64
CAMPOS = ("ts", "evento", "sha256", "ext", "bytes", "estado", "entidades", "error", "prev")
EVENTOS = ("seudonimizacion", "anonimizacion", "reversion")
ESTADOS = ("ok", "error", "rechazado")


class _ManejadorPrivado(RotatingFileHandler):
    """RotatingFileHandler que crea cada archivo con permisos 0600."""

    def _open(self):
        fd = os.open(self.baseFilename, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        return os.fdopen(fd, "a", encoding=self.encoding)


class RegistroAuditoria:
    def __init__(self, ruta, obtener_clave):
        self.ruta = ruta
        self._obtener_clave = obtener_clave
        self._clave = None
        self._lock = threading.Lock()
        self._logger = None
        self._ultimo_mac = None

    def _preparar(self):
        if self._logger:
            return
        clave = derivar_clave(self._obtener_clave())
        carpeta = os.path.dirname(self.ruta)
        os.makedirs(carpeta, exist_ok=True)
        try:
            os.chmod(carpeta, 0o700)
        except OSError:
            pass
        manejador = _ManejadorPrivado(self.ruta, maxBytes=TAMANO_MAXIMO, backupCount=ARCHIVOS_ROTADOS, encoding="utf-8")
        manejador.setFormatter(logging.Formatter("%(message)s"))
        logger = logging.getLogger(f"liavault.auditoria.{id(self)}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(manejador)
        self._clave = clave
        self._ultimo_mac = _ultimo_mac_en(self.ruta) or INICIO_CADENA
        self._logger = logger

    def registrar(self, evento, estado="ok", ruta_archivo=None, sha256=None, entidades=None, error=None):
        """Agrega un evento. Un fallo del registro se avisa por consola pero no detiene el procesamiento."""
        if evento not in EVENTOS or estado not in ESTADOS:
            raise ValueError("Evento o estado de auditoría desconocido.")
        entrada = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "evento": evento,
            "estado": estado,
        }
        if ruta_archivo:
            entrada["ext"] = os.path.splitext(ruta_archivo)[1].lower()[:10]
            if os.path.isfile(ruta_archivo):
                entrada["bytes"] = os.path.getsize(ruta_archivo)
                sha256 = sha256 or sha256_archivo(ruta_archivo)
        if sha256:
            entrada["sha256"] = sha256
        if entidades:
            entrada["entidades"] = {str(k)[:40]: int(v) for k, v in entidades.items()}
        if error is not None:
            entrada["error"] = (error if isinstance(error, str) else type(error).__name__)[:60]
        try:
            with self._lock:
                self._preparar()
                entrada["prev"] = self._ultimo_mac
                entrada["mac"] = firmar(self._clave, entrada)
                self._logger.info(json.dumps(entrada, ensure_ascii=False, sort_keys=True))
                self._ultimo_mac = entrada["mac"]
        except Exception as ex:
            print(f"⚠️ No se pudo escribir el registro de auditoría: {type(ex).__name__}", file=sys.stderr)


def derivar_clave(clave_maestra):
    return hmac.new(clave_maestra, b"liavault-registro-auditoria", hashlib.sha256).digest()


def _canonica(entrada):
    return json.dumps({k: entrada[k] for k in CAMPOS if k in entrada}, ensure_ascii=False, sort_keys=True).encode("utf-8")


def firmar(clave, entrada):
    return hmac.new(clave, _canonica(entrada), hashlib.sha256).hexdigest()


def sha256_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def contar_entidades(mapa):
    """Conteo por tipo a partir de los tokens de una llave ([PERSONA_1] → PERSONA). Nunca mira los valores."""
    conteo = {}
    for token in mapa or {}:
        m = re.match(r"\[(?:PAG\d+_)?([A-Z_]+?)_\d+\]$", token)
        tipo = m.group(1) if m else "OTRO"
        conteo[tipo] = conteo.get(tipo, 0) + 1
    return conteo


def _ultimo_mac_en(ruta):
    if not os.path.exists(ruta):
        return None
    ultima = None
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                ultima = linea
    if not ultima:
        return None
    try:
        return json.loads(ultima)["mac"]
    except (ValueError, KeyError):
        return None


def verificar(ruta, clave):
    """Comprueba firmas y encadenamiento desde el archivo rotado más antiguo. Retorna (ok, detalle)."""
    archivos = [f"{ruta}.{i}" for i in range(ARCHIVOS_ROTADOS, 0, -1) if os.path.exists(f"{ruta}.{i}")]
    if os.path.exists(ruta):
        archivos.append(ruta)
    if not archivos:
        return False, "No hay registro de auditoría."
    anterior = None
    total = 0
    for archivo in archivos:
        with open(archivo, "r", encoding="utf-8") as f:
            for n, linea in enumerate(f, 1):
                if not linea.strip():
                    continue
                donde = f"{os.path.basename(archivo)}, línea {n}"
                try:
                    entrada = json.loads(linea)
                except ValueError:
                    return False, f"Línea ilegible en {donde}."
                if not hmac.compare_digest(entrada.get("mac", ""), firmar(clave, entrada)):
                    return False, f"Firma inválida en {donde}: la línea fue modificada."
                if anterior is not None and entrada.get("prev") != anterior:
                    return False, f"Cadena rota en {donde}: falta o se reordenó una línea anterior."
                anterior = entrada["mac"]
                total += 1
    return True, f"Registro íntegro: {total} eventos en {len(archivos)} archivo(s)."


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "verificar":
        print("Uso: python3 auditoria.py verificar [ruta del registro]")
        sys.exit(2)
    import app_offline

    ruta_registro = sys.argv[2] if len(sys.argv) > 2 else app_offline.registro.ruta
    ok, detalle = verificar(ruta_registro, derivar_clave(app_offline.llaves.obtener_clave_maestra(app_offline.CARPETA_LLAVES)))
    print(("✅ " if ok else "❌ ") + detalle)
    sys.exit(0 if ok else 1)
