#!/usr/bin/env bash
set -euo pipefail


here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"


docker-compose up -d db
sleep 2


# apply migration
psql "postgres://postgres:postgres@localhost:5433/raalisence?sslmode=disable" -v ON_ERROR_STOP=1 \
-f internal/db/migrations/0001_init.sql


echo "DB ready."