#!/usr/bin/env bash
# scripts/run.sh
set -euo pipefail

# --- sanity checks ---
command -v openssl >/dev/null || { echo "OpenSSL is required"; exit 1; }
command -v base64  >/dev/null || { echo "base64 is required";  exit 1; }
command -v go      >/dev/null || { echo "Go toolchain is required"; exit 1; }

# --- config defaults ---
: "${RAAL_SERVER_ADDR:=:8080}"
: "${RAAL_DB_DRIVER:=pgx}"   # pgx | sqlite3
: "${RAAL_DB_PATH:=./raalisence.db}"
: "${RAAL_DB_DSN:=postgres://postgres:postgres@localhost:5433/raalisence?sslmode=disable}"
: "${RAAL_SERVER_ADMIN_API_KEY:=dev-admin-key}"

echo "RAAL_SERVER_ADDR=$RAAL_SERVER_ADDR"
echo "DB Driver: $RAAL_DB_DRIVER"
if [[ "$RAAL_DB_DRIVER" == "sqlite3" ]]; then
  echo "DB Path: $RAAL_DB_PATH"
else
  echo "DB DSN: $RAAL_DB_DSN"
fi
echo "RAAL_SERVER_ADMIN_API_KEY set: $([[ -n "${RAAL_SERVER_ADMIN_API_KEY}" ]] && echo yes || echo no)"

# --- helper: base64 decode (Linux/macOS) ---
b64dec() {
  # read from stdin; GNU uses -d, BSD/macOS uses -D
  if base64 --help 2>&1 | grep -q ' -d'; then
    base64 -d
  else
    base64 -D
  fi
}

# --- generate/resolve signing keys ---
need_keys=false
if [[ -z "${RAAL_SIGNING_PRIVATE_KEY_PEM:-}" || -z "${RAAL_SIGNING_PUBLIC_KEY_PEM:-}" ]]; then
  # try *_B64 env first
  if [[ -n "${RAAL_SIGNING_PRIVATE_KEY_PEM_B64:-}" && -n "${RAAL_SIGNING_PUBLIC_KEY_PEM_B64:-}" ]]; then
    RAAL_SIGNING_PRIVATE_KEY_PEM="$(printf '%s' "$RAAL_SIGNING_PRIVATE_KEY_PEM_B64" | b64dec)"
    RAAL_SIGNING_PUBLIC_KEY_PEM="$(printf '%s' "$RAAL_SIGNING_PUBLIC_KEY_PEM_B64" | b64dec)"
    export RAAL_SIGNING_PRIVATE_KEY_PEM RAAL_SIGNING_PUBLIC_KEY_PEM
  else
    need_keys=true
  fi
fi

if $need_keys; then
  echo "No signing keys found; generating dev ECDSA keys (P-256) via OpenSSL…"
  # ensure generator is executable
  if [[ ! -x "scripts/gen_keys.sh" ]]; then
    chmod +x scripts/gen_keys.sh
  fi
  tmp_env="$(mktemp)"
  trap 'rm -f "$tmp_env"' EXIT
  scripts/gen_keys.sh >"$tmp_env"
  # shellcheck disable=SC1090
  # eval ONLY the export lines printed by gen_keys.sh
  eval "$(grep -E '^export RAAL_SIGNING_.*_B64=' "$tmp_env")"
  if [[ -z "${RAAL_SIGNING_PRIVATE_KEY_PEM_B64:-}" || -z "${RAAL_SIGNING_PUBLIC_KEY_PEM_B64:-}" ]]; then
    echo "Key generator did not produce *_B64 vars" >&2
    exit 1
  fi
  RAAL_SIGNING_PRIVATE_KEY_PEM="$(printf '%s' "$RAAL_SIGNING_PRIVATE_KEY_PEM_B64" | b64dec)"
  RAAL_SIGNING_PUBLIC_KEY_PEM="$(printf '%s' "$RAAL_SIGNING_PUBLIC_KEY_PEM_B64"   | b64dec)"
  export RAAL_SIGNING_PRIVATE_KEY_PEM RAAL_SIGNING_PUBLIC_KEY_PEM
fi

# --- minimal env summary (never print the keys) ---
echo "Signing keys present: $([[ -n "${RAAL_SIGNING_PRIVATE_KEY_PEM:-}" && -n "${RAAL_SIGNING_PUBLIC_KEY_PEM:-}" ]] && echo yes || echo no)"

# --- DB bootstrap (optional helpers) ---
if [[ "$RAAL_DB_DRIVER" == "sqlite3" ]]; then
  if [[ -x ./scripts/dev_sqlite_up.sh ]]; then
    ./scripts/dev_sqlite_up.sh
  else
    # ensure parent dir for sqlite path exists
    mkdir -p "$(dirname -- "$RAAL_DB_PATH")"
  fi
else
  if [[ -x ./scripts/dev_db_up.sh ]]; then
    ./scripts/dev_db_up.sh
  fi
fi

# --- run the app ---
exec env \
  RAAL_SERVER_ADDR="$RAAL_SERVER_ADDR" \
  RAAL_DB_DRIVER="$RAAL_DB_DRIVER" \
  RAAL_DB_DSN="$RAAL_DB_DSN" \
  RAAL_DB_PATH="$RAAL_DB_PATH" \
  RAAL_SERVER_ADMIN_API_KEY="$RAAL_SERVER_ADMIN_API_KEY" \
  RAAL_SIGNING_PRIVATE_KEY_PEM="$RAAL_SIGNING_PRIVATE_KEY_PEM" \
  RAAL_SIGNING_PUBLIC_KEY_PEM="$RAAL_SIGNING_PUBLIC_KEY_PEM" \
  go run ./cmd/raalisence
