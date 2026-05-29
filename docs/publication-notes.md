# ANTS-001 Publication Notes

## Scope

This repository is the public baseline for ANTS AI Gateway.

It intentionally contains only the gateway project, not the parent local workspace. The parent workspace may contain private environment files, deployment context, previous attempts, or operational artifacts that must not be published.

## Validation Evidence

Baseline validation completed before publication:

- Repository was created from a sanitized project package.
- `.env`, `.env.*`, generated archives, cache folders, backup YAML files, and local credential stores are excluded.
- `.env.example` is included with empty placeholder values only.
- Repository tests passed locally before publication.
- The VPS smoke tests confirmed direct DeepSeek and Kimi execution through the gateway.
- Supabase connectivity was restored and `model_usage` recorded successful smoke runs.

## Operational Evidence

Recent VPS smoke evidence:

- `deepseek-v4-flash` returned `ANTS_DEEPSEEK_DB_OK`.
- `kimi-k2.6` returned `ANTS_KIMI_DB_OK`.
- Supabase `/dependencies` reported `reachable:true`.
- `model_usage` stored successful rows for both smoke tests with real token usage and real cost values.

## Security Notes

- Provider API keys are runtime-only environment variables.
- GitHub repository provisioning uses runtime tokens only and defaults to dry-run.
- Codex and Claude Code must keep their own official auth stores.
- CodeRabbit is configured as an automated reviewer, but it does not replace harnesses, secret scanning, or human/agent review.

## Next Steps

- Enable CodeRabbit for this public repository.
- Keep pull requests small and linked to ANTS work records.
- Add GitHub Actions evidence to each implementation PR.
- Promote reusable deployment fixes into tracked specs and harnesses.
