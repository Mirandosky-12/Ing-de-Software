# Guía: ver el proyecto desde la terminal (Git Bash)

Todos los comandos son para **Git Bash** en Windows. En Bash las carpetas se
separan con `/`, nunca con `\`.

## 0. Lo que necesitas

Para **ver** el proyecto basta con:

| Herramienta | Cómo comprobarlo |
|---|---|
| Git | `git --version` |
| Docker Desktop, **abierto** (o Docker Engine en Linux), con Compose 2.20 o más nuevo | `docker info` sin error y `docker compose version` |

Todo lo demás (base de datos, API, portal, antivirus, monitoreo) corre en
contenedores. Node.js y Python 3.13 sólo hacen falta para **correr las
pruebas** (paso 6).

## 1. Bajar el proyecto y cambiar a la rama

Si ya lo tienes, salta al `git checkout`.

```bash
cd ~/Documents/PROYECTOING
git clone https://github.com/Mirandosky-12/Ing-de-Software.git
cd Ing-de-Software
git checkout prueba-local
git pull
```

## 2. Levantar todo con un comando

Desde la raíz del repositorio:

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software
./levantar.sh
```

El script:

1. comprueba que Docker responda;
2. si faltan las claves, las crea en `portal-permisos/monitoreo/secretos/`
   (git las ignora) con un contenedor de Python, sin instalar nada;
3. construye las imágenes del portal y de la API y levanta los servicios;
4. espera a que la API y el portal estén listos y muestra las direcciones.

La primera vez tarda unos minutos porque descarga las imágenes. Al final debe
mostrar:

| Servicio | Estado esperado |
|---|---|
| `migraciones` | `Exited (0)` |
| `portal`, `bd`, `api` | `Up … (healthy)` |
| `clamav` | `healthy` (la primera vez tarda ~2 minutos en bajar sus firmas) |
| `prometheus`, `grafana` | `Up` |

Si las claves ya existen, `docker compose up -d --build` desde la raíz hace lo
mismo que el script. Para ver el estado en cualquier momento:

```bash
docker compose ps -a
curl -s localhost:8000/salud; echo        # "estado":"ok" y la base "arriba":true
```

| Contenedor | Imagen | Qué corre |
|---|---|---|
| `mupa-portal` | `mupa-portal:local` (`portal-permisos/Dockerfile`) | nginx sin privilegios sirviendo `index.html` |
| `mupa-api` | `mupa-api:local` (`portal-permisos/backend/Dockerfile`) | La API FastAPI |
| `mupa-migraciones` | `mupa-api:local` | Crea tablas y permisos, y termina |
| `mupa-bd` | `postgres:17-alpine` | La base, sin puerto al exterior |
| `mupa-clamav`, `mupa-prometheus`, `mupa-grafana` | imágenes oficiales | Antivirus y monitoreo |

## 3. Qué abrir en el navegador

| Dirección | Qué es | Acceso |
|---|---|---|
| http://localhost:5173 | Portal del ciudadano | `demo@mupa.gob.pa` / `demo1234` |
| http://localhost:8000/docs | API: prueba cada ruta desde el navegador | — |
| http://localhost:3001 | Grafana (tablero de 11 paneles) | admin / admin |
| http://localhost:9090/alerts | Prometheus y sus alertas | — |

Si ves una versión vieja del portal, recarga con **Ctrl+F5**. Para la vista de
celular: **F12** y luego **Ctrl+Shift+M**.

## 4. Recorrido sugerido en el portal

1. **Inicio:** el aviso «Requiere tu atención» y los contadores (tócalos: llevan a la lista filtrada).
2. **Solicitar permiso:** escribe «nocturno» en el buscador, avanza los pasos y deja un campo vacío para ver cómo el error señala el campo.
3. **Mis solicitudes → Ver detalle:** línea de tiempo, «Qué sigue» y **Descargar constancia** (PDF).
4. **Citas:** elige la fecha con los atajos de días hábiles.
5. **Tema oscuro** desde el menú; el portal lo recuerda.

El portal todavía usa datos simulados: no está conectado a la API. Su
constancia lleva un código de verificación; la de la API, además, el sello de
la bitácora de auditoría.

## 5. La constancia desde la API (con datos reales)

Con el sistema del paso 2 arriba, copia y pega bloque por bloque:

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software

# Inicia sesión y guarda el token
TOKEN=$(curl -s -X POST localhost:8000/api/sesiones -H 'Content-Type: application/json' \
  -d '{"email":"demo@mupa.gob.pa","password":"demo1234"}' | sed -E 's/.*"token":"([^"]+)".*/\1/')
echo "$TOKEN"
```

Si `TOKEN` sale vacío o con un error, la cuenta demo aún no existe en la base:
créala una vez y repite el bloque anterior.

```bash
curl -s -X POST localhost:8000/api/cuentas -H 'Content-Type: application/json' \
  -d '{"nombre":"Diego","apellido":"Lopez","edad":22,"organizacion":"UTP","email":"demo@mupa.gob.pa","password":"demo1234","cedula":"8-912-345","acepta_tratamiento":true}'; echo
```

```bash
# Sube un PDF: pasa por ClamAV y devuelve su huella SHA-256
printf '%%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%%%EOF\n' > requisitos.pdf
SHA=$(curl -s -X POST localhost:8000/api/documentos/verificar -H "Authorization: Bearer $TOKEN" \
  -F "archivo=@requisitos.pdf;type=application/pdf" | sed -E 's/.*"sha256":"([0-9a-f]{64})".*/\1/')
echo "$SHA"

# Crea la solicitud (el acto, dentro de 40 días)
FECHA=$(date -d '+40 days' +%F)
CODIGO=$(curl -s -X POST localhost:8000/api/solicitudes -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"permiso_id\":\"ESP-4000\",\"corregimiento\":\"San Francisco\",\"tipo_acto\":\"Concierto\",\"lugar\":\"Parque Omar\",\"fecha\":\"$FECHA\",\"hora_inicio\":\"18:00\",\"hora_fin\":\"23:00\",\"aforo\":800,\"responsable\":\"Diego Lopez\",\"telefono\":\"+507 6000-0000\",\"motivo\":\"Concierto benefico al aire libre.\",\"documento_sha256\":\"$SHA\",\"declaracion_jurada\":true}" \
  | sed -E 's/.*"codigo":"([^"]+)".*/\1/')
echo "$CODIGO"

# Descarga la constancia y ábrela
curl -s -o "constancia-$CODIGO.pdf" "localhost:8000/api/solicitudes/$CODIGO/constancia" \
  -H "Authorization: Bearer $TOKEN"
start "constancia-$CODIGO.pdf"
rm requisitos.pdf
```

Comprueba que la bitácora sigue íntegra:

```bash
curl -s localhost:8000/api/bitacora/verificar; echo
```

## 6. Correr las pruebas

Aquí sí hacen falta **Python 3.13** (`py -3.13 --version`) y **Node.js**
(`node -v`). Python 3.14 no sirve todavía: las librerías fijadas no tienen
paquetes para esa versión.

**Backend** (las de ClamAV corren si el sistema está arriba):

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software/portal-permisos/backend
py -3.13 -m venv .venv                      # sólo la primera vez
source .venv/Scripts/activate               # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt         # sólo la primera vez
pytest -q
```

**Contra PostgreSQL real** (18 pruebas de permisos, triggers y concurrencia):

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software
docker compose --profile pruebas up -d bd-pruebas
cd portal-permisos/backend
PRUEBAS_PG=1 pytest -m postgres -v
cd ../.. && docker compose --profile pruebas rm -sf bd-pruebas
```

**Portal** (Playwright, contra el contenedor del portal en el puerto 5173):

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software/portal-permisos/calidad
npm install                                 # sólo la primera vez
npx playwright install chromium             # sólo la primera vez
npx playwright test                         # todas, en escritorio y celular
npx playwright test --ui                    # ventana para verlas correr una por una
```

Si cambias `index.html`, reconstruye el portal para ver el cambio:
`docker compose up -d --build portal`.

## 7. Apagar todo

Desde la raíz del repositorio:

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software
docker compose down
```

Los datos de la base se conservan para la próxima vez. `docker compose down -v`
también **borra los datos**: úsalo sólo si quieres empezar de cero.

## 8. Si algo falla

| Síntoma | Causa | Solución |
|---|---|---|
| `./levantar.sh: Permission denied` | El archivo perdió el permiso de ejecución | `sh levantar.sh` |
| `Docker no responde` / `error during connect` | Docker Desktop cerrado | Ábrelo, espera a que diga *Running* y repite |
| `migraciones` termina con `password authentication failed` | Volumen de una base anterior con otras claves | `docker compose down -v` (borra datos) y repite el paso 2 |
| `port is already allocated` | Otro programa usa 5173, 8000, 3001, 9090 o 3310 | Ciérralo y repite el paso 2 |
| `Conflict. The container name "/mupa-…" is already in use` | Quedaron contenedores de una versión anterior | `docker compose -p monitoreo down` y repite el paso 2 |
| `include` no se reconoce en `compose.yaml` | Docker Compose anterior a 2.20 | Actualiza Docker Desktop |
| El portal se ve viejo | El navegador guardó la versión anterior | Ctrl+F5 |
| `cd: portal-permisosmonitoreo: No such file or directory` | Usaste `\` en Bash | Usa `/`: `cd portal-permisos/monitoreo` |
| `docker compose exec bd psql …` falla con `Peer authentication failed` | La base sólo acepta al usuario de sistema `postgres` | Agrega `-u postgres`: `docker compose exec -u postgres bd psql -d mupa` |
| Una ruta como `/app/x` se convierte en `C:/Program Files/Git/app/x` | Git Bash traduce rutas al llamar a Docker | Antepón `MSYS_NO_PATHCONV=1` al comando |
| `pip install` falla con Python 3.14 | Faltan paquetes para 3.14 | Crea el entorno con `py -3.13 -m venv .venv` |
