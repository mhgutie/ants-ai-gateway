from __future__ import annotations

"""Database queries for the ANTS AI Gateway.

This module provides data access functions for projects, specs, tasks,
model usage statistics, and n8n operational ledger entries (workflow runs,
artifacts, and agent handoffs). It includes a resilient in-memory mock store
fallback for local offline development when Supabase or Postgres database
connections are unavailable.
"""

import logging
import json
from typing import Any
from datetime import datetime
from uuid import uuid4

from app.db import db_connection

logger = logging.getLogger(__name__)

# Resilient in-memory fallback store in case Supabase is not connected
MOCK_STORE: dict[str, list[dict[str, Any]]] = {
    "projects": [
        {
            "id": "c1a92e71-8bfb-4f9e-b2d9-2eabd057d59b",
            "project_key": "ANTS-FACTORY",
            "name": "ANTS MVP Solution Factory",
            "status": "active",
            "owner": "Mauricio Gutierrez",
            "metadata": {},
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "id": "a50c8222-1209-4322-866e-2ba295828261",
            "project_key": "CAREER-LAB",
            "name": "ANTS CareerLab Workspace",
            "status": "active",
            "owner": "Gabriel",
            "metadata": {},
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    ],
    "specs": [
        {
            "id": "d75d332d-222a-4316-bcbf-9a7f537y65b2",
            "project_id": "c1a92e71-8bfb-4f9e-b2d9-2eabd057d59b",
            "task_id": "ANTS-001",
            "title": "Build AI Gateway UI",
            "problem": "Create a premium visual dashboard to invoke and monitor ANTS agents.",
            "context": {"focus": "premium aesthetics", "role_based_split": True},
            "expected_result": "A high-fidelity vanilla HTML/JS/CSS frontend in dark mode served from the gateway.",
            "allowed_tools": ["run_command", "view_file", "write_to_file"],
            "required_agents_models": ["Qwen3-Coder", "Kimi-K2.6"],
            "routing_decision": {"recommended_model": "qwen3-coder", "fallback_model": "kimi-k2.6"},
            "acceptance_criteria": ["Headed browser smoke test passes", "Role switching is immediate", "DB offline mode works"],
            "risks": ["Passphrase SSH block", "Database connectivity lag"],
            "token_cost_budget": {"max_total_cost_usd": 0.50, "max_iterations": 5},
            "test_harness": {"type": "playwright_smoke", "required_score": 95},
            "final_output": None,
            "status": "approved",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    ],
    "tasks": [
        {
            "id": "e2ba2958-8bfb-48d9-2ba2-95828261ab2f",
            "project_id": "c1a92e71-8bfb-4f9e-b2d9-2eabd057d59b",
            "spec_id": "d75d332d-222a-4316-bcbf-9a7f537y65b2",
            "task_id": "ANTS-001",
            "title": "Implement main.py database router endpoints",
            "status": "in_progress",
            "priority": "high",
            "owner_agent": "Qwen3-Coder",
            "linear_issue_key": "ANTS-001",
            "linear_issue_url": "https://linear.app/ants/issue/ANTS-001",
            "github_branch": "feat/ants-001-gateway-db-api",
            "github_pr_url": "https://github.com/ants-factory/ants-ai-gateway/pull/1",
            "acceptance_criteria": ["FastAPI compiles successfully", "Endpoints return correct schema"],
            "definition_of_done": ["Harness checks pass", "PR merged with validation evidence"],
            "decision_log": [{"decision": "Added mock fallbacks", "rationale": "Resilience first"}],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    ],
    "usage": [
        {
            "id": "f898a123-12ba-4bcf-aefc-34eaefd32489",
            "project_id": "c1a92e71-8bfb-4f9e-b2d9-2eabd057d59b",
            "task_id": "ANTS-001",
            "run_id": "run-db-api-001",
            "provider": "openrouter",
            "model": "deepseek/deepseek-chat-v4",
            "task_type": "coding_debug",
            "input_tokens_estimated": 850,
            "input_tokens_real": 874,
            "output_tokens_real": 240,
            "total_tokens_real": 1114,
            "estimated_cost_usd": 0.00045,
            "real_cost_usd": 0.00047,
            "latency_ms": 1120,
            "status": "success",
            "stop_reason": "stop",
            "created_at": datetime.now()
        }
    ],
    "workflow_runs": [],
    "artifacts": [],
    "agent_handoffs": []
}

def to_dict(row: dict | Any) -> dict[str, Any]:
    """Converts a database row or asyncpg Record into a standard dictionary.

    Datetime values inside the row are serialized to ISO 8601 string format
    to ensure JSON compatibility.

    Args:
        row: A database record, asyncpg Record, dictionary, or any row-like object.

    Returns:
        A dictionary containing the row's keys and values, with datetime objects
        serialized to ISO strings. If row is empty, returns an empty dictionary.
    """
    if not row:
        return {}
    # Convert asyncpg Record to dict
    d = dict(row)
    # Serialize datetime objects to ISO strings
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        elif hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d

async def get_projects() -> list[dict[str, Any]]:
    """Retrieves all active projects ordered by creation date descending.

    This function attempts to fetch projects from the live database. If the
    database connection is unavailable or an error occurs, it resiliently
    falls back to the in-memory MOCK_STORE project list.

    Returns:
        A list of dictionaries representing the projects.
    """
    try:
        async with db_connection() as conn:
            if conn is None:
                logger.info("Using mock projects list.")
                return [to_dict(p) for p in MOCK_STORE["projects"]]
            rows = await conn.fetch("select * from projects order by created_at desc")
            return [to_dict(r) for r in rows]
    except Exception as exc:
        logger.warning(f"Error fetching projects: {exc}. Falling back to mocks.")
        return [to_dict(p) for p in MOCK_STORE["projects"]]

async def create_project(name: str, key: str | None = None, owner: str | None = None, metadata: dict | None = None) -> dict[str, Any]:
    """Creates a new project inside the database or fallback mock store.

    Args:
        name: The human-readable name of the project.
        key: An optional unique project key identifier (e.g., 'ANTS-FACTORY').
            If not specified, one is automatically generated based on the name.
        owner: The owner of the project. Defaults to 'Administrator'.
        metadata: Optional dictionary of metadata associated with the project.

    Returns:
        A dictionary representing the newly created project record.
    """
    proj_id = str(uuid4())
    proj_key = key or f"PROJ-{name.upper().replace(' ', '-')[:8]}"
    owner_name = owner or "Administrator"
    meta = metadata or {}
    now = datetime.now()
    
    try:
        async with db_connection() as conn:
            if conn is None:
                new_proj = {
                    "id": proj_id,
                    "project_key": proj_key,
                    "name": name,
                    "status": "active",
                    "owner": owner_name,
                    "metadata": meta,
                    "created_at": now,
                    "updated_at": now
                }
                MOCK_STORE["projects"].insert(0, new_proj)
                return to_dict(new_proj)
            
            await conn.execute(
                """
                insert into projects (id, project_key, name, status, owner, metadata, created_at, updated_at)
                values ($1, $2, $3, 'active', $4, $5, $6, $7)
                """,
                proj_id, proj_key, name, owner_name, json.dumps(meta), now, now
            )
            row = await conn.fetchrow("select * from projects where id = $1", proj_id)
            return to_dict(row)
    except Exception as exc:
        logger.warning(f"Error creating project in DB: {exc}. Saving to mock store.")
        new_proj = {
            "id": proj_id,
            "project_key": proj_key,
            "name": name,
            "status": "active",
            "owner": owner_name,
            "metadata": meta,
            "created_at": now,
            "updated_at": now
        }
        MOCK_STORE["projects"].insert(0, new_proj)
        return to_dict(new_proj)

async def get_specs() -> list[dict[str, Any]]:
    """Retrieves all specification drafts and approved records from the store.

    Attempts to fetch from the live database, falling back to the in-memory
    mock store on failure or if the database is disconnected.

    Returns:
        A list of dictionaries representing the specifications, ordered by creation
        date descending.
    """
    try:
        async with db_connection() as conn:
            if conn is None:
                return [to_dict(s) for s in MOCK_STORE["specs"]]
            rows = await conn.fetch("select * from specs order by created_at desc")
            return [to_dict(r) for r in rows]
    except Exception as exc:
        logger.warning(f"Error fetching specs: {exc}. Falling back to mocks.")
        return [to_dict(s) for s in MOCK_STORE["specs"]]

async def create_spec(
    project_id: str | None, title: str, problem: str, expected_result: str | None = None,
    allowed_tools: list[str] | None = None, required_agents: list[str] | None = None,
    acceptance_criteria: list[str] | None = None, risks: list[str] | None = None,
    budget: dict[str, Any] | None = None, test_harness: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Creates a new task specification in the database or fallback store.

    Args:
        project_id: The UUID of the parent project this specification belongs to.
        title: The title describing the goal or task to perform.
        problem: A detailed statement of the problem to be solved.
        expected_result: The expected deliverables or visual outcome.
        allowed_tools: A list of tool names allowed for agent execution.
        required_agents: A list of AI models or agent types recommended.
        acceptance_criteria: A list of testable conditions for acceptance.
        risks: Identified risks or limitations for the execution.
        budget: Token budget and cost parameters.
        test_harness: Automated testing harness specifications.

    Returns:
        A dictionary representing the newly created specification record.
    """
    spec_id = str(uuid4())
    now = datetime.now()
    tools = allowed_tools or []
    agents = required_agents or []
    criteria = acceptance_criteria or []
    r_list = risks or []
    b_obj = budget or {}
    h_obj = test_harness or {}
    
    try:
        async with db_connection() as conn:
            if conn is None:
                new_spec = {
                    "id": spec_id,
                    "project_id": project_id,
                    "task_id": f"TSK-{spec_id[:6].upper()}",
                    "title": title,
                    "problem": problem,
                    "context": {},
                    "expected_result": expected_result,
                    "allowed_tools": tools,
                    "required_agents_models": agents,
                    "routing_decision": {"recommended_model": "auto"},
                    "acceptance_criteria": criteria,
                    "risks": r_list,
                    "token_cost_budget": b_obj,
                    "test_harness": h_obj,
                    "final_output": None,
                    "status": "draft",
                    "created_at": now,
                    "updated_at": now
                }
                MOCK_STORE["specs"].insert(0, new_spec)
                return to_dict(new_spec)
            
            await conn.execute(
                """
                insert into specs (
                    id, project_id, task_id, title, problem, context, expected_result,
                    allowed_tools, required_agents_models, routing_decision,
                    acceptance_criteria, risks, token_cost_budget, test_harness, status, created_at, updated_at
                )
                values ($1, $2, $3, $4, $5, '{}'::jsonb, $6, $7, $8, '{}'::jsonb, $9, $10, $11, $12, 'draft', $13, $14)
                """,
                spec_id, project_id, f"TSK-{spec_id[:6].upper()}", title, problem, expected_result,
                tools, agents, criteria, r_list, json.dumps(b_obj), json.dumps(h_obj), now, now
            )
            row = await conn.fetchrow("select * from specs where id = $1", spec_id)
            return to_dict(row)
    except Exception as exc:
        logger.warning(f"Error creating spec in DB: {exc}. Saving to mock store.")
        new_spec = {
            "id": spec_id,
            "project_id": project_id,
            "task_id": f"TSK-{spec_id[:6].upper()}",
            "title": title,
            "problem": problem,
            "context": {},
            "expected_result": expected_result,
            "allowed_tools": tools,
            "required_agents_models": agents,
            "routing_decision": {"recommended_model": "auto"},
            "acceptance_criteria": criteria,
            "risks": r_list,
            "token_cost_budget": b_obj,
            "test_harness": h_obj,
            "final_output": None,
            "status": "draft",
            "created_at": now,
            "updated_at": now
        }
        MOCK_STORE["specs"].insert(0, new_spec)
        return to_dict(new_spec)

async def get_tasks() -> list[dict[str, Any]]:
    """Retrieves all task execution records from the database or mock store.

    Returns:
        A list of dictionaries representing the tasks, ordered by creation date
        descending.
    """
    try:
        async with db_connection() as conn:
            if conn is None:
                return [to_dict(t) for t in MOCK_STORE["tasks"]]
            rows = await conn.fetch("select * from tasks order by created_at desc")
            return [to_dict(r) for r in rows]
    except Exception as exc:
        logger.warning(f"Error fetching tasks: {exc}. Falling back to mocks.")
        return [to_dict(t) for t in MOCK_STORE["tasks"]]

async def get_usage_logs() -> list[dict[str, Any]]:
    """Retrieves the latest 50 model usage logging records for transparency.

    Returns:
        A list of dictionaries representing token usage, estimated/real costs,
        and latency logs for past LLM executions.
    """
    try:
        async with db_connection() as conn:
            if conn is None:
                return [to_dict(u) for u in MOCK_STORE["usage"]]
            rows = await conn.fetch("select * from model_usage order by created_at desc limit 50")
            return [to_dict(r) for r in rows]
    except Exception as exc:
        logger.warning(f"Error fetching model_usage logs: {exc}. Falling back to mocks.")
        return [to_dict(u) for u in MOCK_STORE["usage"]]

async def get_dashboard_stats() -> dict[str, Any]:
    """Gathers aggregated dashboard statistics across projects, specs, and usage.

    Calculates total runs, estimated vs real costs, successful execution rates,
    and returns breakdowns by model and provider. Falls back to mock values if
    the database connection is offline.

    Returns:
        A dictionary containing dashboard stats, breakdown lists, and a database
        connection status flag.
    """
    try:
        async with db_connection() as conn:
            if conn is None:
                return _mock_dashboard_stats()
            
            # Query aggregates
            total_runs = await conn.fetchval("select count(*) from model_usage")
            total_real_cost = await conn.fetchval("select coalesce(sum(real_cost_usd), 0) from model_usage")
            total_est_cost = await conn.fetchval("select coalesce(sum(estimated_cost_usd), 0) from model_usage")
            
            success_count = await conn.fetchval("select count(*) from model_usage where status='success'")
            success_rate = (success_count / total_runs * 100) if total_runs > 0 else 100.0
            
            projects_count = await conn.fetchval("select count(*) from projects")
            specs_count = await conn.fetchval("select count(*) from specs")
            tasks_count = await conn.fetchval("select count(*) from tasks")
            
            # Provider breakdown
            p_rows = await conn.fetch(
                """
                select provider, count(*) as count, coalesce(sum(real_cost_usd), 0) as cost 
                from model_usage 
                group by provider 
                order by cost desc
                """
            )
            providers = [{"provider": r["provider"], "count": r["count"], "cost": float(r["cost"])} for r in p_rows]
            
            # Model breakdown
            m_rows = await conn.fetch(
                """
                select model, count(*) as count, coalesce(sum(real_cost_usd), 0) as cost 
                from model_usage 
                group by model 
                order by cost desc
                """
            )
            models = [{"model": r["model"], "count": r["count"], "cost": float(r["cost"])} for r in m_rows]
            
            return {
                "total_runs": total_runs,
                "total_real_cost_usd": float(total_real_cost),
                "total_estimated_cost_usd": float(total_est_cost),
                "success_rate_percent": round(success_rate, 2),
                "projects_count": projects_count,
                "specs_count": specs_count,
                "tasks_count": tasks_count,
                "provider_breakdown": providers,
                "model_breakdown": models,
                "database_connected": True
            }
    except Exception as exc:
        logger.warning(f"Error fetching dashboard stats: {exc}. Using mock data.")
        return _mock_dashboard_stats()

def _mock_dashboard_stats() -> dict[str, Any]:
    """Generates synthetic, premium-looking dashboard statistics for offline mode.

    Returns:
        A dictionary containing representative, mock aggregated stats, provider
        breakdowns, and model distributions with database_connected set to False.
    """
    # Mock aggregates
    return {
        "total_runs": 142,
        "total_real_cost_usd": 0.0845,
        "total_estimated_cost_usd": 0.0912,
        "success_rate_percent": 97.18,
        "projects_count": len(MOCK_STORE["projects"]),
        "specs_count": len(MOCK_STORE["specs"]),
        "tasks_count": len(MOCK_STORE["tasks"]),
        "provider_breakdown": [
            {"provider": "openrouter", "count": 82, "cost": 0.0512},
            {"provider": "openai", "count": 24, "cost": 0.0245},
            {"provider": "gemini", "count": 36, "cost": 0.0088}
        ],
        "model_breakdown": [
            {"model": "qwen3-coder", "count": 68, "cost": 0.0310},
            {"model": "deepseek-v4-pro", "count": 32, "cost": 0.0285},
            {"model": "kimi-k2.6", "count": 18, "cost": 0.0188},
            {"model": "gemini-3.5-flash", "count": 24, "cost": 0.0062}
        ],
        "database_connected": False
    }

async def log_workflow_run(payload: dict[str, Any]) -> bool:
    """Logs an n8n workflow execution run to the database or mock store.

    Args:
        payload: A dictionary containing workflow run details.

    Returns:
        True if the execution run was successfully logged, False otherwise.
    """
    try:
        async with db_connection() as conn:
            if conn is None:
                MOCK_STORE["workflow_runs"].insert(0, payload)
                return True
            
            await conn.execute(
                """
                insert into workflow_runs (
                    project_id, task_id, run_id, workflow_name, workflow_version,
                    orchestrator, n8n_workflow_id, n8n_execution_id, trigger_source,
                    status, input_summary, output_summary, error_message, latency_ms,
                    started_at, completed_at
                )
                values (
                    $1, $2, $3, $4, $5,
                    coalesce($6, 'n8n'), $7, $8, $9,
                    $10, coalesce($11, '{}'::jsonb), coalesce($12, '{}'::jsonb), $13, $14,
                    $15, $16
                )
                """,
                payload.get("project_id"),
                payload.get("task_id"),
                payload.get("run_id"),
                payload.get("workflow_name"),
                payload.get("workflow_version"),
                payload.get("orchestrator"),
                payload.get("n8n_workflow_id"),
                payload.get("n8n_execution_id"),
                payload.get("trigger_source"),
                payload.get("status"),
                json.dumps(payload.get("input_summary") or {}),
                json.dumps(payload.get("output_summary") or {}),
                payload.get("error_message"),
                payload.get("latency_ms"),
                payload.get("started_at"),
                payload.get("completed_at")
            )
            return True
    except Exception as exc:
        logger.warning(f"Error logging workflow run in DB: {exc}. Saving to mock store.")
        MOCK_STORE["workflow_runs"].insert(0, payload)
        return True

async def log_artifact(payload: dict[str, Any]) -> bool:
    """Registers a generated artifact (e.g., file, PDF, mockup) in the database or mock store.

    Args:
        payload: A dictionary containing artifact information.

    Returns:
        True if the artifact registration was successfully logged, False otherwise.
    """
    try:
        async with db_connection() as conn:
            if conn is None:
                MOCK_STORE["artifacts"].insert(0, payload)
                return True
            
            await conn.execute(
                """
                insert into artifacts (
                    project_id, task_id, run_id, artifact_type, name, uri,
                    storage_provider, metadata
                )
                values (
                    $1, $2, $3, $4, $5, $6,
                    $7, coalesce($8, '{}'::jsonb)
                )
                """,
                payload.get("project_id"),
                payload.get("task_id"),
                payload.get("run_id"),
                payload.get("artifact_type"),
                payload.get("name"),
                payload.get("uri"),
                payload.get("storage_provider"),
                json.dumps(payload.get("metadata") or {})
            )
            return True
    except Exception as exc:
        logger.warning(f"Error logging artifact in DB: {exc}. Saving to mock store.")
        MOCK_STORE["artifacts"].insert(0, payload)
        return True

async def log_agent_handoff(payload: dict[str, Any]) -> bool:
    """Logs an agent-to-agent handoff event in the database or mock store.

    Args:
        payload: A dictionary containing handoff transition details.

    Returns:
        True if the handoff was successfully logged, False otherwise.
    """
    try:
        async with db_connection() as conn:
            if conn is None:
                MOCK_STORE["agent_handoffs"].insert(0, payload)
                return True
            
            await conn.execute(
                """
                insert into agent_handoffs (
                    project_id, task_id, run_id, source_agent, target_agent,
                    branch, status, completed, next_steps, risks,
                    artifact_links, sanitized_context, metadata
                )
                values (
                    $1, $2, $3, $4, $5,
                    $6, coalesce($7, 'ready'), coalesce($8, '[]'::jsonb), coalesce($9, '[]'::jsonb), coalesce($10, '[]'::jsonb),
                    coalesce($11, '[]'::jsonb), $12, coalesce($13, '{}'::jsonb)
                )
                """,
                payload.get("project_id"),
                payload.get("task_id"),
                payload.get("run_id"),
                payload.get("source_agent"),
                payload.get("target_agent"),
                payload.get("branch"),
                payload.get("status"),
                json.dumps(payload.get("completed") or []),
                json.dumps(payload.get("next_steps") or []),
                json.dumps(payload.get("risks") or []),
                json.dumps(payload.get("artifact_links") or []),
                payload.get("sanitized_context"),
                json.dumps(payload.get("metadata") or {})
            )
            return True
    except Exception as exc:
        logger.warning(f"Error logging agent handoff in DB: {exc}. Saving to mock store.")
        MOCK_STORE["agent_handoffs"].insert(0, payload)
        return True


async def claim_proposal_candidates(n8n_workflow_id: str | None = None, n8n_execution_id: str | None = None, run_id: str | None = None) -> list[dict[str, Any]]:
    """Claims unclaimed shortlisted or proposal candidates and registers them in the intake queue.

    Args:
        n8n_workflow_id: The active n8n workflow ID that is claiming the candidates.
        n8n_execution_id: The active n8n execution ID.
        run_id: The workflow run logging ID.

    Returns:
        A list of dictionaries representing the claimed opportunity records.
    """
    now = datetime.now()
    workflow_id = n8n_workflow_id or ""
    execution_id = n8n_execution_id or ""
    workflow_run_id = run_id or ""

    try:
        async with db_connection() as conn:
            if conn is None:
                # Return empty list in mock mode
                return []

            # 1. Fetch unclaimed or failed candidates from the opportunity workbench joined with intake
            # We fetch those where intake_status is NULL (not claimed) or 'failed' (retriable)
            unclaimed = await conn.fetch(
                """
                select
                  w.external_tender_id,
                  w.title,
                  w.buyer_name,
                  w.category,
                  w.opportunity_score,
                  w.triage_score,
                  w.closing_at,
                  w.estimated_budget,
                  w.currency,
                  w.source_url,
                  w.tender_tags,
                  w.tender_decision_status,
                  w.tender_priority,
                  w.tender_next_action,
                  w.tender_reviewer_notes,
                  w.tender_recommended_action,
                  w.selected_workflow_count,
                  w.selected_workflows,
                  w.mapped_occupation_count,
                  w.mapped_occupations,
                  w.pipeline_score,
                  w.next_pipeline_stage
                from public.noco_mvp_opportunity_workbench w
                left join public.mp_proposal_candidate_intake i
                  on i.external_tender_id = w.external_tender_id
                where w.tender_decision_status in ('shortlisted', 'proposal_candidate')
                  and (i.intake_status is null or i.intake_status = 'failed')
                order by w.tender_priority asc, w.pipeline_score desc, w.closing_at asc nulls last
                """
            )

            if not unclaimed:
                return []

            # 2. Ingest claimed rows into mp_proposal_candidate_intake with status 'queued'
            claimed_records = []
            for r in unclaimed:
                tender_id = r["external_tender_id"]
                decision = r["tender_decision_status"]
                priority = r["tender_priority"] or 2
                score = r["pipeline_score"] or 0
                stage = r["next_pipeline_stage"] or ""

                await conn.execute(
                    """
                    insert into public.mp_proposal_candidate_intake (
                      external_tender_id, decision_status, priority, pipeline_score, next_pipeline_stage,
                      intake_status, last_workflow_run_id, n8n_workflow_id, n8n_execution_id, claimed_at, updated_at
                    )
                    values ($1, $2, $3, $4, $5, 'queued', $6, $7, $8, $9, $9)
                    on conflict (external_tender_id) do update set
                      decision_status = excluded.decision_status,
                      priority = excluded.priority,
                      pipeline_score = excluded.pipeline_score,
                      next_pipeline_stage = excluded.next_pipeline_stage,
                      intake_status = 'queued',
                      last_workflow_run_id = excluded.last_workflow_run_id,
                      n8n_workflow_id = excluded.n8n_workflow_id,
                      n8n_execution_id = excluded.n8n_execution_id,
                      claimed_at = excluded.claimed_at,
                      updated_at = excluded.updated_at
                    """,
                    tender_id, decision, priority, score, stage, workflow_run_id, workflow_id, execution_id, now
                )
                claimed_records.append(to_dict(r))

            return claimed_records
    except Exception as exc:
        logger.warning(f"Error claiming proposal candidates in DB: {exc}")
        return []


async def update_proposal_intake(
    external_tender_id: str,
    intake_status: str,
    error_message: str | None = None,
    run_id: str | None = None,
    n8n_workflow_id: str | None = None,
    n8n_execution_id: str | None = None
) -> bool:
    """Updates the orchestration intake status of a claimed opportunity candidate in Supabase.

    Args:
        external_tender_id: The unique external Mercado Público tender ID.
        intake_status: The new status ('queued', 'handoff_created', 'analysis_started', 'completed', 'failed').
        error_message: Optional error diagnostics if status is 'failed'.
        run_id: The associated workflow run ID.
        n8n_workflow_id: The active n8n workflow ID.
        n8n_execution_id: The active n8n execution ID.

    Returns:
        True if the update was successful, False otherwise.
    """
    now = datetime.now()
    error_msg = error_message or ""
    workflow_run_id = run_id or ""
    workflow_id = n8n_workflow_id or ""
    exec_id = n8n_execution_id or ""

    try:
        async with db_connection() as conn:
            if conn is None:
                return True

            await conn.execute(
                """
                update public.mp_proposal_candidate_intake
                set
                  intake_status = $2,
                  error_message = case when $3 <> '' then $3 else error_message end,
                  last_workflow_run_id = case when $4 <> '' then $4 else last_workflow_run_id end,
                  n8n_workflow_id = case when $5 <> '' then $5 else n8n_workflow_id end,
                  n8n_execution_id = case when $6 <> '' then $6 else n8n_execution_id end,
                  handoff_created_at = case when $2 = 'handoff_created' then $7 else handoff_created_at end,
                  completed_at = case when $2 = 'completed' then $7 else completed_at end,
                  updated_at = $7
                where external_tender_id = $1
                """,
                external_tender_id, intake_status, error_msg, workflow_run_id, workflow_id, exec_id, now
            )
            return True
    except Exception as exc:
        logger.warning(f"Error updating proposal candidate intake status in DB: {exc}")
        return False

