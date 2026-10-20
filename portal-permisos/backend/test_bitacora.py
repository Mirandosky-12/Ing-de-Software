"""Pruebas de la bitácora encadenada (repositorio.registrar / verificar_bitacora)."""

from datetime import date

from sqlalchemy import select, text

import bd
import repositorio
from tablas import Bitacora


# ──────────────────────────── bitácora ────────────────────────────

def test_cada_entrada_encadena_el_hash_de_la_anterior():
    with bd.SesionLocal() as s:
        a = repositorio.registrar(s, "uno", "sistema")
        b = repositorio.registrar(s, "dos", "sistema", x=1)
        s.commit()
        assert (a.n, b.n) == (1, 2)
        assert a.previo == "0" * 64 and b.previo == a.hash


def test_la_cadena_sigue_integra_al_releerla_de_la_base():
    """Tildes, fechas y claves en desorden: el JSON canónico debe dar el
    mismo hash después de guardarse y volver a leerse."""
    with bd.SesionLocal() as s:
        repositorio.registrar(s, "cuenta.creada", "ñandú@correo.com",
                              organizacion="Fundación Año Nuevo", z=2, a=[1, 2],
                              cuando=date(2026, 10, 18))
        s.commit()
    with bd.SesionLocal() as s:
        assert repositorio.verificar_bitacora(s) == {"integra": True, "entradas": 1}


def _tres_entradas():
    with bd.SesionLocal() as s:
        for accion in ("uno", "dos", "tres"):
            repositorio.registrar(s, accion, "sistema")
        s.commit()


def test_se_detecta_una_fila_alterada():
    _tres_entradas()
    with bd.motor.begin() as c:                  # sólo un administrador podría hacer esto
        c.execute(text("DROP TRIGGER bitacora_sin_update"))
        c.execute(text("UPDATE bitacora SET actor = 'intruso' WHERE n = 2"))
    with bd.SesionLocal() as s:
        assert repositorio.verificar_bitacora(s) == {"integra": False, "rota_en": 2}


def test_se_detecta_una_fila_borrada():
    _tres_entradas()
    with bd.motor.begin() as c:
        c.execute(text("DROP TRIGGER bitacora_sin_delete"))
        c.execute(text("DELETE FROM bitacora WHERE n = 2"))
    with bd.SesionLocal() as s:
        assert repositorio.verificar_bitacora(s) == {"integra": False, "rota_en": 3}


def test_no_hay_filas_de_bitacora_si_nadie_hizo_commit():
    with bd.SesionLocal() as s:
        repositorio.registrar(s, "sin.confirmar", "sistema")
        s.rollback()
        assert s.scalars(select(Bitacora)).first() is None


def test_total_bitacora_cuenta_las_entradas():
    _tres_entradas()
    with bd.SesionLocal() as s:
        assert repositorio.total_bitacora(s) == 3
