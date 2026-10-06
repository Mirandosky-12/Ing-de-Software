"""
tablas.py — Esquema de la base de datos (SQLAlchemy 2).

Las reglas que no pueden fallar viven también en la base, no sólo en la API:
edad mínima, estados válidos, aforo, tamaño del PDF y un solo turno por
sede, fecha y hora. Si mañana otro programa escribe en la base, las reglas
siguen valiendo.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from seguridad import Cifrado

ESTADOS = ("Recibido", "En revisión", "Aprobado", "Subsanación", "Rechazado")
ROLES = ("ciudadano", "revisor", "director")


def _en(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


class MomentoUTC(TypeDecorator):
    """Fecha y hora siempre en UTC y con zona horaria, también en SQLite
    (que la pierde al guardar y devolvería fechas "ingenuas")."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, valor, dialect):
        if valor is None:
            return None
        if valor.tzinfo is None:
            raise ValueError("Fecha sin zona horaria: usa datetime.now(timezone.utc)")
        return valor.astimezone(timezone.utc)

    def process_result_value(self, valor, dialect):
        if valor is not None and valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor


class Base(DeclarativeBase):
    pass


class Cuenta(Base):
    __tablename__ = "cuentas"
    __table_args__ = (
        CheckConstraint("edad BETWEEN 18 AND 110", name="ck_cuentas_edad"),
        CheckConstraint(f"rol IN ({_en(ROLES)})", name="ck_cuentas_rol"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    nombre: Mapped[str] = mapped_column(String(60))
    apellido: Mapped[str] = mapped_column(String(60))
    edad: Mapped[int]
    organizacion: Mapped[str] = mapped_column(String(120))
    cedula: Mapped[str | None] = mapped_column(Cifrado())        # Ley 81: cifrada
    clave: Mapped[str] = mapped_column(String(200))              # pbkdf2_sha256$…
    rol: Mapped[str] = mapped_column(String(12), default="ciudadano")
    consentimiento_en: Mapped[datetime] = mapped_column(MomentoUTC())
    creado_en: Mapped[datetime] = mapped_column(MomentoUTC())


class Sesion(Base):
    __tablename__ = "sesiones"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id", ondelete="CASCADE"), index=True)
    creada_en: Mapped[datetime] = mapped_column(MomentoUTC())
    expira_en: Mapped[datetime] = mapped_column(MomentoUTC(), index=True)


class Permiso(Base):
    __tablename__ = "permisos"

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    categoria: Mapped[str] = mapped_column(String(80))
    dias: Mapped[int]
    aforo_min: Mapped[int | None]
    aforo_max: Mapped[int | None]
    requisitos: Mapped[list[str]] = mapped_column(JSON)


class Documento(Base):
    """Un PDF que pasó ClamAV. El archivo está en el almacén (almacen.py);
    aquí sólo va su huella y su ruta. El mismo PDF subido por dos personas
    son dos filas y un solo archivo."""

    __tablename__ = "documentos"
    __table_args__ = (
        UniqueConstraint("propietario_id", "sha256", name="uq_documentos_propietario_sha"),
        CheckConstraint("tamano > 0 AND tamano <= 10485760", name="ck_documentos_tamano"),
        CheckConstraint("length(sha256) = 64", name="ck_documentos_sha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    propietario_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"), index=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    nombre: Mapped[str] = mapped_column(String(255))
    tamano: Mapped[int]
    ruta: Mapped[str] = mapped_column(String(300))
    sellado_en: Mapped[datetime] = mapped_column(MomentoUTC())


class Expediente(Base):
    __tablename__ = "expedientes"
    __table_args__ = (
        CheckConstraint(f"estado IN ({_en(ESTADOS)})", name="ck_expedientes_estado"),
        CheckConstraint("aforo BETWEEN 1 AND 60000", name="ck_expedientes_aforo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str | None] = mapped_column(String(20), unique=True)   # se fija tras el INSERT
    municipio: Mapped[str] = mapped_column(String(40))
    permiso_id: Mapped[str] = mapped_column(ForeignKey("permisos.id"))
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"), index=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos.id"))
    estado: Mapped[str] = mapped_column(String(15), index=True)
    etapa: Mapped[str] = mapped_column(String(120))
    corregimiento: Mapped[str] = mapped_column(String(60))
    tipo_acto: Mapped[str] = mapped_column(String(80))
    lugar: Mapped[str] = mapped_column(String(200))
    fecha_acto: Mapped[date] = mapped_column(Date)
    hora_inicio: Mapped[str] = mapped_column(String(5))
    hora_fin: Mapped[str] = mapped_column(String(5))
    aforo: Mapped[int]
    responsable: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str] = mapped_column(String(30))
    motivo: Mapped[str] = mapped_column(String(600))
    plazo_dias: Mapped[int]
    declaracion_jurada_en: Mapped[datetime] = mapped_column(MomentoUTC())   # Acuerdo 130/2016
    creado_en: Mapped[datetime] = mapped_column(MomentoUTC())

    permiso: Mapped[Permiso] = relationship()
    solicitante: Mapped[Cuenta] = relationship()
    documento: Mapped[Documento] = relationship()


class Historial(Base):
    """Cada cambio de estado de un expediente. Sólo se agregan filas."""

    __tablename__ = "historial"

    id: Mapped[int] = mapped_column(primary_key=True)
    expediente_id: Mapped[int] = mapped_column(ForeignKey("expedientes.id"), index=True)
    estado: Mapped[str] = mapped_column(String(15))
    etapa: Mapped[str] = mapped_column(String(120))
    actor_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"))
    comentario: Mapped[str | None] = mapped_column(Text)
    en: Mapped[datetime] = mapped_column(MomentoUTC())


class Cita(Base):
    __tablename__ = "citas"
    __table_args__ = (UniqueConstraint("sede", "fecha", "hora", name="uq_citas_turno"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    turno: Mapped[str | None] = mapped_column(String(10), unique=True)     # se fija tras el INSERT
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("cuentas.id"), index=True)
    municipio: Mapped[str] = mapped_column(String(40))
    sede: Mapped[str] = mapped_column(String(80))
    motivo: Mapped[str] = mapped_column(String(120))
    fecha: Mapped[date] = mapped_column(Date)
    hora: Mapped[str] = mapped_column(String(5))
    expediente: Mapped[str | None] = mapped_column(String(200))
    creada_en: Mapped[datetime] = mapped_column(MomentoUTC())

    solicitante: Mapped[Cuenta] = relationship()


class Bitacora(Base):
    """Auditoría encadenada: cada fila lleva el hash de la anterior. La base
    impide UPDATE y DELETE (triggers en migrar.py) y el rol de la API sólo
    tiene permiso de INSERT y SELECT."""

    __tablename__ = "bitacora"

    n: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    ts: Mapped[str] = mapped_column(String(32))          # texto ISO: lo que se hashea, tal cual
    municipio: Mapped[str] = mapped_column(String(40))
    accion: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(254))
    datos: Mapped[str] = mapped_column(Text)             # JSON canónico
    previo: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)
