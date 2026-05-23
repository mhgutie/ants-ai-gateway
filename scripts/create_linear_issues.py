#!/usr/bin/env python3
"""
Create ANTS-001 to ANTS-007 baseline issues in Linear via GraphQL API.

Usage:
  LINEAR_API_KEY=lin_api_xxx python3 create_linear_issues.py [--dry-run] [--team-id TEAM_ID]

Find your team ID at: https://linear.app/settings/api
Or run with --list-teams to discover team IDs.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error

LINEAR_API = "https://api.linear.app/graphql"

ISSUES = [
    {
        "title": "ANTS-001 Gateway baseline",
        "description": """## Goal
Publish a tested public baseline for `ants-ai-gateway`.

## Context
This repository is the first public ANTS candidate and must expose the gateway contract, tests, SQL schema, specs, and safe examples without leaking local operational context.

## Acceptance Criteria
- `ants-ai-gateway` exists as an isolated GitHub repository.
- `pytest` passes in the isolated repository.
- `.env`, archives, and credential blobs are excluded from publication.
- The repository root contains `.coderabbit.yaml`, PR template, and publication docs.
- Baseline PR includes validation evidence.

## Technical Constraints
- Publish only `ants-ai-gateway`, not the parent `appmultiANTS`.
- No secrets, real tokens, or private operational artifacts may be committed.

## Files likely affected
- `README.md`, `.gitignore`, `.coderabbit.yaml`, `.github/`, `docs/publication-checklist.md`

## Test or Harness
- `pytest`
- `python scripts/package_release.py --output ../ants-ai-gateway.tar.gz`

## Definition of Done
- Public repo exists.
- Baseline commit/PR is published.
- Validation evidence is attached in PR description.
""",
    },
    {
        "title": "ANTS-002 Supabase memory baseline",
        "description": """## Goal
Version and harden the Supabase operational schema.

## Context
Supabase is the canonical memory for ANTS. The gateway needs a schema that captures specs, tasks, model usage, workflow runs, harness evidence, and reusable patterns with RLS.

## Acceptance Criteria
- SQL schema includes the operational ledger tables required by ANTS.
- `model_usage` captures `project_id` and `latency_ms`.
- `workflow_runs` exists for orchestrator traceability.
- SQL migrations are versioned and reviewable.
- RLS and revoke statements cover the operational tables.

## Technical Constraints
- No table stores raw secret values.
- Changes must remain compatible with Supabase/Postgres.

## Files likely affected
- `sql/init_supabase_tables.sql`, `sql/migrations/001_init.sql`, `sql/migrations/002_add_workflow_runs.sql`, `tests/test_sql_schema.py`

## Test or Harness
- `pytest tests/test_sql_schema.py`

## Definition of Done
- Migration files committed.
- Tests assert the schema contract.
- Snapshot schema matches the latest migration state.
""",
    },
    {
        "title": "ANTS-003 Qwen provider execution",
        "description": """## Goal
Keep direct Qwen execution stable, explicit, and logged.

## Context
Qwen is the primary implementation model in the gateway, so adapter execution, provider policy, and usage logging need to stay predictable.

## Acceptance Criteria
- Qwen execution path remains green in provider tests.
- Logging captures provider/model/task metadata for Qwen runs.
- Fallback behavior remains explicit when a route is not executable.

## Technical Constraints
- Preserve current direct-provider strategy.
- Do not silently route Qwen calls through a different provider.

## Files likely affected
- `app/providers/qwen.py`, `app/model_router.py`, `app/services/usage_logger.py`, `tests/test_qwen_provider.py`, `tests/test_model_router.py`

## Test or Harness
- `pytest tests/test_qwen_provider.py tests/test_model_router.py`

## Definition of Done
- Provider tests pass.
- Router behavior is documented and stable.
""",
    },
    {
        "title": "ANTS-004 Executor sessions",
        "description": """## Goal
Track Codex, Claude Code, and Antigravity executor session state safely.

## Context
ANTS needs visibility into executor readiness without exposing credentials or treating workstation state as implicit truth.

## Acceptance Criteria
- Executor session endpoint returns structured status.
- Credential pool status remains sanitized.
- Session config can distinguish configured, pending auth, and expired states.

## Technical Constraints
- No secrets or tokens in API responses.
- Local environment assumptions must stay explicit.

## Files likely affected
- `app/tool_executors.py`, `app/executor_credentials.py`, `config/executor_sessions.example.yaml`, `tests/test_executor_credentials.py`

## Test or Harness
- `pytest tests/test_executor_credentials.py tests/test_tool_executors.py`

## Definition of Done
- Session status is queryable.
- Responses are sanitized and documented.
""",
    },
    {
        "title": "ANTS-005 Executor smoke harness",
        "description": """## Goal
Validate executor availability without exposing secrets.

## Context
The gateway needs a lightweight harness to confirm tool executors are callable before higher-risk orchestration depends on them.

## Acceptance Criteria
- Smoke endpoint validates selected executors.
- Commands are non-destructive and sanitized.
- Tests cover failure modes and command construction.

## Technical Constraints
- Never expose credentials in stdout/stderr.
- Avoid interactive prompts in smoke mode.

## Files likely affected
- `app/executor_smoke.py`, `app/main.py`, `tests/test_executor_smoke.py`, `specs/executor-smoke-test.md`

## Test or Harness
- `pytest tests/test_executor_smoke.py`

## Definition of Done
- Smoke tests pass.
- Spec and endpoint behavior match.
""",
    },
    {
        "title": "ANTS-006 Executor service adapter",
        "description": """## Goal
Separate gateway governance from host executor runtime concerns.

## Context
ANTS should keep policy, preflight, and audit behavior in the gateway while allowing executor-specific runtime concerns to evolve separately.

## Acceptance Criteria
- Clear boundary exists between gateway policy and executor runtime calls.
- Adapter/service responsibilities are documented.
- Risks and future extraction path are recorded.

## Technical Constraints
- Do not collapse governance and execution into one opaque subsystem.
- Preserve current API behavior while clarifying the architecture.

## Files likely affected
- `docs/adr/`, `app/executor_smoke.py`, `app/tool_executors.py`, `SPEC.md`

## Test or Harness
- ADR/spec review plus existing executor tests.

## Definition of Done
- Architecture boundary is documented.
- Follow-up implementation path is traceable.
""",
    },
    {
        "title": "ANTS-007 Funding opportunities",
        "description": """## Goal
Track OSS, AI credit, and grant opportunities that can subsidize the public ANTS stack.

## Context
Publishing `ants-ai-gateway` publicly enables CodeRabbit, GitHub programs, and other ecosystem benefits that can reduce operating cost.

## Acceptance Criteria
- Funding opportunities are documented with eligibility and next steps.
- Repository publication dependencies are identified.
- Follow-up actions are linked to GitHub/Linear work.

## Technical Constraints
- Keep the research lightweight and actionable.
- Prefer programs relevant to public repositories and OSS maintainers.

## Files likely affected
- `docs/funding-opportunities.md`, `docs/publication-checklist.md`

## Test or Harness
- Manual review of links, status, and prerequisites.

## Definition of Done
- Opportunity list is current enough to act on.
- Publication blockers are explicit.
""",
    },
]


def gql(query: str, variables: dict, api_key: str) -> dict:
    data = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        LINEAR_API,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    if "errors" in result:
        raise RuntimeError(f"GraphQL errors: {result['errors']}")
    return result


def list_teams(api_key: str):
    result = gql("{ teams { nodes { id name key } } }", {}, api_key)
    teams = result.get("data", {}).get("teams", {}).get("nodes", [])
    print("Available teams:")
    for t in teams:
        print(f"  id={t['id']}  key={t['key']}  name={t['name']}")
    return teams


def create_issue(title: str, description: str, team_id: str, api_key: str) -> dict:
    mutation = """
    mutation CreateIssue($title: String!, $description: String!, $teamId: String!) {
      issueCreate(input: { title: $title, description: $description, teamId: $teamId }) {
        success
        issue { id identifier title url }
      }
    }
    """
    result = gql(mutation, {"title": title, "description": description, "teamId": team_id}, api_key)
    return result.get("data", {}).get("issueCreate", {})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--team-id", default="")
    parser.add_argument("--list-teams", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        print("ERROR: Set LINEAR_API_KEY environment variable.")
        print("  Get it from: https://linear.app/settings/api → Personal API keys")
        sys.exit(1)

    if args.list_teams:
        list_teams(api_key)
        return

    team_id = args.team_id
    if not team_id:
        teams = list_teams(api_key)
        if len(teams) == 1:
            team_id = teams[0]["id"]
            print(f"Using only team: {teams[0]['name']} ({team_id})")
        else:
            print("ERROR: Multiple teams found. Specify --team-id <id>")
            sys.exit(1)

    print(f"\nCreating {len(ISSUES)} issues in team {team_id}{'  [DRY RUN]' if args.dry_run else ''}...")

    for i, issue in enumerate(ISSUES, 1):
        title = issue["title"]
        description = issue["description"]
        if args.dry_run:
            print(f"  [{i}/{len(ISSUES)}] DRY RUN: {title}")
            continue
        try:
            result = create_issue(title, description, team_id, api_key)
            if result.get("success"):
                info = result["issue"]
                print(f"  [{i}/{len(ISSUES)}] Created {info['identifier']}: {info['url']}")
            else:
                print(f"  [{i}/{len(ISSUES)}] FAILED: {title}")
                print(f"    Response: {result}")
        except Exception as e:
            print(f"  [{i}/{len(ISSUES)}] ERROR: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
