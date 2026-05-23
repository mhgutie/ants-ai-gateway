# ANTS AI Gateway v0.1

ANTS AI Gateway is the first production module of ANTS: a mandatory FastAPI gateway between coding agents, n8n, and AI model providers. It estimates tokens and cost, routes tasks to the right model, enforces stop rules, calls providers only when allowed, and logs usage.

This v0.1 intentionally does not include RAG, UI, PDF extraction, or workflow generation.

## Local Setup

```bash
cd ants-ai-gateway
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

On PowerShell:

```powershell
cd ants-ai-gateway
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

## Environment Variables

Secrets are read only from environment variables. Never hardcode keys.

```env
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
SUPABASE_DB_URL=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
GOOGLE_API_KEY=
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
KIMI_API_KEY=
KIMI_BASE_URL=https://api.moonshot.ai/v1
QWEN_API_KEY=
QWEN_BASE_URL=https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
NVIDIA_NIM_API_KEY=
OLLAMA_BASE_URL=
OLLAMA_OPENAI_BASE_URL=https://ollama.com/v1
ANTS_PROFILE_SEQUENCE=1,2,3,4
ANTS_ENV=local
ANTS_DEFAULT_PROVIDER=openrouter
ANTS_GATEWAY_API_KEY=

CODEX_EXECUTOR_ENABLED=true
CODEX_AUTH_MODE=chatgpt
CODEX_CLI_PATH=codex
CODEX_USE_EXTERNAL_AUTH_STORE=true
ANTIGRAVITY_EXECUTOR_ENABLED=false
CLAUDE_CODE_EXECUTOR_ENABLED=false
ANTS_TOOL_EXECUTION_MODE=guarded
ANTS_BLOCK_DESTRUCTIVE_COMMANDS=true
```

For family profile pools, prefer numeric profile IDs:

```env
ANTHROPIC__1__API_KEY=
ANTHROPIC__2__API_KEY=
QWEN__1__API_KEY=
QWEN__2__API_KEY=
OPENROUTER__1__API_KEY=
OPENROUTER__2__API_KEY=
DEEPSEEK__1__API_KEY=
DEEPSEEK__1__BASE_URL=https://api.deepseek.com
DEEPSEEK__2__API_KEY=
DEEPSEEK__2__BASE_URL=https://api.deepseek.com
KIMI__1__API_KEY=
KIMI__1__BASE_URL=https://api.moonshot.ai/v1
KIMI__2__API_KEY=
KIMI__2__BASE_URL=https://api.moonshot.ai/v1
```

## Docker

```bash
cd ants-ai-gateway
cp .env.example .env
docker compose up --build
```

The API will be available at `http://localhost:8000`.

## Operator Frontend

The gateway serves a lightweight operator console at:

```text
http://localhost:8000/ui
```

Use it to inspect health, Supabase dependency status, credential-pool status, model routing, executor policy, executor sessions, preflight decisions, and executor smoke tests. Protected calls use the existing `X-ANTS-API-Key` header. The browser stores the API base URL and gateway key in local storage for operator convenience; do not use shared browsers for production keys.

On the VPS, Supabase already uses port `8000`, so run the gateway on `8010`:

```env
ANTS_GATEWAY_PORT=8010
```

If the gateway must connect to the self-hosted Supabase database from a separate Supabase Compose project, use the Supabase network override and set `SUPABASE_DB_URL` to the Supabase container hostname, for example `supabase-db`:

```env
SUPABASE_DB_URL=postgresql://postgres:YOUR_PASSWORD@supabase-db:5432/postgres
ANTS_SUPABASE_DOCKER_NETWORK=supabase_default
```

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build
```

The VPS helper script wraps the same command and verifies the gateway is healthy:

```bash
bash scripts/deploy_vps_supabase.sh
```

Check protected dependency status:

```bash
ANTS_KEY="$(grep '^ANTS_GATEWAY_API_KEY=' .env | cut -d= -f2-)"
curl -H "X-ANTS-API-Key: $ANTS_KEY" http://localhost:8010/dependencies
```

After configuring direct provider keys, run smoke tests for DeepSeek and Kimi:

```bash
bash scripts/smoke_direct_providers.sh
```

## Safe Release Package

Create a sanitized tarball for VPS deployment or public repository preparation:

```bash
python scripts/package_release.py --output ../ants-ai-gateway.tar.gz
```

The package keeps `.env.example` but excludes real `.env` files, caches, generated archives, backup YAML files, VCS metadata, and local credential files.

## Example `/preflight`

```bash
curl -X POST http://localhost:8000/preflight \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "debug-001",
    "task_type": "coding_debug",
    "user_request": "Fix this failing FastAPI test.",
    "context": {"files": ["app/main.py", "tests/test_main.py"]},
    "budget": {},
    "requested_context_scope": "selected_files",
    "explicitly_authorized": false,
    "model": "auto",
    "iteration": 1
  }'
```

## Example `/chat`

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "debug-001",
    "task_type": "coding_debug",
    "user_request": "Explain why this test fails and suggest a patch.",
    "context": {"error": "AssertionError"},
    "requested_context_scope": "selected_files",
    "explicitly_authorized": false,
    "model": "auto",
    "iteration": 1,
    "messages": [
      {"role": "user", "content": "Explain why this test fails and suggest a patch."}
    ]
  }'
```

## n8n Connection

Use an HTTP Request node:

- Method: `POST`
- URL: `http://ants-ai-gateway:8000/preflight` before execution, or `/chat` for execution.
- Body: JSON matching the request examples.
- Route blocked responses to a human review, summarization, or RAG workflow.
- Store `task_id`, `run_id`, `recommended_model`, `estimated_cost_usd`, and `stop_rules` in your workflow logs.

## GitHub Repository Provisioning

ANTS can prepare GitHub repositories through a protected gateway endpoint. Configure the token only at runtime:

```env
ANTS_GITHUB_TOKEN=
GITHUB_API_BASE_URL=https://api.github.com
```

Use a fine-grained token with the minimum repository administration permission needed. Do not send tokens in request bodies and do not commit them.

Dry-run first:

```bash
curl -s -X POST http://localhost:8010/github/repositories \
  -H "Content-Type: application/json" \
  -H "X-ANTS-API-Key: $ANTS_KEY" \
  -d '{"name":"ants-ai-gateway","visibility":"public","dry_run":true}'
```

Live creation requires both `dry_run:false` and `explicitly_authorized:true`:

```bash
curl -s -X POST http://localhost:8010/github/repositories \
  -H "Content-Type: application/json" \
  -H "X-ANTS-API-Key: $ANTS_KEY" \
  -d '{"name":"ants-ai-gateway","visibility":"public","dry_run":false,"explicitly_authorized":true}'
```

## Codex, Antigravity, Roo, Cline, Continue

Configure agents to call this gateway instead of calling OpenRouter directly:

- Set the agent/provider base URL to `http://localhost:8000` when the tool supports OpenAI-compatible proxies.
- If the tool does not support custom gateway semantics, route requests through n8n or a small adapter that calls `/preflight` and `/chat`.
- Do not store provider API keys in agent configs. Store them only in the gateway `.env`.
- For repository-wide tasks, send `requested_context_scope: "full_repo"` and require `explicitly_authorized: true`.

Recommended executor split:

- Codex: repository edits, patches, tests, diffs, and harness execution.
- Antigravity: guarded live-environment execution when terminal/browser workflows are needed.
- Claude/Anthropic: high-reasoning planning, architecture, review, and long-instruction-following.
- ANTS Gateway: routing, preflight, cost limits, provider policy, and logging.

Keep `ANTIGRAVITY_EXECUTOR_ENABLED=false` until the Antigravity CLI/SDK or connector is explicitly installed and validated in the target environment.

Codex executor credentials:

- Do not paste Codex `access_token`, `refresh_token`, or `id_token` into `.env`.
- Use the official Codex login/session mechanism on the machine where the Codex executor runs.
- ANTS stores only executor policy/configuration such as `CODEX_EXECUTOR_ENABLED`, `CODEX_AUTH_MODE`, `CODEX_CLI_PATH`, `CODEX_WORKSPACE_ROOT`, and allowed roots.
- If a future executor adapter needs to reference a credential, store only a secret reference, not the secret itself.

Inspect executor policy/status:

```bash
ANTS_KEY="$(grep '^ANTS_GATEWAY_API_KEY=' .env | cut -d= -f2-)"
curl -H "X-ANTS-API-Key: $ANTS_KEY" http://localhost:8010/executors
```

This returns safe metadata for `codex`, `claude_code`, and `antigravity`; it never returns OAuth tokens, API keys, or refresh tokens.

Inspect safe executor session references:

```bash
curl -H "X-ANTS-API-Key: $ANTS_KEY" http://localhost:8010/executors/sessions
```

Create `config/executor_sessions.yaml` from `config/executor_sessions.example.yaml` only when you have authenticated the executor through its official CLI/connector. Store session references and status metadata only, never real credentials.

Session status semantics:

- `pending_auth`: no safe session reference is configured.
- `configured`: roots and encrypted credential references are configured, but live CLI authentication has not been proven by a smoke test in the current runtime.
- `authenticated`: set only after a successful external CLI smoke test or an explicit trusted `*_SESSION_STATUS=authenticated` environment override.

Run a guarded executor smoke test:

```bash
curl -s -X POST http://localhost:8010/executors/smoke-test \
  -H "Content-Type: application/json" \
  -H "X-ANTS-API-Key: $ANTS_KEY" \
  -d '{"executor":"claude_code","mode":"version"}'
```

The gateway smoke endpoint runs inside the gateway container. If Codex or Claude Code are installed only on the VPS host, the endpoint will correctly report that the CLI is unavailable in the gateway runtime. Use the host-side harness for the current VPS setup:

```bash
bash scripts/executor_smoke_host.sh /root/ants-workspaces
```

Prompt smoke mode uses a fixed marker prompt (`ANTS_EXECUTOR_SMOKE_OK`) and does not accept arbitrary user prompts. This keeps the first executor harness useful without turning it into an unrestricted command runner.

Hermes-style encrypted executor credentials:

ANTS can store a Hermes-compatible credential pool as an encrypted `.env` blob:

```env
ANTS_EXECUTOR_CREDENTIALS_MODE=encrypted_env
ANTS_EXECUTOR_CREDENTIALS_KEY=
ANTS_EXECUTOR_CREDENTIAL_POOL_ENC=
```

The decrypted JSON can contain `version`, `providers`, `active_provider`, `updated_at`, and `credential_pool` with provider entries such as `openai-codex`. The public API only exposes `/executors/credentials/status`, which returns metadata and never returns OAuth tokens.

Security note: storing the encrypted blob and the decryption key in the same `.env` is supported for operational simplicity, but it protects less than Docker secrets or a dedicated secret manager. Prefer moving `ANTS_EXECUTOR_CREDENTIALS_KEY` to a secret store when possible.

Generate a key:

```bash
python - <<'PY'
from app.executor_credentials import generate_executor_credentials_key
print(generate_executor_credentials_key())
PY
```

Encrypt a local `executor_credentials.json`:

```bash
python - <<'PY'
import json, os
from app.executor_credentials import encrypt_credential_pool
with open("executor_credentials.json", "r", encoding="utf-8") as handle:
    payload = json.load(handle)
print(encrypt_credential_pool(payload, os.environ["ANTS_EXECUTOR_CREDENTIALS_KEY"]))
PY
```

## Tests

```bash
cd ants-ai-gateway
pytest
```

The harness validates token estimation, oversized-context blocking, budget blocking, routing, fallback, and full-repo authorization.
