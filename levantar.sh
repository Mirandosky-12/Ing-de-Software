#!/bin/sh
# Levanta todo el sistema de la Ventanilla Única con un solo comando:
#
#   ./levantar.sh
#
# Sirve en Git Bash (Windows), macOS y Linux. Sólo necesita Docker: si faltan
# las claves, las crea con un contenedor de Python, sin instalar nada más.
#
# Si un puerto ya está en uso en tu máquina, cámbialo al levantar:
#   PUERTO_GRAFANA=3002 ./levantar.sh
# Variables: PUERTO_PORTAL (5173), PUERTO_API (8000), PUERTO_GRAFANA (3001),
#            PUERTO_PROMETHEUS (9090), PUERTO_CLAMAV (3310).
set -eu
cd "$(dirname "$0")"

PUERTO_PORTAL="${PUERTO_PORTAL:-5173}"
PUERTO_API="${PUERTO_API:-8000}"
PUERTO_GRAFANA="${PUERTO_GRAFANA:-3001}"
PUERTO_PROMETHEUS="${PUERTO_PROMETHEUS:-9090}"
PUERTO_CLAMAV="${PUERTO_CLAMAV:-3310}"
export PUERTO_PORTAL PUERTO_API PUERTO_GRAFANA PUERTO_PROMETHEUS PUERTO_CLAMAV

if ! docker info >/dev/null 2>&1; then
  echo "Docker no responde. Abre Docker Desktop (o inicia el servicio de Docker) y vuelve a intentar." >&2
  exit 1
fi

# Si el sistema todavía no corre, sus puertos tienen que estar libres.
# curl devuelve 7 cuando nadie escucha en el puerto. En Windows ese rechazo
# tarda ~2 s en llegar, por eso el límite es de 4 s y no menos.
if command -v curl >/dev/null 2>&1 && [ -z "$(docker compose ps -q 2>/dev/null)" ]; then
  ocupados=""
  for par in PORTAL:$PUERTO_PORTAL API:$PUERTO_API GRAFANA:$PUERTO_GRAFANA \
             PROMETHEUS:$PUERTO_PROMETHEUS CLAMAV:$PUERTO_CLAMAV; do
    codigo=0
    curl -s -o /dev/null --max-time 4 "http://127.0.0.1:${par#*:}" || codigo=$?
    if [ "$codigo" -ne 7 ]; then
      ocupados="$ocupados $par"
    fi
  done
  if [ -n "$ocupados" ]; then
    echo "Estos puertos ya los usa otro programa en tu máquina:$ocupados" >&2
    echo "Ciérralo, o elige otro puerto al levantar. Por ejemplo:" >&2
    for par in $ocupados; do
      echo "  PUERTO_${par%%:*}=$(( ${par#*:} + 1 )) ./levantar.sh" >&2
    done
    exit 1
  fi
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

cat <<FIN

Listo:
  Portal       http://localhost:$PUERTO_PORTAL    demo@mupa.gob.pa / demo1234
  API          http://localhost:$PUERTO_API/docs
  Grafana      http://localhost:$PUERTO_GRAFANA    admin / admin
  Prometheus   http://localhost:$PUERTO_PROMETHEUS

ClamAV tarda unos 2 minutos la primera vez en bajar sus firmas.
Para apagar: docker compose down
FIN
