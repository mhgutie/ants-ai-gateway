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
- Linear contained duplicated backlog issues for several early roadmap items. Clear duplicates were consolidated during this cleanup, and the remaining GitHub cleanup follow-up is now tracked as ANT-21.

## Findings

1. ANT-12 was the highest-risk operational item because public Postgres exposure was identified. VPS execution on 2026-05-24 removed public `5432/6543` listeners and then bound the gateway on `8010` to localhost only.
2. The project had no operator frontend, forcing routine inspection through curl, scripts, or raw API calls. This slows review and makes ANTS less operable for non-developer workflows.
3. Linear had duplicate backlog issues for the early gateway roadmap. ANT-13, ANT-16, ANT-17, ANT-18, and ANT-19 were linked as duplicates of their canonical issues.
4. GitHub issue #2 is still open even though Linear now has matching baseline work items and the publication flow has moved forward. The close/relink action is tracked in Linear as ANT-21, and a follow-up authenticated GitHub session still needs `Issues: write` or equivalent repository triage access to execute the closure remotely.
5. CodeRabbit is configured correctly, but PR templates or docs should keep requiring explicit triage status because summary-only comments are not enough evidence by themselves.

## Implemented Improvement

ANT-20 adds a minimal operator frontend served from the gateway at `/ui`. It uses the existing API key header, calls existing protected endpoints, and avoids creating another backend or state store.

## Recommended Next Improvements

- Keep ANT-12 evidence attached to Linear and PR #5; the VPS now has no public `5432/6543` listeners and gateway `8010` is localhost-only.
- Keep ANT-14 and ANT-15 open unless a canonical replacement is created; they are not exact duplicates of closed work.
- From an authenticated GitHub session with issue write permissions, close issue #2 or update it to point at ANT-21 plus the canonical PR history; until then, the follow-up remains tracked in Linear only.
- Add a PR template that makes CodeRabbit triage, harness evidence, Linear link, and rollback awareness hard to skip.
- Add a lightweight `/ops/summary` API endpoint later if operators need a single consolidated status payload for the UI.
