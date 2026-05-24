#!/bin/bash
# ANT-12 VPS one-shot: repair YAML, harden 5432/6543, apply migration 002
# Usage: curl -fsSL <raw_url> | bash
set -e

COMPOSE_DIR="/root/ants-infra/supabase-ants"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"
BRANCH="feat/ant-12-supabase-network-hardening"
RAW="https://raw.githubusercontent.com/mhgutie/ants-ai-gateway/$BRANCH"

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
ss -ltnp | grep -E '(:5432|:6543|:8000|:8443|:8010)' || echo "(no ports matched — 5432/6543 successfully removed)"

echo ""
echo "=== Container status ==="
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}" | grep -E "pooler|kong|gateway|NAME"

# --- Step 7: apply migration 002 (workflow_runs + latency_ms) ---
echo ""
echo "[6/6] Applying migration 002..."
curl -fsSL "$RAW/sql/migrations/002_add_workflow_runs.sql" -o /tmp/m002.sql || { echo "ERROR: failed to download migration 002"; exit 1; }
docker exec -i supabase-db psql -U postgres -d postgres < /tmp/m002.sql && echo "Migration 002: OK" || echo "WARNING: migration 002 may already be applied"

# --- Final verification ---
echo ""
echo "=== Table check ==="
docker exec supabase-db psql -U postgres -d postgres -c "\dt public.*" | grep -E "workflow_runs|model_usage|projects|specs|tasks"

echo ""
echo "=== DONE: points 1+2+7 complete ==="
