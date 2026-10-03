#!/bin/sh
set -eu

psql \
  -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=app_user="$APP_DB_USER" \
  --set=app_password="$APP_DB_PASSWORD" \
  --set=db_name="$POSTGRES_DB" <<'EOSQL'

CREATE ROLE :"app_user"
    WITH LOGIN
    PASSWORD :'app_password'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION;

GRANT CONNECT
    ON DATABASE :"db_name"
    TO :"app_user";

GRANT USAGE, CREATE
    ON SCHEMA public
    TO :"app_user";

EOSQL