"""
main.py — API de la Ventanilla Única Municipal.

    uvicorn main:app --reload --port 8000

Rutas:
    POST   /api/cuentas                    crear cuenta
    POST   /api/sesiones                   iniciar sesión
    DELETE /api/sesiones                   cerrar sesión
    GET    /api/permisos                   catálogo de trámites
    POST   /api/documentos/verificar       ClamAV + SHA-256  ← el paso 3 del portal
    POST   /api/solicitudes                crear expediente
    GET    /api/solicitudes                listar expedientes del usuario
    POST   /api/citas                      reservar turno
    POST   /api/contacto                   mensaje de contacto
    GET    /api/bitacora/verificar         integridad de la auditoría
    GET    /salud                          health check
    GET    /metrics                        métricas para Prometheus → Grafana

Los datos viven en la base que indique DATABASE_URL (SQLite por defecto,
PostgreSQL en Docker). Todo el acceso pasa por el módulo `repositorio`.
"""

from __future__ import annotations

import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import date
from typing import Literal

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import almacen
import antivirus
import bd
import metricas
import migrar
import repositorio
import seguridad
from tablas import Cuenta

MUNICIPIO = repositorio.MUNICIPIO                  # etiqueta multi-municipio
ORIGENES = os.getenv("CORS_ORIGENES", "http://localhost:5173,http://localhost:3000").split(",")


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    seguridad.comprobar_clave()                    # sin clave de cifrado no se arranca
    motor = bd.configurar()
    if motor.dialect.name == "sqlite":
        migrar.preparar(motor)                     # desarrollo: crea tablas y catálogo
    yield
    motor.dispose()


app = FastAPI(title="Ventanilla Única Municipal", version="1.1.0", lifespan=ciclo_de_vida)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ modelos

class CuentaNueva(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    apellido: str = Field(min_length=2, max_length=60)
    edad: int = Field(ge=18, le=110)
    organizacion: str = Field(min_length=2, max_length=120, description="Lugar donde colabora")
    email: EmailStr
    cedula: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    acepta_tratamiento: Literal[True] = Field(description="Consentimiento, Ley 81 de 2019")


class Credenciales(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class SolicitudNueva(BaseModel):
    permiso_id: str = Field(max_length=12)
    corregimiento: str = Field(max_length=60)
    tipo_acto: str = Field(max_length=80)
    lugar: str = Field(min_length=5, max_length=200)
    fecha: date
    hora_inicio: str = Field(pattern=r"^\d{2}:\d{2}$")
    hora_fin: str = Field(pattern=r"^\d{2}:\d{2}$")
    aforo: int = Field(ge=1, le=60_000)
    responsable: str = Field(max_length=120)
    telefono: str = Field(max_length=30)
    motivo: str = Field(min_length=20, max_length=600)
    documento_sha256: str = Field(min_length=64, max_length=64)
    declaracion_jurada: Literal[True] = Field(description="Acuerdo Municipal 130 de 2016")


class CitaNueva(BaseModel):
    sede: str = Field(max_length=80)
    motivo: str = Field(max_length=120)
    fecha: date
    hora: str = Field(pattern=r"^\d{2}:\d{2}$")
    expediente: str | None = Field(default=None, max_length=200)


class MensajeContacto(BaseModel):
    nombre: str = Field(max_length=120)
    email: EmailStr
    tema: str = Field(max_length=80)
    mensaje: str = Field(min_length=15, max_length=2000)
    expediente: str | None = Field(default=None, max_length=200)


# ------------------------------------------------------------------ sesión

def _token(authorization: str) -> str:
    return authorization.removeprefix("Bearer ").strip()


def usuario_actual(
    authorization: str = Header(default=""),
    s: Session = Depends(bd.sesion),
) -> Cuenta:
    cuenta = repositorio.cuenta_por_token(s, _token(authorization))
    if cuenta is None:
        raise HTTPException(401, "Sesión no válida o expirada. Inicia sesión de nuevo.")
    # Cierra la transacción de lectura: la ruta puede tardar (ClamAV escanea
    # hasta 30 s) y PostgreSQL corta las transacciones inactivas a los 30 s.
    s.commit()
    return cuenta


# ------------------------------------------------------------------ métricas

@app.middleware("http")
async def medir(request: Request, call_next):
    inicio = time.perf_counter()
    respuesta = await call_next(request)
    ruta = request.scope.get("route").path if request.scope.get("route") else request.url.path
    metricas.peticiones_http.labels(request.method, ruta, respuesta.status_code).inc()
    metricas.latencia_http.labels(request.method, ruta).observe(time.perf_counter() - inicio)
    return respuesta


def refrescar_estados(s: Session) -> bool:
    """Actualiza los contadores por estado. Si la base no responde, lo marca
    en mupa_bd_arriba en lugar de tumbar /metrics: las demás series (antivirus,
    latencia) tienen que seguir llegando a Grafana."""
    try:
        conteo = repositorio.conteo_por_estado(s)
    except SQLAlchemyError:
        metricas.bd_arriba.set(0)
        return False
    for estado, n in conteo.items():
        metricas.solicitudes_por_estado.labels(estado, MUNICIPIO).set(n)
    metricas.bd_arriba.set(1)
    return True


@app.get("/metrics", include_in_schema=False)
def endpoint_metricas(s: Session = Depends(bd.sesion)) -> Response:
    metricas.antivirus_arriba.set(1 if antivirus.ping() else 0)
    metricas.info_antivirus.info({"version": antivirus.version_firmas()})
    refrescar_estados(s)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/salud")
def salud(s: Session = Depends(bd.sesion)) -> dict:
    av = antivirus.ping()
    try:
        s.execute(text("SELECT 1"))
        base = {"arriba": True, "expedientes": repositorio.total_expedientes(s),
                "bitacora": repositorio.total_bitacora(s)}
    except SQLAlchemyError:
        base = {"arriba": False}
    return {
        "estado": "ok" if av and base["arriba"] else "degradado",
        "municipio": MUNICIPIO,
        "antivirus": {"arriba": av, "firmas": antivirus.version_firmas()},
        "base_de_datos": base,
    }


# ------------------------------------------------------------------ cuentas

@app.post("/api/cuentas", status_code=201)
def crear_cuenta(c: CuentaNueva, s: Session = Depends(bd.sesion)) -> dict:
    try:
        cuenta = repositorio.crear_cuenta(
            s, nombre=c.nombre, apellido=c.apellido, edad=c.edad,
            organizacion=c.organizacion, email=c.email, cedula=c.cedula, password=c.password,
        )
    except repositorio.Duplicado:
        raise HTTPException(409, "Ya existe una cuenta con ese correo. Inicia sesión.")
    repositorio.registrar(s, "cuenta.creada", cuenta.email, organizacion=c.organizacion)
    token = repositorio.abrir_sesion(s, cuenta)
    s.commit()
    return {"token": token, "usuario": repositorio.publico(cuenta)}


@app.post("/api/sesiones")
def iniciar_sesion(c: Credenciales, s: Session = Depends(bd.sesion)) -> dict:
    correo = c.email.lower()
    u = repositorio.cuenta_por_email(s, correo)
    # Si el correo no existe se compara igual contra una clave falsa, para que
    # la respuesta tarde lo mismo y no revele qué correos están registrados.
    clave_ok = seguridad.verificar_clave(c.password, u.clave if u else seguridad.CLAVE_FALSA)
    if u is None or not clave_ok:
        repositorio.registrar(s, "sesion.fallida", correo)
        s.commit()                                  # el intento fallido queda registrado
        raise HTTPException(401, "El correo o la contraseña no coinciden.")
    token = repositorio.abrir_sesion(s, u)
    repositorio.registrar(s, "sesion.iniciada", u.email)
    s.commit()
    return {"token": token, "usuario": repositorio.publico(u)}


@app.delete("/api/sesiones", status_code=204)
def cerrar_sesion(
    authorization: str = Header(default=""),
    usuario: Cuenta = Depends(usuario_actual),
    s: Session = Depends(bd.sesion),
) -> Response:
    repositorio.cerrar_sesion(s, _token(authorization))
    repositorio.registrar(s, "sesion.cerrada", usuario.email)
    s.commit()
    return Response(status_code=204)


# ------------------------------------------------------------------ permisos

@app.get("/api/permisos")
def catalogo(categoria: str | None = None, s: Session = Depends(bd.sesion)) -> list[dict]:
    return [repositorio.permiso_a_dict(p) for p in repositorio.permisos(s, categoria)]


# ------------------------------------------------------------------ documentos

@app.post("/api/documentos/verificar")
def verificar_documento(
    archivo: UploadFile = File(...),
    usuario: Cuenta = Depends(usuario_actual),
    s: Session = Depends(bd.sesion),
) -> dict:
    """
    Éste es el paso 3 del portal. Recibe el PDF, lo pasa por ClamAV y devuelve
    la huella SHA-256 que después viaja en la solicitud. El archivo sólo se
    guarda si el veredicto es limpio.

    Es una ruta síncrona a propósito: FastAPI la corre en un hilo aparte, así
    el escaneo y las consultas a la base no frenan a las demás peticiones.
    """
    contenido = archivo.file.read()
    original = archivo.filename or "documento.pdf"

    with metricas.cronometrar(metricas.duracion_escaneo):
        v = antivirus.verificar(contenido, original)      # el formato se juzga con el nombre real

    # Cabe en documentos.nombre (255) sin perder la extensión.
    raiz, ext = os.path.splitext(original)
    nombre = original if len(original) <= 255 else raiz[:255 - len(ext)] + ext

    metricas.documentos_verificados.labels(v.resultado.value, MUNICIPIO).inc()

    if v.resultado is antivirus.Resultado.INFECTADO:
        metricas.amenazas_detectadas.labels(v.firma_virus or "desconocida", MUNICIPIO).inc()
        repositorio.registrar(s, "documento.infectado", usuario.email,
                              archivo=nombre, firma=v.firma_virus)
        s.commit()
        raise HTTPException(422, v.mensaje)

    if not v.aceptado:
        repositorio.registrar(s, "documento.rechazado", usuario.email,
                              archivo=nombre, motivo=v.resultado.value)
        s.commit()
        codigo = 503 if v.resultado is antivirus.Resultado.ANTIVIRUS_CAIDO else 400
        raise HTTPException(codigo, v.mensaje)

    ruta = almacen.guardar(v.sha256, contenido)
    doc = repositorio.guardar_documento(s, usuario, v.sha256, nombre, v.bytes_, ruta)
    sello = repositorio.registrar(s, "documento.verificado", usuario.email,
                                  sha256=v.sha256, bytes=v.bytes_)
    s.commit()

    return {
        "sha256": v.sha256,
        "bytes": v.bytes_,
        "nombre": nombre,
        "sellado": doc.sellado_en.isoformat(timespec="seconds"),
        "bitacora": sello.hash,
        "mensaje": v.mensaje,
    }


# ------------------------------------------------------------------ solicitudes

@app.post("/api/solicitudes", status_code=201)
def crear_solicitud(
    sol: SolicitudNueva,
    usuario: Cuenta = Depends(usuario_actual),
    s: Session = Depends(bd.sesion),
) -> dict:
    permiso = repositorio.permiso(s, sol.permiso_id)
    if not permiso:
        raise HTTPException(404, "El permiso solicitado no existe en el catálogo.")

    doc = repositorio.documento_de(s, usuario.id, sol.documento_sha256)
    if not doc:
        raise HTTPException(400, "Adjunta y verifica un documento antes de enviar la solicitud.")

    if (date.today() - sol.fecha).days > 0:
        raise HTTPException(400, "La fecha del acto ya pasó.")
    if (sol.fecha - date.today()).days < 15:
        raise HTTPException(400, "La fecha debe tener al menos 15 días hábiles de antelación.")

    if permiso.aforo_min is not None and not (permiso.aforo_min <= sol.aforo <= permiso.aforo_max):
        raise HTTPException(
            400,
            f"Para «{permiso.nombre}» el aforo debe estar entre "
            f"{permiso.aforo_min} y {permiso.aforo_max} personas.",
        )

    expediente = repositorio.crear_expediente(s, usuario, permiso, doc, sol.model_dump())
    repositorio.registrar(s, "expediente.creado", usuario.email,
                          codigo=expediente.codigo, permiso=permiso.id)
    s.commit()

    metricas.solicitudes_creadas.labels(permiso.nombre, sol.corregimiento, MUNICIPIO).inc()
    refrescar_estados(s)
    return repositorio.expediente_a_dict(expediente)


@app.get("/api/solicitudes")
def listar_solicitudes(
    estado: Literal["Recibido", "En revisión", "Aprobado", "Subsanación", "Rechazado"] | None = None,
    usuario: Cuenta = Depends(usuario_actual),
    s: Session = Depends(bd.sesion),
) -> list[dict]:
    return [repositorio.expediente_a_dict(e) for e in repositorio.expedientes_de(s, usuario, estado)]


# ------------------------------------------------------------------ citas

@app.post("/api/citas", status_code=201)
def reservar_cita(
    c: CitaNueva,
    usuario: Cuenta = Depends(usuario_actual),
    s: Session = Depends(bd.sesion),
) -> dict:
    if c.fecha.weekday() >= 5:
        raise HTTPException(400, "La atención presencial es de lunes a viernes.")
    email = usuario.email          # se lee antes: un rollback expiraría el objeto
    try:
        cita = repositorio.reservar_cita(s, usuario, c.model_dump())
    except repositorio.TurnoOcupado:
        raise HTTPException(409, "Ese horario acaba de ocuparse. Elige otro turno.")
    repositorio.registrar(s, "cita.reservada", email, turno=cita.turno, sede=c.sede)
    s.commit()
    return repositorio.cita_a_dict(cita)


# ------------------------------------------------------------------ contacto

@app.post("/api/contacto", status_code=201)
def contacto(m: MensajeContacto, s: Session = Depends(bd.sesion)) -> dict:
    ticket = f"MSG-{secrets.randbelow(900_000) + 100_000}"
    repositorio.registrar(s, "contacto.recibido", m.email.lower(), ticket=ticket, tema=m.tema)
    s.commit()
    return {"ticket": ticket, "mensaje": "Respondemos en un plazo de 3 días hábiles."}


# ------------------------------------------------------------------ auditoría

@app.get("/api/bitacora/verificar")
def verificar_bitacora(s: Session = Depends(bd.sesion)) -> dict:
    """Recorre la cadena de hashes y reporta la primera fila alterada."""
    return repositorio.verificar_bitacora(s)
