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

Direct SSH verification to `root@173.212.232.176` was attempted in batch mode and failed with:

```text
Permission denied (publickey,password).
```

That means the findings below are split between:

- Verified from repository and runbook state
- Inferred risk where VPS runtime evidence could not be collected

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

### 5. Postgres exposure guidance is good, but runtime verification is still missing

Status: unknown at runtime

The runbook clearly says not to expose `5432` publicly and to keep UFW limited to SSH during first install. This is good.

What could not be verified:
- Actual UFW rules on the VPS
- Whether Docker published any ports unexpectedly
- Whether Postgres is reachable from the public network

Recommendation:
- Verify on the VPS:
  - `sudo ufw status verbose`
  - `docker ps --format '{{.Names}}\t{{.Ports}}'`
  - `ss -ltnp | egrep '(:5432|:6543|:8000|:3000|:443|:80)'`
- Confirm that `5432` is bound only to localhost or an internal Docker network.

### 6. Legacy-style JWT/API key handling should be reviewed against the newer self-hosted auth guidance

Status: review recommended

The runbook currently generates `ANON_KEY` and `SERVICE_ROLE_KEY` manually from `JWT_SECRET`. Supabase's current self-hosting docs now also emphasize the newer auth key model and asymmetric auth guidance for self-hosted setups.

Recommendation:
- Review the current self-hosted auth key documentation before the next VPS hardening pass.
- If the deployed stack supports the newer key flow cleanly, plan a controlled migration instead of carrying legacy key handling forward indefinitely.

### 7. Default self-hosted stack should be kept lean

Status: optimization and attack-surface recommendation

Supabase announced on May 18, 2026 that self-hosted Analytics and Vector are moving to an opt-in overlay instead of the default compose stack.

Recommendation:
- If ANTS does not actively use self-hosted analytics or vector on this VPS, keep them disabled.
- Prefer the lean base stack and add overlays only for services that are truly needed.

### 8. Backup strategy exists, but restore verification is still missing

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

1. Verify the VPS is not exposing Postgres, Studio, or unintended ports publicly.
2. Put Kong behind HTTPS with a reverse proxy if the instance is internet-facing.
3. Move production secrets out of plain `.env`.
4. Add a restore-tested backup procedure.
5. Consider moving ANTS operational tables out of `public` into a private schema.
6. Re-check self-hosted auth key guidance against the current Supabase docs before the next rollout.

## References

- [Supabase: Self-Hosting with Docker](https://supabase.com/docs/guides/self-hosting/docker)
- [Supabase: Securing your API](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase: Using Custom Schemas](https://supabase.com/docs/guides/api/using-custom-schemas)
- [Supabase changelog: Self-hosted Supabase making Analytics and Vector opt-in](https://supabase.com/changelog/46084-self-hosted-supabase-making-analytics-and-vector-opt-in)
