# ANTS AI Gateway Agent Rules

## Purpose

ANTS AI Gateway is a spec-driven, harness-validated gateway for AI model routing, executor policy, cost estimation, and operational logging.

Agents working in this repository must preserve the ANTS operating model:

- Start from a specification or update one before implementation.
- Keep changes small, reviewable, and linked to a traceable work item when available.
- Add or update tests/harnesses for behavior changes.
- Do not commit secrets, populated `.env` files, OAuth tokens, refresh tokens, encrypted credential blobs, local credential stores, VPS backups, or customer data.
- Treat Supabase as the canonical operational memory when persistence is required.
- Treat CodeRabbit as a reviewer, not as a replacement for tests, harnesses, or human/agent review.

## Required Sequence

1. Understand the user need and relevant spec.
2. Update `SPEC.md`, `specs/`, or `docs/adr/` when behavior or architecture changes.
3. Implement only the required change.
4. Run the relevant harness, usually `pytest`.
5. Check secret hygiene before publication.
6. Document validation evidence in the PR.

## Security Rules

- `.env` and `.env.*` must stay out of Git, except `.env.example`.
- Provider keys must come from runtime environment variables or a secret manager.
- Codex and Claude Code must manage their own official auth stores; do not store their OAuth tokens in this repository.
- `/executors/sessions` may report `configured` when safe references exist, but `authenticated` requires a trusted smoke test or explicit trusted runtime override.
- Subprocess execution must avoid shell interpolation, validate workspace roots, close stdin when needed, and sanitize stdout/stderr.
- GitHub repository creation must use runtime tokens only, default to dry-run, and require explicit authorization before live creation.

## Harnesses

Use these commands before PRs:

```bash
pytest
python scripts/package_release.py --output ../ants-ai-gateway.tar.gz
```

For VPS executor validation, run on the host:

```bash
bash scripts/executor_smoke_host.sh /root/ants-workspaces
```

## GitHub and CodeRabbit

Public PRs should include:

- Linked Linear issue or traceable work record.
- Summary of what changed and why.
- Validation evidence.
- Secret-scan status.
- CodeRabbit findings and resolution status.
- Known risks or deferred follow-ups.
