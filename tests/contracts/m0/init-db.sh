#!/bin/sh
# Official PostgreSQL empty-volume initialization; never touch Gitea tables.
set -eu
for name in forge idp; do
    password=$(cat "/run/m0-db/$name-password")
    case "$password" in
        ''|*[!a-f0-9]*) exit 1 ;;
    esac
    {
        printf "CREATE ROLE m0_%s LOGIN PASSWORD '%s';\n" "$name" "$password"
        printf 'CREATE DATABASE m0_%s OWNER m0_%s;\n' "$name" "$name"
    } | psql -X -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres >/dev/null
done
