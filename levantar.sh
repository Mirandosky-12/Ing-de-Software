#!/bin/sh
# Levanta todo el sistema de la Ventanilla Única con un solo comando:
#
#   ./levantar.sh
#
# Sirve en Git Bash (Windows), macOS y Linux. Sólo necesita Docker: si faltan
# las claves, las crea con un contenedor de Python, sin instalar nada más.
set -eu
cd "$(dirname "$0")"

if ! docker info >/dev/null 2>&1; then
  echo "Docker no responde. Abre Docker Desktop (o inicia el servicio de Docker) y vuelve a intentar." >&2
  exit 1
fi

MONITOREO=portal-permisos/monitoreo
if [ ! -f "$MONITOREO/secretos/clave_cifrado.txt" ]; then
  echo "==> Creando las claves en $MONITOREO/secretos/ (una sola vez)"
  # pwd -W da la ruta de Windows en Git Bash; en macOS y Linux no existe.
  CARPETA="$(cd "$MONITOREO" && (pwd -W 2>/dev/null || pwd))"
  MSYS_NO_PATHCONV=1 docker run --rm --user "$(id -u):$(id -g)" \
    -v "$CARPETA:/monitoreo" -w /monitoreo python:3.13-alpine python generar_secretos.py
fi

echo "==> Construyendo y levantando los servicios"
docker compose up -d --build

echo "==> Esperando a que la API y el portal estén listos"
listo=""
for _ in $(seq 1 60); do
  if docker compose ps -a migraciones --format '{{.Status}}' | grep -q 'Exited ([1-9]'; then
    echo "Las migraciones fallaron:" >&2
    docker compose logs --tail 20 migraciones >&2
    echo "Si dice «password authentication failed», quedó una base de un intento anterior" >&2
    echo "con otras claves. En desarrollo: docker compose down -v (BORRA los datos) y repite." >&2
    exit 1
  fi
  if docker compose ps api --format '{{.Status}}' | grep -q healthy &&
     docker compose ps portal --format '{{.Status}}' | grep -q healthy; then
    listo=1
    break
  fi
  sleep 3
done

docker compose ps -a --format 'table {{.Service}}\t{{.Status}}'
if [ -z "$listo" ]; then
  echo "La API o el portal no quedaron listos en 3 minutos. Revisa: docker compose logs api portal" >&2
  exit 1
fi

cat <<'FIN'

Listo:
  Portal       http://localhost:5173    demo@mupa.gob.pa / demo1234
  API          http://localhost:8000/docs
  Grafana      http://localhost:3001    admin / admin
  Prometheus   http://localhost:9090

ClamAV tarda unos 2 minutos la primera vez en bajar sus firmas.
Para apagar: docker compose down
FIN
