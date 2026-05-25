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

RUN_ID="n8n-memory-smoke-$(date +%Y%m%d%H%M%S)"
TASK_ID="ANTS-N8N-SMOKE"

curl --connect-timeout 2 --max-time 15 -fsS -X POST "${BASE_URL}/n8n/workflow-runs" \
  -H "Content-Type: application/json" \
  -H "X-ANTS-API-Key: ${ANTS_KEY}" \
  -d "{
    \"run_id\":\"${RUN_ID}\",
    \"task_id\":\"${TASK_ID}\",
    \"workflow_name\":\"ants-memory-contract-smoke\",
    \"n8n_workflow_id\":\"manual-smoke\",
    \"n8n_execution_id\":\"${RUN_ID}\",
    \"trigger_source\":\"manual_vps_smoke\",
    \"status\":\"success\",
    \"input_summary\":{\"source\":\"script\"},
    \"output_summary\":{\"contract\":\"workflow_runs\"}
  }"
echo

curl --connect-timeout 2 --max-time 15 -fsS -X POST "${BASE_URL}/n8n/artifacts" \
  -H "Content-Type: application/json" \
  -H "X-ANTS-API-Key: ${ANTS_KEY}" \
  -d "{
    \"task_id\":\"${TASK_ID}\",
    \"run_id\":\"${RUN_ID}\",
    \"artifact_type\":\"smoke_evidence\",
    \"name\":\"n8n-memory-contract-smoke\",
    \"uri\":\"ants://smoke/${RUN_ID}\",
    \"storage_provider\":\"ants_gateway\",
    \"metadata\":{\"contract\":\"artifacts\"}
  }"
echo

curl --connect-timeout 2 --max-time 15 -fsS -X POST "${BASE_URL}/n8n/handoffs" \
  -H "Content-Type: application/json" \
  -H "X-ANTS-API-Key: ${ANTS_KEY}" \
  -d "{
    \"run_id\":\"${RUN_ID}\",
    \"task_id\":\"${TASK_ID}\",
    \"source_agent\":\"n8n\",
    \"target_agent\":\"codex\",
    \"status\":\"ready\",
    \"completed\":[\"n8n memory contract smoke executed.\"],
    \"next_steps\":[\"Inspect Supabase agent_handoffs, artifacts, and workflow_runs.\"],
    \"risks\":[\"This payload must not contain secrets.\"],
    \"artifact_links\":[{\"name\":\"n8n-memory-contract-smoke\",\"uri\":\"ants://smoke/${RUN_ID}\"}],
    \"sanitized_context\":\"Smoke test only. No secrets or raw .env values included.\",
    \"metadata\":{\"contract\":\"agent_handoffs\"}
  }"
echo
