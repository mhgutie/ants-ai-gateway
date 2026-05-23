# ANTS Review From Linear, GitHub, and CodeRabbit

Review date: 2026-05-23

## Sources Reviewed

- Linear workspace `Ants-ai-gateway`, including ANT-5 through ANT-20.
- GitHub repository `mhgutie/ants-ai-gateway`.
- Open GitHub PR #5: `ANT-12 Supabase network hardening: remove public 5432/6543`.
- CodeRabbit repository configuration and public PR review artifacts.
- Local repository tests, specs, ADRs, SQL, scripts, and docs.

## Current State

- Gateway baseline is public and tested.
- Direct DeepSeek and Kimi provider routes were implemented and merged through PR #4.
- Supabase network hardening is in progress through ANT-12 and PR #5.
- CI and Secret Scan are passing on the current ANT-12 branch.
- CodeRabbit has produced a summary for PR #5. No public inline actionable review comments were returned by the GitHub API during this review.
- Linear contained duplicated backlog issues for several early roadmap items. Clear duplicates were consolidated during this cleanup.

## Findings

1. ANT-12 remains the highest-risk operational item because public Postgres exposure was identified and the PR currently documents the rollout while the VPS execution remains pending.
2. The project had no operator frontend, forcing routine inspection through curl, scripts, or raw API calls. This slows review and makes ANTS less operable for non-developer workflows.
3. Linear had duplicate backlog issues for the early gateway roadmap. ANT-13, ANT-16, ANT-17, ANT-18, and ANT-19 were linked as duplicates of their canonical issues.
4. GitHub issue #2 is still open even though Linear now has matching baseline work items and the publication flow has moved forward.
5. CodeRabbit is configured correctly, but PR templates or docs should keep requiring explicit triage status because summary-only comments are not enough evidence by themselves.

## Implemented Improvement

ANT-20 adds a minimal operator frontend served from the gateway at `/ui`. It uses the existing API key header, calls existing protected endpoints, and avoids creating another backend or state store.

## Recommended Next Improvements

- Complete ANT-12 VPS execution and capture post-change evidence with `scripts/collect_ant12_vps_evidence.sh`: public port scan, internal database reachability, gateway health, and rollback notes.
- Keep ANT-14 and ANT-15 open unless a canonical replacement is created; they are not exact duplicates of closed work.
- Close GitHub issue #2 or update it to point at the canonical Linear issue and PR history once GitHub write access is available.
- Add a PR template that makes CodeRabbit triage, harness evidence, Linear link, and rollback awareness hard to skip.
- Add a lightweight `/ops/summary` API endpoint later if operators need a single consolidated status payload for the UI.
