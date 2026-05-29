from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.cost_calculator import real_cost_usd
from app.model_router import provider_for
from app.providers import get_provider_client
from app.schemas import ContextScope, SpecBuildRequest, SpecBuildResponse, TaskType
from app.services.preflight_service import run_preflight
from app.schemas import GatewayRequest

logger = logging.getLogger(__name__)

_SPEC_BUILDER_MODEL = "kimi-k2.6"
_SPEC_BUILDER_TASK_TYPE = TaskType.product_design

_SYSTEM_PROMPT = """You are the ANTS Spec Architect. Your sole job is to produce a machine-readable JSON specification for any task described by the user. Return ONLY valid JSON — no markdown fences, no prose, no explanation.

The JSON must have exactly these fields:
{
  "title": "short task title",
  "problem": "1-3 sentence problem description",
  "expected_result": "concrete deliverable description",
  "allowed_tools": ["run_command", "view_file", "write_to_file"],
  "required_agents": ["model-name-1", "model-name-2"],
  "acceptance_criteria": ["criterion 1", "criterion 2", "criterion 3"],
  "risks": ["risk 1", "risk 2"],
  "budget": {"max_total_cost_usd": 0.50, "max_iterations": 5},
  "test_harness": {"type": "pytest", "required_score": 90}
}

Rules:
- acceptance_criteria: 3-6 short, testable, binary items.
- required_agents: use only real model aliases (kimi-k2.6, deepseek-v4-pro, qwen3-coder, gpt-5.5).
- budget.max_total_cost_usd: estimate based on task complexity (0.10 simple, 0.50 medium, 2.00 complex).
- Do not include any key outside the schema above.
- Return raw JSON only."""


def _extract_json(text: str) -> dict[str, Any]:
    """Extract first JSON object from model output, stripping markdown fences."""
    clean = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in spec builder response.")
    return json.loads(match.group())


async def build_spec(request: SpecBuildRequest, db_create_spec_fn: Any) -> SpecBuildResponse:
    """Call Kimi K2.6 to generate a structured spec and persist it to Supabase."""
    task_id = request.task_id or f"SPEC-{str(uuid4())[:6].upper()}"

    preflight_input = GatewayRequest(
        project_id=request.project_id,
        task_id=task_id,
        task_type=_SPEC_BUILDER_TASK_TYPE,
        user_request=request.user_request,
        requested_context_scope=request.context_scope,
        explicitly_authorized=request.explicitly_authorized,
        model=_SPEC_BUILDER_MODEL,
        account_id=request.account_id,
    )
    preflight = run_preflight(preflight_input)

    if not preflight.allowed:
        return SpecBuildResponse(
            spec_id="",
            spec={},
            model_used=_SPEC_BUILDER_MODEL,
            estimated_cost_usd=preflight.estimated_cost_usd,
            real_cost_usd=None,
            allowed=False,
            reason=preflight.reason,
        )

    user_prompt = (
        f"Project: {request.project_name}\n\n"
        f"User Request:\n\"\"\"\n{request.user_request}\n\"\"\""
    )

    provider_name = provider_for(_SPEC_BUILDER_MODEL)
    provider = get_provider_client(provider_name)
    started = time.perf_counter()
    try:
        response = await provider.chat(
            model=_SPEC_BUILDER_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=preflight.max_output_tokens,
            account_id=request.account_id,
        )
    except Exception as exc:
        logger.warning("Spec builder provider call failed: %s — using template spec.", exc)
        spec_data = {
            "title": request.project_name,
            "problem": request.user_request[:300],
            "expected_result": "See user request.",
            "allowed_tools": ["run_command", "view_file", "write_to_file"],
            "required_agents": [_SPEC_BUILDER_MODEL],
            "acceptance_criteria": ["Solution addresses the stated problem.", "Output is complete and correct."],
            "risks": [f"Provider unavailable: {exc.__class__.__name__}. Spec generated from template."],
            "budget": {"max_total_cost_usd": 0.50, "max_iterations": 5},
            "test_harness": {"type": "manual", "required_score": 80},
        }
        saved = await db_create_spec_fn(
            project_id=request.project_id,
            title=spec_data["title"],
            problem=spec_data["problem"],
            expected_result=spec_data["expected_result"],
            allowed_tools=spec_data["allowed_tools"],
            required_agents=spec_data["required_agents"],
            acceptance_criteria=spec_data["acceptance_criteria"],
            risks=spec_data["risks"],
            budget=spec_data["budget"],
            test_harness=spec_data["test_harness"],
        )
        return SpecBuildResponse(
            spec_id=saved.get("id", ""),
            spec=saved,
            model_used=_SPEC_BUILDER_MODEL,
            estimated_cost_usd=preflight.estimated_cost_usd,
            real_cost_usd=0.0,
            allowed=True,
            reason=f"Provider unavailable — template spec generated. Configure {_SPEC_BUILDER_MODEL} API key for AI-generated specs.",
        )

    latency_ms = int((time.perf_counter() - started) * 1000)
    actual_cost = real_cost_usd(
        _SPEC_BUILDER_MODEL,
        response.usage.input_tokens or 0,
        response.usage.output_tokens or 0,
    )

    try:
        spec_data = _extract_json(response.content)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("Failed to parse spec JSON: %s. Raw: %s", exc, response.content[:200])
        spec_data = {
            "title": request.project_name,
            "problem": request.user_request[:300],
            "expected_result": "See user request.",
            "allowed_tools": ["run_command", "view_file", "write_to_file"],
            "required_agents": [_SPEC_BUILDER_MODEL],
            "acceptance_criteria": ["Solution addresses the stated problem."],
            "risks": ["Model output could not be parsed into structured spec."],
            "budget": {"max_total_cost_usd": 0.50, "max_iterations": 5},
            "test_harness": {"type": "manual", "required_score": 80},
        }

    saved = await db_create_spec_fn(
        project_id=request.project_id,
        title=spec_data.get("title", request.project_name),
        problem=spec_data.get("problem", request.user_request),
        expected_result=spec_data.get("expected_result"),
        allowed_tools=spec_data.get("allowed_tools"),
        required_agents=spec_data.get("required_agents"),
        acceptance_criteria=spec_data.get("acceptance_criteria"),
        risks=spec_data.get("risks"),
        budget=spec_data.get("budget"),
        test_harness=spec_data.get("test_harness"),
    )

    return SpecBuildResponse(
        spec_id=saved.get("id", ""),
        spec=saved,
        model_used=response.model,
        estimated_cost_usd=preflight.estimated_cost_usd,
        real_cost_usd=actual_cost,
        allowed=True,
        reason="Spec generated and persisted.",
    )
