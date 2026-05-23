## Linked Work Item

ANT-12 — Supabase network hardening: remove public 5432/6543

## What Changed

- Accept ADR-0002: private Supabase network boundary (status changed from Proposed → Accepted)
- Add `docs/supabase-vps-network-hardening-rollout.md`: step-by-step VPS operator runbook
- Add `docs/supabase-hardening-team-consensus-2026-05-23.md`: decision record with consulted perspectives
- Add `docs/adr/0002-private-supabase-network-boundary.md`: architecture decision record

## Why

The VPS runtime review (ANTS-002) found `supabase-pooler` publishing `5432` and `6543` on `0.0.0.0`, conflicting with the ANTS rule that Postgres must not be exposed publicly. UFW deny rules were not sufficient because Docker bypasses them. The narrowest high-value remediation is to remove those host port publications.

## Validation

- [x] `pytest` — 98 passed, 2 skipped (2026-05-23)
- [x] Secrets scan — no real secrets in diff
- [x] VPS rollout runbook validated by ANTS team consensus
- [x] ADR-0002 accepted with team consensus documented

VPS execution status: ports 5432/6543 removal pending operator execution per `docs/supabase-vps-network-hardening-rollout.md`.

## CodeRabbit

- [ ] CodeRabbit review requested or completed
- [ ] Actionable findings resolved, accepted with rationale, or deferred to Linear

*Note: CodeRabbit GitHub App install pending — see ANTS-007.*

## Risks

- Existing automation using host-published 5432/6543 may break. Pre-change dependency check required per rollout doc.
- Docker Compose YAML on VPS was damaged by a `sed` command during a prior manual attempt; repair required before applying this change (see rollout doc).

## Notes

This PR covers only documentation and ADR acceptance. The compose change itself is applied by the VPS operator following `docs/supabase-vps-network-hardening-rollout.md`. A follow-up PR will carry the compose diff after it is validated on the VPS.
