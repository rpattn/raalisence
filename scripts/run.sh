#!/usr/bin/env bash
set -euo pipefail


export RAAL_SERVER_ADDR=":8080"
export RAAL_DB_DSN="postgres://postgres:postgres@localhost:5432/raalisence?sslmode=disable"


# Generate dev keys if not provided
if [[ -z "${RAAL_SIGNING_PRIVATE_KEY_PEM:-}" || -z "${RAAL_SIGNING_PUBLIC_KEY_PEM:-}" ]]; then
echo "Generating dev ECDSA keys..."
go test ./internal/crypto -run TestGeneratePEM -v -count=1 >/tmp/keys.txt 2>/dev/null || true
RAAL_SIGNING_PRIVATE_KEY_PEM=$(grep -A 1000 "BEGIN EC PRIVATE KEY" /tmp/keys.txt | sed -n '/BEGIN EC PRIVATE KEY/,/END EC PRIVATE KEY/p')
RAAL_SIGNING_PUBLIC_KEY_PEM=$(grep -A 1000 "BEGIN PUBLIC KEY" /tmp/keys.txt | sed -n '/BEGIN PUBLIC KEY/,/END PUBLIC KEY/p')
export RAAL_SIGNING_PRIVATE_KEY_PEM RAAL_SIGNING_PUBLIC_KEY_PEM
fi


export RAAL_SERVER_ADMIN_API_KEY="dev-admin-key"


go run ./cmd/raalisence