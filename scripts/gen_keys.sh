#!/usr/bin/env bash
# scripts/gen_keys.sh
set -euo pipefail

ENV_ONLY=0
if [[ "${1:-}" == "--env-only" ]]; then
  ENV_ONLY=1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
OUT_DIR="${SCRIPT_DIR}/../keys"
mkdir -p "${OUT_DIR}"

PRIV_PEM="${OUT_DIR}/priv.pem"
PUB_PEM="${OUT_DIR}/pub.pem"

# Generate P-256 keypair (overwrite safely)
openssl ecparam -name prime256v1 -genkey -noout -out "$PRIV_PEM" >/dev/null 2>&1
openssl ec -in "$PRIV_PEM" -pubout -out "$PUB_PEM" >/dev/null 2>&1

# Cross-platform base64 (GNU has -w0; BSD/macOS doesn't)
if base64 --help 2>&1 | grep -q ' -w'; then
  b64() { base64 -w0 "$1"; }
else
  b64() { base64 "$1" | tr -d '\n'; }
fi

# Always print the two export lines on STDOUT
printf "export RAAL_SIGNING_PRIVATE_KEY_PEM_B64='%s'\n" "$(b64 "$PRIV_PEM")"
printf "export RAAL_SIGNING_PUBLIC_KEY_PEM_B64='%s'\n"  "$(b64 "$PUB_PEM")"

# If not env-only, print human info on STDERR
if [[ $ENV_ONLY -eq 0 ]]; then
  {
    echo
    echo "Wrote keys:"
    echo "  Private: $PRIV_PEM"
    echo "  Public : $PUB_PEM"
    echo
    echo "Tip: For cloud secrets, paste the RAW PEM file contents (multi-line)."
  } >&2
fi
