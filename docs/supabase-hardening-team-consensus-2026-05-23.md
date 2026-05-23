# Supabase Hardening Team Consensus - 2026-05-23

## Who was consulted

- ANTS architecture perspective
- Claude Code-style implementation perspective
- CodeRabbit criteria perspective from `.coderabbit.yaml`

## Consensus

### Agreed immediately

- Public `5432` and `6543` should be removed.
- UFW deny rules are useful but not sufficient as the main control while Docker is still publishing listeners.
- `8010` should not remain public by default.
- The internet-facing boundary should be the reverse proxy, not the Supabase data plane.

### Agreed sequence

1. Remove public `5432/6543`.
2. Validate internal Docker-network dependencies and smoke tests.
3. Decide whether `8010` is truly required externally.
4. Move Kong behind reverse proxy + HTTPS.
5. Move secrets off plain `.env` and continue deeper hardening later.

### Main hidden risks

- Existing automation may still depend on host-published `5432/6543`.
- The gateway may be using a host-published DB port instead of Docker-internal service discovery.
- Doing reverse proxy, URL, OAuth/CORS, and DB exposure changes in one window would make rollback and diagnosis harder.

## CodeRabbit note

There is no live CodeRabbit review result for this topic yet because there is not yet a PR dedicated to the network remediation.

What CodeRabbit is expected to care about, based on `.coderabbit.yaml`:

- secret leakage
- documentation safety
- validation evidence in the PR
- infra/config changes that create insecure public exposure

When the remediation PR is opened, CodeRabbit review should be treated as required review input, not as the source of truth.
