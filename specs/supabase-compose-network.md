# Supabase Compose Network

## Problem

The gateway can use a self-hosted Supabase database, but when Supabase and the gateway are started by separate Docker Compose projects the gateway container is not automatically attached to Supabase's Docker network. A manual `docker network connect supabase_default ants-ai-gateway-ants-ai-gateway-1` works, but it is easy to forget after rebuilds.

## Expected Result

Provide a repeatable deployment path that attaches the gateway service to the Supabase Docker network without requiring ad-hoc container commands.

## Technical Specification

- Keep the default `docker-compose.yml` standalone-friendly.
- Add an optional `docker-compose.supabase.yml` override.
- Attach `ants-ai-gateway` to both its default project network and the external Supabase network.
- Default the external network name to `supabase_default`.
- Allow overriding the network name through `ANTS_SUPABASE_DOCKER_NETWORK`.
- Do not expose Postgres publicly or store database credentials in repository files.

## Acceptance Criteria

- Standalone compose remains valid without requiring a local Supabase network.
- Supabase-enabled deployment can use:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build
```

- The dependency endpoint can resolve `supabase-db` when `.env` uses that hostname and the container is attached to `supabase_default`.
- A unit test verifies the override file references an external Supabase network and attaches the service to it.

## Harness

```bash
pytest
```
