# Ventanilla Única Municipal — Caso 3: Permisos Municipales

Portal en línea para solicitar permisos ante la Dirección de Permisos y Cumplimiento
del Municipio de Panamá. Sustituye los formularios físicos por un flujo digital con
trazabilidad y auditoría.

| | |
|---|---|
| **Institución** | Municipio de Panamá |
| **Personas afectadas** | +20,000 ciudadanos y empresas al año |
| **Problema** | Formularios físicos, trazabilidad limitada |
| **Tiempo actual** | 2 – 6 meses |
| **Meta** | 15 días hábiles, con flujos de aprobación y auditoría |
| **Catálogo** | 35 trámites reales tomados de [permisosycumplimiento.mupa.gob.pa](https://permisosycumplimiento.mupa.gob.pa/tramites-y-permisos/) |

**Herramientas asignadas al grupo:** Qase (calidad) · ClamAV (seguridad) · Grafana (CI/CD y observabilidad) · JavaScript + Python (lenguajes).

---

## Estructura

```
portal-permisos/
├── index.html                    Portal completo (frontend, sin dependencias)
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
├── calidad/
│   ├── casos-qase.md             27 casos de prueba para cargar en Qase
│   ├── playwright.config.js      Reportero de Qase configurado
│   ├── tests/portal.spec.js      18 pruebas automatizadas del portal
│   └── package.json
├── monitoreo/
│   ├── docker-compose.yml        PostgreSQL + API + ClamAV + Prometheus + Grafana
│   ├── generar_secretos.py       Crea las claves en secretos/ (fuera de git)
│   ├── bd/01-roles.sh            Roles mupa_owner y mupa_app
│   ├── prometheus.yml            Recolección de métricas
│   ├── alertas.yml               6 alertas (antivirus y base caídos, amenazas, plazos…)
│   ├── grafana-dashboard.json    Tablero de 11 paneles
│   ├── grafana-datasource.yml
│   └── grafana-provider.yml
└── .github/workflows/calidad.yml CI: pruebas en cada push, resultados a Qase
```

---

## Cómo levantarlo

### 1. El portal (sólo el frontend)

`index.html` no necesita compilación ni servidor. Ábrelo en el navegador, o:

```bash
npx serve -l 5173 .
```

Cuenta de prueba: **demo@mupa.gob.pa** / **demo1234**

Funciona completo sin backend: el catálogo, las validaciones, la verificación
de formato y el cálculo real de la huella SHA-256 corren en el navegador. La
única parte simulada es la respuesta de ClamAV (para probarla, sube un archivo
cuyo nombre contenga `eicar` y verás el rechazo).

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

### 4. Las pruebas

```bash
cd calidad
npm install
npx playwright install chromium
npm test                    # local
npm run test:qase           # sube resultados a Qase
```

```bash
cd backend
pytest -v                   # local
pytest --qase-mode=testops  # sube resultados a Qase
```

---

## Cómo se conectan las cuatro herramientas

```
        Navegador (JavaScript)
        index.html · validación, SHA-256, interfaz
                    │
                    │ HTTPS
                    ▼
        API (Python · FastAPI)
        ├──► ClamAV  ── escanea cada PDF antes de guardarlo
        ├──► SHA-256 ── huella de integridad del documento
        └──► /metrics ── expone las series de tiempo
                    │
                    ▼
        Prometheus  ── raspa /metrics cada 15 s
                    │
                    ▼
        Grafana     ── 11 paneles + 5 alertas

        Qase  ◄──  Playwright (portal) y pytest (API), en cada push
```

### ClamAV — seguridad documental

`backend/antivirus.py` habla con el demonio `clamd` por socket TCP usando el
comando **INSTREAM**: el PDF viaja en memoria, se escanea, y **sólo si sale
limpio se guarda**. Un archivo nunca toca el disco sin haber sido revisado.

La cadena de verificación tiene cinco pasos, del más barato al más caro:

| # | Verificación | Qué detiene |
|---|---|---|
| 1 | Extensión `.pdf` **y** bytes mágicos `%PDF-` | Un `.exe` renombrado a `.pdf`. El MIME que manda el navegador es falsificable; los bytes no. |
| 2 | Tamaño ≤ 10 MB | Cargas que saturarían el almacenamiento |
| 3 | ClamAV INSTREAM | Malware incrustado en el PDF |
| 4 | SHA-256 del contenido | Identifica al documento de forma única |
| 5 | Sellado en bitácora | Deja constancia con fecha y hora |

**Decisión importante:** si ClamAV no responde, la API devuelve **503** y no
acepta el documento. Un expediente sin escanear es peor que un trámite lento.

### Grafana — observabilidad

Grafana no lee la aplicación: **Prometheus** raspa `/metrics` cada 15 segundos
y guarda las series; Grafana las consulta. `backend/metricas.py` define qué se
mide:

| Métrica | Para qué sirve |
|---|---|
| `mupa_solicitudes_creadas_total` | Demanda por permiso y corregimiento |
| `mupa_tramite_dias` | Días reales hasta la resolución, contra la meta de 15 |
| `mupa_documentos_verificados_total` | Cuántos PDF se rechazan y por qué |
| `mupa_amenazas_detectadas_total` | Amenazas bloqueadas, por firma |
| `mupa_antivirus_arriba` | 1 / 0 según responda `clamd` |
| `mupa_http_segundos` | Latencia de la API |

Todas llevan la etiqueta `municipio`, y el tablero tiene un selector para
filtrar por ella: es lo que permite que San Miguelito y La Chorrera se sumen
sin tocar el tablero.

Las alertas de `alertas.yml` cubren antivirus caído, amenaza detectada, más de
30 % de rechazos, API lenta y trámites que se salen del plazo.

### Qase — gestión de la calidad

`calidad/casos-qase.md` tiene los 27 casos de prueba listos para cargar. Cada
prueba automatizada lleva `qase.id(N)`, que la amarra a su caso; cuando corre
en CI, Qase recibe el resultado, la captura de pantalla del fallo y el video.

La suite más importante es **Seguridad documental** (VUM-20 a VUM-25): si
alguna de esas falla, el despliegue no sale.

### JavaScript y Python

- **JavaScript** — el portal completo, sin framework ni build. Un solo archivo
  que cualquiera del grupo puede abrir, leer y modificar. Usa `crypto.subtle`
  del navegador para calcular el SHA-256 de verdad, y `FileReader` para leer
  los bytes mágicos del PDF antes de enviarlo.
- **Python** — la API, la integración con ClamAV, la instrumentación y las
  pruebas del backend.

---

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
docker compose exec -u postgres bd pg_dump -d mupa -Fc -f /tmp/respaldo.dump
docker compose cp bd:/tmp/respaldo.dump ./respaldo.dump
```

`-u postgres` hace falta: dentro del contenedor la base sólo acepta al
usuario de sistema `postgres` por el socket local (autenticación `peer`).
En PowerShell no saques el respaldo con `>`: convierte el archivo a UTF-16 y
lo daña. Guarda `secretos/clave_cifrado.txt` **aparte** del respaldo: sin
ella las cédulas no se pueden leer, y si se guarda junto al respaldo, el
cifrado no protege nada.

Para restaurar:

```bash
docker compose cp ./respaldo.dump bd:/tmp/respaldo.dump
docker compose exec -u postgres bd pg_restore -d mupa --clean --if-exists /tmp/respaldo.dump
```

Después, `GET /api/bitacora/verificar` debe responder `"integra": true`.

## Variables de entorno

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

# pruebas
QASE_MODE=testops
QASE_TESTOPS_API_TOKEN=...        # Qase → Perfil → API tokens
QASE_PROJECT=VUM
```

En GitHub, `QASE_TOKEN` va en *Settings → Secrets and variables → Actions*.

---

## Marco legal aplicable

| Norma | Qué exige al sistema |
|---|---|
| **Ley 106 de 1973** — Régimen Municipal | Competencia del municipio para otorgar permisos |
| **Ley 51 de 2008** — Documentos y firma electrónica | Validez legal del expediente digital; el sellado con hash es lo que la sustenta |
| **Ley 81 de 2019** — Protección de datos personales | Consentimiento en el registro, minimización de datos, derecho de acceso |
| **Ley 83 de 2019** — Servicios digitales del Estado | Interoperabilidad y trámite en línea |
| **Acuerdo Municipal N.° 130 de 2016** | Declaración jurada del solicitante |
