"""
migrar.py — Crea el esquema, lo blinda y carga el catálogo.

    python migrar.py

Corre con el rol DUEÑO (mupa_owner): en Docker lo hace el servicio
`migraciones` antes de que arranque la API. La API usa el rol mupa_app, que
no puede crear ni borrar tablas, ni modificar la bitácora.

En desarrollo con SQLite, main.py llama a preparar() al arrancar.
Es idempotente: se puede correr las veces que haga falta.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import bd
import catalogo
import seguridad
from tablas import ROLES, Base, Cuenta, Permiso

SOLO_ANEXAR = ("bitacora", "historial")
ROL_APP = "mupa_app"

TRIGGERS_SQLITE = [
    f"CREATE TRIGGER IF NOT EXISTS {tabla}_sin_{op} BEFORE {op.upper()} ON {tabla} "
    f"BEGIN SELECT RAISE(ABORT, '{tabla} es de solo anexado'); END"
    for tabla in SOLO_ANEXAR for op in ("update", "delete")
]

# Sin el signo de porcentaje a propósito: el controlador de PostgreSQL lo
# interpretaría como un parámetro.
TRIGGERS_POSTGRES = [
    """CREATE OR REPLACE FUNCTION solo_anexar() RETURNS trigger LANGUAGE plpgsql AS $$
       BEGIN
         RAISE EXCEPTION USING MESSAGE = TG_TABLE_NAME || ' es de solo anexado';
       END $$""",
    *[f"CREATE OR REPLACE TRIGGER {t}_solo_anexar BEFORE UPDATE OR DELETE ON {t} "
      f"FOR EACH ROW EXECUTE FUNCTION solo_anexar()" for t in SOLO_ANEXAR],
    *[f"CREATE OR REPLACE TRIGGER {t}_sin_truncate BEFORE TRUNCATE ON {t} "
      f"FOR EACH STATEMENT EXECUTE FUNCTION solo_anexar()" for t in SOLO_ANEXAR],
]

# Mínimo privilegio: cada tabla recibe sólo lo que la API usa. Nadie borra
# cuentas, expedientes ni documentos; sólo las sesiones se eliminan.
PERMISOS_APP = [
    f"GRANT SELECT ON permisos TO {ROL_APP}",
    f"GRANT SELECT, INSERT, UPDATE ON cuentas, expedientes, documentos, citas TO {ROL_APP}",
    f"GRANT SELECT, INSERT, DELETE ON sesiones TO {ROL_APP}",
    f"GRANT SELECT, INSERT ON bitacora, historial TO {ROL_APP}",
    f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA mupa TO {ROL_APP}",
]


def crear_esquema(motor: Engine) -> None:
    Base.metadata.create_all(motor)
    sentencias = TRIGGERS_POSTGRES if motor.dialect.name == "postgresql" else TRIGGERS_SQLITE
    with motor.begin() as c:
        for sql in sentencias:
            c.exec_driver_sql(sql)


def otorgar_permisos(motor: Engine) -> None:
    with motor.begin() as c:
        for sql in PERMISOS_APP:
            c.exec_driver_sql(sql)


def sembrar_catalogo(motor: Engine) -> None:
    with Session(motor) as s:
        for id_, nombre, categoria, dias, aforo, requisitos in catalogo.PERMISOS:
            s.merge(Permiso(
                id=id_, nombre=nombre, categoria=categoria, dias=dias,
                aforo_min=aforo[0] if aforo else None,
                aforo_max=aforo[1] if aforo else None,
                requisitos=requisitos,
            ))
        s.commit()


# Cuentas de demostración. Se siembran SÓLO en SQLite, es decir en el entorno
# de desarrollo: hacen falta para poder entrar al portal y a la bandeja sin
# tener que crear nada a mano. En PostgreSQL no se crea ninguna cuenta; ahí el
# funcionario se promueve con `python migrar.py --rol revisor correo@…`.
CUENTAS_DEMO = [
    ("demo@mupa.gob.pa",    "demo1234",    "ciudadano", "Diego", "López",
     22, "Universidad Tecnológica de Panamá"),
    ("revisor@mupa.gob.pa", "revisor1234", "revisor",   "Ana",   "Pérez",
     34, "Dirección de Permisos y Cumplimiento"),
]


def sembrar_cuentas_demo(motor: Engine) -> None:
    ahora = datetime.now(timezone.utc)
    with Session(motor) as s:
        for correo, clave, rol, nombre, apellido, edad, organizacion in CUENTAS_DEMO:
            if s.scalars(select(Cuenta).where(Cuenta.email == correo)).first():
                continue                       # ya existe: no se toca su clave
            s.add(Cuenta(email=correo, nombre=nombre, apellido=apellido, edad=edad,
                         organizacion=organizacion, cedula=None,
                         clave=seguridad.cifrar_clave(clave), rol=rol,
                         consentimiento_en=ahora, creado_en=ahora))
        s.commit()


def asignar_rol(motor: Engine, correo: str, rol: str) -> None:
    """Promueve una cuenta existente. Es la vía para crear funcionarios en
    producción: nadie se registra como revisor desde el portal."""
    if rol not in ROLES:
        raise SystemExit(f"Rol desconocido: {rol}. Son {', '.join(ROLES)}.")
    with Session(motor) as s:
        cuenta = s.scalars(select(Cuenta).where(Cuenta.email == correo.lower())).first()
        if not cuenta:
            raise SystemExit(f"No existe ninguna cuenta con el correo {correo}.")
        cuenta.rol = rol
        s.commit()
        print(f"{correo} ahora es {rol}.")


def preparar(motor: Engine) -> None:
    crear_esquema(motor)
    sembrar_catalogo(motor)
    if motor.dialect.name == "postgresql":
        otorgar_permisos(motor)
    else:
        sembrar_cuentas_demo(motor)


if __name__ == "__main__":
    m = bd.configurar()
    if len(sys.argv) == 4 and sys.argv[1] == "--rol":
        asignar_rol(m, correo=sys.argv[3], rol=sys.argv[2])
    else:
        preparar(m)
        print(f"Esquema listo en {m.url.render_as_string(hide_password=True)}")
