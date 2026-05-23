# ANTS AI Gateway v0.1 Specification

## Problem
Assisted coding agents can spend tokens uncontrollably when they call model providers directly.

## Context
ANTS needs a mandatory FastAPI gateway between agents/n8n and model providers. Version 0.1 must focus only on model routing, token/cost estimation, budget enforcement, stop rules, OpenRouter execution, and usage logging.

## Expected Result
A modular FastAPI service with `/health`, `/models`, `/estimate`, `/preflight`, `/chat`, and `/usage` endpoints.

## Allowed Tools
FastAPI, OpenRouter, Supabase/Postgres, Docker, pytest, YAML configuration, environment variables.

## Required Agents/Models
The gateway routes task types to DeepSeek, Qwen, Kimi, Gemini, GPT-5.5, or NVIDIA NIM model aliases. OpenRouter is the only real provider implemented in v0.1; other providers are stubs.

## Routing Decision
`model="auto"` uses `config/routing_rules.yaml`. Each route has a fallback from `config/models.yaml`. Unavailable selected models fall back automatically.

## Acceptance Criteria
- Estimates tokens using `ceil(character_count / 3)`.
- Blocks direct execution above 128000 estimated input tokens.
- Blocks calls over task budget.
- Blocks iterations over the task budget.
- Blocks `full_repo` context unless explicitly authorized.
- Routes task types to the required model aliases.
- Falls back when selected model is unavailable.
- Calls OpenRouter only after passing preflight.
- Logs estimated and real usage without secrets.
- Provides tests for estimation, stop rules, routing, fallback, and full-repo authorization.

## Risks
Costs can be misestimated because providers tokenize differently. Provider pricing changes must be reflected in `config/models.yaml`. Logs must never include API keys or Authorization headers.

## Token/Cost Budget
Budgets are loaded from `config/budgets.yaml`. Default max cost is USD 0.10, with higher limits for selected task types.

## Test Harness
`pytest` tests in `tests/` validate cost/routing/security guardrails.

## Final Output
A complete `ants-ai-gateway` service ready for local Docker or Python execution.

## Next Step: Operational Ledger
ANTS now treats `AGENTS.md` as the canonical operating document. The next production-safe step is to align Supabase with the work-management model described there:

- Linear tracks what must happen and who/which agent owns it.
- GitHub tracks implementation, review, harness evidence, and version history.
- Supabase stores operational memory: specs, tasks, decisions, routes, budgets, costs, artifacts, and harness results.
- n8n orchestrates triggers and service calls.

For v0.1 this means adding the minimum database tables only. No UI, RAG ingestion, workflow generation, or provider behavior is added in this step.
