#!/bin/bash
# Collect sanitized ANT-12 VPS hardening evidence as Markdown.
#
# Usage:
#   ANTS_GATEWAY_API_KEY=... bash scripts/collect_ant12_vps_evidence.sh > ant12-evidence.md
#
# Optional environment variables:
#   ANTS_GATEWAY_URL=http://127.0.0.1:8010
#   SUPABASE_REST_URL=http://127.0.0.1:8000/rest/v1/
set -euo pipefail

GATEWAY_URL="${ANTS_GATEWAY_URL:-http://127.0.0.1:8010}"
SUPABASE_REST_URL="${SUPABASE_REST_URL:-http://127.0.0.1:8000/rest/v1/}"
ANTS_KEY="${ANTS_GATEWAY_API_KEY:-}"

section() {
  printf '\n## %s\n\n' "$1"
}

code_block() {
  printf '```text\n'
  "$@" 2>&1 || true
  printf '```\n'
}

check_no_public_db_ports() {
  local listeners
  listeners="$(ss -ltnp 2>/dev/null | grep -E '(:5432|:6543)' || true)"
  if [ -z "$listeners" ]; then
    printf 'PASS: no 5432/6543 listeners were reported by ss.\n'
    return 0
  fi
  if printf '%s\n' "$listeners" | grep -Eq '(0\.0\.0\.0|::):?(5432|6543)'; then
    printf 'FAIL: public 5432/6543 listener detected.\n'
    printf '%s\n' "$listeners"
    return 1
  fi
  printf 'WARN: 5432/6543 listeners exist but were not detected as public wildcard binds.\n'
  printf '%s\n' "$listeners"
}

printf '# ANT-12 VPS Hardening Evidence\n\n'
printf -- '- Collected at: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf -- '- Host: %s\n' "$(hostname 2>/dev/null || echo unknown)"
printf -- '- Gateway URL: %s\n' "$GATEWAY_URL"
printf -- '- Supabase REST URL: %s\n' "$SUPABASE_REST_URL"

section "Port Verdict"
code_block check_no_public_db_ports

section "Listening Ports"
code_block bash -lc "ss -ltnp | grep -E '(:5432|:6543|:8000|:8010|:8443|:443|:80)' || true"

section "Container Ports"
code_block docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'

section "Compose Services"
code_block docker compose ps

section "Gateway Health"
code_block curl -fsS --connect-timeout 3 --max-time 10 "$GATEWAY_URL/health"

section "Gateway Dependencies"
if [ -z "$ANTS_KEY" ]; then
  printf '```text\nSKIPPED: ANTS_GATEWAY_API_KEY is not set in the environment.\n```\n'
else
  code_block curl -fsS --connect-timeout 3 --max-time 10 -H "X-ANTS-API-Key: $ANTS_KEY" "$GATEWAY_URL/dependencies"
fi

section "Supabase Local REST"
code_block curl -fsSI --connect-timeout 3 --max-time 10 "$SUPABASE_REST_URL"

section "Recent Supabase Logs"
code_block docker compose logs --tail=30 supabase-pooler
code_block docker compose logs --tail=30 supabase-kong
