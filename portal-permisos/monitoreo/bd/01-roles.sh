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
