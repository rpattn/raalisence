#!/usr/bin/env bash
set -euo pipefail

# --- sanity checks ---
command -v openssl >/dev/null || { echo "OpenSSL is required"; exit 1; }
command -v base64  >/dev/null || { echo "base64 is required";  exit 1; }

# --- config defaults ---
db_conn="postgres://postgres:postgres@localhost:5433/raalisence?sslmode=disable"
export RAAL_SERVER_ADDR="${RAAL_SERVER_ADDR:-":8080"}"
export RAAL_DB_DSN="${RAAL_DB_DSN:-$db_conn}"
export RAAL_SERVER_ADMIN_API_KEY="${RAAL_SERVER_ADMIN_API_KEY:-"dev-admin-key"}"
echo "Set RAAL_SERVER_ADMIN_API_KEY to: $RAAL_SERVER_ADMIN_API_KEY"

# --- helper: base64 decode (Linux/macOS) ---
b64dec() {
  # GNU and BSD base64 both accept -d
  base64 -d 2>/dev/null || base64 -D
}

# --- generate dev keys if not provided ---
if [[ -z "${RAAL_SIGNING_PRIVATE_KEY_PEM:-}" || -z "${RAAL_SIGNING_PUBLIC_KEY_PEM:-}" ]]; then
  echo "No signing keys found; generating dev ECDSA keys (P-256) via OpenSSL…"
  out_env="$(mktemp)"
  trap 'rm -f "$out_env"' EXIT
  # ensure script exists/executable
  if [[ ! -x "scripts/gen_keys.sh" ]]; then
    echo "Making scripts/gen_keys.sh executable"
    chmod +x scripts/gen_keys.sh
  fi
  scripts/gen_keys.sh >"$out_env"
  # shellcheck disable=SC1090
  source "$out_env"

  # Expect *_B64 from generator, decode into raw PEM env vars
  if [[ -z "${RAAL_SIGNING_PRIVATE_KEY_PEM_B64:-}" || -z "${RAAL_SIGNING_PUBLIC_KEY_PEM_B64:-}" ]]; then
    echo "Key generator did not produce expected *_B64 vars" >&2
    exit 1
  fi

  # Decode to actual PEMs (multiline safe)
  RAAL_SIGNING_PRIVATE_KEY_PEM="$(printf '%s' "$RAAL_SIGNING_PRIVATE_KEY_PEM_B64" | b64dec)"
  RAAL_SIGNING_PUBLIC_KEY_PEM="$(printf '%s' "$RAAL_SIGNING_PUBLIC_KEY_PEM_B64"   | b64dec)"

  export RAAL_SIGNING_PRIVATE_KEY_PEM RAAL_SIGNING_PUBLIC_KEY_PEM
fi

# --- minimal env summary (never print the private key) ---
echo "DB Set to: $RAAL_DB_DSN"
echo "RAAL_SERVER_ADDR=$RAAL_SERVER_ADDR"
echo "RAAL_SERVER_ADMIN_API_KEY set: $([[ -n "${RAAL_SERVER_ADMIN_API_KEY}" ]] && echo yes || echo no)"
echo "Signing keys present: $([[ -n "${RAAL_SIGNING_PRIVATE_KEY_PEM:-}" && -n "${RAAL_SIGNING_PUBLIC_KEY_PEM:-}" ]] && echo yes || echo no)"

test -n "$RAAL_SIGNING_PRIVATE_KEY_PEM" && echo "priv ok" || echo "priv missing"
test -n "$RAAL_SIGNING_PUBLIC_KEY_PEM"  && echo "pub ok"  || echo "pub missing"
printf "%s\n" "$RAAL_SIGNING_PRIVATE_KEY_PEM" | head -2
printf "%s\n" "$RAAL_SIGNING_PUBLIC_KEY_PEM" | head -2



# --- run the app ---
exec go run ./cmd/raalisence
