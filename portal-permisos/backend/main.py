"""
main.py — API de la Ventanilla Única Municipal.

    uvicorn main:app --reload --port 8000

Rutas:
    POST /api/cuentas                    crear cuenta
    POST /api/sesiones                   iniciar sesión
    GET  /api/permisos                   catálogo de trámites
    POST /api/documentos/verificar       ClamAV + SHA-256  ← el paso 3 del portal
    POST /api/solicitudes                crear expediente
    GET  /api/solicitudes                listar expedientes del usuario
    POST /api/citas                      reservar turno
    POST /api/contacto                   mensaje de contacto
    GET  /salud                          health check
    GET  /metrics                        métricas para Prometheus → Grafana

El almacenamiento es en memoria a propósito: el objetivo del proyecto es la
integración de las herramientas, no el motor de base de datos. Para pasar a
PostgreSQL sólo hay que cambiar el módulo `repositorio`.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import time
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, EmailStr, Field

import antivirus
import metricas

MUNICIPIO = os.getenv("MUNICIPIO", "panama")   # etiqueta multi-municipio
ORIGENES = os.getenv("CORS_ORIGENES", "http://localhost:5173,http://localhost:3000").split(",")

app = FastAPI(title="Ventanilla Única Municipal", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ almacén

CUENTAS: dict[str, dict] = {}
SESIONES: dict[str, str] = {}          # token -> email
EXPEDIENTES: list[dict] = []
DOCUMENTOS: dict[str, dict] = {}       # sha256 -> metadatos
CITAS: list[dict] = []
BITACORA: list[dict] = []              # auditoría append-only


def registrar(accion: str, actor: str, **datos) -> dict:
    """Bitácora encadenada: cada entrada incluye el hash de la anterior,
    así una fila alterada rompe la cadena y se nota en la auditoría."""
    previo = BITACORA[-1]["hash"] if BITACORA else "0" * 64
    entrada = {
        "n": len(BITACORA) + 1,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "municipio": MUNICIPIO,
        "accion": accion,
        "actor": actor,
        "datos": datos,
        "previo": previo,
    }
    cuerpo = f"{entrada['n']}{entrada['ts']}{accion}{actor}{datos}{previo}"
    entrada["hash"] = hashlib.sha256(cuerpo.encode()).hexdigest()
    BITACORA.append(entrada)
    return entrada


# ------------------------------------------------------------------ modelos

class CuentaNueva(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    apellido: str = Field(min_length=2, max_length=60)
    edad: int = Field(ge=18, le=110)
    organizacion: str = Field(min_length=2, max_length=120, description="Lugar donde colabora")
    email: EmailStr
    cedula: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=128)


class Credenciales(BaseModel):
    email: EmailStr
    password: str


class SolicitudNueva(BaseModel):
    permiso_id: str
    corregimiento: str
    tipo_acto: str
    lugar: str = Field(min_length=5, max_length=200)
    fecha: date
    hora_inicio: str
    hora_fin: str
    aforo: int = Field(ge=1, le=60_000)
    responsable: str
    telefono: str
    motivo: str = Field(min_length=20, max_length=600)
    documento_sha256: str = Field(min_length=64, max_length=64)


class CitaNueva(BaseModel):
    sede: str
    motivo: str
    fecha: date
    hora: str
    expediente: str | None = None


class MensajeContacto(BaseModel):
    nombre: str
    email: EmailStr
    tema: str
    mensaje: str = Field(min_length=15, max_length=2000)
    expediente: str | None = None


# ------------------------------------------------------------------ catálogo
# Fuente: https://permisosycumplimiento.mupa.gob.pa/tramites-y-permisos/

PERMISOS = [
    {"id": "ESP-500-",  "nombre": "Espectáculo Público — menos de 500 personas",
     "categoria": "Espectáculos y eventos públicos", "dias": 15, "aforo": [1, 499]},
    {"id": "ESP-4000",  "nombre": "Espectáculo Público — menos de 4,000 personas",
     "categoria": "Espectáculos y eventos públicos", "dias": 20, "aforo": [500, 3999]},
    {"id": "ESP-500+",  "nombre": "Espectáculo Público — más de 500 personas",
     "categoria": "Espectáculos y eventos públicos", "dias": 25, "aforo": [500, 60000]},
    {"id": "NOC-A",     "nombre": "Permiso Nocturno Categoría A",
     "categoria": "Permisos nocturnos", "dias": 25, "aforo": None},
    {"id": "ACERA",     "nombre": "Uso Temporal de Aceras",
     "categoria": "Publicidad y uso de espacio público", "dias": 12, "aforo": None},
    # … el catálogo completo (35 trámites) vive en el frontend, en CATALOGO.
]
POR_ID = {p["id"]: p for p in PERMISOS}


# ------------------------------------------------------------------ sesión

def usuario_actual(authorization: str = Header(default="")) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    email = SESIONES.get(token)
    if not email:
        raise HTTPException(401, "Sesión no válida o expirada. Inicia sesión de nuevo.")
    return CUENTAS[email]


def hash_password(p: str, sal: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", p.encode(), sal.encode(), 240_000).hex()


# ------------------------------------------------------------------ métricas

@app.middleware("http")
async def medir(request: Request, call_next):
    inicio = time.perf_counter()
    respuesta = await call_next(request)
    ruta = request.scope.get("route").path if request.scope.get("route") else request.url.path
    metricas.peticiones_http.labels(request.method, ruta, respuesta.status_code).inc()
    metricas.latencia_http.labels(request.method, ruta).observe(time.perf_counter() - inicio)
    return respuesta


def refrescar_estados() -> None:
    for estado in ("Recibido", "En revisión", "Aprobado", "Subsanación", "Rechazado"):
        n = sum(1 for e in EXPEDIENTES if e["estado"] == estado)
        metricas.solicitudes_por_estado.labels(estado, MUNICIPIO).set(n)


@app.get("/metrics", include_in_schema=False)
def endpoint_metricas() -> Response:
    metricas.antivirus_arriba.set(1 if antivirus.ping() else 0)
    metricas.info_antivirus.info({"version": antivirus.version_firmas()})
    refrescar_estados()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/salud")
def salud() -> dict:
    av = antivirus.ping()
    return {
        "estado": "ok" if av else "degradado",
        "municipio": MUNICIPIO,
        "antivirus": {"arriba": av, "firmas": antivirus.version_firmas()},
        "expedientes": len(EXPEDIENTES),
        "bitacora": len(BITACORA),
    }


# ------------------------------------------------------------------ cuentas

@app.post("/api/cuentas", status_code=201)
def crear_cuenta(c: CuentaNueva) -> dict:
    correo = c.email.lower()
    if correo in CUENTAS:
        raise HTTPException(409, "Ya existe una cuenta con ese correo. Inicia sesión.")
    sal = secrets.token_hex(16)
    CUENTAS[correo] = {
        "nombre": c.nombre, "apellido": c.apellido, "edad": c.edad,
        "organizacion": c.organizacion, "email": correo, "cedula": c.cedula,
        "sal": sal, "clave": hash_password(c.password, sal),
        "creado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    registrar("cuenta.creada", correo, organizacion=c.organizacion)
    token = secrets.token_urlsafe(32)
    SESIONES[token] = correo
    return {"token": token, "usuario": _publico(CUENTAS[correo])}


@app.post("/api/sesiones")
def iniciar_sesion(c: Credenciales) -> dict:
    u = CUENTAS.get(c.email.lower())
    if not u or hash_password(c.password, u["sal"]) != u["clave"]:
        registrar("sesion.fallida", c.email.lower())
        raise HTTPException(401, "El correo o la contraseña no coinciden.")
    token = secrets.token_urlsafe(32)
    SESIONES[token] = u["email"]
    registrar("sesion.iniciada", u["email"])
    return {"token": token, "usuario": _publico(u)}


def _publico(u: dict) -> dict:
    return {k: v for k, v in u.items() if k not in ("clave", "sal")}


# ------------------------------------------------------------------ permisos

@app.get("/api/permisos")
def catalogo(categoria: str | None = None) -> list[dict]:
    return [p for p in PERMISOS if not categoria or p["categoria"] == categoria]


# ------------------------------------------------------------------ documentos

@app.post("/api/documentos/verificar")
async def verificar_documento(
    archivo: UploadFile = File(...),
    usuario: dict = Depends(usuario_actual),
) -> dict:
    """
    Éste es el paso 3 del portal. Recibe el PDF, lo pasa por ClamAV y devuelve
    la huella SHA-256 que después viaja en la solicitud. El archivo sólo se
    guarda si el veredicto es limpio.
    """
    contenido = await archivo.read()

    with metricas.cronometrar(metricas.duracion_escaneo):
        v = antivirus.verificar(contenido, archivo.filename or "")

    metricas.documentos_verificados.labels(v.resultado.value, MUNICIPIO).inc()

    if v.resultado is antivirus.Resultado.INFECTADO:
        metricas.amenazas_detectadas.labels(v.firma_virus or "desconocida", MUNICIPIO).inc()
        registrar("documento.infectado", usuario["email"],
                  archivo=archivo.filename, firma=v.firma_virus)
        raise HTTPException(422, v.mensaje)

    if not v.aceptado:
        registrar("documento.rechazado", usuario["email"],
                  archivo=archivo.filename, motivo=v.resultado.value)
        codigo = 503 if v.resultado is antivirus.Resultado.ANTIVIRUS_CAIDO else 400
        raise HTTPException(codigo, v.mensaje)

    # Deduplicación: el mismo PDF subido dos veces es un solo objeto almacenado.
    DOCUMENTOS[v.sha256] = {
        "nombre": archivo.filename,
        "bytes": v.bytes_,
        "sha256": v.sha256,
        "propietario": usuario["email"],
        "municipio": MUNICIPIO,
        "sellado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # En producción: ruta en el almacén de objetos (S3/MinIO) cifrado en reposo.
        "ubicacion": f"s3://mupa-{MUNICIPIO}-expedientes/{v.sha256[:2]}/{v.sha256}.pdf",
    }
    sello = registrar("documento.verificado", usuario["email"],
                      sha256=v.sha256, bytes=v.bytes_)

    return {
        "sha256": v.sha256,
        "bytes": v.bytes_,
        "nombre": archivo.filename,
        "sellado": DOCUMENTOS[v.sha256]["sellado"],
        "bitacora": sello["hash"],
        "mensaje": v.mensaje,
    }


# ------------------------------------------------------------------ solicitudes

@app.post("/api/solicitudes", status_code=201)
def crear_solicitud(s: SolicitudNueva, usuario: dict = Depends(usuario_actual)) -> dict:
    permiso = POR_ID.get(s.permiso_id)
    if not permiso:
        raise HTTPException(404, "El permiso solicitado no existe en el catálogo.")

    doc = DOCUMENTOS.get(s.documento_sha256)
    if not doc or doc["propietario"] != usuario["email"]:
        raise HTTPException(400, "Adjunta y verifica un documento antes de enviar la solicitud.")

    if (date.today() - s.fecha).days > 0:
        raise HTTPException(400, "La fecha del acto ya pasó.")
    if (s.fecha - date.today()).days < 15:
        raise HTTPException(400, "La fecha debe tener al menos 15 días hábiles de antelación.")

    rango = permiso.get("aforo")
    if rango and not (rango[0] <= s.aforo <= rango[1]):
        raise HTTPException(
            400,
            f"Para «{permiso['nombre']}» el aforo debe estar entre {rango[0]} y {rango[1]} personas.",
        )

    codigo = f"EXP-{date.today().year}-{len(EXPEDIENTES) + 4183:06d}"
    expediente = {
        "codigo": codigo,
        "municipio": MUNICIPIO,
        "permiso_id": permiso["id"],
        "permiso": permiso["nombre"],
        "solicitante": usuario["email"],
        "estado": "Recibido",
        "etapa": "En cola de asignación · Dirección de Permisos",
        "creado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plazo_dias": permiso["dias"],
        "documento": s.documento_sha256,
        **s.model_dump(mode="json"),
    }
    EXPEDIENTES.append(expediente)

    metricas.solicitudes_creadas.labels(permiso["nombre"], s.corregimiento, MUNICIPIO).inc()
    refrescar_estados()
    registrar("expediente.creado", usuario["email"], codigo=codigo, permiso=permiso["id"])

    return expediente


@app.get("/api/solicitudes")
def listar_solicitudes(
    estado: Literal["Recibido", "En revisión", "Aprobado", "Subsanación", "Rechazado"] | None = None,
    usuario: dict = Depends(usuario_actual),
) -> list[dict]:
    return [
        e for e in reversed(EXPEDIENTES)
        if e["solicitante"] == usuario["email"] and (not estado or e["estado"] == estado)
    ]


# ------------------------------------------------------------------ citas

@app.post("/api/citas", status_code=201)
def reservar_cita(c: CitaNueva, usuario: dict = Depends(usuario_actual)) -> dict:
    if c.fecha.weekday() >= 5:
        raise HTTPException(400, "La atención presencial es de lunes a viernes.")
    if any(x["sede"] == c.sede and x["fecha"] == c.fecha.isoformat() and x["hora"] == c.hora
           for x in CITAS):
        raise HTTPException(409, "Ese horario acaba de ocuparse. Elige otro turno.")

    turno = f"CT-{len(CITAS) + 1001:04d}"
    cita = {"turno": turno, "solicitante": usuario["email"], "municipio": MUNICIPIO,
            **c.model_dump(mode="json")}
    CITAS.append(cita)
    registrar("cita.reservada", usuario["email"], turno=turno, sede=c.sede)
    return cita


# ------------------------------------------------------------------ contacto

@app.post("/api/contacto", status_code=201)
def contacto(m: MensajeContacto) -> dict:
    ticket = f"MSG-{secrets.randbelow(900_000) + 100_000}"
    registrar("contacto.recibido", m.email.lower(), ticket=ticket, tema=m.tema)
    return {"ticket": ticket, "mensaje": "Respondemos en un plazo de 3 días hábiles."}


# ------------------------------------------------------------------ auditoría

@app.get("/api/bitacora/verificar")
def verificar_bitacora() -> dict:
    """Recorre la cadena de hashes y reporta la primera fila alterada."""
    previo = "0" * 64
    for e in BITACORA:
        cuerpo = f"{e['n']}{e['ts']}{e['accion']}{e['actor']}{e['datos']}{previo}"
        if hashlib.sha256(cuerpo.encode()).hexdigest() != e["hash"]:
            return {"integra": False, "rota_en": e["n"]}
        previo = e["hash"]
    return {"integra": True, "entradas": len(BITACORA)}
