"""
generar_secretos.py — Crea las claves que usa docker-compose.yml.

    python generar_secretos.py

Escribe un archivo por secreto en monitoreo/secretos/ (que git ignora).
Nunca sobrescribe: si se pierde clave_cifrado.txt, las cédulas guardadas
ya no se pueden leer, y si cambian las claves de la base, los roles creados
en el volumen dejan de coincidir.
"""

import base64
import os
import secrets
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "secretos"


def main() -> int:
    dueno, app = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    valores = {
        "bd_superusuario_password.txt": secrets.token_urlsafe(24),
        "bd_owner_password.txt": dueno,
        "bd_app_password.txt": app,
        "bd_url_owner.txt": f"postgresql+psycopg://mupa_owner:{dueno}@bd:5432/mupa",
        "bd_url_app.txt": f"postgresql+psycopg://mupa_app:{app}@bd:5432/mupa",
        # Misma forma que Fernet.generate_key(), sin necesitar cryptography aquí.
        "clave_cifrado.txt": base64.urlsafe_b64encode(os.urandom(32)).decode(),
    }
    existentes = [n for n in valores if (CARPETA / n).exists()]
    if existentes:
        print(f"Ya existen {', '.join(existentes)} en {CARPETA}. No se sobrescribe nada.")
        return 1
    CARPETA.mkdir(mode=0o700, exist_ok=True)
    for nombre, valor in valores.items():
        (CARPETA / nombre).write_text(valor, encoding="utf-8")
    print(f"Secretos creados en {CARPETA}. Respáldalos fuera del repositorio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
