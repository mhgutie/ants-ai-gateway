#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Missing .env. Copy .env.example to .env and configure runtime secrets first." >&2
  exit 1
fi

ANTS_KEY="$(grep '^ANTS_GATEWAY_API_KEY=' .env | cut -d= -f2- || true)"
PORT="$(grep '^ANTS_GATEWAY_PORT=' .env | cut -d= -f2- || true)"
PORT="${PORT:-8010}"
BASE_URL="http://localhost:${PORT}"

if [ -z "${ANTS_KEY}" ]; then
  echo "Missing ANTS_GATEWAY_API_KEY in .env." >&2
  exit 1
fi

curl --connect-timeout 2 --max-time 30 -fsS -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -H "X-ANTS-API-Key: ${ANTS_KEY}" \
  -d '{
    "task_id":"deepseek-smoke-script-001",
    "task_type":"classification",
    "user_request":"Responde exactamente: ANTS_DEEPSEEK_SCRIPT_OK",
    "provider":"deepseek",
    "model":"deepseek-v4-flash",
    "requested_context_scope":"limited",
    "explicitly_authorized":false,
    "messages":[{"role":"user","content":"Responde exactamente: ANTS_DEEPSEEK_SCRIPT_OK"}]
  }'
echo

curl --connect-timeout 2 --max-time 30 -fsS -X POST "${BASE_URL}/chat" \
  -H "Content-Type: application/json" \
  -H "X-ANTS-API-Key: ${ANTS_KEY}" \
  -d '{
    "task_id":"kimi-smoke-script-001",
    "task_type":"product_design",
    "user_request":"Responde exactamente: ANTS_KIMI_SCRIPT_OK",
    "provider":"kimi",
    "model":"kimi-k2.6",
    "requested_context_scope":"limited",
    "explicitly_authorized":false,
    "messages":[{"role":"user","content":"Responde exactamente: ANTS_KIMI_SCRIPT_OK"}]
  }'
echo
