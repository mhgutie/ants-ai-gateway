# GitHub, Linear, and CodeRabbit Workflow

## Purpose

ANTS uses GitHub for technical truth, Linear for work orchestration, and CodeRabbit for automated pull request review.

## Baseline Repository

The first public repository candidate is `ants-ai-gateway`.

It should include:

- Gateway source code.
- Provider routing configuration.
- Specs and ADRs.
- SQL migrations and RLS scripts.
- Tests and harnesses.
- Documentation and safe examples.

It must not include:

- `.env` files.
- API keys, OAuth tokens, refresh tokens, or encrypted credential blobs.
- VPS backups.
- Real customer data.
- Personal notes from `intentos_previos` unless cleaned and intentionally migrated.

## Linear Issue Template

Each implementation issue should include:

- Goal.
- Context.
- Acceptance criteria.
- Technical constraints.
- Files likely affected.
- Test or harness.
- Definition of done.

## Suggested Initial Linear Issues

| Key | Title | Goal |
|---|---|---|
| ANTS-001 | Gateway baseline | Publish tested gateway baseline with specs and harnesses. |
| ANTS-002 | Supabase memory baseline | Track Supabase schema, RLS, backups, and deployment docs. |
| ANTS-003 | Qwen provider execution | Keep Qwen direct execution stable and logged. |
| ANTS-004 | Executor sessions | Track Codex and Claude Code authentication status safely. |
| ANTS-005 | Executor smoke harness | Validate executor availability without exposing secrets. |
| ANTS-006 | Executor service adapter | Split host executor runtime from gateway governance. |
| ANTS-007 | Funding opportunities | Track AI credit programs and OSS grant applications. |

## Branch Naming

Use branches that reference Linear keys:

```text
feat/ants-001-gateway-baseline
fix/ants-005-executor-smoke
docs/ants-007-funding-opportunities
```

## Pull Request Requirements

Each PR should include:

- Linked Linear issue.
- What changed.
- Why it changed.
- Validation evidence.
- CodeRabbit status.
- Risks or follow-ups.

## CodeRabbit Use

Use CodeRabbit on public PRs to get automated review coverage. CodeRabbit does not replace ANTS harnesses or human/agent review.

CodeRabbit findings should be:

- Fixed in code.
- Covered by tests.
- Accepted as non-blocking with rationale.
- Deferred with a linked Linear follow-up.

## CodeRabbit Baseline

The repository includes `.coderabbit.yaml` in the repository root. CodeRabbit's official documentation requires the YAML file to live at the root of the repository and says the configuration present in the reviewed branch is automatically detected. The baseline configuration asks CodeRabbit to focus on:

- Secret leakage and `.env` safety.
- Harness evidence in PR descriptions.
- Subprocess/root validation for executor code.
- Provider policy and rate-limit behavior.
- Public documentation that avoids private operational details.

CodeRabbit is still a reviewer, not the source of truth. Secret scanning, pytest, executor smoke tests, and human/agent review remain mandatory.

## Definition of Done

A change is done only when:

- Specification or ADR is updated when needed.
- Tests or harnesses pass.
- Secrets are not present.
- PR is reviewed.
- Linear status is updated.
- Operational memory can be stored in Supabase.
