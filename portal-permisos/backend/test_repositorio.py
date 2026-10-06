"""Pruebas de repositorio.py: cuentas, sesiones, catálogo, documentos, expedientes y citas."""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

import bd
import repositorio
from tablas import Sesion


def _cuenta(s, email="ana@correo.com"):
    return repositorio.crear_cuenta(
        s, nombre="Ana", apellido="Pérez", edad=30, organizacion="X",
        email=email, cedula=None, password="clave-de-prueba")


# ──────────────────────────── cuentas y sesiones ────────────────────────────

def test_no_se_repite_un_correo_aunque_cambien_las_mayusculas():
    with bd.SesionLocal() as s:
        _cuenta(s, "Ana@Correo.com")
        s.commit()
        with pytest.raises(repositorio.Duplicado):
            _cuenta(s, "ana@correo.com")


def test_la_base_guarda_la_huella_del_token_no_el_token():
    with bd.SesionLocal() as s:
        token = repositorio.abrir_sesion(s, _cuenta(s))
        s.commit()
        guardado = s.scalars(select(Sesion.token_hash)).one()
        assert guardado != token and token not in guardado
        assert repositorio.cuenta_por_token(s, token).email == "ana@correo.com"


def test_una_sesion_vencida_no_sirve_y_se_borra():
    with bd.SesionLocal() as s:
        token = repositorio.abrir_sesion(s, _cuenta(s))
        s.commit()
        s.query(Sesion).update({"expira_en": datetime.now(timezone.utc) - timedelta(minutes=1)})
        s.commit()
        assert repositorio.cuenta_por_token(s, token) is None
        assert s.query(Sesion).count() == 0


def test_un_token_vacio_o_inventado_no_da_acceso():
    with bd.SesionLocal() as s:
        assert repositorio.cuenta_por_token(s, "") is None
        assert repositorio.cuenta_por_token(s, "inventado") is None


def test_la_cedula_se_guarda_cifrada_y_se_lee_en_claro():
    with bd.SesionLocal() as s:
        repositorio.crear_cuenta(s, nombre="Ana", apellido="Pérez", edad=30, organizacion="X",
                                 email="ana@correo.com", cedula="8-912-345",
                                 password="clave-de-prueba")
        s.commit()
        crudo = s.execute(text("SELECT cedula FROM cuentas")).scalar_one()
        assert crudo != "8-912-345" and "912" not in crudo
    with bd.SesionLocal() as s:
        assert repositorio.cuenta_por_email(s, "ana@correo.com").cedula == "8-912-345"


def test_la_contrasena_no_se_guarda_en_claro():
    with bd.SesionLocal() as s:
        _cuenta(s)
        s.commit()
        crudo = s.execute(text("SELECT clave FROM cuentas")).scalar_one()
        assert "clave-de-prueba" not in crudo and crudo.startswith("pbkdf2_sha256$")


# ──────────────────────────── documentos ────────────────────────────

def test_dos_personas_pueden_subir_el_mismo_pdf():
    """Antes, la segunda persona le "robaba" el documento a la primera."""
    sha = "f" * 64
    with bd.SesionLocal() as s:
        ana, luis = _cuenta(s), _cuenta(s, "luis@correo.com")
        repositorio.guardar_documento(s, ana, sha, "a.pdf", 100, "ff/f.pdf")
        repositorio.guardar_documento(s, luis, sha, "b.pdf", 100, "ff/f.pdf")
        s.commit()
        assert repositorio.documento_de(s, ana.id, sha) is not None
        assert repositorio.documento_de(s, luis.id, sha) is not None


def test_subir_dos_veces_el_mismo_pdf_no_duplica_el_registro():
    sha = "a" * 64
    with bd.SesionLocal() as s:
        ana = _cuenta(s)
        uno = repositorio.guardar_documento(s, ana, sha, "a.pdf", 100, "aa/a.pdf")
        dos = repositorio.guardar_documento(s, ana, sha, "a.pdf", 100, "aa/a.pdf")
        assert uno.id == dos.id


# ──────────────────────────── citas ────────────────────────────

def test_el_mismo_turno_no_se_puede_tomar_dos_veces():
    cita = {"sede": "Sede Central", "motivo": "Consulta", "fecha": date(2026, 10, 20),
            "hora": "09:00", "expediente": None}
    with bd.SesionLocal() as s:
        ana = _cuenta(s)
        s.commit()
        assert repositorio.reservar_cita(s, ana, cita).turno == "CT-1001"
        s.commit()
    with bd.SesionLocal() as s:
        luis = _cuenta(s, "luis@correo.com")
        s.commit()
        with pytest.raises(repositorio.TurnoOcupado):
            repositorio.reservar_cita(s, luis, cita)


def test_los_contadores_por_estado_incluyen_los_vacios():
    with bd.SesionLocal() as s:
        assert repositorio.conteo_por_estado(s) == {
            "Recibido": 0, "En revisión": 0, "Aprobado": 0, "Subsanación": 0, "Rechazado": 0}



# ──────────────────────────── catálogo y expedientes ────────────────────────────

def test_el_catalogo_se_filtra_por_categoria():
    with bd.SesionLocal() as s:
        nocturnos = repositorio.permisos(s, "Permisos nocturnos")
        assert len(nocturnos) == 5
        assert repositorio.permiso_a_dict(repositorio.permiso(s, "ESP-500-"))["aforo"] == [1, 499]
        assert repositorio.permiso_a_dict(repositorio.permiso(s, "NOC-A"))["aforo"] is None


def _datos_acto() -> dict:
    return {"corregimiento": "Santa Ana", "tipo_acto": "Otro", "lugar": "Ave. Central",
            "fecha": date.today() + timedelta(days=30), "hora_inicio": "08:00",
            "hora_fin": "12:00", "aforo": 10, "responsable": "Ana", "telefono": "60000000",
            "motivo": "Uso temporal de la acera para una actividad."}


def test_el_expediente_nace_con_codigo_estado_e_historial():
    with bd.SesionLocal() as s:
        ana = _cuenta(s)
        doc = repositorio.guardar_documento(s, ana, "e" * 64, "a.pdf", 100, "ee/e.pdf")
        e = repositorio.crear_expediente(s, ana, repositorio.permiso(s, "ACERA"), doc, _datos_acto())
        s.commit()
        assert e.codigo == f"EXP-{date.today().year}-004183"
        assert e.estado == "Recibido" and e.plazo_dias == 12
        assert [h.estado for h in repositorio.historial_de(s, e)] == ["Recibido"]
        assert repositorio.expediente_a_dict(e)["documento_sha256"] == "e" * 64
        assert repositorio.conteo_por_estado(s)["Recibido"] == 1
        assert repositorio.total_expedientes(s) == 1


def test_cada_quien_ve_solo_sus_expedientes():
    with bd.SesionLocal() as s:
        ana, luis = _cuenta(s), _cuenta(s, "luis@correo.com")
        doc = repositorio.guardar_documento(s, ana, "e" * 64, "a.pdf", 100, "ee/e.pdf")
        repositorio.crear_expediente(s, ana, repositorio.permiso(s, "ACERA"), doc, _datos_acto())
        s.commit()
        assert len(repositorio.expedientes_de(s, ana)) == 1
        assert repositorio.expedientes_de(s, luis) == []
        assert repositorio.expedientes_de(s, ana, "Aprobado") == []
