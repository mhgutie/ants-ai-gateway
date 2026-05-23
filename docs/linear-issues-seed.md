# Linear Issue Seed Pack

These issue bodies are ready to paste into Linear for the initial `ANTS-001` to `ANTS-007` backlog defined in [docs/github-linear-coderabbit.md](/C:/Users/EQUIPO/appmultiANTS/ants-ai-gateway/docs/github-linear-coderabbit.md).

## ANTS-001 Gateway baseline

Goal: Publish a tested public baseline for `ants-ai-gateway`.

Context: This repository is the first public ANTS candidate and must expose the gateway contract, tests, SQL schema, specs, and safe examples without leaking local operational context.

Acceptance Criteria:
- `ants-ai-gateway` exists as an isolated GitHub repository.
- `pytest` passes in the isolated repository.
- `.env`, archives, and credential blobs are excluded from publication.
- The repository root contains `.coderabbit.yaml`, PR template, and publication docs.
- Baseline PR includes validation evidence.

Technical Constraints:
- Publish only `ants-ai-gateway`, not the parent `appmultiANTS`.
- No secrets, real tokens, or private operational artifacts may be committed.
- Follow [docs/publication-checklist.md](/C:/Users/EQUIPO/appmultiANTS/ants-ai-gateway/docs/publication-checklist.md).

Files likely affected:
- `README.md`
- `.gitignore`
- `.coderabbit.yaml`
- `.github/`
- `docs/publication-checklist.md`

Test or Harness:
- `pytest`
- Publication package build via `python scripts/package_release.py --output ../ants-ai-gateway.tar.gz`

Definition of Done:
- Public repo exists.
- Baseline commit/PR is published.
- Validation evidence is attached in PR description.

## ANTS-002 Supabase memory baseline

Goal: Version and harden the Supabase operational schema.

Context: Supabase is the canonical memory for ANTS, so the gateway needs a schema that captures specs, tasks, model usage, workflow runs, harness evidence, and reusable patterns with RLS.

Acceptance Criteria:
- SQL schema includes the operational ledger tables required by ANTS.
- `model_usage` captures `project_id` and `latency_ms`.
- `workflow_runs` exists for orchestrator traceability.
- SQL migrations are versioned and reviewable.
- RLS and revoke statements cover the operational tables.

Technical Constraints:
- No table stores raw secret values.
- Changes must remain compatible with Supabase/Postgres.

Files likely affected:
- `sql/init_supabase_tables.sql`
- `sql/migrations/001_init.sql`
- `sql/migrations/002_add_workflow_runs.sql`
- `tests/test_sql_schema.py`

Test or Harness:
- `pytest tests/test_sql_schema.py`

Definition of Done:
- Migration files are committed.
- Tests assert the schema contract.
- Snapshot schema matches the latest migration state.

## ANTS-003 Qwen provider execution

Goal: Keep direct Qwen execution stable, explicit, and logged.

Context: Qwen is the primary implementation model in the gateway, so adapter execution, provider policy, and usage logging need to stay predictable.

Acceptance Criteria:
- Qwen execution path remains green in provider tests.
- Logging captures provider/model/task metadata for Qwen runs.
- Fallback behavior remains explicit when a route is not executable.

Technical Constraints:
- Preserve current direct-provider strategy.
- Do not silently route Qwen calls through a different provider.

Files likely affected:
- `app/providers/qwen.py`
- `app/model_router.py`
- `app/services/usage_logger.py`
- `tests/test_qwen_provider.py`
- `tests/test_model_router.py`

Test or Harness:
- `pytest tests/test_qwen_provider.py tests/test_model_router.py`

Definition of Done:
- Provider tests pass.
- Router behavior is documented and stable.

## ANTS-004 Executor sessions

Goal: Track Codex, Claude Code, and Antigravity executor session state safely.

Context: ANTS needs visibility into executor readiness without exposing credentials or treating workstation state as implicit truth.

Acceptance Criteria:
- Executor session endpoint returns structured status.
- Credential pool status remains sanitized.
- Session config can distinguish configured, pending auth, and expired states.

Technical Constraints:
- No secrets or tokens in API responses.
- Local environment assumptions must stay explicit.

Files likely affected:
- `app/tool_executors.py`
- `app/executor_credentials.py`
- `config/executor_sessions.example.yaml`
- `tests/test_executor_credentials.py`

Test or Harness:
- `pytest tests/test_executor_credentials.py tests/test_tool_executors.py`

Definition of Done:
- Session status is queryable.
- Responses are sanitized and documented.

## ANTS-005 Executor smoke harness

Goal: Validate executor availability without exposing secrets.

Context: The gateway needs a lightweight harness to confirm tool executors are callable before higher-risk orchestration depends on them.

Acceptance Criteria:
- Smoke endpoint validates selected executors.
- Commands are non-destructive and sanitized.
- Tests cover failure modes and command construction.

Technical Constraints:
- Never expose credentials in stdout/stderr.
- Avoid interactive prompts in smoke mode.

Files likely affected:
- `app/executor_smoke.py`
- `app/main.py`
- `tests/test_executor_smoke.py`
- `specs/executor-smoke-test.md`

Test or Harness:
- `pytest tests/test_executor_smoke.py`

Definition of Done:
- Smoke tests pass.
- Spec and endpoint behavior match.

## ANTS-006 Executor service adapter

Goal: Separate gateway governance from host executor runtime concerns.

Context: ANTS should keep policy, preflight, and audit behavior in the gateway while allowing executor-specific runtime concerns to evolve separately.

Acceptance Criteria:
- Clear boundary exists between gateway policy and executor runtime calls.
- Adapter/service responsibilities are documented.
- Risks and future extraction path are recorded.

Technical Constraints:
- Do not collapse governance and execution into one opaque subsystem.
- Preserve current API behavior while clarifying the architecture.

Files likely affected:
- `docs/adr/`
- `app/executor_smoke.py`
- `app/tool_executors.py`
- `SPEC.md`

Test or Harness:
- ADR/spec review plus existing executor tests.

Definition of Done:
- Architecture boundary is documented.
- Follow-up implementation path is traceable.

## ANTS-007 Funding opportunities

Goal: Track OSS, AI credit, and grant opportunities that can subsidize the public ANTS stack.

Context: Publishing `ants-ai-gateway` publicly enables CodeRabbit, GitHub programs, and other ecosystem benefits that can reduce operating cost.

Acceptance Criteria:
- Funding opportunities are documented with eligibility and next steps.
- Repository publication dependencies are identified.
- Follow-up actions are linked to GitHub/Linear work.

Technical Constraints:
- Keep the research lightweight and actionable.
- Prefer programs relevant to public repositories and OSS maintainers.

Files likely affected:
- `docs/funding-opportunities.md`
- `docs/publication-checklist.md`

Test or Harness:
- Manual review of links, status, and prerequisites.

Definition of Done:
- Opportunity list is current enough to act on.
- Publication blockers are explicit.
