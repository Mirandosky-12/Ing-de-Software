# Guía: ver el proyecto en cualquier máquina

Sirve en **Windows (Git Bash)**, **macOS** y **Linux**, en computadoras con
procesador Intel/AMD o ARM (incluidas las Mac con chip Apple).

Todos los comandos se escriben en una terminal Bash:

- **Windows:** abre **Git Bash** (viene con Git para Windows). No uses CMD ni
  PowerShell para esta guía. En Bash las carpetas se separan con `/`, nunca con `\`.
- **macOS:** la app **Terminal**.
- **Linux:** cualquier terminal.

Cuando la guía dice **«la raíz del repositorio»** es la carpeta
`Ing-de-Software` que crea `git clone`, donde están `compose.yaml` y
`levantar.sh`.

## 0. Lo que necesitas

Para **ver** el proyecto basta con Git y Docker. Todo lo demás (portal, API,
base de datos, antivirus y monitoreo) corre en contenedores.

| Sistema | Instala | Detalle |
|---|---|---|
| Windows 10/11 | [Git para Windows](https://git-scm.com/download/win) y [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Docker Desktop usa WSL 2: si al abrirlo pide instalarlo o activar la virtualización, acéptalo y reinicia. |
| macOS | [Docker Desktop](https://www.docker.com/products/docker-desktop/) (elige la versión de tu chip: Apple o Intel) | Git ya viene; si no, `xcode-select --install`. |
| Linux | Git, Docker Engine y el plugin Compose (`docker-compose-plugin`) | Para no usar `sudo`: `sudo usermod -aG docker $USER` y vuelve a iniciar sesión. |

Comprueba, con Docker **abierto y corriendo**:

```bash
git --version
docker info > /dev/null && echo "Docker responde"
docker compose version          # tiene que ser 2.20 o más nuevo
```

**Memoria:** ClamAV ocupa entre 2 y 3 GB. En Docker Desktop, dale al menos
**4 GB** (Settings → Resources → Memory). En Windows con WSL 2 lo toma solo.

**Espacio:** las imágenes ocupan unos 2 GB la primera vez.

Node.js y Python 3.13 sólo hacen falta para **correr las pruebas** (paso 6).

## 1. Bajar el proyecto y cambiar a la rama

Elige la carpeta donde lo quieres (por ejemplo `Documentos`) y clona ahí:

```bash
cd ~/Documents                    # o la carpeta que prefieras
git clone https://github.com/Mirandosky-12/Ing-de-Software.git
cd Ing-de-Software
git checkout prueba-local
```

Si **ya** lo tenías clonado, entra a esa carpeta y trae la rama:

```bash
cd ruta/a/Ing-de-Software
git fetch
git checkout prueba-local
git pull
```

## 2. Levantar todo con un comando

Desde la raíz del repositorio:

```bash
./levantar.sh
```

El script:

1. comprueba que Docker responda;
2. si faltan las claves, las crea en `portal-permisos/monitoreo/secretos/`
   (git las ignora) con un contenedor de Python, sin instalar nada;
3. construye las imágenes del portal y de la API y levanta los servicios;
4. espera a que la API y el portal estén listos y muestra las direcciones.

La primera vez tarda varios minutos porque descarga las imágenes. Al final
debe mostrar:

| Servicio | Estado esperado |
|---|---|
| `migraciones` | `Exited (0)` |
| `portal`, `bd`, `api` | `Up … (healthy)` |
| `clamav` | `healthy` (la primera vez tarda ~2 minutos en bajar sus firmas) |
| `prometheus`, `grafana` | `Up` |

Las claves son **propias de cada máquina**: cada persona tiene las suyas y
nunca se suben a git. No copies la carpeta `secretos/` de otra computadora.

### Si un puerto ya está ocupado

Antes de levantar, el script revisa que los puertos estén libres. Si otro
programa usa alguno (es común con 3000/3001, 8000 o 5173), se detiene y te
dice cuál y cómo cambiarlo:

```text
Estos puertos ya los usa otro programa en tu máquina: GRAFANA:3001
Ciérralo, o elige otro puerto al levantar. Por ejemplo:
  PUERTO_GRAFANA=3002 ./levantar.sh
```

| Variable | Servicio | Puerto por defecto |
|---|---|---|
| `PUERTO_PORTAL` | Portal | 5173 |
| `PUERTO_API` | API | 8000 |
| `PUERTO_GRAFANA` | Grafana | 3001 |
| `PUERTO_PROMETHEUS` | Prometheus | 9090 |
| `PUERTO_CLAMAV` | ClamAV | 3310 |

Se pueden combinar: `PUERTO_PORTAL=5174 PUERTO_GRAFANA=3002 ./levantar.sh`.
Usa los mismos valores cada vez que levantes, y cambia las direcciones del
paso 3 por los puertos que elegiste. Si cambias el puerto de la API, en los
comandos del paso 5 reemplaza `localhost:8000` por el tuyo. Si cambias el del
portal, las pruebas de Playwright necesitan saberlo:
`BASE_URL=http://localhost:5174 npx playwright test`.

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
| `mupa-clamav` | `clamav/clamav-debian:1.4` | El antivirus |
| `mupa-prometheus`, `mupa-grafana` | imágenes oficiales | El monitoreo |

## 3. Qué abrir en el navegador

| Dirección | Qué es | Acceso |
|---|---|---|
| http://localhost:5173 | Portal del ciudadano | `demo@mupa.gob.pa` / `demo1234` |
| http://localhost:8000/docs | API: prueba cada ruta desde el navegador | — |
| http://localhost:3001 | Grafana (tablero de 11 paneles) | admin / admin |
| http://localhost:9090/alerts | Prometheus y sus alertas | — |

| Acción | Windows / Linux | macOS |
|---|---|---|
| Recargar sin la versión guardada | Ctrl+F5 | Cmd+Shift+R |
| Herramientas de desarrollo | F12 | Cmd+Option+I |
| Vista de celular (con las herramientas abiertas) | Ctrl+Shift+M | Cmd+Shift+M |

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

Con el sistema del paso 2 arriba, desde la raíz del repositorio, copia y pega
bloque por bloque.

**1. Crea la cuenta demo en la base** (en una máquina nueva no existe todavía;
si ya existe, responde «Ya existe una cuenta con ese correo» y no pasa nada):

```bash
curl -s -X POST localhost:8000/api/cuentas -H 'Content-Type: application/json' \
  -d '{"nombre":"Diego","apellido":"Lopez","edad":22,"organizacion":"UTP","email":"demo@mupa.gob.pa","password":"demo1234","cedula":"8-912-345","acepta_tratamiento":true}'; echo
```

**2. Inicia sesión** y guarda el token:

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/sesiones -H 'Content-Type: application/json' \
  -d '{"email":"demo@mupa.gob.pa","password":"demo1234"}' | sed -E 's/.*"token":"([^"]+)".*/\1/')
echo "$TOKEN"
```

**3. Sube un PDF** (pasa por ClamAV y devuelve su huella SHA-256), **crea la
solicitud** y **descarga la constancia**:

```bash
printf '%%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%%%EOF\n' > requisitos.pdf
SHA=$(curl -s -X POST localhost:8000/api/documentos/verificar -H "Authorization: Bearer $TOKEN" \
  -F "archivo=@requisitos.pdf;type=application/pdf" | sed -E 's/.*"sha256":"([0-9a-f]{64})".*/\1/')
echo "$SHA"

# Fecha del acto dentro de 40 días (la primera forma es Linux/Git Bash; la segunda, macOS)
FECHA=$(date -d '+40 days' +%F 2>/dev/null || date -v+40d +%F)
CODIGO=$(curl -s -X POST localhost:8000/api/solicitudes -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"permiso_id\":\"ESP-4000\",\"corregimiento\":\"San Francisco\",\"tipo_acto\":\"Concierto\",\"lugar\":\"Parque Omar\",\"fecha\":\"$FECHA\",\"hora_inicio\":\"18:00\",\"hora_fin\":\"23:00\",\"aforo\":800,\"responsable\":\"Diego Lopez\",\"telefono\":\"+507 6000-0000\",\"motivo\":\"Concierto benefico al aire libre.\",\"documento_sha256\":\"$SHA\",\"declaracion_jurada\":true}" \
  | sed -E 's/.*"codigo":"([^"]+)".*/\1/')
echo "$CODIGO"

curl -s -o "constancia-$CODIGO.pdf" "localhost:8000/api/solicitudes/$CODIGO/constancia" \
  -H "Authorization: Bearer $TOKEN"
rm requisitos.pdf
ls -l constancia-*.pdf
```

**4. Ábrela:**

| Sistema | Comando |
|---|---|
| Windows (Git Bash) | `start "constancia-$CODIGO.pdf"` |
| macOS | `open "constancia-$CODIGO.pdf"` |
| Linux | `xdg-open "constancia-$CODIGO.pdf"` |

Comprueba que la bitácora sigue íntegra:

```bash
curl -s localhost:8000/api/bitacora/verificar; echo
```

## 6. Correr las pruebas

Aquí sí hacen falta **Python 3.13** y **Node.js** (18 o más nuevo).
Python 3.14 no sirve todavía: las librerías fijadas no tienen paquetes para
esa versión.

| Sistema | Crear el entorno de Python | Activarlo |
|---|---|---|
| Windows (Git Bash) | `py -3.13 -m venv .venv` | `source .venv/Scripts/activate` |
| macOS / Linux | `python3.13 -m venv .venv` | `source .venv/bin/activate` |

**Backend** (las de ClamAV corren si el sistema está arriba). Desde la raíz:

```bash
cd portal-permisos/backend
py -3.13 -m venv .venv                      # sólo la primera vez (ver tabla de arriba)
source .venv/Scripts/activate               # ver tabla de arriba
pip install -r requirements-dev.txt         # sólo la primera vez
pytest -q
cd ../..
```

**Contra PostgreSQL real** (18 pruebas de permisos, triggers y concurrencia).
Desde la raíz, con el entorno de Python activado:

```bash
docker compose --profile pruebas up -d bd-pruebas
cd portal-permisos/backend
PRUEBAS_PG=1 pytest -m postgres -v
cd ../..
docker compose --profile pruebas rm -sf bd-pruebas
```

**Portal** (Playwright, contra el contenedor del portal en el puerto 5173).
Desde la raíz:

```bash
cd portal-permisos/calidad
npm install                                 # sólo la primera vez
npx playwright install chromium             # sólo la primera vez (en Linux: --with-deps chromium)
npx playwright test                         # todas, en escritorio y celular
npx playwright test --ui                    # ventana para verlas correr una por una
cd ../..
```

Si cambias `index.html`, reconstruye el portal para ver el cambio:
`docker compose up -d --build portal`.

## 7. Apagar todo

Desde la raíz del repositorio:

```bash
docker compose down
```

Los datos de la base se conservan para la próxima vez (`./levantar.sh` otra
vez). `docker compose down -v` también **borra los datos**: úsalo sólo si
quieres empezar de cero.

## 8. Si algo falla

| Síntoma | Causa | Solución |
|---|---|---|
| `./levantar.sh: Permission denied` | El archivo perdió el permiso de ejecución | `sh levantar.sh` |
| `./levantar.sh: No such file or directory` | No estás en la raíz del repositorio | `cd` a la carpeta `Ing-de-Software` (donde está `compose.yaml`) |
| `Docker no responde` / `error during connect` / `Cannot connect to the Docker daemon` | Docker cerrado | Abre Docker Desktop (en Linux: `sudo systemctl start docker`), espera a que diga *Running* y repite |
| `permission denied … docker.sock` (Linux) | Tu usuario no está en el grupo `docker` | `sudo usermod -aG docker $USER`, cierra sesión y vuelve a entrar |
| `migraciones` termina con `password authentication failed` | Volumen de una base anterior con otras claves (por ejemplo, borraste `secretos/`) | `docker compose down -v` (borra datos) y repite el paso 2 |
| «Estos puertos ya los usa otro programa…» o `ports are not available` / `port is already allocated` | Otro programa usa 5173, 8000, 3001, 9090 o 3310 | Ciérralo, o cambia el puerto: [Si un puerto ya está ocupado](#si-un-puerto-ya-está-ocupado) |
| `Conflict. The container name "/mupa-…" is already in use` | Quedaron contenedores de una versión anterior | `docker compose -p monitoreo down` y repite el paso 2 |
| `include` no se reconoce en `compose.yaml` | Docker Compose anterior a 2.20 | Actualiza Docker Desktop o el plugin Compose |
| `clamav` se reinicia o queda `unhealthy` | Poca memoria para Docker | Sube la memoria de Docker a 4 GB o más y repite |
| El portal se ve viejo | El navegador guardó la versión anterior | Ctrl+F5 (Mac: Cmd+Shift+R) |
| `cd: portal-permisosmonitoreo: No such file or directory` | Usaste `\` en Git Bash | Usa `/`: `cd portal-permisos/monitoreo` |
| `pip install` falla con Python 3.14 | Faltan paquetes para 3.14 | Crea el entorno con Python 3.13 (paso 6) |
