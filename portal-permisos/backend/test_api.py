"""
Pruebas de la API, reportadas a Qase igual que las de Playwright.

    pytest                                   # local, sin subir nada
    QASE_MODE=testops \
    QASE_TESTOPS_API_TOKEN=... \
    QASE_TESTOPS_PROJECT=VUM pytest --qase-mode=testops

Las pruebas marcadas con @qase.id(N) se amarran al caso N del proyecto,
los mismos números que usa calidad/casos-qase.md.
"""

import io

import pytest
from fastapi.testclient import TestClient
from qase.pytest import qase

import main

client = TestClient(main.app)

PDF_OK = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
NO_PDF = b"Esto no es un PDF, es texto plano."
EICAR = (b"%PDF-1.4\n"
         rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
         b"\n%%EOF\n")

CUENTA = {
    "nombre": "Diego", "apellido": "López", "edad": 22,
    "organizacion": "Universidad Tecnológica de Panamá",
    "email": "pruebas@mupa.gob.pa", "password": "clave-de-prueba",
}


@pytest.fixture
def token():
    main.CUENTAS.clear(); main.SESIONES.clear()
    main.EXPEDIENTES.clear(); main.DOCUMENTOS.clear(); main.BITACORA.clear()
    r = client.post("/api/cuentas", json=CUENTA)
    assert r.status_code == 201
    return r.json()["token"]


@pytest.fixture
def cabecera(token):
    return {"Authorization": f"Bearer {token}"}


# ───────────────────────────── cuentas ─────────────────────────────

@qase.id(3)
@qase.title("La API rechaza el registro de un menor de edad")
def test_menor_de_edad():
    r = client.post("/api/cuentas", json={**CUENTA, "edad": 16, "email": "x@y.com"})
    assert r.status_code == 422          # pydantic: edad >= 18


@qase.id(2)
def test_password_incorrecta(token):
    r = client.post("/api/sesiones",
                    json={"email": CUENTA["email"], "password": "equivocada"})
    assert r.status_code == 401
    # El mensaje no debe revelar si el correo existe
    assert "no coinciden" in r.json()["detail"]


def test_correo_duplicado(token):
    r = client.post("/api/cuentas", json=CUENTA)
    assert r.status_code == 409


def test_la_clave_nunca_sale_en_la_respuesta(token):
    r = client.post("/api/sesiones",
                    json={"email": CUENTA["email"], "password": CUENTA["password"]})
    cuerpo = r.json()
    assert "clave" not in cuerpo["usuario"] and "sal" not in cuerpo["usuario"]


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
    from datetime import date, timedelta
    base = {
        "permiso_id": "ESP-4000", "corregimiento": "San Francisco",
        "tipo_acto": "Concierto o presentación musical",
        "lugar": "Parque Omar, calle 74 San Francisco",
        "fecha": (date.today() + timedelta(days=40)).isoformat(),
        "hora_inicio": "18:00", "hora_fin": "23:00", "aforo": 800,
        "responsable": "Diego López", "telefono": "+507 6000-0000",
        "motivo": "Concierto benéfico al aire libre organizado por una fundación local.",
        "documento_sha256": sha,
    }
    return {**base, **cambios}


@qase.id(13)
def test_aforo_fuera_de_rango(cabecera, monkeypatch):
    sha = "a" * 64
    main.DOCUMENTOS[sha] = {"propietario": CUENTA["email"]}
    r = client.post("/api/solicitudes",
                    json=_solicitud(sha, permiso_id="ESP-500-", aforo=1200),
                    headers=cabecera)
    assert r.status_code == 400
    assert "aforo debe estar entre" in r.json()["detail"]


@qase.id(12)
def test_fecha_muy_proxima(cabecera):
    from datetime import date, timedelta
    sha = "b" * 64
    main.DOCUMENTOS[sha] = {"propietario": CUENTA["email"]}
    r = client.post("/api/solicitudes",
                    json=_solicitud(sha, fecha=(date.today() + timedelta(days=3)).isoformat()),
                    headers=cabecera)
    assert r.status_code == 400
    assert "15 días hábiles" in r.json()["detail"]


def test_no_se_puede_usar_el_documento_de_otro(cabecera):
    sha = "c" * 64
    main.DOCUMENTOS[sha] = {"propietario": "otra.persona@correo.com"}
    r = client.post("/api/solicitudes", json=_solicitud(sha), headers=cabecera)
    assert r.status_code == 400


@qase.id(16)
def test_expediente_se_crea_con_codigo(cabecera):
    sha = "d" * 64
    main.DOCUMENTOS[sha] = {"propietario": CUENTA["email"]}
    r = client.post("/api/solicitudes", json=_solicitud(sha), headers=cabecera)
    assert r.status_code == 201
    assert r.json()["codigo"].startswith("EXP-")
    assert r.json()["estado"] == "Recibido"


# ──────────────────────────── bitácora ────────────────────────────

def test_la_bitacora_detecta_una_fila_alterada(cabecera):
    client.post("/api/contacto", json={
        "nombre": "Ana", "email": "ana@correo.com", "tema": "Consulta",
        "mensaje": "Quisiera conocer los requisitos del permiso nocturno B.",
    })
    assert client.get("/api/bitacora/verificar").json()["integra"] is True

    main.BITACORA[0]["actor"] = "intruso@correo.com"     # manipulación
    resultado = client.get("/api/bitacora/verificar").json()
    assert resultado["integra"] is False
    assert resultado["rota_en"] == 1


# ──────────────────────────── métricas ────────────────────────────

def test_endpoint_de_metricas_expone_las_series():
    cuerpo = client.get("/metrics").text
    for serie in ("mupa_documentos_verificados_total",
                  "mupa_solicitudes_creadas_total",
                  "mupa_antivirus_arriba"):
        assert serie in cuerpo
