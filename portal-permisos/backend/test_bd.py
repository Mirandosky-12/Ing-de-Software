"""Pruebas del esquema: tablas, restricciones, triggers y catálogo (SQLite)."""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import DBAPIError

import bd
import catalogo
import migrar
from tablas import Bitacora, Cuenta, Documento, Expediente, Historial, Permiso, Sesion

AHORA = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)


def _cuenta(email="ana@correo.com") -> Cuenta:
    return Cuenta(email=email, nombre="Ana", apellido="Pérez", edad=30, organizacion="X",
                  cedula=None, clave="pbkdf2_sha256$1$s$h", rol="ciudadano",
                  consentimiento_en=AHORA, creado_en=AHORA)


def _filas_de_prueba() -> None:
    """Una cuenta con documento y expediente: deja una fila en historial y otra en bitácora."""
    with bd.SesionLocal() as s:
        cuenta = _cuenta()
        s.add(cuenta)
        s.flush()
        doc = Documento(propietario_id=cuenta.id, sha256="e" * 64, nombre="a.pdf",
                        tamano=100, ruta="ee/e.pdf", sellado_en=AHORA)
        s.add(doc)
        s.flush()
        exp = Expediente(
            codigo="EXP-2026-004183", municipio="panama", permiso_id="ACERA",
            solicitante_id=cuenta.id, documento_id=doc.id, estado="Recibido",
            etapa="En cola", corregimiento="Santa Ana", tipo_acto="Otro",
            lugar="Ave. Central", fecha_acto=date(2026, 11, 2), hora_inicio="08:00",
            hora_fin="12:00", aforo=10, responsable="Ana", telefono="60000000",
            motivo="Uso temporal de la acera.", plazo_dias=12,
            declaracion_jurada_en=AHORA, creado_en=AHORA)
        s.add(exp)
        s.flush()
        s.add(Historial(expediente_id=exp.id, estado="Recibido", etapa="En cola",
                        actor_id=cuenta.id, en=AHORA))
        s.add(Bitacora(n=1, ts="2026-09-29T12:00:00+00:00", municipio="panama",
                       accion="prueba", actor="sistema", datos="{}", previo="0" * 64,
                       hash="1" * 64))
        s.commit()


def test_existen_las_ocho_tablas(bd_limpia):
    assert set(inspect(bd_limpia).get_table_names()) == {
        "cuentas", "sesiones", "permisos", "documentos",
        "expedientes", "historial", "citas", "bitacora",
    }


def test_el_catalogo_trae_los_35_tramites():
    assert len(catalogo.PERMISOS) == 35
    assert len({p[0] for p in catalogo.PERMISOS}) == 35          # ids únicos
    with bd.SesionLocal() as s:
        assert len(s.scalars(select(Permiso)).all()) == 35
        esp = s.get(Permiso, "ESP-4000")
        assert (esp.aforo_min, esp.aforo_max) == (500, 3999)
        assert "Plan de seguridad y evacuación" in esp.requisitos
        assert s.get(Permiso, "ACERA").aforo_min is None


def test_migrar_se_puede_correr_dos_veces(bd_limpia):
    migrar.preparar(bd_limpia)
    with bd.SesionLocal() as s:
        assert len(s.scalars(select(Permiso)).all()) == 35


def test_la_base_rechaza_un_menor_de_edad_aunque_la_api_falle():
    with bd.motor.begin() as c, pytest.raises(DBAPIError):
        c.execute(text(
            "INSERT INTO cuentas (email, nombre, apellido, edad, organizacion, clave, rol, "
            "consentimiento_en, creado_en) VALUES ('x@y.com','A','B',15,'O','c','ciudadano',"
            "'2026-01-01','2026-01-01')"))


def test_la_base_rechaza_un_estado_inventado():
    _filas_de_prueba()
    with bd.motor.begin() as c, pytest.raises(DBAPIError):
        c.execute(text("UPDATE expedientes SET estado = 'Aprobadísimo'"))


def test_las_llaves_foraneas_estan_activas():
    with bd.motor.begin() as c, pytest.raises(DBAPIError):
        c.execute(text("INSERT INTO sesiones (token_hash, cuenta_id, creada_en, expira_en) "
                       "VALUES ('h', 999, '2026-01-01', '2026-01-02')"))


@pytest.mark.parametrize("sql", [
    "UPDATE bitacora SET actor = 'intruso'",
    "DELETE FROM bitacora",
    "UPDATE historial SET comentario = 'cambiado'",
    "DELETE FROM historial",
])
def test_bitacora_e_historial_son_de_solo_anexado(sql):
    _filas_de_prueba()
    with bd.motor.begin() as c, pytest.raises(DBAPIError, match="solo anexado"):
        c.execute(text(sql))


def test_las_fechas_vuelven_con_zona_horaria():
    with bd.SesionLocal() as s:
        cuenta = _cuenta()
        s.add(cuenta)
        s.flush()
        s.add(Sesion(token_hash="h" * 64, cuenta_id=cuenta.id, creada_en=AHORA,
                     expira_en=AHORA + timedelta(hours=8)))
        s.commit()
    with bd.SesionLocal() as s:
        ses = s.scalars(select(Sesion)).one()
        assert ses.expira_en == AHORA + timedelta(hours=8)
        assert ses.expira_en.tzinfo is not None


def test_una_fecha_sin_zona_horaria_se_rechaza():
    with bd.SesionLocal() as s:
        cuenta = _cuenta()
        cuenta.creado_en = datetime(2026, 9, 29, 12, 0)            # sin tzinfo
        s.add(cuenta)
        with pytest.raises(Exception, match="zona horaria"):
            s.flush()


def test_los_datos_sobreviven_a_un_reinicio(tmp_path):
    url = f"sqlite:///{tmp_path / 'mupa.db'}"
    migrar.preparar(bd.configurar(url))
    with bd.SesionLocal() as s:
        s.add(_cuenta())
        s.commit()
    bd.motor.dispose()

    bd.configurar(url)                                           # "reinicio"
    with bd.SesionLocal() as s:
        assert s.scalars(select(Cuenta)).one().email == "ana@correo.com"
    bd.motor.dispose()
