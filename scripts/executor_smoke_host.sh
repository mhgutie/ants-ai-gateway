#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${1:-/root/ants-workspaces}"
EXPECTED="ANTS_EXECUTOR_SMOKE_OK"

mkdir -p "$WORKSPACE"
cd "$WORKSPACE"

echo "== executor binaries =="
command -v codex || true
command -v claude || true

echo "== executor versions =="
codex --version
claude --version

echo "== claude prompt smoke =="
claude -p "Reply exactly: ${EXPECTED}" \
  --output-format text \
  --max-turns 1 | tee /tmp/ants-claude-smoke.out

grep -q "$EXPECTED" /tmp/ants-claude-smoke.out

echo "== codex prompt smoke =="
codex exec --json --skip-git-repo-check "Reply exactly: ${EXPECTED}" \
  < /dev/null | tee /tmp/ants-codex-smoke.out

grep -q "$EXPECTED" /tmp/ants-codex-smoke.out

echo "ANTS_EXECUTOR_HOST_SMOKE_OK"
