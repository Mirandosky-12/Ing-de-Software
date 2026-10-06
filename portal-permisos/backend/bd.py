"""
bd.py — Conexión a la base de datos.

    DATABASE_URL=sqlite:///./mupa.db                           desarrollo (por defecto)
    DATABASE_URL_FILE=/run/secrets/bd_url_app                  Docker: la URL con la
                                                               clave vive en un secreto
La API se conecta con el rol mupa_app, que sólo lee y escribe filas. Crear
tablas, triggers y permisos es trabajo de migrar.py, con el rol dueño.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

motor: Engine | None = None
SesionLocal = sessionmaker(expire_on_commit=False)


def url_desde_entorno() -> str:
    archivo = os.getenv("DATABASE_URL_FILE")
    if archivo:
        with open(archivo, encoding="utf-8") as f:
            return f.read().strip()
    return os.getenv("DATABASE_URL", "sqlite:///./mupa.db")


def configurar(url: str | None = None) -> Engine:
    """Crea el motor y lo conecta a SesionLocal. Las pruebas lo llaman con
    "sqlite://" para tener una base nueva en memoria en cada prueba."""
    global motor
    url = url or url_desde_entorno()
    if url.startswith("sqlite"):
        opciones: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            opciones["poolclass"] = StaticPool     # una sola conexión: la base vive en ella
        motor = create_engine(url, **opciones)
        event.listen(motor, "connect", _pragmas_sqlite)
    else:
        motor = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
    SesionLocal.configure(bind=motor)
    return motor


def _pragmas_sqlite(conexion, _registro) -> None:
    cursor = conexion.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")      # SQLite no las revisa si no se le pide
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()


def sesion() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición. No hace commit por su
    cuenta: cada ruta confirma lo suyo, incluso antes de responder un error
    que deba quedar en la bitácora (p. ej. un inicio de sesión fallido)."""
    with SesionLocal() as s:
        yield s
