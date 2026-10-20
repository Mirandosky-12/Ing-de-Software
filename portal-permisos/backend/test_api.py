"""
Pruebas de la API, reportadas a Qase igual que las de Playwright.

    pytest                                   # local, sin subir nada
    QASE_MODE=testops \
    QASE_TESTOPS_API_TOKEN=... \
    QASE_TESTOPS_PROJECT=VUM pytest --qase-mode=testops

Las pruebas marcadas con @qase.id(N) se amarran al caso N del proyecto,
los mismos números que usa calidad/casos-qase.md.

Cada prueba corre sobre una base nueva en memoria (ver conftest.py).
"""

import hashlib
import io
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from qase.pytest import qase
from sqlalchemy.exc import OperationalError

import antivirus
import bd
import main
import repositorio
from tablas import Bitacora, Sesion

client = TestClient(main.app)

PDF_OK = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
NO_PDF = b"Esto no es un PDF, es texto plano."
# ClamAV sólo reconoce EICAR al inicio de un archivo, y la API exige que empiece
# con %PDF: por eso la cadena va dentro de un stream, que ClamAV extrae del PDF.
_CADENA_EICAR = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
EICAR = (b"%PDF-1.4\n1 0 obj\n<< /Type /EmbeddedFile /Length 68 >>\nstream\n"
         + _CADENA_EICAR
         + b"\nendstream\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n")

CUENTA = {
    "nombre": "Diego", "apellido": "López", "edad": 22,
    "organizacion": "Universidad Tecnológica de Panamá",
    "email": "pruebas@mupa.gob.pa", "password": "clave-de-prueba",
    "acepta_tratamiento": True,
}


@pytest.fixture
def token():
    r = client.post("/api/cuentas", json=CUENTA)
    assert r.status_code == 201
    return r.json()["token"]


@pytest.fixture
def cabecera(token):
    return {"Authorization": f"Bearer {token}"}


def _documento_de(email: str, sha: str) -> None:
    """Registra un documento ya verificado a nombre de `email`, sin pasar por ClamAV."""
    with bd.SesionLocal() as s:
        cuenta = repositorio.cuenta_por_email(s, email) or repositorio.crear_cuenta(
            s, nombre="Otra", apellido="Persona", edad=30, organizacion="X",
            email=email, cedula=None, password="clave-de-prueba")
        repositorio.guardar_documento(s, cuenta, sha, "prueba.pdf", 100, f"{sha[:2]}/{sha}.pdf")
        s.commit()


def _acciones() -> list[str]:
    with bd.SesionLocal() as s:
        return [b.accion for b in s.query(Bitacora).order_by(Bitacora.n)]


# ───────────────────────────── cuentas ─────────────────────────────

@qase.id(3)
@qase.title("La API rechaza el registro de un menor de edad")
def test_menor_de_edad():
    r = client.post("/api/cuentas", json={**CUENTA, "edad": 16, "email": "x@y.com"})
    assert r.status_code == 422          # pydantic: edad >= 18


def test_sin_consentimiento_no_hay_cuenta():
    r = client.post("/api/cuentas", json={**CUENTA, "acepta_tratamiento": False})
    assert r.status_code == 422


@qase.id(2)
def test_password_incorrecta(token):
    r = client.post("/api/sesiones",
                    json={"email": CUENTA["email"], "password": "equivocada"})
    assert r.status_code == 401
    # El mensaje no debe revelar si el correo existe
    assert "no coinciden" in r.json()["detail"]


def test_el_intento_fallido_queda_en_la_bitacora(token):
    client.post("/api/sesiones", json={"email": CUENTA["email"], "password": "equivocada"})
    client.post("/api/sesiones", json={"email": "nadie@correo.com", "password": "x"})
    assert _acciones().count("sesion.fallida") == 2


def test_correo_duplicado(token):
    r = client.post("/api/cuentas", json=CUENTA)
    assert r.status_code == 409


def test_la_clave_nunca_sale_en_la_respuesta(token):
    r = client.post("/api/sesiones",
                    json={"email": CUENTA["email"], "password": CUENTA["password"]})
    cuerpo = r.json()
    assert "clave" not in cuerpo["usuario"] and "sal" not in cuerpo["usuario"]


def test_cerrar_sesion_invalida_el_token(cabecera):
    assert client.delete("/api/sesiones", headers=cabecera).status_code == 204
    assert client.get("/api/solicitudes", headers=cabecera).status_code == 401


def test_una_sesion_vencida_devuelve_401(cabecera):
    with bd.SesionLocal() as s:
        s.query(Sesion).update({"expira_en": datetime.now(timezone.utc) - timedelta(seconds=1)})
        s.commit()
    assert client.get("/api/solicitudes", headers=cabecera).status_code == 401


# ──────────────────────── seguridad documental ────────────────────────

def _subir(contenido: bytes, nombre: str, cabecera: dict):
    return client.post(
        "/api/documentos/verificar",
        files={"archivo": (nombre, io.BytesIO(contenido), "application/pdf")},
        headers=cabecera,
    )


@qase.id(21)
@qase.title("Un .txt renombrado a .pdf no pasa la validación de formato")
def test_falso_pdf(cabecera):
    r = _subir(NO_PDF, "documento.pdf", cabecera)
    assert r.status_code == 400
    assert "no es un PDF válido" in r.json()["detail"]


@qase.id(24)
def test_archivo_demasiado_grande(cabecera):
    grande = PDF_OK + b"0" * (11 * 1024 * 1024)
    r = _subir(grande, "grande.pdf", cabecera)
    assert r.status_code == 400
    assert "10 MB" in r.json()["detail"]


def test_sin_sesion_no_se_puede_subir():
    r = _subir(PDF_OK, "x.pdf", {})
    assert r.status_code == 401


@qase.id(25)
@qase.title("Si ClamAV está caído, no se acepta el documento")
def test_antivirus_caido_devuelve_503(cabecera, monkeypatch):
    def sin_conexion():
        raise ConnectionRefusedError("clamd no responde")
    monkeypatch.setattr(antivirus, "_cliente", sin_conexion)
    r = _subir(PDF_OK, "requisitos.pdf", cabecera)
    assert r.status_code == 503
    assert "no está disponible" in r.json()["detail"]
    assert "documento.rechazado" in _acciones()


def test_un_pdf_limpio_se_guarda_en_el_almacen_y_en_la_base(cabecera, monkeypatch):
    sha = hashlib.sha256(PDF_OK).hexdigest()
    monkeypatch.setattr(antivirus, "verificar", lambda contenido, nombre: antivirus.Veredicto(
        antivirus.Resultado.LIMPIO, "Documento verificado.", sha256=sha, bytes_=len(contenido)))
    r = _subir(PDF_OK, "requisitos.pdf", cabecera)
    assert r.status_code == 200 and r.json()["sha256"] == sha
    import almacen
    assert almacen.leer(f"{sha[:2]}/{sha}.pdf") == PDF_OK
    with bd.SesionLocal() as s:
        cuenta = repositorio.cuenta_por_email(s, CUENTA["email"])
        assert repositorio.documento_de(s, cuenta.id, sha) is not None


def test_un_nombre_de_archivo_larguisimo_se_recorta(cabecera, monkeypatch):
    """SQLite no revisa el largo de las columnas, PostgreSQL sí: sin el recorte
    este archivo daría un error 500 en producción. El formato se valida con el
    nombre original; sólo se recorta el que se guarda, conservando la extensión.
    Corre la validación real: sólo se sustituye el cliente de ClamAV."""
    class ClamFalso:
        def instream(self, _flujo):
            return {"stream": ("OK", None)}
    monkeypatch.setattr(antivirus, "_cliente", lambda: ClamFalso())
    r = _subir(PDF_OK, "a" * 300 + ".pdf", cabecera)
    assert r.status_code == 200
    nombre = r.json()["nombre"]
    assert len(nombre) <= 255 and nombre.endswith(".pdf")


def test_validar_la_sesion_no_deja_una_transaccion_abierta(token):
    with bd.SesionLocal() as s:
        main.usuario_actual(authorization=f"Bearer {token}", s=s)
        assert not s.in_transaction()


@pytest.mark.clamav
@qase.id(20)
@qase.title("Un PDF limpio devuelve su huella SHA-256")
def test_pdf_limpio(cabecera):
    """Requiere clamd arriba: docker compose up -d clamav"""
    if not main.antivirus.ping():
        pytest.skip("clamd no está disponible")
    r = _subir(PDF_OK, "requisitos.pdf", cabecera)
    assert r.status_code == 200
    assert len(r.json()["sha256"]) == 64


@pytest.mark.clamav
@qase.id(22)
@qase.title("ClamAV detiene el archivo de prueba EICAR")
def test_eicar(cabecera):
    if not main.antivirus.ping():
        pytest.skip("clamd no está disponible")
    r = _subir(EICAR, "eicar.pdf", cabecera)
    assert r.status_code == 422
    assert "amenaza" in r.json()["detail"].lower()


# ──────────────────────────── solicitudes ────────────────────────────

def _solicitud(sha: str, **cambios) -> dict:
    base = {
        "permiso_id": "ESP-4000", "corregimiento": "San Francisco",
        "tipo_acto": "Concierto o presentación musical",
        "lugar": "Parque Omar, calle 74 San Francisco",
        "fecha": (date.today() + timedelta(days=40)).isoformat(),
        "hora_inicio": "18:00", "hora_fin": "23:00", "aforo": 800,
        "responsable": "Diego López", "telefono": "+507 6000-0000",
        "motivo": "Concierto benéfico al aire libre organizado por una fundación local.",
        "documento_sha256": sha,
        "declaracion_jurada": True,
    }
    return {**base, **cambios}


@qase.id(13)
def test_aforo_fuera_de_rango(cabecera):
    sha = "a" * 64
    _documento_de(CUENTA["email"], sha)
    r = client.post("/api/solicitudes",
                    json=_solicitud(sha, permiso_id="ESP-500-", aforo=1200),
                    headers=cabecera)
    assert r.status_code == 400
    assert "aforo debe estar entre" in r.json()["detail"]


@qase.id(12)
def test_fecha_muy_proxima(cabecera):
    sha = "b" * 64
    _documento_de(CUENTA["email"], sha)
    r = client.post("/api/solicitudes",
                    json=_solicitud(sha, fecha=(date.today() + timedelta(days=3)).isoformat()),
                    headers=cabecera)
    assert r.status_code == 400
    assert "15 días hábiles" in r.json()["detail"]


def test_no_se_puede_usar_el_documento_de_otro(cabecera):
    sha = "c" * 64
    _documento_de("otra.persona@correo.com", sha)
    r = client.post("/api/solicitudes", json=_solicitud(sha), headers=cabecera)
    assert r.status_code == 400


def test_sin_declaracion_jurada_no_hay_expediente(cabecera):
    sha = "d" * 64
    _documento_de(CUENTA["email"], sha)
    r = client.post("/api/solicitudes", json=_solicitud(sha, declaracion_jurada=False),
                    headers=cabecera)
    assert r.status_code == 422


@qase.id(16)
def test_expediente_se_crea_con_codigo(cabecera):
    sha = "d" * 64
    _documento_de(CUENTA["email"], sha)
    r = client.post("/api/solicitudes", json=_solicitud(sha), headers=cabecera)
    assert r.status_code == 201
    assert r.json()["codigo"].startswith("EXP-")
    assert r.json()["estado"] == "Recibido"


def test_el_expediente_se_puede_listar_despues(cabecera):
    sha = "d" * 64
    _documento_de(CUENTA["email"], sha)
    codigo = client.post("/api/solicitudes", json=_solicitud(sha), headers=cabecera).json()["codigo"]
    lista = client.get("/api/solicitudes", headers=cabecera).json()
    assert [e["codigo"] for e in lista] == [codigo]


def test_cualquier_tramite_del_catalogo_se_puede_solicitar(cabecera):
    """Antes sólo existían 5 de los 35 trámites en el backend."""
    sha = "d" * 64
    _documento_de(CUENTA["email"], sha)
    r = client.post("/api/solicitudes", json=_solicitud(sha, permiso_id="GANADO"),
                    headers=cabecera)
    assert r.status_code == 201


def test_el_catalogo_devuelve_los_35_tramites():
    assert len(client.get("/api/permisos").json()) == 35


# ──────────────────────────── constancia ────────────────────────────

def _expediente(cabecera, email: str = CUENTA["email"]) -> str:
    sha = "e" * 64
    _documento_de(email, sha)
    return client.post("/api/solicitudes", json=_solicitud(sha), headers=cabecera).json()["codigo"]


def test_la_constancia_es_un_pdf_con_codigo_huella_y_sello(cabecera):
    codigo = _expediente(cabecera)
    with bd.SesionLocal() as s:
        sello = s.query(Bitacora).filter_by(accion="expediente.creado").one().hash

    r = client.get(f"/api/solicitudes/{codigo}/constancia", headers=cabecera)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert f'filename="constancia-{codigo}.pdf"' in r.headers["content-disposition"]
    pdf = r.content
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    for dato in (codigo.encode(), b"e" * 64, sello.encode(), b"Panam\xe1"):   # á en WinAnsi
        assert dato in pdf
    # startxref apunta a la tabla xref: el archivo abre en cualquier lector
    inicio = int(pdf.rsplit(b"startxref", 1)[1].split()[0])
    assert pdf[inicio:inicio + 4] == b"xref"


def test_la_constancia_de_otro_solicitante_no_se_entrega(cabecera):
    with bd.SesionLocal() as s:
        otra = repositorio.crear_cuenta(s, nombre="Otra", apellido="Persona", edad=30,
                                        organizacion="X", email="otra@correo.com",
                                        cedula=None, password="clave-de-prueba")
        token_otra = repositorio.abrir_sesion(s, otra)
        s.commit()
    codigo = _expediente({"Authorization": f"Bearer {token_otra}"}, "otra@correo.com")
    r = client.get(f"/api/solicitudes/{codigo}/constancia", headers=cabecera)
    assert r.status_code == 404


def test_la_constancia_exige_sesion(cabecera):
    codigo = _expediente(cabecera)
    assert client.get(f"/api/solicitudes/{codigo}/constancia").status_code == 401


def test_descargar_la_constancia_queda_en_la_bitacora(cabecera):
    codigo = _expediente(cabecera)
    client.get(f"/api/solicitudes/{codigo}/constancia", headers=cabecera)
    with bd.SesionLocal() as s:
        assert s.query(Bitacora).filter_by(accion="constancia.descargada").count() == 1
    assert client.get("/api/bitacora/verificar").json()["integra"] is True


# ──────────────────────────── citas ────────────────────────────

def _proximo_lunes() -> str:
    hoy = date.today()
    return (hoy + timedelta(days=7 - hoy.weekday())).isoformat()


@qase.id(33)
@qase.title("Dos personas no pueden tomar el mismo turno")
def test_dos_personas_no_toman_el_mismo_turno(cabecera):
    cita = {"sede": "Sede Central", "motivo": "Consulta", "fecha": _proximo_lunes(),
            "hora": "09:00"}
    assert client.post("/api/citas", json=cita, headers=cabecera).status_code == 201

    otro = client.post("/api/cuentas", json={**CUENTA, "email": "otra@correo.com"}).json()
    r = client.post("/api/citas", json=cita, headers={"Authorization": f"Bearer {otro['token']}"})
    assert r.status_code == 409


# ──────────────────────────── bitácora ────────────────────────────

def test_la_bitacora_detecta_una_fila_alterada(cabecera):
    client.post("/api/contacto", json={
        "nombre": "Ana", "email": "ana@correo.com", "tema": "Consulta",
        "mensaje": "Quisiera conocer los requisitos del permiso nocturno B.",
    })
    assert client.get("/api/bitacora/verificar").json()["integra"] is True

    with bd.motor.begin() as c:                            # manipulación directa en la base
        c.exec_driver_sql("DROP TRIGGER bitacora_sin_update")
        c.exec_driver_sql("UPDATE bitacora SET actor = 'intruso@correo.com' WHERE n = 1")
    resultado = client.get("/api/bitacora/verificar").json()
    assert resultado["integra"] is False
    assert resultado["rota_en"] == 1


# ──────────────────────────── métricas ────────────────────────────

def test_endpoint_de_metricas_expone_las_series():
    cuerpo = client.get("/metrics").text
    for serie in ("mupa_documentos_verificados_total",
                  "mupa_solicitudes_creadas_total",
                  "mupa_antivirus_arriba",
                  "mupa_bd_arriba"):
        assert serie in cuerpo


def test_si_la_base_cae_metrics_sigue_respondiendo(monkeypatch):
    def caida(_s):
        raise OperationalError("SELECT", {}, Exception("sin conexión"))
    monkeypatch.setattr(repositorio, "conteo_por_estado", caida)
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "mupa_bd_arriba 0.0" in r.text


def test_salud_informa_la_base_de_datos():
    cuerpo = client.get("/salud").json()
    assert cuerpo["base_de_datos"]["arriba"] is True
