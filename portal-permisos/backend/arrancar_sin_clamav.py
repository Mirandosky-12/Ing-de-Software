"""
arrancar_sin_clamav.py — Levanta la API sin necesidad de ClamAV.

    py arrancar_sin_clamav.py

Para qué sirve: ClamAV corre dentro de Docker. Cuando se trabaja sin Docker,
la API intenta hablar con él, no lo encuentra, y se queda esperando — lo que
deja al portal sin respuesta y rechaza todos los documentos con un 503.

Este arranque sustituye SÓLO el escaneo antivirus por una comprobación
equivalente que corre en el momento: acepta los PDF válidos y rechaza los que
llevan la firma de prueba EICAR. Todo lo demás —base de datos, bitácora
encadenada, hashes SHA-256, sesiones, roles— es el código real del proyecto.

    Lo que es real      todo menos el escaneo
    Lo que se simula    el veredicto de ClamAV

Con Docker (./levantar.sh) no hace falta: ahí ClamAV es de verdad y se usa
`uvicorn main:app` como siempre.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import sys

AQUI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

# --------------------------------------------------------------- 1. la clave
# La cédula se guarda cifrada. La clave se crea una vez y se reutiliza, para
# que los datos de ayer se sigan leyendo hoy.
ARCHIVO_CLAVE = AQUI / "clave_cifrado.txt"
if not os.getenv("CLAVE_CIFRADO"):
    if not ARCHIVO_CLAVE.exists():
        from cryptography.fernet import Fernet
        ARCHIVO_CLAVE.write_text(Fernet.generate_key().decode(), encoding="utf-8")
        print(f"Clave de cifrado creada en {ARCHIVO_CLAVE.name}")
    os.environ["CLAVE_CIFRADO"] = ARCHIVO_CLAVE.read_text(encoding="utf-8").strip()

# ------------------------------------------------- 2. orígenes que se aceptan
# localhost y 127.0.0.1 son orígenes distintos para el navegador. Se permiten
# los dos para que el portal conecte se abra como se abra.
os.environ.setdefault("CORS_ORIGENES", ",".join([
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:3000", "http://127.0.0.1:3000",
]))

# ------------------------------------------------------- 3. el escáner de pie
import antivirus

MAX_BYTES = 10 * 1024 * 1024


def _ping() -> bool:
    return True


def _version_firmas() -> str:
    return "sin ClamAV (modo local)"


def _verificar(contenido: bytes, nombre: str) -> "antivirus.Veredicto":
    """La misma cadena de verificación, con el paso 3 resuelto aquí mismo."""
    V, R = antivirus.Veredicto, antivirus.Resultado

    if not contenido:
        return V(R.VACIO, "El archivo está vacío.")
    if not nombre.lower().endswith(".pdf") or not contenido.startswith(b"%PDF-"):
        return V(R.FORMATO_INVALIDO,
                 "El archivo no es un PDF válido. Sube un documento con extensión .pdf.")
    if len(contenido) > MAX_BYTES:
        return V(R.DEMASIADO_GRANDE, "El archivo supera los 10 MB.")
    if b"EICAR" in contenido or "eicar" in nombre.lower():
        return V(R.INFECTADO,
                 "Se detectó una amenaza en el archivo (Eicar-Test-Signature). "
                 "El documento fue puesto en cuarentena y no se adjuntó al expediente.",
                 firma_virus="Eicar-Test-Signature", bytes_=len(contenido))

    return V(R.LIMPIO, "Documento verificado y sellado.",
             sha256=hashlib.sha256(contenido).hexdigest(), bytes_=len(contenido))


antivirus.ping = _ping
antivirus.version_firmas = _version_firmas
antivirus.verificar = _verificar

# ------------------------------------------------------------- 4. a levantar
import uvicorn
from main import app

if __name__ == "__main__":
    print()
    print("  Ventanilla Única Municipal · API sin ClamAV")
    print("  " + "-" * 44)
    print("  API ........ http://127.0.0.1:8000")
    print("  Documentos . http://127.0.0.1:8000/docs")
    print("  Portal ..... http://localhost:5173")
    print()
    print("  El escaneo antivirus se resuelve en el proceso; todo lo demás")
    print("  (base de datos, bitácora, hashes) es el código real.")
    print()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
