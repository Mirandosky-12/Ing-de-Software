"""
ver_bd.py — Mirar la base de datos sin tocarla.

Usa la misma conexión que la API (bd.configurar), así que sirve igual para
SQLite en desarrollo y para PostgreSQL en Docker: lo que cambie DATABASE_URL.
Sólo lee; no hay un solo INSERT ni UPDATE en este archivo.

    python ver_bd.py                       resumen: cuántas filas hay en cada tabla
    python ver_bd.py cuentas               las filas de una tabla (20 por defecto)
    python ver_bd.py expedientes -n 5      las primeras 5
    python ver_bd.py --bitacora            la cadena de auditoría y si está íntegra
    python ver_bd.py --expediente EXP-2026-004183     un expediente con su historial
"""

from __future__ import annotations

import argparse

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

import bd
import repositorio
from tablas import Cuenta, Expediente

TABLAS = ("cuentas", "sesiones", "permisos", "documentos",
          "expedientes", "historial", "citas", "bitacora")
# La cédula se guarda cifrada (Ley 81) y la clave es un hash: no se imprimen.
OCULTAS = {"clave", "cedula", "token_hash"}


def _tabla(filas: list[dict], titulo: str) -> None:
    print(f"\n── {titulo} " + "─" * max(0, 60 - len(titulo)))
    if not filas:
        print("   (vacía)")
        return
    columnas = list(filas[0])
    texto = lambda v: "—" if v is None else str(v)
    ancho = {c: min(38, max(len(c), *(len(texto(f[c])) for f in filas))) for c in columnas}
    corta = lambda v, a: (s := "—" if v is None else str(v))[:a - 1] + "…" if len(
        s := "—" if v is None else str(v)) > a else s
    print("   " + "  ".join(c.ljust(ancho[c]) for c in columnas))
    print("   " + "  ".join("-" * ancho[c] for c in columnas))
    for f in filas:
        print("   " + "  ".join(corta(f[c], ancho[c]).ljust(ancho[c]) for c in columnas))


def resumen(s: Session) -> None:
    existentes = set(inspect(s.get_bind()).get_table_names())
    print("\nFilas por tabla")
    for t in TABLAS:
        if t not in existentes:
            print(f"   {t:<14} (no existe todavía)")
            continue
        n = s.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()
        print(f"   {t:<14} {n:>6}")
    print("\n   Las claves están con PBKDF2 y la cédula cifrada con Fernet:")
    print("   ver_bd.py no las imprime ni aunque se las pidas.")


def volcar(s: Session, tabla: str, n: int) -> None:
    if tabla not in TABLAS:
        raise SystemExit(f"No conozco la tabla «{tabla}». Son: {', '.join(TABLAS)}.")
    filas = s.execute(text(f"SELECT * FROM {tabla} LIMIT :n"), {"n": n}).mappings().all()
    visibles = [{k: v for k, v in f.items() if k not in OCULTAS} for f in filas]
    _tabla(visibles, f"{tabla} (primeras {n})")


def bitacora(s: Session, n: int) -> None:
    filas = s.execute(text(
        "SELECT n, ts, accion, actor, substr(hash,1,12) AS hash, substr(previo,1,12) AS previo "
        "FROM bitacora ORDER BY n DESC LIMIT :n"), {"n": n}).mappings().all()
    _tabla(list(reversed(filas)), f"bitácora (últimas {n})")
    estado = repositorio.verificar_bitacora(s)
    print("\n   Integridad de la cadena:",
          "íntegra ✓" if estado.get("integra") else f"ROTA ✗ {estado}")


def expediente(s: Session, codigo: str) -> None:
    e = s.scalars(select(Expediente).where(Expediente.codigo == codigo)).first()
    if not e:
        raise SystemExit(f"No hay ningún expediente con el código {codigo}.")
    d = repositorio.expediente_a_dict(e)
    print(f"\n── {d['codigo']} " + "─" * max(0, 60 - len(d['codigo'])))
    for k, v in d.items():
        print(f"   {k:<18} {v}")
    _tabla(repositorio.historial_a_dicts(s, e), "historial")


def main() -> None:
    p = argparse.ArgumentParser(description="Mirar la base de datos de la Ventanilla Única.")
    p.add_argument("tabla", nargs="?", help=f"una de: {', '.join(TABLAS)}")
    p.add_argument("-n", type=int, default=20, help="cuántas filas (20)")
    p.add_argument("--bitacora", action="store_true", help="la cadena de auditoría")
    p.add_argument("--expediente", metavar="CÓDIGO", help="un expediente con su historial")
    a = p.parse_args()

    motor = bd.configurar()
    print(f"Base: {motor.url.render_as_string(hide_password=True)}")
    with Session(motor) as s:
        if a.expediente:
            expediente(s, a.expediente)
        elif a.bitacora:
            bitacora(s, a.n)
        elif a.tabla:
            volcar(s, a.tabla, a.n)
        else:
            resumen(s)
    print()


if __name__ == "__main__":
    main()
