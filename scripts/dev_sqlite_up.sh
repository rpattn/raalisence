#!/usr/bin/env bash
set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

DB_PATH=${RAAL_DB_PATH:-"./raalisence.db"}
SQLITE_BIN=${SQLITE_BIN:-sqlite3}

if ! command -v "$SQLITE_BIN" >/dev/null 2>&1; then
  echo "sqlite3 binary not found. Install sqlite3 or set SQLITE_BIN" >&2
  exit 1
fi

# create db file and apply migration
"$SQLITE_BIN" "$DB_PATH" < internal/db/migrations_sqlite/0001_init.sql

echo "SQLite DB ready at $DB_PATH"
