# Base de datos segura para la Ventanilla Única — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar el almacenamiento en memoria de la API por una base de datos real, protegida y persistente, con imágenes Docker livianas.

**Architecture:** SQLAlchemy 2 sobre SQLite en desarrollo y PostgreSQL 17 en Docker; el código es el mismo y sólo cambia `DATABASE_URL`. Todo el acceso a datos pasa por `repositorio.py`; `main.py` deja de tener listas en memoria. La seguridad va en capas: dos roles con mínimo privilegio, triggers de sólo anexado para la auditoría, cifrado de la cédula con la clave fuera de la base, tokens y contraseñas guardados como hash, y la base aislada en una red interna de Docker.

**Tech Stack:** Python 3.13 · FastAPI 0.115 · SQLAlchemy 2.1.1 · psycopg 3.3.6 · cryptography 50.0.1 · PostgreSQL 17 (`postgres:17-alpine`) · Docker Compose · pytest.

**Spec:** [portal-permisos/README.md](../../../portal-permisos/README.md) (el sistema) y el esquema de ocho tablas acordado: `cuentas`, `sesiones`, `permisos`, `documentos`, `expedientes`, `historial`, `citas` y `bitacora`.

**Rama sugerida:** `base-de-datos`, creada desde `proyecto_municipal`.

## Estado de la validación

El código de las tareas 1 a 7 se ejecutó completo antes de escribir este plan, aplicando las tareas en orden sobre una copia limpia del repositorio con Python 3.13. Los conteos de pruebas de cada paso son los que se obtuvieron.

Las tareas 8 y 9 (PostgreSQL y Docker) **no se pudieron ejecutar**: Docker Desktop no estaba corriendo y no había PostgreSQL instalado. Sí se comprobó lo siguiente:
- `docker compose config` valida el compose;
- las etiquetas de imagen existen en Docker Hub;
- todas las dependencias tienen paquete precompilado para Alpine (`musllinux`), con sus bibliotecas nativas incluidas;
- el generador de secretos produce una clave Fernet válida.

Si algo falla en esas dos tareas, se corrige ahí y se anota en el commit.

## Global Constraints

- Python **3.13** en el entorno local (`py -3.13 -m venv .venv`) y en la imagen (`python:3.13-alpine`). Las versiones fijadas no tienen paquetes para 3.14.
- Versiones exactas: `SQLAlchemy==2.1.1`, `psycopg[binary]==3.3.6`, `cryptography==50.0.1`; el resto queda como está en `requirements.txt`.
- `uvicorn` va **sin** `[standard]` en la imagen: el extra agrega `watchfiles`, `uvloop` y más, que no hacen falta en producción.
- Todo acceso a datos por SQLAlchemy con parámetros. Nunca SQL armado con f-strings a partir de datos del usuario. Las únicas f-strings SQL permitidas son las constantes DDL de `migrar.py`.
- No hay commit automático: cada ruta llama a `s.commit()`. Si un error debe quedar en la bitácora (inicio de sesión fallido, documento rechazado), se hace commit **antes** del `raise HTTPException`.
- Los textos que ve el usuario no cambian; las pruebas buscan frases como «no coinciden», «15 días hábiles», «aforo debe estar entre», «10 MB» y «no es un PDF válido».
- Las respuestas JSON de las rutas existentes conservan sus claves (`codigo`, `estado`, `sha256`, `token`, `usuario`…).
- Nunca van a git: `monitoreo/secretos/`, `backend/mupa.db*`, `backend/almacen/`, `.env`.
- Imagen de la API: **≤ 120 MB**, sin pip, usuario no-root (uid 10001), sistema de archivos de sólo lectura.
- Estilo del código existente: nombres y comentarios en español y separadores `# ------------------------------------------------------------------ sección`.
- Cada commit termina con la línea `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Un nombre de archivo de más de 255 caracteres.** SQLite no hace cumplir el largo de `documentos.nombre`, pero PostgreSQL sí, y respondería con un 500. La API recorta el nombre. Lo prueba `test_un_nombre_de_archivo_larguisimo_se_recorta` (Tarea 7).
2. **Un escaneo de ClamAV lento con una transacción abierta.** `usuario_actual` lee la sesión y deja la transacción abierta; `idle_in_transaction_session_timeout = 30s` la cortaría a mitad del escaneo. `usuario_actual` hace commit después de leer. Lo prueba `test_validar_la_sesion_no_deja_una_transaccion_abierta` (Tarea 7).
3. **Dos registros simultáneos con el mismo correo en PostgreSQL.** Deben dar 409, no 500. La restricción única decide y `crear_cuenta` lo traduce a `Duplicado`. Lo prueba `test_dos_registros_simultaneos_con_el_mismo_correo` (Tarea 8).
4. **`01-roles.sh` con finales de línea de Windows.** Este equipo tiene `core.autocrlf=true`; el script llegaría con CRLF y PostgreSQL no arrancaría. Lo resuelve `.gitattributes` (Tarea 1) y lo verifica `git ls-files --eol` (Tarea 8).
5. **Un volumen `datos-bd` de un intento anterior con secretos nuevos.** `01-roles.sh` sólo corre con el volumen vacío, así que `migraciones` falla con «password authentication failed». Lo cubren el paso de verificación de la Tarea 9 y la nota del README.

---

### Task 1: Entorno con Python 3.13, dependencias y línea base

**Files:**
- Modify: `portal-permisos/backend/requirements.txt`
- Create: `portal-permisos/backend/requirements-dev.txt`
- Create: `portal-permisos/backend/pytest.ini`
- Create: `portal-permisos/.gitignore`
- Create: `.gitattributes` (raíz del repositorio)
- Modify: `portal-permisos/backend/test_api.py` (agrega VUM-25)

**Interfaces:**
- Produces: el entorno `.venv` con todas las dependencias, y los marcadores de pytest `clamav` y `postgres`.

- [ ] **Step 1: Crear el entorno y comprobar la línea base**

Desde `portal-permisos/backend`, en PowerShell:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

Expected: `13 passed, 2 skipped`, con avisos `PytestUnknownMarkWarning: Unknown pytest.mark.clamav`.

- [ ] **Step 2: Separar las dependencias de ejecución y las de pruebas**

Reemplaza `portal-permisos/backend/requirements.txt` completo (sólo lo que necesita la imagen):

```text
fastapi==0.115.6
uvicorn==0.34.0
pydantic[email]==2.10.4
python-multipart==0.0.20
clamd==1.0.2
prometheus-client==0.21.1
SQLAlchemy==2.1.1
psycopg[binary]==3.3.6
cryptography==50.0.1
```

Crea `portal-permisos/backend/requirements-dev.txt`:

```text
-r requirements.txt

# pruebas
pytest==8.3.4
httpx==0.28.1
qase-pytest==6.2.1
```

Crea `portal-permisos/backend/pytest.ini`:

```ini
[pytest]
markers =
    clamav: requiere el demonio clamd (docker compose up -d clamav)
    postgres: requiere la base de pruebas (docker compose --profile pruebas up -d bd-pruebas)
```

Instala: `pip install -r requirements-dev.txt`

- [ ] **Step 3: Evitar que datos locales o secretos entren a git**

Crea `portal-permisos/.gitignore`:

```text
# Python
__pycache__/
.venv/
.pytest_cache/

# Datos locales: nunca al repositorio
backend/mupa.db
backend/mupa.db-*
backend/almacen/
monitoreo/secretos/
.env
```

Crea `.gitattributes` en la raíz del repositorio (junto al `README.md` principal):

```text
# Lo que corre dentro de contenedores Linux necesita finales de línea LF,
# aunque se edite en Windows (con core.autocrlf=true git los pasaría a CRLF
# y PostgreSQL no podría ejecutar el script de roles).
*.sh        text eol=lf
Dockerfile  text eol=lf
```

- [ ] **Step 4: Agregar la prueba de VUM-25 (ClamAV caído → 503)**

En `portal-permisos/backend/test_api.py`, justo después de `test_sin_sesion_no_se_puede_subir`, agrega:

```python
@qase.id(25)
@qase.title("Si ClamAV está caído, no se acepta el documento")
def test_antivirus_caido_devuelve_503(cabecera, monkeypatch):
    def sin_conexion():
        raise ConnectionRefusedError("clamd no responde")
    monkeypatch.setattr(main.antivirus, "_cliente", sin_conexion)
    r = _subir(PDF_OK, "requisitos.pdf", cabecera)
    assert r.status_code == 503
    assert "no está disponible" in r.json()["detail"]
```

La conducta ya existe, así que esta prueba debe **pasar**. Si falla, hay un error en `antivirus.py`: detente y revísalo antes de seguir.

- [ ] **Step 5: Correr la suite**

Run: `pytest -q`
Expected: `14 passed, 2 skipped`, sin avisos de marcadores desconocidos.

- [ ] **Step 6: Commit**

```bash
git add .gitattributes portal-permisos/.gitignore portal-permisos/backend/requirements.txt portal-permisos/backend/requirements-dev.txt portal-permisos/backend/pytest.ini portal-permisos/backend/test_api.py
git commit -m "chore: entorno Python 3.13, dependencias de BD y prueba VUM-25" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Seguridad — contraseñas, tokens y cifrado de columnas

**Files:**
- Create: `portal-permisos/backend/seguridad.py`
- Create: `portal-permisos/backend/conftest.py` (sólo las variables de entorno; la Tarea 3 lo completa)
- Test: `portal-permisos/backend/test_seguridad.py`

**Interfaces:**
- Produces:
  - `cifrar_clave(password: str) -> str`, con formato `pbkdf2_sha256$<iter>$<sal>$<hash>`
  - `verificar_clave(password: str, guardada: str) -> bool`
  - `CLAVE_FALSA: str`
  - `huella_token(token: str) -> str`, un SHA-256 hex de 64 caracteres
  - `nuevo_token() -> tuple[str, str]`, que devuelve `(token, huella)`
  - `comprobar_clave() -> None`, que lanza `RuntimeError` si falta la clave
  - `Cifrado`, un `TypeDecorator` de texto cifrado
  - `ITERACIONES: int`, tomado de `PBKDF2_ITER` (600 000 por defecto)

- [ ] **Step 1: Escribir las pruebas**

Crea `portal-permisos/backend/conftest.py`:

```python
"""
conftest.py — Preparación común de las pruebas.

Por ahora sólo fija el entorno; la Tarea 3 agrega la base de datos de prueba.
"""

import os

# Antes de importar la aplicación: pocas iteraciones para que las pruebas
# vayan rápido y una clave de cifrado desechable.
os.environ.setdefault("PBKDF2_ITER", "1000")
from cryptography.fernet import Fernet  # noqa: E402

os.environ.setdefault("CLAVE_CIFRADO", Fernet.generate_key().decode())
```

Crea `portal-permisos/backend/test_seguridad.py`:

```python
"""Pruebas de seguridad.py: contraseñas, tokens y clave de cifrado."""

import pytest
from cryptography.fernet import Fernet

import seguridad


def test_la_clave_se_verifica_y_una_equivocada_no():
    guardada = seguridad.cifrar_clave("clave-de-prueba")
    assert seguridad.verificar_clave("clave-de-prueba", guardada)
    assert not seguridad.verificar_clave("otra-clave", guardada)


def test_la_clave_guardada_lleva_algoritmo_iteraciones_y_sal_propia():
    a = seguridad.cifrar_clave("igual")
    b = seguridad.cifrar_clave("igual")
    assert a.startswith(f"pbkdf2_sha256${seguridad.ITERACIONES}$")
    assert a != b                                    # sal distinta en cada cuenta
    assert "igual" not in a


@pytest.mark.parametrize("guardada", ["", "texto-plano", "md5$1$a$b", "pbkdf2_sha256$x$a$b"])
def test_una_clave_guardada_malformada_no_da_acceso(guardada):
    assert seguridad.verificar_clave("lo-que-sea", guardada) is False


def test_el_token_no_se_parece_a_su_huella():
    token, huella = seguridad.nuevo_token()
    assert len(huella) == 64 and token not in huella
    assert seguridad.huella_token(token) == huella


def test_el_cifrado_de_columnas_ida_y_vuelta():
    columna = seguridad.Cifrado()
    cifrado = columna.process_bind_param("8-912-345", None)
    assert cifrado != "8-912-345" and "912" not in cifrado
    assert columna.process_result_value(cifrado, None) == "8-912-345"
    assert columna.process_bind_param(None, None) is None


def test_sin_clave_de_cifrado_no_se_arranca(monkeypatch):
    monkeypatch.delenv("CLAVE_CIFRADO", raising=False)
    monkeypatch.delenv("CLAVE_CIFRADO_FILE", raising=False)
    seguridad._fernet.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="CLAVE_CIFRADO"):
            seguridad.comprobar_clave()
    finally:
        monkeypatch.undo()
        seguridad._fernet.cache_clear()


def test_la_clave_de_cifrado_se_puede_leer_de_un_archivo(tmp_path, monkeypatch):
    archivo = tmp_path / "clave.txt"
    archivo.write_text(Fernet.generate_key().decode() + "\n", encoding="utf-8")
    monkeypatch.setenv("CLAVE_CIFRADO_FILE", str(archivo))
    seguridad._fernet.cache_clear()
    try:
        seguridad.comprobar_clave()
    finally:
        monkeypatch.undo()
        seguridad._fernet.cache_clear()
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest test_seguridad.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'seguridad'`

- [ ] **Step 3: Implementar**

Crea `portal-permisos/backend/seguridad.py`:

```python
"""
seguridad.py — Lo que protege los datos si alguien se lleva una copia de la base.

  · Contraseñas: PBKDF2-SHA256, sal propia por cuenta, 600 000 iteraciones
    (recomendación OWASP). El formato guarda las iteraciones, así se pueden
    subir más adelante sin invalidar las claves existentes.
  · Tokens de sesión: la base guarda su SHA-256, nunca el token. Una copia de
    la tabla de sesiones no sirve para entrar.
  · Cédula: cifrada con Fernet (AES + HMAC). La clave vive FUERA de la base,
    en CLAVE_CIFRADO o en el archivo que indique CLAVE_CIFRADO_FILE.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from functools import lru_cache

from cryptography.fernet import Fernet
from sqlalchemy.types import String, TypeDecorator

ITERACIONES = int(os.getenv("PBKDF2_ITER", "600000"))


# ------------------------------------------------------------------ contraseñas

def cifrar_clave(password: str) -> str:
    sal = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), sal.encode(), ITERACIONES).hex()
    return f"pbkdf2_sha256${ITERACIONES}${sal}${h}"


def verificar_clave(password: str, guardada: str) -> bool:
    try:
        algoritmo, iteraciones, sal, h = guardada.split("$")
        iteraciones = int(iteraciones)
    except ValueError:
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    calculada = hashlib.pbkdf2_hmac("sha256", password.encode(), sal.encode(), iteraciones).hex()
    return hmac.compare_digest(calculada, h)


# Se verifica contra esta clave cuando el correo no existe, para que la
# respuesta tarde lo mismo y no delate qué correos están registrados.
CLAVE_FALSA = cifrar_clave(secrets.token_urlsafe(16))


# ------------------------------------------------------------------ sesiones

def huella_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def nuevo_token() -> tuple[str, str]:
    """Devuelve (token para el navegador, huella para la base)."""
    token = secrets.token_urlsafe(32)
    return token, huella_token(token)


# ------------------------------------------------------------------ cifrado de columnas

@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    archivo = os.getenv("CLAVE_CIFRADO_FILE")
    if archivo:
        with open(archivo, encoding="utf-8") as f:
            clave = f.read().strip()
    else:
        clave = os.getenv("CLAVE_CIFRADO", "")
    if not clave:
        raise RuntimeError(
            "Falta CLAVE_CIFRADO (o CLAVE_CIFRADO_FILE). Genera una con:\n"
            '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(clave.encode())


def comprobar_clave() -> None:
    """Se llama al arrancar: mejor no levantar que guardar datos sin cifrar."""
    _fernet()


class Cifrado(TypeDecorator):
    """Columna de texto que se cifra al escribir y se descifra al leer."""

    impl = String(500)
    cache_ok = True

    def process_bind_param(self, valor, dialect):
        return None if valor is None else _fernet().encrypt(valor.encode()).decode()

    def process_result_value(self, valor, dialect):
        return None if valor is None else _fernet().decrypt(valor.encode()).decode()
```

- [ ] **Step 4: Verificar que pasan**

Run: `pytest test_seguridad.py -q` → `10 passed`
Run: `pytest -q` → `24 passed, 2 skipped`

- [ ] **Step 5: Commit**

```bash
git add portal-permisos/backend/seguridad.py portal-permisos/backend/conftest.py portal-permisos/backend/test_seguridad.py
git commit -m "feat: hash de claves y tokens, cifrado de columnas con Fernet" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Esquema, conexión, catálogo y migraciones

**Files:**
- Create: `portal-permisos/backend/tablas.py` (las 8 tablas)
- Create: `portal-permisos/backend/bd.py` (motor y sesión)
- Create: `portal-permisos/backend/catalogo.py` (los 35 trámites, copiados de `CATALOGO` en `index.html`)
- Create: `portal-permisos/backend/migrar.py` (esquema, triggers, permisos, carga del catálogo)
- Modify: `portal-permisos/backend/conftest.py` (base nueva por prueba)
- Test: `portal-permisos/backend/test_bd.py`

**Interfaces:**
- Consumes: `seguridad.Cifrado`
- Produces:
  - `tablas`:
    - `Base` y las clases `Cuenta`, `Sesion`, `Permiso`, `Documento`, `Expediente`, `Historial`, `Cita`, `Bitacora`
    - las constantes `ESTADOS` y `ROLES`
    - el tipo `MomentoUTC`
  - `bd`:
    - `motor: Engine | None` y `SesionLocal: sessionmaker`
    - `configurar(url: str | None = None) -> Engine`
    - `sesion() -> Iterator[Session]`, la dependencia de FastAPI
    - `url_desde_entorno() -> str`
  - `migrar`:
    - `crear_esquema(motor)`, `otorgar_permisos(motor)`, `sembrar_catalogo(motor)`, `preparar(motor)`
    - las constantes `SOLO_ANEXAR` y `ROL_APP = "mupa_app"`
    - los nombres de trigger de SQLite `bitacora_sin_update`, `bitacora_sin_delete`, `historial_sin_update` e `historial_sin_delete`
  - `catalogo`: `PERMISOS`, una lista de tuplas `(id, nombre, categoria, dias, (min, max) | None, requisitos)`, y `DOCS`
  - `conftest`: el fixture `bd_limpia`, automático, que devuelve el `Engine`

- [ ] **Step 1: Escribir las pruebas**

Reemplaza `portal-permisos/backend/conftest.py` completo:

```python
"""
conftest.py — Preparación común de las pruebas.

Cada prueba recibe una base SQLite nueva en memoria, con el esquema, los
triggers y el catálogo, y un almacén de PDF en una carpeta temporal.
"""

import os

# Antes de importar la aplicación: pocas iteraciones para que las pruebas
# vayan rápido y una clave de cifrado desechable.
os.environ.setdefault("PBKDF2_ITER", "1000")
from cryptography.fernet import Fernet  # noqa: E402

os.environ.setdefault("CLAVE_CIFRADO", Fernet.generate_key().decode())

import pytest  # noqa: E402

import bd  # noqa: E402
import migrar  # noqa: E402


@pytest.fixture(autouse=True)
def bd_limpia(tmp_path, monkeypatch):
    monkeypatch.setenv("ALMACEN_DIR", str(tmp_path / "almacen"))
    motor = bd.configurar("sqlite://")
    migrar.preparar(motor)
    yield motor
    motor.dispose()
```

Crea `portal-permisos/backend/test_bd.py`:

```python
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
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest test_bd.py -q`
Expected: ERROR al importar `conftest.py`, con `ModuleNotFoundError: No module named 'bd'`

- [ ] **Step 3: Implementar el esquema**

Crea `portal-permisos/backend/tablas.py`:

```python
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
```

- [ ] **Step 4: Implementar la conexión**

Crea `portal-permisos/backend/bd.py`:

```python
"""
bd.py — Conexión a la base de datos.

    DATABASE_URL=sqlite:///./mupa.db                           desarrollo (por defecto)
    DATABASE_URL_FILE=/run/secrets/bd_url_app                  Docker: la URL con la
                                                               clave vive en un secreto
La API se conecta con el rol mupa_app, que sólo lee y escribe filas. Crear
tablas, triggers y permisos es trabajo de migrar.py, con el rol dueño.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

motor: Engine | None = None
SesionLocal = sessionmaker(expire_on_commit=False)


def url_desde_entorno() -> str:
    archivo = os.getenv("DATABASE_URL_FILE")
    if archivo:
        with open(archivo, encoding="utf-8") as f:
            return f.read().strip()
    return os.getenv("DATABASE_URL", "sqlite:///./mupa.db")


def configurar(url: str | None = None) -> Engine:
    """Crea el motor y lo conecta a SesionLocal. Las pruebas lo llaman con
    "sqlite://" para tener una base nueva en memoria en cada prueba."""
    global motor
    url = url or url_desde_entorno()
    if url.startswith("sqlite"):
        opciones: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            opciones["poolclass"] = StaticPool     # una sola conexión: la base vive en ella
        motor = create_engine(url, **opciones)
        event.listen(motor, "connect", _pragmas_sqlite)
    else:
        motor = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
    SesionLocal.configure(bind=motor)
    return motor


def _pragmas_sqlite(conexion, _registro) -> None:
    cursor = conexion.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")      # SQLite no las revisa si no se le pide
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()


def sesion() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición. No hace commit por su
    cuenta: cada ruta confirma lo suyo, incluso antes de responder un error
    que deba quedar en la bitácora (p. ej. un inicio de sesión fallido)."""
    with SesionLocal() as s:
        yield s
```

- [ ] **Step 5: Implementar el catálogo**

Crea `portal-permisos/backend/catalogo.py`. Es la misma información que `CATALOGO` en `index.html`, líneas 917–1004:

```python
"""
catalogo.py — Los 35 trámites de la Dirección de Permisos y Cumplimiento.

Fuente: https://permisosycumplimiento.mupa.gob.pa/tramites-y-permisos/
Es la misma lista que CATALOGO en index.html; migrar.py la carga en la tabla
`permisos`. Si cambia un trámite, se cambia aquí y se vuelve a correr migrar.py.
"""

DOCS = {
    "nota":   "Nota de solicitud dirigida al Alcalde de Panamá",
    "ced":    "Copia de cédula o pasaporte del solicitante",
    "aviso":  "Aviso de Operación vigente",
    "paz":    "Paz y Salvo Municipal",
    "rp":     "Certificado del Registro Público (personas jurídicas)",
    "poliza": "Póliza de responsabilidad civil",
    "bomb":   "Visto bueno del Cuerpo de Bomberos de Panamá",
    "plano":  "Plano de ubicación o croquis del sitio",
    "idoneo": "Idoneidad del personal técnico responsable",
    "minsa":  "Registro sanitario del MINSA",
    "ficha":  "Ficha técnica de los productos a utilizar",
    "ipf":    "Informe Previo Favorable vigente",
    "ruta":   "Ruta y horario detallado del recorrido",
    "veh":    "Registro vehicular y revisado vigente",
    "seg":    "Plan de seguridad y evacuación",
    "ambos":  "Nota de no objeción del corregimiento",
}


def _r(*claves: str) -> list[str]:
    """Traduce claves de DOCS a texto; lo que no es clave se deja tal cual."""
    return [DOCS.get(c, c) for c in claves]


ESP = "Espectáculos y eventos públicos"
PUB = "Publicidad y uso de espacio público"
SON = "Sonido y unidades móviles"
NOC = "Permisos nocturnos"
TAL = "Talleres"
SAL = "Salud y saneamiento ambiental"
COM = "Comercio y actividades especiales"
INF = "Informes previos"

# (id, nombre, categoría, días hábiles, aforo (mín, máx) o None, requisitos)
PERMISOS = [
    ("ESP-500-", "Espectáculo Público — menos de 500 personas", ESP, 15, (1, 499),
     _r("nota", "ced", "aviso", "paz", "poliza", "bomb")),
    ("ESP-4000", "Espectáculo Público — menos de 4,000 personas", ESP, 20, (500, 3999),
     _r("nota", "ced", "aviso", "paz", "poliza", "bomb", "seg", "plano")),
    ("ESP-500+", "Espectáculo Público — más de 500 personas", ESP, 25, (500, 60000),
     _r("nota", "ced", "aviso", "paz", "poliza", "bomb", "seg", "plano", "rp")),
    ("FEST", "Festividad", ESP, 15, None,
     _r("nota", "ced", "ambos", "poliza", "bomb")),
    ("BANDAS", "Práctica de Bandas Independientes", ESP, 10, None,
     _r("nota", "ced", "ambos", "ruta")),
    ("PASEO", "Paseo o Excursiones", ESP, 10, None,
     _r("nota", "ced", "ruta", "veh", "poliza")),
    ("CHIVA", "Chiva Parrandera", ESP, 15, None,
     _r("nota", "ced", "veh", "poliza", "ruta", "aviso")),
    ("INVIT", "Invitación de la Alcaldía de Panamá", ESP, 8, None,
     _r("nota", "ced")),

    ("PUB-TEMP", "Instalación de Publicidad Eventual o Temporal", PUB, 12, None,
     _r("nota", "ced", "aviso", "paz", "plano", "ipf")),
    ("BANDEROLA", "Instalación de Banderolas Móviles", PUB, 12, None,
     _r("nota", "ced", "aviso", "paz", "plano")),
    ("ESP-EST", "Uso de Espacio Público para Estacionamiento", PUB, 15, None,
     _r("nota", "ced", "aviso", "paz", "plano", "poliza")),
    ("ACERA", "Uso Temporal de Aceras", PUB, 12, None,
     _r("nota", "ced", "aviso", "paz", "plano")),
    ("CASCO", "Uso Temporal de Espacio Público — Casco Antiguo", PUB, 20, None,
     _r("nota", "ced", "aviso", "paz", "plano", "poliza",
        "Visto bueno de la Oficina del Casco Antiguo")),

    ("SON-TEMP", "Servicio de Unidad Móvil de Sonido u Audio — Temporal", SON, 10, None,
     _r("nota", "ced", "veh", "ruta")),
    ("SON-PERM", "Servicio de Unidad Móvil de Sonido u Audio", SON, 15, None,
     _r("nota", "ced", "aviso", "paz", "veh", "ruta")),

    ("NOC-A", "Permiso Nocturno Categoría A", NOC, 25, None,
     _r("nota", "ced", "aviso", "paz", "rp", "bomb", "ipf", "plano")),
    ("NOC-A-REN", "Renovación de Permiso Nocturno Categoría A", NOC, 15, None,
     _r("nota", "ced", "paz", "Permiso nocturno del período anterior", "bomb")),
    ("NOC-B", "Permiso Nocturno Categoría B", NOC, 20, None,
     _r("nota", "ced", "aviso", "paz", "bomb", "ipf")),
    ("NOC-C", "Permiso Nocturno Categoría C", NOC, 20, None,
     _r("nota", "ced", "aviso", "paz", "bomb", "ipf")),
    ("NOC-D", "Permiso Nocturno Categoría D", NOC, 20, None,
     _r("nota", "ced", "aviso", "paz", "bomb", "ipf")),

    ("TAL-INST", "Instalación y Operación de Taller", TAL, 25, None,
     _r("nota", "ced", "aviso", "paz", "ipf", "plano", "bomb")),
    ("TAL-HOR", "Extensión de Horario para Taller", TAL, 12, None,
     _r("nota", "ced", "aviso", "paz", "Permiso de operación del taller")),
    ("TAL-MOV", "Operación de Taller Móvil", TAL, 15, None,
     _r("nota", "ced", "aviso", "veh", "idoneo")),
    ("TAL-COMB", "Taller — Extensión de Horario y Taller Móvil", TAL, 18, None,
     _r("nota", "ced", "aviso", "paz", "veh", "idoneo")),

    ("DESINF", "Permiso de Desinfección", SAL, 15, None,
     _r("nota", "ced", "aviso", "minsa", "idoneo", "ficha")),
    ("DESINF-A", "Actualización de Desinfección", SAL, 10, None,
     _r("nota", "ced", "minsa", "ficha")),
    ("GICP", "Gestión Integral de Control de Plagas", SAL, 20, None,
     _r("nota", "ced", "aviso", "minsa", "idoneo", "ficha", "paz")),
    ("GICP-REN", "Renovación de Gestión Integral de Control de Plagas", SAL, 12, None,
     _r("nota", "ced", "paz", "minsa", "Permiso GICP del período anterior")),
    ("GICP-ACT", "Actualización de Gestión Integral de Control de Plagas", SAL, 10, None,
     _r("nota", "ced", "minsa", "ficha", "idoneo")),

    ("GANADO", "Guía de Traslado de Ganado", COM, 5, None,
     _r("nota", "ced", "Certificado de salud animal del MIDA", "veh", "ruta")),
    ("GRUAS", "Inscripción de Grúas y Almacenamiento", COM, 20, None,
     _r("nota", "ced", "aviso", "paz", "rp", "veh", "poliza")),
    ("NAVIDAD", "Venta de Árboles de Navidad", COM, 12, None,
     _r("nota", "ced", "aviso", "paz", "plano", "Permiso fitosanitario del MIDA")),
    ("FERRETE", "Ferrete", COM, 8, None,
     _r("nota", "ced", "aviso", "paz")),

    ("IPF", "Informe Previo Favorable", INF, 20, None,
     _r("nota", "ced", "rp", "plano", "Certificación de uso de suelo", "bomb")),
    ("IPF-ACT", "Actualización de Informe Previo Favorable", INF, 12, None,
     _r("nota", "ced", "ipf", "plano")),
]
```

- [ ] **Step 6: Implementar las migraciones**

Crea `portal-permisos/backend/migrar.py`:

```python
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

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import bd
import catalogo
from tablas import Base, Permiso

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


def preparar(motor: Engine) -> None:
    crear_esquema(motor)
    sembrar_catalogo(motor)
    if motor.dialect.name == "postgresql":
        otorgar_permisos(motor)


if __name__ == "__main__":
    m = bd.configurar()
    preparar(m)
    print(f"Esquema listo en {m.url.render_as_string(hide_password=True)}")
```

- [ ] **Step 7: Verificar que pasan**

Run: `pytest test_bd.py -q` → `13 passed`
Run: `pytest -q` → `37 passed, 2 skipped` (el `test_api.py` viejo sigue pasando: aún no usa la base)

- [ ] **Step 8: Commit**

```bash
git add portal-permisos/backend/tablas.py portal-permisos/backend/bd.py portal-permisos/backend/catalogo.py portal-permisos/backend/migrar.py portal-permisos/backend/conftest.py portal-permisos/backend/test_bd.py
git commit -m "feat: esquema de 8 tablas, triggers de solo anexado y catálogo de 35 trámites" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Bitácora encadenada en la base

**Files:**
- Create: `portal-permisos/backend/repositorio.py` (primera parte: la bitácora)
- Test: `portal-permisos/backend/test_bitacora.py`

**Interfaces:**
- Consumes: `tablas.Bitacora`, `bd.SesionLocal`, `bd.motor`
- Produces:
  - `repositorio.registrar(s, accion: str, actor: str, **datos) -> Bitacora`, que hace flush pero no commit
  - `repositorio.verificar_bitacora(s) -> dict`, que devuelve `{"integra": True, "entradas": n}` o `{"integra": False, "rota_en": n}`
  - `repositorio.total_bitacora(s) -> int`
  - `repositorio.MUNICIPIO: str`
  - `repositorio._ahora() -> datetime`, en UTC

La diferencia con la versión en memoria: el hash se calcula sobre **JSON canónico**, con claves ordenadas y sin espacios. Así da lo mismo después de guardarse y leerse desde SQLite, PostgreSQL o un respaldo. En PostgreSQL, un candado (`pg_advisory_xact_lock`) evita que dos escrituras simultáneas lean el mismo «último hash».

- [ ] **Step 1: Escribir las pruebas**

Crea `portal-permisos/backend/test_bitacora.py`:

```python
"""Pruebas de la bitácora encadenada (repositorio.registrar / verificar_bitacora)."""

from datetime import date

from sqlalchemy import select, text

import bd
import repositorio
from tablas import Bitacora


# ──────────────────────────── bitácora ────────────────────────────

def test_cada_entrada_encadena_el_hash_de_la_anterior():
    with bd.SesionLocal() as s:
        a = repositorio.registrar(s, "uno", "sistema")
        b = repositorio.registrar(s, "dos", "sistema", x=1)
        s.commit()
        assert (a.n, b.n) == (1, 2)
        assert a.previo == "0" * 64 and b.previo == a.hash


def test_la_cadena_sigue_integra_al_releerla_de_la_base():
    """Tildes, fechas y claves en desorden: el JSON canónico debe dar el
    mismo hash después de guardarse y volver a leerse."""
    with bd.SesionLocal() as s:
        repositorio.registrar(s, "cuenta.creada", "ñandú@correo.com",
                              organizacion="Fundación Año Nuevo", z=2, a=[1, 2],
                              cuando=date(2026, 10, 18))
        s.commit()
    with bd.SesionLocal() as s:
        assert repositorio.verificar_bitacora(s) == {"integra": True, "entradas": 1}


def _tres_entradas():
    with bd.SesionLocal() as s:
        for accion in ("uno", "dos", "tres"):
            repositorio.registrar(s, accion, "sistema")
        s.commit()


def test_se_detecta_una_fila_alterada():
    _tres_entradas()
    with bd.motor.begin() as c:                  # sólo un administrador podría hacer esto
        c.execute(text("DROP TRIGGER bitacora_sin_update"))
        c.execute(text("UPDATE bitacora SET actor = 'intruso' WHERE n = 2"))
    with bd.SesionLocal() as s:
        assert repositorio.verificar_bitacora(s) == {"integra": False, "rota_en": 2}


def test_se_detecta_una_fila_borrada():
    _tres_entradas()
    with bd.motor.begin() as c:
        c.execute(text("DROP TRIGGER bitacora_sin_delete"))
        c.execute(text("DELETE FROM bitacora WHERE n = 2"))
    with bd.SesionLocal() as s:
        assert repositorio.verificar_bitacora(s) == {"integra": False, "rota_en": 3}


def test_no_hay_filas_de_bitacora_si_nadie_hizo_commit():
    with bd.SesionLocal() as s:
        repositorio.registrar(s, "sin.confirmar", "sistema")
        s.rollback()
        assert s.scalars(select(Bitacora)).first() is None


def test_total_bitacora_cuenta_las_entradas():
    _tres_entradas()
    with bd.SesionLocal() as s:
        assert repositorio.total_bitacora(s) == 3
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest test_bitacora.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'repositorio'`

- [ ] **Step 3: Implementar**

Crea `portal-permisos/backend/repositorio.py`:

```python
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
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from tablas import Bitacora

MUNICIPIO = os.getenv("MUNICIPIO", "panama")
_CERO = "0" * 64


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
```

- [ ] **Step 4: Verificar que pasan**

Run: `pytest test_bitacora.py -q` → `6 passed`

- [ ] **Step 5: Commit**

```bash
git add portal-permisos/backend/repositorio.py portal-permisos/backend/test_bitacora.py
git commit -m "feat: bitácora encadenada persistente con JSON canónico" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Almacén de PDF en disco

**Files:**
- Create: `portal-permisos/backend/almacen.py`
- Test: `portal-permisos/backend/test_almacen.py`

**Interfaces:**
- Produces:
  - `almacen.guardar(sha256: str, contenido: bytes) -> str`, que devuelve la ruta relativa `ab/<sha>.pdf` y lanza `ValueError` si la huella no tiene 64 caracteres hexadecimales en minúscula
  - `almacen.leer(ruta: str) -> bytes`
  - `almacen.raiz() -> Path`, tomada de `ALMACEN_DIR` (`./almacen` por defecto)

Hoy el PDF se descarta y sólo queda una ruta `s3://` inventada. Con esta tarea el archivo se guarda, sólo después de que ClamAV lo aprueba, con el nombre de su huella.

- [ ] **Step 1: Escribir las pruebas**

Crea `portal-permisos/backend/test_almacen.py`:

```python
"""Pruebas de almacen.py: dónde y cómo se guardan los PDF."""

import hashlib

import pytest

import almacen

PDF = b"%PDF-1.4\n%%EOF\n"
SHA = hashlib.sha256(PDF).hexdigest()


def test_el_pdf_se_guarda_con_el_nombre_de_su_huella():
    ruta = almacen.guardar(SHA, PDF)
    assert ruta == f"{SHA[:2]}/{SHA}.pdf"
    assert almacen.leer(ruta) == PDF


def test_guardar_dos_veces_no_deja_temporales_ni_duplicados():
    almacen.guardar(SHA, PDF)
    almacen.guardar(SHA, PDF)
    archivos = [p.name for p in (almacen.raiz() / SHA[:2]).iterdir()]
    assert archivos == [f"{SHA}.pdf"]


@pytest.mark.parametrize("huella", ["../../etc/passwd", "A" * 64, "a" * 63, "", "a" * 64 + "/x"])
def test_una_huella_inventada_no_puede_elegir_la_ruta(huella):
    with pytest.raises(ValueError):
        almacen.guardar(huella, PDF)
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest test_almacen.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'almacen'`

- [ ] **Step 3: Implementar**

Crea `portal-permisos/backend/almacen.py`:

```python
"""
almacen.py — Dónde viven los PDF verificados.

Cada archivo se guarda con el nombre de su huella SHA-256, repartido en
subcarpetas por sus dos primeros caracteres (ab/abcdef….pdf). El mismo PDF
subido dos veces ocupa un solo lugar, y el usuario nunca elige la ruta: el
nombre que manda el navegador no se usa para nada en el disco.

Sólo se llama DESPUÉS de que ClamAV dio el veredicto limpio.
"""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

_HEX64 = re.compile(r"[0-9a-f]{64}")


def raiz() -> Path:
    return Path(os.getenv("ALMACEN_DIR", "./almacen"))


def guardar(sha256: str, contenido: bytes) -> str:
    """Guarda el PDF y devuelve su ruta relativa al almacén."""
    if not _HEX64.fullmatch(sha256):
        raise ValueError("Huella SHA-256 inválida")
    relativa = Path(sha256[:2]) / f"{sha256}.pdf"
    destino = raiz() / relativa
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        # Escribe a un temporal y renombra: nunca queda un PDF a medias.
        temporal = destino.with_name(f"{sha256}.{secrets.token_hex(4)}.tmp")
        temporal.write_bytes(contenido)
        temporal.replace(destino)
    return relativa.as_posix()


def leer(ruta: str) -> bytes:
    return (raiz() / ruta).read_bytes()
```

- [ ] **Step 4: Verificar que pasan**

Run: `pytest test_almacen.py -q` → `7 passed`

- [ ] **Step 5: Commit**

```bash
git add portal-permisos/backend/almacen.py portal-permisos/backend/test_almacen.py
git commit -m "feat: almacén de PDF verificados por huella SHA-256" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Repositorio — cuentas, sesiones, catálogo, documentos, expedientes y citas

**Files:**
- Modify: `portal-permisos/backend/repositorio.py` (cambia la cabecera y agrega funciones al final)
- Test: `portal-permisos/backend/test_repositorio.py`

**Interfaces:**
- Consumes:
  - `seguridad.cifrar_clave` y `seguridad.nuevo_token`
  - `seguridad.huella_token`
  - las clases de `tablas`
- Produces (todas reciben la `Session` como primer argumento y ninguna hace commit, salvo `cuenta_por_token` cuando borra una sesión vencida):
  - Excepciones: `Duplicado`, `TurnoOcupado`
  - Constantes: `SESION_HORAS: float` (de la variable `SESION_HORAS`, 8 por defecto) y `ETAPA_INICIAL: str`
  - Cuentas y sesiones:
    - `cuenta_por_email(s, email) -> Cuenta | None`
    - `crear_cuenta(s, *, nombre, apellido, edad, organizacion, email, cedula, password) -> Cuenta`, que lanza `Duplicado`
    - `abrir_sesion(s, cuenta) -> str`, que devuelve el token
    - `cuenta_por_token(s, token) -> Cuenta | None`
    - `cerrar_sesion(s, token) -> None`
    - `publico(cuenta) -> dict`
  - Catálogo:
    - `permisos(s, categoria=None) -> list[Permiso]`
    - `permiso(s, id) -> Permiso | None`
    - `permiso_a_dict(p) -> dict`
  - Documentos:
    - `guardar_documento(s, propietario, sha256, nombre, tamano, ruta) -> Documento`
    - `documento_de(s, propietario_id, sha256) -> Documento | None`
  - Expedientes:
    - `crear_expediente(s, cuenta, permiso, documento, d: dict) -> Expediente`, donde `d` trae las claves de `SolicitudNueva`
    - `expedientes_de(s, cuenta, estado=None) -> list[Expediente]`
    - `historial_de(s, expediente) -> list[Historial]`
    - `conteo_por_estado(s) -> dict[str, int]`
    - `total_expedientes(s) -> int`
    - `expediente_a_dict(e) -> dict`
  - Citas:
    - `reservar_cita(s, cuenta, d: dict) -> Cita`, que lanza `TurnoOcupado`
    - `cita_a_dict(c) -> dict`

- [ ] **Step 1: Escribir las pruebas**

Crea `portal-permisos/backend/test_repositorio.py`:

```python
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
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest test_repositorio.py -q`
Expected: FAIL con `AttributeError: module 'repositorio' has no attribute 'crear_cuenta'`

- [ ] **Step 3: Ampliar la cabecera de `repositorio.py`**

En `portal-permisos/backend/repositorio.py`, reemplaza este bloque, que va desde `from __future__` hasta la función `_ahora` inclusive:

```python
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from tablas import Bitacora

MUNICIPIO = os.getenv("MUNICIPIO", "panama")
_CERO = "0" * 64


def _ahora() -> datetime:
    return datetime.now(timezone.utc)
```

por este:

```python
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import seguridad
from tablas import (
    ESTADOS, Bitacora, Cita, Cuenta, Documento, Expediente, Historial, Permiso, Sesion,
)

MUNICIPIO = os.getenv("MUNICIPIO", "panama")
SESION_HORAS = float(os.getenv("SESION_HORAS", "8"))
ETAPA_INICIAL = "En cola de asignación · Dirección de Permisos"
_CERO = "0" * 64


class Duplicado(Exception):
    """Ya existe una cuenta con ese correo."""


class TurnoOcupado(Exception):
    """Otra persona tomó esa sede, fecha y hora."""


def _ahora() -> datetime:
    return datetime.now(timezone.utc)
```

- [ ] **Step 4: Agregar el resto de las funciones**

Agrega al **final** de `portal-permisos/backend/repositorio.py`, después de `total_bitacora`:

```python
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


def cita_a_dict(c: Cita) -> dict:
    return {
        "turno": c.turno, "solicitante": c.solicitante.email, "municipio": c.municipio,
        "sede": c.sede, "motivo": c.motivo, "fecha": c.fecha.isoformat(),
        "hora": c.hora, "expediente": c.expediente,
    }
```

- [ ] **Step 5: Verificar que pasan**

Run: `pytest test_repositorio.py -q` → `13 passed`
Run: `pytest -q` → `63 passed, 2 skipped`

- [ ] **Step 6: Commit**

```bash
git add portal-permisos/backend/repositorio.py portal-permisos/backend/test_repositorio.py
git commit -m "feat: repositorio de cuentas, sesiones, documentos, expedientes y citas" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: La API usa la base de datos

**Files:**
- Modify: `portal-permisos/backend/main.py` (se reemplaza completo)
- Modify: `portal-permisos/backend/metricas.py` (agrega `bd_arriba`)
- Modify: `portal-permisos/backend/test_api.py` (se reemplaza completo)
- Modify: `portal-permisos/monitoreo/alertas.yml` (agrega `BaseDeDatosCaida`)
- Modify: `portal-permisos/README.md` (sección «3. La API» y variables de entorno)

**Interfaces:**
- Consumes: todo lo de las tareas 2 a 6.
- Produces:
  - Rutas nuevas y cambios de contrato:
    - `DELETE /api/sesiones` → 204
    - `POST /api/cuentas` exige `acepta_tratamiento: true` (Ley 81)
    - `POST /api/solicitudes` exige `declaracion_jurada: true` (Acuerdo 130)
    - `/salud` agrega `base_de_datos: {arriba, expedientes, bitacora}`
  - La métrica `mupa_bd_arriba`.
  - `main.usuario_actual(authorization, s) -> Cuenta`.

Cambios de conducta que corrigen errores de la versión en memoria:
- Ya se pueden solicitar los 35 trámites, no sólo 5.
- Si dos personas suben el mismo PDF, cada una conserva el suyo.
- Las sesiones vencen a las 8 horas.
- El intento de inicio de sesión fallido queda registrado aunque la respuesta sea 401.
- `/metrics` sigue respondiendo aunque la base se caiga.
- `verificar_documento` pasa a ser una ruta síncrona: FastAPI la corre en un hilo aparte, así el escaneo de ClamAV ya no frena a las demás peticiones.

- [ ] **Step 1: Reemplazar las pruebas de la API**

Reemplaza `portal-permisos/backend/test_api.py` completo:

```python
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
EICAR = (b"%PDF-1.4\n"
         rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
         b"\n%%EOF\n")

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
    este archivo daría un error 500 en producción."""
    sha = hashlib.sha256(PDF_OK).hexdigest()
    monkeypatch.setattr(antivirus, "verificar", lambda contenido, nombre: antivirus.Veredicto(
        antivirus.Resultado.LIMPIO, "Documento verificado.", sha256=sha, bytes_=len(contenido)))
    r = _subir(PDF_OK, "a" * 300 + ".pdf", cabecera)
    assert r.status_code == 200
    assert len(r.json()["nombre"]) == 255


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
```

- [ ] **Step 2: Verificar que fallan**

Run: `pytest test_api.py -q`
Expected: varias FAIL. Por ejemplo, `test_cerrar_sesion_invalida_el_token` responde 405 porque `DELETE /api/sesiones` todavía no existe, y `test_el_catalogo_devuelve_los_35_tramites` recibe 5 trámites en lugar de 35.

- [ ] **Step 3: Agregar la métrica de la base**

En `portal-permisos/backend/metricas.py`, justo antes de `info_antivirus = Info(`, agrega:

```python
bd_arriba = Gauge(
    "mupa_bd_arriba",
    "1 si la API alcanza la base de datos, 0 si no.",
)

```

- [ ] **Step 4: Reemplazar `main.py`**

Reemplaza `portal-permisos/backend/main.py` completo:

```python
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
    nombre = (archivo.filename or "documento.pdf")[:255]      # cabe en documentos.nombre

    with metricas.cronometrar(metricas.duracion_escaneo):
        v = antivirus.verificar(contenido, nombre)

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
```

- [ ] **Step 5: Verificar que pasan**

Run: `pytest -q`
Expected: `77 passed, 2 skipped`

- [ ] **Step 6: Probar la API de verdad, con un reinicio en medio**

En PowerShell, desde `portal-permisos/backend`:

```powershell
$env:CLAVE_CIFRADO = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
uvicorn main:app --port 8000
```

En otra terminal:

```powershell
$cuerpo = @{ nombre="Diego"; apellido="López"; edad=22; organizacion="UTP"; email="demo@mupa.gob.pa"; password="demo1234"; cedula="8-912-345"; acepta_tratamiento=$true } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/cuentas -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($cuerpo))
```

Detén uvicorn con Ctrl+C, vuelve a arrancarlo con la **misma** `$env:CLAVE_CIFRADO` y luego:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/sesiones -ContentType "application/json" -Body '{"email":"demo@mupa.gob.pa","password":"demo1234"}'
Invoke-RestMethod http://localhost:8000/api/bitacora/verificar
```

Expected: el inicio de sesión devuelve un `token` (la cuenta sobrevivió al reinicio) y la bitácora responde `integra: True, entradas: 2`. Al validar este plan se vio además, en `mupa.db`, que la cédula queda como `gAAAA…` y la clave como `pbkdf2_sha256$600000$…`.

- [ ] **Step 7: Alerta de base caída**

En `portal-permisos/monitoreo/alertas.yml`, justo antes de `      - alert: AmenazaDetectada`, agrega:

```yaml
      - alert: BaseDeDatosCaida
        expr: mupa_bd_arriba == 0
        for: 1m
        labels: { severidad: critica }
        annotations:
          summary: "La API no alcanza la base de datos en {{ $labels.municipio }}"
          description: >
            Ningún trámite puede crearse ni consultarse. Revisar:
            docker compose logs bd  y  docker compose logs api

```

- [ ] **Step 8: Actualizar el README**

En `portal-permisos/README.md`, reemplaza toda la sección `### 3. La API`, desde el título hasta la línea `Salud del servicio en http://localhost:8000/salud`, por:

````markdown
### 3. La API

Necesita Python 3.12 o 3.13; las versiones fijadas todavía no tienen paquetes para 3.14.

```powershell
cd backend
py -3.13 -m venv .venv                 # Linux/macOS: python3.13 -m venv .venv
.venv\Scripts\activate                 # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt

# Clave que cifra la cédula en la base. Guárdala: sin ella esos datos no se leen.
$env:CLAVE_CIFRADO = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
uvicorn main:app --reload --port 8000
```

En desarrollo los datos quedan en `backend/mupa.db` (SQLite) y los PDF en
`backend/almacen/`. Las tablas y el catálogo se crean solos al arrancar. Si
cambias el esquema, borra `mupa.db`: todavía no hay migraciones que alteren
tablas existentes.

Documentación interactiva en http://localhost:8000/docs
Salud del servicio en http://localhost:8000/salud
````

En la sección `## Variables de entorno`, reemplaza el bloque `# backend` por:

```bash
# backend
DATABASE_URL=sqlite:///./mupa.db  # o DATABASE_URL_FILE=<archivo con la URL> (Docker)
CLAVE_CIFRADO=...                 # obligatoria; o CLAVE_CIFRADO_FILE=<archivo>
ALMACEN_DIR=./almacen             # dónde se guardan los PDF verificados
SESION_HORAS=8                    # duración de una sesión
CLAMAV_HOST=127.0.0.1
CLAMAV_PORT=3310
CLAMAV_TIMEOUT=30
MUNICIPIO=panama                  # etiqueta que separa los datos de cada municipio
CORS_ORIGENES=http://localhost:5173
```

- [ ] **Step 9: Commit**

```bash
git add portal-permisos/backend/main.py portal-permisos/backend/metricas.py portal-permisos/backend/test_api.py portal-permisos/monitoreo/alertas.yml portal-permisos/README.md
git commit -m "feat: la API persiste en base de datos (SQLite/PostgreSQL)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: PostgreSQL endurecido (roles, secretos, red interna)

**Files:**
- Create: `portal-permisos/monitoreo/bd/01-roles.sh`
- Create: `portal-permisos/monitoreo/generar_secretos.py`
- Modify: `portal-permisos/monitoreo/docker-compose.yml` (se reemplaza completo)
- Test: `portal-permisos/backend/test_bd_postgres.py`

**Interfaces:**
- Consumes: `migrar.preparar`, `migrar.ROL_APP` y `repositorio.registrar`, `crear_cuenta`, `verificar_bitacora`
- Produces:
  - Roles:
    - `mupa_owner`, dueño del esquema `mupa`, sin superusuario
    - `mupa_app`, con `CONNECTION LIMIT 20`, `statement_timeout` de 5 s e `idle_in_transaction_session_timeout` de 30 s
  - Secretos: seis archivos en `monitoreo/secretos/`:
    - `bd_superusuario_password.txt`, `bd_owner_password.txt`, `bd_app_password.txt`
    - `bd_url_owner.txt`, `bd_url_app.txt`
    - `clave_cifrado.txt`
  - Servicios de compose: `bd`, `migraciones`, `api`, y `bd-pruebas` (perfil `pruebas`, en `127.0.0.1:55432`)

**Qué protege cada pieza:**

| Medida | Dónde |
|---|---|
| La API no puede crear ni borrar tablas, ni tocar `bitacora` o `historial` salvo para insertar | `01-roles.sh` + `migrar.PERMISOS_APP` |
| Nadie, ni el dueño, puede hacer UPDATE, DELETE o TRUNCATE sobre la auditoría | `migrar.TRIGGERS_POSTGRES` |
| La base no tiene puerto publicado; la red `datos` es `internal: true` (sin salida a internet) | compose |
| Las claves viven en archivos de secretos, no en variables visibles con `docker inspect` | compose + `*_FILE` |
| Autenticación `scram-sha-256` por red y `peer` en el socket local | `POSTGRES_INITDB_ARGS` |
| Límite de memoria, `no-new-privileges`, reinicio automático | compose |

- [ ] **Step 1: Escribir las pruebas contra PostgreSQL**

Crea `portal-permisos/backend/test_bd_postgres.py`:

```python
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
```

Run: `pytest -q`
Expected: `77 passed, 20 skipped` (las 18 nuevas se omiten sin la base de pruebas).

- [ ] **Step 2: Script de roles**

Crea `portal-permisos/monitoreo/bd/01-roles.sh`:

```sh
#!/bin/sh
# Crea los dos roles de la aplicación. PostgreSQL lo corre UNA sola vez,
# cuando el volumen de datos está vacío.
#
#   mupa_owner  dueño del esquema "mupa": lo usa migrar.py para crear
#               tablas, triggers y permisos. No es superusuario.
#   mupa_app    la API: lee y escribe filas, nada más.
#
# Las claves salen de los secretos de Docker; la base de pruebas las pasa
# por variables de entorno (BD_OWNER_PASSWORD / BD_APP_PASSWORD).
set -eu

leer() {
  if [ -n "${2:-}" ]; then printf '%s' "$2"; else cat "$1"; fi
}
OWNER_PW=$(leer /run/secrets/bd_owner_password "${BD_OWNER_PASSWORD:-}")
APP_PW=$(leer /run/secrets/bd_app_password "${BD_APP_PASSWORD:-}")

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
     -v owner_pw="$OWNER_PW" -v app_pw="$APP_PW" -v db="$POSTGRES_DB" <<'SQL'
CREATE ROLE mupa_owner LOGIN PASSWORD :'owner_pw' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE mupa_app   LOGIN PASSWORD :'app_pw'   NOSUPERUSER NOCREATEDB NOCREATEROLE
                       CONNECTION LIMIT 20;

-- Nadie más que estos dos roles puede conectarse a la base.
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO mupa_owner, mupa_app;

-- Las tablas viven en el esquema "mupa", no en "public".
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA mupa AUTHORIZATION mupa_owner;
GRANT USAGE ON SCHEMA mupa TO mupa_app;
ALTER ROLE mupa_owner SET search_path = mupa;
ALTER ROLE mupa_app   SET search_path = mupa;

-- Una consulta colgada o una transacción olvidada no bloquean la base.
ALTER ROLE mupa_app SET statement_timeout = '5s';
ALTER ROLE mupa_app SET idle_in_transaction_session_timeout = '30s';
SQL
```

- [ ] **Step 3: Generador de secretos**

Crea `portal-permisos/monitoreo/generar_secretos.py`:

```python
"""
generar_secretos.py — Crea las claves que usa docker-compose.yml.

    python generar_secretos.py

Escribe un archivo por secreto en monitoreo/secretos/ (que git ignora).
Nunca sobrescribe: si se pierde clave_cifrado.txt, las cédulas guardadas
ya no se pueden leer, y si cambian las claves de la base, los roles creados
en el volumen dejan de coincidir.
"""

import base64
import os
import secrets
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "secretos"


def main() -> int:
    dueno, app = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    valores = {
        "bd_superusuario_password.txt": secrets.token_urlsafe(24),
        "bd_owner_password.txt": dueno,
        "bd_app_password.txt": app,
        "bd_url_owner.txt": f"postgresql+psycopg://mupa_owner:{dueno}@bd:5432/mupa",
        "bd_url_app.txt": f"postgresql+psycopg://mupa_app:{app}@bd:5432/mupa",
        # Misma forma que Fernet.generate_key(), sin necesitar cryptography aquí.
        "clave_cifrado.txt": base64.urlsafe_b64encode(os.urandom(32)).decode(),
    }
    existentes = [n for n in valores if (CARPETA / n).exists()]
    if existentes:
        print(f"Ya existen {', '.join(existentes)} en {CARPETA}. No se sobrescribe nada.")
        return 1
    CARPETA.mkdir(mode=0o700, exist_ok=True)
    for nombre, valor in valores.items():
        (CARPETA / nombre).write_text(valor, encoding="utf-8")
    print(f"Secretos creados en {CARPETA}. Respáldalos fuera del repositorio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Reemplazar el compose**

Reemplaza `portal-permisos/monitoreo/docker-compose.yml` completo. Este cambio también corrige dos errores que ya existían:
- `clamav/clamav:1.4-bookworm` no existe en Docker Hub, así que `docker compose up` fallaba;
- `alertas.yml` no se montaba en Prometheus, así que las alertas nunca se cargaban.

```yaml
# Levanta todo el sistema:
#   bd           → PostgreSQL 17 (sólo en la red interna, sin puerto al exterior)
#   migraciones  → crea tablas, triggers y permisos con el rol dueño, y termina
#   api          → la API con el rol mupa_app (puerto 8000)
#   clamav       → antivirus documental (puerto 3310)
#   prometheus   → recolecta las métricas de la API (puerto 9090)
#   grafana      → los tableros (puerto 3001, usuario admin / admin)
#
#   python generar_secretos.py        # una sola vez: crea secretos/
#   docker compose up -d --build
#
# La primera vez ClamAV tarda ~2 minutos en descargar su base de firmas.
# Compruébalo con:  docker compose logs -f clamav
#
# Base de pruebas para pytest -m postgres (en memoria, se borra al pararla):
#   docker compose --profile pruebas up -d bd-pruebas

x-endurecido: &endurecido
  security_opt:
    - no-new-privileges:true
  restart: unless-stopped

services:
  bd:
    <<: *endurecido
    image: postgres:17-alpine
    container_name: mupa-bd
    environment:
      POSTGRES_DB: mupa
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD_FILE: /run/secrets/bd_superusuario_password
      POSTGRES_INITDB_ARGS: --auth-host=scram-sha-256 --auth-local=peer
    secrets:
      - bd_superusuario_password
      - bd_owner_password
      - bd_app_password
    volumes:
      - datos-bd:/var/lib/postgresql/data
      - ./bd/01-roles.sh:/docker-entrypoint-initdb.d/01-roles.sh:ro
    networks: [datos]
    # Sin "ports": la base no es alcanzable desde fuera de Docker.
    mem_limit: 512m
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres", "-d", "mupa"]
      interval: 10s
      retries: 5
      start_period: 20s

  migraciones:
    image: mupa-api:local
    build: ../backend
    container_name: mupa-migraciones
    command: ["python", "migrar.py"]
    environment:
      DATABASE_URL_FILE: /run/secrets/bd_url_owner
      CLAVE_CIFRADO_FILE: /run/secrets/clave_cifrado
    secrets: [bd_url_owner, clave_cifrado]
    networks: [datos]
    depends_on:
      bd: { condition: service_healthy }
    security_opt:
      - no-new-privileges:true
    read_only: true
    cap_drop: [ALL]
    restart: "no"

  api:
    <<: *endurecido
    image: mupa-api:local
    build: ../backend
    container_name: mupa-api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL_FILE: /run/secrets/bd_url_app
      CLAVE_CIFRADO_FILE: /run/secrets/clave_cifrado
      CLAMAV_HOST: clamav
      MUNICIPIO: panama
      CORS_ORIGENES: http://localhost:5173
    secrets: [bd_url_app, clave_cifrado]
    volumes:
      - expedientes:/datos/expedientes
    networks: [datos, app]
    depends_on:
      migraciones: { condition: service_completed_successfully }
      clamav: { condition: service_started }
    read_only: true              # el único lugar escribible es el volumen de expedientes
    tmpfs: [/tmp]
    cap_drop: [ALL]
    mem_limit: 256m

  clamav:
    image: clamav/clamav:1.4     # basada en Alpine; la etiqueta 1.4-bookworm no existe
    container_name: mupa-clamav
    ports:
      - "3310:3310"
    volumes:
      - firmas:/var/lib/clamav        # persiste las firmas entre reinicios
    environment:
      CLAMAV_NO_MILTERD: "true"
      FRESHCLAM_CHECKS: "4"           # actualiza firmas 4 veces al día
    networks: [app]
    healthcheck:
      test: ["CMD", "clamdcheck.sh"]
      interval: 60s
      retries: 3
      start_period: 180s

  prometheus:
    image: prom/prometheus:v3.1.0
    container_name: mupa-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./alertas.yml:/etc/prometheus/alertas.yml:ro
      - metricas:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.retention.time=90d
    networks: [app]
    extra_hosts:
      - "host.docker.internal:host-gateway"

  grafana:
    image: grafana/grafana:11.5.0
    container_name: mupa-grafana
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    volumes:
      - tableros:/var/lib/grafana
      - ./grafana-datasource.yml:/etc/grafana/provisioning/datasources/prometheus.yml:ro
      - ./grafana-dashboard.json:/var/lib/grafana/dashboards/mupa.json:ro
      - ./grafana-provider.yml:/etc/grafana/provisioning/dashboards/mupa.yml:ro
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_USERS_ALLOW_SIGN_UP: "false"
    networks: [app]

  bd-pruebas:
    image: postgres:17-alpine
    container_name: mupa-bd-pruebas
    profiles: [pruebas]
    environment:
      POSTGRES_DB: mupa
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: pruebas-superusuario
      # Claves fijas a propósito: base desechable, en memoria y sólo en 127.0.0.1.
      BD_OWNER_PASSWORD: pruebas-dueno
      BD_APP_PASSWORD: pruebas-app
    volumes:
      - ./bd/01-roles.sh:/docker-entrypoint-initdb.d/01-roles.sh:ro
    tmpfs: [/var/lib/postgresql/data]
    ports:
      - "127.0.0.1:55432:5432"

networks:
  datos:
    internal: true               # sin salida a internet: sólo bd, migraciones y api
  app:

secrets:
  bd_superusuario_password: { file: ./secretos/bd_superusuario_password.txt }
  bd_owner_password:        { file: ./secretos/bd_owner_password.txt }
  bd_app_password:          { file: ./secretos/bd_app_password.txt }
  bd_url_owner:             { file: ./secretos/bd_url_owner.txt }
  bd_url_app:               { file: ./secretos/bd_url_app.txt }
  clave_cifrado:            { file: ./secretos/clave_cifrado.txt }

volumes:
  datos-bd:
  expedientes:
  firmas:
  metricas:
  tableros:
```

Run (desde `portal-permisos/monitoreo`): `docker compose config --quiet`
Expected: sin salida (compose válido). Si se queja de los secretos, corre primero `python generar_secretos.py`.

- [ ] **Step 5: Comprobar los finales de línea del script**

Run (desde la raíz del repositorio):

```bash
git add portal-permisos/monitoreo/bd/01-roles.sh
git ls-files --eol portal-permisos/monitoreo/bd/01-roles.sh
```

Expected: `i/lf    w/lf    attr/text eol=lf`. Si aparece `crlf`, el `.gitattributes` de la Tarea 1 no está en la raíz: corrígelo y corre `git add --renormalize .`.

- [ ] **Step 6: Levantar la base de pruebas y correr las pruebas**

Desde `portal-permisos/monitoreo`:

```powershell
docker compose --profile pruebas up -d bd-pruebas
docker compose logs bd-pruebas
```

Expected: en los registros aparecen `CREATE ROLE`, `CREATE SCHEMA` y `ALTER ROLE`, y al final `database system is ready to accept connections`.

Desde `portal-permisos/backend`:

```powershell
$env:PRUEBAS_PG = "1"
pytest -m postgres -v
```

Expected: `18 passed`. Si una prueba de permisos falla porque el mensaje no coincide (por ejemplo, porque la base está en otro idioma), ajusta el patrón de `match=` sin aflojar lo que se comprueba.

Al terminar: `docker compose --profile pruebas down`

- [ ] **Step 7: Commit**

```bash
git add portal-permisos/monitoreo/bd/01-roles.sh portal-permisos/monitoreo/generar_secretos.py portal-permisos/monitoreo/docker-compose.yml portal-permisos/backend/test_bd_postgres.py
git commit -m "feat: PostgreSQL con roles de mínimo privilegio, secretos y red interna" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Imagen liviana de la API y arranque completo

**Files:**
- Create: `portal-permisos/backend/Dockerfile`
- Create: `portal-permisos/backend/.dockerignore`
- Modify: `portal-permisos/monitoreo/prometheus.yml` (agrega el objetivo `api:8000`)
- Modify: `portal-permisos/README.md` (infraestructura, estructura y la sección nueva «Base de datos»)

**Interfaces:**
- Consumes: el compose de la Tarea 8, que construye `../backend` como `mupa-api:local`.
- Produces: la imagen `mupa-api:local`, de **≤ 120 MB**, con usuario `api` (uid 10001).

**Por qué Alpine y no `slim`:** la base `python:3.13-alpine` pesa 17 MB comprimida, contra 43 MB de `python:3.13-slim`. Las dependencias ocupan unos 63 MB instaladas sin bytecode (medido), y todas traen paquete para Alpine con sus bibliotecas nativas incluidas, así que no hace falta instalar nada con `apk`. El resultado esperado ronda los 105 MB, contra unos 190 MB con `slim`. `postgres:17-alpine` comprimida pesa 117 MB, contra 161 MB de la variante Debian.

- [ ] **Step 1: Dockerfile y lista blanca**

Crea `portal-permisos/backend/Dockerfile`:

```dockerfile
# Imagen de la API: Alpine y sólo lo necesario para correr (~105 MB).
#   docker build -t mupa-api:local .
#   docker images mupa-api:local

# ---------- etapa 1: instala las dependencias en un entorno aislado
FROM python:3.13-alpine AS dependencias
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.txt .
# --only-binary: si a una librería le falta paquete para Alpine, el build
# falla aquí en lugar de intentar compilarla sin compilador.
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-compile --only-binary=:all: -r requirements.txt \
 && rm -rf /opt/venv/lib/python3.13/site-packages/pip* /opt/venv/bin/pip*

# ---------- etapa 2: la imagen final, sin pip ni cachés
FROM python:3.13-alpine
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ALMACEN_DIR=/datos/expedientes
RUN rm -rf /usr/local/lib/python3.13/site-packages/pip* /usr/local/bin/pip* \
           /usr/local/lib/python3.13/ensurepip /usr/local/lib/python3.13/idlelib \
 && adduser -D -H -u 10001 api \
 && mkdir -p /datos/expedientes && chown api /datos/expedientes
COPY --from=dependencias /opt/venv /opt/venv
WORKDIR /app
COPY main.py antivirus.py metricas.py bd.py tablas.py seguridad.py repositorio.py \
     catalogo.py almacen.py migrar.py ./
USER api
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD wget -qO- http://127.0.0.1:8000/salud >/dev/null || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Crea `portal-permisos/backend/.dockerignore`:

```text
# Lista blanca: a la imagen sólo entra lo que el Dockerfile copia.
*
!requirements.txt
!*.py
test_*.py
conftest.py
```

- [ ] **Step 2: Construir y medir**

Desde `portal-permisos/backend`:

```powershell
docker build -t mupa-api:local .
docker images mupa-api:local --format "{{.Size}}"
docker run --rm mupa-api:local sh -c "ls /app; pip --version 2>&1 | head -1"
```

Expected:
- tamaño **≤ 120 MB**;
- `/app` contiene sólo los 10 módulos `.py`, sin `test_*.py` ni `conftest.py`;
- `pip` responde «not found».

Si el build falla en `--only-binary` es que a una librería le falta paquete para Alpine. No quites la opción para compilar: detente e informa qué librería es.

- [ ] **Step 3: Prometheus apunta al contenedor**

En `portal-permisos/monitoreo/prometheus.yml`, reemplaza el bloque del trabajo `ventanilla-api`:

```yaml
  # La API de la Ventanilla Única. host.docker.internal permite que Prometheus,
  # dentro de Docker, alcance uvicorn corriendo en tu máquina.
  - job_name: ventanilla-api
    metrics_path: /metrics
    static_configs:
      - targets: ["host.docker.internal:8000"]
        labels:
          municipio: panama
```

por:

```yaml
  # La API de la Ventanilla Única: "api" es el contenedor de docker compose;
  # host.docker.internal alcanza uvicorn corriendo en tu máquina. Normalmente
  # sólo uno de los dos está arriba.
  - job_name: ventanilla-api
    metrics_path: /metrics
    static_configs:
      - targets: ["api:8000", "host.docker.internal:8000"]
        labels:
          municipio: panama
```

- [ ] **Step 4: Levantar todo el sistema**

Desde `portal-permisos/monitoreo`:

```powershell
python generar_secretos.py
docker compose up -d --build
docker compose ps -a
```

Expected: `migraciones` con estado `Exited (0)`; `bd` y `api` con estado `healthy`.

Si `migraciones` termina con `password authentication failed`, quedó un volumen `datos-bd` de un intento anterior con otras claves. En desarrollo: `docker compose down -v`, que **borra los datos**, y vuelve a levantar.

- [ ] **Step 5: Verificar la seguridad del sistema en marcha**

```powershell
Invoke-RestMethod http://localhost:8000/salud
$cuerpo = @{ nombre="Diego"; apellido="López"; edad=22; organizacion="UTP"; email="demo@mupa.gob.pa"; password="demo1234"; cedula="8-912-345"; acepta_tratamiento=$true } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/cuentas -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($cuerpo))
docker compose restart api
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/sesiones -ContentType "application/json" -Body '{"email":"demo@mupa.gob.pa","password":"demo1234"}'
docker compose exec bd psql -U postgres -d mupa -c "SELECT email, left(cedula, 10) AS cedula, left(clave, 22) AS clave FROM mupa.cuentas"
docker compose exec api id
docker compose exec api touch /app/prueba
docker compose port bd 5432
```

Expected, en orden:

| Comprobación | Resultado esperado |
|---|---|
| `/salud` | `base_de_datos.arriba` es `True` |
| Cuenta creada y reinicio de la API | El inicio de sesión devuelve un `token` |
| `psql` | `cedula` empieza con `gAAAA` y `clave` con `pbkdf2_sha256$600000$` |
| `id` | `uid=10001(api)` |
| `touch` | `Read-only file system` |
| `port bd 5432` | Sin puerto publicado (salida vacía o error) |

Luego abre http://localhost:9090/targets: `api:8000` debe estar `UP` (`host.docker.internal:8000` aparecerá `DOWN` mientras no corra uvicorn local). En http://localhost:9090/rules debe aparecer `BaseDeDatosCaida`.

Por último, detén la base (`docker compose stop bd`): en un minuto `/salud` responde `degradado` y la alerta pasa a `firing`. Vuelve a levantarla con `docker compose start bd`.

- [ ] **Step 6: Actualizar el README**

En `portal-permisos/README.md`:

**a)** Reemplaza toda la sección `### 2. La infraestructura`, hasta la línea `` `docker compose logs -f clamav` hasta ver `Self checking every 600 seconds`. ``, por:

````markdown
### 2. La infraestructura

```bash
cd monitoreo
python generar_secretos.py        # una sola vez: crea monitoreo/secretos/ (fuera de git)
docker compose up -d --build
```

| Servicio | Dirección | Credenciales |
|---|---|---|
| API | http://localhost:8000 | — |
| PostgreSQL | sólo la red interna de Docker | `monitoreo/secretos/` |
| ClamAV | `localhost:3310` | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | admin / admin |

La primera vez ClamAV tarda unos 2 minutos en bajar su base de firmas:
`docker compose logs -f clamav` hasta ver `Self checking every 600 seconds`.

Si `migraciones` falla con `password authentication failed`, quedó un volumen
de un intento anterior con otras claves. En desarrollo: `docker compose down -v`
(**borra los datos**) y vuelve a levantar.
````

**b)** En `## Estructura`, reemplaza las líneas de `backend/` y `monitoreo/` del árbol por:

```text
├── backend/
│   ├── main.py                   API FastAPI
│   ├── repositorio.py            Todo el acceso a datos
│   ├── tablas.py                 Esquema de las 8 tablas
│   ├── bd.py                     Conexión (SQLite o PostgreSQL)
│   ├── migrar.py                 Crea tablas, triggers y permisos
│   ├── seguridad.py              Hash de claves y tokens, cifrado de la cédula
│   ├── catalogo.py               Los 35 trámites
│   ├── almacen.py                PDF verificados en disco
│   ├── antivirus.py              Integración con ClamAV
│   ├── metricas.py               Series de tiempo para Prometheus → Grafana
│   ├── test_*.py                 Pruebas (API, BD, seguridad, PostgreSQL…)
│   ├── Dockerfile                Imagen Alpine de la API (≤ 120 MB)
│   ├── requirements.txt          Dependencias de ejecución
│   └── requirements-dev.txt      + pruebas
├── monitoreo/
│   ├── docker-compose.yml        PostgreSQL + API + ClamAV + Prometheus + Grafana
│   ├── generar_secretos.py       Crea las claves en secretos/ (fuera de git)
│   ├── bd/01-roles.sh            Roles mupa_owner y mupa_app
│   ├── prometheus.yml            Recolección de métricas
│   ├── alertas.yml               6 alertas (antivirus y base caídos, amenazas, plazos…)
│   ├── grafana-dashboard.json    Tablero de 11 paneles
│   ├── grafana-datasource.yml
│   └── grafana-provider.yml
```

**c)** Agrega esta sección justo antes de `## Variables de entorno`:

````markdown
## Base de datos

SQLite en desarrollo, PostgreSQL 17 en Docker. El código es el mismo: sólo
cambia `DATABASE_URL`. Son ocho tablas: `cuentas`, `sesiones`, `permisos`,
`documentos`, `expedientes`, `historial`, `citas` y `bitacora`. Todo el
acceso pasa por `backend/repositorio.py`.

### Seguridad

| Medida | Qué evita |
|---|---|
| Dos roles: `mupa_owner` crea el esquema; `mupa_app` (la API) sólo lee y escribe filas | Que un fallo en la API borre tablas o cambie permisos |
| `bitacora` e `historial` sólo aceptan INSERT (permisos y triggers) | Que alguien reescriba la auditoría, ni siquiera el dueño |
| Cédula cifrada con Fernet; la clave vive fuera de la base | Que un respaldo robado exponga datos personales (Ley 81) |
| Contraseñas con PBKDF2 (600 000 iteraciones); tokens guardados como hash | Que una copia de la base sirva para entrar |
| La base está sólo en la red interna `datos`, sin puerto publicado | Conexiones desde fuera de Docker |
| Claves en `monitoreo/secretos/` (secretos de Docker), fuera de git | Contraseñas en el repositorio o visibles con `docker inspect` |
| `statement_timeout` de 5 s para la API y autenticación `scram-sha-256` | Consultas colgadas y claves débiles en la red |
| Restricciones en la base (edad, estados, aforo, un turno por horario) | Datos inválidos aunque la API tenga un error |

### Respaldos

```bash
docker compose exec bd pg_dump -U postgres -d mupa -Fc -f /tmp/respaldo.dump
docker compose cp bd:/tmp/respaldo.dump ./respaldo.dump
```

En PowerShell no saques el respaldo con `>`: convierte el archivo a UTF-16 y
lo daña. Guarda `secretos/clave_cifrado.txt` **aparte** del respaldo: sin
ella las cédulas no se pueden leer, y si se guarda junto al respaldo, el
cifrado no protege nada.

Para restaurar:

```bash
docker compose cp ./respaldo.dump bd:/tmp/respaldo.dump
docker compose exec bd pg_restore -U postgres -d mupa --clean --if-exists /tmp/respaldo.dump
```

Después, `GET /api/bitacora/verificar` debe responder `"integra": true`.
````

- [ ] **Step 7: Commit**

```bash
git add portal-permisos/backend/Dockerfile portal-permisos/backend/.dockerignore portal-permisos/monitoreo/prometheus.yml portal-permisos/README.md
git commit -m "feat: imagen Alpine de la API (<=120 MB) y sistema completo en compose" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Fuera de alcance (planes siguientes)

- **Flujo de aprobación (Fase 3):** los roles `revisor` y `director`, las transiciones de estado y la bandeja del funcionario. La columna `cuentas.rol` y la tabla `historial` ya quedan listas, y `/api/bitacora/verificar` se protegerá con esos roles.
- **Validaciones de la Fase 1:**
  - días hábiles reales con feriados;
  - leer como máximo 10 MB del archivo antes de validar;
  - corregimiento y tipo de acto contra una lista cerrada (hoy el corregimiento es texto libre y crea series de métricas sin límite).
- **Migraciones con Alembic:** `create_all` crea las tablas que faltan, pero **no altera las existentes**. Mientras no haya Alembic, un cambio de esquema en desarrollo se resuelve borrando `backend/mupa.db`.
- **Conectar `index.html` a la API** y el `calidad.yml` de CI que menciona el README pero no existe.
- **Otras mejoras de operación:** cambiar el `admin/admin` de Grafana, TLS hacia PostgreSQL (hoy la conexión no sale de la red interna) y la rotación de la clave de cifrado.
