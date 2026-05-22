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

if [ -z "${ANTS_KEY}" ]; then
  echo "Missing ANTS_GATEWAY_API_KEY in .env." >&2
  exit 1
fi

for attempt in $(seq 1 20); do
  if curl --connect-timeout 2 --max-time 5 -fsS "http://localhost:${PORT}/health"; then
    break
  fi
  if [ "$attempt" = "20" ]; then
    echo "Gateway did not become healthy after ${attempt} attempts." >&2
    docker compose logs --tail 120 ants-ai-gateway >&2
    exit 1
  fi
  sleep 2
done
echo
curl --connect-timeout 2 --max-time 10 -fsS -H "X-ANTS-API-Key: ${ANTS_KEY}" "http://localhost:${PORT}/dependencies"
echo
