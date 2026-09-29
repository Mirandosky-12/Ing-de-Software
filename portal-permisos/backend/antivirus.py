"""
antivirus.py — Integración con ClamAV.

ClamAV corre como un demonio (clamd) al que se le entrega el archivo por socket
TCP usando el comando INSTREAM. El archivo NUNCA se guarda en disco antes de
escanearlo: viaja en memoria, se escanea y sólo si sale limpio se persiste.

Puesta en marcha (ver monitoreo/docker-compose.yml):
    docker compose up -d clamav
    # la base de firmas se actualiza sola con freshclam dentro del contenedor
"""

from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass
from enum import Enum

import clamd

CLAMAV_HOST = os.getenv("CLAMAV_HOST", "127.0.0.1")
CLAMAV_PORT = int(os.getenv("CLAMAV_PORT", "3310"))
CLAMAV_TIMEOUT = float(os.getenv("CLAMAV_TIMEOUT", "30"))

# Límites del expediente municipal
MAX_BYTES = 10 * 1024 * 1024          # 10 MB
FIRMA_PDF = b"%PDF-"                   # bytes mágicos de un PDF real


class Resultado(str, Enum):
    LIMPIO = "limpio"
    INFECTADO = "infectado"
    FORMATO_INVALIDO = "formato_invalido"
    DEMASIADO_GRANDE = "demasiado_grande"
    VACIO = "vacio"
    ANTIVIRUS_CAIDO = "antivirus_caido"


@dataclass
class Veredicto:
    """Lo que la cadena de verificación concluye sobre un archivo."""
    resultado: Resultado
    mensaje: str
    sha256: str | None = None
    firma_virus: str | None = None
    bytes_: int = 0

    @property
    def aceptado(self) -> bool:
        return self.resultado is Resultado.LIMPIO


def _cliente() -> clamd.ClamdNetworkSocket:
    return clamd.ClamdNetworkSocket(
        host=CLAMAV_HOST, port=CLAMAV_PORT, timeout=CLAMAV_TIMEOUT
    )


def ping() -> bool:
    """¿Está vivo el demonio? Se usa en /salud y en la métrica de Grafana."""
    try:
        return _cliente().ping() == "PONG"
    except Exception:
        return False


def version_firmas() -> str:
    """Versión de la base de firmas. Si se queda vieja, Grafana debe avisar."""
    try:
        return _cliente().version()
    except Exception:
        return "desconocida"


def verificar(contenido: bytes, nombre: str) -> Veredicto:
    """
    Cadena de verificación documental. El orden importa: primero lo barato
    (tamaño, formato) y al final lo caro (antivirus, hash). Así un archivo
    basura no consume tiempo de CPU del escáner.

        1. No está vacío
        2. Cabe en el límite
        3. Es un PDF de verdad (extensión + bytes mágicos, no sólo el MIME
           que manda el navegador, que es falsificable)
        4. ClamAV no encuentra amenazas
        5. Se calcula la huella SHA-256 que identifica al documento
    """
    # 1 · vacío
    if not contenido:
        return Veredicto(Resultado.VACIO, "El archivo está vacío.")

    # 2 · tamaño
    if len(contenido) > MAX_BYTES:
        mb = len(contenido) / 1_048_576
        return Veredicto(
            Resultado.DEMASIADO_GRANDE,
            f"El archivo pesa {mb:.1f} MB y el límite es 10 MB.",
            bytes_=len(contenido),
        )

    # 3 · formato real
    if not nombre.lower().endswith(".pdf") or not contenido.startswith(FIRMA_PDF):
        return Veredicto(
            Resultado.FORMATO_INVALIDO,
            "El archivo no es un PDF válido. Sube un documento con extensión .pdf.",
            bytes_=len(contenido),
        )

    # 4 · antivirus
    try:
        respuesta = _cliente().instream(io.BytesIO(contenido))
    except Exception as exc:  # clamd caído, timeout, red
        # Decisión de diseño: si el antivirus no responde, NO se acepta el
        # documento. Un expediente sin escanear es peor que un trámite lento.
        return Veredicto(
            Resultado.ANTIVIRUS_CAIDO,
            f"El servicio de verificación no está disponible ({exc}). "
            "Intenta de nuevo en unos minutos.",
            bytes_=len(contenido),
        )

    estado, firma = respuesta["stream"]          # ('OK', None) | ('FOUND', 'Eicar-Test-Signature')
    if estado == "FOUND":
        return Veredicto(
            Resultado.INFECTADO,
            f"Se detectó una amenaza en el archivo ({firma}). "
            "El documento fue puesto en cuarentena y no se adjuntó al expediente.",
            firma_virus=firma,
            bytes_=len(contenido),
        )

    # 5 · huella de integridad
    huella = hashlib.sha256(contenido).hexdigest()
    return Veredicto(
        Resultado.LIMPIO,
        "Documento verificado.",
        sha256=huella,
        bytes_=len(contenido),
    )
