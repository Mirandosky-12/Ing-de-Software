"""
seguridad.py — Lo que protege los datos si alguien se lleva una copia de la base.

  · Contraseñas: PBKDF2-SHA256, sal propia por cuenta, 600 000 iteraciones
    (recomendación OWASP). El formato guarda las iteraciones, así se pueden
    subir más adelante sin invalidar las claves existentes.
  · Tokens de sesión: la base guarda su SHA-256, nunca el token. Una copia de
    la tabla de sesiones no sirve para entrar.
  · Cédula: cifrada con Fernet (AES + HMAC). La clave vive FUERA de la base,
    en CLAVE_CIFRADO o en el archivo que indique CLAVE_CIFRADO_FILE.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from functools import lru_cache

from cryptography.fernet import Fernet
from sqlalchemy.types import String, TypeDecorator

ITERACIONES = int(os.getenv("PBKDF2_ITER", "600000"))


# ------------------------------------------------------------------ contraseñas

def cifrar_clave(password: str) -> str:
    sal = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), sal.encode(), ITERACIONES).hex()
    return f"pbkdf2_sha256${ITERACIONES}${sal}${h}"


def verificar_clave(password: str, guardada: str) -> bool:
    try:
        algoritmo, iteraciones, sal, h = guardada.split("$")
        iteraciones = int(iteraciones)
    except ValueError:
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    calculada = hashlib.pbkdf2_hmac("sha256", password.encode(), sal.encode(), iteraciones).hex()
    return hmac.compare_digest(calculada, h)


# Se verifica contra esta clave cuando el correo no existe, para que la
# respuesta tarde lo mismo y no delate qué correos están registrados.
CLAVE_FALSA = cifrar_clave(secrets.token_urlsafe(16))


# ------------------------------------------------------------------ sesiones

def huella_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def nuevo_token() -> tuple[str, str]:
    """Devuelve (token para el navegador, huella para la base)."""
    token = secrets.token_urlsafe(32)
    return token, huella_token(token)


# ------------------------------------------------------------------ cifrado de columnas

@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    archivo = os.getenv("CLAVE_CIFRADO_FILE")
    if archivo:
        with open(archivo, encoding="utf-8") as f:
            clave = f.read().strip()
    else:
        clave = os.getenv("CLAVE_CIFRADO", "")
    if not clave:
        raise RuntimeError(
            "Falta CLAVE_CIFRADO (o CLAVE_CIFRADO_FILE). Genera una con:\n"
            '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(clave.encode())


def comprobar_clave() -> None:
    """Se llama al arrancar: mejor no levantar que guardar datos sin cifrar."""
    _fernet()


class Cifrado(TypeDecorator):
    """Columna de texto que se cifra al escribir y se descifra al leer."""

    impl = String(500)
    cache_ok = True

    def process_bind_param(self, valor, dialect):
        return None if valor is None else _fernet().encrypt(valor.encode()).decode()

    def process_result_value(self, valor, dialect):
        return None if valor is None else _fernet().decrypt(valor.encode()).decode()
