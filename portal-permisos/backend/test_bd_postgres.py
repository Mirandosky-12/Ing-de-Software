"""
Pruebas contra PostgreSQL real: lo que el rol de la API NO puede hacer, los
triggers que protegen la auditoría y la bitácora con escrituras simultáneas.

    cd monitoreo
    docker compose --profile pruebas up -d bd-pruebas
    cd ../backend
    PRUEBAS_PG=1 pytest -m postgres -v            # PowerShell: $env:PRUEBAS_PG=1; pytest -m postgres -v

La base de pruebas vive en memoria (tmpfs): al detenerla se borra todo.
"""

import os
import secrets
import threading

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

import migrar
import repositorio

DUENO = os.getenv("PRUEBAS_PG_DUENO",
                  "postgresql+psycopg://mupa_owner:pruebas-dueno@127.0.0.1:55432/mupa")
APP = os.getenv("PRUEBAS_PG_APP",
                "postgresql+psycopg://mupa_app:pruebas-app@127.0.0.1:55432/mupa")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(not os.getenv("PRUEBAS_PG"),
                       reason="define PRUEBAS_PG=1 y levanta bd-pruebas"),
]


@pytest.fixture(scope="module")
def dueno():
    motor = create_engine(DUENO)
    migrar.preparar(motor)
    yield motor
    motor.dispose()


@pytest.fixture(scope="module")
def app(dueno):
    motor = create_engine(APP)
    yield motor
    motor.dispose()


def test_la_api_no_es_superusuario_y_tiene_limite_de_tiempo(app):
    with app.connect() as c:
        assert c.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")).scalar() is False
        assert c.execute(text("SHOW statement_timeout")).scalar() == "5s"
        assert c.execute(text("SHOW search_path")).scalar() == "mupa"


def test_la_api_puede_escribir_en_la_bitacora(app):
    with Session(app) as s:
        repositorio.registrar(s, "prueba.postgres", "sistema")
        s.commit()


@pytest.mark.parametrize("sql", [
    "UPDATE bitacora SET actor = 'intruso'",
    "DELETE FROM bitacora",
    "UPDATE historial SET comentario = 'cambiado'",
    "DELETE FROM cuentas",
    "DELETE FROM expedientes",
    "DELETE FROM documentos",
    "UPDATE permisos SET dias = 1",
    "TRUNCATE sesiones",
    "DROP TABLE bitacora",
    "CREATE TABLE intrusa (x int)",
])
def test_la_api_no_tiene_permiso(app, sql):
    with app.connect() as c, pytest.raises(DBAPIError, match="permission denied|must be owner"):
        c.execute(text(sql))


@pytest.mark.parametrize("sql", [
    "UPDATE bitacora SET actor = 'intruso'",
    "DELETE FROM bitacora",
    "TRUNCATE bitacora",
    "TRUNCATE historial",
])
def test_ni_el_dueno_puede_reescribir_la_auditoria(dueno, sql):
    with Session(dueno) as s:
        repositorio.registrar(s, "prueba.dueno", "sistema")        # que haya al menos una fila
        s.commit()
    with dueno.connect() as c, pytest.raises(DBAPIError, match="solo anexado"):
        c.execute(text(sql))


def test_la_cadena_no_se_bifurca_con_escrituras_simultaneas(app):
    errores = []

    def escribir(i):
        try:
            with Session(app) as s:
                repositorio.registrar(s, "concurrente", f"hilo-{i}")
                s.commit()
        except Exception as exc:                                    # noqa: BLE001
            errores.append(exc)

    hilos = [threading.Thread(target=escribir, args=(i,)) for i in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert errores == []
    with Session(app) as s:
        assert repositorio.verificar_bitacora(s)["integra"] is True


def test_dos_registros_simultaneos_con_el_mismo_correo(app):
    """Los dos pasan la revisión previa; la restricción única decide y el
    segundo recibe Duplicado (un 409 en la API), no un error 500."""
    correo = f"carrera-{secrets.token_hex(4)}@correo.com"
    resultados = []
    barrera = threading.Barrier(2)

    def registrar_cuenta():
        with Session(app) as s:
            barrera.wait()
            try:
                repositorio.crear_cuenta(s, nombre="Ana", apellido="Pérez", edad=30,
                                         organizacion="X", email=correo, cedula=None,
                                         password="clave-de-prueba")
                s.commit()
                resultados.append("creada")
            except repositorio.Duplicado:
                resultados.append("duplicado")

    hilos = [threading.Thread(target=registrar_cuenta) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(resultados) == ["creada", "duplicado"]
