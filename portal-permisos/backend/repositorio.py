"""
repositorio.py — Todo el acceso a datos de la API.

main.py no escribe SQL ni toca tablas: llama a estas funciones. Ninguna hace
commit; lo decide la ruta que las llama, para que una operación y su entrada
en la bitácora se confirmen juntas.
"""


from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from tablas import Bitacora

MUNICIPIO = os.getenv("MUNICIPIO", "panama")
_CERO = "0" * 64


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ bitácora

def _canonico(valor) -> str:
    """JSON con claves ordenadas y sin espacios: el mismo dato produce siempre
    el mismo texto, se lea de SQLite, de PostgreSQL o de un respaldo."""
    return json.dumps(valor, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)


def _huella(n: int, ts: str, municipio: str, accion: str, actor: str,
            datos: str, previo: str) -> str:
    cuerpo = _canonico({"n": n, "ts": ts, "municipio": municipio, "accion": accion,
                        "actor": actor, "datos": datos, "previo": previo})
    return hashlib.sha256(cuerpo.encode()).hexdigest()


def registrar(s: Session, accion: str, actor: str, **datos) -> Bitacora:
    if s.get_bind().dialect.name == "postgresql":
        # Dos peticiones a la vez no pueden leer el mismo "último hash":
        # este candado dura hasta el commit de la transacción.
        s.execute(text("SELECT pg_advisory_xact_lock(4183)"))
    ultima = s.scalars(select(Bitacora).order_by(Bitacora.n.desc()).limit(1)).first()
    n = ultima.n + 1 if ultima else 1
    previo = ultima.hash if ultima else _CERO
    ts = _ahora().isoformat(timespec="seconds")
    datos_json = _canonico(datos)
    entrada = Bitacora(
        n=n, ts=ts, municipio=MUNICIPIO, accion=accion, actor=actor, datos=datos_json,
        previo=previo, hash=_huella(n, ts, MUNICIPIO, accion, actor, datos_json, previo),
    )
    s.add(entrada)
    s.flush()
    return entrada


def verificar_bitacora(s: Session) -> dict:
    """Recorre la cadena y reporta la primera fila alterada o faltante."""
    previo, total = _CERO, 0
    for e in s.scalars(select(Bitacora).order_by(Bitacora.n)):
        esperado = _huella(e.n, e.ts, e.municipio, e.accion, e.actor, e.datos, e.previo)
        if e.n != total + 1 or e.previo != previo or esperado != e.hash:
            return {"integra": False, "rota_en": e.n}
        previo, total = e.hash, total + 1
    return {"integra": True, "entradas": total}


def total_bitacora(s: Session) -> int:
    return s.scalar(select(func.count()).select_from(Bitacora))
