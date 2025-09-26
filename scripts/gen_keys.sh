#!/usr/bin/env bash
set -euo pipefail
# Requires: openssl, base64
# Outputs exports for BASE64-encoded PEMs:
#   RAAL_SIGNING_PRIVATE_KEY_PEM_B64
#   RAAL_SIGNING_PUBLIC_KEY_PEM_B64

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

priv_pem="$workdir/priv.pem"
pub_pem="$workdir/pub.pem"

# Generate P-256 private key and corresponding public key
openssl ecparam -name prime256v1 -genkey -noout -out "$priv_pem" >/dev/null 2>&1
openssl ec      -in "$priv_pem" -pubout -out "$pub_pem"           >/dev/null 2>&1

# Cross-platform base64 (GNU has -w0; BSD doesn't)
if base64 --help 2>&1 | grep -q -- ' -w'; then
  b64() { base64 -w0 "$1"; }  # GNU coreutils
else
  b64() { base64 "$1" | tr -d '\n'; }  # BSD/macOS
fi

printf "export RAAL_SIGNING_PRIVATE_KEY_PEM_B64='%s'\n" "$(b64 "$priv_pem")"
printf "export RAAL_SIGNING_PUBLIC_KEY_PEM_B64='%s'\n"  "$(b64 "$pub_pem")"
