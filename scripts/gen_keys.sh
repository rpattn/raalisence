#!/usr/bin/env bash
set -euo pipefail

# Requires: openssl
# Outputs a file suitable for `source`-ing that exports RAAL_SIGNING_PRIVATE_KEY_PEM and RAAL_SIGNING_PUBLIC_KEY_PEM

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

priv_pem="$workdir/priv.pem"
pub_pem="$workdir/pub.pem"

# Generate P-256 private key and derive public key
openssl ecparam -name prime256v1 -genkey -noout -out "$priv_pem" >/dev/null 2>&1
openssl ec -in "$priv_pem" -pubout -out "$pub_pem" >/dev/null 2>&1

# Escape function to safely export the keys
esc() { awk 'BEGIN{RS="\0"; ORS=""} {gsub(/'\''/, "'\''"); print}' "$1"; }

printf "export RAAL_SIGNING_PRIVATE_KEY_PEM='"
esc "$priv_pem"
printf "'\n"

printf "export RAAL_SIGNING_PUBLIC_KEY_PEM='"
esc "$pub_pem"
printf "'\n"