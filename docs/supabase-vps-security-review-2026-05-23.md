# Supabase VPS Security Review - 2026-05-23

## Scope

This review covers the ANTS self-hosted Supabase deployment guidance and the gateway-side integration points that affect VPS security.

## Verified Inputs

- `infra/supabase-vps-runbook.md` in the parent workspace
- `docker-compose.yml`
- `docker-compose.supabase.yml`
- `sql/init_supabase_tables.sql`
- `sql/enable_rls_ants_tables.sql`
- Official Supabase docs and changelog reviewed on May 23, 2026

## Direct VPS Access Status

Runtime verification was later completed from an interactive VPS shell on May 23, 2026.

Verified commands:

```bash
hostname
pwd
sudo ufw status verbose
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
ss -ltnp | egrep '(:5432|:6543|:8000|:3000|:443|:80)'
```

## Security Findings

### 1. RLS baseline for ANTS tables is now present

Status: improved

The ANTS SQL snapshot and helper script now enable RLS and revoke access from `anon` and `authenticated` for the operational tables, including `workflow_runs`.

Why it matters:
- Supabase recommends explicit grants plus RLS for exposed data APIs.
- This reduces accidental exposure if tables in exposed schemas are later granted API access.

Remaining caution:
- RLS is enabled, but policy design still needs to be added before any application role should read or write these tables through Supabase APIs.

### 2. ANTS operational tables still live in `public`

Status: medium risk

The current schema is created in the default `public` schema. Supabase documentation says the `public` schema is exposed on data APIs by default, and recommends either explicit grants with RLS or using a dedicated API schema to reduce attack surface.

Recommendation:
- Keep the current revoke-first stance.
- For defense in depth, consider moving ANTS internal operational tables to a non-exposed schema such as `ants_internal`.
- Expose only the minimum API-facing objects from a dedicated schema if needed later.

### 3. Production secrets are still `.env`-centric in the runbook

Status: medium risk

The runbook correctly says not to use default secrets, but it still relies on editing `.env` directly for core secrets.

Supabase's self-hosting docs recommend using a secrets manager for production deployments.

Recommendation:
- Move at least `POSTGRES_PASSWORD`, `JWT_SECRET`, `SERVICE_ROLE_KEY`, dashboard credentials, and `VAULT_ENC_KEY` out of plain `.env` into Docker secrets or an external secret manager.
- Treat `.env` on the VPS as transitional only.

### 4. Reverse proxy and HTTPS are not yet first-class in the runbook

Status: medium risk until completed

The runbook explicitly prefers SSH tunneling first and postpones HTTPS/reverse proxy configuration. That is fine for setup, but not for production.

Supabase docs state that production deployments, especially with OAuth providers, need HTTPS with a valid TLS certificate and recommend putting a reverse proxy in front of Kong.

Recommendation:
- Before production use, front Kong with Caddy, Nginx, or Traefik.
- Terminate TLS there and update `SITE_URL`, `API_EXTERNAL_URL`, and `SUPABASE_PUBLIC_URL` to HTTPS origins.
- Avoid exposing Studio broadly on the public internet; prefer IP allowlisting, VPN, or SSH tunneling.

### 5. Supabase pooler is published on public interfaces

Status: high risk

Runtime verification showed:

- `supabase-pooler` publishes `0.0.0.0:5432->5432/tcp`
- `supabase-pooler` publishes `0.0.0.0:6543->6543/tcp`
- `ss -ltnp` confirms listeners on `0.0.0.0:5432`, `0.0.0.0:6543`, `[::]:5432`, and `[::]:6543`

UFW currently contains `DENY IN` rules for `5432/tcp` and `6543/tcp`, which is better than leaving them openly allowed, but this is still not the desired production posture.

Why this matters:
- The runbook explicitly says not to expose Postgres publicly.
- Docker-published ports add avoidable attack surface.
- Depending on host firewall and Docker iptables behavior, relying on firewall rules instead of removing the port publication is a weaker control.

Recommendation:
- Remove published `5432` and `6543` bindings from the Supabase pooler unless they are strictly required externally.
- Keep database access on the Docker network only.
- Re-test with `docker ps` and `ss -ltnp` until neither port is published on `0.0.0.0` or `[::]`.

### 6. Kong is public on port 8000 and 8443 is also published

Status: medium risk now, high if left unmanaged in production

Runtime verification showed:

- `supabase-kong` publishes `0.0.0.0:8000->8000/tcp`
- `supabase-kong` publishes `0.0.0.0:8443->8443/tcp`
- UFW allows `8000/tcp` and denies `8443/tcp`

This is acceptable for a controlled setup phase, but not yet a hardened production shape.

Recommendation:
- Put Kong behind a reverse proxy with HTTPS and restrict direct public exposure where possible.
- If `8443` is not needed directly, stop publishing it.

### 7. ANTS gateway is also published on 0.0.0.0:8010

Status: medium risk

Runtime verification showed:

- `ants-ai-gateway` publishes `0.0.0.0:8010->8000/tcp`
- `ss -ltnp` confirms a listener on `0.0.0.0:8010`

UFW output did not include an explicit allow rule for `8010`, but the container is still bound to all interfaces.

Recommendation:
- If the gateway is meant to be consumed only behind Kong, reverse proxy, or an internal network, stop publishing `8010` publicly.
- Prefer Docker-network-only exposure or bind to localhost while testing.

### 8. Legacy-style JWT/API key handling should be reviewed against the newer self-hosted auth guidance

Status: review recommended

The runbook currently generates `ANON_KEY` and `SERVICE_ROLE_KEY` manually from `JWT_SECRET`. Supabase's current self-hosting docs now also emphasize the newer auth key model and asymmetric auth guidance for self-hosted setups.

Recommendation:
- Review the current self-hosted auth key documentation before the next VPS hardening pass.
- If the deployed stack supports the newer key flow cleanly, plan a controlled migration instead of carrying legacy key handling forward indefinitely.

### 9. Default self-hosted stack should be kept lean

Status: optimization and attack-surface recommendation

Supabase announced on May 18, 2026 that self-hosted Analytics and Vector are moving to an opt-in overlay instead of the default compose stack.

Recommendation:
- If ANTS does not actively use self-hosted analytics or vector on this VPS, keep them disabled.
- Prefer the lean base stack and add overlays only for services that are truly needed.

### 10. Realtime is unhealthy

Status: operational risk

Runtime verification showed:

- `realtime-dev.supabase-realtime` has status `Up 36 hours (unhealthy)`

This is not an immediate perimeter exposure issue by itself, but unhealthy infra often causes teams to disable controls or make rushed config changes later.

Recommendation:
- Inspect `docker compose logs realtime-dev.supabase-realtime`
- Confirm whether Realtime is required at all for ANTS right now.
- If it is not required, consider disabling it until needed.

### 11. Backup strategy exists, but restore verification is still missing

Status: medium risk

The runbook includes daily `pg_dump` backups and explicitly calls for offsite backups and restore tests, but no restore procedure is yet captured in the repo.

Recommendation:
- Add a restore drill document with:
  - restore target host
  - restore command sequence
  - integrity checks after restore
  - RTO/RPO expectations

## Immediate Next Checks on the VPS

Run these on the server before calling Supabase production-ready:

```bash
sudo ufw status verbose
docker ps --format '{{.Names}}\t{{.Ports}}'
ss -ltnp | egrep '(:5432|:6543|:8000|:3000|:443|:80)'
docker compose ps
docker compose logs --tail=100 kong
docker compose exec db psql -U postgres -d postgres -c "\dn+"
docker compose exec db psql -U postgres -d postgres -c "\dp"
```

## Recommended Priority Order

1. Remove public `5432` and `6543` publication from the Supabase pooler.
2. Decide whether `8010` should be public at all; if not, stop publishing the gateway directly.
3. Put Kong behind HTTPS with a reverse proxy if the instance is internet-facing.
4. Move production secrets out of plain `.env`.
5. Add a restore-tested backup procedure.
6. Consider moving ANTS operational tables out of `public` into a private schema.
7. Re-check self-hosted auth key guidance against the current Supabase docs before the next rollout.

## References

- [Supabase: Self-Hosting with Docker](https://supabase.com/docs/guides/self-hosting/docker)
- [Supabase: Securing your API](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase: Using Custom Schemas](https://supabase.com/docs/guides/api/using-custom-schemas)
- [Supabase changelog: Self-hosted Supabase making Analytics and Vector opt-in](https://supabase.com/changelog/46084-self-hosted-supabase-making-analytics-and-vector-opt-in)
