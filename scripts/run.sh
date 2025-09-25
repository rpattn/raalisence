#!/usr/bin/env bash
set -euo pipefail

db_conn="postgres://postgres:postgres@localhost:5433/raalisence?sslmode=disable"
echo "DB Set to: $db_conn"

export RAAL_SERVER_ADDR=${RAAL_SERVER_ADDR:-":8080"}
export RAAL_DB_DSN=${RAAL_DB_DSN:-$db_conn}
export RAAL_SERVER_ADMIN_API_KEY=${RAAL_SERVER_ADMIN_API_KEY:-"dev-admin-key"}


# Generate dev keys if not provided (uses OpenSSL for reliability)
if [[ -z "${RAAL_SIGNING_PRIVATE_KEY_PEM:-}" || -z "${RAAL_SIGNING_PUBLIC_KEY_PEM:-}" ]]; then
echo "Generating dev ECDSA keys via OpenSSL (P-256)..."
scripts/gen_keys.sh >/tmp/raal_keys.env
# shellcheck disable=SC1091
source /tmp/raal_keys.env
export RAAL_SIGNING_PRIVATE_KEY_PEM RAAL_SIGNING_PUBLIC_KEY_PEM
fi


# Show minimal env summary (not the private key)
echo "RAAL_SERVER_ADDR=$RAAL_SERVER_ADDR"
echo "RAAL_DB_DSN=$RAAL_DB_DSN"
echo "RAAL_SERVER_ADMIN_API_KEY set: $([[ -n "${RAAL_SERVER_ADMIN_API_KEY}" ]] && echo yes || echo no)"
echo "Signing keys present: $([[ -n "${RAAL_SIGNING_PRIVATE_KEY_PEM}" && -n "${RAAL_SIGNING_PUBLIC_KEY_PEM}" ]] && echo yes || echo no)"


exec go run ./cmd/raalisence