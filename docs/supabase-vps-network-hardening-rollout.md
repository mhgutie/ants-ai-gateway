# Supabase VPS Network Hardening Rollout

Linked work item: `ANT-12`

## Purpose

Apply the narrowest high-value hardening change first:

- remove public `5432`
- remove public `6543`
- keep internal Docker-network connectivity working
- decide separately whether `8010` remains public

This rollout intentionally does **not** combine:

- reverse proxy/TLS migration
- secret manager migration
- schema moves out of `public`
- broad Realtime debugging

## Preconditions

- You have shell access to the VPS.
- You can edit the Supabase Docker Compose files in the live deployment directory.
- You know how to restore the prior compose file quickly.

## Pre-Change Snapshot

Run and save the output:

```bash
hostname
pwd
docker compose ps
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
ss -ltnp | egrep '(:5432|:6543|:8000|:8010|:8443|:443|:80)'
docker compose logs --tail=30 supabase-pooler
docker compose logs --tail=30 supabase-kong
```

## Dependency Check

Before editing compose files, confirm that no critical workflow depends on host-published `5432` or `6543`.

Check for:

- backup jobs using host ports
- scripts using `localhost:5432` or `localhost:6543`
- gateway DB URLs using a host-published port instead of Docker service DNS

Recommended quick checks:

```bash
grep -R \"5432\\|6543\" -n . /root 2>/dev/null | head -n 200
docker inspect ants-ai-gateway-ants-ai-gateway-1 | grep -i SUPABASE_DB_URL -n
```

If the gateway or maintenance scripts are using Docker-internal service names already, this change is much safer.

## Compose Change

In the Supabase deployment compose file, find the service that currently publishes:

- `5432:5432`
- `6543:6543`

Remove those host port publications from `supabase-pooler`.

Desired end state:

- `supabase-pooler` remains attached to the Docker network
- `supabase-pooler` does not publish `5432` or `6543` to the host

Do **not** remove the service itself in this step.

## Apply Change

After editing the compose file:

```bash
docker compose up -d
docker compose ps
```

## Post-Change Validation

The following checks should now pass:

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
ss -ltnp | egrep '(:5432|:6543|:8000|:8010|:8443|:443|:80)'
docker compose logs --tail=50 supabase-pooler
docker compose logs --tail=50 supabase-kong
curl -I http://127.0.0.1:8000/rest/v1/
```

Expected results:

- no listener on `0.0.0.0:5432`
- no listener on `0.0.0.0:6543`
- no listener on `[::]:5432`
- no listener on `[::]:6543`
- Kong still responds locally on `127.0.0.1:8000`
- Supabase containers stay healthy enough for current ANTS usage

## Gateway Exposure Decision

After `5432/6543` are removed, decide whether `8010` is truly required externally.

If **not** required:

- remove public `8010` publication, or
- bind it only to `127.0.0.1`, or
- place it behind the reverse proxy as an internal upstream

If it **is** required:

- document why
- ensure auth, logging, and rate limiting expectations are explicit

## Rollback

If any internal dependency breaks:

1. restore the prior compose file
2. run:

```bash
docker compose up -d
docker compose ps
ss -ltnp | egrep '(:5432|:6543|:8000|:8010|:8443|:443|:80)'
```

3. verify the old listeners and service health return

## What Comes Next

Only after this step is validated:

1. decide `8010`
2. introduce reverse proxy + TLS
3. move secrets off plain `.env`
4. optionally disable unused Supabase services
5. later consider moving ANTS operational tables into a non-exposed schema
