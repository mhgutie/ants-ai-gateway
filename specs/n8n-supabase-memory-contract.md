# n8n to Supabase Memory Contract

## Goal

Give n8n a stable, guarded API contract for writing ANTS operational memory into Supabase through the gateway instead of embedding database logic directly in workflows.

## Context

ANTS uses Supabase as the canonical memory and system of record. n8n should orchestrate triggers, retries, HTTP calls, and notifications, but durable records must land in Supabase with consistent shape, authentication, and secret hygiene.

## Contract

n8n writes to the gateway with `X-ANTS-API-Key`. The gateway then writes to Supabase using its runtime database credentials.

### Workflow runs

`POST /n8n/workflow-runs`

Required fields:

- `run_id`
- `workflow_name`
- `status`

Optional fields:

- `project_id`
- `task_id`
- `workflow_version`
- `n8n_workflow_id`
- `n8n_execution_id`
- `trigger_source`
- `input_summary`
- `output_summary`
- `error_message`
- `latency_ms`
- `started_at`
- `completed_at`

### Artifacts

`POST /n8n/artifacts`

Required fields:

- `artifact_type`
- `name`
- `uri`

Optional fields:

- `project_id`
- `task_id`
- `run_id`
- `storage_provider`
- `metadata`

### Agent handoffs

`POST /n8n/handoffs`

Required fields:

- `run_id`
- `source_agent`
- `target_agent`
- `sanitized_context`

Optional fields:

- `project_id`
- `task_id`
- `branch`
- `status`
- `completed`
- `next_steps`
- `risks`
- `artifact_links`
- `metadata`

## Acceptance Criteria

- n8n can log workflow runs without direct database access.
- n8n can register generated artifacts such as Drive files, PDFs, mockups, and handoff files.
- n8n can record compact sanitized handoffs between agents.
- No endpoint accepts or requires provider API keys, OAuth tokens, refresh tokens, or database credentials in the body.
- Tables use RLS and revoke public roles.
- Harnesses cover SQL shape and endpoint contracts.

## Harness

- `tests/test_sql_schema.py`
- `tests/test_n8n_contract.py`
