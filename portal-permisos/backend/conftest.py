"""
conftest.py — Preparación común de las pruebas.

Por ahora sólo fija el entorno; la Tarea 3 agrega la base de datos de prueba.
"""

import os

# Antes de importar la aplicación: pocas iteraciones para que las pruebas
# vayan rápido y una clave de cifrado desechable.
os.environ.setdefault("PBKDF2_ITER", "1000")
from cryptography.fernet import Fernet  # noqa: E402

os.environ.setdefault("CLAVE_CIFRADO", Fernet.generate_key().decode())
