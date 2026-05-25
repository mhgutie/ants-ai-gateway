from __future__ import annotations

import logging
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
    ]
}

def to_dict(row: dict | Any) -> dict[str, Any]:
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
                proj_id, proj_key, name, owner_name, meta, now, now
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
                tools, agents, criteria, r_list, b_obj, h_obj, now, now
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
