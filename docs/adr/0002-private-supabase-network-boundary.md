# ADR 0002: Keep Supabase Data Plane Private Behind the Public Edge

## Status

Proposed

## Context

On May 23, 2026, ANTS reviewed the self-hosted Supabase VPS runtime state and found that:

- `supabase-pooler` was published on `0.0.0.0:5432` and `0.0.0.0:6543`
- `supabase-kong` was published on `0.0.0.0:8000` and `0.0.0.0:8443`
- `ants-ai-gateway` was published on `0.0.0.0:8010`
- UFW denied inbound `5432`, `6543`, and `8443`, but Docker still created public listeners

This state conflicts with the ANTS constitution and deployment guidance:

- Supabase is the canonical memory and system of record.
- Postgres must not be exposed publicly.
- Public services should sit behind a reverse proxy with TLS.
- Important production-facing decisions must be versioned and traceable.

Team perspectives consulted:

- ANTS architecture view: public `5432/6543` should be removed immediately and `8010` should not remain public by default.
- Claude Code-style implementation view: make the narrowest reversible network hardening change first, then validate, then do reverse proxy/TLS as a second controlled step.
- CodeRabbit status: no live CodeRabbit review exists yet for this decision because there is no PR review artifact yet. The expected CodeRabbit concerns are inferred from `.coderabbit.yaml`, especially secret safety, public-doc safety, and validation evidence.

## Decision

ANTS will treat the Supabase/Postgres data plane as private-by-design.

The target architecture is:

- Public edge:
  - reverse proxy on `80/443`
- Application edge:
  - `supabase-kong`
  - optionally `ants-ai-gateway` if external access is explicitly required
- Private data plane:
  - Postgres
  - Supavisor / pooler
  - internal service-to-service traffic on Docker networks only

Specific policy decisions:

- Remove public host publication of `5432` and `6543`.
- Do not keep `8010` public by default; only keep it public if ANTS explicitly needs direct external ingress to the gateway.
- Prefer internal Docker DNS/service names over host-published database ports.
- Sequence the rollout:
  1. remove public `5432/6543`
  2. validate internal connectivity and smoke tests
  3. decide `8010` exposure
  4. add reverse proxy + TLS in front of Kong
  5. then move secrets and deeper schema hardening in later windows

## Consequences

Positive:

- Removes avoidable attack surface from the database layer.
- Reduces reliance on firewall rules as the primary security control.
- Aligns runtime topology with ANTS architecture rules.
- Makes reverse proxy and TLS the intentional public boundary.

Trade-offs:

- Existing automation that depends on host-published `5432/6543` may break and must be checked first.
- Requires controlled rollout and smoke testing.
- May create a follow-up requirement to route gateway traffic differently if `8010` is no longer public.

## Documentation and Workflow Notes

- Linear should track the remediation work as an implementation issue with acceptance criteria and validation evidence.
- GitHub should carry the technical decision, runtime evidence, and implementation changes.
- CodeRabbit should review the future PR that applies the network change; until then, any “CodeRabbit view” is expectation-based, not an actual review result.
