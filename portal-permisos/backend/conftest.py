"""
conftest.py — Preparación común de las pruebas.

Cada prueba recibe una base SQLite nueva en memoria, con el esquema, los
triggers y el catálogo, y un almacén de PDF en una carpeta temporal.
"""

import os

# Antes de importar la aplicación: pocas iteraciones para que las pruebas
# vayan rápido y una clave de cifrado desechable.
os.environ.setdefault("PBKDF2_ITER", "1000")
from cryptography.fernet import Fernet  # noqa: E402

os.environ.setdefault("CLAVE_CIFRADO", Fernet.generate_key().decode())

import pytest  # noqa: E402

import bd  # noqa: E402
import migrar  # noqa: E402


@pytest.fixture(autouse=True)
def bd_limpia(tmp_path, monkeypatch):
    monkeypatch.setenv("ALMACEN_DIR", str(tmp_path / "almacen"))
    motor = bd.configurar("sqlite://")
    migrar.preparar(motor)
    yield motor
    motor.dispose()
