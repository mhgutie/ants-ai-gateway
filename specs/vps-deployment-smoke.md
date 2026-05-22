# VPS Deployment Smoke

## Problem

Manual deployment commands are easy to mistype and can skip important validation steps, especially when the gateway must join the Supabase Docker network and validate direct provider routes.

## Expected Result

Provide repeatable host-side scripts for the VPS deployment path and direct provider smoke tests.

## Technical Specification

- `scripts/deploy_vps_supabase.sh` must:
  - Require an existing `.env`.
  - Verify the external Supabase Docker network exists.
  - Use `docker-compose.supabase.yml`.
  - Validate `/health`.
  - Validate protected `/dependencies`.
- `scripts/smoke_direct_providers.sh` must:
  - Use the configured gateway API key.
  - Exercise DeepSeek direct route.
  - Exercise Kimi direct route.
  - Avoid printing secrets.

## Acceptance Criteria

- Scripts are versioned in the repository.
- Tests verify scripts reference the expected compose override, health/dependency checks, and direct provider routes.
- Runtime secrets remain outside the repository.

## Harness

```bash
pytest
```
