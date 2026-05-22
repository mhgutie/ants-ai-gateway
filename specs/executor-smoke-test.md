# Executor Smoke Test Harness

## Problem

ANTS can have configured Codex and Claude Code session references on the VPS, but the gateway needs a safe way to validate executor readiness before delegating real implementation work.

## Expected Result

Expose a protected smoke-test harness that can verify executor availability without exposing credentials or running arbitrary user prompts.

## Technical Specification

- Add `POST /executors/smoke-test`.
- Require the existing gateway API key.
- Support `version` mode for binary/runtime checks.
- Support `prompt` mode only with a fixed smoke prompt: `Reply exactly: ANTS_EXECUTOR_SMOKE_OK`.
- Reject prompt smoke tests when the executor session is not explicitly authenticated.
- Enforce configured workspace roots and allowed roots.
- Run commands without shell interpolation.
- Close stdin for subprocesses to avoid non-interactive CLI hangs.
- Sanitize stdout and stderr before returning them.
- Return structured pass/fail evidence.

## Acceptance Criteria

- The endpoint never returns OAuth tokens, API keys, or refresh tokens.
- Disabled executors fail safely.
- Working directories outside allowed roots are rejected.
- Version smoke tests can verify that a CLI is available in the gateway runtime.
- Prompt smoke tests require an explicitly authenticated executor session. A configured encrypted credential reference is not enough by itself.
- Tests cover sanitization, root checks, version smoke, prompt gating, and prompt success.

## Harness

Repository harness:

```bash
pytest
```

Operational harness on the VPS:

```bash
curl -s -X POST http://localhost:8010/executors/smoke-test \
  -H "Content-Type: application/json" \
  -H "X-ANTS-API-Key: $ANTS_KEY" \
  -d '{"executor":"claude_code","mode":"version"}'
```

## Notes

The gateway currently runs inside Docker while Codex and Claude Code are installed on the VPS host. If the CLIs are not mounted or installed inside the gateway container, the endpoint will correctly report that the CLI is unavailable in the gateway runtime. Host-side executor execution should be introduced only with an explicit adapter, mounts, or a dedicated executor service.

This boundary is intentional. See `docs/adr/0001-separate-gateway-from-executor-runtime.md`: the gateway governs, validates, and logs; the executor runtime acts in the live workspace.
