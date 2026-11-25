#!/usr/bin/env bash
# Write deploy/platform/.env for a new server. Safe to run again: it keeps
# every value that is already set and only adds what is missing.
#
#   ./setup.sh <public-host>
#
# With no host, it uses <server-ip>.sslip.io, a free name that resolves to the
# server's own address, so Caddy can get a certificate before you own a domain.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

host="${1:-}"
if [[ -z "$host" ]] && ! grep -q '^PUBLIC_HOST=.' .env 2>/dev/null; then
  ip="$(curl -4fsS https://api.ipify.org)"
  host="${ip//./-}.sslip.io"
fi

touch .env
chmod 600 .env

set_if_missing() {
  grep -q "^$1=." .env || { sed -i "/^$1=/d" .env; printf '%s=%s\n' "$1" "$2" >> .env; }
}
secret() { openssl rand -hex "${1:-24}"; }

if [[ -n "$host" ]]; then
  sed -i '/^PUBLIC_HOST=/d' .env
  printf 'PUBLIC_HOST=%s\n' "$host" >> .env
fi
set_if_missing POSTGRES_PASSWORD "$(secret)"
set_if_missing REDIS_PASSWORD "$(secret)"
set_if_missing MINIO_ROOT_USER "dograh"
set_if_missing MINIO_ROOT_PASSWORD "$(secret)"
set_if_missing OSS_JWT_SECRET "$(secret 48)"
set_if_missing TELEPHONY_WS_TOKEN_SECRET "$(secret 32)"
set_if_missing PLATFORM_OPERATOR_TOKEN "$(secret 32)"
set_if_missing ENABLE_SIGNUP "false"

missing=()
for key in PLATFORM_TWILIO_ACCOUNT_SID PLATFORM_TWILIO_AUTH_TOKEN \
  PLATFORM_OPENAI_API_KEY PLATFORM_DEEPGRAM_API_KEY PLATFORM_TWILIO_NUMBER_POOL; do
  grep -q "^$key=." .env || missing+=("$key")
done

echo "Public host: $(grep '^PUBLIC_HOST=' .env | cut -d= -f2)"
if ((${#missing[@]})); then
  echo "Add these to deploy/platform/.env before you start the stack:"
  printf '  %s\n' "${missing[@]}"
  exit 2
fi
echo "Configuration is complete. Start with: docker compose up -d --build"
