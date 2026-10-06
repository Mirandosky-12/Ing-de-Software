"""
almacen.py — Dónde viven los PDF verificados.

Cada archivo se guarda con el nombre de su huella SHA-256, repartido en
subcarpetas por sus dos primeros caracteres (ab/abcdef….pdf). El mismo PDF
subido dos veces ocupa un solo lugar, y el usuario nunca elige la ruta: el
nombre que manda el navegador no se usa para nada en el disco.

Sólo se llama DESPUÉS de que ClamAV dio el veredicto limpio.
"""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

_HEX64 = re.compile(r"[0-9a-f]{64}")


def raiz() -> Path:
    return Path(os.getenv("ALMACEN_DIR", "./almacen"))


def guardar(sha256: str, contenido: bytes) -> str:
    """Guarda el PDF y devuelve su ruta relativa al almacén."""
    if not _HEX64.fullmatch(sha256):
        raise ValueError("Huella SHA-256 inválida")
    relativa = Path(sha256[:2]) / f"{sha256}.pdf"
    destino = raiz() / relativa
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        # Escribe a un temporal y renombra: nunca queda un PDF a medias.
        temporal = destino.with_name(f"{sha256}.{secrets.token_hex(4)}.tmp")
        temporal.write_bytes(contenido)
        temporal.replace(destino)
    return relativa.as_posix()


def leer(ruta: str) -> bytes:
    return (raiz() / ruta).read_bytes()
