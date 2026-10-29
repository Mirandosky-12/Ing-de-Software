"""
repositorio.py — Todo el acceso a datos de la API.

main.py no escribe SQL ni toca tablas: llama a estas funciones. Ninguna hace
commit; lo decide la ruta que las llama, para que una operación y su entrada
en la bitácora se confirmen juntas.
"""


from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import seguridad
from tablas import (
    ESTADOS, Bitacora, Cita, Cuenta, Documento, Expediente, Historial, Permiso, Sesion,
)

MUNICIPIO = os.getenv("MUNICIPIO", "panama")
SESION_HORAS = float(os.getenv("SESION_HORAS", "8"))
ETAPA_INICIAL = "En cola de asignación · Dirección de Permisos"

# La etapa que se le muestra al solicitante en cada estado. En Subsanación la
# reemplaza el comentario del revisor: ahí lo útil es saber QUÉ falta.
ETAPAS = {
    "Recibido":    ETAPA_INICIAL,
    "En revisión": "Revisión técnica · Dirección de Permisos",
    "Subsanación": "Pendiente de subsanación por el solicitante",
    "Aprobado":    "Permiso emitido · descargable en ventanilla",
    "Rechazado":   "Resolución negativa notificada al solicitante",
}

# Por dónde puede avanzar un expediente. Aprobado y Rechazado son finales:
# una resolución no se deshace, se recurre. Esto no es cosmética de la
# interfaz, lo impone la API, que es quien escribe en la base.
TRANSICIONES = {
    "Recibido":    ("En revisión", "Rechazado"),
    "En revisión": ("Aprobado", "Subsanación", "Rechazado"),
    "Subsanación": ("En revisión", "Rechazado"),
    "Aprobado":    (),
    "Rechazado":   (),
}

# Un «no» o un «le falta algo» sin explicación no es una resolución.
EXIGEN_COMENTARIO = ("Subsanación", "Rechazado")
_CERO = "0" * 64


class Duplicado(Exception):
    """Ya existe una cuenta con ese correo."""


class TransicionInvalida(Exception):
    """Ese expediente no puede pasar a ese estado desde donde está."""

    def __init__(self, desde: str, hacia: str):
        self.desde, self.hacia = desde, hacia
        super().__init__(f"Un expediente «{desde}» no puede pasar a «{hacia}».")


class TurnoOcupado(Exception):
    """Otra persona tomó esa sede, fecha y hora."""


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ bitácora

def _canonico(valor) -> str:
    """JSON con claves ordenadas y sin espacios: el mismo dato produce siempre
    el mismo texto, se lea de SQLite, de PostgreSQL o de un respaldo."""
    return json.dumps(valor, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)


def _huella(n: int, ts: str, municipio: str, accion: str, actor: str,
            datos: str, previo: str) -> str:
    cuerpo = _canonico({"n": n, "ts": ts, "municipio": municipio, "accion": accion,
                        "actor": actor, "datos": datos, "previo": previo})
    return hashlib.sha256(cuerpo.encode()).hexdigest()


def registrar(s: Session, accion: str, actor: str, **datos) -> Bitacora:
    if s.get_bind().dialect.name == "postgresql":
        # Dos peticiones a la vez no pueden leer el mismo "último hash":
        # este candado dura hasta el commit de la transacción.
        s.execute(text("SELECT pg_advisory_xact_lock(4183)"))
    ultima = s.scalars(select(Bitacora).order_by(Bitacora.n.desc()).limit(1)).first()
    n = ultima.n + 1 if ultima else 1
    previo = ultima.hash if ultima else _CERO
    ts = _ahora().isoformat(timespec="seconds")
    datos_json = _canonico(datos)
    entrada = Bitacora(
        n=n, ts=ts, municipio=MUNICIPIO, accion=accion, actor=actor, datos=datos_json,
        previo=previo, hash=_huella(n, ts, MUNICIPIO, accion, actor, datos_json, previo),
    )
    s.add(entrada)
    s.flush()
    return entrada


def verificar_bitacora(s: Session) -> dict:
    """Recorre la cadena y reporta la primera fila alterada o faltante."""
    previo, total = _CERO, 0
    for e in s.scalars(select(Bitacora).order_by(Bitacora.n)):
        esperado = _huella(e.n, e.ts, e.municipio, e.accion, e.actor, e.datos, e.previo)
        if e.n != total + 1 or e.previo != previo or esperado != e.hash:
            return {"integra": False, "rota_en": e.n}
        previo, total = e.hash, total + 1
    return {"integra": True, "entradas": total}


def total_bitacora(s: Session) -> int:
    return s.scalar(select(func.count()).select_from(Bitacora))


# ------------------------------------------------------------------ cuentas y sesiones

def cuenta_por_email(s: Session, email: str) -> Cuenta | None:
    return s.scalars(select(Cuenta).where(Cuenta.email == email.lower())).first()


def crear_cuenta(s: Session, *, nombre: str, apellido: str, edad: int, organizacion: str,
                 email: str, cedula: str | None, password: str) -> Cuenta:
    if cuenta_por_email(s, email):
        raise Duplicado
    ahora = _ahora()
    cuenta = Cuenta(
        email=email.lower(), nombre=nombre, apellido=apellido, edad=edad,
        organizacion=organizacion, cedula=cedula, clave=seguridad.cifrar_clave(password),
        rol="ciudadano", consentimiento_en=ahora, creado_en=ahora,
    )
    s.add(cuenta)
    try:
        s.flush()
    except IntegrityError:          # dos registros simultáneos con el mismo correo
        s.rollback()
        raise Duplicado from None
    return cuenta


def abrir_sesion(s: Session, cuenta: Cuenta) -> str:
    """Crea la sesión y devuelve el token. En la base sólo queda su huella."""
    ahora = _ahora()
    s.execute(delete(Sesion).where(Sesion.expira_en <= ahora))     # limpieza de paso
    token, huella = seguridad.nuevo_token()
    s.add(Sesion(token_hash=huella, cuenta_id=cuenta.id, creada_en=ahora,
                 expira_en=ahora + timedelta(hours=SESION_HORAS)))
    s.flush()
    return token


def cuenta_por_token(s: Session, token: str) -> Cuenta | None:
    if not token:
        return None
    sesion = s.get(Sesion, seguridad.huella_token(token))
    if sesion is None:
        return None
    if sesion.expira_en <= _ahora():
        s.delete(sesion)
        s.commit()
        return None
    return s.get(Cuenta, sesion.cuenta_id)


def cerrar_sesion(s: Session, token: str) -> None:
    s.execute(delete(Sesion).where(Sesion.token_hash == seguridad.huella_token(token)))


def publico(c: Cuenta) -> dict:
    return {
        "nombre": c.nombre, "apellido": c.apellido, "edad": c.edad,
        "organizacion": c.organizacion, "email": c.email, "cedula": c.cedula,
        "rol": c.rol, "creado": c.creado_en.isoformat(timespec="seconds"),
    }


# ------------------------------------------------------------------ catálogo

def permisos(s: Session, categoria: str | None = None) -> list[Permiso]:
    consulta = select(Permiso).order_by(Permiso.categoria, Permiso.nombre)
    if categoria:
        consulta = consulta.where(Permiso.categoria == categoria)
    return list(s.scalars(consulta))


def permiso(s: Session, permiso_id: str) -> Permiso | None:
    return s.get(Permiso, permiso_id)


def permiso_a_dict(p: Permiso) -> dict:
    return {
        "id": p.id, "nombre": p.nombre, "categoria": p.categoria, "dias": p.dias,
        "aforo": [p.aforo_min, p.aforo_max] if p.aforo_min is not None else None,
        "requisitos": p.requisitos,
    }


# ------------------------------------------------------------------ documentos

def guardar_documento(s: Session, propietario: Cuenta, sha256: str, nombre: str,
                      tamano: int, ruta: str) -> Documento:
    """Registra el PDF para esta cuenta. Si ya lo había subido, devuelve el
    registro existente; si lo subió otra persona, cada una tiene el suyo."""
    doc = documento_de(s, propietario.id, sha256)
    if doc is None:
        doc = Documento(propietario_id=propietario.id, sha256=sha256, nombre=nombre,
                        tamano=tamano, ruta=ruta, sellado_en=_ahora())
        s.add(doc)
        s.flush()
    return doc


def documento_de(s: Session, propietario_id: int, sha256: str) -> Documento | None:
    return s.scalars(select(Documento).where(
        Documento.propietario_id == propietario_id, Documento.sha256 == sha256)).first()


# ------------------------------------------------------------------ expedientes

def crear_expediente(s: Session, cuenta: Cuenta, permiso_: Permiso, documento: Documento,
                     d: dict) -> Expediente:
    ahora = _ahora()
    e = Expediente(
        municipio=MUNICIPIO, permiso_id=permiso_.id, solicitante_id=cuenta.id,
        documento_id=documento.id, estado="Recibido", etapa=ETAPA_INICIAL,
        corregimiento=d["corregimiento"], tipo_acto=d["tipo_acto"], lugar=d["lugar"],
        fecha_acto=d["fecha"], hora_inicio=d["hora_inicio"], hora_fin=d["hora_fin"],
        aforo=d["aforo"], responsable=d["responsable"], telefono=d["telefono"],
        motivo=d["motivo"], plazo_dias=permiso_.dias,
        declaracion_jurada_en=ahora, creado_en=ahora,
    )
    s.add(e)
    s.flush()                                        # ya tiene id
    e.codigo = f"EXP-{ahora.year}-{e.id + 4182:06d}"
    s.add(Historial(expediente_id=e.id, estado=e.estado, etapa=e.etapa,
                    actor_id=cuenta.id, en=ahora))
    s.flush()
    return e


def expedientes_de(s: Session, cuenta: Cuenta, estado: str | None = None) -> list[Expediente]:
    consulta = (select(Expediente).where(Expediente.solicitante_id == cuenta.id)
                .order_by(Expediente.id.desc()))
    if estado:
        consulta = consulta.where(Expediente.estado == estado)
    return list(s.scalars(consulta))


def expediente_de(s: Session, cuenta: Cuenta, codigo: str) -> Expediente | None:
    """Sólo el expediente del propio solicitante: uno ajeno es igual a uno inexistente."""
    return s.scalars(select(Expediente).where(Expediente.codigo == codigo,
                                              Expediente.solicitante_id == cuenta.id)).first()


def sello_de(s: Session, codigo: str) -> Bitacora | None:
    """La entrada «expediente.creado» de la bitácora que selló este expediente."""
    marca = _canonico({"codigo": codigo})[1:-1]          # '"codigo":"EXP-…"', tal como se guarda
    return s.scalars(select(Bitacora)
                     .where(Bitacora.accion == "expediente.creado",
                            Bitacora.datos.contains(marca, autoescape=True))
                     .order_by(Bitacora.n).limit(1)).first()


def expedientes_todos(s: Session, estado: str | None = None,
                      corregimiento: str | None = None,
                      texto: str | None = None) -> list[Expediente]:
    """La bandeja del funcionario: los expedientes de todos los solicitantes.
    Sólo la llaman las rutas que ya comprobaron el rol."""
    consulta = select(Expediente).order_by(Expediente.id.desc())
    if estado:
        consulta = consulta.where(Expediente.estado == estado)
    if corregimiento:
        consulta = consulta.where(Expediente.corregimiento == corregimiento)
    if texto:
        patron = f"%{texto.lower()}%"
        consulta = consulta.where(or_(
            func.lower(Expediente.codigo).like(patron),
            func.lower(Expediente.lugar).like(patron),
            func.lower(Expediente.responsable).like(patron),
        ))
    return list(s.scalars(consulta))


def expediente_por_codigo(s: Session, codigo: str) -> Expediente | None:
    """Sin filtrar por solicitante: es para el funcionario que revisa."""
    return s.scalars(select(Expediente).where(Expediente.codigo == codigo)).first()


def corregimientos_con_expedientes(s: Session) -> list[str]:
    return sorted(c for c in s.scalars(select(Expediente.corregimiento).distinct()) if c)


def cambiar_estado(s: Session, expediente: Expediente, funcionario: Cuenta,
                   estado: str, comentario: str | None = None) -> Expediente:
    """Mueve el expediente y deja la huella de quién lo movió. El historial es
    de sólo anexado: la decisión anterior no se borra, se encadena."""
    if estado not in TRANSICIONES.get(expediente.estado, ()):
        raise TransicionInvalida(expediente.estado, estado)

    comentario = (comentario or "").strip() or None
    etapa = comentario if (estado == "Subsanación" and comentario) else ETAPAS[estado]
    expediente.estado = estado
    expediente.etapa = etapa[:120]
    s.add(Historial(expediente_id=expediente.id, estado=estado, etapa=expediente.etapa,
                    actor_id=funcionario.id, comentario=comentario, en=_ahora()))
    s.flush()
    return expediente


def historial_a_dicts(s: Session, expediente: Expediente) -> list[dict]:
    """El historial con el correo y el rol de quien hizo cada movimiento."""
    filas = s.execute(
        select(Historial, Cuenta.email, Cuenta.rol)
        .join(Cuenta, Cuenta.id == Historial.actor_id)
        .where(Historial.expediente_id == expediente.id)
        .order_by(Historial.id)
    )
    return [{"estado": h.estado, "etapa": h.etapa, "comentario": h.comentario,
             "en": h.en.isoformat(timespec="seconds"), "actor": correo, "rol": rol}
            for h, correo, rol in filas]


def historial_de(s: Session, expediente: Expediente) -> list[Historial]:
    return list(s.scalars(select(Historial).where(Historial.expediente_id == expediente.id)
                          .order_by(Historial.id)))


def conteo_por_estado(s: Session) -> dict[str, int]:
    filas = s.execute(select(Expediente.estado, func.count()).group_by(Expediente.estado))
    conteo = dict.fromkeys(ESTADOS, 0)
    conteo.update({estado: n for estado, n in filas})
    return conteo


def total_expedientes(s: Session) -> int:
    return s.scalar(select(func.count()).select_from(Expediente))


def expediente_a_dict(e: Expediente) -> dict:
    return {
        "codigo": e.codigo, "municipio": e.municipio,
        "permiso_id": e.permiso_id, "permiso": e.permiso.nombre,
        "solicitante": e.solicitante.email, "estado": e.estado, "etapa": e.etapa,
        "creado": e.creado_en.isoformat(timespec="seconds"), "plazo_dias": e.plazo_dias,
        "documento": e.documento.sha256, "documento_sha256": e.documento.sha256,
        "corregimiento": e.corregimiento, "tipo_acto": e.tipo_acto, "lugar": e.lugar,
        "fecha": e.fecha_acto.isoformat(), "hora_inicio": e.hora_inicio,
        "hora_fin": e.hora_fin, "aforo": e.aforo, "responsable": e.responsable,
        "telefono": e.telefono, "motivo": e.motivo,
    }


# ------------------------------------------------------------------ citas

def reservar_cita(s: Session, cuenta: Cuenta, d: dict) -> Cita:
    """La restricción única (sede, fecha, hora) de la base es la que decide:
    si dos personas reservan a la vez, una de las dos recibe TurnoOcupado."""
    cita = Cita(solicitante_id=cuenta.id, municipio=MUNICIPIO, sede=d["sede"],
                motivo=d["motivo"], fecha=d["fecha"], hora=d["hora"],
                expediente=d.get("expediente"), creada_en=_ahora())
    s.add(cita)
    try:
        s.flush()
    except IntegrityError:
        s.rollback()
        raise TurnoOcupado from None
    cita.turno = f"CT-{cita.id + 1000:04d}"
    s.flush()
    return cita


def citas_de(s: Session, cuenta: Cuenta, desde: date | None = None) -> list[Cita]:
    """Las citas del propio solicitante, de la más próxima a la más lejana.
    Con `desde` quedan fuera las que ya pasaron: es lo que el portal muestra
    al entrar. Las de otro solicitante no se devuelven nunca."""
    consulta = select(Cita).where(Cita.solicitante_id == cuenta.id)
    if desde:
        consulta = consulta.where(Cita.fecha >= desde)
    return list(s.scalars(consulta.order_by(Cita.fecha, Cita.hora)))


def horas_ocupadas(s: Session, sede: str, fecha: date) -> list[str]:
    """Las horas ya reservadas en esa sede ese día, de todos los solicitantes.
    Es lo que sostiene la restricción uq_citas_turno (sede, fecha, hora): la
    base sigue siendo la que decide, esto sólo evita que el portal ofrezca un
    turno que ya no está."""
    return list(s.scalars(
        select(Cita.hora).where(Cita.sede == sede, Cita.fecha == fecha).order_by(Cita.hora)
    ))


def cita_a_dict(c: Cita) -> dict:
    return {
        "turno": c.turno, "solicitante": c.solicitante.email, "municipio": c.municipio,
        "sede": c.sede, "motivo": c.motivo, "fecha": c.fecha.isoformat(),
        "hora": c.hora, "expediente": c.expediente,
    }
