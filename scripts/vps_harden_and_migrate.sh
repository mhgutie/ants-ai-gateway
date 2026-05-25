#!/bin/bash
# ANT-12 VPS one-shot: repair YAML, harden 5432/6543, apply migration 002
# Usage: curl -fsSL <raw_url> | bash
set -e

COMPOSE_DIR="/root/ants-infra/supabase-ants"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"
COMMIT_SHA="${ANTS_GATEWAY_COMMIT_SHA:-90ef8ea2fd654545f4aab69edd1128993feb8869}"
RAW="https://raw.githubusercontent.com/mhgutie/ants-ai-gateway/$COMMIT_SHA"
REPAIR_COMPOSE_PORTS_SHA256="865dd4e9759159abac65078023ae8027debca2ec160e90633d2b30f2c881a5b6"
MIGRATION_002_SHA256="1336d6607a812523c46efa1289e67009d6f8469a3cf97e7bfd8f59df9907e840"

echo "=== ANT-12 VPS hardening ==="
echo "Compose dir: $COMPOSE_DIR"
echo "Compose file: $COMPOSE_FILE"
echo ""

# --- Step 1: verify compose file exists ---
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "ERROR: $COMPOSE_FILE not found. Check COMPOSE_DIR."
  exit 1
fi

# --- Step 2: verify pyyaml ---
echo "[1/6] Verifying pyyaml..."
python3 - <<'PY'
import yaml
print("pyyaml: OK")
PY

# --- Step 3: download repair script ---
echo "[2/6] Downloading repair script..."
curl -fsSL "$RAW/scripts/repair_compose_ports.py" -o /tmp/rcp.py || { echo "ERROR: failed to download repair script"; exit 1; }
echo "$REPAIR_COMPOSE_PORTS_SHA256  /tmp/rcp.py" | sha256sum -c -

# --- Step 4: run repair (removes 5432/6543, restores other ports:, validates YAML) ---
echo "[3/6] Repairing docker-compose.yml..."
cd "$COMPOSE_DIR"
python3 /tmp/rcp.py --file "$COMPOSE_FILE"

# --- Step 5: validate YAML ---
echo "[4/6] Validating YAML..."
docker compose config --quiet && echo "YAML: OK"

# --- Step 6: restart pooler without the public 5432/6543 ports ---
echo "[5/6] Restarting Supabase pooler service..."
if docker compose config --services | grep -qx "supavisor"; then
  docker compose up -d supavisor
elif docker compose config --services | grep -qx "supabase-pooler"; then
  docker compose up -d supabase-pooler
else
  echo "Pooler service name not found; applying full compose update."
  docker compose up -d
fi
sleep 6

echo ""
echo "=== Port verification (5432/6543 must NOT appear) ==="
if ss -ltnp | grep -E ':(5432|6543)\b'; then
  echo "ERROR: forbidden public Postgres ports 5432/6543 are still listening."
  exit 1
fi
echo "Forbidden public Postgres ports removed: OK"

echo ""
echo "=== Container status ==="
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}" | grep -E "pooler|kong|gateway|NAME"

# --- Step 7: apply migration 002 (workflow_runs + latency_ms) ---
echo ""
echo "[6/6] Applying migration 002..."
curl -fsSL "$RAW/sql/migrations/002_add_workflow_runs.sql" -o /tmp/m002.sql || { echo "ERROR: failed to download migration 002"; exit 1; }
echo "$MIGRATION_002_SHA256  /tmp/m002.sql" | sha256sum -c -
docker exec -i supabase-db psql -v ON_ERROR_STOP=1 -X -U postgres -d postgres < /tmp/m002.sql
echo "Migration 002: OK"

# --- Final verification ---
echo ""
echo "=== Table check ==="
docker exec supabase-db psql -U postgres -d postgres -c "\dt public.*" | grep -E "workflow_runs|model_usage|projects|specs|tasks"

echo ""
echo "=== DONE: points 1+2+7 complete ==="
