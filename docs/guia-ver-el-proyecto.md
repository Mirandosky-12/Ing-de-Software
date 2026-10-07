# Guía: ver el proyecto desde la terminal (Git Bash)

Todos los comandos son para **Git Bash** en Windows. En Bash las carpetas se
separan con `/`, nunca con `\`.

## 0. Lo que necesitas

| Herramienta | Para qué | Cómo comprobarlo |
|---|---|---|
| Git | Bajar el proyecto | `git --version` |
| Docker Desktop, **abierto** | Base de datos, API, ClamAV, Prometheus, Grafana | `docker info` (sin error) |
| Node.js | Servir el portal y correr sus pruebas | `node -v` |
| Python 3.13 | Claves y pruebas del backend | `py -3.13 --version` |

Python 3.14 no sirve todavía: las librerías fijadas no tienen paquetes para esa versión.

## 1. Bajar el proyecto y cambiar a la rama

Si ya lo tienes, salta al `git checkout`.

```bash
cd ~/Documents/PROYECTOING
git clone https://github.com/Mirandosky-12/Ing-de-Software.git
cd Ing-de-Software
git checkout prueba-local
git pull
```

## 2. Crear las claves (una sola vez por computadora)

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software/portal-permisos/monitoreo
py -3.13 generar_secretos.py
```

Crea `monitoreo/secretos/` (git lo ignora). Si dice «Ya existen… No se
sobrescribe nada», las claves ya estaban: sigue con el paso 3.

## 3. Levantar el sistema

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software/portal-permisos/monitoreo
docker compose up -d --build
docker compose ps -a
```

Espera hasta ver:

| Servicio | Estado esperado |
|---|---|
| `migraciones` | `Exited (0)` |
| `bd`, `api` | `Up … (healthy)` |
| `clamav` | `healthy` (la primera vez tarda ~2 minutos en bajar sus firmas) |
| `prometheus`, `grafana` | `Up` |

Comprueba la API:

```bash
curl -s localhost:8000/salud; echo
```

Debe decir `"estado":"ok"` con `"base_de_datos":{"arriba":true,…}`.

## 4. Abrir el portal

En **otra** terminal, que se queda abierta mientras usas el portal:

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software/portal-permisos
npx serve -l 5173 .
```

> El servidor tiene que arrancar **desde `portal-permisos`**. Si el navegador
> muestra «Files within …» (una lista de archivos), lo arrancaste en otra
> carpeta: Ctrl+C y repite los dos comandos.

## 5. Qué abrir en el navegador

| Dirección | Qué es | Acceso |
|---|---|---|
| http://localhost:5173 | Portal del ciudadano | `demo@mupa.gob.pa` / `demo1234` |
| http://localhost:8000/docs | API: prueba cada ruta desde el navegador | — |
| http://localhost:3001 | Grafana (tablero de 11 paneles) | admin / admin |
| http://localhost:9090/alerts | Prometheus y sus alertas | — |

Si ves una versión vieja del portal, recarga con **Ctrl+F5**. Para la vista de
celular: **F12** y luego **Ctrl+Shift+M**.

## 6. Recorrido sugerido en el portal

1. **Inicio:** el aviso «Requiere tu atención» y los contadores (tócalos: llevan a la lista filtrada).
2. **Solicitar permiso:** escribe «nocturno» en el buscador, avanza los pasos y deja un campo vacío para ver cómo el error señala el campo.
3. **Mis solicitudes → Ver detalle:** línea de tiempo, «Qué sigue» y **Descargar constancia** (PDF).
4. **Citas:** elige la fecha con los atajos de días hábiles.
5. **Tema oscuro** desde el menú; el portal lo recuerda.

El portal todavía usa datos simulados: no está conectado a la API. Su
constancia lleva un código de verificación; la de la API, además, el sello de
la bitácora de auditoría.

## 7. La constancia desde la API (con datos reales)

Con el sistema del paso 3 arriba, copia y pega bloque por bloque:

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

## 8. Correr las pruebas

**Backend** (79+ pruebas; las de ClamAV corren si el sistema está arriba):

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software/portal-permisos/backend
py -3.13 -m venv .venv                      # sólo la primera vez
source .venv/Scripts/activate
pip install -r requirements-dev.txt         # sólo la primera vez
pytest -q
```

**Contra PostgreSQL real** (18 pruebas de permisos, triggers y concurrencia):

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software/portal-permisos/monitoreo
docker compose --profile pruebas up -d bd-pruebas
cd ../backend
PRUEBAS_PG=1 pytest -m postgres -v
cd ../monitoreo && docker compose --profile pruebas rm -sf bd-pruebas
```

**Portal** (Playwright; con el servidor del paso 4 corriendo):

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software/portal-permisos/calidad
npm install                                 # sólo la primera vez
npx playwright install chromium             # sólo la primera vez
npx playwright test                         # todas, en escritorio y celular
npx playwright test --ui                    # ventana para verlas correr una por una
```

## 9. Apagar todo

1. En la terminal del portal: **Ctrl+C**.
2. El resto:

```bash
cd ~/Documents/PROYECTOING/Ing-de-Software/portal-permisos/monitoreo
docker compose down
```

`docker compose down -v` también **borra los datos de la base**: úsalo sólo si
quieres empezar de cero.

## 10. Si algo falla

| Síntoma | Causa | Solución |
|---|---|---|
| `cd: portal-permisosmonitoreo: No such file or directory` | Usaste `\` en Bash | Usa `/`: `cd portal-permisos/monitoreo` |
| El navegador muestra «Files within …» | `npx serve` se arrancó fuera de `portal-permisos` | Ctrl+C y repite el paso 4 |
| `migraciones` termina con `password authentication failed` | Volumen de una base anterior con otras claves | `docker compose down -v` (borra datos) y repite el paso 3 |
| `docker: error during connect` | Docker Desktop cerrado | Ábrelo y espera a que diga *Running* |
| `port is already allocated` / puerto ocupado | Otro programa usa 8000, 5173 o 3001 | Ciérralo, o usa otro puerto para el portal: `npx serve -l 5174 .` |
| `docker compose exec bd psql …` falla con `Peer authentication failed` | La base sólo acepta al usuario de sistema `postgres` | Agrega `-u postgres`: `docker compose exec -u postgres bd psql -d mupa` |
| Una ruta como `/app/x` se convierte en `C:/Program Files/Git/app/x` | Git Bash traduce rutas al llamar a Docker | Antepón `MSYS_NO_PATHCONV=1` al comando |
| `pip install` falla con Python 3.14 | Faltan paquetes para 3.14 | Crea el entorno con `py -3.13 -m venv .venv` |
