#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Missing .env. Copy .env.example to .env and configure runtime secrets first." >&2
  exit 1
fi

if ! docker network inspect "${ANTS_SUPABASE_DOCKER_NETWORK:-supabase_default}" >/dev/null 2>&1; then
  echo "Missing Docker network: ${ANTS_SUPABASE_DOCKER_NETWORK:-supabase_default}" >&2
  echo "Start Supabase first or set ANTS_SUPABASE_DOCKER_NETWORK to the correct external network." >&2
  exit 1
fi

docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build

ANTS_KEY="$(grep '^ANTS_GATEWAY_API_KEY=' .env | cut -d= -f2-)"
PORT="$(grep '^ANTS_GATEWAY_PORT=' .env | cut -d= -f2- || true)"
PORT="${PORT:-8010}"

curl -fsS "http://localhost:${PORT}/health"
echo
curl -fsS -H "X-ANTS-API-Key: ${ANTS_KEY}" "http://localhost:${PORT}/dependencies"
echo
